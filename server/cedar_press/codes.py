"""Access codes: the way in.

An eligible Tribal Business News membership issues one code. The code
establishes the entitlement, the account follows, and Tribal Business News
owns payment, renewals, upgrades and issuance. From here the only questions
are whether a code is real, unspent, unexpired, and issued to the address in
front of us.

WHY THE CODE AND NOT A SIGN-UP FORM
Cedar Press is sold, not self-served. Anyone can type an email address; only
a subscriber has a code. Checking it here is what keeps the shelf closed
without asking the reader to prove anything a subscription has already
proved.

WHAT REPLACES THIS
The issuance table Tribal Business News writes to, and the subscriber table
the account lands in. The seams are ``_register`` and ``_spent``: everything
else — the checks, their order, the error codes the client already renders —
stays as it is.

The codes are read from the environment for the same reason the accounts
are: no credential is committed to the repository, and a deployment without
a register activates nobody rather than falling back to something
convenient.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import date

#: Error codes the client already has copy for. See
#: ``src/features/grove/pressSignup.js::pressSignupError`` — adding one here
#: without adding it there gets the reader a generic "that did not work".
CODE_INVALID = "PRESS_CODE_INVALID"
CODE_USED = "PRESS_CODE_USED"
CODE_EXPIRED = "PRESS_CODE_EXPIRED"
CODE_EMAIL_MISMATCH = "PRESS_CODE_EMAIL_MISMATCH"
EMAIL_IN_USE = "EMAIL_IN_USE"

_SEPARATORS = re.compile(r"[\s-]+")


def normalize(raw: str | None) -> str:
    """Uppercase, no spaces, no hyphens.

    Identical to ``normalizePressCode`` in the client, deliberately. A code
    that the form accepts and the server rejects because of a hyphen the
    reader was told not to worry about is the worst kind of bug: it reads as
    "my subscription is not real".
    """
    return _SEPARATORS.sub("", str(raw or "")).upper()


def is_plausible(raw: str | None) -> bool:
    """Shape only, mirroring ``isPlausiblePressCode``.

    The client checks this before spending a round trip; the server checks it
    again because a client-side check is a courtesy, not a control.
    """
    code = normalize(raw)
    return 8 <= len(code) <= 32 and code.isalnum() and code.isascii()


@dataclass(frozen=True)
class Issued:
    """A code as Tribal Business News issued it."""

    code: str
    email: str
    tier: str
    expires: str | None

    def has_expired(self, today: date) -> bool:
        if not self.expires:
            return False
        try:
            return date.fromisoformat(self.expires) < today
        except ValueError:
            # An unparseable date is a register we cannot trust. Treated as
            # expired rather than as unlimited: the failure that turns a typo
            # into a permanent code is worse than the one that sends a
            # subscriber back to Tribal Business News.
            return True


def _register() -> dict[str, Issued]:
    """Issued codes, from ``CEDAR_PRESS_CODES``.

    A JSON object::

        {"TBN-2026-ABCD-1234": {"email": "reader@example.org",
                                "tier": "press",
                                "expires": "2027-01-31"}}

    Empty by default, so a service started without a register activates
    nobody.
    """
    raw = os.environ.get("CEDAR_PRESS_CODES", "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    issued: dict[str, Issued] = {}
    for code, record in parsed.items():
        if not isinstance(record, dict) or not record.get("email"):
            continue
        key = normalize(code)
        if not key:
            continue
        issued[key] = Issued(
            code=key,
            email=str(record["email"]).strip().lower(),
            tier=str(record.get("tier", "press")),
            expires=(str(record["expires"]) if record.get("expires") else None),
        )
    return issued


#: Codes spent in this process. The real one is a column on the issuance
#: row, written in the same transaction that creates the account; this is
#: in-memory and therefore forgotten on restart, which is the one behaviour
#: here that must not survive into production.
_spent: set[str] = set()


def check(
    raw_code: str | None, email: str | None, *, today: date | None = None
) -> tuple[Issued | None, str | None]:
    """Whether this code may be activated by this address.

    Returns ``(issued, None)`` when it may, and ``(None, error_code)`` when it
    may not.

    The order is deliberate. "Not recognized" comes before every other
    answer, so a code that was never issued cannot be told apart from one
    issued to somebody else: the alternative leaks which codes exist to
    anyone willing to guess.
    """
    code = normalize(raw_code)
    if not is_plausible(code):
        return None, CODE_INVALID

    issued = _register().get(code)
    if issued is None:
        return None, CODE_INVALID
    if code in _spent:
        return None, CODE_USED
    if issued.has_expired(today or date.today()):
        return None, CODE_EXPIRED
    if issued.email != str(email or "").strip().lower():
        return None, CODE_EMAIL_MISMATCH
    return issued, None


def spend(code: str) -> None:
    """Mark a code activated. One code, one account."""
    _spent.add(normalize(code))


def reset_for_tests() -> None:
    """Forget what has been spent. Tests only."""
    _spent.clear()
