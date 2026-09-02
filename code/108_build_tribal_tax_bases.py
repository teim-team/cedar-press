#!/usr/bin/env python3
"""
Cedar Press - 108: tribal tax bases (fuel, tobacco, lodging, sales, severance).

WHY THIS EXISTS
---------------
Elijah, 2026-08-07:

    "tribes have to pay gas excise tax and all those sin taxes and prob
     occupancy taxes too (the former had the Colville cig case, the latter was a
     Navajo case) which are findable, so we can isolate the gaming revenue
     further."

Where a tax is collected, a rate is published and a remittance is recorded.
State-tribal fuel and tobacco tax agreements exist because the incidence was
litigated, and they leave per-tribe records in state revenue departments that
have nothing to do with gaming. That gives this build two uses, and the second
stands on its own:

  1. SUBTRACTION. `may_attribute_to_single_property()` refuses a whole-tribe
     revenue base. Netting out separately-taxed categories reopens it.
  2. A DATASET NOBODY HAS - per-tribe fuel, tobacco and lodging economic
     activity read out of state revenue records. A measure of the NON-gaming
     tribal economy, which gaming coverage systematically ignores.

THE FOUR RULES THAT KEEP THIS HONEST (docs/TRIBAL_TAX_DECOMPOSITION.md)
----------------------------------------------------------------------
1. A TAXABLE BASE IS NOT REVENUE. Fuel excise is per gallon and tobacco per
   pack, so a derived base is a VOLUME unless the tax is ad valorem.
   `rate_unit` and `base_unit` are written on every row and a gallon count is
   never allowed to read as a dollar figure. `derive_base()` refuses to divide
   unless the two units are compatible.
2. SUBTRACTION YIELDS AN UPPER BOUND, NEVER A VALUE. We can only subtract what
   happens to be taxed; untaxed government receipts, grants and other
   enterprise income stay in the residual. Any gaming figure derived that way
   is `bound_basis=NON_GAMING_CATEGORIES_NETTED` and
   `measurement_status=BOUNDED_DERIVED_REVENUE`. A FACTUAL BOUND IS NOT A
   CONFIDENCE INTERVAL - the words "estimate", "predicted" and "confidence
   interval" appear nowhere in this dataset, and `assert_no_forecast_language()`
   enforces that on every written cell.
3. PERIODS AND ENTITIES MUST MATCH ON BOTH SIDES. A calendar-year remittance
   against a fiscal-year revenue figure is not a subtraction, and a tribal
   enterprise remitting under its own name is not automatically inside the
   tribe's reported revenue.
4. NEVER PUBLISH A BARE "TAX BURDEN" FIGURE. Tribal taxation is legally
   contested ground and a naked number invites a wrong reading in both
   directions, so `agreement_or_statute_cite` is required on every row and the
   writer refuses a row without it.

The case names in Elijah's note are ORIENTATION, NOT CITATIONS. Every row cites
the retrieved agreement or statute; no row cites a case.

TWO QUOTES OR IT DOES NOT EXIST
-------------------------------
Same standard as docs/SELF_DISCLOSED_DERIVATION.md. A base is derived only
where the SAME period carries a quoted RATE and a quoted AMOUNT. A rate with no
amount is `RATE_ONLY_NO_AMOUNT`; an amount with no rate is a remittance and
nothing more. Neither is a derivation and neither may be presented as one.

CONTAINMENT
-----------
Containment has failed nine independent ways in this project (AGENTS.md). The
guards that survived measurement are the ones used here and only those:
  * the record's name must be at least as specific as the entity's,
  * the spine row's state must agree with the source's state,
  * a match resting only on NAME_TRAPS tokens is refused,
  * anything name-only goes to review/ at Tier B, never into a published row.

PDF TABLES ARE READ BY WORD POSITION, NEVER LINEARLY
----------------------------------------------------
Script 94 recorded the failure this build would otherwise repeat: `pdftotext
-layout` shifts a label column against its numbers, so every row is
well-sourced and attached to the wrong line. Read linearly, the Oklahoma
apportionment report says $70,341,313.12 of diesel tax went "To Participating
Tribes"; read by position, the apportionment summary says the tribal
apportionment across all statutory funds was $26,120,361.46. The first number
is an artefact of the text layer. Every figure here is taken from word
positions and, where the source prints a total, checked against it.

RUN
    py -3 code/108_build_tribal_tax_bases.py fetch    # raw + manifest + md5
    py -3 code/108_build_tribal_tax_bases.py build    # parse -> CSV
    py -3 code/108_build_tribal_tax_bases.py all

WRITES
    data/raw/external/tribal_tax/<st>/...      + _SOURCE_MANIFEST.csv (md5s)
    data/clean/tribal_tax_bases.csv
    review/tribal_tax_unresolved_<date>.csv
    data/clean/codebook_master.csv             (appends dataset 15_tribal_tax)
    docs/TRIBAL_TAX_BUILD_LOG.md               (state-by-state)

OWNS none of the files other agents hold: nothing here writes gaming_*, nigc_*,
compact_*, ca_gaming_*, wa_*, fl_*, state_gaming_observations.csv,
gaming_revenue_bounds.csv, subawards.csv, consultation_*, oira_*, hearing_*,
earmarks.csv, np_financials.csv, entity_*, resource_*, the identifier ledger or
the spine.
"""

import csv
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
LOGS = CEDAR / "logs"
RAW = CEDAR / "data" / "raw" / "external" / "tribal_tax"
DOCS = CEDAR / "docs"

TODAY = date.today().isoformat()
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

sys.path.insert(0, str(CODE))
from cedar_domain import NAME_TRAPS, Tier  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "party_rulings", str(CODE / "33_apply_party_rulings.py"))
_pr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pr)
resolve_entity, norm, core = _pr.resolve_entity, _pr.norm, _pr.core

# ---------------------------------------------------------------------------
# VOCABULARY. Declared once here because no other module owns these concepts;
# if a second tax build appears they move to cedar_domain.py rather than being
# re-typed (spec 13.1).
# ---------------------------------------------------------------------------

TAX_TYPES = frozenset({
    "MOTOR_FUEL", "TOBACCO", "TRANSIENT_OCCUPANCY", "ALCOHOL",
    "RETAIL_SALES", "SEVERANCE", "OTHER",
})

# What the row actually is. A roster entry and a remittance are different
# facts and a coverage table that pools them is lying about coverage.
STATUS_PER_TRIBE_AMOUNT = "REPORTED_TAX_REMITTANCE_PER_TRIBE"
STATUS_AGGREGATE_AMOUNT = "REPORTED_TAX_REMITTANCE_MULTI_TRIBE_AGGREGATE"
STATUS_ROSTER = "AGREEMENT_ROSTER_NO_AMOUNT"
STATUS_RATE_ONLY = "RATE_ONLY_NO_AMOUNT"
STATUS_DERIVED_BASE = "DERIVED_TAXABLE_BASE"
STATUS_BOUNDED = "BOUNDED_DERIVED_REVENUE"      # the netting output; unused yet

MEASUREMENT_STATUSES = frozenset({
    STATUS_PER_TRIBE_AMOUNT, STATUS_AGGREGATE_AMOUNT, STATUS_ROSTER,
    STATUS_RATE_ONLY, STATUS_DERIVED_BASE, STATUS_BOUNDED,
})

