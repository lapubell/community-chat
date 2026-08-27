"""WebSocket hub for real-time fan-out of chat events.

Protocol (JSON):
  client -> server:
    {"type": "ping", "client_id": "optional"}
    {"type": "typing", "channel": "group"}
    {"type": "read", "channel": "dm", "peer_id": 2, "up_to_id": 42}
  server -> client:
    {"type": "hello", "user_id": 1}
    {"type": "message.new", "channel": "group", "message": {...}}
    {"type": "message.edited", "channel": "group", "message": {...}}
    {"type": "message.deleted", "channel": "group", "message_id": 7}
    {"type": "reaction.changed", "channel": "group", "message_id": 7, "emoji": "👍", "user_ids": [1,2], "count": 2}
    {"type": "dm.new", "channel": "dm", "message": {...}}
    {"type": "dm.read", "channel": "dm", "peer_id": 2, "up_to_id": 42}
    {"type": "typing", "channel": "group|dm", "peer_id": 2}
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket
from sqlalchemy.orm import Session

from .db import SessionLocal, get_db, create_all
from .core.security import decode_access_token
from .models import User

logger = logging.getLogger("chat.ws")


class Hub:
    def __init__(self) -> None:
        self._connections: dict[int, set[WebSocket]] = {}
        self._lock = asyncio.Lock()
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        logger.info("WebSocket hub started")

    async def stop(self) -> None:
        self._running = False
        for sockets in list(self._connections.values()):
            for ws in list(sockets):
                try:
                    await ws.close(code=1001, reason="server shutting down")
                except Exception:
                    pass
        self._connections.clear()
        logger.info("WebSocket hub stopped")

    async def register(self, user_id: int, ws: WebSocket) -> None:
        async with self._lock:
            self._connections.setdefault(user_id, set()).add(ws)

    async def unregister(self, user_id: int, ws: WebSocket) -> None:
        async with self._lock:
            sockets = self._connections.get(user_id)
            if not sockets:
                return
            sockets.discard(ws)
            if not sockets:
                self._connections.pop(user_id, None)

    @property
    def online_user_ids(self) -> set[int]:
        return set(self._connections.keys())

    async def broadcast(self, payload: dict[str, Any], exclude: int | None = None) -> None:
        for user_id, sockets in list(self._connections.items()):
            if user_id == exclude:
                continue
            for ws in list(sockets):
                await self._send(ws, payload)

    async def send_to(self, user_id: int, payload: dict[str, Any]) -> bool:
        sockets = self._connections.get(user_id, set())
        if not sockets:
            return False
        delivered = False
        for ws in list(sockets):
            try:
                await ws.send_text(json.dumps(payload, ensure_ascii=False))
                delivered = True
            except Exception:
                sockets.discard(ws)
                try:
                    await ws.close(code=1006)
                except Exception:
                    pass
        return delivered

    async def _send(self, ws: WebSocket, payload: dict[str, Any]) -> None:
        try:
            await ws.send_text(json.dumps(payload, ensure_ascii=False))
        except Exception:
            pass

    def online_status(self, user_id: int) -> bool:
        return user_id in self._connections


hub = Hub()


async def authenticate_ws(ws: WebSocket, token: str) -> User | None:
    payload = decode_access_token(token)
    db = SessionLocal()
    try:
        user = db.get(User, int(payload.get("sub", 0)))
        if user is None or not user.is_active:
            return None
        return user
    finally:
        db.close()


async def ws_endpoint(ws: WebSocket, token: str = ""):
    user = await authenticate_ws(ws, token)
    if user is None:
        await ws.close(code=1008, reason="unauthorized")
        return

    await ws.accept()
    await hub.register(user.id, ws)
    await ws.send_text(json.dumps({"type": "hello", "user_id": user.id}, ensure_ascii=False))

    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            msg_type = data.get("type")
            if msg_type == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
            elif msg_type == "typing" and data.get("channel") == "group":
                await hub.broadcast(
                    {"type": "typing", "channel": "group", "peer_id": user.id},
                    exclude=user.id,
                )
            elif msg_type == "typing" and data.get("channel") == "dm":
                peer_id = data.get("peer_id")
                if isinstance(peer_id, int):
                    await hub.send_to(peer_id, {"type": "typing", "channel": "dm", "peer_id": user.id})
            elif msg_type == "read" and data.get("channel") == "dm":
                peer_id = data.get("peer_id")
                up_to_id = data.get("up_to_id")
                if isinstance(peer_id, int) and isinstance(up_to_id, int):
                    await hub.send_to(
                        peer_id,
                        {"type": "dm.read", "channel": "dm", "peer_id": user.id, "up_to_id": up_to_id},
                    )
    except Exception as exc:
        logger.debug("websocket error for user %s: %s", user.id, exc)
    finally:
        await hub.unregister(user.id, ws)


def ensure_schema() -> None:
    create_all()
