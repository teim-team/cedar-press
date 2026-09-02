#!/usr/bin/env python3
"""
1094_merge_web_harvest_into_gaming_claims.py -- Cedar Press, workstream GAMING-DEEP.

MERGES the 1,166 staged rows of `data/clean/gaming_web_harvest_observations.csv`
(built 2026-09-02 by `code/980_gaming_web_harvest.py`) into the two tables that
are already the published home of self-published gaming evidence:

    CAPACITY_SIGNAL  309 -> gaming_property_self_published_claims.csv
    FACILITY_IDENTITY 857 -> gaming_property_self_published_assertions.csv

WHY THOSE TWO TABLES AND NOT gaming_facilities / gaming_facility_metrics
------------------------------------------------------------------------
Because of what these rows ARE. Every one carries
`assertion_class = SELF_PUBLISHED_OPERATOR_ASSERTION` -- the operator's own
marketing copy and its own schema.org markup. `588_promote_self_published_claims.py`
already argued this case for the 270 rows it promoted and the argument is
unchanged:

    A MACHINE COUNT A CASINO ADVERTISES IS A CLAIM, NOT A MEASUREMENT.

Writing a harvested slot count onto the facility record, or into
`gaming_capacity_official.csv`, would put a marketing number where a buyer
expects a regulator's. These two tables exist precisely so the two never touch.

THREE QUALIFIERS THE HARVEST RECORDED AND THIS MERGE MUST NOT LOSE
-------------------------------------------------------------------
1. **152 of the 309 capacity figures are LOWER BOUNDS** ("500 + Slots").
   `value_is_bounded = Y`, `bound_direction = at_least`, and `bound_basis`
   quotes the trailing '+' in the operator's own wording. A bound is not a
   count. Carried verbatim; `bound_direction` is renamed to the vocabulary the
   destination table already uses (`at_least` -> `LOWER_BOUND`) and
   `bound_direction_as_harvested` keeps the original word so the rename is
   reversible.
2. **`measurement_scope = UNVERIFIED_SCOPE` on 304 of them**, because nothing
   in the sentence says whether the figure describes the whole property or one
   room. The destination table has no such column, so this merge ADDS
   `measurement_scope` and `measurement_scope_basis` to it. **On the 270
   pre-existing rows those cells are blank, and blank means NOT RECORDED BY
   THAT EXTRACTION -- it does not mean the scope was verified.** That sentence
   is the whole reason the column is added rather than the value dropped.
3. **703 of 1,166 rows are `TRIBE_LEVEL_MULTI_FACILITY_NOT_DISAMBIGUATED`** --
   a page on a host serving several of one tribe's properties, where nothing
   on the page says which. Only the 463 `SINGLE_FACILITY_TRIBE` rows get a
   `facility_id`. The other 703 keep their tribe, and the candidate facility
   list travels in `tribe_facility_ids_not_disambiguated` so the information
   is preserved without being asserted. Guessing which of Chickasaw's 28
   properties a tribe-level page describes is the containment defect with a
   URL attached.

WHAT IT DOES NOT DO
-------------------
No dollar column. No facility-record write. Nothing is summed. Every capacity
row keeps the `not_summable_with` string the harvest wrote, which names NIGC
GGR, state-regulator device counts, `gaming_facility_metrics.official` and
*other rows of this table for the same facility* -- the last because two
sentences on one page counting the same floor are two claims about one thing.

THE REBUILD/IN-PLACE ORDERING, STATED BECAUSE THIS REPO KEEPS LOSING IT
------------------------------------------------------------------------
`code/588_promote_self_published_claims.py` is a FULL REBUILD of both
destination tables from `data/staging/`. This script is an IN-PLACE ENRICHER
on the same two files. **588 first, 1094 last.** A 588 run reverts this merge;
re-running 1094 restores it exactly, because the merge is keyed on a
deterministic id derived from the harvest `observation_id` and `merge_table`
never appends a key it already holds. Declared in
`docs/DEPENDENCY_MANIFEST.md` and in this docstring so the next agent does not
have to find out the way the FERC docket table did.

ROW AND MONEY CONSERVATION
--------------------------
Row conservation: 1,166 staged = 309 + 857, and 309 + 857 = the rows appended
across the two destinations on a first run (0 on a re-run, by design).
Money conservation is vacuous and is asserted as such: **neither destination
table has a dollar column and this merge adds none.** `verify` proves that.

USAGE
    py -3 code/1094_merge_web_harvest_into_gaming_claims.py plan
    py -3 code/1094_merge_web_harvest_into_gaming_claims.py merge
    py -3 code/1094_merge_web_harvest_into_gaming_claims.py verify [--selftest]
"""
import argparse
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parents[1]
CLEAN = CEDAR / "data" / "clean"
LOGS = CEDAR / "logs"
sys.path.insert(0, str(CEDAR / "code"))
import cedar_pipeline as CP  # noqa: E402

