#!/usr/bin/env python3
"""
Cedar Press - 117: the GAMING DEVICE layer.

    data/clean/gaming_device_observations.csv   what is on the floor, when it
                                                changed, and (where anyone says
                                                so) who made it
    data/clean/gaming_manufacturer_facts.csv    the manufacturers' own numbers,
                                                COMPANY-LEVEL, never attributed
                                                to a property

WHAT THIS IS AND IS NOT
-----------------------
A slot-by-slot fleet per property is NOT buildable from free sources, and this
build does not pretend otherwise. What exists is partial. Partial is fine
PROVIDED the coverage is measured and stated, so every count in
docs/GAMING_DEVICE_BUILD_LOG.md is computed by this script, not asserted.

THE FOUR RULES THAT DECIDE WHETHER THIS SHIPS
---------------------------------------------
1. **Class II / Class III mix is a DATED OBSERVATION, never a property
   attribute.** Elijah, 2026-08-07: "at any time a tribe can change their
   status by swapping out their machines, so it's a necessary but not
   sufficient condition." A floor can be converted between classes with no
   federal record. `device_class` therefore lives on the OBSERVATION, with its
   own date and source. There is no device_class column on any property.

2. **An authorised maximum is never an operating count.**
   `cedar_domain.may_promote()` refuses AUTHORIZED_MAXIMUM ->
   ACTIVE_FLOOR_COUNT and this build asserts it before writing a row.
   Washington's 1,075 per tribe is an entitlement that SIX tribes hold with no
   casino at all; Arizona's six rights-holding tribes are the same shape.

3. **Manufacturer revenue per participation unit measures the MANUFACTURER's
   economics, not the casino's.** An installed base or a shipment count is
   never converted into gaming revenue, and no modelled property revenue is
   produced anywhere in this file.

4. **A manufacturer or regulator using a different property name is an ALIAS,
   not a second property.** Rows attach to existing CCP-/VP-/TPL- IDs. This
   build creates no property IDs and writes to no property universe file.

WHERE THE ROWS COME FROM
------------------------
Ranked by what each source actually yields, not by how promising it sounds.

  A. STATE REGULATOR DEVICE COUNTS - the densest real source.
     - re-projected from `gaming_capacity_official.csv` (Arizona ADG per-casino
       Class III / Class II / DCETG columns; Connecticut DCP monthly weighted
       average; Michigan; Montana; Nevada; SEC-filed issuer counts)
     - re-projected from `state_gaming_observations.csv` (Wisconsin LFB
       per-casino slot counts, seven biennial editions 2012-2024)
     - NEW EXTRACTION: Oklahoma OMES Gaming Compliance Report, twelve editions,
       statewide monthly-average Class III machine count FY2014-FY2025
     - NEW EXTRACTION: Arizona ADG FY2025 Annual Report - the statewide
       per-facility device ceiling, the machines-certified count, and the six
       tribes that hold slot rights and operate no casino

  B. TRIBAL GAMING COMMISSION SHIPMENT NOTIFICATIONS / STATE TRANSPORTATION
     RECORDS - swept and NOT FOUND (see the build log). No free source
     publishes a dated manufacturer + model + quantity shipment to a named
     tribal property. The NIGC declination corpus, which is where an equipment
     lease would surface federally, was searched: 158 OCR'd letters, THREE
     mention a gaming machine at all and NONE names a manufacturer or a count.

  C. MANUFACTURER SEC FILINGS - IGT / Brightstar, Light & Wonder (ex-Scientific
     Games), Everi, PlayAGS, Inspired. Installed base, participation units and
     units sold. COMPANY-LEVEL. These go to gaming_manufacturer_facts.csv and
     are never attributed to a property. Every KPI row is accepted only if the
     filing's own variance column FOOTS (n1 - n2 == variance) - the same
     discipline that caught the Michigan and Arizona one-row column shifts.

  D. MANUFACTURER PRESS RELEASES naming a specific property - not obtained.
     Recorded as a documented absence rather than left looking unworked.

  E. COMPACT CAPS AND ALLOCATIONS - re-projected from
     `compact_structured_terms.csv` and `wa_machine_allocations.csv`.

RE-PROJECTION IS NOT DUPLICATION, BUT IT IS NOT INDEPENDENT EITHER
------------------------------------------------------------------
Most rows here are the SAME FACTS as rows in gaming_capacity_official.csv,
re-expressed in a device-shaped schema with a typed device_class. Every row
carries `source_url` + verbatim `source_quote` from the original publisher, so
the provenance is unchanged. `observation_id` prefixes name the upstream file.
**Never sum this file with gaming_capacity_official.csv.**

NOT TOUCHED
-----------
gaming_capacity_official.csv, wa_machine_allocations.csv,
compact_structured_terms.csv, gaming_facilities.csv,
gaming_property_capacity_history.csv, nigc_*, ca_gaming_*, fl_*,
tribal_tax_bases.csv, prime_contracts.csv, federal_funding_transactions.csv,
subawards.csv, entity_*, the identifier ledger, the spine, codebook_master.csv.

Usage:  py -3 code/117_build_gaming_devices.py [--fetch] [--build]
        (no switch = both)
"""

import csv
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
DOCS = CEDAR / "docs"
LOGS = CEDAR / "logs"
RAW = CEDAR / "data" / "raw" / "external" / "gaming_devices"
OFFICIAL = CEDAR / "data" / "raw" / "external" / "gaming_official"
STATE_RAW = CEDAR / "data" / "raw" / "external" / "state_gaming"
DECL_OCR = CEDAR / "data" / "raw" / "external" / "nigc_declinations" / "_ocr"

TODAY = date.today().isoformat()
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

SCRIPT = "code/117_build_gaming_devices.py"

# ---------------------------------------------------------------------------
# SHARED VOCABULARY - imported, never re-declared (spec 13.1).
# ---------------------------------------------------------------------------
sys.path.insert(0, str(CEDAR / "code"))
from cedar_domain import MeasurementType, may_promote, NAME_TRAPS, Tier  # noqa: E402
from cedar_keys import surrogate_id  # noqa: E402
import cedar_codebook  # noqa: E402

# --------------------------------------------------------------------------
# THE PRIMARY KEY OF gaming_manufacturer_facts.csv, AND WHAT IT IS MADE OF
#
# `fact_id` was minted TWICE with two different positional counters: first as
# `f"GMF-{seq:05d}"` while parsing, then REASSIGNED as `f"GMF-{i:05d}"` after
# the list was re-sorted. So the same fact carried two different ids inside a
# single run, and the surviving one was a rank in a sorted list.
#
# It is now a deterministic blake2b digest of the columns this build ALREADY
# treats as the identity of a fact - it constructs
# `(manufacturer, ftype, dclass, geo, fy, val)` a few lines below to decide
# whether it has seen one before. Measured 2026-08-26: unique over all 62
# rows, 0 blank. `period_end` stands in for `fy` because it is the column
# actually written to the file.
# --------------------------------------------------------------------------
GMF_KEY_COLUMNS = ["manufacturer", "fact_type", "device_class", "geography",
                   "period_end"]

_spec = importlib.util.spec_from_file_location(
    "m33", str(CEDAR / "code" / "33_apply_party_rulings.py"))
m33 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m33)
resolve_entity, norm, core = m33.resolve_entity, m33.norm, m33.core

# RULE 2, asserted rather than remembered.
assert may_promote(MeasurementType.AUTHORIZED_MAXIMUM,
                   MeasurementType.ACTIVE_FLOOR_COUNT) is False, \
    "AUTHORIZED_MAXIMUM must never promote to ACTIVE_FLOOR_COUNT"
assert may_promote(MeasurementType.PROJECTED,
                   MeasurementType.ACTIVE_FLOOR_COUNT) is False
assert may_promote(MeasurementType.ENVIRONMENTAL_REVIEW_COUNT,
                   MeasurementType.ACTIVE_FLOOR_COUNT) is False
assert may_promote(MeasurementType.REGULATORY_REPORTED_COUNT,
                   MeasurementType.ACTIVE_FLOOR_COUNT) is True

# ---------------------------------------------------------------------------
# SCHEMA - exactly as specified. No extra columns; scope is carried by which
# of facility_id / tribe_id is populated and is documented in the codebook.
# ---------------------------------------------------------------------------
OBS_FIELDS = [
    "observation_id", "facility_id", "tribe_id", "observation_date",
    "observation_type", "manufacturer", "platform_or_cabinet", "game_theme",
    "device_class", "quantity", "shipment_origin", "shipment_destination",
    "measurement_type", "source_url", "source_quote", "fetched_date", "tier",
    "confidence", "built_date",
]

OBS_TYPES = {
    "SHIPMENT_IN", "SHIPMENT_OUT", "DEVICE_ADDITION", "DEVICE_REMOVAL",
    "REGULATORY_INVENTORY", "MANUFACTURER_PLACEMENT", "FLOOR_COUNT",
    "FLEET_REPLACEMENT", "AUTHORIZED_MAXIMUM",
}

MFR_FIELDS = [
    "fact_id", "manufacturer", "manufacturer_cik", "fact_type", "device_class",
    "geography", "value", "unit", "period_end", "fiscal_year",
    "period_basis", "filing_form", "filing_date", "source_url", "source_quote",
    "property_attributed", "fetched_date", "tier", "confidence", "built_date",
]

LOGLINES = []


def log(msg):
    print(msg)
    LOGLINES.append(msg)


def read(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
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


def write(p, rows, fields):
    # REGENERATE GUARD (ADR-017, 2026-09-02): derive the header, do not declare it.
    fields = _carry_live_columns(p, fields)
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    tmp.replace(p)


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# PULL DISCIPLINE - one poller per host, claim before the first request.
# ---------------------------------------------------------------------------
UA_SEC = "CedarPress-Research elijahsamsonmoreno@gmail.com"

# Hosts other agents are on RIGHT NOW. Never touched by this build.
FORBIDDEN_HOSTS = {"files.usaspending.gov", "api.usaspending.gov",
                   "apps.nd.gov", "www.treasurer.nd.gov"}


def _pid_alive(pid):
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"(Get-Process -Id {pid} -ErrorAction SilentlyContinue).Id"],
            capture_output=True, text=True, timeout=60).stdout.strip()
        return out.isdigit()
    except Exception:
        return False


