"""Hashed activation links, mailbox verification and initial credentials."""

import hashlib
import secrets

from cedar_press import db, subscribers
from cedar_press.accounts.errors import AccountError


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


class AccountSetupService:
    def __init__(self, *, database=db):
        self.db = database

    def issue_link(self, cur, user_id, email):
        token = secrets.token_urlsafe(32)
        cur.execute(
            """INSERT INTO cedar_press_account_setup_links
            (token_hash,user_id,email,expires_at)
            VALUES (%s,%s,%s,now()+interval '1 hour')""",
            (token_hash(token), user_id, email),
        )
        return token

    def account_details(self, token):
        if not self.db.configured():
            raise AccountError(
                "ACCOUNT_UNAVAILABLE", "Account setup is temporarily unavailable.", 503
            )
        row = self.db.one(
            """SELECT s.email FROM cedar_press_account_setup_links l
            JOIN cedar_press_subscribers s ON s.id=l.user_id
            WHERE l.token_hash=%s AND l.used_at IS NULL AND l.expires_at>now()
            AND s.password_hash IS NULL AND s.email=l.email""",
            (token_hash(token),),
        )
        if not row:
            # Preserve outstanding links sent before migration 009.
            row = subscribers.legacy_setup_email(token_hash(token))
        if not row:
            raise AccountError(
                "ACCOUNT_LINK_INVALID",
                "This account link expired or was already used. "
                "Request a password link to sign in.",
            )
        return row

    def confirm(self, token, password, name):
        if not self.db.configured():
            return None
        hashed_password = subscribers.hash_password(password)
        with self.db.pool().connection() as conn, conn.cursor() as cur:
            # Lock the identity first; two different links cannot overwrite
            # credentials when redeemed concurrently.
            cur.execute(
                """SELECT s.id,s.email FROM cedar_press_subscribers s
                JOIN cedar_press_account_setup_links l ON l.user_id=s.id
                WHERE l.token_hash=%s AND l.used_at IS NULL AND l.expires_at>now()
                AND s.password_hash IS NULL AND s.email=l.email FOR UPDATE OF s""",
                (token_hash(token),),
            )
            user = cur.fetchone()
            if user:
                cur.execute(
                    """UPDATE cedar_press_subscribers SET password_hash=%s,display_name=%s,
                    email_verified_at=COALESCE(email_verified_at,now()),updated_at=now()
                    WHERE id=%s AND password_hash IS NULL RETURNING id""",
                    (hashed_password, name, user["id"]),
                )
                if not cur.fetchone():
                    return None
                cur.execute(
                    "UPDATE cedar_press_account_setup_links SET used_at=now() "
                    "WHERE user_id=%s AND used_at IS NULL",
                    (user["id"],),
                )
                cur.execute(
                    "UPDATE cedar_press_password_resets SET used_at=now() "
                    "WHERE email=%s AND used_at IS NULL",
                    (user["email"],),
                )
        if user:
            return subscribers.find(user["email"])
        return subscribers.redeem_reset(token, password, account_setup=True, display_name=name)
