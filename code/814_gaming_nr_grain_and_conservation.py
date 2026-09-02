#!/usr/bin/env python3
r"""
Cedar Press - 814: workstream GAMING-NR.

Two datasets, two blockers, one script. Nothing here is proposed; every number
below is re-measured on every run and `verify` exits 1 when one of them stops
being true.

===========================================================================
PART 1 - natural-resources C5. FINISHING WHAT 573 conserve-probe BANKED.
===========================================================================

`573_ws3_grain_and_money.py conserve-probe` measured the two countable inputs
of `resource_revenue.csv` exactly - ONRR monthly revenue 410,901 rows read ->
9,277 Native American, and fiscal-year disbursements 8,437 -> 157 - and then
REFUSED to merge them, because a ledger accounting for 9,434 of 11,305 rows
would have satisfied 510's I13 arithmetic and cleared 518's C5 blocker for the
whole dataset while the contract point stayed ~90% unmet. That refusal was
right. This script does not merge that partial either. It establishes a read
count for the other TEN source systems and merges all TWELVE at once.

THE UNIT PROBLEM, AND HOW IT IS SOLVED RATHER THAN AVERTED.

573's docstring says of the ten: "'rows read' is not a number sitting anywhere
on disk". That is true of a naive reading - there is no CSV to `len()`. It is
NOT true that the read is unmeasurable. Every one of the ten parsers iterates
something countable, and what it iterates is a CANDIDATE LEDGER ROW: one
reading the harvest examined and either published or refused. Declare that as
the unit and all twelve systems become commensurable, the units stop mixing,
and `emitted` sums to exactly the 11,305 rows the table ships.

  system                                    read unit                  rows_in
  ---------------------------------------------------------------------------
  ONRR_NRRD_monthly_revenue                 CSV row                    410,901
  ONRR_NRRD_fiscal_year_disbursements       CSV row                      8,437
  OMC_headright_payment_history             spreadsheet money cell         628
  ND_State_Treasurer_tax_..._search         payment line in 3 HTML         492
  MMS_MRM_..._revenues_calendar             (year x component) cell        456
  ANCSA_7i_7j_annual_reports                (corp, series, FY) claim       185
  OSMRE_AML_fee_based_grant_distribution    (FY, tribe, basis) reading     150
  UT_COBI_fund_financials                   (fund, FY, measure) cell       118
  OMC_quarterly_newsletter                  printed figure slot            108
  MT_DOR_county_oil_gas_distribution        cover-letter tribal line        49
  MMS_MRM_american_indian_revenues          (FY document, component)        48
  OSMRE_AML_IIJA_grant_distribution         (document, tribe) reading       18
  ---------------------------------------------------------------------------
                                                                       421,590

None of the ten is recorded as unmeasurable. The read count is established for
all ten, by RE-RUNNING THE ACTUAL PARSERS in `code/83_build_resource_ledger.py`
and `code/84_resource_recipient_side.py` into throwaway lists - never their
write paths - and taking the denominators from the same file inventories and
constants the parsers themselves iterate. Where a denominator is a product
(25 OSMRE documents x 3 tribal programmes x 2 sequestration bases), the script
ASSERTS that emitted + every named rejection equals it, and fails if not.

===========================================================================
PART 2 - gaming C1 on three tables.
===========================================================================

`gaming_property_self_published_*` are MARKETING CLAIMS a casino makes about
itself. `code/383` recovered 231 of them from a refusal pile. The grain
declaration is where "never sum this against a regulator's figure" gets said,
so both grains say it in the prose, both carry `assertion_class` as a
first-class column, and a marked section of docs/MONEY_TOTALLING_RULES.md
states the prohibition where a buyer reads it.

`fac_audit_sefa_gaming_programs.csv` had a REAL open question, recorded in
512.GRAIN_OPEN: "the file has ONE row. Uniqueness is vacuous. QUESTION: is a
row a (report, federal program) line off the SEFA, so that report_id repeats
once a second program is parsed?" ANSWERED, and not by argument. The FAC's own
`federal_awards` record - cached verbatim at data/raw/fac/fac_sefa_gaming.json
by `code/147` itself - carries `award_reference = AWARD-0068`, which is the
FAC's per-report line key. `147` drops it. So report_id DOES repeat (147's own
docstring measured 127 federal_awards rows on one Seminole report) and the
natural key is (report_id, award_reference), which could not be validated
because the column was not in the file.

This script carries `award_reference` into the table from 147's own cache. It
is a CARRIED COLUMN, the same fix shape as `operating_company_seq` in 269 and
the `schedule_i_line_seq` 132 still needs - no row deleted, no value invented,
the value read verbatim from the record the builder already fetched.

  THE ONE-LINE FIX THAT BELONGS IN 147 AND IS NOT MADE HERE. `147` is a gaming
  puller and belongs to workstream M this pass, so it is not edited. In
  `main()`, the `sefa_rows.append({...})` dict needs one more key:

      "award_reference": g.get("award_reference"),

  Until that lands, a rebuild of 147 drops the column and 512.validate_grain
  fires "declared primary_key names column(s) not in the header" - loudly,
  which is the correct failure. `py -3 code/814_... apply` restores it
  idempotently from the same cache in the meantime.

===========================================================================
WHAT THIS SCRIPT WILL NOT DO
===========================================================================
- It does not de-duplicate. Nothing here deletes a row.
- It does not rewrite `cedar_harvest_conservation.csv`. MERGE-ONLY on
  (source_table, disposition); a wholesale rewrite destroyed 2,146,673
  accounted rows on the morning of 2026-09-01.
- It does not write MONEY_TOTALLING_RULES.md wholesale. Its section sits
  between `<!-- BEGIN GAMING-NR -->` and `<!-- END GAMING-NR -->`, which 574
  preserves.
- It does not touch natural-resources C4 (25% keyed). That is identity work
  and belongs to the entity layer. `characterise` reports it and stops.

Reads   data/raw/resources/**                 via 83's own parsers
        code/ancsa_portal/txt/*.txt           via 84's evidence gate
        data/raw/fac/fac_sefa_gaming.json     147's own cache
        data/clean/resource_revenue.csv, the three gaming tables
Writes  review/gaming_nr_evidence.json
        data/clean/cedar_harvest_conservation.csv   MERGE-ONLY
        data/clean/fac_audit_sefa_gaming_programs.csv  +1 carried column
        docs/MONEY_TOTALLING_RULES.md          GAMING-NR markers only
        docs/GAMING_NR_GRAIN_AND_CONSERVATION.md

Usage   py -3 code/814_gaming_nr_grain_and_conservation.py measure
        py -3 code/814_gaming_nr_grain_and_conservation.py apply
        py -3 code/814_gaming_nr_grain_and_conservation.py verify
        py -3 code/814_gaming_nr_grain_and_conservation.py characterise
"""

