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

from cedar_press.billing.dependencies import create_billing_services
from cedar_press.billing.errors import BillingError
from cedar_press.billing.stripe_gateway import API_VERSION, StripeGateway
from tests.test_billing import PRICE_MAP, SETTINGS, price_data
from tools.setup_stripe import setup


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
        params = parse_qs(urlsplit(url).query)
        params.update(parse_qs(post_data or ""))
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
                    "id": "bpc_" + params.get("metadata[cedar_press_cohort]", ["management"])[0],
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
        elif path.endswith("/expire"):
            result = {**checkout, "status": "expired"}
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
                        "enabled": (not self.portal_safe)
                        if path.endswith("bpc_management")
                        else True,
                        "default_allowed_updates": ["price"],
                        "proration_behavior": "always_invoice",
                        "products": [
                            {
                                "prices": [
                                    PRICE_MAP[
                                        "standard"
                                        if path.endswith("bpc_standard")
                                        else "early_access"
                                    ]["press_pro"]
                                ]
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
                    {
                        "management": "bpc_management",
                        "early_access": {"press": "bpc_fixture"},
                        "standard": {"press": "bpc_standard"},
                    }
                ),
            },
        )
        patch.start()
        self.addCleanup(patch.stop)
        self.transport = Transport()
        self.gateway = StripeGateway(
            client=stripe.StripeClient(
                "sk_test_synthetic", stripe_version=API_VERSION, http_client=self.transport
            )
        )

    def test_injected_client_does_not_require_credentials_or_construct_a_real_client(self):
        client = mock.Mock()
        client.v1.prices.retrieve.return_value = {"id": "price_stub", "currency": "usd"}
        with (
            mock.patch.dict(os.environ, {"CEDAR_PRESS_STRIPE_SECRET_KEY": ""}),
            mock.patch("stripe.StripeClient", side_effect=AssertionError("unexpected real client")),
        ):
            gateway = StripeGateway(client=client)
            self.assertEqual(gateway.price("price_stub"), {"id": "price_stub", "currency": "usd"})
        client.v1.prices.retrieve.assert_called_once_with("price_stub")

    def test_default_client_is_created_once_on_first_use(self):
        with mock.patch("stripe.StripeClient") as client_factory:
            client_factory.return_value.v1.prices.retrieve.return_value = {"id": "price_stub"}
            gateway = StripeGateway()
            client_factory.assert_not_called()
            self.assertEqual(gateway.price("price_stub"), {"id": "price_stub"})
            self.assertFalse(gateway.livemode)
            self.assertEqual(gateway.price("price_stub"), {"id": "price_stub"})
            client_factory.assert_called_once()
            self.assertEqual(client_factory.call_args.kwargs["stripe_version"], API_VERSION)

    def test_composition_shares_one_gateway_without_requiring_stripe_configuration(self):
        with mock.patch.dict(os.environ, {"CEDAR_PRESS_STRIPE_SECRET_KEY": ""}):
            services = create_billing_services()
            self.assertIsInstance(services.billing.gateway, StripeGateway)
            self.assertIs(services.billing.gateway, services.checkout.gateway)
            self.assertIs(services.billing.gateway, services.reconciler.gateway)
            with self.assertRaises(BillingError):
                _ = services.billing.gateway.livemode
            database = mock.Mock()
            database.one.return_value = {
                "id": "user",
                "email": "reader@example.invalid",
                "stripe_customer_id": None,
            }
            database.query.return_value = []
            services = create_billing_services(database=database)
            self.assertFalse(services.billing.summary("reader@example.invalid")["available"])

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

    def test_sdk_expiration_and_bounded_recovery_use_supported_parameters(self):
        self.assertEqual(self.gateway.expire_checkout("cs_fixture")["status"], "expired")
        method, path, _, headers = self.transport.calls[-1]
        self.assertEqual((method, path), ("post", "/v1/checkout/sessions/cs_fixture/expire"))
        self.assertEqual(headers["Idempotency-Key"], "press-expire-cs_fixture")
        self.gateway.find_checkout(None, "attempt", created_after=10, created_before=20)
        self.assertEqual(self.transport.calls[-1][2]["created[gte]"], ["10"])
        self.assertEqual(self.transport.calls[-1][2]["created[lte]"], ["20"])

    def test_checkout_with_account_setup_leaves_email_and_codes_to_stripe(self):
        attempt = {
            "id": "anonymous-attempt",
            "tier": "press",
            "cohort": "early_access",
            "price_id": "price_fixture",
            "promotion_id": None,
            "expires_at": dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=31),
        }
        self.gateway.checkout(None, attempt, "http://localhost:5173", account_setup=True)
        _, _, params, _ = self.transport.calls[-1]
        self.assertNotIn("customer", params)
        self.assertNotIn("customer_email", params)
        self.assertEqual(params["allow_promotion_codes"], ["true"])
        self.assertEqual(params["client_reference_id"], ["anonymous-attempt"])
        self.assertEqual(params["metadata[cedar_press_checkout_id]"], ["anonymous-attempt"])
        self.assertEqual(
            params["success_url"],
            ["http://localhost:5173/subscribe?billing=processing&checkout=anonymous-attempt"],
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
        self.gateway.portal(
            "cus_fixture", "early_access", "http://localhost:5173", True, "sub_fixture"
        )
        _, _, params, _ = self.transport.calls[-1]
        self.assertEqual(params["flow_data[type]"], ["subscription_update_confirm"])
        self.assertEqual(
            params["flow_data[subscription_update_confirm][items][0][price]"],
            [PRICE_MAP["early_access"]["press_pro"]],
        )
        self.assertEqual(
            params["flow_data[subscription_update_confirm][items][0][quantity]"], ["1"]
        )

    def test_old_canceled_cohort_cannot_enable_price_changes_in_customer_portal(self):
        subscriptions = [
            {"id": "sub_old", "status": "canceled", "items": {"data": [{"price": price_data()}]}},
            {
                "id": "sub_standard",
                "status": "active",
                "items": {"data": [{"id": "si_standard", "price": price_data(cohort="standard")}]},
            },
        ]
        with mock.patch.object(self.gateway, "subscriptions", return_value=subscriptions) as fetch:
            self.gateway.portal(
                "cus_fixture", "early_access", "http://localhost:5173", False, "sub_old"
            )
            fetch.assert_not_called()
            params = self.transport.calls[-1][2]
            self.assertEqual(params["configuration"], ["bpc_management"])
            self.assertNotIn("flow_data[type]", params)
            self.gateway.portal(
                "cus_fixture", "standard", "http://localhost:5173", True, "sub_standard"
            )
            params = self.transport.calls[-1][2]
            self.assertEqual(
                params["flow_data[subscription_update_confirm][subscription]"], ["sub_standard"]
            )
            self.assertEqual(
                params["flow_data[subscription_update_confirm][items][0][price]"],
                [PRICE_MAP["standard"]["press_pro"]],
            )
        with self.assertRaises(BillingError):
            self.gateway.portal("cus_fixture", "early_access", "http://localhost:5173", True)

    def test_first_run_catalog_accepts_empty_compose_configuration(self):
        self.transport.bootstrap = True
        with (
            mock.patch.dict(
                os.environ,
                {"CEDAR_PRESS_STRIPE_PRICES": "", "CEDAR_PRESS_STRIPE_LEGACY_PRICES": ""},
            ),
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            setup(self.gateway, "SUMMIT")
        self.assertIn("CEDAR_PRESS_STRIPE_PRICES=", output.getvalue())
        self.assertIn("CEDAR_PRESS_STRIPE_LEGACY_PRICES=[]", output.getvalue())

    def test_recovery_filters_the_window_and_stops_before_fetching_more_pages(self):
        client = mock.Mock()

        def rows():
            yield {"id": "cs_match", "metadata": {"cedar_press_attempt_id": "attempt"}}
            raise AssertionError("Recovery fetched beyond the matching session")

        client.v1.checkout.sessions.list.return_value.auto_paging_iter.return_value = rows()
        gateway = StripeGateway(client)
        self.assertEqual(
            gateway.find_checkout(None, "attempt", created_after=10, created_before=20)["id"],
            "cs_match",
        )
        client.v1.checkout.sessions.list.assert_called_once_with(
            {"limit": 100, "created": {"gte": 10, "lte": 20}}
        )
        with self.assertRaises(BillingError):
            gateway.find_checkout(None, "attempt")

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
        self.assertEqual(len(configs), 5)
        management = [
            c for c in configs if c.get("features[subscription_update][enabled]") == ["false"]
        ]
        self.assertEqual(len(management), 1)
        self.assertIn("CEDAR_PRESS_STRIPE_PORTALS=", output.getvalue())
        for config in configs:
            if config in management:
                self.assertNotIn("features[subscription_update][products][0][prices][0]", config)
                continue
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
