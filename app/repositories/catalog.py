from collections.abc import Callable, Hashable
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.batching import chunks
from app.domain.constants import KIND_CRATE, KIND_SKIN
from app.domain.names import market_hash_name
from app.domain.records import CrateRecord, SkinRecord
from app.models.case import Case, CaseDrop
from app.models.item import Item


class CatalogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_items(self, skins: list[SkinRecord], crates: list[CrateRecord]) -> int:
        rows = _skin_item_rows(skins) + _crate_item_rows(crates)
        unique_rows = _unique_item_rows(rows)
        for batch in chunks(unique_rows, 400):
            stmt = pg_insert(Item).values(list(batch))
            excluded = stmt.excluded
            stmt = stmt.on_conflict_do_update(
                index_elements=[Item.market_hash_name],
                set_={
                    "bymykel_id": excluded.bymykel_id,
                    "base_name": excluded.base_name,
                    "wear": excluded.wear,
                    "kind": excluded.kind,
                    "weapon": excluded.weapon,
                    "category": excluded.category,
                    "rarity": excluded.rarity,
                    "rarity_color": excluded.rarity_color,
                    "image_url": excluded.image_url,
                    "min_float": excluded.min_float,
                    "max_float": excluded.max_float,
                    "stattrak": excluded.stattrak,
                    "souvenir": excluded.souvenir,
                    "def_index": excluded.def_index,
                    "paint_index": excluded.paint_index,
                },
            )
            await self._session.execute(stmt)
        return len(unique_rows)

    async def upsert_cases(self, crates: list[CrateRecord]) -> int:
        rows = _case_rows(crates)
        for batch in chunks(rows, 200):
            stmt = pg_insert(Case).values(list(batch))
            excluded = stmt.excluded
            stmt = stmt.on_conflict_do_update(
                index_elements=[Case.market_hash_name],
                set_={
                    "bymykel_id": excluded.bymykel_id,
                    "name": excluded.name,
                    "crate_type": excluded.crate_type,
                    "image_url": excluded.image_url,
                    "def_index": excluded.def_index,
                    "first_sale_date": excluded.first_sale_date,
                },
            )
            await self._session.execute(stmt)
        return len(rows)

    async def replace_drops(self, crates: list[CrateRecord]) -> int:
        case_ids = await self._case_ids_by_bymykel()
        rows = _drop_rows(crates, case_ids)
        await self._session.execute(delete(CaseDrop))
        for batch in chunks(rows, 500):
            await self._session.execute(pg_insert(CaseDrop), list(batch))
        return len(rows)

    async def list_cases(self, crate_type: str | None) -> list[Case]:
        stmt = select(Case).order_by(Case.name)
        if crate_type is not None:
            stmt = stmt.where(Case.crate_type == crate_type)
        return list(await self._session.scalars(stmt))

    async def get_case(self, case_id: int) -> Case | None:
        return await self._session.get(Case, case_id)

    async def drops_for(self, case_ids: list[int]) -> list[CaseDrop]:
        if not case_ids:
            return []
        stmt = select(CaseDrop).where(CaseDrop.case_id.in_(case_ids))
        return list(await self._session.scalars(stmt))

    async def float_ranges(
        self,
        names: list[str],
    ) -> dict[str, tuple[float | None, float | None]]:
        found: dict[str, tuple[float | None, float | None]] = {}
        for batch in chunks(names, 1000):
            stmt = (
                select(Item.base_name, func.min(Item.min_float), func.max(Item.max_float))
                .where(Item.kind == KIND_SKIN, Item.base_name.in_(list(batch)))
                .group_by(Item.base_name)
            )
            for name, low, high in (await self._session.execute(stmt)).all():
                found[name] = (low, high)
        return found

    async def _case_ids_by_bymykel(self) -> dict[str, int]:
        result = await self._session.execute(select(Case.bymykel_id, Case.id))
        return {bymykel_id: case_id for bymykel_id, case_id in result.all()}


def _skin_item_rows(skins: list[SkinRecord]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for skin in skins:
        wears = skin.wears or ("",)
        for wear in wears:
            rows.append(
                {
                    "market_hash_name": market_hash_name(skin.name, wear or None),
                    "bymykel_id": skin.bymykel_id,
                    "base_name": skin.name,
                    "wear": wear,
                    "kind": KIND_SKIN,
                    "weapon": skin.weapon,
                    "category": skin.category,
                    "rarity": skin.rarity,
                    "rarity_color": skin.rarity_color,
                    "image_url": skin.image_url,
                    "min_float": skin.min_float,
                    "max_float": skin.max_float,
                    "stattrak": skin.stattrak,
                    "souvenir": skin.souvenir,
                    "def_index": None,
                    "paint_index": skin.paint_index,
                }
            )
    return rows


def _crate_item_rows(crates: list[CrateRecord]) -> list[dict[str, Any]]:
    return [
        {
            "market_hash_name": crate.market_hash_name,
            "bymykel_id": crate.bymykel_id,
            "base_name": crate.name,
            "wear": "",
            "kind": KIND_CRATE,
            "weapon": None,
            "category": crate.crate_type,
            "rarity": None,
            "rarity_color": None,
            "image_url": crate.image_url,
            "min_float": None,
            "max_float": None,
            "stattrak": False,
            "souvenir": False,
            "def_index": crate.def_index,
            "paint_index": None,
        }
        for crate in crates
    ]


def _unique_item_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_hash = _last_by(rows, lambda row: row["market_hash_name"])
    return _last_by(by_hash, lambda row: (row["bymykel_id"], row["wear"], row["kind"]))


def _last_by(
    rows: list[dict[str, Any]],
    key: Callable[[dict[str, Any]], Hashable],
) -> list[dict[str, Any]]:
    chosen = {key(row): row for row in rows}
    return list(chosen.values())


def _case_rows(crates: list[CrateRecord]) -> list[dict[str, Any]]:
    return [
        {
            "bymykel_id": crate.bymykel_id,
            "name": crate.name,
            "market_hash_name": crate.market_hash_name,
            "crate_type": crate.crate_type,
            "image_url": crate.image_url,
            "def_index": crate.def_index,
            "first_sale_date": crate.first_sale_date,
        }
        for crate in crates
    ]


def _drop_rows(crates: list[CrateRecord], case_ids: dict[str, int]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for crate in crates:
        case_id = case_ids.get(crate.bymykel_id)
        if case_id is None:
            continue
        for drop in crate.drops:
            rows.append(
                {
                    "case_id": case_id,
                    "bymykel_id": drop.bymykel_id,
                    "name": drop.name,
                    "rarity": drop.rarity,
                    "is_special": drop.is_special,
                    "weight": drop.weight,
                    "image_url": drop.image_url,
                }
            )
    return rows
