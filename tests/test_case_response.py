from decimal import Decimal

from app.api.v1.cases import to_detail, to_summary
from app.schemas.case import ASSUMPTIONS
from app.services.case_query import CaseView, DropView


def _view() -> CaseView:
    return CaseView(
        id=1,
        name="Kilowatt Case",
        image_url=None,
        market_hash_name="Kilowatt Case",
        crate_type="Case",
        case_price=Decimal("0.15"),
        key_price=Decimal("2.49"),
        expected_value=Decimal("0.71"),
        unboxing_roi=Decimal("-0.73247352"),
        roi_7d=Decimal("0.1"),
        roi_30d=None,
        roi_90d=None,
        odds_valid=True,
        missing_prices=0,
        drops=(
            DropView(
                name="★ Kukri Knife | Fade",
                rarity="Covert",
                is_special=True,
                probability=Decimal("0.0002"),
                price=Decimal("100.5"),
                market_hash_name="★ Kukri Knife | Fade (Factory New)",
                image_url=None,
            ),
        ),
    )


def test_summary_hides_drops_and_keeps_assumptions() -> None:
    summary = to_summary(_view())
    assert summary.case_price == 0.15
    assert summary.unboxing_roi == -0.73247352
    assert summary.roi_30d is None
    assert summary.assumptions == ASSUMPTIONS
    assert "drops" not in summary.model_dump()


def test_detail_includes_resolved_wear() -> None:
    detail = to_detail(_view())
    assert detail.drops[0].market_hash_name == "★ Kukri Knife | Fade (Factory New)"
    assert detail.drops[0].price == 100.5
