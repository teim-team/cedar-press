#!/usr/bin/env python3
"""
33_nonprofit_financials.py — Dataset 6 financial layer from the ProPublica
Nonprofit Explorer API (v2).

One script, --steps switches:
    pull    fetch + cache one JSON per EIN (throttled, checkpointed, resumable)
    build   parse the cache into data/clean/np_financials.csv + np_org_scale.csv
    report  coverage / lobbying / place-name-by-revenue analysis to the log

Scope (NOT the full 12,764):
    1. every np_orgs row with confidence_tier == 'A'                    (1,090)
    2. every nonprofit_exclusion_rulings row with recheck_candidate == 1   (67)
    3. every review/np_placename_risk_2026-08-05.csv row                  (412)
    union = 1,157 EINs

PRIME DIRECTIVE: zero fabrication. Every figure written here comes from an
API response body cached on disk under data/raw/external/propublica_990/.
Nothing is estimated, imputed, interpolated or back-filled.

Source: ProPublica Nonprofit Explorer API v2
        https://projects.propublica.org/nonprofits/api/v2/organizations/{ein}.json
        (free, no key; ProPublica republishes the IRS SOI e-file extracts)
"""

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data", "raw", "external", "propublica_990")
LOGP = os.path.join(ROOT, "logs", "33_nonprofit_financials.log")
FETCHLOG = os.path.join(CACHE, "_fetch_log.csv")
MANIFEST = os.path.join(CACHE, "_SOURCE_MANIFEST.csv")

API = "https://projects.propublica.org/nonprofits/api/v2/organizations/%s.json"
UA = "Cedar Press research build (Dataset 6 nonprofit financial layer)"
THROTTLE = 1.05          # seconds between requests -> ~1 req/sec
RETRIEVED = date.today().isoformat()

_logfh = None


def log(msg):
    global _logfh
    if _logfh is None:
        os.makedirs(os.path.dirname(LOGP), exist_ok=True)
        _logfh = open(LOGP, "a", encoding="utf-8")
        _logfh.write("\n=== RUN %s ===\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
    line = str(msg)
    print(line)
    _logfh.write(line + "\n")
    _logfh.flush()


# --------------------------------------------------------------------------
# target set
# --------------------------------------------------------------------------
def target_set():
    orgs = pd.read_csv(os.path.join(ROOT, "data", "clean", "np_orgs.csv"),
                       dtype=str, low_memory=False)
    excl = pd.read_csv(os.path.join(ROOT, "data", "spine",
                                    "nonprofit_exclusion_rulings.csv"), dtype=str)
    risk = pd.read_csv(os.path.join(ROOT, "review",
                                    "np_placename_risk_2026-08-05.csv"), dtype=str)

    orgs["EIN"] = orgs["EIN"].str.strip().str.zfill(9)
    excl["ein"] = excl["ein"].str.strip().str.zfill(9)
    risk["ein"] = risk["ein"].str.strip().str.zfill(9)

    tier_a = set(orgs.loc[orgs.confidence_tier == "A", "EIN"])
    recheck = set(excl.loc[excl.recheck_candidate == "1", "ein"])
    placename = set(risk["ein"])

    targets = sorted(tier_a | recheck | placename)
    meta = {}
    obyein = orgs.set_index("EIN")
    ebyein = excl.drop_duplicates("ein").set_index("ein")
    for e in targets:
        row = obyein.loc[e] if e in obyein.index else None
        m = {
            "in_tier_a": int(e in tier_a),
            "in_recheck_candidate": int(e in recheck),
            "in_placename_risk": int(e in placename),
        }
        if row is not None:
            m["org_name_bmf"] = row.get("org_name", "")
            m["state"] = row.get("state", "")
            m["confidence_tier"] = row.get("confidence_tier", "")
            m["bmf_990_tier"] = row.get("tier", "")
            m["bmf_revenue_amt"] = row.get("bmf_revenue_amt", "")
            m["review_flag"] = row.get("review_flag", "")
            m["ntee_code"] = row.get("ntee_code", "")
        else:
            er = ebyein.loc[e] if e in ebyein.index else None
            m["org_name_bmf"] = er.get("org_name", "") if er is not None else ""
            m["state"] = er.get("state", "") if er is not None else ""
            m["confidence_tier"] = ""
            m["bmf_990_tier"] = ""
            m["bmf_revenue_amt"] = ""
            m["review_flag"] = ""
            m["ntee_code"] = ""
        meta[e] = m
    return targets, meta, tier_a, recheck, placename


# --------------------------------------------------------------------------
# step: pull
# --------------------------------------------------------------------------
def cache_path(ein):
    return os.path.join(CACHE, "%s.json" % ein)


def fetch_one(ein, max_retries=3):
    """Return (status, payload_or_None). Never raises."""
    url = API % ein
    delay = 2.0
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=45) as r:
                return "ok", json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as ex:
            if ex.code == 404:
                return "not_found", None
            if ex.code in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            return "http_%d" % ex.code, None
        except Exception as ex:                       # noqa: BLE001
            if attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            return "error_%s" % type(ex).__name__, None
    return "error_exhausted", None


