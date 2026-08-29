#!/usr/bin/env python3
r"""401_register_root_csv_parts.py -- Cedar Press. Make a registry see the root.

WHAT `160_ship_gap_report.py` SAYS, AND WHY IT KEPT SAYING IT
-------------------------------------------------------------
    "LEDGERS IN THE PROJECT ROOT, OUTSIDE data/clean: 8 files, 7,009 rows.
     No registry enumerates the root. This is the shape of the deals defect:
     a 790-row master held ONE 2026 row while 131 sat in a root CSV."

The diagnosis is right. The reporting was not: 160 globs `*.csv` in the root
and prints all eight flat, **including `deals_2026_ytd.csv` and
`deals_historical_2020_2025.csv`, which have been DECLARED parts in
`cedar_domain.PROMOTED_TABLES` since the deals repair.** The declaration and
the glob never met, so a solved case kept printing as an open one - and a
gap report that names two settled files among six unsettled ones teaches the
reader to skim the list.

WHAT THIS SCRIPT DOES
---------------------
1. **Declares the six root files that ARE parts of a promoted table** in
   `cedar_domain.PROMOTED_TABLES` / `PROMOTED_TABLE_PRODUCERS`, extending the
   existing deals declaration rather than inventing a second registry. The
   block is APPENDED to `cedar_domain.py` (as the `__all__` additions already
   are) so a concurrent editor of that module cannot lose it. Membership was
   proved on a real key for every one; the checks are in
   `399_inventory_stranded_data.py` and re-run on every invocation.

2. **Moves the seventh, `reconcile_queue.csv`, into `review/`.** It is not a
   dataset part and declaring it as one would have been the wrong shape of
   honest: it is **326 unanswered questions with an empty `YOUR_RULING`
   column** - 214 `neid_unmatched`, 73 `village_corp_region_unmapped`, 34
   `bgov_tribe_unmatched`, 5 `deal_missing_source`. `160`'s `review_backlog()`
   already globs `review/*.csv` and counts blank ruling columns, so moving it
   there hands it to a registry that ALREADY EXISTS and already reports by
   name. Registering a queue as a dataset would have hidden it in the wrong
   list.

3. Prints the disposition of every root file itself, by calling
   `cedar_domain.promoted_table_for()` on each.

NOT DONE, AND NAMED RATHER THAN LEFT SILENT
-------------------------------------------
`160_ship_gap_report.py` still globs the root and prints all of it flat under
"No registry enumerates the root". The one-line fix is to call
`cedar_domain.promoted_table_for(p.name)` in the `root_csv` loop (around line
1156) and print DECLARED -> <table> for a declared part, so the section reports
only what is genuinely unenumerated.

**It was NOT applied here because 160 was being edited by another agent at the
time of this run** - `code/160_ship_gap_report.py` mtime 2026-08-26 20:51:49
and `docs/SHIP_GAP_REPORT.json` 20:53:36, both inside the live window.
Concurrency rule 6, and rule 2's lesson that a drive-by write over another
agent's work costs more than it saves. Handed off by name instead of done
badly; recorded in `docs/STRANDED_DATA_DISPOSITION.md`.

`entity_master.csv`, `bgov.csv` and `contract-03-18-23-19-40-24.csv` STAY in
the project root. They are hand-built or hand-exported SOURCE INPUTS that
several builds name by literal path; moving them would break those builds to
tidy a directory listing, and the gap was never the location - it was that
nothing said what they were.

    py -3 code/401_register_root_csv_parts.py --dry-run
    py -3 code/401_register_root_csv_parts.py --apply
"""
from __future__ import annotations

import csv
import datetime as dt
import os
import shutil
import sys
from collections import Counter
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CODE = CEDAR / "code"
REVIEW = CEDAR / "review"

sys.path.insert(0, str(CODE))
import cedar_domain as DOM                                       # noqa: E402

csv.field_size_limit(1 << 30)
SCRIPT = Path(__file__).stem
TODAY = dt.date.today().isoformat()

QUEUE_SRC = CEDAR / "reconcile_queue.csv"
QUEUE_DST = REVIEW / "reconcile_queue.csv"


