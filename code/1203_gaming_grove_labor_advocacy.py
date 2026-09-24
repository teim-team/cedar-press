#!/usr/bin/env python3
"""Cedar Grove Gaming - 1203: labor observations and advocacy links (lane F).

    py -3 code/1203_gaming_grove_labor_advocacy.py build \
        --input-root "C:\\Users\\esm247\\Desktop\\Cedar Press" \
        --output-root C:\\Users\\esm247\\cedar-grove-gaming-work\\components

Writes `gaming_labor_observations.csv`, `gaming_advocacy_links.csv` and
`1203_gaming_grove_labor_advocacy.receipt.json`. Needs
CEDAR_GAMING_PROVISIONAL_IDS=1 while the owner's ID hold stands (every ID is
then a non-promotable `PROV-` ID; see gaming_grove.ID_CONTRACT_STATUS).

WHY A NEW LABOR TABLE WHEN gaming_employment_observations.csv EXISTS
--------------------------------------------------------------------
The clean table is 3,421 rows of SIX different quantities under one
`employment` column: an establishment's own 300A headcount, the same 300A
filing a second time rolled up to the tribe (332 rows are literal repeats of
the facility-grain OSHA layer), benefit-plan participants, all jobs in a census
block, and planners' projections. Its grain is "whatever the source was", so
a consumer who sums `employment` by tribe-year adds plan participants to block
jobs to injury-log headcounts. The Codex audit rated the lane NOT READY for
exactly that reason.

This producer re-grains to ONE SOURCE OBSERVATION PER ROW PER MEASURE, keyed
on the publisher's own record key, never on a Cedar row number:

    OSHA ITA        establishment_id + filing year (from the raw ITA extract, so
                    the facility-grain and tribe-grain copies of one filing
                    collapse to one source record)
    DOL Form 5500   EIN + ACK_ID + dataset year. The measure is
                    `active_plan_participants` and is NEVER called employees:
                    it excludes employees below the plan's eligibility
                    threshold and includes separated participants.
    NLRB            case number + unit + tally type. `eligible_voters` is a
                    bargaining UNIT on a date, never the employer's workforce.
    LODES           kept, but INTERNAL: the block was chosen from Casino City
                    coordinates (vendor lineage) and the count is every job in
                    the block, noise-infused by design. It is context, not a
                    property labor figure, so it cannot ship as one.
    property sites  job-posting / preference-policy statements: labor DEMAND,
                    never a count; kept internal until retention is reviewed.

NEPA/planning projections (PROJECTED, ENVIRONMENTAL_REVIEW_COUNT) are NOT
carried: environmental review belongs to lane E and a projection is never an
operating count.

cedar_uid comes only from an existing resolved link (the clean table's own
attribution, the entity crosswalk, or a Cedar-ruled facility). NLRB elections
need more than a name: the legal employer must self-identify as a tribal
government or instrumentality AND agree on state, or the d/b/a brand must be a
Cedar gaming facility in the same state. The 4wheeler resolver's NLRB matches
include Golden Nugget/Circus Circus -> Las Vegas Paiute and a Hollywood Casino
-> Perryville (Alaska); those are refused here.

WHY LINKS, NOT LOBBYING ROWS
----------------------------
The Advocacy & Engagement collection is authoritative for lobbying, comments,
consultations and testimony. Gaming never copies a filing, an amount, a
registrant or a spend basis: it emits one row per (advocacy event, Gaming
object) that carries the ORIGINAL event ID verbatim plus the evidence span
that made the event gaming-relevant. A superseded amendment or a withdrawn
attribution is not linked, so a link can never resurrect what the Advocacy
collection has retired. Regulatory-event targets belong to lane E; this lane
emits the Federal Register / docket key in `crossref_source_key` so the
orchestrator can resolve it without guessing lane E's derivation.

OLMS (LM-2/LM-3) and state WARN notices are not on this machine. They are
recorded as source_limited acquisition leads in the receipt, not fetched.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import gaming_grove as gg  # noqa: E402

csv.field_size_limit(10 ** 9)

PRODUCER = "1203_gaming_grove_labor_advocacy"
LABOR_TABLE = "gaming_labor_observations.csv"
ADV_TABLE = "gaming_advocacy_links.csv"
FOURWHEELER_DEFAULT = Path.home() / "Desktop" / "4wheeler" / "casino_employment_validation"
# 4wheeler casino_employment_validation was built 2026-08-12 (its HANDOFF and
# docs/LABOR_SOURCES_FOR_GAMING_2026-08-26.md s1A); its files carry no
# per-row retrieval date, so this is the retrieval date of record.
FOURWHEELER_RETRIEVED = "2026-08-12"
FTE_DIVISOR = 2080
HOURS_PER_EMPLOYEE_PLAUSIBLE = (200, 5000)

# ---------------------------------------------------------------- helpers
_ce_cache: dict[str, bool] = {}


def ce(value: str) -> str:
    """Return value if it is a canonical CE uid, else ''. Cached: the shared
    validator re-imports 503_identity on every call."""
    v = (value or "").strip()
    if not v:
        return ""
    if v not in _ce_cache:
        _ce_cache[v] = gg.is_ce_uid(v)
    return v if _ce_cache[v] else ""


def norm(s: str) -> str:
    s = (s or "").lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def num(s: str) -> str:
    """Canonical numeric text: '1836.00' -> '1836'. Blank stays blank - a
    missing value is never rendered as 0."""
    s = (s or "").strip().replace(",", "")
    if not s:
        return ""
    try:
        f = float(s)
    except ValueError:
        return ""
    return str(int(f)) if f == int(f) else repr(round(f, 4))


SUPPRESSION_MARKERS = {"(d)", "d", "(s)", "s", "*", "(x)", "x", "n", "(n)", "suppressed", "withheld"}


def value_of(raw: str, disclosure_code: str = ""):
    """(value, value_status). A suppressed cell or a blank is NEVER '0'."""
    r = (raw or "").strip()
    if (disclosure_code or "").strip() or r.lower() in SUPPRESSION_MARKERS:
        return "", "suppressed"
    v = num(r)
    if v == "":
        return "", "not_reported"
    return v, "reported"


def iso_date(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        return s[:10]
    for fmt in ("%d %B %Y", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%m/%d/%Y",
                "%d%b%y:%H:%M:%S", "%B %d, %Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def span(text: str, m: re.Match, width: int = 90) -> str:
    a, b = max(0, m.start() - width), min(len(text), m.end() + width)
    out = re.sub(r"\s+", " ", text[a:b]).strip()
    return ("..." if a else "") + out[:220] + ("..." if b < len(text) else "")


def read_external(inputs: gg.Inputs, root: Path | None, rel: str):
    """Read a file outside the Cedar input root (4wheeler, read-only) with the
    same hash receipt Inputs.read records. Absent is recorded, not fatal."""
    label = "4wheeler/casino_employment_validation/" + rel
    p = (root / rel) if root else None
    if p is None or not p.is_file():
        inputs.receipts[label] = {"path": label, "status": "ABSENT"}
        return [], []
    raw = p.read_bytes()
    inputs.receipts[label] = {"path": label, "sha256": hashlib.sha256(raw).hexdigest(),
                              "bytes": len(raw), "status": "READ"}
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig", errors="strict"), newline=""))
    rows = list(reader)
    inputs.receipts[label]["rows"] = len(rows)
    return list(reader.fieldnames or []), rows


# ---------------------------------------------------------------- contracts
LABOR_HEADER = [
    "labor_observation_id", "source_system", "source_record_id", "measure",
    "measured_concept", "evidence_class", "value", "value_status", "unit",
    "disclosure_limitation", "suppression_flag", "period", "period_type",
    "outcome", "cedar_uid", "gaming_facility_id", "employer_name_as_reported",
    "establishment_or_unit_as_reported", "reported_state", "match_method",
    "confidence", "review_status", "flags", "legacy_observation_ids",
    "legacy_facility_id", "source_url", "source_date", "retrieved_date",
    "rights_class",
]
SOURCE_SYSTEMS = {"osha_ita_300a", "dol_form5500", "nlrb_election",
                  "census_lodes_wac", "property_website"}
EVIDENCE_CLASSES = {"reported_establishment_headcount", "reported_hours",
                    "derived_fte", "reported_plan_participants",
                    "reported_bargaining_unit", "reported_election_tally",
                    "geographic_context_not_property_payroll",
                    "labor_demand_statement"}
VALUE_STATUSES = {"reported", "derived", "not_reported", "suppressed",
                  "noise_infused", "withheld_implausible", "not_a_count"}
DISCLOSURE = {"none", "noise_infused", "suppressed", "filing_threshold_rule"}
PERIOD_TYPES = {"calendar_year_filed_for", "form5500_dataset_year",
                "election_tally_date", "lodes_reference_year", "retrieval_date"}

_LABOR_RIGHTS = {c: "public_official" for c in LABOR_HEADER}
_LABOR_RIGHTS.update({
    "labor_observation_id": "public_derived", "measured_concept": "public_derived",
    "evidence_class": "public_derived", "value_status": "public_derived",
    "disclosure_limitation": "public_derived", "suppression_flag": "public_derived",
    "period_type": "public_derived", "outcome": "public_derived",
    "cedar_uid": "public_derived", "gaming_facility_id": "public_derived",
    "match_method": "public_derived", "confidence": "public_derived",
    "review_status": "public_derived", "flags": "public_derived",
    "legacy_observation_ids": "internal_crosswalk",
    "legacy_facility_id": "internal_crosswalk",
})

LABOR_CONTRACT = {
    "grain": ("One measure of one source labor record: an OSHA ITA establishment-year, a DOL "
              "Form 5500 plan filing (ACK_ID), an NLRB election tally, a LODES block-year, or a "
              "property-site labor-demand statement."),
    "primary_key": ["labor_observation_id"],
    "required": ["source_system", "source_record_id", "measure", "measured_concept",
                 "value_status", "unit", "period", "period_type", "confidence",
                 "review_status", "rights_class", "source_url", "retrieved_date"],
    "enums": {"source_system": SOURCE_SYSTEMS, "evidence_class": EVIDENCE_CLASSES,
              "value_status": VALUE_STATUSES, "disclosure_limitation": DISCLOSURE,
              "suppression_flag": {"0", "1"}, "period_type": PERIOD_TYPES,
              "confidence": gg.CONFIDENCE, "review_status": gg.REVIEW_STATUSES,
              "rights_class": set(gg.RIGHTS_CLASSES)},
    "dates": ["period", "source_date", "retrieved_date"],
    "intervals": [],
    "public_id_columns": ["labor_observation_id", "cedar_uid", "gaming_facility_id"],
    "derived_ids": {"labor_observation_id": "GLAB"},
    "field_rights": _LABOR_RIGHTS,
    "field_descriptions": {
        "labor_observation_id": "Derived GLAB id from source_system + source_record_id + measure",
        "source_system": "Publisher/system of the labor record",
        "source_record_id": "Publisher's own record key (OSHA establishment_id:year; EIN/ACK_ID/dataset year; NLRB case/unit/tally; LODES file::block)",
        "measure": "What was measured; plan participants are never called employees",
        "measured_concept": "Plain statement of the population the number counts and what it is not",
        "evidence_class": "Kind of evidence (reported headcount, plan participants, bargaining unit, context, demand)",
        "value": "Numeric value as filed or derived; blank when not reported or suppressed, never 0 for absence",
        "value_status": "reported / derived / not_reported / suppressed / noise_infused / withheld_implausible / not_a_count",
        "unit": "Unit of value",
        "disclosure_limitation": "Source disclosure-avoidance or filing-rule limitation that travels with the value",
        "suppression_flag": "1 when the source suppressed the cell; value is then blank",
        "period": "Year or date the value refers to (see period_type)",
        "period_type": "Meaning of period: OSHA filing year, Form 5500 dataset year, NLRB tally date, LODES year",
        "outcome": "NLRB tally majority only (for/against/tie); not a certification",
        "cedar_uid": "Native entity (CE) from an existing resolved link only; blank if unresolved",
        "gaming_facility_id": "Facility id via gaming_grove.facility_id_for(cedar_place_id), only where the source row already linked a facility",
        "employer_name_as_reported": "Company / plan sponsor / NLRB employer exactly as filed",
        "establishment_or_unit_as_reported": "Establishment name, plan name or bargaining-unit description as filed",
        "reported_state": "State on the source record",
        "match_method": "How cedar_uid / facility were attached",
        "confidence": "high / medium / low for the attachment",
        "review_status": "Attachment review state",
        "flags": "Pipe-joined caveats that must travel with the value",
        "legacy_observation_ids": "INTERNAL: gaming_employment_observations observation_id(s) this row re-grains",
        "legacy_facility_id": "INTERNAL: legacy facility_id (CCP-/VP-/TPL-/CEDAR-FAC) crosswalk only",
        "source_url": "Publisher URL of the record or dataset",
        "source_date": "Date the source record was filed/issued, where stated",
        "retrieved_date": "Date Cedar retrieved the source bytes",
        "rights_class": "Row-level rights class (gaming_grove.RIGHTS_CLASSES)",
    },
    "nonadditive_note": ("NEVER sum across measure or source_system: 300A headcounts, hours, derived FTE, "
                         "plan participants, bargaining-unit voters and block jobs are different "
                         "populations. OSHA establishment sets change year to year (not a balanced "
                         "panel); one sponsor files several plans (largest plan only here, never summed); "
                         "NLRB units are occupational subgroups; LODES counts every employer in a block."),
    "publication_status": "internal",
    "supersedes": [
        {"table": "gaming_employment_observations.csv", "role": "source: re-grained to one source record per measure; PROJECTED/ENV rows left to lane E"},
        {"table": "gaming_property_labor_demand.csv", "role": "source: labor-demand statements, internal"},
        {"table": "data/staging/gaming_employment_form5500_staged.csv", "role": "not read: staging, superseded by the merged clean rows"},
        {"table": "data/staging/gaming_employment_osha_tribe_staged.csv", "role": "not read: staging, superseded by the merged clean rows"},
    ],
    "row_rights_column": "rights_class",
}

ADV_HEADER = [
    "advocacy_link_id", "source_collection", "source_table", "source_event_id",
    "source_native_id", "source_event_type", "event_date", "link_target_type",
    "target_id", "link_basis", "evidence_text", "topics", "crossref_source_key",
    "confidence", "review_status", "source_system", "source_record_id",
    "source_url", "source_date", "retrieved_date", "rights_class",
]
TARGET_TYPES = {"gaming_facility", "enterprise", "cedar_uid", "compact",
                "regulatory_event", "topic_only"}
EVENT_TYPES = {"registered_lobbying", "tribal_consultation", "regulatory_comment",
               "congressional_testimony"}
_ADV_RIGHTS = {c: "public_derived" for c in ADV_HEADER}
_ADV_RIGHTS.update({"source_event_id": "public_official", "source_native_id": "public_official",
                    "evidence_text": "public_official", "source_url": "public_official",
                    "source_date": "public_official", "event_date": "public_official",
                    "source_record_id": "public_official", "source_system": "public_official",
                    "retrieved_date": "public_official"})
ADV_FORBIDDEN_FIELDS = {"income_usd", "expenses_usd", "spend_usd", "amount", "reported_amount_usd",
                        "registrant_name", "registrant_id", "registrant_state", "spend_basis",
                        "client_name", "amount_type"}
ADV_CONTRACT = {
    "grain": "One (advocacy/engagement event, linked Gaming object) pair; the event row itself stays in the Advocacy & Engagement collection.",
    "primary_key": ["advocacy_link_id"],
    "required": ["source_collection", "source_table", "source_event_id", "link_target_type",
                 "target_id", "link_basis", "topics", "confidence", "review_status",
                 "rights_class", "source_url"],
    "enums": {"link_target_type": TARGET_TYPES, "source_event_type": EVENT_TYPES,
              "confidence": gg.CONFIDENCE, "review_status": gg.REVIEW_STATUSES,
              "rights_class": set(gg.RIGHTS_CLASSES),
              "source_collection": {"advocacy_engagement"}},
    "dates": ["event_date", "source_date", "retrieved_date"],
    "intervals": [],
    "public_id_columns": ["advocacy_link_id"],
    "derived_ids": {"advocacy_link_id": "GADV"},
    "field_rights": _ADV_RIGHTS,
    "field_descriptions": {
        "advocacy_link_id": "Derived GADV id from collection + table + source_event_id + target",
        "source_collection": "Always advocacy_engagement: the authoritative collection",
        "source_table": "Advocacy collection table the event lives in",
        "source_event_id": "That table's own event key, verbatim (LDA filing_uuid, consultation_event_id, comment row id, testimony_id)",
        "source_native_id": "Publisher's own id, verbatim (LDA filing_uuid, regulations.gov comment id, FR document number, hearing witness id)",
        "source_event_type": "registered_lobbying / tribal_consultation / regulatory_comment / congressional_testimony",
        "event_date": "Event or posting date as the Advocacy table records it",
        "link_target_type": "gaming_facility / enterprise / cedar_uid / compact / regulatory_event / topic_only",
        "target_id": "Id of the linked Gaming object (facility via facility_id_for, CEDAR-NEST, CE uid, compact_id) or the primary topic for topic_only",
        "link_basis": "Rule that made the link (issue code, matched term, attribution method, facility/compact rule)",
        "evidence_text": "Short span of the source text that evidences gaming relevance or the target",
        "topics": "Pipe-joined topics: gaming|compacts|land|taxation|regulation|sports_betting|environmental_review|facilities|enterprises",
        "crossref_source_key": "Source key for orchestrator resolution to other lanes (FR doc number, docket, LDA period)",
        "confidence": "Confidence in the link",
        "review_status": "Link review state",
        "source_system": "Upstream publisher (LDA, Federal Register, regulations.gov, congressional committee)",
        "source_record_id": "Same as source_native_id; kept for the shared evidence-column contract",
        "source_url": "Publisher URL of the event",
        "source_date": "Posting date of the source record",
        "retrieved_date": "Retrieval date recorded by the Advocacy table, where it records one",
        "rights_class": "Row-level rights class",
    },
    "nonadditive_note": "Links are not events: one lobbying filing links to several targets. Count distinct source_event_id, never rows; no amounts are carried.",
    "publication_status": "internal",
    "supersedes": [
        {"table": "native_entity_lobbying_disclosures.csv", "role": "authoritative source; linked, never copied"},
        {"table": "consultation_events.csv", "role": "authoritative source; linked"},
        {"table": "regulations_gov_comments.csv", "role": "authoritative source; linked"},
        {"table": "data/source/advocacy/congressional_testimony_2025_2026.csv", "role": "authoritative source; linked"},
    ],
    "row_rights_column": "rights_class",
}

CONTRACTS = {LABOR_TABLE: LABOR_CONTRACT, ADV_TABLE: ADV_CONTRACT}

# ---------------------------------------------------------------- vocab regexes
GAMING_RE = re.compile(
    r"\b(?:gaming|gambling|casinos?|IGRA|Indian Gaming Regulatory Act|NIGC|bingo|"
    r"class (?:ii|iii|2|3) gaming|sports? (?:betting|wagering|book)|sportsbook|wagering|"
    r"internet (?:gaming|poker|gambling)|online (?:gaming|gambling|sports betting)|i-?gaming|"
    r"prediction markets?|daily fantasy|fantasy sports|UIGEA|unlawful internet gambling|"
    r"Wire Act|PASPA|slot machines?|pari-?mutuel|tribal-state compacts?|gaming compacts?)\b", re.I)
TOPIC_RES = [
    ("gaming", GAMING_RE),
    ("compacts", re.compile(r"\bcompacts?\b", re.I)),
    ("land", re.compile(r"lands? (?:in|into|to) trust|fee[- ]to[- ]trust|trust (?:land|acquisition)|"
                        r"carcieri|part 151|land acquisition|reservation proclamation|restored lands?|"
                        r"after[- ]acquired|two[- ]part determination|off[- ]reservation", re.I)),
    ("taxation", re.compile(r"\btax(?:es|ation|ing)?\b|excise|internal revenue|\bIRS\b|withholding", re.I)),
    ("regulation", re.compile(r"\bNIGC\b|national indian gaming commission|regulat|rulemaking|"
                              r"minimum internal control|\bMICS\b|ordinance|licens|final rule|"
                              r"proposed rule|25 CFR", re.I)),
    ("sports_betting", re.compile(r"sports? (?:betting|wagering|book)|sportsbook|internet (?:gaming|poker|gambling)|"
                                  r"online (?:gaming|gambling|sports)|i-?gaming|prediction markets?|"
                                  r"fantasy sports|daily fantasy|UIGEA|unlawful internet gambling|"
                                  r"wire act|PASPA|mobile (?:gaming|wagering|betting)", re.I)),
    ("environmental_review", re.compile(r"\bNEPA\b|environmental (?:review|impact|assessment)|\bEIS\b", re.I)),
    ("facilities", re.compile(r"\bcasinos?\b|\bresorts?\b|gaming facilit|gaming establishment|gaming operation", re.I)),
    ("enterprises", re.compile(r"enterprise|gaming authority|development authority|development corporation|"
                               r"economic development", re.I)),
]
TOPIC_ORDER = [t for t, _ in TOPIC_RES]
COMPACT_CONTEXT_RE = re.compile(r"(?:gaming|class iii|tribal[- ]state|state[- ]tribal)\s+compacts?|compacts?\s+(?:with|between)\s+the\s+state|compact amendment", re.I)
US_STATES = ["Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut",
             "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa",
             "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan",
             "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
             "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina",
             "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island",
             "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
             "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming"]
STATE_RE = re.compile(r"\b(" + "|".join(US_STATES) + r")\b")
GENERIC_FACILITY_TOKENS = {"casino", "casinos", "resort", "hotel", "and", "the", "of", "bingo",
                           "gaming", "travel", "center", "centre", "plaza", "spa", "hall", "palace",
                           "club", "inn", "event", "entertainment", "golf", "tribal", "indian",
                           "express", "at", "a", "sports", "bar", "grill", "hard", "rock", "lodge"}
LEGAL_SUFFIX = re.compile(r"\b(inc|incorporated|llc|l l c|corp|corporation|co|company|ltd|lp|the|dba|d b a)\b")
TRIBAL_SELF_ID_RE = re.compile(
    r"\b(?:band of|indian tribe|tribe of|indians|indian community|nation of|rancheria|pueblo of|"
    r"gaming enterprise|development authority|gaming authority|governmental subdivision|"
    r"an enterprise of|tribal)\b", re.I)


def topics_for(text: str, gam_code: bool = False) -> list[str]:
    found = {t for t, rx in TOPIC_RES if rx.search(text or "")}
    if gam_code:
        found.add("gaming")
    return [t for t in TOPIC_ORDER if t in found]


def fkey(s: str) -> str:
    """Facility-name key: normalized, ignoring and/the/at so 'Resort and
    Casino' equals 'Resort Casino'. Used only together with a state."""
    return " ".join(t for t in norm(s).split() if t not in {"and", "the", "at"})


