"""Signed subscriber sessions backed by the existing subscriber store.

PostgreSQL deployments persist accounts and account-wide session revocation.
Logout advances the subscriber's existing updated_at revision, invalidating all
sessions for that account without adding a session table. Preview mode remains
process-local; it is not evidence of durable authentication.

Cookies expire on the server as well as in the browser. Every request reads the
current subscriber and tier, and legacy cookies without lifecycle claims are
refused. No password hash or database revision is exposed in a cookie.
"""

from __future__ import annotations

import hmac
import json
import os
import time
from base64 import b64decode, urlsafe_b64encode
from dataclasses import dataclass, field
from hashlib import sha256

from fastapi import Cookie, HTTPException, Response

from cedar_press import subscribers

COOKIE = "cedar_press_session"
MAX_AGE = 60 * 60 * 24 * 14
_CLOCK_SKEW = 60
_SECRET = os.environ.get("CEDAR_PRESS_SECRET") or os.urandom(32).hex()


@dataclass(frozen=True)
class Session:
    email: str
    tier: str
    revision: str = field(default="", compare=False, repr=False)

    def as_payload(self) -> dict[str, object]:
        return {"email": self.email, "workspace_tier": self.tier}


def account_id_for(email: str) -> str:
    return subscribers.account_id_for(email)


def account_exists(email: str) -> bool:
    return subscribers.exists(email)


def create_account(email: str, password: str, tier: str) -> Session:
    """Internal activation helper; the caller must already verify its code."""
    made = subscribers.create(email, password, tier)
    return _issued_session(made.email)


def forget_activated_for_tests() -> None:
    subscribers.forget_activated_for_tests()


def validate_auth_configuration() -> None:
    """Reject ephemeral authentication for staging/production before use."""
    environment = os.environ.get("CEDAR_PRESS_ENVIRONMENT", "development")
    if environment == "development":
        return
    configured_secret = os.environ.get("CEDAR_PRESS_SECRET", "")
    database = os.environ.get("DATABASE_URL", "").strip()
    if (
        environment not in {"staging", "production"}
        or len(configured_secret) < 32
        or not hmac.compare_digest(configured_secret.encode("utf-8"), _SECRET.encode("utf-8"))
        or not database.startswith(("postgresql://", "postgres://"))
        or os.environ.get("CEDAR_PRESS_INSECURE_COOKIE") == "1"
        or bool(os.environ.get("CEDAR_PRESS_ACCOUNTS", "").strip())
    ):
        raise HTTPException(
            status_code=503,
            detail={
                "code": "AUTH_CONFIGURATION_REQUIRED",
                "message": "Sign-in is temporarily unavailable.",
            },
        )


def _revision(subscriber: subscribers.Subscriber) -> str:
    # Password and account changes invalidate a token even if an external
    # account writer forgot to advance updated_at. The tier is read afresh,
    # never trusted from the cookie; unversioned downgrades apply immediately.
    material = json.dumps(
        [
            "cedar-press-account-session-v2",
            subscriber.email,
            subscriber.account_id,
            subscriber.password_hash,
            subscriber.session_revision,
        ],
        separators=(",", ":"),
    ).encode("utf-8")
    return hmac.new(_SECRET.encode("utf-8"), material, sha256).hexdigest()


def _issued_session(email: str) -> Session:
    found = subscribers.find(email)
    if found is None or found.tier not in subscribers.TIERS:
        raise ValueError("Subscriber is no longer available")
    return Session(found.email, found.tier, _revision(found))


def _lookup(email: str, password: str) -> Session | None:
    validate_auth_configuration()
    found = subscribers.authenticate(email, password)
    if found is None:
        return None
    # Linking updates the subscriber revision. It must finish before issuing
    # the token, not after the login route has already set its cookie.
    subscribers.link_platform_account(found.email)
    current = subscribers.find(found.email)
    if (
        current is None
        or current.tier not in subscribers.TIERS
        or current.password_hash != found.password_hash
    ):
        # A password reset racing the link step must not bless an old password
        # with the new revision. A later revision change invalidates normally.
        return None
    return Session(current.email, current.tier, _revision(current))


def _sign(payload: bytes) -> str:
    digest = hmac.new(_SECRET.encode("utf-8"), payload, sha256).digest()
    return urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _encode(session: Session) -> str:
    if not session.revision:
        # Internal trusted issuance helpers still resolve the actual account.
        session = _issued_session(session.email)
    issued = int(time.time())
    payload = json.dumps(
        {
            "v": 2,
            "email": session.email,
            "iat": issued,
            "exp": issued + MAX_AGE,
            "rev": session.revision,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    body = urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    return f"{body}.{_sign(payload)}"


def _decode(value: str) -> Session | None:
    if not isinstance(value, str) or len(value) > 4096:
        return None
    try:
        body, signature = value.split(".", 1)
        payload = b64decode(body + "=" * (-len(body) % 4), altchars=b"-_", validate=True)
        if not hmac.compare_digest(_sign(payload), signature):
            return None
        parsed = json.loads(payload)
    except (ValueError, TypeError, UnicodeError):
        return None
    if not isinstance(parsed, dict) or type(parsed.get("v")) is not int or parsed["v"] != 2:
        return None
    email, issued, expires, revision = (
        parsed.get("email"),
        parsed.get("iat"),
        parsed.get("exp"),
        parsed.get("rev"),
    )
    if (
        not isinstance(email, str)
        or not email
        or email != email.strip().lower()
        or type(issued) is not int
        or type(expires) is not int
        or not isinstance(revision, str)
        or len(revision) != 64
        or not revision.isascii()
    ):
        return None
    now = int(time.time())
    if issued > now + _CLOCK_SKEW or expires - issued != MAX_AGE or now >= expires:
        return None
    found = subscribers.find(email)
    if found is None or found.tier not in subscribers.TIERS:
        return None
    if not hmac.compare_digest(_revision(found), revision):
        return None
    return Session(found.email, found.tier, revision)


def current_session(cedar_press_session: str | None = Cookie(default=None)) -> Session | None:
    """Current subscriber and entitlement; malformed/expired sessions refuse."""
    validate_auth_configuration()
    return _decode(cedar_press_session) if cedar_press_session else None


def issue(session: Session, response: Response) -> Session:
    """Internal trusted issuance; authentication belongs to the caller."""
    validate_auth_configuration()
    if not session.revision:
        session = _issued_session(session.email)
    _set_cookie(session, response)
    return session


def sign_in(email: str, password: str, response: Response) -> Session | None:
    session = _lookup(email, password)
    if session is None:
        return None
    _set_cookie(session, response)
    return session


def _set_cookie(session: Session, response: Response) -> None:
    secure = os.environ.get("CEDAR_PRESS_INSECURE_COOKIE") != "1"
    response.set_cookie(
        COOKIE,
        _encode(session),
        max_age=MAX_AGE,
        httponly=True,
        secure=secure,
        samesite="none" if secure else "lax",
        path="/",
    )


def sign_out(response: Response, session: Session | None = None) -> None:
    """Sign out this subscriber on every device; invalid cookies only clear."""
    if session is not None:
        subscribers.revoke_sessions(session.email)
    secure = os.environ.get("CEDAR_PRESS_INSECURE_COOKIE") != "1"
    response.delete_cookie(
        COOKIE,
        path="/",
        httponly=True,
        secure=secure,
        samesite="none" if secure else "lax",
    )
