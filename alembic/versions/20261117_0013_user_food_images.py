"""Personal foods and server-local food images. Upgrade once after 0012."""

from alembic import op
import sqlalchemy as sa

revision = "20261117_0013"
down_revision = "20261113_0012"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("foods", sa.Column("image_filename", sa.String(80), nullable=True))
    op.create_table(
        "user_foods",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("calories_per_100g", sa.Numeric(8, 2), nullable=False),
        sa.Column("protein_per_100g", sa.Numeric(8, 2), nullable=False),
        sa.Column("carb_per_100g", sa.Numeric(8, 2), nullable=False),
        sa.Column("fat_per_100g", sa.Numeric(8, 2), nullable=False),
        sa.Column("image_filename", sa.String(80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("calories_per_100g >= 0", name="ck_user_food_calories"),
        sa.CheckConstraint("protein_per_100g >= 0", name="ck_user_food_protein"),
        sa.CheckConstraint("carb_per_100g >= 0", name="ck_user_food_carbs"),
        sa.CheckConstraint("fat_per_100g >= 0", name="ck_user_food_fat"),
        sa.UniqueConstraint("user_id", "name", name="uq_user_food_owner_name"),
    )
    op.create_index("ix_user_foods_user_id", "user_foods", ["user_id"])


def downgrade():
    op.drop_index("ix_user_foods_user_id", table_name="user_foods")
    op.drop_table("user_foods")
    op.drop_column("foods", "image_filename")
