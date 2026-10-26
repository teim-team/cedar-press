"""Small boundary around the official Stripe SDK. No keys or card data leave it."""

from __future__ import annotations

import json
import os
from urllib.parse import urlsplit

import stripe

from cedar_press.billing.errors import BillingError, unavailable
from cedar_press.billing.pricing import identify_price, price_for
from cedar_press.billing.utils import reference

API_VERSION = "2026-09-30.endive"


def plain(value):
    return value.to_dict() if hasattr(value, "to_dict") else json.loads(json.dumps(value))


def stripe_url(value: str) -> str:
    parsed = urlsplit(value or "")
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or not parsed.hostname.endswith(".stripe.com")
        or parsed.username
        or parsed.password
    ):
        raise BillingError("BILLING_URL_INVALID", "Billing could not be opened.", 502)
    return value


class StripeGateway:
    """Stripe operations with an injected client or one initialized on first use."""

    def __init__(self, client: stripe.StripeClient | None = None):
        self._client = client
        self._mode = os.environ.get("CEDAR_PRESS_STRIPE_MODE", "test")

    @property
    def client(self):
        if self._mode not in {"test", "live"}:
            raise unavailable()
        if self._client is None:
            key = os.environ.get("CEDAR_PRESS_STRIPE_SECRET_KEY", "")
            if not key.startswith((f"sk_{self._mode}_", f"rk_{self._mode}_")):
                raise unavailable()
            self._client = stripe.StripeClient(
                key,
                stripe_version=API_VERSION,
                max_network_retries=1,
                http_client=stripe.RequestsClient(timeout=10),
            )
        return self._client

    @property
    def livemode(self):
        # Availability checks must still validate credentials before exposing
        # checkout actions, even though construction itself needs no Stripe key.
        _ = self.client
        return self._mode == "live"

    def rows(self, response):
        return [plain(item) for item in response.auto_paging_iter()]

    def price(self, price_id):
        return plain(self.client.v1.prices.retrieve(price_id))

    def customer(self, user):
        return self.client.v1.customers.create(
            {"email": user["email"], "metadata": {"cedar_press_user_id": str(user["id"])}},
            options={"idempotency_key": f"press-customer-{user['id']}"},
        ).id

    def subscriptions(self, customer):
        return self.rows(
            self.client.v1.subscriptions.list({"customer": customer, "status": "all", "limit": 100})
        )

    def subscription(self, subscription_id):
        return plain(self.client.v1.subscriptions.retrieve(subscription_id))

    def invoices(self, subscription_id):
        return self.rows(
            self.client.v1.invoices.list({"subscription": subscription_id, "limit": 100})
        )

    def invoice(self, invoice_id):
        return plain(self.client.v1.invoices.retrieve(invoice_id))

    def lines(self, invoice_id):
        return self.rows(self.client.v1.invoices.line_items.list(invoice_id, {"limit": 100}))

    def invoice_payments(self, invoice_id):
        return self.rows(
            self.client.v1.invoice_payments.list({"invoice": invoice_id, "limit": 100})
        )

    def payment(self, payment_id):
        return plain(
            self.client.v1.payment_intents.retrieve(payment_id, {"expand": ["latest_charge"]})
        )

    def charge(self, charge_id):
        return plain(self.client.v1.charges.retrieve(charge_id))

    def refunds(self, charge_id):
        return self.rows(self.client.v1.refunds.list({"charge": charge_id, "limit": 100}))

    def refund(self, refund_id):
        return plain(self.client.v1.refunds.retrieve(refund_id))

    def promotion(self, code):
        matches = self.rows(
            self.client.v1.promotion_codes.list({"code": code, "active": True, "limit": 100})
        )
        if len(matches) != 1:
            raise BillingError("DISCOUNT_INVALID", "That discount code is not available.")
        promotion = matches[0]
        coupon_id = reference(
            (promotion.get("promotion") or {}).get("coupon") or promotion.get("coupon")
        )
        if not coupon_id or coupon_id != os.environ.get("CEDAR_PRESS_STRIPE_SUMMIT_COUPON"):
            raise BillingError("DISCOUNT_INVALID", "That discount code is not available.")
        coupon = self.client.v1.coupons.retrieve(coupon_id)
        if (
            not coupon.valid
            or coupon.amount_off != 10_000
            or coupon.currency != "usd"
            or coupon.duration != "once"
        ):
            raise BillingError("DISCOUNT_INVALID", "That discount code is not available.")
        return promotion["id"]

    def checkout(self, customer, attempt, app_url, account_setup=False):
        params = {
            "mode": "subscription",
            "managed_payments": {"enabled": False},
            "customer": customer,
            "line_items": [{"price": attempt["price_id"], "quantity": 1}],
            "client_reference_id": str(attempt["id"] if account_setup else attempt["user_id"]),
            "metadata": {"cedar_press_attempt_id": str(attempt["id"])},
            "subscription_data": {
                "metadata": {
                    "cedar_press_user_id": str(
                        attempt["id"] if account_setup else attempt["user_id"]
                    )
                }
            },
            "success_url": app_url + "/settings?billing=processing",
            "cancel_url": app_url + "/settings?billing=canceled",
            "expires_at": int(attempt["expires_at"].timestamp()),
        }
        if account_setup:
            name = "Cedar Press+" if attempt["tier"] == "press_pro" else "Cedar Press"
            params["custom_text"] = {
                "submit": {
                    "message": name
                    + " membership. Paid annually upfront and renewed once per year."
                }
            }
            if customer is None:
                params.pop("customer")
                params["allow_promotion_codes"] = attempt["cohort"] == "early_access"
            params["metadata"]["cedar_press_checkout_id"] = str(attempt["id"])
            params["subscription_data"] = {
                "metadata": {"cedar_press_checkout_id": str(attempt["id"])}
            }
            params["success_url"] = (
                app_url + "/subscribe?billing=processing&checkout=" + str(attempt["id"])
            )
            params["cancel_url"] = app_url + "/subscribe?billing=canceled"
        if attempt["promotion_id"]:
            params["discounts"] = [{"promotion_code": attempt["promotion_id"]}]
        return plain(
            self.client.v1.checkout.sessions.create(
                params, options={"idempotency_key": f"press-checkout-{attempt['id']}"}
            )
        )

    def checkout_status(self, session_id):
        return plain(self.client.v1.checkout.sessions.retrieve(session_id))

    def expire_checkout(self, session_id):
        return plain(
            self.client.v1.checkout.sessions.expire(
                session_id, options={"idempotency_key": "press-expire-" + session_id}
            )
        )

    def find_checkout(self, customer, attempt_id, *, created_after=None, created_before=None):
        params = {**({"customer": customer} if customer else {}), "limit": 100}
        if created_after is not None and created_before is not None:
            params["created"] = {"gte": created_after, "lte": created_before}
        elif customer is None:
            raise BillingError("CHECKOUT_WINDOW_REQUIRED", "Please start checkout again.", 409)
        response = self.client.v1.checkout.sessions.list(params)
        # Stop at the matching object rather than fetching later pages.
        for item in response.auto_paging_iter():
            row = plain(item)
            if row.get("metadata", {}).get("cedar_press_attempt_id") == attempt_id:
                return row
        return None

    def find_checkout_for_customer(self, customer):
        sessions = self.rows(
            self.client.v1.checkout.sessions.list({"customer": customer, "limit": 100})
        )
        return next(
            (s for s in sessions if s.get("metadata", {}).get("cedar_press_checkout_id")), None
        )

    def _management_portal(self, customer, app_url):
        try:
            config = json.loads(os.environ.get("CEDAR_PRESS_STRIPE_PORTALS", "{}"))["management"]
            if not isinstance(config, str) or not config.startswith("bpc_"):
                raise ValueError
        except (ValueError, KeyError, TypeError):
            raise unavailable() from None
        features = plain(self.client.v1.billing_portal.configurations.retrieve(config)).get(
            "features", {}
        )
        if (
            features.get("subscription_update", {}).get("enabled") is not False
            or features.get("subscription_cancel", {}).get("mode") != "at_period_end"
        ):
            raise unavailable()
        return stripe_url(
            self.client.v1.billing_portal.sessions.create(
                {
                    "customer": customer,
                    "configuration": config,
                    "return_url": app_url + "/settings",
                }
            ).url
        )

    def portal(self, customer, cohort, app_url, change_plan=False, subscription_id=None):
        if not change_plan:
            return self._management_portal(customer, app_url)
        if not subscription_id:
            raise BillingError("SUBSCRIPTION_REQUIRED", "Choose the subscription to change.", 409)
        subscriptions = self.subscriptions(customer)
        if subscription_id:
            subscriptions = [s for s in subscriptions if s["id"] == subscription_id]
            if not subscriptions:
                raise BillingError("SUBSCRIPTION_MISSING", "That subscription was not found.", 404)
        active = [s for s in subscriptions if s["status"] not in {"canceled", "incomplete_expired"}]
        if len(active) > 1:
            raise unavailable()
        current_tier = "press"
        if active:
            items = active[0]["items"]["data"]
            if len(items) != 1:
                raise unavailable()
            current = identify_price(items[0]["price"])
            if current.cohort != cohort:
                raise unavailable()
            current_tier = current.tier
        target_tier = "press_pro" if current_tier == "press" else "press"
        try:
            config = json.loads(os.environ.get("CEDAR_PRESS_STRIPE_PORTALS", "{}"))[cohort][
                current_tier
            ]
            if not isinstance(config, str) or not config.startswith("bpc_"):
                raise ValueError
        except (ValueError, KeyError, TypeError):
            raise unavailable() from None
        features = plain(
            self.client.v1.billing_portal.configurations.retrieve(
                config, {"expand": ["features.subscription_update.products"]}
            )
        ).get("features", {})
        updates = features.get("subscription_update", {})
        allowed = {
            price for product in updates.get("products", []) for price in product.get("prices", [])
        }
        conditions = updates.get("schedule_at_period_end", {}).get("conditions", [])
        if (
            features.get("subscription_cancel", {}).get("mode") != "at_period_end"
            or not updates.get("enabled")
            or updates.get("default_allowed_updates") != ["price"]
            or updates.get("proration_behavior") != "always_invoice"
            or {price_for(target_tier, cohort).id} != allowed
            or {condition.get("type") for condition in conditions} != {"decreasing_item_amount"}
        ):
            raise unavailable()
        params = {
            "customer": customer,
            "configuration": config,
            "return_url": app_url + "/settings",
        }
        if change_plan:
            if (
                not active
                or active[0]["status"] != "active"
                or active[0].get("cancel_at_period_end")
            ):
                raise BillingError(
                    "PLAN_CHANGE_UNAVAILABLE", "Manage your current subscription first.", 409
                )
            params["flow_data"] = {
                "type": "subscription_update_confirm",
                "subscription_update_confirm": {
                    "subscription": active[0]["id"],
                    "items": [
                        {
                            "id": items[0]["id"],
                            "price": price_for(target_tier, cohort).id,
                            "quantity": 1,
                        }
                    ],
                },
                "after_completion": {
                    "type": "redirect",
                    "redirect": {"return_url": app_url + "/settings?billing=processing"},
                },
            }
        return stripe_url(self.client.v1.billing_portal.sessions.create(params).url)
