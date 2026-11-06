"""One consolidated revision for the Android and React Admin integration.

Keeps every previously applied revision intact. Teacher runs upgrade after review.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261105_0011"
down_revision = "20261006_0010"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("role", sa.String(20), nullable=False, server_default="user"))
    op.create_check_constraint("ck_users_role", "users", "role IN ('user', 'admin')")
    op.drop_constraint("ck_health_profile_activity", "health_profiles", type_="check")
    op.create_check_constraint("ck_health_profile_activity", "health_profiles",
        "activity_level IN ('sedentary', 'light', 'moderate', 'very_active', 'extra_active')")
    op.add_column("food_logs", sa.Column("meal_time", sa.String(5), nullable=True))
    op.create_table("water_settings",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("target_ml", sa.Integer(), nullable=True),
        sa.Column("serving_ml", sa.Integer(), nullable=False, server_default="200"),
        sa.CheckConstraint("target_ml IS NULL OR (target_ml >= 500 AND target_ml <= 10000)", name="ck_water_settings_target"),
        sa.CheckConstraint("serving_ml IN (200, 500)", name="ck_water_settings_serving"))
    op.create_table("nutrition_settings",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("calorie_target", sa.Numeric(8, 2), nullable=True),
        sa.Column("protein_pct", sa.Integer(), nullable=False, server_default="25"),
        sa.Column("carb_pct", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("fat_pct", sa.Integer(), nullable=False, server_default="25"),
        sa.Column("target_weight_kg", sa.Numeric(5, 2), nullable=True),
        sa.CheckConstraint("calorie_target IS NULL OR (calorie_target >= 500 AND calorie_target <= 10000)", name="ck_nutrition_calorie"),
        sa.CheckConstraint("protein_pct >= 0 AND carb_pct >= 0 AND fat_pct >= 0 AND protein_pct + carb_pct + fat_pct = 100", name="ck_nutrition_macro"),
        sa.CheckConstraint("target_weight_kg IS NULL OR (target_weight_kg > 20 AND target_weight_kg <= 400)", name="ck_nutrition_weight"))
    op.create_table("ai_interactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("context_date", sa.Date(), nullable=False),
        sa.Column("question", sa.Text(), nullable=True),
        sa.Column("response", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("error_code", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind IN ('chat', 'photo')", name="ck_ai_kind"),
        sa.CheckConstraint("status IN ('success', 'error')", name="ck_ai_status"))
    op.create_index("ix_ai_user_created", "ai_interactions", ["user_id", "created_at"])


def downgrade():
    # Check before any destructive DDL.
    op.execute("DO $$ BEGIN IF EXISTS (SELECT 1 FROM health_profiles WHERE activity_level = 'extra_active') "
               "THEN RAISE EXCEPTION 'Change extra_active profiles before downgrade'; END IF; END $$;")
    op.drop_index("ix_ai_user_created", table_name="ai_interactions")
    op.drop_table("ai_interactions")
    op.drop_table("nutrition_settings")
    op.drop_table("water_settings")
    op.drop_column("food_logs", "meal_time")
    op.drop_constraint("ck_health_profile_activity", "health_profiles", type_="check")
    op.create_check_constraint("ck_health_profile_activity", "health_profiles",
        "activity_level IN ('sedentary', 'light', 'moderate', 'very_active')")
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.drop_column("users", "role")