def entity_key(s: str) -> str:
    return re.sub(r"\s+", " ", LEGAL_SUFFIX.sub(" ", norm(s))).strip()


# ---------------------------------------------------------------- shared lookups
def load_facilities(inputs: gg.Inputs):
    """legacy facility_id -> (cedar_place_id, cedar_uid, name, state, city)."""
    _, rows = inputs.clean("gaming_facilities.csv")
    out = {}
    for r in rows:
        fid = (r.get("facility_id") or "").strip()
        place = (r.get("cedar_place_id") or "").strip()
        if not fid:
            continue
        out[fid] = {"place": place if gg.PLACE_ID_RE.match(place) else "",
                    "cedar_uid": ce(r.get("cedar_uid", "")),
                    "name": r.get("facility_name", ""), "state": (r.get("state") or "").strip().upper(),
                    "city": norm(r.get("city", "")),
                    "duplicate_of": (r.get("duplicate_of_facility_id") or "").strip()}
    return out


def place_facility(facilities, legacy_fid: str, row_place: str = ""):
    """Facility id ONLY through the legacy facility_id -> cedar_place_id mapping
    in gaming_facilities.csv. Returns (gaming_facility_id, flag)."""
    f = facilities.get(legacy_fid)
    if not f or not f["place"]:
        return "", "FACILITY_UNRESOLVED_NO_PLACE_ID" if legacy_fid else ""
    if row_place and row_place != f["place"]:
        return "", "FACILITY_PLACE_ID_DISAGREES_WITH_GAMING_FACILITIES"
    return gg.facility_id_for(f["place"]), ""


