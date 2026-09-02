#!/usr/bin/env python3
"""
Cedar Press - 156: STAGE Form 5500 gaming-sector employment for the gaming
collection.

BOTH BLOCKING RULINGS ARE RESOLVED. THE MERGE IS BLOCKED ONLY ON A LOCK.
------------------------------------------------------------------------
This script originally staged because two rulings were open. Both were settled
2026-08-26 from precedent already in this codebase:

  RULING 1 - `FORM5500_ACTIVE_PARTICIPANTS` was ADDED to
    `cedar_domain.MeasurementType`. Precedent: the enum already carries
    OSHA_ESTABLISHMENT_REPORTED and LODES_BLOCK_WORKPLACE_JOBS, both external
    administrative employment sources, and GAME_FINDER_OBSERVATION was added the
    same way on 2026-08-12 by script 142. It sits in `is_observed` (a plan
    administrator counted a real population on a real date) AND in
    `NEVER_PROMOTES_TO_ACTIVE` (enrollees are not employees, and relabelling one
    as the other would invent a measurement nobody made).

  RULING 2 - a blank `facility_id` on an EIN-keyed row is FINE, behind an
    explicit `entity_level`. Precedent: gaming_facility_metrics.csv already
    holds 1,039 such rows. `entity_level = "tribe"` is now set on every row.

WHAT STILL BLOCKS THE MERGE: a concurrent writer, not a question. Verified
2026-08-26 17:16 - another agent is actively rebuilding the gaming collection
(gaming_facility_metrics.csv 17:12, gaming_properties.csv 17:15,
07n_gaming_employment.csv 17:16, gaming_facilities.csv grown 774 -> 784). A
concurrent write to a shared gaming table is exactly the clobbering this project
has already lost work to. `code/158_merge_staged_labor_employment.py` is written
and ready; run it when that agent is done.

Nothing existing is read-modify-written here, and
`gaming_employment_observations.csv` is not opened for writing at all.

WHERE THE INPUT COMES FROM
--------------------------
`4wheeler/casino_employment_validation/data/resolved_form5500_tribal.csv`
(built 2026-08-12, READ ONLY here). That file is already resolved to the Cedar
Press entity spine - `tribe_id` is in Cedar's own vocabulary (TRBF-/AKNF-/...),
so this is a join, not a new matching problem. Its resolver rules and its known
defects are in `4wheeler/casino_employment_validation/docs/KNOWN_DEFECTS.md`.

Measured before writing: the exact-alias resolver defect (Hamilton / Evansville
/ Georgetown, 131 bad rows in the 4wheeler analysis file) does NOT touch the
gaming-NAICS subset. Zero of those names appear here.

THE CAVEAT THAT TRAVELS WITH EVERY ROW
--------------------------------------
`TOT_ACTIVE_PARTCP_CNT` is a count of ACTIVE PLAN PARTICIPANTS, not employees.
It BRACKETS employment and the bracket is CONDITIONAL:

  - plans exclude employees below an age or service threshold  -> pushes BELOW
    total employment
  - plans include part-timers who clear that threshold         -> pushes ABOVE
    full-time headcount

On the same 13 SEC-overlapping tribe-years the largest RETIREMENT plan gives a
median ratio of 1.65 while the largest WELFARE plan gives 1.19, and against a
study's TOTAL employment the same kind of plan gives 0.79. **None of 0.79 /
1.19 / 1.65 is a calibration factor.** The usable result is longitudinal: a
change slope of ~0.63 against SEC full-time counts (corr 0.93, R2 0.86, 11
pairs, 2 entities). See `4wheeler/.../docs/FORM5500_CALIBRATION.md`.

COLLAPSE RULE
-------------
One sponsor files several plans. Rows are collapsed to (tribe_id, ein, year)
taking the LARGEST `active_participants`, which is the 4wheeler rule. The
number of plans collapsed is carried on every row so the choice is visible.
A sponsor is NOT summed across plans - that double counts the same people.

Writes  data/staging/gaming_employment_form5500_staged.csv
        review/form5500_gaming_coverage_2026-08-26.csv

No network. Writes `.part` then renames.
"""

