"""The consumer-side reference graph and the archive rule it enforces.

The full measurement (``code_reference_graph.measure``) scans every tracked
text file for every numbered script and takes about forty seconds, so the
committed JSON is not re-derived whole here. Instead these tests prove the
properties the archive move relied on against the live tree: every script
under ``code/archive/`` still has zero references of any kind, is named in the
index, is in the census as historical, and the committed graph is internally
consistent (the rule's eligible set equals the archived set). Rerun
``python3 server/tests/code_reference_graph.py --check`` to re-derive the
whole file.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from tests import code_reference_graph as graph

ROOT = graph.ROOT
ARCHIVE = ROOT / "code" / "archive"


def committed() -> dict:
    return json.loads(graph.OUT.read_text(encoding="utf-8"))


class ReferenceGraphShape(unittest.TestCase):
    def test_every_numbered_script_in_the_tree_is_in_the_graph(self) -> None:
        tracked = graph.tracked_files()
        expected = {name for _, name in graph.numbered_scripts(tracked)}
        self.assertEqual(set(committed()["scripts"]), expected)
        self.assertEqual(len(expected), committed()["summary"]["numbered_scripts"])

    def test_summary_counts_are_derived_from_the_rows(self) -> None:
        g = committed()
        rows = g["scripts"].values()
        summary = g["summary"]
        self.assertEqual(summary["referenced"], sum(1 for s in rows if s["reference_count"]))
        self.assertEqual(
            summary["zero_references"], sum(1 for s in rows if not s["reference_count"])
        )
        self.assertEqual(
            summary["in_code_archive"], sum(1 for s in rows if "/archive/" in s["location"])
        )
        self.assertEqual(
            summary["at_code_top_level"] + summary["in_code_archive"], summary["numbered_scripts"]
        )
        self.assertEqual(
            summary["pure_numeric_prefix"] + summary["letter_suffixed_prefix"],
            summary["numbered_scripts"],
        )
        for s in rows:
            self.assertEqual(s["reference_count"], sum(len(v) for v in s["references"].values()))

    def test_archive_rule_set_equals_the_archived_set(self) -> None:
        g = committed()
        archived = {
            name for name, s in g["scripts"].items() if s["disposition"].startswith("archived_")
        }
        self.assertEqual(set(g["summary"]["archive_eligible_by_rule"]), archived)
        self.assertEqual(set(g["summary"]["archived"]), archived)
        for name in archived:
            s = g["scripts"][name]
            self.assertEqual(s["reference_count"], 0, name)
            self.assertEqual(s["tracked_artifacts_written"], [], name)
            self.assertNotEqual(s["census"]["maintenance_status"], "ACTIVE", name)
            self.assertFalse(s["census"]["never_run"], name)
            self.assertFalse(s["census"]["in_a_contract"], name)
            self.assertFalse(s["census"]["in_an_ordering"], name)
        # A referenced script is never archived; an unreferenced one that
        # writes a tracked artifact is kept where it is.
        for name, s in g["scripts"].items():
            if s["reference_count"]:
                self.assertEqual(s["disposition"], "referenced", name)


class ArchivedScriptsAgainstTheLiveTree(unittest.TestCase):
    def test_archive_directory_matches_graph_index_and_census(self) -> None:
        on_disk = {p.name for p in ARCHIVE.glob("*.py")}
        g = committed()
        self.assertEqual(on_disk, set(g["summary"]["archived"]))
        index = (ARCHIVE / "INDEX.md").read_text(encoding="utf-8")
        for name in on_disk:
            self.assertIn(f"`{name}`", index, name)
            self.assertEqual(g["scripts"][name]["location"], f"code/archive/{name}")
        census = json.loads((ROOT / "docs/schema/inventory.json").read_text(encoding="utf-8"))
        rows = {s["script"]: s for s in census["scripts"] if s["dir"] == "archive"}
        self.assertEqual(set(rows), on_disk)
        for name, row in rows.items():
            self.assertEqual(row["maintenance_status"], "HISTORICAL-RETAIN", name)
            self.assertEqual(row["mentions"], 0, name)

    def test_every_archived_script_still_has_zero_references_in_the_tree(self) -> None:
        tracked = graph.tracked_files()
        texts = graph.read_texts(tracked)
        numbers_named = {
            path: graph.number_tokens(text)
            for path, text in texts.items()
            if path.startswith(("code/", "server/", "scripts/"))
        }
        for path in sorted(ARCHIVE.glob("*.py")):
            stem = path.name[:-3]
            number, rest = graph.NUMBERED.match(path.name).groups()
            hits = []
            for text_path, text in texts.items():
                if Path(text_path).name == path.name:
                    continue
                if (
                    stem in text
                    or (len(rest) >= 10 and rest in text)
                    or number in numbers_named.get(text_path, ())
                ):
                    hits.append(text_path)
            self.assertEqual(hits, [], path.name)

    def test_no_archived_script_is_guarded_planned_or_ordered(self) -> None:
        import importlib.util
        import sys

        sys.path.insert(0, str(ROOT / "code"))
        spec = importlib.util.spec_from_file_location(
            "cedar_pipeline", ROOT / "code/cedar_pipeline.py"
        )
        pipeline = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pipeline)
        names = {p.name for p in ARCHIVE.glob("*.py")}
        self.assertEqual(names & set(pipeline.NEVER_RUN), set())
        ordered = {o["rebuild"] for o in pipeline.all_orderings()} | {
            o["enricher"] for o in pipeline.all_orderings()
        }
        self.assertEqual(names & ordered, set())


class LoaderShapes(unittest.TestCase):
    def test_number_tokens_catch_the_loader_and_documentary_forms(self) -> None:
        text = (
            'fact = _script("1185", "deals_fact_check_2025_2026")\n'
            "# see code/566 (the three extracts) and code/567\n"
            'OUT = "563_probe.json"\n'
            "run 24_generate_dataset_docs then 1128_cicd\n"
            "a number alone: 999 and a path code/9990_other\n"
        )
        tokens = graph.number_tokens(text)
        self.assertTrue({"1185", "566", "567", "563", "24", "1128", "9990"} <= tokens)
        self.assertNotIn("999", tokens)

    def test_stem_only_reference_counts_as_a_reference(self) -> None:
        g = committed()
        row = g["scripts"]["1185_deals_fact_check_2025_2026.py"]
        self.assertIn("code/cedar_publication.py", row["references"].get("stem_only", []))
        self.assertEqual(row["disposition"], "referenced")

    def test_catalogues_that_name_every_script_are_not_references(self) -> None:
        for path in (
            "docs/CODE_REFERENCE_GRAPH_2026-10-02.json",
            "code/archive/INDEX.md",
            "server/tests/test_code_reference_graph.py",
            "docs/schema/inventory.json",
            "docs/schema/tables/anything.json",
            "docs/ARCHITECTURE.md",
            "docs/ARCHIVE_CANDIDATES.md",
            "docs/RELEASE_GAP_2026-10-02.md",
        ):
            self.assertTrue(graph.is_catalogue(path), path)
        for path in ("docs/REVIEW_STATUS.md", "Makefile", "code/cedar_publication.py", "AGENTS.md"):
            self.assertFalse(graph.is_catalogue(path), path)

    def test_reference_kinds_cover_every_kind_the_graph_records(self) -> None:
        g = committed()
        used = {k for s in g["scripts"].values() for k in s["references"]}
        self.assertTrue(used <= set(graph.REFERENCE_KINDS), used - set(graph.REFERENCE_KINDS))
        self.assertEqual(graph.reference_kind(".github/workflows/ci.yml"), "ci")
        self.assertEqual(graph.reference_kind("AGENTS.md"), "journal")
        self.assertEqual(graph.reference_kind("review/OWNER_DECISION_QUEUE.md"), "documented")
        self.assertEqual(graph.reference_kind("data/cedar/field_map.json"), "data_or_config")

    def test_numbered_scripts_include_the_archive_and_nothing_deeper(self) -> None:
        tracked = [
            "code/12_a.py",
            "code/107b_fill.py",
            "code/archive/590_x.py",
            "code/ancsa_v2/ocr_stats.py",
            "code/lobbying_pull/04_pull.py",
            "code/cedar_domain.py",
            "code/archive/INDEX.md",
        ]
        found = graph.numbered_scripts(tracked)
        self.assertEqual(
            found,
            [
                ("code/107b_fill.py", "107b_fill.py"),
                ("code/12_a.py", "12_a.py"),
                ("code/archive/590_x.py", "590_x.py"),
            ],
        )
        self.assertTrue(re.fullmatch(r"\d+[a-z]?", "107b"))


if __name__ == "__main__":
    unittest.main()
