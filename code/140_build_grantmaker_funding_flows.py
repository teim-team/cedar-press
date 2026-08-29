#!/usr/bin/env python3
"""140_build_grantmaker_funding_flows.py -- the FUNDER channel, tested.

=== THE HYPOTHESIS ===

An earlier build (`code/139_build_litigation_positions.py`) tested whether the
Hoover Institution and George Mason University took INSTITUTIONAL actions
against ICWA.  They did not: both appear in `native_issue_litigation_positions
.csv` only as `B_AFFILIATED_INDIVIDUAL` -- a scholar signed a brief -- and
never as `C_INSTITUTIONAL_ACTION`.  That hypothesis failed.

The refined claim is about MONEY, not position: that the same foundations
funding the anti-ICWA litigators (Goldwater, Cato, Texas Public Policy
Foundation, Pacific Legal Foundation, New Civil Liberties Alliance, Project on
Fair Representation) also fund Hoover and Mercatus.

**This script tests that claim.  A clean negative is a valid result and is
reported as such.**  Nothing here is written to confirm it.

=== WHY THE EXISTING DATA COULD NOT ANSWER IT ===

`data/clean/np_schedule_i_grants.csv` holds 58,685 rows, but only from the 628
filers scripts 99 and 112 had already cached -- Native-connected nonprofits and
their grantees.  A conservative foundation is absent from that file BY
CONSTRUCTION.  Absence there is absence in a SAMPLE, not in the world.  So this
build pulls the GRANTMAKERS' OWN returns.

=== THE THREE HARD LIMITS.  THEY ARE RECORDED, NOT WORKED AROUND. ===

**1. The Hoover Institution does not file a Form 990.**  It is a unit of
Stanford University; grants to it are filed as grants to "The Board of Trustees
of the Leland Stanford Junior University" (EIN 94-1156365) and are
indistinguishable from a grant to the medical school, the physics department or
the athletics programme -- UNLESS the grant PURPOSE names the unit.  Verified
in this build: a search of the full IRS EO BMF (1,957,340 organisations) for
"HOOVER INSTITUTION" returns **zero** rows.  Every row therefore carries
`recipient_unit_identified`, and where the purpose does not name Hoover the
answer is `STANFORD_UNIT_NOT_IDENTIFIED` -- which may NEVER be read as money
reaching Hoover.  The same applies to the George Mason University Foundation,
which receives for the whole university including the Scalia Law School.

**2. DonorsTrust and Donors Capital Fund are donor-advised funds.**  They
anonymise the original donor BY DESIGN: the grant is legally the fund's, and
the person who chose the recipient is not disclosed on any return.  A
DonorsTrust grant proves money moved through, never who moved it.  This is a
hard wall.  `funder_is_donor_advised_fund` is 1 on those rows and the caveat is
on every one of them.

**3. A shared funder is NOT a shared position.**  Every row is
`cedar_domain.EvidenceClass.FUNDER_ACTIVITY`, whose
`carries_institutional_position` is False.  Two organisations funded by one
foundation have not thereby adopted each other's positions.  `row_caveat` says
so verbatim on every row, and the overlap matrix repeats it.

=== TECHNICAL ROUTE -- THE SAME ONE SCRIPT 132 USED ===

IRS e-file XML via HTTP RANGE READS into the published ZIP archives
(`code/99_build_earmarks_and_schedc.py::HttpRangeFile`).  The bulk year
archives are 1-2 GB each and free disk is ~4.5 GB, so downloading them is not
merely wasteful, it is impossible.  Range reads pull the ZIP central directory
and then only the members we want.  A 2 GB disk floor is checked before every
write.

Two schemas, not one:
  * **Form 990 Schedule I Part II** -- `RecipientTable`, and it CARRIES THE
    RECIPIENT EIN.  Public charities: DonorsTrust, Donors Capital Fund,
    Stand Together Trust.
  * **Form 990-PF Part XV** -- `GrantOrContributionPdDurYrGrp`, and it carries
    NO EIN.  The form does not ask for one.  Recipient identification on a
    990-PF is therefore BY NAME ONLY, which is exactly the condition AGENTS.md
    warns about.  Guarded phrase matching is used, single-token matches are
    refused, and `recipient_match_basis` states which leg was available.

Coverage: mandatory e-filing arrived with the Taxpayer First Act.  Paper filers
2011-2018 are ABSENT from the XML entirely, and the IRS e-file index begins at
submission year 2017.  A funder with no return in a year may simply have filed
on paper.  **Never read absence as "did not fund."**

Steps:
    eins      resolve funder/recipient EINs against the full BMF already on disk
    index     stream the IRS e-file index CSVs, filter to our EINs and names
    xml       range-read the return XMLs out of the published ZIP archives
    parse     both schemas -> data/clean/grantmaker_funding_flows.csv
    overlap   the matrix: who funded BOTH sides, and how much
    coverage  data/clean/grantmaker_funding_coverage.csv
    report    logs/140_build_report_<date>.txt
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import shutil
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cedar_domain import EvidenceClass, NAME_TRAPS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "code"
CLEAN = ROOT / "data" / "clean"
RAW = ROOT / "data" / "raw" / "external" / "irs990_grantmakers"
XMLDIR = RAW / "xml"
BMF_DIR = ROOT / "data" / "raw" / "external" / "irs990" / "bmf_full_2026-08-12"
SCHEDC_RAW = ROOT / "data" / "raw" / "external" / "irs990_schedc"
GRANTEE_RAW = ROOT / "data" / "raw" / "external" / "irs990_grantee"
REVIEW = ROOT / "review"
LOGS = ROOT / "logs"
DOCS = ROOT / "docs"

TODAY = date.today().isoformat()
SCRIPT = "code/140_build_grantmaker_funding_flows.py"
INDEX_URL = "https://apps.irs.gov/pub/epostcard/990/xml/{y}/index_{y}.csv"
INDEX_YEARS = list(range(2017, 2027))
IRS_DOWNLOAD_PAGE = ("https://www.irs.gov/charities-non-profits/"
                     "form-990-series-downloads")
BMF_PAGE = ("https://www.irs.gov/charities-non-profits/"
            "exempt-organizations-business-master-file-extract-eo-bmf")
DISK_FLOOR_GB = 2.0

SHARED_FUNDER_CAVEAT = (
    "A shared funder is not a shared position. This row records that a "
    "foundation made a grant; it does not state that the recipient holds, "
    "endorses or is aware of any position taken by any other grantee of the "
    "same foundation. EvidenceClass.FUNDER_ACTIVITY does not carry an "
    "institutional position."
)
DAF_CAVEAT = (
    "The filer is a donor-advised fund. It anonymises the original donor by "
    "design: the grant is legally the fund's own and no return discloses who "
    "advised it. This row proves money moved through the fund, never who chose "
    "the recipient."
)
STANFORD_CAVEAT = (
    "The Hoover Institution is a unit of Stanford University and files no Form "
    "990 of its own; it is absent from the full IRS EO BMF. A grant to "
    "Stanford whose purpose does not name Hoover CANNOT be claimed to have "
    "reached Hoover."
)
GMU_CAVEAT = (
    "The George Mason University Foundation receives on behalf of the whole "
    "university. A grant whose purpose does not name Mercatus or the Scalia "
    "Law School CANNOT be attributed to either."
)

# ---------------------------------------------------------------------------
# TARGETS.  Every EIN below was resolved against the full IRS EO BMF in this
# build (step `eins`), not assumed.  The BMF row is written out as evidence.
# ---------------------------------------------------------------------------

FUNDERS = [
    # key, canonical name, ein (BMF-resolved), expected form, DAF?, index-name regex
    ("BRADLEY",   "LYNDE AND HARRY BRADLEY FOUNDATION INC", "396037928", "990PF", 0,
     r"LYNDE AND HARRY BRADLEY"),
    ("SCAIFE",    "SARAH SCAIFE FOUNDATION INC",            "251113452", "990PF", 0,
     r"SARAH SCAIFE FOUNDATION"),
    ("SEARLE",    "SEARLE FREEDOM TRUST",                   "367244615", "990PF", 0,
     r"SEARLE FREEDOM TRUST"),
    ("DONORSTRUST", "DONORS TRUST INC",                     "522166327", "990",   1,
     r"DONORS ?TRUST"),
    ("DONORSCAPITAL", "DONORS CAPITAL FUND INC",            "541934032", "990",   1,
     r"DONORS CAPITAL FUND"),
    ("KOCHFDN",   "CHARLES KOCH FOUNDATION",                "480918408", "990PF", 0,
     r"CHARLES KOCH FOUNDATION"),
    ("KOCHFDN2",  "CHARLES KOCH FOUNDATION II",             "854058882", "990PF", 0,
     r"CHARLES KOCH FOUNDATION II"),
    ("KOCHINST",  "CHARLES KOCH INSTITUTE (now STAND TOGETHER TRUST)", "", "990", 0,
     r"CHARLES KOCH INSTITUTE|STAND TOGETHER TRUST"),
    ("UIHLEIN",   "ED UIHLEIN FAMILY FOUNDATION",           "205723621", "990PF", 0,
     r"ED UIHLEIN FAMILY"),
    ("SPENCER",   "DIANA DAVIS SPENCER FOUNDATION",         "203672969", "990PF", 0,
     r"DIANA DAVIS SPENCER"),
    ("TEMPLETON", "JOHN TEMPLETON FOUNDATION",              "621322826", "990PF", 0,
     r"JOHN TEMPLETON FOUNDATION"),
    ("COORS",     "ADOLPH COORS FOUNDATION",                "510172279", "990PF", 0,
     r"ADOLPH COORS FOUNDATION"),
    ("JM",        "THE JM FOUNDATION",                      "", "990PF", 0,
     r"^(THE )?J\.? ?M\.? FOUNDATION$"),
    ("KIRBY",     "F M KIRBY FOUNDATION INC",               "516017929", "990PF", 0,
     r"F\.? ?M\.? KIRBY FOUNDATION"),
]

# BMF name searches used in step `eins`.  Deliberately loose, because the point
# is to SEE the near-misses -- 32 "Bradley Foundation" rows, one of which is
# ours -- rather than to trust the first hit.
FUNDER_BMF_PROBES = {
    "BRADLEY": ["LYNDE AND HARRY BRADLEY"], "SCAIFE": ["SARAH SCAIFE"],
    "SEARLE": ["SEARLE FREEDOM"], "DONORSTRUST": ["DONORS TRUST"],
    "DONORSCAPITAL": ["DONORS CAPITAL FUND"],
    "KOCHFDN": ["CHARLES KOCH FOUNDATION"],
    "KOCHFDN2": ["CHARLES KOCH FOUNDATION II"],
    "KOCHINST": ["CHARLES KOCH INSTITUTE", "STAND TOGETHER TRUST"],
    "UIHLEIN": ["ED UIHLEIN FAMILY"], "SPENCER": ["DIANA DAVIS SPENCER"],
    "TEMPLETON": ["JOHN TEMPLETON FOUNDATION"],
    "COORS": ["ADOLPH COORS FOUNDATION"], "JM": ["JM FOUNDATION"],
    "KIRBY": ["F M KIRBY FOUNDATION", "FM KIRBY FOUNDATION"],
}

# Recipients.  `side` is NOT asserted here -- it is read from
# data/clean/native_issue_litigation_positions.csv (script 139) at build time,
# and a recipient with no documented position gets no side.
RECIPIENTS = [
    # key, canonical name, ein, aliases (phrases, matched whole)
    ("GOLDWATER", "BARRY GOLDWATER INSTITUTE FOR PUBLIC POLICY RESEARCH",
     "860597661",
     ["GOLDWATER INSTITUTE", "BARRY GOLDWATER INSTITUTE",
      "SCHARF NORTON CENTER", "SCHARF-NORTON CENTER",
      "GOLDWATER INSTITUTE FOR PUBLIC POLICY"]),
    ("CATO", "CATO INSTITUTE", "237432162", ["CATO INSTITUTE"]),
    ("TPPF", "TEXAS PUBLIC POLICY FOUNDATION", "742524057",
     ["TEXAS PUBLIC POLICY FOUNDATION"]),
    ("PLF", "PACIFIC LEGAL FOUNDATION", "942197343",
     ["PACIFIC LEGAL FOUNDATION"]),
    ("NCLA", "NEW CIVIL LIBERTIES ALLIANCE", "813474290",
     ["NEW CIVIL LIBERTIES ALLIANCE"]),
    ("POFR", "PROJECT ON FAIR REPRESENTATION INC", "472593047",
     ["PROJECT ON FAIR REPRESENTATION"]),
    ("MERCATUS", "MERCATUS CENTER INC", "541436224",
     ["MERCATUS CENTER", "MERCATUS"]),
    # The Institute for Humane Studies is a SEPARATE 501(c)(3) (EIN
    # 94-1623852, BMF-confirmed) that is HOUSED at George Mason University.
    # Three grant rows name it as "INSTITUTE FOR HUMANE STUDIES GEORGE MASON
    # UNIVERSITY"; without its own key those rows key to the GMU Foundation,
    # which is a different legal person. It is listed BEFORE GMUF so the
    # longest-phrase rule cannot swallow it.
    ("IHS", "INSTITUTE FOR HUMANE STUDIES", "941623852",
     ["INSTITUTE FOR HUMANE STUDIES"]),
    ("GMUF", "GEORGE MASON UNIVERSITY FOUNDATION INC", "541603842",
     ["GEORGE MASON UNIVERSITY FOUNDATION", "GEORGE MASON UNIV FOUNDATION",
      "GMU FOUNDATION"]),
    # A grant filed to bare "George Mason University" names the STATE
    # UNIVERSITY, which is an instrumentality of Virginia and files no Form
    # 990. Whether the money legally landed at the university or at its
    # foundation is NOT established by the return, so it gets its own key
    # rather than being folded into the foundation's.
    ("GMU", "GEORGE MASON UNIVERSITY (state instrumentality; files no Form 990)",
     "", ["GEORGE MASON UNIVERSITY", "GEORGE MASON UNIV"]),
    ("GMU_INSTR", "THE GEORGE MASON UNIVERSITY INSTRUCTIONAL FOUNDATION INC",
     "546063258", ["GEORGE MASON UNIVERSITY INSTRUCTIONAL FOUNDATION"]),
    ("STANFORD", "THE BOARD OF TRUSTEES OF THE LELAND STANFORD JUNIOR UNIVERSITY",
     "941156365",
     ["STANFORD UNIVERSITY", "LELAND STANFORD JUNIOR UNIVERSITY",
      "BOARD OF TRUSTEES OF THE LELAND STANFORD", "STANFORD UNIV"]),
    # Hoover has no EIN.  The alias exists so a purpose or recipient string
    # that DOES name it is caught -- which is the only strong case there is.
    ("HOOVER_NAMED", "HOOVER INSTITUTION (a unit of Stanford University; files no 990)",
     "", ["HOOVER INSTITUTION", "HOOVER INSTITUTE"]),
]

RECIPIENT_BMF_PROBES = {
    "GOLDWATER": ["GOLDWATER INSTITUTE", "SCHARF"], "CATO": ["CATO INSTITUTE"],
    "TPPF": ["TEXAS PUBLIC POLICY"], "PLF": ["PACIFIC LEGAL FOUNDATION"],
    "NCLA": ["NEW CIVIL LIBERTIES"], "POFR": ["PROJECT ON FAIR REPRESENTATION"],
    "MERCATUS": ["MERCATUS"], "GMUF": ["GEORGE MASON UNIVERSITY FOUNDATION"],
    "GMU": ["GEORGE MASON UNIVERSITY"],
    "IHS": ["INSTITUTE FOR HUMANE STUDIES"],
    "GMU_INSTR": ["GEORGE MASON UNIVERSITY INSTRUCTIONAL"],
    "STANFORD": ["LELAND STANFORD JUNIOR UNIVERSITY"],
    "HOOVER_NAMED": ["HOOVER INSTITUTION"],
}

# ---------------------------------------------------------------------------
# NAME TRAPS CAUGHT LIVE IN THIS BUILD.  Discovering a funder by NAME in the
# IRS index is the only route to an organisation absent from the current BMF --
# and it is exactly the route that catches the wrong organisation.  Both of
# these were found by reading the FILED RETURN's own state and grant list, not
# by assuming.  They are excluded from the flows file and written to review/.
# ---------------------------------------------------------------------------

NAME_TRAP_EINS = {
    "384322070": (
        "JM", "JM FOUNDATION, Lafayette CALIFORNIA (BMF asset $2,276,472). A "
        "different organisation from the conservative JM Foundation (EIN "
        "13-6068340) named in the brief. Its four retrieved returns carry 0 "
        "and 1 grant rows and none names any target recipient."),
    "262515785": (
        "DONORSTRUST", "DONORS TRUST, NEBRASKA. A different organisation from "
        "DonorsTrust Inc of Alexandria VA (EIN 52-2166327). Its single "
        "retrieved return reports no grants at all."),
}

# Funder identities established from the FILED RETURN, for the two funders the
# current BMF does not carry under the name in the brief.
FUNDER_IDENTITY_NOTES = {
    "274967732": (
        "CHARLES KOCH INSTITUTE. Absent from the current IRS EO BMF under that "
        "name; the BMF carries EIN 27-4967732 as STAND TOGETHER FELLOWSHIP, "
        "Arlington VA. The filed returns name the filer CHARLES KOCH INSTITUTE "
        "through tax year 2024 at a Virginia address, which is what "
        "establishes the identity here -- the rename, not a name match."),
    "136068340": (
        "THE JM FOUNDATION. Absent from the current IRS EO BMF. Discovered by "
        "taxpayer name in the IRS e-file index; the filed 990-PF is a private "
        "foundation whose Part XV names Hoover Institution and other "
        "movement recipients, which is what distinguishes it from the "
        "California organisation of the same name (see NAME_TRAP_EINS)."),
    "854058882": (
        "CHARLES KOCH FOUNDATION II in the BMF; the filed returns name the "
        "filer CHARLES KOCH CHARITABLE FUND. Same EIN, two names."),
}

# Units whose name inside a purpose string upgrades `recipient_unit_identified`.
UNIT_PATTERNS = {
    "STANFORD": [(r"HOOVER", "HOOVER_NAMED_IN_TEXT")],
    "GMUF": [(r"MERCATUS", "MERCATUS_NAMED_IN_TEXT"),
             (r"SCALIA LAW|ANTONIN SCALIA|SCHOOL OF LAW|LAW ?& ?ECONOMICS"
              r"|LAW AND ECONOMICS", "GMU_LAW_NAMED_IN_TEXT")],
    "GMU": [(r"MERCATUS", "MERCATUS_NAMED_IN_TEXT"),
            (r"SCALIA LAW|ANTONIN SCALIA|SCHOOL OF LAW|LAW ?& ?ECONOMICS"
             r"|LAW AND ECONOMICS", "GMU_LAW_NAMED_IN_TEXT")],
    "GMU_INSTR": [(r"MERCATUS", "MERCATUS_NAMED_IN_TEXT")],
}

# New traps measured in THIS build.  Each is a single token that carries a
# whole match on the containment path and must never link on its own.
NEW_NAME_TRAPS = {
    "hoover",     # HOOVER-FOSTER RAC (Oakland); Herbert Hoover Presidential Fdn
    "bradley",    # BRADLEY UNIVERSITY, Peoria IL; 31 other "Bradley Foundation"s
    "stanford",   # Stanford Health Care; Stanford, CT; Stanford, KY
    "goldwater",  # Goldwater Memorial Hospital, NYC; Barry Goldwater HS
    "mason",      # Mason City; George Mason Bank; Mason County
    "cato",       # Cato, NY; Cato Elementary
    "koch",       # Koch Foundation Inc (Evansville IN) is a Catholic funder
    "scaife",     # Scaife Family Foundation is a DIFFERENT foundation
    "templeton",  # Templeton, MA/CA/IA -- 100 BMF hits, one is ours
    "coors", "kirby", "searle", "uihlein", "spencer",
}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def log(m):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {m}", flush=True)


def read_csv(p, encoding="utf-8-sig"):
    p = Path(p)
    if not p.exists():
        return []
    with p.open(newline="", encoding=encoding, errors="replace") as fh:
        return list(csv.DictReader(fh))


def write_csv(p, rows, fields=None):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0].keys()) if rows else []
    tmp = p.with_suffix(p.suffix + ".part")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    tmp.replace(p)


def free_gb():
    return shutil.disk_usage(str(ROOT)).free / 1e9


def guard_disk(where=""):
    g = free_gb()
    if g < DISK_FLOOR_GB:
        raise RuntimeError(f"DISK FLOOR: {g:.2f} GB free at {where}; "
                           f"floor is {DISK_FLOOR_GB} GB. Stopping.")
    return g


def ein9(v):
    v = re.sub(r"\D", "", str(v or ""))
    return v.zfill(9) if v else ""


def numf(v):
    if v is None:
        return None
    s = re.sub(r"[^0-9.\-]", "", str(v))
    try:
        return float(s) if s not in ("", "-", ".") else None
    except ValueError:
        return None


def norm_name(s):
    s = (s or "").upper()
    s = s.replace("&", " AND ")
    s = re.sub(r"[^A-Z0-9 ]+", " ", s)
    s = re.sub(r"\b(INC|INCORPORATED|CORP|CORPORATION|LLC|LTD|CO|THE|A|OF|"
               r"FDN|FDTN)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def m99():
    """Import HttpRangeFile / Fetcher / zip_manifest from script 99.

    Standing rule 8: never re-implement a shared component.  99 owns the range
    reader; 112 imports it the same way.
    """
    import importlib.util
    p = CODE / "99_build_earmarks_and_schedc.py"
    spec = importlib.util.spec_from_file_location("m99", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# --- host lock (PULL_DISCIPLINE: one poller per host, ever) -----------------

def _pid_alive(pid):
    import subprocess
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"(Get-CimInstance Win32_Process -Filter 'ProcessId={int(pid)}')"
             ".ProcessId"],
            capture_output=True, text=True, timeout=60).stdout.strip()
        return out.isdigit()
    except Exception:
        return False


def claim_host(host, note):
    LOGS.mkdir(parents=True, exist_ok=True)
    p = LOGS / f"_HOSTLOCK_{host}.json"
    if p.exists():
        try:
            j = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            j = {}
        if j.get("active") and _pid_alive(j.get("pid", -1)):
            j.setdefault("queue", []).append(
                {"script": SCRIPT, "note": note, "queued": TODAY})
            p.write_text(json.dumps(j, indent=1), encoding="utf-8")
            log(f"  host {host} held by pid {j.get('pid')} "
                f"({j.get('script')}); QUEUED and exiting this step")
            return False
    p.write_text(json.dumps({
        "host": host, "pid": os.getpid(), "script": SCRIPT,
        "started": datetime.now(timezone.utc).isoformat(), "active": True,
        "queue": [], "policy": "sequential, >=1.0s gap index, >=0.35s ranges",
        "note": note}, indent=1), encoding="utf-8")
    return True


def release_host(host, note=""):
    p = LOGS / f"_HOSTLOCK_{host}.json"
    try:
        j = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return
    j["active"] = False
    j["released"] = datetime.now(timezone.utc).isoformat()
    if note:
        j["note"] = note
    p.write_text(json.dumps(j, indent=1), encoding="utf-8")


# ---------------------------------------------------------------------------
# STEP eins -- resolve every EIN against the FULL BMF already on disk
# ---------------------------------------------------------------------------

EIN_FILE = RAW / "_ein_resolution.csv"


def step_eins():
    log("=== 140 eins (full IRS EO BMF, already on disk; zero network) ===")
    probes = []
    for k, terms in FUNDER_BMF_PROBES.items():
        for t in terms:
            probes.append(("funder", k, t.upper()))
    for k, terms in RECIPIENT_BMF_PROBES.items():
        for t in terms:
            probes.append(("recipient", k, t.upper()))

    hits = []
    n_bmf = 0
    for f in sorted(BMF_DIR.glob("eo*.csv")):
        with f.open(newline="", encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh):
                n_bmf += 1
                nm = (r.get("NAME") or "").upper()
                for role, key, term in probes:
                    if term in nm:
                        hits.append({
                            "role": role, "target_key": key, "probe_term": term,
                            "bmf_ein": ein9(r.get("EIN")),
                            "bmf_name": r.get("NAME", ""),
                            "bmf_city": r.get("CITY", ""),
                            "bmf_state": r.get("STATE", ""),
                            "bmf_subsection": r.get("SUBSECTION", ""),
                            "bmf_foundation_cd": r.get("FOUNDATION", ""),
                            "bmf_filing_req_cd": r.get("FILING_REQ_CD", ""),
                            "bmf_pf_filing_req_cd": r.get("PF_FILING_REQ_CD", ""),
                            "bmf_asset_amt": r.get("ASSET_AMT", ""),
                            "bmf_ntee_cd": r.get("NTEE_CD", ""),
                            "bmf_source": BMF_PAGE,
                            "bmf_local_dir": str(BMF_DIR.relative_to(ROOT)),
                            "fetched_date": "2026-08-12",
                        })
    log(f"  BMF rows scanned {n_bmf:,}; probe hits {len(hits):,}")

    want = {}
    for k, name, ein, form, daf, _rx in FUNDERS:
        want[("funder", k)] = (name, ein)
    for k, name, ein, _al in RECIPIENTS:
        want[("recipient", k)] = (name, ein)
    for h in hits:
        nm, ein = want.get((h["role"], h["target_key"]), ("", ""))
        h["is_declared_target"] = "1" if ein and h["bmf_ein"] == ein else "0"
        h["declared_target_name"] = nm
    write_csv(EIN_FILE, hits)
    log(f"  wrote {EIN_FILE.relative_to(ROOT)}")

    # Report unresolved declared targets -- these become an explicit coverage
    # statement, never a silent gap.
    for (role, k), (nm, ein) in sorted(want.items()):
        if not ein:
            log(f"  NO BMF EIN DECLARED: {role} {k} ({nm}) "
                f"-- discovery is by name in the e-file index")
            continue
        got = [h for h in hits if h["bmf_ein"] == ein]
        mark = "OK " if got else "!! NOT IN BMF"
        log(f"  {mark} {role:9s} {k:12s} {ein} {nm[:48]}")
    return hits


# ---------------------------------------------------------------------------
# STEP index -- the IRS e-file index, streamed, never stored whole
# ---------------------------------------------------------------------------

IDX_FILE = RAW / "_index_targets.csv"
IDX_FIELDS = ["index_year", "ein", "object_id", "return_type", "tax_period",
              "taxpayer_name", "sub_date", "dln", "match_basis", "index_url",
              "fetched_date"]


def step_index(years=None):
    log("=== 140 index ===")
    RAW.mkdir(parents=True, exist_ok=True)
    eins = {f[2] for f in FUNDERS if f[2]}
    rxs = [(f[0], re.compile(f[5])) for f in FUNDERS]
    log(f"  funder EIN filter {len(eins)}; name regexes {len(rxs)}")

    have = read_csv(IDX_FILE)
    done = {int(r["index_year"]) for r in have}
    todo = [y for y in (years or INDEX_YEARS) if y not in done]
    for y in sorted(done):
        log(f"  {y}: cached ({sum(1 for r in have if int(r['index_year'])==y)} rows)")
    if not todo:
        return have
    if not claim_host("apps.irs.gov", "IRS 990 e-file index CSVs (grantmakers)"):
        return have

    M = m99()
    F = M.Fetcher(gap=1.0)
    rows = list(have)
    try:
        for y in todo:
            url = INDEX_URL.format(y=y)
            t0 = time.time()
            status, body = F.get(url, timeout=900)
            if status != 200 or not body:
                # A 0 is a transport fact about the moment, not about the year.
                log(f"  {y}: HTTP {status} -- SKIPPED and recorded, not smoothed")
                continue
            text = body.decode("utf-8", "replace")
            del body
            kept = total = 0
            for rec in csv.DictReader(io.StringIO(text)):
                total += 1
                ein = ein9(rec.get("EIN"))
                nm = (rec.get("TAXPAYER_NAME") or "").upper()
                basis = ""
                if ein in eins:
                    basis = "bmf_resolved_ein"
                else:
                    for k, rx in rxs:
                        if rx.search(nm):
                            basis = f"index_taxpayer_name_match:{k}"
                            break
                if not basis:
                    continue
                rows.append({
                    "index_year": y, "ein": ein,
                    "object_id": (rec.get("OBJECT_ID") or "").strip(),
                    "return_type": (rec.get("RETURN_TYPE") or "").strip(),
                    "tax_period": (rec.get("TAX_PERIOD") or "").strip(),
                    "taxpayer_name": (rec.get("TAXPAYER_NAME") or "").strip(),
                    "sub_date": (rec.get("SUB_DATE") or "").strip(),
                    "dln": (rec.get("DLN") or "").strip(),
                    "match_basis": basis, "index_url": url,
                    "fetched_date": TODAY})
                kept += 1
            log(f"  {y}: {total:,} index rows -> {kept} ours "
                f"({time.time()-t0:.0f}s, {len(text)/1e6:.0f}MB streamed)")
            del text
            write_csv(IDX_FILE, rows, IDX_FIELDS)
            if F.blocked:
                log("  !! host blocked; checkpoint written, stopping")
                break
    finally:
        write_csv(IDX_FILE, rows, IDX_FIELDS)
        release_host("apps.irs.gov", "grantmaker index pull complete")
    log(f"  wrote {IDX_FILE.relative_to(ROOT)} ({len(rows)} rows)")
    return rows


# ---------------------------------------------------------------------------
# STEP xml -- range reads
# ---------------------------------------------------------------------------

EXTRA_MANIFEST = RAW / "_zip_manifest_extra.csv"


def step_probe():
    """The IRS download page no longer LISTS every archive that EXISTS.

    Its cached manifest carries one archive each for 2021 and 2022 and seven
    for 2017 -- and 11 of our returns have a 2021 tax period, so they sit in
    archives the page does not mention.  Script 112 hit the same wall and
    probe-verified `2022_TEOS_XML_02A.zip` by hand.

    This step probes the two published naming patterns with HEAD and keeps only
    what answers **HTTP 200 with a real Content-Length**.  A 404 stops that
    year's walk.  Nothing is inferred from a URL looking plausible -- AGENTS.md:
    check the HTTP status, not the file.
    """
    log("=== 140 probe (extra archives the IRS page does not list) ===")
    RAW.mkdir(parents=True, exist_ok=True)
    known = {r["url"] for r in read_csv(EXTRA_MANIFEST)}
    M = m99()
    F = M.Fetcher(gap=0.5)
    known |= {z["url"] for z in M.zip_manifest(F)}
    known |= {r["url"] for r in read_csv(GRANTEE_RAW / "_zip_manifest_extra.csv")}
    rows = read_csv(EXTRA_MANIFEST)
    rows += [r for r in read_csv(GRANTEE_RAW / "_zip_manifest_extra.csv")]
    if not claim_host("apps.irs.gov", "HEAD probes for unlisted 990 archives"):
        return rows
    try:
        for y in ("2017", "2018", "2019", "2020", "2021", "2022", "2023",
                  "2024", "2025", "2026"):
            cands = []
            if int(y) <= 2020:
                cands = [f"download990xml_{y}_{n}.zip" for n in range(1, 16)]
            else:
                for n in range(1, 20):
                    for a in "ABCD":
                        cands.append(f"{y}_TEOS_XML_{n:02d}{a}.zip")
            misses = 0
            for name in cands:
                url = (f"https://apps.irs.gov/pub/epostcard/990/xml/{y}/{name}")
                if url in known:
                    misses = 0
                    continue
                try:
                    req = urllib.request.Request(
                        url, headers={"User-Agent": "cedar-press/140"},
                        method="HEAD")
                    with urllib.request.urlopen(req, timeout=60) as r:
                        cl = r.headers.get("Content-Length")
                        if r.status == 200 and cl:
                            rows.append({
                                "year": y, "name": name, "url": url,
                                "content_length": cl,
                                "basis": "probe_verified_http_200_"
                                         "not_page_listed",
                                "source_url": IRS_DOWNLOAD_PAGE,
                                "fetched_date": TODAY})
                            known.add(url)
                            log(f"  + {y}/{name}  {int(cl)/1e9:.2f} GB")
                            misses = 0
                        else:
                            misses += 1
                except Exception:
                    misses += 1
                time.sleep(0.4)
                if misses >= 6:
                    break
    finally:
        release_host("apps.irs.gov", "archive probe complete")
    seen, out = set(), []
    for r in rows:
        if r["url"] in seen:
            continue
        seen.add(r["url"])
        out.append(r)
    write_csv(EXTRA_MANIFEST, out)
    log(f"  wrote {EXTRA_MANIFEST.relative_to(ROOT)} ({len(out)} extra archives)")
    return out


FLOG = RAW / "_xml_fetch_log.csv"
FLOG_FIELDS = ["object_id", "ein", "taxpayer_name", "tax_period",
               "return_type", "url", "zip_member", "bytes", "http_status",
               "fetched_date"]


def step_xml(max_minutes=120):
    log("=== 140 xml (HTTP range reads; NO bulk archive download) ===")
    idx = read_csv(IDX_FILE)
    if not idx:
        log("  no index; run --steps index first")
        return
    XMLDIR.mkdir(parents=True, exist_ok=True)

    # Reuse anything scripts 99/112 already retrieved.  object_id is the
    # return's primary key, so it cannot be a different document.
    reused = 0
    for r in idx:
        oid = r["object_id"]
        if (XMLDIR / f"{oid}.xml").exists():
            continue
        for d in (SCHEDC_RAW / "xml", GRANTEE_RAW / "xml"):
            if (d / f"{oid}.xml").exists():
                shutil.copyfile(d / f"{oid}.xml", XMLDIR / f"{oid}.xml")
                reused += 1
                break
    log(f"  reused from existing local caches: {reused}")

    # Form 990-T is the exempt organisation BUSINESS INCOME tax return. It has
    # no Schedule I and no Part XV -- there is no grants list on it to read.
    # Excluding it is a statement about the FORM, not about the filer, and it
    # is recorded in the coverage file rather than silently dropped.
    GRANTS_FORMS = {"990", "990PF", "990EZ", "990PR"}
    skipped_990t = [r for r in idx if r["return_type"] not in GRANTS_FORMS]
    log(f"  excluded {len(skipped_990t)} Form 990-T returns "
        f"(no grants schedule exists on that form)")
    idx = [r for r in idx if r["return_type"] in GRANTS_FORMS]

    want = {r["object_id"]: r for r in idx
            if not (XMLDIR / f"{r['object_id']}.xml").exists()}
    log(f"  returns indexed {len(idx)}; to fetch {len(want)}")
    if not want:
        return
    if not claim_host("apps.irs.gov",
                      "IRS 990 return XML via ZIP range reads (grantmakers)"):
        return

    seen = {r["object_id"]: r for r in read_csv(FLOG)}
    M = m99()
    F = M.Fetcher(gap=0.35)
    deadline = time.time() + max_minutes * 60
    import zipfile
    try:
        zips = list(M.zip_manifest(F)) + read_csv(EXTRA_MANIFEST)
        years = sorted({r["index_year"] for r in want.values()})
        todo = [z for z in zips if z["year"] in years]
        # Open the archives of the years we still need most first.
        need_by_year = Counter(r["index_year"] for r in want.values())
        todo.sort(key=lambda z: (-need_by_year[z["year"]], z["year"], z["name"]))
        log(f"  archives to open: {len(todo)} across years {years}")
        n_ok = 0
        for z in todo:
            if not want:
                break
            if time.time() > deadline:
                log("  !! wall-clock deadline reached; checkpoint written")
                break
            guard_disk("before archive " + z["name"])
            try:
                hf = M.HttpRangeFile(z["url"], F)
                zf = zipfile.ZipFile(hf)
                names = zf.namelist()
            except Exception as e:
                log(f"  !! {z['name']}: cannot open ({type(e).__name__} {e})")
                continue
            bymember = {}
            for nm in names:
                oid = nm.rsplit("/", 1)[-1].split("_")[0]
                if oid in want:
                    bymember[oid] = nm
            got = 0
            for oid, nm in bymember.items():
                guard_disk("before writing " + oid)
                try:
                    body = zf.read(nm)
                except Exception as e:
                    # DEFLATE64 (method 9) raises here on 6 of the 81 archives.
                    log(f"    !! {oid}: {type(e).__name__} {str(e)[:60]}")
                    continue
                tmp = XMLDIR / f"{oid}.xml.part"
                tmp.write_bytes(body)
                tmp.replace(XMLDIR / f"{oid}.xml")
                r = want.pop(oid)
                got += 1
                n_ok += 1
                seen[oid] = {"object_id": oid, "ein": r["ein"],
                             "taxpayer_name": r["taxpayer_name"],
                             "tax_period": r["tax_period"],
                             "return_type": r["return_type"],
                             "url": z["url"], "zip_member": nm,
                             "bytes": len(body), "http_status": 200,
                             "fetched_date": TODAY}
            log(f"  {z['name']}: {len(names):,} members, {len(bymember)} ours, "
                f"got {got} ({hf.bytes_read/1e6:.0f}MB read; "
                f"{len(want)} still wanted; {free_gb():.2f}GB free)")
            write_csv(FLOG, [seen[k] for k in sorted(seen)], FLOG_FIELDS)
            if F.blocked:
                log("  !! host blocked; stopping (checkpoint written)")
                break
        for oid, r in want.items():
            seen.setdefault(oid, {
                "object_id": oid, "ein": r["ein"],
                "taxpayer_name": r["taxpayer_name"],
                "tax_period": r["tax_period"], "return_type": r["return_type"],
                "url": "", "zip_member": "", "bytes": "",
                "http_status": "indexed_but_not_retrieved",
                "fetched_date": TODAY})
        write_csv(FLOG, [seen[k] for k in sorted(seen)], FLOG_FIELDS)
        log(f"  extracted {n_ok}; still missing {len(want)}; "
            f"fetcher stats {dict(F.stats)}")
    finally:
        release_host("apps.irs.gov", "grantmaker return retrieval complete")


def step_deflate64():
    """Recover returns CPython's `zipfile` cannot decompress.

    Four of the archives holding our returns are written with DEFLATE64
    (compression method 9).  Range reads do not help -- the bytes arrive fine,
    the DECODER is missing.  Those archives are downloaded whole, opened with
    the system 7-Zip, the wanted members extracted, and **the archive deleted
    before the next one starts**, so peak disk is one archive (0.37-0.50 GB
    here) rather than all four.  The disk floor is checked before each
    download.  If 7-Zip is absent the step does nothing and the affected rows
    keep the honest basis `indexed_but_not_retrieved`.
    """
    import subprocess
    log("=== 140 deflate64 ===")
    sevenzip = shutil.which("7z") or r"C:\Program Files\7-Zip\7z.exe"
    if not Path(sevenzip).exists():
        log("  7-Zip not found; DEFLATE64 archives unreadable. Skipping.")
        return
    idx = [r for r in read_csv(IDX_FILE)
           if r["return_type"] in ("990", "990PF", "990EZ", "990PR")]
    want = {r["object_id"]: r for r in idx
            if not (XMLDIR / f"{r['object_id']}.xml").exists()}
    log(f"  still missing: {len(want)} returns")
    if not want:
        return
    M = m99()
    zips = {z["name"]: z for z in list(M.zip_manifest(M.Fetcher(gap=0.3)))
            + read_csv(EXTRA_MANIFEST)}
    # Measured method-9 archives (script 99/112 found the same six).
    targets = ["2020_TEOS_XML_CT1.zip", "2025_TEOS_XML_05A.zip",
               "2025_TEOS_XML_05B.zip", "2025_TEOS_XML_11B.zip",
               "2026_TEOS_XML_05A.zip", "2026_TEOS_XML_05B.zip"]
    need_years = {r["index_year"] for r in want.values()}
    if not claim_host("apps.irs.gov", "DEFLATE64 archive download (grantmakers)"):
        return
    seen = {r["object_id"]: r for r in read_csv(FLOG)}
    tmp = RAW / "_tmp"
    tmp.mkdir(exist_ok=True)
    got = 0
    try:
        for name in targets:
            z = zips.get(name)
            if not z or not want or z["year"] not in need_years:
                continue
            guard_disk("before downloading " + name)
            if free_gb() < DISK_FLOOR_GB + 1.5:
                log(f"  refusing {name}: only {free_gb():.2f} GB free")
                continue
            local = tmp / name
            log(f"  downloading {name} ...")
            try:
                req = urllib.request.Request(
                    z["url"], headers={"User-Agent": "cedar-press/140"})
                with urllib.request.urlopen(req, timeout=1800) as r, \
                        open(local, "wb") as fh:
                    shutil.copyfileobj(r, fh, 1 << 20)
            except Exception as e:
                log(f"    !! download failed: {type(e).__name__} {e}")
                local.unlink(missing_ok=True)
                continue
            out = tmp / "x"
            shutil.rmtree(out, ignore_errors=True)
            out.mkdir()
            listing = subprocess.run([sevenzip, "l", "-ba", "-slt", str(local)],
                                     capture_output=True, text=True).stdout
            members = re.findall(r"^Path = (.+\.xml)$", listing, re.M)
            mine = [mm for mm in members
                    if mm.rsplit("\\", 1)[-1].rsplit("/", 1)[-1].split("_")[0]
                    in want]
            log(f"    {len(members):,} members, {len(mine)} ours")
            for chunk in [mine[i:i + 200] for i in range(0, len(mine), 200)]:
                subprocess.run([sevenzip, "e", "-y", f"-o{out}", str(local)]
                               + chunk, capture_output=True, text=True)
            for f in out.glob("*.xml"):
                oid = f.name.split("_")[0]
                if oid in want:
                    shutil.move(str(f), str(XMLDIR / f"{oid}.xml"))
                    r = want.pop(oid)
                    got += 1
                    seen[oid] = {
                        "object_id": oid, "ein": r["ein"],
                        "taxpayer_name": r["taxpayer_name"],
                        "tax_period": r["tax_period"],
                        "return_type": r["return_type"], "url": z["url"],
                        "zip_member": f.name, "bytes": "",
                        "http_status": 200, "fetched_date": TODAY}
            shutil.rmtree(out, ignore_errors=True)
            local.unlink(missing_ok=True)
            log(f"    recovered {got} so far; {len(want)} still missing; "
                f"{free_gb():.2f} GB free")
        write_csv(FLOG, [seen[k] for k in sorted(seen)], FLOG_FIELDS)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        release_host("apps.irs.gov", "DEFLATE64 recovery complete")
    log(f"  recovered {got} returns from DEFLATE64 archives")


# ---------------------------------------------------------------------------
# PARSE -- two schemas
# ---------------------------------------------------------------------------

def _tag(el):
    t = el.tag
    return t.split("}", 1)[1] if "}" in t else t


def _name2(el):
    if el is None:
        return ""
    n1 = n2 = ""
    for c in el.iter():
        t = _tag(c)
        if t in ("BusinessNameLine1Txt", "BusinessNameLine1") and not n1 and c.text:
            n1 = c.text.strip()
        elif t in ("BusinessNameLine2Txt", "BusinessNameLine2") and not n2 and c.text:
            n2 = c.text.strip()
    return (n1 + " " + n2).strip()


def _addr(el):
    city = st = ""
    if el is None:
        return city, st
    for a in el.iter():
        t = _tag(a)
        if t in ("CityNm", "City") and not city and a.text:
            city = a.text.strip()
        elif t in ("StateAbbreviationCd", "State", "ProvinceOrStateNm") \
                and not st and a.text:
            st = a.text.strip()
    return city, st


def parse_return(path):
    """Returns (header, [grant rows]).  Handles Form 990 Schedule I Part II
    and Form 990-PF Part XV, which are DIFFERENT SCHEMAS."""
    try:
        root = ET.parse(path).getroot()
    except Exception as e:
        return None, [], type(e).__name__

    hdr = si = pf = None
    for el in root.iter():
        t = _tag(el)
        if t == "ReturnHeader" and hdr is None:
            hdr = el
        elif t == "IRS990ScheduleI" and si is None:
            si = el
        elif t == "IRS990PF" and pf is None:
            pf = el
    if hdr is None:
        return None, [], "no_return_header"

    filer = next((el for el in hdr.iter() if _tag(el) == "Filer"), None)
    f_ein = f_state = ""
    f_name = _name2(filer)
    if filer is not None:
        for el in filer.iter():
            t = _tag(el)
            if t == "EIN" and not f_ein and el.text:
                f_ein = el.text.strip()
            elif t in ("StateAbbreviationCd", "State") and not f_state and el.text:
                f_state = el.text.strip()
    period = rtype = ""
    for el in hdr.iter():
        t = _tag(el)
        if t in ("TaxPeriodEndDt", "TaxPeriodEndDate") and not period and el.text:
            period = el.text.strip()
        elif t in ("ReturnTypeCd", "ReturnType") and not rtype and el.text:
            rtype = el.text.strip()

    oid = Path(path).stem
    head = dict(filer_ein=ein9(f_ein), filer_name_as_filed=f_name,
                filer_state=f_state, tax_period_end=period[:10],
                tax_year=period[:4], return_type=rtype, object_id=oid,
                schedule_i_present="1" if si is not None else "0",
                form_990pf_present="1" if pf is not None else "0")

    grants = []

    # ---- Form 990 Schedule I Part II -- CARRIES THE RECIPIENT EIN ----------
    if si is not None:
        for child in si:
            if _tag(child) != "RecipientTable":
                continue
            d, addr = {}, None
            for c in child:
                ct = _tag(c)
                if ct in ("USAddress", "ForeignAddress"):
                    addr = c
                elif c.text and ct not in d:
                    d[ct] = c.text.strip()
            grp = next((e for e in child
                        if _tag(e) in ("RecipientBusinessName",
                                       "RecipientNameBusiness")), None)
            rname = _name2(grp) if grp is not None else d.get(
                "RecipientNameBusiness", "")
            city, st = _addr(addr)
            cash = numf(d.get("CashGrantAmt") or d.get("AmountOfCashGrant"))
            noncash = numf(d.get("NonCashAssistanceAmt")
                           or d.get("AmountOfNonCashAssistance"))
            grants.append(dict(
                form_type="IRS Form 990",
                form_schedule="Schedule I Part II (Grants to organizations "
                              "and domestic governments)",
                grant_status="PAID_DURING_YEAR",
                recipient_name_as_filed=rname,
                recipient_ein=ein9(d.get("RecipientEIN") or d.get("EINOfRecipient")),
                recipient_city=city, recipient_state=st,
                irc_section_as_filed=d.get("IRCSectionDesc", ""),
                recipient_relationship_as_filed="",
                recipient_foundation_status_as_filed="",
                cash_grant_usd="" if cash is None else f"{cash:.2f}",
                noncash_assistance_usd="" if noncash is None else f"{noncash:.2f}",
                purpose_verbatim=(d.get("PurposeOfGrantTxt")
                                  or d.get("PurposeOfGrant") or ""),
            ))

    # ---- Form 990-PF Part XV -- NO RECIPIENT EIN EXISTS ON THIS FORM ------
    if pf is not None:
        for grp in pf.iter():
            t = _tag(grp)
            if t == "GrantOrContributionPdDurYrGrp":
                status = "PAID_DURING_YEAR"
            elif t == "ApprovedFutureGrantsGrp":
                status = "APPROVED_FOR_FUTURE_PAYMENT"
            elif t in ("GrantOrContributionPdDurYr", "GrantsPaidDuringYear"):
                status = "PAID_DURING_YEAR"
            else:
                continue
            d, addr = {}, None
            for c in grp:
                ct = _tag(c)
                if ct in ("RecipientUSAddress", "RecipientForeignAddress",
                          "USAddress", "ForeignAddress"):
                    addr = c
                elif ct in ("RecipientBusinessName", "RecipientNameBusiness"):
                    d["_biz"] = _name2(c)
                elif ct in ("RecipientPersonNm", "RecipientNamePerson"):
                    d["_person"] = (c.text or "").strip()
                elif c.text and ct not in d:
                    d[ct] = c.text.strip()
            rname = d.get("_biz") or d.get("_person") or ""
            city, st = _addr(addr)
            amt = numf(d.get("Amt") or d.get("Amount")
                       or d.get("GrantOrContributionAmt"))
            grants.append(dict(
                form_type="IRS Form 990-PF",
                form_schedule=("Part XV line 3a (Grants paid during the year)"
                               if status == "PAID_DURING_YEAR"
                               else "Part XV line 3b (Approved for future "
                                    "payment)"),
                grant_status=status,
                recipient_name_as_filed=rname,
                recipient_ein="",          # the form does not ask for one
                recipient_city=city, recipient_state=st,
                irc_section_as_filed="",
                recipient_relationship_as_filed=(
                    d.get("RecipientRelationshipTxt")
                    or d.get("RecipientRelationship") or ""),
                recipient_foundation_status_as_filed=(
                    d.get("RecipientFoundationStatusTxt")
                    or d.get("RecipientFoundationStatus") or ""),
                cash_grant_usd="" if amt is None else f"{amt:.2f}",
                noncash_assistance_usd="",
                purpose_verbatim=(d.get("GrantOrContributionPurposeTxt")
                                  or d.get("GrantOrContributionPurpose") or ""),
            ))
    return head, grants, ""


# ---------------------------------------------------------------------------
# recipient matching -- EIN first, guarded phrase second, NEVER a single token
# ---------------------------------------------------------------------------

def build_matchers():
    by_ein, phrases = {}, []
    for key, name, ein, aliases in RECIPIENTS:
        if ein:
            by_ein[ein9(ein)] = key
        for a in aliases:
            phrases.append((norm_name(a), key, a))
    # longest phrase first so "GEORGE MASON UNIVERSITY FOUNDATION" wins over
    # "GEORGE MASON UNIVERSITY"
    phrases.sort(key=lambda t: -len(t[0]))
    return by_ein, phrases


def match_recipient(rec_ein, rec_name, purpose, by_ein, phrases):
    """Returns (key, basis, matched_alias).

    An EIN match is one leg of hard evidence.  A phrase match is a NAME match
    and is never presented as equivalent: AGENTS.md records that a name match
    is never Tier A.  A single trap token can never carry a match, because
    matching is on multi-word phrases only.
    """
    e = ein9(rec_ein)
    if e and e in by_ein:
        return by_ein[e], "recipient_ein_on_filed_schedule", ""
    n = norm_name(rec_name)
    if n:
        for ph, key, alias in phrases:
            if len(ph.split()) < 2:
                continue                       # never a single token
            if re.search(r"(^| )" + re.escape(ph) + r"( |$)", n):
                return key, ("recipient_name_phrase_match_no_ein_on_form"
                             if not e else "recipient_name_phrase_match"), alias
    # last resort: the ORGANISATION is named inside the purpose text.  Only
    # used for Hoover, which has no EIN and no return of its own.
    p = norm_name(purpose)
    if p:
        for ph, key, alias in phrases:
            if key != "HOOVER_NAMED":
                continue
            if re.search(r"(^| )" + re.escape(ph) + r"( |$)", p):
                return key, "unit_named_in_purpose_text_only", alias
    return "", "", ""


# ---------------------------------------------------------------------------
# STEP parse -> data/clean/grantmaker_funding_flows.csv
# ---------------------------------------------------------------------------

FLOW_FIELDS = [
    "flow_id",
    "funder_key", "funder_ein", "funder_name_as_filed", "funder_name_canonical",
    "funder_state", "funder_is_donor_advised_fund",
    "tax_year", "tax_period_end",
    "recipient_name_as_filed", "recipient_ein", "recipient_city",
    "recipient_state",
    "recipient_target_key", "recipient_target_name",
    "recipient_resolved_target", "recipient_match_basis",
    "recipient_matched_alias", "recipient_unit_identified",
    "recipient_icwa_position", "recipient_icwa_position_source",
    "grant_status", "cash_grant_usd", "noncash_assistance_usd",
    "purpose_verbatim",
    "recipient_relationship_as_filed", "recipient_foundation_status_as_filed",
    "funder_identity_basis",
    "irc_section_as_filed",
    "form_type", "form_schedule", "return_type", "object_id",
    "source_url", "zip_member", "irs_downloads_page", "irs_index_url",
    "evidence_class", "carries_institutional_position", "row_caveat",
    "retrieved_date", "built_date", "built_by_script",
]

FLOWS = CLEAN / "grantmaker_funding_flows.csv"
COVERAGE = CLEAN / "grantmaker_funding_coverage.csv"
OVERLAP = CLEAN / "grantmaker_funding_overlap.csv"


def icwa_positions():
    """Read documented ICWA positions from script 139's output.

    The side an organisation is on is NOT asserted by this script.  It is read
    from `native_issue_litigation_positions.csv`, where every row is gated on a
    verbatim quote located in the filed document.
    """
    out = {}
    rows = read_csv(CLEAN / "native_issue_litigation_positions.csv")
    alias = {
        "GOLDWATER INSTITUTE": "GOLDWATER", "CATO INSTITUTE": "CATO",
        "TEXAS PUBLIC POLICY FOUNDATION": "TPPF",
        "PACIFIC LEGAL FOUNDATION": "PLF",
        "NEW CIVIL LIBERTIES ALLIANCE": "NCLA",
        "PROJECT ON FAIR REPRESENTATION": "POFR",
        "THE PROJECT ON FAIR REPRESENTATION": "POFR",
        "MERCATUS CENTER": "MERCATUS",
        "ANTONIN SCALIA LAW SCHOOL AT GEORGE MASON UNIVERSITY": "GMUF",
        "HOOVER INSTITUTION AT STANFORD UNIVERSITY": "STANFORD",
        "INSTITUTE FOR HUMANE STUDIES": "IHS",
    }
    for r in rows:
        if r.get("issue_area") != "ICWA":
            continue
        k = alias.get((r.get("organization_name_as_filed") or "").upper())
        if not k:
            continue
        cls = r.get("evidence_class", "")
        pos = r.get("position_relative_to_native_interest", "") or "NOT_STATED"
        cur = out.get(k)
        # C_INSTITUTIONAL_ACTION outranks B_AFFILIATED_INDIVIDUAL.
        rank = {"C_INSTITUTIONAL_ACTION": 2, "A_FUNDER_ACTIVITY": 1,
                "B_AFFILIATED_INDIVIDUAL": 0}.get(cls, 0)
        if cur is None or rank > cur[2]:
            out[k] = (f"{cls}:{pos}", r.get("position_id", ""), rank)
    return {k: (v[0], v[1]) for k, v in out.items()}


def step_parse():
    log("=== 140 parse ===")
    fetch = {r["object_id"]: r for r in read_csv(FLOG)}
    idx = {r["object_id"]: r for r in read_csv(IDX_FILE)}
    canon = {f[2]: (f[0], f[1], f[4]) for f in FUNDERS if f[2]}
    canon_by_key = {f[0]: f for f in FUNDERS}
    by_ein, phrases = build_matchers()
    rec_name = {k: n for k, n, _e, _a in RECIPIENTS}
    positions = icwa_positions()
    log(f"  ICWA positions read from script 139: {len(positions)} "
        f"({', '.join(sorted(positions))})")

    rows, heads, traps = [], [], []
    errs = Counter()
    files = sorted(XMLDIR.glob("*.xml"))
    log(f"  returns on disk: {len(files)}")
    for f in files:
        head, gs, err = parse_return(f)
        if err:
            errs[err] += 1
            continue
        oid = head["object_id"]
        fr = fetch.get(oid, {})
        ix = idx.get(oid, {})
        fk, fname, is_daf = canon.get(head["filer_ein"], ("", "", 0))
        if not fk:
            # discovered by index name match; carry the declared key through
            mb = ix.get("match_basis", "")
            if mb.startswith("index_taxpayer_name_match:"):
                fk = mb.split(":", 1)[1]
                t = canon_by_key.get(fk)
                fname, is_daf = (t[1], t[4]) if t else ("", 0)
        trap = NAME_TRAP_EINS.get(head["filer_ein"])
        head.update(funder_key=("" if trap else fk), n_grant_rows=len(gs),
                    funder_identity_basis=(
                        "EXCLUDED_NAME_TRAP: " + trap[1] if trap
                        else FUNDER_IDENTITY_NOTES.get(
                            head["filer_ein"],
                            "EIN resolved against the full IRS EO BMF "
                            "(1,957,340 organisations).")),
                    source_url=fr.get("url", ""),
                    zip_member=fr.get("zip_member", ""),
                    retrieved_date=fr.get("fetched_date", ""),
                    index_url=ix.get("index_url", ""))
        heads.append(head)
        if trap:
            # An organisation caught only because it shares a name is not a
            # small error to be tidied away -- it is written out, named, with
            # the reason it was refused.
            traps.append({
                "excluded_filer_ein": head["filer_ein"],
                "excluded_filer_name_as_filed": head["filer_name_as_filed"],
                "excluded_filer_state": head["filer_state"],
                "tax_year": head["tax_year"], "object_id": oid,
                "would_have_been_keyed_as": trap[0],
                "declared_target_ein": next(
                    (f[2] for f in FUNDERS if f[0] == trap[0]), ""),
                "grant_rows_refused": len(gs),
                "exclusion_reason": trap[1],
                "built_date": TODAY, "built_by_script": SCRIPT})
            continue
        for i, g in enumerate(gs, 1):
            key, basis, alias = match_recipient(
                g["recipient_ein"], g["recipient_name_as_filed"],
                g["purpose_verbatim"], by_ein, phrases)
            unit = "NOT_APPLICABLE_SINGLE_LEGAL_PERSON"
            if key in UNIT_PATTERNS:
                blob = (g["purpose_verbatim"] + " "
                        + g["recipient_name_as_filed"]).upper()
                unit = ("STANFORD_UNIT_NOT_IDENTIFIED" if key == "STANFORD"
                        else "GMU_UNIT_NOT_IDENTIFIED")
                for rx, label in UNIT_PATTERNS[key]:
                    if re.search(rx, blob):
                        unit = label
                        break
            elif key == "HOOVER_NAMED":
                unit = "HOOVER_NAMED_IN_TEXT"
            elif not key:
                unit = ""
            caveat = SHARED_FUNDER_CAVEAT
            if is_daf:
                caveat += " " + DAF_CAVEAT
            if key == "STANFORD":
                caveat += " " + STANFORD_CAVEAT
            if key in ("GMUF", "GMU_INSTR", "GMU"):
                caveat += " " + GMU_CAVEAT
            # The STRONGEST DEFENSIBLE TARGET. A grant filed to Stanford whose
            # purpose names Hoover, and a grant filed to "Hoover Institution"
            # with no Stanford in the string, are the same fact; a grant to
            # Stanford that names no unit is NOT that fact and must never be
            # folded in with them.
            resolved = key
            if key == "HOOVER_NAMED" or (key == "STANFORD"
                                         and unit == "HOOVER_NAMED_IN_TEXT"):
                resolved = "HOOVER_UNIT_IDENTIFIED"
            elif key == "MERCATUS" or (key in ("GMUF", "GMU", "GMU_INSTR")
                                       and unit == "MERCATUS_NAMED_IN_TEXT"):
                resolved = "MERCATUS_UNIT_IDENTIFIED"
            pos, pos_src = positions.get(key, ("", ""))
            rows.append(dict(
                flow_id=f"{oid}-{i:05d}",
                funder_key=fk, funder_ein=head["filer_ein"],
                funder_name_as_filed=head["filer_name_as_filed"],
                funder_name_canonical=fname, funder_state=head["filer_state"],
                funder_is_donor_advised_fund=int(bool(is_daf)),
                tax_year=head["tax_year"], tax_period_end=head["tax_period_end"],
                recipient_target_key=key, recipient_target_name=rec_name.get(key, ""),
                recipient_resolved_target=resolved,
                recipient_match_basis=basis, recipient_matched_alias=alias,
                recipient_unit_identified=unit,
                recipient_icwa_position=pos,
                recipient_icwa_position_source=pos_src,
                return_type=head["return_type"], object_id=oid,
                source_url=head["source_url"], zip_member=head["zip_member"],
                irs_downloads_page=IRS_DOWNLOAD_PAGE,
                irs_index_url=head["index_url"],
                evidence_class=EvidenceClass.FUNDER_ACTIVITY.value,
                carries_institutional_position=int(
                    EvidenceClass.FUNDER_ACTIVITY.carries_institutional_position),
                row_caveat=caveat,
                retrieved_date=head["retrieved_date"], built_date=TODAY,
                funder_identity_basis=head["funder_identity_basis"],
                built_by_script=SCRIPT, **g))
    if errs:
        log(f"  parse notes: {dict(errs)}")
    write_csv(FLOWS, rows, FLOW_FIELDS)
    log(f"  wrote {FLOWS.relative_to(ROOT)}: {len(rows):,} grant rows from "
        f"{len(heads) - len(traps)} returns")
    if traps:
        tp = REVIEW / f"grantmaker_name_trap_exclusions_{TODAY}.csv"
        write_csv(tp, traps)
        log(f"  NAME TRAPS REFUSED: {len(traps)} returns "
            f"({sum(t['grant_rows_refused'] for t in traps)} grant rows) "
            f"-> {tp.relative_to(ROOT)}")
    write_csv(RAW / "_returns_parsed.csv", heads)
    return rows, heads


# ---------------------------------------------------------------------------
# STEP overlap
# ---------------------------------------------------------------------------

def step_overlap():
    log("=== 140 overlap ===")
    rows = [r for r in read_csv(FLOWS) if r["recipient_target_key"]]
    positions = icwa_positions()
    anti = {k for k, (p, _s) in positions.items()
            if p.startswith("C_INSTITUTIONAL_ACTION")
            and "OPPOSED" in p}
    # TWO TIERS, AND THEY MUST NEVER BE ADDED TOGETHER.
    #
    #   UNIT_IDENTIFIED   the filed return NAMES Hoover or Mercatus, either as
    #                     the recipient or in the purpose line. This is the
    #                     only tier that supports the sentence "this foundation
    #                     funded Hoover".
    #   INSTITUTION_LEVEL the recipient is Stanford University or the George
    #                     Mason University Foundation and NO unit is named. The
    #                     money reached a university that contains Hoover or
    #                     Mercatus. It CANNOT be claimed to have reached them.
    inst_unit = {"HOOVER_UNIT_IDENTIFIED", "MERCATUS_UNIT_IDENTIFIED"}
    inst_house = {"STANFORD", "GMUF", "GMU", "GMU_INSTR"}
    log(f"  documented anti-ICWA institutional actors: {sorted(anti)}")
    log(f"  unit-identified Hoover/Mercatus targets:   {sorted(inst_unit)}")
    log(f"  institution-level (unit NOT named):        {sorted(inst_house)}")

    agg = defaultdict(lambda: {"n": 0, "usd": 0.0, "years": set(),
                               "unit": Counter(), "basis": Counter(),
                               "purposes": []})
    for r in rows:
        rt = r["recipient_resolved_target"]
        k = (r["funder_key"], r["funder_ein"], r["funder_name_canonical"], rt)
        a = agg[k]
        a["n"] += 1
        a["usd"] += numf(r["cash_grant_usd"]) or 0.0
        if r["tax_year"]:
            a["years"].add(r["tax_year"])
        a["unit"][r["recipient_unit_identified"]] += 1
        a["basis"][r["recipient_match_basis"]] += 1
        if rt in inst_unit and len(a["purposes"]) < 4 and r["purpose_verbatim"]:
            a["purposes"].append(r["purpose_verbatim"][:90])

    def side_of(rt):
        if rt in anti:
            return "DOCUMENTED_ANTI_ICWA_INSTITUTIONAL_ACTOR"
        if rt in inst_unit:
            return "HOOVER_OR_MERCATUS_UNIT_IDENTIFIED"
        if rt in inst_house:
            return "HOST_INSTITUTION_UNIT_NOT_IDENTIFIED"
        return ""

    funders = defaultdict(lambda: {"anti": {}, "unit": {}, "house": {}})
    for (fk, fein, fname, rt), a in agg.items():
        s_ = side_of(rt)
        if not s_:
            continue
        bucket = ("anti" if s_.startswith("DOCUMENTED")
                  else "unit" if s_.endswith("UNIT_IDENTIFIED") else "house")
        funders[(fk, fein, fname)][bucket][rt] = a

    out = []
    for (fk, fein, fname), d in sorted(funders.items()):
        both_strict = bool(d["anti"]) and bool(d["unit"])
        both_house = bool(d["anti"]) and bool(d["house"])
        for bucket in ("anti", "unit", "house"):
            for rt, a in sorted(d[bucket].items()):
                out.append({
                    "funder_key": fk, "funder_ein": fein,
                    "funder_name_canonical": fname,
                    "funder_is_donor_advised_fund": int(
                        fk in ("DONORSTRUST", "DONORSCAPITAL")),
                    "recipient_resolved_target": rt,
                    "recipient_side": side_of(rt),
                    "overlap_tier": ("UNIT_IDENTIFIED" if bucket == "unit"
                                     else "INSTITUTION_LEVEL"
                                     if bucket == "house" else "ANTI_ICWA_SIDE"),
                    "n_grants": a["n"],
                    "cash_grant_usd_total": f"{a['usd']:.2f}",
                    "tax_years": ",".join(sorted(a["years"])),
                    "recipient_unit_identified_breakdown":
                        "; ".join(f"{k}={v}" for k, v in a["unit"].most_common()),
                    "recipient_match_basis_breakdown":
                        "; ".join(f"{k}={v}" for k, v in a["basis"].most_common()),
                    "example_purposes_verbatim": " | ".join(a["purposes"]),
                    "funder_gave_to_both_sides_unit_identified": int(both_strict),
                    "funder_gave_to_both_sides_institution_level": int(both_house),
                    "evidence_class": EvidenceClass.FUNDER_ACTIVITY.value,
                    "carries_institutional_position": 0,
                    "row_caveat": SHARED_FUNDER_CAVEAT,
                    "built_date": TODAY, "built_by_script": SCRIPT,
                })
    write_csv(OVERLAP, out)
    n_strict = sum(1 for _f, d in funders.items() if d["anti"] and d["unit"])
    n_house = sum(1 for _f, d in funders.items()
                  if d["anti"] and (d["unit"] or d["house"]))
    log(f"  wrote {OVERLAP.relative_to(ROOT)}: {len(out)} rows")
    log(f"  funders on BOTH sides, UNIT IDENTIFIED       : {n_strict}")
    log(f"  funders on BOTH sides, institution level too : {n_house}")
    return out


# ---------------------------------------------------------------------------
# STEP coverage
# ---------------------------------------------------------------------------

def step_coverage():
    log("=== 140 coverage ===")
    idx = read_csv(IDX_FILE)
    flog = {r["object_id"]: r for r in read_csv(FLOG)}
    heads = {r["object_id"]: r for r in read_csv(RAW / "_returns_parsed.csv")}
    flows = read_csv(FLOWS)
    n_by_oid = Counter(r["object_id"] for r in flows)

    seen_keys = set()
    out = []
    for f in FUNDERS:
        key, name, ein, form, daf, _rx = f
        allmine = [r for r in idx
                   if (ein and r["ein"] == ein)
                   or r["match_basis"] == f"index_taxpayer_name_match:{key}"]
        mine = [r for r in allmine
                if r["return_type"] in ("990", "990PF", "990EZ", "990PR")]
        n_990t = len(allmine) - len(mine)
        seen_keys.add(key)
        if not mine:
            out.append({
                "funder_key": key, "funder_name_canonical": name,
                "funder_ein": ein or "NOT_RESOLVED",
                "expected_form": form, "is_donor_advised_fund": int(daf),
                "index_years_searched": "2017-2026",
                "returns_indexed": 0, "returns_retrieved": 0,
                "returns_parsed": 0, "grant_rows": 0,
                "tax_years_observed": "",
                "coverage_status": ("NOT_FOUND_IN_IRS_EFILE_INDEX_2017_2026"
                                    if ein else
                                    "NO_EIN_RESOLVED_AND_NO_INDEX_NAME_MATCH"),
                "coverage_note": (
                    "Swept the IRS e-file index for submission years 2017-2026 "
                    "on both EIN and taxpayer name and found no return. "
                    "E-filing became mandatory only with the Taxpayer First "
                    "Act; paper filers 2011-2018 are absent from the XML "
                    "entirely, and the index itself begins at submission year "
                    "2017. This is a statement about RETRIEVABILITY, never "
                    "about whether the organisation filed or funded anything."),
                "built_date": TODAY, "built_by_script": SCRIPT})
            continue
        got = [r for r in mine if flog.get(r["object_id"], {}).get(
            "http_status") == "200"]
        parsed = [r for r in mine if r["object_id"] in heads]
        yrs = sorted({heads[r["object_id"]]["tax_year"] for r in parsed
                      if heads[r["object_id"]].get("tax_year")})
        grows = sum(n_by_oid.get(r["object_id"], 0) for r in mine)
        missing = [r for r in mine if r["object_id"] not in heads]
        status = "RETRIEVED_AND_PARSED" if parsed and not missing else (
            "PARTIAL_SOME_RETURNS_INDEXED_NOT_RETRIEVED" if parsed
            else "INDEXED_BUT_NONE_RETRIEVED")
        out.append({
            "funder_key": key, "funder_name_canonical": name,
            "funder_ein": ein or (mine[0]["ein"] if mine else ""),
            "expected_form": form, "is_donor_advised_fund": int(daf),
            "index_years_searched": "2017-2026",
            "returns_indexed": len(mine), "returns_retrieved": len(got),
            "returns_parsed": len(parsed), "grant_rows": grows,
            "tax_years_observed": ",".join(yrs),
            "coverage_status": status,
            "coverage_note": (
                f"{len(missing)} indexed return(s) not retrieved. "
                if missing else "")
            + (f"{n_990t} Form 990-T return(s) indexed and deliberately not "
               f"read: Form 990-T is the business income tax return and "
               f"carries no grants schedule. " if n_990t else "")
            + ("Filed on Form 990-PF, whose Part XV grants list carries NO "
               "recipient EIN -- recipient identification is by name only. "
               if form == "990PF" else
               "Filed on Form 990; Schedule I Part II carries the recipient "
               "EIN. ")
            + ("This filer is a donor-advised fund and anonymises the original "
               "donor by design. " if daf else "")
            + "E-file coverage is partial before tax year 2019.",
            "built_date": TODAY, "built_by_script": SCRIPT})

    # Recipient-side coverage: can this recipient even be observed?
    for key, name, ein, aliases in RECIPIENTS:
        hits = [r for r in read_csv(FLOWS) if r["recipient_target_key"] == key]
        basis = Counter(r["recipient_match_basis"] for r in hits)
        out.append({
            "funder_key": f"RECIPIENT:{key}", "funder_name_canonical": name,
            "funder_ein": ein or "NO_EIN_FILES_NO_FORM_990",
            "expected_form": "", "is_donor_advised_fund": 0,
            "index_years_searched": "", "returns_indexed": "",
            "returns_retrieved": "", "returns_parsed": "",
            "grant_rows": len(hits),
            "tax_years_observed": ",".join(sorted({r["tax_year"] for r in hits
                                                   if r["tax_year"]})),
            "coverage_status": ("OBSERVABLE" if ein else
                                "NOT_SEPARATELY_OBSERVABLE_NO_OWN_FORM_990"),
            "coverage_note": (
                ("The Hoover Institution is a unit of Stanford University, "
                 "files no Form 990, and is absent from the full IRS EO BMF "
                 "(1,957,340 organisations searched). It can be observed ONLY "
                 "where a grant's purpose text names it. "
                 if key == "HOOVER_NAMED" else "")
                + ("Receives on behalf of the whole university; a grant is "
                   "attributable to a unit only where the purpose names one. "
                   if key in ("GMUF", "GMU_INSTR", "GMU", "STANFORD") else "")
                + "match bases: " + ("; ".join(f"{k}={v}" for k, v
                                               in basis.most_common()) or "none")),
            "built_date": TODAY, "built_by_script": SCRIPT})

    write_csv(COVERAGE, out)
    log(f"  wrote {COVERAGE.relative_to(ROOT)}: {len(out)} rows")
    return out



# ---------------------------------------------------------------------------
# STEP codebook
# ---------------------------------------------------------------------------

CODEBOOK = {
    "flow_id": "Row identifier: IRS e-file object_id plus the ordinal of the "
               "grant within the return.",
    "funder_key": "Cedar key for the grantmaking foundation. Blank where the "
                  "filer was refused as a name trap.",
    "funder_ein": "EIN of the filing foundation, from the filed return header.",
    "funder_name_as_filed": "Filer name exactly as written on the return.",
    "funder_name_canonical": "Cedar canonical name for the funder.",
    "funder_state": "Filer state from the return header.",
    "funder_is_donor_advised_fund": "1 where the filer is a donor-advised "
        "fund (DonorsTrust, Donors Capital Fund). A DAF anonymises the "
        "original donor by design: the grant is legally the fund's own and no "
        "return discloses who advised it.",
    "funder_identity_basis": "How this filer's identity was established - BMF "
        "EIN resolution, or, for organisations absent from the current BMF, "
        "the filed return's own name and address.",
    "tax_year": "Tax year of the return (year part of the period end date).",
    "tax_period_end": "Tax period end date on the return.",
    "recipient_name_as_filed": "Recipient organisation name exactly as written "
        "on the filed schedule.",
    "recipient_ein": "Recipient EIN. Populated ONLY on Form 990 Schedule I - "
        "Form 990-PF Part XV does not ask for one.",
    "recipient_city": "Recipient city as filed.",
    "recipient_state": "Recipient state as filed.",
    "recipient_target_key": "Cedar key of the target recipient this row "
        "matched, blank where the recipient is not one of the targets.",
    "recipient_target_name": "Canonical name of that target.",
    "recipient_resolved_target": "The strongest defensible target. "
        "HOOVER_UNIT_IDENTIFIED and MERCATUS_UNIT_IDENTIFIED mean the filed "
        "return NAMES the unit; STANFORD, GMUF, GMU mean it names only the "
        "host institution.",
    "recipient_match_basis": "Which leg of evidence made the match: recipient "
        "EIN on the filed schedule, a guarded multi-word name phrase, or the "
        "unit being named in the purpose text.",
    "recipient_matched_alias": "The alias phrase that matched.",
    "recipient_unit_identified": "Whether a unit inside a multi-unit recipient "
        "is named by the filed return. STANFORD_UNIT_NOT_IDENTIFIED and "
        "GMU_UNIT_NOT_IDENTIFIED mean the money reached the university and "
        "CANNOT be attributed to Hoover, Mercatus or the law school.",
    "recipient_icwa_position": "The recipient's documented position in ICWA "
        "litigation, read from native_issue_litigation_positions.csv. Not "
        "asserted by this build.",
    "recipient_icwa_position_source": "position_id of the row that supplies it.",
    "grant_status": "PAID_DURING_YEAR or APPROVED_FOR_FUTURE_PAYMENT. Never "
        "add the two: an approved future grant is not money paid.",
    "cash_grant_usd": "Cash grant amount as filed.",
    "noncash_assistance_usd": "Non-cash assistance as filed. Never added to "
        "the cash column.",
    "purpose_verbatim": "The grant purpose exactly as written by the filer.",
    "recipient_relationship_as_filed": "990-PF Part XV relationship column.",
    "recipient_foundation_status_as_filed": "990-PF Part XV foundation status.",
    "irc_section_as_filed": "Schedule I IRC section column.",
    "form_type": "IRS Form 990 or IRS Form 990-PF.",
    "form_schedule": "The exact schedule and part the row was read from.",
    "return_type": "Return type code from the e-file index.",
    "object_id": "IRS e-file return object id - the return's primary key.",
    "source_url": "The IRS bulk archive ZIP the return XML was read out of.",
    "zip_member": "The member name inside that archive.",
    "irs_downloads_page": "The IRS page that lists the archives.",
    "irs_index_url": "The IRS e-file index CSV the return was found in.",
    "evidence_class": "Always FUNDER_ACTIVITY. A fact about the DONOR.",
    "carries_institutional_position": "Always 0. A shared funder is not a "
        "shared position.",
    "row_caveat": "The sentence that must travel with the row.",
    "retrieved_date": "Date the return XML was retrieved.",
    "built_date": "Date this row was built.",
    "built_by_script": "The script that built it.",
}


def step_codebook():
    log("=== 140 codebook ===")
    p = CLEAN / "codebook_master.csv"
    rows = read_csv(p)
    if not rows:
        log("  codebook_master.csv not found - skipped")
        return
    bak = p.with_suffix(f".csv.bak_{TODAY}_pre140")
    if not bak.exists():
        bak.write_bytes(p.read_bytes())
        log(f"  backed up -> {bak.name}")
    fields = list(rows[0].keys())
    ds = "17_grantmaker_funding_flows"
    kept = [r for r in rows if r.get("dataset") != ds]
    dropped = len(rows) - len(kept)
    n = len(read_csv(FLOWS))
    for var, desc in CODEBOOK.items():
        row = {k: "" for k in fields}
        for k, v in (("dataset", ds), ("variable", var), ("description", desc),
                     ("n_rows", n), ("published", "0"),
                     ("access_tier", "internal"),
                     ("generated", TODAY),
                     ("source", "IRS Form 990 / 990-PF e-file XML")):
            if k in row:
                row[k] = v
        kept.append(row)
    write_csv(p, kept, fields)
    log(f"  dataset rows replaced: {dropped} -> {len(CODEBOOK)}; "
        f"total {len(kept):,}")


# ---------------------------------------------------------------------------
# STEP report
# ---------------------------------------------------------------------------

def step_report():
    log("=== 140 report ===")
    flows = read_csv(FLOWS)
    overlap = read_csv(OVERLAP)
    cov = read_csv(COVERAGE)
    a = []
    p = a.append
    p(f"140_build_grantmaker_funding_flows.py -- run report {TODAY}")
    p("=" * 74)
    p("")
    p("HYPOTHESIS UNDER TEST: the foundations funding the anti-ICWA litigators")
    p("also fund the Hoover Institution and the Mercatus Center.")
    p("")
    p(f"grant rows parsed          {len(flows):,}")
    p(f"returns parsed             {len(read_csv(RAW / '_returns_parsed.csv')):,}")
    p(f"funders with any return    "
      f"{len({r['funder_key'] for r in flows if r['funder_key']})}")
    p(f"rows matched to a target   "
      f"{sum(1 for r in flows if r['recipient_target_key'])}")
    p("")
    p("-- BY FUNDER -------------------------------------------------------")
    byf = defaultdict(lambda: [0, 0.0, set()])
    for r in flows:
        d = byf[r["funder_name_canonical"] or r["funder_name_as_filed"]]
        d[0] += 1
        d[1] += numf(r["cash_grant_usd"]) or 0.0
        if r["tax_year"]:
            d[2].add(r["tax_year"])
    for k, (n, usd, yrs) in sorted(byf.items()):
        p(f"  {k[:46]:46s} {n:7,} rows  ${usd:16,.0f}  "
          f"TY{min(yrs) if yrs else '-'}-{max(yrs) if yrs else '-'}")
    p("")
    p("-- OVERLAP MATRIX --------------------------------------------------")
    if not overlap:
        p("  NO ROWS. No funder in the pull is observed giving to both a")
        p("  documented anti-ICWA institutional actor and to Hoover/Mercatus/GMU.")
    strict = sorted({r["funder_name_canonical"] for r in overlap
                     if r["funder_gave_to_both_sides_unit_identified"] == "1"})
    house = sorted({r["funder_name_canonical"] for r in overlap
                    if r["funder_gave_to_both_sides_institution_level"] == "1"}
                   ) if overlap else []
    p("")
    p("TIER 1 -- UNIT IDENTIFIED. The filed return names Hoover or Mercatus.")
    p("This is the only tier that supports the sentence 'this foundation")
    p("funded Hoover' or '...funded Mercatus'.")
    p(f"  funders on BOTH sides at this tier: {len(strict)}")
    for b in strict:
        p(f"    {b}")
    p("")
    p("TIER 2 -- INSTITUTION LEVEL. The recipient is Stanford University or")
    p("the George Mason University Foundation and NO unit is named. The money")
    p("reached a university that houses Hoover or Mercatus. It CANNOT be")
    p("claimed to have reached either of them.")
    p(f"  funders on BOTH sides counting this tier: {len(house)}")
    for b in house:
        if b not in strict:
            p(f"    {b}  (institution level only)")
    p("")
    for tier in ("ANTI_ICWA_SIDE", "UNIT_IDENTIFIED", "INSTITUTION_LEVEL"):
        p(f"  [{tier}]")
        for r in overlap:
            if r["overlap_tier"] != tier:
                continue
            p(f"    {r['funder_key']:14s} -> {r['recipient_resolved_target']:26s}"
              f" {r['n_grants']:>4} grants  "
              f"${float(r['cash_grant_usd_total']):>14,.0f}  "
              f"DAF={r['funder_is_donor_advised_fund']}  TY {r['tax_years']}")
    p("")
    p("-- COVERAGE --------------------------------------------------------")
    for r in cov:
        p(f"  {r['funder_key']:22s} {r['coverage_status']:46s} "
          f"idx={r['returns_indexed'] or '-'} parsed={r['returns_parsed'] or '-'} "
          f"rows={r['grant_rows']}")
    p("")
    p("-- THE THREE HARD LIMITS -------------------------------------------")
    p("1. " + STANFORD_CAVEAT)
    p("2. " + DAF_CAVEAT)
    p("3. " + SHARED_FUNDER_CAVEAT)
    p("")
    p("4. Form 990-PF Part XV carries NO recipient EIN. Every recipient")
    p("   identification on a private foundation's return in this file is a")
    p("   NAME match, which AGENTS.md records is never Tier A on its own.")
    p("5. E-file coverage is partial before tax year 2019 (Taxpayer First Act)")
    p("   and the IRS e-file index begins at submission year 2017. Absence of a")
    p("   return is never evidence a funder did not fund.")
    LOGS.mkdir(parents=True, exist_ok=True)
    out = LOGS / f"140_build_report_{TODAY}.txt"
    out.write_text("\n".join(a), encoding="utf-8")
    print("\n".join(a))
    log(f"  wrote {out.relative_to(ROOT)}")


# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps",
                    default="eins,index,probe,xml,deflate64,parse,overlap,coverage,codebook,report")
    ap.add_argument("--years", default="")
    ap.add_argument("--max-minutes", type=int, default=120)
    args = ap.parse_args()
    steps = [s.strip() for s in args.steps.split(",") if s.strip()]
    years = [int(y) for y in args.years.split(",") if y.strip()] or None
    log(f"free disk at start: {free_gb():.2f} GB")
    if "eins" in steps:
        step_eins()
    if "probe" in steps:
        step_probe()
    if "index" in steps:
        step_index(years)
    if "xml" in steps:
        step_xml(args.max_minutes)
    if "deflate64" in steps:
        step_deflate64()
    if "parse" in steps:
        step_parse()
    if "overlap" in steps:
        step_overlap()
    if "coverage" in steps:
        step_coverage()
    if "codebook" in steps:
        step_codebook()
    if "report" in steps:
        step_report()
    log(f"free disk at end: {free_gb():.2f} GB")


if __name__ == "__main__":
    main()
