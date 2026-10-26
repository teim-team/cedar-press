"""Real PostgreSQL migration, compatibility and identity boundary tests."""

from __future__ import annotations

import os
import unittest
import uuid
from unittest import mock
from urllib.parse import urlsplit, urlunsplit

from cedar_press import accounts, db, subscribers
from cedar_press.accounts.services import sessions as session

PG = os.environ.get("CEDAR_PRESS_TEST_DATABASE_URL", "")
FOUNDATION = "004_account_foundation.sql"


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
        self.assertIn(FOUNDATION, db.migrate())
        self.assertEqual(db.migrate(), [])
        self.assertIsNotNone(session._decode(cookie))
        current = db.query("SELECT * FROM cedar_press_subscribers ORDER BY email")
        for before, after in zip(original, current, strict=True):
            for key, value in before.items():
                self.assertEqual(value, after[key], key)
            self.assertEqual(after["sessions_revoked_at"], before["updated_at"])
            self.assertIsNotNone(subscribers.authenticate(before["email"], "existing-password"))
        # Legacy points grouping is preserved as data, not promoted into group accounts.
        for relation in ("cedar_press_users", "cedar_press_billing_accounts",
                         "cedar_press_membership_grants",
                         "cedar_press_account_members"):
            self.assertIsNone(db.one("SELECT to_regclass(%s) AS t", (relation,))["t"])
        self.assertIsNone(db.one("SELECT to_regclass('cedar_press_entitlements') AS t")["t"])
        self.assertEqual(
            [r["tier"] for r in db.query(
                "SELECT tier FROM cedar_press_access_grants ORDER BY tier"
            )],
            ["press", "press_pro"],
        )
        self.assertEqual(db.query(
            "SELECT * FROM cedar_press_subscribers WHERE email_verified_at IS NOT NULL"
        ), [])

    def test_unpaid_identity_does_not_authenticate_or_gain_access(self):
        db.migrate()
        user = accounts.create_user(" Unpaid@Example.org ")
        self.assertEqual(user["email"], "unpaid@example.org")
        self.assertIsNone(user["email_verified_at"])
        self.assertEqual(subscribers.find(user["email"]).tier, "free")
        self.assertIsNone(subscribers.authenticate(user["email"], "anything"))
        self.assertEqual(db.query(
            "SELECT * FROM cedar_press_access_grants WHERE user_id = %s", (user["id"],)
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
        self.assertIsNone(db.one("SELECT to_regclass('cedar_press_login_identities') AS t")["t"])
        self.assertIsNone(db.one(
            "SELECT filename FROM cedar_press_migrations"
            " WHERE filename = '004_account_foundation.sql'"
        ))
        # Correct the injected violation, then prove the same migration succeeds.
        db.execute("DELETE FROM cedar_press_subscribers WHERE email = 'ONE@example.org'")
        self.assertIn(FOUNDATION, db.migrate())

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
            "SELECT * FROM cedar_press_access_grants WHERE user_id = %s AND revoked_at IS NULL",
            (row["id"],)
        )
        self.assertEqual(grant["tier"], "press_pro")
        with self.assertRaisesRegex(self.psycopg.errors.RaiseException,
                                    "account_identity_immutable"):
            db.execute(
                "UPDATE cedar_press_subscribers SET id = gen_random_uuid()"
                " WHERE email = 'new@example.org'"
            )
        # A failed legacy writer rolls back the identity created by its trigger too.
        with self.assertRaises(self.psycopg.errors.CheckViolation):
            db.execute(
                "INSERT INTO cedar_press_subscribers(email, account_id, tier)"
                " VALUES ('rollback@example.org', 'rollback', 'invalid')"
            )
        self.assertIsNone(db.one(
            "SELECT id FROM cedar_press_subscribers WHERE email = 'rollback@example.org'"
        ))
        db.execute("UPDATE cedar_press_subscribers SET tier = NULL WHERE email = 'new@example.org'")
        self.assertIsNotNone(db.one(
            "SELECT revoked_at FROM cedar_press_access_grants WHERE user_id = %s"
            " ORDER BY starts_at DESC LIMIT 1",
            (row["id"],),
        )["revoked_at"])

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
        users = db.query("SELECT id FROM cedar_press_subscribers ORDER BY email")
        db.execute(
            "INSERT INTO cedar_press_login_identities(user_id, provider, subject)"
            " VALUES (%s, 'google', 'stable-provider-subject')", (users[0]["id"],)
        )
        with self.assertRaises(self.psycopg.errors.UniqueViolation):
            db.execute(
                "INSERT INTO cedar_press_login_identities(user_id, provider, subject)"
                " VALUES (%s, 'google', 'stable-provider-subject')", (users[1]["id"],)
            )

    def test_single_account_identity_and_existing_account_activation_refusal(self):
        db.migrate()
        user = accounts.create_user("unverified@example.org")
        with self.assertRaises(self.psycopg.errors.UniqueViolation) as caught:
            db.execute(
                "INSERT INTO cedar_press_subscribers(id, email, account_id, tier)"
                " VALUES (%s, 'another@example.org', 'another', NULL)", (user["id"],)
            )
        self.assertEqual(caught.exception.diag.constraint_name, "cedar_press_subscribers_pkey")
        subscribers.issue_code("EXISTING-IDENTITY-123", user["email"], "press")
        with self.assertRaises(subscribers.AlreadySubscribed):
            subscribers.redeem("EXISTING-IDENTITY-123", "must-not-reset")
        self.assertFalse(subscribers.find_code("EXISTING-IDENTITY-123").spent)
        self.assertIsNone(subscribers.find(user["email"]).password_hash)
        self.assertEqual(subscribers.find(user["email"]).tier, "free")

    def test_google_identity_cannot_follow_an_unverified_legacy_email_edit(self):
        db.migrate()
        identity = db.one(
            "SELECT id FROM cedar_press_subscribers WHERE email = 'one@example.org'"
        )["id"]
        db.execute(
            "INSERT INTO cedar_press_login_identities(user_id, provider, subject)"
            " VALUES (%s, 'google', 'alice-subject')", (identity,)
        )
        with self.assertRaisesRegex(self.psycopg.errors.RaiseException,
                                    "account_email_change_requires_verified_flow"):
            db.execute("UPDATE cedar_press_subscribers SET email = 'bob@example.org'"
                       " WHERE email = 'one@example.org'")
        self.assertEqual(db.one("SELECT email FROM cedar_press_subscribers WHERE id = %s",
                                (identity,))["email"], "one@example.org")
        self.assertIsNone(subscribers.find("bob@example.org"))

    def test_legacy_changes_preserve_grant_history_and_complimentary_access(self):
        db.migrate()
        subscribers.create("seat@example.org", "existing-password", "press")
        identity = db.one(
            "SELECT id FROM cedar_press_subscribers WHERE email = 'seat@example.org'"
        )["id"]
        old_grant = db.one("SELECT * FROM cedar_press_access_grants WHERE user_id = %s",
                           (identity,))
        complimentary = db.one(
            "INSERT INTO cedar_press_access_grants(user_id, tier, source)"
            " VALUES (%s, 'press_pro', 'complimentary') RETURNING id", (identity,)
        )
        db.execute("UPDATE cedar_press_subscribers SET account_id = 'new-account',"
                   " tier = 'press_pro'"
                   " WHERE email = 'seat@example.org'")
        grants = db.query("SELECT * FROM cedar_press_access_grants WHERE user_id = %s"
                          " AND source = 'legacy'"
                          " ORDER BY starts_at", (identity,))
        self.assertEqual(len(grants), 2)
        self.assertEqual(grants[0]["id"], old_grant["id"])
        self.assertEqual(grants[0]["starts_at"], old_grant["starts_at"])
        self.assertIsNotNone(grants[0]["revoked_at"])
        self.assertIsNone(grants[1]["revoked_at"])
        self.assertGreater(grants[1]["starts_at"], grants[0]["starts_at"])
        # An unchanged legacy upsert must not manufacture another grant.
        subscribers.create("seat@example.org", "existing-password", "press_pro")
        self.assertEqual(db.one("SELECT count(*) AS n FROM cedar_press_access_grants"
                                " WHERE user_id = %s AND source = 'legacy'", (identity,))["n"], 2)
        db.execute("UPDATE cedar_press_subscribers SET tier = NULL"
                   " WHERE email = 'seat@example.org'")
        self.assertEqual(db.query("SELECT id FROM cedar_press_access_grants"
                                  " WHERE user_id = %s AND source = 'legacy'"
                                  " AND revoked_at IS NULL", (identity,)), [])
        self.assertIsNone(db.one("SELECT revoked_at FROM cedar_press_access_grants WHERE id = %s",
                                 (complimentary["id"],))["revoked_at"])

    def test_password_writes_revoke_sessions_and_missing_accounts_are_rejected(self):
        db.migrate()
        cookie = session._encode(session.Session("one@example.org", "press"))
        before = subscribers.find("one@example.org").session_revision
        db.execute("UPDATE cedar_press_subscribers SET password_hash = %s"
                   " WHERE email = 'one@example.org'", (subscribers.hash_password("changed"),))
        self.assertNotEqual(subscribers.find("one@example.org").session_revision, before)
        self.assertIsNone(session._decode(cookie))
        with self.assertRaises(self.psycopg.errors.NotNullViolation):
            db.execute("UPDATE cedar_press_subscribers SET account_id = NULL"
                       " WHERE email = 'one@example.org'")
        with self.assertRaises(self.psycopg.errors.CheckViolation) as caught:
            db.execute("UPDATE cedar_press_subscribers SET account_id = '  '"
                       " WHERE email = 'one@example.org'")
        self.assertEqual(caught.exception.diag.constraint_name,
                         "cedar_press_subscriber_account_required")

    def test_paid_access_cannot_be_duplicated_in_explicit_grants(self):
        db.migrate()
        grant = db.one("SELECT * FROM cedar_press_access_grants LIMIT 1")
        with self.assertRaises(self.psycopg.errors.CheckViolation) as caught:
            db.execute(
                "INSERT INTO cedar_press_access_grants(user_id, tier, source)"
                " VALUES (%s, 'press', 'stripe')", (grant["user_id"],)
            )
        self.assertEqual(caught.exception.diag.constraint_name, "cedar_press_access_grant_source")

    def test_stripe_customer_belongs_to_one_individual_user(self):
        db.migrate()
        first = accounts.create_user("first@example.org")
        second = accounts.create_user("second@example.org")
        db.execute("UPDATE cedar_press_subscribers SET stripe_customer_id = 'cus_test_individual'"
                   " WHERE id = %s", (first["id"],))
        with self.assertRaises(self.psycopg.errors.UniqueViolation):
            db.execute("UPDATE cedar_press_subscribers"
                       " SET stripe_customer_id = 'cus_test_individual'"
                       " WHERE id = %s", (second["id"],))

    def test_grant_history_prevents_accidental_account_deletion(self):
        db.migrate()
        with self.assertRaises(self.psycopg.errors.ForeignKeyViolation):
            db.execute("DELETE FROM cedar_press_subscribers WHERE email = 'one@example.org'")
        self.assertIsNotNone(subscribers.find("one@example.org"))

    def test_disabling_then_restoring_legacy_access_does_not_revive_old_cookies(self):
        db.migrate()
        cookie = session._encode(session.Session("one@example.org", "press"))
        db.execute("UPDATE cedar_press_subscribers SET tier = NULL WHERE email = 'one@example.org'")
        self.assertIsNone(session._decode(cookie))
        db.execute("UPDATE cedar_press_subscribers SET tier = 'press'"
                   " WHERE email = 'one@example.org'")
        self.assertIsNone(session._decode(cookie))
