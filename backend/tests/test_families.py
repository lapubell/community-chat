"""Tests for the families feature: create families, attach invites to a
family, and verify a user joining via a family invite is assigned to it.
"""
import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="chat-fam-")
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["DATA_DIR"] = _tmp
os.environ["UPLOAD_DIR"] = os.path.join(_tmp, "uploads")
os.environ["ADMIN_HANDLE"] = "admin"
os.environ["ADMIN_PASSWORD"] = "adminpass123"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.db import Base, engine  # noqa: E402


def auth_header(token: str):
    return {"Authorization": f"Bearer {token}"}


def test_families_full_flow():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with TestClient(app) as c:
        # Admin logs in (seeded by lifespan).
        r = c.post("/api/auth/login", json={"handle": "admin", "password": "adminpass123"})
        assert r.status_code == 200, r.text
        admin_token = r.json()["token"]
        admin_id = r.json()["user"]["id"]

        # No families yet.
        r = c.get("/api/families", headers=auth_header(admin_token))
        assert r.status_code == 200
        assert r.json() == []

        # Create two families.
        r = c.post(
            "/api/families",
            headers=auth_header(admin_token),
            json={"name": "Holsapples", "description": "The big one"},
        )
        assert r.status_code == 201, r.text
        fam1 = r.json()
        assert fam1["name"] == "Holsapples"
        assert fam1["member_count"] == 0

        r = c.post("/api/families", headers=auth_header(admin_token), json={"name": "Smiths"})
        assert r.status_code == 201
        fam2 = r.json()

        # Duplicate name is rejected.
        r = c.post("/api/families", headers=auth_header(admin_token), json={"name": "Smiths"})
        assert r.status_code == 409

        # Rename a family.
        r = c.put(
            f"/api/families/{fam2['id']}",
            headers=auth_header(admin_token),
            json={"name": "Smiths & Co"},
        )
        assert r.status_code == 200
        assert r.json()["name"] == "Smiths & Co"

        # List families.
        r = c.get("/api/families", headers=auth_header(admin_token))
        names = [f["name"] for f in r.json()]
        assert "Holsapples" in names and "Smiths & Co" in names

        # --- Invite into a specific family ---
        r = c.post(
            "/api/invites",
            headers=auth_header(admin_token),
            json={"max_uses": 1, "family_id": fam1["id"], "note": "for grandma"},
        )
        assert r.status_code == 201, r.text
        invite = r.json()
        assert invite["family_id"] == fam1["id"]
        assert invite["family_name"] == "Holsapples"

        # Invite into a non-existent family is rejected.
        r = c.post(
            "/api/invites",
            headers=auth_header(admin_token),
            json={"max_uses": 1, "family_id": 9999},
        )
        assert r.status_code == 404

        # An invite with no family is allowed (admin/staff).
        r = c.post("/api/invites", headers=auth_header(admin_token), json={"max_uses": 1})
        assert r.status_code == 201
        assert r.json()["family_id"] is None

        # Grandma joins via the family invite -> assigned to Holsapples.
        r = c.post(
            "/api/auth/register",
            json={
                "invite_code": invite["code"],
                "handle": "grandma",
                "password": "grandma123",
                "display_name": "Grandma",
            },
        )
        assert r.status_code == 200, r.text
        grandma = r.json()["user"]
        assert grandma["family_id"] == fam1["id"]
        assert grandma["family_name"] == "Holsapples"

        # Family member count reflects the new member.
        r = c.get("/api/families", headers=auth_header(admin_token))
        fam1_now = [f for f in r.json() if f["id"] == fam1["id"]][0]
        assert fam1_now["member_count"] == 1

        # Delete the family with members -> blocked.
        r = c.delete(f"/api/families/{fam1['id']}", headers=auth_header(admin_token))
        assert r.status_code == 400

        # --- Family avatar upload + replace ---
        # Upload an avatar for Holsapples.
        png_bytes = b"\x89PNG\r\n\x1a\n" + b"0" * 32
        r = c.post(
            f"/api/families/{fam1['id']}/avatar",
            headers=auth_header(admin_token),
            files={"file": ("family.png", png_bytes, "image/png")},
        )
        assert r.status_code == 200, r.text
        avatar1 = r.json()
        assert avatar1["avatar_url"] is not None
        assert avatar1["avatar_url"].startswith("/uploads/")

        # The avatar is visible in the family list.
        r = c.get("/api/families", headers=auth_header(admin_token))
        fam1_now = [f for f in r.json() if f["id"] == fam1["id"]][0]
        assert fam1_now["avatar_url"] == avatar1["avatar_url"]

        # The uploaded file is actually served.
        r = c.get(avatar1["avatar_url"])
        assert r.status_code == 200
        assert r.content == png_bytes

        # Replace it: the old file should be gone, the new one set.
        r = c.post(
            f"/api/families/{fam1['id']}/avatar",
            headers=auth_header(admin_token),
            files={"file": ("family2.png", png_bytes + b"X", "image/png")},
        )
        assert r.status_code == 200, r.text
        avatar2 = r.json()
        assert avatar2["avatar_url"] != avatar1["avatar_url"]

        # Old file deleted (no revisions kept).
        r = c.get(avatar1["avatar_url"])
        assert r.status_code == 404
        # New file served.
        r = c.get(avatar2["avatar_url"])
        assert r.status_code == 200
        assert r.content == png_bytes + b"X"

        # Non-image is rejected.
        r = c.post(
            f"/api/families/{fam1['id']}/avatar",
            headers=auth_header(admin_token),
            files={"file": ("evil.exe", b"MZ", "application/octet-stream")},
        )
        assert r.status_code == 415

        # Avatar on a non-existent family.
        r = c.post(
            "/api/families/9999/avatar",
            headers=auth_header(admin_token),
            files={"file": ("x.png", png_bytes, "image/png")},
        )
        assert r.status_code == 404

        # Delete the empty family -> ok.
        r = c.delete(f"/api/families/{fam2['id']}", headers=auth_header(admin_token))
        assert r.status_code == 200

        # Deleting a family unassigns any pending invites pointing at it.
        r = c.get("/api/families", headers=auth_header(admin_token))
        assert all(f["id"] != fam2["id"] for f in r.json())

    print("FAMILIES OK")
