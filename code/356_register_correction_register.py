#!/usr/bin/env python3
"""
Cedar Press - 356: register `cedar_correction_register.csv` so it ships.

WHY THIS IS A SEPARATE SCRIPT, AGAIN
------------------------------------
The instant `354_correction_register.py` wrote its first table into
`data/clean`, `62_no_regression_check.py` failed on five lines:

    ship_tables_at_zero            ROSE 138 -> 139
    tables_missing_codebook_block  ROSE 139 -> 140
    tables_missing_from_25_TABLES  ROSE 234 -> 235
    tables_missing_from_27_SPEC    ROSE 249 -> 250
    tables_missing_notes_contract  ROSE 139 -> 140

That is the gate doing its job, and those five are MINE. `183_register_
lobbying_registrant_layer.py` had this exact experience two hours earlier and
its shape is followed here deliberately - including the part where the two
Python-literal registries are edited BY HAND rather than rewritten by a
script, because a script that edits another agent's script is worse than a
diff a person can read.

Registration is ADDITIVE and touches only this one table:

  1. a codebook FRAGMENT in `data/clean/codebook/` - the MASTER IS NEVER
     WRITTEN (`41_build_codebooks.py` opens it in "w" mode and would delete
     21 of 43 blocks; the 2026-08-07 lost-update fix stands).
  2. a notes contract in `dist/00_reference/`, in the schema
     `87_build_dataset_notes.py` emits, with the reading and research-ready
     blocks IMPORTED from 87 rather than copied.
  3. `TABLES` in 25 and `SPEC` in 27, edited by hand in the same session.

WHAT THIS TABLE IS, AS A PUBLISHED DATASET
------------------------------------------
It is the audit trail of every attribution this project has WITHDRAWN. It is
worth publishing for the same reason the withdrawals themselves are kept
visible: a corrections file is the only way a reader can tell "we never made
that claim" from "we made it and took it back". Cedar Press's whole premise is
never to attribute falsely, and a project that makes that claim owes the
public its list of corrections.

Zero network calls.
"""

import csv
import importlib.util
import json
import os
import sys
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"
FRAG = CLEAN / "codebook"
DIST = CEDAR / "dist" / "00_reference"
TODAY = date.today().isoformat()
SCRIPT = "356_register_correction_register.py"

csv.field_size_limit(min(sys.maxsize, 2147483647))

DATASET = "cedar_correction_register"
FILE = "cedar_correction_register.csv"

CODEBOOK = {
    "correction_id": "Stable id, md5 over (finding_id, entity_id, "
                     "withdrawn_key, table). Content-addressed and NOT "
                     "positional: three ids elsewhere in this project were "
                     "minted from Python's per-process-randomised hash() and "
                     "a re-run changed 482 of 492 of them.",
    "recorded_date": "The date the correction was declared.",
    "recorded_by_script": "The script that APPLIED the correction and "
                          "declared it. Not the script that found it.",
    "finding_id": "The finding this correction discharges, as named in "
                  "docs/ANOMALY_REPORT.md - FA-01, FA-02, ...",
    "entity_id": "The Cedar entity id that was WRONGLY attached. The "
                 "identifier itself is sound; the LINK was not. Never read "
                 "this column as a statement about the entity.",
    "withdrawn_key": "The SUBJECT the entity was wrongly attached to, keyed "
                     "so a sibling table can be re-tested: the LDA client "
                     "name for a lobbying attribution, the FOIA request id "
                     "for a FOIA link. Never a match phrase - a bare token "
                     "like 'Enterprise' cannot express a row-level ruling.",
    "table": "The table the correction was APPLIED to.",
    "column_unlinked": "The column whose value was removed.",
    "rows_affected": "Rows in `table` whose link was withdrawn.",
    "rows_removed": "Rows that CEASED TO EXIST in `table`. Usually 0 - an "
                    "unlink keeps the row. Non-zero only for an aggregate "
                    "whose cell has no surviving member. This figure is the "
                    "EXACT shipping allowance 62_no_regression_check.py "
                    "grants; it is not a tolerance.",
    "action": "UNLINK, REPOINT or REBUILD. Never BLACKLIST: tier X blocks a "
              "whole identifier downstream in 169_build_identifier_graph.py "
              "and would suppress the correct attributions too.",
    "repointed_to": "The entity the row was moved to. Non-blank only for "
                    "REPOINT. Blank on an UNLINK means no spine entity exists "
                    "for the true subject yet - that is a spine task, not a "
                    "licence to attach the row to the nearest name.",
    "provenance_preserved": "The columns deliberately KEPT on the corrected "
                            "rows so the correction is visible rather than "
                            "erased. A reader must be able to see that the "
                            "matcher fired, what it fired on, and who refused "
                            "it.",
    "reason": "Verbatim, in the register. Not in a document somewhere.",
}

