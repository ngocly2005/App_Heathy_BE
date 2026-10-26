from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260924_0003"
down_revision: str | None = "8da74fd2c368"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "health_profiles",
        sa.Column("user_id", sa.Integer(), primary_key=True),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("sex", sa.String(length=10), nullable=False),
        sa.Column("height_cm", sa.Numeric(5, 2), nullable=False),
        sa.Column("weight_kg", sa.Numeric(5, 2), nullable=False),
        sa.Column("activity_level", sa.String(length=20), nullable=False),
        sa.Column("goal", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "sex IN ('male', 'female')",
            name="ck_health_profile_sex",
        ),
        sa.CheckConstraint("height_cm > 0", name="ck_health_profile_height"),
        sa.CheckConstraint("weight_kg > 0", name="ck_health_profile_weight"),
        sa.CheckConstraint(
            "activity_level IN "
            "('sedentary', 'light', 'moderate', 'very_active')",
            name="ck_health_profile_activity",
        ),
        sa.CheckConstraint(
            "goal IN ('lose', 'maintain', 'gain')",
            name="ck_health_profile_goal",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
    )


def downgrade() -> None:
    op.drop_table("health_profiles")
