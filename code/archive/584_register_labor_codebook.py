#!/usr/bin/env python3
"""
Cedar Press - 584: re-register the codebook block for
`gaming_employment_observations.csv`.  WORKSTREAM INT-1 (LABOR).

Writes the fragment ONLY, via `cedar_codebook.write_fragment`, exactly as
`docs/SHIPPING_RUNBOOK.md` §3 requires.  It never touches `codebook_master.csv`
and it never runs `41_build_codebooks.py`.

THREE THINGS THE OLD BLOCK GOT WRONG, ALL OF THEM SILENT
---------------------------------------------------------
1. **It described a 769-row table.** Every `n_rows` said 769 and every
   `pct_filled` was measured against 769. The table holds 3,421 rows. The
   headline error this produces is `facility_id  pct_filled 97.5` - the true
   figure is 23.5%, because 2,617 of 3,421 rows are TRIBE-LEVEL and carry no
   facility at all. A buyer reading 97.5% plans a facility-grain join that
   will drop three quarters of the table.

2. **`measurement_type` listed five values and the table holds six.** The two
   labour types - `FORM5500_ACTIVE_PARTICIPANTS` (1,956 rows) and
   `OSHA_TRIBE_LEVEL_REPORTED` (696) - between them are 77% of the table and
   neither was named. Both have been live in `cedar_domain.MeasurementType`
   since 2026-08-26.

3. **Nowhere did it say which measurement types may be added together.** They
   count four different populations over three different geographies. The
   matrix is now written into the `measurement_type` and `employment`
   definitions, because that is the single thing a buyer is most likely to get
   wrong and the one that silently doubles a jobs number.

usage:
    py -3 code/584_register_labor_codebook.py           # dry run
    py -3 code/584_register_labor_codebook.py --apply
"""
import csv
import sys
import collections
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cedar_codebook  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "data" / "clean" / "gaming_employment_observations.csv"
FRAG = "07n_gaming_employment"
TODAY = "2026-09-01"

# ---------------------------------------------------------------------------
# THE TWO RULINGS, AS RESOLVED BY WORKSTREAM INT-1 ON 2026-09-01.
# Both are SCHEMA decisions - how a number is typed and at what grain a row is
# admitted. Neither decides whether an entity is Native-owned, which remains
# Elijah's alone.
# ---------------------------------------------------------------------------

MT = (
    "Which of six populations this row counts. From `cedar_domain."
    "MeasurementType`; never free text. "
    "`OSHA_ESTABLISHMENT_REPORTED` (364) - one establishment's own filed "
    "annual average employees, attached to a Cedar facility. "
    "`OSHA_TRIBE_LEVEL_REPORTED` (696) - the same 300A figure where Cedar can "
    "name the owning tribe but not the property. "
    "`FORM5500_ACTIVE_PARTICIPANTS` (1,956) - people ENROLLED IN A BENEFIT "
    "PLAN, which is NOT employment (see `employment`). "
    "`LODES_BLOCK_WORKPLACE_JOBS` (384) - Census LEHD jobs in a 2020 block, a "
    "GEOGRAPHY not an employer. "
    "`PROJECTED` (20) and `ENVIRONMENTAL_REVIEW_COUNT` (1) - forecasts inside "
    "NEPA documents, never observations. "
    "**WHICH MAY BE SUMMED.** Only `OSHA_ESTABLISHMENT_REPORTED` rows, and "
    "only across DISTINCT establishments within one year - and even then the "
    "total is 'employment at the establishments that filed', never total "
    "tribal gaming employment, because ITA is not a census. "
    "**NEVER SUM ACROSS TYPES.** `FORM5500_ACTIVE_PARTICIPANTS` covers the "
    "whole plan-sponsoring enterprise while `OSHA_TRIBE_LEVEL_REPORTED` covers "
    "only the establishments that filed, so adding them counts the same casino "
    "floor twice: over the 192 tribe-years carrying both, the median ratio is "
    "1.03 - they are two measurements OF THE SAME PEOPLE, not two workforces. "
    "**NEVER SUM `OSHA_TRIBE_LEVEL_REPORTED` WITH "
    "`OSHA_ESTABLISHMENT_REPORTED`**: 332 tribe-level rows ARE the same 300A "
    "filing as a facility-grain row, and `already_facility_attached = 1` marks "
    "every one. **NEVER SUM `LODES_BLOCK_WORKPLACE_JOBS` WITH ANYTHING** - a "
    "census block contains the casino AND its neighbours. "
    "**NEVER SUM ACROSS YEARS**: the set of establishments filing under one "
    "tribe changes year to year, so the panel is unbalanced and a difference "
    "measures filing behaviour, not hiring."
)

