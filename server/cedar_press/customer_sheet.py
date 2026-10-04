"""The customer spreadsheet: one flat table per collection, at its declared grain.

Owner rules, 2026-10-04 (Elijah Moreno), for every published collection:

1. Identifiers. The only identifiers customers see are Cedar IDs (``CE-``,
   ``CB-`` and ``CEDAR-`` identifiers). Internal keys are removed: source
   record IDs, legacy ``CCP-``/``VP-``/``NESTREL-`` keys, relationship keys,
   row hashes, dedup bases, batch IDs and ``[legacy record]`` placeholders.
   External public registry identifiers (EIN, UEI, CAGE, FAIN, document
   numbers and the like) stay, listed in ``PUBLIC_REGISTRY_ID_COLUMNS`` for the
   owner to rule on. DUNS is a private, proprietary identifier and is removed
   everywhere (owner decision, 2026-10-04).
2. Sources. A published source is a real public citation. A value that points
   at a local spreadsheet, path, terminal, desktop, workstation, dissertation
   workspace, notebook or "manual" entry is traced to the component's recorded
   public origin when one is recorded, and is otherwise left blank and counted.
   Nothing is invented.
3. No version labels. Release, contract, transform and schema version columns
   and version-label values stay internal.
4. One table. Customers get one flat table per collection, designed from its
   grain in ``LAYOUTS``: related-table detail becomes columns on the main row
   or is left out of the customer table (and kept internally).

This module only presents rows the caller has already verified. It never
touches release bytes, hashes or manifests, so internal verification and
provenance are unchanged. It is pure Python with no dependencies and is
vendored byte for byte into cedar-press (``server/cedar_press/customer_sheet.py``);
a test on each side compares the two copies.
"""

from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Callable, Generator, Iterable, Mapping
from typing import Any

#: Internal only; never written into customer data.
POLICY = "customer-sheet-2026-10-04"

Row = dict[str, Any]

# -- Rule 1: identifiers ------------------------------------------------------

