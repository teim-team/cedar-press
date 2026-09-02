#!/usr/bin/env python3
"""
1139 - LINKAGE COVERAGE, MEASURED ONCE, ACROSS THE WHOLE PRODUCT SURFACE.

    py -3 code/1139_linkage_coverage.py report     # measure and print. No writes.
    py -3 code/1139_linkage_coverage.py apply      # write the doc + the machine-readable measurement
    py -3 code/1139_linkage_coverage.py baseline   # record today's figures as the ratchet FLOOR
    py -3 code/1139_linkage_coverage.py verify     # exit 1 if a dataset fell below its floor
    py -3 code/1139_linkage_coverage.py selftest   # prove verify FIRES

Read-only against every table except its own two outputs.  Zero network.
Mints no id.  Writes no key onto any dataset - measuring is not linking, and
this file must never become a writer, because then it would be scanning its
own output (AGENT_FIELD_GUIDE rule 10, and 830 has done that twice).

===========================================================================
WHY THIS EXISTS
===========================================================================
Cedar's product claim is that a row can be attributed to a Native entity.
Coverage of that claim had never been measured across all thirteen customer
datasets at one time, on one definition, with the denominator written down.

The house defect (AGENT_FIELD_GUIDE section 3, twenty-four instances) is a
number that is plausible and is about something else.  For linkage coverage
the specific shape is that **a table has more than one column that looks like
the answer, and they disagree**:

    prime_contracts      tribe_id non-blank        789,456
                         attributed_flag = '1'     789,360   <- 96 rows apart
    federal_funding      tribe_id_neid non-blank   552,602
                         attribution_status=neid   553,106   <- 504 rows apart

Neither pair is a rounding difference; each is a named population.  The 96 are
`Nakupuna Solutions, Llc`, carrying a key and a `ruling_status` of
`RULED_TIER_C_NOT_ATTRIBUTED` - a NEGATIVE ruling, $269,771,379, and not
coverage.  The 504 are `Bristol Bay Native Corporation`, whose keys the FA-01
unlink cleared while the status columns went on saying `cedar_neid`.

So this script refuses to publish one number per dataset.  It publishes:

  * LINKED   - the CONJUNCTION.  A key is present AND nothing on the row
               withdraws it.  This is the only figure safe to quote, because
               it is the smaller of every available reading.
  * a named alternative count for every sibling column that disagrees, with
    the disagreement stated in rows, so a reader can see which definition
    produced a figure they met somewhere else.
  * DENOM    - the denominator, in words, naming what one row IS.

===========================================================================
THREE THINGS THAT MAKE A SCAN REPORT 0% ON A LINKED DATASET
===========================================================================
Each of these was measured on this product surface, and each one produced a
wrong figure before it was fixed here.

**The counts below are WORKED EXAMPLES from 2026-09-02 and they will rot** -
these flagships are rebuilt by other workstreams and two of them moved while
this file was being written.  Run `report` for live figures.  The SHAPES are
what the code depends on, and the shapes are stable.

**1. A LIST-VALUED KEY COLUMN.**  `nagpra_notices` has no `cedar_uid`.  It
carries six pipe-delimited role columns - `consulted_entity_ids`,
`affiliated_entity_ids`, `repatriation_recipient_entity_ids` and three more -
because one notice names many parties in many roles.  A scan looking for
`cedar_uid` / `tribe_id` / `entity_id` reports 0% on a dataset that is 90.83%
linked.  `list_keys` below declares them, and LINKED is the union: a notice is
linked when ANY role resolved.  Verified against the table's own
`has_resolved_entity` flag - 6,169 both ways, **0 rows disagreeing in either
direction** - so the structural predicate and the derived flag are the same
population, and the structural one is used because it survives the flag being
dropped.

**2. THE WRONG ROLE.**  `native_owned_businesses.business_entity_id` is
populated on 4 of 2,916 rows and reading it as the numerator gives 0.14%.
That is a true statement about the wrong column.  These firms are owned by
PEOPLE: `identity_scope` is `any_native` (1,567), `citizen` (385),
`enrolled_member_cskt` (91), `shareholder_descendant_or_spouse` (98), and 280
rows' `business_name_is_person_name` is 1.  A sole proprietor is not a spine
entity and manufacturing one would be fabrication - `resolution_method` shows
the pipeline already REFUSING loose-token matches on `Cherokee Nation`,
`Navajo` and `Eagle`.  The Native entity this row is ABOUT is the certifying
nation whose TERO or member directory it comes from, and that is populated on
2,767 of 2,916 (94.87%).  So every dataset here declares a `role` - which
entity the link names - and the numerator reads the column for that role.

**3. TWO DENOMINATORS, BOTH CORRECT.**  `native_owned_businesses.csv` holds
2,916 rows; `dist/customer/native-owned-businesses.csv` holds 2,044, because
872 are `publishable = N`.  Neither is wrong and a figure quoted without
saying which is.  Where a flagship carries a `publishable` column this script
prints `rows_publishable` beside `rows` and measures LINKED on both.

===========================================================================
THE RULE FOR ADDING A DATASET
===========================================================================
`linked_sql` must be the CONJUNCTION of every column a consumer branches on.
If you add a dataset whose flagship carries a key column and a gate column,
put BOTH in `linked_sql` and put each one alone in `alts`.  A numerator that
reads only the key column counts rows a ruling has already withdrawn.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine"
DOC = ROOT / "docs" / "LINKAGE_COVERAGE.md"
OUT = CLEAN / "_linkage_coverage.json"
FLOOR = CLEAN / "_linkage_coverage_baseline.json"
TODAY = date.today().isoformat()

# A coverage RATIO may fall by this many BASIS POINTS (0.01 pp) without
# failing.  Not zero: several flagships are rebuilt by other workstreams and a
# rebuild that adds honest unlinked rows lowers the ratio without losing a
# single link.  It is small enough that losing links cannot hide inside it -
# 25 bp of prime_contracts is 3,044 rows.
#
# The absolute counter `linkage_<dataset>_rows` gets no percentage tolerance
# at all.  It gets a PRECISE allowance instead, from the denominator that
# travels beside it: a link may fall by as many rows as the table itself lost,
# and not one more.  A link cannot survive a row that does not exist; a link
# lost from a row that STILL EXISTS is the defect.  That rule was earned
# ninety seconds after the first baseline was recorded, when
# native_owned_businesses went 4,274 -> 4,273 rows and 4,125 -> 4,124 links in
# another workstream's rebuild and this gate could not say it was benign.
TOLERANCE_BP = 25

# SQL keywords and literal values that appear inside a predicate and are not
# column names.  The `usable()` guard below refuses to run a predicate naming
# a column the table does not have, because a predicate that raises is better
# than one that silently measures nothing.
_NOT_COLUMNS = {
    "AND", "OR", "NOT", "COALESCE", "TRIM", "CAST", "AS", "VARCHAR", "NULL",
    "IS", "TRUE", "FALSE", "IN", "LIKE", "BETWEEN", "CASE", "WHEN", "THEN",
    "ELSE", "END", "UPPER", "LOWER", "NULLIF",
}


def nb(c: str) -> str:
    return f"coalesce(trim(CAST({c} AS VARCHAR)),'') <> ''"


def any_of(cols) -> str:
    """LINKED for a LIST-VALUED key: the row resolves if ANY role column is
    populated.  This is what stops a scan reporting 0% on `nagpra_notices`,
    which has no single-id column at all."""
    return "(" + " OR ".join(nb(c) for c in cols) + ")"


# --------------------------------------------------------------------------
# THE THIRTEEN.  `collection` is the customer-facing dataset id in
# dist/customer/; `table` is the flagship that 770.FLAGSHIP names, read out of
# data/clean directly so this pass cannot collide with whoever is inside
# 1137_customer_dataset_combine.py.
# --------------------------------------------------------------------------
DATASETS = [
    dict(
        collection="contractors", table="prime_contracts.csv",
        denom="one prime contract award row (FPDS / USAspending), FY2000-2026",
        linked_sql=f"{nb('tribe_id')} AND attributed_flag = '1'",
        alts=[("key_only:tribe_id", nb("tribe_id")),
              ("gate_only:attributed_flag", "attributed_flag = '1'"),
              ("display_only:cedar_uid", nb("cedar_uid"))],
        not_attributable_sql=(
            "ruling_status IN ('RULED_NOT_NATIVE','RULED_CLASS_ONLY')"),
        not_attributable_why=(
            "an owner ruling says the awardee is not a Native entity, or "
            "that the award is a CLASS-level fact naming no individual "
            "entity. `RULED_OWNER_NOT_IN_SPINE` is deliberately NOT counted "
            "here - that one IS a Cedar gap"),
        money="total_obligations", name_col="awardee_name",
    ),
    dict(
        collection="subcontracting", table="subawards.csv",
        denom="one subaward row. LINKED if EITHER side (prime or subawardee) "
              "resolves, because either one makes the row attributable",
        role="EITHER party. **`cedar_uid` on this table is the PRIME leg** - "
             "it equals `prime_cedar_uid` on 39,567 of its 40,201 non-blank "
             "values - and it is **BLANK BY DESIGN** on the majority "
             "population, where the Native party is the SUBAWARDEE. Reading "
             "`cedar_uid` alone gives 44.77% and that is a fill rate, not "
             "coverage. **Do not write a subawardee id into `cedar_uid` to "
             "close it**: the column would then mean the prime on some rows "
             "and the subawardee on others, and every customer "
             "`GROUP BY cedar_uid` would silently mix the two - the same "
             "class of defect as the identifier ledger holding a UEI in "
             "`state`. Exposing the subawardee leg is a SCHEMA decision, in "
             "its own named column",
        linked_sql=f"({nb('prime_cedar_uid')} OR {nb('sub_cedar_uid')})",
        alts=[("subawardee_side:sub_cedar_uid", nb("sub_cedar_uid")),
              ("prime_side:prime_cedar_uid", nb("prime_cedar_uid")),
              ("row_level:cedar_uid_ONLY_a_fill_rate", nb("cedar_uid")),
              ("either_side_via_tribe_id_columns",
               f"({nb('prime_native_tribe_id')} OR "
               f"{nb('sub_native_tribe_id')})")],
        money="subaward_amount", name_col="subawardee_name",
    ),
    dict(
        collection="funding", table="federal_funding_transactions.csv",
        denom="one federal assistance transaction, FY2007-2026",
        linked_sql=(f"{nb('tribe_id_neid')} AND "
                    f"attribution_status = 'cedar_neid' AND "
                    f"attributed_flag = '1'"),
        alts=[("key_only:tribe_id_neid", nb("tribe_id_neid")),
              ("gate_only:attribution_status", "attribution_status = 'cedar_neid'"),
              ("gate_only:attributed_flag", "attributed_flag = '1'")],
        not_attributable_sql="attribution_status = 'excluded_not_native'",
        not_attributable_why="the recipient is ruled not a Native entity",
        money="obligated_usd", name_col="recipient_name",
    ),
    dict(
        collection="gaming", table="gaming_facilities.csv",
        denom="one gaming FACILITY row - not one property. The 787 rows "
              "resolve to 714 distinct properties; the gated denominator "
              "ladder is code/846_session_audit.py::_denom",
        linked_sql=nb("cedar_uid"),
        alts=[("key_only:tribe_id", nb("tribe_id"))],
        money=None, name_col="facility_name",
    ),
    dict(
        collection="natural-resources", table="resource_revenue.csv",
        denom="one resource revenue event row",
        linked_sql=nb("cedar_uid"),
        alts=[("key_only:recipient_entity_id", nb("recipient_entity_id")),
              ("status:keyed_to_cedar_entity",
               "entity_attribution_status = 'keyed_to_cedar_entity'")],
        not_attributable_sql=(
            "entity_attribution_status IN "
            "('aggregate_suppressed_by_publisher',"
            " 'class_recipient_never_an_individual')"),
        not_attributable_why=(
            "ONRR and the state publishers report Indian Country revenue in "
            "AGGREGATE and never name a recipient, and a further class of "
            "row has a recipient that is a category rather than an entity. "
            "These are SOURCE_DOES_NOT_PUBLISH - a fact about the world, "
            "never a Cedar deficiency (AGENT_FIELD_GUIDE section 5) - and "
            "keying them would be fabrication"),
        money="amount_usd", name_col="recipient_name_raw",
    ),
    dict(
        collection="native-owned-businesses", table="native_owned_businesses.csv",
        denom="one directory listing of a Native-owned business",
        role="the CERTIFYING NATION whose TERO, member directory or licence "
             "register the listing comes from. NOT the firm: these firms are "
             "owned by PEOPLE (identity_scope any_native 1,567 / citizen 385 "
             "/ shareholder_descendant_or_spouse 98; 280 rows' names ARE "
             "natural persons), a sole proprietor is not a spine entity, and "
             "`business_entity_id` is populated on 4 rows precisely because "
             "the resolver refuses to manufacture one",
        linked_sql=nb("certifying_authority_entity_id"),
        alts=[("the_firm_itself:business_entity_id", nb("business_entity_id")),
              ("federal_crosswalk:federal_link_status=LINKED",
               "federal_link_status = 'LINKED'")],
        money=None, name_col="business_name_raw",
    ),
    dict(
        collection="nonprofits", table="np_orgs.csv",
        denom="one nonprofit organisation (EIN filer)",
        linked_sql=f"{nb('tribe_id')} AND {nb('cedar_uid')}",
        alts=[("key_only:tribe_id", nb("tribe_id")),
              ("spine_side:cedar_spine_entity_id", nb("cedar_spine_entity_id"))],
        not_attributable_sql="disposition LIKE 'EXCLUDED%'",
        not_attributable_why=(
            "`EXCLUDED_PRIOR_RULING` (4,681) and "
            "`EXCLUDED_PLACE_NAME_COINCIDENCE` (279) are rows a ruling has "
            "already decided are NOT the entity a name matcher proposed. "
            "They are correctly unkeyed and they are not a gap"),
        money=None, name_col="org_name",
    ),
    dict(
        collection="deals", table="deals_classified.csv",
        denom="one classified deal / transaction row",
        linked_sql=f"{nb('native_party_entity_id')} AND {nb('cedar_uid')}",
        alts=[("key_only:native_party_entity_id", nb("native_party_entity_id"))],
        money="Announced_Value_USD", name_col="Native_Party",
    ),
    dict(
        collection="lobbying", table="native_entity_lobbying_disclosures.csv",
        denom="one LDA disclosure filing row",
        linked_sql=f"{nb('entity_id')} AND {nb('cedar_uid')}",
        alts=[("key_only:entity_id", nb("entity_id"))],
        money="spend_usd", name_col="client_name",
    ),
    dict(
        collection="legislation", table="native_bills.csv",
        denom="one bill",
        linked_sql="has_resolved_entity = '1'",
        alts=[("legacy_column:affected_entities", nb("affected_entities"))],
        money=None, name_col="title",
    ),
    dict(
        collection="federal-register", table="consultation_events.csv",
        denom="one Federal Register consultation event",
        linked_sql=f"{nb('tribe_id')} AND {nb('cedar_uid')}",
        alts=[("key_only:tribe_id", nb("tribe_id"))],
        money=None, name_col="title",
    ),
    dict(
        collection="nagpra", table="nagpra_notices.csv",
        denom="one NAGPRA Federal Register notice",
        role="ANY of six party roles. This table has NO single-id column - "
             "the keys are six PIPE-DELIMITED list columns, because one "
             "notice names many parties. LINKED is their union",
        list_keys=["consulted_entity_ids", "affiliated_entity_ids",
                   "disposition_priority_entity_ids",
                   "repatriation_recipient_entity_ids",
                   "letter_of_support_entity_ids",
                   "aboriginal_land_entity_ids"],
        alts=[("derived_flag:has_resolved_entity", "has_resolved_entity = '1'"),
              ("affiliated_role_only", nb("affiliated_entity_ids")),
              ("consulted_role_only", nb("consulted_entity_ids")),
              ("repatriation_recipient_role_only",
               nb("repatriation_recipient_entity_ids"))],
        money=None, name_col="institution_name",
    ),
    dict(
        collection="nest", table="nest_enterprises.csv",
        denom="one tribally / ANC / NHO-owned enterprise. The owner hub is "
              "this table's KEY, so coverage is 100% by construction; the "
              "informative figure is the alternative below - how many "
              "enterprises also carry their OWN spine entity",
        linked_sql=nb("owner_hub_cedar_uid"),
        alts=[("enterprise_own_entity:enterprise_existing_cedar_uid",
               nb("enterprise_existing_cedar_uid"))],
        money=None, name_col="enterprise_name",
    ),
]


def find(name):
    for d in (CLEAN, SPINE):
        p = d / name
        if p.exists():
            return p
    return None


def rd(p):
    return (f"read_csv('{p.as_posix()}', ignore_errors=true, sample_size=-1, "
            f"all_varchar=true)")


def cols_of(con, p):
    return {r[0] for r in con.sql(f"DESCRIBE SELECT * FROM {rd(p)}").fetchall()}


def usable(sql, have):
    """Every bare identifier outside a quoted literal must be a real column.

    A predicate naming a column that is not there does not measure low
    coverage - it raises.  Rule 2: verify your input contains what you think
    it does.
    """
    stripped = re.sub(r"'[^']*'", "''", sql)
    for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", stripped):
        if tok.upper() in _NOT_COLUMNS or tok in have:
            continue
        return False
    return True


def measure_one(con, spec):
    p = find(spec["table"])
    if p is None:
        return dict(collection=spec["collection"], table=spec["table"],
                    status="TABLE_ABSENT", linked=None, rows=None,
                    unmeasured_reason="flagship table not on disk")
    have = cols_of(con, p)
    rows = con.sql(f"SELECT count(*) FROM {rd(p)}").fetchone()[0]
    out = dict(collection=spec["collection"], table=spec["table"],
               denom=spec["denom"], role=spec.get("role"), rows=rows,
               status="MEASURED")

    # A list-valued key is declared, never inferred: LINKED is the union of
    # the role columns.  Without this a scan reports 0% on nagpra_notices.
    if spec.get("list_keys"):
        present = [c for c in spec["list_keys"] if c in have]
        out["list_keys_declared"] = spec["list_keys"]
        out["list_keys_present"] = present
        if not present:
            out.update(status="UNMEASURED_COLUMN_ABSENT", linked=None,
                       unmeasured_reason="none of the declared list-valued "
                                         "key columns is on this table: "
                                         + ", ".join(spec["list_keys"]))
            return out
        spec = dict(spec, linked_sql=any_of(present))
        out["list_keys_missing"] = [c for c in spec["list_keys"]
                                    if c not in have]

    if not usable(spec["linked_sql"], have):
        out.update(status="UNMEASURED_COLUMN_ABSENT", linked=None,
                   unmeasured_reason=(
                       "the LINKED predicate names a column this table does "
                       "not have: " + spec["linked_sql"]))
        return out

    linked = con.sql(
        f"SELECT count(*) FROM {rd(p)} WHERE {spec['linked_sql']}").fetchone()[0]
    out["linked"] = linked
    out["linked_sql"] = spec["linked_sql"]
    out["pct"] = round(100.0 * linked / rows, 4) if rows else 0.0
    out["unlinked"] = rows - linked

    alts = {}
    for label, sql in spec["alts"]:
        alts[label] = (con.sql(f"SELECT count(*) FROM {rd(p)} WHERE {sql}"
                               ).fetchone()[0] if usable(sql, have) else None)
    out["alts"] = alts
    out["alt_disagreement_rows"] = {
        k: v - linked for k, v in alts.items() if v is not None and v != linked}

    # A THIRD DENOMINATOR, and the one that says whether a low figure is a
    # DEFECT or a fact about the world.  `natural-resources` reads 6.24% and
    # 9,791 of its 10,600 unlinked rows are `aggregate_suppressed_by_
    # publisher` - ONRR reports Indian Country revenue in aggregate and never
    # names a recipient.  Against the rows a recipient CAN be named on, the
    # same table is 73.66%.  The exclusion must be a DECLARED, PER-ROW,
    # source-side or ruled fact, never a judgement made here, and the ratchet
    # still runs on the RAW figure so this can never be used to make a real
    # fall look like a definition change.
    na = spec.get("not_attributable_sql")
    if na and usable(na, have):
        nn, nl = con.sql(
            f"SELECT count(*), count(*) FILTER (WHERE {spec['linked_sql']}) "
            f"FROM {rd(p)} WHERE {na}").fetchone()
        out["not_attributable"] = nn
        out["not_attributable_sql"] = na
        out["not_attributable_why"] = spec.get("not_attributable_why", "")
        den = rows - nn
        out["attributable_denominator"] = den
        out["pct_of_attributable"] = (
            round(100.0 * (linked - nl) / den, 4) if den else 0.0)

    # TWO DENOMINATORS, BOTH CORRECT.  data/clean holds every row; the
    # customer file holds only `publishable = Y`.  A figure quoted without
    # saying which one it used is the defect this whole file exists to stop.
    if "publishable" in have:
        pr, pl = con.sql(
            f"SELECT count(*), count(*) FILTER (WHERE {spec['linked_sql']}) "
            f"FROM {rd(p)} WHERE publishable = 'Y'").fetchone()
        out["rows_publishable"] = pr
        out["linked_publishable"] = pl
        out["pct_publishable"] = round(100.0 * pl / pr, 4) if pr else 0.0

    money = spec.get("money")
    if money and money in have:
        tot, unl = con.sql(
            f"SELECT round(sum(TRY_CAST({money} AS DOUBLE)),2), "
            f"round(sum(TRY_CAST({money} AS DOUBLE)) "
            f"FILTER (WHERE NOT ({spec['linked_sql']})),2) FROM {rd(p)}"
        ).fetchone()
        out["money_col"], out["money_total"], out["money_unlinked"] = \
            money, tot, unl

    nc = spec.get("name_col")
    if nc and nc in have:
        sel = f"{nc} AS nm, count(*) AS n"
        if money and money in have:
            sel += f", round(sum(TRY_CAST({money} AS DOUBLE)),2) AS usd"
        out["residue_top"] = [list(r) for r in con.sql(
            f"SELECT {sel} FROM {rd(p)} WHERE NOT ({spec['linked_sql']}) "
            f"GROUP BY 1 ORDER BY 2 DESC LIMIT 5").fetchall()]
    return out


def coverage():
    """The measurement, as a plain dict.  Imported by 62's ratchet."""
    con = duckdb.connect()
    con.sql("SET preserve_insertion_order=false")
    try:
        return {"measured": TODAY,
                "datasets": [measure_one(con, s) for s in DATASETS]}
    finally:
        con.close()


