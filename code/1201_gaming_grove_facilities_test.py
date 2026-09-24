#!/usr/bin/env python3
"""Tests for 1201_gaming_grove_facilities.py on small synthetic fixtures.

    py -3 code/1201_gaming_grove_facilities_test.py

Each test names the failure mode it proves cannot happen:
  * a vendor ID (CCP-/VP-/TPL-) in a public ID column;
  * a vendor-only (Casino City) or research-only (votingpatterns) value in a
    public field or a public row - including a Census point geocoded from it;
  * a legacy facility record dropped without exactly one disposition;
  * ownership stated without evidence (vendor affiliation, non-agreeing text);
  * a relationship / period interval that ends before it starts;
  * a new facility ID minted for a place-less "no casino" record;
  * a vendor placeholder day shown as a day;
  * nondeterminism, and ID rendering while the ID contract is on hold.
No live data is read: the fixture header for every input is the union of the
columns the producer reads, taken from the producer's own source.
"""
from __future__ import annotations

import csv
import importlib.util
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gaming_grove as gg  # noqa: E402

PRODUCER = HERE / "1201_gaming_grove_facilities.py"
_spec = importlib.util.spec_from_file_location("gaming_grove_facilities_1201", PRODUCER)
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

# every column the producer reads from an input row
COLUMNS = sorted(set(re.findall(r'\[["\']([a-z][a-z0-9_]+)["\']\]', PRODUCER.read_text(encoding="utf-8")))
                 | {"cedar_uid", "canonical_name", "place_class", "source_key", "binding_role",
                    "sector", "enterprise_name", "owner_hub_cedar_uid"}
                 # columns the producer reads through f-string keys
                 | {f"{w}_date{s}" for w in ("open", "close") for s in (
                     "", "_basis", "_source_url", "_source_value_verbatim", "_source_value_placeholder",
                     "_not_before", "_not_after", "_precision")}
                 | {f"{m}{s}" for m in ("gaming_machines", "table_games", "poker_tables", "bingo_seats",
                                        "gaming_square_feet", "convention_square_feet", "hotel_rooms",
                                        "parking_spaces", "restaurants")
                    for s in ("", "_value_basis", "_observed_date")})

# valid canonical CE uids (check characters verified by 503_identity)
MIAMI, MODOC, ABS_SHAWNEE, OTOE = "CE-0016Y-PQ", "CE-00175-5P", "CE-00124-6D", "CE-00181-J2"
P1, P2, P3, P4, P5 = ("CEDAR-PLACE-000001-6S", "CEDAR-PLACE-000002-CJ", "CEDAR-PLACE-000003-AA",
                      "CEDAR-PLACE-000004-BB", "CEDAR-PLACE-000005-CC")
VENDOR_NAME = "Vendorland Casino Deluxe"
VENDOR_ADDR = "999 Vendor Only Road"
RESEARCH_ADDR = "123 Research Compiled Way"


def fac(fid, place, name, uid, **kw):
    r = {"facility_id": fid, "cedar_place_id": place, "facility_name": name, "cedar_uid": uid,
         "tribe": "Fixture Tribe", "entity_tier": "A", "entity_match_method": "exact",
         "source_datasets": "casino_city_press|tribal_property_list" if fid.startswith("CCP") else "votingpatterns_canonical",
         "fetched_date": "2026-08-05", "address": VENDOR_ADDR, "casino_city_id": fid[4:] if fid.startswith("CCP") else ""}
    r.update(kw)
    return r