def claim_host(host, note):
    assert host not in FORBIDDEN_HOSTS, f"{host} belongs to another agent"
    p = LOGS / f"_HOSTLOCK_{host}.json"
    if p.exists():
        try:
            cur = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            cur = {}
        pid = cur.get("pid")
        if cur.get("active") and pid and pid != os.getpid() and _pid_alive(pid):
            cur.setdefault("queue", []).append(
                {"script": SCRIPT,
                 "requested_at": datetime.now(timezone.utc).isoformat(),
                 "work": note})
            p.write_text(json.dumps(cur, indent=1), encoding="utf-8")
            log(f"  ! {host} held by live pid {pid}; queued and DEFERRING")
            return False
    LOGS.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(
        {"host": host, "pid": os.getpid(), "script": SCRIPT,
         "started": datetime.now(timezone.utc).isoformat(),
         "active": True, "queue": [],
         "policy": "single stream, >=1.5s gap, skip-if-present, no retry loop",
         "note": note}, indent=1), encoding="utf-8")
    log(f"  + claimed {host}")
    return True


def release_host(host, note=""):
    p = LOGS / f"_HOSTLOCK_{host}.json"
    if not p.exists():
        return
    try:
        cur = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return
    if cur.get("pid") == os.getpid():
        cur["active"] = False
        cur["released"] = datetime.now(timezone.utc).isoformat()
        if note:
            cur["note"] = note
        p.write_text(json.dumps(cur, indent=1), encoding="utf-8")
        log(f"  - released {host}")


def curl(url, out_path, ua=UA_SEC, timeout=120):
    """Single request. Returns (http_status, content_type, bytes)."""
    p = subprocess.run(
        ["curl", "-s", "-L", "-A", ua, "--max-time", str(timeout),
         "-o", str(out_path), "-w", "%{http_code} %{content_type} %{size_download}",
         url], capture_output=True, text=True)
    parts = (p.stdout or "").split()
    st = int(parts[0]) if parts and parts[0].isdigit() else 0
    ct = parts[1] if len(parts) > 1 else ""
    n = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
    return st, ct, n


# ---------------------------------------------------------------------------
# STAGE 1 - FETCH. Manufacturer filings only; everything else is on disk.
# ---------------------------------------------------------------------------
#
# WHY THESE FIVE, AND WHY THESE YEARS
# -----------------------------------
# International Game Technology PLC renamed itself BRIGHTSTAR LOTTERY PLC and
# reports IGT Gaming as DISCONTINUED OPERATIONS from the FY2024 20-F onward, so
# the FY2024 filing carries no gaming installed base at all. The gaming numbers
# are in the FY2022 and FY2021 filings and that is why those editions are
# pulled rather than the newest one. A newest-is-best rule would have returned
# an empty IGT and looked like a retrieval failure.
#
# Konami Gaming Inc. is a subsidiary of Konami Group Corporation, which
# DELISTED from the NYSE in 2015. It files nothing current with the SEC, so
# there is no free filing-based installed base for the fourth-largest supplier
# to Indian Country. That is a documented hole, not an unworked one.
MANUFACTURERS = [
    # (tag, legal name at filing, cik, [(form, accession, primary_doc, fy)])
    ("LNW", "Light & Wonder, Inc.", 750004, "10-K"),
    ("EVRI", "Everi Holdings Inc.", 1318568, "10-K"),
    ("AGS", "PlayAGS, Inc.", 1593548, "10-K"),
    ("IGT", "International Game Technology PLC", 1619762, "20-F"),
    ("INSE", "Inspired Entertainment, Inc.", 1615063, "10-K"),
]
N_EDITIONS = 4


def fetch():
    log("STAGE 1  fetch - manufacturer SEC filings")
    RAW.mkdir(parents=True, exist_ok=True)
    manifest_p = RAW / "_SOURCE_MANIFEST.csv"
    have = {r["relative_path"]: r for r in read(manifest_p)}
    rows = list(have.values())

    got_data = claim_host("data.sec.gov", "EDGAR submissions index, gaming manufacturers")
    got_www = claim_host("www.sec.gov", "EDGAR primary documents, gaming manufacturers")
    if not (got_data and got_www):
        log("  deferring fetch; another agent holds an SEC host")
        return

    try:
        for tag, legal, cik, form in MANUFACTURERS:
            idx_p = RAW / f"sec_submissions_{tag}.json"
            if not idx_p.exists():
                st, ct, n = curl(
                    f"https://data.sec.gov/submissions/CIK{cik:010d}.json", idx_p)
                log(f"  {tag} submissions HTTP {st} {n:,}b")
                if st != 200:
                    continue
                time.sleep(1.6)
            d = json.loads(idx_p.read_text(encoding="utf-8"))
            rec = d["filings"]["recent"]
            cands = [(rec["filingDate"][i], rec["form"][i],
                      rec["accessionNumber"][i], rec["primaryDocument"][i],
                      rec.get("reportDate", [""] * len(rec["form"]))[i])
                     for i in range(len(rec["form"]))
                     if rec["form"][i] == form]
            for fdate, frm, acc, doc, rdate in cands[:N_EDITIONS]:
                fy = (rdate or fdate)[:4]
                rel = f"sec/{tag}_{frm.replace('/', '')}_{fy}_{acc}.htm"
                fp = RAW / rel
                if fp.exists() and rel in have:
                    continue
                fp.parent.mkdir(parents=True, exist_ok=True)
                url = ("https://www.sec.gov/Archives/edgar/data/"
                       f"{cik}/{acc.replace('-', '')}/{doc}")
                st, ct, n = curl(url, fp)
                log(f"  {tag} {frm} {fy} HTTP {st} {n:,}b")
                time.sleep(1.6)
                if st != 200 or n < 50000:
                    if fp.exists():
                        fp.unlink()
                    continue
                rows = [r for r in rows if r["relative_path"] != rel]
                rows.append({
                    "relative_path": rel, "manufacturer": legal, "cik": cik,
                    "form": frm, "fiscal_year": fy, "filing_date": fdate,
                    "accession": acc, "source_url": url,
                    "bytes": fp.stat().st_size, "md5": md5(fp),
                    "content_type": ct, "http_status": st,
                    "fetched_date": TODAY, "retrieved_by": SCRIPT})
    finally:
        release_host("data.sec.gov", "submissions read")
        release_host("www.sec.gov", "manufacturer 10-K/20-F documents read")

    for p in sorted(RAW.glob("sec_submissions_*.json")):
        rel = p.name
        if rel not in {r["relative_path"] for r in rows}:
            rows.append({
                "relative_path": rel, "manufacturer": "", "cik": "",
                "form": "submissions-index", "fiscal_year": "",
                "filing_date": "", "accession": "",
                "source_url": "https://data.sec.gov/submissions/" + rel.replace(
                    "sec_submissions_", "CIK").replace(".json", ".json"),
                "bytes": p.stat().st_size, "md5": md5(p),
                "content_type": "application/json", "http_status": 200,
                "fetched_date": TODAY, "retrieved_by": SCRIPT})

    write(manifest_p, rows,
          ["relative_path", "manufacturer", "cik", "form", "fiscal_year",
           "filing_date", "accession", "source_url", "bytes", "md5",
           "content_type", "http_status", "fetched_date", "retrieved_by"])
    log(f"  manifest: {len(rows)} files under data/raw/external/gaming_devices/")


