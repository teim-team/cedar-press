"""Online sportsbook component of Cedar Grove Gaming, imported by producer 1200.

WHY THIS EXISTS
    The owner delivered a hash-pinned online sports package on 2026-09-24
    (`online_sports_2026-09-24`: 1,247 regulator monthly rows, 293 secondary
    monthly rows, 6 annual-only rows, 39 series-to-tribe relationship rows).
    The integration review asks that it enter the EXISTING Gaming producer
    (1200) rather than a new numbered pipeline, and that it never be appended
    to NIGC regional revenue. Its hazards are specific:

    * handle (wagers) is not revenue, and gross / adjusted / taxable revenue,
      promotions, excise and state payments are different measures;
    * the Maine Caesars report is ONE total for three tribes; the New Jersey
      Hard Rock casino-license aggregate overlaps the Hard Rock Bet brand
      series; Cedar's older digital_gaming_revenue already holds most of the
      Michigan and Connecticut months - each of these double counts if copied;
    * monthly and annual-only rows are different grains;
    * the 293 secondary rows (PlayAZ / PlayNJ) and the Arkansas Business annual
      figures are corroboration, not regulator observations;
    * one Pennsylvania row (Mohegan, December 2019) is published with
      components that do not reconcile.

    So the package becomes four component tables with one grain each: the
    reported unit (series) once, its financial observations once, typed
    unit-to-entity relationships that never carry money, and machine-readable
    coverage gaps. The shared total lives on the unit; nothing is allocated.

INPUTS
    The package is outside the Cedar input root. Its location comes from
    `--online-sports-root` / CEDAR_GAMING_ONLINE_SPORTS_ROOT (default: the
    governed unpack under ~/cedar-grove-gaming-work/raw). Every file read is
    receipted under a path RELATIVE to the Cedar input root (e.g.
    `../../cedar-grove-gaming-work/raw/...`), so the receipt carries no
    absolute path, is identical for any output root, and build.py's candidate
    runner re-verifies it as `input_root / path` without a code change. Every
    bundled raw report cited by a financial row is re-hashed against the row's
    source_sha256, and every package file against the zip content manifest.

MONEY
    Values are carried as the package's exact decimal strings. They are
    checked with decimal.Decimal and never pass through float. Blank stays
    blank (unreported / not applicable / grouped / not extracted), never 0;
    published zeros and negatives are kept.
"""
from __future__ import annotations

import calendar
import csv
import hashlib
import io
import os
import re
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse

import gaming_grove as gg

PACKAGE_LABEL = "online_sports_2026-09-24"
DEFAULT_PACKAGE_ROOT = Path(os.environ.get(
    "CEDAR_GAMING_ONLINE_SPORTS_ROOT",
    str(Path.home() / "cedar-grove-gaming-work" / "raw" / PACKAGE_LABEL / "unpacked" / "tribal_sports")))

T_UNITS = "gaming_online_sportsbook_units.csv"
T_FOB = "gaming_online_sportsbook_financials.csv"
T_REL = "gaming_online_sportsbook_relationships.csv"
T_GAP = "gaming_coverage_gaps.csv"

# The package's own release statistics; the build refuses if it cannot
# reproduce them from the row files.
EXPECTED = {"primary_monthly_rows": 1247, "secondary_monthly_rows": 293, "annual_only_rows": 6,
            "tribes_linked_to_any_financial_data": 31, "tribes_linked_to_primary_monthly": 20,
            "financial_states": 10}

# ------------------------------------------------------------------ measures
# (column, measure_kind). Kinds are semantic classes; a kind in REVENUE_KINDS
# is a revenue concept. Handle is WAGERS and is never a revenue kind.
MEASURES = [
    ("handle_usd", "wagers"),
    ("payouts_usd", "payouts"),
    ("voided_wagers_usd", "wager_adjustment"),
    ("resettlements_usd", "wager_adjustment"),
    ("other_adjustments_usd", "wager_adjustment"),
    ("gross_revenue_usd", "gross_gaming_revenue"),
    ("federal_excise_tax_usd", "federal_excise_tax"),
    ("unadjusted_revenue_usd", "revenue_after_federal_excise"),
    ("promotional_credits_usd", "promotional_credits_reported"),
    ("promotional_deduction_usd", "promotional_deduction_allowed"),
    ("adjusted_revenue_usd", "adjusted_gaming_revenue"),
    ("taxable_revenue_usd", "taxable_gaming_revenue"),
    ("state_payment_usd", "tax_or_payment_to_state"),
    ("local_payment_usd", "tax_or_payment_to_local_government"),
    ("per_wager_tax_usd", "per_wager_tax"),
    ("source_revenue_usd", "secondary_source_revenue_unreconciled"),
]
MEASURE_COLUMNS = [c for c, _ in MEASURES]
MEASURE_KIND = dict(MEASURES)
REVENUE_KINDS = {"gross_gaming_revenue", "revenue_after_federal_excise", "adjusted_gaming_revenue",
                 "taxable_gaming_revenue", "secondary_source_revenue_unreconciled"}
MEASURE_TEXT = {
    "handle_usd": "WAGERS (handle) under the source's timing convention, exact source decimal string. NOT revenue, deposits or bettor spending",
    "payouts_usd": "Winnings paid to bettors as published (exact decimal string)",
    "voided_wagers_usd": "Voided / cancelled wagers as published (exact decimal string)",
    "resettlements_usd": "Resettlements as published (Connecticut; exact decimal string)",
    "other_adjustments_usd": "Explicit printed adjustment (Maine); blank is not a reported zero",
    "gross_revenue_usd": "Gross gaming revenue under the jurisdiction's definition (see revenue_definition_id); not tribal income",
    "federal_excise_tax_usd": "Federal wagering excise tax as published",
    "unadjusted_revenue_usd": "Revenue after federal excise, before promotional deduction (Connecticut 'Unadjusted Monthly Gaming Revenue')",
    "promotional_credits_usd": "Promotional credits reported (may not be deductible)",
    "promotional_deduction_usd": "Promotional amount actually deducted in the source report",
    "adjusted_revenue_usd": "Jurisdiction-specific adjusted revenue; not comparable across jurisdictions without revenue_definition_id; not tribal profit",
    "taxable_revenue_usd": "Source tax base (taxable revenue)",
    "state_payment_usd": "Tax/payment to the STATE as published; not a payment to a tribe",
    "local_payment_usd": "Tax/payment to local government as published",
    "per_wager_tax_usd": "Illinois per-wager tax, separate from state_payment_usd",
    "source_revenue_usd": "Secondary publisher's revenue figure under its own unreconciled definition (PlayAZ / PlayNJ / Arkansas Business); never mapped to gross or adjusted",
}
_DECIMAL_RE = re.compile(r"^-?\d+(?:\.\d+)?$")

SOURCE_CLASSES = {"regulator_official", "secondary_corroboration", "official_annual"}
PERIOD_TYPES = {"monthly", "annual"}
UNIT_TYPES = {"tribal_license", "tribal_master_license", "casino_online_license", "brand",
              "operator", "shared_tribal_report", "license_aggregate", "state_aggregate"}
GRAIN_TO_UNIT = {
    "tribal_license": "tribal_license",
    "tribal_master_license": "tribal_master_license",
    "tribally_owned_casino_online_license": "casino_online_license",
    "three_tribe_group": "shared_tribal_report",
    "multi_brand_license_aggregate": "license_aggregate",
    "tribally_owned_online_operator": "operator",
    "online_operator_via_master_license": "operator",
}
# online_operator is a brand in NJ (Hard Rock Bet brand tables) and an operator
# row elsewhere (IN named HR online row, OH Type A online operator).
BRAND_SERIES = {"NJ_hardrock"}

# Declared overlaps (package README, "Structure and joins"): the NJ Hard Rock
# casino-license aggregate includes the Hard Rock Bet brand; never add both.
OVERLAPPING_UNITS = {
    ("NJ_license_seminole", "NJ_hardrock"):
        "Hard Rock Atlantic City online license aggregate (secondary) includes the Hard Rock Bet brand series "
        "(regulator); same month is never additive (package README, Structure and joins)",
}

# Package relationship vocabulary -> gaming_grove.RELATIONSHIP_TYPES. The
# package term is kept verbatim beside it.
REL_MAP = {
    "tribal_license_or_owned_licensee": None,          # decided by unit type below
    "tribally_affiliated_operator": "affiliate",
    "member_of_published_three_tribe_group": "reported_for",
    "tribal_market_access_partner": "licensed_to",
    "historical_minority_interest": "affiliate",
    "tribally_affiliated_casino_license": "affiliate",
    "affiliated_platform_provider": "affiliate",
}
# Only these can carry a unit's whole total to ONE entity, and only when the
# unit has exactly one link (allocation_status single_entity).
CARRYING_RELATIONSHIPS = {"licensed_to", "reported_for"}
TRIBAL_GOVERNMENT_HOSTS = {"www.quapawtribe.com"}
SECONDARY_HOSTS = {"www.playaz.com", "www.playnj.com"}


class OnlineSportsError(gg.GamingContractError):
    pass