def fixture_tables():
    F = [
        # 1: vendor-only property (no independent evidence at all)
        fac("CCP-100", P1, VENDOR_NAME, ABS_SHAWNEE, open_date="1995", open_date_precision="year",
            open_date_basis="Casino City Tribal Property List, 'Open Date'; DAY PRECISION WITHDRAWN",
            open_date_source_value_verbatim="1995-12-31",
            open_date_source_value_placeholder="vendor_year_end_placeholder_1231",
            open_date_not_before="1995-01-01", open_date_not_after="1995-12-31",
            gaming_machines="500", gaming_machines_value_basis="reported", gaming_machines_observed_date="2026-08-05"),
        # 2: NIGC-listed property with two vintages (alias group)
        fac("CCP-200", P2, "Thunder Vendor Name", ABS_SHAWNEE),
        fac("VP-0002", P2, "Thunder Research Name", ABS_SHAWNEE, address=RESEARCH_ADDR),
        # 3: joint operation (vendor names both) + a held-open research record for the same property
        fac("CCP-305300", P3, "Stables Vendor", MIAMI, operating_entity_cedar_uids=f"{MIAMI}|{MODOC}"),
        fac("VP-0153", P4, "Stables Research", MODOC),
        # 4: place-less 'no casino' assertion
        fac("VP-0009", "", "No casino", ABS_SHAWNEE,
            cedar_place_id_absent_reason="NOT_A_PLACE: this facility_id names a row asserting the entity operates no gaming property",
            open_date_absent_reason="not a gaming facility - this row comes from votingpatterns"),
        # 5: research-only property
        fac("VP-0005", P5, "Research Only Casino", OTOE, address=RESEARCH_ADDR),
    ]
    tables = {
        "data/clean/gaming_facilities.csv": F,
        "data/clean/gaming_nigc_roster_link.csv": [
            {"facility_id": "CCP-200", "cedar_place_id": P2, "nigc_location_name": "Thunder Casino",
             "nigc_address": "2051 S Gordon Cooper, Shawnee OK 74801", "nigc_city": "Shawnee", "nigc_state": "OK",
             "match_basis": "exact_name_state", "link_tier": "A", "cedar_row_has_close_evidence": "0",
             "nigc_listed_as_of": "2026-08-26", "igra_coverage_status": "VERIFIED_NIGC_OPERATION",
             "source_url": "https://www.nigc.gov/map/", "cedar_uid": ABS_SHAWNEE},
            {"facility_id": "CCP-305300", "cedar_place_id": P3, "nigc_location_name": "The Stables Casino",
             "nigc_address": "530 H Street SE, Miami OK 74354", "nigc_city": "Miami", "nigc_state": "OK",
             "match_basis": "exact_name_state", "link_tier": "A", "cedar_row_has_close_evidence": "0",
             "nigc_listed_as_of": "2026-08-26", "igra_coverage_status": "VERIFIED_NIGC_OPERATION",
             "source_url": "https://www.nigc.gov/map/", "cedar_uid": MIAMI}],
        "data/clean/gaming_property_locations.csv": [
            {"property_id": "CCP-100", "source_system": "casino_city_press [LICENSED VENDOR - DO NOT PUBLISH]",
             "address_source_system": "casino_city_press", "address": VENDOR_ADDR, "state": "OK",
             "latitude": "35.0", "longitude": "-97.0", "retrieved_at": "2026-08-05"},
            {"property_id": "VP-0005", "source_system": "us_census_geocoder",
             "address_source_system": "votingpatterns_canonical_addresses", "address": RESEARCH_ADDR,
             "state": "OK", "latitude": "36.1", "longitude": "-96.1", "match_quality": "Exact",
             "county": "Research County", "county_fips": "40999", "retrieved_at": "2026-08-12"},
            {"property_id": "VP-0005", "source_system": "votingpatterns_canonical_addresses",
             "address_source_system": "votingpatterns_canonical_addresses", "address": RESEARCH_ADDR,
             "state": "OK", "retrieved_at": "2026-04-27"},
            {"property_id": "CCP-200", "source_system": "us_census_geocoder",
             "address_source_system": "nigc_gaming_location_map", "address": "2051 S Gordon Cooper",
             "state": "OK", "latitude": "35.3", "longitude": "-96.9", "match_quality": "Exact",
             "county": "Pottawatomie County", "county_fips": "40125", "retrieved_at": "2026-08-12"}],
        "data/clean/ca_gaming_facilities_official.csv": [],
        "data/clean/gaming_capacity_official.csv": [
            {"observation_id": "GCO-1", "facility_id": "CCP-200", "facility_match_method": "exact_name_in_state",
             "metric": "gaming_machines", "metric_class": "capacity_measurement",
             "measurement_status": "reported_measurement", "measurement_type": "REGULATORY_REPORTED_COUNT",
             "value": "800.0", "unit": "machines", "as_of_date": "2025-06-30", "as_of_date_precision": "day",
             "period_start": "2025-06-30", "period_end": "2025-01-01",  # inverted on purpose
             "source_authority": "Fixture Gaming Board", "source_document_type": "state_regulator_status_report",
             "source_url": "https://gaming.example.gov/r.pdf", "source_quote": "Thunder: 800 machines",
             "facility_name_as_published": "Thunder", "fetched_date": "2026-08-07"},
            {"observation_id": "GCO-2", "facility_id": "CCP-200", "facility_match_method": "environmental_review_not_keyed_to_property",
             "metric": "gaming_machines", "metric_class": "capacity_measurement", "measurement_type": "PROJECTED",
             "value": "5000", "as_of_date": "2024-01-01", "source_url": "https://x.gov"}],
        "data/clean/gaming_property_site_observations.csv": [],
        "data/clean/gaming_property_self_published_assertions.csv": [
            # agrees with curated entity -> owner + operator
            {"assertion_id": "SPA-1", "assertion_class": "SELF_PUBLISHED_OWNERSHIP_ASSERTION",
             "assertion_subclass": "owned_and_operated_by", "asserted_value": "the Absentee Shawnee Tribe",
             "asserted_owner_names_tribal_form": "Y", "asserted_owner_is_management_brand": "N",
             "agrees_with_curated_owner": "SHARES_TOKEN:shawnee", "facility_id": "CCP-200", "cedar_uid": ABS_SHAWNEE,
             "attribution_basis": "single_property_host", "record_scope": "entity",
             "source_url": "https://thundercasino.example/about", "source_quote": "owned and operated by the Absentee Shawnee Tribe",
             "retrieved_at": "2026-08-12"},
            # does not agree -> no ownership
            {"assertion_id": "SPA-2", "assertion_class": "SELF_PUBLISHED_OWNERSHIP_ASSERTION",
             "assertion_subclass": "owned_by", "asserted_value": "the Chickasaw Nation",
             "asserted_owner_names_tribal_form": "Y", "asserted_owner_is_management_brand": "N",
             "agrees_with_curated_owner": "no_distinctive_token_either_side", "facility_id": "CCP-100",
             "cedar_uid": ABS_SHAWNEE, "attribution_basis": "single_property_host", "record_scope": "entity",
             "source_url": "https://vendorland.example/faq", "source_quote": "WinStar is owned by the Chickasaw Nation",
             "retrieved_at": "2026-08-12"},
            # text-mined date claim -> lead only
            {"assertion_id": "SPA-3", "assertion_class": "SELF_PUBLISHED_DATE_ASSERTION",
             "assertion_subclass": "in_operation_since", "asserted_value": "2008", "facility_id": "CCP-100",
             "cedar_uid": ABS_SHAWNEE, "attribution_basis": "single_property_host", "record_scope": "entity",
             "source_url": "https://vendorland.example/games", "source_quote": "Pragmatic Play since 2008",
             "retrieved_at": "2026-08-12"}],
        "data/clean/gaming_property_self_published_claims.csv": [],
        "data/clean/gaming_web_harvest_observations.csv": [],
        "data/clean/gaming_property_universe_events.csv": [
            {"event_id": "NIGCMAP-1", "event_type": "present_in_snapshot", "marker_title": "Thunder Casino",
             "from_snapshot_date": "2015-10-02", "to_snapshot_date": "2026-08-06", "facility_id": "CCP-200",
             "event_note": "LISTING event, not an opening", "source_url": "https://web.archive.org/x"}],
        "data/clean/gaming_property_federal_traces.csv": [],
        "data/clean/loyalty_program_property.csv": [],
        "data/clean/sec_gaming_management_contract_terms.csv": [
            {"term_id": "SECMT-1", "manager_name": "Fixture Gaming Inc.", "manager_cik": "0000123",
             "manager_role": "MANAGER", "facility_id": "CCP-200", "adjudication": "ACCEPT",
             "filing_date": "2008-05-15", "source_url": "https://www.sec.gov/x", "source_quote": "manage the casino"}],
        "data/clean/nigc_management_contract_approvals.csv": [],
        "data/clean/nigc_region_assignments.csv": [],
        "data/clean/nest_enterprises.csv": [],
        "data/spine/cedar_identity_register.csv": [
            {"cedar_uid": u, "canonical_name": n} for u, n in
            ((MIAMI, "Miami"), (MODOC, "Modoc"), (ABS_SHAWNEE, "Absentee-Shawnee"), (OTOE, "Otoe-Missouria"))],
        "data/spine/cedar_place_id_register.csv": [
            {"cedar_place_id": P2, "place_class": "GAMING_PROPERTY", "source_key": "CCP-200", "binding_role": "primary"},
            {"cedar_place_id": P2, "place_class": "GAMING_PROPERTY", "source_key": "VP-0002", "binding_role": "merged_duplicate"}],
        "review/place_gaming_adjudication_2026-09-02.csv": [
            {"normalised_name": "THUNDER", "facility_ids": "CCP-200;VP-0002",
             "rule": "P2_one_operator_one_property_two_vintages", "verdict": "MERGE"}],
        "review/place_gaming_hold_open_disposition_2026-09-02.csv": [
            {"group": "THE STABLES", "facility_ids": "VP-0153;CCP-305300", "disposition": "ESCALATE_OWNER",
             "confidence": "the FACTS are settled"}],
        "review/place_non_place_rows_2026-09-02.csv": [
            {"facility_id": "VP-0009", "reason": "the row is an assertion that this entity operates NO gaming property"}],
    }
    return tables


