"""Execute the receipt-only NEED importer in a disposable fixture workspace."""
import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "code" / "09_import_rulings.py"
COLUMNS = ["review_id", "queue", "uei", "cage_code", "entity_or_firm", "question",
           "YOUR_RULING", "YOUR_NOTE", "decision_id", "reviewer", "decided_at",
           "evidence_fingerprint", "queue_version", "target_cedar_uid", "supersedes_decision_id"]


class TestNeedReceiptImport(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source.bin"
        self.source.write_bytes(b"pinned")
        self.queue = self.root / "queue.json"
        self.queue.write_text(json.dumps({
            "candidate_root": str(self.root), "review_id": "fixture-v1",
            "evidence_fingerprint": "a" * 64,
            "input_sha256": {"source.bin": hashlib.sha256(b"pinned").hexdigest()},
            "records": [{"exception": True, "enterprise": {
                "enterprise_id": "CEDAR-NEST-TEST", "enterprise_name": "Fixture enterprise",
                "owner_hub_cedar_uid": "CE-HUB", "enterprise_existing_cedar_uid": "CE-SELF"}}],
        }), encoding="utf-8")
        self.csv = self.root / "decisions.csv"
        self.receipt = self.root / "receipt.json"
        self.row = dict.fromkeys(COLUMNS, "")
        self.row.update(review_id="NEED:CEDAR-NEST-TEST", queue="need_affiliation",
                        entity_or_firm="Fixture enterprise", question="Affiliation?",
                        YOUR_RULING="HOLD", YOUR_NOTE="Need evidence", decision_id="test-1",
                        reviewer="Fixture reviewer", decided_at="2026-01-01T00:00:00Z",
                        evidence_fingerprint="a"*64, queue_version="fixture-v1",
                        target_cedar_uid="CE-HUB")

    def run_import(self, rows=None):
        with self.csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows or [self.row])
        return subprocess.run([sys.executable, "-B", str(SCRIPT), "--need-review", str(self.csv),
                               "--queue", str(self.queue), "--receipt-ledger", str(self.receipt)],
                              text=True, capture_output=True)

    def test_idempotent_receipt_and_explicit_revision_preserve_hold(self):
        first = self.run_import()
        self.assertEqual(first.returncode, 0, first.stderr)
        before = self.receipt.read_bytes()
        again = self.run_import()
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertIn("ALREADY_RECORDED", again.stdout)
        self.assertEqual(before, self.receipt.read_bytes())
        revised = dict(self.row, decision_id="test-2", YOUR_RULING="SUPPORT",
                       YOUR_NOTE="Explicit revised evidence judgment",
                       supersedes_decision_id="test-1")
        result = self.run_import([revised])
        self.assertEqual(result.returncode, 0, result.stderr)
        ledger = json.loads(self.receipt.read_text())
        self.assertEqual([r["status"] for r in ledger["decisions"]],
                         ["HELD", "RECORDED_PENDING_APPLICATION"])
        self.assertEqual(ledger["decisions"][0]["decision"]["YOUR_NOTE"], "Need evidence")
        self.assertEqual(self.source.read_bytes(), b"pinned")

    def test_rejects_invalid_case_target_stale_note_name_time_and_conflicts(self):
        self.assertEqual(self.run_import().returncode, 0)
        before = self.receipt.read_bytes()
        changes = [
            {"target_cedar_uid": "CE-SELF"}, {"review_id": "NEED:UNKNOWN"},
            {"evidence_fingerprint": "b"*64}, {"queue_version": "old"},
            {"YOUR_NOTE": ""}, {"entity_or_firm": "Wrong name"},
            {"decided_at": "2999-01-01T00:00:00Z"}, {"decided_at": "2026-01-01"},
            {"YOUR_RULING": "REJECT"}, {"decision_id": "another-id"},
            {"decision_id": "another-id", "supersedes_decision_id": "unknown"},
        ]
        for change in changes:
            with self.subTest(change=change):
                result = self.run_import([dict(self.row, **change)])
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(before, self.receipt.read_bytes())
        self.source.write_bytes(b"changed")
        result = self.run_import()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Stale queue input", result.stderr)
        self.assertEqual(before, self.receipt.read_bytes())

    def test_legacy_inbox_refuses_need_before_reading_canonical_ledger(self):
        path = self.root / "rulings_inbox_fixture.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerow(self.row)
        spec = importlib.util.spec_from_file_location("need_receipt_test", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(module, "REVIEW", self.root), patch.object(module, "load_base") as load:
            with self.assertRaisesRegex(SystemExit, "legacy propagation refused"):
                module.main(dry_run=True)
            load.assert_not_called()

    def test_field_ruling_and_conflicting_batch_are_not_applied(self):
        field = dict(self.row, review_id="NEED:enterprise_existing_cedar_uid", queue="need_field",
                     target_cedar_uid="", entity_or_firm="enterprise_existing_cedar_uid",
                     YOUR_RULING="INTERNAL_ONLY", decision_id="field-1")
        result = self.run_import([field, dict(field, YOUR_RULING="PUBLISH_CURRENT")])
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.receipt.exists())
        result = self.run_import([field])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)["applied"])
        self.assertIn("RECORDED_PENDING_APPLICATION", result.stdout)


if __name__ == "__main__":
    unittest.main()
