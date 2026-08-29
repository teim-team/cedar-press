#!/usr/bin/env python3
r"""Cedar Press 175 - carry the 172 hub rulings into the PUBLISHED property view.

`160_sync_published_gaming_view.py`, in its own words:

    "**Fixing the internal file and leaving the published one wrong is worse
    than not fixing it**, because the disclosure and the artefact then live in
    different files."

That applies here. `172` keyed 18 hub rows in `gaming_facilities.csv`;
`data/clean/gaming_properties.csv` is the 784-row view that SHIPS, it carries
its own copy of `tribe_id`, `entity`, `entity_class`, `ultimate_parent_entity`
and every tribe-keyed roll-up, and all of those are still blank or zero on
those 18 rows.

WHAT IS PATCHED, AND ONLY FOR THE 18 ROWS 172 KEYED
---------------------------------------------------
Every field below is a TRIBE-KEYED derivation, so each was computed from a
blank tribe_id and is stale BY CONSTRUCTION - not merely absent. Each is
recomputed with `82_*`'s own derivation, read out of that script, so these rows
agree with the other 766 rather than being better than them:

    tribe_id                                  <- gaming_facilities.tribe_id
    entity / ultimate_parent_entity / entity_class   <- the spine row
    n_compacts                                <- compacts.csv by tribe_id
    n_land_decisions / land_decision_urls /
      land_decision_theory /
      earliest_land_decision_date /
      opening_bounded_below_by_land_decision  <- gaming_land_decisions.csv
    n_deals_for_entity                        <- 82's own lookup, see below

NOTHING ELSE IS TOUCHED. No date, no capacity, no row outside the 18.

TWO DEFECTS IN 82 THAT WERE REPRODUCED DELIBERATELY - BOTH NOW FIXED AT SOURCE
------------------------------------------------------------------------------
This section read "reproduced deliberately, NOT fixed" until 2026-08-26. The
reasoning was right and is kept: making 18 rows correct in a way the other 766
are not would be a worse file, so 82's behaviour was copied verbatim and both
defects were QUEUED BY NAME instead of silently improved here. Naming them is
what got them fixed.

**Both are now repaired in `82_build_gaming_property_dataset.py`, and this
script copies the repaired behaviour** - so it still agrees with the other 766
rows rather than being better than them. The live file was patched for this
column by `code/255_fix_gaming_property_deal_counts.py`, in place and one
column only, because rebuilding through 82 would revert this script and two
other in-place enrichers.

1. **`n_deals_for_entity` matches a SHORT canonical name against a free-text
   party string, exactly.** `deals[sp["canonical_name"].lower()]`. So
   "Mashantucket Pequot" never matches "mashantucket pequot tribal nation",
   "Saint Regis" never matches "saint regis mohawk tribe", and
   "Tolowa Dee-ni'" never matches "tolowa dee-ni' nation". Of the 13 entities
   keyed here, deals exist for 7 and exactly ONE - Comanche Nation - matches.
   The column under-reports across the whole view, not just here.
   **FIXED with a JOIN KEY, not a looser string match**, and that choice is
   deliberate: `deals_classified.csv` carries `native_party_entity_id`, which
   IS a spine `tribe_id`, and so does the facility row. Widening the match
   instead would have re-run the containment defect that has failed ten
   distinct ways in this project - a fix that widens matching can be worse
   than the bug.
2. **82 globs `deals_*_additions.csv` only.** That is the miscount
   `docs/FACT_CHECK_2026-08-06.md` finding B-1 identified and
   `START_HERE.md` records as repaired in `88` and `57` - it omits the 131
   rows that come from the two root ledgers, and `deals_classified.csv` is
   never read. 82 was missed.
   **FIXED**: the truth is `cedar_domain.DEALS_TRUTH` =
   `data/clean/deals_classified.csv`, 935 rows measured 2026-08-26.

SAFETY: backup to .bak_<date>_pre175 (if not exists), .part then rename, row
count and column list asserted unchanged, and a facility_name guard on every
patched row.
"""

