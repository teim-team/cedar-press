"""Narrow NEED publication admission after the normal release verifier."""

from __future__ import annotations

import re
from typing import Any

POLICY_HOLD = "NEED_PUBLICATION_QUARANTINE"
COMPONENT = "reviewed_public_base"
SOURCE = "need-reviewed-public-base-evidence"
VERSION = "need-reviewed-public-base-1"
CLAIM_VERSION = "need-reviewed-public-base-2"
FIELDS = (
    "enterprise_id",
    "enterprise_name",
    "source_reported_name",
    "uei",
    "cage_code",
    "cage_evidence_scope",
    "owner_name",
    "owner_scope",
    "relationship_type",
    "ownership_extent",
    "reviewed_on",
    "review_reason",
    "source_release_id",
    "source_row_sha256",
    "decision_sha256",
    "evidence_pins",
    "publication_status",
)
CLAIM_FIELDS = FIELDS + ("related_entity_name", "verified_claims", "subject_binding")
CLAIM_NULLABLE_FIELDS = frozenset(
    {
        "uei",
        "cage_code",
        "cage_evidence_scope",
        "owner_name",
        "owner_scope",
        "relationship_type",
        "ownership_extent",
        "related_entity_name",
    }
)


def metadata_permits_publication(metadata: object) -> bool:
    if not isinstance(metadata, dict):
        return False
    status = metadata.get("publication_status", "public")
    return (
        metadata.get("internal_only", False) is False
        and metadata.get("publication_hold", False) is False
        and isinstance(status, str)
        and status in {"public", "publishable", "eligible"}
    )


def reviewed_base_permitted(manifest: dict[str, Any], name: str, entry: dict[str, Any]) -> bool:
    """Admit only the pinned reviewed base; never clear another NEED component.

    This checks an already verified manifest. It does not replace artifact,
    acquisition-receipt, row-review, entitlement or release-class verification.
    """
    if manifest.get("collection_id") != "need" or name != COMPONENT:
        return False
    metadata = entry.get("metadata")
    contract = entry
    attestations = manifest.get("attestations")
    if not all(isinstance(value, dict) for value in (metadata, contract, attestations)):
        return False
    proof = metadata.get("reviewed_public_base")
    if not isinstance(proof, dict) or proof != attestations.get("reviewed_public_base"):
        return False
    version = proof.get("version")
    if version == VERSION:
        expected_fields = FIELDS
        nullable_fields: frozenset[str] = frozenset()
    elif version == CLAIM_VERSION:
        expected_fields = CLAIM_FIELDS
        nullable_fields = CLAIM_NULLABLE_FIELDS
    else:
        return False
    if (
        proof.get("scope") != "reviewed_public_base_only"
        or proof.get("supersedes") != POLICY_HOLD
        or metadata.get("internal_only") is not False
        or not metadata_permits_publication(metadata)
        or entry.get("download_permitted") is not True
        or contract.get("dataset_id") != "need--" + COMPONENT
        or not isinstance(contract.get("source"), dict)
        or contract["source"].get("source_id") != SOURCE
        or contract.get("primary_key") != ["enterprise_id"]
    ):
        return False
    for key in ("source_release_id", "enterprise_sha256", "register_sha256", "decisions_sha256"):
        value = proof.get(key)
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            return False
    if attestations.get("reviewed_base_source_release_id") != proof["source_release_id"]:
        return False
    source_inputs = attestations.get("input_manifest")
    if not isinstance(source_inputs, dict):
        return False
    inputs = source_inputs.get("inputs")
    if not isinstance(inputs, dict) or any(
        not isinstance(inputs.get(name), dict) for name in ("enterprises", "enterprise_register")
    ):
        return False
    if (
        inputs.get("enterprises", {}).get("sha256") != proof["enterprise_sha256"]
        or inputs.get("enterprise_register", {}).get("sha256") != proof["register_sha256"]
    ):
        return False
    count = proof.get("record_count")
    if (
        type(count) is not int
        or count <= 0
        or type(entry.get("record_count")) is not int
        or entry["record_count"] != count
    ):
        return False
    intake = proof.get("intake_gate")
    if not isinstance(intake, dict) or (
        intake.get("collection") != "need"
        or intake.get("component") != COMPONENT
        or intake.get("status") != "passed"
    ):
        return False
    receipts = intake.get("receipts")
    if not isinstance(receipts, dict) or set(receipts) != {SOURCE}:
        return False
    pins = receipts[SOURCE]
    if (
        not isinstance(pins, list)
        or not pins
        or any(not isinstance(pin, str) or not re.fullmatch(r"[0-9a-f]{64}", pin) for pin in pins)
    ):
        return False
    fields = contract.get("fields")
    if not isinstance(fields, list) or any(not isinstance(field, dict) for field in fields):
        return False
    if (
        tuple(field.get("name") for field in fields) != expected_fields
        or any(
            field.get("nullable") is not (field.get("name") in nullable_fields) for field in fields
        )
        or metadata.get("field_rights") != dict.fromkeys(expected_fields, "PUBLIC_DERIVED")
        or next(field for field in fields if field["name"] == "publication_status").get(
            "allowed_values"
        )
        != ["observed"]
    ):
        return False
    rights = contract.get("rights")
    return isinstance(rights, dict) and (
        rights.get("redistribution") is True and rights.get("publication_class") == "publishable"
    )


def descriptor_metadata(manifest: dict[str, Any], component: str) -> dict[str, Any]:
    entry = manifest.get("components", {}).get(component)
    if not isinstance(entry, dict) or not reviewed_base_permitted(manifest, component, entry):
        return {}
    return {
        "publication_scope": "reviewed_public_base_only",
        "reviewed_public_base": entry["metadata"]["reviewed_public_base"],
    }