def load_neid_crosswalk(inputs: gg.Inputs):
    """Legacy CICD NEID (TRBF-/CNSF-/...) -> CE uid, read-only, APPLIED only."""
    _, rows = inputs.clean("cedar_entity_identity_crosswalk.csv", required=False)
    seen = defaultdict(set)
    for r in rows:
        if r.get("external_scheme") == "CICD_NEID" and r.get("mapping_status") == "APPLIED":
            u = ce(r.get("cedar_uid", ""))
            if u:
                seen[r.get("external_identifier", "").strip()].add(u)
    return {k: next(iter(v)) for k, v in seen.items() if len(v) == 1}


def legacy_prefix_scan(path: str, header, rows, report: dict):
    """Owner hold: report non-CE values in any cedar_uid-bearing input column."""
    for col in header or []:
        if col in ("tribe_id", "entity_id", "tribe_id_as_staged") or col.endswith("_entity_id"):
            legacy = Counter(re.sub(r"-.*$", "", (r.get(col) or "").strip()) + "-"
                             for r in rows if (r.get(col) or "").strip() and not ce(r.get(col)))
            if legacy:
                report[f"{path}::{col} (legacy-id column, read only; never copied to cedar_uid)"] = dict(sorted(legacy.items()))
        if col == "cedar_uid" or col.endswith("_cedar_uid") or col.endswith("cedar_uids"):
            bad = Counter()
            for r in rows:
                for v in re.split(r"[|;,]", r.get(col) or ""):
                    v = v.strip()
                    if v and not ce(v):
                        bad[re.sub(r"[-_].*$", "", v) + "-"] += 1
            if bad:
                report[f"{path}::{col}"] = dict(sorted(bad.items()))


# ---------------------------------------------------------------- labor
def labor_row(**kw) -> dict:
    row = {c: "" for c in LABOR_HEADER}
    row.update({k: ("" if v is None else str(v)) for k, v in kw.items()})
    row["labor_observation_id"] = gg.derive_id("GLAB", row["source_system"],
                                               row["source_record_id"], row["measure"])
    return row


def merge_shared_source_records(rows, withheld, label):
    """One source record attached to several legacy facilities (e.g. two
    Casino City properties geocoded into one census block, or one website
    host serving several properties) is ONE observation. The facility and
    entity survive only if every attachment agrees; otherwise they are
    blanked and flagged, never picked."""
    groups = defaultdict(list)
    for r in rows:
        groups[r["labor_observation_id"]].append(r)
    out = []
    for _, rs in sorted(groups.items()):
        if len(rs) == 1:
            out.append(rs[0])
            continue
        withheld[label] = withheld.get(label, 0) + len(rs) - 1
        r = dict(rs[0])
        if len({x["value"] for x in rs}) > 1:
            raise gg.GamingContractError(f"REFUSED: one source record, different values {r['source_record_id']}")
        flags = set(filter(None, "|".join(x["flags"] for x in rs).split("|")))
        flags.add("ONE_SOURCE_RECORD_ATTACHED_TO_%d_LEGACY_FACILITIES" % len(rs))
        for col, flag in (("gaming_facility_id", "FACILITY_AMBIGUOUS_BLANKED"), ("cedar_uid", "ENTITY_AMBIGUOUS_BLANKED")):
            vals = {x[col] for x in rs}
            if len(vals) > 1:
                r[col] = ""
                flags.add(flag)
        r["legacy_observation_ids"] = "|".join(sorted({x["legacy_observation_ids"] for x in rs}))
        r["legacy_facility_id"] = "|".join(sorted({x["legacy_facility_id"] for x in rs if x["legacy_facility_id"]}))
        r["flags"] = "|".join(sorted(flags))
        out.append(r)
    return out


