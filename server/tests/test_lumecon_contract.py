"""Consume bytes made by Lumecon itself without installing it in Cedar CI.

The checked-in fixture is fictional, never a customer release. Its provenance
pins the producer commit and source hashes, including the uncommitted API seam
used when it was generated. The payloads are existing Lumecon contracts, not a
second manifest format. Wire production flags and fictional crosswalk approval
exist only to exercise the consumer; neither constitutes real publication proof.
"""

import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cedar_press import repository

FIXTURE = Path(__file__).with_name("fixtures") / "lumecon_release_contract.json"


class LumeconContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.catalog_path = Path(self.temp.name) / "catalog.json"
        self.env = patch.dict(os.environ, {"CEDAR_PRESS_RELEASE_CATALOG": str(self.catalog_path)})
        self.env.start()
        self.addCleanup(self.env.stop)

    def consume(self, entry, requested=None):
        self.catalog_path.write_text(json.dumps(entry["catalog"]), encoding="utf-8")
        manifest = entry["manifest"]
        rid = manifest["release_id"]
        prefix = f"/v1/datasets/{entry['collection_id']}/releases/{rid}"

        def metadata(path):
            self.assertEqual(path, prefix + "/manifest")
            return copy.deepcopy(manifest)

        def download(path, *, limit):
            self.assertEqual(path, prefix + "/download")
            self.assertEqual(limit, manifest["files"]["records.jsonl"]["bytes"])
            return entry["records_jsonl_utf8"].encode("utf-8")

        with (
            patch.object(repository, "_release_json", side_effect=metadata),
            patch.object(repository, "_release_bytes", side_effect=download),
        ):
            return repository.full_release(entry["collection_id"], requested or rid)

    def test_actual_lumecon_unicode_serialization_and_catalog_hashes(self):
        vector = self.fixture["canonical_vector"]
        self.assertEqual(
            repository._canonical_bytes(vector),
            self.fixture["canonical_vector_utf8"].encode("utf-8"),
        )
        for entry in self.fixture["collections"]:
            with self.subTest(collection=entry["collection_id"]):
                self.assertEqual(
                    repository._canonical_bytes(entry["catalog"]),
                    entry["catalog_canonical_utf8"].encode("utf-8"),
                )
                content = copy.deepcopy(entry["catalog"])
                catalog_id = content.pop("catalog_id")
                self.assertEqual(
                    hashlib.sha256(repository._canonical_bytes(content)).hexdigest(),
                    catalog_id,
                )

    def test_nonfinite_json_is_refused(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                repository._canonical_bytes({"value": value})

    def test_three_namespaces_receive_exact_producer_artifacts(self):
        self.assertEqual(
            {entry["collection_id"] for entry in self.fixture["collections"]},
            {"legislation", "lobbying", "natural-resources"},
        )
        for entry in self.fixture["collections"]:
            with self.subTest(collection=entry["collection_id"]):
                result = self.consume(entry)
                expected = entry["records_jsonl_utf8"].encode("utf-8")
                self.assertEqual(result["content"], expected)
                self.assertEqual(result["sha256"], hashlib.sha256(expected).hexdigest())
                self.assertEqual(result["release_id"], entry["manifest"]["release_id"])
                self.assertEqual(result["record_count"], 1)

    def test_stale_pin_and_mutated_schema_are_refused(self):
        for entry in self.fixture["collections"]:
            with (
                self.subTest(collection=entry["collection_id"], defect="stale"),
                self.assertRaises(repository.FullReleaseUnavailable),
            ):
                self.consume(entry, "0" * 64)
            for defect in ("schema_version", "fields", "release_id"):
                with self.subTest(collection=entry["collection_id"], defect=defect):
                    changed = copy.deepcopy(entry)
                    if defect == "fields":
                        changed["manifest"]["fields"] = changed["manifest"]["fields"][:-1]
                    elif defect == "schema_version":
                        changed["manifest"]["schema_version"] = 2
                    else:
                        changed["manifest"]["release_id"] = "0" * 64
                    with self.assertRaises(repository.FullReleaseUnavailable):
                        self.consume(changed)

    def test_malformed_pin_and_redistribution_denial_for_every_collection(self):
        for entry in self.fixture["collections"]:
            with self.subTest(collection=entry["collection_id"]):
                with self.assertRaises(repository.FullReleaseUnavailable):
                    self.consume(entry, "../outside")
                changed = copy.deepcopy(entry)
                changed["manifest"]["rights"]["redistribution"] = False
                changed["catalog"]["collections"][0]["rights"]["redistribution"] = False
                content = changed["catalog"]
                content.pop("catalog_id")
                content["catalog_id"] = hashlib.sha256(
                    repository._canonical_bytes(content)
                ).hexdigest()
                with self.assertRaises(repository.FullReleaseUnavailable):
                    self.consume(changed)

    def test_corrupted_artifact_and_synthetic_wire_state_are_refused(self):
        for entry in self.fixture["collections"]:
            with self.subTest(collection=entry["collection_id"], defect="bytes"):
                changed = copy.deepcopy(entry)
                changed["records_jsonl_utf8"] += "\n"
                with self.assertRaises(repository.FullReleaseUnavailable):
                    self.consume(changed)
            with self.subTest(collection=entry["collection_id"], defect="synthetic"):
                changed = copy.deepcopy(entry)
                changed["manifest"]["synthetic"] = True
                changed["catalog"]["collections"][0]["synthetic"] = True
                content = changed["catalog"]
                content.pop("catalog_id")
                content["catalog_id"] = hashlib.sha256(
                    repository._canonical_bytes(content)
                ).hexdigest()
                with self.assertRaises(repository.FullReleaseUnavailable):
                    self.consume(changed)


if __name__ == "__main__":
    unittest.main()