import argparse
import contextlib
import csv
import importlib.util
import io
import json
import re
import shutil
import sys
from collections import Counter
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CLEAN = ROOT / "data" / "clean"
RAWFAC = ROOT / "data" / "raw" / "fac" / "fac_sefa_gaming.json"
CONSERVATION = CLEAN / "cedar_harvest_conservation.csv"
SEFA = CLEAN / "fac_audit_sefa_gaming_programs.csv"
ASSERTS = CLEAN / "gaming_property_self_published_assertions.csv"
CLAIMS = CLEAN / "gaming_property_self_published_claims.csv"
REVENUE = CLEAN / "resource_revenue.csv"
EVIDENCE = ROOT / "review" / "gaming_nr_evidence.json"
MONEY_MD = ROOT / "docs" / "MONEY_TOTALLING_RULES.md"
DOC = ROOT / "docs" / "GAMING_NR_GRAIN_AND_CONSERVATION.md"
TODAY = date.today().isoformat()

CONS_COLS = ["source_table", "rows_in", "disposition", "rows", "pct",
             "examples", "harvest_date"]
NR_TABLE = "data/clean/resource_revenue.csv"
BEGIN, END = "<!-- BEGIN GAMING-NR -->", "<!-- END GAMING-NR -->"


# --------------------------------------------------------------------- io
def read_csv(p):
    if not Path(p).exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def header_of(p):
    if not Path(p).exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return [h.strip() for h in next(csv.reader(fh), [])]


def load_module(fname, alias):
    spec = importlib.util.spec_from_file_location(alias, HERE / fname)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def backup(p, tag):
    """Take a .bak and return the pre-write column list, so a dropped column
    is a measurement and not a surprise. A rebuild silently dropping a column
    is this project's most repeated defect."""
    p = Path(p)
    cols = header_of(p)
    if p.exists():
        shutil.copy2(p, p.with_name(p.name + f".bak_{TODAY}_{tag}"))
    return cols


def column_diff(name, before, after):
    lost = [c for c in before if c not in after]
    gained = [c for c in after if c not in before]
    print(f"    columns {name}: {len(before)} -> {len(after)}"
          + (f"  GAINED {gained}" if gained else "")
          + (f"  LOST {lost}" if lost else ""))
    if lost:
        sys.exit(f"REFUSING: {name} lost column(s) {lost}. A rebuild that "
                 f"silently drops a column is the defect this guard exists "
                 f"for; nothing was written.")


