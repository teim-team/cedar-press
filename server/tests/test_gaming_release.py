"""Gaming (Cedar Grove) delivery through the Cedar server adapter.

Cedar consumes Gaming; it does not produce it. The producers, the ID binding
proposal, the leak gate and the release/catalog build moved to Lumecon-data
(branch ``claude/gaming-grove-release``, ``lumecon_data/gaming``) in the
2026-09-24 repository split, together with their tests. What stays here is the
consumer adapter: the reviewed Grove declaration
(``collections.GROVE_RELEASE_COLLECTIONS``), entitlement before any catalog or
artifact access, exact per-component download, redacted audit and rollback.
"""

import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------- server adapter
try:
    from fastapi.testclient import TestClient

    from cedar_press import collections as launch
    from cedar_press import repository, subscribers
    from cedar_press.app import app
    from cedar_press.session import Session, current_session
    HAVE_SERVER = True
except ImportError:
    HAVE_SERVER = False

SERVED = ("gaming_regional_revenue", "gaming_regulatory_events")


@unittest.skipUnless(HAVE_SERVER, "requires the Cedar server development dependencies")
class GamingServerDeliveryTest(unittest.TestCase):
    """The reviewed Grove declaration serves each pinned component exactly.

    Two synthetic components in one ``cedar_grove`` catalog pinned at
    CEDAR_GROVE_RELEASE_CATALOG; the existing tier model (grove/tree reach the
    grove shelf) decides access before any catalog or artifact is read."""

    URL = "/press/collections/gaming/full-download"

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.catalog = Path(self.temp.name) / "grove-catalog.json"
        tables = json.loads((ROOT / "data/cedar/field_map.json").read_text(encoding="utf-8"))["tables"]
        self.tables = {k: v for k, v in tables.items() if v.get("collection") != "gaming"}
        self.headers = {
            "gaming_regional_revenue": ["revenue_observation_id", "region_name", "ggr_nominal_usd", "research_note"],
            "gaming_regulatory_events": ["event_id", "gaming_facility_id", "event_date", "research_note"],
        }
        self.keys = {"gaming_regional_revenue": "revenue_observation_id", "gaming_regulatory_events": "event_id"}
        for stem, header in self.headers.items():
            self.tables["gaming/" + stem] = {"collection": "gaming", "order": header}
        self.version("a", "100")
        self.product = "cedar_grove"
        self.write_catalog()
        self.fetched = []
        for patcher in (
            patch.dict(os.environ, {"CEDAR_GROVE_RELEASE_CATALOG": str(self.catalog)}),
            patch.object(repository, "_field_map_tables", side_effect=lambda: self.tables),
            patch.object(repository, "_release_bytes", side_effect=self.download),
            patch.object(repository, "_release_json", side_effect=self.response),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        os.environ.pop("CEDAR_PRESS_RELEASE_CATALOG", None)
        self.subscriber = patch.object(subscribers, "find", return_value=subscribers.Subscriber(
            "grove-fixture@example.invalid", "grove", "fixture"))
        self.account = self.subscriber.start()
        self.addCleanup(self.subscriber.stop)
        self.addCleanup(app.dependency_overrides.clear)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def version(self, letter, value):
        """One pinned version of BOTH components (rids derived from `letter`)."""
        # The upstream store keeps every version; the catalog decides which one.
        self.upstream = getattr(self, "upstream", {})
        self.content, self.pins = {}, []
        for i, (stem, header) in enumerate(sorted(self.headers.items())):
            row = {name: None for name in header}
            row[self.keys[stem]] = f"{stem}-{letter}"
            row[header[1]] = value
            content = repository._canonical_bytes(row)
            rid = hashlib.sha256(f"{letter}{i}".encode()).hexdigest()
            pin = {"dataset_id": "gaming--" + stem, "release_id": rid, "record_count": 1,
                   "fields": [{"name": n, "type": "string", "nullable": n != self.keys[stem]} for n in header],
                   "rights": {"publication_class": "publishable", "redistribution": True},
                   "synthetic": False}
            manifest = {**pin, "schema_version": 1, "primary_key": [self.keys[stem]],
                        "files": {"records.jsonl": {"sha256": hashlib.sha256(content).hexdigest(),
                                                    "bytes": len(content)}}}
            pin["manifest_sha256"] = hashlib.sha256(repository._canonical_bytes(manifest)).hexdigest()
            self.content[stem] = content
            self.upstream[(pin["dataset_id"], rid)] = (manifest, content)
            self.pins.append(pin)
        self.rid = {pin["dataset_id"].split("--")[1]: pin["release_id"] for pin in self.pins}

    def write_catalog(self, path=None):
        value = {"schema_version": 1, "product": self.product, "entitlement_required": True,
                 "collections": self.pins}
        value["catalog_id"] = hashlib.sha256(repository._canonical_bytes(value)).hexdigest()
        (path or self.catalog).write_text(json.dumps(value), encoding="utf-8")

    def _stored(self, path):
        parts = path.split("/")                 # /v1/datasets/<id>/releases/<rid>/...
        self.fetched.append(path)
        return self.upstream[(parts[3], parts[5])]

    def response(self, path):
        return copy.deepcopy(self._stored(path)[0])

    def download(self, path, limit=None):
        return self._stored(path)[1]

    def session(self, tier, email="grove-fixture@example.invalid"):
        app.dependency_overrides[current_session] = (
            (lambda: None) if tier is None else (lambda: Session(email, tier)))

    def get(self, component, release_id=None):
        params = {"release_id": release_id or self.rid.get(component, "c" * 64)}
        if component is not None:
            params["component"] = component
        with self.assertLogs("cedar_press.download", level="INFO") as logs:
            response = self.client.get(self.URL, params=params)
        self.assertNotIn("grove-fixture@example", " ".join(logs.output))
        return response, [json.loads(line.split(":", 2)[2]) for line in logs.output]

    def test_declaration_is_the_existing_grove_shelf_and_storefront_is_unchanged(self):
        self.assertEqual([e["id"] for e in launch.GROVE_RELEASE_COLLECTIONS], ["gaming"])
        self.assertEqual({e["shelf"] for e in launch.GROVE_RELEASE_COLLECTIONS}, {"grove"})
        self.assertEqual(repository.grove_components("gaming"), SERVED)
        self.assertEqual(repository.grove_components("legislation"), ())
        for tier in ("press", "press_pro", "grove", "tree", "unknown"):
            with self.subTest(tier=tier):
                # The storefront still neither sells nor previews Gaming ...
                self.assertFalse(repository.may_open(tier, "gaming"))
                self.assertNotIn("gaming", [c["id"] for c in repository.collections_for(tier)])
                # ... and every Press collection's full-release rule is may_open.
                for dataset in launch.LAUNCH_COLLECTION:
                    self.assertEqual(repository.may_download_full(tier, dataset.id),
                                     repository.may_open(tier, dataset.id))
            self.assertEqual(repository.may_download_full(tier, "gaming"), tier in ("grove", "tree"))
        self.assertFalse(repository.is_sold("gaming"))
        self.session("grove")
        self.assertEqual(self.client.get("/press/collections/gaming/download").status_code, 403)

    def test_each_component_is_served_exactly_with_named_headers_and_audit(self):
        for tier in ("grove", "tree"):
            self.session(tier)
            self.account.return_value = subscribers.Subscriber("grove-fixture@example.invalid", tier, "fixture")
            for stem in SERVED:
                with self.subTest(tier=tier, component=stem):
                    response, events = self.get(stem)
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(response.content, self.content[stem])
                    self.assertEqual(response.headers["x-cedar-sha256"],
                                     hashlib.sha256(self.content[stem]).hexdigest())
                    self.assertEqual(response.headers["x-cedar-release"], self.rid[stem])
                    self.assertEqual(response.headers["x-cedar-component"], stem)
                    self.assertIn(f'filename="gaming--{stem}-{self.rid[stem]}.jsonl"',
                                  response.headers["content-disposition"])
                    self.assertEqual(response.headers["x-cedar-citation"],
                                     f"Cedar Grove gaming/{stem}, release {self.rid[stem]}")
                    self.assertEqual((events[0]["outcome"], events[0]["collection_id"], events[0]["component"]),
                                     ("authorized_prepared", "gaming", stem))
        # A component's release ID never opens its sibling.
        response, _ = self.get(SERVED[0], release_id=self.rid[SERVED[1]])
        self.assertEqual(response.status_code, 503)
        metadata = repository.grove_release_metadata("gaming")
        self.assertEqual([m["table_id"] for m in metadata], list(SERVED))
        self.assertTrue(all(m["download_path"].endswith("&component=" + m["table_id"]) for m in metadata))

    def test_wrong_tier_anonymous_and_stale_accounts_are_denied_before_any_access(self):
        for tier, status in [(None, 401), ("press", 403), ("press_pro", 403)]:
            with self.subTest(tier=tier):
                self.session(tier)
                response, events = self.get(SERVED[0])
                self.assertEqual(response.status_code, status)
                self.assertEqual(events[0]["component"], SERVED[0])
        # Stale account: a grove cookie after a downgrade, a removal and an
        # account-store outage never reaches the catalog or an artifact.
        self.session("grove")
        for account, error, status in [
            (subscribers.Subscriber("grove-fixture@example.invalid", "press_pro", "fixture"), None, 403),
            (None, None, 401),
            (None, RuntimeError("secret-store-detail"), 503),
        ]:
            with self.subTest(status=status):
                self.account.return_value, self.account.side_effect = account, error
                response, events = self.get(SERVED[1])
                self.assertEqual(response.status_code, status)
                self.assertNotIn("secret-store-detail", response.text + json.dumps(events))
        self.assertEqual(self.fetched, [])

    def test_missing_unknown_or_malformed_component_is_refused_and_redacted(self):
        self.session("grove")
        response, events = self.get(None)
        self.assertEqual((response.status_code, events[0]["outcome"]), (400, "invalid_release_request"))
        for component in ("private-secret-token", "gaming_facilities", "../legislation"):
            with self.subTest(component=component):
                response, events = self.get(component, release_id="c" * 64)
                self.assertEqual(response.status_code, 503)
                self.assertEqual(events[0]["component"], "unknown")
                self.assertNotIn(component, json.dumps(events))
        self.assertEqual(self.fetched, [])

    def test_rollback_restores_every_component_and_stale_pins_are_refused(self):
        self.session("grove")
        approved_a = self.catalog.read_bytes()
        content_a, rid_a = dict(self.content), dict(self.rid)
        self.version("b", "200")
        self.write_catalog()
        for stem in SERVED:
            response, _ = self.get(stem)
            self.assertEqual((response.status_code, response.content), (200, self.content[stem]))
            # A pin the approved catalog no longer names is refused.
            self.assertEqual(self.get(stem, release_id=rid_a[stem])[0].status_code, 503)
        self.catalog.write_text("{}")
        self.assertEqual(self.get(SERVED[0])[0].status_code, 503)
        # Rollback: reselect catalog A; both components serve A's exact bytes.
        self.catalog.write_bytes(approved_a)
        for stem in SERVED:
            response, _ = self.get(stem, release_id=rid_a[stem])
            self.assertEqual((response.status_code, response.content), (200, content_a[stem]))

    def test_catalog_product_and_pin_location_are_per_product(self):
        self.session("grove")
        # A cedar_press-product catalog at the Grove pin is refused ...
        self.product = "cedar_press"
        self.write_catalog()
        self.assertEqual(self.get(SERVED[0])[0].status_code, 503)
        # ... and a cedar_grove catalog at the Press pin serves nothing Grove.
        self.product = "cedar_grove"
        press_pin = Path(self.temp.name) / "press-catalog.json"
        self.write_catalog(press_pin)
        with patch.dict(os.environ, {"CEDAR_PRESS_RELEASE_CATALOG": str(press_pin)}):
            os.environ.pop("CEDAR_GROVE_RELEASE_CATALOG")
            self.assertEqual(self.get(SERVED[0])[0].status_code, 503)
            with self.assertRaises(repository.FullReleaseUnavailable):
                repository.full_release("legislation", "a" * 64)
        self.assertEqual(self.fetched, [])


if __name__ == "__main__":
    unittest.main()
