"""Fixture-only tests of the individually Native-owned firm publication rule.

Owner ruling, 2026-10-02 (Elijah Moreno): a firm is a business entity
regardless of what it is named after; its name, identifiers and business
address are public business records (SAM and USAspending publish exactly
these for every federal awardee), not personal identifying information, so
consent is not required. `cedar_domain.may_publish_individual_native_field`
therefore answers True for every field in INDIVIDUAL_NATIVE_WITHHELD_FIELDS
whatever `consent_status` and `firm_legal_name_is_person` say. Unchanged:
an unknown field still fails closed, `researcher_note` stays internal, and
small-cell suppression (an aggregate-statistics rule) is untouched.

Mutation check: restoring the pre-ruling consent gate in cedar_domain.py
(`return True` on OPTED_IN only) fails every case in
`EveryBusinessRecordFieldPublishes`. No file is read or written.

Run from the repository root: python3 code/cedar_domain_publication_test.py
"""
import importlib.util
import sys
import unittest
from pathlib import Path

CODE = Path(__file__).resolve().parent
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))


def load(name: str):
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), CODE / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


D = load("cedar_domain.py")
RULE = D.may_publish_individual_native_field

#: The fields the ruling released, named here so a quiet shrinking of the
#: set in cedar_domain.py fails this file rather than passing vacuously.
RELEASED = {
    "canonical_name", "legal_business_name", "awardee_name", "dba_name",
    "owner_name", "owner_tribal_affiliation_named",
    "street", "recipient_city_name", "place_of_perform_city",
    "self_description_sentence", "awardee_uei", "cage_code",
}


class EveryBusinessRecordFieldPublishes(unittest.TestCase):
    def test_the_released_set_is_the_whole_formerly_withheld_set(self):
        self.assertEqual(set(D.INDIVIDUAL_NATIVE_WITHHELD_FIELDS), RELEASED)

    def test_every_field_publishes_with_consent_not_asked(self):
        for field in sorted(D.INDIVIDUAL_NATIVE_WITHHELD_FIELDS):
            with self.subTest(field=field):
                self.assertTrue(RULE(field, consent_status="NOT_ASKED"))
                self.assertTrue(RULE(field))  # the default is NOT_ASKED

    def test_consent_status_never_changes_the_answer(self):
        for status in ("NOT_ASKED", "DECLINED", "WITHDRAWN", "OPTED_IN", "", None):
            for field in sorted(D.INDIVIDUAL_NATIVE_WITHHELD_FIELDS):
                with self.subTest(field=field, consent_status=status):
                    self.assertTrue(RULE(field, consent_status=status))

    def test_a_legal_name_that_is_a_persons_name_still_publishes_every_field(self):
        # The pre-ruling carve-out withheld the UEI and CAGE where this was
        # 1 or UNKNOWN. The ruling: the hop from a UEI resolves to a business
        # registration, not to a private individual.
        for person in ("1", "TRUE", "YES", "UNKNOWN", "", None, "0"):
            for field in ("awardee_uei", "cage_code", "street", "canonical_name", "owner_name"):
                with self.subTest(field=field, name_is_person=person):
                    self.assertTrue(RULE(field, name_is_person=person, consent_status="NOT_ASKED"))

    def test_no_carve_out_for_street(self):
        self.assertTrue(RULE("street", name_is_person="1", consent_status="NOT_ASKED"))
        self.assertTrue(RULE("street", name_is_person="UNKNOWN", consent_status="DECLINED"))

    def test_the_publishable_set_still_publishes(self):
        for field in sorted(D.INDIVIDUAL_NATIVE_PUBLISHABLE_FIELDS):
            with self.subTest(field=field):
                self.assertTrue(RULE(field))


class WhatStillFailsClosed(unittest.TestCase):
    def test_an_unknown_field_is_withheld(self):
        for field in ("", None, "bogus", "home_phone", "owner_ssn", "CANONICAL_NAME_"):
            with self.subTest(field=field):
                self.assertFalse(RULE(field))
                self.assertFalse(RULE(field, name_is_person="0", consent_status="OPTED_IN"))

    def test_researcher_note_is_internal_working_text(self):
        self.assertIn("researcher_note", D.INDIVIDUAL_NATIVE_INTERNAL_FIELDS)
        self.assertNotIn("researcher_note", D.INDIVIDUAL_NATIVE_WITHHELD_FIELDS)
        self.assertFalse(RULE("researcher_note"))
        self.assertFalse(RULE("researcher_note", consent_status="OPTED_IN"))

    def test_the_three_sets_do_not_overlap(self):
        self.assertFalse(D.INDIVIDUAL_NATIVE_PUBLISHABLE_FIELDS & D.INDIVIDUAL_NATIVE_WITHHELD_FIELDS)
        self.assertFalse(D.INDIVIDUAL_NATIVE_PUBLISHABLE_FIELDS & D.INDIVIDUAL_NATIVE_INTERNAL_FIELDS)
        self.assertFalse(D.INDIVIDUAL_NATIVE_WITHHELD_FIELDS & D.INDIVIDUAL_NATIVE_INTERNAL_FIELDS)

    def test_whitespace_around_a_known_field_is_tolerated_as_before(self):
        self.assertTrue(RULE("  canonical_name "))


class SmallCellSuppressionIsLifted(unittest.TestCase):
    """Owner ruling 2026-10-04: no cell of the class is suppressed."""

    def test_threshold_constant_is_kept_for_callers(self):
        self.assertEqual(D.INDIVIDUAL_NATIVE_MIN_CELL_FIRMS, 3)

    def test_no_cell_is_suppressed(self):
        for n in (0, 1, 2, "2", 3, "45", None, "", "n/a"):
            self.assertFalse(D.suppress_small_cell(n), n)

    def test_names_and_one_firm_cells_both_publish(self):
        # 2026-10-02 published the name; 2026-10-04 publishes the 1-firm cell.
        self.assertTrue(RULE("canonical_name"))
        self.assertFalse(D.suppress_small_cell(1))
        self.assertTrue(RULE("n_firms"))
        self.assertTrue(RULE("value_suppressed_small_cell"))


if __name__ == "__main__":
    unittest.main()