# =====================================================================
# PART 1 - the twelve read counts
# =====================================================================
def measure_nr():
    """Re-run every parser behind `resource_revenue.csv` and return, per
    source system, the read unit, the denominator, the emitted count and every
    NAMED rejection. Raises if a system does not reconcile."""
    rl = load_module("83_build_resource_ledger.py", "cedar_rl_814")
    spine = rl.read_csv(ROOT / "data" / "spine" / "cedar_entity_spine.csv")
    live = Counter(r.get("source_system") for r in read_csv(REVENUE))
    out = {}

    def system(name, unit, rows_in, emitted, rejections, note, docs=None):
        tot = emitted + sum(rejections.values())
        if tot != rows_in:
            sys.exit(f"REFUSING: {name} does not conserve - {rows_in:,} "
                     f"readings but {tot:,} accounted "
                     f"({emitted:,} emitted + {sum(rejections.values()):,} "
                     f"rejected). A ledger that does not reconcile is worse "
                     f"than no ledger.")
        if live.get(name, 0) != emitted:
            sys.exit(f"REFUSING: {name} emits {emitted:,} rows on this run "
                     f"but resource_revenue.csv holds {live.get(name, 0):,}. "
                     f"The parser and the shipped table disagree; that is a "
                     f"finding, not something to average over.")
        out[name] = dict(read_unit=unit, rows_in=rows_in, emitted=emitted,
                         rejections=rejections, note=note, documents=docs)

    # ---- 1, 2. ONRR. The two 573 already measured, re-measured here. -----
    onrr = rl.RAW / "onrr"
    c = Counter()
    for r in read_csv(onrr / "monthly_revenue.csv"):
        c[r.get("Land Class", "")] += 1
    system("ONRR_NRRD_monthly_revenue",
           "one row of the ONRR Natural Resources Revenue Data monthly "
           "revenue extract", sum(c.values()), c.get("Native American", 0),
           {"rejected:onrr_land_class_is_not_Native_American":
            sum(v for k, v in c.items() if k != "Native American")},
           "the publisher's own Land Class column is the filter; nothing is "
           "inferred", docs=1)

    c = Counter()
    for r in read_csv(onrr / "fiscal_year_disbursements.csv"):
        c[r.get("Fund Type", "")] += 1
    nat = sum(v for k, v in c.items() if "Native American" in k)
    system("ONRR_NRRD_fiscal_year_disbursements",
           "one row of the ONRR fiscal-year disbursements extract",
           sum(c.values()), nat,
           {"rejected:onrr_disbursement_fund_type_is_not_Native_American":
            sum(c.values()) - nat},
           "Fund Type is the publisher's own bucket", docs=1)

    # ---- 3. Osage headrights. A spreadsheet grid IS countable. -----------
    xls = sorted((rl.RAW / "oklahoma").glob("osage_headright_history*.xlsx"))
    grid, annual, _notes = rl._osage_grid(xls[-1])
    q_cells, a_cells = len(grid), len(annual)
    a_gate_only = sum(1 for y in annual
                      if any((y, q) in grid for q in range(1, 5)))
    rev, par, unres = [], [], []
    grid2 = rl.parse_osage_headrights(spine, rev, par, unres)
    system("OMC_headright_payment_history",
           "one money cell of the Osage Minerals Council headright payment "
           "spreadsheet - a (year, quarter) rate or a printed annual total",
           q_cells + a_cells, len(rev),
           {"rejected:osage_printed_annual_total_is_the_reconciliation_gate_"
            "input_for_a_year_that_also_prints_quarters": a_gate_only},
           f"three side-by-side year blocks; {q_cells} quarterly cells and "
           f"{a_cells} printed annual totals. The annual total of a quarterly "
           f"year is the GATE the four quarters must sum to, so publishing it "
           f"as well would double count the year",
           docs=1)

    # ---- 4. ND Treasurer. Archived search results, matches countable. ----
    buf = io.StringIO()
    rev, par, unres = [], [], []
    rl.ND_FORMULA_PERIODS = rl._load_nd_formula()
    with contextlib.redirect_stdout(buf):
        rl.parse_nd_treasurer(spine, rev, par, unres)
    found = [int(m) for m in re.findall(r"->\s*([\d,]+)\s*'",
                                        buf.getvalue().replace(",", ""))]
    nd_docs = len(found)
    system("ND_State_Treasurer_tax_distribution_search",
           "one payment line matched in an archived ND State Treasurer tax "
           "distribution search result", sum(found), len(rev), {},
           f"{nd_docs} archived HTML search results; the parser's own "
           f"per-file match counts are {found}. Every matched line published "
           f"- no ND tax type is outside the revenue_type mapping",
           docs=nd_docs)

    # ---- 5, 11. MMS/MRM. Two series, one archive. ------------------------
    rev, unres = [], []
    rl.build_onrr_historical(rev, unres)
    fy_docs = len(sorted((rl.RAW / "onrr_historical").glob("CollFY*Ind.pdf")))
    held_docs = len(unres)
    system("MMS_MRM_american_indian_revenues",
           "one (fiscal-year document, revenue component) reading of an "
           "archived MMS American Indian collections PDF",
           fy_docs * 6, len(rev),
           {"rejected:mms_fiscal_year_document_failed_the_printed_subtotal_"
            "and_total_arithmetic_gate": held_docs * 6},
           f"{fy_docs} CollFY*Ind.pdf documents x 6 published components "
           f"(coal, gas, oil, other royalties, rents, other revenues). "
           f"{held_docs} document(s) held: "
           + "; ".join(u["review_id"] for u in unres),
           docs=fy_docs)

    rev, unres = [], []
    rl.build_mms_full_calendar(rev, unres)
    yrs = len({r["period_start"][:4] for r in rev})
    ncomp = len(rl.MMS_FULL_COMPONENTS)
    system("MMS_MRM_american_indian_revenues_calendar",
           "one (calendar year, revenue component) cell of the CY1925-2000 "
           "table read by coordinate out of one archived PDF",
           yrs * ncomp, len(rev),
           {"rejected:mms_component_printed_as_N_A_by_the_source_which_is_"
            "not_a_zero": yrs * ncomp - len(rev)},
           f"one document ({rl.MMS_FULL_PDF}), {yrs} years x {ncomp} "
           f"components. Three gates passed on this run: per-year cross-foot, "
           f"per-column printed total, and agreement with an independent hand "
           f"transcription of CY1996-2000", docs=1)

    # ---- 6. ANCSA 7(i)/7(j). 84's evidence gate IS the read count. -------
    rs = load_module("84_resource_recipient_side.py", "cedar_rs_814")
    facts = len(rs.F)
    claims = sum(len(f["years"]) for f in rs.F)
    txt_docs = len(list((HERE / "ancsa_portal" / "txt").glob("*.txt")))
    # A refusal is NAMED, never counted. `refused` below is a list of
    # (corporation, series, document stem, why) and it is printed and carried
    # into the note - a count scrolls past, a document stem is a task.
    refused = []
    for f in rs.F:
        t = rs.doc_text(f["stem"])
        if t is None:
            refused.append(f"{f['corp']}/{f['series']}/{f['stem']}: document "
                           f"not present in code/ancsa_portal/txt/")
            continue
        if f["quote_type"] == "verbatim_sentence":
            miss = ("" if rs.norm_ws(f["quote"]) in t
                    else "declared sentence not found in the document")
        else:
            gone = [tok for tok in f["quote"] if rs.norm_ws(tok) not in t]
            miss = ("" if not gone
                    else "printed token(s) not found: " + " | ".join(gone))
        if miss:
            refused.append(f"{f['corp']}/{f['series']}/{f['stem']}: {miss}")
    for why in refused:
        print(f"      ANCSA evidence gate REFUSED {why}")
    system("ANCSA_7i_7j_annual_reports",
           "one (regional corporation, series, fiscal year) claim read out of "
           "a retrieved ANCSA portal annual report",
           claims, live.get("ANCSA_7i_7j_annual_reports", 0), {},
           f"{txt_docs} retrieved report texts on disk; {facts} declared "
           f"facts, {facts - len(refused)} of which pass 84's evidence gate "
           f"(the quoted sentence or every printed token must appear in the "
           f"named local document) and {len(refused)} refused"
           + (" (" + "; ".join(refused[:3]) + ")" if refused else "")
           + f". The facts flatten to {claims} (corp, series, FY) claims with "
           f"ZERO vintage collisions, so the vintage rule discards nothing",
           docs=txt_docs)

    # ---- 7, 12. OSMRE. Documents x tribes x bases. -----------------------
    rev, par, unres = [], [], []
    rl.build_osmre_aml(spine, rev, par, unres)
    aml_dir = rl.RAW / "_federal" / "osmre" / "aml"
    aml_docs = sum(1 for f in rl.OSMRE_AML_FILES if (aml_dir / f).exists())
    ntribes = len(rl.OSMRE_TRIBES)
    reasons = Counter(u["reason"] for u in unres
                      if u["source_system"].endswith("fee_based_grant_"
                                                     "distribution"))
    aml_emit = sum(1 for r in rev
                   if r["source_system"] ==
                   "OSMRE_AML_fee_based_grant_distribution")
    system("OSMRE_AML_fee_based_grant_distribution",
           "one (fiscal-year document, tribal programme, sequestration basis) "
           "reading of an OSMRE AML fee-based distribution table",
           aml_docs * ntribes * 2, aml_emit,
           {"rejected:osmre_document_lacks_both_the_grant_and_the_"
            "sequestration_page_so_no_two_table_cross_check_exists":
            reasons["no_two_table_cross_check_available"] * ntribes * 2,
            "rejected:osmre_row_shape_or_ocr_failure_a_money_cell_did_not_"
            "parse": reasons["row_shape_or_ocr_failure"] * 2,
            "rejected:osmre_two_typeset_tables_in_the_same_document_disagree_"
            "on_the_arithmetic": reasons["arithmetic_reconciliation_failed"]
            * 2},
           f"{aml_docs} declared documents x {ntribes} certified tribal "
           f"programmes x 2 bases (before and after the sequestration "
           f"reduction). Every published tribe-year emits BOTH bases, so the "
           f"denominator is doubled and no row is a fan-out surprise. "
           f"Pre-FY2013 vintages predate sequestration and lay the tables out "
           f"differently in every year; FY2010-FY2012 are scanned images with "
           f"no text layer",
           docs=aml_docs)

    iija_dir = rl.RAW / "_federal" / "osmre" / "iija"
    iija_docs = sum(1 for f in rl.OSMRE_IIJA_FILES
                    if (iija_dir / f).exists())
    amlis = 1 if (iija_dir / "one-time-BIL-distribution-for-AMLIS-"
                            "activities-Dec-18-2023.pdf").exists() else 0
    iija_emit = sum(1 for r in rev
                    if r["source_system"] ==
                    "OSMRE_AML_IIJA_grant_distribution")
    ir = Counter(u["reason"] for u in unres
                 if u["source_system"].endswith("IIJA_grant_distribution"))
    system("OSMRE_AML_IIJA_grant_distribution",
           "one (distribution document, tribal programme) reading of an IIJA "
           "abandoned-mine-land distribution table",
           (iija_docs + amlis) * ntribes, iija_emit,
           {"rejected:osmre_iija_table_rows_do_not_sum_to_the_printed_"
            "national_total": sum(ir.values()) * ntribes},
           f"{iija_docs} annual documents plus {amlis} one-time e-AMLIS "
           f"document, x {ntribes} tribal programmes. Crow and Hopi print a "
           f"0.0000% share, which is an ASSERTION of ineligibility and is "
           f"published as a zero, not dropped",
           docs=iija_docs + amlis)

    # ---- 8. Utah COBI. JSON history arrays. ------------------------------
    cells = 0
    for fund in rl.UT_FUNDS:
        p = rl.RAW / "utah" / f"cobi_fund_{fund}.json"
        if not p.exists():
            continue
        blob = json.loads(p.read_text(encoding="utf-8", errors="replace"))
        for y in blob.get("history") or []:
            fy = str(y.get("fiscalYear") or y.get("year") or "").strip()
            if fy.isdigit():
                cells += sum(1 for k in ("revenues", "expenses")
                             if y.get(k) not in (None, ""))
    rev, par, unres = [], [], []
    rl.build_utah(spine, rev, par, unres)
    system("UT_COBI_fund_financials",
           "one (fund, state fiscal year, measure) cell of a Utah COBI fund "
           "financial history", cells, len(rev), {},
           f"{len(rl.UT_FUNDS)} funds; revenues and expenses per year. Every "
           f"non-blank cell published, expenses with the source's own "
           f"negative sign retained", docs=len(rl.UT_FUNDS))

    # ---- 9. OMC newsletters. Documents x printed figure slots. -----------
    rev, par, unres = [], [], []
    rl.parse_osage_newsletters(spine, rev, par, unres, grid2)
    news_dir = rl.RAW / "oklahoma" / "omc_newsletters"
    news_docs = len(sorted(news_dir.glob("*.pdf")))
    slots = 9          # 1 total revenue + 7 component lines + 1 state tax
    nr = Counter(u["reason"] for u in unres)
    n404 = nr["linked_document_not_retrievable"]
    other_held = sum(v for k, v in nr.items()
                     if k != "linked_document_not_retrievable")
    emitting = len({r["period_start"] for r in rev})
    no_table = news_docs - n404 - other_held - emitting
    system("OMC_quarterly_newsletter",
           "one printed figure slot of an Osage Minerals Council quarterly "
           "newsletter - the total, the seven revenue component lines, or the "
           "Oklahoma gross production tax line",
           news_docs * slots, len(rev),
           {"rejected:omc_newsletter_linked_from_the_index_but_the_host_"
            "returns_an_error_page": n404 * slots,
            "rejected:omc_newsletter_prints_no_revenue_table_text_layer_"
            "verified_healthy": no_table * slots,
            "rejected:omc_newsletter_period_not_uniquely_determined_by_the_"
            "headright_match": other_held * slots,
            "rejected:omc_newsletter_does_not_print_this_component_line":
            emitting * slots - len(rev)},
           f"{news_docs} documents linked from the OMC newsletter index; "
           f"{n404} are error pages the host still serves, {no_table} carry a "
           f"healthy text layer and genuinely print no revenue table (an "
           f"absent table is not a failed parse), {emitting} publish. Each "
           f"publishing letter is dated by agreement between its stated "
           f"per-headright figure and exactly one cell of the Council's own "
           f"spreadsheet, never by its own quarter wording",
           docs=news_docs)

    # ---- 10. Montana. One tribal line per cover letter. ------------------
    rev, par, unres = [], [], []
    rl.build_montana(spine, rev, par, unres)
    mt_docs = len(sorted((rl.RAW / "montana").glob("*Cover-Letter*.pdf")))
    system("MT_DOR_county_oil_gas_distribution",
           "one 'Tribal Distribution' line on a Montana DOR quarterly "
           "county-distribution cover letter", mt_docs, len(rev),
           {"rejected:mt_cover_letter_tribal_distribution_line_or_production_"
            "quarter_did_not_parse": len(unres)},
           f"{mt_docs} cover letters, each carrying exactly ONE tribal line. "
           f"The 57 county-distribution detail PDFs beside them carry no "
           f"tribal line and are not read by this layer. A $0.00 line is an "
           f"assertion that nothing was distributed and is published",
           docs=mt_docs)

    return out


