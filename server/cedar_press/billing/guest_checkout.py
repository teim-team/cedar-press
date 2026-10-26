"""Direct Stripe purchases, paid account provisioning and mailbox ownership."""

from __future__ import annotations

import datetime as dt
import hashlib
import re

from cedar_press import db, ratelimit
from cedar_press.account_email import AccountEmailSender
from cedar_press.billing.contracts import BillingGateway
from cedar_press.billing.policy import (
    BillingError,
    cohort_at,
    price_for,
    reference,
    unavailable,
    validate_price,
)
from cedar_press.billing.stripe_gateway import StripeGateway, stripe_url
from cedar_press.billing.support import application_url, utc_now, verify_customer

COOKIE = "cedar_press_guest_checkout"


def digest(secret):
    return hashlib.sha256(secret.encode()).hexdigest()


class GuestCheckoutService:
    """Own guest purchase reservations and paid identity provisioning."""

    def __init__(
        self,
        *,
        gateway: BillingGateway | None = None,
        database=db,
        clock=None,
        app_url=None,
        email_sender=None,
        setup_service=None,
        limiter=ratelimit,
    ):
        self.email_sender = email_sender or AccountEmailSender()
        self.setup = setup_service
        self.limiter = limiter
        self._gateway = gateway
        self.db = database
        self.clock = clock or utc_now
        self.app_url = app_url or application_url

    @property
    def gateway(self):
        if self._gateway is None:
            self._gateway = StripeGateway()
        return self._gateway

    def start(self, tier, secret):
        if not self.db.configured() or not self.email_sender.configured():
            raise unavailable()
        cohort = cohort_at(self.clock())
        chosen = price_for(tier, cohort)
        validate_price(self.gateway.price(chosen.id), chosen)
        with self.db.pool().connection() as conn, conn.cursor() as cur:
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
            if attempt and attempt["expires_at"] <= self.clock():
                cur.execute(
                    "UPDATE cedar_press_guest_checkouts SET status='expired' WHERE id=%s",
                    (attempt["id"],),
                )
                attempt = None
            if not attempt:
                cur.execute(
                    """
                    INSERT INTO cedar_press_guest_checkouts
                    (secret_hash,price_id,tier,cohort,expires_at)
                    VALUES (%s,%s,%s,%s,%s) RETURNING *
                """,
                    (
                        digest(secret),
                        chosen.id,
                        tier,
                        cohort,
                        self.clock() + dt.timedelta(minutes=31),
                    ),
                )
                attempt = cur.fetchone()
        # Persist the reservation before the network call. A lost response retries
        # the same Stripe idempotency key, without creating an account or customer.
        with self.db.pool().connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM cedar_press_guest_checkouts WHERE id=%s FOR UPDATE", (attempt["id"],)
            )
            attempt = cur.fetchone()
            if attempt["status"] not in {"pending", "open"}:
                raise BillingError(
                    "CHECKOUT_PROCESSING",
                    "Your payment is processing. Check your email shortly.",
                    409,
                )
            if attempt["session_id"]:
                session = self.gateway.checkout_status(attempt["session_id"])
            elif attempt["expires_at"] <= self.clock() + dt.timedelta(minutes=30):
                session = self.gateway.find_checkout(None, str(attempt["id"]))
                if not session:
                    cur.execute(
                        "UPDATE cedar_press_guest_checkouts SET status='expired' WHERE id=%s",
                        (attempt["id"],),
                    )
                    conn.commit()
                    raise BillingError("CHECKOUT_EXPIRED", "Please start checkout again.", 409)
            else:
                session = self.gateway.checkout(None, attempt, self.app_url(), guest=True)
            if session["status"] != "open":
                raise BillingError(
                    "CHECKOUT_PROCESSING",
                    "Your payment is processing. Check your email shortly.",
                    409,
                )
            cur.execute(
                "UPDATE cedar_press_guest_checkouts SET session_id=%s,status='open' WHERE id=%s",
                (session["id"], attempt["id"]),
            )
            return {"url": stripe_url(session["url"])}

    def owner(self, cur, customer):
        cur.execute(
            """
            SELECT id FROM cedar_press_subscribers WHERE stripe_customer_id=%s
            UNION SELECT user_id AS id FROM cedar_press_guest_checkouts
            WHERE customer_id=%s AND status='complete' AND user_id IS NOT NULL
        """,
            (customer, customer),
        )
        return cur.fetchone()

    def prepare_activation(self, cur, customer):
        cur.execute(
            "SELECT * FROM cedar_press_guest_checkouts WHERE customer_id=%s FOR UPDATE", (customer,)
        )
        attempt = cur.fetchone()
        session = (
            self.gateway.checkout_status(attempt["session_id"])
            if attempt
            else self.gateway.guest_session(customer)
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
        verify_customer(session, customer)
        if session.get("metadata", {}).get("cedar_press_guest_id") != str(
            attempt["id"]
        ) or session.get("client_reference_id") != str(attempt["id"]):
            raise BillingError(
                "BILLING_OWNER_MISMATCH", "Checkout ownership could not be verified.", 502
            )
        if session["status"] != "complete" or session.get("payment_status") != "paid":
            return None
        subscription = self.gateway.subscription(reference(session.get("subscription")))
        verify_customer(subscription, customer)
        if subscription["status"] != "active":
            return None
        return attempt, session

    def activate(self, cur, customer, prepared):
        if not prepared:
            return None
        attempt, session = prepared
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
            UPDATE cedar_press_guest_checkouts
            SET email=%s,customer_id=%s,user_id=%s,status='complete'
            WHERE id=%s
        """,
            (address, customer, user["id"], attempt["id"]),
        )
        return user

    def status(self, secret):
        if not self.db.configured():
            raise unavailable()
        row = self.db.one(
            """
            SELECT g.email,g.status,g.claim_sent_at,s.password_hash
            FROM cedar_press_guest_checkouts g
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

    def resend(self, secret):
        if not self.db.configured() or not self.email_sender.configured():
            raise unavailable()
        row = self.db.one(
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
        if not self.limiter.allow("checkout-email:" + row["email"], attempts=3):
            raise BillingError(
                "EMAIL_RATE_LIMIT", "Please wait before requesting another email.", 429
            )
        self.setup.request_resend(row["id"])
        try:
            self.setup.send_claim(row["customer_id"])
        except (OSError, RuntimeError):
            raise BillingError(
                "EMAIL_UNAVAILABLE", "We couldn’t send the email. Please try again shortly.", 503
            ) from None
        return self.status(secret)
