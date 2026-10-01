"""The preview consumes complete verified output and cannot disguise a stale tail."""

import hashlib
import importlib.util
import io
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

SPEC = importlib.util.spec_from_file_location(
    "stage_verified_previews",
    Path(__file__).resolve().parents[2] / "scripts/stage_verified_previews.py",
)
preview = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preview)


class VerifiedPreviewTest(unittest.TestCase):
    def test_proof_json_uses_lf_bytes_preserved_by_git(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "proof.json"
            preview.write_json(path, {"source": "line one\nline two", "rows": 27})
            content = path.read_bytes()
            self.assertNotIn(b"\r\n", content)
            self.assertEqual(content, content.replace(b"\r\n", b"\n"))

    def fixture(self, rows):
        columns = ["record_type", "record_key", "record_grain", "amount", "name"]
        blob = preview.sample_bytes(columns, rows)
        metadata = {
            "columns": columns,
            "sha256": hashlib.sha256(blob).hexdigest(),
            "bytes": len(blob),
            "records": len(rows),
        }
        layout = {"columns": columns, "groups": [{"name": "awards"}, {"name": "payments"}]}
        return io.BytesIO(blob), metadata, layout

    def test_samples_keep_negative_zero_blank_and_quoted_multiline_cells(self):
        records = [
            ["awards", '["001"]', "award version", "-125.00", 'Name,\n"source"'],
            ["payments", '["p1"]', "payment", "0", ""],
            ["awards", '["002"]', "award version", "", "'=untrusted()"],
        ]
        stream, metadata, layout = self.fixture(records)
        _, sample, counts = preview.read_preview(stream, metadata, layout)
        self.assertEqual(sample, [records[0], records[1], records[2]])
        self.assertEqual(counts, {"awards": 2, "payments": 1})
        self.assertEqual(records[0][3], "-125.00")
        self.assertFalse(stream.closed)

    def test_full_tail_is_validated_after_ten_preview_rows(self):
        records = [["awards", f'["{i}"]', "award", "0", "source"] for i in range(11)]
        records[-1][0] = "held-component-not-in-plan"
        stream, metadata, layout = self.fixture(records)
        with self.assertRaisesRegex(ValueError, "Unknown record type"):
            preview.read_preview(stream, metadata, layout)

    def test_digest_and_full_count_are_bound_to_the_receipt(self):
        records = [["payments", '["p1"]', "payment", "0", "name"]]
        stream, metadata, layout = self.fixture(records)
        metadata["records"] = 2
        with self.assertRaisesRegex(ValueError, "count differs"):
            preview.read_preview(stream, metadata, layout)
        stream, metadata, layout = self.fixture(records)
        metadata["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "bytes differ"):
            preview.read_preview(stream, metadata, layout)

    def test_rows_are_distributed_by_type_without_summing_amounts(self):
        records = [["awards", f'["a{i}"]', "award", "100", "name"] for i in range(15)]
        records += [["payments", '["p1"]', "payment", "40", "name"]]
        stream, metadata, layout = self.fixture(records)
        _, sample, counts = preview.read_preview(stream, metadata, layout)
        self.assertEqual(len(sample), 10)
        self.assertEqual(sample[1][0], "payments")
        self.assertEqual(counts, {"awards": 15, "payments": 1})

    def test_queue_requires_complete_unique_pins_and_no_implicit_latest(self):
        valid = [
            {
                "collection": cid,
                "release": "a" * 64,
                "manifest_sha256": "b" * 64,
                "store": str(Path.cwd().resolve()),
            }
            for cid in sorted(preview.EXPECTED)
        ]
        self.assertEqual(set(preview.queue_items(valid)), preview.EXPECTED)
        with self.assertRaisesRegex(ValueError, "all 15"):
            preview.queue_items(valid[:-1])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            preview.queue_items([*valid, valid[0]])
        bad = [dict(row) for row in valid]
        bad[0]["release"] = "latest"
        with self.assertRaisesRegex(ValueError, "exact lowercase"):
            preview.queue_items(bad)


if __name__ == "__main__":
    unittest.main()
