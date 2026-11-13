"""Add password authentication alongside Google, preserving applied revisions.

Teacher runs this one new revision after updating requirements and reviewing SQL.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261113_0012"
down_revision = "20261105_0011"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("password_hash", sa.String(255), nullable=True))
    op.alter_column("users", "google_sub", existing_type=sa.String(255), nullable=True)
    op.create_check_constraint("ck_users_auth_method", "users",
                               "google_sub IS NOT NULL OR password_hash IS NOT NULL")


def downgrade():
    op.execute("DO $$ BEGIN IF EXISTS (SELECT 1 FROM users WHERE google_sub IS NULL) "
               "THEN RAISE EXCEPTION 'Link all password-only accounts to Google before downgrade'; END IF; END $$;")
    op.drop_constraint("ck_users_auth_method", "users", type_="check")
    op.alter_column("users", "google_sub", existing_type=sa.String(255), nullable=False)
    op.drop_column("users", "password_hash")
