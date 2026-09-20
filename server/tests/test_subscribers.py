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
import pathlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cedar_press import codes, db, session, subscribers  # noqa: E402

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

    def test_the_subscription_is_read_from_the_row_not_the_environment(self) -> None:
        """Codex, PR #92: two seats of one organization got two ledgers.

        `subscribers.account_id_for` learned to read `account_id` off the row;
        `session.account_id_for` did not, and every points route builds its
        `Account` from that one. So on a Postgres deployment each seat came
        back as its own address: two monthly credits for one subscription,
        two ledgers, and one organization counted twice behind a priority.
        """
        self.assertEqual(subscribers.account_id_for("one@bank.example"), "acct-bank")
        self.assertEqual(subscribers.account_id_for("two@bank.example"), "acct-bank")
        # The name the service actually calls, which is the one that was wrong.
        self.assertEqual(session.account_id_for("one@bank.example"), "acct-bank")
        self.assertEqual(session.account_id_for("two@bank.example"), "acct-bank")
        self.assertEqual(
            session.account_id_for("ONE@Bank.example "), session.account_id_for("two@bank.example")
        )
        # And the existence check, for the same reason: it gated activation
        # and could not see a subscriber row at all.
        self.assertTrue(session.account_exists("reader@example.org"))
        self.assertFalse(session.account_exists("nobody@example.org"))

    def test_a_code_cannot_reset_the_password_on_an_account_that_exists(self) -> None:
        """Codex, PR #92, and this one is the account-takeover shape.

        `redeem` upserted with `DO UPDATE SET password_hash`, so a second code
        issued to an address that already had a subscription would set a new
        password on it without anybody proving they held the old one.
        """
        before = subscribers.find("reader@example.org")
        self.assertIsNotNone(before)
        subscribers.issue_code("TBN9-DUPE-0001", "reader@example.org", "press_pro")
        with self.assertRaises(subscribers.AlreadySubscribed):
            subscribers.redeem("TBN9-DUPE-0001", "a-password-they-do-not-hold")
        after = subscribers.find("reader@example.org")
        self.assertEqual(after.password_hash, before.password_hash)
        self.assertEqual(after.tier, before.tier)
        # And the old password still signs them in.
        self.assertIsNotNone(subscribers.authenticate("reader@example.org", "correct-horse"))
        # The code is not consumed by the refusal, so it can still be voided
        # or reissued deliberately rather than being silently burnt.
        code = db.one(
            "SELECT spent_at FROM cedar_press_codes WHERE code = %s",
            (subscribers.canonical("TBN9-DUPE-0001"),),
        )
        self.assertIsNone(code["spent_at"])

    def test_redemption_needs_one_connection_not_two(self) -> None:
        """Codex, PR #92: `account_id_for` ran inside `redeem`'s transaction.

        It performs a query of its own, so it asked the pool for a second
        connection while the first was still held. A pool of one is the
        smallest case that shows it, and it is a real configuration —
        `CEDAR_PRESS_DB_POOL=1`. At the default of eight, eight simultaneous
        activations hold all eight and each waits for a ninth.
        """
        was = os.environ.get("CEDAR_PRESS_DB_POOL")
        os.environ["CEDAR_PRESS_DB_POOL"] = "1"
        db.reset_for_tests()
        try:
            subscribers.issue_code("TBN9-ONE-CONN", "solo@example.org", "press")
            made = subscribers.redeem("TBN9-ONE-CONN", "correct-horse-battery")
            self.assertIsNotNone(made)
            self.assertEqual(made.email, "solo@example.org")
        finally:
            if was is None:
                os.environ.pop("CEDAR_PRESS_DB_POOL", None)
            else:
                os.environ["CEDAR_PRESS_DB_POOL"] = was
            db.reset_for_tests()


