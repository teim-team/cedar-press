"""Spreadsheet metadata counts the same permitted records as its download."""

import hashlib
import json
import unittest
from unittest.mock import patch

from cedar_press import spreadsheet


class SpreadsheetCountsTest(unittest.TestCase):
    def test_single_release_count_is_not_the_legacy_manifest_total(self):
        source = {
            "release_id": "a" * 64,
            "fields": ["record_id", "amount"],
            "record_count": 12,
        }
        with (
            patch.object(spreadsheet.r, "assert_collection_publishable"),
            patch.object(spreadsheet.r, "is_component_release", return_value=False),
            patch.object(spreadsheet.r, "full_release", return_value=source) as verified,
        ):
            metadata = spreadsheet.download("funding", metadata_only=True)
        self.assertEqual(metadata["record_count"], 12)
        self.assertEqual(metadata["release_id"], source["release_id"])
        verified.assert_called_once_with("funding", None, metadata_only=True)

    def test_component_count_uses_only_the_customer_tables_main_grain(self):
        manifest = {"components": {"held": {"record_count": 999}}}
        pin = {
            "release_id": "b" * 64,
            "manifest_sha256": hashlib.sha256(
                json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        }
        tables = {
            "tract_observations": {"contract": {}, "descriptor": {"record_count": 12}},
            "ownership_observations": {"contract": {}, "descriptor": {"record_count": 8}},
            "permits": {"contract": {}, "descriptor": {"record_count": 999}},
        }
        layout = {
            "grain": "One land observation.",
            "main": {"tables": ["tract_observations", "ownership_observations"]},
            "attach": [],
        }
        with (
            patch.object(spreadsheet.r, "assert_collection_publishable"),
            patch.object(spreadsheet.r, "is_component_release", return_value=True),
            patch.object(spreadsheet.r, "grove_release_pin", return_value=pin),
            patch.object(spreadsheet.r, "_grove_catalog"),
            patch.object(
                spreadsheet.r,
                "_grove_manifest",
                return_value=manifest,
            ),
            patch.object(spreadsheet, "_tables", return_value=tables),
            patch.object(
                spreadsheet, "_layout", return_value=(layout, {"columns": {"amount": {}}})
            ),
        ):
            metadata = spreadsheet.download("plot", metadata_only=True)
        self.assertEqual(metadata["record_count"], 20)
        self.assertEqual(metadata["release_id"], pin["release_id"])
        self.assertEqual(metadata["manifest_sha256"], pin["manifest_sha256"])


if __name__ == "__main__":
    unittest.main()