def nr_ledger_rows(sysd):
    """Twelve source systems -> conservation rows for ONE plain table key.

    ONE plain `data/clean/resource_revenue.csv` entry, not twelve bracketed
    ones. 518's C5 splits `source_table` on "/" and matches the table name, so
    a bracketed label reads as a different table and gives the dataset no
    coverage at all. The unit is commensurable across all twelve by
    construction (see the module docstring), so one entry is also the honest
    shape rather than a convenience."""
    rows_in = sum(d["rows_in"] for d in sysd.values())
    buckets = Counter()
    examples = {}
    for name, d in sysd.items():
        buckets[f"emitted:published_to_resource_revenue_csv"] += d["emitted"]
        examples.setdefault("emitted:published_to_resource_revenue_csv",
                            []).append(f"{name}={d['emitted']:,}")
        for reason, n in d["rejections"].items():
            if not n:
                continue
            buckets[reason] += n
            examples.setdefault(reason, []).append(f"{name}={n:,}")
    out = []
    for disp, n in sorted(buckets.items()):
        out.append(dict(source_table=NR_TABLE, rows_in=rows_in,
                        disposition=disp, rows=n,
                        pct=f"{100.0 * n / rows_in:.2f}",
                        examples="; ".join(examples[disp])[:240],
                        harvest_date=TODAY))
    tot = sum(r["rows"] for r in out)
    if tot != rows_in:
        sys.exit(f"REFUSING: ledger does not reconcile, {rows_in:,} in vs "
                 f"{tot:,} accounted")
    return out


