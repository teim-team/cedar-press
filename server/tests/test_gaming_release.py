"""Gaming (Cedar Grove) through the existing orchestrator, release pilot and adapter.

All fixtures are fictional and data-less. Three layers, each reusing the
shared path rather than a Gaming copy of it:

* ``code/build.py candidate gaming``: registered producers run in declared
  order into a new isolated root; source-key tokens bound through the Gaming
  ID binding register (reuse across rebuilds, deterministic new ordinals, a
  tampered prior register refused); shared validators, cross-table
  references, the public-release leak gate (PROV-, CCP-, VP-, TPL-,
  CEDAR-FAC-, a composite retired handle, a malformed Gaming ID each refused
  by name), a byte-identical manifest with timings in the volatile log, and
  the change report.
* Every canonical Gaming table and public ID surface: a planted bad value is
  named by both the leak gate and the release refusal.
* ``code/build.py release-pilot gaming``: a multi-component release unit. Two
  synthetic components, each with its own field-map entry, grain, key and
  rights, released through the one projection path into two immutable Lumecon
  releases pinned in ONE ``cedar_grove`` catalog; every declared component
  required; a provisional, vendor, non-CE, non-public-row, non-public-field,
  non-public-status or unmapped component refuses the whole release before any
  artifact is written; then (with fixture identifier bindings standing in for
  the pending allowed-ID contract) exact bytes, determinism, immutable-
  replacement refusal and rollback to a prior verified catalog. Single-flagship
  pilots and single-entry field-map callers are shown unchanged. A Gaming
  object ID ships only when ISSUED in the live binding register, and the
  Lumecon ``registered_reference`` fixture proves a retired handle mapped
  ``id: id`` is refused by Cedar although Lumecon alone would accept it.
* The Cedar server adapter with the reviewed Grove declaration
  (``collections.GROVE_RELEASE_COLLECTIONS``): per-component exact download
  from the pinned Grove catalog for grove/tree, denial before any catalog or
  artifact access for anonymous, press/press_pro and stale accounts, redacted
  audit naming the component, stale-pin refusal and rollback of both
  components; the storefront still neither sells nor previews Gaming.
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
PLACE = "CEDAR-PLACE-000001-6S"   # ordinal 1 with its 503 check characters
RETIRED = "TRBF-FIXTURE-00"        # a fixture retired handle (historical vocabulary only)

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

    LEAKS = {{"leak_prov": "see PROV-GREG-0123456789AB", "leak_ccp": "CCP-45100", "leak_vp": "VP-0101",
             "leak_tpl": "TPL-0127", "leak_fac": "CEDAR-FAC-000013",
             "leak_handle": "{retired}-NIGC-2007-0001", "leak_malformed": "CEDAR-OBS-000000001"}}

    def rows_for(table):
        fac = "{place}"
        grev = gg.derive_id("GREV", "fixture_region", "R1", "2025")
        greg = gg.derive_id("GREG", "FR", "2025-00001")
        if table == "gaming_grove_facilities.csv":
            return [{{"gaming_facility_id": fac, "cedar_uid": "{ce}", "facility_name": "Fictional Casino",
                      "rights_class": "public_official"}}]
        if table == "gaming_regulatory_events.csv":
            ref = "CEDAR-PLACE-000002-CJ" if MODE == "dangling" else fac
            out = [{{"event_id": greg, "gaming_facility_id": ref, "event_date": "2025-01-02",
                     "note": LEAKS.get(MODE, "fixture note"), "rights_class": "public_official"}}]
            if MODE == "added":
                out.append({{"event_id": gg.derive_id("GREG", "FR", "2026-00002"), "gaming_facility_id": fac,
                            "event_date": "2026-03-04", "note": "", "rights_class": "public_official"}})
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
         "event_date": "public_official", "note": "public_official", "rights_class": "public_official"},
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
        # The historical vocabulary the leak gate matches by exact membership.
        (self.source / "data" / "spine" / "cedar_retired_neid_crosswalk.csv").write_text(
            f"retired_neid,cedar_uid\n{RETIRED},{CE}\n", encoding="utf-8")
        self.code = base / "code"
        self.code.mkdir()
        for script, contracts in zip(SCRIPTS, (FACILITIES, EVENTS), strict=True):
            (self.code / script).write_text(
                PRODUCER.format(code=str(CODE), contracts=_py_literal(contracts), place=PLACE, ce=CE,
                                retired=RETIRED),
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

    def run_candidate(self, name, mode="ok", previous=None, bindings=None):
        target = self.base / name
        args = argparse.Namespace(collection="gaming", input_root=str(self.source), owner_dir=None,
                                  output_root=str(target), as_of="2026-09-24",
                                  previous=str(previous) if previous else None,
                                  bindings=str(bindings) if bindings else None)
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
                                      output_root=str(target), as_of="2026-09-24", previous=None, bindings=None)
            with self.subTest(target=target), self.assertRaisesRegex(SystemExit, "REFUSED"):
                BUILD.cmd_candidate(args)
        self.assertFalse((self.source / "candidate").exists())
        self.assertEqual(list(existing.iterdir()), [])

    def test_unregistered_component_is_refused_before_dispatch(self):
        self.registry["contracts"][0]["tables"].pop()
        with self.assertRaisesRegex(SystemExit, "UNREGISTERED_TABLE"):
            self.run_candidate("unregistered")
        self.assertFalse((self.base / "unregistered").exists())

    def bindings(self, target):
        return BUILD._csv_table((target / "components" / gaming_grove.BINDINGS_TABLE).read_bytes())[1]

    def test_ids_are_bound_proposed_in_order_and_never_promotable(self):
        code, target, manifest = self.run_candidate("bound")
        self.assertEqual(code, 0)
        self.assertEqual(manifest["status"], "LOCAL_CANDIDATE_PROPOSED_BINDINGS")
        self.assertEqual([s["command"][0] for s in manifest["steps"]], SCRIPTS)
        self.assertEqual(manifest["provisional_id_values"], 0)
        self.assertTrue(manifest["validation"]["passed"], manifest["validation"])
        self.assertTrue(manifest["leak_gate"]["passed"], manifest["leak_gate"])
        self.assertFalse(manifest["id_binding"]["live_register_written"])
        register = self.bindings(target)
        self.assertEqual({(r["issued_id"], r["key_class"], r["status"]) for r in register},
                         {("CEDAR-OBS-500000001", "GREV", "PROPOSED"), ("CEDAR-EVENT-500001", "GREG", "PROPOSED")})
        events = (target / "components" / EVENTS_TABLE).read_text(encoding="utf-8")
        self.assertIn("CEDAR-EVENT-500001", events)
        self.assertNotIn("GKEY~", events)
        self.assertIn(PLACE, events)                                # the place ID itself, unwrapped
        crosswalk = (target / "components" / gaming_grove.MIGRATION_CROSSWALK_TABLE).read_text(encoding="utf-8")
        self.assertIn("PROV-GREV-", crosswalk)
        self.assertIn("CEDAR-OBS-500000001", crosswalk)
        # The manifest is deterministic: timings and the output root live in the volatile log.
        text = (target / "logs" / "gaming-candidate.json").read_text(encoding="utf-8")
        self.assertNotIn("seconds", text)
        self.assertNotIn(str(target), text)
        volatile = json.loads((target / "logs" / "gaming-candidate.volatile.json").read_text(encoding="utf-8"))
        self.assertEqual(len(volatile["steps"]), 2)
        self.assertIn("seconds", volatile["steps"][0])
        self.assertIn("data/clean/fixture_source.csv", [i["path"] for i in manifest["inputs"]])
        self.assertIn("data/spine/cedar_identity_register.csv", [i["path"] for i in manifest["inputs"]])
        for output in manifest["outputs"]:
            data = (target / "components" / output["table"]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), output["sha256"])

    def test_rebuild_reuses_bindings_and_is_byte_identical(self):
        _, first, _ = self.run_candidate("first")
        _, second, _ = self.run_candidate("second")
        for rel in sorted(p.relative_to(first) for p in first.rglob("*") if p.is_file()):
            if rel.as_posix().endswith(".volatile.json") or rel.suffix == ".log":
                continue
            self.assertEqual((first / rel).read_bytes(), (second / rel).read_bytes(), rel)
        prior = first / "components" / gaming_grove.BINDINGS_TABLE
        code, third, manifest = self.run_candidate("third", mode="added", bindings=prior)
        self.assertEqual(code, 0)
        register = {r["issued_id"]: r for r in self.bindings(third)}
        old = {r["issued_id"]: r for r in self.bindings(first)}
        for issued, row in old.items():
            self.assertEqual(register[issued], row)                 # reused byte-exactly
        new = sorted(set(register) - set(old))
        self.assertEqual(new, ["CEDAR-EVENT-500002"])               # next ordinal in the block
        self.assertEqual(manifest["id_binding"]["summary"]["CEDAR-EVENT"],
                         {"new_PROPOSED": 1, "register_rows": 2, "reused_PROPOSED": 1})
        self.assertEqual(manifest["id_binding"]["prior_register"]["status"], "READ")

    def test_tampered_prior_register_is_refused(self):
        _, first, _ = self.run_candidate("first")
        prior = first / "components" / gaming_grove.BINDINGS_TABLE
        tampered = self.base / "tampered.csv"
        tampered.write_bytes(prior.read_bytes().replace(b"CEDAR-OBS-500000001", b"CEDAR-OBS-000000001"))
        code, _, manifest = self.run_candidate("tampered", bindings=tampered)
        self.assertEqual((code, manifest["status"]), (1, "FAILED_BINDING"))
        self.assertIn("outside the Gaming CEDAR-OBS block", manifest["binding_error"])

    def test_leak_gate_refuses_each_planted_value_by_name(self):
        cases = {"leak_prov": "provisional identifier (PROV-)", "leak_ccp": "vendor/source facility key",
                 "leak_vp": "vendor/source facility key", "leak_tpl": "vendor/source facility key",
                 "leak_fac": "vendor/source facility key", "leak_handle": "retired entity handle",
                 "leak_malformed": "malformed Gaming object identifier"}
        for mode, finding in cases.items():
            with self.subTest(mode=mode):
                code, _, manifest = self.run_candidate(mode, mode=mode)
                self.assertEqual((code, manifest["status"]), (1, "FAILED_LEAK_GATE"))
                named = {(f["surface"], f["column"], f["finding"]) for f in manifest["leak_gate"]["findings"]}
                self.assertIn(("public:" + EVENTS_TABLE, "note", finding), named)
                self.assertIn(("sample:" + EVENTS_TABLE, "note", finding), named)

    def test_approved_candidate_samples_public_fields_and_reports_changes(self):
        code, first, manifest = self.run_candidate("first")
        self.assertEqual((code, manifest["status"]), (0, "LOCAL_CANDIDATE_PROPOSED_BINDINGS"))
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


class PromotionTest(GroveFixture):
    """`grove-promote-bindings`: dry run by default; the controlled step flips
    PROPOSED -> ISSUED only for a verified candidate built from the live
    register, keeps a backup and a promotion log, and never renumbers."""

    def promote(self, candidate, live_root, **kw):
        args = argparse.Namespace(collection="gaming", candidate=str(candidate), live_root=str(live_root),
                                  execute=kw.get("execute", False), decision_id=kw.get("decision_id"),
                                  approved_by=kw.get("approved_by"))
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = BUILD.cmd_grove_promote_bindings(args)
        return code, out.getvalue()

    def test_dry_run_then_controlled_execute_then_reuse(self):
        live_root = self.base / "live"
        live = live_root / gaming_grove.LIVE_BINDINGS
        _, first, _ = self.run_candidate("first", bindings=live)
        code, text = self.promote(first, live_root)
        self.assertEqual(code, 0)
        self.assertIn("DRY RUN", text)
        self.assertFalse(live.exists())
        with self.assertRaisesRegex(SystemExit, "needs --decision-id"):
            self.promote(first, live_root, execute=True)
        self.promote(first, live_root, execute=True, decision_id="FIXTURE-DECISION-1", approved_by="fixture owner")
        status = BUILD.pilot_bindings_status("gaming", live)
        self.assertEqual(status, {"CEDAR-OBS-500000001": "ISSUED", "CEDAR-EVENT-500001": "ISSUED"})
        log = (live.parent / "gaming_id_bindings_promotions.jsonl").read_text(encoding="utf-8")
        self.assertIn("FIXTURE-DECISION-1", log)
        # The old candidate was not built from the register now live: refused.
        with self.assertRaisesRegex(SystemExit, "not built from the live register"):
            self.promote(first, live_root)
        # A rebuild from the live register reuses the ISSUED IDs exactly.
        code, second, manifest = self.run_candidate("second", mode="added", bindings=live)
        self.assertEqual(code, 0)
        rows = {r["issued_id"]: r["status"] for r in self.bindings(second)}
        self.assertEqual(rows, {"CEDAR-OBS-500000001": "ISSUED", "CEDAR-EVENT-500001": "ISSUED",
                                "CEDAR-EVENT-500002": "PROPOSED"})
        # The next promotion keeps a byte copy of the register it replaces.
        before = live.read_bytes()
        self.promote(second, live_root, execute=True, decision_id="FIXTURE-DECISION-2", approved_by="fixture owner")
        backups = list(live.parent.glob(live.name + ".bak_*_pre_promotion"))
        self.assertEqual([b.read_bytes() for b in backups], [before])
        self.assertEqual(set(BUILD.pilot_bindings_status("gaming", live).values()), {"ISSUED"})

    def bindings(self, target):
        return BUILD._csv_table((target / "components" / gaming_grove.BINDINGS_TABLE).read_bytes())[1]

    def test_failed_candidate_cannot_be_promoted(self):
        live_root = self.base / "live"
        _, bad, _ = self.run_candidate("bad", mode="leak_ccp", bindings=live_root / gaming_grove.LIVE_BINDINGS)
        with self.assertRaisesRegex(SystemExit, "candidate status is FAILED_LEAK_GATE"):
            self.promote(bad, live_root)


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

REGION = "gaming_regional_revenue.csv"
EVENTS_TABLE = "gaming_regulatory_events.csv"
REGION_CONTRACT = EVENTS[REGION]
EVENT_CONTRACT = EVENTS[EVENTS_TABLE]
# cedar_ids declares no Gaming identifier contract yet (Codex's file). These
# fixture bindings use a fictional keyed namespace so the release MECHANICS can
# be tested; real Gaming object IDs are exercised by the binding refusals below.
BINDINGS = (
    cedar_ids.IdentifierContract(
        "gaming", REGION, "revenue_observation_id", "FIXTURE-REV", "record", "observation",
        "fixture only: stands in for a declared Gaming identifier contract",
        "fixture: cedar_ids Gaming binding pending", pattern=r"FIXTURE-REV-[0-9]{4}"),
    cedar_ids.IdentifierContract(
        "gaming", EVENTS_TABLE, "event_id", "FIXTURE-EVT", "record", "observation",
        "fixture only: stands in for a declared Gaming identifier contract",
        "fixture: cedar_ids Gaming binding pending", pattern=r"FIXTURE-EVT-[0-9]{4}"),
)
FIXTURE_RIGHTS = {"license": "Fixture public record", "publication_class": "publishable",
                  "redistribution": True, "retrieval": True}
# Two synthetic governed components of one Grove collection, each with its own
# grain, key, rights and field-map entry, declared exactly as a real pilot is.
COMPONENTS = {
    REGION: {"owner": "Fixture regulator (regional totals)", "url": "https://example.invalid/region",
             "rights": FIXTURE_RIGHTS, "caveats": ["fixture region caveat"],
             "time_coverage": "fixture fiscal years"},
    EVENTS_TABLE: {"owner": "Fixture regulator (events)", "url": "https://example.invalid/events",
                   "rights": FIXTURE_RIGHTS, "caveats": ["fixture event caveat"]},
}


@unittest.skipUnless(HAVE_LUMECON, "requires Lumecon Data on PYTHONPATH")
class GamingReleasePilotTest(unittest.TestCase):
    """Two components -> two immutable Lumecon releases pinned in ONE catalog."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.canonical = base / "canonical"
        self.canonical.mkdir()
        self.store = base / "store"
        # The LIVE binding register stand-in (absent = nothing is ISSUED).
        self.live_bindings = base / "live_gaming_id_bindings.csv"
        self.headers = {REGION: list(REGION_CONTRACT["field_rights"]),
                        EVENTS_TABLE: list(EVENT_CONTRACT["field_rights"])}
        self.rows = {
            REGION: [
                {"revenue_observation_id": "FIXTURE-REV-0001", "region_name": "Fictional Region",
                 "fiscal_year": "2025", "ggr_nominal_usd": "100", "internal_estimate": "7",
                 "rights_class": "public_official"},
                {"revenue_observation_id": "FIXTURE-REV-0002", "region_name": "Second Region",
                 "fiscal_year": "2024", "ggr_nominal_usd": "90", "internal_estimate": "",
                 "rights_class": "public_official"},
            ],
            EVENTS_TABLE: [
                {"event_id": "FIXTURE-EVT-0001", "gaming_facility_id": PLACE,
                 "event_date": "2025-01-02", "note": "", "rights_class": "public_official"},
            ],
        }
        self.contracts = {REGION: REGION_CONTRACT, EVENTS_TABLE: EVENT_CONTRACT}
        self.status = {REGION: "public", EVENTS_TABLE: "public"}
        self.entries = dict(cedar_publication.field_map_entries())
        for table, contract in self.contracts.items():
            stem = Path(table).stem
            entry = BUILD.grove_field_map_entry("gaming", "fixture", table, contract)
            self.entries[("gaming", stem)] = dict(entry, key="gaming/" + stem)
        config = dict(BUILD.CP.RELEASE_PILOTS["gaming"], components=COMPONENTS)
        for patcher in (
            # The worktree has no ignored ruling ledger; the fixture rows carry
            # no UEI, so an empty verified-denial set changes nothing.
            patch.object(cedar_publication, "denied_ueis", return_value=frozenset()),
            # The compat cache must not keep fixture entries after the test.
            patch.object(cedar_publication, "_FIELD_MAP", {}),
            patch.object(cedar_publication, "field_map_entries", side_effect=lambda: self.entries),
            patch.object(BUILD, "pilot_table_contract", side_effect=lambda c, t: {
                "primary_key": self.contracts[t]["primary_key"], "grain": self.contracts[t]["grain"],
                "publication_status": self.status[t]}),
            patch.dict(BUILD.CP.RELEASE_PILOTS, {"gaming": config}),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def bind(self):
        bindings = dict(cedar_ids.IDENTIFIER_CONTRACTS)
        for binding in BINDINGS:
            bindings[binding.binding] = binding
        return patch.object(cedar_ids, "IDENTIFIER_CONTRACTS", MappingProxyType(bindings))

    def write(self, table, rows=None, header=None):
        path = self.canonical / table
        path.write_bytes(BUILD._csv_bytes(header or self.headers[table], rows or self.rows[table]))
        return path

    def write_all(self):
        return [self.write(table) for table in (REGION, EVENTS_TABLE)]

    def pilot(self, sources, as_of="2026-09-24"):
        args = argparse.Namespace(collection="gaming", source=[str(s) for s in sources],
                                  output_root=str(self.store), as_of=as_of, bindings=str(self.live_bindings))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            BUILD.cmd_release_pilot(args)
        return json.loads(out.getvalue().strip().splitlines()[-1])

    def assert_nothing_written(self):
        self.assertFalse((self.store / "releases").exists())
        self.assertFalse((self.store / "intake").exists())
        self.assertFalse((self.store / "catalogs").exists())

    def test_every_declared_component_is_required_and_named(self):
        region, events = self.write_all()
        stray = self.write("gaming_facilities.csv", header=["facility_id"], rows=[{"facility_id": "x"}])
        cases = [
            ([region], "missing gaming_regulatory_events.csv"),
            ([region, events, stray], "no declared component: gaming_facilities.csv"),
            ([region, events, region], "supplied twice"),
        ]
        for sources, message in cases:
            with self.subTest(message=message), self.bind(), self.assertRaisesRegex(SystemExit, message):
                self.pilot(sources)
        config = dict(BUILD.CP.RELEASE_PILOTS["gaming"])
        with self.assertRaisesRegex(SystemExit, "replaced flagship cannot be a release component"):
            BUILD.pilot_units("gaming", dict(config, components={**COMPONENTS, "gaming_facilities.csv": {}}),
                              cedar_publication.FLAGSHIP, [region, events, stray])
        with self.assertRaisesRegex(SystemExit, "replaced flagship"):
            BUILD.pilot_table("gaming", dict(config, table="gaming_facilities.csv"), cedar_publication.FLAGSHIP)
        with self.assertRaisesRegex(SystemExit, "disagrees"):
            BUILD.pilot_table("gaming", config, {"gaming": "other.csv"})
        self.assert_nothing_written()

    def test_a_refused_component_stops_the_whole_release(self):
        """One bad component refuses the collection before ANY artifact is written."""
        def events_with(**changes):
            rows = copy.deepcopy(self.rows[EVENTS_TABLE])
            rows[0].update(changes)
            return rows
        cases = [
            (events_with(note="PROV-GREG-0123456789AB"), None,
             "gaming_regulatory_events.csv: provisional identifier \\(PROV-\\) in note"),
            (events_with(note=gaming_grove.derive_id("GREG", "FR", "x")), None, "unbound identifier key token in note"),
            (events_with(gaming_facility_id="CCP-1234"), None,
             "vendor-lineage or source facility key in gaming_facility_id"),
            (events_with(note="CEDAR-FAC-000013"), None, "vendor-lineage or source facility key in note"),
            (events_with(gaming_facility_id="CEDAR-PLACE-000001-AB"), None,
             "facility identifier is not a checked CEDAR-PLACE in gaming_facility_id"),
            (events_with(note="TRBF-POARCH-00-NIGC-2007-0011-0010"), None, "retired entity handle in note"),
            (events_with(note="CEDAR-OBS-500000001"), None,
             "identifier binding ABSENT \\(not ISSUED in the live Gaming ID binding register\\) in note"),
            (events_with(rights_class="secondary_corroboration"), None,
             "row rights class\\(es\\) not public: secondary_corroboration"),
            (events_with(rights_class="internal_vendor"), None, "not public: internal_vendor"),
            (events_with(cedar_uid="TRBF-0001"), self.headers[EVENTS_TABLE] + ["cedar_uid"],
             "non-CE entity identifier in cedar_uid"),
        ]
        for rows, header, message in cases:
            with self.subTest(message=message), self.bind():
                region = self.write(REGION)
                events = self.write(EVENTS_TABLE, rows=rows, header=header)
                with self.assertRaisesRegex(SystemExit, "REFUSED: .*" + message):
                    self.pilot([region, events])
        self.assert_nothing_written()

    def test_non_public_field_rights_status_or_unmapped_component_is_refused(self):
        region, events = self.write_all()
        key = ("gaming", "gaming_regulatory_events")
        original = self.entries[key]
        leaked = copy.deepcopy(original)
        for field in leaked["fields"]:
            if field["column"] == "event_date":
                field["rights_class"] = "internal_model"
        self.entries[key] = leaked
        with self.bind(), self.assertRaisesRegex(SystemExit, "field event_date ships with rights class internal_model"):
            self.pilot([region, events])
        undeclared = copy.deepcopy(original)
        for field in undeclared["fields"]:
            field.pop("rights_class")
        self.entries[key] = undeclared
        with self.bind(), self.assertRaisesRegex(SystemExit, "rights class UNDECLARED"):
            self.pilot([region, events])
        self.entries[key] = original
        self.status[EVENTS_TABLE] = "source_limited"
        with self.bind(), self.assertRaisesRegex(SystemExit, "source_limited, not public"):
            self.pilot([region, events])
        self.status[EVENTS_TABLE] = "public"
        self.entries.pop(key)
        with self.bind(), self.assertRaisesRegex(
                SystemExit, "no approved field-map entry for this flagship component gaming_regulatory_events.csv"):
            self.pilot([region, events])
        self.assert_nothing_written()

    def test_release_waits_for_the_identifier_contract(self):
        with self.assertRaisesRegex(SystemExit, "no declared identifier binding"):
            self.pilot(self.write_all())
        self.assert_nothing_written()

    def write_live_bindings(self, status):
        rows = [{"object_prefix": "CEDAR-OBS", "key_class": "GREV", "source_key": '["GREV","fixture"]',
                 "source_key_sha256": gaming_grove.source_key_sha256('["GREV","fixture"]'),
                 "issued_id": "CEDAR-OBS-500000001", "table": REGION, "column": "revenue_observation_id",
                 "status": status, "first_seen_as_of": "2026-09-24"}]
        self.live_bindings.write_bytes(gaming_grove.csv_bytes(gaming_grove.BINDING_HEADER, rows))

    def test_gaming_ids_ship_only_when_issued_in_the_live_register(self):
        """A candidate's PROPOSED binding cannot ship; an ISSUED one passes the
        binding check and then waits on the cedar_ids Gaming contract (Codex)."""
        rows = copy.deepcopy(self.rows[REGION])
        rows[0]["revenue_observation_id"] = "CEDAR-OBS-500000001"
        region = self.write(REGION, rows=rows)
        events = self.write(EVENTS_TABLE)
        for status, message in ((None, "identifier binding ABSENT"), ("PROPOSED", "identifier binding PROPOSED")):
            if status:
                self.write_live_bindings(status)
            with self.subTest(status=status), self.bind(), self.assertRaisesRegex(
                    SystemExit, "REFUSED: gaming_regional_revenue.csv: " + message + " .*revenue_observation_id"):
                self.pilot([region, events])
        self.write_live_bindings("ISSUED")
        with self.assertRaisesRegex(SystemExit, "no declared identifier binding"):
            self.pilot([region, events])
        self.assert_nothing_written()

    def test_lumecon_registered_reference_fixture_refuses_a_retired_handle(self):
        """Cross-repository fixture (docs/IDENTIFIER_STANDARD.md 2026-09-24):
        Lumecon's registered_reference checks pinned membership only, so it
        ACCEPTS `TRBF-X-00: TRBF-X-00`; Cedar must refuse that mapping before
        any intake, even when the handle sits in the pinned register."""
        from lumecon_data.contracts import IdentityBinding
        handle = "TRBF-POARCH-00"
        accepted = IdentityBinding.model_validate({
            "mode": "registered_reference", "source_field": "cedar_uid", "target_field": "cedar_uid",
            "namespace": "native_entity", "registry_version": "fixture", "approved_by": "fixture",
            "approved_on": "2026-09-24", "mapping": {handle: handle}})
        self.assertEqual(accepted.mapping, {handle: handle})        # the boundary Cedar must guard
        with self.assertRaisesRegex(SystemExit, "registered_reference mapping would bless .*" + handle):
            BUILD.pilot_registered_reference({CE, handle})
        retired = BUILD.RetiredHandleMatcher(None, {handle})
        self.assertEqual(BUILD.pilot_registered_reference({CE}, retired), {CE: CE})
        header = self.headers[EVENTS_TABLE] + ["cedar_uid"]
        rows = copy.deepcopy(self.rows[EVENTS_TABLE])
        rows[0]["cedar_uid"] = handle
        region = self.write(REGION)
        events = self.write(EVENTS_TABLE, rows=rows, header=header)
        with patch.object(cedar_publication, "register", return_value={handle: ("x", "y"), CE: ("x", "y")}), \
                self.bind(), self.assertRaisesRegex(SystemExit, "REFUSED: .*(non-CE entity identifier|retired entity handle) in cedar_uid"):
            self.pilot([region, events])
        self.assert_nothing_written()

    def test_two_components_one_catalog_exact_bytes_immutability_and_rollback(self):
        from lumecon_data.catalog import manifest_metadata
        from lumecon_data.pipeline import verify_release
        from lumecon_data.storage import canonical_json, immutable_bytes
        with self.bind():
            first = self.pilot(self.write_all())
            again = self.pilot(self.write_all())
        self.assertEqual(first, again)                       # deterministic, same catalog
        ids = {c["table"]: c for c in first["components"]}
        self.assertEqual([c["dataset_id"] for c in first["components"]],
                         ["gaming--gaming_regional_revenue", "gaming--gaming_regulatory_events"])
        self.assertEqual((ids[REGION]["record_count"], ids[EVENTS_TABLE]["record_count"]), (2, 1))
        catalog_a = json.loads(Path(first["catalog"]).read_text(encoding="utf-8"))
        self.assertEqual(catalog_a["product"], "cedar_grove")
        self.assertEqual({(p["dataset_id"], p["release_id"]) for p in catalog_a["collections"]},
                         {(c["dataset_id"], c["release_id"]) for c in first["components"]})
        before = {}
        for table, component in ids.items():
            release = self.store / "releases" / component["dataset_id"] / component["release_id"]
            records = release / "records.jsonl"
            lines = [json.loads(line) for line in records.read_bytes().splitlines()]
            order = self.entries[("gaming", Path(table).stem)]["order"]
            self.assertEqual([set(row) for row in lines], [set(order)] * len(self.rows[table]))
            self.assertNotIn(b"internal_estimate", records.read_bytes())
            before[table] = {p.name: p.read_bytes() for p in release.iterdir()}
            with self.assertRaises(ValueError):
                immutable_bytes(records, b'{"replaced": true}\n')
            self.assertEqual(records.read_bytes(), before[table]["records.jsonl"])
        # A change to ONE component: a new release for it, the sibling's release
        # ID unchanged, and a new catalog pinning both.
        changed = copy.deepcopy(self.rows[REGION])
        changed[0]["ggr_nominal_usd"] = "101"
        with self.bind():
            second = self.pilot([self.write(REGION, rows=changed), self.write(EVENTS_TABLE)], as_of="2026-09-25")
        after = {c["table"]: c for c in second["components"]}
        self.assertNotEqual(after[REGION]["release_id"], ids[REGION]["release_id"])
        self.assertNotEqual(second["catalog"], first["catalog"])
        # Rollback = select the prior verified catalog: every pin it names still
        # verifies and matches its manifest digest; no release byte changed.
        for pin in catalog_a["collections"]:
            manifest = verify_release(self.store, pin["dataset_id"], pin["release_id"])
            self.assertEqual(pin["manifest_sha256"],
                             hashlib.sha256(canonical_json(manifest_metadata(manifest))).hexdigest())
        for table, component in ids.items():
            release = self.store / "releases" / component["dataset_id"] / component["release_id"]
            self.assertEqual({p.name: p.read_bytes() for p in release.iterdir()}, before[table])
        for component in second["components"]:
            verify_release(self.store, component["dataset_id"], component["release_id"])


class SingleFlagshipUnchangedTest(unittest.TestCase):
    """Press pilots and single-entry field-map callers see the old behaviour."""

    def test_single_flagship_units_and_dataset_ids_are_unchanged(self):
        for collection in ("legislation", "natural-resources"):
            config = BUILD.CP.RELEASE_PILOTS[collection]
            self.assertNotIn("components", config)
            table = cedar_publication.FLAGSHIP[collection]
            with tempfile.TemporaryDirectory() as temp:
                source = Path(temp) / table
                units = BUILD.pilot_units(collection, config, cedar_publication.FLAGSHIP, [source])
                self.assertEqual(units, [(table, source.resolve(), collection, config)])
                with self.assertRaisesRegex(SystemExit, "exactly one --source"):
                    BUILD.pilot_units(collection, config, cedar_publication.FLAGSHIP, [source, source])
                with self.assertRaisesRegex(SystemExit, "must match the declared flagship"):
                    BUILD.pilot_units(collection, config, cedar_publication.FLAGSHIP, [Path(temp) / "x.csv"])
            self.assertEqual(BUILD.release_dataset_id(collection), collection)

    def test_compat_field_map_matches_the_keyed_accessor_for_single_entry_collections(self):
        entries = cedar_publication.field_map_entries()
        compat = cedar_publication.field_map()
        for collection, entry in compat.items():
            mine = [e for (c, _), e in entries.items() if c == collection]
            if len(mine) == 1:
                self.assertEqual(cedar_publication.field_map_entry(collection)["key"], entry["key"])
            self.assertEqual(entry["key"], mine[0]["key"])
        self.assertIsNone(cedar_publication.field_map_entry("fixture-unmapped"))

    def test_a_multi_component_collection_needs_a_named_component(self):
        entries = dict(cedar_publication.field_map_entries())
        for table, contract in ((REGION, REGION_CONTRACT), (EVENTS_TABLE, EVENT_CONTRACT)):
            stem = Path(table).stem
            entries[("gaming", stem)] = dict(
                BUILD.grove_field_map_entry("gaming", "fixture", table, contract), key="gaming/" + stem)
        with patch.object(cedar_publication, "field_map_entries", return_value=entries):
            with self.assertRaisesRegex(SystemExit, "2 component entries"):
                cedar_publication.field_map_entry("gaming")
            with self.assertRaises(cedar_publication.FieldMapRefusal):
                cedar_publication.apply_field_map("gaming", ["event_id"], [], {"event_id"})
            self.assertEqual(cedar_publication.field_map_entry("gaming", EVENTS_TABLE)["key"],
                             "gaming/gaming_regulatory_events")
            self.assertEqual(cedar_publication.field_map_entry("gaming", "gaming_regional_revenue")["key"],
                             "gaming/gaming_regional_revenue")


# ---------------------------------------------------------------- every canonical table
def _real_gaming_contracts():
    """{table: contract} from the registered Gaming producers (no data read)."""
    out = {}
    for script in BUILD.CP.GROVE_COMPONENTS["gaming"]:
        spec = importlib.util.spec_from_file_location("contracts_" + Path(script).stem, CODE / script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        out.update(module.CONTRACTS)
    return out


PLANTED = {
    "PROV-GREV-0123456789AB": ("provisional identifier (PROV-)", "provisional identifier (PROV-)"),
    "CCP-45100": ("vendor/source facility key", "vendor-lineage or source facility key"),
    "VP-0101": ("vendor/source facility key", "vendor-lineage or source facility key"),
    "TPL-0127": ("vendor/source facility key", "vendor-lineage or source facility key"),
    "CEDAR-FAC-000013": ("vendor/source facility key", "vendor-lineage or source facility key"),
    RETIRED + "-NIGC-2007-0001": ("retired entity handle", "retired entity handle"),
    "CEDAR-OBS-000000001": ("malformed Gaming object identifier", "identifier binding ABSENT"),
    "CEDAR-EVENT-500001": (None, "identifier binding PROPOSED"),
}


class EveryCanonicalTableRefusesPlantedIdsTest(unittest.TestCase):
    """For every canonical Gaming table, every public ID surface (declared
    public ID columns, bound component-ID columns and one public text column)
    refuses each planted value BY NAME, in both the candidate leak gate and the
    release refusal. Rows are synthetic; nothing is read from data."""

    @classmethod
    def setUpClass(cls):
        cls.contracts = _real_gaming_contracts()
        cls.retired = BUILD.RetiredHandleMatcher(None, {RETIRED})
        cls.status = {"CEDAR-EVENT-500001": "PROPOSED"}

    def surfaces(self, contract):
        rights = contract["field_rights"]
        public = [c for c in rights if rights[c] in gaming_grove.PUBLIC_RIGHTS and c != "rights_class"]
        ids = [c for c in list(contract.get("public_id_columns", [])) + list(contract.get("derived_ids", {}))
               if c in public]
        text = [c for c in public if c not in ids and not c.endswith("cedar_uid")][:1]
        return sorted(set(ids + text))

    def test_the_matrix_covers_every_registered_table(self):
        self.assertEqual(len(self.contracts), 25)
        self.assertTrue(all(self.surfaces(c) for t, c in self.contracts.items()
                            if any(v in gaming_grove.PUBLIC_RIGHTS for v in c["field_rights"].values())))

    def test_planted_values_are_refused_by_name_on_every_public_surface(self):
        for table, contract in sorted(self.contracts.items()):
            header = list(contract["field_rights"])
            for column in self.surfaces(contract):
                for value, (gate_finding, release_refusal) in PLANTED.items():
                    row = {c: "" for c in header}
                    row["rights_class"] = "public_official"
                    row[column] = value
                    keep, public = gaming_grove.public_projection(table, header, [row], contract["field_rights"])
                    with self.subTest(table=table, column=column, value=value):
                        self.assertIn(column, keep)
                        found = gaming_grove.leak_findings(table, keep, public, retired_pattern=self.retired)
                        if gate_finding:
                            self.assertIn((gate_finding, column), found)
                        refused = BUILD.pilot_identifier_refusals(public, retired_pattern=self.retired,
                                                                  bindings_status=self.status)
                        self.assertTrue(any(r.startswith(release_refusal) and r.endswith(" in " + column)
                                            for r in refused), refused)

    def test_non_ce_uid_and_unchecked_place_are_named(self):
        header = ["cedar_uid", "gaming_facility_id", "enterprise_id"]
        row = {"cedar_uid": "TRBF-0001", "gaming_facility_id": "CEDAR-PLACE-000001-AB",
               "enterprise_id": "CEDAR-NEST-000001-AB"}
        found = gaming_grove.leak_findings("x", header, [row])
        self.assertIn(("non-CE entity identifier", "cedar_uid"), found)
        self.assertIn(("unchecked facility identifier", "gaming_facility_id"), found)
        self.assertIn(("non-NEED enterprise identifier", "enterprise_id"), found)
        found = gaming_grove.leak_findings("x", ["note"], [{"note": gaming_grove.derive_id("GREV", "k")}])
        self.assertIn(("unbound key token", "note"), found)


class GamingBlocksTest(unittest.TestCase):
    """The Gaming static blocks are declared through the ID service, so the
    shared allocator steps over them and a colliding declaration is refused."""

    def test_allocate_steps_over_every_gaming_block(self):
        import cedar_ids as ids
        with tempfile.TemporaryDirectory() as temp, \
                patch.object(ids, "REGISTRY", Path(temp) / "_id_registry.json"), \
                patch.object(ids, "LOCK", Path(temp) / "_id_registry.lock"):
            for prefix, (lo, hi) in gaming_grove.GAMING_BLOCKS.items():
                (Path(temp) / "_id_registry.json").write_text(
                    json.dumps({"counters": {prefix: lo - 2}, "types": {}}), encoding="utf-8")
                got = ids.allocate(prefix, 2)
                self.assertEqual(got, [ids.format_id(prefix, lo - 1), ids.format_id(prefix, hi + 1)], prefix)
                self.assertIsNone(gaming_grove.issued_ordinal(got[1]))

    def test_overlapping_declaration_by_another_owner_is_refused(self):
        import cedar_ids as ids
        lo, hi = gaming_grove.GAMING_BLOCKS["CEDAR-REL"]
        with self.assertRaises(ids.IdCollision):
            ids.declare_static_block("CEDAR-REL", hi, hi + 10, "someone else", "fixture")
        ids.declare_static_block("CEDAR-REL", lo, hi, gaming_grove.BLOCK_OWNER, gaming_grove.BLOCK_WHY)  # idempotent

    def test_new_keys_take_block_ordinals_in_sorted_hash_order(self):
        tokens = {gaming_grove.derive_id("GPAY", "src", str(i)): {"table": "t.csv", "column": "id"}
                  for i in range(5)}
        mapping, rows, _ = gaming_grove.assign_bindings(tokens, [], "2026-09-24")
        by_hash = sorted(rows, key=lambda r: r["source_key_sha256"])
        self.assertEqual([r["issued_id"] for r in by_hash],
                         [f"CEDAR-EVENT-{500001 + i}" for i in range(5)])
        again, rows2, summary = gaming_grove.assign_bindings(tokens, rows, "2026-09-25")
        self.assertEqual(again, mapping)
        self.assertEqual(rows2, rows)
        self.assertEqual(summary["CEDAR-EVENT"], {"register_rows": 5, "reused_PROPOSED": 5})


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