EMPLOYMENT = (
    "The figure exactly as the source states it. Never rounded, scaled, "
    "deflated or reconciled. **IT IS NOT ONE QUANTITY - read `measurement_type` "
    "before using this column.** Four of the six types count people at an "
    "employer; one counts plan enrolment; one counts jobs in a census block. "
    "In particular a `FORM5500_ACTIVE_PARTICIPANTS` value is NOT a headcount: "
    "it EXCLUDES employees who never enrolled or who sit below the plan's "
    "age/service threshold, and it INCLUDES separated employees who still hold "
    "a balance. The two errors do not cancel and their net sign is not stable. "
    "Measured against SEC-overlapping tribe-years the ratio to full-time "
    "headcount is 1.65 for the largest retirement plan, 1.19 for the largest "
    "welfare plan and 0.79 against a study's total employment - NONE of those "
    "is a calibration factor. It is usable as a LOWER-BOUND-ISH PROXY for the "
    "size of the enterprise and as a CHANGE series (slope ~0.63 against SEC "
    "full-time counts, R2 0.86, 11 pairs, 2 entities). It is not a level."
)

FACILITY_ID = (
    "Cedar property id (`CCP-`/`VP-`/`TPL-`). **BLANK ON 2,617 OF 3,421 ROWS "
    "(76.5%), BY DESIGN.** RULING, 2026-09-01: this table ADMITS rows that "
    "carry no facility. A Form 5500 is filed by a PLAN SPONSOR - the tribe or "
    "its enterprise - and names no casino; an OSHA 300A names an establishment "
    "Cedar can sometimes tie to an owning tribe but not to one of its "
    "properties; a LODES figure is a census block. Requiring a `facility_id` "
    "would mean INVENTING an attribution the filing does not make, and where a "
    "tribe runs several casinos there is no non-arbitrary way to pick one. "
    "Cedar's rule is that blank beats confident-wrong, so the row is admitted "
    "at the grain the source actually states and `entity_level` records which "
    "grain that is. **Consequence for a consumer: a join on `facility_id` is "
    "not a join on this table, it is a join on the 23.5% of it that is "
    "facility-grain.** Filter on `entity_level = 'facility'` to say so out "
    "loud, or aggregate to `tribe_id` and use the whole table."
)

ENTITY_LEVEL = (
    "The grain of THIS ROW, and the column that makes the mixed-grain table "
    "safe: `facility` (803) - the row is a fact about one property and "
    "`facility_id` is populated; `tribe` (2,607) - the row is a fact about the "
    "ENTITY and must never be attributed to any one of its casinos. Blank on "
    "11 legacy NEPA rows. RULING, 2026-09-01: tribe-level rows are ADMITTED "
    "(see `facility_id`), so this column is the declared grain per row and "
    "`gaming_employment_observations.csv` has no single grain. The dataset "
    "contract states it as 'one row per employment observation at one "
    "geographic level'; `geographic_level` carries the source's own words for "
    "that level."
)

