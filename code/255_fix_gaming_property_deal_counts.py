#!/usr/bin/env python3
r"""Cedar Press 255 - repair `n_deals_for_entity` in the SHIPPING property view,
IN PLACE, without rebuilding it.

WHY THIS SCRIPT EXISTS RATHER THAN A RE-RUN OF 82
--------------------------------------------------
`82_build_gaming_property_dataset.py` carried two defects that both landed in
`data/clean/gaming_properties.csv`, which SHIPS:

  1. it counted deals over `glob("deals_*_additions.csv")` - the ADDITIONS to
     the deals ledger, never the ledger itself, so 145 of 935 deal rows were
     invisible (`docs/FACT_CHECK_2026-08-06.md` finding B-1, named 2026-08-06
     and still live three weeks later);
  2. it matched a SHORT spine canonical name against a free-text party string,
     exactly - so "Saint Regis" never matched "saint regis mohawk tribe".

Both are now fixed in 82. **82 is not run to apply them.** It is a FULL REBUILD
of `gaming_properties.csv`, and that file has at least three IN-PLACE enrichers
that have written to it since the last build:

    158_merge_staged_labor_employment.py     (employment observations)
    160_sync_published_gaming_view.py        (adds rows to the published view)
    175_sync_published_property_view_entities.py  (18 hub rows keyed by 172)

AGENTS.md concurrency rule 5: a full-rebuild stage and an in-place enricher on
one file need an ordering, and the ENRICHER RUNS LAST. Running 82 here would
revert all three - the exact `133`/`168` collision that happened four times on
2026-08-26 and printed a larger row count while doing it. Repairing one column
in place is the smaller, checkable operation.

THE FIX IS A JOIN KEY, NOT A CLEVERER STRING MATCH
---------------------------------------------------
This matters more than the glob. `resolve_entity` containment has failed TEN
distinct ways in this project - CHICKASAW NATION onto Chickasaw Children's
Village carrying $2.8B onto a school; NATIVE VILLAGE OF ELIM onto Elim Native
Corporation; Sequoyah High School onto a North Carolina CDFI; a place suffix
making a tribe name a place. **A fix that widens matching can be worse than the
bug it replaces**, and "Saint Regis" ⊂ "saint regis mohawk tribe" is precisely
the containment shape.

So no name is compared here at all. `deals_classified.csv` already carries
`native_party_entity_id`, written by `126_apply_deal_party_attribution.py` from
hand rulings, agent research and the autoresolver, with each row's tier
INHERITED from its source row. That column IS a spine `tribe_id`. The property
view carries `tribe_id`. The join is exact.

It also inherits every refusal already ruled by hand, which a string match
would have re-opened - including the four containment refusals in
`review/deals_party_refused_2026-08-26.csv` (Riverside San Bernardino County
Indian Health -> "Native Health", Arizona; Department of Hawaiian Home Lands ->
an NHO; and two AGGREGATE party strings keyed to a single tribe).

WHAT THE NUMBER MEANS AFTERWARDS
---------------------------------
`n_deals_for_entity` = deal rows in `deals_classified.csv` whose
`native_party_entity_id` equals this property's `tribe_id`. 886 of the 935 rows
carry an entity id (94.8%); the 49 that do not are counted for NO entity rather
than guessed onto one. That is a narrower claim than a name collision and a
true one.

SCHEMA IS UNCHANGED ON PURPOSE. One existing column is rewritten. No column is
added, so no codebook block, notes contract or publication spec has to move,
and `62_no_regression_check.py`'s `files_with_columns_lost_vs_backup` cannot
fire.

SAFETY
------
Backup tagged with the SCRIPT NAME (concurrency rule 1), `.part` then rename,
row count and column list asserted unchanged, and the written file is
RE-READ from disk and verified (rule 4) - not trusted from the run log.

    py -3 code/255_fix_gaming_property_deal_counts.py            # apply
    py -3 code/255_fix_gaming_property_deal_counts.py --dry-run  # report only
"""

import csv
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cedar_domain as DOM   # noqa: E402  - DEALS_TRUTH

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
TODAY = date.today().isoformat()
SCRIPT = "255_fix_gaming_property_deal_counts.py"
COL = "n_deals_for_entity"

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


def read(p):
    with open(Path(p), encoding="utf-8-sig", errors="replace", newline="") as f:
        rd = csv.DictReader(f)
        return list(rd), list(rd.fieldnames or [])


