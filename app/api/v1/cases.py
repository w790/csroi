from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.domain.constants import WEAPON_CASE_TYPE
from app.repositories.catalog import CatalogRepository
from app.repositories.prices import PriceRepository
from app.schemas.case import (
    ASSUMPTIONS,
    CaseDetail,
    CaseDropOut,
    CaseHistory,
    CaseSort,
    CaseSummary,
    PricePointOut,
    SortOrder,
)
from app.services.case_query import CaseHistoryView, CaseQueryService, CaseView, DropView

router = APIRouter(prefix="/cases", tags=["cases"])


def _service(session: AsyncSession) -> CaseQueryService:
    return CaseQueryService(CatalogRepository(session), PriceRepository(session))


@router.get("", response_model=list[CaseSummary])
async def list_cases(
    crate_type: str = Query(default=WEAPON_CASE_TYPE),
    sort: CaseSort = Query(default=CaseSort.name),
    order: SortOrder = Query(default=SortOrder.asc),
    session: AsyncSession = Depends(get_session),
) -> list[CaseSummary]:
    views = await _service(session).list_cases(
        crate_type,
        sort=sort.value,
        descending=order is SortOrder.desc,
    )
    return [to_summary(view) for view in views]


@router.get("/{case_id}", response_model=CaseDetail)
async def get_case(
    case_id: int,
    session: AsyncSession = Depends(get_session),
) -> CaseDetail:
    view = await _service(session).get_case(case_id)
    if view is None:
        raise HTTPException(status_code=404, detail="кейс не найден")
    return to_detail(view)


@router.get("/{case_id}/history", response_model=CaseHistory)
async def get_case_history(
    case_id: int,
    days: int = Query(default=90, ge=1, le=3650),
    session: AsyncSession = Depends(get_session),
) -> CaseHistory:
    view = await _service(session).get_history(case_id, days)
    if view is None:
        raise HTTPException(status_code=404, detail="кейс не найден")
    return to_history(view)


def to_summary(view: CaseView) -> CaseSummary:
    return CaseSummary(
        id=view.id,
        name=view.name,
        image_url=view.image_url,
        market_hash_name=view.market_hash_name,
        crate_type=view.crate_type,
        case_price=_money(view.case_price),
        key_price=_money(view.key_price) or 0,
        expected_value=_money(view.expected_value),
        unboxing_roi=_ratio(view.unboxing_roi),
        roi_7d=_ratio(view.roi_7d),
        roi_30d=_ratio(view.roi_30d),
        roi_90d=_ratio(view.roi_90d),
        odds_valid=view.odds_valid,
        missing_prices=view.missing_prices,
        prices_updated_at=view.prices_updated_at,
        assumptions=ASSUMPTIONS,
    )


def to_detail(view: CaseView) -> CaseDetail:
    summary = to_summary(view)
    return CaseDetail(
        **summary.model_dump(),
        drops=[_drop(item) for item in view.drops],
    )


def to_history(view: CaseHistoryView) -> CaseHistory:
    return CaseHistory(
        id=view.id,
        name=view.name,
        market_hash_name=view.market_hash_name,
        currency=view.currency,
        points=[
            PricePointOut(captured_on=point.captured_on, price=_money(point.price))
            for point in view.points
        ],
    )


def _drop(item: DropView) -> CaseDropOut:
    return CaseDropOut(
        name=item.name,
        rarity=item.rarity,
        is_special=item.is_special,
        probability=_ratio(item.probability),
        price=_money(item.price),
        market_hash_name=item.market_hash_name,
        image_url=item.image_url,
    )


def _money(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value.quantize(Decimal("0.01")))


def _ratio(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value.quantize(Decimal("0.00000001")))