def build_osha(inputs, emp_rows, facilities, withheld, notes):
    _, raw = inputs.read("data/raw/external/osha_ita/_gambling_naics_rows.csv")
    _, manifest = inputs.read("data/raw/external/osha_ita/_SOURCE_MANIFEST.csv", required=False)
    fetched = {m.get("year", ""): iso_date(m.get("fetched_date", "")) for m in manifest}
    file_url = {m.get("year", ""): m.get("url", "") for m in manifest}
    by_key: dict[tuple, list] = defaultdict(list)
    for r in raw:
        year = num(r.get("year_filing_for"))
        est = num(r.get("establishment_id"))
        if year and est:
            by_key[(est, year)].append(r)
    by_name = defaultdict(set)
    for (est, year), rs in by_key.items():
        for r in rs:
            by_name[(norm(r.get("establishment_name")), (r.get("state") or "").upper(), year,
                     num(r.get("annual_average_employees")))].add((est, year))

    attach: dict[tuple, dict] = {}
    unkeyed = []
    for e in emp_rows:
        mt = e["measurement_type"]
        if mt not in ("OSHA_ESTABLISHMENT_REPORTED", "OSHA_TRIBE_LEVEL_REPORTED"):
            continue
        year = num(e.get("year"))
        est = num(e.get("establishment_id"))
        key = (est, year) if (est, year) in by_key else None
        if key is None:
            name = e.get("establishment_name") or e.get("name_in_source")
            cands = by_name.get((norm(name), (e.get("state") or "").upper(), year, num(e.get("employment"))), set())
            key = next(iter(cands)) if len(cands) == 1 else None
        if key is None:
            unkeyed.append(e["observation_id"])
            continue
        a = attach.setdefault(key, {"uids": set(), "legacy_fids": set(), "places": set(),
                                    "rules": set(), "obs": set(), "conf": set(), "flags": set()})
        u = ce(e.get("cedar_uid", ""))
        if e.get("cedar_uid") and not u:
            a["flags"].add("SOURCE_CEDAR_UID_NOT_CANONICAL_CE")
        if u:
            a["uids"].add(u)
        if e.get("facility_id"):
            a["legacy_fids"].add(e["facility_id"])
            a["places"].add(e.get("cedar_place_id", ""))
        a["rules"].add(e.get("match_rule", ""))
        a["obs"].add(e["observation_id"])
        a["conf"].add(e.get("confidence", "medium"))
        if e.get("commercial_name_present"):
            a["flags"].add("MANAGEMENT_OR_COMMERCIAL_BRAND_PRESENT_NOT_OWNERSHIP")
        if "IDENTICAL_VALUE_FILED_UNDER_2_PROPERTY_NAMES" in (e.get("flags") or ""):
            a["flags"].add("IDENTICAL_VALUE_FILED_UNDER_2_PROPERTY_NAMES_SAME_TRIBE_YEAR")
        if e.get("attribution_repaired_by"):
            a["flags"].add("ATTRIBUTION_ADJUDICATED_BY_" + re.sub(r"\.py$", "", e["attribution_repaired_by"]))
    if unkeyed:
        withheld["osha_clean_row_without_recoverable_establishment_key"] = len(unkeyed)
        notes.append("OSHA clean rows whose establishment_id/year could not be recovered from the raw "
                     f"ITA extract were not emitted: {sorted(unkeyed)[:10]}")

    out = []
    for (est, year), a in sorted(attach.items()):
        rs = sorted(by_key[(est, year)], key=lambda r: (r.get("_file", ""), num(r.get("id") or r.get("\ufeffid") or r.get("ï»¿id"))))
        r = rs[0]
        flags = set(a["flags"]) | {"ITA_COVERAGE_IS_A_FILING_RULE_ABSENCE_IS_NOT_ZERO",
                                   "DO_NOT_SUM_ACROSS_YEARS_UNBALANCED_PANEL"}
        if len(rs) > 1:
            vals = {(num(x.get("annual_average_employees")), num(x.get("total_hours_worked"))) for x in rs}
            flags.add("RESUBMITTED_FILING_DEDUPLICATED" if len(vals) == 1 else "RESUBMITTED_FILING_VALUES_DIFFER")
        uid = ""
        review = "machine_matched"
        if len(a["uids"]) == 1:
            uid = next(iter(a["uids"]))
        elif len(a["uids"]) > 1:
            flags.add("ATTRIBUTION_CONFLICT_ACROSS_LEGACY_ROWS")
            review = "unresolved"
            withheld["osha_attribution_conflict_uid_blanked"] = withheld.get("osha_attribution_conflict_uid_blanked", 0) + 1
        else:
            review = "unresolved"
        fac_id, legacy_fid = "", ""
        if len(a["legacy_fids"]) == 1:
            legacy_fid = next(iter(a["legacy_fids"]))
            fac_id, fflag = place_facility(facilities, legacy_fid, next(iter(a["places"])))
            if fflag:
                flags.add(fflag)
            fu = facilities.get(legacy_fid, {}).get("cedar_uid", "")
            if fac_id and uid and fu and fu != uid:
                flags.add("FACILITY_ENTITY_DISAGREES_WITH_ROW_ENTITY")
        elif len(a["legacy_fids"]) > 1:
            flags.add("MULTIPLE_LEGACY_FACILITIES_FOR_ONE_FILING")
        conf = "high" if (fac_id and "high" in a["conf"]) else ("medium" if uid else "low")
        state = (r.get("state") or "").upper()
        common = dict(source_system="osha_ita_300a", source_record_id=f"establishment_id={est};year={year}",
                      period=year, period_type="calendar_year_filed_for", cedar_uid=uid,
                      gaming_facility_id=fac_id, employer_name_as_reported=r.get("company_name", "").strip(),
                      establishment_or_unit_as_reported=r.get("establishment_name", "").strip(),
                      reported_state=state, match_method=";".join(sorted(x for x in a["rules"] if x)),
                      confidence=conf, review_status=review,
                      legacy_observation_ids="|".join(sorted(a["obs"])), legacy_facility_id=legacy_fid,
                      source_url=file_url.get(year) or "https://www.osha.gov/Establishment-Specific-Injury-and-Illness-Data",
                      source_date=iso_date(r.get("created_timestamp", "")),
                      retrieved_date=fetched.get(year, "") or "2026-08-07",
                      disclosure_limitation="filing_threshold_rule", suppression_flag="0")
        emp, emp_status = value_of(r.get("annual_average_employees"))
        hours, hours_status = value_of(r.get("total_hours_worked"))
        base_flags = "|".join(sorted(flags))
        out.append(labor_row(**common, measure="annual_average_employees",
                             measured_concept="Establishment's own Form 300A annual average number of employees (self-filed, not audited)",
                             evidence_class="reported_establishment_headcount", value=emp,
                             value_status=emp_status, unit="employees", flags=base_flags,
                             rights_class="public_official"))
        out.append(labor_row(**common, measure="total_hours_worked",
                             measured_concept="Establishment's own Form 300A total hours worked by all employees, including overtime, excluding paid leave",
                             evidence_class="reported_hours", value=hours, value_status=hours_status,
                             unit="hours", flags=base_flags, rights_class="public_official"))
        if emp and hours and float(emp) > 0:
            hpe = float(hours) / float(emp)
            lo, hi = HOURS_PER_EMPLOYEE_PLAUSIBLE
            if lo <= hpe <= hi:
                fte, fst, frights, fflags = f"{float(hours) / FTE_DIVISOR:.1f}", "derived", "public_derived", base_flags
            else:
                fte, fst, frights = "", "withheld_implausible", "withheld_unverified"
                fflags = "|".join(sorted(flags | {"HOURS_PER_EMPLOYEE_OUTSIDE_200_5000"}))
                withheld["osha_fte_implausible_hours_per_employee"] = withheld.get("osha_fte_implausible_hours_per_employee", 0) + 1
            out.append(labor_row(**{**common, "source_system": "osha_ita_300a"}, measure="fte_2080",
                                 measured_concept="DERIVED: total_hours_worked / 2080 (convention, not a filing); never an employee count",
                                 evidence_class="derived_fte", value=fte, value_status=fst, unit="fte",
                                 flags=fflags, rights_class=frights))
    return out, len(attach)


