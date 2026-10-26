"""Individual Stripe billing: durable checkout intents, canonical reconciliation and audit rows."""

from __future__ import annotations

import datetime as dt
import os
from urllib.parse import urlsplit

from cedar_press import db
from cedar_press.billing_policy import (
    AMOUNTS,
    BillingError,
    cohort_at,
    coverage,
    identify_price,
    instant,
    price_for,
    reference,
    unavailable,
    validate_price,
)
from cedar_press.stripe_gateway import Gateway, stripe_url


def now():
    return dt.datetime.now(dt.timezone.utc)


def app_url():
    value = os.environ.get("CEDAR_PRESS_APP_URL", "http://localhost:5173").rstrip("/")
    parsed = urlsplit(value)
    development = os.environ.get("CEDAR_PRESS_ENVIRONMENT", "development") == "development"
    if (
        not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path
        or (
            parsed.scheme != "https"
            and not (
                development
                and parsed.scheme == "http"
                and parsed.hostname in {"localhost", "127.0.0.1"}
            )
        )
    ):
        raise unavailable()
    return value


def account(email):
    if not db.configured():
        raise unavailable()
    row = db.one(
        "SELECT id,email,stripe_customer_id FROM cedar_press_subscribers WHERE lower(email)=%s",
        (email,),
    )
    if not row:
        raise BillingError("ACCOUNT_MISSING", "Please sign in again.", 401)
    return row


