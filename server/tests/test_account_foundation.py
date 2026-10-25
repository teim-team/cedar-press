"""Real PostgreSQL migration, compatibility and identity boundary tests."""

from __future__ import annotations

import os
import unittest
import uuid
from unittest import mock
from urllib.parse import urlsplit, urlunsplit

from cedar_press import accounts, db, session, subscribers

PG = os.environ.get("CEDAR_PRESS_TEST_DATABASE_URL", "")
FOUNDATION = ["003_account_foundation.sql"]


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
        self.assertEqual(db.migrate(), FOUNDATION)
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
        self.assertEqual(db.query(
            "SELECT source, role FROM cedar_press_membership_grants ORDER BY user_id"
        ), [{"source": "legacy", "role": "member"}] * 2)
        self.assertIsNone(db.one("SELECT to_regclass('cedar_press_entitlements') AS t")["t"])
        self.assertEqual(
            [r["tier"] for r in db.query(
                "SELECT tier FROM cedar_press_access_grants ORDER BY tier"
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
        self.assertIsNone(db.one("SELECT to_regclass('cedar_press_users') AS t")["t"])
        self.assertIsNone(db.one(
            "SELECT filename FROM cedar_press_migrations"
            " WHERE filename = '003_account_foundation.sql'"
        ))
        # Correct the injected violation, then prove the same migration succeeds.
        db.execute("DELETE FROM cedar_press_subscribers WHERE email = 'ONE@example.org'")
        self.assertEqual(db.migrate(), FOUNDATION)

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
            (row["identity_id"],)
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
            "SELECT revoked_at FROM cedar_press_access_grants WHERE user_id = %s"
            " ORDER BY starts_at DESC LIMIT 1",
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

    def test_explicit_identity_insert_and_implicit_email_link_are_refused(self):
        db.migrate()
        identity = db.one("SELECT identity_id FROM cedar_press_subscribers LIMIT 1")["identity_id"]
        with self.assertRaisesRegex(self.psycopg.errors.RaiseException,
                                    "legacy_identity_insert_forbidden"):
            db.execute(
                "INSERT INTO cedar_press_subscribers(email, account_id, tier, identity_id)"
                " VALUES ('another@example.org', 'another', 'press', %s)", (identity,)
            )
        user = accounts.create_user("unverified@example.org")
        with self.assertRaises(self.psycopg.errors.UniqueViolation):
            subscribers.create(user["email"], "must-not-link", "press")
        self.assertIsNone(subscribers.find(user["email"]))
        subscribers.issue_code("EXISTING-IDENTITY-123", user["email"], "press")
        with self.assertRaises(subscribers.AlreadySubscribed):
            subscribers.redeem("EXISTING-IDENTITY-123", "must-not-link")
        self.assertFalse(subscribers.find_code("EXISTING-IDENTITY-123").spent)
        # Even with the bridge disabled, the one-to-one database constraint fires.
        db.execute("ALTER TABLE cedar_press_subscribers DISABLE TRIGGER"
                   " cedar_press_legacy_subscriber_bridge")
        try:
            with self.assertRaises(self.psycopg.errors.UniqueViolation) as caught:
                db.execute(
                    "INSERT INTO cedar_press_subscribers(email, account_id, tier, identity_id)"
                    " VALUES ('another@example.org', 'another', 'press', %s)", (identity,)
                )
            self.assertEqual(caught.exception.diag.constraint_name,
                             "cedar_press_subscriber_identity_unique")
        finally:
            db.execute("ALTER TABLE cedar_press_subscribers ENABLE TRIGGER"
                       " cedar_press_legacy_subscriber_bridge")

    def test_google_identity_cannot_follow_an_unverified_legacy_email_edit(self):
        db.migrate()
        identity = db.one(
            "SELECT identity_id FROM cedar_press_subscribers WHERE email = 'one@example.org'"
        )["identity_id"]
        db.execute(
            "INSERT INTO cedar_press_login_identities(user_id, provider, subject)"
            " VALUES (%s, 'google', 'alice-subject')", (identity,)
        )
        with self.assertRaisesRegex(self.psycopg.errors.RaiseException,
                                    "legacy_email_change_requires_verified_flow"):
            db.execute("UPDATE cedar_press_subscribers SET email = 'bob@example.org'"
                       " WHERE email = 'one@example.org'")
        self.assertEqual(db.one("SELECT email FROM cedar_press_users WHERE id = %s",
                                (identity,))["email"], "one@example.org")
        self.assertIsNone(subscribers.find("bob@example.org"))

    def test_legacy_changes_keep_independent_membership_and_grant_history(self):
        db.migrate()
        subscribers.create("seat@example.org", "existing-password", "press")
        identity = db.one(
            "SELECT identity_id FROM cedar_press_subscribers WHERE email = 'seat@example.org'"
        )["identity_id"]
        old_grant = db.one("SELECT * FROM cedar_press_access_grants WHERE user_id = %s",
                           (identity,))
        db.execute(
            "INSERT INTO cedar_press_membership_grants(account_id, user_id, source, role)"
            " VALUES (%s, %s, 'manual', 'owner')", (old_grant["account_id"], identity)
        )
        db.execute("UPDATE cedar_press_subscribers SET account_id = 'new-account',"
                   " tier = 'press_pro'"
                   " WHERE email = 'seat@example.org'")
        kept = db.one("SELECT role FROM cedar_press_account_members"
                      " WHERE account_id = %s AND user_id = %s",
                      (old_grant["account_id"], identity))
        self.assertEqual(kept["role"], "owner")
        grants = db.query("SELECT * FROM cedar_press_access_grants WHERE user_id = %s"
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
                                " WHERE user_id = %s", (identity,))["n"], 2)
        db.execute(
            "INSERT INTO cedar_press_membership_grants(account_id, user_id, source, role)"
            " VALUES (%s, %s, 'manual', 'owner')", (grants[1]["account_id"], identity)
        )
        db.execute("DELETE FROM cedar_press_subscribers WHERE email = 'seat@example.org'")
        self.assertEqual(db.one("SELECT role FROM cedar_press_account_members"
                                " WHERE account_id = %s AND user_id = %s",
                                (old_grant["account_id"], identity))["role"], "owner")
        self.assertEqual(db.one("SELECT role FROM cedar_press_account_members"
                                " WHERE account_id = %s AND user_id = %s",
                                (grants[1]["account_id"], identity))["role"], "owner")
        self.assertEqual(db.query("SELECT id FROM cedar_press_access_grants"
                                  " WHERE user_id = %s AND revoked_at IS NULL", (identity,)), [])

    def test_password_writes_revoke_sessions_and_missing_accounts_are_rejected(self):
        db.migrate()
        cookie = session._encode(session.Session("one@example.org", "press"))
        before = subscribers.find("one@example.org").session_revision
        db.execute("UPDATE cedar_press_subscribers SET password_hash = %s"
                   " WHERE email = 'one@example.org'", (subscribers.hash_password("changed"),))
        self.assertNotEqual(subscribers.find("one@example.org").session_revision, before)
        self.assertIsNone(session._decode(cookie))
        for account in (None, "  "):
            with self.subTest(account=account), self.assertRaisesRegex(
                self.psycopg.errors.RaiseException, "legacy_account_id_required"
            ):
                db.execute("UPDATE cedar_press_subscribers SET account_id = %s"
                           " WHERE email = 'one@example.org'", (account,))

    def test_paid_access_cannot_be_duplicated_in_explicit_grants(self):
        db.migrate()
        grant = db.one("SELECT * FROM cedar_press_access_grants LIMIT 1")
        with self.assertRaises(self.psycopg.errors.CheckViolation) as caught:
            db.execute(
                "INSERT INTO cedar_press_access_grants(account_id, user_id, tier, source)"
                " VALUES (%s, %s, 'press', 'stripe')", (grant["account_id"], grant["user_id"])
            )
        self.assertEqual(caught.exception.diag.constraint_name, "cedar_press_access_grant_source")
