import logging
from typing import Any

from sqlalchemy.exc import IntegrityError

from app.collectors.sources import CollectorError
from app.domain.records import CrateRecord, SkinRecord
from app.repositories.catalog import (
    CatalogRepository,
    case_rows,
    crate_item_rows,
    drop_rows,
    skin_item_rows,
)

logger = logging.getLogger(__name__)


class CatalogSyncService:
    def __init__(self, repository: CatalogRepository) -> None:
        self._repository = repository

    async def sync(self, skins: list[SkinRecord], crates: list[CrateRecord]) -> dict[str, int]:
        if not skins or not crates:
            raise CollectorError("каталог пустой, базу не меняем")

        crates = _unique_crates(crates)
        items = _unique_items(skin_item_rows(skins) + crate_item_rows(crates))
        cases = case_rows(crates)
        item_count = await self._repository.upsert_items(items)
        try:
            case_count = await self._repository.upsert_cases(cases)
        except IntegrityError as exc:
            raise CollectorError(
                "кейс с прежним bymykel_id сменил имя, каталог не обновлён"
            ) from exc
        case_ids = await self._repository.ids_by_bymykel()
        drops = drop_rows(crates, case_ids)
        drop_count = await self._repository.replace_drops(drops)
        logger.info(
            "catalog synced items=%s cases=%s drops=%s",
            item_count,
            case_count,
            drop_count,
        )
        return {"items": item_count, "cases": case_count, "drops": drop_count}


def _unique_crates(crates: list[CrateRecord]) -> list[CrateRecord]:
    chosen: dict[str, CrateRecord] = {}
    for crate in crates:
        current = chosen.get(crate.market_hash_name)
        if current is None or _prefer_crate(crate, current):
            chosen[crate.market_hash_name] = crate
    return list(chosen.values())


def _prefer_crate(candidate: CrateRecord, current: CrateRecord) -> bool:
    if len(candidate.drops) != len(current.drops):
        return len(candidate.drops) > len(current.drops)
    return (candidate.def_index or 0) >= (current.def_index or 0)


def _unique_items(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_hash: dict[str, dict[str, Any]] = {}
    for row in rows:
        by_hash[row["market_hash_name"]] = row
    by_variant: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in by_hash.values():
        by_variant[(row["bymykel_id"], row["wear"], row["kind"])] = row
    return list(by_variant.values())