CEDAR_ID = re.compile(
    r"^(?:CE-[0-9A-Z]{5}-[0-9A-Z]{2}"
    r"|CB-[0-9]{7}"
    r"|CEDAR-(?:NEST|PLACE|ENT|NEED)-[0-9]{6}-[0-9A-Z]{2}"
    r"|CEDAR-(?:OBS|EVENT|REL|SRC|CONTRACT)-[0-9]{6,9})$"
)
#: Retired or vendor keys that must never reach a customer, inside any cell.
INTERNAL_KEY = re.compile(
    r"^(?:\[legacy record\]"
    r"|(?:CCP|VP|TPL|CEDAR-FAC)-[0-9]+"
    r"|(?:NESTREL|NEID|CICD)[-_][A-Za-z0-9_-]+"
    r"|TRBF-[A-Z0-9]+-[0-9]+|NEST-[0-9a-f]{6,}-[A-Z0-9]+|lsg_[0-9a-f]+"
    r"|GKEY~.*"
    r"|[0-9a-f]{40}|[0-9a-f]{64})$"
)
#: Kept: identifiers issued by an external public registry. The owner decides
#: on each (2026-10-04); they are listed per collection in every export report.
PUBLIC_REGISTRY_ID_COLUMNS = frozenset(
    {
        # IRS
        "ein",
        "funder_ein",
        "recipient_ein",
        "owner_ein",
        "enterprise_ein",
        # SAM.gov
        "uei",
        "awardee_uei",
        "recipient_uei",
        "parent_uei",
        "prime_uei",
        "prime_parent_uei",
        "subcontractor_uei",
        "subcontractor_parent_uei",
        "fpds_declared_parent_uei",
        "owner_uei",
        "enterprise_uei",
        "cage_code",
        "prime_cage",
        "prime_parent_cage",
        "subcontractor_cage",
        "subcontractor_parent_cage",
        "owner_cage",
        "enterprise_cage_code",
        # FPDS / USAspending / FSRS
        "fain",
        "award_id_fain",
        "piid",
        "contract_number",
        "parent_contract_number",
        "federal_contract_number",
        "transaction_id",
        "award_id",
        "prime_award_id",
        "prime_award_unique_key",
        "subaward_number",
        "report_id",
        # Federal Register, Congress, Senate LDA
        "document_number",
        "fr_document_number",
        "docket_ids",
        "docket_number",
        "regulation_id_numbers",
        "bill_id",
        "bill_number",
        "companion_bill_id",
        "sponsor_bioguide_id",
        "registrant_id",
        "client_id",
        # EPA, assessors, permitting and certifying authorities, USPTO
        "facility_registry_id",
        "ghgrp_id",
        "source_parcel_id",
        "permit_number",
        "application_number",
        "certification_number",
        "business_license_number",
        "patent_number",
    }
)
#: A registry column that, in one collection, actually holds an internal key.
COLLECTION_INTERNAL_COLUMNS = {
    "foundation-corporate-giving": frozenset({"award_id"}),
}
#: Internal by name, whatever the values look like.
INTERNAL_ID_COLUMNS = frozenset(
    {
        "record_key",
        "record_type",
        "record_grain",
        "source_record_id",
        "source_row_number",
        "source_id",
        "source_edition",
        "source_dataset",
        "consultation_record_key",
        "supersession_group_id",
        "superseded_by_record_id",
        "subject_binding",
        "evidence_key",
        "hold_codes",
        "hold_id",
    }
)
#: Columns whose identifiers are Cedar IDs; a non-Cedar value in one is removed.
CEDAR_ID_COLUMNS = frozenset(
    {
        "enterprise_id",
        "parent_enterprise_id",
        "owner_enterprise_ids",
        "gaming_facility_id",
        "beneficiary_entity_id",
        "operator_entity_id",
        "payer_entity_id",
        "certifying_authority_entity_id",
    }
)
_CEDAR_NAME = re.compile(r"cedar_uids?$|cedar_business_uid$|(?:^|_)business_uid$")
#: Retired identity schemes and vendor directory keys (NEID, CICD, Casino City):
#: legacy keys, never presented, by column name or inside a value. Reuses the
#: patterns of cedar-press code/cedar_publication.py.
LEGACY_SCHEME_COLUMN = re.compile(r"neid|cicd|casino[ _-]?city|tribe_id", re.I)
LEGACY_SCHEME_VALUE = re.compile(r"(?<![a-z])(neid|cicd|casino[ _-]?city)(?![a-z])", re.I)
_INTERNAL_NAME = re.compile(r"sha256|hash|dedup|batch|legacy|_binding$|candidate|crosswalk")
_ID_NAME = re.compile(r"(?:^|_)(?:id|ids|uid|uids|key|keys)$")
_DUNS_NAME = re.compile(r"duns", re.I)
#: A coverage statistic about DUNS carries no identifier (owner, 2026-10-04).
_DUNS_STATISTIC = re.compile(r"^(?:pct|share|n|count|rate)_|_(?:pct|share|count|rate)$")
_DUNS_TOKEN = re.compile(r"\bDUNS\b[\s:#=-]*(?:No\.?|number)?[\s:#=-]*\d{9}\b", re.I)
#: A generic identifier pair whose scheme column names DUNS.
_SCHEME_PAIRS = (
    ("identifier_type", "identifier_value"),
    ("identifier_scheme", "identifier_value"),
    ("key_scheme", "key_value"),
    ("party_external_id_scheme", "party_external_id"),
    ("id_type", "id_value"),
)

# -- Rule 2: sources -----------------------------------------------------------

SOURCE_COLUMNS = frozenset(
    {
        "source",
        "sources",
        "source_url",
        "source_urls",
        "additional_sources",
        "source_system",
        "source_locator",
        "source_citation",
        "citation",
        "citations",
        "evidence_pins",
        "evidence_url",
        "evidence_urls",
        "data_sources",
        "source_document",
        "verification_source",
        "classification_source",
    }
)
_SOURCE_NAME = re.compile(r"(?:^|_)(?:url|urls|source_system|source_url)$")
#: A whole column that only ever records a local location.
_LOCAL_COLUMN = re.compile(r"(?:^|_)(?:path|paths|file|files|inbox)$")
_URL = re.compile(r"^https?://[^\s]+$", re.I)
_LOCAL_SOURCE = re.compile(
    r"(?:^|[\s(\"'])(?:[A-Za-z]:[\\/]|~[/\\]|file:|\\\\|"
    r"/(?:Users|home|mnt|tmp|var|opt|private|Volumes|root|workspace|data)/)"
    r"|(?<![A-Za-z])(?:spreadsheet|terminal|desktop|workstation|dissertation|notebook|"
    r"jupyter|scratchpad|scratch|workspace|onedrive|dropbox|google drive|my drive|"
    r"local (?:file|copy|drive|machine|folder)|manual(?:ly)?)(?![A-Za-z])"
    r"|\.(?:xlsx|xlsm|xls|csv|tsv|dta|sav|rds|rdata|parquet|feather|jsonl|json|ipynb|"
    r"py|sqlite|db|zip|7z|gz|docx|doc|txt)(?![A-Za-z0-9])",
    re.I,
)

