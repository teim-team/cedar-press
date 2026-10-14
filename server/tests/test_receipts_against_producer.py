"""``scripts/check_receipts_against_producer.py`` passes on a match and names each drift.

The script itself runs against the pinned Lumecon-data checkout in CI's
``gaming-release-consumer`` job; these tests prove, without the producer, that
it fires on a release the producer never verified and on a manifest that
differs from the verified one.
"""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "check_receipts_against_producer", ROOT / "scripts" / "check_receipts_against_producer.py"
)
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


def inventory(*entries: tuple[str, str, str]) -> dict:
    return {
        "collections": [
            {"collection_id": c, "release_id": r, "aws_database_receipt": {"manifest_sha256": m}}
            for c, r, m in entries
        ]
    }


RECEIPTS = {"collections": {"deals": {"release_id": "r1", "manifest_sha256": "m1"}}}


class ReceiptsAgainstProducer(unittest.TestCase):
    def test_a_matching_release_and_manifest_pass(self) -> None:
        self.assertEqual(CHECK.problems(RECEIPTS, inventory(("deals", "r1", "m1"))), [])

    def test_an_older_snapshot_beside_the_served_one_still_passes(self) -> None:
        found = CHECK.problems(RECEIPTS, inventory(("deals", "r0", "m0"), ("deals", "r1", "m1")))
        self.assertEqual(found, [])

    def test_a_release_the_producer_never_verified_is_named(self) -> None:
        found = CHECK.problems(RECEIPTS, inventory(("deals", "r0", "m0")))
        self.assertEqual(found, ["deals: release r1 is not in the producer's inventory"])

    def test_the_same_release_under_another_collection_does_not_count(self) -> None:
        found = CHECK.problems(RECEIPTS, inventory(("lobbying", "r1", "m1")))
        self.assertEqual(found, ["deals: release r1 is not in the producer's inventory"])

    def test_a_different_manifest_is_named(self) -> None:
        found = CHECK.problems(RECEIPTS, inventory(("deals", "r1", "m2")))
        self.assertEqual(len(found), 1)
        self.assertIn("deals: manifest m1 differs", found[0])

    def test_an_empty_receipts_file_fails(self) -> None:
        self.assertEqual(
            CHECK.problems({"collections": {}}, inventory(("deals", "r1", "m1"))),
            ["the receipts file lists no collections"],
        )

    def test_the_command_exits_1_and_names_the_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            producer = Path(directory)
            (producer / "docs").mkdir()
            (producer / "docs" / "cloud-review-inventory.json").write_text(
                json.dumps(inventory(("deals", "r1", "m2"))), encoding="utf-8"
            )
            receipts = producer / "receipts.json"
            receipts.write_text(json.dumps(RECEIPTS), encoding="utf-8")
            args = ["--producer", str(producer), "--receipts", str(receipts)]
            self.assertEqual(CHECK.main(args), 1)
            (producer / "docs" / "cloud-review-inventory.json").write_text(
                json.dumps(inventory(("deals", "r1", "m1"))), encoding="utf-8"
            )
            self.assertEqual(CHECK.main(args), 0)


if __name__ == "__main__":
    unittest.main()
