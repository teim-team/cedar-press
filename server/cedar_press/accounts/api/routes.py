"""Account sign-in, password recovery and account setup endpoints."""

from __future__ import annotations

import logging
import os
import re
from urllib.parse import urlencode

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response

from cedar_press import ratelimit
from cedar_press.accounts.api.dependencies import (
    _guard,
    _require_auth_origin,
    get_account_setup,
    require_account,
)
from cedar_press.accounts.api.schemas import (
    AccountLink,
    AccountSetup,
    Credentials,
    PasswordChange,
    ProfileChange,
    ResetConfirm,
    ResetRequest,
)
from cedar_press.accounts.errors import AccountError
from cedar_press.accounts.services import subscribers
from cedar_press.accounts.services.email import AccountEmailSender
from cedar_press.accounts.services.sessions import (
    Session,
    current_session,
    sign_in,
    sign_out,
)
from cedar_press.accounts.services.setup import AccountSetupService

router = APIRouter()


@router.post("/auth/login")
def login(credentials: Credentials, request: Request, response: Response) -> dict[str, object]:
    _guard(request, "login", ratelimit.LOGIN_ATTEMPTS)
    session = sign_in(credentials.email, credentials.password, response)
    if session is None:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "INVALID_CREDENTIALS",
                "message": (
                    "That sign-in did not work. Check the address and password on "
                    "your Cedar Press confirmation."
                ),
            },
        )
    return session.as_payload()


@router.post("/auth/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    session: Session | None = Depends(current_session),
) -> None:
    # CORS governs response access, not whether a simple cross-site POST runs.
    # Reject an unrelated browser origin before account-wide revocation.
    _require_auth_origin(request, "sign-out")
    sign_out(response, session)


@router.post("/auth/password")
def change_password(
    change: PasswordChange,
    request: Request,
    response: Response,
    session: Session = Depends(require_account),
) -> dict[str, object]:
    """Replace the password and keep only this device signed in.

    The password hash is part of every session's revision, so the write signs
    every other device out; this one is re-issued a cookie on the new password.
    """
    _require_auth_origin(request, "password")
    _guard(request, "password", ratelimit.LOGIN_ATTEMPTS)
    found = subscribers.authenticate(session.email, change.current_password)
    if found is None:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_CREDENTIALS",
                "message": "Your current password is not correct.",
            },
        )
    _require_password_length(change.new_password)
    subscribers.change_password(found.email, change.new_password)
    renewed = sign_in(found.email, change.new_password, response)
    if renewed is None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "ACCOUNT_CHANGED",
                "message": "Your account changed. Please sign in again.",
            },
        )
    return renewed.as_payload()


@router.get("/auth/profile")
def read_account_profile(session: Session = Depends(require_account)) -> dict[str, object]:
    return {"email": session.email, **subscribers.profile(session.email)}


@router.patch("/auth/profile")
def write_account_profile(
    change: ProfileChange, request: Request, session: Session = Depends(require_account)
) -> dict[str, object]:
    _require_auth_origin(request, "profile")
    subscribers.set_display_name(session.email, (change.name or "").strip() or None)
    return {"email": session.email, **subscribers.profile(session.email)}


def _require_password_length(password: str) -> None:
    if len(password) < 10:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "PASSWORD_TOO_SHORT",
                "message": "Choose a password of at least 10 characters.",
            },
        )


#: Where the emailed link opens: the client's login page.
_APP_URL = os.environ.get("CEDAR_PRESS_APP_URL", "http://localhost:5173").rstrip("/")
_RESET_LOG = logging.getLogger("cedar_press.password_reset")


def _send_reset_link(email: str, link: str) -> None:
    sender = AccountEmailSender()
    if sender.configured():
        sender.send_link(email, link)
        return
    _RESET_LOG.warning("Password reset link for %s: %s", email, link)


@router.post("/auth/password-reset", status_code=204)
def request_password_reset(
    body: ResetRequest, request: Request, background: BackgroundTasks
) -> None:
    """Email a reset link if the address is a subscriber's.

    The answer is the same either way, and the link is sent after the
    response, so this cannot be used to ask whether somebody subscribes.
    """
    _require_auth_origin(request, "password reset")
    _guard(request, "reset", ratelimit.LOGIN_ATTEMPTS)
    if (
        not AccountEmailSender().configured()
        and os.environ.get("CEDAR_PRESS_ENVIRONMENT", "development") != "development"
    ):
        raise HTTPException(
            status_code=503,
            detail={
                "code": "PASSWORD_RESET_UNAVAILABLE",
                "message": (
                    "Password reset by email is not available yet. Contact Cedar Press for help."
                ),
            },
        )
    address = body.email.strip().lower()
    # Per address as well as per client, so nobody can flood one inbox.
    if not ratelimit.allow(f"reset-email:{address}", attempts=3):
        return
    token = subscribers.issue_reset(address)
    if token:
        destination = body.next
        if (
            not destination.startswith("/")
            or destination.startswith("//")
            or re.search(r"[\s\\]", destination)
        ):
            destination = "/"
        query = "?" + urlencode({"next": destination}) if destination != "/" else ""
        background.add_task(_send_reset_link, address, f"{_APP_URL}/login{query}#reset={token}")


@router.post("/auth/password-reset/confirm")
def confirm_password_reset(
    body: ResetConfirm, request: Request, response: Response
) -> dict[str, object]:
    """Set the new password from an emailed link and sign in on it.

    The password hash is part of every session's revision, so this signs every
    other device out.
    """
    _require_auth_origin(request, "password reset")
    _guard(request, "reset-confirm", ratelimit.LOGIN_ATTEMPTS)
    _require_password_length(body.new_password)
    made = subscribers.redeem_reset(body.token, body.new_password)
    if made is None:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "RESET_LINK_INVALID",
                "message": "That reset link has expired or was already used. Request a new one.",
            },
        )
    session = sign_in(made.email, body.new_password, response)
    if session is None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "ACCOUNT_CHANGED",
                "message": "Your account changed. Please sign in again.",
            },
        )
    return session.as_payload()


@router.post("/auth/account-setup/check")
def check_account_setup(
    body: AccountLink, request: Request, setup: AccountSetupService = Depends(get_account_setup)
):
    _require_auth_origin(request, "account setup")
    _guard(request, "account-setup-check", ratelimit.LOGIN_ATTEMPTS)
    try:
        return setup.account_details(body.token)
    except AccountError as error:
        raise HTTPException(
            error.status, detail={"code": error.code, "message": error.message}
        ) from None


@router.post("/auth/account-setup/confirm")
def finish_account_setup(
    body: AccountSetup,
    request: Request,
    response: Response,
    setup: AccountSetupService = Depends(get_account_setup),
):
    _require_auth_origin(request, "account setup")
    _guard(request, "account-setup", ratelimit.LOGIN_ATTEMPTS)
    _require_password_length(body.new_password)
    if not body.name.strip():
        raise HTTPException(400, detail="Enter your name.")
    made = setup.confirm(body.token, body.new_password, body.name.strip())
    if not made:
        raise HTTPException(
            400,
            detail={
                "code": "ACCOUNT_LINK_INVALID",
                "message": (
                    "This account link expired or was already used. "
                    "Request a password link to sign in."
                ),
            },
        )
    session = sign_in(made.email, body.new_password, response)
    if session is None:
        raise HTTPException(409, detail="Please sign in to your account.")
    return session.as_payload()

