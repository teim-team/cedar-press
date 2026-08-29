#!/usr/bin/env python3
"""
234_measure_reporting_regime_signatures.py — READ-ONLY. NO NETWORK. NO WRITES TO data/.

WHY THIS EXISTS
---------------
A reporting rule can look exactly like a finding. When a threshold moves, a filing
frequency changes, or a relief programme starts, the DATA STEPS — and the step is a
fact about the REGIME, not about Indian Country.

`docs/ASSUMPTIONS_AND_LIMITATIONS.md` is the register that lets a writer tell the two
apart. This script supplies the *measured observation* half of every entry in it: the
in-our-own-data signature of each documented regime change, so that the register can
cite a statute AND a number from our files in the same row.

It is the companion to `code/227_anomaly_sweep.py` (a concurrent agent's year-over-year
anomaly detector, writing `docs/ANOMALY_REPORT.md`). 227 finds the steps. 234 measures
the steps we ALREADY EXPECT from the rulebook. An anomaly that lands on a date in this
file is explained; one that does not is a candidate finding.

WHAT IT MEASURES
----------------
  prime      — rows/dollars/attributed share by FY; set-aside mix by FY;
               extent_competed vocabulary by FY (the download-vintage seam);
               small-action counts against the micro-purchase / SAT floors
  assistance — rows/dollars by FY; the COVID relief CFDAs (21.019, 21.027) by FY;
               ARRA-era share; the FY2007 FAADS overlap
  faads      — max fiscal year actually held (settles the 2007-vs-2008 discrepancy
               between START_HERE and USASPENDING_PROBLEM_BRIEF)
  subawards  — rows/dollars by FY; the FFATA $25k/$30k floor; the pre-FSRS floor
  lobbying   — filings by year and filing_type; the HLOGA 2008 semiannual->quarterly
               doubling; the share of filings carrying no dollar
  nagpra     — notices by year and notice_type; the 2024 43 CFR 10 revision step
  fac        — tribal Single Audits by audit_year; is_public split; the audit
               threshold floor
  nonprofit  — 990-N share of np_orgs; Schedule I recipient EINs absent from BMF
  gaming     — facilities by property_status; open_date distribution vs IGRA 1988

    py -3 code/234_measure_reporting_regime_signatures.py

Writes ONE artefact: review/reporting_regime_signatures_<date>.json
Modifies no dataset. Makes no network request.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean"
OUT = ROOT / "review" / f"reporting_regime_signatures_{date.today().isoformat()}.json"

csv.field_size_limit(10 ** 7)

R: dict = {"generated": date.today().isoformat(), "note": "READ-ONLY measurement. Companion to docs/ASSUMPTIONS_AND_LIMITATIONS.md."}


def num(s):
    try:
        return float(str(s).replace(",", "").replace("$", "").strip() or 0)
    except Exception:
        return 0.0


def rows(name, cols=None):
    """Stream a clean CSV. RAISES on a missing column — standing rule 8:
    an absent column name must never read as an empty source."""
    p = CLEAN / name
    if not p.exists():
        raise SystemExit(f"MISSING FILE: {p}")
    with open(p, newline="", encoding="utf-8", errors="replace") as fh:
        rd = csv.DictReader(fh)
        if cols:
            missing = [c for c in cols if c not in rd.fieldnames]
            if missing:
                raise SystemExit(f"{name}: columns absent, refusing to report a zero: {missing}")
        for r in rd:
            yield r


# ---------------------------------------------------------------- prime
def prime():
    by_fy = defaultdict(lambda: {"rows": 0, "obl": 0.0, "attr_rows": 0, "attr_obl": 0.0,
                                 "native_setaside_obl": 0.0, "no_setaside_obl": 0.0})
    vocab_by_fy = defaultdict(Counter)
    setaside_by_fy = defaultdict(Counter)
    norm_present = 0
    small = defaultdict(lambda: Counter())
    NATIVE_SA = {"Buy Indian", "Indian Business"}
    need = ["fiscal_year", "total_obligations", "attributed_flag", "setaside",
            "extent_competed", "extent_competed_normalized", "source_file"]
    for r in rows("prime_contracts.csv", need):
        fy = r["fiscal_year"]
        o = num(r["total_obligations"])
        d = by_fy[fy]
        d["rows"] += 1
        d["obl"] += o
        if str(r["attributed_flag"]).strip() in ("1", "Y", "True", "true"):
            d["attr_rows"] += 1
            d["attr_obl"] += o
        sa = (r["setaside"] or "").strip()
        setaside_by_fy[fy][sa] += 1
        if sa in NATIVE_SA:
            d["native_setaside_obl"] += o
        if sa == "None reported":
            d["no_setaside_obl"] += o
        ec = (r["extent_competed"] or "").strip()
        vocab_by_fy[fy]["blank" if not ec else
                        ("single_letter_code" if len(ec) == 1 else
                         ("short_alpha_code" if len(ec) <= 4 and " " not in ec else "rendered_label"))] += 1
        if (r["extent_competed_normalized"] or "").strip():
            norm_present += 1
        # micro-purchase / SAT floors, on POSITIVE obligations only
        if o > 0:
            for label, ceil in (("le_2500", 2500), ("le_3000", 3000), ("le_3500", 3500),
                                ("le_10000", 10000), ("le_150000", 150000), ("le_250000", 250000)):
                if o <= ceil:
                    small[fy][label] += 1
            small[fy]["positive_rows"] += 1
    R["prime"] = {
        "by_fiscal_year": {k: {kk: (round(vv, 2) if isinstance(vv, float) else vv)
                               for kk, vv in v.items()} for k, v in sorted(by_fy.items())},
        "extent_competed_token_shape_by_fy": {k: dict(v) for k, v in sorted(vocab_by_fy.items())},
        "extent_competed_normalized_populated_rows": norm_present,
        "setaside_by_fy": {k: dict(v) for k, v in sorted(setaside_by_fy.items())},
        "small_action_counts_by_fy": {k: dict(v) for k, v in sorted(small.items())},
    }


# ---------------------------------------------------------------- assistance
COVID_CFDA = {"21.019": "Coronavirus Relief Fund", "21.027": "Coronavirus State and Local Fiscal Recovery Funds",
              "21.023": "Emergency Rental Assistance", "21.026": "Homeowner Assistance Fund"}


def assistance():
    by_fy = defaultdict(lambda: {"rows": 0, "obl": 0.0, "attr_obl": 0.0})
    covid = defaultdict(lambda: defaultdict(float))
    covid_rows = defaultdict(lambda: defaultdict(int))
    top_by_fy = defaultdict(Counter)
    need = ["fiscal_year", "obligated_usd", "cfda", "cfda_title", "attributed_flag"]
    for r in rows("federal_funding_transactions.csv", need):
        fy = r["fiscal_year"]
        o = num(r["obligated_usd"])
        d = by_fy[fy]
        d["rows"] += 1
        d["obl"] += o
        if str(r["attributed_flag"]).strip() in ("1", "Y", "True", "true"):
            d["attr_obl"] += o
        c = (r["cfda"] or "").strip()
        if c in COVID_CFDA:
            covid[c][fy] += o
            covid_rows[c][fy] += 1
        top_by_fy[fy][(c + " " + (r["cfda_title"] or ""))[:70]] += 1
    R["assistance"] = {
        "by_fiscal_year": {k: {kk: round(vv, 2) if isinstance(vv, float) else vv for kk, vv in v.items()}
                           for k, v in sorted(by_fy.items())},
        "covid_cfda_dollars_by_fy": {c: {fy: round(v, 2) for fy, v in sorted(d.items())} for c, d in covid.items()},
        "covid_cfda_rows_by_fy": {c: dict(sorted(d.items())) for c, d in covid_rows.items()},
        "covid_cfda_titles": COVID_CFDA,
        "top_programmes_2020_2022": {fy: top_by_fy[fy].most_common(12) for fy in ("2020", "2021", "2022") if fy in top_by_fy},
        "top_programmes_2009_2011": {fy: top_by_fy[fy].most_common(12) for fy in ("2009", "2010", "2011") if fy in top_by_fy},
    }


# ---------------------------------------------------------------- faads
def faads():
    fys = Counter()
    idcols = None
    n = 0
    p = CLEAN / "faads_transactions_all_agencies.csv"
    with open(p, newline="", encoding="utf-8", errors="replace") as fh:
        rd = csv.DictReader(fh)
        idcols = rd.fieldnames
        fycol = next((c for c in rd.fieldnames if c.lower() in ("fiscal_year", "fy")), None)
        if not fycol:
            raise SystemExit("faads: no fiscal_year column; refusing to report a zero")
        for r in rd:
            n += 1
            fys[r[fycol]] += 1
    R["faads"] = {"rows": n, "fiscal_years": dict(sorted(fys.items())),
                  "max_fiscal_year": max(k for k in fys if k.strip()),
                  "columns": idcols}


# ---------------------------------------------------------------- subawards
def subawards():
    by_fy = defaultdict(lambda: {"rows": 0, "amt": 0.0})
    bands = Counter()
    flag = Counter()
    need = ["fiscal_year", "subaward_amount", "action_date_precedes_ffata_flag", "subaward_type"]
    for r in rows("subawards.csv", need):
        fy = r["fiscal_year"]
        a = num(r["subaward_amount"])
        by_fy[fy]["rows"] += 1
        by_fy[fy]["amt"] += a
        bands["lt_25000" if a < 25000 else ("lt_30000" if a < 30000 else "ge_30000")] += 1
        flag[str(r["action_date_precedes_ffata_flag"]).strip()] += 1
    R["subawards"] = {
        "by_fiscal_year": {k: {kk: round(vv, 2) if isinstance(vv, float) else vv for kk, vv in v.items()}
                           for k, v in sorted(by_fy.items())},
        "amount_bands_vs_ffata_threshold": dict(bands),
        "action_date_precedes_ffata_flag": dict(flag),
    }


# ---------------------------------------------------------------- lobbying
def lobbying():
    by_year = defaultdict(lambda: Counter())
    types = Counter()
    period_by_year = defaultdict(Counter)
    nodollar = Counter()
    need = ["filing_year", "filing_type", "filing_period", "income_usd", "expenses_usd", "spend_usd"]
    n = 0
    for r in rows("native_entity_lobbying_disclosures.csv", need):
        n += 1
        y = (r["filing_year"] or "").strip()
        ft = (r["filing_type"] or "").strip()
        by_year[y]["filings"] += 1
        by_year[y][ft] += 1
        types[ft] += 1
        period_by_year[y][(r["filing_period"] or "").strip()] += 1
        has = any(num(r[c]) > 0 for c in ("income_usd", "expenses_usd", "spend_usd"))
        by_year[y]["with_dollar" if has else "no_dollar"] += 1
        if not has:
            nodollar[y] += 1
    R["lobbying"] = {
        "rows": n,
        "by_year": {k: dict(v) for k, v in sorted(by_year.items())},
        "filing_type_totals": dict(types.most_common()),
        "filing_period_by_year": {k: dict(v) for k, v in sorted(period_by_year.items())},
        "no_dollar_by_year": dict(sorted(nodollar.items())),
        "no_dollar_total": sum(nodollar.values()),
        "no_dollar_share_pct": round(100.0 * sum(nodollar.values()) / n, 2) if n else None,
    }


# ---------------------------------------------------------------- nagpra
def nagpra():
    by_year = defaultdict(Counter)
    need = ["publication_year", "notice_type", "culturally_unidentifiable", "statute_stage"]
    n = 0
    for r in rows("nagpra_notices.csv", need):
        n += 1
        y = (r["publication_year"] or "").strip()
        by_year[y]["notices"] += 1
        by_year[y][(r["notice_type"] or "BLANK").strip()[:44]] += 1
        if str(r["culturally_unidentifiable"]).strip() in ("1", "Y", "True", "true"):
            by_year[y]["culturally_unidentifiable"] += 1
    R["nagpra"] = {"rows": n, "by_year": {k: dict(v) for k, v in sorted(by_year.items())}}


# ---------------------------------------------------------------- fac
def fac():
    by_year = defaultdict(Counter)
    spend = defaultdict(lambda: Counter())
    need = ["audit_year", "is_public", "total_amount_expended"]
    n = 0
    for r in rows("fac_tribal_single_audits.csv", need):
        n += 1
        y = (r["audit_year"] or "").strip()
        by_year[y]["reports"] += 1
        by_year[y]["public" if str(r["is_public"]).strip().lower() in ("1", "true", "y", "yes") else "nonpublic"] += 1
        e = num(r["total_amount_expended"])
        for lbl, lo in (("lt_300k", 300000), ("lt_500k", 500000), ("lt_750k", 750000), ("lt_1m", 1000000)):
            if 0 < e < lo:
                spend[y][lbl] += 1
        if e > 0:
            spend[y]["with_expenditure"] += 1
    R["fac"] = {"rows": n, "by_audit_year": {k: dict(v) for k, v in sorted(by_year.items())},
                "expenditure_below_threshold_by_year": {k: dict(v) for k, v in sorted(spend.items())}}


# ---------------------------------------------------------------- nonprofit
def nonprofit():
    filing_req = Counter()
    in_bmf = Counter()
    n = 0
    for r in rows("np_orgs.csv", ["bmf_in_snapshot", "bmf_filing_req_cd", "bmf_status"]):
        n += 1
        filing_req[(r["bmf_filing_req_cd"] or "BLANK").strip()] += 1
        in_bmf[str(r["bmf_in_snapshot"]).strip()] += 1
    # Schedule I recipients absent from BMF
    recip = {}
    absent_dollars = 0.0
    absent_eins = set()
    present_eins = set()
    m = 0
    for r in rows("np_schedule_i_grants.csv", ["recipient_ein", "recipient_bmf_status", "cash_grant_usd",
                                               "noncash_assistance_usd", "recipient_outside_990_universe_signal"]):
        m += 1
        ein = (r["recipient_ein"] or "").strip()
        if not ein:
            continue
        amt = num(r["cash_grant_usd"]) + num(r["noncash_assistance_usd"])
        if (r["recipient_bmf_status"] or "").strip():
            present_eins.add(ein)
        else:
            absent_eins.add(ein)
            absent_dollars += amt
    R["nonprofit"] = {
        "np_orgs_rows": n,
        "bmf_filing_req_cd": dict(filing_req.most_common(20)),
        "bmf_in_snapshot": dict(in_bmf),
        "schedule_i_rows": m,
        "recipient_eins_with_bmf_status": len(present_eins),
        "recipient_eins_absent_from_bmf": len(absent_eins),
        "recipient_eins_absent_from_bmf_dollars": round(absent_dollars, 2),
    }


# ---------------------------------------------------------------- gaming
def gaming():
    status = Counter()
    opens = Counter()
    pre_igra = 0
    n = 0
    for r in rows("gaming_facilities.csv", ["property_status", "open_date", "open_date_predates_tribal_gaming_era"]):
        n += 1
        status[(r["property_status"] or "BLANK").strip()] += 1
        od = (r["open_date"] or "").strip()
        if od[:4].isdigit():
            y = int(od[:4])
            opens[str((y // 5) * 5)] += 1
            if y < 1988:
                pre_igra += 1
    R["gaming"] = {"rows": n, "property_status": dict(status.most_common()),
                   "open_year_5yr_buckets": dict(sorted(opens.items())),
                   "open_date_before_IGRA_1988": pre_igra}


def main():
    for fn in (prime, assistance, faads, subawards, lobbying, nagpra, fac, nonprofit, gaming):
        try:
            fn()
        except SystemExit as e:
            R[fn.__name__] = {"ERROR": str(e)}
            print(f"  ! {fn.__name__}: {e}", file=sys.stderr)
        else:
            print(f"  ok {fn.__name__}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".json.part")
    tmp.write_text(json.dumps(R, indent=1, default=str), encoding="utf-8")
    tmp.replace(OUT)          # an interruption must not look like a completion
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
