"""Pinned full-release delivery and negative controls; all fixtures are fictional."""

import copy
import hashlib
import io
import json
import logging
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from cedar_press import repository
from cedar_press.app import app
from cedar_press.session import Session, current_session


class ReleaseDownloadTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.catalog = Path(self.temp.name) / "catalog.json"
        field_map = json.loads(
            (Path(__file__).parents[2] / "data/cedar/field_map.json").read_text()
        )
        self.header = field_map["tables"]["legislation/native_bills"]["order"]
        self.rows = [{key: None for key in self.header}]
        self.rows[0]["bill_id"] = "fixture-bill"
        self.rows[0]["title"] = "Fictional test bill"
        self.rid = "a" * 64
        fields = [
            {"name": name, "type": "string", "nullable": name != "bill_id"} for name in self.header
        ]
        self.pin = {
            "dataset_id": "legislation",
            "release_id": self.rid,
            "record_count": 1,
            "fields": fields,
            "rights": {"publication_class": "publishable", "redistribution": True},
            "synthetic": False,
        }
        self.write_catalog()
        content = b"".join(repository._canonical_bytes(row) for row in self.rows)
        self.manifest = {
            **self.pin,
            "schema_version": 1,
            "primary_key": ["bill_id"],
            "files": {
                "records.jsonl": {
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "bytes": len(content),
                }
            },
        }
        self.env = patch.dict(os.environ, {"CEDAR_PRESS_RELEASE_CATALOG": str(self.catalog)})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.fetch = patch.object(repository, "_release_json", side_effect=self.response)
        self.mock_fetch = self.fetch.start()
        self.addCleanup(self.fetch.stop)
        self.raw = patch.object(
            repository,
            "_release_bytes",
            side_effect=lambda *a, **k: b"".join(
                repository._canonical_bytes(row) for row in self.rows
            ),
        )
        self.raw.start()
        self.addCleanup(self.raw.stop)
        app.dependency_overrides[current_session] = lambda: Session(
            "fixture@example.invalid", "press"
        )
        self.addCleanup(app.dependency_overrides.clear)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def write_catalog(self):
        value = {
            "schema_version": 1,
            "product": "cedar_press",
            "entitlement_required": True,
            "collections": [self.pin],
        }
        value["catalog_id"] = hashlib.sha256(repository._canonical_bytes(value)).hexdigest()
        self.catalog.write_text(json.dumps(value), encoding="utf-8")

    def response(self, path):
        if path.endswith("/manifest"):
            return copy.deepcopy(self.manifest)
        return {
            "dataset_id": "legislation",
            "release_id": self.rid,
            "offset": 0,
            "limit": 1000,
            "total": 1,
            "synthetic": False,
            "records": copy.deepcopy(self.rows),
        }

    def test_authorized_bytes_and_audit(self):
        with self.assertLogs("cedar_press.download", level="INFO") as captured:
            response = self.client.get(
                "/press/collections/legislation/full-download", params={"release_id": self.rid}
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["x-cedar-release"], self.rid)
        self.assertEqual(
            response.headers["x-cedar-sha256"], hashlib.sha256(response.content).hexdigest()
        )
        self.assertIn(b"Fictional test bill", response.content)
        self.assertIn("authorized_prepared", captured.output[0])
        self.assertNotIn("fixture@example", captured.output[0])
        self.assertIn("no-store", response.headers["cache-control"])

    def test_anonymous_and_wrong_tier_never_touch_release(self):
        for session, status in [(None, 401), (Session("fixture", "unknown"), 403)]:
            app.dependency_overrides[current_session] = lambda value=session: value
            self.assertEqual(
                self.client.get(
                    "/press/collections/legislation/full-download", params={"release_id": self.rid}
                ).status_code,
                status,
            )
        self.mock_fetch.assert_not_called()

    def test_held_need_and_excluded_gaming_never_fetch(self):
        app.dependency_overrides[current_session] = lambda: Session("fixture", "press_pro")
        for collection, status in [("need", 503), ("gaming", 403)]:
            self.assertEqual(
                self.client.get(
                    f"/press/collections/{collection}/full-download",
                    params={"release_id": self.rid},
                ).status_code,
                status,
            )
        self.mock_fetch.assert_not_called()

    def test_corruption_is_refused_without_sample_fallback(self):
        self.rows[0]["title"] = "tampered"
        response = self.client.get(
            "/press/collections/legislation/full-download", params={"release_id": self.rid}
        )
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(b"fixture-bill", response.content)

    def test_catalog_corruption_and_malformed_pin_refused(self):
        self.catalog.write_text("{}")
        self.assertEqual(
            self.client.get(
                "/press/collections/legislation/full-download", params={"release_id": self.rid}
            ).status_code,
            503,
        )
        self.pin["release_id"] = "../outside"
        self.write_catalog()
        self.assertEqual(
            self.client.get(
                "/press/collections/legislation/full-download", params={"release_id": self.rid}
            ).status_code,
            503,
        )
        self.mock_fetch.assert_not_called()

    def test_withheld_synthetic_and_schema_mismatch_refused(self):
        baseline = copy.deepcopy(self.pin)
        for mutation in [
            {"synthetic": True},
            {"rights": {"publication_class": "withheld", "redistribution": True}},
            {"fields": [{"name": "internal_secret"}]},
        ]:
            self.pin = {**copy.deepcopy(baseline), **mutation}
            self.write_catalog()
            self.manifest.update(self.pin)
            self.assertEqual(
                self.client.get(
                    "/press/collections/legislation/full-download", params={"release_id": self.rid}
                ).status_code,
                503,
            )

    def test_rollback_restores_exact_bytes_without_mutating_artifacts(self):
        before = self.client.get(
            "/press/collections/legislation/full-download", params={"release_id": self.rid}
        )
        catalog_bytes = self.catalog.read_bytes()
        self.catalog.write_text("{}")
        self.assertEqual(
            self.client.get(
                "/press/collections/legislation/full-download", params={"release_id": self.rid}
            ).status_code,
            503,
        )
        self.catalog.write_bytes(catalog_bytes)
        after = self.client.get(
            "/press/collections/legislation/full-download", params={"release_id": self.rid}
        )
        self.assertEqual(before.content, after.content)
        self.assertEqual(before.headers["x-cedar-release"], after.headers["x-cedar-release"])

    def test_missing_catalog_fails_closed(self):
        with patch.dict(os.environ, {"CEDAR_PRESS_RELEASE_CATALOG": ""}):
            self.assertEqual(
                self.client.get(
                    "/press/collections/legislation/full-download", params={"release_id": self.rid}
                ).status_code,
                503,
            )

    def test_explicit_pin_missing_malformed_or_stale_is_refused_and_audited(self):
        for pin, expected in [(None, 400), ("../outside", 400), ("b" * 64, 503)]:
            with self.assertLogs("cedar_press.download", level="INFO") as log:
                result = self.client.get(
                    "/press/collections/legislation/full-download",
                    params={} if pin is None else {"release_id": pin},
                )
            self.assertEqual(result.status_code, expected)
            self.assertEqual(len(log.output), 1)
            self.assertNotIn("../outside", log.output[0])
        self.mock_fetch.assert_not_called()

    def test_second_collection_uses_identical_adapter(self):
        field_map = json.loads(
            (Path(__file__).parents[2] / "data/cedar/field_map.json").read_text()
        )
        self.header = field_map["tables"]["lobbying/native_entity_lobbying_disclosures"]["order"]
        self.rows = [{key: None for key in self.header}]
        self.rows[0]["activity_id"] = "fixture-filing"
        self.pin.update(
            dataset_id="lobbying",
            fields=[
                {"name": key, "type": "string", "nullable": key != "activity_id"}
                for key in self.header
            ],
        )
        self.write_catalog()
        content = b"".join(repository._canonical_bytes(row) for row in self.rows)
        self.manifest = {
            **self.pin,
            "schema_version": 1,
            "primary_key": ["activity_id"],
            "files": {
                "records.jsonl": {
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "bytes": len(content),
                }
            },
        }
        result = self.client.get(
            "/press/collections/lobbying/full-download", params={"release_id": self.rid}
        )
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.content, content)
        self.assertIn("application/x-ndjson", result.headers["content-type"])

    def test_missing_policy_and_malformed_metadata_fail_closed_with_audit(self):
        with (
            patch.object(repository, "_publication_policy", side_effect=FileNotFoundError),
            self.assertLogs("cedar_press.download", level="INFO"),
        ):
            response = self.client.get(
                "/press/collections/legislation/full-download", params={"release_id": self.rid}
            )
        self.assertEqual(response.status_code, 503)
        for content in ["[]", '{"collections":[null]}']:
            self.catalog.write_text(content)
            response = self.client.get(
                "/press/collections/legislation/full-download", params={"release_id": self.rid}
            )
            self.assertEqual(response.status_code, 503)

    def test_audit_is_enabled_without_test_logger_override_and_redacts_unknown_path(self):
        stream = io.StringIO()
        logger = logging.getLogger("cedar_press.download")
        self.assertTrue(logger.isEnabledFor(logging.INFO))
        handler = logging.StreamHandler(stream)
        logger.addHandler(handler)
        try:
            response = self.client.get(
                "/press/collections/private-secret-token/full-download",
                params={"release_id": self.rid},
            )
        finally:
            logger.removeHandler(handler)
        self.assertEqual(response.status_code, 403)
        event = json.loads(stream.getvalue())
        self.assertEqual(event["collection_id"], "unknown")
        self.assertEqual(event["requested_release_id"], self.rid)
        self.assertIn("timestamp", event)
        self.assertNotIn("private-secret-token", stream.getvalue())
        self.assertNotIn("fixture@example", stream.getvalue())

    def test_primary_key_and_count_mismatch_fail_closed(self):
        self.manifest["primary_key"] = ["missing"]
        self.assertEqual(
            self.client.get(
                "/press/collections/legislation/full-download", params={"release_id": self.rid}
            ).status_code,
            503,
        )


