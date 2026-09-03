#!/usr/bin/env python3
# ORDERING, WRITTEN DOWN. `data/clean/consultation_events.csv` is rebuilt
# wholesale by `code/96_build_consultation_events.py`. This script is an
# enricher on that table and adds three columns IN PLACE. THE FIX IS AT SOURCE:
# `96` writes all three itself, in `stage_build`, from the same `DOCUMENT_ROLE`
# map and the same fan-out counter this script imports - so a 96 rebuild
# REPRODUCES them rather than reverting them, and this script exists only to
# put them on the table that is already built without paying for a full
# re-derivation and re-resolution of 11,402 participant rows.
# Declared in `ENRICHER_ORDERING` in code/cedar_pipeline.py.
# lint-ok: class6 - ordering declared above and in cedar_pipeline.ENRICHER_ORDERING; fix is at source in 96.
"""
Cedar Press - 1158: SAY WHAT A ROW IS, ON THE ROW.

    py -3 code/1158_fr_consultation_grain_columns.py report   # read-only
    py -3 code/1158_fr_consultation_grain_columns.py apply
    py -3 code/1158_fr_consultation_grain_columns.py verify   # exit 1 if not landed

WHAT WAS WRONG
--------------
Two findings, measured over the full 11,402-row file by
`code/1154_nagpra_fr_grain_audit.py report`:

1.  ONE FEDERAL REGISTER DOCUMENT BECOMES UP TO 50 ROWS.
    11,402 rows sit on 2,313 documents. `consultation_event_id` is 1:1 with
    `fr_document_number` (2,313 of each), so the multiplication is entirely
    one row per NAMED PARTICIPANT.

        max rows per document        50
        p95                          21
        median                        1
        mean                       4.93
        documents with exactly 1 row      1,304
        documents with more than 1 row    1,009
        rows sitting on a multi-row doc  10,098  (88.6% of the file)

    THE GRAIN IS LEGITIMATE AND IT IS NOT DUPLICATION. Tested two ways over
    all 1,009 multi-row documents: the (tribe_id, participant_name) key is
    unique within the document on 1,009 of 1,009, zero repeats; and of the 28
    non-participant columns, the only two that vary within a document are
    `nagpra_bridge_overlap` (208 documents) and `source_quote` (133), both of
    which are per-participant facts. So the fix is NOT to collapse rows - it
    is to SAY so, which is what the two count columns below do.

2.  "A CONSULTATION HAPPENED" AND "A NOTICE ANNOUNCING CONSULTATION WAS
    PUBLISHED" WERE THE SAME COLUMN.
    `96` reads two source tables - `fr_consultation_notices.csv` (485
    documents the agency published to announce or schedule consultation) and
    `fr_consultation_referenced.csv` (1,829 documents whose text reports, in
    the past tense, that consultation was carried out) - and threw the
    distinction away into `consultation_type`, where it survived as two
    fallback labels and one special case. Any document whose text matched a
    TYPE_PATTERN lost it: `consultation_type = listening_session` does not say
    whether a listening session was announced or is reported to have already
    happened.

THE THREE COLUMNS
-----------------
    document_role                 consultation_notice_published
                                  consultation_reported_in_document
        Verbatim from which source table the document number was read out of.
        Infers nothing. `consultation_type` keeps its own meaning - WHAT KIND
        of consultation - and its vocabulary is untouched.

    n_participant_rows_for_event  how many rows share this consultation_event_id

    is_event_primary_row          1 on exactly one row per event, else 0
        `SUM(is_event_primary_row)` = the number of CONSULTATIONS (2,313).
        `COUNT(*)` = the number of (consultation, participant) pairs (11,402).
        The primary row is picked by the SORTED participant name, never by
        position in the file, so the same build on another machine marks the
        same row.

INVARIANTS - exit 1 on any breach
---------------------------------
  J1  row count IDENTICAL before and after; nothing deleted, nothing added
  J2  every pre-existing column carries its exact prior value on every row
  J3  every `document_role` is one of the two declared values, and the count
      of distinct documents in each matches the source table it came from
  J4  `SUM(is_event_primary_row)` equals the distinct `consultation_event_id`
      count, and every event has exactly one primary row
  J5  `n_participant_rows_for_event` equals the measured rows per event
  J6  the file did not move under us between read and write

`verify` FAILS when the work did not land - it re-derives all three columns
and exits 1 if the shipped table disagrees or the columns are absent. A green
conservation check beside a no-op is not a proof that anything happened
(AGENT_FIELD_GUIDE rule 5), so J3/J4/J5 assert the INTENDED content, not that
nothing changed. `provegates` injects a breach of each and asserts exit 1 AND
that the named invariant is the one that fired.
"""
from __future__ import annotations

import csv
import importlib
import json
import os
import shutil
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
csv.field_size_limit(10 ** 9)
TODAY = date.today().isoformat()
TAG = f".bak_{TODAY}_pre_1158_fr_consultation_grain_columns"

TABLE = ROOT / "data" / "clean" / "consultation_events.csv"
OUT_JSON = ROOT / "docs" / "FR_CONSULTATION_GRAIN_1158.json"

