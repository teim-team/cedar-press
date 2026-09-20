"""The database, when there is one.

WHAT THIS EXISTS TO END.
Cedar Press kept its subscribers in an environment variable, its activation
codes in a second one, its newly activated accounts in a process-local dict
that its own comment called "the one behaviour here that must not survive
into production", and its points ledger in a SQLite file that defaulted to
`:memory:` — so unless a deployment happened to set `CEDAR_PRESS_DB`, every
point a subscriber had earned was discarded on restart. For a ledger whose
whole design is append-only so that any balance can be explained, a default
that forgets is the one thing it cannot be.

CONFIGURED OR NOT, AND NOTHING IN BETWEEN.
`DATABASE_URL` is the switch, and it is the same variable teim-app reads, so
one deployment configures both services by setting it once. Set: every store
in this service reads and writes Postgres. Unset: the previous behaviour
exactly — environment accounts, in-memory activation, SQLite points — which
is what the preview deployment and the test suite run on.

There is deliberately no third mode. A partly-configured service that keeps
subscribers in Postgres and points in memory would be the worst of both, and
the failure would only show up as a subscriber whose balance did not match
their ledger.

WHY psycopg AND A POOL.
`psycopg_pool` hands out connections rather than opening one per request:
FastAPI serves this from a thread pool, and Postgres charges about 10ms and
a backend process for each connect. The pool is opened lazily on first use
so importing this module never touches the network — the test suite imports
the whole package to check a helper.
"""

from __future__ import annotations

import contextlib
import os
import threading
from pathlib import Path
from typing import Any

#: INSIDE THE PACKAGE, NOT BESIDE IT. This pointed at `server/migrations/`,
#: a sibling of the package, and Hatch's wheel target ships `cedar_press/`
#: only — so an editable install found the files and a real one found an
#: empty directory. `migrate()` then reported nothing to apply, `open_store()`
#: went straight on to seed a `cedar_press_priorities` table that had never
#: been created, and the service failed to start with a missing-relation
#: error that said nothing about packaging.
_MIGRATIONS = Path(__file__).resolve().parent / "migrations"

_pool: Any = None
_lock = threading.Lock()


def url() -> str:
    """The database, or "" when this deployment has none."""
    return os.environ.get("DATABASE_URL", "").strip()


def configured() -> bool:
    """Whether to use Postgres at all. The one switch; see the module docstring."""
    return bool(url())


def reset_for_tests() -> None:
    """Drop the pool so the next call builds one against the current URL."""
    global _pool
    with _lock:
        if _pool is not None:
            # A pool that is already closed, or was never opened, must not
            # fail the reset: this runs in test teardown and an exception
            # there hides the failure the test was actually reporting.
            with contextlib.suppress(Exception):
                _pool.close()
        _pool = None


def pool() -> Any:
    """The connection pool, opened on first use.

    `psycopg` is an optional dependency: a deployment with no `DATABASE_URL`
    never reaches this line, and the preview image does not carry the driver.
    The import is here rather than at module scope so that stays true.
    """
    global _pool
    if _pool is None:
        with _lock:
            if _pool is None:
                from psycopg.rows import dict_row
                from psycopg_pool import ConnectionPool

                _pool = ConnectionPool(
                    url(),
                    min_size=1,
                    max_size=int(os.environ.get("CEDAR_PRESS_DB_POOL", "8")),
                    kwargs={"row_factory": dict_row},
                    open=True,
                )
    return _pool


def query(sql: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
    """Rows, as dicts."""
    with pool().connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params or ())
        return list(cur.fetchall())


def one(sql: str, params: tuple[Any, ...] | None = None) -> dict[str, Any] | None:
    """The first row, or None."""
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: tuple[Any, ...] | None = None) -> int:
    """A write. Returns the row count, which is how a caller learns a
    conditional update did nothing — the difference between "spent this code"
    and "somebody else spent it first"."""
    with pool().connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.rowcount


def migrate() -> list[str]:
    """Apply every migration that has not run, in filename order.

    The applied set is a table rather than a file on disk, because the thing
    that must agree about what has run is the database itself — two app
    instances starting at once would otherwise both believe they were first.
    The advisory lock makes that race a wait instead of a duplicate.
    """
    with pool().connection() as conn, conn.cursor() as cur:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS cedar_press_migrations ("
            " filename TEXT PRIMARY KEY,"
            " applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        conn.commit()
        # One arbitrary but stable key, so two instances booting together
        # take turns rather than both running 001.
        cur.execute("SELECT pg_advisory_lock(%s)", (int.from_bytes(b"cpress", "big") % 2**31,))
        try:
            cur.execute("SELECT filename FROM cedar_press_migrations")
            done = {row["filename"] for row in cur.fetchall()}
            ran: list[str] = []
            for path in sorted(_MIGRATIONS.glob("*.sql")):
                if path.name in done:
                    continue
                cur.execute(path.read_text(encoding="utf-8"))
                cur.execute(
                    "INSERT INTO cedar_press_migrations (filename) VALUES (%s)", (path.name,)
                )
                conn.commit()
                ran.append(path.name)
            return ran
        finally:
            cur.execute(
                "SELECT pg_advisory_unlock(%s)", (int.from_bytes(b"cpress", "big") % 2**31,)
            )
            conn.commit()
