"""Exercise the real Stripe SDK against an in-process HTTP transport, not Stripe."""

from __future__ import annotations

import contextlib
import datetime as dt
import io
import json
import os
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlsplit

import stripe

from cedar_press.billing_admin import setup
from cedar_press.billing_policy import BillingError
from cedar_press.stripe_gateway import StripeGateway
from tests.test_billing import PRICE_MAP, SETTINGS, price_data


class Transport(stripe.HTTPClient):
    name = "fixture"

    def __init__(self):
        super().__init__()
        self.calls = []
        self.portal_safe = True
        self.coupon_valid = True
        self.bootstrap = False

    def request(self, method, url, headers, post_data=None, **kwargs):
        path = urlsplit(url).path
        params = parse_qs(post_data or "")
        self.calls.append((method, path, params, headers))
        price = {"object": "price", **price_data()}
        subscription = {
            "id": "sub_fixture",
            "object": "subscription",
            "status": "active",
            "items": {"data": [{"id": "si_fixture", "price": price_data()}]},
        }
        invoice = {"id": "in_fixture", "object": "invoice"}
        refund = {"id": "re_fixture", "object": "refund", "charge": "ch_fixture"}
        checkout = {
            "id": "cs_fixture",
            "object": "checkout.session",
            "status": "open",
            "url": "https://checkout.stripe.com/c/pay/fixture",
            "metadata": {"cedar_press_attempt_id": "attempt"},
        }
        if path == "/v1/products":
            result = (
                {"object": "list", "url": path, "has_more": False, "data": []}
                if method == "get"
                else {
                    "id": "prod_" + params["metadata[cedar_press_tier]"][0],
                    "object": "product",
                }
            )
        elif path == "/v1/prices":
            result = (
                {"object": "list", "url": path, "has_more": False, "data": []}
                if method == "get"
                else {"id": "price_" + params["lookup_key"][0], "object": "price"}
            )
        elif path == "/v1/billing_portal/configurations":
            result = (
                {"object": "list", "url": path, "has_more": False, "data": []}
                if method == "get"
                else {
                    "id": "bpc_" + params["metadata[cedar_press_cohort]"][0],
                    "object": "billing_portal.configuration",
                }
            )
        elif path.startswith("/v1/prices/"):
            result = price
        elif path == "/v1/customers":
            result = {"id": "cus_fixture", "object": "customer"}
        elif path == "/v1/subscriptions":
            result = {"object": "list", "url": path, "has_more": False, "data": [subscription]}
        elif path == "/v1/subscriptions/sub_fixture":
            result = subscription
        elif path == "/v1/invoices/in_fixture":
            result = invoice
        elif path == "/v1/invoices":
            result = {"object": "list", "url": path, "has_more": False, "data": [invoice]}
        elif path.endswith("/lines"):
            result = {
                "object": "list",
                "url": path,
                "has_more": False,
                "data": [{"id": "il_fixture", "object": "line_item"}],
            }
        elif path == "/v1/invoice_payments":
            result = {
                "object": "list",
                "url": path,
                "has_more": False,
                "data": [{"id": "inpay_fixture", "object": "invoice_payment"}],
            }
        elif path.startswith("/v1/payment_intents/"):
            result = {
                "id": "pi_fixture",
                "object": "payment_intent",
                "latest_charge": {"id": "ch_fixture", "object": "charge"},
            }
        elif path.startswith("/v1/charges/"):
            result = {"id": "ch_fixture", "object": "charge"}
        elif path == "/v1/refunds":
            result = {"object": "list", "url": path, "has_more": False, "data": [refund]}
        elif path.startswith("/v1/refunds/"):
            result = refund
        elif path == "/v1/promotion_codes":
            promotion = {
                "id": "promo_fixture",
                "object": "promotion_code",
                "promotion": {"type": "coupon", "coupon": "coupon_fixture"},
            }
            result = (
                promotion
                if method == "post"
                else {
                    "object": "list",
                    "url": path,
                    "has_more": False,
                    "data": [] if self.bootstrap else [promotion],
                }
            )
        elif path.startswith("/v1/coupons/"):
            result = {
                "id": "coupon_fixture",
                "object": "coupon",
                "valid": self.coupon_valid,
                "amount_off": 10_000,
                "currency": "usd",
                "duration": "once",
            }
        elif path.startswith("/v1/checkout/sessions"):
            result = (
                {"object": "list", "url": path, "has_more": False, "data": [checkout]}
                if method == "get" and path.endswith("/sessions")
                else checkout
            )
        elif path.startswith("/v1/billing_portal/configurations/"):
            result = {
                "id": "bpc_fixture",
                "object": "billing_portal.configuration",
                "features": {
                    "subscription_cancel": {"mode": "at_period_end"},
                    "subscription_update": {
                        "enabled": True,
                        "default_allowed_updates": ["price"],
                        "proration_behavior": "always_invoice",
                        "products": [
                            {
                                "prices": [PRICE_MAP["early_access"]["press_pro"]]
                                if self.portal_safe
                                else ["price_unapproved"]
                            }
                        ],
                        "schedule_at_period_end": {
                            "conditions": [{"type": "decreasing_item_amount"}]
                        },
                    },
                },
            }
        elif path == "/v1/billing_portal/sessions":
            result = {
                "id": "bps_fixture",
                "object": "billing_portal.session",
                "url": "https://billing.stripe.com/p/session/fixture",
            }
        else:
            raise AssertionError(f"Unexpected SDK operation: {method} {path}")
        return json.dumps(result), 200, {"request-id": "req_fixture"}


