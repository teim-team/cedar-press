"""Synthetic subscriber-store/session lifecycle tests; no network or real credentials."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from base64 import urlsafe_b64encode
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from fastapi import HTTPException, Response
from fastapi.testclient import TestClient

from cedar_press import db, session, subscribers


class TestSessionLifecycle(unittest.TestCase):
    """The store outlives session modules; this is not a real Postgres receipt."""

    @classmethod
    def setUpClass(cls):
        cls.password_hash = subscribers.hash_password("correct-horse")

    def setUp(self):
        self.row = {
            "email": "reader@example.org",
            "tier": "press_pro",
            "account_id": "account-fixture",
            "password_hash": self.password_hash,
            "updated_at": datetime(2026, 10, 1, tzinfo=timezone.utc),
        }
        self.lookups = 0
        self.revocations = 0
        self.env = mock.patch.dict(
            os.environ,
            {
                "CEDAR_PRESS_ENVIRONMENT": "development",
                "CEDAR_PRESS_SECRET": "synthetic-session-key-" * 3,
                "CEDAR_PRESS_INSECURE_COOKIE": "0",
                "DATABASE_URL": "postgresql://unused/synthetic",
                "CEDAR_PRESS_ACCOUNTS": "",
            },
        )
        self.env.start()
        self.addCleanup(self.env.stop)
        for patcher in (
            mock.patch.object(session, "_SECRET", os.environ["CEDAR_PRESS_SECRET"]),
            mock.patch.object(db, "configured", return_value=True),
            mock.patch.object(db, "one", side_effect=self.read),
            mock.patch.object(db, "execute", side_effect=self.write),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def read(self, sql, params=None):
        if "to_regclass" in sql:
            return None
        self.assertIn("updated_at", sql)
        self.lookups += 1
        if self.row is None or params != (self.row["email"],):
            return None
        return dict(self.row)

    def write(self, sql, params=None):
        self.assertIn("GREATEST(clock_timestamp(), updated_at + interval '1 microsecond')", sql)
        if self.row is None or params != (self.row["email"],):
            return 0
        self.row["updated_at"] += timedelta(microseconds=1)
        self.revocations += 1
        return 1

    def cookie(self):
        return session._encode(session.Session("reader@example.org", "press_pro"))

    def signed(self, payload):
        raw = json.dumps(payload).encode()
        body = urlsafe_b64encode(raw).decode().rstrip("=")
        return body + "." + session._sign(raw)

    def fresh_module(self, name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        self.addCleanup(sys.modules.pop, name, None)
        spec.loader.exec_module(module)
        return module

    def test_existing_pbkdf2_account_credentials_and_entitlements_are_preserved(self):
        # A pre-existing subscriber row uses the unchanged legacy password
        # format; session hardening is not a credential or subscription reset.
        original = dict(self.row)
        self.assertTrue(self.row["password_hash"].startswith("pbkdf2$240000$"))
        response = Response()
        signed_in = session.sign_in("Reader@Example.org ", "correct-horse", response)
        self.assertEqual(
            signed_in.as_payload(),
            {
                "email": "reader@example.org",
                "workspace_tier": "press_pro",
            },
        )
        self.assertEqual(self.row, original)
        self.assertEqual(self.revocations, 0)
        self.assertIsNotNone(session._decode(session._encode(signed_in)))

    def test_server_expiry_boundary_and_legacy_cookie_refusal(self):
        with mock.patch.object(session.time, "time", return_value=1000):
            cookie = self.cookie()
        with mock.patch.object(session.time, "time", return_value=1000 + session.MAX_AGE - 1):
            self.assertEqual(session._decode(cookie).tier, "press_pro")
        with mock.patch.object(session.time, "time", return_value=1000 + session.MAX_AGE):
            self.assertIsNone(session._decode(cookie))
        self.assertIsNone(
            session._decode(
                self.signed(
                    {
                        "email": "reader@example.org",
                        "tier": "press_pro",
                    }
                )
            )
        )

    def test_bad_claims_and_forgery_do_not_query_subscribers(self):
        good = {
            "v": 2,
            "email": "reader@example.org",
            "iat": 1000,
            "exp": 1000 + session.MAX_AGE,
            "rev": "a" * 64,
        }
        bad = [
            [],
            {**good, "iat": True},
            {**good, "exp": "bad"},
            {**good, "v": 2.0},
            {**good, "rev": "\u00e9" * 64},
            {**good, "iat": 1061, "exp": 1061 + session.MAX_AGE},
            {**good, "exp": 1001},
            {**good, "email": " Reader@example.org "},
        ]
        with mock.patch.object(session.time, "time", return_value=1000):
            for payload in bad:
                with self.subTest(payload=payload):
                    self.assertIsNone(session._decode(self.signed(payload)))
            for value in ("broken", "!!!.forged", "a." + "\u00e9", "x" * 4097):
                self.assertIsNone(session._decode(value))
        self.assertEqual(self.lookups, 0)

    def test_each_request_reads_current_tier_and_refuses_missing_or_inactive_account(self):
        cookie = self.cookie()
        self.assertEqual(session._decode(cookie).tier, "press_pro")
        self.row["tier"] = "press"
        self.assertEqual(session._decode(cookie).tier, "press")
        self.row["tier"] = "inactive"
        self.assertIsNone(session._decode(cookie))
        self.row = None
        self.assertIsNone(session._decode(cookie))
        self.assertEqual(self.lookups, 5)

    def test_equivalent_database_timezones_keep_the_same_session_revision(self):
        cookie = self.cookie()
        instant = self.row["updated_at"]
        self.row["updated_at"] = instant.astimezone(timezone(timedelta(hours=-7)))
        self.assertIsNotNone(session._decode(cookie))
        self.assertEqual(
            subscribers.find("reader@example.org").session_revision,
            instant.astimezone(timezone.utc).isoformat(timespec="microseconds"),
        )

    def test_naive_database_revision_is_refused_without_guessing_a_timezone(self):
        self.row["updated_at"] = self.row["updated_at"].replace(tzinfo=None)
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            subscribers.find("reader@example.org")

    def test_password_account_or_revision_changes_invalidate_existing_cookie(self):
        for field, value in (
            ("password_hash", "a-reset-password-hash"),
            ("account_id", "another-account"),
            ("updated_at", datetime(2026, 10, 2, tzinfo=timezone.utc)),
        ):
            with self.subTest(field=field):
                cookie = self.cookie()
                original = self.row[field]
                self.row[field] = value
                self.assertIsNone(session._decode(cookie))
                self.row[field] = original

    def test_logout_revokes_all_account_cookies_across_synthetic_worker_restart(self):
        first, second = self.cookie(), self.cookie()
        response = Response()
        session.sign_out(response, session._decode(first))
        self.assertEqual(self.revocations, 1)
        self.assertIsNone(session._decode(first))
        self.assertIsNone(session._decode(second))
        fresh = self.fresh_module("cedar_press._session_worker_fixture", session.__file__)
        self.assertIsNone(fresh._decode(first))
        self.assertEqual(fresh._decode(self.cookie()).email, "reader@example.org")
        cookie = response.headers["set-cookie"].lower()
        for flag in ("max-age=0", "httponly", "secure", "samesite=none", "path=/"):
            self.assertIn(flag, cookie)

    def test_invalid_logout_does_not_revoke_a_new_session(self):
        cookie = self.cookie()
        session.sign_out(Response(), None)
        self.assertEqual(self.revocations, 0)
        self.assertIsNotNone(session._decode(cookie))

    def test_login_signs_after_platform_link_revision_change(self):
        def link(email):
            self.assertEqual(email, self.row["email"])
            self.row["updated_at"] += timedelta(microseconds=1)
            return True

        with mock.patch.object(subscribers, "link_platform_account", side_effect=link):
            response = Response()
            signed_in = session.sign_in("reader@example.org", "correct-horse", response)
        self.assertIsNotNone(signed_in)
        self.assertIsNotNone(session._decode(session._encode(signed_in)))
        self.assertIn("HttpOnly", response.headers["set-cookie"])

    def test_password_reset_during_link_is_not_issued_a_new_revision(self):
        def reset(_email):
            self.row["password_hash"] = "a-new-password-hash"
            return True

        response = Response()
        with mock.patch.object(subscribers, "link_platform_account", side_effect=reset):
            signed_in = session.sign_in("reader@example.org", "correct-horse", response)
        self.assertIsNone(signed_in)
        self.assertNotIn("set-cookie", response.headers)

    def test_production_configuration_is_required_before_authentication(self):
        valid = {
            "CEDAR_PRESS_ENVIRONMENT": "production",
            "CEDAR_PRESS_SECRET": session._SECRET,
            "DATABASE_URL": "postgresql://unused/synthetic",
            "CEDAR_PRESS_INSECURE_COOKIE": "0",
            "CEDAR_PRESS_ACCOUNTS": "",
        }
        with mock.patch.dict(os.environ, valid):
            session.validate_auth_configuration()
            for field, value in (
                ("DATABASE_URL", ""),
                ("CEDAR_PRESS_SECRET", ""),
                ("CEDAR_PRESS_SECRET", "x" * 64),
                ("CEDAR_PRESS_INSECURE_COOKIE", "1"),
                ("CEDAR_PRESS_ACCOUNTS", '{"example":{}}'),
                ("CEDAR_PRESS_ENVIRONMENT", "unrecognized"),
            ):
                with (
                    self.subTest(field=field, value=value),
                    mock.patch.dict(os.environ, {field: value}),
                ):
                    with self.assertRaises(HTTPException) as error:
                        session.current_session(None)
                    self.assertEqual(error.exception.status_code, 503)
                    self.assertEqual(error.exception.detail["code"], "AUTH_CONFIGURATION_REQUIRED")

    def test_development_logout_uses_the_same_revision_contract(self):
        with (
            mock.patch.object(db, "configured", return_value=False),
            mock.patch.dict(
                os.environ,
                {
                    "CEDAR_PRESS_ACCOUNTS": json.dumps(
                        {
                            "reader@example.org": {"password": "fixture-only", "tier": "press"},
                        }
                    ),
                },
            ),
            mock.patch.object(subscribers, "_session_revisions", {}),
        ):
            cookie = self.cookie()
            session.sign_out(Response(), session._decode(cookie))
            self.assertIsNone(session._decode(cookie))
            self.assertIsNotNone(session._decode(self.cookie()))


class TestWorkspaceCors(unittest.TestCase):
    def test_default_origins_include_workspace_and_refuse_unrelated_origin(self):
        from cedar_press import priorities

        name = "cedar_press._workspace_cors_fixture"
        path = Path(session.__file__).with_name("app.py")
        with mock.patch.dict(
            os.environ,
            {
                "DATABASE_URL": "",
                "CEDAR_PRESS_ENVIRONMENT": "development",
            },
        ):
            os.environ.pop("CEDAR_PRESS_ORIGINS", None)
            with mock.patch.object(priorities, "open_store", return_value=mock.Mock()):
                spec = importlib.util.spec_from_file_location(name, path)
                module = importlib.util.module_from_spec(spec)
                sys.modules[name] = module
                try:
                    spec.loader.exec_module(module)
                    client = TestClient(module.app)
                    for origin in ("https://cedarpress.ai", "https://app.cedarpress.ai"):
                        reply = client.options(
                            "/auth/login",
                            headers={
                                "Origin": origin,
                                "Access-Control-Request-Method": "POST",
                                "Access-Control-Request-Headers": "content-type",
                            },
                        )
                        self.assertEqual(reply.status_code, 200)
                        self.assertEqual(reply.headers["access-control-allow-origin"], origin)
                        self.assertEqual(reply.headers["access-control-allow-credentials"], "true")
                    reply = client.options(
                        "/auth/login",
                        headers={
                            "Origin": "https://unrelated.example",
                            "Access-Control-Request-Method": "POST",
                        },
                    )
                    self.assertEqual(reply.status_code, 400)
                    self.assertNotIn("access-control-allow-origin", reply.headers)
                    with mock.patch.object(module, "sign_out") as revoke:
                        denied = client.post(
                            "/auth/logout",
                            headers={
                                "Origin": "https://unrelated.example",
                            },
                        )
                        self.assertEqual(denied.status_code, 403)
                        revoke.assert_not_called()
                finally:
                    sys.modules.pop(name, None)
