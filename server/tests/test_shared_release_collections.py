"""Synthetic Giving/PLOT component consumers and the real 15-target entitlement scope."""

import copy
import hashlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from cedar_press import governed_collections, repository, subscribers
from cedar_press.app import app
from cedar_press.session import Session, current_session


class SharedCollectionReleaseTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.addCleanup(app.dependency_overrides.clear)
        self.account = patch.object(
            subscribers,
            "find",
            return_value=subscribers.Subscriber(
                "synthetic@example.invalid", "press_pro", "fixture"
            ),
        )
        self.account.start()
        self.addCleanup(self.account.stop)

    def test_collection_manifests_have_a_separate_bounded_transport_limit(self):
        # Full PLOT has 163 parts and a 14 MB manifest. Catalogs remain small.
        payload = json.dumps({"fixture": "x" * (4 * 1024 * 1024)}).encode()
        with (
            patch.object(repository, "_release_response", return_value=io.BytesIO(payload)),
            self.assertRaisesRegex(repository.FullReleaseUnavailable, "safety limit"),
        ):
            repository._release_json("/catalog")
        with patch.object(repository, "_release_response", return_value=io.BytesIO(payload)):
            self.assertEqual(
                len(
                    repository._release_json(
                        "/manifest", limit=repository.MAX_COLLECTION_MANIFEST_BYTES
                    )["fixture"]
                ),
                4 * 1024 * 1024,
            )

        class TooLarge:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self, size):
                return b" " * size

        with (
            patch.object(repository, "_release_response", return_value=TooLarge()),
            self.assertRaisesRegex(repository.FullReleaseUnavailable, "safety limit"),
        ):
            repository._release_json("/manifest", limit=repository.MAX_COLLECTION_MANIFEST_BYTES)

    def session(self, tier):
        app.dependency_overrides[current_session] = lambda: Session(
            "synthetic@example.invalid", tier
        )

    def fixture(
        self,
        collection="plot",
        component="environmental_events",
        rights=True,
        release_class="production",
        columns=None,
    ):
        if columns is None:
            columns = governed_collections.COMPONENT_COLUMNS[f"{collection}/{component}"]
        row = dict.fromkeys(columns, None)
        row[columns[0]] = "SYNTHETIC-1"
        if "amount_exact_usd" in row:
            row["amount_exact_usd"] = "0.10"
        content = repository._canonical_bytes(row)
        manifest = {
            "collection_id": collection,
            "release_id": "c" * 64,
            "release_kind": "collection",
            "product": "cedar_press",
            "schema_version": 1,
            "release_class": release_class,
            "synthetic": True,
            "components": {
                component: {
                    "fields": [{"name": name, "type": "string"} for name in columns],
                    "rights": {"publication_class": "publishable", "redistribution": rights},
                    "download_permitted": rights,
                    "primary_key": [columns[0]],
                    "record_count": 1,
                    "files": {
                        "records.jsonl": {
                            "bytes": len(content),
                            "sha256": hashlib.sha256(content).hexdigest(),
                        }
                    },
                }
            },
        }
        manifest_sha = hashlib.sha256(repository._canonical_bytes(manifest)).hexdigest()
        catalog = {
            "schema_version": 1,
            "product": "cedar_press",
            "entitlement_required": True,
            "catalog_kind": "collection_releases",
            "collection_releases": [
                {
                    "collection_id": collection,
                    "release_id": "c" * 64,
                    "manifest_sha256": manifest_sha,
                    "manifest_path": f"/v1/collections/{collection}/releases/{'c' * 64}/manifest",
                }
            ],
        }
        catalog_id = hashlib.sha256(repository._canonical_bytes(catalog)).hexdigest()
        catalog["catalog_id"] = catalog_id
        catalog_bytes = repository._canonical_bytes(catalog)
        catalog_path = self.root / "catalog.json"
        catalog_path.write_bytes(catalog_bytes)
        pin = {
            "collection_id": collection,
            "release_id": "c" * 64,
            "manifest_sha256": manifest_sha,
            "catalog_id": catalog_id,
            "catalog_sha256": hashlib.sha256(catalog_bytes).hexdigest(),
        }
        pin_path = self.root / "pin.json"
        pin_path.write_bytes(
            repository._canonical_bytes(
                {"schema_version": 1, "product": "cedar_press", "pins": {collection: pin}}
            )
        )
        for patcher in (
            patch.dict(
                os.environ,
                {
                    "CEDAR_PRESS_COMPONENT_RELEASE_PIN": str(pin_path),
                    "CEDAR_PRESS_COMPONENT_RELEASE_CATALOG": str(catalog_path),
                    "CEDAR_PRESS_ENVIRONMENT": "development",
                    "CEDAR_GROVE_ENVIRONMENT": "review",
                },
            ),
            patch.object(repository, "GROVE_SERVE_SYNTHETIC", True),
            patch.object(repository, "_release_json", return_value=manifest),
            patch.object(
                repository, "_release_response", side_effect=lambda _: io.BytesIO(content)
            ),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        return manifest, pin, content

    def test_discovery_verifies_manifest_once_per_request_and_rejects_later_tampering(self):
        manifest, _, _ = self.fixture()
        with (
            patch.object(repository, "_release_json", return_value=manifest) as fetch,
            patch.object(repository, "_grove_catalog", wraps=repository._grove_catalog) as catalog,
            patch.object(
                repository, "_release_response", side_effect=AssertionError("No row download")
            ),
        ):
            first = repository.grove_release_metadata("plot")
            self.assertEqual(len(first), len(repository.grove_components("plot")))
            self.assertEqual(sum(row.get("record_count", 0) for row in first), 1)
            self.assertEqual((fetch.call_count, catalog.call_count), (1, 1))
            repository.grove_release_metadata("plot")
            self.assertEqual((fetch.call_count, catalog.call_count), (2, 2))
            manifest["components"]["environmental_events"]["record_count"] += 1
            changed = repository.grove_release_metadata("plot")
            self.assertTrue(all(row["status"] == "unavailable" for row in changed))
            self.assertEqual(fetch.call_count, 3)

    def test_need_discovery_is_not_held_before_the_pin(self):
        # Owner ruling 2026-10-04: NEED is not held, so discovery reaches the
        # release pin like any other collection.
        with patch.object(
            repository, "grove_release_pin", side_effect=repository.GroveReleaseNotPinned("x")
        ) as pin:
            repository.grove_release_metadata("need")
        pin.assert_called_once_with("need")

    def test_need_preview_downloads_without_a_reviewed_base_proof(self):
        # Owner ruling 2026-10-04 (Elijah Moreno): the NEED preview publishes
        # like any other collection's; the reviewed-base proof is not consulted.
        self.session("press_pro")
        with patch(
            "cedar_press.need_preview.current_need_preview_permitted",
            side_effect=AssertionError("proof must not gate the preview"),
        ):
            response = self.client.get("/press/collections/need/download")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("cite_as", response.text.splitlines()[0])

    def test_sixteen_targets_preserve_tiers_and_never_invent_samples(self):
        with (
            patch.object(repository, "grove_release_metadata", return_value=None),
            patch.object(repository, "full_release_metadata", return_value=None),
        ):
            for tier in ("press", "press_pro", "grove", "tree"):
                target = repository.release_targets_for(tier)
                self.assertEqual((target["target_count"], target["press_target_count"]), (16, 14))
                ids = {entry["id"] for entry in target["collections"]}
                self.assertIn("foundation-corporate-giving", ids)
                self.assertEqual("need" in ids, tier != "press")
                self.assertEqual(
                    sum(entry["id"] == "need" for entry in target["collections"]),
                    int(tier != "press"),
                )
                self.assertNotIn("entity-register", ids)
                self.assertEqual("plot" in ids, tier != "press")
                self.assertEqual("gaming" in ids, tier in {"grove", "tree"})
                self.assertEqual("infrastructure" in ids, tier in {"grove", "tree"})
                self.assertTrue(
                    all(
                        entry["sample"] is None and entry["release"] is None
                        for entry in target["collections"]
                    )
                )
        self.assertFalse(repository.may_download_full("guest", "plot"))
        self.assertFalse(repository.is_grove_release("plot"))
        self.assertTrue(repository.is_component_release("plot"))
        self.assertTrue(repository.is_component_release("need"))
        self.assertIn("enterprises", repository.grove_components("need"))

    def test_unpinned_shared_collection_is_explicitly_unavailable(self):
        for collection in governed_collections.SHARED_COLLECTIONS:
            with self.assertRaises(repository.GroveReleaseNotPinned):
                repository.grove_release_pin(collection)
            metadata = repository.grove_release_metadata(collection)
            if collection == "need":
                # The collection-wide hold is checked before any pin is read.
                self.assertTrue(metadata)
                self.assertTrue(all(item["status"] == "unavailable" for item in metadata))
            else:
                self.assertIsNone(metadata)

    def test_plot_component_download_uses_existing_hash_path(self):
        _manifest, _pin, content = self.fixture()
        self.session("press_pro")
        response = self.client.get(
            "/press/collections/plot/full-download",
            params={"release_id": "c" * 64, "component": "environmental_events"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, content)
        self.assertEqual(response.headers["X-Cedar-Component"], "environmental_events")
        self.assertIn("Cedar Press", response.headers["X-Cedar-Citation"])

    def test_federal_document_and_participant_components_preserve_standard_access(self):
        self.session("press")
        for component in ("federal_actions", "consultation_participants"):
            columns = governed_collections.presentation("federal-register", component)["order"]
            _, _, content = self.fixture("federal-register", component, columns=columns)
            response = self.client.get(
                "/press/collections/federal-register/full-download",
                params={"release_id": "c" * 64, "component": component},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, content)
            self.assertEqual(response.headers["X-Cedar-Component"], component)

    def test_legacy_federal_download_still_uses_its_explicit_native_pin(self):
        self.session("press")
        content = b'{"consultation_record_key":"SYNTHETIC"}\n'
        released = {
            "content": content,
            "release_id": "b" * 64,
            "sha256": hashlib.sha256(content).hexdigest(),
            "record_count": 1,
            "citation": "Synthetic compatibility fixture",
            "filename": "fixture.jsonl",
            "media_type": "application/x-ndjson",
        }
        with (
            patch.object(repository, "full_release", return_value=released) as native,
            patch.object(
                repository, "grove_full_release", side_effect=AssertionError("No replacement")
            ),
        ):
            response = self.client.get(
                "/press/collections/federal-register/full-download",
                params={"release_id": "b" * 64},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, content)
        native.assert_called_once_with("federal-register", "b" * 64)

    def test_press_tier_cannot_fetch_plot_and_stale_account_cannot_fetch(self):
        self.fixture()
        for cookie_tier, account_tier in (("press", "press_pro"), ("press_pro", "press")):
            self.session(cookie_tier)
            with (
                patch.object(
                    subscribers,
                    "find",
                    return_value=subscribers.Subscriber(
                        "synthetic@example.invalid", account_tier, "fixture"
                    ),
                ),
                patch.object(
                    repository, "_release_json", side_effect=AssertionError("unauthorized fetch")
                ),
            ):
                response = self.client.get(
                    "/press/collections/plot/full-download",
                    params={"release_id": "c" * 64, "component": "environmental_events"},
                )
                self.assertEqual(response.status_code, 403)

    def test_only_tenant_private_rights_are_typed_as_publication_holds(self):
        # Owner ruling 2026-10-04: restricted rights are provenance.
        manifest, _, _ = self.fixture(rights=False)
        repository.grove_component_contract(manifest, "plot", "environmental_events")
        rights = manifest["components"]["environmental_events"]["rights"]
        rights["publication_class"] = "tenant_private"
        with self.assertRaises(repository.ComponentPublicationHeld):
            repository.grove_component_contract(manifest, "plot", "environmental_events")
        manifest["components"]["environmental_events"]["rights"] = "malformed"
        with self.assertRaises(repository.FullReleaseUnavailable) as raised:
            repository.grove_component_contract(manifest, "plot", "environmental_events")
        self.assertNotIsInstance(raised.exception, repository.ComponentPublicationHeld)

    def test_component_metadata_holds_refuse_raw_and_csv_before_artifact_reads(self):
        manifest, pin, _ = self.fixture()
        contract = manifest["components"]["environmental_events"]
        self.session("press_pro")
        # Owner ruling 2026-10-04: only `internal_only` still refuses; a
        # publication_hold flag or a review status no longer does (see
        # test_review_states_no_longer_hold_a_component).
        holds = ({"internal_only": True},)
        with (
            patch.object(repository, "_grove_manifest", return_value=manifest),
            patch.object(repository, "_release_response") as rows,
        ):
            for metadata in holds:
                with self.subTest(metadata=metadata):
                    contract["metadata"] = metadata
                    with self.assertRaises(repository.ComponentPublicationHeld):
                        repository.grove_component_contract(
                            manifest, "plot", "environmental_events"
                        )
                    for route in ("full-download", "spreadsheet-download"):
                        params = {"release_id": pin["release_id"]}
                        if route == "full-download":
                            params["component"] = "environmental_events"
                        response = self.client.get(
                            f"/press/collections/plot/{route}", params=params
                        )
                        self.assertEqual(response.status_code, 503)
                    rows.assert_not_called()

    def test_review_states_no_longer_hold_a_component(self):
        manifest, _, _ = self.fixture()
        contract = manifest["components"]["environmental_events"]
        for metadata in (
            {"publication_hold": True},
            {"publication_status": "held"},
            {"publication_status": "contested"},
            {"publication_status": "withheld"},
            {"publication_status": "unreviewed"},
        ):
            with self.subTest(metadata=metadata):
                contract["metadata"] = metadata
                repository.grove_component_contract(manifest, "plot", "environmental_events")

    def test_malformed_component_metadata_fails_closed_in_both_download_routes(self):
        manifest, pin, _ = self.fixture()
        contract = manifest["components"]["environmental_events"]
        self.session("press_pro")
        invalid = (
            None,
            [],
            "",
            True,
            {"internal_only": "false"},
            {"publication_status": []},
            {"publication_status": ""},
        )
        with (
            patch.object(repository, "_grove_manifest", return_value=manifest),
            patch.object(repository, "_release_response") as rows,
        ):
            for metadata in invalid:
                with self.subTest(metadata=metadata):
                    contract["metadata"] = metadata
                    with self.assertRaises(repository.FullReleaseUnavailable) as raised:
                        repository.grove_component_contract(
                            manifest, "plot", "environmental_events"
                        )
                    self.assertNotIsInstance(raised.exception, repository.ComponentPublicationHeld)
                    for route in ("full-download", "spreadsheet-download"):
                        params = {"release_id": pin["release_id"]}
                        if route == "full-download":
                            params["component"] = "environmental_events"
                        response = self.client.get(
                            f"/press/collections/plot/{route}", params=params
                        )
                        self.assertEqual(response.status_code, 503)
                    rows.assert_not_called()

    def test_explicit_eligible_metadata_preserves_raw_bytes_and_csv_rows(self):
        manifest, pin, content = self.fixture()
        manifest["components"]["environmental_events"]["metadata"] = {
            "internal_only": False,
            "publication_hold": False,
            "publication_status": "eligible",
        }
        self.session("press_pro")
        with patch.object(repository, "_grove_manifest", return_value=manifest):
            response = self.client.get(
                "/press/collections/plot/full-download",
                params={
                    "release_id": pin["release_id"],
                    "component": "environmental_events",
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, content)
            csv_response = self.client.get(
                "/press/collections/plot/spreadsheet-download",
                params={"release_id": pin["release_id"]},
            )
        # Environmental events are not PLOT's customer grain (owner rule 4,
        # 2026-10-04): with no land observations there is no customer table.
        self.assertEqual(csv_response.status_code, 503)

    def test_publication_fields_must_name_declared_columns(self):
        manifest, _, _ = self.fixture()
        contract = manifest["components"]["environmental_events"]
        for changes in (
            {"publication_status_field": []},
            {"publication_status_field": "missing"},
            {"status_value_fields": None},
            {"status_value_fields": "environmental_event_id"},
            {"status_value_fields": ["missing"]},
            {"status_value_fields": ["environmental_event_id"] * 2},
        ):
            with self.subTest(changes=changes):
                changed = copy.deepcopy(manifest)
                changed["components"]["environmental_events"].update(changes)
                with self.assertRaisesRegex(
                    repository.FullReleaseUnavailable, "publication fields"
                ):
                    repository.grove_component_contract(changed, "plot", "environmental_events")
        contract["publication_status_field"] = "environmental_event_id"
        contract["status_value_fields"] = ["environmental_event_id"]
        repository.grove_component_contract(manifest, "plot", "environmental_events")

    def test_owner_ruling_giving_rights_status_downloads_for_entitled_users(self):
        # Owner ruling 2026-10-04 (Elijah Moreno): Lumecon transforms the data
        # it publishes; a rights-status component publishes.
        _manifest, _pin, content = self.fixture(
            "foundation-corporate-giving", "reviewed_disclosures", rights=False
        )
        self.session("press")
        response = self.client.get(
            "/press/collections/foundation-corporate-giving/full-download",
            params={"release_id": "c" * 64, "component": "reviewed_disclosures"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.content, content)

    def test_authorized_giving_preserves_exact_decimal_text_and_component_audit(self):
        _manifest, _pin, content = self.fixture(
            "foundation-corporate-giving", "reviewed_disclosures"
        )
        self.session("press")
        with self.assertLogs("cedar_press.download", level="INFO") as audit:
            response = self.client.get(
                "/press/collections/foundation-corporate-giving/full-download",
                params={"release_id": "c" * 64, "component": "reviewed_disclosures"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, content)
        self.assertIn(b'"amount_exact_usd":"0.10"', response.content)
        self.assertIn('"collection_id": "foundation-corporate-giving"', audit.output[0])
        self.assertIn('"component": "reviewed_disclosures"', audit.output[0])

    def test_tampered_component_and_metadata_refuse(self):
        manifest, pin, _content = self.fixture()
        with (
            patch.object(
                repository, "_release_response", side_effect=lambda _: io.BytesIO(b"changed")
            ),
            self.assertRaisesRegex(repository.FullReleaseUnavailable, "Partition size"),
        ):
            repository.grove_full_release("plot", "c" * 64, component="environmental_events")
        changed = copy.deepcopy(manifest)
        changed["components"]["environmental_events"]["record_count"] = 2
        with (
            patch.object(repository, "_release_json", return_value=changed),
            self.assertRaisesRegex(repository.FullReleaseUnavailable, "Manifest differs"),
        ):
            repository._grove_manifest(pin)

    def test_giving_appended_columns_and_prior_pinned_schema_both_work(self):
        collection, component = "foundation-corporate-giving", "reviewed_disclosures"
        declaration = governed_collections.presentation(collection, component)
        for columns in [declaration["order"], *declaration["compatible_orders"]]:
            with self.subTest(columns=len(columns)):
                manifest, _pin, content = self.fixture(collection, component, columns=columns)
                self.session("press")
                response = self.client.get(
                    "/press/collections/foundation-corporate-giving/full-download",
                    params={"release_id": "c" * 64, "component": component},
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content, content)
                manifest["components"][component]["fields"].append({"name": "unreviewed_extra"})
                with self.assertRaisesRegex(repository.FullReleaseUnavailable, "field map"):
                    repository.grove_component_contract(manifest, collection, component)

    def test_rehearsal_remains_refused_in_production(self):
        _manifest, pin, _content = self.fixture(release_class="rehearsal")
        with (
            patch.dict(os.environ, {"CEDAR_PRESS_ENVIRONMENT": "production"}),
            self.assertRaisesRegex(repository.FullReleaseUnavailable, "never enabled"),
        ):
            repository._grove_manifest(pin)

    def test_schema_drift_and_unknown_component_refuse(self):
        manifest, _pin, _content = self.fixture()
        manifest["components"]["environmental_events"]["fields"].append({"name": "raw_path"})
        with self.assertRaisesRegex(repository.FullReleaseUnavailable, "field map"):
            repository.grove_component_contract(manifest, "plot", "environmental_events")
        with self.assertRaisesRegex(repository.FullReleaseUnavailable, "not offered"):
            repository.grove_full_release("plot", "c" * 64, component="parcels")

    def test_registry_endpoint_requires_authentication(self):
        app.dependency_overrides[current_session] = lambda: None
        self.assertEqual(self.client.get("/press/release-collections").status_code, 401)
        self.session("grove")
        with (
            patch.object(repository, "grove_release_metadata", return_value=None),
            patch.object(repository, "full_release_metadata", return_value=None),
        ):
            response = self.client.get("/press/release-collections")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["collections"]), 14)
        self.assertNotIn("gaming", [entry["id"] for entry in response.json()["collections"]])
        self.assertEqual(response.headers["cache-control"], "private, no-store")

    def test_matching_presentation_never_clears_held_or_missing_field_rights(self):
        for collection in ("gaming", "plot", "foundation-corporate-giving", "need"):
            for rights in (
                {"id": "PUBLIC_OFFICIAL", "secret": "INTERNAL_VENDOR"},
                {"id": "PUBLIC_OFFICIAL", "secret": "UNRECOGNIZED"},
                {"id": "PUBLIC_OFFICIAL"},
                {},
            ):
                with self.subTest(collection=collection, rights=rights):
                    # NEED is checked like every other collection (owner
                    # ruling 2026-10-04: no NEED publication hold).
                    refusal = repository.FullReleaseUnavailable
                    # Owner ruling 2026-10-04: a non-public field rights class
                    # is provenance, so a complete declaration passes the
                    # rights step and stops later, on this fixture's missing
                    # row identity; an incomplete declaration still refuses.
                    reason = "incomplete|Missing declared row identity"
                    entry = {
                        "collection": collection,
                        "order": ["id", "secret"],
                        "fields": [
                            {"column": name, "decision": "keep", "rights_class": value}
                            for name, value in rights.items()
                        ],
                    }
                    contract = {
                        "rights": {"publication_class": "publishable", "redistribution": True},
                        "download_permitted": True,
                        "fields": [{"name": "id"}, {"name": "secret"}],
                        "metadata": {"field_rights": rights},
                    }
                    with (
                        patch.object(
                            repository,
                            "_field_map_tables",
                            return_value={f"{collection}/facts": entry},
                        ),
                        self.assertRaisesRegex(refusal, reason),
                    ):
                        repository.grove_component_contract(
                            {"components": {"facts": contract}}, collection, "facts"
                        )

    def test_real_rehearsal_refuses_inherited_database_before_imports_or_artifacts(self):
        path = Path(__file__).with_name("shared_collection_rehearsal.py")
        spec = importlib.util.spec_from_file_location("isolated_shared_rehearsal", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for variable in ("DATABASE_URL", "CEDAR_PRESS_DB"):
            with (
                patch.dict(os.environ, {variable: "not-a-real-connection"}),
                self.assertRaisesRegex(SystemExit, "isolated environment"),
            ):
                module.main()


class CurrentReleaseFeedTest(unittest.TestCase):
    def target(self, collection="funding"):
        part = {
            "kind": "full",
            "release_id": "a" * 64,
            "manifest_sha256": "b" * 64,
            "record_count": 17,
        }
        return {
            "id": collection,
            "name": "Fixture",
            "shelf": "standard",
            "release": part,
            "spreadsheet": {"format": "csv", **part, "record_count": 17, "kind": "spreadsheet"},
        }

    def feed(self, targets, tier="press_pro"):
        with patch.object(
            repository, "release_targets_for", return_value={"collections": targets}
        ) as lookup:
            result = repository.releases(tier)
        lookup.assert_called_once_with(tier)
        return result

    def test_current_release_has_no_invented_publication_date(self):
        row = self.feed([self.target()])["releases"][0]
        self.assertEqual(row["record_count"], 17)
        self.assertIsNone(row["updated"])
        self.assertIsNone(row["history"][0]["date"])
        self.assertEqual(row["history"][0]["date_basis"], "not_recorded")

    def test_overlapping_components_are_not_summed(self):
        target = self.target()
        part = target["release"]
        target["release"] = [
            part,
            {**part, "record_count": 90},
            {"status": "unavailable", "record_count": 9999},
        ]
        row = self.feed([target])["releases"][0]
        self.assertEqual(row["record_count"], 17)
        self.assertIn("Some collection components are unavailable.", row["history"][0]["changed"])
        self.assertNotIn("9999", str(row))

    def test_conflicting_versions_and_manifests_do_not_make_a_current_entry(self):
        for key in ("release_id", "manifest_sha256"):
            target = self.target()
            part = target["release"]
            target["release"] = [part, {**part, key: "c" * 64}]
            self.assertEqual(self.feed([target])["releases"], [])

    def test_missing_malformed_and_grove_releases_stay_out(self):
        for supplied in (
            None,
            {"kind": "full", "status": "unavailable"},
            {"kind": "full", "release_id": "legacy"},
        ):
            target = self.target()
            target["release"] = supplied
            self.assertEqual(self.feed([target])["releases"], [])
        self.assertEqual(
            self.feed([self.target("gaming"), self.target("infrastructure")])["releases"], []
        )

    def test_spreadsheet_count_requires_matching_release_and_manifest(self):
        for key in ("release_id", "manifest_sha256"):
            target = self.target()
            target["spreadsheet"][key] = "c" * 64
            row = self.feed([target])["releases"][0]
            self.assertNotIn("record_count", row)
            self.assertNotIn("17", str(row["history"]))

    def test_preview_date_requires_both_exact_source_hashes(self):
        target = self.target()
        facts = {"release_id": "a" * 64, "manifest_sha256": "b" * 64}
        with patch.object(repository.launch, "collection_cedar_facts", return_value=facts):
            row = self.feed([target])["releases"][0]
            self.assertIn("preview_updated", row)
            self.assertIsNone(row["updated"])
        for key in facts:
            with patch.object(
                repository.launch, "collection_cedar_facts", return_value={**facts, key: "c" * 64}
            ):
                self.assertNotIn("preview_updated", self.feed([target])["releases"][0])

    def test_endpoint_uses_fresh_subscription_and_refuses_failed_auth(self):
        self.addCleanup(app.dependency_overrides.clear)
        app.dependency_overrides[current_session] = lambda: Session(
            "feed@example.invalid", "press_pro"
        )
        payload = {"source": "verified_current", "history_complete": False, "releases": []}
        with (
            TestClient(app) as client,
            patch.object(repository, "releases", return_value=payload) as service,
        ):
            with patch.object(
                subscribers,
                "find",
                return_value=subscribers.Subscriber("feed@example.invalid", "press", "fixture"),
            ):
                response = client.get("/press/releases")
                self.assertEqual(response.status_code, 200)
                service.assert_called_once_with("press")
                self.assertEqual(response.headers["cache-control"], "private, no-store")
            with patch.object(subscribers, "find", return_value=None):
                self.assertEqual(client.get("/press/releases").status_code, 401)
            with patch.object(subscribers, "find", side_effect=RuntimeError("unavailable")):
                self.assertEqual(client.get("/press/releases").status_code, 503)
            app.dependency_overrides[current_session] = lambda: None
            self.assertEqual(client.get("/press/releases").status_code, 401)
