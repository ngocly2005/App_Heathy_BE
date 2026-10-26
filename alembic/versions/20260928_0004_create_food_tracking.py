
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260928_0004"
down_revision: str | None = "20260924_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    foods = op.create_table(
        "foods",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("calories_per_100g", sa.Numeric(8, 2), nullable=False),
        sa.Column("protein_per_100g", sa.Numeric(8, 2), nullable=False),
        sa.Column("carb_per_100g", sa.Numeric(8, 2), nullable=False),
        sa.Column("fat_per_100g", sa.Numeric(8, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.CheckConstraint("calories_per_100g >= 0", name="ck_food_calories"),
        sa.CheckConstraint("protein_per_100g >= 0", name="ck_food_protein"),
        sa.CheckConstraint("carb_per_100g >= 0", name="ck_food_carbs"),
        sa.CheckConstraint("fat_per_100g >= 0", name="ck_food_fat"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_foods_is_active", "foods", ["is_active"])
    op.bulk_insert(
        foods,
        [
            {
                "name": "Cooked chicken breast",
                "calories_per_100g": 165,
                "protein_per_100g": 31,
                "carb_per_100g": 0,
                "fat_per_100g": 3.6,
                "is_active": True,
            },
            {
                "name": "Cooked white rice",
                "calories_per_100g": 130,
                "protein_per_100g": 2.7,
                "carb_per_100g": 28.2,
                "fat_per_100g": 0.3,
                "is_active": True,
            },
            {
                "name": "Boiled egg",
                "calories_per_100g": 155,
                "protein_per_100g": 12.6,
                "carb_per_100g": 1.1,
                "fat_per_100g": 10.6,
                "is_active": True,
            },
            {
                "name": "Banana",
                "calories_per_100g": 89,
                "protein_per_100g": 1.1,
                "carb_per_100g": 22.8,
                "fat_per_100g": 0.3,
                "is_active": True,
            },
            {
                "name": "Apple",
                "calories_per_100g": 52,
                "protein_per_100g": 0.3,
                "carb_per_100g": 13.8,
                "fat_per_100g": 0.2,
                "is_active": True,
            },
        ],
    )

    op.create_table(
        "food_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("food_id", sa.Integer(), nullable=True),
        sa.Column("log_date", sa.Date(), nullable=False),
        sa.Column("meal_type", sa.String(length=20), nullable=False),
        sa.Column("grams", sa.Numeric(8, 2), nullable=False),
        sa.Column("food_name", sa.String(length=160), nullable=False),
        sa.Column("calories_kcal", sa.Numeric(9, 2), nullable=False),
        sa.Column("protein_g", sa.Numeric(9, 2), nullable=False),
        sa.Column("carb_g", sa.Numeric(9, 2), nullable=False),
        sa.Column("fat_g", sa.Numeric(9, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("grams > 0", name="ck_food_log_grams"),
        sa.CheckConstraint("calories_kcal >= 0", name="ck_food_log_calories"),
        sa.CheckConstraint("protein_g >= 0", name="ck_food_log_protein"),
        sa.CheckConstraint("carb_g >= 0", name="ck_food_log_carbs"),
        sa.CheckConstraint("fat_g >= 0", name="ck_food_log_fat"),
        sa.CheckConstraint(
            "meal_type IN ('breakfast', 'lunch', 'dinner', 'snack')",
            name="ck_food_log_meal_type",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["food_id"], ["foods.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_food_logs_user_date",
        "food_logs",
        ["user_id", "log_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_food_logs_user_date", table_name="food_logs")
    op.drop_table("food_logs")
    op.drop_index("ix_foods_is_active", table_name="foods")
    op.drop_table("foods")
