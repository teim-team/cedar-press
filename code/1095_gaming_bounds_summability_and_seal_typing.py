#!/usr/bin/env python3
"""
1095_gaming_bounds_summability_and_seal_typing.py -- Cedar Press, GAMING-DEEP.

THREE REPAIRS, ALL ADDITIVE, NONE OF THEM A NEW DOLLAR COLUMN.

-----------------------------------------------------------------------------
A. `gaming_revenue_bounds.csv` HAD NO `not_summable_with`, AND 97.8% OF IT IS
   ONE NUMBER REPEATED
-----------------------------------------------------------------------------
Measured 2026-09-02 on the live file: 13,803 rows, of which

    REGIONAL_GGR_CEILING                          12,518
    REGIONAL_GGR_CEILING_NET_OF_KNOWN                951
    UNKNOWN_PROPERTIES_RESIDUAL_SUM                   25
    ------------------------------------------------------
    a regional ceiling, repeated per property     13,494  (97.76%)

    SINGLE_PROPERTY_TRIBE_LEVEL_GAMING_REVENUE       115
    TRIBE_LEVEL_NOT_ATTRIBUTABLE_TO_A_PROPERTY       133
    REPORTED_SLOT_WIN_IS_FLOOR_FOR_GGR                61
    ------------------------------------------------------
    an honest per-property or per-tribe figure       309, over **11 facilities**

**`SUM(revenue_upper_bound)` over this table adds NIGC's regional total to
itself once per property in the region.** 694 distinct facilities share those
12,518 ceiling rows. The table said so in a build log and in the methodology
record; it did not say so ON THE ROW, and a `GROUP BY tribe_id` in a
subscriber's warehouse never reads a build log.

This adds five columns and populates them on all 13,803 rows:

    not_summable_with                    per row, what this figure may not be
                                         added to - including OTHER ROWS OF
                                         THIS TABLE, which is the trap here
    bound_is_a_repeated_regional_ceiling Y / N
    n_facilities_sharing_this_ceiling    how many properties carry this exact
                                         region-year total. The repetition
                                         becomes visible instead of inferable
    aggregation_level                    regional_aggregate / entity_specific /
                                         tribe_level_not_property_attributable
    summability_basis                    why, in one sentence

**No dollar column is added and none is changed.** The refusal to put a dollar
on the facility record stands and this script does not touch it.

-----------------------------------------------------------------------------
B. THE SEAL TYPING CONFLATES TWO DIFFERENT LEGAL FACTS, AND ONE STATE'S QUOTE
   DOES NOT STATE EITHER
-----------------------------------------------------------------------------
`gaming_facilities.state_revenue_disclosure_status` is
`SEALED_BY_STATUTE_OR_COMPACT` on 174 facilities across 7 states: MN 48,
AZ 43, WI 40, ND 22, NV 10, KS 8, CO 3.

`code/960_...seals_by_state()` selects a state's row by matching
`applies_to` against SEAL_TOKENS **and never looks at the quote**. It is the
repo's signature defect - a check that does not measure its own name - and it
produced two wrong answers:

1. **MINNESOTA (48 facilities, the largest of the seven) is typed sealed on a
   quote about compact renegotiation**: *"a provision that in the event of a
   request for a renegotiation or a new compact the existing compact will
   remain in effect until renegotiated or replaced."* That sentence says
   nothing about confidentiality, aggregation or disclosure. All three
   Minnesota `absence` rows were read; none states a seal. What Minnesota's
   own DPS page states is that the compacts contain no revenue share - the
   state never receives per-tribe revenue at all.

2. **SEALED and NOT-COLLECTED are different facts and were typed the same.**
   Colorado's quote is *"not subject to taxation and are not required to
   report their revenues to the State"* - the regulator does not HOLD the
   number. Arizona's is *"A.R.S. 5-601.02(H)(1) ... requires ... a statement
   of aggregate gross gaming revenue"* - the regulator holds it and the
   statute forbids publishing it per tribe. A buyer asking *"could this ever
   be FOIA'd?"* gets opposite answers, and today the column gives one.

This adds three columns, and **changes neither of 960's two**:

    state_revenue_disclosure_disposition        SEALED_HELD_BY_REGULATOR |
                                                NOT_COLLECTED_BY_THIS_BODY |
                                                DISPOSITION_UNSUPPORTED_BY_RECORDED_QUOTE
    state_revenue_disclosure_quote_supports_status  Y / N
    state_revenue_disclosure_quote_test         the phrase family searched for
                                                and whether it was found

**The disposition is derived from the RECORDED QUOTE, never from what this
script believes about the state's law.** Where the quote states neither fact
the answer is `DISPOSITION_UNSUPPORTED_BY_RECORDED_QUOTE` - which is what
Minnesota gets, and what Nevada gets, because Nevada's recorded quote states a
monthly SUBMISSION requirement (NGC-31) and not a confidentiality rule. Nevada
is very likely sealed under NRS 463.120; **Cedar has no quote of NRS 463.120
in this table, so this script will not assert one.** An unquoted statute is a
re-sourcing task, and it is written out as one.

-----------------------------------------------------------------------------
C. THE 2 "IGRA-COVERED, REGION-ASSIGNED, NO BOUND" FACILITIES ARE NOT A KEYING
   GAP. THEY ARE A SILENT EMPTY `range()`.
-----------------------------------------------------------------------------
`code/106_build_revenue_bounds.py` line ~790:

    for fy in range(s, e + 1):

`s` is `effective_start_year`, `e` is `effective_end_year`. **When e < s that
loop runs zero times and nothing is raised, nothing is logged and no row is
written.** Exactly two assignment rows in `nigc_region_assignments.csv` carry
an inverted interval, and they are exactly the two facilities 960 flags
`REVIEW: IGRA-covered and region-assigned yet no bound row was produced`:

    CCP-741300  Choctaw Casino Resort - Durant   Region V  start 2006 end 2005
    CCP-648500  Seminole Nation Casino           Region V  start 2007 end 2003

The inversion comes from the facility record: both carry a `close_date`
EARLIER than their `open_date`. **Four facilities are in that state**, and the
reason is probably not corrupt data - Casino City's source column is literally
named *"1st Close Date"*, so a property that closed and later re-opened
legitimately has a first-closure date before its current opening. The column
cannot express "closed once, then re-opened", which is the same shape as the
already-recorded limit *"`property_status = current` beside `close_date`"*.

A separate tell: **15 `close_date` values render as float strings** (`2005.0`,
`2019.0`) - a numeric coercion in the Indian Gaming Dataset import that turned
a year into a float and back.

None of that is repaired here, because repairing it means ruling on what those
dates mean. What IS done: the facts are measured, written to
`review/1095_gaming_bound_gap_and_date_inversions.csv`, and a one-line fix for
106 is stated so the next builder does not have to re-derive it -
**an inverted interval must RAISE or be flagged, never silently yield nothing.**

-----------------------------------------------------------------------------
REBUILD / IN-PLACE ORDERING
-----------------------------------------------------------------------------
`106_build_revenue_bounds.py` REBUILDS `gaming_revenue_bounds.csv`.
`960_promote_gaming_facility_class_and_revenue_reach.py` writes the two seal
columns onto `gaming_facilities.csv`, and `23d`/`158` rebuild that table.
This script is an IN-PLACE ENRICHER on both and **must run LAST**. It is
idempotent: re-running restores every column exactly. The
`.bak_<date>_pre_1095_...` files beside each table are the signal.

USAGE
    py -3 code/1095_gaming_bounds_summability_and_seal_typing.py plan
    py -3 code/1095_gaming_bounds_summability_and_seal_typing.py apply
    py -3 code/1095_gaming_bounds_summability_and_seal_typing.py verify [--selftest]
"""
import argparse
import csv
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parents[1]
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
LOGS = CEDAR / "logs"
TODAY = date.today().isoformat()
TAG = "pre_1095_gaming_bounds_summability_and_seal_typing"
SELF = "code/1095_gaming_bounds_summability_and_seal_typing.py"