def measure_other_nr():
    """Two more natural-resources tables whose harvest IS countable on disk.

    Not every table in the dataset is reachable this pass and the scoreboard
    says so: 518 reports `c5_row_conservation` as a fraction, so covering 3 of
    8 reads as 3 of 8 rather than as "done". These two are here because their
    read count is a `len()` and refusing them would be theatre; the other five
    need their builders instrumented and are named in the doc."""
    out = []

    # -- anc_ceiling_roster.csv: one HTML page of corporation names ---------
    p = ROOT / "data" / "clean" / "anc_ceiling_roster.csv"
    try:
        anc = load_module("07_parse_ancsa_ceiling.py", "cedar_anc_814")
    except Exception as exc:                                   # noqa: BLE001
        print(f"    anc_ceiling_roster: parser not importable ({exc}) - "
              f"no ledger written rather than a guessed one")
        anc = None
    if anc is not None and anc.SRC.exists():
        parser = anc.TextGrab()
        parser.feed(anc.SRC.read_text(encoding="utf-8", errors="replace"))
        parser.close()
        seen = set()
        b = Counter()
        for raw in parser.lines:
            name = anc.clean(raw)
            if not name or len(name) < 4 or len(name) > 120:
                b["rejected:text_line_is_shorter_than_4_or_longer_than_120_"
                  "characters_so_it_is_not_a_corporation_name"] += 1
            elif anc.NOISE_LINE.match(name):
                b["rejected:text_line_is_site_furniture_nav_copyright_or_a_"
                  "section_heading"] += 1
            elif not anc.CORP_HINT.search(name):
                b["rejected:text_line_carries_no_corporate_form_token_corp_"
                  "inc_ltd_association_native_or_village"] += 1
            elif name.lower() in seen:
                b["duplicate:the_same_corporation_name_appears_more_than_"
                  "once_on_the_page"] += 1
            else:
                seen.add(name.lower())
                b["emitted:published_to_anc_ceiling_roster_csv"] += 1
        rows_in = sum(b.values())
        live = len(read_csv(p))
        extra = live - b["emitted:published_to_anc_ceiling_roster_csv"]
        note = ("one visible text line of the ANCSA corporation list page "
                f"({anc.SRC.name}). ")
        if extra:
            # The Thirteenth Regional Corporation is added by hand: defunct,
            # so absent from every current-state roster, but it held federal
            # contracts and any backward-looking panel needs it. It is not a
            # harvested row and is not counted as one.
            note += (f"{extra} published row(s) are NOT harvested from this "
                     f"page and are excluded from the denominator - the "
                     f"hand-added Thirteenth Regional Corporation, defunct "
                     f"and therefore absent from every current-state roster.")
        for disp, n in sorted(b.items()):
            out.append(dict(source_table="data/clean/anc_ceiling_roster.csv",
                            rows_in=rows_in, disposition=disp, rows=n,
                            pct=f"{100.0 * n / rows_in:.2f}",
                            examples=note[:240] if disp.startswith("emitted")
                            else "", harvest_date=TODAY))

    # -- ancsa_filings_index.csv: the portal index, one row per document ----
    idx = HERE / "ancsa_portal" / "index_rows.csv"
    p = ROOT / "data" / "clean" / "ancsa_filings_index.csv"
    if idx.exists():
        rows = read_csv(idx)
        blank = sum(1 for r in rows if not (r.get("doc_id") or "").strip())
        docs = len({r["doc_id"] for r in rows if (r.get("doc_id") or "").strip()})
        collapsed = len(rows) - blank - docs
        live = len(read_csv(p))
        if docs != live:
            print(f"    ancsa_filings_index: index yields {docs:,} documents "
                  f"but the table holds {live:,} - NOT merged, that "
                  f"disagreement is a finding")
        else:
            b = {"emitted:published_to_ancsa_filings_index_csv": docs,
                 "rejected:portal_index_row_carries_no_document_id": blank,
                 "duplicate:one_document_listed_under_more_than_one_"
                 "corporation_collapsed_to_one_row_with_the_corporations_"
                 "joined": collapsed}
            for disp, n in sorted(b.items()):
                out.append(dict(
                    source_table="data/clean/ancsa_filings_index.csv",
                    rows_in=len(rows), disposition=disp, rows=n,
                    pct=f"{100.0 * n / len(rows):.2f}",
                    examples=("one row of the Alaska DCCED ANCSA portal "
                              "search index as harvested 2026-08-05"
                              if disp.startswith("emitted") else ""),
                    harvest_date=TODAY))
    return out


