#!/usr/bin/env python3
r"""Cedar Press 158 - two edits to `data/clean/gaming_facilities.csv`.

Both are edits the file has needed since it was built, and they are done in ONE
pass so the file is backed up and written once.

-------------------------------------------------------------------------------
EDIT 1 - WITHDRAW FABRICATED DAY PRECISION FROM `open_date` AND `close_date`
-------------------------------------------------------------------------------
The file already knows the truth and does not tell it in the shipping field.
`open_date_precision` types 288 rows `year` and 162 `month`, and
`open_date_not_before`/`_not_after` carry the honest interval - but `open_date`
itself still holds a full `YYYY-MM-DD`, because the build rule was "the source
value is never modified".

That rule is right for a raw column and wrong for a published one. The vendor's
`YYYY-12-31` is its YEAR placeholder and `YYYY-MM-15` its MID-MONTH placeholder;
148 rows land on day 31 and 148 on day 15, which is not what real opening dates
do. Shipped as-is, a subscriber reads a day-precision opening date that no
source states, and the disclosure sits two columns away.

So every value whose own `*_precision` says `year` or `month` is RE-TYPED to
that precision - `1992-12-31` becomes `1992`, `1985-04-15` becomes `1985-04`.
Nothing is lost: the verbatim source string moves to a new internal column
`*_source_value_verbatim`, and `*_not_before` / `*_not_after` are untouched and
remain the columns to parse.

**This is a downgrade, not a re-sourcing.** 298 of the 304 placeholder-shaped
values come from the Casino City vendor roster, which by standing rule may be
read for QA and never published - so re-sourcing them means finding an
independent source for the DATE, not merely a better day. Those are queued, not
invented.

-------------------------------------------------------------------------------
EDIT 2 - APPEND THE NIGC LOCATIONS CEDAR GENUINELY LACKS
-------------------------------------------------------------------------------
`code/157` links 442 of NIGC's 496 current locations to Cedar rows and rules 95
of the 140 staged 2026-08-06 additions as already held. The remainder is split
here by DUPLICATE RISK, measured rather than judged:

  a token is RARE if it appears in at most 5 of Cedar's 774 facility names.
  If any rare token of the NIGC location name appears in ANY Cedar facility
  name anywhere in the country -> QUEUE_POSSIBLE_DUPLICATE.
  Otherwise -> APPEND.

The check is NATIONWIDE on purpose. NIGC files `Cherokee Casino - West Siloam
Springs` under a **Siloam Springs, ARKANSAS** mailing address while the casino
is in West Siloam Springs, OKLAHOMA. A same-state duplicate check would have
found no Arkansas row, called it new, and created a second Cedar row for a
property Cedar already holds in Oklahoma.

TRIBE ATTRIBUTION ON AN APPENDED ROW is only made when it cannot be wrong: it
is made only where EVERY Cedar row already in that city and state belongs to
one tribe, and it is written at tier B with that reasoning in
`entity_match_basis`. An NIGC location name is a FACILITY name and frequently
contains no tribe name at all, so nothing is resolved from the name. Where the
town has no Cedar row, the tribe is left BLANK - a gap, which is recoverable,
rather than a false attribution, which is not.

NO OPENING DATE is written for an appended row. NIGC's map states that a
location is a regulated gaming operation now; it states nothing about when it
opened. `open_date_class = absent`, `open_date_absent_reason` says so.

SAFETY
  * `gaming_facilities.csv` is backed up to `.bak_<date>_pre158` first.
  * IDs come from `code/cedar_ids.allocate("CEDAR-FAC")` under its file lock -
    never minted inline.
  * Run `py -3 code/62_no_regression_check.py` afterwards.
"""

import csv
import importlib.util
import json
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
LOGS = CEDAR / "logs"
TODAY = date.today().isoformat()
NIGC_URL = "https://www.nigc.gov/map/"

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


M157 = _load("m157", CEDAR / "code" / "157_reconcile_nigc_roster.py")
IDS = _load("cedar_ids", CEDAR / "code" / "cedar_ids.py")
read_csv, write_csv, norm, core_key = (M157.read_csv, M157.write_csv,
                                       M157.norm, M157.core_key)


def out(s):
    sys.stdout.write(str(s).encode("ascii", "replace").decode() + "\n")


# ------------------------------------------------------------------ edit 1
def retype_dates(fac):
    """Rewrite a padded ISO value to the precision its own column asserts."""
    stats = Counter()
    for f in fac:
        for fld in ("open_date", "close_date"):
            f.setdefault(f"{fld}_source_value_verbatim", "")
            v = (f.get(fld) or "").strip()
            p = (f.get(f"{fld}_precision") or "").strip()
            if len(v) != 10 or v[4] != "-" or p not in ("year", "month"):
                if v and p == "day" and len(v) == 10 and (v.endswith("-31") or v.endswith("-15")):
                    stats[f"{fld}_day_precision_kept_source_states_the_day"] += 1
                continue
            f[f"{fld}_source_value_verbatim"] = v
            f[fld] = v[:4] if p == "year" else v[:7]
            f[f"{fld}_basis"] = (
                (f.get(f"{fld}_basis") or "") +
                f"; DAY PRECISION WITHDRAWN {TODAY}: the value was a source "
                f"placeholder (YYYY-12-31 = year, YYYY-MM-15 = mid-month) "
                f"carrying a day no source states. Re-typed to the "
                f"{p}-precision the source supports; verbatim source string "
                f"retained in {fld}_source_value_verbatim; parse "
                f"{fld}_not_before/{fld}_not_after for the interval.")
            stats[f"{fld}_downgraded_to_{p}"] += 1
    return stats


