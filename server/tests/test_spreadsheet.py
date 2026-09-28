"""Customer spreadsheets preserve verified observations and all admission gates."""

import csv
import hashlib
import io
import json
import unittest
from unittest.mock import patch

from cedar_press import repository, spreadsheet
from tests import test_release_download as native_fixture
from tests import test_shared_release_collections as shared_fixture


class SpreadsheetRoutes(unittest.TestCase):
    setUp = shared_fixture.SharedCollectionReleaseTest.setUp
    fixture = shared_fixture.SharedCollectionReleaseTest.fixture
    session = shared_fixture.SharedCollectionReleaseTest.session

    def test_one_csv_keeps_the_verified_rows_and_hides_release_label(self):
        manifest, pin, _ = self.fixture()
        self.session("press_pro")
        path = "/press/collections/plot/spreadsheet-download"
        response = self.client.get(path, params={"release_id": pin["release_id"]})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers["content-disposition"], 'attachment; filename="plot.csv"')
        self.assertTrue(response.headers["content-type"].startswith("text/csv"))
        self.assertEqual(
            response.headers["x-cedar-sha256"], hashlib.sha256(response.content).hexdigest()
        )
        rows = list(csv.DictReader(io.StringIO(response.text)))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["record_type"], "environmental_events")
        self.assertEqual(rows[0]["environmental_event_id"], "SYNTHETIC-1")
        self.assertNotIn(pin["release_id"], response.headers["x-cedar-citation"])
        self.assertEqual(self.client.get(path, params={"release_id": "d" * 64}).status_code, 503)
        self.assertEqual(
            self.client.get(
                path, params={"release_id": pin["release_id"], "component": "environmental_events"}
            ).status_code,
            400,
        )
        manifest["components"]["environmental_events"]["record_count"] += 1
        self.assertEqual(
            self.client.get(path, params={"release_id": pin["release_id"]}).status_code, 503
        )

    def test_held_collection_and_revoked_account_never_reach_bytes(self):
        self.fixture()
        self.session("press_pro")
        with patch.object(repository, "_release_response", side_effect=AssertionError):
            self.assertEqual(
                self.client.get(
                    "/press/collections/need/spreadsheet-download", params={"release_id": "c" * 64}
                ).status_code,
                503,
            )
            from cedar_press import subscribers

            with patch.object(subscribers, "find", return_value=None):
                self.assertEqual(
                    self.client.get(
                        "/press/collections/plot/spreadsheet-download",
                        params={"release_id": "c" * 64},
                    ).status_code,
                    401,
                )


class SingleDatasetSpreadsheet(unittest.TestCase):
    setUp = native_fixture.ReleaseDownloadTest.setUp
    approve_manifest_fixture = native_fixture.ReleaseDownloadTest.approve_manifest_fixture
    write_catalog = native_fixture.ReleaseDownloadTest.write_catalog
    response = native_fixture.ReleaseDownloadTest.response

    def test_existing_flagship_is_a_single_csv_with_identical_observations(self):
        response = self.client.get(
            "/press/collections/legislation/spreadsheet-download", params={"release_id": self.rid}
        )
        self.assertEqual(response.status_code, 200, response.text)
        rows = list(csv.DictReader(io.StringIO(response.text)))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["bill_id"], "fixture-bill")
        self.assertEqual(rows[0]["title"], "Fictional test bill")
        self.assertEqual(set(rows[0]), set(self.header))


class SpreadsheetUnion(unittest.TestCase):
    def test_different_grains_append_without_fanout_or_rounding(self):
        fields = [
            {"name": "id", "type": "string", "description": "Source observation ID"},
            {
                "name": "amount",
                "type": "string",
                "description": "Exact reported amount",
                "unit": "USD",
            },
        ]
        manifest = {
            "components": {
                name: {"fields": fields, "primary_key": ["id"], "row_grain": grain}
                for name, grain in [("awards", "One award"), ("payments", "One payment")]
            }
        }
        values = {
            "awards": {"id": "same-key", "amount": "9007199254740993.01"},
            "payments": {"id": "same-key", "amount": None},
        }

        def component(_pin, _manifest, name, metadata_only=False):
            if metadata_only:
                return {"record_count": 1}
            return {"content_file": io.BytesIO((json.dumps(values[name]) + "\n").encode())}

        with (
            patch.object(repository, "assert_collection_publishable"),
            patch.object(repository, "is_component_release", return_value=True),
            patch.object(repository, "grove_release_pin", return_value={"release_id": "c" * 64}),
            patch.object(repository, "_grove_catalog"),
            patch.object(repository, "_grove_manifest", return_value=manifest),
            patch.object(repository, "grove_components", return_value=("awards", "payments")),
            patch.object(repository, "_grove_component_release", side_effect=component),
        ):
            result = spreadsheet.download("fixture", "c" * 64)
            with result["content_file"] as content:
                rows = list(csv.DictReader(io.StringIO(content.read().decode())))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["amount"], "9007199254740993.01")
            self.assertEqual(rows[1]["amount"], "")
            self.assertEqual({row["record_grain"] for row in rows}, {"One award", "One payment"})
            manifest["components"]["payments"]["fields"] = [dict(field) for field in fields]
            manifest["components"]["payments"]["fields"][1]["unit"] = "thousands of USD"
            metadata = spreadsheet.metadata("fixture")
            self.assertNotIn("amount", metadata["fields"])
            self.assertIn("awards__amount", metadata["fields"])
            self.assertIn("payments__amount", metadata["fields"])

    def test_cells_preserve_nulls_zeros_and_exact_decimals(self):
        self.assertEqual(spreadsheet._cell(None), "")
        self.assertEqual(spreadsheet._cell(0), "0")
        self.assertEqual(spreadsheet._cell("-9007199254740993.01"), "-9007199254740993.01")
        self.assertEqual(spreadsheet._cell("=HYPERLINK(1)"), "'=HYPERLINK(1)")
