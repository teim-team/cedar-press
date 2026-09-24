#!/usr/bin/env python3
"""Tests for 1200_gaming_grove_revenue (lane D) on small synthetic fixtures.

Each test names a failure mode the producer must refuse or neutralise: a
regional total attached to an entity, overlapping region systems summed, a
national figure computed and passed off as printed, nominal and real mixed, a
forecast counted as paid, a cumulative line summed, a legacy tribe id used as
cedar_uid, a commercial licensee given a Native entity id. No live data needed.

    py -3 code/1200_gaming_grove_revenue_test.py
"""
from __future__ import annotations

import csv
import importlib.util
import os
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
os.environ["CEDAR_GAMING_PROVISIONAL_IDS"] = "1"
import gaming_grove as gg  # noqa: E402

_spec = importlib.util.spec_from_file_location("rev1200", HERE / "1200_gaming_grove_revenue.py")
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

CE_A = "CE-001A9-CA"   # real canonical ids (valid check characters)
CE_B = "CE-0016X-GY"

FY25 = [("Sacramento", 12631303247, 88), ("D.C.", 11218298614, 46), ("St. Paul", 5320261193, 101),
        ("Portland", 4943983904, 58), ("Phoenix", 4211135056, 54), ("Oklahoma City", 3744841561, 80),
        ("Tulsa", 3653169798, 74), ("Rapid City", 439790197, 44)]


