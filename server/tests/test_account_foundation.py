"""Real PostgreSQL migration, compatibility and identity boundary tests."""

from __future__ import annotations

import os
import unittest
import uuid
from unittest import mock
from urllib.parse import urlsplit, urlunsplit

from cedar_press import accounts, db, session, subscribers

PG = os.environ.get("CEDAR_PRESS_TEST_DATABASE_URL", "")


@unittest.skipUnless(PG, "set CEDAR_PRESS_TEST_DATABASE_URL")
class TestAccountFoundation(unittest.TestCase):
    def setUp(self):
        import psycopg
        from psycopg import sql

        self.psycopg = psycopg
        self.name = "press_accounts_" + uuid.uuid4().hex
        with psycopg.connect(PG, autocommit=True) as connection:
            connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(self.name)))
        self.addCleanup(self.drop_database)
        parsed = urlsplit(PG)
        url = urlunsplit(parsed._replace(path="/" + self.name))
        self.env = mock.patch.dict(os.environ, {"DATABASE_URL": url})
        self.env.start()
        self.addCleanup(self.env.stop)
        db.reset_for_tests()
        self.addCleanup(db.reset_for_tests)
        # Reproduce the exact pre-foundation schema and ledger.
        with db.pool().connection() as connection:
            connection.execute(
                "CREATE TABLE cedar_press_migrations"
                " (filename TEXT PRIMARY KEY, applied_at TIMESTAMPTZ DEFAULT now())"
            )
            for path in sorted(db._MIGRATIONS.glob("00[12]_*.sql")):
                connection.execute(path.read_text())
                connection.execute(
                    "INSERT INTO cedar_press_migrations(filename) VALUES (%s)", (path.name,)
                )
        self.password = subscribers.hash_password("existing-password")
        for email, tier in (("one@example.org", "press"), ("two@example.org", "press_pro")):
            db.execute(
                "INSERT INTO cedar_press_subscribers(email, account_id, tier, password_hash)"
                " VALUES (%s, 'shared-organization', %s, %s)",
                (email, tier, self.password),
            )

    def drop_database(self):
        from psycopg import sql

        with self.psycopg.connect(PG, autocommit=True) as connection:
            connection.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(self.name)))

    def test_migration_preserves_credentials_grouping_and_cookie_revision(self):
        original = db.query("SELECT * FROM cedar_press_subscribers ORDER BY email")
        old = original[0]
        legacy = subscribers.Subscriber(
            old["email"], old["tier"], old["account_id"], old["password_hash"],
            subscribers._session_revision(old["updated_at"]),
        )
        cookie = session._encode(session.Session(
            legacy.email, legacy.tier, session._revision(legacy)
        ))
        self.assertEqual(db.migrate(), ["003_account_foundation.sql"])
        self.assertEqual(db.migrate(), [])
        self.assertIsNotNone(session._decode(cookie))
        current = db.query("SELECT * FROM cedar_press_subscribers ORDER BY email")
        for before, after in zip(original, current, strict=True):
            for key, value in before.items():
                self.assertEqual(value, after[key], key)
            self.assertEqual(after["sessions_revoked_at"], before["updated_at"])
            self.assertIsNotNone(after["identity_id"])
            self.assertIsNotNone(subscribers.authenticate(before["email"], "existing-password"))
        self.assertEqual(db.one("SELECT count(*) AS n FROM cedar_press_billing_accounts")["n"], 1)
        self.assertEqual(db.one("SELECT count(*) AS n FROM cedar_press_account_members")["n"], 2)
        self.assertEqual(
            [r["tier"] for r in db.query(
                "SELECT tier FROM cedar_press_entitlements ORDER BY tier"
            )],
            ["press", "press_pro"],
        )
        self.assertEqual(db.query(
            "SELECT * FROM cedar_press_users WHERE email_verified_at IS NOT NULL"
        ), [])

    def test_unpaid_identity_does_not_authenticate_or_gain_access(self):
        db.migrate()
        user = accounts.create_user(" Unpaid@Example.org ")
        self.assertEqual(user["email"], "unpaid@example.org")
        self.assertIsNone(user["email_verified_at"])
        self.assertIsNone(subscribers.find(user["email"]))
        self.assertEqual(db.query(
            "SELECT * FROM cedar_press_entitlements WHERE user_id = %s", (user["id"],)
        ), [])
        with self.assertRaises(self.psycopg.errors.UniqueViolation):
            accounts.create_user("UNPAID@example.org")
        with self.assertRaises(ValueError):
            accounts.create_user("")

    def test_ambiguous_existing_email_collision_rolls_back_migration(self):
        db.execute(
            "INSERT INTO cedar_press_subscribers(email, account_id, tier)"
            " VALUES ('ONE@example.org', 'different-seat', 'press')"
        )
        with self.assertRaises(self.psycopg.errors.UniqueViolation) as caught:
            db.migrate()
        self.assertEqual(caught.exception.diag.constraint_name,
                         "cedar_press_subscriber_normalized_email")
        self.assertIsNone(db.one("SELECT to_regclass('cedar_press_users') AS t")["t"])
        self.assertIsNone(db.one(
            "SELECT filename FROM cedar_press_migrations"
            " WHERE filename = '003_account_foundation.sql'"
        ))
        # Correct the injected violation, then prove the same migration succeeds.
        db.execute("DELETE FROM cedar_press_subscribers WHERE email = 'ONE@example.org'")
        self.assertEqual(db.migrate(), ["003_account_foundation.sql"])

    def test_legacy_activation_bridge_is_atomic_and_retains_identity_on_update(self):
        db.migrate()
        subscribers.issue_code("LOCAL-TEST-1234", "new@example.org", "press")
        subscribers.redeem("LOCAL-TEST-1234", "activation-password")
        row = db.one("SELECT * FROM cedar_press_subscribers WHERE email = 'new@example.org'")
        db.execute(
            "UPDATE cedar_press_subscribers SET account_id = 'another', tier = 'press_pro'"
            " WHERE email = 'new@example.org'"
        )
        grant = db.one(
            "SELECT * FROM cedar_press_entitlements WHERE user_id = %s", (row["identity_id"],)
        )
        self.assertEqual(grant["tier"], "press_pro")
        self.assertEqual(db.one(
            "SELECT count(*) AS n FROM cedar_press_account_members WHERE user_id = %s",
            (row["identity_id"],),
        )["n"], 1)
        with self.assertRaisesRegex(self.psycopg.errors.RaiseException,
                                    "legacy_identity_rebinding_forbidden"):
            db.execute(
                "UPDATE cedar_press_subscribers SET identity_id = gen_random_uuid()"
                " WHERE email = 'new@example.org'"
            )
        # A failed legacy writer rolls back the identity created by its trigger too.
        with self.assertRaises(self.psycopg.errors.CheckViolation):
            db.execute(
                "INSERT INTO cedar_press_subscribers(email, account_id, tier)"
                " VALUES ('rollback@example.org', 'rollback', 'invalid')"
            )
        self.assertIsNone(db.one(
            "SELECT id FROM cedar_press_users WHERE email = 'rollback@example.org'"
        ))
        db.execute("DELETE FROM cedar_press_subscribers WHERE email = 'new@example.org'")
        self.assertIsNotNone(db.one(
            "SELECT revoked_at FROM cedar_press_entitlements WHERE user_id = %s",
            (row["identity_id"],),
        )["revoked_at"])
        self.assertEqual(db.query(
            "SELECT * FROM cedar_press_account_members WHERE user_id = %s", (row["identity_id"],)
        ), [])

    def test_billing_updates_keep_sessions_and_explicit_logout_revokes(self):
        db.migrate()
        cookie = session._encode(session.Session("one@example.org", "press"))
        db.execute(
            "UPDATE cedar_press_subscribers SET updated_at = now(), tier = 'press_pro'"
            " WHERE email = 'one@example.org'"
        )
        self.assertEqual(session._decode(cookie).tier, "press_pro")
        subscribers.revoke_sessions("one@example.org")
        self.assertIsNone(session._decode(cookie))

    def test_google_subject_cannot_belong_to_two_users(self):
        db.migrate()
        users = db.query("SELECT id FROM cedar_press_users ORDER BY email")
        db.execute(
            "INSERT INTO cedar_press_login_identities(user_id, provider, subject)"
            " VALUES (%s, 'google', 'stable-provider-subject')", (users[0]["id"],)
        )
        with self.assertRaises(self.psycopg.errors.UniqueViolation):
            db.execute(
                "INSERT INTO cedar_press_login_identities(user_id, provider, subject)"
                " VALUES (%s, 'google', 'stable-provider-subject')", (users[1]["id"],)
            )
