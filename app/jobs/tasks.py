import asyncio
import logging

import httpx

from app.cache.prices import acquire_price_lock, release_price_lock
from app.collectors.sources import BymykelClient, CollectorError, SkinportClient
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import SessionLocal
from app.domain.constants import SOURCE_SKINPORT
from app.repositories.catalog import CatalogRepository
from app.repositories.prices import PriceRepository
from app.services.catalog_sync import CatalogSyncService

logger = logging.getLogger(__name__)
_catalog_lock = asyncio.Lock()
_price_lock = asyncio.Lock()


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=settings.http_timeout_seconds, follow_redirects=True)


async def run_catalog() -> dict[str, int]:
    setup_logging()
    async with _catalog_lock:
        return await _load_catalog()


async def _load_catalog() -> dict[str, int]:
    async with _client() as client:
        bymykel = BymykelClient(client, settings.bymykel_base_url)
        skins = await bymykel.fetch_skins()
        crates = await bymykel.fetch_crates()
    async with SessionLocal() as session:
        stats = await CatalogSyncService(CatalogRepository(session)).sync(skins, crates)
        await session.commit()
    return stats


async def run_price_sync() -> None:
    setup_logging()
    async with _price_lock:
        token = await acquire_price_lock()
        if token is None:
            logger.info("price sync skipped, another process holds the lock")
            return
        try:
            await _sync_prices()
        finally:
            await release_price_lock(token)


async def _sync_prices() -> None:
    async with _client() as client:
        skinport = SkinportClient(
            client,
            settings.skinport_base_url,
            settings.skinport_app_id,
            settings.skinport_currency,
        )
        listings = await skinport.fetch_listings()
        if not listings:
            raise CollectorError("skinport вернул пустой список цен")
        async with SessionLocal() as session:
            repository = PriceRepository(session)
            saved = await repository.upsert_listings(listings)
            snapshots = await repository.capture_daily_snapshot(
                SOURCE_SKINPORT,
                settings.skinport_currency,
            )
            await session.commit()
        logger.info("skinport listings=%s snapshots=%s", saved, snapshots)

        try:
            windows = await skinport.fetch_windows()
        except (CollectorError, httpx.HTTPError):
            logger.exception("skinport history skipped, listings and snapshot are already saved")
            return
        async with SessionLocal() as session:
            saved_windows = await PriceRepository(session).upsert_windows(windows)
            await session.commit()
        logger.info("skinport windows=%s", saved_windows)