def step_pull(targets, limit=None):
    os.makedirs(CACHE, exist_ok=True)
    todo = [e for e in targets if not os.path.exists(cache_path(e))]
    cached = len(targets) - len(todo)
    if limit:
        todo = todo[:limit]
    log("[pull] targets=%d already_cached=%d to_fetch=%d"
        % (len(targets), cached, len(todo)))

    new = os.path.getsize(FETCHLOG) == 0 if os.path.exists(FETCHLOG) else True
    fh = open(FETCHLOG, "a", newline="", encoding="utf-8")
    w = csv.writer(fh)
    if new:
        w.writerow(["ein", "status", "n_filings_with_data",
                    "n_filings_without_data", "source_url", "retrieved_date"])

    counts = {}
    t0 = time.time()
    for i, ein in enumerate(todo, 1):
        status, payload = fetch_one(ein)
        counts[status] = counts.get(status, 0) + 1
        nw = nwo = ""
        if payload is not None:
            nw = len(payload.get("filings_with_data") or [])
            nwo = len(payload.get("filings_without_data") or [])
            payload["_cedar_retrieved_date"] = RETRIEVED
            payload["_cedar_source_url"] = API % ein
            with open(cache_path(ein), "w", encoding="utf-8") as cf:
                json.dump(payload, cf)
        else:
            # sentinel so a rerun does not re-hit a known-dead EIN
            with open(cache_path(ein), "w", encoding="utf-8") as cf:
                json.dump({"_cedar_status": status, "_cedar_ein": ein,
                           "_cedar_retrieved_date": RETRIEVED,
                           "_cedar_source_url": API % ein}, cf)
        w.writerow([ein, status, nw, nwo, API % ein, RETRIEVED])
        fh.flush()
        if i % 100 == 0:
            el = time.time() - t0
            log("[pull]   %d/%d  %.0fs elapsed  %s" % (i, len(todo), el, counts))
        time.sleep(THROTTLE)
    fh.close()
    log("[pull] done. status counts: %s" % counts)

    with open(MANIFEST, "w", newline="", encoding="utf-8") as mf:
        mw = csv.writer(mf)
        mw.writerow(["source", "url", "access", "fetched_date", "n_files", "note"])
        mw.writerow(["ProPublica Nonprofit Explorer API v2",
                     "https://projects.propublica.org/nonprofits/api/v2/organizations/{ein}.json",
                     "free, no API key", RETRIEVED,
                     len([f for f in os.listdir(CACHE) if f.endswith(".json")]),
                     "One JSON per EIN. ProPublica republishes IRS SOI e-file "
                     "extracts; filings_with_data carry parsed financials, "
                     "filings_without_data carry a PDF link only."])


# --------------------------------------------------------------------------
# step: build
# --------------------------------------------------------------------------
FORMTYPE = {0: "990", 1: "990EZ", 2: "990PF"}


def num(v):
    """Return the value only if it is a real number in the response."""
    if v is None or v == "":
        return ""
    if isinstance(v, bool):
        return ""
    if isinstance(v, (int, float)):
        return v
    try:
        return float(v)
    except (TypeError, ValueError):
        return ""


