"""Canonical Stripe reconciliation and durable webhook processing."""

from __future__ import annotations

from contextlib import contextmanager

from cedar_press import db
from cedar_press.billing.adapters.stripe import BillingAdapter, StripeAdapter, stripe_url
from cedar_press.billing.errors import BillingError
from cedar_press.billing.pricing import RANK, identify_price, validate_price
from cedar_press.billing.utils import instant, reference, verify_customer, verify_write


def coverage(lines: list[dict]):
    candidates = []
    for line in lines:
        price_id = line.get("price") or (line.get("pricing") or {}).get("price_details", {}).get(
            "price"
        )
        if not price_id or line.get("amount", 0) < 0:
            continue
        try:
            price = identify_price(price_id)
        except BillingError:
            continue  # Tax or unrelated invoice lines never establish Press access.
        period = line.get("period") or {}
        start, end = instant(period.get("start")), instant(period.get("end"))
        if end <= start:
            raise BillingError("BILLING_DATA_INVALID", "Invoice access dates are invalid.", 502)
        candidates.append((price.tier, start, end))
    return max(candidates, key=lambda c: (RANK[c[0]], c[2])) if candidates else (None, None, None)


class BillingReconciler:
    """Synchronize provider state while keeping transaction boundaries visible."""

    def __init__(
        self,
        checkout_service,
        delivery_service,
        *,
        adapter: BillingAdapter | None = None,
        database=db,
    ):
        self.checkout = checkout_service
        self.delivery = delivery_service
        self._adapter = adapter
        self.db = database

    @property
    def adapter(self):
        if self._adapter is None:
            self._adapter = StripeAdapter()
        return self._adapter

    def _payment(self, cur, user_id, customer, snapshot, invoice_id=None):
        payment, refunds = snapshot
        payment_id = payment["id"]
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
            for refund in refunds:
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

    def _subscription(self, cur, user_id, customer, snapshot):
        subscription, invoices = snapshot
        subscription_id = subscription["id"]
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
        for invoice, lines, payments in invoices:
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
            tier, start, end = coverage(lines)
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
            for payment in payments:
                self._payment(cur, user_id, customer, payment, invoice["id"])
        if activated:
            cur.execute(
                """
                UPDATE cedar_press_subscriptions SET activated_at=COALESCE(activated_at,
                now()) WHERE id=%s
                """,
                (subscription_id,),
            )

    def _load_payment(self, payment_id):
        payment = self.adapter.payment(payment_id)
        charge = reference(payment.get("latest_charge"))
        return payment, self.adapter.refunds(charge) if charge else []

    def _load_subscription(self, subscription_id, *, full=False, invoice=None):
        subscription = self.adapter.subscription(subscription_id)
        if full:
            invoices = self.adapter.invoices(subscription_id)
        elif invoice:
            invoices = [invoice]
        else:
            latest = reference(subscription.get("latest_invoice"))
            invoices = [self.adapter.invoice(latest)] if latest else []
        snapshots = []
        for row in invoices:
            payments = []
            for record in self.adapter.invoice_payments(row["id"]):
                payment_id = reference((record.get("payment") or {}).get("payment_intent"))
                if payment_id:
                    payments.append(self._load_payment(payment_id))
            snapshots.append((row, self.adapter.lines(row["id"]), payments))
        return subscription, snapshots

    @contextmanager
    def _customer_connection(self, customer):
        # Serialize canonical reads and writes without an open transaction while
        # Stripe is contacted. Use this same connection for all SQL in the scope,
        # including activation, so a pool of one remains usable.
        with self.db.pool().connection() as conn:
            previous = conn.autocommit
            conn.autocommit = True
            try:
                conn.execute("SELECT pg_advisory_lock(hashtextextended(%s,0))", (customer,))
                yield conn
            finally:
                try:
                    conn.execute("SELECT pg_advisory_unlock(hashtextextended(%s,0))", (customer,))
                finally:
                    conn.autocommit = previous

    def reconcile_customer(self, customer):
        with self._customer_connection(customer) as conn, conn.cursor() as cur:
            user = self.checkout.owner(cur, customer)
            prepared = self.checkout.prepare_activation(cur, customer) if not user else None
            if not user and not prepared:
                return False
            snapshots = [
                self._load_subscription(s["id"], full=True)
                for s in self.adapter.subscriptions(customer)
            ]
            with conn.transaction():
                if not user:
                    user = self.checkout.activate(cur, customer, prepared)
                for snapshot in snapshots:
                    self._subscription(cur, user["id"], customer, snapshot)
        self.delivery.send_claim(customer)
        return True

    def process_event(self, event):
        obj = event["data"]["object"]
        event_type, object_id = event["type"], obj["id"]
        if event.get("livemode") is not self.adapter.livemode:
            raise BillingError("WEBHOOK_MODE_INVALID", "Webhook mode does not match this service.")
        customer = reference(obj.get("customer"))
        self.db.execute(
            """INSERT INTO cedar_press_webhook_events(id,event_type,object_id,customer_id)
            VALUES (%s,%s,%s,%s) ON CONFLICT(id) DO NOTHING""",
            (event["id"], event_type, object_id, customer),
        )
        try:
            # Resolve the customer for refund events before taking its session lock.
            if event_type.startswith("refund."):
                charge = self.adapter.charge(reference(self.adapter.refund(object_id)["charge"]))
                customer = reference(charge.get("customer"))
            with self._customer_connection(customer or event["id"]) as conn, conn.cursor() as cur:
                cur.execute(
                    "SELECT status FROM cedar_press_webhook_events WHERE id=%s", (event["id"],)
                )
                done = cur.fetchone()["status"] in {"processed", "ignored"}
                if not done:
                    user = self.checkout.owner(cur, customer)
                    supported = (
                        event_type.startswith(
                            (
                                "customer.subscription.",
                                "invoice.",
                                "payment_intent.",
                                "refund.",
                                "checkout.session.",
                            )
                        )
                        or event_type == "charge.refunded"
                    )
                    prepared = (
                        self.checkout.prepare_activation(cur, customer)
                        if customer and supported and not user
                        else None
                    )
                    subscription_id, invoice, payment, checkout = None, None, None, None
                    if (user or prepared) and supported:
                        if event_type.startswith("customer.subscription."):
                            subscription_id = object_id
                        elif event_type.startswith("invoice."):
                            invoice = self.adapter.invoice(object_id)
                            verify_customer(invoice, customer)
                            subscription_id = reference(
                                invoice.get("subscription")
                                or (invoice.get("parent") or {})
                                .get("subscription_details", {})
                                .get("subscription")
                            )
                        elif event_type.startswith("checkout.session."):
                            checkout = self.adapter.checkout_status(object_id)
                            verify_customer(checkout, customer)
                            subscription_id = reference(checkout.get("subscription"))
                        elif event_type.startswith("payment_intent."):
                            payment = self._load_payment(object_id)
                        else:
                            charge = (
                                self.adapter.charge(object_id)
                                if event_type == "charge.refunded"
                                else self.adapter.charge(
                                    reference(self.adapter.refund(object_id)["charge"])
                                )
                            )
                            verify_customer(charge, customer)
                            payment = self._load_payment(reference(charge.get("payment_intent")))
                        # Initial activation also needs its paid invoice even if
                        # the first delivery happens to be a payment/refund event.
                        if not subscription_id and prepared:
                            subscription_id = reference(prepared[1].get("subscription"))
                    snapshot = (
                        self._load_subscription(subscription_id, invoice=invoice)
                        if subscription_id
                        else None
                    )
                    with conn.transaction():
                        if not user and prepared:
                            user = self.checkout.activate(cur, customer, prepared)
                        if user and snapshot:
                            self._subscription(cur, user["id"], customer, snapshot)
                        if user and payment:
                            self._payment(cur, user["id"], customer, payment)
                        if user and checkout:
                            cur.execute(
                                "UPDATE cedar_press_checkout_attempts SET status=%s "
                                "WHERE session_id=%s AND user_id=%s",
                                (checkout["status"], object_id, user["id"]),
                            )
                        cur.execute(
                            """UPDATE cedar_press_webhook_events SET status=%s,
                            customer_id=%s,processed_at=now(),error_code=NULL,attempts=attempts+1
                            WHERE id=%s""",
                            (
                                "processed" if user and supported else "ignored",
                                customer,
                                event["id"],
                            ),
                        )
        except Exception:
            self.db.execute(
                """UPDATE cedar_press_webhook_events SET status='failed',
                attempts=attempts+1,error_code='RECONCILIATION_FAILED' WHERE id=%s""",
                (event["id"],),
            )
            raise
        # Delivery failure leaves financial state processed. A duplicate webhook
        # or the repair command retries the separately persisted email job.
        self.delivery.send_claim(customer)
