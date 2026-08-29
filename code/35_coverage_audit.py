#!/usr/bin/env python3
"""
Cedar Press - 35: Temporal coverage audit, measured from the data.

PURPOSE
-------
Cedar Press promises 2000-2026 on every dataset where the source allows it.
This script does not read that promise out of the documentation - it measures
it out of the rows, so a doc claim and the actual file can be compared and any
disagreement surfaces as a defect rather than passing quietly.

For each dataset it reports: the date column used, first and last observed
year, per-year row counts, INTERIOR gaps (years inside the observed range with
zero rows) and EDGE gaps (missing years between 2000 and 2026 at either end).

The two gap kinds mean different things and must not be pooled:

  INTERIOR gap  a year inside the range with no rows. Almost always a defect -
                a failed pull, a dropped chunk, a filter that ate a year.
  EDGE gap      coverage that has not reached the floor or the present yet.
                Sometimes a real source limit (FSRS subawards do not exist
                before 2010; the Lobbying Disclosure Act electronic filings
                start in 1999-2000) and sometimes just unfinished work.

A source limit is only legitimate when it is DOCUMENTED. `SOURCE_FLOORS`
records the ones established so far; anything else reports as unexplained.

WHICH FILE EACH DATASET IS TREATED AS THE TRUTH
-----------------------------------------------
`DATASETS` below IS that statement: one dataset name -> one file (or glob)
under `data/clean/`. Read it before quoting any number this script produces.

Where a dataset has a PROMOTED table assembled from parts, the promoted table
is the truth and the parts are refused - see the `deals` entry and the guard in
`main()`. That refusal exists because this script's own `deals` entry was
`deals_*_additions.csv` and undercounted the ledger by 145 rows for three
weeks (`docs/FACT_CHECK_2026-08-06.md` finding B-1).

Writes docs/COVERAGE_AUDIT.md and data/clean/coverage_audit.csv
"""

import csv
import glob
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cedar_domain as DOM   # noqa: E402  - DEALS_TRUTH, PROMOTED_TABLES
import cedar_period_columns as PERIODS   # noqa: E402  - the ONE declaration

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
DOCS = CEDAR / "docs"
TODAY = date.today().isoformat()

FLOOR, CEILING = 2000, 2026

# Candidate date columns, best first. The first one present in a file wins.
#
# 2026-08-05: gaming was reported as "no usable date column" and that was a
# defect in THIS LIST, not in the data. Both gaming files were fully dated -
# `gaming_facilities` under `open_date`, `gaming_facility_metrics` under
# `observation_date` / `observation_period` - and neither name was here. The
# lesson generalises: an entity dataset dates itself with a LIFESPAN column
# and a measurement dataset with an AS-OF column, and neither looks like the
# `action_date` of a transaction file. Both shapes are now recognised.
#
# Matching is exact on the lowercased name, so "date" does NOT match
# "open_date" and "fetched_date" is correctly never picked up as an event date.
DATE_COLS = [
    "action_date", "Event_Date", "event_date", "filing_date", "decision_date",
    "publication_date", "effective_date", "award_date", "date",
    "Event_Year", "fiscal_year", "filing_year", "year", "tax_year",
    "report_year", "vote_date", "introduced_date", "signed_date",
    # entity lifespans and point-in-time measurements
    "open_date", "as_of_date", "observation_date", "observation_period",
    "document_date", "source_document_date",
]

# Event data is legitimately sparse: compacts are not signed every year and
# neither are gaming land decisions. Flagging a quiet year as a defect there
# manufactures alarm. Only CONTINUOUS transaction data earns an interior-gap
# defect, because for those a zero year really does mean a failed pull.
EVENT_DATASETS = {"compacts", "gaming_land_decisions", "bills_votes",
                  "deals", "ownership_events", "gaming_decision_events",
                  "gaming_facilities", "gaming_project_facilities",
                  "gaming_mitigation_agreements", "gaming_projections",
                  # added 2026-08-26 with the five newly-visible datasets.
                  # Consultation notices and revenue BOUNDS are genuinely
                  # event-driven and sparse: a tribe is not consulted every
                  # year and a bound is only published where a source states
                  # one, so a quiet year is not a failed pull. FERC filings,
                  # CA gaming payments and resource revenue are CONTINUOUS and
                  # are deliberately NOT listed - for those a zero year really
                  # would be a defect and should be allowed to say so.
                  "consultation_events", "section_106_consultation_events",
                  "gaming_revenue_bounds"}

