"""Authenticated Ask Cedar transport; synthetic HTTP only, no provider calls."""
from __future__ import annotations

import base64
import hmac
import importlib
import io
import json
import os
import unittest
import uuid
from unittest import mock

from fastapi.testclient import TestClient

from cedar_press import cedar_service

app_module = importlib.import_module("cedar_press.app")


class TestConversationHandles(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {
            "CEDAR_BASE_URL": "https://cedar.internal",
            "CEDAR_INTERNAL_API_KEY": "synthetic-internal-key",
            "CEDAR_ENABLED": "true",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        account = mock.patch.object(
            cedar_service.subscribers, "account_id_for", side_effect=lambda email: email.lower()
        )
        account.start()
        self.addCleanup(account.stop)
        self.scope = {
            "email": "reader@example.org", "tier": "press", "collection_id": "deals"
        }

    def test_scope_expiry_and_key_rotation_start_new_conversations(self):
        with mock.patch.object(cedar_service.time, "time", return_value=1000):
            token = cedar_service._seal_thread("service-thread", **self.scope)
            self.assertEqual(cedar_service._open_thread(token, **self.scope), "service-thread")
            for overrides in (
                {"email": "other@example.org"}, {"tier": "press_pro"},
                {"collection_id": "need"}, {"account_id": "different-subscription"},
            ):
                self.assertIsNone(cedar_service._open_thread(token, **{**self.scope, **overrides}))
            with mock.patch.dict(os.environ, {"CEDAR_INTERNAL_API_KEY": "rotated-key"}):
                self.assertIsNone(cedar_service._open_thread(token, **self.scope))
        with mock.patch.object(
            cedar_service.time, "time", return_value=1000 + cedar_service.THREAD_MAX_AGE
        ):
            self.assertIsNone(cedar_service._open_thread(token, **self.scope))

    def test_unsigned_oversized_forged_and_wrong_domain_handles_are_rejected(self):
        token = cedar_service._seal_thread("service-thread", **self.scope)
        data = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
        forged = bytearray(data)
        forged[-1] ^= 1
        wrong_domain = data[:-32] + hmac.new(
            cedar_service.api_key().encode(), b"another-domain:" + data[:-32], "sha256"
        ).digest()
        for value in (
            None, "", "raw-service-thread", "!" * 10, "A" * 4097,
            base64.urlsafe_b64encode(forged).decode(),
            base64.urlsafe_b64encode(wrong_domain).decode(),
        ):
            with self.subTest(value_type=type(value).__name__):
                self.assertIsNone(cedar_service._open_thread(value, **self.scope))

    def test_valid_signature_does_not_admit_invalid_claim_types(self):
        for invalid in ({"v": True}, {"exp": True}, {"thread": []}, {"thread": "x" * 513}):
            claims = {
                "v": 1, "thread": "service-thread",
                "scope": cedar_service._thread_scope(**self.scope),
                "exp": int(cedar_service.time.time()) + 100,
                **invalid,
            }
            body = json.dumps(claims).encode()
            signature = hmac.new(
                cedar_service.api_key().encode(), cedar_service._THREAD_DOMAIN + body, "sha256"
            ).digest()
            token = base64.urlsafe_b64encode(body + signature).decode()
            self.assertIsNone(cedar_service._open_thread(token, **self.scope))

    def test_real_contract_hop_uses_server_uuid_and_continues_only_its_handle(self):
        calls = []
        def exchange(request, timeout):
            body = json.loads(request.data)
            calls.append((request, body, timeout))
            return io.BytesIO(json.dumps({
                "answer": "Evidence is missing.", "threadId": body["threadId"]
            }).encode())
        with mock.patch.object(cedar_service.urllib.request, "urlopen", side_effect=exchange):
            first = cedar_service.ask(question="q", thread_id="victims-thread", **self.scope)
            self.assertIsInstance(uuid.UUID(calls[0][1]["threadId"]), uuid.UUID)
            self.assertNotEqual(calls[0][1]["threadId"], "victims-thread")
            second = cedar_service.ask(
                question="follow up", thread_id=first.thread_id, **self.scope
            )
        self.assertEqual(calls[0][1]["threadId"], calls[1][1]["threadId"])
        self.assertNotEqual(second.thread_id, calls[1][1]["threadId"])
        self.assertEqual(calls[0][0].full_url, "https://cedar.internal/api/v1/messages")
        self.assertEqual(calls[0][0].get_header("Authorization"), "Bearer synthetic-internal-key")
        self.assertEqual(calls[0][1]["user"]["id"], self.scope["email"])
        self.assertFalse(calls[0][1]["context"]["pressContext"]["retrieval"]["available"])

    def test_subscription_move_cannot_resume_former_subscription_history(self):
        calls = []
        def exchange(request, timeout):
            body = json.loads(request.data)
            calls.append(body)
            return io.BytesIO(json.dumps({
                "answer": "A scoped reply", "threadId": body["threadId"]
            }).encode())
        with mock.patch.object(
            cedar_service.subscribers, "account_id_for", side_effect=["account-a", "account-b"]
        ), mock.patch.object(cedar_service.urllib.request, "urlopen", side_effect=exchange):
            first = cedar_service.ask(question="q", **self.scope)
            cedar_service.ask(question="q2", thread_id=first.thread_id, **self.scope)
        self.assertNotEqual(calls[0]["threadId"], calls[1]["threadId"])

    def test_reply_shapes_and_size_fail_closed(self):
        for payload in (
            [], "text", {"answer": "ok"},
            {"answer": "ok", "threadId": []},
            {"answer": "ok", "threadId": "t", "unavailable": "false"},
        ):
            with self.subTest(payload=payload), mock.patch.object(
                cedar_service.urllib.request, "urlopen",
                return_value=io.BytesIO(json.dumps(payload).encode()),
            ), self.assertRaises(cedar_service.CedarUnavailable):
                cedar_service.ask(question="q", **self.scope)
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b"x" * (cedar_service.MAX_REPLY_BYTES + 1)
        with mock.patch.object(
            cedar_service.urllib.request, "urlopen", return_value=response
        ), self.assertRaises(cedar_service.CedarUnavailable):
            cedar_service.ask(question="q", **self.scope)
        response.read.assert_called_once_with(cedar_service.MAX_REPLY_BYTES + 1)

    def test_non_finite_timeout_uses_bounded_default(self):
        for value in ("inf", "Infinity", "nan", "1e999"):
            with self.subTest(value=value), mock.patch.dict(
                os.environ, {"CEDAR_TIMEOUT_MS": value}
            ):
                self.assertEqual(cedar_service.timeout_seconds(), 45.0)


class TestAuthenticatedAskRoute(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app_module.app)
        saved = dict(app_module.app.dependency_overrides)
        def restore():
            app_module.app.dependency_overrides.clear()
            app_module.app.dependency_overrides.update(saved)
        self.addCleanup(restore)
        app_module.app.dependency_overrides.clear()

    def test_anonymous_caller_never_reaches_cedar(self):
        app_module.app.dependency_overrides[app_module.current_session] = lambda: None
        with mock.patch.object(cedar_service, "ask") as ask:
            response = self.client.post("/cedar/ask", json={"question": "Help"})
        self.assertEqual(response.status_code, 401)
        ask.assert_not_called()

    def test_authenticated_principal_and_tier_cannot_be_supplied_by_browser(self):
        app_module.app.dependency_overrides[app_module.require_session] = lambda: (
            app_module.Session(email="reader@example.org", tier="press")
        )
        reply = cedar_service.CedarReply("A real service reply", "signed-handle", False)
        with mock.patch.object(cedar_service, "available", return_value=True), mock.patch.object(
            cedar_service, "ask", return_value=reply
        ) as ask:
            response = self.client.post("/cedar/ask", json={
                "question": "Help", "email": "other@example.org", "tier": "press_pro"
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["source"], "cedar")
        self.assertEqual(ask.call_args.kwargs["email"], "reader@example.org")
        self.assertEqual(ask.call_args.kwargs["tier"], "press")

    def test_two_api_turns_round_trip_an_opaque_handle_without_exposing_raw_ids(self):
        app_module.app.dependency_overrides[app_module.require_session] = lambda: (
            app_module.Session(email="reader@example.org", tier="press")
        )
        calls = []

        def exchange(request, timeout):
            body = json.loads(request.data)
            calls.append(body)
            return io.BytesIO(json.dumps({
                "answer": "The evidence provided is incomplete.",
                "threadId": body["threadId"],
                "upstreamConversationId": body["threadId"],
            }).encode())

        with mock.patch.dict(os.environ, {
            "CEDAR_BASE_URL": "https://cedar.internal",
            "CEDAR_INTERNAL_API_KEY": "synthetic-internal-key",
            "CEDAR_ENABLED": "true",
        }), mock.patch.object(
            cedar_service.subscribers, "account_id_for", return_value="subscription-one"
        ), mock.patch.object(cedar_service.urllib.request, "urlopen", side_effect=exchange):
            first = self.client.post("/cedar/ask", json={
                "question": "What evidence is missing?", "threadId": "foreign-raw-id"
            })
            self.assertEqual(first.status_code, 200, first.text)
            handle = first.json()["threadId"]
            self.assertIsInstance(handle, str)
            self.assertGreater(len(handle), 64)
            second = self.client.post("/cedar/ask", json={
                "question": "Explain that limitation.", "threadId": handle
            })
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]["threadId"], calls[1]["threadId"])
        self.assertNotEqual(calls[0]["threadId"], "foreign-raw-id")
        for response in (first, second):
            self.assertEqual(response.json()["source"], "cedar")
            self.assertNotEqual(response.json()["threadId"], calls[0]["threadId"])
            self.assertNotIn(calls[0]["threadId"], response.text)
            self.assertNotIn("upstreamConversationId", response.json())

    def test_degraded_service_reply_is_not_labelled_as_synthesis(self):
        app_module.app.dependency_overrides[app_module.require_session] = lambda: (
            app_module.Session(email="reader@example.org", tier="press")
        )
        with mock.patch.object(cedar_service, "available", return_value=True), mock.patch.object(
            cedar_service, "ask",
            return_value=cedar_service.CedarReply("Unavailable", None, True),
        ):
            response = self.client.post("/cedar/ask", json={"question": "Help"})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "CEDAR_UNAVAILABLE")
        self.assertNotIn("answerBasis", response.json())
