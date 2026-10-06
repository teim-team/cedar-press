"""The application adapter cannot bypass the existing release consumer."""

import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cedar_press import grove_exchange as exchange
from cedar_press import repository


class GroveExchange(unittest.TestCase):
    def request(self, operation="discover", **extra):
        return {"protocol_version": 1, "operation": operation, "tier": "grove", **extra}

    def test_rejects_tiers_unknown_keys_and_unknown_protocol_before_data(self):
        with patch.object(repository, "release_targets_for", side_effect=AssertionError):
            for request, status in [
                (self.request(tier="press_pro"), 403),
                (self.request(tier="guest"), 403),
                (self.request(protocol_version=2), 400),
                (self.request(store="arbitrary"), 400),
                (self.request(operation="sql"), 400),
                (self.request(operation=[]), 400),
                (self.request(tier=[]), 403),
                ([], 400),
            ]:
                self.assertEqual(exchange.response(request)["status"], status)

    def test_discovery_uses_sixteen_existing_targets_and_existing_tiers(self):
        with (
            patch.object(repository, "grove_release_metadata", return_value=None),
            patch.object(repository, "full_release_metadata", return_value=None),
        ):
            result = exchange.response(self.request())["payload"]
        self.assertEqual((result["target_count"], result["press_target_count"]), (16, 14))
        self.assertEqual(len(result["collections"]), 16)
        self.assertNotIn("entity-register", [item["id"] for item in result["collections"]])

    def test_held_need_download_and_enterprise_profile_never_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = exchange.response(
                self.request(
                    "download", collection="need", component="enterprises", release_id="a" * 64
                ),
                Path(temporary),
            )
            self.assertEqual(result["status"], 503)
            self.assertEqual(list(Path(temporary).iterdir()), [])
        result = exchange.response(self.request("profile", cedar_uid="CEDAR-NEST-000049-BS"))
        self.assertEqual(result["status"], 404)

    def test_streamed_bytes_match_pin_and_failure_discards_partial_download(self):
        content = b'{"synthetic":true,"amount":"0.10"}\n'
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request = self.request(
                "download", collection="gaming", component="gaming_facilities", release_id="a" * 64
            )
            for returned_pin, digest, status in [
                ("b" * 64, hashlib.sha256(content).hexdigest(), 503),
                ("a" * 64, "0" * 64, 503),
                ("a" * 64, hashlib.sha256(content).hexdigest(), 200),
            ]:
                stream = io.BytesIO(content)
                release = dict(
                    content_file=stream,
                    release_id=returned_pin,
                    sha256=digest,
                    filename="gaming.jsonl",
                    media_type="application/x-ndjson",
                    record_count=1,
                    citation="Synthetic fixture",
                )
                with patch.object(
                    repository, "grove_full_release", return_value=release
                ) as consumer:
                    result = exchange.response(request, root)
                consumer.assert_called_once_with("gaming", "a" * 64, component="gaming_facilities")
                self.assertTrue(stream.closed)
                self.assertEqual(result["status"], status)
                if status == 200:
                    payload = result["payload"]
                    self.assertEqual((root / payload["file"]).read_bytes(), content)
                    self.assertEqual(payload["bytes"], len(content))
                else:
                    self.assertEqual(list(root.iterdir()), [])

    def test_bad_identifiers_and_unavailable_configuration(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            valid = dict(collection="gaming", component="gaming_facilities", release_id="a" * 64)
            for changes in [
                {"collection": "../gaming"},
                {"release_id": "main"},
                {"component": "../part"},
            ]:
                self.assertEqual(
                    exchange.response(self.request("download", **(valid | changes)), root)[
                        "status"
                    ],
                    400,
                )
            self.assertEqual(exchange.response(self.request("download", **valid))["status"], 503)
        with patch.object(
            repository, "release_targets_for", side_effect=ValueError("credential-detail")
        ):
            self.assertNotIn("credential-detail", str(exchange.response(self.request())))