# Documented source limits. A dataset that cannot reach 2000 is only excused
# when the reason is recorded HERE, with the reason - never inferred from the
# data being absent, which is circular.
SOURCE_FLOORS = {
    "subcontracts": (2010, "FSRS subaward reporting began under FFATA in 2010; "
                           "no subaward records exist before then."),
    "federal_actions": (2000, "Federal Register API covers the full window."),
    "gaming_land_decisions": (2000, "Interior published decisions; earlier ones "
                                    "are paper-only."),
    "gaming_projections": (2023, "Not a time series. A two-project NEPA "
                                 "extraction pilot (Osage Lake Ozark 2025, "
                                 "Menominee Kenosha 2023-2026); the range is "
                                 "the pilot's, not the source's."),
    "gaming_project_facilities": (2013, "Same two-project NEPA pilot."),
    "gaming_mitigation_agreements": (1992, "Same two-project NEPA pilot; the "
                                           "1992 row is the Menominee-Wisconsin "
                                           "compact cited in the Kenosha EA."),
}

# The mirror of SOURCE_FLOORS at the top end. A dataset can be complete and
# still stop short of the present because its source does. Narrative only -
# an undocumented ceiling still reports as unfinished work.
SOURCE_CEILINGS = {
    # `gaming_facilities` was here with a 2018 ceiling and has been REMOVED
    # (2026-08-06). The 2018 ceiling belonged to the INHERITED Casino City
    # `Open Date` column, not to the dataset. Hand research against primary
    # sources has since dated openings through 2025, so the vendor ceiling no
    # longer binds the dataset's reach and asserting it would understate what
    # the file now covers.
    #
    # What remains - no 2026 openings - is NOT a source limit. It is ordinary
    # unfinished work, and letting the audit say so is the honest outcome. A
    # ceiling entry would have suppressed that warning permanently, which is
    # exactly the failure mode SOURCE_CEILINGS exists to avoid: a documented
    # limit must be a real limit, not a place to park a known gap.
    #
    # The fact that post-2018 coverage rests on hand research rather than on a
    # vendor column is a genuine caveat and is recorded in
    # docs/GAMING_TEMPORAL_BUILD_LOG.md and STATE_OF_BUILD.md, where it belongs.
    "gaming_facility_metrics": (2026, "Capacity observations end with the "
                                      "Casino City panel (2023-01); revenue and "
                                      "payment observations run to 2026."),
}

