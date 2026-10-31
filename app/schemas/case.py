from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel

from app.core.config import settings

ASSUMPTIONS = (
    "Шансы Valve для оружейного кейса. "
    "Допущение, не подтверждённое Valve: каждая фаза Doppler — отдельная запись в пуле ножей "
    "с равным шансом, цена у фаз общая. "
    "Цена предмета — медиана продаж на Skinport за 30 дней, если продаж не было — за 90 дней, "
    "иначе цена лота. Износ — Field-Tested, если есть цена, иначе тот, "
    "который занимает большую часть float-диапазона скина. Цена кейса — по текущим лотам. "
    f"Ключ {settings.key_price_usd} USD. StatTrak и точный float не учитываются. "
    "Investing ROI сравнивает медиану 24 часов с медианой окна 7/30/90 дней."
)


class CaseSort(str, Enum):
    name = "name"
    case_price = "case_price"
    expected_value = "expected_value"
    unboxing_roi = "unboxing_roi"
    roi_7d = "roi_7d"
    roi_30d = "roi_30d"
    roi_90d = "roi_90d"


class SortOrder(str, Enum):
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


class CaseSummary(BaseModel):
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


class CaseDetail(CaseSummary):
    drops: list[CaseDropOut]


class PricePointOut(BaseModel):
    captured_on: date
    price: float


class CaseHistory(BaseModel):
    id: int
    name: str
    market_hash_name: str
    currency: str
    points: list[PricePointOut]