# -- Rule 3: versions ----------------------------------------------------------

_VERSION_NAME = re.compile(
    r"(?:^|_)(?:schema|contract|transform|release|policy|producer|pipeline|build)_?"
    r"(?:version|id|class|sha|commit)$|(?:^|_)version$|^versions?$"
)
_VERSION_VALUE = re.compile(r"^(?:[A-Za-z][\w.-]*[-_.])?[vV]\d+(?:\.\d+){0,3}$")
#: A version-named column that holds a real-world attribute, renamed instead.
VERSION_RENAMES = {"version_kind": "revision_kind"}

# -- Rule 4: one table per collection ------------------------------------------
#
# ``main`` lists alternatives: the first with any of its tables present is used.
# Tables in one alternative share one grain and are stacked; ``kind`` names a
# column that says which one a row came from. ``attach`` adds detail from a
# related table as columns of the main row, matched on exact keys; aggregation
# is ``distinct`` (sorted unique values joined with "; "), ``count``, ``min`` or
# ``max``. ``left_out`` documents related tables kept internal. A collection
# with one presented table needs no layout.

LAYOUTS: dict[str, dict[str, Any]] = {
    "federal-register": {
        "grain": "One Federal Register document affecting Indian Country.",
        "main": [{"tables": ["federal_actions"]}],
        "attach": [
            {
                "table": "consultation_participants",
                "on": "document_number",
                "key": "fr_document_number",
                "columns": {
                    "consultation_cedar_uids": ["cedar_uid", "distinct"],
                    "consultation_entity_names": ["canonical_name", "distinct"],
                    "consultation_participant_names": ["participant_name", "distinct"],
                    "consultation_participant_count": ["participant_name", "count"],
                    "consultation_activity_types": ["activity_type", "distinct"],
                    "consultation_start_date": ["event_start_date", "min"],
                    "consultation_comment_deadline": ["comment_deadline", "min"],
                },
            }
        ],
        "left_out": {
            "consultation_participants": "Participants without a matching Federal Register "
            "document stay internal; matched ones are summarized as columns."
        },
    },
    "foundation-corporate-giving": {
        "grain": "One source disclosure of a gift or grant; not an additive award.",
        "main": [
            {
                "tables": ["reviewed_disclosures", "policy_eligible_disclosures"],
                "kind": "review_level",
                "labels": {
                    "reviewed_disclosures": "independently reviewed",
                    "policy_eligible_disclosures": "source disclosure",
                },
            }
        ],
    },
    "gaming": {
        "grain": "One physical gaming facility, with its owning and operating entities.",
        "main": [{"tables": ["gaming_grove_facilities"]}],
        "drop": ["cedar_place_id"],
        "attach": [
            {
                "table": "gaming_facility_relationships",
                "on": "gaming_facility_id",
                "key": "gaming_facility_id",
                "where": {"relationship_type": ["owner"]},
                "columns": {
                    "owner_cedar_uids": ["cedar_uid", "distinct"],
                    "owner_names": ["party_name", "distinct"],
                    "owner_enterprise_ids": ["enterprise_id", "distinct"],
                },
            },
            {
                "table": "gaming_facility_relationships",
                "on": "gaming_facility_id",
                "key": "gaming_facility_id",
                "where": {"relationship_type": ["operator", "operated_by"]},
                "columns": {
                    "operator_cedar_uids": ["cedar_uid", "distinct"],
                    "operator_names": ["party_name", "distinct"],
                },
            },
            {
                "table": "gaming_facility_relationships",
                "on": "gaming_facility_id",
                "key": "gaming_facility_id",
                "columns": {"relationship_source_urls": ["source_url", "distinct"]},
            },
            {
                "table": "gaming_facility_names",
                "on": "gaming_facility_id",
                "key": "gaming_facility_id",
                "where": {"is_selected_public_name": ["N"]},
                "columns": {"other_names": ["name", "distinct"]},
            },
        ],
        "left_out": {
            "*": "Compacts, revenue, payments, regulatory, land, licence, litigation, "
            "labor, capacity and sportsbook tables have other grains and stay internal."
        },
    },
    "infrastructure": {
        "grain": "One Native entity's infrastructure profile.",
        "main": [{"tables": ["profiles"]}],
        "left_out": {"*": "Annual, spatial, asset and supporting tables stay internal."},
    },
    "need": {
        "grain": "One enterprise a Native entity owns, with its owner and parent enterprise.",
        "main": [
            {
                "tables": ["reviewed_public_base"],
                "rename": {"evidence_pins": "source_urls"},
                "attach_ref": "enterprises",
            },
            {
                "tables": ["enterprises"],
                "rename": {
                    "asserted_owner_hub_cedar_uid": "owner_cedar_uid",
                    "owner_hub_name": "owner_entity_name",
                    "parent_name": "parent_enterprise_name",
                },
            },
        ],
        "attach": [
            {
                "table": "enterprises",
                "on": "enterprise_id",
                "key": "enterprise_id",
                "only_with": "reviewed_public_base",
                "columns": {
                    "owner_cedar_uid": ["asserted_owner_hub_cedar_uid", "distinct"],
                    "owner_entity_name": ["owner_hub_name", "distinct"],
                    "parent_enterprise_id": ["parent_enterprise_id", "distinct"],
                    "parent_enterprise_name": ["parent_name", "distinct"],
                },
            }
        ],
        "left_out": {
            "*": "Source observations, enrichment, patent, rating and review tables stay internal."
        },
    },
    "plot": {
        "grain": "One land observation: a BIA tract or an assessor parcel.",
        "main": [
            {
                "tables": ["tract_observations", "ownership_observations"],
                "kind": "land_record_kind",
                "labels": {
                    "tract_observations": "BIA tract",
                    "ownership_observations": "assessor parcel",
                },
            }
        ],
        "left_out": {"*": "Permit and EPA tables have other grains and stay internal."},
    },
}

