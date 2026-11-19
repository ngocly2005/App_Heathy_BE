"""Seed 100 foods with local photos and give the five original foods photos.

Nutrition is per 100 g from USDA FNDDS 2019-2020 or SR Legacy 2018.
Existing food IDs and user edits are preserved.
"""

import json
from pathlib import Path

from alembic import op
import sqlalchemy as sa


revision = "20261119_0015"
down_revision = "20261119_0014"
branch_labels = None
depends_on = None


ORIGINAL_PHOTOS = {
    "Cooked chicken breast": "f33842a2ef52316056a6a85b2558bcd1.jpg",
    "Cooked white rice": "91c01ca82680df08fde14ffd87c65e41.jpg",
    "Boiled egg": "72c452cacedcc2d0b04f8fccdeac1181.jpg",
    "Banana": "e6f9c347672daae5a2557ae118f44a1e.jpg",
    "Apple": "9f6290f4436e5a2351f12e03b6433c3c.jpg",
}


def upgrade() -> None:
    foods = sa.table(
        "foods",
        sa.column("name", sa.String(160)),
        sa.column("calories_per_100g", sa.Numeric(8, 2)),
        sa.column("protein_per_100g", sa.Numeric(8, 2)),
        sa.column("carb_per_100g", sa.Numeric(8, 2)),
        sa.column("fat_per_100g", sa.Numeric(8, 2)),
        sa.column("is_active", sa.Boolean()),
        sa.column("image_filename", sa.String(80)),
    )
    catalog_path = Path(__file__).resolve().parents[2] / "app" / "data" / "food_catalog_100.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    existing = set(op.get_bind().execute(sa.select(foods.c.name)).scalars())
    rows = [
        {key: row[key] for key in (
            "name", "calories_per_100g", "protein_per_100g", "carb_per_100g",
            "fat_per_100g", "image_filename",
        )} | {"is_active": True}
        for row in catalog if row["name"] not in existing
    ]
    if rows:
        op.bulk_insert(foods, rows)

    # An admin-uploaded photo takes precedence over a bundled photo.
    for name, filename in ORIGINAL_PHOTOS.items():
        op.get_bind().execute(
            foods.update()
            .where(foods.c.name == name, foods.c.image_filename.is_(None))
            .values(image_filename=filename)
        )


def downgrade() -> None:
    # Do not remove catalog records: saved meals and food logs can reference
    # them, and admins may have changed their data after upgrade.
    pass
