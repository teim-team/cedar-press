#!/usr/bin/env python3
"""
Cedar Press - 82: The Indian Gaming Property dataset.

ELIJAH, 2026-08-06
------------------
"we should build an indian gaming property dataset, we dont need to add revenue
 thats not there ... a lot of this isnt even in casinocity ... we can also
 update this and link to other datasets like indian country deals and add urls
 as they come up, like a living and breathing dataset ... id rather someone else
 estimate revenue than us lol"

NO REVENUE, AND THAT IS THE POSITION
------------------------------------
Tribal gaming revenue is not publicly reported per facility. We hold 493
`implied_gaming_revenue` rows and some state-payment streams, and 38 rows are
literally flagged `reverse_engineered`. Publishing an estimate would put Cedar
Press in the business of being confidently wrong, and the incumbent - Casino
City Press, selling 2017 statistics in 2026 - already occupies that ground.

So this dataset states what is MEASURED: where a property is, who owns it, when
it opened, what capacity it has carried over 33 years, and which legal
instruments authorise it. Anyone who wants a revenue estimate can build one on
top and own it.

WHAT WE HAVE THAT CASINO CITY DOES NOT
--------------------------------------
Their product is a property list with capacity. Ours links the property to the
legal and financial record around it, which is the part nobody has assembled:

  - the ENTITY, resolved through the crosswalk, with its ultimate parent
  - the BIA land-into-trust decision that made the site gaming-eligible
  - the tribal-state COMPACT and its terms
  - dated capacity history, 1994-2026, so expansion is visible rather than
    implied
  - deals, ownership events, and the federal money around the operator

LIVING AND BREATHING
--------------------
Every row carries `source_url` and `fetched_date`, and the script is idempotent -
re-running folds in new observations without disturbing what is already there.
A property that gains a URL, a compact, or a new capacity observation just gets
richer.

THE FILE THIS BUILD TREATS AS THE TRUTH
---------------------------------------
Deals: **`data/clean/deals_classified.csv`** (`cedar_domain.DEALS_TRUTH`).
Facilities: `data/clean/gaming_facilities.csv`. Entities: the spine.

TWO DEFECTS REPAIRED 2026-08-26 - both were live in the SHIPPING view
----------------------------------------------------------------------
1. **The additions glob.** `n_deals_for_entity` was counted over
   `CLEAN.glob("deals_*_additions.csv")` - the ADDITIONS to the deals ledger,
   never the ledger itself. `docs/FACT_CHECK_2026-08-06.md` finding B-1 named
   that miscount on 2026-08-06 and it was still here three weeks later, because
   the repairs to `88`, `57` and `41` each fixed only the instance that session
   tripped over. It now reads the promoted table and nothing else. See
   `cedar_domain.PROMOTED_TABLES` for the rule.

2. **A short canonical name matched exactly against a free-text party string.**
   The lookup was `deals[sp["canonical_name"].lower()]` against
   `Native_Party.lower()`, so "Saint Regis" never matched "saint regis mohawk
   tribe", "Mashantucket Pequot" never matched "mashantucket pequot tribal
   nation", and "Tolowa Dee-ni'" never matched "tolowa dee-ni' nation". The
   column under-reported across the whole view.

   **It is fixed with a JOIN KEY, not with a cleverer string match**, and that
   choice is deliberate. Widening the match here would re-run the containment
   defect that has failed ten distinct ways in this project (AGENTS.md: CHICKASAW
   NATION -> Chickasaw Children's Village, $2.8B onto a school; NATIVE VILLAGE OF
   ELIM -> Elim Native Corporation; a place suffix making a tribe name a place).
   A fix that widens matching can be worse than the bug it replaces.

   `deals_classified.csv` already carries `native_party_entity_id`, written by
   `126_apply_deal_party_attribution.py` from hand rulings, agent research and
   the autoresolver, each row's tier INHERITED from its source. That column is a
   spine `tribe_id`. The facility row carries a `tribe_id`. The join is exact,
   requires no name comparison at all, and inherits every refusal already ruled
   - including the four containment refusals in
   `review/deals_party_refused_2026-08-26.csv`.

   The count is therefore of deals ATTRIBUTED TO THE ENTITY at a recorded tier,
   which is a narrower and more honest claim than a name collision. 886 of the
   935 rows carry an entity id (94.8%); the 49 that do not are counted for no
   entity rather than guessed onto one.

Writes data/clean/gaming_properties.csv
       data/clean/gaming_property_capacity_history.csv

DO NOT RUN THIS CASUALLY. It is a FULL REBUILD of `gaming_properties.csv`, and
that file has at least three IN-PLACE enrichers - `158_merge_staged_labor_
employment.py`, `160_sync_published_gaming_view.py` and `175_sync_published_
property_view_entities.py`. Per AGENTS.md concurrency rule 5 the enrichers run
LAST, so a rebuild here means re-running all of them in order. To repair
`n_deals_for_entity` alone, use `255_fix_gaming_property_deal_counts.py`, which
patches that one column in place and touches nothing else.
"""