DATASETS = {
    # THE FILE THIS AUDIT TREATS AS THE TRUTH FOR DEALS: the PROMOTED table.
    #
    # This entry read `deals_*_additions.csv` from the first version until
    # 2026-08-26 and it is the origin of `docs/FACT_CHECK_2026-08-06.md`
    # finding B-1, which named the miscount and was then ignored for three
    # weeks: "the audit globs `deals_*_additions.csv` and never sees the 132
    # rows in the root ledgers." An additions file is meaningless without the
    # base it adds to. Measured the day this was fixed:
    #
    #     9 x data/clean/deals_*_additions.csv          790 rows
    #     deals_2026_ytd.csv           (PROJECT ROOT)     90
    #     deals_historical_2020_2025.csv (PROJECT ROOT)   56
    #     data/clean/deals_classified.csv  <- THE TRUTH  935
    #
    # 790 is what this file reported, and it is also why `docs/COVERAGE_AUDIT.md`
    # said 790 in two places. The promoted table is the only correct input: it
    # is the merged superset AND it already honours
    # `review/deals_withdrawn_duplicates.csv` (MA2020-008, withdrawn as a
    # duplicate of ANCSA2-2020-004), which re-assembling the parts here would
    # not. See `cedar_domain.PROMOTED_TABLES` for the general rule.
    "deals": DOM.DEALS_TRUTH.rsplit("/", 1)[-1],
    "federal_funding": "federal_funding_transactions.csv",
    "faads": "faads_transactions_all_agencies.csv",
    "subcontracts": "subawards.csv",
    "lobbying": "native_entity_lobbying_disclosures.csv",
    "federal_actions": "federal_actions.csv",
    "bills_votes": "bill_votes.csv",
    "native_bills": "native_bills.csv",
    "nonprofit_financials": "np_financials.csv",
    "compacts": "compact_events.csv",
    "gaming_land_decisions": "gaming_land_decisions.csv",
    "gaming_decision_events": "gaming_decision_events.csv",
    # Split, because they answer different questions and a glob over both made
    # one arbitrary date column stand for both. The facility file is an ENTITY
    # file dated by when each casino opened; the metrics file is a MEASUREMENT
    # file dated by when each quantity was observed. Pooling them would put a
    # 2019 slot count in the same series as a 1987 opening.
    "gaming_facilities": "gaming_facilities.csv",
    "gaming_facility_metrics": "gaming_facility_metrics.csv",
    "gaming_project_facilities": "gaming_project_facilities.csv",
    "gaming_projections": "gaming_projections.csv",
    "gaming_mitigation_agreements": "gaming_mitigation_agreements.csv",
    "prime_contracts": "prime_contracts.csv",
    "ownership_events": "ownership_events.csv",
    # --- added 2026-08-26 by script 337 -----------------------------------
    # FIVE FULLY-DATED TABLES THAT THIS AUDIT HAS NEVER SEEN. Each keys its
    # period in a column absent from `DATE_COLS` below, so `audit_file()` fell
    # through its candidate loop, hit `continue`, and the dataset simply never
    # appeared - which reads as "not audited yet" and is indistinguishable from
    # "has no dates". Measured fill at the time of adding, all 100% except the
    # documented resource_revenue coalesce:
    #     gaming_revenue_bounds  fiscal_year  13,803   1994-2025
    #     ca_gaming_payments     period_end   40,164   2001-2026
    #     resource_revenue       period_end +
    #                            payment_date 10,482   1993-2026
    #     consultation_events    notice_date  11,402   1994-2026
    #     ferc_docket_filings    filed_date  102,615   1990-2026
    # Their period column is DECLARED in `code/cedar_period_columns.py` and
    # resolved from there, not guessed from a name list.
    "gaming_revenue_bounds": "gaming_revenue_bounds.csv",
    "ca_gaming_payments": "ca_gaming_payments.csv",
    "resource_revenue": "resource_revenue.csv",
    "consultation_events": "consultation_events.csv",
    "section_106_consultation_events": "section_106_consultation_events.csv",
    "ferc_docket_filings": "ferc_docket_filings.csv",
}

YEAR_RE = re.compile(r"(19|20)\d{2}")

# Datasets that grade their own dates. An undated row is not one thing: it may
# be BOUNDED (a source proves the event happened inside a window, we just have
# no stated date) or ABSENT (nothing found). Pooling them understates the
# dataset, because a bounded row is usable and a missing one is not.
# dataset -> (class column, interval columns)
CLASS_COLS = {
    "gaming_facilities": ("open_date_class",
                          "open_date_not_before", "open_date_not_after"),
}


def class_breakdown(paths, cls_col, lo_col, hi_col):
    """Count the date-evidence classes, and the year span the BOUNDED rows
    cover, which no date column can express."""
    counts, lo, hi = Counter(), None, None
    for p in paths:
        with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
            rd = csv.DictReader(fh)
            if not rd.fieldnames or cls_col not in rd.fieldnames:
                continue
            for row in rd:
                c = (row.get(cls_col) or "").strip() or "unclassified"
                counts[c] += 1
                if c != "bounded":
                    continue
                for col, keep in ((lo_col, "lo"), (hi_col, "hi")):
                    y = year_of(row.get(col))
                    if not y:
                        continue
                    if keep == "lo":
                        lo = y if lo is None else min(lo, y)
                    else:
                        hi = y if hi is None else max(hi, y)
    return counts, lo, hi


def year_of(v):
    """Pull a plausible year out of a date-ish value. Returns None, never a
    guess: a value with no 4-digit year in range yields nothing."""
    if not v:
        return None
    s = str(v).strip()
    if not s:
        return None
    m = YEAR_RE.search(s)
    if not m:
        return None
    y = int(m.group(0))
    return y if 1900 <= y <= 2100 else None


