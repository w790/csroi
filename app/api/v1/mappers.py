from decimal import Decimal

from app.domain.assumptions import assumptions_text
from app.schemas.case import (
    CaseDetailOut,
    CaseDropOut,
    CaseHistoryOut,
    CaseSort,
    CaseSummaryOut,
    PricePointOut,
)
from app.services.case_query import CaseHistoryView, CaseView, DropView, SortField

_SORT_FIELDS = {
    CaseSort.name: SortField.name,
    CaseSort.case_price: SortField.case_price,
    CaseSort.expected_value: SortField.expected_value,
    CaseSort.unboxing_roi: SortField.unboxing_roi,
    CaseSort.roi_7d: SortField.roi_7d,
    CaseSort.roi_30d: SortField.roi_30d,
    CaseSort.roi_90d: SortField.roi_90d,
}


def to_sort_field(sort: CaseSort) -> SortField:
    return _SORT_FIELDS[sort]


def to_summary(view: CaseView) -> CaseSummaryOut:
    return CaseSummaryOut(
        id=view.id,
        name=view.name,
        image_url=view.image_url,
        market_hash_name=view.market_hash_name,
        crate_type=view.crate_type,
        case_price=_optional_money(view.case_price),
        key_price=_money(view.key_price),
        expected_value=_optional_money(view.expected_value),
        unboxing_roi=_optional_ratio(view.unboxing_roi),
        roi_7d=_optional_ratio(view.roi_7d),
        roi_30d=_optional_ratio(view.roi_30d),
        roi_90d=_optional_ratio(view.roi_90d),
        odds_valid=view.odds_valid,
        missing_prices=view.missing_prices,
        prices_updated_at=view.prices_updated_at,
        assumptions=assumptions_text(view.key_price),
    )


def to_detail(view: CaseView) -> CaseDetailOut:
    summary = to_summary(view)
    drops = [_to_drop_out(item) for item in view.drops]
    return CaseDetailOut(**summary.model_dump(), drops=drops)


def to_history(view: CaseHistoryView) -> CaseHistoryOut:
    points = [
        PricePointOut(captured_on=point.captured_on, price=_money(point.price))
        for point in view.points
    ]
    return CaseHistoryOut(
        id=view.id,
        name=view.name,
        market_hash_name=view.market_hash_name,
        currency=view.currency,
        points=points,
    )


def _to_drop_out(item: DropView) -> CaseDropOut:
    return CaseDropOut(
        name=item.name,
        rarity=item.rarity,
        is_special=item.is_special,
        probability=_optional_ratio(item.probability),
        price=_optional_money(item.price),
        market_hash_name=item.market_hash_name,
        image_url=item.image_url,
    )


def _optional_money(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return _money(value)


def _money(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01")))


def _optional_ratio(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value.quantize(Decimal("0.00000001")))
