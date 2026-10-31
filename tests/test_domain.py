from decimal import Decimal

from app.domain.constants import WEAR_PREFERENCE
from app.domain.names import merge_phases, price_candidates, wear_order
from app.domain.odds import SPECIAL_ODDS, TIER_ODDS
from app.domain.pricing import (
    choose_item_price,
    choose_listing_price,
    investing_roi,
    resolve_wear_price,
)
from app.domain.records import DropRecord
from app.domain.roi import DropInput, evaluate_unboxing


def test_tier_odds_sum_to_one() -> None:
    total = sum(TIER_ODDS.values(), Decimal(0)) + SPECIAL_ODDS
    assert total == Decimal("1.0000")


def test_price_candidates_try_field_tested_before_factory_new() -> None:
    assert price_candidates("★ Karambit | Fade")[0].endswith("(Field-Tested)")
    assert price_candidates("★ Karambit | Fade")[-1] == "★ Karambit | Fade"


def test_duplicate_knife_phases_collapse_to_one_name() -> None:
    rows = [
        DropRecord("a", "★ Bowie Knife | Gamma Doppler", "Covert", True, None),
        DropRecord("b", "★ Bowie Knife | Gamma Doppler", "Covert", True, None),
        DropRecord("c", "★ Bowie Knife | Lore", "Covert", True, None),
    ]
    merged = merge_phases(rows)
    assert [(row.name, row.weight) for row in merged] == [
        ("★ Bowie Knife | Gamma Doppler", 2),
        ("★ Bowie Knife | Lore", 1),
    ]
    assert merged[0].bymykel_id == "a"


def test_missing_field_tested_uses_next_listed_wear() -> None:
    amount, name = resolve_wear_price(
        "★ Karambit | Fade",
        {"★ Karambit | Fade (Factory New)": Decimal("100")},
    )
    assert name == "★ Karambit | Fade (Factory New)"
    assert amount == Decimal("100")


def test_unpriced_wear_does_not_count_as_zero() -> None:
    amount, name = resolve_wear_price(
        "AK-47 | Redline",
        {"AK-47 | Redline (Field-Tested)": None},
    )
    assert amount is None
    assert name == "AK-47 | Redline (Field-Tested)"


def test_listing_price_prefers_suggested() -> None:
    assert choose_listing_price(Decimal("10"), Decimal("8"), Decimal("7")) == Decimal("10")
    assert choose_listing_price(None, Decimal("8"), Decimal("7")) == Decimal("8")
    assert choose_listing_price(None, None, None) is None


def test_item_price_prefers_recent_sales_over_listing() -> None:
    assert choose_item_price(Decimal("2014"), Decimal("2066"), Decimal("11456")) == Decimal("2014")
    assert choose_item_price(None, Decimal("2066"), Decimal("11456")) == Decimal("2066")
    assert choose_item_price(None, None, Decimal("11456")) == Decimal("11456")
    assert choose_item_price(None, None, None) is None


def test_investing_roi() -> None:
    assert investing_roi(Decimal("12"), Decimal("10")) == Decimal("0.2")
    assert investing_roi(Decimal("12"), Decimal("0")) is None
    assert investing_roi(None, Decimal("10")) is None


def _one_of_each() -> list[DropInput]:
    return [
        DropInput("blue", "Mil-Spec Grade", False, Decimal("1")),
        DropInput("purple", "Restricted", False, Decimal("2")),
        DropInput("pink", "Classified", False, Decimal("10")),
        DropInput("red", "Covert", False, Decimal("100")),
        DropInput("gold", "Covert", True, Decimal("200")),
    ]


def test_unboxing_expected_value_and_roi() -> None:
    evaluation = evaluate_unboxing(_one_of_each(), Decimal("1"), Decimal("2.49"))
    expected = (
        Decimal("0.7992") * Decimal("1")
        + Decimal("0.1598") * Decimal("2")
        + Decimal("0.0320") * Decimal("10")
        + Decimal("0.0064") * Decimal("100")
        + Decimal("0.0026") * Decimal("200")
    )
    assert evaluation.odds_valid
    assert evaluation.expected_value == expected
    assert evaluation.cost == Decimal("3.49")
    assert evaluation.roi == (expected - Decimal("3.49")) / Decimal("3.49")
    assert sum(evaluation.probabilities.values(), Decimal(0)) == Decimal("1.0000")
    assert evaluation.probabilities["gold"] == Decimal("0.0026")