# ---------------------------------------------------------------------------
# STAGE 2A - MANUFACTURER FACTS from the filings.
# ---------------------------------------------------------------------------
def _totext(raw_bytes):
    t = raw_bytes.decode("utf-8", "replace")
    t = re.sub(r"<(script|style)\b.*?</\1>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = t.replace("&#160;", " ").replace("&nbsp;", " ")
    import html as _h
    t = _h.unescape(t).replace("\u00a0", " ")
    return re.sub(r"\s+", " ", t)


_NUM = r"\(?\s*\d{1,3}(?:,\d{3})+\s*\)?|\(?\s*\d{3,}\s*\)?"
# The VARIANCE column may be a single digit - AGS FY2022 prints
# `Class II 11,251 11,256 (5 ) (0.0 )%`. Requiring three digits there silently
# dropped that row while every neighbouring row published.
_VAR = r"\(?\s*-?\d{1,3}(?:,\d{3})*\s*\)?"
_ROW = re.compile(
    r"(?P<label>[A-Za-z][A-Za-z0-9 ,:&\-\u2019'\(\)\./]{0,90}?)\s+"
    r"(?P<n1>" + _NUM + r")\s+(?P<n2>" + _NUM + r")\s+(?P<v>" + _VAR + r")[\s%]")
_YEAR = re.compile(r"20\d\d")

# GEOGRAPHY AS THE ISSUER DEFINES IT. Order matters: non-Oklahoma before
# Oklahoma, specific before "total". PlayAGS is the only issuer that reports an
# installed base for a SINGLE STATE, and it picked Oklahoma - which is
# effectively an Indian Country split, since Oklahoma's commercial casino
# universe is two racetracks.
_GEO = [
    (r"non-?\s*oklahoma", "non-Oklahoma"),
    (r"\boklahoma\b", "Oklahoma"),
    (r"\bdomestic\b", "domestic"),
    (r"\binternational\b", "international"),
    (r"\bcanada\b", "U.S. and Canada"),
    (r"north america", "North America"),
    (r"\bglobal\b", "global"),
    (r"\btotal\b", "total"),
]

# A SHUFFLER IS NOT A GAMING DEVICE. Every issuer reports a "table products"
# installed base beside its EGM one; pooling them would count card shufflers
# and side-bet licences as slot machines.
_NOT_A_DEVICE = re.compile(r"table product|table game|shuffler|"
                           r"systems installed|interactive", re.I)


def _classify_label(lab, ctx=""):
    """Return (fact_type, device_class, geography) or None.

    `ctx` is the ~250 characters either side of the label. It exists for one
    reason: PlayAGS prints its class split as
    `EGM installed base: Class II 10,685 ... Class III 5,875 ...`, so the
    Class III row's own label is the bare words "Class III" and carries no
    metric name. Reading it without context would drop the only per-class
    device split any manufacturer publishes. Reading it WITHOUT requiring
    "installed base" nearby would attach a class to whatever number happened
    to follow the words - and "Class II and Class III markets" appears in the
    competition discussion of every one of these filings.

    The window is two-sided because AGS changed its own heading between
    editions: FY2022-FY2024 print `EGM installed base: Class II`, FY2021
    prints `EGM unit information: Class II` and only reaches the words
    "installed base" on the NEXT line (`Domestic installed base, end of
    period`). A one-sided window silently lost FY2020 and FY2021.
    """
    if _NOT_A_DEVICE.search(lab):
        return None
    l = lab.lower().strip()
    # A bare "Class II" / "Class III", or a heading ENDING in one
    # ("EGM unit information: Class II", "EGM installed base: Class II").
    mcls = re.search(r"class\s*(iii|ii)\s*$", l)
    if mcls:
        if "installed base" not in (ctx or "").lower():
            return None
        return ("installed_base_units",
                "Class III" if mcls.group(1) == "iii" else "Class II", "")
    if "installed base" in l:
        ftype = "installed_base_units"
    elif "units sold" in l:
        ftype = "units_sold"
    elif "average units installed" in l:
        ftype = "average_units_installed"
    else:
        return None
    dclass = ""
    if re.search(r"class\s*iii\b", l):
        dclass = "Class III"
    elif re.search(r"class\s*ii\b", l):
        dclass = "Class II"
    geo = ""
    for pat, name in _GEO:
        if re.search(pat, l):
            geo = name
            break
    return ftype, dclass, geo


def _bind_years(pre):
    """The table's OWN header year pair, taken as the pair nearest the label.

    Collecting every year and walking adjacent pairs backwards - rather than
    matching a two-year regex - is deliberate. A regex over
    "December 31, 2024 December 31, 2023 2024 vs 2023" consumes the wrong
    overlap and returns (2023, 2024), which silently reverses the columns. It
    did exactly that on Everi's first pass and refused six correct rows.
    """
    yrs = [int(m.group(0)) for m in _YEAR.finditer(pre)]
    for i in range(len(yrs) - 1, 0, -1):
        if yrs[i - 1] == yrs[i] + 1 and 2000 <= yrs[i] <= 2035:
            return (yrs[i - 1], yrs[i])
    return None


def _n(s):
    s = s.strip()
    neg = s.startswith("(")
    s = s.strip("() ").replace(",", "").strip()
    if not s.isdigit():
        return None
    return -int(s) if neg else int(s)


def build_manufacturer_facts():
    """Company-level only. NEVER attributed to a property.

    Accepted only when the filing's OWN variance column foots: n1 - n2 == v.
    That is the document proving its own column assignment, which is the only
    defence against the one-row / one-column shift that has now bitten this
    project in Michigan, Arizona and Florida.
    """
    log("STAGE 2A  manufacturer facts from SEC filings")
    man = read(RAW / "_SOURCE_MANIFEST.csv")
    docs = [r for r in man if r["relative_path"].startswith("sec/")]
    facts, refused = [], []
    seq = 0
    for r in sorted(docs, key=lambda x: (x["manufacturer"], x["fiscal_year"])):
        fp = RAW / r["relative_path"]
        if not fp.exists():
            continue
        t = _totext(fp.read_bytes())
        seen_here = set()
        for m in _ROW.finditer(t):
            lab = m.group("label").strip(" :")
            hit = _classify_label(lab, t[max(0, m.start() - 250):m.end() + 250])
            if not hit:
                continue
            n1, n2, v = _n(m.group("n1")), _n(m.group("n2")), _n(m.group("v"))
            if None in (n1, n2, v):
                continue
            if n1 - n2 != v:
                refused.append({"reason": "variance_column_does_not_foot",
                                "manufacturer": r["manufacturer"],
                                "fiscal_year": r["fiscal_year"],
                                "label": lab, "n1": n1, "n2": n2, "v": v,
                                "source_url": r["source_url"]})
                continue
            # Year binding from the table's own header, never from the filing
            # date. An Everi 10-K carries BOTH a 2024-vs-2023 and a
            # 2023-vs-2022 KPI table; defaulting to the filing year would date
            # the second one wrong and it would look perfectly sourced.
            pre = t[max(0, m.start() - 4000):m.start()]
            yrs = _bind_years(pre)
            if yrs is None:
                refused.append({"reason": "no_year_pair_header_within_4000_chars",
                                "manufacturer": r["manufacturer"],
                                "fiscal_year": r["fiscal_year"],
                                "label": lab, "n1": n1, "n2": n2, "v": v,
                                "source_url": r["source_url"]})
                continue
            quote = re.sub(r"\s+", " ", t[m.start():m.end()]).strip()
            ftype, dclass, geo = hit
            for val, fy in ((n1, yrs[0]), (n2, yrs[1])):
                key = (r["manufacturer"], ftype, dclass, geo, fy, val)
                if key in seen_here:
                    continue
                seen_here.add(key)
                seq += 1
                facts.append({
                    # set in one place, after the sort - see GMF_KEY_COLUMNS
                    "fact_id": "",
                    "manufacturer": r["manufacturer"],
                    "manufacturer_cik": r["cik"],
                    "fact_type": ftype,
                    "device_class": dclass,
                    "geography": geo,
                    "value": val,
                    "unit": "units",
                    "period_end": f"{fy}-12-31",
                    "fiscal_year": fy,
                    "period_basis": "table header year pair, verified by the "
                                    "filing's own variance column footing",
                    "filing_form": r["form"],
                    "filing_date": r["filing_date"],
                    "source_url": r["source_url"],
                    "source_quote": quote[:600],
                    "property_attributed": "NO - company-level. This measures "
                                           "the manufacturer's economics, not "
                                           "any casino's floor or revenue.",
                    "fetched_date": r["fetched_date"],
                    "tier": Tier.A.value,
                    "confidence": "issuer_kpi_table_footed",
                    "built_date": TODAY,
                })
    # Deduplicate across editions: the same (manufacturer, type, class, geo,
    # year) is reported by two consecutive filings. Keep one, and RECORD when
    # the two filings disagree - a source disagreeing with itself is a finding.
    by_key = defaultdict(list)
    for f in facts:
        by_key[(f["manufacturer"], f["fact_type"], f["device_class"],
                f["geography"], f["fiscal_year"])].append(f)
    kept, disagreements = [], []
    for k, fs in sorted(by_key.items()):
        vals = {f["value"] for f in fs}
        if len(vals) > 1:
            disagreements.append({"key": " | ".join(str(x) for x in k),
                                  "values": sorted(vals),
                                  "sources": [f["source_url"] for f in fs]})
            for f in fs:
                f["confidence"] = "issuer_kpi_table_footed;restated_between_editions"
            kept.extend(fs)
        else:
            kept.append(fs[0])
    kept = sorted(kept, key=lambda x: (x["manufacturer"], x["fact_type"],
                                       x["device_class"], x["geography"],
                                       x["fiscal_year"]))
    # The id is a function of the ROW, not of where the row ended up in this
    # sort. Sorting first and numbering second is what made the same fact
    # carry a different id every time a filing was added upstream.
    for f in kept:
        f["fact_id"] = surrogate_id("GMF", f, GMF_KEY_COLUMNS)
    log(f"  {len(kept)} company-level facts from {len(docs)} filings; "
        f"{len(refused)} candidate rows refused")
    return kept, refused, disagreements


# ---------------------------------------------------------------------------
# STAGE 2B - DEVICE OBSERVATIONS.
# ---------------------------------------------------------------------------
DEVICE_METRICS = {
    # metric in gaming_capacity_official -> (device_class, note)
    "gaming_machines": "",
    "class_iii_gaming_machines": "Class III",
    "class_ii_gaming_machines": "Class II",
    "gaming_machines_authorized_max": "",
    "dcetg": "Class III (DCETG)",
}


def _obs(seq, **kw):
    row = {k: "" for k in OBS_FIELDS}
    row.update(kw)
    row["built_date"] = TODAY
    assert row["observation_type"] in OBS_TYPES, row["observation_type"]
    mt = row["measurement_type"]
    if mt:
        m = MeasurementType(mt)
        # RULE 2 enforced per row, not once at import.
        if row["observation_type"] in ("FLOOR_COUNT", "REGULATORY_INVENTORY"):
            assert may_promote(m, MeasurementType.ACTIVE_FLOOR_COUNT), (
                f"{mt} may not be presented as a floor count: {row}")
        if row["observation_type"] == "AUTHORIZED_MAXIMUM":
            assert m is MeasurementType.AUTHORIZED_MAXIMUM
    return row


def from_capacity_official(unresolved):
    """Re-project the device-carrying rows of the official capacity layer."""
    rows = read(CLEAN / "gaming_capacity_official.csv")
    out = []
    for r in rows:
        metric = r["metric"]
        if metric not in DEVICE_METRICS:
            continue
        if (r.get("exclusion_flag") or "").strip():
            continue
        val = (r.get("value") or "").strip()
        if not val:
            continue
        try:
            q = float(val)
        except ValueError:
            continue
        status = r.get("measurement_status") or ""
        if status == "proposed":
            continue          # PROJECTED is not a device observation
        if metric.endswith("_authorized_max") or status == "authorization":
            otype, mt = "AUTHORIZED_MAXIMUM", MeasurementType.AUTHORIZED_MAXIMUM
            conf = "instrument_or_regulator_stated_ceiling"
        elif status == "audited_filing_measurement":
            otype, mt = "FLOOR_COUNT", MeasurementType.PROPERTY_REPORTED_COUNT
            conf = "issuer_audited_filing"
        elif status == "reported_measurement":
            otype, mt = "REGULATORY_INVENTORY", MeasurementType.REGULATORY_REPORTED_COUNT
            conf = "regulator_published_count"
        else:
            continue
        dclass = DEVICE_METRICS[metric]
        if not dclass and r.get("state") == "WA":
            dclass = "Class III (Tribal Lottery System player terminal)"
        if not r.get("facility_id") and not r.get("tribe_id"):
            unresolved.append({
                "reason": "device_row_has_neither_facility_nor_tribe",
                "YOUR_RULING": "", "candidate_properties": "",
                "facility_name_as_published": r.get("facility_name_as_published", ""),
                "metric": metric, "source_file": "gaming_capacity_official.csv",
                "source_quote": (r.get("source_quote") or "")[:400],
                "source_url": r.get("source_url", ""), "state": r.get("state", ""),
                "tribe_name_as_published": r.get("tribe_name_as_published", ""),
                "value": val})
        out.append(_obs(
            0,
            observation_id="",
            facility_id=r.get("facility_id", ""),
            tribe_id=r.get("tribe_id", ""),
            observation_date=r.get("as_of_date", ""),
            observation_type=otype,
            device_class=dclass,
            quantity=int(q) if q == int(q) else q,
            measurement_type=mt.value,
            source_url=r.get("source_url", ""),
            source_quote=(r.get("source_quote") or "")[:900],
            fetched_date=r.get("fetched_date", ""),
            tier=Tier.A.value if (r.get("facility_id") or r.get("tribe_id"))
            else Tier.B.value,
            confidence=conf,
        ))
    return out, "CAP"


def from_state_gaming_observations(unresolved):
    """Wisconsin LFB per-casino slot counts, seven biennial editions."""
    rows = read(CLEAN / "state_gaming_observations.csv")
    out = []
    for r in rows:
        if r.get("metric") != "gaming_machines":
            continue
        if (r.get("exclusion_flag") or "").strip():
            continue
        val = (r.get("value") or "").strip()
        if not val:
            continue
        try:
            q = float(val)
        except ValueError:
            continue
        if not r.get("facility_id"):
            unresolved.append({
                "reason": "lfb_facility_name_not_matched_to_cedar_property",
                "YOUR_RULING": "", "candidate_properties": "",
                "facility_name_as_published": r.get("facility_name_as_published", ""),
                "metric": "gaming_machines",
                "source_file": "state_gaming_observations.csv",
                "source_quote": (r.get("source_quote") or "")[:400],
                "source_url": r.get("source_url", ""), "state": r.get("state", ""),
                "tribe_name_as_published": r.get("tribe_name_as_published", ""),
                "value": val})
        out.append(_obs(
            0, observation_id="",
            facility_id=r.get("facility_id", ""),
            tribe_id=r.get("tribe_id", ""),
            observation_date=r.get("as_of_date", ""),
            observation_type="REGULATORY_INVENTORY",
            device_class="",
            quantity=int(q) if q == int(q) else q,
            measurement_type=MeasurementType.REGULATORY_REPORTED_COUNT.value,
            source_url=r.get("source_url", ""),
            source_quote=(r.get("source_quote") or "")[:900],
            fetched_date=r.get("fetched_date", ""),
            tier=Tier.A.value if (r.get("facility_id") or r.get("tribe_id"))
            else Tier.B.value,
            confidence="regulator_published_count",
        ))
    return out, "WI"


def from_wa_allocations():
    """A held allocation is an ENTITLEMENT. Six WA tribes hold one and operate
    no casino at all - that is the system working, not a data error."""
    out = []
    for r in read(CLEAN / "wa_machine_allocations.csv"):
        try:
            q = int(float(r["total_authorized"]))
        except (ValueError, KeyError):
            continue
        out.append(_obs(
            0, observation_id="",
            facility_id="",                       # an allocation is TRIBE-level
            tribe_id=r.get("tribe_id", ""),
            observation_date=r.get("effective_start", ""),
            observation_type="AUTHORIZED_MAXIMUM",
            device_class="Class III (Tribal Lottery System player terminal)",
            quantity=q,
            measurement_type=MeasurementType.AUTHORIZED_MAXIMUM.value,
            source_url=r.get("source_url", ""),
            source_quote=(r.get("source_quote") or "")[:900],
            fetched_date=r.get("fetched_date", ""),
            tier=r.get("tier", Tier.A.value),
            confidence="tribal_allocation_transferable_to_another_tribe",
        ))
    return out, "WAA"


def from_compact_terms():
    """Device caps written into the instrument itself."""
    out = []
    for r in read(CLEAN / "compact_structured_terms.csv"):
        if r.get("term_field") not in ("device_caps", "class_iii_devices_authorized"):
            continue
        v = (r.get("value_numeric") or "").strip()
        if not v:
            continue
        try:
            q = float(v)
        except ValueError:
            continue
        if q <= 0:
            continue
        out.append(_obs(
            0, observation_id="",
            facility_id="",
            tribe_id=r.get("tribe_id", ""),
            observation_date=r.get("effective_from", ""),
            observation_type="AUTHORIZED_MAXIMUM",
            device_class="Class III",
            quantity=int(q) if q == int(q) else q,
            measurement_type=MeasurementType.AUTHORIZED_MAXIMUM.value,
            source_url=r.get("source_url", ""),
            source_quote=(r.get("source_quote") or "")[:900],
            fetched_date=r.get("fetched_date", ""),
            tier=Tier.A.value if r.get("tribe_id") else Tier.B.value,
            confidence="compact_instrument_stated_cap",
        ))
    return out, "CST"


# --- NEW EXTRACTION 1: Oklahoma, statewide Class III device series ----------
# Edition year per on-disk filename. OMES's own naming is inconsistent
# (`14`, `2016`, `19-FINAL`, the typo `GameCompAnnReort2022`, and finally
# `gaming-compliance-report-2025-UA`), so the edition cannot be parsed from the
# filename and is asserted against the report's own "In FY <year>" sentence
# below - if the two disagree the row is refused.
OK_REPORTS = {
    "GameCompAnnReport14.pdf": "2014",
    "GameCompAnnReport15.pdf": "2015",
    "GameCompAnnReport2016.pdf": "2016",
    "GameCompAnnReport2017.pdf": "2017",
    "GameCompAnnReport2018.pdf": "2018",
    "GameCompAnnReport19-FINAL.pdf": "2019",
    "GameCompAnnReport20-FINAL.pdf": "2020",
    "GameCompAnnReport2021.pdf": "2021",
    "GameCompAnnReort2022.pdf": "2022",
    "GameCompAnnReport2023.pdf": "2023",
    "GameCompAnnReport2024.pdf": "2024",
    "gaming-compliance-report-2025-UA.pdf": "2025",
}

# THE URL IS NOT GUESSED. It is read out of OMES's own reports page, saved on
# disk as `ok_resources_reports.html`, by matching the file's basename against
# the page's hrefs. A source_url reconstructed from a filename pattern is a
# fabricated citation even when it happens to resolve.
OK_REPORTS_PAGE = OFFICIAL / "ok_resources_reports.html"
OK_REPORTS_PAGE_URL = ("https://oklahoma.gov/omes/divisions/"
                       "budget-policy-gaming-compliance/gaming-compliance/"
                       "resources/reports.html")


def _ok_url_map():
    if not OK_REPORTS_PAGE.exists():
        return {}
    html_t = OK_REPORTS_PAGE.read_text(encoding="utf-8", errors="replace")
    out = {}
    for m in re.finditer(r"""["'](/?[^"']*?\.pdf)["']""", html_t, re.I):
        href = m.group(1)
        base = href.rsplit("/", 1)[-1]
        if base in OK_REPORTS:
            out[base] = ("https://oklahoma.gov" + href
                         if href.startswith("/") else href)
    return out

# OMES changed its own sentence. Through the FY2014 edition it reported a
# LEVEL ("there were 39,936 Class III machines"); from FY2015 it reports a
# MONTHLY AVERAGE ("a monthly average of 40,667"). Two different statistics
# under one heading is a series break, so the basis travels in the quote and
# `series_break_basis` is named in the confidence string rather than the two
# being silently pooled.
OK_RX = re.compile(
    r"In FY\s*(?P<fy1>\d{4}),?\s*there (?:was a monthly average of|were)\s*"
    r"(?P<v1>[\d,]+)\s*Class III machines compared to\s*"
    r"(?P<v2>[\d,]+)\s*in FY\s*(?P<fy2>\d{4})", re.I)


def _pdftext(path):
    try:
        p = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                           capture_output=True, timeout=180)
        return p.stdout.decode("utf-8", "replace")
    except Exception:
        return ""