# A rate levied per unit yields a base measured in that unit. Dollars only come
# out of an ad valorem rate. This table is the whole of rule 1 in code form.
RATE_UNIT_TO_BASE_UNIT = {
    "usd_per_gallon": "gallons",
    "usd_per_pack_of_20": "packs_of_20",
    "usd_per_ounce": "ounces",
    "share_of_wholesale_price": "usd",
    "share_of_retail_price": "usd",
    "share_of_state_tax_collected": None,     # a revenue SHARE, not a rate on a base
    "share_of_gross_receipts": "usd",
    "per_capita_formula": None,               # not levied on a base at all
}

# Rule 2, enforced rather than remembered. A bound is a fact about the world;
# a forecast is a claim about a distribution. These words would turn one into
# the other and are refused at write time.
FORECAST_WORDS = re.compile(
    r"\b(estimate[ds]?|estimating|estimation|predict(?:ed|s|ion)?|forecast(?:ed|s)?|"
    r"confidence interval|margin of error|projected|modell?ed)\b", re.I)

# Columns whose text is ours; source quotes are exempt because a source may use
# the word "estimate" about its own formula and we must reproduce it verbatim.
OUR_TEXT_COLUMNS = ("measurement_status", "bound_basis", "confidence",
                    "base_unit", "rate_unit")

FIELDS = [
    "tax_observation_id", "tribe_id", "tribe_name", "state", "tax_type",
    "period_start", "period_end", "tax_remitted_usd", "statutory_rate",
    "rate_unit", "derived_taxable_base", "base_unit", "rate_source_quote",
    "amount_source_quote", "agreement_or_statute_cite", "measurement_status",
    "bound_basis", "source_url", "fetched_date", "tier", "confidence",
    "built_date",
]


# ---------------------------------------------------------------------------
# Fetching. One lock per host even for a one-shot pull, so a later agent that
# wants to poll the host can see who touched it (docs/PULL_DISCIPLINE.md).
# api.usaspending.gov is edge-blocking and is never contacted here.
# ---------------------------------------------------------------------------

BANNED_HOSTS = {"api.usaspending.gov"}


def claim_host(host, note):
    LOGS.mkdir(parents=True, exist_ok=True)
    p = LOGS / f"_HOSTLOCK_{host}.json"
    if p.exists():
        try:
            cur = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            cur = {}
        if cur.get("active") and cur.get("script") != "code/108_build_tribal_tax_bases.py":
            cur.setdefault("queue", []).append({
                "script": "code/108_build_tribal_tax_bases.py",
                "host_target": host, "purpose": note,
                "queued_at": datetime.now(timezone.utc).isoformat()})
            p.write_text(json.dumps(cur, indent=1), encoding="utf-8")
            print(f"  [lock] {host} held by {cur.get('script')}; queued, "
                  f"single-shot fetch only")
            return
    p.write_text(json.dumps({
        "host": host, "pid": os.getpid(),
        "script": "code/108_build_tribal_tax_bases.py",
        "claimed_at": datetime.now(timezone.utc).isoformat(),
        "active": False,           # single-shot; no poller left running
        "policy": "single-shot document fetch, no retry loop",
        "note": note, "queue": [],
    }, indent=1), encoding="utf-8")


def fetch(url, dest):
    host = re.sub(r"^https?://([^/]+).*", r"\1", url)
    if host in BANNED_HOSTS:
        raise RuntimeError(f"refusing banned host {host}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.run(
        ["curl", "-s", "-L", "-A", UA, "--max-time", "180",
         "-w", "%{http_code}", "-o", str(dest), url],
        capture_output=True, text=True)
    status = int((p.stdout or "0").strip() or 0)
    body = dest.read_bytes() if dest.exists() else b""
    # CHECK THE HTTP STATUS, NOT THE FILE. A 404 body still parses.
    return status, body


def md5(b):
    return hashlib.md5(b).hexdigest()


# ---------------------------------------------------------------------------
# SOURCES. Each entry is a document we retrieved and can quote.
# ---------------------------------------------------------------------------

SOURCES = [
    dict(key="wa_dol_fuel_2024", state="WA",
         url="https://dol.wa.gov/media/pdf/3665/2024-tribal-fuel-tax-reportpdf",
         path="wa/2024_tribal_fuel_tax_agreement_report.pdf",
         publisher="Washington State Department of Licensing",
         title="2024 Tribal Fuel Tax Agreement Report"),
    dict(key="wa_dor_sales_compact", state="WA",
         url="https://dor.wa.gov/sites/default/files/2025-07/DORARLTribalRSTaxCompact.pdf",
         path="wa/dor_tribal_retail_sales_tax_compact_revenue_sharing.pdf",
         publisher="Washington State Department of Revenue",
         title="Tribal Retail Sales Tax Compact Revenue Sharing (agency request legislation)"),
    dict(key="mt_biennial_other_taxes", state="MT",
         url=("https://revenue.mt.gov/files/DOR-Publications/Biennial-Reports/"
              "July-1-2022-June-30-2024-Biennial-Report/"
              "Biennial-Report-7-1-2022-6-30-2024-Other-Taxes.pdf"),
         path="mt/mt_biennial_2022_2024_other_taxes.pdf",
         publisher="Montana Department of Revenue",
         title="Biennial Report July 1, 2022 - June 30, 2024, Other Taxes chapter"),
    dict(key="ok_otc_ar2025", state="OK",
         url=("https://oklahoma.gov/content/dam/ok/en/tax/documents/resources/"
              "reports/annual-reports/otc/AR-2025.pdf"),
         path="ok/otc_revenue_and_apportionment_FY2025.pdf",
         publisher="Oklahoma Tax Commission",
         title="FY2025 Revenue & Apportionment Report"),
    dict(key="wa_rcw_82_38_030", state="WA",
         url="https://app.leg.wa.gov/RCW/default.aspx?cite=82.38.030",
         path="wa/rcw_82_38_030_fuel_tax_rate.html",
         publisher="Washington State Legislature",
         title="RCW 82.38.030 Tax imposed - Rate - Incidence"),
    dict(key="nm_cig_stamp_listing", state="NM",
         url=("https://www.tax.newmexico.gov/governments/tribal-governments/"
              "cigarette-tax-credit-stamp-listing/"),
         path="nm/cigarette_tax_credit_stamp_listing.html",
         publisher="New Mexico Taxation and Revenue Department",
         title="Cigarette Tax Credit Stamp Listing"),
]

# Michigan publishes one page per tribe holding that tribe's tax agreement and
# every amendment with its effective date. That is a per-tribe agreement roster
# with a citable instrument, which is exactly what rule 4 requires to travel
# with a row.
MI_TRIBE_SLUGS = [
    "bay-mills-indian-community",
    "grand-traverse-band-of-ottawa-and-chippewa-indians",
    "hannahville-indian-community",
    "little-river-band-of-ottawa-indians",
    "little-traverse-bay-bands-of-odawa-indians",
    "match-e-be-nash-she-wish-band-of-pottawatomi-indians",
    "nottawaseppi-huron-band-of-potawatomi-indians",
    "pokagon-band-of-potawatomi-indians",
    "saginaw-chippewa-indian-tribe-of-michigan",
    "sault-ste--marie-tribe-of-chippewa-indians",
]
for _slug in MI_TRIBE_SLUGS:
    SOURCES.append(dict(
        key=f"mi_agreement_{_slug}", state="MI",
        url=f"https://www.michigan.gov/taxes/tribes/agreements/{_slug}",
        path=f"mi/agreement_{_slug}.html",
        publisher="Michigan Department of Treasury",
        title=f"Tax agreement page: {_slug.replace('-', ' ')}"))


