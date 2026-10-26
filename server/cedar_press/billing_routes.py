"""Billing HTTP routes. Stripe webhook signatures replace browser-origin authentication."""

from __future__ import annotations

import json
import os
import secrets
from typing import Literal

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from cedar_press import billing, guest_checkout, ratelimit
from cedar_press.billing_policy import BillingError
from cedar_press.session import Session, current_session
from cedar_press.stripe_gateway import API_VERSION

router = APIRouter()


class CheckoutRequest(BaseModel):
    tier: Literal["press", "press_pro"]
    discount_code: str = Field(default="", max_length=64)


class GuestCheckoutRequest(BaseModel):
    tier: Literal["press", "press_pro"]


@router.get("/billing/plans")
def public_plans():
    from cedar_press.billing_policy import AMOUNTS, cohort_at

    cohort = cohort_at(billing.now())
    return {"cohort": cohort, "annualPrices": AMOUNTS[cohort]}


@router.post("/billing/guest/checkout")
def guest_start(body: GuestCheckoutRequest, request: Request):
    guard(request)
    secret = request.cookies.get(guest_checkout.COOKIE, "")
    if not 32 <= len(secret) <= 128:
        secret = secrets.token_urlsafe(32)
    try:
        result = call(guest_checkout.start, body.tier, secret)
        response = JSONResponse(result)
    except HTTPException as error:
        response = JSONResponse(error.detail, status_code=error.status_code)
    response.set_cookie(
        guest_checkout.COOKIE,
        secret,
        httponly=True,
        samesite="lax",
        secure=os.environ.get("CEDAR_PRESS_ENVIRONMENT", "development") != "development",
        max_age=86400,
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/billing/guest/status")
def guest_status(request: Request, response: Response):
    response.headers["Cache-Control"] = "private, no-store"
    return call(guest_checkout.status, request.cookies.get(guest_checkout.COOKIE, ""))


@router.post("/billing/guest/resend")
def resend_guest_email(request: Request, response: Response):
    guard(request)
    response.headers["Cache-Control"] = "private, no-store"
    return call(guest_checkout.resend, request.cookies.get(guest_checkout.COOKIE, ""))


def account(session: Session | None = Depends(current_session)) -> Session:
    if session is None:
        raise HTTPException(status_code=401, detail="Not signed in.")
    return session


def guard(request: Request):
    origins = os.environ.get(
        "CEDAR_PRESS_ORIGINS",
        "http://localhost:5173,https://cedarpress.ai,https://app.cedarpress.ai",
    ).split(",")
    origin = request.headers.get("origin")
    if origin is not None and origin not in [value.strip() for value in origins]:
        raise HTTPException(status_code=403, detail="Untrusted billing origin.")
    if not ratelimit.allow("billing:" + ratelimit.client_key(request), attempts=10):
        raise HTTPException(status_code=429, detail="Please wait before trying billing again.")


def call(function, *args):
    try:
        return function(*args)
    except BillingError as error:
        raise HTTPException(
            error.status, detail={"code": error.code, "message": error.message}
        ) from None
    except stripe.StripeError:
        raise HTTPException(
            502,
            detail={
                "code": "STRIPE_UNAVAILABLE",
                "message": "Billing could not be reached. Please try again.",
            },
        ) from None


@router.get("/billing")
def read_billing(session: Session = Depends(account)):
    return call(billing.summary, session.email)


@router.post("/billing/checkout")
def checkout(body: CheckoutRequest, request: Request, session: Session = Depends(account)):
    guard(request)
    return call(billing.checkout, session.email, body.tier, body.discount_code.strip())


@router.post("/billing/portal")
def portal(request: Request, session: Session = Depends(account)):
    guard(request)
    return call(billing.portal, session.email)


@router.post("/billing/change-plan")
def change_plan(request: Request, session: Session = Depends(account)):
    guard(request)
    return call(billing.portal, session.email, None, True)


@router.post("/billing/webhook")
async def webhook(request: Request):
    secret = os.environ.get("CEDAR_PRESS_STRIPE_WEBHOOK_SECRET", "")
    if not secret.startswith("whsec_"):
        raise HTTPException(503, detail="Billing webhook is not configured.")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 1_048_576:
            raise HTTPException(413, detail="Webhook is too large.")
    try:
        stripe.Webhook.construct_event(
            bytes(body), request.headers.get("stripe-signature", ""), secret
        )
        parsed = json.loads(body)
        if not isinstance(parsed, dict) or not isinstance(parsed.get("data"), dict):
            raise ValueError("Invalid event")
        if not isinstance(parsed.get("id"), str) or not isinstance(parsed.get("type"), str):
            raise ValueError("Missing event identifiers")
        if not isinstance(parsed["data"].get("object"), dict):
            raise ValueError("Missing event object")
        if parsed.get("api_version") != API_VERSION:
            raise ValueError("Unsupported event version")
        if not isinstance(parsed["data"]["object"]["id"], str):
            raise ValueError("Missing object ID")
    except (ValueError, KeyError, TypeError, stripe.SignatureVerificationError):
        raise HTTPException(400, detail="Invalid billing webhook.") from None
    call(billing.process_event, parsed)
    return {"received": True}