def audit_file(paths):
    """Count rows per year.

    COLUMN CHOICE, IN PRIORITY ORDER (changed 2026-08-26 by script 337):

      1. The table's own DECLARATION in `code/cedar_period_columns.py`. A
         declaration is a measured, documented statement about THIS table and
         it beats any global name list. If a table declares a column and the
         file does not have it, `resolve()` RAISES - that is fatal and is
         reported as a defect, never as a year with no rows.
      2. Otherwise the global `DATE_COLS` candidate list, as before.
      3. Otherwise the dataset is recorded as NO_DATE_COLUMN and NAMED.

    Step 3 is the change that matters as much as step 1. This function used to
    `continue` when no candidate matched, so a table with an unrecognised date
    column produced an empty counter and vanished from the report - the same
    shape as `102` reading a missing column as an empty source. A dataset that
    cannot be dated is now a stated finding with its header attached.

    A DECLARED COALESCE IS APPLIED PER ROW, not per file. `resource_revenue`
    carries its period in `period_end` on 9,993 rows and `payment_date` on the
    other 489, disjointly; picking one column for the whole file would drop
    whichever slice lost. `resolve()` names the first column present, and the
    remaining declared columns are tried per row when it is blank.
    """
    years, col_used, rows_total, undated = Counter(), None, 0, 0
    note = None
    for p in paths:
        name = Path(p).name
        try:
            with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
                rd = csv.DictReader(fh)
                if not rd.fieldnames:
                    continue
                lower = {c.lower(): c for c in rd.fieldnames}

                # 1. the declaration wins
                declared = PERIODS.PERIOD_COLUMNS.get(name)
                cols = []
                if declared:
                    try:
                        PERIODS.resolve(name, rd.fieldnames)
                    except PERIODS.PeriodColumnMissing as e:
                        # FATAL, and it must look fatal.
                        print(f"    !! {name}: DECLARED PERIOD COLUMN ABSENT")
                        print(f"       {e}")
                        note = "DECLARED_PERIOD_COLUMN_ABSENT"
                        continue
                    cols = [lower[c.lower()] for c in declared["cols"]
                            if c.lower() in lower]
                else:
                    # 2. the global candidate list
                    for cand in DATE_COLS:
                        if cand.lower() in lower:
                            cols = [lower[cand.lower()]]
                            break

                # 3. neither: a finding, with the header, not a silent skip
                if not cols:
                    print(f"    !! {name}: NO DATE COLUMN RECOGNISED "
                          f"({rows_total:,} rows unread). Header: "
                          f"{', '.join(list(rd.fieldnames)[:10])} ...")
                    print(f"       If this table IS dated, declare it in "
                          f"code/cedar_period_columns.py rather than adding a "
                          f"name to DATE_COLS.")
                    note = "NO_DATE_COLUMN"
                    continue

                col_used = col_used or cols[0]
                for row in rd:
                    rows_total += 1
                    y = None
                    for c in cols:            # documented coalesce, per row
                        y = year_of(row.get(c))
                        if y:
                            break
                    if y:
                        years[y] += 1
                    else:
                        undated += 1
        except Exception as e:
            print(f"    !! {Path(p).name}: {e}")
    if note and col_used is None:
        col_used = note
    return years, col_used, rows_total, undated