def do_fetch():
    print("=== 108 fetch ===")
    hosts = sorted({re.sub(r"^https?://([^/]+).*", r"\1", s["url"])
                    for s in SOURCES})
    for h in hosts:
        claim_host(h, "tribal fuel/tobacco/lodging tax agreement documents")

    man_rows = []
    for s in SOURCES:
        dest = RAW / s["path"]
        status, body = fetch(s["url"], dest)
        ok = status == 200 and len(body) > 500
        print(f"  [{status}] {len(body):>9,}B  {s['path']}")
        man_rows.append(dict(
            file=s["path"], key=s["key"], state=s["state"], url=s["url"],
            http_status=status, bytes=len(body),
            md5=md5(body) if body else "", publisher=s["publisher"],
            title=s["title"], fetched_date=TODAY,
            usable=int(bool(ok))))
    RAW.mkdir(parents=True, exist_ok=True)
    with open(RAW / "_SOURCE_MANIFEST.csv", "w", encoding="utf-8",
              newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(man_rows[0].keys()))
        w.writeheader()
        w.writerows(man_rows)
    bad = [r for r in man_rows if not r["usable"]]
    print(f"\n  manifest: {len(man_rows)} files, {len(bad)} unusable")
    for r in bad:
        print(f"    UNUSABLE {r['http_status']} {r['file']}")


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


def pdf_lines(path):
    """Word-position lines: [(y_band, [(x0, text), ...]), ...] per page.

    Never `pdftotext -layout`. See script 94: the linear text layer shifts a
    label column against its numbers and every row comes out well-sourced and
    wrong.
    """
    import pdfplumber
    pages = []
    with pdfplumber.open(str(path)) as pdf:
        for pg in pdf.pages:
            bands = {}
            for w in pg.extract_words():
                bands.setdefault(round(w["top"] / 3), []).append(
                    (w["x0"], w["text"]))
            pages.append([(k, sorted(v)) for k, v in sorted(bands.items())])
    return pages


def band_text(band):
    return " ".join(t for _, t in band[1])


def html_text_lines(path):
    raw = Path(path).read_bytes().decode("utf-8", "replace")
    raw = re.sub(r"<head\b.*?</head>", " ", raw, flags=re.S | re.I)
    raw = re.sub(r"<(script|style|noscript|svg)\b.*?</\1>", " ", raw,
                 flags=re.S | re.I)
    raw = re.sub(r"<!--.*?-->", " ", raw, flags=re.S)
    raw = re.sub(r"</(p|div|li|tr|h\d|td|th|br)>", "\n", raw, flags=re.I)
    import html as _h
    txt = _h.unescape(re.sub(r"<[^>]+>", "\n", raw))
    out, seen = [], set()
    for line in txt.split("\n"):
        line = re.sub(r"\s+", " ", line).strip()
        if line and line not in seen:
            seen.add(line)
            out.append(line)
    return out


def money(s):
    return float(re.sub(r"[^\d.\-]", "", s))


# ---------------------------------------------------------------------------
# Entity resolution. `resolve_entity` is the ONE resolver (standing rule 8);
# this adds only the guards AGENTS.md says survived measurement.
# ---------------------------------------------------------------------------


class Resolver:
    def __init__(self, spine):
        self.spine = spine
        self.by_id = {r["tribe_id"]: r for r in spine}
        self.unresolved = []

    def resolve(self, name, state, context):
        """(tribe_id, canonical_name, tier, reason). Never guesses."""
        tid, canon, how = resolve_entity(name, self.spine)
        if not tid:
            self.unresolved.append(dict(
                source_name=name, state=state, context=context,
                reason=how, resolved_tribe_id="", staged_date=TODAY))
            return "", name, Tier.B.value, how

        row = self.by_id[tid]

        # STATE AGREEMENT. Cross-state containment put a New Mexico cultural
        # centre onto a Hawaii one and a Cherokee Nation school onto a North
        # Carolina CDFI. A tax agreement is with a state; the entity has to be
        # in it.
        if state and row.get("state") and row["state"] != state:
            self.unresolved.append(dict(
                source_name=name, state=state, context=context,
                reason=f"state_disagreement:spine={row['state']}",
                resolved_tribe_id="", staged_date=TODAY))
            return "", name, Tier.B.value, f"state_disagreement:{row['state']}"

        if how == "containment":
            rc, ec = core(name), core(row["canonical_name"])
            # The record must be at least as specific as the entity. The
            # reverse direction is how NATIVE VILLAGE OF ELIM became Elim
            # Native Corporation - containment rewards the shortest name.
            if not (ec <= rc):
                self.unresolved.append(dict(
                    source_name=name, state=state, context=context,
                    reason="containment_entity_more_specific_than_record",
                    resolved_tribe_id="", staged_date=TODAY))
                return "", name, Tier.B.value, "containment_wrong_direction"
            # A match resting only on trap tokens is not a match.
            if ec and ec <= NAME_TRAPS:
                self.unresolved.append(dict(
                    source_name=name, state=state, context=context,
                    reason=f"name_trap_only:{sorted(ec)}",
                    resolved_tribe_id="", staged_date=TODAY))
                return "", name, Tier.B.value, "name_trap_only"

        return tid, row["canonical_name"], Tier.A.value, how


# ---------------------------------------------------------------------------
# Rule 1 in code: a base only comes out of a rate levied on a base, and it
# carries that rate's unit.
# ---------------------------------------------------------------------------


def derive_base(amount_usd, rate, rate_unit):
    """(base, base_unit) or (None, None). Refuses where the rate is a share of
    somebody else's tax, or a per-capita formula, because neither is levied on
    a quantity and dividing by it would manufacture a base that does not
    exist."""
    if amount_usd is None or rate in (None, "", 0):
        return None, None
    base_unit = RATE_UNIT_TO_BASE_UNIT.get(rate_unit)
    if base_unit is None:
        return None, None
    try:
        return round(float(amount_usd) / float(rate), 2), base_unit
    except (TypeError, ValueError, ZeroDivisionError):
        return None, None


def assert_no_forecast_language(row):
    """Rule 2. A factual bound is not a confidence interval."""
    for col in OUR_TEXT_COLUMNS:
        v = str(row.get(col) or "")
        m = FORECAST_WORDS.search(v)
        if m:
            raise AssertionError(
                f"forecast language {m.group(0)!r} in {col} of "
                f"{row.get('tax_observation_id')}")