TODAY = date.today().isoformat()
TAG = "pre_1094_merge_web_harvest_into_gaming_claims"

HARVEST = CLEAN / "gaming_web_harvest_observations.csv"
CLAIMS = CLEAN / "gaming_property_self_published_claims.csv"
ASSERTS = CLEAN / "gaming_property_self_published_assertions.csv"
SITEOBS = CLEAN / "gaming_property_site_observations.csv"
FACILITIES = CLEAN / "gaming_facilities.csv"
REPORT = LOGS / "1094_web_harvest_merge_report.json"

SELF = "code/1094_merge_web_harvest_into_gaming_claims.py"
FAMILY = "web_harvest_980"

# A harvested capacity figure is an operator assertion. This is the same fence
# 588 put on its 270 rows, restated for the harvest's provenance.
CLAIM_NOTE = (
    "SELF-PUBLISHED BY THE OPERATOR, harvested from the property's own site by "
    "code/980_gaming_web_harvest.py. It is an ASSERTION, not a regulator's "
    "measurement and not an audited figure, and it must never be pooled with "
    "`gaming_capacity_official.csv` (regulator-reported), with NIGC gross "
    "gaming revenue, or with the Casino City vendor panel. Where the two "
    "disagree, this row is the weaker evidence and says so.")

IDENTITY_NOTE = (
    "SELF-PUBLISHED BY THE OPERATOR: what the property states about its own "
    "identity on its own website, most of it from schema.org markup the page "
    "publishes for search engines. It is evidence of what the operator SAYS, "
    "which is not the same as a regulator's or a registrar's record of the "
    "same fact. It measures no capacity and no money.")

# metric -> (assertion_class, whether an open-year comparison is meaningful)
IDENTITY_CLASS = {
    "legal_or_published_name": "SELF_PUBLISHED_IDENTITY_ASSERTION",
    "legal_name": "SELF_PUBLISHED_IDENTITY_ASSERTION",
    "property_type_schema_org": "SELF_PUBLISHED_IDENTITY_ASSERTION",
    "street_address": "SELF_PUBLISHED_LOCATION_ASSERTION",
    "city": "SELF_PUBLISHED_LOCATION_ASSERTION",
    "state": "SELF_PUBLISHED_LOCATION_ASSERTION",
    "postal_code": "SELF_PUBLISHED_LOCATION_ASSERTION",
    "latitude": "SELF_PUBLISHED_LOCATION_ASSERTION",
    "longitude": "SELF_PUBLISHED_LOCATION_ASSERTION",
    "telephone": "SELF_PUBLISHED_CONTACT_ASSERTION",
    "operating_hours": "SELF_PUBLISHED_OPERATING_HOURS_ASSERTION",
    "founding_date": "SELF_PUBLISHED_DATE_ASSERTION",
    "parent_organization": "SELF_PUBLISHED_OWNERSHIP_ASSERTION",
}

# The destination claims table already uses these unit words. The harvest
# writes `count` / `square_feet`; map to what is on disk rather than adding a
# second vocabulary to one column.
UNIT_MAP = {
    ("gaming_machines", "count"): "machines",
    ("table_games", "count"): "tables",
    ("hotel_rooms", "count"): "rooms",
    ("bingo_seats", "count"): "seats",
    ("restaurants", "count"): "outlets",
    ("employees", "count"): "persons",
    ("gaming_square_feet", "square_feet"): "sq_ft",
    ("convention_square_feet", "square_feet"): "sq_ft",
}

BOUND_DIRECTION_MAP = {"at_least": "LOWER_BOUND", "at_most": "UPPER_BOUND"}


def read(p):
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def det_id(prefix, *parts):
    return prefix + hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:12]


