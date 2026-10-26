"""Stripe boundaries and lifecycle contracts; synthetic provider data, real PostgreSQL."""

from __future__ import annotations

import asyncio
import copy
import datetime as dt
import hashlib
import hmac
import json
import os
import threading
import time
import unittest
import uuid
from unittest import mock
from urllib.parse import urlsplit, urlunsplit

import stripe
from fastapi.testclient import TestClient

from cedar_press import db, session, subscribers
from cedar_press.billing.dependencies import create_billing_services, get_billing_services
from cedar_press.billing.policy import (
    AMOUNTS,
    BillingError,
    cohort_at,
    coverage,
    instant,
    price_for,
    prices,
    validate_price,
)
from cedar_press.billing.service import BillingService
from cedar_press.billing.stripe_gateway import API_VERSION, StripeGateway, stripe_url
from cedar_press.billing.support import application_url

PRICE_MAP = {
    cohort: {tier: f"price_{cohort}_{tier}" for tier in amounts}
    for cohort, amounts in AMOUNTS.items()
}
SETTINGS = {
    "CEDAR_PRESS_STRIPE_PRICES": json.dumps(PRICE_MAP),
    "CEDAR_PRESS_STRIPE_LEGACY_PRICES": "[]",
    "CEDAR_PRESS_STRIPE_SECRET_KEY": "sk_test_synthetic",
    "CEDAR_PRESS_STRIPE_MODE": "test",
    "CEDAR_PRESS_APP_URL": "http://localhost:5173",
    "CEDAR_PRESS_ENVIRONMENT": "development",
    "CEDAR_PRESS_INSECURE_COOKIE": "1",
    "CEDAR_PRESS_STRIPE_WEBHOOK_SECRET": "whsec_synthetic",
}
PG = os.environ.get("CEDAR_PRESS_TEST_DATABASE_URL", "")


def price_data(tier="press", cohort="early_access"):
    return {
        "id": PRICE_MAP[cohort][tier],
        "unit_amount": AMOUNTS[cohort][tier],
        "currency": "usd",
        "type": "recurring",
        "livemode": False,
        "recurring": {"interval": "year", "interval_count": 1},
        "product": "prod_" + tier,
    }


class FakeGateway:
    livemode = False

    def __init__(self):
        self.subs = []
        self.invoice_rows = []
        self.line_rows = []
        self.refund_rows = []
        self.sessions = {}
        self.attempts = []
        self.fail_checkout = False
        self.fail_subscription = False
        self.amount = 50_000

    def price(self, price_id):
        return next(
            price_data(tier, cohort)
            for cohort in AMOUNTS
            for tier in AMOUNTS[cohort]
            if PRICE_MAP[cohort][tier] == price_id
        )

    def customer(self, user):
        return "cus_" + str(user["id"])

    def subscriptions(self, customer):
        return copy.deepcopy(self.subs)

    def subscription(self, subscription_id):
        if self.fail_subscription:
            raise stripe.APIConnectionError("synthetic provider timeout")
        return copy.deepcopy(next(s for s in self.subs if s["id"] == subscription_id))

    def invoice(self, invoice_id):
        return copy.deepcopy(next(i for i in self.invoice_rows if i["id"] == invoice_id))

    def invoices(self, subscription_id):
        return copy.deepcopy(self.invoice_rows)

    def lines(self, invoice_id):
        return copy.deepcopy(self.line_rows)

    def invoice_payments(self, invoice_id):
        return [{"payment": {"payment_intent": "pi_fixture"}}]

    def payment(self, payment_id):
        return {
            "id": payment_id,
            "customer": self.subs[0]["customer"],
            "latest_charge": "ch_fixture",
            "status": "succeeded",
            "currency": "usd",
            "amount": self.amount,
            "amount_received": self.amount,
            "created": int(time.time()),
        }

    def refunds(self, charge_id):
        return copy.deepcopy(self.refund_rows)

    def promotion(self, code):
        if code != "SUMMIT":
            raise BillingError("DISCOUNT_INVALID", "That discount code is not available.")
        return "promo_fixture"

    def checkout(self, customer, attempt, app_url):
        key = str(attempt["id"])
        self.attempts.append(key)
        self.sessions.setdefault(
            key,
            {
                "id": "cs_" + key,
                "status": "open",
                "customer": customer,
                "url": "https://checkout.stripe.com/c/pay/fixture",
            },
        )
        if self.fail_checkout:
            self.fail_checkout = False
            raise stripe.APIConnectionError("synthetic lost response after creation")
        return copy.deepcopy(self.sessions[key])

    def checkout_status(self, session_id):
        return copy.deepcopy(next(s for s in self.sessions.values() if s["id"] == session_id))

    def find_checkout(self, customer, attempt_id, **kwargs):
        return copy.deepcopy(self.sessions.get(attempt_id))

    def expire_checkout(self, session_id):
        for value in self.sessions.values():
            if value["id"] == session_id:
                value["status"] = "expired"
                return copy.deepcopy(value)
        raise AssertionError("Unknown checkout")

    def portal(self, customer, cohort, app_url, change_plan=False, subscription_id=None):
        return "https://billing.stripe.com/p/session/fixture"


