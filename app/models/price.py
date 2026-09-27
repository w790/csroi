from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

MONEY = Numeric(14, 2)


class Price(Base):
    __tablename__ = "prices"
    __table_args__ = (
        UniqueConstraint(
            "market_hash_name",
            "source",
            "currency",
            name="uq_prices_identity",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    market_hash_name: Mapped[str] = mapped_column(String(512))
    source: Mapped[str] = mapped_column(String(32))
    currency: Mapped[str] = mapped_column(String(8))
    suggested_price: Mapped[Decimal | None] = mapped_column(MONEY)
    min_price: Mapped[Decimal | None] = mapped_column(MONEY)
    max_price: Mapped[Decimal | None] = mapped_column(MONEY)
    mean_price: Mapped[Decimal | None] = mapped_column(MONEY)
    median_price: Mapped[Decimal | None] = mapped_column(MONEY)
    quantity: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class PriceWindow(Base):
    __tablename__ = "price_windows"
    __table_args__ = (
        UniqueConstraint(
            "market_hash_name",
            "source",
            "currency",
            "window",
            name="uq_price_windows_identity",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    market_hash_name: Mapped[str] = mapped_column(String(512))
    source: Mapped[str] = mapped_column(String(32))
    currency: Mapped[str] = mapped_column(String(8))
    window: Mapped[str] = mapped_column(String(8))
    min_price: Mapped[Decimal | None] = mapped_column(MONEY)
    max_price: Mapped[Decimal | None] = mapped_column(MONEY)
    avg_price: Mapped[Decimal | None] = mapped_column(MONEY)
    median_price: Mapped[Decimal | None] = mapped_column(MONEY)
    volume: Mapped[int | None] = mapped_column(Integer)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "market_hash_name",
            "source",
            "currency",
            "captured_on",
            name="uq_price_snapshots_identity",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    market_hash_name: Mapped[str] = mapped_column(String(512))
    source: Mapped[str] = mapped_column(String(32))
    currency: Mapped[str] = mapped_column(String(8))
    price: Mapped[Decimal] = mapped_column(MONEY)
    captured_on: Mapped[date] = mapped_column(Date)
