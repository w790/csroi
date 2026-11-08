import json
from decimal import Decimal

import httpx

from app.domain.constants import (
    WINDOW_7D,
    WINDOW_24H,
    WINDOW_30D,
    WINDOW_90D,
)
from app.domain.records import CrateRecord, DropRecord, Listing, SaleWindow, SkinRecord

SKINPORT_WINDOWS = {
    "last_24_hours": WINDOW_24H,
    "last_7_days": WINDOW_7D,
    "last_30_days": WINDOW_30D,
    "last_90_days": WINDOW_90D,
}


class CollectorError(Exception):
    pass


class BymykelClient:
    def __init__(self, client: httpx.AsyncClient, base_url: str) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")

    async def fetch_skins(self) -> list[SkinRecord]:
        payload = await self._get_list("skins.json")
        parsed = (_parse_skin(raw) for raw in payload)
        return [skin for skin in parsed if skin is not None]

    async def fetch_crates(self) -> list[CrateRecord]:
        payload = await self._get_list("crates.json")
        parsed = (_parse_crate(raw) for raw in payload)
        return [crate for crate in parsed if crate is not None]

    async def _get_list(self, name: str) -> list[object]:
        response = await self._client.get(f"{self._base_url}/{name}")
        if response.status_code != 200:
            raise CollectorError(f"{name}: HTTP {response.status_code}")
        payload = _load_json(response.content)
        if not isinstance(payload, list):
            raise CollectorError(f"{name}: ожидался список")
        return payload


class SkinportClient:
    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        app_id: int,
        currency: str,
    ) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._app_id = app_id
        self._currency = currency

    async def fetch_listings(self) -> list[Listing]:
        payload = await self._get_list("/items")
        parsed = (_parse_listing(raw, self._currency) for raw in payload)
        return [listing for listing in parsed if listing is not None]

    async def fetch_windows(self) -> list[SaleWindow]:
        payload = await self._get_list("/sales/history")
        windows: list[SaleWindow] = []
        for raw in payload:
            windows.extend(_parse_windows(raw, self._currency))
        return windows

    async def _get_list(self, path: str) -> list[object]:
        response = await self._client.get(
            f"{self._base_url}{path}",
            params={"app_id": self._app_id, "currency": self._currency},
            headers={
                "Accept-Encoding": "br",
                "User-Agent": "csroi-study/0.1",
            },
        )
        _raise_for_skinport_status(response, path)
        payload = _load_json(response.content)
        if not isinstance(payload, list):
            raise CollectorError(f"skinport {path}: ожидался список")
        return payload


def _parse_skin(raw: object) -> SkinRecord | None:
    if not isinstance(raw, dict):
        return None
    name = _str_or_none(raw.get("name"))
    bymykel_id = _str_or_none(raw.get("id"))
    if name is None or bymykel_id is None:
        return None
    return SkinRecord(
        bymykel_id=bymykel_id,
        name=name,
        weapon=_nested_str(raw.get("weapon"), "name"),
        category=_nested_str(raw.get("category"), "name"),
        rarity=_nested_str(raw.get("rarity"), "name"),
        rarity_color=_nested_str(raw.get("rarity"), "color"),
        min_float=_float_or_none(raw.get("min_float")),
        max_float=_float_or_none(raw.get("max_float")),
        stattrak=bool(raw.get("stattrak")),
        souvenir=bool(raw.get("souvenir")),
        image_url=_str_or_none(raw.get("image")),
        paint_index=_str_or_none(raw.get("paint_index")),
        wears=_parse_wears(raw.get("wears")),
    )


def _parse_wears(raw_wears: object) -> tuple[str, ...]:
    if not isinstance(raw_wears, list):
        return ()
    names = (_nested_str(wear, "name") for wear in raw_wears)
    return tuple(name for name in names if name is not None)


