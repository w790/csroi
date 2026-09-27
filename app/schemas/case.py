from pydantic import BaseModel

ASSUMPTIONS = (
    "Шансы Valve для оружейного кейса. "
    "Цена предмета — Field-Tested, если он есть в продаже, иначе ближайший доступный износ. "
    "Ключ 2.49 USD. StatTrak и точный float не учитываются. "
    "Investing ROI сравнивает медиану 24 часов с медианой окна 7/30/90 дней."
)


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
    assumptions: str


class CaseDetail(CaseSummary):
    drops: list[CaseDropOut]
