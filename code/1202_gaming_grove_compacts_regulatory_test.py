"""Tests for 1202 (Gaming Grove lane E: compacts, regulatory events, land,
environment, licences, litigation).

Synthetic fixtures only - no live data. Each test names the failure mode it
guards: a declination read as an approval, a decision date promoted to an
opening, a compact rate emitted as a payment, the same Federal Register notice
counted twice, a rescission overwriting the approval it reverses, a legacy
TRBF- handle leaking into cedar_uid, and non-deterministic output.

    py -3 code/1202_gaming_grove_compacts_regulatory_test.py
"""
from __future__ import annotations

import csv
import importlib.util
import os
import shutil
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("lane_e", HERE / "1202_gaming_grove_compacts_regulatory.py")
lane = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lane)
gg = lane.gg

UID_A = "CE-0013Z-D0"   # real, check-char-valid CE uids (shape only matters here)
UID_B = "CE-001BR-BH"
FRNUM = "2024-11111"
FR_URL = f"https://www.federalregister.gov/documents/2024/05/20/{FRNUM}/indian-gaming"


def _write(root: Path, rel: str, rows: list[dict], header: list[str] | None = None):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    header = header or (list(dict.fromkeys(k for r in rows for k in r)) if rows else ["id"])
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header)
        w.writeheader()
        w.writerows(rows)


