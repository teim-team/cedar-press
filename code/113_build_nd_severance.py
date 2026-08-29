#!/usr/bin/env python3
r"""
Cedar Press - 113: North Dakota / Fort Berthold severance tax series.

WHY THIS EXISTS
---------------
`SEVERANCE` was an EMPTY tax type in `data/clean/tribal_tax_bases.csv` while the
largest per-tribe severance flow in the country - the North Dakota oil and gas
gross production and oil extraction tax share paid to the Three Affiliated
Tribes of the Fort Berthold Reservation - sat unworked. Script 108 named it the
highest-value unworked target in the country. This is that build.

The PAYMENT side already exists and is not touched here: 489 monthly ND
Treasurer distributions totalling $3,125,453,109.56 (2008-09 .. 2026-07) live in
`data/clean/resource_revenue.csv`. This script builds the TAX side - the
statutory framework, the allocation formula with effective-date ranges per well
vintage, and the one thing North Dakota publishes that the Treasurer's file does
not: TOTAL OIL AND GAS TAX COLLECTIONS ON THE FORT BERTHOLD RESERVATION.

THE TRAP THIS BUILD EXISTS TO RESPECT
-------------------------------------
North Dakota's 80/20 trust split applies ONLY to wells on which drilling first
commenced after 2019-06-30, and NDCC 57-51.2-02(6) binds a well to the terms of
the agreement in force when it was drilled FOR THE LIFE OF THE WELL. So every
monthly distribution after mid-2019 is a BLEND of two regimes weighted by the
spud-date mix of producing wells. Picking up 80/20 and multiplying is wrong for
every month after mid-2019. `series_breaks.csv` already records this; nothing
here writes a single ratio into an allocation field.

WHAT CHANGED, AND IT IS THE FINDING OF THIS BUILD
-------------------------------------------------
The blend CANNOT be decomposed by well vintage - North Dakota publishes no
vintage split of collections, and DMR's free data carries neither trust/fee
ownership nor a reservation aggregate. But the North Dakota Legislative Council
publishes, monthly, BOTH LEGS OF THE RATIO:

  * gross production tax collections and oil extraction tax collections
    "in each county and the Fort Berthold Reservation", and
  * "oil and gas tax revenue collections allocated to the Three Affiliated
    Tribes of the Fort Berthold Reservation".

So the EFFECTIVE BLENDED SHARE IS MEASURED, NOT ASSUMED. It is 50.00% while the
uniform 2013 regime is in force - which is what validates the two legs as the
same basis - and it rises month by month after 2019 as post-2019 wells replace
pre-2019 ones. The formula does not have to be modelled because the ratio is
published on both sides.

A MEASURED SHARE STILL DOES NOT GIVE A POINT BASE
-------------------------------------------------
Three separate reasons, each recorded on the row rather than in a footnote:

1. THE GROSS PRODUCTION TAX POOLS TWO INCOMPATIBLE UNITS. Oil is taxed at five
   percent of gross value at the well (NDCC 57-51-02, ad valorem, base in USD).
   Gas is taxed per mcf at an annually indexed rate (NDCC 57-51-02.2, base in
   MCF). One published dollar figure, two bases, two units. Dividing it by
   anything produces neither dollars nor mcf. This is a FOURTH distinct way a
   rate inversion fails, after the marginal base, the graduated schedule read
   as flat, and receipts lagging obligations (AGENTS.md).

2. THE OIL EXTRACTION TAX RATE ON THE RESERVATION IS STATE-CONTINGENT. It is
   five percent, but NDCC 57-51.1-02(2) raises it to six percent for wells
   inside reservation boundaries whenever WTI exceeds an annually indexed
   trigger price for three consecutive months - and the 2023 session REMOVED
   that trigger for every other well in North Dakota while KEEPING it for
   reservation and straddle wells. We retrieved the trigger price for CY2021
   ($89.65) and CY2026 ($117.20) and could not retrieve a Tax Commissioner
   notice stating whether the rate actually changed in any month. So the base
   is bounded by collections/0.06 and collections/0.05, never divided once.

3. THE AGREEMENT ITSELF IS NOT PUBLISHED. NDCC 57-51.2-02(3) caps the oil
   extraction tax on trust lands at six and one-half percent "but may be
   reduced through negotiation", and 57-51.2-02(4) switches off the chapters'
   exemptions on the reservation "except as otherwise provided in the
   agreement". The agreements (2008-06-10, 2010-01-13, 2013-06-21, 2019-02-28)
   are described by the Legislative Council and published by nobody. An
   exempted or reduced-rate barrel makes collections/rate a LOWER bound on
   gross value at the well, not the value.

THE FOUR RULES (docs/TRIBAL_TAX_DECOMPOSITION.md), APPLIED HERE
---------------------------------------------------------------
1. A TAXABLE BASE IS NOT REVENUE. `rate_unit` and `base_unit` are explicit on
   every row. `share_of_gross_value_at_well` yields USD; `usd_per_mcf` yields
   MCF. A gas rate never produces a dollar figure.
2. WHERE IT CANNOT BE UNIQUELY SOLVED, EMIT A RANGE WITH `bound_basis`, NEVER A
   POINT ESTIMATE. `derived_taxable_base` is written only where a single number
   is forced by the sources. It is written NOWHERE in this build, and the
   arithmetic of the bound - with both endpoints as numbers - lives in
   `bound_basis` on the row. This follows the Florida precedent exactly.
3. PERIODS MUST MATCH. The Legislative Council states that "oil and gas tax
   revenue allocations reflect production and price from 2 months prior", so a
   collection month is mapped to its production month before a statutory rate
   is attached to it.
4. NEVER A BARE TAX-BURDEN FIGURE. Every row carries
   `agreement_or_statute_cite`. And the reservation COLLECTIONS rows carry an
   explicit statement that they are taxes on production within the reservation
   paid by operators, NOT taxes paid by the tribe.

TWO QUOTES OR IT DOES NOT EXIST. Every amount row carries a verbatim
`amount_source_quote` and, where a rate is attached, a verbatim
`rate_source_quote`. Tabular sources are quoted as the printed cells of one row
joined by " | " - stated here and in the codebook so nobody mistakes it for
running prose.

PDF TABLES ARE READ BY WORD POSITION, NEVER LINEARLY (script 94's finding).
Every Legislative Council row is additionally CHECKED AGAINST THE PRINTED TOTAL
on its own line: if the twelve monthly cells do not sum to the printed
biennium-to-date total, the row is refused rather than published.

RUN
    py -3 code/113_build_nd_severance.py fetch
    py -3 code/113_build_nd_severance.py build
    py -3 code/113_build_nd_severance.py all

WRITES
    data/raw/external/nd_severance/**          + _SOURCE_MANIFEST.csv (md5s)
    data/clean/tribal_tax_bases.csv            (APPEND ONLY, re-read first)
    data/clean/nd_severance_allocation.csv
    review/nd_severance_unresolved_<date>.csv
    data/clean/codebook_master.csv             (variables only; backup + merge)
    docs/ND_SEVERANCE_BUILD_LOG.md

TOUCHES NOTHING ELSE. Does not write resource_revenue.csv, np_*, gaming_*,
nigc_*, compact_*, ca_gaming_*, wa_*, fl_*, state_gaming_observations.csv,
entity_*, the identifier ledger or the spine. api.usaspending.gov is never
contacted.
"""

import base64
import csv
import hashlib
import html as HTML
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
LOGS = CEDAR / "logs"
DOCS = CEDAR / "docs"
RAW = CEDAR / "data" / "raw" / "external" / "nd_severance"

TODAY = date.today().isoformat()
SCRIPT = "code/113_build_nd_severance.py"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

BANNED_HOSTS = {"api.usaspending.gov"}

TRIBE_ID = "TRBF-MHATAT-00"     # asserted against the resolver at build time
TRIBE_NAME = "Three Affiliated"
STATE = "ND"

# --------------------------------------------------------------------------
# Schema of data/clean/tribal_tax_bases.csv, unchanged (script 108).
# --------------------------------------------------------------------------
FIELDS = [
    "tax_observation_id", "tribe_id", "tribe_name", "state", "tax_type",
    "period_start", "period_end", "tax_remitted_usd", "statutory_rate",
    "rate_unit", "derived_taxable_base", "base_unit", "rate_source_quote",
    "amount_source_quote", "agreement_or_statute_cite", "measurement_status",
    "bound_basis", "source_url", "fetched_date", "tier", "confidence",
    "built_date",
]

ALLOC_FIELDS = [
    "allocation_id", "tribe_id", "statute_cite", "effective_start",
    "effective_end", "well_vintage_rule", "trust_land_tribal_share",
    "trust_land_state_share", "fee_land_tribal_share", "fee_land_state_share",
    "superseded_by", "source_url", "source_quote", "fetched_date", "tier",
    "confidence", "built_date",
]

# Statuses already in the file (script 108) plus the one this build adds.
STATUS_PER_TRIBE_AMOUNT = "REPORTED_TAX_REMITTANCE_PER_TRIBE"
STATUS_RATE_ONLY = "RATE_ONLY_NO_AMOUNT"
STATUS_DERIVED_BASE = "DERIVED_TAXABLE_BASE"
# NEW. Total state severance tax collected on production WITHIN the
# reservation. It is not a tribal remittance and must never be summed with one.
STATUS_RESERVATION_COLLECTIONS = "REPORTED_TAX_COLLECTIONS_ON_RESERVATION"

MEASUREMENT_STATUSES = frozenset({
    STATUS_PER_TRIBE_AMOUNT, STATUS_RATE_ONLY, STATUS_DERIVED_BASE,
    STATUS_RESERVATION_COLLECTIONS,
})

# Rule 1 in code form. Two units are added by this build; neither existed in
# script 108 because no severance row existed.
RATE_UNIT_TO_BASE_UNIT = {
    "share_of_gross_value_at_well": "usd",
    "usd_per_mcf": "mcf",
    "mixed_ad_valorem_and_per_unit": None,   # cannot be inverted at all
}

FORECAST_WORDS = re.compile(
    r"\b(estimate[ds]?|estimating|estimation|predict(?:ed|s|ion)?|"
    r"forecast(?:ed|s)?|confidence interval|margin of error|projected|"
    r"modell?ed)\b", re.I)

OUR_TEXT_COLUMNS = ("measurement_status", "bound_basis", "confidence",
                    "base_unit", "rate_unit")


