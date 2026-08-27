import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy import select

from ..db import get_db
from ..models import File as FileModel, User
from ..core.security import get_current_user

router = APIRouter()

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", str(Path(__file__).resolve().parent.parent.parent / "uploads")))
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/svg+xml",
    "image/avif",
    "video/mp4",
    "video/webm",
    "text/plain",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def public_url(filename: str) -> str:
    return f"/uploads/{filename}"


@router.get("/me")
async def my_files(user: User = Depends(get_current_user), db=Depends(get_db)):
    rows = db.execute(select(FileModel).where(FileModel.owner_id == user.id).order_by(FileModel.created_at.desc())).scalars().all()
    return [
        {
            "id": f.id,
            "filename": f.filename,
            "content_type": f.content_type,
            "size": f.size,
            "url": public_url(f.storage_name),
            "created_at": f.created_at.isoformat(),
        }
        for f in rows
    ]


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported file type")

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    ext = ""
    if file.filename and "." in file.filename:
        ext = "." + file.filename.rsplit(".", 1)[-1].lower()
    storage_name = f"{user.id}-{timestamp}-{secrets.token_hex(6)}{ext}"
    (UPLOAD_DIR / storage_name).write_bytes(content)

    record = FileModel(
        owner_id=user.id,
        filename=file.filename or "file",
        storage_name=storage_name,
        content_type=file.content_type,
        size=len(content),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {
        "id": record.id,
        "filename": record.filename,
        "content_type": record.content_type,
        "size": record.size,
        "url": public_url(storage_name),
    }


@router.delete("/{file_id}")
async def delete_file(
    file_id: int,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    record = db.get(FileModel, file_id)
    if record is None or record.owner_id != user.id:
        raise HTTPException(status_code=404, detail="File not found")
    path = UPLOAD_DIR / record.storage_name
    if path.exists():
        path.unlink()
    db.delete(record)
    db.commit()
    return {"ok": True}