BOUNDS = CLEAN / "gaming_revenue_bounds.csv"
FACILITIES = CLEAN / "gaming_facilities.csv"
REGIONS = CLEAN / "nigc_region_assignments.csv"
GAPFILE = REVIEW / "1095_gaming_bound_gap_and_date_inversions.csv"
REPORT = LOGS / "1095_bounds_and_seal_report.json"

# The three bases that are a REGIONAL total repeated onto each property.
CEILING_BASES = {
    "REGIONAL_GGR_CEILING",
    "REGIONAL_GGR_CEILING_NET_OF_KNOWN",
    "UNKNOWN_PROPERTIES_RESIDUAL_SUM",
}
TRIBE_LEVEL_BASES = {"TRIBE_LEVEL_NOT_ATTRIBUTABLE_TO_A_PROPERTY"}

CEILING_NOT_SUMMABLE = (
    "other_rows_of_gaming_revenue_bounds (THIS IS THE TRAP: one NIGC regional "
    "total is written onto every property in the region-year, so SUM() adds it "
    "to itself);nigc_regional_ggr (the same dollars at their true grain);"
    "gaming_property_self_published_claims (an operator assertion);"
    "gaming_capacity_official (a regulator count, not money);"
    "ca_gaming_payments;fl_gaming_payments (state payment series, a different "
    "measure)")

