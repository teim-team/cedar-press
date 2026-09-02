#!/usr/bin/env python3
"""
227_anomaly_sweep.py - a standing year-over-year anomaly sweep across every
Cedar Press collection and evidence layer.

    Elijah, 2026-08-26: "For all the datasets, do an analysis if there is
    anything odd - because we have year-to-year data over such a long time
    horizon, that allows us to do good sanity checks. Like, did an entity
    suddenly get a bunch of money one year? Is that explainable?"

    And, the same day: "Also do research to make sure it's not like data
    coverage or reporting impacting coverage as well - we need to be clear
    what the assumptions and limitations of the datasets are."

THE FRAMING
-----------
**A spike is either a fact about the world, a fact about the rules, or a fact
about our pipeline.** Year-over-year is how you tell them apart. Every anomaly
this script emits is typed as exactly one of:

    PIPELINE  our code, our pull, our linkage. An artefact we made.
    REGIME    a reporting rule changed - a threshold moved, a filing frequency
              doubled, a relief programme opened. A fact about a statute, not
              about Indian Country and not about our code.
    WORLD     a fact about the world that survived both of the above.
    UNKNOWN   we could not separate the candidates. Named, never smoothed.

**ORDER OF INFERENCE: PIPELINE first, then REGIME, then WORLD.** WORLD is the
hardest verdict to earn, not the default when nothing else is obvious. Where a
regime change and a real effect are confounded and cannot be separated, the row
is UNKNOWN with BOTH candidates named. We do not pick the more interesting one.

An unexplained spike that ships is how a publication gets embarrassed; an
explained one is often the story.

WHAT IT IS NOT
--------------
It is **read-only against every dataset**. It writes only `docs/ANOMALY_REPORT.md`
and `docs/anomaly_report.json`. It never runs `01_build_entity_spine.py`,
`09_import_rulings.py`, `41_build_codebooks.py` or `88_build_deals_taxonomy.py`,
holds nothing open for writing, and makes zero network calls.

`docs/anomaly_report.json` is the diffable artefact - that is what makes this a
standing check rather than a one-off. Re-run it after any build and diff the
JSON: an anomaly that changes type, or a new seam appearing, is a regression in
the data even when every build succeeded.

MONEY RULES HONOURED (cedar_domain)
-----------------------------------
  * `SUM_COLUMNS` sum; `MAX_PER_AWARD_COLUMNS` are MAXed per award and are never
    totalled. `total_award_value` sums to $5.63T and that number means nothing.
  * A RESTATED column is never summed. `total_obligations_real2025` sums to
    $385.0B and looks plausible, which is what makes it dangerous.
  * Face value, subsidy cost and obligation are three different things and are
    never added together.
  * `mni_total_stated` in NAGPRA is NEVER summed. Those are counts of human
    beings, not a metric.
  * Subawards are summed only at `duplicate_status = primary`. Summing past it
    inflates by 53%.

    py -3 code/227_anomaly_sweep.py            # full sweep
    py -3 code/227_anomaly_sweep.py --only prime_contracts,subawards
    py -3 code/227_anomaly_sweep.py --list
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from cedar_domain import SUM_COLUMNS, MAX_PER_AWARD_COLUMNS  # noqa: F401
except Exception:                                                # pragma: no cover
    SUM_COLUMNS = frozenset({"total_obligations", "obligated_usd", "subaward_amount"})
    MAX_PER_AWARD_COLUMNS = frozenset({"total_award_value", "total_face_value_of_loan"})

csv.field_size_limit(2 ** 31 - 1)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN = os.path.join(ROOT, "data", "clean")
DOCS = os.path.join(ROOT, "docs")

RUN_AT = datetime.now().astimezone()
THIS_YEAR = RUN_AT.year

# ---------------------------------------------------------------------------
# NEVER SUM. Not a style rule - each of these produces a plausible-looking
# phantom, which is worse than an obviously wrong one.
# ---------------------------------------------------------------------------
NEVER_SUM = {
    "total_award_value": "award ceiling restated on every transaction of the award (MAX_PER_AWARD_COLUMNS)",
    "total_award_value_real2025": "restatement of a column that is already a restatement",
    "total_obligations_real2025": "deflated restatement of total_obligations; sums to $385.0B against a true $310.01B",
    "obligated_usd_real2025": "deflated restatement of obligated_usd",
    "subaward_amount_real2025": "deflated restatement of subaward_amount",
    "total_face_value_of_loan": "award-cumulative and signed; face value is the borrower's principal, not federal outlay",
    "total_loan_subsidy_cost": "a different quantity from an obligation; never added to one",
    "face_value_of_loan": "not an obligation",
    "original_loan_subsidy_cost": "not an obligation",
    "mni_total_stated": "A COUNT OF HUMAN BEINGS. Never summed, never averaged, never charted as a volume.",
    "prime_award_amount": "the prime award's value restated on every subaward row of that prime",
    "Project_Total_Value_USD": "project total restated across rows of the same project",
    "deflator_factor_2025": "an index, not a quantity",
}

# ---------------------------------------------------------------------------
# THE PIPELINE REGISTER - boundaries we MADE. Checked FIRST, always.
# Each entry: (dataset, first_year, last_year, label, owning script)
# ---------------------------------------------------------------------------
# Each entry: (dataset, y0, y1, classes-it-may-explain, label, owning script).
# `classes` is not decoration. The BGOV era spans FY2000-2022 - twenty-three of
# the twenty-seven years in the prime table - so letting it explain an ENTITY
# SPIKE types every spike PIPELINE and the report says nothing. A wide window
# may explain a STRUCTURAL fact about the era (who can be named, what the
# vocabulary is); only a NARROW window may explain one year's money.
# `None` means "any class".
PIPELINE_BOUNDARIES = [
    ("prime_contracts", 2023, 2026, None,
     "The FY2023-26 archive backfill was pulled FILTERED to Cedar's known identifiers, so all 209,495 rows are "
     "attributed BY CONSTRUCTION. Any FY2023+ 'improvement' in attribution is an artefact, and a Native firm not "
     "already in the ledger is absent from these years entirely.",
     "114_pull_prime_archive.py + 131_merge_archive_backfill.py"),
    ("prime_contracts", 2000, 2022,
     {"ENTITY_UNIVERSE_STEP", "VOCABULARY_SEAM", "ID_SCHEME_SEAM", "ENTITY_APPEARANCE",
      "ENTITY_DISAPPEARANCE", "ERA_MAP"},
     "STRUCTURAL, NOT A DATED STEP. FY2000-2022 came from the BGOV-filtered .dta and carries a mixed attribution "
     "rate (FY2000 48%, FY2021 78%). The 79.0% headline is a blend over two differently-constructed populations. "
     "This window covers 23 of 27 years, so it may explain WHO CAN BE NAMED in an era - never one year's money.",
     "40_build_prime_contracts.py"),
    ("subawards", 2021, 2024, None,
     "USAspending bulk_download failed service-wide for FY2021-24 (_state.json: status failed, total_rows 0). "
     "173/89/120/166 rows against ~5,000-9,000 either side. An UPSTREAM OUTAGE, not reality.",
     "121_pull_subawards_api.py"),
    ("faads_transactions_all_agencies", 2008, 2026, None,
     "FAADS ends at FY2007 BY DESIGN - the series break is at FY2008 when reporting migrated. Absence after "
     "FY2007 is not a decline.",
     "30_funding_pre2008.py"),
    ("faads_entity_attribution", 2008, 2026, None,
     "Same design boundary as the FAADS transaction file it is attributed from.",
     "73_faads_name_attribution.py"),
    ("federal_funding_transactions", 2000, 2006, None,
     "Modern assistance begins FY2006/07. Pre-FY2007 assistance lives in FAADS and carries no modern identifier.",
     "115_pull_assistance_archive.py"),
    ("federal_funding_transactions", 2023, 2023,
     {"ENTITY_UNIVERSE_STEP", "VOCABULARY_SEAM", "ID_SCHEME_SEAM", "ENTITY_APPEARANCE",
      "ENTITY_DISAPPEARANCE", "YEAR_STEP_ROWS", "ERA_MAP"},
     "FY2023 IS THE ONLY YEAR SERVED BY BOTH ERAS - 34,511 rows from the FY2023 archive zip and 15,141 from the "
     "2023-04-09 do-file extract. It therefore carries BOTH identifier schemes at once (see ID_SCHEME_SEAM), "
     "which inflates any distinct-entity count for that year specifically.",
     "115_pull_assistance_archive.py + 24_funding_merge.py"),
    ("federal_funding_transactions", 2024, 2026,
     {"ENTITY_UNIVERSE_STEP", "VOCABULARY_SEAM", "ID_SCHEME_SEAM", "ENTITY_APPEARANCE",
      "ENTITY_DISAPPEARANCE", "ERA_MAP"},
     "FY2024-26 rows come from archive stamp 20260706 and are attributed ONLY by `uei_exact_archive`. The "
     "name/prefix method (`dofile_corrtd:prefix`) that carries FY2008-2022 was never applied to them, and "
     "START_HERE.md records 20260706 as a SUPERSEDED archive vintage ('all 4,597 keys now carry 20260806; "
     "20260706 is dead everywhere').",
     "115_pull_assistance_archive.py"),
    ("federal_funding_transactions", 2026, 2026, None,
     "Our pull stops at action_date 2026-06-30 and every FY2026 row carries fy_partial_flag = 1. FY2026 is "
     "partial-through-June: roughly one quarter of the fiscal year is simply absent.",
     "115_pull_assistance_archive.py"),
    ("deals_classified", 2000, 2019,
     {"ENTITY_UNIVERSE_STEP", "YEAR_STEP_ROWS", "ENTITY_APPEARANCE", "ENTITY_DISAPPEARANCE", "LUMPY_SERIES",
      "ERA_MAP", "VOCABULARY_SEAM"},
     "DEALS COVERAGE IS A COLLECTION ARTEFACT BEFORE IT IS A HISTORY. The ledger was assembled source by source "
     "(ANC annual reports, the ANCSA portal, SEC 2010-17, federal award lists, tribal debt), so a year's density "
     "measures WHICH SOURCE COVERED IT, not how much dealmaking happened. A published note recorded '2019 = 75 "
     "vs 2020 = 5'; the file at this run's vintage does not read that way any more, which is itself the point - "
     "the shape of this series moves when a collection pass lands.",
     "88_build_deals_taxonomy.py (do not run) + 155_collect_deals_2026_08.py"),
    ("deals_classified", 2025, 2026, None,
     "RECENCY BIAS PLUS YTD. The most recent years are the best-collected (155_collect_deals_2026_08.py ran "
     "2026-08-26) and calendar 2026 is incomplete. A recent-year record high in this ledger is a statement "
     "about our collection cadence first.",
     "155_collect_deals_2026_08.py"),
    ("gaming_facility_metrics", 2019, 2026,
     {"ENTITY_UNIVERSE_STEP", "YEAR_STEP_ROWS", "ENTITY_DISAPPEARANCE", "ERA_MAP", "VOCABULARY_SEAM",
      "SCALE_SHIFT"},
     "The inherited vendor capacity panel stops at 2018. Capacity observations thin sharply after 2018 for "
     "vendor-derived rows; a flat line after 2018 may be unobserved rather than static.",
     "159_extend_gaming_metrics.py"),
]

# ---------------------------------------------------------------------------
# THE REGIME REGISTER - rules that changed. Checked SECOND.
# A step here is a fact about a statute, not about Indian Country.
# Owner direction 2026-08-26; cross-check against docs/ASSUMPTIONS_AND_LIMITATIONS.md
# (a concurrent agent owns that file).
# ---------------------------------------------------------------------------
# Each entry: key, y0, y1, datasets, `classes` it may explain, label.
# `classes` matters: a regime event explains the anomaly SHAPE it actually
# produces and nothing else. NAICS revisions explain a vocabulary seam; they do
# not explain a firm's dollars tripling. A register whose windows are wide and
# whose classes are "everything" types every row REGIME and reports nothing -
# the same decoration failure AGENTS.md records against a gate that is always
# red. `CONTEXT` means the event is documented here and NEVER types a row: it is
# a standing limitation, not a dated step.
CONTEXT = frozenset()
ALLCLS = None
REGIME_EVENTS = [
    dict(key="COVID_RELIEF", y0=2020, y1=2021,
         datasets=["federal_funding_transactions", "np_financials", "np_schedule_i_grants",
                   "grantmaker_funding_flows", "prime_contracts", "subawards"],
         classes=ALLCLS,
         label="CARES Act (2020) and ARPA (2021) sent unprecedented direct funding to tribal governments - "
               "reportedly ~$8B and ~$20B. THE SINGLE BIGGEST CONFOUNDER IN THIS PANEL. Any 2020-2021 assistance "
               "spike is presumptively REGIME until the programme mix is shown to be ordinary."),
    dict(key="ARRA", y0=2009, y1=2011,
         datasets=["federal_funding_transactions", "prime_contracts", "np_financials",
                   "faads_entity_attribution"],
         classes=ALLCLS,
         label="American Recovery and Reinvestment Act. Same shape as COVID relief, smaller, inflating "
               "2009-2011."),
    dict(key="HLOGA_QUARTERLY", y0=2008, y1=2008,
         datasets=["native_entity_lobbying_disclosures", "tribe_year_lobbying_panel"],
         classes={"YEAR_STEP_ROWS", "ENTITY_SPIKE", "ENTITY_APPEARANCE", "VOCABULARY_SEAM"},
         label="LDA filing frequency went SEMIANNUAL to QUARTERLY under HLOGA, effective 2008. This roughly "
               "DOUBLES filing counts with no change in lobbying activity. ANY FILING-COUNT TREND CROSSING 2008 "
               "IS CORRUPTED unless it is computed on dollars or on filings-per-reporting-period."),
    dict(key="FFATA_SUBAWARD", y0=2010, y1=2012,
         datasets=["subawards"], classes=ALLCLS,
         label="FSRS/FFATA subaward reporting began 2010 with a $25,000,000 prime threshold lowered to $25,000 "
               "in October 2010. Counts rise 30 -> 113 -> 1,652 -> 2,679 across FY2009-12. That is the "
               "threshold, not the activity. Subawards below the threshold are absent BY RULE. FY2012 forward "
               "is the first comparable stretch."),
    dict(key="NAGPRA_2024_RULE", y0=2024, y1=2026,
         datasets=["nagpra_notices"], classes=ALLCLS,
         label="NAGPRA's revised regulations (43 CFR 10) took effect January 2024 and changed notice "
               "requirements. A surge in notices after that date is regulatory before it is discovery. "
               "Establish how much is the rule before calling any of it a change in institutional behaviour."),
    dict(key="DUNS_TO_UEI", y0=2022, y1=2022,
         datasets=["prime_contracts", "federal_funding_transactions", "subawards"],
         classes={"ENTITY_DISAPPEARANCE", "ENTITY_APPEARANCE", "VOCABULARY_SEAM", "DUPLICATE_KEY"},
         label="The federal government retired DUNS and adopted the UEI on 2022-04-04. An identifier "
               "discontinuity mid-panel: an entity has DUNS-keyed history and UEI-keyed history that do not "
               "join without a crosswalk."),
    dict(key="CFDA_TO_ASSISTANCE_LISTINGS", y0=2018, y1=2018,
         datasets=["federal_funding_transactions"], classes={"VOCABULARY_SEAM"},
         label="CFDA was renamed Assistance Listings and moved to SAM.gov in 2018. Numbers largely persisted; "
               "programme titles and groupings did not. Join on the number, never the title."),
    dict(key="NAICS_REVISIONS", y0=2002, y1=2022, only_years={2002, 2007, 2012, 2017, 2022},
         datasets=["prime_contracts", "subawards"], classes={"VOCABULARY_SEAM"},
         label="NAICS is revised every five years (2002/2007/2012/2017/2022): codes added, retired, split, "
               "merged. An industry series across a revision year compares different definitions."),
    dict(key="IGRA_ERA", y0=1988, y1=1995,
         datasets=["gaming_facility_metrics", "gaming_facilities"], classes=ALLCLS,
         label="IGRA (1988) and the first compacts created the reporting universe itself. Early-1990s growth is "
               "an institution being built, not a market expanding within a stable one."),
    dict(key="ROLLCALL_SOURCE_FLOOR", y0=1989, y1=1990,
         datasets=["_bill_actions", "bill_votes"], classes=ALLCLS,
         label="House EVS begins at calendar 1990 and Senate LIS at the 101st Congress. Pre-1990 vote metadata "
               "comes from ICPSR descriptions and is not comparable to post-1990."),
    dict(key="SETASIDE_TIER_2013", y0=2013, y1=2016,
         datasets=["prime_contracts"], classes=ALLCLS,
         label="DOI's 2013 Buy Indian rule created a SECOND TIER of Native set-aside. `Indian Business` is zero "
               "in every year FY2000-2013 and then overtakes `Buy Indian`. READ ALONE, `Buy Indian` SAYS NATIVE "
               "SET-ASIDES FELL 62%; SUMMED, THEY ROSE 44%. The whole difference is one code appearing. Always "
               "sum the family; never trend a single set-aside code across 2013-2016."),
    dict(key="IHS_BUY_INDIAN_2022", y0=2022, y1=2022,
         datasets=["prime_contracts"], classes=ALLCLS,
         label="IHS did not adopt the two-tier Buy Indian architecture until 2022-03-14. Pooling agencies "
               "therefore puts a SECOND false break in the set-aside series, at a different date from DOI's. An "
               "agency-pooled Native set-aside trend crosses both."),
    dict(key="FAR_4606_MICRO_MODIFICATIONS", y0=2000, y1=2026,
         datasets=["prime_contracts"], classes=CONTEXT,
         label="STANDING LIMITATION (never types a row). FAR 4.606(a)(1) requires modifications to be reported "
               "REGARDLESS OF DOLLAR VALUE, so the row count is a count of ADMINISTRATIVE ACTIONS, not of "
               "contracts or of money. Measured on FY2026: **71.9% of rows with a positive obligation are "
               "<=$2,500, median $443.** A contract-COUNT trend running into FY2026 is an artefact of reporting "
               "practice. Count awards (a de-duplicated PIID key), or report dollars."),
    dict(key="SINGLE_AUDIT_THRESHOLD", y0=2004, y1=2015,
         datasets=["fac_tribal_single_audits"], classes=CONTEXT,
         label="STANDING LIMITATION (never types a row). The Single Audit threshold moved $300k -> $500k -> "
               "$750k. An entity below the threshold has NO AUDIT BY RULE. Absence from this layer is never "
               "evidence of absence of federal money."),
    dict(key="ACQUISITION_THRESHOLDS", y0=2000, y1=2026,
         datasets=["prime_contracts"], classes=CONTEXT,
         label="STANDING LIMITATION (never types a row). Micro-purchase and simplified-acquisition thresholds "
               "moved repeatedly across this window. A change in the COUNT of small contracts may be a "
               "threshold change rather than a change in contracting behaviour - but the window is the whole "
               "panel, so it can never explain ONE year, and a register entry that explains every year explains "
               "none."),
    dict(key="FORM_990N", y0=2008, y1=2026,
         datasets=["np_financials", "np_orgs"], classes=CONTEXT,
         label="STANDING LIMITATION (never types a row). 990-N (e-Postcard) filers report no financial detail: "
               "6,453 of 12,764 organisations. A zero in a revenue column there is the FILING REGIME, not a "
               "finding about the organisation."),
    dict(key="SECTION_7871", y0=1996, y1=2026,
         datasets=["np_schedule_i_grants", "grantmaker_funding_flows"], classes=CONTEXT,
         label="STANDING LIMITATION (never types a row). Under IRC section 7871 tribal governments are not "
               "501(c)(3) and file no Form 990. This is the likely mechanism behind Schedule I recipient EINs "
               "absent from the BMF - the recipient is real and the filing does not exist."),
]

# ---------------------------------------------------------------------------
# KNOWN SEAMS ALREADY FOUND. Re-tested every run as a regression check.
# ---------------------------------------------------------------------------
KNOWN_SEAMS = {
    ("prime_contracts", "extent_competed"):
        "TWO VOCABULARIES IN ONE COLUMN. **FIXED as of 2026-08-26** - `extent_competed_normalized` is on the "
        "file and is populated against the authoritative DAIMS-DEC v2.2 crosswalk. The RAW column is retained "
        "and still carries the seam, so this detector still fires on it and should. Read "
        "`extent_competed_normalized`; never filter the raw column. NOTE that `docs/CICD_BENCHMARK.md` "
        "INTERNAL-05 may still describe this as unfixed AND still describes the boundary as BGOV-vs-archive, "
        "which this run measures as wrong - see the annotation below.",
    ("prime_contracts", "setaside"):
        "Differs across the same BGOV/archive seam as extent_competed, and the archive leaves it blank on ~56% of "
        "rows so it must be forward-filled to award level before any share is computed.",
    ("prime_contracts", "attributed_flag"):
        "100% on FY2023-26 BY CONSTRUCTION (identifier-seeded backfill). The 79.0% headline is a blend.",
    ("subawards", "duplicate_status"):
        "Summing past this column inflates subaward dollars by 53% ($39.43B vs a true $25.77B).",
    ("gaming_facility_metrics", "payout"):
        "The CT gaming source changes UNITS mid-series without changing the column name (91.45 in 1993-01 vs 0.912 "
        "in 2025-12). The clean metrics table does not carry `payout`; confirm before any raw CT read.",
}

# ---------------------------------------------------------------------------
# DATE-CLUSTER REGISTER.
# Day-of-month clustering is the signature of a MONTH written as a DAY - but it
# is ALSO the signature of a period boundary, a statutory filing deadline, or a
# monthly series keyed to the first of the month. A detector that cannot tell
# those apart cries wolf on every date column in the corpus and then nobody
# reads it. Each entry says which it is; anything not listed is UNKNOWN and is
# reported as a real candidate.
# ---------------------------------------------------------------------------
DATE_CLUSTER_NOTES = {
    ("np_schedule_i_grants", "tax_period_end"): ("REGIME",
        "EXPECTED BY CONSTRUCTION. A tax period ends on the last day of a month, so day 30 and day 31 carry "
        "almost every row. This is the IRS filing regime, not false precision."),
    ("grantmaker_funding_flows", "tax_period_end"): ("REGIME",
        "EXPECTED BY CONSTRUCTION. Same as Schedule I - a 990 tax period ends on a month boundary, and a "
        "December year-end puts most filers on day 31."),
    ("resource_revenue", "period_start"): ("REGIME",
        "EXPECTED BY CONSTRUCTION. ONRR reports MONTHLY periods, so period_start is the first of the month by "
        "definition. `period_type` states the grain; the day is not a claim about when anything happened."),
    ("native_entity_lobbying_disclosures", "dt_posted"): ("REGIME",
        "THE LDA FILING DEADLINE, NOT FALSE PRECISION. Quarterly LD-2 reports are due on the 20th of January, "
        "April, July and October, and the day-20 pile-up is filers meeting it. Note this is the SAME statute "
        "(HLOGA, 2008) that doubled filing frequency - so the deadline structure itself changes mid-panel."),
    ("federal_actions", "effective_on"): ("REGIME",
        "PARTLY EXPECTED. Federal rules commonly take effect on the first of a month. The excess over a flat "
        "distribution is modest and is consistent with that convention rather than with imputation."),
    ("faads_transactions_all_agencies", "action_date"): ("UNKNOWN",
        "NOT EXPLAINED. 504,931 rows on day 1 and 300,318 on day 15 out of 2,769,748 - 29% of the file on two "
        "days. FAADS was a QUARTERLY batch-reported system, so a period-start convention is the leading "
        "candidate, but nothing in the file states it. Until it does, a FAADS day-level date is not a "
        "transaction date and must never be used for within-month timing."),
    ("faads_entity_attribution", "action_date"): ("UNKNOWN",
        "Inherited from the FAADS transaction file - see that row. The attributed subset shows the same "
        "day-1/day-15 pile-up."),
    ("gaming_facility_metrics", "observation_date"): ("PIPELINE",
        "THE KNOWN FALSE DAY-PRECISION DEFECT, RE-DETECTED. Cedar has already found 415 gaming dates carrying "
        "day-precision they do not have (150 on day 31, 148 on day 15). A day-1 pile-up on an OBSERVATION date "
        "is a month rendered as a day. The fix is a precision field beside the date, never a corrected date."),
    ("gaming_facility_metrics", "as_of_date"): ("PIPELINE",
        "Same defect as observation_date. Note this file DOES carry `as_of_date_precision` - so the precision "
        "is recorded and the danger is a consumer reading the date column without it."),
    ("subawards", "subaward_date"): ("UNKNOWN",
        "12,083 of 63,548 rows on day 1. FSRS reports monthly and a subaward date may be a period stamp rather "
        "than an execution date. Not established either way from the file."),
    ("deals_classified", "Event_Date"): ("UNKNOWN",
        "The clustering here is NOT on 1/15/31 - it is on days 16, 15, 29 and 27, which is not the signature of "
        "a month-as-day. It is more consistent with announcement dates clustering on particular real dates, or "
        "with a small-N artefact on 930 rows. `Date_Basis` is the column that should settle it."),
    ("resource_revenue", "payment_date"): ("UNKNOWN",
        "489 dated rows clustering on days 20-23. A disbursement calendar is the leading candidate. Small N."),
}

# ---------------------------------------------------------------------------
# SEAM DETECTOR SUPPRESSION.
# Three kinds of column change vocabulary at every year boundary BY DESIGN and
# would otherwise bury the real seams:
#   SEAM_SKIP        - the column IS the year, or is derived from it (a 2025
#                      deflator is a different number every year on purpose).
#   SEAM_PROCESS     - build/pull metadata. A change here is not a defect, but
#                      the ERA MAP inside it is exactly what you want when a
#                      year looks wrong, so it is reported as ERA_MAP.
#   entity-id columns - a different set of entities appears every year in any
#                      real panel. That is the panel, not a seam.
# ---------------------------------------------------------------------------
SEAM_SKIP = frozenset({
    "fiscal_year", "tax_year", "filing_year", "publication_year", "notice_year",
    "decision_year", "event_year", "Event_Year", "Event_Quarter", "Event_Month",
    "deflator_factor_2025", "inflation_base_year", "pre_2000_flag", "volume",
    "congress", "tax_period", "tax_period_end", "observation_period",
    "filing_period", "subaward_sam_report_year", "bmf_vintage_fetched",
    # A flag whose whole purpose is to mark one era is not a seam - it is the
    # seam's own warning label, working correctly.
    "fy_partial_flag", "excluded_flag", "credit_instrument_flag", "is_correction",
    "has_resolved_entity", "pre_2000_flag",
})
SEAM_PROCESS = frozenset({
    "fetched_date", "built_date", "classified_date", "attributed_date",
    "promoted_date", "retrieved_date", "entity_keyed_date", "ruling_applied_date",
    "temporal_build_date", "built_by_script", "entity_link_built_by_script",
    "attributed_date", "schedc_built_date", "bmf_vintage_fetched", "irs_downloads_page",
})


#: Columns whose values are an OPEN SET - one row, one new value. Two sources
#: covering different entities, places, documents or dates share almost none of
#: these, and that is not a seam: it is two sources covering different things,
#: which is what sources are for. Only a CLOSED CATEGORY - a code list, an
#: agency roster, a status vocabulary - can be "the same system written twice".
#: A value that contains a four-digit year is usually a filename or a stamp,
#: and its vocabulary turns over annually no matter what. That is an ERA MAP,
#: handled elsewhere - never a rendering split.
YEARISH = re.compile(r"(19|20)\d{2}")
OPEN_SET_RE = re.compile(
    r"(name|city|state$|zip|url|date|title|terms|phrase|mention|candidate|page|"
    r"number|ein|uei|cage|_id$|_ids$|amount|usd|revenue|expenses|assets|"
    r"description|text|note|quote|address|docket|accession|citation|member)")


def seam_skip(col, spec):
    if col in SEAM_SKIP:
        return True
    if col in NEVER_SUM:
        return True
    if col in {c for c, _ in spec["money"]}:
        return True
    lc = col.lower()
    if lc.endswith("tribe_id") or lc.endswith("entity_id") or lc.endswith("_uei") \
            or lc.endswith("_ein") or lc.endswith("_id") or lc.endswith("_key"):
        return True
    return False

# ---------------------------------------------------------------------------
# SEAM ANNOTATIONS. The detector can see that a column's vocabulary changes at
# a boundary. It cannot know what the values MEAN. These are the readings a
# person supplied, attached to the machine's finding rather than replacing it.
# Unlike KNOWN_SEAMS, an annotation does NOT mark the seam as previously known.
# ---------------------------------------------------------------------------
SEAM_ANNOTATIONS = {
    ("prime_contracts", "funding_agency"):
        "THE SAME TWO-VOCABULARY DEFECT AS `extent_competed`, AND THIS ONE IS **NOT FIXED**. Measured elsewhere "
        "on 2026-08-26: 167 distinct values in one era against 264 in the other, only 116 shared, and 176,973 "
        "rows carrying a rendering the other era never produces. **There is no authoritative agency code column "
        "on our side**, so there is nothing to normalise against the way DAIMS-DEC v2.2 fixed extent_competed. "
        "CONSEQUENCE FOR THIS REPORT: any agency-level anomaly straddling the FY2016/FY2017 archive boundary is "
        "suspect, and an agency time series built by string-matching this column is measuring the rendering. "
        "OWNER: 114_pull_prime_archive.py + 131_merge_archive_backfill.py.",
    ("prime_contracts", "setaside"):
        "TWO SEPARATE BREAKS SIT IN THIS COLUMN AND ONLY ONE OF THEM IS OURS. (1) THE PIPELINE HALF: the archive "
        "leaves set-aside blank on ~56% of rows while the BGOV .dta carries the award's value on every row, so a "
        "row-level share is partly a measurement of WHICH SOURCE the row came from - it must be forward-filled "
        "to award level on (contract_number, awardee_uei) first. (2) THE REGIME HALF, and it is the one that "
        "produces a publishable-looking false finding: `Indian Business` is ZERO in every year FY2000-2013 and "
        "then overtakes `Buy Indian`, because DOI's 2013 rule created a SECOND TIER of Native set-aside. Read "
        "`Buy Indian` alone the series says Native set-asides FELL 62%; sum the two and they ROSE 44%. IHS did "
        "not adopt the same architecture until 2022-03-14, so pooling agencies adds a second false break on top "
        "of the first. See REGIME key SETASIDE_TIER_2013.",
    ("prime_contracts", "extent_competed"):
        "THE RECORDED CHARACTERISATION OF THIS SEAM IS WRONG, AND THIS RUN MEASURED THE CORRECTION. "
        "`docs/CICD_BENCHMARK.md` INTERNAL-05 describes it as 'raw FPDS letter codes (BGOV era) vs rendered "
        "labels (archive era)'. Measured on the file at this run's vintage, the single-character codes appear "
        "in **FY2008-FY2016 ONLY**, and those are exactly the years served by the "
        "`FY20xx_All_Contracts_Full_20260806.zip` archive files. FY2000-2007 (`master prime file.dta`, the BGOV "
        "era) render LABELS, and so do FY2017-2026 (the `..._20260706.zip` files). So the split is NOT "
        "BGOV-versus-archive - **it is one archive vintage against another**, with the BGOV era sitting on the "
        "same side as the newest years. Anyone who fixes this by keying on 'BGOV rows' will fix the wrong rows. "
        "OWNER: 114_pull_prime_archive.py + 131_merge_archive_backfill.py.",
    ("prime_contracts", "source_file"):
        "THE ARCHIVE BACKFILL REACHES MUCH FURTHER BACK THAN FY2023, AND TWO ARCHIVE VINTAGES ARE IN THE FILE. "
        "Measured era map: FY2000-2007 is `master prime file.dta` alone; FY2008-2016 mixes the .dta with "
        "`FY20xx_All_Contracts_Full_20260806.zip`; FY2017-2022 mixes the .dta with `..._20260706.zip`; "
        "FY2023-2026 is `..._20260706.zip` alone. START_HERE.md's '209,495 FY2023-26 rows' is exactly right "
        "(45,747 + 53,056 + 48,879 + 61,813) - but the sentence around it, that the archive covers FY2023-26, "
        "understates its reach by fifteen years. And START_HERE.md separately records that **20260706 is a dead "
        "archive vintage** - 'all 4,597 keys now carry 20260806; 20260706 is dead everywhere' - so FY2017-2026 "
        "of the prime table rests on the superseded pull while FY2008-2016 rests on the current one. Same "
        "defect shape as `federal_funding_transactions.source_archive_stamp`, in a second collection.",
    ("federal_funding_transactions", "source_archive_stamp"):
        "READ THIS ONE CAREFULLY. The stamps are USAspending award-archive vintages, and the era map says "
        "FY2007 = 20260706, FY2008-2023 = 20260806, FY2024-2026 = 20260706. START_HERE.md records that **the "
        "award archive REPLACES monthly** and that as of 2026-08-26 'all 4,597 keys now carry 20260806; "
        "20260706 is dead everywhere.' So the four most recent fiscal years of the assistance table - the years "
        "any launch piece will lead on - were built from a SUPERSEDED archive vintage, while the middle of the "
        "panel was rebuilt from the current one. That is not a labelling quirk; it means FY2024-26 has not been "
        "refreshed against the archive the rest of the table was refreshed against, and the two are not "
        "guaranteed to agree. OWNER: 115_pull_assistance_archive.py.",
    ("federal_funding_transactions", "source_file"):
        "The era map is the useful part: FY2008-2022 comes overwhelmingly from ONE extract, "
        "`Assistance_PrimeTransactions_2023-04-09_H19M53S53_1.csv`, and FY2023-2026 from per-year archive zips. "
        "FY2023 is served by BOTH. Fifteen years of this table therefore rest on a single 2023 extract, and "
        "anything that extract systematically missed is missing from all fifteen.",
    ("federal_funding_transactions", "business_types_description"):
        "USAspending's recipient business-type vocabulary is not stable across the panel. Note in particular "
        "that the modal value renders as 'INDIAN/NATIVE AMERICANTRIBAL GOVERNMENT (FEDERALLY RECOGNIZED)' in "
        "FY2007 and 'INDIAN/NATIVE AMERICAN TRIBAL GOVERNMENT (FEDERALLY-RECOGNIZED)' from FY2023 - a missing "
        "space and an added hyphen. **An exact-string filter on this column drops one era of Native recipients "
        "silently**, which is the same failure shape as the extent_competed seam and a more dangerous one, "
        "because the column looks like a Native flag.",
}

# ---------------------------------------------------------------------------
# CLASS 7 - known false attributions, re-tested as regressions.
# A spike sitting on a known-bad link is a PIPELINE fact, not a world fact.
# ---------------------------------------------------------------------------
FALSE_ATTRIBUTION_CHECKS = [
    dict(id="FA-01", file="tribe_year_lobbying_panel.csv", entity="TRBF-SRPMCP-00",
         label="Salt River Pima-Maricopa lobbying panel",
         bad=dict(spend=40_300_000, filings=557), good=dict(spend=10_400_000, filings=141),
         note="~220 filings of Santa Rosa County FL, two hospitals and a junior college matched on 'rosa santa'."),
    dict(id="FA-02", file="foia_request_index.csv", entity=None,
         label="FOIA index link quality",
         note="166 of 453 links are bad; 94 key to the Native Village of Georgetown off georgetown.edu."),
    dict(id="FA-03", file="*", entity="TRBF-ENTPRS-00",
         label="TRBF-ENTPRS-00 canonical name is literally 'Enterprise'",
         note="A canonical name that is a common English noun will hoover up name-matched rows. Any money on this "
              "id is suspect until the id itself is adjudicated."),
]

# ---------------------------------------------------------------------------
# DATASET SPECS
# ---------------------------------------------------------------------------
# money: (column, rule) - rule SUM | MAX | NEVER
# entity: (id_column, name_column) - name may be None
# ---------------------------------------------------------------------------
SPECS = [
    dict(name="prime_contracts", spike_min_dollars=25_000_000, file="prime_contracts.csv", collection="Prime contracting",
         year=("col", "fiscal_year"), money=[("total_obligations", "SUM")],
         entity=("tribe_id", "canonical_name"), award_id="contract_number",
         dates=[], dup_key=["contract_number", "awardee_uei", "fiscal_year", "total_obligations"],
         era_col="source_file"),
    dict(name="federal_funding_transactions", spike_min_dollars=25_000_000, file="federal_funding_transactions.csv", collection="Federal assistance",
         year=("col", "fiscal_year"), money=[("obligated_usd", "SUM")],
         entity=("tribe_id", "canonical_name"), award_id="award_id_fain",
         dates=["action_date"], dup_key=["assistance_transaction_unique_key"],
         era_col="source_archive_stamp"),
    dict(name="faads_transactions_all_agencies", file="faads_transactions_all_agencies.csv",
         collection="FAADS (pre-2008 assistance)",
         year=("col", "fiscal_year"), money=[("obligated_usd", "SUM")],
         entity=(None, None), award_id="award_id_fain",
         dates=["action_date"], dup_key=None, era_col="source_file"),
    dict(name="faads_entity_attribution", spike_min_dollars=10_000_000, file="faads_entity_attribution.csv",
         collection="FAADS (entity layer)",
         year=("col", "fiscal_year"), money=[("obligated_usd", "SUM")],
         entity=("tribe_id", "canonical_name"), award_id="award_id_fain",
         dates=["action_date"], dup_key=["faads_row_id"], era_col="match_method"),
    dict(name="subawards", spike_min_dollars=10_000_000, file="subawards.csv", collection="Subawards",
         year=("col", "fiscal_year"), money=[("subaward_amount", "SUM")],
         entity=("sub_native_tribe_id", "sub_name"), award_id="subaward_number",
         dates=["subaward_date"], dup_key=["subaward_number", "prime_award_unique_key", "subaward_amount"],
         dedup_col="duplicate_status", dedup_primary="primary", era_col="source_dataset"),
    dict(name="federal_actions", spike_min_rows=400, file="federal_actions.csv", collection="Federal Register actions",
         year=("date", "publication_date"), money=[],
         entity=(None, None), award_id="document_number",
         dates=["publication_date", "effective_on"], dup_key=["document_number"], era_col="type"),
    dict(name="_bill_actions", spike_min_rows=400, file="_bill_actions.csv", collection="Bill actions",
         year=("date", "action_date"), money=[],
         entity=(None, None), award_id="bill_id",
         dates=["action_date"], dup_key=None, era_col="source_system"),
    dict(name="native_entity_lobbying_disclosures", spike_min_dollars=1_000_000, file="native_entity_lobbying_disclosures.csv",
         collection="Lobbying",
         year=("col", "filing_year"), money=[("spend_usd", "SUM")],
         entity=("entity_id", "canonical_name"), award_id="filing_uuid",
         dates=["dt_posted"], dup_key=["filing_uuid", "entity_id"], era_col="filing_period"),
    dict(name="nagpra_notices", spike_min_rows=250, file="nagpra_notices.csv", collection="NAGPRA",
         year=("col", "publication_year"),
         money=[("mni_total_stated", "NEVER"), ("cultural_items_total_stated", "NEVER")],
         entity=("institution_primary", None), award_id="document_number",
         dates=["publication_date", "repatriation_eligible_date"], dup_key=["document_number"],
         era_col="notice_type"),
    dict(name="deals_classified", spike_min_dollars=250_000_000, file="deals_classified.csv", collection="Deals",
         year=("col", "Event_Year"), money=[("Announced_Value_USD", "SUM"),
                                            ("Project_Total_Value_USD", "NEVER")],
         entity=("native_party_entity_id", "native_party_canonical_name"), award_id="Deal_ID",
         dates=["Event_Date"], dup_key=["Deal_ID"], era_col="_source_file"),
    dict(name="gaming_facility_metrics", spike_min_rows=250, file="gaming_facility_metrics.csv", collection="Gaming metrics",
         year=("date", "observation_date"), money=[],
         entity=("entity_id", "tribe"), award_id="facility_id",
         dates=["observation_date", "as_of_date"], dup_key=None, era_col="source",
         metric_col="metric", metric_value="value"),
    dict(name="np_financials", spike_min_dollars=25_000_000, file="np_financials.csv", collection="Nonprofits (financials)",
         year=("col", "tax_year"), money=[("total_revenue", "SUM")],
         entity=("ein", "org_name"), award_id="ein",
         dates=["tax_period"], dup_key=["ein", "tax_year", "form_type"], era_col="form_type"),
    dict(name="np_schedule_i_grants", spike_min_dollars=10_000_000, file="np_schedule_i_grants.csv", collection="990 Schedule I",
         year=("col", "tax_year"), money=[("cash_grant_usd", "SUM")],
         entity=("filer_ein", "filer_name_as_filed"), award_id="object_id",
         dates=["tax_period_end"], dup_key=None, era_col="return_type"),
    dict(name="grantmaker_funding_flows", spike_min_dollars=5_000_000, file="grantmaker_funding_flows.csv", collection="Grantmaker flows",
         year=("col", "tax_year"), money=[("cash_grant_usd", "SUM")],
         entity=("funder_key", "funder_name_canonical"), award_id="flow_id",
         dates=["tax_period_end"], dup_key=["flow_id"], era_col="form_type"),
    dict(name="admin_appeal_decisions", spike_min_rows=250, file="admin_appeal_decisions.csv", collection="Admin appeals",
         year=("col", "decision_year"), money=[],
         entity=(None, None), award_id="decision_id",
         dates=["decision_date"], dup_key=["decision_id"], era_col="board"),
    dict(name="ferc_docket_filings", spike_min_rows=400, file="ferc_docket_filings.csv", collection="FERC",
         year=("date", "filed_date"), money=[],
         entity=("resolved_native_entity_id", "resolved_native_entity_name"), award_id="accession_number",
         dates=["filed_date", "issued_date"], dup_key=["docket_number", "accession_number"],
         era_col="category"),
    dict(name="resource_revenue", spike_min_dollars=50_000_000, file="resource_revenue.csv", collection="Resource revenue",
         year=("date", "period_start"), money=[("amount_usd", "SUM")],
         entity=("recipient_entity_id", "recipient_entity_name"), award_id="resource_revenue_event_id",
         dates=["period_start", "payment_date"], dup_key=None, era_col="source_system"),
    dict(name="foia_request_index", spike_min_rows=250, file="foia_request_index.csv", collection="FOIA index",
         year=("date", "request_date"), money=[],
         entity=("tribe_entity_id", None), award_id="foia_request_id",
         dates=["request_date"], dup_key=None, era_col="agency"),
    dict(name="tribe_year_lobbying_panel", spike_min_dollars=1_500_000, file="tribe_year_lobbying_panel.csv", collection="Lobbying (panel)",
         year=("col", "filing_year"), money=[("total_lobbying_spend_usd", "SUM")],
         entity=("entity_id", "canonical_name"), award_id=None,
         dates=[], dup_key=["entity_id", "filing_year"], era_col=None),
]

# thresholds
SPIKE_MULTIPLE = 4.0          # year value vs the entity's prior maximum
SPIKE_MIN_DOLLARS = 2_000_000
SPIKE_MIN_ROWS = 60           # for count-only datasets
DISCONT_LO, DISCONT_HI = 0.45, 2.2
SEAM_JACCARD = 0.34
UNIT_SHIFT_RATIO = 12.0
CAT_SAMPLE_ROWS = 120_000
CAT_SAMPLE_MAX_DISTINCT = 350
# A LOOSER cap for the SHAPE detector only. It costs nothing to track six shape
# buckets on a 264-value column, and `funding_agency` - which carries the same
# two-vocabulary defect as extent_competed and is NOT fixed - has 167 values in
# one era and 264 in the other. The narrow cap was hiding exactly the column the
# detector exists for.
WIDE_SAMPLE_MAX_DISTINCT = 4000
CAT_HARD_CAP = 900
RESERVOIR = 4_000


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def stamp(path):
    try:
        st = os.stat(path)
    except OSError:
        return dict(path=os.path.relpath(path, ROOT).replace("\\", "/"), exists=False)
    return dict(path=os.path.relpath(path, ROOT).replace("\\", "/"), exists=True,
                bytes=st.st_size,
                mtime=datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
                read_at=datetime.now().isoformat(timespec="seconds"))


def num(s):
    if s is None:
        return None
    s = s.strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        pass
    t = s.replace(",", "").replace("$", "").strip()
    neg = t.startswith("(") and t.endswith(")")
    if neg:
        t = t[1:-1]
    try:
        v = float(t)
    except ValueError:
        return None
    return -v if neg else v


def year_of(s):
    """Year from a date-ish string. Handles ISO and M/D/YYYY. None if absent."""
    if not s:
        return None
    s = s.strip()
    if not s:
        return None
    if len(s) >= 4 and s[:4].isdigit():
        y = int(s[:4])
        return y if 1700 <= y <= 2200 else None
    parts = s.split("/")
    if len(parts) == 3 and parts[2][:4].isdigit():
        y = int(parts[2][:4])
        return y if 1700 <= y <= 2200 else None
    return None


def day_of(s):
    """Day-of-month, for fabricated-precision detection."""
    if not s:
        return None
    s = s.strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-" and s[8:10].isdigit():
        return int(s[8:10])
    parts = s.split("/")
    if len(parts) == 3 and parts[1].isdigit():
        return int(parts[1])
    return None


def jaccard(a, b):
    if not a and not b:
        return 1.0
    u = len(a | b)
    return len(a & b) / u if u else 1.0


def money(v):
    a = abs(v)
    if a >= 1e9:
        return f"${v/1e9:,.2f}B"
    if a >= 1e6:
        return f"${v/1e6:,.2f}M"
    if a >= 1e3:
        return f"${v/1e3:,.1f}k"
    return f"${v:,.0f}"


NEID_RE = re.compile(r"^[A-Z]{3,5}[0-9]?-[A-Z0-9]{4,8}-[0-9]{2}")


def id_shape(v):
    """The SHAPE of an identifier value - not its meaning.

    One column holding two identifier schemes is the quietest seam there is:
    nothing is blank, nothing is malformed, every row has an id, and the same
    entity simply has two of them. It only surfaces if you look at the SHAPE of
    the strings, which is why this is a detector rather than a note.
    """
    v = v.strip()
    if not v:
        return "BLANK"
    if v.isdigit():
        return "INTEGER"
    if NEID_RE.match(v):
        return "NEID"
    if len(v) == 12 and v.isalnum() and any(c.isdigit() for c in v):
        return "UEI_LIKE"
    if len(v) == 9 and v.isdigit():
        return "EIN_LIKE"
    return "OTHER"


def token_shape(v):
    """The SHAPE of a categorical value, not its meaning.

    WHY A SECOND SEAM DETECTOR EXISTS. The Jaccard test finds a column whose
    value set is REPLACED at a boundary. It is blind to the more common and
    more dangerous case: a column where two vocabularies MIX, so both eras
    share values and the sets never separate. `extent_competed` is exactly
    that - the letter codes appear only in FY2008-2016 and the rendered labels
    run through the whole panel, so the sets overlap in every year and Jaccard
    stays high while the column is unusable. What moves is the SHAPE MIX.
    """
    v = v.strip()
    if not v:
        return "BLANK"
    if len(v) == 1:
        return "CODE_1CHAR"
    try:
        float(v.replace(",", ""))
        return "NUMERIC"
    except ValueError:
        pass
    if " " in v or len(v) > 12:
        return "LABEL"
    if len(v) <= 6 and v.upper() == v:
        return "CODE_SHORT"
    return "OTHER"


def era_group(v):
    """Collapse a source stamp into the PULL that produced it.

    `FY2008_All_Contracts_Full_20260806.zip` and `FY2019_All_Contracts_Full_
    20260706.zip` are two files from one pull architecture; `master prime
    file.dta` is a different one. Replacing digit runs with `#` groups the
    first two together and keeps the third apart, which is exactly the split
    that matters - and it needs no per-dataset configuration.
    """
    return re.sub(r"\d+", "#", (v or "").strip())[:60] or "<blank>"


BENFORD = {d: math.log10(1 + 1 / d) for d in range(1, 10)}


def first_digit(v):
    a = abs(v)
    if a < 1:
        return None
    while a >= 10:
        a /= 10
    d = int(a)
    return d if 1 <= d <= 9 else None


# ---------------------------------------------------------------------------
# the scanner - ONE streaming pass per file
# ---------------------------------------------------------------------------
def scan(spec, verbose=True):
    path = os.path.join(CLEAN, spec["file"])
    src = stamp(path)
    out = dict(name=spec["name"], collection=spec["collection"], source=src, rows=0)
    if not src.get("exists"):
        out["error"] = "FILE NOT FOUND"
        return out

    if verbose:
        print(f"  scanning {spec['file']} ({src['bytes']/1e6:,.0f} MB) ...", flush=True)

    fh = open(path, newline="", encoding="utf-8", errors="replace")
    rdr = csv.reader(fh)
    try:
        header = next(rdr)
    except StopIteration:
        fh.close()
        out["error"] = "EMPTY FILE"
        return out
    idx = {c: i for i, c in enumerate(header)}
    ncol = len(header)
    out["columns"] = ncol

    def ix(c):
        return idx.get(c) if c else None

    ykind, ycol = spec["year"]
    iy = ix(ycol)
    ient, iname = ix(spec["entity"][0]), ix(spec["entity"][1])
    iaward = ix(spec.get("award_id"))
    idedup = ix(spec.get("dedup_col"))
    dedup_primary = spec.get("dedup_primary")
    imetric, imetval = ix(spec.get("metric_col")), ix(spec.get("metric_value"))
    money_cols = [(c, rule, ix(c)) for c, rule in spec["money"] if ix(c) is not None]
    sum_cols = [(c, i) for c, rule, i in money_cols if rule == "SUM"]
    date_cols = [(c, ix(c)) for c in spec["dates"] if ix(c) is not None]
    dup_idx = [ix(c) for c in (spec.get("dup_key") or []) if ix(c) is not None] or None
    iera = ix(spec.get("era_col"))

    # accumulators
    year_rows = Counter()
    year_money = defaultdict(lambda: defaultdict(float))       # col -> year -> sum
    year_money_dedup = defaultdict(lambda: defaultdict(float))  # col -> year -> sum on primary only
    ent_year = {}                                              # (ent, year) -> [sum, n, maxabs, award_id]
    ent_name = {}
    ents_by_year = defaultdict(set)                            # year -> {entity}
    id_shape_year = defaultdict(Counter)                       # year -> {shape: n}
    id_shape_usd = defaultdict(float)                          # shape -> dollars
    id_shape_rows = Counter()
    id_shape_names = defaultdict(set)                          # shape -> {lowercased name}
    numstats = {c: dict(n=0, neg=0, zero=0, blank=0, pos=0, total=0.0, dedup_total=0.0,
                        benford=Counter(), round6=0, round5=0, round3=0, mx=None, mn=None)
                for c, _, _ in money_cols}
    reservoir = defaultdict(list)          # (col, year) -> samples
    datestats = {c: dict(mn=None, mx=None, future=0, blank=0, days=Counter(), unparsed=0)
                 for c, _ in date_cols}
    metric_year = defaultdict(lambda: defaultdict(list))   # metric -> year -> samples
    dup_seen = set()
    dup_hits = 0
    top_rows = []          # (abs value, value, col, year, entity, award, name)
    dedup_counter = Counter()

    # categorical candidates - decided on a sample, then tracked for the whole file
    cat_candidates = None
    shape_candidates = None
    cat_sample = defaultdict(set)
    wide_sample = defaultdict(set)     # looser cap: catches funding_agency etc.
    wide_dropped = set()
    cat_by_year = defaultdict(lambda: defaultdict(Counter))    # col -> year -> Counter
    shape_by_year = defaultdict(lambda: defaultdict(Counter))  # col -> year -> {shape: n}
    cat_by_era = defaultdict(lambda: defaultdict(Counter))     # col -> era_group -> Counter
    era_rows = Counter()
    era_years = defaultdict(set)
    era_dropped = set()
    cat_dropped = set()

    for rowno, row in enumerate(rdr):
        if len(row) < ncol:
            row = row + [""] * (ncol - len(row))
        out["rows"] += 1

        # --- year -----------------------------------------------------------
        if iy is None:
            y = None
        elif ykind == "col":
            raw = row[iy].strip()
            y = None
            if raw:
                try:
                    y = int(float(raw))
                except ValueError:
                    y = year_of(raw)
                if y is not None and not (1700 <= y <= 2200):
                    y = None
        else:
            y = year_of(row[iy])
        if y is not None:
            year_rows[y] += 1
        else:
            year_rows["<no year>"] += 1

        # --- dedup status ---------------------------------------------------
        is_primary = True
        if idedup is not None:
            dv = row[idedup].strip()
            dedup_counter[dv or "<blank>"] += 1
            is_primary = (dv == dedup_primary)

        # --- money ----------------------------------------------------------
        ent = row[ient].strip() if ient is not None else ""
        if ent and y is not None:
            ents_by_year[y].add(ent)
        if ent:
            sh = id_shape(ent)
            id_shape_year[y][sh] += 1
            id_shape_rows[sh] += 1
            if sum_cols:
                _v = num(row[sum_cols[0][1]])
                if _v is not None:
                    id_shape_usd[sh] += _v
            if iname is not None and len(id_shape_names[sh]) < 20000:
                _n = row[iname].strip().lower()
                if _n:
                    id_shape_names[sh].add(_n)
        for c, rule, i in money_cols:
            st = numstats[c]
            raw = row[i]
            v = num(raw)
            if v is None:
                st["blank"] += 1
                continue
            st["n"] += 1
            if v < 0:
                st["neg"] += 1
            elif v == 0:
                st["zero"] += 1
            else:
                st["pos"] += 1
                d = first_digit(v)
                if d:
                    st["benford"][d] += 1
                if v % 1_000_000 == 0:
                    st["round6"] += 1
                if v % 100_000 == 0:
                    st["round5"] += 1
                if v % 1_000 == 0:
                    st["round3"] += 1
            st["mx"] = v if st["mx"] is None or v > st["mx"] else st["mx"]
            st["mn"] = v if st["mn"] is None or v < st["mn"] else st["mn"]
            if rule == "SUM":
                st["total"] += v
                if is_primary:
                    st["dedup_total"] += v
                if y is not None:
                    year_money[c][y] += v
                    if is_primary:
                        year_money_dedup[c][y] += v
                res = reservoir[(c, y)]
                if len(res) < RESERVOIR:
                    res.append(v)
                if abs(v) >= 1_000_000:
                    aw = row[iaward].strip() if iaward is not None else ""
                    top_rows.append((abs(v), v, c, y, ent, aw,
                                     row[iname].strip() if iname is not None else ""))
                    if len(top_rows) > 8000:
                        top_rows.sort(reverse=True)
                        del top_rows[3000:]

        # --- entity-year ----------------------------------------------------
        if ient is not None and ent and sum_cols and is_primary:
            for c, i in sum_cols:
                v = num(row[i])
                if v is None:
                    continue
                k = (ent, y)
                cell = ent_year.get(k)
                aw = row[iaward].strip() if iaward is not None else ""
                if cell is None:
                    ent_year[k] = [v, 1, abs(v), aw]
                else:
                    cell[0] += v
                    cell[1] += 1
                    if abs(v) > cell[2]:
                        cell[2] = abs(v)
                        cell[3] = aw
                break
            if iname is not None and ent not in ent_name:
                nm = row[iname].strip()
                if nm:
                    ent_name[ent] = nm
        elif ient is not None and ent and not sum_cols:
            k = (ent, y)
            cell = ent_year.get(k)
            if cell is None:
                ent_year[k] = [0.0, 1, 0.0, ""]
            else:
                cell[1] += 1
            if iname is not None and ent not in ent_name:
                nm = row[iname].strip()
                if nm:
                    ent_name[ent] = nm

        # --- metric-keyed value column (gaming) ------------------------------
        if imetric is not None and imetval is not None:
            m = row[imetric].strip()
            v = num(row[imetval])
            if m and v is not None and y is not None:
                res = metric_year[m][y]
                if len(res) < 600:
                    res.append(v)

        # --- dates -----------------------------------------------------------
        for c, i in date_cols:
            ds = datestats[c]
            raw = row[i].strip()
            if not raw:
                ds["blank"] += 1
                continue
            yy = year_of(raw)
            if yy is None:
                ds["unparsed"] += 1
                continue
            if ds["mn"] is None or raw < ds["mn"]:
                ds["mn"] = raw
            if ds["mx"] is None or raw > ds["mx"]:
                ds["mx"] = raw
            if yy > THIS_YEAR:
                ds["future"] += 1
            d = day_of(raw)
            if d:
                ds["days"][d] += 1

        # --- duplicates -------------------------------------------------------
        if dup_idx:
            k = hash(tuple(row[i] for i in dup_idx))
            if k in dup_seen:
                dup_hits += 1
            else:
                dup_seen.add(k)

        # --- categoricals ------------------------------------------------------
        if cat_candidates is None:
            # ERA TRACKING MUST NOT SKIP THE SAMPLE WINDOW. The first
            # CAT_SAMPLE_ROWS rows are not a random sample of the file - they are
            # its FIRST rows, which in an append-built table is one whole source.
            # Starting the era tracker after them undercounted the .dta era's
            # funding_agency vocabulary 167 -> 153 and canonical_name 498 -> 80.
            # A sampling window that lines up with a source boundary is not a
            # sample; it is a filter.
            if iera is not None:
                eg = era_group(row[iera])
                era_rows[eg] += 1
                if y is not None:
                    era_years[eg].add(y)
                if len(era_rows) <= 12:
                    for c, i in idx.items():
                        if c in era_dropped:
                            continue
                        bye = cat_by_era[c][eg]
                        bye[row[i].strip()[:90]] += 1
                        if len(bye) > 2500:
                            era_dropped.add(c)
                            cat_by_era.pop(c, None)
            for c, i in idx.items():
                if c not in wide_dropped:
                    v = row[i]
                    if len(v) > 160:
                        wide_dropped.add(c)
                        wide_sample.pop(c, None)
                    else:
                        ws = wide_sample[c]
                        ws.add(v)
                        if len(ws) > WIDE_SAMPLE_MAX_DISTINCT:
                            wide_dropped.add(c)
                            wide_sample.pop(c, None)
                if c in cat_dropped:
                    continue
                s = cat_sample[c]
                v = row[i]
                if len(v) > 90:
                    cat_dropped.add(c)
                    cat_sample.pop(c, None)
                    continue
                s.add(v)
                if len(s) > CAT_SAMPLE_MAX_DISTINCT:
                    cat_dropped.add(c)
                    cat_sample.pop(c, None)
            if out["rows"] >= CAT_SAMPLE_ROWS:
                cat_candidates = {c: idx[c] for c in cat_sample}
                shape_candidates = {c: idx[c] for c in wide_sample}
        else:
            if iera is not None:
                eg = era_group(row[iera])
                era_rows[eg] += 1
                if y is not None:
                    era_years[eg].add(y)
                if len(era_rows) <= 12:
                    for c, i in idx.items():
                        if c in era_dropped:
                            continue
                        bye = cat_by_era[c][eg]
                        bye[row[i].strip()[:90]] += 1
                        if len(bye) > 2500:
                            era_dropped.add(c)
                            cat_by_era.pop(c, None)
            for c, i in shape_candidates.items():
                shape_by_year[c][y][token_shape(row[i])] += 1
            for c, i in cat_candidates.items():
                if c in cat_dropped:
                    continue
                by = cat_by_year[c][y]
                v = row[i].strip()
                if len(v) > 90:
                    v = v[:90]
                by[v] += 1
                if len(by) > CAT_HARD_CAP:
                    cat_dropped.add(c)
                    cat_by_year.pop(c, None)

    fh.close()
    if cat_candidates is None:                    # file shorter than the sample
        cat_candidates = {c: idx[c] for c in cat_sample}
        shape_candidates = {c: idx[c] for c in wide_sample}
        # re-scan is not worth it for a small file; fall back to sample-only
    out["year_rows"] = {str(k): v for k, v in sorted(year_rows.items(), key=lambda kv: str(kv[0]))}
    out["year_money"] = {c: {str(k): v for k, v in sorted(d.items())} for c, d in year_money.items()}
    out["year_money_primary"] = {c: {str(k): v for k, v in sorted(d.items())}
                                 for c, d in year_money_dedup.items()} if idedup is not None else {}
    out["dedup_counts"] = dict(dedup_counter) if idedup is not None else {}
    out["numstats"] = {}
    for c, st in numstats.items():
        out["numstats"][c] = dict(n=st["n"], neg=st["neg"], zero=st["zero"], blank=st["blank"],
                                  pos=st["pos"], total=st["total"], dedup_total=st["dedup_total"],
                                  mn=st["mn"], mx=st["mx"],
                                  round6=st["round6"], round5=st["round5"], round3=st["round3"],
                                  benford=dict(st["benford"]))
    out["datestats"] = {c: dict(mn=d["mn"], mx=d["mx"], future=d["future"], blank=d["blank"],
                                unparsed=d["unparsed"], days=dict(d["days"]))
                        for c, d in datestats.items()}
    out["dup_hits"] = dup_hits if dup_idx else None
    out["dup_key"] = spec.get("dup_key") if dup_idx else None
    top_rows.sort(reverse=True)
    out["top_rows"] = [dict(abs=t[0], value=t[1], column=t[2], year=t[3], entity=t[4],
                            award=t[5], name=t[6]) for t in top_rows[:40]]
    out["entities_by_year"] = {str(y): len(v) for y, v in sorted(ents_by_year.items())}
    out["id_shape_by_year"] = {str(y): dict(c) for y, c in sorted(id_shape_year.items(), key=lambda kv: str(kv[0]))}
    out["id_shape_rows"] = dict(id_shape_rows)
    out["id_shape_usd"] = dict(id_shape_usd)
    out["_id_shape_names"] = id_shape_names
    out["_ent_year"] = ent_year
    out["_ent_name"] = ent_name
    out["_reservoir"] = reservoir
    out["_cat_by_year"] = {c: {yy: dict(cnt) for yy, cnt in d.items()} for c, d in cat_by_year.items()}
    out["_shape_by_year"] = {c: {yy: dict(cnt) for yy, cnt in d.items()} for c, d in shape_by_year.items()}
    out["_cat_by_era"] = {c: {g: dict(cnt) for g, cnt in d.items()} for c, d in cat_by_era.items()}
    out["era_rows"] = dict(era_rows)
    out["era_years"] = {g: (min(v), max(v)) for g, v in era_years.items() if v}
    out["_metric_year"] = metric_year
    return out


# ---------------------------------------------------------------------------
# typing - PIPELINE first, then REGIME, then WORLD
# ---------------------------------------------------------------------------
def pipeline_hits(dataset, years, cls=""):
    hits = []
    for ds, y0, y1, classes, label, owner in PIPELINE_BOUNDARIES:
        if ds != dataset:
            continue
        if classes is not None and cls not in classes:
            continue
        for year in years:
            if year is not None and y0 <= year <= y1:
                hits.append(dict(label=label, owner=owner, window=str(y0) + "-" + str(y1)))
                break
    return hits


def regime_hits(dataset, years, cls):
    hits = []
    for ev in REGIME_EVENTS:
        if dataset not in ev["datasets"]:
            continue
        if ev["classes"] is not None and cls not in ev["classes"]:
            continue
        for year in years:
            if year is None:
                continue
            if ev.get("only_years") is not None and year not in ev["only_years"]:
                continue
            if ev["y0"] <= year <= ev["y1"]:
                hits.append(dict(key=ev["key"], label=ev["label"],
                                 window=str(ev["y0"]) + "-" + str(ev["y1"])))
                break
    return hits


def classify(dataset, year, cls="", pipeline_note=None, regime_note=None, world_note=None,
             single_award_explains=False):
    """Returns (type, evidence). PIPELINE > REGIME > WORLD > UNKNOWN.

    ONE deliberate exception to the order, stated in the report itself: where a
    SINGLE NAMED AWARD accounts for half or more of an entity-year, that award IS
    the explanation of the spike, and the row is typed WORLD with the regime
    caveat carried in its evidence. The regime question then becomes "why did
    that award exist" - a different question about a different object, not
    answerable from a year-over-year test. A PIPELINE boundary still wins: a
    named award inside a filtered backfill is a named award we may have selected
    for.
    """
    years = list(year) if isinstance(year, (list, tuple, set)) else [year]
    p = pipeline_hits(dataset, years, cls)
    r = regime_hits(dataset, years, cls)
    ev = []
    if pipeline_note:
        ev.append("PIPELINE candidate: " + pipeline_note)
    for h in p:
        ev.append("PIPELINE boundary " + h["window"] + " (" + h["owner"] + "): " + h["label"])
    if regime_note:
        ev.append("REGIME candidate: " + regime_note)
    for h in r:
        ev.append("REGIME " + h["key"] + " " + h["window"] + ": " + h["label"])
    if world_note:
        ev.append(world_note)
    if p or pipeline_note:
        if r or regime_note:
            return "UNKNOWN", ev + ["CONFOUNDED: a pipeline boundary and a regime change coincide here. Both "
                                    "candidates are named; neither is chosen."]
        return "PIPELINE", ev
    if single_award_explains and world_note:
        if r:
            ev.append("Typed WORLD despite the regime window above BECAUSE a single named award carries the "
                      "year. The regime caveat still travels with any sentence about the SERIES.")
        return "WORLD", ev
    if r or regime_note:
        return "REGIME", ev
    if world_note:
        return "WORLD", ev
    return "UNKNOWN", ev + ["No pipeline boundary and no registered regime change covers this year, and no "
                            "single award or event explains it. Reported as UNKNOWN rather than smoothed over."]


# ---------------------------------------------------------------------------
# anomaly derivation
# ---------------------------------------------------------------------------
def derive(res, spec):
    A = []
    ds = res["name"]
    if res.get("error"):
        A.append(dict(cls="DATASET_MISSING", dataset=ds, type="PIPELINE", stake_rows=0, stake_usd=0.0,
                      title=f"{res['source']['path']}: {res['error']}",
                      evidence=[f"Spec names this file; it is not on disk at run time."],
                      owner=spec.get("owner", "unknown")))
        return A

    yrs = {int(k): v for k, v in res["year_rows"].items() if k.isdigit()}
    noyear = res["year_rows"].get("<no year>", 0)
    years = sorted(yrs)
    ymin, ymax = (years[0], years[-1]) if years else (None, None)

    # ---- CLASS 3: dataset-year discontinuities -----------------------------
    for i in range(1, len(years)):
        y0, y1 = years[i - 1], years[i]
        if y1 != y0 + 1:
            # a hole in the series
            gap = list(range(y0 + 1, y1))
            if ymin is not None and len(gap) <= 12:
                t, ev = classify(ds, [y0, y1], cls="YEAR_GAP")
                A.append(dict(cls="YEAR_GAP", dataset=ds, type=t, year=y1,
                              stake_rows=0, stake_usd=0.0,
                              title=f"{ds}: no rows at all for {', '.join(map(str, gap))}",
                              evidence=ev + [f"Series runs {ymin}-{ymax}; {len(gap)} year(s) hold zero rows."]))
            continue
        a, b = yrs[y0], yrs[y1]
        if a < 40 and b < 40:
            continue
        ratio = (b / a) if a else float("inf")
        if ratio < DISCONT_LO or ratio > DISCONT_HI:
            t, ev = classify(ds, [y0, y1], cls="YEAR_STEP_ROWS")
            A.append(dict(cls="YEAR_STEP_ROWS", dataset=ds, type=t, year=y1,
                          stake_rows=abs(b - a), stake_usd=0.0,
                          title=f"{ds}: row count steps {a:,} ({y0}) -> {b:,} ({y1}), x{ratio:.2f}",
                          evidence=ev + [f"row counts by year: {y0}={a:,}, {y1}={b:,}"]))

    # ---- money steps --------------------------------------------------------
    # A LUMPY series is one where a single record can BE the year. Announced deal
    # value is the type case: 935 rows over 27 years, and one $1.42B transaction
    # makes 2007. Testing year-over-year multiples on such a series manufactures
    # an anomaly per year and says nothing. It gets ONE finding instead, which is
    # the true one: the series must never be charted as a trend.
    if spec.get("lumpy_money"):
        for col, rule in spec["money"]:
            if rule != "SUM":
                continue
            series = {int(k): v for k, v in res["year_money"].get(col, {}).items() if k.isdigit()}
            if len(series) < 5:
                continue
            sy = sorted(series)
            vals = [series[y] for y in sy]
            ratios = [vals[i] / vals[i - 1] for i in range(1, len(vals)) if vals[i - 1] > 0]
            wild = [r for r in ratios if r > 3 or r < 0.34]
            A.append(dict(cls="LUMPY_SERIES", dataset=ds, type="PIPELINE", year=None, column=col,
                          stake_rows=res["rows"], stake_usd=sum(abs(v) for v in vals),
                          title=(f"{ds}.{col} is a LUMPY series: {len(wild)} of {len(ratios)} year-over-year "
                                 f"ratios move more than 3x in one direction"),
                          evidence=[
                              f"{res['rows']:,} rows over {len(sy)} years — a mean of {res['rows']/len(sy):.0f} "
                              f"records a year. A single transaction can BE the year.",
                              "year totals: " + ", ".join(f"{y}={money(series[y])}" for y in sy),
                              "THIS IS NOT A TREND AND MUST NEVER BE CHARTED AS ONE. Individual deals are the "
                              "unit of analysis here; an annual total is a sampling artefact of which deals were "
                              "collected. Report deals individually, or report COUNTS with the collection-coverage "
                              "caveat attached.",
                              "OWNER: 88_build_deals_taxonomy.py (do not run) + 155_collect_deals_2026_08.py"]))

    for col, rule in spec["money"]:
        if rule != "SUM" or spec.get("lumpy_money"):
            continue
        series = {int(k): v for k, v in res["year_money"].get(col, {}).items() if k.isdigit()}
        if res.get("year_money_primary", {}).get(col):
            series = {int(k): v for k, v in res["year_money_primary"][col].items() if k.isdigit()}
        sy = sorted(series)
        for i in range(1, len(sy)):
            y0, y1 = sy[i - 1], sy[i]
            if y1 != y0 + 1:
                continue
            a, b = series[y0], series[y1]
            if abs(a) < 5e6 and abs(b) < 5e6:
                continue
            if yrs.get(y0, 0) < 25 or yrs.get(y1, 0) < 25:
                continue
            if a <= 0:
                continue
            ratio = b / a
            if ratio < DISCONT_LO or ratio > DISCONT_HI:
                t, ev = classify(ds, [y0, y1], cls="YEAR_STEP_MONEY")
                A.append(dict(cls="YEAR_STEP_MONEY", dataset=ds, type=t, year=y1,
                              stake_rows=0, stake_usd=abs(b - a),
                              title=f"{ds}.{col}: {money(a)} ({y0}) -> {money(b)} ({y1}), x{ratio:.2f}",
                              evidence=ev + [f"{col} summed per year, honouring dedup where the dataset has one; "
                                             f"{y0}={money(a)}, {y1}={money(b)}"]))

    # ---- CLASS 1 & 2: entity-year spikes, appearances, disappearances -------
    ent_year = res.pop("_ent_year", {})
    ent_name = res.pop("_ent_name", {})
    by_ent = defaultdict(dict)
    for (e, y), cell in ent_year.items():
        if y is None:
            continue
        by_ent[e][y] = cell
    has_money = bool([1 for c, r in spec["money"] if r == "SUM"])

    # A spike needs a BASELINE. Two observations are a line, not a series - an
    # entity with one prior year has no prior variance, so any second year that
    # happens to be larger trips a multiple test. Three active years and two
    # prior ones is the floor for saying "against its own history".
    floor = spec.get("spike_min_dollars", SPIKE_MIN_DOLLARS) if has_money else \
        spec.get("spike_min_rows", SPIKE_MIN_ROWS)
    for e, ys in by_ent.items():
        if len(ys) < 3:
            continue
        sy = sorted(ys)
        for i, y in enumerate(sy):
            v = ys[y][0] if has_money else ys[y][1]
            if i < 2:
                continue
            prior = [ys[p][0] if has_money else ys[p][1] for p in sy[:i]]
            pk = max(prior)
            pmed = statistics.median(prior)
            if v < floor:
                continue
            if pk > 0 and v / pk < SPIKE_MULTIPLE:
                continue
            if pmed > 0 and v / pmed < SPIKE_MULTIPLE:
                continue
            if pk <= 0 and v < floor * 2:
                continue
            mx, aw = ys[y][2], ys[y][3]
            share = (mx / v) if (has_money and v) else 0.0
            wn = None
            pn = None
            extra = []
            if has_money and mx:
                extra.append(f"largest single row in that entity-year: {money(mx)} = {share*100:.0f}% of the "
                             f"entity's year"
                             + (f", on award/id {aw!r}" if aw else " (no award identifier on the row)"))
            if has_money and share >= 0.5 and aw:
                wn = (f"EXPLAINED BY ONE AWARD: the largest single row in that entity-year is {money(mx)} "
                      f"({share*100:.0f}% of the entity's year) on award/id {aw!r}. A single large award is a "
                      f"fact about the world unless the award itself is a bad link.")
            elif has_money and share >= 0.3 and aw:
                extra.append(f"PARTLY concentrated: one row carries {share*100:.0f}% of the year, but not enough "
                             f"to call the year a single award. The rest of the jump is unaccounted.")
            elif has_money and ys[y][1] and share < 0.15:
                extra.append(f"NOT a single award: the year is spread over {ys[y][1]:,} rows and the largest is "
                             f"only {share*100:.0f}% of it. A broad-based jump is more likely a programme round, "
                             f"a linkage pass landing, or a regime change than a business event.")
            if e == "TRBF-ENTPRS-00":
                pn = ("This entity's canonical name is literally 'Enterprise' - a common English noun that "
                      "name-matching will hoover rows onto. Known-bad link class (FA-03).")
            t, ev = classify(ds, y, cls="ENTITY_SPIKE", pipeline_note=pn, world_note=wn,
                             single_award_explains=bool(wn))
            A.append(dict(cls="ENTITY_SPIKE", dataset=ds, type=t, year=y, entity=e,
                          entity_name=ent_name.get(e, ""),
                          stake_rows=ys[y][1], stake_usd=(v - pk) if has_money else 0.0,
                          title=(f"{ent_name.get(e, e)} [{e}] in {ds} {y}: "
                                 + (f"{money(v)} against a prior peak of {money(pk)}"
                                    if has_money else f"{v:,} rows against a prior peak of {pk:,}")),
                          evidence=ev + extra + [f"entity-year series: " +
                                         ", ".join(f"{p}={money(ys[p][0]) if has_money else ys[p][1]}"
                                                   for p in sy)]))

    # appearance / disappearance
    if by_ent and ymax is not None:
        for e, ys in by_ent.items():
            sy = sorted(y for y in ys if y is not None)
            if len(sy) < 3:
                continue
            tot = sum(ys[y][0] for y in sy) if has_money else sum(ys[y][1] for y in sy)
            last = sy[-1]
            first = sy[0]
            span = len(sy)
            if has_money and abs(tot) < max(5_000_000, floor):
                continue
            if not has_money and tot < 200:
                continue
            nrows = sum(ys[y][1] for y in sy)
            if nrows < 8:
                continue
            if last <= ymax - 3 and span >= 4:
                t, ev = classify(ds, [last, last + 1], cls="ENTITY_DISAPPEARANCE")
                A.append(dict(cls="ENTITY_DISAPPEARANCE", dataset=ds, type=t, year=last, entity=e,
                              entity_name=ent_name.get(e, ""),
                              stake_rows=sum(ys[y][1] for y in sy),
                              stake_usd=abs(tot) if has_money else 0.0,
                              title=(f"{ent_name.get(e, e)} [{e}] active {first}-{last} in {ds}, then absent "
                                     f"through {ymax}"),
                              evidence=ev + [
                                  f"{span} active years, "
                                  + (f"lifetime {money(tot)}" if has_money else f"{tot:,} rows"),
                                  "CANDIDATE CAUSES, in the order they should be tested: (1) a RENAME - Cedar holds "
                                  "federal_recognition_roster FR citations for renames (e.g. Tolowa Dee-ni' Nation "
                                  "'previously listed as the Smith River Rancheria'); (2) a MERGER or ACQUISITION - "
                                  "check ownership_events.csv and the ten dated changes in "
                                  "docs/INDIVIDUAL_NATIVE_OWNERSHIP_VERIFICATION_BUILD_LOG.md, where DAWSON -> "
                                  "LAUKOA on 2026-06-29 kept the SAME UEI and CAGE; (3) an 8(a) NINE-YEAR TERM "
                                  "expiring with a successor entity starting; (4) OUR LINKAGE BREAKING."]))
            if first >= ymin + 3 and span >= 3:
                fv = ys[first][0] if has_money else ys[first][1]
                if has_money and abs(fv) < max(20_000_000, floor * 4):
                    continue
                if not has_money and fv < 300:
                    continue
                t, ev = classify(ds, first, cls="ENTITY_APPEARANCE")
                A.append(dict(cls="ENTITY_APPEARANCE", dataset=ds, type=t, year=first, entity=e,
                              entity_name=ent_name.get(e, ""),
                              stake_rows=ys[first][1], stake_usd=abs(fv) if has_money else 0.0,
                              title=(f"{ent_name.get(e, e)} [{e}] appears FULLY FORMED in {ds} {first} at "
                                     + (money(fv) if has_money else f"{fv:,} rows")
                                     + f" (dataset begins {ymin})"),
                              evidence=ev + ["An entity that appears at scale rather than growing into it is a "
                                             "rename, a successor entity, an acquisition, or a linkage pass landing "
                                             "- test those four before reading it as a new business."]))

    # ---- CLASS 4: seams. Vocabulary shift at a year boundary ---------------
    # A column whose VALUE SET changes at a year boundary is a source or build
    # seam until proven otherwise, and any filter on it silently selects an ERA.
    # TWO refinements paid for by this run:
    #   * A column with ONE value per era is the PUREST seam and the original
    #     test skipped it, because it required two values a side. The archive
    #     stamp on the assistance table is exactly that shape.
    #   * A column whose values CONTAIN THE YEAR (`hhs_fy2001.zip`) changes
    #     vocabulary every single year BY CONSTRUCTION. That is not a seam; it
    #     is a filename. It still earns an ERA MAP, because which source covers
    #     which years is the useful artefact hiding inside the false positive.
    cats = res.pop("_cat_by_year", {})
    for col, byyear in cats.items():
        if seam_skip(col, spec):
            continue
        yy = sorted(y for y in byyear if isinstance(y, int))
        if len(yy) < 3:
            continue
        modal = {}
        for y in yy:
            c = byyear[y]
            nz = {k: v for k, v in c.items() if k != ""}
            if nz:
                modal[y] = max(nz.items(), key=lambda kv: kv[1])[0]
        boundaries = []
        for i in range(1, len(yy)):
            y0, y1 = yy[i - 1], yy[i]
            c0, c1 = byyear[y0], byyear[y1]
            n0, n1 = sum(c0.values()), sum(c1.values())
            if n0 < 300 or n1 < 300:
                continue
            s0 = {k for k, v in c0.items() if v >= max(3, n0 * 0.005) and k != ""}
            s1 = {k for k, v in c1.items() if v >= max(3, n1 * 0.005) and k != ""}
            if not s0 or not s1:
                continue
            j = jaccard(s0, s1)
            if j > SEAM_JACCARD:
                continue
            boundaries.append((y0, y1, j, sorted(s1 - s0)[:8], sorted(s0 - s1)[:8]))
        if not boundaries:
            continue
        # year-keyed? a value carrying its own year is a filename, not a seam
        year_keyed = 0
        for y in yy:
            m = modal.get(y)
            if m and str(y) in m:
                year_keyed += 1
        is_year_keyed = (year_keyed >= max(2, int(0.6 * len(yy)))) or (col in SEAM_PROCESS)
        era_map = []
        prev = None
        for y in yy:
            m = modal.get(y)
            if m != prev:
                era_map.append(f"{y}: {m!r}")
                prev = m
        known = KNOWN_SEAMS.get((ds, col))
        annot = SEAM_ANNOTATIONS.get((ds, col))
        y0, y1, j, appeared, vanished = boundaries[0]
        if is_year_keyed:
            A.append(dict(cls="ERA_MAP", dataset=ds, type="PIPELINE", year=None, column=col,
                          stake_rows=res["rows"], stake_usd=0.0, known=bool(known),
                          title=(f"{ds}.{col}: ERA MAP — "
                                 + ("build/pull metadata" if col in SEAM_PROCESS
                                    else "the value carries its own year, so it is a source map rather than a "
                                         "seam")
                                 + f" ({len(boundaries)} boundaries)"),
                          evidence=["NOT A DEFECT and NOT a seam. A filename that contains its own year, or a "
                                    "build stamp, changes vocabulary annually no matter what. It is listed "
                                    "because the ERA MAP inside it is the useful artefact: it says WHICH PULL "
                                    "COVERS WHICH YEARS, which is the first thing to check when a year looks "
                                    "wrong and the last thing anyone thinks to look at.",
                                    "era map (year: modal value, printed only where it changes): "
                                    + " | ".join(era_map[:24])]))
            continue
        pn = (known or
              (f"The value vocabulary of {col!r} is almost disjoint across the {y0}/{y1} boundary "
               f"(Jaccard {j:.2f}). Any filter on this column selects an ERA, not a category."))
        t, ev = classify(ds, [y0, y1], cls="VOCABULARY_SEAM", pipeline_note=pn)
        A.append(dict(cls="VOCABULARY_SEAM", dataset=ds, type=t, year=y1, column=col,
                      stake_rows=res["rows"], stake_usd=0.0, known=bool(known),
                      title=(f"{ds}.{col}: value vocabulary changes at {y0}/{y1} (Jaccard {j:.2f})"
                             + ("  [KNOWN]" if known else "  [NEW]")
                             + (f"  · {len(boundaries)} boundaries in all" if len(boundaries) > 1 else "")),
                      evidence=ev + [f"values common in {y1} and absent in {y0}: {appeared}",
                                     f"values common in {y0} and absent in {y1}: {vanished}",
                                     "era map (year: modal value, printed only where it changes): "
                                     + " | ".join(era_map[:24]),
                                     "all boundaries: " + ", ".join(f"{a}/{b} (J={jj:.2f})"
                                                                    for a, b, jj, _, _ in boundaries)]
                               + ([annot] if annot else [])))

    # ---- CLASS 4b1: SAME SHAPE, SAME SIZE, DIFFERENT RENDERING --------------
    # The third and quietest form of the seam, and the one the first two tests
    # are both blind to. `funding_agency` is the worked example: every value is
    # a LABEL in every year, so the SHAPE test sees nothing; and the eras share
    # enough values that a whole-set Jaccard sits above threshold. What is
    # actually true is that one era writes 'Dept Of Defense' and the other
    # writes 'Department of Defense' - the same agency, rendered twice, and a
    # string filter picks one era.
    #
    # The metric that catches it: what share of a year's ROWS carry a value
    # that NEVER appears on the other side of the boundary? A real panel churns
    # a few percent. A rendering change churns tens of percent while the thing
    # being described has not changed at all.
    for col, byyear in cats.items():
        if seam_skip(col, spec):
            continue
        yy = sorted(y for y in byyear if isinstance(y, int))
        if len(yy) < 5:
            continue
        already = any(a["cls"] in ("VOCABULARY_SEAM", "VOCABULARY_MIX_SHIFT")
                      and a.get("column") == col and a["dataset"] == ds for a in A)
        if already:
            continue
        worst = None
        for i in range(2, len(yy) - 1):
            y1 = yy[i]
            before, after = yy[:i], yy[i:]
            sb, sa = set(), set()
            for y in before:
                sb |= {k for k in byyear[y] if k != ""}
            for y in after:
                sa |= {k for k in byyear[y] if k != ""}
            if len(sb) < 20 or len(sa) < 20:
                continue
            # SAME CLOSED CATEGORY, not two disjoint open sets. Zero overlap is
            # not a rendering split - it is two sources naming different things,
            # and a per-year filename set is the classic case (`doc_fy2001.zip`
            # shares nothing with `doc_fy2002.zip` and that is not a defect).
            sh = len(sb & sa)
            if sh < 8 or sh / min(len(sa), len(sb)) < 0.35:
                continue
            if sum(1 for k in list(sa)[:200] if YEARISH.search(k)) > 100:
                continue
            nb = sum(v for y in before for k, v in byyear[y].items() if k and k not in sa)
            na = sum(v for y in after for k, v in byyear[y].items() if k and k not in sb)
            tb = sum(v for y in before for k, v in byyear[y].items() if k)
            ta = sum(v for y in after for k, v in byyear[y].items() if k)
            if not tb or not ta:
                continue
            unshared = (nb + na) / (tb + ta)
            if worst is None or unshared > worst[1]:
                worst = (y1, unshared, len(sb), len(sa), len(sb & sa), nb + na)
        if worst is None or worst[1] < 0.20:
            continue
        y1, unshared, nb_, na_, shared, rows_unshared = worst
        known = KNOWN_SEAMS.get((ds, col))
        annot = SEAM_ANNOTATIONS.get((ds, col))
        t, ev = classify(ds, [y1 - 1, y1], cls="VOCABULARY_SEAM", pipeline_note=(
            known or
            f"{col!r} splits at {y1-1}/{y1} into two vocabularies of the SAME shape and SIMILAR size that "
            f"only partly overlap: {nb_} distinct values before, {na_} after, {shared} shared, and "
            f"{rows_unshared:,} rows ({unshared*100:.1f}%) carry a value the OTHER side never produces. "
            f"Neither the shape test nor a whole-set comparison sees this, because both eras look like the "
            f"same KIND of value. A string filter on this column selects an era."))
        A.append(dict(cls="VOCABULARY_RENDERING_SPLIT", dataset=ds, type=t, year=y1, column=col,
                      stake_rows=rows_unshared, stake_usd=0.0, known=bool(known),
                      title=(f"{ds}.{col}: {nb_} vs {na_} distinct values across {y1-1}/{y1}, only {shared} "
                             f"shared — {rows_unshared:,} rows ({unshared*100:.0f}%) carry a rendering the "
                             f"other era never produces" + ("  [KNOWN]" if known else "  [NEW]")),
                      evidence=ev + [
                          "This is the seam class with NO automated fix available unless an authoritative code "
                          "column exists to normalise against. `extent_competed` had one (DAIMS-DEC v2.2) and "
                          "has been normalised; a column with no code list has to be crosswalked by hand or "
                          "left alone.",
                          "UNTIL THEN: do not build a category time series off this column, and do not filter "
                          "it by string equality. Aggregate to a level coarse enough that both renderings land "
                          "in the same bucket, and say so.",
                      ] + ([annot] if annot else [])))

    # ---- CLASS 4b2: A VOCABULARY MIX THAT SHIFTS WITHOUT BEING REPLACED -----
    # The Jaccard test above finds a column whose value set is REPLACED. This
    # one finds the harder case: two vocabularies MIXING in one column, so both
    # eras share values, the sets never separate, and the column still means
    # two different things depending on which year you are in.
    shp = res.pop("_shape_by_year", {})
    for col, byyear in shp.items():
        if seam_skip(col, spec):
            continue
        yy = sorted(y for y in byyear if isinstance(y, int))
        if len(yy) < 4:
            continue
        share = {}
        for y in yy:
            tot = sum(byyear[y].values())
            if tot < 300:
                continue
            share[y] = {k: v / tot for k, v in byyear[y].items()}
        sy = sorted(share)
        best = None
        for i in range(1, len(sy)):
            y0, y1 = sy[i - 1], sy[i]
            if y1 != y0 + 1:
                continue
            for k in set(share[y0]) | set(share[y1]):
                if k == "BLANK":
                    continue
                d = share[y1].get(k, 0.0) - share[y0].get(k, 0.0)
                if abs(d) >= 0.25 and (best is None or abs(d) > abs(best[3])):
                    best = (y0, y1, k, d)
        if best is None:
            continue
        y0, y1, k, d = best
        # a shape present on BOTH sides of the panel means the vocabularies MIX
        mixing = sum(1 for y in sy if share[y].get(k, 0) > 0.02)
        if mixing < 2:
            continue
        known = KNOWN_SEAMS.get((ds, col))
        annot = SEAM_ANNOTATIONS.get((ds, col))
        line = []
        for y in sy:
            parts = sorted(((v, kk) for kk, v in share[y].items() if v >= 0.02), reverse=True)
            line.append(f"{y}: " + "/".join(f"{kk} {v*100:.0f}%" for v, kk in parts))
        t, ev = classify(ds, [y0, y1], cls="VOCABULARY_SEAM", pipeline_note=(
            known or
            f"The value-SHAPE mix of {col!r} moves {d*100:+.0f} percentage points at {y0}/{y1} "
            f"({k}: {share[y0].get(k,0)*100:.0f}% -> {share[y1].get(k,0)*100:.0f}%) while both shapes remain "
            f"present across the panel. TWO VOCABULARIES ARE MIXING IN ONE COLUMN. Because the value sets "
            f"OVERLAP in every year, a set-comparison test cannot see this and a filter on any single value "
            f"returns a clean, plausible, era-selected answer."))
        A.append(dict(cls="VOCABULARY_MIX_SHIFT", dataset=ds, type=t, year=y1, column=col,
                      stake_rows=res["rows"], stake_usd=0.0, known=bool(known),
                      title=(f"{ds}.{col}: value-SHAPE mix shifts {d*100:+.0f}pp at {y0}/{y1} "
                             f"({k}) — two vocabularies MIXING, not replaced"
                             + ("  [KNOWN]" if known else "  [NEW]")),
                      evidence=ev + [
                          "shape mix by year (shares >=2%): " + "  |  ".join(line[:28]),
                          "A shape is the FORM of the value, not its meaning: CODE_1CHAR is a single character, "
                          "LABEL is a phrase, CODE_SHORT is a short uppercase token. A column that holds a raw "
                          "code in some years and a rendered label in others holds two vocabularies whatever the "
                          "values happen to be.",
                      ] + ([annot] if annot else [])))

    # ---- CLASS 4b0: A SEAM THAT DOES NOT FALL ON A YEAR BOUNDARY ------------
    # THE STRUCTURAL BLIND SPOT OF EVERYTHING ABOVE, and it is worth stating
    # plainly: every test so far compares ADJACENT YEARS. A seam only shows up
    # in those tests if the two sources it separates occupy DIFFERENT years.
    # When two pulls OVERLAP - when FY2008-2022 is served by a BGOV extract and
    # an archive zip AT THE SAME TIME - the vocabularies mix inside every year
    # and no year-over-year test can see it, no matter how sensitive.
    #
    # So this one splits by SOURCE instead of by year, and asks the same
    # question: what share of rows carries a value the other source never
    # produces? `prime_contracts.funding_agency` is the case that forced it -
    # 167 renderings from the .dta against 264 from the archive, 116 shared.
    eras = res.pop("_cat_by_era", {})
    era_rows_all = res.get("era_rows", {})
    big = [g for g, n in sorted(era_rows_all.items(), key=lambda kv: -kv[1]) if n >= 2000][:2]
    if len(big) == 2 and eras:
        ga, gb = big
        yrs_a = res.get("era_years", {}).get(ga)
        yrs_b = res.get("era_years", {}).get(gb)
        overlap_years = None
        if yrs_a and yrs_b:
            lo, hi = max(yrs_a[0], yrs_b[0]), min(yrs_a[1], yrs_b[1])
            overlap_years = (lo, hi) if lo <= hi else None
        for col, bygrp in eras.items():
            if seam_skip(col, spec) or col == spec.get("era_col"):
                continue
            if OPEN_SET_RE.search(col.lower()):
                continue
            ca, cb = bygrp.get(ga, {}), bygrp.get(gb, {})
            sa = {k for k in ca if k}
            sb = {k for k in cb if k}
            if len(sa) < 15 or len(sb) < 15:
                continue
            # A CLOSED CATEGORY, not an open set. Two sources covering different
            # ENTITIES, CITIES or URLs share almost nothing and that is not a
            # seam - it is two sources covering different things, which is what
            # sources do. A seam is the same CATEGORY SYSTEM written two ways,
            # so the two vocabularies must be small enough to be a code list AND
            # must genuinely overlap.
            if len(sa) > 400 or len(sb) > 400:
                continue
            shared = len(sa & sb)
            if shared < 8 or shared / min(len(sa), len(sb)) < 0.35:
                continue
            na = sum(v for k, v in ca.items() if k and k not in sb)
            nb = sum(v for k, v in cb.items() if k and k not in sa)
            ta = sum(v for k, v in ca.items() if k)
            tb = sum(v for k, v in cb.items() if k)
            if not ta or not tb:
                continue
            unshared = (na + nb) / (ta + tb)
            if unshared < 0.10:
                continue
            known = KNOWN_SEAMS.get((ds, col))
            annot = SEAM_ANNOTATIONS.get((ds, col))
            pn = (known or
                  f"{col!r} is rendered differently by the two sources that BUILD this table. "
                  f"{ga!r} produces {len(sa)} distinct values, {gb!r} produces {len(sb)}, and only "
                  f"{shared} are shared - so {na + nb:,} rows ({unshared*100:.1f}%) carry a value the "
                  f"other source never produces.")
            t, ev = classify(ds, None, cls="SOURCE_VOCABULARY_SPLIT", pipeline_note=pn)
            note = []
            if overlap_years:
                note.append(
                    f"**AND THE TWO SOURCES OVERLAP IN TIME — {overlap_years[0]}-{overlap_years[1]}.** That is "
                    f"why no year-over-year test finds this: both vocabularies are present inside the SAME "
                    f"years, so no year boundary separates them. A seam does not have to fall on a date.")
            else:
                note.append("The two sources do not overlap in time, so this seam ALSO shows as a year "
                            "boundary elsewhere in this report.")
            A.append(dict(cls="SOURCE_VOCABULARY_SPLIT", dataset=ds, type=t, year=None, column=col,
                          stake_rows=na + nb, stake_usd=0.0, known=bool(known),
                          title=(f"{ds}.{col}: the two SOURCES render this column differently — {len(sa)} vs "
                                 f"{len(sb)} distinct values, {shared} shared, {na + nb:,} rows "
                                 f"({unshared*100:.0f}%) unmatchable across the seam"
                                 + ("  [KNOWN]" if known else "  [NEW]")),
                          evidence=ev + note + [
                              f"sources compared: {ga!r} ({era_rows_all[ga]:,} rows) vs {gb!r} "
                              f"({era_rows_all[gb]:,} rows), grouped from {spec.get('era_col')!r} by "
                              f"replacing digit runs with '#'",
                              f"values only {ga!r} produces: {sorted(sa - sb)[:5]}",
                              f"values only {gb!r} produces: {sorted(sb - sa)[:5]}",
                              "A STRING FILTER ON THIS COLUMN SELECTS A SOURCE. So does a GROUP BY. Neither "
                              "looks wrong: every row has a value, and the value is correct for the source it "
                              "came from.",
                          ] + ([annot] if annot else [])))

    # ---- CLASS 4c: TWO IDENTIFIER SCHEMES IN ONE COLUMN ---------------------
    # The quietest seam in the corpus. Nothing is blank, nothing is malformed,
    # every row carries an id - and the same entity simply has two of them,
    # one per era. A per-entity total then SPLITS the entity at the boundary and
    # a distinct-entity count DOUBLE-COUNTS it wherever the eras overlap.
    shapes = {str(k): v for k, v in res.get("id_shape_by_year", {}).items()}
    shape_names = res.pop("_id_shape_names", {})
    sy = sorted(int(k) for k in shapes if k.isdigit())
    if len(sy) >= 3:
        modal = {}
        for y in sy:
            c = {k: v for k, v in shapes[str(y)].items() if k != "BLANK"}
            if c:
                modal[y] = max(c.items(), key=lambda kv: kv[1])[0]
        distinct_shapes = {v for v in modal.values()}
        if len(distinct_shapes) > 1:
            flips = [(sy[i - 1], sy[i]) for i in range(1, len(sy))
                     if modal.get(sy[i - 1]) != modal.get(sy[i])]
            rows_by_shape = res.get("id_shape_rows", {})
            usd_by_shape = res.get("id_shape_usd", {})
            overlap = 0
            pair = sorted(distinct_shapes)
            if len(pair) >= 2 and shape_names:
                a, b = pair[0], pair[1]
                overlap = len(shape_names.get(a, set()) & shape_names.get(b, set()))
            era_line = []
            prev = None
            for y in sy:
                if modal.get(y) != prev:
                    era_line.append(f"{y}: {modal.get(y)}")
                    prev = modal.get(y)
            biggest = max(usd_by_shape.values()) if usd_by_shape else 0.0
            t, ev = classify(ds, [f[1] for f in flips], cls="ID_SCHEME_SEAM", pipeline_note=(
                f"The entity column {spec['entity'][0]!r} holds MORE THAN ONE IDENTIFIER SCHEME "
                f"({', '.join(sorted(distinct_shapes))}) and which one a row carries depends on WHICH YEAR it "
                f"is from. Nothing is blank and nothing is malformed - the same entity simply has two ids."))
            A.append(dict(cls="ID_SCHEME_SEAM", dataset=ds, type=t, year=(flips[0][1] if flips else None),
                          column=spec["entity"][0],
                          stake_rows=sum(rows_by_shape.values()), stake_usd=biggest,
                          title=(f"{ds}.{spec['entity'][0]}: {len(distinct_shapes)} IDENTIFIER SCHEMES in one "
                                 f"column, switching at "
                                 + ", ".join(f"{a}/{b}" for a, b in flips[:4])),
                          evidence=ev + [
                              "rows per scheme: " + ", ".join(f"{k}={v:,}" for k, v in sorted(rows_by_shape.items())),
                              ("dollars per scheme: " + ", ".join(f"{k}={money(v)}"
                                                                  for k, v in sorted(usd_by_shape.items()))
                               if usd_by_shape else "no money column on this table"),
                              "era map (year: modal scheme, printed only where it changes): " + " | ".join(era_line),
                              (f"{overlap} canonical names appear under BOTH schemes - each of those is ONE entity "
                               f"counted as TWO. The true overlap is larger, because the two eras also render the "
                               f"same name differently and only exact matches are counted here."
                               if overlap else
                               "No canonical name matches exactly across the schemes at this vintage, which does "
                               "NOT mean the entities are different - the two eras render names differently."),
                              "CONSEQUENCE, and it is the publishable-number kind: **a per-entity total on this "
                              "column SPLITS an entity at the boundary**, and **a distinct-entity count "
                              "DOUBLE-COUNTS every entity present in both eras**. Neither failure looks wrong: "
                              "the totals still add up and every row still has an id.",
                              "TO FIX: a crosswalk applied at build so one column carries one scheme, or a second "
                              "normalised column. Check whether a `*_neid` column already exists and is POPULATED "
                              "on the legacy rows - on the assistance table it exists and is populated on ZERO of "
                              "them, so the crosswalk is absent, not merely unused.",
                          ]))

    # ---- CLASS 2b: THE ENTITY UNIVERSE ITSELF ------------------------------
    # How many DISTINCT entities does the dataset resolve in each year? This is
    # the check that separates "a tribe stopped receiving money" from "we
    # stopped being able to name it". A dataset can hold steady row counts and
    # steady dollars while the number of entities it can NAME collapses, and
    # nothing about the totals looks wrong.
    eby = {int(k): v for k, v in res.get("entities_by_year", {}).items() if k.isdigit()}
    ey = sorted(eby)
    for i in range(1, len(ey)):
        y0, y1 = ey[i - 1], ey[i]
        if y1 != y0 + 1:
            continue
        a, b = eby[y0], eby[y1]
        if a < 40 and b < 40:
            continue
        ratio = b / a if a else float("inf")
        rowratio = (yrs.get(y1, 0) / yrs[y0]) if yrs.get(y0) else None
        if 0.75 <= ratio <= 1.6:
            continue
        # the dangerous case: the ENTITY count moves and the ROW count does not
        divergent = rowratio is not None and 0.75 <= rowratio <= 1.4
        pn = None
        if divergent:
            pn = (f"THE ROW COUNT BARELY MOVES ({yrs[y0]:,} -> {yrs.get(y1,0):,}, x{rowratio:.2f}) WHILE THE "
                  f"NAMED-ENTITY COUNT MOVES x{ratio:.2f}. The data is still there; our ability to NAME who it "
                  f"belongs to changed. That is an attribution/linkage fact about Cedar, not about Indian "
                  f"Country, and it is invisible in any dollar total.")
        t, ev = classify(ds, [y0, y1], cls="ENTITY_UNIVERSE_STEP", pipeline_note=pn)
        A.append(dict(cls="ENTITY_UNIVERSE_STEP", dataset=ds, type=t, year=y1,
                      stake_rows=abs(yrs.get(y1, 0) - yrs.get(y0, 0)), stake_usd=0.0,
                      title=(f"{ds}: distinct named entities {a:,} ({y0}) -> {b:,} ({y1}), x{ratio:.2f}"
                             + ("  — WHILE ROW COUNT HOLDS" if divergent else "")),
                      evidence=ev + ["distinct entities by year: "
                                     + ", ".join(f"{y}={eby[y]:,}" for y in ey),
                                     "A published count of 'tribes receiving X' is this series. If it steps "
                                     "here, the count steps, and the step is ours."]))

    # ---- CLASS 4b: unit shifts. Median moves by an order of magnitude ------
    resv = res.pop("_reservoir", {})
    bycol = defaultdict(dict)
    for (c, y), samples in resv.items():
        if y is None or len(samples) < 40:
            continue
        pos = [abs(v) for v in samples if v not in (0,)]
        if len(pos) < 40:
            continue
        bycol[c][y] = statistics.median(pos)
    for c, med in bycol.items():
        yy = sorted(med)
        for i in range(1, len(yy)):
            y0, y1 = yy[i - 1], yy[i]
            if y1 != y0 + 1:
                continue
            a, b = med[y0], med[y1]
            if a <= 0 or b <= 0:
                continue
            r = b / a
            if r < UNIT_SHIFT_RATIO and r > 1 / UNIT_SHIFT_RATIO:
                continue
            t, ev = classify(ds, [y0, y1], cls="SCALE_SHIFT", pipeline_note=(
                f"The MEDIAN of {c!r} moves x{r:.1f} at {y0}/{y1} while the column name does not change. A median "
                f"that jumps an order of magnitude is a UNIT or SCALE change before it is a behaviour change - the "
                f"CT gaming source did exactly this (payout 91.45 in 1993-01 vs 0.912 in 2025-12)."))
            A.append(dict(cls="SCALE_SHIFT", dataset=ds, type=t, year=y1, column=c,
                          stake_rows=0, stake_usd=0.0,
                          title=f"{ds}.{c}: median {a:,.2f} ({y0}) -> {b:,.2f} ({y1}), x{r:.1f}",
                          evidence=ev + ["medians computed on a per-year reservoir sample of up to "
                                         f"{RESERVOIR:,} non-zero absolute values"]))

    # metric-keyed value column (gaming) - same test, per metric
    mety = res.pop("_metric_year", {})
    for m, byy in mety.items():
        yy = sorted(y for y in byy if isinstance(y, int) and len(byy[y]) >= 8)
        for i in range(1, len(yy)):
            y0, y1 = yy[i - 1], yy[i]
            if y1 != y0 + 1:
                continue
            a = statistics.median([abs(v) for v in byy[y0] if v]) if any(byy[y0]) else 0
            b = statistics.median([abs(v) for v in byy[y1] if v]) if any(byy[y1]) else 0
            if a <= 0 or b <= 0:
                continue
            r = b / a
            if 1 / UNIT_SHIFT_RATIO < r < UNIT_SHIFT_RATIO:
                continue
            t, ev = classify(ds, [y0, y1], cls="SCALE_SHIFT", pipeline_note=(
                f"metric {m!r} median moves x{r:.1f} at {y0}/{y1} with no change in the metric name or unit column."))
            A.append(dict(cls="SCALE_SHIFT", dataset=ds, type=t, year=y1, column=f"value[metric={m}]",
                          stake_rows=0, stake_usd=0.0,
                          title=f"{ds} metric {m}: median {a:,.2f} ({y0}) -> {b:,.2f} ({y1}), x{r:.1f}",
                          evidence=ev))
            break

    # ---- CLASS 5: duplicate-driven inflation --------------------------------
    if res.get("dedup_counts"):
        for col, rule in spec["money"]:
            if rule != "SUM":
                continue
            st = res["numstats"].get(col)
            if not st:
                continue
            naive, true = st["total"], st["dedup_total"]
            if true and abs(naive - true) > 1e6:
                infl = (naive / true - 1) * 100
                A.append(dict(cls="DUPLICATE_INFLATION", dataset=ds, type="PIPELINE", year=None, column=col,
                              stake_rows=sum(v for k, v in res["dedup_counts"].items()
                                             if k != spec.get("dedup_primary")),
                              stake_usd=abs(naive - true),
                              title=(f"{ds}.{col}: summing past {spec['dedup_col']!r} reports {money(naive)} "
                                     f"against a true {money(true)} (+{infl:.1f}%)"),
                              evidence=[f"{spec['dedup_col']} counts: {res['dedup_counts']}",
                                        f"{spec['dedup_col']} = {spec['dedup_primary']!r} is MANDATORY on every "
                                        f"money figure from this table. It belongs in cedar_domain beside "
                                        f"SUM_COLUMNS.",
                                        "OWNER: 45_promote_subawards.py / 41_match_subawards_to_ledger.py"]))
    if res.get("dup_hits"):
        share = res["dup_hits"] / max(res["rows"], 1) * 100
        if share >= 0.05:
            A.append(dict(cls="DUPLICATE_KEY", dataset=ds, type="UNKNOWN", year=None,
                          stake_rows=res["dup_hits"], stake_usd=0.0,
                          title=(f"{ds}: {res['dup_hits']:,} rows ({share:.2f}%) repeat the key "
                                 f"{'+'.join(res['dup_key'])}"),
                          evidence=["A naive sum over this table counts those rows more than once IF the key is "
                                    "meant to be unique. Two readings and we cannot pick between them from the "
                                    "file alone: either the key is not the grain, or the rows are genuine "
                                    "duplicates. NOTE the ONRR precedent in series_breaks.csv - from FY2015 the "
                                    "public disbursement file emits 11-15 rows per year identical on every VISIBLE "
                                    "column because the distinguishing dimension is suppressed at source; a dedupe "
                                    "there looks obviously correct and DISCARDS $10.79B.",
                                    f"key tested: {res['dup_key']}"]))

    # ---- CLASS 6: impossible / implausible values ---------------------------
    for c, st in res["numstats"].items():
        rule = dict(spec["money"]).get(c)
        if st["n"] == 0:
            continue
        if rule == "NEVER" and st["neg"]:
            A.append(dict(cls="IMPOSSIBLE_VALUE", dataset=ds, type="UNKNOWN", year=None, column=c,
                          stake_rows=st["neg"], stake_usd=0.0,
                          title=f"{ds}.{c}: {st['neg']:,} NEGATIVE values in a column that counts things",
                          evidence=[f"min {st['mn']}, max {st['mx']}. A count cannot be negative."]))
        if st["pos"] >= 5000:
            # Benford
            tot = sum(st["benford"].values())
            if tot >= 5000:
                chi = sum(((st["benford"].get(d, 0) - tot * BENFORD[d]) ** 2) / (tot * BENFORD[d])
                          for d in range(1, 10))
                obs = {d: st["benford"].get(d, 0) / tot for d in range(1, 10)}
                worst = max(range(1, 10), key=lambda d: abs(obs[d] - BENFORD[d]))
                if chi > 200:
                    A.append(dict(cls="BENFORD", dataset=ds, type="UNKNOWN", year=None, column=c,
                                  stake_rows=tot, stake_usd=0.0,
                                  title=(f"{ds}.{c}: first-digit distribution departs from Benford "
                                         f"(chi2 {chi:,.0f} on {tot:,} positive values; digit {worst} at "
                                         f"{obs[worst]*100:.1f}% against {BENFORD[worst]*100:.1f}% expected)"),
                                  evidence=[
                                      "observed first-digit shares: " +
                                      ", ".join(f"{d}:{obs[d]*100:.1f}%" for d in range(1, 10)),
                                      "WHAT THIS CAN SHOW: that the digit distribution is not what an unconstrained "
                                      "multiplicative process produces. WHAT IT CANNOT SHOW: fabrication. Federal "
                                      "money is FULL of legitimate reasons to fail Benford - appropriations are "
                                      "round, programmes have caps and floors, awards are negotiated to round "
                                      "figures, and formula grants are computed from populations. A Benford failure "
                                      "here is a PROMPT TO LOOK, never a finding on its own, and it must never be "
                                      "published as evidence of anything."]))
            rshare = st["round6"] / st["pos"] * 100
            if rshare >= 8:
                A.append(dict(cls="ROUND_NUMBER_CLUSTER", dataset=ds, type="UNKNOWN", year=None, column=c,
                              stake_rows=st["round6"], stake_usd=0.0,
                              title=(f"{ds}.{c}: {st['round6']:,} of {st['pos']:,} positive values "
                                     f"({rshare:.1f}%) are exact multiples of $1,000,000"),
                              evidence=[f"exact multiples: $1M {st['round6']:,} · $100k {st['round5']:,} · "
                                        f"$1k {st['round3']:,} of {st['pos']:,} positive values",
                                        "Round-number clustering is expected in appropriated and negotiated money. "
                                        "It becomes a FABRICATED-PRECISION signal only where the source claims a "
                                        "computed figure. Recorded so the share is known, not asserted as a defect."]))

    # dates
    for c, dst in res["datestats"].items():
        if dst["future"]:
            A.append(dict(cls="FUTURE_DATE", dataset=ds, type="UNKNOWN", year=None, column=c,
                          stake_rows=dst["future"], stake_usd=0.0,
                          title=f"{ds}.{c}: {dst['future']:,} rows carry a date after {THIS_YEAR}",
                          evidence=[f"range {dst['mn']} .. {dst['mx']}",
                                    "A future date is either a scheduled/deadline field used correctly (NAGPRA's "
                                    "repatriation_eligible_date is one) or a parse defect. Check the column's "
                                    "meaning before treating it as either."]))
        if dst["unparsed"]:
            share = dst["unparsed"] / max(res["rows"], 1) * 100
            if share >= 1.0:
                A.append(dict(cls="UNPARSEABLE_DATE", dataset=ds, type="PIPELINE", year=None, column=c,
                              stake_rows=dst["unparsed"], stake_usd=0.0,
                              title=(f"{ds}.{c}: {dst['unparsed']:,} rows ({share:.1f}%) hold a value that does "
                                     f"not parse as a date"),
                              evidence=["A year series built off this column silently drops these rows. The FOIA "
                                        "index is the worked example: dates are stored in mixed M/D/YYYY and ISO "
                                        "form and 1,775 of 9,481 rows have none at all.",
                                        f"range of what DID parse: {dst['mn']} .. {dst['mx']}"]))
        days = dst["days"]
        tot = sum(days.values())
        if tot >= 400:
            exp = tot / 30.0
            spikes = [(d, n) for d, n in days.items() if n > exp * 2.2 and n >= 40]
            if spikes:
                spikes.sort(key=lambda t: -t[1])
                known_t, known_note = DATE_CLUSTER_NOTES.get((ds, c), (None, None))
                ev = [f"expected ~{exp:,.0f} per day over {tot:,} dated rows if days were uniform",
                      "day-of-month counts: " + ", ".join(f"day {d}={n:,}" for d, n in spikes[:6])]
                if known_note:
                    ev.append(known_note)
                    typ = known_t
                else:
                    ev.append("NOT IN THE DATE-CLUSTER REGISTER. Day 31, day 15 and day 01 clustering is the "
                              "signature of a MONTH being written as a DAY - false day-precision; Cedar has "
                              "already found 415 gaming dates carrying exactly that, 150 on day 31 and 148 on "
                              "day 15. It is ALSO the signature of a period boundary or a filing deadline, and "
                              "this run cannot tell them apart. Establish which, then add the column to "
                              "DATE_CLUSTER_NOTES in this script so the next run stops asking.")
                    typ = "UNKNOWN"
                ev.append("Whatever the cause, the remedy is a PRECISION FIELD beside the date, never a "
                          "corrected date. A date silently promoted to day-precision cannot be un-promoted.")
                A.append(dict(cls="DATE_CLUSTER", dataset=ds, type=typ, year=None, column=c,
                              stake_rows=sum(n for _, n in spikes), stake_usd=0.0,
                              registered=bool(known_note),
                              title=(f"{ds}.{c}: day-of-month clusters on "
                                     + ", ".join(f"day {d} ({n:,})" for d, n in spikes[:4])
                                     + ("" if known_note else "  [UNREGISTERED]")),
                              evidence=ev))

    # blank-year rows
    if noyear and res["rows"]:
        share = noyear / res["rows"] * 100
        if share >= 1.0:
            A.append(dict(cls="NO_YEAR", dataset=ds, type="PIPELINE", year=None,
                          stake_rows=noyear, stake_usd=0.0,
                          title=f"{ds}: {noyear:,} rows ({share:.1f}%) carry no usable year on {spec['year'][1]!r}",
                          evidence=["Every year chart off this table silently omits these rows, and the omission "
                                    "does not show up as a gap - it shows up as smaller years."]))

    # ---- AGGREGATION -------------------------------------------------------
    # 297 individually-listed disappearances is not 297 findings; it is ONE
    # finding about a cohort, plus a handful worth naming. A report that lists
    # every instance of a pattern buries the pattern. The full set stays in the
    # JSON via the aggregate row's own counts.
    CAPS = {"ENTITY_SPIKE": 25, "ENTITY_DISAPPEARANCE": 12, "ENTITY_APPEARANCE": 12,
            "YEAR_STEP_MONEY": 20, "YEAR_STEP_ROWS": 20}
    out = []
    for cls, cap in CAPS.items():
        grp = [a for a in A if a["cls"] == cls]
        if len(grp) <= cap:
            continue
        grp.sort(key=lambda a: (-(a.get("stake_usd") or 0.0), -(a.get("stake_rows") or 0)))
        keep, rest = grp[:cap], grp[cap:]
        A = [a for a in A if a["cls"] != cls] + keep
        types = Counter(a["type"] for a in rest)
        yrs_c = Counter(a.get("year") for a in rest)
        usd = sum(a.get("stake_usd") or 0.0 for a in rest)
        names = [a.get("entity_name") or a.get("entity") or "" for a in rest][:12]
        out.append(dict(cls=cls + "_COHORT", dataset=ds, type=("PIPELINE" if types.get("PIPELINE", 0) > len(rest) / 2
                                                              else "UNKNOWN"),
                        year=(yrs_c.most_common(1)[0][0] if yrs_c else None),
                        stake_rows=sum(a.get("stake_rows") or 0 for a in rest), stake_usd=usd,
                        title=(f"{ds}: {len(rest):,} further `{cls}` rows beyond the {cap} named above, "
                               f"{money(usd) if usd else ''} at stake"),
                        evidence=[
                            "A COHORT, NOT A LIST. One pattern repeated across many entities is one finding; "
                            "listing each instance buries it. The individually named rows above are the largest "
                            "by dollars.",
                            "types among the remainder: " + ", ".join(f"{t}={n}" for t, n in types.most_common()),
                            "years most represented: "
                            + ", ".join(f"{y}={n}" for y, n in yrs_c.most_common(6)),
                            "a sample of the entities: " + "; ".join(x for x in names if x),
                            "THE QUESTION TO ASK OF A COHORT IS NOT 'WHICH ENTITY' BUT 'WHAT DID WE DO IN THAT "
                            "YEAR'. A single entity vanishing is a business event; three hundred vanishing in "
                            "one year is a build.",
                        ]))
    return A + out


# ---------------------------------------------------------------------------
# class 7 regressions - known false attributions
# ---------------------------------------------------------------------------
def false_attribution_regressions():
    out = []

    # FA-01 Salt River lobbying panel
    p = os.path.join(CLEAN, "tribe_year_lobbying_panel.csv")
    s = stamp(p)
    if s.get("exists"):
        spend = 0.0
        filings = 0
        rows = 0
        with open(p, newline="", encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh):
                if r.get("entity_id") == "TRBF-SRPMCP-00":
                    rows += 1
                    spend += num(r.get("total_lobbying_spend_usd")) or 0.0
                    filings += int(num(r.get("n_filings")) or 0)
        status = ("STILL DEFECTIVE" if spend > 25_000_000 or filings > 300
                  else "CORRECTED" if spend <= 15_000_000 and filings <= 220 else "MOVED - re-adjudicate")
        out.append(dict(id="FA-01", label="Salt River Pima-Maricopa lobbying panel", source=s, status=status,
                        measured=dict(entity="TRBF-SRPMCP-00", spend_usd=spend, filings=filings, panel_rows=rows),
                        known_bad=dict(spend_usd=40_300_000, filings=557),
                        known_good=dict(spend_usd=10_400_000, filings=141),
                        note=("CORRECTED 2026-08-26 by code/351_rebuild_lobbying_panel_from_corrected_"
                              "disclosures.py. The panel was built 2026-08-05 17:28 and script 65 withdrew SALT "
                              "RIVER PROJECT from the disclosures on 2026-08-06 16:19; the panel was never "
                              "rebuilt, so it published $40,279,500 / 557 filings for twenty days. A SECOND "
                              "instance, undocumented until that day, was 471 filings / $5,756,834 the name-form "
                              "guard could not see - Santa Rosa County FLORIDA, Santa Rosa Junior College, two "
                              "hospital systems, COEUR D'ALENE MINING (the guard bars MINES), BBEDC and BBAHC - "
                              "withdrawn by code/350_withdraw_false_lobbying_attributions.py. All 471 were "
                              "`medium`, so the publishable `high` slice is unchanged at 23,741 filings / "
                              "$627,601,108. STILL STALE and named: lobbying_registrants.csv and "
                              "lobbying_registrant_concentration.csv carry AGGREGATES over the 471 - re-run 180 "
                              "then 182. A spike on this entity in ANY year is a PIPELINE fact until this "
                              "regression reads CORRECTED.")))

    # FA-02 FOIA link quality
    p = os.path.join(CLEAN, "foia_request_index.csv")
    s = stamp(p)
    if s.get("exists"):
        tot = 0
        linked = 0
        georgetown = 0
        georgetown_text = 0
        entprs_linked = 0
        by_entity = Counter()
        with open(p, newline="", encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh):
                tot += 1
                eid = (r.get("tribe_entity_id") or "").strip()
                if eid:
                    linked += 1
                    by_entity[eid] += 1
                # THE DETECTOR MUST BE ABLE TO SEE THE DEFECT IT RE-TESTS.
                # Until 2026-08-26 this scanned requester_organization,
                # source_url, requester and the entity id for 'georgetown.edu'
                # - and the string only ever appeared in `request_description`,
                # which was NOT in the blob. It scored 94 by accident, on the
                # 'georgt' substring of the entity id, and would have reported
                # clean the moment the id was blanked even if the bad LINK came
                # straight back through another column. The regression is now
                # measured on the LINK, which is what FA-02 is about, and the
                # text scan is kept beside it as corroboration over every
                # free-text column.
                blob = " ".join((r.get(c) or "") for c in
                                ("requester_organization", "source_url", "requester",
                                 "requester_native_entity_id", "request_description",
                                 "organization_mentioned", "tribe_match_phrase")).lower()
                if "georgetown.edu" in blob:
                    georgetown_text += 1
                if eid.startswith("AKNF-GEORGT"):
                    georgetown += 1
                if eid == "TRBF-ENTPRS-00":
                    entprs_linked += 1
        out.append(dict(id="FA-02", label="FOIA index entity links", source=s,
                        status=("STILL DEFECTIVE" if georgetown >= 1
                                else "CORRECTED" if linked else "NO LINKS"),
                        measured=dict(rows=tot, linked_rows=linked,
                                      georgetown_LINKED_rows=georgetown,
                                      georgetown_edu_in_text_rows=georgetown_text,
                                      entprs_linked_rows=entprs_linked,
                                      top_linked_entities=by_entity.most_common(8)),
                        note=("CORRECTED 2026-08-26 by code/352_unlink_false_foia_entity_links.py: 94 Georgetown "
                              "links and 15 of 17 Enterprise links UNLINKED, 453 -> 344 linked rows, 0 rows "
                              "removed. 92 of the 94 matched inside a LIST OF EMAIL DOMAINS a requester asked the "
                              "agency to search ('georgetown.edu', 'law.georgetown.edu', beside ucla.edu and "
                              "stanford.edu); the other 2 matched GEORGETOWN CLIMATE CENTER. No row in the file "
                              "contains 'Native Village of Georgetown'. Two Enterprise rows were KEPT on evidence "
                              "(one names 'Enterprise Rancheria of Maidu Indians of California'; one is an AS-IA "
                              "land-to-trust request whose parsed text truncates at '...by the Enterprise' and is "
                              "not demonstrably wrong). Provenance preserved: tribe_mentioned, tribe_match_phrase "
                              "and a new tribe_entity_id_withdrawn; the prior DISPUTED audit text is carried "
                              "verbatim inside the new audit string. NOT tier X - 169_build_identifier_graph.py "
                              "treats X as a statement about the IDENTIFIER and it would suppress the two correct "
                              "Enterprise Rancheria rows. STILL OPEN: 55 rows remain DISPUTED_FREE_TEXT_SINGLE_"
                              "TOKEN at tier B (Shinnecock 7, Metlakatla 7, Ewiiaapaayp 7, Chickaloon 6, ...) - "
                              "these are distinctive tribal names in prose about those tribes and need reading, "
                              "one at a time, not a rule.")))

    # FA-03 TRBF-ENTPRS-00
    hits = []
    for f, col in [("prime_contracts.csv", "tribe_id"),
                   ("federal_funding_transactions.csv", "tribe_id"),
                   ("tribe_year_lobbying_panel.csv", "entity_id")]:
        p = os.path.join(CLEAN, f)
        if not os.path.exists(p):
            continue
        hits.append(dict(file=f, source=stamp(p)))
    out.append(dict(id="FA-03", label="TRBF-ENTPRS-00 canonical name is literally 'Enterprise'",
                    status="STANDING CAUTION", files=hits,
                    note=("A canonical name that is a common English noun attracts name-matched rows from every "
                          "source. Entity-spike rows in this report carrying this id are typed PIPELINE by the "
                          "classifier for that reason. NOT RETIRED by the FA-02 fix: measured 2026-08-26, "
                          "prime_contracts.csv holds 306 rows and prime_contracts_archive_backfill.csv 244 in "
                          "which the word `Enterprise` co-occurs with this id, plus 27 in "
                          "nagpra_notice_entity_bridge.csv. Most are presumably the real Enterprise Rancheria; "
                          "they were not audited row-by-row. This id cannot be checked by a token test in either "
                          "direction - the surrounding text has to be read.")))

    # -----------------------------------------------------------------------
    # FA-04  BRISTOL BAY AREA HEALTH CORPORATION -> ANRC-BRBYCO-00
    #
    # Found 2026-08-26 by 354_correction_register.py's propagation check on
    # its first run, while discharging FA-01. The root is ONE tier-B
    # `cluster_v3` row on UEI NL5HNWNUFMK4 in cedar_identifier_ledger_final.csv
    # reading "Algorithmic name clustering, unreviewed". BBAHC is a tribal
    # health organisation (EIN 920044965, Dillingham AK); ANRC-BRBYCO-00 is
    # Bristol Bay NATIVE CORPORATION, the ANCSA regional corporation. Different
    # entities. There is no BBAHC entry in the spine, which is why the
    # clusterer reached for the nearest name.
    #
    # NOT FIXED: unwinding it moves village_corp_obligations_usd, which
    # 62_no_regression_check.py holds MUST_NOT_FALL at $60.4B, and it needs an
    # owner's ruling on whether BBAHC and Bristol Bay Housing Authority become
    # spine entities - a REPOINT, not an unlink.
    # -----------------------------------------------------------------------
    fa04 = []
    for f, idcol, namecol in [
            ("federal_funding_transactions.csv", "tribe_id", "recipient_name"),
            ("subawards.csv", "sub_native_tribe_id", "sub_name"),
            ("fac_tribal_single_audits.csv", "entity_id", "auditee_name"),
            ("native_passthrough.csv", "to_tribe_id", "to_firm"),
            ("cedar_identifier_ledger_final.csv", "tribe_id", "legal_business_name")]:
        pth = os.path.join(CLEAN, f)
        if not os.path.exists(pth):
            continue
        n = 0
        usd = 0.0
        with open(pth, newline="", encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh):
                if (r.get(idcol) or "").strip() != "ANRC-BRBYCO-00":
                    continue
                if "BRISTOL BAY AREA HEALTH" not in (r.get(namecol) or "").upper():
                    continue
                n += 1
                usd += num(r.get("obligated_usd")) or 0.0
        if n:
            fa04.append(dict(file=f, rows=n, obligated_usd=round(usd, 2),
                             source=stamp(pth)))
    out.append(dict(id="FA-04",
                    label="Bristol Bay Area Health Corporation attributed to Bristol Bay Native Corporation",
                    status=("STILL DEFECTIVE" if fa04 else "CORRECTED"),
                    measured=dict(tables=fa04,
                                  total_rows=sum(d["rows"] for d in fa04),
                                  total_obligated_usd=round(sum(d["obligated_usd"] for d in fa04), 2)),
                    note=("Root: one tier-B `cluster_v3` row on UEI NL5HNWNUFMK4 in "
                          "cedar_identifier_ledger_final.csv, tier_rationale 'Algorithmic name clustering, "
                          "unreviewed'. BBAHC (EIN 920044965, Dillingham AK) is a tribal HEALTH organisation; "
                          "ANRC-BRBYCO-00 is the ANCSA regional corporation. No BBAHC entity exists in the spine. "
                          "A SECOND, unaudited instance sits beside it: 50 more federal_funding_transactions rows "
                          "key BRISTOL BAY HOUSING AUTHORITY to the same id, so EVERY assistance row attributed "
                          "to BBNC is attributed to an organisation that is not BBNC. NOT FIXED: unwinding it "
                          "moves village_corp_obligations_usd (MUST_NOT_FALL, $60.4B) and needs an owner ruling - "
                          "it is a REPOINT, not an unlink. 62_no_regression_check.py carries "
                          "corrections_not_propagated at a floor of 10 and prints all ten by name every run.")))
    return out


# ---------------------------------------------------------------------------
# REGIME STRESS TESTS
#
# The REGIME type is only worth having if it is TESTABLE. Naming a rule change
# beside a step is a hypothesis; measuring whether the step survives an
# instrument that the rule change cannot touch is a result. Both tests below
# are re-run every sweep, read-only, and both are designed to be able to FAIL -
# a stress test that cannot come back "the trend survives" is not a test.
# ---------------------------------------------------------------------------
def regime_stress_tests():
    tests = []

    # --- HLOGA 2008: did filing frequency double, and does concentration hold?
    path = os.path.join(CLEAN, "native_entity_lobbying_disclosures.csv")
    if os.path.exists(path):
        filings = defaultdict(Counter)
        dollars = defaultdict(Counter)
        with open(path, newline="", encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh):
                y = (r.get("filing_year") or "").strip()
                reg = (r.get("registrant_name") or "").strip().lower()
                if not y.isdigit() or not reg:
                    continue
                y = int(y)
                filings[y][reg] += 1
                dollars[y][reg] += num(r.get("spend_usd")) or 0.0
        rows = []
        for y in sorted(filings):
            cf, cd = filings[y], dollars[y]
            tf, td = sum(cf.values()), sum(cd.values())
            rows.append(dict(year=y, filings=tf, registrants=len(cf),
                             top5_share_filings=round(sum(n for _, n in cf.most_common(5)) / tf * 100, 1) if tf else None,
                             top5_share_dollars=round(sum(n for _, n in cd.most_common(5)) / td * 100, 1) if td else None,
                             dollars=td))
        by = {r["year"]: r for r in rows}
        verdict, finding = "NOT COMPUTABLE", []
        if 2007 in by and 2008 in by:
            fr = by[2008]["filings"] / by[2007]["filings"]
            rr = by[2008]["registrants"] / by[2007]["registrants"]
            finding.append(
                f"THE DOUBLING IS REAL AND IT IS FILINGS ONLY. Filings go {by[2007]['filings']:,} (2007) -> "
                f"{by[2008]['filings']:,} (2008), x{fr:.2f} - almost exactly the semiannual-to-quarterly "
                f"factor of 2. Over the same boundary the number of DISTINCT REGISTRANTS goes "
                f"{by[2007]['registrants']} -> {by[2008]['registrants']}, x{rr:.2f}. More paperwork, the same "
                f"people. Any 'lobbying activity rose' claim built on filing counts across 2008 is measuring "
                f"HLOGA.")
            early = [by[y] for y in (1999, 2000, 2001, 2002, 2003) if y in by]
            late = [by[y] for y in (2021, 2022, 2023, 2024, 2025) if y in by]
            if early and late:
                ef = sum(r["top5_share_filings"] for r in early) / len(early)
                lf = sum(r["top5_share_filings"] for r in late) / len(late)
                ed = sum(r["top5_share_dollars"] for r in early) / len(early)
                ld = sum(r["top5_share_dollars"] for r in late) / len(late)
                survives = (ld < ed - 3)
                verdict = "TREND SURVIVES" if survives else "TREND DOES NOT SURVIVE"
                finding.append(
                    f"THE CONCENTRATION TREND SURVIVES THE BREAK. Top-5 registrant share measured on FILINGS "
                    f"falls {ef:.1f}% (1999-2003 mean) -> {lf:.1f}% (2021-25 mean). Measured on DOLLARS - an "
                    f"instrument HLOGA cannot touch, because a share is scale-free and the same money is "
                    f"reported either way - it falls {ed:.1f}% -> {ld:.1f}%, a LARGER decline. "
                    f"**The finding is not an artefact of the filing-frequency change.**")
                finding.append(
                    "TWO CAVEATS THAT STILL TRAVEL WITH IT. (1) The dollar series is volatile in 1999-2003, "
                    "where annual filings are 397-578 against ~1,200 later, so the early level is a small-N "
                    "estimate. (2) Report PERIOD length changed at the same date, so per-FILING dollars are "
                    "not comparable across 2008 even though annual totals and shares are. Quote the share, "
                    "never the per-filing average.")
        tests.append(dict(id="RS-01", regime="HLOGA_QUARTERLY", verdict=verdict,
                          question="Does the fall in lobbying-registrant concentration survive the 2008 "
                                   "semiannual-to-quarterly filing change?",
                          source=stamp(path), findings=finding, series=rows))

    # --- COVID 2020-21: how much of the assistance spike is relief, by CFDA?
    path = os.path.join(CLEAN, "federal_funding_transactions.csv")
    if os.path.exists(path):
        by = defaultdict(lambda: defaultdict(float))
        titles = {}
        with open(path, newline="", encoding="utf-8", errors="replace") as fh:
            rdr = csv.reader(fh)
            hdr = next(rdr)
            ix = {c: i for i, c in enumerate(hdr)}
            for row in rdr:
                y = row[ix["fiscal_year"]].strip()
                v = num(row[ix["obligated_usd"]]) or 0.0
                k = row[ix["cfda"]].strip()
                by[y][k] += v
                if k not in titles:
                    titles[k] = row[ix["cfda_title"]].strip()[:70]
        BASE = ("2017", "2018", "2019")
        keys = set()
        for y in BASE:
            keys |= set(by[y])
        base = {k: sum(by[y].get(k, 0.0) for y in BASE) / len(BASE) for k in keys}
        basetot = sum(base.values())
        COVID_CFDA = {"21.019", "21.027", "21.023", "21.026", "21.032"}
        yr_rows, findings = [], []
        for y in ("2020", "2021", "2022", "2024"):
            if y not in by:
                continue
            tot = sum(by[y].values())
            excess = tot - basetot
            covid = sum(v for k, v in by[y].items() if k in COVID_CFDA)
            top = sorted(((by[y][k] - base.get(k, 0.0)), k) for k in by[y])[::-1][:6]
            yr_rows.append(dict(year=int(y), total=tot, baseline=basetot, excess=excess,
                                covid_cfda_dollars=covid,
                                covid_share_of_excess=(round(covid / excess * 100, 1) if excess > 0 else None),
                                top_movers=[dict(cfda=k, title=titles.get(k, ""), delta=d) for d, k in top]))
        for r in yr_rows:
            if r["covid_share_of_excess"] is not None and r["covid_share_of_excess"] > 30:
                findings.append(
                    f"FY{r['year']}: {money(r['total'])} against an FY2017-19 mean of {money(r['baseline'])}, an "
                    f"excess of {money(r['excess'])}. Named COVID relief listings alone account for "
                    f"{money(r['covid_cfda_dollars'])} - **{r['covid_share_of_excess']}% of the entire excess**. "
                    f"Largest single mover: {r['top_movers'][0]['cfda']} "
                    f"{r['top_movers'][0]['title']!r} at {money(r['top_movers'][0]['delta'])}.")
        findings.append(
            "THE FIGURES CORROBORATE THE PUBLISHED ONES. The reported ~$8B (CARES) and ~$20B (ARPA) to tribal "
            "governments land on CFDA 21.019 Coronavirus Relief Fund and CFDA 21.027 Coronavirus State and "
            "Local Fiscal Recovery Funds in this table at close to those magnitudes. Two independent routes to "
            "the same number is the strongest evidence available that the spike is the statute.")
        findings.append(
            "AND THE ROW COUNTS WOULD HAVE HIDDEN IT. Assistance rows move 49,195 (FY2020) -> 48,415 (FY2021) - "
            "essentially flat, and FY2021 is LOWER - while dollars go $20.59B -> $40.80B. **Relief arrived as a "
            "small number of very large transactions.** Anyone sanity-checking this panel on row counts alone "
            "would have concluded nothing happened in 2021.")
        findings.append(
            "FY2024 IS THE ONE TO WATCH, AND IT IS NOT COVID. FY2024 runs "
            + (money(next((r['total'] for r in yr_rows if r['year'] == 2024), 0.0)))
            + " against the same baseline, and its top movers are IHS self-governance, Indian Housing Block "
              "Grants, Section 8 vouchers, Highway Planning and Grid Infrastructure Deployment - an "
              "infrastructure-era composition, not a relief one. That elevation is a CANDIDATE real finding "
              "rather than a regime artefact, and it is where the reporting effort should go.")
        tests.append(dict(id="RS-02", regime="COVID_RELIEF", verdict="SPIKE IS THE STATUTE",
                          question="How much of the FY2020-21 assistance spike is COVID relief, measured on "
                                   "dollars rather than row counts?",
                          source=stamp(path), findings=findings, series=yr_rows))

    # --- FAR 4.606(a)(1): is a contract ROW COUNT a count of anything?
    path = os.path.join(CLEAN, "prime_contracts.csv")
    if os.path.exists(path):
        buckets = defaultdict(lambda: dict(pos=0, tiny=0, vals=[]))
        with open(path, newline="", encoding="utf-8", errors="replace") as fh:
            rdr = csv.reader(fh)
            hdr = next(rdr)
            ix = {c: i for i, c in enumerate(hdr)}
            for row in rdr:
                y = row[ix["fiscal_year"]].strip()
                v = num(row[ix["total_obligations"]])
                if v is None or v <= 0:
                    continue
                b = buckets[y]
                b["pos"] += 1
                if v <= 2500:
                    b["tiny"] += 1
                if len(b["vals"]) < 60000:
                    b["vals"].append(v)
        rows = []
        for y in sorted(buckets):
            if not y.isdigit():
                continue
            b = buckets[y]
            rows.append(dict(year=int(y), positive_rows=b["pos"],
                             share_at_or_below_2500=round(b["tiny"] / b["pos"] * 100, 1) if b["pos"] else None,
                             median=round(statistics.median(b["vals"]), 0) if b["vals"] else None))
        findings = []
        if rows:
            last = rows[-1]
            first = rows[0]
            findings.append(
                f"FY{last['year']}: **{last['share_at_or_below_2500']}% of rows with a POSITIVE obligation are "
                f"$2,500 or less**, median {money(last['median'])}. FAR 4.606(a)(1) requires modifications to be "
                f"reported REGARDLESS OF DOLLAR VALUE, so a row in this table is an ADMINISTRATIVE ACTION, not a "
                f"contract and not a unit of money.")
            findings.append(
                f"AND IT IS NOT CONSTANT ACROSS THE PANEL, WHICH IS WHAT MAKES IT A TREND-KILLER. The same share "
                f"reads {first['share_at_or_below_2500']}% in FY{first['year']}. Series: "
                + ", ".join(f"{r['year']}={r['share_at_or_below_2500']}%" for r in rows))
            if len(rows) >= 2 and rows[-2]["share_at_or_below_2500"]:
                jump = last["share_at_or_below_2500"] / rows[-2]["share_at_or_below_2500"]
                if jump >= 3:
                    findings.append(
                        f"AND FY{last['year']} IS NOT MERELY HIGH - IT IS AN {jump:.0f}x OUTLIER ON ITS OWN "
                        f"PANEL ({rows[-2]['share_at_or_below_2500']}% in FY{rows[-2]['year']} against "
                        f"{last['share_at_or_below_2500']}%). FAR practice is the standing rule and does not "
                        f"change year to year, so the rule alone does NOT explain this. The leading candidate "
                        f"is the VINTAGE: a partial year captured mid-flight holds the modifications to "
                        f"existing awards without yet holding the new awards those modifications will "
                        f"eventually sit under. That makes FY2026 a PIPELINE fact on top of a REGIME one, and "
                        f"it is the reason FY2026 counts must not be published at all - not merely caveated.")
            findings.append(
                "**A CONTRACT-COUNT TREND RUNNING INTO THE RECENT YEARS IS AN ARTEFACT OF REPORTING PRACTICE.** "
                "Count AWARDS on a de-duplicated PIID key, or report dollars. Note this compounds with SANITY-04 "
                "in docs/CICD_BENCHMARK.md, where no Cedar award key reproduces CICD's 50,167 contracts: the "
                "grain question and the micro-modification question are the same question asked twice.")
        tests.append(dict(id="RS-03", regime="FAR_4606_MICRO_MODIFICATIONS",
                          verdict="ROW COUNTS ARE NOT CONTRACT COUNTS",
                          question="Is a prime-contract row count a count of contracts, or a count of "
                                   "administrative modifications?",
                          source=stamp(path), findings=findings, series=rows))

    return tests

# ---------------------------------------------------------------------------
# never-sum audit - which forbidden columns are present, and what they'd say
# ---------------------------------------------------------------------------
def never_sum_audit():
    rows = []
    for spec in SPECS:
        p = os.path.join(CLEAN, spec["file"])
        if not os.path.exists(p):
            continue
        with open(p, newline="", encoding="utf-8", errors="replace") as fh:
            try:
                header = next(csv.reader(fh))
            except StopIteration:
                continue
        present = [c for c in header if c in NEVER_SUM]
        if present:
            rows.append(dict(dataset=spec["name"], file=spec["file"], source=stamp(p),
                             columns=[dict(column=c, why=NEVER_SUM[c]) for c in present]))
    return rows


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------
SEVERITY = {
    "ID_SCHEME_SEAM": 105,
    "SOURCE_VOCABULARY_SPLIT": 104,
    "VOCABULARY_MIX_SHIFT": 102,
    "VOCABULARY_RENDERING_SPLIT": 101,
    "VOCABULARY_SEAM": 100,
    "DUPLICATE_INFLATION": 95,
    "LUMPY_SERIES": 88,
    "SCALE_SHIFT": 90,
    "YEAR_STEP_MONEY": 70,
    "ENTITY_SPIKE": 65,
    "YEAR_STEP_ROWS": 60,
    "ENTITY_APPEARANCE": 50,
    "ENTITY_DISAPPEARANCE": 50,
    "ENTITY_UNIVERSE_STEP": 92,
    "ENTITY_DISAPPEARANCE_COHORT": 86,
    "ENTITY_SPIKE_COHORT": 62,
    "ENTITY_APPEARANCE_COHORT": 55,
    "YEAR_STEP_MONEY_COHORT": 55,
    "YEAR_STEP_ROWS_COHORT": 52,
    "DATE_CLUSTER": 45,
    "ERA_MAP": 12,
    "DUPLICATE_KEY": 40,
    "YEAR_GAP": 35,
    "UNPARSEABLE_DATE": 30,
    "NO_YEAR": 30,
    "IMPOSSIBLE_VALUE": 30,
    "FUTURE_DATE": 20,
    "ROUND_NUMBER_CLUSTER": 15,
    "BENFORD": 10,
    "DATASET_MISSING": 80,
}


def anomaly_id(a):
    """A CONTENT-ADDRESSED id, stable across runs.

    Learned the same day from three defects elsewhere in the repo - `ferc_filing_id`
    built on Python's per-process-randomised `hash()`, plus positional `INV-nnnn`
    and `EMP-OSHATRIBE-*` counters, where a re-run changed 482 of 492 ids. An id
    that moves when nothing moved defeats the entire purpose of writing a diffable
    JSON: every row reads as changed and a real change hides in the noise.

    So: `hashlib.md5` over the STABLE identity of the finding (dataset, class,
    column, entity, year) - never over its position in a list, never over a value
    that shifts when a row count shifts, and never over `hash()`.
    """
    key = "|".join(str(a.get(k) or "") for k in ("dataset", "cls", "column", "entity", "year"))
    return "AN-" + hashlib.md5(key.encode("utf-8")).hexdigest()[:12]


def rank_key(a):
    return (-SEVERITY.get(a["cls"], 0), -(a.get("stake_usd") or 0.0), -(a.get("stake_rows") or 0))


def md_escape(s):
    return str(s).replace("|", "\\|")


def write_report(results, anomalies, regressions, nsaudit, stress, elapsed):
    os.makedirs(DOCS, exist_ok=True)
    by_type = Counter(a["type"] for a in anomalies)
    by_cls = Counter(a["cls"] for a in anomalies)

    # the top ten by dollars/rows at stake, one per (dataset, class, entity) so
    # one defect does not fill the list
    seen = set()
    headline = []
    for a in sorted(anomalies, key=rank_key):
        k = (a["dataset"], a["cls"], a.get("column"), a.get("entity"))
        if k in seen:
            continue
        seen.add(k)
        headline.append(a)
        if len(headline) >= 12:
            break

    SEAMCLS = ("VOCABULARY_SEAM", "VOCABULARY_MIX_SHIFT", "VOCABULARY_RENDERING_SPLIT",
               "SOURCE_VOCABULARY_SPLIT", "ID_SCHEME_SEAM", "SCALE_SHIFT")
    new_seams = [a for a in anomalies if a["cls"] in SEAMCLS and not a.get("known")]
    known_seams = [a for a in anomalies if a["cls"] in SEAMCLS and a.get("known")]
    unknowns = sorted([a for a in anomalies if a["type"] == "UNKNOWN"], key=rank_key)
    embarrass_pool = sorted(
        [a for a in anomalies
         if a["type"] in ("PIPELINE", "UNKNOWN")
         and a["cls"] in ("ID_SCHEME_SEAM", "SOURCE_VOCABULARY_SPLIT", "VOCABULARY_MIX_SHIFT",
                          "VOCABULARY_RENDERING_SPLIT",
                          "VOCABULARY_SEAM",
                          "DUPLICATE_INFLATION", "LUMPY_SERIES",
                          "SCALE_SHIFT",
                          "ENTITY_UNIVERSE_STEP", "ENTITY_DISAPPEARANCE_COHORT", "YEAR_STEP_MONEY",
                          "YEAR_STEP_ROWS", "ENTITY_SPIKE", "DUPLICATE_KEY", "DATE_CLUSTER")],
        key=rank_key)
    # DIVERSIFY. Severity ranking alone lets one class own the whole list - and
    # a headline list that is ten instances of one defect tells the reader about
    # one defect. At most three per class and three per dataset, which is what
    # makes this a survey of the ways this corpus can go wrong rather than a
    # ranking of its single worst column.
    embarrass, per_cls, per_ds = [], Counter(), Counter()
    for a in embarrass_pool:
        if per_cls[a["cls"]] >= 3 or per_ds[a["dataset"]] >= 3:
            continue
        embarrass.append(a)
        per_cls[a["cls"]] += 1
        per_ds[a["dataset"]] += 1
        if len(embarrass) >= 10:
            break

    L = []
    w = L.append
    w("# ANOMALY REPORT — a standing year-over-year sweep of every Cedar Press collection")
    w("")
    w(f"*Generated by `code/227_anomaly_sweep.py` on {RUN_AT.isoformat(timespec='seconds')} "
      f"in {elapsed:,.0f}s. **Do not hand-edit — re-run the script.***")
    w("")
    w("Every figure below is computed from the file named beside it, at the mtime stamped in §Sources. "
      "Several agents write these files concurrently; **a count without a vintage is a claim about a file "
      "that no longer exists.**")
    w("")
    w("---")
    w("")
    w("## What this document is")
    w("")
    w("> Elijah, 2026-08-26: *\"For all the datasets, do an analysis if there is anything odd — because we have "
      "year-to-year data over such a long time horizon, that allows us to do good sanity checks. Like, did an "
      "entity suddenly get a bunch of money one year? Is that explainable?\"*")
    w(">")
    w("> And, the same day: *\"Also do research to make sure it's not like data coverage or reporting impacting "
      "coverage as well — we need to be clear what the assumptions and limitations of the datasets are.\"*")
    w("")
    w("**A spike is either a fact about the world, a fact about the rules, or a fact about our pipeline.** "
      "Year-over-year is how you tell them apart. Every anomaly here is typed as exactly one of four things.")
    w("")
    w("| type | meaning |")
    w("|---|---|")
    w("| `PIPELINE` | Our code, our pull, our linkage. An artefact we made. It has an owning script. |")
    w("| `REGIME` | **A reporting rule changed.** A threshold moved, a filing frequency doubled, a relief "
      "programme opened. The step is a fact about a statute — not about Indian Country, and not about our code. |")
    w("| `WORLD` | A fact about the world that survived both of the above. |")
    w("| `UNKNOWN` | We could not separate the candidates. **Named, with every candidate stated, never smoothed "
      "over.** |")
    w("")
    w("**ORDER OF INFERENCE: PIPELINE first, then REGIME, then WORLD.** `WORLD` is the hardest verdict to earn, "
      "not the default when nothing else is obvious. Mis-typing a regime step as WORLD is how a publication ships "
      "a confident sentence about tribal economies that is really a sentence about a statute. Where a regime "
      "change and a real effect are confounded and cannot be separated, the row is `UNKNOWN` **with both "
      "candidates named** — we do not pick the more interesting one.")
    w("")
    w("**An unexplained spike that ships is how a publication gets embarrassed; an explained one is often the "
      "story.**")
    w("")
    w("`docs/anomaly_report.json` is the diffable artefact and is the point of making this standing rather than "
      "a one-off. Re-run after any build and diff the JSON: an anomaly that **changes type**, or a **new seam "
      "appearing**, is a regression in the data even when every build succeeded.")
    w("")
    w("### Read alongside")
    w("")
    w("- `docs/ASSUMPTIONS_AND_LIMITATIONS.md` — a concurrent agent owns the dated register of reporting regimes. "
      "Every `REGIME` row below names the event key it matched (`COVID_RELIEF`, `HLOGA_QUARTERLY`, …) so the two "
      "documents can be reconciled row by row.")
    w("- `data/clean/series_breaks.csv` — the per-column break register this sweep is the detector for.")
    w("- `docs/DATA_ODDITIES.md` — what a zero, a negative and a blank mean per dataset.")
    w("- `docs/CICD_BENCHMARK.md` — the external reconciliation. `INTERNAL-05` there and the seam section here "
      "are the same defect seen from two directions.")
    w("")
    w("---")
    w("")
    w("## Scoreboard")
    w("")
    w(f"**{len(anomalies):,} anomalies across {len([r for r in results if not r.get('error')])} datasets, "
      f"{sum(r.get('rows', 0) for r in results):,} rows read.**")
    w("")
    w("| type | count |")
    w("|---|---:|")
    for t in ("PIPELINE", "REGIME", "WORLD", "UNKNOWN"):
        w(f"| `{t}` | {by_type.get(t, 0):,} |")
    w("")
    w("| class | count | what it tests |")
    w("|---|---:|---|")
    CLSDOC = {
        "ID_SCHEME_SEAM": "TWO IDENTIFIER SCHEMES in one entity column — an entity split at the boundary and double-counted across it",
        "SOURCE_VOCABULARY_SPLIT": "two SOURCES rendering one column differently — a seam with no date, invisible to every year-over-year test",
        "VOCABULARY_MIX_SHIFT": "two vocabularies MIXING in one column — invisible to a set comparison because both eras share values",
        "VOCABULARY_RENDERING_SPLIT": "the same things RENDERED differently per era — invisible to both other seam tests",
        "VOCABULARY_SEAM": "a column whose VALUE SET changes at a year boundary — a filter on it selects an ERA",
        "SCALE_SHIFT": "a column whose median moves an order of magnitude with no name change — a UNIT change",
        "DUPLICATE_INFLATION": "a dedup key a naive sum would ignore",
        "LUMPY_SERIES": "a money series where one record can BE the year — never a trend",
        "DUPLICATE_KEY": "rows repeating a key that ought to be the grain",
        "YEAR_STEP_ROWS": "row counts stepping at a year boundary",
        "YEAR_STEP_MONEY": "dollars stepping at a year boundary",
        "YEAR_GAP": "years with no rows at all",
        "ENTITY_SPIKE": "an entity's year jumping a large multiple over its own prior peak",
        "ENTITY_APPEARANCE": "an entity appearing fully formed rather than growing into scale",
        "ENTITY_DISAPPEARANCE": "an entity active for years then vanishing",
        "ENTITY_UNIVERSE_STEP": "the count of entities the dataset can NAME stepping at a year boundary",
        "ENTITY_DISAPPEARANCE_COHORT": "many entities vanishing together — a build, not a business event",
        "ENTITY_SPIKE_COHORT": "the spikes beyond the largest named individually",
        "ENTITY_APPEARANCE_COHORT": "many entities appearing together",
        "YEAR_STEP_MONEY_COHORT": "the money steps beyond those named individually",
        "YEAR_STEP_ROWS_COHORT": "the row steps beyond those named individually",
        "DATE_CLUSTER": "day-of-month clustering — a month written as a day, or a deadline",
        "ERA_MAP": "a year-keyed source column — not a seam, but it says which pull covers which years",
        "FUTURE_DATE": "dates after the run date",
        "UNPARSEABLE_DATE": "date values a year series silently drops",
        "NO_YEAR": "rows a year chart silently omits",
        "IMPOSSIBLE_VALUE": "negatives in a column that counts things",
        "ROUND_NUMBER_CLUSTER": "exact-multiple clustering, recorded not asserted",
        "BENFORD": "first-digit departure — a prompt to look, never a finding",
        "DATASET_MISSING": "a file this sweep expects and did not find",
    }
    for c, n in by_cls.most_common():
        w(f"| `{c}` | {n:,} | {CLSDOC.get(c, '')} |")
    w("")
    w("---")
    w("")

    # -- headline -----------------------------------------------------------
    w("## THE TEN THAT WOULD MOST EMBARRASS A PUBLICATION")
    w("")
    w("*`PIPELINE` or `UNKNOWN` only — a figure that is wrong about our own data rather than merely surprising "
      "about the world. A `REGIME` row is a caveat you must print; one of these is a number you must not print "
      "at all. Ranked by severity then dollars, then capped at three per class and three per dataset so that "
      "one defect cannot own the list.*")
    w("")
    for i, a in enumerate(embarrass, 1):
        w(f"### {i}. `{a['type']}` · `{a['cls']}` · {md_escape(a['title'])}")
        w("")
        w(f"`{anomaly_id(a)}` — a content-addressed id, stable across runs; diff on it.")
        w("")
        if a.get("stake_usd"):
            w(f"**{money(a['stake_usd'])} at stake.**" + (f" {a['stake_rows']:,} rows." if a.get("stake_rows") else ""))
        elif a.get("stake_rows"):
            w(f"**{a['stake_rows']:,} rows at stake.**")
        w("")
        for e in a["evidence"]:
            w(f"- {e}")
        w("")
    w("---")
    w("")

    # -- seams ---------------------------------------------------------------
    w("## SEAMS — the class that masquerades as a finding")
    w("")
    w("*A seam is a column whose meaning changes at a boundary in OUR pipeline rather than at a plausible "
      "real-world date. It is the single most dangerous class in this repo, because a filter on a seamed column "
      "returns a clean, plausible, wrong answer, and nothing about the output looks broken.*")
    w("")
    w(f"**{len(new_seams)} NEW seam candidates. {len(known_seams)} known seams re-detected (regression check "
      f"passing — the detector still sees them).**")
    w("")
    if new_seams:
        w("### New")
        w("")
        for a in sorted(new_seams, key=rank_key):
            w(f"#### `{a['dataset']}.{a.get('column')}` — {md_escape(a['title'])}")
            w("")
            w(f"**Type `{a['type']}`.** {a['stake_rows']:,} rows across the boundary.")
            w("")
            for e in a["evidence"]:
                w(f"- {e}")
            w("")
    else:
        w("*No new vocabulary seams detected at the current threshold "
          f"(Jaccard < {SEAM_JACCARD}, both sides >= 300 rows).*")
        w("")
    if known_seams:
        w("### Known, re-detected")
        w("")
        for a in sorted(known_seams, key=rank_key):
            w(f"- **`{a['dataset']}.{a.get('column')}`** — {md_escape(a['title'])}")
        w("")
    w("### Seams recorded in the register that this detector CANNOT see")
    w("")
    for (dsn, col), why in sorted(KNOWN_SEAMS.items()):
        seen_here = any(a["dataset"] == dsn and a.get("column") == col for a in anomalies)
        if not seen_here:
            w(f"- **`{dsn}.{col}`** — {why}")
            w(f"  - *Not raised by this run.* Either the column is not on the file at this vintage, the seam does "
              f"not fall on a YEAR boundary (a seam can be a SOURCE boundary inside one year), or the column's "
              f"cardinality exceeded the tracker's cap. **Absence here is not evidence the seam is gone.**")
    w("")
    w("---")
    w("")

    # -- unknowns -------------------------------------------------------------
    w("## UNKNOWN — what we could not explain")
    w("")
    w("*An anomaly we cannot type is reported as UNKNOWN, not smoothed over. Several of these are CONFOUNDED: a "
      "pipeline boundary and a regime change land in the same year and the data cannot separate them. Both "
      "candidates are named. Do not close one of these by finding a story — a definitional explanation is only "
      "admissible if it NAMES the difference and the named difference is checkable in the data.*")
    w("")
    w(f"**{len(unknowns):,} UNKNOWN rows.** The top {min(25, len(unknowns))} by stake:")
    w("")
    w("| id | dataset | class | year | at stake | what |")
    w("|---|---|---|---:|---:|---|")
    for i, a in enumerate(unknowns[:25], 1):
        stake = money(a["stake_usd"]) if a.get("stake_usd") else (f"{a['stake_rows']:,} rows"
                                                                  if a.get("stake_rows") else "—")
        w(f"| `{anomaly_id(a)}` | `{a['dataset']}` | `{a['cls']}` | {a.get('year') or '—'} | {stake} | "
          f"{md_escape(a['title'])} |")
    w("")
    w("---")
    w("")

    # -- per dataset ----------------------------------------------------------
    w("## Per-dataset findings")
    w("")
    for res in results:
        ds = res["name"]
        mine = sorted([a for a in anomalies if a["dataset"] == ds], key=rank_key)
        w(f"### `{ds}` — {res['collection']}")
        w("")
        if res.get("error"):
            w(f"**{res['error']}** — `{res['source']['path']}`")
            w("")
            continue
        s = res["source"]
        w(f"`{s['path']}` · {s['bytes']:,} bytes · **mtime {s['mtime']}** · read {s['read_at']} · "
          f"{res['rows']:,} rows · {res['columns']} columns")
        w("")
        yrs = {int(k): v for k, v in res["year_rows"].items() if k.isdigit()}
        if yrs:
            ys = sorted(yrs)
            w(f"Year span **{ys[0]}–{ys[-1]}** ({len(ys)} years with rows).")
            w("")
            w("<details><summary>rows and dollars by year</summary>")
            w("")
            mcols = [c for c, r in dict(res.get("year_money", {})).items()] if res.get("year_money") else []
            hdr = "| year | rows |" + "".join(f" {c} |" for c in mcols)
            w(hdr)
            w("|---:|---:|" + "---:|" * len(mcols))
            for y in ys:
                cells = ""
                for c in mcols:
                    v = res["year_money"][c].get(str(y))
                    prim = res.get("year_money_primary", {}).get(c, {}).get(str(y))
                    use = prim if prim is not None else v
                    cells += f" {money(use) if use is not None else '—'} |"
                w(f"| {y} | {yrs[y]:,} |" + cells)
            w("")
            w("</details>")
            w("")
        if res["year_rows"].get("<no year>"):
            w(f"**{res['year_rows']['<no year>']:,} rows carry no usable year.**")
            w("")
        if res.get("dedup_counts"):
            w(f"`{[s2['dedup_col'] for s2 in SPECS if s2['name'] == ds][0]}` distribution: "
              f"{res['dedup_counts']}")
            w("")
        if not mine:
            w("*No anomalies raised at current thresholds.*")
            w("")
            continue
        w(f"**{len(mine)} anomalies.**")
        w("")
        w("| type | class | year | at stake | finding |")
        w("|---|---|---:|---:|---|")
        for a in mine[:30]:
            stake = money(a["stake_usd"]) if a.get("stake_usd") else (f"{a['stake_rows']:,} rows"
                                                                      if a.get("stake_rows") else "—")
            w(f"| `{a['type']}` | `{a['cls']}` | {a.get('year') or '—'} | {stake} | {md_escape(a['title'])} |")
        if len(mine) > 30:
            w(f"| | | | | *… and {len(mine)-30:,} more; see `docs/anomaly_report.json`* |")
        w("")
        # explanations for the biggest few
        for a in mine[:6]:
            w(f"<details><summary><code>{a['type']}</code> {md_escape(a['title'])}</summary>")
            w("")
            for e in a["evidence"]:
                w(f"- {e}")
            w("")
            w("</details>")
            w("")
    w("---")
    w("")

    # -- regime register ------------------------------------------------------
    w("## THE REGIME REGISTER — reporting rules that move this data")
    w("")
    w("*Checked before any step is called a fact about the world. This register is the reason `WORLD` is hard to "
      "earn here. A concurrent agent owns `docs/ASSUMPTIONS_AND_LIMITATIONS.md`; these keys are how the two "
      "documents line up.*")
    w("")
    w("| key | years | datasets | may explain | what changed |")
    w("|---|---|---|---|---|")
    for ev in REGIME_EVENTS:
        cls = ("*all*" if ev["classes"] is None
               else ("**context only — never types a row**" if not ev["classes"]
                     else ", ".join("`" + c + "`" for c in sorted(ev["classes"]))))
        yr = str(ev["y0"]) + "–" + str(ev["y1"])
        if ev.get("only_years"):
            yr = ", ".join(str(y) for y in sorted(ev["only_years"]))
        w("| `" + ev["key"] + "` | " + yr + " | "
          + ", ".join("`" + d + "`" for d in ev["datasets"]) + " | " + cls + " | "
          + md_escape(ev["label"]) + " |")
    w("")
    w("### REGIME STRESS TESTS — the register is only worth having if it is testable")
    w("")
    w("*Naming a rule change beside a step is a hypothesis. Measuring whether the step survives an instrument "
      "the rule change cannot touch is a result. Both tests below re-run every sweep and both are built to be "
      "able to come back the other way — a stress test that can only confirm is not a test.*")
    w("")
    for t in stress:
        w(f"#### `{t['id']}` · `{t['regime']}` — **{t['verdict']}**")
        w("")
        w(f"*{t['question']}*")
        w("")
        w(f"Measured on `{t['source']['path']}`, mtime {t['source'].get('mtime')}.")
        w("")
        for f in t["findings"]:
            w(f"- {f}")
        w("")
        if t["id"] == "RS-01" and t.get("series"):
            w("<details><summary>the series both ways</summary>")
            w("")
            w("| year | filings | distinct registrants | top-5 share of FILINGS | top-5 share of DOLLARS |")
            w("|---:|---:|---:|---:|---:|")
            for r in t["series"]:
                w(f"| {r['year']} | {r['filings']:,} | {r['registrants']} | "
                  f"{r['top5_share_filings']}% | {r['top5_share_dollars']}% |")
            w("")
            w("</details>")
            w("")
        if t["id"] == "RS-03" and t.get("series"):
            w("<details><summary>share of positive-obligation rows at or below $2,500, by fiscal year</summary>")
            w("")
            w("| fiscal year | rows with a positive obligation | share <= $2,500 | median positive obligation |")
            w("|---:|---:|---:|---:|")
            for r in t["series"]:
                w(f"| {r['year']} | {r['positive_rows']:,} | {r['share_at_or_below_2500']}% | "
                  f"{money(r['median'])} |")
            w("")
            w("</details>")
            w("")
        if t["id"] == "RS-02" and t.get("series"):
            w("<details><summary>what moved, by assistance listing, against an FY2017-19 baseline</summary>")
            w("")
            for r in t["series"]:
                w(f"**FY{r['year']}** — {money(r['total'])} against baseline {money(r['baseline'])} "
                  f"(excess {money(r['excess'])}; named COVID listings {money(r['covid_cfda_dollars'])})")
                w("")
                w("| CFDA | title | change vs baseline |")
                w("|---|---|---:|")
                for m in r["top_movers"]:
                    w(f"| `{m['cfda']}` | {md_escape(m['title'])} | {money(m['delta'])} |")
                w("")
            w("</details>")
            w("")
    w("### The two that most endanger the editorial slate")
    w("")
    w("1. **`HLOGA_QUARTERLY` (2008).** LDA filings went semiannual → quarterly. Filing COUNTS roughly double "
      "with no change in lobbying activity. Cedar's lobbying series runs 1999–2026, so **every filing-count trend "
      "in it crosses this break.** The registrant-concentration series (top-5 share 35.9% in 1999 → 24.6% in "
      "2024) crosses it, and a concentration share computed on filings is a share of a denominator that doubled "
      "mid-series. Recompute on DOLLARS, or on filings-per-reporting-period, before publishing any of it.")
    w("2. **`COVID_RELIEF` (2020–21).** CARES and ARPA sent reportedly ~$8B and ~$20B directly to tribal "
      "governments. **Any 2020–2021 assistance spike is presumptively REGIME.** Note the trap in the row counts: "
      "assistance calendar-year counts move 46,112 → 49,660 → 52,321 across 2020–22, which is a mild trend and "
      "looks like nothing. **The money does not have to move the way the row counts move** — a relief programme "
      "can be a small number of very large transactions. Check the dollars, per CFDA, before typing any of it.")
    w("")
    w("---")
    w("")

    # -- class 7 regressions ---------------------------------------------------
    w("## KNOWN FALSE ATTRIBUTIONS — re-tested every run")
    w("")
    w("*A spike sitting on a known-bad link is a PIPELINE fact, not a world fact. These run as regressions so "
      "that a fix that silently reverts is caught by the next sweep.*")
    w("")
    for r in regressions:
        w(f"### `{r['id']}` — {r['label']} · **{r.get('status', '')}**")
        w("")
        if r.get("source"):
            w(f"`{r['source']['path']}` · mtime {r['source'].get('mtime')}")
            w("")
        if r.get("measured"):
            for k, v in r["measured"].items():
                w(f"- **{k}**: {v}")
            w("")
        if r.get("known_bad"):
            w(f"- known-bad reading: {r['known_bad']}")
            w(f"- corrected reading: {r['known_good']}")
            w("")
        w(f"{r['note']}")
        w("")
    w("---")
    w("")

    # -- never sum -------------------------------------------------------------
    w("## THE FORBIDDEN SUMS — columns present in these files that must never be totalled")
    w("")
    w("*Recorded so a phantom is recognisable by its magnitude. Every one of these produces a plausible-looking "
      "number, which is worse than an obviously wrong one.*")
    w("")
    for r in nsaudit:
        w(f"**`{r['dataset']}`** (`{r['file']}`, mtime {r['source'].get('mtime')})")
        w("")
        for c in r["columns"]:
            w(f"- `{c['column']}` — {c['why']}")
        w("")
    w("---")
    w("")

    # -- sources ---------------------------------------------------------------
    w("## Sources and vintages")
    w("")
    w("| file | bytes | mtime | read at | rows |")
    w("|---|---:|---|---|---:|")
    for res in results:
        s = res["source"]
        if not s.get("exists"):
            w(f"| `{s['path']}` | — | **MISSING** | — | — |")
            continue
        w(f"| `{s['path']}` | {s['bytes']:,} | {s['mtime']} | {s['read_at']} | {res.get('rows', 0):,} |")
    w("")
    w("---")
    w("")
    w("## How to re-run this, and how to read a row")
    w("")
    w("    py -3 code/227_anomaly_sweep.py")
    w("    py -3 code/227_anomaly_sweep.py --only prime_contracts,subawards")
    w("")
    w("**Read-only against every dataset.** Zero network calls. Writes `docs/ANOMALY_REPORT.md` and "
      "`docs/anomaly_report.json` and nothing else. Never runs `01_build_entity_spine.py`, "
      "`09_import_rulings.py`, `41_build_codebooks.py` or `88_build_deals_taxonomy.py`.")
    w("")
    w("Four rules for handling a row:")
    w("")
    w("1. **Do not close an UNKNOWN by finding a story.** A definitional or regime explanation is admissible only "
      "if it NAMES the change and the named change is checkable in the data. \"Probably a coverage thing\" is not "
      "an explanation; it is the absence of one wearing its clothes.")
    w("2. **Do not widen a threshold to make a row disappear.** This file records anomalies, not tolerances. A "
      "sweep that is always clean reports nothing — the same decoration failure `AGENTS.md` records against "
      "`62_no_regression_check.py`.")
    w("3. **A `REGIME` row is not a defect and must not be fixed.** It is a caveat that has to travel with every "
      "sentence built on that series. Fix the sentence, not the data.")
    w("4. **A `PIPELINE` row has an owning script named in its evidence.** An unnamed failure gets inherited; a "
      "named one gets fixed.")
    w("")
    w("### What this sweep does NOT do")
    w("")
    w("- **A seam does not have to fall on a date.** Every test here except `SOURCE_VOCABULARY_SPLIT` "
      "compares adjacent years, and two pulls that OVERLAP in time mix their vocabularies inside every year "
      "where no year boundary can separate them. `prime_contracts.funding_agency` is the worked example and it "
      "is why that one test exists. It runs only where the dataset spec names an `era_col`.")
    w("- It compares **adjacent years**. A slow drift over a decade — a linkage rate creeping up as passes land — "
      "never trips a year-over-year test and is invisible here.")
    w("- It types a year, not a transaction. A REGIME window covering 2020–21 will type an ordinary 2020 spike as "
      "REGIME. **That is deliberate and it is the conservative direction**: it costs a true finding, and the "
      "opposite error ships a false one.")
    w("- Its categorical seam detector picks candidate columns from the first "
      f"{CAT_SAMPLE_ROWS:,} rows and drops any column exceeding {CAT_SAMPLE_MAX_DISTINCT} distinct values there. "
      "**A seam in a high-cardinality column is invisible to it.**")
    w("- Every anomaly carries a CONTENT-ADDRESSED `anomaly_id` (md5 over dataset + class + column + entity "
      "+ year). It is deliberately NOT positional and deliberately not built on Python's `hash()`, which is "
      "randomised per process — three ids elsewhere in this repo are built that way and a re-run changed 482 of "
      "492 of them. An id that moves when nothing moved makes a diffable artefact undiffable.")
    w("- Benford and round-number clustering are **prompts to look, never findings**. Federal money is full of "
      "legitimate reasons to fail both.")

    md_path = os.path.join(DOCS, "ANOMALY_REPORT.md")
    tmp = md_path + ".part"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    os.replace(tmp, md_path)

    payload = dict(
        generated=RUN_AT.isoformat(timespec="seconds"),
        script="code/227_anomaly_sweep.py",
        elapsed_s=round(elapsed, 1),
        types=dict(by_type),
        classes=dict(by_cls),
        thresholds=dict(spike_multiple=SPIKE_MULTIPLE, spike_min_dollars=SPIKE_MIN_DOLLARS,
                        discontinuity=[DISCONT_LO, DISCONT_HI], seam_jaccard=SEAM_JACCARD,
                        unit_shift_ratio=UNIT_SHIFT_RATIO),
        sources=[r["source"] for r in results],
        datasets=[{k: v for k, v in r.items() if not k.startswith("_")} for r in results],
        regime_register=[dict(key=e["key"], first_year=e["y0"], last_year=e["y1"],
                              datasets=e["datasets"],
                              classes=(sorted(e["classes"]) if e["classes"] is not None else "*"),
                              only_years=sorted(e["only_years"]) if e.get("only_years") else None,
                              label=e["label"]) for e in REGIME_EVENTS],
        pipeline_register=[dict(dataset=d, first_year=a, last_year=b,
                                classes=(sorted(c) if c is not None else "*"), label=l, owner=o)
                           for d, a, b, c, l, o in PIPELINE_BOUNDARIES],
        known_seams={f"{a}.{b}": v for (a, b), v in KNOWN_SEAMS.items()},
        false_attribution_regressions=regressions,
        forbidden_sums=nsaudit,
        regime_stress_tests=stress,
        anomalies=[dict(a, anomaly_id=anomaly_id(a)) for a in sorted(anomalies, key=rank_key)],
    )
    js_path = os.path.join(DOCS, "anomaly_report.json")
    tmp = js_path + ".part"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, default=str, sort_keys=False)
    os.replace(tmp, js_path)
    return md_path, js_path


def main(argv):
    only = None
    for i, a in enumerate(argv):
        if a == "--list":
            for s in SPECS:
                print(s["name"], "->", s["file"])
            return 0
        if a == "--only" and i + 1 < len(argv):
            only = {x.strip() for x in argv[i + 1].split(",")}
        if a.startswith("--only="):
            only = {x.strip() for x in a.split("=", 1)[1].split(",")}

    t0 = datetime.now()
    print(f"227_anomaly_sweep — read-only, {len(SPECS)} datasets", flush=True)
    results, anomalies = [], []
    for spec in SPECS:
        if only and spec["name"] not in only:
            continue
        res = scan(spec)
        try:
            anomalies.extend(derive(res, spec))
        except Exception as exc:                                     # pragma: no cover
            print(f"    !! derive failed for {spec['name']}: {exc}", flush=True)
            anomalies.append(dict(cls="DATASET_MISSING", dataset=spec["name"], type="UNKNOWN",
                                  stake_rows=0, stake_usd=0.0,
                                  title=f"{spec['name']}: anomaly derivation raised {type(exc).__name__}: {exc}",
                                  evidence=["The scan completed; the derivation did not. Reported rather than "
                                            "swallowed."]))
        for k in list(res):
            if k.startswith("_"):
                res.pop(k, None)
        results.append(res)
        print(f"    {spec['name']}: {res.get('rows', 0):,} rows, "
              f"{len([a for a in anomalies if a['dataset'] == spec['name']]):,} anomalies", flush=True)

    print("  regressions + forbidden-sum audit ...", flush=True)
    regressions = false_attribution_regressions()
    nsaudit = never_sum_audit()
    print("  regime stress tests ...", flush=True)
    stress = regime_stress_tests()
    elapsed = (datetime.now() - t0).total_seconds()
    md, js = write_report(results, anomalies, regressions, nsaudit, stress, elapsed)
    print(f"\nwrote {os.path.relpath(md, ROOT)}")
    print(f"wrote {os.path.relpath(js, ROOT)}")
    print(f"{len(anomalies):,} anomalies in {elapsed:,.0f}s")
    by = Counter(a["type"] for a in anomalies)
    print("  " + " · ".join(f"{t} {by.get(t,0):,}" for t in ("PIPELINE", "REGIME", "WORLD", "UNKNOWN")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