_METRICS_CACHE = {}


def metrics(cov=None):
    """62's shape: MUST_NOT_FALL scalars, in basis points and in rows.

    Basis points rather than a float, because a ratchet compares numbers and
    a float round-tripping through JSON is a source of spurious failures.

    MEMOISED FOR THE LIFE OF THE PROCESS. `coverage()` scans thirteen
    flagships including a 1.57 GB `prime_contracts.csv`, and `selftest` calls
    `verify` five times to prove five cases - unmemoised that is five full
    scans to answer a question about a JSON file. The cache is per-process
    and the tables cannot change under a single run; anything that wants a
    fresh measurement calls `coverage()`.
    """
    if cov is None and "m" in _METRICS_CACHE:
        return dict(_METRICS_CACHE["m"])
    cov = cov or coverage()
    m = {}
    for d in cov["datasets"]:
        k = d["collection"].replace("-", "_")
        if d.get("linked") is None or not d.get("rows"):
            m[f"linkage_{k}_bp"] = "UNMEASURED"
            m[f"linkage_{k}_rows"] = "UNMEASURED"
            continue
        m[f"linkage_{k}_bp"] = int(round(10000.0 * d["linked"] / d["rows"]))
        m[f"linkage_{k}_rows"] = d["linked"]
        # The DENOMINATOR travels with the numerator, and it is not decoration.
        # A rebuild that removes rows legitimately removes their links, and a
        # zero-tolerance counter on a flagship nine agents are rebuilding fires
        # on that within the minute - measured: `native_owned_businesses` went
        # 4,274 -> 4,273 rows and 4,125 -> 4,124 links while this file was
        # being written. Without the denominator there is no way to tell that
        # from a link being lost off a row that still exists, which is the
        # defect the ratchet is for.
        m[f"linkage_{k}_denom"] = d["rows"]
    live = [d for d in cov["datasets"] if d.get("linked") is not None]
    m["linkage_datasets_measured"] = len(live)
    m["linkage_linked_rows_total"] = sum(d["linked"] for d in live)
    m["linkage_linked_rows_total_denom"] = sum(d["rows"] for d in live)
    _METRICS_CACHE["m"] = dict(m)
    return m


