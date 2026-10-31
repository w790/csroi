from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_drop_price_market_hash_name"
down_revision: str | Sequence[str] | None = "0002_case_drop_weight"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_case_drops_price_market_hash_name", table_name="case_drops")
    op.drop_column("case_drops", "price_market_hash_name")


def downgrade() -> None:
    op.add_column(
        "case_drops",
        sa.Column("price_market_hash_name", sa.String(length=512), nullable=True),
    )
    op.execute("UPDATE case_drops SET price_market_hash_name = name")
    op.alter_column("case_drops", "price_market_hash_name", nullable=False)
    op.create_index(
        "ix_case_drops_price_market_hash_name",
        "case_drops",
        ["price_market_hash_name"],
    )