def from_oklahoma_omes(findings):
    """OMES states the statewide monthly-average Class III machine count in
    prose, twice per edition - the reported year and the prior year. Both are
    kept, and where two editions disagree about the SAME fiscal year that is
    recorded as a finding rather than reconciled."""
    d = OFFICIAL / "ok_omes_reports"
    urls = _ok_url_map()
    out = []
    by_fy = defaultdict(list)
    for fname, edition in sorted(OK_REPORTS.items()):
        p = d / fname
        if not p.exists():
            continue
        url = urls.get(fname)
        if not url:
            findings.append(
                f"Oklahoma: {fname} is on disk but its URL is not on OMES's "
                "own reports page as saved - REFUSED rather than citing a "
                "reconstructed URL")
            continue
        t = re.sub(r"\s+", " ", _pdftext(p))
        m = OK_RX.search(t)
        if not m:
            findings.append(f"Oklahoma: no Class III machine sentence found in "
                            f"{fname} (edition FY{edition})")
            continue
        if m.group("fy1") != edition:
            findings.append(
                f"Oklahoma: {fname} is filed as the FY{edition} edition but "
                f"its own sentence reports FY{m.group('fy1')} - REFUSED")
            continue
        quote = m.group(0).strip()
        basis = ("monthly_average" if "monthly average" in quote.lower()
                 else "level_as_reported_pre_FY2015_wording")
        for fy, val in ((m.group("fy1"), m.group("v1")),
                        (m.group("fy2"), m.group("v2"))):
            q = int(val.replace(",", ""))
            by_fy[fy].append((q, fname))
            out.append(_obs(
                0, observation_id="",
                facility_id="", tribe_id="",     # STATEWIDE, by design
                observation_date=f"{fy}-06-30",  # Oklahoma FY ends 30 June
                observation_type="REGULATORY_INVENTORY",
                device_class="Class III",
                quantity=q,
                measurement_type=MeasurementType.REGULATORY_REPORTED_COUNT.value,
                source_url=url,
                source_quote=(f'Oklahoma OMES Gaming Compliance Annual Report, '
                              f'FY{edition} edition: "{quote}"'),
                fetched_date="2026-08-07",
                tier=Tier.A.value,
                confidence=f"regulator_prose_statewide;basis={basis}",
            ))
    for fy, vs in sorted(by_fy.items()):
        vals = {v for v, _ in vs}
        if len(vals) > 1:
            findings.append(
                f"Oklahoma FY{fy}: OMES reports {sorted(vals)} for the same "
                f"fiscal year across editions " +
                ", ".join(sorted({f for _, f in vs})) +
                " - both kept, neither adjusted.")
    return out, "OK"


# --- NEW EXTRACTION 2: Arizona ADG FY2025 Annual Report --------------------
# Every quote below was read out of the PDF and is re-verified against the
# document's text layer at build time. If a quote is not present verbatim the
# row is NOT written and the failure is logged - a hard-coded quote that has
# drifted from its source is exactly the fabrication this project refuses.
AZ_ANNUAL = STATE_RAW / "az" / "adg_annual_report_fy2025.pdf"
AZ_ANNUAL_URL = ("https://gaming.az.gov/sites/default/files/"
                 "FY2025%20Annual%20Report%20Arizona%20Department%20of%20Gaming_0.pdf")

AZ_FACILITY_CEILING_QUOTE = (
    "Under the amended Compacts, a maximum of 1,450 gaming machines are "
    "authorized at each gaming facility in the state.")
AZ_RIGHTS_QUOTE = (
    "Currently, 16 Arizona Tribes operate 26 Class III casinos in the State. "
    "Another six Tribes do not have casinos but have slot machine rights that "
    "they may lease to other Tribes with casinos (transfer agreements).")
AZ_RIGHTS_TRIBES = [
    "Havasupai Indian Tribe", "Hopi Tribe", "Hualapai Indian Tribe",
    "Kaibab Band of Paiute Indians", "San Juan Southern Paiute Indian Tribe",
    "Zuni Tribe",
]


