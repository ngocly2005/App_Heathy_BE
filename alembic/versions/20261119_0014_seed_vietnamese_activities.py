"""Add the exercise names supplied in the activity workbook.

Revision ID: 20261119_0014
Revises: 20261117_0013

METs use a representative adult intensity from the 2024 Adult Compendium of
Physical Activities (https://pacompendium.com/adult-compendium/). Pickleball
uses the measured recreational mean of 4.1 METs (Smith et al., 2018,
https://ijrep.org/wp-content/uploads/lana-downloads/2018/06/smith.et_.al_.spring.2018.pdf).
These are estimates; actual expenditure depends on effort and the individual.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20261119_0014"
down_revision: str | None = "20261117_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# The workbook has 27 rows but repeats swimming and cycling. Catalog names
# are unique; each repeated activity therefore has one entry.
ACTIVITIES = (
    ("Bài tập thể chất", 3.8),
    ("Bơi lội", 6.0),
    ("Đạp xe", 7.0),
    ("Đi bộ", 3.5),
    ("Chạy bộ", 8.5),
    ("Tập tạ", 3.5),
    ("Thể dục dụng cụ", 3.8),
    ("Bowling", 3.8),
    ("Bóng đá trong nhà", 7.8),
    ("Bóng chày", 5.0),
    ("Bóng đá", 7.0),
    ("Bắn cung", 4.3),
    ("Bóng rổ", 7.5),
    ("Bóng chuyền", 4.0),
    ("Bóng bàn", 4.0),
    ("Cử tạ", 6.0),
    ("Cầu lông", 5.5),
    ("Đấu vật", 6.0),
    ("Golf", 4.5),
    ("Nhảy dây", 11.0),
    ("Pilates", 2.8),
    ("Pickleball", 4.1),
    ("Quần vợt", 6.8),
    ("Quyền anh", 7.8),
    ("Yoga", 2.3),
)


def upgrade() -> None:
    table = sa.table(
        "activity_types",
        sa.column("name", sa.String(120)),
        sa.column("met", sa.Numeric(5, 2)),
        sa.column("is_active", sa.Boolean()),
    )
    existing = set(op.get_bind().execute(sa.select(table.c.name)).scalars())
    rows = [
        {"name": name, "met": met, "is_active": True}
        for name, met in ACTIVITIES if name not in existing
    ]
    if rows:
        op.bulk_insert(table, rows)
    # The initial English seed names represent the same four activities.
    # Keep their IDs for existing logs, but omit them from the user catalog.
    op.get_bind().execute(
        table.update().where(table.c.name.in_(("Walking", "Running", "Cycling", "Swimming")))
        .values(is_active=False)
    )


def downgrade() -> None:
    # Keep catalog records on downgrade: users and admins may have edited or
    # referenced them after this migration, and deleting them loses data.
    table = sa.table(
        "activity_types",
        sa.column("name", sa.String(120)),
        sa.column("is_active", sa.Boolean()),
    )
    op.get_bind().execute(
        table.update().where(table.c.name.in_(("Walking", "Running", "Cycling", "Swimming")))
        .values(is_active=True)
    )