# --------------------------------------------------------------------------


def fmt(n):
    return "UNMEASURED" if n is None else f"{n:,}"


def render(cov):
    L = []
    A = L.append
    A("# Linkage coverage - what fraction of each shipped dataset can be "
      "attributed to a Native entity")
    A("")
    A(f"*GENERATED by `code/1139_linkage_coverage.py apply`. Measured "
      f"{cov['measured']} against `data/clean` directly rather than against "
      f"`dist/customer`, so it cannot collide with a build in progress. "
      f"**Do not hand-edit - re-run the script.***")
    A("")
    A("**Every percentage here states its denominator in the row beneath it.** "
      "This project has shipped percentages whose denominator nobody stated, "
      "and one gaming count circulated in five values in a single day "
      "(`docs/AGENT_FIELD_GUIDE.md` rule 15). The `LINKED` column is always "
      "the CONJUNCTION - a key column is populated **and** no gate column on "
      "the same row withdraws it - so it is the smallest defensible reading. "
      "Where a sibling column gives a different answer the difference is "
      "printed, in rows, in that dataset's own section.")
    A("")
    A("| dataset | flagship | rows (denominator) | LINKED | % | unlinked | "
      "% of rows that CAN name an entity |")
    A("|---|---|---:|---:|---:|---:|---:|")
    for d in cov["datasets"]:
        if d.get("linked") is None:
            A(f"| `{d['collection']}` | `{d['table']}` | "
              f"{fmt(d.get('rows'))} | UNMEASURED | - | - | - |")
            continue
        att = (f"{d['pct_of_attributable']:.2f}% of "
               f"{d['attributable_denominator']:,}"
               if d.get("attributable_denominator") is not None else "—")
        A(f"| `{d['collection']}` | `{d['table']}` | {d['rows']:,} | "
          f"{d['linked']:,} | {d['pct']:.2f}% | {d['unlinked']:,} | {att} |")
    live = [d for d in cov["datasets"] if d.get("linked") is not None]
    tr = sum(d["rows"] for d in live)
    tl = sum(d["linked"] for d in live)
    A("")
    A(f"**Across the {len(live)} measured flagships: {tl:,} of {tr:,} rows "
      f"({100.0 * tl / tr:.2f}%) carry a resolved Cedar entity.** That total "
      f"sums tables whose rows are not the same kind of thing - a contract "
      f"award and a NAGPRA notice each count as one - so it is a SCALE "
      f"figure and never a quality figure. Quote the per-dataset rows.")
    A("")
    A("---")
    A("")
    for d in cov["datasets"]:
        A(f"## `{d['collection']}` - `{d['table']}`")
        A("")
        if d.get("linked") is None:
            A(f"**UNMEASURED.** "
              f"{d.get('unmeasured_reason') or d.get('status')}")
            A("")
            continue
        A(f"**Denominator: {d['rows']:,} rows.** One row is {d['denom']}.")
        A("")
        if d.get("rows_publishable") is not None and \
                d["rows_publishable"] != d["rows"]:
            A(f"**Second denominator, also correct:** the customer file "
              f"carries only `publishable = Y`, which is "
              f"{d['rows_publishable']:,} rows, of which "
              f"{d['linked_publishable']:,} are LINKED "
              f"({d['pct_publishable']:.2f}%). Say which denominator you "
              f"used; the two differ by "
              f"{d['rows'] - d['rows_publishable']:,} rows.")
            A("")
        if d.get("attributable_denominator") is not None:
            A(f"**Third denominator - the one that says whether a low figure "
              f"is a DEFECT.** {d['not_attributable']:,} rows can never name "
              f"an individual Cedar entity, because "
              f"{d['not_attributable_why']} (`{d['not_attributable_sql']}`). "
              f"Against the {d['attributable_denominator']:,} rows that CAN, "
              f"this dataset is **{d['pct_of_attributable']:.2f}%** linked. "
              f"The ratchet still runs on the raw {d['pct']:.2f}%, so this "
              f"reading can never be used to make a real fall look like a "
              f"change of definition.")
            A("")
        if d.get("role"):
            A(f"**Which entity the link names:** {d['role']}.")
            A("")
        if d.get("list_keys_present"):
            A(f"**This table's key is LIST-VALUED.** No single-id column "
              f"exists; LINKED is the union of "
              + ", ".join(f"`{c}`" for c in d["list_keys_present"])
              + ". A scan looking only for `cedar_uid` / `tribe_id` / "
                "`entity_id` reports 0% here and is wrong.")
            A("")
        A(f"**LINKED: {d['linked']:,} ({d['pct']:.2f}%)** - "
          f"`{d['linked_sql']}`")
        A("")
        if d.get("alts"):
            A("| alternative reading | rows | apart from LINKED |")
            A("|---|---:|---:|")
            for k, v in d["alts"].items():
                A(f"| `{k}` | column absent | - |" if v is None
                  else f"| `{k}` | {v:,} | {v - d['linked']:+,} |")
            A("")
        if d.get("money_total") is not None:
            mt = d["money_total"] or 0.0
            mu = d["money_unlinked"] or 0.0
            share = (100.0 * mu / mt) if mt else 0.0
            A(f"**Money on unlinked rows: ${mu:,.2f} of an UNFILTERED "
              f"${mt:,.2f}** in `{d['money_col']}`, {share:.2f}%. "
              f"**Neither figure is a Cedar total and neither may be quoted "
              f"as one.** They sum the column exactly as recorded, with no "
              f"countability rule applied; `docs/MONEY_TOTALLING_RULES.md` "
              f"governs every total this project publishes, and on "
              f"`subawards` in particular the countable total is billions "
              f"below the unfiltered one. What is measured here is EXPOSURE "
              f"- the share of the money that sits on rows nothing can be "
              f"attributed to - and a ratio of two unfiltered sums answers "
              f"that question honestly while answering no other.")
            A("")
        if d.get("residue_top"):
            A("**The largest unlinked residue, by row count:**")
            A("")
            has_usd = len(d["residue_top"][0]) == 3
            A("| name as recorded | rows |" + (" amount |" if has_usd else ""))
            A("|---|---:|" + ("---:|" if has_usd else ""))
            for r in d["residue_top"]:
                nm = str(r[0])[:70] if r[0] is not None else "(blank)"
                line = f"| {nm} | {r[1]:,} |"
                if has_usd:
                    line += f" ${(r[2] or 0):,.2f} |"
                A(line)
            A("")
    A("---")
    A("")
    A("## The ratchet")
    A("")
    A(f"`py -3 code/1139_linkage_coverage.py baseline` records the figures "
      f"above as a floor in `data/clean/_linkage_coverage_baseline.json`, and "
      f"`verify` exits 1 when any dataset falls more than {TOLERANCE_BP} "
      f"basis points ({TOLERANCE_BP / 100:.2f} pp) below it. "
      f"`code/62_no_regression_check.py` carries the same figures as "
      f"`linkage_<dataset>_bp` (MUST_NOT_FALL) by importing `metrics()` from "
      f"this file, so there is ONE measurement and not two - "
      f"`248` is a retired stub for exactly the reason that two detectors "
      f"for one class drift.")
    A("")
    A(f"**The ratio's tolerance is not zero on purpose.** Several flagships "
      f"are rebuilt by other workstreams, and a rebuild that adds honest "
      f"unlinked rows lowers the ratio without losing a single link. Losing "
      f"links cannot hide inside it: {TOLERANCE_BP} bp of `prime_contracts` "
      f"is more than 3,000 rows.")
    A("")
    A("**`linkage_<dataset>_rows` — the absolute count of linked rows — is "
      "carried beside it, and the rule on it is exact:**")
    A("")
    A("> A link may fall by as many rows as the table itself lost, and not "
      "one more.")
    A("")
    A("A link cannot survive a row that does not exist, so a rebuild that "
      "removes rows legitimately removes their links; a link lost from a row "
      "that still EXISTS is the defect, and it fails with no tolerance at "
      "all. `linkage_<dataset>_denom` carries the row count so the two can "
      "be told apart. The rule was earned ninety seconds after the first "
      "baseline, when `native_owned_businesses` went 4,274 → 4,273 rows and "
      "4,125 → 4,124 links in another workstream's rebuild and the gate "
      "could not say that was benign. A percentage tolerance was rejected: "
      "0.1% of `prime_contracts` is 791 rows, which is the hiding place zero "
      "tolerance existed to close.")
    A("")
    A("---")
    A("")
    A("<!-- BEGIN LINKAGE-NOTES -->")
    A("## Notes a person wrote, which the generator will not delete")
    A("")
    A("*This file is rewritten WHOLESALE by "
      "`code/1139_linkage_coverage.py apply`, which is the defect class "
      "`code/845_regenerate_guard.py` exists to catch. Anything you write "
      "**between the BEGIN and END markers of this block** is read off disk "
      "and carried forward on every regeneration. Anything outside them is "
      "gone on the next run. If you need a second protected section, give it "
      "a marker name nobody else has — two blocks sharing a name are one "
      "block to the preserver.*")
    A("")
    A("<!-- END LINKAGE-NOTES -->")
    A("")
    return "\n".join(L) + "\n"