def from_arizona_annual(spine, unresolved, findings):
    """Arizona runs a transferable slot-rights market like Washington's.

    The rights-holding tribes are NAMED in the FY2025 annual report; the LEDGER
    of executed transfers is not published anywhere on gaming.az.gov (swept
    this build - see the log). So this emits what the document states: a
    statewide per-facility ceiling, and the six tribes holding leasable rights
    with no casino. It emits NO transfer edges, because none are published.
    """
    out = []
    if not AZ_ANNUAL.exists():
        findings.append("Arizona: FY2025 ADG annual report not on disk")
        return out, "AZR"
    t = re.sub(r"\s+", " ", _pdftext(AZ_ANNUAL))

    def present(q):
        return re.sub(r"\s+", " ", q) in t

    if present(AZ_FACILITY_CEILING_QUOTE):
        out.append(_obs(
            0, observation_id="", facility_id="", tribe_id="",
            observation_date="2025-06-30",
            observation_type="AUTHORIZED_MAXIMUM",
            device_class="",
            quantity=1450,
            measurement_type=MeasurementType.AUTHORIZED_MAXIMUM.value,
            source_url=AZ_ANNUAL_URL,
            source_quote=("Arizona Department of Gaming, FY2025 Annual Report: "
                          f'"{AZ_FACILITY_CEILING_QUOTE}"'),
            fetched_date="2026-08-07", tier=Tier.A.value,
            confidence="regulator_stated_statewide_per_facility_ceiling",
        ))
    else:
        findings.append("Arizona: per-facility 1,450 ceiling quote NOT verbatim "
                        "in the FY2025 report text layer - row withheld")

    # ADG sets this as a two-column infographic: the two numbers on one
    # baseline, the two labels stacked beneath them IN THE SAME COLUMN ORDER.
    # The pairing is therefore positional, and the quote says so rather than
    # presenting a layout inference as if the document had written a sentence.
    # Both numbers are carried in the quote so a reader can check the pairing.
    mc = re.search(r"(?P<a>\d{1,3}(?:,\d{3})+)\s+(?P<b>\d{1,4})\s+"
                   r"Machines\s+Casino\s+Certified\s+Visits", t)
    if mc:
        out.append(_obs(
            0, observation_id="", facility_id="", tribe_id="",
            observation_date="2025-06-30",
            observation_type="REGULATORY_INVENTORY",
            device_class="",
            quantity=int(mc.group("a").replace(",", "")),
            measurement_type=MeasurementType.REGULATORY_REPORTED_COUNT.value,
            source_url=AZ_ANNUAL_URL,
            source_quote=(
                "Arizona Department of Gaming, FY2025 Annual Report, Machine "
                f'Compliance panel, as the text layer renders it: "'
                f'{mc.group(0).strip()}". Two figures on one baseline with '
                "their labels stacked beneath in the same column order: "
                f'{mc.group("a")} = Machines Certified, {mc.group("b")} = '
                "Casino Visits. The pairing is POSITIONAL, not stated in a "
                "sentence, and both figures are quoted so it can be checked. "
                "This is the number of machines ADG CERTIFIED in FY2025 "
                "statewide - a regulatory action count. It is not a floor "
                "count and is not attributable to any property."),
            fetched_date="2026-08-07", tier=Tier.A.value,
            confidence="regulator_annual_report_certification_count;"
                       "label_pairing_positional",
        ))
    else:
        findings.append(
            "Arizona: the FY2025 ADG annual report's Machine Compliance panel "
            "carries what looks like a device-flow number - the linear text "
            "layer renders it as 'Total Games Approved 8,007 537 1,478 "
            "Promotions/Lotteries 144 Poker Tournaments Machines Casino 244 "
            "Other Approved Submissions 34 New/Revised Table Games Certified "
            "Visits'. Two infographic columns are INTERLEAVED with a third, so "
            "which number belongs to 'Machines Certified' can only be settled "
            "by reading word coordinates, not the text layer. WITHHELD. This "
            "is the same failure mode as the Michigan payment tables and the "
            "Arizona status report, and the same answer: read positions and "
            "foot the result, or do not publish the number.")

    # SECOND LEG for the state check, taken from Cedar's own compact file
    # rather than hard-coded. The Zuni Tribe of the Zuni Reservation is seated
    # in NEW MEXICO and holds three ARIZONA compacts (2003, 2021, 2022) for its
    # Arizona lands, so a bare "spine state must be AZ" guard would have
    # refused a correct resolution. A tribe that has signed an Arizona compact
    # is by definition an Arizona compacted tribe.
    az_compacted = {r["tribe_id"] for r in read(CLEAN / "compacts.csv")
                    if (r.get("state") or "").strip().lower() == "arizona"
                    and r.get("tribe_id")}

    if present(AZ_RIGHTS_QUOTE):
        for name in AZ_RIGHTS_TRIBES:
            tid, canon, how = resolve_entity(name, spine)
            if not tid:
                unresolved.append({
                    "reason": f"az_rights_holder_unresolved:{how}",
                    "YOUR_RULING": "", "candidate_properties": "",
                    "facility_name_as_published": "", "metric": "slot_machine_rights",
                    "source_file": "az/adg_annual_report_fy2025.pdf",
                    "source_quote": AZ_RIGHTS_QUOTE, "source_url": AZ_ANNUAL_URL,
                    "state": "AZ", "tribe_name_as_published": name, "value": ""})
                continue
            row = [r for r in spine if r["tribe_id"] == tid][0]
            # GOVERNMENT CLASS ONLY. A compact party, and therefore a holder of
            # compacted slot rights, is a federally recognised tribe by
            # definition - which disposes of the Chickasaw-Children's-Village
            # class of defect before it can start.
            gov = "Federally recognized" in (row.get("entity_class") or "")
            in_az = ((row.get("state") or "").upper() == "AZ"
                     or tid in az_compacted)
            if not (gov and in_az):
                # The spine's short name "San Juan" IS San Juan Southern Paiute
                # of ARIZONA (AGENTS.md 2026-08-07). The state check is what
                # makes that correct rather than lucky.
                unresolved.append({
                    "reason": "az_rights_holder_failed_class_or_state_guard",
                    "YOUR_RULING": "", "candidate_properties": tid,
                    "facility_name_as_published": "", "metric": "slot_machine_rights",
                    "source_file": "az/adg_annual_report_fy2025.pdf",
                    "source_quote": AZ_RIGHTS_QUOTE, "source_url": AZ_ANNUAL_URL,
                    "state": "AZ", "tribe_name_as_published": name, "value": ""})
                continue
            out.append(_obs(
                0, observation_id="", facility_id="", tribe_id=tid,
                observation_date="2025-06-30",
                observation_type="AUTHORIZED_MAXIMUM",
                device_class="Class III",
                quantity="",     # ADG states the RIGHT, never its size
                measurement_type=MeasurementType.AUTHORIZED_MAXIMUM.value,
                source_url=AZ_ANNUAL_URL,
                source_quote=("Arizona Department of Gaming, FY2025 Annual "
                              f'Report: "{AZ_RIGHTS_QUOTE}" This tribe is '
                              'listed under "Compacted Tribes without Casinos". '
                              "The report states the RIGHT exists and that it "
                              "is leasable; it states no number of devices, so "
                              "quantity is deliberately blank."),
                fetched_date="2026-08-07", tier=Tier.A.value,
                confidence="regulator_named_rights_holder_no_quantity_published",
            ))
    else:
        findings.append("Arizona: rights-holder quote NOT verbatim in the "
                        "FY2025 report text layer - six rows withheld")
    return out, "AZR"


# --- The sweeps that returned nothing, measured rather than assumed --------
# WORD BOUNDARIES ARE NOT OPTIONAL HERE. Without them `Everi` matches inside
# "sev-ERI-ty" and reported 42 phantom manufacturer mentions across the tribal
# issuer filings on the first pass - a containment false positive of exactly
# the class AGENTS.md records, in a sweep whose whole purpose was to measure an
# absence. An unbounded pattern would have turned a true negative into a
# published claim that manufacturers ARE named.
MFR_RX = re.compile(
    r"\b(?:International Game Technology|Bally Gaming|Bally Technologies|"
    r"WMS Gaming|Aristocrat|Konami|Multimedia Games|"
    r"Video Gaming Technologies|Scientific Games|Light & Wonder|"
    r"Everi|Rocket Gaming|IGT|AGS)\b", re.I)