def load_harvest():
    rows = read(HARVEST)
    if not rows:
        raise RuntimeError("gaming_web_harvest_observations.csv is EMPTY - "
                           "refusing to report a clean merge of nothing")
    return rows


def split(rows):
    cap = [r for r in rows if r["observation_kind"] == "CAPACITY_SIGNAL"]
    idn = [r for r in rows if r["observation_kind"] == "FACILITY_IDENTITY"]
    other = [r for r in rows
             if r["observation_kind"] not in ("CAPACITY_SIGNAL", "FACILITY_IDENTITY")]
    if other:
        raise RuntimeError(
            f"{len(other)} harvest rows carry an observation_kind this merge "
            f"has no destination for: "
            f"{sorted({r['observation_kind'] for r in other})}. Refusing to "
            f"drop them silently.")
    return cap, idn


def twin_flags(rows):
    """Byte-identical repeats of one claim on one page.

    588 found two of these in the recovered pile and COLLAPSED them because
    they shared a claim_id. Here the observation ids differ, so collapsing
    would be a de-dupe on a key the upstream did not assert. FLAG, NEVER
    DELETE: the count is reported so `980`'s owner can fix the emitter.
    """
    groups = defaultdict(list)
    for r in rows:
        groups[(r["source_url"], r["metric"], r["value"], r["text_value"],
                r["source_quote"])].append(r["observation_id"])
    flags, n_groups, n_extra = {}, 0, 0
    for k, ids in groups.items():
        if len(ids) < 2:
            continue
        n_groups += 1
        n_extra += len(ids) - 1
        for i in ids:
            flags[i] = ";".join(sorted(ids))
    return flags, n_groups, n_extra


def facility_key(r):
    """A facility_id ONLY where the harvest disambiguated to one facility."""
    if r["facility_attribution_status"] == "SINGLE_FACILITY_TRIBE":
        fid = (r["facility_ids"] or "").strip()
        if ";" in fid:
            raise RuntimeError(
                f"{r['observation_id']} is SINGLE_FACILITY_TRIBE and carries "
                f"a multi-valued facility_ids '{fid}' - the harvest's own "
                f"status and its own key disagree")
        return fid
    return ""


def build_claims(cap, existing_claims, siteobs, twins):
    ck = {(r["source_url"], r["metric"], str(r["value"])): r["claim_id"]
          for r in existing_claims}
    ok = {(r["source_url"], r["metric"], str(r["value"])) for r in siteobs}
    out = []
    for r in cap:
        k = (r["source_url"], r["metric"], r["value"])
        fid = facility_key(r)
        bd_raw = (r["bound_direction"] or "").strip()
        out.append({
            "claim_id": det_id("GSPC-", FAMILY, r["observation_id"]),
            "source_claim_id": r["observation_id"],
            "claim_family": FAMILY,
            "assertion_class": "SELF_PUBLISHED_OPERATOR_CLAIM",
            "assertion_class_note": CLAIM_NOTE,
            "metric": r["metric"],
            "value": r["value"],
            "unit": UNIT_MAP.get((r["metric"], r["unit"]), r["unit"]),
            "unit_as_harvested": r["unit"],
            "value_verbatim": r["value_verbatim"],
            "value_is_bounded": r["value_is_bounded"],
            "bound_direction": BOUND_DIRECTION_MAP.get(bd_raw, bd_raw),
            "bound_direction_as_harvested": bd_raw,
            "bound_basis": r["bound_basis"],
            "measurement_scope": r["measurement_scope"],
            "measurement_scope_basis": r["measurement_scope_basis"],
            "not_summable_with": r["not_summable_with"],
            "measurement_type": "SELF_PUBLISHED_MARKETING_CLAIM",
            "measurement_basis": (
                "a capacity figure the operator publishes about itself on its "
                "own website, regex-extracted with the verbatim sentence "
                "retained; promotional, not audited"),
            "vocabulary_status": "",
            "metric_renamed_from": "",
            "recovery_rule": "",
            "recovery_reason": "",
            "n_occurrences_collapsed": "1",
            "facility_id": fid,
            "facility_name": r["facility_names"] if fid else "",
            "facility_attribution_status": r["facility_attribution_status"],
            "tribe_facility_ids_not_disambiguated": (
                "" if fid else r["facility_ids"]),
            "n_facilities_for_tribe": r["n_facilities_for_tribe"],
            "tribe_id": r["tribe_id"],
            "tribe_name": r["tribe_name"],
            "cedar_uid": r["cedar_uid"],
            "state": r["state"],
            "record_scope": "entity" if r["tribe_id"] else "unresolved",
            "record_scope_basis": (
                "the claim is published on a host operated by one Native "
                "entity; the property it describes is "
                + ("that entity's single gaming facility"
                   if fid else
                   "one of several the entity operates and the page does not "
                      "say which")),
            "inclusion_basis": (
                "published on the website of a tribally owned or operated "
                "gaming property in Cedar's facility universe"),
            "also_in_gaming_property_site_observations": (
                "Y" if k in ok else "N"),
            "duplicate_of_existing_claim_id": ck.get(k, ""),
            "duplicate_within_source_page": twins.get(r["observation_id"], ""),
            "site_host": r["site_host"],
            "source_url": r["source_url"],
            "source_quote": r["source_quote"],
            "source_file": r["source_file"],
            "source_md5": r["source_md5"],
            "retrieved_at": r["retrieved_at"],
            "as_of_date": r["as_of_date"],
            "as_of_date_precision": r["as_of_date_precision"],
            "as_of_date_basis": r["as_of_date_basis"],
            "attribution_basis": (
                "single_facility_tribe" if fid
                else "tribe-level host serving "
                     f"{r['n_facilities_for_tribe']} Cedar facilities - not "
                     "attributable to one"),
            "confidence": r["confidence"],
            "adjudicated_by_script": r["built_by"],
            "built_by": SELF,
            "built_date": TODAY,
        })
    return out