EXTRA_READING = [
    ("This table is a list of claims Cedar Press WITHDREW.",
     "Every row records an attribution that was made, published, and then "
     "removed. It is not a list of errors found in the sources; it is a list "
     "of errors found in Cedar Press."),
    ("`entity_id` here is never a statement about that entity.",
     "It names the id that was wrongly attached. `TRBF-SROSAR-00` appearing "
     "eleven times means eleven organisations were wrongly attributed TO the "
     "Santa Rosa Rancheria Tachi Tribe, not that the tribe did anything."),
    ("A blank `repointed_to` on an UNLINK is a spine gap, not a judgement.",
     "Bristol Bay Economic Development Corporation, Bristol Bay Area Health "
     "Corporation and the Santa Rosa organisations have no entity in "
     "data/spine/cedar_entity_spine.csv. The honest state is unlinked."),
]


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def read_csv(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8-sig", errors="replace") as fh:
        return list(csv.DictReader(fh))


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(path.suffix + ".part")
    with open(part, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    if path.exists():
        bak = path.with_name(path.name + f".bak_{TODAY}_pre_{SCRIPT}")
        if not bak.exists():
            bak.write_bytes(path.read_bytes())
    os.replace(part, path)


def pct_filled(rows, col):
    if not rows:
        return "0.0"
    n = sum(1 for r in rows if (r.get(col) or "").strip())
    return f"{100 * n / len(rows):.1f}"


def guess_type(rows, col):
    vals = [(r.get(col) or "").strip() for r in rows]
    vals = [v for v in vals if v]
    if not vals:
        return "string"
    try:
        for v in vals[:500]:
            int(v)
        return "integer"
    except ValueError:
        return "string"


def main():
    print("=== Cedar Press 356: register the correction register ===\n")
    N87 = load_module(CODE / "87_build_dataset_notes.py", "notes87")
    p = CLEAN / FILE
    rows = read_csv(p)
    if not rows:
        print(f"  !! {FILE} absent or empty - SKIPPED, and that is a failure "
              f"to fix, not a clean skip.")
        return 1
    header = list(rows[0].keys())
    print(f"  {FILE}: {len(rows):,} rows, {len(header)} columns")

    missing = [c for c in header if c not in CODEBOOK]
    if missing:
        print(f"  !! {len(missing)} column(s) have NO WRITTEN DEFINITION and "
              f"are named here rather than counted: {missing}")

    FRAG.mkdir(parents=True, exist_ok=True)
    frag_rows = [{
        "dataset": DATASET, "variable": c, "type": guess_type(rows, c),
        "units": "", "pct_filled": pct_filled(rows, c), "n_rows": len(rows),
        "published": "1", "access_tier": "public",
        "description": CODEBOOK.get(c, ""), "generated": TODAY,
    } for c in header]
    fp = FRAG / f"{DATASET}.csv"
    write_csv(fp, frag_rows, ["dataset", "variable", "type", "units",
                              "pct_filled", "n_rows", "published",
                              "access_tier", "description", "generated"])
    print(f"  fragment  -> data/clean/codebook/{fp.name}  "
          f"({len(frag_rows)} vars)")

    DIST.mkdir(parents=True, exist_ok=True)
    # 87.scan() returns 8 values as of 2026-08-26 (it grew a last-date, a
    # date column and a vintage histogram). Unpacked by slice so a ninth does
    # not break this the way the fifth-to-eighth just did.
    scanned = N87.scan(p)
    n, span, n_ents, ycol, ecol = scanned[:5]
    notes = {
        "identity": {
            "dataset": DATASET, "file": FILE, "group": "00_reference",
            "vintage": TODAY, "rows": n, "columns": len(header),
            "sha256": N87.sha256(p),
            "fits_in_a_worksheet": n <= N87.XLSX_MAX,
        },
        "coverage": {
            "year_column": ycol,
            "year_span": list(span) if span else None,
            "n_years": (span[1] - span[0] + 1) if span else None,
            "entity_column": ecol, "n_entities": n_ents,
            "purpose": "Every attribution Cedar Press has WITHDRAWN, stated "
                       "as an (entity, subject) pair that must no longer "
                       "co-occur in any table, so the withdrawal can be "
                       "re-tested on every build.",
            "universe": "Corrections APPLIED and declared from 2026-08-26 "
                        "onward. Corrections made before that date are not in "
                        "here and their propagation is UNMEASURED, not clean.",
        },
        "reading": N87.READING + EXTRA_READING,
        "comparability": [
            {"break_period": "before 2026-08-26",
             "verification_status": "measured",
             "what_changed": "The register did not exist. Corrections applied "
                             "before that date - including the 841 filings "
                             "script 65 withdrew on 2026-08-06 - are not "
                             "enumerated here.",
             "effect_on_series": "An empty stretch means nobody was "
                                 "recording, never that nothing was "
                                 "corrected. Do not read a count of rows per "
                                 "year as a rate of error."},
        ],
        "research_ready": N87.RESEARCH_READY,
        "codebook": [
            {"variable": c, "type": guess_type(rows, c), "units": "",
             "pct_filled": pct_filled(rows, c),
             "description": CODEBOOK.get(c, "")} for c in header],
        "terms": N87.TERMS,
        "citation": {
            "text": f"Cedar Press, \"Corrections register\", {TODAY}. "
                    f"https://cedarpress.co",
            "url": "https://cedarpress.co",
            "note": "This file lists attributions Cedar Press made and then "
                    "withdrew. Quoting a row is quoting a correction, not a "
                    "finding about the entity named in it.",
        },
        "provenance": {
            "built_by": "354_correction_register.py, written by the scripts "
                        "that apply each correction",
            "built_date": TODAY,
        },
    }
    jp = DIST / f"{DATASET}.notes.json"
    part = jp.with_suffix(".json.part")
    part.write_text(json.dumps(notes, indent=2), encoding="utf-8")
    os.replace(part, jp)
    print(f"  notes     -> {jp.relative_to(CEDAR)}")

    try:
        md = N87.md(notes)
        mp = DIST / f"{DATASET}.notes.md"
        partm = mp.with_suffix(".md.part")
        partm.write_text(md, encoding="utf-8")
        os.replace(partm, mp)
        print(f"  notes.md  -> {mp.relative_to(CEDAR)}")
    except Exception as e:
        print(f"  (no markdown rendering: {type(e).__name__}: {e})")

    print("\n  TABLES in 25_build_publication_layer.py and SPEC in "
          "27_build_dataset_manifests.py were edited BY HAND in this session,\n"
          "  additively, per 183's precedent. Verify with "
          "`py -3 code/62_no_regression_check.py`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
