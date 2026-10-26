"""Run the same real-PostgreSQL contracts locally and in CI, refusing skips."""

import os
import unittest
import uuid
from urllib.parse import urlsplit, urlunsplit

import psycopg
from psycopg import sql


def main() -> int:
    admin_url = os.environ.get("CEDAR_PRESS_TEST_DATABASE_ADMIN_URL", "").strip()
    if not admin_url:
        raise SystemExit("CEDAR_PRESS_TEST_DATABASE_ADMIN_URL is required for database contracts")
    parsed = urlsplit(admin_url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise SystemExit("CEDAR_PRESS_TEST_DATABASE_ADMIN_URL must be a PostgreSQL URL")
    name = "cedar_press_test_" + uuid.uuid4().hex
    test_url = urlunsplit(parsed._replace(path="/" + name))
    previous = os.environ.get("CEDAR_PRESS_TEST_DATABASE_URL")
    with psycopg.connect(admin_url, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        try:
            os.environ["CEDAR_PRESS_TEST_DATABASE_URL"] = test_url
            # This table belongs to teim-app, not the application migrations.
            # Only the disposable compatibility fixture needs it.
            with psycopg.connect(test_url) as connection:
                connection.execute("""
                    CREATE TABLE users (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        email TEXT NOT NULL UNIQUE,
                        password_hash TEXT NOT NULL,
                        workspace_tier TEXT
                    )
                """)
            from cedar_press import db

            # Apply the real migrations before tests populate their fixtures.
            saved_database = os.environ.get("DATABASE_URL")
            try:
                os.environ["DATABASE_URL"] = test_url
                db.reset_for_tests()
                db.migrate()
            finally:
                db.reset_for_tests()
                if saved_database is None:
                    os.environ.pop("DATABASE_URL", None)
                else:
                    os.environ["DATABASE_URL"] = saved_database
            suite = unittest.defaultTestLoader.loadTestsFromNames([
                "tests.test_subscribers",
                "tests.test_account_foundation",
                "tests.test_billing",
                "tests.test_guest_checkout",
                "tests.test_priorities",
                "tests.test_auth_session_lifecycle",
                "tests.test_release_download",
            ])
            result = unittest.TextTestRunner(verbosity=2).run(suite)
            if result.skipped:
                raise SystemExit("Database contract run unexpectedly skipped tests")
            return 0 if result.wasSuccessful() else 1
        finally:
            # Drop only the unique database this invocation created.
            if previous is None:
                os.environ.pop("CEDAR_PRESS_TEST_DATABASE_URL", None)
            else:
                os.environ["CEDAR_PRESS_TEST_DATABASE_URL"] = previous
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


if __name__ == "__main__":
    raise SystemExit(main())
