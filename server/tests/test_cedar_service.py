"""The Cedar contract, checked against the two files that define it.

No network and no HTTP client: ``test_api.py`` already cannot run in this
checkout (``fastapi.testclient`` needs ``httpx``, a dev extra), and the part
worth pinning here is not that a POST succeeds — it is that the body Cedar
Press sends is the body ``cedar/schemas/chat.py`` accepts and the body
``teim-app/server/cedar/client.js`` sends. Those are the things that drift.
"""

from __future__ import annotations

import os
import unittest
from unittest import mock

from cedar_press import cedar_service


class TestTheContractFields(unittest.TestCase):
    """``CedarMessageRequest`` is the authority; these are its required fields."""

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
        # requestId, user, project and message are required by the schema;
        # threadId, projectContext and context are optional.
        for key in ("version", "requestId", "user", "project", "message"):
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
            self.assertEqual(cedar_service.chat_path(), "/api/v1/messages")
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
        with mock.patch.dict(os.environ, {"CEDAR_BASE_URL": "", "CEDAR_INTERNAL_API_KEY": ""}):
            with self.assertRaises(cedar_service.CedarUnavailable):
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
        self.assertEqual(reply.thread_id, "t-9")
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
        if not os.path.isfile(os.path.join(cedar, "schemas", "chat.py")):
            self.skipTest(f"no cedar checkout at {cedar}; set CEDAR_REPO")
        sys.path.insert(0, cedar)
        try:
            from schemas.chat import CedarMessageRequest
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
        parsed = CedarMessageRequest.model_validate(body)
        self.assertEqual(parsed.message.text, body["message"]["text"])
        self.assertEqual(parsed.project.name, "Native Federal Contractors")


if __name__ == "__main__":
    unittest.main()
