from dataclasses import dataclass
from decimal import Decimal

from app.domain.odds import SPECIAL_ODDS, TIER_ODDS


@dataclass(frozen=True)
class DropInput:
    name: str
    rarity: str | None
    is_special: bool
    price: Decimal | None
    weight: int = 1


@dataclass(frozen=True)
class UnboxingEvaluation:
    expected_value: Decimal | None
    cost: Decimal | None
    roi: Decimal | None
    missing_prices: int
    odds_valid: bool
    probabilities: dict[str, Decimal]


def not_evaluated(cost: Decimal | None = None) -> UnboxingEvaluation:
    return UnboxingEvaluation(
        expected_value=None,
        cost=cost,
        roi=None,
        missing_prices=0,
        odds_valid=False,
        probabilities={},
    )


def evaluate_unboxing(
    drops: list[DropInput],
    case_price: Decimal | None,
    key_price: Decimal,
) -> UnboxingEvaluation:
    cost = _cost(case_price, key_price)
    _ensure_unique_names(drops)
    probabilities = _probabilities(drops)
    if probabilities is None:
        return not_evaluated(cost)
    missing = sum(1 for drop in drops if drop.price is None)
    expected = _expected_value(drops, probabilities) if missing == 0 else None
    return UnboxingEvaluation(
        expected_value=expected,
        cost=cost,
        roi=_roi(expected, cost),
        missing_prices=missing,
        odds_valid=True,
        probabilities=probabilities,
    )


def _cost(case_price: Decimal | None, key_price: Decimal) -> Decimal | None:
    if case_price is None:
        return None
    return case_price + key_price


def _ensure_unique_names(drops: list[DropInput]) -> None:
    names = [drop.name for drop in drops]
    if len(names) != len(set(names)):
        raise ValueError("у предметов кейса должны быть уникальные имена")


def _probabilities(drops: list[DropInput]) -> dict[str, Decimal] | None:
    pools = _odds_pools(drops)
    if pools is None or not _pools_cover_whole_case(pools):
        return None
    probabilities: dict[str, Decimal] = {}
    for odds, group in pools:
        probabilities.update(_share(odds, group))
    return probabilities


def _odds_pools(drops: list[DropInput]) -> list[tuple[Decimal, list[DropInput]]] | None:
    if not drops:
        return None
    specials = [drop for drop in drops if drop.is_special]
    tiers: dict[str, list[DropInput]] = {}
    for drop in drops:
        if drop.is_special:
            continue
        if drop.rarity not in TIER_ODDS:
            return None
        tiers.setdefault(drop.rarity, []).append(drop)
    pools = [(TIER_ODDS[rarity], group) for rarity, group in tiers.items()]
    if specials:
        pools.append((SPECIAL_ODDS, specials))
    return pools


def _pools_cover_whole_case(pools: list[tuple[Decimal, list[DropInput]]]) -> bool:
    total = sum((odds for odds, _ in pools), Decimal(0))
    return total == Decimal("1.0000")


def _share(odds: Decimal, group: list[DropInput]) -> dict[str, Decimal]:
    total = sum(drop.weight for drop in group)
    return {drop.name: odds * drop.weight / total for drop in group}


def _expected_value(drops: list[DropInput], probabilities: dict[str, Decimal]) -> Decimal:
    total = Decimal(0)
    for drop in drops:
        if drop.price is not None:
            total += probabilities[drop.name] * drop.price
    return total


def _roi(expected: Decimal | None, cost: Decimal | None) -> Decimal | None:
    if expected is None or cost is None or cost == 0:
        return None
    return (expected - cost) / cost
