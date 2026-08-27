import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, or_, select

from ..db import get_db
from ..models import DirectMessage, User
from ..core.security import get_current_user
from ..ws import hub

router = APIRouter()


def dm_payload(db, msg: DirectMessage) -> dict:
    return {
        "id": msg.id,
        "sender": {
            "id": msg.sender.id,
            "handle": msg.sender.handle,
            "display_name": msg.sender.display_name or msg.sender.handle,
            "avatar_url": msg.sender.avatar_url,
        },
        "recipient_id": msg.recipient_id,
        "text": msg.text,
        "file_url": msg.file_url,
        "file_name": msg.file_name,
        "file_content_type": msg.file_content_type,
        "read_at": msg.read_at.isoformat() if msg.read_at else None,
        "created_at": msg.created_at.isoformat(),
        "reactions": dm_reactions(db, msg.id),
    }


def dm_reactions(db, dm_message_id: int) -> list[dict]:
    from ..models import Reaction

    rows = (
        db.execute(
            select(Reaction, User)
            .where(Reaction.dm_message_id == dm_message_id)
            .join(User, Reaction.user_id == User.id)
        )
        .all()
    )
    grouped: dict[str, list[int]] = {}
    for reaction, author in rows:
        grouped.setdefault(reaction.emoji, []).append(author.id)
    return [
        {"emoji": emoji, "user_ids": uids, "count": len(uids)}
        for emoji, uids in grouped.items()
    ]


@router.get("/conversations")
async def conversations(user: User = Depends(get_current_user), db=Depends(get_db)):
    peer_id_expr = case(
        (DirectMessage.sender_id == user.id, DirectMessage.recipient_id),
        else_=DirectMessage.sender_id,
    )
    subq = (
        select(
            peer_id_expr.label("peer_id"),
            func.max(DirectMessage.id).label("last_id"),
            func.max(DirectMessage.created_at).label("last_at"),
        )
        .where(
            or_(
                DirectMessage.sender_id == user.id,
                DirectMessage.recipient_id == user.id,
            )
        )
        .group_by(peer_id_expr)
        .subquery()
    )
    rows = db.execute(select(subq)).all()

    unread_counts = dict(
        db.execute(
            select(DirectMessage.recipient_id, func.count(DirectMessage.id))
            .where(DirectMessage.recipient_id == user.id, DirectMessage.read_at.is_(None))
            .group_by(DirectMessage.recipient_id)
        )
        .all()
    )

    result = []
    for row in rows:
        other = db.get(User, row.peer_id)
        if other is None or not other.is_active:
            continue
        last = db.get(DirectMessage, row.last_id)
        result.append(
            {
                "peer": {
                    "id": other.id,
                    "handle": other.handle,
                    "display_name": other.display_name or other.handle,
                    "avatar_url": other.avatar_url,
                },
                "last_message": dm_payload(db, last) if last else None,
                "unread_count": unread_counts.get(other.id, 0),
                "last_at": row.last_at.isoformat() if row.last_at else None,
            }
        )
    result.sort(key=lambda c: c["last_at"] or "", reverse=True)
    return result


