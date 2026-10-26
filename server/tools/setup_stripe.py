"""Provision the Stripe catalog: python server/tools/setup_stripe.py [--live]."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from zoneinfo import ZoneInfo

import stripe

from cedar_press.billing.policy import AMOUNTS
from cedar_press.billing.stripe_gateway import StripeGateway, plain
from cedar_press.billing.support import application_url


def setup(gateway, code):
    client = gateway.client.v1
    products, prices, portals = {}, {}, {}
    existing = gateway.rows(client.products.list({"limit": 100}))
    for tier in ("press", "press_pro"):
        matches = [
            p
            for p in existing
            if p.get("metadata", {}).get("cedar_press_catalog") == "annual_v4"
            and p.get("metadata", {}).get("cedar_press_tier") == tier
        ]
        if len(matches) > 1:
            raise SystemExit("Multiple matching Stripe products; resolve them before setup")
        products[tier] = (
            matches[0]["id"]
            if matches
            else client.products.create(
                {
                    "name": "Cedar Press+" if tier == "press_pro" else "Cedar Press",
                    "metadata": {
                        "cedar_press_catalog": "annual_v4",
                        "cedar_press_tier": tier,
                    },
                },
                options={"idempotency_key": "press-product-annual-v4-" + tier},
            ).id
        )
    for cohort, amounts in AMOUNTS.items():
        prices[cohort] = {}
        for tier, amount in amounts.items():
            lookup = f"cedar_press_{cohort}_{tier}_annual_v4"
            found = gateway.rows(client.prices.list({"lookup_keys": [lookup], "limit": 100}))
            if found:
                price = found[0]
                if (
                    price.get("unit_amount") != amount
                    or price.get("currency") != "usd"
                    or price.get("recurring", {}).get("interval") != "year"
                ):
                    raise SystemExit("Existing price differs from the approved annual offer")
            else:
                price = plain(
                    client.prices.create(
                        {
                            "product": products[tier],
                            "currency": "usd",
                            "unit_amount": amount,
                            "recurring": {"interval": "year"},
                            "lookup_key": lookup,
                        },
                        options={"idempotency_key": lookup},
                    )
                )
            prices[cohort][tier] = price["id"]
        portals[cohort] = {}
        configurations = gateway.rows(client.billing_portal.configurations.list({"limit": 100}))
        for current_tier in ("press", "press_pro"):
            target_tier = "press_pro" if current_tier == "press" else "press"
            found = [
                c
                for c in configurations
                if c.get("metadata", {}).get("cedar_press_cohort") == cohort
                and c.get("metadata", {}).get("cedar_press_current_tier") == current_tier
                and c.get("metadata", {}).get("cedar_press_catalog") == "annual_v4"
            ]
            config = (
                found[0]
                if found
                else plain(
                    client.billing_portal.configurations.create(
                        {
                            "metadata": {
                                "cedar_press_cohort": cohort,
                                "cedar_press_current_tier": current_tier,
                                "cedar_press_catalog": "annual_v4",
                            },
                            "default_return_url": application_url() + "/settings",
                            "features": {
                                "invoice_history": {"enabled": True},
                                "payment_method_update": {"enabled": True},
                                "subscription_cancel": {
                                    "enabled": True,
                                    "mode": "at_period_end",
                                },
                                "subscription_update": {
                                    "enabled": True,
                                    "default_allowed_updates": ["price"],
                                    "proration_behavior": "always_invoice",
                                    "schedule_at_period_end": {
                                        "conditions": [{"type": "decreasing_item_amount"}]
                                    },
                                    "products": [
                                        {
                                            "product": products[target_tier],
                                            "prices": [prices[cohort][target_tier]],
                                        }
                                    ],
                                },
                            },
                        },
                        options={"idempotency_key": f"press-portal-{cohort}-{current_tier}-v4"},
                    )
                )
            )
            portals[cohort][current_tier] = config["id"]
    coupon_id = "cedar_press_summit_2026_v4"
    try:
        client.coupons.retrieve(coupon_id)
    except stripe.InvalidRequestError as error:
        if error.http_status != 404:
            raise
        client.coupons.create(
            {
                "id": coupon_id,
                "amount_off": 10_000,
                "currency": "usd",
                "duration": "once",
                "applies_to": {"products": list(products.values())},
            },
            options={"idempotency_key": coupon_id},
        )
    promotions = gateway.rows(
        client.promotion_codes.list({"code": code, "active": True, "limit": 100})
    )
    for promotion in promotions:
        if (promotion.get("promotion") or {}).get("coupon") != coupon_id:
            client.promotion_codes.update(promotion["id"], {"active": False})
    if not any((p.get("promotion") or {}).get("coupon") == coupon_id for p in promotions):
        client.promotion_codes.create(
            {
                "code": code,
                "promotion": {"type": "coupon", "coupon": coupon_id},
                "restrictions": {"first_time_transaction": True},
                "expires_at": int(
                    dt.datetime(2027, 1, 1, tzinfo=ZoneInfo("America/Chicago")).timestamp()
                ),
            },
            options={"idempotency_key": "press-promotion-v4-" + code},
        )
    legacy = json.loads(os.environ.get("CEDAR_PRESS_STRIPE_LEGACY_PRICES") or "[]")
    previous = json.loads(os.environ.get("CEDAR_PRESS_STRIPE_PRICES") or "{}")
    for cohort, tiers in previous.items():
        for tier, price_id in tiers.items():
            entry = {"id": price_id, "tier": tier, "cohort": cohort}
            if price_id != prices.get(cohort, {}).get(tier) and entry not in legacy:
                legacy.append(entry)
    print("CEDAR_PRESS_STRIPE_LEGACY_PRICES=" + json.dumps(legacy, separators=(",", ":")))
    print("CEDAR_PRESS_STRIPE_PRICES=" + json.dumps(prices, separators=(",", ":")))
    print("CEDAR_PRESS_STRIPE_PORTALS=" + json.dumps(portals, separators=(",", ":")))
    print("CEDAR_PRESS_STRIPE_SUMMIT_COUPON=" + coupon_id)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Explicitly permit live-account setup")
    parser.add_argument("--summit-code", default="GREATLAKES2026")
    args = parser.parse_args(argv)
    gateway = StripeGateway()
    if gateway.livemode and not args.live:
        parser.error("Setup defaults to sandbox; live setup requires --live")
    setup(gateway, args.summit_code)


if __name__ == "__main__":
    main()
