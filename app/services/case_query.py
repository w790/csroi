from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from enum import StrEnum

from app.domain.constants import (
    SOURCE_SKINPORT,
    WEAPON_CASE_TYPE,
    WINDOW_7D,
    WINDOW_24H,
    WINDOW_30D,
    WINDOW_90D,
)
from app.domain.names import price_candidates
from app.domain.pricing import (
    choose_item_price,
    choose_listing_price,
    investing_roi,
    resolve_wear_price,
)
from app.domain.roi import DropInput, UnboxingEvaluation, evaluate_unboxing, not_evaluated
from app.domain.wear import wear_order
from app.models.case import Case, CaseDrop
from app.models.price import Price, PriceWindow
from app.repositories.catalog import CatalogRepository
from app.repositories.prices import PriceRepository


class SortField(StrEnum):
    name = "name"
    case_price = "case_price"
    expected_value = "expected_value"
    unboxing_roi = "unboxing_roi"
    roi_7d = "roi_7d"
    roi_30d = "roi_30d"
    roi_90d = "roi_90d"


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


_SORT_KEYS: dict[SortField, Callable[[CaseView], str | Decimal | None]] = {
    SortField.name: lambda view: view.name.casefold(),
    SortField.case_price: lambda view: view.case_price,
    SortField.expected_value: lambda view: view.expected_value,
    SortField.unboxing_roi: lambda view: view.unboxing_roi,
    SortField.roi_7d: lambda view: view.roi_7d,
    SortField.roi_30d: lambda view: view.roi_30d,
    SortField.roi_90d: lambda view: view.roi_90d,
}


class CaseQueryService:
    def __init__(
        self,
        catalog: CatalogRepository,
        prices: PriceRepository,
        *,
        currency: str,
        key_price: Decimal,
    ) -> None:
        self._catalog = catalog
        self._prices = prices
        self._currency = currency
        self._key_price = key_price

    async def list_cases(
        self,
        crate_type: str = WEAPON_CASE_TYPE,
        sort: SortField = SortField.name,
        descending: bool = False,
    ) -> list[CaseView]:
        cases = await self._catalog.list_cases(crate_type)
        views = await self._build_views(cases, include_drops=False)
        return sort_views(views, sort, descending=descending)

    async def get_case(self, case_id: int) -> CaseView | None:
        case = await self._catalog.get_case(case_id)
        if case is None:
            return None
        views = await self._build_views([case], include_drops=True)
        return views[0]

    async def get_history(self, case_id: int, days: int) -> CaseHistoryView | None:
        case = await self._catalog.get_case(case_id)
        if case is None:
            return None
        since = datetime.now(UTC).date() - timedelta(days=days - 1)
        snapshots = await self._prices.snapshots_for(
            case.market_hash_name,
            SOURCE_SKINPORT,
            self._currency,
            since,
        )
        points = tuple(
            PricePointView(captured_on=row.captured_on, price=row.price) for row in snapshots
        )
        return CaseHistoryView(
            id=case.id,
            name=case.name,
            market_hash_name=case.market_hash_name,
            currency=self._currency,
            points=points,
        )

    async def _build_views(self, cases: list[Case], *, include_drops: bool) -> list[CaseView]:
        if not cases:
            return []
        market = await self._load_market(cases)
        return [self._build_view(case, market, include_drops=include_drops) for case in cases]

    async def _load_market(self, cases: list[Case]) -> "_Market":
        drops = await self._catalog.drops_for([case.id for case in cases])
        names = _price_names(cases, drops)
        listings = await self._prices.listings_for(names, SOURCE_SKINPORT, self._currency)
        windows = await self._prices.windows_for(names, SOURCE_SKINPORT, self._currency)
        floats = await self._catalog.float_ranges(sorted({drop.name for drop in drops}))
        return _Market(
            drops_by_case=_group_drops(cases, drops),
            listings=listings,
            windows=windows,
            floats=floats,
        )

    def _build_view(self, case: Case, market: "_Market", *, include_drops: bool) -> CaseView:
        ordered = sorted(market.drops_by_case[case.id], key=_drop_sort_key)
        priced = [_price_drop(drop, market) for drop in ordered]
        case_price = market.listing_price(case.market_hash_name)
        evaluation = self._evaluate(case, priced, case_price)
        current = market.investing_current_price(case.market_hash_name)
        return CaseView(
            id=case.id,
            name=case.name,
            image_url=case.image_url,
            market_hash_name=case.market_hash_name,
            crate_type=case.crate_type,
            case_price=case_price,
            key_price=self._key_price,
            expected_value=evaluation.expected_value,
            unboxing_roi=evaluation.roi,
            roi_7d=investing_roi(current, market.sale_median(case.market_hash_name, WINDOW_7D)),
            roi_30d=investing_roi(current, market.sale_median(case.market_hash_name, WINDOW_30D)),
            roi_90d=investing_roi(current, market.sale_median(case.market_hash_name, WINDOW_90D)),
            odds_valid=evaluation.odds_valid,
            missing_prices=evaluation.missing_prices,
            prices_updated_at=market.listing_updated_at(case.market_hash_name),
            drops=_drop_views(priced, evaluation) if include_drops else (),
        )

    def _evaluate(
        self,
        case: Case,
        priced: list["_PricedDrop"],
        case_price: Decimal | None,
    ) -> UnboxingEvaluation:
        if case.crate_type != WEAPON_CASE_TYPE:
            return not_evaluated()
        inputs = [_drop_input(item) for item in priced]
        return evaluate_unboxing(inputs, case_price, self._key_price)


