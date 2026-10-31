"""The Cedar contract, checked against the two files that define it.

No network and no HTTP client: ``test_api.py`` already cannot run in this
checkout (``fastapi.testclient`` needs ``httpx``, a dev extra), and the part
worth pinning here is not that a POST succeeds — it is that the body Cedar
Press sends is the body ``cedar/schemas/press.py`` accepts. That is the
thing that drifts.
"""

from __future__ import annotations

import os
import unittest
from types import SimpleNamespace
from unittest import mock

from cedar_press import cedar_service


class TestTheContractFields(unittest.TestCase):
    """``PressMessageRequest`` is the authority; these are its required fields."""

    def payload(self, **overrides):
        base = {
            "question": "How was this built?",
            "email": "reader@example.org",
            "tier": "press_pro",
            "thread_id": None,
            "collection_id": "contractors",
            "collection_name": "Prime Contracting",
            "pathname": "/data",
        }
        base.update(overrides)
        return cedar_service._payload(**base)

    def test_it_carries_every_field_the_schema_requires(self):
        body = self.payload()
        # requestId, user, project, context and message are required by the schema;
        # threadId is optional.
        for key in ("version", "requestId", "user", "project", "context", "message"):
            self.assertIn(key, body)
        self.assertEqual(body["version"], cedar_service.CONTRACT_VERSION)
        self.assertEqual(body["user"]["id"], "reader@example.org")
        self.assertEqual(body["message"]["text"], "How was this built?")

    def test_the_request_id_is_also_the_message_id(self):
        """``teim-app`` sends one id for both, and Cedar echoes it back as
        ``messageId``. Sending two would make a reply impossible to match."""
        body = self.payload()
        self.assertEqual(body["requestId"], body["message"]["id"])

    def test_the_collection_takes_the_project_slot_and_says_so(self):
        """Cedar Press has no TEIM project. The slot is required, so the
        collection fills it — named, not a placeholder that reads like an id."""
        body = self.payload()
        self.assertEqual(body["project"]["id"], "collection:contractors")
        self.assertEqual(body["project"]["name"], "Prime Contracting")
        self.assertEqual(body["project"]["projectData"]["surface"], "cedar-press")
        self.assertEqual(body["project"]["projectData"]["tier"], "press_pro")

    def test_unscoped_questions_still_have_a_project(self):
        body = self.payload(collection_id=None, collection_name=None)
        self.assertEqual(body["project"]["id"], "cedar-press")
        self.assertEqual(body["project"]["name"], "Cedar Press")

    def test_a_thread_id_is_passed_through_when_there_is_one(self):
        """The whole of what makes it a conversation."""
        self.assertIsNone(self.payload()["threadId"])
        self.assertEqual(self.payload(thread_id="t-7")["threadId"], "t-7")


class TestTheEnvironmentSurfaceMatchesTeimApp(unittest.TestCase):
    """One service, two callers, one set of variables.

    Every name and every default here is read off
    ``teim-app/server/cedar/client.js``. The tests are here because a
    divergence is silent: a deployment sets ``CEDAR_ENABLED=false`` expecting
    both products to go quiet, and one of them does not.
    """

    def test_cedar_enabled_is_off_only_for_the_literal_false(self):
        """teim-app's ``parseEnabled``: unset is ON, and only "false" is off."""
        wired = {"CEDAR_BASE_URL": "https://cedar.internal", "CEDAR_INTERNAL_API_KEY": "k"}
        for value, expected in [
            (None, True),
            ("false", False),
            ("true", True),
            ("", True),
            ("0", True),
            ("FALSE", True),
        ]:
            env = dict(wired)
            if value is not None:
                env["CEDAR_ENABLED"] = value
            with self.subTest(value=value), mock.patch.dict(os.environ, env, clear=False):
                if value is None:
                    os.environ.pop("CEDAR_ENABLED", None)
                self.assertEqual(cedar_service.available(), expected)

    def test_the_key_falls_back_to_cedar_api_key(self):
        with mock.patch.dict(
            os.environ, {"CEDAR_INTERNAL_API_KEY": "", "CEDAR_API_KEY": "fallback"}
        ):
            self.assertEqual(cedar_service.api_key(), "fallback")
        with mock.patch.dict(
            os.environ, {"CEDAR_INTERNAL_API_KEY": "internal", "CEDAR_API_KEY": "fallback"}
        ):
            self.assertEqual(cedar_service.api_key(), "internal")

    def test_the_path_is_overridable_and_always_rooted(self):
        with mock.patch.dict(os.environ, {"CEDAR_API_PATH": ""}):
            self.assertEqual(cedar_service.chat_path(), "/api/v1/press/messages")
        with mock.patch.dict(os.environ, {"CEDAR_API_PATH": "/v2/messages"}):
            self.assertEqual(cedar_service.chat_path(), "/v2/messages")
        # A path without its leading slash would concatenate into the host.
        with mock.patch.dict(os.environ, {"CEDAR_API_PATH": "v2/messages"}):
            self.assertEqual(cedar_service.chat_path(), "/v2/messages")

    def test_the_timeout_is_milliseconds_and_survives_nonsense(self):
        """Milliseconds, because that is the unit teim-app's variable carries."""
        with mock.patch.dict(os.environ, {"CEDAR_TIMEOUT_MS": "9000"}):
            self.assertEqual(cedar_service.timeout_seconds(), 9.0)
        for bad in ("", "soon", "-1", "0"):
            with self.subTest(bad=bad), mock.patch.dict(os.environ, {"CEDAR_TIMEOUT_MS": bad}):
                self.assertEqual(cedar_service.timeout_seconds(), 45.0)