def _parse_crate(raw: object) -> CrateRecord | None:
    if not isinstance(raw, dict):
        return None
    name = _str_or_none(raw.get("name"))
    bymykel_id = _str_or_none(raw.get("id"))
    if name is None or bymykel_id is None:
        return None
    regular = _parse_drops(raw.get("contains"), is_special=False)
    special = _parse_drops(raw.get("contains_rare"), is_special=True)
    return CrateRecord(
        bymykel_id=bymykel_id,
        name=name,
        market_hash_name=_str_or_none(raw.get("market_hash_name")) or name,
        crate_type=_str_or_none(raw.get("type")),
        image_url=_str_or_none(raw.get("image")),
        def_index=_int_or_none(raw.get("def_index")),
        first_sale_date=_str_or_none(raw.get("first_sale_date")),
        drops=tuple(regular + special),
    )


def _parse_drops(raw_items: object, *, is_special: bool) -> list[DropRecord]:
    if not isinstance(raw_items, list):
        return []
    parsed = (_parse_drop(raw, is_special=is_special) for raw in raw_items)
    return [drop for drop in parsed if drop is not None]


def _parse_drop(raw: object, *, is_special: bool) -> DropRecord | None:
    if not isinstance(raw, dict):
        return None
    name = _str_or_none(raw.get("name"))
    if name is None:
        return None
    return DropRecord(
        bymykel_id=_str_or_none(raw.get("id")),
        name=name,
        rarity=_nested_str(raw.get("rarity"), "name"),
        is_special=is_special,
        image_url=_str_or_none(raw.get("image")),
    )


def _parse_listing(raw: object, default_currency: str) -> Listing | None:
    if not isinstance(raw, dict):
        return None
    name = _str_or_none(raw.get("market_hash_name"))
    if name is None:
        return None
    return Listing(
        market_hash_name=name,
        currency=_str_or_none(raw.get("currency")) or default_currency,
        suggested_price=_decimal_or_none(raw.get("suggested_price")),
        min_price=_decimal_or_none(raw.get("min_price")),
        max_price=_decimal_or_none(raw.get("max_price")),
        mean_price=_decimal_or_none(raw.get("mean_price")),
        median_price=_decimal_or_none(raw.get("median_price")),
        quantity=_int_or_none(raw.get("quantity")),
    )


def _parse_windows(raw: object, default_currency: str) -> list[SaleWindow]:
    if not isinstance(raw, dict):
        return []
    name = _str_or_none(raw.get("market_hash_name"))
    if name is None:
        return []
    currency = _str_or_none(raw.get("currency")) or default_currency
    windows: list[SaleWindow] = []
    for field, window in SKINPORT_WINDOWS.items():
        stats = raw.get(field) or {}
        if isinstance(stats, dict):
            windows.append(_parse_window(name, currency, window, stats))
    return windows


def _parse_window(
    name: str,
    currency: str,
    window: str,
    stats: dict[str, object],
) -> SaleWindow:
    return SaleWindow(
        market_hash_name=name,
        currency=currency,
        window=window,
        min_price=_decimal_or_none(stats.get("min")),
        max_price=_decimal_or_none(stats.get("max")),
        avg_price=_decimal_or_none(stats.get("avg")),
        median_price=_decimal_or_none(stats.get("median")),
        volume=_int_or_none(stats.get("volume")),
    )


def _raise_for_skinport_status(response: httpx.Response, path: str) -> None:
    if response.status_code == 429:
        raise CollectorError("skinport: лимит 8 запросов за 5 минут")
    if response.status_code == 406:
        raise CollectorError("skinport: нужен заголовок Accept-Encoding: br")
    if response.status_code == 403:
        raise CollectorError("skinport: запрос заблокирован Cloudflare, повторим позже")
    if response.status_code != 200:
        raise CollectorError(f"skinport {path}: HTTP {response.status_code}")


def _load_json(content: bytes) -> object:
    return json.loads(content, parse_float=Decimal)


def _nested_str(value: object, key: str) -> str | None:
    if isinstance(value, dict):
        return _str_or_none(value.get(key))
    return None


def _str_or_none(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _decimal_or_none(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.01"))
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _int_or_none(value: object) -> int | None:
    if value is None or value == "" or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, Decimal):
        return int(value)
    if isinstance(value, str) and value.lstrip("-").isdigit():
        return int(value)
    return None


def _float_or_none(value: object) -> float | None:
    if isinstance(value, int | float | str | Decimal) and value != "":
        return float(value)
    return None
