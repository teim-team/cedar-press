"""Paid account activation and retryable delivery, separate from checkout."""

from __future__ import annotations

import hashlib
import secrets
import uuid

from cedar_press import db, subscribers
from cedar_press.billing.contracts import EmailSender
from cedar_press.billing.policy import BillingError, unavailable
from cedar_press.billing.support import application_url


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


class AccountSetupService:
    def __init__(self, email_sender: EmailSender, *, database=db, app_url=None):
        self.db = database
        self.email_sender = email_sender
        self.app_url = app_url or application_url

    def send_claim(self, customer):
        # Recoverable queue entry. The checkout flag also covers emails sent by
        # older releases, so deploying the queue does not resend every purchase.
        self.db.execute(
            """INSERT INTO cedar_press_account_email_deliveries(checkout_id)
            SELECT id FROM cedar_press_guest_checkouts WHERE customer_id=%s
            AND status='complete' AND claim_sent_at IS NULL ON CONFLICT DO NOTHING""",
            (customer,),
        )
        lease = uuid.uuid4()
        with self.db.pool().connection() as conn, conn.cursor() as cur:
            cur.execute(
                """UPDATE cedar_press_account_email_deliveries d SET status='sending',
                lease_id=%s,lease_until=now()+interval '2 minutes',attempts=attempts+1,
                updated_at=now() FROM cedar_press_guest_checkouts g
                WHERE d.checkout_id=g.id AND g.customer_id=%s
                AND (d.status='pending' OR (d.status='sending' AND d.lease_until<now()))
                RETURNING g.id,g.user_id,g.email""",
                (lease, customer),
            )
            delivery = cur.fetchone()
            if not delivery:
                return
            cur.execute(
                "SELECT password_hash FROM cedar_press_subscribers WHERE id=%s",
                (delivery["user_id"],),
            )
            sign_in = cur.fetchone()["password_hash"] is not None
            token = None if sign_in else secrets.token_urlsafe(32)
            if token:
                cur.execute(
                    """INSERT INTO cedar_press_account_setup_links
                    (token_hash,user_id,email,expires_at)
                    VALUES (%s,%s,%s,now()+interval '1 hour')""",
                    (token_hash(token), delivery["user_id"], delivery["email"]),
                )
        # No open transaction, row lock or checked-out connection during SMTP.
        try:
            link = self.app_url() + ("/login" if sign_in else "/create-account#token=" + token)
            self.email_sender.send_link(
                delivery["email"], link, **({"sign_in": True} if sign_in else {})
            )
        except Exception:
            self.db.execute(
                """UPDATE cedar_press_account_email_deliveries SET status='pending',
                lease_until=NULL,updated_at=now() WHERE checkout_id=%s AND lease_id=%s""",
                (delivery["id"], lease),
            )
            raise
        with self.db.pool().connection() as conn, conn.cursor() as cur:
            cur.execute(
                """UPDATE cedar_press_account_email_deliveries SET status='sent',
                lease_until=NULL,updated_at=now() WHERE checkout_id=%s AND lease_id=%s
                AND status='sending' RETURNING checkout_id""",
                (delivery["id"], lease),
            )
            if cur.fetchone():
                cur.execute(
                    "UPDATE cedar_press_guest_checkouts SET claim_sent_at=now() WHERE id=%s",
                    (delivery["id"],),
                )

    def request_resend(self, checkout_id):
        # Do not revoke any delivered tokens. A token expires or is consumed
        # when the account is established, regardless of delivery retries.
        self.db.execute(
            """INSERT INTO cedar_press_account_email_deliveries(checkout_id)
            VALUES (%s) ON CONFLICT(checkout_id) DO UPDATE SET status='pending',updated_at=now()
            WHERE cedar_press_account_email_deliveries.status='sent'""",
            (checkout_id,),
        )

    def account_details(self, token):
        if not self.db.configured():
            raise unavailable()
        row = self.db.one(
            """SELECT s.email FROM cedar_press_account_setup_links l
            JOIN cedar_press_subscribers s ON s.id=l.user_id
            WHERE l.token_hash=%s AND l.used_at IS NULL AND l.expires_at>now()
            AND s.password_hash IS NULL AND s.email=l.email""",
            (token_hash(token),),
        )
        if not row:
            # Preserve outstanding links sent before migration 009.
            row = self.db.one(
                """SELECT s.email FROM cedar_press_password_resets r
                JOIN cedar_press_subscribers s ON s.email=r.email
                JOIN cedar_press_guest_checkouts g ON g.user_id=s.id
                WHERE r.token_hash=%s AND r.used_at IS NULL AND r.expires_at>now()
                AND s.password_hash IS NULL AND g.status='complete'""",
                (token_hash(token),),
            )
        if not row:
            raise BillingError(
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
