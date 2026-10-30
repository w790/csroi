from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_case_drop_weight"
down_revision: str | Sequence[str] | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "case_drops",
        sa.Column("weight", sa.Integer(), server_default="1", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("case_drops", "weight")