@router.get("/with/{user_id}")
async def history_with(
    user_id: int,
    before_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")

    query = (
        select(DirectMessage)
        .where(
            or_(
                (DirectMessage.sender_id == user.id) & (DirectMessage.recipient_id == user_id),
                (DirectMessage.sender_id == user_id) & (DirectMessage.recipient_id == user.id),
            )
        )
        .order_by(DirectMessage.id.desc())
    )
    if before_id is not None:
        query = query.where(DirectMessage.id < before_id)
    rows = db.execute(query.limit(limit)).scalars().all()
    messages = [dm_payload(db, msg) for msg in rows]
    messages.reverse()

    unread_ids = [
        m.id for m in rows if m.sender_id == user_id and m.read_at is None
    ]
    if unread_ids:
        now = datetime.now(timezone.utc)
        db.execute(
            __import__("sqlalchemy").update(DirectMessage)
            .where(DirectMessage.id.in_(unread_ids))
            .values(read_at=now)
        )
        db.commit()
    return messages


@router.post("/with/{user_id}", status_code=201)
async def send_dm(
    user_id: int,
    data: dict,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    recipient = db.get(User, user_id)
    if recipient is None:
        raise HTTPException(status_code=404, detail="User not found")

    text = (data.get("text") or "").strip()
    if not text and not data.get("file_url"):
        raise HTTPException(status_code=400, detail="Message must contain text or a file")
    if len(text) > 4000:
        raise HTTPException(status_code=400, detail="Message too long (max 4000 chars)")

    msg = DirectMessage(
        sender_id=user.id,
        recipient_id=user_id,
        text=text or None,
        file_url=data.get("file_url"),
        file_name=data.get("file_name"),
        file_content_type=data.get("file_content_type"),
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    payload = dm_payload(db, msg)
    asyncio.get_event_loop().create_task(
        hub.send_to(user_id, {"type": "dm.new", "channel": "dm", "message": payload})
    )
    asyncio.get_event_loop().create_task(
        hub.send_to(user.id, {"type": "dm.new", "channel": "dm", "message": payload})
    )
    return payload


@router.post("/{dm_id}/read")
async def mark_read(
    dm_id: int,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    msg = db.get(DirectMessage, dm_id)
    if msg is None or msg.recipient_id != user.id:
        raise HTTPException(status_code=404, detail="Message not found")
    if msg.read_at is None:
        msg.read_at = datetime.now(timezone.utc)
        db.commit()
    return {"ok": True}


@router.post("/{dm_id}/reactions/{emoji}")
async def add_dm_reaction(
    dm_id: int,
    emoji: str,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    from ..routers.messages import REACTION_EMOJIS

    if emoji not in REACTION_EMOJIS:
        raise HTTPException(status_code=400, detail="Unsupported emoji")
    msg = db.get(DirectMessage, dm_id)
    if msg is None or user.id not in (msg.sender_id, msg.recipient_id):
        raise HTTPException(status_code=404, detail="Message not found")
    from ..models import Reaction

    existing = db.execute(
        select(Reaction).where(
            Reaction.dm_message_id == dm_id,
            Reaction.user_id == user.id,
            Reaction.emoji == emoji,
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(Reaction(emoji=emoji, user_id=user.id, dm_message_id=dm_id))
        db.commit()
    user_ids = [
        r[0]
        for r in db.execute(
            select(Reaction.user_id).where(
                Reaction.dm_message_id == dm_id, Reaction.emoji == emoji
            )
        ).all()
    ]
    asyncio.get_event_loop().create_task(
        hub.broadcast(
            {
                "type": "reaction.changed",
                "channel": "dm",
                "message_id": dm_id,
                "emoji": emoji,
                "user_ids": user_ids,
                "count": len(user_ids),
            }
        )
    )
    return {"emoji": emoji, "user_ids": user_ids, "count": len(user_ids)}


@router.delete("/{dm_id}/reactions/{emoji}")
async def remove_dm_reaction(
    dm_id: int,
    emoji: str,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    from ..models import Reaction

    existing = db.execute(
        select(Reaction).where(
            Reaction.dm_message_id == dm_id,
            Reaction.user_id == user.id,
            Reaction.emoji == emoji,
        )
    ).scalar_one_or_none()
    if existing:
        db.delete(existing)
        db.commit()
    user_ids = [
        r[0]
        for r in db.execute(
            select(Reaction.user_id).where(
                Reaction.dm_message_id == dm_id, Reaction.emoji == emoji
            )
        ).all()
    ]
    asyncio.get_event_loop().create_task(
        hub.broadcast(
            {
                "type": "reaction.changed",
                "channel": "dm",
                "message_id": dm_id,
                "emoji": emoji,
                "user_ids": user_ids,
                "count": len(user_ids),
            }
        )
    )
    return {"emoji": emoji, "removed": existing is not None}
