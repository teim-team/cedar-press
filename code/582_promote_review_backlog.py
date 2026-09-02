#!/usr/bin/env python3
"""
Cedar Press - 582: promote what `581_triage_review_backlog.py` found PROMOTABLE.

    py -3 code/582_promote_review_backlog.py           # dry run, writes nothing
    py -3 code/582_promote_review_backlog.py --apply
    py -3 code/582_promote_review_backlog.py --selftest

WHAT IT PROMOTES, AND WHAT IT DELIBERATELY DOES NOT
---------------------------------------------------
581 put 3 of `review/`'s 364 CSVs in PROMOTABLE_NOW. This file promotes exactly
ONE of them:

    review/sam_class_distributions_PUBLISHABLE_2026-08-26.csv  (176 rows)
        -> data/clean/sam_native_class_distributions.csv
        -> data/clean/codebook/02s_sam_native_class_distributions.csv

The other two are gaming and belong to a live sibling workstream:

    review/nm_revshare_2023_2026_staged_2026-08-26.csv   188 rows -> INT-2
    review/sealed_state_typed_rows_2026-08-26.csv         10 rows -> INT-2

Cedar's rule is one owner per dataset. Promoting another workstream's table
while it is live is how this project lost 2,146,673 accounted rows on
2026-09-01.

WHY THIS ONE IS SAFE AND THE 62-TRIBE VENDOR REGISTRY WAS NOT
--------------------------------------------------------------
`358_measure_sam_individual_native_class_delta.py` wrote the source file as the
publishable HALF of a two-file split. Its header states the contract:

    "It never publishes a private individual. The per-firm file is INTERNAL.
     The publishable artefact is AGGREGATE ONLY, with any cell resolving to
     fewer than 3 firms suppressed and the suppression reported."

358 also stated the ONLY reason it stopped short of `data/clean`: *"a new
`data/clean` table would move six shipping counters that are already failing for
another agent"* - a scheduling constraint from 2026-08-26, not a data defect.
That is the definition of "nothing but effort blocks it".

By contrast `review/tribal_vendor_list_registry_2026-08-26.csv` reads finished
and is not: re-measured 2026-09-01 it carries `publishable = N` on all 62 rows
and `consent_status = UNRESOLVED` on all 62. It stays in `review/`.

THREE GUARDS, EACH OF WHICH REFUSES THE WRITE
----------------------------------------------
A check does not count until a fixture proves it FIRES, so `--selftest` injects
a violation of each and requires a refusal.

  G1 SMALL CELL   no row may report a value with `n_firms < 3` unless
                  `value_suppressed_small_cell = 1`. Measured on the real file:
                  33 of 176 cells suppressed, 0 violations.
  G2 PRIVACY      no column may be person-shaped. 32 rows leaked into a
                  diagnostic payload on 2026-09-01 exactly this way. This file
                  is aggregate, so ANY person-shaped column is a defect.
  G3 NO TOTAL     ENTITY_OWNED and INDIVIDUAL_NATIVE_OWNED are separate
                  populations. A row whose `variant_class` is neither - a total
                  line - would be quotable by accident and is refused.

WHAT IT DOES NOT DO
-------------------
Writes the codebook FRAGMENT only. It does NOT call `cedar_codebook.build()`:
the master is shared and the shipping runbook owns that step (step 1 of
`docs/SHIPPING_RUNBOOK.md`). It does not run 87, 25 or 27. It touches no ledger,
no spine, no `cedar_harvest_conservation.csv`, and no sibling's file.
"""
from __future__ import annotations

import csv
import importlib.util
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = os.path.join(ROOT, "code")
SRC = os.path.join(ROOT, "review",
                   "sam_class_distributions_PUBLISHABLE_2026-08-26.csv")
DST = os.path.join(ROOT, "data", "clean", "sam_native_class_distributions.csv")
DATASET = "02s_sam_native_class_distributions"
TODAY = "2026-09-01"
CLASSES = {"ENTITY_OWNED", "INDIVIDUAL_NATIVE_OWNED"}

PERSON_COL = re.compile(
    r"(personal|home_address|owner_name|individual_name|surrogate|email|phone|"
    r"street_address|_dob|principal_name|legal_business_name|awardee_name|uei|"
    r"cage)", re.I)

DESCRIPTIONS = {
    "variant_class":
        "Which Native-ownership population the cell belongs to: ENTITY_OWNED "
        "(a tribe, ANC or NHO owns the firm) or INDIVIDUAL_NATIVE_OWNED (a "
        "Native individual owns it). THESE ARE NEVER SUMMED INTO ONE NATIVE "
        "TOTAL - they are different populations counted from different SAM "
        "extracts, and a combined figure double-counts firms carrying both "
        "flags.",
    "dimension":
        "What the distribution is cut by: fiscal_year, funding_department, "
        "naics_2_digit or setaside_name.",
    "value": "The category within `dimension` this cell counts.",
    "n_firms":
        "Distinct UEIs in the cell. Blank when the cell is suppressed.",
    "n_rows":
        "Contract action rows in the cell. Blank when the cell is suppressed.",
    "action_obligation_usd":
        "Sum of action obligations, nominal USD, not deflated. Blank when the "
        "cell is suppressed.",
    "value_suppressed_small_cell":
        "1 when the cell resolved to fewer than 3 firms and its figures were "
        "withheld. The CELL is still listed, so the reader can see that a "
        "category exists and was suppressed rather than being absent.",
    "suppression_rule":
        "The rule that suppressed the cell, stated in the row rather than only "
        "in a codebook: 'fewer than 3 firms in the cell'.",
    "universe":
        "The population the cell is drawn from: include_in_native_universe = 1 "
        "only.",
    "class_rule":
        "The standing rule against summing the two classes, carried on every "
        "row so it cannot be separated from the numbers.",
    "generated": "Date 358 measured the distribution.",
    "source_review_file":
        "The `review/` file this row was promoted from, for provenance.",
    "promoted_by": "Script that promoted the row into data/clean.",
    "promoted_date": "Date of promotion.",
}

