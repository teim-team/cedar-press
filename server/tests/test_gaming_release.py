"""Gaming (Cedar Grove) through the existing orchestrator, release pilot and adapter.

All fixtures are fictional and data-less. Three layers, each reusing the
shared path rather than a Gaming copy of it:

* ``code/build.py candidate gaming``: registered producers run in declared
  order into a new isolated root; shared validators, cross-table references,
  provisional-ID status and change report.
* ``code/build.py release-pilot gaming``: refusal of provisional, vendor and
  non-CE identifiers and of the vendor-lineage flagship; then (with a fixture
  identifier binding standing in for the pending allowed-ID contract) exact
  Lumecon release bytes, determinism, immutable-replacement refusal and
  rollback to a prior verified catalog.
* The Cedar server adapter: today it refuses Gaming for every tier before any
  fetch and refuses a ``cedar_grove`` catalog. The last class simulates the
  reviewed Grove declaration proposed in docs/GAMING_GROVE_INFRASTRUCTURE_NOTES.md
  with the EXISTING tier model (grove/tree reach the grove shelf) to prove the
  adapter's denial, exact bytes, redacted audit, stale-account and rollback
  behaviour carry over unchanged.
"""

import argparse
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from types import MappingProxyType
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

import cedar_ids  # noqa: E402
import cedar_publication  # noqa: E402
import gaming_grove  # noqa: E402

SPEC = importlib.util.spec_from_file_location("gaming_release_build", CODE / "build.py")
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)

CE = "CE-00001-6S"          # an issued CE id with a valid check pair
PLACE = "CEDAR-PLACE-000001-AB"

# ---------------------------------------------------------------- fixture producers
PRODUCER = textwrap.dedent('''
    """Fictional Grove component producer for build.py tests."""
    import json, os, sys
    from pathlib import Path
    sys.path.insert(0, {code!r})
    import gaming_grove as gg

    MODE = os.environ.get("FIXTURE_MODE", "ok")
    SCRIPT = Path(__file__).stem
    CONTRACTS = {contracts}

    def rows_for(table):
        prov = MODE == "provisional"
        fac = ("PROV-GFAC:" if prov else "GFAC-") + "{place}"
        grev = ("PROV-" if prov else "") + "GREV-0123456789AB"
        greg = ("PROV-" if prov else "") + "GREG-0123456789AB"
        if table == "gaming_grove_facilities.csv":
            return [{{"gaming_facility_id": fac, "cedar_uid": "{ce}", "facility_name": "Fictional Casino",
                      "rights_class": "public_official"}}]
        if table == "gaming_regulatory_events.csv":
            ref = "GFAC-MISSING" if MODE == "dangling" else fac
            out = [{{"event_id": greg, "gaming_facility_id": ref, "event_date": "2025-01-02",
                     "rights_class": "public_official"}}]
            if MODE == "added":
                out.append({{"event_id": greg.replace("0123", "9999"), "gaming_facility_id": fac,
                            "event_date": "2026-03-04", "rights_class": "public_official"}})
            return out
        return [{{"revenue_observation_id": grev, "region_name": "Fictional Region", "fiscal_year": "2025",
                 "ggr_nominal_usd": "100", "internal_estimate": "7", "rights_class": "public_official"}}]

    def main():
        args = sys.argv[1:]
        assert args[0] == "build"
        root, out, as_of = args[2], Path(args[4]), args[6]
        if MODE == "fail" and SCRIPT.startswith("9001"):
            print("fixture failure")
            return 1
        inputs = gg.Inputs(root)
        inputs.clean("fixture_source.csv")
        tables = []
        for table, contract in sorted(CONTRACTS.items()):
            rows = rows_for(table)
            tables.append(gg.write_table(out, table, list(contract["field_rights"]), rows, contract))
        receipt = {{"tables": tables, "inputs": inputs.receipts, "coverage": {{"fixture": True}},
                   "withheld": {{}}, "notes": [], "as_of": as_of}}
        (out / (SCRIPT + ".receipt.json")).write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")
        return 0

    if __name__ == "__main__":
        sys.exit(main())
''')


