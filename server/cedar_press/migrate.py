"""Apply the migrations. `python -m cedar_press.migrate`.

The service also does this when it opens its store, so setting `DATABASE_URL`
is the whole of the installation. This exists for the case that stops being
true: a migration that drops or retypes a column an instance still running the
old code is reading. Then the schema change belongs in a deploy step, before
the new code ships, rather than in whichever instance happens to boot first.

Same code, same advisory lock, idempotent either way. What this adds is that
it says what it did.
"""

from __future__ import annotations

import sys

from cedar_press import db


def main() -> int:
    if not db.configured():
        print("DATABASE_URL is not set; nothing to migrate.", file=sys.stderr)
        return 1
    ran = db.migrate()
    if ran:
        print("applied:\n  " + "\n  ".join(ran))
    else:
        print("already up to date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
