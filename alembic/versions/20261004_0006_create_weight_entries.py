"""Create weight_entries table.

Revision ID: 20261004_0006
Revises: 20260928_0005
Create Date: 2026-10-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261004_0006"
down_revision: str | None = "20260928_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "weight_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("measured_on", sa.Date(), nullable=False),
        sa.Column("weight_kg", sa.Numeric(5, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("weight_kg > 0", name="ck_weight_entry_weight"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "user_id",
            "measured_on",
            name="uq_weight_user_date",
        ),
    )
    op.create_index(
        "ix_weight_entries_user_id",
        "weight_entries",
        ["user_id"],
    )
    op.execute(
        """
        INSERT INTO weight_entries (user_id, measured_on, weight_kg, created_at)
        SELECT user_id, CURRENT_DATE, weight_kg, CURRENT_TIMESTAMP
        FROM health_profiles
        """
    )


def downgrade() -> None:
    op.drop_index("ix_weight_entries_user_id", table_name="weight_entries")
    op.drop_table("weight_entries")