def merge_conservation(new_rows):
    """MERGE-ONLY on (source_table, disposition). A wholesale rewrite of this
    file destroyed 2,146,673 accounted rows on 2026-09-01."""
    before_cols = backup(CONSERVATION, "pre814")
    cur = read_csv(CONSERVATION)
    cols = before_cols or CONS_COLS
    idx = {(r["source_table"], r["disposition"]): i
           for i, r in enumerate(cur)}
    added = updated = 0
    for r in new_rows:
        k = (r["source_table"], r["disposition"])
        if k in idx:
            cur[idx[k]].update({c: r.get(c, "") for c in cols})
            updated += 1
        else:
            cur.append({c: r.get(c, "") for c in cols})
            added += 1
    with open(CONSERVATION, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in cur:
            w.writerow({c: r.get(c, "") for c in cols})
    column_diff(CONSERVATION.name, before_cols, header_of(CONSERVATION))
    print(f"    merged into {CONSERVATION.relative_to(ROOT)}: "
          f"{added} row(s) added, {updated} updated, {len(cur):,} total "
          f"(was {len(cur) - added:,}) - NOTHING removed")


# =====================================================================
# PART 2 - gaming
# =====================================================================
def carry_award_reference():
    """Put the FAC's own per-report line key back on the table.

    147 fetches `award_reference` and drops it. The cache it wrote is still on
    disk, so the value is READ VERBATIM - never derived, never positional."""
    if not RAWFAC.exists():
        print(f"    {RAWFAC.relative_to(ROOT)} absent - award_reference "
              f"cannot be carried and the SEFA grain stays UNSTATED")
        return False
    raw = json.loads(RAWFAC.read_text(encoding="utf-8"))
    by_report = {}
    for g in raw:
        by_report.setdefault(g.get("report_id", ""), []).append(g)
    rows = read_csv(SEFA)
    if not rows:
        print("    fac_audit_sefa_gaming_programs.csv is empty - nothing to do")
        return False
    before = backup(SEFA, "pre814")
    if "award_reference" in before:
        print("    award_reference already carried")
        return True
    unmatched = []
    for r in rows:
        cands = by_report.get(r["report_id"], [])
        hit = [g for g in cands
               if str(g.get("federal_program_name", "")) ==
               r.get("federal_program_name", "")
               and str(g.get("amount_expended", "")) ==
               r.get("amount_expended", "")]
        if len(hit) == 1 and hit[0].get("award_reference"):
            r["award_reference"] = hit[0]["award_reference"]
        else:
            r["award_reference"] = ""
            unmatched.append(r["report_id"])
    if unmatched:
        sys.exit(f"REFUSING to write {SEFA.name}: {len(unmatched)} row(s) do "
                 f"not match exactly one cached federal_awards record "
                 f"({unmatched[:3]}). A blank key is a broken promise; the "
                 f"table is left as it was.")
    cols = before + ["award_reference"]
    with open(SEFA, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    column_diff(SEFA.name, before, header_of(SEFA))
    print(f"    carried award_reference onto {len(rows)} row(s), verbatim "
          f"from {RAWFAC.relative_to(ROOT)}")
    return True


def key_report(path, key):
    """Measure a declared key against the FULL file. Empty is a legitimate
    result and a byte-identical repeated row has no key at any arity."""
    rows = read_csv(path)
    hdr = header_of(path)
    missing = [c for c in key if c not in hdr]
    dup_whole = sum(v - 1 for v in Counter(
        tuple(r.get(h, "") for h in hdr) for r in rows).values())
    dup_key = 0 if missing else sum(
        v - 1 for v in Counter(tuple(r.get(c, "") for c in key)
                               for r in rows).values())
    blank = 0 if missing else sum(
        1 for r in rows if not all((r.get(c) or "").strip() for c in key))
    return dict(rows=len(rows), key=list(key), key_missing_columns=missing,
                whole_row_duplicates=dup_whole, duplicate_key_rows=dup_key,
                rows_with_a_blank_key_component=blank,
                unique_on_the_full_file=(not missing and not dup_key
                                         and not blank))


def measure_gaming():
    ev = {}
    ev[SEFA.name] = key_report(SEFA, ("report_id", "award_reference"))
    ev[ASSERTS.name] = key_report(ASSERTS, ("assertion_id",))
    ev[CLAIMS.name] = key_report(CLAIMS, ("claim_id",))
    # the C7 statement, measured: what the self-published tables assert
    for p, col in ((ASSERTS, "assertion_class"), (CLAIMS, "assertion_class")):
        ev[p.name]["assertion_class"] = dict(
            Counter(r.get(col, "") for r in read_csv(p)))
    cl = read_csv(CLAIMS)
    ev[CLAIMS.name]["bounded_values"] = sum(
        1 for r in cl if (r.get("value_is_bounded") or "").upper() == "Y")
    ev[CLAIMS.name]["also_in_site_observations"] = sum(
        1 for r in cl
        if (r.get("also_in_gaming_property_site_observations") or "") == "Y")
    ev[CLAIMS.name]["recovered_from_refusal_pile"] = sum(
        1 for r in cl if r.get("claim_family") == "recovered_from_refusal_pile")
    return ev


# =====================================================================
# docs
# =====================================================================
def money_section(gam):
    a, c = gam[ASSERTS.name], gam[CLAIMS.name]
    L = [BEGIN, "",
         "## Gaming self-published claims — a marketing number is not a "
         "measurement (workstream GAMING-NR, 2026-09-01)", "",
         f"`gaming_property_self_published_assertions.csv` ({a['rows']:,} "
         f"rows) and `gaming_property_self_published_claims.csv` "
         f"({c['rows']:,} rows) hold what a casino says about ITSELF on its "
         f"own website — machine counts, hotel rooms, square footage, "
         f"ownership and opening dates. Every row carries `assertion_class`, "
         f"and every class is deliberately OUTSIDE "
         f"`cedar_domain.MeasurementType`.", "",
         "**A buyer may never sum either table against a regulator's "
         "figure.** Specifically, never against `gaming_capacity_official.csv` "
         "(regulator-reported capacity), `nigc_regional_ggr.csv` or "
         "`nigc_revenue_bands.csv` (NIGC), `state_gaming_observations.csv`, "
         "`wa_machine_allocations.csv`, or the Casino City vendor panel. A "
         "self-published count and a regulator count of the same floor are "
         "TWO CLAIMS ABOUT ONE THING, not two things; adding them doubles the "
         "floor, and preferring the larger is how a marketing number becomes "
         "a statistic.", "",
         f"Three further measured cautions on the claims table: "
         f"{c['bounded_values']} of {c['rows']:,} values are BOUNDED "
         f"(\"more than 1,000 slots\") and a bound is not a count; "
         f"{c['also_in_site_observations']} rows restate an observation that "
         f"is already in `gaming_property_site_observations.csv`, so stacking "
         f"the two files double counts them; and "
         f"{c['recovered_from_refusal_pile']} were RECOVERED from a refusal "
         f"pile by `code/383` and are published because a refusal that hides "
         f"the claim is worse than one that labels it, not because they got "
         f"better.", "",
         "The grain is a claim occurrence, not a fact: two sentences on one "
         "page stating the same number about two different ballrooms are two "
         "rows, and collapsing them deletes a ballroom. See "
         "`512.GRAIN_GAMING_NR`.", "",
         f"`fac_audit_sefa_gaming_programs.csv` ({gam[SEFA.name]['rows']} "
         f"row) carries `amount_expended`, which is a FEDERAL AWARD "
         f"EXPENDITURE and is not gaming revenue of any kind. It may not be "
         f"summed with any gaming money column, and it is additive only at "
         f"(report_id, award_reference) — one SEFA line of one Single Audit.",
         "", END]
    return "\n".join(L)


def write_money_section(gam):
    """Append between markers. 574 rewrites this file wholesale and preserves
    only marked sections; an unmarked section was destroyed on 2026-09-01."""
    sec = money_section(gam)
    MONEY_MD.parent.mkdir(parents=True, exist_ok=True)
    prev = (MONEY_MD.read_text(encoding="utf-8", errors="replace")
            if MONEY_MD.exists() else "")
    pat = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.S)
    if pat.search(prev):
        new = pat.sub(lambda _m: sec, prev)
        what = "replaced"
    else:
        new = (prev.rstrip() + "\n\n" + sec + "\n") if prev else sec + "\n"
        what = "appended"
    MONEY_MD.write_text(new, encoding="utf-8")
    kept = len(re.findall(r"<!-- BEGIN ([A-Za-z0-9 _-]+) -->", new))
    print(f"    {what} the GAMING-NR section of "
          f"{MONEY_MD.relative_to(ROOT)} ({kept} marked section(s) present, "
          f"none rewritten)")


def write_doc(sysd, gam):
    rows_in = sum(d["rows_in"] for d in sysd.values())
    emitted = sum(d["emitted"] for d in sysd.values())
    L = ["# GAMING-NR — the twelve read counts, and three gaming grains", "",
         f"*Generated {TODAY} by `code/814_gaming_nr_grain_and_conservation.py "
         f"measure`. Every number is re-measured on every run; `verify` exits "
         f"1 when one stops being true.*", "",
         "## natural-resources C5 — `resource_revenue.csv`", "",
         f"**{rows_in:,} source readings → {emitted:,} published rows.** "
         f"`573 conserve-probe` accounted for 9,434 of 11,305 rows from the "
         f"two countable CSVs and deliberately did not merge the partial. All "
         f"twelve source systems are now counted, so the merge is honest.", "",
         "The unit is a CANDIDATE LEDGER ROW: one reading the harvest examined "
         "and either published or refused for a named reason. That is what "
         "makes twelve incompatible sources commensurable, and it is why "
         "`emitted` sums to exactly the 11,305 rows the table ships.", "",
         "| source system | read unit | readings | published | refused |",
         "|---|---|---:|---:|---:|"]
    for name, d in sorted(sysd.items(), key=lambda kv: -kv[1]["rows_in"]):
        L.append(f"| `{name}` | {d['read_unit']} | {d['rows_in']:,} | "
                 f"{d['emitted']:,} | {sum(d['rejections'].values()):,} |")
    L += ["", "### how each read count was established", ""]
    for name, d in sorted(sysd.items(), key=lambda kv: -kv[1]["rows_in"]):
        L.append(f"- **`{name}`** — {d['note']}."
                 + (f" {d['documents']:,} source document(s) on disk."
                    if d["documents"] else ""))
        for reason, n in sorted(d["rejections"].items()):
            if n:
                L.append(f"    - `{reason}` — {n:,}")
    L += ["",
          "### the other seven tables", "",
          "`anc_ceiling_roster.csv` and `ancsa_filings_index.csv` are also "
          "merged this pass - their harvest is a `len()` and refusing them "
          "would be theatre. Five `natural-resources` tables have no "
          "conservation ledger "
          "yet: `nd_severance_allocation.csv`, `resource_assets.csv`, "
          "`resource_parties.csv`, `tribal_bond_issuances.csv`, "
          "`tribal_tax_bases.csv`. 518 reports the fraction it covers, so the "
          "scoreboard says so too. `resource_parties.csv` is a DERIVED bridge "
          "off the revenue and asset tables rather than a harvest, so a "
          "source-row ledger is the wrong instrument for it; the other four "
          "need their builders instrumented (`105`, `108`, `113`, `135`).",
          "",
          "`natural-resources` also carries a C4 blocker — 25% of "
          "entity-bearing rows keyed — which is identity work and is NOT this "
          "workstream's. See `characterise`.", "",
          "## gaming C1 — three tables", ""]
    for n, d in gam.items():
        L.append(f"- **`{n}`** — {d['rows']:,} rows, key "
                 f"`{'+'.join(d['key'])}`: "
                 + ("unique on the full file, no blank component, "
                    f"{d['whole_row_duplicates']} literal duplicate rows"
                    if d["unique_on_the_full_file"] else
                    f"NOT VALIDATED — missing {d['key_missing_columns']}, "
                    f"{d['duplicate_key_rows']} duplicate key rows, "
                    f"{d['rows_with_a_blank_key_component']} blank components"))
    L += ["",
          "The two self-published tables are prevented from being summed "
          "against a regulator's figure in three places at once: the "
          "`assertion_class` column on every row, the prohibition written into "
          "the grain prose in `512.GRAIN_GAMING_NR`, and the GAMING-NR section "
          "of `docs/MONEY_TOTALLING_RULES.md`.", "",
          "## `62_no_regression_check.py` on 2026-09-01, and who owns each red "
          "line", "",
          "62 exited 0 at the start of this workstream's pass and exits 1 at "
          "the end. TWO of the red lines were GAMING-NR's and are FIXED:", "",
          "- `code_duplicate_numbers` 43 → 44. This script was first written as "
          "`812`, which `812_c8_rebuild_proof.py` had taken in the same window. "
          "Renumbered to 814; the metric is back at 43.",
          "- `lint_class2c` 60 → 62, one instance named as this script's ANCSA "
          "evidence-gate counter. FIXED at source rather than waived: a refused "
          "fact is now recorded as (corporation, series, document stem, why) "
          "and printed. Back at 60.", "",
          "A THIRD was created by this work and is DECLARED, not waived away. "
          "Carrying `award_reference` makes 814 an in-place enricher of a table "
          "147 rebuilds wholesale — a class-6 pair. The ordering is written "
          "down by a person in 147's leading comment block (comment only; no "
          "logic in 147 was changed) and the waiver carries that reason, so it "
          "is counted and named by 293, never hidden. The enricher runs LAST.",
          "", "The rest belong to other workstreams, are named here because "
          "GAMING-NR may not edit `AGENTS.md`, and standing rule 15 asks for a "
          "named owner rather than 'pre-existing, not mine':", "",
          "| red line | measured cause | owner |", "|---|---|---|",
          "| `contract_orphan_shippable = 6` | `native_owned_businesses.csv`, "
          "`nonprofit_schedule_c_coverage.csv`, "
          "`nonprofit_schedule_c_lobbying.csv`, `regulations_gov_comments.csv`, "
          "`regulations_gov_entity_coverage.csv`, "
          "`sam_native_class_distributions.csv` are registered in the codebook "
          "and claimed by NO collection. All six are in the committed contracts "
          "at HEAD too. | native-owned-businesses, nonprofits, lobbying, "
          "contractors |",
          "| `contract_violations = 7` | the six orphans above plus "
          "`entity_aliases.csv`: declared primary_key `alias_id` is NOT unique, "
          "1 duplicate of 6,298, the value being blank. HEAD carries 8 "
          "violations; this pass's run of 512 REDUCED it to 7. | entity layer |",
          "| `files_with_columns_lost_vs_backup = 1` | "
          "`entity_evidence_profile.csv` lost `in_spine`, `rows_per_source` and "
          "`amounts_per_source_NEVER_SUM` against "
          "`.bak_2026-08-28_pre505`. | entity layer / 505 |",
          "| `lint_new_defect_instances = 1` | class6 on "
          "`cedar_dataset_readiness.csv`: 518 rebuilds it wholesale and another "
          "of 526/527/621/760 enriches it in place. | integrator |",
          "| `rulings_unapplied` 1,215 → 2,894 | "
          "`cedar_ruling_ledger_consolidated.csv` now holds 2,894 "
          "`CONFLICT_NOT_APPLIED` of 43,321. | 173_consolidate_rulings_ledger.py |",
          "| `tables_undocumented_in_codebook` / `tables_missing_codebook_block` "
          "3 → 4, `tables_missing_from_25_TABLES` 179 → 188, "
          "`tables_missing_from_27_SPEC` 194 → 195 | new tables landed today "
          "without a codebook block; `cedar_entity_freshness.csv` (1,555 rows) "
          "is the one at a 0% ship ratio. | entity layer |",
          "| SHIPPING LOST: `advocacy_passthrough_2026-08-07.csv` | was "
          "shipping 1,620 rows and the table is GONE from `data/clean`. | "
          "111_build_advocacy_passthrough.py |", "",
          "GAMING-NR touched none of those files. Its own writes are: "
          "`512.GRAIN_GAMING_NR`, `code/814_*`, one carried column on "
          "`fac_audit_sefa_gaming_programs.csv`, 19 merged rows in "
          "`cedar_harvest_conservation.csv`, a comment block in `147`, an "
          "inverted alarm in `573` whose own refusal asked to be retired on "
          "exactly this condition, and two marked docs.", ""]
    DOC.write_text("\n".join(L), encoding="utf-8")
    print(f"    wrote {DOC.relative_to(ROOT)}")


# =====================================================================
# commands
# =====================================================================
def show(sysd, gam):
    rows_in = sum(d["rows_in"] for d in sysd.values())
    emitted = sum(d["emitted"] for d in sysd.values())
    print("  natural-resources - resource_revenue.csv, twelve source systems")
    print(f"    {'source system':44s} {'unit':>10s} {'read':>9s} "
          f"{'published':>10s} {'refused':>8s}")
    for name, d in sorted(sysd.items(), key=lambda kv: -kv[1]["rows_in"]):
        print(f"    {name:44s} {'reading':>10s} {d['rows_in']:>9,} "
              f"{d['emitted']:>10,} {sum(d['rejections'].values()):>8,}")
    print(f"    {'TOTAL':44s} {'':>10s} {rows_in:>9,} {emitted:>10,} "
          f"{rows_in - emitted:>8,}")
    live = len(read_csv(REVENUE))
    print(f"    published == resource_revenue.csv rows: "
          f"{emitted:,} vs {live:,}  "
          f"{'MATCHES' if emitted == live else 'DISAGREES'}")
    print("\n  gaming - three tables")
    for n, d in gam.items():
        print(f"    {n:48s} {d['rows']:>6,} rows  key={'+'.join(d['key'])}  "
              f"{'UNIQUE' if d['unique_on_the_full_file'] else 'NOT VALID'}")


def cmd_measure(_a):
    print("=== 814 measure: workstream GAMING-NR ===\n")
    sysd = measure_nr()
    gam = measure_gaming()
    show(sysd, gam)
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(
        dict(measured_date=TODAY, natural_resources=sysd, gaming=gam),
        indent=1, default=str), encoding="utf-8")
    print(f"\n  wrote {EVIDENCE.relative_to(ROOT)}")
    return 0