def build_assertions(idn, facilities, twins):
    open_by_fac = {r["facility_id"]: (r.get("open_date", ""),
                                      r.get("open_date_precision", ""))
                   for r in facilities}
    out = []
    for r in idn:
        fid = facility_key(r)
        cls = IDENTITY_CLASS.get(r["metric"])
        if cls is None:
            raise RuntimeError(
                f"identity metric '{r['metric']}' has no assertion_class in "
                f"IDENTITY_CLASS - refusing to publish an untyped assertion")
        cedar_open, cedar_prec = open_by_fac.get(fid, ("", ""))
        agrees = ""
        if r["metric"] == "founding_date":
            agrees = compare_year(r["text_value"], cedar_open)
        else:
            agrees = "not_comparable_this_subclass"
        out.append({
            "assertion_id": det_id("SPA-", FAMILY, r["observation_id"]),
            "assertion_class": cls,
            "assertion_subclass": r["metric"],
            "assertion_class_note": IDENTITY_NOTE,
            "asserted_value": r["text_value"],
            "asserted_value_verbatim": r["source_quote"],
            "asserted_precision": ("year" if r["metric"] == "founding_date"
                                   else ""),
            "asserted_owner_names_tribal_form": "",
            "asserted_owner_is_management_brand": "",
            "cedar_curated_owner": "",
            "agrees_with_curated_owner": "",
            "cedar_open_date": cedar_open if r["metric"] == "founding_date" else "",
            "cedar_open_date_precision": (cedar_prec
                                          if r["metric"] == "founding_date" else ""),
            "agrees_with_cedar_open_year": agrees,
            "facility_id": fid,
            "facility_name": r["facility_names"] if fid else "",
            "facility_attribution_status": r["facility_attribution_status"],
            "tribe_facility_ids_not_disambiguated": ("" if fid
                                                     else r["facility_ids"]),
            "n_facilities_for_tribe": r["n_facilities_for_tribe"],
            "tribe_id": r["tribe_id"],
            "tribe_name": r["tribe_name"],
            "state": r["state"],
            "entity_id": r["tribe_id"],
            "site_host": r["site_host"],
            "source_url": r["source_url"],
            "source_quote": r["source_quote"],
            "retrieved_at": r["retrieved_at"],
            "as_of_date": r["as_of_date"],
            "as_of_date_precision": r["as_of_date_precision"],
            "as_of_date_basis": r["as_of_date_basis"],
            "source_file": r["source_file"],
            "source_md5": r["source_md5"],
            "attribution_basis": ("single_facility_tribe" if fid
                                  else "tribe_level_host_not_disambiguated"),
            "confidence": r["confidence"],
            "built_by_script": r["built_by"],
            "built_date": TODAY,
            "cedar_uid": r["cedar_uid"],
            "record_scope": "entity" if r["tribe_id"] else "unresolved",
            "record_scope_basis": (
                "the assertion is published on a host operated by one Native "
                "entity"),
            "inclusion_basis": (
                "published on the website of a gaming property in Cedar's "
                "facility universe"),
            "duplicate_within_source_page": twins.get(r["observation_id"], ""),
            "not_summable_with": (
                "nothing - this row carries no additive measure. It is an "
                "identity, location, contact or hours statement."),
            "built_by": SELF,
        })
    return out