def build_form5500(emp_rows, withheld):
    out = []
    for e in emp_rows:
        if e["measurement_type"] != "FORM5500_ACTIVE_PARTICIPANTS":
            continue
        ein, ack, year = e.get("ein", "").strip(), e.get("ack_id", "").strip(), num(e.get("year"))
        if not (ein and ack and year):
            withheld["form5500_row_without_ein_ack_year"] = withheld.get("form5500_row_without_ein_ack_year", 0) + 1
            continue
        uid = ce(e.get("cedar_uid", ""))
        flags = {"PLAN_PARTICIPANTS_ARE_NOT_EMPLOYEES", "SPONSOR_LEVEL_NOT_FACILITY",
                 "LARGEST_PLAN_OF_SPONSOR_YEAR_OTHER_PLANS_NEVER_SUMMED",
                 "NAICS_" + (e.get("naics_specificity") or "unstated").upper()}
        rights, conf, review = "public_official", "medium", "machine_matched"
        if e.get("state_mismatch_flag") == "1":
            flags.add("SPONSOR_STATE_DIFFERS_FROM_ENTITY_STATE_RULING_OPEN")
            rights, conf, review = "withheld_unverified", "low", "unresolved"
            withheld["form5500_state_mismatch_ruling_open"] = withheld.get("form5500_state_mismatch_ruling_open", 0) + 1
        if e.get("attribution_repaired_by"):
            flags.add("ATTRIBUTION_REPAIRED_BY_262")
        if e.get("cedar_uid") and not uid:
            flags.add("SOURCE_CEDAR_UID_NOT_CANONICAL_CE")
            review = "unresolved"
        v, st = value_of(e.get("employment"))
        out.append(labor_row(
            source_system="dol_form5500", source_record_id=f"ein={ein};ack_id={ack};dataset_year={year}",
            measure="active_plan_participants",
            measured_concept=("Form 5500 active plan participants of the sponsor's largest plan: NOT employees - "
                              "excludes employees below the plan's age/service threshold, includes eligible part-timers"),
            evidence_class="reported_plan_participants", value=v, value_status=st, unit="participants",
            disclosure_limitation="none", suppression_flag="0", period=year,
            period_type="form5500_dataset_year", cedar_uid=uid,
            employer_name_as_reported=e.get("sponsor_name", ""),
            establishment_or_unit_as_reported=e.get("plan_name", ""),
            reported_state=e.get("sponsor_state", ""),
            match_method="clean_table_attribution:" + (e.get("match_rule") or "") +
                         (";repair=" + e["attribution_repaired_by"] if e.get("attribution_repaired_by") else ""),
            confidence=conf, review_status=review, flags="|".join(sorted(flags)),
            legacy_observation_ids=e["observation_id"], source_url=e.get("source_url", ""),
            retrieved_date=FOURWHEELER_RETRIEVED, rights_class=rights))
    return out


def build_lodes(emp_rows, facilities):
    out = []
    for e in emp_rows:
        if e["measurement_type"] != "LODES_BLOCK_WORKPLACE_JOBS":
            continue
        q = dict(re.findall(r'(\w+)="([^"]*)"', e.get("source_quote", "")))
        block = q.get("w_geocode", "")
        key = f"{e.get('source_record', '')}::block={block}" if block else f"{e.get('source_record', '')}::obs={e['observation_id']}"
        fac_id, fflag = place_facility(facilities, e.get("facility_id", ""), e.get("cedar_place_id", ""))
        flags = {"BLOCK_JOBS_ARE_NOT_PROPERTY_PAYROLL", "BLOCK_ASSIGNED_FROM_VENDOR_COORDINATES",
                 "NOISE_INFUSED_BY_DESIGN"} | ({fflag} if fflag else set())
        common = dict(source_system="census_lodes_wac", source_record_id=key, period=num(e.get("year")),
                      period_type="lodes_reference_year", cedar_uid=ce(e.get("cedar_uid", "")),
                      gaming_facility_id=fac_id, reported_state=e.get("state", ""),
                      match_method=e.get("match_rule", ""), confidence="low", review_status="machine_matched",
                      disclosure_limitation="noise_infused", suppression_flag="0",
                      legacy_observation_ids=e["observation_id"], legacy_facility_id=e.get("facility_id", ""),
                      source_url=e.get("source_url", ""), retrieved_date=iso_date(e.get("fetched_date", "")),
                      evidence_class="geographic_context_not_property_payroll",
                      flags="|".join(sorted(flags)), rights_class="internal_vendor")
        for measure, field, concept in (
                ("block_total_jobs_all_employers", "C000", "All jobs whose workplace is this census block, every employer"),
                ("block_jobs_naics71_all_employers", "CNS17", "Block jobs in NAICS 71 (arts/entertainment/recreation), every employer")):
            v, st = value_of(q.get(field, e.get("employment", "") if field == "C000" else ""))
            out.append(labor_row(**common, measure=measure, measured_concept=concept, value=v,
                                 value_status="noise_infused" if v else st, unit="jobs"))
    return out


def build_labor_demand(inputs, facilities):
    _, rows = inputs.clean("gaming_property_labor_demand.csv", required=False)
    out = []
    for r in rows:
        key = f"{r.get('source_url', '')}#md5={r.get('source_md5', '')}#{r.get('provision_type', '')}"
        fac_id, fflag = place_facility(facilities, r.get("facility_id", ""), r.get("cedar_place_id", ""))
        v, st = value_of(r.get("value"))
        out.append(labor_row(
            source_system="property_website", source_record_id=key,
            measure="labor_demand:" + (r.get("provision_type") or "unspecified"),
            measured_concept="A job posting or employment-policy statement on a property website: labor DEMAND, never an employee count",
            evidence_class="labor_demand_statement", value=v, value_status=st if v else "not_a_count",
            unit=r.get("unit", "") or "statement", disclosure_limitation="none", suppression_flag="0",
            period=iso_date(r.get("retrieved_at", "")), period_type="retrieval_date",
            cedar_uid=ce(r.get("cedar_uid", "")), gaming_facility_id=fac_id,
            establishment_or_unit_as_reported=r.get("facility_name", ""),
            match_method=r.get("attribution_basis", ""), confidence="low", review_status="machine_matched",
            flags="|".join(sorted({"NOT_AN_EMPLOYEE_COUNT", "SITE_RETENTION_TERMS_UNREVIEWED"} | ({fflag} if fflag else set()))),
            legacy_observation_ids=r.get("observation_id", ""), legacy_facility_id=r.get("facility_id", ""),
            source_url=r.get("source_url", ""), retrieved_date=iso_date(r.get("retrieved_at", "")),
            rights_class="withheld_unverified"))
    return out


def nlrb_evidence(r, facilities_by_name, neid_to_ce):
    """Return (cedar_uid, gaming_facility_id, legacy_fid, method, confidence, reason).
    Never a bare name match: a tribal self-identification must agree on
    state with a spine resolution, or a d/b/a brand must be a Cedar facility
    in the same state."""
    employer = r.get("employer", "")
    loc = r.get("Unit Location", "")
    state = (loc.rsplit(",", 1)[-1].strip().upper()) if "," in loc else ""
    city = norm(loc.rsplit(",", 1)[0]) if "," in loc else ""
    brands = [employer] + re.split(r"\bd/?b/?a\b|\bdoing business as\b", employer, flags=re.I)[1:]
    for b in brands:
        hits = facilities_by_name.get((fkey(b), state), [])
        if len(hits) == 1:
            fid, f = hits[0]
            method = "dba_brand_equals_cedar_facility_name_same_state"
            if f["city"] and city and f["city"] != city:
                method += ";city_differs"
            return (f["cedar_uid"], gg.facility_id_for(f["place"]), fid, method,
                    "medium", "")
    self_id = bool(TRIBAL_SELF_ID_RE.search(employer))
    tid = (r.get("tribe_id") or "").strip()
    if self_id and tid and r.get("resolution") == "matched":
        uid = neid_to_ce.get(tid, "")
        core = norm(r.get("matched_core", ""))
        tribe_states = {f["state"] for f in facilities_by_name.get(("__uid__", uid), [])}
        if uid and core and core in norm(employer) and state in tribe_states:
            return (uid, "", "", "employer_self_identifies_as_tribal_enterprise+spine_resolution+state_agrees",
                    "medium", "")
        return ("", "", "", "", "low", "tribal_self_id_without_state_or_crosswalk_agreement")
    if self_id:
        return ("", "", "", "", "low", "tribal_self_id_unresolved")
    if r.get("resolution") == "matched":
        return ("", "", "", "", "low", "resolver_false_positive_no_tribal_signal")
    if r.get("resolution") == "commercial operator":
        return ("", "", "", "", "low", "commercial_operator")
    return ("", "", "", "", "low", "no_tribal_signal")