def checkout(email, tier, discount_code="", gateway=None):
    gateway = gateway or Gateway()
    user = account(email)
    cohort = cohort_at(now())
    chosen = price_for(tier, cohort)
    validate_price(gateway.price(chosen.id), chosen)
    promotion = None
    if discount_code:
        if cohort != "early_access":
            raise BillingError("DISCOUNT_INVALID", "That discount code is not available.")
        promotion = gateway.promotion(discount_code)
    url = app_url()
    # Persist the intent before the external call, so a timeout retries the same
    # idempotency key rather than creating a second Checkout Session.
    with db.pool().connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, email, stripe_customer_id FROM cedar_press_subscribers WHERE
            id=%s FOR UPDATE
            """,
            (user["id"],),
        )
        user = cur.fetchone()
        if not user["stripe_customer_id"]:
            user["stripe_customer_id"] = gateway.customer(user)
            cur.execute(
                """
                UPDATE cedar_press_subscribers SET stripe_customer_id=%s,
                updated_at=now() WHERE id=%s
                """,
                (user["stripe_customer_id"], user["id"]),
            )
        if any(
            s["status"] not in {"canceled", "incomplete_expired"}
            for s in gateway.subscriptions(user["stripe_customer_id"])
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
            session = gateway.checkout_status(attempt["session_id"])
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
        if attempt and attempt["expires_at"] <= now() + dt.timedelta(minutes=30):
            if attempt["price_id"] != chosen.id or attempt["promotion_id"] != promotion:
                raise BillingError("CHECKOUT_EXISTS", "Retry your original checkout first.", 409)
            recovered = gateway.find_checkout(user["stripe_customer_id"], str(attempt["id"]))
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
        if attempt and (attempt["price_id"] != chosen.id or attempt["promotion_id"] != promotion):
            raise BillingError("CHECKOUT_EXISTS", "Retry your original checkout first.", 409)
        if not attempt:
            if any(
                s["status"] not in {"canceled", "incomplete_expired"}
                for s in gateway.subscriptions(user["stripe_customer_id"])
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
                (user["id"], chosen.id, tier, cohort, promotion, now() + dt.timedelta(minutes=31)),
            )
            attempt = cur.fetchone()
    with db.pool().connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM cedar_press_subscribers WHERE id=%s FOR UPDATE", (user["id"],))
        cur.execute(
            "SELECT * FROM cedar_press_checkout_attempts WHERE id=%s FOR UPDATE", (attempt["id"],)
        )
        attempt = cur.fetchone()
        if attempt["status"] not in {"pending", "open"}:
            raise BillingError("CHECKOUT_EXPIRED", "Please start checkout again.", 409)
        if not attempt["session_id"] and attempt["expires_at"] <= now() + dt.timedelta(minutes=30):
            raise BillingError("CHECKOUT_EXPIRED", "Please start checkout again.", 409)
        session = (
            gateway.checkout_status(attempt["session_id"])
            if attempt["session_id"]
            else gateway.checkout(user["stripe_customer_id"], attempt, url)
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


def portal(email, gateway=None, change_plan=False):
    user = account(email)
    if not user["stripe_customer_id"]:
        raise BillingError("NO_BILLING_ACCOUNT", "Choose an annual plan first.")
    row = db.one(
        """
        SELECT cohort,customer_id FROM cedar_press_subscriptions WHERE user_id=%s ORDER BY
        CASE WHEN status NOT IN ('canceled', 'incomplete_expired') THEN 0 ELSE 1 END,
        activated_at DESC NULLS LAST, updated_at DESC LIMIT 1
        """,
        (user["id"],),
    )
    cohort = row["cohort"] if row else cohort_at(now())
    customer = row["customer_id"] if row and row["customer_id"] else user["stripe_customer_id"]
    return {"url": (gateway or Gateway()).portal(customer, cohort, app_url(), change_plan)}


def _owned(value, customer):
    if reference(value.get("customer")) != customer:
        raise BillingError("BILLING_OWNER_MISMATCH", "Billing data could not be verified.", 502)


def _written(cur):
    if cur.rowcount != 1:
        raise BillingError(
            "BILLING_OWNER_MISMATCH", "Billing ownership could not be verified.", 502
        )


def _payment(cur, gateway, user_id, customer, payment_id, invoice_id=None):
    payment = gateway.payment(payment_id)
    _owned(payment, customer)
    charge_id = reference(payment.get("latest_charge"))
    cur.execute(
        """
        INSERT INTO cedar_press_payments(id, user_id, invoice_id, charge_id, status,
        currency, amount, amount_received, created_at) VALUES (%s, %s, %s, %s, %s,
        %s, %s, %s, %s) ON CONFLICT(id) DO UPDATE SET
        invoice_id=COALESCE(EXCLUDED.invoice_id, cedar_press_payments.invoice_id),
        charge_id=EXCLUDED.charge_id, status=EXCLUDED.status,
        amount=EXCLUDED.amount, amount_received=EXCLUDED.amount_received,
        updated_at=now() WHERE cedar_press_payments.user_id=EXCLUDED.user_id
        """,
        (
            payment_id,
            user_id,
            invoice_id,
            charge_id,
            payment["status"],
            payment["currency"],
            payment["amount"],
            payment["amount_received"],
            instant(payment["created"]),
        ),
    )
    _written(cur)
    if charge_id:
        for refund in gateway.refunds(charge_id):
            if reference(refund.get("payment_intent")) != payment_id:
                raise BillingError(
                    "BILLING_OWNER_MISMATCH", "Refund data could not be verified.", 502
                )
            cur.execute(
                """
                INSERT INTO cedar_press_refunds(id, payment_id, status, currency,
                amount, created_at) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT(id)
                DO UPDATE SET status=EXCLUDED.status, amount=EXCLUDED.amount,
                updated_at=now() WHERE cedar_press_refunds.payment_id=EXCLUDED.payment_id
                """,
                (
                    refund["id"],
                    payment_id,
                    refund["status"],
                    refund["currency"],
                    refund["amount"],
                    instant(refund["created"]),
                ),
            )
            _written(cur)


def _subscription(cur, gateway, user_id, customer, subscription_id):
    subscription = gateway.subscription(subscription_id)
    _owned(subscription, customer)
    items = subscription["items"]["data"]
    if len(items) != 1 or items[0].get("quantity") != 1:
        raise BillingError("BILLING_DATA_INVALID", "Subscription items could not be verified.", 502)
    item = items[0]
    price = identify_price(item["price"])
    validate_price(item["price"], price)
    cur.execute(
        """
        INSERT INTO cedar_press_subscriptions(id, user_id, price_id, tier, cohort,
        status, cancel_at_period_end, period_end, customer_id) VALUES (%s, %s, %s, %s, %s, %s,
        %s, %s, %s) ON CONFLICT(id) DO UPDATE SET price_id=EXCLUDED.price_id,
        customer_id=EXCLUDED.customer_id,
        tier=EXCLUDED.tier, status=EXCLUDED.status,
        cancel_at_period_end=EXCLUDED.cancel_at_period_end,
        period_end=EXCLUDED.period_end, updated_at=now()
        WHERE cedar_press_subscriptions.user_id=EXCLUDED.user_id
        """,
        (
            subscription_id,
            user_id,
            price.id,
            price.tier,
            price.cohort,
            subscription["status"],
            subscription.get("cancel_at_period_end", False),
            instant(item["current_period_end"]),
            customer,
        ),
    )
    _written(cur)
    activated = False
    for invoice in gateway.invoices(subscription_id):
        _owned(invoice, customer)
        if invoice["currency"] != "usd":
            raise BillingError("BILLING_DATA_INVALID", "Invoice currency is not supported.", 502)
        invoice_subscription = reference(
            invoice.get("subscription")
            or (invoice.get("parent") or {}).get("subscription_details", {}).get("subscription")
        )
        if invoice_subscription != subscription_id:
            raise BillingError("BILLING_OWNER_MISMATCH", "Invoice data could not be verified.", 502)
        tier, start, end = coverage(gateway.lines(invoice["id"]))
        hosted = (
            stripe_url(invoice["hosted_invoice_url"]) if invoice.get("hosted_invoice_url") else None
        )
        cur.execute(
            """
            INSERT INTO cedar_press_invoices(id, user_id, subscription_id, status,
            currency, amount_due, amount_paid, tier, access_starts_at,
            access_ends_at, hosted_url, created_at) VALUES (%s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s) ON CONFLICT(id) DO UPDATE SET
            status=EXCLUDED.status, amount_due=EXCLUDED.amount_due,
            amount_paid=EXCLUDED.amount_paid, tier=EXCLUDED.tier,
            access_starts_at=EXCLUDED.access_starts_at,
            access_ends_at=EXCLUDED.access_ends_at, hosted_url=EXCLUDED.hosted_url,
            updated_at=now() WHERE cedar_press_invoices.user_id=EXCLUDED.user_id
            """,
            (
                invoice["id"],
                user_id,
                subscription_id,
                invoice["status"] or "draft",
                invoice["currency"],
                invoice["amount_due"],
                invoice["amount_paid"],
                tier,
                start,
                end,
                hosted,
                instant(invoice["created"]),
            ),
        )
        _written(cur)
        activated |= invoice["status"] == "paid" and tier is not None
        for record in gateway.invoice_payments(invoice["id"]):
            payment_id = reference((record.get("payment") or {}).get("payment_intent"))
            if payment_id:
                _payment(cur, gateway, user_id, customer, payment_id, invoice["id"])
    if activated:
        cur.execute(
            """
            UPDATE cedar_press_subscriptions SET activated_at=COALESCE(activated_at,
            now()) WHERE id=%s
            """,
            (subscription_id,),
        )


def reconcile_customer(customer, gateway=None):
    gateway = gateway or Gateway()
    with db.pool().connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (customer,))
        from cedar_press import guest_checkout

        user = guest_checkout.owner(cur, customer)
        if not user:
            from cedar_press import guest_checkout

            user = guest_checkout.activate(cur, gateway, customer)
        if not user:
            return False
        for subscription in gateway.subscriptions(customer):
            _subscription(cur, gateway, user["id"], customer, subscription["id"])
    from cedar_press import guest_checkout

    guest_checkout.send_claim(customer)
    return True


def process_event(event, gateway=None):
    gateway = gateway or Gateway()
    obj = event["data"]["object"]
    event_type, object_id = event["type"], obj["id"]
    if event.get("livemode") is not gateway.livemode:
        raise BillingError("WEBHOOK_MODE_INVALID", "Webhook mode does not match this service.")
    customer = reference(obj.get("customer"))
    db.execute(
        """
        INSERT INTO cedar_press_webhook_events(id, event_type, object_id,
        customer_id) VALUES (%s, %s, %s, %s) ON CONFLICT(id) DO NOTHING
        """,
        (event["id"], event_type, object_id, customer),
    )
    try:
        with db.pool().connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT status,customer_id FROM cedar_press_webhook_events WHERE id=%s FOR UPDATE",
                (event["id"],),
            )
            inbox = cur.fetchone()
            if inbox["status"] in {"processed", "ignored"}:
                from cedar_press import guest_checkout

                guest_checkout.send_claim(inbox["customer_id"])
                return
            cur.execute(
                "UPDATE cedar_press_webhook_events SET attempts=attempts+1 WHERE id=%s",
                (event["id"],),
            )
            if event_type.startswith("refund."):
                customer = reference(
                    gateway.charge(reference(gateway.refund(object_id)["charge"]))["customer"]
                )
                cur.execute(
                    "UPDATE cedar_press_webhook_events SET customer_id=%s WHERE id=%s",
                    (customer, event["id"]),
                )
            supported = event_type.startswith(
                (
                    "customer.subscription.",
                    "invoice.",
                    "payment_intent.",
                    "charge.refunded",
                    "refund.",
                    "checkout.session.",
                )
            )
            cur.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (customer or event["id"],)
            )
            from cedar_press import guest_checkout

            user = guest_checkout.owner(cur, customer)
            if not user and customer and supported:
                from cedar_press import guest_checkout

                user = guest_checkout.activate(cur, gateway, customer)
            if user and supported:
                if event_type.startswith("checkout.session."):
                    current = gateway.checkout_status(object_id)
                    _owned(current, customer)
                    cur.execute(
                        """
                        UPDATE cedar_press_checkout_attempts SET status=%s WHERE
                        session_id=%s AND user_id=%s
                        """,
                        (current["status"], object_id, user["id"]),
                    )
                # Always fetch current Stripe state under the customer lock;
                # delivery order and event creation timestamps are not authority.
                for subscription in gateway.subscriptions(customer):
                    _subscription(cur, gateway, user["id"], customer, subscription["id"])
                if event_type.startswith("payment_intent."):
                    _payment(cur, gateway, user["id"], customer, object_id)
                if event_type == "charge.refunded" or event_type.startswith("refund."):
                    charge = (
                        gateway.charge(object_id)
                        if event_type == "charge.refunded"
                        else gateway.charge(reference(gateway.refund(object_id)["charge"]))
                    )
                    _owned(charge, customer)
                    _payment(
                        cur, gateway, user["id"], customer, reference(charge["payment_intent"])
                    )
            cur.execute(
                """
                UPDATE cedar_press_webhook_events SET status=%s, processed_at=now(),
                error_code=NULL WHERE id=%s
                """,
                ("processed" if user and supported else "ignored", event["id"]),
            )
        from cedar_press import guest_checkout

        guest_checkout.send_claim(customer)
    except Exception:
        db.execute(
            """
            UPDATE cedar_press_webhook_events SET status='failed',
            attempts=attempts+1, error_code='RECONCILIATION_FAILED' WHERE id=%s
            """,
            (event["id"],),
        )
        raise


def summary(email):
    user = account(email)
    try:
        from cedar_press.billing_policy import prices

        prices()
        Gateway()
        configured = True
    except BillingError:
        configured = False
    return {
        "available": configured,
        "cohort": cohort_at(now()),
        "annualPrices": AMOUNTS[cohort_at(now())],
        "subscriptions": db.query(
            """
            SELECT id, tier, cohort, status, cancel_at_period_end, period_end,
            activated_at FROM cedar_press_subscriptions WHERE user_id=%s ORDER BY
            updated_at DESC
            """,
            (user["id"],),
        ),
        "invoices": db.query(
            """
            SELECT id, status, currency, amount_due, amount_paid, hosted_url,
            created_at FROM cedar_press_invoices WHERE user_id=%s ORDER BY
            created_at DESC LIMIT 50
            """,
            (user["id"],),
        ),
        "payments": db.query(
            """
            SELECT id, status, currency, amount, amount_received, created_at FROM
            cedar_press_payments WHERE user_id=%s ORDER BY created_at DESC LIMIT 50
            """,
            (user["id"],),
        ),
        "refunds": db.query(
            """
            SELECT r.id, r.status, r.currency, r.amount, r.created_at FROM
            cedar_press_refunds r JOIN cedar_press_payments p ON p.id=r.payment_id
            WHERE p.user_id=%s ORDER BY r.created_at DESC LIMIT 50
            """,
            (user["id"],),
        ),
        "hasCustomer": bool(user["stripe_customer_id"]),
    }
