#!/usr/bin/env python3
"""Tests for gaming_grove_online_sports (imported by producer 1200), on a tiny
synthetic package shaped like online_sports_2026-09-24.

Each test names a failure mode the review forbids: monthly and annual grains
summed together, a shared three-tribe total copied or divided per tribe,
handle labelled revenue, money passed through float, blank turned into zero,
secondary rows promoted to public, the NJ license aggregate added to the
brand series, the Pennsylvania discrepancy spread to other rows, existing
digital sportsbook rows silently double counted, and an ID rendered without
the provisional hold. No live data needed.

    py -3 code/gaming_grove_online_sports_test.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
import tempfile
import unittest
from collections import Counter
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gaming_grove as gg  # noqa: E402
import gaming_grove_online_sports as gos  # noqa: E402

# real canonical ids (valid check characters)
HANNAH, SEMI, PENOB, HOULT, MIKM, MOHEG, QUAP = ("CE-0014W-05", "CE-001A9-CA", "CE-0018D-TE", "CE-0014Z-JG",
                                                  "CE-0016Z-WG", "CE-0016X-GY", "CE-0018Z-6G")

M_HDR = ["record_id", "series_id", "state", "month", "cedar_uid", "tribe_name", "reporting_entity", "reporting_grain",
         "source_platform_label", "platform_label_caveat", "relationship_type", "record_status", "currency",
         "handle_usd", "payouts_usd", "voided_wagers_usd", "resettlements_usd", "other_adjustments_usd",
         "gross_revenue_usd", "federal_excise_tax_usd", "unadjusted_revenue_usd", "promotional_credits_usd",
         "promotional_deduction_usd", "adjusted_revenue_usd", "taxable_revenue_usd", "state_payment_usd",
         "local_payment_usd", "gross_revenue_method", "revenue_definition_id", "source_file", "source_url",
         "source_sha256", "source_locator", "retrieved_at", "qa_status", "notes"]
S_HDR = ["record_id", "series_id", "state", "month", "cedar_uid", "tribe_name", "reporting_entity", "reporting_grain",
         "source_platform_label", "platform_label_caveat", "relationship_type", "record_status", "currency",
         "source_file", "source_url", "source_sha256", "source_locator", "retrieved_at", "notes", "handle_usd",
         "source_revenue_usd", "state_payment_usd", "source_type", "revenue_definition_id", "qa_status",
         "source_precision"]
A_HDR = ["record_id", "series_id", "state", "cedar_uid", "tribe_name", "reporting_entity", "reporting_grain",
         "source_platform_label", "platform_label_caveat", "relationship_type", "record_status", "currency",
         "source_file", "source_url", "source_sha256", "source_locator", "retrieved_at", "notes", "year",
         "period_start", "period_end", "handle_usd", "source_revenue_usd", "source_type", "revenue_definition_id",
         "source_precision", "qa_status", "payouts_usd", "adjusted_revenue_usd", "state_payment_usd",
         "per_wager_tax_usd"]
R_HDR = ["series_id", "state", "cedar_uid", "canonical_name", "entity_class", "relationship_type", "valid_from_month",
         "valid_through_month", "ownership_share_if_explicit", "allocation_weight", "financial_allocation_permitted",
         "evidence_url", "relationship_status", "notes"]
SC_HDR = ["series_id", "state", "reporting_entity", "reporting_grain", "table", "evidence_tier", "first_period",
          "last_period", "frequency", "records", "reported_zero_months", "internal_missing_months",
          "handle_available", "revenue_definition_id", "notes", "source_url"]


def _w(path: Path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({h: r.get(h, "") for h in header})


def make_package(tmp: Path):
    """Returns (input_root, package_root, expected counts)."""
    pkg = tmp / "pkg" / "tribal_sports"
    raw = {"raw/mi.xlsx": b"mi bytes", "raw/me.pdf": b"me bytes", "raw/nj.pdf": b"nj bytes",
           "raw/pa.xlsx": b"pa bytes", "raw/playnj.html": b"playnj", "raw/ar.html": b"ar dash"}
    sha = {}
    for rel, data in raw.items():
        (pkg / rel).parent.mkdir(parents=True, exist_ok=True)
        (pkg / rel).write_bytes(data)
        sha[rel] = hashlib.sha256(data).hexdigest()

    def m(rid, series, state, month, f, url, **kw):
        r = {"record_id": rid, "series_id": series, "state": state, "month": month, "record_status": "reported",
             "currency": "USD", "source_file": f, "source_url": url, "source_sha256": sha[f],
             "source_locator": "sheet!A1", "retrieved_at": "2026-09-24T20:00:00Z", "qa_status": "passed_extraction_checks",
             "revenue_definition_id": state, "reporting_entity": series, "gross_revenue_method": "reported"}
        r.update(kw)
        return r
    monthly = [
        m("MI_hannahville__2024-01", "MI_hannahville", "MI", "2024-01", "raw/mi.xlsx", "https://www.michigan.gov/x",
          cedar_uid=HANNAH, reporting_grain="tribal_license", handle_usd="3377189.27", gross_revenue_usd="0.00",
          adjusted_revenue_usd="-12.34", state_payment_usd=""),
        m("MI_hannahville__2024-02", "MI_hannahville", "MI", "2024-02", "raw/mi.xlsx", "https://www.michigan.gov/x",
          cedar_uid=HANNAH, reporting_grain="tribal_license", handle_usd="100.10", gross_revenue_usd="10.05",
          adjusted_revenue_usd="9.00", state_payment_usd="0.76"),
        m("ME_caesars_group__2024-01", "ME_caesars_group", "ME", "2024-01", "raw/me.pdf", "https://www.maine.gov/x",
          reporting_grain="three_tribe_group", handle_usd="900.00", gross_revenue_usd="300.00"),
        m("ME_caesars_group__2024-02", "ME_caesars_group", "ME", "2024-02", "raw/me.pdf", "https://www.maine.gov/x",
          reporting_grain="three_tribe_group", handle_usd="600.00", gross_revenue_usd="150.00"),
        m("NJ_hardrock__2024-01", "NJ_hardrock", "NJ", "2024-01", "raw/nj.pdf", "https://www.nj.gov/x",
          cedar_uid=SEMI, reporting_grain="online_operator", gross_revenue_usd="994450.00",
          source_locator="page 6, Hard Rock Bet, prior-year comparative"),
        m("PA_mohegan__2019-12", "PA_mohegan", "PA", "2019-12", "raw/pa.xlsx", "https://gamingcontrolboard.pa.gov/x",
          cedar_uid=MOHEG, reporting_grain="tribally_owned_casino_online_license", handle_usd="1.00",
          gross_revenue_usd="88599.81", promotional_deduction_usd="131475.21", taxable_revenue_usd="-31744.02",
          qa_status="published_components_do_not_reconcile"),
    ]
    supp = [dict(m(f"NJ_license_seminole__{ym}", "NJ_license_seminole", "NJ", ym, "raw/playnj.html",
                   "https://www.playnj.com/x", cedar_uid=SEMI, reporting_grain="multi_brand_license_aggregate",
                   source_revenue_usd=v, source_type="secondary_compilation",
                   revenue_definition_id="NJ_LICENSE_SECONDARY", qa_status="regulator_original_not_acquired",
                   source_precision="whole USD"))
            for ym, v in (("2023-12", "-3381.0"), ("2024-01", "2970331.0"))]
    annual = [{"record_id": "AR_saracen__2022", "series_id": "AR_saracen", "state": "AR", "cedar_uid": QUAP,
               "reporting_entity": "Saracen", "reporting_grain": "tribally_owned_online_operator",
               "record_status": "reported", "currency": "USD", "source_file": "raw/ar.html",
               "source_url": "https://example.cloudfront.net/x", "source_sha256": sha["raw/ar.html"],
               "source_locator": "js", "retrieved_at": "2026-09-24T20:00:00Z", "year": "2022",
               "period_start": "2022-01-01", "period_end": "2022-12-31", "handle_usd": "68160000.00",
               "source_revenue_usd": "6170000.0", "source_type": "secondary_compilation",
               "revenue_definition_id": "AR_SECONDARY", "source_precision": "USD millions rounded to 0.01 million",
               "qa_status": "rounded_secondary_values"}]
    rel = [
        {"series_id": "MI_hannahville", "state": "MI", "cedar_uid": HANNAH, "canonical_name": "Hannahville",
         "relationship_type": "tribal_license_or_owned_licensee", "valid_from_month": "2024-01",
         "valid_through_month": "2024-02", "financial_allocation_permitted": "False",
         "evidence_url": "https://www.michigan.gov/x", "relationship_status": "verified_named_relationship"},
        {"series_id": "MI_hannahville", "state": "MI", "cedar_uid": SEMI, "canonical_name": "Seminole",
         "relationship_type": "affiliated_platform_provider", "valid_from_month": "2024-02",
         "valid_through_month": "2024-02", "financial_allocation_permitted": "False",
         "evidence_url": "https://www.michigan.gov/y", "relationship_status": "verified_named_relationship"},
    ] + [{"series_id": "ME_caesars_group", "state": "ME", "cedar_uid": u, "canonical_name": n,
          "relationship_type": "member_of_published_three_tribe_group", "valid_from_month": "2024-01",
          "valid_through_month": "2024-02", "financial_allocation_permitted": "False",
          "evidence_url": "https://newsroom.caesars.com/x", "relationship_status": "verified_named_relationship"}
         for u, n in ((PENOB, "Penobscot Nation"), (HOULT, "Houlton"), (MIKM, "Mi'kmaq Nation"))] + [
        {"series_id": s, "state": st, "cedar_uid": u, "canonical_name": "x", "relationship_type": t,
         "valid_from_month": f, "valid_through_month": "2024-01", "financial_allocation_permitted": "False",
         "evidence_url": e, "relationship_status": "verified_named_relationship"}
        for s, st, u, t, f, e in (
            ("NJ_hardrock", "NJ", SEMI, "tribally_affiliated_operator", "2024-01", "https://www.hardrockdigital.com/x"),
            ("NJ_license_seminole", "NJ", SEMI, "tribally_affiliated_casino_license", "2023-12", "https://www.hardrockdigital.com/x"),
            ("PA_mohegan", "PA", MOHEG, "tribal_license_or_owned_licensee", "2019-11", "https://www.sec.gov/x"),
            ("AR_saracen", "AR", QUAP, "tribal_license_or_owned_licensee", "2022-05", "https://www.quapawtribe.com/x"))]
    sc = [
        {"series_id": "MI_hannahville", "state": "MI", "reporting_entity": "Hannahville Indian Community",
         "reporting_grain": "tribal_license", "evidence_tier": "primary_regulator", "first_period": "2024-01",
         "last_period": "2024-02", "handle_available": "True", "revenue_definition_id": "MI", "source_url": "https://www.michigan.gov/x"},
        {"series_id": "ME_caesars_group", "state": "ME", "reporting_entity": "Penobscot / Maliseet / Micmac",
         "reporting_grain": "three_tribe_group", "evidence_tier": "primary_regulator", "first_period": "2024-01",
         "last_period": "2024-02", "handle_available": "True", "revenue_definition_id": "ME", "source_url": "https://www.maine.gov/x"},
        {"series_id": "NJ_hardrock", "state": "NJ", "reporting_entity": "Hard Rock Bet", "reporting_grain": "online_operator",
         "evidence_tier": "primary_regulator", "first_period": "2024-01", "last_period": "2024-01",
         "handle_available": "False", "revenue_definition_id": "NJ", "source_url": "https://www.nj.gov/x"},
        {"series_id": "NJ_license_seminole", "state": "NJ", "reporting_entity": "Hard Rock Atlantic City",
         "reporting_grain": "multi_brand_license_aggregate", "evidence_tier": "secondary_compilation",
         "first_period": "2023-12", "last_period": "2024-01", "handle_available": "False",
         "revenue_definition_id": "NJ_LICENSE_SECONDARY", "source_url": "https://www.playnj.com/x"},
        {"series_id": "PA_mohegan", "state": "PA", "reporting_entity": "MOHEGAN",
         "reporting_grain": "tribally_owned_casino_online_license", "evidence_tier": "primary_regulator",
         "first_period": "2019-12", "last_period": "2019-12", "handle_available": "True",
         "revenue_definition_id": "PA", "source_url": "https://gamingcontrolboard.pa.gov/x"},
        {"series_id": "AR_saracen", "state": "AR", "reporting_entity": "Saracen",
         "reporting_grain": "tribally_owned_online_operator", "evidence_tier": "secondary_compilation",
         "first_period": "2022", "last_period": "2022", "handle_available": "True",
         "revenue_definition_id": "AR_SECONDARY", "source_url": "https://example.cloudfront.net/x"},
    ]
    d = pkg / "data"
    _w(d / "monthly_online_sports.csv", M_HDR, monthly)
    _w(d / "supplementary_monthly.csv", S_HDR, supp)
    _w(d / "annual_only.csv", A_HDR, annual)
    _w(d / "tribal_relationships.csv", R_HDR, rel)
    _w(d / "series_coverage.csv", SC_HDR, sc)
    _w(d / "coverage_gaps.csv", ["state", "cedar_uid", "canonical_name", "subject", "status", "earliest_lead",
                                 "evidence_url", "next_action", "notes"],
       [{"state": "IL", "cedar_uid": SEMI, "subject": "monthly", "status": "monthly_app_blocked_annual_collected",
         "earliest_lead": "2024-08", "notes": "blocked"}])
    _w(d / "revenue_definitions.csv", ["revenue_definition_id", "gross_source_label", "adjusted_or_taxable_source_label",
                                       "interpretation"],
       [{"revenue_definition_id": k, "gross_source_label": "g", "interpretation": "i"}
        for k in ("MI", "ME", "NJ", "PA", "NJ_LICENSE_SECONDARY", "AR_SECONDARY")])
    _w(d / "source_revisions.csv", ["state", "year", "cell", "older_file", "newer_file", "older_value", "newer_value"], [])
    _w(d / "validation_checks.csv", ["check", "source_file", "locator", "actual", "expected", "difference", "tolerance", "status"],
       [{"check": "PA_taxable_identity", "locator": "PA_mohegan__2019-12", "difference": "-11131.38", "status": "review"},
        {"check": "MI_x", "locator": "MI_hannahville__2024-01", "status": "pass"}])
    _w(d / "metric_evidence.csv", ["record_id", "normalized_field", "source_metric_label", "source_value", "source_file",
                                   "source_locator", "source_url"],
       [{"record_id": "MI_hannahville__2024-01", "normalized_field": "handle_usd", "source_metric_label": "Total Handle",
         "source_value": "3377189.2699999996"}])
    _w(d / "source_manifest.csv", ["url", "file", "status", "bytes", "sha256", "retrieved_at", "used_in_financial_tables"],
       [{"file": f, "sha256": h} for f, h in sha.items()])
    expected = {"primary_monthly_rows": 6, "secondary_monthly_rows": 2, "annual_only_rows": 1,
                "tribes_linked_to_any_financial_data": 7, "tribes_linked_to_primary_monthly": 6, "financial_states": 5}
    (d / "release_stats.json").write_text(json.dumps({k: v for k, v in expected.items() if k != "financial_states"}),
                                          encoding="utf-8")
    root = tmp / "cedar"
    (root / "data" / "clean").mkdir(parents=True)
    _w(root / "data" / "spine" / "cedar_identity_register.csv",
       ["cedar_uid", "canonical_name", "register_status", "federal_register_legal_name"],
       [{"cedar_uid": u, "canonical_name": "x", "register_status": "active", "federal_register_legal_name": "x"}
        for u in (HANNAH, SEMI, PENOB, HOULT, MIKM, MOHEG, QUAP)])
    return root, pkg, expected


def dg(rid, metric, value, uid=HANNAH, month="2024-02"):
    return {"revenue_id": rid, "state": "MI", "product_type": "ONLINE_SPORTSBOOK", "cedar_uid": uid,
            "period_type": "month", "period_start": f"{month}-01", "metric": metric, "value_usd": value}


class Built(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root, pkg, expected = make_package(Path(cls.tmp.name))
        cls.inputs = gg.Inputs(root)
        digital = [dg("DGREV-MI-1", "HANDLE", "100.10"), dg("DGREV-MI-2", "GROSS_GAMING_REVENUE", "10.05"),
                   dg("DGREV-MI-3", "ADJUSTED_GROSS_REVENUE", "9.01")]
        cls.tables, cls.cov, cls.withheld, cls.notes, cls.dg_map = gos.build_component(
            cls.inputs, pkg, digital, expected=expected)
        cls.fob = {r["source_record_id"]: r for r in cls.tables[gos.T_FOB]}
        cls.units = {r["source_series_id"]: r for r in cls.tables[gos.T_UNITS]}
        cls.out = Path(cls.tmp.name) / "out"
        for t, c in gos.CONTRACTS.items():
            gg.write_table(cls.out, t, c["header"], cls.tables[t], c)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    # grains
    def test_monthly_and_annual_never_mixed(self):
        rows = self.tables[gos.T_FOB]
        self.assertEqual(Counter(r["period_type"] for r in rows), {"monthly": 8, "annual": 1})
        ar = self.fob["AR_saracen__2022"]
        self.assertEqual((ar["additivity"], ar["period_start"], ar["period_end"], ar["partial_period_flag"]),
                         ("annual_only_never_mixed_with_monthly", "2022-01-01", "2022-12-31", "partial_launch_year"))
        with self.assertRaises(gos.OnlineSportsError):
            gos.sum_units(rows, "handle_usd", "monthly")          # the table as a whole mixes grains
        with self.assertRaises(gos.OnlineSportsError):
            gos.check_financials([dict(ar, additivity="additive_across_months_within_unit_and_measure")])
        mi = {self.units["MI_hannahville"]["sportsbook_unit_id"]}
        self.assertEqual(gos.sum_units(rows, "handle_usd", "monthly", mi), (Decimal("3377289.37"), 0))

    def test_shared_total_stored_once_never_per_tribe(self):
        me = self.units["ME_caesars_group"]
        self.assertEqual((me["shared_report"], me["allocation_status"], me["linked_entity_count"]),
                         ("yes", "not_allocated", "3"))
        me_rows = [r for r in self.tables[gos.T_FOB] if r["sportsbook_unit_id"] == me["sportsbook_unit_id"]]
        self.assertEqual(len(me_rows), 2)                            # one row per month, not per tribe
        self.assertNotIn("cedar_uid", gos.FOB_CONTRACT["header"])   # entities only via relationships
        rels = self.tables[gos.T_REL]
        me_rels = [r for r in rels if r["sportsbook_unit_id"] == me["sportsbook_unit_id"]]
        self.assertEqual({r["allocation_status"] for r in me_rels}, {"not_allocated"})
        self.assertEqual({r["relationship_type"] for r in me_rels}, {"reported_for"})
        totals, excluded = gos.entity_totals(self.tables[gos.T_FOB], rels, "handle_usd", "monthly")
        self.assertNotIn(PENOB, totals)
        self.assertIn(me["sportsbook_unit_id"], excluded)
        unit_total = gos.sum_units(self.tables[gos.T_FOB], "handle_usd", "monthly",
                                   {self.units[s]["sportsbook_unit_id"] for s in ("MI_hannahville", "ME_caesars_group")})[0]
        self.assertLessEqual(sum(totals.values()), unit_total)
        self.assertEqual(totals, {HANNAH: Decimal("3377289.37")})   # Seminole platform link carries nothing
        doctored = [dict(r, allocation_status="single_entity") if r["cedar_uid"] == PENOB else r for r in rels]
        with self.assertRaises(gos.OnlineSportsError):
            gos.check_relationships(doctored, self.tables[gos.T_UNITS])
        with self.assertRaises(gos.OnlineSportsError):
            gos.entity_totals(self.tables[gos.T_FOB], doctored, "handle_usd", "monthly")

    def test_handle_never_labelled_revenue(self):
        self.assertEqual(gos.MEASURE_KIND["handle_usd"], "wagers")
        self.assertNotIn(gos.MEASURE_KIND["handle_usd"], gos.REVENUE_KINDS)
        self.assertIn("NOT revenue", gos.FOB_CONTRACT["field_descriptions"]["handle_usd"])
        with self.assertRaises(gos.OnlineSportsError):
            gos.check_measure_semantics([("handle_usd", "gross_gaming_revenue")])
        # the state payment is paid TO the state, never a tribal receipt
        self.assertIn("not a payment to a tribe", gos.FOB_CONTRACT["field_descriptions"]["state_payment_usd"])

    def test_decimals_preserved_exactly_and_blank_never_zero(self):
        mi = self.fob["MI_hannahville__2024-01"]
        self.assertEqual((mi["handle_usd"], mi["gross_revenue_usd"], mi["adjusted_revenue_usd"]),
                         ("3377189.27", "0.00", "-12.34"))                      # published zero and negative kept
        self.assertEqual(mi["state_payment_usd"], "")                          # blank stays blank
        self.assertEqual(self.fob["NJ_license_seminole__2023-12"]["source_revenue_usd"], "-3381.0")
        with open(self.out / gos.T_FOB, encoding="utf-8", newline="") as f:
            back = {r["source_record_id"]: r for r in csv.DictReader(f)}
        self.assertEqual(back["MI_hannahville__2024-01"]["handle_usd"], "3377189.27")
        self.assertEqual(back["MI_hannahville__2024-01"]["state_payment_usd"], "")
        _, missing = gos.sum_units(self.tables[gos.T_FOB], "state_payment_usd", "monthly",
                                   {self.units["MI_hannahville"]["sportsbook_unit_id"]})
        self.assertEqual(missing, 1)                                             # counted missing, not 0
        for bad in ("1e5", " 12.0", "1,000.00", "12.", "nan"):
            with self.assertRaises(gos.OnlineSportsError):
                gos.exact_decimal(bad, "t")

    def test_secondary_never_public_official(self):
        for rid in ("NJ_license_seminole__2023-12", "AR_saracen__2022"):
            r = self.fob[rid]
            self.assertEqual((r["source_class"], r["rights_class"], r["publication_status"]),
                             ("secondary_corroboration", "secondary_corroboration", "source_limited"))
        self.assertEqual(gos.FOB_CONTRACT["field_rights"]["source_revenue_usd"], "secondary_corroboration")
        with self.assertRaises(gos.OnlineSportsError):
            gos.check_financials([dict(self.fob["AR_saracen__2022"], rights_class="public_official")])
        keep, rows = gg.public_projection(gos.T_FOB, gos.FOB_CONTRACT["header"], self.tables[gos.T_FOB],
                                          gos.FOB_CONTRACT["field_rights"])
        self.assertNotIn("source_revenue_usd", keep)
        self.assertFalse({r["source_record_id"] for r in rows} & {"NJ_license_seminole__2023-12", "AR_saracen__2022"})
        self.assertEqual(gos.row_rights("regulator_official", "https://example.com/x"), "withheld_unverified")

    def test_nj_license_aggregate_overlap_flagged(self):
        lic, brand = self.fob["NJ_license_seminole__2024-01"], self.fob["NJ_hardrock__2024-01"]
        self.assertEqual(lic["nonadditive_with_observation_ids"], brand["financial_observation_id"])
        self.assertEqual(brand["nonadditive_with_observation_ids"], lic["financial_observation_id"])
        self.assertEqual(self.fob["NJ_license_seminole__2023-12"]["nonadditive_with_observation_ids"], "")
        both = {self.units[s]["sportsbook_unit_id"] for s in ("NJ_hardrock", "NJ_license_seminole")}
        with self.assertRaises(gos.OnlineSportsError):
            gos.sum_units(self.tables[gos.T_FOB], "gross_revenue_usd", "monthly", both)
        self.assertEqual(self.units["NJ_hardrock"]["nonadditive_with_unit_ids"],
                         self.units["NJ_license_seminole"]["sportsbook_unit_id"])
        self.assertEqual(brand["revision_label"], "later_publication_prior_year_comparative")

    def test_pa_discrepancy_only_on_that_row(self):
        flagged = [r for r in self.tables[gos.T_FOB] if r["discrepancy_flag"] == "yes"]
        self.assertEqual([r["source_record_id"] for r in flagged], ["PA_mohegan__2019-12"])
        pa = flagged[0]
        self.assertEqual((pa["discrepancy_published_value"], pa["discrepancy_calculated_value"],
                          pa["discrepancy_difference"], pa["taxable_revenue_usd"]),
                         ("-31744.02", "-42875.40", "-11131.38", "-31744.02"))       # published value untouched
        self.assertIn("pa.xlsx", pa["discrepancy_citation"])
        others = [r for r in self.tables[gos.T_FOB] if r["source_record_id"] != "PA_mohegan__2019-12"]
        self.assertTrue(all(r["discrepancy_flag"] == "no" and not r["discrepancy_measure"] for r in others))
        gap = [g for g in self.tables[gos.T_GAP] if g["affected_record_id"] == pa["financial_observation_id"]]
        self.assertEqual(len(gap), 1)

    def test_existing_digital_rows_cross_referenced_not_added(self):
        feb = self.fob["MI_hannahville__2024-02"]
        self.assertEqual(feb["existing_overlap_source_record_ids"], "DGREV-MI-1|DGREV-MI-2|DGREV-MI-3")
        self.assertEqual(feb["existing_overlap_value_check"], "differs:ADJUSTED_GROSS_REVENUE")
        self.assertEqual(self.dg_map["DGREV-MI-1"], feb["financial_observation_id"])
        self.assertEqual(self.fob["MI_hannahville__2024-01"]["existing_overlap_source_record_ids"], "")

    def test_counts_must_reproduce(self):
        root, pkg, expected = make_package(Path(self.tmp.name) / "again")
        with self.assertRaises(gos.OnlineSportsError):
            gos.build_component(gg.Inputs(root), pkg, [], expected=dict(expected, primary_monthly_rows=7))

    def test_tampered_raw_report_refused(self):
        root, pkg, expected = make_package(Path(self.tmp.name) / "tamper")
        (pkg / "raw" / "mi.xlsx").write_bytes(b"changed")
        with self.assertRaises(gos.OnlineSportsError):
            gos.build_component(gg.Inputs(root), pkg, [], expected=expected)

    def test_receipts_are_relative(self):
        pk = [k for k in self.inputs.receipts if "tribal_sports" in k]
        self.assertTrue(pk)
        for k in pk:
            self.assertFalse(Path(k).is_absolute(), k)
            self.assertNotIn("source", self.inputs.receipts[k])
            self.assertTrue((self.inputs.root / k).is_file(), k)      # build.py re-verifies input_root / path

    def test_ids_are_registered_prefix_tokens_and_gaps_use_natural_keys(self):
        want = {"sportsbook_unit_id": "CEDAR-SRC", "financial_observation_id": "CEDAR-OBS",
                "relationship_id": "CEDAR-REL"}
        for t in (gos.T_FOB, gos.T_UNITS, gos.T_REL):
            for r in self.tables[t]:
                for col in gos.CONTRACTS[t]["derived_ids"]:
                    self.assertEqual(gg.KEY_CLASSES[gg.decode_token(r[col])[0]][0], want[col], (t, col))
        for r in self.tables[gos.T_GAP]:
            self.assertEqual(r["coverage_gap_id"], "|".join(r[c] for c in gos.GAP_KEY_COLUMNS))
            self.assertNotIn("GKEY~", r["coverage_gap_id"])
        self.assertNotIn("coverage_gap_id", gos.CONTRACTS[gos.T_GAP]["derived_ids"])

    def test_property_named_unit_links_only_an_unambiguous_facility(self):
        units = [dict(sportsbook_unit_id="U1", jurisdiction="MI", property_named_in_source="FireKeepers Casino",
                      gaming_facility_id="", facility_link_status="property_named_unresolved"),
                 dict(sportsbook_unit_id="U2", jurisdiction="PA", property_named_in_source="Wind Creek",
                      gaming_facility_id="", facility_link_status="property_named_unresolved"),
                 dict(sportsbook_unit_id="U3", jurisdiction="CT", property_named_in_source="Twin Casino",
                      gaming_facility_id="", facility_link_status="property_named_unresolved")]
        rels = [{"sportsbook_unit_id": "U1", "cedar_uid": HANNAH}, {"sportsbook_unit_id": "U3", "cedar_uid": MOHEG}]
        fk, wc, t1, t2 = ("CEDAR-PLACE-000176-S0", "CEDAR-PLACE-000004-R4", "CEDAR-PLACE-000001-6S",
                          "CEDAR-PLACE-000002-CJ")
        index = {"by_name": {("MI", "firekeepers"): {fk}, ("AL", "wind creek"): {wc}, ("CT", "twin"): {t1, t2}},
                 "uids": {fk: {HANNAH}, wc: {SEMI}, t1: {MOHEG}, t2: {MOHEG}}}
        withheld = Counter()
        gos.resolve_unit_facilities(units, rels, index, withheld)
        self.assertEqual([(u["gaming_facility_id"], u["facility_link_status"]) for u in units],
                         [(fk, "property_named_resolved"),               # one MI facility, same tribe
                          ("", "property_named_unresolved"),             # only an AL property: other state
                          ("", "property_named_unresolved")])            # two candidates: ambiguous
        units[0].update(gaming_facility_id="", facility_link_status="property_named_unresolved")
        gos.resolve_unit_facilities(units[:1], [], None, Counter())      # 1201 absent: no link
        self.assertEqual(units[0]["gaming_facility_id"], "")

    def test_tables_pass_the_shared_validator(self):
        for t, c in gos.CONTRACTS.items():
            self.assertEqual(gg.validate_rows(t, c["header"], self.tables[t], c), [], t)
            self.assertEqual(c["publication_status"], "internal")


if __name__ == "__main__":
    unittest.main(verbosity=1)