def pick(f, *keys):
    """First key present with a non-null value. No arithmetic, no defaults."""
    for k in keys:
        if k in f and f[k] is not None and f[k] != "":
            v = num(f[k])
            if v != "":
                return v
    return ""


def parse_filing(f, form_type):
    """Map IRS SOI extract fields to the output schema. Field names differ by
    form; only fields actually present in the response are used."""
    if form_type == "990PF":
        # 990-PF: revenue/expenses per books. No program service revenue line.
        rev = pick(f, "totrevenue", "totrcptperbks")
        exp = pick(f, "totfuncexpns", "totexpnspbks")
        contrib = pick(f, "grscontrgifts", "totcntrbgfts")
        prgm = ""
    elif form_type == "990EZ":
        rev = pick(f, "totrevenue", "totrevnue")
        exp = pick(f, "totfuncexpns", "totexpns")
        contrib = pick(f, "totcntrbs", "totcntrbgfts")
        prgm = pick(f, "prgmservrev", "totprgmrevnue")
    else:                                    # full 990
        rev = pick(f, "totrevenue")
        exp = pick(f, "totfuncexpns")
        contrib = pick(f, "totcntrbgfts")
        prgm = pick(f, "totprgmrevnue")
    return {
        "total_revenue": rev,
        "total_expenses": exp,
        "total_assets": pick(f, "totassetsend"),
        "total_liabilities": pick(f, "totliabend"),
        "program_service_revenue": prgm,
        "contributions_grants": contrib,
        "net_assets_end": pick(f, "totnetassetend", "totnetassetsend"),
        "officer_compensation": pick(f, "compnsatncurrofcr", "compofficers"),
    }


FIN_COLS = [
    "ein", "org_name", "tax_year", "form_type",
    "total_revenue", "total_expenses", "total_assets", "total_liabilities",
    "program_service_revenue", "contributions_grants",
    "lobbying_expenditure", "n_employees",
    "pdf_url", "source_url", "retrieved_date",
    # provenance / cross-dataset columns
    "tax_period", "form_type_raw", "has_financial_data", "pre_2000_flag",
    "lobbying_indicator_990pf", "propaganda_indicator_990pf",
    "lobbying_field_basis", "n_employees_basis",
    "net_assets_end", "officer_compensation",
    "state", "confidence_tier", "bmf_990_tier",
    "in_tier_a", "in_recheck_candidate", "in_placename_risk",
    "source_dataset", "filing_updated",
]

# Short codes, expanded in docs/NONPROFIT_FINANCIALS_LOG.md:
#   990pf_infleg_indicator_only = 990-PF "influencing legislation" Y/N flag
#                                 (infleg); the API carries no dollar amount
#   not_exposed_by_api          = ProPublica v2 SOI extract has no Schedule C
#                                 lobbying field for this form type
#   not_exposed_by_api          = Form 990 Part I line 5 (employee count) is
#                                 likewise absent from the extract
LOBBY_BASIS_PF = "990pf_infleg_indicator_only"
LOBBY_BASIS_OTHER = "not_exposed_by_api"
EMP_BASIS = "not_exposed_by_api"