LIST_SEPARATOR = "; "
#: Column classes that never reach a customer.
REMOVED_CLASSES = frozenset({"private_id", "internal_id", "version", "local_source"})


# -- Classification ------------------------------------------------------------


def is_private_identifier(name: str) -> bool:
    """A DUNS column: licensed for internal matching only, never published.

    cedar-press docs/PUBLICATION_POLICY.md (2026-09-02): "Casino City and
    D-U-N-S are licensed to Cedar for internal use and never ship, in any
    dataset, at any tier"; reaffirmed 2026-10-04. A coverage statistic such as
    ``pct_with_duns`` names no identifier and stays.
    """
    lowered = name.lower()
    return bool(_DUNS_NAME.search(lowered)) and not _DUNS_STATISTIC.search(lowered)


def column_class(collection: str, name: str) -> str:
    """How a source column is presented.

    ``private_id`` (DUNS), ``internal_id``, ``version`` and ``local_source`` are
    removed. ``registry_id`` is kept and reported. ``cedar_id`` keeps only Cedar
    ID values. Any other identifier-shaped name is internal. ``source`` values
    are checked for local origins. Everything else is ``data``. The decision
    depends on the name alone, so a preview and its full table share a header.
    """
    lowered = name.lower()
    if is_private_identifier(lowered):
        return "private_id"
    if lowered in VERSION_RENAMES:
        return "data"
    if LEGACY_SCHEME_COLUMN.search(lowered):
        return "internal_id"
    if _VERSION_NAME.search(lowered):
        return "version"
    if lowered in COLLECTION_INTERNAL_COLUMNS.get(collection, frozenset()):
        return "internal_id"
    if lowered in PUBLIC_REGISTRY_ID_COLUMNS:
        return "registry_id"
    if lowered in INTERNAL_ID_COLUMNS or _INTERNAL_NAME.search(lowered):
        return "internal_id"
    if _LOCAL_COLUMN.search(lowered):
        return "local_source"
    if lowered in SOURCE_COLUMNS or _SOURCE_NAME.search(lowered):
        return "source"
    if lowered in CEDAR_ID_COLUMNS or _CEDAR_NAME.search(lowered):
        return "cedar_id"
    if _ID_NAME.search(lowered):
        return "internal_id"
    return "data"


def is_cedar_id(value: Any) -> bool:
    return isinstance(value, str) and CEDAR_ID.fullmatch(value) is not None


