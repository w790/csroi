from dataclasses import replace

from app.domain.records import CrateRecord, DropRecord


def merge_crate_phases(crate: CrateRecord) -> CrateRecord:
    return replace(crate, drops=tuple(merge_phases(crate.drops)))


def merge_phases(rows: list[DropRecord] | tuple[DropRecord, ...]) -> list[DropRecord]:
    first: dict[str, DropRecord] = {}
    weights: dict[str, int] = {}
    for row in rows:
        first.setdefault(row.name, row)
        weights[row.name] = weights.get(row.name, 0) + row.weight
    return [replace(row, weight=weights[name]) for name, row in first.items()]
