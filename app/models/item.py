from sqlalchemy import Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (UniqueConstraint("bymykel_id", "wear", "kind", name="uq_items_variant"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    market_hash_name: Mapped[str] = mapped_column(String(512), unique=True)
    bymykel_id: Mapped[str] = mapped_column(String(128), index=True)
    base_name: Mapped[str] = mapped_column(String(512), index=True)
    wear: Mapped[str] = mapped_column(String(32), default="")
    kind: Mapped[str] = mapped_column(String(16))
    weapon: Mapped[str | None] = mapped_column(String(128))
    category: Mapped[str | None] = mapped_column(String(128))
    rarity: Mapped[str | None] = mapped_column(String(64))
    rarity_color: Mapped[str | None] = mapped_column(String(16))
    image_url: Mapped[str | None] = mapped_column(Text)
    min_float: Mapped[float | None] = mapped_column(Float)
    max_float: Mapped[float | None] = mapped_column(Float)
    stattrak: Mapped[bool] = mapped_column(default=False, server_default="false")
    souvenir: Mapped[bool] = mapped_column(default=False, server_default="false")
    def_index: Mapped[int | None] = mapped_column(Integer)
    paint_index: Mapped[str | None] = mapped_column(String(32))