class TestBillingPolicy(unittest.TestCase):
    def setUp(self):
        patch = mock.patch.dict(os.environ, SETTINGS)
        patch.start()
        self.addCleanup(patch.stop)

    def install_services(self):
        from cedar_press.app import app

        self.services = create_billing_services(gateway=mock.Mock())
        app.dependency_overrides[get_billing_services] = lambda: self.services
        self.addCleanup(app.dependency_overrides.clear)

    def test_billing_routes_require_identity_and_reject_foreign_origins(self):
        self.install_services()
        from cedar_press.app import app
        from cedar_press.session import current_session

        app.dependency_overrides[current_session] = lambda: None
        self.addCleanup(app.dependency_overrides.clear)
        client = TestClient(app)
        self.assertEqual(client.get("/billing").status_code, 401)
        self.assertEqual(client.post("/billing/portal").status_code, 401)
        app.dependency_overrides[current_session] = lambda: session.Session(
            "test@example.invalid", "free"
        )
        with mock.patch.object(self.services.billing, "portal") as portal:
            self.assertEqual(
                client.post(
                    "/billing/change-plan", headers={"Origin": "https://untrusted.invalid"}
                ).status_code,
                403,
            )
            portal.assert_not_called()
            portal.return_value = {"url": "https://billing.stripe.com/p/session/fixture"}
            response = client.post(
                "/billing/change-plan", headers={"Origin": "http://localhost:5173"}
            )
            self.assertEqual(response.status_code, 200)
            portal.assert_called_once_with("test@example.invalid", True, None)

    def test_webhook_processing_runs_off_the_event_loop(self):
        from cedar_press.billing.routes import webhook

        event = {
            "id": "evt_thread",
            "type": "invoice.paid",
            "api_version": API_VERSION,
            "data": {"object": {"id": "in_thread"}},
        }
        payload = json.dumps(event).encode()
        timestamp = int(time.time())
        signature = hmac.new(
            b"whsec_synthetic", str(timestamp).encode() + b"." + payload, hashlib.sha256
        ).hexdigest()
        request = mock.Mock()
        request.headers = {"stripe-signature": f"t={timestamp},v1={signature}"}

        async def stream():
            yield payload

        request.stream = stream
        services = create_billing_services(gateway=mock.Mock())
        entered, release = threading.Event(), threading.Event()
        worker_threads = []

        def slow_processing(event):
            worker_threads.append(threading.get_ident())
            entered.set()
            release.wait(2)

        async def check():
            main_thread = threading.get_ident()
            timer = threading.Timer(2, release.set)
            timer.start()
            try:
                with mock.patch.object(
                    services.reconciler, "process_event", side_effect=slow_processing
                ):
                    task = asyncio.create_task(webhook(request, services))
                    self.assertTrue(await asyncio.to_thread(entered.wait, 1))
                    self.assertNotEqual(worker_threads[0], main_thread)
                    await asyncio.sleep(0)
                    self.assertFalse(task.done())
                    release.set()
                    self.assertEqual(await task, {"received": True})
            finally:
                release.set()
                timer.cancel()

        asyncio.run(check())

    def test_annual_offer_boundary_is_central_time(self):
        self.assertEqual(
            cohort_at(dt.datetime(2027, 1, 1, 5, 59, tzinfo=dt.timezone.utc)), "early_access"
        )
        self.assertEqual(
            cohort_at(dt.datetime(2027, 1, 1, 6, 0, tzinfo=dt.timezone.utc)), "standard"
        )
        self.assertEqual(price_for("press_pro", "early_access").amount, 100_000)

    def test_missing_duplicate_and_wrong_prices_are_refused(self):
        for invalid in ({}, {"early_access": {"press": "price_same"}}):
            with (
                mock.patch.dict(os.environ, {"CEDAR_PRESS_STRIPE_PRICES": json.dumps(invalid)}),
                self.assertRaises(BillingError),
            ):
                prices()
        for change in (
            {"unit_amount": 1},
            {"currency": "eur"},
            {"recurring": {"interval": "month", "interval_count": 1}},
        ):
            with self.assertRaises(BillingError):
                validate_price({**price_data(), **change}, price_for("press", "early_access"))
        validate_price(price_data(), price_for("press", "early_access"))

    def test_legacy_prices_remain_recognized_but_new_purchases_use_named_tier_prices(self):
        legacy = [{"id": "price_previous", "tier": "press_pro", "cohort": "early_access"}]
        with mock.patch.dict(os.environ, {"CEDAR_PRESS_STRIPE_LEGACY_PRICES": json.dumps(legacy)}):
            from cedar_press.billing.policy import identify_price

            self.assertEqual(identify_price("price_previous").tier, "press_pro")
            self.assertEqual(
                price_for("press_pro", "early_access").id, PRICE_MAP["early_access"]["press_pro"]
            )

    def test_invoice_coverage_uses_positive_recognized_lines(self):
        line = {"price": price_data(), "amount": 50_000, "period": {"start": 1, "end": 20}}
        self.assertEqual(coverage([line])[0], "press")
        self.assertEqual(coverage([{**line, "amount": -1}]), (None, None, None))
        self.assertEqual(coverage([{**line, "price": "price_unrelated"}]), (None, None, None))
        with self.assertRaises(BillingError):
            coverage([{**line, "period": {"start": 20, "end": 1}}])
        with self.assertRaises(BillingError):
            instant(True)

    def test_redirects_and_app_origin_are_not_caller_controlled(self):
        for url in (
            "javascript:alert(1)",
            "https://stripe.com.evil.invalid",
            "http://checkout.stripe.com",
            "https://x@checkout.stripe.com",
        ):
            with self.assertRaises(BillingError):
                stripe_url(url)
        self.assertEqual(
            stripe_url("https://checkout.stripe.com/c/test"), "https://checkout.stripe.com/c/test"
        )
        with (
            mock.patch.dict(
                os.environ, {"CEDAR_PRESS_APP_URL": "https://example.org/redirect?next=x"}
            ),
            self.assertRaises(BillingError),
        ):
            application_url()

    def test_real_sdk_client_is_pinned_and_keys_are_mode_checked(self):
        gateway = StripeGateway()
        self.assertFalse(gateway.livemode)
        with (
            mock.patch.dict(os.environ, {"CEDAR_PRESS_STRIPE_MODE": "live"}),
            self.assertRaises(BillingError),
        ):
            StripeGateway()

    def test_signed_webhook_signature_and_version_checked_before_processing(self):
        from cedar_press.app import app

        client = TestClient(app)
        event = {
            "id": "evt_fixture",
            "object": "event",
            "type": "invoice.paid",
            "api_version": API_VERSION,
            "livemode": False,
            "data": {"object": {"id": "in_fixture"}},
        }
        body = json.dumps(event).encode()
        timestamp = int(time.time())
        signature = hmac.new(
            b"whsec_synthetic", str(timestamp).encode() + b"." + body, hashlib.sha256
        ).hexdigest()
        header = f"t={timestamp},v1={signature}"
        self.install_services()
        with mock.patch.object(self.services.reconciler, "process_event") as process:
            self.assertEqual(
                client.post(
                    "/billing/webhook", content=body, headers={"Stripe-Signature": "invalid"}
                ).status_code,
                400,
            )
            process.assert_not_called()
            self.assertEqual(
                client.post(
                    "/billing/webhook", content=body, headers={"Stripe-Signature": header}
                ).status_code,
                200,
            )
            process.assert_called_once_with(event)


