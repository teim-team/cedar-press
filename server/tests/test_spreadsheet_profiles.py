"""Current producer profiles keep source observation grains and rights scope."""

import unittest
from unittest.mock import patch

from cedar_press.collection_profiles import _spreadsheet_construction, profile_for


class SpreadsheetProfileTest(unittest.TestCase):
    def test_current_contractors_profile_does_not_claim_one_entity_per_row(self):
        with patch(
            "cedar_press.collection_profiles.collection_tables",
            return_value=({"record_types": {"prime_contracts": 12}},),
        ):
            result = profile_for("contractors")
        self.assertIn("record_grain", result["unit_of_observation"])
        self.assertIn("prime_contracts: 12", result["unit_of_observation"])
        self.assertNotIn("One Native-owned contracting entity", result["unit_of_observation"])
        self.assertIn(
            "current affiliation does not establish ownership", result["entity_resolution_method"]
        )
        self.assertIn("not unique entities", result["known_limitations"])

    def test_owned_listing_and_certifier_are_not_business_identity(self):
        with patch(
            "cedar_press.collection_profiles.collection_tables",
            return_value=({"record_types": {"records": 3}},),
        ):
            result = _spreadsheet_construction("owned")
        self.assertIn("certification or directory listing", result["unit_of_observation"])
        self.assertIn("certifying authority is not", result["known_limitations"])
        self.assertNotIn("White Earth", result["known_limitations"])

    def test_need_scope_is_explicit_and_other_components_are_rejected(self):
        with patch(
            "cedar_press.collection_profiles.collection_tables",
            return_value=({"record_types": {"reviewed_public_base": 27}},),
        ):
            result = _spreadsheet_construction("need")
        self.assertIn("reviewed_public_base: 27", result["unit_of_observation"])
        self.assertIn(
            "Only the evidence-pinned reviewed base is public", result["known_limitations"]
        )
        with (
            patch(
                "cedar_press.collection_profiles.collection_tables",
                return_value=({"record_types": {"enterprises": 5820}},),
            ),
            self.assertRaisesRegex(ValueError, "only the reviewed public base"),
        ):
            _spreadsheet_construction("need")

    def test_missing_producer_metadata_preserves_legacy_profile_path(self):
        with patch("cedar_press.collection_profiles.collection_tables", return_value=()):
            self.assertIsNone(_spreadsheet_construction("funding"))

    def test_invalid_count_cannot_be_reported_as_an_observation_count(self):
        for count in (True, -1, "12"):
            with (
                self.subTest(count=count),
                patch(
                    "cedar_press.collection_profiles.collection_tables",
                    return_value=({"record_types": {"records": count}},),
                ),
                self.assertRaisesRegex(ValueError, "record-type count"),
            ):
                _spreadsheet_construction("funding")

    def test_giving_and_plot_profiles_preserve_component_claim_limits(self):
        for collection, kinds, phrases in (
            (
                "foundation-corporate-giving",
                {"policy_eligible_disclosures": 155, "reviewed_disclosures": 38},
                (
                    "not necessarily a distinct award or payment",
                    "unpaid balances",
                    "intermediary or program",
                ),
            ),
            (
                "plot",
                {"tract_observations": 20, "permit_events": 4},
                (
                    "tract can contain several parcels",
                    "not title certification",
                    "not unique projects",
                ),
            ),
        ):
            with (
                self.subTest(collection=collection),
                patch(
                    "cedar_press.collection_profiles.collection_tables",
                    return_value=({"record_types": kinds},),
                ),
            ):
                result = _spreadsheet_construction(collection)
            for phrase in phrases:
                self.assertIn(phrase, result["known_limitations"])