class Rows:
    def __init__(self):
        self.rows = []
        self.seq = {}

    def add(self, **kw):
        st = kw["state"]
        self.seq[st] = self.seq.get(st, 0) + 1
        kw.setdefault("tribe_id", "")
        kw.setdefault("tax_remitted_usd", "")
        kw.setdefault("statutory_rate", "")
        kw.setdefault("rate_unit", "")
        kw.setdefault("derived_taxable_base", "")
        kw.setdefault("base_unit", "")
        kw.setdefault("rate_source_quote", "")
        kw.setdefault("amount_source_quote", "")
        kw.setdefault("bound_basis", "")
        kw["tax_observation_id"] = f"TTAX-{st}-{self.seq[st]:04d}"
        kw["built_date"] = TODAY

        # A unit with no rate beside it reads as a rate we hold and did not
        # print. The only unit that means something on its own is
        # per_capita_formula, which says the amount is NOT computed from a
        # rate at all - and is therefore the reason such a row can never
        # derive a base.
        if not kw["statutory_rate"] and kw["rate_unit"] != "per_capita_formula":
            kw["rate_unit"] = ""

        assert kw["tax_type"] in TAX_TYPES, kw["tax_type"]
        assert kw["measurement_status"] in MEASUREMENT_STATUSES, \
            kw["measurement_status"]
        # Rule 4: the agreement or statute travels with the row.
        assert kw.get("agreement_or_statute_cite"), \
            f"no cite on {kw['tax_observation_id']}"
        # Two quotes or it does not exist.
        if kw["measurement_status"] == STATUS_DERIVED_BASE:
            assert kw["rate_source_quote"] and kw["amount_source_quote"], \
                f"derived base without two quotes: {kw['tax_observation_id']}"
        if kw["measurement_status"] == STATUS_BOUNDED:
            assert kw["bound_basis"], "a bound must state its basis"
        assert_no_forecast_language(kw)
        self.rows.append({k: kw.get(k, "") for k in FIELDS})


# ---------------------------------------------------------------------------
# WASHINGTON - Department of Licensing, 2024 Tribal Fuel Tax Agreement Report
#
# The richest fuel source in the country for the ROSTER, and a hard stop for
# per-tribe money: RCW 82.38.310 deems tribal fuel information exempt from
# public inspection, so the state holds per-tribe figures it may not publish.
# That is a finding about the statute, not a gap in our coverage, and the
# report says so in as many words - which is why the sentence is quoted onto
# every Washington fuel row.
# ---------------------------------------------------------------------------

WA_COL_BANDS = ((85, 240), (243, 400), (401, 560))


def parse_wa_fuel(src, res, out):
    pages = pdf_lines(RAW / src["path"])
    url = src["url"]

    flat = []
    for pg in pages:
        for b in pg:
            flat.append(band_text(b))
    full = " ".join(flat)
    full = full.replace("\u2019", "'").replace("\ufffd", "-")

    def sentence(pattern):
        m = re.search(pattern, full)
        if not m:
            return ""
        return re.sub(r"\s+", " ", m.group(0)).strip()

    # A sentence terminator is a period NOT inside a number, so "$68.4
    # million." ends once, not twice. Getting this wrong silently truncated
    # both dollar quotes on the first pass.
    END = r"(?:[^.]|\.(?=\d))*\."
    q_rate = sentence(r"DOL refunds 75 percent of the state fuel tax to the "
                      r"tribes" + END)
    if not q_rate:
        q_rate = sentence(r"tribal fuel stations received fuel" + END)
    q_percap = sentence(r"A per capita agreement is a computational formula" + END)
    q_exempt = sentence(r"Information from the tribe or tribal retailers" + END)
    q_refund = sentence(r"The annual refund for the per-capita and 75/25 "
                        r"agreements" + END)
    q_retain = sentence(r"The fuel tax revenue retained by Washington state"
                        + END)
    q_status = sentence(r"DOL is party to " + END)
    cite = "RCW 82.38.310 (fuel tax agreements with federally recognized tribes)"

    # --- roster: three printed columns, bullets at fixed x positions ---
    roster = {"per_capita": [], "75_25": []}
    mode = None
    cols = {i: [] for i in range(3)}
    for pg in pages:
        for b in pg:
            t = band_text(b)
            if re.match(r"^Per Capita Agreements", t):
                mode = "per_capita"
                cols = {i: [] for i in range(3)}
                continue
            if re.match(r"^75/25 Agreements", t):
                # flush per-capita column buffers before switching
                _flush_wa_cols(cols, roster, "per_capita")
                mode = "75_25"
                cols = {i: [] for i in range(3)}
                continue
            if mode and re.match(r"^(New Agreements|U\.S\. Supreme Court|"
                                 r"April 20\d\d)", t):
                _flush_wa_cols(cols, roster, mode)
                mode = None
                continue
            if not mode:
                continue
            for x, word in b[1]:
                ci = None
                for i, (lo, hi) in enumerate(WA_COL_BANDS):
                    if lo <= x <= hi:
                        ci = i
                        break
                if ci is None:
                    continue
                if word in ("\u2022", "-", "\ufffd", "�"):
                    cols[ci].append("|")
                else:
                    cols[ci].append(word)
    if mode:
        _flush_wa_cols(cols, roster, mode)

    for kind, names in roster.items():
        for nm in names:
            tid, canon, tier, how = res.resolve(
                nm, "WA", "WA DOL tribal fuel tax agreement roster 2024")
            out.add(
                tribe_id=tid, tribe_name=canon, state="WA",
                tax_type="MOTOR_FUEL",
                period_start="2024-04-01", period_end="2024-04-30",
                statutory_rate="0.75" if kind == "75_25" else "",
                rate_unit=("share_of_state_tax_collected" if kind == "75_25"
                           else "per_capita_formula"),
                rate_source_quote=(q_rate if kind == "75_25" else q_percap),
                amount_source_quote=q_exempt,
                agreement_or_statute_cite=cite,
                measurement_status=STATUS_ROSTER,
                source_url=url, fetched_date=TODAY, tier=tier,
                confidence=("agreement in force at report date; per-tribe "
                            "amounts are withheld from publication by statute, "
                            "not absent from the record"
                            if tier == "A" else
                            f"held: {how}"))

    # --- the two aggregate figures, CY2023, across all agreements ---
    for label, quote, kind in (
            ("annual refund to tribes", q_refund, "refund"),
            ("state-retained share", q_retain, "retained")):
        m = re.search(r"\$([\d.]+) million", quote or "")
        if not m:
            continue
        out.add(
            tribe_id="", tribe_name="MULTIPLE TRIBES - NOT DISAGGREGATED",
            state="WA", tax_type="MOTOR_FUEL",
            period_start="2023-01-01", period_end="2023-12-31",
            tax_remitted_usd=str(int(float(m.group(1)) * 1_000_000)),
            statutory_rate="0.75" if kind == "refund" else "0.25",
            rate_unit="share_of_state_tax_collected",
            rate_source_quote=q_status or q_rate,
            amount_source_quote=quote,
            agreement_or_statute_cite=cite,
            measurement_status=STATUS_AGGREGATE_AMOUNT,
            source_url=url, fetched_date=TODAY, tier="A",
            confidence=("state total across all fuel tax agreements; the "
                        f"source does not disaggregate by tribe ({label})"))
    # ------------------------------------------------------------------
    # THE ONE DERIVATION THIS DATASET SUPPORTS, AND WHY ONLY THIS ONE.
    #
    # The state-retained figure is stated for a defined population - fuel
    # purchased under the 75/25 agreements - and the agreements fix the state's
    # share at 25 percent. So the fuel tax borne on that fuel is
    # retained / 0.25, and at a per-gallon statutory rate that is a VOLUME.
    #
    #     $22.8M retained / 0.25  = $91.2M of state fuel tax
    #     $91.2M / $0.494 per gal = gallons delivered to tribal stations
    #
    # The $68.4M refund figure is NOT divisible the same way: it pools the two
    # per-capita agreements, whose amount comes from a population formula and
    # not from a quantity of fuel. Dividing it would manufacture gallons that
    # nobody sold. That row stays an aggregate remittance.
    #
    # RATE 1 IN FORCE: the rate is read from RCW 82.38.030 as the cumulative
    # sum of the subsections effective on or before 2023-01-01, because the
    # statute states increments rather than a total.
    # ------------------------------------------------------------------
    rate, rate_quote = wa_fuel_rate_2023()
    if rate and q_retain:
        m = re.search(r"\$([\d.]+) million", q_retain)
        if m:
            retained = float(m.group(1)) * 1_000_000
            tax_on_fuel = retained / 0.25
            gallons, unit = derive_base(tax_on_fuel, rate, "usd_per_gallon")
            out.add(
                tribe_id="", tribe_name="MULTIPLE TRIBES - NOT DISAGGREGATED",
                state="WA", tax_type="MOTOR_FUEL",
                period_start="2023-01-01", period_end="2023-12-31",
                tax_remitted_usd=f"{retained:.2f}",
                statutory_rate=f"{rate:.3f}", rate_unit="usd_per_gallon",
                derived_taxable_base=f"{gallons:.0f}", base_unit=unit,
                rate_source_quote=rate_quote,
                amount_source_quote=q_retain,
                agreement_or_statute_cite=(
                    "RCW 82.38.310 (fuel tax agreements) and RCW 82.38.030 "
                    "(fuel tax rate)"),
                measurement_status=STATUS_DERIVED_BASE,
                source_url=url, fetched_date=TODAY, tier="A",
                confidence=(
                    "volume of fuel delivered to tribally licensed retail "
                    "stations under Washington's 75/25 fuel tax agreements, "
                    "CY2023, across all such agreements. Two steps, both on "
                    "quoted figures: the state retains 25 percent, so state "
                    f"fuel tax borne on this fuel is ${retained:,.0f} / 0.25 = "
                    f"${tax_on_fuel:,.0f}; at ${rate:.3f} per gallon that is "
                    f"{gallons:,.0f} gallons. GALLONS, NOT DOLLARS. The "
                    "per-capita agreements are excluded because the source "
                    "states this figure for 75/25 fuel only"))
    return q_status


