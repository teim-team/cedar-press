"""Who is signed in.

Subscriptions are sold and renewed by Tribal Business News, so accounts are
provisioned rather than self-served: this verifies a subscriber, it never
creates one. The account list is a stand-in for the subscriber table and is
read from the environment, so no credential is committed to the repository
and a deployment without one authenticates nobody.

The session rides in a signed, HTTP-only cookie. Not browser storage: a token
in storage is a token any script on the page can read, and this service's
readers are exactly the people whose interest in Indian Country's economy is
worth knowing about.

WHAT REPLACES THIS
The subscriber table and the platform's own password hashing. The seam is
``_lookup``: everything else here — the cookie, its flags, the payload shape
the client reads — stays.
"""

from __future__ import annotations

import hmac
import json
import os
from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass
from hashlib import sha256

from fastapi import Cookie, Response

COOKIE = "cedar_press_session"
MAX_AGE = 60 * 60 * 24 * 14

#: Signing key for the session cookie. A deployment without one signs with a
#: value that changes on restart, which invalidates every session rather than
#: silently accepting cookies anyone could forge.
_SECRET = os.environ.get("CEDAR_PRESS_SECRET") or os.urandom(32).hex()


@dataclass(frozen=True)
class Session:
    email: str
    tier: str

    def as_payload(self) -> dict[str, object]:
        """The session as the client reads it.

        ``workspace_tier`` rather than ``tier`` because that is the field
        ``src/workspaceTier.js`` resolves entitlement from, and renaming it
        here would put a translation in every caller.
        """
        return {"email": self.email, "workspace_tier": self.tier}


def _accounts() -> dict[str, tuple[str, str]]:
    """Provisioned subscribers, as ``email -> (password, tier)``.

    From ``CEDAR_PRESS_ACCOUNTS``, a JSON object::

        {"reader@example.org": {"password": "...", "tier": "press"}}

    Empty by default, so a service started without accounts refuses every
    sign-in instead of falling back to something convenient.
    """
    raw = os.environ.get("CEDAR_PRESS_ACCOUNTS", "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    accounts: dict[str, tuple[str, str]] = {}
    for email, record in parsed.items():
        if isinstance(record, dict) and record.get("password"):
            accounts[email.strip().lower()] = (
                str(record["password"]),
                str(record.get("tier", "press")),
            )
    return accounts


#: Accounts created by activation in this process, layered over the ones the
#: environment provisions. In-memory, so they are forgotten on restart — the
#: one behaviour here that must not survive into production, where this is
#: the subscriber table and a row is written in the same transaction that
#: spends the access code.
_activated: dict[str, tuple[str, str]] = {}


def account_exists(email: str) -> bool:
    """Whether an address already has an account, provisioned or activated."""
    key = email.strip().lower()
    return key in _accounts() or key in _activated


def create_account(email: str, password: str, tier: str) -> Session:
    """Create a subscriber. The caller has already verified the access code.

    No entitlement decision is made here: the code carried the tier, and this
    records it. Doing it the other way round — letting a caller name a tier —
    is how an activation route becomes an escalation route.
    """
    key = email.strip().lower()
    _activated[key] = (password, tier)
    return Session(email=key, tier=tier)


def forget_activated_for_tests() -> None:
    """Drop accounts created by activation. Tests only."""
    _activated.clear()


def _lookup(email: str, password: str) -> Session | None:
    """Verify a subscriber. The seam the subscriber table replaces.

    Compared with ``compare_digest`` so the answer does not leak through how
    long it took.
    """
    key = email.strip().lower()
    record = _activated.get(key) or _accounts().get(key)
    if record is None:
        return None
    expected, tier = record
    if not hmac.compare_digest(expected, password):
        return None
    return Session(email=key, tier=tier)


def _sign(payload: bytes) -> str:
    digest = hmac.new(_SECRET.encode("utf-8"), payload, sha256).digest()
    return urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _encode(session: Session) -> str:
    payload = json.dumps({"email": session.email, "tier": session.tier}).encode("utf-8")
    body = urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    return f"{body}.{_sign(payload)}"


def _decode(value: str) -> Session | None:
    try:
        body, signature = value.split(".", 1)
    except ValueError:
        return None
    padded = body + "=" * (-len(body) % 4)
    try:
        payload = urlsafe_b64decode(padded)
    except (ValueError, TypeError):
        return None
    # Verified before it is read: an unsigned cookie is attacker-supplied JSON.
    if not hmac.compare_digest(_sign(payload), signature):
        return None
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return None
    email, tier = parsed.get("email"), parsed.get("tier")
    if not isinstance(email, str) or not isinstance(tier, str):
        return None
    return Session(email=email, tier=tier)


def current_session(cedar_press_session: str | None = Cookie(default=None)) -> Session | None:
    """The signed-in subscriber, or None. Never raises: routes decide."""
    return _decode(cedar_press_session) if cedar_press_session else None


def issue(session: Session, response: Response) -> Session:
    """Put a signed session on the response. The activation route's way in.

    Split out of ``sign_in`` so activation does not have to re-verify a
    password it has just set, and so both paths set one cookie with one set
    of flags rather than two that can drift.
    """
    _set_cookie(session, response)
    return session


def sign_in(email: str, password: str, response: Response) -> Session | None:
    session = _lookup(email, password)
    if session is None:
        return None
    _set_cookie(session, response)
    return session


def _set_cookie(session: Session, response: Response) -> None:
    response.set_cookie(
        COOKIE,
        _encode(session),
        max_age=MAX_AGE,
        httponly=True,
        secure=os.environ.get("CEDAR_PRESS_INSECURE_COOKIE") != "1",
        samesite="none" if os.environ.get("CEDAR_PRESS_INSECURE_COOKIE") != "1" else "lax",
        path="/",
    )


def sign_out(response: Response) -> None:
    response.delete_cookie(COOKIE, path="/")
