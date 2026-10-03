"""Legacy discovery labels must never become primary Native-status rulings."""

import copy
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "legacy_nonprofit_disposition", ROOT / "code/952_nonprofit_disposition.py"
)
disposition = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(disposition)


class LegacyNonprofitDispositionTest(unittest.TestCase):
    def test_distinctive_name_and_high_confidence_do_not_establish_native_status(self):
        row = {
            "EIN": "232025143",
            "org_name": "LENAPE CHAMBER ENSEMBLE",
            "funnel_stage": "verified_strict",
            "classification_ruling": "UNRULED",
            "confidence_tier": "A",
            "canonical_name_token_match": "Lenape Indian Tribe of Delaware",
            "cedar_uid": "CE-PRESERVE-EXACT",
            "evidence": "survived place-name filter and v2 ambiguous-token strict filter",
        }
        before = copy.deepcopy(row)
        support, _ = disposition.support(row["org_name"], row["canonical_name_token_match"])
        self.assertEqual(support, "distinctive_token")
        status, reason = disposition.decide(row, support)
        self.assertEqual(status, "CANDIDATE_NAME_MATCH_UNVERIFIED")
        self.assertIn("Needs evidence review", reason)
        self.assertNotIn("EXCLUDED", status)
        self.assertEqual(row, before)

    def test_heuristic_strict_generic_and_unexplained_matches_stay_candidates(self):
        for support in ("generic_token_only", "no_shared_token_with_canonical_name"):
            with self.subTest(support=support):
                status, _ = disposition.decide(
                    {"funnel_stage": "verified_strict", "classification_ruling": "UNRULED"},
                    support,
                )
                self.assertTrue(status.startswith("CANDIDATE_"))
                self.assertNotIn("NATIVE_VERIFIED", status)

    def test_recorded_ruling_is_not_overturned_by_name_heuristics(self):
        status, _ = disposition.decide(
            {
                "funnel_stage": "ruled_native_verified",
                "classification_ruling": "tribally_controlled",
            },
            "generic_token_only",
        )
        self.assertEqual(status, "NATIVE_RULED_VERIFIED")
        status, _ = disposition.decide(
            {"funnel_stage": "ruled_native_needs_elijah"}, "no_shared_token_with_canonical_name"
        )
        self.assertEqual(status, "NATIVE_PROPOSED_AWAITING_OWNER_RULING")

    def test_prior_exclusion_and_contradictory_rulings_are_preserved(self):
        status, _ = disposition.decide(
            {"funnel_stage": "verified_strict", "excluded_by_prior_ruling": "1"},
            "distinctive_token",
        )
        self.assertEqual(status, "EXCLUDED_PRIOR_RULING")
        status, _ = disposition.decide(
            {"funnel_stage": "ruled_native_verified", "excluded_by_prior_ruling": "1"},
            "distinctive_token",
        )
        self.assertEqual(status, "CONFLICT_EXCLUDED_AND_RULED_NATIVE")


if __name__ == "__main__":
    unittest.main()