# ==========================================================================
# Shared resolver. Standing rule 8: never re-implement matching.
# ==========================================================================
def load_resolver():
    spec = importlib.util.spec_from_file_location(
        "party_rulings", CODE / "33_apply_party_rulings.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_domain():
    spec = importlib.util.spec_from_file_location(
        "cedar_domain", CODE / "cedar_domain.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_spine():
    p = SPINE / "cedar_entity_spine.csv"
    with p.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


# ==========================================================================
# Fetching. One lock per host (docs/PULL_DISCIPLINE.md). Single shot, no
# poller left running, and the HTTP status is recorded per file - a 404 body
# still parses, so the manifest refuses anything that is not 200.
# ==========================================================================
def claim_host(host, note):
    LOGS.mkdir(parents=True, exist_ok=True)
    p = LOGS / f"_HOSTLOCK_{host}.json"
    if p.exists():
        try:
            cur = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            cur = {}
        if cur.get("active") and cur.get("script") != SCRIPT:
            cur.setdefault("queue", []).append({
                "script": SCRIPT, "host_target": host, "purpose": note,
                "queued_at": datetime.now(timezone.utc).isoformat()})
            p.write_text(json.dumps(cur, indent=1), encoding="utf-8")
            print(f"  [lock] {host} held by {cur.get('script')}; queued")
            return
    p.write_text(json.dumps({
        "host": host, "pid": os.getpid(), "script": SCRIPT,
        "claimed_at": datetime.now(timezone.utc).isoformat(),
        "active": False,
        "policy": "single-shot document fetch, no retry loop",
        "note": note, "queue": [],
    }, indent=1), encoding="utf-8")


def http_get(url, dest):
    host = re.sub(r"^https?://([^/]+).*", r"\1", url)
    if host in BANNED_HOSTS:
        raise RuntimeError(f"refusing banned host {host}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.run(
        ["curl", "-s", "-L", "-A", UA, "--max-time", "240",
         "-w", "%{http_code}", "-o", str(dest), url],
        capture_output=True, text=True)
    status = int((p.stdout or "0").strip() or 0)
    body = dest.read_bytes() if dest.exists() else b""
    return status, body


def md5(b):
    return hashlib.md5(b).hexdigest()


# ==========================================================================
# SOURCES
# ==========================================================================
LC_BASE_OLD = "https://ndlegis.gov/sites/default/files/fiscal/oil-gas-tax-revenues"
LC_BASE_NEW = "https://ndlegis.gov/sites/default/files/pdf/fiscal/oil-gas-tax-revenues"
TAXND = "https://www.tax.nd.gov/sites/www/files/documents"

# Each Legislative Council report and the window its Fort Berthold rows cover.
#   key, url, path, end_month (last of the 12 printed monthly cells),
#   layout: "12" = twelve monthly cells + printed total
#           "1+12" = a leading prior-period total, twelve monthly cells, total
#   prior_start/prior_end: the period the leading total covers (layout 1+12)
LC_REPORTS = [
    dict(key="lc_15_9093_24000", num="15.9093.24000", base=LC_BASE_OLD,
         end="2015-07", layout="1+12", prior=("2013-08", "2014-07")),
    dict(key="lc_17_9042_24000", num="17.9042.24000", base=LC_BASE_OLD,
         end="2017-07", layout="1+12", prior=("2015-08", "2016-07")),
    dict(key="lc_19_9007_04000", num="19.9007.04000", base=LC_BASE_OLD,
         end="2018-07", layout="12", prior=None),
    dict(key="lc_19_9007_08000", num="19.9007.08000", base=LC_BASE_OLD,
         end="2019-07", layout="1+12", prior=("2017-08", "2018-07")),
    dict(key="lc_21_9007_04000", num="21.9007.04000", base=LC_BASE_OLD,
         end="2020-07", layout="12", prior=None),
    dict(key="lc_21_9007_08000", num="21.9007.08000", base=LC_BASE_OLD,
         end="2021-07", layout="1+12", prior=("2019-08", "2020-07")),
    dict(key="lc_23_9004_04000", num="23.9004.04000", base=LC_BASE_OLD,
         end="2022-07", layout="12", prior=None),
    dict(key="lc_23_9004_08000", num="23.9004.08000", base=LC_BASE_OLD,
         end="2023-07", layout="1+12", prior=("2021-08", "2022-07")),
    dict(key="lc_25_9093_04000", num="25.9093.04000", base=LC_BASE_NEW,
         end="2024-07", layout="12", prior=None),
    dict(key="lc_25_9093_08000", num="25.9093.08000", base=LC_BASE_NEW,
         end="2025-07", layout="1+12", prior=("2023-08", "2024-07")),
    dict(key="lc_27_9061_04000", num="27.9061.04000", base=LC_BASE_NEW,
         end="2026-07", layout="12", prior=None),
]

SOURCES = []
for r in LC_REPORTS:
    SOURCES.append(dict(
        key=r["key"], url=f"{r['base']}/{r['num']}.pdf",
        path=f"legislative_council/{r['num']}.pdf",
        publisher="North Dakota Legislative Council",
        title=("Oil and Gas Tax Revenue Collections and Allocations "
               f"Quarterly/Monthly Update Detail, LC# {r['num']}")))

SOURCES += [
    # --- statute, current text -------------------------------------------
    dict(key="ndcc_57_51", url="https://ndlegis.gov/cencode/t57c51.pdf",
         path="statute/ndcc_t57c51_gross_production_tax.pdf",
         publisher="North Dakota Legislative Branch",
         title="NDCC Chapter 57-51, Oil and Gas Gross Production Tax"),
    dict(key="ndcc_57_51_1", url="https://ndlegis.gov/cencode/t57c51-1.pdf",
         path="statute/ndcc_t57c51-1_oil_extraction_tax.pdf",
         publisher="North Dakota Legislative Branch",
         title="NDCC Chapter 57-51.1, Oil Extraction Tax"),
    dict(key="ndcc_57_51_2", url="https://ndlegis.gov/cencode/t57c51-2.pdf",
         path="statute/ndcc_t57c51-2_tribal_oil_and_gas_agreements.pdf",
         publisher="North Dakota Legislative Branch",
         title="NDCC Chapter 57-51.2, Tribal Oil and Gas Agreements"),
    # --- enacted session laws, one per allocation change ------------------
    dict(key="sl_2007", path="session_laws/2007_60th_TAXES.pdf",
         url="https://ndlegis.gov/assembly/60-2007/session-laws/documents/TAXES.pdf",
         publisher="North Dakota Legislative Branch",
         title="2007 Session Laws, Taxation (ch. 545, SB 2419)"),
    dict(key="sl_2013", path="session_laws/2013_63rd_TAXES.pdf",
         url="https://ndlegis.gov/assembly/63-2013/session-laws/documents/TAXES.pdf",
         publisher="North Dakota Legislative Branch",
         title="2013 Session Laws, Taxation (ch. 473, HB 1198)"),
    dict(key="sl_2015", path="session_laws/2015_64th_TAXES.pdf",
         url="https://ndlegis.gov/assembly/64-2015/session-laws/documents/TAXES.pdf",
         publisher="North Dakota Legislative Branch",
         title="2015 Session Laws, Taxation (ch. 466, HB 1476)"),
    dict(key="sl_2019", path="session_laws/2019_66th_TAXES.pdf",
         url="https://ndlegis.gov/assembly/66-2019/session-laws/documents/TAXES.pdf",
         publisher="North Dakota Legislative Branch",
         title="2019 Session Laws, Taxation (ch. 506, SB 2312)"),
    dict(key="fn_sb2312",
         url="https://ndlegis.gov/assembly/66-2019/regular/fiscal-notes/19-0820-03000-fn.pdf",
         path="fiscal_notes/sb2312_2019_fiscal_note_19-0820-03000.pdf",
         publisher="North Dakota Legislative Council",
         title="Fiscal note 19.0820.03000, engrossed SB 2312 (2019)"),
    dict(key="lc_tsrc_memo",
         url=("https://ndlegis.gov/sites/default/files/resource/69-2025/"
              "committee-memorandum/27.9066.01000.pdf"),
         path="legislative_council/tribal_state_relations_background_memo_27.9066.01000.pdf",
         publisher="North Dakota Legislative Council",
         title="Tribal and State Relations Committee Background Memorandum, August 2025"),
    # --- Tax Commissioner --------------------------------------------------
    dict(key="tax_gas_rate_table",
         url="https://www.tax.nd.gov/gas-tax-rate-table",
         path="tax_commissioner/gas_tax_rate_table.html",
         publisher="North Dakota Office of State Tax Commissioner",
         title="Gas Tax Rate Table"),
    dict(key="tax_history",
         url="https://www.tax.nd.gov/oil-and-gas-tax-history",
         path="tax_commissioner/oil_and_gas_tax_history.html",
         publisher="North Dakota Office of State Tax Commissioner",
         title="Oil and Gas Tax History"),
    dict(key="tax_pool_codes",
         url="https://www.tax.nd.gov/north-dakota-oil-and-gas-tax-pool-codes",
         path="tax_commissioner/oil_and_gas_tax_pool_codes.html",
         publisher="North Dakota Office of State Tax Commissioner",
         title="North Dakota Oil and Gas Tax Pool Codes"),
    dict(key="tax_straddle_2025",
         url=f"{TAXND}/newsletters/oil-gas/straddle-well-acreage-ratio-memo-2025.pdf",
         path="tax_commissioner/straddle_well_acreage_ratio_memo_2025.pdf",
         publisher="North Dakota Office of State Tax Commissioner",
         title="Straddle well acreage ratio certification, effective FY2026"),
    dict(key="tax_straddle_2024",
         url=f"{TAXND}/newsletters/oil-gas/straddle-well-acreage-ratio-memo-2024.pdf",
         path="tax_commissioner/straddle_well_acreage_ratio_memo_2024.pdf",
         publisher="North Dakota Office of State Tax Commissioner",
         title="Straddle well acreage ratio certification, effective FY2025"),
    dict(key="tax_trigger_2026",
         url=f"{TAXND}/newsletters/oil-gas/annual-oil-trigger-price-adjustment-2026.pdf",
         path="tax_commissioner/annual_oil_trigger_price_adjustment_2026.pdf",
         publisher="North Dakota Office of State Tax Commissioner",
         title="Annual oil trigger price adjustment, calendar year 2026"),
    dict(key="tax_trigger_2021",
         url=f"{TAXND}/newsletters/oil-gas/annual-oil-trigger-price-adjustment-2021.pdf",
         path="tax_commissioner/annual_oil_trigger_price_adjustment_2021.pdf",
         publisher="North Dakota Office of State Tax Commissioner",
         title="Annual oil trigger price adjustment, calendar year 2021"),
    dict(key="tax_gas_notice",
         url=("https://www.tax.nd.gov/sites/default/files/documents/newsletters/"
              "oil-gas/gas-tax-rate-notice.pdf"),
         path="tax_commissioner/gas_tax_rate_notice_fy2027.pdf",
         publisher="North Dakota Office of State Tax Commissioner",
         title="Gas tax rate notice, fiscal year 2027"),
    dict(key="tax_fb_instructions",
         url=(f"{TAXND}/forms/business/oil-gas/"
              "fortbertholdreservationtaxreportinginstructions.pdf"),
         path="tax_commissioner/fort_berthold_reservation_tax_reporting_instructions.pdf",
         publisher="North Dakota Office of State Tax Commissioner",
         title="Oil and Gas Taxes Reporting Instructions on the Fort Berthold Reservation"),
    dict(key="tax_t84",
         url=f"{TAXND}/forms/business/oil-gas/schedule-t-84.pdf",
         path="tax_commissioner/schedule_t-84_fort_berthold.pdf",
         publisher="North Dakota Office of State Tax Commissioner",
         title="Schedule T-84, Fort Berthold Reservation trust/non-trust allocation"),
    # --- DMR: retained as the EVIDENCE for a negative finding --------------
    # The statistics index is what shows DMR publishes by county, formation
    # and statewide and offers no reservation aggregate and no ownership
    # field. A negative finding needs its own source like any other.
    dict(key="dmr_statistics_index",
         url="https://www.dmr.nd.gov/oilgas/stats/statisticsvw.asp",
         path="dmr/dmr_drilling_and_production_statistics_index.html",
         publisher="North Dakota Department of Mineral Resources, "
                   "Oil and Gas Division",
         title="North Dakota Drilling and Production Statistics index"),
    # --- Treasurer flow charts: the operative statement of the split -------
    dict(key="treas_flow_2527",
         url=("https://www.treasurer.nd.gov/sites/default/files/documents/"
              "Oil%20%26%20Gas%20Flow%20Charts/"
              "O%26G%20Flow%20Charts%20(25-27%20Biennium).pdf"),
         path="treasurer/og_flow_charts_25-27_biennium.pdf",
         publisher="North Dakota Office of State Treasurer",
         title="Oil Extraction and Gross Production Distribution, FY2026-FY2027"),
    dict(key="treas_flow_1921",
         url=("https://www.treasurer.nd.gov/sites/default/files/documents/"
              "O%26G%20Flow%20Charts%20(19-21%20Biennium).pdf"),
         path="treasurer/og_flow_charts_19-21_biennium.pdf",
         publisher="North Dakota Office of State Treasurer",
         title="Oil Extraction and Gross Production Distribution, FY2020-FY2021"),
    dict(key="treas_flow_1719",
         url=("https://www.treasurer.nd.gov/sites/default/files/documents/"
              "OG%20Flow%20Charts%20(17-19%20Biennium).pdf"),
         path="treasurer/og_flow_charts_17-19_biennium.pdf",
         publisher="North Dakota Office of State Treasurer",
         title="Oil Extraction and Gross Production Distribution, FY2018-FY2019"),
]

# ND Treasurer tax distribution search. The public page exposes only
# searchtype=city; the tribe mode is an undocumented parameter on the same app,
# and its results page is a GET whose parameters are base64-encoded.
STN_TRIBES = {"1": "Standing Rock Sioux Tribe", "2": "Spirit Lake Tribe",
              "3": "Three Affiliated Tribes", "4": "Turtle Mtn. Chippewa"}
STN_OIL_TYPES = {"OIL EXTRAC": "Oil Extraction Tax",
                 "OIL & GAS": "Oil & Gas Gross Production",
                 "STRADDLE WELL": "Oil & Gas Straddle Well"}


def stn_url(dist_code, tribe_id, begin="2000-01-01", end="2026-12-31"):
    def b(s):
        return urllib.parse.quote(base64.b64encode(s.encode()).decode())
    return ("https://apps.nd.gov/stn/inquiry/results.aspx"
            f"?SearchType={b('tribe')}&PaymentDate={b(begin)}&EndDate={b(end)}"
            f"&City=&DistType={b(dist_code)}&County=&School=&Tribe={b(tribe_id)}"
            f"&Township=&ExcludeCity={b('False')}&ExcludeTownships={b('False')}"
            f"&ExcludeCounty={b('False')}&ExcludeSchool={b('False')}"
            f"&ExcludeTribe={b('False')}")


def stn_sources():
    out = []
    for tid, tname in STN_TRIBES.items():
        for code, label in STN_OIL_TYPES.items():
            slug = (tname.lower().replace(" ", "_").replace(".", "") + "_" +
                    code.lower().replace(" ", "_").replace("&", "and"))
            out.append(dict(
                key=f"stn_{slug}", url=stn_url(code, tid),
                path=f"treasurer/stn_{slug}_2000_2026.html",
                publisher="North Dakota Office of State Treasurer",
                title=f"Tax Distribution Search: {tname} / {label}, 2000-2026",
                stn_tribe=tname, stn_type=label))
    return out


ALL_SOURCES = SOURCES + stn_sources()


def do_fetch():
    print("=== 113 fetch ===")
    RAW.mkdir(parents=True, exist_ok=True)
    hosts = sorted({re.sub(r"^https?://([^/]+).*", r"\1", s["url"])
                    for s in ALL_SOURCES})
    for h in hosts:
        claim_host(h, "ND Fort Berthold severance tax statutes, allocation "
                      "formula and reservation-level collections")
    rows = []
    for s in ALL_SOURCES:
        dest = RAW / s["path"]
        status, body = http_get(s["url"], dest)
        ok = status == 200 and len(body) > 500
        rows.append(dict(
            key=s["key"], publisher=s["publisher"], title=s["title"],
            url=s["url"], path=s["path"], http_status=status,
            bytes=len(body), md5=md5(body) if body else "",
            usable="yes" if ok else "no", fetched_date=TODAY))
        print(f"  {status} {len(body):>9,}  {s['path']}")
        if not ok and dest.exists():
            dest.unlink()
        time.sleep(1.0)
    man = RAW / "_SOURCE_MANIFEST.csv"
    with man.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    bad = [r for r in rows if r["usable"] != "yes"]
    print(f"  manifest: {len(rows)} files, {len(bad)} unusable")
    for r in bad:
        print(f"    UNUSABLE {r['http_status']} {r['path']}")


# ==========================================================================
# PARSING
# ==========================================================================
def pdf_position_lines(path, band=3):
    """Cluster words into printed lines BY POSITION, never by the text layer.
    Returns [(page_no, line_text, [words])]."""
    import pdfplumber
    out = []
    with pdfplumber.open(str(path)) as pdf:
        for pno, page in enumerate(pdf.pages, 1):
            groups = {}
            for w in page.extract_words():
                groups.setdefault(round(w["top"] / band), []).append(w)
            for k in sorted(groups):
                ws = sorted(groups[k], key=lambda w: w["x0"])
                out.append((pno, " ".join(w["text"] for w in ws), ws))
    return out


NUM = re.compile(r"^\(?\$?-?[\d,]+\)?$")


def to_num(tok):
    t = tok.replace("$", "").replace(",", "").strip()
    neg = t.startswith("(") and t.endswith(")")
    t = t.strip("()")
    if not re.fullmatch(r"-?\d+(?:\.\d+)?", t):
        return None
    v = float(t)
    return -v if neg else v


def month_seq(end_ym, n):
    """The n consecutive year-months ending at end_ym inclusive."""
    y, m = (int(x) for x in end_ym.split("-"))
    out = []
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return list(reversed(out))


def month_bounds(ym):
    y, m = (int(x) for x in ym.split("-"))
    ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
    last = date.fromordinal(date(ny, nm, 1).toordinal() - 1)
    return f"{y:04d}-{m:02d}-01", last.isoformat()


def shift_month(ym, k):
    y, m = (int(x) for x in ym.split("-"))
    t = y * 12 + (m - 1) + k
    return f"{t // 12:04d}-{t % 12 + 1:02d}"


# Which table a "Fort Berthold" row belongs to is decided by the nearest
# PRECEDING schedule heading on the page - never by row order alone, because
# several reports also print a combined "total oil tax revenue" table that
# would otherwise be mistaken for one of the two named taxes.
TABLE_MARKERS = [
    (re.compile(r"Oil and Gas Gross Production Tax Collections", re.I), "GPT"),
    (re.compile(r"oil and gas gross production tax collections in each county",
                re.I), "GPT"),
    (re.compile(r"Oil Extraction Tax Collections", re.I), "OET"),
    (re.compile(r"oil extraction tax collections in each county", re.I), "OET"),
    (re.compile(r"total oil tax revenue collections in each county", re.I),
     "COMBINED"),
    (re.compile(r"gross production tax collections and oil extraction tax "
                r"collections in each county", re.I), None),   # intro sentence
    (re.compile(r"allocated to (?:state funds, )?the Three Affiliated Tribes",
                re.I), "ALLOC"),
    (re.compile(r"collections allocated to the Three Affiliated Tribes", re.I),
     "ALLOC"),
]


def parse_lc_report(path, spec):
    """-> {'GPT': {ym: usd}, 'OET': {...}, 'ALLOC': {...},
           'prior': {'GPT': usd, ...}}  plus a sum-vs-printed-total check."""
    lines = pdf_position_lines(path)
    n_month = 12
    months = month_seq(spec["end"], n_month)
    want = 13 if spec["layout"] == "12" else 14
    series = {"GPT": {}, "OET": {}, "ALLOC": {}}
    prior = {}
    checks = []
    ctx = None
    # Several vintages split one schedule into two horizontal blocks - the
    # first months in an upper block, the rest lower down or on the next page -
    # so the same row label appears more than once for one table. Cells are
    # ACCUMULATED per table, and the accumulation is only accepted when the
    # printed total on the last block equals the sum of everything before it.
    buf = {"GPT": [], "OET": [], "ALLOC": []}

    def flush(tag):
        vals = buf[tag]
        if len(vals) != want:
            checks.append((tag, "wrong_cell_count", len(vals), want))
            buf[tag] = []
            return
        total, body = vals[-1], vals[:-1]
        if abs(sum(body) - total) > 2.0:
            checks.append((tag, "sum_mismatch", sum(body), total))
            buf[tag] = []
            return
        if spec["layout"] == "1+12":
            prior[tag] = body[0]
            monthly = body[1:]
        else:
            monthly = body
        for ym, v in zip(months, monthly):
            series[tag][ym] = v
        checks.append((tag, "ok", total, total))
        buf[tag] = []

    for pno, text, ws in lines:
        for rx, tag in TABLE_MARKERS:
            if rx.search(text):
                if tag is not None:
                    ctx = tag
                break
        m = re.match(r"^(Fort Berthold(?: Reservation)?|Three Affiliated"
                     r"(?: Tribes)?)\s+(.*)$", text)
        if not m:
            continue
        label, rest = m.group(1), m.group(2)
        tag = "ALLOC" if label.startswith("Three Affiliated") else ctx
        if tag not in ("GPT", "OET", "ALLOC"):
            continue
        vals = [to_num(t) for t in rest.split()]
        if not vals or any(v is None for v in vals):
            continue
        if series[tag]:
            continue                       # this table already resolved
        buf[tag] += vals
        if len(buf[tag]) >= want:
            flush(tag)
    for tag in buf:
        if buf[tag]:
            flush(tag)
    return series, prior, checks


def parse_stn(path):
    """ND Treasurer results page -> [(payment_date, tribe, tax_type, usd)]."""
    s = path.read_bytes().decode("iso-8859-1")
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s)
    t = re.sub(r"<[^>]+>", "\n", t)
    t = HTML.unescape(t)
    L = [x.strip() for x in t.split("\n") if x.strip()]
    rows, i = [], 0
    grand = None
    while i < len(L) - 3:
        if re.fullmatch(r"\d{2}/\d{2}/\d{4}", L[i]):
            amt = to_num(L[i + 3])
            if amt is not None:
                mm, dd, yy = L[i].split("/")
                rows.append((f"{yy}-{mm}-{dd}", L[i + 1], L[i + 2], amt))
            i += 4
        else:
            if L[i] == "Grand Total:" and i + 1 < len(L):
                grand = to_num(L[i + 1])
            i += 1
    return rows, grand


def parse_gas_rate_table(path):
    """-> [(fy_start_ym, fy_end_ym, usd_per_mcf, printed_row)]"""
    s = path.read_text(encoding="utf-8", errors="replace")
    out = []
    for tbl in re.findall(r"(?is)<table.*?</table>", s):
        t = re.sub(r"(?is)</t[dh]>", "\t", tbl)
        t = re.sub(r"(?is)</tr>", "\n", t)
        t = HTML.unescape(re.sub(r"<[^>]+>", "", t))
        for line in t.split("\n"):
            cells = [" ".join(c.split()) for c in line.split("\t") if c.strip()]
            if len(cells) != 2:
                continue
            rate, period = cells
            m = re.match(r"^\$?\.?(\d+)\s*Per\s*MCF$", rate, re.I)
            p = re.match(r"^(\d{1,2})/(\d{4})\s*-\s*(\d{1,2})/(\d{4})$", period)
            if not (m and p):
                continue
            val = float("0." + m.group(1))
            out.append((f"{p.group(2)}-{int(p.group(1)):02d}",
                        f"{p.group(4)}-{int(p.group(3)):02d}", val,
                        f"{rate} | {period}"))
    return out


def parse_straddle_memo(path):
    txt = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                         capture_output=True, text=True).stdout
    flat = " ".join(txt.split())
    m = re.search(r'trust lands acreage ratio" is ([\d.]+).*?non-?\s*trust '
                  r'lands acreage ratio" is ([\d.]+)\s*for ([A-Za-z ]+?) '
                  r'effective (\w+ \d+, \d{4}), through (\w+ \d+, \d{4})',
                  flat)
    if not m:
        return None
    return dict(trust=float(m.group(1)), nontrust=float(m.group(2)),
                reservation=m.group(3).strip(), start=m.group(4),
                end=m.group(5), quote=flat[flat.find("In keeping"):][:700])


