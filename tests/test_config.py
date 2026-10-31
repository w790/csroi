import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_usd_is_accepted() -> None:
    assert Settings(skinport_currency="USD").skinport_currency == "USD"


def test_other_currency_is_rejected() -> None:
    with pytest.raises(ValidationError, match="USD"):
        Settings(skinport_currency="EUR")
