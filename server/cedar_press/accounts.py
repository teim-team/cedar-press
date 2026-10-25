"""Persistent identity and billing foundation, independent of paid access.

No public registration or provider-token handling lives here. Existing passwords
and subscriber authorization remain in subscribers.py during the additive bridge.
"""

from __future__ import annotations

from cedar_press import db


def create_user(email: str) -> dict[str, object]:
    """Create an unverified, unpaid identity; never grant a subscription.

    Duplicate emails raise the database uniqueness error, rather than returning
    another person's identity as if the caller had authenticated it.
    """
    address = email.strip().lower()
    if not address or "@" not in address:
        raise ValueError("An email address is required")
    if not db.configured():
        raise RuntimeError("Account creation requires PostgreSQL")
    row = db.one(
        "INSERT INTO cedar_press_users (email) VALUES (%s)"
        " RETURNING id, email, email_verified_at, created_at",
        (address,),
    )
    assert row is not None
    return row
