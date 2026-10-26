"""Annual offers, price validation and invoice coverage; all amounts are integer cents."""

from __future__ import annotations

import datetime as dt
import json
import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo

AMOUNTS = {
    "early_access": {"press": 50_000, "press_pro": 100_000},
    "standard": {"press": 100_000, "press_pro": 200_000},
}
RANK = {"press": 1, "press_pro": 2}


class BillingError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def unavailable() -> BillingError:
    return BillingError("BILLING_UNAVAILABLE", "Billing is temporarily unavailable.", 503)


def cohort_at(now: dt.datetime) -> str:
    return (
        "early_access"
        if now.astimezone(ZoneInfo("America/Chicago")).date() < dt.date(2027, 1, 1)
        else "standard"
    )


def reference(value) -> str | None:
    return value.get("id") if isinstance(value, dict) else value if isinstance(value, str) else None


def instant(value) -> dt.datetime:
    if type(value) is not int or value < 0:
        raise BillingError("BILLING_DATA_INVALID", "Billing data could not be verified.", 502)
    return dt.datetime.fromtimestamp(value, dt.timezone.utc)


@dataclass(frozen=True)
class Price:
    id: str
    tier: str
    cohort: str

    @property
    def amount(self) -> int:
        return AMOUNTS[self.cohort][self.tier]


def prices() -> list[Price]:
    try:
        raw = json.loads(os.environ.get("CEDAR_PRESS_STRIPE_PRICES", "{}"))
        result = [Price(raw[cohort][tier], tier, cohort) for cohort in AMOUNTS for tier in RANK]
        if any(not isinstance(p.id, str) or not p.id.startswith("price_") for p in result):
            raise ValueError
        if len({p.id for p in result}) != 4:
            raise ValueError
        legacy = json.loads(os.environ.get("CEDAR_PRESS_STRIPE_LEGACY_PRICES", "[]"))
        if not isinstance(legacy, list):
            raise ValueError
        for entry in legacy:
            price = Price(entry["id"], entry["tier"], entry["cohort"])
            if (
                price.tier not in RANK
                or price.cohort not in AMOUNTS
                or not isinstance(price.id, str)
                or not price.id.startswith("price_")
            ):
                raise ValueError
            existing = next((p for p in result if p.id == price.id), None)
            if existing and existing != price:
                raise ValueError
            if not existing:
                result.append(price)
        return result
    except (ValueError, TypeError, KeyError):
        raise unavailable() from None


def price_for(tier: str, cohort: str) -> Price:
    for price in prices():
        if (price.tier, price.cohort) == (tier, cohort):
            return price
    raise BillingError("PLAN_INVALID", "Choose Cedar Press or Cedar Press+.")


def identify_price(value) -> Price:
    for price in prices():
        if price.id == reference(value):
            return price
    raise BillingError("PRICE_UNRECOGNIZED", "This subscription price is not configured.", 502)


def validate_price(value: dict, expected: Price) -> None:
    recurring = value.get("recurring") or {}
    if (
        value.get("id") != expected.id
        or value.get("currency") != "usd"
        or value.get("unit_amount") != expected.amount
        or recurring.get("interval") != "year"
        or recurring.get("interval_count") != 1
        or value.get("type") != "recurring"
    ):
        raise BillingError("PRICE_INVALID", "The annual plan price could not be verified.", 503)


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
