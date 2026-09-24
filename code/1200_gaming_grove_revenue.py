#!/usr/bin/env python3
"""1200 - Cedar Grove Gaming, lane D: revenue, bands, payments, disclosures.

WHY THIS EXISTS
    Cedar already holds a dozen clean gaming money tables. Each was built by a
    careful per-source script (84 NIGC, 103 California, 105 Florida, 119
    digital, 1080 SEC, 147/814 FAC, 91 NIGC declinations). They do not share
    a grain, a direction vocabulary, a forecast flag or a rights class, so a
    reader who stacks them adds a regional ceiling to a tribe payment to a
    state forecast. This producer re-reads those tables (never the raw PDFs,
    except to re-verify NIGC's printed national totals) and emits five
    component tables with ONE grain each:

    gaming_regional_revenue.csv
        NIGC gross gaming revenue per (region-system version, region, FY),
        plus a national row ONLY where NIGC prints a national total. The
        region sum is carried beside it as a labelled check column, never as
        the reported figure. Nominal and real dollars are separate columns.
        No cedar_uid, no facility id: NIGC publishes no entity revenue and
        this table must never be joined down to one.
    gaming_revenue_bands.csv
        NIGC's FY2022-FY2025 revenue-by-range distribution.
    gaming_government_payments.csv
        One source payment line (CA RSTF/TNGF, FL revenue share, WI/NY/AZ
        payments from state_gaming_observations, digital-gaming taxes), with
        payer, recipient, direction (inflow / redistribution / internal
        allocation), payment_status (paid / forecast / obligation_stated /
        suppressed / empty_cell) and a summability flag. A forecast is never
        `paid`, and an inception-to-date or year-to-date line never summable.
    gaming_reported_revenue_observations.csv
        One reported revenue measure per reporting party x period x measure
        (state aggregates, tribe Net Win, online licensees), with scope and
        evidence_class. Only direct_reported official values are public.
    gaming_financial_disclosures.csv
        SEC, FAC, NIGC financing-review and bond disclosures. FAC SEFA
        amount_expended is a FEDERAL AWARD expenditure, not gaming revenue.
    gaming_online_sportsbook_units / _financials / _relationships.csv and
    gaming_coverage_gaps.csv
        The owner-delivered online sports package (online_sports_2026-09-24),
        built by the imported module gaming_grove_online_sports.py (see its
        docstring): one row per reported unit, per unit x period x revision,
        per unit-entity link, and per machine-readable gap. Never appended to
        regional revenue. Overlapping digital_gaming_revenue sportsbook rows
        stay in gaming_reported_revenue_observations / gaming_government_payments
        and are cross-referenced both ways (overlaps_online_sportsbook_
        observation_id), so neither side is added to the other.

NIGC NATIONAL-TOTAL VINTAGE RULE
    NIGC prints FY2002 and FY2007 national totals twice (own-year report and a
    later report's prior-year column). preferred_figure_for_fy marks exactly one
    figure per (geography level, fiscal year): own_year_report is preferred over
    prior_year_column; when only a prior_year_column figure exists it is
    preferred. FY2013 has regions (prior-year column of the FY2014 chart) but
    no printed national total; it is disclosed in coverage and in
    gaming_coverage_gaps, never computed from regions.

WHAT IS DELIBERATELY LEFT OUT (decision recorded in the receipt)
    gaming_revenue_bounds.csv (13,803 rows) repeats NIGC regional ceilings
    across facilities; votingpatterns property revenue is a compact-rate/GDP
    model. Neither is an observation of revenue and both invite the
    regional-to-facility allocation this collection forbids. They stay where
    they are (internal QA tables) and are NOT copied into a component table;
    the receipt carries the bounds row count and hash so the exclusion is
    auditable. Capacity and facility-universe rows of state_gaming_observations
    belong to the facility/capacity lane and are counted, not emitted.

IDENTIFIERS
    Component ids come only from gaming_grove.derive_id (PROVISIONAL while the
    owner's ID hold stands - run with CEDAR_GAMING_PROVISIONAL_IDS=1). Facility
    ids only via gaming_grove.facility_id_for(cedar_place_id). cedar_uid is
    carried only where the source row already has a canonical CE- value
    (gaming_grove.is_ce_uid); legacy TRBF-/entity_id values are counted and
    dropped, never translated, and no name is ever joined to an entity.

Usage:
    set CEDAR_GAMING_PROVISIONAL_IDS=1
    py -3 code/1200_gaming_grove_revenue.py build --input-root "C:/Users/.../Cedar Press" \
        --output-root C:/Users/.../cedar-grove-gaming-work/components
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gaming_grove as gg  # noqa: E402
import gaming_grove_online_sports as gos  # noqa: E402

SCRIPT = "1200_gaming_grove_revenue"

T_REGION = "gaming_regional_revenue.csv"
T_BANDS = "gaming_revenue_bands.csv"
T_PAY = "gaming_government_payments.csv"
T_OBS = "gaming_reported_revenue_observations.csv"
T_FIN = "gaming_financial_disclosures.csv"
T_OS_UNITS, T_OS_FOB, T_OS_REL, T_GAPS = gos.T_UNITS, gos.T_FOB, gos.T_REL, gos.T_GAP

NIGC_TXT_DIR = "data/raw/external/nigc/ggr_reports/_txt"
NIGC_RECON = "review/nigc_total_reconciliation_2026-08-06.csv"

NIGC_FY_DEFINITION = (
    "NIGC report fiscal year: the aggregate of each gaming operation's OWN audited fiscal year "
    "(operations have differing fiscal year-ends; NIGC states no common Oct-Sep or calendar basis). "
    "FY2025 report: 'fiscal year GGR data ... includes revenue which may have been earned up to 16 "
    "months prior to publication.'")
NIGC_MEASURE_NOTE = (
    "NIGC gross gaming revenue = gaming win only, before expenses and before tribal-state compact "
    "payments; excludes hotel, food, retail and entertainment. Published at region/national level "
    "only. NEVER allocate to a tribe or facility, and never add rows from different "
    "region_system_version values or from different geography_level values.")
NONADDITIVE_REGION = (
    "Rows are additive ONLY across regions within one (region_system_version, fiscal_year, "
    "source_document). The national row is the printed total of those regions, so adding it to them "
    "double counts. FY2002, FY2007 and FY2016 appear under two region systems (first publication vs "
    "restatement); never sum across versions. ggr_nominal_usd and ggr_real_usd are different units.")


# ------------------------------------------------------------------ helpers
def _cols(spec):
    """spec = [(column, rights_class, description)] -> header, rights, descriptions."""
    header = [c for c, _, _ in spec]
    if len(set(header)) != len(header):
        raise gg.GamingContractError("duplicate column in spec")
    for c, r, _ in spec:
        if r not in gg.RIGHTS_CLASSES:
            raise gg.GamingContractError(f"{c}: unknown rights class {r}")
    return header, {c: r for c, r, _ in spec}, {c: d for c, _, d in spec}


def _contract(spec, **kw):
    header, rights, desc = _cols(spec)
    c = {"required": [], "enums": {}, "dates": [], "intervals": [], "public_id_columns": [],
         "derived_ids": {}, "supersedes": [], "row_rights_column": ""}
    c.update(kw)
    c["field_rights"] = rights
    c["field_descriptions"] = desc
    c["header"] = header
    return c


def _money(v):
    """Canonical decimal text for a dollar value; '' stays ''."""
    v = (v or "").strip()
    if v == "":
        return ""
    f = float(v)
    if f == int(f) and abs(f) < 1e15:
        return str(int(f))
    return f"{f:.2f}"


_MDY = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")


def _iso(v):
    v = (v or "").strip()
    m = _MDY.match(v)
    if m:
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    return v if gg.ISO_DATE_RE.match(v) else ""


class UidGate:
    """Carry a cedar_uid only when the source already holds a canonical CE- id."""

    def __init__(self):
        self.legacy = Counter()   # (table, column) -> count of legacy-prefix values seen

    def take(self, value, table, column="cedar_uid"):
        v = (value or "").strip()
        if not v:
            return ""
        if gg.is_ce_uid(v):
            return v
        self.legacy[(table, column)] += 1
        return ""

    def note_legacy_column(self, rows, table, column):
        for r in rows:
            v = (r.get(column) or "").strip()
            if v and not gg.is_ce_uid(v):
                self.legacy[(table, column)] += 1


def _place(value):
    v = (value or "").strip()
    return gg.facility_id_for(v) if gg.PLACE_ID_RE.match(v) else ""


def _year(d):
    return (d or "")[:4]


# ================================================================== 1. REGIONS
REGION_SPEC = [
    ("revenue_observation_id", "public_derived", "Derived GREV id from (version, geography level, region id or NATIONAL, FY, source document)"),
    ("geography_level", "public_official", "nigc_region, or national where NIGC prints a national total"),
    ("region_system_code", "public_official", "Region system family (NIGC_REGION)"),
    ("region_system_version", "public_official", "NIGC region-system version the figure was published under; never sum across versions"),
    ("administrative_region_id", "public_official", "Cedar administrative-region id for the region-version (blank on national rows)"),
    ("region_name", "public_official", "Region name normalised per system version (blank on national rows)"),
    ("region_states_in_force", "public_official", "States in the region under this version's legend (pipe-separated)"),
    ("fiscal_year", "public_official", "NIGC report fiscal year"),
    ("fiscal_year_definition", "public_official", "How NIGC's fiscal year is defined (not federal Oct-Sep, not calendar)"),
    ("figure_vintage", "public_official", "own_year_report or prior_year_column (restated/first published in the next report)"),
    ("preferred_figure_for_fy", "public_derived", "yes on exactly one report's figures per (geography_level, fiscal_year) under preferred_figure_rule; no = retained other vintage, never added to the preferred one"),
    ("preferred_figure_rule", "public_official", "The deterministic vintage rule applied"),
    ("figure_precision", "public_official", "exact_dollars, exact_thousands or rounded_0.1B as printed"),
    ("ggr_nominal_usd", "public_official", "Gross gaming revenue in NOMINAL US dollars as printed"),
    ("operation_count", "public_official", "Gaming operations (audited-financial-statement submitters) as printed"),
    ("ggr_real_usd", "public_derived", "ggr_nominal_usd x deflator_factor; REAL dollars of real_usd_base_year - never mix with nominal"),
    ("real_usd_base_year", "public_official", "Base year of ggr_real_usd"),
    ("deflator_series", "public_official", "Price index used for ggr_real_usd"),
    ("deflator_factor", "public_derived", "Multiplier from fiscal_year dollars to base-year dollars (calendar-year index applied to NIGC FY)"),
    ("ggr_change_pct", "public_derived", "Year-on-year change within this region-system version (computed, see basis)"),
    ("ggr_change_pct_basis", "public_official", "How ggr_change_pct was computed or why it is blank"),
    ("check_sum_of_regions_usd", "public_derived", "CHECK ONLY (national rows): computed sum of this version/FY/document's region rows - not a reported figure"),
    ("check_sum_of_region_operations", "public_derived", "CHECK ONLY (national rows): computed sum of region operation counts"),
    ("check_printed_minus_sum_usd", "public_derived", "CHECK ONLY: printed national total minus computed region sum"),
    ("check_tolerance_usd", "public_derived", "Rounding tolerance applied to the check (exact years $2,000; rounded maps per-region envelope)"),
    ("check_reconciles", "public_derived", "yes/no: printed national total and operations agree with the region sum within tolerance"),
    ("printed_total_found_in_source_text", "public_derived", "yes/no/no_text_layer: the national figure was located in the report's extracted text on this run"),
    ("revenue_measure", "public_official", "nigc_gross_gaming_revenue"),
    ("includes_nongaming_revenue", "public_official", "false: GGR is gaming win only"),
    ("measure_note", "public_official", "What NIGC GGR is and is not; allocation prohibition"),
    ("source_system", "public_official", "nigc_regional_ggr (regions) or nigc_total_reconciliation (national printed totals)"),
    ("source_record_id", "public_official", "Source key: administrative_region_id|FY, or version|FY for national rows"),
    ("source_document", "public_official", "NIGC report file name"),
    ("source_document_title", "public_official", "NIGC report title"),
    ("source_url", "public_official", "NIGC GGR report archive URL"),
    ("source_date", "public_official", "Report publication date where recorded (blank: not recorded upstream)"),
    ("retrieved_date", "public_official", "Date the report was retrieved from nigc.gov"),
    ("rights_class", "public_official", "Row-level rights class"),
]
REGION_CONTRACT = _contract(
    REGION_SPEC,
    grain="One NIGC-published gross gaming revenue figure for one geography (a region under one region-system version, or the printed national total) and one NIGC fiscal year, from one report.",
    primary_key=["revenue_observation_id"],
    required=["region_system_version", "fiscal_year", "ggr_nominal_usd", "geography_level", "source_document"],
    enums={"geography_level": {"nigc_region", "national"},
           "figure_precision": {"exact_dollars", "exact_thousands", "rounded_0.1B"},
           "figure_vintage": {"own_year_report", "prior_year_column"},
           "preferred_figure_for_fy": {"yes", "no"},
           "check_reconciles": {"", "yes", "no"},
           "printed_total_found_in_source_text": {"", "yes", "no", "no_text_layer"},
           "rights_class": gg.PUBLIC_RIGHTS},
    derived_ids={"revenue_observation_id": "GREV"},
    nonadditive_note=NONADDITIVE_REGION,
    publication_status="public",
    supersedes=[{"table": "nigc_regional_ggr.csv", "role": "source of every region row (read-only)"},
                {"table": "review/nigc_total_reconciliation_2026-08-06.csv", "role": "NIGC printed national totals (read-only)"},
                {"table": "inflation_deflator.csv", "role": "deflator series metadata"}],
    row_rights_column="rights_class",
)

VINTAGE_RULE = ("One preferred figure per (geography_level, fiscal_year): the report whose own year it is "
                "(own_year_report) is preferred over a later report's prior-year column (prior_year_column); "
                "when only a prior_year_column figure exists it is preferred. Non-preferred figures are "
                "retained restatements/first publications and are never added to preferred ones.")


def apply_vintage_rule(rows):
    """Mark exactly one source document preferred per (geography level, FY)."""
    docs = defaultdict(dict)
    for r in rows:
        k = (r["geography_level"], r["fiscal_year"])
        prior = docs[k].get(r["source_document"])
        if prior and prior != r["figure_vintage"]:
            raise gg.GamingContractError(f"{k} {r['source_document']}: one report with two vintages")
        docs[k][r["source_document"]] = r["figure_vintage"]
    chosen = {}
    for k, d in docs.items():
        own = sorted(doc for doc, v in d.items() if v == "own_year_report")
        prior = sorted(doc for doc, v in d.items() if v == "prior_year_column")
        pick = own if own else prior
        if len(pick) != 1:
            raise gg.GamingContractError(f"REFUSED: vintage rule ambiguous for {k}: own={own} prior={prior}")
        chosen[k] = pick[0]
    for r in rows:
        r["preferred_figure_for_fy"] = "yes" if chosen[(r["geography_level"], r["fiscal_year"])] == r["source_document"] else "no"
        r["preferred_figure_rule"] = VINTAGE_RULE
    return rows


def check_one_preferred_national(rows):
    """Exactly one preferred national figure for every FY that has one; returns
    the fiscal years with regions but no printed national total."""
    pref = Counter(r["fiscal_year"] for r in rows if r["geography_level"] == "national"
                   and r["preferred_figure_for_fy"] == "yes")
    nat = {r["fiscal_year"] for r in rows if r["geography_level"] == "national"}
    bad = sorted(fy for fy in nat if pref[fy] != 1)
    if bad:
        raise gg.GamingContractError(f"REFUSED: preferred national figure not unique for FY {bad}")
    return sorted({r["fiscal_year"] for r in rows if r["geography_level"] == "nigc_region"} - nat)


FORBIDDEN_REGION_COLUMNS = ("cedar_uid", "gaming_facility_id", "facility_id", "cedar_place_id",
                            "enterprise_id", "tribe_id")


def _printed_tokens(value: int, precision: str):
    if precision == "exact_dollars":
        return [f"{value:,}"]
    if precision == "exact_thousands":
        return [f"{value // 1000:,}"]
    b = value / 1e9
    return [f"{b:.1f}B", f"{b:.1f} B", f"${b:.1f}", f"{b:.1f} Billion", f"{b:.1f}"]


def sum_regions(rows, version, fiscal_year, source_document=None):
    """The only sanctioned way to add NIGC regions: one version, one FY, (one document)."""
    sel = [r for r in rows if r["geography_level"] == "nigc_region"
           and r["region_system_version"] == version and r["fiscal_year"] == str(fiscal_year)
           and (source_document is None or r["source_document"] == source_document)]
    docs = {r["source_document"] for r in sel}
    if len(docs) > 1:
        raise gg.GamingContractError(f"{version} FY{fiscal_year}: regions from {len(docs)} reports; pick one vintage")
    return sum(int(float(r["ggr_nominal_usd"])) for r in sel), sum(int(r["operation_count"] or 0) for r in sel), len(sel)


def assert_no_cross_version_sum(rows):
    """Refuse a table in which one (version, FY, document) mixes region systems."""
    by = defaultdict(set)
    for r in rows:
        if r["geography_level"] == "nigc_region":
            by[(r["fiscal_year"], r["source_document"])].add(r["region_system_version"])
    bad = {k: v for k, v in by.items() if len(v) > 1}
    if bad:
        raise gg.GamingContractError(f"one report mixes region systems: {bad}")


def build_regional(inputs: gg.Inputs, notes):
    _, reg = inputs.clean("nigc_regional_ggr.csv")
    _, defl = inputs.clean("inflation_deflator.csv")
    _, recon = inputs.read(NIGC_RECON)
    dmeta = {int(r["year"]): r for r in defl}
    series = {r["source"] for r in defl}
    out = []
    for r in reg:
        fy = int(r["fiscal_year"])
        dm = dmeta.get(fy, {})
        out.append({
            "revenue_observation_id": gg.derive_id("GREV", r["region_system_version"], "nigc_region",
                                                   r["administrative_region_id"], r["fiscal_year"], r["source_document"]),
            "geography_level": "nigc_region",
            "region_system_code": r["region_system_code"],
            "region_system_version": r["region_system_version"],
            "administrative_region_id": r["administrative_region_id"],
            "region_name": r["region_name"],
            "region_states_in_force": r["region_states_in_force"],
            "fiscal_year": r["fiscal_year"],
            "fiscal_year_definition": NIGC_FY_DEFINITION,
            "figure_vintage": r["figure_vintage"],
            "figure_precision": r["figure_precision"],
            "ggr_nominal_usd": _money(r["ggr_usd"]),
            "operation_count": r["operation_count"],
            "ggr_real_usd": _money(r["ggr_usd_real2025"]),
            "real_usd_base_year": r["inflation_base_year"],
            "deflator_series": dm.get("source", ""),
            "deflator_factor": r["deflator_factor_2025"],
            "ggr_change_pct": r["ggr_change_pct"],
            "ggr_change_pct_basis": r["ggr_change_pct_basis"],
            "check_sum_of_regions_usd": "", "check_sum_of_region_operations": "",
            "check_printed_minus_sum_usd": "", "check_tolerance_usd": "", "check_reconciles": "",
            "printed_total_found_in_source_text": "",
            "revenue_measure": r["revenue_measure"],
            "includes_nongaming_revenue": r["includes_nongaming_revenue"],
            "measure_note": NIGC_MEASURE_NOTE,
            "source_system": "nigc_regional_ggr",
            "source_record_id": f"{r['administrative_region_id']}|{r['fiscal_year']}|{r['source_document']}",
            "source_document": r["source_document"],
            "source_document_title": r["source_document_title"],
            "source_url": r["source_url"],
            "source_date": "",
            "retrieved_date": r["fetched_date"],
            "rights_class": "public_official",
        })
    assert_no_cross_version_sum(out)
    titles = {r["source_document"]: r["source_document_title"] for r in reg}
    fetched = {r["source_document"]: r["fetched_date"] for r in reg}
    states = defaultdict(set)
    for r in reg:
        states[(r["region_system_version"], r["fiscal_year"])].update(r["region_states_in_force"].split("|"))
    text_cache = {}
    unreconciled = []
    for n in recon:
        fy = int(n["fiscal_year"])
        doc = n["source_document"]
        printed = int(float(n["printed_ggr_usd"]))
        ops = int(n["printed_operations"])
        # the regions of this national total are the rows from the same report
        s_usd, s_ops, n_reg = sum_regions(out, n["region_system_version"], fy, doc)
        if n_reg == 0:  # printed total from a report whose regions are carried under another row vintage
            s_usd, s_ops, n_reg = sum_regions(out, n["region_system_version"], fy)
        tol = float(n["tolerance_usd"])
        ok = abs(printed - s_usd) <= tol and ops == s_ops
        if not ok:
            unreconciled.append((n["region_system_version"], fy))
        stem = doc.rsplit(".", 1)[0]
        if stem not in text_cache:
            rel = f"{NIGC_TXT_DIR}/{stem}.txt"
            p = inputs.path(rel)
            if p.is_file():
                raw = p.read_bytes()
                inputs.receipts[rel] = {"path": rel, "sha256": hashlib.sha256(raw).hexdigest(),
                                        "bytes": len(raw), "status": "READ"}
                text_cache[stem] = raw.decode("utf-8", errors="replace")
            else:
                inputs.receipts[rel] = {"path": rel, "status": "ABSENT"}
                text_cache[stem] = None
        txt = text_cache[stem]
        if txt is None or not txt.strip():
            found = "no_text_layer"
        else:
            found = "yes" if any(t in txt for t in _printed_tokens(printed, n["figure_precision"])) else "no"
        f = float(dmeta[fy]["factor_to_base"]) if fy in dmeta else None
        out.append({
            "revenue_observation_id": gg.derive_id("GREV", n["region_system_version"], "national", "NATIONAL", fy, doc),
            "geography_level": "national",
            "region_system_code": "NIGC_REGION",
            "region_system_version": n["region_system_version"],
            "administrative_region_id": "", "region_name": "",
            "region_states_in_force": "|".join(sorted(states[(n["region_system_version"], str(fy))])),
            "fiscal_year": str(fy),
            "fiscal_year_definition": NIGC_FY_DEFINITION,
            "figure_vintage": "own_year_report" if (doc, str(fy)) in {(r["source_document"], r["fiscal_year"]) for r in reg if r["figure_vintage"] == "own_year_report"} else "prior_year_column",
            "figure_precision": n["figure_precision"],
            "ggr_nominal_usd": str(printed),
            "operation_count": str(ops),
            "ggr_real_usd": f"{printed * f:.2f}" if f else "",
            "real_usd_base_year": dmeta[fy]["base_year"] if fy in dmeta else "",
            "deflator_series": dmeta[fy]["source"] if fy in dmeta else "",
            "deflator_factor": dmeta[fy]["factor_to_base"] if fy in dmeta else "",
            "ggr_change_pct": "", "ggr_change_pct_basis": "not_computed_for_national_rows",
            "check_sum_of_regions_usd": str(s_usd),
            "check_sum_of_region_operations": str(s_ops),
            "check_printed_minus_sum_usd": str(printed - s_usd),
            "check_tolerance_usd": _money(n["tolerance_usd"]),
            "check_reconciles": "yes" if ok else "no",
            "printed_total_found_in_source_text": found,
            "revenue_measure": "nigc_gross_gaming_revenue",
            "includes_nongaming_revenue": "false",
            "measure_note": NIGC_MEASURE_NOTE,
            "source_system": "nigc_total_reconciliation",
            "source_record_id": f"{n['region_system_version']}|{fy}|{doc}",
            "source_document": doc,
            "source_document_title": titles.get(doc, ""),
            "source_url": "https://www.nigc.gov/downloads/gross-gaming-revenue-reports/",
            "source_date": "",
            "retrieved_date": fetched.get(doc, ""),
            "rights_class": "public_official",
        })
    if unreconciled:
        raise gg.GamingContractError(f"REFUSED: national totals do not reconcile: {unreconciled}")
    apply_vintage_rule(out)
    check_one_preferred_national(out)
    fy25 = check_fy2025(out)
    notes.append(f"FY2025 check: 8 regions sum to printed national ${fy25[0]:,} and {fy25[1]} operations "
                 "(NIGC_R4_FY2017_present, GGR25_071526.pdf); printed total located in the report text.")
    if len(series) != 1:
        notes.append(f"deflator series not unique: {sorted(series)}")
    return out


FY2025_PRINTED = (46162783570, 545)


def check_fy2025(rows):
    """Runtime proof required by the brief; refuses the build if FY2025 drifts."""
    s, o, n = sum_regions(rows, "NIGC_R4_FY2017_present", 2025)
    nat = [r for r in rows if r["geography_level"] == "national" and r["fiscal_year"] == "2025"]
    if n != 8 or (s, o) != FY2025_PRINTED or len(nat) != 1 \
            or int(nat[0]["ggr_nominal_usd"]) != FY2025_PRINTED[0] or int(nat[0]["operation_count"]) != 545 \
            or nat[0]["printed_total_found_in_source_text"] != "yes":
        raise gg.GamingContractError(f"REFUSED: FY2025 does not reconcile: regions={n} sum={s} ops={o} national={nat}")
    return s, o


# ================================================================== 2. BANDS
BAND_SPEC = [
    ("band_observation_id", "public_derived", "Derived GBND id from (source band_id, FY, report)"),
    ("source_band_id", "internal_crosswalk", "Upstream nigc_revenue_bands.band_id"),
    ("fiscal_year", "public_official", "NIGC report fiscal year"),
    ("fiscal_year_definition", "public_official", "NIGC fiscal-year definition (operations' own fiscal years)"),
    ("band_ordinal", "public_official", "1 = smallest revenue range"),
    ("band_label", "public_official", "NIGC's printed range label"),
    ("band_lower_usd", "public_official", "Range lower edge, nominal USD (blank = open)"),
    ("band_upper_usd", "public_official", "Range upper edge, nominal USD (blank = open)"),
    ("pct_of_operations", "public_official", "Printed share of operations in this range (%)"),
    ("pct_of_revenue", "public_official", "Printed share of national GGR in this range (%)"),
    ("pct_precision", "public_official", "Precision of the printed percentages"),
    ("national_operation_count", "public_official", "Printed national operation count of the report"),
    ("national_ggr_nominal_usd", "public_official", "Printed national GGR (nominal) of the report"),
    ("implied_operation_count_low", "public_derived", "Lower edge of operations implied by the printed share and its rounding"),
    ("implied_operation_count_high", "public_derived", "Upper edge of operations implied by the printed share and its rounding"),
    ("implied_band_ggr_nominal_low_usd", "public_derived", "Lower edge of band GGR implied by printed share x printed total (NOT printed)"),
    ("implied_band_ggr_nominal_high_usd", "public_derived", "Upper edge of band GGR implied by printed share x printed total (NOT printed)"),
    ("suppression_status", "public_official", "not_suppressed_aggregate_only: NIGC prints shares, never operation-level values"),
    ("derivation_note", "public_official", "How the implied ranges were computed"),
    ("source_system", "public_official", "nigc_revenue_bands"),
    ("source_record_id", "public_official", "Upstream band_id"),
    ("source_document", "public_official", "NIGC report file"),
    ("source_page", "public_official", "Page of the chart"),
    ("source_quote", "public_official", "Printed sentence supporting the band shares"),
    ("source_url", "public_official", "NIGC GGR report archive URL"),
    ("source_date", "public_official", "Report publication date (blank: not recorded upstream)"),
    ("retrieved_date", "public_official", "Retrieval date"),
    ("review_status", "public_official", "Upstream review status"),
    ("rights_class", "public_official", "Row-level rights class"),
]
BAND_CONTRACT = _contract(
    BAND_SPEC,
    grain="One NIGC revenue range (band) in one fiscal-year report: its printed share of operations and of national GGR.",
    primary_key=["band_observation_id"],
    required=["fiscal_year", "band_ordinal", "pct_of_operations", "pct_of_revenue"],
    enums={"rights_class": gg.PUBLIC_RIGHTS,
           "suppression_status": {"not_suppressed_aggregate_only"}},
    derived_ids={"band_observation_id": "GBND"},
    nonadditive_note="Shares add to ~100% within one fiscal year only. Implied counts/dollars are rounding envelopes, never point values, never per-operation revenue, never joined to a facility.",
    publication_status="public",
    supersedes=[{"table": "nigc_revenue_bands.csv", "role": "source (read-only)"}],
    row_rights_column="rights_class",
)


def build_bands(inputs):
    _, bands = inputs.clean("nigc_revenue_bands.csv")
    out = []
    for r in bands:
        out.append({
            "band_observation_id": gg.derive_id("GBND", r["band_id"], r["fiscal_year"], r["source_document"]),
            "source_band_id": r["band_id"],
            "fiscal_year": r["fiscal_year"],
            "fiscal_year_definition": NIGC_FY_DEFINITION,
            "band_ordinal": r["band_ordinal"], "band_label": r["band_label"],
            "band_lower_usd": r["band_lower_usd"], "band_upper_usd": r["band_upper_usd"],
            "pct_of_operations": r["pct_of_operations"], "pct_of_revenue": r["pct_of_revenue"],
            "pct_precision": r["pct_precision"],
            "national_operation_count": r["national_operation_count"],
            "national_ggr_nominal_usd": r["national_ggr_usd"],
            "implied_operation_count_low": r["n_operations_implied_low"],
            "implied_operation_count_high": r["n_operations_implied_high"],
            "implied_band_ggr_nominal_low_usd": r["band_aggregate_ggr_implied_low_usd"],
            "implied_band_ggr_nominal_high_usd": r["band_aggregate_ggr_implied_high_usd"],
            "suppression_status": "not_suppressed_aggregate_only",
            "derivation_note": r["derivation_note"],
            "source_system": "nigc_revenue_bands", "source_record_id": r["band_id"],
            "source_document": r["source_document"], "source_page": r["source_page"],
            "source_quote": r["source_quote"], "source_url": r["source_url"], "source_date": "",
            "retrieved_date": r["fetched_date"], "review_status": r["review_status"],
            "rights_class": "public_official",
        })
    return out


def check_bands_against_regions(bands, regions):
    """Band tables quote the same national total as the regional report."""
    nat = {r["fiscal_year"]: (r["ggr_nominal_usd"], r["operation_count"]) for r in regions
           if r["geography_level"] == "national"}
    bad = [b["fiscal_year"] for b in bands
           if nat.get(b["fiscal_year"]) != (b["national_ggr_nominal_usd"], b["national_operation_count"])]
    if bad:
        raise gg.GamingContractError(f"REFUSED: band national totals disagree with regional table for FY {sorted(set(bad))}")


# ================================================================== 3. PAYMENTS
DIRECTIONS = {"inflow", "redistribution", "internal_allocation"}
PAYMENT_STATUSES = {"paid", "forecast", "obligation_stated", "suppressed", "empty_cell"}
AMOUNT_KINDS = {"revenue_share", "distribution", "grant", "tax_or_payment", "federal_excise_tax",
                "lump_sum_payment", "exclusivity_payment", "contribution"}
AMOUNT_ROLES = {"total", "component"}
CADENCES = {"month", "quarter", "fiscal_year", "fiscal_year_to_date", "inception_to_date",
            "state_fiscal_year", "revenue_sharing_cycle", "cumulative_window", "annual"}
NON_SUMMABLE_CADENCES = {"fiscal_year_to_date", "inception_to_date", "cumulative_window"}
PARTY_TYPES = {"tribe", "state_government", "state_fund", "local_governments", "federal_government",
               "online_licensee", "aggregate_of_suppressed_tribes", "all_tribes_state_aggregate"}

PAY_SPEC = [
    ("payment_observation_id", "public_derived", "Derived GPAY id from (source table, source record id)"),
    ("source_system", "public_official", "Upstream clean table the line was read from"),
    ("source_record_id", "public_official", "Upstream id (payment_id / observation_id / revenue_id), preserved"),
    ("source_metric", "public_official", "Upstream metric name, unchanged"),
    ("state", "public_official", "State whose regulator/agency published the line"),
    ("fund", "public_official", "Fund or programme named by the source (RSTF, TNGF, revenue share ...)"),
    ("payer_name", "public_official", "Paying party as published"),
    ("payer_type", "public_official", "Kind of paying party"),
    ("recipient_name", "public_official", "Receiving party as published or as named by the source's own fund"),
    ("recipient_type", "public_official", "Kind of receiving party"),
    ("party_cedar_uid", "public_derived", "Canonical CE- cedar_uid carried from the source row (never name-joined here)"),
    ("party_cedar_uid_role", "public_official", "Which side the cedar_uid identifies: payer, recipient, or licensee_attributed_tribe"),
    ("entity_match_method", "public_official", "How the upstream builder linked the source name to the cedar_uid"),
    ("direction", "public_official", "inflow (to a government), redistribution (government pays onward), internal_allocation (split inside a government)"),
    ("amount_kind", "public_official", "Substantive kind of money"),
    ("amount_role", "public_official", "total or component of a total printed on another line; never add a component to its total"),
    ("payment_status", "public_official", "paid, forecast, obligation_stated, suppressed or empty_cell; a forecast is never paid"),
    ("is_forecast", "public_official", "yes/no"),
    ("amount_nominal_usd", "public_official", "Amount in NOMINAL US dollars (blank when suppressed or an empty cell)"),
    ("amount_as_published", "public_official", "Figure as printed"),
    ("published_unit", "public_official", "Unit as printed (USD, USD millions ...)"),
    ("period_start", "public_official", "Period start (ISO)"),
    ("period_end", "public_official", "Period end (ISO)"),
    ("period_cadence", "public_official", "Cadence of the period; ytd/inception-to-date/cumulative are never summable"),
    ("fiscal_year_definition", "public_official", "Fiscal-year basis of the period"),
    ("basis", "public_official", "Revenue concept / base the payment is computed on, if the source or compact states it"),
    ("compact_reference", "public_official", "Governing compact id given on the source row (compacts lane namespace)"),
    ("compact_rate_text", "public_official", "Compact rate schedule text given on the source row"),
    ("value_suppressed_by_source", "public_official", "yes when the publisher suppressed the amount"),
    ("sum_exclusion_flag", "public_official", "Upstream exclusion flag (restated, superseded, cumulative, suppressed ...)"),
    ("sum_exclusion_reason", "public_official", "Upstream exclusion reason text"),
    ("summable_within_series", "public_derived", "yes only for paid, non-excluded, non-cumulative lines; add only within nonadditive_series_key"),
    ("nonadditive_series_key", "public_derived", "Lines may be added only when this key is equal"),
    ("upstream_revenue_evidence_class", "public_official", "Upstream revenue_evidence_class (a payment is never a revenue figure)"),
    ("overlaps_online_sportsbook_observation_id", "public_derived", "GFOB id of the online-sports package observation for the same state/month/licensee (digital sportsbook tax rows); never add both"),
    ("document_status", "public_official", "original / revised / latest_statement_for_period, as upstream"),
    ("source_authority", "public_official", "Publishing agency"),
    ("source_document_type", "public_official", "Kind of source document"),
    ("source_url", "public_official", "Source document URL"),
    ("source_page", "public_official", "Page in the source document"),
    ("source_quote", "public_official", "Printed line the figure was read from"),
    ("source_date", "public_official", "Issue/conference date of the document (ISO) where given"),
    ("retrieved_date", "public_official", "Date retrieved"),
    ("rights_class", "public_official", "Row-level rights class"),
    ("publication_status", "public_official", "Row-level publication status"),
]
PAY_CONTRACT = _contract(
    PAY_SPEC,
    grain="One government payment line as published: one payer, one recipient, one fund, one period, one status (paid/forecast/obligation/suppressed), one amount.",
    primary_key=["payment_observation_id"],
    required=["source_system", "source_record_id", "direction", "payment_status", "amount_kind", "period_cadence"],
    enums={"direction": DIRECTIONS, "payment_status": PAYMENT_STATUSES, "amount_kind": AMOUNT_KINDS,
           "amount_role": AMOUNT_ROLES, "period_cadence": CADENCES, "is_forecast": {"yes", "no"},
           "payer_type": PARTY_TYPES, "recipient_type": PARTY_TYPES,
           "party_cedar_uid_role": {"", "payer", "recipient", "licensee_attributed_tribe"},
           "summable_within_series": {"yes", "no"}, "value_suppressed_by_source": {"yes", "no"},
           "publication_status": gg.PUBLICATION_STATUSES},
    dates=["period_start", "period_end", "source_date", "retrieved_date"],
    intervals=[("period_start", "period_end")],
    derived_ids={"payment_observation_id": "GPAY"},
    nonadditive_note=("Never add inflow to redistribution, a forecast/obligation to a paid line, a component to "
                      "its total, a ytd/inception-to-date line to anything, or two funds. Add only lines with "
                      "summable_within_series=yes and an equal nonadditive_series_key. A payment is not revenue "
                      "and is never inverted into revenue here."),
    publication_status="public",
    supersedes=[{"table": "ca_gaming_payments.csv", "role": "all 41,758 lines"},
                {"table": "fl_gaming_payments.csv", "role": "payment/receipt/obligation lines (Net Win and rate lines go elsewhere)"},
                {"table": "state_gaming_observations.csv", "role": "payment-class rows (WI, NY, AZ contributions)"},
                {"table": "digital_gaming_revenue.csv", "role": "TAX_OR_PAYMENT and FEDERAL_EXCISE_TAX rows"}],
    row_rights_column="rights_class",
)

CA_METRICS = {
    # metric: (amount_kind, direction, role, cadence override)
    "rstf_payment_received_fiscal_year_to_date": ("revenue_share", "inflow", "total", "fiscal_year_to_date"),
    "rstf_payment_received_inception_to_date": ("revenue_share", "inflow", "total", "inception_to_date"),
    "rstf_distribution_total": ("distribution", "redistribution", "total", "quarter"),
    "rstf_distribution_from_revenue_received": ("distribution", "redistribution", "component", "quarter"),
    "rstf_distribution_from_shortfall_transfer": ("distribution", "redistribution", "component", "quarter"),
    "rstf_distribution_annual_from_revenue_received": ("distribution", "redistribution", "component", "annual"),
    "rstf_distribution_inception_to_date": ("distribution", "redistribution", "total", "inception_to_date"),
}

FL_PAY_METRICS = {
    "monthly_collections_total": ("revenue_share", "inflow", "total", "month"),
    "monthly_collections_general_revenue": ("revenue_share", "internal_allocation", "component", "month"),
    "monthly_collections_trust_fund": ("revenue_share", "internal_allocation", "component", "month"),
    "receipts_total_received": ("revenue_share", "inflow", "total", "state_fiscal_year"),
    "receipts_general_revenue": ("revenue_share", "internal_allocation", "component", "state_fiscal_year"),
    "receipts_trust_fund": ("revenue_share", "internal_allocation", "component", "state_fiscal_year"),
    "receipts_reserve_within_gr": ("revenue_share", "internal_allocation", "component", "state_fiscal_year"),
    "receipts_release_of_reserve": ("revenue_share", "internal_allocation", "component", "state_fiscal_year"),
    "receipts_after_release_of_reserve": ("revenue_share", "internal_allocation", "component", "state_fiscal_year"),
    "receipts_excluding_banked_card_game_reserve": ("revenue_share", "internal_allocation", "component", "state_fiscal_year"),
    "receipts_local_distribution": ("revenue_share", "redistribution", "component", "state_fiscal_year"),
    "revenue_share_obligation_for_cycle": ("revenue_share", "inflow", "total", "revenue_sharing_cycle"),
    "forecast_revenue_share_all_covered_games": ("revenue_share", "inflow", "total", "revenue_sharing_cycle"),
    "forecast_revenue_share_slot_machines": ("revenue_share", "inflow", "component", "revenue_sharing_cycle"),
    "forecast_revenue_share_table_games": ("revenue_share", "inflow", "component", "revenue_sharing_cycle"),
    "forecast_revenue_share_sports_betting": ("revenue_share", "inflow", "component", "revenue_sharing_cycle"),
    "forecast_revenue_share_sports_betting_qualified_permitholder_brand": ("revenue_share", "inflow", "component", "revenue_sharing_cycle"),
}
FL_OBS_METRICS = {"net_win_total", "net_win_subject_to_revenue_share", "forecast_net_win_all_covered_games",
                  "forecast_net_win_slot_machines", "forecast_net_win_table_games", "forecast_net_win_sports_betting",
                  "forecast_net_win_sports_betting_qualified_permitholder_brand",
                  "property_revenue_published_by_state_regulator"}
FL_RATE_PREFIX = "forecast_effective_share_rate_"

STATE_PAY_METRICS = {
    "lump_sum_payment_to_state": ("lump_sum_payment", "tribe"),
    "lump_sum_payment_to_state_cumulative_199900_to_201617": ("lump_sum_payment", "tribe"),
    "regulatory_exclusivity_payment_to_state": ("exclusivity_payment", "tribe"),
    "tribal_contributions_state_aggregate": ("contribution", "all_tribes_state_aggregate"),
    "tribal_contributions_to_local_government_aggregate": ("contribution", "all_tribes_state_aggregate"),
}
STATE_OBS_METRICS = {"net_win_state_aggregate", "gross_gaming_revenue_state_aggregate", "slot_machine_net_drop_class_iii"}
STATE_OUT_OF_LANE = {"gaming_machines", "table_games", "regulator_listed_facility", "compact_facility_listed"}
STATE_NAMES = {"WI": "State of Wisconsin", "NY": "State of New York", "AZ": "State of Arizona",
               "FL": "State of Florida", "CT": "State of Connecticut", "MI": "State of Michigan"}


def _summable(status, flag, cadence):
    return "yes" if status == "paid" and not flag and cadence not in NON_SUMMABLE_CADENCES else "no"


def _pay_row(**kw):
    row = {c: "" for c in PAY_CONTRACT["header"]}
    row.update(kw)
    row["payment_observation_id"] = gg.derive_id("GPAY", row["source_system"], row["source_record_id"])
    row["is_forecast"] = "yes" if row["payment_status"] == "forecast" else "no"
    if row["payment_status"] in ("suppressed", "empty_cell"):
        row["amount_nominal_usd"] = ""
    row["summable_within_series"] = _summable(row["payment_status"], row["sum_exclusion_flag"], row["period_cadence"])
    row["nonadditive_series_key"] = "|".join([row["source_system"], row["state"], row["fund"], row["source_metric"],
                                              row["direction"], row["amount_role"], row["period_cadence"],
                                              row["payment_status"]])
    if not row["rights_class"]:
        row["rights_class"] = "withheld_suppressed" if row["payment_status"] == "suppressed" else "public_official"
    row["publication_status"] = "public" if row["rights_class"] in gg.PUBLIC_RIGHTS else "withheld"
    return row


def payments_from_ca(rows, uid, withheld):
    out = []
    for r in rows:
        m = r["metric"]
        if r["fund"] == "TNGF":
            kind, direction, role, cadence = "grant", "redistribution", "total", "fiscal_year"
        elif m in CA_METRICS:
            kind, direction, role, cadence = CA_METRICS[m]
        else:
            withheld[f"ca_unmapped_metric:{m}"] += 1
            continue
        tribe_side = r["party_name_as_published"]
        agg = r["recipient_type"] == "aggregate_of_suppressed_tribes"
        tribe_type = "aggregate_of_suppressed_tribes" if agg else "tribe"
        fund_party = f"California Gambling Control Commission ({r['fund']})"
        cu = "" if agg else uid.take(r["cedar_uid"], "ca_gaming_payments.csv")
        if direction == "inflow":
            payer, ptype, rec, rtype, role_uid = tribe_side, tribe_type, fund_party, "state_fund", "payer"
        else:
            payer, ptype, rec, rtype, role_uid = fund_party, "state_fund", tribe_side, tribe_type, "recipient"
        status = "suppressed" if r["value_suppressed_by_regulator"] == "yes" else "paid"
        basis_fy = ("California state fiscal year Jul 1-Jun 30" if cadence in ("fiscal_year", "fiscal_year_to_date", "annual")
                    else "calendar quarter inside the California state fiscal year (Jul 1-Jun 30)"
                    if cadence == "quarter" else "inception of the fund to period_end")
        out.append(_pay_row(
            source_system="ca_gaming_payments", source_record_id=r["payment_id"], source_metric=m,
            state="CA", fund=r["fund"], payer_name=payer, payer_type=ptype, recipient_name=rec, recipient_type=rtype,
            party_cedar_uid=cu, party_cedar_uid_role=role_uid if cu else "",
            entity_match_method=r["entity_match_method"],
            direction=direction, amount_kind=kind, amount_role=role, payment_status=status,
            amount_nominal_usd=_money(r["value"]), amount_as_published=r["value"], published_unit=r["unit"],
            period_start=r["period_start"], period_end=r["period_end"], period_cadence=cadence,
            fiscal_year_definition=basis_fy,
            basis=r["compact_revenue_concept"], compact_reference="",
            compact_rate_text=(r["compact_rate_pct"] + "%") if r["compact_rate_pct"] else "",
            value_suppressed_by_source="yes" if status == "suppressed" else "no",
            sum_exclusion_flag=r["exclusion_flag"], sum_exclusion_reason=r["exclusion_reason"],
            upstream_revenue_evidence_class=r["revenue_evidence_class"], document_status=r["document_status"],
            source_authority=r["source_authority"], source_document_type=r["source_document_type"],
            source_url=r["source_url"], source_page=r["source_page"], source_quote=r["source_quote"],
            source_date=_iso(r["issue_date"]), retrieved_date=r["fetched_date"]))
    return out


def _fl_status(r):
    if r["exclusion_flag"] == "month_after_conference_date_not_yet_occurred":
        return "empty_cell"
    if r["is_forecast"] == "yes":
        return "forecast"
    if r["metric"] == "revenue_share_obligation_for_cycle":
        return "obligation_stated"
    return "paid"


def _fl_fy_def(cadence):
    return {"month": "calendar month of collection (EDR: collections lag activity by one month)",
            "state_fiscal_year": "Florida state fiscal year Jul 1-Jun 30",
            "revenue_sharing_cycle": "compact revenue-sharing cycle as labelled by EDR"}[cadence]


def payments_from_fl(rows, uid, withheld):
    out = []
    for r in rows:
        m = r["metric"]
        if m in FL_OBS_METRICS:
            continue
        if m.startswith(FL_RATE_PREFIX):
            withheld["fl_effective_share_rate_forecast_not_money"] += 1
            continue
        if m not in FL_PAY_METRICS:
            withheld[f"fl_unmapped_metric:{m}"] += 1
            continue
        kind, direction, role, cadence = FL_PAY_METRICS[m]
        status = _fl_status(r)
        cu = uid.take(r["cedar_uid"], "fl_gaming_payments.csv")
        if direction == "inflow":
            payer, ptype, rec, rtype, cu_role = r["party_name_as_published"], "tribe", "State of Florida", "state_government", "payer"
        elif direction == "redistribution":
            payer, ptype, rec, rtype, cu_role = "State of Florida", "state_government", "Florida local governments (local distribution)", "local_governments", ""
            cu = ""
        else:
            payer, ptype, rec, rtype, cu_role = "State of Florida", "state_government", "State of Florida (fund allocation)", "state_government", ""
            cu = ""
        out.append(_pay_row(
            source_system="fl_gaming_payments", source_record_id=r["payment_id"], source_metric=m,
            state="FL", fund=r["fund"] or "Florida Indian Gaming revenue share",
            payer_name=payer, payer_type=ptype, recipient_name=rec, recipient_type=rtype,
            party_cedar_uid=cu, party_cedar_uid_role=cu_role if cu else "",
            entity_match_method=r["entity_match_method"], direction=direction, amount_kind=kind,
            amount_role=role, payment_status=status,
            amount_nominal_usd=_money(r["value"]) if r["unit"] == "USD" else "",
            amount_as_published=r["value_as_published"], published_unit=r["published_unit"],
            period_start=r["period_start"], period_end=r["period_end"], period_cadence=cadence,
            fiscal_year_definition=_fl_fy_def(cadence),
            basis=r["compact_revenue_concept"], compact_reference=r["governing_compact_id"],
            compact_rate_text=r["compact_rate_schedule"], value_suppressed_by_source="no",
            sum_exclusion_flag=r["exclusion_flag"], sum_exclusion_reason=r["exclusion_reason"],
            upstream_revenue_evidence_class=r["revenue_evidence_class"], document_status=r["document_status"],
            source_authority=r["source_authority"], source_document_type=r["source_document_type"],
            source_url=r["source_url"], source_page=r["source_page"], source_quote=r["source_quote"],
            source_date=r["conference_date"], retrieved_date=r["fetched_date"]))
    return out


def payments_from_state(rows, uid, withheld):
    out = []
    for r in rows:
        m = r["metric"]
        if m not in STATE_PAY_METRICS:
            continue
        kind, ptype = STATE_PAY_METRICS[m]
        cumulative = r["exclusion_flag"] == "cumulative_window" or "cumulative" in m
        cadence = "cumulative_window" if cumulative else "fiscal_year"
        suppressed = r["metric_class"] == "absence" or r["exclusion_flag"] == "withheld_by_source"
        status = "suppressed" if suppressed else "paid"
        local = "local_government" in m
        payer = r["tribe_name_as_published"] or r["tribe_canonical_name"] if ptype == "tribe" \
            else f"All {r['state']} compact tribes (state aggregate)"
        cu = uid.take(r["cedar_uid"], "state_gaming_observations.csv") if ptype == "tribe" else ""
        mult = 1e6 if r["unit"] == "usd_millions" else 1
        amt = _money(str(float(r["value"]) * mult)) if r["value"] not in ("",) else ""
        out.append(_pay_row(
            source_system="state_gaming_observations", source_record_id=r["observation_id"], source_metric=m,
            state=r["state"], fund="",
            payer_name=payer, payer_type=ptype,
            recipient_name=f"{r['state']} local governments" if local else STATE_NAMES.get(r["state"], r["state"]),
            recipient_type="local_governments" if local else "state_government",
            party_cedar_uid=cu, party_cedar_uid_role="payer" if cu else "",
            entity_match_method=r["tribe_match_method"], direction="inflow", amount_kind=kind,
            amount_role="total", payment_status=status, amount_nominal_usd=amt,
            amount_as_published=r["value"], published_unit=r["unit"],
            period_start=r["period_start"], period_end=r["period_end"] or (r["as_of_date"] if len(r["as_of_date"]) == 10 else ""),
            period_cadence=cadence, fiscal_year_definition=f"{r['state']} state fiscal year as published ({r['as_of_date_precision']})",
            value_suppressed_by_source="yes" if suppressed else "no",
            sum_exclusion_flag=r["exclusion_flag"], sum_exclusion_reason=r["exclusion_reason"],
            upstream_revenue_evidence_class=r["revenue_evidence"],
            source_authority=r["source_authority"], source_document_type=r["source_document_type"],
            source_url=r["source_url"], source_page=r["source_page"], source_quote=r["source_quote"],
            source_date="", retrieved_date=r["fetched_date"]))
    return out


DIGITAL_PAY_METRICS = {"TAX_OR_PAYMENT": "tax_or_payment", "FEDERAL_EXCISE_TAX": "federal_excise_tax"}


def payments_from_digital(rows, uid, withheld):
    out = []
    for r in rows:
        kind = DIGITAL_PAY_METRICS.get(r["metric"])
        if not kind:
            continue
        attributable = r["is_tribe_attributable"] == "yes"
        cu = uid.take(r["cedar_uid"], "digital_gaming_revenue.csv") if attributable else ""
        fed = kind == "federal_excise_tax"
        out.append(_pay_row(
            source_system="digital_gaming_revenue", source_record_id=r["revenue_id"], source_metric=r["metric"],
            state=r["state"], fund=r["product_type"],
            payer_name=r["licensee_name_as_published"], payer_type="online_licensee",
            recipient_name="United States (federal wagering excise tax)" if fed else STATE_NAMES.get(r["state"], r["state"]),
            recipient_type="federal_government" if fed else "state_government",
            party_cedar_uid=cu, party_cedar_uid_role="licensee_attributed_tribe" if cu else "",
            entity_match_method=r["entity_link_rung"], direction="inflow", amount_kind=kind,
            amount_role="total", payment_status="paid", amount_nominal_usd=_money(r["value_usd"]),
            amount_as_published=r["value_usd"], published_unit="USD",
            period_start=r["period_start"], period_end=r["period_end"], period_cadence="month",
            fiscal_year_definition="calendar month", basis=r["revenue_scope"],
            value_suppressed_by_source="no", sum_exclusion_flag="", sum_exclusion_reason="",
            upstream_revenue_evidence_class="", source_authority=r["source_agency"],
            source_document_type=r["source_document"], source_url=r["source_url"], source_page="",
            source_quote=r["source_quote"], source_date="", retrieved_date=r["fetched_date"]))
    return out


# ================================================================== 4. REPORTED REVENUE
SCOPES = {"state_aggregate", "tribe", "property", "online_licensee", "enterprise"}
EVIDENCE = {"direct_reported", "derived_from_compact_rate", "bound", "model", "forecast", "documented_absence"}

OBS_SPEC = [
    ("reported_observation_id", "public_derived", "Derived GSRC id from (source table, source record id)"),
    ("source_system", "public_official", "Upstream clean table"),
    ("source_record_id", "public_official", "Upstream id, preserved"),
    ("source_metric", "public_official", "Upstream metric name, unchanged"),
    ("source_measure_label", "public_official", "Publisher's own field label where the source row names it"),
    ("state", "public_official", "State of the publishing agency"),
    ("scope", "public_official", "Who the figure is about: state_aggregate, tribe, property, online_licensee, enterprise"),
    ("reporting_party_name", "public_official", "Party the figure is about, as published"),
    ("brand", "public_official", "Brand/skin as published (online licensees)"),
    ("cedar_uid", "public_derived", "Canonical CE- id carried from the source row only (blank for commercial operators and aggregates)"),
    ("attribution_basis", "public_official", "Why the source row is or is not attributed to a Native entity"),
    ("gaming_facility_id", "public_derived", "Facility id via gaming_grove.facility_id_for(cedar_place_id) (property scope only)"),
    ("product_scope", "public_official", "Product or game scope of the measure"),
    ("measure", "public_official", "Normalised measure name (net_win, gross_gaming_revenue, adjusted_gross_revenue, handle ...)"),
    ("evidence_class", "public_official", "direct_reported, derived_from_compact_rate, bound, model, forecast or documented_absence"),
    ("value_nominal_usd", "public_official", "Value in NOMINAL US dollars (blank for absences)"),
    ("value_as_published", "public_official", "Value as printed"),
    ("published_unit", "public_official", "Unit as printed"),
    ("period_start", "public_official", "Period start (ISO)"),
    ("period_end", "public_official", "Period end (ISO)"),
    ("period_cadence", "public_official", "month, fiscal_year, calendar_year, revenue_sharing_cycle, none"),
    ("fiscal_year_definition", "public_official", "Fiscal/calendar basis of the period"),
    ("alternate_column_of", "public_derived", "When the publisher prints the same concept in two columns, the id of the first; never add both"),
    ("sum_exclusion_flag", "public_official", "Upstream exclusion flag"),
    ("sum_exclusion_reason", "public_official", "Upstream exclusion reason"),
    ("summable_within_series", "public_derived", "yes only for direct_reported, non-excluded, non-alternate rows; add only within nonadditive_series_key"),
    ("nonadditive_series_key", "public_derived", "Rows may be added only when this key is equal"),
    ("absence_reason", "public_official", "For documented_absence rows: why the figure does not exist"),
    ("overlaps_online_sportsbook_observation_id", "public_derived", "GFOB id of the online-sports package observation describing the same state/month/licensee; the two are never added"),
    ("source_authority", "public_official", "Publishing agency"),
    ("source_document", "public_official", "Source document / dataset"),
    ("source_url", "public_official", "Source URL"),
    ("source_page", "public_official", "Page"),
    ("source_quote", "public_official", "Printed text the figure came from"),
    ("source_date", "public_official", "Document date where given"),
    ("retrieved_date", "public_official", "Date retrieved"),
    ("rights_class", "public_official", "Row-level rights class"),
    ("publication_status", "public_official", "Row-level publication status"),
]
OBS_CONTRACT = _contract(
    OBS_SPEC,
    grain="One reported revenue-type measure for one reporting party (state aggregate, tribe, property or online licensee) for one period, as one source row publishes it.",
    primary_key=["reported_observation_id"],
    required=["source_system", "source_record_id", "scope", "measure", "evidence_class"],
    enums={"scope": SCOPES, "evidence_class": EVIDENCE, "summable_within_series": {"yes", "no"},
           "period_cadence": {"month", "fiscal_year", "calendar_year", "revenue_sharing_cycle", "none"},
           "publication_status": gg.PUBLICATION_STATUSES},
    dates=["period_start", "period_end", "source_date", "retrieved_date"],
    intervals=[("period_start", "period_end")],
    public_id_columns=["gaming_facility_id"],
    derived_ids={"reported_observation_id": "GSRC"},
    nonadditive_note=("Different scopes (state aggregate, tribe, licensee), measures (handle, GGR, AGR, Net Win), "
                      "products (online casino vs sportsbook) and evidence classes are never added. Online revenue "
                      "is never added to physical casino GGR or to NIGC regional GGR. Forecast/derived rows are internal."),
    publication_status="public",
    supersedes=[{"table": "state_gaming_observations.csv", "role": "revenue and documented-absence rows"},
                {"table": "fl_gaming_payments.csv", "role": "Net Win lines and property-revenue absence"},
                {"table": "digital_gaming_revenue.csv", "role": "all non-payment rows"}],
    row_rights_column="rights_class",
)


def _obs_row(**kw):
    row = {c: "" for c in OBS_CONTRACT["header"]}
    row.update(kw)
    row["reported_observation_id"] = gg.derive_id("GSRC", row["source_system"], row["source_record_id"])
    ev = row["evidence_class"]
    if not row["rights_class"]:
        row["rights_class"] = "public_official" if ev in ("direct_reported", "documented_absence") else "internal_model"
    row["publication_status"] = "public" if row["rights_class"] in gg.PUBLIC_RIGHTS else "internal"
    row["summable_within_series"] = "yes" if (ev == "direct_reported" and not row["sum_exclusion_flag"]
                                              and not row["alternate_column_of"]) else "no"
    row["nonadditive_series_key"] = "|".join([row["source_system"], row["state"], row["scope"], row["product_scope"],
                                              row["measure"], row["evidence_class"], row["period_cadence"]])
    return row


def obs_from_state(rows, uid, withheld):
    out = []
    for r in rows:
        m = r["metric"]
        if m in STATE_OUT_OF_LANE:
            withheld[f"state_obs_out_of_lane_capacity_or_universe:{m}"] += 1
            continue
        if m in STATE_PAY_METRICS:
            continue
        absence = r["metric_class"] == "absence"
        if not absence and m not in STATE_OBS_METRICS:
            withheld[f"state_obs_unmapped:{m}"] += 1
            continue
        if absence:
            ev, measure = "documented_absence", "documented_absence"
        elif m == "slot_machine_net_drop_class_iii":
            ev, measure = "derived_from_compact_rate", "slot_machine_net_drop"
        else:
            ev, measure = "direct_reported", ("net_win" if m.startswith("net_win") else "gross_gaming_revenue")
        scope = {"state": "state_aggregate", "tribe": "tribe", "property": "property"}.get(r["applies_to"], "state_aggregate")
        mult = 1e6 if r["unit"] == "usd_millions" else 1
        val = _money(str(float(r["value"]) * mult)) if (r["value"] and not absence) else ""
        cadence = "calendar_year" if r["as_of_date_precision"] == "reporting_period" and r["period_start"].endswith("-01-01") \
            else ("fiscal_year" if r["period_start"] else "none")
        out.append(_obs_row(
            source_system="state_gaming_observations", source_record_id=r["observation_id"], source_metric=m,
            state=r["state"], scope=scope,
            reporting_party_name=r["tribe_name_as_published"] or r["facility_name_as_published"] or f"all tribal gaming in {r['state']}",
            cedar_uid=uid.take(r["cedar_uid"], "state_gaming_observations.csv") if scope == "tribe" else "",
            attribution_basis=r["tribe_match_method"], gaming_facility_id=_place(r["cedar_place_id"]) if scope == "property" else "",
            product_scope="class_iii_slot_machines" if "slot" in m else r["applies_to"],
            measure=measure, evidence_class=ev, value_nominal_usd=val,
            value_as_published=r["value"], published_unit=r["unit"],
            period_start=r["period_start"], period_end=r["period_end"], period_cadence=cadence,
            fiscal_year_definition=f"as published ({r['as_of_date_precision']})",
            sum_exclusion_flag=r["exclusion_flag"], sum_exclusion_reason=r["exclusion_reason"],
            absence_reason=(r["exclusion_flag"] + ": " + r["applies_to"]) if absence else "",
            source_authority=r["source_authority"], source_document=r["source_document_type"],
            source_url=r["source_url"], source_page=r["source_page"], source_quote=r["source_quote"],
            source_date="", retrieved_date=r["fetched_date"]))
    return out


def obs_from_fl(rows, uid, withheld):
    out = []
    for r in rows:
        m = r["metric"]
        if m not in FL_OBS_METRICS:
            continue
        if m == "property_revenue_published_by_state_regulator":
            out.append(_obs_row(
                source_system="fl_gaming_payments", source_record_id=r["payment_id"], source_metric=m, state="FL",
                scope="property", reporting_party_name=r["facility_name"],
                cedar_uid="", attribution_basis=r["entity_match_method"],
                gaming_facility_id=_place(r["cedar_place_id"]), product_scope="all_gaming",
                measure="documented_absence", evidence_class="documented_absence",
                period_cadence="none", fiscal_year_definition="not applicable",
                sum_exclusion_flag=r["exclusion_flag"], sum_exclusion_reason=r["exclusion_reason"],
                absence_reason=r["exclusion_reason"], source_authority=r["source_authority"],
                source_document=r["source_document_type"], source_url=r["source_url"], source_page=r["source_page"],
                source_quote=r["source_quote"], retrieved_date=r["fetched_date"]))
            continue
        forecast = r["is_forecast"] == "yes"
        measure = "net_win_subject_to_revenue_share" if m == "net_win_subject_to_revenue_share" else "net_win"
        product = m.replace("forecast_net_win_", "") if forecast and m.startswith("forecast_net_win_") else "covered_games_all"
        out.append(_obs_row(
            source_system="fl_gaming_payments", source_record_id=r["payment_id"], source_metric=m, state="FL",
            scope="tribe", reporting_party_name=r["party_name_as_published"],
            cedar_uid=uid.take(r["cedar_uid"], "fl_gaming_payments.csv"), attribution_basis=r["entity_match_method"],
            product_scope=product, measure=measure, evidence_class="forecast" if forecast else "direct_reported",
            value_nominal_usd=_money(r["value"]), value_as_published=r["value_as_published"],
            published_unit=r["published_unit"], period_start=r["period_start"], period_end=r["period_end"],
            period_cadence="revenue_sharing_cycle",
            fiscal_year_definition="compact revenue-sharing cycle as labelled by EDR (tribe-reported Net Win stated by the State)",
            sum_exclusion_flag=r["exclusion_flag"], sum_exclusion_reason=r["exclusion_reason"],
            source_authority=r["source_authority"], source_document=r["source_document_type"],
            source_url=r["source_url"], source_page=r["source_page"], source_quote=r["source_quote"],
            source_date=r["conference_date"], retrieved_date=r["fetched_date"]))
    return out


_LABEL_RE = re.compile(r",\s*([a-z0-9_]+)\s*=\s*[-0-9.,$ ]+$")


def obs_from_digital(rows, uid, withheld):
    out = []
    firsts = {}
    for r in sorted(rows, key=lambda x: x["revenue_id"]):
        if r["metric"] in DIGITAL_PAY_METRICS:
            continue
        absence = r["revenue_scope"] == "NO_REVENUE_OBSERVATION"
        attributable = r["is_tribe_attributable"] == "yes"
        m = _LABEL_RE.search(r["source_quote"] or "")
        key = (r["state"], r["licensee_name_as_published"], r["brand"], r["product_type"], r["metric"],
               r["period_start"], r["period_end"])
        row = _obs_row(
            source_system="digital_gaming_revenue", source_record_id=r["revenue_id"], source_metric=r["metric"],
            source_measure_label=m.group(1) if m else "", state=r["state"],
            scope="online_licensee" if not absence else "tribe",
            reporting_party_name=r["licensee_name_as_published"], brand=r["brand"],
            # commercial operators keep their rows but never an entity id
            cedar_uid=uid.take(r["cedar_uid"], "digital_gaming_revenue.csv") if (attributable or absence) else "",
            attribution_basis=r["attribution_basis"], product_scope=r["product_type"].lower(),
            measure="documented_absence" if absence else r["metric"].lower(),
            evidence_class="documented_absence" if absence else "direct_reported",
            value_nominal_usd="" if absence else _money(r["value_usd"]), value_as_published=r["value_usd"],
            published_unit="USD", period_start=r["period_start"], period_end=r["period_end"],
            period_cadence="month" if r["period_type"] == "month" else "none",
            fiscal_year_definition="calendar month" if r["period_type"] == "month" else "not applicable",
            alternate_column_of=firsts.get(key, "") if not absence else "",
            absence_reason=r["note"] if absence else "",
            source_authority=r["source_agency"], source_document=r["source_document"], source_url=r["source_url"],
            source_quote=r["source_quote"], retrieved_date=r["fetched_date"])
        if not absence:
            firsts.setdefault(key, row["reported_observation_id"])
            if row["alternate_column_of"] == row["reported_observation_id"]:
                row["alternate_column_of"] = ""
            row["summable_within_series"] = "yes" if not row["alternate_column_of"] else "no"
        out.append(row)
    return out


# ================================================================== 5. DISCLOSURES
DISCLOSURE_KINDS = {"sec_facility_financial_figure", "sec_management_contract_term", "fac_audit_narrative",
                    "fac_sefa_federal_award", "nigc_financing_document_review", "rating_agency_bond_action",
                    "sec_fund_holding", "fac_single_audit_record"}
FIN_EVIDENCE = {"direct_reported", "derived_from_stated_rate", "narrative", "execution_unconfirmed", "contract_term"}

FIN_SPEC = [
    ("financial_disclosure_id", "public_derived", "Derived GFIN id from (source table, source record key)"),
    ("source_system", "public_official", "Upstream clean table"),
    ("source_record_id", "public_official", "Upstream id, preserved (FAC narrative rows: report_id|page|document type)"),
    ("disclosure_kind", "public_official", "Kind of disclosure"),
    ("figure_type", "public_official", "Upstream figure/term/measurement type"),
    ("evidence_class", "public_official", "direct_reported, derived_from_stated_rate, narrative, execution_unconfirmed or contract_term"),
    ("amount_nominal_usd", "public_official", "Amount in NOMINAL US dollars where the disclosure states one"),
    ("amount_as_published", "public_official", "Amount text as filed/printed"),
    ("amount_concept", "public_official", "What the amount measures, in the source's terms"),
    ("is_gaming_revenue", "public_official", "yes / no / manager_revenue_not_facility_revenue / derived_not_reported"),
    ("period_label", "public_official", "Fiscal period as filed"),
    ("period_type", "public_official", "FISCAL_YEAR, QUARTER, NINE_MONTHS, AUDIT_YEAR, POINT_IN_TIME ..."),
    ("period_end", "public_official", "Period end (ISO) where given"),
    ("fiscal_year", "public_official", "Fiscal/audit year where given"),
    ("filer_or_issuer_name", "public_official", "Filer, auditee, borrower or issuer as published"),
    ("filer_role", "public_official", "Filer's role (operator instrumentality, manager, auditee, borrower ...)"),
    ("counterparty_name", "public_official", "Manager / lender / counterparty as published"),
    ("cedar_uid", "public_derived", "Canonical CE- id carried from the source row only"),
    ("gaming_facility_id", "public_derived", "Facility id via gaming_grove.facility_id_for(cedar_place_id); SEC rows only"),
    ("facility_is_on_indian_lands", "public_official", "Y/N as upstream (SEC rows)"),
    ("term_rate_pct", "public_official", "Stated fee/term percentage (contract terms)"),
    ("term_rate_base", "public_official", "Base the percentage applies to"),
    ("term_text", "public_official", "Verbatim fee formula / term / figures in the quote"),
    ("derivation_note", "public_official", "Derivation arithmetic and caveat for derived rows"),
    ("is_first_statement_of_fact", "public_official", "Y/N: first filing stating this fact (restatements are not additive)"),
    ("filing_form", "public_official", "Form (10-K, single audit, NIGC declination letter, rating action ...)"),
    ("filing_reference", "public_official", "Accession / FAC report id / NIGC opinion id"),
    ("source_authority", "public_official", "Publishing authority"),
    ("source_url", "public_official", "Source URL"),
    ("source_page", "public_official", "Page"),
    ("source_quote", "public_official", "Quoted text"),
    ("source_date", "public_official", "Filing/opinion/issue date (ISO) where given"),
    ("retrieved_date", "public_official", "Date retrieved"),
    ("rights_class", "public_official", "Row-level rights class"),
    ("publication_status", "public_official", "Row-level publication status"),
]
FIN_CONTRACT = _contract(
    FIN_SPEC,
    grain="One financial disclosure as filed or printed: one SEC figure or contract term, one FAC audit statement or federal-award line, one NIGC financing review, or one bond/rating disclosure.",
    primary_key=["financial_disclosure_id"],
    required=["source_system", "disclosure_kind", "evidence_class"],
    enums={"disclosure_kind": DISCLOSURE_KINDS, "evidence_class": FIN_EVIDENCE,
           "is_gaming_revenue": {"yes", "no", "manager_revenue_not_facility_revenue", "derived_not_reported", "unknown"},
           "publication_status": gg.PUBLICATION_STATUSES},
    dates=["period_end", "source_date", "retrieved_date"],
    public_id_columns=["gaming_facility_id"],
    derived_ids={"financial_disclosure_id": "GFIN"},
    nonadditive_note=("Disclosures are not a revenue panel. SEC facility net revenues, manager fee revenue, "
                      "relinquishment payments, FAC federal award expenditures (NOT gaming revenue) and bond par "
                      "amounts are different concepts and are never added to each other, to NIGC GGR or to "
                      "payments. Restatements (is_first_statement_of_fact=N) repeat a fact."),
    publication_status="public",
    supersedes=[{"table": "sec_gaming_financial_disclosures.csv", "role": "all rows"},
                {"table": "sec_gaming_management_contract_terms.csv", "role": "all rows as contract_term disclosures"},
                {"table": "fac_audit_gaming_disclosures.csv", "role": "all rows"},
                {"table": "fac_audit_sefa_gaming_programs.csv", "role": "all rows (federal award, not revenue)"},
                {"table": "gaming_financing_events.csv", "role": "all rows (NIGC reviewed drafts, execution unconfirmed)"},
                {"table": "tribal_bond_issuances.csv", "role": "gaming bond rows (Moody's lineage: internal_vendor)"},
                {"table": "seminole_bond_disclosures.csv", "role": "rows not already carried from tribal_bond_issuances"}],
    row_rights_column="rights_class",
)


def _fin_row(key_parts, **kw):
    row = {c: "" for c in FIN_CONTRACT["header"]}
    row.update(kw)
    row["financial_disclosure_id"] = gg.derive_id("GFIN", row["source_system"], *key_parts)
    rc = row["rights_class"] or "public_official"
    row["rights_class"] = rc
    if not row["publication_status"]:
        row["publication_status"] = ("public" if rc in gg.PUBLIC_RIGHTS
                                     else "withheld" if rc.startswith("withheld") else "internal")
    return row


SEC_REVENUE = {"FACILITY_NET_REVENUES": "yes", "FACILITY_NET_GAMING_REVENUE": "yes",
               "MANAGEMENT_FEE_REVENUE": "manager_revenue_not_facility_revenue",
               "RELINQUISHMENT_PAYMENT": "manager_revenue_not_facility_revenue",
               "DERIVED_FACILITY_GROSS_REVENUES_AS_DEFINED": "derived_not_reported",
               "DERIVED_FACILITY_NET_INCOME_AS_DEFINED": "no"}


def fin_from_sources(inputs, uid, withheld):
    out = []
    _, sec = inputs.clean("sec_gaming_financial_disclosures.csv")
    for r in sec:
        derived = r["derived_from_fee"] == "Y" or r["figure_type"].startswith("DERIVED")
        out.append(_fin_row(
            [r["disclosure_id"]], source_system="sec_gaming_financial_disclosures", source_record_id=r["disclosure_id"],
            disclosure_kind="sec_facility_financial_figure", figure_type=r["figure_type"],
            evidence_class="derived_from_stated_rate" if derived else "direct_reported",
            amount_nominal_usd=_money(r["value_usd"]), amount_as_published=r["value_verbatim"],
            amount_concept=r["figure_type_note"], is_gaming_revenue=SEC_REVENUE.get(r["figure_type"], "unknown"),
            period_label=r["fiscal_period_label"], period_type=r["period_type"], period_end=r["period_end"],
            fiscal_year=r["fiscal_year"], filer_or_issuer_name=r["filer_name"], filer_role=r["filer_role"],
            counterparty_name=r["manager_name"], cedar_uid=uid.take(r["cedar_uid"], "sec_gaming_financial_disclosures.csv"),
            gaming_facility_id=_place(r["cedar_place_id"]), facility_is_on_indian_lands=r["facility_is_on_indian_lands"],
            term_rate_pct=r["derivation_stated_percentage"], term_rate_base=r["derivation_percentage_base"],
            derivation_note=" | ".join(x for x in (r["derivation_arithmetic"], r["derivation_caveat"]) if x),
            is_first_statement_of_fact=r["is_first_filing_of_this_fact"], filing_form=r["form"],
            filing_reference=r["accession"], source_authority="U.S. Securities and Exchange Commission, EDGAR",
            source_url=r["source_url"], source_quote=r["source_quote"], source_date=r["filing_date"],
            retrieved_date="",  # upstream records no retrieval date (only its build date)
            # derived values are research arithmetic on public figures: kept internal, per the owner's rule
            rights_class="internal_model" if derived else "public_official"))
    _, terms = inputs.clean("sec_gaming_management_contract_terms.csv")
    for r in terms:
        out.append(_fin_row(
            [r["term_id"]], source_system="sec_gaming_management_contract_terms", source_record_id=r["term_id"],
            disclosure_kind="sec_management_contract_term", figure_type=r["assertion_class"], evidence_class="contract_term",
            amount_concept="no money: a contract term", is_gaming_revenue="no",
            filer_or_issuer_name=r["manager_name"], filer_role=r["manager_role"], counterparty_name=r["tribe_name"],
            cedar_uid="", gaming_facility_id=_place(r["cedar_place_id"]),
            term_rate_pct=r["fee_percentage"], term_rate_base=r["fee_percentage_base"],
            term_text=" | ".join(x for x in (r["fee_formula_verbatim"], r["contract_expiry_as_stated"]) if x),
            derivation_note=r["adjudication_note"], filing_form=r["form"], filing_reference=r["accession"],
            source_authority="U.S. Securities and Exchange Commission, EDGAR", source_url=r["source_url"],
            source_quote=r["source_quote"], source_date=r["filing_date"], retrieved_date=""))
    uid.note_legacy_column(terms, "sec_gaming_management_contract_terms.csv", "tribe_id")
    _, fac = inputs.clean("fac_audit_gaming_disclosures.csv")
    for r in fac:
        suspect = r["parse_quality"] == "SUSPECT_TABLE_FRAGMENT"
        # A blank entity link is often a NON-Native auditee (e.g. NJ Casino Reinvestment
        # Development Authority): a Native-gaming disclosure is not established, so unresolved.
        unlinked = not r["cedar_uid"]
        if unlinked:
            withheld["fac_narrative_unresolved_no_entity_link"] += 1
        out.append(_fin_row(
            [r["report_id"], r["source_page"], r["source_document_type"], r["verbatim_quote"]],
            source_system="fac_audit_gaming_disclosures",
            source_record_id=f"{r['report_id']}|p{r['source_page']}|{r['source_document_type']}",
            disclosure_kind="fac_audit_narrative", figure_type=r["measurement_type"] or r["disclosure_class"] or r["term"],
            evidence_class="narrative", amount_concept=r["measurement_type_basis"][:300],
            is_gaming_revenue="unknown", period_type="AUDIT_YEAR", fiscal_year=r["audit_year"],
            filer_or_issuer_name=r["auditee_name"], filer_role="single_audit_auditee",
            cedar_uid=uid.take(r["cedar_uid"], "fac_audit_gaming_disclosures.csv"),
            term_text=r["figures_in_quote"], derivation_note=r["scope_caution"],
            filing_form="Single Audit (2 CFR 200 Subpart F)", filing_reference=r["report_id"],
            source_authority=r["source_authority"], source_url=r["source_url"], source_page=r["source_page"],
            source_quote=r["verbatim_quote"], retrieved_date=r["retrieved_at"],
            rights_class="withheld_unverified" if (suspect or unlinked) else "public_official",
            publication_status="unresolved" if (suspect or unlinked) else ""))
    _, sefa = inputs.clean("fac_audit_sefa_gaming_programs.csv")
    for r in sefa:
        out.append(_fin_row(
            [r["report_id"], r["award_reference"]], source_system="fac_audit_sefa_gaming_programs",
            source_record_id=f"{r['report_id']}|{r['award_reference']}", disclosure_kind="fac_sefa_federal_award",
            figure_type=r["measurement_type"], evidence_class="direct_reported",
            amount_nominal_usd=_money(r["amount_expended"]), amount_as_published=r["amount_expended"],
            amount_concept="FEDERAL AWARD EXPENDITURE (SEFA amount_expended) - NOT gaming revenue: " + r["federal_program_name"],
            is_gaming_revenue="no", period_type="AUDIT_YEAR", fiscal_year=r["audit_year"],
            filer_or_issuer_name=r["auditee_name"], filer_role="single_audit_auditee",
            cedar_uid=uid.take(r["cedar_uid"], "fac_audit_sefa_gaming_programs.csv"),
            derivation_note=r["measurement_type_note"], filing_form="SEFA federal award line",
            filing_reference=r["report_id"], source_authority=r["source_authority"], source_url=r["source_url"],
            source_quote=r["verbatim_quote"], retrieved_date=r["retrieved_at"],
            # FAC marks this tribal report is_public=0 (2 CFR 200.512(b)(2)); withheld
            rights_class="public_official" if r["is_public"] == "1" else "withheld_suppressed"))
    _, fin = inputs.clean("gaming_financing_events.csv")
    for r in fin:
        out.append(_fin_row(
            [r["financing_event_id"]], source_system="gaming_financing_events", source_record_id=r["financing_event_id"],
            disclosure_kind="nigc_financing_document_review", figure_type=r["agreement_type"],
            evidence_class="execution_unconfirmed", amount_concept=r["principal_amount_basis"][:300],
            is_gaming_revenue="no", period_type="POINT_IN_TIME",
            filer_or_issuer_name=r["borrower"] or r["index_tribe_string"], filer_role="borrower_as_indexed_by_nigc",
            counterparty_name=r["lender"] or r["administrative_agent"] or r["index_company_string"],
            cedar_uid=uid.take(r["cedar_uid"], "gaming_financing_events.csv"),
            term_text=r["re_line"], derivation_note=r["evidentiary_stage_basis"][:500] + " " + r["property_attachment_caution"][:300],
            filing_form="NIGC declination letter (loan document review)", filing_reference=r["cedar_opinion_id"],
            source_authority="National Indian Gaming Commission", source_url=r["source_url"],
            source_quote=r["execution_status_basis"], source_date=r["opinion_date"], retrieved_date=r["fetched_date"]))
    withheld["financing_collateral_properties_dropped_vendor_ids"] += sum(1 for r in fin if r["collateral_properties"])
    _, bonds = inputs.clean("tribal_bond_issuances.csv", required=False)
    uid.note_legacy_column(bonds, "tribal_bond_issuances.csv", "issuer_entity_id")
    for r in bonds:
        out.append(_fin_row(
            [r["issuer"], r["instrument_type"], r["par_amount"], r["maturity"], r["source_url"]],
            source_system="tribal_bond_issuances", source_record_id="",
            disclosure_kind="rating_agency_bond_action", figure_type=r["instrument_type"], evidence_class="direct_reported",
            amount_nominal_usd=_money(r["par_amount"]), amount_as_published=r["par_amount"],
            amount_concept="par amount of a debt instrument as quoted by the rating agency (not revenue)",
            is_gaming_revenue="no", period_type="POINT_IN_TIME", period_label=f"maturity {r['maturity']}",
            filer_or_issuer_name=r["issuer"], filer_role="issuer", counterparty_name=r["rating_agency"],
            cedar_uid="",  # upstream holds only a legacy issuer_entity_id; never translated here
            term_text=" | ".join(x for x in (r["use_of_proceeds"], r["rating_at_issue"]) if x),
            derivation_note=r["date_basis"], filing_form="rating action", source_authority=r["rating_agency"],
            source_url=r["source_url"], source_quote=r["notes"], source_date=_iso(r["issue_date"]),
            retrieved_date=r["retrieved_date"], rights_class="internal_vendor"))
    _, sem = inputs.clean("seminole_bond_disclosures.csv", required=False)
    for r in sem:
        if r["availability_status"] == "carried_from_tribal_bond_issuances":
            withheld["seminole_row_duplicates_tribal_bond_issuances"] += 1
            continue
        if r["disclosure_class"] == "robots_exclusion_file" or r["source_document_type"] == "robots_exclusion_file":
            withheld["seminole_row_is_a_robots_record_not_a_disclosure"] += 1
            continue
        fac_row = r["source_document_type"] == "fac_dissemination_general_record"
        rights = ("withheld_suppressed" if r["availability_status"] == "withheld_by_rule"
                  else "public_official" if r["availability_status"] == "retrieved" else "withheld_unverified")
        out.append(_fin_row(
            [r["disclosure_id"]], source_system="seminole_bond_disclosures", source_record_id=r["disclosure_id"],
            disclosure_kind="fac_single_audit_record" if fac_row else "sec_fund_holding",
            figure_type=r["disclosure_class"], evidence_class="direct_reported",
            amount_nominal_usd=_money(r["amount_usd"]), amount_as_published=r["amount_usd"],
            amount_concept=r["amount_concept"] or r["security_description"],
            is_gaming_revenue="no", period_type="AUDIT_YEAR" if fac_row else "POINT_IN_TIME",
            period_end=r["period_end"], fiscal_year=r["fiscal_year"],
            filer_or_issuer_name=r["obligor_name_as_published"], filer_role="obligor",
            counterparty_name=r["filer_name"], cedar_uid=uid.take(r["cedar_uid"], "seminole_bond_disclosures.csv"),
            term_text=" | ".join(x for x in (r["security_description"], r["coupon_pct"], r["maturity_date"]) if x),
            derivation_note=r["availability_basis"][:400], filing_form=r["filing_form"],
            source_authority=r["source_authority"], source_url=r["source_url"], source_quote=r["source_quote"],
            source_date=r["filing_date"], retrieved_date=r["fetched_date"], rights_class=rights))
    for name, col in (("fac_audit_gaming_disclosures.csv", "entity_id"), ("fac_audit_sefa_gaming_programs.csv", "entity_id"),
                      ("gaming_financing_events.csv", "tribe_entity_id"), ("sec_gaming_financial_disclosures.csv", "tribe_id"),
                      ("seminole_bond_disclosures.csv", "tribe_id")):
        _, rows = inputs.clean(name, required=False)
        uid.note_legacy_column(rows, name, col)
    return out


# ================================================================== orchestration
CONTRACTS = {T_REGION: REGION_CONTRACT, T_BANDS: BAND_CONTRACT, T_PAY: PAY_CONTRACT,
             T_OBS: OBS_CONTRACT, T_FIN: FIN_CONTRACT, **gos.CONTRACTS}
for _t, _c in CONTRACTS.items():
    missing = [c for c in _c["header"] if c not in _c["field_rights"] or c not in _c["field_descriptions"]]
    assert not missing, (_t, missing)


def check_payments(rows):
    """Brief-required invariants, refused rather than warned."""
    bad = [r["source_record_id"] for r in rows
           if r["payment_status"] == "paid" and (r["is_forecast"] == "yes")]
    bad += [r["source_record_id"] for r in rows
            if r["payment_status"] in ("forecast", "obligation_stated", "suppressed", "empty_cell")
            and r["summable_within_series"] == "yes"]
    bad += [r["source_record_id"] for r in rows
            if r["period_cadence"] in NON_SUMMABLE_CADENCES and r["summable_within_series"] == "yes"]
    if bad:
        raise gg.GamingContractError(f"REFUSED: payment status/summability violations e.g. {bad[:5]}")


def check_regions_have_no_entity_ids(header):
    leaked = [c for c in header if c in FORBIDDEN_REGION_COLUMNS]
    if leaked:
        raise gg.GamingContractError(f"REFUSED: entity/facility columns in regional table: {leaked}")


def _coverage(rows, date_cols):
    by_year = Counter()
    for r in rows:
        y = ""
        for c in date_cols:
            y = _year(r.get(c, ""))
            if y:
                break
        by_year[y or "undated"] += 1
    return dict(sorted(by_year.items()))


def nigc_gaps(regions, missing_national):
    """NIGC coverage gaps as gaming_coverage_gaps rows (never computed values)."""
    out = []
    for fy in missing_national:
        docs = sorted({r["source_document"] for r in regions if r["fiscal_year"] == fy})
        out.append(dict(gap_source="nigc_regional_revenue", component_table=T_REGION, state="", cedar_uid="",
                        entity_name_in_source="", subject=f"NIGC printed national gross gaming revenue total FY{fy}",
                        measure="nigc_gross_gaming_revenue (national)", expected_frequency="fiscal_year",
                        known_start=fy, known_end=fy, missing_from=fy, missing_through=fy,
                        missing_periods=f"FY{fy} national total",
                        source_status="national_total_not_printed",
                        reason=(f"FY{fy} regions are carried only from {', '.join(docs)} (figure_vintage "
                                "prior_year_column), which prints no FY national total; Cedar never computes one "
                                "from regions"),
                        next_action="Locate an NIGC publication printing the FY national total (press release or FY report)",
                        evidence_url="https://www.nigc.gov/downloads/gross-gaming-revenue-reports/",
                        affected_record_id=""))
    latest = max(int(r["fiscal_year"]) for r in regions)
    latest_doc = [r for r in regions if r["fiscal_year"] == str(latest) and r["preferred_figure_for_fy"] == "yes"]
    out.append(dict(gap_source="nigc_regional_revenue", component_table=T_REGION, state="", cedar_uid="",
                    entity_name_in_source="", subject=f"NIGC gross gaming revenue FY{latest + 1}",
                    measure="nigc_gross_gaming_revenue (regions and national)", expected_frequency="fiscal_year",
                    known_start="", known_end="", missing_from=str(latest + 1), missing_through=str(latest + 1),
                    missing_periods=f"FY{latest + 1} (all regions and national)",
                    source_status="not_yet_published",
                    reason=(f"latest NIGC report held is FY{latest} ({latest_doc[0]['source_document'] if latest_doc else ''}, "
                            f"retrieved {latest_doc[0]['retrieved_date'] if latest_doc else ''}); NIGC publishes about "
                            "16 months after the fiscal year"),
                    next_action="Re-check the NIGC GGR archive after the next annual release",
                    evidence_url="https://www.nigc.gov/downloads/gross-gaming-revenue-reports/",
                    affected_record_id=""))
    return out


def build(inputs: gg.Inputs, out_dir: Path, online_sports_root=None) -> dict:
    notes, withheld = [], Counter()
    uid = UidGate()
    tables = []

    regions = build_regional(inputs, notes)
    check_regions_have_no_entity_ids(REGION_CONTRACT["header"])
    bands = build_bands(inputs)
    check_bands_against_regions(bands, regions)

    _, ca = inputs.clean("ca_gaming_payments.csv")
    _, fl = inputs.clean("fl_gaming_payments.csv")
    _, st = inputs.clean("state_gaming_observations.csv")
    _, dg = inputs.clean("digital_gaming_revenue.csv")
    for name, rows, col in (("ca_gaming_payments.csv", ca, "tribe_id"), ("fl_gaming_payments.csv", fl, "tribe_id"),
                            ("state_gaming_observations.csv", st, "tribe_id"), ("digital_gaming_revenue.csv", dg, "tribe_id"),
                            ("digital_gaming_revenue.csv", dg, "entity_id")):
        uid.note_legacy_column(rows, name, col)
    pays = (payments_from_ca(ca, uid, withheld) + payments_from_fl(fl, uid, withheld)
            + payments_from_state(st, uid, withheld) + payments_from_digital(dg, uid, withheld))
    check_payments(pays)
    obs = obs_from_state(st, uid, withheld) + obs_from_fl(fl, uid, withheld) + obs_from_digital(dg, uid, withheld)
    fins = fin_from_sources(inputs, uid, withheld)

    # Online sports package (imported module; never appended to regional revenue).
    missing_national = check_one_preferred_national(regions)
    os_tables, os_cov, os_withheld, os_notes, dg_overlap = gos.build_component(
        inputs, online_sports_root or gos.DEFAULT_PACKAGE_ROOT, dg, nigc_gaps(regions, missing_national))
    withheld.update(os_withheld)
    notes += os_notes
    for r in obs + pays:
        r["overlaps_online_sportsbook_observation_id"] = (
            dg_overlap.get(r["source_record_id"], "") if r["source_system"] == "digital_gaming_revenue" else "")

    # Internal-only QA tables: read for a hash receipt, never emitted (see module docstring).
    _, bounds = inputs.clean("gaming_revenue_bounds.csv", required=False)
    withheld["gaming_revenue_bounds_not_emitted_internal_ceiling_repeats"] = len(bounds)
    notes.append("gaming_revenue_bounds and votingpatterns modeled property revenue are NOT emitted: bounds repeat "
                 "regional ceilings across facilities (never summable) and votingpatterns values are compact-rate/GDP "
                 "models; both stay internal QA outside the component tables.")

    emitted = [(T_REGION, regions, REGION_CONTRACT), (T_BANDS, bands, BAND_CONTRACT),
               (T_PAY, pays, PAY_CONTRACT), (T_OBS, obs, OBS_CONTRACT), (T_FIN, fins, FIN_CONTRACT)]
    emitted += [(t, os_tables[t], gos.CONTRACTS[t]) for t in (T_OS_UNITS, T_OS_FOB, T_OS_REL, T_GAPS)]
    for table, rows, contract in emitted:
        tables.append(gg.write_table(out_dir, table, contract["header"], rows, contract))

    pub = {}
    for table, rows, contract in emitted:
        keep, prow = gg.public_projection(table, contract["header"], rows, contract["field_rights"])
        pub[table] = {"public_fields": len(keep), "withheld_fields": len(contract["header"]) - len(keep),
                      "public_rows": len(prow), "rows": len(rows),
                      "rows_by_publication_status": dict(sorted(Counter(r.get("publication_status", "public") for r in rows).items()))}

    cov = {
        T_REGION: {"fiscal_years": _coverage(regions, ["fiscal_year"]),
                   "national_rows": sum(r["geography_level"] == "national" for r in regions),
                   "latest_fiscal_year": max(int(r["fiscal_year"]) for r in regions),
                   "fiscal_years_without_printed_national_total": missing_national,
                   "fiscal_years_with_two_printed_national_totals": sorted(
                       fy for fy, n in Counter(r["fiscal_year"] for r in regions
                                               if r["geography_level"] == "national").items() if n > 1),
                   "preferred_figure_rule": VINTAGE_RULE,
                   "fy2026": "not published: NIGC archive lists FY25 (released July 2026) as latest on 2026-09-24"},
        T_BANDS: {"fiscal_years": _coverage(bands, ["fiscal_year"])},
        T_PAY: {"period_end_years": _coverage(pays, ["period_end", "period_start"]),
                "by_source": dict(sorted(Counter(r["source_system"] for r in pays).items())),
                "by_status": dict(sorted(Counter(r["payment_status"] for r in pays).items())),
                "by_direction": dict(sorted(Counter(r["direction"] for r in pays).items())),
                "with_cedar_uid": sum(1 for r in pays if r["party_cedar_uid"]),
                "distinct_cedar_uid": len({r["party_cedar_uid"] for r in pays if r["party_cedar_uid"]}),
                "overlapping_online_sportsbook_rows": sum(1 for r in pays if r["overlaps_online_sportsbook_observation_id"])},
        T_OBS: {"period_end_years": _coverage(obs, ["period_end", "period_start"]),
                "by_scope": dict(sorted(Counter(r["scope"] for r in obs).items())),
                "by_evidence": dict(sorted(Counter(r["evidence_class"] for r in obs).items())),
                "with_cedar_uid": sum(1 for r in obs if r["cedar_uid"]),
                "alternate_columns": sum(1 for r in obs if r["alternate_column_of"]),
                "overlapping_online_sportsbook_rows": sum(1 for r in obs if r["overlaps_online_sportsbook_observation_id"])},
        T_FIN: {"years": _coverage(fins, ["period_end", "fiscal_year", "source_date"]),
                "by_kind": dict(sorted(Counter(r["disclosure_kind"] for r in fins).items())),
                "with_facility_id": sum(1 for r in fins if r["gaming_facility_id"])},
        T_OS_FOB: os_cov,
        T_GAPS: {"rows": len(os_tables[T_GAPS]),
                 "by_gap_source": dict(sorted(Counter(r["gap_source"] for r in os_tables[T_GAPS]).items()))},
    }
    legacy = {f"{t}:{c}": n for (t, c), n in sorted(uid.legacy.items())}
    return {"tables": tables, "inputs": dict(sorted(inputs.receipts.items())), "coverage": cov,
            "withheld": dict(sorted(withheld.items())), "publication": pub,
            "legacy_entity_ids_dropped": legacy, "id_contract_status": gg.ID_CONTRACT_STATUS,
            "notes": notes}


def _strip_contract(c):
    return {k: (sorted(v) if isinstance(v, set) else
                {kk: sorted(vv) if isinstance(vv, set) else vv for kk, vv in v.items()} if isinstance(v, dict) else v)
            for k, v in c.items()}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--input-root", default=str(gg.DEFAULT_INPUT_ROOT))
    b.add_argument("--output-root", required=True)
    b.add_argument("--as-of", default="")
    b.add_argument("--online-sports-root", default=str(gos.DEFAULT_PACKAGE_ROOT),
                   help="unpacked online sports package (tribal_sports/); env CEDAR_GAMING_ONLINE_SPORTS_ROOT")
    a = ap.parse_args(argv)
    inputs = gg.Inputs(a.input_root)
    out = Path(a.output_root)
    receipt = build(inputs, out, Path(a.online_sports_root))
    receipt["script"] = f"code/{SCRIPT}.py"
    receipt["schema_version"] = gg.SCHEMA_VERSION
    receipt["as_of"] = a.as_of
    receipt["contracts"] = {t: _strip_contract(c) for t, c in CONTRACTS.items()}
    data = json.dumps(receipt, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    (out / f"{SCRIPT}.receipt.json").write_bytes(data)
    for t in receipt["tables"]:
        print(f"  {t['table']:45s} {t['rows']:>7,} rows  {t['sha256'][:12]}")
    print(f"  withheld: {receipt['withheld']}")
    print(f"  legacy entity ids dropped: {receipt['legacy_entity_ids_dropped']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
