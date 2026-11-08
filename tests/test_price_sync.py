import asyncio
from decimal import Decimal
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.sources import CollectorError, SkinportClient
from app.domain.records import Listing, SaleWindow
from app.jobs.worker import MISFIRE_GRACE_SECONDS, create_scheduler
from app.repositories.prices import PriceRepository
from app.services.price_sync import PriceSyncError, PriceSyncService

LISTING = Listing(
    market_hash_name="Kilowatt Case",
    currency="USD",
    suggested_price=Decimal("0.15"),
    min_price=None,
    max_price=None,
    mean_price=None,
    median_price=None,
    quantity=1,
)


class _Session:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class _Repo:
    def __init__(self) -> None:
        self.snapshots = 0
        self.windows = 0

    async def upsert_listings(self, listings: list[Listing]) -> int:
        return len(listings)

    async def capture_daily_snapshot(self, _source: str, _currency: str) -> int:
        self.snapshots += 1
        return 1

    async def upsert_windows(self, windows: list[SaleWindow]) -> int:
        self.windows += len(windows)
        return len(windows)


class _Skinport:
    def __init__(self, listings: list[Listing], *, history_up: bool) -> None:
        self._listings = listings
        self._history_up = history_up

    async def fetch_listings(self) -> list[Listing]:
        return self._listings

    async def fetch_windows(self) -> list[SaleWindow]:
        if not self._history_up:
            raise CollectorError("history down")
        return []


def _sync(skinport: _Skinport) -> tuple[_Repo, _Session]:
    repo = _Repo()
    session = _Session()
    service = PriceSyncService(
        cast(SkinportClient, skinport),
        cast(PriceRepository, repo),
        cast(AsyncSession, session),
        "USD",
    )
    asyncio.run(service.sync())
    return repo, session


def test_snapshot_is_saved_when_history_fails() -> None:
    repo, session = _sync(_Skinport([LISTING], history_up=False))

    assert repo.snapshots == 1
    assert repo.windows == 0
    assert session.commits == 1


def test_empty_listings_stop_the_sync() -> None:
    with pytest.raises(PriceSyncError, match="пустой"):
        _sync(_Skinport([], history_up=True))


def test_worker_tolerates_a_busy_event_loop() -> None:
    async def grace_times() -> list[int]:
        scheduler = create_scheduler()
        scheduler.start(paused=True)
        try:
            return [job.misfire_grace_time for job in scheduler.get_jobs()]
        finally:
            scheduler.shutdown(wait=False)

    assert asyncio.run(grace_times()) == [MISFIRE_GRACE_SECONDS] * 3