# ------------------------------------------------------------------ helpers
def _cols(spec):
    header = [c for c, _, _ in spec]
    if len(set(header)) != len(header):
        raise OnlineSportsError("duplicate column in spec")
    for c, r, _ in spec:
        if r not in gg.RIGHTS_CLASSES:
            raise OnlineSportsError(f"{c}: unknown rights class {r}")
    return header, {c: r for c, r, _ in spec}, {c: d for c, _, d in spec}


def _contract(spec, **kw):
    header, rights, desc = _cols(spec)
    c = {"required": [], "enums": {}, "dates": [], "intervals": [], "public_id_columns": [],
         "derived_ids": {}, "supersedes": [], "row_rights_column": ""}
    c.update(kw)
    c["field_rights"], c["field_descriptions"], c["header"] = rights, desc, header
    return c


def exact_decimal(value, where=""):
    """Validate a source money string WITHOUT converting it; '' stays ''."""
    v = value if value is not None else ""
    if v == "":
        return ""
    if v != v.strip() or not _DECIMAL_RE.match(v):
        raise OnlineSportsError(f"{where}: not a plain decimal string {value!r}")
    try:
        Decimal(v)
    except InvalidOperation as e:  # pragma: no cover - regex already guards
        raise OnlineSportsError(f"{where}: {value!r}") from e
    return v


def check_measure_semantics(measures=MEASURES):
    """Handle is wagers, never revenue; every revenue column is a revenue kind."""
    for col, kind in measures:
        if "handle" in col and kind in REVENUE_KINDS:
            raise OnlineSportsError(f"{col} labelled as revenue kind {kind}")
        if col.startswith("handle") and kind != "wagers":
            raise OnlineSportsError(f"{col} must be wagers, not {kind}")


def _month_bounds(ym):
    y, m = int(ym[:4]), int(ym[5:7])
    return f"{ym}-01", f"{ym}-{calendar.monthrange(y, m)[1]:02d}"


def _prev_month(ym):
    y, m = int(ym[:4]), int(ym[5:7])
    return f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"


def _host(url):
    try:
        return (urlparse(url.strip()).hostname or "").lower()
    except ValueError:
        return ""


def row_rights(source_class, url):
    """Regulator rows are public_official only if the cited URL is a
    government publication; secondary rows are never public."""
    if source_class == "secondary_corroboration":
        return "secondary_corroboration"
    return "public_official" if _host(url).endswith(".gov") else "withheld_unverified"


def evidence_rights(urls):
    hosts = [_host(u) for u in urls.split("|") if u.strip()]
    if any(h.endswith(".gov") or h in TRIBAL_GOVERNMENT_HOSTS for h in hosts):
        return "public_official"
    if hosts and all(h in SECONDARY_HOSTS for h in hosts):
        return "secondary_corroboration"
    return "public_first_party" if hosts else "withheld_unverified"


def _pub(rights):
    if rights in gg.PUBLIC_RIGHTS:
        return "public"
    return "source_limited" if rights == "secondary_corroboration" else "withheld"


# ------------------------------------------------------------------ package reader
class Package:
    """Read package files with receipts relative to the Cedar input root."""

    def __init__(self, root, inputs: gg.Inputs):
        self.root = Path(root).resolve()
        self.inputs = inputs
        self.present = (self.root / "data" / "monthly_online_sports.csv").is_file()
        self.zip_hashes = {}
        zm = self.root.parent / "_ZIP_CONTENT_MANIFEST.csv"
        if self.present and zm.is_file():
            raw = self._raw(zm, "_ZIP_CONTENT_MANIFEST.csv")
            for r in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline="")):
                self.zip_hashes[r["path"]] = r["sha256"]
        self.zip_checked = 0

    def key(self, path: Path, label: str) -> str:
        try:
            return Path(os.path.relpath(path, self.inputs.root)).as_posix()
        except ValueError:          # another drive: no relative path exists
            return f"{PACKAGE_LABEL}/{label}"

    def _raw(self, path: Path, label: str, expected_sha=None):
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        rel = self.key(path, label)
        self.inputs.receipts[rel] = {"path": rel, "label": f"{PACKAGE_LABEL}/{label}", "sha256": digest,
                                     "bytes": len(raw), "status": "READ"}
        if expected_sha is not None and digest != expected_sha:
            raise OnlineSportsError(f"REFUSED: {label} sha256 {digest} != recorded {expected_sha}")
        zkey = "tribal_sports/" + label
        if zkey in self.zip_hashes:
            if self.zip_hashes[zkey] != digest:
                raise OnlineSportsError(f"REFUSED: {label} differs from the zip content manifest")
            self.zip_checked += 1
        return raw

    def csv(self, label):
        raw = self._raw(self.root / label, label)
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig", errors="strict"), newline=""))
        rows = list(reader)
        self.inputs.receipts[self.key(self.root / label, label)]["rows"] = len(rows)
        return rows

    def verify(self, label, expected_sha):
        self._raw(self.root / label, label, expected_sha)


# ------------------------------------------------------------------ contracts
UNIT_SPEC = [
    ("sportsbook_unit_id", "public_derived", "Registered source-series ID (CEDAR-SRC, Gaming block) bound to the stable key (package, state, source series_id)"),
    ("source_package", "public_official", "Delivered package label (online_sports_2026-09-24)"),
    ("source_series_id", "public_official", "Package series_id, preserved (a local series key, not an entity id)"),
    ("jurisdiction", "public_official", "State whose regulator (or secondary publisher) reports the unit"),
    ("reported_unit_type", "public_official", "What one series is: tribal_license, tribal_master_license, casino_online_license, brand, operator, shared_tribal_report, license_aggregate, state_aggregate"),
    ("source_reporting_grain", "public_official", "Package reporting_grain, verbatim"),
    ("reporting_entity_as_reported", "public_official", "Licensee / operator / report-group label as the source prints it"),
    ("platform_labels_as_reported", "public_official", "Distinct platform/brand labels printed for the unit (pipe-separated); may be stale, not dated partnership history"),
    ("property_named_in_source", "public_official", "Casino property the source names for the unit, if any (text; not an identity claim)"),
    ("gaming_facility_id", "public_derived", "Existing CEDAR-PLACE ID of the property the source names, only when 1201's facility tables resolve it unambiguously (see resolve_unit_facilities); blank = unresolved"),
    ("facility_link_status", "public_official", "no_property_named, property_named_unresolved (named property not resolved unambiguously) or property_named_resolved"),
    ("evidence_tier", "public_official", "Package evidence tier (primary_regulator / secondary_compilation)"),
    ("source_class", "public_official", "regulator_official, official_annual or secondary_corroboration"),
    ("period_type", "public_official", "monthly or annual; a unit reports one grain"),
    ("first_period", "public_official", "First collected period (YYYY-MM or YYYY)"),
    ("last_period", "public_official", "Last collected period (YYYY-MM or YYYY)"),
    ("record_count", "public_official", "Financial observations for the unit in this build"),
    ("reported_zero_months", "public_official", "Months published as zero activity (zero does not prove continuing operation)"),
    ("internal_missing_months", "public_official", "Months missing inside the collected window (package series_coverage)"),
    ("handle_available", "public_official", "yes/no: the unit publishes handle"),
    ("revenue_definition_id", "public_official", "Key into the package revenue_definitions (jurisdiction definition of gross/adjusted/taxable)"),
    ("revenue_definition_interpretation", "public_official", "Package interpretation of the jurisdiction's revenue labels, verbatim"),
    ("shared_report", "public_official", "yes when one published total covers several Native entities (never allocated)"),
    ("linked_entity_count", "public_derived", "Number of distinct cedar_uid linked by relationships (context, never a divisor)"),
    ("allocation_status", "public_official", "single_entity only when one entity holds/reports the whole unit; otherwise not_allocated"),
    ("nonadditive_with_unit_ids", "public_derived", "Units whose same-period values overlap this unit's (pipe-separated sportsbook_unit_id values); never add them"),
    ("nonadditive_reason", "public_official", "Why the overlap exists"),
    ("source_url", "public_official", "Series source URL (package series_coverage)"),
    ("source_notes", "public_official", "Package series note, verbatim"),
    ("rights_class", "public_official", "Row-level rights class"),
    ("publication_status", "public_official", "Row-level publication status"),
]
UNIT_CONTRACT = _contract(
    UNIT_SPEC,
    grain="One reported online-sportsbook unit: a single reporting series (tribal license, master license, casino online license, brand, operator row, shared three-tribe report or multi-brand license aggregate) in one jurisdiction as one source publishes it.",
    primary_key=["sportsbook_unit_id"],
    required=["source_series_id", "jurisdiction", "reported_unit_type", "source_class", "period_type"],
    enums={"reported_unit_type": UNIT_TYPES, "source_class": SOURCE_CLASSES, "period_type": PERIOD_TYPES,
           "handle_available": {"yes", "no"}, "shared_report": {"yes", "no"},
           "allocation_status": gg.ALLOCATION_STATUSES,
           "facility_link_status": {"no_property_named", "property_named_unresolved", "property_named_resolved"},
           "publication_status": gg.PUBLICATION_STATUSES},
    dates=["first_period", "last_period"],
    intervals=[("first_period", "last_period")],
    public_id_columns=["gaming_facility_id"],
    derived_ids={"sportsbook_unit_id": "GSBK"},
    nonadditive_note=("A unit is a reporting series, not a tribe, facility or owner. Units flagged in "
                      "nonadditive_with_unit_ids overlap for the same period. A shared_report unit's total is "
                      "stored once and is never divided or copied to its linked entities."),
    publication_status="internal",
    supersedes=[],
    row_rights_column="rights_class",
)

