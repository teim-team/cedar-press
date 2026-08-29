#!/usr/bin/env python3
"""
208 — add the two normalised extent-competed variables to the PRIME codebook
FRAGMENT, and only to the fragment.

    py -3 code/208_register_extent_competed_codebook_fragment.py

WHY A FRAGMENT AND NOT `41_build_codebooks.py`
----------------------------------------------
41 is a GLOBAL rebuild across every dataset and
`docs/INDIVIDUAL_NATIVE_OWNERSHIP_VERIFICATION_BUILD_LOG.md` §10 records that
running it today would delete 21 of the 43 blocks the master now holds. This
machine runs concurrent agents. One dataset's fragment is the unit of work
here, exactly as `156_refresh_deals_codebook_fragment.py` established.

`data/clean/codebook_master.csv` is deliberately NOT touched. It is stale in a
way this script must not paper over: it carries `02_prime_contracting` TWICE
(78 rows for a 43-column table) and it does not yet know about `ruling_status`,
`ruling_source_file` or `ruling_applied_date` either. Reconciling master from
fragments is `cedar_register_codebook.py`'s job and its owner's timing.

Backup, `.part`, rename, re-read. Idempotent.
"""
from __future__ import annotations

import csv
import os
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRAG = ROOT / "data" / "clean" / "codebook" / "02_prime_contracting.csv"
PRIME = ROOT / "data" / "clean" / "prime_contracts.csv"
TODAY = date.today().isoformat()

csv.field_size_limit(10 ** 7)

NEW = {
    "extent_competed_normalized": (
        "The FPDS competition category on ONE vocabulary, so a filter selects a "
        "competition status rather than a source vintage. Derived from "
        "`extent_competed`, which is left exactly as recorded and holds TWO "
        "vocabularies: raw FPDS codes (A, B, C, D, E, F, G, CDO, NDO) on the "
        "FY2008-FY2016 archive files, and rendered description tags everywhere "
        "else. The crosswalk is quoted verbatim in `code/cedar_extent_competed.py` "
        "from DAIMS-DEC v2.2 (2022-06-03), sheet `Public`, element "
        "`ExtentCompeted`, column `Domain Values`, "
        "https://files.usaspending.gov/docs/Data_Dictionary_Crosswalk.xlsx - it "
        "was NOT inferred from our own data. One of: "
        "`FULL AND OPEN COMPETITION`, `NOT AVAILABLE FOR COMPETITION`, "
        "`NOT COMPETED`, `FULL AND OPEN COMPETITION AFTER EXCLUSION OF SOURCES`, "
        "`FOLLOW ON TO COMPETED ACTION`, `COMPETED UNDER SAP`, "
        "`NOT COMPETED UNDER SAP`, `COMPETITIVE DELIVERY ORDER`, "
        "`NON-COMPETITIVE DELIVERY ORDER`, `NOT_REPORTED`. `NOT_REPORTED` is "
        "blank-or-null at source and is NOT a competition status - 9,420 blanks "
        "plus 9,411 rows carrying the literal string `nan`, which the archive "
        "emits for a null and which the dictionary does not define. "
        "`UNDEFINED_BY_DICTIONARY` would mark a token the dictionary does not "
        "define; no row carries it today. NOTE that `COMPETED UNDER SAP` and "
        "`NOT COMPETED UNDER SAP` are Simplified Acquisition Procedures under "
        "FAR Part 13 and are not a FAR Part 6 competition at all, so 'competed' "
        "is a research decision across these nine categories, not one line."),
    "extent_competed_normalized_basis": (
        "Names the crosswalk that produced `extent_competed_normalized` and its "
        "source URL, then how the raw token was disposed of. Format: "
        "`DAIMS-DEC v2.2 ExtentCompeted | <url> | <disposition>`. Disposition is "
        "one of `FPDS_CODE_MAPPED` (raw was a dictionary code), "
        "`LABEL_AS_RECORDED` (raw was already the dictionary label, unchanged), "
        "`NOT_REPORTED_BLANK`, `NOT_REPORTED_NULL_TOKEN` (raw was the literal "
        "`nan`), or `UNDEFINED_BY_DICTIONARY`. Written by "
        "`code/207_normalize_extent_competed.py`; a full rebuild of "
        "`prime_contracts.csv` reverts it and 207 must be re-run afterwards, "
        "the same way `124_apply_rulings_in_place.py` must be."),
}


def main() -> int:
    if not FRAG.exists():
        print(f"MISSING: {FRAG}", file=sys.stderr)
        return 2

    with PRIME.open(newline="", encoding="utf-8") as fh:
        rdr = csv.reader(fh)
        hdr = next(rdr)
        n_rows = sum(1 for _ in rdr)
    for v in NEW:
        if v not in hdr:
            print(f"FATAL: {v} is not a column of prime_contracts.csv. "
                  "Run 207 apply first.", file=sys.stderr)
            return 3
    print(f"prime_contracts.csv: {n_rows:,} rows, {len(hdr)} columns")

    with FRAG.open(encoding="utf-8-sig", newline="") as fh:
        rdr = csv.DictReader(fh)
        fields = rdr.fieldnames or []
        rows = list(rdr)
    have = {r["variable"] for r in rows}
    todo = [v for v in NEW if v not in have]
    if not todo:
        print("Both variables already registered. Nothing to do (idempotent).")
        return 0

    # pct_filled is a measurement, so measure it rather than assert it.
    filled = {v: 0 for v in todo}
    with PRIME.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            for v in todo:
                if (row.get(v) or "").strip():
                    filled[v] += 1

    for v in todo:
        rows.append({
            "dataset": "02_prime_contracting",
            "variable": v,
            "type": "text",
            "units": "category" if v.endswith("normalized") else "provenance",
            "pct_filled": f"{100.0 * filled[v] / n_rows:.1f}",
            "n_rows": str(n_rows),
            "published": "1",
            "access_tier": "public",
            "description": NEW[v],
            "generated": TODAY,
        })
        print(f"  + {v}  pct_filled {100.0 * filled[v] / n_rows:.1f}")

    bak = FRAG.with_suffix(
        FRAG.suffix + f".bak_{TODAY}_pre_208_register_extent_competed")
    if not bak.exists():
        shutil.copy2(FRAG, bak)
        print(f"backed up -> {bak.name}")

    tmp = FRAG.with_suffix(FRAG.suffix + ".part")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, FRAG)

    with FRAG.open(encoding="utf-8-sig", newline="") as fh:
        back = list(csv.DictReader(fh))
    got = {r["variable"] for r in back}
    if not all(v in got for v in NEW):
        print("FATAL: re-read does not show the new variables", file=sys.stderr)
        return 4
    print(f"re-read {len(back)} variables in {FRAG.name}; both present.")
    print("codebook_master.csv deliberately NOT touched - fragment only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
