from decimal import Decimal

from app.domain.constants import WEAR_PREFERENCE
from app.domain.names import price_candidates


def choose_listing_price(
    suggested: Decimal | None,
    median: Decimal | None,
    minimum: Decimal | None,
) -> Decimal | None:
    for value in (suggested, median, minimum):
        if value is not None:
            return value
    return None


def choose_item_price(
    median_30d: Decimal | None,
    median_90d: Decimal | None,
    listing: Decimal | None,
) -> Decimal | None:
    for value in (median_30d, median_90d, listing):
        if value is not None:
            return value
    return None


def resolve_wear_price(
    base_name: str,
    amounts: dict[str, Decimal | None],
    wears: tuple[str, ...] = WEAR_PREFERENCE,
) -> tuple[Decimal | None, str]:
    candidates = price_candidates(base_name, wears)
    for name in candidates:
        amount = amounts.get(name)
        if amount is not None:
            return amount, name
    return None, candidates[0]


def investing_roi(current: Decimal | None, baseline: Decimal | None) -> Decimal | None:
    if current is None or baseline is None or baseline == 0:
        return None
    return (current - baseline) / baseline