FOB_SPEC = [
    ("financial_observation_id", "public_derived", "Registered observation ID (CEDAR-OBS, Gaming block) bound to the stable key (package, source record_id, revision_label)"),
    ("sportsbook_unit_id", "public_derived", "sportsbook_unit_id (CEDAR-SRC) of the reported unit (join to units; entities only via relationships)"),
    ("source_package", "public_official", "Delivered package label"),
    ("source_record_id", "public_official", "Package record_id, preserved"),
    ("source_series_id", "public_official", "Package series_id, preserved"),
    ("source_table", "public_official", "Package file the row came from (monthly_online_sports / supplementary_monthly / annual_only)"),
    ("jurisdiction", "public_official", "State"),
    ("period_type", "public_official", "monthly or annual - distinct grains, never summed together"),
    ("period_start", "public_official", "Period start (ISO date)"),
    ("period_end", "public_official", "Period end (ISO date)"),
    ("period_label", "public_official", "Period as the package labels it (YYYY-MM or YYYY)"),
    ("period_convention", "public_official", "calendar_month or calendar_year (package: reporting month, not publication month)"),
    ("partial_period_flag", "public_official", "no, first_collected_month_of_series (launch-month partiality unknown) or partial_launch_year"),
    ("revision_label", "public_official", "Which publication vintage the value is: as_published, later_publication_prior_year_comparative, or earlier_intact_publication_preferred_over_excluded_revision"),
    ("revision_note", "public_official", "Revision context from package source_revisions / locator"),
    ("record_status", "public_official", "reported or reported_zero_activity (zero does not prove continuing operation)"),
    ("currency", "public_official", "USD, nominal"),
] + [(c, "secondary_corroboration" if c == "source_revenue_usd" else "public_official", MEASURE_TEXT[c])
     for c in MEASURE_COLUMNS] + [
    ("gross_revenue_method", "public_official", "reported, or Maine's explicit derivation (handle + adjustments - voids - payouts)"),
    ("revenue_definition_id", "public_official", "Key into package revenue_definitions.csv"),
    ("revenue_definition_gross_label", "public_official", "Source label mapped to gross_revenue_usd for this definition"),
    ("revenue_definition_adjusted_label", "public_official", "Source label mapped to adjusted/taxable revenue for this definition"),
    ("source_metric_labels", "public_official", "Original source labels per normalised field from metric_evidence (field:label, pipe-separated)"),
    ("source_value_precision", "public_official", "Precision as published where the package states it (whole USD, USD millions rounded to 0.01 million ...)"),
    ("source_class", "public_official", "regulator_official, official_annual or secondary_corroboration"),
    ("source_url", "public_official", "Source URL"),
    ("bundled_file_path", "public_official", "Raw report inside the package (e.g. raw/mi_2024.xlsx)"),
    ("raw_sha256", "public_official", "SHA-256 of the bundled raw report (re-verified in this build)"),
    ("source_locator", "public_official", "Sheet/cell, CSV row, PDF page/section or HTML table/row"),
    ("source_publication_date", "public_official", "Report publication date; blank = not recorded by the package"),
    ("retrieved_date", "public_official", "Retrieval date (ISO)"),
    ("retrieved_at", "public_official", "Retrieval timestamp as recorded by the package"),
    ("qa_status", "public_official", "Package extraction/reconciliation disposition"),
    ("source_notes", "public_official", "Package row note, verbatim"),
    ("additivity", "public_official", "additive_across_months_within_unit_and_measure (monthly) or annual_only_never_mixed_with_monthly"),
    ("nonadditive_with_observation_ids", "public_derived", "financial_observation_id values of overlapping same-period observations (NJ license aggregate vs brand); never add both"),
    ("nonadditive_reason", "public_official", "Why the overlap exists"),
    ("existing_overlap_source_record_ids", "public_derived", "digital_gaming_revenue revenue_ids (source_record_id in gaming_reported_revenue_observations / gaming_government_payments) describing the same state, month and licensee; never add both"),
    ("existing_overlap_value_check", "public_derived", "none, all_compared_values_equal, or differs:<metrics> between this row and the overlapping digital rows"),
    ("discrepancy_flag", "public_official", "yes only on a row whose published components do not reconcile"),
    ("discrepancy_measure", "public_official", "Measure whose published value disagrees with its published components"),
    ("discrepancy_formula", "public_official", "Identity checked"),
    ("discrepancy_published_value", "public_official", "Published value (exact)"),
    ("discrepancy_calculated_value", "public_derived", "Value calculated from published components with decimal arithmetic"),
    ("discrepancy_difference", "public_derived", "calculated minus published"),
    ("discrepancy_citation", "public_official", "Source file, locator and URL of the disagreement"),
    ("discrepancy_disposition", "public_official", "What was done: published values retained, row qualified, no correction inferred"),
    ("rights_class", "public_official", "Row-level rights class (secondary rows are secondary_corroboration, never public)"),
    ("publication_status", "public_official", "Row-level publication status"),
]
FOB_CONTRACT = _contract(
    FOB_SPEC,
    grain="One financial observation: one reported online-sportsbook unit x one period (monthly calendar month, or annual calendar year for annual-only sources) x one publication revision, with each financial measure in its own column.",
    primary_key=["financial_observation_id"],
    required=["sportsbook_unit_id", "source_record_id", "period_type", "period_start", "period_end",
              "revision_label", "source_class", "rights_class"],
    enums={"period_type": PERIOD_TYPES, "source_class": SOURCE_CLASSES,
           "period_convention": {"calendar_month", "calendar_year"},
           "partial_period_flag": {"no", "first_collected_month_of_series", "partial_launch_year"},
           "revision_label": {"as_published", "later_publication_prior_year_comparative",
                              "earlier_intact_publication_preferred_over_excluded_revision"},
           "record_status": {"reported", "reported_zero_activity"}, "currency": {"USD"},
           "additivity": {"additive_across_months_within_unit_and_measure",
                          "annual_only_never_mixed_with_monthly"},
           "discrepancy_flag": {"yes", "no"},
           "publication_status": gg.PUBLICATION_STATUSES},
    dates=["period_start", "period_end", "source_publication_date", "retrieved_date"],
    intervals=[("period_start", "period_end")],
    derived_ids={"financial_observation_id": "GFOB", "sportsbook_unit_id": "GSBK"},
    nonadditive_note=("Measures are never interchangeable: handle is wagers, not revenue; gross, adjusted, taxable "
                      "and source_revenue_usd follow different jurisdiction definitions; state payments are paid TO "
                      "the state. Add only one measure, one unit set, one period_type; never add monthly to annual; "
                      "never add rows listed in nonadditive_with_observation_ids or existing_overlap_source_record_ids "
                      "to their counterparts; never add online sportsbook values to NIGC GGR or physical casino "
                      "revenue. Nothing here is tribal retained income."),
    publication_status="internal",
    supersedes=[{"table": "digital_gaming_revenue.csv",
                 "role": "cross-referenced: MI/CT online sportsbook months overlap and are flagged nonadditive (both kept)"}],
    row_rights_column="rights_class",
)

