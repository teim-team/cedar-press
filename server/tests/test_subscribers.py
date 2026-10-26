"""The subscriber store, on both backends.

Every test here runs twice: once with no `DATABASE_URL`, which is the
preview and the suite's default, and once against a real Postgres when
`CEDAR_PRESS_TEST_DATABASE_URL` names one. The point of the pair is that the
two backends answer the same questions the same way — a seam whose two sides
disagree is worse than no seam, because the disagreement only shows up in
production.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cedar_press import db
from cedar_press.accounts.services import sessions as session
from cedar_press.accounts.services import subscribers

PG = os.environ.get("CEDAR_PRESS_TEST_DATABASE_URL", "").strip()

ACCOUNTS = json.dumps(
    {
        "reader@example.org": {"password": "correct-horse", "tier": "press"},
        "pro@example.org": {"password": "correct-horse", "tier": "press_pro"},
        # Two seats, one subscription, declared.
        "one@bank.example": {
            "password": "correct-horse",
            "tier": "press_pro",
            "account": "acct-bank",
        },
        "two@bank.example": {
            "password": "correct-horse",
            "tier": "press_pro",
            "account": "acct-bank",
        },
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
            db.migrate()
            db.execute(
                "TRUNCATE cedar_press_subscribers, cedar_press_password_resets,"
                " cedar_press_email_changes, cedar_press_reader_profiles,"
                " cedar_press_login_identities, cedar_press_access_grants,"
                " cedar_press_account_setup_links, cedar_press_account_email_deliveries,"
                " cedar_press_checkout_attempts, cedar_press_checkouts,"
                " cedar_press_refunds, cedar_press_payments,"
                " cedar_press_invoices, cedar_press_subscriptions"
            )
            for email, tier in (("reader@example.org", "press"), ("pro@example.org", "press_pro")):
                subscribers.create(email, "correct-horse", tier)
            for seat in ("one@bank.example", "two@bank.example"):
                subscribers.create(seat, "correct-horse", "press_pro")
                db.execute(
                    "UPDATE cedar_press_subscribers SET account_id = %s WHERE email = %s",
                    ("acct-bank", seat),
                )
        else:
            os.environ.pop("DATABASE_URL", None)
            os.environ["CEDAR_PRESS_ACCOUNTS"] = ACCOUNTS

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
        self.assertEqual(subscribers.account_id_for("reader@example.org"), "reader@example.org")

    def test_a_reset_token_sets_the_password_once(self) -> None:
        self.assertIsNone(subscribers.issue_reset("stranger@example.org"))
        token = subscribers.issue_reset("pro@example.org")
        made = subscribers.redeem_reset(token, "a-reset-password")
        self.assertEqual((made.email, made.tier), ("pro@example.org", "press_pro"))
        self.assertIsNotNone(subscribers.authenticate("pro@example.org", "a-reset-password"))
        self.assertIsNone(subscribers.authenticate("pro@example.org", "correct-horse"))
        self.assertIsNone(subscribers.redeem_reset(token, "again-a-password"))
        self.assertIsNone(subscribers.redeem_reset("", "again-a-password"))

    def test_a_reset_keeps_the_seat_on_its_subscription(self) -> None:
        subscribers.redeem_reset(subscribers.issue_reset("one@bank.example"), "a-reset-password")
        self.assertEqual(subscribers.account_id_for("one@bank.example"), "acct-bank")

    def test_a_new_reset_token_replaces_the_older_one(self) -> None:
        older = subscribers.issue_reset("reader@example.org")
        newer = subscribers.issue_reset("Reader@Example.org")
        self.assertIsNone(subscribers.redeem_reset(older, "another-password"))
        self.assertIsNotNone(subscribers.redeem_reset(newer, "a-reset-password"))
        self.assertIsNotNone(subscribers.authenticate("reader@example.org", "a-reset-password"))

    def test_an_expired_reset_token_is_refused(self) -> None:
        with mock.patch.object(subscribers, "RESET_LIFETIME", -subscribers.RESET_LIFETIME):
            token = subscribers.issue_reset("reader@example.org")
        self.assertIsNone(subscribers.redeem_reset(token, "a-reset-password"))
        self.assertIsNotNone(subscribers.authenticate("reader@example.org", "correct-horse"))

    def test_a_display_name_is_kept_and_cleared(self) -> None:
        subscribers.set_display_name("Reader@Example.org", "Ada Reader")
        self.assertEqual(subscribers.profile("reader@example.org")["name"], "Ada Reader")
        subscribers.set_display_name("reader@example.org", None)
        self.assertIsNone(subscribers.profile("reader@example.org")["name"])


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

    def test_the_profile_reads_join_date_and_verification_off_the_row(self) -> None:
        row = db.one(
            "SELECT created_at::date AS joined FROM cedar_press_subscribers WHERE email = %s",
            ("reader@example.org",),
        )
        found = subscribers.profile("reader@example.org")
        self.assertEqual(found["member_since"], row["joined"].isoformat())
        self.assertFalse(found["email_verified"])
        db.execute(
            "UPDATE cedar_press_subscribers SET email_verified_at = now() WHERE email = %s",
            ("reader@example.org",),
        )
        self.assertTrue(subscribers.profile("reader@example.org")["email_verified"])

    def test_an_older_hash_is_upgraded_at_sign_in(self) -> None:
        with mock.patch.object(subscribers, "_ROUNDS", 1_000):
            older = subscribers.hash_password("correct-horse")
        db.execute(
            "UPDATE cedar_press_subscribers SET password_hash = %s WHERE email = %s",
            (older, "reader@example.org"),
        )
        self.assertIsNone(subscribers.authenticate("reader@example.org", "wrong"))
        self.assertIsNotNone(subscribers.authenticate("reader@example.org", "correct-horse"))
        self.assertEqual(subscribers.find("reader@example.org").password_hash, older)
        from fastapi import Response

        signed_in = session.sign_in("reader@example.org", "correct-horse", Response())
        self.assertIsNotNone(signed_in)
        self.assertIsNotNone(session._decode(session._encode(signed_in)))
        current = f"pbkdf2${subscribers._ROUNDS}$"
        self.assertTrue(subscribers.find("reader@example.org").password_hash.startswith(current))
        self.assertIsNotNone(subscribers.authenticate("reader@example.org", "correct-horse"))

    def test_an_email_change_moves_the_account_once_and_signs_it_out(self) -> None:
        cookie = session._encode(session.Session("reader@example.org", "press"))
        db.execute(
            "INSERT INTO cedar_press_reader_profiles (email, work) VALUES (%s, 'research')",
            ("reader@example.org",),
        )
        reset = subscribers.issue_reset("reader@example.org")
        token = subscribers.issue_email_change("reader@example.org", " New@Example.org ")
        self.assertEqual(
            subscribers.redeem_email_change(token), ("reader@example.org", "new@example.org")
        )
        self.assertIsNone(subscribers.find("reader@example.org"))
        self.assertEqual(subscribers.find("new@example.org").tier, "press")
        self.assertIsNotNone(subscribers.authenticate("new@example.org", "correct-horse"))
        self.assertTrue(subscribers.profile("new@example.org")["email_verified"])
        self.assertIsNone(session._decode(cookie))
        self.assertEqual(
            db.one("SELECT work FROM cedar_press_reader_profiles WHERE email = %s",
                   ("new@example.org",))["work"],
            "research",
        )
        self.assertIsNone(subscribers.redeem_reset(reset, "a-reset-password"))
        self.assertIsNone(subscribers.redeem_email_change(token))

    def test_an_email_change_cannot_take_an_address_in_use(self) -> None:
        self.assertIsNone(subscribers.issue_email_change("reader@example.org", "PRO@example.org"))
        token = subscribers.issue_email_change("reader@example.org", "later@example.org")
        subscribers.create("later@example.org", "correct-horse", "press")
        self.assertIsNone(subscribers.redeem_email_change(token))
        self.assertIsNotNone(subscribers.find("reader@example.org"))

    def test_a_billing_failure_rolls_the_email_change_back(self) -> None:
        db.execute(
            "UPDATE cedar_press_subscribers SET stripe_customer_id = 'cus_test' WHERE email = %s",
            ("reader@example.org",),
        )
        token = subscribers.issue_email_change("reader@example.org", "new@example.org")

        def refuse(customer, email):
            raise RuntimeError("billing is down")

        with self.assertRaises(RuntimeError):
            subscribers.redeem_email_change(token, refuse)
        self.assertIsNotNone(subscribers.find("reader@example.org"))
        updated = []
        subscribers.redeem_email_change(token, lambda *call: updated.append(call))
        self.assertEqual(updated, [("cus_test", "new@example.org")])
        self.assertIsNotNone(subscribers.find("new@example.org"))

    def test_an_expired_email_change_is_refused(self) -> None:
        with mock.patch.object(subscribers, "RESET_LIFETIME", -subscribers.RESET_LIFETIME):
            token = subscribers.issue_email_change("reader@example.org", "new@example.org")
        self.assertIsNone(subscribers.redeem_email_change(token))
        self.assertIsNotNone(subscribers.find("reader@example.org"))

    def test_a_subscription_survives_a_restart(self) -> None:
        # The whole reason this module exists. `reset_for_tests` drops the
        # pool, which is as close to a restart as a test gets.
        subscribers.create("new@example.org", "kept", "press")
        db.reset_for_tests()
        self.assertIsNotNone(subscribers.authenticate("new@example.org", "kept"))

    def test_a_subscription_can_be_tied_to_a_platform_account(self) -> None:
        # A subscriber may buy Cedar Press before they have ever opened the
        # platform, so the binding happens later, if at all.
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

    def test_platform_binding_happens_at_sign_in(self) -> None:
        """Sign-in binds an existing platform account before issuing the cookie."""
        from fastapi import Response

        # `users` is teim-app's, so this makes and unmakes exactly its own row
        # rather than truncating a table it does not own.
        db.execute("DELETE FROM users WHERE email = %s", ("pro@example.org",))
        self.assertFalse(subscribers.link_platform_account("pro@example.org"))
        user = db.one(
            "INSERT INTO users (email, password_hash) VALUES (%s, 'x') RETURNING id",
            ("pro@example.org",),
        )
        # The platform account appeared second; the next sign-in finds it.
        old_cookie = session._encode(session.Session("pro@example.org", "press_pro"))
        signed_in = session.sign_in("PRO@Example.org ", "correct-horse", Response())
        self.assertIsNotNone(signed_in)
        self.assertIsNone(session._decode(old_cookie))
        self.assertIsNotNone(session._decode(session._encode(signed_in)))
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
        # And the service works: an account, a sign-in.
        made = subscribers.create("alone@example.org", "correct-horse-battery", "press_pro")
        self.assertEqual(made.tier, "press_pro")
        self.assertIsNotNone(subscribers.authenticate("alone@example.org", "correct-horse-battery"))
        # Binding is the no-op it always promised to be, not a crash.
        self.assertFalse(subscribers.link_platform_account("alone@example.org"))


if __name__ == "__main__":
    unittest.main()