def write_fixture(root: Path, tables: dict):
    for rel, rows in tables.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
            w.writeheader()
            for r in rows:
                w.writerow({c: r.get(c, "") for c in COLUMNS})


class _Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["CEDAR_GAMING_PROVISIONAL_IDS"] = "1"
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name) / "in"
        write_fixture(cls.root, fixture_tables())
        cls.out = Path(cls.tmp.name) / "out"
        cls.receipt = M.build(gg.Inputs(cls.root), cls.out)
        cls.t = {}
        for name in M.CONTRACTS:
            with (cls.out / name).open(encoding="utf-8", newline="") as fh:
                cls.t[name] = list(csv.DictReader(fh))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def public_rows(self, name):
        c = M.CONTRACTS[name]
        rows = self.t[name]
        header = list(rows[0].keys()) if rows else list(c["field_rights"])
        return gg.public_projection(name, header, rows, c["field_rights"])[1]


class VendorIds(_Base):
    def test_no_vendor_id_in_any_public_id_column(self):
        for name, c in M.CONTRACTS.items():
            for col in c["public_id_columns"]:
                for r in self.t[name]:
                    self.assertFalse(gg.VENDOR_ID_RE.match(r.get(col, "")), (name, col, r.get(col)))

    def test_writer_refuses_vendor_id_as_facility_id(self):
        c = M.CONTRACTS["gaming_grove_facilities.csv"]
        row = {k: "" for k in c["field_rights"]}
        row.update(gaming_facility_id="CCP-100", record_status="property", publication_status="withheld",
                   current_status="unknown", facility_type="unknown")
        for k in ("public_name_rights", "address_rights", "county_rights", "coordinate_rights", "status_rights"):
            row[k] = "withheld_unverified"
        with self.assertRaises(gg.GamingContractError):
            gg.write_table(self.out / "x", "gaming_grove_facilities.csv", list(c["field_rights"]), [row], c)

    def test_no_vendor_id_anywhere_in_public_projection(self):
        for name in M.CONTRACTS:
            for r in self.public_rows(name):
                for v in r.values():
                    self.assertIsNone(re.search(r"\b(?:CCP|VP|TPL)-\d+\b", v or ""), (name, v))


