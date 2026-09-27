from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("market_hash_name", sa.String(length=512), nullable=False),
        sa.Column("bymykel_id", sa.String(length=128), nullable=False),
        sa.Column("base_name", sa.String(length=512), nullable=False),
        sa.Column("wear", sa.String(length=32), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("weapon", sa.String(length=128), nullable=True),
        sa.Column("category", sa.String(length=128), nullable=True),
        sa.Column("rarity", sa.String(length=64), nullable=True),
        sa.Column("rarity_color", sa.String(length=16), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("min_float", sa.Float(), nullable=True),
        sa.Column("max_float", sa.Float(), nullable=True),
        sa.Column("stattrak", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("souvenir", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("def_index", sa.Integer(), nullable=True),
        sa.Column("paint_index", sa.String(length=32), nullable=True),
        sa.UniqueConstraint("market_hash_name", name="uq_items_market_hash_name"),
        sa.UniqueConstraint("bymykel_id", "wear", "kind", name="uq_items_variant"),
    )
    op.create_index("ix_items_bymykel_id", "items", ["bymykel_id"])
    op.create_index("ix_items_base_name", "items", ["base_name"])

    op.create_table(
        "cases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bymykel_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("market_hash_name", sa.String(length=512), nullable=False),
        sa.Column("crate_type", sa.String(length=64), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("def_index", sa.Integer(), nullable=True),
        sa.Column("first_sale_date", sa.String(length=32), nullable=True),
        sa.UniqueConstraint("bymykel_id", name="uq_cases_bymykel_id"),
        sa.UniqueConstraint("market_hash_name", name="uq_cases_market_hash_name"),
    )
    op.create_index("ix_cases_crate_type", "cases", ["crate_type"])

    op.create_table(
        "case_drops",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("bymykel_id", sa.String(length=128), nullable=True),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("rarity", sa.String(length=64), nullable=True),
        sa.Column("is_special", sa.Boolean(), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("price_market_hash_name", sa.String(length=512), nullable=False),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name="fk_case_drops_case_id_cases",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("case_id", "name", name="uq_case_drops_case_name"),
    )
    op.create_index("ix_case_drops_case_id", "case_drops", ["case_id"])
    op.create_index(
        "ix_case_drops_price_market_hash_name",
        "case_drops",
        ["price_market_hash_name"],
    )

    op.create_table(
        "prices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("market_hash_name", sa.String(length=512), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("suggested_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("min_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("max_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("mean_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("median_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "market_hash_name",
            "source",
            "currency",
            name="uq_prices_identity",
        ),
    )

    op.create_table(
        "price_windows",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("market_hash_name", sa.String(length=512), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("window", sa.String(length=8), nullable=False),
        sa.Column("min_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("max_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("avg_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("median_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("volume", sa.Integer(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "market_hash_name",
            "source",
            "currency",
            "window",
            name="uq_price_windows_identity",
        ),
    )

    op.create_table(
        "price_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("market_hash_name", sa.String(length=512), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("price", sa.Numeric(14, 2), nullable=False),
        sa.Column("captured_on", sa.Date(), nullable=False),
        sa.UniqueConstraint(
            "market_hash_name",
            "source",
            "currency",
            "captured_on",
            name="uq_price_snapshots_identity",
        ),
    )


def downgrade() -> None:
    op.drop_table("price_snapshots")
    op.drop_table("price_windows")
    op.drop_table("prices")
    op.drop_table("case_drops")
    op.drop_table("cases")
    op.drop_table("items")
