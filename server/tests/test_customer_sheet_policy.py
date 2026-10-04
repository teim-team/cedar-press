"""The customer-table rules are the producer's, and every sample download obeys them.

``cedar_press/customer_sheet.py`` is vendored byte for byte from Lumecon-data
(``src/lumecon_data/customer_sheet.py``): the owner's rulings of 2026-10-04 --
Cedar IDs only, DUNS private, public-citation sources, one table per
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
                for packaging in ("record_type", "record_key", "record_grain"):
                    self.assertNotIn(packaging, header)
                self.assertIn("cite_as", rows[0])


if __name__ == "__main__":
    sys.exit(unittest.main())