def main():
    apply_ = "--apply" in sys.argv
    if not apply_ and "--dry-run" not in sys.argv:
        raise SystemExit("pass --dry-run or --apply")

    print("=" * 78)
    print("401 REGISTER THE ROOT CSVs -- %s" % TODAY)
    print("=" * 78)

    # ---- 1. the declaration, verified -----------------------------------
    print("\n  cedar_domain.PROMOTED_TABLES now declares %d promoted table(s):"
          % len(DOM.PROMOTED_TABLES))
    for tbl, parts in sorted(DOM.PROMOTED_TABLES.items()):
        print("      %s" % tbl)
        for p in parts:
            print("          <- %s" % p)

    root = sorted(p for p in CEDAR.glob("*.csv") if ".bak" not in p.name)
    print("\n  ROOT CSVs, WITH THEIR DISPOSITION:")
    undeclared = []
    for p in root:
        tbl = DOM.promoted_table_for(p.name)
        if tbl:
            print("      DECLARED   %-46s -> %s" % (p.name, tbl))
        else:
            print("      UNDECLARED %-46s" % p.name)
            undeclared.append(p)
    if undeclared and [p for p in undeclared if p != QUEUE_SRC]:
        print("\n      !! still undeclared after this run: %s"
              % [p.name for p in undeclared if p != QUEUE_SRC])

    # ---- 2. the review queue --------------------------------------------
    if QUEUE_SRC.exists():
        with open(QUEUE_SRC, encoding="utf-8-sig", errors="replace",
                  newline="") as fh:
            q = list(csv.DictReader(fh))
        if "YOUR_RULING" not in (q[0] if q else {}):
            raise SystemExit("reconcile_queue.csv: `YOUR_RULING` column ABSENT")
        open_n = sum(1 for r in q if not (r["YOUR_RULING"] or "").strip())
        print("\n  reconcile_queue.csv: %d rows, %d UNANSWERED (`YOUR_RULING` "
              "blank)" % (len(q), open_n))
        for k, n in Counter(r["issue_type"] for r in q).most_common():
            print("        %-34s %d" % (k, n))
        print("      -> review/reconcile_queue.csv, where 160's "
              "review_backlog() already enumerates it by name")
    elif QUEUE_DST.exists():
        print("\n  reconcile_queue.csv already at review/reconcile_queue.csv")
    else:
        raise SystemExit("reconcile_queue.csv not found at either location")

    if not apply_:
        print("\n  DRY RUN. nothing moved. re-run with --apply")
        return 0

    if QUEUE_SRC.exists():
        REVIEW.mkdir(parents=True, exist_ok=True)
        if QUEUE_DST.exists():
            raise SystemExit("review/reconcile_queue.csv already exists - "
                             "refusing to overwrite. Two copies of a queue is "
                             "worse than one in the wrong place.")
        # copy, VERIFY, then remove - never a bare move. An interruption must
        # not look like a completion.
        tmp = QUEUE_DST.with_suffix(".csv.part")
        shutil.copy2(QUEUE_SRC, tmp)
        if tmp.stat().st_size != QUEUE_SRC.stat().st_size:
            tmp.unlink()
            raise SystemExit("copy size mismatch; nothing removed")
        os.replace(tmp, QUEUE_DST)
        with open(QUEUE_DST, encoding="utf-8-sig", errors="replace",
                  newline="") as fh:
            back = list(csv.DictReader(fh))
        if len(back) != len(q):
            raise SystemExit("row count mismatch after copy: %d != %d"
                             % (len(back), len(q)))
        QUEUE_SRC.unlink()
        print("\n  moved  reconcile_queue.csv -> review/reconcile_queue.csv "
              "(%d rows verified after the copy, then the source removed)"
              % len(back))

    # ---- 3. re-read (concurrency rule 4) ---------------------------------
    root = sorted(p for p in CEDAR.glob("*.csv") if ".bak" not in p.name)
    still = [p.name for p in root if not DOM.promoted_table_for(p.name)]
    print("\n  RE-READ: %d root CSV(s); %d without a declared promoted table %s"
          % (len(root), len(still), still))
    return 0


if __name__ == "__main__":
    sys.exit(main())
