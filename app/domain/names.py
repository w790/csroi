from typing import TypeVar

from app.domain.constants import WEAR_PREFERENCE

T = TypeVar("T")


def market_hash_name(base_name: str, wear: str | None) -> str:
    if wear:
        return f"{base_name} ({wear})"
    return base_name


def preferred_wear(wears: tuple[str, ...] | list[str]) -> str | None:
    available = set(wears)
    for wear in WEAR_PREFERENCE:
        if wear in available:
            return wear
    if wears:
        return wears[0]
    return None


def preferred_market_hash_name(base_name: str, wears: tuple[str, ...] | list[str]) -> str:
    return market_hash_name(base_name, preferred_wear(wears))


def price_candidates(base_name: str) -> list[str]:
    ordered = [market_hash_name(base_name, wear) for wear in WEAR_PREFERENCE]
    ordered.append(base_name)
    unique: list[str] = []
    seen: set[str] = set()
    for name in ordered:
        if name not in seen:
            seen.add(name)
            unique.append(name)
    return unique


def unique_by_name(rows: list[T] | tuple[T, ...]) -> list[T]:
    seen: set[str] = set()
    result: list[T] = []
    for row in rows:
        name = getattr(row, "name", None)
        if not name or name in seen:
            continue
        seen.add(name)
        result.append(row)
    return result
