import asyncio
from typing import Any, cast

import pytest
from sqlalchemy.exc import IntegrityError

from app.collectors.sources import CollectorError
from app.domain.records import CrateRecord, DropRecord, SkinRecord
from app.repositories.catalog import CatalogRepository
from app.services.catalog_sync import CatalogSyncService

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

    async def upsert_items(self, rows: list[dict[str, Any]]) -> int:
        return len(rows)

    async def upsert_cases(self, _rows: list[dict[str, Any]]) -> int:
        raise IntegrityError("INSERT", {}, Exception("uq_cases_bymykel_id"))

    async def replace_drops(self, _rows: list[dict[str, Any]]) -> int:
        self.drops_replaced = True
        return 0


def test_renamed_case_stops_the_sync_with_a_clear_error() -> None:
    repository = _RenamedCase()
    service = CatalogSyncService(cast(CatalogRepository, repository))

    with pytest.raises(CollectorError, match="сменил имя"):
        asyncio.run(service.sync([SKIN], [CRATE]))

    assert repository.drops_replaced is False