MARKER_RE = re.compile(
    r"<!--\s*BEGIN\s+([A-Za-z0-9_\-]+)\s*-->(.*?)<!--\s*END\s+\1\s*-->",
    re.S)


def carry_marked_blocks(new_text: str, doc: Path) -> str:
    """Re-insert every `<!-- BEGIN X -->…<!-- END X -->` block already on disk.

    This file is written WHOLESALE, which is the defect class `845` names:
    a generator that rewrites a doc over a paragraph a human wrote. `574`
    deleted exactly such a paragraph, written to close a reviewer finding,
    within hours of its being written. The convention that came out of that
    is a marker pair, and a marker only helps if the generator honours it -
    so this reads the live file FIRST and carries every marked block forward,
    replacing an empty placeholder of the same name and appending any block
    the generator does not know about.
    """
    if not doc.exists():
        return new_text
    try:
        old = doc.read_text(encoding="utf-8")
    except OSError:
        return new_text
    out = new_text
    for name, body in MARKER_RE.findall(old):
        block = f"<!-- BEGIN {name} -->{body}<!-- END {name} -->"
        here = re.search(
            rf"<!--\s*BEGIN\s+{re.escape(name)}\s*-->.*?"
            rf"<!--\s*END\s+{re.escape(name)}\s*-->", out, re.S)
        if here:
            out = out[:here.start()] + block + out[here.end():]
        else:
            out = out.rstrip() + "\n\n" + block + "\n"
    return out