def is_local_source(value: str) -> bool:
    """A source value that names a local location rather than a public citation."""
    text = value.strip()
    if not text or _URL.fullmatch(text):
        return False
    return _LOCAL_SOURCE.search(text) is not None


def is_version_label(value: Any) -> bool:
    return isinstance(value, str) and _VERSION_VALUE.fullmatch(value.strip()) is not None


def _elements(value: Any) -> tuple[list[Any], Callable[[list[Any]], Any]] | None:
    """The members of a list-valued cell and how to write them back, or None."""
    if isinstance(value, list):
        return value, lambda items: items
    if not isinstance(value, str):
        return None
    text = value.strip()
    if text.startswith("["):
        try:
            parsed = json.loads(text)
        except ValueError:
            return None
        if isinstance(parsed, list):
            return parsed, lambda items: json.dumps(
                items, ensure_ascii=False, separators=(",", ":")
            )
        return None
    for separator in ("|", ";"):
        if separator in text:
            parts = [part.strip() for part in text.split(separator)]
            joiner = separator if separator == "|" else LIST_SEPARATOR
            return parts, lambda items, joiner=joiner: joiner.join(items)
    return None


def _blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip()) or value == []


def _cedar_only(value: Any) -> tuple[Any, int]:
    """Keep only Cedar ID values; count the removed ones."""
    if _blank(value):
        return None, 0
    if is_cedar_id(value):
        return value, 0
    found = _elements(value)
    if found is None:
        return None, 1
    items, rebuild = found
    kept = list(dict.fromkeys(item for item in items if is_cedar_id(item)))
    removed = sum(1 for item in items if not _blank(item) and not is_cedar_id(item))
    return (rebuild(kept) if kept else None), removed


def _urls(value: Any) -> list[str] | None:
    """Public URLs carried by a structured source cell (JSON pins, link lists)."""
    if isinstance(value, str) and value.strip()[:1] in "[{":
        try:
            value = json.loads(value)
        except ValueError:
            return None
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        return None
    found = []
    for item in value:
        if isinstance(item, dict):
            for key in ("url", "source_url", "href", "link"):
                candidate = item.get(key)
                if isinstance(candidate, str):
                    found.append(candidate)
        elif isinstance(item, str):
            found.append(item)
    return found


def present_source(value: Any, origin: str | None) -> tuple[Any, str]:
    """A source cell for customers and what happened to it.

    Status is ``empty``, ``public``, ``partial`` (local members of a list
    removed, public ones kept), ``traced`` (a local value replaced by the
    recorded public origin) or ``blanked`` (local, with no recorded origin).
    """
    if _blank(value):
        return None, "empty"
    structured = _urls(value)
    if structured is not None:
        if not structured:
            return None, "empty"
        kept = [url for url in structured if url.strip() and not is_local_source(url)]
        if kept:
            status = "public" if len(kept) == len(structured) else "partial"
            return LIST_SEPARATOR.join(dict.fromkeys(kept)), status
        return (origin, "traced") if origin else (None, "blanked")
    text = str(value)
    found = _elements(text)
    if found is not None and found[0] and all(isinstance(item, str) for item in found[0]):
        items, rebuild = found
        local = [item for item in items if is_local_source(item)]
        if not local:
            return text, "public"
        kept = [item for item in items if item and not is_local_source(item)]
        if kept:
            return rebuild(kept), "partial"
        return (origin, "traced") if origin else (None, "blanked")
    if not is_local_source(text):
        return text, "public"
    return (origin, "traced") if origin else (None, "blanked")


def public_origin(url: Any) -> str | None:
    """A component's recorded source URL, when it is a public web address."""
    return url if isinstance(url, str) and _URL.fullmatch(url.strip()) else None


def _scrub_data(value: Any, counts: dict[str, int], *, edition: bool = False) -> Any:
    """Remove internal keys, DUNS tokens and version labels inside a data cell.

    ``edition`` marks a column that records a public source's own edition
    (``source_vintage``): its label is a citation detail, not a Lumecon version.
    """
    if not isinstance(value, (str, list)):
        return value
    if isinstance(value, str):
        if INTERNAL_KEY.fullmatch(value.strip()) or LEGACY_SCHEME_VALUE.search(value):
            counts["internal_key_values_blanked"] += 1
            return None
        if is_version_label(value) and not edition:
            counts["version_label_values_blanked"] += 1
            return None
        if _DUNS_TOKEN.search(value):
            counts["duns_values_removed"] += 1
            value = _DUNS_TOKEN.sub("", value).strip(" ;,|") or None
            return value
    found = _elements(value)
    if found is None:
        return value
    items, rebuild = found
    kept = [
        item
        for item in items
        if not (isinstance(item, str) and (INTERNAL_KEY.fullmatch(item) or is_version_label(item)))
    ]
    if len(kept) != len(items):
        counts["internal_key_values_blanked"] += len(items) - len(kept)
        return rebuild(kept) if any(not _blank(item) for item in kept) else None
    return value


