"""Superseded Cedar Gaming writers are fenced, not deleted; input producers stay live.

Repository split 2026-09-24: Lumecon-data builds, validates and releases Cedar
Grove Gaming. The Cedar scripts in `cedar_pipeline.GAMING_SUPERSEDED_BY_LUMECON`
wrote Gaming tables that job now belongs to (or, for 588, duplicated the
maintained writer). This proves, for each one, that

* it is in `NEVER_RUN`, so the supported runner refuses it as FORBIDDEN_PRODUCER;
* its FIRST statement after the docstring is the guard, so nothing runs before it;
* run directly, in an isolated copy, it exits non-zero with REFUSED and creates,
  changes or deletes no file;

and that no Cedar script whose output Lumecon still reads was fenced.
"""

import ast
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "gaming_fence_pipeline", ROOT / "code/cedar_pipeline.py"
)
PIPELINE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PIPELINE)

# Writers of Cedar tables Lumecon-data's Gaming producers still read (pinned in
# its intake/profiles/gaming.json). They must stay runnable until Lumecon reads
# its own acquisition instead; the inventory is in
# docs/handoffs/GAMING_INTELLIGENCE_AUDIT_HANDOFF_2026-09-24.md.
TRANSITIONAL_INPUT_PRODUCERS = (
    "23d_build_gaming_facilities.py", "143_build_gaming_property_locations.py",
    "23b_build_gaming_land_decisions.py", "15b_build_compact_index.py", "15e_finalize_terms.py",
    "95_parse_compact_terms.py", "32a_fetch_gaming_nepa_pilot.py", "32b_build_gaming_nepa_pilot.py",
    "84_build_nigc_regions.py", "106_build_revenue_bounds.py", "91_build_nigc_declinations.py",
    "100_finish_declinations_and_employment.py", "103_build_california_gaming.py",
    "105_build_florida_gaming.py", "107_pull_remaining_states.py", "104_build_wa_allocations.py",
    "119_build_digital_and_loyalty.py", "142_build_property_site_observations.py",
    "147_build_fac_single_audits.py", "148_build_gaming_vendor_tribal_licenses.py",
    "157_reconcile_nigc_roster.py", "158_merge_staged_labor_employment.py",
    "118_build_gaming_ordinances.py", "153_merge_ordinance_ocr.py",
    "88_gaming_property_federal_traces.py", "89_nigc_map_wayback_universe.py",
    "586_promote_nigc_gaming.py", "1094_merge_web_harvest_into_gaming_claims.py",
    "980_gaming_web_harvest.py", "1080_sec_gaming_facility_revenue.py", "1129_place_ids.py",
)


def _fence_ends_at(tree):
    """Index of the guard call among the module's top-level statements."""
    for index, node in enumerate(tree.body):
        if (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Attribute)
                and node.value.func.attr == "guard"):
            return index
    return None


class GamingWriterFenceTest(unittest.TestCase):
    def test_fenced_writers_are_never_run_and_exist(self):
        fenced = PIPELINE.GAMING_SUPERSEDED_BY_LUMECON
        self.assertGreaterEqual(len(fenced), 5)
        for name, reason in fenced.items():
            with self.subTest(script=name):
                self.assertTrue((ROOT / "code" / name).is_file())
                self.assertEqual(PIPELINE.NEVER_RUN[name], reason)
                self.assertIn("Lumecon", reason)
        # The pre-existing prohibition is untouched.
        self.assertIn("41_build_codebooks.py", PIPELINE.NEVER_RUN)

    def test_guard_is_the_first_thing_each_fenced_script_runs(self):
        for name in PIPELINE.GAMING_SUPERSEDED_BY_LUMECON:
            with self.subTest(script=name):
                tree = ast.parse((ROOT / "code" / name).read_text(encoding="utf-8"))
                index = _fence_ends_at(tree)
                self.assertIsNotNone(index)
                before = tree.body[1:index]  # after the docstring
                self.assertTrue(all(isinstance(n, (ast.Import, ast.ImportFrom, ast.Expr))
                                    for n in before), name)
                imported = {a.name for n in before if isinstance(n, (ast.Import, ast.ImportFrom))
                            for a in n.names}
                self.assertLessEqual(imported, {"sys", "Path", "cedar_pipeline"}, name)

    def test_direct_run_refuses_before_any_read_or_write(self):
        for name in PIPELINE.GAMING_SUPERSEDED_BY_LUMECON:
            with self.subTest(script=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "code").mkdir()
                (root / "data/clean").mkdir(parents=True)
                sentinel = root / "data/clean/gaming_properties.csv"
                sentinel.write_text("facility_id\nsentinel\n", encoding="utf-8")
                for source in ("cedar_pipeline.py", name):
                    (root / "code" / source).write_bytes((ROOT / "code" / source).read_bytes())
                before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
                run = subprocess.run(
                    [sys.executable, "-B", str(root / "code" / name)],
                    cwd=root, capture_output=True, text=True, timeout=60,
                )
                self.assertNotEqual(run.returncode, 0)
                self.assertIn("REFUSED: " + name, run.stderr)
                self.assertIn("ForbiddenScript", run.stderr)
                after = {p: p.read_bytes() for p in root.rglob("*")
                         if p.is_file() and "__pycache__" not in p.parts}
                self.assertEqual(after, before)

    def test_supported_runner_refuses_each_fenced_writer(self):
        for name in PIPELINE.GAMING_SUPERSEDED_BY_LUMECON:
            with self.subTest(script=name):
                plan = {"id": "gaming", "phase1": [name], "phase2": [],
                        "rb": {name: ["gaming_properties.csv"]}, "en": {}}
                contracts = {"contracts": [{
                    "collection": "gaming",
                    "rebuild_command": "py -3 code/build.py run gaming --execute",
                    "tables": [{"table": "gaming_properties.csv", "rebuilt_by": [name]}],
                }]}
                self.assertIn("FORBIDDEN_PRODUCER: " + name,
                              PIPELINE.registration_problems(plan, contracts))
                with self.assertRaises(PIPELINE.ForbiddenScript):
                    PIPELINE.guard(name)

    def test_transitional_input_producers_stay_runnable(self):
        for name in TRANSITIONAL_INPUT_PRODUCERS:
            with self.subTest(script=name):
                self.assertTrue((ROOT / "code" / name).is_file(), name)
                self.assertNotIn(name, PIPELINE.NEVER_RUN)
                self.assertTrue(PIPELINE.guard(name))
                tree = ast.parse((ROOT / "code" / name).read_text(encoding="utf-8"))
                self.assertIsNone(_fence_ends_at(tree), name)


if __name__ == "__main__":
    unittest.main()
