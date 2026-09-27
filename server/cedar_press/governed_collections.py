"""Approved additive collection targets and public component presentation order.

These declarations contain no row counts, publication claims or release pins.
Exact reviewed Lumecon manifests remain the authority for those facts.
"""

SHARED_COLLECTIONS = {
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
    columns = COMPONENT_COLUMNS.get(f"{collection_id}/{component}")
    if columns is None:
        return None
    return {"collection": collection_id, "order": list(columns), "fields": []}
