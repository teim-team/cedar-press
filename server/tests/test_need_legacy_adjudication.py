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


class RowBoundChugachAdjudicationTest(unittest.TestCase):
    """The two rows the Chugach ruling was written for keep it (restored 2026-10-04)."""

    @classmethod
    def setUpClass(cls):
        path = Path(__file__).parents[2] / "code/1102_need_corroboration_adjudication.py"
        spec = importlib.util.spec_from_file_location("need_evidence_enricher_bound", path)
        cls.producer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.producer)

    def blanket(self, enterprise_id, name, owner="Chugach Alaska Corporation"):
        return {
            "enterprise_id": enterprise_id, "enterprise_name": name,
            "owner_hub_name": owner, "published_value": "holding_company",
            "adjudicated_by": "code/1102_need_corroboration_adjudication.py",
            "adjudicated_date": "2026-09-23",
            "adjudication": "UPHELD, and now on two of three sources; "
                            "www.chugach.com/business/directory",
            "third_source": "ANC_TRIBE_LOOKUP",
            "third_source_says": "lists Chugach Commercial Holdings (CCH)",
        }

    def test_bound_rows_carry_the_row_specific_decision(self):
        for eid, name in (("CEDAR-NEST-000473-WH", "Chugach Government Solutions, LLC"),
                          ("CEDAR-NEST-000479-07", "Chugach Regional Development, LLC")):
            result = self.producer.clear_unbound_conflict_adjudication(self.blanket(eid, name))
            self.assertIn("published value `holding_company` stands", result["adjudication"])
            self.assertIn("NEED_BUILD_LOG", result["adjudication"])
            self.assertEqual(result["adjudication_hold_reason"], "")
            self.assertEqual(result["published_value"], "holding_company")
            # Restored even where a previous run already cleared the copy.
            cleared = dict(result, adjudication="", adjudicated_by="", adjudicated_date="")
            again = self.producer.clear_unbound_conflict_adjudication(cleared)
            self.assertEqual(again["adjudication"], self.producer.ROW_BOUND_TEXT)

    def test_copies_on_other_rows_stay_cleared(self):
        for eid, name in (("CEDAR-NEST-000049-BS", "Ahtna Builders, LLC"),
                          ("CEDAR-NEST-000473-WH", "Ahtna Builders, LLC"),
                          ("CEDAR-NEST-000999-XX", "Chugach Government Solutions, LLC")):
            result = self.producer.clear_unbound_conflict_adjudication(self.blanket(eid, name))
            self.assertEqual(result["adjudication"], "")
            self.assertIn("unadjudicated", result["adjudication_hold_reason"])
