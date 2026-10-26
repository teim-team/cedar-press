"""Guest purchase boundaries: existing accounts, paid provisioning and mailbox proof."""

import concurrent.futures
import os
import threading
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlsplit

import stripe
from fastapi.testclient import TestClient

from cedar_press import accounts, db, ratelimit, subscribers
from cedar_press.account_email import AccountEmailSender
from cedar_press.billing.dependencies import create_billing_services
from cedar_press.billing.policy import BillingError
from tests import test_billing as fixtures
from tests.test_billing import PG, FakeGateway

EMAIL = "guest@example.invalid"
SECRET = "synthetic-browser-secret-for-testing-only"


class GuestGateway(FakeGateway):
    def checkout(self, customer, attempt, app_url, guest=False):
        result = super().checkout(customer, attempt, app_url)
        result.update(
            {
                "metadata": {"cedar_press_guest_id": str(attempt["id"])},
                "client_reference_id": str(attempt["id"]),
                "payment_status": "unpaid",
            }
        )
        self.sessions[str(attempt["id"])] = result
        return result

    def guest_session(self, customer):
        return next(
            (session for session in self.sessions.values() if session.get("customer") == customer),
            None,
        )


@unittest.skipUnless(PG, "set CEDAR_PRESS_TEST_DATABASE_URL")
class TestGuestCheckout(unittest.TestCase):
    setUp_database = fixtures.TestBillingPostgres.setUp
    drop_database = fixtures.TestBillingPostgres.drop_database
    paid_subscription = fixtures.TestBillingPostgres.paid_subscription
    event = fixtures.TestBillingPostgres.event

    def setUp(self):
        self.setUp_database()
        self.gateway = GuestGateway()
        self.sender = mock.Mock(spec=AccountEmailSender)
        self.sender.configured.return_value = True
        self.mail = self.sender.send_link
        self.services = create_billing_services(gateway=self.gateway, email_sender=self.sender)
        self.service = self.services.guest
        self.billing = self.services.billing
        self.reconciler = self.services.reconciler

    def start(self, secret=SECRET):
        return self.service.start("press", secret)

    def complete(self, paid=True, email=EMAIL):
        row = db.one("SELECT * FROM cedar_press_guest_checkouts ORDER BY created_at DESC LIMIT 1")
        self.customer = "cus_guest_" + str(row["id"])
        self.paid_subscription()
        session = self.gateway.sessions[str(row["id"])]
        session.update(
            status="complete",
            customer=self.customer,
            payment_status="paid" if paid else "unpaid",
            subscription="sub_fixture",
            customer_details={"email": email},
        )
        return self.event()

    def test_checkout_is_public_without_email_or_account_and_sets_httponly_cookie(self):
        from cedar_press.app import app

        client = TestClient(app)
        response = client.post("/billing/guest/checkout", json={"tier": "press"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("HttpOnly", response.headers["set-cookie"])
        self.assertNotIn(SECRET, response.text)
        self.assertEqual(client.get("/billing/guest/status").json()["status"], "open")
        self.assertEqual(TestClient(app).get("/billing/guest/status").status_code, 404)
        self.assertIsNone(subscribers.find(EMAIL))
        row = db.one("SELECT email,customer_id FROM cedar_press_guest_checkouts")
        self.assertIsNone(row["email"])
        self.assertIsNone(row["customer_id"])

    def test_unpaid_checkout_does_not_create_an_account_or_send_claim(self):
        self.start()
        self.reconciler.process_event(self.complete(paid=False))
        self.assertIsNone(subscribers.find(EMAIL))
        self.mail.assert_not_called()

    def test_paid_webhook_uses_stripe_email_and_only_mailbox_token_can_set_password(self):
        self.start()
        event = self.complete(email="  GUEST@EXAMPLE.INVALID  ")
        self.reconciler.process_event(event)
        found = subscribers.find(EMAIL)
        self.assertEqual(found.tier, "press")
        self.assertIsNone(found.password_hash)
        self.assertIsNone(subscribers.authenticate(EMAIL, SECRET))
        self.assertIsNone(subscribers.redeem_reset(SECRET, "new-password-long"))
        self.mail.assert_called_once()
        target, link = self.mail.call_args.args
        self.assertEqual(target, EMAIL)
        token = parse_qs(urlsplit(link).fragment)["token"][0]
        self.assertNotEqual(
            db.one("SELECT token_hash FROM cedar_press_account_setup_links")["token_hash"], token
        )
        self.assertIsNotNone(self.services.setup.confirm(token, "new-password-long", "Reader"))
        self.assertIsNone(self.services.setup.confirm(token, "another-password", "Reader"))
        self.reconciler.process_event(event)
        self.mail.assert_called_once()

    def test_account_setup_requires_a_paid_email_token_and_stores_name(self):
        from cedar_press.app import app

        self.start()
        self.reconciler.process_event(self.complete())
        token = parse_qs(urlsplit(self.mail.call_args.args[1]).fragment)["token"][0]
        client = TestClient(app)
        self.assertEqual(
            client.post("/auth/account-setup/check", json={"token": SECRET}).status_code, 400
        )
        self.assertEqual(
            client.post("/auth/account-setup/check", json={"token": token}).json(), {"email": EMAIL}
        )
        result = client.post(
            "/auth/account-setup/confirm",
            json={"token": token, "name": "Test Reader", "new_password": "new-local-password"},
        )
        self.assertEqual(result.status_code, 200)
        self.assertEqual(client.get("/me").json()["email"], EMAIL)
        stored = db.one(
            "SELECT display_name,email_verified_at FROM cedar_press_subscribers WHERE email=%s",
            (EMAIL,),
        )
        self.assertEqual(stored["display_name"], "Test Reader")
        self.assertIsNotNone(stored["email_verified_at"])
        self.assertEqual(
            client.post("/auth/account-setup/check", json={"token": token}).status_code, 400
        )

    def test_failed_email_retries_without_creating_a_second_account_or_payment(self):
        self.start()
        event = self.complete()
        self.mail.side_effect = OSError("synthetic SMTP failure")
        with self.assertRaises(OSError):
            self.reconciler.process_event(event)
        self.mail.side_effect = None
        self.reconciler.process_event(event)
        self.assertEqual(
            db.one("SELECT count(*) AS n FROM cedar_press_subscribers WHERE email=%s", (EMAIL,))[
                "n"
            ],
            1,
        )
        self.assertEqual(db.one("SELECT count(*) AS n FROM cedar_press_payments")["n"], 1)
        self.assertTrue(self.service.status(SECRET)["emailSent"])

    def test_resend_requires_own_paid_checkout_and_limits_mail_to_three_requests(self):
        ratelimit.reset_for_tests()
        self.addCleanup(ratelimit.reset_for_tests)
        self.start()
        with self.assertRaises(BillingError):
            self.service.resend(SECRET)
        self.reconciler.process_event(self.complete())
        first_token = parse_qs(urlsplit(self.mail.call_args.args[1]).fragment)["token"][0]
        with self.assertRaises(BillingError):
            self.service.resend("another-browser-secret")
        result = self.service.resend(SECRET)
        self.assertTrue(result["emailSent"])
        self.assertEqual(self.mail.call_count, 2)
        self.assertEqual(self.services.setup.account_details(first_token)["email"], EMAIL)
        self.service.resend(SECRET)
        self.service.resend(SECRET)
        with self.assertRaises(BillingError) as caught:
            self.service.resend(SECRET)
        self.assertEqual(caught.exception.status, 429)
        self.assertEqual(self.mail.call_count, 4)

    def test_failed_resend_preserves_previously_delivered_link(self):
        ratelimit.reset_for_tests()
        self.addCleanup(ratelimit.reset_for_tests)
        self.start()
        self.reconciler.process_event(self.complete())
        token = parse_qs(urlsplit(self.mail.call_args.args[1]).fragment)["token"][0]
        self.mail.side_effect = OSError("synthetic SMTP failure")
        with self.assertRaises(BillingError):
            self.service.resend(SECRET)
        self.assertEqual(self.services.setup.account_details(token)["email"], EMAIL)
        self.assertTrue(self.service.status(SECRET)["emailSent"])
        self.assertEqual(
            db.one("SELECT status FROM cedar_press_account_email_deliveries")["status"], "pending"
        )
        self.mail.side_effect = None
        self.services.setup.send_claim(self.customer)
        self.assertEqual(
            db.one("SELECT status FROM cedar_press_account_email_deliveries")["status"], "sent"
        )
        made = self.services.setup.confirm(token, "new-password-long", "Reader")
        self.assertEqual(made.email, EMAIL)
        latest = parse_qs(urlsplit(self.mail.call_args.args[1]).fragment)["token"][0]
        self.assertIsNone(self.services.setup.confirm(latest, "different-password-long", "Other"))

    def test_delivery_releases_pool_connection_and_concurrent_retry_uses_lease(self):
        self.start()
        event = self.complete()
        db.reset_for_tests()
        with mock.patch.dict(os.environ, {"CEDAR_PRESS_DB_POOL": "1"}):
            entered, release = threading.Event(), threading.Event()

            def slow_smtp(*args, **kwargs):
                # This borrows the only connection. It would time out if the
                # sender still held its transaction or a pool connection.
                self.assertEqual(db.one("SELECT 1 AS n")["n"], 1)
                entered.set()
                if not release.wait(5):
                    raise AssertionError("SMTP test release timed out")

            self.mail.side_effect = slow_smtp
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                    first = pool.submit(self.reconciler.process_event, event)
                    try:
                        self.assertTrue(entered.wait(5))
                        duplicate = pool.submit(self.reconciler.process_event, event)
                        duplicate.result(timeout=3)
                        self.assertEqual(self.mail.call_count, 1)
                    finally:
                        release.set()
                    first.result(timeout=3)
            finally:
                db.reset_for_tests()
        self.assertTrue(self.service.status(SECRET)["emailSent"])

    def test_setup_link_does_not_follow_an_email_reassignment(self):
        self.start()
        self.reconciler.process_event(self.complete())
        token = parse_qs(urlsplit(self.mail.call_args.args[1]).fragment)["token"][0]
        db.execute(
            "UPDATE cedar_press_account_setup_links SET email='other@example.invalid'",
        )
        with self.assertRaises(BillingError):
            self.services.setup.account_details(token)
        self.assertIsNone(self.services.setup.confirm(token, "new-password-long", "Reader"))

    def test_legacy_setup_links_still_work_after_delivery_migration(self):
        self.start()
        self.reconciler.process_event(self.complete())
        token = subscribers.issue_reset(EMAIL)
        self.assertEqual(self.services.setup.account_details(token)["email"], EMAIL)
        self.assertEqual(
            self.services.setup.confirm(token, "legacy-password-long", "Reader").email, EMAIL
        )
        self.assertIsNone(self.services.setup.confirm(token, "another-password-long", "Reader"))

    def test_expired_delivery_lease_can_be_recovered(self):
        self.start()
        self.reconciler.process_event(self.complete())
        db.execute("""UPDATE cedar_press_account_email_deliveries SET status='sending',
            lease_until=now()-interval '1 second'""")
        self.services.setup.send_claim(self.customer)
        self.assertEqual(self.mail.call_count, 2)
        self.assertEqual(
            db.one("SELECT status,attempts FROM cedar_press_account_email_deliveries"),
            {"status": "sent", "attempts": 2},
        )

    def test_retries_reuse_reservation_and_other_browsers_cannot_read_it(self):
        self.assertEqual(self.start(), self.start())
        self.assertEqual(len(self.gateway.sessions), 1)
        with self.assertRaises(BillingError):
            self.service.status("another-browser-secret")

    def test_confirmation_and_resend_target_paid_checkout_when_newer_tab_is_unpaid(self):
        from cedar_press.app import app

        self.start()
        older = db.one("SELECT id FROM cedar_press_guest_checkouts")["id"]
        event = self.complete()
        self.service.start("press_pro", SECRET)
        self.reconciler.process_event(event)
        self.assertEqual(self.service.status(SECRET, older)["status"], "complete")
        self.assertEqual(self.service.status(SECRET)["status"], "open")
        ratelimit.reset_for_tests()
        self.addCleanup(ratelimit.reset_for_tests)
        self.assertEqual(self.service.resend(SECRET, older)["status"], "complete")
        client = TestClient(app)
        self.assertEqual(client.get(f"/billing/guest/status?checkout_id={older}").status_code, 404)
        client.cookies.set("cedar_press_guest_checkout", SECRET)
        self.assertEqual(
            client.get(f"/billing/guest/status?checkout_id={older}").json()["status"], "complete"
        )
        self.assertEqual(
            client.post("/billing/guest/resend", json={"checkout_id": str(older)}).json()["status"],
            "complete",
        )
        self.assertEqual(client.get("/billing/guest/status?checkout_id=invalid").status_code, 422)

    def test_guest_recovery_passes_the_reservation_creation_window(self):
        self.gateway.fail_checkout = True
        with self.assertRaises(stripe.APIConnectionError):
            self.start()
        db.execute("UPDATE cedar_press_guest_checkouts SET expires_at=now()+interval '29 minutes'")
        row = db.one("SELECT * FROM cedar_press_guest_checkouts")
        with mock.patch.object(
            self.gateway, "find_checkout", wraps=self.gateway.find_checkout
        ) as find:
            self.start()
        self.assertEqual(
            find.call_args.kwargs,
            {
                "created_after": int(row["created_at"].timestamp()) - 60,
                "created_before": int(row["expires_at"].timestamp()) + 60,
            },
        )

    def test_lost_checkout_response_reuses_idempotency_key(self):
        self.gateway.fail_checkout = True
        with self.assertRaises(stripe.APIConnectionError):
            self.start()
        self.start()
        self.assertEqual(len(self.gateway.sessions), 1)
        self.assertEqual(len(set(self.gateway.attempts)), 1)

    def test_existing_credentials_are_preserved_and_new_customer_history_is_linked(self):
        self.start()
        original = db.one("SELECT * FROM cedar_press_subscribers WHERE id=%s", (self.user["id"],))
        event = self.complete(email=self.user["email"].upper())
        self.reconciler.process_event(event)
        stored = db.one("SELECT * FROM cedar_press_subscribers WHERE id=%s", (self.user["id"],))
        for field in (
            "id",
            "email",
            "password_hash",
            "email_verified_at",
            "stripe_customer_id",
            "sessions_revoked_at",
        ):
            self.assertEqual(stored[field], original[field])
        self.assertEqual(db.one("SELECT count(*) AS n FROM cedar_press_subscribers")["n"], 1)
        self.assertIsNotNone(subscribers.authenticate(self.user["email"], "existing-password"))
        self.assertIsNone(subscribers.authenticate(self.user["email"], SECRET))
        self.mail.assert_called_once_with(
            self.user["email"], "http://localhost:5173/login", sign_in=True
        )
        self.assertIsNone(db.one("SELECT * FROM cedar_press_password_resets"))
        with db.pool().connection() as conn, conn.cursor() as cur:
            self.assertEqual(self.service.owner(cur, self.customer)["id"], self.user["id"])
            self.assertEqual(
                self.service.owner(cur, original["stripe_customer_id"])["id"], self.user["id"]
            )
        self.reconciler.reconcile_customer(self.customer)
        self.assertEqual(
            db.one("SELECT customer_id FROM cedar_press_subscriptions")["customer_id"],
            self.customer,
        )
        self.assertFalse(self.service.status(SECRET)["accountSetup"])

    def test_existing_unpaid_account_can_claim_membership_by_email_without_duplicate_user(self):
        accounts.create_user(EMAIL)
        self.start()
        self.reconciler.process_event(self.complete())
        self.assertEqual(
            db.one("SELECT count(*) AS n FROM cedar_press_subscribers WHERE email=%s", (EMAIL,))[
                "n"
            ],
            1,
        )
        token = parse_qs(urlsplit(self.mail.call_args.args[1]).fragment)["token"][0]
        self.assertEqual(self.services.setup.account_details(token)["email"], EMAIL)

    def test_wrong_checkout_metadata_cannot_provision_an_identity(self):
        self.start()
        event = self.complete()
        next(iter(self.gateway.sessions.values()))["client_reference_id"] = "another-attempt"
        with self.assertRaises(BillingError):
            self.reconciler.process_event(event)
        self.assertIsNone(subscribers.find(EMAIL))
        self.mail.assert_not_called()


class TestAccountEmail(unittest.TestCase):
    def test_local_smtp_sends_link_without_logging_tokens(self):
        settings = {
            "CEDAR_PRESS_SMTP_HOST": "mailpit",
            "CEDAR_PRESS_SMTP_PORT": "1025",
            "CEDAR_PRESS_SMTP_STARTTLS": "0",
            "CEDAR_PRESS_EMAIL_FROM": "accounts@example.invalid",
            "CEDAR_PRESS_ENVIRONMENT": "development",
        }
        smtp = mock.MagicMock()
        sender = AccountEmailSender(settings=settings, smtp_factory=smtp)
        sender.send_link(EMAIL, "http://localhost:5173/login#reset=synthetic")
        smtp.assert_called_once_with("mailpit", 1025, timeout=10)
        message = smtp.return_value.__enter__.return_value.send_message.call_args.args[0]
        self.assertEqual(message["To"], EMAIL)
        self.assertIn("#reset=synthetic", message.get_content())
        smtp.return_value.__enter__.return_value.starttls.assert_not_called()
        settings["CEDAR_PRESS_ENVIRONMENT"] = "production"
        self.assertFalse(sender.configured())
