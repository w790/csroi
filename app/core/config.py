from decimal import Decimal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://csroi:csroi@localhost:5433/csroi"
    redis_url: str = "redis://localhost:6379/0"

    bymykel_base_url: str = "https://raw.githubusercontent.com/ByMykel/CSGO-API/main/public/api/en"
    skinport_base_url: str = "https://api.skinport.com/v1"
    skinport_app_id: int = 730
    skinport_currency: str = "USD"

    key_price_usd: Decimal = Decimal("2.49")
    price_refresh_minutes: int = 5
    http_timeout_seconds: float = 120

    @field_validator("skinport_currency")
    @classmethod
    def _key_price_is_in_usd(cls, value: str) -> str:
        if value != "USD":
            raise ValueError("цена ключа задана в USD, другие валюты дадут неверный ROI")
        return value


settings = Settings()
