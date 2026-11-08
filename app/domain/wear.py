from app.domain.constants import WEAR_FLOAT_RANGES, WEAR_PREFERENCE


def wear_order(min_float: float | None, max_float: float | None) -> tuple[str, ...]:
    if min_float is None or max_float is None or max_float <= min_float:
        return WEAR_PREFERENCE
    shares = {
        wear: _float_overlap(low, high, min_float, max_float)
        for wear, (low, high) in WEAR_FLOAT_RANGES.items()
    }
    first, *rest = WEAR_PREFERENCE
    fallbacks = sorted(rest, key=lambda wear: -shares[wear])
    return (first, *fallbacks)


def _float_overlap(low: float, high: float, min_float: float, max_float: float) -> float:
    overlap = min(high, max_float) - max(low, min_float)
    return max(0.0, overlap)
