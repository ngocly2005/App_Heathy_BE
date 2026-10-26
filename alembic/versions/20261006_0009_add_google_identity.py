"""Add Google identity while preserving password sign-in for linking."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261006_0009"
down_revision: str | None = "20261004_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("google_sub", sa.String(255), nullable=True))
    op.create_unique_constraint("uq_users_google_sub", "users", ["google_sub"])
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=True)


def downgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM users WHERE password_hash IS NULL) THEN
                RAISE EXCEPTION 'Cannot remove Google sign-in from passwordless accounts';
            END IF;
        END $$;
        """
    )
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=False)
    op.drop_constraint("uq_users_google_sub", "users", type_="unique")
    op.drop_column("users", "google_sub")
