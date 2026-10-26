"""Determine access tiers and dates established by invoice lines."""

from cedar_press.billing.errors import BillingError
from cedar_press.billing.pricing import RANK, identify_price
from cedar_press.billing.utils import instant


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
