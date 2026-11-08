import logging

from sqlalchemy.exc import IntegrityError

from app.domain.phases import merge_crate_phases
from app.domain.records import CrateRecord, SkinRecord
from app.repositories.catalog import CatalogRepository

logger = logging.getLogger(__name__)


class CatalogSyncError(Exception):
    pass


class CatalogSyncService:
    def __init__(self, repository: CatalogRepository) -> None:
        self._repository = repository

    async def sync(self, skins: list[SkinRecord], crates: list[CrateRecord]) -> dict[str, int]:
        _ensure_not_empty(skins, crates)
        prepared = _prepare_crates(crates)
        stats = await self._save(skins, prepared)
        logger.info(
            "catalog synced items=%s cases=%s drops=%s",
            stats["items"],
            stats["cases"],
            stats["drops"],
        )
        return stats

    async def _save(self, skins: list[SkinRecord], crates: list[CrateRecord]) -> dict[str, int]:
        items = await self._repository.upsert_items(skins, crates)
        cases = await self._upsert_cases(crates)
        drops = await self._repository.replace_drops(crates)
        return {"items": items, "cases": cases, "drops": drops}

    async def _upsert_cases(self, crates: list[CrateRecord]) -> int:
        try:
            return await self._repository.upsert_cases(crates)
        except IntegrityError as exc:
            raise CatalogSyncError(
                "кейс с прежним bymykel_id сменил имя, каталог не обновлён"
            ) from exc


def _ensure_not_empty(skins: list[SkinRecord], crates: list[CrateRecord]) -> None:
    if not skins or not crates:
        raise CatalogSyncError("каталог пустой, базу не меняем")


def _prepare_crates(crates: list[CrateRecord]) -> list[CrateRecord]:
    merged = [merge_crate_phases(crate) for crate in crates]
    return _unique_crates(merged)


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
