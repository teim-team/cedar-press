"""Selected refreshes reuse producer validation and preserve unselected previews."""

import copy
import hashlib
import importlib.util
import io
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/stage_verified_previews.py"
SPEC = importlib.util.spec_from_file_location("selected_preview_stage", SCRIPT)
stage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stage)

OLD = "a" * 64
OLD_MANIFEST = "b" * 64
NEW = "c" * 64
NEW_MANIFEST = "d" * 64
COMMIT = "e" * 40


class SelectedPreviewRefreshTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "press"
        self.producer = self.root / "producer"
        self.output = self.root / "staged"
        self.queue_path = self.root / "queue.json"
        self.entries = []
        self.ledger = {
            "schema_version": 1,
            "producer_commit": "f" * 40,
            "updated": "2026-09-27",
            "collections": {},
        }
        self.book = {"tables": {}, "note": "Preserve unrelated definitions"}
        self.queue = []
        for cid in sorted(stage.EXPECTED):
            raw = f"original,{cid}\n".encode()
            self.ledger["collections"][cid] = {
                "release_id": OLD,
                "manifest_sha256": OLD_MANIFEST,
                "sample_sha256": hashlib.sha256(raw).hexdigest(),
                "sample_rows": 1,
                "public_records": 1,
                "storefront_asset": cid != "gaming",
                "sample_path": f"review-samples/{cid}.csv",
            }
            self.queue.append(
                {
                    "collection": cid,
                    "release": OLD,
                    "manifest_sha256": OLD_MANIFEST,
                    "store": str(self.root / "store"),
                }
            )
            if cid == "gaming":
                continue
            url = f"/data/cedar/samples/{cid}/spreadsheet__10.csv"
            path = self.repo / "public" / url.lstrip("/")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            self.entries.append(
                {
                    "id": cid,
                    "descriptor": {"name": cid, "method": "Prior method", "version": "v4"},
                    "cedar": {"release_id": OLD, "manifest_sha256": OLD_MANIFEST},
                    "sample": {"path": url, "release_id": OLD, "manifest_sha256": OLD_MANIFEST},
                    "tables": [{"table": f"{cid}.csv", "sample_path": url}],
                }
            )
            self.book["tables"][f"{cid}/{cid}"] = {"retained_definition": cid}
        self.manifest = {
            "collections": self.entries,
            "excluded": [{"id": "gaming"}],
            "provenance": {"producer_commit": "f" * 40, "updated": "2026-09-27"},
        }
        stage.write_json(self.repo / "data/cedar/collections.manifest.json", self.manifest)
        stage.write_json(self.repo / "data/cedar/codebook.json", self.book)
        stage.write_json(self.repo / "data/cedar/verified-preview-releases.json", self.ledger)
        stage.write_json(self.repo / "data/cedar/field_map.json", {})
        self.select("funding")
        self.columns = ["record_type", "record_key", "record_grain", "amount"]
        self.rows = [["records", '["source-1"]', "one source observation", "12.50"]]
        self.raw = stage.sample_bytes(self.columns, self.rows)
        self.layout = {
            "columns": self.columns,
            "groups": [{"name": "records"}],
            "mappings": {"records": {"amount": "amount"}},
        }
        self.metadata = {
            "release_id": NEW,
            "source_manifest_sha256": NEW_MANIFEST,
            "sha256": hashlib.sha256(self.raw).hexdigest(),
            "bytes": len(self.raw),
            "columns": self.columns,
            "records": 1,
            "fields": {},
            "held_records_in_selected_groups": 0,
            "release_class": "PUBLIC_DERIVED",
            "unharmonized_fields": [],
        }
        self.package = types.ModuleType("lumecon_data")
        self.dbload = types.ModuleType("lumecon_data.dbload")
        self.spreadsheet = types.ModuleType("lumecon_data.spreadsheet")
        self.dbload.__file__ = str(self.producer / "src/lumecon_data/dbload.py")
        self.spreadsheet.__file__ = str(self.producer / "src/lumecon_data/spreadsheet.py")
        self.dbload.load_manifest = Mock(return_value=({"synthetic": False}, NEW_MANIFEST))
        self.spreadsheet.plan = Mock(side_effect=lambda _: copy.deepcopy(self.layout))
        self.spreadsheet.spool = Mock(
            side_effect=lambda *_: (io.BytesIO(self.raw), copy.deepcopy(self.metadata))
        )
        self.package.dbload, self.package.spreadsheet = self.dbload, self.spreadsheet

    def select(self, cid):
        self.selected = cid
        for item in self.queue:
            item.update(
                release=NEW if item["collection"] == cid else OLD,
                manifest_sha256=NEW_MANIFEST if item["collection"] == cid else OLD_MANIFEST,
            )
        stage.write_json(self.queue_path, self.queue)

    def run_stage(self, expected=OLD):
        modules = {
            "lumecon_data": self.package,
            "lumecon_data.dbload": self.dbload,
            "lumecon_data.spreadsheet": self.spreadsheet,
        }
        with (
            patch.dict(sys.modules, modules),
            patch.dict(os.environ, {"LUMECON_ENVIRONMENT": "review"}),
            patch.object(stage.subprocess, "check_output", side_effect=[COMMIT, ""]),
            patch.object(
                stage,
                "_reviewed_preview_fields",
                return_value=[
                    {"column": name, "meaning": "Fixture observation field"}
                    for name in self.columns
                ],
            ),
        ):
            return stage.stage(
                self.repo,
                self.producer,
                self.queue_path,
                self.output,
                COMMIT,
                "2026-10-01",
                refresh_existing=True,
                collections=[self.selected],
                expected_existing_releases={self.selected: expected},
            )

    def test_only_selected_release_is_loaded_and_spooled_with_complete_merged_ledger(self):
        before = {
            p.relative_to(self.repo): p.read_bytes() for p in self.repo.rglob("*") if p.is_file()
        }
        result = self.run_stage()
        self.dbload.load_manifest.assert_called_once_with(self.root / "store", "funding", NEW)
        self.spreadsheet.spool.assert_called_once_with(self.root / "store", "funding", NEW)
        self.assertEqual(set(result["collections"]), stage.EXPECTED)
        for cid in stage.EXPECTED - {"funding"}:
            self.assertEqual(result["collections"][cid], self.ledger["collections"][cid])
        selected = result["collections"]["funding"]
        self.assertEqual(selected["release_id"], NEW)
        self.assertEqual(selected["producer_commit"], COMMIT)
        self.assertEqual(selected["replaces"], {"release_id": OLD, "manifest_sha256": OLD_MANIFEST})
        self.assertEqual(result["producer_commit"], self.ledger["producer_commit"])
        assets = self.output / "assets"
        proposed = stage.read_json(assets / "data/cedar/collections.manifest.json")
        for previous, current in zip(self.entries, proposed["collections"], strict=True):
            if previous["id"] != "funding":
                self.assertEqual(current, previous)
            else:
                self.assertEqual(previous["descriptor"]["version"], "v4")
                self.assertEqual(current["descriptor"]["version"], "v5")
        self.assertEqual(selected["preview_version"], "v5")
        self.assertEqual(selected["replaces_preview_version"], "v4")
        book = stage.read_json(assets / "data/cedar/codebook.json")
        for key, value in self.book["tables"].items():
            if key != "funding/funding":
                self.assertEqual(book["tables"][key], value)
        self.assertEqual(
            before,
            {p.relative_to(self.repo): p.read_bytes() for p in self.repo.rglob("*") if p.is_file()},
        )
        self.assertEqual(
            [p.parent.name for p in (assets / "public/data/cedar/samples").rglob("*.csv")],
            ["funding"],
        )
        ready = stage.read_json(self.output / "READY.json")
        self.assertEqual(ready["selected_collections"], ["funding"])
        self.assertEqual(ready["ledger_collection_count"], 15)
        self.assertEqual(ready["collection_count"], 1)
        for name, digest in ready["staged_asset_sha256"].items():
            self.assertEqual(hashlib.sha256((assets / name).read_bytes()).hexdigest(), digest)

    def test_unversioned_or_ambiguous_selected_preview_refuses_before_source_read(self):
        for version in (None, "latest", "4", "v04"):
            with self.subTest(version=version):
                manifest = copy.deepcopy(self.manifest)
                next(entry for entry in manifest["collections"] if entry["id"] == "funding")[
                    "descriptor"
                ]["version"] = version
                stage.write_json(self.repo / "data/cedar/collections.manifest.json", manifest)
                with self.assertRaisesRegex(ValueError, "numeric preview version"):
                    self.run_stage()
                self.dbload.load_manifest.assert_not_called()
                self.assertFalse(self.output.exists())

    def test_numeric_preview_increment_is_monotonic_across_digits(self):
        self.assertEqual(stage._next_preview_version("v9"), "v10")
        self.assertEqual(stage._next_preview_version("v99"), "v100")

    def test_wrong_existing_release_refuses_before_any_source_read(self):
        with self.assertRaisesRegex(ValueError, "expected existing release"):
            self.run_stage(expected="9" * 64)
        self.dbload.load_manifest.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_unselected_queue_change_cannot_be_hidden_in_selected_refresh(self):
        next(item for item in self.queue if item["collection"] == "plot")["release"] = "8" * 64
        stage.write_json(self.queue_path, self.queue)
        with self.assertRaisesRegex(ValueError, "unselected queue pin changed"):
            self.run_stage()
        self.spreadsheet.spool.assert_not_called()

    def test_tampered_installed_unselected_sample_refuses_before_spooling(self):
        path = self.repo / "public/data/cedar/samples/contractors/spreadsheet__10.csv"
        path.write_text("tampered")
        with self.assertRaisesRegex(ValueError, "artifact hash mismatch"):
            self.run_stage()
        self.spreadsheet.spool.assert_not_called()

    def test_tampered_new_spreadsheet_cannot_get_ready_marker(self):
        self.metadata["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Spreadsheet bytes differ"):
            self.run_stage()
        self.assertFalse((self.output / "READY.json").exists())

    def test_concurrent_unselected_sample_edit_prevents_ready_marker(self):
        def changed_sample(*_):
            (self.repo / "public/data/cedar/samples/contractors/spreadsheet__10.csv").write_text(
                "race"
            )
            return io.BytesIO(self.raw), copy.deepcopy(self.metadata)

        self.spreadsheet.spool.side_effect = changed_sample
        with self.assertRaisesRegex(ValueError, "input metadata changed"):
            self.run_stage()
        self.assertFalse((self.output / "READY.json").exists())

    def test_need_refresh_cannot_select_an_internal_component(self):
        self.select("need")
        with self.assertRaisesRegex(ValueError, "exact-proof reviewed public base"):
            self.run_stage()
        self.spreadsheet.spool.assert_not_called()
        self.assertFalse((self.output / "READY.json").exists())

    def test_expected_existing_pin_parser_rejects_duplicates_or_unpinned_values(self):
        self.assertEqual(stage._existing_release_pins(["need=" + OLD]), {"need": OLD})
        for values in (["need=" + OLD, "need=" + OLD], ["need=latest"], ["unknown=" + OLD]):
            with self.subTest(values=values), self.assertRaises(ValueError):
                stage._existing_release_pins(values)


if __name__ == "__main__":
    unittest.main()
