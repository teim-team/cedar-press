#!/usr/bin/env python3
r"""Cedar Press 92 — stage the NIGC-mapped properties Cedar does not hold.

`review/nigc_roster_diff_2026-08-06.csv` carries 140 `IN_NIGC_NOT_IN_CEDAR`
rows: locations NIGC's published gaming location map lists and Cedar's
`gaming_facilities.csv` does not match. 39 of them resolve to a spine entity
through `resolve_entity`; the other 101 do not.

THE CORRECTION THIS SCRIPT EXISTS TO MAKE
-----------------------------------------
**Not all 140 are missing properties. A large share are MATCH FAILURES against
rows Cedar already holds**, and appending them would manufacture duplicates in
a file whose duplicate problem is already the subject of two review queues.

The roster match is deterministic and ONE-TO-ONE: nearest-first greedy on
coordinates within 1.2 km in the same state, then identical normalised name in
the same state. Two things defeat it:

  * a name variant wider than normalisation — NIGC's `Barona Valley Ranch
    Resort and Casino` against Cedar's `Barona Resort & Casino`; NIGC's
    `Apache Gold Casino` against Cedar's `Apache Gold Casino Resort`;
  * a coordinate gap over 1.2 km, or a Cedar row with no coordinates at all.

Both leave a real Cedar property looking absent from NIGC AND an NIGC marker
looking absent from Cedar — the same property counted as two different gaps at
opposite ends of the diff. The 39 "resolved" set alone contains `Pechanga
Resort and Casino`, `Sycuan Resort & Casino`, `Tulalip Bingo` and `Harrah's
Rincon Casino and Resort`, none of which is plausibly missing from a
774-property tribal gaming file.

So this script does NOT stage 140 additions. It partitions them, using a test
that is exact string equality on a parsed city and a state — deterministic, and
NOT a name matcher:

  PROBABLE_MATCH_FAILURE_DO_NOT_ADD   a Cedar row already sits in this marker's
                                      own city and state. Adding it would
                                      duplicate. Needs a human ruling on which
                                      Cedar row it is.
  STAGE_FOR_ADDITION                  resolves to a spine entity AND no Cedar
                                      row shares its city and state.
  HOLD_UNRESOLVED                     no spine resolution. Held, not guessed —
                                      an NIGC location name is a FACILITY name
                                      and often contains no tribe name at all
                                      (`Stumps Bar & Grill, LLC`).

`data/clean/gaming_facilities.csv` is NOT touched. Nothing is appended anywhere.

Writes  review/gaming_additions_<date>.csv
"""

import csv
import importlib.util
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

_spec = importlib.util.spec_from_file_location(
    "m88", str(CEDAR / "code" / "88_gaming_property_federal_traces.py"))
M88 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M88)
read_csv, write_csv = M88.read_csv, M88.write_csv
nigc_city_state = M88.nigc_city_state


