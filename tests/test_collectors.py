import asyncio
from collections.abc import Awaitable, Callable
from decimal import Decimal

import httpx
import pytest

from app.collectors.sources import BymykelClient, CollectorError, SkinportClient

BASE = "https://bymykel.test/api/en"


def _rarity(name: str) -> dict[str, str]:
    return {"id": name.lower(), "name": name, "color": "#eb4b4b"}


def _crates_payload() -> list[object]:
    doppler = [
        {
            "id": f"skin-doppler-{phase}",
            "name": "★ Karambit | Doppler",
            "rarity": _rarity("Covert"),
            "phase": phase,
        }
        for phase in ("Phase 1", "Phase 2", "Ruby")
    ]
    return [
        {
            "id": "crate-1",
            "name": "Chroma Case",
            "type": "Case",
            "def_index": "4061",
            "market_hash_name": "Chroma Case",
            "contains": [
                {"id": "skin-1", "name": "AK-47 | Cartel", "rarity": _rarity("Classified")},
                {"id": "skin-2", "name": ""},
            ],
            "contains_rare": doppler
            + [{"id": "skin-3", "name": "★ Karambit | Rust Coat", "rarity": _rarity("Covert")}],
        },
        "not a crate",
    ]


def _run[T](
    handler: Callable[[httpx.Request], httpx.Response],
    call: Callable[[httpx.AsyncClient], Awaitable[T]],
) -> T:
    async def main() -> T:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await call(client)

    return asyncio.run(main())


def test_crate_phases_become_one_weighted_drop() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/crates.json")
        return httpx.Response(200, json=_crates_payload())

    crates = _run(handler, lambda client: BymykelClient(client, BASE).fetch_crates())

    assert len(crates) == 1
    crate = crates[0]
    assert crate.def_index == 4061
    assert [(drop.name, drop.is_special, drop.weight) for drop in crate.drops] == [
        ("AK-47 | Cartel", False, 1),
        ("★ Karambit | Doppler", True, 3),
        ("★ Karambit | Rust Coat", True, 1),
    ]


def test_skinport_history_is_split_into_windows() -> None:
    payload = [
        {
            "market_hash_name": "Chroma Case",
            "currency": "USD",
            "last_24_hours": {"min": 4.9, "max": 5.2, "avg": 5.01, "median": 5.0, "volume": 120},
            "last_7_days": {"min": 4.5, "max": 5.5, "avg": 5.0, "median": 4.95, "volume": 800},
            "last_30_days": None,
            "last_90_days": {"min": None, "max": None, "avg": None, "median": None, "volume": 0},
        }
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Accept-Encoding"] == "br"
        assert request.url.params["app_id"] == "730"
        return httpx.Response(200, json=payload)

    windows = _run(
        handler,
        lambda client: SkinportClient(
            client, "https://skinport.test/v1", 730, "USD"
        ).fetch_windows(),
    )

    by_window = {row.window: row for row in windows}
    assert set(by_window) == {"24h", "7d", "30d", "90d"}
    assert by_window["24h"].median_price == Decimal("5.00")
    assert by_window["7d"].volume == 800
    assert by_window["30d"].median_price is None
    assert by_window["90d"].volume == 0


def test_skinport_rate_limit_is_reported() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(429)

    with pytest.raises(CollectorError, match="лимит"):
        _run(
            handler,
            lambda client: SkinportClient(
                client, "https://skinport.test/v1", 730, "USD"
            ).fetch_listings(),
        )


def test_skin_float_range_keeps_zero_and_skips_missing() -> None:
    payload = [
        {"id": "skin-1", "name": "AK-47 | Redline", "min_float": 0, "max_float": 0.7},
        {"id": "skin-2", "name": "★ Kukri Knife", "min_float": None, "max_float": ""},
    ]

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    skins = _run(handler, lambda client: BymykelClient(client, BASE).fetch_skins())

    assert (skins[0].min_float, skins[0].max_float) == (0.0, 0.7)
    assert (skins[1].min_float, skins[1].max_float) == (None, None)
