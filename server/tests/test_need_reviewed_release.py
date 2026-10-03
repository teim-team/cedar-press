"""A reviewed NEED subset passes the real HTTP and shared Grove boundaries."""

import copy
import csv
import hashlib
import io
import json
import unittest
from unittest.mock import patch

from cedar_press import grove_exchange, repository, spreadsheet
from cedar_press import need_publication as policy
from tests import test_shared_release_collections as shared


class ReviewedNeedReleaseTest(unittest.TestCase):
    setUp = shared.SharedCollectionReleaseTest.setUp
    fixture = shared.SharedCollectionReleaseTest.fixture
    session = shared.SharedCollectionReleaseTest.session

    def reviewed_fixture(self):
        manifest, pin, _ = self.fixture("need", policy.COMPONENT, columns=policy.FIELDS)
        row = dict.fromkeys(policy.FIELDS, "synthetic")
        row.update(
            enterprise_id="NEST-SYNTHETIC-1",
            enterprise_name="Synthetic Enterprise",
            source_reported_name="Synthetic Enterprise",
            uei="TESTUEI12345",
            cage_code="T1234",
            cage_evidence_scope="corroborates_existing",
            owner_name="Synthetic Parent",
            owner_scope="immediate",
            relationship_type="owned_by",
            ownership_extent="majority",
            reviewed_on="2026-10-01",
            publication_status="observed",
            source_release_id="a" * 64,
            source_row_sha256="b" * 64,
            decision_sha256="c" * 64,
            evidence_pins="[]",
        )
        content = repository._canonical_bytes(row)
        proof = {
            "version": policy.VERSION,
            "scope": "reviewed_public_base_only",
            "supersedes": policy.POLICY_HOLD,
            "source_release_id": "a" * 64,
            "enterprise_sha256": "b" * 64,
            "register_sha256": "c" * 64,
            "decisions_sha256": "d" * 64,
            "record_count": 1,
            "intake_gate": {
                "collection": "need",
                "component": policy.COMPONENT,
                "status": "passed",
                "receipts": {policy.SOURCE: ["e" * 64]},
            },
        }
        entry = manifest["components"][policy.COMPONENT]
        entry.update(
            dataset_id="need--" + policy.COMPONENT,
            source={"source_id": policy.SOURCE},
            row_grain="One reviewed enterprise",
            fields=[
                {
                    "name": name,
                    "type": "string",
                    "nullable": False,
                    "allowed_values": ["observed"] if name == "publication_status" else None,
                }
                for name in policy.FIELDS
            ],
            metadata={
                "internal_only": False,
                "field_rights": dict.fromkeys(policy.FIELDS, "PUBLIC_DERIVED"),
                "reviewed_public_base": copy.deepcopy(proof),
            },
            files={
                "records.jsonl": {
                    "bytes": len(content),
                    "sha256": hashlib.sha256(content).hexdigest(),
                }
            },
        )
        manifest["attestations"] = {
            "reviewed_base_source_release_id": "a" * 64,
            "reviewed_public_base": proof,
            "input_manifest": {
                "inputs": {
                    "enterprises": {"sha256": "b" * 64},
                    "enterprise_register": {"sha256": "c" * 64},
                }
            },
        }
        private = copy.deepcopy(entry)
        private["download_permitted"] = False
        private["rights"] = {"publication_class": "restricted", "redistribution": False}
        private["metadata"] = {"internal_only": True, "publication_hold": policy.POLICY_HOLD}
        manifest["components"]["enterprises"] = private
        self.repin(manifest, pin)
        fetch = patch.object(
            repository, "_release_response", side_effect=lambda _: io.BytesIO(content)
        )
        fetch.start()
        self.addCleanup(fetch.stop)
        return manifest, pin, content

    def repin(self, manifest, pin):
        pin["manifest_sha256"] = hashlib.sha256(repository._canonical_bytes(manifest)).hexdigest()
        catalog = json.loads((self.root / "catalog.json").read_bytes())
        catalog["collection_releases"][0]["manifest_sha256"] = pin["manifest_sha256"]
        catalog.pop("catalog_id")
        catalog_id = hashlib.sha256(repository._canonical_bytes(catalog)).hexdigest()
        catalog["catalog_id"] = catalog_id
        content = repository._canonical_bytes(catalog)
        (self.root / "catalog.json").write_bytes(content)
        pin.update(catalog_id=catalog_id, catalog_sha256=hashlib.sha256(content).hexdigest())
        (self.root / "pin.json").write_bytes(
            repository._canonical_bytes(
                {"schema_version": 1, "product": "cedar_press", "pins": {"need": pin}}
            )
        )

    def test_reviewed_rows_only_reach_authenticated_press_and_shared_grove_csv(self):
        _, pin, content = self.reviewed_fixture()
        self.session("press_pro")
        result = self.client.get(
            "/press/collections/need/full-download",
            params={"release_id": pin["release_id"], "component": policy.COMPONENT},
        )
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.content, content)
        result = self.client.get(
            "/press/collections/need/spreadsheet-download", params={"release_id": pin["release_id"]}
        )
        self.assertEqual(result.status_code, 200, result.text)
        rows = list(csv.DictReader(io.StringIO(result.text)))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["record_type"], policy.COMPONENT)
        self.assertEqual(rows[0]["enterprise_id"], "NEST-SYNTHETIC-1")
        self.assertNotIn("private_rating", result.text)
        metadata = spreadsheet.metadata("need")
        self.assertEqual(metadata["publication_scope"], "reviewed_public_base_only")
        self.assertEqual(metadata["reviewed_public_base"]["record_count"], 1)
        response = grove_exchange.response(
            {
                "protocol_version": 1,
                "tier": "grove",
                "operation": "spreadsheet",
                "collection": "need",
                "release_id": pin["release_id"],
            },
            self.root,
        )
        self.assertEqual(response["status"], 200, response)
        self.assertEqual(response["payload"]["record_count"], 1)
        self.assertFalse(repository.may_download_full("press", "need"))
        self.assertFalse(repository.may_download_full("guest", "need"))

    def test_original_raw_components_and_legacy_sample_remain_held_without_fetch(self):
        _, pin, _ = self.reviewed_fixture()
        with patch.object(
            repository, "_release_response", side_effect=AssertionError("No held bytes")
        ):
            with self.assertRaises(repository.FullReleaseUnavailable):
                repository.grove_full_release("need", pin["release_id"], component="enterprises")
            # Exercise an explicit legacy declaration, independently of the
            # current installed preview's finite reviewed-public exception.
            legacy = {
                "id": "need",
                "sample": {"path": "/data/cedar/samples/need/enterprises__10.csv"},
                "tables": [
                    {
                        "table": "enterprises.csv",
                        "sample_path": "/data/cedar/samples/need/enterprises__10.csv",
                    }
                ],
            }
            manifest_path = self.root / "data/cedar/collections.manifest.json"
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(json.dumps({"collections": [legacy]}), encoding="utf-8")
            with (
                patch.object(repository.launch, "_REPO", self.root),
                self.assertRaises(repository.FullReleaseUnavailable),
            ):
                repository.collection_csv("need")
        rows = repository.grove_release_metadata("need")
        available = [row for row in rows if row.get("record_count")]
        self.assertEqual([row["table_id"] for row in available], [policy.COMPONENT])

    def test_malformed_or_unpaired_evidence_refuses_before_reading_any_component(self):
        manifest, pin, _ = self.reviewed_fixture()
        original = copy.deepcopy(manifest)
        for failure in ("missing", "unpaired", "bad_receipt", "extra_field", "held_metadata"):
            with self.subTest(failure=failure):
                manifest.clear()
                manifest.update(copy.deepcopy(original))
                entry = manifest["components"][policy.COMPONENT]
                if failure == "missing":
                    del manifest["attestations"]["reviewed_public_base"]
                elif failure == "unpaired":
                    entry["metadata"]["reviewed_public_base"]["decisions_sha256"] = "f" * 64
                elif failure == "bad_receipt":
                    for proof in (
                        manifest["attestations"]["reviewed_public_base"],
                        entry["metadata"]["reviewed_public_base"],
                    ):
                        proof["intake_gate"]["status"] = "failed"
                elif failure == "extra_field":
                    entry["fields"].append(
                        {"name": "licensed_rating", "type": "string", "nullable": False}
                    )
                else:
                    entry["metadata"]["publication_hold"] = True
                self.repin(manifest, pin)
                with patch.object(
                    repository, "_release_response", side_effect=AssertionError("No rejected bytes")
                ):
                    with self.assertRaises(repository.FullReleaseUnavailable):
                        repository.grove_full_release(
                            "need", pin["release_id"], component=policy.COMPONENT
                        )
                    with self.assertRaises(repository.FullReleaseUnavailable):
                        spreadsheet.download("need", pin["release_id"])

    def claim_scoped_fixture(self):
        manifest, pin, _ = self.reviewed_fixture()
        entry = manifest["components"][policy.COMPONENT]
        proof = manifest["attestations"]["reviewed_public_base"]
        proof["version"] = policy.CLAIM_VERSION
        entry["metadata"]["reviewed_public_base"] = copy.deepcopy(proof)
        entry["metadata"]["field_rights"] = dict.fromkeys(policy.CLAIM_FIELDS, "PUBLIC_DERIVED")
        entry["fields"] = [
            {
                "name": name,
                "type": "string",
                "nullable": name in policy.CLAIM_NULLABLE_FIELDS,
                "allowed_values": ["observed"] if name == "publication_status" else None,
            }
            for name in policy.CLAIM_FIELDS
        ]
        row = dict.fromkeys(policy.CLAIM_FIELDS, "synthetic")
        row.update(
            enterprise_id="NEST-SYNTHETIC-1",
            enterprise_name="Synthetic Enterprise",
            source_reported_name="Synthetic Enterprise",
            publication_status="observed",
            source_release_id="a" * 64,
            source_row_sha256="b" * 64,
            decision_sha256="c" * 64,
            uei=None,
            cage_code=None,
            cage_evidence_scope=None,
            owner_name=None,
            owner_scope=None,
            ownership_extent=None,
            related_entity_name="Synthetic Regional Organization",
            relationship_type="affiliated_with",
            reviewed_on="2026-10-01",
            review_reason="Reviewed official portfolio affiliation only.",
            verified_claims=json.dumps(["identity", "affiliation"]),
            subject_binding=json.dumps(
                {
                    "kind": "reviewed_profile_link",
                    "profile_link_id": "f" * 64,
                    "profile_row_sha256": "f" * 64,
                }
            ),
            evidence_pins=json.dumps(
                [
                    {
                        "url": "https://example.test/portfolio",
                        "sha256": "e" * 64,
                        "supports": ["identity", "affiliation"],
                    }
                ]
            ),
        )
        content = repository._canonical_bytes(row)
        entry["files"]["records.jsonl"] = {
            "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        }
        self.repin(manifest, pin)
        return manifest, pin, content

    def test_claim_scoped_http_export_does_not_turn_affiliation_into_ownership(self):
        manifest, pin, content = self.claim_scoped_fixture()
        self.assertTrue(
            policy.reviewed_base_permitted(
                manifest, policy.COMPONENT, manifest["components"][policy.COMPONENT]
            )
        )
        self.session("press_pro")
        with patch.object(
            repository, "_release_response", side_effect=lambda _: io.BytesIO(content)
        ):
            result = self.client.get(
                "/press/collections/need/spreadsheet-download",
                params={"release_id": pin["release_id"]},
            )
            self.assertEqual(result.status_code, 200, result.text)
            rows = list(csv.DictReader(io.StringIO(result.text)))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["related_entity_name"], "Synthetic Regional Organization")
            self.assertEqual(rows[0]["relationship_type"], "affiliated_with")
            for column in ("owner_name", "owner_scope", "ownership_extent", "uei", "cage_code"):
                self.assertEqual(rows[0][column], "")
            self.assertEqual(json.loads(rows[0]["verified_claims"]), ["identity", "affiliation"])
            response = grove_exchange.response(
                {
                    "protocol_version": 1,
                    "tier": "grove",
                    "operation": "spreadsheet",
                    "collection": "need",
                    "release_id": pin["release_id"],
                },
                self.root,
            )
            self.assertEqual(response["status"], 200, response)
            self.assertEqual(
                response["payload"]["reviewed_public_base"]["version"], policy.CLAIM_VERSION
            )
            self.assertEqual(response["payload"]["record_count"], 1)
        with (
            patch.object(
                repository,
                "_release_response",
                side_effect=AssertionError("Private components stay held"),
            ),
            self.assertRaises(repository.FullReleaseUnavailable),
        ):
            repository.grove_full_release("need", pin["release_id"], component="enterprises")

    def test_claim_scoped_proof_is_exact_and_refuses_before_component_fetch(self):
        manifest, pin, _ = self.claim_scoped_fixture()
        original = copy.deepcopy(manifest)
        for failure in (
            "unknown_version",
            "old_version_new_fields",
            "missing_binding",
            "nullable_identity",
            "required_unproved_owner",
            "licensed_field",
            "unpaired_proof",
        ):
            with self.subTest(failure=failure):
                manifest.clear()
                manifest.update(copy.deepcopy(original))
                entry = manifest["components"][policy.COMPONENT]
                if failure in {"unknown_version", "old_version_new_fields"}:
                    version = (
                        "need-reviewed-public-base-99"
                        if failure == "unknown_version"
                        else policy.VERSION
                    )
                    manifest["attestations"]["reviewed_public_base"]["version"] = version
                    entry["metadata"]["reviewed_public_base"]["version"] = version
                elif failure == "missing_binding":
                    entry["fields"] = [f for f in entry["fields"] if f["name"] != "subject_binding"]
                elif failure in {"nullable_identity", "required_unproved_owner"}:
                    target = "enterprise_id" if failure == "nullable_identity" else "owner_name"
                    next(f for f in entry["fields"] if f["name"] == target)["nullable"] = (
                        target == "enterprise_id"
                    )
                elif failure == "licensed_field":
                    entry["metadata"]["field_rights"]["related_entity_name"] = "LICENSED"
                else:
                    entry["metadata"]["reviewed_public_base"]["version"] = policy.VERSION
                self.repin(manifest, pin)
                with (
                    patch.object(
                        repository,
                        "_release_response",
                        side_effect=AssertionError("Rejected proof must not fetch"),
                    ),
                    self.assertRaises(repository.FullReleaseUnavailable),
                ):
                    spreadsheet.download("need", pin["release_id"])
