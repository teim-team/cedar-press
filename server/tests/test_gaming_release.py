"""Gaming (Cedar Grove) as a CONSUMER of one pinned Lumecon-data release.

Cedar consumes Gaming; it does not produce it. The producers, the ID binding
proposal, the leak gate and the release/catalog build moved to Lumecon-data
(branch ``claude/gaming-grove-release``, ``lumecon_data/gaming``) in the
2026-09-24 repository split. Lumecon publishes ONE immutable Gaming release
(one collection-level manifest, one catalog entry, components addressable
under it); Cedar pins it in ``data/cedar/grove_release_pin.json`` and serves
authorized components of exactly that release.

Two layers:

* ``GamingConsumerBoundaryTest`` needs no Lumecon install: the production pin
  is empty and fails closed with a clear error, malformed and per-table pins
  are refused, entitlement is decided before any pin, catalog or artifact is
  read, and no canonical Gaming data or producer exists in this tree.
* ``PinnedLumeconReleaseTest`` builds the deterministic synthetic fixture
  release with the INSTALLED ``lumecon-data gaming fixture-release`` and
  serves it through Lumecon's own read-only API app: schema compatibility per
  component against the embedded contract, manifest/hash agreement, exact
  component bytes, idempotent re-pinning, atomic rollback, unavailable and
  mismatched releases failing closed, and per-table catalogs refused. It skips
  without the Lumecon branch unless ``CEDAR_REQUIRE_LUMECON_GAMING=1`` (CI),
  where a skip is a failure.
"""

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
REQUIRE_LUMECON = os.environ.get("CEDAR_REQUIRE_LUMECON_GAMING") == "1"

try:
    from fastapi.testclient import TestClient

    from cedar_press import collections as launch
    from cedar_press import repository, subscribers
    from cedar_press.app import app
    from cedar_press.session import Session, current_session

    HAVE_SERVER = True
except ImportError:
    HAVE_SERVER = False

URL = "/press/collections/gaming/full-download"


