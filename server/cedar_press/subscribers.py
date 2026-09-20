"""Who holds a Cedar Press subscription, and which access code bought it.

TWO BACKENDS, ONE INTERFACE, CHOSEN BY `DATABASE_URL`.
Without it, this is exactly what the service did before: subscribers parsed
out of `CEDAR_PRESS_ACCOUNTS`, codes out of `CEDAR_PRESS_CODES`, and anything
activated at runtime held in a module-level dict that a restart forgets. That
is the right behaviour for the preview deployment and for the test suite, and
the wrong behaviour for a product somebody has paid for.

With it, the same calls read and write `cedar_press_subscribers` and
`cedar_press_codes` in the platform's own database, beside teim-app's
`users`. A subscriber who activates a code is a row, written in the same
transaction that marks the code spent, so the two can never disagree about
whether an access code was used.

WHY EMAIL IS THE KEY AND `user_id` IS NOT.
A Tribal Business News subscriber can arrive with an access code before they
have ever opened the platform. Requiring a `users` row first would make the
platform a prerequisite for a product sold separately through somebody else's
magazine. So `email` is the key that always exists and `user_id` is bound
when — if — a platform account appears. `bind_user` is that moment.

WHY THE PASSWORD RULE IS NOT IN HERE.
This module answers "is this address a subscriber, and on which tier".
`session.py` still owns the cookie, the signature and the comparison, so
there is one place that decides whether somebody is signed in. What changed
is where it looks the subscriber up.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import os
import re
from dataclasses import dataclass

from cedar_press import db

TIERS = ("press", "press_pro")


@dataclass(frozen=True)
class Subscriber:
    email: str
    tier: str
    account_id: str
    password_hash: str | None = None


@dataclass(frozen=True)
class Code:
    code: str
    email: str
    tier: str
    expires_on: dt.date | None
    spent_at: dt.datetime | None

    def has_expired(self, today: dt.date) -> bool:
        return self.expires_on is not None and self.expires_on < today

    @property
    def spent(self) -> bool:
        return self.spent_at is not None


# ── the subscription an address belongs to ──────────────────────────────────

def account_id_for(email: str) -> str:
    """The SUBSCRIPTION an address belongs to, for Shape the Research.

    Two seats naming one account share one ledger: the organization earns its
    points once a month, not once per seat, and the priorities page counts
    subscriptions rather than people — "30 points from 25 organizations" is
    not "30 from 5". An address with no account of its own is its own
    subscription.

    THE RULE IS NOT THE EMAIL DOMAIN, AND THAT WAS TEMPTING. Grouping by
    domain would put every address at a shared tribal-enterprise domain on
    one ledger without anybody saying so, and would split an organization
    whose staff use two domains after an acquisition — which is precisely the
    thing Cedar's own identity work exists to get right, and not something to
    guess at from a string. So the grouping is declared: the `account` field
    on the provisioned record, or the `account_id` column on the subscriber
    row. Absent, an address is its own subscription.
    """
    address = (email or "").strip().lower()
    if not address:
        return ""
    if db.configured():
        row = db.one(
            "SELECT account_id FROM cedar_press_subscribers WHERE lower(email) = %s",
            (address,),
        )
        if row and row["account_id"]:
            return str(row["account_id"])
        return address
    raw = os.environ.get("CEDAR_PRESS_ACCOUNTS", "").strip()
    if raw:
        try:
            record = json.loads(raw).get(address)
        except json.JSONDecodeError:
            record = None
        if isinstance(record, dict) and record.get("account"):
            return str(record["account"]).strip()
    return address


# ── password hashing ────────────────────────────────────────────────────────

_ROUNDS = 240_000


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    """`pbkdf2$rounds$salt$hash`, which is what the column stores.

    PBKDF2 out of the standard library rather than argon2 or bcrypt: this
    service has no compiled dependencies today and adding one to the image
    for a preview is a poor trade. The format carries its own parameters, so
    moving to argon2 later is a new prefix and a re-hash on next sign-in
    rather than a migration.
    """
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ROUNDS)
    return f"pbkdf2${_ROUNDS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    """Constant-time, and false for anything it does not recognise."""
    if not stored:
        return False
    try:
        scheme, rounds, salt_hex, want = stored.split("$", 3)
    except ValueError:
        return False
    if scheme != "pbkdf2":
        return False
    try:
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(rounds)
        )
    except ValueError:
        return False
    return hmac.compare_digest(digest.hex(), want)


# ── the environment backend (no DATABASE_URL) ───────────────────────────────

#: Accounts activated in this process. In-memory, so a restart forgets them —
#: which is why `DATABASE_URL` exists.
_activated: dict[str, tuple[str, str]] = {}
_spent: set[str] = set()


def _env_accounts() -> dict[str, tuple[str, str]]:
    raw = os.environ.get("CEDAR_PRESS_ACCOUNTS", "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    out: dict[str, tuple[str, str]] = {}
    for email, record in parsed.items():
        if isinstance(record, dict) and record.get("password"):
            out[email.strip().lower()] = (
                str(record["password"]),
                str(record.get("tier", "press")),
            )
    return out


#: A code, in the one form everything stores and compares it in: uppercase,
#: no spaces, no hyphens. `codes.normalize` is the same rule and the client's
#: `normalizePressCode` is the same rule again — a code the form accepts and
#: the server rejects over a hyphen the reader was told not to worry about
#: reads as "my subscription is not real". Keeping the canonical form HERE
#: means the database column holds it too, so a lookup is an index hit rather
#: than a scan over every stored spelling.
_SEPARATORS = re.compile(r"[\s-]+")


def canonical(raw: str | None) -> str:
    return _SEPARATORS.sub("", str(raw or "")).upper()


def _env_codes() -> dict[str, dict[str, object]]:
    raw = os.environ.get("CEDAR_PRESS_CODES", "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return {canonical(k): v for k, v in parsed.items() if isinstance(v, dict)}


def forget_activated_for_tests() -> None:
    _activated.clear()
    _spent.clear()


# ── the interface ───────────────────────────────────────────────────────────


def find(email: str) -> Subscriber | None:
    """The subscriber at this address, or None."""
    address = (email or "").strip().lower()
    if not address:
        return None
    if db.configured():
        row = db.one(
            "SELECT email, tier, account_id, password_hash"
            " FROM cedar_press_subscribers WHERE lower(email) = %s",
            (address,),
        )
        if not row:
            return None
        return Subscriber(row["email"], row["tier"], row["account_id"], row["password_hash"])
    if address in _activated:
        password, tier = _activated[address]
    else:
        found = _env_accounts().get(address)
        if not found:
            return None
        password, tier = found
    return Subscriber(address, tier, account_id_for(address), password)


def authenticate(email: str, password: str) -> Subscriber | None:
    """The subscriber, if the password is theirs.

    The two backends store the secret differently and deliberately: the
    environment one holds it in plain text, because it is a list of preview
    logins in a deployment variable and pretending otherwise would be
    theatre. The database one holds a PBKDF2 hash and never the password.
    """
    found = find(email)
    if not found:
        return None
    if db.configured():
        return found if verify_password(password, found.password_hash) else None
    return found if hmac.compare_digest(found.password_hash or "", password) else None


def create(email: str, password: str, tier: str) -> Subscriber:
    """Add a subscriber. Used by activation, which has already spent a code."""
    address = (email or "").strip().lower()
    if tier not in TIERS:
        raise ValueError(f"tier must be one of {TIERS}")
    account = account_id_for(address)
    if db.configured():
        db.execute(
            "INSERT INTO cedar_press_subscribers (email, account_id, tier, password_hash)"
            " VALUES (%s, %s, %s, %s)"
            " ON CONFLICT (email) DO UPDATE SET tier = EXCLUDED.tier,"
            " password_hash = EXCLUDED.password_hash, updated_at = now()",
            (address, account, tier, hash_password(password)),
        )
    else:
        _activated[address] = (password, tier)
    return Subscriber(address, tier, account)


def exists(email: str) -> bool:
    return find(email) is not None


def bind_user(email: str, user_id: str) -> bool:
    """Tie a subscription to a platform account once one exists.

    Returns False without a database, because there is nothing to tie it to:
    `users` lives in Postgres and the environment backend has no notion of a
    platform account at all.
    """
    if not db.configured():
        return False
    return (
        db.execute(
            "UPDATE cedar_press_subscribers SET user_id = %s, updated_at = now()"
            " WHERE lower(email) = %s",
            (user_id, (email or "").strip().lower()),
        )
        > 0
    )


def link_platform_account(email: str) -> bool:
    """Tie this subscription to the teim-app account at the same address.

    Called on sign-in and on activation, because those are the two moments
    the service is certain who is at the keyboard, and because the order the
    two accounts appear in is not ours to choose: a Tribal Business News
    subscriber may activate a press code months before they ever open the
    platform, or the other way round. Binding on every sign-in means whichever
    comes second still finds the first.

    One statement, so a sign-in costs one no-op UPDATE rather than a lookup
    and a write: `IS DISTINCT FROM` makes a subscription that is already bound
    — the overwhelming majority — touch nothing.

    Returns whether a binding was made. False is the ordinary answer: no
    database, no `users` table (Cedar Press pointed at a database of its own),
    no platform account at that address yet, or already bound.
    """
    if not db.configured():
        return False
    address = (email or "").strip().lower()
    if not address:
        return False
    # Asked rather than caught: a deployment that runs Cedar Press against its
    # own database has no `users` table, and that is a supported arrangement,
    # not an error to swallow.
    present = db.one("SELECT to_regclass('public.users') AS table_name")
    if not present or not present["table_name"]:
        return False
    return (
        db.execute(
            "UPDATE cedar_press_subscribers s SET user_id = u.id, updated_at = now()"
            " FROM users u"
            " WHERE lower(s.email) = %s AND lower(u.email) = lower(s.email)"
            " AND s.user_id IS DISTINCT FROM u.id",
            (address,),
        )
        > 0
    )


# ── access codes ────────────────────────────────────────────────────────────


def find_code(code: str) -> Code | None:
    key = canonical(code)
    if not key:
        return None
    if db.configured():
        row = db.one(
            "SELECT code, email, tier, expires_on, spent_at FROM cedar_press_codes"
            " WHERE code = %s",
            (key,),
        )
        if not row:
            return None
        return Code(row["code"], row["email"], row["tier"], row["expires_on"], row["spent_at"])
    raw = _env_codes().get(key)
    if not raw:
        return None
    expires = raw.get("expires")
    return Code(
        key,
        str(raw.get("email", "")).strip().lower(),
        str(raw.get("tier", "press")),
        dt.date.fromisoformat(str(expires)) if expires else None,
        dt.datetime.now(dt.timezone.utc) if key in _spent else None,
    )


def redeem(code: str, password: str) -> Subscriber | None:
    """Spend a code and create the subscriber it names, together.

    ONE TRANSACTION, AND THAT IS THE POINT. The old flow marked the code
    spent in one place and added the account in another, so a failure between
    them left a code that could never be used again and a subscriber who had
    never been created. Here the `UPDATE ... WHERE spent_at IS NULL` both
    claims the code and proves nobody else claimed it first — the row count
    is the answer — and the subscriber is inserted before the commit.

    Returns None when the code does not exist, has expired, or was already
    spent. The caller decides what to tell the reader; this decides what is
    true.
    """
    key = canonical(code)
    found = find_code(key)
    if not found or found.spent or found.has_expired(dt.date.today()):
        return None

    if not db.configured():
        _spent.add(key)
        return create(found.email, password, found.tier)

    with db.pool().connection() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE cedar_press_codes SET spent_at = now(), spent_by = %s"
            " WHERE code = %s AND spent_at IS NULL",
            (found.email, key),
        )
        if cur.rowcount == 0:
            # Somebody redeemed it between the read above and this write.
            conn.rollback()
            return None
        cur.execute(
            "INSERT INTO cedar_press_subscribers (email, account_id, tier, password_hash)"
            " VALUES (%s, %s, %s, %s)"
            " ON CONFLICT (email) DO UPDATE SET tier = EXCLUDED.tier,"
            " password_hash = EXCLUDED.password_hash, updated_at = now()",
            (found.email, account_id_for(found.email), found.tier, hash_password(password)),
        )
        conn.commit()
    return Subscriber(found.email, found.tier, account_id_for(found.email))


def issue_code(code: str, email: str, tier: str, expires_on: dt.date | None = None) -> None:
    """Record a code Tribal Business News has issued. Database only."""
    if not db.configured():
        raise RuntimeError("issuing codes needs DATABASE_URL")
    if tier not in TIERS:
        raise ValueError(f"tier must be one of {TIERS}")
    db.execute(
        "INSERT INTO cedar_press_codes (code, email, tier, expires_on)"
        " VALUES (%s, %s, %s, %s) ON CONFLICT (code) DO NOTHING",
        (canonical(code), (email or "").strip().lower(), tier, expires_on),
    )