def do_apply():
    cov = coverage()
    OUT.write_text(json.dumps(cov, indent=2), encoding="utf-8")
    DOC.write_text(carry_marked_blocks(render(cov), DOC), encoding="utf-8")
    print(f"wrote {DOC.relative_to(ROOT)}")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


def do_baseline():
    m = metrics()
    bad = [k for k, v in m.items() if v == "UNMEASURED"]
    if bad:
        print("REFUSING to record a baseline while a dataset is UNMEASURED - "
              "a floor of UNMEASURED is a floor of nothing, and re-recording "
              "a baseline around a red light is the waiver standing rule 15 "
              "forbids: " + ", ".join(bad), file=sys.stderr)
        return 2
    FLOOR.write_text(json.dumps(
        {"recorded": TODAY, "tolerance_bp": TOLERANCE_BP, "metrics": m},
        indent=2), encoding="utf-8")
    print(f"baseline recorded -> {FLOOR.relative_to(ROOT)}")
    for k in sorted(m):
        print(f"  {k:44s} {m[k]}")
    return 0


def below_floor():
    """[(metric, reason)] for everything under its floor.  62 calls this.

    Returns a one-element list naming the missing baseline rather than an
    empty one, because an absent floor is UNMEASURED and must never read as
    clean (AGENT_FIELD_GUIDE rule 4).
    """
    if not FLOOR.exists():
        return [("_no_baseline",
                 "data/clean/_linkage_coverage_baseline.json is absent - "
                 "linkage coverage has no floor recorded, so a fall cannot "
                 "be told from a first run. Record it: "
                 "py -3 code/1139_linkage_coverage.py baseline")]
    base = json.loads(FLOOR.read_text(encoding="utf-8"))
    tol = int(base.get("tolerance_bp", TOLERANCE_BP))
    now = metrics()
    out = []
    for k, floor in sorted(base["metrics"].items()):
        v = now.get(k)
        if v is None:
            out.append((k, "present at the baseline, ABSENT now - a dataset "
                           "that stopped being measured is not one that "
                           "improved"))
            continue
        if v == "UNMEASURED":
            out.append((k, f"UNMEASURED now, {floor} at the baseline"))
            continue
        if not isinstance(floor, int) or k.endswith("_denom"):
            continue
        if k.endswith("_bp"):
            if v < floor - tol:
                out.append((k, f"{v:,} is below its floor of {floor:,} "
                               f"(tolerance {tol} bp)"))
            continue
        # A ROW COUNTER. Zero tolerance for links lost, full allowance for
        # rows that are simply no longer in the table: `shrank` is how many
        # rows the flagship lost since the baseline, and a link cannot
        # survive a row that does not exist.
        dk = k[:-5] + "_denom" if k.endswith("_rows") else None
        dk = "linkage_linked_rows_total_denom" if \
            k == "linkage_linked_rows_total" else dk
        shrank = 0
        if dk and isinstance(base["metrics"].get(dk), int) \
                and isinstance(now.get(dk), int):
            shrank = max(0, base["metrics"][dk] - now[dk])
        if v < floor - shrank:
            out.append((k, f"{v:,} is below its floor of {floor:,}"
                           + (f", and the table only shrank by {shrank:,} "
                              f"row(s) - so {floor - shrank - v:,} link(s) "
                              f"were lost from rows that still exist"
                              if shrank else
                              " and the table did not shrink - links were "
                              "lost from rows that still exist")))
    return out