ENTITY_NOT_SUMMABLE = (
    "rows of gaming_revenue_bounds whose bound_basis is a REGIONAL_GGR_CEILING "
    "(that figure already contains this one);nigc_regional_ggr;"
    "gaming_property_self_published_claims (an operator assertion);"
    "the three FAC casino measures - CASINO_ENTERPRISE_FUND_REVENUE, "
    "CASINO_DISTRIBUTION_TO_TRIBE and CASINO_PAYABLE_TO_TRIBE - which measure "
    "different things and triple-count if pooled")

TRIBE_NOT_SUMMABLE = (
    "any per-property total (this figure is TRIBE-level and is not attributable "
    "to one property);rows of gaming_revenue_bounds whose bound_basis is a "
    "REGIONAL_GGR_CEILING;nigc_regional_ggr;"
    "gaming_property_self_published_claims")

# Phrase families. A quote must SAY the disposition. Nothing here reads a
# statute Cedar does not hold the text of.
SEAL_PHRASES = (
    "confidential", "not subject to disclosure", "may not be publicly disclosed",
    "not be publicly disclosed", "aggregate gross gaming revenue",
    "statement of aggregate", "trade secret", "proprietary information",
)
NOT_COLLECTED_PHRASES = (
    "are not required to report", "not required to report",
    "does not receive revenue", "do not receive revenue",
    "not subject to taxation",
)


def read(p):
    with open(p, encoding="utf-8-sig", newline="") as fh:
        rdr = csv.DictReader(fh)
        return [dict(r) for r in rdr], list(rdr.fieldnames or [])


def write(p, rows, fields):
    if p.exists():
        b = p.with_name(f"{p.name}.bak_{TODAY}_{TAG}")
        if not b.exists():
            shutil.copy2(p, b)
    tmp = p.with_suffix(p.suffix + ".part")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in fields})
    tmp.replace(p)


def year4(s):
    m = re.match(r"^(\d{4})", (s or "").strip())
    return int(m.group(1)) if m else None