MEASUREMENT_TYPE_STATUS = (
    "Whether the measurement type on this row may be read as an ACTIVE "
    "headcount. `FORM5500_ACTIVE_PARTICIPANTS` is `NEVER_PROMOTES_TO_ACTIVE`: "
    "plan participants are not employees. Blank where the type is a filed "
    "headcount and no such caution applies. The column is a machine-readable "
    "restatement of the second half of `measurement_type`, so a consumer that "
    "reads only schema still cannot mistake enrolment for employment."
)

OBS_AS_STAGED = (
    "The `observation_id` this row carried in its staging file, kept so the "
    "seam stays auditable across a re-key. **STALE BY 2026-09-01 AND NOT A "
    "JOIN KEY**: `157` renumbered the staging file after the 16 rows carrying "
    "this column were repaired, so the id it names now points at a DIFFERENT "
    "staged row. Verified 2026-09-01 that the 502 staged OSHA rows and the "
    "clean rows agree one-for-one on the natural key (establishment name, "
    "state, year) - nothing is lost and nothing is duplicated; only this "
    "backlink is dangling. Use the natural key, not this column."
)

CEDAR_UID = (
    "Cedar's cross-collection universal id for the entity on this row, written "
    "by the entity layer. Populated only where the entity layer has reached "
    "this row. A DISPLAY-AND-JOIN convenience carried alongside `tribe_id`, "
    "never a second, competing key."
)

ATTRIBUTION_REPAIRED_BY = (
    "Names the script that CORRECTED this row's tribe attribution after it was "
    "merged. `262_repair_form5500_tribe_attribution` set 133 Form 5500 rows "
    "whose tribe came from 4wheeler's resolver. "
    "`583_labor_surface_factcheck.py` (2026-09-01) carries the 79 OSHA rows "
    "adjudicated out of `review/osha_gambling_unresolved_2026-08-26.csv`, "
    "and `589_adjudicate_osha_711.py` the 115 adjudicated out of the 711-"
    "establishment hold in `review/employment_osha_unmatched_2026-08-07.csv`. "
    "**A row with a blank here is not a row that was checked and passed - it "
    "is a row nothing has revisited.** 583 also REMOVED 19 rows rather than "
    "repairing them: four commercial Las Vegas employers (Westgate, Fitzgeralds, "
    "Gaming Ventures of Las Vegas, Las Vegas Gaming Inc) that a name match had "
    "put on the Las Vegas Paiute Tribe because that tribe's spine handle is a "
    "bare US settlement name. They are in "
    "`review/gaming_employment_lsvgas_removed_2026-09-01.csv`."
)

FLAGS = (
    "Machine-readable cautions, `;`-separated. "
    "`BLOCK_JOBS_ARE_NOT_PROPERTY_PAYROLL`; "
    "`IDENTICAL_VALUE_FILED_UNDER_n_PROPERTY_NAMES_SAME_TRIBE_YEAR`; "
    "`PLAN_PARTICIPANTS_ARE_NOT_A_HEADCOUNT`; "
    "`SPONSOR_LEVEL_NOT_FACILITY_LEVEL`; "
    "`TRIBE_LEVEL_ROLLUP_NOT_A_FACILITY_FIGURE`; "
    "`ITA_COVERAGE_IS_NOT_A_CENSUS`; "
    "`DO_NOT_SUM_ACROSS_YEARS_WITHOUT_A_BALANCED_PANEL`; "
    "`ADJUDICATED_FROM_REVIEW_HOLD_2026-09-01` (the 79 rows 583 promoted); "
    "`ADJUDICATED_FROM_711_HOLD_2026-09-01` (the 115 rows 587 promoted, on "
    "an EIN in the identifier ledger, a street-address+ZIP match to a Cedar "
    "facility, or the filing naming the government - never on a shared "
    "token); "
    "`SPONSOR_IS_NOT_A_GAMING_EMPLOYER_NO_CEDAR_FACILITY` - 4 rows, correctly "
    "keyed to the right entity but the plan sponsor is not a gaming employer "
    "and Cedar holds no gaming facility for it (Sitnasuak Native Corporation, "
    "Bering Straits Development Company). Flagged in place and never removed: "
    "the attribution is right and the filing is real."
)

