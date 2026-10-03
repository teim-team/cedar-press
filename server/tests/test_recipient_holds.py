"""The recipient-hold policy input (data/cedar/recipient_holds.json).

Written 2026-10-02 for the Siletz repair: two Federal Funding transactions
under recipient UEI GJV4PJ8M5PC7 project to the tribal government while the
recipient is the Siletz Tribal Arts and Heritage Society, a separate Native
nonprofit. The only withholding vocabulary the consumer honoured was
``not_native``; this is the shape that states the real fact. These tests hold
the committed file to the validator, prove the drafted Siletz entry validates
as ``evidence_incomplete`` and is refused as ``ready`` while the bound uid is
unknown, and inject each dangerous shape (a ``not_native`` ruling, a minted
uid, a duplicate scope, a URL with no quotation) to watch the refusal fire.
Nothing here applies a hold to any uid.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODE = ROOT / "code"
sys.path.insert(0, str(CODE))


def _load_publication():
    spec = importlib.util.spec_from_file_location(
        "cedar_publication", CODE / "cedar_publication.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pub = _load_publication()
REGISTER = set(pub.register().keys())
SILETZ_GOVERNMENT = "CE-001A3-8M"  # Confederated Tribes of Siletz Indians of Oregon
ANOTHER_UID = "CE-00001-6S"

#: The entry docs/RECIPIENT_HOLDS_2026-10-02.md drafts. bound_cedar_uid is
#: null because the two transactions are not in Git and the uid they carry
#: was not read; the register's only Siletz government is named in the doc,
#: not here, so that nothing infers the binding from the register.
SILETZ_DRAFT = {
    "hold_id": "RH-2026-0001",
    "collection": "funding",
    "recipient_uei": "GJV4PJ8M5PC7",
    "award_ids": ["ASST_NON_1896753-42-22_417"],
    "hold_kind": "distinct_recipient",
    "action": "withhold",
    "bound_cedar_uid": None,
    "correct_recipient": {
        "name": "Siletz Tribal Arts and Heritage Society",
        "cedar_uid": None,
        "register_status": "not_in_register",
    },
    "ruling": (
        "Distinct legal entity from the tribal government: a separate Native nonprofit "
        "with its own board. No register entity yet; admission is the owner's adjudication."
    ),
    "evidence": [
        {
            "url": "https://siletzartsheritagesociety.org/board-of-directors/",
            "quoted": "QUOTE TO BE RE-READ AND PASTED WHEN THE PAGE IS REACHABLE",
            "checked_on": "2026-10-02",
        },
        {
            "url": "https://www.usaspending.gov/award/ASST_NON_1896753-42-22_417",
            "quoted": "QUOTE TO BE RE-READ AND PASTED WHEN THE PAGE IS REACHABLE",
            "checked_on": "2026-10-02",
        },
    ],
    "status": "evidence_incomplete",
    "recorded_on": "2026-10-02",
    "recorded_by": "consumer-side release-gap pass",
    "owner_review": "Havala Hanson",
}


def doc_with(*entries) -> dict:
    return {
        "schema_version": 1,
        "policy": "recipient_hold",
        "entries": [copy.deepcopy(e) for e in entries],
    }


class CommittedFile(unittest.TestCase):
    def test_committed_file_validates_and_carries_no_entry(self) -> None:
        self.assertEqual(pub.recipient_holds(), [])
        doc = json.loads(pub.RECIPIENT_HOLDS.read_text(encoding="utf-8"))
        self.assertEqual(doc["entries"], [])
        self.assertIn("GJV4PJ8M5PC7", doc["_pending"])
        self.assertEqual(pub.validate_recipient_holds(doc, REGISTER), [])

    def test_the_file_is_tracked_not_ignored(self) -> None:
        import subprocess

        out = subprocess.run(
            ["git", "check-ignore", "-q", "data/cedar/recipient_holds.json"], cwd=ROOT
        )
        self.assertEqual(out.returncode, 1, "the policy file must survive a fresh clone")

    def test_schema_document_names_the_same_vocabulary(self) -> None:
        schema = json.loads(
            (ROOT / "docs/schema/recipient_holds.schema.json").read_text(encoding="utf-8")
        )
        entry = schema["$defs"]["entry"]["properties"]
        self.assertEqual(set(entry["hold_kind"]["enum"]), set(pub.RECIPIENT_HOLD_KINDS))
        self.assertEqual(set(entry["action"]["enum"]), set(pub.RECIPIENT_HOLD_ACTIONS))
        self.assertEqual(tuple(entry["status"]["enum"]), pub.RECIPIENT_HOLD_STATUSES)
        self.assertEqual(set(schema["$defs"]["entry"]["required"]), set(SILETZ_DRAFT))

    def test_hold_status_is_not_the_denial_status(self) -> None:
        self.assertNotEqual(pub.RECIPIENT_HOLD_STATUS, pub.DENIED_STATUS)
        self.assertNotIn("not_native", pub.RECIPIENT_HOLD_STATUS)
        for text in pub.RECIPIENT_HOLD_KINDS.values():
            self.assertNotIn("not_native", text)


class SiletzDraft(unittest.TestCase):
    def test_draft_validates_as_evidence_incomplete(self) -> None:
        self.assertEqual(pub.validate_recipient_holds(doc_with(SILETZ_DRAFT), REGISTER), [])

    def test_draft_is_refused_as_ready_until_the_bound_uid_is_read(self) -> None:
        ready = copy.deepcopy(SILETZ_DRAFT)
        ready["status"] = "ready"
        problems = pub.validate_recipient_holds(doc_with(ready), REGISTER)
        self.assertTrue(
            any("requires the uid the projection currently carries" in p for p in problems),
            problems,
        )

    def test_draft_becomes_ready_only_with_a_register_uid_read_off_the_projection(self) -> None:
        ready = copy.deepcopy(SILETZ_DRAFT)
        ready["status"] = "ready"
        ready["bound_cedar_uid"] = SILETZ_GOVERNMENT
        self.assertIn(SILETZ_GOVERNMENT, REGISTER)
        self.assertEqual(pub.validate_recipient_holds(doc_with(ready), REGISTER), [])
        unknown = copy.deepcopy(ready)
        unknown["bound_cedar_uid"] = "CE-ZZZZZ-ZZ"
        self.assertTrue(
            any(
                "is not in the register" in p
                for p in pub.validate_recipient_holds(doc_with(unknown), REGISTER)
            )
        )

    def test_loader_reads_a_file_with_the_draft(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recipient_holds.json"
            path.write_text(json.dumps(doc_with(SILETZ_DRAFT)), encoding="utf-8")
            entries = pub.recipient_holds(path, REGISTER)
            self.assertEqual([e["hold_id"] for e in entries], ["RH-2026-0001"])


class Refusals(unittest.TestCase):
    def refused(self, mutate, needle: str) -> None:
        entry = copy.deepcopy(SILETZ_DRAFT)
        mutate(entry)
        problems = pub.validate_recipient_holds(doc_with(entry), REGISTER)
        self.assertTrue(any(needle in p for p in problems), (needle, problems))

    def test_not_native_ruling_is_refused(self) -> None:
        for text in ("not_native", "Not a Native entity", "NOT-NATIVE recipient"):
            self.refused(lambda e, t=text: e.__setitem__("ruling", t), "may not say not_native")

    def test_a_hold_never_mints_a_uid(self) -> None:
        def mint(e):
            e["hold_kind"] = "rebind_to_entity"
            e["action"] = "rebind"
            e["bound_cedar_uid"] = SILETZ_GOVERNMENT
            e["correct_recipient"] = {
                "name": "x",
                "cedar_uid": "CE-NEWID-00",
                "register_status": "in_register",
            }

        self.refused(mint, "a hold never mints")

    def test_hold_id_may_not_look_like_an_entity_id(self) -> None:
        self.refused(lambda e: e.__setitem__("hold_id", "CE-00001-6S"), "never a CE-/CB- id")
        self.refused(lambda e: e.__setitem__("hold_id", "CB-0000001"), "never a CE-/CB- id")

    def test_uei_format_is_enforced(self) -> None:
        for bad in ("GJV4PJ8M5PC", "gjv4pj8m5pc7", "GJV4PJ8M5PCO", "123456789012A"):
            self.refused(
                lambda e, b=bad: e.__setitem__("recipient_uei", b), "is not a 12-character SAM UEI"
            )

    def test_award_scope_must_be_exact_and_unique(self) -> None:
        self.refused(lambda e: e.__setitem__("award_ids", []), "at least one exact award key")
        self.refused(lambda e: e.__setitem__("award_ids", ["A", "A"]), "repeats a key")
        other = copy.deepcopy(SILETZ_DRAFT)
        other["hold_id"] = "RH-2026-0002"
        problems = pub.validate_recipient_holds(doc_with(SILETZ_DRAFT, other), REGISTER)
        self.assertTrue(any("is already scoped by RH-2026-0001" in p for p in problems), problems)

    def test_kind_and_action_must_agree(self) -> None:
        self.refused(
            lambda e: e.__setitem__("action", "rebind"), "a distinct_recipient hold withholds"
        )

        def rebind_kind(e):
            e["hold_kind"] = "rebind_to_entity"

        self.refused(rebind_kind, "rebind_to_entity rebinds")

    def test_rebind_requires_a_register_uid_different_from_the_bound_one(self) -> None:
        def rebind(e, target):
            e["hold_kind"] = "rebind_to_entity"
            e["action"] = "rebind"
            e["bound_cedar_uid"] = SILETZ_GOVERNMENT
            e["correct_recipient"] = {
                "name": "x",
                "cedar_uid": target,
                "register_status": "in_register",
            }

        self.refused(lambda e: rebind(e, None), "rebind requires correct_recipient.cedar_uid")
        self.refused(lambda e: rebind(e, SILETZ_GOVERNMENT), "nothing to rebind")
        ok = copy.deepcopy(SILETZ_DRAFT)
        rebind(ok, ANOTHER_UID)
        self.assertIn(ANOTHER_UID, REGISTER)
        self.assertEqual(pub.validate_recipient_holds(doc_with(ok), REGISTER), [])

    def test_withhold_carries_no_recipient_uid(self) -> None:
        self.refused(
            lambda e: e["correct_recipient"].__setitem__("cedar_uid", ANOTHER_UID),
            "a withhold carries correct_recipient.cedar_uid null",
        )

    def test_evidence_needs_a_quotation_and_an_https_url(self) -> None:
        self.refused(lambda e: e.__setitem__("evidence", []), "at least one source")
        self.refused(
            lambda e: e["evidence"][0].__setitem__("quoted", ""), "a URL alone is not evidence"
        )
        self.refused(
            lambda e: e["evidence"][0].__setitem__("url", "http://example.org"), "url must be https"
        )
        self.refused(
            lambda e: e["evidence"][0].__setitem__("checked_on", "yesterday"),
            "checked_on must be YYYY-MM-DD",
        )

    def test_vocabulary_and_document_shape_are_closed(self) -> None:
        self.refused(lambda e: e.__setitem__("status", "approved"), "status 'approved' not in")
        self.refused(
            lambda e: e.__setitem__("hold_kind", "not_native"), "hold_kind 'not_native' not in"
        )
        self.refused(lambda e: e.pop("ruling"), "missing ruling")
        self.assertEqual(pub.validate_recipient_holds([], REGISTER), ["document must be an object"])
        self.assertIn(
            "policy must be 'recipient_hold'",
            pub.validate_recipient_holds({"schema_version": 1, "entries": []}, REGISTER),
        )
        self.assertTrue(
            any(
                "entries must be a list" in p
                for p in pub.validate_recipient_holds(
                    {"schema_version": 1, "policy": "recipient_hold"}, REGISTER
                )
            )
        )

    def test_loader_fails_closed_on_an_absent_or_broken_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recipient_holds.json"
            with self.assertRaises(pub.RecipientHoldInvalid):
                pub.recipient_holds(path, REGISTER)
            path.write_text("{not json", encoding="utf-8")
            with self.assertRaises(pub.RecipientHoldInvalid):
                pub.recipient_holds(path, REGISTER)
            bad = doc_with(SILETZ_DRAFT)
            bad["entries"][0]["ruling"] = "not_native"
            path.write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaises(pub.RecipientHoldInvalid):
                pub.recipient_holds(path, REGISTER)


if __name__ == "__main__":
    unittest.main()
