"""Push notification tests.

We don't hit a real push service; instead we monkeypatch pywebpush.webpush to
record the (subscription, payload) pairs it would have sent. VAPID keys are
set for the test process so push_enabled() is true.

The fan-out functions are tested directly (synchronously) to avoid the
background-task timing issues of the HTTP layer.
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ["VAPID_PRIVATE_KEY"] = "test-private-key"
os.environ["VAPID_PUBLIC_KEY"] = "test-public-key"
os.environ["VAPID_EMAIL"] = "mailto:test@example.com"

_tmp = tempfile.mkdtemp(prefix="chat-push-test-")
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["DATA_DIR"] = _tmp
os.environ["UPLOAD_DIR"] = os.path.join(_tmp, "uploads")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.models import PushSubscription, User  # noqa: E402
from app.routers import push as push_mod  # noqa: E402

import pywebpush  # noqa: E402


def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return TestClient(app)


def auth(tok):
    return {"Authorization": f"Bearer {tok}"}


def _sub(endpoint, p256dh="pk", authk="ak"):
    return {"endpoint": endpoint, "keys": {"p256dh": p256dh, "auth": authk}}


def _make_user(c: TestClient, handle: str) -> dict:
    db = SessionLocal()
    from app.models import Invite

    inv = Invite(code="PUSH" + handle, max_uses=5, times_used=0)
    db.add(inv)
    db.commit()
    db.close()
    r = c.post(
        "/api/auth/register",
        json={
            "invite_code": "PUSH" + handle,
            "handle": handle,
            "password": "secret123",
            "display_name": handle.title(),
        },
    )
    assert r.status_code in (200, 201), r.text
    return r.json()


def test_push_key():
    c = client()
    info = _make_user(c, "kate1")
    r = c.get("/api/push/key", headers=auth(info["token"]))
    assert r.status_code == 200
    assert r.json()["public_key"] == "test-public-key"


def test_subscribe_and_unsubscribe():
    c = client()
    info = _make_user(c, "kate2")
    tok = info["token"]
    uid = info["user"]["id"]

    r = c.post("/api/push/subscribe", headers=auth(tok), json=_sub("https://push.example/1"))
    assert r.status_code == 201, r.text
    db = SessionLocal()
    n = db.query(PushSubscription).filter_by(user_id=uid).count()
    db.close()
    assert n == 1

    # Idempotent re-subscribe of the same endpoint.
    r = c.post("/api/push/subscribe", headers=auth(tok), json=_sub("https://push.example/1"))
    assert r.status_code == 201
    db = SessionLocal()
    n = db.query(PushSubscription).filter_by(user_id=uid).count()
    db.close()
    assert n == 1

    # Different endpoint -> second row.
    c.post("/api/push/subscribe", headers=auth(tok), json=_sub("https://push.example/2"))
    db = SessionLocal()
    n = db.query(PushSubscription).filter_by(user_id=uid).count()
    db.close()
    assert n == 2

    # Unsubscribe one.
    r = c.delete("/api/push/subscribe?endpoint=https://push.example/1", headers=auth(tok))
    assert r.status_code == 200
    assert r.json()["removed"] is True
    db = SessionLocal()
    n = db.query(PushSubscription).filter_by(user_id=uid).count()
    db.close()
    assert n == 1


def test_deliver_to_user(monkeypatch):
    sent: list[dict] = []

    def fake_webpush(subscription_info, data, **kw):
        sent.append({"endpoint": subscription_info["endpoint"], "data": data})
        return "ok"

    monkeypatch.setattr(pywebpush, "webpush", fake_webpush)

    c = client()
    info = _make_user(c, "dana1")
    uid = info["user"]["id"]
    c.post("/api/push/subscribe", headers=auth(info["token"]), json=_sub("https://push.example/x1"))
    c.post("/api/push/subscribe", headers=auth(info["token"]), json=_sub("https://push.example/x2"))

    db = SessionLocal()
    count = push_mod.deliver_to_user(db, uid, {"title": "T", "body": "B"})
    db.close()

    assert count == 2
    assert {s["endpoint"] for s in sent} == {"https://push.example/x1", "https://push.example/x2"}


def test_notify_group_skips_sender(monkeypatch):
    sent: list[str] = []

    def fake_webpush(subscription_info, data, **kw):
        sent.append(subscription_info["endpoint"])
        return "ok"

    monkeypatch.setattr(pywebpush, "webpush", fake_webpush)

    c = client()
    a = _make_user(c, "greg1")
    b = _make_user(c, "gina2")
    a_uid, b_uid = a["user"]["id"], b["user"]["id"]
    c.post("/api/push/subscribe", headers=auth(a["token"]), json=_sub("https://push.example/a"))
    c.post("/api/push/subscribe", headers=auth(b["token"]), json=_sub("https://push.example/b"))

    db = SessionLocal()
    push_mod.notify_group(db, a_uid, {"title": "T", "body": "B"})
    db.close()

    assert "https://push.example/b" in sent
    assert "https://push.example/a" not in sent


def test_notify_room_skips_sender(monkeypatch):
    sent: list[str] = []

    def fake_webpush(subscription_info, data, **kw):
        sent.append(subscription_info["endpoint"])
        return "ok"

    monkeypatch.setattr(pywebpush, "webpush", fake_webpush)

    c = client()
    a = _make_user(c, "ravi1")
    b = _make_user(c, "rita2")
    a_uid, b_uid = a["user"]["id"], b["user"]["id"]
    c.post("/api/push/subscribe", headers=auth(a["token"]), json=_sub("https://push.example/a"))
    c.post("/api/push/subscribe", headers=auth(b["token"]), json=_sub("https://push.example/b"))

    db = SessionLocal()
    push_mod.notify_room(db, {a_uid, b_uid}, a_uid, {"title": "T", "body": "B"})
    db.close()

    assert "https://push.example/b" in sent
    assert "https://push.example/a" not in sent


def test_disabled_without_private_key(monkeypatch):
    monkeypatch.delenv("VAPID_PRIVATE_KEY", raising=False)
    c = client()
    info = _make_user(c, "omar1")
    r = c.get("/api/push/key", headers=auth(info["token"]))
    assert r.status_code == 503
    # Subscribing is also refused.
    r = c.post("/api/push/subscribe", headers=auth(info["token"]), json=_sub("https://push.example/zz"))
    assert r.status_code == 503
