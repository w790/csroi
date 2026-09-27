from dataclasses import dataclass
from decimal import Decimal

from app.domain.odds import SPECIAL_ODDS, TIER_ODDS


@dataclass(frozen=True)
class DropInput:
    name: str
    rarity: str | None
    is_special: bool
    price: Decimal | None


@dataclass(frozen=True)
class UnboxingEvaluation:
    expected_value: Decimal | None
    cost: Decimal | None
    roi: Decimal | None
    missing_prices: int
    odds_valid: bool
    probabilities: dict[str, Decimal]


def evaluate_unboxing(
    drops: list[DropInput],
    case_price: Decimal | None,
    key_price: Decimal,
) -> UnboxingEvaluation:
    empty = UnboxingEvaluation(
        expected_value=None,
        cost=_cost(case_price, key_price),
        roi=None,
        missing_prices=0,
        odds_valid=False,
        probabilities={},
    )
    if not drops:
        return empty

    names = [drop.name for drop in drops]
    if len(names) != len(set(names)):
        raise ValueError("у предметов кейса должны быть уникальные имена")

    specials: list[DropInput] = []
    groups: dict[str, list[DropInput]] = {}
    for drop in drops:
        if drop.is_special:
            specials.append(drop)
            continue
        if drop.rarity not in TIER_ODDS:
            return empty
        groups.setdefault(drop.rarity, []).append(drop)

    used = sum((TIER_ODDS[rarity] for rarity in groups), Decimal(0))
    if specials:
        used += SPECIAL_ODDS
    if used != Decimal("1.0000"):
        return empty

    probabilities: dict[str, Decimal] = {}
    for rarity, group in groups.items():
        chance = TIER_ODDS[rarity] / len(group)
        for drop in group:
            probabilities[drop.name] = chance
    if specials:
        chance = SPECIAL_ODDS / len(specials)
        for drop in specials:
            probabilities[drop.name] = chance

    missing = sum(1 for drop in drops if drop.price is None)
    expected: Decimal | None = None
    if missing == 0:
        expected = sum(
            (probabilities[drop.name] * drop.price for drop in drops),
            Decimal(0),
        )

    cost = _cost(case_price, key_price)
    roi = None
    if expected is not None and cost not in (None, 0):
        roi = (expected - cost) / cost

    return UnboxingEvaluation(
        expected_value=expected,
        cost=cost,
        roi=roi,
        missing_prices=missing,
        odds_valid=True,
        probabilities=probabilities,
    )


def _cost(case_price: Decimal | None, key_price: Decimal) -> Decimal | None:
    if case_price is None:
        return None
    return case_price + key_price
