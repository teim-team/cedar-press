"""1202 - Cedar Grove Gaming, Lane E: compacts, regulatory events, land
eligibility, environmental review, licensing and litigation.

WHY THIS EXISTS
---------------
Cedar already holds the regulatory record of Indian gaming in some twenty
source-shaped tables: the BIA compact index (compacts / compact_versions /
compact_structured_terms / compact_events), BIA gaming land decisions and their
dated events, five NIGC document families (declination letters, enforcement
actions, management-contract approvals, Indian-lands opinions, game
classification opinions), NIGC ordinance approvals, Federal Register notices,
the NEPA pilot, digital-wagering relationships, WA machine allocations, SEC
vendor-licence mentions and scattered court records. Each was built by a
different script with its own vocabulary, so a question as plain as "what
happened to this tribe's gaming authority in 2025?" had to be answered by
reading eight files and knowing which dates mean what.

This producer consolidates them into one canonical table per OBJECT TYPE,
without collapsing different objects into one another:

    gaming_compacts.csv               instrument (BIA compact_id kept)
    gaming_compact_versions.csv       amendment / extension / renewal (version_id kept)
    gaming_compact_terms.csv          contractual clause terms (term_id kept)
    gaming_regulatory_events.csv      one row per dated regulatory action
    gaming_land_eligibility.csv       one row per land / Indian-lands determination
    gaming_environmental_reviews.csv  one row per NEPA document per project
    gaming_licenses.csv               licence mentions, wagering authorisations,
                                      machine allocations
    gaming_litigation.csv             court and administrative proceedings

THE DISTINCTIONS THIS SCRIPT EXISTS TO KEEP
-------------------------------------------
* A NIGC declination letter is an opinion that submitted documents are NOT a
  management contract. It is never an approval (status `declination_issued`;
  `_guard_event` refuses any declination row carrying an approval status).
* A decision date is the date of a federal action. It is never a facility
  opening date; no output column holds an opening date, and applicant
  "projected opening" figures from NEPA documents are not read into any row.
* A compact revenue-share RATE is a contractual term. It is never a payment,
  and no terms row carries a dollar amount paid (`is_payment_observation` = no).
* The same Federal Register document is cited by compact_versions, compacts,
  gaming_land_decisions, gaming_decision_events, federal_actions and
  consultation_events. It becomes ONE regulatory event keyed on the FR
  document number; every citing source ID is kept in `also_cited_by`.
* A reversal is a second event, not an overwrite: an approval followed by a
  rescission survives as two rows with their own dates.
* `cedar_uid` holds only canonical CE- identifiers taken from the source row's
  existing link (gaming_grove.is_ce_uid). Legacy TRBF-/handle values are never
  copied or translated here; they are counted and reported.

IDENTIFIERS (ratified contract 2026-09-24)
------------------------------------------
Every component ID is a source-key token from gaming_grove.derive_id that the
candidate runner binds to a registered Cedar object ID: events, land
decisions, environmental reviews, licence issuances and proceedings to
CEDAR-EVENT; clause terms to CEDAR-OBS; compacts and compact versions to
CEDAR-CONTRACT. The BIA-index compact key (CMP-<state>-<slug>-<date>) is
built from a tribe name and a date, so it is NOT an identity: it is kept as
the source ID (`source_record_id`, `also_cited_by`) and the public
`compact_id` / `version_id` / `successor_compact_id` are the bound
CEDAR-CONTRACT IDs. A compact version is a distinct instrument document
(amendment, extension, renewal), so it is a contract object of its own, not
an event: its approval is the separate CEDAR-EVENT in
`regulatory_event_id`. Other source IDs (term_id, decision_id, NIGC ids, FR
document numbers) are preserved verbatim in their own columns.

USAGE
    py -3 code/1202_gaming_grove_compacts_regulatory.py build \
        --input-root "C:\\Users\\esm247\\Desktop\\Cedar Press" \
        --output-root C:\\Users\\esm247\\cedar-grove-gaming-work\\components
"""
from __future__ import annotations

import argparse
import csv
import hashlib

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import gaming_grove as gg  # noqa: E402

LANE = "1202_gaming_grove_compacts_regulatory"
csv.field_size_limit(2 ** 31 - 1)

# The compact corpus carries no per-row fetch date; SOURCE_MANIFEST.md records
# that the local BIA copy was assembled on this date.
COMPACT_CORPUS_ASSEMBLED = "2026-08-05"

PUB, DER, XW = "public_official", "public_derived", "internal_crosswalk"

# ---------------------------------------------------------------- vocabularies
EVENT_TYPES = {
    "compact_fr_notice", "compact_secretarial_decision", "compact_disapproval",
    "bia_gaming_land_decision", "bia_land_decision_subsequent_action",
    "governor_concurrence_action", "bia_land_decision_note",
    "fr_land_acquisition_notice", "fr_gaming_land_notice",
    "nigc_declination_letter", "nigc_notice_of_violation", "nigc_settlement_agreement",
    "nigc_civil_fine_assessment", "nigc_closure_order", "nigc_temporary_closure_order",
    "nigc_enforcement_other", "nigc_enforcement_document_untyped",
    "nigc_management_contract_approval", "nigc_indian_lands_opinion",
    "nigc_game_classification_opinion", "gaming_ordinance_approval",
    "nigc_fr_final_rule", "nigc_fr_proposed_rule", "nigc_fr_notice",
    "gaming_consultation_notice",
}
APPROVAL_STATUSES = {"approved", "deemed_approved", "prescribed", "extended", "in_effect"}
EVENT_STATUSES = APPROVAL_STATUSES | {
    "disapproved", "declination_issued", "issued", "settled", "pending", "proposed",
    "final", "withdrawn", "rescinded", "reversed", "remanded", "reconsidered",
    "denied", "affirmed", "concurred", "nonconcurred", "theory_accepted",
    "theory_not_accepted", "published", "stated", "unknown",
}
LAND_THEORY_CLASSES = {
    "two_part_determination": "25 U.S.C. 2719(b)(1)(A)",
    "settlement_of_land_claim": "25 U.S.C. 2719(b)(1)(B)(i)",
    "initial_reservation": "25 U.S.C. 2719(b)(1)(B)(ii)",
    "restored_lands": "25 U.S.C. 2719(b)(1)(B)(iii)",
    "within_or_contiguous_reservation": "25 U.S.C. 2719(a)(1)",
    "oklahoma_former_reservation": "25 U.S.C. 2719(a)(2)(A)",
    "last_recognized_reservation": "25 U.S.C. 2719(a)(2)(B)",
    "jurisdiction_or_governmental_power": "",
    "indian_lands_status_question": "",
    "after_acquired_or_pre_igra": "",
    "other": "",
    "unknown": "",
}
ENV_ROLES = {"record_of_decision", "fonsi", "environmental_impact_statement",
             "environmental_assessment", "notice_of_availability", "notice_of_intent",
             "scoping_report", "comment_period_extension", "other_nepa_document"}
TERM_CLASSES = {"rate", "base_definition", "cap", "fixed_amount_term", "authorization",
                "date", "confidentiality", "exclusivity", "dispute_resolution", "other"}
VALUE_SEMANTICS = {"contractual_rate", "contractual_rate_schedule", "contractual_base_definition",
                   "contractual_cap", "contractual_fixed_amount_term", "authorization_flag",
                   "contractual_date", "clause_text"}
LICENSE_FAMILIES = {"vendor_license_mention", "wagering_authorization", "machine_allocation"}
LICENSE_STATUSES = {"regulator_named_license_unconfirmed", "vendor_authorized_by_regulator",
                    "authorized_operation_not_observed", "operating_observed",
                    "ceased_as_platform_provider", "authorized_maximum_open_interval",
                    "authorized_maximum_superseded", "unknown"}
LITIGATION_KINDS = {"federal_court_case", "supreme_court_docket", "administrative_appeal",
                    "nigc_commission_proceeding"}
LITIGATION_SUBJECTS = {"compact", "land_gaming_eligibility", "land_into_trust",
                       "regulation_enforcement", "financing_debt", "management_contract",
                       "administrative_appeal_unclassified"}

GAMING_KW = re.compile(r"\b(gaming|igra|class iii|casino|management contract|bingo)\b", re.I)


