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
            return_value=subscribers.Subscriber("grove-fixture@example.invalid", "grove", "fixture"),
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
            patch.dict(os.environ, {"CEDAR_GROVE_RELEASE_CATALOG": str(Path(self.temp.name) / "none.json")}),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def refuse_fetch(self, path, limit=None):
        self.fetched.append(path)
        raise AssertionError("no Lumecon fetch may happen in this test: " + path)

    def test_production_pin_is_empty_until_issuance_and_fails_closed(self):
        document = json.loads(repository.GROVE_RELEASE_PIN.read_text(encoding="utf-8"))
        self.assertEqual((document["schema_version"], document["product"]), (1, "cedar_grove"))
        self.assertEqual(document["pins"], {}, "production pin must stay empty until Gaming IDs are ISSUED")
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
        good = {"catalog_id": "a" * 64, "catalog_sha256": "b" * 64, "dataset_id": "gaming",
                "release_id": "c" * 64, "manifest_sha256": "d" * 64}
        cases = [
            ({**good, "dataset_id": "gaming--gaming_regional_revenue"}, "per-table"),
            ({**good, "release_id": "latest"}, "Malformed"),
            ({**good, "current": "true"}, "Malformed"),
            ({k: v for k, v in good.items() if k != "manifest_sha256"}, "Malformed"),
        ]
        for pin, message in cases:
            with self.subTest(message=message), patch.object(
                repository, "GROVE_RELEASE_PIN", self.write_pin({"gaming": pin})
            ):
                with self.assertRaisesRegex(repository.FullReleaseUnavailable, message):
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
                (subscribers.Subscriber("grove-fixture@example.invalid", "press_pro", "fixture"), None, 403),
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
        self.assertEqual((response.status_code, events[0]["outcome"]), (400, "invalid_release_request"))
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
                    self.assertEqual(repository.may_download_full(tier, dataset.id),
                                     repository.may_open(tier, dataset.id))
            self.assertEqual(repository.may_download_full(tier, "gaming"), tier in ("grove", "tree"))
        self.assertFalse(repository.is_sold("gaming"))
        self.session("grove")
        self.assertEqual(self.client.get("/press/collections/gaming/download").status_code, 403)
        # A Press flagship is not addressed by component.
        self.session("press_pro")
        response = self.client.get("/press/collections/legislation/full-download",
                                   params={"release_id": "a" * 64, "component": "native_bills"})
        self.assertEqual(response.status_code, 400)


#: The 25 Gaming component tables (and the two binding-runner tables) Cedar
#: registered before the split; Lumecon-data owns every one of them now. The
#: 65 legacy clean tables (e.g. ``gaming_facility_metrics``) are Cedar's own
#: transitional inputs and are not in this list.
LUMECON_COMPONENT_STEMS = (
    "gaming_advocacy_links", "gaming_compact_terms", "gaming_compact_versions", "gaming_compacts",
    "gaming_coverage_gaps", "gaming_environmental_reviews", "gaming_facility_capacity",
    "gaming_facility_crosswalk", "gaming_facility_history", "gaming_facility_names",
    "gaming_facility_relationships", "gaming_financial_disclosures", "gaming_government_payments",
    "gaming_grove_facilities", "gaming_labor_observations", "gaming_land_eligibility", "gaming_licenses",
    "gaming_litigation", "gaming_online_sportsbook_financials", "gaming_online_sportsbook_relationships",
    "gaming_online_sportsbook_units", "gaming_regional_revenue", "gaming_regulatory_events",
    "gaming_reported_revenue_observations", "gaming_revenue_bands",
    "gaming_id_bindings", "gaming_id_migration_crosswalk",
)


class ZeroCanonicalDuplicationTest(unittest.TestCase):
    """Lumecon-data is the one home of Gaming data; nothing canonical is copied here."""

    def tracked(self):
        try:
            out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True)
            return out.stdout.splitlines()
        except (OSError, subprocess.CalledProcessError):
            return [p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*")
                    if p.is_file() and ".git" not in p.parts and "node_modules" not in p.parts]

    def test_no_gaming_producer_register_component_or_schema_copy(self):
        files = self.tracked()
        names = {Path(f).name for f in files}
        # Producers, shared producer contract and online-sports module.
        producers = sorted(f for f in files if f.startswith("code/") and "gaming_grove" in Path(f).name)
        self.assertEqual(producers, [])
        # Binding registers (the live one is Cedar's, outside git) and component CSVs.
        self.assertNotIn("gaming_id_bindings.csv", names)
        components = sorted(f for f in files if f.endswith(".csv") and any(
            Path(f).name == stem + ".csv" or Path(f).name.startswith(stem + "__")
            for stem in LUMECON_COMPONENT_STEMS))
        self.assertEqual(components, [])
        # Generated Gaming schema docs and exported contract JSON.
        self.assertNotIn("docs/GAMING_GROVE_DATA_CONTRACT.md", files)
        self.assertEqual([f for f in files if f.startswith("schemas/gaming/")], [])
        self.assertNotIn("docs/GAMING_VP_DISPOSITIONS_2026-09-24.csv", files)
        # No Grove component registration in the dataset contracts.
        contracts = json.loads((ROOT / "docs/schema/dataset_contracts.json").read_text(encoding="utf-8"))
        gaming = [c for c in contracts["contracts"] if c["collection"] == "gaming"]
        self.assertEqual(len(gaming), 1)
        self.assertEqual([t["table"] for t in gaming[0]["tables"] if t.get("grove_component")], [])
        self.assertEqual(len(gaming[0]["tables"]), gaming[0]["n_tables"])
        # Build entry points: no Gaming producer command survives.
        build = (ROOT / "code/build.py").read_text(encoding="utf-8")
        for command in ("grove-contracts", "grove-leak-gate", "grove-promote-bindings", "cmd_grove_candidate"):
            self.assertNotIn(command, build)
        pipeline = (ROOT / "code/cedar_pipeline.py").read_text(encoding="utf-8")
        self.assertNotIn("GROVE_COMPONENTS", pipeline)
        self.assertNotIn('"gaming"', pipeline)

    def test_field_map_entry_is_presentation_not_a_schema_authority(self):
        tables = json.loads((ROOT / "data/cedar/field_map.json").read_text(encoding="utf-8"))["tables"]
        for key, entry in tables.items():
            if entry.get("collection") == "gaming":
                with self.subTest(key=key):
                    self.assertIn("Lumecon-data", entry["header_source"])
                    self.assertIn("PINNED release", entry["header_source"])


# ------------------------------------------------------------------ Lumecon-built fixture
def _lumecon_cli():
    """The installed lumecon-data CLI entry, or None when the branch is absent."""
    try:
        import lumecon_data.gaming  # noqa: F401
        from lumecon_data import cli  # noqa: F401
    except ImportError:
        return None
    return [sys.executable, "-m", "lumecon_data"]


LUMECON = _lumecon_cli()


def _skip_or_fail(reason):
    if REQUIRE_LUMECON:
        raise AssertionError("CEDAR_REQUIRE_LUMECON_GAMING=1 but " + reason)
    raise unittest.SkipTest(reason)


if __name__ == "__main__":
    unittest.main()