def write_atomic(path, fields, rows):
    """An interruption must not look like a completion."""
    path = Path(path)
    part = path.with_suffix(path.suffix + ".part")
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    part.replace(path)


def main():
    dry = "--dry-run" in sys.argv
    print(f"=== Cedar Press 255: repair {COL} in the shipping property view "
          f"==={'  [DRY RUN]' if dry else ''}\n")

    truth = CEDAR / DOM.DEALS_TRUTH
    deals, fields_d = read(truth)
    if "native_party_entity_id" not in fields_d:
        print(f"FATAL: {DOM.DEALS_TRUTH} has no `native_party_entity_id`. "
              f"Run 126_apply_deal_party_attribution.py first. Refusing to "
              f"write - a coverage computation must RAISE on a missing "
              f"column, never print a zero.")
        return 1

    by_entity = defaultdict(int)
    unkeyed = 0
    for r in deals:
        t = (r.get("native_party_entity_id") or "").strip()
        if t:
            by_entity[t] += 1
        else:
            unkeyed += 1
    print(f"THE TRUTH: {DOM.DEALS_TRUTH}")
    print(f"  {len(deals):,} deal rows")
    print(f"  {len(deals) - unkeyed:,} carry native_party_entity_id "
          f"({(len(deals)-unkeyed)/len(deals)*100:.1f}%) across "
          f"{len(by_entity):,} distinct entities")
    print(f"  {unkeyed:,} carry none - counted for NO entity, never guessed "
          f"onto one\n")

    p = CLEAN / "gaming_properties.csv"
    rows, fields = read(p)
    n_before, fields_before = len(rows), list(fields)
    if COL not in fields:
        print(f"FATAL: {p.name} has no `{COL}` column.")
        return 1

    changed, deltas, moved = 0, Counter(), []
    old_total = new_total = 0
    for r in rows:
        tid = (r.get("tribe_id") or "").strip()
        try:
            old = int(float(r.get(COL) or 0))
        except ValueError:
            old = 0
        new = by_entity.get(tid, 0) if tid else 0
        old_total += old
        new_total += new
        if new != old:
            changed += 1
            deltas["rose" if new > old else "fell"] += 1
            moved.append((r.get("facility_name", ""), r.get("entity", ""),
                          tid, old, new))
        r[COL] = new

    print(f"{p.name}: {n_before:,} rows, {changed:,} carry a different "
          f"{COL}  ({deltas['rose']:,} rose, {deltas['fell']:,} fell)")
    print(f"  sum of {COL}: {old_total:,} -> {new_total:,}")
    print(f"  properties with at least one deal: "
          f"{sum(1 for r in rows if int(r[COL] or 0) > 0):,}\n")

    for name, ent, tid, o, n in sorted(moved, key=lambda x: -(x[4] - x[3]))[:25]:
        print(f"  {o:>4} -> {n:>4}   {tid:<16} {ent[:34]:<34} {name[:36]}")
    if len(moved) > 25:
        print(f"  ...and {len(moved) - 25} more")

    if dry:
        print("\nDRY RUN - nothing written.")
        return 0

    assert len(rows) == n_before, "row count moved - refusing to write"
    assert fields == fields_before, "column list moved - refusing to write"

    bak = p.with_suffix(p.suffix + f".bak_{TODAY}_pre_{SCRIPT}")
    if not bak.exists():
        shutil.copy2(p, bak)
    write_atomic(p, fields, rows)

    # Rule 4: verify by RE-READING, not by trusting the run log.
    back, back_fields = read(p)
    assert len(back) == n_before, f"re-read {len(back)}, expected {n_before}"
    assert back_fields == fields_before, "re-read column list differs"
    recomputed = sum(int(r[COL] or 0) for r in back)
    assert recomputed == new_total, f"re-read sum {recomputed} != {new_total}"
    bad = [r["facility_id"] for r in back
           if int(r[COL] or 0)
           != by_entity.get((r.get("tribe_id") or "").strip(), 0)]
    assert not bad, f"re-read disagrees on {len(bad)} rows: {bad[:5]}"

    print(f"\nwrote {p.name}  (backup {bak.name})")
    print(f"  re-read from disk and verified: {len(back):,} rows, "
          f"{len(back_fields)} columns, {COL} sums to {recomputed:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
