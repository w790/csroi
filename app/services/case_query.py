from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from app.core.config import settings
from app.domain.constants import (
    SOURCE_SKINPORT,
    WEAPON_CASE_TYPE,
    WINDOW_24H,
    WINDOW_30D,
    WINDOW_7D,
    WINDOW_90D,
)
from app.domain.names import price_candidates, wear_order
from app.domain.pricing import choose_listing_price, investing_roi, resolve_wear_price
from app.domain.roi import DropInput, UnboxingEvaluation, evaluate_unboxing
from app.models.case import Case, CaseDrop
from app.models.price import Price, PriceWindow
from app.repositories.catalog import CatalogRepository
from app.repositories.prices import PriceRepository

@dataclass(frozen=True)
class DropView:
    name: str
    rarity: str | None
    is_special: bool
    probability: Decimal | None
    price: Decimal | None
    market_hash_name: str
    image_url: str | None


@dataclass(frozen=True)
class CaseView:
    id: int
    name: str
    image_url: str | None
    market_hash_name: str
    crate_type: str | None
    case_price: Decimal | None
    key_price: Decimal
    expected_value: Decimal | None
    unboxing_roi: Decimal | None
    roi_7d: Decimal | None
    roi_30d: Decimal | None
    roi_90d: Decimal | None
    odds_valid: bool
    missing_prices: int
    prices_updated_at: datetime | None
    drops: tuple[DropView, ...]


@dataclass(frozen=True)
class PricePointView:
    captured_on: date
    price: Decimal


@dataclass(frozen=True)
class CaseHistoryView:
    id: int
    name: str
    market_hash_name: str
    currency: str
    points: tuple[PricePointView, ...]


_RARITY_ORDER = {
    "Mil-Spec Grade": 0,
    "Restricted": 1,
    "Classified": 2,
    "Covert": 3,
}


class CaseQueryService:
    def __init__(self, catalog: CatalogRepository, prices: PriceRepository) -> None:
        self._catalog = catalog
        self._prices = prices

    async def list_cases(
        self,
        crate_type: str = WEAPON_CASE_TYPE,
        sort: str = "name",
        descending: bool = False,
    ) -> list[CaseView]:
        cases = await self._catalog.list_cases(crate_type)
        views = await self._compose(cases, include_drops=False)
        return sort_views(views, sort, descending=descending)

    async def get_case(self, case_id: int) -> CaseView | None:
        case = await self._catalog.get_case(case_id)
        if case is None:
            return None
        details = await self._compose([case], include_drops=True)
        return details[0]

    async def get_history(self, case_id: int, days: int) -> CaseHistoryView | None:
        case = await self._catalog.get_case(case_id)
        if case is None:
            return None
        currency = settings.skinport_currency
        since = datetime.now(timezone.utc).date() - timedelta(days=days - 1)
        snapshots = await self._prices.snapshots_for(
            case.market_hash_name,
            SOURCE_SKINPORT,
            currency,
            since,
        )
        return CaseHistoryView(
            id=case.id,
            name=case.name,
            market_hash_name=case.market_hash_name,
            currency=currency,
            points=tuple(
                PricePointView(captured_on=row.captured_on, price=row.price)
                for row in snapshots
            ),
        )

    async def _compose(self, cases: list[Case], *, include_drops: bool) -> list[CaseView]:
        if not cases:
            return []
        case_ids = [case.id for case in cases]
        drops = await self._catalog.drops_for(case_ids)
        drops_by_case: dict[int, list[CaseDrop]] = {case_id: [] for case_id in case_ids}
        names: set[str] = set()
        for case in cases:
            names.add(case.market_hash_name)
        for drop in drops:
            drops_by_case[drop.case_id].append(drop)
            names.update(price_candidates(drop.name))

        currency = settings.skinport_currency
        listings = await self._prices.listings_for(list(names), SOURCE_SKINPORT, currency)
        windows = await self._prices.windows_for(
            [case.market_hash_name for case in cases],
            SOURCE_SKINPORT,
            currency,
        )
        floats = await self._catalog.float_ranges(sorted({drop.name for drop in drops}))
        return [
            _to_detail(
                case,
                drops_by_case.get(case.id, []),
                listings,
                windows,
                floats,
                include_drops=include_drops,
            )
            for case in cases
        ]


