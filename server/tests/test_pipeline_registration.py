"""Data-less checks of producer admission through the existing runner contract."""

import argparse
import contextlib
import copy
import importlib.util
import io
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "pipeline_registration", ROOT / "code/cedar_pipeline.py"
)
PIPELINE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PIPELINE)


class ProducerRegistrationTest(unittest.TestCase):
    def test_release_pilot_delegates_pinned_inputs_without_local_builder(self):
        spec = importlib.util.spec_from_file_location("delegated_build", ROOT / "code/build.py")
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        publication = __import__("cedar_publication")
        pipeline = types.ModuleType("lumecon_data.pipeline")
        pipeline.build_collection_release = Mock(return_value={
            "manifest": {"release_id": "fixture-release", "record_count": 1},
            "catalog_path": "fixture-catalog", "receipt_sha256": "fixture-receipt"})
        storage = types.ModuleType("lumecon_data.storage")
        storage.checked_path = lambda value: value
        storage.canonical_json = lambda value: json.dumps(value, sort_keys=True).encode()
        modules = {"lumecon_data": types.ModuleType("lumecon_data"),
                   "lumecon_data.pipeline": pipeline, "lumecon_data.storage": storage}
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source_dir = base / "source"
            source_dir.mkdir()
            source = source_dir / "native_bills.csv"
            source.write_bytes(b"fixture source bytes")
            actions = source.with_name("native_bill_actions.csv")
            actions.write_bytes(b"fixture action bytes")
            args = argparse.Namespace(collection="legislation", source=str(source),
                                      output_root=str(base / "store"), as_of="2026-09-24")
            with (patch.dict(sys.modules, modules),
                  patch.object(publication, "field_map", return_value={"legislation": {"fixture": "map"}}),
                  patch.object(publication, "register", return_value={}),
                  patch.object(publication, "scopes", return_value={}),
                  contextlib.redirect_stdout(io.StringIO())):
                self.assertEqual(runner.cmd_release_pilot(args), 0)
            call = pipeline.build_collection_release.call_args
            self.assertEqual(call.args, (base / "store", "legislation"))
            self.assertEqual(call.kwargs["source_bytes"], b"fixture source bytes")
            self.assertEqual(call.kwargs["actions_bytes"], b"fixture action bytes")
            self.assertEqual(json.loads(call.kwargs["field_map_bytes"]), {"fixture": "map"})
            self.assertFalse((base / "store").exists())
            self.assertEqual(source.read_bytes(), b"fixture source bytes")

    def test_twelve_collection_allowlist_excludes_other_products(self):
        self.assertEqual(set(PIPELINE.RELEASE_PILOTS), {
            "funding", "federal-register", "legislation", "deals", "nagpra", "lobbying",
            "contractors", "subcontracting", "native-owned-businesses", "nonprofits", "natural-resources", "need",
        })

    def test_blocked_adapter_streams_source_and_returns_failure_receipt(self):
        spec = importlib.util.spec_from_file_location("blocked_build", ROOT / "code/build.py")
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        publication = __import__("cedar_publication")
        pipeline = types.ModuleType("lumecon_data.pipeline")
        pipeline.build_collection_release = Mock()
        blocked = types.ModuleType("lumecon_data.collections.press_blocked")
        blocked.build_blocked_press_candidate = Mock(return_value={
            "status": "BLOCKED", "source_rows": 1, "withheld_rows": 1,
            "candidate_id": "held-fixture", "blockers": ["engineering_gate"]})
        storage = types.ModuleType("lumecon_data.storage")
        storage.checked_path = lambda value: value
        storage.canonical_json = lambda value: json.dumps(value, sort_keys=True).encode()
        modules = {"lumecon_data": types.ModuleType("lumecon_data"),
                   "lumecon_data.pipeline": pipeline, "lumecon_data.storage": storage,
                   "lumecon_data.collections": types.ModuleType("lumecon_data.collections"),
                   "lumecon_data.collections.press_blocked": blocked}
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source" / "federal_funding_transactions.csv"
            source.parent.mkdir()
            source.write_bytes(b"source-key\nsource-record\n")
            args = argparse.Namespace(collection="funding", source=str(source),
                                      output_root=str(base / "store"), as_of="2026-09-25")
            original_read = Path.read_bytes
            def guarded_read(path):
                if path == source:
                    raise AssertionError("Bulk source must not be materialized by Cedar")
                return original_read(path)
            output = io.StringIO()
            with (patch.dict(sys.modules, modules),
                  patch.object(Path, "read_bytes", guarded_read),
                  patch.object(publication, "field_map", return_value={"funding": {}}),
                  patch.object(publication, "register", return_value={}),
                  patch.object(publication, "scopes", return_value={}),
                  patch.object(publication, "denied_ueis", return_value={}),
                  contextlib.redirect_stdout(output)):
                self.assertEqual(runner.cmd_release_pilot(args), 1)
            call = blocked.build_blocked_press_candidate.call_args
            self.assertEqual(call.args, (base / "store", "funding", source))
            self.assertIn("publication-policy.json", call.kwargs["decision_inputs"])
            self.assertEqual(json.loads(output.getvalue())["withheld_rows"], 1)
            pipeline.build_collection_release.assert_not_called()
            self.assertFalse((base / "store").exists())

    def test_writer_authority_refresh_preserves_measurements_and_input(self):
        spec = importlib.util.spec_from_file_location(
            "contract_refresh", ROOT / "code/512_build_dataset_contracts.py"
        )
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        doc = json.loads((ROOT / "docs/schema/dataset_contracts.json").read_text(encoding="utf-8"))
        # Include stale edges even after the checked-in generated contract is refreshed.
        table = next(
            t
            for c in doc["contracts"]
            for t in c["tables"]
            if t["table"] == "federal_funding_transactions.csv"
        )
        retired = [
            "335_harmonize_assistance_seams_in_place.py",
            "336_correct_scheme_resolution_by_spine_membership.py",
        ]
        table["enriched_by"] += [s for s in retired if s not in table["enriched_by"]]
        before = copy.deepcopy(doc)
        expected = copy.deepcopy(doc)
        for contract in expected["contracts"]:
            for target in contract["tables"]:
                if target["table"] == "federal_funding_transactions.csv":
                    for field in ("rebuilt_by", "enriched_by"):
                        target[field] = [s for s in target[field] if s not in retired]
        with patch.object(generator, "build_contracts", side_effect=AssertionError("no data scan")):
            actual = generator.refresh_writer_authority(doc)
        self.assertEqual(actual, expected)
        self.assertEqual(doc, before)
        self.assertEqual(generator.refresh_writer_authority(actual), actual)

    def test_retired_funding_edges_cannot_be_reauthorized_by_stale_contract(self):
        table = "federal_funding_transactions.csv"
        retired = [
            "335_harmonize_assistance_seams_in_place.py",
            "336_correct_scheme_resolution_by_spine_membership.py",
        ]
        for stage in retired:
            plan = {
                "id": "funding",
                "phase1": [],
                "phase2": [stage],
                "rb": {},
                "en": {stage: [table]},
            }
            contracts = {
                "contracts": [
                    {
                        "collection": "funding",
                        "rebuild_command": "py -3 code/build.py run funding --execute",
                        "tables": [{"table": table, "enriched_by": [stage]}],
                    }
                ]
            }
            with self.subTest(stage=stage):
                self.assertIn(
                    "RETIRED_TABLE_WRITER: " + stage + " -> " + table,
                    PIPELINE.registration_problems(plan, contracts),
                )
        self.assertEqual(
            PIPELINE.active_table_writers(
                table, retired + ["24_funding_merge.py", "503_identity.py"]
            ),
            ["24_funding_merge.py", "503_identity.py"],
        )
        self.assertEqual(PIPELINE.active_table_writers("historical.csv", retired), retired)

    def test_retired_funding_direct_entrypoints_refuse_before_io_even_with_force(self):
        for name in ("335_harmonize_assistance_seams_in_place.py",
                     "336_correct_scheme_resolution_by_spine_membership.py"):
            spec = importlib.util.spec_from_file_location("retired_funding", ROOT / "code" / name)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            with self.subTest(script=name), \
                 patch.object(sys, "argv", [name, "--force-retired-cicd-crosswalk"]), \
                 patch("builtins.open", side_effect=AssertionError("retired entry point performed IO")), \
                 patch.object(Path, "exists", side_effect=AssertionError("retired entry point inspected data")), \
                 patch.object(Path, "stat", side_effect=AssertionError("retired entry point inspected data")), \
                 patch.object(module.shutil, "copy2", side_effect=AssertionError("retired entry point wrote backup")):
                with self.assertRaisesRegex(SystemExit, "RETIRED_TABLE_WRITER"):
                    module.main()

    def test_dependency_snapshot_refresh_removes_only_retired_edges(self):
        spec = importlib.util.spec_from_file_location("dependency_refresh", ROOT / "code/287_build_dependency_manifest.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        table = "federal_funding_transactions.csv"
        retired = "335_harmonize_assistance_seams_in_place.py"
        original = {"generated": "2026-09-02", "columns_lost_vs_backup": {"legacy": ["x"]},
                    "writers": {table: [retired, "24_funding_merge.py", "503_identity.py"]},
                    "contested_files": {table: {"rebuilders": ["24_funding_merge.py", retired],
                                                "enrichers": [retired, "503_identity.py"]}}}
        before = copy.deepcopy(original)
        refreshed = module.refresh_writer_authority(original)
        self.assertEqual(original, before)
        self.assertEqual(refreshed["generated"], before["generated"])
        self.assertEqual(refreshed["columns_lost_vs_backup"], before["columns_lost_vs_backup"])
        self.assertNotIn(retired, refreshed["writers"][table])
        self.assertEqual(module.refresh_writer_authority(refreshed), refreshed)
        text = "Dated introduction\n## Contested files (1)\nold\n## Survival check\nmeasured historic result\n"
        rendered = module.refresh_writer_markdown(text, refreshed)
        self.assertNotIn(retired, rendered)
        self.assertIn("503_identity.py", rendered)
        self.assertTrue(rendered.endswith("## Survival check\nmeasured historic result\n"))
        self.assertEqual(module.refresh_writer_markdown(rendered, refreshed), rendered)
        with self.assertRaises(ValueError):
            module.refresh_writer_markdown("missing section", refreshed)

    def test_forbidden_codebook_entrypoint_keeps_helpers_without_writing(self):
        spec = importlib.util.spec_from_file_location("retired_codebook", ROOT / "code/41_build_codebooks.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(callable(module.access_tier))
        self.assertTrue(callable(module.describe))
        import cedar_pipeline
        with patch.object(Path, "mkdir", side_effect=AssertionError("forbidden writer created output")), \
             patch("builtins.open", side_effect=AssertionError("forbidden writer performed IO")):
            with self.assertRaises(cedar_pipeline.ForbiddenScript):
                module.main()

    def test_methodology_authority_refresh_preserves_all_measurements_and_editorial(self):
        spec = importlib.util.spec_from_file_location("methodology_refresh", ROOT / "code/1143_methodology_papers.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        before = (ROOT / "docs/methodology/funding.md").read_text(encoding="utf-8")
        # Exercise a stale stored section even after its committed regeneration.
        before = before.replace("| `24_funding_merge.py` |", "| `24_funding_merge.py`, `335_harmonize_assistance_seams_in_place.py` |", 1)
        with patch.object(module, "measure", side_effect=AssertionError("no data measurement allowed")):
            after = module.refresh_pipeline_authority(before, "funding")
            self.assertEqual(module.refresh_pipeline_authority(after, "funding"), after)
        prefix, section = before.split("## M2 ", 1)
        _, suffix = section.split("## M3 ", 1)
        self.assertTrue(after.startswith(prefix + "## M2 "))
        self.assertTrue(after.endswith("## M3 " + suffix))
        m2 = after.split("## M2 ", 1)[1].split("## M3 ", 1)[0]
        self.assertNotIn("335_harmonize_assistance_seams_in_place.py", m2)
        self.assertNotIn("336_correct_scheme_resolution_by_spine_membership.py", m2)
        self.assertIn("503_identity.py", m2)
        self.assertIn("release-pilot funding --source", m2)
        self.assertIn("not current release certification", m2)
        for invalid in ("missing", before.replace(module.MARK_M_E, "")):
            with self.assertRaises(ValueError):
                module.refresh_pipeline_authority(invalid, "funding")
        with self.assertRaises(ValueError):
            module.refresh_pipeline_authority(before, "../funding")

    def test_funding_plan_cuts_over_discovered_retired_edges_without_build(self):
        spec = importlib.util.spec_from_file_location("funding_build", ROOT / "code/build.py")
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        table = "federal_funding_transactions.csv"
        retired = [
            "335_harmonize_assistance_seams_in_place.py",
            "336_correct_scheme_resolution_by_spine_membership.py",
        ]
        with (
            patch.object(runner, "collection_tables", return_value=[table]),
            patch.object(
                runner,
                "_io_map",
                return_value=(
                    {table: ["24_funding_merge.py"]},
                    {table: retired + ["503_identity.py"]},
                ),
            ),
            patch.object(runner.subprocess, "run") as dispatch,
        ):
            plan = runner.plan_for("funding")
        self.assertEqual(plan["phase1"], ["24_funding_merge.py"])
        self.assertEqual(plan["phase2"], ["503_identity.py"])
        self.assertFalse(set(retired) & (set(plan["rb"]) | set(plan["en"])))
        dispatch.assert_not_called()

    def test_projection_provenance_records_absence_and_changed_decision_inputs(self):
        spec = importlib.util.spec_from_file_location("authority_build", ROOT / "code/build.py")
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before = runner.pilot_authority_hashes(root)
            key = "data/clean/cedar_ruling_ledger_consolidated.csv"
            self.assertEqual(before[key], "ABSENT")
            self.assertIn("code/503_identity.py", before)
            self.assertIn("graveyard/cicd/cedar_handle_history.csv", before)
            path = root / key
            path.parent.mkdir(parents=True)
            path.write_text("fixture ruling", encoding="utf-8")
            present = runner.pilot_authority_hashes(root)
            self.assertNotEqual(before, present)
            self.assertEqual(len(present[key]), 64)
            path.write_text("changed fixture ruling", encoding="utf-8")
            self.assertNotEqual(present, runner.pilot_authority_hashes(root))

    def test_candidate_store_cannot_target_any_repository(self):
        spec = importlib.util.spec_from_file_location("target_build", ROOT / "code/build.py")
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source" / "source.csv"
            other_repo = root / "other-repo"
            other_repo.mkdir()
            (other_repo / ".git").write_text("gitdir: fictional-worktree", encoding="utf-8")
            for target in (source.parent / "candidate", root, other_repo / "data" / "clean"):
                with self.subTest(target=target), self.assertRaises(ValueError):
                    runner.assert_pilot_target(source, target)
            runner.assert_pilot_target(source, root / "isolated-candidates")

    def setUp(self):
        self.plan = {
            "id": "fixture",
            "phase1": ["build_fixture.py"],
            "phase2": [],
            "rb": {"build_fixture.py": ["fixture.csv"]},
            "en": {},
        }
        self.contracts = {
            "contracts": [
                {
                    "collection": "fixture",
                    "rebuild_command": "py -3 code/build.py run fixture --execute",
                    "tables": [{"table": "fixture.csv", "rebuilt_by": ["build_fixture.py"]}],
                }
            ]
        }

    def test_registered_stage_and_explicit_ordered_component(self):
        self.assertEqual(PIPELINE.registration_problems(self.plan, self.contracts), [])
        self.plan["phase2"] = ["enrich_fixture.py"]
        self.plan["en"] = {"enrich_fixture.py": ["fixture.csv"]}
        with patch.object(
            PIPELINE,
            "KNOWN_ORDERINGS",
            [
                {
                    "file": "fixture.csv",
                    "rebuild": "build_fixture.py",
                    "enricher": "enrich_fixture.py",
                }
            ],
        ):
            self.assertEqual(PIPELINE.registration_problems(self.plan, self.contracts), [])

    def test_new_writer_in_discovery_does_not_authorize_it(self):
        self.plan["phase1"].append("new_builder.py")
        self.plan["rb"]["new_builder.py"] = ["fixture.csv"]
        self.assertIn(
            "UNREGISTERED_PRODUCER: new_builder.py -> fixture.csv",
            PIPELINE.registration_problems(self.plan, self.contracts),
        )
        self.contracts["contracts"][0]["tables"][0]["rebuilt_by"].append("new_builder.py")
        self.assertEqual(PIPELINE.registration_problems(self.plan, self.contracts), [])

    def test_new_output_and_missing_write_set_are_refused(self):
        self.plan["rb"]["build_fixture.py"] = ["unowned.csv"]
        self.assertIn(
            "UNREGISTERED_TABLE: unowned.csv",
            PIPELINE.registration_problems(self.plan, self.contracts),
        )
        self.plan["rb"] = {}
        self.assertIn(
            "UNDECLARED_OUTPUTS: build_fixture.py",
            PIPELINE.registration_problems(self.plan, self.contracts),
        )

    def test_no_parallel_runner_or_path_escape(self):
        self.contracts["contracts"][0]["rebuild_command"] = "python new_master.py fixture"
        self.assertTrue(
            PIPELINE.registration_problems(self.plan, self.contracts)[0].startswith(
                "UNSUPPORTED_ENTRY_POINT"
            )
        )
        self.contracts["contracts"][0]["rebuild_command"] = (
            "python code/build.py run fixture --execute"
        )
        self.plan["phase1"] = ["../outside.py"]
        self.assertIn(
            "INVALID_STAGE_PATH: ../outside.py",
            PIPELINE.registration_problems(self.plan, self.contracts),
        )

    def test_missing_and_ambiguous_authority_fails_closed(self):
        for contracts in (
            {},
            {"contracts": []},
            {"contracts": [self.contracts["contracts"][0]] * 2},
        ):
            with self.subTest(contracts=contracts):
                self.assertTrue(PIPELINE.registration_problems(self.plan, contracts))
        broken = copy.deepcopy(self.contracts)
        broken["contracts"][0]["tables"][0]["rebuilt_by"] = "not-a-list"
        self.assertTrue(PIPELINE.registration_problems(self.plan, broken))

    def test_inventory_or_contract_cannot_override_hard_prohibition(self):
        with patch.object(PIPELINE, "NEVER_RUN", {"build_fixture.py": "fixture prohibition"}):
            self.assertEqual(
                PIPELINE.registration_problems(self.plan, self.contracts),
                ["FORBIDDEN_PRODUCER: build_fixture.py"],
            )

    def test_new_executable_requires_existing_inventory_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "code").mkdir()
            (root / "code/new_builder.py").write_text("print('fixture')\n", encoding="utf-8")
            inventory = {"scripts": []}
            self.assertEqual(
                PIPELINE.script_inventory_problems(root, inventory),
                ["UNINVENTORIED_DATA_CODE: code/new_builder.py"],
            )
            inventory["scripts"] = [{"script": "new_builder.py", "dir": ""}]
            self.assertEqual(PIPELINE.script_inventory_problems(root, inventory), [])
            # Being inventoried still does not grant a producer authority.
            self.plan["phase1"] = ["new_builder.py"]
            self.plan["rb"] = {"new_builder.py": ["fixture.csv"]}
            self.assertTrue(PIPELINE.registration_problems(self.plan, self.contracts))

    def test_current_tree_has_no_uninventoried_data_code(self):
        self.assertEqual(PIPELINE.script_inventory_problems(ROOT), [])

    def test_supported_runner_refuses_unregistered_dispatch(self):
        spec = importlib.util.spec_from_file_location("registered_build", ROOT / "code/build.py")
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        plan = {**self.plan, "tables": ["fixture.csv"], "ambiguous": [], "blocked": []}
        with (
            patch.object(runner, "plan_for", return_value=plan),
            patch.object(runner.subprocess, "run") as dispatch,
            contextlib.redirect_stderr(io.StringIO()) as errors,
        ):
            self.assertEqual(
                runner.cmd_run(argparse.Namespace(execute=True, collection="fixture")), 1
            )
        dispatch.assert_not_called()
        self.assertIn("UNREGISTERED_COLLECTION", errors.getvalue())


class ScriptCensusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "script_census", ROOT / "code/521_inventory.py"
        )
        cls.inventory = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.inventory)

    def test_writer_evidence_uses_write_operations_not_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "candidate.py"
            path.write_text(
                "from pathlib import Path\n"
                "OUT = Path('data/clean') / 'governed.csv'\n"
                "text = 'data/spine/private.csv write_text'\n"
                "OUT.read_text()\n"
                "OUT.write_text('fixture')\n"
                "open('read_only.csv', 'r')\n"
                "gzip.open('data.csv', 'r')\n"
                "Image.open('data.png')\n"
                "def dynamic(target):\n    target.write_bytes(b'fixture')\n",
                encoding="utf-8",
            )
            evidence = self.inventory.writer_evidence(path, {"governed.csv": {}})
            self.assertEqual(len(evidence), 2)
            self.assertEqual(evidence[0]["target"], "data/clean/governed.csv")
            self.assertEqual(evidence[0]["scope"], "governed_table")
            self.assertEqual(evidence[1]["scope"], "unresolved_target")

    def test_current_tree_has_no_new_unregistered_writer_edges(self):
        self.assertEqual(self.inventory.writer_admission_problems(ROOT), [])

    def test_new_writer_edges_cannot_be_admitted_by_filename_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            code = root / "code"
            code.mkdir()
            path = code / "helper.py"
            path.write_text("print('original fixture')\n", encoding="utf-8")
            contracts = {"governed.csv": {"rebuilt_by": ["approved.py"]}}
            baseline = {"scripts": [{"script": "helper.py", "dir": "", "writer_evidence": []}]}
            self.assertEqual(
                self.inventory.writer_admission_problems(root, baseline, contracts), []
            )
            path.write_text("open('governed.csv', 'w').write('fixture')\n", encoding="utf-8")
            issues = self.inventory.writer_admission_problems(root, baseline, contracts)
            self.assertEqual(len(issues), 1)
            self.assertIn("NEW_UNREGISTERED_WRITE", issues[0])
            self.assertIn("governed.csv", issues[0])
            baseline["scripts"][0].pop("writer_evidence")
            self.assertIn(
                "WRITER_BASELINE_MISSING",
                self.inventory.writer_admission_problems(root, baseline, contracts)[0],
            )

    def test_writer_ratchet_detects_retargeted_binding_and_exposes_existing_risk(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            code = root / "code"
            code.mkdir()
            path = code / "helper.py"
            source = (
                "from pathlib import Path\n"
                "OUT = Path('data/clean') / %r\nOUT.write_text('fixture')\n"
            )
            path.write_text(source % "first.csv", encoding="utf-8")
            contracts = {"first.csv": {"rebuilt_by": []}, "second.csv": {"rebuilt_by": []}}
            evidence = self.inventory.writer_evidence(path, contracts)
            baseline = {
                "scripts": [{"script": "helper.py", "dir": "", "writer_evidence": evidence}]
            }
            self.assertEqual(
                self.inventory.writer_admission_problems(root, baseline, contracts), []
            )
            path.write_text(source % "second.csv", encoding="utf-8")
            self.assertIn(
                "second.csv", self.inventory.writer_admission_problems(root, baseline, contracts)[0]
            )
            contracts["second.csv"]["rebuilt_by"] = ["helper.py"]
            self.assertEqual(
                self.inventory.writer_admission_problems(root, baseline, contracts), []
            )

    def test_unresolved_writer_context_changes_require_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            code = root / "code"
            code.mkdir()
            path = code / "helper.py"
            source = "def write(target):\n    target.write_text('fixture')\nwrite(%r)\n"
            path.write_text(source % "first.csv", encoding="utf-8")
            evidence = self.inventory.writer_evidence(path, {})
            baseline = {
                "scripts": [{"script": "helper.py", "dir": "", "writer_evidence": evidence}]
            }
            path.write_text(source % "second.csv", encoding="utf-8")
            self.assertIn(
                "NEW_UNREGISTERED_WRITE",
                self.inventory.writer_admission_problems(root, baseline, {})[0],
            )

    def test_new_unknown_governed_paths_cannot_bypass_writer_ratchet(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            code = root / "code"
            code.mkdir()
            path = code / "helper.py"
            baseline = {"scripts": [{"script": "helper.py", "dir": "", "writer_evidence": []}]}
            for target in (
                "data/clean/new.csv",
                "public/new.csv",
                "dist/review/new.csv",
                "store/releases/new.csv",
                "store/snapshots/new.csv",
                "store/catalogs/new.json",
            ):
                with self.subTest(target=target):
                    path.write_text(f"open({target!r}, 'w').write('fixture')\n", encoding="utf-8")
                    issues = self.inventory.writer_admission_problems(root, baseline, {})
                    self.assertEqual(len(issues), 1)
                    self.assertIn("NEW_UNREGISTERED_WRITE", issues[0])
            contracts = {"approved.csv": {"rebuilt_by": ["helper.py"]}}
            path.write_text(
                "open('data/clean/approved.csv', 'w').write('fixture')\n", encoding="utf-8"
            )
            self.assertEqual(
                self.inventory.writer_admission_problems(root, baseline, contracts), []
            )
            path.write_text("open('public/approved.csv', 'w').write('fixture')\n", encoding="utf-8")
            self.assertIn(
                "NEW_UNREGISTERED_WRITE",
                self.inventory.writer_admission_problems(root, baseline, contracts)[0],
            )

    def test_roles_derive_from_declarations_and_test_structure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            code = root / "code"
            code.mkdir()
            bodies = {
                "fixture_builder.py": "def selftest():\n    return True\n",
                "oddly_named_checks.py": (
                    "import unittest\nclass Checks(unittest.TestCase):\n    pass\n"
                ),
                "unknown.py": "print('never executed')\n",
                "production_test.py": "def transform(value):\n    return value\n",
                "custom_harness_test.py": (
                    "def check(condition):\n    assert condition\ncheck(1 == 1)\n"
                ),
                "caller.py": "import fixture_builder\n",
            }
            for name, content in bodies.items():
                (code / name).write_text(content, encoding="utf-8")
            records = [{"script": name, "dir": "", "mentions": 0} for name in bodies]
            contracts = {
                "fixture.csv": {
                    "collection": "fixture",
                    "rebuilt_by": ["fixture_builder.py"],
                    "rebuild_command": "python code/build.py run fixture --execute",
                }
            }
            with (
                patch.object(self.inventory, "ROOT", root),
                patch.object(self.inventory, "CODE", code),
                patch.object(
                    self.inventory, "read_archive_candidates", return_value={"candidates": []}
                ),
            ):
                self.inventory.add_operational_roles(
                    records, list(code.glob("*.py")), contracts, {"fixture"}
                )
            by_name = {record["script"]: record for record in records}
            self.assertEqual(by_name["fixture_builder.py"]["operational_role"], "active producer")
            self.assertEqual(by_name["fixture_builder.py"]["embedded_test_functions"], 1)
            self.assertEqual(by_name["fixture_builder.py"]["static_consumers"], ["code/caller.py"])
            self.assertEqual(by_name["oddly_named_checks.py"]["operational_role"], "test/fixture")
            self.assertEqual(by_name["unknown.py"]["operational_role"], "unresolved")
            self.assertEqual(by_name["production_test.py"]["operational_role"], "unresolved")
            self.assertEqual(by_name["custom_harness_test.py"]["operational_role"], "test/fixture")
            self.assertEqual(
                by_name["custom_harness_test.py"]["standalone_test_evidence"][
                    "local_check_harness_calls"
                ],
                ["check"],
            )

    def test_runtime_discovery_proves_local_loader_and_authoritative_chain(self):
        import ast
        tree = ast.parse("""
import importlib.util
SHIP_CHAIN = [("ship.py", [], "description.py", "")]
POST_CHAIN = ("post.py", "post stage", "")
def load_module(path):
    spec = importlib.util.spec_from_file_location("loaded", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
def pretend_loader(path):
    return path
load_module(ROOT / "actual.py")
pretend_loader("not_executed.py")
""")
        ordinary = self.inventory._runtime_script_references(tree)
        self.assertIn("actual.py", ordinary)
        for absent in ("ship.py", "post.py", "description.py", "not_executed.py"):
            self.assertNotIn(absent, ordinary)
        authoritative = self.inventory._runtime_script_references(tree, authoritative_runner=True)
        self.assertTrue({"actual.py", "ship.py", "post.py"} <= authoritative)
        self.assertNotIn("description.py", authoritative)

    def test_runtime_roles_require_executable_edges_and_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            code = root / "code"
            code.mkdir()
            bodies = {
                "test_only.py": "import cedar_publication as pub\npub.apply_field_map([])\n",
                "literal_only.py": "def check():\n    return True\ncheck()\n",
                "comment_only.py": "# cedar_publication\nprint('fixture')\n",
                "filename_audit.py": "print('fixture')\n",
                "real_validation.py": "def validate_rows():\n    return True\nvalidate_rows()\n",
                "real_product.py": (
                    "from cedar_publication import apply_field_map\napply_field_map([])\n"
                ),
                "scope_only.py": "import cedar_publication as pub\npub.shelves()\n",
                "caller.py": (
                    "import comment_only, filename_audit, scope_only\n"
                    "note = 'literal_only.py'\n"
                    "import subprocess, importlib.util\n"
                    "subprocess.run(['python', 'real_validation.py'], stderr='literal_only.py')\n"
                    "importlib.util.spec_from_file_location('product', 'real_product.py')\n"
                ),
                "caller_test.py": "import test_only\n",
            }
            for name, content in bodies.items():
                (code / name).write_text(content, encoding="utf-8")
            records = [{"script": name, "dir": "", "mentions": 0} for name in bodies]
            with (
                patch.object(self.inventory, "ROOT", root),
                patch.object(self.inventory, "CODE", code),
                patch.object(
                    self.inventory, "read_archive_candidates", return_value={"candidates": []}
                ),
            ):
                self.inventory.add_operational_roles(records, list(code.glob("*.py")), {}, set())
            by_name = {record["script"]: record for record in records}
            for name in (
                "test_only.py",
                "literal_only.py",
                "comment_only.py",
                "filename_audit.py",
                "scope_only.py",
            ):
                with self.subTest(name=name):
                    self.assertEqual(by_name[name]["operational_role"], "unresolved")
            self.assertEqual(by_name["test_only.py"]["static_consumers"], ["code/caller_test.py"])
            self.assertEqual(by_name["test_only.py"]["runtime_consumer_candidates"], [])
            self.assertEqual(by_name["literal_only.py"]["static_consumers"], ["code/caller.py"])
            self.assertEqual(by_name["literal_only.py"]["runtime_consumer_candidates"], [])
            self.assertEqual(
                by_name["real_validation.py"]["operational_role"],
                "active validator/migration/review",
            )
            self.assertEqual(
                by_name["real_product.py"]["operational_role"], "product consumer/shared service"
            )
            self.assertEqual(
                by_name["real_product.py"]["runtime_consumer_candidates"], ["code/caller.py"]
            )

    def test_maintenance_classification_requires_evidence_and_never_authorizes_removal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "code/history").mkdir(parents=True)
            (root / ".github/workflows").mkdir(parents=True)
            bodies = {"main.py": "import helper\n", "helper.py": "VALUE = 1\n",
                      "copy_a.py": "VALUE = 2\n", "copy_b.py": "VALUE = 2\n",
                      "unknown.py": "VALUE = 3\n", "history/old.py": "VALUE = 4\n",
                      "ci.py": "VALUE = 5\n", "old_writer.py": "VALUE = 6\n"}
            records = []
            for relative, body in bodies.items():
                path = root / "code" / relative
                path.write_text(body, encoding="utf-8")
                role = "active producer" if relative == "main.py" else (
                    "historical" if relative.startswith("history/") else "unresolved")
                records.append({"script": path.name, "dir": "history" if "/" in relative else "",
                                "operational_role": role,
                                "runtime_consumer_candidates": ["code/main.py"] if relative == "helper.py" else [],
                                "writer_evidence": [], "unknown_io_literals": []})
            workflow = root / ".github/workflows/test.yml"
            workflow.write_text("run: python code/ci.py\n", encoding="utf-8")
            records[-1]["writer_evidence"] = [{"table": "retired.csv"}]
            retirement = [{"file": "retired.csv", "rebuild": "main.py", "enricher": "helper.py",
                           "retired_writers": ["old_writer.py"]}]
            with (patch.object(self.inventory, "ROOT", root),
                  patch.object(self.inventory.cp, "KNOWN_ORDERINGS", retirement)):
                self.inventory.add_maintenance_classification(records, [workflow])
                by_name = {r["script"]: r for r in records}
                expected = {"main.py": "ACTIVE", "helper.py": "ACTIVE", "ci.py": "ACTIVE",
                            "copy_a.py": "DUPLICATE", "old.py": "HISTORICAL-RETAIN",
                            "unknown.py": "REQUIRES-REVIEW", "old_writer.py": "SUPERSEDED"}
                for name, status in expected.items():
                    self.assertEqual(by_name[name]["maintenance_status"], status, name)
                before = by_name["unknown.py"]["source_sha256"]
                (root / "code/unknown.py").write_text("VALUE = 30\n", encoding="utf-8")
                records[-1]["writer_evidence"].append({"table": None, "target": "<unresolved>"})
                self.inventory.add_maintenance_classification(records, [workflow])
                self.assertEqual(by_name["old_writer.py"]["maintenance_status"], "REQUIRES-REVIEW")
                self.assertEqual(by_name["old_writer.py"]["maintenance_evidence"]["review_owner"], "Codex")
                self.assertIn("<unresolved>", by_name["old_writer.py"]["maintenance_evidence"]["reason"])
                self.assertEqual(by_name["old_writer.py"]["maintenance_evidence"]["review_write_sites"][-1]["target"], "<unresolved>")
                self.assertFalse(any(r["maintenance_status"] == "SAFE-DELETE-CANDIDATE" for r in records))
                self.assertNotEqual(by_name["unknown.py"]["source_sha256"], before)
                self.assertTrue(all(not r["maintenance_evidence"]["retirement_authorized"] for r in records))
                replay = {"spine.csv": {"order": ["unknown.py"], "mints": ["unknown.py"],
                                        "evidence": "issued-ID restore history"}}
                with patch.object(self.inventory.cp, "REPLAY_ORDERS", replay):
                    self.inventory.add_maintenance_classification(records, [workflow])
                self.assertEqual(by_name["unknown.py"]["maintenance_status"], "HISTORICAL-RETAIN")
                self.assertTrue(by_name["unknown.py"]["maintenance_evidence"]["historical_replay_evidence"][0]["mints_issued_ids"])


    def test_script_refresh_preserves_prior_table_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "inventory.json"
            before = {"generated": "2026-09-02", "tables": [{"table": "kept.csv", "rows": 7}]}
            target.write_text(json.dumps(before), encoding="utf-8")
            with (
                patch.object(self.inventory, "OUT_JSON", target),
                patch.object(self.inventory.subprocess, "check_output", return_value=b""),
                patch.object(self.inventory, "inventory_scripts", return_value=([], {})),
                patch.object(self.inventory, "add_operational_roles"),
                patch.object(self.inventory, "read_contracts", return_value=({}, {})),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(self.inventory.refresh_script_census(), 0)
            after = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(after["tables"], before["tables"])
            self.assertEqual(after["generated"], before["generated"])
            self.assertEqual(after["script_census"]["data_generated_unchanged"], "2026-09-02")


if __name__ == "__main__":
    unittest.main()
