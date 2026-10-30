import json
from decimal import Decimal

import httpx

from app.domain.constants import (
    WINDOW_7D,
    WINDOW_24H,
    WINDOW_30D,
    WINDOW_90D,
)
from app.domain.names import merge_phases
from app.domain.records import CrateRecord, DropRecord, Listing, SaleWindow, SkinRecord

SKINPORT_WINDOWS = {
    "last_24_hours": WINDOW_24H,
    "last_7_days": WINDOW_7D,
    "last_30_days": WINDOW_30D,
    "last_90_days": WINDOW_90D,
}


class CollectorError(Exception):
    pass


def _text(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _nested_name(value: object) -> str | None:
    if isinstance(value, dict):
        return _text(value.get("name"))
    return None


def _nested_color(value: object) -> str | None:
    if isinstance(value, dict):
        return _text(value.get("color"))
    return None


def _money(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.01"))
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _whole(value: object) -> int | None:
    if value is None or value == "" or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, Decimal):
        return int(value)
    if isinstance(value, str) and value.lstrip("-").isdigit():
        return int(value)
    return None


def _loads(content: bytes) -> object:
    return json.loads(content, parse_float=Decimal)


class BymykelClient:
    def __init__(self, client: httpx.AsyncClient, base_url: str) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")

    async def fetch_skins(self) -> list[SkinRecord]:
        payload = await self._get_json("skins.json")
        if not isinstance(payload, list):
            raise CollectorError("skins.json: ожидался список")
        skins: list[SkinRecord] = []
        for raw in payload:
            if not isinstance(raw, dict):
                continue
            name = _text(raw.get("name"))
            bymykel_id = _text(raw.get("id"))
            if name is None or bymykel_id is None:
                continue
            wears = tuple(
                wear_name
                for wear in raw.get("wears") or []
                if isinstance(wear, dict) and (wear_name := _text(wear.get("name")))
            )
            skins.append(
                SkinRecord(
                    bymykel_id=bymykel_id,
                    name=name,
                    weapon=_nested_name(raw.get("weapon")),
                    category=_nested_name(raw.get("category")),
                    rarity=_nested_name(raw.get("rarity")),
                    rarity_color=_nested_color(raw.get("rarity")),
                    min_float=_float_or_none(raw.get("min_float")),
                    max_float=_float_or_none(raw.get("max_float")),
                    stattrak=bool(raw.get("stattrak")),
                    souvenir=bool(raw.get("souvenir")),
                    image_url=_text(raw.get("image")),
                    paint_index=_text(raw.get("paint_index")),
                    wears=wears,
                )
            )
        return skins

    async def fetch_crates(self) -> list[CrateRecord]:
        payload = await self._get_json("crates.json")
        if not isinstance(payload, list):
            raise CollectorError("crates.json: ожидался список")
        crates: list[CrateRecord] = []
        for raw in payload:
            if not isinstance(raw, dict):
                continue
            name = _text(raw.get("name"))
            bymykel_id = _text(raw.get("id"))
            if name is None or bymykel_id is None:
                continue
            drops = _drops(raw.get("contains"), is_special=False) + _drops(
                raw.get("contains_rare"),
                is_special=True,
            )
            crates.append(
                CrateRecord(
                    bymykel_id=bymykel_id,
                    name=name,
                    market_hash_name=_text(raw.get("market_hash_name")) or name,
                    crate_type=_text(raw.get("type")),
                    image_url=_text(raw.get("image")),
                    def_index=_whole(raw.get("def_index")),
                    first_sale_date=_text(raw.get("first_sale_date")),
                    drops=tuple(merge_phases(drops)),
                )
            )
        return crates

    async def _get_json(self, name: str) -> object:
        response = await self._client.get(f"{self._base_url}/{name}")
        if response.status_code != 200:
            raise CollectorError(f"{name}: HTTP {response.status_code}")
        return _loads(response.content)


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
        payload = await self._get("/items")
        if not isinstance(payload, list):
            raise CollectorError("skinport /items: ожидался список")
        listings: list[Listing] = []
        for raw in payload:
            if not isinstance(raw, dict):
                continue
            name = _text(raw.get("market_hash_name"))
            if name is None:
                continue
            listings.append(
                Listing(
                    market_hash_name=name,
                    currency=_text(raw.get("currency")) or self._currency,
                    suggested_price=_money(raw.get("suggested_price")),
                    min_price=_money(raw.get("min_price")),
                    max_price=_money(raw.get("max_price")),
                    mean_price=_money(raw.get("mean_price")),
                    median_price=_money(raw.get("median_price")),
                    quantity=_whole(raw.get("quantity")),
                )
            )
        return listings

    async def fetch_windows(self) -> list[SaleWindow]:
        payload = await self._get("/sales/history")
        if not isinstance(payload, list):
            raise CollectorError("skinport /sales/history: ожидался список")
        windows: list[SaleWindow] = []
        for raw in payload:
            if not isinstance(raw, dict):
                continue
            name = _text(raw.get("market_hash_name"))
            if name is None:
                continue
            currency = _text(raw.get("currency")) or self._currency
            for field, window in SKINPORT_WINDOWS.items():
                stats = raw.get(field) or {}
                if not isinstance(stats, dict):
                    continue
                windows.append(
                    SaleWindow(
                        market_hash_name=name,
                        currency=currency,
                        window=window,
                        min_price=_money(stats.get("min")),
                        max_price=_money(stats.get("max")),
                        avg_price=_money(stats.get("avg")),
                        median_price=_money(stats.get("median")),
                        volume=_whole(stats.get("volume")),
                    )
                )
        return windows

    async def _get(self, path: str) -> object:
        response = await self._client.get(
            f"{self._base_url}{path}",
            params={"app_id": self._app_id, "currency": self._currency},
            headers={
                "Accept-Encoding": "br",
                "User-Agent": "csroi-study/0.1",
            },
        )
        if response.status_code == 429:
            raise CollectorError("skinport: лимит 8 запросов за 5 минут")
        if response.status_code == 406:
            raise CollectorError("skinport: нужен заголовок Accept-Encoding: br")
        if response.status_code != 200:
            raise CollectorError(f"skinport {path}: HTTP {response.status_code}")
        return _loads(response.content)


def _drops(raw_items: object, *, is_special: bool) -> list[DropRecord]:
    if not isinstance(raw_items, list):
        return []
    drops: list[DropRecord] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        name = _text(raw.get("name"))
        if name is None:
            continue
        drops.append(
            DropRecord(
                bymykel_id=_text(raw.get("id")),
                name=name,
                rarity=_nested_name(raw.get("rarity")),
                is_special=is_special,
                image_url=_text(raw.get("image")),
            )
        )
    return drops


def _float_or_none(value: object) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