def main():
    print("=== Cedar Press 35: temporal coverage audit ===\n")
    out_rows, report = [], []

    # A DATASETS entry that names a PART of a promoted table is the B-1 defect
    # being re-introduced. It is refused loudly here rather than reported as a
    # smaller row count, because a smaller row count reads as a fact about the
    # dataset. This is a coverage audit; an audit that undercounts by
    # construction is worse than no audit.
    mis = {n: p for n, p in DATASETS.items() if DOM.promoted_table_for(p)}
    if mis:
        for n, p in sorted(mis.items()):
            print(f"FATAL: dataset '{n}' is pointed at '{p}', which is a PART "
                  f"of {DOM.promoted_table_for(p)}, not the promoted table. "
                  f"That is FACT_CHECK_2026-08-06 finding B-1. Point it at the "
                  f"promoted table.")
        raise SystemExit(2)

    for name, pattern in DATASETS.items():
        paths = sorted(glob.glob(str(CLEAN / pattern)))
        # Never audit a dataset against its own review/queue by-products.
        paths = [p for p in paths
                 if not re.search(r"(queue|matches|attribution|unmatched|"
                                  r"candidates|_map|harvest)", Path(p).name, re.I)]
        if not paths:
            print(f"{name:24s} NO FILE  ({pattern})")
            report.append((name, None, None, [], [], 0, 0, pattern, []))
            continue

        years, col, total, undated = audit_file(paths)
        if not years:
            print(f"{name:24s} no usable date column  ({len(paths)} file(s))")
            report.append((name, None, None, [], [], total, undated, col, paths))
            continue

        lo, hi = min(years), max(years)
        interior = ([] if name in EVENT_DATASETS
                    else [y for y in range(lo, hi + 1) if years.get(y, 0) == 0])
        floor = SOURCE_FLOORS.get(name, (FLOOR, None))[0]
        edge_lo = [y for y in range(floor, min(lo, CEILING + 1))]
        edge_hi = [y for y in range(hi + 1, CEILING + 1)]

        print(f"{name:24s} {lo}-{hi}  rows={total:>9,}  col={col}")
        if undated:
            print(f"{'':24s}   undated rows: {undated:,}")
        if interior:
            print(f"{'':24s}   INTERIOR GAPS: {interior}")
        if edge_lo:
            print(f"{'':24s}   missing early: {edge_lo[0]}-{edge_lo[-1]}")
        if edge_hi:
            print(f"{'':24s}   missing late : {edge_hi[0]}-{edge_hi[-1]}")

        report.append((name, lo, hi, interior, edge_lo + edge_hi, total,
                       undated, col, paths))
        for y in range(min(lo, FLOOR), max(hi, CEILING) + 1):
            out_rows.append({"dataset": name, "year": y,
                             "rows": years.get(y, 0),
                             "in_observed_range": int(lo <= y <= hi),
                             "date_column": col, "audited": TODAY})

    with open(CLEAN / "coverage_audit.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["dataset", "year", "rows",
                                           "in_observed_range", "date_column",
                                           "audited"])
        w.writeheader()
        w.writerows(out_rows)
    print(f"\nwrote data/clean/coverage_audit.csv ({len(out_rows):,} rows)")

    # ---- markdown -------------------------------------------------------
    L = [f"# Coverage Audit\n",
         f"*Measured from the data on {TODAY}. Not copied from any doc - "
         f"regenerate with `py -3 code/35_coverage_audit.py` and this file "
         f"reflects the files as they actually are.*\n",
         f"Target window: **{FLOOR}-{CEILING}**.\n",
         "| Dataset | Observed | Rows | Interior gaps | Outside target window |",
         "|---|---|---:|---|---|"]
    for (name, lo, hi, interior, edge, total, undated, col, paths) in report:
        if lo is None:
            L.append(f"| `{name}` | — | — | — | no dated file found |")
            continue
        ig = ", ".join(str(y) for y in interior) if interior else "none"
        eg = f"{len(edge)} yr" if edge else "complete"
        L.append(f"| `{name}` | {lo}–{hi} | {total:,} | {ig} | {eg} |")

    L.append("\n## Interior gaps\n")
    L.append("A year inside a dataset's own range with zero rows. These are "
             "defects until proven otherwise - a year that genuinely had no "
             "activity is rare, and a failed pull looks exactly like one.\n")
    any_gap = False
    for (name, lo, hi, interior, edge, total, undated, col, paths) in report:
        if interior:
            any_gap = True
            L.append(f"- **`{name}`** — {interior}")
    if not any_gap:
        L.append("None. Every dataset is contiguous across its observed range.\n")

    L.append("\n## Distance to the target window\n")
    for (name, lo, hi, interior, edge, total, undated, col, paths) in report:
        if lo is None:
            continue
        floor, why = SOURCE_FLOORS.get(name, (FLOOR, None))
        bits = []
        if lo > floor:
            bits.append(f"starts {lo}, {lo-floor} yr short of {floor}")
        if hi < CEILING:
            bits.append(f"ends {hi}, {CEILING-hi} yr short of {CEILING}")
        if not bits:
            continue
        line = f"- **`{name}`** — " + "; ".join(bits)
        notes = []
        if name in SOURCE_FLOORS:
            notes.append(f"*Documented source limit (start):* {SOURCE_FLOORS[name][1]}")
        if name in SOURCE_CEILINGS and hi <= SOURCE_CEILINGS[name][0]:
            notes.append(f"*Documented source limit (end):* {SOURCE_CEILINGS[name][1]}")
        if notes:
            line += "  \n  " + "  \n  ".join(notes)
        else:
            line += "  \n  *No documented source limit — treat as unfinished work.*"
        L.append(line)

    # Some datasets are halves of one series and are misread alone. FAADS ends
    # exactly where the modern assistance file begins, so judging either
    # against 2000-2026 on its own reports a gap that the pair does not have.
    # ATTRIBUTABLE COVERAGE
    # ---------------------
    # Rows present is not the same claim as rows usable, so the attributable
    # floor is reported separately from the row range.
    #
    # This section used to say "Attributable floor: FY2007", on the evidence
    # that `pct_with_duns` is 0.0% across all 66 pre-2007 agency-years. The
    # identifier evidence was right and the CONCLUSION was wrong, because it
    # answered a question nobody asked. Pre-2007 rows are 100.0% populated on
    # `recipient_name`, `recipient_type` and `recipient_state`, and name-based
    # attribution is what every other dataset in this project uses. "No
    # identifier" means a WEAKER attribution, not an impossible one - a tier,
    # not a wall.
    #
    # `code/73_faads_name_attribution.py` therefore attributes the pre-2007
    # rows by name at tier B, and this section now reports two floors: the
    # tier-A/identifier floor, which really is FY2007, and the tier-B/name
    # floor, which is FY2001. Reporting only the first understated the series
    # by six years; reporting only the second would let a subscriber treat a
    # name match as an identifier match.
    L.append("\n## Attributable coverage\n")
    L.append("Rows existing is a weaker claim than rows usable, so each "
             "dataset reports the year from which its rows can actually be "
             "attributed to an entity — which is not always the year its rows "
             "begin.\n")
    L.append("Attributability is a TIER, not a yes/no. A row carrying a DUNS "
             "or UEI supports a tier-A per-entity series. A row carrying only "
             "a recipient name, state and recipient-type code supports a "
             "tier-B one — weaker, guarded, and auditable, but not nothing. "
             "A row carrying neither supports programme-level totals only. "
             "Conflating the second case with the third is how six years of "
             "this dataset were written off once.\n")
    cov = CLEAN / "faads_identifier_coverage_by_agency_year.csv"
    if cov.exists():
        byyr = {}
        with open(cov, encoding="utf-8-sig", newline="") as fh:
            cov_rows = list(csv.DictReader(fh))
        for r in cov_rows:
            try:
                y = int(r["fiscal_year"])
                byyr.setdefault(y, []).append(float(r.get("pct_with_duns") or 0))
            except (ValueError, TypeError):
                continue
        if byyr:
            usable = sorted(y for y, v in byyr.items() if max(v) > 0)
            dead = sorted(y for y, v in byyr.items() if max(v) == 0)
            floor_id = min(usable) if usable else None
            L.append(f"- **`faads`** — rows span {min(byyr)}–{max(byyr)}. "
                     f"**No row carries a recipient identifier before "
                     f"{floor_id or 'n/a'}**: {len(dead)} fiscal years "
                     f"({dead[0]}–{dead[-1]}) are 0.0% DUNS across every "
                     f"agency, maximum 0.0%. That is a reporting-regime fact, "
                     f"not a retrieval failure, and it was confirmed by "
                     f"pulling one agency-year through two independent routes "
                     f"with identical results.")
            L.append(f"  \n  **Identifier floor (tier A): FY{floor_id or '?'}.** "
                     f"Any series that requires a DUNS or UEI must start "
                     f"there.")

            # The name-based floor, measured from the attribution file itself.
            summ = CLEAN / "faads_attribution_summary.json"
            if summ.exists():
                import json as _json
                s = _json.loads(summ.read_text(encoding="utf-8"))
                yrs_b = s.get("years") or []
                if yrs_b:
                    L.append(
                        f"  \n  **Name floor (tier B): FY{min(yrs_b)}.** The "
                        f"pre-{floor_id or '?'} rows are NOT unattributable. "
                        f"They are 100.0% populated on `recipient_name`, "
                        f"`recipient_type` and `recipient_state`, and "
                        f"`code/73_faads_name_attribution.py` attributes "
                        f"**{s['attributed_rows']:,} transactions** to "
                        f"**{s['distinct_entities']:,} entities** across "
                        f"FY{min(yrs_b)}–FY{max(yrs_b)} — "
                        f"${s['attributed_gross_usd']:,.0f} gross, "
                        f"${s['attributed_net_usd']:,.0f} net of "
                        f"deobligations. Every one of those links is **tier "
                        f"B**: a name is not an identifier, and none may be "
                        f"promoted to tier A.")
                    L.append(
                        f"  \n  The attributed rows are "
                        f"{s['attributed_rows']/s['window_rows']*100:.2f}% of "
                        f"the {s['window_rows']:,} rows in the window and "
                        f"{s['attributed_rows']/s['pool_I_rows']*100:.1f}% of "
                        f"the {s['pool_I_rows']:,} rows USAspending itself "
                        f"codes as tribal government (`recipient_type = I`). "
                        f"The remainder of the window is state governments, "
                        f"individuals, universities and cities — not Native "
                        f"recipients, and never attributable to a tribe. "
                        f"Refusals are itemised in "
                        f"`review/faads_attribution_refusals_*.csv` and the "
                        f"method and audited error rate in "
                        f"`docs/FAADS_NAME_ATTRIBUTION_LOG.md`.")

    L.append("\n## Combined series\n")
    L.append("Two files can form one continuous series. Judged separately each "
             "looks short; judged together the coverage is real. Report the "
             "combination, not either half.\n")
    obs = {name: (lo, hi) for (name, lo, hi, *_rest) in report if lo}
    for label, parts in [
        ("Federal assistance", ["faads", "federal_funding"]),
    ]:
        have = [p for p in parts if p in obs]
        if len(have) < 2:
            continue
        lo = min(obs[p][0] for p in have)
        hi = max(obs[p][1] for p in have)
        seg = " + ".join(f"`{p}` {obs[p][0]}–{obs[p][1]}" for p in have)
        L.append(f"- **{label}** — {seg} → **{lo}–{hi} continuous**")
        if hi < CEILING:
            L.append(f"  \n  Still short of {CEILING} by {CEILING-hi} yr.")

    L.append("\n## Undated rows\n")
    L.append("A row with no parseable date cannot be placed in any year, so it "
             "silently vanishes from every time series built off this data.\n")
    for (name, lo, hi, interior, edge, total, undated, col, paths) in report:
        if undated:
            pct = undated / total * 100 if total else 0
            L.append(f"- **`{name}`** — {undated:,} of {total:,} ({pct:.1f}%)")

    L.append("\n## Undated is not one thing\n")
    L.append("Where a dataset grades its own date evidence, an undated row "
             "splits into **bounded** (a source proves the event happened "
             "inside a window; no source states the date) and **absent** "
             "(nothing found, or the row is not the kind of thing that has "
             "one). A bounded row is usable — it can be filtered, ranked and "
             "placed in an interval — so pooling the two understates the "
             "dataset.\n")
    for (name, lo, hi, interior, edge, total, undated, col, paths) in report:
        if name not in CLASS_COLS or not paths:
            continue
        cls_col, lo_col, hi_col = CLASS_COLS[name]
        counts, blo, bhi = class_breakdown(paths, cls_col, lo_col, hi_col)
        if not counts:
            continue
        n = sum(counts.values())
        parts = " · ".join(f"**{k}** {v:,} ({v/n:.0%})"
                           for k, v in counts.most_common())
        L.append(f"- **`{name}`** ({cls_col}) — {parts}")
        if blo and bhi:
            L.append(f"  \n  Bounded rows are pinned to intervals spanning "
                     f"{blo}–{bhi}; none of that shows in the `{col}` range "
                     f"above.")

    (DOCS / "COVERAGE_AUDIT.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote docs/COVERAGE_AUDIT.md")


if __name__ == "__main__":
    main()