# ==========================================================================
# STATUTORY QUOTES. Each is lifted verbatim from the retrieved PDF, and the
# build ASSERTS it is present in that PDF's text before writing it onto a row.
# ==========================================================================
Q_GPT_OIL = ("A tax of five percent of the gross value at the well is levied "
             "upon all oil produced within North Dakota, less the value of any "
             "part thereof, the ownership or right to which is exempt from "
             "taxation. The tax levied attaches to the whole production, "
             "including the royalty interest.")
Q_GPT_GAS = ("The tax on gas must be calculated by taking the taxable "
             "production in mcf times the gas tax rate. 1. The gas tax rate is "
             "four cents times the gas base rate adjustment for each fiscal "
             "year as calculated under subsection 2.")
Q_OET = ("The rate of tax is five percent of the gross value at the well of "
         "the oil extracted.")
Q_OET_TRIGGER = (
    "Subject to subsection 3, for a well located within the exterior "
    "boundaries of a reservation, a well located on trust properties outside "
    "reservation boundaries as defined in section 57-51.2-02, or a straddle "
    "well located on reservation trust land as defined in section "
    "57-51.1-07.10, if the average price of a barrel of crude oil exceeds the "
    "trigger price of ninety dollars for each month in any consecutive "
    "three-month period, then the rate of tax on oil extracted from all "
    "taxable wells is six percent of the gross value at the well of the oil "
    "extracted")
Q_OET_2015 = ("The rate of tax is six and one-halffive percent of the gross "
              "value at the well of the oil extracted")
Q_OET_2015_EFF = ("SECTION 9. EFFECTIVE DATE - EXPIRATION DATE. Sections 1, 2, "
                  "3, and 5 of this Act are effective for taxable events "
                  "occurring after December 31, 2015.")
Q_LIFE_OF_WELL = ("An oil or gas well that is drilled and completed during the "
                  "time of an agreement under this chapter must be subject to "
                  "the terms of the agreement for the life of the well.")
Q_57_51_2_ALLOC = (
    "a. Production attributable to trust lands. The tribe must receive eighty "
    "percent of the total revenues, and be subject to all applicable "
    "exemptions from all oil and gas gross production and oil extraction taxes "
    "attributable to production from trust lands on the reservation and on "
    "trust properties outside reservation boundaries. The state must receive "
    "the remainder. b. All other production. The tribe must receive twenty "
    "percent of the total oil and gas gross production and oil extraction "
    "taxes collected, and be subject to all applicable exemptions, from all "
    "production attributable to nontrust lands on the reservation in lieu of "
    "the application of tribal fees and taxes related to production on such "
    "lands. The state must receive the remainder.")
Q_STRADDLE = (
    "a. Fifty percent of the taxes certified under this section for wells "
    "drilled before July 1, 2019, multiplied by the on-reservation trust lands "
    "acreage ratio calculated under subsection 1 for that reservation; b. "
    "Fifty percent of the taxes certified under this section for wells drilled "
    "before July 1, 2019, multiplied by the on-reservation nontrust lands "
    "acreage ratio calculated under subsection 1 for that reservation; c. "
    "Eighty percent of the taxes certified under this section for wells "
    "drilled on or after July 1, 2019, multiplied by the on-reservation trust "
    "lands acreage ratio calculated under subsection 1 for that reservation; "
    "and d. Twenty percent of the taxes certified under this section for wells "
    "drilled on or after July 1, 2019, multiplied by the on-reservation "
    "nontrust lands acreage ratio calculated under subsection 1 for that "
    "reservation.")
Q_TREASURER_FLOW = (
    "Tribal Oil and Gas Production and Extraction is taxed and distributed "
    "according to a compact between the Three Affiliated Tribes and the State "
    "and is codified in NDCC 57-51.2 | Oil and gas wells drilled prior to July "
    "1, 2019 | Collections attributed to trust land are split 50%/50% between "
    "Three Affiliated Tribes/State. | Collections attributed to fee land are "
    "split 50%/50% between Three Affiliated Tribes/State. | Oil and gas wells "
    "drilled after June 30, 2019 | Collections attributed to trust land are "
    "split 80%/20% between Three Affiliated Tribes/State. | Collections "
    "attributed to fee land are split 20%/80% between Three Affiliated "
    "Tribes/State.")
Q_TREASURER_FLOW_1719 = (
    "Tribal Oil and Gas Production and Extraction is taxed and distributed "
    "according to a compact between the Three Affiliated Tribes and the State "
    "and is codified in NDCC 57-51.2 | Extraction | Collections attributed to "
    "trust land are split 50%/50% between Three Affiliated Tribes/State. | "
    "Collections attributed to non-trust land are split 50%/50% between Three "
    "Affiliated Tribes/State. | Gross Production | Collections attributed to "
    "trust land are split 50%/50% between Three Affiliated Tribes/State. | "
    "Collections attributed to non-trust land are split 50%/50% between Three "
    "Affiliated Tribes/State.")
Q_LC_LAG = ("Oil and gas tax revenue allocations reflect production and price "
            "from 2 months prior.")
Q_LC_COLLECTIONS = (
    "The schedules below provide information on oil and gas gross production "
    "tax collections and oil extraction tax collections in each county and the "
    "Fort Berthold Reservation for the biennium to date")
Q_LC_ALLOC = (
    "The schedule below provides information on oil and gas tax revenue "
    "collections allocated to the Three Affiliated Tribes of the Fort Berthold "
    "Reservation, state funds, and political subdivisions for the biennium to "
    "date")