import csv
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cedar_domain as DOM   # noqa: E402  - DEALS_TRUTH, PROMOTED_TABLES

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
TODAY = date.today().isoformat()

# Capacity metrics that describe the PROPERTY. Revenue and payment streams are
# deliberately excluded - see the header.
CAPACITY = {"gaming_machines", "table_games", "poker_tables", "bingo_seats",
            "hotel_rooms", "restaurants", "parking_spaces",
            "gaming_square_feet", "convention_square_feet", "employees"}


def read_csv(p):
    if not Path(p).exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def main():
    print("=== Cedar Press 82: Indian Gaming Property dataset ===\n")
    spine = {r["tribe_id"]: r for r in
             read_csv(CEDAR / "data" / "spine" / "cedar_entity_spine.csv")}
    fac = read_csv(CLEAN / "gaming_facilities.csv")
    met = read_csv(CLEAN / "gaming_facility_metrics.csv")
    print(f"facilities: {len(fac):,}   metric observations: {len(met):,}")

    # ---- capacity history, and the latest value per metric ---------------
    hist, latest = [], defaultdict(dict)
    for r in met:
        m = (r.get("metric") or "").strip()
        if m not in CAPACITY:
            continue
        fid = r.get("facility_id", "")
        asof = (r.get("as_of_date") or r.get("observation_date") or "")[:10]
        try:
            v = float(r.get("value") or 0)
        except ValueError:
            continue
        hist.append({
            "facility_id": fid, "facility_name": r.get("facility_name", ""),
            "metric": m, "value": v, "unit": r.get("unit", ""),
            "as_of_date": asof,
            "as_of_date_precision": r.get("as_of_date_precision", ""),
            "value_basis": r.get("value_basis", ""),
            "source": r.get("source", ""), "built_date": TODAY,
        })
        cur = latest[fid].get(m)
        if not cur or asof > cur[1]:
            latest[fid][m] = (v, asof)

    p2 = CLEAN / "gaming_property_capacity_history.csv"
    with open(p2, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(hist[0].keys()))
        w.writeheader()
        w.writerows(hist)
    print(f"  wrote {p2.relative_to(CEDAR)}  ({len(hist):,} dated observations)")

    # ---- what links to each tribe ----------------------------------------
    compacts = defaultdict(list)
    for r in read_csv(CLEAN / "compacts.csv"):
        t = (r.get("tribe_id") or "").strip()
        if t:
            compacts[t].append(r.get("compact_id") or r.get("source_url", ""))
    land = defaultdict(list)
    for r in read_csv(CLEAN / "gaming_land_decisions.csv"):
        t = (r.get("tribe_id") or r.get("entity_id") or "").strip()
        if t:
            land[t].append({"id": r.get("decision_id", ""),
                            "date": r.get("decision_date", ""),
                            "theory": r.get("legal_theory", ""),
                            "url": r.get("federal_register_url")
                                   or r.get("source_url", "")})
    # Deals, from the PROMOTED table and keyed on the ENTITY ID. See the two
    # defects in the header - the glob and the string match were both wrong,
    # and the second is fixed with a join key rather than looser matching.
    deals, deals_rows, deals_unkeyed = defaultdict(int), 0, 0
    for r in read_csv(CEDAR / DOM.DEALS_TRUTH):
        deals_rows += 1
        tid = (r.get("native_party_entity_id") or "").strip()
        if tid:
            deals[tid] += 1
        else:
            deals_unkeyed += 1
    print(f"deals: {deals_rows:,} rows in {DOM.DEALS_TRUTH} -> "
          f"{deals_rows - deals_unkeyed:,} carry native_party_entity_id "
          f"({len(deals):,} distinct entities); {deals_unkeyed:,} carry none "
          f"and are counted for NO entity rather than guessed onto one")

    # ---- one row per property -------------------------------------------
    out, stats = [], Counter()
    for r in fac:
        fid = r.get("facility_id", "")
        tid = (r.get("tribe_id") or r.get("entity_id") or "").strip()
        sp = spine.get(tid, {})
        L = latest.get(fid, {})
        ld = land.get(tid, [])
        # The earliest land decision bounds an opening from below - a site
        # cannot host gaming before it becomes eligible. Recorded as a BOUND,
        # never converted into an opening date.
        earliest_land = min((d["date"] for d in ld if d["date"]), default="")

        if tid:
            stats["entity resolved"] += 1
        if r.get("open_date"):
            stats["has an opening date"] += 1
        if r.get("duplicate_of_facility_id"):
            stats["RULED a duplicate of another row - exclude from counts"] += 1
        if ld:
            stats["linked to a land decision"] += 1
        if compacts.get(tid):
            stats["linked to a compact"] += 1

        out.append({
            "facility_id": fid,
            "facility_name": r.get("facility_name", ""),
            "operating_company": r.get("company", ""),
            "tribe_id": tid,
            "entity": sp.get("canonical_name", r.get("tribe", "")),
            "ultimate_parent_entity": sp.get("ultimate_parent_entity_name", ""),
            "entity_class": sp.get("entity_class", ""),
            "address": r.get("address", ""), "city": r.get("city", ""),
            "state": r.get("state", ""), "postal_code": r.get("postal_code", ""),
            "latitude": r.get("latitude", ""), "longitude": r.get("longitude", ""),
            "coords_basis": r.get("coords_basis", ""),
            "property_status": r.get("property_status", ""),
            # Lifespan. `open_date_event` says WHICH event the date marks -
            # gaming commencing is not the same as a building opening.
            "open_date": r.get("open_date", ""),
            "open_date_basis": r.get("open_date_class") or r.get("open_date_basis", ""),
            "open_date_event": r.get("open_date_event", ""),
            "interim_open_date": r.get("interim_open_date", ""),
            "close_date": r.get("close_date", ""),
            # WHY THIS COLUMN IS HERE, added 2026-08-06 (session 3). This file
            # publishes one row per FACILITY ROW, and nine of those rows are
            # ruled to be the same property as another row - the contributing
            # rosters name one property twice under different naming. Without
            # this column a subscriber counting properties double-counts nine
            # casinos and cannot tell which. The row is retained (never-delete)
            # and the duplication is disclosed instead.
            #   filter to distinct properties: duplicate_of_facility_id == ""
            # `open_date_absent_reason` carries the ruling in full, including
            # the rows retired as a golf course, a grocery-brand label and a
            # three-nation name collision. See docs/GAMING_TEMPORAL_BUILD_LOG.md
            # section 9.
            "duplicate_of_facility_id": r.get("duplicate_of_facility_id", ""),
            "open_date_absent_reason": r.get("open_date_absent_reason", ""),
            "earliest_land_decision_date": earliest_land,
            "opening_bounded_below_by_land_decision": int(bool(earliest_land)),
            # Latest observed capacity, each with its own as-of date, because a
            # machine count with no date cannot be interpreted.
            **{f"latest_{m}": L.get(m, ("", ""))[0] for m in sorted(CAPACITY)},
            **{f"latest_{m}_as_of": L.get(m, ("", ""))[1] for m in sorted(CAPACITY)},
            "n_capacity_observations": sum(
                1 for h in hist if h["facility_id"] == fid),
            # Links out. This is the part Casino City does not have.
            "n_land_decisions": len(ld),
            "land_decision_urls": " | ".join(d["url"] for d in ld if d["url"])[:400],
            "land_decision_theory": " | ".join(
                sorted({d["theory"] for d in ld if d["theory"]}))[:200],
            "n_compacts": len(compacts.get(tid, [])),
            # Exact join on the spine id both sides already carry. No name
            # comparison - see defect 2 in the header.
            "n_deals_for_entity": deals.get(tid, 0) if tid else 0,
            "revenue_note": ("NOT REPORTED. Tribal gaming revenue is not "
                             "published per facility. Cedar Press states "
                             "measured capacity and does not estimate revenue."),
            "source_url": r.get("source_url", ""),
            "fetched_date": r.get("fetched_date", ""),
            "built_date": TODAY,
        })

    p1 = CLEAN / "gaming_properties.csv"
    with open(p1, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    print(f"  wrote {p1.relative_to(CEDAR)}  ({len(out):,} properties, "
          f"{len(out[0])} columns)")

    print()
    for k, v in stats.most_common():
        print(f"   {v:5,} of {len(out):,}  {k}")

    yrs = sorted({h["as_of_date"][:4] for h in hist if h["as_of_date"][:4].isdigit()})
    multi = sum(1 for f_ in out if f_["n_capacity_observations"] > 3)
    print(f"\n   capacity history spans {yrs[0]}-{yrs[-1]} ({len(yrs)} years)")
    print(f"   {multi:,} properties carry 4+ dated observations - expansion is "
          f"visible, not inferred")


if __name__ == "__main__":
    main()