def wa_fuel_rate_2023():
    """(rate_usd_per_gallon, quote) for calendar 2023, or (None, '').

    RCW 82.38.030 publishes increments, not a total, so the rate in force is
    the sum of the subsections whose effective date had arrived. Summing them
    is arithmetic on the statute's own words, and the words are quoted onto the
    row so the sum can be checked.
    """
    p = RAW / "wa/rcw_82_38_030_fuel_tax_rate.html"
    if not p.exists():
        return None, ""
    lines = html_text_lines(p)
    WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
             "seven": 7, "eight": 8, "nine": 9, "ten": 10,
             "twenty-three": 23}
    parts, quotes = [], []
    for l in lines:
        if "cents per gallon of fuel is imposed" not in l and \
                "tax at the rate of" not in l:
            continue
        if "special fuel" in l:
            continue
        m_eff = re.search(r"Beginning (?:July|August|January) 1, (\d{4})", l)
        year = int(m_eff.group(1)) if m_eff else 0
        if year > 2022:            # not yet in force during calendar 2023
            continue
        m = re.search(r"rate of ([a-z\- ]+?) cents per gallon", l) or \
            re.search(r"rate of (\d+) cents per gallon", l)
        if not m:
            continue
        txt = m.group(1).strip()
        val = None
        if txt.isdigit():
            val = float(txt)
        else:
            frac = re.match(r"^(.*?) and (?:(one)-half|"
                            r"([a-z\-]+)-tenths)$", txt)
            if frac:
                whole = WORDS.get(frac.group(1).strip())
                if whole is not None:
                    if frac.group(2):
                        val = whole + 0.5
                    else:
                        val = whole + WORDS.get(frac.group(3), 0) / 10.0
            elif txt in WORDS:
                val = float(WORDS[txt])
        if val is None:
            continue
        parts.append(val)
        quotes.append(l.strip())
    if not parts:
        return None, ""
    total_cents = round(sum(parts), 3)
    return (round(total_cents / 100.0, 5),
            f"RCW 82.38.030, subsections in force during calendar 2023, "
            f"summing to {total_cents} cents per gallon: " + " ".join(quotes))


def _flush_wa_cols(cols, roster, mode):
    if not mode:
        return
    for i in sorted(cols):
        blob = " ".join(cols[i])
        for item in blob.split("|"):
            item = re.sub(r"\s+", " ", item).strip(" ,;")
            if len(item) > 4 and re.search(r"[A-Za-z]{4}", item):
                roster[mode].append(item)


# ---------------------------------------------------------------------------
# WASHINGTON - Department of Revenue, tribal retail sales tax compacts.
# A rate with no per-tribe amount: RATE_ONLY_NO_AMOUNT, and it stays that way.
# ---------------------------------------------------------------------------


def parse_wa_sales(src, res, out):
    pages = pdf_lines(RAW / src["path"])
    full = " ".join(band_text(b) for pg in pages for b in pg)
    full = full.replace("\u2019", "'")

    def sentence(pat):
        m = re.search(pat, full)
        return re.sub(r"\s+", " ", m.group(0)).strip() if m else ""

    END = r"(?:[^.]|\.(?=\d))*\."
    q_rate = sentence(r"Compacting Tribes receive 100% of certain state "
                      r"B&O taxes" + END)
    q_share = sentence(r"A Tribe that has completed their qualified capital "
                       r"investment" + END)
    q_amt = sentence(r"To date, Tribal qualified capital investment "
                     r"contributions total" + END)
    if not (q_rate and q_share):
        return
    out.add(
        tribe_id="", tribe_name="MULTIPLE TRIBES - NOT DISAGGREGATED",
        state="WA", tax_type="RETAIL_SALES",
        period_start="", period_end="",
        statutory_rate="0.50-0.60",
        rate_unit="share_of_state_tax_collected",
        rate_source_quote=q_share,
        amount_source_quote=q_amt,
        agreement_or_statute_cite=(
            "Washington tribal retail sales tax compacts negotiated under "
            "gubernatorial authority; Department of Revenue agency request "
            "legislation, 2025"),
        measurement_status=STATUS_RATE_ONLY,
        source_url=src["url"], fetched_date=TODAY, tier="A",
        confidence=("compact share of state retail sales and use tax above the "
                    "first $500,000; the source publishes no per-tribe "
                    "distribution"))


# ---------------------------------------------------------------------------
# MONTANA - Department of Revenue Biennial Report, Other Taxes chapter.
#
# Two tables carry a line for tribal revenue-sharing agreements. Both are read
# by word position and both are CHECKED AGAINST THE PRINTED TOTAL: the tribal
# line plus the remainder must equal total revenue, or the column is reported
# and not published.
#
# The tribal line is a SHARE OF TAX REVENUE, not a rate on a quantity, so no
# gallon or pack base comes out of it. `derive_base` refuses it by design.
# ---------------------------------------------------------------------------