class TestExpiryIsFailClosed(unittest.TestCase):
    """Codex, PR #92: a typo in `CEDAR_PRESS_CODES` became a 500.

    `codes.py` has always promised the opposite, in as many words: "An
    unparseable date is a register we cannot trust. Treated as expired rather
    than as unlimited." When the lookup moved into `subscribers`, the parse
    became a bare `date.fromisoformat`, so an operator's typo stopped
    refusing the code and started telling the reader the service was broken.
    """

    def setUp(self) -> None:
        self._was = os.environ.get("CEDAR_PRESS_CODES")
        os.environ.pop("DATABASE_URL", None)
        db.reset_for_tests()
        subscribers.forget_activated_for_tests()
        os.environ["CEDAR_PRESS_CODES"] = json.dumps(
            {
                "TBN4-BAD0-DATE": {"email": "typo@example.org", "tier": "press", "expires": "soon"},
                "TBN4-GOOD-DATE": {
                    "email": "fine@example.org", "tier": "press", "expires": "2999-01-01"
                },
            }
        )

    def tearDown(self) -> None:
        if self._was is None:
            os.environ.pop("CEDAR_PRESS_CODES", None)
        else:
            os.environ["CEDAR_PRESS_CODES"] = self._was

    def test_an_unparseable_expiry_is_expired_and_not_an_error(self) -> None:
        found = subscribers.find_code("TBN4-BAD0-DATE")
        self.assertIsNotNone(found)
        self.assertTrue(found.has_expired(dt.date.today()))
        # And through the route's own gate, which is where the 500 surfaced.
        issued, error = codes.check("TBN4-BAD0-DATE", "typo@example.org")
        self.assertEqual(error, codes.CODE_EXPIRED)
        self.assertIsNone(issued)

    def test_a_good_expiry_still_works(self) -> None:
        issued, error = codes.check("TBN4-GOOD-DATE", "fine@example.org")
        self.assertIsNone(error)
        self.assertEqual(issued.tier, "press")


class TestMigrationsTravelWithThePackage(unittest.TestCase):
    """Codex, PR #92: the SQL files were a sibling of the package, not in it.

    Hatch's wheel target ships `cedar_press/` and nothing else, so an
    editable install found the migrations and a real one found nothing.
    `migrate()` then reported nothing to apply and `open_store()` went on to
    seed a table that had never been created. There is no test that can build
    a wheel cheaply, so what is asserted is the property that made the wheel
    wrong: the directory has to be INSIDE the package.
    """

    def test_the_directory_is_inside_the_package(self) -> None:
        package = pathlib.Path(db.__file__).resolve().parent
        self.assertEqual(db._MIGRATIONS.parent, package)
        self.assertTrue(sorted(db._MIGRATIONS.glob("*.sql")), "no migrations found")


@unittest.skipUnless(PG, "set CEDAR_PRESS_TEST_DATABASE_URL")
class TestAStandaloneDatabase(unittest.TestCase):
    """Codex, PR #92: the migration required teim-app's `users` table.

    `link_platform_account` asks `to_regclass` and treats a missing `users`
    as a supported deployment — Cedar Press pointed at a database of its own.
    Migration 001 contradicted that by declaring the foreign key inline, so
    that deployment failed at `relation "users" does not exist`, and since the
    service migrates when it opens its store, it did not start at all.
    """

    @staticmethod
    def _ddl(statement: str) -> None:
        """CREATE/DROP DATABASE, which cannot run inside a transaction.

        Straight through psycopg rather than the service's pool, because the
        pool hands out connections that have already begun one.
        """
        import psycopg

        with psycopg.connect(PG, autocommit=True) as conn:
            conn.execute(statement)

    def setUp(self) -> None:
        self._was = os.environ.get("DATABASE_URL")
        self.name = f"cedar_press_standalone_{os.getpid()}"
        db.reset_for_tests()
        self._ddl(f'DROP DATABASE IF EXISTS "{self.name}"')
        self._ddl(f'CREATE DATABASE "{self.name}"')

    def tearDown(self) -> None:
        db.reset_for_tests()
        self._ddl(f'DROP DATABASE IF EXISTS "{self.name}"')
        if self._was is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self._was

    def test_it_migrates_and_runs_without_the_platform_users_table(self) -> None:
        os.environ["DATABASE_URL"] = PG.rsplit("/", 1)[0] + "/" + self.name
        db.reset_for_tests()
        self.assertIsNone(db.one("SELECT to_regclass('public.users') AS t")["t"])
        applied = db.migrate()
        self.assertIn("001_cedar_press_subscribers.sql", applied)
        # The table is there and carries no foreign key it cannot satisfy.
        self.assertIsNotNone(db.one("SELECT to_regclass('cedar_press_subscribers') AS t")["t"])
        keys = db.query(
            "SELECT conname FROM pg_constraint WHERE conrelid ="
            " 'cedar_press_subscribers'::regclass AND contype = 'f'"
        )
        self.assertEqual(keys, [])
        # And the service works: a code, an activation, a sign-in.
        subscribers.issue_code("TBN5-SOLO-0001", "alone@example.org", "press_pro")
        made = subscribers.redeem("TBN5-SOLO-0001", "correct-horse-battery")
        self.assertEqual(made.tier, "press_pro")
        self.assertIsNotNone(subscribers.authenticate("alone@example.org", "correct-horse-battery"))
        # Binding is the no-op it always promised to be, not a crash.
        self.assertFalse(subscribers.link_platform_account("alone@example.org"))


if __name__ == "__main__":
    unittest.main()