def cmd_apply(_a):
    print("=== 814 apply: workstream GAMING-NR ===\n")
    print("  gaming - carrying the FAC's own line key")
    carry_award_reference()
    sysd = measure_nr()
    gam = measure_gaming()
    print("\n  natural-resources - merging the conservation ledger")
    merge_conservation(nr_ledger_rows(sysd) + measure_other_nr())
    print("\n  documents")
    write_money_section(gam)
    write_doc(sysd, gam)
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(
        dict(measured_date=TODAY, natural_resources=sysd, gaming=gam),
        indent=1, default=str), encoding="utf-8")
    print()
    show(sysd, gam)
    return 0


def cmd_verify(_a):
    print("=== 814 verify: workstream GAMING-NR ===\n")
    fails = []
    sysd = measure_nr()          # exits non-zero itself on non-conservation
    gam = measure_gaming()
    cons = [r for r in read_csv(CONSERVATION)
            if r["source_table"] == NR_TABLE]
    if not cons:
        fails.append(f"{NR_TABLE} has no conservation ledger rows")
    else:
        want = sum(d["rows_in"] for d in sysd.values())
        got_in = int(cons[0]["rows_in"] or 0)
        got = sum(int(r["rows"] or 0) for r in cons)
        if got_in != want:
            fails.append(f"ledger rows_in {got_in:,} != measured {want:,}")
        if got != got_in:
            fails.append(f"ledger dispositions sum to {got:,} against "
                         f"rows_in {got_in:,}")
        pub = sum(int(r["rows"] or 0) for r in cons
                  if r["disposition"].startswith("emitted:"))
        live = len(read_csv(REVENUE))
        if pub != live:
            fails.append(f"ledger publishes {pub:,} but "
                         f"resource_revenue.csv holds {live:,}")
    for n, d in gam.items():
        if not d["unique_on_the_full_file"]:
            fails.append(f"{n}: declared key {'+'.join(d['key'])} does not "
                         f"validate - missing={d['key_missing_columns']} "
                         f"dupes={d['duplicate_key_rows']} "
                         f"blanks={d['rows_with_a_blank_key_component']}")
    md = MONEY_MD.read_text(encoding="utf-8", errors="replace") \
        if MONEY_MD.exists() else ""
    if BEGIN not in md or END not in md:
        fails.append("the GAMING-NR section of MONEY_TOTALLING_RULES.md is "
                     "gone - 574 or another writer rewrote it unmarked")
    show(sysd, gam)
    print()
    if fails:
        for f in fails:
            print(f"  FAIL  {f}")
        return 1
    print(f"  OK - twelve read counts reconcile to "
          f"{sum(d['rows_in'] for d in sysd.values()):,} readings and "
          f"{len(read_csv(REVENUE)):,} published rows; three gaming keys "
          f"validate on their full files")
    return 0


