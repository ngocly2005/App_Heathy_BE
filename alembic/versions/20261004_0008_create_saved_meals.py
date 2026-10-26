"""Create saved meals tables.

Revision ID: 20261004_0008
Revises: 20261004_0007
Create Date: 2026-10-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261004_0008"
down_revision: str | None = "20261004_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "saved_meals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "name", name="uq_saved_meal_user_name"),
    )
    op.create_index("ix_saved_meals_user_id", "saved_meals", ["user_id"])

    op.create_table(
        "saved_meal_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("saved_meal_id", sa.Integer(), nullable=False),
        sa.Column("food_id", sa.Integer(), nullable=True),
        sa.Column("food_name", sa.String(length=160), nullable=False),
        sa.Column("grams", sa.Numeric(8, 2), nullable=False),
        sa.Column("calories_per_100g", sa.Numeric(8, 2), nullable=False),
        sa.Column("protein_per_100g", sa.Numeric(8, 2), nullable=False),
        sa.Column("carb_per_100g", sa.Numeric(8, 2), nullable=False),
        sa.Column("fat_per_100g", sa.Numeric(8, 2), nullable=False),
        sa.CheckConstraint("grams > 0", name="ck_saved_meal_item_grams"),
        sa.CheckConstraint(
            "calories_per_100g >= 0",
            name="ck_saved_item_calories",
        ),
        sa.CheckConstraint("protein_per_100g >= 0", name="ck_saved_item_protein"),
        sa.CheckConstraint("carb_per_100g >= 0", name="ck_saved_item_carbs"),
        sa.CheckConstraint("fat_per_100g >= 0", name="ck_saved_item_fat"),
        sa.ForeignKeyConstraint(
            ["saved_meal_id"],
            ["saved_meals.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["food_id"], ["foods.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_saved_meal_items_saved_meal_id",
        "saved_meal_items",
        ["saved_meal_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_saved_meal_items_saved_meal_id",
        table_name="saved_meal_items",
    )
    op.drop_table("saved_meal_items")
    op.drop_index("ix_saved_meals_user_id", table_name="saved_meals")
    op.drop_table("saved_meals")