MT_TABLES = [
    dict(anchor="Table 5.8 Distribution of Cigarette Tax", tax_type="TOBACCO",
         label="cigarette tax", concept="cigarette tax revenue sharing"),
    dict(anchor="Table 5.37 Distribution of Tobacco Products Tax",
         tax_type="TOBACCO", label="tobacco products tax",
         concept="tobacco products tax revenue sharing"),
]


def parse_mt(src, res, out, log):
    pages = pdf_lines(RAW / src["path"])
    url = src["url"]
    full = " ".join(band_text(b) for pg in pages for b in pg)

    def sentence(pat):
        m = re.search(pat, full)
        return re.sub(r"\s+", " ", m.group(0)).strip() if m else ""

    q_rate = sentence(r"These agreements provide for a refund of the tax on a "
                      r"fixed number of cigarettes[^.]*\.")
    q_ctx = sentence(r"Under federal law, tribal governments reserve the right "
                     r"to tax cigarettes[^.]*\.")

    for spec in MT_TABLES:
        page = None
        for pg in pages:
            if any(band_text(b).startswith(spec["anchor"][:18])
                   and spec["anchor"][-12:] in band_text(b) for b in pg):
                page = pg
                break
        if page is None:
            log.append(f"MT: table not found - {spec['anchor']}")
            continue

        years, totals, tribal, remainder = [], [], [], []
        for b in page:
            t = band_text(b)
            if re.search(r"FY 20\d\d FY 20\d\d", t) and not years:
                years = re.findall(r"FY (20\d\d)", t)
            if t.startswith("Total Revenue"):
                totals = [money(x) for x in re.findall(r"\$[\d,]+", t)]
            if t.startswith("Agreement $") or re.match(
                    r"^Tribal Agreement \$", t):
                tribal = [money(x) for x in re.findall(r"\$[\d,]+", t)]
            if t.startswith("Remainder"):
                remainder = [money(x) for x in re.findall(r"\$[\d,]+", t)]

        if not (years and totals and tribal and remainder):
            log.append(f"MT: incomplete table - {spec['anchor']}")
            continue
        if not (len(years) == len(totals) == len(tribal) == len(remainder)):
            log.append(f"MT: column count mismatch - {spec['anchor']}")
            continue
        # FOOTING CHECK. A column that does not foot is reported, not published.
        bad = [i for i in range(len(years))
               if abs(totals[i] - tribal[i] - remainder[i]) > 1.0]
        if bad:
            log.append(f"MT: {spec['anchor']} failed footing on FY "
                       f"{[years[i] for i in bad]} - NOT PUBLISHED")
            continue
        log.append(f"MT: {spec['anchor']} foots on all {len(years)} years")

        amt_quote = (f"{spec['anchor']} - Tobacco and Cig. Tribal Agreement: "
                     + "; ".join(f"FY {years[i]} ${tribal[i]:,.0f}"
                                 for i in range(len(years))))
        for i, y in enumerate(years):
            out.add(
                tribe_id="", tribe_name="MULTIPLE TRIBES - NOT DISAGGREGATED",
                state="MT", tax_type=spec["tax_type"],
                period_start=f"{int(y)-1}-07-01", period_end=f"{y}-06-30",
                tax_remitted_usd=f"{tribal[i]:.2f}",
                statutory_rate="", rate_unit="share_of_state_tax_collected",
                rate_source_quote=q_rate or q_ctx,
                amount_source_quote=amt_quote,
                agreement_or_statute_cite=(
                    "Montana state-tribal cigarette and tobacco products tax "
                    "revenue-sharing agreements; 16-11-119, MCA"),
                measurement_status=STATUS_AGGREGATE_AMOUNT,
                source_url=url, fetched_date=TODAY, tier="A",
                confidence=(f"{spec['concept']} distributed to tribes, state "
                            "total; the source does not disaggregate by tribe. "
                            "Column checked against the printed total"))


# ---------------------------------------------------------------------------
# OKLAHOMA - Tax Commission FY2025 Revenue & Apportionment Report.
#
# The statutory apportionment summary prints one line per receiving fund with
# the current and prior fiscal year beside it. "To Participating Tribes" is the
# motor fuel apportionment; the tobacco lines sit in the same table.
#
# Read linearly this report says $70,341,313.12 of diesel excise went to
# tribes. Read by position the apportionment total is $26,120,361.46. The
# first figure is a text-layer artefact; only the positional read is used.
# ---------------------------------------------------------------------------

# ONLY the apportionment table is used, and the reason is worth recording.
#
# Three other tables in this report carry a tribal line and all three were
# REFUSED after inspection:
#
#   SOURCE OF REVENUE (alphabetical, two label columns and two value columns)
#       - a band groups a label from the LEFT column with values belonging to
#         the RIGHT column's row. It reads "State / Tribal Compact Stamps
#         $63,889,121.46" and "Use Tax $63,889,121.46" from the same numbers.
#   "Where it came from / Where it went" fund pages
#       - two independent two-column tables share a baseline, so a "To
#         Participating Tribes" figure cannot be tied to the tax named at the
#         top of the page.
#   1695T Tribal Trust Account / Tribal License Plate
#       - values are not adjacent to the label, and the license-plate line does
#         not state the direction of the flow. Rule 4 forbids publishing a bare
#         tribal number whose direction is unstated.
#
# The apportionment table is different: the label sits alone on its band and
# the two fiscal-year values sit alone on the next one. That is checkable, and
# it is checked.
OK_LINES = [
    dict(label="To Participating Tribes", tax_type="MOTOR_FUEL",
         cite=("Oklahoma Tax Commission, Apportionment of Statutory Revenues, "
               "'To Participating Tribes'; state-tribal motor fuel tax "
               "compacts"),
         note="apportioned to participating tribes"),
]


