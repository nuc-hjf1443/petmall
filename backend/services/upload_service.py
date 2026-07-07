from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from core.errors import bad_request
from settings.config import get_settings


IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
ALLOWED_USAGES = {"product", "adoption", "community", "pet", "general"}


async def save_public_image(upload: UploadFile, user_id: int, usage: str = "general") -> dict[str, str | int]:
    if usage not in ALLOWED_USAGES:
        raise bad_request("Unsupported upload usage")
    if upload.content_type not in IMAGE_TYPES:
        raise bad_request("Only JPG, PNG and WEBP images are supported")

    settings = get_settings()
    limit = settings.max_upload_size_mb * 1024 * 1024
    data = await upload.read(limit + 1)
    if not data or len(data) > limit:
        raise bad_request("Image file is empty or too large")

    expected_extension = IMAGE_TYPES[upload.content_type]
    filename_extension = Path(upload.filename or "").suffix.lower()
    if filename_extension and filename_extension not in IMAGE_TYPES.values():
        raise bad_request("Unsupported image extension")

    directory = settings.public_asset_path / "uploads" / usage / str(user_id)
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{expected_extension}"
    path = directory / filename
    path.write_bytes(data)

    return {
        "file_url": f"/generated/uploads/{usage}/{user_id}/{filename}",
        "mime_type": upload.content_type,
        "file_size": len(data),
    }