class VendorValuesNeverPublic(_Base):
    def test_vendor_only_facility_has_no_public_fields(self):
        row = next(r for r in self.t["gaming_grove_facilities.csv"] if r["cedar_place_id"] == P1)
        for col in ("public_name", "street_address", "city", "state", "latitude", "longitude", "county"):
            self.assertEqual(row[col], "", col)
        self.assertEqual(row["current_status"], "unknown")
        self.assertEqual(row["publication_status"], "withheld")
        self.assertIn("name:vendor_only", row["withheld_fields"])

    def test_vendor_and_research_strings_absent_from_public_projection(self):
        for name in M.CONTRACTS:
            for r in self.public_rows(name):
                blob = " ".join(r.values())
                for s in (VENDOR_NAME, VENDOR_ADDR, RESEARCH_ADDR, "Thunder Research Name", "Stables Vendor"):
                    self.assertNotIn(s, blob, (name, s))

    def test_vendor_rows_kept_internally(self):
        n = [r for r in self.t["gaming_facility_names.csv"] if r["name"] == VENDOR_NAME]
        self.assertEqual([r["rights_class"] for r in n], ["internal_vendor"])
        cap = [r for r in self.t["gaming_facility_capacity.csv"] if r["value"] == "500"]
        self.assertEqual([r["rights_class"] for r in cap], ["internal_vendor"])

    def test_census_point_of_research_address_not_used(self):
        row = next(r for r in self.t["gaming_grove_facilities.csv"] if r["cedar_place_id"] == P5)
        self.assertEqual((row["latitude"], row["county"]), ("", ""))
        self.assertIn("address:research_compilation_unverified", row["withheld_fields"])

    def test_independent_evidence_publishes(self):
        row = next(r for r in self.t["gaming_grove_facilities.csv"] if r["cedar_place_id"] == P2)
        self.assertEqual(row["public_name"], "Thunder Casino")
        self.assertEqual((row["street_address"], row["city"], row["state"]), ("2051 S Gordon Cooper", "Shawnee", "OK"))
        self.assertEqual(row["county_fips"], "40125")          # Census geocode of the NIGC address
        self.assertEqual(row["current_status"], "operating")
        self.assertEqual(row["publication_status"], "public")


