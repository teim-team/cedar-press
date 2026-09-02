#!/usr/bin/env python3
r"""
Cedar Press - 116: North Dakota per-tribe NON-GAMING tax distributions.

WHY THIS EXISTS
---------------
`docs/TRIBAL_TAX_BUILD_LOG.md` states, in as many words, that "no tribe in this
dataset yet carries a per-tribe non-gaming tax amount", and that the netting
machinery in `docs/TRIBAL_TAX_DECOMPOSITION.md` is therefore "built, tested and
idle". Script 113 found, while building the Fort Berthold severance series, that
the same North Dakota State Treasurer application publishes per-tribe monthly
amounts for four more taxes and left them out of scope with the raw NOT retained
(nothing for those four types appears in
`data/raw/external/nd_severance/_SOURCE_MANIFEST.csv`).

This build closes that. It is the FIRST per-tribe non-gaming tax money in the
dataset, and Washington - the fullest fuel-agreement roster in the country -
cannot supply it, because Washington deems per-tribe fuel data "personal
information and exempt from public inspection and copying". North Dakota does
not withhold it.

WHAT NORTH DAKOTA PUBLISHES THAT NOBODY ELSE DOES
-------------------------------------------------
For the motor fuel series, the Legislative Council prints BOTH LEGS OF THE
DIVISION in one paragraph: the statutory rate ("at a rate of 23 cents per
gallon") AND the per-tribe allocation percentage under each agreement (87, 76,
70 and 96 percent, each less a one percent administration fee). That is what a
derived base needs and what no other state in this dataset has supplied.

A DISTRIBUTION IS NOT A BASE, AND TWO DIVISIONS ARE NEEDED
----------------------------------------------------------
Every amount here is what the state DISTRIBUTED TO a tribe under a tax
agreement. That is a share of collections. Recovering a taxable base takes two
divisions and each needs its own quoted rate:

    payment / tribal_allocation_share = tax collected within the reservation
    tax collected / statutory_rate    = the taxable base

Where only one of the two is published, `derived_taxable_base` stays BLANK and
`measurement_status` stays at the reported level. The arithmetic that would have
been done, and the reason it was not, is written onto the row in `bound_basis`.

THE FOUR DOCUMENTED WAYS A RATE INVERSION FAILS, CHECKED ON ALL FOUR TAXES
--------------------------------------------------------------------------
1. MARGINAL BASE. Checked. NDCC 57-43.1-02(1) and 57-43.2-02(1) read "a tax of
   twenty-three cents per gallon ... on all motor vehicle fuel sold or used in
   this state" - no "in excess of", no threshold. The allocation percentages are
   flat shares of collections, not marginal.
2. GRADUATED SCHEDULE READ AS FLAT. This one FIRES, three times, and kills three
   of the four derivations:
     - cigarette/tobacco: 22 mills per cigarette (57-36-06 plus 57-36-32) AND
       28% of wholesale purchase price on cigars and pipe tobacco (57-36-25(1))
       AND 60 cents per ounce on snuff AND 16 cents per ounce on chewing tobacco
       (57-36-25(2)). Four bases in one agreement.
     - sales: the Standing Rock agreement required a 5% general rate, 3% on new
       manufactured homes, 7% alcohol gross receipts, 3% farm machinery, plus a
       .25% tribal local tax. Five rates in one distribution.
     - alcohol: 5-03-07 is a SIX-TIER per-gallon schedule by product class,
       $.08 to $4.05 per wine gallon.
3. RECEIPTS LAG OBLIGATIONS. The Treasurer publishes a PAYMENT DATE and North
   Dakota publishes no statement of which collection period each payment
   settles. Every row therefore carries the payment date as its period and says
   so. The Standing Rock sales tax series is the live case: state administration
   of those taxes was discontinued 2017-03-07 and payments continue to 2019-03.
4. MIXED UNITS IN ONE FIGURE. Fires on alcohol: NDCC 57-39.10-07 and -09 pay the
   alcoholic beverages WHOLESALE tax (per wine gallon, six tiers) and the
   alcoholic beverages GROSS RECEIPTS tax (seven percent ad valorem, 57-39.6-02)
   out of the SAME "tribal allocation fund", and the Treasurer's label is
   "Tribal Alcohol" for both. One published figure, two units.

So exactly ONE of the four taxes derives a base, and it derives a VOLUME in
gallons - never dollars. That is rule 1 of docs/TRIBAL_TAX_DECOMPOSITION.md.

TWO THINGS THIS BUILD REFUSES TO DO
-----------------------------------
* It does not publish the "County Sales Tax" distributions the same application
  shows for the Standing Rock Sioux Tribe (21 payments, measured here). No
  instrument authorising a county sales tax distribution to a tribe was
  retrieved, and rule 4 forbids publishing a bare tribal tax figure whose
  authority is unstated. Measured, staged for a ruling, not published.
* It does not run per-tax-type absence probes. The application VALIDATES its
  DistType parameter against an unpublished code list and answers an unknown
  code with "Unable to Process" - an application error, not an empty result. A
  naive per-type sweep would manufacture false absences. Absence is instead
  measured from each tribe's COMPLETE distribution listing, which foots to the
  application's own printed Grand Total.

RUN
    py -3 code/116_build_nd_tribal_taxes.py fetch
    py -3 code/116_build_nd_tribal_taxes.py build
    py -3 code/116_build_nd_tribal_taxes.py all

WRITES
    data/raw/external/nd_tribal_tax/**   + _SOURCE_MANIFEST.csv (md5s, status)
    data/clean/tribal_tax_bases.csv      (APPEND ONLY, re-read immediately first)
    data/clean/codebook/15_tribal_tax.csv (FRAGMENT only, never the master)
    review/nd_tribal_tax_unresolved_<date>.csv
    docs/ND_TRIBAL_TAX_LOG.md

TOUCHES NOTHING ELSE. Never writes nd_severance_allocation.csv,
resource_revenue.csv, prime_contracts.csv, federal_funding_transactions.csv,
subawards.csv, gaming_*, nigc_*, compact_*, ca_gaming_*, wa_*, fl_*, np_*,
entity_*, the identifier ledger, the spine or codebook_master.csv. Never
contacts api.usaspending.gov or files.usaspending.gov.
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
import urllib.parse
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
LOGS = CEDAR / "logs"
DOCS = CEDAR / "docs"
RAW = CEDAR / "data" / "raw" / "external" / "nd_tribal_tax"
FRAG = CLEAN / "codebook"

TODAY = date.today().isoformat()
SCRIPT = "code/116_build_nd_tribal_taxes.py"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# Two other agents are pulling from these right now. Never.
BANNED_HOSTS = {"api.usaspending.gov", "files.usaspending.gov"}

STATE = "ND"

# --------------------------------------------------------------------------
# Schema of data/clean/tribal_tax_bases.csv, unchanged (scripts 108 and 113).
# --------------------------------------------------------------------------
FIELDS = [
    "tax_observation_id", "tribe_id", "tribe_name", "state", "tax_type",
    "period_start", "period_end", "tax_remitted_usd", "statutory_rate",
    "rate_unit", "derived_taxable_base", "base_unit", "rate_source_quote",
    "amount_source_quote", "agreement_or_statute_cite", "measurement_status",
    "bound_basis", "source_url", "fetched_date", "tier", "confidence",
    "built_date",
]

# ID BLOCK. Script 113 owns `TTAX-ND-####` and re-numbers by counting rows whose
# id startswith "TTAX-ND-". `TTAX-NDT-####` does NOT match that prefix, so
# neither script can renumber the other's rows on a re-run.
ID_PREFIX = "TTAX-NDT-"

TAX_TYPES = {"MOTOR_FUEL", "TOBACCO", "RETAIL_SALES", "ALCOHOL"}

STATUS_PER_TRIBE_AMOUNT = "REPORTED_TAX_REMITTANCE_PER_TRIBE"
STATUS_RATE_ONLY = "RATE_ONLY_NO_AMOUNT"
STATUS_DERIVED_BASE = "DERIVED_TAXABLE_BASE"
STATUS_AGREEMENT_ROSTER = "AGREEMENT_ROSTER_NO_AMOUNT"
# NEW in this build. The tribe is IN the publishing application's own tribe list
# and its complete distribution listing contains no payment of this tax type.
# That is a measured absence, not a blank and not a NOT_CHECKED.
STATUS_MEASURED_ABSENCE = "MEASURED_ABSENCE_NO_DISTRIBUTION"

MEASUREMENT_STATUSES = frozenset({
    STATUS_PER_TRIBE_AMOUNT, STATUS_RATE_ONLY, STATUS_DERIVED_BASE,
    STATUS_AGREEMENT_ROSTER, STATUS_MEASURED_ABSENCE,
})

# Rule 1 in code form: what unit a rate is levied on decides what unit its base
# comes out in. A per-gallon rate can never yield dollars.
RATE_UNIT_TO_BASE_UNIT = {
    "usd_per_gallon": "gallons",
    "usd_per_cigarette": "cigarettes",
    "share_of_wholesale_purchase_price": "usd",
    "share_of_gross_receipts": "usd",
    "share_of_state_tax_collected": "usd",
    "usd_per_ounce": "ounces",
    # No single base exists for these two. They are written WITHOUT a
    # statutory_rate, because they are the reason there is no rate.
    "mixed_ad_valorem_and_per_unit": None,
    "mixed_per_unit_schedule_by_product_class": None,
}

FORECAST_WORDS = re.compile(
    r"\b(estimate[ds]?|estimating|estimation|predict(?:ed|s|ion)?|"
    r"forecast(?:ed|s)?|confidence interval|margin of error|projected|"
    r"modell?ed)\b", re.I)

OUR_TEXT_COLUMNS = ("measurement_status", "bound_basis", "confidence",
                    "base_unit", "rate_unit")


# ==========================================================================
# Shared resolver and domain. Standing rule 8: never re-implement matching.
# ==========================================================================
def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, CODE / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_spine():
    with (SPINE / "cedar_entity_spine.csv").open(
            encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


# --------------------------------------------------------------------------
# THE ONE HAND RULING IN THIS BUILD, WITH ITS EVIDENCE
# --------------------------------------------------------------------------
# `resolve_entity("Turtle Mtn. Chippewa", spine)` returns no_spine_match, which
# script 113 already staged. It now blocks REAL MONEY - 189 motor fuel payments
# totalling $10.8M - so it has to be settled rather than left.
#
# It is settled by EVIDENCE, not by loosening the matcher. AGENTS.md permits
# containment only "to resolve an owner already named in evidence", and the
# owner IS named: the North Dakota Legislative Council states that the state's
# motor vehicle fuel and special fuel tax agreement is with "The Turtle Mountain
# Band of Chippewa Indians" and "became effective September 1, 2010", and the
# Treasurer's first Turtle Mountain distribution is 2010-11-15. Two published
# sources, one agreement, one tribe.
#
# The guard is a UNIQUENESS check, not a similarity score: the build asserts
# that exactly one federally recognised tribe in North Dakota carries "Turtle
# Mountain" in its canonical name, and that the Legislative Council's own full
# name resolves to that same id through the shared resolver. If either fails,
# the build refuses to key the dollars.
HAND_RULED_ALIASES = {
    "Turtle Mtn. Chippewa": dict(
        full_name="Turtle Mountain Band of Chippewa Indians",
        must_contain="turtle mountain",
        evidence=("North Dakota Legislative Council, Tribal and State Relations "
                  "Committee background memorandum 27.9066.01000 (August 2025): "
                  "'The Turtle Mountain Band of Chippewa Indians, which became "
                  "effective September 1, 2010, provides for a revenue "
                  "allocation of 96 percent, less a 1 percent administration "
                  "fee, to the tribe.' The Treasurer's first Turtle Mountain "
                  "distribution is 2010-11-15.")),
}

# The Treasurer application's tribe list. Ids 5 and 6 were probed and the
# application answers "Unable to Process" - it errors on an id outside its own
# list rather than returning an empty result, which is what closes the list at
# four.
STN_TRIBES = {"1": "Standing Rock Sioux Tribe", "2": "Spirit Lake Tribe",
              "3": "Three Affiliated Tribes", "4": "Turtle Mtn. Chippewa"}
STN_PROBE_IDS = ["5", "6"]

# Treasurer distribution-type label -> Cedar tax_type. Labels are read off the
# results table, never guessed.
TYPE_TO_TAX_TYPE = {
    "Tribal Highway Tax": "MOTOR_FUEL",
    "Tribal Cigarette": "TOBACCO",
    "Tribal Sales Tax": "RETAIL_SALES",
    "Tribal Alcohol": "ALCOHOL",
}
# Present in the same listing, deliberately NOT published. See the docstring.
TYPE_REFUSED = {"County Sales Tax"}
# Oil types belong to script 113 and are not touched here.
TYPE_OWNED_BY_113 = {"Oil Extraction Tax", "Oil & Gas Gross Production",
                     "Oil & Gas Straddle Well"}


# ==========================================================================
# FETCH. One lock per host. Single shot, no poller. HTTP status recorded per
# file, because a 404 body still parses.
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
            print(f"  [lock] {host} held by {cur.get('script')}; queued, exiting")
            return False
    p.write_text(json.dumps({
        "host": host, "pid": os.getpid(), "script": SCRIPT,
        "claimed_at": datetime.now(timezone.utc).isoformat(),
        "active": False,
        "policy": "single-shot document fetch, no retry loop",
        "note": note, "queue": [],
    }, indent=1), encoding="utf-8")
    return True


def host_of(url):
    return re.sub(r"^https?://([^/]+).*", r"\1", url)


def http_get(url, dest):
    host = host_of(url)
    if host in BANNED_HOSTS:
        raise RuntimeError(f"refusing banned host {host}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.run(
        ["curl", "-s", "-L", "-A", UA, "--max-time", "300",
         "-w", "%{http_code}", "-o", str(dest), url],
        capture_output=True, text=True)
    status = int((p.stdout or "0").strip() or 0)
    body = dest.read_bytes() if dest.exists() else b""
    return status, body


def md5(b):
    return hashlib.md5(b).hexdigest()


# --------------------------------------------------------------------------
# SOURCES
# --------------------------------------------------------------------------
CENCODE = "https://ndlegis.gov/cencode"
TAXND = "https://www.tax.nd.gov"

DOC_SOURCES = [
    # --- statute: the taxes themselves --------------------------------------
    dict(key="ndcc_57_43_1", url=f"{CENCODE}/t57c43-1.pdf",
         path="statute/ndcc_t57c43-1_motor_vehicle_fuel_tax.pdf",
         publisher="North Dakota Legislative Branch",
         title="NDCC Chapter 57-43.1, Motor Vehicle Fuel Tax"),
    dict(key="ndcc_57_43_2", url=f"{CENCODE}/t57c43-2.pdf",
         path="statute/ndcc_t57c43-2_special_fuels_tax.pdf",
         publisher="North Dakota Legislative Branch",
         title="NDCC Chapter 57-43.2, Special Fuels Tax"),
    dict(key="ndcc_57_36", url=f"{CENCODE}/t57c36.pdf",
         path="statute/ndcc_t57c36_tobacco_products_tax.pdf",
         publisher="North Dakota Legislative Branch",
         title="NDCC Chapter 57-36, Tobacco Products Tax"),
    dict(key="ndcc_57_39_2", url=f"{CENCODE}/t57c39-2.pdf",
         path="statute/ndcc_t57c39-2_sales_tax.pdf",
         publisher="North Dakota Legislative Branch",
         title="NDCC Chapter 57-39.2, Sales Tax"),
    dict(key="ndcc_57_39_6", url=f"{CENCODE}/t57c39-6.pdf",
         path="statute/ndcc_t57c39-6_alcoholic_beverages_gross_receipts_tax.pdf",
         publisher="North Dakota Legislative Branch",
         title="NDCC Chapter 57-39.6, Alcoholic Beverages Gross Receipts Tax"),
    dict(key="ndcc_5_03", url=f"{CENCODE}/t05c03.pdf",
         path="statute/ndcc_t05c03_beer_and_liquor_wholesalers_taxation.pdf",
         publisher="North Dakota Legislative Branch",
         title="NDCC Chapter 5-03, Beer and Liquor Wholesalers - Taxation"),
    # --- statute: the state-tribal agreement chapters ------------------------
    dict(key="ndcc_57_39_8", url=f"{CENCODE}/t57c39-8.pdf",
         path="statute/ndcc_t57c39-8_state_tribal_sales_tax_agreements_REPEALED.pdf",
         publisher="North Dakota Legislative Branch",
         title=("NDCC Chapter 57-39.8, State-Tribal Sales, Use, and Gross "
                "Receipts Tax Agreements [REPEALED 2019]")),
    dict(key="ndcc_57_39_9", url=f"{CENCODE}/t57c39-9.pdf",
         path="statute/ndcc_t57c39-9_state_tribal_sales_tax_agreements.pdf",
         publisher="North Dakota Legislative Branch",
         title=("NDCC Chapter 57-39.9, State-Tribal Sales, Use, and Gross "
                "Receipts Tax Agreements")),
    dict(key="ndcc_57_39_10", url=f"{CENCODE}/t57c39-10.pdf",
         path="statute/ndcc_t57c39-10_state_tribal_alcohol_tobacco_agreements.pdf",
         publisher="North Dakota Legislative Branch",
         title=("NDCC Chapter 57-39.10, State-Tribal Alcohol, Tobacco, and "
                "Alcoholic Beverages Gross Receipts Tax Agreements")),
    # --- the document that prints BOTH legs of the fuel division -------------
    dict(key="lc_tsrc_memo",
         url=("https://ndlegis.gov/sites/default/files/resource/69-2025/"
              "committee-memorandum/27.9066.01000.pdf"),
         path="legislative_council/tribal_state_relations_background_memo_27.9066.01000.pdf",
         publisher="North Dakota Legislative Council",
         title=("Tribal and State Relations Committee Background Memorandum, "
                "August 2025")),
    # --- enacted session law creating 57-39.9 / 57-39.10 and repealing 57-39.8
    dict(key="sl_2019", url=("https://ndlegis.gov/assembly/66-2019/"
                             "session-laws/documents/TAXES.pdf"),
         path="session_laws/2019_66th_TAXES.pdf",
         publisher="North Dakota Legislative Branch",
         title="2019 Session Laws, Taxation (ch. 500, SB 2257; ch. 501, SB 2258)"),
    # --- Tax Commissioner rate histories -------------------------------------
    dict(key="hist_motor_fuel", url=f"{TAXND}/motor-fuel-tax-history",
         path="tax_commissioner/motor_fuel_tax_history.html",
         publisher="North Dakota Office of State Tax Commissioner",
         title="Motor Fuel Tax History"),
    dict(key="hist_cigarette",
         url=f"{TAXND}/cigarette-and-tobacco-products-tax-history",
         path="tax_commissioner/cigarette_and_tobacco_products_tax_history.html",
         publisher="North Dakota Office of State Tax Commissioner",
         title="Cigarette and Tobacco Products Tax History"),
    dict(key="hist_alcohol", url=f"{TAXND}/alcohol-tax-history",
         path="tax_commissioner/alcohol_tax_history.html",
         publisher="North Dakota Office of State Tax Commissioner",
         title="Alcohol Tax History"),
    dict(key="tax_native_american", url=f"{TAXND}/native-american",
         path="tax_commissioner/native_american.html",
         publisher="North Dakota Office of State Tax Commissioner",
         title="Native American"),
]


def stn_url(tribe_id, dist_code="", begin="1990-01-01", end="2026-12-31"):
    """Tax Distribution Search. `searchtype=tribe` is an undocumented mode on
    the public application and its result page is a GET whose parameters are
    base64-encoded. An EMPTY DistType returns EVERY distribution type for the
    tribe, which is what makes an absence measurable."""
    def b(s):
        return urllib.parse.quote(base64.b64encode(s.encode()).decode())
    return ("https://apps.nd.gov/stn/inquiry/results.aspx"
            f"?SearchType={b('tribe')}&PaymentDate={b(begin)}&EndDate={b(end)}"
            f"&City=&DistType={b(dist_code) if dist_code else ''}&County="
            f"&School=&Tribe={b(tribe_id)}"
            f"&Township=&ExcludeCity={b('False')}&ExcludeTownships={b('False')}"
            f"&ExcludeCounty={b('False')}&ExcludeSchool={b('False')}"
            f"&ExcludeTribe={b('False')}")


def stn_sources():
    out = []
    for tid, tname in STN_TRIBES.items():
        slug = tname.lower().replace(" ", "_").replace(".", "")
        out.append(dict(
            key=f"stn_all_{slug}", url=stn_url(tid),
            path=f"treasurer/stn_{slug}_all_distribution_types_1990_2026.html",
            publisher="North Dakota Office of State Treasurer",
            title=(f"Tax Distribution Search: {tname}, ALL distribution types, "
                   "1990-2026"),
            stn_tribe=tname, stn_tribe_id=tid))
    for pid in STN_PROBE_IDS:
        out.append(dict(
            key=f"stn_probe_{pid}", url=stn_url(pid),
            path=f"treasurer/stn_tribe_id_{pid}_boundary_probe.html",
            publisher="North Dakota Office of State Treasurer",
            title=(f"Tax Distribution Search: Tribe id {pid} - boundary probe "
                   "establishing that the application's tribe list ends at 4"),
            stn_tribe=None, stn_tribe_id=pid))
    return out


ALL_SOURCES = DOC_SOURCES + stn_sources()


def do_fetch():
    print("=== 116 fetch ===")
    RAW.mkdir(parents=True, exist_ok=True)
    for h in sorted({host_of(s["url"]) for s in ALL_SOURCES}):
        if h in BANNED_HOSTS:
            raise RuntimeError(f"banned host in source list: {h}")
        if not claim_host(h, "ND per-tribe non-gaming tax distributions: motor "
                             "fuel, cigarette, sales and alcohol, plus the "
                             "statutes and the Legislative Council memorandum "
                             "that state the rates"):
            print("  another script holds this host; queued and exiting fetch")
            return
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
        time.sleep(1.2)
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
def to_num(tok):
    t = tok.replace("$", "").replace(",", "").strip()
    neg = t.startswith("(") and t.endswith(")")
    t = t.strip("()")
    if not re.fullmatch(r"-?\d+(?:\.\d+)?", t):
        return None
    v = float(t)
    return -v if neg else v


def parse_stn(path):
    """ND Treasurer results page -> (rows, grand_total, page_state).

    `page_state` distinguishes three things that look alike and are completely
    different facts:
      RESULTS        - the application answered with payment rows
      NO_RECORDS     - the application answered 'No records found ...', $0.00
      UNABLE         - the application errored ('Unable to Process'). NOT an
                       absence. A broken answer is not evidence of absence.

    The grand total is scanned across the WHOLE line list, not only where the
    row loop happens to stop. Script 113's copy stops at len-3 and therefore
    never reaches the trailing 'Grand Total:' line, which is why its build log
    prints $0.00 against Three Affiliated Tribes rows that are worth $1.5bn.
    """
    s = path.read_bytes().decode("iso-8859-1")
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s)
    t = re.sub(r"<[^>]+>", "\n", t)
    t = HTML.unescape(t)
    L = [x.strip() for x in t.split("\n") if x.strip()]
    rows, grand, i = [], None, 0
    while i < len(L):
        if (i < len(L) - 3 and re.fullmatch(r"\d{2}/\d{2}/\d{4}", L[i])
                and to_num(L[i + 3]) is not None):
            mm, dd, yy = L[i].split("/")
            rows.append((f"{yy}-{mm}-{dd}", L[i + 1], L[i + 2],
                         to_num(L[i + 3])))
            i += 4
            continue
        if L[i] == "Grand Total:" and i + 1 < len(L):
            grand = to_num(L[i + 1])
        i += 1
    if any("Unable to Process" in x for x in L):
        state = "UNABLE"
    elif any("No records found" in x for x in L):
        state = "NO_RECORDS"
    elif rows:
        state = "RESULTS"
    else:
        state = "UNKNOWN"
    return rows, grand, state


def prev_day(iso):
    y, m, d = (int(x) for x in iso.split("-"))
    return date.fromordinal(date(y, m, d).toordinal() - 1).isoformat()


def pdf_flat_text(path):
    txt = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                         capture_output=True, text=True).stdout
    return " ".join(txt.split())


def html_flat_text(path):
    s = path.read_text(encoding="utf-8", errors="replace")
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s)
    t = re.sub(r"<[^>]+>", " ", t)
    return " ".join(HTML.unescape(t).split())


def verify_quote(quote, path, label, problems):
    """A quote is only a quote if it is in the file.

    Whitespace is normalised and nothing else. Bracketed metric conversions
    ([3.79 liters]) are tried BOTH ways because pdftotext keeps them and a
    stripped probe would silently match on the empty string.
    """
    flat = pdf_flat_text(path) if path.suffix.lower() == ".pdf" \
        else html_flat_text(path)
    base = " ".join(quote.split())
    base = base.split(" ... ")[0].split(" || ")[0].split(" | ")[0]
    stripped = " ".join(re.sub(r"\[.*?\]", " ", base).split())
    for probe in (base, stripped):
        if not probe.strip():
            continue
        if probe[:110] in flat or probe[:55] in flat:
            return True
    problems.append((label, path.name, base[:90]))
    return False


# ==========================================================================
# QUOTES. Each is lifted verbatim from a retrieved file and the build ASSERTS
# it is present in that file before writing it onto a row.
# ==========================================================================
Q_MVF_RATE = ("Except as otherwise provided in this section, a tax of "
              "twenty-three cents per gallon [3.79 liters] is imposed on all "
              "motor vehicle fuel sold or used in this state.")
Q_SF_RATE = ("Except as otherwise provided in this chapter, an excise tax of "
             "twenty-three cents per gallon [3.79 liters] is imposed on the "
             "sale or delivery of all special fuel sold or used in this state.")
Q_SF_EXCISE = ("Except as otherwise provided in this chapter, a special excise "
               "tax of two percent is imposed on all sales of propane and a tax "
               "of four cents per gallon is imposed on all sales of diesel fuel "
               "and other special fuels, which are exempted from the tax "
               "imposed under section 57-43.2-02.")
Q_MVF_HISTORY_2005 = ("The legislature provided for an increase in the tax "
                      "rates for both motor vehicle fuel and special fuels from "
                      "21 cents per gallon to 23 cents per gallon.")
Q_NA_FUEL_REFUND = (
    "A native American may file a claim with the tax commissioner for a refund "
    "of motor vehicle fuel taxes paid by that person under this chapter or "
    "special fuel taxes paid under chapter 57-43.2 if the motor vehicle fuel or "
    "special fuel was purchased from a retail fuel dealer located on the Indian "
    "reservation where the native American is an enrolled member and the fuel "
    "was delivered to the native American on that reservation.")
Q_NA_FUEL_FUND = (
    "A fuels tax refund reserve fund is created as a special fund in the state "
    "treasury. The tax commissioner shall deposit in that fund such amounts "
    "from motor vehicle fuel tax and special fuel tax collections as necessary "
    "to be expended for refunds to which native American government entities "
    "may be entitled under qualifying circumstances and conditions determined "
    "by the attorney general.")

Q_MEMO_FUEL_HEAD = (
    "The state has entered motor vehicle fuel and special fuel tax agreements "
    "with several tribes in the state. The tax applies to motor vehicle fuel "
    "and special fuel within the exterior boundaries of the reservation at a "
    "rate of 23 cents per gallon.")
Q_MEMO_FUEL = {
    "Standing Rock Sioux Tribe": (
        "The Standing Rock Sioux Tribe became effective January 1, 1999. A "
        "renegotiated agreement was signed on May 1, 2015, and provides for a "
        "revenue allocation of 87 percent, less a 1 percent administration fee, "
        "to the tribe. Thirteen percent, plus the 1 percent administration fee, "
        "is deposited in the general fund."),
    "Spirit Lake Tribe": (
        "The Spirit Lake Tribe, which became effective September 1, 2006, "
        "provides for a revenue allocation of 76 percent, less a 1 percent "
        "administration fee, to the tribe. Twenty-four percent, plus the 1 "
        "percent administration fee, is deposited in the general fund."),
    "Three Affiliated Tribes": (
        "The Three Affiliated Tribes of the Fort Berthold Reservation, which "
        "became effective September 1, 2007, provides for a revenue allocation "
        "of 70 percent, less a 1 percent administration fee, to the tribe. "
        "Thirty percent, plus the 1 percent administration fee, is deposited in "
        "the general fund."),
    "Turtle Mtn. Chippewa": (
        "The Turtle Mountain Band of Chippewa Indians, which became effective "
        "September 1, 2010, provides for a revenue allocation of 96 percent, "
        "less a 1 percent administration fee, to the tribe. Four percent, plus "
        "the 1 percent administration fee, is deposited in the general fund."),
}
# Tribal share of collections, AFTER the administration fee. The reading is
# forced by the source's own second sentence in each case: the two legs sum to
# exactly 100 percent only if the fee is one percentage POINT off the tribe's
# share (87 - 1 = 86 and 13 + 1 = 14), never a one percent haircut of it.
MEMO_FUEL_SHARE = {
    "Standing Rock Sioux Tribe": 0.86,
    "Spirit Lake Tribe": 0.75,
    "Three Affiliated Tribes": 0.69,
    "Turtle Mtn. Chippewa": 0.95,
}
# The date from which the memo's stated allocation is in force for that tribe.
# Standing Rock is the exception the memo itself flags: its agreement became
# effective 1999-01-01 but the memo states the allocation only for the
# RENEGOTIATED agreement signed 2015-05-01. The 1999-2015 allocation is not
# published, so no payment before 2015-05-01 is divided.
MEMO_FUEL_SHARE_FROM = {
    "Standing Rock Sioux Tribe": "2015-05-01",
    "Spirit Lake Tribe": "2006-09-01",
    "Three Affiliated Tribes": "2007-09-01",
    "Turtle Mtn. Chippewa": "2010-09-01",
}
MEMO_FUEL_AGREEMENT_FROM = {
    "Standing Rock Sioux Tribe": "1999-01-01",
    "Spirit Lake Tribe": "2006-09-01",
    "Three Affiliated Tribes": "2007-09-01",
    "Turtle Mtn. Chippewa": "2010-09-01",
}

Q_MEMO_CIGARETTE = (
    "On July 1, 1993, a collection agreement between the Tax Commissioner and "
    "the Standing Rock Sioux Tribe became effective. Under this agreement, the "
    "Standing Rock Sioux Tribe levies a cigarette and tobacco excise tax on all "
    "licensed wholesalers and distributors operating on the reservation. The "
    "tax rates are identical to the state tax rates. The Tax Department serves "
    "as an agent of the tribe in collecting the tax. Under the agreement, 87 "
    "percent of the tax, less a 1 percent administrative fee, is returned to "
    "the tribe. Thirteen percent, plus the 1 percent administrative fee, is "
    "deposited in the general fund. The terms of the renegotiated agreement "
    "became effective on May 1, 2015.")
Q_MEMO_SALES = (
    "The agreement, which became effective July 1, 2016, provided for an 80/20 "
    "tribal/state split of tax collections. The agreement required the Standing "
    "Rock Sioux Tribe to impose a 5 percent general sales and use tax, a 3 "
    "percent sales and use tax on new manufactured homes, a 7 percent alcohol "
    "gross receipts tax, and a 3 percent farm machinery gross receipts tax on "
    "new farm machinery and new farm irrigation equipment.")
Q_MEMO_SALES_END = (
    "On January 27, 2017, Tax Commissioner Ryan Rauschenberger issued a "
    "memorandum to North Dakota sales and use tax permitholders which provided "
    "\"[e]ffective March 7, 2017, the North Dakota Office of State Tax "
    "Commissioner will discontinue its administration of the Standing Rock "
    "Sioux Tribe's sales, use and farm machinery and alcohol gross receipts "
    "taxes including the tribal .25 percent local tax.\"")
Q_MEMO_ALCOHOL_2023 = (
    "The method of allocating revenue under an agreement for the collection and "
    "administration of alcoholic beverages wholesale tax and alcoholic "
    "beverages gross receipts tax was amended from one determined by "
    "multiplying the enrolled membership of the tribe by the tax revenue "
    "generated per capita for the respective tax type to a method which "
    "allocates 80 percent of the tax revenue to the tribe and 20 percent to the "
    "state.")

Q_CIG_RATE_06 = (
    "There are levied and assessed, and there must be collected and paid to the "
    "state tax commissioner, upon all cigarettes sold in this state, the "
    "following excise taxes, payment thereof to be made prior to the time of "
    "the sale and delivery thereof: 1. Class A. On cigarettes weighing not more "
    "than three pounds [1360.78 grams] per thousand, five mills on each such "
    "cigarette. 2. Class B. On cigarettes weighing more than three pounds "
    "[1360.78 grams] per thousand, five and one-half mills on each such "
    "cigarette.")
Q_CIG_RATE_32 = (
    "There is hereby levied and assessed and there shall be collected by the "
    "state tax commissioner and paid to the state treasurer, upon all "
    "cigarettes sold in this state, an additional tax, separate and apart from "
    "all other taxes, of seventeen mills on each cigarette")
Q_OTP_RATE = (
    "There is hereby levied and assessed upon all cigars and pipe tobacco sold "
    "in this state an excise tax at the rate of twenty-eight percent of the "
    "wholesale purchase price at which such cigars and pipe tobacco are "
    "purchased by distributors.")
Q_OTP_WEIGHT = (
    "There is levied and assessed upon all other tobacco products sold in this "
    "state an excise tax at the following rates: a. Upon each can or package of "
    "snuff, sixty cents per ounce and a proportionate tax at the like rate on "
    "all fractional parts of an ounce. b. On chewing tobacco, sixteen cents per "
    "ounce and a proportionate tax at the like rate on all fractional parts of "
    "an ounce.")
Q_SALES_RATE = (
    "Except as otherwise expressly provided in this chapter, there is imposed a "
    "tax of five percent upon the gross receipts of retailers from all sales at "
    "retail, including the leasing or renting of tangible personal property as "
    "provided in this section, within this state")
Q_ALC_GR_RATE = (
    "There is imposed a tax of seven percent on the gross receipts of retailers "
    "from all sales at retail of alcoholic beverages.")
Q_ALC_WHOLESALE_RATE = (
    "A tax is hereby imposed upon all alcoholic beverage wholesalers, domestic "
    "wineries, domestic distilleries, microbrew pubs, brewer taproom licensees, "
    "and direct shippers for the privilege of doing business in this state. The "
    "amount of this tax shall be determined by the gallonage according to the "
    "following schedule: | Beer in bulk containers - per wine gallon $.08 | "
    "Beer in bottles and cans - per wine gallon .16 | Wine, including sparkling "
    "wine, containing less than 17% alcohol by volume - per wine gallon .50 | "
    "Wine containing 17%-24% alcohol by volume - per wine gallon .60 | "
    "Distilled spirits - per wine gallon 2.50 | Alcohol - per wine gallon 4.05")
Q_ALC_WHOLESALE_ALLOC = (
    "The tax revenue collected from taxable transactions and activities within "
    "the exterior boundaries of the Fort Berthold Reservation, that portion of "
    "the Lake Traverse Reservation located in this state, the Spirit Lake "
    "Reservation, that portion of the Standing Rock Reservation located in this "
    "state, or the Turtle Mountain Reservation, pursuant to an agreement under "
    "this section must be allocated eighty percent to the tribe and twenty "
    "percent to the state.")
Q_ALC_FUND = (
    "The tax commissioner shall certify and transfer to the state treasurer for "
    "deposit in the tribal allocation fund, a special fund created in the state "
    "treasury, tax revenues allocated to a tribe or tribes under subsection 4 "
    "of section 57-39.10-03. Tax revenues collected under section 57-39.10-03 "
    "are provided as a standing and continuing appropriation to the state "
    "treasurer for distribution on a quarterly basis.")
Q_TOBACCO_PERCAPITA = (
    "The amount of tax revenue allocated to the tribe pursuant to an agreement "
    "under this section must be equal to an amount determined by multiplying "
    "the enrolled membership of the tribe by the state tobacco revenue per "
    "capita.")
Q_39_8_REPEALED = "Repealed by S.L. 2019, ch. 500"
Q_39_9_AUTHORITY = (
    "The governor, in consultation with the tax commissioner, may enter "
    "separate agreements on behalf of the state with the governing body of the "
    "Three Affiliated Tribes of the Fort Berthold Reservation, "
    "Sisseton-Wahpeton Oyate of the Lake Traverse Reservation, Spirit Lake "
    "Tribe, Standing Rock Sioux Tribe, and Turtle Mountain Band of Chippewa "
    "Indians")

URL_57_43_1 = f"{CENCODE}/t57c43-1.pdf"
URL_57_43_2 = f"{CENCODE}/t57c43-2.pdf"
URL_57_36 = f"{CENCODE}/t57c36.pdf"
URL_57_39_2 = f"{CENCODE}/t57c39-2.pdf"
URL_57_39_6 = f"{CENCODE}/t57c39-6.pdf"
URL_57_39_9 = f"{CENCODE}/t57c39-9.pdf"
URL_57_39_10 = f"{CENCODE}/t57c39-10.pdf"
URL_5_03 = f"{CENCODE}/t05c03.pdf"
URL_MEMO = ("https://ndlegis.gov/sites/default/files/resource/69-2025/"
            "committee-memorandum/27.9066.01000.pdf")
URL_HIST_FUEL = f"{TAXND}/motor-fuel-tax-history"
URL_STN = "https://apps.nd.gov/stn/inquiry/"


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
    def __init__(self):
        self.rows = []
        self.seq = 0

    def add(self, **kw):
        self.seq += 1
        kw.setdefault("state", STATE)
        kw.setdefault("tribe_id", "")
        kw.setdefault("tribe_name", "")
        for c in ("tax_remitted_usd", "statutory_rate", "rate_unit",
                  "derived_taxable_base", "base_unit", "rate_source_quote",
                  "amount_source_quote", "bound_basis", "period_start",
                  "period_end"):
            kw.setdefault(c, "")
        kw["tax_observation_id"] = f"{ID_PREFIX}{self.seq:04d}"
        kw["built_date"] = TODAY
        kw.setdefault("fetched_date", TODAY)
        kw.setdefault("tier", "A")

        assert kw["tax_type"] in TAX_TYPES, kw["tax_type"]
        assert kw["measurement_status"] in MEASUREMENT_STATUSES, \
            kw["measurement_status"]
        # Rule 4: tribal taxation is contested ground and a bare number invites
        # a wrong reading. The agreement or statute travels with every row.
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
            assert kw["rate_source_quote"] and kw["amount_source_quote"], \
                f"derived base without two quotes: {kw['tax_observation_id']}"
            assert kw["derived_taxable_base"] != "" and kw["base_unit"], \
                f"derived base incomplete: {kw['tax_observation_id']}"
            assert kw["tribe_id"], \
                f"derived base not keyed to a tribe: {kw['tax_observation_id']}"
        # Rule 1 in code: a rate_unit decides the base_unit and nothing else may.
        if kw["rate_unit"]:
            assert kw["rate_unit"] in RATE_UNIT_TO_BASE_UNIT, kw["rate_unit"]
            if kw["base_unit"]:
                assert kw["base_unit"] == RATE_UNIT_TO_BASE_UNIT[kw["rate_unit"]], (
                    f"{kw['rate_unit']} cannot yield {kw['base_unit']} "
                    f"({kw['tax_observation_id']})")
        # A unit with no rate beside it reads as a rate we hold and did not
        # print. The two `mixed_*` units are the exception: they ARE the reason
        # there is no rate, and saying so is the point of the row.
        if not kw["statutory_rate"] and not kw["rate_unit"].startswith("mixed"):
            kw["rate_unit"] = ""
        if kw["derived_taxable_base"] == "":
            kw["base_unit"] = ""
        assert_no_forecast_language(kw)
        self.rows.append({k: kw.get(k, "") for k in FIELDS})


# ==========================================================================
# STANDING TEXT
# ==========================================================================
NOT_A_TAX_BURDEN = (
    "This is money the STATE OF NORTH DAKOTA DISTRIBUTED TO the tribe under a "
    "state-tribal tax agreement. It is the tribe's share of tax collected from "
    "retailers, wholesalers and consumers inside the reservation - it is not a "
    "tax paid BY the tribe and must never be published as a tribal tax burden. "
    "It is also not a taxable base: recovering a base needs the agreement's "
    "sharing rate AND the statutory tax rate, two divisions.")

PAYMENT_DATE_NOTE = (
    "PERIOD IS THE PAYMENT DATE, NOT A TAX PERIOD. The State Treasurer "
    "publishes the date the distribution was made. North Dakota publishes no "
    "statement of which collection period each payment settles, so the period "
    "columns carry the payment date on both ends and the underlying sale month "
    "is earlier by an unpublished lag.")

FUEL_DERIVE = (
    "TWO DIVISIONS, BOTH ON QUOTED RATES. ${amt:,.2f} distributed / {share} "
    "(the tribe's share of collections under the agreement, {pct} percent less "
    "a 1 percent administration fee, North Dakota Legislative Council) = "
    "${tax:,.2f} of state motor vehicle fuel and special fuel tax collected "
    "within the reservation; / $0.23 per gallon (NDCC 57-43.1-02(1) and "
    "57-43.2-02(1)) = {gal:,.0f} GALLONS. IT IS A VOLUME AND NEVER A DOLLAR "
    "FIGURE. Treat it as a LOWER BOUND on gallons: NDCC 57-43.2-03(1) taxes "
    "propane at two percent of value and dyed diesel at four cents per gallon, "
    "and any such fuel pooled into the distribution generated fewer cents per "
    "gallon than 23; and NDCC 57-43.1-03.2(1) refunds fuel tax to individual "
    "enrolled members buying on their own reservation, which removes gallons "
    "from the pool. Both leaks push the true gallon count UP, never down.")

FUEL_NO_SHARE = (
    "NOT DIVIDED. The statutory rate is published ($0.23 per gallon, NDCC "
    "57-43.1-02(1) and 57-43.2-02(1)) but the tribe's SHARE of collections "
    "under the agreement in force on this payment date is not. The Legislative "
    "Council states the Standing Rock agreement became effective 1999-01-01 and "
    "gives an allocation only for the RENEGOTIATED agreement signed 2015-05-01. "
    "Carrying the 2015 percentage backwards would be an assumption, so no base "
    "is derived for any payment before 2015-05-01. One division of two is not a "
    "base.")

TOBACCO_BOUND = (
    "NOT INVERTIBLE. The agreement covers a CIGARETTE AND TOBACCO excise tax "
    "whose rates are 'identical to the state tax rates', and the state's rates "
    "are four different bases in one instrument: 22 mills per cigarette (five "
    "mills under NDCC 57-36-06(1) plus seventeen under 57-36-32, i.e. $0.44 per "
    "package of 20), 28 percent of the WHOLESALE PURCHASE PRICE on cigars and "
    "pipe tobacco (57-36-25(1)), 60 cents per OUNCE on snuff and 16 cents per "
    "ounce on chewing tobacco (57-36-25(2)). North Dakota publishes no split of "
    "the tribal distribution across them. {cond}")
TOBACCO_BOUND_COND = (
    "IF the Treasurer's 'Tribal Cigarette' line were cigarettes only, then "
    "${amt:,.2f} / 0.86 / $0.44 per pack = {packs:,.0f} packs of 20 - which is "
    "an UPPER BOUND on packs and not a value, because every dollar in the line "
    "that came from cigars, pipe tobacco, snuff or chewing tobacco inflates it.")
TOBACCO_BOUND_NOSHARE = (
    "No arithmetic is offered at all for this payment: the Legislative Council "
    "states the allocation only for the agreement renegotiated effective "
    "2015-05-01, and this payment precedes it.")

SALES_BOUND = (
    "NOT INVERTIBLE - FIVE RATES IN ONE DISTRIBUTION. The first division is "
    "sound: ${amt:,.2f} / 0.80 (the 80/20 tribal/state split of tax "
    "collections) = ${tax:,.2f} of tax collected within the reservation. The "
    "second is not. The agreement required the tribe to impose a 5 percent "
    "general sales and use tax, 3 percent on new manufactured homes, 7 percent "
    "alcohol gross receipts and 3 percent farm machinery gross receipts, plus a "
    ".25 percent tribal local tax on everything, and no split across them is "
    "published. Reading the 5 percent as if it were the whole schedule is the "
    "graduated-schedule-read-as-flat error. Taken as a range across the "
    "published rates, gross receipts lie between ${lo:,.0f} (all at 7 percent) "
    "and ${hi:,.0f} (all at 3 percent), which is a factor of 2.3 and is not a "
    "figure worth publishing as a base.")

ALCOHOL_BOUND = (
    "NOT INVERTIBLE - MIXED UNITS IN ONE FIGURE. The first division is sound: "
    "${amt:,.2f} / 0.80 (NDCC 57-39.10-03(4) and 57-39.10-05(5), the 80/20 "
    "split the 2023 session substituted for the earlier per-capita method) = "
    "${tax:,.2f} of tax collected within the reservation. The second is "
    "impossible. 'Tribal Alcohol' does not distinguish the alcoholic beverages "
    "WHOLESALE tax - a six-tier schedule from $.08 to $4.05 PER WINE GALLON "
    "under NDCC 5-03-07, so a volume base - from the alcoholic beverages GROSS "
    "RECEIPTS tax at seven percent ad valorem under NDCC 57-39.6-02, so a "
    "dollar base. NDCC 57-39.10-07 and 57-39.10-09 pay both out of the SAME "
    "tribal allocation fund on the same quarterly cycle, and 57-39.10-07(3) "
    "claws refunds back out of that fund, so a single payment can pool two "
    "units and be net of a third tax's refunds. Dividing it yields neither "
    "gallons nor dollars.")

ABSENCE_NOTE = (
    "MEASURED ABSENCE, NOT A BLANK. {tribe} is in the North Dakota State "
    "Treasurer's own tribe list, and its COMPLETE distribution listing - "
    "{n} payments totalling ${total:,.2f}, which foots to the application's own "
    "printed Grand Total - contains no {label} payment. The absence is "
    "therefore a property of the record, not of our coverage. It was NOT "
    "measured by a per-type query: the application validates its distribution-"
    "type parameter against an unpublished code list and answers an unknown "
    "code with 'Unable to Process', so a per-type sweep would manufacture false "
    "absences.")


# ==========================================================================
# BUILD
# ==========================================================================
def build():
    print("=== 116 build ===")
    problems, unresolved = [], []

    resolver = load_module("party_rulings", "33_apply_party_rulings.py")
    domain = load_module("cedar_domain", "cedar_domain.py")
    spine = read_spine()
    assert domain.Tier.A.value == "A"

    # ---- entity resolution ------------------------------------------------
    resolved = {}
    for name in STN_TRIBES.values():
        tid, canon, how = resolver.resolve_entity(name, spine)
        if tid is None and name in HAND_RULED_ALIASES:
            rule = HAND_RULED_ALIASES[name]
            # Guard 1: the Legislative Council's own full name must resolve.
            tid2, canon2, how2 = resolver.resolve_entity(rule["full_name"], spine)
            # Guard 2: uniqueness, not similarity. Exactly one ND federally
            # recognised tribe may carry the distinguishing words.
            cands = [r for r in spine
                     if r.get("state") == "ND"
                     and r.get("entity_class") == "Federally recognized tribe"
                     and rule["must_contain"] in
                     (r.get("canonical_name") or "").lower()]
            assert tid2 and len(cands) == 1 and cands[0]["tribe_id"] == tid2, (
                f"hand ruling for {name!r} does not hold against the raw spine "
                f"({tid2!r}, {len(cands)} candidates); refusing to key a dollar")
            tid, canon, how = tid2, canon2, f"hand_ruling_via[{how2}]"
            unresolved.append(dict(
                item=f"ND-TREASURER-ALIAS-RULED::{name}",
                kind="ALIAS_RULED_IN_SCRIPT_NOT_IN_SPINE",
                detail=(f"The ND Treasurer's label {name!r} does not resolve "
                        f"against the spine and was ruled to {tid} in "
                        f"{SCRIPT} on published evidence, not by matching. "
                        + rule["evidence"] +
                        " Two guards were applied and both hold: the "
                        "Legislative Council's full name resolves to the same "
                        "id through the shared resolver, and exactly one ND "
                        "federally recognised tribe carries the name. This "
                        "ruling now keys real money and belongs in the spine's "
                        "alias list rather than in a build script."),
                action=("add the alias to cedar_entity_spine.csv so no later "
                        "build has to re-rule it")))
        resolved[name] = (tid, canon, how)
        print(f"  resolve {name!r} -> {tid} ({how})")
        if tid is None:
            unresolved.append(dict(
                item=f"ND-TREASURER-TRIBE-UNRESOLVED::{name}",
                kind="ENTITY_NOT_RESOLVED",
                detail=(f"The ND Treasurer's label {name!r} does not resolve "
                        "against the spine and no hand ruling exists. Every "
                        "dollar for this tribe is REFUSED rather than keyed."),
                action="rule the alias into the spine; do not fuzzy-match it"))

    # ---- verify every quote against its retrieved file ---------------------
    S = RAW / "statute"
    T = RAW / "tax_commissioner"
    L = RAW / "legislative_council"
    checks = [
        (Q_MVF_RATE, S / "ndcc_t57c43-1_motor_vehicle_fuel_tax.pdf", "57-43.1-02(1)"),
        (Q_NA_FUEL_REFUND, S / "ndcc_t57c43-1_motor_vehicle_fuel_tax.pdf",
         "57-43.1-03.2(1)"),
        (Q_NA_FUEL_FUND, S / "ndcc_t57c43-1_motor_vehicle_fuel_tax.pdf",
         "57-43.1-03.2(2)"),
        (Q_SF_RATE, S / "ndcc_t57c43-2_special_fuels_tax.pdf", "57-43.2-02(1)"),
        (Q_SF_EXCISE, S / "ndcc_t57c43-2_special_fuels_tax.pdf", "57-43.2-03(1)"),
        (Q_CIG_RATE_06, S / "ndcc_t57c36_tobacco_products_tax.pdf", "57-36-06"),
        (Q_CIG_RATE_32, S / "ndcc_t57c36_tobacco_products_tax.pdf", "57-36-32"),
        (Q_OTP_RATE, S / "ndcc_t57c36_tobacco_products_tax.pdf", "57-36-25(1)"),
        (Q_OTP_WEIGHT, S / "ndcc_t57c36_tobacco_products_tax.pdf", "57-36-25(2)"),
        (Q_SALES_RATE, S / "ndcc_t57c39-2_sales_tax.pdf", "57-39.2-02.1(1)"),
        (Q_ALC_GR_RATE,
         S / "ndcc_t57c39-6_alcoholic_beverages_gross_receipts_tax.pdf",
         "57-39.6-02"),
        (Q_ALC_WHOLESALE_RATE,
         S / "ndcc_t05c03_beer_and_liquor_wholesalers_taxation.pdf", "5-03-07"),
        (Q_ALC_WHOLESALE_ALLOC,
         S / "ndcc_t57c39-10_state_tribal_alcohol_tobacco_agreements.pdf",
         "57-39.10-03(4)"),
        (Q_ALC_FUND,
         S / "ndcc_t57c39-10_state_tribal_alcohol_tobacco_agreements.pdf",
         "57-39.10-07(1)"),
        (Q_TOBACCO_PERCAPITA,
         S / "ndcc_t57c39-10_state_tribal_alcohol_tobacco_agreements.pdf",
         "57-39.10-04(4)"),
        (Q_39_8_REPEALED,
         S / "ndcc_t57c39-8_state_tribal_sales_tax_agreements_REPEALED.pdf",
         "57-39.8 repeal"),
        (Q_39_9_AUTHORITY,
         S / "ndcc_t57c39-9_state_tribal_sales_tax_agreements.pdf",
         "57-39.9-01"),
        (Q_MEMO_FUEL_HEAD,
         L / "tribal_state_relations_background_memo_27.9066.01000.pdf",
         "TSRC fuel"),
        (Q_MEMO_CIGARETTE,
         L / "tribal_state_relations_background_memo_27.9066.01000.pdf",
         "TSRC cigarette"),
        (Q_MEMO_SALES,
         L / "tribal_state_relations_background_memo_27.9066.01000.pdf",
         "TSRC sales"),
        (Q_MEMO_SALES_END,
         L / "tribal_state_relations_background_memo_27.9066.01000.pdf",
         "TSRC sales discontinued"),
        (Q_MEMO_ALCOHOL_2023,
         L / "tribal_state_relations_background_memo_27.9066.01000.pdf",
         "TSRC alcohol 2023"),
        (Q_MVF_HISTORY_2005, T / "motor_fuel_tax_history.html",
         "motor fuel history 2005"),
    ]
    for tribe, q in Q_MEMO_FUEL.items():
        checks.append(
            (q, L / "tribal_state_relations_background_memo_27.9066.01000.pdf",
             f"TSRC fuel {tribe}"))
    for q, p, lab in checks:
        if not p.exists():
            problems.append((lab, str(p), "MISSING FILE"))
            continue
        verify_quote(q, p, lab, problems)
    for lab, fn, frag in problems:
        print(f"  QUOTE NOT VERIFIED: {lab} in {fn} :: {frag!r}")

    # ---- read the Treasurer listings --------------------------------------
    listings = {}
    for s in stn_sources():
        p = RAW / s["path"]
        if not p.exists():
            unresolved.append(dict(
                item=f"STN listing not retrieved: {s['path']}",
                kind="SOURCE_MISSING", detail=str(p), action="re-run fetch"))
            continue
        rows, grand, state = parse_stn(p)
        listings[s["stn_tribe_id"]] = dict(
            tribe=s["stn_tribe"], rows=rows, grand=grand, state=state,
            url=s["url"], path=s["path"])
        print(f"  stn tribe={s['stn_tribe_id']:>1} {str(s['stn_tribe']):26} "
              f"{state:10} rows={len(rows):4} grand={grand}")

    # Boundary probes are evidence, never data.
    probe_states = {pid: listings[pid]["state"] for pid in STN_PROBE_IDS
                    if pid in listings}

    # FOOTING CHECK. A tribe whose listed rows do not sum to the application's
    # own printed Grand Total is REFUSED whole rather than published.
    usable, refused_tribes = {}, []
    for tid, name in STN_TRIBES.items():
        rec = listings.get(tid)
        if not rec or rec["state"] != "RESULTS":
            refused_tribes.append((name, "no RESULTS page"))
            continue
        s = sum(r[3] for r in rec["rows"])
        if rec["grand"] is None or abs(s - rec["grand"]) > 0.005:
            refused_tribes.append(
                (name, f"footing failed: rows {s:,.2f} vs printed "
                       f"{rec['grand']}"))
            unresolved.append(dict(
                item=f"ND-STN-FOOTING-FAILED::{name}", kind="TABLE_CHECK_FAILED",
                detail=f"rows sum to {s:,.2f}, printed Grand Total {rec['grand']}",
                action="re-fetch and re-read before publishing this tribe"))
            continue
        usable[tid] = rec
        print(f"    footing OK {name}: {len(rec['rows'])} rows = "
              f"${s:,.2f} = printed Grand Total")

    # ---- split the listings by distribution type --------------------------
    by_tribe_type = defaultdict(list)
    refused_rows = []
    for tid, rec in usable.items():
        for pdate, tname_pub, dtype, amt in rec["rows"]:
            if dtype in TYPE_OWNED_BY_113:
                continue
            if dtype in TYPE_REFUSED:
                refused_rows.append((rec["tribe"], dtype, pdate, amt))
                continue
            if dtype not in TYPE_TO_TAX_TYPE:
                refused_rows.append((rec["tribe"], dtype, pdate, amt))
                unresolved.append(dict(
                    item=f"ND-STN-UNKNOWN-DISTRIBUTION-TYPE::{dtype}",
                    kind="UNTYPED_DISTRIBUTION",
                    detail=(f"The Treasurer's listing for {rec['tribe']} carries "
                            f"distribution type {dtype!r}, which this build does "
                            "not map to a Cedar tax_type. Not published."),
                    action="identify the authorising instrument, then type it"))
                continue
            by_tribe_type[(rec["tribe"], dtype)].append((pdate, amt))

    for (tribe, dtype), rows in sorted(by_tribe_type.items()):
        print(f"    {tribe:26} {dtype:20} {len(rows):4} payments  "
              f"${sum(a for _d, a in rows):>16,.2f}  "
              f"{min(d for d, _a in rows)} .. {max(d for d, _a in rows)}")

    # County Sales Tax and anything else refused, measured but not published.
    if refused_rows:
        agg = defaultdict(lambda: [0, 0.0, "9999", "0000"])
        for tribe, dtype, pdate, amt in refused_rows:
            a = agg[(tribe, dtype)]
            a[0] += 1
            a[1] += amt
            a[2] = min(a[2], pdate)
            a[3] = max(a[3], pdate)
        for (tribe, dtype), (n, tot, d0, d1) in sorted(agg.items()):
            unresolved.append(dict(
                item=f"ND-DISTRIBUTION-NOT-PUBLISHED::{tribe}::{dtype}",
                kind="AUTHORITY_NOT_ESTABLISHED",
                detail=(f"The ND Treasurer's tribe listing shows {n} "
                        f"{dtype!r} payments to {tribe} totalling ${tot:,.2f}, "
                        f"{d0} to {d1}. NO instrument authorising a "
                        f"{dtype.lower()} distribution to a tribe was retrieved "
                        "from ndlegis.gov or tax.nd.gov. Rule 4 of "
                        "docs/TRIBAL_TAX_DECOMPOSITION.md forbids publishing a "
                        "tribal tax figure whose authority is unstated, so "
                        "these rows are MEASURED AND NOT PUBLISHED."),
                action=("find the county-tribe or state-tribe instrument; "
                        "the Standing Rock sales tax agreement's .25 percent "
                        "tribal local tax is the likeliest candidate and is "
                        "not the same thing as a county tax")))

    # ======================================================================
    # ROWS
    # ======================================================================
    R = Rows()

    # -- 1. statutory rate rows, not tribe-specific -------------------------
    NOT_TRIBE = "NOT TRIBE-SPECIFIC - STATUTORY RATE ROW"
    R.add(tax_type="MOTOR_FUEL", tribe_name=NOT_TRIBE,
          period_start="2006-01-01", period_end="",
          statutory_rate="0.23", rate_unit="usd_per_gallon",
          rate_source_quote=f"{Q_MVF_RATE} || {Q_SF_RATE} || {Q_MVF_HISTORY_2005}",
          agreement_or_statute_cite=(
              "NDCC 57-43.1-02(1) (motor vehicle fuel) and NDCC 57-43.2-02(1) "
              "(special fuel); rate history from the Office of State Tax "
              "Commissioner"),
          measurement_status=STATUS_RATE_ONLY, source_url=URL_57_43_1,
          confidence=(
              "Both chapters carry the SAME 23 cents per gallon, which is what "
              "lets one figure covering both be divided once. The Tax "
              "Commissioner's Motor Fuel Tax History records the 2005 session "
              "raising both from 21 cents and lists no later rate change "
              "through the 2025 session. The 2005 act sits in an appropriations "
              "volume not retrieved here, so period_start is set to 2006-01-01 "
              "- the first date on which 23 cents is unambiguously in force "
              "under both retrieved sources, and earlier than every payment "
              "this build divides. The 2005 act also carved E85 out at 1 cent "
              "per gallon until 1.2 million gallons had been sold; the current "
              "Century Code text of 57-43.1-02 carries no E85 subsection."))
    R.add(tax_type="MOTOR_FUEL", tribe_name=NOT_TRIBE,
          period_start="2007-08-01", period_end="",
          rate_unit="mixed_ad_valorem_and_per_unit",
          agreement_or_statute_cite="NDCC 57-43.2-03(1) (special excise tax)",
          measurement_status=STATUS_RATE_ONLY, source_url=URL_57_43_2,
          rate_source_quote="",
          bound_basis=(
              "RECORDED AS A HAZARD, NOT AS A RATE IN THE AGREEMENT. North "
              "Dakota levies a SECOND fuel tax with incompatible units - two "
              "percent of value on propane and four cents per gallon on dyed "
              "diesel and other special fuels exempt from the 23-cent tax: \""
              + Q_SF_EXCISE + "\" The Legislative Council states the tribal "
              "agreements apply \"at a rate of 23 cents per gallon\", so this "
              "tax is read as OUTSIDE them. If any of it is in fact pooled into "
              "a tribal distribution, the derived gallon counts on the MOTOR_"
              "FUEL rows are understated, which is why those rows are written "
              "as a lower bound."),
          confidence=("no rate is written in statutory_rate because two "
                      "incompatible rates are levied by the same subsection"))
    R.add(tax_type="TOBACCO", tribe_name=NOT_TRIBE,
          period_start="1993-07-01", period_end="",
          statutory_rate="0.022", rate_unit="usd_per_cigarette",
          rate_source_quote=f"{Q_CIG_RATE_06} || {Q_CIG_RATE_32}",
          agreement_or_statute_cite=(
              "NDCC 57-36-06(1) (five mills) and NDCC 57-36-32 (an additional "
              "seventeen mills), which together are 22 mills per cigarette"),
          measurement_status=STATUS_RATE_ONLY, source_url=URL_57_36,
          confidence=(
              "22 mills per cigarette is $0.44 per package of twenty. The rate "
              "is a SUM ACROSS TWO SECTIONS, like Washington's fuel rate, and "
              "it is also a two-class schedule: 57-36-06(2) charges five and "
              "one-half mills on cigarettes weighing more than three pounds per "
              "thousand, so Class B is 22.5 mills. Class A is written here."))
    R.add(tax_type="TOBACCO", tribe_name=NOT_TRIBE,
          period_start="2001-08-01", period_end="",
          rate_unit="mixed_ad_valorem_and_per_unit",
          rate_source_quote="",
          agreement_or_statute_cite="NDCC 57-36-25(1) and 57-36-25(2)",
          measurement_status=STATUS_RATE_ONLY, source_url=URL_57_36,
          bound_basis=(
              "THIS ROW IS THE REASON NO TOBACCO BASE IS DERIVED. The same "
              "chapter taxes cigars and pipe tobacco AD VALOREM and snuff and "
              "chewing tobacco BY WEIGHT: \"" + Q_OTP_RATE + "\" and \""
              + Q_OTP_WEIGHT + "\" A distribution under an agreement whose "
              "rates are 'identical to the state tax rates' can therefore pool "
              "a per-cigarette base, a dollar base and an ounce base in one "
              "figure."),
          confidence="no single rate exists for this row to carry")
    R.add(tax_type="RETAIL_SALES", tribe_name=NOT_TRIBE,
          period_start="2016-07-01", period_end="",
          statutory_rate="0.05", rate_unit="share_of_gross_receipts",
          rate_source_quote=Q_SALES_RATE,
          agreement_or_statute_cite="NDCC 57-39.2-02.1(1) (sales tax imposed)",
          measurement_status=STATUS_RATE_ONLY, source_url=URL_57_39_2,
          bound_basis=(
              "THE GENERAL RATE ONLY. The Standing Rock agreement required four "
              "state-level rates plus a tribal local rate, so this five percent "
              "is one row of a schedule and dividing a distribution by it would "
              "be the graduated-schedule-read-as-flat error."),
          confidence=("the tribal taxes under the agreement were 'identical to "
                      "North Dakota's sales, use, and gross receipts taxes'"))
    R.add(tax_type="ALCOHOL", tribe_name=NOT_TRIBE,
          period_start="2016-07-01", period_end="",
          statutory_rate="0.07", rate_unit="share_of_gross_receipts",
          rate_source_quote=Q_ALC_GR_RATE,
          agreement_or_statute_cite=(
              "NDCC 57-39.6-02 (gross receipts tax on alcoholic beverages)"),
          measurement_status=STATUS_RATE_ONLY, source_url=URL_57_39_6,
          confidence=("an AD VALOREM alcohol tax, so its base would be dollars. "
                      "It is one of the two taxes the Treasurer's 'Tribal "
                      "Alcohol' line can contain; the other is per gallon."))
    R.add(tax_type="ALCOHOL", tribe_name=NOT_TRIBE,
          period_start="2009-08-01", period_end="",
          rate_unit="mixed_per_unit_schedule_by_product_class",
          rate_source_quote="",
          agreement_or_statute_cite="NDCC 5-03-07 (imposition of tax - rate)",
          measurement_status=STATUS_RATE_ONLY, source_url=URL_5_03,
          bound_basis=(
              "THIS ROW IS THE REASON NO ALCOHOL BASE IS DERIVED. The wholesale "
              "tax is a six-tier per-gallon schedule spanning a factor of 50: \""
              + Q_ALC_WHOLESALE_RATE + "\" No single division of a pooled "
              "figure yields a gallon count, and the pooled figure may also "
              "contain the seven percent ad valorem gross receipts tax."),
          confidence=("period_start is the 2009 session's reduction of the "
                      "sparkling wine rate, the last change to this schedule "
                      "recorded in the Tax Commissioner's Alcohol Tax History"))

    # -- 2. one agreement roster row per (tribe, tax) -----------------------
    for tribe, share in MEMO_FUEL_SHARE.items():
        tid, canon, _how = resolved[tribe]
        if tid is None:
            continue
        pct = round(share * 100) + 1
        # Where the agreement predates the allocation the source states, the
        # earlier period gets its OWN roster row with NO rate. Stretching the
        # stated percentage back over a period the source does not cover would
        # put an unsourced number in a rate column, whatever the prose said.
        if MEMO_FUEL_AGREEMENT_FROM[tribe] < MEMO_FUEL_SHARE_FROM[tribe]:
            R.add(tax_type="MOTOR_FUEL", tribe_id=tid, tribe_name=canon,
                  period_start=MEMO_FUEL_AGREEMENT_FROM[tribe],
                  period_end=prev_day(MEMO_FUEL_SHARE_FROM[tribe]),
                  rate_source_quote="",
                  agreement_or_statute_cite=(
                      "State-tribal motor vehicle fuel and special fuel tax "
                      "agreement effective "
                      f"{MEMO_FUEL_AGREEMENT_FROM[tribe]}, described by the "
                      "North Dakota Legislative Council"),
                  measurement_status=STATUS_AGREEMENT_ROSTER,
                  source_url=URL_MEMO,
                  bound_basis=(
                      "AGREEMENT IN FORCE, ALLOCATION NOT PUBLISHED. The "
                      "Legislative Council states this agreement's effective "
                      f"date ({MEMO_FUEL_AGREEMENT_FROM[tribe]}) and gives an "
                      "allocation only for the agreement renegotiated "
                      f"{MEMO_FUEL_SHARE_FROM[tribe]}. The rate columns are "
                      "left BLANK for this period rather than carrying the "
                      "later percentage backwards, and no payment inside it is "
                      "divided."),
                  confidence=("the roster row proves the agreement existed; it "
                              "subtracts nothing and derives nothing"))
        R.add(tax_type="MOTOR_FUEL", tribe_id=tid, tribe_name=canon,
              period_start=MEMO_FUEL_SHARE_FROM[tribe], period_end="",
              statutory_rate=f"{share:.2f}",
              rate_unit="share_of_state_tax_collected",
              rate_source_quote=f"{Q_MEMO_FUEL_HEAD} || {Q_MEMO_FUEL[tribe]}",
              agreement_or_statute_cite=(
                  "State-tribal motor vehicle fuel and special fuel tax "
                  "agreement, described by the North Dakota Legislative "
                  "Council; NDCC 57-43.1-03.2(2) creates the fuels tax refund "
                  "reserve fund the distribution is paid from"),
              measurement_status=STATUS_AGREEMENT_ROSTER, source_url=URL_MEMO,
              bound_basis=(
                  f"THE SHARE IS {share:.2f}, NOT {pct / 100:.2f}. The source "
                  f"says {pct} percent 'less a 1 percent administration fee' to "
                  f"the tribe and {100 - pct} percent 'plus the 1 percent "
                  "administration fee' to the general fund. Those two legs sum "
                  "to exactly 100 percent only if the fee is one percentage "
                  "POINT off the tribe's share, never a one percent haircut of "
                  "it. The source's own second sentence forces the reading."
                  + ("" if tribe != "Standing Rock Sioux Tribe" else
                     " This allocation belongs to the agreement RENEGOTIATED "
                     "2015-05-01. The allocation under the agreement effective "
                     "1999-01-01 is not published, so no Standing Rock fuel "
                     "payment before 2015-05-01 is divided.")),
              confidence=(
                  "the agreement text itself is not published; the North Dakota "
                  "Legislative Council's Tribal and State Relations Committee "
                  "background memorandum is the citable statement of its terms. "
                  f"Allocation in force from {MEMO_FUEL_SHARE_FROM[tribe]}."))
    sr_id, sr_name, _ = resolved["Standing Rock Sioux Tribe"]
    mha_id, mha_name, _ = resolved["Three Affiliated Tribes"]
    assert sr_id == "TRBF-STNDRK-00" and mha_id == "TRBF-MHATAT-00", \
        "Standing Rock or Three Affiliated does not key where this build expects"

    R.add(tax_type="TOBACCO", tribe_id=sr_id, tribe_name=sr_name,
          period_start="1993-07-01", period_end="2015-04-30",
          rate_source_quote="",
          agreement_or_statute_cite=(
              "Collection agreement between the North Dakota Tax Commissioner "
              "and the Standing Rock Sioux Tribe effective 1993-07-01"),
          measurement_status=STATUS_AGREEMENT_ROSTER, source_url=URL_MEMO,
          bound_basis=(
              "AGREEMENT IN FORCE, ALLOCATION NOT PUBLISHED. The Legislative "
              "Council states this agreement became effective 1993-07-01 and "
              "gives an allocation only for the terms that 'became effective on "
              "May 1, 2015'. The rate columns are left BLANK for the first "
              "twenty-two years rather than carrying the 2015 percentage "
              "backwards."),
          confidence=("the oldest state-tribal tax agreement in this dataset; "
                      "the Treasurer's data begins 2005-01-14, which is the "
                      "application's floor and not the agreement's"))
    R.add(tax_type="TOBACCO", tribe_id=sr_id, tribe_name=sr_name,
          period_start="2015-05-01", period_end="",
          statutory_rate="0.86", rate_unit="share_of_state_tax_collected",
          rate_source_quote=Q_MEMO_CIGARETTE,
          agreement_or_statute_cite=(
              "Collection agreement between the North Dakota Tax Commissioner "
              "and the Standing Rock Sioux Tribe effective 1993-07-01, "
              "renegotiated effective 2015-05-01; the tribe levies the tax and "
              "the Tax Department collects it as the tribe's agent"),
          measurement_status=STATUS_AGREEMENT_ROSTER, source_url=URL_MEMO,
          bound_basis=(
              "THE TAX IS THE TRIBE'S OWN, NOT THE STATE'S. Under this "
              "agreement the Standing Rock Sioux Tribe levies a cigarette and "
              "tobacco excise tax at rates identical to the state's and North "
              "Dakota collects it as agent, returning 87 percent less a 1 "
              "percent administrative fee. That makes the distribution a "
              "remittance of the TRIBE's tax revenue and makes the 13 percent "
              "retained by the state the price of collection. The stated "
              "allocation belongs to the agreement renegotiated effective "
              "2015-05-01."),
          confidence=("the oldest state-tribal tax agreement in this dataset, "
                      "in force since 1993 and the only tribal tobacco money "
                      "any state has been found to publish per tribe"))
    R.add(tax_type="RETAIL_SALES", tribe_id=sr_id, tribe_name=sr_name,
          period_start="2016-07-01", period_end="2019-03-14",
          statutory_rate="0.80", rate_unit="share_of_state_tax_collected",
          rate_source_quote=Q_MEMO_SALES,
          agreement_or_statute_cite=(
              "State-tribal sales, use, and gross receipts tax agreement "
              "authorised by 2015 HB 1406 and NDCC ch. 57-39.8, effective "
              "2016-07-01; ch. 57-39.8 was repealed by 2019 SB 2257 and SB "
              "2258 and replaced by ch. 57-39.9"),
          measurement_status=STATUS_AGREEMENT_ROSTER, source_url=URL_MEMO,
          bound_basis=(
              "THE SERIES ENDS FOR A REASON THE SOURCE STATES. \""
              + Q_MEMO_SALES_END + "\" State administration stopped 2017-03-07 "
              "and the Standing Rock Sioux Tribe Tax Department took the taxes "
              "over, yet distributions continue to 2019-03-14 - which is a "
              "receipt series outliving the obligation series that generated "
              "it. period_end is the last observed payment, not the end of the "
              "agreement. The authorising chapter was then repealed outright."),
          confidence=("the successor chapter 57-39.9 authorises agreements with "
                      "five named tribes and no distribution has appeared under "
                      "it in the Treasurer's data through 2026-07"))
    R.add(tax_type="ALCOHOL", tribe_id=mha_id, tribe_name=mha_name,
          period_start="2025-01-15", period_end="",
          statutory_rate="0.80", rate_unit="share_of_state_tax_collected",
          rate_source_quote=f"{Q_ALC_WHOLESALE_ALLOC} || {Q_MEMO_ALCOHOL_2023}",
          agreement_or_statute_cite=(
              "State-tribal agreement under NDCC ch. 57-39.10; allocation set "
              "by NDCC 57-39.10-03(4) (alcoholic beverages wholesale tax) and "
              "57-39.10-05(5) (alcoholic beverages gross receipts tax), both "
              "amended to 80/20 by the 2023 session"),
          measurement_status=STATUS_AGREEMENT_ROSTER, source_url=URL_57_39_10,
          bound_basis=(
              "THE ALLOCATION METHOD CHANGED, AND THE SERIES STARTS AFTER IT. "
              "From 2019 to 2023 chapter 57-39.10 allocated alcohol revenue by "
              "PER-CAPITA FORMULA - enrolled membership times state revenue per "
              "capita - which is not a share of anything and cannot be "
              "inverted at all. The 2023 session replaced it with a flat 80/20. "
              "The first distribution in the Treasurer's data is 2025-01-15, so "
              "every observed payment falls under the 80/20 method. The "
              "companion tobacco products wholesale allocation in "
              "57-39.10-04(4) is STILL per-capita: \"" + Q_TOBACCO_PERCAPITA
              + "\""),
          confidence=("period_start is the first observed distribution; the "
                      "agreement's own effective date is not published"))

    # -- 3. payment rows ----------------------------------------------------
    derived_count = Counter()
    for (tribe, dtype), payments in sorted(by_tribe_type.items()):
        tax_type = TYPE_TO_TAX_TYPE[dtype]
        tid, canon, _how = resolved[tribe]
        if tid is None:
            continue
        for pdate, amt in sorted(payments):
            # The application prints MM/DD/YYYY. A verbatim quote reproduces
            # the source's own typography, never an ISO reformatting of it.
            quote = (f"Payment Date {pdate[5:7]}/{pdate[8:10]}/{pdate[0:4]} | "
                     f"Tribe Name {tribe} | Tax Type {dtype} | Amount "
                     f"{amt:,.2f}")
            common = dict(
                tax_type=tax_type, tribe_id=tid, tribe_name=canon,
                period_start=pdate, period_end=pdate,
                tax_remitted_usd=f"{amt:.2f}", amount_source_quote=quote,
                source_url=URL_STN)
            if tax_type == "MOTOR_FUEL":
                share = MEMO_FUEL_SHARE[tribe]
                if pdate >= MEMO_FUEL_SHARE_FROM[tribe]:
                    tax = amt / share
                    gal = tax / 0.23
                    R.add(**common,
                          statutory_rate="0.23", rate_unit="usd_per_gallon",
                          derived_taxable_base=f"{gal:.0f}", base_unit="gallons",
                          rate_source_quote=(f"{Q_MVF_RATE} || {Q_SF_RATE} || "
                                             f"{Q_MEMO_FUEL[tribe]}"),
                          agreement_or_statute_cite=(
                              "State-tribal motor vehicle fuel and special fuel "
                              "tax agreement (allocation stated by the North "
                              "Dakota Legislative Council); NDCC 57-43.1-02(1) "
                              "and 57-43.2-02(1) (rate); NDCC 57-43.1-03.2(2) "
                              "(fuels tax refund reserve fund)"),
                          measurement_status=STATUS_DERIVED_BASE,
                          bound_basis=FUEL_DERIVE.format(
                              amt=amt, share=f"{share:.2f}",
                              pct=round(share * 100) + 1, tax=tax, gal=gal),
                          confidence=NOT_A_TAX_BURDEN + " " + PAYMENT_DATE_NOTE)
                    derived_count[(tribe, tax_type)] += 1
                else:
                    R.add(**common,
                          agreement_or_statute_cite=(
                              "State-tribal motor vehicle fuel and special fuel "
                              "tax agreement effective 1999-01-01 (North Dakota "
                              "Legislative Council); NDCC 57-43.1-02(1) and "
                              "57-43.2-02(1) (rate)"),
                          measurement_status=STATUS_PER_TRIBE_AMOUNT,
                          bound_basis=FUEL_NO_SHARE,
                          confidence=NOT_A_TAX_BURDEN + " " + PAYMENT_DATE_NOTE)
            elif tax_type == "TOBACCO":
                if pdate >= "2015-05-01":
                    packs = amt / 0.86 / 0.44
                    cond = TOBACCO_BOUND_COND.format(amt=amt, packs=packs)
                else:
                    cond = TOBACCO_BOUND_NOSHARE
                R.add(**common,
                      agreement_or_statute_cite=(
                          "Collection agreement between the North Dakota Tax "
                          "Commissioner and the Standing Rock Sioux Tribe "
                          "effective 1993-07-01, renegotiated effective "
                          "2015-05-01; NDCC 57-36-06, 57-36-25 and 57-36-32 "
                          "(the state rates the tribal rates are identical to)"),
                      measurement_status=STATUS_PER_TRIBE_AMOUNT,
                      bound_basis=TOBACCO_BOUND.format(cond=cond),
                      confidence=NOT_A_TAX_BURDEN + " " + PAYMENT_DATE_NOTE)
            elif tax_type == "RETAIL_SALES":
                tax = amt / 0.80
                R.add(**common,
                      agreement_or_statute_cite=(
                          "State-tribal sales, use, and gross receipts tax "
                          "agreement authorised by 2015 HB 1406 and NDCC ch. "
                          "57-39.8 (repealed 2019), effective 2016-07-01; NDCC "
                          "57-39.2-02.1 and 57-39.6-02 (the state rates the "
                          "tribal rates are identical to)"),
                      measurement_status=STATUS_PER_TRIBE_AMOUNT,
                      bound_basis=SALES_BOUND.format(
                          amt=amt, tax=tax, lo=tax / 0.07, hi=tax / 0.03),
                      confidence=NOT_A_TAX_BURDEN + " " + PAYMENT_DATE_NOTE)
            elif tax_type == "ALCOHOL":
                tax = amt / 0.80
                R.add(**common,
                      agreement_or_statute_cite=(
                          "State-tribal agreement under NDCC ch. 57-39.10; "
                          "NDCC 57-39.10-03(4) and 57-39.10-05(5) (80/20 "
                          "allocation); NDCC 5-03-07 and 57-39.6-02 (rates)"),
                      measurement_status=STATUS_PER_TRIBE_AMOUNT,
                      bound_basis=ALCOHOL_BOUND.format(amt=amt, tax=tax),
                      confidence=NOT_A_TAX_BURDEN + " " + PAYMENT_DATE_NOTE)

    # -- 4. measured absences ------------------------------------------------
    label_of = {v: k for k, v in TYPE_TO_TAX_TYPE.items()}
    absences = []
    for tid, rec in sorted(usable.items()):
        tribe = rec["tribe"]
        etid, canon, _how = resolved[tribe]
        if etid is None:
            continue
        n_all = len(rec["rows"])
        for tax_type, label in sorted(label_of.items()):
            if (tribe, label) in by_tribe_type:
                continue
            absences.append((tribe, tax_type, label))
            R.add(tax_type=tax_type, tribe_id=etid, tribe_name=canon,
                  period_start="1990-01-01", period_end="2026-12-31",
                  tax_remitted_usd="0.00",
                  amount_source_quote=(
                      f"Tax Distribution Search Results | Payment Date "
                      f"1990-01-01 - 2026-12-31 | Tribe: {tribe} | "
                      f"Grand Total: ${rec['grand']:,.2f} across {n_all} "
                      f"payments, none of them of type {label!r}"),
                  agreement_or_statute_cite=(
                      "NDCC 57-39.9-01 and 57-39.10-01 authorise state-tribal "
                      "sales, alcohol and tobacco tax agreements with five "
                      "named tribes; the North Dakota Legislative Council "
                      "describes every agreement actually in force"),
                  measurement_status=STATUS_MEASURED_ABSENCE,
                  bound_basis=ABSENCE_NOTE.format(
                      tribe=tribe, n=n_all, total=rec["grand"], label=label),
                  source_url=rec["url"],
                  confidence=(
                      "$0.00 here is a measured zero over the application's own "
                      "full date range, not a missing value. It must never be "
                      "read as a tribe paying no such tax: it means North "
                      "Dakota distributes nothing to this tribe under an "
                      "agreement of this kind, which usually means no such "
                      "agreement exists."))

    new_rows = R.rows
    print(f"  built {len(new_rows)} rows "
          f"({Counter(r['tax_type'] for r in new_rows)})")

    # ======================================================================
    # REVIEW QUEUE
    # ======================================================================
    unresolved += [
        dict(item="ND-TRIBAL-TAX-AGREEMENT-TEXTS-NOT-PUBLISHED",
             kind="SOURCE_WITHHELD_OR_UNPUBLISHED",
             detail=("Not one of the state-tribal fuel, cigarette, sales or "
                     "alcohol agreement TEXTS was found on ndlegis.gov or "
                     "tax.nd.gov. Every allocation percentage in this build "
                     "comes from the Legislative Council's description of the "
                     "agreements, not from the instruments. The same blocker "
                     "was recorded for the oil and gas agreements by script "
                     "113, so it is now four tax types deep and is the single "
                     "highest-value document request in the North Dakota work."),
             action=("request the agreements from the Governor's office or the "
                     "Tax Commissioner; the fuel agreements would also settle "
                     "whether the 57-43.2-03 special excise tax is inside them")),
        dict(item="ND-STANDING-ROCK-FUEL-ALLOCATION-1999-2015-UNKNOWN",
             kind="RATE_NOT_UNIQUELY_DETERMINED",
             detail=("The Standing Rock motor fuel agreement became effective "
                     "1999-01-01 and the Legislative Council states an "
                     "allocation only for the agreement RENEGOTIATED "
                     "2015-05-01. Every Standing Rock fuel payment before "
                     "2015-05-01 therefore carries an amount and a per-gallon "
                     "rate but no sharing rate, and no base is derived from it. "
                     "The same gap applies to the 1993 cigarette agreement "
                     "before its 2015-05-01 renegotiation."),
             action=("find the pre-2015 agreements or a Tax Commissioner "
                     "statement of the earlier allocation; each recovered "
                     "percentage converts reported payments into derived "
                     "gallons")),
        dict(item="ND-TRIBAL-ALCOHOL-WHICH-TAX-UNKNOWN",
             kind="MIXED_UNITS_IN_ONE_FIGURE",
             detail=("The Treasurer's 'Tribal Alcohol' line does not say "
                     "whether it is the alcoholic beverages WHOLESALE tax "
                     "(NDCC 5-03-07, six per-gallon tiers), the alcoholic "
                     "beverages GROSS RECEIPTS tax (NDCC 57-39.6-02, seven "
                     "percent ad valorem), or both. NDCC 57-39.10-07 and -09 "
                     "pay both from the same tribal allocation fund on the same "
                     "quarterly cycle. If the Tax Commissioner confirms the "
                     "line is gross receipts only, the base follows in one more "
                     "division: payment / 0.80 / 0.07 = dollars of alcoholic "
                     "beverage retail sales inside the reservation."),
             action=("ask the Tax Commissioner which taxes the Three Affiliated "
                     "Tribes agreement covers; this is the cheapest available "
                     "route to a second derived base")),
        dict(item="ND-TRIBAL-CIGARETTE-LINE-SCOPE-UNKNOWN",
             kind="MIXED_UNITS_IN_ONE_FIGURE",
             detail=("The agreement is a 'cigarette and tobacco excise tax' "
                     "agreement but the Treasurer's label is 'Tribal "
                     "Cigarette'. If the line is cigarettes only, packs = "
                     "payment / 0.86 / $0.44 and the arithmetic is already "
                     "written onto every post-2015-05-01 row as an UPPER bound. "
                     "If it pools cigars, pipe tobacco, snuff and chewing "
                     "tobacco, no volume comes out of it at all."),
             action=("ask whether the distribution line separates cigarettes "
                     "from other tobacco products")),
        dict(item="ND-57-39.9-AUTHORISED-BUT-NO-DISTRIBUTION",
             kind="MEASURED_ABSENCE",
             detail=("NDCC 57-39.9-01, enacted 2019, authorises state-tribal "
                     "sales, use and gross receipts tax agreements with FIVE "
                     "named tribes including Sisseton-Wahpeton Oyate. The "
                     "Treasurer's complete listings for all four tribes in its "
                     "own tribe list show NO sales tax distribution after "
                     "2019-03-14. The authority exists and nothing has flowed "
                     "under it, at least to these four tribes."),
             action=("re-probe annually; a first distribution under 57-39.9 is "
                     "a publishable event")),
        dict(item="ND-TREASURER-TRIBE-LIST-EXCLUDES-SISSETON-WAHPETON",
             kind="SOURCE_COVERAGE_GAP",
             detail=("NDCC 57-39.9-01 and 57-39.10-01 each name FIVE tribes - "
                     "Three Affiliated, Sisseton-Wahpeton Oyate of the Lake "
                     "Traverse Reservation, Spirit Lake, Standing Rock and "
                     "Turtle Mountain. The Treasurer's tribe list holds FOUR. "
                     f"Tribe ids 5 and 6 were probed and the application "
                     f"answered {probe_states} - 'Unable to Process' is an "
                     "application error, not an empty result, so the list is "
                     "closed at four rather than merely returning nothing for "
                     "a fifth. Sisseton-Wahpeton's ND-side reservation area is "
                     "therefore unrepresented in this series."),
             action=("check whether Sisseton-Wahpeton distributions appear "
                     "under a county or city search rather than the tribe "
                     "search")),
        dict(item="ND-STN-DISTTYPE-CODE-LIST-NOT-PUBLISHED",
             kind="SOURCE_STRUCTURALLY_SILENT",
             detail=("The Treasurer application's DistType parameter is "
                     "validated against an internal code list that is not "
                     "exposed anywhere in the public interface - the search "
                     "page serves only a county selector. Probed 2026-08-07 "
                     "with 'TRIBAL HWY', 'TRIBAL HIGHWAY', 'TRIBAL CIG', "
                     "'TRIBAL CIGARETTE', 'TRIBAL SALES', 'TRIBAL ALCOHOL' and "
                     "'COUNTY SALES': every one returned 'Unable to Process'. "
                     "A per-type absence sweep would therefore have produced "
                     "false absences that looked exactly like real ones."),
             action=("none needed - the all-types listing is complete and foots "
                     "to the application's own Grand Total. Recorded so nobody "
                     "reruns the failed approach")),
        dict(item="ND-113-BUILD-LOG-PRINTS-ZERO-FOR-1.5BN",
             kind="DOWNSTREAM_DEFECT_IN_ANOTHER_BUILD",
             detail=("`parse_stn` in code/113_build_nd_severance.py scans for "
                     "the trailing 'Grand Total:' line inside a loop bounded by "
                     "`i < len(L) - 3`, so it never reaches it and always "
                     "returns grand=None. docs/ND_SEVERANCE_BUILD_LOG.md "
                     "consequently prints 'Three Affiliated Tribes | 215 "
                     "payments, $0.00' for a series worth $1,587,965,950.39, "
                     "and $0.00 for the extraction and straddle rows too. The "
                     "CSV rows are unaffected - only the log's table is wrong. "
                     "This build's parser scans the whole line list and uses "
                     "the Grand Total as a footing check."),
             action=("owner of script 113 should widen the loop bound and "
                     "regenerate the log; do not hand-edit the number")),
        dict(item="TRIBAL-TAX-BUILD-LOG-NETTING-SECTION-NOW-FALSE",
             kind="DOWNSTREAM_UPDATE_OWED",
             detail=("`docs/TRIBAL_TAX_BUILD_LOG.md` (script 108) carries a "
                     "section headed 'Netting readiness: zero tribes, and that "
                     "is the honest number' whose second sentence reads 'No "
                     "tribe in this dataset yet carries a per-tribe non-gaming "
                     "tax amount'. That is now false: four North Dakota tribes "
                     "do. Its 'Next targets' list also still ranks North Dakota "
                     "first with SEVERANCE described as an empty tax type, "
                     "which scripts 113 and 116 have both closed. The zero "
                     "COUNT of nettable tribes happens to remain correct, but "
                     "for a completely different reason - North Dakota seals "
                     "tribal gaming records - so the sentence would mislead "
                     "even where it lands on the right number."),
             action=("script 108 owns that log and regenerates it; the "
                     "sentences must be changed there, not hand-edited. "
                     "docs/TRIBAL_TAX_DECOMPOSITION.md already carries the "
                     "correction in its CORRECTION AND EXTENSION section")),
        dict(item="ND-NETTING-BLOCKED-BY-SEALED-GAMING-RECORDS",
             kind="OTHER_SIDE_OF_THE_SUBTRACTION_MISSING",
             detail=("Four North Dakota tribes now carry per-tribe non-gaming "
                     "tax money, which is the input the netting method in "
                     "docs/TRIBAL_TAX_DECOMPOSITION.md was waiting for. It "
                     "still cannot run for a single ND tribe, and the blocker "
                     "has MOVED to the other operand: North Dakota holds and "
                     "seals every tribal gaming record under NDCC 54-58-02, "
                     "recorded in data/clean/state_gaming_observations.csv as "
                     "SG-ND-00001 with exclusion_flag "
                     "'held_by_state_but_sealed'. There is no whole-tribe or "
                     "gaming revenue figure for any ND tribe anywhere in this "
                     "dataset to subtract from, and gaming_revenue_bounds.csv "
                     "holds zero ND rows."),
             action=("the minuend must come from a tribal source - an audited "
                     "financial statement, a bond official statement or a "
                     "tribal annual report - not from North Dakota")),
    ]

    # ======================================================================
    # WRITE
    # ======================================================================
    write_tax_bases(new_rows)
    ufields = ["item", "kind", "detail", "action"]
    write_csv(REVIEW / f"nd_tribal_tax_unresolved_{TODAY}.csv",
              [{k: u.get(k, "") for k in ufields} for u in unresolved], ufields)
    print(f"  review/nd_tribal_tax_unresolved_{TODAY}.csv: "
          f"{len(unresolved)} rows")
    write_codebook_fragment()
    write_log(new_rows, by_tribe_type, usable, listings, refused_tribes,
              refused_rows, absences, derived_count, resolved, probe_states,
              unresolved, problems)
    return new_rows


# ==========================================================================
# IO
# ==========================================================================
def read_csv(p):
    if not Path(p).exists():
        return []
    with Path(p).open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


# --- REGENERATE GUARD (ADR-017, 2026-09-02) --------------------------------
def _carry_live_columns(path, canonical):
    """Derive this writer's header instead of declaring it.

    A wholesale writer holding a FIXED `fieldnames` list deletes every column
    an in-place enricher added since - no error, no exception, a diff nobody
    reads. Canonical order first so column order stays stable, then whatever
    the live file already carries. A retired column stays retired because it
    is not on disk; a promoted column survives because it is.

    THIS BUILD CANNOT REPOPULATE AN ENRICHER'S COLUMN. Carried columns are
    written BLANK and NAMED on stdout, which is strictly better than deleted:
    the schema survives and the enricher can refill them. Re-run the enricher
    after this build - `cedar_pipeline.enrichers_to_rerun(<table>)` names it.
    """
    import csv as _csv
    import os as _os
    canonical = list(canonical)
    _p = str(path)
    if not _os.path.exists(_p):
        return canonical
    with open(_p, encoding="utf-8-sig", newline="", errors="replace") as _fh:
        _live = next(_csv.reader(_fh), [])
    _extra = [c for c in _live if c and c not in canonical]
    if _extra:
        print("  [regenerate guard] %s: carrying %d enricher column(s) through "
              "this rebuild, BLANK - re-run the enricher: %s"
              % (_os.path.basename(_p), len(_extra), ", ".join(_extra)))
    return canonical + _extra


def write_csv(p, rows, fields):
    # REGENERATE GUARD (ADR-017, 2026-09-02): derive the header, do not declare it.
    fields = _carry_live_columns(p, fields)
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(p).with_suffix(Path(p).suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    tmp.replace(p)


def write_tax_bases(new_rows):
    """APPEND ONLY, and idempotent, exactly as script 113 is.

    This script is the sole author of ND rows whose tax_type is one of the four
    non-severance types. Replacing exactly that slice makes a re-run replace
    rather than duplicate, and carries everything any other agent wrote through
    untouched. The predicate is deliberately narrow: ND SEVERANCE rows belong to
    script 113 and are never in the slice.
    """
    p = CLEAN / "tribal_tax_bases.csv"
    bak = CLEAN / f"tribal_tax_bases.csv.bak_{TODAY}_pre116"
    if p.exists() and not bak.exists():
        shutil.copy2(p, bak)
    cur = read_csv(p)                      # re-read, late, on purpose
    ours = [r for r in cur
            if r.get("state") == "ND" and r.get("tax_type") in TAX_TYPES]
    keep = [r for r in cur if r not in ours]
    n_sev = sum(1 for r in keep if r.get("state") == "ND"
                and r.get("tax_type") == "SEVERANCE")
    out = keep + new_rows
    write_csv(p, out, FIELDS)
    print(f"  tribal_tax_bases.csv: {len(cur)} before -> {len(out)} after "
          f"({len(ours)} prior ND non-severance rows replaced, {len(keep)} "
          f"kept of which {n_sev} are script 113's ND severance rows)")


CODEBOOK_VARS = [
    ("measurement_status:MEASURED_ABSENCE_NO_DISTRIBUTION",
     "The tribe is in the publishing agency's own list and its COMPLETE "
     "distribution listing - which foots to the agency's printed grand total - "
     "contains no payment of this tax type. tax_remitted_usd is a measured "
     "0.00, not a blank, and must never be read as a tribe paying no such tax: "
     "it means the state distributes nothing to that tribe under an agreement "
     "of this kind."),
    ("rate_unit:usd_per_gallon",
     "A per-gallon excise rate. The base it yields is a VOLUME in gallons and "
     "is never a dollar figure."),
    ("rate_unit:usd_per_cigarette",
     "A per-cigarette excise rate. The base it yields is a count of cigarettes; "
     "twenty cigarettes is one package."),
    ("rate_unit:usd_per_ounce",
     "A per-ounce excise rate on tobacco sold by weight. Its base is ounces."),
    ("rate_unit:share_of_gross_receipts",
     "An ad valorem rate on retail gross receipts. The base it yields is USD."),
    ("rate_unit:share_of_wholesale_purchase_price",
     "An ad valorem rate on the wholesale purchase price. Its base is USD and "
     "is a WHOLESALE figure, never a retail one."),
    ("rate_unit:mixed_per_unit_schedule_by_product_class",
     "The rate is a schedule of different per-unit rates by product class - "
     "North Dakota's alcohol wholesale tax runs $.08 to $4.05 per wine gallon "
     "across six classes. One published figure covering the schedule has no "
     "single base. Written without a statutory_rate, because it is the reason "
     "there is no rate."),
    ("statutory_rate:two_rates_are_needed_for_a_base",
     "On a distribution row this column holds ONE of the two rates a base "
     "needs. A distribution is a share of collections, so recovering a base is "
     "payment / sharing_rate / tax_rate. Where the row carries the tax rate the "
     "sharing rate is quoted in bound_basis and vice versa; where only one of "
     "the two exists, derived_taxable_base is blank by rule."),
    ("derived_taxable_base:nd_motor_fuel_is_a_lower_bound",
     "On North Dakota MOTOR_FUEL rows this is GALLONS and is a LOWER BOUND. Two "
     "identified leaks both push the true count up: NDCC 57-43.2-03(1) taxes "
     "propane ad valorem and dyed diesel at four cents rather than 23, and NDCC "
     "57-43.1-03.2(1) refunds fuel tax to individual enrolled members buying on "
     "their own reservation. Neither can push it down."),
    ("period_start:nd_distribution_rows_carry_the_payment_date",
     "On North Dakota distribution rows period_start and period_end are both "
     "the PAYMENT DATE. The State Treasurer publishes when the money moved and "
     "North Dakota publishes no statement of which collection period each "
     "payment settles, so the underlying sales are earlier by an unpublished "
     "lag. Do not read these as tax periods."),
    ("amount_source_quote:tabular_convention",
     "Where the source is a table rather than prose, the quote is the printed "
     "cells of ONE row joined by ' | ', each preceded by its column heading. "
     "Nothing is reordered and no figure is recomputed."),
    ("rate_source_quote:two_quotes_joined_by_double_pipe",
     "Where a row rests on more than one instrument - a per-gallon statutory "
     "rate and an agreement's sharing percentage, or a rate spread across two "
     "Century Code sections - the verbatim quotes are joined by ' || ' in "
     "source order. Each side is quoted in full."),
    ("tax_observation_id:TTAX-NDT_id_block",
     "North Dakota non-severance tribal tax rows use the TTAX-NDT- block. "
     "Script 113 owns TTAX-ND- and renumbers by counting that prefix; TTAX-NDT- "
     "does not match it, so neither build can renumber the other's rows."),
]


def write_codebook_fragment():
    """FRAGMENT ONLY. codebook_master.csv is being written concurrently and is
    never touched here - `code/cedar_codebook.py build` regenerates it from
    fragments when its owner chooses to."""
    p = FRAG / "15_tribal_tax.csv"
    if not p.exists():
        print("  codebook fragment 15_tribal_tax.csv missing; skipped")
        return
    bak = FRAG / f"15_tribal_tax.csv.bak_{TODAY}_pre116"
    if not bak.exists():
        shutil.copy2(p, bak)
    cur = read_csv(p)
    if not cur:
        print("  codebook fragment read empty; refusing to write")
        return
    fields = list(cur[0].keys())
    have = {r.get("variable") for r in cur}
    tax = read_csv(CLEAN / "tribal_tax_bases.csv")
    n = len(tax)
    added = 0
    for var, desc in CODEBOOK_VARS:
        if var in have:
            continue
        row = {k: "" for k in fields}
        vals = {"dataset": "15_tribal_tax", "variable": var, "description": desc,
                "type": "text", "units": "text", "published": "1",
                "access_tier": "public", "n_rows": str(n), "pct_filled": "",
                "generated": TODAY, "built_date": TODAY, "source": SCRIPT}
        for k, v in vals.items():
            if k in row:
                row[k] = v
        cur.append(row)
        have.add(var)
        added += 1
    # Standing rule 10: a number in a doc that is not recomputed from the data
    # is a claim. n_rows and pct_filled on the column rows were computed against
    # 86 rows and this build moved the file, so they are regenerated here rather
    # than left stale. No other cell is touched.
    resynced = 0
    for r in cur:
        var = r.get("variable", "")
        if "n_rows" not in r:
            continue
        if r.get("n_rows") != str(n):
            r["n_rows"] = str(n)
            resynced += 1
        # pct_filled is only meaningful for a COLUMN row; a value-level row
        # documents one permitted value and has no column to measure.
        if var in FIELDS and "pct_filled" in r and n:
            filled = sum(1 for t in tax if (t.get(var) or "").strip())
            r["pct_filled"] = f"{100.0 * filled / n:.1f}"
    write_csv(p, cur, fields)
    print(f"  codebook fragment 15_tribal_tax.csv: +{added} variables, "
          f"{resynced} n_rows resynced to {n}, {len(cur)} rows total")


# ==========================================================================
# LOG
# ==========================================================================
def write_log(rows, by_tribe_type, usable, listings, refused_tribes,
              refused_rows, absences, derived_count, resolved, probe_states,
              unresolved, problems):
    L = []
    A = L.append
    A("# North Dakota per-tribe non-gaming tax distributions - build log")
    A("")
    A(f"*Built {TODAY} by `{SCRIPT}`. Output: appended `MOTOR_FUEL`, "
      "`TOBACCO`, `RETAIL_SALES` and `ALCOHOL` rows in "
      "`data/clean/tribal_tax_bases.csv`, a codebook fragment at "
      "`data/clean/codebook/15_tribal_tax.csv`, "
      f"`review/nd_tribal_tax_unresolved_{TODAY}.csv`, raw under "
      "`data/raw/external/nd_tribal_tax/` with `_SOURCE_MANIFEST.csv` and "
      "md5s.*")
    A("")
    A("---")
    A("")
    A("## The finding: this is the first per-tribe non-gaming tax money in the "
      "dataset, and it arrives with both legs of the division")
    A("")
    A("`docs/TRIBAL_TAX_BUILD_LOG.md` recorded that **no tribe carried a "
      "per-tribe non-gaming tax amount** and that the netting machinery was "
      "\"built, tested and idle\". Four North Dakota tribes now carry one. "
      "Washington holds the fullest fuel-agreement roster in the country and "
      "**may not publish** the per-tribe figures - its report says so in its "
      "own words. North Dakota does not withhold them.")
    A("")
    A("More than that: for motor fuel the North Dakota Legislative Council "
      "prints, in a single paragraph, **the statutory rate and the per-tribe "
      "allocation percentage**. A distribution is a share of collections, so a "
      "base needs two divisions and two quoted rates:")
    A("")
    A("```")
    A("payment / tribal_allocation_share = tax collected inside the reservation")
    A("tax collected / statutory_rate    = the taxable base")
    A("```")
    A("")
    A("That is the first time both have been available together anywhere in "
      "this dataset.")
    A("")
    A("---")
    A("")
    A("## What the ND Treasurer publishes, per tribe")
    A("")
    A("| Tribe | Tax type | Payments | Total | First | Last |")
    A("|---|---|---:|---:|---|---|")
    for (tribe, dtype), pay in sorted(by_tribe_type.items()):
        tot = sum(a for _d, a in pay)
        A(f"| {tribe} | {dtype} | {len(pay)} | ${tot:,.2f} | "
          f"{min(d for d, _a in pay)} | {max(d for d, _a in pay)} |")
    A("")
    A("Each tribe's listing was read whole and **footed against the "
      "application's own printed Grand Total** before any row was written:")
    A("")
    A("| Tribe | Payments in listing | Rows sum to | Printed Grand Total |")
    A("|---|---:|---:|---:|")
    for tid, rec in sorted(usable.items()):
        s = sum(r[3] for r in rec["rows"])
        A(f"| {rec['tribe']} | {len(rec['rows'])} | ${s:,.2f} | "
          f"${rec['grand']:,.2f} |")
    A("")
    if refused_tribes:
        A("Refused whole: " + "; ".join(f"{t} ({why})"
                                        for t, why in refused_tribes))
        A("")
    A("---")
    A("")
    A("## Only one of the four taxes derives a base, and it derives a VOLUME")
    A("")
    A("| Tax | Sharing rate published? | Statutory rate a single number? | "
      "Base derived |")
    A("|---|---|---|---|")
    A("| **MOTOR_FUEL** | yes, per tribe | yes - 23 cents per gallon under "
      "**both** NDCC 57-43.1-02(1) and 57-43.2-02(1) | **GALLONS** |")
    A("| TOBACCO | yes, 87% less 1% | **no** - 22 mills per cigarette, 28% of "
      "wholesale price on cigars and pipe tobacco, 60c and 16c per ounce on "
      "snuff and chewing tobacco | none |")
    A("| RETAIL_SALES | yes, 80/20 | **no** - five rates in one agreement "
      "(5%, 3%, 7%, 3%, plus .25% tribal local) | none |")
    A("| ALCOHOL | yes, 80/20 | **no** - a six-tier per-gallon schedule, "
      "possibly pooled with a 7% ad valorem tax | none |")
    A("")
    A("The single derivation:")
    A("")
    A("```")
    A("payment / tribal share (0.86, 0.75, 0.69 or 0.95) = fuel tax collected")
    A("fuel tax collected / $0.23 per gallon             = GALLONS")
    A("```")
    A("")
    A("**It is a volume. It is not a dollar figure and must never be read as "
      "one.** It is also a **lower bound**: NDCC 57-43.2-03(1) taxes propane at "
      "two percent of value and dyed diesel at four cents rather than 23, and "
      "NDCC 57-43.1-03.2(1) refunds fuel tax to individual enrolled members "
      "buying on their own reservation. Both leaks push the true gallon count "
      "**up**, never down.")
    A("")
    A("### The one percent administration fee is a percentage POINT")
    A("")
    A("The source says *87 percent, less a 1 percent administration fee* to the "
      "tribe and *thirteen percent, plus the 1 percent administration fee* to "
      "the general fund. Those two legs sum to exactly 100 percent only if the "
      "fee is one percentage **point** off the tribe's share - 86 and 14, not "
      "86.13 and 13.87. **The source's own second sentence forces the "
      "reading**, and it forces it identically for all four tribes.")
    A("")
    A("| Tribe | Agreement effective | Allocation stated | Tribal share used |")
    A("|---|---|---|---:|")
    for tribe, share in MEMO_FUEL_SHARE.items():
        A(f"| {tribe} | {MEMO_FUEL_AGREEMENT_FROM[tribe]} | "
          f"{round(share * 100) + 1}% less 1% | **{share:.2f}** "
          f"(from {MEMO_FUEL_SHARE_FROM[tribe]}) |")
    A("")
    A("Standing Rock is the exception and it costs rows. Its agreement became "
      "effective **1999-01-01** and the Legislative Council states an "
      "allocation only for the agreement **renegotiated 2015-05-01**. Carrying "
      "the 2015 percentage backwards would be an assumption, so no Standing "
      "Rock fuel payment before 2015-05-01 is divided - it keeps the amount and "
      "the per-gallon rate and gets no base. One division of two is not a base.")
    A("")
    A("Derived rows by tribe:")
    A("")
    A("| Tribe | Payments | of which derive a base |")
    A("|---|---:|---:|")
    for (tribe, dtype), pay in sorted(by_tribe_type.items()):
        if dtype != "Tribal Highway Tax":
            continue
        A(f"| {tribe} | {len(pay)} | "
          f"{derived_count.get((tribe, 'MOTOR_FUEL'), 0)} |")
    A("")
    A("---")
    A("")
    A("## The four documented failure modes, checked on all four taxes")
    A("")
    A("| Failure mode | Fired? | Where |")
    A("|---|---|---|")
    A("| **Marginal base** (\"in excess of\") | no | both fuel statutes read "
      "\"on **all** motor vehicle fuel sold or used in this state\"; the "
      "allocations are flat shares |")
    A("| **Graduated schedule read as flat** | **yes, three times** | tobacco "
      "(four bases), sales (five rates), alcohol (six per-gallon tiers) |")
    A("| **Receipts lag obligations** | **yes** | the Treasurer publishes a "
      "payment date only. Standing Rock's sales tax is the live case: state "
      "administration was discontinued **2017-03-07** and payments continue to "
      "**2019-03-14** |")
    A("| **Mixed units in one figure** | **yes** | \"Tribal Alcohol\" can pool "
      "a per-wine-gallon wholesale tax with a seven percent ad valorem gross "
      "receipts tax - NDCC 57-39.10-07 and -09 pay both out of the same tribal "
      "allocation fund |")
    A("")
    A("A fifth complication, short of failure: **the tobacco products wholesale "
      "allocation in NDCC 57-39.10-04(4) is still a PER-CAPITA FORMULA** - "
      "enrolled membership times state revenue per capita. That is the same "
      "shape as Washington's per-capita fuel agreements, which `derive_base()` "
      "already refuses in code. The 2023 session replaced the per-capita method "
      "for **alcohol only**; the alcohol series begins 2025-01-15 and so falls "
      "entirely under the 80/20 method that replaced it.")
    A("")
    A("---")
    A("")
    A("## Measured absences")
    A("")
    A("| Tribe | Tax type with no distribution |")
    A("|---|---|")
    for tribe, tax_type, label in absences:
        A(f"| {tribe} | {label} |")
    A("")
    A("These are **measured**, not blank. Each tribe's complete listing foots "
      "to the application's own Grand Total and contains no payment of that "
      "type.")
    A("")
    A("**They were NOT measured by per-type queries, and that matters.** The "
      "application validates its `DistType` parameter against an unpublished "
      "code list and answers an unknown code with **\"Unable to Process\"** - "
      "an application error, not an empty result. Seven candidate codes were "
      "probed and every one errored. A per-type sweep would have produced false "
      "absences indistinguishable from real ones. This is the same class as "
      "South Dakota's broken search: a site's own navigation failing is a fact "
      "about the navigation.")
    A("")
    A(f"Tribe ids 5 and 6 were probed for the same reason and answered "
      f"`{probe_states}`. The application **errors** outside its own list "
      "rather than returning nothing, which is what closes the list at four - "
      "while **NDCC 57-39.9-01 and 57-39.10-01 each name five tribes**. "
      "Sisseton-Wahpeton Oyate is authorised by statute and absent from the "
      "Treasurer's tribe list.")
    A("")
    A("---")
    A("")
    A("## Measured and deliberately NOT published")
    A("")
    if refused_rows:
        agg = defaultdict(lambda: [0, 0.0, "9999", "0000"])
        for tribe, dtype, pdate, amt in refused_rows:
            a = agg[(tribe, dtype)]
            a[0] += 1
            a[1] += amt
            a[2] = min(a[2], pdate)
            a[3] = max(a[3], pdate)
        A("| Tribe | Distribution type | Payments | Total | Range | Why not "
          "published |")
        A("|---|---|---:|---:|---|---|")
        for (tribe, dtype), (n, tot, d0, d1) in sorted(agg.items()):
            A(f"| {tribe} | {dtype} | {n} | ${tot:,.2f} | {d0} .. {d1} | no "
              "authorising instrument retrieved |")
        A("")
        A("Rule 4 forbids publishing a tribal tax figure whose authority is "
          "unstated, and *\"County Sales Tax\"* paid to a tribe is exactly the "
          "kind of number that invites a wrong reading in either direction. It "
          "is measured here, staged in `review/`, and kept out of the CSV until "
          "the instrument is found.")
    else:
        A("None.")
    A("")
    A("---")
    A("")
    A("## Entity resolution")
    A("")
    A("| Treasurer label | Spine id | How |")
    A("|---|---|---|")
    for name, (tid, canon, how) in resolved.items():
        A(f"| {name} | {tid or '**refused**'} | {how} |")
    A("")
    A("**\"Turtle Mtn. Chippewa\" is the one hand ruling in this build, and it "
      "was worth making rather than refusing** - it keys 189 motor fuel "
      "payments worth $10.85M that would otherwise have been dropped. It does "
      "not rest on the matcher. The Legislative Council names the agreement "
      "party in full - *\"The Turtle Mountain Band of Chippewa Indians, which "
      "became effective September 1, 2010\"* - and the Treasurer's first Turtle "
      "Mountain distribution is 2010-11-15. Two guards run at build time and "
      "both must hold or the build refuses to key a dollar: the Legislative "
      "Council's full name must resolve to the same id through the shared "
      "resolver, and **exactly one** federally recognised tribe in North Dakota "
      "may carry the name. That is a uniqueness test, not a similarity score. "
      "The alias is staged for the spine so no later build re-rules it.")
    A("")
    A("---")
    A("")
    A("## Netting: still zero North Dakota tribes, and the blocker has MOVED")
    A("")
    A("This build supplies the input the subtraction method was waiting for - "
      "per-tribe non-gaming money, for four tribes, over twenty-one years. It "
      "still cannot net a single North Dakota tribe, and the reason is now the "
      "**other operand**.")
    A("")
    A("**North Dakota seals every tribal gaming record by statute.** "
      "`data/clean/state_gaming_observations.csv` carries `SG-ND-00001`, a "
      "documented absence quoting *N.D.C.C. 54-58-02, \"Tribal gaming records "
      "not subject to disclosure\"*, flagged `held_by_state_but_sealed`. "
      "`gaming_revenue_bounds.csv` holds **zero** North Dakota rows. There is "
      "no whole-tribe or gaming revenue figure for any ND tribe anywhere in "
      "this dataset to subtract from.")
    A("")
    A("So the honest count is:")
    A("")
    A("- **4 of 4** tribes in the Treasurer's list now carry per-tribe "
      "non-gaming tax money.")
    A("- **1** tribe - the Three Affiliated Tribes - carries **two** separately "
      "taxed categories here (motor fuel and alcohol) plus the severance series "
      "from script 113, so it is the best-covered subtrahend in the dataset.")
    A("- **0** tribes have a whole-tribe revenue figure to net it out of.")
    A("")
    A("The minuend has to come from a **tribal** source - an audited financial "
      "statement, a bond official statement, a tribal annual report - because "
      "North Dakota will not supply it. That is a different research task from "
      "the one this build closed, and naming it precisely is worth more than "
      "the rows.")
    A("")
    A("---")
    A("")
    A("## Rows added")
    A("")
    c = Counter((r["tax_type"], r["measurement_status"]) for r in rows)
    A("| tax_type | measurement_status | rows |")
    A("|---|---|---:|")
    for (tt, ms), n in sorted(c.items()):
        A(f"| {tt} | {ms} | {n} |")
    A(f"")
    A(f"**Total {len(rows)} rows.** `derived_taxable_base` is populated on "
      f"{sum(1 for r in rows if r['derived_taxable_base'])} of them, all "
      "MOTOR_FUEL, all in gallons.")
    A("")
    if problems:
        A("## Quotes that could not be verified against their source file")
        A("")
        for lab, fn, frag in problems:
            A(f"- **{lab}** in `{fn}`: `{frag}`")
        A("")
    A("## Unresolved, staged for a ruling")
    A("")
    for u in unresolved:
        A(f"- **{u['item']}** (`{u['kind']}`) - {u['detail']}")
    A("")
    (DOCS / "ND_TRIBAL_TAX_LOG.md").write_text("\n".join(L), encoding="utf-8")
    print("  docs/ND_TRIBAL_TAX_LOG.md written")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd in ("fetch", "all"):
        do_fetch()
    if cmd in ("build", "all"):
        build()


if __name__ == "__main__":
    main()
