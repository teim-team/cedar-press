#!/usr/bin/env python3
"""
Cedar Press - 1172: generate codebook blocks FROM MEASURED SCHEMA for the
tables that have none, and separate the ones that should be internal instead.

    py -3 code/1172_codebook_block_generator.py            # report
    py -3 code/1172_codebook_block_generator.py apply      # write fragments
    py -3 code/1172_codebook_block_generator.py selftest

WHY, AND WHY NOT BY HAND
------------------------
External review, 2026-09-03:

    "Do not solve the forty-seven missing codebook blocks by hand-writing
     forty-seven independent prose sections that will drift from the code. The
     canonical object should be a schema... Generate Markdown codebook blocks
     from that schema and require human review of the definitions."

`62_no_regression_check.py` is red on `tables_undocumented_in_codebook`, and a
table without a block cannot ship. That red blocks `289_update_collection.py`
at step 4, which is why `dist/cedar_press.db`, `dist/collections/*.json`,
`dist/manifests/*.json` and `dist/schema.sql` are all stale - and why the
database still carries the retired identity scheme on 73 of 231 tables while
the CSVs are clean. **One red gate is holding two of the six release blockers.**

Measured 2026-09-03 via `cedar_codebook.registered_tables()`: **27 tables**
undocumented (not 47 - that figure was from an earlier snapshot; the count moves
as other workstreams write).

WHAT THIS GENERATES, AND WHAT IT REFUSES TO INVENT
---------------------------------------------------
Everything mechanical is MEASURED from the file: column name, inferred type,
percent filled, row count. Those are facts and this script will state them.

A column's MEANING is not mechanical. This script will not write a plausible
sentence about what `conservation_basis` means, because a codebook whose
definitions are fabricated is worse than one with gaps - a reader cannot tell
which entries were authored and which were guessed, so none of them can be
trusted. Where a definition is not derivable, the description is the literal
string `DEFINITION NOT YET AUTHORED`, which is greppable, countable, and
impossible to mistake for a real definition.

Definitions ARE derived for columns whose meaning is fixed by this project's own
conventions and enforced elsewhere in code: `cedar_uid`, `*_uei`, `*_cage`,
`*_ein`, `*_date`, `*_usd`, `*_flag`, `*_url`, `n_*`, `*_basis`, `*_source_file`.
Those are not guesses; they are this repo's documented vocabulary.

INTERNAL IS A CLASSIFICATION, NOT A GAP
----------------------------------------
`62`'s own comment records the trap: adding three internal tables once raised
four "missing from X" ratchets by three apiece, "reporting a registration
backlog for files that are registered - as internal". Several of these 27 are
plainly Cedar's own audit machinery (`cedar_corroboration_*`,
`cedar_fact_corroboration`, `cedar_harvest_coverage_*`, `*_web_harvest_*`,
`*_coverage`). Those want `INTERNAL_TABLES`, not a public block.

This script PROPOSES that classification and does not make it. Deciding a table
is internal is a product decision about what a customer is owed, and it is not
the sort of thing a generator should settle on a name pattern.
"""
from __future__ import annotations

import csv
import importlib.util
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()
CLEAN = ROOT / "data" / "clean"
NOT_AUTHORED = "DEFINITION NOT YET AUTHORED"
SAMPLE = 5000     # rows read per file to infer type; fill rate is FULL-file


