from app.domain.constants import WEAR_PREFERENCE


def price_candidates(base_name: str, wears: tuple[str, ...] = WEAR_PREFERENCE) -> list[str]:
    ordered = [market_hash_name(base_name, wear) for wear in wears]
    ordered.append(base_name)
    return list(dict.fromkeys(ordered))


def market_hash_name(base_name: str, wear: str | None) -> str:
    if wear:
        return f"{base_name} ({wear})"
    return base_name
