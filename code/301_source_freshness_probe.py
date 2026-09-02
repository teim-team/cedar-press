#!/usr/bin/env py -3
"""
301_source_freshness_probe.py — measure how fast each Cedar collection is still
filling in, and record what changed since the last run.

WHY THIS EXISTS
---------------
Every source has a *stated* publication schedule.  Almost none of them tell you
the thing that actually drives cadence: **how long after a period ends does that
period stop growing?**  A source that publishes daily but whose most recent
quarter is only 60% populated needs a slower cadence than one that publishes
quarterly and is complete on release.  This script measures the second number
from files we already hold.

TWO JOBS, TWO CADENCES — the distinction the whole design rests on:
  REFRESH   new rows for entities we already know.  Identifier-seeded, cheap,
            targeted.  Its cadence is set by the LAG PROFILE this script
            measures.
  DISCOVERY finding entities we do NOT know.  Needs a broad filter or a full
            sweep.  Its cadence is set by how fast the *entity population*
            turns over, which is measured by code/276_measure_discovery_gap.py
            and lives in docs/DISCOVERY_GAP.json.  This script reports the
            entity-arrival curve (stage `entities`) but does not size the gap.

WHAT IT MEASURES (stages)
-------------------------
  files      mtime / size / row count for each registered clean table.
  periods    period histogram (month where a real date exists, else FY/year)
             and, from it:
               - last_period_present
               - plateau          median count over a mature window
               - filling_window   how many trailing periods sit below 90% of
                                  the plateau -> "still filling in"
               - settled_from     the newest period that is NOT still filling
  provenance max(fetched_date), max(built_date), distinct source_archive_stamp.
  archive    parses the USAspending award-archive listings already on disk:
             stamp, S3 last_modified, object count, total bytes.
  entities   distinct-entity arrival by period (the discovery-side curve).
  diff       compares everything above against the previous snapshot and
             reports WHICH PERIODS CHANGED.  This is the point of the script:
             the oldest period whose count moved since the last run is the
             empirical answer to "how far back does a refresh actually reach?",
             and it gets sharper every time this is re-run.

NETWORK
-------
Default is ZERO network requests.  `--probe-net` issues at most one cheap
conditional GET per allowlisted host, honours logs/_HOSTLOCK_<host>.json,
sleeps >= MIN_GAP_S between hosts, and records status + Last-Modified + ETag
into the snapshot so the NEXT run can tell whether the object changed.

HARD REFUSALS (encoded, not documented):
  * api.sam.gov          — never contacted.  10 calls/day, org role pending.
  * api.usaspending.gov  — refused while code/121_pull_subawards_api.py is live.
  * files.usaspending.gov— same budget as the line above (they refuse the same
                           IP within two minutes of each other).
  Only 404 and 403 are treated as facts about an object.  Everything else is
  recorded as "unknown", never as absence.

USAGE
-----
  py -3 code/301_source_freshness_probe.py                 # all offline stages
  py -3 code/301_source_freshness_probe.py --stages periods,diff
  py -3 code/301_source_freshness_probe.py --probe-net     # + bounded probes
  py -3 code/301_source_freshness_probe.py --no-snapshot   # do not overwrite

OUTPUTS
-------
  docs/SOURCE_FRESHNESS.json            full measurement, human-readable
  docs/SOURCE_FRESHNESS_SNAPSHOT.json   compact state for the next diff
  logs/301_source_freshness.log         run log

Written 2026-08-26.  Modifies no dataset.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
RAW = ROOT / "data" / "raw"
DOCS = ROOT / "docs"
LOGS = ROOT / "logs"

OUT_FULL = DOCS / "SOURCE_FRESHNESS.json"
OUT_SNAP = DOCS / "SOURCE_FRESHNESS_SNAPSHOT.json"
RUN_LOG = LOGS / "301_source_freshness.log"

NOW = dt.datetime.now(dt.timezone.utc)
TODAY = NOW.date()

# ---------------------------------------------------------------------------
# Host policy
# ---------------------------------------------------------------------------

FORBIDDEN_HOSTS = {
    "api.sam.gov": "10 calls/day, org role request pending; never contacted by this script",
    "api.usaspending.gov": "code/121_pull_subawards_api.py holds this host",
    "files.usaspending.gov": "same rate-limit budget as api.usaspending.gov",
}

# Cheap, stable objects.  One conditional GET each, only with --probe-net.
PROBE_TARGETS = [
    ("www.federalregister.gov", "https://www.federalregister.gov/api/v1/documents.json?per_page=1&order=newest&fields[]=publication_date",
     "Federal Register — newest publication_date"),
    ("lda.senate.gov", "https://lda.senate.gov/api/v1/filings/?page_size=1&ordering=-dt_posted",
     "LDA — newest dt_posted"),
    ("api.fac.gov", "https://api.fac.gov/general?limit=1&order=fac_accepted_date.desc&select=fac_accepted_date",
     "Federal Audit Clearinghouse — newest acceptance"),
]

MIN_GAP_S = 6.0
NET_TIMEOUT_S = 25
NET_DEADLINE_S = 240  # whole probe stage

# ---------------------------------------------------------------------------
# The registry.  One entry per shipped collection.
#
#   period_cols   tried in order; first present wins
#   period_kind   "date" -> month buckets, "year" -> year buckets
#   documented    the source's STATED schedule (verify, cite, do not trust)
#   closed        True if the source no longer produces new periods at all
#   lag_pairs     (from_col, to_col, label, stated_deadline_days) — the direct
#                 in-file measurement of submission lag.  This is the strongest
#                 evidence available: it does not depend on our pull history at
#                 all, only on two dates the SOURCE itself stamped.
#   season_col    a column whose MONTH-OF-YEAR histogram exposes the publication
#                 rhythm (quarterly spikes, annual drops).
#   regime_cols   (a, b) cross-tab that exposes a schedule REGIME CHANGE — e.g.
#                 the 2008 HLOGA break from semiannual to quarterly LD-2.
# ---------------------------------------------------------------------------

REGISTRY = [
    dict(key="prime_contracts", file="prime_contracts.csv",
         period_cols=["fiscal_year"], period_kind="year",
         prov_cols=["built_date"], entity_col="tribe_id",
         documented="FPDS-NG: agencies report within 3 business days; USAspending "
                    "award archive replaces monthly. Corrections accepted indefinitely.",
         closed=False),
    dict(key="prime_contracts_monthly", file=None,
         glob=str(RAW / "contracts" / "usaspending_archive_2026-08-07" / "filtered" / "FY*_ledger_rows.csv"),
         period_cols=["action_date"], period_kind="date",
         prov_cols=[], entity_col="recipient_uei",
         documented="Same source as prime_contracts; this is the per-FY filtered "
                    "extract, which retains action_date so a MONTHLY fill curve is "
                    "measurable. Vintage: archive stamps 20260706 (FY2017-26) and "
                    "20260806 (FY2007-16).",
         closed=False),
    dict(key="assistance", file="federal_funding_transactions.csv",
         period_cols=["action_date"], period_kind="date",
         prov_cols=["fetched_date", "source_archive_stamp"], entity_col="tribe_id",
         documented="USAspending assistance: submitted twice monthly by agencies "
                    "(DATA Act), archive replaces monthly.",
         closed=False),
    dict(key="faads", file="faads_transactions_all_agencies.csv",
         period_cols=["action_date", "fiscal_year"], period_kind="date",
         prov_cols=["fetched_date"], entity_col="tribe_id",
         documented="CLOSED BY DESIGN. FAADS was retired when USAspending took over; "
                    "the series ends FY2007 and will never gain a period.",
         closed=True),
    dict(key="subawards", file="subawards.csv",
         period_cols=["subaward_date"], period_kind="date",
         prov_cols=["fetched_date", "promoted_date"], entity_col="sub_uei",
         documented="FSRS: prime reports a subaward by the END OF THE MONTH FOLLOWING "
                    "the month of award. So a month is structurally incomplete for "
                    "~30-60 days.",
         closed=False),
    dict(key="lobbying", file="native_entity_lobbying_disclosures.csv",
         period_cols=["dt_posted", "filing_year"], period_kind="date",
         prov_cols=[], entity_col="entity_id",
         documented="LDA quarterly LD-2, due 20 days after quarter end: "
                    "20 Jan / 20 Apr / 20 Jul / 20 Oct. Semiannual LD-203 due "
                    "30 Jan / 30 Jul. Pre-2008 (HLOGA) the LD-2 was SEMIANNUAL.",
         season_col="dt_posted",
         regime_cols=("filing_year", "filing_period"),
         closed=False),
    dict(key="federal_register", file="federal_actions.csv",
         period_cols=["publication_date"], period_kind="date",
         prov_cols=["fetched_date", "classified_date"], entity_col=None,
         documented="Federal Register publishes every federal business day; the "
                    "public inspection desk posts the day before. Complete on release.",
         season_col="publication_date",
         closed=False),
    dict(key="nagpra", file="nagpra_notices.csv",
         period_cols=["publication_date"], period_kind="date",
         prov_cols=["fetched_date"], entity_col=None,
         documented="NAGPRA notices are Federal Register documents — same daily "
                    "cadence, but arrival is event-driven, not periodic.",
         closed=False),
    dict(key="np_schedule_i", file="np_schedule_i_grants.csv",
         period_cols=["tax_period_end", "tax_year"], period_kind="date",
         prov_cols=["retrieved_date", "built_date"], entity_col="filer_ein",
         documented="IRS Form 990 e-file XML index, released in batches. A return "
                    "appears roughly 9-18 months after the filer's fiscal year end "
                    "(extensions push it out).",
         lag_pairs=[("tax_period_end", "retrieved_date",
                     "filer fiscal year end -> our retrieval (UPPER BOUND on the "
                     "source's own lag; it also contains our own delay)", None)],
         closed=False),
    dict(key="fac_single_audits", file="fac_tribal_single_audits.csv",
         period_cols=["fac_accepted_date", "fy_end_date", "audit_year"], period_kind="date",
         prov_cols=["retrieved_at", "built_date"], entity_col="auditee_ein",
         documented="Uniform Guidance 2 CFR 200.512(a): submit the reporting package "
                    "within the EARLIER of 30 days after receiving the auditor's "
                    "report or 9 MONTHS after the audit period ends.",
         lag_pairs=[("fy_end_date", "fac_accepted_date",
                     "audit period end -> FAC acceptance", 274)],
         season_col="fac_accepted_date",
         closed=False),
    dict(key="ferc", file="ferc_docket_filings.csv",
         period_cols=["filed_date"], period_kind="date",
         prov_cols=["fetched_date", "built_date"], entity_col="resolved_native_entity_id",
         documented="FERC eLibrary indexes a filing within about one business day of "
                    "acceptance. Continuous, event-driven.",
         # ⚠ THIS LAG PAIR MEASURES NOTHING AND IS KEPT ONLY TO SAY SO.
         # Measured 2026-08-26: `issued_date` is populated on **0 of 102,615
         # rows**. A lag pair whose second column is entirely blank yields an
         # empty distribution, and an empty distribution renders as "no lag
         # detected" rather than "not measurable" - which is the flattering
         # reading. Either 133_build_ferc_advocacy.py stops populating it or
         # the pair should be removed; until one of those happens, the emptiness
         # is documented here so nobody quotes a filed->issued lag from it.
         lag_pairs=[("filed_date", "issued_date",
                     "filed -> issued (⚠ issued_date is blank on ALL 102,615 "
                     "rows as of 2026-08-26; this pair yields NOTHING)", None)],
         season_col="filed_date",
         closed=False),
    dict(key="admin_appeals", file="admin_appeal_decisions.csv",
         period_cols=["decision_date"], period_kind="date",
         prov_cols=["fetched_date"], entity_col=None,
         documented="IBIA / IBLA post decisions to the Interior year indices as they "
                    "issue; the bound volume lags. Event-driven.",
         closed=False),
    dict(key="ca_gaming", file="ca_gaming_payments.csv",
         period_cols=["period_end"], period_kind="date",
         prov_cols=["fetched_date", "built_date"], entity_col="tribe_id",
         documented="California Gambling Control Commission publishes RSTF/SDF "
                    "allocations QUARTERLY, with the audited statements annual.",
         closed=False),
    dict(key="fl_gaming", file="fl_gaming_payments.csv",
         period_cols=["period_end", "period_start"], period_kind="date",
         prov_cols=["fetched_date"], entity_col="tribe_id",
         documented="Florida compact revenue share is reported by the state on a "
                    "monthly/annual mix depending on the series.",
         closed=False),
    dict(key="gaming_facility_metrics", file="gaming_facility_metrics.csv",
         period_cols=["observation_date", "as_of_date"], period_kind="date",
         prov_cols=["fetched_date"], entity_col="entity_id",
         documented="NIGC gaming revenue report is ANNUAL (typically released mid-year "
                    "for the prior FY). State regulators differ: CT is MONTHLY per "
                    "casino, CA quarterly, several states annual only.",
         closed=False),
    dict(key="resource_revenue", file="resource_revenue.csv",
         period_cols=["period_end", "payment_date"], period_kind="date",
         prov_cols=["fetched_date", "built_date"], entity_col="recipient_entity_id",
         documented="ONRR disburses monthly and publishes monthly/annual statistics; "
                    "state severance series are quarterly or annual.",
         closed=False),
    dict(key="deals", file="deals_classified.csv",
         period_cols=["Event_Date"], period_kind="date",
         prov_cols=["Date_Added", "Data_As_Of", "classified_date"], entity_col="native_party_entity_id",
         documented="Continuous. Press releases and filings; there is no schedule, "
                    "only link rot.",
         closed=False),
    # `period_cols` was None here until 2026-08-26 and the table has been
    # 100% dated the whole time: `notice_date` is populated on all 11,402 rows
    # and spans 1994-2026. A None period column produces
    # `{"status": "NO_PERIOD_COLUMN"}` in the lag profile, which reads as "this
    # collection cannot be measured" and is indistinguishable from a table with
    # no dates. Declared in `code/cedar_period_columns.py` and taken from
    # there, so 35, 102 and 301 cannot drift apart again.
    # DO NOT substitute event_start_date / event_end_date: they are populated
    # on 93 of 11,402 rows (0.8%) and would silently shrink the collection to
    # those 93.
    dict(key="consultations", file="consultation_events.csv",
         period_cols=["notice_date"], period_kind="date",
         prov_cols=["fetched_date"], entity_col="tribe_id",
         documented="Section 106 / agency consultation notices; event-driven, "
                    "surfaced through the Federal Register and agency e-planning.",
         season_col="notice_date",
         closed=False),
    dict(key="section_106_consultations", file="section_106_consultation_events.csv",
         period_cols=["notice_date"], period_kind="date",
         prov_cols=["fetched_date", "built_date"], entity_col="tribe_id",
         documented="Section 106 consultation events extracted from Federal "
                    "Register undertakings; same cadence as the FR feed.",
         closed=False),
    # A YEAR IS A YEAR. `gaming_revenue_bounds` keys on `fiscal_year` and the
    # source (NIGC regional totals, tribal audited statements) gives nothing
    # finer. `period_kind="year"` so no month or day is ever synthesised - the
    # project has already put 415 gaming dates on day-15 and day-31 that way.
    dict(key="gaming_revenue_bounds", file="gaming_revenue_bounds.csv",
         period_cols=["fiscal_year"], period_kind="year",
         prov_cols=["built_date"], entity_col="tribe_id",
         documented="NIGC publishes gaming revenue ANNUALLY by region for the "
                    "prior fiscal year; tribal audited statements are annual. "
                    "There is no sub-annual period at source.",
         closed=False),
    dict(key="foia_index", file="foia_request_index.csv",
         period_cols=None, period_kind="date",
         prov_cols=["fetched_date"], entity_col=None,
         documented="Agency FOIA logs are posted irregularly, most annually, some "
                    "quarterly. 1,775 of 9,481 rows carry no parseable date.",
         closed=False),
    dict(key="nrc_meetings", file="nrc_public_meetings.csv",
         period_cols=None, period_kind="date",
         prov_cols=["fetched_date"], entity_col=None,
         documented="NRC public meeting notices; forward-looking calendar, refreshed "
                    "continuously but with a short horizon.",
         closed=False),
]

# ---------------------------------------------------------------------------
# KEEP THIS REGISTRY AND `code/cedar_period_columns.py` IN AGREEMENT.
#
# Three tools decide "which column is the period" and they used to decide it
# three different ways: this REGISTRY, `35_coverage_audit.py`'s global
# `DATE_COLS` name list, and `102_build_coverage_profile.py`'s (file, column)
# declarations. Three lists drift, and the drift is invisible, because a period
# column absent under the name a tool looks for is indistinguishable from a
# table with no dates. That defect has now been paid for three times in this
# repo in one day - `102` at 0.0% for 19 days on two tables keyed
# `tribe_entity_id`, `35` on gaming, and these five.
#
# `cedar_period_columns.py` is the single declaration. This check runs at
# import and fails LOUDLY on disagreement rather than letting the two versions
# coexist. It is deliberately a hard failure: a silent divergence here is
# exactly the class of bug the module exists to end.
# ---------------------------------------------------------------------------
def _assert_period_declarations_agree():
    try:
        import cedar_period_columns as PERIODS
    except ImportError:          # module absent -> nothing to reconcile
        return []
    problems = []
    for spec in REGISTRY:
        fn = spec.get("file")
        if not fn:
            continue
        declared = PERIODS.PERIOD_COLUMNS.get(fn)
        if not declared:
            continue
        mine = list(spec.get("period_cols") or [])
        theirs = list(declared["cols"])
        if mine != theirs:
            problems.append(
                f"  {fn}: 301 REGISTRY says {mine or None}, "
                f"cedar_period_columns says {theirs}")
        if spec.get("period_kind") != declared["kind"]:
            problems.append(
                f"  {fn}: 301 period_kind={spec.get('period_kind')!r}, "
                f"cedar_period_columns kind={declared['kind']!r}")
    return problems


_PERIOD_DISAGREEMENTS = _assert_period_declarations_agree()
if _PERIOD_DISAGREEMENTS:
    raise SystemExit(
        "FATAL: 301's REGISTRY disagrees with code/cedar_period_columns.py "
        "about which column carries a period:\n"
        + "\n".join(_PERIOD_DISAGREEMENTS)
        + "\nReconcile them. Do not 'fix' this by deleting the check.")

DATE_RE = re.compile(r"^(\d{4})[-/]?(\d{2})")
YEAR_RE = re.compile(r"^(\d{4})$")


def log(msg: str, fh=None) -> None:
    line = f"[{dt.datetime.now(dt.timezone.utc).strftime('%H:%M:%SZ')}] {msg}"
    print(line, flush=True)
    if fh:
        fh.write(line + "\n")
        fh.flush()


def parse_period(val: str, kind: str) -> str | None:
    """Return 'YYYY-MM' for date-kind, 'YYYY' for year-kind. None if unusable."""
    if not val:
        return None
    v = val.strip()
    if not v:
        return None
    if kind == "year":
        m = YEAR_RE.match(v)
        if m:
            y = int(m.group(1))
            return str(y) if 1900 <= y <= 2100 else None
        m = DATE_RE.match(v)
        return m.group(1) if m and 1900 <= int(m.group(1)) <= 2100 else None
    # date kind
    m = DATE_RE.match(v)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        if 1900 <= y <= 2100 and 1 <= mo <= 12:
            return f"{y:04d}-{mo:02d}"
        if 1900 <= y <= 2100:
            return f"{y:04d}-00"
        return None
    # US style M/D/YYYY
    parts = re.split(r"[/-]", v)
    if len(parts) == 3 and len(parts[2]) == 4:
        try:
            mo, y = int(parts[0]), int(parts[2])
            if 1 <= mo <= 12 and 1900 <= y <= 2100:
                return f"{y:04d}-{mo:02d}"
        except ValueError:
            return None
    m = YEAR_RE.match(v)
    if m:
        return f"{int(m.group(1)):04d}-00"
    return None


def pick_col(header: list[str], candidates) -> str | None:
    if not candidates:
        return None
    lower = {h.lower(): h for h in header}
    for c in candidates:
        if c in header:
            return c
        if c.lower() in lower:
            return lower[c.lower()]
    return None


ISO_D = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")


def to_date(v: str):
    """Parse ISO or M/D/YYYY into a date.  None if unusable."""
    if not v:
        return None
    v = v.strip()
    m = ISO_D.match(v)
    if m:
        try:
            return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    parts = re.split(r"[/-]", v)
    if len(parts) == 3 and len(parts[2]) == 4:
        try:
            return dt.date(int(parts[2]), int(parts[0]), int(parts[1]))
        except ValueError:
            return None
    return None


def summarise_lag(days: list[int], stated: int | None) -> dict:
    if not days:
        return {"status": "NO_PAIRS"}
    days.sort()
    n = len(days)

    def pct(p):
        return days[min(n - 1, int(round(p * (n - 1))))]

    out = {
        "n_pairs": n,
        "median_days": pct(0.50),
        "p10_days": pct(0.10),
        "p75_days": pct(0.75),
        "p90_days": pct(0.90),
        "p99_days": pct(0.99),
        "max_days": days[-1],
        "negative_or_zero": sum(1 for d in days if d <= 0),
    }
    if stated:
        beyond = sum(1 for d in days if d > stated)
        out["stated_deadline_days"] = stated
        out["n_beyond_stated_deadline"] = beyond
        out["pct_beyond_stated_deadline"] = round(100 * beyond / n, 2)
        out["VERDICT"] = ("the stated deadline describes the source"
                          if beyond / n < 0.25 else
                          "the stated deadline does NOT describe the source — plan on "
                          f"p90={out['p90_days']}d, not {stated}d")
    return out


LDA_PERIOD_END = {  # period label -> (month, day) the reporting period closes
    "first_quarter": (3, 31), "second_quarter": (6, 30),
    "third_quarter": (9, 30), "fourth_quarter": (12, 31),
    "mid_year": (6, 30), "year_end": (12, 31),
}
LDA_DEADLINE_DAYS = 20  # LD-2 is due 20 days after the period closes


def lda_posting_lag(path: Path) -> dict:
    """Days from the LD-2 reporting period's close to the filing appearing.

    This is the measurement that fixes the pull DATE, not just the cadence: it
    says how long after 20 Jan / 20 Apr / 20 Jul / 20 Oct you must wait before a
    pull is substantially complete, and how much still arrives after that.
    """
    if not path.exists():
        return {"status": "FILE_ABSENT"}
    buckets = defaultdict(list)
    regimes = Counter()
    with path.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            per = (r.get("filing_period") or "").strip()
            yr = (r.get("filing_year") or "").strip()
            posted = to_date(r.get("dt_posted") or "")
            if per not in LDA_PERIOD_END or not yr.isdigit() or not posted:
                continue
            mo, dy = LDA_PERIOD_END[per]
            try:
                close = dt.date(int(yr), mo, dy)
            except ValueError:
                continue
            regimes["semiannual (pre-HLOGA)" if per in ("mid_year", "year_end")
                    else "quarterly (post-HLOGA)"] += 1
            buckets["ALL"].append((posted - close).days)
            buckets[per].append((posted - close).days)
    out = {"stated_deadline_days_after_period_close": LDA_DEADLINE_DAYS,
           "regime_row_counts": dict(regimes)}
    for k, v in buckets.items():
        s = summarise_lag(list(v), LDA_DEADLINE_DAYS)
        if k == "ALL":
            days = sorted(v)
            n = len(days)
            for w in (20, 27, 34, 41, 55, 90, 180, 365):
                s[f"pct_filed_by_day_{w}"] = round(100 * sum(1 for d in days if d <= w) / n, 2)
            s["PULL_DATE_GUIDANCE"] = (
                "the smallest w where pct_filed_by_day_w clears ~97% is the number of days "
                "after the period close that a pull should wait; anything later is a "
                "trailing re-pull, not a first pull")
        out[k] = s
    return out


def _stated_for(spec: dict, label: str):
    for a, b, lbl, stated in spec.get("lag_pairs", []):
        if label.startswith(lbl):
            return stated
    return None


def scan_table(paths: list[Path], spec: dict, fh) -> dict:
    """One streaming pass per file.  Returns the measurement block."""
    period_counts: Counter = Counter()
    entity_first: dict[str, str] = {}
    prov_max: dict[str, str] = {}
    prov_values: dict[str, Counter] = defaultdict(Counter)
    lag_days: dict[str, list] = defaultdict(list)
    season: Counter = Counter()
    regime: dict[str, Counter] = defaultdict(Counter)
    # entity concentration per period.  A single vendor's transaction blizzard
    # can move a monthly ROW count by 9x (measured: ASRC FEDERAL FACILITIES
    # LOGISTICS contributed 33,502 of 37,323 prime rows in 2026-03).  Distinct
    # entities per period is the robust series; the row count is not.
    ent_by_period: dict[str, Counter] = defaultdict(Counter)
    max_date: list = [None]
    min_date: list = [None]
    rows = 0
    period_col_used = None
    entity_col_used = None
    unparsed = 0

    for p in paths:
        try:
            f = p.open("r", encoding="utf-8-sig", newline="")
        except OSError as e:
            log(f"    ! cannot open {p.name}: {e}", fh)
            continue
        with f:
            rdr = csv.reader(f)
            try:
                header = next(rdr)
            except StopIteration:
                continue
            pc = pick_col(header, spec.get("period_cols"))
            ec = pick_col(header, [spec["entity_col"]] if spec.get("entity_col") else None)
            provs = {c: header.index(pick_col(header, [c]))
                     for c in spec.get("prov_cols", []) if pick_col(header, [c])}
            pi = header.index(pc) if pc else None
            ei = header.index(ec) if ec else None

            pairs = []
            for a, b, label, stated in spec.get("lag_pairs", []):
                ca, cb = pick_col(header, [a]), pick_col(header, [b])
                if ca and cb:
                    pairs.append((header.index(ca), header.index(cb), f"{label} [{a} -> {b}]"))
            sc = pick_col(header, [spec["season_col"]]) if spec.get("season_col") else None
            si = header.index(sc) if sc else None
            rg = spec.get("regime_cols")
            ra = pick_col(header, [rg[0]]) if rg else None
            rb = pick_col(header, [rg[1]]) if rg else None
            rai = header.index(ra) if ra else None
            rbi = header.index(rb) if rb else None
            period_col_used = period_col_used or pc
            entity_col_used = entity_col_used or ec
            kind = spec.get("period_kind", "date")
            n = len(header)
            for row in rdr:
                rows += 1
                if len(row) < n:
                    row = row + [""] * (n - len(row))
                if pi is not None:
                    if kind == "date":
                        raw = row[pi].strip()
                        if raw:
                            dd = to_date(raw)
                            if dd:
                                if max_date[0] is None or dd > max_date[0]:
                                    max_date[0] = dd
                                if min_date[0] is None or dd < min_date[0]:
                                    min_date[0] = dd
                    per = parse_period(row[pi], kind)
                    if per:
                        period_counts[per] += 1
                    else:
                        unparsed += 1
                    if ei is not None and per:
                        ent = row[ei].strip()
                        if ent:
                            prev = entity_first.get(ent)
                            if prev is None or per < prev:
                                entity_first[ent] = per
                            ent_by_period[per][ent] += 1
                for c, idx in provs.items():
                    v = row[idx].strip()
                    if not v:
                        continue
                    if c.endswith("stamp") or c in ("source_archive_stamp",):
                        prov_values[c][v] += 1
                    else:
                        if c not in prov_max or v > prov_max[c]:
                            prov_max[c] = v
                for ai, bi, label in pairs:
                    da, db = to_date(row[ai]), to_date(row[bi])
                    if da and db:
                        lag_days[label].append((db - da).days)
                if si is not None:
                    d = to_date(row[si])
                    if d:
                        season[f"{d.month:02d}"] += 1
                if rai is not None and rbi is not None:
                    a_, b_ = row[rai].strip(), row[rbi].strip()
                    if a_ and b_:
                        regime[a_][b_] += 1

    entity_arrival = Counter(entity_first.values())
    distinct_by_period = {p: len(c) for p, c in sorted(ent_by_period.items())}
    concentration = {}
    for p, c in sorted(ent_by_period.items()):
        tot = sum(c.values())
        if tot >= 200:
            name, n = c.most_common(1)[0]
            share = n / tot
            if share >= 0.25:
                concentration[p] = {"top_entity": name, "rows": n, "period_rows": tot,
                                    "share": round(share, 3)}
    return dict(
        submission_lag={k: summarise_lag(v, _stated_for(spec, k)) for k, v in lag_days.items()},
        EXACT_LAST_DATE=str(max_date[0]) if max_date[0] else None,
        exact_first_date=str(min_date[0]) if min_date[0] else None,
        distinct_entities_by_period=distinct_by_period or None,
        SINGLE_ENTITY_DOMINATED_PERIODS=concentration or None,
        month_of_year_profile=(dict(sorted(season.items())) if season else None),
        schedule_regime_by_year=({k: dict(v.most_common()) for k, v in sorted(regime.items())}
                                 if regime else None),
        rows=rows,
        period_col_used=period_col_used,
        entity_col_used=entity_col_used,
        rows_with_unparseable_period=unparsed,
        period_counts=dict(sorted(period_counts.items())),
        entity_first_seen_by_period=dict(sorted(entity_arrival.items())),
        distinct_entities=len(entity_first),
        provenance_max=prov_max,
        provenance_values={k: dict(v.most_common(12)) for k, v in prov_values.items()},
    )


def lag_profile(period_counts: dict, kind: str) -> dict:
    """The measurement that actually drives cadence.

    plateau        = median count over a MATURE window (periods that predate the
                     trailing edge by enough that nothing should still be
                     arriving)
    filling_window = trailing periods whose count is below 90% of plateau
    settled_from   = newest period that is NOT still filling
    """
    if not period_counts:
        return {"status": "NO_PERIOD_COLUMN"}
    keys = [k for k in sorted(period_counts) if not k.endswith("-00")]
    if len(keys) < 6:
        return {"status": "TOO_FEW_PERIODS", "n_periods": len(keys)}

    # mature window: skip the newest `skip`, take the next `take`
    skip, take = (24, 36) if kind == "date" else (3, 6)
    mature = keys[max(0, len(keys) - skip - take): max(0, len(keys) - skip)]
    if len(mature) < 3:
        mature = keys[: max(3, len(keys) // 2)]
    plateau = statistics.median(period_counts[k] for k in mature)
    if plateau <= 0:
        return {"status": "DEGENERATE_PLATEAU"}

    thresh = 0.90 * plateau
    filling = []
    for k in reversed(keys):
        if period_counts[k] < thresh:
            filling.append(k)
        else:
            break
    filling.reverse()
    settled_from = None
    for k in reversed(keys):
        if k not in filling:
            settled_from = k
            break

    # ratio curve over the trailing 18 periods, so the shape is legible
    tail = keys[-18:]
    curve = {k: round(period_counts[k] / plateau, 3) for k in tail}

    # SEASONAL plateau — compare each period to the median of the SAME calendar
    # month across the mature window.  Required for any source whose periods are
    # not uniform: 990 tax_period_end piles onto month 12 and month 06, LD-2
    # dt_posted onto Jan/Apr/Jul/Oct, CA gaming onto quarter ends.  A flat
    # plateau reports those as "97% missing" every single month.
    seasonal = None
    seasonal_filling = None
    if kind == "date":
        by_month = defaultdict(list)
        for k in mature:
            by_month[k[-2:]].append(period_counts[k])
        med = {m: statistics.median(v) for m, v in by_month.items() if v}
        if med:
            seasonal = {}
            for k in tail:
                base = med.get(k[-2:])
                seasonal[k] = round(period_counts[k] / base, 3) if base else None
            sf = []
            for k in reversed(keys):
                base = med.get(k[-2:])
                if base and period_counts[k] < 0.90 * base:
                    sf.append(k)
                elif base:
                    break
            sf.reverse()
            seasonal_filling = sf

    # Is the mature window itself trustworthy?  If the plateau sits far below
    # the all-period median, the window has landed inside a KNOWN HOLE and every
    # ratio computed from it is meaningless.  Measured case: subawards, whose
    # mature window 2021-08..2024-08 is exactly the FY2021-24 upstream gap.
    global_med = statistics.median(period_counts[k] for k in keys)
    plateau_warning = None
    if plateau < 0.25 * global_med:
        plateau_warning = (
            f"PLATEAU IS UNTRUSTWORTHY: the mature window {mature[0]}..{mature[-1]} has a "
            f"median of {plateau} against an all-period median of {global_med}. The window "
            f"has landed inside a data hole; every ratio below is an artifact of that hole, "
            f"not a statement about the source.")

    return {
        "status": "OK",
        "n_periods": len(keys),
        "first_period": keys[0],
        "last_period": keys[-1],
        "mature_window": [mature[0], mature[-1]] if mature else None,
        "plateau_rows_per_period": plateau,
        "all_period_median": global_med,
        "PLATEAU_WARNING": plateau_warning,
        "filling_periods": filling,
        "filling_window_length": len(filling),
        "settled_from": settled_from,
        "trailing_ratio_to_plateau": curve,
        "trailing_ratio_to_SEASONAL_plateau": seasonal,
        "filling_periods_seasonal": seasonal_filling,
        "filling_window_length_seasonal": len(seasonal_filling) if seasonal_filling is not None else None,
    }


def attribute_edge(block: dict, spec: dict) -> dict:
    """Split the trailing deficit into OUR staleness and the SOURCE's lag.

    A trailing period that is short because we have not pulled since the 5th is
    not evidence of anything about the source.  Measured case: federal_actions
    shows 2026-08 at 17% of plateau, and federal_actions.csv was last written
    2026-08-05 — the whole deficit is ours.
    """
    lp = block.get("lag_profile") or {}
    if lp.get("status") != "OK":
        return {"status": "NO_PROFILE"}
    mtimes = [f["mtime_utc"] for f in block.get("files", [])]
    newest = max(mtimes) if mtimes else None
    fetched = (block.get("provenance_max") or {})
    our_asof = max([v for v in list(fetched.values()) + ([newest[:10]] if newest else []) if v],
                   default=None)
    try:
        our_dt = dt.date.fromisoformat(our_asof[:10]) if our_asof else None
    except ValueError:
        our_dt = None
    days_stale = (TODAY - our_dt).days if our_dt else None

    last = lp.get("last_period")
    src_edge = None
    exact = block.get("EXACT_LAST_DATE")
    if exact and our_dt:
        # Use the TRUE last date, never the month bucket.  A month bucket rounds
        # a source that stops on the 3rd up to the 31st and hides four weeks of
        # lag.  Measured: prime action_date stops 2026-07-03, which the bucket
        # 2026-07 reports as 12 days when it is 40.
        try:
            src_edge = (our_dt - dt.date.fromisoformat(exact)).days
        except ValueError:
            src_edge = None
    if src_edge is None and last and our_dt:
        try:
            y, m = int(last[:4]), int(last[5:7]) if len(last) >= 7 else 12
            last_day = dt.date(y + (m == 12), (m % 12) + 1, 1) - dt.timedelta(days=1)
            src_edge = (our_dt - last_day).days
        except ValueError:
            src_edge = None

    verdict = "UNKNOWN"
    if days_stale is not None:
        if days_stale >= 14 and (src_edge is None or src_edge < 14):
            verdict = ("OUR STALENESS. The last period is short because we have not pulled "
                       f"in {days_stale} days, not because the source is behind. "
                       "Re-pull before drawing any lag conclusion.")
        elif src_edge is not None and src_edge >= 21:
            verdict = (f"SOURCE LAG. Our as-of is {our_asof} and the newest period ends "
                       f"{src_edge} days before it — the source itself stops there.")
        else:
            verdict = (f"CURRENT. Pulled {days_stale}d ago; the newest period ends "
                       f"{src_edge}d before our as-of.")
    return {
        "our_as_of": our_asof,
        "days_since_our_as_of": days_stale,
        "newest_period": last,
        "exact_last_date": exact,
        "days_from_newest_period_end_to_our_as_of": src_edge,
        "VERDICT": verdict,
    }


# ---------------------------------------------------------------------------
# Archive listings already on disk
# ---------------------------------------------------------------------------

def measure_archive(fh) -> dict:
    out = {"listings": [], "finding": None}
    listings = [
        RAW / "contracts" / "archive_listing_2026-08-12.csv",
        RAW / "usaspending_archive_2026-08-07" / "_archive_listing.csv",
    ]
    stamp_pat = re.compile(r"_(\d{8})\.zip$")
    for p in listings:
        if not p.exists():
            continue
        stamps, lms, total, n = Counter(), Counter(), 0, 0
        with p.open(encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                n += 1
                m = stamp_pat.search(r.get("key", ""))
                stamps[m.group(1) if m else "none"] += 1
                lm = (r.get("last_modified") or "")[:19]
                if lm:
                    lms[lm] += 1
                sz = r.get("size_bytes") or r.get("size") or "0"
                try:
                    total += int(sz)
                except ValueError:
                    pass
        out["listings"].append({
            "path": str(p.relative_to(ROOT)),
            "listing_file_mtime_utc": dt.datetime.fromtimestamp(p.stat().st_mtime, dt.timezone.utc).isoformat(),
            "objects": n,
            "total_bytes": total,
            "total_gb": round(total / 1e9, 2),
            "stamps": dict(stamps),
            "distinct_s3_last_modified": len(lms),
            "s3_last_modified_top": dict(lms.most_common(5)),
        })

    # per-FY manifests: which stamp did each fiscal year actually come from?
    manifests = []
    for p in [RAW / "contracts" / "usaspending_archive_2026-08-07" / "_SOURCE_MANIFEST.csv",
              RAW / "usaspending_archive_2026-08-07" / "_SOURCE_MANIFEST.csv"]:
        if not p.exists():
            continue
        rows = []
        with p.open(encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                rows.append({k: r.get(k) for k in
                             ("fiscal_year", "stamp", "rows_scanned", "rows_kept", "bytes", "fetched_utc")
                             if k in r})
        manifests.append({"path": str(p.relative_to(ROOT)), "rows": rows})
    out["per_fy_manifests"] = manifests

    # the trap: state.json and SOURCE_MANIFEST.csv are the SAME record, so
    # differencing them measures nothing.  Say so, loudly, in the output.
    out["TRAP"] = (
        "_SOURCE_MANIFEST.csv is GENERATED FROM _state.json. Their rows_scanned "
        "columns are identical by construction. Differencing them looks like a "
        "month-over-month archive comparison and is not one. A real cross-vintage "
        "measurement needs two independently-fetched extracts of the SAME fiscal "
        "year under DIFFERENT stamps; Cedar does not hold one today."
    )
    return out


# ---------------------------------------------------------------------------
# Host locks
# ---------------------------------------------------------------------------

def read_hostlocks() -> dict:
    locks = {"total": 0, "active": [], "stale_active": [], "queued_work": []}
    for p in sorted(LOGS.glob("_HOSTLOCK_*.json")):
        locks["total"] += 1
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        host = d.get("host") or p.stem.replace("_HOSTLOCK_", "")
        released = d.get("released")
        active = d.get("active")
        holder = d.get("holder") or {}
        pid = d.get("pid") or holder.get("pid")
        claimed = d.get("claimed_at") or d.get("started") or holder.get("claimed")
        q = d.get("queue") or d.get("queue_appended_by_me") or []
        if active is True or (active is None and not released and holder):
            rec = {"host": host, "pid": pid, "claimed": claimed,
                   "script": d.get("script") or d.get("claimed_by") or holder.get("script"),
                   "queue_len": len(q) if isinstance(q, list) else None}
            locks["active"].append(rec)
        if q:
            locks["queued_work"].append({"host": host, "queue_len": len(q) if isinstance(q, list) else 1,
                                         "released": released})
    return locks


def live_pollers() -> list:
    """Win32_Process.CommandLine.  ps aux cannot answer this on Windows."""
    try:
        import subprocess
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python|py\\.exe' } | "
             "Select-Object ProcessId,ParentProcessId,Name,CommandLine | ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=60).stdout
        data = json.loads(out) if out.strip() else []
        if isinstance(data, dict):
            data = [data]
    except Exception as e:
        return [{"error": f"process enumeration failed: {e}"}]
    # `py.exe -3 script.py` LAUNCHES `python.exe script.py`, so a self-check on
    # os.getpid() alone sees its own launcher and defers to itself.  Walk the
    # ancestry BOTH ways: up to every ancestor of this process, and down to
    # every descendant of those, then exclude the whole tree.
    parent = {d.get("ProcessId"): d.get("ParentProcessId") for d in data}
    kin = {os.getpid()}
    cur = os.getpid()
    for _ in range(12):  # bounded walk up
        cur = parent.get(cur)
        if cur is None or cur in kin:
            break
        kin.add(cur)
    for _ in range(12):  # fixpoint walk down
        grew = False
        for pid, ppid in parent.items():
            if ppid in kin and pid not in kin:
                kin.add(pid)
                grew = True
        if not grew:
            break
    res = []
    for d in data:
        cl = d.get("CommandLine") or ""
        if d.get("ProcessId") in kin:
            continue
        m = re.search(r"code[/\\](\d+[\w]*\.py)", cl)
        if m:
            res.append({"pid": d.get("ProcessId"), "script": m.group(1), "cmdline": cl[:200]})
    return res


# ---------------------------------------------------------------------------
# Bounded network probe
# ---------------------------------------------------------------------------

def probe_net(prev_snapshot: dict, fh) -> dict:
    import urllib.request
    import urllib.error

    results = {}
    started = time.time()
    prev = (prev_snapshot or {}).get("net_probes", {})
    locked = {l["host"] for l in read_hostlocks()["active"]}
    for host, url, why in PROBE_TARGETS:
        if host in FORBIDDEN_HOSTS:
            results[host] = {"skipped": "FORBIDDEN", "reason": FORBIDDEN_HOSTS[host]}
            continue
        if host in locked:
            results[host] = {"skipped": "HOSTLOCK_ACTIVE",
                             "reason": "another poller holds this host; deferring per PULL_DISCIPLINE rule 1"}
            continue
        if time.time() - started > NET_DEADLINE_S:
            results[host] = {"skipped": "RUN_DEADLINE"}
            continue
        req = urllib.request.Request(url, headers={
            "User-Agent": "cedar-press-freshness-probe/1 (one request per host, no retry loop)",
            "Accept": "application/json",
        })
        etag = prev.get(host, {}).get("etag")
        if etag:
            req.add_header("If-None-Match", etag)
        rec = {"url": url, "why": why, "probed_at": dt.datetime.now(dt.timezone.utc).isoformat()}
        try:
            with urllib.request.urlopen(req, timeout=NET_TIMEOUT_S) as resp:
                body = resp.read(4096)
                rec.update(status=resp.status,
                           etag=resp.headers.get("ETag"),
                           last_modified=resp.headers.get("Last-Modified"),
                           body_head=body[:400].decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            rec.update(status=e.code,
                       etag=e.headers.get("ETag") if e.headers else None,
                       last_modified=e.headers.get("Last-Modified") if e.headers else None,
                       fact_about_object=(e.code in (403, 404)))
        except Exception as e:
            # NOT a fact about the object.  Record the shape and move on.
            rec.update(status=None, error=type(e).__name__, detail=str(e)[:200],
                       fact_about_object=False,
                       note="transport-level failure; says nothing about whether the object exists")
        p = prev.get(host, {})
        rec["changed_since_last_run"] = bool(
            p and (p.get("etag") != rec.get("etag") or p.get("last_modified") != rec.get("last_modified"))
        ) if p else None
        results[host] = rec
        log(f"    probe {host} -> {rec.get('status')}", fh)
        time.sleep(MIN_GAP_S)
    return results


# ---------------------------------------------------------------------------
# Diff against the previous snapshot
# ---------------------------------------------------------------------------

def diff_against(prev: dict, cur: dict) -> dict:
    if not prev:
        return {"status": "NO_PREVIOUS_SNAPSHOT",
                "note": "First run. Re-run this script after any refresh; the diff "
                        "below is where the real cadence evidence accumulates."}
    out = {"status": "OK", "previous_run": prev.get("generated"), "collections": {}}
    pc = prev.get("collections", {})
    for key, cm in cur.get("collections", {}).items():
        p = pc.get(key)
        if not p:
            out["collections"][key] = {"status": "NEW_COLLECTION"}
            continue
        a, b = p.get("period_counts", {}), cm.get("period_counts", {})
        changed = {k: [a.get(k, 0), b.get(k, 0)] for k in set(a) | set(b) if a.get(k, 0) != b.get(k, 0)}
        new_periods = sorted(set(b) - set(a))
        oldest_changed = min(changed) if changed else None
        rec = {
            "rows_before": p.get("rows"), "rows_after": cm.get("rows"),
            "rows_delta": (cm.get("rows") or 0) - (p.get("rows") or 0),
            "periods_changed": len(changed),
            "new_periods": new_periods,
            "OLDEST_PERIOD_THAT_MOVED": oldest_changed,
            "changed_detail": dict(sorted(changed.items())[-24:]),
        }
        if oldest_changed and cm.get("last_period"):
            rec["retro_reach_note"] = (
                f"a refresh reached back to {oldest_changed} while the newest period is "
                f"{cm.get('last_period')} — that reach, not the vendor's schedule, is "
                f"the trailing window a re-pull must cover")
        out["collections"][key] = rec
    return out


# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stages", default="files,periods,archive,entities,diff",
                    help="comma list: files,periods,archive,entities,diff")
    ap.add_argument("--probe-net", action="store_true",
                    help="issue at most one cheap conditional GET per allowlisted host")
    ap.add_argument("--no-snapshot", action="store_true", help="do not overwrite the snapshot")
    ap.add_argument("--only", default="", help="comma list of registry keys")
    args = ap.parse_args()

    stages = {s.strip() for s in args.stages.split(",") if s.strip()}
    only = {s.strip() for s in args.only.split(",") if s.strip()}

    LOGS.mkdir(exist_ok=True)
    fh = RUN_LOG.open("a", encoding="utf-8")
    log(f"=== 301_source_freshness_probe start {NOW.isoformat()} stages={sorted(stages)} "
        f"probe_net={args.probe_net}", fh)

    prev = {}
    if OUT_SNAP.exists():
        try:
            prev = json.loads(OUT_SNAP.read_text(encoding="utf-8"))
            log(f"loaded previous snapshot from {prev.get('generated')}", fh)
        except Exception as e:
            log(f"previous snapshot unreadable: {e}", fh)

    result = {
        "generated": NOW.isoformat(),
        "script": "code/301_source_freshness_probe.py",
        "network_requests": 0,
        "modifies_datasets": False,
        "host_policy": FORBIDDEN_HOSTS,
        "collections": {},
    }

    pollers = live_pollers()
    result["live_pollers_at_run_start"] = pollers
    for p in pollers:
        if "121_pull_subawards_api" in (p.get("script") or ""):
            log(f"  LIVE 121 poller pid={p['pid']} — usaspending hosts REFUSED this run", fh)
    result["hostlocks"] = read_hostlocks()

    snapshot = {"generated": NOW.isoformat(), "collections": {}}

    for spec in REGISTRY:
        key = spec["key"]
        if only and key not in only:
            continue
        paths = []
        if spec.get("file"):
            p = CLEAN / spec["file"]
            if p.exists():
                paths = [p]
        elif spec.get("glob"):
            from glob import glob as _g
            paths = [Path(x) for x in sorted(_g(spec["glob"]))]
        if not paths:
            result["collections"][key] = {"status": "FILE_ABSENT",
                                          "expected": spec.get("file") or spec.get("glob")}
            log(f"  {key:26s} ABSENT", fh)
            continue

        block = {
            "files": [{"path": str(p.relative_to(ROOT)),
                       "size_bytes": p.stat().st_size,
                       "mtime_utc": dt.datetime.fromtimestamp(p.stat().st_mtime, dt.timezone.utc).isoformat()}
                      for p in paths],
            "documented_schedule": spec["documented"],
            "source_closed": spec.get("closed", False),
        }

        if "files" in stages and not ({"periods", "entities"} & stages):
            result["collections"][key] = block
            continue

        t0 = time.time()
        m = scan_table(paths, spec, fh)
        block.update({k: v for k, v in m.items()
                      if k not in ("entity_first_seen_by_period",) or "entities" in stages})
        block["scan_seconds"] = round(time.time() - t0, 1)
        if "periods" in stages:
            block["lag_profile"] = lag_profile(m["period_counts"], spec.get("period_kind", "date"))
            block["edge_attribution"] = attribute_edge(block, spec)
        result["collections"][key] = block

        snapshot["collections"][key] = {
            "rows": m["rows"],
            "period_counts": m["period_counts"],
            "last_period": (block.get("lag_profile") or {}).get("last_period"),
            "provenance_max": m["provenance_max"],
        }
        lp = block.get("lag_profile", {})
        log(f"  {key:26s} rows={m['rows']:>9,}  last={lp.get('last_period')}  "
            f"filling={lp.get('filling_window_length')}  ({block['scan_seconds']}s)", fh)

    if "archive" in stages:
        result["usaspending_archive"] = measure_archive(fh)
        log("  archive listings measured", fh)

    if "periods" in stages and (not only or "lobbying" in only):
        result["lda_posting_lag"] = lda_posting_lag(CLEAN / "native_entity_lobbying_disclosures.csv")
        log("  LDA posting lag measured", fh)

    if args.probe_net:
        log("  --probe-net: bounded conditional GETs", fh)
        result["net_probes"] = probe_net(prev, fh)
        result["network_requests"] = sum(1 for v in result["net_probes"].values() if "skipped" not in v)
        snapshot["net_probes"] = {h: {"etag": v.get("etag"), "last_modified": v.get("last_modified"),
                                      "status": v.get("status")}
                                  for h, v in result["net_probes"].items() if "skipped" not in v}

    if "diff" in stages:
        result["diff_since_last_run"] = diff_against(prev, snapshot)

    DOCS.mkdir(exist_ok=True)

    # A PARTIAL RUN MUST NEVER REPLACE A FULL ONE.
    # Caught by this script destroying its own outputs: `--only deals
    # --stages files` overwrote the 243 KB measurement with 3.9 KB and truncated
    # the snapshot to 68 bytes, erasing the diff baseline for all 20
    # collections.  Same failure shape as a full-rebuild stage reverting an
    # in-place enricher — it printed success and looked like progress.
    partial = bool(only) or "periods" not in stages
    if partial:
        alt = OUT_FULL.with_name(OUT_FULL.stem + ".partial.json")
        tmp = alt.with_suffix(".json.part")
        tmp.write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
        tmp.replace(alt)
        log(f"PARTIAL RUN -> wrote {alt.relative_to(ROOT)} (full measurement left intact)", fh)
    else:
        tmp = OUT_FULL.with_suffix(".json.part")
        tmp.write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
        tmp.replace(OUT_FULL)
        log(f"wrote {OUT_FULL.relative_to(ROOT)}", fh)

    if not args.no_snapshot:
        # MERGE, never replace: a partial run updates only the collections it
        # actually measured and leaves every other baseline standing.
        merged = dict(prev) if prev else {}
        base = dict(merged.get("collections") or {})
        base.update(snapshot["collections"])
        merged["collections"] = base
        merged["generated"] = snapshot["generated"]
        if "net_probes" in snapshot:
            np_ = dict(merged.get("net_probes") or {})
            np_.update(snapshot["net_probes"])
            merged["net_probes"] = np_
        merged["last_run_measured"] = sorted(snapshot["collections"])
        merged["last_run_was_partial"] = partial
        tmp = OUT_SNAP.with_suffix(".json.part")
        tmp.write_text(json.dumps(merged, default=str), encoding="utf-8")
        tmp.replace(OUT_SNAP)
        log(f"wrote {OUT_SNAP.relative_to(ROOT)} "
            f"({len(base)} collections, {len(snapshot['collections'])} refreshed this run)", fh)

    log(f"=== done. network_requests={result['network_requests']}", fh)
    fh.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
