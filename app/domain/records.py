from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class SkinRecord:
    bymykel_id: str
    name: str
    weapon: str | None
    category: str | None
    rarity: str | None
    rarity_color: str | None
    min_float: float | None
    max_float: float | None
    stattrak: bool
    souvenir: bool
    image_url: str | None
    paint_index: str | None
    wears: tuple[str, ...]


@dataclass(frozen=True)
class DropRecord:
    bymykel_id: str | None
    name: str
    rarity: str | None
    is_special: bool
    image_url: str | None


@dataclass(frozen=True)
class CrateRecord:
    bymykel_id: str
    name: str
    market_hash_name: str
    crate_type: str | None
    image_url: str | None
    def_index: int | None
    first_sale_date: str | None
    drops: tuple[DropRecord, ...]


@dataclass(frozen=True)
class Listing:
    market_hash_name: str
    currency: str
    suggested_price: Decimal | None
    min_price: Decimal | None
    max_price: Decimal | None
    mean_price: Decimal | None
    median_price: Decimal | None
    quantity: int | None


@dataclass(frozen=True)
class SaleWindow:
    market_hash_name: str
    currency: str
    window: str
    min_price: Decimal | None
    max_price: Decimal | None
    avg_price: Decimal | None
    median_price: Decimal | None
    volume: int | None
