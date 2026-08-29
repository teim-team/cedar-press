#!/usr/bin/env python3
r"""Cedar Press 173 - fill `entity_id` on gaming_facility_metrics.csv for the
hub rows that 172 keyed. ADDITIVE ONLY: a blank is filled, a value is never
changed.

WHY THIS IS A SEPARATE SCRIPT
-----------------------------
`164_link_facility_hub_sources.py` deliberately does NOT touch `entity_id` on
`gaming_facility_metrics.csv` - its docstring says so in words, because
`159_extend_gaming_metrics.py` owns that column and 164 only adds the tier the
link was made at. That is the right contract and it is not changed here.

But it leaves a hole. 159 ran BEFORE the 20 unkeyed hub rows were ruled, so
1,736 metric rows sat on facilities that carried no tribe and got no
`entity_id`; and re-running 159 is not the answer, because 159 also re-pulls
Connecticut and rebuilds rows. So this script does the one thing that is
missing, by the one join that is allowed:

    metrics.facility_id -> gaming_facilities.facility_id -> that row's tribe_id

No name is matched. No coordinate is read. No existing `entity_id` is
overwritten - if 159 wrote a value, that value stands, and a disagreement
between it and the hub row is REPORTED, not resolved.

THE TIER IS NOT WRITTEN HERE. Run `164` afterwards; it inherits
`entity_tier` from the facility row for every row whose `entity_id` this script
just filled, which is exactly the "inherited, never assigned" discipline.

SAFETY: backup to .bak_<date>_pre173 (if not exists), .part then rename,
columns written in place, row count asserted unchanged.
"""

import csv
import shutil
import sys
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
LOGS = CEDAR / "logs"
TODAY = date.today().isoformat()
SCRIPT = "173_fill_gaming_metrics_entity_for_newly_keyed_hubs.py"

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


def read(p):
    with open(Path(p), encoding="utf-8-sig", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        return list(r), list(r.fieldnames or [])


def write_atomic(path, fields, rows):
    path = Path(path)
    part = path.with_suffix(path.suffix + ".part")
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    part.replace(path)


def main():
    print("=== Cedar Press 173: fill metrics entity_id from the hub ===\n")
    LOGS.mkdir(exist_ok=True)

    fac, _ = read(CLEAN / "gaming_facilities.csv")
    hub = {(r.get("facility_id") or "").strip(): r for r in fac
           if (r.get("facility_id") or "").strip()}

    p = CLEAN / "gaming_facility_metrics.csv"
    rows, fields = read(p)
    n_before = len(rows)
    filled_before = sum(1 for r in rows if (r.get("entity_id") or "").strip())

    filled, per_fac, conflicts, dangling = 0, Counter(), [], Counter()
    for r in rows:
        fid = (r.get("facility_id") or "").strip()
        eid = (r.get("entity_id") or "").strip()
        f = hub.get(fid) if fid else None
        if f is None:
            if fid:
                dangling[fid] += 1
            continue
        ftribe = (f.get("tribe_id") or "").strip()
        if not ftribe:
            continue
        if eid:
            if eid != ftribe:
                conflicts.append((fid, eid, ftribe))
            continue                      # never overwrite 159's value
        r["entity_id"] = ftribe
        r["entity_level"] = r.get("entity_level") or "facility"
        filled += 1
        per_fac[fid] += 1

    assert len(rows) == n_before, "row count moved - refusing to write"

    b = p.with_suffix(p.suffix + f".bak_{TODAY}_pre173")
    if not b.exists():
        shutil.copy2(p, b)
    write_atomic(p, fields, rows)

    after = sum(1 for r in rows if (r.get("entity_id") or "").strip())
    print(f"gaming_facility_metrics.csv  {n_before:,} rows")
    print(f"  entity_id  {filled_before:,} -> {after:,}  (+{filled:,})")
    for fid, n in per_fac.most_common():
        print(f"    {fid:<16} +{n:>6,}  {hub[fid].get('facility_name','')}"
              f"  [tier {hub[fid].get('entity_tier','')}]")
    if conflicts:
        print(f"\n  {len(conflicts)} rows where 159's entity_id DISAGREES with "
              f"the hub row. NOT overwritten, reported:")
        for c in sorted(set(conflicts))[:20]:
            print("   ", c)
    if dangling:
        print(f"\n  {sum(dangling.values()):,} rows carry a facility_id that is "
              f"not in the hub ({len(dangling)} distinct) - left alone, never "
              f"minted as a property.")
    print(f"\n  backup {b.name}")
    print("\nNEXT: re-run `py -3 code/164_link_facility_hub_sources.py` so the "
          "inherited entity_tier lands on the rows just filled.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