def _cb():
    spec = importlib.util.spec_from_file_location(
        "cedar_codebook", ROOT / "code" / "cedar_codebook.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# This repo's own column vocabulary, enforced in code elsewhere. Not guesses.
KNOWN = [
    (re.compile(r"^cedar_uid$"), "text", "code",
     "Cedar's permanent key for the Native entity this row concerns."),
    (re.compile(r"^cedar_place_id$"), "text", "code",
     "Cedar's permanent key for a place."),
    (re.compile(r"_uei$|^uei$"), "text", "code",
     "SAM.gov Unique Entity ID (12 characters)."),
    (re.compile(r"cage(_code)?$"), "text", "code",
     "Commercial and Government Entity (CAGE) code."),
    (re.compile(r"^ein$|_ein$"), "text", "code",
     "IRS Employer Identification Number."),
    (re.compile(r"_date$|^date$"), "date", "ISO-8601",
     "Date, ISO-8601. See the dataset notes for which event it marks."),
    (re.compile(r"_year$|^year$|^fiscal_year$"), "integer", "year", "Year."),
    (re.compile(r"_usd$|_amount$|_dollars$"), "numeric", "USD",
     "Amount in US dollars, nominal unless the column name says real."),
    (re.compile(r"_flag$|^is_|^has_"), "boolean", "flag",
     "Boolean flag."),
    (re.compile(r"_url$|^url$"), "text", "url", "Source URL."),
    (re.compile(r"^n_"), "integer", "count",
     "Row count from a joined table. See the join-cardinality note."),
    (re.compile(r"_basis$"), "text", "prose",
     "Stated basis for the value beside it - evidence, not lineage."),
    (re.compile(r"_state$|^state$|_state_code$"), "text", "USPS",
     "US state, USPS two-letter code."),
    (re.compile(r"_name$|^name$"), "text", "prose", "Name, as recorded."),
    (re.compile(r"_tier$|^tier$"), "text", "code",
     "Tier. WARNING: `tier` means different things in different datasets - "
     "confirm against this dataset's notes before comparing across datasets."),
]

# Name patterns that suggest Cedar's own machinery rather than a customer table.
INTERNAL_HINT = re.compile(
    r"corroboration|_freshness$|harvest_coverage|web_harvest|"
    r"^cedar_constellation|_coverage$|^source_coverage")


def infer(path: Path):
    """Measured schema for one file. Fill rate is a FULL pass, never sampled."""
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.reader(fh)
        hdr = next(rd, None)
        if not hdr:
            return None, 0, {}
        filled = {c: 0 for c in hdr}
        vals = {c: [] for c in hdr}
        n = 0
        for row in rd:
            n += 1
            for i, c in enumerate(hdr):
                if i < len(row) and (row[i] or "").strip():
                    filled[c] += 1
                    if len(vals[c]) < 20 and n <= SAMPLE:
                        vals[c].append(row[i].strip())
    return hdr, n, {"filled": filled, "vals": vals}


def describe(col: str, samples: list):
    for rx, typ, unit, desc in KNOWN:
        if rx.search(col.lower()):
            return typ, unit, desc
    # Type is inferable from values even when meaning is not.
    if samples:
        if all(re.fullmatch(r"-?\d+", s) for s in samples):
            return "integer", "count", NOT_AUTHORED
        if all(re.fullmatch(r"-?\d*\.?\d+", s) for s in samples):
            return "numeric", "", NOT_AUTHORED
        if all(re.fullmatch(r"\d{4}-\d{2}-\d{2}.*", s) for s in samples):
            return "date", "ISO-8601", NOT_AUTHORED
        if {s.lower() for s in samples} <= {"y", "n", "yes", "no", "true",
                                            "false", "0", "1"}:
            return "boolean", "flag", NOT_AUTHORED
    return "text", "", NOT_AUTHORED


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "report"
    CB = _cb()
    _sh, _lic, und = CB.registered_tables()
    targets = sorted({Path(t[0]) if isinstance(t, tuple) else Path(t)
                      for t in und})

    if mode == "selftest":
        # POSITIVE CONTROL. A generator that silently produces nothing looks
        # identical to a tree with nothing to generate.
        t, u, d = describe("total_obligations_usd", ["100"])
        ok1 = u == "USD" and d != NOT_AUTHORED
        t2, _u2, d2 = describe("conservation_basis_xyz", ["abc"])
        ok2 = d2 == NOT_AUTHORED
        t3, _u3, _d3 = describe("some_count", ["1", "2", "3"])
        ok3 = t3 == "integer"
        for ok, what in ((ok1, "a known column gets a real definition"),
                         (ok2, "an unknown column is marked NOT AUTHORED, never invented"),
                         (ok3, "type is inferred from values")):
            print(f"    {'ok  ' if ok else 'FAIL'}  {what}")
        bad = sum(1 for ok in (ok1, ok2, ok3) if not ok)
        print(f"\n  1172 selftest   {'ok' if not bad else 'FAIL'}   {bad} failure(s)")
        return 1 if bad else 0

    internal, public, rows_written = [], [], 0
    print(f"  undocumented tables: {len(targets)}\n")
    for p in targets:
        if not p.exists():
            continue
        stem = p.stem
        (internal if INTERNAL_HINT.search(stem) else public).append(stem)

    print(f"  PROPOSED INTERNAL (Cedar's own machinery, not a customer table): "
          f"{len(internal)}")
    for s in internal:
        print(f"      {s}")
    print(f"\n  NEEDS A PUBLIC BLOCK: {len(public)}")

    authored = unauthored = 0
    for p in targets:
        if not p.exists() or p.stem in internal:
            continue
        hdr, n, meta = infer(p)
        if not hdr:
            continue
        frag = []
        for c in hdr:
            typ, unit, desc = describe(c, meta["vals"].get(c, []))
            if desc == NOT_AUTHORED:
                unauthored += 1
            else:
                authored += 1
            frag.append({
                "dataset": p.stem, "variable": c, "type": typ, "units": unit,
                "pct_filled": round(meta["filled"][c] / n * 100, 1) if n else 0.0,
                "n_rows": n, "published": 1, "access_tier": "public",
                "description": desc, "generated": TODAY,
            })
        print(f"      {p.stem:<44} {len(hdr):>3} cols  {n:>9,} rows")
        if mode == "apply":
            rows_written += CB.write_fragment(p.stem, frag)

    print(f"\n  column definitions derived from this repo's vocabulary : {authored}")
    print(f"  column definitions NOT authored (honest gaps)          : {unauthored}")
    if mode == "apply":
        print(f"\n  wrote {rows_written} codebook rows across "
              f"{len(public)} fragment(s)")
        print("  now run: cedar_codebook.build(), then 87 -> 25 -> 27 per "
              "docs/SHIPPING_RUNBOOK.md")
    else:
        print("\n  report only - pass `apply` to write fragments")
    return 0


if __name__ == "__main__":
    sys.exit(main())