def _to_detail(
    case: Case,
    drops: list[CaseDrop],
    listings: dict[str, Price],
    windows: dict[tuple[str, str], PriceWindow],
    floats: dict[str, tuple[float | None, float | None]],
    *,
    include_drops: bool,
) -> CaseView:
    ordered = sorted(drops, key=_drop_sort)
    amounts = {
        name: choose_listing_price(row.suggested_price, row.median_price, row.min_price)
        for name, row in listings.items()
    }
    case_price = amounts.get(case.market_hash_name)
    resolved = [
        resolve_wear_price(
            drop.name,
            amounts,
            wear_order(*floats.get(drop.name, (None, None))),
        )
        for drop in ordered
    ]
    inputs = [
        DropInput(
            name=drop.name,
            rarity=drop.rarity,
            is_special=drop.is_special,
            price=amount,
            weight=drop.weight,
        )
        for drop, (amount, _) in zip(ordered, resolved, strict=True)
    ]
    if case.crate_type == WEAPON_CASE_TYPE:
        evaluation = evaluate_unboxing(inputs, case_price, settings.key_price_usd)
    else:
        evaluation = UnboxingEvaluation(
            expected_value=None,
            cost=None,
            roi=None,
            missing_prices=0,
            odds_valid=False,
            probabilities={},
        )

    current = _current_price(case.market_hash_name, windows, case_price)
    case_listing = listings.get(case.market_hash_name)
    drop_views: tuple[DropView, ...] = ()
    if include_drops:
        drop_views = tuple(
            DropView(
                name=drop.name,
                rarity=drop.rarity,
                is_special=drop.is_special,
                probability=evaluation.probabilities.get(drop.name),
                price=amount,
                market_hash_name=priced_as,
                image_url=drop.image_url,
            )
            for drop, (amount, priced_as) in zip(ordered, resolved, strict=True)
        )

    return CaseView(
        id=case.id,
        name=case.name,
        image_url=case.image_url,
        market_hash_name=case.market_hash_name,
        crate_type=case.crate_type,
        case_price=case_price,
        key_price=settings.key_price_usd,
        expected_value=evaluation.expected_value,
        unboxing_roi=evaluation.roi,
        roi_7d=_window_roi(case.market_hash_name, WINDOW_7D, windows, current),
        roi_30d=_window_roi(case.market_hash_name, WINDOW_30D, windows, current),
        roi_90d=_window_roi(case.market_hash_name, WINDOW_90D, windows, current),
        odds_valid=evaluation.odds_valid,
        missing_prices=evaluation.missing_prices,
        prices_updated_at=case_listing.updated_at if case_listing is not None else None,
        drops=drop_views,
    )


def sort_views(views: list[CaseView], field: str, *, descending: bool) -> list[CaseView]:
    present = [view for view in views if getattr(view, field) is not None]
    missing = [view for view in views if getattr(view, field) is None]
    present.sort(key=lambda view: getattr(view, field), reverse=descending)
    return present + missing


def _current_price(
    market_hash_name: str,
    windows: dict[tuple[str, str], PriceWindow],
    case_price: Decimal | None,
) -> Decimal | None:
    recent = windows.get((market_hash_name, WINDOW_24H))
    if recent is not None and recent.median_price is not None:
        return recent.median_price
    return case_price


def _window_roi(
    market_hash_name: str,
    window: str,
    windows: dict[tuple[str, str], PriceWindow],
    current: Decimal | None,
) -> Decimal | None:
    row = windows.get((market_hash_name, window))
    baseline = row.median_price if row is not None else None
    return investing_roi(current, baseline)


def _drop_sort(drop: CaseDrop) -> tuple[int, int, str]:
    if drop.is_special:
        return (1, 0, drop.name)
    return (0, _RARITY_ORDER.get(drop.rarity or "", 9), drop.name)
