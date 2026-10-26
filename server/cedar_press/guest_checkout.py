"""Direct Stripe Checkout, paid account provisioning and mailbox ownership."""

from __future__ import annotations

import datetime as dt
import hashlib
import re

from cedar_press import account_email, billing, db, ratelimit, subscribers
from cedar_press.billing_policy import (
    BillingError,
    cohort_at,
    price_for,
    reference,
    unavailable,
    validate_price,
)
from cedar_press.stripe_gateway import Gateway, stripe_url

COOKIE = "cedar_press_guest_checkout"


def digest(secret):
    return hashlib.sha256(secret.encode()).hexdigest()


def start(tier, secret, gateway=None):
    if not db.configured() or not account_email.configured():
        raise unavailable()
    gateway = gateway or Gateway()
    cohort = cohort_at(billing.now())
    chosen = price_for(tier, cohort)
    validate_price(gateway.price(chosen.id), chosen)
    with db.pool().connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (digest(secret),))
        cur.execute(
            """
            SELECT * FROM cedar_press_guest_checkouts WHERE secret_hash=%s
            AND price_id=%s AND email IS NULL AND status IN ('pending','open')
            ORDER BY created_at DESC LIMIT 1 FOR UPDATE
        """,
            (digest(secret), chosen.id),
        )
        attempt = cur.fetchone()
        if attempt and attempt["expires_at"] <= billing.now():
            cur.execute(
                "UPDATE cedar_press_guest_checkouts SET status='expired' WHERE id=%s",
                (attempt["id"],),
            )
            attempt = None
        if not attempt:
            cur.execute(
                """
                INSERT INTO cedar_press_guest_checkouts(secret_hash,price_id,tier,cohort,expires_at)
                VALUES (%s,%s,%s,%s,%s) RETURNING *
            """,
                (digest(secret), chosen.id, tier, cohort, billing.now() + dt.timedelta(minutes=31)),
            )
            attempt = cur.fetchone()
    # Persist the reservation before the network call. A lost response retries
    # the same Stripe idempotency key, without creating an account or customer.
    with db.pool().connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM cedar_press_guest_checkouts WHERE id=%s FOR UPDATE", (attempt["id"],)
        )
        attempt = cur.fetchone()
        if attempt["status"] not in {"pending", "open"}:
            raise BillingError(
                "CHECKOUT_PROCESSING", "Your payment is processing. Check your email shortly.", 409
            )
        if attempt["session_id"]:
            session = gateway.checkout_status(attempt["session_id"])
        elif attempt["expires_at"] <= billing.now() + dt.timedelta(minutes=30):
            session = gateway.find_checkout(None, str(attempt["id"]))
            if not session:
                cur.execute(
                    "UPDATE cedar_press_guest_checkouts SET status='expired' WHERE id=%s",
                    (attempt["id"],),
                )
                conn.commit()
                raise BillingError("CHECKOUT_EXPIRED", "Please start checkout again.", 409)
        else:
            session = gateway.checkout(None, attempt, billing.app_url(), guest=True)
        if session["status"] != "open":
            raise BillingError(
                "CHECKOUT_PROCESSING", "Your payment is processing. Check your email shortly.", 409
            )
        cur.execute(
            "UPDATE cedar_press_guest_checkouts SET session_id=%s,status='open' WHERE id=%s",
            (session["id"], attempt["id"]),
        )
        return {"url": stripe_url(session["url"])}


def owner(cur, customer):
    cur.execute(
        """
        SELECT id FROM cedar_press_subscribers WHERE stripe_customer_id=%s
        UNION SELECT user_id AS id FROM cedar_press_guest_checkouts
        WHERE customer_id=%s AND status='complete' AND user_id IS NOT NULL
    """,
        (customer, customer),
    )
    return cur.fetchone()


