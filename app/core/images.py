import warnings
from io import BytesIO

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

IMAGE_TYPES = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


def validate_image(data: bytes, declared_type: str | None) -> str:
    if not data or declared_type not in IMAGE_TYPES.values():
        raise HTTPException(status_code=422, detail="Upload a JPEG, PNG or WebP image")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                detected_type = IMAGE_TYPES.get(image.format)
                if detected_type != declared_type:
                    raise ValueError("Image format does not match Content-Type")
                if image.width * image.height > 25_000_000:
                    raise ValueError("Image has too many pixels")
                if getattr(image, "n_frames", 1) != 1:
                    raise ValueError("Upload a single-frame image")
                image.load()
    except (
        UnidentifiedImageError, OSError, ValueError,
        Image.DecompressionBombWarning, Image.DecompressionBombError,
    ) as error:
        raise HTTPException(status_code=422, detail="Invalid or oversized image") from error
    return detected_type