class TestStripeGateway(unittest.TestCase):
    def setUp(self):
        patch = mock.patch.dict(
            os.environ,
            {
                **SETTINGS,
                "CEDAR_PRESS_STRIPE_SUMMIT_COUPON": "coupon_fixture",
                "CEDAR_PRESS_STRIPE_PORTALS": json.dumps(
                    {"early_access": {"press": "bpc_fixture"}}
                ),
            },
        )
        patch.start()
        self.addCleanup(patch.stop)
        self.transport = Transport()
        self.gateway = StripeGateway()
        self.gateway.client = stripe.StripeClient("sk_test_synthetic", http_client=self.transport)

    def test_sdk_resources_are_converted_and_pagination_is_followed(self):
        self.assertEqual(self.gateway.price("price_fixture")["currency"], "usd")
        self.assertEqual(
            self.gateway.customer({"id": "user", "email": "reader@example.org"}), "cus_fixture"
        )
        self.assertEqual(self.gateway.subscriptions("cus_fixture")[0]["id"], "sub_fixture")
        self.assertEqual(self.gateway.subscription("sub_fixture")["id"], "sub_fixture")
        self.assertEqual(self.gateway.invoices("sub_fixture")[0]["id"], "in_fixture")
        self.assertEqual(self.gateway.invoice("in_fixture")["id"], "in_fixture")
        self.assertEqual(self.gateway.lines("in_fixture")[0]["id"], "il_fixture")
        self.assertEqual(self.gateway.invoice_payments("in_fixture")[0]["id"], "inpay_fixture")
        self.assertEqual(self.gateway.payment("pi_fixture")["latest_charge"]["id"], "ch_fixture")
        self.assertEqual(self.gateway.charge("ch_fixture")["id"], "ch_fixture")
        self.assertEqual(self.gateway.refunds("ch_fixture")[0]["id"], "re_fixture")
        self.assertEqual(self.gateway.refund("re_fixture")["id"], "re_fixture")

    def test_sdk_checkout_request_contains_server_price_and_stable_idempotency_key(self):
        attempt = {
            "id": "attempt",
            "user_id": "user",
            "price_id": "price_fixture",
            "promotion_id": "promo_fixture",
            "expires_at": dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=31),
        }
        result = self.gateway.checkout("cus_fixture", attempt, "http://localhost:5173")
        self.assertEqual(result["id"], "cs_fixture")
        _, _, params, headers = self.transport.calls[-1]
        self.assertEqual(params["line_items[0][price]"], ["price_fixture"])
        self.assertEqual(params["managed_payments[enabled]"], ["false"])
        self.assertEqual(params["discounts[0][promotion_code]"], ["promo_fixture"])
        self.assertEqual(headers["Idempotency-Key"], "press-checkout-attempt")
        self.assertEqual(self.gateway.checkout_status("cs_fixture")["status"], "open")
        self.assertEqual(self.gateway.find_checkout("cus_fixture", "attempt")["id"], "cs_fixture")
        self.assertIsNone(self.gateway.find_checkout("cus_fixture", "different"))

    def test_direct_guest_checkout_leaves_email_and_codes_to_stripe(self):
        attempt = {
            "id": "anonymous-attempt",
            "tier": "press",
            "cohort": "early_access",
            "price_id": "price_fixture",
            "promotion_id": None,
            "expires_at": dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=31),
        }
        self.gateway.checkout(None, attempt, "http://localhost:5173", guest=True)
        _, _, params, _ = self.transport.calls[-1]
        self.assertNotIn("customer", params)
        self.assertNotIn("customer_email", params)
        self.assertEqual(params["allow_promotion_codes"], ["true"])
        self.assertEqual(params["client_reference_id"], ["anonymous-attempt"])
        self.assertEqual(params["metadata[cedar_press_guest_id]"], ["anonymous-attempt"])
        self.assertEqual(
            params["success_url"], ["http://localhost:5173/subscribe?billing=processing"]
        )
        self.assertNotIn("discounts[0][promotion_code]", params)

    def test_only_the_approved_first_invoice_coupon_is_accepted(self):
        self.assertEqual(self.gateway.promotion("SUMMIT"), "promo_fixture")
        self.transport.coupon_valid = False
        with self.assertRaises(BillingError):
            self.gateway.promotion("SUMMIT")
        with (
            mock.patch.dict(os.environ, {"CEDAR_PRESS_STRIPE_SUMMIT_COUPON": "different"}),
            self.assertRaises(BillingError),
        ):
            self.gateway.promotion("SUMMIT")

    def test_portal_prices_preserve_cohort_and_downgrades_wait_until_term_end(self):
        self.assertTrue(
            self.gateway.portal("cus_fixture", "early_access", "http://localhost:5173").startswith(
                "https://billing.stripe.com/"
            )
        )
        self.transport.portal_safe = False
        with self.assertRaises(BillingError):
            self.gateway.portal("cus_fixture", "early_access", "http://localhost:5173")
        with self.assertRaises(BillingError):
            self.gateway.portal("cus_fixture", "standard", "http://localhost:5173")

    def test_plan_change_uses_stripe_confirmation_and_only_cohort_target(self):
        self.gateway.portal("cus_fixture", "early_access", "http://localhost:5173", True)
        _, _, params, _ = self.transport.calls[-1]
        self.assertEqual(params["flow_data[type]"], ["subscription_update_confirm"])
        self.assertEqual(
            params["flow_data[subscription_update_confirm][items][0][price]"],
            [PRICE_MAP["early_access"]["press_pro"]],
        )
        self.assertEqual(
            params["flow_data[subscription_update_confirm][items][0][quantity]"], ["1"]
        )

    def test_bootstrap_encodes_all_four_annual_prices_and_cohort_portals(self):
        self.transport.bootstrap = True
        with contextlib.redirect_stdout(io.StringIO()) as output:
            setup(self.gateway, "SUMMIT")
        self.assertIn("CEDAR_PRESS_STRIPE_PRICES=", output.getvalue())
        creates = [
            params
            for method, path, params, _ in self.transport.calls
            if method == "post" and path == "/v1/prices"
        ]
        self.assertEqual(
            sorted(int(p["unit_amount"][0]) for p in creates), [50_000, 100_000, 100_000, 200_000]
        )
        configs = [
            params
            for method, path, params, _ in self.transport.calls
            if method == "post" and path == "/v1/billing_portal/configurations"
        ]
        self.assertEqual(len({p["product"][0] for p in creates}), 2)
        self.assertEqual(len(configs), 4)
        for config in configs:
            self.assertEqual(config["features[subscription_cancel][mode]"], ["at_period_end"])
            self.assertEqual(
                config["features[subscription_update][proration_behavior]"], ["always_invoice"]
            )
            self.assertEqual(
                config[
                    "features[subscription_update][schedule_at_period_end][conditions][0][type]"
                ],
                ["decreasing_item_amount"],
            )