def do_verify(quiet=False):
    if not FLOOR.exists():
        print("NO BASELINE ON FILE. Record one: "
              "py -3 code/1139_linkage_coverage.py baseline", file=sys.stderr)
        return 1
    base = json.loads(FLOOR.read_text(encoding="utf-8"))
    tol = int(base.get("tolerance_bp", TOLERANCE_BP))
    now = metrics()
    fails = [f"{k} - {why}" for k, why in below_floor()]
    for k, floor in sorted(base["metrics"].items()):
        v = now.get(k)
        if v is None:
            fails.append(f"{k}: present at the baseline, ABSENT now. A "
                         f"dataset that stopped being measured is not a "
                         f"dataset that improved.")
        elif v == "UNMEASURED":
            fails.append(f"{k}: UNMEASURED now, {floor} at the baseline. "
                         f"An absence of evidence must never print as "
                         f"evidence of absence.")
    fails = sorted(set(fails))
    if not DOC.exists():
        fails.append(f"{DOC.relative_to(ROOT)} is absent - run "
                     f"`py -3 code/1139_linkage_coverage.py apply`.")
    if fails:
        if not quiet:
            print("LINKAGE COVERAGE RATCHET: FAIL", file=sys.stderr)
            for f in fails:
                print("  " + f, file=sys.stderr)
        return 1
    if not quiet:
        n = len([k for k in base["metrics"] if k.endswith("_bp")])
        print(f"LINKAGE COVERAGE RATCHET: PASS - {n} datasets, none below "
              f"floor. Ratios carry {tol} bp; a linked-row count may fall "
              f"only by as many rows as its table lost, and not one more.")
    return 0


