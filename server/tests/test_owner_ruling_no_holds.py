"""Owner ruling 2026-10-04 (Elijah Moreno): no publication holds.

NEED records and individual Native-owned business records come from publicly
available websites and Lumecon has permission to publish them. Neither
collection carries a collection-wide publication hold, and NEED's committed
samples are served like every other collection's.
"""

import csv
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data" / "cedar" / "collections.manifest.json"


def _collection(cid):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return next(c for c in manifest["collections"] if c["id"] == cid)


class NoPublicationHold(unittest.TestCase):
    def test_no_collection_carries_a_publication_hold(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        for collection in manifest["collections"]:
            with self.subTest(collection=collection["id"]):
                self.assertNotIn("publication_hold", collection)
                for table in collection["tables"]:
                    self.assertNotIn(
                        "held:need_publication", table.get("sample_withheld_columns") or []
                    )

    def test_need_samples_are_declared_and_served_with_rows(self):
        need = _collection("need")
        self.assertTrue(need["sample"]["path"])
        served = [t["sample_path"] for t in need["tables"] if t.get("sample_path")]
        self.assertEqual(len(served), 3)
        for path in served:
            with self.subTest(path=path):
                file = ROOT / "public" / path.lstrip("/")
                with file.open(encoding="utf-8", newline="") as handle:
                    rows = list(csv.DictReader(handle))
                self.assertGreater(len(rows), 0)

    def test_no_need_cleared_set_gates_publication(self):
        self.assertFalse((ROOT / "data" / "cedar" / "need_cleared_enterprise_ids.json").exists())
        source = (ROOT / "code" / "cedar_publication.py").read_text(encoding="utf-8")
        self.assertNotIn("need_row_cleared", source)


if __name__ == "__main__":
    unittest.main()