REL_SPEC = [
    ("relationship_id", "public_derived", "Registered relationship ID (CEDAR-REL, Gaming block) bound to the stable key (package, series_id, cedar_uid, package relationship type, valid_from)"),
    ("sportsbook_unit_id", "public_derived", "sportsbook_unit_id (CEDAR-SRC) of the reported unit"),
    ("source_series_id", "public_official", "Package series_id"),
    ("jurisdiction", "public_official", "State"),
    ("cedar_uid", "public_derived", "Native entity (checksum-valid CE id present and active in the current identity register)"),
    ("entity_name_in_package", "public_official", "Canonical name the package pinned for the cedar_uid (Cedar entity-names blob 2bf4b58e)"),
    ("gaming_facility_id", "public_derived", "Facility id only via 1201's crosswalk when the source names a property; blank = unresolved"),
    ("relationship_type", "public_official", "gaming_grove relationship vocabulary: licensed_to, reported_for, affiliate ..."),
    ("source_relationship_type", "public_official", "Package relationship_type, verbatim"),
    ("relationship_status", "public_official", "Package relationship_status (verified_named_relationship / secondary_named_licensee)"),
    ("effective_from", "public_official", "Start of the collected relationship window (YYYY-MM), not contractual history"),
    ("effective_through", "public_official", "End of the collected relationship window (YYYY-MM)"),
    ("effective_dates_basis", "public_official", "What the dates mean"),
    ("allocation_status", "public_official", "single_entity (one entity holds/reports the whole unit) or not_allocated; never source_allocated here"),
    ("financial_allocation_permitted", "public_official", "no: the package permits no allocation of unit totals to entities"),
    ("ownership_share_as_stated", "public_official", "Ownership share stated by an authoritative source (holding-company interest), never a revenue share"),
    ("allocation_weight", "public_official", "Always blank: no source allocation exists"),
    ("evidence_url", "public_official", "Evidence URL(s) the package cites (pipe-separated)"),
    ("evidence_rights_basis", "public_official", "Rights of the evidence: public_official (.gov / tribal government), public_first_party (operator self-description), secondary_corroboration"),
    ("confidence", "public_official", "high (official evidence), medium (first-party self-description), low (secondary)"),
    ("review_status", "public_official", "source_asserted: stated by the package, not independently re-reviewed by Cedar"),
    ("source_notes", "public_official", "Package relationship note, verbatim"),
    ("rights_class", "public_official", "Row-level rights class"),
    ("publication_status", "public_official", "Row-level publication status"),
]
REL_CONTRACT = _contract(
    REL_SPEC,
    grain="One typed relationship between one reported online-sportsbook unit and one Native entity over the package's collected window; carries no money.",
    primary_key=["relationship_id"],
    required=["sportsbook_unit_id", "cedar_uid", "relationship_type", "allocation_status", "review_status"],
    enums={"relationship_type": gg.RELATIONSHIP_TYPES, "allocation_status": gg.ALLOCATION_STATUSES,
           "review_status": gg.REVIEW_STATUSES, "confidence": gg.CONFIDENCE,
           "financial_allocation_permitted": {"no"},
           "evidence_rights_basis": {"public_official", "public_first_party", "secondary_corroboration",
                                     "withheld_unverified"},
           "publication_status": gg.PUBLICATION_STATUSES},
    dates=["effective_from", "effective_through"],
    intervals=[("effective_from", "effective_through")],
    public_id_columns=["gaming_facility_id"],
    derived_ids={"relationship_id": "GREL", "sportsbook_unit_id": "GSBK"},
    nonadditive_note=("A relationship is context, not an allocation. Only allocation_status=single_entity links may "
                      "carry a unit's total to an entity; shared reports, affiliates, platform providers and "
                      "minority interests are not_allocated and must not be summed by entity."),
    publication_status="internal",
    supersedes=[],
    row_rights_column="rights_class",
)

GAP_SPEC = [
    ("coverage_gap_id", "public_derived", "Natural composite key (no minted ID): gap_source|component_table|state|cedar_uid|subject|source_status"),
    ("gap_source", "public_official", "online_sports_package, online_sports_package_series_coverage, online_sports_package_validation, or nigc_regional_revenue"),
    ("component_table", "public_official", "Gaming component table the gap belongs to"),
    ("state", "public_official", "State (MULTI = national/multi-state; blank = national NIGC)"),
    ("cedar_uid", "public_derived", "Native entity the gap concerns, if any (CE id)"),
    ("entity_name_in_source", "public_official", "Name as the gap source gives it"),
    ("subject", "public_official", "Series, report or figure that is missing"),
    ("measure", "public_official", "Measure(s) missing"),
    ("expected_frequency", "public_official", "monthly, annual or fiscal_year, or not_applicable"),
    ("known_start", "public_official", "Earliest known activity / lead (ISO, may be year or month)"),
    ("known_end", "public_official", "Known end of activity, if any"),
    ("missing_from", "public_official", "First missing period (ISO)"),
    ("missing_through", "public_official", "Last missing period (ISO); blank = open through the build's as-of"),
    ("missing_periods", "public_official", "Human-readable missing period statement"),
    ("source_status", "public_official", "Status code of the source (blocked, not_found, not_printed ...)"),
    ("reason", "public_official", "Why the data are absent"),
    ("next_action", "public_official", "What would close the gap"),
    ("evidence_url", "public_official", "Where the gap was established"),
    ("affected_record_id", "public_derived", "Observation id the gap qualifies, when it concerns one row"),
    ("rights_class", "public_official", "Row-level rights class"),
    ("publication_status", "public_official", "Row-level publication status"),
]
GAP_CONTRACT = _contract(
    GAP_SPEC,
    grain="One machine-readable coverage gap or qualified observation: one missing series, figure or period range (or one non-reconciling published row) for one subject, as established by a named source.",
    primary_key=["coverage_gap_id"],
    required=["gap_source", "component_table", "subject", "source_status", "reason"],
    enums={"expected_frequency": {"monthly", "annual", "fiscal_year", "not_applicable"},
           "publication_status": gg.PUBLICATION_STATUSES},
    dates=["known_start", "known_end", "missing_from", "missing_through"],
    intervals=[("missing_from", "missing_through")],
    nonadditive_note="A gap is an absence, never a zero; unlisted tribes and missing periods are not zero activity.",
    publication_status="internal",
    supersedes=[],
    row_rights_column="rights_class",
)

CONTRACTS = {T_UNITS: UNIT_CONTRACT, T_FOB: FOB_CONTRACT, T_REL: REL_CONTRACT, T_GAP: GAP_CONTRACT}
for _t, _c in CONTRACTS.items():
    _missing = [c for c in _c["header"] if c not in _c["field_rights"] or c not in _c["field_descriptions"]]
    assert not _missing, (_t, _missing)
check_measure_semantics()


# ------------------------------------------------------------------ invariants
def check_financials(rows):
    """Refuse the violations the review names, on the built rows."""
    bad = []
    natural = Counter((r["sportsbook_unit_id"], r["period_type"], r["period_start"], r["revision_label"]) for r in rows)
    dup = [k for k, n in natural.items() if n > 1]
    if dup:
        bad.append(f"duplicate unit x period x revision {dup[:3]}")
    for r in rows:
        where = r["source_record_id"]
        for c in MEASURE_COLUMNS:
            exact_decimal(r.get(c, ""), f"{where}.{c}")
        if r["period_type"] == "monthly" and (r["period_start"][:7] != r["period_end"][:7] or len(r["period_label"]) != 7):
            bad.append(f"{where}: monthly row spans more than one month")
        if r["period_type"] == "annual" and (r["period_start"][5:] != "01-01" or r["period_end"][5:] != "12-31"):
            bad.append(f"{where}: annual row is not a whole year")
        if r["period_type"] == "annual" and r["additivity"] != "annual_only_never_mixed_with_monthly":
            bad.append(f"{where}: annual row marked additive with monthly")
        if r["source_class"] == "secondary_corroboration" and r["rights_class"] in gg.PUBLIC_RIGHTS:
            bad.append(f"{where}: secondary row promoted to public rights")
        if r["source_revenue_usd"] and r["rights_class"] in gg.PUBLIC_RIGHTS:
            bad.append(f"{where}: unreconciled secondary revenue on a public row")
        if (r["discrepancy_flag"] == "yes") != bool(r["discrepancy_measure"]):
            bad.append(f"{where}: discrepancy fields inconsistent")
    if bad:
        raise OnlineSportsError("REFUSED: " + "; ".join(bad[:8]))


def check_relationships(rels, units):
    """A shared total can never reach a tribe: single_entity only when the unit
    has exactly one link and it is a carrying relationship."""
    per_unit = Counter(r["sportsbook_unit_id"] for r in rels if r["relationship_type"] in CARRYING_RELATIONSHIPS)
    bad = []
    for r in rels:
        if r["allocation_status"] == "single_entity" and (
                per_unit[r["sportsbook_unit_id"]] != 1 or r["relationship_type"] not in CARRYING_RELATIONSHIPS):
            bad.append(r["relationship_id"])
        if r["allocation_weight"] or r["allocation_status"] == "source_allocated":
            bad.append(r["relationship_id"])
    shared = {u["sportsbook_unit_id"] for u in units if u["shared_report"] == "yes"}
    bad += [r["relationship_id"] for r in rels if r["sportsbook_unit_id"] in shared
            and r["allocation_status"] != "not_allocated"]
    if bad:
        raise OnlineSportsError(f"REFUSED: allocation violations {bad[:5]}")


def sum_units(financials, measure, period_type, unit_ids=None):
    """Decimal sum of ONE measure over ONE period_type. Refuses mixed grains and
    overlapping observations; blank is counted as missing, never as zero."""
    if period_type not in PERIOD_TYPES:
        raise OnlineSportsError(f"period_type {period_type!r}")
    if measure not in MEASURE_KIND:
        raise OnlineSportsError(f"unknown measure {measure!r}")
    rows = [r for r in financials if unit_ids is None or r["sportsbook_unit_id"] in unit_ids]
    if any(r["period_type"] != period_type for r in rows):
        raise OnlineSportsError("REFUSED: monthly and annual observations cannot be summed together")
    ids = {r["financial_observation_id"] for r in rows}
    for r in rows:
        clash = {x for x in r.get("nonadditive_with_observation_ids", "").split("|") if x} & ids
        if clash:
            raise OnlineSportsError(f"REFUSED: {r['financial_observation_id']} overlaps {sorted(clash)}")
    total, missing = Decimal(0), 0
    for r in rows:
        v = r.get(measure, "")
        if v == "":
            missing += 1
        else:
            total += Decimal(v)
    return total, missing


