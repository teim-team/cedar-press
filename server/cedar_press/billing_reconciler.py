"""Canonical Stripe reconciliation and durable webhook processing."""

from __future__ import annotations

from cedar_press import db
from cedar_press.billing_policy import (
    BillingError,
    coverage,
    identify_price,
    instant,
    reference,
    validate_price,
)
from cedar_press.billing_support import verify_customer, verify_write
from cedar_press.stripe_gateway import StripeGateway, stripe_url


class BillingReconciler:
    """Synchronize provider state while keeping transaction boundaries visible."""

    def __init__(self, guest_service, *, gateway=None, database=db):
        self.guests = guest_service
        self._gateway = gateway
        self.db = database

    @property
    def gateway(self):
        if self._gateway is None:
            self._gateway = StripeGateway()
        return self._gateway

    def _payment(self, cur, user_id, customer, payment_id, invoice_id=None):
        payment = self.gateway.payment(payment_id)
        verify_customer(payment, customer)
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
        verify_write(cur)
        if charge_id:
            for refund in self.gateway.refunds(charge_id):
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
                verify_write(cur)

    def _subscription(self, cur, user_id, customer, subscription_id):
        subscription = self.gateway.subscription(subscription_id)
        verify_customer(subscription, customer)
        items = subscription["items"]["data"]
        if len(items) != 1 or items[0].get("quantity") != 1:
            raise BillingError(
                "BILLING_DATA_INVALID", "Subscription items could not be verified.", 502
            )
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
        verify_write(cur)
        activated = False
        for invoice in self.gateway.invoices(subscription_id):
            verify_customer(invoice, customer)
            if invoice["currency"] != "usd":
                raise BillingError(
                    "BILLING_DATA_INVALID", "Invoice currency is not supported.", 502
                )
            invoice_subscription = reference(
                invoice.get("subscription")
                or (invoice.get("parent") or {}).get("subscription_details", {}).get("subscription")
            )
            if invoice_subscription != subscription_id:
                raise BillingError(
                    "BILLING_OWNER_MISMATCH", "Invoice data could not be verified.", 502
                )
            tier, start, end = coverage(self.gateway.lines(invoice["id"]))
            hosted = (
                stripe_url(invoice["hosted_invoice_url"])
                if invoice.get("hosted_invoice_url")
                else None
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
            verify_write(cur)
            activated |= invoice["status"] == "paid" and tier is not None
            for record in self.gateway.invoice_payments(invoice["id"]):
                payment_id = reference((record.get("payment") or {}).get("payment_intent"))
                if payment_id:
                    self._payment(cur, user_id, customer, payment_id, invoice["id"])
        if activated:
            cur.execute(
                """
                UPDATE cedar_press_subscriptions SET activated_at=COALESCE(activated_at,
                now()) WHERE id=%s
                """,
                (subscription_id,),
            )

    def reconcile_customer(self, customer):
        with self.db.pool().connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (customer,))

            user = self.guests.owner(cur, customer)
            if not user:
                user = self.guests.activate(cur, customer)
            if not user:
                return False
            for subscription in self.gateway.subscriptions(customer):
                self._subscription(cur, user["id"], customer, subscription["id"])

        self.guests.send_claim(customer)
        return True

    def process_event(self, event):
        obj = event["data"]["object"]
        event_type, object_id = event["type"], obj["id"]
        if event.get("livemode") is not self.gateway.livemode:
            raise BillingError("WEBHOOK_MODE_INVALID", "Webhook mode does not match this service.")
        customer = reference(obj.get("customer"))
        self.db.execute(
            """
            INSERT INTO cedar_press_webhook_events(id, event_type, object_id,
            customer_id) VALUES (%s, %s, %s, %s) ON CONFLICT(id) DO NOTHING
            """,
            (event["id"], event_type, object_id, customer),
        )
        try:
            with self.db.pool().connection() as conn, conn.cursor() as cur:
                cur.execute(
                    "SELECT status,customer_id FROM cedar_press_webhook_events "
                    "WHERE id=%s FOR UPDATE",
                    (event["id"],),
                )
                inbox = cur.fetchone()
                if inbox["status"] in {"processed", "ignored"}:
                    self.guests.send_claim(inbox["customer_id"])
                    return
                cur.execute(
                    "UPDATE cedar_press_webhook_events SET attempts=attempts+1 WHERE id=%s",
                    (event["id"],),
                )
                if event_type.startswith("refund."):
                    customer = reference(
                        self.gateway.charge(reference(self.gateway.refund(object_id)["charge"]))[
                            "customer"
                        ]
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
                    "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
                    (customer or event["id"],),
                )

                user = self.guests.owner(cur, customer)
                if not user and customer and supported:
                    user = self.guests.activate(cur, customer)
                if user and supported:
                    if event_type.startswith("checkout.session."):
                        current = self.gateway.checkout_status(object_id)
                        verify_customer(current, customer)
                        cur.execute(
                            """
                            UPDATE cedar_press_checkout_attempts SET status=%s WHERE
                            session_id=%s AND user_id=%s
                            """,
                            (current["status"], object_id, user["id"]),
                        )
                    # Always fetch current Stripe state under the customer lock;
                    # delivery order and event creation timestamps are not authority.
                    for subscription in self.gateway.subscriptions(customer):
                        self._subscription(cur, user["id"], customer, subscription["id"])
                    if event_type.startswith("payment_intent."):
                        self._payment(cur, user["id"], customer, object_id)
                    if event_type == "charge.refunded" or event_type.startswith("refund."):
                        charge = (
                            self.gateway.charge(object_id)
                            if event_type == "charge.refunded"
                            else self.gateway.charge(
                                reference(self.gateway.refund(object_id)["charge"])
                            )
                        )
                        verify_customer(charge, customer)
                        self._payment(
                            cur, user["id"], customer, reference(charge["payment_intent"])
                        )
                cur.execute(
                    """
                    UPDATE cedar_press_webhook_events SET status=%s, processed_at=now(),
                    error_code=NULL WHERE id=%s
                    """,
                    ("processed" if user and supported else "ignored", event["id"]),
                )

            self.guests.send_claim(customer)
        except Exception:
            self.db.execute(
                """
                UPDATE cedar_press_webhook_events SET status='failed',
                attempts=attempts+1, error_code='RECONCILIATION_FAILED' WHERE id=%s
                """,
                (event["id"],),
            )
            raise
