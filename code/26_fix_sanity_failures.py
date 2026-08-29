#!/usr/bin/env python3
"""
Cedar Press - 26: Fix the two defects the publication sanity checks caught.

DEFECT 1 - the federal roll-up is still in the ownership edge file.
UEI NW2RJN8TQQW1 records as "GOVERNMENT OF THE UNITED STATES" and carries 29
children including BIA, IHS and tribally-controlled grant schools. Script 18
blocks it at propagation time, but the block lives in ONE consumer. Anyone
joining `fpds_uei_edges.csv` directly still inherits through it and attributes
federal agencies to tribes.

Fix: put the block IN THE DATA. Flag (never delete) with `blocklisted_parent`
and a reason, so every consumer sees it whether or not they read script 18.

DEFECT 2 - "orphan bill_votes" was a false positive in my own check.
The 25 rows have a BLANK bill_id, not a dangling one. They are 1978 Senate
procedural votes that never attached to a numbered bill. That is a real and
expected category, not a referential break. The check needed to distinguish
"blank" from "points at a bill that does not exist".

Fix: stamp `bill_link_status` on bill_votes so the category is explicit, and
tighten the check in script 25 to only flag genuinely dangling keys.
"""

import csv
import shutil
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
TODAY = date.today().isoformat()

# Parents that must never transmit ownership. Each needs a stated reason.
BLOCKLISTED_PARENTS = {
    "NW2RJN8TQQW1": ("federal_registrant_rollup",
                     "Records as GOVERNMENT OF THE UNITED STATES. Carries 29 children "
                     "including BIA, IHS and tribally-controlled grant schools. "
                     "Inheriting through it would attribute federal agencies to tribes."),
}


def read_csv(p):
    if not p.exists():
        return None
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(p, rows, fields):
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {p.relative_to(CEDAR)}  ({len(rows):,} rows)")


def fix_edges():
    print("[1] Blocklisting the federal roll-up in the edge data itself")
    p = CLEAN / "fpds_uei_edges.csv"
    rows = read_csv(p)
    if rows is None:
        print("  fpds_uei_edges.csv not built")
        return
    shutil.copy2(p, p.with_suffix(p.suffix + ".bak_" + TODAY))

    n = 0
    for r in rows:
        parent = (r.get("parent_uei") or "").strip().upper()
        child = (r.get("child_uei") or "").strip().upper()
        hit = BLOCKLISTED_PARENTS.get(parent) or BLOCKLISTED_PARENTS.get(child)
        if hit:
            r["blocklisted_parent"] = "1"
            r["blocklist_reason"] = hit[0]
            r["blocklist_note"] = hit[1]
            n += 1
        else:
            r["blocklisted_parent"] = ""
            r["blocklist_reason"] = ""
            r["blocklist_note"] = ""

    fields = list(rows[0].keys())
    for extra in ("blocklisted_parent", "blocklist_reason", "blocklist_note"):
        if extra not in fields:
            fields.append(extra)
    write_csv(p, rows, fields)
    print(f"  edges flagged blocklisted: {n}")
    print("  Consumers must filter `blocklisted_parent != '1'` before inheriting ownership.")


def fix_votes():
    print("\n[2] Distinguishing unlinked votes from dangling keys")
    vp, bp = CLEAN / "bill_votes.csv", CLEAN / "native_bills.csv"
    votes, bills = read_csv(vp), read_csv(bp)
    if votes is None or bills is None:
        print("  bill_votes / native_bills not built")
        return
    shutil.copy2(vp, vp.with_suffix(vp.suffix + ".bak_" + TODAY))

    known = {(b.get("bill_id") or "").strip() for b in bills}
    counts = Counter()
    for v in votes:
        bid = (v.get("bill_id") or "").strip()
        if not bid:
            # Procedural votes, amendments and motions on unnumbered vehicles.
            v["bill_link_status"] = "unlinked_no_bill_number"
            counts["unlinked"] += 1
        elif bid in known:
            v["bill_link_status"] = "linked"
            counts["linked"] += 1
        else:
            v["bill_link_status"] = "DANGLING_bill_id_not_in_native_bills"
            counts["dangling"] += 1

    fields = list(votes[0].keys())
    if "bill_link_status" not in fields:
        fields.append("bill_link_status")
    write_csv(vp, votes, fields)
    for k, n in counts.most_common():
        print(f"    {k:<10} {n:>5,}")
    if counts["dangling"]:
        print(f"  WARNING: {counts['dangling']} genuinely dangling bill_ids - investigate.")
    else:
        print("  No dangling keys. The 25 'orphans' are unlinked procedural votes, "
              "which is a real category.")


def main():
    print("=== Cedar Press: fix sanity failures ===\n")
    fix_edges()
    fix_votes()
    print("\n  Re-run code/25_build_publication_layer.py to confirm both now pass.")


if __name__ == "__main__":
    main()
