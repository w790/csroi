from decimal import Decimal

TIER_ODDS: dict[str, Decimal] = {
    "Mil-Spec Grade": Decimal("0.7992"),
    "Restricted": Decimal("0.1598"),
    "Classified": Decimal("0.0320"),
    "Covert": Decimal("0.0064"),
}

SPECIAL_ODDS = Decimal("0.0026")
