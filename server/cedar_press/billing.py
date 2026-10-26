"""Account billing operations, independent of HTTP and webhook processing."""

from __future__ import annotations

import datetime as dt

from cedar_press import db
from cedar_press.billing_policy import (
    AMOUNTS,
    BillingError,
    cohort_at,
    price_for,
    prices,
    unavailable,
    validate_price,
)
from cedar_press.billing_support import application_url, utc_now
from cedar_press.stripe_gateway import StripeGateway, stripe_url


class BillingService:
    """Checkout, billing portal and account history with explicit dependencies."""

    def __init__(self, *, gateway=None, database=db, clock=None, app_url=None):
        self._gateway = gateway
        self.db = database
        self.clock = clock or utc_now
        self.app_url = app_url or application_url

    @property
    def gateway(self):
        if self._gateway is None:
            self._gateway = StripeGateway()
        return self._gateway

    def account(self, email):
        if not self.db.configured():
            raise unavailable()
        row = self.db.one(
            "SELECT id,email,stripe_customer_id FROM cedar_press_subscribers WHERE lower(email)=%s",
            (email,),
        )
        if not row:
            raise BillingError("ACCOUNT_MISSING", "Please sign in again.", 401)
        return row

    def checkout(self, email, tier, discount_code=""):
        user = self.account(email)
        cohort = cohort_at(self.clock())
        chosen = price_for(tier, cohort)
        validate_price(self.gateway.price(chosen.id), chosen)
        promotion = None
        if discount_code:
            if cohort != "early_access":
                raise BillingError("DISCOUNT_INVALID", "That discount code is not available.")
            promotion = self.gateway.promotion(discount_code)
        url = self.app_url()
        # Persist the intent before the external call, so a timeout retries the same
        # idempotency key rather than creating a second Checkout Session.
        with self.db.pool().connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, email, stripe_customer_id FROM cedar_press_subscribers WHERE
                id=%s FOR UPDATE
                """,
                (user["id"],),
            )
            user = cur.fetchone()
            if not user["stripe_customer_id"]:
                user["stripe_customer_id"] = self.gateway.customer(user)
                cur.execute(
                    """
                    UPDATE cedar_press_subscribers SET stripe_customer_id=%s,
                    updated_at=now() WHERE id=%s
                    """,
                    (user["stripe_customer_id"], user["id"]),
                )
            if any(
                s["status"] not in {"canceled", "incomplete_expired"}
                for s in self.gateway.subscriptions(user["stripe_customer_id"])
            ):
                raise BillingError(
                    "SUBSCRIPTION_EXISTS", "Manage your existing subscription instead.", 409
                )
            cur.execute(
                """
                SELECT * FROM cedar_press_checkout_attempts WHERE user_id=%s AND status
                IN ('pending', 'open') FOR UPDATE
                """,
                (user["id"],),
            )
            attempt = cur.fetchone()
            if attempt and attempt["session_id"]:
                session = self.gateway.checkout_status(attempt["session_id"])
                if session["status"] == "open":
                    if attempt["price_id"] != chosen.id or attempt["promotion_id"] != promotion:
                        raise BillingError(
                            "CHECKOUT_EXISTS", "Finish or cancel your open checkout first.", 409
                        )
                    return {"url": stripe_url(session["url"])}
                cur.execute(
                    "UPDATE cedar_press_checkout_attempts SET status=%s WHERE id=%s",
                    (session["status"], attempt["id"]),
                )
                if session["status"] == "complete":
                    raise BillingError(
                        "CHECKOUT_PROCESSING",
                        "Your payment is processing. Refresh billing shortly.",
                        409,
                    )
                attempt = None
            if attempt and attempt["expires_at"] <= self.clock() + dt.timedelta(minutes=30):
                if attempt["price_id"] != chosen.id or attempt["promotion_id"] != promotion:
                    raise BillingError(
                        "CHECKOUT_EXISTS", "Retry your original checkout first.", 409
                    )
                recovered = self.gateway.find_checkout(
                    user["stripe_customer_id"], str(attempt["id"])
                )
                if recovered and recovered["status"] == "open":
                    cur.execute(
                        """
                        UPDATE cedar_press_checkout_attempts SET session_id=%s,
                        status='open' WHERE id=%s
                        """,
                        (recovered["id"], attempt["id"]),
                    )
                    return {"url": stripe_url(recovered["url"])}
                if recovered and recovered["status"] == "complete":
                    raise BillingError(
                        "CHECKOUT_PROCESSING",
                        "Your payment is processing. Refresh billing shortly.",
                        409,
                    )
                cur.execute(
                    "UPDATE cedar_press_checkout_attempts SET status='expired' WHERE id=%s",
                    (attempt["id"],),
                )
                attempt = None
            if attempt and (
                attempt["price_id"] != chosen.id or attempt["promotion_id"] != promotion
            ):
                raise BillingError("CHECKOUT_EXISTS", "Retry your original checkout first.", 409)
            if not attempt:
                if any(
                    s["status"] not in {"canceled", "incomplete_expired"}
                    for s in self.gateway.subscriptions(user["stripe_customer_id"])
                ):
                    raise BillingError(
                        "SUBSCRIPTION_EXISTS", "Manage your existing subscription instead.", 409
                    )
                cur.execute(
                    """
                    INSERT INTO cedar_press_checkout_attempts(user_id, price_id, tier,
                    cohort, promotion_id, expires_at) VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        user["id"],
                        chosen.id,
                        tier,
                        cohort,
                        promotion,
                        self.clock() + dt.timedelta(minutes=31),
                    ),
                )
                attempt = cur.fetchone()
        with self.db.pool().connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM cedar_press_subscribers WHERE id=%s FOR UPDATE", (user["id"],)
            )
            cur.execute(
                "SELECT * FROM cedar_press_checkout_attempts WHERE id=%s FOR UPDATE",
                (attempt["id"],),
            )
            attempt = cur.fetchone()
            if attempt["status"] not in {"pending", "open"}:
                raise BillingError("CHECKOUT_EXPIRED", "Please start checkout again.", 409)
            if not attempt["session_id"] and attempt["expires_at"] <= self.clock() + dt.timedelta(
                minutes=30
            ):
                raise BillingError("CHECKOUT_EXPIRED", "Please start checkout again.", 409)
            session = (
                self.gateway.checkout_status(attempt["session_id"])
                if attempt["session_id"]
                else self.gateway.checkout(user["stripe_customer_id"], attempt, url)
            )
            cur.execute(
                "UPDATE cedar_press_checkout_attempts SET session_id=%s,status=%s WHERE id=%s",
                (session["id"], session["status"], attempt["id"]),
            )
            if session["status"] != "open":
                raise BillingError(
                    "CHECKOUT_PROCESSING", "Refresh billing before starting another checkout.", 409
                )
            return {"url": stripe_url(session["url"])}

    def portal(self, email, change_plan=False):
        user = self.account(email)
        if not user["stripe_customer_id"]:
            raise BillingError("NO_BILLING_ACCOUNT", "Choose an annual plan first.")
        row = self.db.one(
            """
            SELECT cohort,customer_id FROM cedar_press_subscriptions WHERE user_id=%s ORDER BY
            CASE WHEN status NOT IN ('canceled', 'incomplete_expired') THEN 0 ELSE 1 END,
            activated_at DESC NULLS LAST, updated_at DESC LIMIT 1
            """,
            (user["id"],),
        )
        cohort = row["cohort"] if row else cohort_at(self.clock())
        customer = row["customer_id"] if row and row["customer_id"] else user["stripe_customer_id"]
        return {"url": self.gateway.portal(customer, cohort, self.app_url(), change_plan)}

    def summary(self, email):
        user = self.account(email)
        try:
            prices()
            _ = self.gateway
            configured = True
        except BillingError:
            configured = False
        return {
            "available": configured,
            "cohort": cohort_at(self.clock()),
            "annualPrices": AMOUNTS[cohort_at(self.clock())],
            "subscriptions": self.db.query(
                """
                SELECT id, tier, cohort, status, cancel_at_period_end, period_end,
                activated_at FROM cedar_press_subscriptions WHERE user_id=%s ORDER BY
                updated_at DESC
                """,
                (user["id"],),
            ),
            "invoices": self.db.query(
                """
                SELECT id, status, currency, amount_due, amount_paid, hosted_url,
                created_at FROM cedar_press_invoices WHERE user_id=%s ORDER BY
                created_at DESC LIMIT 50
                """,
                (user["id"],),
            ),
            "payments": self.db.query(
                """
                SELECT id, status, currency, amount, amount_received, created_at FROM
                cedar_press_payments WHERE user_id=%s ORDER BY created_at DESC LIMIT 50
                """,
                (user["id"],),
            ),
            "refunds": self.db.query(
                """
                SELECT r.id, r.status, r.currency, r.amount, r.created_at FROM
                cedar_press_refunds r JOIN cedar_press_payments p ON p.id=r.payment_id
                WHERE p.user_id=%s ORDER BY r.created_at DESC LIMIT 50
                """,
                (user["id"],),
            ),
            "hasCustomer": bool(user["stripe_customer_id"]),
        }