def fixture(root: Path, *, compact_uid=UID_A, include_fa=True):
    c = "data/clean/"
    _write(root, c + "compacts.csv", [{
        "compact_id": "CMP-AZ-test-20240520", "tribe": "Test Tribe", "state": "Arizona",
        "approval_type": "secretarial", "bia_decision": "Approve", "bia_decision_date": "2024-05-01",
        "original_effective_date": "2024-05-20", "FR_citation": f"FR Doc. {FRNUM}",
        "FR_notice_url": FR_URL, "status": "active", "instrument_type": "compact",
        "tribe_id": "TRBF-TEST-00", "entity_id": "TRBF-TEST-00", "cedar_uid": compact_uid,
        "source_url": "https://www.bia.gov/x.pdf"}])
    _write(root, c + "compact_versions.csv", [{
        "version_id": "CMP-AZ-test-20240520-V01", "compact_id": "CMP-AZ-test-20240520",
        "approval_date": "2024-05-20", "FR_citation": f"FR Doc. {FRNUM}", "FR_notice_url": FR_URL,
        "version_role": "original-instrument", "bia_decision": "Approve", "approval_type": "secretarial",
        "bia_decision_date": "2024-05-01", "bia_title": "Test Compact", "version_seq": "1",
        "source_url": "https://www.bia.gov/x.pdf"}])
    _write(root, c + "compact_structured_terms.csv", [
        {"term_id": "CTM-1", "compact_id": "CMP-AZ-test-20240520", "version_id": "CMP-AZ-test-20240520-V01",
         "term_field": "revenue_sharing_rate", "value": "8", "value_numeric": "8", "unit": "percent",
         "revenue_concept": "net win", "cedar_uid": compact_uid, "state": "Arizona",
         "source_quote": "shall pay 8% of net win", "fetched_date": "2026-08-05"},
        {"term_id": "CTM-2", "compact_id": "CMP-AZ-test-20240520", "version_id": "CMP-AZ-test-20240520-V01",
         "term_field": "expiration_date", "value": "2044-05-20", "unit": "date", "cedar_uid": compact_uid,
         "state": "Arizona", "fetched_date": "2026-08-05"}])
    _write(root, c + "compact_terms.csv", [
        {"version_id": "CMP-AZ-test-20240520-V01", "compact_id": "CMP-AZ-test-20240520",
         "term_type": "exclusivity", "value": "exclusive right", "unit": "text", "source_page": "4",
         "quote": "the State shall not authorize", "cedar_uid": compact_uid},
        {"version_id": "CMP-AZ-test-20240520-V01", "compact_id": "CMP-AZ-test-20240520",
         "term_type": "revenue_share_rate", "value": "8", "unit": "percent", "source_page": "9",
         "quote": "8%", "cedar_uid": compact_uid}])
    _write(root, c + "gaming_land_decisions.csv", [{
        "decision_id": "GLD-CA-test-20250110", "tribe": "Test Band", "state_abbr": "CA",
        "legal_theory": "Restored Lands", "decision_status": "Approved", "decision_date": "2025-01-10",
        "federal_register_doc_number": FRNUM, "federal_register_date": "2024-05-20",
        "federal_register_url": FR_URL, "cedar_uid": UID_B, "source_url": "https://www.bia.gov/gld",
        "fetched_date": "2026-08-05", "bia_note_text":
            "Approved on remand from Test Band v. U.S. Dep't of the Interior , 633 F. Supp. 3d 132, 171 (D.D.C. 2022).",
        "document_urls": "https://www.bia.gov/rod.pdf|https://www.bia.gov/app.pdf",
        "document_labels": "Record of Decision|Appendix A",
        "document_types": "record_of_decision|record_of_decision+appendix"}])
    _write(root, c + "gaming_decision_events.csv", [
        {"event_id": "GLD-CA-test-20250110-E01", "decision_id": "GLD-CA-test-20250110",
         "event_date": "2025-01-10", "event_type": "decision_approved", "tribe": "Test Band",
         "evidence_text": 'Decision Status="Approved"'},
        {"event_id": "GLD-CA-test-20250110-E02", "decision_id": "GLD-CA-test-20250110",
         "event_date": "2024-05-20", "event_type": "federal_register_land_acquisition_notice",
         "document_url": FR_URL, "tribe": "Test Band"},
        {"event_id": "GLD-CA-test-20250110-E04", "decision_id": "GLD-CA-test-20250110",
         "event_date": "2025-03-27", "event_type": "rescission_stated_in_note", "tribe": "Test Band",
         "evidence_text": "Gaming eligibility decision temporarily rescinded effective March 27, 2025."}])
    _write(root, c + "gaming_project_facilities.csv", [{
        "project_id": "TEST-PROJ", "decision_id": "GLD-CA-test-20250110", "projected_opening": "2027-01",
        "construction_start": "2026 (assumed)", "observation_status": "proposed"}])
    _write(root, c + "nigc_declination_letters.csv", [{
        "cedar_opinion_id": "NIGC-DL-20250101-01", "opinion_date": "2025-01-01",
        "is_management_contract": "NO_NOT_A_MANAGEMENT_CONTRACT", "cedar_uid": UID_A,
        "tribe_entity_id": "TRBF-TEST-00", "re_line": "Review of Loan Documents"}])
    _write(root, c + "nigc_enforcement_actions.csv", [{
        "action_id": "NIGCEA-1", "action_type": "NOV", "action_code": "NOV-25-01",
        "document_date": "", "index_post_date": "2025-02-01", "cedar_uid": UID_A}])
    _write(root, c + "nigc_management_contract_approvals.csv", [], ["action_id", "cedar_uid"])
    _write(root, c + "nigc_indian_lands_opinions.csv", [], ["opinion_id", "cedar_uid"])
    _write(root, c + "gaming_ordinances.csv", [], ["ordinance_id", "cedar_uid"])
    if include_fa:
        _write(root, c + "federal_actions.csv", [
            {"document_number": FRNUM, "publication_date": "2024-05-20", "title": "Indian Gaming",
             "abstract": "notice of approved Tribal-State Compact", "type": "Notice", "action": "Notice.",
             "agency_names": "Interior Department", "agency_slugs": "interior-department",
             "action_type": "tribal_state_compact", "html_url": FR_URL, "docket_ids": "",
             "fetched_date": "2026-08-05"},
            {"document_number": "2024-22222", "publication_date": "2024-06-01", "title": "Housing grants",
             "abstract": "", "type": "Notice", "action": "", "agency_names": "", "agency_slugs": "",
             "action_type": "other", "html_url": "", "docket_ids": "", "fetched_date": "2026-08-05"}])


