#!/usr/bin/env python3
"""
Cedar Press - 334: Which shipping tables carry MORE THAN ONE source vintage?

WHY
---
`data/clean/federal_funding_transactions.csv` carries the USAspending award
archive stamp `20260706` on 131,495 rows and `20260806` on 93,536 (measured by
`code/301_source_freshness_probe.py`, recorded in `docs/SOURCE_FRESHNESS.json`).
The product's citation string is GENERATED from a single `vintage` field
(`code/87_build_dataset_notes.py` -> `dist/*/notes.json` -> the app's
`collections.py`: "Version and vintage are load-bearing, not garnish").

**No single `vintage` string describes a two-vintage file honestly.** So before
anything can be decided about that one file, the same question has to be asked
of EVERY other clean table, because a defect found in one table and not looked
for in the others is a defect you have merely relocated.

WHAT IT MEASURES
----------------
For every `data/clean/*.csv`, the DISTINCT VALUE SET of each provenance column
it actually carries. A provenance column is one that records WHERE OR WHEN THE
ROW WAS OBTAINED, never when the event happened:

    source_archive_stamp   the USAspending monthly archive stamp (YYYYMMDD)
    fetched_date           when we retrieved it
    retrieved_date         "
    retrieved_at           "
    built_date             when the row was assembled
    promoted_date          when it was promoted into the clean table
    source_file            the physical object it came out of
    vintage                an explicit vintage, where a builder wrote one

A table is MIXED on a column when that column holds 2+ distinct non-blank
values. Mixing is NOT automatically a defect:

  * `built_date` differing across rows is normal and harmless - it says two
    scripts touched the file on two days, not that two source vintages are in
    it.
  * `source_archive_stamp` differing across rows IS the fatal kind, because it
    means the rows were cut from two different published states of the SAME
    upstream corpus, and a single citation would name one of them and be wrong
    about the other.

So the report separates SOURCE-VINTAGE columns (fatal to a single `vintage`
string) from BUILD-PROVENANCE columns (informational).

BLANKS ARE COUNTED SEPARATELY AND ON PURPOSE
--------------------------------------------
A blank provenance cell is a THIRD state, not a member of either vintage. On
`federal_funding_transactions.csv` the blanks are the majority of the file, and
reporting "two vintages" while 68% of rows carry neither would be the same
class of error as reading a missing column as an empty source
(`102_build_coverage_profile.py`, the defect that hid 307 declination letters
for 19 days).

READ-ONLY. Writes one report and touches no dataset.

Writes docs/VINTAGE_MIXING_AUDIT.json
       docs/VINTAGE_MIXING_AUDIT.md
"""

import csv
import json
import sys
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
DOCS = CEDAR / "docs"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

# Columns that name the SOURCE STATE a row was cut from. Two distinct values
# here means two upstream vintages are in one file and one `vintage` string
# cannot describe it.
SOURCE_VINTAGE_COLS = [
    "source_archive_stamp",
    "vintage",
    "source_vintage",
    "archive_stamp",
    "source_file",
]

# Columns that record OUR handling. Differing values are ordinary.
BUILD_PROV_COLS = [
    "fetched_date",
    "retrieved_date",
    "retrieved_at",
    "built_date",
    "promoted_date",
    "classified_date",
    "built_by_script",
]

# `source_file` is a source-vintage column in principle but is high-cardinality
# by design on files assembled from many objects (one value per raw object).
# Distinct-count alone would flag every one of them. It is reported, but a
# table is only called MIXED on it when the values resolve to more than one
# ARCHIVE VINTAGE, which only `source_archive_stamp` can actually answer. So it
# is carried as evidence, never as the verdict.
VERDICT_COLS = ["source_archive_stamp", "vintage", "source_vintage",
                "archive_stamp"]

MAX_DISTINCT_KEPT = 25