def parse_ok(src, res, out, log):
    pages = pdf_lines(RAW / src["path"])
    url = src["url"]
    found = 0

    # STRUCTURAL evidence, not numeric: which tax sections contain the line.
    # This is safe where the numbers on those pages are not, because it asks
    # which heading a label appears under, never which figure sits beside it.
    sections = []
    for pg in pages:
        head = " ".join(band_text(b) for b in pg[:2])
        if "Where it came from" not in head:
            continue
        if not any("To Participating Tribes" in band_text(b) for b in pg):
            continue
        m = re.search(r"Where it came from Where it went ([A-Z][A-Za-z /&]+?) "
                      r"(?:Collections|Tax Collections)", head)
        if m:
            sections.append(m.group(1).strip())
    sect_note = ("; the same line appears under the following tax sections of "
                 "this report: " + ", ".join(sorted(set(sections)))
                 if sections else "")

    for pg in pages:
        head = " ".join(band_text(b) for b in pg[:3])
        m = re.search(r"Apportionment of Statutory Revenues\s+(20\d\d)\s+(20\d\d)",
                      head)
        if not m:
            continue
        y_cur, y_prev = m.group(1), m.group(2)
        for i, b in enumerate(pg):
            t = band_text(b).strip()
            for spec in OK_LINES:
                if t != spec["label"]:
                    continue
                # values print on the NEXT band, right-aligned in two columns
                nxt = band_text(pg[i + 1]) if i + 1 < len(pg) else ""
                vals = re.findall(r"\$[\d,]+\.\d\d", nxt)
                if len(vals) != 2:
                    log.append(f"OK: '{spec['label']}' had "
                               f"{len(vals)} adjacent values, refused")
                    continue
                found += 1
                quote = f"{spec['label']} {vals[0]} {vals[1]}"
                for y, v in ((y_cur, vals[0]), (y_prev, vals[1])):
                    out.add(
                        tribe_id="",
                        tribe_name="MULTIPLE TRIBES - NOT DISAGGREGATED",
                        state="OK", tax_type=spec["tax_type"],
                        period_start=f"{int(y)-1}-07-01",
                        period_end=f"{y}-06-30",
                        tax_remitted_usd=f"{money(v):.2f}",
                        rate_unit="share_of_state_tax_collected",
                        rate_source_quote=(
                            f"Apportionment of Statutory Revenues {y_cur} "
                            f"{y_prev}"),
                        amount_source_quote=quote,
                        agreement_or_statute_cite=spec["cite"],
                        measurement_status=STATUS_AGGREGATE_AMOUNT,
                        source_url=url, fetched_date=TODAY, tier="A",
                        confidence=(f"{spec['note']}, state total; the source "
                                    "does not disaggregate by tribe. Read by "
                                    "word position, not from the text layer"
                                    + sect_note))
    log.append(f"OK: {found} apportionment lines matched positionally; the "
               "SOURCE OF REVENUE and 'Where it came from' tables were "
               "inspected and refused (label/value alignment not verifiable)")


# ---------------------------------------------------------------------------
# NEW MEXICO - Cigarette Tax Credit Stamp Listing.
#
# Per-tribe eligibility under a QUALIFYING TRIBAL CIGARETTE TAX, which means
# the tribe itself levies the tax. The state names the tribes and cites the
# statute; it publishes no amounts here.
# ---------------------------------------------------------------------------


def parse_nm(src, res, out, log):
    lines = html_text_lines(RAW / src["path"])
    try:
        anchor = next(i for i, l in enumerate(lines)
                      if l.startswith("The following Tribes, Pueblos and "
                                      "Nations are eligible"))
    except StopIteration:
        log.append("NM: eligibility list anchor not found")
        return
    q_rate = next((l for l in lines if "qualifying tribal cigarette tax" in l),
                  "")
    q_list = lines[anchor]

    names = []
    for l in lines[anchor + 1:]:
        if len(l) > 70 or not re.search(
                r"(Tribe|Pueblo|Nation|Owingeh|Apache|Navajo|Center)", l):
            if names:
                break
            continue
        names.append(l)
    log.append(f"NM: {len(names)} eligible tribes/pueblos listed")

    for nm in names:
        tid, canon, tier, how = res.resolve(
            nm, "NM", "NM cigarette tax credit stamp eligibility listing")
        out.add(
            tribe_id=tid, tribe_name=canon, state="NM", tax_type="TOBACCO",
            period_start="", period_end="",
            rate_unit="usd_per_pack_of_20",
            rate_source_quote=q_rate,
            amount_source_quote=q_list,
            agreement_or_statute_cite=(
                "Section 7-12-2 NMSA 1978 (qualifying tribal cigarette tax); "
                "New Mexico cigarette tax credit stamp"),
            measurement_status=STATUS_ROSTER,
            source_url=src["url"], fetched_date=TODAY, tier=tier,
            confidence=("tribe levies a cigarette tax the department has "
                        "determined is a qualifying tribal cigarette tax; the "
                        "listing carries no volumes or amounts"
                        if tier == "A" else f"held: {how}"))


# ---------------------------------------------------------------------------
# MICHIGAN - per-tribe tax agreement pages.
#
# One page per tribe listing the agreement and every amendment with its
# effective date. That is the citable instrument rule 4 demands; it carries no
# amounts, so the row is a roster row and says so.
# ---------------------------------------------------------------------------

MI_AGREEMENT_RE = re.compile(
    r"^(?P<title>(?:First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|"
    r"Tenth)?\s*(?:Amendment to (?:the )?)?Tax Agreement Between (?:the )?"
    r"(?P<tribe>.+?) and the State of Michigan)\s*"
    r"\((?:implemented|effective) (?P<eff>\d{1,2}/\d{1,2}/\d{2,4})\)")


def parse_mi(src, res, out, log):
    lines = html_text_lines(RAW / src["path"])
    agreements = []
    for l in lines:
        m = MI_AGREEMENT_RE.match(l)
        if m:
            agreements.append((m.group("tribe").strip(),
                               m.group("eff"), l.strip()))
    if not agreements:
        log.append(f"MI: no agreement lines on {src['path']}")
        return

    # THE SOURCE DISAGREES WITH ITSELF AND THAT IS A FINDING, NOT A BUG TO
    # SMOOTH OVER. Michigan's own page titles the Sixth Amendment "...Between
    # the Traverse Bay Bands of Odawa Indians", dropping "Little" from a name
    # its five earlier instruments spell in full. Taking the first or the
    # newest title would have carried the state's typo into our entity
    # resolution; the name every instrument agrees on wins, and the
    # disagreement is logged rather than silently corrected.
    from collections import Counter
    counts = Counter(a[0] for a in agreements)
    tribe_name, _ = counts.most_common(1)[0]
    if len(counts) > 1:
        log.append(f"MI: {src['path']} spells the tribe "
                   f"{len(counts)} ways across its own instruments "
                   f"({dict(counts)}); used the majority spelling")

    def key(a):
        mm, dd, yy = a[1].split("/")
        yy = int(yy)
        return (yy + 2000 if yy < 100 else yy, int(mm), int(dd))
    newest = max(agreements, key=key)
    original = min(agreements, key=key)

    tid, canon, tier, how = res.resolve(
        tribe_name, "MI", "MI Treasury state-tribal tax agreement page")
    y, m_, d = newest[1].split("/")[2], newest[1].split("/")[0], \
        newest[1].split("/")[1]
    out.add(
        tribe_id=tid, tribe_name=canon, state="MI", tax_type="OTHER",
        period_start=f"{y}-{int(m_):02d}-{int(d):02d}", period_end="",
        rate_source_quote=original[2],
        amount_source_quote=newest[2],
        agreement_or_statute_cite=newest[2],
        measurement_status=STATUS_ROSTER,
        source_url=src["url"], fetched_date=TODAY, tier=tier,
        confidence=(f"state-tribal tax agreement in force; {len(agreements)} "
                    "instruments published (original plus amendments). "
                    "Michigan publishes the agreements, not the amounts "
                    "remitted under them"
                    if tier == "A" else f"held: {how}"))


# ---------------------------------------------------------------------------
# Netting readiness. Rule 2 lives here: this counts where a subtraction COULD
# run, and never performs one that the evidence does not support.
# ---------------------------------------------------------------------------


def netting_readiness(rows):
    """Tribes carrying at least one per-tribe AMOUNT in a non-gaming category.

    Only a per-tribe amount can be netted out of a whole-tribe revenue figure.
    A roster row proves an agreement exists and subtracts nothing.
    """
    by_tribe = {}
    for r in rows:
        if not r["tribe_id"]:
            continue
        if r["measurement_status"] not in (STATUS_PER_TRIBE_AMOUNT,
                                           STATUS_DERIVED_BASE):
            continue
        by_tribe.setdefault(r["tribe_id"], set()).add(r["tax_type"])
    return by_tribe