def build_nlrb(inputs, fw_root, facilities, neid_to_ce, withheld, coverage, legacy_report):
    header, rows = read_external(inputs, fw_root, "data/resolved_nlrb_gaming.csv")
    legacy_prefix_scan("4wheeler/casino_employment_validation/data/resolved_nlrb_gaming.csv", header, rows, legacy_report)
    if not rows:
        return []
    by_name = defaultdict(list)
    for fid, f in facilities.items():
        if f["place"] and f["cedar_uid"] and not f["duplicate_of"]:
            by_name[(fkey(f["name"]), f["state"])].append((fid, f))
            by_name[("__uid__", f["cedar_uid"])].append(f)
    out, reasons, seen = [], Counter(), Counter()
    for r in rows:
        case = (r.get("Case Number") or "").strip()
        uid, fac_id, legacy_fid, method, conf, reason = nlrb_evidence(r, by_name, neid_to_ce)
        if reason in ("resolver_false_positive_no_tribal_signal", "commercial_operator", "no_tribal_signal"):
            reasons[reason] += 1
            continue
        key = f"case={case};unit={r.get('Unit ID', '')};tally={r.get('Tally Type', '')};tally_date={iso_date(r.get('Tally Issued Date', ''))}"
        seen[key] += 1
        if seen[key] > 1:
            reasons["duplicate_source_row"] += 1
            continue
        linked = bool(uid or fac_id)
        rights = "public_official" if linked else "withheld_unverified"
        review = "machine_matched" if linked else "unresolved"
        reasons["linked" if linked else reason] += 1
        vf, va = num(r.get("votes_for_unions")), num(r.get("Votes Against"))
        outcome = ""
        if vf and va:
            outcome = ("majority_for_labor_organization" if float(vf) > float(va) else
                       "majority_against" if float(vf) < float(va) else "tie")
        tally_date = iso_date(r.get("Tally Issued Date", ""))
        flags = {"BARGAINING_UNIT_NOT_EMPLOYER_WORKFORCE", "NLRA_JURISDICTION_OVER_TRIBAL_GAMING_PER_SAN_MANUEL_2004",
                 "TALLY_MAJORITY_IS_NOT_CERTIFICATION"}
        if tally_date and tally_date < "2004-05-28":
            flags.add("PRE_SAN_MANUEL_DECISION_JURISDICTION_UNSETTLED")
        common = dict(source_system="nlrb_election", source_record_id=key, period=tally_date,
                      period_type="election_tally_date", outcome=outcome, cedar_uid=uid,
                      gaming_facility_id=fac_id, employer_name_as_reported=r.get("employer", ""),
                      establishment_or_unit_as_reported=r.get("voting_unit_text", ""),
                      reported_state=(r.get("Unit Location", "").rsplit(",", 1)[-1].strip().upper()),
                      match_method=method or reason, confidence=conf, review_status=review,
                      disclosure_limitation="none", suppression_flag="0", legacy_facility_id=legacy_fid,
                      source_url=f"https://www.nlrb.gov/case/{case}", source_date=tally_date,
                      retrieved_date=FOURWHEELER_RETRIEVED, flags="|".join(sorted(flags)), rights_class=rights)
        for measure, field, concept, ev in (
                ("eligible_voters", "No. of Eligible Voters", "Employees eligible to vote in this bargaining unit on the election date; a unit, not the workforce", "reported_bargaining_unit"),
                ("votes_for_labor_organization", "votes_for_unions", "Ballots cast for the labor organization(s)", "reported_election_tally"),
                ("votes_against", "Votes Against", "Ballots cast against representation", "reported_election_tally"),
                ("ballots_counted", "Total Ballots Counted", "Total ballots counted in the tally", "reported_election_tally")):
            v, st = value_of(r.get(field))
            out.append(labor_row(**common, measure=measure, measured_concept=concept, evidence_class=ev,
                                 value=v, value_status=st, unit="voters" if measure == "eligible_voters" else "ballots"))
    coverage["nlrb_candidate_disposition"] = dict(sorted(reasons.items()))
    for k in ("resolver_false_positive_no_tribal_signal", "commercial_operator", "no_tribal_signal"):
        if reasons.get(k):
            withheld["nlrb_excluded_" + k] = reasons[k]
    return out


# ---------------------------------------------------------------- advocacy
def adv_row(**kw) -> dict:
    row = {c: "" for c in ADV_HEADER}
    row.update({k: ("" if v is None else str(v)) for k, v in kw.items()})
    row["source_collection"] = "advocacy_engagement"
    row["advocacy_link_id"] = gg.derive_id("GADV", row["source_collection"], row["source_table"],
                                           row["source_event_id"], row["link_target_type"], row["target_id"])
    return row


def load_compacts(inputs):
    _, rows = inputs.clean("compacts.csv", required=False)
    by_uid = defaultdict(list)
    for r in rows:
        u = ce(r.get("cedar_uid", ""))
        if u and r.get("compact_id") and r.get("original_effective_date"):
            by_uid[u].append(r)
    return by_uid, rows


def compact_target(text, uid, event_date, compacts_by_uid):
    if not (uid and COMPACT_CONTEXT_RE.search(text or "")):
        return None
    cs = compacts_by_uid.get(uid, [])
    states = {c["state"] for c in cs}
    named = {m.group(1) for m in STATE_RE.finditer(text)} & states
    if len(named) == 1:
        state = next(iter(named))
    elif len(states) == 1 and not STATE_RE.search(text):
        state = next(iter(states))
    else:
        return None
    in_force = [c for c in cs if c["state"] == state and c["original_effective_date"] <= (event_date or "9999")]
    if not in_force:
        return None
    c = max(in_force, key=lambda c: (c["original_effective_date"], c["compact_id"]))
    return c["compact_id"], state


FACILITY_WORD = r"(?:casino|casinos|resort|hotel|bingo|travel center|event center)"
NON_BRAND_WORDS = ({"tribe", "tribes", "band", "nation", "nations", "indian", "indians", "rancheria",
                    "pueblo", "community", "reservation", "river", "lake", "creek", "valley", "mountain",
                    "north", "south", "east", "west", "northern", "southern", "eastern", "western",
                    "county", "city", "grand", "little", "big", "new", "tribal", "native", "american"}
                   | {w for st in US_STATES for w in norm(st).split()})


def facility_targets(text_n, uid, fac_by_uid):
    hits = []
    for place, core in fac_by_uid.get(uid, []):
        if re.search(r"(?:^| )" + re.escape(core) + r" " + FACILITY_WORD + r"\b", text_n):
            hits.append((place, core))
    return hits


ENTERPRISE_WORD_RE = re.compile(r"gaming|casino|entertainment|enterprise|authority|development|resort|holdings|hospitality", re.I)
TRIBAL_GOV_RE = re.compile(r"\b(?:tribe|tribes|band|nation|rancheria|indians|pueblo|community|council)\b", re.I)


def facility_owner_names(inputs):
    """cedar_uid -> names the owner is known by in gaming_facilities (tribe +
    canonical name), used only to refuse single-word brands that are the
    owner's own name."""
    _, rows = inputs.clean("gaming_facilities.csv")
    out = defaultdict(set)
    for r in rows:
        u = ce(r.get("cedar_uid", ""))
        if u:
            out[u].update({r.get("tribe", ""), r.get("tribe_canonical_name", "")})
    return out