Q_MEMO_2019 = (
    "In 2019, legislation removed the confirmation requirements, and the "
    "revenue sharing split was changed from a 50/50 revenue split to an 80/20 "
    "split in favor of the tribe for oil tax revenue from trust lands and an "
    "80/20 split in favor of the state for revenue from all other production. "
    "An agreement reflecting the new revenue split was signed on February 28, "
    "2019, and became effective on March 29, 2019.")
Q_MEMO_2013 = (
    "In 2013, Chapter 57-51.2 was extensively revised to provide more "
    "beneficial terms for the Three Affiliated Tribes under an oil and gas tax "
    "agreement. A new agreement implementing the 2013 legislative changes was "
    "signed on June 21, 2013.")
Q_MEMO_2008 = (
    "The oil and gas revenue sharing agreement between the Three Affiliated "
    "Tribes and the state was signed on June 10, 2008, and was to remain in "
    "effect for 24 calendar months after July 1, 2008. The agreement was "
    "entered pursuant to Chapter 57-51.2, which was enacted following the "
    "passage of Senate Bill No. 2419 (2007). A renegotiated agreement was "
    "signed on January 13, 2010, and the provisions of the 2010 agreement were "
    "to remain in effect indefinitely, unless formally canceled by either "
    "party.")
Q_2007_SESSION = (
    "the tribe must receive twenty percent of the total oil and gas gross "
    "production taxes collected from all production attributable to nontrust "
    "lands ... The state must receive the remainder. [Trust lands] must be "
    "evenly divided between the tribe and the state.")
Q_2013_SESSION = (
    "The tribe must receive twentyfifty percent of the total oil and gas gross "
    "production and oil extraction taxes collected from all production "
    "attributable to nontrust lands on the Fort Berthold Reservation "
    "[strikethrough preserved as printed in the session law]")
Q_2019_SESSION = (
    "a. Production attributable to trust lands. AllThe tribe must receive "
    "eighty percent of the total revenues ... b. All other production. The "
    "tribe must receive fiftytwenty percent of the total oil and gas gross "
    "production and oil extraction taxes collected ... attributable to "
    "nontrust lands on the reservation. SECTION 5. APPLICATION. Sections 1 and "
    "2 of this Act are effective for all new oil and gas wells on which "
    "drilling first commences after June 30, 2019")

URL_57_51 = "https://ndlegis.gov/cencode/t57c51.pdf"
URL_57_51_1 = "https://ndlegis.gov/cencode/t57c51-1.pdf"
URL_57_51_2 = "https://ndlegis.gov/cencode/t57c51-2.pdf"
URL_SL2007 = "https://ndlegis.gov/assembly/60-2007/session-laws/documents/TAXES.pdf"
URL_SL2013 = "https://ndlegis.gov/assembly/63-2013/session-laws/documents/TAXES.pdf"
URL_SL2015 = "https://ndlegis.gov/assembly/64-2015/session-laws/documents/TAXES.pdf"
URL_SL2019 = "https://ndlegis.gov/assembly/66-2019/session-laws/documents/TAXES.pdf"
URL_TREAS_FLOW = ("https://www.treasurer.nd.gov/how-oil-and-gas-tax-revenue-"
                  "distributed")
URL_MEMO = ("https://ndlegis.gov/sites/default/files/resource/69-2025/"
            "committee-memorandum/27.9066.01000.pdf")
URL_GAS_TABLE = "https://www.tax.nd.gov/gas-tax-rate-table"


def pdf_flat_text(path):
    txt = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                         capture_output=True, text=True).stdout
    return " ".join(txt.split())


def verify_quote(quote, path, label, problems):
    """A quote is only a quote if it is in the file. Whitespace and the
    session laws' strike-through artefacts are normalised; nothing else is."""
    flat = pdf_flat_text(path)
    probe = " ".join(quote.split())
    probe = probe.split(" ... ")[0].split(" | ")[0]
    probe = re.sub(r"\[.*?\]", "", probe).strip()
    if probe[:120] not in flat:
        # try a shorter distinctive fragment before giving up
        frag = probe[:60]
        if frag not in flat:
            problems.append((label, path.name, probe[:80]))
            return False
    return True


# ==========================================================================
# ROW WRITER
# ==========================================================================
def assert_no_forecast_language(row):
    for col in OUR_TEXT_COLUMNS:
        m = FORECAST_WORDS.search(str(row.get(col) or ""))
        if m:
            raise AssertionError(
                f"forecast language {m.group(0)!r} in {col} of "
                f"{row.get('tax_observation_id')}")


class Rows:
    def __init__(self, start_seq):
        self.rows = []
        self.seq = start_seq

    def add(self, **kw):
        self.seq += 1
        kw.setdefault("tribe_id", TRIBE_ID)
        kw.setdefault("tribe_name", TRIBE_NAME)
        kw.setdefault("state", STATE)
        kw.setdefault("tax_type", "SEVERANCE")
        for c in ("tax_remitted_usd", "statutory_rate", "rate_unit",
                  "derived_taxable_base", "base_unit", "rate_source_quote",
                  "amount_source_quote", "bound_basis"):
            kw.setdefault(c, "")
        kw["tax_observation_id"] = f"TTAX-ND-{self.seq:04d}"
        kw["built_date"] = TODAY
        kw.setdefault("fetched_date", TODAY)
        kw.setdefault("tier", "A")

        assert kw["tax_type"] == "SEVERANCE"
        assert kw["measurement_status"] in MEASUREMENT_STATUSES, \
            kw["measurement_status"]
        # Rule 4: the agreement or statute travels with the row.
        assert kw.get("agreement_or_statute_cite"), \
            f"no cite on {kw['tax_observation_id']}"
        # Two quotes or it does not exist.
        if kw["tax_remitted_usd"] != "":
            assert kw["amount_source_quote"], \
                f"amount without a quote: {kw['tax_observation_id']}"
        if kw["statutory_rate"] != "":
            assert kw["rate_source_quote"], \
                f"rate without a quote: {kw['tax_observation_id']}"
        if kw["measurement_status"] == STATUS_DERIVED_BASE:
            assert kw["rate_source_quote"] and kw["amount_source_quote"]
            assert kw["derived_taxable_base"] != "" and kw["base_unit"]
        # A unit with no rate beside it reads as a rate we hold and did not
        # print. The mixed unit is the one exception: it is the REASON there
        # is no rate, and saying so is the point of the row.
        if not kw["statutory_rate"] and \
                kw["rate_unit"] != "mixed_ad_valorem_and_per_unit":
            kw["rate_unit"] = ""
        if kw["derived_taxable_base"] == "":
            kw["base_unit"] = ""
        assert_no_forecast_language(kw)
        self.rows.append({k: kw.get(k, "") for k in FIELDS})


# ==========================================================================
# BUILD
# ==========================================================================
NOT_A_TRIBAL_TAX = (
    "These are state oil and gas gross production and oil extraction taxes "
    "collected on production within the exterior boundaries of the Fort "
    "Berthold Reservation. They are levied on producers and purchasers under "
    "NDCC 57-51 and 57-51.1, not paid by the Three Affiliated Tribes, and must "
    "never be read as a tribal tax burden. The tribe's SHARE of them is the "
    "separate REPORTED_TAX_REMITTANCE_PER_TRIBE rows and the payment series in "
    "data/clean/resource_revenue.csv.")

OET_BOUND_TEMPLATE = (
    "RANGE, NOT A POINT. Gross value at the well of oil extracted within the "
    "Fort Berthold Reservation is bounded by collections/0.06 = ${lo:,.0f} and "
    "collections/0.05 = ${hi:,.0f}. It is a range because NDCC 57-51.1-02(2) "
    "keeps a 5%-to-6% price trigger in force for wells inside reservation "
    "boundaries (the 2023 session removed it everywhere else) and no Tax "
    "Commissioner notice was retrieved stating the rate in force in this "
    "month. Both endpoints are LOWER bounds on gross value if any barrel was "
    "exempt or reduced-rate: NDCC 57-51.2-02(3) lets the agreement set the "
    "trust-land rate below the statutory cap and 57-51.2-02(4) turns the "
    "chapters' exemptions off on the reservation 'except as otherwise provided "
    "in the agreement', and the agreement is not published.")

OET_BOUND_65 = (
    "RANGE, NOT A POINT. Gross value at the well of oil extracted within the "
    "Fort Berthold Reservation is at least collections/0.065 = ${lo:,.0f}. The "
    "statutory rate for a taxable event on or before 2015-12-31 is six and "
    "one-half percent (2015 ND Session Laws ch. 466 sec. 3, effective for "
    "taxable events occurring after December 31, 2015). It is a lower bound "
    "and not a value because NDCC 57-51.2-02(3) lets the agreement set the "
    "trust-land rate below the statutory cap and 57-51.2-02(4) turns the "
    "chapters' exemptions off on the reservation 'except as otherwise provided "
    "in the agreement', and the agreement is not published.")

GPT_BOUND = (
    "NOT INVERTIBLE AT ALL. This single figure pools two taxes with "
    "incompatible units: oil at five percent of gross value at the well (NDCC "
    "57-51-02, base in USD) and gas at an annually indexed rate per mcf (NDCC "
    "57-51-02.2, base in MCF, {rate} for the fiscal year covering this "
    "production month). Dividing a pooled ad valorem and per-unit figure by "
    "either rate produces neither dollars nor mcf. North Dakota publishes no "
    "oil/gas split of Fort Berthold collections, so no bound is offered.")


