from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_case_query_service
from app.api.v1.mappers import to_detail, to_history, to_sort_field, to_summary
from app.domain.constants import WEAPON_CASE_TYPE
from app.schemas.case import CaseDetailOut, CaseHistoryOut, CaseSort, CaseSummaryOut, SortOrder
from app.services.case_query import CaseQueryService

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("", response_model=list[CaseSummaryOut])
async def list_cases(
    crate_type: str = Query(default=WEAPON_CASE_TYPE),
    sort: CaseSort = Query(default=CaseSort.name),
    order: SortOrder = Query(default=SortOrder.asc),
    service: CaseQueryService = Depends(get_case_query_service),
) -> list[CaseSummaryOut]:
    views = await service.list_cases(
        crate_type,
        sort=to_sort_field(sort),
        descending=order is SortOrder.desc,
    )
    return [to_summary(view) for view in views]


@router.get("/{case_id}", response_model=CaseDetailOut)
async def get_case(
    case_id: int,
    service: CaseQueryService = Depends(get_case_query_service),
) -> CaseDetailOut:
    view = await service.get_case(case_id)
    if view is None:
        raise HTTPException(status_code=404, detail="кейс не найден")
    return to_detail(view)


@router.get("/{case_id}/history", response_model=CaseHistoryOut)
async def get_case_history(
    case_id: int,
    days: int = Query(default=90, ge=1, le=3650),
    service: CaseQueryService = Depends(get_case_query_service),
) -> CaseHistoryOut:
    view = await service.get_history(case_id, days)
    if view is None:
        raise HTTPException(status_code=404, detail="кейс не найден")
    return to_history(view)
