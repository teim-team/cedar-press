#!/usr/bin/env python3
"""
Cedar Press - 355: push the FA-01 / FA-02 corrections into the SHIPPED
database, `dist/cedar_press.db`.

WHY THIS IS NOT OPTIONAL
------------------------
`dist/cedar_press.db` is 4.4 GB, 138 tables, and it is **the artefact the
Collections pipeline publishes**. Measured 2026-08-26 19:29, before this ran,
by byte-scanning it for the panel's own numbers:

    40279500  x1     the Salt River Pima-Maricopa false total
     5148500  x60    the pre-correction Bristol Bay panel total

A correction that lands in `data/clean` and not in `dist/` ships the defect
anyway. That is FA-01's own shape - the panel was fixed in the disclosures and
not in the table that published - repeated one layer further out.

WHY IT IS SAFE TO PATCH IN PLACE, AND WHY A REBUILD DOES NOT UNDO IT
--------------------------------------------------------------------
`25_build_publication_layer.py` DROPS the whole database (`dbpath.unlink()`)
and rebuilds every table from `data/clean`. Because the CLEAN files are now
correct, a 25 rebuild REPRODUCES this fix rather than reverting it - the
opposite of the class-6 hazard. This script exists only so the shelf is right
NOW, without a 4.4 GB rebuild racing three live agents.

The table names, the licensed-column drops and the SQL-name cleaning are all
IMPORTED from 25 rather than restated. A patcher holding its own copy of the
publisher's mapping is the defect this project keeps paying for.

Reads   data/clean/{the five corrected tables}
Writes  dist/cedar_press.db   (DROP + CREATE + INSERT, per table, one txn)
"""

import importlib.util
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"
DIST = CEDAR / "dist"
DB = DIST / "cedar_press.db"
TODAY = date.today().isoformat()
SCRIPT = "355_patch_dist_database_for_corrections.py"

# The clean files this session corrected. Their DB table names are looked up
# in 25's own registry, never guessed.
CORRECTED = [
    "tribe_year_lobbying_panel.csv",
    "native_entity_lobbying_disclosures.csv",
    "foia_request_index.csv",
    "lobbying_registrant_client_relationships.csv",
    "lobbying_issue_families_filing.csv",
    # Not a correction TO this table - it IS the register. Its notes contract
    # asserts 163 shipped rows, and a notes contract asserting a row count
    # that has not actually shipped is a false claim (183's own words).
    "cedar_correction_register.csv",
]


def load25():
    spec = importlib.util.spec_from_file_location(
        "pub25", CODE / "25_build_publication_layer.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    print("=== Cedar Press 355: patch the shipped database ===\n")
    if not DB.exists():
        print(f"  {DB} absent - nothing to patch. Run 25 when the machine is "
              f"quiet.")
        return 0

    pub = load25()
    CB = pub.CB
    resolved, licensed, undocumented = pub.resolve_tables()
    by_file = {p.name: (t, p, idx) for t, p, idx, _x in resolved}

    st = DB.stat()
    print(f"  {DB.relative_to(CEDAR)}  {st.st_size / 1e9:.2f} GB  "
          f"mtime {date.fromtimestamp(st.st_mtime)}")
    before_mtime = st.st_mtime

    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA journal_mode=OFF")
    conn.execute("PRAGMA synchronous=OFF")
    have = {r[0] for r in conn.execute(
        "select name from sqlite_master where type='table'")}

    todo = []
    for fn in CORRECTED:
        if fn not in by_file:
            print(f"  - {fn:48s} not in 25's registry - it does not ship; "
                  f"skipped by name, not silently")
            continue
        t, path, idx = by_file[fn]
        t = pub.sqlname(t)
        if t not in have:
            # A table registered to ship but absent from the database is a
            # notes contract asserting rows that have not shipped. Create it
            # rather than skip - a skip here is the false claim 183 refused.
            print(f"  - {fn:48s} -> {t}: NOT YET IN THE DATABASE; creating it")
        todo.append((fn, t, path, idx))

    if DB.stat().st_mtime != before_mtime:
        print("  !! the database moved under us. Refusing to write.")
        return 2

    for fn, t, path, idx in todo:
        old = (conn.execute(f'select count(*) from "{t}"').fetchone()[0]
               if t in have else 0)
        header, rows = pub.load(path)
        if header is None:
            print(f"  !! {fn} unreadable - {t} LEFT ALONE")
            continue
        drop = {i for i, c in enumerate(header) if CB.is_licensed_col(c)}
        if drop:
            print(f"    [licensed] {t}: dropping "
                  f"{', '.join(header[i] for i in sorted(drop))}")
            header = [c for i, c in enumerate(header) if i not in drop]
            rows = [[v for i, v in enumerate(r) if i not in drop] for r in rows]
        cols = [pub.sqlname(c) for c in header]
        seen, final = {}, []
        for c in cols:
            if c in seen:
                seen[c] += 1
                c = f"{c}_{seen[c]}"
            else:
                seen[c] = 0
            final.append(c)
        if t in have:
            conn.execute(f'DROP TABLE "{t}"')
        conn.execute(f'CREATE TABLE {t} (\n  '
                     + ",\n  ".join(f'"{c}" TEXT' for c in final) + "\n);")
        conn.executemany(
            f"INSERT INTO {t} VALUES ({','.join('?' * len(final))})",
            [r[:len(final)] + [None] * (len(final) - len(r)) for r in rows])
        for ic in idx:
            ic_s = pub.sqlname(ic)
            if ic_s in final:
                conn.execute(f"CREATE INDEX ix_{t}_{ic_s} ON {t}({ic_s});")
        conn.commit()
        print(f"  - {t:<44s} {old:>7,} -> {len(rows):>7,} rows, "
              f"{len(final)} columns")

    # ---- verify by RE-READING the database, never from the run log --------
    print("\n  RE-READ from the shipped database:")
    checks = [
        ("lobbying_entity_year",
         "select sum(cast(n_filings as int)), sum(cast("
         "total_lobbying_spend_usd as real)) from lobbying_entity_year "
         "where entity_id='TRBF-SRPMCP-00'",
         "TRBF-SRPMCP-00 must read 141 filings / $10,414,000"),
        ("lobbying_entity_year",
         "select sum(cast(n_filings as int)), sum(cast("
         "total_lobbying_spend_usd as real)) from lobbying_entity_year "
         "where entity_id='TRBF-SROSAR-00'",
         "TRBF-SROSAR-00 must read 13 filings / $210,000"),
        ("foia_request_index",
         "select count(*) from foia_request_index where tribe_entity_id like "
         "'AKNF-GEORGT%'", "must be 0"),
        ("foia_request_index",
         "select count(*) from foia_request_index where "
         "tribe_entity_id='TRBF-ENTPRS-00'", "must be 2"),
    ]
    for t, q, why in checks:
        if t not in have:
            continue
        try:
            print(f"    {q.split('from')[1].strip()[:52]:52s} "
                  f"{conn.execute(q).fetchone()}   [{why}]")
        except sqlite3.Error as e:
            print(f"    !! {t}: {e}")
    conn.close()

    st2 = DB.stat()
    print(f"\n  {DB.name} now {st2.st_size / 1e9:.2f} GB")
    print(f"\n  NOTE: a full `py -3 code/25_build_publication_layer.py` "
          f"REPRODUCES this fix\n        (it rebuilds from the corrected "
          f"data/clean), it does not revert it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