def compare_year(asserted, cedar):
    a = "".join(ch for ch in (asserted or "") if ch.isdigit())[:4]
    c = "".join(ch for ch in (cedar or "") if ch.isdigit())[:4]
    if not a:
        return "asserted_value_has_no_year"
    if not c:
        return "cedar_has_no_open_year"
    return "AGREES" if a == c else f"DIFFERS_{a}_vs_{c}"


def money_columns(rows):
    """Any column whose name says dollars. Must stay empty in both tables."""
    if not rows:
        return []
    bad = ("usd", "amount", "revenue", "dollar", "par_", "_paid")
    return [c for c in rows[0] if any(b in c.lower() for b in bad)]


def do_merge(dry):
    harvest = load_harvest()
    cap, idn = split(harvest)
    twins, tgroups, textra = twin_flags(harvest)

    claim_rows = build_claims(cap, read(CLAIMS), read(SITEOBS), twins)
    assert_rows = build_assertions(idn, read(FACILITIES), twins)

    assert len(claim_rows) == len(cap) == 309 or len(claim_rows) == len(cap)
    assert len(assert_rows) == len(idn)

    c_fields = list(claim_rows[0].keys())
    a_fields = list(assert_rows[0].keys())

    _, cf, crep = CP.merge_table(
        CLAIMS, claim_rows, c_fields, ["claim_id"],
        dry_run=dry, backup_tag=TAG)
    _, af, arep = CP.merge_table(
        ASSERTS, assert_rows, a_fields, ["assertion_id"],
        dry_run=dry, backup_tag=TAG)

    for rep, name in ((crep, CLAIMS.name), (arep, ASSERTS.name)):
        if rep.cols_lost:
            raise RuntimeError(f"{name} would lose columns {rep.cols_lost}")
        if rep.rows_after < rep.rows_before:
            raise RuntimeError(
                f"{name} row conservation FAILED: {rep.rows_before} -> "
                f"{rep.rows_after}")

    rep = {
        "built_by": SELF,
        "built_date": TODAY,
        "dry_run": dry,
        "harvest_rows": len(harvest),
        "capacity_signal": len(cap),
        "facility_identity": len(idn),
        "row_conservation": (
            f"{len(harvest)} staged = {len(cap)} capacity + {len(idn)} "
            f"identity; {crep.rows_appended} + {arep.rows_appended} appended "
            f"this run (0 + 0 on a re-run, by design)"),
        "claims": {
            "rows_before": crep.rows_before, "rows_after": crep.rows_after,
            "rows_appended": crep.rows_appended,
            "rows_matched_existing": crep.rows_matched,
            "cols_before": len(crep.cols_before), "cols_after": len(cf),
            "cols_added": crep.cols_added,
        },
        "assertions": {
            "rows_before": arep.rows_before, "rows_after": arep.rows_after,
            "rows_appended": arep.rows_appended,
            "rows_matched_existing": arep.rows_matched,
            "cols_before": len(arep.cols_before), "cols_after": len(af),
            "cols_added": arep.cols_added,
        },
        "qualifier_1_lower_bounds": {
            "capacity_rows_bounded_Y": sum(
                1 for r in cap if r["value_is_bounded"] == "Y"),
            "capacity_rows_bounded_N": sum(
                1 for r in cap if r["value_is_bounded"] == "N"),
            "note": "a bound is not a count; bound_direction is carried and "
                    "bound_direction_as_harvested keeps the source word",
        },
        "qualifier_2_measurement_scope": {
            "UNVERIFIED_SCOPE": sum(
                1 for r in cap if r["measurement_scope"] == "UNVERIFIED_SCOPE"),
            "SUBPROPERTY_QUALIFIED": sum(
                1 for r in cap
                if r["measurement_scope"] == "SUBPROPERTY_QUALIFIED"),
            "note": "the two columns are NEW on the destination table; blank "
                    "on the 270 pre-existing rows means NOT RECORDED BY THAT "
                    "EXTRACTION, never 'scope verified'",
        },
        "qualifier_3_facility_keying": {
            "SINGLE_FACILITY_TRIBE": sum(
                1 for r in harvest
                if r["facility_attribution_status"] == "SINGLE_FACILITY_TRIBE"),
            "TRIBE_LEVEL_MULTI_FACILITY_NOT_DISAMBIGUATED": sum(
                1 for r in harvest
                if r["facility_attribution_status"] != "SINGLE_FACILITY_TRIBE"),
            "distinct_facility_ids_keyed": len(
                {r["facility_id"] for r in claim_rows + assert_rows
                 if r["facility_id"]}),
            "distinct_tribes_left_at_tribe_grain": len(
                {r["tribe_id"] for r in harvest
                 if r["facility_attribution_status"] != "SINGLE_FACILITY_TRIBE"}),
        },
        "flagged_not_dropped": {
            "capacity_rows_duplicating_an_existing_claim": sum(
                1 for r in claim_rows if r["duplicate_of_existing_claim_id"]),
            "capacity_rows_also_in_site_observations": sum(
                1 for r in claim_rows
                if r["also_in_gaming_property_site_observations"] == "Y"),
            "byte_identical_repeat_groups_in_harvest": tgroups,
            "extra_rows_those_groups_carry": textra,
            "note": "UPSTREAM DEFECT in code/980: one page emitting the same "
                    "JSON-LD block twice yields two observation_ids for one "
                    "sentence. Flagged, not collapsed - collapsing would be a "
                    "de-dupe on a key the upstream did not assert.",
        },
        "money_conservation": {
            "claims_money_columns": money_columns(claim_rows),
            "assertions_money_columns": money_columns(assert_rows),
            "note": "VACUOUS BY CONSTRUCTION and asserted as such: neither "
                    "destination table has a dollar column and this merge "
                    "adds none. `employees` and `*_square_feet` are counts.",
        },
        "assertion_classes_added": dict(
            Counter(r["assertion_class"] for r in assert_rows)),
        "capacity_metrics": dict(Counter(r["metric"] for r in cap)),
    }
    if not dry:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    return rep