# ------------------------------------------------------------------ edit 2
def split_additions(fac, adds):
    tokfreq = Counter()
    for f in fac:
        for t in set(core_key(f["facility_name"]).split()):
            tokfreq[t] += 1
    append, queue = [], []
    for a in adds:
        rare = [t for t in core_key(a["nigc_location_name"]).split()
                if tokfreq.get(t, 0) and tokfreq[t] <= 5]
        if rare:
            hits = [f["facility_id"] for f in fac
                    if set(rare) & set(core_key(f["facility_name"]).split())]
            a["duplicate_risk_tokens"] = "|".join(rare)
            a["duplicate_risk_facility_ids"] = "|".join(hits[:8])
            queue.append(a)
        else:
            append.append(a)
    return append, queue


def main():
    src = CLEAN / "gaming_facilities.csv"
    bak = CLEAN / f"gaming_facilities.csv.bak_{TODAY}_pre158"
    if not bak.exists():
        shutil.copy2(src, bak)
        out(f"backed up -> {bak.name}")

    fac = read_csv(src)
    fields = list(fac[0].keys())
    n_before = len(fac)
    pub_before = sum(1 for f in fac if not f["facility_id"].startswith(("CCP-", "TPL-")))
    out(f"gaming_facilities.csv in: {n_before} rows; "
        f"{pub_before} carry a non-vendor facility_id")

    # ---------------- edit 1
    stats = retype_dates(fac)
    for k, v in sorted(stats.items()):
        out(f"  {k}: {v}")
    for fld in ("open_date", "close_date"):
        c = f"{fld}_source_value_verbatim"
        if c not in fields:
            fields.insert(fields.index(fld) + 1, c)

    # ---------------- edit 2
    recon = read_csv(REVIEW / f"gaming_nigc_additions_{TODAY}.csv")
    adds = [r for r in recon if r["RULING_2026-08-26"] == "ADD_AS_NEW_CEDAR_PROPERTY"]
    roster = {norm(r["nigc_location_name"]): r for r in
              read_csv(CEDAR / "data" / "raw" / "external" / "nigc" /
                       "locations" / f"nigc_roster_current_{TODAY}.csv")}
    # Idempotence: a row this script appended on an earlier run is already in
    # the file, and re-running must not create a second one. `code/157` will
    # normally have re-ruled it to ALREADY_IN_CEDAR by now, but the guard does
    # not depend on that having happened.
    have = {(norm(f["facility_name"]), f.get("state", "")) for f in fac}
    adds = [a for a in adds
            if (norm(a["nigc_location_name"]), a["parsed_state"]) not in have]
    append, queue = split_additions(fac, adds)
    out(f"\nNIGC additions: {len(adds)} -> append {len(append)}, "
        f"queue as possible duplicates {len(queue)}")

    # tribe only where the town is unanimous in Cedar
    by_place = defaultdict(set)
    for f in fac:
        if f.get("tribe_id"):
            by_place[(norm(f.get("city", "")), f.get("state", ""))].add(
                (f["tribe_id"], f.get("tribe_canonical_name", "")))

    new_ids = IDS.allocate("CEDAR-FAC", n=len(append),
                           note="NIGC current gaming location roster 2026-08-26")
    new_rows, attributed = [], 0
    for fid, a in zip(new_ids, append):
        r = roster.get(norm(a["nigc_location_name"]), {})
        row = {k: "" for k in fields}
        tribes = by_place.get((norm(a["parsed_city"]), a["parsed_state"]), set())
        if len(tribes) == 1:
            tid, tname = next(iter(tribes))
            row["tribe_id"], row["tribe_canonical_name"] = tid, tname
            row["tribe"] = tname
            row["entity_tier"] = "B"
            row["entity_match_method"] = "unanimous_city_operator"
            row["entity_match_basis"] = (
                f"TIER B. Not resolved from the facility name - an NIGC "
                f"location name is a facility name and often carries no tribe "
                f"name. Every Cedar gaming property already recorded in "
                f"{a['parsed_city']}, {a['parsed_state']} belongs to "
                f"{tname}, and NIGC lists this location as gaming on Indian "
                f"lands there. That is corroboration, not an identification: "
                f"it must be confirmed against the operator before it "
                f"publishes at tier A.")
            attributed += 1
        else:
            row["entity_match_basis"] = (
                "BLANK BY RULING. " + (
                    f"Cedar records {len(tribes)} different tribal operators in "
                    f"{a['parsed_city']}, {a['parsed_state']}, so the town does "
                    f"not identify the operator."
                    if tribes else
                    f"Cedar records no gaming property in {a['parsed_city']}, "
                    f"{a['parsed_state']}, so there is nothing to corroborate "
                    f"against.") +
                " A false attribution is worse than a gap.")
        row.update({
            "facility_id": fid,
            "facility_name": a["nigc_location_name"],
            "address": r.get("street", ""), "city": a["parsed_city"],
            "state": a["parsed_state"], "postal_code": r.get("postal_code", ""),
            "observation_status": "current",
            "property_status": "current",
            "open_date_class": "absent",
            "open_date_absent_reason": (
                "no opening date sourced - this row is created from NIGC's "
                "gaming location map, which states that the location is a "
                "regulated gaming operation NOW and states nothing about when "
                "it opened. Absence of a date here is the source's silence, "
                "not a gap in searching."),
            "close_date_class": "absent",
            "source_datasets": "NIGC_GAMING_LOCATION_MAP",
            "match_status": "nigc_only_no_cedar_match",
            "match_basis": ("no rung of the code/157 ladder matched, and no "
                            "rare token of this name appears in any Cedar "
                            "facility name nationwide"),
            "duplicate_risk": "0",
            "fetched_date": TODAY, "entity_keyed_date": TODAY,
            "temporal_build_date": TODAY,
            "n_capacity_observations": "0",
            "gaming_machines_value_basis": "no_capacity_source_for_this_facility",
            "table_games_value_basis": "no_capacity_source_for_this_facility",
            "poker_tables_value_basis": "no_capacity_source_for_this_facility",
            "bingo_seats_value_basis": "no_capacity_source_for_this_facility",
            "gaming_square_feet_value_basis": "no_capacity_source_for_this_facility",
            "convention_square_feet_value_basis": "no_capacity_source_for_this_facility",
            "hotel_rooms_value_basis": "no_capacity_source_for_this_facility",
            "parking_spaces_value_basis": "no_capacity_source_for_this_facility",
            "employees_value_basis": "no_capacity_source_for_this_facility",
            "restaurants_value_basis": "no_capacity_source_for_this_facility",
            "open_date_evidence": (
                f"NIGC gaming location map lists this location in its "
                f"{a['nigc_region_name']} region as of {TODAY}; NIGC address "
                f"as published: {a['nigc_address']}"),
            "open_date_evidence_url": NIGC_URL,
            "first_observed_date": TODAY, "last_observed_date": TODAY,
        })
        # A handful of NIGC markers carry a COORDINATE PAIR in the address cell
        # instead of an address (Golden Eagle Casino, Naskila Gaming). Those
        # rows have no city or state to parse, so the coordinate is the only
        # locator the source gives - it is carried rather than discarded, and
        # city/state stay blank rather than being inferred from it.
        if r.get("address_is_coordinates") == "1":
            try:
                la, lo = [x.strip() for x in a["nigc_address"].split(",")]
                float(la), float(lo)
                row["latitude"], row["longitude"] = la, lo
                row["coords_basis"] = (
                    "NIGC gaming location map, coordinate published in the "
                    "address field; NIGC states no street address for this "
                    "marker, so city and state are blank rather than reverse "
                    "geocoded")
            except ValueError:
                pass
        new_rows.append(row)

    fac.extend(new_rows)
    write_csv(src, fac, fields)
    pub_after = sum(1 for f in fac if not f["facility_id"].startswith(("CCP-", "TPL-")))
    out(f"\nWROTE gaming_facilities.csv: {n_before} -> {len(fac)} rows")
    out(f"  non-vendor facility_id rows: {pub_before} -> {pub_after}")
    out(f"  appended rows with a tier-B tribe: {attributed} of {len(new_rows)}")

    if queue:
        for q in queue:
            q["YOUR_RULING"] = ""
            q["question"] = (
                "NIGC lists this gaming location and no rung of the code/157 "
                "ladder matched it to a Cedar row, BUT a distinctive token of "
                "its name appears on the Cedar rows named in "
                "duplicate_risk_facility_ids. Is this a property Cedar lacks, "
                "or another name for one of those? NOT APPENDED without a "
                "ruling.")
        write_csv(REVIEW / f"gaming_nigc_possible_duplicates_{TODAY}.csv", queue,
                  ["nigc_location_name", "nigc_address", "parsed_city",
                   "parsed_state", "nigc_region_name", "duplicate_risk_tokens",
                   "duplicate_risk_facility_ids", "question", "YOUR_RULING",
                   "source_url", "fetched_date"])
        out(f"  queued {len(queue)} possible duplicates for a human ruling")

    (LOGS / f"158_extend_gaming_facilities_{TODAY}.json").write_text(json.dumps({
        "built": TODAY, "rows_before": n_before, "rows_after": len(fac),
        "non_vendor_id_rows_before": pub_before,
        "non_vendor_id_rows_after": pub_after,
        "date_retyping": dict(stats),
        "nigc_additions_considered": len(adds),
        "nigc_additions_appended": len(new_rows),
        "nigc_additions_queued_as_possible_duplicates": len(queue),
        "appended_with_tier_b_tribe": attributed,
    }, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
