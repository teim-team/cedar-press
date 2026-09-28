"""Synthetic transport fixtures for generic development-only partition assembly."""

import asyncio
import copy
import hashlib
import io
import json
import os
import tempfile
import tracemalloc
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from cedar_press import repository, subscribers
from cedar_press.app import _VerifiedDownloadResponse, app
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
            repository,
            "_release_json",
            side_effect=lambda _, **_options: copy.deepcopy(self.manifest),
        )
        self.fetch.start()
        self.addCleanup(self.fetch.stop)
        self.raw = patch.object(
            repository,
            "_release_response",
            side_effect=self.table_response,
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

    def table_response(self, path):
        self.assertEqual(path, f"/v1/collections/legislation/releases/{self.rid}/download")
        content = b"".join(self.parts.values())
        response = io.BytesIO(content)
        response.headers = {
            "Content-Length": str(len(content)),
            "X-Lumecon-Release": self.rid,
            "X-Lumecon-Rows": str(
                sum(p["record_count"] for p in self.manifest["components"].values())
            ),
            "X-Lumecon-SHA256": hashlib.sha256(content).hexdigest(),
        }
        return response

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
        self.assertEqual(self.mock_raw.call_count, 1)
        self.assertTrue(files and all(f.closed for f in files))
        self.assertNotIn("partition@example.invalid", str(log.output))

    def test_global_duplicate_refused(self):
        self.parts["part-2"] = self.parts["part-0"]
        self.manifest["components"]["part-2"]["files"] = copy.deepcopy(
            self.manifest["components"]["part-0"]["files"]
        )
        self.approve()
        self.assertEqual(self.request().status_code, 503)

    def test_logical_table_headers_and_body_bounds_fail_closed(self):
        for field, value in (
            ("Content-Length", "0"),
            ("X-Lumecon-Rows", "4"),
            ("X-Lumecon-Release", "f" * 64),
            ("X-Lumecon-SHA256", "f" * 64),
        ):
            with self.subTest(field=field):
                response = self.table_response(self.prefix + "/download")
                response.headers[field] = value
                self.mock_raw.side_effect = None
                self.mock_raw.return_value = response
                self.assertEqual(self.request().status_code, 503)
                self.assertTrue(response.closed)
        content = b"".join(self.parts.values())
        for body in (content[:-1], content + b"x", b"".join(reversed(self.parts.values()))):
            with self.subTest(body_size=len(body)):
                original = self.table_response(self.prefix + "/download")
                response = io.BytesIO(body)
                response.headers = original.headers
                original.close()
                self.mock_raw.side_effect = None
                self.mock_raw.return_value = response
                self.assertEqual(self.request().status_code, 503)
                self.assertTrue(response.closed)

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


class VerifiedRecordStreamTest(unittest.TestCase):
    @staticmethod
    def expected(content):
        return {"bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}

    def consume(self, content, count=1, *, response=None):
        response = response if response is not None else io.BytesIO(content)
        with patch.object(repository, "_release_response", return_value=response):
            return repository._verified_component_spool(
                {"collection_id": "gaming", "release_id": "a" * 64},
                [("example", count, self.expected(content))],
                ["id", "value"],
                ["id"],
            )

    def test_large_artifact_uses_bounded_reads_and_one_record_memory(self):
        content = b"".join(
            (json.dumps({"id": str(i), "value": "x" * 8192}) + "\n").encode() for i in range(1500)
        )

        class BoundedRead(io.BytesIO):
            def read(self, size=-1):
                if not 0 < size <= 64 * 1024:
                    raise AssertionError("Unbounded release read")
                return super().read(size)

        response = BoundedRead(content)
        tracemalloc.start()
        try:
            spool, digest, count = self.consume(content, 1500, response=response)
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        try:
            self.assertLess(peak, 2 * 1024 * 1024)
            self.assertEqual(spool.read(), content)
            self.assertEqual((digest, count), (hashlib.sha256(content).hexdigest(), 1500))
            self.assertTrue(response.closed)
        finally:
            spool.close()

    def test_short_reads_are_not_truncation(self):
        class ShortRead(io.BytesIO):
            def read(self, size=-1):
                return super().read(min(size, 7))

        content = b'{"id":"1","value":"\\u00e9"}\n'
        spool, _, _ = self.consume(content, response=ShortRead(content))
        try:
            self.assertEqual(spool.read(), content)
        finally:
            spool.close()

    def test_pinned_but_invalid_rows_refuse_and_close_storage(self):
        invalid = [
            (b'{"id":"1","id":"2","value":1}\n', "Duplicate JSON"),
            (b'{"id":"1","value":NaN}\n', "Nonfinite"),
            (b'{"id":true,"value":1}\n', "primary key"),
            (b'{"id":[],"value":1}\n', "primary key"),
            (b'{"id":"1","value":1}', "newline"),
            (b'{"id":"1","extra":1}\n', "schema"),
            (b'{"id":"1","value":1}\n' * 2, "Duplicate key"),
        ]
        original = tempfile.TemporaryFile
        for content, message in invalid:
            with self.subTest(message=message):
                opened = []

                def capture(*args, _opened=opened, **kwargs):
                    value = original(*args, **kwargs)
                    _opened.append(value)
                    return value

                with (
                    patch.object(repository.tempfile, "TemporaryFile", side_effect=capture),
                    self.assertRaisesRegex(ValueError, message),
                ):
                    self.consume(content, 2 if "Duplicate key" in message else 1)
                self.assertTrue(opened and all(value.closed for value in opened))

    def test_changed_truncated_extra_and_wrong_count_are_refused(self):
        content = b'{"id":"1","value":"0.10"}\n'
        for served, count in (
            (content[:-1], 1),
            (content + b"x", 1),
            (content.replace(b"0.10", b"0.11"), 1),
            (content, 2),
        ):
            with (
                self.subTest(served=served, count=count),
                self.assertRaises(repository.FullReleaseUnavailable),
            ):
                self.consume(content, count, response=io.BytesIO(served))


class DownloadLifetimeTest(unittest.IsolatedAsyncioTestCase):
    async def test_completion_header_failure_body_failure_and_cancellation_close_spool(self):
        for failure in (None, "http.response.start", "http.response.body", "cancel"):
            with self.subTest(failure=failure):
                spool = io.BytesIO(b"verified\n")
                response = _VerifiedDownloadResponse(spool)

                async def receive():
                    raise AssertionError("ASGI 2.4 does not need a disconnect listener")

                async def send(message, _failure=failure):
                    if _failure == "cancel":
                        raise asyncio.CancelledError
                    if message["type"] == _failure:
                        raise RuntimeError("Disconnected")

                scope = {"type": "http", "asgi": {"spec_version": "2.4"}}
                try:
                    if failure is None:
                        await response(scope, receive, send)
                    else:
                        error = asyncio.CancelledError if failure == "cancel" else RuntimeError
                        with self.assertRaises(error):
                            await response(scope, receive, send)
                finally:
                    self.assertTrue(spool.closed)


if __name__ == "__main__":
    unittest.main()
