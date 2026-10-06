"""Every Cedar suggestion is answered, by the branch it claims.

The client offers Cedar's suggested questions from ``COLLECTION_JOBS`` in
``src/features/grove/pressJobs.js`` (owner's brief, 2026-09-26: outcome-led
once the reader is inside the product). Cedar Press answers from the
collection's release profile, ``collection_profiles.answer_from_profile``,
which matches words: it can say what a collection holds, how it is built and
how a record reaches its entity, and what its latest release changed, and it
cannot read records. So a suggestion is only an honest offer if two things
hold, and this suite holds both for every one of them:

- it is answered at all, rather than falling through to a refusal; and
- it is answered by the branch it names (``route``). The router is a word
  match, so "what changed in this organization's structure" would be
  "answered" with the release notes, confidently and in the release's name.
  That is the failure this checks for, which is why a non-empty answer is not
  enough.

The branch is recognised by what it returns, not by re-implementing the word
lists: a content answer opens on the collection's description, a construct
answer carries its entity-resolution method and does not open on the
description, and a release answer names the collection's current version.
"""

from __future__ import annotations

import unittest

from cedar_press import collection_profiles, press_catalog


def _sentence(text: str) -> str:
    stripped = (text or "").strip()
    return stripped if not stripped or stripped[-1] in ".?!" else f"{stripped}."


def branch_of(answer: str, profile: dict) -> str:
    """Which profile branch produced ``answer``: content, construct, changes or stats."""
    description = _sentence(profile["description"])
    method = _sentence(profile.get("entity_resolution_method") or "")
    release = press_catalog.RELEASES.get(profile["collection_id"]) or {}
    history = release.get("history") or []
    if answer.startswith(description):
        return "content"
    if method and method in answer:
        return "construct"
    if history and answer.startswith(
        f"{profile['collection_name']}, updated {history[0]['date']} ("
    ):
        return "changes"
    if profile.get("record_count_label") and profile["record_count_label"] in answer:
        return "stats"
    return "unknown"


class TestCedarQuestions(unittest.TestCase):
    def test_there_are_questions_to_check(self) -> None:
        # Without this the suite passes against an empty dump.
        self.assertGreaterEqual(len(press_catalog.CEDAR_QUESTIONS), 12)
        total = sum(len(items) for items in press_catalog.CEDAR_QUESTIONS.values())
        self.assertGreaterEqual(total, 36)

    def test_every_suggestion_is_answered_by_the_branch_it_names(self) -> None:
        for collection_id, items in press_catalog.CEDAR_QUESTIONS.items():
            profile = collection_profiles.profile_for(collection_id)
            self.assertIsNotNone(profile, collection_id)
            for item in items:
                with self.subTest(collection=collection_id, question=item["q"]):
                    answered = collection_profiles.answer_from_profile(item["q"], collection_id)
                    self.assertIsNotNone(answered, "falls through to a refusal")
                    self.assertEqual(branch_of(answered["answer"], profile), item["route"])

    def test_the_branch_check_catches_a_misroute(self) -> None:
        # The owner's example, which reads as a structure question and lands on
        # the release notes: the check has to see that, or it proves nothing.
        profile = collection_profiles.profile_for("need")
        answered = collection_profiles.answer_from_profile(
            "What changed in this organization's structure?", "need"
        )
        self.assertIsNotNone(answered)
        self.assertEqual(branch_of(answered["answer"], profile), "changes")
        # And a question about records is refused outright.
        self.assertIsNone(
            collection_profiles.answer_from_profile(
                "Which programs appear most often among these organizations?", "funding"
            )
        )


if __name__ == "__main__":
    unittest.main()