def entity_totals(financials, relationships, measure, period_type):
    """Totals by cedar_uid through single_entity links only. Units whose links
    are not_allocated (shared reports, affiliates) are returned untouched and
    never divided or copied to their entities."""
    units_by_uid, excluded = defaultdict(set), set()
    per_unit = defaultdict(set)
    for r in relationships:
        if r["relationship_type"] in CARRYING_RELATIONSHIPS:
            per_unit[r["sportsbook_unit_id"]].add(r["cedar_uid"])
    for r in relationships:
        if r["allocation_status"] == "single_entity":
            if len(per_unit[r["sportsbook_unit_id"]]) != 1:
                raise OnlineSportsError(f"REFUSED: single_entity unit {r['sportsbook_unit_id']} has several entities")
            units_by_uid[r["cedar_uid"]].add(r["sportsbook_unit_id"])
        else:
            excluded.add(r["sportsbook_unit_id"])
    out = {uid: sum_units(financials, measure, period_type, units)[0] for uid, units in sorted(units_by_uid.items())}
    return out, sorted(excluded - {u for s in units_by_uid.values() for u in s})


# ------------------------------------------------------------------ builders
def _unit_type(series_id, grain):
    if grain == "online_operator":
        return "brand" if series_id in BRAND_SERIES else "operator"
    return GRAIN_TO_UNIT[grain]


def _property_named(series_id, entity):
    """Only labels that literally name a casino property (no identity claim)."""
    m = re.search(r"\(([^)]*Casino[^)]*)\)", entity)
    if m:
        return m.group(1)
    if re.search(r"Atlantic City|Casino Rockford|CINCINNATI", entity, re.I):
        return entity.split(" - ")[0].split(" / ")[0]
    if series_id in ("PA_mohegan", "PA_poarch"):   # PA reports by licensed casino
        return entity
    return ""


_GENERIC_NAME_WORDS = {"casino", "hotel", "resort", "and", "the", "spa", "at", "llc", "inc"}
FACILITY_TABLES = ("gaming_grove_facilities.csv", "gaming_facility_names.csv", "gaming_facility_relationships.csv")


def _core_name(text):
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return " ".join(w for w in words if w not in _GENERIC_NAME_WORDS)


