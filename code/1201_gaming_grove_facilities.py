#!/usr/bin/env python3
"""
Cedar Grove Gaming - 1201: the FACILITY lane. One row per distinct physical
gaming property, and around it the evidence that says what it is called, where
it is, whether it is operating, how big it is and who it belongs to.

    py -3 code/1201_gaming_grove_facilities.py build \
        --input-root "C:\\Users\\esm247\\Desktop\\Cedar Press" \
        --output-root C:\\Users\\esm247\\cedar-grove-gaming-work\\components

WHY THIS IS NOT A COPY OF gaming_facilities.csv
-----------------------------------------------
`gaming_facilities.csv` has 787 rows and they are not 787 casinos. They are
787 SOURCE records from four vintages (CCP- = Casino City Press property
numbers, TPL- = Casino City's Tribal Property List, VP- = the votingpatterns
research compilation, CEDAR-FAC- = rows Cedar created from NIGC/OSHA). 1129
bound them to 717 distinct `cedar_place_id` values and 16 rows that assert a
tribe has NO casino. Almost every field on them - name, address, coordinate,
status, open date, capacity - is Casino City lineage, which is internal QA
only (docs/GAMING_SPEC_RECONCILIATION.md: "Casino City may be read for QA and
may never be published or resold"). So this producer:

  * keys the facility on the place, never on the vendor number
    (`gaming_grove.facility_id_for` is the only renderer; the ID contract is
    on OWNER HOLD, so every ID written here is a non-promotable PROV- value);
  * rebuilds every public field from INDEPENDENT evidence only - the NIGC
    gaming location map, the California Gambling Control Commission lists,
    state regulators' facility-level reports, SEC filings, the operator's own
    website, and the US Census geocode of an address that itself came from one
    of those - and leaves the field BLANK with its reason when no such
    evidence exists. A vendor value is never written into a public column,
    not even "as a fallback";
  * keeps the vendor/research values as rows with an internal rights class in
    the names/history/capacity/relationship tables, so QA can still see them;
  * gives every one of the 787 legacy rows exactly one disposition
    (mapped / merged_into / unresolved / not_a_gaming_facility) in the
    internal crosswalk, so nothing is dropped silently.

RULINGS THIS PRODUCER APPLIES (and where they come from)
--------------------------------------------------------
  * votingpatterns addresses/names are a research compilation: the site is
    named but there is no URL, retrieval date or quote (GAMING_LOCATION_LAYER
    tier C; audit handoff 2026-09-24: "inherit that provenance, not
    independent corroboration"). Here: `withheld_unverified`, a lead.
  * A Census geocode of a withheld address is withheld too: re-geocoding does
    not launder the input.
  * The operator's own website (single-property host, retrieved with URL and
    quote) is `public_official` for its own name/location/operating status and
    its own reported counts - it is the sovereign's or its enterprise's own
    publication about its own property. Text-mined DATE claims from marketing
    copy are NOT: they are demonstrably noisy ("Pragmatic Play ... since 2008"
    was extracted as a casino's in-operation-since), so they stay leads.
  * An NIGC map listing is a LISTING, not an opening; a snapshot diff bounds a
    listing change between two capture dates and is never an open/close date.
  * YYYY-12-31 / YYYY-MM-15 values in the vendor workbook are placeholders
    (code/1159); they are carried at the precision the source supports and
    flagged, never shown as a day.
  * Relationships default to `affiliate`. `owner`/`operator` only where the
    operator's own site says "owned by"/"owned and operated by" AND the named
    owner agrees with the curated entity; a management brand is a
    `management_contractor`, never an owner. No ownership percentage is
    stated anywhere authoritative, so none is written.
  * NEED/NEST enterprise links are under an affiliation HOLD and no source
    here links a NEST enterprise to a facility except by name, so none is
    emitted (count reported).
  * Held-open place groups (docs/.../place_gaming_hold_open_disposition):
    The Stables (Miami/Modoc joint operation) and 7 Clans First Council
    (Ponca vs Otoe-Missouria) stay `unresolved` on the questioned record;
    the place held by the regulator-listed record stays live. Glacier Peaks
    and Cities of Gold are casino+hotel pairs held apart by the standing rule.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import gaming_grove as gg  # noqa: E402

csv.field_size_limit(10_000_000)
SCRIPT = "code/1201_gaming_grove_facilities.py"
RECEIPT = "1201_gaming_grove_facilities.receipt.json"

# ------------------------------------------------------------------ vocab
DISPOSITIONS = {"mapped", "merged_into", "unresolved", "not_a_gaming_facility"}
RECORD_STATUSES = {"property", "held_open_pending_owner_ruling",
                   "disputed_distinctness", "cross_reference_stub"}
FACILITY_TYPES = {"casino", "casino_resort", "casino_hotel", "bingo_hall",
                  "gaming_center", "travel_plaza_gaming", "sportsbook", "unknown"}
CURRENT_STATUSES = {"operating", "unknown"}
HISTORY_EVENT_TYPES = {
    "opening", "interim_opening", "closure", "relocation", "expansion", "renovation",
    "acquisition", "renaming", "status_change", "status_observation",
    "regulator_listing_added", "regulator_listing_removed",
    "regulator_location_changed", "anniversary_claim"}
PRECISIONS = {"day", "month", "quarter", "year", "fiscal_year",
              "observed_on_retrieval_date", "unknown"}
PARTY_KINDS = {"native_entity", "enterprise", "external_company"}
YN = {"Y", "N"}

OFFICIAL_SYSTEMS = {"nigc_gaming_location_map", "ca_cgcc_official_lists",
                    "state_regulator_or_federal_record", "sec_edgar",
                    "operator_website", "us_census_geocoder", "osha_ita",
                    "nigc_map_snapshot_diff", "cedar_hand_research_official_url"}

# Commercial directories: same class as Casino City (internal_vendor).
DIRECTORY_HOSTS = {"500nations.com", "worldcasinodirectory.com", "allbiz.com",
                   "gamingdirectory.com", "yelp.com", "tripadvisor.com",
                   "chipguide.themogh.org", "casinocity.com", "indiangaming.com"}

SELF_PUB_SINGLE = ("single_property_host", "single_facility_tribe", "hand_ruling")
BAD_PAGE_VERDICTS = {"NAME_TOKEN_ABSENT", "DOMAIN_MIGRATED"}


# ------------------------------------------------------------------ helpers
def _cols(spec):
    return [c for c, _, _ in spec]


def _contract(grain, pk, spec, *, required=(), enums=None, dates=(), intervals=(),
              public_ids=(), derived=None, nonadd="", status="source_limited",
              supersedes=(), row_rights=""):
    return {
        "grain": grain, "primary_key": list(pk), "required": list(required),
        "enums": enums or {}, "dates": list(dates), "intervals": list(intervals),
        "public_id_columns": list(public_ids), "derived_ids": derived or {},
        "field_rights": {c: r for c, r, _ in spec},
        "field_descriptions": {c: d for c, _, d in spec},
        "nonadditive_note": nonadd, "publication_status": status,
        "supersedes": list(supersedes), "row_rights_column": row_rights,
    }


VENDOR_TEXT_RE = re.compile(r"\b(?:CCP|VP|TPL)-\d+\b")


def scrub(text: str) -> str:
    """Public free text may not carry a vendor-lineage record number."""
    return VENDOR_TEXT_RE.sub("[legacy record]", text or "")


def host_of(url: str) -> str:
    u = (url or "").strip()
    m = re.match(r"^https?://web\.archive\.org/web/[^/]+/(.*)$", u)
    if m:
        u = m.group(1)
    u = re.sub(r"^https?://", "", u)
    h = u.split("/")[0].lower()
    return h[4:] if h.startswith("www.") else h


def iso_day(value: str) -> str:
    v = (value or "").strip()[:10]
    return v if gg.ISO_DATE_RE.match(v) else ""


def norm_date(value: str):
    """Return (iso_or_blank, verbatim). '2019.0' -> '2019' (a float-typed year)."""
    v = (value or "").strip()
    if re.fullmatch(r"\d{4}\.0", v):
        return v[:4], v
    return (v, v) if gg.ISO_DATE_RE.match(v) else ("", v)


ADMIN_ADDR_RE = re.compile(r"(^| )(c o|p ?o box|box \d+|hc \d+)( |$)")


def addr_key(street: str, state: str) -> str:
    n = norm_addr(street)
    return f"{n}|{state}" if n else ""


_STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA", "colorado": "CO",
    "connecticut": "CT", "delaware": "DE", "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS", "kentucky": "KY", "louisiana": "LA",
    "maine": "ME", "maryland": "MD", "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY", "north carolina": "NC",
    "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
    "rhode island": "RI", "south carolina": "SC", "south dakota": "SD", "tennessee": "TN", "texas": "TX",
    "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY"}


def usps(state: str) -> str:
    s = (state or "").strip()
    return _STATES.get(s.lower(), s.upper() if len(s) == 2 else s)


def split_nigc_address(full: str, city: str, state: str):
    """'2051 S Gordon Cooper, Shawnee OK 74801' -> (street, city, state, zip).
    The roster's own street/city split is broken (ilani: street '1'), so the
    verbatim address is split here on its last comma."""
    full = (full or "").strip()
    z = (re.search(r"(\d{5})(?:-\d{4})?\s*$", full) or [None, ""])[1]
    street = full.rsplit(",", 1)[0].strip() if "," in full else ""
    if re.fullmatch(r"-?\d+\.\d+", street):   # 'address' that is a coordinate pair
        street = ""
    return street, (city or "").strip(), (state or "").strip(), z


def same_street(k1: str, k2: str) -> bool:
    """Two addr_keys name the same street address: same state, same leading
    house number (or both none), and at least one shared street token. Tolerates
    'Dr'/'Drive' and suffix omissions; refuses different house numbers."""
    a, sa = (k1.split("|") + [""])[:2]
    b, sb = (k2.split("|") + [""])[:2]
    if sa != sb:
        return False
    ta, tb = a.split(), b.split()
    na = ta[0] if ta and ta[0][:1].isdigit() else ""
    nb = tb[0] if tb and tb[0][:1].isdigit() else ""
    if na != nb:
        return False
    rest_a = {t for t in ta[1 if na else 0:] if len(t) > 2}
    rest_b = {t for t in tb[1 if nb else 0:] if len(t) > 2}
    return bool(rest_a & rest_b) or (not rest_a and not rest_b)


def norm_addr(a: str) -> str:
    a = (a or "").lower()
    a = re.sub(r"[^a-z0-9 ]", " ", a)
    rep = {"road": "rd", "street": "st", "avenue": "ave", "boulevard": "blvd",
           "highway": "hwy", "drive": "dr", "lane": "ln", "north": "n", "south": "s",
           "east": "e", "west": "w", "southwest": "sw", "northwest": "nw",
           "trail": "tr", "parkway": "pkwy", "us": "", "state": ""}
    toks = [rep.get(t, t) for t in a.split()]
    return " ".join(t for t in toks if t)


def haversine_km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(h))


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def facility_type_from(name: str, schema_type: str = "") -> tuple[str, str]:
    n = (name or "").lower()
    if "sportsbook" in n and "casino" not in n:
        return "sportsbook", "public name"
    if re.search(r"travel (center|plaza)|truck stop|travel stop", n):
        return "travel_plaza_gaming", "public name"
    if "bingo" in n and "casino" not in n:
        return "bingo_hall", "public name"
    if "resort" in n and ("casino" in n or "gaming" in n):
        return "casino_resort", "public name"
    if "hotel" in n and "casino" in n:
        return "casino_hotel", "public name"
    if "gaming center" in n or "gaming centre" in n or "gaming" in n and "casino" not in n:
        return "gaming_center", "public name"
    if "casino" in n:
        return "casino", "public name"
    if schema_type.lower() == "casino":
        return "casino", "operator website schema.org type"
    return "unknown", ""


# ------------------------------------------------------------------ table specs
# (column, field rights class, description). Every column is classified; the
# per-row `*_rights` columns say whether THIS row's value is public.
FAC_SPEC = [
    ("gaming_facility_id", "public_derived", "Gaming facility ID rendered by gaming_grove.facility_id_for from the place ID (PROV- until the ID contract is approved)"),
    ("record_status", "public_derived", "property | held_open_pending_owner_ruling | disputed_distinctness | cross_reference_stub"),
    ("publication_status", "public_derived", "public (name+location+status all independently evidenced) | source_limited (some) | withheld (none) | unresolved (identity not settled)"),
    ("public_name", "public_official", "Facility name as published by the highest-priority independent source; blank when none"),
    ("public_name_source_system", "public_derived", "Source system of public_name"),
    ("public_name_source_url", "public_official", "URL of the source of public_name"),
    ("public_name_as_of", "public_derived", "As-of/retrieval date of public_name (ISO)"),
    ("public_name_rights", "public_derived", "Rights class of this row's public_name value"),
    ("facility_type", "public_derived", "Facility type derived from the public name or operator schema.org type; unknown when not derivable"),
    ("facility_type_basis", "public_derived", "What facility_type was derived from"),
    ("street_address", "public_official", "Street address from an independent source (regulator map or operator website)"),
    ("city", "public_official", "City from an independent source"),
    ("state", "public_official", "State (USPS) from an independent source"),
    ("postal_code", "public_official", "ZIP from an independent source"),
    ("address_source_system", "public_derived", "Source system of the address fields"),
    ("address_source_url", "public_official", "URL of the address source"),
    ("address_as_of", "public_derived", "As-of/retrieval date of the address"),
    ("address_rights", "public_derived", "Rights class of this row's address values"),
    ("county", "public_official", "County from Census geocode of an independent address, or CA CGCC list"),
    ("county_fips", "public_official", "5-digit county FIPS from the Census geocoder"),
    ("county_source_system", "public_derived", "Source system of county"),
    ("county_rights", "public_derived", "Rights class of this row's county values"),
    ("latitude", "public_official", "Latitude (WGS84) from NIGC point, Census geocode of an independent address, or operator website"),
    ("longitude", "public_official", "Longitude (WGS84)"),
    ("coordinate_source_system", "public_derived", "Source system of the coordinate"),
    ("coordinate_method", "public_derived", "NIGC_PUBLISHED_POINT | CENSUS_GEOCODE_EXACT | CENSUS_GEOCODE_NON_EXACT | OPERATOR_WEBSITE_POINT"),
    ("coordinate_as_of", "public_derived", "As-of/retrieval date of the coordinate"),
    ("coordinate_rights", "public_derived", "Rights class of this row's coordinate"),
    ("current_status", "public_derived", "operating when an independent dated source shows it listed/reporting/advertising; unknown otherwise (a vendor 'closed' is internal and not shown)"),
    ("status_as_of", "public_derived", "Date of the most recent independent status evidence"),
    ("status_basis", "public_derived", "Plain statement of what the status evidence is"),
    ("status_source_system", "public_derived", "Source system of the status evidence"),
    ("status_source_url", "public_official", "URL of the status evidence"),
    ("status_rights", "public_derived", "Rights class of this row's status"),
    ("withheld_fields", "public_derived", "Field groups withheld on this row and why (field:reason;...)"),
    ("n_legacy_records", "public_derived", "Number of legacy source records resolved to this facility (mapped + merged_into + unresolved)"),
    ("n_independent_sources", "public_derived", "Distinct independent (public) source systems evidencing this facility"),
    ("n_name_rows", "public_derived", "Rows in gaming_facility_names (all rights)"),
    ("n_public_name_rows", "public_derived", "Public rows in gaming_facility_names"),
    ("n_history_rows", "public_derived", "Rows in gaming_facility_history (all rights)"),
    ("n_public_history_rows", "public_derived", "Public rows in gaming_facility_history"),
    ("n_capacity_rows", "public_derived", "Rows in gaming_facility_capacity (all rights)"),
    ("n_public_capacity_rows", "public_derived", "Public rows in gaming_facility_capacity"),
    ("n_relationship_rows", "public_derived", "Rows in gaming_facility_relationships (all rights)"),
    ("n_public_relationship_rows", "public_derived", "Public rows in gaming_facility_relationships"),
    ("cedar_place_id", "internal_crosswalk", "Underlying CEDAR-PLACE id (1129); internal while the ID contract is on hold"),
    ("dedup_basis", "internal_crosswalk", "How the legacy records sharing this place were adjudicated (alias vs co-located vs held open)"),
    ("qa_flags", "internal_crosswalk", "Conflicts found (address/coordinate/status/listing) - internal because some cite vendor values"),
]

XW_SPEC = [
    ("legacy_facility_id", "internal_crosswalk", "Legacy gaming_facilities.facility_id (CCP-/VP-/TPL-/CEDAR-FAC-)"),
    ("legacy_id_scheme", "internal_crosswalk", "CCP (Casino City Press) | TPL (Casino City Tribal Property List) | VP (votingpatterns) | CEDAR-FAC (Cedar-created)"),
    ("key_scheme", "internal_crosswalk", "Which identifier this row carries"),
    ("key_value", "internal_crosswalk", "The identifier value as held by its source"),
    ("gaming_facility_id", "internal_crosswalk", "Facility the legacy record resolves to (blank for place-less rows)"),
    ("cedar_place_id", "internal_crosswalk", "The legacy record's own place id from 1129 (blank for the 16 NOT_A_PLACE rows)"),
    ("place_binding_role", "internal_crosswalk", "primary | merged_duplicate, from data/spine/cedar_place_id_register.csv"),
    ("disposition", "internal_crosswalk", "mapped | merged_into | unresolved | not_a_gaming_facility - exactly one per legacy record"),
    ("disposition_basis", "internal_crosswalk", "Evidence/ruling behind the disposition"),
    ("merged_into_gaming_facility_id", "internal_crosswalk", "For merged_into: the surviving facility"),
    ("candidate_gaming_facility_id", "internal_crosswalk", "For unresolved: the facility this record is suspected to duplicate"),
    ("publication_status", "internal_crosswalk", "internal for every crosswalk row; unresolved for place-less rows"),
    ("source_table", "internal_crosswalk", "Clean table the key was read from"),
    ("rights_class", "internal_crosswalk", "Always internal_crosswalk"),
]

EVID = [
    ("source_system", "public_derived", "Source system"),
    ("source_record_id", "internal_crosswalk", "Original source record ID (may be a vendor ID, hence internal)"),
    ("source_url", "public_official", "Source URL (blank when the source has none)"),
    ("source_date", "public_derived", "Date the source states for itself (ISO) where known"),
    ("retrieved_date", "public_derived", "Date the source was retrieved (ISO)"),
    ("rights_class", "public_derived", "Row-level rights class; non-public rows are dropped by public_projection"),
]

NAME_SPEC = [
    ("name_id", "public_derived", "GFNM derived id from (facility, source system, source record, field)"),
    ("gaming_facility_id", "public_derived", "Facility"),
    ("name", "public_official", "Name exactly as the source publishes it"),
    ("name_type", "public_derived", "regulator_listed | state_regulator_reported | operator_website | federal_dataset | vendor_directory | research_compilation | regulator_listed_prior"),
    ("first_observed", "public_derived", "Earliest date this source shows the name"),
    ("last_observed", "public_derived", "Latest date this source shows the name (not an end-of-validity date)"),
    ("observation_precision", "public_derived", "Precision of first/last observed"),
    ("is_selected_public_name", "public_derived", "Y on the row chosen as gaming_grove_facilities.public_name"),
    ("n_observations", "public_derived", "Source records from this source showing this name (collapsed into this row)"),
    ("evidence_quote", "public_official", "Verbatim source text"),
] + EVID

HIST_SPEC = [
    ("history_id", "public_derived", "GFST derived id"),
    ("gaming_facility_id", "public_derived", "Facility"),
    ("record_kind", "public_derived", "event | status_observation"),
    ("event_type", "public_derived", "opening/closure/renaming/... or status_observation / regulator_listing_*"),
    ("status_value", "public_derived", "For status observations: operating | listed | temporarily_closed | under_construction | approved | closed (as the source states it)"),
    ("event_date", "public_derived", "Date at the precision the source supports (YYYY, YYYY-MM or YYYY-MM-DD); blank when only an interval is known"),
    ("date_precision", "public_derived", "day | month | quarter | year | fiscal_year | observed_on_retrieval_date | unknown"),
    ("date_not_before", "public_derived", "Earliest date consistent with the evidence"),
    ("date_not_after", "public_derived", "Latest date consistent with the evidence"),
    ("date_is_placeholder", "public_derived", "Y when the source value carried a vendor placeholder day (YYYY-12-31 / YYYY-MM-15, code/1159)"),
    ("source_value_verbatim", "internal_crosswalk", "Source date string exactly as held (may be vendor)"),
    ("event_qualifier", "public_derived", "gaming_commenced | property_opened | unspecified | listing_not_opening | not_gaming_commencement | ..."),
    ("evidence_text", "public_official", "Evidence text or quote"),
    ("review_status", "public_derived", "source_asserted | machine_matched | reviewed_confirmed | reviewed_disputed | unresolved"),
] + EVID

CAP_SPEC = [
    ("capacity_observation_id", "public_derived", "GFCP derived id"),
    ("gaming_facility_id", "public_derived", "Facility"),
    ("metric", "public_derived", "What is counted (gaming_machines, table_games, hotel_rooms, gaming_square_feet, ...)"),
    ("metric_family", "public_derived", "gaming_devices | gaming_tables | lodging | floor_space | amenity | venue"),
    ("value", "public_official", "Numeric value as stated (blank for text-only amenities)"),
    ("value_text", "public_official", "Text value for amenities (e.g. loyalty programme name) or the verbatim number"),
    ("unit", "public_derived", "Unit as stated"),
    ("measurement_type", "public_derived", "REGULATORY_REPORTED_COUNT | AUTHORIZED_MAXIMUM | PROPERTY_REPORTED_COUNT | AUDITED_FILING | VENDOR_DIRECTORY_VALUE | AMENITY_PRESENT"),
    ("as_of_date", "public_derived", "Date the value applies to (or the retrieval date for undated operator claims)"),
    ("as_of_precision", "public_derived", "Precision of as_of_date"),
    ("period_start", "public_derived", "Reporting period start where stated"),
    ("period_end", "public_derived", "Reporting period end where stated"),
    ("qualifier", "public_derived", "Scope qualifiers (area of property, bound direction, applies_to)"),
    ("attribution_basis", "internal_crosswalk", "How the source record was attributed to this facility"),
    ("evidence_quote", "public_official", "Verbatim source text"),
] + EVID

REL_SPEC = [
    ("relationship_id", "public_derived", "GREL derived id from (facility, party, type, source system)"),
    ("gaming_facility_id", "public_derived", "Facility"),
    ("party_kind", "public_derived", "native_entity | enterprise | external_company"),
    ("cedar_uid", "public_derived", "Native entity (canonical CE- id only; blank when party is not a Native entity)"),
    ("enterprise_id", "public_derived", "NEST enterprise id (none emitted: affiliation HOLD, no non-name evidence)"),
    ("party_name", "public_official", "Party name as the source states it (external companies; the Native entity's register name otherwise)"),
    ("party_external_id", "public_official", "External identifier of an external company (SEC CIK)"),
    ("party_external_id_scheme", "public_derived", "Scheme of party_external_id"),
    ("relationship_type", "public_derived", "owner | operator | affiliate | licensee | landholder | beneficiary | management_contractor | other_documented"),
    ("role_as_stated", "public_official", "The source's own words for the role"),
    ("ownership_percent", "public_official", "Only from an authoritative source; blank everywhere today"),
    ("effective_start", "public_derived", "Start of the relationship where the source states it"),
    ("effective_end", "public_derived", "End of the relationship where the source states it"),
    ("observed_as_of", "public_derived", "Date the evidence was observed/published (not a start date)"),
    ("evidence_text", "public_official", "Evidence text/quote"),
    ("confidence", "public_derived", "high | medium | low"),
    ("review_status", "public_derived", "source_asserted | machine_matched | reviewed_confirmed | reviewed_disputed | unresolved"),
    ("n_source_records", "public_derived", "Source records collapsed into this row"),
] + EVID

_R = sorted(gg.RIGHTS_CLASSES)
CONTRACTS = {
    "gaming_grove_facilities.csv": _contract(
        "One row per distinct physical gaming property (a CEDAR-PLACE gaming place that at least one legacy record resolves to as mapped or unresolved).",
        ["gaming_facility_id"], FAC_SPEC,
        required=["publication_status", "record_status", "current_status"],
        enums={"record_status": RECORD_STATUSES, "publication_status": gg.PUBLICATION_STATUSES,
               "facility_type": FACILITY_TYPES, "current_status": CURRENT_STATUSES,
               "public_name_rights": gg.RIGHTS_CLASSES, "address_rights": gg.RIGHTS_CLASSES,
               "county_rights": gg.RIGHTS_CLASSES, "coordinate_rights": gg.RIGHTS_CLASSES,
               "status_rights": gg.RIGHTS_CLASSES},
        dates=["public_name_as_of", "address_as_of", "coordinate_as_of", "status_as_of"],
        public_ids=["gaming_facility_id"],
        nonadd="A facility row is not an NIGC 'gaming operation' or 'establishment'; row counts are not comparable to NIGC's 545 FY2025 operations and are not a revenue base.",
        status="source_limited",
        supersedes=["gaming_facilities (legacy 787-row source-record table: identity + fields re-derived; vendor fields dropped)",
                    "gaming_properties (property view of the same records)", "cedar_places (GAMING_PROPERTY rows: id source)",
                    "gaming_property_locations (location evidence)", "gaming_nigc_roster_link (name/status evidence)"]),
    "gaming_facility_crosswalk.csv": _contract(
        "One row per (legacy facility record, identifier scheme, identifier value); every legacy gaming_facilities row has a legacy_facility_id row carrying its disposition.",
        ["legacy_facility_id", "key_scheme", "key_value"], XW_SPEC,
        required=["disposition", "rights_class"],
        enums={"disposition": DISPOSITIONS, "publication_status": {"internal", "unresolved"},
               "rights_class": {"internal_crosswalk"}},
        public_ids=["gaming_facility_id", "merged_into_gaming_facility_id", "candidate_gaming_facility_id"],
        nonadd="Identifiers only. Several legacy records and several NIGC/CA keys can resolve to one facility.",
        status="internal",
        supersedes=["gaming_facilities.facility_id / casino_city_id (retired from public keys)",
                    "data/spine/cedar_place_id_register.csv (read)", "review/place_gaming_* (read)"],
        row_rights="rights_class"),
    "gaming_facility_names.csv": _contract(
        "One row per (facility, source record, name) observation; names are observations with first/last observed dates, not validity periods.",
        ["name_id"], NAME_SPEC,
        required=["gaming_facility_id", "name", "rights_class"],
        enums={"rights_class": gg.RIGHTS_CLASSES, "is_selected_public_name": YN,
               "observation_precision": PRECISIONS},
        dates=["first_observed", "last_observed", "source_date", "retrieved_date"],
        intervals=[("first_observed", "last_observed")],
        public_ids=["name_id", "gaming_facility_id"], derived={"name_id": "GFNM"},
        nonadd="Names are not counted as facilities.", status="source_limited",
        supersedes=["gaming_facilities.facility_name", "gaming_nigc_roster_link.nigc_location_name",
                    "ca_gaming_facilities_official.facility_name_as_published",
                    "gaming_property_universe_events (renamed)"],
        row_rights="rights_class"),
    "gaming_facility_history.csv": _contract(
        "One row per dated facility event or dated status observation from one source record.",
        ["history_id"], HIST_SPEC,
        required=["gaming_facility_id", "record_kind", "event_type", "date_precision", "rights_class"],
        enums={"record_kind": {"event", "status_observation"}, "event_type": HISTORY_EVENT_TYPES,
               "date_precision": PRECISIONS, "date_is_placeholder": YN,
               "review_status": gg.REVIEW_STATUSES, "rights_class": gg.RIGHTS_CLASSES},
        dates=["event_date", "date_not_before", "date_not_after", "source_date", "retrieved_date"],
        intervals=[("date_not_before", "date_not_after")],
        public_ids=["history_id", "gaming_facility_id"], derived={"history_id": "GFST"},
        nonadd="Events are not additive; a listing event is not an opening; land/decision dates are excluded (regulatory lane).",
        status="source_limited",
        supersedes=["gaming_facilities open/close/status columns", "gaming_property_universe_events",
                    "gaming_property_self_published_assertions (date claims, as leads)"],
        row_rights="rights_class"),
    "gaming_facility_capacity.csv": _contract(
        "One row per dated capacity/amenity observation for one facility from one source record.",
        ["capacity_observation_id"], CAP_SPEC,
        required=["gaming_facility_id", "metric", "measurement_type", "rights_class"],
        enums={"rights_class": gg.RIGHTS_CLASSES, "as_of_precision": PRECISIONS,
               "metric_family": {"gaming_devices", "gaming_tables", "lodging", "floor_space", "amenity", "venue"}},
        dates=["as_of_date", "period_start", "period_end", "source_date", "retrieved_date"],
        intervals=[("period_start", "period_end")],
        public_ids=["capacity_observation_id", "gaming_facility_id"], derived={"capacity_observation_id": "GFCP"},
        nonadd="Snapshots: never sum across dates, sources, or measurement types; AUTHORIZED_MAXIMUM is not an installed count; operator claims are upper-bounded by retrieval date.",
        status="source_limited",
        supersedes=["gaming_capacity_official (capacity/authorization rows)", "gaming_property_site_observations",
                    "gaming_property_self_published_claims", "gaming_facilities latest_* capacity (vendor, internal)",
                    "loyalty_program_property"],
        row_rights="rights_class"),
    "gaming_facility_relationships.csv": _contract(
        "One row per (facility, party, relationship type, source system).",
        ["relationship_id"], REL_SPEC,
        required=["gaming_facility_id", "party_kind", "relationship_type", "confidence", "review_status", "rights_class"],
        enums={"party_kind": PARTY_KINDS, "relationship_type": gg.RELATIONSHIP_TYPES,
               "confidence": gg.CONFIDENCE, "review_status": gg.REVIEW_STATUSES,
               "rights_class": gg.RIGHTS_CLASSES},
        dates=["effective_start", "effective_end", "observed_as_of", "source_date", "retrieved_date"],
        intervals=[("effective_start", "effective_end")],
        public_ids=["relationship_id", "gaming_facility_id", "cedar_uid", "enterprise_id"],
        derived={"relationship_id": "GREL"},
        nonadd="A relationship row is not an ownership share; no percentages are summed or inferred.",
        status="source_limited",
        supersedes=["gaming_facilities.cedar_uid / operating_entity_cedar_uids", "sec_gaming_management_contract_terms (facility-named rows)",
                    "gaming_property_self_published_assertions (ownership/management)"],
        row_rights="rights_class"),
}


# ------------------------------------------------------------------ build
# Held-open place groups (review/place_gaming_hold_open_disposition_2026-09-02):
# the QUESTIONED record of each ESCALATE_OWNER pair -> (the record whose place
# is the settled property, why). Which record is questioned is a reading of
# the 1141 evidence, so it is written here, not re-derived by a name test.
QUESTIONED = {
    "VP-0170": ("CCP-843900", "7 Clans First Council: VP-0170 files the property to the Ponca Tribe; the Otoe-Missouria Tribe's own casino listing and the NIGC map name the same address for CCP-843900 (review/place_gaming_hold_open_disposition, ESCALATE_OWNER). Held unresolved pending the owner's repoint ruling."),
    "VP-0153": ("CCP-305300", "The Stables: one property, Miami/Modoc joint operation; VP-0153 keys it to Modoc alone while CCP-305300 carries both operators (docs/GAMING_JOINT_OPERATORS.json). Same property on the facts; merging two place ids is an owner ruling (ESCALATE_OWNER)."),
}


class _Ctx:
    """Accumulates rows and counters for one build."""

    def __init__(self):
        self.names, self.hist, self.cap, self.rel = {}, {}, {}, {}
        self.withheld = Counter()
        self.notes = []
        self.defects = Counter()


def _legacy_scheme(fid: str) -> str:
    return "CEDAR-FAC" if fid.startswith("CEDAR-FAC") else fid.split("-")[0]


def _vendor_rights(fid: str) -> tuple[str, str]:
    """Rights and source system of a value that lives on a legacy facility row."""
    s = _legacy_scheme(fid)
    if s in ("CCP", "TPL"):
        return "internal_vendor", "casino_city_press"
    if s == "VP":
        return "withheld_unverified", "votingpatterns_research"
    return "withheld_unverified", "cedar_created_record"


def _url_rights(url: str, evidence: str, own_hosts: set) -> tuple[str, str]:
    h = host_of(url)
    if not h:
        return "withheld_unverified", "no_url"
    if h.endswith(".gov") or ".gov/" in url or h.endswith(".nsn.us"):
        return "public_official", "government_url"
    if h in DIRECTORY_HOSTS:
        return "internal_vendor", "commercial_directory"
    if h in own_hosts:
        return "public_official", "operator_website"
    ev = (evidence or "").lower()
    if "own" in ev and ("site" in ev or "page" in ev or "listing" in ev):
        return "public_official", "operator_website_per_researcher"
    return "withheld_unverified", "secondary_source_lead"


def build(inputs: "gg.Inputs", out_dir: Path) -> dict:
    ctx = _Ctx()
    _, F = inputs.clean("gaming_facilities.csv")
    _, NIGC = inputs.clean("gaming_nigc_roster_link.csv")
    _, LOC = inputs.clean("gaming_property_locations.csv")
    _, CA = inputs.clean("ca_gaming_facilities_official.csv")
    _, CAPO = inputs.clean("gaming_capacity_official.csv")
    _, SITE = inputs.clean("gaming_property_site_observations.csv")
    _, SPA = inputs.clean("gaming_property_self_published_assertions.csv")
    _, SPC = inputs.clean("gaming_property_self_published_claims.csv")
    _, WEB = inputs.clean("gaming_web_harvest_observations.csv")
    _, UNI = inputs.clean("gaming_property_universe_events.csv")
    _, TRACE = inputs.clean("gaming_property_federal_traces.csv")
    _, LOY = inputs.clean("loyalty_program_property.csv")
    _, SECM = inputs.clean("sec_gaming_management_contract_terms.csv")
    _, NMC = inputs.clean("nigc_management_contract_approvals.csv")
    _, REGN = inputs.clean("nigc_region_assignments.csv")
    _, NEST = inputs.clean("nest_enterprises.csv", required=False)
    _, REG = inputs.read("data/spine/cedar_identity_register.csv")
    _, PREG = inputs.read("data/spine/cedar_place_id_register.csv")
    _, ADJ = inputs.read("review/place_gaming_adjudication_2026-09-02.csv")
    _, HOLD = inputs.read("review/place_gaming_hold_open_disposition_2026-09-02.csv")
    _, NONPLACE = inputs.read("review/place_non_place_rows_2026-09-02.csv")

    register = {r["cedar_uid"]: r for r in REG}
    binding = {r["source_key"]: r["binding_role"] for r in PREG if r["place_class"] == "GAMING_PROPERTY"}
    byfid = {r["facility_id"]: r for r in F}
    trace = {r["facility_id"]: r for r in TRACE}
    nonplace = {r["facility_id"]: r for r in NONPLACE}
    hold = {}
    for h in HOLD:
        for fid in h["facility_ids"].split(";"):
            hold[fid.strip()] = h
    adj_by_fid = {}
    for a in ADJ:
        for fid in a["facility_ids"].split(";"):
            adj_by_fid[fid.strip()] = a
    place_of = {r["facility_id"]: r["cedar_place_id"] for r in F if r["cedar_place_id"]}

    def gfid(place):
        return gg.facility_id_for(place) if place else ""

    # ---------------------------------------------------------- dispositions
    # Held-open groups: which record in the pair is the questioned one. The
    # other keeps its place live (it is the regulator-listed / joint-operator
    # record). Decided from the 1141 disposition evidence, not re-derived.
    # A record that another record is ruled a duplicate OF is the surviving
    # record, whatever binding role 1129 gave it (Northern Lights: VP-0261 is
    # the register primary but is ruled a duplicate of CCP-67000).
    dup_targets = {r["duplicate_of_facility_id"] for r in F if r["duplicate_of_facility_id"]}
    disp = {}
    for r in F:
        fid, place = r["facility_id"], r["cedar_place_id"]
        t = trace.get(fid, {})
        lik = t.get("property_likelihood", "")
        dup = r["duplicate_of_facility_id"]
        absent = r["open_date_absent_reason"]
        if not place:
            np_ = nonplace.get(fid, {})
            disp[fid] = ("not_a_gaming_facility", "", "",
                         "NOT_A_PLACE: " + (np_.get("reason") or r["cedar_place_id_absent_reason"]))
        elif lik == "NOT_A_GAMING_PROPERTY" or absent.startswith("not a gaming facility"):
            disp[fid] = ("not_a_gaming_facility", "", "",
                         "ruled not a gaming facility: " + (t.get("property_likelihood_basis") or absent)[:300])
        elif dup and dup in place_of:
            disp[fid] = ("merged_into", place_of[dup], "",
                         f"ruled duplicate of another legacy record (duplicate_of_facility_id); same place={place_of[dup] == place}")
        elif fid in QUESTIONED and QUESTIONED[fid][0] in place_of:
            other, why = QUESTIONED[fid]
            disp[fid] = ("unresolved", "", place_of[other], why)
        elif lik == "DUPLICATE" or absent.startswith(("cross-reference stub", "duplicate row", "not a distinct")):
            disp[fid] = ("unresolved", "", "",
                         "ruled a duplicate/cross-reference stub with no keyed target: " + (t.get("property_likelihood_basis") or absent)[:300])
        elif absent.startswith(("gaming status not established", "identity not established")):
            disp[fid] = ("unresolved", "", "", absent[:300])
        elif binding.get(fid) == "merged_duplicate" and fid not in dup_targets:
            disp[fid] = ("merged_into", place, "",
                         "1129 bound this record to an existing place as a second vintage of one property (register binding_role=merged_duplicate; "
                         + (adj_by_fid.get(fid, {}).get("rule", "") or "adjudication row absent") + ")")
        else:
            disp[fid] = ("mapped", place, "", "primary record of its place" + (
                " (1129 group " + adj_by_fid[fid]["normalised_name"] + ": " + adj_by_fid[fid]["rule"] + ")" if fid in adj_by_fid else ""))
    # A record 'mapped' to a place whose other records all point elsewhere is fine;
    # a place with only merged/not-gaming records gets no facility row.
    facility_places = set()
    for fid, (d, tgt, cand, _) in disp.items():
        if d == "mapped":
            facility_places.add(tgt)
        elif d == "unresolved" and (cand or place_of.get(fid)):
            facility_places.add(cand or place_of[fid])
    # merged_into targets must be live facilities
    for fid, (d, tgt, cand, why) in list(disp.items()):
        if d == "merged_into" and tgt not in facility_places:
            facility_places.add(tgt)
            ctx.notes.append(f"merge target place for {fid} had no mapped record; kept live")

    def resolved_place(fid):
        d, tgt, cand, _ = disp[fid]
        if d in ("mapped", "merged_into"):
            return tgt
        if d == "unresolved":
            # A held-open record whose property is settled on the facts (only the
            # operator ruling is pending) carries its evidence to that property;
            # its own place id stays in the crosswalk.
            return cand or place_of.get(fid, "")
        return ""

    members = defaultdict(list)
    for fid in sorted(disp):
        p = resolved_place(fid)
        if p:
            members[p].append(fid)

    # ---------------------------------------------------------- own hosts
    own_hosts = set()
    for r in SITE:
        if r["attribution_basis"].startswith(SELF_PUB_SINGLE):
            own_hosts.add(host_of("https://" + r["site_host"]))
    for r in SPA:
        if r["attribution_basis"].startswith(SELF_PUB_SINGLE):
            own_hosts.add(host_of("https://" + r["site_host"]))
    bad_pages = {r["source_url"] for r in WEB if r["page_verdict"] in BAD_PAGE_VERDICTS}

    # ---------------------------------------------------------- evidence per place
    ev = defaultdict(lambda: defaultdict(list))   # place -> field -> [candidates]

    def add_name(place, name, ntype, system, rec, url, first, last, prec, quote, rights, src_date="", retrieved=""):
        if not place or not name.strip():
            return
        # One row per (facility, source system, name, rights): a state regulator
        # repeating a name in 60 monthly reports is one name observed over a span.
        nid = gg.derive_id("GFNM", place, system, name.strip(), rights)
        old = ctx.names.get(nid)
        if old:
            old["n_observations"] += 1
            if first and (not old["first_observed"] or first < old["first_observed"]):
                old["first_observed"] = first
            if last and last > old["last_observed"]:
                old["last_observed"], old["source_url"], old["retrieved_date"] = last, url, retrieved
                old["evidence_quote"] = scrub(quote) if rights in gg.PUBLIC_RIGHTS else ""
            if rec < old["source_record_id"]:
                old["source_record_id"] = rec
            return
        ctx.names[nid] = {
            "name_id": nid, "gaming_facility_id": gfid(place), "name": name.strip(),
            "name_type": ntype, "first_observed": first, "last_observed": last,
            "observation_precision": prec, "is_selected_public_name": "N", "n_observations": 1,
            "evidence_quote": scrub(quote) if rights in gg.PUBLIC_RIGHTS else "",
            "source_system": system, "source_record_id": rec, "source_url": url,
            "source_date": src_date, "retrieved_date": retrieved, "rights_class": rights,
            "_place": place}

    def add_hist(place, kind, etype, system, rec, *, status="", date="", prec="unknown",
                 nb="", na="", placeholder="N", verbatim="", qual="", text="", review="source_asserted",
                 url="", src_date="", retrieved="", rights="withheld_unverified", key_extra=""):
        if not place:
            return
        hid = gg.derive_id("GFST", place, system, rec, etype, key_extra)
        ctx.hist[hid] = {
            "history_id": hid, "gaming_facility_id": gfid(place), "record_kind": kind,
            "event_type": etype, "status_value": status, "event_date": date,
            "date_precision": prec, "date_not_before": nb, "date_not_after": na,
            "date_is_placeholder": placeholder, "source_value_verbatim": verbatim,
            "event_qualifier": qual, "evidence_text": (scrub(text) if rights in gg.PUBLIC_RIGHTS else text)[:600],
            "review_status": review,
            "source_system": system, "source_record_id": rec, "source_url": url,
            "source_date": src_date, "retrieved_date": retrieved, "rights_class": rights,
            "_place": place}
        if rights in gg.PUBLIC_RIGHTS and kind == "status_observation" and status in ("operating", "listed"):
            ev[place]["status"].append((date or na, system, url, text[:300]))

    METRIC_FAMILY = {"gaming_machines": "gaming_devices", "gaming_machines_authorized_max": "gaming_devices",
                     "class_iii_gaming_devices": "gaming_devices", "table_games": "gaming_tables",
                     "poker_tables": "gaming_tables", "blackjack_tables": "gaming_tables",
                     "bingo_seats": "gaming_tables", "hotel_rooms": "lodging", "hotel_suites": "lodging",
                     "gaming_square_feet": "floor_space", "convention_square_feet": "floor_space",
                     "meeting_square_feet": "floor_space", "restaurants": "amenity",
                     "parking_spaces": "amenity", "venue_capacity": "venue",
                     "loyalty_program": "amenity"}

    def family(metric):
        if metric in METRIC_FAMILY:
            return METRIC_FAMILY[metric]
        if "table" in metric:
            return "gaming_tables"
        if "machine" in metric or "device" in metric:
            return "gaming_devices"
        if "square" in metric:
            return "floor_space"
        return "amenity"

    def add_cap(place, metric, value, unit, mtype, system, rec, *, as_of="", prec="unknown", ps="", pe="",
                qual="", attrib="", quote="", url="", src_date="", retrieved="", rights="withheld_unverified",
                value_text=""):
        if not place:
            return
        if metric == "employees":
            ctx.withheld["capacity_skipped_employees_metric_labor_lane"] += 1
            return
        cid = gg.derive_id("GFCP", place, system, rec, metric)
        if ps and pe and pe < ps:
            # Source defect: an inverted reporting period. Kept visible, not "fixed".
            ctx.defects[f"{system}:period_end_before_period_start"] += 1
            qual = "; ".join(x for x in (qual, f"SOURCE PERIOD INVERTED {ps}..{pe}") if x)
            ps = pe = ""
        v = (value or "").strip()
        if v.endswith(".0"):
            v = v[:-2]
        ctx.cap[cid] = {
            "capacity_observation_id": cid, "gaming_facility_id": gfid(place), "metric": metric,
            "metric_family": family(metric), "value": v, "value_text": value_text, "unit": unit,
            "measurement_type": mtype, "as_of_date": as_of, "as_of_precision": prec,
            "period_start": ps, "period_end": pe, "qualifier": qual, "attribution_basis": attrib[:200],
            "evidence_quote": scrub(quote)[:400] if rights in gg.PUBLIC_RIGHTS else "",
            "source_system": system, "source_record_id": rec, "source_url": url,
            "source_date": src_date, "retrieved_date": retrieved, "rights_class": rights, "_place": place}

    rel_acc = {}

    def add_rel(place, kind, party_key, rtype, system, rec, *, cedar_uid="", party_name="", ext_id="",
                ext_scheme="", role="", start="", end="", observed="", text="", conf="low",
                review="machine_matched", url="", src_date="", retrieved="", rights="withheld_unverified"):
        if not place:
            return
        k = (place, party_key, rtype, system)
        if k in rel_acc:
            rel_acc[k]["n_source_records"] += 1
            return
        rid = gg.derive_id("GREL", place, party_key, rtype, system)
        rel_acc[k] = {
            "relationship_id": rid, "gaming_facility_id": gfid(place), "party_kind": kind,
            "cedar_uid": cedar_uid, "enterprise_id": "", "party_name": party_name,
            "party_external_id": ext_id, "party_external_id_scheme": ext_scheme,
            "relationship_type": rtype,
            "role_as_stated": (scrub(role) if rights in gg.PUBLIC_RIGHTS else role)[:200], "ownership_percent": "",
            "effective_start": start, "effective_end": end, "observed_as_of": observed,
            "evidence_text": (scrub(text) if rights in gg.PUBLIC_RIGHTS else text)[:600],
            "confidence": conf, "review_status": review,
            "n_source_records": 1, "source_system": system, "source_record_id": rec,
            "source_url": url, "source_date": src_date, "retrieved_date": retrieved,
            "rights_class": rights, "_place": place}

    def good_uid(v, where):
        v = (v or "").strip()
        if not v:
            return ""
        if not gg.is_ce_uid(v):
            ctx.defects[f"non_CE_value_in_cedar_uid:{where}"] += 1
            return ""
        if v not in register:
            ctx.defects[f"cedar_uid_absent_from_identity_register:{where}"] += 1
            return ""
        return v

    # ---- 1. legacy facility rows: names, dates, status, capacity, affiliation (internal)
    INLINE_METRICS = ["gaming_machines", "table_games", "poker_tables", "bingo_seats", "gaming_square_feet",
                      "convention_square_feet", "hotel_rooms", "parking_spaces", "restaurants"]
    for fid in sorted(byfid):
        r = byfid[fid]
        place = resolved_place(fid)
        if not place:
            continue
        rights, system = _vendor_rights(fid)
        srcs = r["source_datasets"]
        if fid.startswith("CEDAR-FAC") and srcs in ("NIGC_GAMING_LOCATION_MAP", "OSHA_ITA_300A"):
            rights = "public_official"
            system = "nigc_gaming_location_map" if srcs.startswith("NIGC") else "osha_ita"
        name_url = "https://www.nigc.gov/map/" if system == "nigc_gaming_location_map" else ""
        ntype = {"casino_city_press": "vendor_directory", "votingpatterns_research": "research_compilation",
                 "nigc_gaming_location_map": "regulator_listed", "osha_ita": "federal_dataset"}.get(system, "research_compilation")
        fetched = iso_day(r["fetched_date"])
        add_name(place, r["facility_name"], ntype, system, fid, name_url, fetched, fetched,
                 "observed_on_retrieval_date" if fetched else "unknown", "", rights, retrieved=fetched)
        # opening / interim opening / closure
        for which, etype in (("open", "opening"), ("close", "closure")):
            raw = r[f"{which}_date"]
            nb, na = r.get(f"{which}_date_not_before", ""), r.get(f"{which}_date_not_after", "")
            if not raw and not (nb or na):
                continue
            iso, verb = norm_date(raw)
            if raw and not iso:
                ctx.defects[f"gaming_facilities.{which}_date_non_iso"] += 1
            if verb != raw or re.fullmatch(r"\d{4}\.0", raw or ""):
                pass
            if re.fullmatch(r"\d{4}\.0", raw or ""):
                ctx.defects[f"gaming_facilities.{which}_date_float_typed_year"] += 1
            basis = r[f"{which}_date_basis"]
            prec = r.get(f"{which}_date_precision", "") or ("year" if len(iso) == 4 else "month" if len(iso) == 7 else "day" if iso else "unknown")
            if prec not in PRECISIONS:
                prec = "unknown"
            ph = r.get(f"{which}_date_source_value_placeholder", "")
            placeholder = "Y" if ph.startswith("vendor_") else "N"
            url = r.get(f"{which}_date_source_url", "") or (r.get("open_date_evidence_url", "") if which == "open" else "")
            evid = (r.get("open_date_evidence", "") + " " + r.get("open_date_evidence_quote", "")) if which == "open" else ""
            if basis.startswith("Casino City") or (not url and system == "casino_city_press"):
                hr, hs = "internal_vendor", "casino_city_press"
            else:
                hr, cls = _url_rights(url, evid, own_hosts)
                hs = {"public_official": "cedar_hand_research_official_url"}.get(hr, "cedar_hand_research_" + cls)
                if basis.startswith("Indian Gaming Dataset"):
                    hs = "indian_gaming_dataset_" + cls
            qual = r.get("open_date_event", "") if which == "open" else ""
            text = (r.get("open_date_evidence_quote") or r.get("open_date_evidence") or basis) if which == "open" else basis
            add_hist(place, "event", etype, hs, fid, date=iso, prec=prec, nb=nb, na=na,
                     placeholder=placeholder, verbatim=r.get(f"{which}_date_source_value_verbatim", "") or raw,
                     qual=qual or "unspecified", text=text, review="source_asserted", url=url,
                     retrieved=fetched, rights=hr)
        if r["interim_open_date"]:
            iso, _ = norm_date(r["interim_open_date"])
            add_hist(place, "event", "interim_opening", "cedar_hand_research", fid, date=iso,
                     prec="day" if len(iso) == 10 else "unknown", verbatim=r["interim_open_date"],
                     qual="interim_facility", text=r["interim_open_note"] or r["interim_open_date_basis"],
                     rights="withheld_unverified")
        lit = r["property_status_literal"].split("|")[0].strip()
        if lit:
            sv = {"Open": "operating", "Temporarily Closed": "temporarily_closed",
                  "Under Construction": "under_construction"}.get(lit, lit.lower().replace(" ", "_"))
            obs = iso_day(r["property_status_observed_date"]) or fetched
            add_hist(place, "status_observation", "status_observation", system, fid, status=sv,
                     date=obs, prec="observed_on_retrieval_date" if obs else "unknown",
                     text=f"vendor status literal '{lit}'", review="source_asserted", retrieved=fetched,
                     rights=rights if rights != "public_official" else "withheld_unverified")
        if system == "casino_city_press":
            for m in INLINE_METRICS:
                if r[m] and r[f"{m}_value_basis"] == "reported":
                    obs = iso_day(r[f"{m}_observed_date"])
                    add_cap(place, m, r[m], "count" if "feet" not in m else "square_feet",
                            "VENDOR_DIRECTORY_VALUE", "casino_city_press", fid, as_of=obs,
                            prec="observed_on_retrieval_date" if obs else "unknown",
                            attrib="native vendor record", rights="internal_vendor")
        # affiliation as held by the legacy record (internal: vendor/research attribution)
        uids = [u for u in (r["operating_entity_cedar_uids"] or r["cedar_uid"]).split("|") if u]
        if r["cedar_uid"] and r["cedar_uid"] not in uids:
            uids.insert(0, r["cedar_uid"])
        for u in uids:
            u2 = good_uid(u, "gaming_facilities.cedar_uid")
            if not u2:
                continue
            review = "machine_matched"
            conf = "medium" if r["entity_tier"] == "A" else "low"
            text = f"legacy record names '{r['tribe']}' (entity_match_method={r['entity_match_method']}, tier={r['entity_tier']})"
            if fid == "CCP-305300":
                text += "; joint operation per docs/GAMING_JOINT_OPERATORS.json"
            if fid in ("VP-0170",):
                review, conf = "reviewed_disputed", "low"
                text += "; DISPUTED: the operator's own listing names Otoe-Missouria for this address"
            if fid == "VP-0169":
                review, conf = "unresolved", "low"
                text += "; 7 Clans Ponca: ruled not a distinct property; Otoe-Missouria's listing names no Ponca City property"
            if disp[fid][0] == "unresolved" and review == "machine_matched":
                review = "unresolved"
            add_rel(place, "native_entity", u2, "affiliate", system, fid, cedar_uid=u2,
                    party_name=register[u2]["canonical_name"], role=r["tribe"], text=text,
                    conf=conf, review=review, retrieved=fetched,
                    rights=rights if rights != "public_official" else "withheld_unverified")

    # ---- 2. NIGC roster link (public name + status) and region marker ids
    nigc_by_place = defaultdict(list)
    for r in NIGC:
        place = resolved_place(r["facility_id"]) if r["facility_id"] in disp else ""
        if not place:
            ctx.withheld["nigc_roster_link_row_without_live_facility"] += 1
            continue
        nigc_by_place[place].append(r)
        asof = iso_day(r["nigc_listed_as_of"])
        street, city, st, z = split_nigc_address(r["nigc_address"], r["nigc_city"], r["nigc_state"])
        if street or city:
            ev[place]["address"].append((asof, "nigc_gaming_location_map", r["source_url"], street, city, st, z))
            ev[place]["roster_keys"].append(addr_key(street, st))
        rec = r["nigc_location_name"] + " | " + r["nigc_address"]
        add_name(place, r["nigc_location_name"], "regulator_listed", "nigc_gaming_location_map", rec,
                 r["source_url"], asof, asof, "day", rec, "public_official", retrieved=asof)
        add_hist(place, "status_observation", "status_observation", "nigc_gaming_location_map", rec,
                 status="listed", date=asof, prec="day",
                 text=f"Listed on the NIGC gaming location map as '{r['nigc_location_name']}', {r['nigc_address']} (igra_coverage_status={r['igra_coverage_status']}); a listing, not an opening",
                 review="source_asserted" if r["link_tier"] == "A" else "machine_matched",
                 url=r["source_url"], retrieved=asof, rights="public_official")
        if r["cedar_row_has_close_evidence"] == "1":
            ev[place]["flags"].append("vendor_close_evidence_vs_current_regulator_listing")

    # ---- 3. location observations (address, county, coordinates)
    for r in LOC:
        fid = r["property_id"]
        if fid not in disp:
            continue
        place = resolved_place(fid)
        if not place:
            continue
        sys_ = r["source_system"]
        asrc = r["address_source_system"]
        independent_addr = asrc in ("nigc_gaming_location_map", "ca_cgcc_licensed_facility_list")
        ret = iso_day(r["retrieved_at"])
        if sys_ == "nigc_gaming_location_map":
            if r["address"]:
                ev[place]["address"].append((ret, "nigc_gaming_location_map", r["source_url"],
                                             r["address"], r["city"], r["state"], r["postal_code"]))
                ev[place]["layer_keys"].append(addr_key(r["address"], r["state"]))
            if r["latitude"] and r["longitude"]:
                ev[place]["coord"].append((0, ret, "nigc_gaming_location_map", "NIGC_PUBLISHED_POINT",
                                           r["latitude"], r["longitude"], addr_key(r["address"], r["state"])))
            elif r["coordinate_withheld_reason"]:
                ev[place]["flags"].append("nigc_point_is_shared_tribal_marker")
        elif sys_ == "us_census_geocoder":
            if independent_addr and r["latitude"] and r["longitude"] and r["match_quality"] in ("Exact", "Non_Exact"):
                rank = 1 if r["match_quality"] == "Exact" else 2
                ev[place]["coord"].append((rank, ret, "us_census_geocoder",
                                           "CENSUS_GEOCODE_EXACT" if rank == 1 else "CENSUS_GEOCODE_NON_EXACT",
                                           r["latitude"], r["longitude"], addr_key(r["address"], r["state"])))
                if r["county"]:
                    ev[place]["county"].append((ret, "us_census_geocoder", r["county"], r["county_fips"],
                                                addr_key(r["address"], r["state"])))
            elif not independent_addr:
                ctx.withheld["census_geocode_of_research_address_withheld"] += 1
        elif sys_ == "ca_cgcc_licensed_facility_list":
            ev[place]["cityonly"].append((ret, "ca_cgcc_official_lists", r["source_url"], r["city"], r["state"]))
            if r["county"]:
                ev[place]["county"].append((ret, "ca_cgcc_official_lists", r["county"], "", ""))
        elif sys_ == "votingpatterns_canonical_addresses":
            ev[place]["research_addr"].append(r["address"])
        elif sys_.startswith("casino_city_press"):
            ev[place]["vendor_addr"].append(r["address"])

    # ---- 4. CA CGCC lists (name, status, affiliation)
    ca_ok = ("exact_name_in_state", "sole_property_of_tribe_in_state")
    for r in CA:
        fid = r["facility_id"]
        if not fid or fid not in disp or r["facility_name_match_method"] not in ca_ok:
            ctx.withheld["ca_official_rows_not_keyed_to_one_facility"] += 1
            continue
        place = resolved_place(fid)
        if not place:
            continue
        asof = iso_day(r["as_of_date"])
        if r["facility_name_as_published"]:
            add_name(place, r["facility_name_as_published"], "state_regulator_reported", "ca_cgcc_official_lists",
                     r["record_id"], r["source_url"], asof, asof, "day", r["source_quote"], "public_official",
                     src_date=asof, retrieved=iso_day(r["fetched_date"]))
        if r["list_type"] == "cgcc_casino_list":
            add_hist(place, "status_observation", "status_observation", "ca_cgcc_official_lists", r["record_id"],
                     status="listed", date=asof, prec="day",
                     text="Listed on the California Gambling Control Commission list of tribal casinos: " + r["source_quote"],
                     review="source_asserted", url=r["source_url"], src_date=asof,
                     retrieved=iso_day(r["fetched_date"]), rights="public_official")
        u = good_uid(r["cedar_uid"], "ca_gaming_facilities_official.cedar_uid")
        if u:
            add_rel(place, "native_entity", u, "affiliate", "ca_cgcc_official_lists", r["record_id"], cedar_uid=u,
                    party_name=r["tribe_name_as_published"], role=f"listed by CGCC ({r['list_type']}) with this casino",
                    observed=asof, text=r["source_quote"],
                    conf="high" if r["facility_name_match_method"] == "exact_name_in_state" else "medium",
                    review="source_asserted", url=r["source_url"], src_date=asof,
                    retrieved=iso_day(r["fetched_date"]), rights="public_official")

    # ---- 5. state regulator / federal / SEC facility-level records
    keyed = lambda m: not m.startswith(("tribe_level", "published_at_tribe_level", "tribe_has_", "no_facility",
                                        "environmental_review", "unresolved"))
    latest_report = {}
    for r in CAPO:
        fid = r["facility_id"]
        if not fid or fid not in disp or not keyed(r["facility_match_method"]):
            continue
        place = resolved_place(fid)
        if not place or r["exclusion_flag"] == "1":
            continue
        is_sec = r["source_document_type"] == "sec_form_10k"
        system = "sec_edgar" if is_sec else "state_regulator_or_federal_record"
        asof = iso_day(r["as_of_date"])
        prec = r["as_of_date_precision"] if r["as_of_date_precision"] in PRECISIONS else "unknown"
        if r["facility_name_as_published"]:
            nid_key = (place, r["source_authority"], r["facility_name_as_published"])
            add_name(place, r["facility_name_as_published"], "state_regulator_reported", system,
                     r["observation_id"], r["source_url"], asof, asof, prec, r["source_quote"], "public_official",
                     src_date=asof, retrieved=iso_day(r["fetched_date"]))
        if r["metric_class"] == "revenue" and r["measurement_status"] == "reported_revenue":
            k = (place, r["source_authority"])
            if asof and (k not in latest_report or asof > latest_report[k]["as_of_date"]):
                latest_report[k] = r
            continue
        if r["metric_class"] not in ("capacity_measurement", "authorization"):
            continue
        if r["measurement_type"] == "PROJECTED" or r["proposed_vs_actual"] in ("proposed", "selected_in_rod", "no_action"):
            ctx.withheld["capacity_official_projection_excluded"] += 1
            continue
        mtype = {"REGULATORY_REPORTED_COUNT": "REGULATORY_REPORTED_COUNT", "AUTHORIZED_MAXIMUM": "AUTHORIZED_MAXIMUM",
                 "PROPERTY_REPORTED_COUNT": "AUDITED_FILING" if is_sec else "PROPERTY_REPORTED_COUNT",
                 "COMPACT_REPORTED_COUNT": "REGULATORY_REPORTED_COUNT"}.get(r["measurement_type"], r["measurement_type"])
        qual = "; ".join(x for x in (r["applies_to"], r["qualifier"]) if x)
        add_cap(place, r["metric"], r["value"], r["unit"], mtype, system, r["observation_id"], as_of=asof,
                prec=prec, ps=iso_day(r["period_start"]), pe=iso_day(r["period_end"]), qual=qual,
                attrib=r["facility_match_method"], quote=r["source_quote"], url=r["source_url"],
                src_date=asof, retrieved=iso_day(r["fetched_date"]), rights="public_official")
    for (place, auth), r in sorted(latest_report.items()):
        system = "sec_edgar" if r["source_document_type"] == "sec_form_10k" else "state_regulator_or_federal_record"
        add_hist(place, "status_observation", "status_observation", system, r["observation_id"],
                 status="operating", date=iso_day(r["period_end"]) or iso_day(r["as_of_date"]),
                 prec=r["as_of_date_precision"] if r["as_of_date_precision"] in PRECISIONS else "unknown",
                 text=f"{auth} reports gaming activity ({r['metric']}) for this facility for the period ending {r['period_end'] or r['as_of_date']}; latest such report (value not carried here)",
                 review="source_asserted", url=r["source_url"], src_date=iso_day(r["as_of_date"]),
                 retrieved=iso_day(r["fetched_date"]), rights="public_official", key_extra="latest_report")

    # ---- 6. operator website: capacity observations
    for r in SITE:
        fid = r["facility_id"]
        if fid not in disp:
            continue
        place = resolved_place(fid)
        ab = r["attribution_basis"]
        if not place or not ab.startswith(SELF_PUB_SINGLE):
            ctx.withheld["site_observation_not_attributable_to_one_facility"] += 1
            continue
        ret = iso_day(r["retrieved_at"])
        public = r["confidence"] == "B" and r["source_url"] not in bad_pages
        add_cap(place, r["metric"], r["value"], r["unit"], "PROPERTY_REPORTED_COUNT", "operator_website",
                r["observation_id"], as_of=ret, prec="observed_on_retrieval_date", attrib=ab,
                quote=r["source_quote"], url=r["source_url"], retrieved=ret,
                rights="public_official" if public else "withheld_unverified")
    for r in SPC:
        fid = r["facility_id"]
        if not fid or fid not in disp or r["also_in_gaming_property_site_observations"] == "Y":
            continue
        place = resolved_place(fid)
        ab = r["attribution_basis"]
        if not place or "not attributable" in ab or r["facility_attribution_status"] == "TRIBE_LEVEL_MULTI_FACILITY_NOT_DISAMBIGUATED":
            ctx.withheld["self_published_claim_not_attributable_to_one_facility"] += 1
            continue
        ret = iso_day(r["retrieved_at"])
        public = (r["confidence"] == "B" and r["measurement_scope"] != "UNVERIFIED_SCOPE"
                  and r["source_url"] not in bad_pages)
        qual = "; ".join(x for x in (r["measurement_scope"], (r["bound_direction"] + " bound") if r["value_is_bounded"] in ("Y", "1", "True") else "") if x)
        add_cap(place, r["metric"], r["value"], r["unit"], "PROPERTY_REPORTED_COUNT", "operator_website",
                r["claim_id"], as_of=ret, prec="observed_on_retrieval_date", qual=qual, attrib=ab,
                quote=r["source_quote"], url=r["source_url"], retrieved=ret,
                rights="public_official" if public else "withheld_unverified")
    for r in LOY:
        fid = r["facility_id"]
        if fid not in disp or not resolved_place(fid):
            continue
        obs = iso_day(r["observation_date"])
        add_cap(resolved_place(fid), "loyalty_program", "", "", "AMENITY_PRESENT", "operator_website",
                r["loyalty_program_id"], as_of=obs, prec="observed_on_retrieval_date", attrib=r["evidence_basis"],
                quote=r["source_quote"], url=r["source_url"], retrieved=obs, value_text=r["program_name"],
                rights="public_official" if r["source_url"] and r["confidence_tier"] in ("A", "B") else "withheld_unverified")

    # ---- 7. operator website: self-published assertions (name, location, status, ownership, dates)
    loc_by_page = defaultdict(dict)
    for r in SPA:
        fid = r["facility_id"]
        cls, sub = r["assertion_class"], r["assertion_subclass"]
        if not fid or fid not in disp or cls.startswith("WITHDRAWN"):
            continue
        place = resolved_place(fid)
        ab = r["attribution_basis"]
        single = ab.startswith(SELF_PUB_SINGLE) and r["record_scope"] == "entity" \
            and r["facility_attribution_status"] != "TRIBE_LEVEL_MULTI_FACILITY_NOT_DISAMBIGUATED"
        if not place or not single or r["source_url"] in bad_pages:
            ctx.withheld["self_published_assertion_not_attributable_or_bad_page"] += 1
            continue
        ret = iso_day(r["retrieved_at"])
        if cls == "SELF_PUBLISHED_LOCATION_ASSERTION":
            loc_by_page[(place, r["source_url"])][sub] = (r["asserted_value"], ret, r["assertion_id"])
        elif cls == "SELF_PUBLISHED_IDENTITY_ASSERTION" and sub in ("legal_or_published_name", "legal_name"):
            v = r["asserted_value"]
            lv = v.lower()
            if re.search(r"casino|resort|bingo|gaming|hotel|sportsbook", lv) and not re.search(
                    r"\btribe\b|\bnation\b|\bband\b|\bindians\b|\bcommunity\b|rancheria\b|pueblo of", lv):
                add_name(place, v, "operator_website", "operator_website", r["assertion_id"], r["source_url"],
                         ret, ret, "observed_on_retrieval_date", r["source_quote"][:300], "public_official",
                         retrieved=ret)
            else:
                ctx.withheld["operator_site_name_is_entity_not_property"] += 1
        elif cls == "SELF_PUBLISHED_IDENTITY_ASSERTION" and sub == "property_type_schema_org":
            ev[place]["schema_type"].append(r["asserted_value"])
        elif cls == "SELF_PUBLISHED_OPERATING_HOURS_ASSERTION":
            add_hist(place, "status_observation", "status_observation", "operator_website", r["assertion_id"],
                     status="operating", date=ret, prec="observed_on_retrieval_date",
                     text="Operator's own site publishes current operating hours: " + r["asserted_value"][:200],
                     review="machine_matched", url=r["source_url"], retrieved=ret, rights="public_official")
        elif cls == "SELF_PUBLISHED_DATE_ASSERTION":
            etype = {"opening": "opening", "in_operation_since": "opening", "renovation": "renovation",
                     "expansion": "expansion", "anniversary": "anniversary_claim",
                     "founding_date": "opening"}.get(sub, "anniversary_claim")
            y = r["asserted_value"]
            iso = y if re.fullmatch(r"\d{4}", y or "") else ""
            add_hist(place, "event", etype, "operator_website", r["assertion_id"], date=iso,
                     prec="year" if iso else "unknown", verbatim=r["asserted_value_verbatim"][:200],
                     qual=f"text-mined claim ({sub}); agrees_with_cedar_open_year={r['agrees_with_cedar_open_year']}",
                     text=r["source_quote"], review="machine_matched", url=r["source_url"], retrieved=ret,
                     rights="withheld_unverified")
            ctx.withheld["history_operator_date_claim_textmined_withheld"] += 1
        elif cls in ("SELF_PUBLISHED_OWNERSHIP_ASSERTION", "SELF_PUBLISHED_MANAGEMENT_ASSERTION"):
            u = good_uid(r["cedar_uid"], "gaming_property_self_published_assertions.cedar_uid")
            agrees = r["agrees_with_curated_owner"].startswith(("SHARES_TOKEN", "AGREE", "EXACT"))
            brand = r["asserted_owner_is_management_brand"] == "Y"
            if brand:
                add_rel(place, "external_company", "brand:" + r["asserted_value"].lower()[:80], "management_contractor",
                        "operator_website", r["assertion_id"], party_name=r["asserted_value"][:120],
                        role=sub, observed=ret, text=r["source_quote"], conf="low", review="machine_matched",
                        url=r["source_url"], retrieved=ret, rights="public_official")
                continue
            if not (u and agrees and r["asserted_owner_names_tribal_form"] != "N"):
                ctx.withheld["ownership_assertion_not_matching_curated_entity"] += 1
                continue
            types = {"owned_by": ["owner"], "owned_and_operated_by": ["owner", "operator"],
                     "enterprise_of": ["owner"], "owner_asserts": ["owner"], "parent_organization": ["owner"],
                     "operated_by": ["operator"]}.get(sub, ["other_documented"])
            for t in types:
                add_rel(place, "native_entity", u, t, "operator_website", r["assertion_id"], cedar_uid=u,
                        party_name=register[u]["canonical_name"], role=f"{sub}: {r['asserted_value'][:120]}",
                        observed=ret, text=r["source_quote"], conf="medium", review="machine_matched",
                        url=r["source_url"], retrieved=ret, rights="public_official")
    for (place, url), parts in sorted(loc_by_page.items()):
        ret = max(v[1] for v in parts.values())
        if "street_address" in parts or "city" in parts:
            ev[place]["self_addr"].append((ret, "operator_website", url, parts.get("street_address", ("",))[0],
                                           parts.get("city", ("",))[0], parts.get("state", ("",))[0],
                                           parts.get("postal_code", ("",))[0]))
        if "latitude" in parts and "longitude" in parts and fnum(parts["latitude"][0]) is not None:
            ev[place]["coord"].append((3, ret, "operator_website", "OPERATOR_WEBSITE_POINT",
                                       parts["latitude"][0], parts["longitude"][0], ""))

    # ---- 8. NIGC map snapshot diffs (universe events)
    for r in UNI:
        fid = r["facility_id"]
        if not fid or fid not in disp or not resolved_place(fid):
            ctx.withheld["universe_event_without_facility"] += 1
            continue
        place = resolved_place(fid)
        nb, na = iso_day(r["from_snapshot_date"]), iso_day(r["to_snapshot_date"])
        et = {"renamed": "renaming", "present_in_snapshot": "regulator_listing_added",
              "absent_from_snapshot": "regulator_listing_removed",
              "coordinates_changed": "regulator_location_changed"}.get(r["event_type"])
        if not et:
            continue
        add_hist(place, "event", et, "nigc_map_snapshot_diff", r["event_id"], date="", prec="unknown",
                 nb=nb, na=na, qual="listing_not_opening" if et != "renaming" else "regulator_listed_name_changed",
                 text=r["event_note"], review="source_asserted", url=r["source_url"], retrieved=na,
                 rights="public_official")
        if et == "renaming" and r["prior_marker_title"]:
            add_name(place, r["prior_marker_title"], "regulator_listed_prior", "nigc_map_snapshot_diff",
                     r["event_id"] + ":prior", r["from_snapshot_url"] or r["source_url"], nb, nb, "day",
                     r["prior_marker_title"], "public_official", retrieved=na)
            add_name(place, r["marker_title"], "regulator_listed", "nigc_map_snapshot_diff",
                     r["event_id"] + ":new", r["to_snapshot_url"] or r["source_url"], na, na, "day",
                     r["marker_title"], "public_official", retrieved=na)

    # ---- 9. SEC management contracts naming a facility
    for r in SECM:
        fid = r["facility_id"]
        if r["adjudication"] != "ACCEPT" or fid not in disp or not resolved_place(fid):
            continue
        fd = iso_day(r["filing_date"])
        add_rel(resolved_place(fid), "external_company", "cik:" + (r["manager_cik"] or r["manager_name"]),
                "management_contractor", "sec_edgar", r["term_id"], party_name=r["manager_name"],
                ext_id=r["manager_cik"], ext_scheme="SEC_CIK" if r["manager_cik"] else "",
                role=r["manager_role"] + (("; term: " + r["contract_expiry_as_stated"]) if r["contract_expiry_as_stated"] else ""),
                observed=fd, text=r["source_quote"], conf="high", review="source_asserted",
                url=r["source_url"], src_date=fd, rights="public_official")
    nmc_facility_named = 0  # NIGC approvals are tribe-level documents; none names a Cedar facility key
    ctx.withheld["nigc_management_contract_approvals_tribe_level_not_emitted"] = len(NMC)

    # ---------------------------------------------------------- assemble facility rows
    for k, v in rel_acc.items():
        ctx.rel[v["relationship_id"]] = v

    per_place = defaultdict(Counter)
    for tbl, key in ((ctx.names, "name"), (ctx.hist, "hist"), (ctx.cap, "cap"), (ctx.rel, "rel")):
        for row in tbl.values():
            per_place[row["_place"]][key] += 1
            if row["rights_class"] in gg.PUBLIC_RIGHTS:
                per_place[row["_place"]][key + "_pub"] += 1
                per_place[row["_place"]]["sys:" + row["source_system"]] += 1

    # A regulator street address shared by 3+ distinct places, or a c/o / P.O.
    # box / HC box string, is an administrative or mailing address (Chickasaw
    # Nation's 2020 Lonnie Abbott Blvd appears on 8 properties). It is not the
    # property's location: withheld, and so is any Census point geocoded from it.
    addr_use = defaultdict(set)
    for place, e in ev.items():
        for t in e["address"]:
            addr_use[addr_key(t[3], t[5])].add(place)
    admin_addr = {k for k, v in addr_use.items() if k and (len(v) >= 3 or ADMIN_ADDR_RE.search(k))}

    names_by_place = defaultdict(list)
    for n in ctx.names.values():
        if n["rights_class"] in gg.PUBLIC_RIGHTS:
            names_by_place[n["_place"]].append(n)

    NAME_PRI = {"regulator_listed": 0, "state_regulator_reported": 1, "federal_dataset": 2,
                "operator_website": 3, "regulator_listed_prior": 9}
    fac_rows = []
    coverage = Counter()
    withheld_fields = Counter()
    qa_groups = {"address_conflict_within_place": [], "two_regulator_listings_in_one_place": [],
                 "public_coordinate_conflict_gt_5km": [], "co_located_distinct_places": [],
                 "vendor_close_vs_regulator_listing": [], "nigc_roster_vs_location_layer_address_conflict": []}
    for place in sorted(facility_places):
        fids = members.get(place, [])
        e = ev[place]
        row = {c: "" for c in _cols(FAC_SPEC)}
        row["gaming_facility_id"] = gfid(place)
        row["cedar_place_id"] = place
        dstates = [disp[f][0] for f in fids]
        # The 2026-08-06 location layer and the 2026-08-26 roster can attach two
        # different NIGC markers to one facility (Thunderbird Casino - Shawnee).
        # The roster link is the name-matched, later listing; a layer address it
        # does not contain is a conflicting marker and its point is not used.
        rk = set(e["roster_keys"])
        conflicting = {k for k in e["layer_keys"] if rk and k and not any(same_street(k, x) for x in rk)}
        if conflicting:
            e["address"] = [t for t in e["address"] if addr_key(t[3], t[5]) not in conflicting]
            e["coord"] = [t for t in e["coord"] if t[6] not in conflicting]
            e["county"] = [t for t in e["county"] if t[4] not in conflicting]
            e["flags"].append("nigc_roster_and_location_layer_name_different_addresses")
            qa_groups["nigc_roster_vs_location_layer_address_conflict"].append(
                {"gaming_facility_id": gfid(place), "roster": sorted(rk), "layer_dropped": sorted(conflicting)})
        if any(f in QUESTIONED for f in fids) and "mapped" not in dstates:
            rs = "held_open_pending_owner_ruling"
        elif "mapped" not in dstates and any("stub" in disp[f][3] or "duplicate" in disp[f][3] for f in fids):
            rs = "cross_reference_stub"
        elif "mapped" not in dstates:
            rs = "disputed_distinctness"
        else:
            rs = "property"
        row["record_status"] = rs
        flags = list(dict.fromkeys(e["flags"]))
        # name
        wf = []
        names = [(n["last_observed"] or n["first_observed"], n["source_system"], n["source_url"], n["name"],
                  n["name_id"], n["name_type"]) for n in names_by_place.get(place, [])]
        names = sorted(names, key=lambda t: (NAME_PRI.get(t[5], 5), "" if not t[0] else "~" + t[0], t[1], t[3]))
        # prefer the most recent within the best-priority class
        if names:
            best_pri = NAME_PRI.get(names[0][5], 5)
            cands = sorted([t for t in names if NAME_PRI.get(t[5], 5) == best_pri], key=lambda t: (t[0], t[3]), reverse=True)
            asof, system, url, name, nid, _ = cands[0]
            row.update(public_name=name, public_name_source_system=system, public_name_source_url=url,
                       public_name_as_of=asof, public_name_rights="public_official")
            ctx.names[nid]["is_selected_public_name"] = "Y"
        else:
            row["public_name_rights"] = "withheld_unverified"
            reason = "vendor_only" if all(_legacy_scheme(f) in ("CCP", "TPL") for f in fids) else "no_independent_source"
            wf.append("name:" + reason)
            withheld_fields["name:" + reason] += 1
        if len(nigc_by_place.get(place, [])) > 1:
            flags.append("two_regulator_listings_in_one_place")
            qa_groups["two_regulator_listings_in_one_place"].append(
                {"gaming_facility_id": gfid(place), "nigc_names": sorted(r["nigc_location_name"] for r in nigc_by_place[place])})
        # facility type
        stype = sorted(e["schema_type"])[0] if e["schema_type"] else ""
        ft, fb = facility_type_from(row["public_name"], "Casino" if "Casino" in e["schema_type"] else "")
        row["facility_type"], row["facility_type_basis"] = ft, fb
        # address
        good_addr = [t for t in e["address"] if addr_key(t[3], t[5]) not in admin_addr]
        if len(good_addr) < len(e["address"]):
            flags.append("regulator_address_is_administrative_or_mailing")
            withheld_fields["street_address:regulator_address_administrative_or_mailing"] += 1
        addr = sorted(good_addr, reverse=True) or sorted(e["self_addr"], reverse=True)
        if addr:
            ret, system, url, street, city, st, z = addr[0]
            row.update(street_address=street, city=city, state=usps(st), postal_code=z, address_source_system=system,
                       address_source_url=url, address_as_of=ret, address_rights="public_official")
        elif len(good_addr) < len(e["address"]) and not e["cityonly"]:
            # administrative/mailing address: the regulator's STATE is still the
            # property's state; street, city and ZIP are not shown.
            ret, system, url, _, _, st, _ = sorted(e["address"], reverse=True)[0]
            row.update(state=usps(st), address_source_system=system, address_source_url=url,
                       address_as_of=ret, address_rights="public_official")
            wf.append("street_address,city,postal_code:regulator_address_administrative_or_mailing")
        elif e["cityonly"]:
            ret, system, url, city, st = sorted(e["cityonly"], reverse=True)[0]
            row.update(city=city, state=usps(st), address_source_system=system, address_source_url=url,
                       address_as_of=ret, address_rights="public_official")
            wf.append("street_address:regulator_publishes_city_only")
            withheld_fields["street_address:regulator_publishes_city_only"] += 1
        else:
            row["address_rights"] = "withheld_unverified"
            reason = "research_compilation_unverified" if e["research_addr"] else "vendor_only" if e["vendor_addr"] else "no_source"
            wf.append("address:" + reason)
            withheld_fields["address:" + reason] += 1
        # address conflicts across the legacy records of one place (vendor+research values: internal flag)
        la = {norm_addr(a) for a in e["vendor_addr"] + e["research_addr"] if a and norm_addr(a)}
        if len(fids) > 1 and len(la) > 1:
            flags.append("address_conflict_within_place")
            qa_groups["address_conflict_within_place"].append(gfid(place))
        # county
        counties = [t for t in e["county"] if t[4] not in admin_addr]
        if counties:
            ret, system, county, fips, _ = sorted(counties, reverse=True)[0]
            row.update(county=county, county_fips=fips, county_source_system=system, county_rights="public_official")
        else:
            row["county_rights"] = "withheld_unverified"
            withheld_fields["county:no_independent_source"] += 1
        # coordinates
        # An administrative/mailing address withholds the Census point geocoded
        # FROM it; NIGC's own published point is a separate fact and stays.
        coords = sorted((t for t in e["coord"] if not (t[3].startswith("CENSUS") and t[6] in admin_addr)),
                        key=lambda t: (t[0], "~" if not t[1] else t[1], t[4], t[5]))
        if coords:
            rank, ret, system, method, lat, lon, _ = coords[0]
            row.update(latitude=lat, longitude=lon, coordinate_source_system=system, coordinate_method=method,
                       coordinate_as_of=ret, coordinate_rights="public_official")
            p0 = (fnum(lat), fnum(lon))
            far = [c for c in coords[1:] if None not in p0 and fnum(c[4]) is not None
                   and haversine_km(p0, (fnum(c[4]), fnum(c[5]))) > 5]
            if far:
                flags.append("public_coordinate_conflict_gt_5km")
                qa_groups["public_coordinate_conflict_gt_5km"].append(gfid(place))
        else:
            row["coordinate_rights"] = "withheld_unverified"
            wf.append("coordinate:no_independent_point")
            withheld_fields["coordinate:no_independent_point"] += 1
        # status
        st_ev = sorted(e["status"], reverse=True)
        if st_ev:
            d, system, url, text = st_ev[0]
            row.update(current_status="operating", status_as_of=d, status_basis=text[:300],
                       status_source_system=system, status_source_url=url, status_rights="public_official")
        else:
            row.update(current_status="unknown", status_rights="withheld_unverified")
            wf.append("status:no_independent_dated_evidence")
            withheld_fields["status:no_independent_dated_evidence"] += 1
        if "vendor_close_evidence_vs_current_regulator_listing" in flags:
            qa_groups["vendor_close_vs_regulator_listing"].append(gfid(place))
        # publication status
        has_name = bool(row["public_name"])
        has_loc = bool(row["city"] and row["state"]) or bool(row["latitude"])
        has_status = row["current_status"] == "operating"
        if rs != "property":
            pub = "unresolved"
        elif has_name and has_loc and has_status:
            pub = "public"
        elif has_name or has_loc or has_status:
            pub = "source_limited"
        else:
            pub = "withheld"
        row["publication_status"] = pub
        coverage["publication_status:" + pub] += 1
        if has_name and has_loc and has_status:
            coverage["name_location_status_all_independent"] += 1
        for k, v in (("has_public_name", has_name), ("has_public_location", has_loc),
                     ("has_public_status", has_status), ("has_public_street_address", bool(row["street_address"])),
                     ("has_public_coordinate", bool(row["latitude"]))):
            coverage[k] += int(v)
        pp = per_place[place]
        row.update(n_legacy_records=str(len(fids)),
                   n_independent_sources=str(sum(1 for k in pp if k.startswith("sys:"))),
                   n_name_rows=str(pp["name"]), n_public_name_rows=str(pp["name_pub"]),
                   n_history_rows=str(pp["hist"]), n_public_history_rows=str(pp["hist_pub"]),
                   n_capacity_rows=str(pp["cap"]), n_public_capacity_rows=str(pp["cap_pub"]),
                   n_relationship_rows=str(pp["rel"]), n_public_relationship_rows=str(pp["rel_pub"]))
        # dedup basis
        if len(fids) > 1:
            kinds = Counter(disp[f][0] for f in fids)
            basis = "alias group: " + ", ".join(f"{k}={n}" for k, n in sorted(kinds.items()))
            basis += "; one operator, one property, two vintages (1129 P2)" if any(
                adj_by_fid.get(f, {}).get("rule", "").startswith("P2") for f in fids) else ""
            basis += "; addresses disagree across vintages - possible relocation or address renaming, not asserted as an event" \
                if "address_conflict_within_place" in flags else "; addresses agree after normalisation"
        else:
            basis = "single legacy record"
        if any(f in QUESTIONED for f in fids):
            basis += "; carries a held-open record (" + ",".join(f for f in fids if f in QUESTIONED) +                 ") whose operator attribution awaits an owner ruling"
        h = next((hold[f] for f in fids if f in hold), None)
        if h:
            basis += f"; held-open group {h['group']}: {h['disposition']} ({h['confidence']})"
            if h["disposition"] == "SETTLED_SEPARATE":
                qa_groups["co_located_distinct_places"].append({"group": h["group"], "gaming_facility_id": gfid(place)})
        row["dedup_basis"] = basis
        row["withheld_fields"] = ";".join(wf)
        row["qa_flags"] = ";".join(sorted(set(flags)))
        fac_rows.append(row)

    # ---------------------------------------------------------- crosswalk
    xw = []
    regn_marker = defaultdict(set)
    for r in REGN:
        if r["nigc_marker_id"]:
            regn_marker[r["facility_id"]].add(r["nigc_marker_id"])
    nigc_by_fid = defaultdict(list)
    for r in NIGC:
        nigc_by_fid[r["facility_id"]].append(r)
    ca_by_fid = defaultdict(list)
    for r in CA:
        if r["facility_id"]:
            ca_by_fid[r["facility_id"]].append(r)
    for fid in sorted(byfid):
        r = byfid[fid]
        d, tgt, cand, why = disp[fid]
        place = r["cedar_place_id"]
        live = resolved_place(fid)
        base = {"legacy_facility_id": fid, "legacy_id_scheme": _legacy_scheme(fid),
                "gaming_facility_id": gfid(live), "cedar_place_id": place,
                "place_binding_role": binding.get(fid, ""), "disposition": d, "disposition_basis": why,
                "merged_into_gaming_facility_id": gfid(tgt) if d == "merged_into" else "",
                "candidate_gaming_facility_id": gfid(cand) if cand else "",
                "publication_status": "unresolved" if not place else "internal",
                "rights_class": "internal_crosswalk"}
        keys = [("legacy_facility_id", fid, "gaming_facilities")]
        if r["casino_city_id"]:
            keys.append(("casino_city_id", r["casino_city_id"].replace(".0", ""), "gaming_facilities"))
        for n in nigc_by_fid.get(fid, []):
            keys.append(("nigc_map_location", n["nigc_location_name"] + " | " + n["nigc_address"], "gaming_nigc_roster_link"))
        for m in sorted(regn_marker.get(fid, ())):
            keys.append(("nigc_marker_id", m, "nigc_region_assignments"))
        for c in ca_by_fid.get(fid, []):
            keys.append(("ca_cgcc_record_id", c["record_id"], "ca_gaming_facilities_official"))
        if place:
            keys.append(("cedar_place_id", place, "cedar_place_id_register"))
        seen = set()
        for scheme, val, src in keys:
            if (scheme, val) in seen:
                continue
            seen.add((scheme, val))
            xw.append(dict(base, key_scheme=scheme, key_value=val, source_table=src))

    # ---------------------------------------------------------- write
    def strip(rows):
        return [{k: (str(v) if not isinstance(v, str) else v) for k, v in r.items() if not k.startswith("_")} for r in rows]

    out = {}
    tables = []
    for table, spec, rows in (
            ("gaming_grove_facilities.csv", FAC_SPEC, fac_rows),
            ("gaming_facility_crosswalk.csv", XW_SPEC, xw),
            ("gaming_facility_names.csv", NAME_SPEC, list(ctx.names.values())),
            ("gaming_facility_history.csv", HIST_SPEC, list(ctx.hist.values())),
            ("gaming_facility_capacity.csv", CAP_SPEC, list(ctx.cap.values())),
            ("gaming_facility_relationships.csv", REL_SPEC, list(ctx.rel.values()))):
        rows = strip(rows)
        c = CONTRACTS[table]
        rec = gg.write_table(out_dir, table, _cols(spec), rows, c)
        rr = c["row_rights_column"]
        if rr:
            rec["rows_public"] = sum(1 for x in rows if x[rr] in gg.PUBLIC_RIGHTS)
            rec["rows_by_rights_class"] = dict(sorted(Counter(x[rr] for x in rows).items()))
        rec["publication_status"] = c["publication_status"]
        rec["fields_public"] = sum(1 for v in c["field_rights"].values() if v in gg.PUBLIC_RIGHTS)
        rec["fields_internal"] = sum(1 for v in c["field_rights"].values() if v not in gg.PUBLIC_RIGHTS)
        tables.append(rec)
        out[table] = rows

    # ---------------------------------------------------------- QA / receipt
    disp_counts = Counter(v[0] for v in disp.values())
    nest_gaming = 0
    fac_uids = {r["cedar_uid"] for r in out["gaming_facility_relationships.csv"] if r["cedar_uid"]}
    for r in NEST:
        if re.search(r"casino|gaming|bingo", (r.get("sector", "") + " " + r.get("enterprise_name", "")).lower()) \
                and r.get("owner_hub_cedar_uid") in fac_uids:
            nest_gaming += 1
    legacy_scan = legacy_prefix_scan({
        "data/clean/gaming_facilities.csv": F, "data/clean/gaming_nigc_roster_link.csv": NIGC,
        "data/clean/ca_gaming_facilities_official.csv": CA, "data/clean/gaming_capacity_official.csv": CAPO,
        "data/clean/gaming_property_site_observations.csv": SITE,
        "data/clean/gaming_property_self_published_assertions.csv": SPA,
        "data/clean/gaming_property_self_published_claims.csv": SPC,
        "data/clean/gaming_web_harvest_observations.csv": WEB,
        "data/clean/gaming_property_universe_events.csv": UNI,
        "data/clean/gaming_property_federal_traces.csv": TRACE,
        "data/clean/loyalty_program_property.csv": LOY,
        "data/clean/nigc_management_contract_approvals.csv": NMC,
        "data/clean/nigc_region_assignments.csv": REGN,
        "data/spine/cedar_place_id_register.csv": PREG})
    roster_defects = 0
    groups = defaultdict(list)
    for fid, (d, tgt, cand, why) in sorted(disp.items()):
        if d == "merged_into":
            groups[gfid(tgt)].append(fid)
    shared_addr = defaultdict(set)
    for row in fac_rows:
        if row["street_address"] and row["state"]:
            shared_addr[(norm_addr(row["street_address"]), row["state"])].add(row["gaming_facility_id"])
    shared_public = {f"{a} ({s})": sorted(v) for (a, s), v in sorted(shared_addr.items()) if len(v) > 1}

    qa = {
        "legacy_rows": len(F),
        "legacy_rows_with_disposition": len(disp),
        "dispositions": dict(sorted(disp_counts.items())),
        "unresolved_legacy_rows": sorted(f for f, v in disp.items() if v[0] == "unresolved"),
        "not_a_gaming_facility_rows": sorted(f for f, v in disp.items() if v[0] == "not_a_gaming_facility"),
        "merged_into_cross_place": sorted(f for f, v in disp.items() if v[0] == "merged_into" and v[1] != place_of.get(f)),
        "alias_groups_n": sum(1 for p in members if len(members[p]) > 1),
        "alias_groups_with_address_conflict": sorted(qa_groups["address_conflict_within_place"]),
        "places_with_two_regulator_listings": qa_groups["two_regulator_listings_in_one_place"],
        "public_coordinate_conflicts_gt_5km": sorted(qa_groups["public_coordinate_conflict_gt_5km"]),
        "co_located_distinct_places_held_apart": qa_groups["co_located_distinct_places"],
        "nigc_roster_vs_location_layer_address_conflict": qa_groups["nigc_roster_vs_location_layer_address_conflict"],
        "vendor_close_vs_current_regulator_listing": sorted(qa_groups["vendor_close_vs_regulator_listing"]),
        "distinct_facilities_sharing_a_public_street_address": shared_public,
        "multi_operator": {
            "the_stables": "CCP-305300 kept live with both Miami (CE-0016Y-PQ) and Modoc (CE-00175-5P) as affiliates (internal_vendor evidence); VP-0153 unresolved, candidate = same facility",
            "7_clans_first_council": "CCP-843900 (Otoe-Missouria, NIGC-listed) live; VP-0170 (Ponca) unresolved + relationship reviewed_disputed",
            "7_clans_ponca": "VP-0169 unresolved (ruled not distinct, no target); its Ponca affiliation unresolved",
        },
        "facility_places_total": len(fac_rows),
        "facility_places_expected_le_717": len(fac_rows) <= 717,
        "withheld_field_counts": dict(sorted(withheld_fields.items())),
    }
    receipt = {
        "script": SCRIPT, "schema_version": gg.SCHEMA_VERSION, "id_contract_status": gg.ID_CONTRACT_STATUS,
        "tables": tables, "inputs": dict(sorted(inputs.receipts.items())),
        "coverage": dict(sorted(coverage.items())),
        "withheld": dict(sorted(ctx.withheld.items())),
        "defects_found_in_inputs": dict(sorted(ctx.defects.items())),
        "legacy_prefix_scan": legacy_scan,
        "nest_gaming_enterprise_candidates_not_linked": nest_gaming,
        "qa": qa,
        "notes": ctx.notes + [
            "gaming_web_harvest_observations duplicates self_published assertions (861/861 identity rows) and claims (314/314 capacity rows) by (source_url, value); used here only for its page_verdict gate.",
            "gaming_facility_metrics (68,211 Casino City rows) and gaming_property_capacity_history (64,181) are not read: vendor lineage, internal only; the latest vendor value per metric is carried from gaming_facilities as internal_vendor rows.",
            "Land/decision dates (gaming_properties.earliest_land_decision_date) are not history events here: a decision is not an opening.",
        ],
    }
    return receipt


LEGACY_COLS = re.compile(r"(cedar_uid|entity_id|tribe_id|entity_ids)$")


def legacy_prefix_scan(tables: dict) -> dict:
    """Count entity identifiers that are not canonical CE- uids, per table/column.
    Feeds the CICD identifier-retirement audit; nothing is translated here."""
    out = {}
    for path, rows in sorted(tables.items()):
        if not rows:
            continue
        for col in sorted(rows[0]):
            if not LEGACY_COLS.search(col):
                continue
            cnt = Counter()
            for r in rows:
                for v in re.split(r"[|;]", r.get(col) or ""):
                    v = v.strip()
                    if not v:
                        continue
                    if v.startswith("CE-"):
                        cnt["CE_valid" if gg.is_ce_uid(v) else "CE_invalid"] += 1
                    else:
                        cnt[(re.match(r"^[A-Za-z]+", v).group(0) if re.match(r"^[A-Za-z]+", v) else "other") + "-"] += 1
            legacy = {k: n for k, n in cnt.items() if k != "CE_valid"}
            if legacy:
                out[f"{path}::{col}"] = dict(sorted(cnt.items()))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--input-root", default=str(gg.DEFAULT_INPUT_ROOT))
    b.add_argument("--output-root", required=True)
    b.add_argument("--as-of", default="")
    a = ap.parse_args(argv)
    out_dir = Path(a.output_root)
    receipt = build(gg.Inputs(a.input_root), out_dir)
    if a.as_of:
        receipt["as_of"] = a.as_of
    (out_dir / RECEIPT).write_text(json.dumps(receipt, sort_keys=True, indent=1, ensure_ascii=False) + "\n",
                                   encoding="utf-8", newline="\n")
    cov = receipt["coverage"]
    print(f"facilities={receipt['qa']['facility_places_total']} "
          f"public={cov.get('publication_status:public', 0)} "
          f"name+location+status={cov.get('name_location_status_all_independent', 0)}")
    for t in receipt["tables"]:
        print(f"  {t['table']}: {t['rows']} rows ({t.get('rows_public', '-')} public) sha256={t['sha256'][:12]}")


if __name__ == "__main__":
    main()