def test_special_pool_is_split_and_not_treated_as_covert() -> None:
    drops = [
        DropInput("blue", "Mil-Spec Grade", False, Decimal("1")),
        DropInput("purple", "Restricted", False, Decimal("1")),
        DropInput("pink", "Classified", False, Decimal("1")),
        DropInput("red", "Covert", False, Decimal("1")),
        DropInput("knife-a", "Covert", True, Decimal("100")),
        DropInput("knife-b", "Extraordinary", True, Decimal("300")),
    ]
    evaluation = evaluate_unboxing(drops, Decimal("1"), Decimal("2.49"))
    assert evaluation.probabilities["knife-a"] == SPECIAL_ODDS / 2
    assert evaluation.probabilities["red"] == Decimal("0.0064")


def test_missing_price_blocks_expected_value_but_keeps_odds() -> None:
    drops = _one_of_each()
    drops[0] = DropInput("blue", "Mil-Spec Grade", False, None)
    evaluation = evaluate_unboxing(drops, Decimal("1"), Decimal("2.49"))
    assert evaluation.odds_valid
    assert evaluation.expected_value is None
    assert evaluation.roi is None
    assert evaluation.missing_prices == 1
    assert evaluation.probabilities["blue"] == Decimal("0.7992")


def test_unknown_rarity_is_not_a_weapon_case() -> None:
    drops = [DropInput("sticker", "High Grade", False, Decimal("1"))]
    evaluation = evaluate_unboxing(drops, Decimal("1"), Decimal("2.49"))
    assert evaluation.odds_valid is False
    assert evaluation.expected_value is None


def test_two_skins_in_one_tier_share_its_odds() -> None:
    drops = [
        DropInput("blue-a", "Mil-Spec Grade", False, Decimal("1")),
        DropInput("blue-b", "Mil-Spec Grade", False, Decimal("3")),
        DropInput("purple", "Restricted", False, Decimal("1")),
        DropInput("pink", "Classified", False, Decimal("1")),
        DropInput("red", "Covert", False, Decimal("1")),
        DropInput("gold", "Covert", True, Decimal("1")),
    ]
    evaluation = evaluate_unboxing(drops, Decimal("1"), Decimal("2.49"))
    assert evaluation.probabilities["blue-a"] == Decimal("0.7992") / 2
    assert evaluation.expected_value == (
        (Decimal("0.7992") / 2) * Decimal("1")
        + (Decimal("0.7992") / 2) * Decimal("3")
        + Decimal("0.1598")
        + Decimal("0.0320")
        + Decimal("0.0064")
        + Decimal("0.0026")
    )


def test_doppler_phases_weigh_the_special_pool() -> None:
    drops = [
        DropInput("blue", "Mil-Spec Grade", False, Decimal("1")),
        DropInput("purple", "Restricted", False, Decimal("1")),
        DropInput("pink", "Classified", False, Decimal("1")),
        DropInput("red", "Covert", False, Decimal("1")),
        DropInput("★ Karambit | Doppler", "Covert", True, Decimal("700"), weight=7),
        DropInput("★ Karambit | Rust Coat", "Covert", True, Decimal("300")),
    ]
    evaluation = evaluate_unboxing(drops, Decimal("1"), Decimal("2.49"))
    assert evaluation.probabilities["★ Karambit | Doppler"] == SPECIAL_ODDS * 7 / 8
    assert evaluation.probabilities["★ Karambit | Rust Coat"] == SPECIAL_ODDS / 8
    assert sum(evaluation.probabilities.values(), Decimal(0)) == Decimal("1.0000")


def test_wear_order_keeps_field_tested_first_for_full_range_skins() -> None:
    assert wear_order(0.0, 1.0)[0] == "Field-Tested"
    assert wear_order(None, None) == WEAR_PREFERENCE


def test_doppler_without_field_tested_is_priced_as_factory_new() -> None:
    wears = wear_order(0.0, 0.08)
    assert wears[:3] == ("Field-Tested", "Factory New", "Minimal Wear")
    amount, name = resolve_wear_price(
        "★ Talon Knife | Doppler",
        {
            "★ Talon Knife | Doppler (Minimal Wear)": Decimal("3389.33"),
            "★ Talon Knife | Doppler (Factory New)": Decimal("2745.84"),
        },
        wears,
    )
    assert name == "★ Talon Knife | Doppler (Factory New)"
    assert amount == Decimal("2745.84")


def test_high_float_skin_falls_back_to_battle_scarred() -> None:
    assert wear_order(0.4, 1.0)[1] == "Battle-Scarred"
