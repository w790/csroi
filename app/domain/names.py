from dataclasses import replace

from app.domain.constants import WEAR_FLOAT_RANGES, WEAR_PREFERENCE
from app.domain.records import DropRecord


def market_hash_name(base_name: str, wear: str | None) -> str:
    if wear:
        return f"{base_name} ({wear})"
    return base_name


def wear_order(min_float: float | None, max_float: float | None) -> tuple[str, ...]:
    if min_float is None or max_float is None or max_float <= min_float:
        return WEAR_PREFERENCE
    shares = {
        wear: max(0.0, min(high, max_float) - max(low, min_float))
        for wear, (low, high) in WEAR_FLOAT_RANGES.items()
    }
    first, *rest = WEAR_PREFERENCE
    return (first, *sorted(rest, key=lambda wear: -shares[wear]))


def price_candidates(base_name: str, wears: tuple[str, ...] = WEAR_PREFERENCE) -> list[str]:
    ordered = [market_hash_name(base_name, wear) for wear in wears]
    ordered.append(base_name)
    unique: list[str] = []
    seen: set[str] = set()
    for name in ordered:
        if name not in seen:
            seen.add(name)
            unique.append(name)
    return unique


def merge_phases(rows: list[DropRecord] | tuple[DropRecord, ...]) -> list[DropRecord]:
    first: dict[str, DropRecord] = {}
    weights: dict[str, int] = {}
    for row in rows:
        first.setdefault(row.name, row)
        weights[row.name] = weights.get(row.name, 0) + row.weight
    return [replace(row, weight=weights[name]) for name, row in first.items()]
