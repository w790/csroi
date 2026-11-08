from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel


class CaseSort(StrEnum):
    name = "name"
    case_price = "case_price"
    expected_value = "expected_value"
    unboxing_roi = "unboxing_roi"
    roi_7d = "roi_7d"
    roi_30d = "roi_30d"
    roi_90d = "roi_90d"


class SortOrder(StrEnum):
    asc = "asc"
    desc = "desc"


class CaseDropOut(BaseModel):
    name: str
    rarity: str | None
    is_special: bool
    probability: float | None
    price: float | None
    market_hash_name: str
    image_url: str | None


class CaseSummaryOut(BaseModel):
    id: int
    name: str
    image_url: str | None
    market_hash_name: str
    crate_type: str | None
    case_price: float | None
    key_price: float
    expected_value: float | None
    unboxing_roi: float | None
    roi_7d: float | None
    roi_30d: float | None
    roi_90d: float | None
    odds_valid: bool
    missing_prices: int
    prices_updated_at: datetime | None
    assumptions: str


class CaseDetailOut(CaseSummaryOut):
    drops: list[CaseDropOut]


class PricePointOut(BaseModel):
    captured_on: date
    price: float


class CaseHistoryOut(BaseModel):
    id: int
    name: str
    market_hash_name: str
    currency: str
    points: list[PricePointOut]