OVERRIDES = {
    "measurement_type": MT,
    "employment": EMPLOYMENT,
    "facility_id": FACILITY_ID,
    "entity_level": ENTITY_LEVEL,
    "measurement_type_status": MEASUREMENT_TYPE_STATUS,
    "observation_id_as_staged": OBS_AS_STAGED,
    "cedar_uid": CEDAR_UID,
    "attribution_repaired_by": ATTRIBUTION_REPAIRED_BY,
    "flags": FLAGS,
    "observation_id": (
        "Cedar id, unique. Prefix names the source family: `EMP-OSHA-` "
        "(facility-grain 300A), `EMP-OSHATRIBE-` (tribe-grain 300A; `-R` = "
        "attribution repaired by 262, `-A` = adjudicated out of review by 583), "
        "`EMP-F5500-`, `EMP-LODES-`, `EMP-DOC-`, `EMP-EA-`."),
    "geographic_level": (
        "What the number is measured OVER, in the source's own terms: "
        "`plan_sponsor` (1,956), `establishment_rolled_to_tribe` (642), "
        "`census_block_2020` (384), `establishment` (418), `property`, "
        "`named_project`, or a verbatim geography string from a NEPA document "
        "(e.g. *State of Missouri*). Distinct from `entity_level`, which says "
        "what Cedar could ATTACH the number to. A row can be measured over one "
        "establishment and attached only to a tribe."),
}


def main():
    apply = "--apply" in sys.argv
    with open(TABLE, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    n = len(rows)
    cols = list(rows[0].keys())

    frag = ROOT / "data" / "clean" / "codebook" / f"{FRAG}.csv"
    with open(frag, newline="", encoding="utf-8-sig") as fh:
        old = {r["variable"]: r for r in csv.DictReader(fh)}
    fields = list(next(iter(old.values())).keys())

    out, changed, added = [], 0, 0
    for c in cols:
        prev = old.get(c)
        filled = sum(1 for r in rows if (r.get(c) or "").strip())
        rec = dict(prev) if prev else {
            "dataset": FRAG, "variable": c, "type": "text", "units": "",
            "published": "1", "access_tier": "public", "description": "",
            "pct_filled": "", "n_rows": "", "generated": ""}
        if not prev:
            added += 1
        before = (rec.get("description"), rec.get("pct_filled"),
                  rec.get("n_rows"))
        rec["pct_filled"] = f"{100.0 * filled / n:.1f}"
        rec["n_rows"] = str(n)
        rec["generated"] = TODAY
        if c in OVERRIDES:
            rec["description"] = OVERRIDES[c]
        if (rec.get("description"), rec["pct_filled"], rec["n_rows"]) != before:
            changed += 1
        out.append({k: rec.get(k, "") for k in fields})

    undocumented = [r["variable"] for r in out
                    if not (r.get("description") or "").strip()]
    print(f"{TABLE.name}: {n:,} rows, {len(cols)} columns")
    print(f"  codebook rows written : {len(out)}  (new {added}, "
          f"updated {changed})")
    print(f"  stale n_rows corrected: 769 -> {n:,} on every row")
    fid = next(r for r in out if r["variable"] == "facility_id")
    print(f"  facility_id pct_filled: 97.5 (claimed) -> "
          f"{fid['pct_filled']} (measured)")
    print(f"  undefined variables   : {len(undocumented)} {undocumented}")

    if not apply:
        print("\nDRY RUN. Re-run with --apply.")
        return
    wrote = cedar_codebook.write_fragment(FRAG, out, fields)
    print(f"\nwrote {wrote} rows -> data/clean/codebook/{FRAG}.csv")
    print("now run: py -3 code/cedar_codebook.py build")


if __name__ == "__main__":
    main()
