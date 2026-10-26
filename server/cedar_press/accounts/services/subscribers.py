"""Who holds a Cedar Press subscription, and on which tier.

TWO BACKENDS, ONE INTERFACE, CHOSEN BY `DATABASE_URL`.
Without it, subscribers are parsed out of `CEDAR_PRESS_ACCOUNTS`, and
anything created at runtime is held in a module-level dict that a restart
forgets. That is the right behaviour for the preview deployment and for the
test suite, and the wrong behaviour for a product somebody has paid for.

With it, the same calls read and write `cedar_press_subscribers` in the
platform's own database, beside teim-app's `users`.

WHY EMAIL IS THE KEY AND `user_id` IS NOT.
A subscriber can buy Cedar Press before they have ever opened the platform.
Requiring a `users` row first would make the platform a prerequisite for a
product sold on its own. So `email` is the key that always exists and
`user_id` is bound when — if — a platform account appears. `bind_user` is
that moment.

WHY THE PASSWORD RULE IS NOT IN HERE.
This module answers "is this address a subscriber, and on which tier".
`sessions.py` still owns the cookie, the signature and the comparison, so
there is one place that decides whether somebody is signed in. What changed
is where it looks the subscriber up.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import os
import secrets
import threading

from cedar_press import db
from cedar_press.accounts.models import Subscriber as Subscriber

TIERS = ("press", "press_pro")


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

_ROUNDS = 600_000


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


#: A hash of nothing anybody can sign in with, used to spend the same work on
#: an unknown address as on a wrong password. Built at import, so a refusal
#: costs one verification rather than a derivation and a verification.
_DUMMY_HASH = hash_password(os.urandom(32).hex())


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
_session_revisions: dict[str, int] = {}
#: Email -> display name, for accounts without a database.
_names: dict[str, str] = {}
_session_lock = threading.Lock()
#: Email -> (reset token hash, expires at): one live link per address.
_resets: dict[str, tuple[str, dt.datetime]] = {}


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


def forget_activated_for_tests() -> None:
    _activated.clear()
    _resets.clear()
    _names.clear()
    with _session_lock:
        _session_revisions.clear()


# ── the interface ───────────────────────────────────────────────────────────


def _session_revision(value: dt.datetime) -> str:
    """Stable instant across worker/database session timezone settings."""
    if not isinstance(value, dt.datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Subscriber session revision must be timezone-aware")
    return value.astimezone(dt.timezone.utc).isoformat(timespec="microseconds")


def find(email: str) -> Subscriber | None:
    """The subscriber at this address, or None."""
    address = (email or "").strip().lower()
    if not address:
        return None
    if db.configured():
        row = db.one(
            "SELECT s.email, COALESCE(access.tier, 'free') AS tier, s.account_id,"
            " s.password_hash, s.sessions_revoked_at FROM cedar_press_subscribers s"
            " JOIN cedar_press_current_access access ON access.user_id=s.id"
            " WHERE lower(s.email) = %s",
            (address,),
        )
        if not row:
            return None
        return Subscriber(
            row["email"],
            row["tier"],
            row["account_id"],
            row["password_hash"],
            _session_revision(row["sessions_revoked_at"]),
        )
    if address in _activated:
        password, tier = _activated[address]
    else:
        found = _env_accounts().get(address)
        if not found:
            return None
        password, tier = found
    with _session_lock:
        revision = str(_session_revisions.get(address, 0))
    return Subscriber(address, tier, account_id_for(address), password, revision)


def revoke_sessions(email: str) -> bool:
    """Invalidate all sessions for this account, persistently when configured."""
    address = (email or "").strip().lower()
    if not address:
        return False
    if db.configured():
        return (
            db.execute(
                "UPDATE cedar_press_subscribers SET sessions_revoked_at ="
                " GREATEST(clock_timestamp(), sessions_revoked_at + interval '1 microsecond')"
                " WHERE lower(email) = %s",
                (address,),
            )
            > 0
        )
    if find(address) is None:
        return False
    with _session_lock:
        _session_revisions[address] = _session_revisions.get(address, 0) + 1
    return True


def authenticate(email: str, password: str) -> Subscriber | None:
    """The subscriber, if the password is theirs.

    The two backends store the secret differently and deliberately: the
    environment one holds it in plain text, because it is a list of preview
    logins in a deployment variable and pretending otherwise would be
    theatre. The database one holds a PBKDF2 hash and never the password.
    """
    found = find(email)
    if not found:
        if db.configured():
            # THE SAME 401 IS NOT THE SAME ANSWER IF ONE ARRIVES FASTER.
            # A known address costs 600,000 PBKDF2 rounds to refuse and an
            # unknown one used to cost a SELECT, which is a difference large
            # enough and repeatable enough to read off a stopwatch. That turns
            # the login form into a query for "is this person a Cedar Press
            # subscriber" — answerable about anybody, without an account.
            # The work is done and the result discarded.
            verify_password(password, _DUMMY_HASH)
        return None
    if db.configured():
        if not verify_password(password, found.password_hash):
            return None
        if int(found.password_hash.split("$")[1]) < _ROUNDS:
            # Sign-in is the only time the password is in hand to re-derive an
            # older, cheaper hash. Conditional on the hash just verified, so a
            # password changed in the same instant is never overwritten.
            upgraded = db.execute(
                "UPDATE cedar_press_subscribers SET password_hash = %s, updated_at = now()"
                " WHERE lower(email) = %s AND password_hash = %s",
                (hash_password(password), found.email, found.password_hash),
            )
            if upgraded:
                return find(found.email)
        return found
    return found if hmac.compare_digest(found.password_hash or "", password) else None


def create(email: str, password: str, tier: str) -> Subscriber:
    """Add a subscriber, or replace an existing one's password and tier."""
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
        with _session_lock:
            _session_revisions[address] = _session_revisions.get(address, 0) + 1
    return Subscriber(address, tier, account)