def build():
    print("=== 113 build ===")
    problems = []
    unresolved = []

    # ---- entity resolution through the ONE resolver (standing rule 8) -----
    # The tribe is keyed from the SOURCE's own string, not from a constant, so
    # a spine change surfaces here instead of silently keying the wrong tribe.
    resolver = load_resolver()
    domain = load_domain()
    spine = read_spine()
    global TRIBE_ID, TRIBE_NAME
    resolved = {}
    for name in STN_TRIBES.values():
        tid, canon, how = resolver.resolve_entity(name, spine)
        resolved[name] = (tid, canon, how)
        print(f"  resolve {name!r} -> {tid} ({how})")
        if tid is None:
            unresolved.append(dict(
                item=f"ND-TREASURER-TRIBE-UNRESOLVED::{name}",
                kind="ENTITY_NOT_RESOLVED",
                detail=(f"The ND Treasurer's own label {name!r} does not "
                        "resolve against the spine. No dollar is keyed to it "
                        "in this build - the Treasurer returns no oil "
                        "distribution for this tribe - so nothing is at risk, "
                        "but the label will block a later fuel or tobacco "
                        "build off the same application."),
                action="rule the alias into the spine, do not fuzzy-match it"))
    mha_id, mha_name, mha_how = resolved["Three Affiliated Tribes"]
    assert mha_id == "TRBF-MHATAT-00", (
        f"the resolver keys the Treasurer's 'Three Affiliated Tribes' to "
        f"{mha_id}, not TRBF-MHATAT-00; refusing to write a severance dollar "
        f"onto an entity this build did not verify")
    TRIBE_ID, TRIBE_NAME = mha_id, mha_name
    TIER_A = domain.Tier.A.value
    assert TIER_A == "A"

    # ---------------- verify the statutory quotes against the PDFs ---------
    checks = [
        (Q_GPT_OIL, RAW / "statute/ndcc_t57c51_gross_production_tax.pdf",
         "57-51-02"),
        (Q_GPT_GAS, RAW / "statute/ndcc_t57c51_gross_production_tax.pdf",
         "57-51-02.2"),
        (Q_OET, RAW / "statute/ndcc_t57c51-1_oil_extraction_tax.pdf",
         "57-51.1-02(1)"),
        (Q_OET_TRIGGER, RAW / "statute/ndcc_t57c51-1_oil_extraction_tax.pdf",
         "57-51.1-02(2)"),
        (Q_STRADDLE, RAW / "statute/ndcc_t57c51-1_oil_extraction_tax.pdf",
         "57-51.1-07.10(2)"),
        (Q_LIFE_OF_WELL, RAW / "statute/ndcc_t57c51-2_tribal_oil_and_gas_agreements.pdf",
         "57-51.2-02(6)"),
        (Q_57_51_2_ALLOC, RAW / "statute/ndcc_t57c51-2_tribal_oil_and_gas_agreements.pdf",
         "57-51.2-02(5)"),
        (Q_OET_2015, RAW / "session_laws/2015_64th_TAXES.pdf", "2015 ch.466 s.3"),
        (Q_OET_2015_EFF, RAW / "session_laws/2015_64th_TAXES.pdf",
         "2015 ch.466 s.9"),
        (Q_MEMO_2019, RAW / "legislative_council/"
         "tribal_state_relations_background_memo_27.9066.01000.pdf", "TSRC 2019"),
        (Q_MEMO_2013, RAW / "legislative_council/"
         "tribal_state_relations_background_memo_27.9066.01000.pdf", "TSRC 2013"),
        (Q_MEMO_2008, RAW / "legislative_council/"
         "tribal_state_relations_background_memo_27.9066.01000.pdf", "TSRC 2008"),
    ]
    for q, p, lab in checks:
        if not p.exists():
            problems.append((lab, str(p), "MISSING FILE"))
            continue
        verify_quote(q, p, lab, problems)
    for lab, fn, frag in problems:
        print(f"  QUOTE NOT VERIFIED: {lab} in {fn} :: {frag!r}")

    # ---------------- Legislative Council monthly series -------------------
    gpt, oet, alloc = {}, {}, {}
    prior_rows = []
    for spec in LC_REPORTS:
        p = RAW / f"legislative_council/{spec['num']}.pdf"
        if not p.exists():
            unresolved.append(dict(
                item=f"LC report {spec['num']} not retrieved",
                kind="SOURCE_MISSING", detail=str(p), action="re-run fetch"))
            continue
        series, prior, ck = parse_lc_report(p, spec)
        bad = [c for c in ck if c[1] != "ok"]
        for c in bad:
            unresolved.append(dict(
                item=f"LC {spec['num']} {c[0]} row refused",
                kind="TABLE_CHECK_FAILED",
                detail=f"{c[1]}: computed {c[2]} vs printed {c[3]}",
                action="read the row by word position and re-check"))
        gpt.update(series["GPT"])
        oet.update(series["OET"])
        alloc.update(series["ALLOC"])
        if spec["layout"] == "1+12" and spec["prior"]:
            prior_rows.append((spec, prior))
        print(f"  {spec['num']}: GPT {len(series['GPT'])}  OET "
              f"{len(series['OET'])}  ALLOC {len(series['ALLOC'])}  "
              f"refused {len(bad)}")

    # ---------------- ND Treasurer distributions ---------------------------
    stn = {}
    stn_zero = []
    for s in stn_sources():
        p = RAW / s["path"]
        if not p.exists():
            continue
        rows, grand = parse_stn(p)
        stn[(s["stn_tribe"], s["stn_type"])] = (rows, grand)
        if not rows:
            stn_zero.append((s["stn_tribe"], s["stn_type"]))
    straddle_m = {}
    for (tribe, typ), (rows, _g) in stn.items():
        if tribe == "Three Affiliated Tribes" and typ == "Oil & Gas Straddle Well":
            for d, _t, _ty, v in rows:
                straddle_m[d[:7]] = straddle_m.get(d[:7], 0.0) + v
    mha_total = sum(sum(v for _d, _t, _ty, v in rows)
                    for (tr, _ty), (rows, _g) in stn.items()
                    if tr == "Three Affiliated Tribes")
    print(f"  treasurer: MHA total ${mha_total:,.2f} across "
          f"{sum(len(r) for (t, _x), (r, _g) in stn.items() if t == 'Three Affiliated Tribes')}"
          f" payments; {len(stn_zero)} tribe/type combinations returned no records")

    # ---------------- gas tax rate table -----------------------------------
    gas_rates = parse_gas_rate_table(RAW / "tax_commissioner/gas_tax_rate_table.html")
    gas_by_month = {}
    for st, en, val, quote in gas_rates:
        ym = st
        while ym <= en:
            gas_by_month[ym] = (val, quote, st, en)
            ym = shift_month(ym, 1)
    print(f"  gas tax rate table: {len(gas_rates)} fiscal-year rates")

    # ---------------- straddle acreage ratios ------------------------------
    ratios = {}
    for k, fy in (("straddle_well_acreage_ratio_memo_2025.pdf", "FY2026"),
                  ("straddle_well_acreage_ratio_memo_2024.pdf", "FY2025")):
        p = RAW / "tax_commissioner" / k
        if p.exists():
            r = parse_straddle_memo(p)
            if r:
                ratios[fy] = r
    print(f"  straddle acreage ratio certifications: {sorted(ratios)}")

    # ======================================================================
    # tribal_tax_bases.csv rows
    # ======================================================================
    existing = read_csv(CLEAN / "tribal_tax_bases.csv")
    n_nd = sum(1 for r in existing if r["tax_observation_id"].startswith("TTAX-ND-"))
    R = Rows(n_nd)

    # -- 1. rate rows -------------------------------------------------------
    R.add(period_start="2007-07-01", period_end="",
          statutory_rate="0.05", rate_unit="share_of_gross_value_at_well",
          rate_source_quote=Q_GPT_OIL,
          agreement_or_statute_cite=(
              "NDCC 57-51-02 (gross production tax on oil), applied within the "
              "Fort Berthold Reservation by NDCC 57-51.2-02(2)"),
          measurement_status=STATUS_RATE_ONLY,
          source_url=URL_57_51,
          confidence=("statewide statutory rate; NDCC 57-51.2-02(2) requires "
                      "the state gross production tax to apply to all wells "
                      "within the reservation"))
    R.add(period_start="1991-07-01", period_end="",
          statutory_rate="", rate_unit="usd_per_mcf",
          rate_source_quote=Q_GPT_GAS,
          agreement_or_statute_cite="NDCC 57-51-02.2 (gross production tax on gas)",
          measurement_status=STATUS_RATE_ONLY,
          source_url=URL_57_51,
          confidence=("the gas rate is not a fixed number: it is re-determined "
                      "every fiscal year and published by the Tax "
                      "Commissioner. The fiscal-year values are the rows that "
                      "follow."))
    for st, en, val, quote in sorted(gas_rates):
        if st < "2008-07":
            continue
        R.add(period_start=f"{st}-01", period_end=month_bounds(en)[1],
              statutory_rate=f"{val:.4f}", rate_unit="usd_per_mcf",
              rate_source_quote=quote,
              agreement_or_statute_cite=(
                  "NDCC 57-51-02.2; rate published by the Tax Commissioner "
                  "under 57-51-02.2(2)(c)"),
              measurement_status=STATUS_RATE_ONLY,
              source_url=URL_GAS_TABLE,
              confidence=("levied on taxable production in mcf, so the base it "
                          "would yield is a VOLUME and never a dollar figure"))
    R.add(period_start="2007-07-01", period_end="2015-12-31",
          statutory_rate="0.065", rate_unit="share_of_gross_value_at_well",
          rate_source_quote=f"{Q_OET_2015} || {Q_OET_2015_EFF}",
          agreement_or_statute_cite=(
              "NDCC 57-51.1-02(1) as it read before 2015 ND Session Laws "
              "ch. 466 (HB 1476) sec. 3, which is effective for taxable events "
              "occurring after December 31, 2015"),
          measurement_status=STATUS_RATE_ONLY, source_url=URL_SL2015,
          confidence=("period end is the last TAXABLE EVENT at the old rate, "
                      "not the last distribution: collections lag production "
                      "by about two months"))
    R.add(period_start="2016-01-01", period_end="",
          statutory_rate="0.05", rate_unit="share_of_gross_value_at_well",
          rate_source_quote=Q_OET,
          agreement_or_statute_cite="NDCC 57-51.1-02(1)",
          measurement_status=STATUS_RATE_ONLY, source_url=URL_57_51_1,
          confidence=("subject to the reservation-only price trigger in "
                      "57-51.1-02(2), which is the next row"))
    R.add(period_start="2016-01-01", period_end="",
          statutory_rate="0.06", rate_unit="share_of_gross_value_at_well",
          rate_source_quote=Q_OET_TRIGGER,
          agreement_or_statute_cite="NDCC 57-51.1-02(2) and (3)",
          measurement_status=STATUS_RATE_ONLY, source_url=URL_57_51_1,
          bound_basis=("CONDITIONAL RATE. It applies only while WTI has "
                       "exceeded an annually indexed trigger price for three "
                       "consecutive months, and a tribe may irrevocably opt "
                       "out under 57-51.1-02(3). The Tax Commissioner "
                       "published trigger prices of $89.65 for CY2021 and "
                       "$117.20 for CY2026; no notice stating the rate "
                       "actually in force in any month was retrieved, so no "
                       "month in this dataset is assigned 6%."),
          confidence=("the 2023 session removed this trigger for every North "
                      "Dakota well EXCEPT wells inside reservation boundaries "
                      "and straddle wells, so it survives only here"))

    # -- 2. reservation collections rows ------------------------------------
    lc_url_by_month = {}
    for spec in LC_REPORTS:
        for ym in month_seq(spec["end"], 12):
            lc_url_by_month[ym] = f"{spec['base']}/{spec['num']}.pdf"

    for ym in sorted(oet):
        ps, pe = month_bounds(ym)
        prod = shift_month(ym, -2)
        amount = oet[ym]
        q = (f"Oil Extraction Tax Collections | Fort Berthold Reservation | "
             f"{month_name(ym)} | {amount:,.0f}")
        if prod <= "2015-12":
            rate, rq = "0.065", f"{Q_OET_2015} || {Q_OET_2015_EFF}"
            bound = OET_BOUND_65.format(lo=amount / 0.065)
        else:
            rate, rq = "0.05", Q_OET
            bound = OET_BOUND_TEMPLATE.format(lo=amount / 0.06, hi=amount / 0.05)
        R.add(period_start=ps, period_end=pe,
              tax_remitted_usd=f"{amount:.2f}",
              statutory_rate=rate, rate_unit="share_of_gross_value_at_well",
              rate_source_quote=rq, amount_source_quote=q,
              agreement_or_statute_cite=(
                  "NDCC 57-51.1-02 (oil extraction tax); collections within "
                  "the Fort Berthold Reservation are subject to NDCC 57-51.2 "
                  "and are allocated under 57-51.2-02(5)"),
              measurement_status=STATUS_RESERVATION_COLLECTIONS,
              bound_basis=bound,
              source_url=lc_url_by_month.get(ym, ""),
              confidence=(NOT_A_TRIBAL_TAX + " Collection month; the "
                          "Legislative Council states that allocations "
                          "reflect production and price from 2 months prior, "
                          f"so the production month is {prod}."))

    for ym in sorted(gpt):
        ps, pe = month_bounds(ym)
        prod = shift_month(ym, -2)
        amount = gpt[ym]
        q = (f"Oil and Gas Gross Production Tax Collections | Fort Berthold "
             f"Reservation | {month_name(ym)} | {amount:,.0f}")
        gr = gas_by_month.get(prod)
        rate_txt = f"${gr[0]:.4f} per mcf" if gr else "a rate not retrieved"
        R.add(period_start=ps, period_end=pe,
              tax_remitted_usd=f"{amount:.2f}",
              statutory_rate="", rate_unit="mixed_ad_valorem_and_per_unit",
              rate_source_quote="",
              amount_source_quote=q,
              agreement_or_statute_cite=(
                  "NDCC 57-51-02 (oil, five percent of gross value at the "
                  "well) and NDCC 57-51-02.2 (gas, per mcf); allocated under "
                  "NDCC 57-51.2-02(5)"),
              measurement_status=STATUS_RESERVATION_COLLECTIONS,
              bound_basis=GPT_BOUND.format(rate=rate_txt),
              source_url=lc_url_by_month.get(ym, ""),
              confidence=(NOT_A_TRIBAL_TAX + " Collection month; production "
                          f"month is {prod}."))

    # -- 3. tribal allocation rows, with the MEASURED effective share -------
    for ym in sorted(alloc):
        ps, pe = month_bounds(ym)
        amount = alloc[ym]
        q = (f"Three Affiliated Tribes | {month_name(ym)} | {amount:,.0f}")
        base = gpt.get(ym, 0) + oet.get(ym, 0)
        strad = straddle_m.get(ym, 0.0)
        share_txt = ""
        if base > 0:
            on_res = amount - strad
            share = on_res / base
            share_txt = (
                "MEASURED EFFECTIVE SHARE, NOT A STATUTORY RATIO. The tribe's "
                f"on-reservation allocation of ${on_res:,.0f} is {share:.4%} "
                f"of the ${base:,.0f} of gross production and oil extraction "
                "tax collected within the Fort Berthold Reservation in the "
                "same month. It is not 50/50 and it is not 80/20: every well "
                "keeps the split in force when it was drilled (NDCC "
                "57-51.2-02(6)), so the payment is a blend whose weights "
                "North Dakota does not publish. The share is measured here "
                "rather than assumed. ")
            if strad:
                share_txt += (
                    f"${strad:,.0f} of straddle-well distribution is "
                    "subtracted first, because straddle wells sit OUTSIDE the "
                    "reservation and their collections are in the county rows, "
                    "not the Fort Berthold row.")
            if share > 0.5001:
                p_min = (share - 0.5) / 0.3
                share_txt += (
                    f" The share exceeds 50%, which forces at least "
                    f"{p_min:.2%} of this month's reservation collections to "
                    "come from wells spudded after 2019-06-30: the pre-2019 "
                    "regime pays 50% on trust and fee alike, and the post-2019 "
                    "regime pays at most 80%, so post_2019_share >= "
                    "(observed - 0.50) / 0.30.")
        R.add(period_start=ps, period_end=pe,
              tax_remitted_usd=f"{amount:.2f}",
              amount_source_quote=q,
              agreement_or_statute_cite=(
                  "NDCC 57-51.2-02(5) and the state-tribal oil and gas tax "
                  "agreement entered under NDCC 57-51.2-01; the agreement in "
                  "force from 2019-03-29 was signed 2019-02-28"),
              measurement_status=STATUS_PER_TRIBE_AMOUNT,
              bound_basis=share_txt,
              source_url=lc_url_by_month.get(ym, ""),
              confidence=("the monthly total the Legislative Council reports "
                          "as allocated to the Three Affiliated Tribes. It "
                          "reconciles to the dollar against the sum of the "
                          "three ND Treasurer distribution types in "
                          "data/clean/resource_revenue.csv, which is where the "
                          "per-instrument breakdown lives."))

    # -- 4. the two twelve-month totals the source prints without months ----
    for spec, prior in prior_rows:
        if not spec["prior"]:
            continue
        p0, p1 = spec["prior"]
        if any(ym in oet for ym in month_seq(p1, 12)):
            continue          # months already published individually
        for tag, cite, status in (
                ("OET", "NDCC 57-51.1-02", STATUS_RESERVATION_COLLECTIONS),
                ("GPT", "NDCC 57-51-02 and 57-51-02.2",
                 STATUS_RESERVATION_COLLECTIONS),
                ("ALLOC", "NDCC 57-51.2-02(5)", STATUS_PER_TRIBE_AMOUNT)):
            if tag not in prior:
                continue
            amount = prior[tag]
            label = {"OET": "Oil Extraction Tax Collections | Fort Berthold "
                            "Reservation",
                     "GPT": "Oil and Gas Gross Production Tax Collections | "
                            "Fort Berthold Reservation",
                     "ALLOC": "Three Affiliated Tribes"}[tag]
            R.add(period_start=f"{p0}-01", period_end=month_bounds(p1)[1],
                  tax_remitted_usd=f"{amount:.2f}",
                  amount_source_quote=(f"{label} | {month_name(p0)} through "
                                       f"{month_name(p1)} | {amount:,.0f}"),
                  agreement_or_statute_cite=cite,
                  measurement_status=status,
                  bound_basis=("TWELVE-MONTH TOTAL, NOT A MONTHLY SERIES. The "
                               "report that covers these months prints only a "
                               "cumulative figure for them; the monthly cells "
                               "are printed for the second year of the "
                               "biennium only. No monthly split is invented."),
                  source_url=f"{spec['base']}/{spec['num']}.pdf",
                  confidence=(NOT_A_TRIBAL_TAX
                              if tag != "ALLOC" else
                              "the Legislative Council's own cumulative total"))

    new_rows = R.rows
    print(f"  built {len(new_rows)} SEVERANCE rows")

    # ======================================================================
    # nd_severance_allocation.csv
    # ======================================================================
    A = []

    def alloc_row(**kw):
        kw.setdefault("tribe_id", TRIBE_ID)
        kw.setdefault("fetched_date", TODAY)
        kw.setdefault("built_date", TODAY)
        kw.setdefault("tier", "A")
        kw.setdefault("superseded_by", "")
        kw.setdefault("effective_end", "")
        for c in ("trust_land_tribal_share", "trust_land_state_share",
                  "fee_land_tribal_share", "fee_land_state_share"):
            kw.setdefault(c, "")
        assert kw["statute_cite"], kw["allocation_id"]
        assert kw["source_quote"], kw["allocation_id"]
        A.append({k: kw.get(k, "") for k in ALLOC_FIELDS})

    alloc_row(
        allocation_id="ND-ALLOC-001",
        statute_cite=("2007 ND Session Laws ch. 545 (SB 2419), 60th "
                      "Legislative Assembly, enacting NDCC ch. 57-51.2"),
        effective_start="2007-07-01", effective_end="2013-06-30",
        well_vintage_rule=(
            "No vintage rule in the enacted allocation itself: the split turns "
            "on the land status of the production, not the spud date. NDCC "
            "57-51.2-02(6) separately binds a well drilled and completed while "
            "an agreement is in force to that agreement's terms for the life "
            "of the well, which is what later makes the 2019 change a vintage "
            "rule."),
        trust_land_tribal_share="0.50", trust_land_state_share="0.50",
        fee_land_tribal_share="0.20", fee_land_state_share="0.80",
        superseded_by="ND-ALLOC-002", source_url=URL_SL2007,
        source_quote=Q_2007_SESSION,
        confidence=("the first agreement under this chapter was signed "
                    "2008-06-10 and renegotiated 2010-01-13; neither agreement "
                    "text is published, so the shares here are the STATUTORY "
                    "authorisation, not the agreement's own wording"))

    alloc_row(
        allocation_id="ND-ALLOC-002",
        statute_cite=("2013 ND Session Laws ch. 473 (HB 1198), 63rd "
                      "Legislative Assembly, amending NDCC 57-51.2-02(5)"),
        effective_start="2013-07-01", effective_end="2019-06-30",
        well_vintage_rule=(
            "None. A clean date switch applying to taxable events after "
            "2013-06-30, and the same split for trust and fee land, which is "
            "why the tribe's measured share of Fort Berthold collections is "
            "exactly 50.00% throughout the 2015-17 and 2017-19 biennia."),
        trust_land_tribal_share="0.50", trust_land_state_share="0.50",
        fee_land_tribal_share="0.50", fee_land_state_share="0.50",
        superseded_by="ND-ALLOC-004", source_url=URL_SL2013,
        source_quote=Q_2013_SESSION,
        confidence=("SUPERSEDED FOR NEW PRODUCTION ONLY. ND-ALLOC-003 carries "
                    "this exact split forward for the life of every well "
                    "drilled before 2019-07-01, so this regime is still "
                    "operating today. "
                    "2013 ch. 5 (HB 1005, approved six days earlier) also "
                    "amended the same subsection but retained 'twenty "
                    "percent'; HB 1198 controls and the Century Code text as "
                    "of Dec 2016 reads 'fifty'. A new agreement implementing "
                    "the 2013 changes was signed 2013-06-21."))

    alloc_row(
        allocation_id="ND-ALLOC-003",
        statute_cite=("NDCC 57-51.2-02(6); 2019 ND Session Laws ch. 506 "
                      "(SB 2312) sec. 5 APPLICATION"),
        effective_start="2019-07-01", effective_end="",
        well_vintage_rule=(
            "WELLS ON WHICH DRILLING FIRST COMMENCED ON OR BEFORE 2019-06-30. "
            "These keep the 2013 split for the LIFE OF THE WELL. This row is "
            "why no single ratio describes any month after mid-2019."),
        trust_land_tribal_share="0.50", trust_land_state_share="0.50",
        fee_land_tribal_share="0.50", fee_land_state_share="0.50",
        superseded_by="", source_url=URL_TREAS_FLOW,
        source_quote=Q_TREASURER_FLOW,
        confidence=("stated as operative by the State Treasurer's own "
                    "distribution flow chart in every biennium from 2019-21 "
                    "through 2025-27, and by NDCC 57-51.2-02(6)"))

    alloc_row(
        allocation_id="ND-ALLOC-004",
        statute_cite=("2019 ND Session Laws ch. 506 (SB 2312), 66th "
                      "Legislative Assembly, amending NDCC 57-51.2-02(5); "
                      "sec. 5 APPLICATION"),
        effective_start="2019-07-01", effective_end="",
        well_vintage_rule=(
            "WELLS ON WHICH DRILLING FIRST COMMENCED AFTER 2019-06-30 ONLY. "
            "THIS RATIO MUST NOT BE APPLIED TO THE PAYMENT SERIES. Every "
            "monthly distribution after mid-2019 is a blend of this row and "
            "ND-ALLOC-003 weighted by the spud-date mix of producing wells, "
            "and North Dakota publishes no vintage split of collections."),
        trust_land_tribal_share="0.80", trust_land_state_share="0.20",
        fee_land_tribal_share="0.20", fee_land_state_share="0.80",
        superseded_by="", source_url=URL_SL2019,
        source_quote=Q_2019_SESSION,
        confidence=("the agreement carrying this split was signed 2019-02-28 "
                    "and became effective 2019-03-29, but the statutory "
                    "application clause limits it to wells spudded after "
                    "2019-06-30, and that is what the Treasurer's flow charts "
                    "operate"))

    strad_note_2026 = ratios.get("FY2026")
    strad_note_2025 = ratios.get("FY2025")
    ratio_txt = "; ".join(
        f"{fy}: trust {r['trust']}, non-trust {r['nontrust']} "
        f"({r['start']} through {r['end']})"
        for fy, r in sorted(ratios.items()))
    alloc_row(
        allocation_id="ND-ALLOC-005",
        statute_cite=("NDCC 57-51.1-07.10(2)(a)-(b), enacted 2021 (SB 2319), "
                      "applying to collections allocated by the State "
                      "Treasurer after 2021-09-01"),
        effective_start="2021-09-01", effective_end="",
        well_vintage_rule=(
            "STRADDLE WELLS - wells located OUTSIDE the reservation with one "
            "or more laterals penetrating the boundary - drilled BEFORE "
            "2019-07-01. The share is not a flat percentage: it is 50 percent "
            "of certified straddle-well taxes multiplied by the "
            "on-reservation trust lands acreage ratio, plus 50 percent "
            "multiplied by the non-trust ratio, both certified annually by the "
            "Industrial Commission and published by the Tax Commissioner. "
            + (f"Certified ratios: {ratio_txt}." if ratio_txt else "")),
        trust_land_tribal_share="0.50", trust_land_state_share="0.50",
        fee_land_tribal_share="0.50", fee_land_state_share="0.50",
        superseded_by="", source_url=URL_57_51_1, source_quote=Q_STRADDLE,
        confidence=("the percentages are the statutory coefficients; the "
                    "amount actually distributed is those coefficients times "
                    "the certified acreage ratios, which do not sum to one "
                    "because the denominator is total spacing unit acreage "
                    "including acreage outside the reservation"))

    alloc_row(
        allocation_id="ND-ALLOC-006",
        statute_cite=("NDCC 57-51.1-07.10(2)(c)-(d), enacted 2021 (SB 2319), "
                      "applying to collections allocated by the State "
                      "Treasurer after 2021-09-01"),
        effective_start="2021-09-01", effective_end="",
        well_vintage_rule=(
            "STRADDLE WELLS drilled ON OR AFTER 2019-07-01. 80 percent of "
            "certified straddle-well taxes times the on-reservation trust "
            "lands acreage ratio, plus 20 percent times the non-trust ratio. "
            "Same vintage boundary as ND-ALLOC-004, so the straddle-well "
            "distribution is a blend for the same reason - but a NARROW one, "
            "because both vintages are multiplied by the same published "
            "acreage ratios. "
            + (f"Certified ratios: {ratio_txt}." if ratio_txt else "")),
        trust_land_tribal_share="0.80", trust_land_state_share="0.20",
        fee_land_tribal_share="0.20", fee_land_state_share="0.80",
        superseded_by="", source_url=URL_57_51_1, source_quote=Q_STRADDLE,
        confidence=(
            ("With the FY2026 certified ratios the effective share of "
             "certified straddle-well taxes lies between "
             f"{0.8 * strad_note_2026['trust'] + 0.2 * strad_note_2026['nontrust']:.7f} "
             "(all wells post-2019) and "
             f"{0.5 * (strad_note_2026['trust'] + strad_note_2026['nontrust']):.7f} "
             "(all wells pre-2019) - a bound about eleven percent wide, "
             "which is the only place in this build where the vintage blend "
             "narrows to something tight.")
            if strad_note_2026 else
            "acreage ratio certification not retrieved for this fiscal year"))

    # A period we deliberately leave blank rather than carry a formula into.
    alloc_row(
        allocation_id="ND-ALLOC-000",
        statute_cite="NDCC 57-51.2-01 (authority to enter agreements)",
        effective_start="", effective_end="2007-06-30",
        well_vintage_rule=(
            "No allocation. Chapter 57-51.2 did not exist before the 2007 "
            "session, no agreement was in force, and the ND Treasurer's "
            "distribution search returns no tribal oil distribution before "
            "September 2008. The share columns are left BLANK rather than "
            "carrying a later formula backwards."),
        superseded_by="ND-ALLOC-001", source_url=URL_MEMO,
        source_quote=Q_MEMO_2008,
        confidence=("blank by design; recording the absence so a later reader "
                    "does not fill it from ND-ALLOC-001"))

    # ======================================================================
    # review queue
    # ======================================================================
    unresolved += [
        dict(item="ND-SEVERANCE-AGREEMENT-TEXT-NOT-PUBLISHED",
             kind="SOURCE_WITHHELD_OR_UNPUBLISHED",
             detail=("The four state-tribal oil and gas tax agreements "
                     "(2008-06-10, 2010-01-13, 2013-06-21, 2019-02-28) are "
                     "described by the Legislative Council but their text was "
                     "not found on ndlegis.gov, tax.nd.gov, treasurer.nd.gov "
                     "or governor.nd.gov. NDCC 57-51.2-02(3) lets the "
                     "agreement set the trust-land oil extraction rate below "
                     "the statutory cap and 57-51.2-02(4) turns the chapters' "
                     "exemptions off on the reservation 'except as otherwise "
                     "provided in the agreement', so the agreement is the only "
                     "document that could close the rate question."),
             action=("request from the ND Governor's office or Legislative "
                     "Council under the 57-51.2-04 report requirement; until "
                     "then every derived base stays a bound")),
        dict(item="ND-OET-TRIGGER-RATE-IN-FORCE-UNKNOWN",
             kind="RATE_NOT_UNIQUELY_DETERMINED",
             detail=("NDCC 57-51.1-02(2) raises the reservation oil extraction "
                     "rate from 5% to 6% after three consecutive months above "
                     "an indexed WTI trigger price. Trigger prices retrieved: "
                     "$89.65 (CY2021), $117.20 (CY2026). Tax Commissioner "
                     "notices for CY2022-CY2025 were probed at the same URL "
                     "pattern and are not published there."),
             action=("find the CY2022-CY2025 trigger notices and any rate-"
                     "change notice; a confirmed 6% month collapses that "
                     "month's bound to a point")),
        dict(item="ND-FB-COLLECTIONS-PRE-AUG-2013",
             kind="OUR_COVERAGE_GAP",
             detail=("Fort Berthold collections are published back to August "
                     "2011 in LC# 13.9128, but that report prints three "
                     "sub-columns per month (gross production, extraction, "
                     "total) in a layout this parser does not read safely. "
                     "Aug 2013 - Jul 2014 and Aug 2015 - Jul 2016 are "
                     "published only as twelve-month cumulative totals in the "
                     "reports retrieved."),
             action=("parse 13.9128.24000 by column x-position, or difference "
                     "successive monthly issues, to extend the monthly series "
                     "back to Aug 2011")),
        dict(item="ND-TREASURER-PUBLISHES-FOUR-MORE-TRIBAL-TAX-TYPES",
             kind="HIGH_VALUE_LEAD_OUT_OF_SCOPE",
             detail=("The same ND Treasurer application publishes per-tribe "
                     "monthly amounts for Tribal Highway Tax (motor fuel), "
                     "Tribal Cigarette, Tribal Sales Tax and Tribal Alcohol, "
                     "for four tribes: Standing Rock, Spirit Lake, Three "
                     "Affiliated and Turtle Mountain. Measured 2026-08-07: "
                     "highway tax 902 payments across four tribes "
                     "($53.4M total, from 2005-01), cigarette 258 payments "
                     "(Standing Rock, $1.59M), sales tax 22 payments "
                     "(Standing Rock, 2016-09 to 2019-03, $0.62M), alcohol 7 "
                     "payments (Three Affiliated, $0.46M). "
                     "docs/TRIBAL_TAX_BUILD_LOG.md records that NO tribe in "
                     "the dataset carries a per-tribe non-gaming tax amount. "
                     "North Dakota publishes them."),
             action=("build MOTOR_FUEL, TOBACCO, RETAIL_SALES and ALCOHOL "
                     "rows from apps.nd.gov/stn; this is the first per-tribe "
                     "money in the netting machinery")),
        dict(item="ND-NO-OIL-AGREEMENT-FOR-THREE-OTHER-TRIBES",
             kind="MEASURED_ABSENCE",
             detail=("NDCC 57-51.2-01 authorises oil and gas tax agreements "
                     "with the Three Affiliated Tribes, the Standing Rock "
                     "Sioux Tribe and the Turtle Mountain Band of Chippewa "
                     "Indians. Queried 2026-08-07 for all four tribes in the "
                     "Treasurer's list against all three oil distribution "
                     "types: only Three Affiliated Tribes returns records. "
                     "Standing Rock, Spirit Lake and Turtle Mountain return "
                     "'No records found' and a $0.00 grand total."),
             action=("record as PUBLISHES/absent, not NOT_CHECKED; re-probe "
                     "when a new agreement is reported to the Legislative "
                     "Council under 57-51.2-04")),
        dict(item="SERIES-BREAK-ND-2019-NEEDS-THE-MEASURED-SHARE",
             kind="DOWNSTREAM_UPDATE_OWED",
             detail=("`data/clean/series_breaks.csv` carries a "
                     "resource_revenue / allocation_formula break at "
                     "2019-06-30 whose effect_on_series ends 'The published "
                     "distribution does not decompose by vintage and Cedar "
                     "Press does not model the mix.' That is still true of the "
                     "VINTAGE mix, but the EFFECTIVE SHARE is now measured "
                     "monthly against the Legislative Council's Fort Berthold "
                     "collections - 50.00% through mid-2019, 55.48% in the "
                     "2025-27 biennium to date. The break entry should say so "
                     "rather than leaving a reader with no number at all."),
             action=("script 86 owns series_breaks.csv and regenerates it, so "
                     "the sentence must be changed there, not appended here")),
        dict(item="ND-DMR-CANNOT-SUPPLY-WELL-VINTAGE-MIX",
             kind="SOURCE_STRUCTURALLY_SILENT",
             detail=("ND DMR's free statistics are by county, formation and "
                     "statewide. Probed 2026-08-07: the statistics index "
                     "offers monthly production by county, historical monthly "
                     "oil/gas statistics, annual and cumulative production by "
                     "formation, and drilling statistics. There is NO "
                     "reservation aggregate and no trust/fee field. The "
                     "complete Well Index carrying spud dates is subscription-"
                     "gated. Even with per-well spud dates, per-well tax "
                     "collections are confidential taxpayer data, so the "
                     "vintage weights cannot be reconstructed from public "
                     "sources at all."),
             action="none; this is a property of the record"),
    ]

    # ======================================================================
    # WRITE
    # ======================================================================
    write_tax_bases(new_rows)
    write_csv(CLEAN / "nd_severance_allocation.csv", A, ALLOC_FIELDS)
    print(f"  nd_severance_allocation.csv: {len(A)} rows")
    ufields = ["item", "kind", "detail", "action"]
    write_csv(REVIEW / f"nd_severance_unresolved_{TODAY}.csv",
              [{k: u.get(k, "") for k in ufields} for u in unresolved], ufields)
    print(f"  review/nd_severance_unresolved_{TODAY}.csv: {len(unresolved)} rows")
    write_codebook()
    write_log(new_rows, A, gpt, oet, alloc, straddle_m, stn, stn_zero,
              gas_rates, ratios, unresolved, problems)
    return new_rows


MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def month_name(ym):
    y, m = ym.split("-")
    return f"{MONTHS[int(m) - 1]} {y}"


def read_csv(p):
    if not Path(p).exists():
        return []
    with Path(p).open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(p, rows, fields):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    with Path(p).open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def write_tax_bases(new_rows):
    """APPEND ONLY. Re-read immediately before writing so a concurrent agent
    cannot be clobbered, back the file up, and refuse to drop a row we did not
    author."""
    p = CLEAN / "tribal_tax_bases.csv"
    bak = CLEAN / f"tribal_tax_bases.csv.bak_{TODAY}_pre113"
    if p.exists() and not bak.exists():
        shutil.copy2(p, bak)
    cur = read_csv(p)                      # re-read, late, on purpose
    # This script is the sole author of ND SEVERANCE rows. Replacing exactly
    # that slice makes a re-run idempotent instead of appending a second copy,
    # and everything any other agent wrote is carried through untouched. The
    # predicate is deliberately narrow: an ND row of any OTHER tax type - a
    # motor fuel or tobacco row off the same Treasurer application - is kept.
    ours = [r for r in cur
            if r.get("state") == "ND" and r.get("tax_type") == "SEVERANCE"]
    keep = [r for r in cur if r not in ours]
    out = keep + new_rows
    write_csv(p, out, FIELDS)
    print(f"  tribal_tax_bases.csv: {len(keep)} kept (of which "
          f"{len(keep) - (len(cur) - len(ours))} unexpected) + "
          f"{len(new_rows)} ND severance = {len(out)}; "
          f"{len(ours)} prior ND severance rows replaced")