class LaneETest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "in"
        fixture(self.root)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_build(self, out="out"):
        o = self.tmp / out
        res = lane.build(gg.Inputs(self.root), o)
        tables = {}
        for t in res["tables"]:
            with (o / t["table"]).open(encoding="utf-8", newline="") as fh:
                r = csv.DictReader(fh)
                tables[t["table"]] = (r.fieldnames, list(r))
        return res, tables, o

    def test_declination_never_mapped_to_approval(self):
        _, t, _ = self.run_build()
        ev = [r for r in t["gaming_regulatory_events.csv"][1] if r["source_record_id"] == "NIGC-DL-20250101-01"]
        self.assertEqual(len(ev), 1)
        self.assertEqual(ev[0]["status"], "declination_issued")
        self.assertNotIn(ev[0]["status"], lane.APPROVAL_STATUSES)
        bad = {c: "" for c in lane.EVENT_COLUMNS}
        bad.update(event_type="nigc_declination_letter", status="approved", source_record_id="x")
        with self.assertRaises(gg.GamingContractError):
            lane._guard_event(bad)

    def test_decision_date_never_becomes_opening(self):
        _, t, _ = self.run_build()
        for name, (header, rows) in t.items():
            self.assertFalse([h for h in header if "open" in h.lower()], name)
            for r in rows:
                self.assertNotIn("2027-01", r.values(), name)   # applicant projected opening
        land = t["gaming_land_eligibility.csv"][1]
        bia = [r for r in land if r["decision_id"] == "GLD-CA-test-20250110"][0]
        self.assertEqual(bia["decision_date"], "2025-01-10")
        ev = t["gaming_regulatory_events.csv"][1]
        self.assertTrue(all(r["gaming_facility_id"] == "" for r in ev if r["decision_id"]))

    def test_compact_rate_never_emitted_as_payment(self):
        _, t, _ = self.run_build()
        header, rows = t["gaming_compact_terms.csv"]
        rate = [r for r in rows if r["term_id"] == "CTM-1"][0]
        self.assertEqual(rate["value_semantics"], "contractual_rate")
        self.assertEqual(rate["is_payment_observation"], "no")
        self.assertFalse([h for h in header if "paid" in h or "payment_amount" in h or h.endswith("_usd")])
        # the view's revenue_share_rate duplicates the structured family and is not re-emitted
        self.assertEqual(sum(1 for r in rows if r["term_source_table"] == "compact_terms"), 1)
        c = lane.CONTRACTS["gaming_compact_terms.csv"]
        bad = dict(rate, is_payment_observation="yes")
        self.assertTrue(gg.validate_rows("t", header, [bad], c))

    def test_same_fr_document_in_several_tables_is_one_event(self):
        _, t, _ = self.run_build()
        ev = [r for r in t["gaming_regulatory_events.csv"][1] if r["fr_document_number"] == FRNUM]
        self.assertEqual(len(ev), 1)
        cites = ev[0]["also_cited_by"].split("|")
        for expected in (f"compact_versions:CMP-AZ-test-20240520-V01", f"federal_actions:{FRNUM}",
                         "compacts:CMP-AZ-test-20240520", "gaming_land_decisions:GLD-CA-test-20250110",
                         "gaming_decision_events:GLD-CA-test-20250110-E02"):
            self.assertIn(expected, cites)
        self.assertEqual(ev[0]["event_type"], "compact_fr_notice")   # highest-precedence source kept
        self.assertEqual(ev[0]["compact_id"], gg.derive_id("GCMP", "CMP-AZ-test-20240520"))   # bound later to CEDAR-CONTRACT
        self.assertEqual(ev[0]["decision_id"], "GLD-CA-test-20250110")
        self.assertEqual(ev[0]["regulatory_event_id"], gg.derive_id("GREG", "FR", FRNUM))
        # an unrelated FR row is filtered out, not emitted
        self.assertFalse([r for r in t["gaming_regulatory_events.csv"][1] if r["fr_document_number"] == "2024-22222"])

    def test_approval_then_rescission_survive_as_two_events(self):
        _, t, _ = self.run_build()
        ev = [r for r in t["gaming_regulatory_events.csv"][1]
              if r["decision_id"] == "GLD-CA-test-20250110" and r["source_system"] != "federal_register"]
        by_status = {r["status"]: r for r in ev}
        self.assertIn("approved", by_status)
        self.assertIn("rescinded", by_status)
        self.assertEqual(by_status["approved"]["action_date"], "2025-01-10")
        self.assertEqual(by_status["rescinded"]["action_date"], "2025-03-27")
        self.assertNotEqual(by_status["approved"]["regulatory_event_id"],
                            by_status["rescinded"]["regulatory_event_id"])
        land = [r for r in t["gaming_land_eligibility.csv"][1] if r["decision_id"] == "GLD-CA-test-20250110"][0]
        self.assertEqual(land["current_status"], "approved")           # index state kept as published
        self.assertEqual(land["latest_subsequent_action"], "rescinded")

    def test_legacy_handle_never_becomes_cedar_uid(self):
        shutil.rmtree(self.root)
        fixture(self.root, compact_uid="TRBF-TEST-00")
        res, t, _ = self.run_build()
        self.assertEqual(t["gaming_compacts.csv"][1][0]["cedar_uid"], "")
        for name, (header, rows) in t.items():
            for r in rows:
                self.assertFalse(any(str(v).startswith("TRBF-") for v in r.values()), name)
        self.assertTrue(any(x["prefix"] == "TRBF-" for x in res["coverage"]["legacy_id_values_in_inputs"]))

    def test_litigation_parsed_from_note_and_deduped(self):
        _, t, _ = self.run_build()
        lit = t["gaming_litigation.csv"][1]
        self.assertEqual(len(lit), 1)
        self.assertEqual(lit[0]["reporter_citation"], "633 F. Supp. 3d 132")
        self.assertEqual(lit[0]["forum"], "D.D.C.")
        self.assertEqual(lit[0]["party_cedar_uids"], "")          # subject of the decision is not a party
        self.assertEqual(lit[0]["affected_subject_cedar_uid"], UID_B)

    def test_environmental_appendix_not_rowed_and_projection_counts_only(self):
        res, t, _ = self.run_build()
        env = t["gaming_environmental_reviews.csv"][1]
        self.assertEqual([r["document_role"] for r in env], ["record_of_decision"])
        self.assertEqual(res["withheld"]["environmental.appendix_documents_not_rowed"], 1)

    def test_rerun_is_byte_identical(self):
        r1, _, o1 = self.run_build("a")
        r2, _, o2 = self.run_build("b")
        self.assertEqual([t["sha256"] for t in r1["tables"]], [t["sha256"] for t in r2["tables"]])

    def test_missing_required_input_refused(self):
        (self.root / "data/clean/compacts.csv").unlink()
        with self.assertRaises(SystemExit):
            self.run_build()

    def test_compact_key_is_source_id_never_public_identity(self):
        """The BIA-index key names a tribe and a date: compact_id / version_id
        are CEDAR-CONTRACT key tokens (bound by the runner), the key survives
        only as source_record_id, and no PROV- value is written."""
        _, _, out = self.run_build("ids")
        import csv
        for table in ("gaming_compacts.csv", "gaming_compact_versions.csv"):
            with (out / table).open(encoding="utf-8", newline="") as fh:
                rows = list(csv.DictReader(fh))
            self.assertTrue(rows)
            for r in rows:
                key_col = "compact_id" if table == "gaming_compacts.csv" else "version_id"
                klass, key = gg.decode_token(r[key_col])
                self.assertEqual(klass, "GCMP" if key_col == "compact_id" else "GCMV")
                self.assertEqual(r["source_record_id"], __import__("json").loads(key)[1])
                self.assertEqual(gg.KEY_CLASSES[klass][0], "CEDAR-CONTRACT")
        for path in out.glob("*.csv"):
            self.assertNotIn("PROV-", path.read_text(encoding="utf-8"), path.name)

    def test_parse_case_citations_known_shapes(self):
        got = lane.parse_case_citations(
            "Remanded by Butte Cty. v. Hogen , 392 U.S. App. D.C. 25 (2010). "
            "On remand by Sokaogon Chippewa Community, et al., v. Babbitt, et al., Case No. 95-C-659-C (W.D. Wis.).")
        self.assertEqual(got[0], ("Butte Cty. v. Hogen", "392 U.S. App. D.C. 25", "D.C. Cir.", "2010"))
        self.assertEqual(got[1][1], "Case No. 95-C-659-C")


if __name__ == "__main__":
    unittest.main(verbosity=2)