import csv
import shutil
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cedar_domain as DOM   # noqa: E402  - DEALS_TRUTH

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
LOGS = CEDAR / "logs"
TODAY = date.today().isoformat()
SCRIPT = "175_sync_published_property_view_entities.py"

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
    print("=== Cedar Press 175: sync the published property view ===\n")

    ruling_log = LOGS / f"172_facility_hub_rulings_{TODAY}.csv"
    if not ruling_log.exists():
        print(f"FATAL: {ruling_log.name} is absent. Run 172 first.")
        return 1
    ruled, _ = read(ruling_log)
    target = {r["facility_id"]: r for r in ruled}
    print(f"rulings to carry across: {len(target)}")

    fac, _ = read(CLEAN / "gaming_facilities.csv")
    hub = {r["facility_id"]: r for r in fac}
    spine = {r["tribe_id"]: r for r in read(SPINE / "cedar_entity_spine.csv")[0]}

    compacts = defaultdict(list)
    for r in read(CLEAN / "compacts.csv")[0]:
        t = (r.get("tribe_id") or "").strip()
        if t:
            compacts[t].append(r.get("compact_id") or r.get("source_url", ""))
    land = defaultdict(list)
    for r in read(CLEAN / "gaming_land_decisions.csv")[0]:
        t = (r.get("tribe_id") or r.get("entity_id") or "").strip()
        if t:
            land[t].append({"date": r.get("decision_date", ""),
                            "theory": r.get("legal_theory", ""),
                            "url": r.get("federal_register_url")
                                   or r.get("source_url", "")})
    # 82's lookup, repaired - see the docstring. Promoted table, entity-id
    # join, no name comparison anywhere.
    deals = defaultdict(int)
    for r in read(CEDAR / DOM.DEALS_TRUTH)[0]:
        t = (r.get("native_party_entity_id") or "").strip()
        if t:
            deals[t] += 1

    p = CLEAN / "gaming_properties.csv"
    rows, fields = read(p)
    n_before = len(rows)
    patched, skipped = 0, []
    for r in rows:
        fid = (r.get("facility_id") or "").strip()
        if fid not in target:
            continue
        f = hub.get(fid)
        if f is None or (f.get("facility_name") or "") != (
                r.get("facility_name") or ""):
            print(f"FATAL: {fid} facility_name disagrees between the hub and "
                  f"the view. Refusing to write.")
            return 1
        if (r.get("tribe_id") or "").strip():
            skipped.append(fid)
            continue
        tid = (f.get("tribe_id") or "").strip()
        sp = spine.get(tid, {})
        if not sp:
            print(f"FATAL: {fid}: {tid} is not in the spine.")
            return 1
        ld = land.get(tid, [])
        earliest = min((d["date"] for d in ld if d["date"]), default="")
        r["tribe_id"] = tid
        r["entity"] = sp.get("canonical_name", "")
        r["ultimate_parent_entity"] = sp.get("ultimate_parent_entity_name", "")
        r["entity_class"] = sp.get("entity_class", "")
        r["n_compacts"] = len(compacts.get(tid, []))
        r["n_land_decisions"] = len(ld)
        r["land_decision_urls"] = " | ".join(
            d["url"] for d in ld if d["url"])[:400]
        r["land_decision_theory"] = " | ".join(
            sorted({d["theory"] for d in ld if d["theory"]}))[:200]
        r["earliest_land_decision_date"] = earliest
        r["opening_bounded_below_by_land_decision"] = int(bool(earliest))
        r["n_deals_for_entity"] = deals.get(tid, 0)
        patched += 1
        print(f"  {fid:<18} {tid:<16} {r['entity']:<28} "
              f"compacts={r['n_compacts']:<3} land={r['n_land_decisions']:<3} "
              f"deals={r['n_deals_for_entity']}")

    assert len(rows) == n_before, "row count moved - refusing to write"
    b = p.with_suffix(p.suffix + f".bak_{TODAY}_pre175")
    if not b.exists():
        shutil.copy2(p, b)
    write_atomic(p, fields, rows)

    have = sum(1 for r in rows if (r.get("tribe_id") or "").strip())
    print(f"\nwrote {p.name} (backup {b.name})")
    print(f"  rows with tribe_id  {have - patched:,} -> {have:,}")
    if skipped:
        print(f"  already carried a tribe_id, left alone: {skipped}")
    print(f"  rows still without one: {len(rows) - have} "
          f"(the two 172 refused, by ruling)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
