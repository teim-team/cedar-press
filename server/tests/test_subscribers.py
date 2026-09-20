"""The subscriber store, on both backends.

Every test here runs twice: once with no `DATABASE_URL`, which is the
preview and the suite's default, and once against a real Postgres when
`CEDAR_PRESS_TEST_DATABASE_URL` names one. The point of the pair is that the
two backends answer the same questions the same way — a seam whose two sides
disagree is worse than no seam, because the disagreement only shows up in
production.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cedar_press import db, subscribers  # noqa: E402

PG = os.environ.get("CEDAR_PRESS_TEST_DATABASE_URL", "").strip()

ACCOUNTS = json.dumps(
    {
        "reader@example.org": {"password": "correct-horse", "tier": "press"},
        "pro@example.org": {"password": "correct-horse", "tier": "press_pro"},
        # Two seats, one subscription, declared.
        "one@bank.example": {
            "password": "correct-horse", "tier": "press_pro", "account": "acct-bank"
        },
        "two@bank.example": {
            "password": "correct-horse", "tier": "press_pro", "account": "acct-bank"
        },
    }
)
CODES = json.dumps(
    {
        "TBN4-9K2M-X7QD": {"email": "new@example.org", "tier": "press"},
        "TBN4-0000-EXPD": {"email": "late@example.org", "tier": "press", "expires": "2020-01-01"},
    }
)


class _Backend:
    """Both backends, one set of expectations.

    A mixin, not a TestCase: as a TestCase it would be collected and run a
    third time on whatever backend the environment happened to have.
    """

    pg = False

    def setUp(self) -> None:
        subscribers.forget_activated_for_tests()
        db.reset_for_tests()
        if self.pg:
            os.environ["DATABASE_URL"] = PG
            os.environ.pop("CEDAR_PRESS_ACCOUNTS", None)
            os.environ.pop("CEDAR_PRESS_CODES", None)
            db.migrate()
            db.execute("TRUNCATE cedar_press_subscribers, cedar_press_codes")
            for email, tier in (("reader@example.org", "press"), ("pro@example.org", "press_pro")):
                subscribers.create(email, "correct-horse", tier)
            for seat in ("one@bank.example", "two@bank.example"):
                subscribers.create(seat, "correct-horse", "press_pro")
                db.execute(
                    "UPDATE cedar_press_subscribers SET account_id = %s WHERE email = %s",
                    ("acct-bank", seat),
                )
            subscribers.issue_code("TBN4-9K2M-X7QD", "new@example.org", "press")
            subscribers.issue_code(
                "TBN4-0000-EXPD", "late@example.org", "press", dt.date(2020, 1, 1)
            )
        else:
            os.environ.pop("DATABASE_URL", None)
            os.environ["CEDAR_PRESS_ACCOUNTS"] = ACCOUNTS
            os.environ["CEDAR_PRESS_CODES"] = CODES

    def tearDown(self) -> None:
        os.environ.pop("DATABASE_URL", None)
        db.reset_for_tests()

    def test_a_provisioned_subscriber_is_found_with_their_tier(self) -> None:
        found = subscribers.find("reader@example.org")
        self.assertIsNotNone(found)
        self.assertEqual(found.tier, "press")
        self.assertEqual(subscribers.find("pro@example.org").tier, "press_pro")

    def test_an_unknown_address_is_nobody(self) -> None:
        self.assertIsNone(subscribers.find("stranger@example.org"))
        self.assertIsNone(subscribers.find(""))
        self.assertIsNone(subscribers.find(None))

    def test_the_password_has_to_be_theirs(self) -> None:
        self.assertIsNotNone(subscribers.authenticate("reader@example.org", "correct-horse"))
        self.assertIsNone(subscribers.authenticate("reader@example.org", "wrong"))
        self.assertIsNone(subscribers.authenticate("stranger@example.org", "correct-horse"))

    def test_seats_of_one_organization_share_a_subscription(self) -> None:
        # The points ledger counts by this: 30 points from 25 organizations
        # is not 30 from 5, and the difference is only visible if seats group.
        # The grouping is DECLARED, never inferred from the email domain —
        # see `account_id_for` for why guessing it is the wrong move in this
        # product of all products.
        self.assertEqual(
            subscribers.account_id_for("one@bank.example"),
            subscribers.account_id_for("two@bank.example"),
        )
        # And an address that declares nothing is its own subscription.
        self.assertEqual(
            subscribers.account_id_for("reader@example.org"), "reader@example.org"
        )

    def test_a_code_creates_the_subscriber_it_names(self) -> None:
        made = subscribers.redeem("TBN4-9K2M-X7QD", "a-new-password")
        self.assertIsNotNone(made)
        self.assertEqual(made.email, "new@example.org")
        self.assertEqual(made.tier, "press")
        # And they can now sign in, which is the whole point of activation.
        self.assertIsNotNone(subscribers.authenticate("new@example.org", "a-new-password"))

    def test_a_code_is_spent_once(self) -> None:
        self.assertIsNotNone(subscribers.redeem("TBN4-9K2M-X7QD", "first"))
        # The second attempt gets nothing, and the first password still works:
        # a spent code must not be a way to reset somebody's account.
        self.assertIsNone(subscribers.redeem("TBN4-9K2M-X7QD", "second"))
        self.assertIsNotNone(subscribers.authenticate("new@example.org", "first"))
        self.assertIsNone(subscribers.authenticate("new@example.org", "second"))

    def test_an_expired_code_is_refused(self) -> None:
        self.assertIsNone(subscribers.redeem("TBN4-0000-EXPD", "whatever"))
        self.assertFalse(subscribers.exists("late@example.org"))

    def test_an_unknown_code_is_refused(self) -> None:
        self.assertIsNone(subscribers.redeem("TBN4-NOPE-NOPE", "whatever"))
        self.assertIsNone(subscribers.redeem("", "whatever"))


class TestEnvironmentBackend(_Backend, unittest.TestCase):
    pg = False


@unittest.skipUnless(PG, "set CEDAR_PRESS_TEST_DATABASE_URL to run against Postgres")
class TestPostgresBackend(_Backend, unittest.TestCase):
    pg = True

    def test_the_password_is_never_stored(self) -> None:
        # The environment backend holds a plain password because it is a list
        # of preview logins in a deployment variable. The database one must
        # not, and this is the assertion that says so.
        row = db.one(
            "SELECT password_hash FROM cedar_press_subscribers WHERE email = %s",
            ("reader@example.org",),
        )
        self.assertNotIn("correct-horse", row["password_hash"])
        self.assertTrue(row["password_hash"].startswith("pbkdf2$"))

    def test_a_subscription_survives_a_restart(self) -> None:
        # The whole reason this module exists. `reset_for_tests` drops the
        # pool, which is as close to a restart as a test gets.
        subscribers.redeem("TBN4-9K2M-X7QD", "kept")
        db.reset_for_tests()
        self.assertIsNotNone(subscribers.authenticate("new@example.org", "kept"))

    def test_spending_a_code_and_making_the_subscriber_are_one_transaction(self) -> None:
        # A failure between the two used to leave a code nobody could use
        # and a subscriber who was never created.
        subscribers.redeem("TBN4-9K2M-X7QD", "together")
        # Stored in the canonical form — uppercase, no hyphens — so a lookup
        # is one index hit rather than a scan over every way a reader might
        # have typed it. `canonical` is the same rule as `codes.normalize`
        # and the client's `normalizePressCode`.
        code = db.one(
            "SELECT spent_at, spent_by FROM cedar_press_codes WHERE code = %s",
            (subscribers.canonical("TBN4-9K2M-X7QD"),),
        )
        self.assertIsNotNone(code["spent_at"])
        self.assertEqual(code["spent_by"], "new@example.org")
        self.assertTrue(subscribers.exists("new@example.org"))

    def test_a_subscription_can_be_tied_to_a_platform_account(self) -> None:
        # A Tribal Business News subscriber may arrive before they have ever
        # opened the platform, so the binding happens later, if at all.
        # `users` is teim-app's table, so this test creates its row without
        # truncating one it does not own — which is also how the real binding
        # will run, against a users table full of other people.
        user = db.one(
            "INSERT INTO users (email, password_hash) VALUES (%s, 'x')"
            " ON CONFLICT (email) DO UPDATE SET password_hash = EXCLUDED.password_hash"
            " RETURNING id",
            ("reader@example.org",),
        )
        self.assertTrue(subscribers.bind_user("reader@example.org", user["id"]))
        row = db.one(
            "SELECT user_id FROM cedar_press_subscribers WHERE email = %s",
            ("reader@example.org",),
        )
        self.assertEqual(str(row["user_id"]), str(user["id"]))

    def test_the_binding_happens_by_itself_at_sign_in(self) -> None:
        """`link_platform_account` is what the login route calls, in one statement."""
        # `users` is teim-app's, so this makes and unmakes exactly its own row
        # rather than truncating a table it does not own.
        db.execute("DELETE FROM users WHERE email = %s", ("pro@example.org",))
        self.assertFalse(subscribers.link_platform_account("pro@example.org"))
        user = db.one(
            "INSERT INTO users (email, password_hash) VALUES (%s, 'x') RETURNING id",
            ("pro@example.org",),
        )
        # The platform account appeared second; the next sign-in finds it.
        self.assertTrue(subscribers.link_platform_account("PRO@Example.org "))
        row = db.one(
            "SELECT user_id FROM cedar_press_subscribers WHERE email = %s",
            ("pro@example.org",),
        )
        self.assertEqual(str(row["user_id"]), str(user["id"]))
        # Already bound: every sign-in after the first writes nothing, which is
        # why the route can afford to call this unconditionally.
        self.assertFalse(subscribers.link_platform_account("pro@example.org"))
        # And an address with no subscription binds nothing at all.
        self.assertFalse(subscribers.link_platform_account("stranger@example.org"))
        # Tidied here rather than in a cleanup, which would run after tearDown
        # has already put `DATABASE_URL` back and closed the pool.
        db.execute("DELETE FROM users WHERE email = %s", ("pro@example.org",))


if __name__ == "__main__":
    unittest.main()
