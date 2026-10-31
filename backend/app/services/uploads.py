"""Validated image uploads. Type is decided from the file's bytes, never from its name or header."""
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.errors import AppError

# SVG is deliberately absent: it can carry scripts.
SIGNATURES = (
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"\xff\xd8\xff", "jpg"),
)


def detect_image_type(head: bytes) -> str | None:
    for magic, ext in SIGNATURES:
        if head.startswith(magic):
            return ext
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    return None


def _bad(message: str) -> AppError:
    return AppError(422, "VALIDATION_ERROR", message, {"file": message})


async def save_logo(file: UploadFile) -> str:
    """Returns the stored file name. Raises 422 for a wrong type or an oversized file."""
    settings = get_settings()
    data = await file.read(settings.max_logo_bytes + 1)
    if not data:
        raise _bad("The file is empty.")
    if len(data) > settings.max_logo_bytes:
        raise _bad(f"The logo must be smaller than {settings.max_logo_bytes // (1024 * 1024)} MB.")
    ext = detect_image_type(data[:16])
    if ext is None:
        raise _bad("Upload a PNG, JPG or WEBP image.")
    folder = settings.upload_path / "logos"
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{ext}"
    (folder / name).write_bytes(data)
    return name


def delete_logo(name: str | None) -> None:
    if name:
        path: Path = get_settings().upload_path / "logos" / Path(name).name
        path.unlink(missing_ok=True)