def step_build(targets, meta):
    rows = []
    org_rows = []
    status_counts = {}
    key_union = set()
    lobby_seen = {"infleg_Y": 0, "propgnda_Y": 0, "pf_filings": 0}

    for ein in targets:
        p = cache_path(ein)
        m = meta[ein]
        base = {
            "state": m["state"], "confidence_tier": m["confidence_tier"],
            "bmf_990_tier": m["bmf_990_tier"],
            "in_tier_a": m["in_tier_a"],
            "in_recheck_candidate": m["in_recheck_candidate"],
            "in_placename_risk": m["in_placename_risk"],
            "source_dataset": "ProPublica Nonprofit Explorer API v2",
            "retrieved_date": RETRIEVED,
            "source_url": API % ein,
        }
        if not os.path.exists(p):
            status_counts["not_pulled"] = status_counts.get("not_pulled", 0) + 1
            org_rows.append(dict(base, ein=ein, org_name=m["org_name_bmf"],
                                 api_status="not_pulled"))
            continue
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
        if "_cedar_status" in d:
            st = d["_cedar_status"]
            status_counts[st] = status_counts.get(st, 0) + 1
            org_rows.append(dict(base, ein=ein, org_name=m["org_name_bmf"],
                                 api_status=st))
            continue

        status_counts["ok"] = status_counts.get("ok", 0) + 1
        org = d.get("organization") or {}
        name = org.get("name") or m["org_name_bmf"]
        ret = d.get("_cedar_retrieved_date", RETRIEVED)

        byperiod = {}
        for f in (d.get("filings_with_data") or []):
            key_union |= set(f.keys())
            ft = FORMTYPE.get(f.get("formtype"), "UNKNOWN")
            vals = parse_filing(f, ft)
            infleg = f.get("infleg")
            propg = f.get("propgndacd")
            if ft == "990PF":
                lobby_seen["pf_filings"] += 1
                if infleg not in (None, "", "N"):
                    lobby_seen["infleg_Y"] += 1
                if propg not in (None, "", "N"):
                    lobby_seen["propgnda_Y"] += 1
            r = dict(base)
            r.update({
                "ein": ein, "org_name": name,
                "tax_year": f.get("tax_prd_yr", ""),
                "tax_period": f.get("tax_prd", ""),
                "form_type": ft,
                "form_type_raw": "",
                "has_financial_data": 1,
                "lobbying_expenditure": "",
                "n_employees": "",
                "lobbying_indicator_990pf": infleg if ft == "990PF" and infleg else "",
                "propaganda_indicator_990pf": propg if ft == "990PF" and propg else "",
                "lobbying_field_basis": LOBBY_BASIS_PF if ft == "990PF" else LOBBY_BASIS_OTHER,
                "n_employees_basis": EMP_BASIS,
                "pdf_url": f.get("pdf_url") or "",
                "retrieved_date": ret,
                "filing_updated": f.get("updated", ""),
            })
            r.update(vals)
            k = (f.get("tax_prd"), ft)
            # keep the richer record if the same period appears twice
            if k not in byperiod or (r["total_revenue"] != "" and
                                     byperiod[k]["total_revenue"] == ""):
                byperiod[k] = r

        for f in (d.get("filings_without_data") or []):
            # `formtype` (0/1/2) is the base form; `formtype_str` adds
            # ProPublica PDF annotations (O = with Schedule O, R = restated),
            # so normalize on the integer and keep the raw string alongside.
            ft = FORMTYPE.get(f.get("formtype"), "UNKNOWN")
            k = (f.get("tax_prd"), ft)
            if k in byperiod:
                if not byperiod[k]["pdf_url"] and f.get("pdf_url"):
                    byperiod[k]["pdf_url"] = f["pdf_url"]
                continue
            # also fill a pdf onto a same-period row of a different form label
            same = [kk for kk in byperiod if kk[0] == f.get("tax_prd")]
            if same:
                if not byperiod[same[0]]["pdf_url"] and f.get("pdf_url"):
                    byperiod[same[0]]["pdf_url"] = f["pdf_url"]
                continue
            r = dict(base)
            r.update({
                "ein": ein, "org_name": name,
                "tax_year": f.get("tax_prd_yr", ""),
                "tax_period": f.get("tax_prd", ""),
                "form_type": ft,
                "form_type_raw": f.get("formtype_str", ""),
                "has_financial_data": 0,
                "total_revenue": "", "total_expenses": "", "total_assets": "",
                "total_liabilities": "", "program_service_revenue": "",
                "contributions_grants": "", "net_assets_end": "",
                "officer_compensation": "",
                "lobbying_expenditure": "", "n_employees": "",
                "lobbying_indicator_990pf": "", "propaganda_indicator_990pf": "",
                "lobbying_field_basis": LOBBY_BASIS_OTHER,
                "n_employees_basis": EMP_BASIS,
                "pdf_url": f.get("pdf_url") or "",
                "retrieved_date": ret, "filing_updated": "",
            })
            byperiod[k] = r

        frows = sorted(byperiod.values(),
                       key=lambda r: (str(r["tax_period"]), str(r["form_type"])))
        rows.extend(frows)

        # ---- org-level scale row (latest year WITH financial data) ----
        withfin = [r for r in frows if r["has_financial_data"] == 1
                   and r["total_revenue"] != ""]
        latest = max(withfin, key=lambda r: str(r["tax_period"])) if withfin else None
        years = [int(r["tax_year"]) for r in frows if str(r["tax_year"]).isdigit()]
        o = dict(base)
        o.update({
            "ein": ein, "org_name": name, "api_status": "ok",
            "n_filings_returned": len(frows),
            "n_filings_with_financials": len(withfin),
            "first_filing_year": min(years) if years else "",
            "latest_filing_year": max(years) if years else "",
            "propublica_url": "https://projects.propublica.org/nonprofits/organizations/%s" % int(ein),
            "bmf_revenue_amt": m["bmf_revenue_amt"],
            "ntee_code": m["ntee_code"],
            "review_flag": m["review_flag"],
        })
        if latest:
            o.update({
                "latest_year": latest["tax_year"],
                "latest_form_type": latest["form_type"],
                "total_revenue": latest["total_revenue"],
                "total_expenses": latest["total_expenses"],
                "total_assets": latest["total_assets"],
                "total_liabilities": latest["total_liabilities"],
                "program_service_revenue": latest["program_service_revenue"],
                "contributions_grants": latest["contributions_grants"],
                "scale_band": band(latest["total_revenue"]),
                "scale_band_basis": "latest filing with parsed financials (tax_prd %s, form %s)"
                                    % (latest["tax_period"], latest["form_type"]),
            })
        else:
            o.update({
                "latest_year": "", "latest_form_type": "",
                "total_revenue": "", "total_expenses": "", "total_assets": "",
                "total_liabilities": "", "program_service_revenue": "",
                "contributions_grants": "",
                "scale_band": "none",
                "scale_band_basis": "no filing with parsed financials returned by the API",
            })
        org_rows.append(o)

    fin = pd.DataFrame(rows)
    for c in FIN_COLS:
        if c not in fin.columns:
            fin[c] = ""
    _yr = pd.to_numeric(fin["tax_year"], errors="coerce")
    fin["pre_2000_flag"] = (_yr < 2000).fillna(False).astype(int)
    fin = fin[FIN_COLS].sort_values(["ein", "tax_period", "form_type"])
    outf = os.path.join(ROOT, "data", "clean", "np_financials.csv")
    fin.to_csv(outf, index=False)
    log("[build] wrote %s  rows=%d  unique EIN=%d"
        % (outf, len(fin), fin.ein.nunique()))

    SCALE_COLS = ["ein", "org_name", "state", "confidence_tier", "bmf_990_tier",
                  "in_tier_a", "in_recheck_candidate", "in_placename_risk",
                  "api_status", "n_filings_returned", "n_filings_with_financials",
                  "first_filing_year", "latest_filing_year",
                  "latest_year", "latest_form_type",
                  "total_revenue", "total_expenses", "total_assets",
                  "total_liabilities", "program_service_revenue",
                  "contributions_grants",
                  "scale_band", "scale_band_basis",
                  "bmf_revenue_amt", "ntee_code", "review_flag",
                  "propublica_url", "source_dataset", "source_url",
                  "retrieved_date"]
    sc = pd.DataFrame(org_rows)
    for c in SCALE_COLS:
        if c not in sc.columns:
            sc[c] = ""
    sc["scale_band"] = sc["scale_band"].replace("", "none").fillna("none")
    sc = sc[SCALE_COLS].sort_values("ein")
    outs = os.path.join(ROOT, "data", "clean", "np_org_scale.csv")
    sc.to_csv(outs, index=False)
    log("[build] wrote %s  rows=%d" % (outs, len(sc)))
    log("[build] api status counts: %s" % status_counts)
    log("[build] lobbying-relevant fields present in ANY filing payload: %s"
        % sorted(k for k in key_union if "lobb" in k.lower() or k in
                 ("infleg", "propgndacd")))
    log("[build] employee-count fields present in ANY filing payload: %s"
        % sorted(k for k in key_union
                 if "empl" in k.lower() or k.endswith("cnt")))
    log("[build] 990-PF filings=%d  infleg!=N: %d  propgndacd!=N: %d"
        % (lobby_seen["pf_filings"], lobby_seen["infleg_Y"],
           lobby_seen["propgnda_Y"]))
    return fin, sc