class _ServerCase(unittest.TestCase):
    """Shared session/audit plumbing for the full-download route."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.fetched = []
        self.subscriber = patch.object(
            subscribers,
            "find",
            return_value=subscribers.Subscriber(
                "grove-fixture@example.invalid", "grove", "fixture"
            ),
        )
        self.account = self.subscriber.start()
        self.addCleanup(self.subscriber.stop)
        self.addCleanup(app.dependency_overrides.clear)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def session(self, tier, email="grove-fixture@example.invalid"):
        app.dependency_overrides[current_session] = (
            (lambda: None) if tier is None else (lambda: Session(email, tier))
        )

    def get(self, component, release_id=None):
        params = {"release_id": release_id or "c" * 64}
        if component is not None:
            params["component"] = component
        with self.assertLogs("cedar_press.download", level="INFO") as logs:
            response = self.client.get(URL, params=params)
        self.assertNotIn("grove-fixture@example", " ".join(logs.output))
        return response, [json.loads(line.split(":", 2)[2]) for line in logs.output]

    def write_pin(self, pins, path=None):
        path = path or Path(self.temp.name) / "grove_release_pin.json"
        path.write_text(
            json.dumps({"schema_version": 1, "product": "cedar_grove", "pins": pins}),
            encoding="utf-8",
        )
        return path


@unittest.skipUnless(HAVE_SERVER, "requires the Cedar server development dependencies")
class GamingConsumerBoundaryTest(_ServerCase):
    COMPONENT = "gaming_regional_revenue"

    def setUp(self):
        super().setUp()
        for patcher in (
            patch.object(repository, "_release_bytes", side_effect=self.refuse_fetch),
            patch.dict(
                os.environ, {"CEDAR_GROVE_RELEASE_CATALOG": str(Path(self.temp.name) / "none.json")}
            ),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def refuse_fetch(self, path, limit=None):
        self.fetched.append(path)
        raise AssertionError("no Lumecon fetch may happen in this test: " + path)

    def test_production_pin_is_empty_until_issuance_and_fails_closed(self):
        document = json.loads(repository.GROVE_RELEASE_PIN.read_text(encoding="utf-8"))
        self.assertEqual((document["schema_version"], document["product"]), (1, "cedar_grove"))
        self.assertEqual(
            document["pins"], {}, "production pin must stay empty until Gaming IDs are ISSUED"
        )
        self.assertIn("ISSUED", document["status"])
        with self.assertRaises(repository.GroveReleaseNotPinned):
            repository.grove_release_pin("gaming")
        self.assertIsNone(repository.grove_release_metadata("gaming"))
        self.session("grove")
        response, events = self.get(self.COMPONENT)
        self.assertEqual(response.status_code, 503)
        self.assertIn("No released data is pinned", response.text)
        self.assertEqual(events[0]["outcome"], "not_pinned")
        self.assertEqual(self.fetched, [])

    def test_malformed_and_per_table_pins_are_refused(self):
        good = {
            "catalog_id": "a" * 64,
            "catalog_sha256": "b" * 64,
            "collection_id": "gaming",
            "release_id": "c" * 64,
            "manifest_sha256": "d" * 64,
        }
        cases = [
            ({**good, "collection_id": "gaming--gaming_regional_revenue"}, "per-table"),
            ({**good, "release_id": "latest"}, "Malformed"),
            ({**good, "current": "true"}, "Malformed"),
            ({k: v for k, v in good.items() if k != "manifest_sha256"}, "Malformed"),
        ]
        for pin, message in cases:
            with (
                self.subTest(message=message),
                patch.object(repository, "GROVE_RELEASE_PIN", self.write_pin({"gaming": pin})),
                self.assertRaisesRegex(repository.FullReleaseUnavailable, message),
            ):
                repository.grove_release_pin("gaming")
        with patch.object(repository, "GROVE_RELEASE_PIN", self.write_pin({"gaming": good})):
            self.assertEqual(repository.grove_release_pin("gaming"), good)

    def test_entitlement_is_decided_before_any_pin_catalog_or_artifact(self):
        reads = []
        with patch.object(repository, "grove_release_pin", side_effect=reads.append):
            for tier, status in [(None, 401), ("press", 403), ("press_pro", 403)]:
                with self.subTest(tier=tier):
                    self.session(tier)
                    response, events = self.get(self.COMPONENT)
                    self.assertEqual(response.status_code, status)
                    self.assertEqual(events[0]["component"], self.COMPONENT)
            # Stale account: a grove cookie after a downgrade, a removal and an
            # account-store outage never reaches the pin, catalog or artifact.
            self.session("grove")
            for account, error, status in [
                (
                    subscribers.Subscriber("grove-fixture@example.invalid", "press_pro", "fixture"),
                    None,
                    403,
                ),
                (None, None, 401),
                (None, RuntimeError("secret-store-detail"), 503),
            ]:
                with self.subTest(status=status):
                    self.account.return_value, self.account.side_effect = account, error
                    response, events = self.get(self.COMPONENT)
                    self.assertEqual(response.status_code, status)
                    self.assertNotIn("secret-store-detail", response.text + json.dumps(events))
        self.assertEqual((reads, self.fetched), ([], []))

    def test_missing_unknown_or_malformed_component_is_refused_and_redacted(self):
        self.session("grove")
        response, events = self.get(None)
        self.assertEqual(
            (response.status_code, events[0]["outcome"]), (400, "invalid_release_request")
        )
        for component in ("private-secret-token", "../legislation", "gaming_facilities"):
            with self.subTest(component=component):
                response, events = self.get(component)
                self.assertEqual(response.status_code, 503)
                self.assertEqual(events[0]["component"], "unknown")
                self.assertNotIn(component, json.dumps(events))
        self.assertEqual(self.fetched, [])

    def test_declaration_is_the_existing_grove_shelf_and_storefront_is_unchanged(self):
        self.assertEqual([e["id"] for e in launch.GROVE_RELEASE_COLLECTIONS], ["gaming"])
        self.assertEqual({e["shelf"] for e in launch.GROVE_RELEASE_COLLECTIONS}, {"grove"})
        self.assertEqual(repository.grove_components("gaming"), (self.COMPONENT,))
        self.assertEqual(repository.grove_components("legislation"), ())
        for tier in ("press", "press_pro", "grove", "tree", "unknown"):
            with self.subTest(tier=tier):
                self.assertFalse(repository.may_open(tier, "gaming"))
                self.assertNotIn("gaming", [c["id"] for c in repository.collections_for(tier)])
                for dataset in launch.LAUNCH_COLLECTION:
                    self.assertEqual(
                        repository.may_download_full(tier, dataset.id),
                        repository.may_open(tier, dataset.id),
                    )
            self.assertEqual(
                repository.may_download_full(tier, "gaming"), tier in ("grove", "tree")
            )
        self.assertFalse(repository.is_sold("gaming"))
        self.session("grove")
        self.assertEqual(self.client.get("/press/collections/gaming/download").status_code, 403)
        # A Press flagship is not addressed by component.
        self.session("press_pro")
        response = self.client.get(
            "/press/collections/legislation/full-download",
            params={"release_id": "a" * 64, "component": "native_bills"},
        )
        self.assertEqual(response.status_code, 400)


#: The 25 Gaming component tables (and the two binding-runner tables) Cedar
#: registered before the split; Lumecon-data owns every one of them now. The
#: 65 legacy clean tables (e.g. ``gaming_facility_metrics``) are Cedar's own
#: transitional inputs and are not in this list.
LUMECON_COMPONENT_STEMS = (
    "gaming_advocacy_links",
    "gaming_compact_terms",
    "gaming_compact_versions",
    "gaming_compacts",
    "gaming_coverage_gaps",
    "gaming_environmental_reviews",
    "gaming_facility_capacity",
    "gaming_facility_crosswalk",
    "gaming_facility_history",
    "gaming_facility_names",
    "gaming_facility_relationships",
    "gaming_financial_disclosures",
    "gaming_government_payments",
    "gaming_grove_facilities",
    "gaming_labor_observations",
    "gaming_land_eligibility",
    "gaming_licenses",
    "gaming_litigation",
    "gaming_online_sportsbook_financials",
    "gaming_online_sportsbook_relationships",
    "gaming_online_sportsbook_units",
    "gaming_regional_revenue",
    "gaming_regulatory_events",
    "gaming_reported_revenue_observations",
    "gaming_revenue_bands",
    "gaming_id_bindings",
    "gaming_id_migration_crosswalk",
)


class ZeroCanonicalDuplicationTest(unittest.TestCase):
    """Lumecon-data is the one home of Gaming data; nothing canonical is copied here."""

    def tracked(self):
        try:
            out = subprocess.run(
                ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
            )
            return out.stdout.splitlines()
        except (OSError, subprocess.CalledProcessError):
            return [
                p.relative_to(ROOT).as_posix()
                for p in ROOT.rglob("*")
                if p.is_file() and ".git" not in p.parts and "node_modules" not in p.parts
            ]

    def test_no_gaming_producer_register_component_or_schema_copy(self):
        files = self.tracked()
        names = {Path(f).name for f in files}
        # Producers, shared producer contract and online-sports module.
        producers = sorted(
            f for f in files if f.startswith("code/") and "gaming_grove" in Path(f).name
        )
        self.assertEqual(producers, [])
        # Binding registers (the live one is Cedar's, outside git) and component CSVs.
        self.assertNotIn("gaming_id_bindings.csv", names)
        components = sorted(
            f
            for f in files
            if f.endswith(".csv")
            and any(
                Path(f).name == stem + ".csv" or Path(f).name.startswith(stem + "__")
                for stem in LUMECON_COMPONENT_STEMS
            )
        )
        self.assertEqual(components, [])
        # Generated Gaming schema docs and exported contract JSON.
        self.assertNotIn("docs/GAMING_GROVE_DATA_CONTRACT.md", files)
        self.assertEqual([f for f in files if f.startswith("schemas/gaming/")], [])
        self.assertNotIn("docs/GAMING_VP_DISPOSITIONS_2026-09-24.csv", files)
        # No Grove component registration in the dataset contracts.
        contracts = json.loads(
            (ROOT / "docs/schema/dataset_contracts.json").read_text(encoding="utf-8")
        )
        gaming = [c for c in contracts["contracts"] if c["collection"] == "gaming"]
        self.assertEqual(len(gaming), 1)
        self.assertEqual([t["table"] for t in gaming[0]["tables"] if t.get("grove_component")], [])
        self.assertEqual(len(gaming[0]["tables"]), gaming[0]["n_tables"])
        # Build entry points: no Gaming producer command survives.
        build = (ROOT / "code/build.py").read_text(encoding="utf-8")
        for command in (
            "grove-contracts",
            "grove-leak-gate",
            "grove-promote-bindings",
            "cmd_grove_candidate",
        ):
            self.assertNotIn(command, build)
        pipeline = (ROOT / "code/cedar_pipeline.py").read_text(encoding="utf-8")
        self.assertNotIn("GROVE_COMPONENTS", pipeline)
        self.assertNotIn('"gaming"', pipeline)

    def test_field_map_entry_is_presentation_not_a_schema_authority(self):
        tables = json.loads((ROOT / "data/cedar/field_map.json").read_text(encoding="utf-8"))[
            "tables"
        ]
        for key, entry in tables.items():
            if entry.get("collection") == "gaming":
                with self.subTest(key=key):
                    self.assertIn("Lumecon-data", entry["header_source"])
                    self.assertIn("PINNED release", entry["header_source"])


# ------------------------------------------------------------------ Lumecon-built fixture
def _lumecon_release_module():
    """The installed Lumecon-data Gaming release module, or None without the branch."""
    try:
        from lumecon_data.gaming import release as lumecon_release

        lumecon_release.fixture_release  # noqa: B018 - the interface this suite needs
    except (ImportError, AttributeError):
        return None
    return lumecon_release


def _skip_or_fail(reason):
    if REQUIRE_LUMECON:
        raise AssertionError("CEDAR_REQUIRE_LUMECON_GAMING=1 but " + reason)
    raise unittest.SkipTest(reason)


def _fixture_cli(store):
    """`lumecon-data gaming fixture-release --store <store>` through the installed package."""
    out = subprocess.run(
        [sys.executable, "-m", "lumecon_data", "gaming", "fixture-release", "--store", str(store)],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(out.stdout)


def _bump_first_revenue_figure(fixture_dir):
    """A later release: the same fixture with one revenue figure changed."""
    import csv
    import io

    path = fixture_dir / "components" / (SERVED + ".csv")
    rows = list(csv.reader(io.StringIO(path.read_bytes().decode("utf-8"), newline="")))
    column = rows[0].index("ggr_nominal_usd")
    rows[1][column] = str(int(float(rows[1][column] or 0)) + 1)
    buffer = io.StringIO(newline="")
    csv.writer(buffer, lineterminator="\n").writerows(rows)
    path.write_bytes(buffer.getvalue().encode("utf-8"))


SERVED = "gaming_regional_revenue"


@unittest.skipUnless(HAVE_SERVER, "requires the Cedar server development dependencies")
class PinnedLumeconReleaseTest(_ServerCase):
    """The synthetic Gaming fixture release, built by the INSTALLED Lumecon-data
    (`lumecon-data gaming fixture-release`), pinned and served through the
    Cedar adapter. Lumecon's own verification reads the store: the bridge
    below only stands in for the network hop to its read-only API, answering
    `/v1/collections/<id>/releases/<rid>/manifest` with
    `collection_manifest_metadata` and `.../components/<name>/download` with
    `read_collection_component`, each after `verify_collection_release`."""

    @classmethod
    def setUpClass(cls):
        cls.work = None
        cls.lumecon = _lumecon_release_module()
        if cls.lumecon is None:
            _skip_or_fail(
                "lumecon_data.gaming.release is not installed "
                "(Lumecon-data branch claude/gaming-grove-release)"
            )
        cls.work = tempfile.TemporaryDirectory()
        root = Path(cls.work.name)
        # Release A: exactly what CI builds, through the installed CLI.
        cls.store_a = root / "store-a"
        cls.a = _fixture_cli(cls.store_a)
        # Release B: a later release of the same collection.
        fixtures = root / "fixtures-b"
        shutil.copytree(cls.lumecon.FIXTURE_DIR, fixtures)
        _bump_first_revenue_figure(fixtures)
        cls.store_b = root / "store-b"
        with patch.object(cls.lumecon, "FIXTURE_DIR", fixtures):
            cls.b = cls.lumecon.fixture_release(cls.store_b)
        cls.stores = {cls.a["release_id"]: cls.store_a, cls.b["release_id"]: cls.store_b}

    @classmethod
    def tearDownClass(cls):
        if cls.work is not None:
            cls.work.cleanup()

    def setUp(self):
        super().setUp()
        from lumecon_data.collection import (
            collection_manifest_metadata,
            read_collection_component,
            verify_collection_release,
        )

        self.metadata = collection_manifest_metadata
        self.read_component = read_collection_component
        self.verify = verify_collection_release
        self.pin_path = Path(self.temp.name) / "grove_release_pin.json"
        for patcher in (
            patch.object(repository, "GROVE_RELEASE_PIN", self.pin_path),
            # The fixture is a labelled synthetic rehearsal; production serves
            # neither. Only this suite widens the served classes.
            patch.object(
                repository, "GROVE_SERVED_RELEASE_CLASSES", frozenset({"production", "rehearsal"})
            ),
            patch.object(repository, "GROVE_SERVE_SYNTHETIC", True),
            patch.object(repository, "_release_bytes", side_effect=self.lumecon_api),
            patch.dict(os.environ, {}),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.session("grove")

    def lumecon_api(self, path, limit=None):
        """The network hop to Lumecon's read-only API, answered by Lumecon's library."""
        self.fetched.append(path)
        parts = path.split("/")  # /v1/collections/<id>/releases/<rid>/...
        if parts[1:3] != ["v1", "collections"] or parts[4] != "releases":
            raise OSError("unexpected Lumecon path " + path)
        collection, release_id = parts[3], parts[5]
        store = self.stores.get(release_id)
        if store is None or not store.exists():
            raise OSError("release unavailable in the Lumecon store")
        manifest = self.verify(store, collection, release_id)
        if parts[6:] == ["manifest"]:
            return repository._canonical_bytes(self.metadata(manifest))
        if parts[6] == "components" and parts[8:] == ["download"]:
            if manifest["components"][parts[7]]["download_permitted"] is not True:
                raise OSError("403 download not permitted")
            return self.read_component(store, collection, release_id, parts[7])
        raise OSError("unexpected Lumecon path " + path)

    def pin(self, built, catalog_path=None, **override):
        catalog_path = Path(catalog_path or built["catalog_path"])
        value = {
            "catalog_id": built["catalog_id"],
            "catalog_sha256": hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
            "collection_id": built["collection_id"],
            "release_id": built["release_id"],
            "manifest_sha256": built["manifest_sha256"],
            **override,
        }
        self.write_pin({"gaming": value}, self.pin_path)
        os.environ["CEDAR_GROVE_RELEASE_CATALOG"] = str(catalog_path)
        return value

    def component_bytes(self, built, name=SERVED):
        return self.read_component(
            self.stores[built["release_id"]], "gaming", built["release_id"], name
        )

    def test_the_fixture_is_one_collection_release_with_one_catalog_entry(self):
        catalog = json.loads(Path(self.a["catalog_path"]).read_bytes())
        self.assertEqual(catalog["catalog_kind"], "collection_releases")
        self.assertEqual([e["collection_id"] for e in catalog["collection_releases"]], ["gaming"])
        self.assertEqual(catalog["collection_releases"][0]["release_id"], self.a["release_id"])
        self.assertEqual((self.a["release_class"], self.a["synthetic"]), ("rehearsal", True))
        self.assertNotEqual(self.a["release_id"], self.b["release_id"])

    def test_production_settings_refuse_the_synthetic_rehearsal(self):
        self.pin(self.a)
        with patch.object(repository, "GROVE_SERVED_RELEASE_CLASSES", frozenset({"production"})):
            self.assertEqual(self.get(SERVED, self.a["release_id"])[0].status_code, 503)
        with patch.object(repository, "GROVE_SERVE_SYNTHETIC", False):
            self.assertEqual(self.get(SERVED, self.a["release_id"])[0].status_code, 503)

    def test_schema_compatibility_field_map_against_the_embedded_contract(self):
        manifest = self.metadata(self.verify(self.store_a, "gaming", self.a["release_id"]))
        tables = repository._field_map_tables()
        presented = [k for k, e in tables.items() if e.get("collection") == "gaming"]
        self.assertEqual(presented, ["gaming/" + SERVED])
        for key in presented:
            entry, component = tables[key], key.split("/", 1)[1]
            with self.subTest(component=component):
                contract = manifest["components"][component]
                self.assertEqual([f["name"] for f in contract["fields"]], entry["order"])
                rights = contract["metadata"]["field_rights"]
                for field in entry["fields"]:
                    if field["decision"] in {"keep", "rename"}:
                        self.assertEqual(
                            field.get("rights_class"), rights[field["column"]], field["column"]
                        )
        # Drift in the presentation entry (order or rights) is refused, never served.
        self.pin(self.a)
        for mutate in (
            lambda e: e.__setitem__("order", list(reversed(e["order"]))),
            lambda e: e["fields"][0].__setitem__("rights_class", "internal_vendor"),
        ):
            drifted = copy.deepcopy(tables)
            mutate(drifted["gaming/" + SERVED])
            with patch.object(repository, "_field_map_tables", return_value=drifted):
                self.assertEqual(self.get(SERVED, self.a["release_id"])[0].status_code, 503)

    def test_manifest_hash_agreement_and_exact_component_download(self):
        self.pin(self.a)
        expected = self.component_bytes(self.a)
        for tier in ("grove", "tree"):
            with self.subTest(tier=tier):
                self.session(tier)
                self.account.return_value = subscribers.Subscriber(
                    "grove-fixture@example.invalid", tier, "fixture"
                )
                response, events = self.get(SERVED, self.a["release_id"])
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.content, expected)
                self.assertEqual(
                    response.headers["x-cedar-sha256"], hashlib.sha256(expected).hexdigest()
                )
                self.assertEqual(
                    response.headers["x-cedar-sha256"],
                    self.a["components"][SERVED]["records_jsonl_sha256"],
                )
                self.assertEqual(response.headers["x-cedar-release"], self.a["release_id"])
                self.assertEqual(response.headers["x-cedar-component"], SERVED)
                self.assertEqual(
                    response.headers["x-cedar-rows"],
                    str(self.a["components"][SERVED]["record_count"]),
                )
                self.assertIn(
                    f'filename="gaming--{SERVED}-{self.a["release_id"]}.jsonl"',
                    response.headers["content-disposition"],
                )
                self.assertEqual(
                    (events[0]["outcome"], events[0]["component"]), ("authorized_prepared", SERVED)
                )
        catalog = json.loads(Path(self.a["catalog_path"]).read_bytes())
        self.assertEqual(catalog["catalog_id"], self.a["catalog_id"])
        self.assertEqual(
            catalog["collection_releases"][0]["manifest_sha256"], self.a["manifest_sha256"]
        )
        metadata = repository.grove_release_metadata("gaming")
        self.assertEqual([m["table_id"] for m in metadata], [SERVED])
        self.assertEqual(
            metadata[0]["records_sha256"], self.a["components"][SERVED]["records_jsonl_sha256"]
        )

    def test_entitlement_anonymous_wrong_tier_and_stale_account_with_a_real_pin(self):
        self.pin(self.a)
        for tier, status in [(None, 401), ("press", 403), ("press_pro", 403)]:
            with self.subTest(tier=tier):
                self.session(tier)
                self.assertEqual(self.get(SERVED, self.a["release_id"])[0].status_code, status)
        self.session("grove")
        self.account.return_value = subscribers.Subscriber(
            "grove-fixture@example.invalid", "press", "fixture"
        )
        self.assertEqual(self.get(SERVED, self.a["release_id"])[0].status_code, 403)
        self.account.return_value = None
        self.assertEqual(self.get(SERVED, self.a["release_id"])[0].status_code, 401)
        self.assertEqual(self.fetched, [])

    def test_idempotent_import_same_release_twice_is_a_no_op(self):
        again = _fixture_cli(self.store_a)
        self.assertEqual(again, self.a)
        first_pin = self.pin(self.a)
        first = self.pin_path.read_bytes()
        body_1 = self.get(SERVED, self.a["release_id"])[0].content
        self.assertEqual(self.pin(again), first_pin)
        self.assertEqual(self.pin_path.read_bytes(), first)
        self.assertEqual(self.get(SERVED, self.a["release_id"])[0].content, body_1)

    def test_rollback_to_the_prior_pin_is_atomic_and_exact(self):
        self.pin(self.a)
        body_a = self.get(SERVED, self.a["release_id"])[0].content
        self.pin(self.b)
        response = self.get(SERVED, self.b["release_id"])[0]
        self.assertEqual(
            (response.status_code, response.content), (200, self.component_bytes(self.b))
        )
        self.assertNotEqual(response.content, body_a)
        self.assertEqual(self.get(SERVED, self.a["release_id"])[0].status_code, 503)
        # Reverting the pin restores A's exact bytes: the whole release moves back.
        self.pin(self.a)
        response = self.get(SERVED, self.a["release_id"])[0]
        self.assertEqual((response.status_code, response.content), (200, body_a))
        self.assertEqual(self.get(SERVED, self.b["release_id"])[0].status_code, 503)

    def test_unavailable_or_mismatched_release_fails_closed(self):
        for label, override in {
            "manifest hash": {"manifest_sha256": "0" * 64},
            "catalog bytes": {"catalog_sha256": "0" * 64},
            "catalog id": {"catalog_id": "0" * 64},
            "release id": {"release_id": self.b["release_id"]},
        }.items():
            with self.subTest(label=label):
                self.pin(self.a, **override)
                response, events = self.get(
                    SERVED, override.get("release_id", self.a["release_id"])
                )
                self.assertEqual(response.status_code, 503)
                self.assertEqual(events[0]["outcome"], "unavailable")
        self.pin(self.a)
        os.environ["CEDAR_GROVE_RELEASE_CATALOG"] = str(Path(self.temp.name) / "absent.json")
        self.assertEqual(self.get(SERVED, self.a["release_id"])[0].status_code, 503)
        copied = Path(self.temp.name) / "copied-store"
        shutil.copytree(self.store_a, copied)
        with patch.dict(self.stores, {self.a["release_id"]: copied}):
            self.pin(self.a)
            self.assertEqual(self.get(SERVED, self.a["release_id"])[0].status_code, 200)
            records = [p for p in copied.rglob("records.jsonl") if SERVED in p.parts]
            self.assertEqual(len(records), 1)
            records[0].write_bytes(records[0].read_bytes().replace(b"1", b"2", 1))
            self.assertEqual(self.get(SERVED, self.a["release_id"])[0].status_code, 503)
            shutil.rmtree(copied)
            self.assertEqual(self.get(SERVED, self.a["release_id"])[0].status_code, 503)

    def test_unpresented_undownloadable_and_per_table_catalogs_are_refused(self):
        self.pin(self.a)
        # A component in the release that Cedar does not present is not offered.
        self.assertEqual(self.get("gaming_compacts", self.a["release_id"])[0].status_code, 503)
        # A presented component whose download Lumecon does not permit is refused.
        manifest = self.metadata(self.verify(self.store_a, "gaming", self.a["release_id"]))
        history = manifest["components"]["gaming_facility_history"]
        self.assertIs(history["download_permitted"], False)
        tables = copy.deepcopy(repository._field_map_tables())
        tables["gaming/gaming_facility_history"] = {
            "collection": "gaming",
            "order": [f["name"] for f in history["fields"]],
            "fields": [],
        }
        with patch.object(repository, "_field_map_tables", return_value=tables):
            self.assertEqual(
                self.get("gaming_facility_history", self.a["release_id"])[0].status_code, 503
            )
        self.assertFalse(any(p.endswith("gaming_facility_history/download") for p in self.fetched))
        # A catalog of per-table dataset releases cannot stand in for the collection.
        entry = json.loads(Path(self.a["catalog_path"]).read_bytes())["collection_releases"][0]
        per_table = {
            "schema_version": 1,
            "product": "cedar_grove",
            "entitlement_required": True,
            "collections": [
                {
                    "dataset_id": c["dataset_id"],
                    "release_id": entry["release_id"],
                    "manifest_sha256": entry["manifest_sha256"],
                }
                for c in entry["components"]
            ],
        }
        per_table["catalog_id"] = hashlib.sha256(repository._canonical_bytes(per_table)).hexdigest()
        path = Path(self.temp.name) / "per-table-catalog.json"
        path.write_text(json.dumps(per_table), encoding="utf-8")
        self.pin(self.a, catalog_path=path, catalog_id=per_table["catalog_id"])
        with self.assertRaisesRegex(repository.FullReleaseUnavailable, "Per-table"):
            repository._grove_catalog(repository.grove_release_pin("gaming"))
        self.assertEqual(self.get(SERVED, self.a["release_id"])[0].status_code, 503)


if __name__ == "__main__":
    unittest.main()