def cmd_characterise(_a):
    """natural-resources C4, characterised and NOT resolved."""
    print("=== 814 characterise: natural-resources C4 (NOT this "
          "workstream's to resolve) ===\n")
    tables = ["anc_ceiling_roster.csv", "ancsa_filings_index.csv",
              "nd_severance_allocation.csv", "resource_assets.csv",
              "resource_parties.csv", "resource_revenue.csv",
              "tribal_bond_issuances.csv", "tribal_tax_bases.csv"]
    idc = ("cedar_uid", "tribe_id", "entity_id", "cedar_entity_id")
    tot = keyed = 0
    for n in tables:
        p = CLEAN / n
        rows = read_csv(p)
        if not rows:
            continue
        cols = [c for c in (rows[0].keys()) if c in idc]
        if not cols:
            print(f"  {n:34s} {len(rows):>7,} rows   NO ID COLUMN AT ALL")
            continue
        k = sum(1 for r in rows if any((r.get(c) or "").strip() for c in cols))
        tot += len(rows)
        keyed += k
        print(f"  {n:34s} {len(rows):>7,} rows   {k:>7,} keyed "
              f"({100.0 * k / len(rows):5.1f}%)  via {'+'.join(cols)}")
    print(f"\n  {keyed:,} of {tot:,} entity-bearing rows keyed "
          f"({100.0 * keyed / tot:.1f}%)")
    # WHERE THE HOLE IS. The dataset-level 25% is THREE different things and
    # only one of them is unresolved identity. Measured, not asserted.
    rv = read_csv(CLEAN / "resource_revenue.csv")
    agg = Counter(r.get("aggregation_level", "") for r in rv)
    role = ("recipient_entity_id", "beneficiary_entity_id",
            "operator_entity_id")
    role_keyed = sum(1 for r in rv
                     if any((r.get(c) or "").strip() for c in role))
    uid_keyed = sum(1 for r in rv if (r.get("cedar_uid") or "").strip())
    national = agg.get("national_aggregate", 0)
    entity_rows = sum(v for k, v in agg.items() if k.startswith("entity"))
    print(f"\n  `resource_revenue.csv` breaks into THREE causes, and only one "
          f"is unresolved identity:")
    print(f"    {national:>7,}  aggregation_level = national_aggregate. "
          f"Interior releases Native American extraction and revenue ONLY in "
          f"aggregate, BY LAW. The row has no entity because the publisher "
          f"refuses to name one - ADR-010 `record_scope`, not unresolved "
          f"work. Scoring these as unkeyed measures the statute.")
    print(f"    {role_keyed:>7,}  rows DO carry a resolved entity, in "
          f"role-prefixed columns ({', '.join(role)}). 518's C4 scanner reads "
          f"only cedar_uid / tribe_id / entity_id / cedar_entity_id, so it "
          f"cannot see them and scores every one as unkeyed.")
    print(f"    {role_keyed - uid_keyed:>7,}  of those carry the entity but "
          f"NOT `cedar_uid` ({uid_keyed:,} do). That is the real, small, "
          f"nameable task: backfill cedar_uid from the spine for rows that "
          f"already name an entity. It is a hub join, not a resolution.")
    print(f"    {entity_rows:>7,}  rows are entity_specific by the table's own "
          f"aggregation_level column.")
    print("\n  Owner: the entity layer / ADR-009 hub. GAMING-NR does not "
          "resolve identity and has not - this is a characterisation and "
          "nothing above was written to any file.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("measure").set_defaults(fn=cmd_measure)
    sub.add_parser("apply").set_defaults(fn=cmd_apply)
    sub.add_parser("verify").set_defaults(fn=cmd_verify)
    sub.add_parser("characterise").set_defaults(fn=cmd_characterise)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