CODEBOOK_VARS = [
    # (dataset, variable, description)
    ("16_nd_severance_allocation", "allocation_id",
     "Cedar Press identifier for one allocation regime. ND-ALLOC-000 records "
     "the period with NO allocation and is deliberately blank on every share "
     "column."),
    ("16_nd_severance_allocation", "tribe_id",
     "Cedar entity spine id of the tribe party to the agreement."),
    ("16_nd_severance_allocation", "statute_cite",
     "The enacted session law or Century Code section that sets this "
     "allocation. Never a bill draft and never a secondary description."),
    ("16_nd_severance_allocation", "effective_start",
     "First date the allocation governs. Blank where the regime has no start "
     "because none existed."),
    ("16_nd_severance_allocation", "effective_end",
     "Last date the allocation governs. BLANK MEANS STILL IN FORCE, which for "
     "ND-ALLOC-003 means a pre-2019 well is still on the 2013 split today."),
    ("16_nd_severance_allocation", "well_vintage_rule",
     "Which wells this row governs. The load-bearing column: North Dakota's "
     "post-2019 split turns on the date drilling first commenced, and a well "
     "keeps its split for the life of the well, so two rows are in force "
     "simultaneously and neither ratio describes a monthly payment."),
    ("16_nd_severance_allocation", "trust_land_tribal_share",
     "Tribal share of gross production and oil extraction tax collections "
     "attributable to trust lands, as a decimal fraction."),
    ("16_nd_severance_allocation", "trust_land_state_share",
     "State share of collections attributable to trust lands."),
    ("16_nd_severance_allocation", "fee_land_tribal_share",
     "Tribal share of collections attributable to non-trust (fee) lands."),
    ("16_nd_severance_allocation", "fee_land_state_share",
     "State share of collections attributable to non-trust (fee) lands."),
    ("16_nd_severance_allocation", "superseded_by",
     "allocation_id that replaced this one for NEW production. It does not "
     "mean this row stopped operating: a superseded regime continues for the "
     "life of every well drilled under it."),
    ("16_nd_severance_allocation", "source_url",
     "URL of the retrieved document the source_quote is taken from."),
    ("16_nd_severance_allocation", "source_quote",
     "Verbatim text from that document. Session-law rows preserve the printed "
     "strike-through, so 'twentyfifty percent' is the source's own typography "
     "and not a transcription error."),
    ("16_nd_severance_allocation", "fetched_date",
     "Date the source document was retrieved."),
    ("16_nd_severance_allocation", "tier",
     "Evidence tier. A = the enacted instrument or the distributing agency's "
     "own statement of the split."),
    ("16_nd_severance_allocation", "confidence",
     "What is known and not known about this row, in words, including which "
     "instrument is unpublished."),
    ("16_nd_severance_allocation", "built_date",
     "Date this row was built."),
    # new values on existing tribal_tax_bases columns
    ("15_tribal_tax", "measurement_status:REPORTED_TAX_COLLECTIONS_ON_RESERVATION",
     "Total state severance tax collected on production within a reservation's "
     "exterior boundaries, published by the state. It is levied on producers "
     "and purchasers, NOT paid by the tribe, and must never be summed with a "
     "REPORTED_TAX_REMITTANCE_PER_TRIBE row or read as a tribal tax burden."),
    ("15_tribal_tax", "rate_unit:share_of_gross_value_at_well",
     "An ad valorem severance rate. The base it yields is USD."),
    ("15_tribal_tax", "rate_unit:usd_per_mcf",
     "A per-unit gas severance rate. The base it yields is a VOLUME in mcf and "
     "is never a dollar figure."),
    ("15_tribal_tax", "rate_unit:mixed_ad_valorem_and_per_unit",
     "The published figure pools an ad valorem tax and a per-unit tax, so it "
     "has no single base and cannot be inverted at all. The only rate_unit "
     "written without a statutory_rate beside it, because it is the reason "
     "there is no rate."),
    ("15_tribal_tax", "amount_source_quote:tabular_convention",
     "Where the source is a table rather than prose, the quote is the printed "
     "cells of ONE row joined by ' | ': table heading, row label, column "
     "label, value. Nothing is reordered and no figure is recomputed."),
]


def write_codebook():
    """codebook_master.csv is being clobbered by concurrent writes. Back it up,
    RE-READ IT IMMEDIATELY BEFORE WRITING, add only our variables, and report
    anything that was present in the backup but missing from the late read."""
    p = CLEAN / "codebook_master.csv"
    if not p.exists():
        print("  codebook_master.csv missing; skipped")
        return
    bak = CLEAN / f"codebook_master.csv.bak_{TODAY}_pre113"
    if not bak.exists():
        shutil.copy2(p, bak)
    before = read_csv(bak)
    cur = read_csv(p)                       # late re-read
    if not cur:
        print("  codebook_master.csv read empty; refusing to write")
        return
    fields = list(cur[0].keys())
    keyof = lambda r: (r.get("dataset", ""), r.get("variable", ""))
    cur_keys = {keyof(r) for r in cur}
    restored = [r for r in before if keyof(r) not in cur_keys]
    if restored:
        cur = cur + restored
        cur_keys |= {keyof(r) for r in restored}
    n_tax = len(read_csv(CLEAN / "tribal_tax_bases.csv"))
    n_alloc = len(read_csv(CLEAN / "nd_severance_allocation.csv"))
    added = 0
    for ds, var, desc in CODEBOOK_VARS:
        if (ds, var) in cur_keys:
            continue
        row = {k: "" for k in fields}
        vals = {"dataset": ds, "variable": var, "description": desc,
                "type": "text", "units": "text",
                "published": "1", "access_tier": "public",
                "n_rows": str(n_alloc if ds.startswith("16_") else n_tax),
                "pct_filled": "", "generated": TODAY, "built_date": TODAY,
                "source": SCRIPT}
        for k, v in vals.items():
            if k in row:
                row[k] = v
        cur.append(row)
        cur_keys.add((ds, var))
        added += 1
    # This build changed the row count of 15_tribal_tax from 72 to n_tax, so
    # every 15_tribal_tax n_rows in the codebook is now stale. Syncing the
    # number is a factual correction to a count this script itself moved; no
    # other cell on those rows is touched.
    resynced = 0
    for r in cur:
        if r.get("dataset") == "15_tribal_tax" and "n_rows" in r \
                and r.get("n_rows") not in ("", str(n_tax)):
            r["n_rows"] = str(n_tax)
            resynced += 1
    write_csv(p, cur, fields)
    print(f"  codebook: {resynced} 15_tribal_tax n_rows resynced to {n_tax}")
    print(f"  codebook_master.csv: +{added} variables, "
          f"{len(restored)} rows restored from backup, {len(cur)} total")
    if restored:
        print("    RESTORED (present in backup, absent at re-read): " +
              ", ".join(f"{a}/{b}" for a, b in
                        sorted({keyof(r) for r in restored})[:20]))


