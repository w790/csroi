import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.sources import CollectorError, SkinportClient
from app.domain.constants import SOURCE_SKINPORT
from app.repositories.prices import PriceRepository

logger = logging.getLogger(__name__)


class PriceSyncError(Exception):
    pass


class PriceSyncService:
    def __init__(
        self,
        skinport: SkinportClient,
        repository: PriceRepository,
        session: AsyncSession,
        currency: str,
    ) -> None:
        self._skinport = skinport
        self._repository = repository
        self._session = session
        self._currency = currency

    async def sync(self) -> None:
        await self._save_listings()
        await self._save_windows_if_available()

    async def _save_listings(self) -> None:
        listings = await self._skinport.fetch_listings()
        if not listings:
            raise PriceSyncError("skinport вернул пустой список цен")
        saved = await self._repository.upsert_listings(listings)
        snapshots = await self._repository.capture_daily_snapshot(SOURCE_SKINPORT, self._currency)
        await self._session.commit()
        logger.info("skinport listings=%s snapshots=%s", saved, snapshots)

    async def _save_windows_if_available(self) -> None:
        try:
            windows = await self._skinport.fetch_windows()
        except (CollectorError, httpx.HTTPError):
            logger.exception("skinport history skipped, listings and snapshot are already saved")
            return
        saved = await self._repository.upsert_windows(windows)
        await self._session.commit()
        logger.info("skinport windows=%s", saved)