def do_selftest():
    """Prove verify FIRES.  A check that has never failed on purpose is not
    known to work (AGENT_FIELD_GUIDE rule 1).

    THE REAL BASELINE IS NEVER WRITTEN TO.  The first version poisoned
    `FLOOR` in place and restored it in a `finally`, which is correct right up
    to the moment the process is killed - and one was, leaving a poisoned
    floor on disk that then failed every subsequent `verify` for a reason
    that had nothing to do with the data.  A `finally` is not a guarantee.
    So the poisoned copies go to a sibling path and the module's FLOOR is
    repointed at it for the duration; a kill leaves a stray temp file and an
    untouched baseline.
    """
    global FLOOR
    if not FLOOR.exists():
        print("selftest needs a baseline on file first.", file=sys.stderr)
        return 2
    real = FLOOR
    orig = real.read_text(encoding="utf-8")
    base = json.loads(orig)
    FLOOR = real.with_name(real.stem + ".selftest_scratch.json")
    key = next((k for k in base["metrics"]
                if k.endswith("_bp") and isinstance(base["metrics"][k], int)),
               None)
    rowkey = next((k for k in base["metrics"]
                   if k.endswith("_rows")
                   and isinstance(base["metrics"][k], int)
                   and base["metrics"][k] > 0), None)
    if key is None or rowkey is None:
        print("selftest: no numeric metric in the baseline.", file=sys.stderr)
        FLOOR = real
        return 2
    ok = True
    try:
        p = json.loads(orig)
        p["metrics"][key] = base["metrics"][key] + 5000       # +50 pp
        FLOOR.write_text(json.dumps(p, indent=2), encoding="utf-8")
        rc = do_verify(quiet=True)
        print(f"  floor {key} raised by 5000 bp   -> verify exit {rc} "
              f"(expect 1)")
        ok &= rc == 1

        p = json.loads(orig)
        p["metrics"][rowkey] = base["metrics"][rowkey] + 1    # 1 row is enough
        FLOOR.write_text(json.dumps(p, indent=2), encoding="utf-8")
        rc = do_verify(quiet=True)
        print(f"  floor {rowkey} raised by 1 row  -> verify exit {rc} "
              f"(expect 1 - a lost link has NO tolerance)")
        ok &= rc == 1

        # THE SHRINK ALLOWANCE, proven in BOTH directions. Raising the row
        # floor by 1 AND the denominator floor by 1 says "the table lost one
        # row and with it one link", which is not a regression and must PASS.
        # Raising the row floor by 2 while the denominator floor moves 1 says
        # a link was lost from a row that still exists, and must FAIL.
        dk = (rowkey[:-5] + "_denom") if rowkey.endswith("_rows") else None
        if dk and isinstance(base["metrics"].get(dk), int):
            p = json.loads(orig)
            p["metrics"][rowkey] = base["metrics"][rowkey] + 1
            p["metrics"][dk] = base["metrics"][dk] + 1
            FLOOR.write_text(json.dumps(p, indent=2), encoding="utf-8")
            rc = do_verify(quiet=True)
            print(f"  ... and its denominator by 1  -> verify exit {rc} "
                  f"(expect 0 - a row that left took its link with it)")
            ok &= rc == 0

            p = json.loads(orig)
            p["metrics"][rowkey] = base["metrics"][rowkey] + 2
            p["metrics"][dk] = base["metrics"][dk] + 1
            FLOOR.write_text(json.dumps(p, indent=2), encoding="utf-8")
            rc = do_verify(quiet=True)
            print(f"  2 links lost, 1 row lost     -> verify exit {rc} "
                  f"(expect 1 - one link left a row that still exists)")
            ok &= rc == 1
        else:
            print("  shrink-allowance case SKIPPED - no denominator on the "
                  "baseline. Re-record it: `baseline`.")
            ok = False

        FLOOR.write_text(orig, encoding="utf-8")
        rc = do_verify(quiet=True)
        print(f"  unpoisoned copy               -> verify exit {rc} "
              f"(expect 0)")
        ok &= rc == 0
    finally:
        scratch, FLOOR = FLOOR, real
        try:
            scratch.unlink()
        except OSError:
            pass
    rc = do_verify(quiet=True)
    print(f"  REAL baseline, never written  -> verify exit {rc} (expect 0)")
    ok &= rc == 0
    print("selftest PASS" if ok else "selftest FAIL")
    return 0 if ok else 1


