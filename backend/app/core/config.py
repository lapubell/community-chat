"""Environment-driven configuration.

Centralizes the env vars so they're read in one place. Values are optional;
callers get sensible defaults (or None when a feature is disabled).
"""
import os


def vapid_private_key() -> str | None:
    """Base64url VAPID private key (raw P-256 scalar). None disables push."""
    key = os.environ.get("VAPID_PRIVATE_KEY", "").strip()
    return key or None


def vapid_public_key() -> str | None:
    """Base64url VAPID public key (DER SubjectPublicKeyInfo). Exposed to the
    browser for pushManager.subscribe(); not sensitive."""
    key = os.environ.get("VAPID_PUBLIC_KEY", "").strip()
    return key or None


def vapid_email() -> str:
    """The VAPID 'sub' claim. Must look like a contact (email or url)."""
    return os.environ.get("VAPID_EMAIL", "").strip() or "mailto:admin@example.com"


def push_enabled() -> bool:
    """Push notifications require a private key + a public key. Without them
    the subscribe endpoint returns a 503 and sends are skipped."""
    return bool(vapid_private_key() and vapid_public_key())


# Base URL used as the VAPID audience / deep-link origin. In production this
# is set to https://your-domain; locally it's http://localhost:PORT.
def app_origin() -> str:
    return os.environ.get("APP_ORIGIN", "").strip().rstrip("/") or "http://localhost:8983"