class Dispositions(_Base):
    def test_every_legacy_row_exactly_one_disposition(self):
        legacy = {r["facility_id"] for r in fixture_tables()["data/clean/gaming_facilities.csv"]}
        xw = [r for r in self.t["gaming_facility_crosswalk.csv"] if r["key_scheme"] == "legacy_facility_id"]
        self.assertEqual(sorted(r["legacy_facility_id"] for r in xw), sorted(legacy))
        for fid in legacy:
            ds = {r["disposition"] for r in self.t["gaming_facility_crosswalk.csv"] if r["legacy_facility_id"] == fid}
            self.assertEqual(len(ds), 1, fid)
            self.assertTrue(ds <= M.DISPOSITIONS)
        self.assertEqual(self.receipt["qa"]["legacy_rows_with_disposition"], len(legacy))

    def test_alias_and_held_open(self):
        d = {r["legacy_facility_id"]: r for r in self.t["gaming_facility_crosswalk.csv"] if r["key_scheme"] == "legacy_facility_id"}
        self.assertEqual(d["VP-0002"]["disposition"], "merged_into")
        self.assertEqual(d["VP-0002"]["merged_into_gaming_facility_id"], gg.facility_id_for(P2))
        self.assertEqual(d["CCP-305300"]["disposition"], "mapped")

    def test_writer_refuses_unknown_disposition(self):
        c = M.CONTRACTS["gaming_facility_crosswalk.csv"]
        row = {k: "x" for k in c["field_rights"]}
        row.update(disposition="dropped", rights_class="internal_crosswalk", publication_status="internal",
                   gaming_facility_id="", merged_into_gaming_facility_id="", candidate_gaming_facility_id="")
        with self.assertRaises(gg.GamingContractError):
            gg.write_table(self.out / "x", "gaming_facility_crosswalk.csv", list(c["field_rights"]), [row], c)


class NoMintForPlacelessRows(_Base):
    def test_placeless_row_gets_no_facility_id(self):
        r = next(r for r in self.t["gaming_facility_crosswalk.csv"] if r["legacy_facility_id"] == "VP-0009")
        self.assertEqual((r["gaming_facility_id"], r["cedar_place_id"]), ("", ""))
        self.assertEqual(r["disposition"], "not_a_gaming_facility")
        self.assertEqual(r["publication_status"], "unresolved")

    def test_facility_ids_only_wrap_existing_places(self):
        fixture_places = {P1, P2, P3, P4, P5}
        for name in M.CONTRACTS:
            for r in self.t[name]:
                g = r.get("gaming_facility_id", "")
                if g:
                    self.assertIn(g.replace("PROV-GFAC:", ""), fixture_places)
        # the held-open record's own place is kept in the crosswalk, not given a facility row
        self.assertNotIn(gg.facility_id_for(P4), {r["gaming_facility_id"] for r in self.t["gaming_grove_facilities.csv"]})
        x = next(r for r in self.t["gaming_facility_crosswalk.csv"] if r["legacy_facility_id"] == "VP-0153")
        self.assertEqual((x["disposition"], x["cedar_place_id"], x["candidate_gaming_facility_id"]),
                         ("unresolved", P4, gg.facility_id_for(P3)))