class ReleaseConfigurationTest(unittest.TestCase):
    def test_invalid_configuration_never_sends_request(self):
        configurations = [
            {"CEDAR_PRESS_ENVIRONMENT": "unknown"},
            {"CEDAR_PRESS_DATA_API": "http://remote.invalid"},
            {"CEDAR_PRESS_DATA_API": "https://user:secret@example.invalid"},
            {"CEDAR_PRESS_DATA_TOKEN": "secret\n"},
            {"CEDAR_PRESS_ENVIRONMENT": "production", "CEDAR_PRESS_DATA_API": "http://localhost"},
            {"CEDAR_PRESS_ENVIRONMENT": "staging", "CEDAR_PRESS_INSECURE_COOKIE": "1"},
        ]
        for configuration in configurations:
            with (
                self.subTest(configuration=list(configuration)),
                patch.dict(
                    os.environ,
                    {
                        "CEDAR_PRESS_DATA_API": "https://data.example.invalid",
                        "CEDAR_PRESS_DATA_TOKEN": "fixture-token",
                        **configuration,
                    },
                    clear=True,
                ),
                patch.object(repository, "build_opener") as opener,
            ):
                with self.assertRaises(repository.FullReleaseUnavailable):
                    repository._release_bytes("/v1/datasets")
                opener.assert_not_called()
