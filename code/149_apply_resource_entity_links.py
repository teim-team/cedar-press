#!/usr/bin/env python3
"""
Cedar Press - 146: apply the tier-A resource revenue entity links, in place.

WHY
---
`code/137_link_resource_revenue_entities.py` resolved 127 named-but-unlinked
resource revenue rows to a single spine entity at tier A, and wrote them as
proposals. Proposals that never get applied are the ruling-import defect all
over again - the answer computed and left beside the file that needs it.

Linkage goes 607 -> 734 of 10,482 (5.8% -> 7.0%).

THE CEILING IS NOT OUR FAILURE
------------------------------
9,516 unlinked rows carry NO recipient name at all, and 9,238 of those are
`ONRR_NRRD_monthly_revenue`. ONRR publishes **no tribe-name field for any land
class**, 0 of 9,238 Native rows carry geography, and "Osage" appears zero times
in the entire feed despite that estate having a single owner. Those rows are
WITHHELD at source - unlinkable by anyone outside ONRR.

So the honest ceiling is **966 rows (9.2%)**, and this moves us to 7.0% of it.
Reporting 7% without that denominator would read as a quality problem. It is a
statutory one.

WHAT IT APPLIES, AND WHAT IT WILL NOT
-------------------------------------
Applies ONLY `confidence_tier == A` with a `proposed_entity_id` that resolves to
the spine. Everything else stays a proposal:

- **106 Osage headright rows are NOT applied.** Those payments run to individual
  headright holders, and the Nation's own auditor states the distributions "are
  not received by the Nation." Attributing them to the tribal government would
  be a category error worth six figures a year.
- **66 multi-party rows are NOT applied.** "Village corporations and at-large
  shareholders" names a CLASS, not an entity. Splitting a payment across an
  unnamed class invents rows nobody reported.
- **60 statutory funds stay at tier B.** The Uintah Basin and Navajo
  Revitalization Funds are state-created; the beneficiary tribe is implied but
  the instrument was not read. That needs a ruling, never an assertion.

    py -3 code/146_apply_resource_entity_links.py --check
    py -3 code/146_apply_resource_entity_links.py
"""

import csv
import glob
import shutil
import sys
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
SPINE = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"
SRC = CLEAN / "resource_revenue.csv"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


def load(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def main():
    check = "--check" in sys.argv
    print("=== 146: apply tier-A resource entity links ===\n")

    props = []
    for f in sorted(glob.glob(str(REVIEW / "resource_revenue_entity_proposals_*.csv"))):
        props = load(f)
        src = Path(f).name
    if not props:
        print("  no proposals found - run 137 first")
        return

    spine_ids = {r["tribe_id"] for r in load(SPINE)}
    rows = load(SRC)
    fields = list(rows[0])
    before = sum(1 for r in rows if (r.get("recipient_entity_id") or "").strip())

    apply_by_event = {}
    refused = Counter()
    for p in props:
        tier = (p.get("confidence_tier") or "").strip()
        tid = (p.get("proposed_entity_id") or "").strip()
        cls = (p.get("recipient_class") or "").strip()
        if tier != "A":
            refused[f"not tier A ({cls or 'no class'})"] += 1
            continue
        if not tid:
            refused["tier A but no entity id"] += 1
            continue
        if tid not in spine_ids:
            refused["REFUSED - entity id not in spine"] += 1
            continue
        eid = (p.get("resource_revenue_event_id") or "").strip()
        if eid:
            apply_by_event[eid] = (tid, p.get("proposed_name", ""))

    print(f"  proposals            : {len(props):,}  ({src})")
    print(f"  applying (tier A)    : {len(apply_by_event):,}")
    for k, v in refused.most_common():
        print(f"    {k:44s} {v:>4}")

    changed = 0
    for r in rows:
        eid = (r.get("resource_revenue_event_id") or "").strip()
        hit = apply_by_event.get(eid)
        if not hit:
            continue
        if (r.get("recipient_entity_id") or "").strip():
            continue                      # never overwrite an existing link
        r["recipient_entity_id"] = hit[0]
        if not (r.get("recipient_entity_name") or "").strip():
            r["recipient_entity_name"] = hit[1]
        changed += 1

    after = sum(1 for r in rows if (r.get("recipient_entity_id") or "").strip())
    nameless = sum(1 for r in rows
                   if not (r.get("recipient_entity_name") or "").strip()
                   and not (r.get("recipient_entity_id") or "").strip())
    ceiling = len(rows) - nameless
    print(f"\n  rows changed         : {changed:,}")
    print(f"  linked  {before:,} -> {after:,}  ({100*after/len(rows):.1f}%)")
    print(f"  honest ceiling       : {ceiling:,} ({100*ceiling/len(rows):.1f}%) "
          f"- the rest is ONRR withholding, not our gap")
    print(f"  entities             : "
          f"{len({r['recipient_entity_id'] for r in rows if r.get('recipient_entity_id')})}")

    if check:
        print("\n  --check: nothing written")
        return
    if after < before:
        print("\n  *** linkage FELL - refusing to write ***")
        return

    bak = SRC.with_suffix(f".csv.bak_{TODAY}_pre146")
    if not bak.exists():
        shutil.copy2(SRC, bak)
        print(f"\n  backed up -> {bak.name}")
    with open(SRC, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {SRC.name}  ({len(rows):,} rows, unchanged count)")
    print("\n  now run:  py -3 code/62_no_regression_check.py")


if __name__ == "__main__":
    main()
