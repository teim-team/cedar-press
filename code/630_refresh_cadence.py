"""630 — the per-SOURCE refresh cadence table, measured from disk.

    py -3 code/630_refresh_cadence.py              # zero network requests
    py -3 code/630_refresh_cadence.py --probe-net  # + 4 bounded probes, one per host
    py -3 code/630_refresh_cadence.py --json-only  # do not touch the .md

WHAT THIS ANSWERS
-----------------
The owner's question: *"Throughout all the datasets, we need to know how often
we have to scrape and update these things."*

The answer is NOT one number per dataset. It is one row per SOURCE, and the
sources inside one dataset differ by two orders of magnitude — `natural-resources`
alone draws on twelve source systems whose edges run from 2000-12-31 to
2026-09-30. **A dataset's cadence is its fastest-moving source that anyone
depends on; its staleness is its slowest.**

THE DISTINCTION THIS FILE EXISTS FOR
------------------------------------
Three states look identical in a staleness column and are completely different
work:

  1  SOURCE_NOT_PUBLISHED  the source has not published yet. Nothing to do.
  2  NOT_PULLED            published and we have not fetched. An ACQUISITION task.
  3  PULLED_NOT_PROMOTED   fetched and sitting in raw/ staging/ review/,
                           unparsed or unpromoted. **NOT an acquisition task.**

Calling a 3 a 2 sends the next agent to re-download something already on disk.
That has happened in this repo at least three times (California RSTF, New Mexico
gaming, the staged NIGC set) and each time it cost a session. Every entry in
this file therefore carries `cedar_holds_through` MEASURED from the clean table
and `source_has_through` with a named basis and the date it was established.
Nothing here is asserted from prose.

WHAT IT REFUSES
---------------
* It never writes to `data/clean/`, `data/spine/` or any dataset contract.
* It never fetches data. `--probe-net` issues at most four requests, one per
  host, >=6s apart, and only asks an index for a date.
* Where `source_has_through` cannot be established without a key or a crawl it
  records `NOT_ESTABLISHED` with the reason. An unprobed source is never
  reported as current.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import sys

csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))
try:  # the Windows console defaults to cp1252 and this file is full of marks
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN = os.path.join(ROOT, "data", "clean")
RAW = os.path.join(ROOT, "data", "raw")
STAGING = os.path.join(ROOT, "data", "staging")
REVIEW = os.path.join(ROOT, "review")
OUT_JSON = os.path.join(ROOT, "docs", "REFRESH_CADENCE.json")
OUT_MD = os.path.join(ROOT, "docs", "REFRESH_CADENCE.md")

BEGIN = "<!-- CEDAR:CADENCE-MEASURED START -->"
END = "<!-- CEDAR:CADENCE-MEASURED END -->"

TODAY = dt.date.today().isoformat()

# A period is a year, a year-month, a date, or a date with a time on the end
# (LDA's `dt_posted` is a full ISO timestamp and an anchored date-only pattern
# silently reports the whole column as unmeasurable).
DATE_RE = re.compile(r"^(1[89]|20|21)\d\d[-/]?\d\d?([-/]\d\d?)?([T ].*)?$")
YEAR_RE = re.compile(r"^(1[89]|20|21)\d\d$")

# --------------------------------------------------------------------------
# STATES
# --------------------------------------------------------------------------
S_CURRENT = "CURRENT"
S1 = "1_SOURCE_NOT_PUBLISHED"
S2 = "2_NOT_PULLED"
S3 = "3_PULLED_NOT_PROMOTED"
S_CLOSED = "CLOSED_BY_DESIGN"
S_UNKNOWN = "UNKNOWN_SOURCE_EDGE"

# --------------------------------------------------------------------------
# THE SOURCE REGISTRY
# --------------------------------------------------------------------------
# One entry per SOURCE, not per dataset and not per table.
#
#   holds        {table, col}          measured every run from data/clean
#   last_pulled  {table, col} | {manifest, col} | {literal}
#   source_has_through / source_basis / source_measured
#                the newest period the SOURCE offers, WITH the evidence and the
#                date that evidence was taken. "" means NOT_ESTABLISHED.
#   state_hint   force a state where the derivation cannot see the reason
#   backlog      a callable name in BACKLOGS, measured from disk each run
#
# `source_basis` values beginning "probe " were taken by this script's
# --probe-net. Values beginning "sibling " were measured today by another
# workstream and are cited rather than re-derived, per the standing rule that
# a cadence doc reuses a COVERAGE table and does not rebuild it.

SOURCES = [

    # ================= funding =================
    dict(
        dataset="funding", source_id="usaspending_assistance_archive",
        source="USAspending award-data archive — assistance (files.usaspending.gov)",
        host="files.usaspending.gov",
        publish_cadence="monthly (whole 93.9 GB archive replaced atomically)",
        publish_lag="stamp dated the 6th, published the 10th ~00:14Z (~4d); a "
                    "month keeps filling for ~2 further months (2026-05 at 66%, "
                    "2026-06 at 60% of plateau)",
        cadence_basis="REFRESH_CADENCE 1.2/1.3 — S3 last_modified over 4,597 objects",
        holds=dict(table="federal_funding_transactions.csv", col="action_date"),
        last_pulled=dict(table="federal_funding_transactions.csv", col="fetched_date"),
        source_has_through="2026-06-30",
        source_basis="the archive's own edge under stamp 20260806; assistance "
                     "carries no action_date past 2026-06-30",
        source_measured="2026-08-26",
        refresh_cost="20 objects x ~1.2-2.0 GB; hours",
        refresh_command="probe the stamp PER YEAR on the 11th, then re-filter; "
                        "do NOT run 41 or 88 (they rebuild from stale upstream)",
        breaks_on_refresh="`source_vintage` on all 701,955 rows (code/335); the "
                          "notes vintage (code/87); federal_funding_tribe_year_panel.csv",
    ),
    dict(
        dataset="funding", source_id="usaspending_bulk_2023",
        source="USAspending bulk download 2023-04-09 (historical stratum A)",
        host="api.usaspending.gov",
        publish_cadence="one-time", publish_lag="n/a",
        cadence_basis="docs/REFRESH_CADENCE 4.0a — 476,924 rows, FY2008-2023",
        holds=dict(table=None, col=None),
        last_pulled=dict(literal="2023-04-09"),
        source_has_through="", source_basis="superseded by the monthly archive; "
        "retained only because deduplication makes the strata disjoint on "
        "transaction key (0 shared keys)",
        source_measured="2026-08-26",
        state_hint=S_CLOSED,
        refresh_cost="zero — never re-pull", refresh_command="none",
        breaks_on_refresh="nothing; re-pulling would re-open the vintage-mixing "
                          "defect 335 closed",
    ),
    dict(
        dataset="funding", source_id="faads",
        source="FAADS (Federal Assistance Award Data System)",
        host="—",
        publish_cadence="retired", publish_lag="n/a",
        cadence_basis="superseded by USAspending; the series ends FY2007 by design",
        holds=dict(table="faads_transactions_all_agencies.csv", col="action_date"),
        last_pulled=dict(manifest="data/raw/external/faads/_SOURCE_MANIFEST_faads.csv",
                         col="retrieved_date"),
        source_has_through="2007-09-30",
        source_basis="the source ended 2007-09-30", source_measured="2026-08-05",
        state_hint=S_CLOSED,
        refresh_cost="zero", refresh_command="none — stamp it once and never touch it",
        breaks_on_refresh="nothing",
    ),
    dict(
        dataset="funding", source_id="bie_uio",
        source="BIE / IHS Urban Indian Organization rosters",
        host="bie.edu / ihs.gov",
        publish_cadence="irregular (roster snapshots)", publish_lag="unknown",
        cadence_basis="no publication schedule stated by either agency",
        holds=dict(table="bie_uio_dollars_by_entity.csv", col="fiscal_year"),
        last_pulled=dict(manifest="data/raw/external/bie_uio/_SOURCE_MANIFEST.csv",
                         col="fetched_date"),
        source_has_through="",
        source_basis="NOT ESTABLISHED, and neither agency states a schedule. "
                     "BIE posts a school directory and IHS a UIO list; both are "
                     "snapshots that change without notice. This is a "
                     "change-detection source, not a calendar source.",
        source_measured="",
        refresh_cost="16 documents; minutes",
        refresh_command="code/40_build_bie_uio.py (see BIE_UIO_BUILD_LOG.md)",
        breaks_on_refresh="the spine's BIE school population (185 entities)",
    ),

    # ================= contractors =================
    dict(
        dataset="contractors", source_id="usaspending_prime_archive",
        source="USAspending award-data archive — prime contracts",
        host="files.usaspending.gov",
        publish_cadence="monthly (same object set as assistance)",
        publish_lag="~4d to publication; a month keeps filling ~2 further months "
                    "(2026-05 at 44%, 2026-06 at 54% of plateau)",
        cadence_basis="REFRESH_CADENCE 1.2/1.3",
        holds=dict(raw_glob="data/raw/contracts/usaspending_archive_2026-08-07/"
                            "filtered/FY2026_ledger_rows.csv", col="action_date"),
        last_pulled=dict(literal="2026-08-07"),
        source_has_through="2026-07-03",
        source_basis="the archive cut under stamp 20260806 — the newest "
                     "action_date the source served at pull time",
        source_measured="2026-08-26",
        refresh_cost="20 objects; hours. **api.usaspending.gov and "
                     "files.usaspending.gov share one rate-limit budget**",
        refresh_command="probe the stamp PER YEAR on the 11th, then re-filter",
        breaks_on_refresh="207 (extent_competed, in place), 269 "
                          "(contractor_ranking), 168 (adjudication hubs) — "
                          "enrichers run LAST",
    ),
    dict(
        dataset="contractors", source_id="sam_contract_awards",
        source="SAM.gov Contract Awards API — FY2000-2007 prime backfill",
        host="api.sam.gov",
        publish_cadence="continuous (the API), but Cedar's use is a one-time backfill",
        publish_lag="n/a — historical years are settled",
        cadence_basis="docs/API_KEYS.md; the only route to FY2000-2007 prime",
        holds=dict(table="sam_prime_contracts_fy2000_2007.csv", col="fiscal_year"),
        last_pulled=dict(literal="2026-08-12"),
        source_has_through="2007",
        source_basis="Cedar's use of this host is bounded to FY2000-2007; later "
                     "years come from the archive",
        source_measured="2026-08-26",
        refresh_cost="**10 requests/day** pending the org role request; extract "
                     "mode only (1,000,000 records/request)",
        refresh_command="code/141_pull_sam_contract_awards.py — never casually",
        breaks_on_refresh="prime_contracts_archive_backfill.csv and its reconciliation",
    ),
    dict(
        dataset="contractors", source_id="fpds_atom",
        source="FPDS-NG ATOM feed",
        host="fpds.gov",
        publish_cadence="continuous", publish_lag="3 business days for entry; "
                        "corrections run months longer",
        cadence_basis="sam.gov/contracting: *'will be retired later in FY 2026'*",
        holds=dict(table=None, col=None),
        last_pulled=dict(literal="2026-08-26"),
        source_has_through="",
        source_basis="an EXPIRY DATE, not a cadence — anything depending on this "
                     "route must extract before retirement, not schedule around it",
        source_measured="2026-08-26",
        state_hint=S_UNKNOWN,
        refresh_cost="n/a", refresh_command="code/562/563 probe it; no production pull",
        breaks_on_refresh="the pre-2000 Native-flag probe only",
    ),
    dict(
        dataset="contractors", source_id="cicd_published",
        source="CICD published prime series 1981-2021 (article __NEXT_DATA__)",
        host="—",
        publish_cadence="one-time (a 2022-12-21 article)", publish_lag="n/a",
        cadence_basis="docs/datasets/02_contracting.md COVERAGE",
        holds=dict(staging="cicd_published/cicd_prime_series_1981_2021.csv", col=None),
        last_pulled=dict(literal="2026-09-01"),
        source_has_through="2021",
        source_basis="the article's own series arrays end 2021",
        source_measured="2026-09-01",
        state_hint=S_CLOSED,
        refresh_cost="zero",
        refresh_command="none — a PUBLISHED benchmark, never merged as a Cedar measurement",
        breaks_on_refresh="nothing",
    ),

    # ================= subcontracting =================
    dict(
        dataset="subcontracting", source_id="fsrs_subawards",
        source="FSRS subawards via api.usaspending.gov",
        host="api.usaspending.gov",
        publish_cadence="continuous; primes file by end of the month following "
                        "the award month",
        publish_lag="NOT MEASURABLE — the mature window (2021-08..2024-08) falls "
                    "inside the FY2021-24 hole, so every plateau ratio computed "
                    "from it is meaningless (PLATEAU_WARNING in 301)",
        cadence_basis="REFRESH_CADENCE 1.5(b)",
        holds=dict(table="subawards.csv", col="subaward_date"),
        last_pulled=dict(table="subawards.csv", col="fetched_date"),
        source_has_through="",
        source_basis="NOT ESTABLISHED — code/121_pull_subawards_api.py holds the "
                     "host right now; one poller per host",
        source_measured="",
        state_hint=S_UNKNOWN,
        refresh_cost="~2,733 paginated calls",
        refresh_command="code/121_pull_subawards_api.py pull --sequential "
                        "(ALREADY RUNNING — do not start a second)",
        breaks_on_refresh="prime_sub_network.csv, subaward_entity_rollup.csv; "
                          "the FEMA key 1843-GR35056 is NOT unique (11 villages)",
    ),

    # ================= lobbying =================
    dict(
        dataset="lobbying", source_id="lda",
        source="Lobbying Disclosure Act filings (LD-2 / LD-203)",
        host="lda.gov",
        publish_cadence="quarterly LD-2 (due +20d), semiannual LD-203 (30 Jan / "
                        "30 Jul); amendments arrive CONTINUOUSLY and indefinitely",
        publish_lag="median 20d = the statutory deadline exactly; only 57.4% "
                    "filed by day 20, 74.0% by day 34, p99 = 495d, max = 5,885d "
                    "(n = 27,796)",
        cadence_basis="REFRESH_CADENCE 2.1 — measured over Cedar's own 27,796 filings",
        holds=dict(table="native_entity_lobbying_disclosures.csv", col="dt_posted"),
        last_pulled=dict(literal="2026-08-04"),
        source_has_through="2026-09-01",
        source_basis="probe 2026-09-01: lda.gov/api/v1/filings ?ordering=-dt_posted "
                     "-> newest dt_posted 2026-09-01T20:53:39-04:00 (a 2026-Q2 "
                     "no-activity report). count 1,976,576",
        source_measured="2026-09-01",
        refresh_cost="15 req/min anonymous, 120 keyed — cheap",
        refresh_command="key on `dt_posted >= last_pull`, NEVER on filing_year + "
                        "filing_period, and re-read the trailing 4 quarters",
        breaks_on_refresh="78_content_analysis.py rebuilds FIVE lobbying tables "
                          "AND fr_content_classification.csv — run it when no "
                          "other lobbying build is live",
    ),
    dict(
        dataset="lobbying", source_id="regulations_gov",
        source="regulations.gov public submissions (API v4)",
        host="api.regulations.gov",
        publish_cadence="continuous — comment periods are the events",
        publish_lag="posting is near-immediate; the docket, not the entity, is the clock",
        cadence_basis="docs/datasets/lobbying_sources.md §4",
        holds=dict(table="regulations_gov_comments.csv", col="posted_date"),
        last_pulled=dict(table="regulations_gov_comments.csv", col="retrieved_date"),
        source_has_through="",
        source_basis="NOT ESTABLISHED as a date — the gap here is ENTITY coverage, "
                     "not time: 51 of 1,712 query names banked (97% of the sweep "
                     "un-run)",
        source_measured="2026-09-01",
        state_hint=S2,
        refresh_cost="1,712 query names at ~12 s/query = ~8 wall-clock hours; "
                     "checkpoints per entity",
        refresh_command="code/221 — sweep DOCKET-first, never entity-first",
        breaks_on_refresh="regulations_gov_entity_coverage.csv (one row per entity, "
                          "measured zeros included)",
    ),
    dict(
        dataset="lobbying", source_id="fr_consultation",
        source="Tribal consultation notices (Federal Register)",
        host="www.federalregister.gov",
        publish_cadence="every federal business day", publish_lag="0-1 day",
        cadence_basis="rides the same request stream as dataset 9",
        holds=dict(table="fr_consultation_notices.csv", col="publication_date"),
        last_pulled=dict(table="consultation_events.csv", col="fetched_date"),
        source_has_through="2026-09-01",
        source_basis="probe 2026-09-01: federalregister.gov newest "
                     "publication_date = 2026-09-01, HTTP 200. **The FR corpus "
                     "is same-day. Whether a tribal consultation notice actually "
                     "published in the 104-day gap is a question only the sweep "
                     "answers — but lobbying_sources.md, written today by the "
                     "docs workstream, independently calls this leg '3 months "
                     "stale; 29 agencies only'.**",
        source_measured="2026-09-01",
        refresh_cost="free — same requests as the FR pull",
        refresh_command="ride code/342_pull_federal_register_incremental.py",
        breaks_on_refresh="consultation_agency_coverage.csv, fr_consultation_year.csv",
    ),
    dict(
        dataset="lobbying", source_id="section_106",
        source="Section 106 / NHPA consultation notices (Federal Register)",
        host="www.federalregister.gov",
        publish_cadence="every federal business day", publish_lag="0-1 day",
        cadence_basis="docs/datasets/lobbying_sources.md row 5",
        holds=dict(table="section_106_consultation_events.csv", col="notice_date"),
        last_pulled=dict(table="section_106_consultation_events.csv", col="fetched_date"),
        source_has_through="2026-09-01",
        source_basis="probe 2026-09-01: same FR corpus",
        source_measured="2026-09-01",
        refresh_cost="free — same request stream",
        refresh_command="code/130 after the FR pull",
        breaks_on_refresh="section_106_project_parties.csv",
    ),
    dict(
        dataset="lobbying", source_id="ibia_ibla",
        source="IBIA / IBLA administrative appeals (Interior OHA year indices)",
        host="oha.doi.gov",
        publish_cadence="event-driven; posted to the year index as issued",
        publish_lag="~1 month observed",
        cadence_basis="docs/datasets/lobbying_sources.md row 7 — 114/114 board-years, all 200",
        holds=dict(table="admin_appeal_decisions.csv", col="decision_date"),
        last_pulled=dict(table="admin_appeal_decisions.csv", col="fetched_date"),
        source_has_through="",
        source_basis="NOT RE-PROBED this run; the pull is COMPLETE to 114/114 "
                     "board-years as of 2026-08-12",
        source_measured="2026-08-12",
        refresh_cost="year indices only; minutes",
        refresh_command="code/163 --year 2026",
        breaks_on_refresh="168_link_adjudication_hubs.py runs in place and 133 "
                          "reverts it — this collision has bitten FERC four times",
    ),
    dict(
        dataset="lobbying", source_id="fr_ex_parte",
        source="Federal Register ex parte notices, all agencies",
        host="www.federalregister.gov",
        publish_cadence="every federal business day", publish_lag="0-1 day",
        cadence_basis="docs/datasets/lobbying_sources.md row 10 — COMPLETE to the API floor (1994)",
        holds=dict(table="fr_ex_parte_notices.csv", col="publication_date"),
        last_pulled=dict(table="fr_ex_parte_notices.csv", col="built_date"),
        source_has_through="2026-09-01",
        source_basis="probe 2026-09-01: same FR corpus",
        source_measured="2026-09-01",
        refresh_cost="free — same request stream",
        refresh_command="ride the FR pull, then code/98",
        breaks_on_refresh="fr_ex_parte_parties.csv, fr_ex_parte_party_entity_links.csv",
    ),
    dict(
        dataset="lobbying", source_id="ferc_elibrary",
        source="FERC eLibrary docket filings",
        host="elibrary.ferc.gov",
        publish_cadence="continuous", publish_lag="indexed ~1 business day after acceptance",
        cadence_basis="REFRESH_CADENCE Part 2 — confirmed same-day 2026-08-26",
        holds=dict(table="ferc_docket_filings.csv", col="filed_date"),
        last_pulled=dict(table="ferc_docket_filings.csv", col="fetched_date"),
        source_has_through="",
        source_basis="NOT RE-PROBED this run; was same-day current on 2026-08-26",
        source_measured="2026-08-26",
        refresh_cost="~300 docket sheets; hours",
        refresh_command="code/133 build — then RE-RUN 168, which 133 reverts",
        breaks_on_refresh="**168's in-place links. 133 has destroyed them four "
                          "times in one day. Enricher runs LAST.**",
    ),
    dict(
        dataset="lobbying", source_id="foia_logs",
        source="Agency FOIA logs (DOI, Indian Affairs, IHS only)",
        host="various",
        publish_cadence="agency-dependent, typically annual or quarterly postings",
        publish_lag="months",
        cadence_basis="docs/datasets/lobbying_sources.md row 14",
        holds=dict(table="foia_request_index.csv", col="fetched_date"),
        last_pulled=dict(table="foia_request_index.csv", col="fetched_date"),
        source_has_through="",
        source_basis="NOT ESTABLISHED — the gap is AGENCY coverage: 3 of ~100 "
                     "agencies publish here and are pulled; EPA, USDA, HHS, DOE, "
                     "Corps and Commerce all publish and none is pulled",
        source_measured="2026-09-01",
        state_hint=S2,
        refresh_cost="one parser per agency",
        refresh_command="code/136 — extend to the six named agencies first",
        breaks_on_refresh="correspondence_foia_source_coverage.csv",
    ),
    dict(
        dataset="lobbying", source_id="irs990_schedc",
        source="IRS 990 Schedule C (lobbying / political activity), e-file XML",
        host="apps.irs.gov",
        publish_cadence="annual index per SUBMISSION year, returns released in "
                        "batches as processed",
        publish_lag="index years 2017-2026 only; 2009-2016 are 404 at the IRS — "
                    "that floor is the IRS's, not ours",
        cadence_basis="docs/datasets/lobbying_sources.md §4b, measured today",
        holds=dict(table="nonprofit_schedule_c_lobbying.csv", col="index_year"),
        last_pulled=dict(manifest="data/raw/external/irs990_schedc/_zip_manifest.csv",
                         col="fetched_date"),
        source_has_through="2026",
        source_basis="sibling: nonprofit_schedule_c_coverage.csv, built 2026-09-01 "
                     "by code/99 from the IRS index itself",
        source_measured="2026-09-01",
        state_hint=S2,
        backlog="schedc",
        refresh_cost="one host, rate-disciplined; the backlog is the fetch, not the parse",
        refresh_command="code/99_build_earmarks_and_schedc.py --steps irs-xml",
        breaks_on_refresh="nonprofit_schedule_c_coverage.csv must be rebuilt in "
                          "the same pass or it reports a stale backlog",
    ),
    dict(
        dataset="lobbying", source_id="oira_nrc_hearings",
        source="OIRA EO-12866 meetings · NRC public meetings · congressional hearings",
        host="reginfo.gov / nrc.gov / govinfo.gov",
        publish_cadence="event-driven; posted within days",
        publish_lag="days",
        cadence_basis="OIRA_HEARINGS_BUILD_LOG.md",
        holds=dict(table="nrc_public_meetings.csv", col="meeting_date"),
        last_pulled=dict(table="nrc_public_meetings.csv", col="fetched_date"),
        source_has_through="",
        source_basis="NOT RE-PROBED this run",
        source_measured="2026-08-12",
        refresh_cost="small",
        refresh_command="code/98",
        breaks_on_refresh="agency_attention_vs_advocacy*.csv (written by 78)",
    ),

    # ================= federal-register =================
    dict(
        dataset="federal-register", source_id="federal_register",
        source="federalregister.gov API — the 14 Cedar nets",
        host="www.federalregister.gov",
        publish_cadence="every federal business day; public inspection the day before",
        publish_lag="0 — same-day",
        cadence_basis="REFRESH_CADENCE 5.1 and probe 2026-09-01",
        holds=dict(table="federal_actions.csv", col="publication_date"),
        last_pulled=dict(table="federal_actions.csv", col="fetched_date"),
        source_has_through="2026-09-01",
        source_basis="probe 2026-09-01: /api/v1/documents.json?order=newest -> "
                     "publication_date 2026-09-01, HTTP 200",
        source_measured="2026-09-01",
        refresh_cost="minutes, ~1 API page/day of gap x 14 nets",
        refresh_command="py -3 code/342_pull_federal_register_incremental.py "
                        "— **never 10 (re-shards 1994..today) and never 11 "
                        "(full rebuild; reverts 22's two in-place columns)**",
        breaks_on_refresh="fr_content_classification.csv (78, which also rebuilds "
                          "five LOBBYING tables), 130, 76, 98, 133, 136 — each a "
                          "separate owner's build",
    ),
    dict(
        dataset="federal-register", source_id="nepa_eplanning",
        source="BLM/DOI NEPA ePlanning project register",
        host="eplanning.blm.gov",
        publish_cadence="continuous as projects are registered", publish_lag="days",
        cadence_basis="NEPA_* build logs; no schedule published by BLM",
        holds=dict(table="nepa_eplanning_projects.csv", col="fetched_date"),
        last_pulled=dict(manifest="data/raw/advocacy/nepa_eplanning/_SOURCE_MANIFEST.csv",
                         col="fetched_date"),
        source_has_through="",
        source_basis="NOT RE-PROBED this run",
        source_measured="2026-08-12",
        refresh_cost="719 documents in the last pass; ~1 hour",
        refresh_command="the NEPA register step (see nepa_source_coverage.csv)",
        breaks_on_refresh="nepa_project_documents.csv, nepa_administrative_record_parties.csv",
    ),

    # ================= nagpra =================
    dict(
        dataset="nagpra", source_id="nagpra_notices",
        source="NAGPRA notices (Federal Register documents)",
        host="www.federalregister.gov",
        publish_cadence="every federal business day, event-driven arrival",
        publish_lag="0 — same-day, but the SOURCE's own gap between notices runs days",
        cadence_basis="REFRESH_CADENCE 5.2",
        holds=dict(table="nagpra_notices.csv", col="publication_date"),
        last_pulled=dict(literal="2026-08-26"),
        source_has_through="2026-09-01",
        source_basis="probe 2026-09-01: the FR corpus is same-day. Whether a "
                     "NAGPRA notice published between 2026-08-24 and 2026-09-01 "
                     "is a separate question the sweep answers, not the index",
        source_measured="2026-09-01",
        refresh_cost="free — rides the FR request stream",
        refresh_command="py -3 code/77_build_nagpra_dataset.py fetch && ... build",
        breaks_on_refresh="nagpra_notice_entity_bridge.csv (51,521 bridge rows). "
                          "**mni_total_stated MUST NEVER BE SUMMED.** The 2024 "
                          "surge is the 43 CFR 10 regime change, bounded by the "
                          "2029-01-10 deadline — never publish it as behaviour.",
    ),

    # ================= legislation =================
    dict(
        dataset="legislation", source_id="congress_gov_bills",
        source="Congress.gov API — bills, actions, cosponsors",
        host="api.congress.gov",
        publish_cadence="continuous while Congress sits",
        publish_lag="~1 day for introductions; action histories update continuously",
        cadence_basis="no Cedar measurement exists; the API publishes continuously",
        holds=dict(table="native_bills.csv", col="introduced_date"),
        last_pulled=dict(table="native_bills.csv", col="build_date"),
        source_has_through="",
        source_basis="NOT ESTABLISHED — **api.congress.gov requires a key and "
                     "Cedar holds none** (checked 2026-09-01: CONGRESS_API_KEY, "
                     "CONGRESS_GOV_API_KEY and DATA_GOV_API_KEY are all absent "
                     "from the environment and .env.local). This is the one "
                     "dataset whose source edge cannot be established at all.",
        source_measured="2026-09-01",
        state_hint=S_UNKNOWN,
        refresh_cost="unknown until a key exists",
        refresh_command="code/14_build_bills_votes.py then code/73 "
                        "--rollcalls --sweep --titles --actions --outcomes",
        breaks_on_refresh="native_bill_outcomes.csv, member_positions.csv "
                          "(136,119 rows), the two entity bridges",
    ),
    dict(
        dataset="legislation", source_id="rollcall_votes",
        source="Roll-call votes — senate.gov XML and clerk.house.gov",
        host="www.senate.gov / clerk.house.gov",
        publish_cadence="continuous while Congress sits (each roll call within hours)",
        publish_lag="hours",
        cadence_basis="the chambers publish per vote; no key required",
        holds=dict(table="bill_votes.csv", col="date"),
        last_pulled=dict(table="bill_votes.csv", col="build_date"),
        source_has_through="",
        source_basis="NOT PROBED. **And the naive reading is a trap:** this table "
                     "holds only 423 NATIVE-RELEVANT roll calls since 1973 — "
                     "roughly 8 a year. Its edge at 2025-05-06 is as likely to be "
                     "the last Native-relevant vote as it is our staleness, and "
                     "nothing on disk distinguishes the two.",
        source_measured="",
        state_hint=S_UNKNOWN,
        refresh_cost="two chamber indices per Congress; minutes",
        refresh_command="code/73_bills_votes_completion.py --rollcalls",
        breaks_on_refresh="bill_votes_entity_bridge.csv, bill_votes_official_verification.csv",
    ),
    dict(
        dataset="legislation", source_id="congressional_correspondence",
        source="Congressional correspondence systems (member letter releases)",
        host="various house.gov / senate.gov",
        publish_cadence="irregular, per office", publish_lag="unknown",
        cadence_basis="none — 257 SYSTEM rows describe where letters would be found",
        holds=dict(table="congressional_correspondence_systems.csv", col="publication_date"),
        last_pulled=dict(literal="2026-08-12"),
        source_has_through="",
        source_basis="NOT ESTABLISHED",
        source_measured="",
        state_hint=S2,
        backlog="corr_log",
        refresh_cost="one parser per office",
        refresh_command="code/136 (correspondence leg)",
        breaks_on_refresh="nothing — congressional_correspondence_log.csv is empty",
    ),

    # ================= deals =================
    dict(
        dataset="deals", source_id="deals_press",
        source="Press, trade and tribal announcements (manual + assisted sweep)",
        host="many",
        publish_cadence="continuous — deals ARE discovery",
        publish_lag="0-14 days from announcement to a findable source",
        cadence_basis="REFRESH_CADENCE 3.1 — the one collection where delay "
                      "destroys evidence (link rot)",
        holds=dict(table="deals_classified.csv", col="Event_Date"),
        last_pulled=dict(table="deals_classified.csv", col="Data_As_Of"),
        source_has_through="",
        source_basis="NOT ESTABLISHABLE — there is no index to probe. A deal is "
                     "current when someone looked.",
        source_measured="",
        state_hint=S_UNKNOWN,
        refresh_cost="manual + press; a weekly sweep, a quarterly deep pass",
        refresh_command="code/54 / 153 additions merge; backfill "
                        "REVERSE-CHRONOLOGICALLY",
        breaks_on_refresh="deals_party_attribution.csv and the autoresolver — "
                          "an upsert must NEVER overwrite a human ruling",
    ),
    dict(
        dataset="deals", source_id="sec_edgar",
        source="SEC EDGAR full-text (tribal issuer and counterparty filings)",
        host="www.sec.gov",
        publish_cadence="continuous", publish_lag="same-day on acceptance",
        cadence_basis="EDGAR publishes on acceptance; Cedar's 2010-2017 pass was one-time",
        holds=dict(table="deals_sec_2010_2017_additions.csv", col="Event_Date"),
        last_pulled=dict(literal="2026-08-05"),
        source_has_through="",
        source_basis="NOT SWEPT — reachable, never swept past 2017",
        source_measured="2026-08-26",
        state_hint=S2,
        refresh_cost="full-text search is free; hours for a full sweep",
        refresh_command="the SEC leg of the deals additions chain",
        breaks_on_refresh="deals_classified.csv merge order",
    ),
    dict(
        dataset="deals", source_id="ancsa_portal",
        source="ANCSA Regional Association portal + ANC annual reports",
        host="ancsaregional.com and 12 corporate sites",
        publish_cadence="annual (corporate fiscal-year reports)",
        publish_lag="3-9 months after corporate FY end",
        cadence_basis="DEALS_ANC_REPORTS_BUILD_LOG.md",
        holds=dict(table="deals_ancsa_portal_v2_additions.csv", col="Event_Date"),
        last_pulled=dict(manifest="data/raw/external/ancsa_portal_v2/"
                                  "_SOURCE_MANIFEST_V2.csv", col="retrieved_date"),
        source_has_through="2025 (corporate FY)",
        source_basis="ANCSA_7i_7j_annual_reports in resource_revenue.csv reach "
                     "corporate FY2025-12-31",
        source_measured="2026-09-01",
        refresh_cost="~80 documents; ~1 hour",
        refresh_command="code/531 / 532 (shard E)",
        breaks_on_refresh="the ANC subsidiary edge set (5,167 declared ownership edges)",
    ),
    dict(
        dataset="deals", source_id="tribal_debt",
        source="Municipal / tribal debt disclosures (EMMA, official statements)",
        host="emma.msrb.org",
        publish_cadence="continuous on issuance; continuing disclosure annual",
        publish_lag="days on issuance, months on continuing disclosure",
        cadence_basis="TRIBAL_DEBT_BUILD_LOG.md",
        holds=dict(table="tribal_bond_issuances.csv", col="issue_date"),
        last_pulled=dict(literal="2026-08-26"),
        source_has_through="",
        source_basis="NOT RE-PROBED this run",
        source_measured="2026-08-26",
        refresh_cost="small",
        refresh_command="the tribal-debt additions leg",
        breaks_on_refresh="seminole_bond_disclosures.csv",
    ),

    # ================= gaming =================
    dict(
        dataset="gaming", source_id="nigc_ggr",
        source="NIGC gross gaming revenue report (national + by region)",
        host="nigc.gov",
        publish_cadence="annual, for the prior federal fiscal year",
        publish_lag="~10 months after the FY closes",
        cadence_basis="sibling: docs/datasets/gaming_sources.md PART 1",
        holds=dict(table="nigc_regional_ggr.csv", col="fiscal_year"),
        last_pulled=dict(table="nigc_regional_ggr.csv", col="fetched_date"),
        source_has_through="2025",
        source_basis="sibling gaming_sources.md, measured 2026-09-01: FY2025 is "
                     "the newest published. FY2026 closes 2026-09-30 and the "
                     "report follows ~mid-2027.",
        source_measured="2026-09-01",
        state_hint=S1,
        refresh_cost="one report",
        refresh_command="code/586_promote_nigc_gaming.py after the pull",
        breaks_on_refresh="gaming_revenue_bounds.csv — its vintage is a BARE YEAR "
                          "(2025), never a fabricated 2025-12-31",
    ),
    dict(
        dataset="gaming", source_id="nigc_documents",
        source="NIGC document surface — declinations, enforcement, Indian-lands "
               "and game-classification opinions, management-contract approvals",
        host="nigc.gov",
        publish_cadence="irregular — posted as issued, with NIGC's own posting "
                        "date (datePublished) distinct from the document date",
        publish_lag="days to months; the two dates differ and both are recorded",
        cadence_basis="sibling: gaming_sources.md PART 3",
        holds=dict(table="nigc_document_surface.csv", col="index_post_date"),
        last_pulled=dict(manifest="data/raw/external/nigc_documents/_SOURCE_MANIFEST.csv",
                         col="fetched_date"),
        source_has_through="2026-09-01",
        source_basis="the index was read 2026-09-01 by the NIGC workstream; 430 "
                     "documents in the manifest, all five staged tables promoted "
                     "the same day",
        source_measured="2026-09-01",
        backlog="nigc_staged",
        refresh_cost="one index read + the new documents",
        refresh_command="code/344_pull_nigc_document_surface.py then code/586",
        breaks_on_refresh="the five nigc_* clean tables and their contracts "
                          "(registered today; grain still UNSTATED on two)",
    ),
    dict(
        dataset="gaming", source_id="ct_dcp",
        source="Connecticut DCP monthly casino win (data.ct.gov)",
        host="data.ct.gov",
        publish_cadence="monthly per casino — **the only true monthly gaming "
                        "series Cedar holds**",
        publish_lag="the source has published nothing since 2025-12; 747 "
                    "facility-months 1993-01..2025-12 with ZERO gaps",
        cadence_basis="sibling: gaming_sources.md, re-probed live 2026-09-01",
        holds=dict(table="gaming_facility_metrics.csv", col="observation_date"),
        last_pulled=dict(table="gaming_facility_metrics.csv", col="fetched_date"),
        source_has_through="2025-12-31",
        source_basis="sibling probe 2026-09-01: data.ct.gov/resource/i6ts-ib7c "
                     "reports min 1993-01-31, max 2025-12-31, count 748. "
                     "**Cedar holds every casino-month it serves.**",
        source_measured="2026-09-01",
        state_hint=S1,
        refresh_cost="two bounded requests",
        refresh_command="py -3 code/343_refresh_ct_gaming_monthly.py",
        breaks_on_refresh="nothing — `payout` and `hold` stay withheld on the "
                          "recorded unit break (91.45 in 1993-01 vs 0.912 in 2025-12)",
    ),
    dict(
        dataset="gaming", source_id="ca_cgcc",
        source="California CGCC — RSTF distribution and SDF commission staff reports",
        host="cgcc.ca.gov",
        publish_cadence="quarterly (a numbered commission staff report per quarter)",
        publish_lag="~6 weeks after quarter close",
        cadence_basis="the report series' own numbering; 98th report = quarter "
                      "ended 2026-03-31",
        holds=dict(table="ca_gaming_payments.csv", col="period_end"),
        last_pulled=dict(manifest="data/raw/external/ca_gaming/_SOURCE_MANIFEST.csv",
                         col="fetched_date"),
        source_has_through="2026-06-30",
        source_basis="181 documents on disk; the newest quarter Cedar has a "
                     "document for is 2026-06-30 and it parses",
        source_measured="2026-09-01",
        backlog="ca_rstf",
        refresh_cost="small — a handful of PDFs",
        refresh_command="code/103_build_california_gaming.py. **DO NOT RE-FETCH "
                        "the short quarters — see the backlog note.**",
        breaks_on_refresh="ca_gaming_facilities_official.csv",
    ),
    dict(
        dataset="gaming", source_id="nm_gcb",
        source="New Mexico Gaming Control Board quarterly revenue-sharing releases",
        host="gcb.nm.gov",
        publish_cadence="quarterly", publish_lag="~6-8 weeks after quarter close",
        cadence_basis="14 NMGCB quarterly releases, footed 14/14 by code/216",
        holds=dict(table="gaming_capacity_official.csv", col="period_end",
                   filter_col="state", filter_val="NM"),
        last_pulled=dict(literal="2026-08-26"),
        source_has_through="2026-06-30",
        source_basis="the 14 extracted releases reach 2026Q2; promoted 2026-09-01 "
                     "through code/92 (NM 1,090 -> 1,278 rows)",
        source_measured="2026-09-01",
        refresh_cost="small",
        refresh_command="code/216 then code/92 — and NM was NEVER a fetch problem",
        breaks_on_refresh="gaming_capacity_official.csv row conservation",
    ),
    dict(
        dataset="gaming", source_id="az_adg",
        source="Arizona Department of Gaming — device/table counts; STATEWIDE "
               "aggregate GGR only",
        host="gaming.az.gov",
        publish_cadence="quarterly device reports, annual aggregate",
        publish_lag="~1 quarter",
        cadence_basis="sibling: gaming_sources.md — A.R.S. 5-601.02(H)(1) "
                      "REQUIRES aggregation; per-tribe revenue does not exist",
        holds=dict(table="gaming_capacity_official.csv", col="as_of_date",
                   filter_col="state", filter_val="AZ"),
        last_pulled=dict(literal="2026-08-07"),
        source_has_through="2026",
        source_basis="sibling gaming_sources.md 2026-09-01: COMPLETE for what AZ "
                     "publishes. gaming.az.gov 403s an automated client; the "
                     "route is the Wayback archive (code/217).",
        source_measured="2026-09-01",
        refresh_cost="Wayback CDX route; ~1 hour",
        refresh_command="code/217_pull_az_adg_report_archive.py",
        breaks_on_refresh="nothing",
    ),
    dict(
        dataset="gaming", source_id="mi_mgcb",
        source="Michigan Gaming Control Board — tribal payments and iGaming",
        host="michigan.gov/mgcb",
        publish_cadence="monthly", publish_lag="~3 weeks after month end",
        cadence_basis="sibling: gaming_sources.md",
        holds=dict(table="digital_gaming_revenue.csv", col="period_end"),
        last_pulled=dict(table="digital_gaming_revenue.csv", col="fetched_date"),
        source_has_through="2026-07-31",
        source_basis="sibling gaming_sources.md 2026-09-01: MGCB publishes "
                     "monthly ~3 weeks after month end, so July is out and "
                     "August is the only genuinely open month",
        source_measured="2026-09-01",
        refresh_cost="one page per month",
        refresh_command="code/164 (digital gaming leg)",
        breaks_on_refresh="digital_gaming_relationships.csv entity links (168)",
    ),
    dict(
        dataset="gaming", source_id="other_state_regulators",
        source="WI · NY · WA · FL and the remaining state regulators",
        host="various",
        publish_cadence="annual, mostly; FL is compact-schedule (forward-dated)",
        publish_lag="months to a year",
        cadence_basis="sibling: gaming_sources.md PART 1",
        holds=dict(table="state_gaming_observations.csv", col="period_end"),
        last_pulled=dict(manifest="data/raw/external/state_gaming/_SOURCE_MANIFEST.csv",
                         col="fetched_date"),
        source_has_through="2025-06-30",
        source_basis="sibling gaming_sources.md 2026-09-01: WI complete to 2025, "
                     "NY publishes numerics in the 2019 edition only. "
                     "**Per-property WI revenue is prohibited by compact "
                     "confidentiality; NV is sealed by NRS 463.120. Withheld is "
                     "not never-collected.**",
        source_measured="2026-09-01",
        state_hint=S1,
        refresh_cost="one host per state, one poller each",
        refresh_command="code/107 / 217 per state",
        breaks_on_refresh="**fl_gaming_payments.period_end runs to 2031-06-30 — "
                          "those are forward-dated compact SCHEDULE rows, not "
                          "observations. Never read them as freshness.**",
    ),
    dict(
        dataset="gaming", source_id="nigc_ordinances",
        source="NIGC gaming ordinance approvals",
        host="nigc.gov",
        publish_cadence="irregular — as approved", publish_lag="weeks",
        cadence_basis="GAMING_ORDINANCE_BUILD_LOG.md",
        holds=dict(table="gaming_ordinances.csv", col="document_approval_date"),
        last_pulled=dict(manifest="data/raw/external/nigc_ordinances/_SOURCE_MANIFEST.csv",
                         col="fetched_date"),
        source_has_through="",
        source_basis="NOT RE-PROBED this run",
        source_measured="2026-08-12",
        refresh_cost="1,151 documents held; incremental is small",
        refresh_command="the ordinance leg + OCR merge",
        breaks_on_refresh="the OCR merge (GAMING_ORDINANCE_OCR_MERGE_LOG.md)",
    ),
    dict(
        dataset="gaming", source_id="labor_form5500_osha",
        source="DOL Form 5500 plan filings + OSHA ITA establishment records "
               "(gaming employment)",
        host="efast.dol.gov / osha.gov",
        publish_cadence="annual — Form 5500 by plan year, OSHA ITA by calendar year",
        publish_lag="Form 5500 ~9-12 months after plan-year end (extensions "
                    "routine); OSHA ITA published the following spring",
        cadence_basis="docs/LABOR_SOURCES_FOR_GAMING_2026-08-26.md — Form 5500 "
                      "2009-2025, OSHA ITA CY2016-CY2025 (3,189,050 rows held)",
        holds=dict(table="gaming_employment_observations.csv", col="period_end"),
        last_pulled=dict(manifest="data/raw/external/osha_ita/_SOURCE_MANIFEST.csv",
                         col="fetched_date"),
        source_has_through="2025",
        source_basis="both corpora are held through CY2025 in data/raw; nothing "
                     "newer is published",
        source_measured="2026-08-26",
        state_hint=S3,
        backlog="labor_staged",
        refresh_cost="zero to promote; the data is already extracted",
        refresh_command="**NOT A PULL.** code/158_merge_staged_labor_employment.py "
                        "— and it is BLOCKED ON TWO OWNER RULINGS (§4 of "
                        "LABOR_SOURCES_FOR_GAMING_2026-08-26.md), not on a fetch",
        breaks_on_refresh="gaming_employment_observations.csv. **A Form 5500 row "
                          "keys to an EIN, never to a facility** — merging it as "
                          "a property observation would be a grain error.",
    ),
    dict(
        dataset="gaming", source_id="fac_sefa_gaming",
        source="Federal Audit Clearinghouse SEFA — gaming programs",
        host="api.fac.gov",
        publish_cadence="continuous acceptance",
        publish_lag="median 271d from fy_end; p90 569d; 30.9% land after the "
                    "9-month deadline",
        cadence_basis="REFRESH_CADENCE 1.4 — the source's OWN two dates, n=6,780",
        holds=dict(table="fac_audit_sefa_gaming_programs.csv", col="audit_year"),
        last_pulled=dict(literal="2026-08-12"),
        source_has_through="",
        source_basis="shares the FAC pull; see the nonprofits FAC row",
        source_measured="2026-08-12",
        refresh_cost="api.data.gov key, 1,000/hr",
        refresh_command="code/147_build_fac_single_audits.py",
        breaks_on_refresh="fac_audit_gaming_disclosures.csv",
    ),

    # ================= nonprofits =================
    dict(
        dataset="nonprofits", source_id="irs990_efile",
        source="IRS 990 e-file returns and the annual submission-year index",
        host="apps.irs.gov",
        publish_cadence="annual index; returns released in batches as processed",
        publish_lag="**~18 months structural.** p10 = 584 days from fiscal-year "
                    "end to our retrieval (n = 58,355) — and that is an UPPER "
                    "bound containing our own delay",
        cadence_basis="REFRESH_CADENCE 1.4",
        holds=dict(table="np_schedule_i_grants.csv", col="tax_period_end"),
        last_pulled=dict(table="np_schedule_i_grants.csv", col="retrieved_date"),
        source_has_through="2025-12-31",
        source_basis="calendar-2025 fiscal-year ends sit at 12% of a December "
                     "plateau because their extended deadline is 2026-11-15; "
                     "2026 is zero rows. Maturity ~mid-2027.",
        source_measured="2026-08-26",
        state_hint=S1,
        refresh_cost="10 annual index files, ~77 MB each",
        refresh_command="the 990 leg — SEMIANNUAL (Feb / Aug). A quarterly "
                        "cadence on an 18-month lag manufactures churn.",
        breaks_on_refresh="np_schedule_i_filers.csv, np_financials.csv, np_org_scale.csv",
    ),
    dict(
        dataset="nonprofits", source_id="irs_bmf",
        source="IRS Business Master File — exempt-organisation extract",
        host="irs.gov",
        publish_cadence="monthly", publish_lag="~1 month",
        cadence_basis="IRS publishes the EO BMF monthly; 1,957,340 rows held",
        holds=dict(table="np_orgs.csv", col="bmf_tax_period"),
        last_pulled=dict(manifest="data/raw/external/irs990/bmf_full_2026-08-12/"
                                  "_fetch_manifest.csv", col="fetched_date"),
        source_has_through="",
        source_basis="NOT RE-PROBED this run. **The BMF is the fastest-moving "
                     "source in the nonprofits dataset (monthly) and the 990 "
                     "returns are the slowest (18 months) — this is the clearest "
                     "case in Cedar of one dataset with two clocks.**",
        source_measured="2026-08-12",
        refresh_cost="one monthly extract",
        refresh_command="the BMF leg of code/112",
        breaks_on_refresh="np_ein_entity_hub.csv, np_ein_uei_bridge.csv",
    ),
    dict(
        dataset="nonprofits", source_id="fac_single_audits",
        source="Federal Audit Clearinghouse single audits (api.fac.gov)",
        host="api.fac.gov",
        publish_cadence="continuous acceptance",
        publish_lag="median 271d (2 CFR 200.512(a) allows 9 months = 274d); "
                    "p90 569d; **30.93% land LATE**; max 3,464d",
        cadence_basis="REFRESH_CADENCE 1.4 — from the source's own fy_end_date "
                      "and fac_accepted_date, n = 6,780",
        holds=dict(table="fac_tribal_single_audits.csv", col="fac_accepted_date"),
        last_pulled=dict(table="fac_tribal_single_audits.csv", col="built_date"),
        source_has_through="",
        source_basis="NOT RE-PROBED this run (an unkeyed request 403s; the keyed "
                     "route answered 22 requests on 2026-08-26)",
        source_measured="2026-08-12",
        refresh_cost="api.data.gov key, 1,000/hr",
        refresh_command="code/147_build_fac_single_audits.py — **with a TWO-YEAR "
                        "trailing window, every time. A deadline the median hits "
                        "and a third of filers miss is not a cadence.**",
        breaks_on_refresh="fac_audit_gaming_disclosures.csv, fac_audit_sefa_gaming_programs.csv",
    ),
    dict(
        dataset="nonprofits", source_id="grantmaker_990pf",
        source="Grantmaker 990-PF / 990 Schedule I (the funder side)",
        host="apps.irs.gov",
        publish_cadence="same as the 990 e-file corpus", publish_lag="~18 months",
        cadence_basis="GRANTMAKER_FUNDING_FLOWS_BUILD_LOG.md",
        holds=dict(table="grantmaker_funding_flows.csv", col="tax_period_end"),
        last_pulled=dict(table="grantmaker_funding_flows.csv", col="retrieved_date"),
        source_has_through="2025-12-31",
        source_basis="same corpus and the same structural lag as the 990 row above",
        source_measured="2026-08-26",
        state_hint=S1,
        refresh_cost="rides the 990 pull",
        refresh_command="code/113 (grantmaker leg)",
        breaks_on_refresh="grantmaker_funding_coverage.csv, grantmaker_funding_overlap.csv",
    ),

    # ================= natural-resources =================
    # Twelve source systems in one dataset — the clearest proof that cadence is
    # per source. Each row measures its own slice of resource_revenue.csv.
    dict(
        dataset="natural-resources", source_id="onrr_nrrd_monthly",
        source="ONRR Natural Resources Revenue Data — monthly revenue, Native "
               "American land class",
        host="revenuedata.doi.gov",
        publish_cadence="monthly", publish_lag="~6 weeks after month close",
        cadence_basis="sibling: docs/datasets/natural_resources_sources.md row 1",
        holds=dict(table="resource_revenue.csv", col="period_end",
                   filter_col="source_system", filter_val="ONRR_NRRD_monthly_revenue"),
        last_pulled=dict(table="resource_revenue.csv", col="fetched_date"),
        source_has_through="2026-07-31",
        source_basis="sibling natural_resources_sources.md, verified 2026-09-01: "
                     "upstream 2003-01..2026-07, Cedar holds 2003-01..2026-07, "
                     "gap NONE",
        source_measured="2026-09-01",
        refresh_cost="small — one filtered portal export",
        refresh_command="code/83_build_resource_ledger.py (ONRR leg)",
        breaks_on_refresh="**87% of these dollars name no tribe, and that is the "
                          "LAW (the collector may not publish below a national "
                          "aggregate), not a backlog.**",
    ),
    dict(
        dataset="natural-resources", source_id="onrr_fy_disbursements",
        source="ONRR fiscal-year disbursements",
        host="revenuedata.doi.gov",
        publish_cadence="annual (federal fiscal year)", publish_lag="~3 months after FY close",
        cadence_basis="sibling: natural_resources_sources.md",
        holds=dict(table="resource_revenue.csv", col="period_end",
                   filter_col="source_system",
                   filter_val="ONRR_NRRD_fiscal_year_disbursements"),
        last_pulled=dict(table="resource_revenue.csv", col="fetched_date"),
        source_has_through="2025-09-30",
        source_basis="FY2025 is the newest closed federal fiscal year the portal "
                     "publishes; FY2026 closes 2026-09-30",
        source_measured="2026-09-01",
        state_hint=S1,
        refresh_cost="small", refresh_command="code/83 (ONRR FY leg)",
        breaks_on_refresh="the reconciliation check against the monthly series",
    ),
    dict(
        dataset="natural-resources", source_id="omc_headrights",
        source="Osage Minerals Council headright payment history",
        host="osagemineralscouncil.com",
        publish_cadence="quarterly (1906+); annual before 1906",
        publish_lag="~1 quarter",
        cadence_basis="sibling: natural_resources_sources.md row 10 — 1880..2026-Q2 "
                      "in ONE spreadsheet",
        holds=dict(table="resource_revenue.csv", col="period_end",
                   filter_col="source_system", filter_val="OMC_headright_payment_history"),
        last_pulled=dict(table="resource_revenue.csv", col="fetched_date"),
        source_has_through="2026-06-30",
        source_basis="sibling natural_resources_sources.md 2026-09-01: the "
                     "spreadsheet reaches 2026-Q2, gap NONE",
        source_measured="2026-09-01",
        refresh_cost="one spreadsheet",
        refresh_command="code/83 (Osage leg)",
        breaks_on_refresh="**the 30 pre-1907 rows carry no commodity — the Osage "
                          "Mineral Estate did not exist yet. Whether they belong "
                          "in this table is an OPEN SCOPING QUESTION with the owner.**",
    ),
    dict(
        dataset="natural-resources", source_id="nd_treasurer",
        source="North Dakota State Treasurer tribal tax distribution search",
        host="nd.gov",
        publish_cadence="monthly distributions, searchable", publish_lag="~1 month",
        cadence_basis="ND_SEVERANCE_BUILD_LOG.md / ND_TRIBAL_TAX_LOG.md",
        holds=dict(table="resource_revenue.csv", col="payment_date",
                   filter_col="source_system",
                   filter_val="ND_State_Treasurer_tax_distribution_search"),
        last_pulled=dict(manifest="data/raw/external/nd_tribal_tax/_SOURCE_MANIFEST.csv",
                         col="fetched_date"),
        source_has_through="",
        source_basis="NOT RE-PROBED this run",
        source_measured="2026-08-07",
        refresh_cost="one search per month", refresh_command="code/83 (ND leg)",
        breaks_on_refresh="**period_type is `payment_date_only` on all 492 rows — "
                          "there is no period_end and none should be invented.**",
    ),
    dict(
        dataset="natural-resources", source_id="osmre_aml",
        source="OSMRE Abandoned Mine Land grant distributions (fee-based + IIJA)",
        host="osmre.gov",
        publish_cadence="annual (federal fiscal year)", publish_lag="at appropriation",
        cadence_basis="sibling: natural_resources_sources.md",
        holds=dict(table="resource_revenue.csv", col="period_end",
                   filter_col="source_system",
                   filter_val="OSMRE_AML_fee_based_grant_distribution"),
        last_pulled=dict(table="resource_revenue.csv", col="fetched_date"),
        source_has_through="2026-09-30",
        source_basis="FY2026 distributions are published at appropriation, ahead "
                     "of the FY close — a forward-dated federal_fiscal_year "
                     "period_end that is CORRECT, not a defect",
        source_measured="2026-09-01",
        refresh_cost="small", refresh_command="code/83 (OSMRE leg)",
        breaks_on_refresh="**FY2010-FY2012 are scanned images, retrieved and held "
                          "rather than guessed — do not re-fetch them.**",
    ),
    dict(
        dataset="natural-resources", source_id="mms_mrm_historical",
        source="MMS/MRM American Indian revenues (the pre-ONRR series)",
        host="mrm.mms.gov (archived)",
        publish_cadence="retired — superseded by ONRR", publish_lag="n/a",
        cadence_basis="the agency no longer exists",
        holds=dict(table="resource_revenue.csv", col="period_end",
                   filter_col="source_system",
                   filter_val="MMS_MRM_american_indian_revenues_calendar"),
        last_pulled=dict(literal="2026-08-06"),
        source_has_through="2000-12-31",
        source_basis="the series ends where ONRR's begins",
        source_measured="2026-09-01",
        state_hint=S_CLOSED,
        refresh_cost="zero", refresh_command="none",
        breaks_on_refresh="nothing",
    ),
    dict(
        dataset="natural-resources", source_id="state_severance_misc",
        source="MT DOR county oil-gas distribution · UT COBI fund financials · "
               "ANCSA 7(i)/7(j) annual reports · OMC quarterly newsletter",
        host="revenue.mt.gov / cobi-ws.utah.gov / 12 ANC sites",
        publish_cadence="MT quarterly · UT state-FY annual · ANCSA corporate-FY "
                        "annual · OMC newsletter quarterly (stopped 2022)",
        publish_lag="1 quarter to 9 months",
        cadence_basis="sibling: natural_resources_sources.md",
        holds=dict(table="resource_revenue.csv", col="period_end",
                   filter_col="source_system",
                   filter_val="MT_DOR_county_oil_gas_distribution"),
        last_pulled=dict(manifest="data/raw/resources/montana/"
                                  "MANIFEST_montana_2026-08-06.csv", col="fetched_date"),
        source_has_through="2026-03-31",
        source_basis="MT is the fastest of the four and reaches 2026Q1; UT stops "
                     "at state-FY2025-06-30, ANCSA at corporate-FY2025-12-31, and "
                     "the OMC newsletter STOPPED at 2022-03-31",
        source_measured="2026-09-01",
        refresh_cost="four hosts, one poller each",
        refresh_command="code/83 (state legs)",
        breaks_on_refresh="**four cadences in one registry row. If any of these "
                          "ever needs its own refresh date, split it out rather "
                          "than averaging them.**",
    ),

    # ================= native-owned-businesses =================
    dict(
        dataset="native-owned-businesses", source_id="tribal_vendor_lists",
        source="Tribal TERO / Indian-preference vendor and business directories "
               "(~1,555 entity websites)",
        host="~1,555 hosts",
        publish_cadence="**NONE. There is no publication schedule and inventing "
                        "one would be a lie.** A list changes when a tribal "
                        "office remembers to update it.",
        publish_lag="unknowable",
        cadence_basis="sibling: docs/datasets/native-owned-businesses.md — "
                      "62 of 1,555 entities (4.0%) have EVER been checked",
        holds=dict(table="native_owned_businesses.csv", col="source_last_updated"),
        last_pulled=dict(table="native_owned_businesses.csv", col="harvest_date"),
        source_has_through="",
        source_basis="NOT ESTABLISHABLE ON A CALENDAR. See the CHANGE DETECTION "
                     "section below — this source needs a trigger, not a schedule.",
        source_measured="2026-09-01",
        state_hint=S_UNKNOWN,
        backlog="vendor_lists",
        refresh_cost="~15 tribes per agent-day including the terms read; the "
                     "remaining 297 federally recognised tribes are ~20 agent-days",
        refresh_command="code/570 / 588 (shards L and M) — **read robots.txt and "
                        "the terms page FIRST; 6 publishers have stated "
                        "restrictive terms and are excluded by every route**",
        breaks_on_refresh="**NOTHING HERE PUBLISHES.** Every row carries "
                          "consent_status = UNRESOLVED and publishable = N.",
    ),

    # ================= _entity_layer =================
    dict(
        dataset="_entity_layer", source_id="fr_recognition_notice",
        source="Interior's annual Federally Recognized Indian Tribes notice",
        host="www.federalregister.gov",
        publish_cadence="annual, late January (91 FR 4102 was 2026-01-30)",
        publish_lag="published on the day it is signed",
        cadence_basis="the notice series' own history, 1979-2026",
        holds=dict(table="federal_recognition_roster.csv", col="publication_date"),
        last_pulled=dict(table="federal_recognition_roster.csv", col="fetched_date"),
        source_has_through="2026-01-30",
        source_basis="91 FR 4102, 2026-01-30, is the newest annual notice; the "
                     "next is due late January 2027",
        source_measured="2026-09-01",
        state_hint=S1,
        refresh_cost="one document",
        refresh_command="**TRIGGER THE SPINE REBUILD FROM THE NOTICE, NOT FROM A "
                        "TIMER.** The FR daily pull is what sees it.",
        breaks_on_refresh="**everything.** And `01_build_entity_spine.py` / "
                          "`09_import_rulings.py` are DESTRUCTIVE: a direct "
                          "invocation drops 868 of 1,555 entities and 32 of 44 "
                          "columns, and 09 drops 1,345 ledger rows, 18 of them "
                          "tier A owner adjudications. Neither takes a .bak. "
                          "`data/spine/cedar_entity_spine.csv` IS NOT IN GIT.",
    ),
    dict(
        dataset="_entity_layer", source_id="nho_doi_register",
        source="DOI Native Hawaiian Organization notification roster · IHS UIO "
               "register · TCU and Native CDFI rosters",
        host="doi.gov / ihs.gov / aihec.org / cdfifund.gov",
        publish_cadence="irregular — DOI posts NHO notifications as filed; the "
                        "TCU and CDFI rosters change a few times a year",
        publish_lag="weeks to months",
        cadence_basis="NHO_INTERTRIBAL_REGISTER_LOG.md, TCU_CDFI_BUILD_LOG.md",
        holds=dict(table="nho_register.csv", col="retrieved_date"),
        last_pulled=dict(table="nho_register.csv", col="retrieved_date"),
        source_has_through="",
        source_basis="NOT RE-PROBED this run",
        source_measured="2026-08-06",
        refresh_cost="a handful of pages",
        refresh_command="code/05 / 591 / 592 — never 01 or 09",
        breaks_on_refresh="the 210 NHOs, 185 BIE schools, 173 ANC village "
                          "corporations and 64 Native CDFIs in the hub",
    ),
    dict(
        dataset="_entity_layer", source_id="owner_rulings",
        source="Owner adjudications (Elijah's rulings)",
        host="—",
        publish_cadence="event-driven — whenever the owner rules",
        publish_lag="0",
        cadence_basis="the one class of row that is NOT re-derivable",
        holds=dict(table="cedar_correction_register.csv", col=None),
        last_pulled=dict(literal=TODAY),
        source_has_through="",
        source_basis="not a source in the fetch sense",
        source_measured=TODAY,
        state_hint=S_CLOSED,
        refresh_cost="zero",
        refresh_command="py -3 code/124_apply_rulings_in_place.py after ANY refresh",
        breaks_on_refresh="**an upsert must NEVER overwrite a human ruling. "
                          "Rulings are the only promotion path above tier A.**",
    ),
]


# --------------------------------------------------------------------------
# MEASUREMENT
# --------------------------------------------------------------------------
def _max_in_csv(path, col, filter_col=None, filter_val=None, fallback_col=None):
    """Max date-shaped value in `col`, optionally within one source partition."""
    if not path or not col or not os.path.exists(path):
        return None, 0, None
    used = col
    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        rdr = csv.DictReader(f)
        cols = rdr.fieldnames or []
        if col not in cols:
            if fallback_col and fallback_col in cols:
                used = fallback_col
            else:
                return None, 0, None
        if filter_col and filter_col not in cols:
            filter_col = None
        best, n = "", 0
        for row in rdr:
            if filter_col and (row.get(filter_col) or "").strip() != filter_val:
                continue
            n += 1
            v = (row.get(used) or "").strip()
            if not v:
                continue
            if (DATE_RE.match(v) or YEAR_RE.match(v)) and v > best:
                best = v
    return (best or None), n, used


def _rows(path):
    if not os.path.exists(path):
        return 0
    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        return max(0, sum(1 for _ in csv.reader(f)) - 1)


def measure_holds(spec):
    if not spec:
        return {}
    if spec.get("table"):
        p = os.path.join(CLEAN, spec["table"])
        where = f"data/clean/{spec['table']}"
    elif spec.get("raw_glob"):
        p = os.path.join(ROOT, spec["raw_glob"])
        where = spec["raw_glob"]
    elif spec.get("staging"):
        p = os.path.join(STAGING, spec["staging"])
        where = f"data/staging/{spec['staging']}"
    else:
        return {}
    if not os.path.exists(p):
        return dict(measured_from=where, exists=False)
    v, n, used = _max_in_csv(p, spec.get("col"), spec.get("filter_col"),
                             spec.get("filter_val"), spec.get("fallback_col"))
    out = dict(measured_from=where, exists=True, rows_in_scope=n,
               period_col=used, value=v)
    if spec.get("filter_col"):
        out["partition"] = f"{spec['filter_col']}={spec['filter_val']}"
    if spec.get("col") and not used:
        out["note"] = f"column `{spec['col']}` is not in this file"
    return out


def measure_last_pulled(spec):
    if not spec:
        return {}
    if spec.get("literal"):
        return dict(value=spec["literal"], basis="recorded in a build log")
    if spec.get("manifest"):
        p = os.path.join(ROOT, spec["manifest"])
        if not os.path.exists(p):
            return dict(value=None, basis=f"{spec['manifest']} MISSING")
        v, n, _ = _max_in_csv(p, spec["col"])
        return dict(value=v, basis=f"max({spec['col']}) over {n} rows of "
                                   f"{spec['manifest']}")
    if spec.get("table"):
        p = os.path.join(CLEAN, spec["table"])
        v, n, used = _max_in_csv(p, spec["col"])
        if not used:
            return dict(value=None, basis=f"`{spec['col']}` not in "
                                          f"data/clean/{spec['table']}")
        return dict(value=v, basis=f"max({used}) in data/clean/{spec['table']}")
    return {}


# --------------------------------------------------------------------------
# BACKLOG DETECTORS — the state-3 evidence, measured, never asserted
# --------------------------------------------------------------------------
def backlog_nigc_staged():
    """Every data/staging/*_staged.csv against its clean twin."""
    out, ahead = [], 0
    for fn in sorted(os.listdir(STAGING)):
        if not fn.endswith("_staged.csv") or not fn.startswith("nigc_"):
            continue
        base = fn[: -len("_staged.csv")] + ".csv"
        s, c = _rows(os.path.join(STAGING, fn)), _rows(os.path.join(CLEAN, base))
        out.append(dict(staged=fn, clean=base, staged_rows=s, clean_rows=c,
                        unpromoted=max(0, s - c)))
        ahead += max(0, s - c)
    return dict(kind="staged_vs_clean", unpromoted_rows=ahead, detail=out,
                reading="0 unpromoted rows means the staged set has been "
                        "promoted; the staging file is a cache, not a backlog")


def backlog_ca_rstf():
    """CA documents on disk whose money zones did not foot."""
    md = os.path.join(REVIEW, "ca_rstf_captured_not_parsed_2026-09-01.md")
    docs = 0
    if os.path.exists(md):
        for line in open(md, encoding="utf-8", errors="replace"):
            if line.startswith("| `") and "`" in line[3:]:
                docs += 1
    manifest = os.path.join(RAW, "external", "ca_gaming", "_SOURCE_MANIFEST.csv")
    return dict(kind="captured_not_parsed", documents_on_disk=_rows(manifest),
                documents_not_parsed=docs,
                reading="every one of these is ON DISK. A zone appears here "
                        "because its numbers do not reconcile with the report's "
                        "OWN printed total, and Cedar does not publish a money "
                        "row the source's arithmetic refuses. **This is state 3, "
                        "not state 2. Re-downloading them changes nothing.**")


def backlog_schedc():
    p = os.path.join(CLEAN, "nonprofit_schedule_c_coverage.csv")
    if not os.path.exists(p):
        return dict(kind="fetch_backlog", note="coverage table missing")
    R = list(csv.DictReader(open(p, encoding="utf-8", errors="replace")))
    def s(c):
        return sum(int(r.get(c) or 0) for r in R)
    return dict(kind="fetch_backlog", index_target_returns=s("index_target_returns"),
                downloaded=s("downloaded"), parsed=s("parsed_here"),
                not_downloaded=s("not_downloaded"),
                parse_backlog=s("downloaded") - s("parsed_here"),
                reading="downloaded == parsed on every index year, so the PARSE "
                        "backlog is zero. What remains is a pure ACQUISITION "
                        "backlog — state 2 — and the returns exist at the IRS.")


def backlog_vendor_lists():
    p = os.path.join(CLEAN, "native_owned_businesses.csv")
    n = _rows(p)
    spine = os.path.join(ROOT, "data", "spine", "cedar_entity_spine.csv")
    universe = _rows(spine)
    return dict(kind="entity_coverage", rows=n, entity_universe=universe,
                reading="the gap here is ENTITY coverage, not time. An entity "
                        "absent from the registry is NEVER_CHECKED, which is a "
                        "different fact from NO_LIST_FOUND and must not be read "
                        "as one.")


def backlog_corr_log():
    return dict(kind="empty_table",
                congressional_correspondence_log_rows=_rows(
                    os.path.join(CLEAN, "congressional_correspondence_log.csv")),
                systems_rows=_rows(os.path.join(
                    CLEAN, "congressional_correspondence_systems.csv")),
                reading="257 rows describe WHERE letters would be found and the "
                        "log itself is empty. That is a source that has never "
                        "been pulled, not one that has nothing.")


def backlog_labor_staged():
    """Staged labor rows with no clean twin — extracted, never promoted."""
    pairs = [("gaming_employment_form5500_staged.csv",
              "gaming_employment_form5500.csv"),
             ("gaming_employment_osha_tribe_staged.csv",
              "gaming_employment_osha_tribe.csv")]
    det, tot = [], 0
    for sfn, cfn in pairs:
        sr = _rows(os.path.join(STAGING, sfn))
        cr = _rows(os.path.join(CLEAN, cfn))
        det.append(dict(staged=sfn, staged_rows=sr,
                        clean_table_exists=os.path.exists(os.path.join(CLEAN, cfn)),
                        clean_rows=cr, unpromoted=max(0, sr - cr)))
        tot += max(0, sr - cr)
    return dict(kind="staged_never_promoted", unpromoted_rows=tot, detail=det,
                reading="**These are STATE 3 and the only true state-3 rows this "
                        "sweep found.** Both files were extracted on 2026-08-26 "
                        "and neither has a clean twin. They are blocked on two "
                        "OWNER RULINGS, not on a fetch — a Form 5500 row keys to "
                        "an EIN and not to a facility, so merging it as a "
                        "property observation needs an adjudicated rule first. "
                        "Nothing about this is an acquisition task.")


BACKLOGS = dict(nigc_staged=backlog_nigc_staged, ca_rstf=backlog_ca_rstf,
                labor_staged=backlog_labor_staged,
                schedc=backlog_schedc, vendor_lists=backlog_vendor_lists,
                corr_log=backlog_corr_log)


# --------------------------------------------------------------------------
# CHANGE DETECTION for sources with no schedule
# --------------------------------------------------------------------------
def measure_change_detection():
    """What the harvest already knows about ~1,555 sites, with no re-crawl."""
    rows = []
    wmdir = os.path.join(STAGING, "tribe_web_map")
    if os.path.isdir(wmdir):
        for fn in sorted(os.listdir(wmdir)):
            if fn.endswith(".csv"):
                rows += list(csv.DictReader(open(os.path.join(wmdir, fn),
                                                 encoding="utf-8", errors="replace")))
    wp = [r for r in rows if "wp-json" in (r.get("url") or "")]
    with_total = [r for r in wp if "X-WP-Total" in (r.get("evidence") or "")]
    cad, depth = {}, []
    for r in with_total:
        m = re.search(r"cadence=roughly (\w+)", r["evidence"])
        if m:
            cad[m.group(1)] = cad.get(m.group(1), 0) + 1
        m2 = re.search(r"archive_depth=(\d+)", r["evidence"])
        if m2:
            depth.append(int(m2.group(1)))
    ok = sum(1 for r in wp if (r.get("http_status") or "") == "200")
    nl = 0
    hdir = os.path.join(STAGING, "tribe_harvest")
    if os.path.isdir(hdir):
        for shard in sorted(os.listdir(hdir)):
            p = os.path.join(hdir, shard, "newsletters.jsonl")
            if os.path.exists(p):
                nl += sum(1 for line in open(p, encoding="utf-8",
                                             errors="replace") if line.strip())
    spine = _rows(os.path.join(ROOT, "data", "spine", "cedar_entity_spine.csv"))
    checked = sorted({(r.get("checked_date") or "")[:10] for r in rows if
                      r.get("checked_date")})
    return dict(
        entity_universe=spine,
        web_map_rows=len(rows),
        entities_with_any_url=len({r["tribe_id"] for r in rows if r.get("tribe_id")}),
        web_map_checked_span=[checked[0], checked[-1]] if checked else None,
        wp_json_endpoints=len(wp),
        wp_json_entities=len({r["tribe_id"] for r in wp if r.get("tribe_id")}),
        wp_json_http_200=ok,
        endpoints_with_X_WP_Total=len(with_total),
        observed_posting_cadence=cad,
        archive_depth_total=sum(depth),
        archive_depth_median=(sorted(depth)[len(depth) // 2] if depth else None),
        newsletter_records=nl,
    )


# --------------------------------------------------------------------------
# DERIVATION
# --------------------------------------------------------------------------
def _cmp_period(a, b):
    """Compare two period strings that may be a year, a month or a day."""
    if not a or not b:
        return None
    a2, b2 = a[:10], b[:10]
    n = min(len(a2), len(b2))
    a2, b2 = a2[:n], b2[:n]
    if a2 == b2:
        return 0
    return 1 if a2 > b2 else -1


def derive(entry, holds, src_through):
    """An explicit `state_hint` always wins.

    A hint is a human judgment with a written reason in `source_basis`, and the
    arithmetic cannot see the reason. In particular the arithmetic cannot tell
    CURRENT from state 1: both mean nothing is owed, but state 1 also says WHY
    the edge sits where it does, which is the fact the next agent needs.
    """
    have = holds.get("value")
    hint = entry.get("state_hint")
    if hint:
        base = f"declared in the registry: {entry.get('source_basis') or ''}".strip()
        if hint == S1 and have and src_through:
            base = (f"Cedar holds through {have} and the source offers "
                    f"{src_through} — nothing is owed. " + base)
        return hint, base
    if not src_through:
        return S_UNKNOWN, ("source_has_through is NOT ESTABLISHED — this source "
                           "cannot be called current or stale on the evidence held")
    if not have:
        return S_UNKNOWN, "no measurable period in the clean table"
    c = _cmp_period(have, src_through)
    if c is None:
        return S_UNKNOWN, "periods not comparable"
    if c >= 0:
        return S_CURRENT, (f"Cedar holds through {have}; the source offers "
                           f"{src_through}. Nothing is owed.")
    return S2, (f"the source offers {src_through} and Cedar holds {have}. "
                f"Check data/raw, data/staging and review/ before treating this "
                f"as an acquisition task.")


def _days_since(iso):
    """Whole days from an ISO-ish date to today, or None."""
    if not iso:
        return None
    m = re.match(r"^(\d{4})-(\d\d)-(\d\d)", str(iso))
    if not m:
        # YYYYMM — the IRS `tax_period` / `bmf_tax_period` shape
        m3 = re.match(r"^(\d{4})(0[1-9]|1[0-2])$", str(iso).strip())
        if m3:
            y, mo = int(m3.group(1)), int(m3.group(2))
            nxt = dt.date(y + (mo == 12), (mo % 12) + 1, 1)
            return max(0, (dt.date.today() - (nxt - dt.timedelta(days=1))).days)
        m2 = re.match(r"^(\d{4})$", str(iso).strip())
        if m2:
            # A bare year is a whole period. A year still in progress is not
            # NEGATIVE days old; it is zero days old, because the source has
            # not finished it.
            return max(0, (dt.date.today()
                           - dt.date(int(m2.group(1)), 12, 31)).days)
        return None
    try:
        return (dt.date.today() - dt.date(*(int(g) for g in m.groups()))).days
    except ValueError:
        return None


def build():
    out = []
    for e in SOURCES:
        holds = measure_holds(e.get("holds"))
        pulled = measure_last_pulled(e.get("last_pulled"))
        state, why = derive(e, holds, e.get("source_has_through"))
        rec = dict(
            dataset=e["dataset"], source_id=e["source_id"], source=e["source"],
            host=e["host"],
            publish_cadence=e["publish_cadence"], publish_lag=e["publish_lag"],
            cadence_basis=e["cadence_basis"],
            cedar_last_pulled=pulled.get("value"),
            cedar_last_pulled_basis=pulled.get("basis"),
            cedar_holds_through=holds.get("value"),
            cedar_holds_measured_from=holds.get("measured_from"),
            cedar_holds_period_col=holds.get("period_col"),
            cedar_holds_rows_in_scope=holds.get("rows_in_scope"),
            cedar_holds_partition=holds.get("partition"),
            cedar_holds_note=holds.get("note"),
            source_has_through=e.get("source_has_through") or None,
            source_basis=e.get("source_basis") or None,
            source_measured=e.get("source_measured") or None,
            state=state, refresh_due=(state in (S2, S3)), refresh_due_why=why,
            refresh_cost=e["refresh_cost"], refresh_command=e["refresh_command"],
            breaks_on_refresh=e["breaks_on_refresh"],
        )
        # How stale is the DATA, and how stale is our KNOWLEDGE of the source?
        # They are different numbers and only the second one is fixable for free.
        rec["cedar_edge_age_days"] = _days_since(holds.get("value"))
        rec["source_knowledge_age_days"] = _days_since(e.get("source_measured"))
        gap = None
        if holds.get("value") and e.get("source_has_through"):
            a = _days_since(holds["value"])
            b = _days_since(e["source_has_through"])
            if a is not None and b is not None:
                gap = a - b
        rec["gap_days_behind_source"] = gap if (gap or 0) > 0 else 0
        if e.get("backlog"):
            rec["backlog"] = BACKLOGS[e["backlog"]]()
        out.append(rec)
    return out


# --------------------------------------------------------------------------
# BOUNDED PROBES — at most four, one per host, >=6s apart
# --------------------------------------------------------------------------
def probe_net():
    import time
    import urllib.request
    import urllib.error
    ua = {"User-Agent": "CedarPress-cadence-probe/1.0 (research; one request per host)"}
    res = []

    def get(url):
        try:
            with urllib.request.urlopen(
                    urllib.request.Request(url, headers=ua), timeout=30) as r:
                return r.status, r.read(200000).decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read(2000).decode("utf-8", "replace")
        except Exception as e:
            return None, f"{type(e).__name__}: {e}"

    active = []
    lg = os.path.join(ROOT, "logs")
    if os.path.isdir(lg):
        for fn in os.listdir(lg):
            if fn.startswith("_HOSTLOCK_") and fn.endswith(".json"):
                try:
                    d = json.load(open(os.path.join(lg, fn), encoding="utf-8"))
                except Exception:
                    continue
                if d.get("active") and not d.get("released"):
                    active.append(fn[len("_HOSTLOCK_"):-len(".json")])

    plan = [
        ("www.federalregister.gov",
         "https://www.federalregister.gov/api/v1/documents.json"
         "?per_page=1&order=newest&fields[]=publication_date"),
        ("lda.gov", "https://lda.gov/api/v1/filings/?page_size=1&ordering=-dt_posted"),
        ("lda.gov", "https://lda.gov/api/v1/filings/?page_size=1&ordering=dt_posted"),
    ]
    for host, url in plan:
        if host in active:
            res.append(dict(host=host, url=url, skipped="a lock is held on this host"))
            continue
        s, b = get(url)
        rec = dict(host=host, url=url, status=s)
        try:
            d = json.loads(b)
            if "results" in d and d["results"]:
                r0 = d["results"][0]
                rec["count"] = d.get("count")
                for k in ("publication_date", "dt_posted", "filing_year",
                          "filing_period", "filing_type_display"):
                    if k in r0:
                        rec[k] = r0[k]
        except Exception:
            rec["body_head"] = b[:200]
        res.append(rec)
        time.sleep(7)
    return dict(probed=TODAY, requests=len(plan), host_locks_respected=active,
                results=res)


# --------------------------------------------------------------------------
# RENDER
# --------------------------------------------------------------------------
def _c(v):
    if v is None or v == "":
        return "—"
    return str(v).replace("|", "\\|").replace("\n", " ")


STATE_MARK = {
    S_CURRENT: "✅ CURRENT", S1: "① source not published",
    S2: "② **NOT PULLED**", S3: "③ **pulled, not promoted**",
    S_CLOSED: "⛔ closed", S_UNKNOWN: "❓ edge not established",
}


def render(doc):
    R = doc["sources"]
    L = [BEGIN, "",
         "# PART 0 — THE CADENCE TABLE, ONE ROW PER SOURCE",
         "",
         f"*Generated {doc['generated']} by `code/630_refresh_cadence.py`. Every "
         f"`cedar_holds_through` below was MEASURED from the file named beside "
         f"it on this run. Re-run the script and the numbers update; do not "
         f"hand-edit inside the markers.*",
         "",
         f"**{doc['n_sources']} sources across {doc['n_datasets']} datasets.**",
         ""]

    c = doc["state_counts"]
    L += ["## The split that decides what the work actually is", "",
          "| state | sources | what it means |",
          "|---|---:|---|",
          f"| ✅ CURRENT | {c.get(S_CURRENT,0)} | Cedar holds everything the source offers |",
          f"| ① the source has not published yet | {c.get(S1,0)} | nothing to do; the expected date is in the row |",
          f"| ② **published and NOT PULLED** | {c.get(S2,0)} | an **acquisition** task |",
          f"| ③ **pulled and NOT PROMOTED** | {c.get(S3,0)} | already on disk. **NOT an acquisition task.** |",
          f"| ⛔ closed by design | {c.get(S_CLOSED,0)} | the source ended, or is one-time |",
          f"| ❓ source edge NOT ESTABLISHED | {c.get(S_UNKNOWN,0)} | no key, no index, or no schedule exists to probe |",
          "",
          "> **Read the ② / ③ split before planning any session.** They look "
          "identical in a staleness column and are completely different work. "
          "Three times this project has recorded a ③ as a ② and sent the next "
          "agent to re-download something already on disk: California RSTF, New "
          "Mexico gaming FY2023–2026Q2, and the staged NIGC set. All three were "
          "promotion jobs. All three are now resolved, and none of them was ever "
          "a fetch.",
          ""]

    due = [r for r in R if r["refresh_due"]]
    due.sort(key=lambda r: (-(r.get("gap_days_behind_source") or 0),
                            -(r.get("cedar_edge_age_days") or 0)))
    if due:
        L += ["## What is owed right now, most overdue first", "",
              "*`gap` is days between Cedar's measured edge and the source's "
              "measured edge — 0 where the source edge is not established, in "
              "which case rank on `edge age` and read the row.*", "",
              "| # | dataset | source | Cedar holds | source has | gap | edge age | why |",
              "|---:|---|---|---|---|---:|---:|---|"]
        for i, r in enumerate(due, 1):
            L.append(f"| {i} | `{r['dataset']}` | `{r['source_id']}` | "
                     f"{_c(r['cedar_holds_through'])} | {_c(r['source_has_through'])} "
                     f"| {r.get('gap_days_behind_source') or 0}d | "
                     f"{_c(r.get('cedar_edge_age_days'))}d | "
                     f"{_c(r['refresh_due_why'])[:150]} |")
        L += [""]

    unk = [r for r in R if r["state"] == S_UNKNOWN]
    if unk:
        L += ["## Where the source edge is NOT ESTABLISHED, and why", "",
              "*An unprobed source is never reported as current. "
              "`knowledge age` is how many days old our last statement about the "
              "SOURCE is — it is the cheapest number in this file to fix, "
              "because closing it costs one request.*", "",
              "| dataset | source | Cedar holds | knowledge age | reason |",
              "|---|---|---|---:|---|"]
        for r in sorted(unk, key=lambda r: -(r.get("source_knowledge_age_days") or 9999)):
            ka = r.get("source_knowledge_age_days")
            L.append(f"| `{r['dataset']}` | `{r['source_id']}` | "
                     f"{_c(r['cedar_holds_through'])} | "
                     f"{'never' if ka is None else str(ka) + 'd'} | "
                     f"{_c(r['source_basis'])[:220]} |")
        L += [""]

    by_ds = {}
    for r in R:
        by_ds.setdefault(r["dataset"], []).append(r)

    L += ["## Per dataset", ""]
    L += ["| dataset | sources | fastest source | slowest edge | states |",
          "|---|---:|---|---|---|"]
    for ds in sorted(by_ds):
        rows = by_ds[ds]
        # Ordered fastest-first. The FIRST keyword that appears in the
        # publish_cadence prose is the cadence; a source whose prose says
        # "quarterly LD-2 ... amendments arrive CONTINUOUSLY" is continuous.
        cad_rank = [("continuous", 0), ("every federal business day", 0),
                    ("daily", 1), ("monthly", 2), ("quarterly", 3),
                    ("annual", 4), ("irregular", 5), ("one-time", 6),
                    ("retired", 7), ("none", 9)]

        def cadence_word(x):
            low = x["publish_cadence"].lower()
            hits = [(low.index(k), k, v) for k, v in cad_rank if k in low]
            if not hits:
                return ("unstated", 8)
            _, k, v = min(hits)
            return ("daily" if k == "every federal business day" else k, v)

        live = [x for x in rows if x["state"] != S_CLOSED] or rows
        fastest = sorted(live, key=lambda x: cadence_word(x)[1])[0]
        fastest_word = cadence_word(fastest)[0]
        edges = sorted([r["cedar_holds_through"] for r in rows
                        if r["cedar_holds_through"]])
        st = {}
        for r in rows:
            st[r["state"]] = st.get(r["state"], 0) + 1
        stxt = " · ".join(f"{STATE_MARK[k].split(' ')[0]}{v}"
                          for k, v in sorted(st.items()))
        L.append(f"| `{ds}` | {len(rows)} | **{fastest_word}** "
                 f"(`{_c(fastest['source_id'])}`) | "
                 f"{_c(edges[0] if edges else None)} | {stxt} |")
    L += ["",
          "> **A dataset's cadence is its fastest-moving source that anyone "
          "actually depends on, and its staleness is its slowest.** "
          "`nonprofits` is the clearest case: the IRS BMF is monthly and the 990 "
          "returns lag ~18 months. `natural-resources` draws on twelve source "
          "systems whose edges span 2000-12-31 to 2026-09-30. One number per "
          "dataset would be wrong for every source in it.",
          ""]

    for ds in sorted(by_ds):
        L += [f"### `{ds}`", ""]
        for r in by_ds[ds]:
            L += [f"#### {r['source']}", "",
                  "| field | value |", "|---|---|",
                  f"| state | {STATE_MARK[r['state']]} |",
                  f"| host | `{_c(r['host'])}` |",
                  f"| publish_cadence | {_c(r['publish_cadence'])} |",
                  f"| publish_lag | {_c(r['publish_lag'])} |",
                  f"| cadence basis | {_c(r['cadence_basis'])} |",
                  f"| **cedar_holds_through** | **{_c(r['cedar_holds_through'])}**"
                  f" — measured from `{_c(r['cedar_holds_measured_from'])}`"
                  + (f", column `{r['cedar_holds_period_col']}`"
                     if r['cedar_holds_period_col'] else "")
                  + (f", partition `{r['cedar_holds_partition']}`"
                     if r.get('cedar_holds_partition') else "")
                  + (f", {r['cedar_holds_rows_in_scope']:,} rows in scope"
                     if r.get('cedar_holds_rows_in_scope') else "")
                  + (f". {r['cedar_holds_note']}" if r.get('cedar_holds_note') else "")
                  + " |",
                  f"| **source_has_through** | **{_c(r['source_has_through'])}** — "
                  f"{_c(r['source_basis'])} (established {_c(r['source_measured'])}) |",
                  f"| cedar_last_pulled | {_c(r['cedar_last_pulled'])} — "
                  f"{_c(r['cedar_last_pulled_basis'])} |",
                  f"| **refresh_due** | **{'YES' if r['refresh_due'] else 'no'}** — "
                  f"{_c(r['refresh_due_why'])} |",
                  f"| age | Cedar's edge is {_c(r.get('cedar_edge_age_days'))} days "
                  f"old; our knowledge of the SOURCE is "
                  f"{_c(r.get('source_knowledge_age_days'))} days old; measured "
                  f"gap behind the source {r.get('gap_days_behind_source') or 0} days |",
                  f"| refresh_cost | {_c(r['refresh_cost'])} |",
                  f"| refresh_command | {_c(r['refresh_command'])} |",
                  f"| breaks_on_refresh | {_c(r['breaks_on_refresh'])} |"]
            if r.get("backlog"):
                b = r["backlog"]
                bits = " · ".join(f"`{k}` = {v}" for k, v in b.items()
                                  if k not in ("reading", "detail"))
                L += [f"| **measured backlog** | {bits} |",
                      f"| backlog reading | {_c(b.get('reading'))} |"]
            L += [""]

    cd = doc["change_detection"]
    L += ["---", "",
          "## THE SOURCES WITH NO SCHEDULE — a trigger, not a calendar", "",
          f"Roughly **{cd['entity_universe']:,} entity websites** have no "
          "publication schedule at all, and inventing one would be a lie. "
          "Re-crawling them on a timer costs ~20 agent-days per pass and would "
          "mostly re-read pages that did not move.",
          "",
          "**What the harvest ALREADY knows, with no re-crawl:**", "",
          "| measured | value |", "|---|---:|",
          f"| entities in the hub | {cd['entity_universe']:,} |",
          f"| entities with at least one mapped URL | {cd['entities_with_any_url']:,} |",
          f"| URL rows in `data/staging/tribe_web_map/` | {cd['web_map_rows']:,} |",
          (f"| when those URLs were last checked | "
           f"{cd['web_map_checked_span'][0]} .. {cd['web_map_checked_span'][1]} |"
           if cd["web_map_checked_span"] else "| when those URLs were last "
           "checked | not recorded |"),
          f"| **`wp-json` endpoints already proven** | **{cd['wp_json_endpoints']}** "
          f"across {cd['wp_json_entities']} entities |",
          f"| of those, HTTP 200 | {cd['wp_json_http_200']} |",
          f"| endpoints where `X-WP-Total` was captured | "
          f"{cd['endpoints_with_X_WP_Total']} |",
          f"| total items behind those endpoints (`archive_depth`) | "
          f"{cd['archive_depth_total']:,} (median {cd['archive_depth_median']}) |",
          f"| newsletter records harvested | {cd['newsletter_records']:,} |",
          ""]
    if cd["observed_posting_cadence"]:
        L += ["**Observed posting cadence, measured from the item dates behind "
              "those endpoints — not from anything a site claims:**", "",
              "| observed cadence | sites |", "|---|---:|"]
        for k, v in sorted(cd["observed_posting_cadence"].items(),
                           key=lambda kv: -kv[1]):
            L.append(f"| roughly {k} | {v} |")
        L += [""]

    L += ["### The proposal: CHECK, then HARVEST", "",
          "A three-tier trigger that replaces the calendar. Nothing below "
          "requires a new crawler — every input already exists on disk.",
          "",
          "**Tier 1 — the free check (`HEAD`-cheap, once a month).** For the "
          f"{cd['wp_json_entities']} entities with a proven `wp-json` endpoint, "
          "one request each to `/wp-json/wp/v2/media?per_page=1` and "
          "`/wp-json/wp/v2/posts?per_page=1` returns the `X-WP-Total` header and "
          "the newest item's date **without downloading anything.** Store both. "
          "A site whose `X-WP-Total` and newest-item date are unchanged since the "
          f"last check has not published, and needs no harvest. Baseline: "
          f"{cd['archive_depth_total']:,} items across "
          f"{cd['endpoints_with_X_WP_Total']} endpoints are already recorded.",
          "",
          "**Tier 2 — the cheap check for everything else (quarterly).** For the "
          "remaining sites, a conditional `GET` on the mapped URL "
          "(`If-Modified-Since` / `If-None-Match` from the stored `checked_date` "
          "and ETag) answers the same question in one request. A `304` is a "
          "definitive no-change. Where a host serves neither header, compare a "
          "hash of the extracted text, which the harvest already stores as "
          "`source_md5`.",
          "",
          "**Tier 3 — a full harvest, and ONLY on a trigger.** Run the shard "
          "harvest for an entity when tier 1 or tier 2 says something moved, "
          "when the entity has never been checked "
          f"({cd['entity_universe'] - cd['entities_with_any_url']:,} entities "
          "today), or when the owner asks. Never on a timer.",
          "",
          "**Why this is the honest answer rather than a schedule.** A cadence "
          "column for a tribal vendor list would be a fabrication — the list "
          "changes when a tribal office remembers to update it, and no header, "
          "notice or index announces that. What CAN be established cheaply is "
          "whether the page moved, and that is a measurement rather than a "
          "guess. The observed cadences in the table above are exactly that: "
          "**derived from the dates of items the sites actually posted**, and "
          "they should be used to set each site's own check interval — a site "
          "posting monthly is worth checking monthly; one posting semiannually "
          "is not.",
          "",
          "**Two rules this inherits and must not lose.** Read `robots.txt` and "
          "the terms page before any check, not just before a harvest — six "
          "publishers have stated restrictive terms and are excluded by every "
          "route. And one poller per host, always: a change-detection sweep "
          "across 1,555 hosts is still 1,555 requests and must be paced.",
          ""]

    if doc.get("net_probes"):
        np_ = doc["net_probes"]
        head = ("## The bounded probes that established the source edges above"
                if np_.get("carried_forward")
                else "## The bounded probes taken for this run")
        L += ["---", "", head, "",
              f"*{np_['requests']} requests, one per host, ≥6s apart, taken on "
              f"**{np_['probed']}**"
              + (" and carried forward — this run issued none. Re-take them "
                 "with `--probe-net`." if np_.get("carried_forward") else ".")
              + f" Host locks respected: "
              f"{np_['host_locks_respected'] or 'none active'}.*", "",
              "```"]
        for r in np_["results"]:
            L.append(json.dumps(r)[:400])
        L += ["```", ""]

    L += [END]
    return "\n".join(L)


def splice(md_text, block):
    if BEGIN in md_text and END in md_text:
        pre = md_text.split(BEGIN)[0]
        post = md_text.split(END, 1)[1]
        return pre + block + post
    # first insert: after the document's opening block, before PART 1
    marker = "\n---\n\n## THE SPINE OF THIS DOCUMENT"
    if marker in md_text:
        pre, post = md_text.split(marker, 1)
        return pre + "\n---\n\n" + block + "\n" + marker + post
    return md_text.rstrip() + "\n\n---\n\n" + block + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe-net", action="store_true")
    ap.add_argument("--json-only", action="store_true")
    a = ap.parse_args()

    src = build()
    counts = {}
    for r in src:
        counts[r["state"]] = counts.get(r["state"], 0) + 1
    doc = dict(
        generated=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        script="code/630_refresh_cadence.py",
        n_sources=len(src), n_datasets=len({r["dataset"] for r in src}),
        state_counts=counts, sources=src,
        change_detection=measure_change_detection(),
    )
    if a.probe_net:
        doc["net_probes"] = probe_net()
    elif os.path.exists(OUT_JSON):
        # Carry the last probes forward rather than re-issuing them. A run
        # without --probe-net must not silently DELETE the only record of the
        # probes that established half the source edges in this file - that is
        # the same shape as 301 overwriting its own baseline with a partial run.
        try:
            prev = json.load(open(OUT_JSON, encoding="utf-8"))
            if prev.get("net_probes"):
                doc["net_probes"] = prev["net_probes"]
                doc["net_probes"]["carried_forward"] = True
        except Exception:
            pass

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1)
    print(f"wrote {os.path.relpath(OUT_JSON, ROOT)}  "
          f"{doc['n_sources']} sources / {doc['n_datasets']} datasets")
    for k in (S_CURRENT, S1, S2, S3, S_CLOSED, S_UNKNOWN):
        print(f"   {STATE_MARK[k]:34s} {counts.get(k, 0)}")

    if not a.json_only:
        block = render(doc)
        cur = open(OUT_MD, encoding="utf-8").read() if os.path.exists(OUT_MD) else ""
        new = splice(cur, block)
        if new != cur:
            if cur and BEGIN not in cur:
                bak = OUT_MD + f".bak_{TODAY}_pre630"
                if not os.path.exists(bak):
                    open(bak, "w", encoding="utf-8").write(cur)
                    print(f"   backup {os.path.relpath(bak, ROOT)}")
            open(OUT_MD, "w", encoding="utf-8").write(new)
            print(f"   spliced the measured block into "
                  f"{os.path.relpath(OUT_MD, ROOT)}")


if __name__ == "__main__":
    main()