def _w(path: Path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({h: r.get(h, "") for h in header})


REG_HDR = ["administrative_region_id", "region_system_code", "region_name", "region_system_version", "fiscal_year",
           "ggr_usd", "ggr_usd_real2025", "operation_count", "ggr_change_pct", "ggr_change_pct_basis",
           "revenue_measure", "includes_nongaming_revenue", "figure_precision", "figure_vintage",
           "deflator_factor_2025", "inflation_base_year", "region_states_in_force", "source_url",
           "source_document", "source_document_title", "fetched_date"]
REC_HDR = ["region_system_version", "fiscal_year", "source_document", "figure_precision", "summed_ggr_usd",
           "printed_ggr_usd", "tolerance_usd", "ggr_agrees", "summed_operations", "printed_operations",
           "operations_agree"]


def make_root(tmp: Path, fy25=FY25, printed=46162783570, text="Totals      $46,162,783,570"):
    rows = []
    for i, (name, usd, ops) in enumerate(fy25):
        rows.append({"administrative_region_id": f"CEDAR-ADMREG-9000{20 + i}", "region_system_code": "NIGC_REGION",
                     "region_name": name, "region_system_version": "NIGC_R4_FY2017_present", "fiscal_year": "2025",
                     "ggr_usd": str(usd), "ggr_usd_real2025": str(usd), "operation_count": str(ops),
                     "revenue_measure": "nigc_gross_gaming_revenue", "includes_nongaming_revenue": "false",
                     "figure_precision": "exact_dollars", "figure_vintage": "own_year_report",
                     "deflator_factor_2025": "1.0", "inflation_base_year": "2025", "region_states_in_force": "CA",
                     "source_url": "https://www.nigc.gov/x", "source_document": "GGR25_071526.pdf",
                     "source_document_title": "FY 2025", "fetched_date": "2026-08-06"})
    # the same FY2002 under two systems: legitimately present, never to be summed together
    for ver, doc, usd, vint in (("NIGC_R1_FY2001_FY2002", "a2002.pdf", 100000, "own_year_report"),
                                ("NIGC_R2_FY2003_FY2007", "b2003.pdf", 110000, "prior_year_column")):
        rows.append({"administrative_region_id": f"CEDAR-ADMREG-{ver[-4:]}", "region_system_code": "NIGC_REGION",
                     "region_name": "Region I", "region_system_version": ver, "fiscal_year": "2002",
                     "ggr_usd": str(usd), "ggr_usd_real2025": str(usd * 2), "operation_count": "3",
                     "revenue_measure": "nigc_gross_gaming_revenue", "includes_nongaming_revenue": "false",
                     "figure_precision": "exact_thousands", "figure_vintage": vint,
                     "deflator_factor_2025": "2.0", "inflation_base_year": "2025", "region_states_in_force": "WA",
                     "source_url": "https://www.nigc.gov/x", "source_document": doc,
                     "source_document_title": "old", "fetched_date": "2026-08-06"})
    clean = tmp / "data" / "clean"
    _w(clean / "nigc_regional_ggr.csv", REG_HDR, rows)
    _w(clean / "inflation_deflator.csv", ["year", "gdp_deflator_index", "base_year", "factor_to_base", "source", "retrieved"],
       [{"year": "2025", "base_year": "2025", "factor_to_base": "1.0", "source": "BEA NIPA Table 1.1.9"},
        {"year": "2002", "base_year": "2025", "factor_to_base": "2.0", "source": "BEA NIPA Table 1.1.9"}])
    _w(tmp / M.NIGC_RECON, REC_HDR,
       [{"region_system_version": "NIGC_R4_FY2017_present", "fiscal_year": "2025", "source_document": "GGR25_071526.pdf",
         "figure_precision": "exact_dollars", "printed_ggr_usd": str(printed), "tolerance_usd": "2000.0",
         "printed_operations": "545"}])
    txt = tmp / M.NIGC_TXT_DIR / "GGR25_071526.txt"
    txt.parent.mkdir(parents=True, exist_ok=True)
    txt.write_text(text, encoding="utf-8")
    return gg.Inputs(tmp)


class RegionalTests(unittest.TestCase):
    def test_fy2025_reconciles_and_national_is_printed_not_computed(self):
        with tempfile.TemporaryDirectory() as d:
            rows = M.build_regional(make_root(Path(d)), [])
        nat = [r for r in rows if r["geography_level"] == "national"]
        self.assertEqual(len(nat), 1)
        self.assertEqual(nat[0]["ggr_nominal_usd"], "46162783570")
        self.assertEqual(nat[0]["operation_count"], "545")
        self.assertEqual(nat[0]["check_reconciles"], "yes")
        self.assertEqual(nat[0]["printed_total_found_in_source_text"], "yes")
        self.assertEqual(nat[0]["source_system"], "nigc_total_reconciliation")  # printed source, not a sum

    def test_unreconciled_national_total_is_refused(self):
        bad = list(FY25)
        bad[0] = ("Sacramento", FY25[0][1] + 5_000_000, 88)
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(gg.GamingContractError):
                M.build_regional(make_root(Path(d), fy25=bad), [])

    def test_printed_total_missing_from_report_text_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(gg.GamingContractError):
                M.build_regional(make_root(Path(d), text="no total printed here"), [])

    def test_region_systems_never_overlap_summed(self):
        with tempfile.TemporaryDirectory() as d:
            rows = M.build_regional(make_root(Path(d)), [])
        fy02 = [r for r in rows if r["fiscal_year"] == "2002"]
        self.assertEqual(len({r["region_system_version"] for r in fy02}), 2)
        self.assertEqual(M.sum_regions(rows, "NIGC_R1_FY2001_FY2002", 2002)[0], 100000)
        mixed = [dict(r) for r in fy02]
        mixed[1]["source_document"] = mixed[0]["source_document"]
        with self.assertRaises(gg.GamingContractError):
            M.assert_no_cross_version_sum(mixed)
        two_docs = [dict(r) for r in fy02]
        for r in two_docs:
            r["region_system_version"] = "NIGC_R1_FY2001_FY2002"
        with self.assertRaises(gg.GamingContractError):
            M.sum_regions(two_docs, "NIGC_R1_FY2001_FY2002", 2002)

    def test_no_entity_or_facility_ids_in_regional_table(self):
        hdr = M.REGION_CONTRACT["header"]
        for c in M.FORBIDDEN_REGION_COLUMNS:
            self.assertNotIn(c, hdr)
        with self.assertRaises(gg.GamingContractError):
            M.check_regions_have_no_entity_ids(hdr + ["cedar_uid"])

    def test_nominal_and_real_are_separate_columns(self):
        with tempfile.TemporaryDirectory() as d:
            rows = M.build_regional(make_root(Path(d)), [])
        r02 = [r for r in rows if r["region_system_version"] == "NIGC_R1_FY2001_FY2002"][0]
        self.assertEqual(r02["ggr_nominal_usd"], "100000")
        self.assertEqual(r02["ggr_real_usd"], "200000")
        self.assertEqual(r02["real_usd_base_year"], "2025")
        rights = M.REGION_CONTRACT["field_rights"]
        self.assertEqual(rights["ggr_real_usd"], "public_derived")

    def test_duplicate_primary_key_refused(self):
        with tempfile.TemporaryDirectory() as d:
            rows = M.build_regional(make_root(Path(d)), [])
            rows.append(dict(rows[0]))
            with self.assertRaises(gg.GamingContractError):
                gg.write_table(Path(d) / "out", M.T_REGION, M.REGION_CONTRACT["header"], rows, M.REGION_CONTRACT)

    def test_band_totals_must_match_regional_print(self):
        regions = [{"geography_level": "national", "fiscal_year": "2025", "ggr_nominal_usd": "46162783570",
                    "operation_count": "545"}]
        M.check_bands_against_regions([{"fiscal_year": "2025", "national_ggr_nominal_usd": "46162783570",
                                        "national_operation_count": "545"}], regions)
        with self.assertRaises(gg.GamingContractError):
            M.check_bands_against_regions([{"fiscal_year": "2025", "national_ggr_nominal_usd": "46000000000",
                                            "national_operation_count": "545"}], regions)


def nat(fy, doc, vintage):
    return {"geography_level": "national", "fiscal_year": fy, "source_document": doc, "figure_vintage": vintage}


class VintageRuleTests(unittest.TestCase):
    def test_exactly_one_preferred_national_figure_per_fy(self):
        rows = [nat("2002", "r2002.pdf", "own_year_report"), nat("2002", "r2003.pdf", "prior_year_column"),
                nat("2001", "r2002.pdf", "prior_year_column"),
                {"geography_level": "nigc_region", "fiscal_year": "2013", "source_document": "r2014.pdf",
                 "figure_vintage": "prior_year_column"}]
        M.apply_vintage_rule(rows)
        pref = {(r["fiscal_year"], r["source_document"]): r["preferred_figure_for_fy"] for r in rows
                if r["geography_level"] == "national"}
        self.assertEqual(pref, {("2002", "r2002.pdf"): "yes", ("2002", "r2003.pdf"): "no",
                                ("2001", "r2002.pdf"): "yes"})   # prior-year column alone is preferred
        self.assertEqual(M.check_one_preferred_national(rows), ["2013"])  # regions, no printed national
        with self.assertRaises(gg.GamingContractError):
            M.check_one_preferred_national([dict(r, preferred_figure_for_fy="yes") for r in rows])

    def test_ambiguous_vintage_refused(self):
        with self.assertRaises(gg.GamingContractError):
            M.apply_vintage_rule([nat("2002", "a.pdf", "own_year_report"), nat("2002", "b.pdf", "own_year_report")])

    def test_built_regions_carry_the_rule(self):
        with tempfile.TemporaryDirectory() as d:
            rows = M.build_regional(make_root(Path(d)), [])
        fy02 = {r["source_document"]: r["preferred_figure_for_fy"] for r in rows if r["fiscal_year"] == "2002"}
        self.assertEqual(fy02, {"a2002.pdf": "yes", "b2003.pdf": "no"})
        self.assertTrue(all(r["preferred_figure_rule"] == M.VINTAGE_RULE for r in rows))
        gaps = M.nigc_gaps(rows, ["2002"])
        self.assertEqual([g["source_status"] for g in gaps], ["national_total_not_printed", "not_yet_published"])
        self.assertEqual(gaps[1]["missing_from"], "2026")


def ca_row(**kw):
    r = {k: "" for k in ("payment_id", "fund", "direction", "recipient_type", "cedar_uid", "tribe_id",
                         "party_name_as_published", "metric", "value", "unit", "period_start", "period_end",
                         "value_suppressed_by_regulator", "revenue_evidence_class", "compact_rate_pct",
                         "compact_revenue_concept", "entity_match_method", "exclusion_flag", "exclusion_reason",
                         "source_authority", "source_document_type", "source_url", "source_page", "source_quote",
                         "document_status", "issue_date", "fetched_date")}
    r.update({"payment_id": "CAGP-1", "fund": "RSTF", "recipient_type": "tribe", "party_name_as_published": "A Tribe",
              "metric": "rstf_distribution_total", "value": "275000.0", "unit": "USD", "period_start": "2024-07-01",
              "period_end": "2024-09-30", "issue_date": "6/4/2020", "tribe_id": "TRBF-XXXX-00"})
    r.update(kw)
    return r


def fl_row(**kw):
    r = {k: "" for k in ("payment_id", "fund", "direction", "recipient_type", "tribe_id", "party_name_as_published",
                         "cedar_place_id", "facility_name", "metric", "value", "unit", "value_as_published",
                         "published_unit", "period_start", "period_end", "conference_date", "is_forecast",
                         "revenue_evidence_class", "governing_compact_id", "compact_rate_schedule",
                         "compact_revenue_concept", "entity_match_method", "exclusion_flag", "exclusion_reason",
                         "source_authority", "source_document_type", "source_url", "source_page", "source_quote",
                         "document_status", "fetched_date", "cedar_uid")}
    r.update({"payment_id": "FLGP-1", "party_name_as_published": "Seminole Tribe of Florida", "cedar_uid": CE_A,
              "metric": "monthly_collections_total", "value": "19500000.0", "unit": "USD", "is_forecast": "no",
              "period_start": "2024-07-01", "period_end": "2024-07-31", "conference_date": "2024-08-01"})
    r.update(kw)
    return r


class PaymentTests(unittest.TestCase):
    def test_forecast_is_never_paid_nor_summable(self):
        w = Counter()
        rows = M.payments_from_fl([fl_row(), fl_row(payment_id="FLGP-2", is_forecast="yes",
                                                     exclusion_flag="state_forecast_not_an_observation")],
                                  M.UidGate(), w)
        paid, fc = rows
        self.assertEqual((paid["payment_status"], paid["summable_within_series"]), ("paid", "yes"))
        self.assertEqual((fc["payment_status"], fc["is_forecast"], fc["summable_within_series"]), ("forecast", "yes", "no"))
        self.assertNotEqual(paid["nonadditive_series_key"], fc["nonadditive_series_key"])
        doctored = dict(fc, payment_status="paid")
        with self.assertRaises(gg.GamingContractError):
            M.check_payments([doctored])

    def test_empty_cell_is_not_a_measured_zero(self):
        r = M.payments_from_fl([fl_row(value="0.0", exclusion_flag="month_after_conference_date_not_yet_occurred")],
                               M.UidGate(), Counter())[0]
        self.assertEqual((r["payment_status"], r["amount_nominal_usd"]), ("empty_cell", ""))

    def test_inflow_vs_redistribution_and_recipient(self):
        rows = M.payments_from_ca([ca_row(cedar_uid=CE_B),
                                   ca_row(payment_id="CAGP-2", metric="rstf_payment_received_fiscal_year_to_date",
                                          cedar_uid=CE_B)], M.UidGate(), Counter())
        out, inn = rows
        self.assertEqual((out["direction"], out["recipient_name"], out["party_cedar_uid_role"]),
                         ("redistribution", "A Tribe", "recipient"))
        self.assertEqual((inn["direction"], inn["payer_name"], inn["party_cedar_uid_role"]), ("inflow", "A Tribe", "payer"))
        self.assertEqual(inn["summable_within_series"], "no")  # year-to-date is cumulative within the year
        self.assertEqual(out["source_date"], "2020-06-04")
        self.assertEqual(out["source_record_id"], "CAGP-1")

    def test_inception_to_date_never_summable(self):
        r = M.payments_from_ca([ca_row(metric="rstf_distribution_inception_to_date")], M.UidGate(), Counter())[0]
        self.assertEqual(r["summable_within_series"], "no")
        with self.assertRaises(gg.GamingContractError):
            M.check_payments([dict(r, summable_within_series="yes")])

    def test_suppressed_amount_is_blank_and_withheld(self):
        r = M.payments_from_ca([ca_row(value="", value_suppressed_by_regulator="yes",
                                       exclusion_flag="value_suppressed_by_regulator")], M.UidGate(), Counter())[0]
        self.assertEqual((r["payment_status"], r["amount_nominal_usd"], r["rights_class"], r["publication_status"]),
                         ("suppressed", "", "withheld_suppressed", "withheld"))

    def test_legacy_tribe_id_never_becomes_cedar_uid(self):
        gate = M.UidGate()
        r = M.payments_from_ca([ca_row(cedar_uid="TRBF-XXXX-00")], gate, Counter())[0]
        self.assertEqual(r["party_cedar_uid"], "")
        self.assertEqual(gate.legacy[("ca_gaming_payments.csv", "cedar_uid")], 1)
        r2 = M.payments_from_ca([ca_row(cedar_uid="")], gate, Counter())[0]
        self.assertEqual(r2["party_cedar_uid"], "")   # no name-only join fills a blank

    def test_aggregate_of_suppressed_tribes_gets_no_entity(self):
        r = M.payments_from_ca([ca_row(recipient_type="aggregate_of_suppressed_tribes", cedar_uid=CE_B)],
                               M.UidGate(), Counter())[0]
        self.assertEqual((r["recipient_type"], r["party_cedar_uid"]), ("aggregate_of_suppressed_tribes", ""))


def dg_row(**kw):
    r = {k: "" for k in ("revenue_id", "state", "period_start", "period_end", "period_type", "licensee_name_as_published",
                         "brand", "product_type", "revenue_scope", "metric", "value_usd", "is_tribe_attributable",
                         "attribution_basis", "source_agency", "source_document", "source_url", "source_quote",
                         "fetched_date", "note", "entity_link_rung", "cedar_uid")}
    r.update({"revenue_id": "DGREV-MI-1", "state": "MI", "period_start": "2026-01-01", "period_end": "2026-01-31",
              "period_type": "month", "licensee_name_as_published": "Op", "product_type": "ONLINE_CASINO",
              "revenue_scope": "ONLINE_CASINO_ONLY", "metric": "GROSS_GAMING_REVENUE", "value_usd": "10.00",
              "is_tribe_attributable": "yes", "cedar_uid": CE_B})
    r.update(kw)
    return r


class ObservationTests(unittest.TestCase):
    def test_commercial_licensee_keeps_row_but_no_entity_id(self):
        rows = M.obs_from_digital([dg_row(revenue_id="DGREV-MI-2", is_tribe_attributable="no", cedar_uid=CE_A)],
                                  M.UidGate(), Counter())
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["cedar_uid"], rows[0]["publication_status"]), ("", "public"))

    def test_alternate_publisher_column_is_not_summed_twice(self):
        a = dg_row(revenue_id="DGREV-CT-5", state="CT", metric="PROMOTIONAL_DEDUCTION",
                   source_quote='x, promotional_coupons_or_credits = 11129')
        b = dg_row(revenue_id="DGREV-CT-6", state="CT", metric="PROMOTIONAL_DEDUCTION",
                   source_quote='x, promotional_deduction_4 = 11129')
        r1, r2 = M.obs_from_digital([b, a], M.UidGate(), Counter())
        self.assertEqual(r1["source_record_id"], "DGREV-CT-5")
        self.assertEqual((r1["summable_within_series"], r2["summable_within_series"]), ("yes", "no"))
        self.assertEqual(r2["alternate_column_of"], r1["reported_observation_id"])
        self.assertEqual(r2["source_measure_label"], "promotional_deduction_4")

    def test_tax_rows_go_to_payments_not_revenue(self):
        t = dg_row(revenue_id="DGREV-MI-9", metric="TAX_OR_PAYMENT")
        self.assertEqual(M.obs_from_digital([t], M.UidGate(), Counter()), [])
        p = M.payments_from_digital([t], M.UidGate(), Counter())[0]
        self.assertEqual((p["amount_kind"], p["direction"], p["party_cedar_uid_role"]),
                         ("tax_or_payment", "inflow", "licensee_attributed_tribe"))

    def test_only_direct_reported_is_public(self):
        rows = M.obs_from_fl([fl_row(metric="net_win_total", value="2098000000", unit="USD"),
                              fl_row(payment_id="FLGP-3", metric="forecast_net_win_slot_machines", is_forecast="yes",
                                     value="1", unit="USD")], M.UidGate(), Counter())
        self.assertEqual([(r["evidence_class"], r["publication_status"]) for r in rows],
                         [("direct_reported", "public"), ("forecast", "internal")])


class IdentifierTests(unittest.TestCase):
    def test_ids_paused_without_provisional_flag(self):
        os.environ.pop("CEDAR_GAMING_PROVISIONAL_IDS")
        try:
            with self.assertRaises(gg.IdContractPending):
                gg.derive_id("GPAY", "x", "y")
        finally:
            os.environ["CEDAR_GAMING_PROVISIONAL_IDS"] = "1"

    def test_vendor_facility_id_never_rendered(self):
        self.assertEqual(M._place("CCP-45100"), "")
        self.assertTrue(M._place("CEDAR-PLACE-000140-WC").endswith("CEDAR-PLACE-000140-WC"))

    def test_every_column_has_rights_and_description(self):
        for t, c in M.CONTRACTS.items():
            for col in c["header"]:
                self.assertIn(col, c["field_rights"], t)
                self.assertIn(col, c["field_descriptions"], t)
            self.assertIn(c["publication_status"], gg.PUBLICATION_STATUSES)


if __name__ == "__main__":
    unittest.main(verbosity=1)
