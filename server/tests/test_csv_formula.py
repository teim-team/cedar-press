"""Every CSV the API writes neutralizes a cell a spreadsheet would run.

The cases are shared with the client's suite
(``csvFormula.test.js``), so the server and the browser
cannot drift into two rules: the same table is enforced on both sides.
"""

from __future__ import annotations

import csv
import io
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cedar_press import collections as launch  # noqa: E402
from cedar_press import csv_safety, spreadsheet  # noqa: E402

CASES = json.loads(
    (Path(__file__).with_name("fixtures") / "csv_formula_cases.json").read_text("utf-8")
)["cases"]


def expected(case: dict) -> str:
    return ("'" if case["neutralized"] else "") + case["value"]


def parsed(cell: str) -> str:
    """What a CSV reader gets back for one written cell."""
    return next(csv.reader(io.StringIO(cell, newline="")))[0] if cell else ""


class TestCsvFormulaNeutralization(unittest.TestCase):
    def test_the_shared_rule(self) -> None:
        for case in CASES:
            with self.subTest(value=case["value"]):
                self.assertEqual(csv_safety.spreadsheet_safe(case["value"]), expected(case))

    def test_the_preview_download_applies_it(self) -> None:
        for case in CASES:
            with self.subTest(value=case["value"]):
                self.assertEqual(parsed(launch._csv_cell(case["value"])), expected(case))

    def test_the_full_spreadsheet_download_applies_it(self) -> None:
        for case in CASES:
            with self.subTest(value=case["value"]):
                self.assertEqual(spreadsheet._cell(case["value"]), expected(case))

    def test_numbers_that_are_not_text_are_left_alone(self) -> None:
        # A typed number cannot be a formula, whatever its string form looks
        # like, and an apostrophe would turn it into text.
        self.assertEqual(spreadsheet._cell(-1e-05), "-1e-05")
        self.assertEqual(spreadsheet._cell(-7), "-7")


if __name__ == "__main__":
    unittest.main()
