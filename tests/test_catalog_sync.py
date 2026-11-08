import asyncio
from typing import cast

import pytest
from sqlalchemy.exc import IntegrityError

from app.domain.records import CrateRecord, DropRecord, SkinRecord
from app.repositories.catalog import CatalogRepository
from app.services.catalog_sync import CatalogSyncError, CatalogSyncService

SKIN = SkinRecord(
    "skin-1", "AK-47 | Redline", None, None, None, None, None, None, False, False, None, None, ()
)
CRATE = CrateRecord(
    "crate-1",
    "Chroma Case",
    "Chroma Case",
    "Case",
    None,
    None,
    None,
    (DropRecord("skin-1", "AK-47 | Redline", None, False, None),),
)


class _RenamedCase:
    def __init__(self) -> None:
        self.drops_replaced = False

    async def upsert_items(self, skins: list[SkinRecord], _crates: list[CrateRecord]) -> int:
        return len(skins)

    async def upsert_cases(self, _crates: list[CrateRecord]) -> int:
        raise IntegrityError("INSERT", {}, Exception("uq_cases_bymykel_id"))

    async def replace_drops(self, _crates: list[CrateRecord]) -> int:
        self.drops_replaced = True
        return 0


def test_renamed_case_stops_the_sync_with_a_clear_error() -> None:
    repository = _RenamedCase()
    service = CatalogSyncService(cast(CatalogRepository, repository))

    with pytest.raises(CatalogSyncError, match="сменил имя"):
        asyncio.run(service.sync([SKIN], [CRATE]))

    assert repository.drops_replaced is False


class _Recorder:
    def __init__(self) -> None:
        self.crates: list[CrateRecord] = []

    async def upsert_items(self, skins: list[SkinRecord], _crates: list[CrateRecord]) -> int:
        return len(skins)

    async def upsert_cases(self, crates: list[CrateRecord]) -> int:
        return len(crates)

    async def replace_drops(self, crates: list[CrateRecord]) -> int:
        self.crates = crates
        return sum(len(crate.drops) for crate in crates)


def test_doppler_phases_are_merged_before_saving() -> None:
    phases = tuple(
        DropRecord(f"doppler-{phase}", "★ Karambit | Doppler", "Covert", True, None)
        for phase in range(3)
    )
    crate = CrateRecord("crate-1", "Chroma Case", "Chroma Case", "Case", None, None, None, phases)
    repository = _Recorder()

    asyncio.run(CatalogSyncService(cast(CatalogRepository, repository)).sync([SKIN], [crate]))

    drops = repository.crates[0].drops
    assert [(drop.name, drop.weight) for drop in drops] == [("★ Karambit | Doppler", 3)]
