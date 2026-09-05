#!/usr/bin/env python3
"""Cedar Press - the ONE place a DuckDB connection is opened.

WHY THIS EXISTS
---------------
Twice in two days a Cedar script took the owner's desktop down, and both times
the mechanism was identical:

    2026-09-03 02:30-02:39  python.exe committed 55.5 GB -> dwm.exe died ->
                            bugcheck 0xD1, 3.18 GB MEMORY.DMP
    2026-09-04 16:05-16:19  python.exe committed 57.2 GB -> dwm.exe crashed
                            SEVEN times (this is the black screen the owner
                            saw) -> apps failed to launch with 0xc000012d
                            (STATUS_COMMITMENT_LIMIT), Task Manager itself
                            could not start -> forced power off

The machine has 15.7 GB of RAM and a 16 GB pagefile, so the commit limit is
31.4 GB. Nothing in DuckDB was going to stop at 31.4 GB, because **not one of
the 23 `duckdb.connect()` sites in code/ set `memory_limit`**. An unbounded
connection plus `read_csv(..., all_varchar=true, sample_size=-1)` over the
delivered CSVs - `sample_size=-1` reads whole files to infer types and
`all_varchar` materialises every column as a string - is a straight line to
committing more than the machine has.

THE FIX IS A LIMIT, NOT A SMALLER QUERY. With `memory_limit` and a
`temp_directory` set, DuckDB SPILLS TO DISK instead of committing past the
limit: the job gets slower and it finishes. Without them it is the desktop
that fails, not the query.

This module exists so the guard is not something 23 call sites have to
remember, and so the 24th - written next week by someone who never read this -
inherits it for free.

Override per-run without editing code:

    CEDAR_DUCKDB_MEMORY_LIMIT=10GB   CEDAR_DUCKDB_THREADS=8   py -3 code/...
"""
from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: Well under the 31.4 GB commit limit, and low enough that several scripts can
#: run at once - which is exactly what was happening on 2026-09-04, when a
#: 1170 scan was still climbing while another session ran 1179.
MEMORY_LIMIT = os.environ.get("CEDAR_DUCKDB_MEMORY_LIMIT", "6GB")

#: 1170 asked for 8. Threads do not cause the overrun on their own, but each
#: one carries buffers, so 8 multiplies whatever a single thread holds.
THREADS = os.environ.get("CEDAR_DUCKDB_THREADS", "4")

#: Spill lives on C: (NVMe). D: is a 7200rpm platter used for cold archive;
#: spilling a hash join onto it would be correct and unusably slow.
SPILL_DIR = os.environ.get("CEDAR_DUCKDB_SPILL", str(ROOT / ".duckdb_spill"))

#: Cap the spill too, so a runaway query fails as a query instead of filling
#: the disk that the pagefile needs. C: had 41.9 GB free on 2026-09-04.
MAX_SPILL = os.environ.get("CEDAR_DUCKDB_MAX_SPILL", "20GB")


def connect(database: str = ":memory:", *, memory_limit: str | None = None,
            threads: str | int | None = None, spill: bool = True):
    """Open a DuckDB connection that cannot exhaust the machine.

    Drop-in for `duckdb.connect()`. `memory_limit` is the whole point of
    this wrapper, so a failure to install it is fatal: a malformed
    `CEDAR_DUCKDB_MEMORY_LIMIT` must not hand back the unbounded connection
    the wrapper exists to prevent (Codex, PR #56). The spill settings stay
    best-effort, because a DuckDB old enough to lack
    `max_temp_directory_size` should still get the cap - a partial guard
    beats an import error in a pipeline the owner runs unattended.
    """
    import duckdb

    con = duckdb.connect(database)
    cap = memory_limit or MEMORY_LIMIT
    try:
        con.execute("SET memory_limit=?", [cap])
    except Exception as exc:
        con.close()
        raise RuntimeError(
            "cedar_duck: could not set memory_limit=%r (%s); refusing to "
            "hand back an unbounded connection. Fix CEDAR_DUCKDB_MEMORY_LIMIT."
            % (cap, exc)) from exc
    settings = [("threads", str(threads or THREADS))]
    if spill:
        try:
            Path(SPILL_DIR).mkdir(parents=True, exist_ok=True)
            settings.append(("temp_directory", SPILL_DIR))
            settings.append(("max_temp_directory_size", MAX_SPILL))
        except OSError:
            pass                      # no spill dir: the limit still applies
    for key, val in settings:
        try:
            con.execute("SET %s=?" % key, [val])
        except Exception:
            pass
    return con


def _bytes(limit: str) -> int:
    """`4GB` / `512MiB` / `1024` -> bytes, the way DuckDB reads them:
    `GB` is decimal (10^9), `GiB` binary (2^30). DuckDB reports back in
    binary units to one decimal, so callers compare with a tolerance."""
    m = re.fullmatch(r"\s*([0-9.]+)\s*(([KMGT])(I?)B?)?\s*", limit, re.I)
    if not m:
        raise ValueError(limit)
    n = float(m.group(1))
    if not m.group(2):
        return int(n)
    power = "KMGT".index(m.group(3).upper()) + 1
    base = 1024 if m.group(4) else 1000
    return int(n * base ** power)


def selftest() -> int:
    """Prove the REQUESTED limit is in force, not DuckDB's default, and
    that a limit DuckDB rejects refuses the connection instead of returning
    an unbounded one."""
    con = connect()
    got = dict(con.execute(
        "SELECT name, value FROM duckdb_settings() "
        "WHERE name IN ('memory_limit','threads','temp_directory')").fetchall())
    print("memory_limit   : %s  (requested %s)" % (got.get("memory_limit"), MEMORY_LIMIT))
    print("threads        : %s" % got.get("threads"))
    print("temp_directory : %s" % got.get("temp_directory"))
    want = _bytes(MEMORY_LIMIT)
    have = _bytes(got.get("memory_limit") or "0")
    # DuckDB reports the cap in its own units and rounding (`3.7 GiB` for
    # `4GB`); within a few percent of the request is the request.
    ok = have > 0 and abs(have - want) <= max(want * 0.05, 1 << 20)
    print("requested cap in force : %s" % ("yes" if ok else "NO"))
    con.close()
    # positive control: an unparseable limit must raise, never connect
    try:
        connect(memory_limit="not-a-size")
    except RuntimeError as exc:
        refused = True
        print("bad limit refused      : yes (%s)" % str(exc).split(";")[0])
    else:
        refused = False
        print("bad limit refused      : NO - unbounded connection returned")
    ok = ok and refused
    print("PASS" if ok else "FAIL - memory limit not enforced as requested")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(selftest())