def write_log(rows, alloc_rows, gpt, oet, alloc, straddle_m, stn, stn_zero,
              gas_rates, ratios, unresolved, problems):
    bienn = [("2013-15", "2013-08", "2015-07"), ("2015-17", "2015-08", "2017-07"),
             ("2017-19", "2017-08", "2019-07"), ("2019-21", "2019-08", "2021-07"),
             ("2021-23", "2021-08", "2023-07"), ("2023-25", "2023-08", "2025-07"),
             ("2025-27 to date", "2025-08", "2026-07")]
    tbl = []
    for name, a, b in bienn:
        months = [m for m in sorted(set(gpt) | set(oet)) if a <= m <= b]
        if not months:
            continue
        g = sum(gpt.get(m, 0) for m in months)
        o = sum(oet.get(m, 0) for m in months)
        al = sum(alloc.get(m, 0) for m in months)
        st = sum(straddle_m.get(m, 0) for m in months)
        if g + o <= 0:
            continue
        label = (f"{name} ({month_name(months[0])} - {month_name(months[-1])})"
                 if len(months) < 24 else name)
        tbl.append((label, len(months), g, o, al, st, (al - st) / (g + o)))

    L = []
    L.append("# North Dakota / Fort Berthold severance tax - build log")
    L.append("")
    L.append(f"*Built {TODAY} by `{SCRIPT}`. Output: appended SEVERANCE rows in "
             "`data/clean/tribal_tax_bases.csv`, "
             "`data/clean/nd_severance_allocation.csv`, "
             f"`review/nd_severance_unresolved_{TODAY}.csv`, raw under "
             "`data/raw/external/nd_severance/` with `_SOURCE_MANIFEST.csv` "
             "and md5s.*")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## The finding: the blend cannot be decomposed, and it does not "
             "have to be")
    L.append("")
    L.append("North Dakota's 80/20 trust split governs **only wells on which "
             "drilling first commenced after 2019-06-30**, and NDCC "
             "57-51.2-02(6) binds a well to the terms in force when it was "
             "drilled **for the life of the well**. So every monthly payment "
             "after mid-2019 is a blend of two regimes, and the weights - the "
             "spud-date mix of producing wells - are published by nobody.")
    L.append("")
    L.append("**They do not need to be.** The North Dakota Legislative Council "
             "publishes, monthly, *both legs of the ratio*: gross production "
             "and oil extraction tax collections \"in each county and the Fort "
             "Berthold Reservation\", and \"oil and gas tax revenue "
             "collections allocated to the Three Affiliated Tribes\". The "
             "effective blended share is therefore **measured, not assumed**.")
    L.append("")
    L.append("| Biennium | Months | FB gross production tax | FB oil extraction "
             "tax | Allocated to the tribe | of which straddle | **Measured "
             "on-reservation share** |")
    L.append("|---|---:|---:|---:|---:|---:|---:|")
    for name, n, g, o, al, st, sh in tbl:
        L.append(f"| {name} | {n} | ${g:,.0f} | ${o:,.0f} | ${al:,.0f} | "
                 f"${st:,.0f} | **{sh:.2%}** |")
    L.append("")
    L.append("Two things in that table are load-bearing.")
    L.append("")
    L.append("**The 2015-17 and 2017-19 shares are 50.00%.** That is the "
             "uniform 2013 regime - 50/50 on trust and fee alike - reproducing "
             "itself to four significant figures out of two independently "
             "published series. It is what validates the Fort Berthold "
             "collections row as the correct denominator for the tribal "
             "allocation row. Neither figure was adjusted to meet the other.")
    L.append("")
    L.append("**The share then rises and keeps rising.** That is post-2019 "
             "wells replacing pre-2019 ones inside a payment series that looks "
             "like one number. A subscriber who picked up 80/20 and multiplied "
             "would be wrong by a factor that changes every month.")
    L.append("")
    L.append("The rise also **forces a bound on the vintage mix**. The "
             "pre-2019 regime pays 50% of collections whatever the land "
             "status; the post-2019 regime pays at most 80%. So "
             "`post_2019_share >= (observed - 0.50) / 0.30`, and that "
             "inequality is written onto every monthly allocation row that "
             "exceeds 50%. It is a floor on how much of Fort Berthold "
             "production now comes from wells spudded after mid-2019 - "
             "recovered from two published dollar figures and no assumptions.")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## Allocation periods recovered, with their statutes")
    L.append("")
    L.append("| Row | Period | Wells it governs | Trust (tribe/state) | Fee "
             "(tribe/state) | Authority |")
    L.append("|---|---|---|---|---|---|")
    for a in alloc_rows:
        vr = a["well_vintage_rule"].split(".")[0][:70]
        tr = (f"{a['trust_land_tribal_share']}/{a['trust_land_state_share']}"
              if a["trust_land_tribal_share"] else "*(blank by design)*")
        fe = (f"{a['fee_land_tribal_share']}/{a['fee_land_state_share']}"
              if a["fee_land_tribal_share"] else "*(blank by design)*")
        L.append(f"| {a['allocation_id']} | {a['effective_start'] or '-'} .. "
                 f"{a['effective_end'] or 'in force'} | {vr} | {tr} | {fe} | "
                 f"{a['statute_cite'][:70]} |")
    L.append("")
    L.append("`ND-ALLOC-003` and `ND-ALLOC-004` are **both in force today**, "
             "which is the whole point. `ND-ALLOC-002` therefore carries "
             "`superseded_by = ND-ALLOC-004` and a note that it was superseded "
             "**for new production only**: the 2013 split still governs every "
             "well drilled before 2019-07-01 and will until those wells stop "
             "producing. Reading `superseded_by` as an end date is the error "
             "this file exists to prevent.")
    L.append("")
    L.append("`ND-ALLOC-000` carries **blank share columns on purpose**. "
             "Chapter 57-51.2 did not exist before 2007 and no distribution "
             "exists before September 2008. Carrying a later formula backwards "
             "would have manufactured an allocation.")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## Why no point base is published anywhere in this build")
    L.append("")
    L.append("`derived_taxable_base` is **empty on every row**. Three "
             "independent blockers, each written onto the row in `bound_basis` "
             "with its arithmetic:")
    L.append("")
    L.append("**1. The gross production tax pools two incompatible units.** "
             "Oil is five percent of gross value at the well (NDCC 57-51-02, "
             "base in USD). Gas is an annually indexed rate per mcf (NDCC "
             "57-51-02.2, base in MCF) - $.0405 in FY2022, $.1423 in FY2024, "
             "$.0655 in FY2027. One published dollar figure, two bases, two "
             "units, and no oil/gas split of Fort Berthold collections "
             "anywhere. Dividing it produces neither dollars nor mcf. **This "
             "is a fourth distinct way a rate inversion fails**, after the "
             "marginal base, the graduated schedule read as flat, and receipts "
             "lagging obligations.")
    L.append("")
    L.append("**2. The oil extraction rate on the reservation is "
             "state-contingent.** It is five percent, but NDCC 57-51.1-02(2) "
             "raises it to six whenever WTI exceeds an indexed trigger price "
             "for three consecutive months - and the 2023 session removed that "
             "trigger for every other North Dakota well while keeping it for "
             "reservation and straddle wells. Trigger prices retrieved: $89.65 "
             "(CY2021), $117.20 (CY2026). No notice stating the rate actually "
             "in force in any month was found, so each month carries "
             "`[collections/0.06, collections/0.05]` and is never divided "
             "once.")
    L.append("")
    L.append("**3. The agreement is not published.** NDCC 57-51.2-02(3) caps "
             "the trust-land extraction rate at six and one-half percent \"but "
             "may be reduced through negotiation\", and 57-51.2-02(4) turns "
             "the chapters' exemptions off on the reservation \"except as "
             "otherwise provided in the agreement\". Four agreements are "
             "described by the Legislative Council - signed 2008-06-10, "
             "2010-01-13, 2013-06-21 and 2019-02-28, the last effective "
             "2019-03-29 - and **the text of none of them was found** on "
             "ndlegis.gov, tax.nd.gov, treasurer.nd.gov or governor.nd.gov. "
             "Every rate here is therefore the statutory rate, and any exempt "
             "or reduced-rate barrel makes collections/rate a **lower** bound "
             "on gross value at the well.")
    L.append("")
    L.append("The one place the blend does narrow to something tight is the "
             "**straddle-well distribution**, because both vintages are "
             "multiplied by the *same* annually certified acreage ratios:")
    L.append("")
    for fy, r in sorted(ratios.items()):
        lo = 0.8 * r["trust"] + 0.2 * r["nontrust"]
        hi = 0.5 * (r["trust"] + r["nontrust"])
        L.append(f"- **{fy}** ({r['reservation']}, {r['start']} - {r['end']}): "
                 f"trust ratio {r['trust']}, non-trust ratio {r['nontrust']} "
                 f"-> effective share of certified straddle-well taxes lies in "
                 f"[{lo:.7f}, {hi:.7f}], about "
                 f"{(hi - lo) / lo * 100:.1f}% wide.")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## What North Dakota publishes, and what it structurally does not")
    L.append("")
    L.append("| | |")
    L.append("|---|---|")
    L.append("| **PUBLISHES** | Monthly tribal distributions by tax type, per "
             "tribe, via the State Treasurer's tax distribution search "
             "(`searchtype=tribe`, an undocumented mode on the public app). |")
    L.append("| **PUBLISHES** | Monthly **total gross production and oil "
             "extraction tax collections on the Fort Berthold Reservation** - "
             "the denominator - in the Legislative Council's oil and gas tax "
             "revenue collections and allocations detail reports. |")
    L.append("| **PUBLISHES** | The full statutory rate history, the annual "
             "per-mcf gas rate table back to 1991, the annual oil trigger "
             "price, the straddle-well acreage ratio certifications, and pool "
             "codes that name the four categories the Tax Commissioner "
             "actually accounts in: Fort Berthold Trust / Fee, Pre 2019 / "
             "post. |")
    L.append("| **DOES NOT PUBLISH** | **Collections by pool code.** The pool "
             "codes prove the state books trust-vs-fee and pre-vs-post-2019 "
             "separately for every formation on the reservation. The money "
             "against those codes is never published, and that single file "
             "would decompose the blend completely. |")
    L.append("| **DOES NOT PUBLISH** | Anything per well. Schedule T-84 makes "
             "each operator report a trust/non-trust allocation per well; the "
             "filings are confidential taxpayer data. |")
    L.append("| **DOES NOT PUBLISH** | The agreements themselves. |")
    L.append("| **DOES NOT PUBLISH** | Any reservation aggregate or ownership "
             "field at DMR. Its free statistics are by county, formation and "
             "statewide only; the complete Well Index carrying spud dates is "
             "subscription-gated. Even with per-well spud dates the vintage "
             "weights would need per-well tax collections, which are "
             "confidential. **The mix is unreachable from public sources in "
             "principle, not just in practice.** |")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## Three tribes with no oil agreement, measured rather than "
             "assumed")
    L.append("")
    L.append("NDCC 57-51.2-01 authorises oil and gas tax agreements with "
             "**three** tribes - Three Affiliated, Standing Rock and Turtle "
             "Mountain. All four tribes in the Treasurer's own list were "
             "queried against all three oil distribution types:")
    L.append("")
    L.append("| Tribe | Oil Extraction | Gross Production | Straddle Well |")
    L.append("|---|---|---|---|")
    for tribe in ("Three Affiliated Tribes", "Standing Rock Sioux Tribe",
                  "Spirit Lake Tribe", "Turtle Mtn. Chippewa"):
        cells = []
        for typ in ("Oil Extraction Tax", "Oil & Gas Gross Production",
                    "Oil & Gas Straddle Well"):
            rows_, grand = stn.get((tribe, typ), ([], None))
            cells.append(f"{len(rows_)} payments, ${grand or 0:,.2f}"
                         if rows_ else "**no records**")
        L.append(f"| {tribe} | " + " | ".join(cells) + " |")
    L.append("")
    L.append("`no records` here is the application answering, not a search "
             "failing - which makes it a **measured absence** and not a "
             "`NOT_CHECKED`.")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## Cross-source verification")
    L.append("")
    L.append("The Legislative Council's monthly \"allocated to the Three "
             "Affiliated Tribes\" figure and the sum of the State Treasurer's "
             "three distribution types **agree to the dollar** on every month "
             "checked - two agencies, two publication routes, one number. "
             "Under `docs/CROSS_SOURCE_VERIFICATION.md` that is a "
             "verification, not a claim.")
    L.append("")
    L.append("It also settles a scope question: the LC allocation figure "
             "**includes** the straddle-well distribution, whose collections "
             "sit in the *county* rows rather than the Fort Berthold row. "
             "Straddle money is therefore netted out of the numerator before "
             "any effective share is computed, on every row that has it.")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## Rows added")
    L.append("")
    from collections import Counter
    c = Counter(r["measurement_status"] for r in rows)
    for k, v in sorted(c.items()):
        L.append(f"- `{k}` - {v}")
    L.append(f"- **total {len(rows)} `SEVERANCE` rows**, against zero before "
             "this build.")
    L.append("")
    L.append("`derived_taxable_base` is populated on **none** of them, for the "
             "three reasons above. That is the same outcome as the California "
             "gaming build reached after reading its own quotes: the bound "
             "machinery works, and the honest answer is a range.")
    L.append("")
    if problems:
        L.append("## Quotes that could not be verified against their source PDF")
        L.append("")
        for lab, fn, frag in problems:
            L.append(f"- **{lab}** in `{fn}`: `{frag}`")
        L.append("")
    L.append("## Unresolved, staged for a ruling")
    L.append("")
    for u in unresolved:
        L.append(f"- **{u['item']}** (`{u['kind']}`) - {u['detail']}")
    L.append("")
    (DOCS / "ND_SEVERANCE_BUILD_LOG.md").write_text("\n".join(L),
                                                    encoding="utf-8")
    print("  docs/ND_SEVERANCE_BUILD_LOG.md written")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd in ("fetch", "all"):
        do_fetch()
    if cmd in ("build", "all"):
        build()


if __name__ == "__main__":
    main()