# -- Layout --------------------------------------------------------------------


class LayoutError(ValueError):
    """The collection has no customer table that can be built from this release."""


def choose_layout(collection: str, available: Iterable[str]) -> dict[str, Any]:
    """The customer layout to apply to a release's presented tables."""
    present = list(dict.fromkeys(available))
    spec = LAYOUTS.get(collection)
    if spec is None:
        if len(present) != 1:
            raise LayoutError(
                f"{collection} presents {len(present)} tables and declares no customer layout"
            )
        return {"grain": None, "main": {"tables": present}, "attach": [], "left_out": {}}
    for declared in spec["main"]:
        # A stacked grain needs at least one of its tables; absent ones add no rows.
        tables = [table for table in declared["tables"] if table in present]
        if not tables:
            continue
        alternative = {**declared, "tables": tables}
        attach = [
            item
            for item in spec.get("attach", [])
            if item["table"] in present and item.get("only_with", declared["tables"][0]) in tables
        ]
        return {
            "grain": spec["grain"],
            "main": alternative,
            "attach": attach,
            "drop": spec.get("drop", []),
            "left_out": {
                table: spec.get("left_out", {}).get(table) or spec.get("left_out", {}).get("*")
                for table in present
                if table not in tables and table not in {item["table"] for item in attach}
            },
        }
    raise LayoutError(f"{collection}: the release lacks its customer table")


def plan(
    collection: str, tables: Mapping[str, list[Row]], layout: Mapping[str, Any]
) -> dict[str, Any]:
    """Customer columns from the presented fields of each table.

    ``tables`` maps a table name to its presented field definitions (``name``,
    ``type``, ``unit``, ``description``). Returns ordered output columns, each
    with its source per main table and its class; removed columns are listed
    for the internal receipt.
    """
    main = layout["main"]
    rename = {**VERSION_RENAMES, **main.get("rename", {})}
    dropped_by_layout = set(layout.get("drop", []))
    columns: dict[str, Row] = {}
    removed: dict[str, str] = {}
    for table in main["tables"]:
        for field in tables[table]:
            name = field["name"]
            kind = column_class(collection, name)
            if name in dropped_by_layout:
                removed[name] = "layout"
                continue
            if kind in REMOVED_CLASSES:
                removed[name] = kind
                continue
            target = str(rename.get(name) or name)
            definition = {k: field.get(k) for k in ("type", "unit", "description")}
            if target in columns:
                existing = columns[target]
                if (existing["type"], existing["unit"]) != (definition["type"], definition["unit"]):
                    target = f"{table}__{name}"
                else:
                    existing["sources"][table] = name
                    continue
            columns[target] = {**definition, "class": kind, "field": name, "sources": {table: name}}
    if main.get("kind"):
        columns[main["kind"]] = {
            "type": "string",
            "unit": None,
            "description": "Which kind of record this row is: "
            + "; ".join(main["labels"][table] for table in main["tables"])
            + ".",
            "class": "data",
            "sources": {},
        }
    for item in layout.get("attach", []):
        fields = {field["name"]: field for field in tables[item["table"]]}
        for target, (field, aggregation) in item["columns"].items():
            if field not in fields:
                continue
            kind = column_class(collection, field)
            if kind in REMOVED_CLASSES:
                removed[f"{item['table']}.{field}"] = kind
                continue
            if target in columns:
                continue
            definition = fields[field]
            columns[target] = {
                "type": "integer" if aggregation == "count" else definition.get("type"),
                "unit": None if aggregation == "count" else definition.get("unit"),
                "description": (
                    f"Number of related {item['table'].replace('_', ' ')} records."
                    if aggregation == "count"
                    else (definition.get("description") or field)
                    + (
                        f" ({aggregation} across related {item['table'].replace('_', ' ')})"
                        if aggregation != "distinct"
                        else f" (all related {item['table'].replace('_', ' ')}, '; '-separated)"
                    )
                ),
                "class": kind if aggregation != "count" else "data",
                "attach": item,
                "field": field,
                "aggregation": aggregation,
                "sources": {},
            }

    def order(item: tuple[str, Row]) -> int:
        _name, column = item
        if column["class"] == "cedar_id" and not column.get("attach"):
            return 0
        if column["class"] == "source":
            return 3
        if column.get("attach"):
            return 2
        return 1

    ordered = dict(sorted(columns.items(), key=order))
    return {"columns": ordered, "removed": removed}