def build_advocacy(inputs, facilities, withheld, coverage, legacy_report):
    links = []
    compacts_by_uid, compact_rows = load_compacts(inputs)
    fac_by_uid = defaultdict(list)
    owner_names = {u: " ".join(sorted(v)) for u, v in facility_owner_names(inputs).items()}
    for fid, f in facilities.items():
        if not (f["place"] and f["cedar_uid"]) or f["duplicate_of"]:
            continue
        # Brand core: the facility name minus generic words. A single-token
        # core must be long and must not be a word of the owner's own name
        # (so "Seminole" never names a casino, "Foxwoods" does).
        # A tribe's or state's own name is not a casino brand: "Bay Mills" in a
        # land-claims bill is the community, not Bay Mills Resort & Casinos.
        # The brand core must carry a word that is neither generic, tribal,
        # geographic-state nor part of the owner's name, and in the text it
        # must be followed by a facility word (see facility_targets).
        core = [t for t in norm(f["name"]).split() if t not in GENERIC_FACILITY_TOKENS]
        owner_words = set(norm(owner_names.get(f["cedar_uid"], "")).split())
        free = [t for t in core if t not in owner_words and t not in NON_BRAND_WORDS and len(t) >= 4]
        if core and free:
            fac_by_uid[f["cedar_uid"]].append((f["place"], " ".join(core)))
    for u in fac_by_uid:
        fac_by_uid[u] = sorted(set(fac_by_uid[u]))
    _, nest = inputs.clean("nest_enterprises.csv", required=False)
    legacy_prefix_scan("data/clean/nest_enterprises.csv", list(nest[0].keys()) if nest else [], nest, legacy_report)
    ent_by = defaultdict(set)
    for r in nest:
        u = ce(r.get("owner_hub_cedar_uid", ""))
        name = r.get("enterprise_name", "")
        # A NEST row that is the tribal government itself is not an enterprise
        # link target; the cedar_uid link already carries that relationship.
        if not ENTERPRISE_WORD_RE.search(name) or TRIBAL_GOV_RE.search(name):
            continue
        if u and gg.ENTERPRISE_ID_RE.match(r.get("enterprise_id", "")):
            ent_by[(entity_key(r.get("enterprise_name", "")), u)].add(r["enterprise_id"])

    # --- LDA
    header, lda = inputs.clean("native_entity_lobbying_disclosures.csv")
    legacy_prefix_scan("data/clean/native_entity_lobbying_disclosures.csv", header, lda, legacy_report)
    reasons = Counter()
    for r in lda:
        fu = r.get("filing_uuid", "").strip()
        codes = [c.strip() for c in (r.get("lobbying_issues_codes") or "").split("|") if c.strip()]
        text = r.get("specific_issues_text") or ""
        gam = "GAM" in codes
        m = GAMING_RE.search(text)
        if not (gam or m):
            continue
        if r.get("attribution_withdrawn") == "1" or (r.get("match_confidence") or "").startswith("withdrawn"):
            reasons["lda_attribution_withdrawn"] += 1
            continue
        if r.get("is_superseded") == "1":
            reasons["lda_superseded_by_amendment"] += 1
            continue
        tops = topics_for(text, gam)
        basis = []
        if gam:
            basis.append("LDA general_issue_code GAM (Gaming)")
        if m:
            basis.append(f"specific_issues_text mentions '{m.group(0)}'")
        evidence = span(text, m) if m else "lobbying_issues_codes=" + "|".join(codes)
        date = iso_date(r.get("dt_posted", ""))
        uid = ce(r.get("cedar_uid", ""))
        conf_attr = r.get("match_confidence") if r.get("match_confidence") in gg.CONFIDENCE else "low"
        common = dict(source_table="native_entity_lobbying_disclosures.csv", source_event_id=fu,
                      source_native_id=fu, source_event_type="registered_lobbying", event_date=date,
                      topics="|".join(tops), crossref_source_key=f"lda_period={r.get('filing_year', '')}-{r.get('filing_period', '')}",
                      source_system="senate_lda", source_record_id=fu, source_url=r.get("filing_url", ""),
                      source_date=date, rights_class="public_official")
        if uid:
            links.append(adv_row(**common, link_target_type="cedar_uid", target_id=uid,
                                 link_basis="; ".join(basis) + f"; client attributed by Advocacy collection ({r.get('attribution_method', '')})",
                                 evidence_text=evidence, confidence=conf_attr, review_status="machine_matched"))
            text_n = f" {norm(text)} "
            for place, name_n in facility_targets(text_n, uid, fac_by_uid):
                links.append(adv_row(**common, link_target_type="gaming_facility",
                                     target_id=gg.facility_id_for(place),
                                     link_basis=f"issue text names Cedar facility '{name_n}' of the same client cedar_uid",
                                     evidence_text=span(text, re.search(r"(?i)" + r"\W+".join(map(re.escape, name_n.split())), text)) if re.search(r"(?i)" + r"\W+".join(map(re.escape, name_n.split())), text) else name_n,
                                     confidence="medium", review_status="machine_matched"))
            ct = compact_target(text, uid, date, compacts_by_uid)
            if ct:
                cm = COMPACT_CONTEXT_RE.search(text)
                links.append(adv_row(**common, link_target_type="compact", target_id=ct[0],
                                     link_basis=f"issue text concerns a gaming compact; client's {ct[1]} compact in force on the posting date (compacts.csv)",
                                     evidence_text=span(text, cm), confidence="low", review_status="machine_matched"))
            ents = ent_by.get((entity_key(r.get("client_name", "")), uid), set())
            if len(ents) == 1:
                links.append(adv_row(**common, link_target_type="enterprise", target_id=next(iter(ents)),
                                     link_basis="LDA client is the NEED enterprise of the same owner cedar_uid (exact normalized name + owner agreement)",
                                     evidence_text="client named on the filing (see source_url)", confidence="medium",
                                     review_status="machine_matched"))
        else:
            reasons["lda_gaming_filing_without_ce_client"] += 1
            links.append(adv_row(**common, link_target_type="topic_only", target_id=tops[0] if tops else "gaming",
                                 link_basis="; ".join(basis) + "; client not resolved to a CE entity",
                                 evidence_text=evidence, confidence="high" if gam else "medium",
                                 review_status="source_asserted"))

    # --- FR consultation events (no participant uid on any gaming row today)
    header, cons = inputs.clean("consultation_events.csv")
    legacy_prefix_scan("data/clean/consultation_events.csv", header, cons, legacy_report)
    seen = set()
    for r in cons:
        text = " ".join(r.get(k, "") for k in ("agency", "sub_agency", "program", "topic"))
        m = GAMING_RE.search(text)
        if not m:
            continue
        eid = r.get("consultation_event_id", "").strip()
        uid = ce(r.get("cedar_uid", ""))
        ttype, tid = ("cedar_uid", uid) if uid else ("topic_only", "")
        tops = topics_for(text)
        tid = tid or (tops[0] if tops else "gaming")
        if (eid, ttype, tid) in seen:
            continue
        seen.add((eid, ttype, tid))
        fr = r.get("fr_document_number", "").strip()
        links.append(adv_row(source_table="consultation_events.csv", source_event_id=eid, source_native_id=fr,
                             source_event_type="tribal_consultation", event_date=iso_date(r.get("event_start_date") or r.get("notice_date")),
                             link_target_type=ttype, target_id=tid,
                             link_basis=f"consultation agency/topic mentions '{m.group(0)}'",
                             evidence_text=re.sub(r"\s+", " ", (r.get("topic") or text))[:220],
                             topics="|".join(tops), crossref_source_key=f"federal_register_document={fr}" if fr else "",
                             confidence="high" if uid else "medium",
                             review_status="machine_matched" if uid else "source_asserted",
                             source_system="federal_register", source_record_id=fr or eid,
                             source_url=r.get("source_url", ""), source_date=iso_date(r.get("notice_date")),
                             retrieved_date=iso_date(r.get("fetched_date")), rights_class="public_official"))

    # --- regulations.gov comments
    header, rgc = inputs.clean("regulations_gov_comments.csv")
    legacy_prefix_scan("data/clean/regulations_gov_comments.csv", header, rgc, legacy_report)
    for r in rgc:
        text = (r.get("title") or "") + " " + (r.get("highlighted_excerpt") or "")
        m = GAMING_RE.search(text)
        nigc = r.get("agency_id") == "NIGC"
        if not (m or nigc):
            continue
        cid = r.get("comment_id", "").strip()
        uid = ce(r.get("cedar_uid", ""))
        tops = topics_for(text + (" NIGC" if nigc else ""))
        if nigc and "gaming" not in tops:
            tops = ["gaming"] + tops
            tops = [t for t in TOPIC_ORDER if t in set(tops)]
        docket = cid.rsplit("-", 1)[0] if cid.count("-") >= 2 else ""
        basis = ("comment filed on a National Indian Gaming Commission docket" if nigc else
                 f"comment title/excerpt mentions '{m.group(0)}'")
        ttype, tid = ("cedar_uid", uid) if uid else ("topic_only", tops[0] if tops else "gaming")
        date = iso_date(r.get("posted_date"))
        links.append(adv_row(source_table="regulations_gov_comments.csv",
                             source_event_id=r.get("regulations_gov_comment_row_id", ""), source_native_id=cid,
                             source_event_type="regulatory_comment", event_date=date, link_target_type=ttype,
                             target_id=tid, link_basis=basis + ("; filer attributed by Advocacy collection (" + (r.get("attribution_class") or "") + ")" if uid else ""),
                             evidence_text=span(text, m) if m else re.sub(r"\s+", " ", r.get("title", ""))[:220],
                             topics="|".join(tops), crossref_source_key=f"regulations_gov_docket={docket}" if docket else "",
                             confidence="high" if (uid and nigc) else "medium",
                             review_status="machine_matched" if uid else "source_asserted",
                             source_system="regulations_gov", source_record_id=cid,
                             source_url=r.get("comment_url", ""), source_date=date,
                             retrieved_date=iso_date(r.get("retrieved_date")), rights_class="public_official"))

    # --- congressional testimony (2025-2026 harvest); uid from 1187's own output
    _, tst = inputs.read("data/source/advocacy/congressional_testimony_2025_2026.csv", required=False)
    header, adv_out = inputs.read("dist/customer/native_federal_advocacy_2025_2026.csv", required=False)
    legacy_prefix_scan("dist/customer/native_federal_advocacy_2025_2026.csv", header, adv_out, legacy_report)
    tuid = defaultdict(set)
    for r in adv_out:
        if r.get("activity_type") == "congressional_testimony" and ce(r.get("cedar_uid", "")):
            tuid[r.get("activity_id", "")].add(r["cedar_uid"])
    for r in tst:
        text = (r.get("hearing_title") or "") + " " + (r.get("witness_organization") or "")
        m = GAMING_RE.search(text)
        if not m:
            continue
        tid_ = r.get("testimony_id", "").strip()
        uids = tuid.get(tid_, set())
        tops = topics_for(text)
        uid = next(iter(uids)) if len(uids) == 1 else ""
        ttype, target = ("cedar_uid", uid) if uid else ("topic_only", tops[0] if tops else "gaming")
        date = iso_date(r.get("activity_date"))
        links.append(adv_row(source_table="data/source/advocacy/congressional_testimony_2025_2026.csv",
                             source_event_id=tid_, source_native_id=r.get("source_record_id", ""),
                             source_event_type="congressional_testimony", event_date=date,
                             link_target_type=ttype, target_id=target,
                             link_basis=f"hearing title / witness organization mentions '{m.group(0)}'" +
                                        ("; witness organization resolved by 1187" if uid else ""),
                             evidence_text=span(text, m), topics="|".join(tops),
                             crossref_source_key=r.get("source_record_id", ""),
                             confidence="medium", review_status="machine_matched" if uid else "source_asserted",
                             source_system="congressional_committee", source_record_id=r.get("source_record_id", "") or tid_,
                             source_url=r.get("source_url", ""), source_date=date, rights_class="public_official"))
    for k, v in reasons.items():
        withheld[k] = v
    coverage["advocacy_sources_not_linkable"] = {
        "nonprofit_schedule_c_lobbying.csv": "no issue text or topic field; cannot be tied to gaming without inventing relevance",
        "dear_tribal_leader_letters.csv": "0 gaming-subject letters in the current table",
        "fr_ex_parte_parties.csv": "0 gaming-agency notices in the current table",
        "bia_and_new_fr_meetings_2025_2026.csv / fr_consultations_new_2025_2026.csv": "0 gaming topics",
    }
    return links