def load_facility_index(inputs: gg.Inputs, out_dir):
    """1201's facility authority, written earlier in the same components run:
    {(state, core name): {gaming_facility_id}} and {gaming_facility_id:
    {cedar_uid}}. None when 1201 has not run (standalone): no link is made
    rather than a private name match 1201 never saw. Receipted relative to the
    candidate root, like 1203's crosswalk read."""
    out_dir = Path(out_dir)
    data = {}
    for table in FACILITY_TABLES:
        p = out_dir / table
        label = "components/" + table
        if not p.is_file():
            inputs.receipts[label] = {"path": label, "scope": "candidate_component", "status": "ABSENT"}
            return None
        raw = p.read_bytes()
        rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline="")))
        inputs.receipts[label] = {"path": label, "scope": "candidate_component", "status": "READ",
                                  "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "rows": len(rows)}
        data[table] = rows
    state = {r["gaming_facility_id"]: r["state"] for r in data["gaming_grove_facilities.csv"]
             if r["record_status"] == "property"}
    by_name = defaultdict(set)
    for r in data["gaming_facility_names.csv"]:
        fid = r["gaming_facility_id"]
        if fid in state and state[fid]:
            by_name[(state[fid], _core_name(r["name"]))].add(fid)
    uids = defaultdict(set)
    for r in data["gaming_facility_relationships.csv"]:
        if r["cedar_uid"]:
            uids[r["gaming_facility_id"]].add(r["cedar_uid"])
    return {"by_name": by_name, "uids": uids}


def resolve_unit_facilities(units, rels, index, withheld):
    """Link a unit to the existing CEDAR-PLACE of the property its source names,
    ONLY when unambiguous: exactly one 1201 facility in the unit's
    jurisdiction has a name whose core words equal the named property's, and
    (when the unit has linked Native entities) that facility is related to
    one of them. Everything else stays unresolved; nothing is guessed."""
    linked = defaultdict(set)
    for r in rels:
        linked[r["sportsbook_unit_id"]].add(r["cedar_uid"])
    for u in units:
        prop = u["property_named_in_source"]
        if not prop:
            continue
        hits = set(index["by_name"].get((u["jurisdiction"], _core_name(prop)), ())) if index else set()
        if hits and linked[u["sportsbook_unit_id"]]:
            hits = {f for f in hits if index["uids"].get(f, set()) & linked[u["sportsbook_unit_id"]]}
        if len(hits) == 1:
            u["gaming_facility_id"] = gg.facility_id_for(hits.pop())
            u["facility_link_status"] = "property_named_resolved"
            withheld["unit_property_named_facility_resolved"] += 1
        else:
            withheld["unit_property_named_facility_unresolved"] += 1


def build_component(inputs: gg.Inputs, package_root, digital_rows, extra_gaps=(), expected=None,
                    facility_index=None):
    """Return {table: rows} plus coverage/withheld/notes and digital overlap map."""
    pkg = Package(package_root, inputs)
    notes, withheld = [], Counter()
    if not pkg.present:
        notes.append(f"online sports package ABSENT at the configured root: component tables are empty "
                     f"(set CEDAR_GAMING_ONLINE_SPORTS_ROOT / --online-sports-root)")
        inputs.receipts[f"{PACKAGE_LABEL}/data/monthly_online_sports.csv"] = {
            "path": f"{PACKAGE_LABEL}/data/monthly_online_sports.csv", "status": "ABSENT"}
        gaps = [gap_row(**g) for g in extra_gaps]
        return {T_UNITS: [], T_FOB: [], T_REL: [], T_GAP: gaps}, {"package": "ABSENT"}, withheld, notes, {}

    monthly = pkg.csv("data/monthly_online_sports.csv")
    supp = pkg.csv("data/supplementary_monthly.csv")
    annual = pkg.csv("data/annual_only.csv")
    rels_src = pkg.csv("data/tribal_relationships.csv")
    gaps_src = pkg.csv("data/coverage_gaps.csv")
    revdefs = {r["revenue_definition_id"]: r for r in pkg.csv("data/revenue_definitions.csv")}
    series_cov = {r["series_id"]: r for r in pkg.csv("data/series_coverage.csv")}
    revisions = pkg.csv("data/source_revisions.csv")
    checks = pkg.csv("data/validation_checks.csv")
    evidence = pkg.csv("data/metric_evidence.csv")
    manifest = {r["file"]: r for r in pkg.csv("data/source_manifest.csv")}
    stats_raw = pkg._raw(pkg.root / "data" / "release_stats.json", "data/release_stats.json")
    import json
    stats = json.loads(stats_raw.decode("utf-8"))

    # ---- identity: every package cedar_uid against the CURRENT register
    _, register = inputs.read("data/spine/cedar_identity_register.csv")
    reg = {r["cedar_uid"]: r for r in register}
    pinned = (pkg.root / "raw" / "cedar_entity_names.csv")
    pinned_sha = hashlib.sha256(pinned.read_bytes()).hexdigest() if pinned.is_file() else ""
    if pinned.is_file():
        pkg._raw(pinned, "raw/cedar_entity_names.csv")
    current_names = inputs.path("data/spine/cedar_entity_names.csv")
    current_sha = ""
    if current_names.is_file():
        inputs.read("data/spine/cedar_entity_names.csv")
        current_sha = inputs.receipts["data/spine/cedar_entity_names.csv"]["sha256"]
    uids = sorted({r["cedar_uid"] for r in monthly + supp + annual + rels_src + gaps_src if r.get("cedar_uid")})
    uid_ok = {u: gg.is_ce_uid(u) and u in reg and reg[u]["register_status"].startswith("active") for u in uids}
    refused_uids = sorted(u for u, ok in uid_ok.items() if not ok)
    withheld["package_cedar_uid_refused_not_current_ce"] += len(refused_uids)
    pkg_names = {r["cedar_uid"]: r["canonical_name"] for r in gaps_src + rels_src if r.get("cedar_uid")}
    fr_name_diff = sorted(u for u, n in pkg_names.items()
                          if u in reg and n != reg[u]["federal_register_legal_name"])

    # ---- reproduce the package's reported counts (refuse if they drift)
    fin_series = {r["series_id"] for r in monthly + supp + annual}
    prim_series = {r["series_id"] for r in monthly}
    linked = {r["cedar_uid"] for r in rels_src if r["series_id"] in fin_series}
    linked_prim = {r["cedar_uid"] for r in rels_src if r["series_id"] in prim_series}
    states = sorted({r["state"] for r in monthly + supp + annual})
    reproduced = {"primary_monthly_rows": len(monthly), "secondary_monthly_rows": len(supp),
                  "annual_only_rows": len(annual), "tribes_linked_to_any_financial_data": len(linked),
                  "tribes_linked_to_primary_monthly": len(linked_prim), "financial_states": len(states)}
    expected = EXPECTED if expected is None else expected
    if reproduced != expected or any(stats.get(k) != v for k, v in reproduced.items() if k in stats):
        raise OnlineSportsError(f"REFUSED: package counts do not reproduce: {reproduced} vs {expected}")

    # ---- source hashes: every cited raw report re-hashed
    cited = {}
    for r in monthly + supp + annual:
        cited.setdefault(r["source_file"], set()).add(r["source_sha256"])
    for f, hs in sorted(cited.items()):
        if len(hs) != 1:
            raise OnlineSportsError(f"REFUSED: {f} cited with {len(hs)} different hashes")
        if manifest.get(f, {}).get("sha256") not in hs:
            raise OnlineSportsError(f"REFUSED: {f} hash disagrees with package source_manifest")
        pkg.verify(f, next(iter(hs)))

    # ---- units
    unit_id = {s: gg.derive_id("GSBK", PACKAGE_LABEL, sc["state"], s) for s, sc in series_cov.items()}
    if set(unit_id) != fin_series:
        raise OnlineSportsError("REFUSED: series_coverage and financial rows disagree on series")
    by_series = defaultdict(list)
    for tbl, rows in (("monthly_online_sports", monthly), ("supplementary_monthly", supp), ("annual_only", annual)):
        for r in rows:
            by_series[r["series_id"]].append((tbl, r))
    rel_by_series = defaultdict(list)
    for r in rels_src:
        rel_by_series[r["series_id"]].append(r)

    def source_class(tbl, r):
        if tbl == "supplementary_monthly" or r.get("source_type") == "secondary_compilation":
            return "secondary_corroboration"
        return "official_annual" if tbl == "annual_only" else "regulator_official"

    # relationships first (allocation_status feeds the unit row)
    rels = []
    def mapped_type(src_t, utype):
        if src_t == "tribal_license_or_owned_licensee":
            return "licensed_to" if utype in ("tribal_license", "tribal_master_license") else "affiliate"
        return REL_MAP.get(src_t) or "other_documented"

    for s in sorted(rel_by_series):
        links = rel_by_series[s]
        grain = series_cov[s]["reporting_grain"]
        utype = _unit_type(s, grain)
        carrying = [r for r in links if mapped_type(r["relationship_type"], utype) in CARRYING_RELATIONSHIPS]
        for r in links:
            src_t = r["relationship_type"]
            rtype = mapped_type(src_t, utype)
            if not uid_ok.get(r["cedar_uid"]):
                withheld["relationship_dropped_cedar_uid_not_current_ce"] += 1
                continue
            # one carrying link = the unit's whole total belongs to that licensee/reported party;
            # extra affiliate links (platform providers) never carry money
            single = len(carrying) == 1 and rtype in CARRYING_RELATIONSHIPS and utype != "shared_tribal_report"
            ev = evidence_rights(r["evidence_url"])
            rc = ev if ev in gg.PUBLIC_RIGHTS or ev == "secondary_corroboration" else "withheld_unverified"
            rels.append({
                "relationship_id": gg.derive_id("GREL", PACKAGE_LABEL, s, r["cedar_uid"], src_t, r["valid_from_month"]),
                "sportsbook_unit_id": unit_id[s], "source_series_id": s, "jurisdiction": r["state"],
                "cedar_uid": gg.checked_cedar_uid(r["cedar_uid"]), "entity_name_in_package": r["canonical_name"],
                "gaming_facility_id": "", "relationship_type": rtype, "source_relationship_type": src_t,
                "relationship_status": r["relationship_status"],
                "effective_from": r["valid_from_month"], "effective_through": r["valid_through_month"],
                "effective_dates_basis": "package collected window for this series; not the contractual or legal history",
                "allocation_status": "single_entity" if single else "not_allocated",
                "financial_allocation_permitted": "no" if r["financial_allocation_permitted"] == "False" else "INVALID",
                "ownership_share_as_stated": r["ownership_share_if_explicit"],
                "allocation_weight": r["allocation_weight"],
                "evidence_url": r["evidence_url"], "evidence_rights_basis": ev,
                "confidence": {"public_official": "high", "public_first_party": "medium"}.get(ev, "low"),
                "review_status": "source_asserted", "source_notes": r["notes"],
                "rights_class": rc, "publication_status": _pub(rc),
            })

    rel_units = defaultdict(list)
    for r in rels:
        rel_units[r["sportsbook_unit_id"]].append(r)
    overlaps = defaultdict(dict)
    for (a, b), why in OVERLAPPING_UNITS.items():
        if a in unit_id and b in unit_id:
            overlaps[a][b] = why
            overlaps[b][a] = why

    units = []
    for s in sorted(series_cov):
        sc = series_cov[s]
        rows = by_series[s]
        tbl0, r0 = rows[0]
        cls = source_class(tbl0, r0)
        utype = _unit_type(s, sc["reporting_grain"])
        url = sc["source_url"] or r0["source_url"]
        rc = row_rights(cls, url)
        prop = _property_named(s, sc["reporting_entity"])
        links = rel_units[unit_id[s]]
        units.append({
            "sportsbook_unit_id": unit_id[s], "source_package": PACKAGE_LABEL, "source_series_id": s,
            "jurisdiction": sc["state"], "reported_unit_type": utype, "source_reporting_grain": sc["reporting_grain"],
            "reporting_entity_as_reported": sc["reporting_entity"],
            "platform_labels_as_reported": "|".join(sorted({r["source_platform_label"] for _, r in rows
                                                            if r["source_platform_label"]})),
            "property_named_in_source": prop, "gaming_facility_id": "",
            "facility_link_status": "property_named_unresolved" if prop else "no_property_named",
            "evidence_tier": sc["evidence_tier"], "source_class": cls,
            "period_type": "annual" if tbl0 == "annual_only" else "monthly",
            "first_period": sc["first_period"], "last_period": sc["last_period"],
            "record_count": str(len(rows)), "reported_zero_months": sc["reported_zero_months"],
            "internal_missing_months": sc["internal_missing_months"],
            "handle_available": "yes" if sc["handle_available"] == "True" else "no",
            "revenue_definition_id": sc["revenue_definition_id"],
            "revenue_definition_interpretation": revdefs.get(sc["revenue_definition_id"], {}).get("interpretation", ""),
            "shared_report": "yes" if utype == "shared_tribal_report" else "no",
            "linked_entity_count": str(len({r["cedar_uid"] for r in links})),
            "allocation_status": "single_entity" if any(r["allocation_status"] == "single_entity" for r in links)
            else "not_allocated",
            "nonadditive_with_unit_ids": "|".join(sorted(unit_id[o] for o in overlaps.get(s, {}))),
            "nonadditive_reason": " | ".join(overlaps[s][o] for o in sorted(overlaps.get(s, {}))),
            "source_url": url, "source_notes": sc["notes"],
            "rights_class": rc, "publication_status": _pub(rc),
        })
    resolve_unit_facilities(units, rels, facility_index, withheld)
    check_relationships(rels, units)

    # ---- financial observations
    labels = defaultdict(list)
    ev_prec = Counter()
    by_rec = {}
    for r in monthly + supp + annual:
        by_rec[r["record_id"]] = r
    for e in evidence:
        labels[e["record_id"]].append(f"{e['normalized_field']}:{e['source_metric_label']}")
        # QA only: the package's 2-dp string equals the unrounded source cell (Decimal, no float)
        pr = by_rec.get(e["record_id"])
        if pr is not None and pr.get(e["normalized_field"], "") not in ("",) and e["source_value"]:
            try:
                same = Decimal(e["source_value"]).quantize(Decimal("0.01")) == Decimal(pr[e["normalized_field"]]).quantize(Decimal("0.01"))
            except InvalidOperation:
                same = False
            ev_prec["equal_at_cents" if same else "differs_at_cents"] += 1
    rev_years = {(r["state"], r["year"]): r for r in revisions}
    flagged = {c["locator"]: c for c in checks if c["status"] != "pass"}
    first_month = {s: min(r.get("month", "") for _, r in rows if r.get("month")) for s, rows in by_series.items()
                   if any(r.get("month") for _, r in rows)}
    launch_from = {}
    for r in rels_src:
        launch_from[r["series_id"]] = min(launch_from.get(r["series_id"], "9999"), r["valid_from_month"])

    fobs = []
    for s in sorted(by_series):
        for tbl, r in by_series[s]:
            cls = source_class(tbl, r)
            rc = row_rights(cls, r["source_url"])
            if tbl == "annual_only":
                ptype, start, end, label, conv = "annual", r["period_start"], r["period_end"], r["year"], "calendar_year"
                partial = "partial_launch_year" if launch_from.get(s, "")[:4] == r["year"] and \
                    launch_from[s] > f"{r['year']}-01" else "no"
            else:
                ptype, label, conv = "monthly", r["month"], "calendar_month"
                start, end = _month_bounds(r["month"])
                partial = "first_collected_month_of_series" if first_month.get(s) == r["month"] else "no"
            revision, rev_note = "as_published", ""
            if "prior-year comparative" in r["source_locator"]:
                revision = "later_publication_prior_year_comparative"
                rev_note = "Value taken from the later publication's prior-year comparative column (package rule: prefer the later publication for repeated months)"
            elif (r["state"], label[:4]) in rev_years:
                rv = rev_years[(r["state"], label[:4])]
                revision = "earlier_intact_publication_preferred_over_excluded_revision"
                rev_note = (f"{rv['newer_file']} restates {label[:4]} with {rv['newer_value']}; that version is excluded "
                            f"and the intact earlier publication is used ({r['source_file']})")
            disc = flagged.get(r["record_id"])
            d = {"discrepancy_flag": "no", "discrepancy_measure": "", "discrepancy_formula": "",
                 "discrepancy_published_value": "", "discrepancy_calculated_value": "",
                 "discrepancy_difference": "", "discrepancy_citation": "", "discrepancy_disposition": ""}
            if disc:
                d.update(pa_discrepancy(r, disc))
            row = {
                "financial_observation_id": gg.derive_id("GFOB", PACKAGE_LABEL, r["record_id"], revision),
                "sportsbook_unit_id": unit_id[s], "source_package": PACKAGE_LABEL,
                "source_record_id": r["record_id"], "source_series_id": s, "source_table": tbl,
                "jurisdiction": r["state"], "period_type": ptype, "period_start": start, "period_end": end,
                "period_label": label, "period_convention": conv, "partial_period_flag": partial,
                "revision_label": revision, "revision_note": rev_note,
                "record_status": r["record_status"], "currency": r["currency"],
            }
            for c in MEASURE_COLUMNS:
                row[c] = exact_decimal(r.get(c, ""), f"{r['record_id']}.{c}")
            rd = revdefs.get(r["revenue_definition_id"], {})
            row.update({
                "gross_revenue_method": r.get("gross_revenue_method", ""),
                "revenue_definition_id": r["revenue_definition_id"],
                "revenue_definition_gross_label": rd.get("gross_source_label", ""),
                "revenue_definition_adjusted_label": rd.get("adjusted_or_taxable_source_label", ""),
                "source_metric_labels": "|".join(sorted(labels.get(r["record_id"], []))),
                "source_value_precision": r.get("source_precision", ""),
                "source_class": cls, "source_url": r["source_url"], "bundled_file_path": r["source_file"],
                "raw_sha256": r["source_sha256"], "source_locator": r["source_locator"],
                "source_publication_date": "", "retrieved_date": r["retrieved_at"][:10],
                "retrieved_at": r["retrieved_at"], "qa_status": r["qa_status"], "source_notes": r["notes"],
                "additivity": "annual_only_never_mixed_with_monthly" if ptype == "annual"
                else "additive_across_months_within_unit_and_measure",
                "nonadditive_with_observation_ids": "", "nonadditive_reason": "",
                "existing_overlap_source_record_ids": "", "existing_overlap_value_check": "none",
                "rights_class": rc, "publication_status": _pub(rc),
            })
            row.update(d)
            fobs.append(row)
            if rc == "withheld_unverified":
                withheld["financial_regulator_row_non_government_url"] += 1

    # NJ overlap: same period in two overlapping units
    by_unit_period = {(r["sportsbook_unit_id"], r["period_type"], r["period_start"]): r for r in fobs}
    nj_pairs = 0
    for r in fobs:
        s = r["source_series_id"]
        for o, why in sorted(overlaps.get(s, {}).items()):
            other = by_unit_period.get((unit_id[o], r["period_type"], r["period_start"]))
            if other:
                r["nonadditive_with_observation_ids"] = "|".join(
                    sorted(set(filter(None, r["nonadditive_with_observation_ids"].split("|")))
                           | {other["financial_observation_id"]}))
                r["nonadditive_reason"] = why
                nj_pairs += 1

    # existing digital_gaming_revenue overlap (same state, month, licensee entity)
    digital_overlap = cross_reference_digital(fobs, rels, digital_rows)
    check_financials(fobs)

    # ---- coverage gaps
    gaps = [gap_row(**g) for g in package_gaps(gaps_src, series_cov, uid_ok)]
    for r in fobs:
        if r["discrepancy_flag"] == "yes":
            gaps.append(gap_row(
                gap_source="online_sports_package_validation", component_table=T_FOB, state=r["jurisdiction"],
                cedar_uid="", entity_name_in_source=r["source_series_id"],
                subject=f"{r['source_record_id']} {r['discrepancy_measure']}", measure=r["discrepancy_measure"],
                expected_frequency="monthly", known_start="", known_end="",
                missing_from="", missing_through="",
                missing_periods=f"qualified observation {r['period_label']} (not missing: published components do not reconcile)",
                source_status=r["qa_status"],
                reason=(f"published {r['discrepancy_published_value']} vs calculated {r['discrepancy_calculated_value']} "
                        f"({r['discrepancy_formula']}); difference {r['discrepancy_difference']}"),
                next_action="Confirm with the Pennsylvania Gaming Control Board whether the published December 2019 figures were later revised; keep published values meanwhile",
                evidence_url=r["source_url"], affected_record_id=r["financial_observation_id"]))
    gaps += [gap_row(**g) for g in extra_gaps]

    cov = {
        "package": PACKAGE_LABEL,
        "reproduced_counts": dict(reproduced, all_monthly_rows=len(monthly) + len(supp),
                                  total_financial_rows=len(monthly) + len(supp) + len(annual)),
        "financial_states": states,
        "financial_states_basis": ("10 = the 7 primary-monthly states (CT, IN, ME, MI, NJ, OH, PA) + AZ (secondary "
                                   "monthly only) + AR (secondary annual) + IL (official annual); NJ also has "
                                   "secondary monthly rows. Gap-only states (FL, NC, CO, TN, VA, IA) are not counted."),
        "tribes_basis": {
            "rule": "distinct cedar_uid in tribal_relationships whose series has financial rows",
            "via_primary_monthly": len(linked_prim),
            "added_by_secondary_monthly": len({r["cedar_uid"] for r in rels_src if r["series_id"] in {x["series_id"] for x in supp}} - linked_prim),
            "added_by_annual_only": len({r["cedar_uid"] for r in rels_src if r["series_id"] in {x["series_id"] for x in annual}}
                                        - linked_prim - {r["cedar_uid"] for r in rels_src if r["series_id"] in {x["series_id"] for x in supp}}),
            "linked_only_through_shared_report": sorted(
                {r["cedar_uid"] for r in rels_src if r["relationship_type"] == "member_of_published_three_tribe_group"}
                - {r["cedar_uid"] for r in rels_src if r["relationship_type"] != "member_of_published_three_tribe_group"}),
        },
        "cedar_uid": {"package_distinct": len(uids), "valid_current_active": sum(uid_ok.values()),
                      "refused": refused_uids,
                      "package_name_differs_from_register_federal_register_legal_name": fr_name_diff,
                      "pinned_entity_names_sha256": pinned_sha, "current_entity_names_sha256": current_sha,
                      "pinned_equals_current": bool(pinned_sha) and pinned_sha == current_sha},
        "source_files_rehashed": len(cited), "zip_manifest_files_verified": pkg.zip_checked,
        "metric_evidence_cents_check": dict(sorted(ev_prec.items())),
        "rows_by_source_class": dict(sorted(Counter(r["source_class"] for r in fobs).items())),
        "rows_by_period_type": dict(sorted(Counter(r["period_type"] for r in fobs).items())),
        "rows_by_rights_class": dict(sorted(Counter(r["rights_class"] for r in fobs).items())),
        "rows_by_revision_label": dict(sorted(Counter(r["revision_label"] for r in fobs).items())),
        "period_span": {c: [min(r["period_label"] for r in fobs if r["source_class"] == c),
                            max(r["period_label"] for r in fobs if r["source_class"] == c)]
                        for c in sorted({r["source_class"] for r in fobs})},
        "rows_touching_2025": sum(1 for r in fobs if r["period_start"][:4] <= "2025" <= r["period_end"][:4]),
        "rows_touching_2026": sum(1 for r in fobs if r["period_end"][:4] == "2026"),
        "nj_license_brand_overlap_rows_flagged": nj_pairs,
        "discrepancy_rows": [r["source_record_id"] for r in fobs if r["discrepancy_flag"] == "yes"],
        "relationships_by_allocation_status": dict(sorted(Counter(r["allocation_status"] for r in rels).items())),
        "relationships_by_type": dict(sorted(Counter(r["relationship_type"] for r in rels).items())),
        "digital_gaming_revenue_overlap": digital_overlap["summary"],
    }
    notes.append(f"online sports: {len(fobs)} observations ({len(monthly)} regulator monthly, {len(supp)} secondary "
                 f"monthly, {len(annual)} annual-only), {len(units)} units, {len(rels)} relationships; "
                 f"{len(cited)} cited raw reports re-hashed; counts reproduce the package release statistics.")
    return ({T_UNITS: units, T_FOB: fobs, T_REL: rels, T_GAP: gaps}, cov, withheld, notes, digital_overlap["by_revenue_id"])


def pa_discrepancy(r, check):
    """Machine-readable published-vs-calculated record for a non-reconciling row.
    Only the Pennsylvania taxable identity is known; others are refused."""
    if check["check"] != "PA_taxable_identity":
        raise OnlineSportsError(f"REFUSED: unhandled failed validation {check['check']} for {r['record_id']}")
    gross = Decimal(r["gross_revenue_usd"])
    promo = Decimal(r["promotional_deduction_usd"] or r["promotional_credits_usd"])
    published = Decimal(r["taxable_revenue_usd"])
    calc = gross - promo
    diff = calc - published
    if abs(diff - Decimal(check["difference"])) > Decimal("0.005"):
        raise OnlineSportsError(f"REFUSED: {r['record_id']} discrepancy does not reproduce ({diff} vs {check['difference']})")
    return {"discrepancy_flag": "yes", "discrepancy_measure": "taxable_revenue_usd",
            "discrepancy_formula": "gross_revenue_usd - promotional_deduction_usd = taxable_revenue_usd",
            "discrepancy_published_value": r["taxable_revenue_usd"],
            "discrepancy_calculated_value": str(calc), "discrepancy_difference": str(diff),
            "discrepancy_citation": f"{r['source_file']} {r['source_locator']} {r['source_url']}",
            "discrepancy_disposition": ("published values retained; only this observation is qualified; no correction "
                                        "inferred (package validation_checks status=review)")}


DIGITAL_TO_PACKAGE = {"HANDLE": ("handle_usd",), "GROSS_GAMING_REVENUE": ("gross_revenue_usd", "unadjusted_revenue_usd"),
                      "ADJUSTED_GROSS_REVENUE": ("adjusted_revenue_usd",), "TAX_OR_PAYMENT": ("state_payment_usd",),
                      "PROMOTIONAL_DEDUCTION": ("promotional_deduction_usd", "promotional_credits_usd"),
                      "PATRON_WINNINGS": ("payouts_usd",), "CANCELLED_WAGERS": ("voided_wagers_usd",),
                      "MONTHLY_RESETTLEMENTS": ("resettlements_usd",), "FEDERAL_EXCISE_TAX": ("federal_excise_tax_usd",)}


def cross_reference_digital(fobs, rels, digital_rows):
    """Flag package observations that describe the same state/month/licensee as
    existing digital_gaming_revenue ONLINE_SPORTSBOOK rows. Nothing is dropped;
    both sides get the other's id so neither is silently added to the other."""
    licensed = {r["sportsbook_unit_id"]: r["cedar_uid"] for r in rels if r["allocation_status"] == "single_entity"}
    by_key = defaultdict(list)
    for d in digital_rows:
        if d.get("product_type") == "ONLINE_SPORTSBOOK" and d.get("cedar_uid") and d.get("period_type") == "month":
            by_key[(d["state"], d["period_start"][:7], d["cedar_uid"])].append(d)
    by_revenue_id, stats, metric_cmp = {}, Counter(), Counter()
    for r in fobs:
        uid = licensed.get(r["sportsbook_unit_id"])
        if r["period_type"] != "monthly" or not uid:
            continue
        ds = by_key.get((r["jurisdiction"], r["period_label"], uid), [])
        if not ds:
            continue
        differs = set()
        for d in ds:
            cols = DIGITAL_TO_PACKAGE.get(d["metric"])
            if cols and d["value_usd"] != "":
                vals = [r[c] for c in cols if r[c] != ""]
                if vals:
                    ok = any(Decimal(v) == Decimal(d["value_usd"]) for v in vals)
                    metric_cmp[f"{r['jurisdiction']}:{d['metric']}:{'equal' if ok else 'differs'}"] += 1
                    if not ok:
                        differs.add(d["metric"])
            by_revenue_id[d["revenue_id"]] = r["financial_observation_id"]
        r["existing_overlap_source_record_ids"] = "|".join(sorted(d["revenue_id"] for d in ds))
        r["existing_overlap_value_check"] = ("differs:" + ",".join(sorted(differs))) if differs else "all_compared_values_equal"
        stats[r["jurisdiction"]] += 1
    summary = {"package_rows_overlapping": dict(sorted(stats.items())),
               "package_rows_overlapping_total": sum(stats.values()),
               "digital_rows_overlapping": len(by_revenue_id),
               "digital_rows_overlapping_by_state": dict(sorted(Counter(k.split("-")[1] for k in by_revenue_id).items())),
               "value_comparisons": dict(sorted(metric_cmp.items())),
               "rule": "same state + calendar month + single-entity licensee cedar_uid; ONLINE_SPORTSBOOK, month rows only"}
    return {"summary": summary, "by_revenue_id": by_revenue_id}


GAP_KEY_COLUMNS = ("gap_source", "component_table", "state", "cedar_uid", "subject", "source_status")


def gap_row(**kw):
    row = {c: "" for c in GAP_CONTRACT["header"]}
    row.update(kw)
    # A coverage gap is an absence, not an object: its key is the natural
    # composite of what is missing (ratified contract: no minted ID).
    row["coverage_gap_id"] = "|".join(row[c].strip() for c in GAP_KEY_COLUMNS)
    if row["cedar_uid"]:
        gg.checked_cedar_uid(row["cedar_uid"])
    row["rights_class"] = row["rights_class"] or "public_derived"
    row["publication_status"] = _pub(row["rights_class"])
    return row


# Per-gap machine-readable windows where the package states them only in prose.
_GAP_WINDOWS = {
    ("NJ", "license_aggregate_only_collected"): ("2019-01", "2023-12", "Hard Rock Bet brand months before the brand series starts (2024-01)"),
    ("NJ", "ownership_and_license_continuity_review"): ("2024-09", "", "Resorts license months after August 2024"),
    ("IL", "excluded_retail_only_source"): ("", "", "none: no online operator approved (retail only)"),
    ("MULTI", "national_universe_not_exhaustively_closed"): ("", "", "unknown: the national participation universe is not closed"),
    ("MULTI", "private_financial_measure_not_observed"): ("", "", "all periods: tribe-retained revenue is not published"),
}
_GAP_FREQ = {"IL": "monthly", "AR": "monthly", "AZ": "monthly", "FL": "monthly", "NJ": "monthly"}


def package_gaps(gaps_src, series_cov, uid_ok):
    out = []
    for g in gaps_src:
        key = (g["state"], g["status"])
        start = g["earliest_lead"]
        mf, mt, text = _GAP_WINDOWS.get(key, (start, "", f"{start or 'unknown start'} onward (open)"))
        out.append(dict(gap_source="online_sports_package", component_table=T_FOB, state=g["state"],
                        cedar_uid=g["cedar_uid"] if uid_ok.get(g["cedar_uid"]) else "",
                        entity_name_in_source=g["canonical_name"], subject=g["subject"],
                        measure="online sportsbook handle and revenue (series)",
                        expected_frequency=_GAP_FREQ.get(g["state"], "not_applicable" if g["state"] == "MULTI" else "monthly"),
                        known_start=start, known_end="", missing_from=mf, missing_through=mt,
                        missing_periods=text, source_status=g["status"], reason=g["notes"],
                        next_action=g["next_action"], evidence_url=g["evidence_url"], affected_record_id=""))
    # Arizona after the last collected month, any source (computed from series_coverage)
    az_last = max((sc["last_period"] for sc in series_cov.values() if sc["state"] == "AZ"), default="")
    if az_last:
        y, m = int(az_last[:4]), int(az_last[5:7])
        nxt = f"{y + 1}-01" if m == 12 else f"{y}-{m + 1:02d}"
        out.append(dict(gap_source="online_sports_package_series_coverage", component_table=T_FOB, state="AZ",
                        cedar_uid="", entity_name_in_source="", subject="Arizona tribal event-wagering licensees, all sources",
                        measure="handle_usd|source_revenue_usd|state_payment_usd", expected_frequency="monthly",
                        known_start="2021-09", known_end="", missing_from=nxt, missing_through="",
                        missing_periods=f"{nxt} onward: no official or secondary monthly rows collected",
                        source_status="no_observations_after_" + az_last,
                        reason="Official ADG reports returned HTTP 403; the secondary PlayAZ slice ends " + az_last,
                        next_action="Acquire official ADG monthly event-wagering reports through a permitted channel",
                        evidence_url="https://gaming.az.gov/resources/reports", affected_record_id=""))
    # internal missing months inside collected windows
    for s, sc in sorted(series_cov.items()):
        if sc["internal_missing_months"].strip():
            out.append(dict(gap_source="online_sports_package_series_coverage", component_table=T_FOB,
                            state=sc["state"], cedar_uid="", entity_name_in_source=sc["reporting_entity"],
                            subject=f"{s} internal missing months", measure="all measures",
                            expected_frequency="monthly", known_start=sc["first_period"], known_end=sc["last_period"],
                            missing_from="", missing_through="", missing_periods=sc["internal_missing_months"],
                            source_status="internal_month_gap", reason="months absent inside the collected window",
                            next_action="Locate the missing monthly reports", evidence_url=sc["source_url"],
                            affected_record_id=""))
    return out
