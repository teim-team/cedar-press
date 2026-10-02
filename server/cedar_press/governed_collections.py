"""Approved additive collection targets and public component presentation order.

Declarations preserve machine columns and display metadata from verified releases.
Their source pins record provenance; configured runtime pins, entitlements and
publication policy remain the authority for serving bytes.
"""

import json
from pathlib import Path

from cedar_press import need_publication


def component_declarations(collection_id: str) -> dict:
    """Maintained presentation metadata; never a runtime publication decision."""
    if collection_id not in {
        "gaming",
        "need",
        "plot",
        "foundation-corporate-giving",
        "federal-register",
    }:
        return {}
    filename = collection_id.replace("-", "_") + "_component_contracts.json"
    path = Path(__file__).resolve().parents[2] / "data/cedar" / filename
    if not path.exists() and collection_id in {"plot", "foundation-corporate-giving"}:
        return {}  # Existing fixed declarations until their component expansion lands.
    declaration = json.loads(path.read_text(encoding="utf-8"))
    if declaration.get("schema_version") != 1 or declaration.get("collection") != collection_id:
        raise ValueError("Invalid governed component presentation declaration")
    return declaration["components"]


SHARED_COLLECTIONS = {
    "federal-register": {
        "name": "Federal Register - Indian Affairs",
        "shelf": "standard",
        "components": ("consultation_participants", "federal_actions"),
    },
    "need": {
        "name": "Native Entity Enterprise Dataset",
        "shelf": "pro",
        "components": (need_publication.COMPONENT,),
    },
    "foundation-corporate-giving": {
        "name": "Foundation and Corporate Giving",
        "shelf": "standard",
        "components": ("reviewed_disclosures",),
    },
    "plot": {
        "name": "PLOT",
        "shelf": "pro",
        "components": ("environmental_permits", "environmental_events"),
    },
}

COMPONENT_COLUMNS = {
    "foundation-corporate-giving/reviewed_disclosures": (
        "disclosure_id",
        "award_id",
        "version_kind",
        "funder_name",
        "recipient_name",
        "cedar_uid",
        "recipient_entity_type",
        "recipient_affiliation",
        "purpose",
        "amount_exact_usd",
        "amount_lower_usd",
        "amount_upper_usd",
        "amount_aggregate_usd",
        "financial_status",
        "announcement_date",
        "report_year",
        "award_period_text",
        "project_geography",
        "source_url",
        "source_document_sha256",
        "source_retrieved_date",
        "source_class",
        "source_id",
        "publication_rights_status",
        "overlap_status",
        "addability_status",
        "observation",
    ),
    "plot/environmental_permits": (
        "environmental_record_id",
        "source_permit_id",
        "facility_registry_id",
        "facility_name_raw",
        "state",
        "program",
        "status_raw",
        "latitude",
        "longitude",
        "submitted_date",
        "issued_date",
        "effective_date",
        "expiration_date",
        "terminated_date",
        "source_snapshot_date",
        "native_ownership_supported",
        "research_scope",
        "source_record_url",
        "source_id",
        "source_url",
    ),
    "plot/environmental_events": (
        "environmental_event_id",
        "environmental_record_id",
        "event_date",
        "event_type",
        "event_date_precision",
        "event_interpretation",
        "future_relative_to_capture",
        "source_field",
        "source_id",
        "source_url",
    ),
}


def presentation(collection_id: str, component: str) -> dict | None:
    if collection_id == "need" and component == need_publication.COMPONENT:
        return {
            "collection": "need",
            "order": list(need_publication.FIELDS),
            "compatible_orders": [list(need_publication.CLAIM_FIELDS)],
            "fields": [
                {"column": name, "decision": "keep", "rights_class": "PUBLIC_DERIVED"}
                for name in dict.fromkeys(
                    (*need_publication.FIELDS, *need_publication.CLAIM_FIELDS)
                )
            ],
        }
    declared = component_declarations(collection_id).get(component)
    if declared is not None:
        return declared
    columns = COMPONENT_COLUMNS.get(f"{collection_id}/{component}")
    if columns is None:
        return None
    return {"collection": collection_id, "order": list(columns), "fields": []}