def audit(path: Path) -> dict | None:
    try:
        with open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
            rd = csv.DictReader(fh)
            if not rd.fieldnames:
                return None
            lower = {c.lower(): c for c in rd.fieldnames}
            want = {}
            for cand in SOURCE_VINTAGE_COLS + BUILD_PROV_COLS:
                if cand.lower() in lower:
                    want[cand] = lower[cand.lower()]
            if not want:
                return {"file": path.name, "rows": sum(1 for _ in rd),
                        "columns": len(rd.fieldnames),
                        "provenance_columns": {},
                        "NO_PROVENANCE_COLUMN": True}
            counters = {k: Counter() for k in want}
            blanks = Counter()
            n = 0
            for row in rd:
                n += 1
                for k, real in want.items():
                    v = (row.get(real) or "").strip()
                    if v:
                        counters[k][v] += 1
                    else:
                        blanks[k] += 1
    except Exception as e:  # a file we cannot read is a finding, not a crash
        return {"file": path.name, "ERROR": f"{type(e).__name__}: {e}"}

    prov = {}
    for k, c in counters.items():
        distinct = len(c)
        top = c.most_common(MAX_DISTINCT_KEPT)
        prov[k] = {
            "kind": "SOURCE_VINTAGE" if k in SOURCE_VINTAGE_COLS
                    else "BUILD_PROVENANCE",
            "distinct_values": distinct,
            "blank_rows": blanks[k],
            "blank_pct": round(blanks[k] / n * 100, 2) if n else None,
            "values": dict(top) if distinct <= MAX_DISTINCT_KEPT
                      else {"_top_%d_of_%d" % (MAX_DISTINCT_KEPT, distinct):
                            dict(top)},
        }

    mixed_on = [k for k in VERDICT_COLS
                if k in counters and len(counters[k]) > 1]
    partial_on = [k for k in VERDICT_COLS
                  if k in counters and counters[k] and blanks[k]]

    return {
        "file": path.name,
        "rows": n,
        "provenance_columns": prov,
        "MIXED_SOURCE_VINTAGE": bool(mixed_on),
        "mixed_on": mixed_on,
        "PARTIALLY_STAMPED": bool(partial_on),
        "partially_stamped_on": partial_on,
    }


def main():
    print("=== Cedar Press 334: source-vintage mixing audit ===\n")
    files = sorted(p for p in CLEAN.glob("*.csv") if p.is_file())
    print(f"scanning {len(files)} tables under data/clean/\n")

    results = []
    for p in files:
        r = audit(p)
        if r is None:
            continue
        results.append(r)
        if r.get("ERROR"):
            print(f"  !! {r['file']}: {r['ERROR']}")
            continue
        if r.get("MIXED_SOURCE_VINTAGE"):
            cols = ", ".join(r["mixed_on"])
            print(f"  MIXED     {r['file']:<58} on {cols}")
            for k in r["mixed_on"]:
                d = r["provenance_columns"][k]
                print(f"                 {k}: {d['distinct_values']} values, "
                      f"{d['blank_rows']:,} blank ({d['blank_pct']}%)")
                vals = d["values"]
                if not any(x.startswith("_top_") for x in vals):
                    for v, c in sorted(vals.items(), key=lambda kv: -kv[1]):
                        print(f"                     {v:<24} {c:>10,}")
        elif r.get("PARTIALLY_STAMPED"):
            k = r["partially_stamped_on"][0]
            d = r["provenance_columns"][k]
            print(f"  PARTIAL   {r['file']:<58} {k} blank on "
                  f"{d['blank_rows']:,} of {r['rows']:,} rows")

    mixed = [r for r in results if r.get("MIXED_SOURCE_VINTAGE")]
    partial = [r for r in results
               if r.get("PARTIALLY_STAMPED") and not r.get("MIXED_SOURCE_VINTAGE")]
    nostamp = [r for r in results
               if not r.get("ERROR") and not r.get("MIXED_SOURCE_VINTAGE")
               and not r.get("PARTIALLY_STAMPED")]

    print(f"\n  {len(mixed)} table(s) carry MORE THAN ONE source vintage")
    print(f"  {len(partial)} table(s) are PARTIALLY stamped "
          f"(one vintage + blanks)")
    print(f"  {len(nostamp)} table(s) are single-vintage or unstamped")

    out = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "script": "code/334_audit_source_vintage_mixing.py",
        "modifies_datasets": False,
        "tables_scanned": len(results),
        "MIXED_SOURCE_VINTAGE": [r["file"] for r in mixed],
        "PARTIALLY_STAMPED": [r["file"] for r in partial],
        "SINGLE_VINTAGE_OR_UNSTAMPED": [r["file"] for r in nostamp],
        "detail": {r["file"]: r for r in results},
    }
    DOCS.mkdir(exist_ok=True)
    p = DOCS / "VINTAGE_MIXING_AUDIT.json"
    part = p.with_suffix(".json.part")
    part.write_text(json.dumps(out, indent=1), encoding="utf-8")
    part.replace(p)
    print(f"\n  wrote {p.relative_to(CEDAR)}")


if __name__ == "__main__":
    main()