import csv
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
FOURWHEELER = Path(r"C:\Users\esm247\Desktop\4wheeler\casino_employment_validation")
SRC = FOURWHEELER / "data" / "resolved_form5500_tribal.csv"

CLEAN = CEDAR / "data" / "clean"
sys.path.insert(0, str(CEDAR / "code"))
import cedar_domain as CD          # noqa: E402  the ONE shared vocabulary

STAGING = CEDAR / "data" / "staging"
REVIEW = CEDAR / "review"
LOGS = CEDAR / "logs"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

# 4wheeler's prefixes. Kept as prefixes, never as an exact set: filers use the
# 4-digit group padded out (713200) at least as often as the specific code
# (713210), and an exact-set filter on the specific codes cost 4wheeler 120
# sponsors including Mashantucket, San Manuel, Tulalip and Shakopee.
GAMING_PREFIXES = ("7132", "72112", "7139", "72111")

# NAICS SPECIFICITY, NOT "is it a casino".
#
# A flag reading "strict casino code = 0" on SEMINOLE TRIBE OF FLORIDA, whose
# filings carry `713200`, would be read as "not a casino" and would be wrong on
# the single largest employer in the file. `713200` is the 4-digit GAMBLING
# INDUSTRIES group padded to six digits - it is the same industry, filed less
# precisely. That padding is the exact trap that cost 4wheeler 120 sponsors.
#
# So the column records how SPECIFIC the filer was, and nothing else.
NAICS_SPECIFIC = {"713210", "721120", "713290", "713940", "713950", "713990"}
NAICS_PADDED_GROUP = {"713200", "721100", "713900", "721110", "713000",
                      "721000"}

SRC_URL = ("https://askebsa.dol.gov/FOIA%20Files/{yr}/Latest/"
           "F_5500_{yr}_Latest.zip")


def log(msg):
    LOGS.mkdir(exist_ok=True)
    print(msg)
    with open(LOGS / f"156_form5500_gaming_{TODAY}.log", "a",
              encoding="utf-8") as fh:
        fh.write(msg + "\n")


