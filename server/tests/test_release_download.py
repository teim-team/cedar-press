"""Pinned full-release delivery and negative controls; all fixtures are fictional."""

import copy
import hashlib
import importlib.util
import io
import json
import logging
import os
import tempfile
import unittest
import uuid
from http.client import IncompleteRead
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from cedar_press import db, repository, subscribers
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
        self.approve_manifest_fixture()
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

    def use_producer_fixture(self, collection_id):
        fixture = json.loads(
            (Path(__file__).with_name("fixtures") / "lumecon_release_contract.json").read_text(
                encoding="utf-8"
            )
        )
        entry = next(row for row in fixture["collections"] if row["collection_id"] == collection_id)
        self.manifest = copy.deepcopy(entry["manifest"])
        self.pin = copy.deepcopy(entry["catalog"]["collections"][0])
        self.rid = self.manifest["release_id"]
        self.rows = [json.loads(line) for line in entry["records_jsonl_utf8"].splitlines()]
        self.write_catalog()
        return entry["records_jsonl_utf8"].encode("utf-8")

    def write_catalog(self):
        value = {
            "schema_version": 1,
            "product": "cedar_press",
            "entitlement_required": True,
            "collections": [self.pin],
        }
        value["catalog_id"] = hashlib.sha256(repository._canonical_bytes(value)).hexdigest()
        self.catalog.write_text(json.dumps(value), encoding="utf-8")

    def approve_manifest_fixture(self):
        self.pin["manifest_sha256"] = hashlib.sha256(
            repository._canonical_bytes(self.manifest)
        ).hexdigest()
        self.write_catalog()

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

    @unittest.skipUnless(
        os.environ.get("CEDAR_PRESS_TEST_DATABASE_URL"), "requires disposable Postgres fixture"
    )
    def test_database_subscriber_login_reaches_the_exact_pinned_artifact(self):
        # No dependency override: exercise the actual database -> login -> cookie
        # -> entitlement -> release path. The data transport remains fictional.
        app.dependency_overrides.clear()
        email = f"release-{uuid.uuid4().hex}@example.invalid"
        pro_email = f"release-pro-{uuid.uuid4().hex}@example.invalid"
        with patch.dict(
            os.environ,
            {
                "DATABASE_URL": os.environ["CEDAR_PRESS_TEST_DATABASE_URL"],
                "CEDAR_PRESS_INSECURE_COOKIE": "1",
                "CEDAR_PRESS_ENVIRONMENT": "development",
            },
        ):
            db.reset_for_tests()
            try:
                db.migrate()
                subscribers.create(email, "disposable-fixture-password", "press")
                url = "/press/collections/legislation/full-download"
                self.assertEqual(
                    self.client.get(url, params={"release_id": self.rid}).status_code, 401
                )
                login = self.client.post(
                    "/auth/login", json={"email": email, "password": "disposable-fixture-password"}
                )
                self.assertEqual(login.status_code, 200)
                db.reset_for_tests()
                self.assertIsNotNone(subscribers.authenticate(email, "disposable-fixture-password"))
                with self.assertLogs("cedar_press.download", level="INFO") as captured:
                    response = self.client.get(url, params={"release_id": self.rid})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.content,
                    b"".join(repository._canonical_bytes(row) for row in self.rows),
                )
                self.assertIn("authorized_prepared", captured.output[0])
                self.assertNotIn(email, captured.output[0])
                expected = self.use_producer_fixture("natural-resources")
                resources_url = "/press/collections/natural-resources/full-download"
                self.mock_fetch.reset_mock()
                with self.assertLogs("cedar_press.download", level="INFO") as denial:
                    denied = self.client.get(resources_url, params={"release_id": self.rid})
                self.assertEqual(denied.status_code, 403)
                self.mock_fetch.assert_not_called()
                self.assertIn("denied_entitlement", denial.output[0])
                self.assertNotIn(email, denial.output[0])
                subscribers.create(pro_email, "disposable-pro-password", "press_pro")
                login = self.client.post(
                    "/auth/login", json={"email": pro_email, "password": "disposable-pro-password"}
                )
                self.assertEqual(login.status_code, 200)
                db.reset_for_tests()
                self.assertIsNotNone(subscribers.authenticate(pro_email, "disposable-pro-password"))
                with self.assertLogs("cedar_press.download", level="INFO") as approval:
                    approved = self.client.get(resources_url, params={"release_id": self.rid})
                self.assertEqual(approved.status_code, 200)
                self.assertEqual(approved.content, expected)
                self.assertIn("authorized_prepared", approval.output[0])
                self.assertNotIn(pro_email, approval.output[0])
                self.assertNotIn("disposable-pro-password", approval.output[0])

            finally:
                for address in (email, pro_email):
                    db.execute("DELETE FROM cedar_press_subscribers WHERE email = %s", (address,))
                db.reset_for_tests()

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

    def test_coherent_upstream_tampering_cannot_change_the_approved_artifact(self):
        approved_catalog = self.catalog.read_bytes()
        self.rows[0]["title"] = "changed upstream claim"
        content = b"".join(repository._canonical_bytes(row) for row in self.rows)
        self.manifest["files"]["records.jsonl"] = {
            "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()
        }
        with self.assertLogs("cedar_press.download", level="INFO") as logs:
            response = self.client.get(
                "/press/collections/legislation/full-download", params={"release_id": self.rid}
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.catalog.read_bytes(), approved_catalog)
        self.assertNotIn("changed upstream claim", response.text + str(logs.output))
        self.assertIn("unavailable", logs.output[0])

    def test_legacy_or_malformed_manifest_pin_fails_before_upstream_access(self):
        for digest in (None, "", "not-a-hash", 1):
            with self.subTest(digest=digest):
                self.pin["manifest_sha256"] = digest
                self.write_catalog()
                response = self.client.get(
                    "/press/collections/legislation/full-download",
                    params={"release_id": self.rid},
                )
                self.assertEqual(response.status_code, 503)
        self.mock_fetch.assert_not_called()

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
            self.manifest.update({k: v for k, v in self.pin.items() if k != "manifest_sha256"})
            self.approve_manifest_fixture()
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

    def test_natural_resources_pro_entitlement_and_exact_artifact(self):
        expected = self.use_producer_fixture("natural-resources")
        url = "/press/collections/natural-resources/full-download"
        for session, status in [(None, 401), (Session("fictional@example.invalid", "press"), 403)]:
            app.dependency_overrides[current_session] = lambda value=session: value
            self.mock_fetch.reset_mock()
            with self.assertLogs("cedar_press.download", level="INFO") as logs:
                result = self.client.get(url, params={"release_id": self.rid})
            self.assertEqual(result.status_code, status)
            self.mock_fetch.assert_not_called()
            self.assertNotIn("fictional@example.invalid", logs.output[0])
        app.dependency_overrides[current_session] = lambda: Session(
            "fictional@example.invalid", "press_pro"
        )
        with self.assertLogs("cedar_press.download", level="INFO") as logs:
            result = self.client.get(url, params={"release_id": self.rid})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.content, expected)
        self.assertEqual(result.headers["x-cedar-sha256"], hashlib.sha256(expected).hexdigest())
        self.assertIn("authorized_prepared", logs.output[0])
        self.assertNotIn("fictional@example.invalid", logs.output[0])

    def test_natural_resources_invalid_requests_and_rights_are_audited(self):
        self.use_producer_fixture("natural-resources")
        app.dependency_overrides[current_session] = lambda: Session(
            "fictional@example.invalid", "press_pro"
        )
        url = "/press/collections/natural-resources/full-download"
        for pin, status in [("../outside", 400), ("0" * 64, 503)]:
            with self.assertLogs("cedar_press.download", level="INFO") as logs:
                response = self.client.get(url, params={"release_id": pin})
            self.assertEqual(response.status_code, status)
            self.assertNotIn("../outside", logs.output[0])
            self.assertNotIn("fictional@example.invalid", logs.output[0])
        self.pin["rights"]["redistribution"] = False
        self.manifest["rights"]["redistribution"] = False
        self.approve_manifest_fixture()
        with self.assertLogs("cedar_press.download", level="INFO") as logs:
            response = self.client.get(url, params={"release_id": self.rid})
        self.assertEqual(response.status_code, 503)
        self.assertIn("unavailable", logs.output[0])
        self.assertNotIn("fictional@example.invalid", logs.output[0])

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
        self.pin.pop("manifest_sha256", None)
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
        self.approve_manifest_fixture()
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

    def test_truncated_upstream_response_fails_closed_and_is_audited(self):
        self.mock_fetch.side_effect = IncompleteRead(b"private partial response", 12)
        with self.assertLogs("cedar_press.download", level="INFO") as log:
            response = self.client.get(
                "/press/collections/legislation/full-download", params={"release_id": self.rid}
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(len(log.records), 1)
        event = json.loads(log.records[0].getMessage())
        self.assertEqual(event["outcome"], "unavailable")
        self.assertNotIn("private partial response", log.output[0] + response.text)

    def test_primary_key_and_count_mismatch_fail_closed(self):
        self.manifest["primary_key"] = ["missing"]
        self.approve_manifest_fixture()
        self.assertEqual(
            self.client.get(
                "/press/collections/legislation/full-download", params={"release_id": self.rid}
            ).status_code,
            503,
        )


class ReleaseConfigurationTest(unittest.TestCase):
    def test_rehearsal_refuses_inherited_database_before_creating_artifacts(self):
        spec = importlib.util.spec_from_file_location(
            "isolated_rehearsal", Path(__file__).with_name("release_download_rehearsal.py")
        )
        rehearsal = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rehearsal)
        for key in ("DATABASE_URL", "CEDAR_PRESS_DB"):
            with patch.dict(os.environ, {key: "sensitive-fixture-not-a-real-store"}, clear=True):
                with self.assertRaisesRegex(
                    SystemExit, "requires an isolated environment"
                ) as error:
                    rehearsal.main()
                self.assertNotIn("sensitive-fixture", str(error.exception))

    def test_invalid_configuration_never_sends_request(self):
        configurations = [
            {"CEDAR_PRESS_ENVIRONMENT": "unknown"},
            {"CEDAR_PRESS_ENVIRONMENT": "production"},
            {"CEDAR_PRESS_ENVIRONMENT": "staging"},
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

    def test_production_configuration_is_explicit_and_transport_remains_bounded(self):
        configured = {
            "CEDAR_PRESS_ENVIRONMENT": "production",
            "CEDAR_PRESS_DATA_API": "https://data.example.invalid",
            "CEDAR_PRESS_DATA_TOKEN": "fixture-" + "t" * 32,
            "CEDAR_PRESS_SECRET": "fixture-" + "s" * 32,
            "DATABASE_URL": "postgresql://fixture.invalid/not-connected",
        }
        with (
            patch.dict(os.environ, configured, clear=True),
            patch.object(repository, "build_opener") as opener,
        ):
            opener.return_value.open.return_value.__enter__.return_value.read.return_value = b"{}"
            self.assertEqual(repository._release_json("/v1/datasets"), {})
            request = opener.return_value.open.call_args.args[0]
            self.assertEqual(request.full_url, "https://data.example.invalid/v1/datasets")
            self.assertEqual(opener.return_value.open.call_args.kwargs["timeout"], 30)
            opener.return_value.open.return_value.__enter__.return_value.read.return_value = (
                b"too long"
            )
            with self.assertRaises(repository.FullReleaseUnavailable):
                repository._release_bytes("/v1/datasets", limit=2)
        for changes in [
            {"CEDAR_PRESS_ACCOUNTS": '{"fake":"never-use-env-accounts-in-production"}'},
            {"DATABASE_URL": "sqlite://memory"},
            {"CEDAR_PRESS_SECRET": "short"},
            {"CEDAR_PRESS_DATA_TOKEN": "short"},
        ]:
            with (
                patch.dict(os.environ, {**configured, **changes}, clear=True),
                patch.object(repository, "build_opener") as opener,
            ):
                with self.assertRaises(repository.FullReleaseUnavailable):
                    repository._release_bytes("/v1/datasets")
                opener.assert_not_called()
