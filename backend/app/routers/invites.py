import secrets
import string

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from ..db import SessionLocal, get_db
from ..models import Invite, User
from ..core.security import get_current_user

router = APIRouter()

ALPHABET = string.ascii_uppercase + string.digits
CODE_LENGTH = 8


class InviteCreateRequest(BaseModel):
    max_uses: int = Field(default=1, ge=1, le=100)
    note: str | None = Field(default=None, max_length=200)


class InviteOut(BaseModel):
    id: int
    code: str
    max_uses: int
    times_used: int
    is_active: bool
    note: str | None
    created_at: str
    used_at: str | None


def generate_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))


def serialize(invite: Invite) -> InviteOut:
    return InviteOut(
        id=invite.id,
        code=invite.code,
        max_uses=invite.max_uses,
        times_used=invite.times_used,
        is_active=invite.used_at is None and invite.times_used < invite.max_uses,
        note=invite.note,
        created_at=invite.created_at.isoformat(),
        used_at=invite.used_at.isoformat() if invite.used_at else None,
    )


@router.get("", response_model=list[InviteOut])
async def list_invites(user: User = Depends(get_current_user), db=Depends(get_db)):
    rows = db.execute(select(Invite).order_by(Invite.created_at.desc())).scalars().all()
    return [serialize(r) for r in rows]


@router.post("", response_model=InviteOut, status_code=201)
async def create_invite(
    req: InviteCreateRequest, user: User = Depends(get_current_user), db=Depends(get_db)
):
    for _ in range(25):
        code = generate_code()
        existing = db.execute(select(Invite).where(Invite.code == code)).scalar_one_or_none()
        if existing is None:
            break
    else:
        raise HTTPException(status_code=500, detail="Could not generate unique invite code")

    invite = Invite(
        code=code,
        max_uses=req.max_uses,
        times_used=0,
        created_by=user.id,
        note=req.note,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return serialize(invite)


@router.delete("/{invite_id}")
async def revoke_invite(
    invite_id: int, user: User = Depends(get_current_user), db=Depends(get_db)
):
    invite = db.get(Invite, invite_id)
    if invite is None:
        raise HTTPException(status_code=404, detail="Invite not found")
    if invite.times_used >= invite.max_uses or invite.used_at is not None:
        db.delete(invite)
    else:
        invite.max_uses = 0
        invite.used_at = invite.created_at
    db.commit()
    return {"ok": True}
