"""Small shared billing rules with no service or HTTP dependencies."""

from __future__ import annotations

import datetime as dt
import os
from urllib.parse import urlsplit

from cedar_press.billing.policy import BillingError, reference, unavailable


def utc_now():
    return dt.datetime.now(dt.timezone.utc)


def application_url():
    value = os.environ.get("CEDAR_PRESS_APP_URL", "http://localhost:5173").rstrip("/")
    parsed = urlsplit(value)
    development = os.environ.get("CEDAR_PRESS_ENVIRONMENT", "development") == "development"
    if (
        not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path
        or (
            parsed.scheme != "https"
            and not (
                development
                and parsed.scheme == "http"
                and parsed.hostname in {"localhost", "127.0.0.1"}
            )
        )
    ):
        raise unavailable()
    return value


def verify_customer(value, customer):
    if reference(value.get("customer")) != customer:
        raise BillingError("BILLING_OWNER_MISMATCH", "Billing data could not be verified.", 502)


def verify_write(cur):
    if cur.rowcount != 1:
        raise BillingError(
            "BILLING_OWNER_MISMATCH", "Billing ownership could not be verified.", 502
        )
