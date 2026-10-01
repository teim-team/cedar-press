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