def do_report():
    cov = coverage()
    print(f"LINKAGE COVERAGE - measured {cov['measured']} from data/clean\n")
    print(f"{'dataset':26s} {'rows':>12s} {'LINKED':>12s} {'pct':>8s} "
          f"{'of attributable':>17s}  disagreeing sibling columns")
    for d in cov["datasets"]:
        if d.get("linked") is None:
            print(f"{d['collection']:26s} {fmt(d.get('rows')):>12s} "
                  f"{'UNMEASURED':>12s}           "
                  f"{d.get('unmeasured_reason', '')}")
            continue
        dis = "; ".join(
            f"{k}{v:+,}" for k, v in (d.get("alt_disagreement_rows") or {}
                                      ).items())
        att = (f"{d['pct_of_attributable']:>6.2f}% of "
               f"{d['attributable_denominator']:>8,}"
               if d.get("attributable_denominator") is not None
               else " " * 17)
        print(f"{d['collection']:26s} {d['rows']:>12,} {d['linked']:>12,} "
              f"{d['pct']:>7.2f}% {att}  {dis}")
    live = [d for d in cov["datasets"] if d.get("linked") is not None]
    tr = sum(d["rows"] for d in live)
    tl = sum(d["linked"] for d in live)
    print(f"\n{'TOTAL (scale, not quality)':26s} {tr:>12,} {tl:>12,} "
          f"{100.0 * tl / tr:>7.2f}%")
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    fn = {"report": do_report, "apply": do_apply, "baseline": do_baseline,
          "verify": do_verify, "selftest": do_selftest}.get(cmd)
    if fn is None:
        print(__doc__)
        return 2
    return fn()


if __name__ == "__main__":
    raise SystemExit(main())
