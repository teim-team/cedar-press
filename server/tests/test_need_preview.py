"""Static previews require both the maintained proof and exact artifact membership."""

import base64
import csv
import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from cedar_press import need_preview as n
from cedar_press.repository import _canonical_bytes

ROOT = Path(__file__).resolve().parents[2]


def digest(value):
    return hashlib.sha256(value).hexdigest()


class NeedStaticPreviewTest(unittest.TestCase):
    def fixture(self, root):
        # This synthetic two-field artifact isolates the byte/subset boundary.
        # The maintained 17-field evidence-proof gate is deliberately mocked in
        # boundary tests and separately required by the real committed-sample test.
        records = [{"id": "001", "name": "Source name"}, {"id": "002", "name": "'=safe"}]
        raw = b"".join(_canonical_bytes(row) for row in records)
        entry = {
            "fields": [{"name": "id"}, {"name": "name"}],
            "primary_key": ["id"],
            "row_grain": "reviewed enterprise fact",
            "record_count": 2,
            "files": {"records.jsonl": {"sha256": digest(raw), "bytes": len(raw)}},
        }
        manifest = {
            "collection_id": "need",
            "release_id": "a" * 64,
            "synthetic": False,
            "components": {n.COMPONENT: entry},
        }
        envelope = {
            "schema_version": 1,
            "manifest": manifest,
            "records_jsonl_base64": base64.b64encode(raw).decode("ascii"),
        }
        proof = root / n.ENVELOPE
        proof.parent.mkdir(parents=True)
        proof.write_bytes(_canonical_bytes(envelope))
        header = ["record_type", "record_key", "record_grain", "id", "name"]
        out = io.StringIO(newline="")
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(header)
        for row in records:
            writer.writerow(
                [
                    n.COMPONENT,
                    json.dumps([row["id"]], separators=(",", ":")),
                    entry["row_grain"],
                    row["id"],
                    row["name"],
                ]
            )
        sample = root / "public" / n.URL.lstrip("/")
        sample.parent.mkdir(parents=True)
        sample.write_bytes(out.getvalue().encode())
        sha = digest(_canonical_bytes(manifest))
        table = {"table": "need.csv", "sample_path": n.URL, "rows_published": 2}
        collection = {
            "id": "need",
            "cedar": {"cedar_id": "need"},
            "sample": {
                "table": "need.csv",
                "path": n.URL,
                "rows": 2,
                "of": 2,
                "columns": 5,
                "release_id": "a" * 64,
                "manifest_sha256": sha,
            },
            "tables": [table],
            "verified_preview": {
                "component": n.COMPONENT,
                "envelope": n.ENVELOPE,
                "envelope_sha256": digest(proof.read_bytes()),
                "release_id": "a" * 64,
                "manifest_sha256": sha,
                "sample_sha256": digest(sample.read_bytes()),
                "public_records": 2,
            },
        }
        return collection, table, sample, proof, envelope

    def test_valid_subset_requires_the_maintained_flattened_manifest_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            collection, table, _, _, envelope = self.fixture(root)
            with patch.object(n, "reviewed_base_permitted", return_value=True) as gate:
                self.assertTrue(n.need_preview_permitted(root, collection, table))
                gate.assert_called_once_with(
                    envelope["manifest"],
                    n.COMPONENT,
                    envelope["manifest"]["components"][n.COMPONENT],
                )
            with patch.object(n, "reviewed_base_permitted", return_value=False):
                self.assertFalse(n.need_preview_permitted(root, collection, table))

    def test_rehashed_arbitrary_csv_cannot_borrow_a_valid_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            collection, table, sample, _, _ = self.fixture(root)
            sample.write_bytes(sample.read_bytes().replace(b"Source name", b"Fabricated owner"))
            collection["verified_preview"]["sample_sha256"] = digest(sample.read_bytes())
            with patch.object(n, "reviewed_base_permitted", return_value=True):
                self.assertFalse(n.need_preview_permitted(root, collection, table))

    def test_artifact_and_manifest_changes_refuse_even_if_envelope_is_rehashed(self):
        for kind in ("artifact", "manifest"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                collection, table, _, proof, envelope = self.fixture(root)
                if kind == "artifact":
                    envelope["records_jsonl_base64"] = base64.b64encode(b"{}\n").decode()
                else:
                    envelope["manifest"]["release_id"] = "b" * 64
                proof.write_bytes(_canonical_bytes(envelope))
                collection["verified_preview"]["envelope_sha256"] = digest(proof.read_bytes())
                with patch.object(n, "reviewed_base_permitted", return_value=True):
                    self.assertFalse(n.need_preview_permitted(root, collection, table))

    def test_missing_proof_refuses_before_the_sample_locator_runs(self):
        collection = {"id": "need", "sample": {"path": n.URL}}
        table = {"table": "need.csv", "sample_path": n.URL}
        locate = Mock(side_effect=AssertionError("Unproved sample must not be read"))
        self.assertFalse(n.need_preview_permitted(ROOT, collection, table, locate))
        locate.assert_not_called()

    def test_other_need_table_or_path_cannot_use_the_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            collection, table, _, _, _ = self.fixture(root)
            for change in (
                {"table": "patents.csv"},
                {"sample_path": "/data/cedar/samples/need/old.csv"},
            ):
                altered = {**table, **change}
                with patch.object(n, "reviewed_base_permitted", return_value=True):
                    self.assertFalse(n.need_preview_permitted(root, collection, altered))

    def test_import_audit_admits_only_the_verified_table_and_strikes_a_later_held_table(self):
        spec = importlib.util.spec_from_file_location(
            "need_preview_importer_test", ROOT / "scripts/import_cedar_manifest.py"
        )
        importer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(importer)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            collection, table, sample, _, _ = self.fixture(root)
            held = {"table": "patents.csv", "sample_path": "/data/cedar/samples/need/patents.csv"}
            collection["tables"].append(held)
            manifest = {"collections": [collection]}
            with (
                patch.object(n, "reviewed_base_permitted", return_value=True),
                patch.object(importer, "sample_violations", return_value=[]),
            ):
                struck = importer.withhold_samples(
                    manifest,
                    lambda *_: sample,
                    frozenset(),
                    repo=root,
                )
            self.assertEqual([entry["table"] for entry in struck], ["patents.csv"])
            self.assertEqual(table["sample_path"], n.URL)
            self.assertIsNone(held["sample_path"])
            self.assertNotIn("publication_hold", collection)

    def test_two_tables_cannot_share_the_reviewed_preview_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            collection, table, _, _, _ = self.fixture(root)
            collection["tables"].append({"table": "patents.csv", "sample_path": n.URL})
            locate = Mock(side_effect=AssertionError("Ambiguous preview must not be read"))
            with patch.object(n, "reviewed_base_permitted", return_value=True) as gate:
                self.assertFalse(n.need_preview_permitted(root, collection, table, locate))
            locate.assert_not_called()
            gate.assert_not_called()

    def test_current_committed_need_sample_has_real_proof_or_is_not_advertised(self):
        manifest = json.loads(
            (ROOT / "data/cedar/collections.manifest.json").read_text(encoding="utf-8")
        )
        entries = [entry for entry in manifest["collections"] if entry["id"] == "need"]
        self.assertEqual(len(entries), 1)
        if entries[0].get("sample", {}).get("path"):
            self.assertTrue(n.current_need_preview_permitted(ROOT))
        else:
            self.assertFalse(n.current_need_preview_permitted(ROOT))


if __name__ == "__main__":
    unittest.main()
