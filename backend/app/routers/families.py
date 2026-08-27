from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from ..db import get_db
from ..models import Family, User
from ..core.security import get_current_user

router = APIRouter()


class FamilyOut(BaseModel):
    id: int
    name: str
    description: str | None
    member_count: int
    created_at: str


class FamilyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=280)


class FamilyUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=280)


def serialize(db, family: Family) -> FamilyOut:
    members = db.query(User).filter(User.family_id == family.id, User.is_active == True).count()
    return FamilyOut(
        id=family.id,
        name=family.name,
        description=family.description,
        member_count=members,
        created_at=family.created_at.isoformat(),
    )


@router.get("", response_model=list[FamilyOut])
async def list_families(
    user: User = Depends(get_current_user), db=Depends(get_db)
):
    rows = db.execute(select(Family).order_by(Family.name)).scalars().all()
    return [serialize(db, f) for f in rows]


@router.post("", response_model=FamilyOut, status_code=201)
async def create_family(
    req: FamilyCreateRequest,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    name = req.name.strip()
    existing = db.execute(select(Family).where(Family.name == name)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="A family with that name already exists")

    family = Family(name=name, description=req.description, created_by=user.id)
    db.add(family)
    db.commit()
    db.refresh(family)
    return serialize(db, family)


@router.put("/{family_id}", response_model=FamilyOut)
async def update_family(
    family_id: int,
    req: FamilyUpdateRequest,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    family = db.get(Family, family_id)
    if family is None:
        raise HTTPException(status_code=404, detail="Family not found")

    if req.name is not None:
        name = req.name.strip()
        clash = db.execute(
            select(Family).where(Family.name == name, Family.id != family_id)
        ).scalar_one_or_none()
        if clash is not None:
            raise HTTPException(status_code=409, detail="A family with that name already exists")
        family.name = name
    if req.description is not None:
        family.description = req.description
    db.commit()
    db.refresh(family)
    return serialize(db, family)


@router.delete("/{family_id}")
async def delete_family(
    family_id: int,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    family = db.get(Family, family_id)
    if family is None:
        raise HTTPException(status_code=404, detail="Family not found")

    members = db.query(User).filter(User.family_id == family_id).count()
    if members > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete: {members} member(s) are still in this family",
        )

    # Unassign any pending invites pointing at this family.
    from ..models import Invite

    for inv in db.execute(select(Invite).where(Invite.family_id == family_id)).scalars().all():
        inv.family_id = None

    db.delete(family)
    db.commit()
    return {"ok": True}