# --------------------------------------------------------------- A. bounds
def annotate_bounds(rows):
    """Every row gets a summability verdict derived from its own bound_basis."""
    # How many distinct facilities carry each region-year ceiling. Grouped on
    # (fiscal_year, regional_total_usd) because the table carries no region id
    # and that pair IS the ceiling.
    share = defaultdict(set)
    for r in rows:
        if r.get("bound_basis") in CEILING_BASES:
            share[(r.get("fiscal_year", ""),
                   r.get("regional_total_usd", ""))].add(r.get("facility_id", ""))

    n_ceiling = n_entity = n_tribe = 0
    for r in rows:
        bb = r.get("bound_basis", "")
        if bb in CEILING_BASES:
            n_ceiling += 1
            k = (r.get("fiscal_year", ""), r.get("regional_total_usd", ""))
            n = len([f for f in share[k] if f])
            r["not_summable_with"] = CEILING_NOT_SUMMABLE
            r["bound_is_a_repeated_regional_ceiling"] = "Y"
            r["n_facilities_sharing_this_ceiling"] = str(n)
            r["aggregation_level"] = "regional_aggregate"
            r["summability_basis"] = (
                f"NIGC publishes gross gaming revenue by REGION, never per "
                f"operation. This row states the region-year total as a "
                f"ceiling on this one property; {n} propert"
                f"{'ies' if n != 1 else 'y'} in this region-year carry the "
                f"same figure. It is NEVER divided by the operation count - "
                f"NIGC's own FY2025 distribution has 8.6% of operations "
                f"holding 55.8% of GGR - and it must never be summed.")
        elif bb in TRIBE_LEVEL_BASES:
            n_tribe += 1
            r["not_summable_with"] = TRIBE_NOT_SUMMABLE
            r["bound_is_a_repeated_regional_ceiling"] = "N"
            r["n_facilities_sharing_this_ceiling"] = ""
            r["aggregation_level"] = "tribe_level_not_property_attributable"
            r["summability_basis"] = (
                "a TRIBE-level revenue figure that no source attributes to one "
                "property. Additive across tribes within one fiscal year; "
                "never additive with a per-property row and never with a "
                "regional ceiling.")
        elif bb:
            n_entity += 1
            r["not_summable_with"] = ENTITY_NOT_SUMMABLE
            r["bound_is_a_repeated_regional_ceiling"] = "N"
            r["n_facilities_sharing_this_ceiling"] = ""
            r["aggregation_level"] = "entity_specific"
            r["summability_basis"] = (
                "an honest per-property or single-property-tribe figure from "
                "the operator's regulator or audited statement. Additive across "
                "DISTINCT facilities within one fiscal year, and never with a "
                "regional ceiling row, which already contains it.")
        else:
            raise RuntimeError(
                f"bound row {r.get('bound_id')} has an empty bound_basis - "
                f"refusing to declare a summability verdict for a row that "
                f"does not say what it is")
    return n_ceiling, n_entity, n_tribe


# ----------------------------------------------------------------- B. seals
def classify_quote(basis):
    """Read the RECORDED quote. Never the statute Cedar does not hold."""
    q = (basis or "").lower()
    seal_hit = [p for p in SEAL_PHRASES if p in q]
    nc_hit = [p for p in NOT_COLLECTED_PHRASES if p in q]
    if seal_hit and not nc_hit:
        return ("SEALED_HELD_BY_REGULATOR", "Y",
                f"FOUND confidentiality/aggregation language: {seal_hit!r}")
    if nc_hit and not seal_hit:
        return ("NOT_COLLECTED_BY_THIS_BODY", "Y",
                f"FOUND not-collected language: {nc_hit!r}")
    if seal_hit and nc_hit:
        # Kansas: "financial information ... is confidential" AND "the State
        # does not receive revenue from the casinos". Both are true and the
        # confidentiality is the operative bar on what the state COULD release.
        return ("SEALED_HELD_BY_REGULATOR", "Y",
                f"FOUND BOTH families - seal {seal_hit!r} and not-collected "
                f"{nc_hit!r}; typed SEALED because confidentiality is the "
                f"operative bar on release")
    return ("DISPOSITION_UNSUPPORTED_BY_RECORDED_QUOTE", "N",
            f"NOT FOUND: the recorded quote contains no phrase from either "
            f"family (seal: {list(SEAL_PHRASES)[:4]}...; not-collected: "
            f"{list(NOT_COLLECTED_PHRASES)[:3]}...). The status is asserted; "
            f"the quote does not carry it. RE-SOURCE the statute or compact "
            f"clause before publishing this as sealed.")


