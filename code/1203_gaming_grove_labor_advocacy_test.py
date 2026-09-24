#!/usr/bin/env python3
"""Tests for 1203_gaming_grove_labor_advocacy (lane F), on synthetic fixtures.

    py -3 code/1203_gaming_grove_labor_advocacy_test.py

Each test names a failure mode this lane exists to prevent: plan participants
published as employees, a suppressed or absent value rendered as 0, lobbying
rows or amounts copied into Gaming, a cedar_uid assigned from a name alone,
the same OSHA 300A filing counted twice, and nondeterministic output. No live
data is read; the CE uids below are real canonical uids so the shared
check-character validator accepts them.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
os.environ["CEDAR_GAMING_PROVISIONAL_IDS"] = "1"
import gaming_grove as gg  # noqa: E402

_spec = importlib.util.spec_from_file_location("lane_f", HERE / "1203_gaming_grove_labor_advocacy.py")
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

MASH = "CE-0017C-F5"     # Mashantucket Pequot
SAGINAW = "CE-0019W-SN"  # Saginaw Chippewa
MORONGO = "CE-00178-Q1"
PLACE_FOX = "CEDAR-PLACE-000674-N2"
PLACE_SOAR = "CEDAR-PLACE-000192-Y0"


def write_csv(path: Path, rows: list[dict], header: list[str] | None = None):
    path.parent.mkdir(parents=True, exist_ok=True)
    header = header or list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})


EMP_HEADER = ["observation_id", "facility_id", "cedar_place_id", "tribe_id", "year", "employment",
              "measurement_type", "source_url", "source_quote", "fetched_date", "confidence",
              "source_record", "match_rule", "name_in_source", "state", "flags", "cedar_uid",
              "ein", "sponsor_name", "plan_name", "naics_specificity", "sponsor_state", "ack_id",
              "state_mismatch_flag", "attribution_repaired_by", "establishment_name",
              "company_name", "establishment_id", "commercial_name_present"]


def make_fixture(root: Path) -> tuple[Path, Path]:
    clean = root / "data" / "clean"
    write_csv(clean / "gaming_facilities.csv", [
        {"facility_id": "CCP-10600", "cedar_place_id": PLACE_FOX, "cedar_uid": MASH,
         "facility_name": "Foxwoods Resort Casino", "state": "CT", "city": "Mashantucket",
         "tribe": "Mashantucket Pequot", "tribe_canonical_name": "Mashantucket Pequot Indian Tribe"},
        {"facility_id": "CCP-25600", "cedar_place_id": PLACE_SOAR, "cedar_uid": SAGINAW,
         "facility_name": "Soaring Eagle Casino & Resort", "state": "MI", "city": "Mount Pleasant",
         "tribe": "Saginaw Chippewa", "tribe_canonical_name": "Saginaw Chippewa Indian Tribe"},
    ], ["facility_id", "cedar_place_id", "cedar_uid", "facility_name", "state", "city", "tribe",
        "tribe_canonical_name", "duplicate_of_facility_id"])
    write_csv(clean / "cedar_entity_identity_crosswalk.csv", [
        {"external_scheme": "CICD_NEID", "external_identifier": "TRBF-SGINAW-00",
         "mapping_status": "APPLIED", "cedar_uid": SAGINAW},
        {"external_scheme": "CICD_NEID", "external_identifier": "TRBF-LSVGAS-00",
         "mapping_status": "APPLIED", "cedar_uid": MORONGO},  # deliberately a real uid
    ])
    emp = [
        # the same 300A filing twice: facility grain and tribe grain
        {"observation_id": "EMP-OSHA-000001", "facility_id": "CCP-25600", "cedar_place_id": PLACE_SOAR,
         "year": "2024", "employment": "3000", "measurement_type": "OSHA_ESTABLISHMENT_REPORTED",
         "confidence": "high", "match_rule": "exact_normalised_establishment_name_and_state",
         "name_in_source": "Soaring Eagle Casino & Resort", "state": "MI", "cedar_uid": SAGINAW},
        {"observation_id": "EMP-OSHATRIBE-00001", "year": "2024", "employment": "3000",
         "measurement_type": "OSHA_TRIBE_LEVEL_REPORTED", "confidence": "medium",
         "match_rule": "brand_exact", "state": "MI", "cedar_uid": SAGINAW, "establishment_id": "777",
         "establishment_name": "Soaring Eagle Casino & Resort", "company_name": "Saginaw Chippewa Indian Tribe"},
        {"observation_id": "EMP-OSHATRIBE-00002", "year": "2024", "employment": "19",
         "measurement_type": "OSHA_TRIBE_LEVEL_REPORTED", "confidence": "medium",
         "match_rule": "containment_plus_guards", "state": "MI", "cedar_uid": SAGINAW, "establishment_id": "888",
         "establishment_name": "Tiny Annex", "company_name": "Saginaw Chippewa Indian Tribe"},
        {"observation_id": "EMP-F5500-000001", "year": "2024", "employment": "4288",
         "measurement_type": "FORM5500_ACTIVE_PARTICIPANTS", "cedar_uid": MASH, "ein": "060000001",
         "ack_id": "20250101000000P000000000001001", "sponsor_name": "MASHANTUCKET PEQUOT GAMING ENTERPRISE",
         "plan_name": "401K PLAN", "sponsor_state": "CT", "state_mismatch_flag": "0",
         "source_url": "https://askebsa.dol.gov/x.zip", "match_rule": "spine"},
        {"observation_id": "EMP-F5500-000002", "year": "2024", "employment": "12",
         "measurement_type": "FORM5500_ACTIVE_PARTICIPANTS", "cedar_uid": MASH, "ein": "060000002",
         "ack_id": "20250101000000P000000000002001", "sponsor_name": "SOME SPONSOR",
         "sponsor_state": "NV", "state_mismatch_flag": "1", "source_url": "https://askebsa.dol.gov/x.zip",
         "match_rule": "spine"},
        {"observation_id": "EMP-LODES-000001", "facility_id": "CCP-10600", "cedar_place_id": PLACE_FOX,
         "year": "2022", "employment": "5000", "measurement_type": "LODES_BLOCK_WORKPLACE_JOBS",
         "source_quote": 'w_geocode="090110000000001"; C000="5000"; CNS17="4000"; CNS18="500"',
         "source_record": "CT_wac.csv.gz", "fetched_date": "2026-08-07", "state": "CT", "cedar_uid": MASH,
         "match_rule": "facility_lat_lon_geocoded_to_2020_block"},
        {"observation_id": "EMP-DOC-000001", "year": "2026", "employment": "1075",
         "measurement_type": "PROJECTED"},
    ]
    write_csv(clean / "gaming_employment_observations.csv", emp, EMP_HEADER)
    raw = root / "data" / "raw" / "external" / "osha_ita"
    write_csv(raw / "_gambling_naics_rows.csv", [
        {"id": "1", "company_name": "Saginaw Chippewa Indian Tribe", "establishment_name": "Soaring Eagle Casino & Resort",
         "state": "MI", "annual_average_employees": "3000", "total_hours_worked": "5000000",
         "establishment_id": "777", "year_filing_for": "2024", "created_timestamp": "3/1/2025 10:00:00",
         "_file": "ita_300a_2024.zip"},
        {"id": "2", "company_name": "Saginaw Chippewa Indian Tribe", "establishment_name": "Tiny Annex",
         "state": "MI", "annual_average_employees": "19", "total_hours_worked": "117335",
         "establishment_id": "888", "year_filing_for": "2024", "_file": "ita_300a_2024.zip"},
    ])
    write_csv(raw / "_SOURCE_MANIFEST.csv", [{"year": "2024", "url": "https://osha.example/2024.zip",
                                               "fetched_date": "2026-08-07"}])
    write_csv(clean / "native_entity_lobbying_disclosures.csv", [
        {"filing_uuid": "aaaaaaaa-0000-0000-0000-000000000001", "cedar_uid": MASH, "client_name": "MASHANTUCKET PEQUOT TRIBE",
         "lobbying_issues_codes": "GAM|IND", "specific_issues_text": "Tribal-state gaming compact with the State of Connecticut",
         "dt_posted": "2024-04-20T00:00:00-04:00", "match_confidence": "high", "is_superseded": "0",
         "income_usd": "90000", "registrant_name": "BIG LOBBY LLC", "filing_url": "https://lda.gov/f/1",
         "attribution_method": "exact_normalized", "filing_year": "2024", "filing_period": "first_quarter"},
        {"filing_uuid": "aaaaaaaa-0000-0000-0000-000000000002", "cedar_uid": MASH, "client_name": "MASHANTUCKET PEQUOT TRIBE",
         "lobbying_issues_codes": "GAM", "specific_issues_text": "gaming", "dt_posted": "2024-01-20",
         "match_confidence": "high", "is_superseded": "1", "income_usd": "90000"},
        {"filing_uuid": "aaaaaaaa-0000-0000-0000-000000000003", "cedar_uid": "", "client_name": "SAGINAW CHIPPEWA INDIAN TRIBE",
         "lobbying_issues_codes": "", "specific_issues_text": "Sports betting legislation", "dt_posted": "2025-02-01",
         "match_confidence": "medium", "is_superseded": "0", "filing_url": "https://lda.gov/f/3"},
        {"filing_uuid": "aaaaaaaa-0000-0000-0000-000000000004", "cedar_uid": MASH, "client_name": "X",
         "lobbying_issues_codes": "GAM", "specific_issues_text": "", "dt_posted": "2025-02-01",
         "match_confidence": "withdrawn_false_attribution", "attribution_withdrawn": "1", "is_superseded": "0"},
        {"filing_uuid": "aaaaaaaa-0000-0000-0000-000000000005", "cedar_uid": MASH,
         "lobbying_issues_codes": "HCR", "specific_issues_text": "Indian Health Service appropriations",
         "dt_posted": "2025-02-01", "match_confidence": "high", "is_superseded": "0"},
    ], ["filing_uuid", "cedar_uid", "client_name", "lobbying_issues_codes", "specific_issues_text",
        "dt_posted", "match_confidence", "is_superseded", "attribution_withdrawn", "income_usd",
        "registrant_name", "filing_url", "attribution_method", "filing_year", "filing_period"])
    write_csv(clean / "compacts.csv", [
        {"compact_id": "CMP-CT-mashantucket-19910101", "cedar_uid": MASH, "state": "Connecticut",
         "original_effective_date": "1991-01-01"}])
    write_csv(clean / "consultation_events.csv", [
        {"consultation_event_id": "CONS-FR-2010-1", "agency": "National Indian Gaming Commission",
         "topic": "Notice of Consultation", "notice_date": "2010-11-01", "fr_document_number": "2010-1",
         "source_url": "https://www.federalregister.gov/d/2010-1"}])
    write_csv(clean / "regulations_gov_comments.csv", [
        {"regulations_gov_comment_row_id": "RGC-1", "comment_id": "NIGC-2007-0010-0044", "agency_id": "NIGC",
         "title": "Comment from a tribal gaming commission", "posted_date": "2007-09-01", "cedar_uid": SAGINAW,
         "attribution_class": "TITLE_NAMES_THE_ENTITY", "comment_url": "https://www.regulations.gov/comment/NIGC-2007-0010-0044"}])
    fw = root / "fourwheeler"
    write_csv(fw / "data" / "resolved_nlrb_gaming.csv", [
        {"employer": "GNLV, LLC d/b/a Golden Nugget Las Vegas", "Case Number": "28-RC-1", "Tally Issued Date": "16 October 2019",
         "Tally Type": "Initial", "No. of Eligible Voters": "291", "Unit ID": "A", "Unit Location": "Las Vegas, NV",
         "votes_for_unions": "200", "Votes Against": "50", "tribe_id": "TRBF-LSVGAS-00", "matched_core": "las vegas",
         "resolution": "matched"},
        {"employer": "Foxwoods Resort Casino", "Case Number": "34-RC-002230", "Tally Issued Date": "24 November 2007",
         "Tally Type": "Initial", "No. of Eligible Voters": "2619", "Unit ID": "A", "Unit Location": "Ledyard, CT",
         "votes_for_unions": "1289", "Votes Against": "1008", "Total Ballots Counted": "2297", "resolution": "no spine match"},
        {"employer": "Foxwoods Resort Casino", "Case Number": "28-RC-9", "Tally Issued Date": "01 May 2010",
         "Tally Type": "Initial", "No. of Eligible Voters": "30", "Unit ID": "A", "Unit Location": "Reno, NV",
         "resolution": "no spine match"},
        {"employer": "VIEJAS BAND OF KUMEYAAY INDIANS", "Case Number": "21-RD-134839", "Tally Issued Date": "05 August 2014",
         "Tally Type": "Initial", "No. of Eligible Voters": "475", "Unit ID": "A", "Unit Location": "ALPINE, CA",
         "votes_for_unions": "", "Votes Against": "300", "resolution": "no spine match"},
        {"employer": "Soaring Eagle Casino and Resort, An Enterprise of The Saginaw Chippewa Indian Tribe",
         "Case Number": "07-RC-129013", "Tally Issued Date": "27 October 2014", "Tally Type": "Initial",
         "No. of Eligible Voters": "162", "Unit ID": "A", "Unit Location": "Mount Pleasant, MI",
         "votes_for_unions": "40", "Votes Against": "100", "tribe_id": "TRBF-SGINAW-00",
         "matched_core": "saginaw chippewa", "resolution": "matched"},
    ], ["employer", "Case Number", "Date Filed", "Tally Issued Date", "Tally Type", "No. of Eligible Voters",
        "Total Ballots Counted", "Votes Against", "Unit ID", "Unit Location", "votes_for_unions",
        "voting_unit_text", "tribe_id", "matched_core", "resolution"])
    return root, fw


def rows_of(path: Path):
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


class LaneF(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        base = Path(cls.tmp.name)
        cls.root, cls.fw = make_fixture(base / "in")
        cls.out = base / "out"
        cls.result = M.build(gg.Inputs(cls.root), cls.out, cls.fw)
        cls.labor = rows_of(cls.out / M.LABOR_TABLE)
        cls.links = rows_of(cls.out / M.ADV_TABLE)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    # --- participants are never employees
    def test_form5500_participants_never_labelled_employees(self):
        f = [r for r in self.labor if r["source_system"] == "dol_form5500"]
        self.assertEqual(len(f), 2)
        for r in f:
            self.assertEqual(r["measure"], "active_plan_participants")
            self.assertEqual(r["unit"], "participants")
            self.assertNotIn("employ", r["measure"])
            self.assertIn("NOT employees", r["measured_concept"])
            self.assertIn("PLAN_PARTICIPANTS_ARE_NOT_EMPLOYEES", r["flags"])
        bad = dict(f[0], measure="employees", unit="employees")
        with self.assertRaises(gg.GamingContractError):
            M.assert_labor_invariants([bad])

    def test_state_mismatch_sponsor_withheld(self):
        r = next(r for r in self.labor if r["source_record_id"].startswith("ein=060000002"))
        self.assertEqual(r["rights_class"], "withheld_unverified")
        self.assertEqual(r["review_status"], "unresolved")

    # --- suppressed / absent is never zero
    def test_suppressed_and_blank_never_zero(self):
        self.assertEqual(M.value_of("(D)"), ("", "suppressed"))
        self.assertEqual(M.value_of("123", disclosure_code="N"), ("", "suppressed"))
        self.assertEqual(M.value_of(""), ("", "not_reported"))
        self.assertEqual(M.value_of("0"), ("0", "reported"))
        viejas_for = next(r for r in self.labor if "21-RD-134839" in r["source_record_id"]
                          and r["measure"] == "votes_for_labor_organization")
        self.assertEqual((viejas_for["value"], viejas_for["value_status"]), ("", "not_reported"))
        row = dict(viejas_for, value="0", value_status="suppressed", suppression_flag="1")
        with self.assertRaises(gg.GamingContractError):
            M.assert_labor_invariants([row])
        for r in self.labor:
            if r["value_status"] in ("suppressed", "not_reported", "withheld_implausible"):
                self.assertEqual(r["value"], "")

    def test_implausible_hours_fte_withheld_not_invented(self):
        # 19 employees, 117,335 hours: a construction project's hours on a casino filing
        fte = next(r for r in self.labor if r["source_record_id"] == "establishment_id=888;year=2024"
                   and r["measure"] == "fte_2080")
        self.assertEqual((fte["value"], fte["value_status"]), ("", "withheld_implausible"))
        self.assertNotIn(fte["rights_class"], gg.PUBLIC_RIGHTS)
        emp = next(r for r in self.labor if r["source_record_id"] == "establishment_id=888;year=2024"
                   and r["measure"] == "annual_average_employees")
        self.assertEqual(emp["value"], "19")

    # --- one 300A filing is one source record
    def test_osha_facility_and_tribe_copies_collapse(self):
        o = [r for r in self.labor if r["source_system"] == "osha_ita_300a"]
        recs = {r["source_record_id"] for r in o}
        self.assertEqual(recs, {"establishment_id=777;year=2024", "establishment_id=888;year=2024"})
        emp = [r for r in o if r["measure"] == "annual_average_employees" and "777" in r["source_record_id"]]
        self.assertEqual(len(emp), 1)
        self.assertEqual(emp[0]["legacy_observation_ids"], "EMP-OSHA-000001|EMP-OSHATRIBE-00001")
        self.assertEqual(emp[0]["gaming_facility_id"], gg.facility_id_for(PLACE_SOAR))
        fte = next(r for r in o if r["measure"] == "fte_2080" and "777" in r["source_record_id"])
        self.assertEqual(fte["rights_class"], "public_derived")
        self.assertEqual(fte["value"], "2403.8")

    def test_projections_left_to_lane_e_and_lodes_internal(self):
        self.assertFalse(any("EMP-DOC" in r["legacy_observation_ids"] for r in self.labor))
        self.assertEqual(self.result["withheld"].get("excluded_to_lane_E_projected"), 1)
        lodes = [r for r in self.labor if r["source_system"] == "census_lodes_wac"]
        self.assertEqual(len(lodes), 2)
        self.assertTrue(all(r["rights_class"] not in gg.PUBLIC_RIGHTS for r in lodes))
        _, pub = gg.public_projection(M.LABOR_TABLE, M.LABOR_HEADER, self.labor,
                                      M.LABOR_CONTRACT["field_rights"])
        self.assertFalse(any(r["source_system"] == "census_lodes_wac" for r in pub))
        self.assertTrue(all("legacy_facility_id" not in r for r in pub))

    # --- no name-only cedar_uid
    def test_nlrb_no_name_only_uid(self):
        n = {r["source_record_id"].split(";")[0]: r for r in self.labor
             if r["source_system"] == "nlrb_election" and r["measure"] == "eligible_voters"}
        self.assertNotIn("case=28-RC-1", n)   # Golden Nugget -> Las Vegas Paiute refused
        self.assertEqual(n["case=34-RC-002230"]["cedar_uid"], MASH)
        self.assertEqual(n["case=34-RC-002230"]["value"], "2619")
        self.assertEqual(n["case=34-RC-002230"]["outcome"], "majority_for_labor_organization")
        self.assertNotIn("case=28-RC-9", n)   # same brand, wrong state: no link, no tribal signal
        self.assertEqual(n["case=21-RD-134839"]["cedar_uid"], "")   # Viejas: named, not resolved
        self.assertEqual(n["case=21-RD-134839"]["rights_class"], "withheld_unverified")
        self.assertEqual(n["case=07-RC-129013"]["cedar_uid"], SAGINAW)
        for r in self.labor:
            if r["cedar_uid"]:
                self.assertTrue(r["match_method"])
                self.assertTrue(gg.is_ce_uid(r["cedar_uid"]))

    def test_lobbying_unresolved_client_is_topic_only(self):
        l3 = [r for r in self.links if r["source_event_id"] == "aaaaaaaa-0000-0000-0000-000000000003"]
        self.assertEqual([r["link_target_type"] for r in l3], ["topic_only"])
        self.assertIn("sports_betting", l3[0]["topics"])

    # --- lobbying rows never duplicated
    def test_links_carry_ids_not_lobbying_rows(self):
        self.assertFalse(M.ADV_FORBIDDEN_FIELDS & set(M.ADV_HEADER))
        with open(self.out / M.ADV_TABLE, encoding="utf-8") as fh:
            body = fh.read()
        self.assertNotIn("90000", body)
        self.assertNotIn("BIG LOBBY", body)
        ids = {r["source_event_id"] for r in self.links if r["source_table"] == "native_entity_lobbying_disclosures.csv"}
        self.assertEqual(ids, {"aaaaaaaa-0000-0000-0000-000000000001", "aaaaaaaa-0000-0000-0000-000000000003"})
        l1 = [r for r in self.links if r["source_event_id"] == "aaaaaaaa-0000-0000-0000-000000000001"]
        self.assertEqual(sorted(r["link_target_type"] for r in l1), ["cedar_uid", "compact"])
        self.assertTrue(all(r["source_native_id"] == r["source_event_id"] for r in l1))
        with self.assertRaises(gg.GamingContractError):
            M.assert_link_invariants(M.ADV_HEADER + ["income_usd"], [])
        self.assertTrue(any(r["crossref_source_key"] == "federal_register_document=2010-1" for r in self.links))
        self.assertTrue(any(r["source_native_id"] == "NIGC-2007-0010-0044" and r["target_id"] == SAGINAW
                            for r in self.links))

    # --- determinism and the ID hold
    def test_rebuild_is_byte_identical(self):
        out2 = Path(self.tmp.name) / "out2"
        M.build(gg.Inputs(self.root), out2, self.fw)
        for t in (M.LABOR_TABLE, M.ADV_TABLE):
            a = hashlib.sha256((self.out / t).read_bytes()).hexdigest()
            b = hashlib.sha256((out2 / t).read_bytes()).hexdigest()
            self.assertEqual(a, b, t)

    def test_ids_refused_without_provisional_flag(self):
        os.environ.pop("CEDAR_GAMING_PROVISIONAL_IDS")
        try:
            with self.assertRaises(gg.IdContractPending):
                M.labor_row(source_system="dol_form5500", source_record_id="x", measure="m")
        finally:
            os.environ["CEDAR_GAMING_PROVISIONAL_IDS"] = "1"

    def test_duplicate_pk_refused(self):
        r = self.labor[0]
        with self.assertRaises(gg.GamingContractError):
            gg.write_table(Path(self.tmp.name) / "dup", M.LABOR_TABLE, M.LABOR_HEADER, [r, dict(r)],
                           M.LABOR_CONTRACT)


if __name__ == "__main__":
    unittest.main(verbosity=2)