def _aggregate(values: list[Any], aggregation: str) -> Any:
    present = [value for value in values if not _blank(value)]
    if aggregation == "count":
        return len(values)
    if not present:
        return None
    if aggregation == "min":
        return min(present, key=str)
    if aggregation == "max":
        return max(present, key=str)
    flat: list[str] = []
    for value in present:
        found = _elements(value)
        flat.extend(str(v) for v in (found[0] if found else [value]) if not _blank(v))
    return LIST_SEPARATOR.join(sorted(dict.fromkeys(flat)))


def flatten(
    collection: str,
    layout: Mapping[str, Any],
    layout_plan: Mapping[str, Any],
    rows: Callable[[str], Iterable[Row]],
    origins: Mapping[str, str | None],
) -> tuple[list[str], Generator[Row, None, None], dict[str, Any]]:
    """The customer table: header, row iterator and an internal report.

    ``rows(table)`` yields that table's already verified rows. ``origins`` maps
    a table to its recorded public source URL for tracing local sources. Rows
    are staged in a private temporary database, so every count in the report
    is final before the first row is written.
    """
    columns = layout_plan["columns"]
    counts: dict[str, int] = {
        "rows": 0,
        "cedar_id_values_removed": 0,
        "internal_key_values_blanked": 0,
        "version_label_values_blanked": 0,
        "duns_values_removed": 0,
        "duns_scheme_values_removed": 0,
        "sources_public": 0,
        "sources_partial": 0,
        "sources_traced": 0,
        "sources_blanked": 0,
        "unmatched_related_rows": 0,
    }
    # An empty name is SQLite's private temporary database, removed on close.
    store = sqlite3.connect("")
    try:
        store.execute("CREATE TABLE related (slot INTEGER, key TEXT, payload TEXT)")
        store.execute("CREATE INDEX related_key ON related (slot, key)")
        attachments = list(layout.get("attach", []))
        matched_keys: list[set[str]] = [set() for _ in attachments]
        for slot, item in enumerate(attachments):
            where = item.get("where", {})
            fields = sorted({field for field, _ in item["columns"].values()})
            for row in rows(item["table"]):
                row = _scheme_scrubbed(row, counts)
                if any(str(row.get(field)) not in allowed for field, allowed in where.items()):
                    continue
                key = row.get(item["key"])
                if _blank(key):
                    continue
                store.execute(
                    "INSERT INTO related VALUES (?, ?, ?)",
                    (slot, str(key), json.dumps({f: row.get(f) for f in fields})),
                )
        store.execute("CREATE TABLE out (n INTEGER PRIMARY KEY, payload TEXT)")
        main = layout["main"]
        for table in main["tables"]:
            origin = origins.get(table)
            for row in rows(table):
                row = _scheme_scrubbed(row, counts)
                out: Row = {}
                for target, column in columns.items():
                    if column.get("attach") is not None:
                        continue
                    if target == main.get("kind"):
                        out[target] = main["labels"][table]
                        continue
                    source = column["sources"].get(table)
                    value = row.get(source) if source else None
                    out[target] = _present(column, value, origin, counts)
                for slot, item in enumerate(attachments):
                    key = row.get(item["on"])
                    related = (
                        []
                        if _blank(key)
                        else [
                            json.loads(payload)
                            for (payload,) in store.execute(
                                "SELECT payload FROM related WHERE slot = ? AND key = ? "
                                "ORDER BY rowid",
                                (slot, str(key)),
                            )
                        ]
                    )
                    if related:
                        matched_keys[slot].add(str(key))
                    for target, column in columns.items():
                        if column.get("attach") is not item:
                            continue
                        value = _aggregate(
                            [r.get(column["field"]) for r in related], column["aggregation"]
                        )
                        out[target] = _present(column, value, origins.get(item["table"]), counts)
                counts["rows"] += 1
                store.execute("INSERT INTO out (payload) VALUES (?)", (json.dumps(out),))
        for slot, _item in enumerate(attachments):
            (keys,) = store.execute(
                "SELECT COUNT(DISTINCT key) FROM related WHERE slot = ?", (slot,)
            ).fetchone()
            counts["unmatched_related_rows"] += keys - len(matched_keys[slot])
    except BaseException:
        store.close()
        raise
    header = list(columns)
    report = {
        "policy": POLICY,
        "grain": layout.get("grain"),
        "main_tables": list(main["tables"]),
        "attached_tables": sorted({item["table"] for item in attachments}),
        "left_out_tables": dict(layout.get("left_out", {})),
        "removed_columns": dict(layout_plan["removed"]),
        "public_registry_id_columns": [
            name for name in header if columns[name]["class"] == "registry_id"
        ],
        "counts": counts,
    }

    def staged() -> Generator[Row, None, None]:
        try:
            for (payload,) in store.execute("SELECT payload FROM out ORDER BY n"):
                row = json.loads(payload)
                yield {name: row.get(name) for name in header}
        finally:
            store.close()

    return header, staged(), report


