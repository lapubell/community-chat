"""Verify the SPA static-serving caching strategy.

The app shell (index.html) must never be cached, and hashed build assets
(/assets/*) must be cached immutably. A stale cached index.html is what pins
a user to an old JS/CSS bundle after a deploy.
"""
import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="chat-spa-test-")
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["DATA_DIR"] = _tmp
os.environ["UPLOAD_DIR"] = os.path.join(_tmp, "uploads")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app, FRONTEND_DIR  # noqa: E402
from app.db import Base, engine  # noqa: E402

# The SPA fallback + /assets mount only exist if a built frontend is present.
# In a build artifact this is always true; skip cleanly if not.
_HAS_FRONTEND = (FRONTEND_DIR / "index.html").exists()


def _client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return TestClient(app)


def test_index_html_is_not_cached():
    if not _HAS_FRONTEND:
        return
    c = _client()
    # The root shell and an SPA route both resolve to index.html via the
    # fallback, so both must carry a no-cache Cache-Control.
    for path in ("/", "/members"):
        r = c.get(path)
        assert r.status_code == 200
        assert "no-cache" in r.headers.get("cache-control", ""), (
            path,
            r.headers.get("cache-control"),
        )


def test_spa_route_returns_shell_for_unknown_path():
    if not _HAS_FRONTEND:
        return
    c = _client()
    r = c.get("/some/deep/spa/route")
    assert r.status_code == 200
    # Should be the shell, not a 404, and non-cached.
    body = r.text
    assert "<div id=\"app\"" in body or "index.html" in (r.headers.get("content-type") or "")
    assert "no-cache" in r.headers.get("cache-control", "")


def test_api_prefix_is_not_served_by_spa_fallback():
    c = _client()
    # /api/... and /ws must not be swallowed by the SPA fallback.
    r = c.get("/api/does-not-exist")
    assert r.status_code == 404
    assert r.headers.get("cache-control") is None or "no-cache" not in r.headers.get("cache-control", "")


def test_assets_are_immutable():
    if not _HAS_FRONTEND:
        return
    assets_dir = FRONTEND_DIR / "assets"
    if not assets_dir.exists():
        return
    # Pick a real hashed asset that exists in the build.
    js_files = [f for f in assets_dir.glob("*.js")]
    if not js_files:
        return
    target = js_files[0]
    c = _client()
    r = c.get(f"/assets/{target.name}")
    assert r.status_code == 200
    cc = r.headers.get("cache-control", "")
    assert "immutable" in cc, cc
    assert "max-age=31536000" in cc, cc