def sort_views(views: list[CaseView], field: SortField, *, descending: bool) -> list[CaseView]:
    key = _SORT_KEYS[field]
    keyed = [(key(view), view) for view in views]
    present: list[tuple[str | Decimal, CaseView]] = [
        (value, view) for value, view in keyed if value is not None
    ]
    missing = [view for value, view in keyed if value is None]
    present.sort(key=lambda pair: pair[0], reverse=descending)
    return [view for _, view in present] + missing


@dataclass(frozen=True)
class _Market:
    drops_by_case: dict[int, list[CaseDrop]]
    listings: dict[str, Price]
    windows: dict[tuple[str, str], PriceWindow]
    floats: dict[str, tuple[float | None, float | None]]

    def listing_price(self, name: str) -> Decimal | None:
        row = self.listings.get(name)
        if row is None:
            return None
        return choose_listing_price(row.suggested_price, row.median_price, row.min_price)

    def item_price(self, name: str) -> Decimal | None:
        return choose_item_price(
            self.sale_median(name, WINDOW_30D),
            self.sale_median(name, WINDOW_90D),
            self.listing_price(name),
        )

    def sale_median(self, name: str, window: str) -> Decimal | None:
        row = self.windows.get((name, window))
        if row is None:
            return None
        return row.median_price

    def investing_current_price(self, name: str) -> Decimal | None:
        recent = self.sale_median(name, WINDOW_24H)
        if recent is not None:
            return recent
        return self.listing_price(name)

    def listing_updated_at(self, name: str) -> datetime | None:
        row = self.listings.get(name)
        if row is None:
            return None
        return row.updated_at

    def wears_for(self, drop_name: str) -> tuple[str, ...]:
        low, high = self.floats.get(drop_name, (None, None))
        return wear_order(low, high)


@dataclass(frozen=True)
class _PricedDrop:
    drop: CaseDrop
    price: Decimal | None
    priced_as: str


def _price_names(cases: list[Case], drops: list[CaseDrop]) -> list[str]:
    names = {case.market_hash_name for case in cases}
    for drop in drops:
        names.update(price_candidates(drop.name))
    return list(names)


def _group_drops(cases: list[Case], drops: list[CaseDrop]) -> dict[int, list[CaseDrop]]:
    grouped: dict[int, list[CaseDrop]] = {case.id: [] for case in cases}
    for drop in drops:
        grouped[drop.case_id].append(drop)
    return grouped


def _drop_sort_key(drop: CaseDrop) -> tuple[int, int, str]:
    if drop.is_special:
        return (1, 0, drop.name)
    return (0, _RARITY_ORDER.get(drop.rarity or "", 9), drop.name)


def _price_drop(drop: CaseDrop, market: _Market) -> _PricedDrop:
    wears = market.wears_for(drop.name)
    candidates = price_candidates(drop.name, wears)
    prices = {name: market.item_price(name) for name in candidates}
    price, priced_as = resolve_wear_price(drop.name, prices, wears)
    return _PricedDrop(drop=drop, price=price, priced_as=priced_as)


def _drop_input(item: _PricedDrop) -> DropInput:
    return DropInput(
        name=item.drop.name,
        rarity=item.drop.rarity,
        is_special=item.drop.is_special,
        price=item.price,
        weight=item.drop.weight,
    )


def _drop_views(
    priced: list[_PricedDrop],
    evaluation: UnboxingEvaluation,
) -> tuple[DropView, ...]:
    return tuple(_drop_view(item, evaluation) for item in priced)


def _drop_view(item: _PricedDrop, evaluation: UnboxingEvaluation) -> DropView:
    return DropView(
        name=item.drop.name,
        rarity=item.drop.rarity,
        is_special=item.drop.is_special,
        probability=evaluation.probabilities.get(item.drop.name),
        price=item.price,
        market_hash_name=item.priced_as,
        image_url=item.drop.image_url,
    )
