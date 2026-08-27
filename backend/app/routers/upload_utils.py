"""Shared file-upload helpers.

Used by the general files router and the family-avatar endpoint. Files are
stored flat under UPLOAD_DIR with a collision-safe name and served from
/uploads/<storage_name>.
"""
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, UploadFile

# Single source of truth for where uploaded files live. main.py imports this
# so the write path and the /uploads serve path always agree.
UPLOAD_DIR = Path(
    os.environ.get(
        "UPLOAD_DIR",
        str(Path(__file__).resolve().parent.parent.parent / "uploads"),
    )
)

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB

# Families only allow images (this is an avatar). The general files router has
# its own broader allow-list; this one is image-only.
IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/avif",
}


def public_url(filename: str) -> str:
    return f"/uploads/{filename}"


def _storage_name(prefix: str, ext: str = "") -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    return f"{prefix}-{timestamp}-{secrets.token_hex(6)}{ext}"


async def save_upload(
    file: UploadFile,
    *,
    prefix: str,
    allowed_content_types: set[str],
    max_size: int = MAX_UPLOAD_SIZE,
) -> tuple[str, int]:
    """Persist an uploaded file.

    Validates content type and size, writes to disk, and returns
    (storage_name, size). The caller decides how to reference it (via
    public_url) and is responsible for deleting the old file when replacing
    (see delete_file).
    """
    if file.content_type not in allowed_content_types:
        raise HTTPException(status_code=415, detail="Unsupported file type")

    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")

    ext = ""
    if file.filename and "." in file.filename:
        ext = "." + file.filename.rsplit(".", 1)[-1].lower()
    storage_name = _storage_name(prefix, ext)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOAD_DIR / storage_name).write_bytes(content)
    return storage_name, len(content)


def delete_file(public_file_url: str | None) -> None:
    """Delete a previously uploaded file from disk (best-effort)."""
    if not public_file_url:
        return
    filename = public_file_url.rsplit("/", 1)[-1]
    if not filename:
        return
    path = (UPLOAD_DIR / filename).resolve()
    if UPLOAD_DIR.resolve() not in path.parents:
        return
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass
