"""Account services and authentication guards shared by HTTP routes."""

import os

from fastapi import Depends, HTTPException, Request

from cedar_press import ratelimit
from cedar_press.accounts.services.sessions import (
    Session,
    current_session,
    validate_auth_configuration,
)
from cedar_press.accounts.services.setup import AccountSetupService


def auth_origins():
    return [
        origin.strip()
        for origin in os.environ.get(
            "CEDAR_PRESS_ORIGINS",
            "http://localhost:5173,https://cedarpress.ai,https://app.cedarpress.ai",
        ).split(",")
        if origin.strip()
    ]


def get_account_setup() -> AccountSetupService:
    return AccountSetupService()


def _require_auth_origin(request: Request, action: str) -> None:
    origin = request.headers.get("origin")
    if origin is not None and origin not in auth_origins():
        raise HTTPException(status_code=403, detail=f"Untrusted {action} origin.")


def require_account(session: Session | None = Depends(current_session)) -> Session:
    """Authenticated identity, including an account without current paid access."""
    if session is None:
        raise HTTPException(status_code=401, detail="Not signed in.")
    return session


def _guard(request: Request, bucket: str, attempts: int) -> None:
    """Refuse a caller who has spent their attempts.

    Keyed by bucket as well as by client, so exhausting the sign-in allowance
    does not also lock the same person out of a password reset — those are different
    tasks and a subscriber may legitimately be doing the second after failing
    the first.
    """
    validate_auth_configuration()
    key = f"{bucket}:{ratelimit.client_key(request)}"
    if not ratelimit.allow(key, attempts=attempts):
        raise HTTPException(
            status_code=429,
            detail={
                "code": "TOO_MANY_ATTEMPTS",
                "message": "Too many attempts. Wait a few minutes and try again.",
            },
            headers={"Retry-After": str(ratelimit.retry_after(key))},
        )