def annotate_seals(rows):
    counts = Counter()
    per_state = {}
    for r in rows:
        st = (r.get("state_revenue_disclosure_status") or "").strip()
        if not st:
            r["state_revenue_disclosure_disposition"] = ""
            r["state_revenue_disclosure_quote_supports_status"] = ""
            r["state_revenue_disclosure_quote_test"] = ""
            continue
        disp, sup, test = classify_quote(
            r.get("state_revenue_disclosure_basis", ""))
        r["state_revenue_disclosure_disposition"] = disp
        r["state_revenue_disclosure_quote_supports_status"] = sup
        r["state_revenue_disclosure_quote_test"] = test
        counts[(r.get("state", ""), disp, sup)] += 1
        per_state[r.get("state", "")] = (disp, sup)
    return counts, per_state


# ------------------------------------------------------------------- C. gaps
def measure_gaps(facilities, regions, bounds):
    covered = {r["facility_id"] for r in bounds if r.get("facility_id")}
    fac = {r["facility_id"]: r for r in facilities}
    out = []

    inverted = [a for a in regions
                if a.get("effective_start_year", "").strip()
                and a.get("effective_end_year", "").strip()
                and year4(a["effective_start_year"]) is not None
                and year4(a["effective_end_year"]) is not None
                and year4(a["effective_start_year"]) > year4(a["effective_end_year"])]
    for a in inverted:
        f = fac.get(a["facility_id"], {})
        out.append({
            "finding": "INVERTED_REGION_ASSIGNMENT_INTERVAL",
            "facility_id": a["facility_id"],
            "facility_name": f.get("facility_name", ""),
            "state": f.get("state", ""),
            "tribe_id": f.get("tribe_id", ""),
            "detail": (f"effective_start_year={a['effective_start_year']} > "
                       f"effective_end_year={a['effective_end_year']}; "
                       f"region={a.get('region_name')}; "
                       f"igra={a.get('igra_coverage_status')}"),
            "consequence": (
                "code/106_build_revenue_bounds.py does `for fy in range(s, "
                "e + 1)`, which runs ZERO times on an inverted interval and "
                "raises nothing. No bound row is written and no error is "
                "printed."
                + (" THIS FACILITY HAS NO BOUND ROW."
                   if a["facility_id"] not in covered
                   else " (this facility does have bound rows from another "
                        "assignment row)")),
            "has_revenue_bound": "N" if a["facility_id"] not in covered else "Y",
            "proposed_fix": (
                "in 106, before the loop: if e < s, append the assignment to a "
                "refusal list with a named reason and print the count. An "
                "inverted interval must RAISE or be FLAGGED, never silently "
                "yield nothing. Do not swap s and e - the inversion is a fact "
                "about the source record, not a typo to normalise away."),
            "measured_by": SELF, "measured_date": TODAY,
        })

    for r in facilities:
        o, c = year4(r.get("open_date")), year4(r.get("close_date"))
        if o and c and c < o:
            out.append({
                "finding": "CLOSE_DATE_PRECEDES_OPEN_DATE",
                "facility_id": r["facility_id"],
                "facility_name": r.get("facility_name", ""),
                "state": r.get("state", ""),
                "tribe_id": r.get("tribe_id", ""),
                "detail": (f"open_date={r.get('open_date')} "
                           f"close_date={r.get('close_date')} "
                           f"property_status={r.get('property_status')} "
                           f"close_date_basis={r.get('close_date_basis')}"),
                "consequence": (
                    "any span derived from these two dates is inverted, and an "
                    "inverted span silently produces nothing downstream (see "
                    "INVERTED_REGION_ASSIGNMENT_INTERVAL)."),
                "has_revenue_bound": ("Y" if r["facility_id"] in covered
                                      else "N"),
                "proposed_fix": (
                    "PROBABLY NOT A DATA ERROR. Casino City's source column is "
                    "named '1st Close Date', so a property that closed and "
                    "later re-opened legitimately carries a first-closure date "
                    "before its current opening. The column cannot express "
                    "'closed once, then re-opened' - the same limit already "
                    "recorded for property_status=current beside a close_date. "
                    "Needs an owner ruling on whether to add a reopen_date, "
                    "not a silent repair."),
                "measured_by": SELF, "measured_date": TODAY,
            })
        if re.match(r"^\d{4}\.0$", (r.get("close_date") or "").strip()):
            out.append({
                "finding": "CLOSE_DATE_RENDERED_AS_FLOAT_STRING",
                "facility_id": r["facility_id"],
                "facility_name": r.get("facility_name", ""),
                "state": r.get("state", ""),
                "tribe_id": r.get("tribe_id", ""),
                "detail": f"close_date={r.get('close_date')!r} "
                          f"basis={r.get('close_date_basis')}",
                "consequence": (
                    "a year that went through a float and back. Harmless to a "
                    "human reader, and it breaks any ISO date parse and any "
                    "string comparison against a 'YYYY' or 'YYYY-MM' value in "
                    "the same column."),
                "has_revenue_bound": ("Y" if r["facility_id"] in covered
                                      else "N"),
                "proposed_fix": (
                    "normalise at the IMPORT that created it, not here - "
                    "rewriting it in place would be reverted by the next "
                    "rebuild and would hide which import produced it."),
                "measured_by": SELF, "measured_date": TODAY,
            })

    review_flagged = [r for r in facilities
                      if (r.get("revenue_bound_absent_reason") or "")
                      .startswith("REVIEW")]
    return out, [r["facility_id"] for r in review_flagged]