def change_password(email: str, password: str) -> Subscriber | None:
    """Change credentials without copying a resolved billing tier into legacy access."""
    address = email.strip().lower()
    if db.configured():
        changed = db.execute(
            "UPDATE cedar_press_subscribers SET password_hash=%s,updated_at=now()"
            " WHERE lower(email)=%s",
            (hash_password(password), address),
        )
        return find(address) if changed else None
    found = find(address)
    return create(address, password, found.tier) if found else None


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

    Called after password authentication during sign-in and activation. It is
    a no-op when the optional teim-app users table or matching account is absent.

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


# ── password resets ─────────────────────────────────────────────────────────

RESET_LIFETIME = dt.timedelta(hours=1)


def _reset_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def legacy_setup_email(token_digest: str):
    """Recognize outstanding setup links issued before migration 009."""
    return db.one(
        """SELECT s.email FROM cedar_press_password_resets r
        JOIN cedar_press_subscribers s ON s.email=r.email
        JOIN cedar_press_checkouts c ON c.user_id=s.id
        WHERE r.token_hash=%s AND r.used_at IS NULL AND r.expires_at>now()
        AND s.password_hash IS NULL AND c.status='complete'""",
        (token_digest,),
    )


def issue_reset(email: str) -> str | None:
    """A single-use reset token for this subscriber, or None if there is none.

    Only the token's hash is stored, so reading the table resets nobody. A new
    token replaces any outstanding one, so an older email in the inbox stops
    working.
    """
    found = find(email)
    if found is None:
        return None
    address = found.email.lower()
    token = secrets.token_urlsafe(32)
    expires = dt.datetime.now(dt.timezone.utc) + RESET_LIFETIME
    if db.configured():
        db.execute(
            "INSERT INTO cedar_press_password_resets (token_hash, email, expires_at)"
            " VALUES (%s, %s, %s)"
            " ON CONFLICT (email) WHERE used_at IS NULL DO UPDATE SET"
            " token_hash = EXCLUDED.token_hash, expires_at = EXCLUDED.expires_at,"
            " created_at = now()",
            (_reset_hash(token), address, expires),
        )
    else:
        _resets[address] = (_reset_hash(token), expires)
    return token


def redeem_reset(
    token: str, password: str, *, account_setup=False, display_name=None
) -> Subscriber | None:
    """Set a new password from a reset token.

    None when the token is unknown, expired or already used.
    """
    key = _reset_hash(token or "")
    if db.configured():
        with db.pool().connection() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE cedar_press_password_resets SET used_at=now()"
                " WHERE token_hash=%s AND used_at IS NULL AND expires_at>now()"
                " AND (NOT %s OR EXISTS (SELECT 1 FROM cedar_press_subscribers s"
                " JOIN cedar_press_checkouts g ON g.user_id=s.id"
                " WHERE s.email=cedar_press_password_resets.email AND s.password_hash IS NULL"
                " AND g.status='complete')) RETURNING email",
                (key, account_setup),
            )
            row = cur.fetchone()
            if not row:
                return None
            email = row["email"]
            cur.execute(
                "UPDATE cedar_press_subscribers SET password_hash=%s,updated_at=now(),"
                " email_verified_at=COALESCE(email_verified_at,now()),"
                " display_name=COALESCE(%s,display_name) WHERE email=%s",
                (hash_password(password), display_name, email),
            )
        return find(email)
    else:
        now = dt.datetime.now(dt.timezone.utc)
        email = next((e for e, (h, x) in _resets.items() if h == key and x > now), None)
        if email:
            del _resets[email]
    found = email and find(email)
    return change_password(found.email, password) if found else None


def profile(email: str) -> dict[str, object]:
    """The account's name, when it joined, and whether its address is proven.

    Without a database there is no join date or verification to report, so
    those are None rather than a guess.
    """
    address = (email or "").strip().lower()
    if db.configured():
        row = db.one(
            "SELECT display_name, created_at, email_verified_at FROM cedar_press_subscribers"
            " WHERE lower(email) = %s",
            (address,),
        )
        if row:
            return {
                "name": row["display_name"],
                "member_since": row["created_at"].date().isoformat(),
                "email_verified": row["email_verified_at"] is not None,
            }
    return {"name": _names.get(address), "member_since": None, "email_verified": None}


def set_display_name(email: str, name: str | None) -> None:
    address = (email or "").strip().lower()
    if db.configured():
        db.execute(
            "UPDATE cedar_press_subscribers SET display_name = %s WHERE lower(email) = %s",
            (name, address),
        )
    elif name is None:
        _names.pop(address, None)
    else:
        _names[address] = name