@unittest.skipUnless(PG, "set CEDAR_PRESS_TEST_DATABASE_URL")
class TestBillingPostgres(unittest.TestCase):
    def setUp(self):
        import psycopg
        from psycopg import sql

        self.psycopg = psycopg
        self.name = "press_billing_" + uuid.uuid4().hex
        with psycopg.connect(PG, autocommit=True) as connection:
            connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(self.name)))
        self.addCleanup(self.drop_database)
        url = urlunsplit(urlsplit(PG)._replace(path="/" + self.name))
        patch = mock.patch.dict(os.environ, {**SETTINGS, "DATABASE_URL": url})
        patch.start()
        self.addCleanup(patch.stop)
        db.reset_for_tests()
        self.addCleanup(db.reset_for_tests)
        db.migrate()
        subscribers.create("reader@example.org", "existing-password", "press")
        self.user = db.one("SELECT * FROM cedar_press_subscribers WHERE email='reader@example.org'")
        self.customer = "cus_" + str(self.user["id"])
        db.execute(
            "UPDATE cedar_press_subscribers SET stripe_customer_id=%s WHERE id=%s",
            (self.customer, self.user["id"]),
        )
        self.gateway = FakeGateway()
        self.services = create_billing_services(gateway=self.gateway)
        self.billing = self.services.billing
        self.reconciler = self.services.reconciler
        from cedar_press.app import app

        app.dependency_overrides[get_billing_services] = lambda: self.services
        self.addCleanup(app.dependency_overrides.clear)

    def drop_database(self):
        from psycopg import sql

        with self.psycopg.connect(PG, autocommit=True) as connection:
            connection.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(self.name))
            )

    def paid_subscription(self, tier="press", cohort="early_access", status="active", paid=True):
        timestamp = int(time.time())
        self.gateway.amount = AMOUNTS[cohort][tier]
        self.gateway.subs = [
            {
                "id": "sub_fixture",
                "customer": self.customer,
                "status": status,
                "cancel_at_period_end": False,
                "latest_invoice": "in_fixture",
                "items": {
                    "data": [
                        {
                            "quantity": 1,
                            "price": price_data(tier, cohort),
                            "current_period_end": timestamp + 86400,
                        }
                    ]
                },
            }
        ]
        self.gateway.invoice_rows = [
            {
                "id": "in_fixture",
                "customer": self.customer,
                "parent": {"subscription_details": {"subscription": "sub_fixture"}},
                "status": "paid" if paid else "open",
                "currency": "usd",
                "amount_due": self.gateway.amount,
                "amount_paid": self.gateway.amount if paid else 0,
                "created": timestamp,
                "hosted_invoice_url": "https://invoice.stripe.com/i/fixture",
            }
        ]
        self.gateway.line_rows = [
            {
                "pricing": {"price_details": {"price": PRICE_MAP[cohort][tier]}},
                "amount": self.gateway.amount,
                "period": {"start": timestamp - 10, "end": timestamp + 86400},
            }
        ]

    def event(self, event_id="evt_fixture", event_type="customer.subscription.updated"):
        return {
            "id": event_id,
            "type": event_type,
            "livemode": False,
            "data": {"object": {"id": "sub_fixture", "customer": self.customer}},
        }

    def test_confirmed_payment_updates_access_and_records_transactions(self):
        self.paid_subscription(tier="press_pro")
        cookie = session._encode(session.Session(self.user["email"], "press"))
        self.reconciler.process_event(self.event())
        self.assertEqual(subscribers.find(self.user["email"]).tier, "press_pro")
        self.assertEqual(session._decode(cookie).tier, "press_pro")
        self.assertEqual(db.one("SELECT count(*) AS n FROM cedar_press_invoices")["n"], 1)
        self.assertEqual(db.one("SELECT count(*) AS n FROM cedar_press_payments")["n"], 1)
        self.assertEqual(db.one("SELECT tier FROM cedar_press_subscribers")["tier"], "press")

    def test_duplicates_and_old_events_use_current_provider_state(self):
        self.paid_subscription()
        self.reconciler.process_event(self.event())
        self.reconciler.process_event(self.event())
        self.assertEqual(db.one("SELECT attempts FROM cedar_press_webhook_events")["attempts"], 1)
        self.gateway.subs[0]["status"] = "canceled"
        self.reconciler.process_event(self.event("evt_old"))
        self.assertEqual(subscribers.find(self.user["email"]).tier, "free")
        self.assertEqual(
            db.one("""
            SELECT count(*) AS n FROM cedar_press_access_grants WHERE
            source='legacy' AND revoked_at IS NULL
            """)["n"],
            1,
        )
        self.assertEqual(db.one("SELECT count(*) AS n FROM cedar_press_subscriptions")["n"], 1)

    def test_provider_failure_is_durable_and_retryable(self):
        self.paid_subscription()
        self.gateway.fail_subscription = True
        with self.assertRaises(stripe.APIConnectionError):
            self.reconciler.process_event(self.event())
        self.assertEqual(
            db.one("SELECT status FROM cedar_press_webhook_events")["status"], "failed"
        )
        self.assertEqual(db.one("SELECT count(*) AS n FROM cedar_press_subscriptions")["n"], 0)
        self.gateway.fail_subscription = False
        self.reconciler.process_event(self.event())
        self.assertEqual(
            db.one("SELECT status FROM cedar_press_webhook_events")["status"], "processed"
        )

    def test_failed_renewal_cannot_extend_paid_access(self):
        self.paid_subscription()
        self.reconciler.process_event(self.event())
        self.gateway.subs[0]["status"] = "past_due"
        self.gateway.line_rows[0]["period"] = {
            "start": int(time.time()) - 100,
            "end": int(time.time()) - 1,
        }
        self.reconciler.process_event(self.event("evt_failed"))
        self.assertEqual(subscribers.find(self.user["email"]).tier, "free")

    def test_cancel_at_term_end_keeps_paid_access(self):
        self.paid_subscription()
        self.gateway.subs[0]["cancel_at_period_end"] = True
        self.reconciler.process_event(self.event())
        self.assertEqual(subscribers.find(self.user["email"]).tier, "press")

    def test_partial_and_full_refund_history_affects_paid_coverage(self):
        self.paid_subscription()
        self.gateway.refund_rows = [
            {
                "id": "re_fixture",
                "payment_intent": "pi_fixture",
                "status": "succeeded",
                "amount": 100,
                "currency": "usd",
                "created": int(time.time()),
            }
        ]
        self.reconciler.process_event(self.event())
        self.assertEqual(subscribers.find(self.user["email"]).tier, "press")
        self.gateway.refund_rows[0]["amount"] = 50_000
        self.reconciler.process_event(self.event("evt_full_refund"))
        self.assertEqual(subscribers.find(self.user["email"]).tier, "free")
        self.assertEqual(db.one("SELECT amount FROM cedar_press_refunds")["amount"], 50_000)

    def test_checkout_retries_reuse_persisted_intent_and_never_grant_access(self):
        self.gateway.fail_checkout = True
        with self.assertRaises(stripe.APIConnectionError):
            self.billing.checkout(self.user["email"], "press", "SUMMIT")
        result = self.billing.checkout(self.user["email"], "press", "SUMMIT")
        self.assertTrue(result["url"].startswith("https://checkout.stripe.com/"))
        self.assertEqual(len(set(self.gateway.attempts)), 1)
        self.assertEqual(len(self.gateway.sessions), 1)
        self.assertIsNone(db.one("SELECT activated_at FROM cedar_press_subscriptions LIMIT 1"))

    def test_revised_plan_expires_the_owned_open_session_before_replacement(self):
        self.billing.checkout(self.user["email"], "press")
        original = db.one("SELECT * FROM cedar_press_checkout_attempts")
        self.billing.checkout(self.user["email"], "press_pro", "SUMMIT", True)
        self.assertEqual(self.gateway.checkout_status(original["session_id"])["status"], "expired")
        rows = db.query(
            "SELECT tier,status,promotion_id FROM cedar_press_checkout_attempts ORDER BY created_at"
        )
        self.assertEqual(
            [(r["tier"], r["status"]) for r in rows], [("press", "expired"), ("press_pro", "open")]
        )
        self.assertEqual(rows[1]["promotion_id"], "promo_fixture")

    def test_replacement_does_not_create_checkout_when_original_is_processing(self):
        self.billing.checkout(self.user["email"], "press")
        with mock.patch.object(
            self.gateway, "expire_checkout", return_value={"status": "complete"}
        ), self.assertRaises(BillingError) as error:
            self.billing.checkout(self.user["email"], "press_pro", replace_open=True)
        self.assertEqual(error.exception.code, "CHECKOUT_PROCESSING")
        self.assertEqual(db.one("SELECT count(*) AS n FROM cedar_press_checkout_attempts")["n"], 1)

    def test_completed_checkout_blocks_a_second_purchase_before_webhook(self):
        self.billing.checkout(self.user["email"], "press")
        first = next(iter(self.gateway.sessions.values()))
        first["status"] = "complete"
        with self.assertRaises(BillingError) as caught:
            self.billing.checkout(self.user["email"], "press")
        self.assertEqual(caught.exception.code, "CHECKOUT_PROCESSING")
        self.assertEqual(len(self.gateway.sessions), 1)

    def test_aged_pending_checkout_recovers_lost_response(self):
        self.gateway.fail_checkout = True
        with self.assertRaises(stripe.APIConnectionError):
            self.billing.checkout(self.user["email"], "press")
        with db.pool().connection() as conn:
            conn.execute("UPDATE cedar_press_checkout_attempts SET expires_at=now()")
        self.billing.checkout(self.user["email"], "press")
        self.assertEqual(len(self.gateway.sessions), 1)
        self.assertEqual(
            db.one("SELECT status FROM cedar_press_checkout_attempts")["status"], "open"
        )

    def test_new_subscriptions_after_cutoff_use_standard_price(self):
        future = dt.datetime(2027, 2, 1, tzinfo=dt.timezone.utc)
        service = BillingService(gateway=self.gateway, clock=lambda: future)
        service.checkout(self.user["email"], "press")
        self.assertEqual(
            db.one("SELECT cohort FROM cedar_press_checkout_attempts")["cohort"], "standard"
        )
        with self.assertRaises(BillingError):
            service.checkout(self.user["email"], "press", "SUMMIT")

    def test_wrong_customer_and_duplicate_subscription_are_refused(self):
        self.paid_subscription()
        with self.assertRaises(BillingError) as caught:
            self.billing.checkout(self.user["email"], "press")
        self.assertEqual(caught.exception.code, "SUBSCRIPTION_EXISTS")
        self.gateway.subs[0]["customer"] = "cus_someone_else"
        with self.assertRaises(BillingError):
            self.reconciler.process_event(self.event())
        self.assertEqual(db.one("SELECT count(*) AS n FROM cedar_press_subscriptions")["n"], 0)

    def test_resubscribed_account_portal_uses_active_cohort(self):
        for sub_id, cohort, status in (
            ("sub_old", "early_access", "canceled"),
            ("sub_new", "standard", "active"),
        ):
            db.execute(
                "INSERT INTO cedar_press_subscriptions(id,user_id,price_id,tier,cohort,status) "
                "VALUES (%s,%s,%s,'press',%s,%s)",
                (sub_id, self.user["id"], PRICE_MAP[cohort]["press"], cohort, status),
            )
        with mock.patch.object(
            self.gateway, "portal", return_value="https://billing.stripe.com/p/session/fixture"
        ) as portal:
            self.billing.portal(self.user["email"], subscription_id="sub_new")
            portal.assert_called_once_with(
                self.customer, "standard", "http://localhost:5173", False, "sub_new"
            )

    def test_every_subscription_has_an_owned_management_target(self):
        for sub_id, customer in (("sub_one", self.customer), ("sub_two", "cus_second")):
            db.execute(
                """INSERT INTO cedar_press_subscriptions
                (id,user_id,price_id,tier,cohort,status,customer_id)
                VALUES (%s,%s,%s,'press','early_access','active',%s)""",
                (sub_id, self.user["id"], PRICE_MAP["early_access"]["press"], customer),
            )
        with mock.patch.object(
            self.gateway, "portal", return_value="https://billing.stripe.com/p/session/fixture"
        ) as portal:
            for sub_id, customer in (("sub_one", self.customer), ("sub_two", "cus_second")):
                self.billing.portal(self.user["email"], subscription_id=sub_id)
                self.assertEqual(portal.call_args.args[0], customer)
                self.assertEqual(portal.call_args.args[-1], sub_id)
            count = portal.call_count
            for target in (None, "sub_other_users"):
                with self.assertRaises(BillingError):
                    self.billing.portal(self.user["email"], subscription_id=target)
            self.assertEqual(portal.call_count, count)

    def test_webhook_fetches_only_affected_invoice_without_open_transaction(self):
        self.paid_subscription()
        original = self.gateway.invoice

        def checked_invoice(invoice_id):
            with self.psycopg.connect(db.url(), autocommit=True) as monitor:
                row = monitor.execute("""SELECT count(*) FROM pg_stat_activity
                    WHERE datname=current_database() AND state='idle in transaction'""").fetchone()
                self.assertEqual(row[0], 0)
            return original(invoice_id)

        event = self.event("evt_invoice", "invoice.paid")
        event["data"]["object"]["id"] = "in_fixture"
        with (
            mock.patch.object(self.gateway, "invoices", side_effect=AssertionError("full scan")),
            mock.patch.object(
                self.gateway, "subscriptions", side_effect=AssertionError("full scan")
            ),
            mock.patch.object(self.gateway, "invoice", side_effect=checked_invoice),
        ):
            self.reconciler.process_event(event)
        self.assertEqual(subscribers.find(self.user["email"]).tier, "press")

    def test_expired_user_can_sign_in_and_manage_billing_but_not_content(self):
        from cedar_press.app import app

        self.paid_subscription(status="canceled")
        self.reconciler.process_event(self.event())
        app.dependency_overrides.clear()
        app.dependency_overrides[get_billing_services] = lambda: self.services
        client = TestClient(app)
        response = client.post(
            "/auth/login", json={"email": self.user["email"], "password": "existing-password"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["workspace_tier"], "free")
        self.assertEqual(client.get("/billing").status_code, 200)
        self.assertEqual(client.get("/press/collections").status_code, 403)
        self.assertEqual(client.get("/me").status_code, 200)
        subscribers.change_password(self.user["email"], "another-password")
        self.assertEqual(db.one("SELECT tier FROM cedar_press_subscribers")["tier"], "press")