def _contract(pk, rights, grain, **extra):
    base = {"grain": grain, "primary_key": pk, "required": [], "enums": {}, "dates": [],
            "intervals": [], "public_id_columns": [], "derived_ids": {},
            "field_rights": rights, "field_descriptions": {c: "fixture column " + c for c in rights},
            "publication_status": "public", "supersedes": [], "row_rights_column": "rights_class",
            "nonadditive_note": "fixture"}
    base.update(extra)
    return base


FACILITIES = {"gaming_grove_facilities.csv": _contract(
    ["gaming_facility_id"],
    {"gaming_facility_id": "public_derived", "cedar_uid": "public_official",
     "facility_name": "withheld_unverified", "rights_class": "public_official"},
    "one fictional gaming facility",
    supersedes=[{"table": "gaming_facilities.csv", "role": "superseded: vendor-lineage directory"},
                {"table": "compacts.csv", "role": "source (read-only)"}])}
EVENTS = {
    "gaming_regulatory_events.csv": _contract(
        ["event_id"],
        {"event_id": "public_derived", "gaming_facility_id": "public_derived",
         "event_date": "public_official", "rights_class": "public_official"},
        "one fictional regulatory event", dates=["event_date"], derived_ids={"event_id": "GREG"}),
    "gaming_regional_revenue.csv": _contract(
        ["revenue_observation_id"],
        {"revenue_observation_id": "public_derived", "region_name": "public_official",
         "fiscal_year": "public_official", "ggr_nominal_usd": "public_official",
         "internal_estimate": "internal_model", "rights_class": "public_official"},
        "one fictional regional revenue figure", derived_ids={"revenue_observation_id": "GREV"},
        supersedes=[{"table": "nigc_regional_ggr.csv", "role": "source of every region row"}]),
}
SCRIPTS = ["9001_fixture_facilities.py", "9002_fixture_events.py"]


def _py_literal(contracts):
    return repr(contracts)


class GroveFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.source = base / "inputs"
        (self.source / "data" / "clean").mkdir(parents=True)
        (self.source / "data" / "spine").mkdir(parents=True)
        (self.source / "data" / "clean" / "fixture_source.csv").write_text("a\n1\n", encoding="utf-8")
        (self.source / "data" / "spine" / "cedar_identity_register.csv").write_text(
            f"cedar_uid,canonical_name\n{CE},Fictional Nation\n", encoding="utf-8")
        self.code = base / "code"
        self.code.mkdir()
        for script, contracts in zip(SCRIPTS, (FACILITIES, EVENTS), strict=True):
            (self.code / script).write_text(
                PRODUCER.format(code=str(CODE), contracts=_py_literal(contracts), place=PLACE, ce=CE),
                encoding="utf-8")
        self.base = base
        self.registry = {"contracts": [{
            "collection": "gaming", "rebuild_command": "py -3 code/build.py run gaming --execute",
            "tables": [{"table": t, "rebuilt_by": [s]}
                       for s, c in zip(SCRIPTS, (FACILITIES, EVENTS), strict=True) for t in c]}]}
        real = BUILD.CP.registration_problems
        for patcher in (
            patch.dict(BUILD.CP.GROVE_COMPONENTS, {"gaming": SCRIPTS}),
            patch.object(BUILD, "GROVE_CODE", self.code),
            patch.object(BUILD.CP, "registration_problems",
                         side_effect=lambda plan, contracts=None: real(plan, self.registry)),
            patch.dict(BUILD.CP.GROVE_REFERENCES, {"gaming": [
                ("gaming_facility_id", "component", None, "gaming_facility_id"),
                ("cedar_uid", "input", "data/spine/cedar_identity_register.csv", "cedar_uid")]}),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def run_candidate(self, name, mode="ok", previous=None):
        target = self.base / name
        args = argparse.Namespace(collection="gaming", input_root=str(self.source), owner_dir=None,
                                  output_root=str(target), as_of="2026-09-24",
                                  previous=str(previous) if previous else None)
        with patch.dict(os.environ, {"FIXTURE_MODE": mode}), contextlib.redirect_stdout(io.StringIO()):
            code = BUILD.cmd_candidate(args)
        manifest = json.loads((target / "logs" / "gaming-candidate.json").read_text(encoding="utf-8"))
        return code, target, manifest


class GroveCandidateTest(GroveFixture):
    def test_existing_or_overlapping_root_is_refused_before_anything_runs(self):
        existing = self.base / "exists"
        existing.mkdir()
        for target in (existing, self.source / "candidate", self.source.parent):
            args = argparse.Namespace(collection="gaming", input_root=str(self.source), owner_dir=None,
                                      output_root=str(target), as_of="2026-09-24", previous=None)
            with self.subTest(target=target), self.assertRaisesRegex(SystemExit, "REFUSED"):
                BUILD.cmd_candidate(args)
        self.assertFalse((self.source / "candidate").exists())
        self.assertEqual(list(existing.iterdir()), [])

    def test_unregistered_component_is_refused_before_dispatch(self):
        self.registry["contracts"][0]["tables"].pop()
        with self.assertRaisesRegex(SystemExit, "UNREGISTERED_TABLE"):
            self.run_candidate("unregistered")
        self.assertFalse((self.base / "unregistered").exists())

    def test_provisional_ids_run_in_order_and_are_never_promotable(self):
        code, target, manifest = self.run_candidate("provisional", mode="provisional")
        self.assertEqual(code, 0)
        self.assertEqual(manifest["status"], "LOCAL_DRY_RUN_PROVISIONAL_IDS")
        self.assertEqual([s["command"][0] for s in manifest["steps"]], SCRIPTS)
        self.assertGreater(manifest["provisional_id_values"], 0)
        self.assertTrue(manifest["validation"]["passed"], manifest["validation"])
        self.assertIn("data/clean/fixture_source.csv", [i["path"] for i in manifest["inputs"]])
        self.assertIn("data/spine/cedar_identity_register.csv", [i["path"] for i in manifest["inputs"]])
        for output in manifest["outputs"]:
            data = (target / "components" / output["table"]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), output["sha256"])

    def test_approved_candidate_samples_public_fields_and_reports_changes(self):
        code, first, manifest = self.run_candidate("first")
        self.assertEqual((code, manifest["status"]), (0, "LOCAL_CANDIDATE_NOT_PROMOTED"))
        sample = (first / "samples" / "gaming_grove_facilities.csv").read_text(encoding="utf-8")
        self.assertNotIn("facility_name", sample)          # withheld_unverified never sampled
        self.assertNotIn("Fictional Casino", sample)
        self.assertNotIn("internal_estimate", (first / "samples" / "gaming_regional_revenue.csv").read_text())
        coverage = json.loads((first / "coverage.json").read_text(encoding="utf-8"))
        self.assertEqual(coverage["gaming_regulatory_events.csv"]["rows_touching_2025"], 1)
        code, second, manifest = self.run_candidate("second", mode="added", previous=first)
        self.assertEqual(code, 0)
        report = json.loads((second / "change_report.json").read_text(encoding="utf-8"))
        events = report["tables"]["gaming_regulatory_events.csv"]
        self.assertEqual((events["status"], events["keys_added"], events["rows_after"]), ("changed", 1, 2))
        self.assertEqual(report["tables"]["gaming_grove_facilities.csv"]["status"], "unchanged")

    def test_dangling_reference_fails_the_candidate_by_name(self):
        code, _target, manifest = self.run_candidate("dangling", mode="dangling")
        self.assertEqual((code, manifest["status"]), (1, "FAILED_VALIDATION"))
        self.assertTrue(any("DANGLING_REFERENCE: gaming_regulatory_events.csv.gaming_facility_id" in p
                            for p in manifest["validation"]["problems"]))

    def test_a_failed_producer_stops_the_chain(self):
        code, target, manifest = self.run_candidate("failed", mode="fail")
        self.assertEqual((code, manifest["status"]), (1, "FAILED"))
        self.assertEqual(len(manifest["steps"]), 1)
        self.assertIn("fixture failure", (target / "logs" / ("01-" + SCRIPTS[0] + ".log")).read_text())

    def test_component_reusing_an_existing_clean_table_name_is_refused(self):
        repo = self.base / "repo"
        (repo / "docs/schema").mkdir(parents=True)
        shutil.copy2(ROOT / "docs/schema/dataset_contracts.json", repo / "docs/schema/dataset_contracts.json")
        producers = BUILD.grove_producers("gaming")
        script, path, module = producers[0]
        clashing = type(module)("clash")
        clashing.CONTRACTS = {"gaming_facilities.csv": module.CONTRACTS["gaming_grove_facilities.csv"]}
        text = (repo / "docs/schema/dataset_contracts.json").read_text(encoding="utf-8")
        with self.assertRaisesRegex(SystemExit, "NAME_COLLISION: .*gaming_facilities.csv"):
            BUILD.grove_dataset_contracts("gaming", [(script, path, clashing)], text)

    def test_contract_sync_registers_components_and_is_checkable(self):
        repo = self.base / "repo"
        for rel in ("docs/schema/dataset_contracts.json", "data/cedar/field_map.json"):
            (repo / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, repo / rel)
        args = argparse.Namespace(collection="gaming", check=True)
        with patch.object(BUILD, "ROOT", repo), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(BUILD.cmd_grove_contracts(args), 1)
            args.check = False
            self.assertEqual(BUILD.cmd_grove_contracts(args), 0)
            args.check = True
            self.assertEqual(BUILD.cmd_grove_contracts(args), 0)
        contracts = json.loads((repo / "docs/schema/dataset_contracts.json").read_text(encoding="utf-8"))
        entry = next(c for c in contracts["contracts"] if c["collection"] == "gaming")
        roles = {t["table"]: t.get("grove_role") for t in entry["tables"] if not t.get("grove_component")}
        self.assertEqual(roles["gaming_facilities.csv"], "historical_superseded_by_grove")
        self.assertEqual(roles["compacts.csv"], "grove_source_input")
        self.assertEqual(roles["gaming_facility_metrics.csv"], "internal_qa")
        self.assertTrue(all(roles.values()))
        plan = BUILD.grove_plan("gaming", BUILD.grove_producers("gaming"))
        self.assertEqual(_real_registration()(plan, contracts), [])
        field_map = json.loads((repo / "data/cedar/field_map.json").read_text(encoding="utf-8"))
        generated = field_map["tables"]["gaming/gaming_regional_revenue"]
        self.assertEqual(generated["order"], ["revenue_observation_id", "region_name", "fiscal_year",
                                              "ggr_nominal_usd", "rights_class", "research_note"])
        self.assertIn("internal_estimate", [f["column"] for f in generated["fields"]
                                            if f["decision"] == "internal"])
        doc = (repo / "docs/GAMING_GROVE_DATA_CONTRACT.md").read_text(encoding="utf-8")
        self.assertIn("`gaming_regional_revenue.csv`", doc)
        self.assertIn("historical_superseded_by_grove", doc)