def verify(selftest=False):
    fails = []
    harvest = load_harvest()
    cap, idn = split(harvest)
    claims = read(CLAIMS)
    asserts = read(ASSERTS)
    mine_c = [r for r in claims if r.get("claim_family") == FAMILY]
    mine_a = [r for r in asserts if r.get("built_by") == SELF]

    # V1 -- every staged row reached a destination, exactly once.
    if len(mine_c) != len(cap):
        fails.append(f"V1 {len(cap)} capacity staged, {len(mine_c)} in "
                     f"{CLAIMS.name}")
    if len(mine_a) != len(idn):
        fails.append(f"V1 {len(idn)} identity staged, {len(mine_a)} in "
                     f"{ASSERTS.name}")

    # V2 -- NOTHING WAS LOST from the pre-existing rows.
    if len(claims) < 270:
        fails.append(f"V2 claims table fell below its 270-row floor: "
                     f"{len(claims)}")
    if len(asserts) < 622:
        fails.append(f"V2 assertions table fell below its 622-row floor: "
                     f"{len(asserts)}")

    # V3 -- a facility_id is present on EXACTLY the disambiguated rows.
    for label, mine in (("claims", mine_c), ("assertions", mine_a)):
        bad = [r for r in mine
               if bool(r.get("facility_id"))
               != (r.get("facility_attribution_status") == "SINGLE_FACILITY_TRIBE")]
        if bad:
            fails.append(f"V3 {label}: {len(bad)} rows key a facility_id "
                         f"against their own attribution status "
                         f"(e.g. {bad[0].get('claim_id') or bad[0].get('assertion_id')})")

    # V4 -- every bounded capacity row still says so, and says which way.
    b = [r for r in mine_c if r.get("value_is_bounded") == "Y"]
    if any(not r.get("bound_direction") for r in b):
        fails.append("V4 a bounded row lost its bound_direction")
    staged_bounded = sum(1 for r in cap if r["value_is_bounded"] == "Y")
    if len(b) != staged_bounded:
        fails.append(f"V4 {staged_bounded} lower bounds staged, {len(b)} "
                     f"survived the merge")

    # V5 -- measurement_scope survived, and its blank is documented.
    staged_scope = Counter(r["measurement_scope"] for r in cap)
    live_scope = Counter(r.get("measurement_scope", "") for r in mine_c)
    for k, v in staged_scope.items():
        if live_scope.get(k, 0) != v:
            fails.append(f"V5 measurement_scope '{k}': staged {v}, live "
                         f"{live_scope.get(k, 0)}")

    # V6 -- not_summable_with is populated on every capacity row.
    if any(not r.get("not_summable_with") for r in mine_c):
        fails.append("V6 a capacity row has an empty not_summable_with")

    # V7 -- NO DOLLAR COLUMN was introduced.
    for label, rows in (("claims", claims), ("assertions", asserts)):
        m = money_columns(rows)
        if m:
            fails.append(f"V7 {label} now carries a money-named column: {m}")

    # V8 -- a self-published row is never typed as a regulator measurement.
    bad = [r for r in mine_c
           if "OFFICIAL" in (r.get("measurement_type") or "").upper()
           or "REGULATOR" in (r.get("measurement_type") or "").upper()]
    if bad:
        fails.append(f"V8 {len(bad)} self-published rows typed as official")

    if selftest:
        # A check that has never failed on purpose is not known to work.
        # Inject each violation into a COPY of the row set and assert the
        # named invariant is the one that fires.
        probes = []
        r0 = dict(mine_c[0]) if mine_c else {}

        def fires(name, rows_c, rows_a, expect):
            f = []
            if len(rows_c) != len(cap):
                f.append("V1")
            bad = [r for r in rows_c
                   if bool(r.get("facility_id"))
                   != (r.get("facility_attribution_status") == "SINGLE_FACILITY_TRIBE")]
            if bad:
                f.append("V3")
            if any(r.get("value_is_bounded") == "Y" and not r.get("bound_direction")
                   for r in rows_c):
                f.append("V4")
            if any(not r.get("not_summable_with") for r in rows_c):
                f.append("V6")
            probes.append((name, expect, expect in f, f))

        bad3 = [dict(r) for r in mine_c]
        for r in bad3:
            if r["facility_attribution_status"] != "SINGLE_FACILITY_TRIBE":
                r["facility_id"] = "CCP-999999"
                break
        fires("facility_id on a non-disambiguated row", bad3, mine_a, "V3")

        bad4 = [dict(r) for r in mine_c]
        for r in bad4:
            if r["value_is_bounded"] == "Y":
                r["bound_direction"] = ""
                break
        fires("bounded row with no direction", bad4, mine_a, "V4")

        bad6 = [dict(r) for r in mine_c]
        if bad6:
            bad6[0]["not_summable_with"] = ""
        fires("capacity row with no not_summable_with", bad6, mine_a, "V6")

        fires("clean set", [dict(r) for r in mine_c], mine_a, "__none__")

        print("\n  SELFTEST (a check that has never failed on purpose is not "
              "known to work)")
        for name, expect, ok, got in probes:
            if expect == "__none__":
                ok = not got
                print(f"    {'PASS' if ok else 'FAIL'}  {name}: fired {got or 'nothing'}")
                if not ok:
                    fails.append(f"SELFTEST clean set fired {got}")
            else:
                print(f"    {'PASS' if ok else 'FAIL'}  {name}: expected "
                      f"{expect}, fired {got}")
                if not ok:
                    fails.append(f"SELFTEST {name} did not fire {expect}")
        _ = r0

    print(f"\n  {CLAIMS.name}: {len(claims):,} rows ({len(mine_c):,} from this "
          f"merge)")
    print(f"  {ASSERTS.name}: {len(asserts):,} rows ({len(mine_a):,} from this "
          f"merge)")
    print(f"  staged: {len(harvest):,} = {len(cap)} capacity + {len(idn)} identity")
    if fails:
        print("\n  VERIFY FAILED")
        for f in fails:
            print("   -", f)
        return 1
    print("\n  VERIFY OK - 8 invariants")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["plan", "merge", "verify"])
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.stage in ("plan", "merge"):
        rep = do_merge(dry=(a.stage == "plan"))
        print(json.dumps(rep, indent=2))
        return 0
    return verify(a.selftest)


if __name__ == "__main__":
    sys.exit(main())
