"""Authenticated food photos on this server's local filesystem."""

from io import BytesIO
import logging
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image, ImageOps

from app.core.config import get_settings
from app.core.images import validate_image
from app.dependencies import AdminUser, CurrentUser, DbSession
from app.models import Food, UserFood

router = APIRouter(tags=["food images"])


def media_root() -> Path:
    return Path(get_settings().food_media_dir).resolve()


def image_path(filename: str) -> Path:
    # Database values are generated UUID names, never client-supplied paths.
    if len(filename) != 36 or not filename.endswith(".jpg") or any(c not in "0123456789abcdef" for c in filename[:-4]):
        raise HTTPException(status_code=404, detail="Food image not found")
    return media_root() / filename


def remove_image(filename: str) -> None:
    try:
        image_path(filename).unlink(missing_ok=True)
    except OSError:
        # The database mutation already committed; an orphan file can be cleaned later.
        logging.warning("Could not remove an old food image")


def store_image(upload: UploadFile) -> str:
    max_bytes = get_settings().max_image_size_mb * 1024 * 1024
    try:
        raw = upload.file.read(max_bytes + 1)
    finally:
        upload.file.close()
    if len(raw) > max_bytes:
        raise HTTPException(status_code=413, detail="Food image is too large")
    validate_image(raw, upload.content_type)
    with Image.open(BytesIO(raw)) as original:
        photo = ImageOps.exif_transpose(original).convert("RGB")
        photo.thumbnail((1280, 1280))
        output = BytesIO()
        photo.save(output, format="JPEG", quality=85, optimize=True)
    filename = uuid4().hex + ".jpg"
    root = media_root()
    root.mkdir(parents=True, exist_ok=True)
    temporary = root / (filename + ".tmp")
    try:
        temporary.write_bytes(output.getvalue())
        temporary.replace(root / filename)
    finally:
        temporary.unlink(missing_ok=True)
    return filename


def replace_image(db: DbSession, row: Food | UserFood, upload: UploadFile) -> dict[str, bool]:
    new_filename = store_image(upload)
    old_filename = row.image_filename
    row.image_filename = new_filename
    try:
        db.commit()
    except Exception:
        db.rollback()
        remove_image(new_filename)
        raise
    if old_filename:
        remove_image(old_filename)
    return {"has_image": True}


def get_custom(db: DbSession, food_id: int, user_id: int) -> UserFood:
    row = db.get(UserFood, food_id)
    if row is None or row.user_id != user_id:
        raise HTTPException(status_code=404, detail="Food image not found")
    return row


def get_catalog(db: DbSession, food_id: int) -> Food:
    row = db.get(Food, food_id)
    if row is None or not row.is_active:
        raise HTTPException(status_code=404, detail="Food image not found")
    return row


def serve(row: Food | UserFood) -> FileResponse:
    if not row.image_filename:
        raise HTTPException(status_code=404, detail="Food image not found")
    path = image_path(row.image_filename)
    if not path.is_file() and isinstance(row, Food):
        path = Path(__file__).resolve().parent / "assets" / "food_catalog" / row.image_filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Food image not found")
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "private, no-store"})


@router.get("/foods/{food_id}/image")
def catalog_image(food_id: int, current_user: CurrentUser, db: DbSession):
    return serve(get_catalog(db, food_id))


@router.put("/admin/foods/{food_id}/image")
def upload_catalog_image(food_id: int, current_user: AdminUser, db: DbSession, image: UploadFile = File(...)):
    return replace_image(db, get_catalog(db, food_id), image)


@router.get("/custom-foods/{food_id}/image")
def custom_image(food_id: int, current_user: CurrentUser, db: DbSession):
    return serve(get_custom(db, food_id, current_user.id))


@router.put("/custom-foods/{food_id}/image")
def upload_custom_image(food_id: int, current_user: CurrentUser, db: DbSession, image: UploadFile = File(...)):
    return replace_image(db, get_custom(db, food_id, current_user.id), image)


@router.delete("/custom-foods/{food_id}/image", status_code=status.HTTP_204_NO_CONTENT)
def delete_custom_image(food_id: int, current_user: CurrentUser, db: DbSession):
    row = get_custom(db, food_id, current_user.id)
    filename = row.image_filename
    row.image_filename = None
    db.commit()
    if filename:
        remove_image(filename)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