# ---------------------------------------------------------------------------


def read_csv(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as fh:
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
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {p.relative_to(CEDAR)}  ({len(rows):,} rows)")


CODEBOOK = [
    ("tax_observation_id", "text", "code",
     "Identifier, TTAX-<state>-<n>."),
    ("tribe_id", "text", "code",
     "Cedar entity spine id. Empty where the source reports a state total "
     "across tribes or where resolution was refused."),
    ("tribe_name", "text", "",
     "Entity name. 'MULTIPLE TRIBES - NOT DISAGGREGATED' on a state total."),
    ("state", "text", "USPS", "State whose revenue department published the record."),
    ("tax_type", "text", "",
     "One of: MOTOR_FUEL, TOBACCO, TRANSIENT_OCCUPANCY, ALCOHOL, "
     "RETAIL_SALES, SEVERANCE, OTHER."),
    ("period_start", "date", "YYYY-MM-DD", "First day of the period the row covers."),
    ("period_end", "date", "YYYY-MM-DD", "Last day of the period the row covers."),
    ("tax_remitted_usd", "numeric", "USD",
     "Dollar amount the source states for this row."),
    ("statutory_rate", "numeric", "see rate_unit",
     "Rate the source publishes. Read with rate_unit; never a bare number."),
    ("rate_unit", "text", "",
     "What the rate is levied on: usd_per_gallon, usd_per_pack_of_20, "
     "usd_per_ounce, share_of_wholesale_price, share_of_retail_price, "
     "share_of_state_tax_collected, share_of_gross_receipts, "
     "per_capita_formula."),
    ("derived_taxable_base", "numeric", "see base_unit",
     "Amount divided by rate. Populated only where both are quoted for the "
     "same period and the rate is levied on a quantity."),
    ("base_unit", "text", "",
     "Unit of derived_taxable_base: gallons, packs_of_20, ounces or usd. A "
     "volume is never a dollar figure."),
    ("rate_source_quote", "text", "", "Verbatim rate language from the source."),
    ("amount_source_quote", "text", "",
     "Verbatim language establishing the amount. On a roster row, which "
     "carries no amount, this holds the verbatim language that places the row "
     "in the record - and in Washington, the statutory reason no per-tribe "
     "amount is published."),
    ("agreement_or_statute_cite", "text", "",
     "The agreement or statute the row rests on. Required on every row."),
    ("measurement_status", "text", "",
     "REPORTED_TAX_REMITTANCE_PER_TRIBE, "
     "REPORTED_TAX_REMITTANCE_MULTI_TRIBE_AGGREGATE, "
     "AGREEMENT_ROSTER_NO_AMOUNT, RATE_ONLY_NO_AMOUNT, DERIVED_TAXABLE_BASE, "
     "BOUNDED_DERIVED_REVENUE."),
    ("bound_basis", "text", "",
     "Populated only on a bound; states what makes it a bound."),
    ("source_url", "text", "URL", "Document retrieved."),
    ("fetched_date", "date", "YYYY-MM-DD", "Date the document was retrieved."),
    ("tier", "text", "", "A publishes; B is internal only."),
    ("confidence", "text", "", "What the row does and does not establish."),
    ("built_date", "date", "YYYY-MM-DD", "Build date."),
]


def write_codebook(n_rows, rows):
    p = CLEAN / "codebook_master.csv"
    existing = read_csv(p)
    if not existing:
        print("  codebook_master.csv missing; skipped")
        return
    fields = list(existing[0].keys())
    keep = [r for r in existing if r.get("dataset") != "15_tribal_tax"]
    filled = {}
    for var, *_ in CODEBOOK:
        filled[var] = sum(1 for r in rows if str(r.get(var, "")).strip())
    for var, typ, units, desc in CODEBOOK:
        keep.append({
            "dataset": "15_tribal_tax", "variable": var, "type": typ,
            "units": units,
            "pct_filled": f"{100.0*filled[var]/max(n_rows,1):.1f}",
            "n_rows": str(n_rows), "published": "1", "access_tier": "public",
            "description": desc, "generated": TODAY,
        })
    bak = p.with_suffix(f".csv.bak_{TODAY}_pre108")
    if not bak.exists():
        bak.write_bytes(p.read_bytes())
    write_csv(p, keep, fields)


def do_build():
    print("=== 108 build ===")
    man = {r["key"]: r for r in read_csv(RAW / "_SOURCE_MANIFEST.csv")}
    spine = read_csv(SPINE / "cedar_entity_spine.csv")
    print(f"spine entities: {len(spine):,}")
    res = Resolver(spine)
    out = Rows()
    log = []

    for src in SOURCES:
        rec = man.get(src["key"])
        if not rec or not int(rec.get("usable") or 0):
            log.append(f"{src['state']}: source unusable, skipped "
                       f"({src['key']})")
            continue
        try:
            if src["key"] == "wa_dol_fuel_2024":
                parse_wa_fuel(src, res, out)
            elif src["key"] == "wa_dor_sales_compact":
                parse_wa_sales(src, res, out)
            elif src["key"] == "mt_biennial_other_taxes":
                parse_mt(src, res, out, log)
            elif src["key"] == "ok_otc_ar2025":
                parse_ok(src, res, out, log)
            elif src["key"] == "nm_cig_stamp_listing":
                parse_nm(src, res, out, log)
            elif src["key"].startswith("mi_agreement_"):
                parse_mi(src, res, out, log)
        except Exception as exc:                       # noqa: BLE001
            log.append(f"{src['state']}: parser error {src['key']}: {exc}")
            print(f"  ! {src['key']}: {exc}")

    rows = out.rows
    write_csv(CLEAN / "tribal_tax_bases.csv", rows, FIELDS)
    write_csv(REVIEW / f"tribal_tax_unresolved_{TODAY}.csv", res.unresolved,
              ["source_name", "state", "context", "reason",
               "resolved_tribe_id", "staged_date"])
    write_codebook(len(rows), rows)

    ready = netting_readiness(rows)
    summary = dict(
        rows=len(rows),
        by_state={}, by_tax_type={}, by_status={},
        tribes_reached=len({r["tribe_id"] for r in rows if r["tribe_id"]}),
        rows_with_rate_and_amount=sum(
            1 for r in rows if r["statutory_rate"] and r["tax_remitted_usd"]),
        rows_with_derived_base=sum(1 for r in rows if r["derived_taxable_base"]),
        unresolved=len(res.unresolved),
        netting_ready_tribes=len(ready),
        log=log,
    )
    for r in rows:
        summary["by_state"][r["state"]] = summary["by_state"].get(r["state"], 0) + 1
        summary["by_tax_type"][r["tax_type"]] = \
            summary["by_tax_type"].get(r["tax_type"], 0) + 1
        summary["by_status"][r["measurement_status"]] = \
            summary["by_status"].get(r["measurement_status"], 0) + 1
    (CLEAN / "_108_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps({k: v for k, v in summary.items() if k != "log"},
                     indent=2))
    for l in log:
        print("  log:", l)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("fetch", "all"):
        do_fetch()
    if mode in ("build", "all"):
        do_build()


if __name__ == "__main__":
    main()