def _present(column: Row, value: Any, origin: str | None, counts: dict[str, int]) -> Any:
    kind = column["class"]
    if kind == "cedar_id":
        kept, removed = _cedar_only(value)
        counts["cedar_id_values_removed"] += removed
        return kept
    if kind == "source":
        if isinstance(value, str) and LEGACY_SCHEME_VALUE.search(value):
            # A retired vendor or scheme is never a published source.
            value = origin or None
            counts["sources_" + ("traced" if origin else "blanked")] += 1
            return value
        kept, status = present_source(value, origin)
        if status != "empty":
            counts["sources_" + status] += 1
        return kept
    return _scrub_data(value, counts, edition="vintage" in str(column.get("field") or ""))


def _scheme_scrubbed(row: Row, counts: dict[str, int]) -> Row:
    """Blank the value of a generic identifier whose scheme is DUNS."""
    for scheme, value in _SCHEME_PAIRS:
        if (
            isinstance(row.get(scheme), str)
            and row[scheme].strip().upper() == "DUNS"
            and not _blank(row.get(value))
        ):
            row = {**row, value: None}
            counts["duns_scheme_values_removed"] += 1
    return row


def check_table(header: Iterable[str], rows: Iterable[Mapping[str, Any]]) -> list[str]:
    """Problems that would break the owner's rules in a finished customer table."""
    problems = []
    names = list(header)
    for name in names:
        kind = column_class("", name)
        if kind in REMOVED_CLASSES:
            problems.append(f"column {name}: {kind}")
        if name in {"record_type", "record_key", "record_grain"}:
            problems.append(f"column {name}: component packaging")
    for index, row in enumerate(rows):
        for name in names:
            value = row.get(name)
            if _blank(value):
                continue
            kind = column_class("", name)
            if kind == "cedar_id":
                text = str(value)
                found = _elements(text)
                if not all(is_cedar_id(item) for item in (found[0] if found else [text])):
                    problems.append(f"row {index} {name}: non-Cedar identifier")
            if kind == "source" and is_local_source(str(value)):
                problems.append(f"row {index} {name}: local source")
            if isinstance(value, str) and (
                INTERNAL_KEY.fullmatch(value.strip())
                or LEGACY_SCHEME_VALUE.search(value)
                or is_version_label(value)
                or _DUNS_TOKEN.search(value)
            ):
                problems.append(f"row {index} {name}: internal value")
    return problems


def present_rows(
    collection: str,
    fields: list[Row],
    rows: Iterable[Row],
    origin: str | None = None,
) -> tuple[list[str], list[Row], dict[str, Any]]:
    """One table's rows under the same rules, for bounded previews and samples.

    ``fields`` are the table's presented field definitions. Used where a few
    verified example rows are shown on their own, outside the full table.
    """
    layout: dict[str, Any] = {
        "grain": None,
        "main": {"tables": ["rows"]},
        "attach": [],
        "left_out": {},
    }
    sheet = plan(collection, {"rows": fields}, layout)
    materialized = list(rows)
    header, records, report = flatten(
        collection, layout, sheet, lambda _name: iter(materialized), {"rows": origin}
    )
    return header, list(records), report
