import asyncio
from decimal import Decimal

from app.collectors.sources import CollectorError
from app.domain.records import Listing
from app.jobs.tasks import _sync_prices


class _Session:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def commit(self):
        return None


class _Repo:
    def __init__(self, _session):
        self.snapshots = 0
        self.windows = 0

    async def upsert_listings(self, _listings):
        return len(_listings)

    async def capture_daily_snapshot(self, _source, _currency):
        self.snapshots += 1
        return 1

    async def upsert_windows(self, windows):
        self.windows += len(windows)
        return len(windows)


class _Client:
    def __init__(self, *_args, **_kwargs):
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False


class _SkinportDown:
    def __init__(self, *_args, **_kwargs):
        return None

    async def fetch_listings(self):
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

    async def fetch_windows(self):
        raise CollectorError("history down")


def test_snapshot_is_saved_when_history_fails(monkeypatch) -> None:
    repo = _Repo(None)

    monkeypatch.setattr("app.jobs.tasks.httpx.AsyncClient", _Client)
    monkeypatch.setattr("app.jobs.tasks.SkinportClient", _SkinportDown)
    monkeypatch.setattr("app.jobs.tasks.SessionLocal", _Session)
    monkeypatch.setattr("app.jobs.tasks.PriceRepository", lambda _session: repo)

    asyncio.run(_sync_prices())

    assert repo.snapshots == 1
    assert repo.windows == 0
