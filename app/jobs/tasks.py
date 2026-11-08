import asyncio
import logging

import httpx

from app.cache.price_lock import acquire_price_lock, release_price_lock
from app.collectors.sources import BymykelClient, SkinportClient
from app.core.config import settings
from app.db.session import SessionLocal
from app.domain.records import CrateRecord, SkinRecord
from app.repositories.catalog import CatalogRepository
from app.repositories.prices import PriceRepository
from app.services.catalog_sync import CatalogSyncService
from app.services.price_sync import PriceSyncService

logger = logging.getLogger(__name__)
_catalog_lock = asyncio.Lock()
_price_lock = asyncio.Lock()


async def run_catalog_sync() -> dict[str, int]:
    async with _catalog_lock:
        return await _sync_catalog()


async def run_price_sync() -> None:
    async with _price_lock:
        await _sync_prices_under_redis_lock()


async def _sync_catalog() -> dict[str, int]:
    skins, crates = await _fetch_catalog()
    async with SessionLocal() as session:
        repository = CatalogRepository(session)
        service = CatalogSyncService(repository)
        stats = await service.sync(skins, crates)
        await session.commit()
    return stats


async def _fetch_catalog() -> tuple[list[SkinRecord], list[CrateRecord]]:
    async with _http_client() as client:
        bymykel = BymykelClient(client, settings.bymykel_base_url)
        skins = await bymykel.fetch_skins()
        crates = await bymykel.fetch_crates()
    return skins, crates


async def _sync_prices_under_redis_lock() -> None:
    token = await acquire_price_lock()
    if token is None:
        logger.info("price sync skipped, another process holds the lock")
        return
    try:
        await _sync_prices()
    finally:
        await release_price_lock(token)


async def _sync_prices() -> None:
    async with _http_client() as client, SessionLocal() as session:
        skinport = SkinportClient(
            client,
            settings.skinport_base_url,
            settings.skinport_app_id,
            settings.skinport_currency,
        )
        repository = PriceRepository(session)
        service = PriceSyncService(skinport, repository, session, settings.skinport_currency)
        await service.sync()


def _http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=settings.http_timeout_seconds, follow_redirects=True)
