#!/usr/bin/env python3
"""
Cedar Press - 126: link deals to the entity spine, IN PLACE.

THE PROBLEM
-----------
`deals_classified.csv` holds 790 deals. `Native_Party` is filled on all 790.
**Zero carry an entity id.** Meanwhile four separate files hold the resolution
work, already done:

    deals_party_attribution.csv         56 rows   Elijah's rulings
    deals_party_attribution_agent.csv  530 rows   agent research
    deals_party_autoresolved.csv       443 rows   autoresolved
    deals_party_matches.csv            481 rows   PROPOSED ONLY - excluded

Same shape as the ruling-import defect: the answers were computed and never
written back to the file that needs them.

WHY deals_party_matches.csv IS EXCLUDED
---------------------------------------
Its id column is literally named `proposed_tribe_id` - candidates, not
decisions - and it carries a DIFFERENT id scheme. Measured 2026-08-12:

    Arctic Slope Regional Corporation
      deals_party_autoresolved.csv -> ANRC-ARCSLO-00   in spine: TRUE
      deals_party_matches.csv      -> ANC-0003         in spine: FALSE

Only 441 of its 481 ids resolve to the spine (92%). The other three files
resolve at 100%. Merging it would inject 40 dead ids and, worse, would
overwrite correct ids with a stale scheme wherever it disagreed.

PRECEDENCE - a human ruling is never overwritten by a machine
-------------------------------------------------------------
    1. deals_party_attribution.csv        (Elijah's rulings)
    2. deals_party_attribution_agent.csv  (agent research, carries tier)
    3. deals_party_autoresolved.csv       (autoresolved)

First writer wins. Lower-precedence files may only FILL a blank.

WHAT IT REFUSES TO DO
---------------------
- **It does not touch `Announced_Value_USD`.** Attributing a deal to an entity
  is not the same as attributing its VALUE to that entity - a joint venture or a
  minority stake is not a dollar the tribe received. Rows whose attribution
  source carries `value_attribution_caution` get that flag copied through so the
  caution travels with the link.
- **It does not collapse ownership and service.** `party_role` and
  `parent_native_entity` are carried verbatim; nothing is inferred.
- **It adds columns, never overwrites existing ones.** `deals_classified.csv`
  already has a `native_party_role` column from the classifier; this writes
  `native_party_*` fields under distinct names so neither clobbers the other.

    py -3 code/126_apply_deal_party_attribution.py --check
    py -3 code/126_apply_deal_party_attribution.py
"""

import csv
import re
import shutil
import sys
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
SPINE = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"
DEALS = CLEAN / "deals_classified.csv"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

# highest precedence first
SOURCES = [
    ("deals_party_attribution.csv", "elijah_ruling"),
    ("deals_party_attribution_agent.csv", "agent_research"),
    ("deals_party_autoresolved.csv", "autoresolved"),
]
EXCLUDED = ("deals_party_matches.csv",
            "proposed ids, different scheme, 40 of 481 not in spine")

NEW_COLS = [
    "native_party_entity_id",
    "native_party_canonical_name",
    "native_party_parent_entity",
    "native_party_attribution_tier",
    "native_party_attribution_method",
    "native_party_attribution_source",
    "native_party_value_caution",
]


def load(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def main():
    check = "--check" in sys.argv
    print("=== 126: link deals to the spine (in place) ===\n")

    spine_ids = {r["tribe_id"] for r in load(SPINE)}
    deals = load(DEALS)
    if not deals:
        print("  deals_classified.csv missing or empty - refusing")
        return
    fields = list(deals[0])
    print(f"  deals            : {len(deals):,}")
    print(f"  spine entities   : {len(spine_ids):,}")
    print(f"  EXCLUDED         : {EXCLUDED[0]} - {EXCLUDED[1]}\n")

    # ---- build the lookup, precedence-respecting -------------------------
    lookup, provenance = {}, Counter()
    dropped_bad_id = Counter()
    for fname, method in SOURCES:
        rows = load(CLEAN / fname)
        added = 0
        for r in rows:
            party = norm(r.get("native_party"))
            if not party:
                continue
            tid = (r.get("tribe_id") or "").strip()
            if not tid:
                continue
            if tid not in spine_ids:
                dropped_bad_id[fname] += 1
                continue
            if party in lookup:          # first writer wins
                continue
            lookup[party] = {
                "native_party_entity_id": tid,
                "native_party_canonical_name": r.get("canonical_name", ""),
                "native_party_parent_entity": r.get("parent_native_entity", ""),
                "native_party_attribution_tier": r.get("confidence_tier", ""),
                "native_party_attribution_method": (
                    r.get("match_method") or method),
                "native_party_attribution_source": fname,
                "native_party_value_caution": r.get(
                    "value_attribution_caution", ""),
            }
            added += 1
        provenance[fname] = added
        print(f"  {fname:38s} contributed {added:>4} parties")
    if dropped_bad_id:
        for k, v in dropped_bad_id.items():
            print(f"    REFUSED {v} rows from {k}: tribe_id not in spine")
    print(f"\n  distinct parties resolvable: {len(lookup):,}")

    # ---- apply ------------------------------------------------------------
    linked = 0
    unmatched = Counter()
    for d in deals:
        for c in NEW_COLS:
            d.setdefault(c, "")
        hit = lookup.get(norm(d.get("Native_Party")))
        if hit:
            d.update(hit)
            linked += 1
        elif (d.get("Native_Party") or "").strip():
            unmatched[d["Native_Party"].strip()] += 1

    tiers = Counter(d["native_party_attribution_tier"] for d in deals if
                    d.get("native_party_entity_id"))
    ents = {d["native_party_entity_id"] for d in deals
            if d.get("native_party_entity_id")}
    print(f"\n  deals linked      : {linked:,} of {len(deals):,} "
          f"({100*linked/len(deals):.1f}%)")
    print(f"  distinct entities : {len(ents):,}")
    print(f"  tier distribution : {dict(tiers)}")
    print(f"  unmatched parties : {len(unmatched):,} distinct, "
          f"{sum(unmatched.values()):,} deals")
    caution = sum(1 for d in deals if d.get("native_party_value_caution"))
    print(f"  carrying value caution: {caution:,}")

    if check:
        print("\n  --check: nothing written")
        print("  top unmatched:")
        for n, c in unmatched.most_common(15):
            print(f"    {c:>3}  {n[:66]}")
        return

    bak = DEALS.with_suffix(f".bak_{TODAY}_pre126")
    if not bak.exists():
        shutil.copy2(DEALS, bak)
        print(f"\n  backed up -> {bak.name}")

    out_fields = fields + [c for c in NEW_COLS if c not in fields]
    with open(DEALS, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=out_fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(deals)
    print(f"  wrote {DEALS.name}  ({len(deals):,} rows, "
          f"{len(out_fields)} cols)")

    if unmatched:
        dest = REVIEW / f"deals_party_unmatched_{TODAY}.csv"
        with open(dest, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["native_party", "n_deals"])
            w.writerows(unmatched.most_common())
        print(f"  wrote {dest.name}  ({len(unmatched):,} parties to rule)")

    print("\n  now run:  py -3 code/62_no_regression_check.py")


if __name__ == "__main__":
    main()
