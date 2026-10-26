"""Retryable account email delivery triggered by completed purchases."""

import uuid

from cedar_press import db
from cedar_press.accounts.interfaces import EmailSender
from cedar_press.accounts.services.setup import AccountSetupService
from cedar_press.billing.utils import application_url


class CheckoutEmailService:
    def __init__(
        self, email_sender: EmailSender, accounts: AccountSetupService, *, database=db, app_url=None
    ):
        self.db = database
        self.email_sender = email_sender
        self.accounts = accounts
        self.app_url = app_url or application_url

    def send_claim(self, customer):
        # Recoverable queue entry. The checkout flag also covers emails sent by
        # older releases, so deploying the queue does not resend every purchase.
        self.db.execute(
            """INSERT INTO cedar_press_account_email_deliveries(checkout_id)
            SELECT id FROM cedar_press_checkouts WHERE customer_id=%s
            AND status='complete' AND claim_sent_at IS NULL ON CONFLICT DO NOTHING""",
            (customer,),
        )
        lease = uuid.uuid4()
        with self.db.pool().connection() as conn, conn.cursor() as cur:
            cur.execute(
                """UPDATE cedar_press_account_email_deliveries d SET status='sending',
                lease_id=%s,lease_until=now()+interval '2 minutes',attempts=attempts+1,
                updated_at=now() FROM cedar_press_checkouts g
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
            token = (
                None
                if sign_in
                else self.accounts.issue_link(cur, delivery["user_id"], delivery["email"])
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
                    "UPDATE cedar_press_checkouts SET claim_sent_at=now() WHERE id=%s",
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
