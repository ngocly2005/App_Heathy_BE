"""Store short, one-use email password-reset codes in the database."""

from alembic import op
import sqlalchemy as sa


revision = "20261119_0016"
down_revision = "20261119_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "password_reset_codes",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("attempts >= 0 AND attempts <= 5", name="ck_password_reset_attempts"),
    )


def downgrade() -> None:
    op.drop_table("password_reset_codes")
