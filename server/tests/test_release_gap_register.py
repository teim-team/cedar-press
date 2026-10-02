"""The consumer-side release-gap register stays derived from the tracked files.

``release_gap_register.build()`` measures the manifest, receipts, contracts,
spine, legacy extracts, fixtures, register and census and renders the rows;
the committed JSON and Markdown must equal that rendering, so a count in
either file is always the repository's, never a typed one. The shape rules
below are what make a row usable: one classification from the vocabulary,
an owner and exactly one question on a DECISION row, a named file and command
on an EVIDENCE_NEEDED row.
"""

from __future__ import annotations

import json
import unittest

from tests import release_gap_register as reg

REGISTER = reg.build()


class RegisterIsCurrent(unittest.TestCase):
    def test_committed_json_and_markdown_equal_the_measurement(self) -> None:
        self.assertEqual(reg.OUT_JSON.read_text(encoding="utf-8"), reg.render_json(REGISTER))
        self.assertEqual(reg.OUT_MD.read_text(encoding="utf-8"), reg.render_markdown(REGISTER))

    def test_markdown_names_every_row_and_every_decision(self) -> None:
        md = reg.OUT_MD.read_text(encoding="utf-8")
        for row in REGISTER["rows"]:
            self.assertIn(f"### {row['id']}: ", md)
            if row.get("question"):
                self.assertIn(row["question"], md)


class RowShape(unittest.TestCase):
    def test_ids_are_unique_and_sequential(self) -> None:
        ids = [r["id"] for r in REGISTER["rows"]]
        self.assertEqual(ids, [f"GAP-{n:02d}" for n in range(1, len(ids) + 1)])

    def test_every_row_has_a_known_classification_and_the_required_fields(self) -> None:
        for row in REGISTER["rows"]:
            self.assertIn(row["classification"], reg.CLASSES, row["id"])
            for key in (
                "collection",
                "gate",
                "exists",
                "served",
                "gate_location",
                "closing_condition",
                "evidence",
            ):
                self.assertTrue(str(row.get(key, "")).strip(), (row["id"], key))

    def test_decision_rows_name_an_owner_and_one_question(self) -> None:
        for row in REGISTER["rows"]:
            if row["classification"] == "DECISION":
                self.assertIn(row["owner"], reg.OWNERS.values(), row["id"])
                self.assertTrue(row["question"].endswith("?"), row["id"])
                self.assertEqual(row["question"].count("?"), 1, row["id"])
            elif row.get("question"):
                # A question on any other row still names who answers it.
                self.assertIn(row["owner"], reg.OWNERS.values(), row["id"])
                self.assertEqual(row["question"].count("?"), 1, row["id"])

    def test_evidence_needed_rows_name_the_file_and_the_command(self) -> None:
        for row in REGISTER["rows"]:
            if row["classification"] == "EVIDENCE_NEEDED":
                needs = row.get("needs", "")
                self.assertTrue(needs, row["id"])
                self.assertTrue(
                    "`" in needs
                    or "data/clean" in needs
                    or "Lumecon-data" in needs
                    or "review/" in needs,
                    row["id"],
                )

    def test_measured_numbers_are_the_repositorys(self) -> None:
        m = REGISTER["measured"]
        manifest = json.loads(
            (reg.ROOT / "data/cedar/collections.manifest.json").read_text(encoding="utf-8")
        )
        for c in manifest["collections"]:
            self.assertEqual(m["served"][c["id"]]["n_rows"], c["cedar"]["n_rows"])
        register = json.loads(
            (reg.ROOT / "public/data/cedar/register.json").read_text(encoding="utf-8")
        )
        self.assertEqual(m["withheld"]["total"], register["withheld_names"])
        self.assertEqual(sum(m["withheld"]["by_class"].values()), register["withheld_names"])
        self.assertEqual(m["cev"]["in_served_sample"], [])
        self.assertEqual(m["overrides"]["live_keys"], [])
        self.assertEqual(m["overrides"]["retired"], 27)
        self.assertEqual(m["overrides"]["lobbying_superseded_by"], "superseded_by_record_id")
        self.assertEqual(
            m["graph"]["in_code_archive"], len(list((reg.ROOT / "code/archive").glob("*.py")))
        )


if __name__ == "__main__":
    unittest.main()