def read_csv(p):
    if not Path(p).exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path, rows, fields):
    """`.part` then rename. An interruption must not look like a completion."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(path.suffix + ".part")
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    part.replace(path)
    log(f"  wrote {path.relative_to(CEDAR)}  ({len(rows):,} rows)")


def num(x):
    try:
        v = float(str(x).strip())
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def main():
    log(f"=== Cedar Press 156: stage Form 5500 gaming employment ({TODAY}) ===")
    if not SRC.exists():
        log(f"FATAL: source not found: {SRC}")
        return 1

    src = read_csv(SRC)
    log(f"read {len(src):,} resolved Form 5500 rows (4wheeler, read-only)")

    gaming = [r for r in src
              if str(r.get("naics", "")).startswith(GAMING_PREFIXES)]
    log(f"  gaming-NAICS rows: {len(gaming):,}")

    # Resolution triage. `no spine match` is dropped - it carries no tribe_id,
    # so it cannot key anything here. `matched (state mismatch)` is KEPT and
    # FLAGGED: the sponsor filed from a different state than the spine records,
    # which is common for an enterprise HQ and is corroboration lost, not a
    # falsification.
    by_res = defaultdict(int)
    for r in gaming:
        by_res[r.get("resolution", "")] += 1
    for k, v in sorted(by_res.items(), key=lambda kv: -kv[1]):
        log(f"    resolution {k!r}: {v:,}")

    keep = [r for r in gaming
            if r.get("tribe_id")
            and r.get("resolution", "").startswith("matched")
            and (num(r.get("active_participants")) or 0) > 0]
    log(f"  usable (tribe_id + matched + participants>0): {len(keep):,}")

    # --- the resolver defect check, measured not assumed -------------------
    DEFECT = {"hamilton", "evansville", "georgetown", "st. mary's", "st. marys"}
    hits = sorted({r.get("cedar_entity_name", "") for r in keep
                   if r.get("cedar_entity_name", "").strip().lower() in DEFECT})
    log(f"  exact-alias defect names present in this subset: "
        f"{hits if hits else 'NONE'}")

    # --- collapse to (tribe_id, ein, year), largest plan -------------------
    groups = defaultdict(list)
    for r in keep:
        groups[(r["tribe_id"], r.get("ein", ""), r.get("data_year", ""))].append(r)

    out = []
    n = 0
    for (tid, ein, yr), rows in sorted(groups.items()):
        rows.sort(key=lambda r: -(num(r.get("active_participants")) or 0))
        best = rows[0]
        ap = int(num(best["active_participants"]))
        naics = str(best.get("naics", "")).strip()
        n += 1
        out.append({
            "observation_id": f"EMP-F5500-{n:06d}",
            "facility_id": "",
            "tribe_id": tid,
            "cedar_entity_name": best.get("cedar_entity_name", ""),
            "entity_class": best.get("entity_class", ""),
            "year": yr,
            "employment": ap,
            "measurement_type": CD.MeasurementType.FORM5500_ACTIVE_PARTICIPANTS.value,
            # RULING 2 (2026-08-26): an EIN-keyed row with a blank facility_id
            # is the established pattern. gaming_facility_metrics.csv already
            # carries 1,039 blank-facility rows behind an `entity_level`
            # column - implied_gaming_revenue (490), ok_exclusivity_fee_annual
            # (316), ct_slot_contribution_annual / ct_slot_win_annual (63 each),
            # and the MI/WA/WI compact payments. Set entity_level and the row
            # follows precedent instead of inventing a shape.
            "entity_level": "tribe",
            "geographic_level": "plan_sponsor",
            "ein": ein,
            "sponsor_name": best.get("sponsor_name", ""),
            "plan_name": best.get("plan_name", ""),
            "naics": naics,
            "naics_specificity":
                "specific_industry_code" if naics[:6] in NAICS_SPECIFIC
                else ("padded_group_code" if naics[:6] in NAICS_PADDED_GROUP
                      else "other_in_prefix_range"),
            "naics_specificity_note":
                "Describes how precisely the SPONSOR filed its NAICS, and "
                "nothing about whether the employer is a casino. `713200` is "
                "the 4-digit Gambling Industries group padded to six digits "
                "and is the most common filing on this file - Seminole Tribe "
                "of Florida, the largest employer here, files it.",
            "sponsor_city": best.get("city", ""),
            "sponsor_state": best.get("state", ""),
            "plans_collapsed": len(rows),
            "plan_participants_all_plans_DO_NOT_SUM":
                ";".join(str(int(num(r["active_participants"])))
                         for r in rows),
            "ack_id": best.get("ack_id", ""),
            "source_url": SRC_URL.format(yr=yr),
            "source_name": f"DOL Form 5500 annual dataset {yr} (Latest)",
            "source_record": f"F_5500_{yr}_Latest.zip",
            "source_quote":
                f'sponsor_name="{best.get("sponsor_name","")}"; '
                f'plan_name="{best.get("plan_name","")}"; '
                f'ein="{ein}"; naics="{naics}"; '
                f'active_participants="{ap}"; ack_id="{best.get("ack_id","")}"',
            "measurement_note":
                "ACTIVE PLAN PARTICIPANTS, NOT EMPLOYEES. The count excludes "
                "employees below the plan's age/service threshold (pushing it "
                "BELOW total employment) and includes part-timers who clear "
                "that threshold (pushing it ABOVE full-time headcount). The "
                "bracket is CONDITIONAL on plan type and on what it is "
                "compared to: 1.65 (largest retirement plan vs SEC full-time), "
                "1.19 (largest welfare plan vs SEC full-time), 0.79 (vs a "
                "study's total employment). NONE of those is a calibration "
                "factor. Use CHANGES, not levels: the change slope against SEC "
                "full-time counts is ~0.63 (corr 0.93, R2 0.86, 11 pairs, 2 "
                "entities). `year` is the Form 5500 data year, not a fiscal "
                "year end aligned to anything else. A sponsor's plans are "
                "NEVER summed - the largest is taken.",
            "match_rule": "cedar_entity_spine_resolution_in_4wheeler_step18",
            "resolution": best.get("resolution", ""),
            "state_mismatch_flag":
                "1" if "state mismatch" in best.get("resolution", "") else "0",
            "confidence": "medium",
            "flags": "PLAN_PARTICIPANTS_ARE_NOT_A_HEADCOUNT;"
                     "SPONSOR_LEVEL_NOT_FACILITY_LEVEL",
            "source_provenance":
                "4wheeler/casino_employment_validation/data/"
                "resolved_form5500_tribal.csv (2026-08-12)",
            "built_by_script": "156_stage_form5500_gaming_employment.py",
            "built_date": TODAY,
        })

    fields = list(out[0].keys()) if out else ["observation_id"]
    write_csv(STAGING / "gaming_employment_form5500_staged.csv", out, fields)

    # ------------------------------------------------------------- coverage --
    fac = read_csv(CLEAN / "gaming_facilities.csv")
    fac_tribes = {f["tribe_id"] for f in fac if f.get("tribe_id")}
    emp = read_csv(CLEAN / "gaming_employment_observations.csv")
    emp_tribes = {e["tribe_id"] for e in emp if e.get("tribe_id")}
    emp_years = {e.get("year", "") for e in emp if e.get("year")}

    staged_tribes = {r["tribe_id"] for r in out}
    years = sorted({r["year"] for r in out})

    per_year = defaultdict(lambda: {"rows": 0, "tribes": set()})
    for r in out:
        per_year[r["year"]]["rows"] += 1
        per_year[r["year"]]["tribes"].add(r["tribe_id"])

    cov = []
    for y in years:
        d = per_year[y]
        cov.append({
            "year": y,
            "staged_rows": d["rows"],
            "staged_tribes": len(d["tribes"]),
            "tribes_with_a_cedar_gaming_facility":
                len(d["tribes"] & fac_tribes),
            "tribes_new_to_cedar_employment_table":
                len(d["tribes"] - emp_tribes),
            "cedar_employment_table_has_this_year":
                "1" if y in emp_years else "0",
        })
    write_csv(REVIEW / f"form5500_gaming_coverage_{TODAY}.csv", cov,
              list(cov[0].keys()) if cov else ["year"])

    log("")
    log("SUMMARY")
    log(f"  staged observations          {len(out):,}")
    log(f"  distinct tribes              {len(staged_tribes)}")
    log(f"  years                        {years[0]}-{years[-1]}")
    log(f"  tribes with a Cedar facility {len(staged_tribes & fac_tribes)}")
    log(f"  tribes NEW to employment     {len(staged_tribes - emp_tribes)}")
    log(f"  state-mismatch flagged rows  "
        f"{sum(1 for r in out if r['state_mismatch_flag'] == '1'):,}")
    spec = defaultdict(int)
    for r in out:
        spec[r["naics_specificity"]] += 1
    for k, v in sorted(spec.items(), key=lambda kv: -kv[1]):
        log(f"  naics_specificity {k:<24} {v:,}")
    post = [r for r in out if r["year"] >= "2024"]
    log(f"  rows in 2024-2025            {len(post):,} "
        f"({len({r['tribe_id'] for r in post})} tribes) - "
        f"gaming_facility_metrics stops at 2023")
    log("")
    log("NOT MERGED - but no longer for want of a ruling. Both rulings are "
        "settled (see docstring); the only blocker is a concurrent writer on "
        "the gaming tables. Run `py -3 code/158_merge_staged_labor_employment"
        ".py --check`, then `--merge` when it reports CLEAR.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