class Relationships(_Base):
    def rels(self):
        return self.t["gaming_facility_relationships.csv"]

    def test_vendor_affiliation_is_affiliate_and_internal(self):
        for r in self.rels():
            if r["source_system"] in ("casino_city_press", "votingpatterns_research"):
                self.assertEqual(r["relationship_type"], "affiliate")
                self.assertNotIn(r["rights_class"], gg.PUBLIC_RIGHTS)

    def test_owner_only_with_agreeing_evidence(self):
        owners = [r for r in self.rels() if r["relationship_type"] == "owner"]
        self.assertEqual(len(owners), 1)
        self.assertEqual(owners[0]["gaming_facility_id"], gg.facility_id_for(P2))
        self.assertIn("owned and operated by", owners[0]["evidence_text"])
        self.assertFalse(any(r["relationship_type"] == "owner" and r["gaming_facility_id"] == gg.facility_id_for(P1)
                             for r in self.rels()))
        self.assertTrue(all(r["ownership_percent"] == "" for r in self.rels()))

    def test_joint_operation_both_parties(self):
        uids = {r["cedar_uid"] for r in self.rels() if r["gaming_facility_id"] == gg.facility_id_for(P3)}
        self.assertEqual(uids, {MIAMI, MODOC})

    def test_management_contractor_is_not_owner(self):
        m = [r for r in self.rels() if r["party_external_id"] == "0000123"]
        self.assertEqual([r["relationship_type"] for r in m], ["management_contractor"])
        self.assertEqual(m[0]["cedar_uid"], "")

    def test_writer_refuses_inverted_interval_and_legacy_uid(self):
        c = M.CONTRACTS["gaming_facility_relationships.csv"]
        base = dict(self.rels()[0])
        bad = dict(base, effective_start="2020-01-01", effective_end="2019-01-01")
        with self.assertRaises(gg.GamingContractError):
            gg.write_table(self.out / "x", "gaming_facility_relationships.csv", list(base), [bad], c)
        bad2 = dict(base, cedar_uid="TRBF-ASHAWN-00")
        with self.assertRaises(gg.GamingContractError):
            gg.write_table(self.out / "x", "gaming_facility_relationships.csv", list(base), [bad2], c)


class Dates(_Base):
    def test_placeholder_day_flagged_not_shown(self):
        o = next(r for r in self.t["gaming_facility_history.csv"]
                 if r["event_type"] == "opening" and r["gaming_facility_id"] == gg.facility_id_for(P1)
                 and r["source_system"] == "casino_city_press")
        self.assertEqual((o["event_date"], o["date_precision"], o["date_is_placeholder"]), ("1995", "year", "Y"))
        self.assertEqual(o["rights_class"], "internal_vendor")

    def test_listing_is_not_an_opening(self):
        ev = [r for r in self.t["gaming_facility_history.csv"] if r["source_system"] == "nigc_map_snapshot_diff"]
        self.assertEqual([r["event_type"] for r in ev], ["regulator_listing_added"])
        self.assertEqual((ev[0]["event_date"], ev[0]["date_not_before"], ev[0]["date_not_after"]),
                         ("", "2015-10-02", "2026-08-06"))

    def test_textmined_date_claim_is_a_lead(self):
        c = [r for r in self.t["gaming_facility_history.csv"] if r["source_system"] == "operator_website"
             and r["event_type"] == "opening"]
        self.assertTrue(c and all(r["rights_class"] == "withheld_unverified" for r in c))

    def test_inverted_source_period_recorded_not_emitted(self):
        r = next(r for r in self.t["gaming_facility_capacity.csv"] if r["value"] == "800")
        self.assertEqual((r["period_start"], r["period_end"]), ("", ""))
        self.assertIn("SOURCE PERIOD INVERTED", r["qualifier"])
        self.assertFalse(any(r["value"] == "5000" for r in self.t["gaming_facility_capacity.csv"]))  # projection


class Determinism(unittest.TestCase):
    def test_two_builds_identical_bytes_and_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "in"
            write_fixture(root, fixture_tables())
            os.environ["CEDAR_GAMING_PROVISIONAL_IDS"] = "1"
            r1 = M.build(gg.Inputs(root), Path(tmp) / "a")
            r2 = M.build(gg.Inputs(root), Path(tmp) / "b")
            self.assertEqual([t["sha256"] for t in r1["tables"]], [t["sha256"] for t in r2["tables"]])
            del os.environ["CEDAR_GAMING_PROVISIONAL_IDS"]
            try:
                if gg.ID_CONTRACT_STATUS != "APPROVED":
                    with self.assertRaises(gg.IdContractPending):
                        M.build(gg.Inputs(root), Path(tmp) / "c")
            finally:
                os.environ["CEDAR_GAMING_PROVISIONAL_IDS"] = "1"


if __name__ == "__main__":
    unittest.main(verbosity=2)
