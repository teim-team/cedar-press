"""Registered entity profiles retain exact legal issuers and related NEED records."""

import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from cedar_press import need_profiles as profiles
from cedar_press import repository
from cedar_press.app import app, require_session
from cedar_press.session import Session

UID = "CE-00000-00"
ENTERPRISE = "CEDAR-NEST-SYNTHETIC"
PIN = "a" * 64


class NeedProfiles(unittest.TestCase):
    def setUp(self):
        registered = patch.object(profiles, "registered_entity", return_value="Synthetic ANC")
        registered.start()
        self.addCleanup(registered.stop)

    def row(self, **updates):
        return (
            dict(
                observation_id="synthetic-1",
                enterprise_id=ENTERPRISE,
                legal_subject_cedar_uid="",
                publication_status="eligible",
                hold_reason="",
                source_url="https://example.org/fact",
                issuer_name="Synthetic enterprise",
                rating="BBB",
                historical_status="historical",
            )
            | updates
        )

    def link(self, **updates):
        return (
            dict(
                profile_link_id="synthetic-link",
                profile_cedar_uid=UID,
                enterprise_id=ENTERPRISE,
                enterprise_name="Synthetic subsidiary",
                relationship_type="subsidiary",
                source_url="https://example.org/ownership",
                publication_status="eligible",
                hold_reason="",
            )
            | updates
        )

    def serve(self, links=None, records=None, returned_pin=PIN):
        policy = SimpleNamespace(
            assert_collection_publishable=lambda _: None, FieldMapRefusal=ValueError
        )
        streams = []

        def released(*args, **kwargs):
            rows = (
                (links if links is not None else [self.link()])
                if kwargs["component"] == "profile_links"
                else (records if records is not None else [self.row()])
            )
            stream = io.BytesIO(b"".join((json.dumps(row) + "\n").encode() for row in rows))
            streams.append(stream)
            return {"content_file": stream, "release_id": returned_pin}

        with (
            patch.object(repository, "_publication_policy", return_value=policy),
            patch.object(repository, "grove_release_pin", return_value={"release_id": PIN}),
            patch.object(repository, "grove_full_release", side_effect=released) as transport,
        ):
            try:
                result = profiles.entity_evidence(UID)
            finally:
                self.assertTrue(all(stream.closed for stream in streams))
        for call in transport.call_args_list:
            self.assertEqual(call.args, ("need", PIN))
        return result

    def test_publication_hold_precedes_pin_and_transport(self):
        with patch.object(
            repository, "grove_release_pin", side_effect=AssertionError("No pin read")
        ):
            result = profiles.entity_evidence(UID)
        self.assertEqual(result["status"], "publication_held")
        self.assertIsNone(result["release_id"])
        self.assertFalse(any(result[key] for key in profiles.COMPONENTS))

    def test_direct_issuer_and_related_enterprise_never_transfer_identity(self):
        rows = [
            self.row(),
            self.row(observation_id="direct", enterprise_id="", legal_subject_cedar_uid=UID),
            self.row(observation_id="held", hold_reason="rights"),
            self.row(observation_id="other", enterprise_id="CEDAR-NEST-OTHER"),
            self.row(observation_id="unknown", publication_status="unreviewed"),
        ]
        selected = profiles.select_entity_rows(rows, UID, {ENTERPRISE: [self.link()]})
        self.assertEqual(len(selected), 2)
        self.assertEqual(selected[0]["enterprise_id"], ENTERPRISE)
        self.assertEqual(selected[0]["legal_subject_cedar_uid"], "")
        self.assertEqual(selected[0]["profile_attribution"]["kind"], "related_enterprise")
        self.assertEqual(selected[1]["profile_attribution"]["kind"], "registered_entity")
        self.assertEqual(len(profiles.select_entity_rows(rows, UID, {})), 1)

    def test_anc_can_be_entity_and_need_counterpart_with_one_profile(self):
        result = self.serve(
            records=[self.row(legal_subject_cedar_uid=UID)],
            links=[self.link(relationship_type="same_legal_subject")],
        )
        fact = result["credit_rating_actions"][0]
        self.assertEqual(fact["enterprise_id"], ENTERPRISE)
        self.assertEqual(fact["legal_subject_cedar_uid"], UID)
        self.assertEqual(fact["profile_attribution"]["kind"], "registered_entity")
        self.assertEqual(fact["historical_status"], "historical")
        with self.assertRaises(profiles.UnregisteredEntity):
            profiles.entity_evidence(ENTERPRISE)

    def test_patent_event_uses_its_event_key_and_preserves_both_dates(self):
        row = self.row(event_id="synthetic-event", effective_date="2018-05-01",
                       recordation_date="2025-02-01")
        row.pop("observation_id")
        selected = profiles.select_entity_rows([row], UID, {ENTERPRISE: [self.link()]})
        self.assertEqual(selected[0]["event_id"], "synthetic-event")
        self.assertEqual(selected[0]["effective_date"], "2018-05-01")
        self.assertEqual(selected[0]["recordation_date"], "2025-02-01")

    def test_held_unrelated_missing_and_malformed_links(self):
        for links in (
            [],
            [self.link(hold_reason="unconfirmed")],
            [self.link(profile_cedar_uid="CE-OTHER-00")],
        ):
            self.assertEqual(self.serve(links=links)["status"], "no_evidence")
        for links in (
            [None],
            [self.link(source_url="http://example.org")],
            [self.link(), self.link()],
        ):
            with self.assertRaises(repository.FullReleaseUnavailable):
                self.serve(links=links)
        with self.assertRaises(repository.FullReleaseUnavailable):
            self.serve(returned_pin="b" * 64)

    def test_sources_duplicates_limits_and_bytes_fail_closed(self):
        for source in (
            None,
            "http://example.org",
            "javascript:alert(1)",
            "https://a:b@example.org",
            "https://[",
        ):
            with self.subTest(source=source), self.assertRaises(repository.FullReleaseUnavailable):
                profiles.select_entity_rows(
                    [self.row(source_url=source)], UID, {ENTERPRISE: [self.link()]}
                )
        for rows in ([self.row(), self.row()], [self.row(observation_id="")], [None]):
            with self.assertRaises(repository.FullReleaseUnavailable):
                profiles.select_entity_rows(rows, UID, {ENTERPRISE: [self.link()]})
        with (
            patch.object(profiles, "MAX_PROFILE_ROWS", 1),
            self.assertRaises(repository.FullReleaseUnavailable),
        ):
            profiles.select_entity_rows(
                [self.row(), self.row(observation_id="two")], UID, {ENTERPRISE: [self.link()]}
            )
        for content in (b"{bad}\n", b"x" * (profiles.MAX_ROW_BYTES + 1)):
            with self.assertRaises(repository.FullReleaseUnavailable):
                list(profiles._rows(io.BytesIO(content)))
        with patch.object(
            repository, "grove_full_release", return_value={"content": b"{}\n", "release_id": PIN}
        ):
            self.assertEqual(list(profiles._component_rows("synthetic", PIN)), [{}])
        with (
            patch.object(repository, "grove_full_release", return_value={}),
            self.assertRaises(repository.FullReleaseUnavailable),
        ):
            list(profiles._component_rows("synthetic", PIN))
        with patch.object(profiles, "registered_entity", return_value=None):
            self.assertEqual(profiles.entity_evidence(UID)["status"], "identity_held")
        with (
            patch.object(repository, "_publication_policy", side_effect=ImportError),
            self.assertRaises(repository.FullReleaseUnavailable),
        ):
            profiles.entity_evidence(UID)

    def test_http_requires_live_entitled_account_and_registered_profile(self):
        client = TestClient(app)
        path = f"/press/entities/{UID}/need-evidence"
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
                self.assertEqual(
                    client.get(f"/press/entities/{ENTERPRISE}/need-evidence").status_code, 404
                )
            with patch("cedar_press.app.subscribers.find", side_effect=RuntimeError):
                self.assertEqual(client.get(path).status_code, 503)
        finally:
            app.dependency_overrides.pop(require_session, None)


class EntityRegister(unittest.TestCase):
    def test_only_registered_ids_create_profiles_and_withheld_names_stay_withheld(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "register.json"
            path.write_text(
                json.dumps({"entities": [[UID, "Synthetic ANC", 0], ["CE-00001-00", None, 0]]}),
                encoding="utf-8",
            )
            with patch.object(profiles, "REGISTER_PATH", path):
                self.assertEqual(profiles.registered_entity(UID), "Synthetic ANC")
                self.assertIsNone(profiles.registered_entity("CE-00001-00"))
                with self.assertRaises(profiles.UnregisteredEntity):
                    profiles.registered_entity(ENTERPRISE)
                path.write_text("{}", encoding="utf-8")
                with self.assertRaises(repository.FullReleaseUnavailable):
                    profiles.registered_entity(UID)
