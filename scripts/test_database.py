"""Run the same real-PostgreSQL contracts locally and in CI, refusing skips."""

import os
import unittest


def main() -> int:
    if not os.environ.get("CEDAR_PRESS_TEST_DATABASE_URL", "").strip():
        raise SystemExit("CEDAR_PRESS_TEST_DATABASE_URL is required for database contracts")
    suite = unittest.defaultTestLoader.loadTestsFromNames([
        "tests.test_subscribers",
        "tests.test_account_foundation",
        "tests.test_priorities",
        "tests.test_auth_session_lifecycle",
        "tests.test_release_download",
    ])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.skipped:
        raise SystemExit("Database contract run unexpectedly skipped tests")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