class TestWhenItIsNotWiredUp(unittest.TestCase):
    def test_a_base_url_without_a_key_is_not_available(self):
        """A key-less call gets a 401 from every request. That is a
        misconfiguration, and reporting it as an outage hides it."""
        with mock.patch.dict(
            os.environ, {"CEDAR_BASE_URL": "https://cedar.internal", "CEDAR_INTERNAL_API_KEY": ""}
        ):
            self.assertFalse(cedar_service.available())

    def test_neither_set_is_not_available(self):
        with mock.patch.dict(os.environ, {"CEDAR_BASE_URL": "", "CEDAR_INTERNAL_API_KEY": ""}):
            self.assertFalse(cedar_service.available())

    def test_both_set_is_available(self):
        with mock.patch.dict(
            os.environ,
            {"CEDAR_BASE_URL": "https://cedar.internal/", "CEDAR_INTERNAL_API_KEY": "k"},
        ):
            self.assertTrue(cedar_service.available())
            # The trailing slash is stripped, so the path is not doubled.
            self.assertEqual(cedar_service.base_url(), "https://cedar.internal")

    def test_asking_an_unconfigured_cedar_raises_rather_than_inventing(self):
        with (
            mock.patch.dict(os.environ, {"CEDAR_BASE_URL": "", "CEDAR_INTERNAL_API_KEY": ""}),
            self.assertRaises(cedar_service.CedarUnavailable),
        ):
            cedar_service.ask(question="anything", email="a@b.c", tier="press")


class TestReadingTheReply(unittest.TestCase):
    """A 200 is not an answer. These are the three bodies that are not one."""

    def ask_returning(self, payload):
        raw = mock.MagicMock()
        raw.read.return_value = __import__("json").dumps(payload).encode()
        raw.__enter__ = lambda self_: self_
        raw.__exit__ = lambda *_: False
        with mock.patch.dict(
            os.environ, {"CEDAR_BASE_URL": "https://cedar.internal", "CEDAR_INTERNAL_API_KEY": "k"}
        ), mock.patch.object(cedar_service.urllib.request, "urlopen", return_value=raw):
            return cedar_service.ask(question="q", email="a@b.c", tier="press")

    def test_an_answer_comes_back_with_its_thread(self):
        reply = self.ask_returning({"answer": "  Because.  ", "threadId": "t-9"})
        self.assertEqual(reply.answer, "Because.")
        with mock.patch.dict(os.environ, {"CEDAR_INTERNAL_API_KEY": "k"}):
            self.assertEqual(
                cedar_service._open_thread(
                    reply.thread_id, email="a@b.c", tier="press", collection_id=None
                ),
                "t-9",
            )
        self.assertFalse(reply.unavailable)

    def test_the_contracts_own_degraded_flag_is_kept(self):
        """Cedar saying 'I am unavailable' inside a 200 is not an answer, and
        the panel must not file it under one."""
        reply = self.ask_returning({"answer": "Cedar is unavailable.", "unavailable": True})
        self.assertTrue(reply.unavailable)

    def test_an_empty_answer_is_not_an_answer(self):
        for body in ({}, {"answer": ""}, {"answer": "   "}, {"answer": 7}):
            with self.subTest(body=body), self.assertRaises(cedar_service.CedarUnavailable):
                self.ask_returning(body)


class TestAgainstTheRealSchema(unittest.TestCase):
    """The strongest check available: hand the body to Cedar's own pydantic model.

    Self-skipping, because the `cedar` checkout is not always beside this one.
    When it is, this is not a restatement of the contract — it *is* the
    contract, and a field renamed over there fails here rather than in
    production.
    """

    def test_cedar_accepts_the_body_cedar_press_sends(self):
        import sys

        cedar = os.path.join(os.path.dirname(__file__), "..", "..", "..", "cedar")
        cedar = os.path.abspath(os.environ.get("CEDAR_REPO", cedar))
        if not os.path.isfile(os.path.join(cedar, "schemas", "press.py")):
            self.skipTest(f"no cedar checkout at {cedar}; set CEDAR_REPO")
        sys.path.insert(0, cedar)
        try:
            from schemas.press import PressMessageRequest
        finally:
            sys.path.remove(cedar)

        body = cedar_service._payload(
            question="Which nations appear in more than one collection?",
            email="reader@example.org",
            tier="press_pro",
            thread_id=None,
            collection_id="contractors",
            collection_name="Native Federal Contractors",
            pathname="/data",
        )
        parsed = PressMessageRequest.model_validate(body)
        self.assertEqual(parsed.message.text, body["message"]["text"])
        self.assertEqual(parsed.project.name, "Native Federal Contractors")


