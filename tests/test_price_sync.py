import asyncio
from decimal import Decimal
from typing import Self

import pytest

from app.collectors.sources import CollectorError
from app.domain.records import Listing
from app.jobs.tasks import _sync_prices
from app.jobs.worker import MISFIRE_GRACE_SECONDS, create_scheduler


class _Session:
    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_args: object) -> bool:
        return False

    async def commit(self) -> None:
        return None


class _Repo:
    def __init__(self, _session: object) -> None:
        self.snapshots = 0
        self.windows = 0

    async def upsert_listings(self, _listings: list[Listing]) -> int:
        return len(_listings)

    async def capture_daily_snapshot(self, _source: str, _currency: str) -> int:
        self.snapshots += 1
        return 1

    async def upsert_windows(self, windows: list[object]) -> int:
        self.windows += len(windows)
        return len(windows)


class _Client:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        return None

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_args: object) -> bool:
        return False


class _SkinportDown:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        return None

    async def fetch_listings(self) -> list[Listing]:
        return [
            Listing(
                market_hash_name="Kilowatt Case",
                currency="USD",
                suggested_price=Decimal("0.15"),
                min_price=None,
                max_price=None,
                mean_price=None,
                median_price=None,
                quantity=1,
            )
        ]

    async def fetch_windows(self) -> list[object]:
        raise CollectorError("history down")


def test_snapshot_is_saved_when_history_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _Repo(None)

    monkeypatch.setattr("app.jobs.tasks.httpx.AsyncClient", _Client)
    monkeypatch.setattr("app.jobs.tasks.SkinportClient", _SkinportDown)
    monkeypatch.setattr("app.jobs.tasks.SessionLocal", _Session)
    monkeypatch.setattr("app.jobs.tasks.PriceRepository", lambda _session: repo)

    asyncio.run(_sync_prices())

    assert repo.snapshots == 1
    assert repo.windows == 0


def test_worker_tolerates_a_busy_event_loop() -> None:
    async def grace_times() -> list[int]:
        scheduler = create_scheduler()
        scheduler.start(paused=True)
        try:
            return [job.misfire_grace_time for job in scheduler.get_jobs()]
        finally:
            scheduler.shutdown(wait=False)

    assert asyncio.run(grace_times()) == [MISFIRE_GRACE_SECONDS] * 3
