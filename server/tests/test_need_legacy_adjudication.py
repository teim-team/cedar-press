"""No synthetic conflict may inherit a different enterprise's adjudication."""

import contextlib
import importlib.util
import io
import unittest
from pathlib import Path


class NeedConflictEvidenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).parents[2] / "code/1102_need_corroboration_adjudication.py"
        spec = importlib.util.spec_from_file_location("need_evidence_enricher", path)
        cls.producer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.producer)

    def test_actual_builder_does_not_copy_ruling_across_distinct_enterprises(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.producer.fixture_selftest(), 0)

    def test_recognized_blanket_claim_is_removed_without_replacing_evidence(self):
        for enterprise, owner in (
            ("Ahtna Builders, LLC", "Ahtna, Incorporated"),
            ("Chugach Commercial Holdings", "Chugach Alaska Corporation"),
        ):
            original = {
                "enterprise_id": "SYNTHETIC-" + enterprise,
                "enterprise_name": enterprise,
                "owner_hub_name": owner,
                "audited_filing_says": "subsidiary",
                "web_list_says": "operating_company",
                "published_value": "subsidiary",
                "adjudicated_by": "code/1102_need_corroboration_adjudication.py",
                "adjudicated_date": "2026-09-23",
                "adjudication": (
                    "UPHELD, and now on two of three sources; www.chugach.com/business/directory"
                ),
                "third_source": "ANC_TRIBE_LOOKUP",
                "third_source_says": "lists Chugach Commercial Holdings (CCH)",
            }
            result = self.producer.clear_unbound_conflict_adjudication(original)
            self.assertEqual(result["adjudication"], "")
            self.assertEqual(result["third_source_says"], "")
            self.assertEqual(result["published_value"], original["published_value"])
            self.assertEqual(result["enterprise_id"], original["enterprise_id"])
            self.assertEqual(result["audited_filing_says"], "subsidiary")
            self.assertIn("unadjudicated", result["adjudication_hold_reason"])
            self.assertTrue(original["adjudication"])
            self.assertEqual(self.producer.clear_unbound_conflict_adjudication(result), result)

    def test_independent_review_is_preserved(self):
        row = {
            "enterprise_id": "SYNTHETIC",
            "adjudicated_by": "independent-review",
            "adjudication": "Separate exact source statement",
            "published_value": "subsidiary",
        }
        self.assertEqual(self.producer.clear_unbound_conflict_adjudication(row), row)
