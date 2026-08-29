#!/usr/bin/env python3
"""
Cedar Press - 120: make every ruling importable, whatever shape it arrived in.

THE BUG, FOUND 2026-08-08
-------------------------
`09_import_rulings.py` keys on a `review_id` column shaped `IDTYPE:IDENTIFIER`:

    rid = (r.get("review_id") or "").strip()
    if not rid or not ruling: continue        # <- silently skipped

The review WEB PAGE emits `identifier, entity_name, YOUR_RULING, notes, ...`.
No `review_id`. So **every ruling made on the page was silently skipped by the
importer** - it did not error, it did not warn, it just dropped them.

Measured consequence: of Elijah's 319 hand rulings, **176 sit in the ledger
carrying an ALGORITHMIC method** - 69 `cluster_v3`, 64 `need_v6`, 40
`unmatched`. 39 of them are still tier C (unattributed) and 57 are tier X,
despite having been ruled. They are not protected by `tier_A_ruled`, so an
algorithmic re-run could overwrite a human decision.

Nothing was lost - the inbox files are all on disk. But a ruling that does not
reach the ledger is a ruling that does not exist.

WHAT THIS DOES
--------------
Reads every `rulings_inbox_*.csv` in whatever shape, and writes ONE normalised
file that 09 can consume, with `review_id` synthesised as `UEI:<value>` or
`CAGE:<value>` by inspecting the identifier itself (UEIs are 12 alphanumeric,
CAGE 5). Original inbox files are never modified.

It does NOT decide anything. Ruling text passes through verbatim so 09's own
grammar - NOT_NATIVE, redirect-to-owner, HOLD - still governs.

    py -3 code/120_normalize_rulings.py         # write the normalised inbox
    py -3 code/120_normalize_rulings.py --check # report only, write nothing
"""

import csv
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
REVIEW = CEDAR / "review"
CLEAN = CEDAR / "data" / "clean"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

UEI = re.compile(r"^[A-Z0-9]{12}$")
CAGE = re.compile(r"^[A-Z0-9]{5}$")
EIN = re.compile(r"^\d{2}-?\d{7}$")

RULING_COLS = ("YOUR_RULING", "your_ruling", "RULING", "ruling")
ID_COLS = ("identifier", "uei", "cage", "ein", "cage_code", "awardee_uei")


def read(p):
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def id_type(v):
    v = (v or "").strip().upper()
    if UEI.match(v):
        return "UEI"
    if CAGE.match(v):
        return "CAGE"
    if EIN.match(v):
        return "EIN"
    return None


def main():
    check = "--check" in sys.argv
    print("=== Cedar Press 120: normalise rulings for import ===\n")

    out, stats, already = [], Counter(), 0
    for p in sorted(REVIEW.glob("rulings_inbox_*.csv")):
        if p.name.startswith("rulings_inbox_NORMALISED"):
            continue
        rows = read(p)
        if not rows:
            continue
        n_ok = n_skip = 0
        for r in rows:
            ruling = next((r[c].strip() for c in RULING_COLS
                           if (r.get(c) or "").strip()), "")
            if not ruling:
                continue
            rid = (r.get("review_id") or "").strip()
            if rid and ":" in rid:
                already += 1
                out.append({"review_id": rid, "YOUR_RULING": ruling,
                            "YOUR_NOTE": (r.get("notes") or
                                          r.get("YOUR_NOTE") or ""),
                            "entity_name": r.get("entity_name", ""),
                            "source_inbox": p.name})
                n_ok += 1
                continue
            # synthesise review_id from whichever identifier column is present
            made = False
            for c in ID_COLS:
                v = (r.get(c) or "").strip().upper()
                t = id_type(v)
                if t:
                    out.append({"review_id": f"{t}:{v}", "YOUR_RULING": ruling,
                                "YOUR_NOTE": (r.get("notes") or ""),
                                "entity_name": r.get("entity_name", ""),
                                "source_inbox": p.name})
                    stats[f"synthesised {t}"] += 1
                    n_ok += 1
                    made = True
                    break
            if not made:
                # a ruling on something that is not an identifier - a spine
                # collision card, a named blocker. Real, but not 09's job.
                stats["no identifier - not importable by 09"] += 1
                n_skip += 1
        print(f"  {p.name:44s} {n_ok:>4} importable, {n_skip:>3} not")

    print(f"\n  already had review_id : {already}")
    for k, v in stats.most_common():
        print(f"  {k:38s} {v}")
    print(f"  TOTAL importable rulings: {len(out):,}")

    if check:
        print("\n  --check: nothing written")
        return

    dest = REVIEW / f"rulings_inbox_NORMALISED_{TODAY}.csv"
    with open(dest, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["review_id", "YOUR_RULING",
                                           "YOUR_NOTE", "entity_name",
                                           "source_inbox"])
        w.writeheader()
        w.writerows(out)
    print(f"\n  wrote {dest.relative_to(CEDAR)}")
    print("  now run:  py -3 code/09_import_rulings.py")
    print("  then:     py -3 code/62_no_regression_check.py")


if __name__ == "__main__":
    main()
