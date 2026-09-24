"""Data-less checks of producer admission through the existing runner contract."""

import argparse
import contextlib
import copy
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "pipeline_registration", ROOT / "code/cedar_pipeline.py"
)
PIPELINE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PIPELINE)


class ProducerRegistrationTest(unittest.TestCase):
    def test_release_projection_cannot_fill_or_reassign_entity_links(self):
        spec = importlib.util.spec_from_file_location("conserved_build", ROOT / "code/build.py")
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        original = [{"record": "one", "cedar_uid": ""}, {"record": "two", "cedar_uid": "existing"}]
        runner.assert_pilot_conservation(original, list(reversed(original)), ["record"])
        for records in (
            [{"record": "one", "cedar_uid": "new"}, original[1]],
            [original[0], {"record": "two", "cedar_uid": "other"}],
            original[:1],
        ):
            with self.subTest(records=records), self.assertRaises(ValueError):
                runner.assert_pilot_conservation(original, records, ["record"])

    def test_release_projection_refuses_lossy_source_csv(self):
        spec = importlib.util.spec_from_file_location("source_build", ROOT / "code/build.py")
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        for source in (
            b"id,note,note\n1,first,second\n",
            b"id,note\n1,a,extra\n",
            b"id,note\n1\n",
            b"id,\n1,a\n",
            b"id, note\n1,a\n",
        ):
            with self.subTest(source=source), self.assertRaises(ValueError):
                runner.pilot_source_rows(source)
        self.assertEqual(
            runner.pilot_source_rows(b'id,note\n1,"first\nsecond"\n'),
            [{"id": "1", "note": "first\nsecond"}],
        )

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
