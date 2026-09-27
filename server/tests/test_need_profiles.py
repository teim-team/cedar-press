"""Publication, object identity and source evidence on NEED enterprise profiles."""

import io
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from cedar_press import need_profiles, repository
from cedar_press.app import app, require_session
from cedar_press.session import Session


class NeedProfiles(unittest.TestCase):
    def row(self, **updates):
        return {
            "observation_id": "synthetic-1",
            "enterprise_id": "CEDAR-NEST-SYNTHETIC",
            "publication_status": "eligible",
            "hold_reason": "",
            "source_url": "https://example.org/fact",
            "issuer_name": "Synthetic enterprise",
            "rating": "BBB",
            "historical_status": "historical",
            **updates,
        }

    def test_hold_precedes_pins_and_transport(self):
        with patch.object(
            repository, "grove_release_pin", side_effect=AssertionError("No pin read")
        ):
            result = need_profiles.enterprise_evidence("CEDAR-NEST-SYNTHETIC")
        self.assertEqual(result["status"], "publication_held")
        self.assertIsNone(result["release_id"])
        self.assertFalse(any(result[key] for key in need_profiles.COMPONENTS))

    def test_exact_enterprise_does_not_inherit_or_leak_holds(self):
        records = [
            self.row(),
            self.row(observation_id="held", hold_reason="rights"),
            self.row(observation_id="other", enterprise_id="CEDAR-NEST-OTHER"),
            self.row(observation_id="tribe", enterprise_id="CE-SYNTHETIC"),
            self.row(observation_id="unknown", publication_status="unreviewed"),
        ]
        self.assertEqual(
            need_profiles.select_enterprise_rows(records, "CEDAR-NEST-SYNTHETIC"), [records[0]]
        )
        self.assertEqual(
            need_profiles.enterprise_evidence("CE-SYNTHETIC")["status"], "enterprise_required"
        )

    def test_sources_duplicates_and_limits_fail_closed(self):
        for source in (
            None,
            "http://example.org",
            "javascript:alert(1)",
            "https://a:b@example.org",
            "https://[",
        ):
            with self.subTest(source=source), self.assertRaises(repository.FullReleaseUnavailable):
                need_profiles.select_enterprise_rows(
                    [self.row(source_url=source)], "CEDAR-NEST-SYNTHETIC"
                )
        for rows in ([self.row(), self.row()], [self.row(observation_id="")], [None]):
            with self.assertRaises(repository.FullReleaseUnavailable):
                need_profiles.select_enterprise_rows(rows, "CEDAR-NEST-SYNTHETIC")
        with (
            patch.object(need_profiles, "MAX_PROFILE_ROWS", 1),
            self.assertRaises(repository.FullReleaseUnavailable),
        ):
            need_profiles.select_enterprise_rows(
                [self.row(), self.row(observation_id="two")], "CEDAR-NEST-SYNTHETIC"
            )

    def test_all_components_same_pin_streams_closed_historical_values_preserved(self):
        streams = []

        def released(*args, **kwargs):
            stream = io.BytesIO((json.dumps(self.row()) + "\n").encode())
            streams.append(stream)
            return {"content_file": stream, "release_id": "a" * 64}

        policy = SimpleNamespace(
            assert_collection_publishable=lambda _: None, FieldMapRefusal=ValueError
        )
        with (
            patch.object(repository, "_publication_policy", return_value=policy),
            patch.object(repository, "grove_release_pin", return_value={"release_id": "a" * 64}),
            patch.object(repository, "grove_full_release", side_effect=released) as transport,
        ):
            result = need_profiles.enterprise_evidence("CEDAR-NEST-SYNTHETIC")
        self.assertEqual(result["status"], "available")
        self.assertEqual(result["credit_rating_actions"][0]["historical_status"], "historical")
        self.assertEqual(transport.call_count, 3)
        self.assertTrue(all(stream.closed for stream in streams))
        for call in transport.call_args_list:
            self.assertEqual(call.args, ("need", "a" * 64))

    def test_bad_bytes_pin_and_identifier_refused(self):
        for content in (b"{bad}\n", b"x" * (need_profiles.MAX_ROW_BYTES + 1)):
            with self.assertRaises(repository.FullReleaseUnavailable):
                list(need_profiles._rows(io.BytesIO(content)))
        with self.assertRaises(ValueError):
            need_profiles.enterprise_evidence("../other")
        with (
            patch.object(repository, "_publication_policy", side_effect=ImportError),
            self.assertRaises(repository.FullReleaseUnavailable),
        ):
            need_profiles.enterprise_evidence("CEDAR-NEST-SYNTHETIC")
        policy = SimpleNamespace(
            assert_collection_publishable=lambda _: None, FieldMapRefusal=ValueError
        )
        stream = io.BytesIO(b"")
        with (
            patch.object(repository, "_publication_policy", return_value=policy),
            patch.object(repository, "grove_release_pin", return_value={"release_id": "a" * 64}),
            patch.object(
                repository,
                "grove_full_release",
                return_value={"content_file": stream, "release_id": "b" * 64},
            ),
            self.assertRaises(repository.FullReleaseUnavailable),
        ):
            need_profiles.enterprise_evidence("CEDAR-NEST-SYNTHETIC")
        self.assertTrue(stream.closed)

    def test_single_component_verified_bytes_and_honest_empty(self):
        policy = SimpleNamespace(
            assert_collection_publishable=lambda _: None, FieldMapRefusal=ValueError
        )
        with (
            patch.object(repository, "_publication_policy", return_value=policy),
            patch.object(repository, "grove_release_pin", return_value={"release_id": "a" * 64}),
            patch.object(
                repository,
                "grove_full_release",
                return_value={
                    "content": (
                        json.dumps(self.row(enterprise_id="CEDAR-NEST-OTHER")) + "\n"
                    ).encode(),
                    "release_id": "a" * 64,
                },
            ),
        ):
            self.assertEqual(
                need_profiles.enterprise_evidence("CEDAR-NEST-SYNTHETIC")["status"], "no_evidence"
            )

    def test_http_requires_live_entitled_account_and_keeps_hold(self):
        client = TestClient(app)
        path = "/press/need/enterprises/CEDAR-NEST-SYNTHETIC/evidence"
        self.assertEqual(client.get(path).status_code, 401)
        try:
            app.dependency_overrides[require_session] = lambda: Session(
                email="synthetic@example.org", tier="press_pro"
            )
            with patch("cedar_press.app.subscribers.find", return_value=None):
                self.assertEqual(client.get(path).status_code, 401)
            with patch(
                "cedar_press.app.subscribers.find", return_value=SimpleNamespace(tier="press")
            ):
                self.assertEqual(client.get(path).status_code, 403)
            with patch(
                "cedar_press.app.subscribers.find", return_value=SimpleNamespace(tier="press_pro")
            ):
                response = client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["status"], "publication_held")
                self.assertEqual(response.headers["cache-control"], "private, no-store")
            with patch("cedar_press.app.subscribers.find", side_effect=RuntimeError):
                self.assertEqual(client.get(path).status_code, 503)
        finally:
            app.dependency_overrides.pop(require_session, None)
