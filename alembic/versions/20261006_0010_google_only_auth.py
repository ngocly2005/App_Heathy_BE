"""Require linked Google accounts before removing password authentication."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261006_0010"
down_revision: str | None = "20261006_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Executed before any destructive DDL, including when using offline SQL.
    op.execute(
        """
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM users
                WHERE google_sub IS NULL OR btrim(google_sub) = ''
            ) THEN
                RAISE EXCEPTION 'Link all users using Lesson 17 before Lesson 18';
            END IF;
        END $$;
        """
    )
    op.execute(
        "UPDATE refresh_tokens SET revoked_at = CURRENT_TIMESTAMP "
        "WHERE revoked_at IS NULL"
    )
    op.alter_column("users", "google_sub", existing_type=sa.String(255), nullable=False)
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.drop_column("users", "role")
    op.drop_column("users", "password_hash")


def downgrade() -> None:
    # Schema rollback cannot recover removed password hashes or active sessions.
    op.add_column("users", sa.Column("password_hash", sa.String(255), nullable=True))
    op.add_column(
        "users",
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
    )
    op.create_check_constraint("ck_users_role", "users", "role IN ('user', 'admin')")
    op.alter_column("users", "google_sub", existing_type=sa.String(255), nullable=True)
