import asyncio
from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import cast

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_session
from app.domain.odds import SPECIAL_ODDS
from app.main import app
from app.models.case import Case, CaseDrop
from app.models.price import Price, PriceSnapshot, PriceWindow
from app.repositories.catalog import CatalogRepository
from app.repositories.prices import PriceRepository
from app.services.case_query import CaseQueryService, CaseView, sort_views

UPDATED_AT = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)

_view = CaseView(
    id=1,
    name="",
    image_url=None,
    market_hash_name="",
    crate_type="Case",
    case_price=None,
    key_price=Decimal("2.49"),
    expected_value=None,
    unboxing_roi=None,
    roi_7d=None,
    roi_30d=None,
    roi_90d=None,
    odds_valid=False,
    missing_prices=0,
    prices_updated_at=None,
    drops=(),
)

TIERS = (
    ("blue", "Mil-Spec Grade"),
    ("purple", "Restricted"),
    ("pink", "Classified"),
    ("red", "Covert"),
)


def _weapon_case(case_id: int, name: str) -> tuple[Case, list[CaseDrop]]:
    case = Case(
        id=case_id,
        bymykel_id=f"crate-{case_id}",
        name=name,
        market_hash_name=name,
        crate_type="Case",
        image_url=None,
    )
    drops = [
        CaseDrop(
            case_id=case_id,
            name=f"{name} {color}",
            rarity=rarity,
            is_special=False,
            weight=1,
            image_url=None,
        )
        for color, rarity in TIERS
    ]
    drops += [
        CaseDrop(
            case_id=case_id,
            name=f"★ {name} | Doppler",
            rarity="Covert",
            is_special=True,
            weight=7,
            image_url=None,
        ),
        CaseDrop(
            case_id=case_id,
            name=f"★ {name} | Rust Coat",
            rarity="Covert",
            is_special=True,
            weight=1,
            image_url=None,
        ),
    ]
    return case, drops


def _price(name: str, amount: str) -> Price:
    return Price(
        market_hash_name=name,
        suggested_price=Decimal(amount),
        median_price=None,
        min_price=None,
        updated_at=UPDATED_AT,
    )


class _Catalog:
    def __init__(self, cases: list[Case], drops: list[CaseDrop]) -> None:
        self._cases = cases
        self._drops = drops

    async def list_cases(self, crate_type: str | None) -> list[Case]:
        return [case for case in self._cases if case.crate_type == crate_type]

    async def get_case(self, case_id: int) -> Case | None:
        return next((case for case in self._cases if case.id == case_id), None)

    async def drops_for(self, case_ids: list[int]) -> list[CaseDrop]:
        return [drop for drop in self._drops if drop.case_id in case_ids]

    async def float_ranges(self, names: list[str]) -> dict[str, tuple[float | None, float | None]]:
        return {name: (0.0, 0.08) for name in names if name.endswith("| Doppler")}


class _Prices:
    def __init__(
        self,
        listings: list[Price],
        snapshots: list[PriceSnapshot],
        windows: list[PriceWindow],
    ) -> None:
        self._listings = {row.market_hash_name: row for row in listings}
        self._windows = {(row.market_hash_name, row.window): row for row in windows}
        self._snapshots = list(snapshots)
        self.since: date | None = None

    async def listings_for(
        self, names: list[str], _source: str, _currency: str
    ) -> dict[str, Price]:
        return {name: row for name, row in self._listings.items() if name in names}

    async def windows_for(
        self, names: list[str], _source: str, _currency: str
    ) -> dict[tuple[str, str], PriceWindow]:
        return {key: row for key, row in self._windows.items() if key[0] in names}

    async def snapshots_for(
        self, _name: str, _source: str, _currency: str, since: date
    ) -> list[PriceSnapshot]:
        self.since = since
        return self._snapshots


def _window(name: str, window: str, median: str | None) -> PriceWindow:
    return PriceWindow(
        market_hash_name=name,
        window=window,
        median_price=Decimal(median) if median is not None else None,
    )


def _service(windows: tuple[PriceWindow, ...] = ()) -> CaseQueryService:
    cheap, cheap_drops = _weapon_case(1, "Cheap")
    rich, rich_drops = _weapon_case(2, "Rich")
    unpriced, unpriced_drops = _weapon_case(3, "Unpriced")
    listings = [_price("Cheap", "0.50"), _price("Rich", "1.00")]
    for drops, special in ((cheap_drops, "10"), (rich_drops, "1000")):
        for drop in drops:
            if drop.name != "★ Rich | Doppler":
                listings.append(_price(drop.name, special if drop.is_special else "0.10"))
    listings += [
        _price("★ Rich | Doppler (Minimal Wear)", "5000"),
        _price("★ Rich | Doppler (Factory New)", "1000"),
    ]
    snapshots = [
        PriceSnapshot(
            market_hash_name="Rich", price=Decimal("0.90"), captured_on=date(2026, 9, 30)
        ),
        PriceSnapshot(
            market_hash_name="Rich", price=Decimal("1.00"), captured_on=date(2026, 10, 1)
        ),
    ]
    return CaseQueryService(
        cast(
            CatalogRepository,
            _Catalog([cheap, rich, unpriced], cheap_drops + rich_drops + unpriced_drops),
        ),
        cast(PriceRepository, _Prices(listings, snapshots, list(windows))),
    )


