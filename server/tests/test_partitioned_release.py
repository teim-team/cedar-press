"""Synthetic transport fixtures for generic development-only partition assembly."""

import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from cedar_press import repository, subscribers
from cedar_press.app import app
from cedar_press.session import Session, current_session


class PartitionedReleaseTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.catalog = Path(self.temp.name) / "catalog.json"
        fmap = json.loads(
            (Path(__file__).parents[2] / "data/cedar/field_map.json").read_text(encoding="utf-8")
        )
        self.header = fmap["tables"]["legislation/native_bills"]["order"]
        self.rid = "b" * 64
        self.prefix = f"/v1/collections/legislation/releases/{self.rid}"
        self.parts = {}
        self.manifest = {
            "schema_version": 1,
            "collection_id": "legislation",
            "release_id": self.rid,
            "product": "cedar_press",
            "release_class": "rehearsal",
            "synthetic": False,
            "omitted_components": [],
            "components": {},
        }
        for n in range(3):
            name = f"part-{n}"
            row = dict.fromkeys(self.header)
            row["bill_id"] = f"fixture-{n}"
            content = repository._canonical_bytes(row)
            self.parts[name] = content
            self.manifest["components"][name] = {
                "dataset_id": name,
                "title": name,
                "row_grain": "bill",
                "primary_key": ["bill_id"],
                "record_count": 1,
                "fields": [{"name": k} for k in self.header],
                "rights": {"publication_class": "publishable", "redistribution": True},
                "download_permitted": True,
                "contract_sha256": "c" * 64,
                "metadata": {"logical_table": "native_bills", "ordinal": n},
                "files": {
                    "records.jsonl": {
                        "bytes": len(content),
                        "sha256": hashlib.sha256(content).hexdigest(),
                    }
                },
            }
        self.approve()
        env = patch.dict(
            os.environ,
            {
                "CEDAR_PRESS_RELEASE_CATALOG": str(self.catalog),
                "CEDAR_PRESS_ENVIRONMENT": "development",
                "CEDAR_PRESS_PARTITIONED_REHEARSAL": "1",
            },
        )
        env.start()
        self.addCleanup(env.stop)
        self.fetch = patch.object(
            repository, "_release_json", side_effect=lambda _: copy.deepcopy(self.manifest)
        )
        self.fetch.start()
        self.addCleanup(self.fetch.stop)
        self.raw = patch.object(
            repository,
            "_release_bytes",
            side_effect=lambda path, **_: self.parts[path.split("/")[-2]],
        )
        self.mock_raw = self.raw.start()
        self.addCleanup(self.raw.stop)
        app.dependency_overrides[current_session] = lambda: Session(
            "partition@example.invalid", "press_pro"
        )
        self.addCleanup(app.dependency_overrides.clear)
        sub = patch.object(
            subscribers,
            "find",
            return_value=subscribers.Subscriber(
                "partition@example.invalid", "press_pro", "fixture"
            ),
        )
        sub.start()
        self.addCleanup(sub.stop)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def approve(self):
        parts = [
            {"name": name, **entry, "path": self.prefix + "/components/" + name}
            for name, entry in self.manifest["components"].items()
        ]
        pin = {
            k: self.manifest[k]
            for k in (
                "collection_id",
                "release_id",
                "release_class",
                "synthetic",
                "omitted_components",
            )
        }
        pin.update(
            components=parts,
            record_count=sum(p["record_count"] for p in parts),
            manifest_path=self.prefix + "/manifest",
            manifest_sha256=hashlib.sha256(repository._canonical_bytes(self.manifest)).hexdigest(),
        )
        value = {
            "schema_version": 1,
            "catalog_kind": "collection_releases",
            "product": "cedar_press",
            "entitlement_required": True,
            "collection_releases": [pin],
        }
        value["catalog_id"] = hashlib.sha256(repository._canonical_bytes(value)).hexdigest()
        self.catalog.write_text(json.dumps(value), encoding="utf-8")

    def request(self):
        return self.client.get(
            "/press/collections/legislation/full-download", params={"release_id": self.rid}
        )

    def test_all_parts_exact_bytes_audit_and_cleanup(self):
        files = []
        real = tempfile.TemporaryFile

        def track(*args, **kwargs):
            f = real(*args, **kwargs)
            files.append(f)
            return f

        with (
            patch.object(repository.tempfile, "TemporaryFile", side_effect=track),
            self.assertLogs("cedar_press.download", level="INFO") as log,
        ):
            response = self.request()
        expected = b"".join(self.parts.values())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, expected)
        self.assertEqual(response.headers["x-cedar-sha256"], hashlib.sha256(expected).hexdigest())
        self.assertEqual(self.mock_raw.call_count, 3)
        self.assertTrue(files and all(f.closed for f in files))
        self.assertNotIn("partition@example.invalid", str(log.output))

    def test_global_duplicate_refused(self):
        self.parts["part-2"] = self.parts["part-0"]
        self.manifest["components"]["part-2"]["files"] = copy.deepcopy(
            self.manifest["components"]["part-0"]["files"]
        )
        self.approve()
        self.assertEqual(self.request().status_code, 503)

    def test_last_part_tamper_refused_before_response(self):
        self.parts["part-2"] += b" "
        self.assertEqual(self.request().status_code, 503)

    def test_missing_part_refused(self):
        del self.parts["part-2"]
        self.assertEqual(self.request().status_code, 503)

    def test_omission_refused(self):
        self.manifest["omitted_components"] = [{"name": "other", "reason": "missing"}]
        self.approve()
        self.assertEqual(self.request().status_code, 503)

    def test_gap_and_repeated_order_refused(self):
        for ordinal in (0, 5):
            with self.subTest(ordinal=ordinal):
                self.manifest["components"]["part-2"]["metadata"]["ordinal"] = ordinal
                self.approve()
                self.assertEqual(self.request().status_code, 503)

    def test_rights_refused(self):
        self.manifest["components"]["part-2"]["rights"]["redistribution"] = False
        self.approve()
        self.assertEqual(self.request().status_code, 503)

    def test_production_and_missing_opt_in_refused(self):
        for env in (
            {"CEDAR_PRESS_ENVIRONMENT": "production"},
            {"CEDAR_PRESS_PARTITIONED_REHEARSAL": "0"},
        ):
            with patch.dict(os.environ, env):
                self.assertEqual(self.request().status_code, 503)
        self.mock_raw.assert_not_called()

    def test_unauthorized_requests_never_fetch(self):
        app.dependency_overrides[current_session] = lambda: None
        self.assertEqual(self.request().status_code, 401)
        app.dependency_overrides[current_session] = lambda: Session(
            "partition@example.invalid", "press_pro"
        )
        with patch.object(repository, "may_open", return_value=False):
            self.assertEqual(self.request().status_code, 403)
        self.mock_raw.assert_not_called()

    def test_rollback_restores_previous_complete_version_without_mutation(self):
        old_manifest = copy.deepcopy(self.manifest)
        old_catalog = self.catalog.read_bytes()
        old_parts = copy.deepcopy(self.parts)
        old_rid = self.rid
        self.rid = "e" * 64
        self.prefix = f"/v1/collections/legislation/releases/{self.rid}"
        self.manifest["release_id"] = self.rid
        row = json.loads(self.parts["part-0"])
        row["title"] = "Second version"
        self.parts["part-0"] = repository._canonical_bytes(row)
        self.manifest["components"]["part-0"]["files"]["records.jsonl"] = {
            "bytes": len(self.parts["part-0"]),
            "sha256": hashlib.sha256(self.parts["part-0"]).hexdigest(),
        }
        self.approve()
        self.assertEqual(self.request().content, b"".join(self.parts.values()))
        self.manifest = old_manifest
        self.parts = old_parts
        self.rid = old_rid
        self.catalog.write_bytes(old_catalog)
        self.assertEqual(self.request().content, b"".join(old_parts.values()))
        self.assertEqual(self.catalog.read_bytes(), old_catalog)

    def test_failure_closes_spool(self):
        files = []
        real = tempfile.TemporaryFile

        def track(*args, **kwargs):
            f = real(*args, **kwargs)
            files.append(f)
            return f

        self.parts["part-2"] += b"tampered"
        with patch.object(repository.tempfile, "TemporaryFile", side_effect=track):
            self.assertEqual(self.request().status_code, 503)
        self.assertTrue(files and all(f.closed for f in files))

    def test_malformed_component_fails_closed(self):
        self.manifest["components"]["part-0"]["rights"] = []
        self.approve()
        self.assertEqual(self.request().status_code, 503)

    def test_stale_pin_refused(self):
        self.rid = "d" * 64
        self.assertEqual(self.request().status_code, 503)


if __name__ == "__main__":
    unittest.main()