def _real_registration():
    spec = importlib.util.spec_from_file_location("gaming_registration", CODE / "cedar_pipeline.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.registration_problems


# ---------------------------------------------------------------- release pilot
try:
    import lumecon_data  # noqa: F401
    HAVE_LUMECON = True
except ImportError:
    HAVE_LUMECON = False

REGION_CONTRACT = EVENTS["gaming_regional_revenue.csv"]
BINDING = cedar_ids.IdentifierContract(
    "gaming", "gaming_regional_revenue.csv", "revenue_observation_id", "GREV", "record",
    "observation", "fixture only: stands in for the pending allowed-ID contract",
    "fixture: pending CICD identifier-retirement audit", pattern=r"GREV-[0-9A-F]{12}")


@unittest.skipUnless(HAVE_LUMECON, "requires Lumecon Data on PYTHONPATH")
class GamingReleasePilotTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.canonical = base / "canonical"
        self.canonical.mkdir()
        self.store = base / "store"
        self.header = list(REGION_CONTRACT["field_rights"])
        self.rows = [
            {"revenue_observation_id": "GREV-0123456789AB", "region_name": "Fictional Region",
             "fiscal_year": "2025", "ggr_nominal_usd": "100", "internal_estimate": "7",
             "rights_class": "public_official"},
            {"revenue_observation_id": "GREV-0123456789AC", "region_name": "Second Region",
             "fiscal_year": "2024", "ggr_nominal_usd": "90", "internal_estimate": "",
             "rights_class": "public_official"},
        ]
        entry = BUILD.grove_field_map_entry("gaming", "fixture", "gaming_regional_revenue.csv",
                                            REGION_CONTRACT)
        real_map = cedar_publication.field_map()
        self.fixture_map = {**real_map, "gaming": dict(entry, key="gaming/gaming_regional_revenue")}
        for patcher in (
            # The worktree has no ignored ruling ledger; the fixture rows carry
            # no UEI, so an empty verified-denial set changes nothing.
            patch.object(cedar_publication, "denied_ueis", return_value=frozenset()),
            patch.object(cedar_publication, "field_map", side_effect=lambda: self.fixture_map),
            patch.object(BUILD, "pilot_table_contract", return_value={
                "primary_key": ["revenue_observation_id"], "grain": REGION_CONTRACT["grain"]}),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def bind(self):
        bindings = dict(cedar_ids.IDENTIFIER_CONTRACTS)
        bindings[BINDING.binding] = BINDING
        return patch.object(cedar_ids, "IDENTIFIER_CONTRACTS", MappingProxyType(bindings))

    def write(self, rows=None, name="gaming_regional_revenue.csv"):
        path = self.canonical / name
        path.write_bytes(BUILD._csv_bytes(self.header, rows or self.rows))
        return path

    def pilot(self, source, as_of="2026-09-24"):
        args = argparse.Namespace(collection="gaming", source=str(source),
                                  output_root=str(self.store), as_of=as_of)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            BUILD.cmd_release_pilot(args)
        return json.loads(out.getvalue().strip().splitlines()[-1])

    def test_provisional_vendor_and_non_ce_identifiers_are_refused(self):
        cases = [
            ("revenue_observation_id", "PROV-GREV-0123456789AB", "provisional identifier"),
            ("region_name", "Casino property CCP-1234", "vendor-lineage identifier"),
            ("region_name", "VP-77", "vendor-lineage identifier"),
        ]
        for column, value, message in cases:
            with self.subTest(value=value), self.bind():
                rows = copy.deepcopy(self.rows)
                rows[0][column] = value
                with self.assertRaisesRegex(SystemExit, "REFUSED: .*" + message):
                    self.pilot(self.write(rows))
        self.header.append("cedar_uid")
        rows = copy.deepcopy(self.rows)
        for row in rows:
            row["cedar_uid"] = ""
        rows[0]["cedar_uid"] = "TRBF-0001"
        with self.bind(), self.assertRaisesRegex(SystemExit, "non-CE entity identifier in cedar_uid"):
            self.pilot(self.write(rows))
        self.assertFalse((self.store / "releases").exists())

    def test_vendor_lineage_flagship_and_unmapped_table_are_refused(self):
        with self.bind(), self.assertRaisesRegex(SystemExit, "REFUSED"):
            self.pilot(self.write(name="gaming_facilities.csv"))
        with self.assertRaisesRegex(SystemExit, "replaced flagship"):
            BUILD.pilot_table("gaming", dict(BUILD.CP.RELEASE_PILOTS["gaming"],
                                             table="gaming_facilities.csv"), cedar_publication.FLAGSHIP)
        with self.assertRaisesRegex(SystemExit, "disagrees"):
            BUILD.pilot_table("gaming", BUILD.CP.RELEASE_PILOTS["gaming"], {"gaming": "other.csv"})
        self.fixture_map.pop("gaming")
        with self.bind(), self.assertRaisesRegex(SystemExit, "no approved field-map entry"):
            self.pilot(self.write())

    def test_release_waits_for_the_identifier_contract(self):
        with self.assertRaisesRegex(SystemExit, "no declared identifier binding"):
            self.pilot(self.write())
        self.assertFalse((self.store / "releases").exists())

    def test_exact_bytes_determinism_immutability_and_rollback(self):
        from lumecon_data.catalog import manifest_metadata
        from lumecon_data.pipeline import verify_release
        from lumecon_data.storage import canonical_json, immutable_bytes
        with self.bind():
            first = self.pilot(self.write())
            again = self.pilot(self.write())
        self.assertEqual(first["release_id"], again["release_id"])
        self.assertEqual(first["record_count"], 2)
        release = self.store / "releases" / "gaming" / first["release_id"]
        records = release / "records.jsonl"
        lines = [json.loads(line) for line in records.read_bytes().splitlines()]
        order = self.fixture_map["gaming"]["order"]
        self.assertEqual([set(row) for row in lines], [set(order), set(order)])
        self.assertEqual({row["revenue_observation_id"] for row in lines},
                         {row["revenue_observation_id"] for row in self.rows})
        self.assertNotIn(b"internal_estimate", records.read_bytes())
        catalog_a = json.loads(Path(first["catalog"]).read_text(encoding="utf-8"))
        self.assertEqual(catalog_a["product"], "cedar_grove")
        before = {p.name: p.read_bytes() for p in release.iterdir()}
        with self.assertRaises(ValueError):
            immutable_bytes(records, b'{"replaced": true}\n')
        self.assertEqual(records.read_bytes(), before["records.jsonl"])
        changed = copy.deepcopy(self.rows)
        changed[0]["ggr_nominal_usd"] = "101"
        with self.bind():
            second = self.pilot(self.write(changed), as_of="2026-09-25")
        self.assertNotEqual(second["release_id"], first["release_id"])
        self.assertNotEqual(second["catalog"], first["catalog"])
        # Rollback = select the prior verified catalog; neither release changes.
        manifest = verify_release(self.store, "gaming", first["release_id"])
        pin = catalog_a["collections"][0]
        self.assertEqual(pin["release_id"], first["release_id"])
        self.assertEqual(pin["manifest_sha256"],
                         hashlib.sha256(canonical_json(manifest_metadata(manifest))).hexdigest())
        self.assertEqual({p.name: p.read_bytes() for p in release.iterdir()}, before)
        verify_release(self.store, "gaming", second["release_id"])


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

GAMING_KEY = "gaming/gaming_regional_revenue"


@unittest.skipUnless(HAVE_SERVER, "requires the Cedar server development dependencies")
class GamingServerDeliveryTest(unittest.TestCase):
    """Denial, exact bytes, audit and rollback for a Grove pin."""

    URL = "/press/collections/gaming/full-download"

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.catalog = Path(self.temp.name) / "catalog.json"
        field_map = json.loads((ROOT / "data/cedar/field_map.json").read_text(encoding="utf-8"))
        entry = field_map["tables"].get(GAMING_KEY)
        self.header = entry["order"] if entry else ["revenue_observation_id", "research_note"]
        self.rows = [{name: None for name in self.header}]
        self.rows[0]["revenue_observation_id"] = "GREV-0123456789AB"
        self.rid = "c" * 64
        self.pin = {"dataset_id": "gaming", "release_id": self.rid, "record_count": 1,
                    "fields": [{"name": n, "type": "string", "nullable": n != "revenue_observation_id"}
                               for n in self.header],
                    "rights": {"publication_class": "publishable", "redistribution": True},
                    "synthetic": False}
        content = b"".join(repository._canonical_bytes(row) for row in self.rows)
        self.manifest = {**self.pin, "schema_version": 1, "primary_key": ["revenue_observation_id"],
                         "files": {"records.jsonl": {"sha256": hashlib.sha256(content).hexdigest(),
                                                     "bytes": len(content)}}}
        self.pin["manifest_sha256"] = hashlib.sha256(repository._canonical_bytes(self.manifest)).hexdigest()
        self.product = "cedar_press"
        self.write_catalog()
        for patcher in (
            patch.dict(os.environ, {"CEDAR_PRESS_RELEASE_CATALOG": str(self.catalog)}),
            patch.object(repository, "_release_bytes", side_effect=lambda *a, **k: b"".join(
                repository._canonical_bytes(row) for row in self.rows)),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        fetch = patch.object(repository, "_release_json", side_effect=self.response)
        self.fetch = fetch.start()
        self.addCleanup(fetch.stop)
        self.subscriber = patch.object(subscribers, "find", return_value=subscribers.Subscriber(
            "grove-fixture@example.invalid", "grove", "fixture"))
        self.account = self.subscriber.start()
        self.addCleanup(self.subscriber.stop)
        self.addCleanup(app.dependency_overrides.clear)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def write_catalog(self):
        value = {"schema_version": 1, "product": self.product, "entitlement_required": True,
                 "collections": [self.pin]}
        value["catalog_id"] = hashlib.sha256(repository._canonical_bytes(value)).hexdigest()
        self.catalog.write_text(json.dumps(value), encoding="utf-8")

    def response(self, path):
        return copy.deepcopy(self.manifest)

    def session(self, tier, email="grove-fixture@example.invalid"):
        app.dependency_overrides[current_session] = (
            (lambda: None) if tier is None else (lambda: Session(email, tier)))

    def get(self):
        with self.assertLogs("cedar_press.download", level="INFO") as logs:
            response = self.client.get(self.URL, params={"release_id": self.rid})
        self.assertNotIn("grove-fixture@example", " ".join(logs.output))
        return response, logs.output

    def declared(self):
        """The proposed reviewed Grove declaration, simulated with the existing
        tier model: a grove-shelf dataset that grove and tree already reach."""
        gaming = launch.CollectionDataset(
            id="gaming", name="Gaming Intelligence (fixture)", short_name="Gaming", origin="official",
            level="geography", tracks="fixture", rows_label="fixture", downloads=None, vintage=None,
            version="v0", updated="", sources="NIGC", method="fixture", shelf="grove")
        return patch.object(launch, "LAUNCH_COLLECTION", launch.LAUNCH_COLLECTION + (gaming,))

    def test_current_server_refuses_gaming_to_every_tier_before_any_fetch(self):
        for tier in ("press", "press_pro", "grove", "tree"):
            with self.subTest(tier=tier):
                self.session(tier)
                response, logs = self.get()
                self.assertEqual(response.status_code, 403)
                self.assertIn('"collection_id": "unknown"', logs[0])
        self.fetch.assert_not_called()

    def test_a_cedar_grove_catalog_is_refused_by_the_press_adapter(self):
        self.product = "cedar_grove"
        self.write_catalog()
        self.session("grove")
        with self.declared():
            response, logs = self.get()
        self.assertEqual(response.status_code, 503)
        self.assertIn("unavailable", logs[0])
        self.fetch.assert_not_called()

    @unittest.skipUnless(
        GAMING_KEY in json.loads((ROOT / "data/cedar/field_map.json").read_text(encoding="utf-8"))["tables"],
        "requires the generated gaming field-map entry")
    def test_declared_grove_pin_denies_serves_exact_bytes_and_rolls_back(self):
        expected = b"".join(repository._canonical_bytes(row) for row in self.rows)
        with self.declared():
            for tier, status in [(None, 401), ("press", 403), ("press_pro", 403)]:
                with self.subTest(tier=tier):
                    self.session(tier)
                    self.assertEqual(self.get()[0].status_code, status)
            self.fetch.assert_not_called()
            for tier in ("grove", "tree"):
                self.session(tier)
                self.account.return_value = subscribers.Subscriber(
                    "grove-fixture@example.invalid", tier, "fixture")
                response, logs = self.get()
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.content, expected)
                self.assertEqual(response.headers["x-cedar-sha256"], hashlib.sha256(expected).hexdigest())
                self.assertIn("authorized_prepared", logs[0])
            # Stale account: the same grove cookie after a downgrade, a removal
            # and an account-store outage never reaches the release.
            self.session("grove")
            self.fetch.reset_mock()
            for account, error, status in [
                (subscribers.Subscriber("grove-fixture@example.invalid", "press_pro", "fixture"), None, 403),
                (None, None, 401),
                (None, RuntimeError("secret-store-detail"), 503),
            ]:
                self.account.return_value, self.account.side_effect = account, error
                response, logs = self.get()
                self.assertEqual(response.status_code, status)
                self.assertNotIn("secret-store-detail", response.text + " ".join(logs))
            self.fetch.assert_not_called()
            self.account.return_value = subscribers.Subscriber(
                "grove-fixture@example.invalid", "grove", "fixture")
            self.account.side_effect = None
            # A stale pin is refused; rollback re-selects the approved catalog.
            approved = self.catalog.read_bytes()
            with self.assertLogs("cedar_press.download", level="INFO"):
                self.assertEqual(self.client.get(self.URL, params={"release_id": "d" * 64}).status_code, 503)
            self.catalog.write_text("{}")
            self.assertEqual(self.get()[0].status_code, 503)
            self.catalog.write_bytes(approved)
            response, _ = self.get()
            self.assertEqual((response.status_code, response.content), (200, expected))


if __name__ == "__main__":
    unittest.main()
