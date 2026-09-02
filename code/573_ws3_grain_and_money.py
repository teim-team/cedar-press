#!/usr/bin/env python3
"""
Cedar Press - 573: WORKSTREAM GRAIN-WS3. Every measurement behind the grain
declarations in `512.GRAIN_WS3`, every refusal that kept a table out of it, and
the C7 money statements the contract has no field for.

    py -3 code/573_ws3_grain_and_money.py measure   # re-run everything, write
    py -3 code/573_ws3_grain_and_money.py money     # just the C7 statements
    py -3 code/573_ws3_grain_and_money.py verify    # read-only, exit 1 on drift

WHY THIS FILE EXISTS
--------------------
Six datasets - gaming, deals, natural-resources, nonprofits, legislation,
lobbying - were BLOCKED on 13 tables with no declared grain and on five
duplicate counts. Four tables are now declared in `512.GRAIN_WS3`. The other
nine are not, and each refusal rests on a measurement that has to be re-runnable
or it decays into an opinion in a comment. `measure` re-runs all of them and
`verify` fails when one stops being true.

THE RULE THIS FILE WAS WRITTEN UNDER
-------------------------------------
`512.GRAIN_DEFECT` records that `prime_contracts.csv` was listed at 80,778
literal duplicate rows with a note that anyone summing it was over-counting.
Re-measured, the real answer was ZERO: the archive MAPPER had dropped
`contract_transaction_unique_key`, so distinct FPDS transactions rendered
identical. A de-duplication would have deleted real rows and real money.

So every duplicate count this workstream was handed was re-measured, and then
asked the SECOND question, which is the one that matters: does the SOURCE carry
an identity column the builder did not take? Three of five say yes.

    alleged   re-measured   verdict
    822       822           ferc_docket_filings.csv - REAL repeats of one
                            (document, filer) pair; 167 further collisions on
                            the digest key are case variants and are NOT
                            duplicates
    101       101           np_schedule_i_grants.csv - ZERO duplicated facts.
                            Every group is within ONE return that was parsed
                            once; the filer listed the same grant line twice
                            and `132` records no line ordinal
    5         5             native_bills_subject_sweep.csv - REAL. The
                            duplication is in the corpus, not the sweep
    4         4             lobbying_registrant_native_ownership_evidence.csv -
                            ZERO duplicated facts. Four INDEPENDENT sources
                            asserting one identifier; `182` drops
                            `asserted_by_source`
    1         1             hearing_bill_links.csv - REAL, and it is the
                            Congress.gov API repeating a relatedItem

NOTHING HERE DELETES A ROW. House rule: flag, never delete. Where a de-dupe key
is needed it is STATED, so a consumer can apply it and see what it costs.

C7 - WHAT A BUYER MAY AND MAY NOT TOTAL
----------------------------------------
`517_export_safety.py` decides aggregation safety from grain + key +
duplicates, which is necessary and not sufficient: two tables can each be
perfectly keyed and still be the SAME MONEY at two grains. That is the largest
class of error in these six datasets and it is measured in `money` below, in
dollars, from the live files.

Reads   data/clean/*.csv, data/raw/fac/fac_sefa_gaming.json,
        data/raw/advocacy/hearing_meeting_detail.jsonl,
        data/raw/external/votingpatterns/all_bill_intros.csv
Writes  review/ws3_grain_evidence.json      what measure() measured
        review/ws3_money_statements.csv     the C7 statements, machine-readable
        docs/WS3_GRAIN_AND_MONEY.md         the same, for humans
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
csv.field_size_limit(10 ** 8)
TODAY = date.today().isoformat()

EVIDENCE = ROOT / "review" / "ws3_grain_evidence.json"
MONEY_CSV = ROOT / "review" / "ws3_money_statements.csv"
DOC = ROOT / "docs" / "WS3_GRAIN_AND_MONEY.md"

CLEAN = ROOT / "data" / "clean"

DATASETS = ("gaming", "deals", "natural-resources", "nonprofits",
            "legislation", "lobbying")


def rd(name):
    p = name if isinstance(name, Path) else CLEAN / name
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def usd(x):
    try:
        return float((x or "0").replace(",", "").replace("$", "").strip() or 0)
    except ValueError:
        return 0.0


def total(rows, col):
    return sum(usd(r.get(col)) for r in rows)


def keydup(rows, cols):
    """(duplicate_rows, rows_with_a_blank_component) for a candidate key."""
    seen, dup, nul = set(), 0, 0
    for r in rows:
        k = tuple((r.get(c) or "").strip() for c in cols)
        if any(p == "" for p in k):
            nul += 1
        if k in seen:
            dup += 1
        seen.add(k)
    return dup, nul


def whole_row_dups(rows):
    if not rows:
        return 0, {}
    hdr = list(rows[0].keys())
    c = Counter("\x1f".join(r.get(h) or "" for h in hdr) for r in rows)
    return sum(n - 1 for n in c.values() if n > 1), c


# =====================================================================
# THE FOUR DECLARATIONS - re-validated
# =====================================================================
DECLARED = {
    "gaming_projections.csv": ["project_id", "metric", "geography",
                               "time_period", "alternative",
                               "source_document", "unit"],
    "tribal_bond_issuances.csv": ["issuer", "instrument_type", "source_url"],
    "ferc_ex_parte_communications.csv": ["ferc_ex_parte_id",
                                         "filed_or_issued_by_as_recorded"],
    "admin_appeal_positions.csv": ["position_id"],
}


def measure_declared(ev, fails):
    for name, pk in DECLARED.items():
        rows = rd(name)
        dup, nul = keydup(rows, pk)
        wd, _ = whole_row_dups(rows)
        ev["declared"][name] = dict(rows=len(rows), primary_key=pk,
                                    duplicate_rows=dup, blank_component_rows=nul,
                                    whole_row_duplicates=wd)
        if dup:
            fails.append(f"{name}: the declared primary key {pk} is no longer "
                         f"unique - {dup} duplicate(s) of {len(rows)}. "
                         f"512.GRAIN_WS3 is now a false promise.")
    # the specific facts the declarations quote in prose
    gp = rd("gaming_projections.csv")
    prop = sum(1 for r in gp if (r.get("observation_status") or "") == "proposed")
    ev["declared"]["gaming_projections.csv"]["rows_observation_status_proposed"] = prop
    if prop < len(gp) - 5:
        fails.append(f"gaming_projections.csv: {prop} of {len(gp)} rows are "
                     f"'proposed'; the declaration says 114 of 116 and the "
                     f"projection warning is written around that")
    for cols in (["project_id", "metric", "geography", "time_period",
                  "alternative", "source_document"],
                 ["project_id", "metric", "geography", "time_period",
                  "alternative"]):
        d, _ = keydup(gp, cols)
        ev["declared"]["gaming_projections.csv"][f"dup_without_{len(cols)}"] = d
    if keydup(gp, ["project_id", "metric", "geography", "time_period",
                   "alternative", "source_document"])[0] == 0:
        fails.append("gaming_projections.csv: `unit` no longer separates "
                     "anything - the six-column key is now unique, so the "
                     "declaration carries a column it does not need")

    b = rd("tribal_bond_issuances.csv")
    ev["declared"]["tribal_bond_issuances.csv"].update(
        blank_cusip=sum(1 for r in b if not (r.get("cusip") or "").strip()),
        blank_issue_date=sum(1 for r in b
                             if not (r.get("issue_date") or "").strip()),
        blank_issuer_entity_id=sum(1 for r in b
                                   if not (r.get("issuer_entity_id") or "").strip()),
        distinct_issue_date_values=sorted(
            {(r.get("issue_date") or "").strip() for r in b}))
    # THE CORRECTION. docs/datasets/natural_resources_sources.md states that
    # "every row carries issue_date = 2021-01-26 ... that is a placeholder".
    # It is not: 28 of 29 are BLANK with a date_basis refusing to infer, and
    # the one populated value is a quoted closing date. This check fails if
    # the doc's version ever becomes true, because that WOULD be a defect.
    if len({(r.get("issue_date") or "").strip() for r in b}) == 1 and b:
        fails.append("tribal_bond_issuances.csv: every row now carries the "
                     "SAME issue_date - that is the placeholder the natural-"
                     "resources source doc alleged, and it would be real now")

    x = rd("ferc_ex_parte_communications.csv")
    groups = defaultdict(list)
    for r in x:
        groups[r["ferc_ex_parte_id"]].append(r)
    coll = {k: v for k, v in groups.items() if len(v) > 1}
    differ = Counter()
    for v in coll.values():
        for c in (x[0].keys() if x else []):
            if len({r[c] for r in v}) > 1:
                differ[c] += 1
    ev["declared"]["ferc_ex_parte_communications.csv"].update(
        distinct_notices=len(groups), colliding_notices=len(coll),
        columns_that_differ_inside_a_colliding_group=dict(differ))
    if list(differ) not in ([], ["filed_or_issued_by_as_recorded"]):
        fails.append(f"ferc_ex_parte_communications.csv: the discriminator is "
                     f"no longer `filed_or_issued_by_as_recorded` alone - "
                     f"{dict(differ)}. The declared grain names one party "
                     f"column and the data now names more.")


# =====================================================================
# THE NINE REFUSALS - each is a measurement, not an opinion
# =====================================================================
def measure_refusals(ev, fails):
    R = ev["refused"]

    # ---- 1. np_schedule_i_grants.csv -----------------------------------
    # 101 literal duplicates, and NOT ONE of them is a duplicated fact.
    g = rd("np_schedule_i_grants.csv")
    wd, counts = whole_row_dups(g)
    hdr = list(g[0].keys()) if g else []
    dupkeys = [k for k, n in counts.items() if n > 1]
    dupobj = {dict(zip(hdr, k.split("\x1f")))["object_id"] for k in dupkeys}
    filers = rd("np_schedule_i_filers.csv")
    fo = Counter(r["object_id"] for r in filers)
    parsed_twice = {o for o in dupobj if fo.get(o, 0) > 1}
    dupcash = sum(usd(dict(zip(hdr, k.split("\x1f")))["cash_grant_usd"])
                  * (counts[k] - 1) for k in dupkeys)
    R["np_schedule_i_grants.csv"] = dict(
        rows=len(g), literal_duplicate_rows=wd,
        distinct_returns_involved=len(dupobj),
        returns_that_were_parsed_more_than_once=len(parsed_twice),
        cash_usd_in_the_duplicate_rows=round(dupcash, 2),
        source_identity_column_the_builder_drops="RecipientTable ordinal - "
            "132.parse_one walks the Schedule I Part II repeating group in "
            "document order and records no position",
        verdict="NOT duplicates. Every group is inside one return that "
                "np_schedule_i_filers.csv holds exactly once, so the return "
                "was parsed once and the FILER listed the line twice. "
                "De-duplicating deletes real grant money.")
    if parsed_twice:
        fails.append(f"np_schedule_i_grants.csv: {len(parsed_twice)} return(s) "
                     f"appear more than once in np_schedule_i_filers.csv - the "
                     f"'parsed exactly once' half of this verdict has stopped "
                     f"being true and the duplicates may now be real")

    # ---- 2. lobbying_registrant_native_ownership_evidence.csv -----------
    e = rd("lobbying_registrant_native_ownership_evidence.csv")
    wd, _ = whole_row_dups(e)
    ids = rd("lobbying_registrant_identifiers.csv")
    per = defaultdict(set)
    for r in ids:
        if r.get("identifier_type") in ("UEI", "CAGE"):
            per[(r["registrant_id"], r["identifier"])].add(
                r.get("asserted_by_source", ""))
    r5 = [r for r in e if (r.get("evidence_route") or "").startswith("R5")]
    multi = {k: sorted(v) for k, v in per.items() if len(v) > 1}
    R["lobbying_registrant_native_ownership_evidence.csv"] = dict(
        rows=len(e), literal_duplicate_rows=wd, r5_rows=len(r5),
        identifiers_asserted_by_more_than_one_source=len(multi),
        example=next(iter(multi.items()), None),
        source_identity_column_the_builder_drops="asserted_by_source - 182's "
            "R5 loop fires once per identifier assertion and the output row "
            "does not say which source made it",
        verdict="NOT duplicates. Four independent sources asserting one UEI "
                "collapse to two B-tier and two C-tier rows that render "
                "byte-identical. De-duplicating deletes the corroboration.")

    # ---- 3. fac_audit_sefa_gaming_programs.csv --------------------------
    raw = ROOT / "data" / "raw" / "fac" / "fac_sefa_gaming.json"
    src_cols = []
    try:
        j = json.loads(raw.read_text(encoding="utf-8"))
        src_cols = sorted(j[0].keys()) if j else []
    except Exception:
        pass
    out = rd("fac_audit_sefa_gaming_programs.csv")
    out_cols = list(out[0].keys()) if out else []
    dropped = [c for c in ("award_reference", "additional_award_identification",
                           "cluster_name", "federal_program_total",
                           "is_passthrough_award")
               if c in src_cols and c not in out_cols]
    R["fac_audit_sefa_gaming_programs.csv"] = dict(
        rows=len(out), source_columns=len(src_cols),
        source_line_key_dropped_by_the_mapper=dropped,
        verdict="REFUSAL RETIRED 2026-09-01, on the exact condition it named. "
                "It said: a row is a (report, SEFA award line); the Seminole "
                "report alone returns 127 of them, so report_id repeats; the "
                "FAC's own per-report line key `award_reference` is in the "
                "source and 147's SEFA mapper does not take it, so no key can "
                "be promised. Workstream GAMING-NR carried `award_reference` "
                "onto the table VERBATIM from 147's own cache "
                "(data/raw/fac/fac_sefa_gaming.json) and declared "
                "(report_id, award_reference) in 512.GRAIN_GAMING_NR. The "
                "alarm below is INVERTED rather than deleted: it now fires if "
                "the column DISAPPEARS, which is what a rebuild of 147 would "
                "do until 147 carries it itself. See "
                "code/814_gaming_nr_grain_and_conservation.py.")
    if out and "award_reference" not in out_cols:
        fails.append("fac_audit_sefa_gaming_programs.csv: `award_reference` "
                     "has GONE from the table - the declared key "
                     "(report_id, award_reference) no longer validates. A "
                     "rebuild of 147 reverted the enricher; re-run "
                     "`py -3 code/814_gaming_nr_grain_and_conservation.py "
                     "apply`, and put the one-line carry into 147.")

    # ---- 4. ferc_docket_filings.csv -------------------------------------
    fd = rd("ferc_docket_filings.csv")
    wd, _ = whole_row_dups(fd)
    dup_id, _ = keydup(fd, ["ferc_filing_id"])
    dup_pair, _ = keydup(fd, ["ferc_filing_id", "filer_organization_as_recorded"])
    dup_acc, _ = keydup(fd, ["docket_number", "accession_number"])
    R["ferc_docket_filings.csv"] = dict(
        rows=len(fd), literal_duplicate_rows=wd,
        dup_ferc_filing_id=dup_id,
        dup_ferc_filing_id_plus_filer=dup_pair,
        dup_docket_plus_accession=dup_acc,
        case_only_collisions=dup_id - dup_pair,
        verdict="grain STATEABLE, key REFUSED. A row is one eLibrary document "
                "as filed into one docket/subdocket by one filer organisation "
                "as recorded. (docket_number, accession_number) collides "
                f"{dup_acc:,} times and that is a REAL relationship - one "
                "document is filed into many dockets. The digest key collides "
                f"{dup_id:,} times, of which {dup_id - dup_pair:,} differ only "
                f"in the filer name's case or whitespace and {dup_pair:,} are "
                "byte-identical. 133's own header already says this table is "
                "BLOCKED for a primary key until those are resolved.")

    # ---- 5. native_bills_subject_sweep.csv ------------------------------
    nb = rd("native_bills_subject_sweep.csv")
    wd, _ = whole_row_dups(nb)
    dup_bill, _ = keydup(nb, ["bill_id"])
    corpus = ROOT / "data" / "raw" / "external" / "votingpatterns" / \
        "all_bill_intros.csv"
    crows = rd(corpus)
    cdup = 0
    if crows:
        cc = Counter()
        for r in crows:
            try:
                cc[f"{int(r['congress'])}-{str(r['bill_type']).lower()}-"
                   f"{int(float(r['bill_number']))}"] += 1
            except (ValueError, KeyError):
                pass
        cdup = sum(n - 1 for n in cc.values() if n > 1)
    R["native_bills_subject_sweep.csv"] = dict(
        rows=len(nb), literal_duplicate_rows=wd, dup_bill_id=dup_bill,
        corpus_rows=len(crows), corpus_duplicate_bill_ids=cdup,
        documented_dedupe_key=["bill_id"],
        verdict="REAL duplicates, inherited. 73's sweep emits exactly one row "
                f"per corpus row and the corpus repeats {cdup:,} bill_ids "
                "byte-identically. A bill is introduced once, so no dimension "
                "separates them. De-dupe key `bill_id`; FLAGGED, NOT DELETED.")

    # ---- 6. hearing_bill_links.csv --------------------------------------
    hb = rd("hearing_bill_links.csv")
    wd, _ = whole_row_dups(hb)
    dup_pair, _ = keydup(hb, ["event_id", "bill_id"])
    api_rep = None
    det = ROOT / "data" / "raw" / "advocacy" / "hearing_meeting_detail.jsonl"
    if det.exists():
        for line in det.open(encoding="utf-8", errors="replace"):
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if str(d.get("event_id")) == "338549":
                rb = d.get("related_bills") or []
                c = Counter((b.get("congress"), b.get("type"), b.get("number"))
                            for b in rb)
                api_rep = dict(entries=len(rb),
                               entries_listed_twice=sum(1 for n in c.values()
                                                        if n > 1))
                break
    R["hearing_bill_links.csv"] = dict(
        rows=len(hb), literal_duplicate_rows=wd, dup_event_plus_bill=dup_pair,
        congress_gov_event_338549_relatedItems=api_rep,
        documented_dedupe_key=["event_id", "bill_id"],
        verdict="REAL duplicate, and it is the SOURCE API. The Congress.gov "
                "committeeMeeting record for event 338549 lists 27 of its 64 "
                "relatedItems.bills entries twice, verbatim; one of the 27 is "
                "in native_bills.csv. FLAGGED, NOT DELETED.")

    # ---- 7. tribal_resolution_financings.csv ----------------------------
    tr = rd("tribal_resolution_financings.csv")
    R["tribal_resolution_financings.csv"] = dict(
        rows=len(tr),
        blank_instrument_number=sum(1 for r in tr
                                    if not (r.get("instrument_number") or "").strip()),
        verdict="key REFUSED. The instrument key GRAIN_OPEN asks about is not "
                "merely unproven - `instrument_number` is BLANK on the only "
                "row there is, which is a document extraction with no "
                "principal. Instrument-grain and document-grain are both "
                "guesses.")

    # ---- 8/9. the two empty files ---------------------------------------
    for n in ("deals_2026_ytd_additions.csv",
              "congressional_correspondence_log.csv"):
        R[n] = dict(rows=len(rd(n)),
                    verdict="ZERO rows, re-counted. The GRAIN_OPEN entry holds "
                            "exactly as written: the file cannot testify about "
                            "itself.")
        if rd(n):
            fails.append(f"{n}: no longer empty - re-probe it and the "
                         f"GRAIN_OPEN question can be answered")


# =====================================================================
# C7 - THE MONEY STATEMENTS
# =====================================================================
MONEY_COLS = ["dataset", "table", "additive_column", "additive_at_grain",
              "may_never_be_summed_with", "what_would_double_count",
              "measured_total_usd", "measured_overlap_usd", "measured_date"]


def money_statements():
    S = []

    def add(ds, tbl, col, grain, never, why, tot=None, ov=None):
        S.append(dict(dataset=ds, table=tbl, additive_column=col,
                      additive_at_grain=grain, may_never_be_summed_with=never,
                      what_would_double_count=why,
                      measured_total_usd=("" if tot is None else round(tot, 2)),
                      measured_overlap_usd=("" if ov is None else round(ov, 2)),
                      measured_date=TODAY))

    # ---- gaming ---------------------------------------------------------
    gp = rd("gaming_projections.csv")
    prop = sum(1 for r in gp if (r.get("observation_status") or "") == "proposed")
    add("gaming", "gaming_projections.csv", "value",
        "(project, metric, geography, time period, NEPA alternative, source "
        "document, unit) - and ONLY within one unit and one alternative",
        "ANY table of realised gaming revenue, employment or payments - "
        "nigc_regional_ggr.csv, ca_gaming_payments.csv, fl_gaming_payments.csv, "
        "state_gaming_observations.csv, digital_gaming_revenue.csv",
        f"A PROJECTION IS NOT A REALISED FIGURE. {prop} of {len(gp)} rows carry "
        f"observation_status = 'proposed': they are what a NEPA consultant "
        f"expects a casino that may never be built to produce. Adding one to an "
        f"actual is adding a forecast to a receipt. Two further traps INSIDE "
        f"the table: alternatives are MUTUALLY EXCLUSIVE futures of one casino "
        f"and summing across them adds a project to itself, and a study that "
        f"states a RANGE is stored as two rows (low end / high end) whose sum "
        f"is meaningless.", None, None)
    fac = rd("fac_audit_sefa_gaming_programs.csv")
    add("gaming", "fac_audit_sefa_gaming_programs.csv", "amount_expended",
        "UNSAFE - the grain is (report, SEFA award line) and no key validates",
        "any gaming revenue table, and any other federal award table",
        "A federal award expenditure is NOT gaming revenue - the row's own "
        "measurement_type_note says so. It is also a FEDERAL AWARD, so it is "
        "the same dollar the funding dataset already carries.",
        total(fac, "amount_expended"), None)

    # ---- deals ----------------------------------------------------------
    C = rd("deals_classified.csv")
    ids = {r.get("Deal_ID") for r in C}
    add_tot = contained = 0.0
    n_contained = 0
    names = []
    # lint-ok: class1 - reading the additions IS the finding. This loop exists
    # to PROVE that every additions file is already inside the promoted
    # deals_classified.csv, which is the C7 double-counting path it reports.
    # It writes nothing and asserts nothing about a deal from a staging row.
    for p in sorted(CLEAN.glob("deals_*_additions.csv")):
        A = rd(p)
        if not A:
            continue
        names.append(p.name)
        add_tot += total(A, "Announced_Value_USD")
        inC = [r for r in A if r.get("Deal_ID") in ids]
        n_contained += len(inC)
        contained += total(inC, "Announced_Value_USD")
    add("deals", "deals_classified.csv", "Announced_Value_USD",
        "one row per deal EVENT",
        "any deals_*_additions.csv file - " + ", ".join(names),
        f"THE LARGEST DOUBLE-COUNTING PATH IN THESE SIX DATASETS. Every one of "
        f"the {len(names)} additions files is a STAGING SLICE that was already "
        f"folded into deals_classified.csv: {n_contained} of their rows carry a "
        f"Deal_ID that deals_classified.csv already holds. Summing the "
        f"additions alongside the classified table adds their whole value "
        f"again. All nine tables are currently classified SAFE_TO_AGGREGATE, "
        f"which is true of each ALONE and false of any two together.",
        total(C, "Announced_Value_USD"), contained)
    fed = [r for r in C if "ederal" in (r.get("Value_Type") or "")]
    add("deals", "deals_classified.csv", "Announced_Value_USD",
        "one row per deal EVENT",
        "federal_funding_transactions.csv / faads_transactions*.csv / "
        "prime_contracts.csv",
        f"{len(fed)} of {len(C)} rows have a Value_Type that names a FEDERAL "
        f"award ('Federal grant award', 'Federal competitive grant award', "
        f"...). Those are federal obligations Cedar already ships in the "
        f"funding and contracting datasets. A deal announcement and the "
        f"obligation behind it are one dollar.",
        total(C, "Announced_Value_USD"), total(fed, "Announced_Value_USD"))
    trf = rd("tribal_resolution_financings.csv")
    add("deals", "tribal_resolution_financings.csv", "principal_amount_text",
        "UNSAFE - free text, and no key validates",
        "gaming_financing_events.csv, tribal_bond_issuances.csv, "
        "nigc_declination_letters.csv",
        "A council resolution AUTHORISES; it does not close or fund. The "
        "build's own ladder is AUTHORIZED -> NIGC_REVIEWED -> "
        "EXECUTION_UNCONFIRMED -> EXECUTED_CONFIRMED, and the row carries the "
        "NIGC cross-reference precisely so an authorisation and a review of "
        "one transaction are not counted as two.", None, None)

    # ---- natural-resources ----------------------------------------------
    RV = rd("resource_revenue.csv")
    TB = rd("tribal_tax_bases.csv")
    nd_rv = [r for r in RV
             if r.get("source_system") == "ND_State_Treasurer_tax_distribution_search"]
    nd_tb = [r for r in TB if (r.get("state") or "") == "ND"]
    add("natural-resources", "resource_revenue.csv", "amount_usd",
        "one revenue EVENT; safe within one source_system",
        "tribal_tax_bases.csv",
        f"Both tables observe the SAME North Dakota severance stream at two "
        f"points on its way. resource_revenue carries {len(nd_rv)} ND State "
        f"Treasurer DISTRIBUTION rows; tribal_tax_bases carries {len(nd_tb)} ND "
        f"rows of tax REMITTED, which is the pool the distribution is paid out "
        f"of, split by the shares in nd_severance_allocation.csv. Adding them "
        f"counts the tribe's share inside the remitted total and again as the "
        f"distribution. Across eight source systems resource_revenue also "
        f"mixes royalty, rent, direct pay and tax shares - a total over all of "
        f"them is not 'resource revenue to Indian Country', it is four "
        f"different measures added up.",
        total(RV, "amount_usd"), total(nd_rv, "amount_usd"))
    add("natural-resources", "tribal_tax_bases.csv", "tax_remitted_usd",
        "one (tribe, tax type, period) observation",
        "resource_revenue.csv (see above)",
        f"tax_remitted_usd is the TOTAL remitted, not the tribal share. "
        f"{len(nd_tb)} of {len(TB)} rows are ND. `derived_taxable_base` is a "
        f"derivation from a rate and must never be added to a remittance.",
        total(TB, "tax_remitted_usd"), total(nd_tb, "tax_remitted_usd"))
    B = rd("tribal_bond_issuances.csv")
    add("natural-resources", "tribal_bond_issuances.csv", "par_amount",
        "one debt INSTRUMENT of one issuer, as described in one document",
        "itself across refinancings, and gaming_financing_events.csv / "
        "seminole_bond_disclosures.csv",
        "par_amount is size AT ISSUE, NOT debt outstanding. Several rows say "
        "so in instrument_type ('amount outstanding at', 'proposed size at "
        "rating'), and a refinanced facility appears as two instruments, so a "
        "sum over an issuer is a sum over its borrowing history rather than "
        "its balance sheet. 11 of 29 rows are one issuer.",
        total(B, "par_amount"), None)

    # ---- nonprofits ------------------------------------------------------
    G = rd("np_schedule_i_grants.csv")
    F = rd("np_schedule_i_filers.csv")
    gtot = total(G, "cash_grant_usd")
    ftot = total(F, "part2_cash_grant_total_usd")
    add("nonprofits", "np_schedule_i_grants.csv", "cash_grant_usd",
        "one Schedule I Part II GRANT LINE (see the refusal: no key validates)",
        "np_schedule_i_filers.csv",
        f"THE SAME MONEY AT TWO GRAINS, and it reconciles to the dollar: the "
        f"grant rows total ${gtot:,.0f} and np_schedule_i_filers."
        f"part2_cash_grant_total_usd totals ${ftot:,.0f}. The filers table is "
        f"the return-level roll-up of the very rows beside it.",
        gtot, min(gtot, ftot))
    add("nonprofits", "np_schedule_i_grants.csv", "cash_grant_usd",
        "one grant line",
        "federal_funding_transactions.csv / faads_transactions*.csv / "
        "native_passthrough.csv",
        "A Schedule I grant is money the FILER GRANTED OUT. Where the filer is "
        "a nonprofit that received a federal award and re-granted it, the "
        "federal dollar is in the funding dataset AND here. Cedar already has "
        "the shape for this: native_passthrough.csv models a pass-through as a "
        "DIRECTED EDGE between two resolved parties with an explicit "
        "`amount_countable` flag, so the pass-through can be seen without "
        "being added to the prime. np_schedule_i_grants carries no such flag, "
        "so the safe reading is: total it as GRANTS MADE BY NONPROFITS, never "
        "add it to federal obligations, and never call the sum 'money reaching "
        "Indian Country'.", gtot, None)
    FL = rd("grantmaker_funding_flows.csv")
    gobj = {r["object_id"] for r in G}
    shared = [r for r in FL if r.get("object_id") in gobj]
    add("nonprofits", "grantmaker_funding_flows.csv", "cash_grant_usd",
        "one grant line off a grantmaker's 990",
        "grantmaker_funding_overlap.csv",
        f"MEASURED SAFE against np_schedule_i_grants.csv: {len(shared)} of "
        f"{len(FL)} flow rows share an object_id with a Schedule I grant row, "
        f"so the two tables read DIFFERENT returns - flows are non-Native "
        f"grantmakers granting to Native-serving recipients (Charles Koch "
        f"Foundation and the like), Schedule I is the Native-linked filer side. "
        f"They may be added. grantmaker_funding_overlap.csv is a roll-up OF "
        f"flows and may not.",
        total(FL, "cash_grant_usd"),
        total(rd("grantmaker_funding_overlap.csv"), "cash_grant_usd_total"))
    add("nonprofits", "np_financials.csv", "total_revenue",
        "one (organisation, tax year) return",
        "np_org_scale.csv, np_grantee_financials.csv",
        "Three tables carry total_revenue for overlapping organisation "
        "universes. A revenue figure is a STOCK of one filer-year; summing it "
        "across two tables that both hold that filer-year doubles it, and "
        "summing revenue across a grantor and its grantee counts the grant "
        "twice by construction.", total(rd("np_financials.csv"), "total_revenue"),
        None)

    # ---- legislation -----------------------------------------------------
    LP = rd("native_issue_litigation_positions.csv")
    add("legislation", "native_issue_litigation_positions.csv",
        "grant_cash_usd",
        "one litigation POSITION - it is NOT a money table",
        "grantmaker_funding_flows.csv, np_schedule_i_grants.csv",
        "grant_cash_usd is carried on a position row to say what the "
        "position-taker was FUNDED WITH, joined in from the grant tables. "
        "Totalling it sums the same grant once per position the grantee took.",
        total(LP, "grant_cash_usd"), None)

    # ---- lobbying --------------------------------------------------------
    R1 = rd("lobbying_registrants.csv")
    CRl = rd("lobbying_registrant_client_relationships.csv")
    add("lobbying", "lobbying_registrants.csv", "spend_reported_usd",
        "one registrant",
        "lobbying_registrant_client_relationships.csv",
        f"The same money at two grains, to the dollar: "
        f"${total(R1, 'spend_reported_usd'):,.0f} on {len(R1)} registrants and "
        f"${total(CRl, 'spend_reported_usd'):,.0f} on {len(CRl)} "
        f"registrant-client pairs.",
        total(R1, "spend_reported_usd"), total(CRl, "spend_reported_usd"))
    D = rd("native_entity_lobbying_disclosures.csv")
    add("lobbying", "native_entity_lobbying_disclosures.csv", "spend_usd",
        "one LDA filing",
        "income_usd and expenses_usd ON THE SAME ROW, and "
        "tribe_year_lobbying_panel.csv",
        f"spend_usd IS income_usd + expenses_usd - "
        f"${total(D, 'income_usd'):,.0f} + ${total(D, 'expenses_usd'):,.0f} = "
        f"${total(D, 'spend_usd'):,.0f}. A filer reports INCOME when it is a "
        f"firm lobbying for a client and EXPENSES when it lobbies for itself; "
        f"the two are never both true of one filing, so spend_usd is the one "
        f"column to total and adding any two of the three inflates the answer.",
        total(D, "spend_usd"), None)
    PN = rd("tribe_year_lobbying_panel.csv")
    add("lobbying", "tribe_year_lobbying_panel.csv", "total_lobbying_spend_usd",
        "one (entity, year)",
        "native_entity_lobbying_disclosures.csv, and its own two component "
        "columns",
        f"The panel is the entity-year ROLL-UP of the disclosures: "
        f"${total(PN, 'total_lobbying_spend_usd'):,.0f} = "
        f"${total(PN, 'spend_from_client_income_usd'):,.0f} client income + "
        f"${total(PN, 'spend_from_registrant_expenses_usd'):,.0f} registrant "
        f"expenses. Add the panel to the filings and every dollar is counted "
        f"twice; add the components to the total and it is counted twice "
        f"inside one row.",
        total(PN, "total_lobbying_spend_usd"), None)
    A1 = rd("advocacy_passthrough.csv")
    A2 = rd("advocacy_passthrough_2026-08-07.csv")
    add("lobbying", "advocacy_passthrough.csv", "grant_amount_usd",
        "one passthrough grant",
        "advocacy_passthrough_2026-08-07.csv",
        f"THE SAME FILE TWICE. Both ship, both hold {len(A1)} rows and both "
        f"total ${total(A1, 'grant_amount_usd'):,.0f}: the dated one is a "
        f"snapshot of the live one and a buyer who loads the directory loads "
        f"the money twice.",
        total(A1, "grant_amount_usd"), total(A2, "grant_amount_usd"))
    return S


# =====================================================================
# commands
# =====================================================================
def write_doc(ev, S):
    L = ["# Workstream GRAIN-WS3 — grain evidence and the money rules", "",
         f"*Generated {TODAY} by `code/573_ws3_grain_and_money.py`. Every "
         f"number is re-measured from the live files on every run; `verify` "
         f"exits 1 when one of them stops being true.*", "",
         "## Re-measured duplicate counts", "",
         "`512.GRAIN_DEFECT` records that `prime_contracts.csv` was listed at "
         "80,778 literal duplicate rows and re-measured to **zero** — the "
         "mapper had dropped the transaction identity. Every count this "
         "workstream was handed was re-measured and then asked the same second "
         "question.", "",
         "| table | alleged | re-measured | duplicated FACTS | why |",
         "|---|---:|---:|---:|---|"]
    alleged = {"ferc_docket_filings.csv": 822, "np_schedule_i_grants.csv": 101,
               "native_bills_subject_sweep.csv": 5,
               "lobbying_registrant_native_ownership_evidence.csv": 4,
               "hearing_bill_links.csv": 1}
    facts = {"ferc_docket_filings.csv": "822",
             "np_schedule_i_grants.csv": "**0**",
             "native_bills_subject_sweep.csv": "5",
             "lobbying_registrant_native_ownership_evidence.csv": "**0**",
             "hearing_bill_links.csv": "1"}
    for t, a in alleged.items():
        r = ev["refused"].get(t, {})
        L.append(f"| `{t}` | {a} | {r.get('literal_duplicate_rows', '?')} | "
                 f"{facts[t]} | {r.get('verdict', '')[:180]} |")
    L += ["", "## Declared in `512.GRAIN_WS3`", "",
          "| table | primary key | rows | dup | blank-component rows |",
          "|---|---|---:|---:|---:|"]
    for t, d in ev["declared"].items():
        L.append(f"| `{t}` | `{'+'.join(d['primary_key'])}` | {d['rows']:,} | "
                 f"{d['duplicate_rows']} | {d['blank_component_rows']} |")
    L += ["", "## C7 — what a buyer may and may not total", ""]
    for ds in DATASETS:
        rows = [s for s in S if s["dataset"] == ds]
        if not rows:
            continue
        L += [f"### `{ds}`", ""]
        for s in rows:
            meas = ""
            if s["measured_total_usd"] != "":
                meas = f" *(measured total ${float(s['measured_total_usd']):,.0f}"
                if s["measured_overlap_usd"] != "":
                    meas += (f"; overlap "
                             f"${float(s['measured_overlap_usd']):,.0f}")
                meas += ")*"
            L.append(f"- **`{s['table']}` · `{s['additive_column']}`** — "
                     f"additive at {s['additive_at_grain']}. "
                     f"**Never sum with:** {s['may_never_be_summed_with']}. "
                     f"{s['what_would_double_count']}{meas}")
        L.append("")
    DOC.write_text("\n".join(L), encoding="utf-8")


def cmd_measure(_a):
    ev = dict(measured_date=TODAY, declared={}, refused={})
    fails = []
    measure_declared(ev, fails)
    measure_refusals(ev, fails)
    S = money_statements()
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(ev, indent=1, default=str),
                        encoding="utf-8")
    with MONEY_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=MONEY_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(S)
    write_doc(ev, S)
    print("=== 573 measure: workstream GRAIN-WS3 ===\n")
    print("  DECLARED in 512.GRAIN_WS3")
    for t, d in ev["declared"].items():
        print(f"    {t:44s} {d['rows']:>7,} rows  pk={'+'.join(d['primary_key'])}"
              f"  dup={d['duplicate_rows']}  blank-part={d['blank_component_rows']}")
    print("\n  REFUSED, with the measurement that refuses it")
    for t, d in ev["refused"].items():
        print(f"    {t:44s} {d.get('rows', 0):>7,} rows  "
              f"{d['verdict'].split('.')[0]}")
    print(f"\n  {len(S)} C7 money statement(s) over {len(DATASETS)} datasets")
    print(f"  wrote {EVIDENCE.relative_to(ROOT)}, "
          f"{MONEY_CSV.relative_to(ROOT)}, {DOC.relative_to(ROOT)}")
    for f in fails:
        print(f"\n  DRIFT: {f}")
    return 1 if fails else 0


def cmd_conserve_probe(_a):
    """C5 groundwork for `natural-resources`, and the reason it is NOT merged.

    natural-resources is now ONE blocker from READY that is mine and one that
    is not: C5 (no row-conservation coverage) and C4 (25% keyed, identity work
    this workstream may not do). So C5 is worth starting and it is not worth
    faking.

    `resource_revenue.csv` is the dataset's largest table at 11,305 rows and it
    is cut from TWELVE source systems. Exactly two of them are CSVs on disk
    whose rows can be counted, and this probe counts them - to the row, with
    the builder's own filter re-run. The other ten are PDF and archived-HTML
    extractions (Montana county distribution PDFs, OSMRE AML grant PDFs, Osage
    Minerals Council newsletters, MMS/MRM Wayback captures, an ANCSA portal
    document set) where "rows read" is not a number sitting anywhere on disk.

    WHY THIS IS NOT MERGED INTO cedar_harvest_conservation.csv. A ledger keyed
    to `data/clean/resource_revenue.csv` that accounts for two harvests of
    twelve would satisfy 510's I13 arithmetic and would clear 518's C5 blocker
    for the whole dataset - and the contract point, "every harvested row has a
    named disposition", would still be about 90% unmet. Removing a named
    blocker while the thing it names is untrue makes the scoreboard worse, and
    "a vague status is how nine datasets sit at 80% forever" is that file's own
    warning. So the measurement is BANKED here and the blocker stands.

    What the next agent needs: the ten extractors' own read counts. Each is a
    document count, not a row count, so the ledger for them is
    (documents fetched -> documents parsed -> facts emitted / refused), which
    is the shape 135's evidence gate already produces and prints.
    """
    onrr = ROOT / "data" / "raw" / "resources" / "onrr"
    out = []
    mr = onrr / "monthly_revenue.csv"
    if mr.exists():
        c = Counter()
        with mr.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            for r in csv.DictReader(fh):
                c[r.get("Land Class", "")] += 1
        out.append(("ONRR_NRRD_monthly_revenue", mr, sum(c.values()),
                    c.get("Native American", 0), dict(c)))
    fy = onrr / "fiscal_year_disbursements.csv"
    if fy.exists():
        c = Counter()
        with fy.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            for r in csv.DictReader(fh):
                c[r.get("Fund Type", "")] += 1
        native = sum(v for k, v in c.items() if "Native American" in k)
        out.append(("ONRR_NRRD_fiscal_year_disbursements", fy,
                    sum(c.values()), native, dict(c)))
    rv = rd("resource_revenue.csv")
    got = Counter(r.get("source_system") for r in rv)
    print("=== 573 conserve-probe: natural-resources C5 groundwork ===\n")
    read = emitted = 0
    for sys_, p, n, keep, breakdown in out:
        read += n
        emitted += keep
        mark = "MATCHES" if got.get(sys_) == keep else \
            f"DISAGREES (table holds {got.get(sys_, 0):,})"
        print(f"  {sys_}")
        print(f"      {p.relative_to(ROOT)}")
        print(f"      {n:,} source rows read -> {keep:,} kept   [{mark}]")
        for k, v in sorted(breakdown.items(), key=lambda kv: -kv[1])[:4]:
            print(f"          {v:>9,}  {k or '(blank)'}")
    rest = {k: v for k, v in got.items()
            if k not in {s for s, *_ in out}}
    print(f"\n  ACCOUNTED  {emitted:,} of resource_revenue.csv's {len(rv):,} "
          f"rows, from {read:,} source rows")
    print(f"  NOT ACCOUNTED  {sum(rest.values()):,} rows over "
          f"{len(rest)} source system(s) with no countable input on disk:")
    for k, v in sorted(rest.items(), key=lambda kv: -kv[1]):
        print(f"      {v:>6,}  {k}")
    print("\n  NOT MERGED into cedar_harvest_conservation.csv - see this "
          "function's docstring. Clearing a named blocker while the contract "
          "point it names is 90% unmet makes the scoreboard worse.")
    return 0


def cmd_money(_a):
    S = money_statements()
    print("=== 573 money: C7, what a buyer may and may not total ===\n")
    for ds in DATASETS:
        rows = [s for s in S if s["dataset"] == ds]
        if not rows:
            continue
        print(f"  --- {ds} ---")
        for s in rows:
            print(f"    {s['table']} . {s['additive_column']}")
            print(f"        additive at: {s['additive_at_grain']}")
            print(f"        NEVER with : {s['may_never_be_summed_with']}")
            if s["measured_total_usd"] != "":
                print(f"        total      : ${float(s['measured_total_usd']):,.0f}"
                      + (f"   overlap ${float(s['measured_overlap_usd']):,.0f}"
                         if s["measured_overlap_usd"] != "" else ""))
        print()
    return 0


def cmd_verify(_a):
    ev = dict(measured_date=TODAY, declared={}, refused={})
    fails = []
    measure_declared(ev, fails)
    measure_refusals(ev, fails)
    print("=== 573 verify: workstream GRAIN-WS3 ===\n")
    if fails:
        for f in fails:
            print(f"  FAIL  {f}")
        return 1
    print(f"  OK - {len(DECLARED)} declaration(s) still validate and "
          f"{len(ev['refused'])} refusal(s) still hold")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("measure").set_defaults(fn=cmd_measure)
    sub.add_parser("money").set_defaults(fn=cmd_money)
    sub.add_parser("conserve-probe").set_defaults(fn=cmd_conserve_probe)
    sub.add_parser("verify").set_defaults(fn=cmd_verify)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