# ---------------------------------------------------------------- helpers
def _date(value: str):
    """(iso, precision) for YYYY-MM-DD / YYYY-MM / YYYY; else ('', 'unknown')."""
    v = (value or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        return v, "day"
    if re.fullmatch(r"\d{4}-\d{2}", v):
        return v, "month"
    if re.fullmatch(r"\d{4}", v):
        return v, "year"
    return "", "unknown"


_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def _us_date(text: str):
    """First 'Mon DD YYYY' / 'Month D, YYYY' / 'MM/DD/YYYY' in text -> ISO day."""
    t = text or ""
    m = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", t)
    if m:
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    m = re.search(r"\b([A-Z][a-z]{2})[a-z]*\.? (\d{1,2}),? (\d{4})\b", t)
    if m and m.group(1).lower() in _MONTHS:
        return f"{m.group(3)}-{_MONTHS[m.group(1).lower()]:02d}-{int(m.group(2)):02d}"
    return ""


def _fr_docnum(text: str) -> str:
    t = (text or "").strip()
    m = re.search(r"federalregister\.gov/documents/\d{4}/\d{2}/\d{2}/([0-9A-Za-z-]+)/", t)
    if m:
        return m.group(1)
    m = re.search(r"FR Doc\.?\s*([0-9]{2,4}-[0-9]+)", t)
    if m:
        return m.group(1)
    return ""


def _fr_date(url: str) -> str:
    m = re.search(r"federalregister\.gov/documents/(\d{4})/(\d{2})/(\d{2})/", url or "")
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ""


def _uid(value: str) -> str:
    v = (value or "").strip()
    return v if gg.is_ce_uid(v) else ""


def _join(values) -> str:
    return "|".join(sorted({v for v in values if v}))


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Ctx:
    """Per-build state: inputs, counters, legacy-ID observations."""

    def __init__(self, inputs: gg.Inputs):
        self.inputs = inputs
        self.withheld = Counter()
        self.notes: list[str] = []
        self.legacy = Counter()   # (input, column, prefix) -> count

    def clean(self, name, required=True):
        header, rows = self.inputs.clean(name, required)
        self._scan_legacy("data/clean/" + name, header, rows)
        return rows

    def raw_csv(self, rel, required=False):
        header, rows = self.inputs.read(rel, required)
        self._scan_legacy(rel, header, rows)
        return rows

    def raw_json(self, rel):
        p = self.inputs.path(rel)
        if not p.is_file():
            self.inputs.receipts[rel] = {"path": rel, "status": "ABSENT"}
            return None
        raw = p.read_bytes()
        self.inputs.receipts[rel] = {"path": rel, "sha256": _sha(raw), "bytes": len(raw),
                                     "status": "READ"}
        return json.loads(raw.decode("utf-8-sig"))

    def stream_filtered(self, name, keep, required=False):
        """Stream a large clean CSV (federal_actions is ~250 MB): hash every
        byte for the receipt, keep only rows `keep(row)` accepts."""
        rel = "data/clean/" + name
        p = self.inputs.path(rel)
        if not p.is_file():
            if required:
                raise SystemExit(f"REFUSED: missing required input {rel}")
            self.inputs.receipts[rel] = {"path": rel, "status": "ABSENT"}
            return []
        h = hashlib.sha256()
        size = 0
        with p.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
                size += len(chunk)
        kept, n = [], 0
        with p.open("r", encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                n += 1
                if keep(row):
                    kept.append(row)
        self.inputs.receipts[rel] = {"path": rel, "sha256": h.hexdigest(), "bytes": size,
                                     "status": "READ_STREAMED_FILTERED", "rows": n,
                                     "rows_kept": len(kept)}
        return kept

    _ID_COLS = ("cedar_uid", "tribe_id", "entity_id", "tribe_entity_id", "operator_entity_id",
                "designee_entity_id", "vendor_native_entity_id", "resolved_native_entity_id",
                "object_entity_id", "subject_entity_id", "obligor_cedar_handle",
                "additional_entity_ids", "from_tribe_id", "to_tribe_id")

    def _scan_legacy(self, rel, header, rows):
        for col in [c for c in header if c in self._ID_COLS or c.endswith("_cedar_uid")]:
            for r in rows:
                for v in (r.get(col) or "").split("|"):
                    v = v.strip()
                    if v and not gg.is_ce_uid(v):
                        m = re.match(r"^([A-Za-z]+-?)", v)
                        self.legacy[(rel, col, m.group(1) if m else v[:6])] += 1


# ---------------------------------------------------------------- event bag
class EventBag:
    """Regulatory events keyed on a stable source key. A second source that
    carries the same key (e.g. the same FR document number) MERGES into the
    first row: blank fields are filled, list fields are unioned, and the
    second source's own ID is appended to `also_cited_by`. Nothing is dropped
    and the first-added (highest-precedence) event_type/status stands."""

    LIST_FIELDS = ("subject_cedar_uids", "compact_id", "version_id", "decision_id")

    def __init__(self):
        self.rows: dict[tuple, dict] = {}
        self.cites: dict[tuple, set] = defaultdict(set)
        self.lists: dict[tuple, dict] = defaultdict(lambda: defaultdict(set))
        self.merges = 0

    def add(self, key: tuple, row: dict, cite: str):
        lists = {f: set(filter(None, (row.pop(f, "") or "").split("|"))) for f in self.LIST_FIELDS}
        if key in self.rows:
            self.merges += 1
            cur = self.rows[key]
            for k, v in row.items():
                if v and not cur.get(k):
                    cur[k] = v
        else:
            row = dict(row)
            row["regulatory_event_id"] = gg.derive_id("GREG", *key)
            self.rows[key] = row
        self.cites[key].add(cite)
        for f, vals in lists.items():
            self.lists[key][f] |= vals

    def finalize(self) -> list[dict]:
        out = []
        for key, row in self.rows.items():
            for f in self.LIST_FIELDS:
                row[f] = _join(self.lists[key][f])
            uids = sorted(self.lists[key]["subject_cedar_uids"])
            row["cedar_uid"] = uids[0] if len(uids) == 1 else ""
            cites = sorted(self.cites[key])
            row["also_cited_by"] = "|".join(c for c in cites if c != row.get("_primary_cite"))
            row["n_source_records"] = str(len(cites))
            row.pop("_primary_cite", None)
            _guard_event(row)
            out.append(row)
        return out


def _guard_event(row: dict):
    """Refuse the mappings this lane exists to prevent."""
    if row["event_type"] == "nigc_declination_letter" and row["status"] in APPROVAL_STATUSES:
        raise gg.GamingContractError(
            f"REFUSED: declination mapped to approval status {row['status']!r} "
            f"({row.get('source_record_id')})")
    if row["event_type"] not in EVENT_TYPES or row["status"] not in EVENT_STATUSES:
        raise gg.GamingContractError(f"REFUSED: unmapped event {row['event_type']}/{row['status']}")


def _ev(**kw) -> dict:
    base = {c: "" for c in EVENT_COLUMNS}
    base.update(kw)
    iso, prec = _date(base.get("action_date", ""))
    base["action_date"] = iso
    if not base.get("action_date_precision") or not iso:
        base["action_date_precision"] = prec
    base["_primary_cite"] = kw.get("_primary_cite", "")
    return base


# ---------------------------------------------------------------- columns
def _spec(cols):
    """cols: [(name, rights, description)] -> (header, field_rights, field_descriptions)."""
    return ([c[0] for c in cols], {c[0]: c[1] for c in cols}, {c[0]: c[2] for c in cols})


EVIDENCE = [
    ("source_system", PUB, "Publishing system the row was read from (controlled short name)"),
    ("source_record_id", PUB, "The source's own record ID, preserved verbatim"),
    ("source_url", PUB, "Official URL of the source document or index row"),
    ("source_date", PUB, "Date the source states for this record (publication/decision/document)"),
    ("retrieved_date", PUB, "Date Cedar retrieved the source bytes"),
    ("rights_class", DER, "Row-level rights class (gaming_grove.RIGHTS_CLASSES)"),
]

COMPACT_COLS = [
    ("compact_id", DER, "Registered CEDAR-CONTRACT ID (Gaming block) bound to the BIA-index compact key; the key itself (CMP-<state>-<slug>-<yyyymmdd>) is source_record_id"),
    ("instrument_type", PUB, "compact | secretarial-procedures | orphan-no-base-instrument-in-index"),
    ("state", PUB, "State named on the BIA index row"),
    ("tribe_name_as_published", PUB, "Tribe string as printed in the BIA index Tribes column"),
    ("bia_tribes_column_conflict", DER, "1 when BIA's Tribes column disagrees with its Title (known BIA misalignment)"),
    ("cedar_uid", DER, "Native entity (CE-) carried by the source row's existing link; blank if none/legacy"),
    ("cedar_uid_basis", DER, "How the source build linked the entity (method; basis)"),
    ("approval_type", PUB, "secretarial | deemed-approved | secretarial-procedures | unknown (BIA Decision column)"),
    ("bia_decision", PUB, "BIA index Decision column verbatim"),
    ("bia_decision_date", PUB, "BIA index Date column"),
    ("original_effective_date", PUB, "Effective date of the base instrument per the source build"),
    ("original_effective_date_basis", PUB, "Which source field supplied original_effective_date"),
    ("fr_document_number", PUB, "Federal Register document number of the approval/taking-effect notice"),
    ("fr_notice_url", PUB, "Federal Register notice URL"),
    ("term_end", PUB, "Stated end of term, only when the instrument states one"),
    ("term_end_basis", PUB, "Basis for term_end"),
    ("renewal_provisions", PUB, "Renewal language quoted from the instrument"),
    ("status", DER, "active | renegotiated | expired | unknown (rule-based, see status_basis)"),
    ("status_basis", DER, "Rule that produced status (a later base instrument, not a document saying so)"),
    ("successor_compact_id", DER, "compact_id (CEDAR-CONTRACT) of the next base instrument for the same state+tribe in the BIA index"),
    ("n_versions", DER, "Count of versions in gaming_compact_versions for this compact"),
    ("source_pdf", PUB, "BIA PDF filename"),
] + EVIDENCE

VERSION_COLS = [
    ("version_id", DER, "Registered CEDAR-CONTRACT ID (Gaming block) of this version instrument, bound to the compact_versions.csv version key (kept as source_record_id)"),
    ("compact_id", DER, "Parent instrument (CEDAR-CONTRACT compact_id)"),
    ("state", PUB, "State of the parent instrument"),
    ("tribe_name_as_published", PUB, "BIA index Tribes column for this version row"),
    ("cedar_uid", DER, "Inherited from the parent compact's existing CE link"),
    ("version_seq", DER, "Chronological position within the compact (derived)"),
    ("amendment_number", PUB, "Ordinal only when stated in the BIA title"),
    ("version_role", PUB, "original-instrument | amendment | extension"),
    ("bia_title", PUB, "BIA index Title column"),
    ("bia_decision", PUB, "BIA index Decision column verbatim"),
    ("approval_type", PUB, "secretarial | deemed-approved | secretarial-procedures | unknown"),
    ("approval_status", DER, "approved | deemed_approved | prescribed | extended | unknown"),
    ("approval_date", PUB, "Approval date as built (FR publication or BIA index date; see basis)"),
    ("approval_date_basis", PUB, "Which source supplied approval_date"),
    ("effective_date", DER, "FR publication date: a compact takes effect on FR notice (25 U.S.C. 2710(d)(3)(B)); blank without FR"),
    ("effective_date_basis", DER, "Basis for effective_date"),
    ("expiry_date", DER, "Instrument-stated expiration date when exactly one is extracted for this version"),
    ("expiry_date_basis", DER, "term_id(s) the expiry was read from"),
    ("fr_document_number", PUB, "Federal Register document number"),
    ("fr_notice_url", PUB, "Federal Register notice URL"),
    ("doc_kind", PUB, "instrument_text | stub | letter_or_short_doc | ... (text layer of the PDF)"),
    ("regulatory_event_id", DER, "The gaming_regulatory_events row for this version's approval"),
] + EVIDENCE

TERM_COLS = [
    ("gaming_term_id", DER, "Registered CEDAR-OBS ID (Gaming block) for the clause-observation, bound to the source table + source key"),
    ("term_id", PUB, "compact_structured_terms term_id, preserved; blank for compact_terms view rows"),
    ("term_source_table", PUB, "compact_structured_terms | compact_terms"),
    ("compact_id", DER, "Instrument the clause is in (CEDAR-CONTRACT compact_id)"),
    ("version_id", DER, "Version the clause is in (CEDAR-CONTRACT version_id)"),
    ("cedar_uid", DER, "Existing CE link carried by the source row"),
    ("state", PUB, "State"),
    ("term_field", PUB, "Clause family as extracted (revenue_sharing_rate, exclusivity, ...)"),
    ("term_class", DER, "rate | base_definition | cap | fixed_amount_term | authorization | date | ..."),
    ("value_semantics", DER, "What the value IS: a contractual rate/cap/term, never a payment or revenue"),
    ("value_text", PUB, "Extracted value as text"),
    ("value_numeric", PUB, "Numeric value when the clause states one (a rate, a cap, a per-device fee)"),
    ("unit", PUB, "Unit of value_numeric (percent, devices, usd_per_device, ...)"),
    ("applies_to", PUB, "Scope stated for the clause"),
    ("revenue_concept", PUB, "Base the rate applies to, verbatim (net win, adjusted gross revenue, ...)"),
    ("base_scope", PUB, "tribe | facility | ... as extracted"),
    ("formula_invertibility", PUB, "Whether a payment could be inverted through this clause (source build)"),
    ("measurement_type", PUB, "AUTHORIZED_MAXIMUM etc. when the clause is a ceiling"),
    ("is_payment_observation", DER, "Always 'no': a clause is not a payment"),
    ("effective_from", PUB, "Clause effective start as built"),
    ("effective_from_basis", PUB, "Basis for effective_from"),
    ("effective_to", PUB, "Clause effective end as built"),
    ("effective_to_basis", PUB, "Basis for effective_to"),
    ("is_instrument_language", PUB, "yes when the quote is instrument text, not a cover letter"),
    ("doc_zone", PUB, "Document zone the quote came from"),
    ("confidence_tier", PUB, "Source build tier"),
    ("source_page", PUB, "PDF page of the quote"),
    ("source_quote", PUB, "Verbatim quote supporting the value"),
    ("extraction_method", PUB, "Extraction method recorded by the source build"),
] + EVIDENCE

EVENT_COLUMNS_SPEC = [
    ("regulatory_event_id", DER, "Registered CEDAR-EVENT ID (Gaming block) for the event, bound to the stable source key (FR doc number, NIGC id, BIA event id)"),
    ("event_type", DER, "Controlled vocabulary of regulatory action types"),
    ("event_subtype", PUB, "Source-specific subtype (NOV code, ordinance type, version role, FR action line)"),
    ("agency", PUB, "Acting agency (BIA/AS-IA, NIGC, NIGC OGC, Governor, Federal Register agency)"),
    ("action_date", PUB, "Date of the regulatory action as the source states it; NOT a facility opening"),
    ("action_date_precision", DER, "day | month | year | unknown"),
    ("action_date_basis", PUB, "Which field/rule supplied action_date"),
    ("posted_date", PUB, "Website posting / index date when distinct from the action date"),
    ("status", DER, "approved, deemed_approved, declination_issued, disapproved, rescinded, pending, ..."),
    ("status_basis", PUB, "Source field or phrase that set status"),
    ("cedar_uid", DER, "Single subject Native entity when exactly one CE link exists"),
    ("subject_cedar_uids", DER, "All CE links attached by the source rows (pipe-joined)"),
    ("subject_link_basis", DER, "How the subject links were made by the source builds"),
    ("subject_name_as_published", PUB, "Subject tribe/party/game as printed by the source"),
    ("state", PUB, "State when the source names one"),
    ("gaming_facility_id", XW, "Facility (via gaming_grove.facility_id_for) only when the source carries a place id; else blank"),
    ("compact_id", DER, "Linked compact(s) (pipe-joined CEDAR-CONTRACT compact_id values) when the source links one"),
    ("version_id", DER, "Linked compact version(s) (pipe-joined CEDAR-CONTRACT version_id values)"),
    ("decision_id", PUB, "Linked BIA gaming land decision(s)"),
    ("fr_document_number", PUB, "Federal Register document number (citation); raw key for cross-lane links"),
    ("docket_ids", PUB, "Agency / regulations.gov docket IDs printed on the FR document (pipe-joined)"),
    ("title_or_description", PUB, "Title / RE line / description from the source"),
    ("source_system", PUB, "Primary source system for the event key"),
    ("source_record_id", PUB, "Primary source record ID"),
    ("also_cited_by", PUB, "Every other <table>:<id> that carries the same event key (dedupe preserves them)"),
    ("n_source_records", DER, "Number of source records merged into this event"),
    ("source_url", PUB, "Official URL"),
    ("source_date", PUB, "Source's own date for the record"),
    ("retrieved_date", PUB, "Retrieval date"),
    ("rights_class", DER, "Row-level rights class"),
    ("evidence_note", PUB, "Caveat carried from the source build (what this event does not establish)"),
]
EVENT_COLUMNS = [c[0] for c in EVENT_COLUMNS_SPEC]

LAND_COLS = [
    ("land_eligibility_id", DER, "Registered CEDAR-EVENT ID (Gaming block) for the determination, bound to the key (LAND-ELIGIBILITY, source system, decision/opinion id)"),
    ("determination_kind", DER, "bia_gaming_land_decision | nigc_indian_lands_opinion"),
    ("determination_body", PUB, "Interior (BIA/AS-IA) or NIGC Office of General Counsel"),
    ("decision_id", PUB, "Source decision/opinion ID, preserved"),
    ("legal_theory_as_published", PUB, "Legal theory verbatim from the index"),
    ("legal_theory_class", DER, "Normalized IGRA section 20 theory class"),
    ("igra_provision", DER, "25 U.S.C. 2719 provision the theory class corresponds to (Cedar mapping)"),
    ("current_status", DER, "approved | disapproved | pending | theory_accepted | theory_not_accepted | unknown"),
    ("current_status_basis", PUB, "Source column for current_status (index shows current state only)"),
    ("decision_date", PUB, "Date of the determination per the index; NOT an opening or operating date"),
    ("decision_date_precision", DER, "day | month | year | unknown"),
    ("decision_date_basis", PUB, "Basis for decision_date"),
    ("latest_subsequent_action", DER, "Latest dated later action on this decision (rescinded, reversed, ...)"),
    ("latest_subsequent_action_date", PUB, "Date of latest_subsequent_action"),
    ("regulatory_event_ids", DER, "gaming_regulatory_events rows for this decision (pipe-joined)"),
    ("cedar_uid", DER, "Existing CE link of the decision's tribe"),
    ("subject_name_as_published", PUB, "Tribe as printed"),
    ("state", PUB, "State"),
    ("parcel_as_published", PUB, "Parcel description (NIGC opinions)"),
    ("fr_document_number", PUB, "FR notice linked from the BIA index row"),
    ("fr_publication_date", PUB, "FR publication date of that notice"),
    ("project_key", PUB, "NEPA pilot project key when one exists (distinct from any facility id)"),
] + EVIDENCE

ENV_COLS = [
    ("environmental_review_id", DER, "Registered CEDAR-EVENT ID (Gaming block) for the review-document, bound to the document URL or source key"),
    ("project_key", PUB, "Project key (NEPA pilot project_id, else the BIA decision_id); never a facility id"),
    ("project_key_basis", DER, "Which identifier project_key is"),
    ("review_level", DER, "EIS | EA | CATEX | unknown"),
    ("document_role", DER, "record_of_decision | fonsi | environmental_impact_statement | ..."),
    ("lead_agency", PUB, "BIA or NIGC"),
    ("document_title", PUB, "Document label as published"),
    ("document_date", PUB, "Date printed in the document label, if any"),
    ("document_date_precision", DER, "day | month | year | unknown"),
    ("document_date_basis", DER, "How document_date was read"),
    ("related_decision_id", PUB, "BIA gaming land decision the document is posted under"),
    ("related_decision_date", PUB, "That decision's index date (context; not the document's date)"),
    ("related_decision_status", PUB, "That decision's current index status"),
    ("cedar_uid", DER, "Existing CE link of the decision's tribe"),
    ("subject_name_as_published", PUB, "Tribe/project as printed"),
    ("state", PUB, "State"),
    ("applicant_projection_rows", DER, "Count of applicant-scenario PROJECTION rows for this project (gaming_projections); never outcomes"),
    ("mitigation_agreement_rows", DER, "Count of mitigation-agreement lines for this project"),
    ("facility_scenario_rows", DER, "Count of proposed-alternative facility rows (proposed, not built)"),
    ("local_sha256", PUB, "SHA-256 of the local copy when a manifest records one"),
    ("also_cited_by", PUB, "Other source records carrying the same document"),
] + EVIDENCE

LIC_COLS = [
    ("license_id", DER, "Registered CEDAR-EVENT ID (Gaming block) for the licence/authorisation, bound to the source key"),
    ("license_family", DER, "vendor_license_mention | wagering_authorization | machine_allocation"),
    ("authority_name", PUB, "Licensing authority as named (tribal regulator, state host, compact appendix)"),
    ("authority_level", DER, "tribal | state | tribal_state_compact"),
    ("authority_cedar_uid", DER, "CE link of the tribe whose regulator is named (existing link)"),
    ("holder_name_as_published", PUB, "Licensee/operator/allocation holder as printed"),
    ("holder_cedar_uid", DER, "CE link of the holder when it is a Native entity (existing link)"),
    ("holder_sec_cik", PUB, "SEC CIK of a vendor registrant"),
    ("gaming_facility_id", XW, "Facility only when the source carries a place id (none currently do)"),
    ("state", PUB, "State"),
    ("product_type", PUB, "ONLINE_CASINO, RETAIL_SPORTSBOOK, class III machines, ..."),
    ("license_type_as_published", PUB, "Licence type / statute text as printed"),
    ("license_number", PUB, "Licence number when printed"),
    ("status", DER, "Controlled licence status (see contract)"),
    ("status_basis", PUB, "Source basis for status"),
    ("effective_start", PUB, "Authorisation start when stated"),
    ("effective_end", PUB, "Authorisation end when stated"),
    ("operation_start_date", PUB, "Observed launch/operation date (digital) - distinct from authorisation"),
    ("cessation_date", PUB, "Observed cessation date"),
    ("authorized_quantity", PUB, "Authorised maximum (machine allocations); a ceiling, not a count in use"),
    ("quantity_unit", PUB, "Unit of authorized_quantity"),
    ("measurement_type", PUB, "AUTHORIZED_MAXIMUM etc."),
    ("compact_citation", PUB, "Compact/appendix citation for the authority"),
    ("evidence_quote", PUB, "Verbatim quote from the source"),
] + EVIDENCE

LIT_COLS = [
    ("litigation_id", DER, "Registered CEDAR-EVENT ID (Gaming block) for the proceeding, bound to forum + docket/citation"),
    ("proceeding_kind", DER, "federal_court_case | supreme_court_docket | administrative_appeal | nigc_commission_proceeding"),
    ("case_name", PUB, "Caption as published (blank when the source does not name the case)"),
    ("forum", PUB, "Court or tribunal"),
    ("docket_number", PUB, "Docket / case number when published"),
    ("reporter_citation", PUB, "Reporter citation when published"),
    ("filing_date", PUB, "Filing / docketing date"),
    ("filing_date_precision", DER, "day | month | year | unknown"),
    ("decision_date", PUB, "Decision / order date"),
    ("decision_date_precision", DER, "day | month | year | unknown"),
    ("date_basis", PUB, "Where the dates came from"),
    ("subject_area", DER, "compact | land_gaming_eligibility | land_into_trust | regulation_enforcement | financing_debt | ..."),
    ("related_decision_id", PUB, "BIA gaming land decision(s) the proceeding affected (pipe-joined)"),
    ("affected_subject_cedar_uid", DER, "CE link of the subject of the affected decision (existing link; not necessarily a party)"),
    ("party_cedar_uids", DER, "CE links of parties, only where the source build linked a party"),
    ("party_link_basis", DER, "How party links were made"),
    ("parties_as_published", PUB, "Parties as printed"),
    ("outcome_as_stated", PUB, "Outcome text as stated by the source; blank when not extracted"),
    ("outcome_basis", PUB, "Where outcome_as_stated came from"),
    ("also_cited_by", PUB, "Other source records (incl. Advocacy collection links) for the same proceeding"),
    ("local_file", PUB, "Local copy path under the Cedar data root"),
] + EVIDENCE


def _contract(grain, pk, cols, status, supersedes, nonadd, enums=None, dates=(), intervals=(),
              derived=None, public_ids=(), required=None, id_recipe=""):
    header, rights, desc = _spec(cols)
    return {
        "grain": grain, "primary_key": pk, "required": required or list(pk),
        "enums": enums or {}, "dates": list(dates), "intervals": list(intervals),
        "public_id_columns": list(public_ids), "derived_ids": derived or {},
        "field_rights": rights, "field_descriptions": desc, "nonadditive_note": nonadd,
        "publication_status": status, "supersedes": supersedes,
        "row_rights_column": "rights_class", "_header": header, "id_recipe": id_recipe,
    }


CONTRACTS = {
    "gaming_compacts.csv": _contract(
        "one row per tribal-state Class III compact base instrument (or secretarial procedures) in the BIA index",
        ["compact_id"], COMPACT_COLS, "public",
        [{"table": "compacts", "role": "source (1:1, columns renamed, legacy tribe_id/entity_id dropped)"}],
        "An instrument is not a payment, a facility or a licence. n_versions counts versions; never sum instruments across states as 'compacts in force'.",
        enums={"approval_type": {"secretarial", "deemed-approved", "secretarial-procedures", "unknown"}},
        dates=["bia_decision_date", "original_effective_date", "term_end", "source_date", "retrieved_date"],
        derived={"compact_id": "GCMP", "successor_compact_id": "GCMP"},
        public_ids=["compact_id", "cedar_uid"],
        id_recipe='compact_id = derive_id("GCMP", BIA-index compact key); successor_compact_id likewise; the key is source_record_id'),
    "gaming_compact_versions.csv": _contract(
        "one row per compact version (original instrument, amendment or extension) as indexed by BIA",
        ["version_id"], VERSION_COLS, "public",
        [{"table": "compact_versions", "role": "source (1:1)"},
         {"table": "compact_structured_terms", "role": "expiration_date terms feed expiry_date"}],
        "Versions are successive states of one instrument: never count versions as instruments.",
        enums={"approval_status": {"approved", "deemed_approved", "prescribed", "extended", "unknown"}},
        dates=["approval_date", "effective_date", "expiry_date", "source_date", "retrieved_date"],
        derived={"regulatory_event_id": "GREG", "version_id": "GCMV", "compact_id": "GCMP"},
        public_ids=["version_id", "compact_id", "cedar_uid"],
        id_recipe='version_id = derive_id("GCMV", compact_versions version key); compact_id = derive_id("GCMP", compact key); regulatory_event_id per gaming_regulatory_events recipe'),
    "gaming_compact_terms.csv": _contract(
        "one row per extracted contractual clause term (structured terms plus exclusivity/dispute clauses from the compact_terms view)",
        ["gaming_term_id"], TERM_COLS, "internal",
        [{"table": "compact_structured_terms", "role": "source (1:1)"},
         {"table": "compact_terms", "role": "derived view; only exclusivity and dispute_provision rows added (other types duplicate structured terms)"}],
        "A rate, base, cap or per-device fee is a CONTRACT TERM. It is never a payment, revenue or an amount paid; never multiply a rate by a revenue estimate and publish it as a payment.",
        enums={"term_class": TERM_CLASSES, "value_semantics": VALUE_SEMANTICS,
               "is_payment_observation": {"no"},
               "term_source_table": {"compact_structured_terms", "compact_terms"}},
        dates=["effective_from", "effective_to", "source_date", "retrieved_date"],
        derived={"gaming_term_id": "GSRC", "compact_id": "GCMP", "version_id": "GCMV"},
        public_ids=["compact_id", "version_id", "cedar_uid"],
        id_recipe='gaming_term_id = derive_id("GSRC", "compact_structured_terms", term_id) | derive_id("GSRC", "compact_terms", version_id, term_type, source_page, sha256(quote)[:16])'),
    "gaming_regulatory_events.csv": _contract(
        "one row per dated regulatory action, deduplicated on its stable source key (FR document number, NIGC record id, BIA event id); merged source IDs kept in also_cited_by",
        ["regulatory_event_id"], EVENT_COLUMNS_SPEC, "public",
        [{"table": t, "role": "event source"} for t in (
            "compacts", "compact_versions", "compact_events", "gaming_land_decisions",
            "gaming_decision_events", "nigc_declination_letters", "nigc_enforcement_actions",
            "nigc_action_parties", "nigc_management_contract_approvals", "nigc_indian_lands_opinions",
            "nigc_game_classification_opinions", "gaming_ordinances", "federal_actions",
            "federal_actions_entity_bridge", "consultation_events", "gaming_financing_events")],
        "Events are actions, not states: never count events as facilities, tribes or compacts in force. A declination is not an approval; a decision date is not an opening date.",
        enums={"event_type": EVENT_TYPES, "status": EVENT_STATUSES,
               "action_date_precision": gg.DATE_PRECISIONS},
        dates=["action_date", "posted_date", "source_date", "retrieved_date"],
        derived={"regulatory_event_id": "GREG"},
        public_ids=["regulatory_event_id", "cedar_uid", "gaming_facility_id"],
        id_recipe='regulatory_event_id = derive_id("GREG", *key) with key = ("FR", fr_document_number) for every FR-published event (compact notices, land notices, NIGC FR, consultations with an FR number); ("BIA-OIG-COMPACT-INDEX", version_id); ("BIA-OIG-COMPACT-EVENT", compact_events.event_id); ("BIA-GLD-EVENT", gaming_decision_events.event_id); ("NIGC-DL", cedar_opinion_id); ("NIGC-EA", action_id); ("NIGC-MC", action_id); ("NIGC-IL", opinion_id); ("NIGC-GC", opinion_id); ("NIGC-ORD", ordinance_id); ("CONS", consultation_event_id)'),
    "gaming_land_eligibility.csv": _contract(
        "one row per BIA gaming land decision or NIGC Indian-lands opinion (determination), with its current index status and latest later action",
        ["land_eligibility_id"], LAND_COLS, "public",
        [{"table": "gaming_land_decisions", "role": "source (1:1)"},
         {"table": "nigc_indian_lands_opinions", "role": "source (1:1)"},
         {"table": "gaming_decision_events", "role": "latest subsequent action"}],
        "A determination makes land eligible (or not) for gaming. It is not a facility, a trust acquisition closing or an opening; never count determinations as casinos.",
        enums={"legal_theory_class": set(LAND_THEORY_CLASSES),
               "determination_kind": {"bia_gaming_land_decision", "nigc_indian_lands_opinion"},
               "current_status": {"approved", "disapproved", "pending", "theory_accepted",
                                  "theory_not_accepted", "unknown"}},
        dates=["decision_date", "latest_subsequent_action_date", "fr_publication_date",
               "source_date", "retrieved_date"],
        derived={"land_eligibility_id": "GREG"}, public_ids=["land_eligibility_id", "cedar_uid"],
        id_recipe='land_eligibility_id = derive_id("GREG", "LAND-ELIGIBILITY", source_system, decision_id|opinion_id)'),
    "gaming_environmental_reviews.csv": _contract(
        "one row per NEPA review document per project (EA, EIS, FONSI, ROD, NOA, NOI, scoping), deduplicated on document URL",
        ["environmental_review_id"], ENV_COLS, "source_limited",
        [{"table": "gaming_land_decisions", "role": "document lists"},
         {"table": "raw/external/gaming_nepa/_SOURCE_MANIFEST.csv", "role": "pilot documents"},
         {"table": "nigc_document_surface", "role": "NIGC past FONSIs"},
         {"table": "gaming_projections / gaming_project_facilities / gaming_mitigation_agreements", "role": "counts only"},
         {"table": "nepa_eplanning_projects", "role": "checked; no gaming projects (BLM register)"}],
        "Applicant projections are scenarios, never outcomes; counts of projection rows are not values. Documents of one project are stages of one review, not separate projects.",
        enums={"document_role": ENV_ROLES, "review_level": {"EIS", "EA", "CATEX", "unknown"}},
        dates=["document_date", "related_decision_date", "source_date", "retrieved_date"],
        derived={"environmental_review_id": "GENV"}, public_ids=["environmental_review_id", "cedar_uid"],
        id_recipe='environmental_review_id = derive_id("GENV", "document_url", url or NIGC membership_id)'),
    "gaming_licenses.csv": _contract(
        "one row per licence mention, wagering authorisation or machine-allocation interval as published by its source",
        ["license_id"], LIC_COLS, "source_limited",
        [{"table": "gaming_vendor_tribal_licenses", "role": "SEC-filing licence mentions (self-references excluded)"},
         {"table": "digital_gaming_relationships", "role": "state wagering authorisations/operations"},
         {"table": "wa_machine_allocations", "role": "compact machine allocations"},
         {"table": "wa_machine_transfers", "role": "empty in source"}],
        "An allocation is an AUTHORIZED_MAXIMUM, not machines in use; a regulator named in a filing is not a confirmed licence; never sum allocations across overlapping intervals.",
        enums={"license_family": LICENSE_FAMILIES, "status": LICENSE_STATUSES,
               "authority_level": {"tribal", "state", "tribal_state_compact"}},
        dates=["effective_start", "effective_end", "operation_start_date", "cessation_date",
               "source_date", "retrieved_date"],
        intervals=[("effective_start", "effective_end")],
        derived={"license_id": "GLIC"},
        public_ids=["license_id", "gaming_facility_id"],
        id_recipe='license_id = derive_id("GLIC", "SEC-EDGAR-VENDOR", cik, source_url, regulator, license_type, license_number) | ("GLIC", "DIGITAL", digital_gaming_id) | ("GLIC", "WA-ALLOC", allocation_id)'),
    "gaming_litigation.csv": _contract(
        "one row per court or administrative proceeding (forum + docket or reporter citation) affecting gaming compacts, land, regulation or financing",
        ["litigation_id"], LIT_COLS, "source_limited",
        [{"table": "native_issue_litigation_positions", "role": "Advocacy collection: LINKED by position_id, rows not copied"},
         {"table": "native_issue_litigation_coverage", "role": "forum coverage"},
         {"table": "gaming_land_decisions / gaming_decision_events", "role": "BIA notes citing cases"},
         {"table": "admin_appeal_decisions", "role": "IBIA gaming captions"},
         {"table": "nigc_document_surface", "role": "NIGC commission final decisions"},
         {"table": "raw/external/fl_gaming/_SOURCE_MANIFEST.csv", "role": "USCOURTS opinions"},
         {"table": "staging/tribal_debt_court_dockets", "role": "CourtListener dockets (staging, not promoted)"}],
        "A proceeding is not an outcome; amounts in court records are what that document states and are never summed with payments or revenue.",
        enums={"proceeding_kind": LITIGATION_KINDS, "subject_area": LITIGATION_SUBJECTS},
        dates=["filing_date", "decision_date", "source_date", "retrieved_date"],
        derived={"litigation_id": "GLIT"}, public_ids=["litigation_id"],
        id_recipe='litigation_id = derive_id("GLIT", *key) with key = ("REPORTER", citation) | ("DOCKET", court, docket_number) | ("USCOURTS", court_code, docket) | ("IBIA", citation) | ("NIGC-CFD", document_slug) | ("BIA-NOTE-UNNAMED", decision_id, court, date)'),
}


# ---------------------------------------------------------------- builders
def build_compacts(ctx: Ctx, bag: EventBag):
    compacts = ctx.clean("compacts.csv")
    versions = ctx.clean("compact_versions.csv")
    sterms = ctx.clean("compact_structured_terms.csv")
    cevents = ctx.clean("compact_events.csv", required=False)

    cmp_by_id = {r["compact_id"]: r for r in compacts}
    nver = Counter(v["compact_id"] for v in versions)
    out_c = []
    for r in compacts:
        uid = _uid(r.get("cedar_uid"))
        if r.get("cedar_uid") and not uid:
            ctx.withheld["compacts.cedar_uid_legacy_or_malformed"] += 1
        out_c.append({
            "compact_id": r["compact_id"], "instrument_type": r.get("instrument_type", ""),
            "state": r.get("state", ""), "tribe_name_as_published": r.get("tribe", ""),
            "bia_tribes_column_conflict": r.get("bia_tribes_column_conflict", ""),
            "cedar_uid": uid,
            "cedar_uid_basis": "; ".join(x for x in (r.get("entity_match_method", ""),
                                                   r.get("entity_match_basis", "")) if x) if uid else "",
            "approval_type": r.get("approval_type", "") or "unknown",
            "bia_decision": r.get("bia_decision", ""),
            "bia_decision_date": _date(r.get("bia_decision_date"))[0],
            "original_effective_date": _date(r.get("original_effective_date"))[0],
            "original_effective_date_basis": r.get("original_effective_date_basis", ""),
            "fr_document_number": _fr_docnum(r.get("FR_citation")) or _fr_docnum(r.get("FR_notice_url")),
            "fr_notice_url": r.get("FR_notice_url", ""),
            "term_end": _date(r.get("term_end"))[0], "term_end_basis": r.get("term_end_basis", ""),
            "renewal_provisions": r.get("renewal_provisions", ""),
            "status": r.get("status", ""), "status_basis": r.get("status_basis", ""),
            "successor_compact_id": r.get("successor_compact_id", ""),
            "n_versions": str(nver.get(r["compact_id"], 0)),
            "source_pdf": r.get("source_pdf", ""),
            "source_system": "bia_oig_compact_index", "source_record_id": r["compact_id"],
            "source_url": r.get("source_url", ""),
            "source_date": _date(r.get("bia_decision_date"))[0],
            "retrieved_date": COMPACT_CORPUS_ASSEMBLED, "rights_class": PUB,
        })

    # expiry per version: only when exactly one instrument-stated date exists
    exp = defaultdict(set)
    exp_ids = defaultdict(set)
    for t in sterms:
        if t.get("term_field") == "expiration_date":
            iso, _ = _date(t.get("value"))
            if iso:
                exp[t["version_id"]].add(iso)
                exp_ids[t["version_id"]].add(t["term_id"])

    out_v = []
    status_map = {"secretarial": "approved", "deemed-approved": "deemed_approved",
                  "secretarial-procedures": "prescribed"}
    for v in versions:
        parent = cmp_by_id.get(v["compact_id"], {})
        uid = _uid(parent.get("cedar_uid"))
        docnum = _fr_docnum(v.get("FR_citation")) or _fr_docnum(v.get("FR_notice_url"))
        frd = _fr_date(v.get("FR_notice_url"))
        role = v.get("version_role", "")
        astat = status_map.get(v.get("approval_type", ""),
                               "extended" if v.get("bia_decision") == "Extensions" else "unknown")
        ev_status = astat if astat != "unknown" else "published"
        if docnum:
            key = ("FR", docnum)
            bag.add(key, _ev(
                event_type="compact_fr_notice", event_subtype=role, agency="Department of the Interior (AS-IA)",
                action_date=frd or v.get("approval_date", ""),
                action_date_basis="Federal Register publication date (compact/amendment takes effect on publication)",
                status=ev_status, status_basis=f"compact_versions.approval_type={v.get('approval_type','')}; bia_decision={v.get('bia_decision','')}",
                subject_cedar_uids=uid, subject_link_basis="compacts.cedar_uid (existing link)" if uid else "",
                subject_name_as_published=v.get("bia_tribes_column", ""), state=parent.get("state", ""),
                compact_id=v["compact_id"], version_id=v["version_id"], fr_document_number=docnum,
                title_or_description=v.get("bia_title", ""), source_system="federal_register",
                source_record_id=docnum, source_url=v.get("FR_notice_url", ""), source_date=frd,
                retrieved_date=COMPACT_CORPUS_ASSEMBLED, rights_class=PUB,
                evidence_note="FR notice date; the Secretary's decision may precede publication",
                _primary_cite=f"federal_register:{docnum}"), f"compact_versions:{v['version_id']}")
            eid = bag.rows[key]["regulatory_event_id"]
        else:
            key = ("BIA-OIG-COMPACT-INDEX", v["version_id"])
            bag.add(key, _ev(
                event_type="compact_secretarial_decision", event_subtype=role,
                agency="Department of the Interior (AS-IA)",
                action_date=v.get("bia_decision_date") or v.get("approval_date", ""),
                action_date_basis="BIA Office of Indian Gaming index Date column",
                status=ev_status, status_basis=f"bia_decision={v.get('bia_decision','')}",
                subject_cedar_uids=uid, subject_link_basis="compacts.cedar_uid (existing link)" if uid else "",
                subject_name_as_published=v.get("bia_tribes_column", ""), state=parent.get("state", ""),
                compact_id=v["compact_id"], version_id=v["version_id"],
                title_or_description=v.get("bia_title", ""), source_system="bia_oig_compact_index",
                source_record_id=v["version_id"], source_url=v.get("source_url", ""),
                source_date=_date(v.get("bia_decision_date"))[0],
                retrieved_date=COMPACT_CORPUS_ASSEMBLED, rights_class=PUB,
                _primary_cite=f"compact_versions:{v['version_id']}"), f"compact_versions:{v['version_id']}")
            eid = bag.rows[key]["regulatory_event_id"]
        e = exp.get(v["version_id"], set())
        out_v.append({
            "version_id": v["version_id"], "compact_id": v["compact_id"],
            "state": parent.get("state", ""), "tribe_name_as_published": v.get("bia_tribes_column", ""),
            "cedar_uid": uid, "version_seq": v.get("version_seq", ""),
            "amendment_number": v.get("amendment_number", ""), "version_role": role,
            "bia_title": v.get("bia_title", ""), "bia_decision": v.get("bia_decision", ""),
            "approval_type": v.get("approval_type", "") or "unknown", "approval_status": astat,
            "approval_date": _date(v.get("approval_date"))[0],
            "approval_date_basis": v.get("approval_date_basis", ""),
            "effective_date": frd, "effective_date_basis": "FR publication date in notice URL" if frd else "",
            "expiry_date": next(iter(e)) if len(e) == 1 else "",
            "expiry_date_basis": _join(exp_ids[v["version_id"]]) if len(e) == 1 else
            ("conflicting instrument dates; withheld" if e else ""),
            "fr_document_number": docnum, "fr_notice_url": v.get("FR_notice_url", ""),
            "doc_kind": v.get("doc_kind", ""), "regulatory_event_id": eid,
            "source_system": "bia_oig_compact_index", "source_record_id": v["version_id"],
            "source_url": v.get("source_url", ""), "source_date": _date(v.get("bia_decision_date"))[0],
            "retrieved_date": COMPACT_CORPUS_ASSEMBLED, "rights_class": PUB,
        })
        if len(e) > 1:
            ctx.withheld["compact_versions.expiry_conflicting_dates"] += 1

    # compacts.csv carries the same FR citation as its first version: merge, keep the id
    for r in compacts:
        d = _fr_docnum(r.get("FR_citation")) or _fr_docnum(r.get("FR_notice_url"))
        if d and ("FR", d) in bag.rows:
            bag.add(("FR", d), _ev(event_type="compact_fr_notice", status="published",
                                   compact_id=r["compact_id"]), f"compacts:{r['compact_id']}")

    for e in cevents:
        uid = _uid(e.get("cedar_uid"))
        bag.add(("BIA-OIG-COMPACT-EVENT", e["event_id"]), _ev(
            event_type="compact_disapproval", event_subtype=e.get("event_type", ""),
            agency="Department of the Interior (AS-IA)", action_date=e.get("event_date", ""),
            action_date_basis="BIA index Date column", status="disapproved",
            status_basis=e.get("basis", ""), subject_cedar_uids=uid,
            subject_link_basis="compact_events.cedar_uid (inherited from compact)" if uid else "",
            subject_name_as_published=e.get("tribe", ""), state=e.get("state", ""),
            compact_id=e.get("compact_id", ""), fr_document_number=_fr_docnum(e.get("FR_citation")),
            title_or_description=e.get("description", ""), source_system="bia_oig_compact_index",
            source_record_id=e["event_id"], source_url=e.get("source_url", ""),
            source_date=_date(e.get("event_date"))[0], retrieved_date=COMPACT_CORPUS_ASSEMBLED,
            rights_class=PUB, _primary_cite=f"compact_events:{e['event_id']}"),
            f"compact_events:{e['event_id']}")

    # ---- terms
    out_t = []
    for t in sterms:
        tc, sem = _term_semantics(t.get("term_field", ""), t.get("unit", ""))
        out_t.append(_term_row(t, "compact_structured_terms", t["term_id"], tc, sem,
                               value=t.get("value", ""), value_numeric=t.get("value_numeric", ""),
                               quote=t.get("source_quote", ""),
                               retrieved=t.get("fetched_date", "")))
    view = ctx.clean("compact_terms.csv", required=False)
    added_types = {"exclusivity": ("exclusivity", "clause_text"),
                   "dispute_provision": ("dispute_resolution", "clause_text")}
    for t in view:
        if t.get("term_type") not in added_types:
            ctx.withheld["compact_terms_view.duplicates_structured_family_not_reemitted"] += 1
            continue
        tc, sem = added_types[t["term_type"]]
        key = (t.get("version_id", ""), t["term_type"], t.get("source_page", ""),
               _sha((t.get("quote") or "").encode("utf-8"))[:16])
        row = _term_row(t, "compact_terms", "", tc, sem, value=t.get("value", ""),
                        value_numeric="", quote=t.get("quote", ""), retrieved="",
                        term_field=t["term_type"], key=key)
        out_t.append(row)
    return out_c, out_v, out_t


def _term_semantics(field: str, unit: str):
    f = field
    if f in ("revenue_sharing_rate",):
        return "rate", "contractual_rate"
    if f == "progressive_rate_schedule":
        return "rate", "contractual_rate_schedule"
    if f == "revenue_sharing_base":
        return "base_definition", "contractual_base_definition"
    if f in ("device_caps", "facility_caps", "table_caps"):
        return "cap", "contractual_cap"
    if f in ("machine_based_payment", "local_payment", "state_payment", "minimum_payment",
             "other_mitigation_payments", "hotel_tax_equivalent"):
        if unit in ("percent", "percent_of_bracket"):
            return "rate", "contractual_rate"
        return "fixed_amount_term", ("contractual_fixed_amount_term"
                                     if unit in ("usd", "usd_per_device") else "clause_text")
    if f in ("class_iii_devices_authorized", "sports_wagering_authorized",
             "internet_wagering_authorized", "gaming_types_authorized", "mobile_wagering_scope"):
        return "authorization", "authorization_flag" if unit == "boolean" else "clause_text"
    if f == "expiration_date":
        return "date", "contractual_date"
    if f == "confidentiality_provision":
        return "confidentiality", "clause_text"
    return "other", "clause_text"


def _term_row(t, table, term_id, tc, sem, value, value_numeric, quote, retrieved,
              term_field=None, key=None):
    uid = _uid(t.get("cedar_uid"))
    src_id = term_id or "|".join(key)
    return {
        "gaming_term_id": gg.derive_id("GSRC", table, *(key or (term_id,))),
        "term_id": term_id, "term_source_table": table,
        "compact_id": t.get("compact_id", ""), "version_id": t.get("version_id", ""),
        "cedar_uid": uid, "state": t.get("state", ""),
        "term_field": term_field or t.get("term_field", ""), "term_class": tc,
        "value_semantics": sem, "value_text": value, "value_numeric": value_numeric,
        "unit": t.get("unit", ""), "applies_to": t.get("applies_to", ""),
        "revenue_concept": " ".join((t.get("revenue_concept") or "").split()),
        "base_scope": t.get("base_scope", ""),
        "formula_invertibility": t.get("formula_invertibility", ""),
        "measurement_type": t.get("measurement_type", ""), "is_payment_observation": "no",
        "effective_from": _date(t.get("effective_from"))[0],
        "effective_from_basis": t.get("effective_from_basis", ""),
        "effective_to": _date(t.get("effective_to"))[0],
        "effective_to_basis": t.get("effective_to_basis", ""),
        "is_instrument_language": t.get("is_instrument_language", ""),
        "doc_zone": t.get("doc_zone", ""), "confidence_tier": t.get("confidence_tier", ""),
        "source_page": t.get("source_page", ""), "source_quote": quote,
        "extraction_method": t.get("extraction_method", ""),
        "source_system": "bia_oig_compact_pdf", "source_record_id": src_id,
        "source_url": t.get("source_url", ""), "source_date": "",
        "retrieved_date": _date(retrieved)[0] or COMPACT_CORPUS_ASSEMBLED, "rights_class": PUB,
    }


LAND_EVENT_MAP = {
    "decision_approved": ("bia_gaming_land_decision", "approved"),
    "decision_disapproved": ("bia_gaming_land_decision", "disapproved"),
    "decision_pending": ("bia_gaming_land_decision", "pending"),
    "remand_stated_in_note": ("bia_land_decision_subsequent_action", "remanded"),
    "approval_stated_in_note": ("bia_land_decision_subsequent_action", "approved"),
    "reconsideration_stated_in_note": ("bia_land_decision_subsequent_action", "reconsidered"),
    "denial_stated_in_note": ("bia_land_decision_subsequent_action", "denied"),
    "withdrawal_stated_in_note": ("bia_land_decision_subsequent_action", "withdrawn"),
    "rescission_stated_in_note": ("bia_land_decision_subsequent_action", "rescinded"),
    "affirmance_stated_in_note": ("bia_land_decision_subsequent_action", "affirmed"),
    "reversal_stated_in_note": ("bia_land_decision_subsequent_action", "reversed"),
    "governor_concurrence_stated_in_note": ("governor_concurrence_action", "concurred"),
    "governor_nonconcurrence_stated_in_note": ("governor_concurrence_action", "nonconcurred"),
    "stated_in_bia_note": ("bia_land_decision_note", "stated"),
    "federal_register_land_acquisition_notice": ("fr_land_acquisition_notice", "published"),
    "federal_register_reversal_of_land_acquisition": ("fr_land_acquisition_notice", "reversed"),
    "federal_register_notice": ("fr_gaming_land_notice", "published"),
}


def build_land(ctx: Ctx, bag: EventBag):
    decisions = ctx.clean("gaming_land_decisions.csv")
    devents = ctx.clean("gaming_decision_events.csv")
    dec = {d["decision_id"]: d for d in decisions}
    for e in devents:
        etype, status = LAND_EVENT_MAP.get(e.get("event_type"), ("bia_land_decision_note", "unknown"))
        d = dec.get(e.get("decision_id"), {})
        uid = _uid(d.get("cedar_uid"))
        common = dict(
            subject_cedar_uids=uid,
            subject_link_basis="gaming_land_decisions.cedar_uid (existing link)" if uid else "",
            subject_name_as_published=e.get("tribe", ""), state=d.get("state_abbr", ""),
            decision_id=e.get("decision_id", ""), rights_class=PUB,
            retrieved_date=e.get("fetched_date", ""))
        docnum = _fr_docnum(e.get("document_url")) if etype.startswith("fr_") else ""
        if docnum:
            bag.add(("FR", docnum), _ev(
                event_type=etype, agency="Department of the Interior (BIA)",
                action_date=e.get("event_date", ""), action_date_basis=e.get("event_date_basis", ""),
                status=status, status_basis=f"gaming_decision_events.event_type={e.get('event_type')}",
                fr_document_number=docnum, title_or_description=e.get("description", ""),
                source_system="federal_register", source_record_id=docnum,
                source_url=e.get("document_url", ""), source_date=_date(e.get("event_date"))[0],
                _primary_cite=f"federal_register:{docnum}", **common),
                f"gaming_decision_events:{e['event_id']}")
            continue
        agency = "State Governor" if etype == "governor_concurrence_action" else "Department of the Interior (AS-IA)"
        bag.add(("BIA-GLD-EVENT", e["event_id"]), _ev(
            event_type=etype, event_subtype=e.get("event_type", ""), agency=agency,
            action_date=e.get("event_date", ""), action_date_basis=e.get("event_date_basis", ""),
            status=status, status_basis=e.get("evidence_text", "")[:300],
            title_or_description=e.get("description", ""), source_system="bia_oig_gaming_land_decisions",
            source_record_id=e["event_id"], source_url=e.get("source_url", ""),
            source_date=_date(e.get("event_date"))[0],
            evidence_note="Decision/action date only; it is not a trust-acquisition closing or a facility opening",
            _primary_cite=f"gaming_decision_events:{e['event_id']}", **common),
            f"gaming_decision_events:{e['event_id']}")
    for d in decisions:
        docnum = d.get("federal_register_doc_number") or _fr_docnum(d.get("federal_register_url"))
        if docnum:
            uid = _uid(d.get("cedar_uid"))
            bag.add(("FR", docnum), _ev(
                event_type="fr_land_acquisition_notice", agency="Department of the Interior (BIA)",
                action_date=d.get("federal_register_date", ""),
                action_date_basis="publication date in the Federal Register URL path",
                status="reversed" if "reversal" in (d.get("federal_register_slug") or "") else "published",
                status_basis="FR link on the BIA gaming land-decision index row (slug)",
                subject_cedar_uids=uid,
                subject_link_basis="gaming_land_decisions.cedar_uid (existing link)" if uid else "",
                subject_name_as_published=d.get("tribe", ""), state=d.get("state_abbr", ""),
                decision_id=d["decision_id"], fr_document_number=docnum,
                title_or_description=d.get("federal_register_slug", ""),
                source_system="federal_register", source_record_id=docnum,
                source_url=d.get("federal_register_url", ""),
                source_date=_date(d.get("federal_register_date"))[0],
                retrieved_date=d.get("fetched_date", ""), rights_class=PUB,
                _primary_cite=f"federal_register:{docnum}"), f"gaming_land_decisions:{d['decision_id']}")
    return decisions, devents


def _theory_class(text: str) -> str:
    t = (text or "").lower()
    if not t:
        return "unknown"
    if "two-part" in t:
        return "two_part_determination"
    if "restored" in t:
        return "restored_lands"
    if "initial reservation" in t:
        return "initial_reservation"
    if "settlement agreement" in t:
        return "other"
    if "settlement" in t:
        return "settlement_of_land_claim"
    if "oklahoma" in t:
        return "oklahoma_former_reservation"
    if "last recognized" in t:
        return "last_recognized_reservation"
    if "within" in t or "contiguous" in t:
        return "within_or_contiguous_reservation"
    if "jurisdiction" in t or "governmental power" in t:
        return "jurisdiction_or_governmental_power"
    if "aquired" in t or "acquired" in t or "pre-igra" in t:
        return "after_acquired_or_pre_igra"
    if "indian lands" in t:
        return "indian_lands_status_question"
    return "other"


def build_land_eligibility(ctx: Ctx, decisions, events_by_decision, nigc_il, nepa_projects):
    out = []
    for d in decisions:
        evs = sorted(events_by_decision.get(d["decision_id"], []),
                     key=lambda r: (r["action_date"], r["regulatory_event_id"]))
        later = [r for r in evs if r["event_type"] in ("bia_land_decision_subsequent_action",
                                                       "fr_land_acquisition_notice")
                 and r["status"] in ("rescinded", "reversed", "withdrawn", "remanded",
                                     "denied", "reconsidered", "affirmed")
                 and r["action_date"]]
        last = later[-1] if later else None
        tc = _theory_class(d.get("legal_theory"))
        iso, prec = _date(d.get("decision_date"))
        uid = _uid(d.get("cedar_uid"))
        out.append({
            "land_eligibility_id": gg.derive_id("GREG", "LAND-ELIGIBILITY", "bia_oig_gaming_land_decisions",
                                                d["decision_id"]),
            "determination_kind": "bia_gaming_land_decision",
            "determination_body": "Department of the Interior (AS-IA / BIA Office of Indian Gaming)",
            "decision_id": d["decision_id"], "legal_theory_as_published": d.get("legal_theory", ""),
            "legal_theory_class": tc, "igra_provision": LAND_THEORY_CLASSES[tc],
            "current_status": (d.get("decision_status") or "unknown").lower(),
            "current_status_basis": d.get("decision_status_basis", ""),
            "decision_date": iso, "decision_date_precision": prec,
            "decision_date_basis": d.get("decision_date_basis", ""),
            "latest_subsequent_action": last["status"] if last else "",
            "latest_subsequent_action_date": last["action_date"] if last else "",
            "regulatory_event_ids": _join(r["regulatory_event_id"] for r in evs),
            "cedar_uid": uid, "subject_name_as_published": d.get("tribe", ""),
            "state": d.get("state_abbr", ""), "parcel_as_published": "",
            "fr_document_number": d.get("federal_register_doc_number", ""),
            "fr_publication_date": _date(d.get("federal_register_date"))[0],
            "project_key": nepa_projects.get(d["decision_id"], ""),
            "source_system": "bia_oig_gaming_land_decisions", "source_record_id": d["decision_id"],
            "source_url": d.get("source_url", ""), "source_date": iso,
            "retrieved_date": d.get("fetched_date", ""), "rights_class": PUB,
        })
    for o in nigc_il:
        tc = _theory_class(o.get("legal_theory"))
        iso, prec = _date(o.get("opinion_date"))
        acc = {"Yes": "theory_accepted", "No": "theory_not_accepted"}.get(o.get("theory_accepted"), "unknown")
        out.append({
            "land_eligibility_id": gg.derive_id("GREG", "LAND-ELIGIBILITY", "nigc_indian_lands_opinions",
                                                o["opinion_id"]),
            "determination_kind": "nigc_indian_lands_opinion",
            "determination_body": "NIGC Office of General Counsel",
            "decision_id": o["opinion_id"], "legal_theory_as_published": o.get("legal_theory", ""),
            "legal_theory_class": tc, "igra_provision": LAND_THEORY_CLASSES[tc],
            "current_status": acc, "current_status_basis": "NIGC index theory_accepted column",
            "decision_date": iso, "decision_date_precision": prec,
            "decision_date_basis": o.get("opinion_date_basis", ""),
            "latest_subsequent_action": "", "latest_subsequent_action_date": "",
            "regulatory_event_ids": gg.derive_id("GREG", "NIGC-IL", o["opinion_id"]),
            "cedar_uid": _uid(o.get("cedar_uid")),
            "subject_name_as_published": o.get("tribe_name_as_published", ""), "state": "",
            "parcel_as_published": o.get("parcel", ""), "fr_document_number": "",
            "fr_publication_date": "", "project_key": "",
            "source_system": "nigc_indian_lands_opinions", "source_record_id": o["opinion_id"],
            "source_url": o.get("document_url", ""), "source_date": iso,
            "retrieved_date": o.get("fetched_date", ""), "rights_class": PUB,
        })
    return out


NIGC_EA_MAP = {"NOV": ("nigc_notice_of_violation", "issued"),
               "SA": ("nigc_settlement_agreement", "settled"),
               "CFA": ("nigc_civil_fine_assessment", "issued"),
               "CO": ("nigc_closure_order", "issued"),
               "TCO": ("nigc_temporary_closure_order", "issued"),
               "NDO": ("nigc_enforcement_other", "issued")}


def build_nigc(ctx: Ctx, bag: EventBag):
    fin = ctx.clean("gaming_financing_events.csv", required=False)
    fin_by_op = defaultdict(set)
    for f in fin:
        if f.get("cedar_opinion_id"):
            fin_by_op[f["cedar_opinion_id"]].add(f["financing_event_id"])

    for r in ctx.clean("nigc_declination_letters.csv"):
        uid = _uid(r.get("cedar_uid"))
        key = ("NIGC-DL", r["cedar_opinion_id"])
        bag.add(key, _ev(
            event_type="nigc_declination_letter", event_subtype=r.get("agreement_type", ""),
            agency="NIGC Office of General Counsel", action_date=r.get("opinion_date", ""),
            action_date_basis=r.get("opinion_date_basis", ""), status="declination_issued",
            status_basis=f"is_management_contract={r.get('is_management_contract','')}; evidentiary_stage={r.get('evidentiary_stage','')}",
            subject_cedar_uids=uid, subject_link_basis=f"nigc_declination_letters.cedar_uid ({r.get('tribe_resolve_how','')})" if uid else "",
            subject_name_as_published=r.get("index_tribe_string", ""),
            title_or_description=r.get("re_line", ""), source_system="nigc_declination_letters",
            source_record_id=r["cedar_opinion_id"], source_url=r.get("source_url", ""),
            source_date=_date(r.get("opinion_date"))[0], retrieved_date=r.get("fetched_date", ""),
            rights_class=PUB, evidence_note=(r.get("what_this_does_not_establish") or "")[:300],
            _primary_cite=f"nigc_declination_letters:{r['cedar_opinion_id']}"),
            f"nigc_declination_letters:{r['cedar_opinion_id']}")
        for fid in sorted(fin_by_op.get(r["cedar_opinion_id"], ())):
            bag.add(key, _ev(event_type="nigc_declination_letter", status="declination_issued"),
                    f"gaming_financing_events:{fid}")

    parties = defaultdict(set)
    for p in ctx.clean("nigc_action_parties.csv", required=False):
        u = _uid(p.get("cedar_uid"))
        if u:
            parties[p["record_id"]].add(u)

    for r in ctx.clean("nigc_enforcement_actions.csv"):
        etype, status = NIGC_EA_MAP.get(r.get("action_type", ""),
                                        ("nigc_enforcement_document_untyped", "unknown"))
        uids = {_uid(r.get("cedar_uid"))} | parties.get(r["action_id"], set())
        bag.add(("NIGC-EA", r["action_id"]), _ev(
            event_type=etype, event_subtype=r.get("action_code", ""), agency="NIGC",
            action_date=r.get("document_date", ""), action_date_basis=r.get("document_date_basis", ""),
            posted_date=_date(r.get("index_post_date"))[0], status=status,
            status_basis=f"NIGC action_type={r.get('action_type','') or 'blank'}",
            subject_cedar_uids=_join(uids),
            subject_link_basis="nigc_enforcement_actions / nigc_action_parties cedar_uid (existing link)" if any(uids) else "",
            subject_name_as_published=r.get("tribe_name_as_published", ""),
            title_or_description=r.get("document_title_verbatim", ""),
            source_system="nigc_enforcement_actions", source_record_id=r["action_id"],
            source_url=r.get("resolved_document_url") or r.get("document_url", ""),
            source_date=_date(r.get("document_date"))[0], retrieved_date=r.get("fetched_date", ""),
            rights_class=PUB,
            evidence_note="posted_date is the website posting date, not the action date" if not r.get("document_date") else "",
            _primary_cite=f"nigc_enforcement_actions:{r['action_id']}"),
            f"nigc_enforcement_actions:{r['action_id']}")

    for r in ctx.clean("nigc_management_contract_approvals.csv"):
        uids = {_uid(r.get("cedar_uid"))} | parties.get(r["action_id"], set())
        bag.add(("NIGC-MC", r["action_id"]), _ev(
            event_type="nigc_management_contract_approval", agency="NIGC Chair",
            action_date=r.get("document_date", ""), action_date_basis=r.get("document_date_basis", ""),
            posted_date=_date(r.get("index_post_date"))[0], status="approved",
            status_basis="listed on NIGC 'approved-management-contracts' index",
            subject_cedar_uids=_join(uids),
            subject_link_basis="nigc_management_contract_approvals.cedar_uid (existing link)" if any(uids) else "",
            subject_name_as_published=r.get("tribe_name_as_published", ""),
            title_or_description=r.get("document_title_verbatim", ""),
            source_system="nigc_management_contract_approvals", source_record_id=r["action_id"],
            source_url=r.get("resolved_document_url") or r.get("document_url", ""),
            source_date=_date(r.get("document_date"))[0], retrieved_date=r.get("fetched_date", ""),
            rights_class=PUB, _primary_cite=f"nigc_management_contract_approvals:{r['action_id']}"),
            f"nigc_management_contract_approvals:{r['action_id']}")

    il = ctx.clean("nigc_indian_lands_opinions.csv")
    for r in il:
        uid = _uid(r.get("cedar_uid"))
        status = {"Yes": "theory_accepted", "No": "theory_not_accepted"}.get(r.get("theory_accepted"), "issued")
        bag.add(("NIGC-IL", r["opinion_id"]), _ev(
            event_type="nigc_indian_lands_opinion", event_subtype=r.get("legal_theory", ""),
            agency="NIGC Office of General Counsel", action_date=r.get("opinion_date", ""),
            action_date_basis=r.get("opinion_date_basis", ""), status=status,
            status_basis=f"theory_accepted={r.get('theory_accepted','')}",
            subject_cedar_uids=uid, subject_link_basis="nigc_indian_lands_opinions.cedar_uid (existing link)" if uid else "",
            subject_name_as_published=r.get("tribe_name_as_published", ""),
            title_or_description=r.get("parcel", ""), source_system="nigc_indian_lands_opinions",
            source_record_id=r["opinion_id"], source_url=r.get("document_url", ""),
            source_date=_date(r.get("opinion_date"))[0], retrieved_date=r.get("fetched_date", ""),
            rights_class=PUB, _primary_cite=f"nigc_indian_lands_opinions:{r['opinion_id']}"),
            f"nigc_indian_lands_opinions:{r['opinion_id']}")

    for r in ctx.clean("nigc_game_classification_opinions.csv", required=False):
        bag.add(("NIGC-GC", r["opinion_id"]), _ev(
            event_type="nigc_game_classification_opinion", event_subtype=f"class {r.get('game_class','')}",
            agency="NIGC Office of General Counsel", action_date=r.get("opinion_date", ""),
            action_date_basis=r.get("opinion_date_basis", ""), status="issued",
            status_basis="game classification opinion on NIGC index",
            subject_name_as_published=r.get("game_title", ""),
            title_or_description=r.get("game_title", ""),
            source_system="nigc_game_classification_opinions", source_record_id=r["opinion_id"],
            source_url=r.get("document_url", ""), source_date=_date(r.get("opinion_date"))[0],
            retrieved_date=r.get("fetched_date", ""), rights_class=PUB,
            evidence_note="classifies a game; names no Native entity",
            _primary_cite=f"nigc_game_classification_opinions:{r['opinion_id']}"),
            f"nigc_game_classification_opinions:{r['opinion_id']}")

    for r in ctx.clean("gaming_ordinances.csv"):
        uid = _uid(r.get("cedar_uid"))
        note = []
        if r.get("date_agreement", "").startswith("DISAGREE"):
            note.append(f"document date disagrees with index ({r['date_agreement']})")
        if r.get("index_anomaly"):
            note.append(r["index_anomaly"])
        bag.add(("NIGC-ORD", r["ordinance_id"]), _ev(
            event_type="gaming_ordinance_approval", event_subtype=r.get("ordinance_type", ""),
            agency="NIGC Chair", action_date=r.get("approval_date", ""),
            action_date_basis="NIGC gaming-ordinance index date", status="approved",
            status_basis="listed on NIGC gaming ordinances index as approved",
            subject_cedar_uids=uid, subject_link_basis="gaming_ordinances.cedar_uid (existing link)" if uid else "",
            subject_name_as_published=r.get("index_tribe_name") or r.get("tribe_name", ""),
            state=r.get("entity_state", ""), title_or_description=r.get("tribal_gaming_agency_named", ""),
            source_system="nigc_gaming_ordinances", source_record_id=r["ordinance_id"],
            source_url=r.get("resolved_pdf_url") or r.get("source_url", ""),
            source_date=_date(r.get("approval_date"))[0], retrieved_date=r.get("fetched_date", ""),
            rights_class=PUB, evidence_note="; ".join(note),
            _primary_cite=f"gaming_ordinances:{r['ordinance_id']}"),
            f"gaming_ordinances:{r['ordinance_id']}")
    return il


def _fr_status(text: str, at: str, rtype: str, action: str):
    t = text.lower()
    a = (action or "").lower()
    if at == "tribal_state_compact":
        if re.search(r"deemed approved|considered to have been approved|considered approved", t):
            return "deemed_approved", "FR text: deemed/considered approved"
        if "disapprov" in t:
            return "disapproved", "FR text: disapprov*"
        if "approv" in t:
            return "approved", "FR text: approv*"
        if "extension" in t:
            return "extended", "FR text: extension"
        if "taking effect" in t or "takes effect" in t:
            return "in_effect", "FR text: taking effect"
        return "published", "FR notice; status not stated in title/abstract"
    if "withdraw" in a:
        return "withdrawn", "FR action line: withdrawal"
    if rtype == "Rule":
        return "final", "FR document type Rule"
    if rtype == "Proposed Rule":
        return "proposed", "FR document type Proposed Rule"
    if at == "gaming_land_decision" and "revers" in t:
        return "reversed", "FR text: reversal"
    if "approval of class iii" in a or "approval of class iii" in t:
        return "approved", "FR action line: approval"
    return "published", "FR notice; status not stated"


def build_federal_register(ctx: Ctx, bag: EventBag):
    def keep(r):
        at = r.get("action_type", "")
        nigc = "national-indian-gaming-commission" in (r.get("agency_slugs") or "")
        if at in ("tribal_state_compact", "gaming_land_decision") or nigc:
            return True
        return at == "land_into_trust" and bool(GAMING_KW.search((r.get("title") or "") + " " + (r.get("abstract") or "")))

    rows = ctx.stream_filtered("federal_actions.csv", keep)
    bridge = defaultdict(set)
    for b in ctx.clean("federal_actions_entity_bridge.csv", required=False):
        basis = b.get("entity_match_basis", "")
        if basis.startswith(("exact_span_with_tribal_designator", "multi_token_exact_span_with_tribal_designator")):
            u = _uid(b.get("cedar_uid"))
            if u:
                bridge[b["document_number"]].add(u)
        else:
            ctx.withheld["fr_bridge.link_refused_weak_basis"] += 1
    for r in rows:
        at = r.get("action_type", "")
        nigc = "national-indian-gaming-commission" in (r.get("agency_slugs") or "")
        text = (r.get("title") or "") + " " + (r.get("abstract") or "")
        if at == "tribal_state_compact":
            etype = "compact_fr_notice"
        elif at == "gaming_land_decision":
            etype = "fr_gaming_land_notice"
        elif at == "land_into_trust":
            etype = "fr_land_acquisition_notice"
        elif nigc and r.get("type") == "Rule":
            etype = "nigc_fr_final_rule"
        elif nigc and r.get("type") == "Proposed Rule":
            etype = "nigc_fr_proposed_rule"
        elif nigc and at == "consultation":
            etype = "gaming_consultation_notice"
        else:
            etype = "nigc_fr_notice"
        status, basis = _fr_status(text, at, r.get("type", ""), r.get("action", ""))
        docnum = r["document_number"]
        uids = bridge.get(docnum, set())
        bag.add(("FR", docnum), _ev(
            event_type=etype, event_subtype=(r.get("action") or "")[:120],
            agency=(r.get("agency_names") or "").strip("; "),
            action_date=r.get("publication_date", ""), action_date_basis="Federal Register publication_date",
            status=status, status_basis=basis, subject_cedar_uids=_join(uids),
            subject_link_basis="federal_actions_entity_bridge (tribal-designator span matches only)" if uids else "",
            fr_document_number=docnum, title_or_description=r.get("title", ""),
            docket_ids=_join(x.strip() for x in (r.get("docket_ids") or "").split(";")),
            source_system="federal_register", source_record_id=docnum,
            source_url=r.get("html_url") or r.get("source_url", ""),
            source_date=_date(r.get("publication_date"))[0], retrieved_date=r.get("fetched_date", ""),
            rights_class=PUB, _primary_cite=f"federal_register:{docnum}"), f"federal_actions:{docnum}")

    for c in ctx.clean("consultation_events.csv", required=False):
        blob = " ".join((c.get("topic") or "", c.get("agency") or "", c.get("source_quote") or ""))
        if not GAMING_KW.search(blob) and "gaming commission" not in blob.lower():
            continue
        docnum = c.get("fr_document_number", "")
        key = ("FR", docnum) if docnum else ("CONS", c["consultation_event_id"])
        bag.add(key, _ev(
            event_type="gaming_consultation_notice", event_subtype=c.get("consultation_type", ""),
            agency=c.get("agency", ""), action_date=c.get("notice_date", ""),
            action_date_basis="FR notice date", status="published",
            status_basis="consultation notice", fr_document_number=docnum,
            title_or_description=c.get("topic", ""),
            source_system="federal_register" if docnum else "consultation_events",
            source_record_id=docnum or c["consultation_event_id"], source_url=c.get("source_url", ""),
            source_date=_date(c.get("notice_date"))[0], retrieved_date=c.get("fetched_date", ""),
            rights_class=PUB,
            _primary_cite=f"federal_register:{docnum}" if docnum else f"consultation_events:{c['consultation_event_id']}"),
            f"consultation_events:{c['consultation_event_id']}")
    return rows


# ---------------------------------------------------------------- environmental reviews
def _env_role(types: str):
    t = types or ""
    if "record_of_decision" in t:
        role = "record_of_decision"
    elif "fonsi" in t:
        role = "fonsi"
    elif "notice_of_availability" in t:
        role = "notice_of_availability"
    elif "notice_of_intent" in t:
        role = "notice_of_intent"
    elif "scoping" in t:
        role = "scoping_report"
    elif "extension" in t and ("environmental" in t or "notice" in t):
        role = "comment_period_extension"
    elif "environmental_impact_statement" in t:
        role = "environmental_impact_statement"
    elif "environmental_assessment" in t:
        role = "environmental_assessment"
    else:
        return None, None
    if "environmental_impact_statement" in t or role == "record_of_decision":
        level = "EIS" if "environmental_impact_statement" in t else "unknown"
    elif "environmental_assessment" in t or role == "fonsi":
        level = "EA"
    else:
        level = "unknown"
    return role, level


def _label_date(label: str):
    d = _us_date(label)
    if d:
        return d, "day", "date printed in the document label"
    m = re.search(r"\b(January|February|March|April|May|June|July|August|September|October|November|December) (\d{4})\b", label or "")
    if m:
        return f"{m.group(2)}-{_MONTHS[m.group(1)[:3].lower()]:02d}", "month", "month printed in the document label"
    return "", "unknown", "no date printed in the document label"


def build_environmental(ctx: Ctx, decisions, fr_rows=(), fr_events=None):
    manifest = ctx.raw_csv("data/raw/external/gaming_nepa/_SOURCE_MANIFEST.csv")
    proj_by_dec, sha_by_url, local_by_url = {}, {}, {}
    for m in manifest:
        if m.get("decision_id"):
            proj_by_dec[m["decision_id"]] = m.get("project_id", "")
        sha_by_url[m.get("source_url", "")] = m.get("sha256", "")
        local_by_url[m.get("source_url", "")] = m.get("local_file", "")
    counts = defaultdict(Counter)
    for name, key in (("gaming_projections.csv", "applicant_projection_rows"),
                      ("gaming_mitigation_agreements.csv", "mitigation_agreement_rows"),
                      ("gaming_project_facilities.csv", "facility_scenario_rows")):
        for r in ctx.clean(name, required=False):
            counts[r.get("project_id", "")][key] += 1

    rows: dict[str, dict] = {}
    cites = defaultdict(set)

    def add(key, row, cite):
        if key in rows:
            for k, v in row.items():
                if v and not rows[key].get(k):
                    rows[key][k] = v
        else:
            rows[key] = row
        cites[key].add(cite)

    for d in decisions:
        urls = (d.get("document_urls") or "").split("|")
        labels = (d.get("document_labels") or "").split("|")
        types = (d.get("document_types") or "").split("|")
        pk = proj_by_dec.get(d["decision_id"], "")
        uid = _uid(d.get("cedar_uid"))
        for i, url in enumerate(urls):
            t = types[i] if i < len(types) else ""
            if not url or "appendix" in t:
                if "appendix" in t:
                    ctx.withheld["environmental.appendix_documents_not_rowed"] += 1
                continue
            role, level = _env_role(t)
            if not role:
                continue
            label = labels[i] if i < len(labels) else ""
            dd, prec, basis = _label_date(label)
            c = counts.get(pk, Counter())
            add(url, {
                "environmental_review_id": gg.derive_id("GENV", "document_url", url),
                "project_key": pk or d["decision_id"],
                "project_key_basis": "gaming_nepa project_id" if pk else "bia gaming land decision_id (no NEPA project id)",
                "review_level": level, "document_role": role,
                "lead_agency": "Bureau of Indian Affairs", "document_title": label,
                "document_date": dd, "document_date_precision": prec, "document_date_basis": basis,
                "related_decision_id": d["decision_id"],
                "related_decision_date": _date(d.get("decision_date"))[0],
                "related_decision_status": d.get("decision_status", ""),
                "cedar_uid": uid, "subject_name_as_published": d.get("tribe", ""),
                "state": d.get("state_abbr", ""),
                "applicant_projection_rows": str(c["applicant_projection_rows"]),
                "mitigation_agreement_rows": str(c["mitigation_agreement_rows"]),
                "facility_scenario_rows": str(c["facility_scenario_rows"]),
                "local_sha256": sha_by_url.get(url, ""),
                "source_system": "bia_oig_gaming_land_decisions", "source_record_id": d["decision_id"],
                "source_url": url, "source_date": dd, "retrieved_date": d.get("fetched_date", ""),
                "rights_class": PUB,
            }, f"gaming_land_decisions:{d['decision_id']}")
            if url in local_by_url:
                cites[url].add(f"gaming_nepa_manifest:{local_by_url[url]}")

    for m in manifest:
        role, level = _env_role(m.get("document_type", ""))
        url = m.get("source_url", "")
        if not role or "appendix" in m.get("document_type", "") or url in rows:
            continue
        dd, prec, basis = _label_date(m.get("document_label", ""))
        c = counts.get(m.get("project_id", ""), Counter())
        add(url, {
            "environmental_review_id": gg.derive_id("GENV", "document_url", url),
            "project_key": m.get("project_id", ""), "project_key_basis": "gaming_nepa project_id",
            "review_level": level, "document_role": role, "lead_agency": "Bureau of Indian Affairs",
            "document_title": m.get("document_label", ""), "document_date": dd,
            "document_date_precision": prec, "document_date_basis": basis,
            "related_decision_id": m.get("decision_id", ""), "related_decision_date": "",
            "related_decision_status": "", "cedar_uid": "", "subject_name_as_published": "",
            "state": "", "applicant_projection_rows": str(c["applicant_projection_rows"]),
            "mitigation_agreement_rows": str(c["mitigation_agreement_rows"]),
            "facility_scenario_rows": str(c["facility_scenario_rows"]),
            "local_sha256": m.get("sha256", ""), "source_system": "gaming_nepa_manifest",
            "source_record_id": m.get("local_file", ""), "source_url": url, "source_date": dd,
            "retrieved_date": m.get("fetched_date", ""), "rights_class": PUB,
        }, f"gaming_nepa_manifest:{m.get('local_file','')}")

    # Federal Register NEPA notices for gaming actions (NOI / NOA / ROD / FONSI)
    fr_events = fr_events or {}
    for r in fr_rows:
        tl = (r.get("title") or "").lower()
        if not re.search(r"environmental (impact statement|assessment)|record of decision|"
                         r"finding of no significant impact|scoping", tl):
            continue
        role = ("record_of_decision" if "record of decision" in tl else
                "fonsi" if "finding of no significant impact" in tl else
                "comment_period_extension" if re.search(r"extension|reopen", tl) else
                "notice_of_intent" if "intent" in tl else
                "notice_of_availability" if "availability" in tl else
                "scoping_report" if "scoping" in tl else
                "environmental_impact_statement" if "environmental impact statement" in tl else
                "environmental_assessment" if "environmental assessment" in tl else "other_nepa_document")
        level = ("EIS" if "environmental impact statement" in tl else
                 "EA" if "environmental assessment" in tl else "unknown")
        docnum = r["document_number"]
        ev = fr_events.get(docnum, {})
        url = r.get("html_url") or r.get("source_url", "")
        add(url, {
            "environmental_review_id": gg.derive_id("GENV", "document_url", url),
            "project_key": (ev.get("decision_id") or "").split("|")[0],
            "project_key_basis": "bia gaming land decision_id linked through the FR event" if ev.get("decision_id")
            else "no project id published; not linked",
            "review_level": level, "document_role": role,
            "lead_agency": (r.get("agency_names") or "").strip("; "), "document_title": r.get("title", ""),
            "document_date": _date(r.get("publication_date"))[0], "document_date_precision": "day",
            "document_date_basis": "Federal Register publication date",
            "related_decision_id": ev.get("decision_id", ""), "related_decision_date": "",
            "related_decision_status": "", "cedar_uid": ev.get("cedar_uid", ""),
            "subject_name_as_published": "", "state": "", "applicant_projection_rows": "0",
            "mitigation_agreement_rows": "0", "facility_scenario_rows": "0", "local_sha256": "",
            "source_system": "federal_register", "source_record_id": docnum, "source_url": url,
            "source_date": _date(r.get("publication_date"))[0],
            "retrieved_date": r.get("fetched_date", ""), "rights_class": PUB,
        }, f"federal_register:{docnum}")

    for s in ctx.clean("nigc_document_surface.csv", required=False):
        if s.get("nigc_category") != "past-fonsis":
            continue
        url = s.get("document_url", "")
        add(url or s["membership_id"], {
            "environmental_review_id": gg.derive_id("GENV", "document_url", url or s["membership_id"]),
            "project_key": s.get("document_slug", ""), "project_key_basis": "NIGC document slug (no project id published)",
            "review_level": "CATEX" if "categorical exclusion" in s.get("document_title", "").lower() else "EA",
            "document_role": "other_nepa_document" if "categorical exclusion" in s.get("document_title", "").lower() else "fonsi",
            "lead_agency": "National Indian Gaming Commission", "document_title": s.get("document_title", ""),
            "document_date": "", "document_date_precision": "unknown",
            "document_date_basis": "NIGC index gives only a posting date (not the FONSI date)",
            "related_decision_id": "", "related_decision_date": "", "related_decision_status": "",
            "cedar_uid": "", "subject_name_as_published": s.get("document_title", ""), "state": "",
            "applicant_projection_rows": "0", "mitigation_agreement_rows": "0",
            "facility_scenario_rows": "0", "local_sha256": "",
            "source_system": "nigc_document_surface", "source_record_id": s["membership_id"],
            "source_url": url, "source_date": "", "retrieved_date": s.get("fetched_date", ""),
            "rights_class": PUB,
        }, f"nigc_document_surface:{s['membership_id']}")

    blm = ctx.clean("nepa_eplanning_projects.csv", required=False)
    ctx.notes.append(f"nepa_eplanning_projects ({len(blm)} BLM rows) checked: no gaming projects; BLM is not a lead agency for Indian gaming NEPA")
    out = []
    for key, row in rows.items():
        cs = sorted(cites[key])
        primary = f"{row['source_system'] if row['source_system'] != 'bia_oig_gaming_land_decisions' else 'gaming_land_decisions'}:{row['source_record_id']}"
        row["also_cited_by"] = "|".join(c for c in cs if c != primary)
        out.append(row)
    return out


# ---------------------------------------------------------------- licences
def build_licenses(ctx: Ctx):
    out = []
    for r in ctx.clean("gaming_vendor_tribal_licenses.csv", required=False):
        if r.get("status") == "SELF_REFERENCE_NOT_A_VENDOR_RELATIONSHIP":
            ctx.withheld["licenses.vendor_self_reference_excluded"] += 1
            continue
        status = {"TRIBAL_REGULATOR_NAMED": "regulator_named_license_unconfirmed",
                  "VENDOR_AUTHORIZED_BY_TRIBAL_REGULATOR": "vendor_authorized_by_regulator"}.get(r.get("status"), "unknown")
        key = ("SEC-EDGAR-VENDOR", r.get("vendor_cik", ""), r.get("source_url", ""),
               r.get("tribal_gaming_regulator", ""), r.get("license_type", ""), r.get("license_number", ""))
        iso, _ = _date(r.get("filed_date"))
        out.append({**{c: "" for c in CONTRACTS["gaming_licenses.csv"]["_header"]},
            "license_id": gg.derive_id("GLIC", *key), "license_family": "vendor_license_mention",
            "authority_name": r.get("tribal_gaming_regulator", ""), "authority_level": "tribal",
            "authority_cedar_uid": _uid(r.get("cedar_uid")),
            "holder_name_as_published": r.get("vendor_name", ""),
            "holder_cedar_uid": "", "holder_sec_cik": r.get("vendor_cik", ""),
            "product_type": "", "license_type_as_published": r.get("license_type", ""),
            "license_number": r.get("license_number", ""), "status": status,
            "status_basis": r.get("status_basis", ""),
            "effective_start": _date(r.get("approval_date"))[0],
            "evidence_quote": (r.get("verbatim_quote") or "")[:500],
            "source_system": "sec_edgar", "source_record_id": "|".join(key[1:]),
            "source_url": r.get("source_url", ""), "source_date": iso,
            "retrieved_date": r.get("retrieved_at", ""), "rights_class": PUB})
    for r in ctx.clean("digital_gaming_relationships.csv", required=False):
        cs = r.get("current_status", "")
        status = ("operating_observed" if cs == "operating" else
                  "ceased_as_platform_provider" if cs.startswith("ceased") else
                  "authorized_operation_not_observed" if cs.startswith("authorised_by_compact") else "unknown")
        fac = ""
        if r.get("cedar_place_id"):
            try:
                fac = gg.facility_id_for(r["cedar_place_id"])
            except ValueError:
                ctx.withheld["licenses.malformed_place_id"] += 1
        uid = _uid(r.get("cedar_uid"))
        out.append({**{c: "" for c in CONTRACTS["gaming_licenses.csv"]["_header"]},
            "license_id": gg.derive_id("GLIC", "DIGITAL", r["digital_gaming_id"]),
            "license_family": "wagering_authorization",
            "authority_name": r.get("compact_authority_cite") or urlparse(r.get("source_url", "")).netloc,
            "authority_level": "tribal_state_compact" if r.get("compact_authority_cite") else "state",
            "authority_cedar_uid": "", "holder_name_as_published": r.get("tribe_canonical_name", ""),
            "holder_cedar_uid": uid, "gaming_facility_id": fac, "state": r.get("state", ""),
            "product_type": r.get("product_type", ""),
            "license_type_as_published": r.get("license_type", ""), "status": status,
            "status_basis": cs, "operation_start_date": _date(r.get("launch_date"))[0],
            "cessation_date": _date(r.get("cessation_date"))[0],
            "compact_citation": r.get("compact_authority_cite", ""),
            "evidence_quote": (r.get("source_quote") or r.get("compact_authority_quote") or "")[:500],
            "source_system": "digital_gaming_relationships", "source_record_id": r["digital_gaming_id"],
            "source_url": r.get("source_url", ""), "source_date": "",
            "retrieved_date": r.get("fetched_date", ""), "rights_class": PUB})
    for r in ctx.clean("wa_machine_allocations.csv", required=False):
        m = re.search(r"unit=([A-Za-z_]+)", r.get("compact_or_appendix_cite", ""))
        out.append({**{c: "" for c in CONTRACTS["gaming_licenses.csv"]["_header"]},
            "license_id": gg.derive_id("GLIC", "WA-ALLOC", r["allocation_id"]),
            "license_family": "machine_allocation",
            "authority_name": "Tribal-State compact appendix (Washington)",
            "authority_level": "tribal_state_compact",
            "holder_name_as_published": r.get("tribe_name", ""), "holder_cedar_uid": _uid(r.get("cedar_uid")),
            "state": "WA", "product_type": "tribal lottery system player terminals",
            "status": "authorized_maximum_superseded" if r.get("effective_end") else "authorized_maximum_open_interval",
            "status_basis": r.get("confidence", ""),
            "effective_start": _date(r.get("effective_start"))[0],
            "effective_end": _date(r.get("effective_end"))[0],
            "authorized_quantity": r.get("total_authorized", ""),
            "quantity_unit": m.group(1) if m else "", "measurement_type": r.get("measurement_type", ""),
            "compact_citation": r.get("compact_or_appendix_cite", ""),
            "evidence_quote": (r.get("source_quote") or "")[:500],
            "source_system": "wa_machine_allocations", "source_record_id": r["allocation_id"],
            "source_url": r.get("source_url", ""), "source_date": "",
            "retrieved_date": r.get("fetched_date", ""), "rights_class": PUB})
    transfers = ctx.clean("wa_machine_transfers.csv", required=False)
    if not transfers:
        ctx.notes.append("wa_machine_transfers is empty in source: no WA transfer rows")
    return out


# ---------------------------------------------------------------- litigation
CASE_RE = re.compile(
    r"(?:from|by|following|in|nom\.)\s+(?P<name>[A-Z][^()]*?v\.\s[^()]*?)\s*,\s*"
    r"(?P<cite>\d+\s+(?:F\.\s?(?:Supp\.\s)?\d?[a-z]{0,2}\.?|U\.S\. App\. D\.C\.)\s+\d+|Case No\.\s*[\w-]+)"
    r"(?:,\s*\d+)?\s*\((?P<paren>[^)]*)\)")
REPORTER_COURT = {"U.S. App. D.C.": "D.C. Cir."}


def parse_case_citations(text: str):
    """Case citations printed in a BIA note: [(name, cite, court, year)]."""
    out = []
    for m in CASE_RE.finditer(text or ""):
        name = re.sub(r"\s+", " ", m.group("name")).strip(" ,")
        cite = re.sub(r"\s+", " ", m.group("cite")).strip()
        paren = m.group("paren").strip()
        ym = re.search(r"(\d{4})\s*$", paren)
        year = ym.group(1) if ym else ""
        court = paren[:ym.start()].strip() if ym else paren
        if not court:
            court = next((c for r, c in REPORTER_COURT.items() if r in cite), "")
        out.append((name, cite, court, year))
    return out


def _court_kind(court: str) -> str:
    return "supreme_court_docket" if "Supreme" in court else "federal_court_case"


def build_litigation(ctx: Ctx, decisions, devents):
    rows: dict[tuple, dict] = {}
    cites = defaultdict(set)
    lists = defaultdict(lambda: defaultdict(set))

    def add(key, row, cite, rel_dec=(), subj=(), party=()):
        if key in rows:
            for k, v in row.items():
                if v and not rows[key].get(k):
                    rows[key][k] = v
        else:
            rows[key] = dict(row, litigation_id=gg.derive_id("GLIT", *key))
        cites[key].add(cite)
        lists[key]["related_decision_id"] |= set(filter(None, rel_dec))
        lists[key]["affected_subject_cedar_uid"] |= set(filter(None, subj))
        lists[key]["party_cedar_uids"] |= set(filter(None, party))

    def base(**kw):
        r = {c: "" for c in CONTRACTS["gaming_litigation.csv"]["_header"]}
        r.update(kw)
        for f in ("filing_date", "decision_date"):
            iso, prec = _date(r.get(f, ""))
            r[f], r[f + "_precision"] = iso, prec
        r["rights_class"] = r.get("rights_class") or PUB
        return r

    # 1. BIA land-decision notes that cite a case
    ev_by_dec = defaultdict(list)
    for e in devents:
        ev_by_dec[e.get("decision_id")].append(e)
    for d in decisions:
        note = d.get("bia_note_text", "")
        uid = _uid(d.get("cedar_uid"))
        for name, cite, court, year in parse_case_citations(note):
            key = ("REPORTER", cite)
            add(key, base(
                proceeding_kind=_court_kind(court), case_name=name, forum=court,
                reporter_citation=cite if not cite.startswith("Case No") else "",
                docket_number=cite.replace("Case No.", "").strip() if cite.startswith("Case No") else "",
                decision_date=year, date_basis="year in the reporter parenthetical of the BIA note" if year else "",
                subject_area="land_gaming_eligibility", outcome_as_stated=note[:300],
                outcome_basis="BIA gaming land-decision index note (describes the effect on the decision)",
                source_system="bia_oig_gaming_land_decisions", source_record_id=d["decision_id"],
                source_url=d.get("source_url", ""), retrieved_date=d.get("fetched_date", "")),
                f"gaming_land_decisions:{d['decision_id']}", rel_dec=[d["decision_id"]], subj=[uid])
            for e in ev_by_dec.get(d["decision_id"], []):
                if cite in re.sub(r"\s+", " ", e.get("evidence_text", "")):
                    cites[key].add(f"gaming_decision_events:{e['event_id']}")
        m = re.search(r"remanded by (United States District Court for the District of Columbia) on ([A-Z][a-z]+ \d{1,2}, \d{4})", note)
        if m:
            dd = _us_date(m.group(2))
            key = ("BIA-NOTE-UNNAMED", d["decision_id"], "D.D.C.", dd)
            add(key, base(
                proceeding_kind="federal_court_case", case_name="", forum=m.group(1),
                decision_date=dd, date_basis="date stated in the BIA note",
                subject_area="land_gaming_eligibility", outcome_as_stated=note[:300],
                outcome_basis="BIA gaming land-decision index note; the case is not named in the source",
                source_system="bia_oig_gaming_land_decisions", source_record_id=d["decision_id"],
                source_url=d.get("source_url", ""), retrieved_date=d.get("fetched_date", "")),
                f"gaming_land_decisions:{d['decision_id']}", rel_dec=[d["decision_id"]], subj=[uid])

    # 2. Supreme Court docket JSON already on disk (first: its dates win)
    for rel, subj in (("data/raw/external/fl_gaming/scotus_23A315.json", "compact"),
                      ("data/raw/litigation/docket_16-1320.json", "land_into_trust")):
        d = ctx.raw_json(rel)
        if not d:
            continue
        num = (d.get("CaseNumber") or "").strip()
        procs = d.get("ProceedingsandOrder") or []
        first = _us_date(procs[0]["Date"]) if procs else ""
        outcome = [p for p in procs if re.search(r"\b(denied|DENIED|granted|GRANTED|dismissed|DISMISSED)\b", p.get("Text", ""))]
        last = outcome[-1] if outcome else None
        key = ("DOCKET", "Supreme Court of the United States", num)
        add(key, base(
            proceeding_kind="supreme_court_docket",
            case_name=f"{d.get('PetitionerTitle','')} v. {d.get('RespondentTitle','')}".strip(" v."),
            forum="Supreme Court of the United States", docket_number=num,
            filing_date=first, decision_date=_us_date(last["Date"]) if last else "",
            date_basis="first and last dispositive docket entries (Supreme Court docket JSON)",
            subject_area=subj, parties_as_published=f"{d.get('PetitionerTitle','')} / {d.get('RespondentTitle','')}",
            outcome_as_stated=re.sub(r"<[^>]+>", "", last["Text"])[:300] if last else "",
            outcome_basis="Supreme Court docket entry" if last else "",
            source_system="supremecourt_docket_json", source_record_id=num,
            source_url=f"https://www.supremecourt.gov/rss/cases/JSON/{num}.json", local_file=rel),
            f"supremecourt_docket_json:{num}")

    # 3. Advocacy collection litigation positions: LINK by position_id (rows not copied)
    for p in ctx.clean("native_issue_litigation_positions.csv", required=False):
        if p.get("issue_area") != "TRIBAL_GAMING":
            continue
        court = p.get("court", "")
        key = ("DOCKET", court, p.get("docket_number", ""))
        subj = "compact" if re.search(r"Flagler|Maverick", p.get("case_name", "")) else "land_into_trust"
        add(key, base(
            proceeding_kind=_court_kind(court), case_name=p.get("case_name", ""), forum=court,
            docket_number=p.get("docket_number", ""),
            date_basis=f"no case filing date on disk; Advocacy-linked docket entry dated {p.get('filing_date','')} is not the case filing date",
            subject_area=subj, source_system="advocacy:native_issue_litigation_positions",
            source_record_id=p["position_id"], source_url=p.get("source_url", ""),
            local_file=p.get("local_file", ""), retrieved_date=p.get("fetched_date", "")),
            f"advocacy:native_issue_litigation_positions:{p['position_id']}")
    for c in ctx.clean("native_issue_litigation_coverage.csv", required=False):
        if c.get("issue_area") == "TRIBAL_GAMING" and "W.D. Wash. 3:22-cv-05325" in c.get("source_or_forum", ""):
            key = ("DOCKET", "United States District Court for the Western District of Washington", "3:22-cv-05325")
            add(key, base(
                proceeding_kind="federal_court_case", case_name="Maverick Gaming LLC v. United States",
                forum="United States District Court for the Western District of Washington",
                docket_number="3:22-cv-05325", date_basis="no date in source", subject_area="compact",
                source_system="advocacy:native_issue_litigation_coverage",
                source_record_id=c.get("source_or_forum", ""),
                outcome_basis="forum named in coverage row only; docket not retrieved"),
                "advocacy:native_issue_litigation_coverage:" + c.get("source_or_forum", ""))

    # 4. USCOURTS opinions in the FL gaming manifest
    for m in ctx.raw_csv("data/raw/external/fl_gaming/_SOURCE_MANIFEST.csv"):
        if m.get("doc_class") != "uscourts_opinion":
            continue
        pm = re.match(r"USCOURTS-(\w+?)-(.+)-0\.pdf$", m.get("local_file", ""))
        lm = re.match(r"(?P<name>.+?) \((?P<court>[^)]*?) (?P<date>\d{4}-\d{2}-\d{2})\)$", m.get("doc_label", ""))
        if not pm or not lm:
            continue
        court_code, docket = pm.group(1), pm.group(2).replace("_", ":")
        docket = re.sub(r"^(\d{2})-0*(\d+)$", r"\1-\2", docket)
        key = ("USCOURTS", court_code, docket)
        add(key, base(
            proceeding_kind="federal_court_case", case_name=lm.group("name"), forum=lm.group("court"),
            docket_number=docket, decision_date=lm.group("date"),
            date_basis="opinion date in the govinfo USCOURTS package label", subject_area="compact",
            outcome_basis="opinion on disk; outcome not extracted",
            source_system="govinfo_uscourts", source_record_id=m.get("local_file", "").replace("-0.pdf", ""),
            source_url=m.get("source_url", "").split("?")[0],
            local_file="data/raw/external/fl_gaming/" + m.get("local_file", ""),
            retrieved_date=m.get("fetched_date", "")),
            f"fl_gaming_manifest:{m.get('local_file','')}")

    # 5. IBIA administrative appeals with a gaming caption
    for a in ctx.clean("admin_appeal_decisions.csv", required=False):
        cap = a.get("case_name_published", "")
        if a.get("board") != "IBIA" or not re.search(r"gaming|casino|bingo", cap, re.I):
            continue
        party = [u for u in (a.get("native_party_entity_ids_all") or "").split("|") if _uid(u)]
        add(("IBIA", a.get("citation", "")), base(
            proceeding_kind="administrative_appeal", case_name=cap, forum="Interior Board of Indian Appeals",
            docket_number=a.get("docket_number", ""), reporter_citation=a.get("citation", ""),
            decision_date=a.get("decision_date", ""), date_basis="IBIA chronological index",
            subject_area="administrative_appeal_unclassified",
            outcome_as_stated=a.get("disposition", ""), outcome_basis=a.get("disposition_basis", ""),
            source_system="admin_appeal_decisions", source_record_id=a["decision_id"],
            source_url=a.get("decision_pdf_url", ""), retrieved_date=a.get("fetched_date", ""),
            party_link_basis="admin_appeal_decisions native party links" if party else ""),
            f"admin_appeal_decisions:{a['decision_id']}", party=party)

    # 6. NIGC Commission final decisions (index membership only)
    for s in ctx.clean("nigc_document_surface.csv", required=False):
        if s.get("nigc_category") != "commission-final-decisions":
            continue
        title = s.get("document_title", "")
        dm = re.search(r"(\d{4}-\d{2}-\d{2})", title)
        add(("NIGC-CFD", s.get("document_slug") or s["membership_id"]), base(
            proceeding_kind="nigc_commission_proceeding",
            case_name=re.split(r"\s+\W\s+\d{4}-", title)[0].strip(), forum="National Indian Gaming Commission",
            decision_date=dm.group(1) if dm else "",
            date_basis="date printed in the NIGC index title" if dm else "NIGC index gives only a posting date",
            subject_area="regulation_enforcement", parties_as_published=title,
            source_system="nigc_document_surface", source_record_id=s["membership_id"],
            source_url=s.get("document_url", ""), retrieved_date=s.get("fetched_date", "")),
            f"nigc_document_surface:{s['membership_id']}")

    # 7. Casino-debt dockets staged by 1110 (CourtListener RECAP; staging, not promoted)
    for t in ctx.raw_csv("data/staging/tribal_debt_court_dockets.csv"):
        party = [_uid(t.get("obligor_cedar_uid"))]
        add(("DOCKET", t.get("court", ""), t.get("docket_number", "")), base(
            proceeding_kind="federal_court_case", case_name=t.get("case_name_as_captioned", ""),
            forum=t.get("court", ""), docket_number=t.get("docket_number", ""),
            filing_date=t.get("as_of_date", ""), date_basis=t.get("as_of_date_basis", ""),
            subject_area="financing_debt", parties_as_published=t.get("parties_as_recorded_by_the_clerk", "")[:500],
            party_link_basis=("staging 1110 obligor link: " + t.get("obligor_entity_match_method", ""))[:300] if any(party) else "",
            outcome_basis=t.get("event_type_basis", "")[:300],
            source_system="courtlistener_recap_staging_1110", source_record_id=t.get("docket_row_id", ""),
            source_url=t.get("source_url", ""), retrieved_date=t.get("built_date", "")),
            f"staging_tribal_debt_court_dockets:{t.get('docket_row_id','')}", party=party)

    out = []
    for key, row in rows.items():
        for f in ("related_decision_id", "affected_subject_cedar_uid", "party_cedar_uids"):
            row[f] = _join(lists[key][f])
        if "|" in row["affected_subject_cedar_uid"]:
            row["affected_subject_cedar_uid"] = ""  # several subjects: kept only via related_decision_id
            ctx.withheld["litigation.multiple_affected_subjects_blanked"] += 1
        primary = f"{row['source_system']}:{row['source_record_id']}"
        cs = sorted(cites[key])
        row["also_cited_by"] = "|".join(c for c in cs if not c.endswith(":" + row["source_record_id"]))
        row["source_date"] = row["decision_date"] or row["filing_date"]
        out.append(row)
    return out


# ---------------------------------------------------------------- acquisition leads
ACQUISITION_LEADS = [
    {"component": "gaming_environmental_reviews", "lead": "EPA EIS Database (CDX e-NEPA)",
     "url": "https://cdxapps.epa.gov/cdx-enepa-II/public/action/eis/search",
     "why": "Draft/final EIS filing and comment-period dates for BIA/NIGC casino EISs; nothing on disk"},
    {"component": "gaming_environmental_reviews", "lead": "USACE Regulatory permits (ORM2 / district public notices)",
     "url": "https://permits.ops.usace.army.mil/orm-public",
     "why": "Section 404 permits for casino sites; nothing on disk"},
    {"component": "gaming_environmental_reviews", "lead": "NIGC past FONSI PDFs (dates and projects)",
     "url": "https://www.nigc.gov/downloads/past-fonsis/",
     "why": "index membership only; FONSI dates and cedar_uid links need the documents"},
    {"component": "gaming_licenses", "lead": "State sports-wagering / iGaming licensee registers",
     "url": "MGCB, AZDG, NYSGC, CT DCP, WA WSGC, CO DOG licensee lists",
     "why": "digital_gaming_relationships covers 15 states' observed operations, not a licence census"},
    {"component": "gaming_licenses", "lead": "WSGC machine-transfer records (Appendix D)",
     "url": "https://wsgc.wa.gov/",
     "why": "wa_machine_transfers is empty"},
    {"component": "gaming_licenses", "lead": "Tribal gaming commission vendor-licence lists",
     "url": "tribal regulator websites (per-regulator terms review needed)",
     "why": "SEC mentions name a regulator; they do not confirm a licence"},
    {"component": "gaming_litigation", "lead": "CourtListener REST v4 dockets for BIA-note cases",
     "url": "https://www.courtlistener.com/api/rest/v4/search/",
     "why": "dockets/filing dates for Gila River v. US, Scotts Valley v. DOI, Koi Nation v. DOI, Butte Cty v. Hogen, Littlefield, Maverick W.D. Wash.; "
            "no pass run: robots.txt returned HTTP 403 at the CDN on 2026-09-24 so crawl permission could not be verified"},
    {"component": "gaming_litigation", "lead": "govinfo USCOURTS collection (public API)",
     "url": "https://api.govinfo.gov/collections/USCOURTS",
     "why": "opinions for IGRA cases already cited in BIA notes"},
    {"component": "gaming_litigation", "lead": "NIGC Commission final decision PDFs",
     "url": "https://www.nigc.gov/downloads/commission-final-decisions/",
     "why": "index membership only; decision dates/outcomes need the documents"},
]


# ---------------------------------------------------------------- build
# Columns that carry a BIA-index compact/version key (pipe lists allowed).
# The key names a tribe and a date, so it is never the public ID: each value
# becomes the token of its CEDAR-CONTRACT binding, after every join above has
# used the source key. `source_record_id` / `also_cited_by` keep the key.
COMPACT_KEY_COLUMNS = {"compact_id": "GCMP", "successor_compact_id": "GCMP", "version_id": "GCMV"}


def bind_compact_keys(rows):
    for r in rows:
        for col, klass in COMPACT_KEY_COLUMNS.items():
            if r.get(col):
                r[col] = "|".join(gg.derive_id(klass, v) for v in r[col].split("|") if v.strip())


def build(inputs: gg.Inputs, out_dir: Path) -> dict:
    ctx = Ctx(inputs)
    bag = EventBag()
    compacts, versions, terms = build_compacts(ctx, bag)
    decisions, devents = build_land(ctx, bag)
    nigc_il = build_nigc(ctx, bag)
    fr_rows = build_federal_register(ctx, bag)
    events = bag.finalize()
    fr_events = {e['fr_document_number']: e for e in events if e['source_system'] == 'federal_register'}

    by_dec = defaultdict(list)
    for e in events:
        for d in filter(None, e["decision_id"].split("|")):
            by_dec[d].append(e)
    manifest_proj = {}
    for m in ctx.raw_csv("data/raw/external/gaming_nepa/_SOURCE_MANIFEST.csv"):
        if m.get("decision_id") and m.get("project_id"):
            manifest_proj[m["decision_id"]] = m["project_id"]
    land = build_land_eligibility(ctx, decisions, by_dec, nigc_il, manifest_proj)
    env = build_environmental(ctx, decisions, fr_rows, fr_events)
    lic = build_licenses(ctx)
    lit = build_litigation(ctx, decisions, devents)

    tables = {
        "gaming_compacts.csv": compacts, "gaming_compact_versions.csv": versions,
        "gaming_compact_terms.csv": terms, "gaming_regulatory_events.csv": events,
        "gaming_land_eligibility.csv": land, "gaming_environmental_reviews.csv": env,
        "gaming_licenses.csv": lic, "gaming_litigation.csv": lit,
    }
    for rows in tables.values():
        bind_compact_keys(rows)
    receipts = []
    for name, rows in tables.items():
        c = CONTRACTS[name]
        for r in rows:
            for k in [k for k in r if k.endswith("cedar_uids") or k == "party_cedar_uids"]:
                bad = [u for u in r[k].split("|") if u and not gg.is_ce_uid(u)]
                if bad:
                    raise gg.GamingContractError(f"REFUSED: {name}.{k} non-CE ids {bad[:3]}")
        receipts.append(gg.write_table(out_dir, name, c["_header"], rows, c))

    def yr(v):
        return (v or "")[:4] or "undated"

    coverage = {
        "regulatory_events_by_type": dict(sorted(Counter(e["event_type"] for e in events).items())),
        "regulatory_events_by_year": dict(sorted(Counter(yr(e["action_date"]) for e in events).items())),
        "regulatory_events_2025_by_type": dict(sorted(Counter(e["event_type"] for e in events if e["action_date"][:4] == "2025").items())),
        "regulatory_events_2026_by_type": dict(sorted(Counter(e["event_type"] for e in events if e["action_date"][:4] == "2026").items())),
        "regulatory_events_by_status": dict(sorted(Counter(e["status"] for e in events).items())),
        "regulatory_events_merged_source_records": bag.merges,
        "regulatory_events_multi_source": sum(1 for e in events if int(e["n_source_records"]) > 1),
        "regulatory_events_with_cedar_uid": sum(1 for e in events if e["subject_cedar_uids"]),
        "regulatory_events_distinct_subjects": len({u for e in events for u in e["subject_cedar_uids"].split("|") if u}),
        "compacts_distinct_cedar_uid": len({c["cedar_uid"] for c in compacts if c["cedar_uid"]}),
        "land_eligibility_by_kind_status": dict(sorted(Counter(f"{r['determination_kind']}:{r['current_status']}" for r in land).items())),
        "land_eligibility_by_year": dict(sorted(Counter(yr(r["decision_date"]) for r in land).items())),
        "environmental_by_role": dict(sorted(Counter(r["document_role"] for r in env).items())),
        "licenses_by_family_status": dict(sorted(Counter(f"{r['license_family']}:{r['status']}" for r in lic).items())),
        "litigation_by_kind_subject": dict(sorted(Counter(f"{r['proceeding_kind']}:{r['subject_area']}" for r in lit).items())),
        "litigation_by_year": dict(sorted(Counter(yr(r["decision_date"] or r["filing_date"]) for r in lit).items())),
        "acquisition_leads": ACQUISITION_LEADS,
        "legacy_id_values_in_inputs": [
            {"input": k[0], "column": k[1], "prefix": k[2], "count": n}
            for k, n in sorted(ctx.legacy.items())],
        "id_contract_status": gg.ID_CONTRACT_STATUS,
    }
    field_counts = {}
    for name in tables:
        fr = CONTRACTS[name]["field_rights"]
        field_counts[name] = {"public_fields": sum(1 for v in fr.values() if v in gg.PUBLIC_RIGHTS),
                              "nonpublic_fields": sum(1 for v in fr.values() if v not in gg.PUBLIC_RIGHTS),
                              "publication_status": CONTRACTS[name]["publication_status"]}
    coverage["field_rights_counts"] = field_counts
    return {"tables": receipts, "inputs": inputs.receipts, "coverage": coverage,
            "withheld": dict(sorted(ctx.withheld.items())), "notes": sorted(ctx.notes)}


def _public_contracts():
    return {k: {kk: (sorted(vv) if isinstance(vv, set) else
                     {a: sorted(b) for a, b in vv.items()} if kk == "enums" else vv)
                for kk, vv in c.items() if kk != "_header"} for k, c in CONTRACTS.items()}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--input-root", default=str(gg.DEFAULT_INPUT_ROOT))
    b.add_argument("--output-root", required=True)
    b.add_argument("--as-of", default="")
    a = ap.parse_args(argv)
    out = Path(a.output_root)
    result = build(gg.Inputs(a.input_root), out)
    result["producer"] = LANE
    result["schema_version"] = gg.SCHEMA_VERSION
    result["contracts"] = _public_contracts()
    if a.as_of:
        result["as_of"] = a.as_of
    (out / f"{LANE}.receipt.json").write_text(
        json.dumps(result, sort_keys=True, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    for t in result["tables"]:
        print(f"{t['table']}: {t['rows']} rows sha256={t['sha256'][:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
