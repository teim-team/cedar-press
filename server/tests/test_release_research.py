"""Research packets use the release, rights and current-account boundaries."""

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cedar_press import grove_exchange, release_research, repository


class ReleaseResearchTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.directory = root / "giving"
        self.directory.mkdir()
        self.rid = "a" * 64
        row = {"disclosure_id": "TEST-1", "amount": "1.01", "source_inbox": "C:/private/input.csv"}
        header = list(row)
        self.preview = {
            "scope": "permitted_review_preview",
            "collection": "foundation-corporate-giving",
            "release_id": self.rid,
            "component": "reviewed_disclosures",
            "source_rows": 1,
            "rows": [
                {
                    "component": "reviewed_disclosures",
                    "row": row,
                    "temporal_bucket": "2026",
                    "selection_sha256": hashlib.sha256(
                        repository._canonical_bytes(row)
                    ).hexdigest(),
                }
            ],
        }
        codebook = {
            "reviewed_disclosures": {
                "download_permitted": True,
                "row_grain": "One commitment",
                "primary_key": ["disclosure_id"],
                "fields": [
                    {
                        "name": name,
                        "label": name,
                        "definition": "Exact source field",
                        "permitted_review_preview": True,
                    }
                    for name in header
                ],
            }
        }
        declarations = {
            "components": {"reviewed_disclosures": {"order": header, "display_order": header}}
        }
        artifacts = {
            name: self.write(self.directory / name, value)
            for name, value in {
                "reviewed_disclosures.preview.json": self.preview,
                "codebook.json": codebook,
                "consumer-declarations.json": declarations,
            }.items()
        }
        self.receipt = {
            "schema_version": 1,
            "collection": "foundation-corporate-giving",
            "release_id": self.rid,
            "synthetic": False,
            "release_class": "rehearsal",
            "consumer_manifest_sha256": "b" * 64,
            "manifest_file_sha256": "c" * 64,
            "artifacts": artifacts,
            "method": "Offline fixture",
        }
        self.catalog = {
            "review_only": True,
            "packets": {
                "foundation-corporate-giving": {
                    "release_id": self.rid,
                    "directory": "giving",
                    "receipt_sha256": self.write(self.directory / "receipt.json", self.receipt),
                }
            },
        }
        self.catalog_path = root / "catalog.json"
        self.write(self.catalog_path, self.catalog)
        environment = patch.dict(
            os.environ,
            {
                "CEDAR_PRESS_RESEARCH_CATALOG": str(self.catalog_path),
                "CEDAR_PRESS_ENVIRONMENT": "development",
            },
        )
        environment.start()
        self.addCleanup(environment.stop)
        self.release = {
            "release_id": self.rid,
            "manifest_sha256": "b" * 64,
            "record_count": 1,
            "fields": header,
        }
        backend = patch.object(
            repository, "grove_full_release", side_effect=lambda *a, **kw: self.release
        )
        backend.start()
        self.addCleanup(backend.stop)

    @staticmethod
    def write(path, value):
        raw = repository._canonical_bytes(value)
        path.write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    def read(self):
        return release_research.packet(
            "press", "foundation-corporate-giving", self.rid, "reviewed_disclosures"
        )

    def repin(self, filename, content):
        self.receipt["artifacts"][filename] = self.write(self.directory / filename, content)
        self.catalog["packets"]["foundation-corporate-giving"]["receipt_sha256"] = self.write(
            self.directory / "receipt.json", self.receipt
        )
        self.write(self.catalog_path, self.catalog)

    def test_exact_values_and_codebook_remove_internal_display_fields(self):
        value = self.read()
        # The verified row is shown under the owner's rules of 2026-10-04: the
        # dataset's disclosure ID stays (owner correction 2026-10-04).
        self.assertEqual(value["rows"][0]["row"], {"disclosure_id": "TEST-1", "amount": "1.01"})
        self.assertEqual(value["source_rows"], 1)
        self.assertNotIn("private", json.dumps(value))
        self.assertEqual(value["display_order"], ["disclosure_id", "amount"])
        self.assertEqual(
            [field["name"] for field in value["codebook"]["fields"]], ["disclosure_id", "amount"]
        )
        self.assertEqual(value["provenance"]["consumer_manifest_sha256"], "b" * 64)

    def test_missing_or_modified_packet_artifacts_are_refused(self):
        for name in ("codebook.json", "reviewed_disclosures.preview.json", "receipt.json"):
            with self.subTest(artifact=name):
                path = self.directory / name
                raw = path.read_bytes()
                path.write_bytes(raw + b" ")
                with self.assertRaises(repository.FullReleaseUnavailable):
                    self.read()
                path.unlink()
                with self.assertRaises(repository.FullReleaseUnavailable):
                    self.read()
                path.write_bytes(raw)

    def test_current_pin_count_schema_and_environment_are_checked(self):
        for field, value in [
            ("release_id", "d" * 64),
            ("manifest_sha256", "d" * 64),
            ("record_count", 2),
            ("fields", ["different"]),
        ]:
            with (
                self.subTest(field=field),
                patch.dict(self.release, {field: value}),
                self.assertRaises(repository.FullReleaseUnavailable),
            ):
                self.read()
        with (
            patch.dict(os.environ, {"CEDAR_PRESS_ENVIRONMENT": "production"}),
            self.assertRaises(repository.FullReleaseUnavailable),
        ):
            self.read()
        self.catalog["packets"]["foundation-corporate-giving"]["receipt_sha256"] = None
        self.write(self.catalog_path, self.catalog)
        with self.assertRaises(repository.FullReleaseUnavailable):
            self.read()

    def test_rehashed_held_scope_and_changed_row_are_refused(self):
        self.preview["scope"] = "internal_only"
        self.repin("reviewed_disclosures.preview.json", self.preview)
        with self.assertRaises(repository.FullReleaseUnavailable):
            self.read()
        self.preview["scope"] = "permitted_review_preview"
        self.preview["rows"][0]["row"]["amount"] = "99.99"
        self.repin("reviewed_disclosures.preview.json", self.preview)
        with self.assertRaisesRegex(repository.FullReleaseUnavailable, "row checksum"):
            self.read()

    def test_collection_and_tier_denial_precede_disk_access(self):
        with patch.object(release_research, "_read", side_effect=AssertionError("must not read")):
            # NEED is no longer held (owner ruling 2026-10-04), so only the
            # tier denial is exercised here.
            for tier, collection in [("press", "gaming")]:
                with (
                    self.subTest(collection=collection),
                    self.assertRaises(repository.FullReleaseUnavailable),
                ):
                    release_research.packet(tier, collection, "a" * 64, "profile_links")

    def test_grove_exchange_uses_same_packet_boundary(self):
        value = grove_exchange.exchange(
            {
                "protocol_version": 1,
                "tier": "grove",
                "operation": "research",
                "collection": "foundation-corporate-giving",
                "release_id": self.rid,
                "component": "reviewed_disclosures",
            }
        )
        self.assertEqual(value["rows"][0]["row"]["amount"], "1.01")

    def test_private_paths_and_credentials_are_removed(self):
        for value in [
            "Source retained at C:/private/file.csv",
            "~/research/data.csv",
            "/Users/" + "person/data.csv",
            "https://name:secret@example.org/report",
            "https://example.org/report?token=private",
        ]:
            with self.subTest(value=value):
                self.assertIsNone(release_research._public_value(value))
        self.assertEqual(
            release_research._public_value("https://example.org/home/about"),
            "https://example.org/home/about",
        )

    def test_http_rechecks_current_account_including_revocation(self):
        from fastapi.testclient import TestClient

        from cedar_press import subscribers
        from cedar_press.app import app
        from cedar_press.session import Session, current_session

        target = "/press/collections/foundation-corporate-giving/research"
        params = {"release_id": self.rid, "component": "reviewed_disclosures"}
        with TestClient(app) as client, patch.object(subscribers, "find") as find:
            try:
                app.dependency_overrides[current_session] = lambda: None
                self.assertEqual(client.get(target, params=params).status_code, 401)
                find.assert_not_called()
                app.dependency_overrides[current_session] = lambda: Session(
                    "test@example.invalid", "press_pro"
                )
                find.return_value = None
                self.assertEqual(client.get(target, params=params).status_code, 401)
                find.return_value = subscribers.Subscriber("test@example.invalid", "free", "test")
                self.assertEqual(client.get(target, params=params).status_code, 403)
                find.return_value = subscribers.Subscriber(
                    "test@example.invalid", "press_pro", "test"
                )
                result = client.get(target, params=params)
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.headers["cache-control"], "private, no-store")
                find.side_effect = RuntimeError("private service detail")
                result = client.get(target, params=params)
                self.assertEqual(result.status_code, 503)
                self.assertNotIn("private service", result.text)
            finally:
                app.dependency_overrides.pop(current_session, None)