EVIDENCE_NOTE = (
    "EVIDENCE CEILING: every UEI counted here entered through SAM's "
    "`awardeeBusinessTypeName`, which is a SELF-CERTIFICATION. Per "
    "docs/INDIVIDUAL_NATIVE_CLASS_PROPOSAL.md s4 that evidence tops out at "
    "tier C. These aggregates describe what firms CLAIMED, not what Cedar has "
    "adjudicated. Absence of a flag is NO_CLAIM_FOUND, never NOT_NATIVE."
)


def read(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def guard(rows: list[dict]) -> list[str]:
    """Returns a list of refusals. Empty list == safe to write."""
    bad: list[str] = []
    if not rows:
        return ["G0 EMPTY: source file has no rows"]
    cols = list(rows[0].keys())

    for c in cols:                                                    # G2
        if PERSON_COL.search(c):
            bad.append(f"G2 PRIVACY: person-shaped column {c!r} in an "
                       "aggregate-only table")

    for i, r in enumerate(rows, 2):
        supp = (r.get("value_suppressed_small_cell") or "").strip()
        nf = (r.get("n_firms") or "").strip()
        if supp != "1" and nf.isdigit() and int(nf) < 3:              # G1
            bad.append(f"G1 SMALL CELL: line {i} reports n_firms={nf} "
                       "unsuppressed")
        vc = (r.get("variant_class") or "").strip()
        if vc not in CLASSES:                                         # G3
            bad.append(f"G3 NO TOTAL: line {i} variant_class={vc!r} is neither "
                       "ENTITY_OWNED nor INDIVIDUAL_NATIVE_OWNED")
    return bad


def selftest() -> int:
    """A check does not count until a fixture proves it FIRES."""
    base = dict(variant_class="ENTITY_OWNED", dimension="fiscal_year",
                value="2020", n_firms="40", n_rows="100",
                action_obligation_usd="1", value_suppressed_small_cell="0",
                suppression_rule="", universe="u", class_rule="c",
                generated=TODAY)
    ok = True
    cases = [
        ("G1", [dict(base, n_firms="2")]),
        ("G2", [{**base, "awardee_name": "X"}]),
        ("G3", [dict(base, variant_class="ALL_NATIVE")]),
    ]
    for name, rows in cases:
        hits = [b for b in guard(rows) if b.startswith(name)]
        print(f"  {name}: {'FIRED' if hits else 'DID NOT FIRE  <-- BROKEN'}"
              f"  {hits[0] if hits else ''}")
        ok = ok and bool(hits)
    clean = guard([base])
    print(f"  clean row: {'no refusal (correct)' if not clean else clean}")
    ok = ok and not clean
    print("SELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    apply = "--apply" in sys.argv

    rows = read(SRC)
    print(f"source  {os.path.relpath(SRC, ROOT)}  {len(rows):,} rows")

    bad = guard(rows)
    if bad:
        print(f"REFUSING to promote - {len(bad)} guard violation(s):")
        for b in bad[:20]:
            print("   " + b)
        return 1
    nsupp = sum(1 for r in rows
                if (r.get("value_suppressed_small_cell") or "") == "1")
    print(f"guards  G1 small-cell OK ({nsupp} of {len(rows)} cells suppressed) "
          "| G2 privacy OK | G3 no-total OK")

    for r in rows:
        r["source_review_file"] = os.path.relpath(SRC, ROOT).replace("\\", "/")
        r["promoted_by"] = "code/582_promote_review_backlog.py"
        r["promoted_date"] = TODAY
    fields = list(rows[0].keys())

    if not apply:
        print(f"DRY RUN. Would write {len(rows):,} rows -> "
              f"{os.path.relpath(DST, ROOT)}")
        print(f"          and codebook fragment {DATASET} "
              f"({len(fields)} variables)")
        print("Re-run with --apply.")
        return 0

    if os.path.exists(DST):
        shutil.copy2(DST, DST + f".bak_{TODAY}_pre582")
    tmp = DST + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, DST)
    print(f"WROTE   {os.path.relpath(DST, ROOT)}  {len(rows):,} rows")

    spec = importlib.util.spec_from_file_location(
        "cedar_codebook", os.path.join(CODE, "cedar_codebook.py"))
    cb = importlib.util.module_from_spec(spec)
    sys.modules["cedar_codebook"] = cb
    spec.loader.exec_module(cb)

    n = len(rows)
    frag = []
    for c in fields:
        filled = sum(1 for r in rows if (r.get(c) or "").strip())
        desc = DESCRIPTIONS.get(c, "")
        if c == "variant_class":
            desc += " " + EVIDENCE_NOTE
        frag.append(dict(
            dataset=DATASET, variable=c,
            type="number" if c in ("n_firms", "n_rows",
                                   "action_obligation_usd",
                                   "value_suppressed_small_cell") else "text",
            units="USD" if c == "action_obligation_usd" else
                  ("count" if c in ("n_firms", "n_rows") else "text"),
            pct_filled=round(100.0 * filled / n, 1), n_rows=n,
            published=1, access_tier="public", description=desc,
            generated=TODAY))
    cb.write_fragment(DATASET, frag)
    print(f"WROTE   data/clean/codebook/{DATASET}.csv  "
          f"{len(frag)} variables")
    print("\nNOT DONE HERE, ON PURPOSE: cedar_codebook.build(), 87, 25, 27. "
          "The master codebook and dist/ are shared; the shipping runbook owns "
          "them and the gate must be green first.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