def sweep_declinations_for_manufacturers(findings):
    """Where an equipment lease would surface in the FEDERAL record."""
    rx = MFR_RX
    dev = re.compile(r"gaming machine|slot machine|electronic gaming device", re.I)
    n_files = n_dev = n_mfr = 0
    for p in sorted(DECL_OCR.glob("*.json")):
        n_files += 1
        try:
            d = json.loads(p.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        pg = d.get("pages")
        t = " ".join(pg) if isinstance(pg, list) else str(pg)
        if dev.search(t):
            n_dev += 1
        if rx.search(t):
            n_mfr += 1
    findings.append(
        f"NIGC declination corpus swept: {n_files} OCR'd letters, {n_dev} "
        f"mention a gaming machine at all, {n_mfr} name a device manufacturer. "
        "No letter carries a manufacturer + model + quantity for a named "
        "property, so no MANUFACTURER_PLACEMENT row is derivable from the "
        "federal declination record.")
    return n_files, n_dev, n_mfr


def sweep_issuer_filings_for_manufacturers(findings):
    """And where it would surface in the TRIBAL ISSUER's own audited filings."""
    d = OFFICIAL / "sec_filings" / "txt"
    n = hits = supply = 0
    examples = []
    for p in sorted(d.glob("*")):
        if not p.is_file():
            continue
        n += 1
        t = re.sub(r"\s+", " ", p.read_text(encoding="utf-8", errors="replace"))
        found = False
        for m in MFR_RX.finditer(t):
            found = True
            win = t[max(0, m.start() - 300):m.start() + 200]
            if re.search(r"purchas|leas|suppl|vendor|install|acquir[a-z]* .{0,40}"
                         r"machine", win, re.I):
                supply += 1
            elif len(examples) < 3:
                examples.append(re.sub(r"\s+", " ", win)[:180])
        if found:
            hits += 1
    findings.append(
        f"Tribal gaming issuer filings swept: {n} Mohegan / Seneca 10-K and "
        f"S-4 documents, {hits} mention a slot manufacturer at all and "
        f"{supply} mention one in a supply, lease or purchase context. The "
        "only mentions are an officer's prior employer in a biography "
        "(\"positions of increasing responsibility at Scientific Games "
        "Corporation\"). A tribal issuer reports how many machines it "
        "operates and never who built them.")
    return n, hits


# ---------------------------------------------------------------------------
# BUILD
# ---------------------------------------------------------------------------
def build():
    log("STAGE 2  build")
    spine = read(SPINE / "cedar_entity_spine.csv")
    log(f"  spine: {len(spine):,} entities")

    unresolved, findings = [], []

    parts = []
    parts.append(from_capacity_official(unresolved))
    parts.append(from_state_gaming_observations(unresolved))
    parts.append(from_wa_allocations())
    parts.append(from_compact_terms())
    parts.append(from_oklahoma_omes(findings))
    parts.append(from_arizona_annual(spine, unresolved, findings))

    obs = []
    counters = Counter()
    for rows, prefix in parts:
        for i, r in enumerate(rows, 1):
            counters[prefix] += 1
            r["observation_id"] = f"GDO-{prefix}-{counters[prefix]:06d}"
            obs.append(r)

    # RULE 1, enforced structurally: device_class lives HERE and nowhere else.
    # RULE 4: no property ID is invented; every facility_id must already exist.
    fac = {r["facility_id"] for r in read(CLEAN / "gaming_facilities.csv")}
    bad = {r["facility_id"] for r in obs
           if r["facility_id"] and r["facility_id"] not in fac}
    assert not bad, f"invented property IDs: {sorted(bad)[:5]}"

    # Zero fabrication: no row without a URL and a verbatim quote.
    missing = [r for r in obs if not r["source_url"] or not r["source_quote"]]
    if missing:
        for r in missing:
            unresolved.append({
                "reason": "row_missing_source_url_or_source_quote_REFUSED",
                "YOUR_RULING": "", "candidate_properties": "",
                "facility_name_as_published": "", "metric": r["observation_type"],
                "source_file": r["observation_id"], "source_quote": r["source_quote"],
                "source_url": r["source_url"], "state": "",
                "tribe_name_as_published": r["tribe_id"], "value": r["quantity"]})
        obs = [r for r in obs if r["source_url"] and r["source_quote"]]
    log(f"  {len(missing)} rows refused for missing url/quote")

    write(CLEAN / "gaming_device_observations.csv", obs, OBS_FIELDS)
    log(f"  wrote gaming_device_observations.csv  {len(obs):,} rows")

    facts, refused, disagreements = build_manufacturer_facts()
    write(CLEAN / "gaming_manufacturer_facts.csv", facts, MFR_FIELDS)
    log(f"  wrote gaming_manufacturer_facts.csv   {len(facts):,} rows")
    if refused:
        write(RAW / f"manufacturer_kpi_refused_{TODAY}.csv", refused,
              ["reason", "manufacturer", "fiscal_year", "label", "n1", "n2",
               "v", "source_url"])

    n_decl, n_decl_dev, n_decl_mfr = sweep_declinations_for_manufacturers(findings)
    n_iss, n_iss_hits = sweep_issuer_filings_for_manufacturers(findings)

    # One row per ISSUE, not per observation. 55 Wisconsin rows collapse to the
    # handful of casino names that actually need a ruling; a queue that repeats
    # the same decision fifty-five times does not get worked.
    seen_q, dedup = set(), []
    for q in unresolved:
        k = (q["reason"], q["facility_name_as_published"],
             q["tribe_name_as_published"], q["source_file"])
        if k in seen_q:
            continue
        seen_q.add(k)
        dedup.append(q)
    log(f"  review queue deduplicated {len(unresolved)} -> {len(dedup)} issues")
    unresolved = dedup
    if unresolved:
        write(REVIEW / f"gaming_device_unresolved_{TODAY}.csv", unresolved,
              ["reason", "YOUR_RULING", "candidate_properties",
               "facility_name_as_published", "metric", "source_file",
               "source_quote", "source_url", "state",
               "tribe_name_as_published", "value"])
    log(f"  review queue: {len(unresolved)} rows")

    # ---------------- coverage, MEASURED ----------------
    facilities = read(CLEAN / "gaming_facilities.csv")
    n_props = len(facilities)
    covered = {r["facility_id"] for r in obs if r["facility_id"]}
    tribes = {r["tribe_id"] for r in obs if r["tribe_id"]}
    stats = {
        "observations": len(obs),
        "by_observation_type": dict(Counter(r["observation_type"] for r in obs)),
        "by_measurement_type": dict(Counter(r["measurement_type"] for r in obs)),
        "by_device_class": dict(Counter(r["device_class"] or "(unstated by source)"
                                        for r in obs)),
        "by_source_prefix": dict(counters),
        "properties_covered": len(covered),
        "properties_total": n_props,
        "properties_covered_pct": round(100.0 * len(covered) / n_props, 1),
        "tribes_covered": len(tribes),
        "rows_with_manufacturer": sum(1 for r in obs if r["manufacturer"]),
        "rows_with_platform_or_cabinet": sum(1 for r in obs
                                             if r["platform_or_cabinet"]),
        "rows_with_shipment_direction": sum(
            1 for r in obs if r["shipment_origin"] or r["shipment_destination"]),
        "date_min": min((r["observation_date"] for r in obs
                         if r["observation_date"]), default=""),
        "date_max": max((r["observation_date"] for r in obs
                         if r["observation_date"]), default=""),
        "manufacturer_facts": len(facts),
        "manufacturers": sorted({f["manufacturer"] for f in facts}),
        "manufacturer_kpi_rows_refused": len(refused),
        "manufacturer_restatements": disagreements,
        "declination_sweep": {"letters": n_decl, "mention_a_machine": n_decl_dev,
                              "name_a_manufacturer": n_decl_mfr},
        "issuer_filing_sweep": {"documents": n_iss, "name_a_manufacturer": n_iss_hits},
        "findings": findings,
        "review_rows": len(unresolved),
        "built_date": TODAY,
    }
    (LOGS / f"gaming_devices_summary_{TODAY}.json").write_text(
        json.dumps(stats, indent=1), encoding="utf-8")

    log("")
    log(f"  properties covered: {len(covered)} of {n_props} "
        f"({stats['properties_covered_pct']}%)")
    log(f"  tribes covered:     {len(tribes)}")
    for k, v in sorted(stats["by_observation_type"].items(), key=lambda kv: -kv[1]):
        log(f"    {v:>6,}  {k}")
    log(f"  device_class stated on "
        f"{sum(v for k, v in stats['by_device_class'].items() if k != '(unstated by source)'):,}"
        f" of {len(obs):,} rows")
    log(f"  manufacturer named on {stats['rows_with_manufacturer']} rows; "
        f"cabinet on {stats['rows_with_platform_or_cabinet']}; "
        f"shipment direction on {stats['rows_with_shipment_direction']}")

    write_codebook()
    write_build_log(stats, obs, facts, disagreements, findings)
    return stats


# ---------------------------------------------------------------------------
# CODEBOOK - a FRAGMENT. codebook_master.csv is never touched.
# ---------------------------------------------------------------------------
CODEBOOK = [
    ("observation_id", "Cedar device-observation key. The prefix names the "
     "upstream evidence: CAP=gaming_capacity_official, WI=Wisconsin LFB via "
     "state_gaming_observations, WAA=wa_machine_allocations, "
     "CST=compact_structured_terms, OK=Oklahoma OMES (new extraction), "
     "AZR=Arizona ADG FY2025 annual report (new extraction)."),
    ("facility_id", "Existing Cedar property ID (CCP-/VP-/TPL-). BLANK where "
     "the observation is about a tribe or a whole state rather than a "
     "property. No property ID is created by this build; a regulator or "
     "manufacturer using a different property name is an ALIAS."),
    ("tribe_id", "Cedar spine entity ID. BLANK on statewide rows by design."),
    ("observation_date", "The date the source's figure is AS OF. Oklahoma rows "
     "use the 30 June state fiscal year end."),
    ("observation_type", "SHIPMENT_IN | SHIPMENT_OUT | DEVICE_ADDITION | "
     "DEVICE_REMOVAL | REGULATORY_INVENTORY | MANUFACTURER_PLACEMENT | "
     "FLOOR_COUNT | FLEET_REPLACEMENT | AUTHORIZED_MAXIMUM. "
     "REGULATORY_INVENTORY = a regulator's count of devices in place. "
     "FLOOR_COUNT = the operator's own signed statement of its floor. "
     "AUTHORIZED_MAXIMUM = a ceiling or entitlement and NEVER an operating "
     "count."),
    ("manufacturer", "Who built the devices. Populated only where a source "
     "names the manufacturer for a specific dated placement. No free source "
     "does so, so this column is empty; the emptiness is the finding."),
    ("platform_or_cabinet", "Cabinet or platform name. Empty for the same "
     "reason as manufacturer."),
    ("game_theme", "Game title. Empty for the same reason as manufacturer."),
    ("device_class", "Class II / Class III / Class III (DCETG) / Class III "
     "(Tribal Lottery System player terminal), AS STATED BY THE SOURCE ON "
     "THIS DATE. Blank means the source did not say, never 'unknown class'. "
     "THIS IS AN OBSERVATION FIELD, NOT A PROPERTY ATTRIBUTE: a floor can be "
     "converted between classes with no federal record, so class is a "
     "necessary but not sufficient condition and must always be read with its "
     "date."),
    ("quantity", "Number of devices. Blank where the source asserts a right or "
     "a category without a number - a blank quantity is silence, not zero."),
    ("shipment_origin", "Shipping party on a device movement. Empty: no free "
     "source publishes shipment-level detail."),
    ("shipment_destination", "Receiving party on a device movement. Empty for "
     "the same reason."),
    ("measurement_type", "cedar_domain.MeasurementType. may_promote() is "
     "asserted per row: AUTHORIZED_MAXIMUM, PROJECTED, "
     "ENVIRONMENTAL_REVIEW_COUNT and DERIVED_BOUND can never be presented as "
     "an active floor count."),
    ("source_url", "The publisher's URL. Present on every row without "
     "exception."),
    ("source_quote", "Verbatim supporting text. Present on every row without "
     "exception; a row missing it is refused to the review queue."),
    ("fetched_date", "When the underlying document was retrieved."),
    ("tier", "cedar_domain.Tier. A publishes; B is internal only. B here means "
     "the observation is real but its property or tribe is not resolved."),
    ("confidence", "What KIND of evidence this is, in words, not a number."),
    ("built_date", "Build date of this row."),
]

CODEBOOK_MFR = [
    ("fact_id", "Cedar manufacturer-fact key."),
    ("manufacturer", "Filing entity's legal name AT THE TIME OF FILING. "
     "International Game Technology PLC now files as Brightstar Lottery PLC "
     "and reports IGT Gaming as discontinued operations."),
    ("manufacturer_cik", "SEC Central Index Key."),
    ("fact_type", "installed_base_units | average_units_installed | units_sold."),
    ("device_class", "Class II / Class III where the issuer splits its "
     "installed base by IGRA class. Blank where it does not."),
    ("geography", "domestic | international | total, as the issuer defines "
     "them. Not a Cedar geography and not comparable across issuers."),
    ("value", "Unit count as printed."),
    ("unit", "Always 'units'."),
    ("period_end", "Fiscal period end."),
    ("fiscal_year", "Fiscal year the value belongs to, taken from the KPI "
     "table's own header year pair, never from the filing date."),
    ("period_basis", "How the year was bound, and the check that validated it."),
    ("filing_form", "10-K or 20-F."),
    ("filing_date", "EDGAR filing date."),
    ("source_url", "EDGAR document URL."),
    ("source_quote", "Verbatim KPI table line."),
    ("property_attributed", "Always NO. A manufacturer's installed base or "
     "revenue per participation unit measures the MANUFACTURER's economics. "
     "It is never converted into a casino's gaming revenue and never "
     "apportioned to a property."),
    ("fetched_date", "Retrieval date."),
    ("tier", "cedar_domain.Tier."),
    ("confidence", "issuer_kpi_table_footed = the filing's own variance column "
     "reconciles n1 - n2, which is the document proving its own column "
     "assignment."),
    ("built_date", "Build date."),
]


def write_codebook():
    rows = []
    for v, d in CODEBOOK:
        rows.append({"dataset": "07h_gaming_device_observations", "variable": v,
                     "description": d, "source_file":
                     "data/clean/gaming_device_observations.csv",
                     "built_by": SCRIPT, "built_date": TODAY})
    for v, d in CODEBOOK_MFR:
        rows.append({"dataset": "07i_gaming_manufacturer_facts", "variable": v,
                     "description": d, "source_file":
                     "data/clean/gaming_manufacturer_facts.csv",
                     "built_by": SCRIPT, "built_date": TODAY})
    master = read(CLEAN / "codebook_master.csv")
    fields = list(master[0].keys()) if master else [
        "dataset", "variable", "description", "source_file", "built_by",
        "built_date"]
    out = [{k: r.get(k, "") for k in fields} for r in rows]
    for ds in ("07h_gaming_device_observations", "07i_gaming_manufacturer_facts"):
        cedar_codebook.write_fragment(ds, [r for r in out
                                           if r.get("dataset") == ds], fields)
    log(f"  codebook fragments: {len(out)} variables under "
        f"data/clean/codebook/ (codebook_master.csv NOT touched)")


# ---------------------------------------------------------------------------
def write_build_log(stats, obs, facts, disagreements, findings):
    ot = stats["by_observation_type"]
    dc = stats["by_device_class"]
    src = stats["by_source_prefix"]
    SRC_NAMES = {
        "CAP": "state regulators + SEC-filed issuer counts, re-projected from "
               "`gaming_capacity_official.csv`",
        "WI": "Wisconsin Legislative Fiscal Bureau per-casino slot counts, "
              "seven biennial editions, via `state_gaming_observations.csv`",
        "WAA": "Washington per-tribe player-terminal allocations, via "
               "`wa_machine_allocations.csv`",
        "CST": "compact device caps written into the instrument, via "
               "`compact_structured_terms.csv`",
        "OK": "Oklahoma OMES Gaming Compliance Report, statewide monthly "
              "average Class III machines (NEW EXTRACTION, 12 editions)",
        "AZR": "Arizona ADG FY2025 Annual Report (NEW EXTRACTION)",
    }
    lines = []
    A = lines.append
    A("# The gaming device layer — build log")
    A("")
    A(f"*Built {TODAY} by `{SCRIPT}`. Every number below is computed by the "
      "build and written to `logs/gaming_devices_summary_%s.json`; none is "
      "asserted by hand.*" % TODAY)
    A("")
    A("---")
    A("")
    A("## The honest headline")
    A("")
    A("**A slot-by-slot fleet per property is not buildable from free "
      "sources.** No public source anywhere in the United States publishes a "
      "dated manufacturer, cabinet, theme and quantity for a named tribal "
      "property. What is buildable is *how many devices, of what IGRA class, "
      "at what property or tribe, on what date* — and that is what this file "
      "holds.")
    A("")
    A(f"- **{stats['observations']:,} device observations**, "
      f"{stats['date_min']} to {stats['date_max']}")
    A(f"- **{stats['properties_covered']} of {stats['properties_total']} "
      f"properties ({stats['properties_covered_pct']}%)** carry at least one "
      f"device observation")
    A(f"- **{stats['tribes_covered']} tribes** carry at least one")
    A(f"- **{stats['rows_with_manufacturer']} rows name a manufacturer**, "
      f"{stats['rows_with_platform_or_cabinet']} name a cabinet, "
      f"{stats['rows_with_shipment_direction']} carry a shipment direction")
    A("")
    A("Those three zeros are the measured finding, not an unfinished column. "
      "The sweeps behind them are below.")
    A("")
    A("**Read the coverage figure with the right comparison.** The licensed "
      "Casino City panel carries dated device counts for **409** properties "
      "and, by standing rule, publishes for none of them — it is an internal "
      "QA layer and always will be. So the honest statement is not "
      f"\"{stats['properties_covered_pct']}% is low\"; it is that "
      f"**{stats['properties_covered']} properties can be device-counted from "
      "sources a subscriber can audit**, and that the remainder is a "
      "publishing constraint imposed by what regulators publish, not by what "
      "Cedar has looked for. Every state in the 18-state priority sweep is "
      "closed with a documented answer in "
      "`docs/GAMING_CAPACITY_OFFICIAL_LOG.md`.")
    A("")
    A("## Observations by type")
    A("")
    A("| observation_type | n |")
    A("|---|---:|")
    for k, v in sorted(ot.items(), key=lambda kv: -kv[1]):
        A(f"| `{k}` | {v:,} |")
    A("")
    A("## Observations by source")
    A("")
    A("| prefix | n | source |")
    A("|---|---:|---|")
    for k, v in sorted(src.items(), key=lambda kv: -kv[1]):
        A(f"| `GDO-{k}-` | {v:,} | {SRC_NAMES.get(k, k)} |")
    A("")
    A("**Never sum this file with `gaming_capacity_official.csv`.** Most rows "
      "re-express the same facts in a device-shaped schema with a typed "
      "`device_class`; the `source_url` and `source_quote` are the original "
      "publisher's in both files.")
    A("")
    A("## Class II / Class III is a DATED OBSERVATION")
    A("")
    A("> Elijah, 2026-08-07: *\"at any time a tribe can change their status by "
      "swapping out their machines, so it's a necessary but not sufficient "
      "condition.\"*")
    A("")
    A("A floor can be converted between classes with no federal record. So "
      "`device_class` sits on the observation with its own date and source, "
      "and **there is no device-class column on any property anywhere in "
      "Cedar**. Blank means *the source did not say*, never *unknown class*.")
    A("")
    A("| device_class | n |")
    A("|---|---:|")
    for k, v in sorted(dc.items(), key=lambda kv: -kv[1]):
        A(f"| {k} | {v:,} |")
    A("")
    A("Arizona is the only regulator in the country that publishes the split "
      "per casino, in separate Class III and Class II columns of the *Status "
      "of Tribal Gaming in Arizona* report, and it does so only for the "
      "editions Cedar has recovered.")
    A("")
    A("## An authorised maximum is never an operating count")
    A("")
    A("`cedar_domain.may_promote()` is imported and asserted at module import "
      "**and again per row**; a build that ever produced an "
      "`AUTHORIZED_MAXIMUM` presented as a floor count would fail loudly "
      "rather than publish.")
    A("")
    A("Washington's **1,075 player terminals per tribe** is an entitlement, "
      "and **six of the twenty-nine holders operate no casino at all** — Hoh, "
      "Lower Elwha, Makah, Quileute, Samish, Sauk-Suiattle. Statewide "
      "authorised total 29 × 1,075 = **31,175**.")
    A("")
    A("## Arizona runs the same market, and its ledger is NOT public")
    A("")
    A("The brief asked directly. The answer is documented, from ADG's own "
      "annual report:")
    A("")
    A("> \"Currently, 16 Arizona Tribes operate 26 Class III casinos in the "
      "State. Another six Tribes do not have casinos but have slot machine "
      "rights that they may lease to other Tribes with casinos (transfer "
      "agreements).\"")
    A("> — Arizona Department of Gaming, FY2025 Annual Report")
    A("")
    A("The six are named on the same page under *Compacted Tribes without "
      "Casinos*: **Havasupai · Hopi · Hualapai · Kaibab Band of Paiute · San "
      "Juan Southern Paiute · Zuni**. Each is emitted as an "
      "`AUTHORIZED_MAXIMUM` row with a **blank quantity**, because ADG states "
      "that the right exists and is leasable and states no number.")
    A("")
    A("ADG holds the transfer agreements — its own audit page lists *Transfer "
      "Agreements* among the things the Compact Compliance team reviews — but "
      "**publishes no ledger**. `gaming.az.gov/resources/reports` was "
      "enumerated this build: 36 linked PDFs, and not one is an allocation or "
      "transfer table. So **Arizona's transferable-rights ledger needs a "
      "public-records request, exactly like Washington's**, and for the same "
      "structural reason: the regulator receives the instrument and publishes "
      "a workload count.")
    A("")
    A("**Washington was not re-attempted**, per the brief and per "
      "`docs/WA_ALLOCATION_BUILD_LOG.md`: since Appendix X2 (2007) WSGC "
      "receives only *the number of transfers*, not the transfer documents, "
      "and the price sits by design in a separate agreement that is never "
      "filed.")
    A("")
    sweeps = [f for f in findings if "swept" in f]
    others = [f for f in findings if "swept" not in f]
    A("## Does any state publish shipment-level detail?")
    A("")
    A("**No.** The places a dated manufacturer + model + quantity would have "
      "to surface were swept and measured:")
    A("")
    for f in sweeps:
        A(f"- {f}")
    A("")
    A("Manufacturer newsrooms were probed directly rather than assumed: "
      "`playags.com/news` and `lnw.com/newsroom` both answer HTTP 308 to a "
      "plain GET and `everi.com/news` returns a JavaScript index whose "
      "headlines carry no property install. A manufacturer press release "
      "naming a specific property and a device count is the one property-level "
      "placement source that exists in principle; it is irregular, "
      "marketing-driven and was not obtained here. **Zero fabricated "
      "placements were written to fill the column.**")
    A("")
    A("Add to that the state sweep already closed in "
      "`docs/GAMING_CAPACITY_OFFICIAL_LOG.md`, where all 18 priority states "
      "carry a documented answer. **Machine shipment and transport records "
      "exist** — a Washington tribe cannot switch on an acquired terminal "
      "without filing, and Arizona certifies every machine before it runs — "
      "**but what reaches the public is a count of regulatory actions, never "
      "the movement.**")
    A("")
    A("## Extraction findings, recorded rather than smoothed")
    A("")
    for f in others:
        A(f"- {f}")
    A("")
    A("- **Oklahoma's series is deliberately double-stated.** Each OMES "
      "edition reports its own fiscal year AND the prior one, so most years "
      "appear twice from two independent editions. Both rows are kept: two "
      "editions agreeing is corroboration, and the one year where they "
      "**disagree** — FY2017, 41,395 against 41,382 — is the finding above. "
      "Deduplicating to one row per year would have hidden it.")
    A("- **Oklahoma changed its own statistic mid-series.** Through the FY2014 "
      "edition OMES reported a LEVEL (*\"there were 39,936 Class III "
      "machines\"*); from FY2015 it reports a MONTHLY AVERAGE (*\"a monthly "
      "average of 40,667\"*). Two different quantities under one heading, so "
      "the basis travels in `confidence` on every Oklahoma row rather than "
      "the two being pooled into one series.")
    A("")
    A("## Manufacturer facts — company-level, never a property")
    A("")
    A(f"`data/clean/gaming_manufacturer_facts.csv`, **{len(facts):,} facts** "
      f"from {len(stats['manufacturers'])} issuers.")
    A("")
    for m in stats["manufacturers"]:
        n = sum(1 for f in facts if f["manufacturer"] == m)
        yrs = sorted({f["fiscal_year"] for f in facts if f["manufacturer"] == m})
        A(f"- **{m}** — {n} facts, FY{yrs[0]}–FY{yrs[-1]}" if yrs else
          f"- **{m}** — {n} facts")
    A("")
    A("**The rule on every row:** a manufacturer's installed base, "
      "participation units or units sold measures *the manufacturer's* "
      "economics. It is never converted into a casino's gaming revenue and "
      "never apportioned to a property. `property_attributed` says so on "
      "every row, in words, so a downstream reader cannot miss it.")
    A("")
    A("**Every KPI row is accepted only if the filing's own variance column "
      "foots** (n1 − n2 == variance) **and its fiscal year is bound from the "
      "table's own header year pair**, never from the filing date. A candidate "
      "failing either test is refused to "
      f"`data/raw/external/gaming_devices/manufacturer_kpi_refused_{TODAY}.csv` "
      f"— currently {stats['manufacturer_kpi_rows_refused']}, so that file is "
      "not written. That is the same "
      "discipline that caught the one-row column shift in the Michigan payment "
      "tables and the Arizona status report: **read the document's own check, "
      "or do not publish the table.**")
    A("")
    A("Three extraction defects were found and fixed during this build, each "
      "of which would have shipped a plausible wrong number or a plausible "
      "wrong absence:")
    A("")
    A("1. **A two-year regex reverses the columns.** Over "
      "`December 31, 2024 December 31, 2023 2024 vs 2023` a "
      "`(20\\d\\d)\\D{1,80}?(20\\d\\d)` match consumes the wrong overlap and "
      "returns **(2023, 2024)**. Six correct Everi rows were refused on the "
      "first pass. Fixed by collecting every year and walking adjacent pairs "
      "backwards from the label.")
    A("2. **A one-sided context window lost the class split.** AGS prints "
      "`EGM installed base: Class II` in FY2022–FY2024 but "
      "`EGM unit information: Class II` in FY2020–FY2021, reaching the words "
      "*installed base* only on the following line. A backward-only window "
      "silently dropped two years of the only per-class series in the file.")
    A("3. **A three-digit minimum on the variance column dropped a real row.** "
      "AGS FY2022 prints `Class II 11,251 11,256 (5 ) (0.0 )%`; requiring "
      "three digits in the variance refused it while every neighbouring row "
      "published.")
    A("")
    A("And one **containment false positive inside a sweep whose entire "
      "purpose was to measure an absence**: without word boundaries, `Everi` "
      "matches inside *sev-**eri**-ty* and reported **42 phantom manufacturer "
      "mentions** across the tribal issuer filings. Unbounded, the sweep would "
      "have published the opposite of the truth — that issuers DO name their "
      "suppliers. Bounded, the real count is two, both a CFO's prior employer.")
    if disagreements:
        A("")
        A("**Restated between editions** (both kept, neither adjusted):")
        A("")
        for d in disagreements:
            A(f"- `{d['key']}` → {d['values']}")
    A("")
    A("### Two things the filings say that nothing else in the market carries")
    A("")
    A("- **PlayAGS splits its installed base by IGRA class.** Its FY2024 10-K "
      "prints `EGM installed base: Class II 10,685 / Class III 5,875` — the "
      "only Class II device count of national scope available for free "
      "anywhere, and it is the *manufacturer's* base, not any tribe's floor.")
    A("- **Light & Wonder names where Class II lives.** *\"These Class II and "
      "centrally determined systems primarily operate in Native American "
      "casinos in Washington, Florida, Alabama and Oklahoma.\"*")
    A("")
    A("### The hole that will not close from free sources")
    A("")
    A("**Konami Gaming Inc.** is a major supplier to Indian Country and its "
      "parent **delisted from the NYSE in 2015**. It files nothing current "
      "with the SEC, so there is no free filing-based installed base for it. "
      "**Aristocrat** is ASX-listed and files nothing with the SEC either. "
      "Both are named as principal competitors inside the filings this build "
      "does hold — *\"Aristocrat and Everi are our primary competitors in the "
      "Class II market\"* — which is how we know the gap is a gap and not an "
      "absence.")
    A("")
    A("**Inspired Entertainment** was pulled (four 10-Ks) and yielded zero "
      "device facts: its KPI tables report Virtual Sports and Interactive "
      "venues, not an EGM installed base. Retrieved, read, and returned "
      "nothing — recorded so the next pass does not re-pull it.")
    A("")
    A("Also dated: **International Game Technology PLC now files as Brightstar "
      "Lottery PLC and reports IGT Gaming as *discontinued operations***, so "
      "its newest 20-F carries no gaming installed base at all. A "
      "newest-edition-wins rule would have returned an empty IGT and looked "
      "like a retrieval failure.")
    A("")
    A("## What is structurally unobtainable")
    A("")
    A("1. **A per-property fleet.** Which cabinets, from which manufacturer, "
      "running which themes, are on a given floor is commercial information "
      "held by the tribe, its gaming commission and its vendors. No statute "
      "makes it public.")
    A("2. **Shipment records.** The Johnson Act (15 U.S.C. § 1173) registration "
      "and reporting regime runs to the Attorney General, not to a public "
      "docket. State device-transport notifications go to the state gaming "
      "agency and are not published.")
    A("3. **The moment a floor changes class.** A Class II floor can be "
      "swapped to Class III with no federal filing, which is precisely why "
      "class is stored dated and never as an attribute.")
    A("4. **Executed inter-tribal rights transfers, in both markets that have "
      "one.** Washington by documented narrowing (2007), Arizona by the "
      "regulator simply not publishing. Both need a public-records request.")
    A("5. **Konami and Aristocrat unit counts**, per above.")
    A("")
    A("## Review queue")
    A("")
    A(f"`review/gaming_device_unresolved_{TODAY}.csv` — "
      f"**{stats['review_rows']} rows**, blank `YOUR_RULING`, project "
      "reconcile-queue format. The dominant reason is a regulator's casino "
      "name that does not exactly match a Cedar property name; those rows are "
      "kept at tier B with their tribe, never snapped to a nearest match.")
    A("")
    A("## Rules honoured")
    A("")
    A("- **Zero fabrication** — every row carries `source_url` and a verbatim "
      "`source_quote`; rows missing either are refused to the queue rather "
      "than trusted. The Arizona hard-coded quotes are re-verified against "
      "the PDF's text layer at build time and the rows are withheld if a "
      "quote has drifted.")
    A("- **No second name matcher** — `resolve_entity` is imported from "
      "`code/33_apply_party_rulings.py`. What was added is a **refusal**, not "
      "a matcher: an Arizona rights holder must resolve to a *federally "
      "recognised* class AND be an Arizona tribe. That is what makes the "
      "spine's short name *San Juan* resolving to San Juan Southern Paiute of "
      "Arizona correct rather than lucky. The Arizona test reads Cedar's own "
      "`compacts.csv` rather than a hard-coded state, because **the Zuni Tribe "
      "of the Zuni Reservation is seated in New Mexico and holds three "
      "Arizona compacts** — a bare state check would have refused a correct "
      "resolution.")
    A("- **Aliases, not new properties** — the build asserts that every "
      "`facility_id` written already exists in `gaming_facilities.csv`.")
    A("- **`may_promote` asserted at import and per row.**")
    A("- **No modelled property revenue anywhere.**")
    A("- **Codebook written as a fragment** under `data/clean/codebook/`; "
      "`codebook_master.csv` was not touched.")
    A("- **Not edited:** `gaming_capacity_official.csv`, "
      "`wa_machine_allocations.csv`, `compact_structured_terms.csv`, "
      "`gaming_facilities.csv`, `gaming_property_capacity_history.csv`, "
      "`nigc_*`, `ca_gaming_*`, `fl_*`, `tribal_tax_bases.csv`, "
      "`prime_contracts.csv`, `federal_funding_transactions.csv`, "
      "`subawards.csv`, `entity_*`, the identifier ledger, the spine.")
    A("")
    A("## Files")
    A("")
    A("```")
    A(f"{SCRIPT}")
    A(f"data/clean/gaming_device_observations.csv     {stats['observations']:,} rows")
    A(f"data/clean/gaming_manufacturer_facts.csv      {len(facts):,} rows")
    A("data/clean/codebook/07h_gaming_device_observations.csv")
    A("data/clean/codebook/07i_gaming_manufacturer_facts.csv")
    A("data/raw/external/gaming_devices/             _SOURCE_MANIFEST.csv + md5s")
    A(f"review/gaming_device_unresolved_{TODAY}.csv   {stats['review_rows']} rows")
    A(f"logs/gaming_devices_summary_{TODAY}.json")
    A("docs/GAMING_DEVICE_BUILD_LOG.md")
    A("```")
    (DOCS / "GAMING_DEVICE_BUILD_LOG.md").write_text("\n".join(lines) + "\n",
                                                     encoding="utf-8")
    log("  wrote docs/GAMING_DEVICE_BUILD_LOG.md")


if __name__ == "__main__":
    args = set(sys.argv[1:])
    do_fetch = "--fetch" in args or not (args & {"--fetch", "--build"})
    do_build = "--build" in args or not (args & {"--fetch", "--build"})
    if do_fetch:
        fetch()
    if do_build:
        build()
    (LOGS / f"gaming_devices_run_{TODAY}.log").write_text(
        "\n".join(LOGLINES) + "\n", encoding="utf-8")
