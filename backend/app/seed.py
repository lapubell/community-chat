"""Idempotent database seeder.

Creates the initial admin user on first boot so the app can be joined via
invites only. Subsequent runs are no-ops (never overwrites an existing admin).

Configuration (all optional, via environment):
  ADMIN_HANDLE   -- admin username, default "admin"
  ADMIN_PASSWORD -- admin password. If unset, a random one is generated and
                    printed to the log exactly once (when the admin is created).
  ADMIN_NAME     -- admin display name, default "Admin"
"""
import logging
import secrets
import string

from .db import Base, SessionLocal, engine
from .core.security import hash_password
from .models import User

logger = logging.getLogger("chat.seed")

ALPHABET = string.ascii_uppercase + string.digits


def generate_password(length: int = 16) -> str:
    return "".join(secrets.choice(ALPHABET + string.ascii_lowercase) for _ in range(length))


def seed_admin() -> None:
    """Create tables and the admin user if it doesn't already exist."""
    Base.metadata.create_all(engine)

    import os

    handle = os.environ.get("ADMIN_HANDLE", "admin").strip().lower()
    password = os.environ.get("ADMIN_PASSWORD", "").strip()
    display_name = os.environ.get("ADMIN_NAME", "Admin").strip() or "Admin"
    generated = False
    if not password:
        password = generate_password()
        generated = True

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.handle == handle).first()
        if existing is not None:
            logger.info("Admin '%s' already exists, skipping seed", handle)
            return

        admin = User(
            handle=handle,
            password_hash=hash_password(password),
            display_name=display_name,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        logger.info("Seeded admin user '%s'", handle)
        if generated:
            logger.warning(
                "Generated admin password: %s (set ADMIN_PASSWORD to avoid this)",
                password,
            )
    finally:
        db.close()
