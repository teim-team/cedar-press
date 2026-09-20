"""The answer basis: what a reader is told a claim rests on.

Unit tests against ``_answer_basis`` directly rather than over HTTP, because
``fastapi.testclient`` needs a client library this checkout does not install
(see ``test_api.py``, which cannot import for the same reason). The rules
below are about the SHAPE of the claim, and the shape is decided here.
"""

from __future__ import annotations

import unittest

from cedar_press.app import _answer_basis

PROFILE = {
    "collection_name": "Native Federal Contractors",
    "version": "v1",
    "last_updated": "2026-09-04",
    "primary_sources": "FPDS via USAspending; SAM entity registrations.",
}


class TestTheBasisStatesOnlyWhatIsTrue(unittest.TestCase):
    def test_a_release_grounded_answer_cites_its_release_and_its_sources(self):
        basis = _answer_basis("release", PROFILE, "contractors")
        self.assertEqual(basis["kind"], "release")
        self.assertEqual(basis["collectionName"], "Native Federal Contractors")
        self.assertEqual(basis["version"], "v1")
        self.assertEqual(basis["updated"], "2026-09-04")
        self.assertIn("FPDS", basis["sources"])

    def test_a_synthesis_names_its_scope_and_cites_no_sources(self):
        """The distinction the whole feature exists for.

        A synthesis was asked *against* this collection, which is a real fact
        and is what the scope states. It did not read the collection's
        sources — there is no retrieval — so it does not list them. Listing
        them would be the product asserting that an answer rests on evidence
        it never touched.
        """
        basis = _answer_basis("synthesis", PROFILE, "contractors")
        self.assertEqual(basis["kind"], "synthesis")
        self.assertEqual(basis["collectionName"], "Native Federal Contractors")
        self.assertNotIn("sources", basis)

    def test_a_cited_record_count_is_never_invented(self):
        """Absent, not zero, and never a number nobody counted.

        Cedar returns no record citations. A zero would be read as "checked,
        found none" by a reader and by any renderer that tests truthiness.
        """
        for kind in ("release", "synthesis", "review"):
            with self.subTest(kind=kind):
                self.assertNotIn("citedRecords", _answer_basis(kind, PROFILE, "contractors"))

    def test_an_unscoped_question_still_produces_a_basis(self):
        """No collection means no release to name, not a missing contract."""
        basis = _answer_basis("synthesis", None, None)
        self.assertEqual(basis["kind"], "synthesis")
        self.assertIsNone(basis["collectionName"])
        self.assertIsNone(basis["version"])
        self.assertIsNone(basis["collectionId"])

    def test_review_is_declared_and_carries_no_evidence_claim(self):
        """`review` has no producer yet; it must not imply one until it does."""
        basis = _answer_basis("review", PROFILE, "contractors")
        self.assertEqual(basis["kind"], "review")
        self.assertNotIn("sources", basis)


if __name__ == "__main__":
    unittest.main()
