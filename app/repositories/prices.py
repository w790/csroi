from collections.abc import Iterable, Sequence
from datetime import UTC, date, datetime
from typing import Any, cast

from sqlalchemy import CursorResult, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.constants import SOURCE_SKINPORT
from app.domain.records import Listing, SaleWindow
from app.models.price import Price, PriceSnapshot, PriceWindow


def _chunks[T](rows: Sequence[T], size: int) -> Iterable[Sequence[T]]:
    for index in range(0, len(rows), size):
        yield rows[index : index + size]


class PriceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_listings(self, listings: list[Listing], source: str = SOURCE_SKINPORT) -> int:
        folded: dict[tuple[str, str], Listing] = {}
        for item in listings:
            folded[(item.market_hash_name, item.currency)] = item
        rows = [
            {
                "market_hash_name": item.market_hash_name,
                "source": source,
                "currency": item.currency,
                "suggested_price": item.suggested_price,
                "min_price": item.min_price,
                "max_price": item.max_price,
                "mean_price": item.mean_price,
                "median_price": item.median_price,
                "quantity": item.quantity,
                "updated_at": datetime.now(UTC),
            }
            for item in folded.values()
        ]
        for batch in _chunks(rows, 500):
            stmt = pg_insert(Price).values(list(batch))
            excluded = stmt.excluded
            stmt = stmt.on_conflict_do_update(
                constraint="uq_prices_identity",
                set_={
                    "suggested_price": excluded.suggested_price,
                    "min_price": excluded.min_price,
                    "max_price": excluded.max_price,
                    "mean_price": excluded.mean_price,
                    "median_price": excluded.median_price,
                    "quantity": excluded.quantity,
                    "updated_at": excluded.updated_at,
                },
            )
            await self._session.execute(stmt)
        return len(rows)

    async def upsert_windows(self, windows: list[SaleWindow], source: str = SOURCE_SKINPORT) -> int:
        fetched_at = datetime.now(UTC)
        folded: dict[tuple[str, str, str], SaleWindow] = {}
        for item in windows:
            folded[(item.market_hash_name, item.currency, item.window)] = item
        rows = [
            {
                "market_hash_name": item.market_hash_name,
                "source": source,
                "currency": item.currency,
                "window": item.window,
                "min_price": item.min_price,
                "max_price": item.max_price,
                "avg_price": item.avg_price,
                "median_price": item.median_price,
                "volume": item.volume,
                "fetched_at": fetched_at,
            }
            for item in folded.values()
        ]
        for batch in _chunks(rows, 500):
            stmt = pg_insert(PriceWindow).values(list(batch))
            excluded = stmt.excluded
            stmt = stmt.on_conflict_do_update(
                constraint="uq_price_windows_identity",
                set_={
                    "min_price": excluded.min_price,
                    "max_price": excluded.max_price,
                    "avg_price": excluded.avg_price,
                    "median_price": excluded.median_price,
                    "volume": excluded.volume,
                    "fetched_at": excluded.fetched_at,
                },
            )
            await self._session.execute(stmt)
        return len(rows)

    async def capture_daily_snapshot(self, source: str, currency: str) -> int:
        result = await self._session.execute(
            text(
                """
                INSERT INTO price_snapshots (
                    market_hash_name, source, currency, price, captured_on
                )
                SELECT
                    market_hash_name,
                    source,
                    currency,
                    COALESCE(median_price, suggested_price, min_price),
                    (now() AT TIME ZONE 'UTC')::date
                FROM prices
                WHERE source = :source
                  AND currency = :currency
                  AND COALESCE(median_price, suggested_price, min_price) IS NOT NULL
                ON CONFLICT ON CONSTRAINT uq_price_snapshots_identity DO NOTHING
                """
            ),
            {"source": source, "currency": currency},
        )
        return cast(CursorResult[Any], result).rowcount or 0

    async def listings_for(
        self,
        names: list[str],
        source: str,
        currency: str,
    ) -> dict[str, Price]:
        if not names:
            return {}
        found: dict[str, Price] = {}
        for batch in _chunks(names, 1000):
            stmt = select(Price).where(
                Price.source == source,
                Price.currency == currency,
                Price.market_hash_name.in_(list(batch)),
            )
            for price in await self._session.scalars(stmt):
                found[price.market_hash_name] = price
        return found

    async def windows_for(
        self,
        names: list[str],
        source: str,
        currency: str,
    ) -> dict[tuple[str, str], PriceWindow]:
        if not names:
            return {}
        found: dict[tuple[str, str], PriceWindow] = {}
        for batch in _chunks(names, 1000):
            stmt = select(PriceWindow).where(
                PriceWindow.source == source,
                PriceWindow.currency == currency,
                PriceWindow.market_hash_name.in_(list(batch)),
            )
            for row in await self._session.scalars(stmt):
                found[(row.market_hash_name, row.window)] = row
        return found

    async def snapshots_for(
        self,
        name: str,
        source: str,
        currency: str,
        since: date,
    ) -> list[PriceSnapshot]:
        stmt = (
            select(PriceSnapshot)
            .where(
                PriceSnapshot.market_hash_name == name,
                PriceSnapshot.source == source,
                PriceSnapshot.currency == currency,
                PriceSnapshot.captured_on >= since,
            )
            .order_by(PriceSnapshot.captured_on)
        )
        return list(await self._session.scalars(stmt))