HEX_A = "a" * 64
HEX_B = "b" * 64
HEX_C = "c" * 64

_DATASETS = (
    SimpleNamespace(id="funding", shelf="standard"),
    SimpleNamespace(id="deals", shelf="standard"),
    SimpleNamespace(id="contractors", shelf="pro"),
    SimpleNamespace(id="need", shelf="pro"),
)


def _facts(table):
    def lookup(dataset_id):
        return table.get(dataset_id)

    return lookup


class TestRetrievalAllowlist(unittest.TestCase):
    def setUp(self):
        from cedar_press import collections as launch

        self.launch = launch
        self.table = {
            "funding": {"release_id": HEX_A},
            "deals": {"release_id": HEX_B},
            "contractors": {"release_id": HEX_C},
            "need": {"release_id": "short"},
        }
        self.catalog = mock.patch.object(launch, "LAUNCH_COLLECTION", _DATASETS)
        self.facts = mock.patch.object(
            launch, "collection_cedar_facts", side_effect=_facts(self.table)
        )
        self.catalog.start()
        self.facts.start()

    def tearDown(self):
        self.facts.stop()
        self.catalog.stop()

    def test_press_sends_standard_ids_in_catalog_order(self):
        allowed, pins = cedar_service.retrieval_allowlist("press")
        self.assertEqual(allowed, ["funding", "deals"])
        self.assertEqual(pins, {"funding": HEX_A, "deals": HEX_B})

    def test_press_pro_adds_a_pro_id_with_a_real_release_id(self):
        allowed, pins = cedar_service.retrieval_allowlist("press_pro")
        self.assertEqual(allowed, ["funding", "deals", "contractors"])
        self.assertEqual(pins["contractors"], HEX_C)
        self.assertNotIn("need", allowed)

    def test_grove_and_tree_receive_the_same_open_storefront_ids(self):
        for tier in ("grove", "tree"):
            with self.subTest(tier=tier):
                allowed, _pins = cedar_service.retrieval_allowlist(tier)
                self.assertEqual(allowed, ["funding", "deals", "contractors"])
                # Gaming stays out because it is not in LAUNCH_COLLECTION,
                # which test_access.py already pins.

    def test_an_unknown_tier_sends_nothing(self):
        allowed, pins = cedar_service.retrieval_allowlist("seed")
        self.assertEqual(allowed, [])
        self.assertEqual(pins, {})

    def test_a_missing_release_id_drops_that_id_and_keeps_the_other(self):
        self.table["deals"] = None
        allowed, pins = cedar_service.retrieval_allowlist("press")
        self.assertEqual(allowed, ["funding"])
        self.assertEqual(pins, {"funding": HEX_A})

    def test_an_uppercase_release_id_is_dropped(self):
        self.table["funding"] = {"release_id": "A" * 64}
        allowed, pins = cedar_service.retrieval_allowlist("press")
        self.assertEqual(allowed, ["deals"])
        self.assertEqual(pins, {"deals": HEX_B})

    def test_may_open_false_drops_the_id_even_with_a_release_id(self):
        with mock.patch("cedar_press.repository.may_open", return_value=False):
            allowed, pins = cedar_service.retrieval_allowlist("press_pro")
        self.assertEqual(allowed, [])
        self.assertEqual(pins, {})

    def test_the_page_does_not_filter_the_payload(self):
        body = cedar_service._payload(
            question="How many deals did the Cherokee Nation have?",
            email="reader@example.org",
            tier="press",
            thread_id=None,
            collection_id="contractors",
            collection_name="Prime Contracting",
            pathname="/data",
        )
        press = body["context"]["pressContext"]
        self.assertEqual(press["collectionId"], "contractors")
        self.assertEqual(press["allowedCollectionIds"], ["funding", "deals"])
        self.assertEqual(
            press["pinnedReleaseIds"], {"funding": HEX_A, "deals": HEX_B}
        )
        self.assertNotIn("contractors", press["allowedCollectionIds"])
        self.assertFalse(press["retrieval"]["available"])
        again = cedar_service._payload(
            question="A different question that names funding",
            email="reader@example.org",
            tier="press",
            thread_id=None,
            collection_id="contractors",
            collection_name="Prime Contracting",
            pathname="/data",
        )
        self.assertEqual(
            again["context"]["pressContext"]["allowedCollectionIds"],
            press["allowedCollectionIds"],
        )


if __name__ == "__main__":
    unittest.main()