def band(rev):
    if rev == "" or rev is None:
        return "none"
    try:
        v = float(rev)
    except (TypeError, ValueError):
        return "none"
    if v < 50_000:
        return "under_50k"
    if v < 1_000_000:
        return "50k_1m"
    if v < 10_000_000:
        return "1m_10m"
    if v < 100_000_000:
        return "10m_100m"
    return "over_100m"


# --------------------------------------------------------------------------
# step: report
# --------------------------------------------------------------------------
def step_report(fin, sc):
    fin = fin.copy()
    for c in ("lobbying_indicator_990pf", "propaganda_indicator_990pf",
              "lobbying_expenditure"):
        fin[c] = fin[c].fillna("").astype(str).replace("nan", "")

    def money(v):
        try:
            return "${:,.0f}".format(float(v))
        except (TypeError, ValueError):
            return "n/a"

    log("")
    log("========== COVERAGE ==========")
    log(sc.api_status.value_counts().to_string())
    log("")
    log("-- scale_band, all pulled EINs --")
    log(sc.scale_band.value_counts().to_string())
    log("")
    log("-- scale_band x pull set --")
    for setname, col in [("tier_A", "in_tier_a"),
                         ("recheck_candidate", "in_recheck_candidate"),
                         ("placename_risk", "in_placename_risk")]:
        sub = sc[sc[col] == 1]
        log("%s (n=%d):\n%s" % (setname, len(sub),
                                sub.scale_band.value_counts().to_string()))
        log("")
    log("-- filings by form type --")
    log(fin.form_type.value_counts().to_string())
    log("-- filings with parsed financials --")
    log(fin.has_financial_data.value_counts().to_string())
    log("-- tax_year range --")
    yr = pd.to_numeric(fin.tax_year, errors="coerce").dropna()
    log("min %d  max %d" % (yr.min(), yr.max()))
    log("")
    log("-- BMF 990 tier vs whether the API returned any financials --")
    sc2 = sc.copy()
    sc2["got_fin"] = (pd.to_numeric(sc2.n_filings_with_financials,
                                    errors="coerce").fillna(0) > 0)
    log(pd.crosstab(sc2.bmf_990_tier, sc2.got_fin).to_string())

    log("")
    log("========== PLACE-NAME RISK ORGS RANKED BY REVENUE ==========")
    pn = sc[sc.in_placename_risk == 1].copy()
    pn["rev"] = pd.to_numeric(pn.total_revenue, errors="coerce")
    pn = pn.sort_values("rev", ascending=False)
    tot = pn.rev.sum()
    log("n=%d, %d with revenue, combined latest-year revenue %s"
        % (len(pn), pn.rev.notna().sum(), money(tot)))
    log("")
    log("%-5s %-52s %-3s %-6s %14s %-10s" %
        ("rank", "org_name", "st", "year", "revenue", "band"))
    for i, (_, r) in enumerate(pn.head(40).iterrows(), 1):
        log("%-5d %-52s %-3s %-6s %14s %-10s" %
            (i, str(r.org_name)[:52], r.state, r.latest_year,
             money(r.total_revenue), r.scale_band))
    log("")
    log("-- concentration --")
    if pn.rev.notna().sum():
        for n in (1, 5, 10, 25):
            log("top %2d = %s (%.1f%% of the 412-org total)"
                % (n, money(pn.rev.head(n).sum()),
                   100 * pn.rev.head(n).sum() / tot if tot else 0))
    log("-- how many place-name orgs are financially trivial --")
    log(pn.scale_band.value_counts().to_string())

    log("")
    log("========== RECHECK CANDIDATES RANKED BY REVENUE ==========")
    rc = sc[sc.in_recheck_candidate == 1].copy()
    rc["rev"] = pd.to_numeric(rc.total_revenue, errors="coerce")
    rc = rc.sort_values("rev", ascending=False)
    for i, (_, r) in enumerate(rc.head(25).iterrows(), 1):
        log("%-4d %-52s %-3s %-6s %14s" %
            (i, str(r.org_name)[:52], r.state, r.latest_year,
             money(r.total_revenue)))
    log("")
    log("-- recheck scale bands --")
    log(rc.scale_band.value_counts().to_string())

    log("")
    log("========== LOBBYING DISCLOSURE ==========")
    nz = fin[pd.to_numeric(fin.lobbying_expenditure,
                           errors="coerce").fillna(0) > 0]
    log("filings with a non-zero lobbying_expenditure dollar amount: %d" % len(nz))
    log("orgs with a non-zero lobbying_expenditure dollar amount: %d"
        % nz.ein.nunique())
    pf = fin[fin.form_type == "990PF"]
    ind = pf[~pf.lobbying_indicator_990pf.isin(["", "N"])]
    log("990-PF filings pulled: %d; with infleg indicator != N: %d (orgs: %d)"
        % (len(pf), len(ind), ind.ein.nunique()))
    prop = pf[~pf.propaganda_indicator_990pf.isin(["", "N"])]
    log("990-PF filings with propgndacd != N: %d (orgs: %d)"
        % (len(prop), prop.ein.nunique()))
    if len(ind):
        log(ind[["ein", "org_name", "tax_year",
                 "lobbying_indicator_990pf"]].to_string(index=False))

    log("")
    log("========== WHAT THE PLACE-NAME PROBLEM COSTS THE TIER-A AGGREGATE ==========")
    log("NOT a publishable Native-nonprofit figure either way. Tier A is an "
        "unruled screened candidate set. This only sizes the contamination.")
    ta = sc[sc.in_tier_a == 1].copy()
    ta["rev"] = pd.to_numeric(ta.total_revenue, errors="coerce")
    tot_a = ta.rev.sum()
    contam = ta.loc[ta.in_placename_risk == 1, "rev"].sum()
    log("tier-A orgs with a latest-year revenue figure: %d of %d"
        % (ta.rev.notna().sum(), len(ta)))
    log("tier-A latest-year revenue, as pulled:            %s" % money(tot_a))
    log("  of which sits in place-name-risk orgs:          %s (%.1f%%)"
        % (money(contam), 100 * contam / tot_a if tot_a else 0))
    log("  remainder, still unruled:                       %s"
        % money(tot_a - contam))

    log("")
    log("========== LARGEST ORGS OVERALL (latest year) ==========")
    top = sc.copy()
    top["rev"] = pd.to_numeric(top.total_revenue, errors="coerce")
    top = top.dropna(subset=["rev"]).sort_values("rev", ascending=False)
    for i, (_, r) in enumerate(top.head(30).iterrows(), 1):
        tags = []
        if r.in_tier_a == 1:
            tags.append("A")
        if r.in_placename_risk == 1:
            tags.append("PLACENAME-RISK")
        if r.in_recheck_candidate == 1:
            tags.append("RECHECK")
        log("%-4d %-50s %-3s %-6s %14s  [%s]" %
            (i, str(r.org_name)[:50], r.state, r.latest_year,
             money(r.total_revenue), ",".join(tags)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", default="pull,build,report")
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    steps = [s.strip() for s in a.steps.split(",") if s.strip()]

    targets, meta, tier_a, recheck, placename = target_set()
    log("[targets] tier_A=%d recheck_candidate=%d placename_risk=%d union=%d"
        % (len(tier_a), len(recheck), len(placename), len(targets)))

    fin = sc = None
    if "pull" in steps:
        step_pull(targets, a.limit)
    if "build" in steps:
        fin, sc = step_build(targets, meta)
    if "report" in steps:
        if fin is None:
            fin = pd.read_csv(os.path.join(ROOT, "data", "clean",
                                           "np_financials.csv"), dtype=str)
            sc = pd.read_csv(os.path.join(ROOT, "data", "clean",
                                          "np_org_scale.csv"), dtype=str)
            for c in ("in_tier_a", "in_recheck_candidate", "in_placename_risk"):
                sc[c] = pd.to_numeric(sc[c], errors="coerce").fillna(0).astype(int)
                fin[c] = pd.to_numeric(fin[c], errors="coerce").fillna(0).astype(int)
            fin["has_financial_data"] = pd.to_numeric(
                fin["has_financial_data"], errors="coerce").fillna(0).astype(int)
        step_report(fin, sc)
    log("[done]")


if __name__ == "__main__":
    sys.exit(main() or 0)