def activate(cur, gateway, customer):
    cur.execute(
        "SELECT * FROM cedar_press_guest_checkouts WHERE customer_id=%s FOR UPDATE", (customer,)
    )
    attempt = cur.fetchone()
    session = (
        gateway.checkout_status(attempt["session_id"])
        if attempt
        else gateway.guest_session(customer)
    )
    if not session:
        return None
    if not attempt:
        cur.execute(
            "SELECT * FROM cedar_press_guest_checkouts WHERE id=%s FOR UPDATE",
            (session.get("metadata", {}).get("cedar_press_guest_id"),),
        )
        attempt = cur.fetchone()
    if not attempt or session["id"] != attempt["session_id"]:
        return None
    billing._owned(session, customer)
    if session.get("metadata", {}).get("cedar_press_guest_id") != str(attempt["id"]) or session.get(
        "client_reference_id"
    ) != str(attempt["id"]):
        raise BillingError(
            "BILLING_OWNER_MISMATCH", "Checkout ownership could not be verified.", 502
        )
    if session["status"] != "complete" or session.get("payment_status") != "paid":
        return None
    subscription = gateway.subscription(reference(session.get("subscription")))
    billing._owned(subscription, customer)
    if subscription["status"] != "active":
        return None
    address = ((session.get("customer_details") or {}).get("email") or "").strip().lower()
    if len(address) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", address):
        raise BillingError("BILLING_DATA_INVALID", "Checkout email could not be verified.", 502)
    cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", ("guest:" + address,))
    cur.execute(
        """
        INSERT INTO cedar_press_subscribers(email,account_id,tier,stripe_customer_id)
        VALUES (%s,%s,NULL,%s) ON CONFLICT DO NOTHING RETURNING id
    """,
        (address, address, customer),
    )
    user = cur.fetchone()
    if not user:
        # Paying for an existing email never replaces credentials or proves
        # mailbox ownership. The existing reader signs in normally afterward.
        cur.execute(
            "SELECT id FROM cedar_press_subscribers WHERE lower(btrim(email))=%s", (address,)
        )
        user = cur.fetchone()
        if not user:
            raise BillingError(
                "BILLING_OWNER_MISMATCH", "Account ownership could not be verified.", 502
            )
        cur.execute(
            "UPDATE cedar_press_subscribers SET stripe_customer_id="
            "COALESCE(stripe_customer_id,%s) WHERE id=%s",
            (customer, user["id"]),
        )
    cur.execute(
        """
        UPDATE cedar_press_guest_checkouts SET email=%s,customer_id=%s,user_id=%s,status='complete'
        WHERE id=%s
    """,
        (address, customer, user["id"], attempt["id"]),
    )
    return user


def send_claim(customer):
    with db.pool().connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT * FROM cedar_press_guest_checkouts WHERE customer_id=%s AND
            status='complete' AND claim_sent_at IS NULL FOR UPDATE
            """,
            (customer,),
        )
        attempt = cur.fetchone()
        if not attempt:
            return
        found = subscribers.find(attempt["email"])
        if found and found.password_hash:
            account_email.send_link(attempt["email"], billing.app_url() + "/login", sign_in=True)
            cur.execute(
                "UPDATE cedar_press_guest_checkouts SET claim_sent_at=now() WHERE id=%s",
                (attempt["id"],),
            )
            return
        token = subscribers.issue_reset(attempt["email"])
        if not token:
            raise RuntimeError("Paid account is unavailable")
        account_email.send_link(
            attempt["email"], billing.app_url() + "/create-account#token=" + token
        )
        cur.execute(
            """
            UPDATE cedar_press_guest_checkouts SET claim_sent_at=now() WHERE id=%s
            """,
            (attempt["id"],),
        )


def status(secret):
    if not db.configured():
        raise unavailable()
    row = db.one(
        """
        SELECT g.email,g.status,g.claim_sent_at,s.password_hash FROM cedar_press_guest_checkouts g
        LEFT JOIN cedar_press_subscribers s ON s.id=g.user_id
        WHERE g.secret_hash=%s ORDER BY g.created_at DESC LIMIT 1
        """,
        (digest(secret),),
    )
    if not row:
        raise BillingError("CHECKOUT_MISSING", "Start a new checkout to subscribe.", 404)
    return {
        "status": row["status"],
        "email": row["email"],
        "emailSent": row["claim_sent_at"] is not None,
        "accountSetup": row["password_hash"] is None,
    }


def resend(secret):
    if not db.configured() or not account_email.configured():
        raise unavailable()
    row = db.one(
        """
        SELECT id,email,customer_id FROM cedar_press_guest_checkouts
        WHERE secret_hash=%s AND status='complete' AND user_id IS NOT NULL
        ORDER BY created_at DESC LIMIT 1
    """,
        (digest(secret),),
    )
    if not row:
        raise BillingError(
            "CHECKOUT_PENDING",
            "Your payment is still being confirmed. Please try again shortly.",
            409,
        )
    if not ratelimit.allow("checkout-email:" + row["email"], attempts=3):
        raise BillingError("EMAIL_RATE_LIMIT", "Please wait before requesting another email.", 429)
    db.execute(
        "UPDATE cedar_press_guest_checkouts SET claim_sent_at=NULL WHERE id=%s", (row["id"],)
    )
    try:
        send_claim(row["customer_id"])
    except (OSError, RuntimeError):
        raise BillingError(
            "EMAIL_UNAVAILABLE", "We couldn’t send the email. Please try again shortly.", 503
        ) from None
    return status(secret)


def account_details(token):
    if not db.configured():
        raise unavailable()
    row = db.one(
        """
        SELECT s.email FROM cedar_press_password_resets r
        JOIN cedar_press_subscribers s ON s.email=r.email
        JOIN cedar_press_guest_checkouts g ON g.user_id=s.id
        WHERE r.token_hash=%s AND r.used_at IS NULL AND r.expires_at>now()
        AND s.password_hash IS NULL AND g.status='complete'
    """,
        (digest(token),),
    )
    if not row:
        raise BillingError(
            "ACCOUNT_LINK_INVALID",
            "This account link expired or was already used. Request a password link to sign in.",
        )
    return row