# ---------------------------------------------------------------- build
ACQUISITION_LEADS = [
    {"source": "DOL OLMS LM-2/LM-3/LM-4 union financial reports (units at tribal casinos, e.g. UNITE HERE, UAW, Teamsters locals)",
     "status": "source_limited", "local_copy": "none found on this machine (Cedar Press data/, 4wheeler, Lumecon-data searched)",
     "lead": "https://olmsapps.dol.gov/olpdr/ (public data download, yearly zip); download off C: or filter by employer before storing",
     "rights_class_expected": "public_official"},
    {"source": "State WARN Act notices (tribal casino COVID layoffs Mar-Apr 2020, exact affected-employee counts)",
     "status": "source_limited", "local_copy": "none found",
     "lead": "state workforce agency WARN listings (CA EDD, WA ESD, MI LEO, OK OESC...); no central file",
     "rights_class_expected": "public_official"},
    {"source": "BLS QCEW county x NAICS 7132", "status": "source_limited",
     "local_copy": "4wheeler test_c_county_panel.csv (county aggregates; NAICS 7132 suppressed in every shock county-year checked)",
     "lead": "never attach a county cell to a facility or tribe; suppressed cells must be carried as suppressed, never 0",
     "rights_class_expected": "public_official"},
    {"source": "SEC 10-K employee counts (Mohegan, Seneca Gaming, Inn of the Mountain Gods, River Rock, Choctaw Resort Dev.)",
     "status": "source_limited", "local_copy": "4wheeler data/sec_employment_sentences.csv (not read: verbatim sentences need per-filing definition review)",
     "lead": "enterprise-level headcounts FY1996-FY2022; lane for financial disclosures", "rights_class_expected": "public_official"},
]


def build(inputs: gg.Inputs, out_dir: Path, fourwheeler_root: Path | None = FOURWHEELER_DEFAULT) -> dict:
    withheld: dict[str, int] = {}
    coverage: dict = {}
    notes: list[str] = []
    legacy_report: dict = {}

    facilities = load_facilities(inputs)
    fh, frows = inputs.clean("gaming_facilities.csv")
    legacy_prefix_scan("data/clean/gaming_facilities.csv", fh, frows, legacy_report)
    neid_to_ce = load_neid_crosswalk(inputs)
    eh, emp = inputs.clean("gaming_employment_observations.csv")
    legacy_prefix_scan("data/clean/gaming_employment_observations.csv", eh, emp, legacy_report)
    lh, ld = inputs.clean("gaming_property_labor_demand.csv", required=False)
    legacy_prefix_scan("data/clean/gaming_property_labor_demand.csv", lh, ld, legacy_report)
    ch, crows = inputs.clean("compacts.csv", required=False)
    legacy_prefix_scan("data/clean/compacts.csv", ch, crows, legacy_report)

    excluded_types = Counter(e["measurement_type"] for e in emp
                             if e["measurement_type"] in ("PROJECTED", "ENVIRONMENTAL_REVIEW_COUNT"))
    for k, v in excluded_types.items():
        withheld["excluded_to_lane_E_" + k.lower()] = v
    unknown = Counter(e["measurement_type"] for e in emp) - Counter({
        k: 10 ** 9 for k in ("OSHA_ESTABLISHMENT_REPORTED", "OSHA_TRIBE_LEVEL_REPORTED",
                             "FORM5500_ACTIVE_PARTICIPANTS", "LODES_BLOCK_WORKPLACE_JOBS",
                             "PROJECTED", "ENVIRONMENTAL_REVIEW_COUNT")})
    if unknown:
        raise gg.GamingContractError(f"REFUSED: unmapped measurement_type(s) {dict(unknown)}")

    osha, n_osha = build_osha(inputs, emp, facilities, withheld, notes)
    labor = (osha + build_form5500(emp, withheld)
             + merge_shared_source_records(build_lodes(emp, facilities), withheld,
                                           "lodes_block_shared_by_legacy_facilities_merged")
             + merge_shared_source_records(build_labor_demand(inputs, facilities), withheld,
                                           "labor_demand_statement_shared_by_facilities_merged"))
    labor += build_nlrb(inputs, fourwheeler_root, facilities, neid_to_ce, withheld, coverage, legacy_report)
    assert_labor_invariants(labor)
    links = build_advocacy(inputs, facilities, withheld, coverage, legacy_report)
    assert_link_invariants(ADV_HEADER, links)

    receipts = [gg.write_table(out_dir, LABOR_TABLE, LABOR_HEADER, labor, LABOR_CONTRACT),
                gg.write_table(out_dir, ADV_TABLE, ADV_HEADER, links, ADV_CONTRACT)]
    for table, header, rows in ((LABOR_TABLE, LABOR_HEADER, labor), (ADV_TABLE, ADV_HEADER, links)):
        keep, pub = gg.public_projection(table, header, rows, CONTRACTS[table]["field_rights"])
        coverage[table] = {"public_projection_rows": len(pub), "public_fields": len(keep),
                           "withheld_fields": len(header) - len(keep),
                           "rows_by_rights_class": dict(sorted(Counter(r["rights_class"] for r in rows).items()))}

    by_sys_year = defaultdict(Counter)
    for r in labor:
        by_sys_year[r["source_system"]][r["period"][:4] or "undated"] += 1
    coverage["labor_rows_by_source_system_year"] = {k: dict(sorted(v.items())) for k, v in sorted(by_sys_year.items())}
    records = defaultdict(set)
    for r in labor:
        records[r["source_system"]].add(r["source_record_id"])
    coverage["labor_source_records_by_system"] = {k: len(v) for k, v in sorted(records.items())}
    coverage["labor_osha_establishment_years"] = n_osha
    coverage["labor_2025_2026_rows"] = {y: dict(sorted(Counter(r["source_system"] for r in labor if r["period"][:4] == y).items()))
                                        for y in ("2025", "2026")}
    coverage["labor_distinct_cedar_uid"] = len({r["cedar_uid"] for r in labor if r["cedar_uid"]})
    coverage["labor_distinct_facilities"] = len({r["gaming_facility_id"] for r in labor if r["gaming_facility_id"]})
    coverage["labor_rows_by_review_status"] = dict(sorted(Counter(r["review_status"] for r in labor).items()))
    coverage["links_by_target_type"] = dict(sorted(Counter(r["link_target_type"] for r in links).items()))
    coverage["links_by_source_table"] = dict(sorted(Counter(r["source_table"] for r in links).items()))
    coverage["links_distinct_events_by_table"] = {t: len({r["source_event_id"] for r in links if r["source_table"] == t})
                                                  for t in sorted({r["source_table"] for r in links})}
    coverage["links_by_topic"] = dict(sorted(Counter(t for r in links for t in r["topics"].split("|") if t).items()))
    coverage["links_by_event_year"] = dict(sorted(Counter(r["event_date"][:4] or "undated" for r in links).items()))
    coverage["acquisition_leads_source_limited"] = ACQUISITION_LEADS
    coverage["legacy_prefix_values_in_inputs"] = legacy_report
    notes.append("OLMS and WARN are absent locally; recorded as source_limited leads, nothing downloaded.")
    notes.append("Form 5500 plan number (PN) is not carried by the 4wheeler/Cedar extract; ACK_ID identifies the plan-year filing.")
    notes.append("Regulatory-event targets are not emitted: lane E owns GREG derivation; FR document / docket keys are in crossref_source_key.")
    return {"tables": receipts, "inputs": inputs.receipts, "coverage": coverage,
            "withheld": dict(sorted(withheld.items())), "notes": notes,
            "id_contract_status": gg.ID_CONTRACT_STATUS}


def assert_labor_invariants(rows):
    for r in rows:
        if r["source_system"] == "dol_form5500" and ("employ" in r["measure"] or r["unit"] == "employees"):
            raise gg.GamingContractError(f"REFUSED: plan participants labelled employees {r['source_record_id']}")
        if r["value_status"] in ("suppressed", "not_reported", "withheld_implausible") and r["value"] != "":
            raise gg.GamingContractError(f"REFUSED: {r['value_status']} value carries a number {r['labor_observation_id']}")
        if r["suppression_flag"] == "1" and r["value"] != "":
            raise gg.GamingContractError(f"REFUSED: suppressed cell carries a value {r['labor_observation_id']}")
        if r["cedar_uid"] and not r["match_method"]:
            raise gg.GamingContractError(f"REFUSED: cedar_uid without a match method {r['labor_observation_id']}")
        if r["match_method"].startswith("name") or r["match_method"] == "name_only":
            raise gg.GamingContractError(f"REFUSED: name-only attribution {r['labor_observation_id']}")


def assert_link_invariants(header, rows):
    bad = ADV_FORBIDDEN_FIELDS & set(header)
    if bad:
        raise gg.GamingContractError(f"REFUSED: lobbying fields copied into Gaming {sorted(bad)}")
    for r in rows:
        if not r["source_event_id"]:
            raise gg.GamingContractError("REFUSED: link without the original event id")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--input-root", default=str(gg.DEFAULT_INPUT_ROOT))
    b.add_argument("--output-root", required=True)
    b.add_argument("--fourwheeler-root", default=str(FOURWHEELER_DEFAULT))
    b.add_argument("--as-of", default="")
    a = ap.parse_args(argv)
    inputs = gg.Inputs(a.input_root)
    out = Path(a.output_root)
    result = build(inputs, out, Path(a.fourwheeler_root) if a.fourwheeler_root else None)
    result["producer"] = PRODUCER
    result["schema_version"] = gg.SCHEMA_VERSION
    if a.as_of:
        result["as_of"] = a.as_of
    (out / f"{PRODUCER}.receipt.json").write_text(
        json.dumps(result, sort_keys=True, indent=1, default=sorted) + "\n", encoding="utf-8", newline="\n")
    for t in result["tables"]:
        print(f"  {t['table']}: {t['rows']} rows  sha256={t['sha256'][:16]}")
    print("  withheld:", json.dumps(result["withheld"], sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
