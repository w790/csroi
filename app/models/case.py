from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    bymykel_id: Mapped[str] = mapped_column(String(128), unique=True)
    name: Mapped[str] = mapped_column(String(512))
    market_hash_name: Mapped[str] = mapped_column(String(512), unique=True)
    crate_type: Mapped[str | None] = mapped_column(String(64), index=True)
    image_url: Mapped[str | None] = mapped_column(Text)
    def_index: Mapped[int | None] = mapped_column(Integer)
    first_sale_date: Mapped[str | None] = mapped_column(String(32))

    drops: Mapped[list["CaseDrop"]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
    )


class CaseDrop(Base):
    __tablename__ = "case_drops"
    __table_args__ = (UniqueConstraint("case_id", "name", name="uq_case_drops_case_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"),
        index=True,
    )
    bymykel_id: Mapped[str | None] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(512))
    rarity: Mapped[str | None] = mapped_column(String(64))
    is_special: Mapped[bool] = mapped_column(Boolean)
    weight: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    image_url: Mapped[str | None] = mapped_column(Text)

    case: Mapped[Case] = relationship(back_populates="drops")