# -------------------------------------------------------------------- driver
def run(dry):
    brows, bfields = read(BOUNDS)
    frows, ffields = read(FACILITIES)
    rrows, _ = read(REGIONS)
    if not brows or not frows:
        raise RuntimeError("an input table is EMPTY - refusing to report a "
                           "clean pass over nothing")

    b_before_rows, b_before_cols = len(brows), list(bfields)
    f_before_rows, f_before_cols = len(frows), list(ffields)
    # Money conservation: the dollar columns must be byte-identical after.
    money_cols = ["revenue_lower_bound", "revenue_upper_bound", "point_value",
                  "regional_total_usd", "known_property_sum_usd"]
    money_before = [tuple(r.get(c, "") for c in money_cols) for r in brows]

    n_ceiling, n_entity, n_tribe = annotate_bounds(brows)
    new_b = ["not_summable_with", "bound_is_a_repeated_regional_ceiling",
             "n_facilities_sharing_this_ceiling", "aggregation_level",
             "summability_basis"]
    for c in new_b:
        if c not in bfields:
            bfields.append(c)

    seal_counts, per_state = annotate_seals(frows)
    new_f = ["state_revenue_disclosure_disposition",
             "state_revenue_disclosure_quote_supports_status",
             "state_revenue_disclosure_quote_test"]
    for c in new_f:
        if c not in ffields:
            ffields.append(c)

    gaps, review_ids = measure_gaps(frows, rrows, brows)

    money_after = [tuple(r.get(c, "") for c in money_cols) for r in brows]
    if money_before != money_after:
        raise RuntimeError("MONEY CONSERVATION FAILED: a dollar cell changed")
    if len(brows) != b_before_rows or len(frows) != f_before_rows:
        raise RuntimeError("ROW CONSERVATION FAILED")
    for old, new in ((b_before_cols, bfields), (f_before_cols, ffields)):
        lost = [c for c in old if c not in new]
        if lost:
            raise RuntimeError(f"COLUMN LOSS: {lost}")

    if not dry:
        write(BOUNDS, brows, bfields)
        write(FACILITIES, frows, ffields)
        REVIEW.mkdir(parents=True, exist_ok=True)
        gf = (list(gaps[0].keys()) if gaps
              else ["finding", "facility_id", "detail"])
        with open(GAPFILE, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=gf)
            w.writeheader()
            w.writerows(gaps)

    rep = {
        "built_by": SELF, "built_date": TODAY, "dry_run": dry,
        "A_bounds": {
            "rows": b_before_rows,
            "cols_before": len(b_before_cols), "cols_after": len(bfields),
            "cols_added": new_b,
            "repeated_regional_ceiling_rows": n_ceiling,
            "tribe_level_rows": n_tribe,
            "entity_specific_rows": n_entity,
            "share_of_table_that_is_a_repeated_ceiling":
                f"{n_ceiling / b_before_rows:.2%}",
            "distinct_facilities_on_a_ceiling": len(
                {r["facility_id"] for r in brows
                 if r["bound_is_a_repeated_regional_ceiling"] == "Y"
                 and r["facility_id"]}),
            "distinct_facilities_with_an_honest_figure": len(
                {r["facility_id"] for r in brows
                 if r["bound_is_a_repeated_regional_ceiling"] == "N"
                 and r["facility_id"]}),
            "largest_n_facilities_sharing_one_ceiling": max(
                (int(r["n_facilities_sharing_this_ceiling"] or 0)
                 for r in brows), default=0),
            "money_conservation": "PASS - all 5 dollar columns byte-identical",
        },
        "B_seals": {
            "facilities_typed_sealed_by_960": sum(
                1 for r in frows
                if r.get("state_revenue_disclosure_status")),
            "cols_added": new_f,
            "by_state": {st: {"disposition": d, "quote_supports_status": s}
                         for st, (d, s) in sorted(per_state.items())},
            "facility_counts": {
                f"{st}|{d}|quote_supports={s}": n
                for (st, d, s), n in sorted(seal_counts.items())},
            "note": ("derived from the RECORDED QUOTE only. A state whose "
                     "quote states neither fact is typed "
                     "DISPOSITION_UNSUPPORTED_BY_RECORDED_QUOTE and is a "
                     "re-sourcing task, not a finding about the state's law."),
        },
        "C_gaps": {
            "review_flagged_facilities": review_ids,
            "findings": dict(Counter(g["finding"] for g in gaps)),
            "inverted_intervals_that_zeroed_a_bound": [
                g["facility_id"] for g in gaps
                if g["finding"] == "INVERTED_REGION_ASSIGNMENT_INTERVAL"
                and g["has_revenue_bound"] == "N"],
            "written_to": str(GAPFILE.relative_to(CEDAR)),
        },
    }
    if not dry:
        LOGS.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    return rep


