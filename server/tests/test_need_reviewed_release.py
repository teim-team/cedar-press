"""NEED's published table passes the real HTTP and shared Grove boundaries."""

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
            "supersedes": policy.PROOF_SUPERSEDES,
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
        private["metadata"] = {"internal_only": True, "publication_hold": policy.PROOF_SUPERSEDES}
        manifest["components"]["enterprises"] = private
        self.repin(manifest, pin)
        fetch = patch.object(
            repository, "_release_response", side_effect=lambda _: io.BytesIO(content)
        )
        fetch.start()
        self.addCleanup(fetch.stop)
        return manifest, pin, content

    def published_fixture(self):
        manifest, pin, _ = self.fixture(
            "need", policy.PUBLISHED_COMPONENT, columns=policy.PUBLISHED_FIELDS
        )
        row = dict.fromkeys(policy.PUBLISHED_FIELDS, "synthetic")
        row.update(
            enterprise_id="NEST-SYNTHETIC-1",
            enterprise_name="Synthetic Enterprise",
            owner_entity_name="Synthetic Parent",
            source_url="https://example.test/report",
            selection_basis="owner_document",
        )
        content = repository._canonical_bytes(row)
        proof = {
            "basis_counts": {"owner_document": 1},
            "producer_commit": "a" * 40,
            "record_count": 1,
            "selection_sha256": "b" * 64,
            "source_release_id": "c" * 64,
            "version": policy.PUBLISHED_VERSIONS[-1],
        }
        entry = manifest["components"][policy.PUBLISHED_COMPONENT]
        entry.update(
            dataset_id="need--" + policy.PUBLISHED_COMPONENT,
            row_grain="One enterprise a Native entity owns",
            metadata={
                "internal_only": False,
                "field_rights": dict.fromkeys(policy.PUBLISHED_FIELDS, "PUBLIC_DERIVED"),
                policy.PUBLISHED_COMPONENT: copy.deepcopy(proof),
            },
            files={
                "records.jsonl": {
                    "bytes": len(content),
                    "sha256": hashlib.sha256(content).hexdigest(),
                }
            },
        )
        manifest["attestations"] = {policy.PUBLISHED_COMPONENT: proof}
        working = copy.deepcopy(entry)
        working["metadata"] = {"internal_only": True}
        manifest["components"]["enterprises"] = working
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

    def test_published_rows_only_reach_authenticated_press_and_shared_grove_csv(self):
        _, pin, content = self.published_fixture()
        self.session("press_pro")
        result = self.client.get(
            "/press/collections/need/full-download",
            params={"release_id": pin["release_id"], "component": policy.PUBLISHED_COMPONENT},
        )
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.content, content)
        result = self.client.get(
            "/press/collections/need/spreadsheet-download", params={"release_id": pin["release_id"]}
        )
        self.assertEqual(result.status_code, 200, result.text)
        rows = list(csv.DictReader(io.StringIO(result.text)))
        self.assertEqual(len(rows), 1)
        # One row per enterprise and no packaging columns. The enterprise is
        # identified by its Cedar Business ID only (owner ruling 2026-10-04);
        # no register binds one to this key, so it is blank and flagged.
        self.assertNotIn("record_type", rows[0])
        self.assertNotIn("enterprise_id", rows[0])
        self.assertEqual(rows[0]["business_uid"], "")
        self.assertEqual(rows[0]["needs_cedar_id"], "yes")
        self.assertEqual(rows[0]["owner_entity_name"], "Synthetic Parent")
        self.assertEqual(rows[0]["selection_basis"], "owner_document")
        self.assertNotIn("NEST-SYNTHETIC-1", result.text)
        metadata = spreadsheet.metadata("need")
        self.assertEqual(metadata["publication_scope"], policy.PUBLISHED_COMPONENT)
        self.assertEqual(metadata[policy.PUBLISHED_COMPONENT]["record_count"], 1)
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
        self.assertEqual(
            response["payload"][policy.PUBLISHED_COMPONENT]["version"],
            policy.PUBLISHED_VERSIONS[-1],
        )
        self.assertFalse(repository.may_download_full("press", "need"))
        self.assertFalse(repository.may_download_full("guest", "need"))

    def test_reviewed_base_is_recognized_whatever_its_rights_flags(self):
        # Owner ruling 2026-10-04: rights statuses are provenance and do not
        # block publication. `internal_only` still marks a working table.
        manifest, _, _ = self.reviewed_fixture()
        entry = manifest["components"][policy.COMPONENT]
        entry["download_permitted"] = False
        entry["rights"] = {"publication_class": "restricted", "redistribution": False}
        entry["metadata"]["publication_status"] = "source_limited"
        self.assertTrue(policy.reviewed_base_permitted(manifest, policy.COMPONENT, entry))
        entry["metadata"]["internal_only"] = True
        self.assertFalse(policy.reviewed_base_permitted(manifest, policy.COMPONENT, entry))

    def test_tenant_private_reviewed_base_is_refused(self):
        # Tenant-private data is a customer's own: the reviewed-base check is
        # the only gate the preview staging script applies, so it refuses it.
        manifest, _, _ = self.reviewed_fixture()
        entry = manifest["components"][policy.COMPONENT]
        self.assertTrue(policy.reviewed_base_permitted(manifest, policy.COMPONENT, entry))
        entry["rights"]["publication_class"] = "tenant_private"
        self.assertFalse(policy.reviewed_base_permitted(manifest, policy.COMPONENT, entry))
        entry["rights"]["publication_class"] = "publishable"
        manifest["rights"] = {"publication_class": "tenant_private"}
        self.assertFalse(policy.reviewed_base_permitted(manifest, policy.COMPONENT, entry))
        del manifest["rights"]
        entry["rights"] = None
        self.assertFalse(policy.reviewed_base_permitted(manifest, policy.COMPONENT, entry))

    def test_only_the_published_table_is_offered_and_others_refuse_without_fetch(self):
        _, pin, _ = self.published_fixture()
        for component in ("enterprises", policy.COMPONENT):
            with (
                self.subTest(component=component),
                patch.object(
                    repository, "_release_response", side_effect=AssertionError("No bytes")
                ),
                self.assertRaises(repository.FullReleaseUnavailable),
            ):
                repository.grove_full_release("need", pin["release_id"], component=component)
        rows = repository.grove_release_metadata("need")
        self.assertEqual([row["table_id"] for row in rows], [policy.PUBLISHED_COMPONENT])
        self.assertEqual(rows[0]["record_count"], 1)

    def test_the_new_table_version_and_the_one_it_replaces_are_both_admitted(self):
        manifest, _, _ = self.published_fixture()
        name = policy.PUBLISHED_COMPONENT
        entry = manifest["components"][name]
        for version in ("need-published-enterprises-1", "need-published-enterprises-2"):
            with self.subTest(version=version):
                manifest["attestations"][name]["version"] = version
                entry["metadata"][name]["version"] = version
                self.assertTrue(policy.published_enterprises_permitted(manifest, name, entry))

    def test_a_table_that_differs_from_its_proof_refuses_before_any_bytes(self):
        manifest, pin, _ = self.published_fixture()
        original = copy.deepcopy(manifest)
        name = policy.PUBLISHED_COMPONENT

        def both_proofs(key, value):
            manifest["attestations"][name][key] = value
            manifest["components"][name]["metadata"][name][key] = value

        failures = {
            "missing": lambda: manifest["attestations"].pop(name),
            "unpaired": lambda: manifest["attestations"][name].update(selection_sha256="f" * 64),
            "version": lambda: both_proofs("version", "need-published-enterprises-99"),
            "commit": lambda: both_proofs("producer_commit", "main"),
            "count": lambda: both_proofs("record_count", 2),
            "dataset": lambda: manifest["components"][name].update(dataset_id="need--other"),
            "working_table": lambda: manifest["components"][name]["metadata"].update(
                internal_only=True
            ),
            "extra_column": lambda: manifest["components"][name]["fields"].append(
                {"name": "licensed_rating", "type": "string"}
            ),
        }
        for failure, change in failures.items():
            with self.subTest(failure=failure):
                manifest.clear()
                manifest.update(copy.deepcopy(original))
                change()
                self.repin(manifest, pin)
                self.assertFalse(
                    policy.published_enterprises_permitted(
                        manifest, name, manifest["components"][name]
                    )
                )
                with patch.object(
                    repository, "_release_response", side_effect=AssertionError("No bytes")
                ):
                    with self.assertRaises(repository.FullReleaseUnavailable):
                        repository.grove_full_release("need", pin["release_id"], component=name)
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

    def test_claim_scoped_preview_proof_is_exact(self):
        manifest, _, _ = self.claim_scoped_fixture()
        entry = manifest["components"][policy.COMPONENT]
        self.assertTrue(policy.reviewed_base_permitted(manifest, policy.COMPONENT, entry))
        changed = copy.deepcopy(entry)
        changed["fields"] = [f for f in changed["fields"] if f["name"] != "subject_binding"]
        self.assertFalse(policy.reviewed_base_permitted(manifest, policy.COMPONENT, changed))
        changed = copy.deepcopy(entry)
        changed["metadata"]["field_rights"]["related_entity_name"] = "LICENSED"
        self.assertFalse(policy.reviewed_base_permitted(manifest, policy.COMPONENT, changed))