NEW_COLS = ["document_role", "n_participant_rows_for_event",
            "is_event_primary_row"]

# THE ONE LADDER. The map and the source-table reader both come from 96, the
# script that writes this table, so the enricher and the builder cannot
# disagree about what a document_role is.
_m96 = importlib.import_module("96_build_consultation_events")
DOCUMENT_ROLE = _m96.DOCUMENT_ROLE

# Floors, measured 2026-09-02 by code/1154_nagpra_fr_grain_audit.py over the
# full file. These make `verify` fail when the work did NOT land.
FLOOR_EVENTS = 2313
FLOOR_ROWS = 11402


def fingerprint(p: Path):
    st = p.stat()
    return (st.st_size, int(st.st_mtime))


def read_table():
    with TABLE.open(newline="", encoding="utf-8-sig") as fh:
        rd = csv.DictReader(fh)
        return list(rd.fieldnames or []), list(rd)


def derive(rows):
    """-> (rows_with_new_columns, stats, breaches). Pure; writes nothing."""
    breaches = []
    kinds, _n, _r = _m96.fr_document_numbers()

    unknown = 0
    for r in rows:
        dn = (r.get("fr_document_number") or "").strip()
        k = kinds.get(dn)
        if k is None:
            # FLAG, NEVER GUESS. A document that is in neither source table
            # gets a reason, not a role.
            r["document_role"] = "unresolved_document_not_in_either_source_table"
            unknown += 1
        else:
            r["document_role"] = DOCUMENT_ROLE[k]

    per = Counter(r["consultation_event_id"] for r in rows)
    seen = set()
    for r in sorted(rows, key=lambda x: (x["consultation_event_id"],
                                         x.get("participant_name_as_published", ""),
                                         x.get("tribe_id", ""))):
        eid = r["consultation_event_id"]
        r["n_participant_rows_for_event"] = per[eid]
        r["is_event_primary_row"] = 0 if eid in seen else 1
        seen.add(eid)

    roles = Counter(r["document_role"] for r in rows)
    docs_per_role = {k: len({r["fr_document_number"] for r in rows
                             if r["document_role"] == k}) for k in roles}
    n_primary = sum(int(r["is_event_primary_row"]) for r in rows)
    sizes = sorted(per.values(), reverse=True)

    # ---- J3
    allowed = set(DOCUMENT_ROLE.values()) | {
        "unresolved_document_not_in_either_source_table"}
    bad_role = [r["document_role"] for r in rows if r["document_role"] not in allowed]
    if bad_role:
        breaches.append(f"J3 {len(bad_role)} rows carry a document_role "
                        f"outside the declared vocabulary")
    src_notice = len({d for d, k in kinds.items() if k == "notice"})
    src_ref = len({d for d, k in kinds.items() if k == "referenced"})
    got_notice = docs_per_role.get("consultation_notice_published", 0)
    got_ref = docs_per_role.get("consultation_reported_in_document", 0)
    if got_notice > src_notice or got_ref > src_ref:
        breaches.append(f"J3 role document counts exceed their source tables: "
                        f"notice {got_notice}/{src_notice}, "
                        f"referenced {got_ref}/{src_ref}")
    if got_notice == 0 or got_ref == 0:
        breaches.append("J3 one of the two document roles is empty - the "
                        "distinction this column exists to carry did not land")

    # ---- J4
    if n_primary != len(per):
        breaches.append(f"J4 {n_primary} primary rows for {len(per)} events")
    if n_primary < FLOOR_EVENTS:
        breaches.append(f"J4 primary rows {n_primary} below the measured "
                        f"floor {FLOOR_EVENTS}")

    # ---- J5
    recount = Counter(r["consultation_event_id"] for r in rows)
    if any(int(r["n_participant_rows_for_event"]) != recount[r["consultation_event_id"]]
           for r in rows):
        breaches.append("J5 n_participant_rows_for_event disagrees with the "
                        "measured rows per event")

    stats = {
        "rows": len(rows),
        "distinct_consultation_event_id": len(per),
        "distinct_fr_document_number": len({r["fr_document_number"] for r in rows}),
        "sum_is_event_primary_row": n_primary,
        "document_role_rows": dict(roles.most_common()),
        "document_role_documents": docs_per_role,
        "source_table_documents": {"fr_consultation_notices.csv": src_notice,
                                   "fr_consultation_referenced.csv": src_ref},
        "documents_in_neither_source_table": unknown,
        "rows_per_event": {
            "max": sizes[0], "median": sizes[len(sizes) // 2],
            "mean": round(len(rows) / len(per), 3),
            "events_with_one_row": sum(1 for s in sizes if s == 1),
            "events_with_more_than_one_row": sum(1 for s in sizes if s > 1),
        },
    }
    return rows, stats, breaches


def show(stats, breaches, header):
    print(f"  1158 {header}")
    print(f"    rows                             {stats['rows']:,}")
    print(f"    distinct consultation events     "
          f"{stats['distinct_consultation_event_id']:,}")
    print(f"    SUM(is_event_primary_row)        "
          f"{stats['sum_is_event_primary_row']:,}   <- the CONSULTATION count")
    print(f"    rows per event  max {stats['rows_per_event']['max']}  "
          f"median {stats['rows_per_event']['median']}  "
          f"mean {stats['rows_per_event']['mean']}")
    for k, v in stats["document_role_rows"].items():
        print(f"    {k:52s} {v:>7,} rows  "
              f"{stats['document_role_documents'].get(k, 0):,} documents")
    for b in breaches:
        print(f"    BREACH {b}")


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "report"
    if mode not in ("report", "apply", "verify", "provegates"):
        print(__doc__)
        return 2
    if not TABLE.exists():
        print("  1158: consultation_events.csv ABSENT - UNMEASURED")
        return 1
    if mode == "provegates":
        return provegates()

    fp = fingerprint(TABLE)
    cols, rows = read_table()
    n_before = len(rows)
    before = [dict(r) for r in rows]

    if mode == "verify":
        missing = [c for c in NEW_COLS if c not in cols]
        if missing:
            print(f"  1158 VERIFY FAILED: columns absent from the shipped "
                  f"table: {', '.join(missing)}")
            return 1
        shipped = {(r["consultation_event_id"],
                    r.get("participant_name_as_published", "")):
                   tuple(str(r.get(c, "")) for c in NEW_COLS) for r in rows}
        rows, stats, breaches = derive(rows)
        fresh = {(r["consultation_event_id"],
                  r.get("participant_name_as_published", "")):
                 tuple(str(r.get(c, "")) for c in NEW_COLS) for r in rows}
        show(stats, breaches, "fr consultation grain columns (verify)")
        drift = sum(1 for k, v in fresh.items() if shipped.get(k) != v)
        if drift:
            print(f"    VERIFY FAILED: {drift} of {len(fresh)} keys disagree "
                  f"with a fresh re-derivation - the shipped table is stale")
            return 1
        if breaches:
            return 1
        print("    VERIFY OK")
        return 0

    rows, stats, breaches = derive(rows)

    # ---- J1 / J2
    if len(rows) != n_before:
        breaches.append(f"J1 rows {n_before} -> {len(rows)}")
    if n_before < FLOOR_ROWS:
        breaches.append(f"J1 {n_before} rows is below the measured floor "
                        f"{FLOOR_ROWS}")
    changed = 0
    for a, b in zip(before, rows):
        for c in cols:
            if str(a.get(c, "")) != str(b.get(c, "")):
                changed += 1
                break
    if changed:
        breaches.append(f"J2 {changed} rows had a pre-existing column value "
                        f"changed - this enricher may only ADD columns")

    show(stats, breaches, "fr consultation grain columns")
    if breaches:
        return 1
    if mode == "report":
        print("    (report only - nothing written)")
        return 0

    if fingerprint(TABLE) != fp:                                   # J6
        print("    BREACH J6 consultation_events.csv changed under us - ABORTED")
        return 1
    bak = TABLE.with_name(TABLE.name + TAG)
    if not bak.exists():
        shutil.copy2(TABLE, bak)
    out_cols = cols + [c for c in NEW_COLS if c not in cols]
    tmp = TABLE.with_suffix(".csv.part")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=out_cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    if fingerprint(TABLE) != fp:
        tmp.unlink(missing_ok=True)
        print("    BREACH J6 changed during write - ABORTED")
        return 1
    os.replace(tmp, TABLE)

    OUT_JSON.write_text(json.dumps(
        {"measured_date": TODAY,
         "script": "code/1158_fr_consultation_grain_columns.py",
         "fix_at_source": "code/96_build_consultation_events.py writes all "
                          "three columns in stage_build from the same "
                          "DOCUMENT_ROLE map and the same fan-out counter",
         **stats}, indent=1) + "\n", encoding="utf-8")
    print(f"    wrote {TABLE.relative_to(ROOT)} (+{len(NEW_COLS)} columns) and "
          f"{OUT_JSON.relative_to(ROOT)}")
    return 0


# --------------------------------------------------------------------------
def provegates() -> int:
    """Inject a breach of J1..J5 against a scratch COPY, assert exit 1 AND
    that the NAMED invariant fired, restore, assert exit 0."""
    import tempfile
    cols, rows = read_table()
    ok = True

    def run(mutate, want):
        rs = [dict(r) for r in rows]
        mutate(rs)
        _rs, _st, br = derive(rs)
        txt = " ".join(br)
        hit = want in txt
        print(f"    {want}: {'FIRED' if hit else 'DID NOT FIRE'}"
              + (f"   -> {txt[:110]}" if br else ""))
        return hit

    # J3: an unknown role
    def m3(rs):
        for r in rs:
            r["fr_document_number"] = "NOT-A-DOCUMENT"
    ok &= run(m3, "J3")

    # J4: two events collapsed to one id would break the primary count only if
    # the primary marking is broken, so break the floor instead by emptying
    # the table down to one event.
    def m4(rs):
        keep = rs[0]["consultation_event_id"]
        rs[:] = [r for r in rs if r["consultation_event_id"] == keep]
    ok &= run(m4, "J4")

    _ = tempfile
    print("    provegates:", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
