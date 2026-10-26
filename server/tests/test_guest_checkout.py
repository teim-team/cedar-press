"""Guest purchase boundaries: existing accounts, paid provisioning and mailbox proof."""

import os
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlsplit

import stripe
from fastapi.testclient import TestClient

from cedar_press import account_email, accounts, billing, db, guest_checkout, ratelimit, subscribers
from cedar_press.billing_policy import BillingError
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
        ready = mock.patch.object(account_email, "configured", return_value=True)
        ready.start()
        self.addCleanup(ready.stop)
        mailer = mock.patch.object(account_email, "send_link")
        self.mail = mailer.start()
        self.addCleanup(mailer.stop)

    def start(self, secret=SECRET):
        return guest_checkout.start("press", secret, self.gateway)

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
        with mock.patch("cedar_press.guest_checkout.Gateway", return_value=self.gateway):
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
        billing.process_event(self.complete(paid=False), self.gateway)
        self.assertIsNone(subscribers.find(EMAIL))
        self.mail.assert_not_called()

    def test_paid_webhook_uses_stripe_email_and_only_mailbox_token_can_set_password(self):
        self.start()
        event = self.complete(email="  GUEST@EXAMPLE.INVALID  ")
        billing.process_event(event, self.gateway)
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
            db.one("SELECT token_hash FROM cedar_press_password_resets")["token_hash"], token
        )
        self.assertIsNotNone(subscribers.redeem_reset(token, "new-password-long"))
        self.assertIsNone(subscribers.redeem_reset(token, "another-password"))
        billing.process_event(event, self.gateway)
        self.mail.assert_called_once()

    def test_account_setup_requires_a_paid_email_token_and_stores_name(self):
        from cedar_press.app import app

        self.start()
        billing.process_event(self.complete(), self.gateway)
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
            billing.process_event(event, self.gateway)
        self.mail.side_effect = None
        billing.process_event(event, self.gateway)
        self.assertEqual(
            db.one("SELECT count(*) AS n FROM cedar_press_subscribers WHERE email=%s", (EMAIL,))[
                "n"
            ],
            1,
        )
        self.assertEqual(db.one("SELECT count(*) AS n FROM cedar_press_payments")["n"], 1)
        self.assertTrue(guest_checkout.status(SECRET)["emailSent"])

    def test_resend_requires_own_paid_checkout_and_limits_mail_to_three_requests(self):
        ratelimit.reset_for_tests()
        self.addCleanup(ratelimit.reset_for_tests)
        self.start()
        with self.assertRaises(BillingError):
            guest_checkout.resend(SECRET)
        billing.process_event(self.complete(), self.gateway)
        first_token = parse_qs(urlsplit(self.mail.call_args.args[1]).fragment)["token"][0]
        with self.assertRaises(BillingError):
            guest_checkout.resend("another-browser-secret")
        result = guest_checkout.resend(SECRET)
        self.assertTrue(result["emailSent"])
        self.assertEqual(self.mail.call_count, 2)
        self.assertIsNone(subscribers.redeem_reset(first_token, "a-long-new-password"))
        guest_checkout.resend(SECRET)
        guest_checkout.resend(SECRET)
        with self.assertRaises(BillingError) as caught:
            guest_checkout.resend(SECRET)
        self.assertEqual(caught.exception.status, 429)
        self.assertEqual(self.mail.call_count, 4)

    def test_retries_reuse_reservation_and_other_browsers_cannot_read_it(self):
        self.assertEqual(self.start(), self.start())
        self.assertEqual(len(self.gateway.sessions), 1)
        with self.assertRaises(BillingError):
            guest_checkout.status("another-browser-secret")

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
        billing.process_event(event, self.gateway)
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
            self.assertEqual(guest_checkout.owner(cur, self.customer)["id"], self.user["id"])
            self.assertEqual(
                guest_checkout.owner(cur, original["stripe_customer_id"])["id"], self.user["id"]
            )
        billing.reconcile_customer(self.customer, self.gateway)
        self.assertEqual(
            db.one("SELECT customer_id FROM cedar_press_subscriptions")["customer_id"],
            self.customer,
        )
        self.assertFalse(guest_checkout.status(SECRET)["accountSetup"])

    def test_existing_unpaid_account_can_claim_membership_by_email_without_duplicate_user(self):
        accounts.create_user(EMAIL)
        self.start()
        billing.process_event(self.complete(), self.gateway)
        self.assertEqual(
            db.one("SELECT count(*) AS n FROM cedar_press_subscribers WHERE email=%s", (EMAIL,))[
                "n"
            ],
            1,
        )
        token = parse_qs(urlsplit(self.mail.call_args.args[1]).fragment)["token"][0]
        self.assertEqual(guest_checkout.account_details(token)["email"], EMAIL)

    def test_wrong_checkout_metadata_cannot_provision_an_identity(self):
        self.start()
        event = self.complete()
        next(iter(self.gateway.sessions.values()))["client_reference_id"] = "another-attempt"
        with self.assertRaises(BillingError):
            billing.process_event(event, self.gateway)
        self.assertIsNone(subscribers.find(EMAIL))
        self.mail.assert_not_called()


class TestAccountEmail(unittest.TestCase):
    def test_local_smtp_sends_link_without_logging_tokens(self):
        with (
            mock.patch.dict(
                os.environ,
                {
                    "CEDAR_PRESS_SMTP_HOST": "mailpit",
                    "CEDAR_PRESS_SMTP_PORT": "1025",
                    "CEDAR_PRESS_SMTP_STARTTLS": "0",
                    "CEDAR_PRESS_EMAIL_FROM": "accounts@example.invalid",
                    "CEDAR_PRESS_ENVIRONMENT": "development",
                },
            ),
            mock.patch("smtplib.SMTP") as smtp,
        ):
            account_email.send_link(EMAIL, "http://localhost:5173/login#reset=synthetic")
            message = smtp.return_value.__enter__.return_value.send_message.call_args.args[0]
            self.assertEqual(message["To"], EMAIL)
            self.assertIn("#reset=synthetic", message.get_content())
            smtp.return_value.__enter__.return_value.starttls.assert_not_called()
            with mock.patch.dict(os.environ, {"CEDAR_PRESS_ENVIRONMENT": "production"}):
                self.assertFalse(account_email.configured())
