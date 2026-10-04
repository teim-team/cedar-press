"""The customer-table rules are the producer's, and every sample download obeys them.

``cedar_press/customer_sheet.py`` is vendored byte for byte from Lumecon-data
(``src/lumecon_data/customer_sheet.py``): the owner's rulings of 2026-10-04 --
dataset and public registry identifiers stay and only proprietary identifiers
(DUNS, Casino City) are removed, public-citation sources, one table per
collection, no version labels -- are one set of rules on both sides.
"""

import csv
import io
import os
import sys
import unittest
from pathlib import Path

from cedar_press import customer_sheet

ROOT = Path(__file__).resolve().parents[2]


class VendoredPolicy(unittest.TestCase):
    def test_vendored_copy_is_the_producers(self):
        """Required where the producer is installed (Lumecon-data cedar-check, Gaming job)."""
        required = os.environ.get("CEDAR_REQUIRE_LUMECON_GAMING") == "1"
        try:
            from lumecon_data import customer_sheet as producer
        except ImportError:
            if required:
                raise
            self.skipTest("Lumecon-data is not installed in this job")
        self.assertEqual(
            Path(producer.__file__).read_bytes(),
            Path(customer_sheet.__file__).read_bytes(),
        )


class IdentifierRules(unittest.TestCase):
    """Owner correction 2026-10-04: dataset IDs stay; DUNS and Casino City go."""

    DATASET_IDS = {
        "deal_id": "ACQ2020-015",
        "disclosure_id": "GIV-000123",
        "award_id": "AWD-77",
        "source_record_id": "990PF-2019-25",
        "activity_id": "LDA-ACT-9",
        "superseded_by_record_id": "f0a2-lda",
        "supersession_group_id": "LDA-GRP-4",
        "resource_revenue_event_id": "ONRR-2020-55",
        "subject_binding": "uei:Y1WNAYBJH9Z6",
        "business_source_id": "OWNERV6-12",
        "plot_record_id": "PLOT-TRACT-1",
        "subaward_record_id": "FSRS-SUB-31",
        "uei": "Y1WNAYBJH9Z6",
        "ein": "47-0000001",
        "cedar_uid": "CE-0017X-NE",
        "legacy_facility_id": "VP-0170",
    }
    REMOVED = {
        "recipient_duns": "123456789",
        "casino_city_id": "CC-55",
        "row_sha256": "a" * 64,
        "schema_version": "v1.0",
        "record_key": '["K"]',
    }

    def test_dataset_ids_are_presented_and_proprietary_ids_are_not(self):
        row = {
            **self.DATASET_IDS,
            **self.REMOVED,
            "identifier_type": "DUNS",
            "identifier_value": "987654321",
            "facility_keys": "CCP-843900; VP-0171",
            "note": "listed by Casino City",
            "remark": "DUNS 123456789 per vendor list",
            "label": "v1.0",
        }
        fields = [{"name": name, "type": "string"} for name in row]
        header, rows, report = customer_sheet.present_rows("deals", fields, [row])
        for name, value in self.DATASET_IDS.items():
            self.assertIn(name, header)
            self.assertEqual(rows[0][name], value)
        for name in self.REMOVED:
            self.assertNotIn(name, header)
        self.assertIsNone(rows[0]["identifier_value"])
        self.assertEqual(rows[0]["facility_keys"], "VP-0171")
        self.assertIsNone(rows[0]["note"])
        self.assertEqual(rows[0]["remark"], "per vendor list")
        self.assertIsNone(rows[0]["label"])
        text = repr(rows)
        for leaked in ("123456789", "987654321", "CCP-", "Casino City"):
            self.assertNotIn(leaked, text)
        self.assertIn("deal_id", report["dataset_id_columns"])
        self.assertIn("uei", report["public_registry_id_columns"])
        self.assertEqual(customer_sheet.check_table(header, rows), [])


class SampleDownloads(unittest.TestCase):
    """Every collection's sample download is one clean customer table."""

    def test_every_sample_download_obeys_the_customer_table_rules(self):
        from cedar_press import collections as launch
        from cedar_press import repository

        served = [d.id for d in launch.LAUNCH_COLLECTION if launch.collection_csv(d.id)]
        self.assertGreaterEqual(len(served), 10)
        for collection in served:
            with self.subTest(collection=collection):
                text = repository.collection_csv(collection)
                rows = list(csv.DictReader(io.StringIO(text, newline="")))
                self.assertTrue(rows)
                header = [name for name in rows[0] if name != "cite_as"]
                self.assertEqual(customer_sheet.check_table(header, rows), [])
                self.assertFalse([c for c in header if "duns" in c.lower()])
                self.assertFalse([c for c in header if "casino" in c.lower()])
                for packaging in ("record_type", "record_key", "record_grain"):
                    self.assertNotIn(packaging, header)
                self.assertIn("cite_as", rows[0])


if __name__ == "__main__":
    sys.exit(unittest.main())