def test_list_sorts_by_roi_and_keeps_unpriced_last() -> None:
    service = _service()

    descending = asyncio.run(service.list_cases(sort="unboxing_roi", descending=True))
    ascending = asyncio.run(service.list_cases(sort="unboxing_roi", descending=False))

    assert [view.name for view in descending] == ["Rich", "Cheap", "Unpriced"]
    assert [view.name for view in ascending] == ["Cheap", "Rich", "Unpriced"]
    assert descending[-1].unboxing_roi is None
    assert descending[0].prices_updated_at == UPDATED_AT
    assert descending[-1].prices_updated_at is None


def test_name_sort_ignores_case() -> None:
    views = [replace(_view, name=name) for name in ("eSports", "Winter", "Chroma")]
    assert [view.name for view in sort_views(views, "name", descending=False)] == [
        "Chroma",
        "eSports",
        "Winter",
    ]


def test_detail_gives_doppler_its_phase_share() -> None:
    view = asyncio.run(_service().get_case(2))
    assert view is not None

    drops = {drop.name: drop for drop in view.drops}
    assert drops["★ Rich | Doppler"].probability == SPECIAL_ODDS * 7 / 8
    assert drops["★ Rich | Rust Coat"].probability == SPECIAL_ODDS / 8
    assert drops["★ Rich | Doppler"].market_hash_name == "★ Rich | Doppler (Factory New)"
    assert (
        view.expected_value == Decimal("0.10") * (1 - SPECIAL_ODDS) + Decimal("1000") * SPECIAL_ODDS
    )


def test_item_price_uses_sales_median_before_listing() -> None:
    service = _service(
        (
            _window("★ Rich | Doppler (Factory New)", "30d", "200"),
            _window("★ Rich | Doppler (Factory New)", "90d", "300"),
            _window("★ Rich | Rust Coat", "30d", None),
            _window("★ Rich | Rust Coat", "90d", "400"),
            _window("Rich", "30d", "0.70"),
        )
    )

    view = asyncio.run(service.get_case(2))
    assert view is not None

    prices = {drop.name: drop.price for drop in view.drops}
    assert prices["★ Rich | Doppler"] == Decimal("200")
    assert prices["★ Rich | Rust Coat"] == Decimal("400")
    assert prices["Rich blue"] == Decimal("0.10")
    assert view.case_price == Decimal("1.00")


def test_item_without_listing_is_priced_by_past_sales() -> None:
    service = _service((_window("Unpriced blue", "30d", "0.20"),))

    view = asyncio.run(service.get_case(3))
    assert view is not None

    prices = {drop.name: drop.price for drop in view.drops}
    assert prices["Unpriced blue"] == Decimal("0.20")
    assert view.missing_prices == 5


def test_history_returns_snapshots_for_the_window() -> None:
    service = _service()

    history = asyncio.run(service.get_history(2, days=30))
    assert history is not None

    assert history.market_hash_name == "Rich"
    assert [point.price for point in history.points] == [Decimal("0.90"), Decimal("1.00")]
    since = cast(_Prices, service._prices).since
    assert since is not None
    assert (datetime.now(UTC).date() - since).days == 29
    assert asyncio.run(service.get_history(404, days=30)) is None


async def _no_session() -> AsyncIterator[None]:
    yield None


def test_cases_endpoint_validates_sort_and_history_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.api.v1.cases._service", lambda _session: _service())
    app.dependency_overrides[get_session] = _no_session
    try:
        client = TestClient(app)

        listed = client.get("/api/v1/cases", params={"sort": "unboxing_roi", "order": "desc"})
        assert listed.status_code == 200
        assert [row["name"] for row in listed.json()] == ["Rich", "Cheap", "Unpriced"]
        assert client.get("/api/v1/cases", params={"sort": "bogus"}).status_code == 422

        history = client.get("/api/v1/cases/2/history", params={"days": 7})
        assert history.status_code == 200
        assert history.json()["points"] == [
            {"captured_on": "2026-09-30", "price": 0.9},
            {"captured_on": "2026-10-01", "price": 1.0},
        ]
        assert client.get("/api/v1/cases/2/history", params={"days": 0}).status_code == 422
        assert client.get("/api/v1/cases/404/history").status_code == 404
    finally:
        app.dependency_overrides.clear()