def main():
    print("=== Cedar Press 92: stage NIGC-mapped properties Cedar lacks ===\n")

    fac = read_csv(CLEAN / "gaming_facilities.csv")
    diff = read_csv(REVIEW / "nigc_roster_diff_2026-08-06.csv")
    traces = {r["facility_id"]: r
              for r in read_csv(CLEAN / "gaming_property_federal_traces.csv")}

    # Cedar rows indexed by (city, state) — exact equality on both.
    cedar_by_place = defaultdict(list)
    for f in fac:
        c = (f.get("city") or "").strip().lower()
        s = (f.get("state") or "").strip().upper()
        if c and s:
            cedar_by_place[(c, s)].append(f)
    print(f"Cedar rows with a usable (city,state): "
          f"{sum(len(v) for v in cedar_by_place.values()):,} of {len(fac):,}")

    missing = [d for d in diff if d["outcome"] == "IN_NIGC_NOT_IN_CEDAR"]
    print(f"IN_NIGC_NOT_IN_CEDAR rows: {len(missing)}\n")

    out = []
    for d in missing:
        city, st = nigc_city_state(d.get("nigc_address", ""))
        st = st or (d.get("state") or "").strip().upper()
        collisions = cedar_by_place.get((city, st), []) if city and st else []
        resolved = bool(d.get("tribe_id"))

        # A collision is stronger evidence when the colliding Cedar row is
        # itself unmatched to any NIGC marker — that is the exact shape of a
        # two-ended match failure: one property, two apparent gaps.
        unmatched_coll = [c for c in collisions
                          if traces.get(c["facility_id"], {})
                          .get("trace_nigc_gaming_location_map") == "0"]

        if unmatched_coll:
            disp = "PROBABLE_MATCH_FAILURE_DO_NOT_ADD"
            why = (f"{len(unmatched_coll)} Cedar row(s) already sit in "
                   f"{city.title()}, {st} AND carry no NIGC marker of their own. "
                   "That is the signature of one property counted as two gaps at "
                   "opposite ends of the roster diff. Adding this marker as a new "
                   "property would duplicate an existing row. Rule which Cedar "
                   "row it is; do not append.")
        elif collisions:
            disp = "PROBABLE_MATCH_FAILURE_DO_NOT_ADD"
            why = (f"{len(collisions)} Cedar row(s) already sit in "
                   f"{city.title()}, {st}, though each already carries its own "
                   "NIGC marker. A tribe can run more than one location in one "
                   "town, so this may still be a genuine addition — but it must "
                   "be ruled by a human against the specific Cedar rows named "
                   "here, not appended.")
        elif resolved:
            disp = "STAGE_FOR_ADDITION"
            why = ("Resolves to a spine entity and no Cedar row shares this "
                   "marker's city and state. NIGC's map is a published federal "
                   "universe — every entry exists by definition — so this is a "
                   "property Cedar is missing.")
        else:
            disp = "HOLD_UNRESOLVED"
            why = ("No spine resolution. An NIGC location name is a FACILITY "
                   "name and frequently contains no tribe name at all, so there "
                   "is nothing to resolve. Held rather than guessed: a false "
                   "attribution is worse than a gap.")

        out.append({
            "disposition": disp,
            "nigc_marker_id": d.get("nigc_marker_id", ""),
            "nigc_location_name": d.get("nigc_location_name", ""),
            "nigc_address": d.get("nigc_address", ""),
            "parsed_city": city.title(), "parsed_state": st,
            "nigc_region_name": d.get("nigc_region_name", ""),
            "spine_tribe_id": d.get("tribe_id", ""),
            "spine_tribe_canonical_name": d.get("tribe_canonical_name", ""),
            "entity_resolution_basis": d.get("investigate_reason", ""),
            "entity_resolution_caveat": (
                "resolve_entity CONTAINMENT tier. AGENTS.md restricts "
                "containment to resolving an owner ALREADY NAMED IN EVIDENCE. "
                "Here the tribe name appears inside NIGC's own location name "
                "(e.g. 'M&W Service of White Earth' -> White Earth). Verify "
                "that is true of this row before accepting; no dollar is keyed "
                "off it." if d.get("tribe_id") else ""),
            "cedar_rows_in_same_city_state": "|".join(
                f"{c['facility_id']}:{c['facility_name']}" for c in collisions)[:500],
            "n_cedar_rows_in_same_city_state": len(collisions),
            "n_of_those_with_no_nigc_marker": len(unmatched_coll),
            "igra_coverage_status": d.get("igra_coverage_status", ""),
            "corroborating_sources": d.get("corroborating_sources", ""),
            "evidence": why,
            "source_url": "https://www.nigc.gov/map/",
            "source_route": ("WP Google Maps admin-ajax.php map_id=6; raw at "
                             "data/raw/external/nigc/locations/"
                             "nigc_gaming_locations_map6_2026-08-06.json"),
            "fetched_date": d.get("fetched_date", ""),
            "gaming_class_recorded": "NOT_RECORDED_BY_DESIGN",
            "do_not_append_without_ruling": 1,
            "YOUR_RULING": "",
            "built_date": TODAY,
        })

    out.sort(key=lambda r: (r["disposition"], r["parsed_state"],
                            r["nigc_location_name"]))
    write_csv(REVIEW / f"gaming_additions_{TODAY}.csv", out, list(out[0].keys()))

    print("\n--- disposition ---")
    for k, v in Counter(r["disposition"] for r in out).most_common():
        print(f"  {k:36s} {v:3d}")
    print("\n--- PROBABLE_MATCH_FAILURE, the clearest cases ---")
    for r in out:
        if r["disposition"] == "PROBABLE_MATCH_FAILURE_DO_NOT_ADD" and \
                r["n_of_those_with_no_nigc_marker"]:
            print(f"  {r['nigc_location_name'][:42]:42s} <-> "
                  f"{r['cedar_rows_in_same_city_state'][:70]}")
    print("\n--- STAGE_FOR_ADDITION ---")
    for r in out:
        if r["disposition"] == "STAGE_FOR_ADDITION":
            print(f"  {r['parsed_state']}  {r['nigc_location_name'][:46]:46s} "
                  f"{r['spine_tribe_canonical_name']}")
    print("\ndata/clean/gaming_facilities.csv was NOT touched. Nothing appended.")


if __name__ == "__main__":
    main()