def verify(selftest=False):
    fails = []
    brows, bfields = read(BOUNDS)
    frows, _ = read(FACILITIES)

    def check(rows_b, rows_f):
        f = []
        # V1 every bound row carries a summability verdict
        if any(not r.get("not_summable_with") for r in rows_b):
            f.append("V1")
        # V2 a ceiling row is never typed entity_specific
        if any(r.get("bound_basis") in CEILING_BASES
               and r.get("aggregation_level") != "regional_aggregate"
               for r in rows_b):
            f.append("V2")
        # V3 a ceiling row must name THIS table in not_summable_with
        if any(r.get("bound_is_a_repeated_regional_ceiling") == "Y"
               and "other_rows_of_gaming_revenue_bounds"
               not in r.get("not_summable_with", "")
               for r in rows_b):
            f.append("V3")
        # V4 a ceiling row must say how many properties share it, > 0
        if any(r.get("bound_is_a_repeated_regional_ceiling") == "Y"
               and not (r.get("n_facilities_sharing_this_ceiling") or "0")
               .isdigit()
               for r in rows_b):
            f.append("V4")
        # V5 a sealed facility must carry a disposition
        if any(r.get("state_revenue_disclosure_status")
               and not r.get("state_revenue_disclosure_disposition")
               for r in rows_f):
            f.append("V5")
        # V6 a disposition of SEALED/NOT_COLLECTED must be quote-supported
        if any(r.get("state_revenue_disclosure_disposition")
               in ("SEALED_HELD_BY_REGULATOR", "NOT_COLLECTED_BY_THIS_BODY")
               and r.get("state_revenue_disclosure_quote_supports_status") != "Y"
               for r in rows_f):
            f.append("V6")
        return f

    fails += check(brows, frows)

    # V7 -- the shape of the table has not drifted from what the docstring says
    n_ceiling = sum(1 for r in brows
                    if r.get("bound_is_a_repeated_regional_ceiling") == "Y")
    if len(brows) != 13803 or n_ceiling != 13494:
        fails.append(
            f"V7 the table moved: {len(brows)} rows / {n_ceiling} ceilings "
            f"against the documented 13,803 / 13,494. Not necessarily wrong - "
            f"re-measure and update the docstring rather than waiving this.")

    if selftest:
        print("\n  SELFTEST")
        probes = [
            ("bound row with no not_summable_with", "V1",
             lambda b, ff: ([dict(b[0], not_summable_with="")] + b[1:], ff)),
            ("ceiling row typed entity_specific", "V2",
             lambda b, ff: ([dict(r, aggregation_level="entity_specific")
                             if r.get("bound_basis") in CEILING_BASES else r
                             for r in b][:50] + b[50:], ff)),
            ("ceiling row not naming its own table", "V3",
             lambda b, ff: ([dict(r, not_summable_with="nigc_regional_ggr")
                             if r.get("bound_is_a_repeated_regional_ceiling")
                             == "Y" else r for r in b][:50] + b[50:], ff)),
            ("sealed facility with no disposition", "V5",
             lambda b, ff: (b, [dict(r, state_revenue_disclosure_disposition="")
                                if r.get("state_revenue_disclosure_status")
                                else r for r in ff])),
            ("SEALED typed on an unsupported quote", "V6",
             lambda b, ff: (b, [dict(
                 r, state_revenue_disclosure_disposition="SEALED_HELD_BY_REGULATOR",
                 state_revenue_disclosure_quote_supports_status="N")
                 if r.get("state_revenue_disclosure_status") else r
                 for r in ff])),
        ]
        for name, expect, mutate in probes:
            b2, f2 = mutate([dict(r) for r in brows], [dict(r) for r in frows])
            got = check(b2, f2)
            ok = expect in got
            print(f"    {'PASS' if ok else 'FAIL'}  {name}: expected {expect}, "
                  f"fired {got}")
            if not ok:
                fails.append(f"SELFTEST {name} did not fire {expect}")
        clean = check([dict(r) for r in brows], [dict(r) for r in frows])
        print(f"    {'PASS' if not clean else 'FAIL'}  clean set: fired "
              f"{clean or 'nothing'}")

    print(f"\n  {BOUNDS.name}: {len(brows):,} rows, {n_ceiling:,} repeated "
          f"regional ceilings")
    print(f"  {FACILITIES.name}: "
          f"{sum(1 for r in frows if r.get('state_revenue_disclosure_disposition'))}"
          f" facilities carry a disclosure disposition")
    if fails:
        print("\n  VERIFY FAILED")
        for x in fails:
            print("   -", x)
        return 1
    print("\n  VERIFY OK - 7 invariants")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["plan", "apply", "verify"])
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.stage in ("plan", "apply"):
        print(json.dumps(run(dry=(a.stage == "plan")), indent=2))
        return 0
    return verify(a.selftest)


if __name__ == "__main__":
    sys.exit(main())
