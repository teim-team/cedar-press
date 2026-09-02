#!/usr/bin/env python3
"""
Cedar Press - 112: extend the IRS 990 e-file pull to the PHILANTHROPY GRANTEES.

WHAT THIS CLOSES
----------------
`code/111_build_advocacy_passthrough.py` built 185 complete
funding -> lobbying chains, and **every one of them rests on the LDA leg**.
The 990 leg contributed nothing:

    only 24 of the 927 recipient EINs have any row in np_financials.csv,
    and every one of those filed no Schedule C and $0 on Part IX line 11d.

That is not a parser failure.  `docs/PHILANTHROPY_DISCOVERY_LOG.md` measured
the reason: **491 of the 601 philanthropy grantees are outside the nonprofit
corpus entirely**, so their returns were never in script 99's index filter and
have never been retrieved.  This script points the SAME machinery at the
grantee EIN list.  It is queue length, not new engineering.

REUSE, NOT REBUILD.  Everything hard was solved in
`code/99_build_earmarks_and_schedc.py` and is IMPORTED from it:

  * `HttpRangeFile` - ProPublica's API does not expose Schedule C at all, and
    the IRS per-return S3 bucket (`s3.amazonaws.com/irs-form-990/<oid>_public
    .xml`) is retired and 404s on every object.  Returns now live only inside
    81 multi-GB ZIPs.  apps.irs.gov answers `Accept-Ranges: bytes`, so
    `zipfile.ZipFile` is pointed at an HTTP-range-backed file object and reads
    the central directory plus only the members we want.  Script 99 measured
    ~1.3 GB fetched instead of 30 GB.
  * `zip_manifest` - the archive list read from the IRS's own download page,
    cached at `data/raw/external/irs990_schedc/_zip_manifest.csv`.  Guessing
    the filenames does not work; two naming schemes coexist.
  * `parse_schedule_c` - written against a tag inventory taken over 2,647 real
    returns.  Do not write an XML parser for a federal schema from memory: the
    first draft of that function invented `PaidStaffOrMgmtInd`,
    `LobbyingExpendituresGrp` and `Organization501hElectionInd`, all plausible,
    all wrong.
  * `_consolidate_lobbying` - the three Schedule C reporting regimes ranked and
    never added, and Part IX line 11d deliberately NOT a fallback for
    Schedule C (fees paid to OUTSIDE lobbyists vs the organisation's OWN
    expenditure - they overlap without being the same quantity).

`resolve_entity` is imported from `code/33_apply_party_rulings.py` (standing
rule 8) and the eight guards are imported from script 111.  No second matcher
is written here, and this file writes NO relationship edge of any kind -
`bears_ownership` is asserted against at module load.

`schedc_expected` IS THE LOAD-BEARING COLUMN
--------------------------------------------
A 990-N filer reports gross receipts under $50,000 and nothing else.  Zero
lobbying there is the FILING REGIME, not a finding, and such an organisation
must never be counted as a zero.  In script 99's build, 1,592 of 8,507 rows
were 990-N and the true Schedule C denominator was 6,397, never 8,507.  Every
count published from this file states its denominator, and the retrieval rate
travels with every figure.

WHAT THIS FILE NEVER SAYS
-------------------------
1. That the grant paid for the lobbying.  Money is fungible and most grants are
   restricted to program work.  Both facts are recorded with their dates and
   their source documents; there is no causal column anywhere.
2. Anything pejorative about lobbying.  A 501(c)(3) may lobby within limits and
   many elect 501(h) precisely to do it transparently.  This documents a
   structure; it alleges nothing.
3. That a membership organisation is a hidden channel.  NCAI, NIGA, USET,
   NAIHC, AFN, NARF and the tribal health boards are funded by their tribal
   members and advocate on their behalf - that is their stated purpose.  Note
   that **membership dues are not a Schedule I grant and appear in no public
   filing**, which is why the ordinary way a tribe funds NCAI is invisible by
   construction.
4. That serving Native entities is owning or being owned by them.

FILES OWNED BY OTHER BUILDS ARE NOT TOUCHED.  `np_financials.csv` (another
build owns its 36 appended columns and its row order), `np_orgs.csv` and
`advocacy_passthrough.csv` are read only.  The refreshed pass-through is
written to a DATED sibling file.

Run:
  py -3 code/112_pull_grantee_990s.py --steps index
  py -3 code/112_pull_grantee_990s.py --steps xml
  py -3 code/112_pull_grantee_990s.py --steps deflate64
  py -3 code/112_pull_grantee_990s.py --steps build,passthrough,codebook,report
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
RAW = CEDAR / "data" / "raw" / "external"
REVIEW = CEDAR / "review"
LOGS = CEDAR / "logs"
DOCS = CEDAR / "docs"

GRANTEE_RAW = RAW / "irs990_grantee"
GRANTEE_XML = GRANTEE_RAW / "xml"
SCHEDC_RAW = RAW / "irs990_schedc"          # script 99's cache, read only
PHIL = RAW / "philanthropy"

TODAY = date.today().isoformat()
UA = "CedarPress/1.0 (research data; elijahsamsonmoreno@gmail.com)"

OUT = CLEAN / "np_grantee_financials.csv"
OUT_PASSTHROUGH = CLEAN / f"advocacy_passthrough_{TODAY}.csv"
OUT_REVIEW = REVIEW / f"grantee_990_unresolved_{TODAY}.csv"
REPORT = LOGS / f"112_build_report_{TODAY}.txt"

INDEX_YEARS = list(range(2017, 2027))
INDEX_URL = "https://apps.irs.gov/pub/epostcard/990/xml/{y}/index_{y}.csv"
IRS_NS = "{http://www.irs.gov/efile}"
SCHEDC_BEARING = {"990", "990EZ", "990O", "990EO", "990PF"}

# BMF FILING_REQ_CD -> filing regime.  Same mapping as scripts 17 and 99; one
# constant, not a third copy with its own drift.  (`docs/PHILANTHROPY_
# DISCOVERY_LOG.md` 2b: duplicated constants drift, and the stale one fires.)
FILING_REGIME = {
    "01": "990_or_990EZ", "02": "990_N", "03": "990_or_990EZ",
    "06": "990_PF", "07": "990_or_990EZ", "13": "990_or_990EZ",
    "14": "not_required", "00": "not_required",
}

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


def log(m):
    print(m, flush=True)


def read_csv(p, encoding="utf-8-sig"):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding=encoding, newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(p, rows, fields=None):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0].keys()) if rows else []
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    log(f"  wrote {p.relative_to(CEDAR)}  ({len(rows):,} rows)")


def ein9(v):
    d = re.sub(r"\D", "", str(v or ""))
    return d.zfill(9) if d else ""


def numf(v):
    try:
        return float(str(v).replace(",", "").replace("$", "").strip())
    except Exception:
        return None


# ---------------------------------------------------------------------------
# THE ONE RESOLVER and script 99's machinery, both IMPORTED.
# ---------------------------------------------------------------------------
def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, CEDAR / "code" / filename)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_M99 = None
_M111 = None


def m99():
    """Script 99: HttpRangeFile, zip_manifest, parse_schedule_c, Fetcher."""
    global _M99
    if _M99 is None:
        _M99 = _load("m99", "99_build_earmarks_and_schedc.py")
    return _M99


def m111():
    """Script 111: resolve_entity + the eight containment guards."""
    global _M111
    if _M111 is None:
        _M111 = _load("m111", "111_build_advocacy_passthrough.py")
    return _M111


sys.path.insert(0, str(CEDAR / "code"))
from cedar_domain import Tier, bears_ownership  # noqa: E402

# This build records a FILING FACT about an organisation.  It is not an
# ownership edge and it is not a service edge, and `serves_native_entities` is
# not `parent_native_entity`.  Enforced rather than remembered.
assert not bears_ownership("serves_native_entities")
assert not bears_ownership("affiliated_with")
assert not bears_ownership("member_of")


# ---------------------------------------------------------------------------
# host lock (docs/PULL_DISCIPLINE.md rule 2).  api.usaspending.gov is HELD by
# the prime-contracts pull (PID checked with Win32_Process, never `ps`, and
# never `taskkill /F /IM python.exe`) and is NOT touched by this script.
# ---------------------------------------------------------------------------
def _pid_alive(pid):
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
    p = LOGS / f"_HOSTLOCK_{host}.json"
    if p.exists():
        try:
            cur = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            cur = {}
        pid = cur.get("pid") or (cur.get("holder") or {}).get("pid")
        if cur.get("active") and pid and pid != os.getpid() and _pid_alive(pid):
            cur.setdefault("queue", []).append(
                {"script": "code/112_pull_grantee_990s.py",
                 "requested_at": datetime.now(timezone.utc).isoformat(),
                 "work": note})
            p.write_text(json.dumps(cur, indent=1), encoding="utf-8")
            log(f"  ! {host} held by live pid {pid}; queued and DEFERRING")
            return False
    LOGS.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(
        {"host": host, "pid": os.getpid(),
         "script": "code/112_pull_grantee_990s.py",
         "started": datetime.now(timezone.utc).isoformat(),
         "active": True, "queue": [],
         "policy": "sequential, >=1.0s gap on index, >=0.3s on range reads",
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


# ---------------------------------------------------------------------------
# THE TARGET LIST
# ---------------------------------------------------------------------------
def target_eins():
    """Who we are fetching returns for, and where each EIN came from.

    The NAMED target is the 601 distinct grantee EINs on the Schedule I Part II
    of the seven Native grantmakers in the philanthropy channel.  The review
    queue's 567 EINs are a strict subset of those (34 tribal colleges were held
    out for the TCU agent, which is why the queue is shorter).

    The pass-through build's funding leg reaches 927 distinct recipient EINs -
    the 601 plus 326 more read out of the LOCAL IRS e-file Schedule I cache
    (tribal and intertribal grantmakers: Tulalip Foundation, Osage Nation
    Foundation, ANTHC, NPAIHB, ITCA, NIHB).  Those 326 cost nothing extra: the
    index stream and the ZIP central directories have to be read either way, so
    they are included and the two denominators are reported separately.
    """
    src = defaultdict(set)
    for r in read_csv(PHIL / "schedule_i_grantees_2026-08-06.csv"):
        e = ein9(r.get("grantee_ein"))
        if e:
            src[e].add("philanthropy_schedule_i")
    for r in read_csv(REVIEW / "agent_native_org_candidates_philanthropy_"
                               "2026-08-06.csv"):
        rid = r.get("review_id") or ""
        if rid.startswith("EIN:"):
            e = ein9(rid[4:])
            if e:
                src[e].add("philanthropy_review_queue")
    for r in read_csv(CLEAN / "advocacy_passthrough.csv"):
        e = ein9(r.get("recipient_ein"))
        if e:
            src[e].add("advocacy_passthrough_recipient")
    return src


def grantee_context():
    """Name / state / IRS record / BMF regime for every target EIN.

    THE NAME IS SPLIT AT 35 CHARACTERS.  IRS e-file writes a business name
    across `BusinessNameLine1Txt` and `BusinessNameLine2Txt`; reading only line
    1 left `FOND DU LAC TRIBAL AND COMMUNITY` - a Minnesota STATE community
    college - looking like the Fond du Lac Band, and produced
    `AMERICAN INDIAN HIGHER EDUCATION` without its `CONSORTIUM`.  Both lines
    are joined everywhere in this file.
    """
    ctx = {}
    for r in read_csv(PHIL / "schedule_i_grantees_2026-08-06.csv"):
        e = ein9(r.get("grantee_ein"))
        if not e:
            continue
        c = ctx.setdefault(e, {"names": set(), "state": "", "irc": set(),
                               "funders": set(), "schedi_url": "",
                               "irs_name": "", "irs_status": "",
                               "bmf_regime": "", "in_np_orgs": 0})
        c["names"].add((r.get("grantee_name_as_filed") or "").strip())
        c["state"] = c["state"] or (r.get("grantee_state") or "").strip().upper()[:2]
        c["irc"].add((r.get("irc_section_as_filed") or "").strip().upper())
        c["funders"].add((r.get("funder_name") or "").strip())
        c["schedi_url"] = c["schedi_url"] or (r.get("source_url") or "")

    for r in read_csv(CLEAN / "advocacy_passthrough.csv"):
        e = ein9(r.get("recipient_ein"))
        if not e:
            continue
        c = ctx.setdefault(e, {"names": set(), "state": "", "irc": set(),
                               "funders": set(), "schedi_url": "",
                               "irs_name": "", "irs_status": "",
                               "bmf_regime": "", "in_np_orgs": 0})
        c["names"].add((r.get("recipient_org_name") or "").strip())
        c["funders"].add((r.get("funder_name") or "").strip())
        if not c["schedi_url"]:
            c["schedi_url"] = r.get("source_url_funding") or ""

    for r in read_csv(PHIL / "grantee_ein_resolved_2026-08-06.csv"):
        e = ein9(r.get("ein"))
        if e in ctx:
            ctx[e]["irs_name"] = (r.get("name") or "").strip()
            ctx[e]["irs_status"] = (r.get("status") or "").strip()
            ctx[e]["state"] = ctx[e]["state"] or (r.get("state") or "").strip()[:2]

    for r in read_csv(CLEAN / "np_orgs.csv"):
        e = ein9(r.get("EIN"))
        if e in ctx:
            ctx[e]["in_np_orgs"] = 1
            ctx[e]["bmf_regime"] = FILING_REGIME.get(
                (r.get("bmf_filing_req_cd") or "").strip(), "")
    for r in read_csv(RAW / "irs990" / "irs_bmf_slice_universe_2026-08-05.csv"):
        e = ein9(r.get("EIN"))
        if e in ctx and not ctx[e]["bmf_regime"]:
            ctx[e]["bmf_regime"] = FILING_REGIME.get(
                (r.get("FILING_REQ_CD") or "").strip().zfill(2), "")
    return ctx


# ---------------------------------------------------------------------------
# STEP: index
# ---------------------------------------------------------------------------
def step_index(years=None):
    """Stream the IRS e-file index CSVs and keep only our EINs.

    Script 99 filtered the same indexes against np_financials + np_orgs, which
    is exactly why the grantees are missing: 491 of 601 are outside that
    universe.  Nothing is written to disk but the matched rows.
    """
    log("=== 112 index ===")
    GRANTEE_RAW.mkdir(parents=True, exist_ok=True)
    src = target_eins()
    wanted = set(src)
    log(f"  target EINs: {len(wanted):,}")

    out = GRANTEE_RAW / "_index_targets.csv"
    rows = read_csv(out)
    done = {int(r["index_year"]) for r in rows if r.get("index_year")}

    if not claim_host("apps.irs.gov",
                      "IRS 990 e-file index CSVs 2017-2026, grantee EIN filter"):
        return
    F = m99().Fetcher(gap=1.0)
    try:
        for y in (years or INDEX_YEARS):
            if y in done:
                log(f"  {y}: cached")
                continue
            url = INDEX_URL.format(y=y)
            t0 = time.time()
            status, body = F.get(url, timeout=900)
            if status != 200 or not body:
                log(f"  {y}: HTTP {status} - SKIPPED (recorded, not smoothed)")
                continue
            rdr = csv.DictReader(io.StringIO(body.decode("utf-8", "replace")))
            kept = total = 0
            for rec in rdr:
                total += 1
                e = ein9(rec.get("EIN"))
                if e not in wanted:
                    continue
                rows.append({
                    "index_year": y, "ein": e,
                    "object_id": (rec.get("OBJECT_ID") or "").strip(),
                    "return_type": (rec.get("RETURN_TYPE") or "").strip(),
                    "tax_period": (rec.get("TAX_PERIOD") or "").strip(),
                    "taxpayer_name": (rec.get("TAXPAYER_NAME") or "").strip(),
                    "sub_date": (rec.get("SUB_DATE") or "").strip(),
                    "dln": (rec.get("DLN") or "").strip(),
                    "index_url": url, "fetched_date": TODAY})
                kept += 1
            log(f"  {y}: {total:,} index rows -> {kept:,} ours "
                f"({time.time()-t0:.0f}s, {len(body)/1e6:.0f}MB streamed)")
            write_csv(out, rows)
    finally:
        release_host("apps.irs.gov", "grantee index filter complete")
    write_csv(out, rows)
    eins = {r["ein"] for r in rows}
    log(f"  indexed returns {len(rows):,} over {len(eins):,} of "
        f"{len(wanted):,} target EINs")


# ---------------------------------------------------------------------------
# STEP: xml  - HTTP-range reads over the IRS ZIP archives
# ---------------------------------------------------------------------------
def _fetch_queue():
    idx = read_csv(GRANTEE_RAW / "_index_targets.csv")
    q = [r for r in idx if r.get("return_type") in SCHEDC_BEARING]
    return idx, q


EXTRA_MANIFEST = GRANTEE_RAW / "_zip_manifest_extra.csv"
FLOG_FIELDS = ["object_id", "ein", "tax_period", "return_type", "url",
               "zip_member", "http_status", "fetched_date"]


def all_archives(F):
    """Script 99's cached manifest plus any archive this script probed."""
    return list(m99().zip_manifest(F)) + read_csv(EXTRA_MANIFEST)


def step_fetchlog():
    """Give every retrieved return its true archive URL.

    A return can arrive by three routes - an HTTP range read, the DEFLATE64
    recovery pass, or a later pass over an archive the IRS page does not list -
    and only the first wrote the archive URL into the fetch log.  A row whose
    `source_url` names no document is a provenance hole, and this project's
    rule is that every published row cites the document it was read from.

    So the archives are re-opened by range read (central directory only, a few
    MB each), and each object id on disk is matched to the member that carries
    it.  Nothing is inferred: an object id is written against an archive only
    where that archive's own namelist contains the member.
    """
    log("=== 112 fetchlog ===")
    M = m99()
    idx, q = _fetch_queue()
    on_disk = {r["object_id"]: r for r in q
               if (GRANTEE_XML / f"{r['object_id']}.xml").exists()}
    flog = {r["object_id"]: r for r in read_csv(GRANTEE_RAW / "_xml_fetch_log.csv")}
    need = {oid: r for oid, r in on_disk.items()
            if not (flog.get(oid) or {}).get("url")}
    log(f"  returns on disk {len(on_disk):,};  missing an archive URL "
        f"{len(need):,}")
    if not need:
        return
    if not claim_host("apps.irs.gov", "archive central directories for provenance"):
        return
    try:
        F = M.Fetcher(gap=0.3)
        zips = all_archives(F)
        years = sorted({need[o]["index_year"] for o in need})
        for z in [x for x in zips if x["year"] in years]:
            if not need:
                break
            try:
                hf = M.HttpRangeFile(z["url"], F)
                import zipfile
                names = zipfile.ZipFile(hf).namelist()
            except Exception as e:
                log(f"  !! {z['name']}: {type(e).__name__} {e}")
                continue
            hit = 0
            for nm in names:
                oid = nm.rsplit("/", 1)[-1].split("_")[0]
                if oid in need:
                    r = need.pop(oid)
                    flog[oid] = {"object_id": oid, "ein": r["ein"],
                                 "tax_period": r["tax_period"],
                                 "return_type": r["return_type"],
                                 "url": z["url"], "zip_member": nm,
                                 "http_status": 200, "fetched_date": TODAY}
                    hit += 1
            if hit:
                log(f"  {z['name']}: {hit:,} object ids located "
                    f"({hf.bytes_read/1e6:.0f}MB read; {len(need):,} left)")
    finally:
        release_host("apps.irs.gov", "fetch-log provenance reconciliation done")
    # Anything indexed and NOT on disk keeps its honest status.
    for r in q:
        oid = r["object_id"]
        if oid in on_disk:
            continue
        flog.setdefault(oid, {"object_id": oid, "ein": r["ein"],
                              "tax_period": r["tax_period"],
                              "return_type": r["return_type"], "url": "",
                              "zip_member": "",
                              "http_status": "indexed_but_not_retrieved",
                              "fetched_date": TODAY})
    write_csv(GRANTEE_RAW / "_xml_fetch_log.csv",
              [flog[k] for k in sorted(flog)], FLOG_FIELDS)
    still = sum(1 for oid in on_disk if not (flog.get(oid) or {}).get("url"))
    log(f"  retrieved returns still without an archive URL: {still:,}")


def step_archives():
    """HEAD-probe for archives the IRS download page does not list.

    Measured on this run: the page lists exactly ONE archive for 2021 and one
    for 2022.  For 2021 that is correct - `2021_TEOS_XML_01A.zip` holds all
    589,904 returns of that submission year.  For 2022 it is not:
    `2022_TEOS_XML_01A.zip` holds 433,529 members against 656,503 rows in
    `index_2022.csv`, so roughly a third of the 2022 returns are in archives
    the page does not link.

    Script 99 already established the rule for this situation - the 2017 and
    2018 archives exist but are unlisted, and each candidate was accepted only
    on a real HTTP 200 with a Content-Length.  This does the same thing for the
    remaining years.  A URL is never inferred; it is probed and its status
    recorded.  Script 99's own `_zip_manifest.csv` is NOT modified - the extra
    archives are written to a separate file that this script merges at fetch
    time.
    """
    log("=== 112 archives ===")
    M = m99()
    _, q = _fetch_queue()
    missing_years = sorted({r["index_year"] for r in q
                            if not (GRANTEE_XML / f"{r['object_id']}.xml").exists()})
    log(f"  years with unretrieved returns: {missing_years}")
    known = {z["url"] for z in M.zip_manifest(M.Fetcher(gap=0.3))}
    rows = read_csv(EXTRA_MANIFEST)
    known |= {r["url"] for r in rows}
    if not claim_host("apps.irs.gov", "HEAD probe for unlisted IRS 990 archives"):
        return
    found = 0
    try:
        for y in missing_years:
            if int(y) < 2021:
                # 2017-2020 use download990xml_{Y}_{n}.zip and script 99 already
                # probed that sequence to its first non-200.
                continue
            for nn in range(1, 13):
                miss_in_a_row = 0
                for ab in "ABCD":
                    name = f"{y}_TEOS_XML_{nn:02d}{ab}.zip"
                    url = (f"https://apps.irs.gov/pub/epostcard/990/xml/{y}/"
                           f"{name}")
                    if url in known:
                        continue
                    try:
                        req = urllib.request.Request(
                            url, headers={"User-Agent": UA}, method="HEAD")
                        with urllib.request.urlopen(req, timeout=60) as r:
                            ok = (r.status == 200
                                  and r.headers.get("Content-Length"))
                            size = r.headers.get("Content-Length")
                    except Exception:
                        ok, size = False, ""
                    time.sleep(0.4)
                    if not ok:
                        miss_in_a_row += 1
                        continue
                    rows.append({
                        "year": y, "name": name, "url": url,
                        "content_length": size,
                        "basis": "probe_verified_http_200_not_page_listed",
                        "source_url": ("https://www.irs.gov/charities-non-"
                                       "profits/form-990-series-downloads"),
                        "fetched_date": TODAY})
                    found += 1
                    log(f"  + {name}  {int(size)/1e6:.0f}MB")
                if miss_in_a_row == 4:
                    break
    finally:
        release_host("apps.irs.gov", "unlisted-archive probe complete")
    if rows:
        write_csv(EXTRA_MANIFEST, rows,
                  ["year", "name", "url", "content_length", "basis",
                   "source_url", "fetched_date"])
    log(f"  archives found that the IRS page does not list: {found}")


def step_xml(max_fetch=None):
    log("=== 112 xml ===")
    M = m99()
    idx, q = _fetch_queue()
    if not idx:
        log("  no index; run --steps index first")
        return
    GRANTEE_XML.mkdir(parents=True, exist_ok=True)

    # Script 99 already holds 6,870 returns.  Any object id it retrieved is
    # reused rather than fetched a second time - the object_id is the return's
    # primary key, so this cannot be a different document.
    reused = 0
    for r in q:
        oid = r["object_id"]
        if (GRANTEE_XML / f"{oid}.xml").exists():
            continue
        p99 = SCHEDC_RAW / "xml" / f"{oid}.xml"
        if p99.exists():
            shutil.copyfile(p99, GRANTEE_XML / f"{oid}.xml")
            reused += 1
    log(f"  reused from script 99's cache: {reused:,}")

    queue = [r for r in q if not (GRANTEE_XML / f"{r['object_id']}.xml").exists()]
    log(f"  Schedule-C-bearing returns indexed {len(q):,}")
    log(f"  to fetch (not already cached)      {len(queue):,}")
    if max_fetch:
        queue = queue[:max_fetch]
    if not queue:
        return

    if not claim_host("apps.irs.gov",
                      "IRS 990 e-file returns via ZIP HTTP range reads (grantees)"):
        return

    want = {r["object_id"]: r for r in queue}
    fl = GRANTEE_RAW / "_xml_fetch_log.csv"
    seen = {r["object_id"]: r for r in read_csv(fl)}
    FLD = FLOG_FIELDS

    def flush():
        write_csv(fl, [seen[k] for k in sorted(seen)], FLD)

    F = M.Fetcher(gap=0.3)
    try:
        zips = list(M.zip_manifest(F)) + read_csv(EXTRA_MANIFEST)
        years = sorted({r["index_year"] for r in queue})
        todo = [z for z in zips if z["year"] in years]
        log(f"  zip archives to open: {len(todo)} (years {years})")
        n_ok = 0
        total_read = 0
        for z in todo:
            if not want:
                break
            try:
                hf = M.HttpRangeFile(z["url"], F)
                import zipfile
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
                try:
                    body = zf.read(nm)
                except Exception as e:
                    # DEFLATE64 (compression method 9) raises here.  Six of the
                    # 81 archives use it; the deflate64 step recovers them with
                    # the system 7-Zip.  Recorded, not smoothed.
                    log(f"    !! {oid}: {type(e).__name__} {str(e)[:60]}")
                    continue
                (GRANTEE_XML / f"{oid}.xml").write_bytes(body)
                r = want.pop(oid)
                got += 1
                n_ok += 1
                # UPSERT, never append-if-unseen: a second pass over an archive
                # the IRS page does not list must OVERWRITE the earlier
                # `indexed_but_not_retrieved` row, or the log would keep saying
                # a retrieved return was never retrieved.
                seen[oid] = {"object_id": oid, "ein": r["ein"],
                             "tax_period": r["tax_period"],
                             "return_type": r["return_type"],
                             "url": z["url"], "zip_member": nm,
                             "http_status": 200, "fetched_date": TODAY}
            total_read += hf.bytes_read
            log(f"  {z['name']}: {len(names):,} members, {len(bymember):,} ours,"
                f" extracted {got:,} ({hf.bytes_read/1e6:.0f}MB read; "
                f"{len(want):,} still wanted)")
            flush()
            if F.blocked:
                log("  !! host blocked; stopping (checkpoint written)")
                break
        for oid, r in want.items():
            if oid not in seen:
                seen[oid] = {"object_id": oid, "ein": r["ein"],
                             "tax_period": r["tax_period"],
                             "return_type": r["return_type"], "url": "",
                             "zip_member": "",
                             "http_status": "indexed_but_not_retrieved",
                             "fetched_date": TODAY}
        flush()
        log(f"  extracted ok={n_ok:,}  still missing={len(want):,}  "
            f"total range bytes={total_read/1e6:.0f}MB  stats={dict(F.stats)}")
    finally:
        release_host("apps.irs.gov", "grantee return retrieval complete")


def step_deflate64():
    """Recover returns CPython's `zipfile` cannot decompress.

    Six of the 81 IRS archives are written with DEFLATE64 (method 9).  Range
    reads do not help - the bytes arrive fine, the DECODER is missing.  So
    those archives are downloaded whole, opened with the system 7-Zip, the
    wanted members extracted, and the archive DELETED before the next starts.
    Peak disk is one archive, not all six.  If 7-Zip is absent the step does
    nothing and the affected rows keep the honest basis
    `efile_return_indexed_not_retrieved`.
    """
    log("=== 112 deflate64 ===")
    sevenzip = shutil.which("7z") or r"C:\Program Files\7-Zip\7z.exe"
    if not Path(sevenzip).exists():
        log("  7-Zip not found; DEFLATE64 archives cannot be read. Skipping.")
        return
    M = m99()
    _, q = _fetch_queue()
    want = {r["object_id"]: r for r in q
            if not (GRANTEE_XML / f"{r['object_id']}.xml").exists()}
    log(f"  still missing: {len(want):,} returns")
    if not want:
        return
    if not claim_host("apps.irs.gov", "DEFLATE64 archive download (grantees)"):
        return
    try:
        zips = {z["name"]: z for z in M.zip_manifest(M.Fetcher(gap=0.3))}
        # The six method-9 archives, identified by measurement in script 99.
        targets = ["2020_TEOS_XML_CT1.zip", "2025_TEOS_XML_05A.zip",
                   "2025_TEOS_XML_05B.zip", "2025_TEOS_XML_11B.zip",
                   "2026_TEOS_XML_05A.zip", "2026_TEOS_XML_05B.zip"]
        need_years = {r["index_year"] for r in want.values()}
        tmp = GRANTEE_RAW / "_tmp"
        tmp.mkdir(exist_ok=True)
        got = 0
        for name in targets:
            z = zips.get(name)
            if not z or not want or z["year"] not in need_years:
                continue
            local = tmp / name
            log(f"  downloading {name} ...")
            try:
                req = urllib.request.Request(z["url"],
                                             headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=1800) as r, \
                        open(local, "wb") as fh:
                    shutil.copyfileobj(r, fh, 1 << 20)
            except Exception as e:
                log(f"    !! download failed: {type(e).__name__} {e}")
                local.unlink(missing_ok=True)
                continue
            out = tmp / "x"
            if out.exists():
                shutil.rmtree(out, ignore_errors=True)
            out.mkdir()
            listing = subprocess.run([sevenzip, "l", "-ba", "-slt", str(local)],
                                     capture_output=True, text=True).stdout
            members = re.findall(r"^Path = (.+\.xml)$", listing, re.M)
            mine = [mm for mm in members
                    if mm.rsplit("\\", 1)[-1].rsplit("/", 1)[-1].split("_")[0]
                    in want]
            log(f"    {len(members):,} members, {len(mine):,} ours")
            for chunk in [mine[i:i + 200] for i in range(0, len(mine), 200)]:
                subprocess.run([sevenzip, "e", "-y", f"-o{out}", str(local)]
                               + chunk, capture_output=True, text=True)
            for f in out.glob("*.xml"):
                oid = f.name.split("_")[0]
                if oid in want:
                    shutil.move(str(f), str(GRANTEE_XML / f"{oid}.xml"))
                    want.pop(oid, None)
                    got += 1
            shutil.rmtree(out, ignore_errors=True)
            local.unlink(missing_ok=True)
            log(f"    recovered {got:,} so far; {len(want):,} still missing")
        shutil.rmtree(tmp, ignore_errors=True)
        log(f"  recovered {got:,} returns from DEFLATE64 archives")
    finally:
        release_host("apps.irs.gov", "DEFLATE64 recovery complete")


# ---------------------------------------------------------------------------
# STEP: build
# ---------------------------------------------------------------------------
# TOTAL REVENUE / TOTAL EXPENSES.  These tag names were OBSERVED, not guessed:
# a tag inventory was taken over the retrieved returns (1,096 Form 990,
# 378 Form 990-EZ, 163 Form 990-PF) before this was written, for the same
# reason script 99's docstring gives - a plausible invented element name
# produces a silently empty column that looks like a finding.
CORE_TOTALS = {
    "IRS990":   ("CYTotalRevenueAmt", "CYTotalExpensesAmt"),
    "IRS990EZ": ("TotalRevenueAmt", "TotalExpensesAmt"),
    # 990-PF Part I column (a), "Revenue and expenses per books".
    "IRS990PF": ("TotalRevAndExpnssAmt", "TotalExpensesRevAndExpnssAmt"),
}

FIELDS = [
    "ein", "org_name", "tax_year", "return_type", "schedc_filed",
    "schedc_501h_election", "lobbying_expenditure", "grassroots_lobbying",
    "direct_lobbying", "political_activity", "partix_line11d_lobbying_fees",
    "total_revenue", "total_expenses", "schedc_expected", "source_url",
    "retrieved_date", "tier", "confidence", "built_date",
]

NO_CAUSATION = ("This row records a filing fact about one organisation. It "
                "does not state that any grant paid for any lobbying, and no "
                "column in this dataset supports that reading.")
LEGITIMACY = ("Lobbying reported on a Form 990 is disclosed, lawful activity "
              "within the limits of the organisation's tax status; many "
              "organisations elect 501(h) precisely to report it "
              "transparently.")
DUES_NOTE = ("Membership organisation: funded by its tribal members and "
             "advocating on their behalf is its stated purpose, not a "
             "concealed channel. Membership dues are not a Schedule I grant "
             "and appear in no public filing, so the ordinary way a tribe "
             "funds such a body is invisible by construction.")

# Typed from the spine's own membership classes plus the organisations named in
# docs/ADVOCACY_PASSTHROUGH_LOG.md.  This is a NOTE, never a characterisation.
MEMBERSHIP_CLASSES = {"Intertribal Organization",
                      "Federal-level self-governance consortium"}


def _filer_name(hdr):
    """Both name lines joined.  See grantee_context() for why."""
    n1 = n2 = ""
    filer = None
    for el in hdr.iter():
        if el.tag.split("}")[-1] == "Filer":
            filer = el
            break
    if filer is None:
        return ""
    for el in filer.iter():
        t = el.tag.split("}")[-1]
        if t == "BusinessNameLine1Txt" and not n1 and el.text:
            n1 = el.text.strip()
        elif t == "BusinessNameLine2Txt" and not n2 and el.text:
            n2 = el.text.strip()
    return (n1 + " " + n2).strip()


def parse_return(path):
    """Schedule C + Part IX 11d + totals out of one e-file return."""
    try:
        raw = Path(path).read_bytes()
        root = ET.fromstring(raw)
    except Exception as e:
        return {"_error": type(e).__name__}
    sc = m99().parse_schedule_c(raw)
    out = dict(sc)
    n = IRS_NS
    hdr = root.find(f"{n}ReturnHeader")
    if hdr is not None:
        out["_name"] = _filer_name(hdr)
        for tag, col in ((f"{n}ReturnTypeCd", "_return_type"),
                         (f"{n}TaxPeriodEndDt", "_period_end")):
            el = hdr.find(tag)
            if el is not None and (el.text or "").strip():
                out[col] = el.text.strip()
    data = root.find(f"{n}ReturnData")
    if data is not None:
        for form, (rev, exp) in CORE_TOTALS.items():
            core = data.find(f"{n}{form}")
            if core is None:
                continue
            out["_form"] = form
            for tag, col in ((rev, "_revenue"), (exp, "_expenses")):
                el = core.find(f"{n}{tag}")
                if el is not None and (el.text or "").strip():
                    out[col] = el.text.strip()
    return out


def step_build():
    log("=== 112 build ===")
    src = target_eins()
    ctx = grantee_context()
    idx = read_csv(GRANTEE_RAW / "_index_targets.csv")
    fetchlog = {r["object_id"]: r
                for r in read_csv(GRANTEE_RAW / "_xml_fetch_log.csv")}
    spine = read_csv(CEDAR / "data" / "spine" / "cedar_entity_spine.csv")
    membership = {r["canonical_name"].strip().lower() for r in spine
                  if r.get("entity_class") in MEMBERSHIP_CLASSES}
    G = m111()

    by_ein = defaultdict(list)
    for r in idx:
        by_ein[r["ein"]].append(r)

    rows, review, join_rows = [], [], defaultdict(list)
    stat = Counter()
    for ein in sorted(src):
        c = ctx.get(ein) or {"names": set(), "state": "", "irc": set(),
                             "funders": set(), "schedi_url": "",
                             "irs_name": "", "irs_status": "",
                             "bmf_regime": "", "in_np_orgs": 0}
        filed = [r for r in by_ein.get(ein, [])
                 if r.get("return_type") in SCHEDC_BEARING]
        got = [r for r in filed
               if (GRANTEE_XML / f"{r['object_id']}.xml").exists()]

        # --- schedc_expected, the load-bearing column ----------------------
        regime = c["bmf_regime"]
        if filed:
            expected, exp_basis = 1, ("an e-filed Form 990/990-EZ/990-PF is "
                                      "indexed by the IRS for this EIN, so a "
                                      "Schedule C could exist")
        elif regime == "990_N":
            expected, exp_basis = 0, ("990-N e-Postcard filer per the IRS "
                                      "Business Master File filing requirement "
                                      "code: no Schedule C EXISTS to be filed, "
                                      "and no zero may be recorded here")
        elif regime == "not_required":
            expected, exp_basis = 0, ("the IRS Business Master File records no "
                                      "filing requirement for this EIN")
        elif c["irs_status"] == "FETCH_FAILED" or (
                not c["irs_name"] and not c["in_np_orgs"]):
            expected, exp_basis = 0, (
                "this EIN has no IRS Business Master File record and no e-filed "
                "return in the 2017-2026 index. An EIN printed on a filed "
                "Schedule I but absent from the BMF is the signature of an "
                "entity outside the Form 990 universe - most often a tribal "
                "government or instrumentality under IRC 7871, which files no "
                "Form 990 at all")
        else:
            expected, exp_basis = 1, (
                "the IRS holds a Business Master File record for this EIN but "
                "no e-filed return is indexed for submission years 2017-2026; "
                "the filing regime is not established from any source on disk, "
                "so a Schedule C is treated as possible rather than ruled out")
        stat[f"expected_{expected}"] += 1

        name_pool = [x for x in ([c["irs_name"]] + sorted(c["names"])) if x]
        base_name = name_pool[0] if name_pool else ""
        is_member = base_name.strip().lower() in membership

        if not got:
            # ABSENT IS NOT ZERO, and the row says WHICH absence it is.
            if filed:
                why = ("efile_return_indexed_but_not_retrieved: the IRS index "
                       f"lists {len(filed)} return(s) for this EIN but none "
                       "could be extracted from the ZIP archives")
                url = filed[0]["index_url"]
            elif expected == 0:
                why = "no_return_expected: " + exp_basis
                url = c["schedi_url"] or ""
            else:
                why = "no_efile_return_indexed_2017_2026: " + exp_basis
                url = c["schedi_url"] or ""
            stat["ein_no_return"] += 1
            note = [NO_CAUSATION, why]
            if is_member:
                note.append(DUES_NOTE)
            rows.append(dict(
                ein=ein, org_name=base_name, tax_year="", return_type="",
                schedc_filed="", schedc_501h_election="",
                lobbying_expenditure="", grassroots_lobbying="",
                direct_lobbying="", political_activity="",
                partix_line11d_lobbying_fees="", total_revenue="",
                total_expenses="", schedc_expected=expected,
                source_url=url, retrieved_date=TODAY,
                tier=Tier.B.value,
                confidence=("No Form 990 was retrieved for this EIN. " +
                            " ".join(note)),
                built_date=TODAY))
            review.append(dict(
                review_id=f"G990-{ein}", queue="grantee_990",
                ein=ein, org_name=base_name,
                state=c["state"], funders=";".join(sorted(c["funders"]))[:300],
                irc_section_as_filed=";".join(sorted(x for x in c["irc"] if x)),
                schedc_expected=expected, reason=why,
                source_url=url, question=(
                    "No machine-readable Form 990 exists for this EIN in the "
                    "IRS e-file index. Is this organisation outside the 990 "
                    "universe (a tribal government or instrumentality under "
                    "IRC 7871, a fiscally sponsored project filed under a "
                    "sponsor's EIN), a 990-N postcard filer, or a paper "
                    "filer?"),
                YOUR_RULING="", YOUR_NOTE=""))
            continue

        for r in sorted(got, key=lambda x: x["tax_period"]):
            oid = r["object_id"]
            p = parse_return(GRANTEE_XML / f"{oid}.xml")
            if p.get("_error"):
                stat["parse_error"] += 1
                continue
            stat["returns_parsed"] += 1
            period = (r.get("tax_period") or "")[:4] or (p.get("_period_end") or "")[:4]
            nm = p.get("_name") or r.get("taxpayer_name") or base_name
            amt, basis = m99()._consolidate_lobbying(p)
            schedc_filed = "1" if p.get("schedc_present") == "1" else "0"
            if schedc_filed == "1":
                stat["schedc_filed"] += 1
            if amt not in ("", None) and numf(amt) and numf(amt) > 0:
                stat["lobbying_gt_zero"] += 1
            p9 = p.get("form990_part9_lobbying_fees") or ""
            if numf(p9) and numf(p9) > 0:
                stat["part9_gt_zero"] += 1

            fl = fetchlog.get(oid) or {}
            zurl = fl.get("url") or ""
            url = ((zurl or "https://apps.irs.gov/pub/epostcard/990/xml/") +
                   f" (IRS e-file return object_id {oid}, member "
                   f"{oid}_public.xml)")

            note = [NO_CAUSATION]
            if schedc_filed == "1":
                note.append(LEGITIMACY)
                note.append("Reporting basis: " + (basis or "not determinable") +
                            ". " + (p.get("schedc_501h_basis") or ""))
            else:
                note.append("This return carries NO Schedule C. The filer "
                            "answered the Form 990 Part IV lobbying question "
                            "'No', so the schedule was not required. That is a "
                            "reported fact and is different from a filer that "
                            "completed the schedule and reported $0.")
            note.append("Part IX line 11d counts fees paid to OUTSIDE "
                        "lobbyists and Schedule C counts the organisation's "
                        "OWN expenditure; they are kept in separate columns "
                        "and are never added.")
            if is_member:
                note.append(DUES_NOTE)

            row = dict(
                ein=ein, org_name=nm, tax_year=period,
                return_type=p.get("_return_type") or r.get("return_type") or "",
                schedc_filed=schedc_filed,
                schedc_501h_election=p.get("schedc_501h_election") or "",
                lobbying_expenditure=amt or "",
                grassroots_lobbying=p.get("schedc_grassroots_lobbying") or "",
                direct_lobbying=p.get("schedc_direct_lobbying") or "",
                political_activity=p.get("form990_political_activity_ind") or "",
                partix_line11d_lobbying_fees=p9,
                total_revenue=p.get("_revenue") or "",
                total_expenses=p.get("_expenses") or "",
                schedc_expected=1, source_url=url, retrieved_date=TODAY,
                tier=Tier.A.value,
                confidence=("Every figure is read from this EIN's own filed "
                            "Form 990, retrieved from the IRS e-file archive "
                            "and keyed on the return's object id. " +
                            " ".join(note)),
                built_date=TODAY)
            rows.append(row)

            # The join view script 111 consumes.  Same column names, so the
            # existing `lobbying_990()` reads it without modification.
            join_rows[ein].append({
                "ein": ein, "tax_year": period,
                "schedc_lobbying_usd": amt or "",
                "form990_part9_lobbying_fees": p9,
                "schedc_source_url": url,
                "schedc_basis": ("irs_efile_xml_schedule_c" if schedc_filed == "1"
                                 else "irs_efile_xml_no_schedule_c_filed"),
                "form990_lobbying_activities_ind":
                    p.get("form990_lobbying_activities_ind") or "",
                "form990pf_influence_legislation_ind":
                    p.get("form990pf_influence_legislation_ind") or "",
                "source_url": url})

    write_csv(OUT, rows, FIELDS)
    write_csv(OUT_REVIEW, review,
              ["review_id", "queue", "ein", "org_name", "state", "funders",
               "irc_section_as_filed", "schedc_expected", "reason",
               "source_url", "question", "YOUR_RULING", "YOUR_NOTE"])
    (GRANTEE_RAW / "_join_view.json").write_text(
        json.dumps(join_rows), encoding="utf-8")

    n_indexed = len([r for r in idx if r.get("return_type") in SCHEDC_BEARING])
    n_got = stat["returns_parsed"]
    log(f"  target EINs                        {len(src):,}")
    log(f"  Schedule-C-bearing returns indexed {n_indexed:,}")
    log(f"  returns retrieved and parsed       {n_got:,} "
        f"({100.0*n_got/n_indexed if n_indexed else 0:.1f}%)")
    log(f"  rows where a Schedule C could exist (schedc_expected=1) "
        f"{stat['expected_1']:,}")
    log(f"  EINs excluded, NOT zeroed (schedc_expected=0) {stat['expected_0']:,}")
    log(f"  returns carrying a Schedule C      {stat['schedc_filed']:,}")
    log(f"  returns with lobbying expenditure > 0 {stat['lobbying_gt_zero']:,}")
    log(f"  returns with Part IX 11d fees > 0     {stat['part9_gt_zero']:,}")
    return rows, stat


# ---------------------------------------------------------------------------
# STEP: passthrough  - re-run script 111's join with the new 990 leg
# ---------------------------------------------------------------------------
def step_passthrough():
    """Re-run the pass-through join with the grantee returns in the 990 leg.

    `advocacy_passthrough.csv` is NOT rewritten - another build owns it and the
    task forbids editing it.  The refreshed file is a dated sibling.
    """
    log("=== 112 passthrough ===")
    G = m111()
    D = G.load_all()
    jv = json.loads((GRANTEE_RAW / "_join_view.json").read_text(encoding="utf-8"))
    added = 0
    for ein, rs in jv.items():
        D["np_fin_by_ein"][ein].extend(rs)
        added += len(rs)
    log(f"  grantee 990 rows added to the join view: {added:,} over "
        f"{len(jv):,} EINs")

    edges, refused = G.step_funding(D)
    lda_idx = G.build_lda_index()
    rows, review = G.step_join(D, edges, lda_idx)
    write_csv(OUT_PASSTHROUGH, rows, G.FIELDS)

    # Compare on the row's CONTENT, not on passthrough_id: the id is a running
    # counter and would silently misalign if the edge order ever changed.
    def key(r):
        return (r.get("funder_name", ""), r.get("recipient_ein", ""),
                r.get("recipient_org_name", ""), r.get("grant_year", ""),
                r.get("grant_amount_usd", ""))

    prev = read_csv(CLEAN / "advocacy_passthrough.csv")
    old = {key(r): r for r in prev}
    comp = Counter(r["chain_completeness"] for r in rows)
    oldc = Counter(r["chain_completeness"] for r in prev)
    flipped = [r for r in rows
               if r["chain_completeness"] == "FUNDING_AND_LOBBYING_BOTH_DOCUMENTED"
               and (old.get(key(r)) or {}).get("chain_completeness")
               == "FUNDING_ONLY"]
    via990 = [r for r in flipped
              if "FORM990" in (r.get("recipient_lobbying_source") or "")]
    # ---------------------------------------------------------------------
    # A REFUSAL THE 990 LEG MADE VISIBLE, and it must not publish quietly.
    #
    # The largest lobbying figure this build recovered is $43,568,567 on the
    # Form 990 of NEW VENTURE FUND (EIN 20-5806345), a Washington DC fiscal
    # sponsor with roughly $900M of annual expenses.  The philanthropy review
    # queue proposes `NATIVE_ORG` for that EIN - but read its own note: the
    # evidence is First Nations' grantee profile for **Alaska Native
    # Birthworkers Community**, a fiscally SPONSORED PROJECT.  The project is
    # Native; the legal person that received the money and filed the return is
    # not.  `docs/PHILANTHROPY_DISCOVERY_LOG.md` names this exact failure mode:
    # "the grantee named is not always the legal person paid."
    #
    # Attaching a $43.6M national lobbying total to a Native organisation on
    # that basis is the false attribution this project forbids, and it is the
    # same shape as Guard 8 - a separate legal person carrying another body's
    # work.  Nothing here rewrites the queue (it is another build's file and
    # those rulings await Elijah).  Every such row is pushed into the review
    # queue with the dollar figure attached, so the question is unavoidable.
    q = []
    for r in rows:
        usd = numf(r.get("recipient_lobbying_expenditure"))
        if not usd or usd <= 0:
            continue
        if "FORM990" not in (r.get("recipient_lobbying_source") or ""):
            continue
        if "philanthropy_queue_proposed_ruling" not in (r.get("evidence_note") or ""):
            continue
        q.append(r)
    seen_q = set()
    for r in sorted(q, key=lambda x: -(numf(x["recipient_lobbying_expenditure"]) or 0)):
        if r["recipient_ein"] in seen_q:
            continue
        seen_q.add(r["recipient_ein"])
        review.append(dict(
            review_id=f"G990-TYPE-{r['recipient_ein']}", queue="grantee_990",
            ein=r["recipient_ein"], org_name=r["recipient_org_name"],
            state="", funders=r["funder_name"],
            irc_section_as_filed="", schedc_expected=1,
            reason=("recipient typed NATIVE_NONPROFIT on an agent-proposed "
                    "philanthropy-queue ruling, not a human one, and it now "
                    "carries a lobbying figure of $"
                    f"{numf(r['recipient_lobbying_expenditure']):,.0f} from its "
                    "own Form 990"),
            source_url=r["source_url_lobbying"],
            question=("Is this organisation itself the Native entity, or is it "
                      "a FISCAL SPONSOR whose sponsored project is the Native "
                      "one? A fiscally sponsored project has no EIN and files "
                      "under its sponsor's, so the organisation named on a "
                      "grantee list is not always the legal person paid or the "
                      "legal person that reported this lobbying. If it is the "
                      "sponsor, this lobbying total is the sponsor's own and "
                      "must not be attributed to a Native organisation."),
            YOUR_RULING="", YOUR_NOTE=""))
    if seen_q:
        rev_path = REVIEW / f"grantee_990_unresolved_{TODAY}.csv"
        existing = read_csv(rev_path)
        existing_ids = {r["review_id"] for r in existing}
        add = [r for r in review if r.get("review_id", "").startswith("G990-TYPE-")
               and r["review_id"] not in existing_ids]
        write_csv(rev_path, existing + add,
                  ["review_id", "queue", "ein", "org_name", "state", "funders",
                   "irc_section_as_filed", "schedc_expected", "reason",
                   "source_url", "question", "YOUR_RULING", "YOUR_NOTE"])
        log(f"  recipients whose Native typing rests on a proposed ruling AND "
            f"now carry a 990 lobbying figure: {len(seen_q)} (sent to review)")

    log(f"  chain_completeness BEFORE: {dict(oldc)}")
    log(f"  chain_completeness AFTER : {dict(comp)}")
    log(f"  FUNDING_ONLY -> BOTH_DOCUMENTED: {len(flipped):,} rows "
        f"({len({r['recipient_ein'] for r in flipped}):,} recipients); "
        f"{len(via990):,} of them on the new 990 leg")
    return rows, review, comp, oldc, flipped, via990


# ---------------------------------------------------------------------------
# STEP: codebook  - VARIABLES ONLY, and defensively
# ---------------------------------------------------------------------------
DESCRIPTIONS = {
    "ein": "Employer Identification Number of the grantee organisation, as printed on the funder's filed Form 990 Schedule I Part II.",
    "org_name": "Organisation name from its own filed return, with BusinessNameLine1Txt and BusinessNameLine2Txt joined because IRS e-file splits a name at 35 characters. Falls back to the IRS index taxpayer name.",
    "tax_year": "Year of the tax period the return covers. Blank where no return was retrieved.",
    "return_type": "Form filed: 990, 990EZ, 990PF, 990O or 990EO.",
    "schedc_filed": "1 where the return carries a Schedule C, 0 where it does not, blank where no return was retrieved. A filer answering 'No' to the Form 990 Part IV lobbying question files no Schedule C at all; that is different from filing one and reporting $0.",
    "schedc_501h_election": "1 where the filer completed Schedule C Part II-A (only a 501(h) electing organisation does), 0 where it completed Part II-B, blank where neither is determinable. The election itself is made on Form 5768 and Schedule C carries no element for it, so this value is derived and the confidence field says so.",
    "lobbying_expenditure": "The organisation's own lobbying expenditure in US dollars: Schedule C Part II-A total for 501(h) electing filers, otherwise the Part II-B total for non-electing filers. The two regimes are ranked and never added. Column (a), the filing organisation, only; column (b) is an affiliated group and is a different legal person's money.",
    "grassroots_lobbying": "Grassroots lobbying expenditure, US dollars, Schedule C Part II-A. Exists only for 501(h) electing filers; Part II-B has no such line, so a blank here is the form's structure, not a failed parse.",
    "direct_lobbying": "Direct lobbying expenditure, US dollars, Schedule C Part II-A. Same structural caveat as grassroots_lobbying.",
    "political_activity": "Form 990 Part IV political campaign activity indicator, 1 or 0, as answered on the return. An indicator, not a dollar amount.",
    "partix_line11d_lobbying_fees": "Form 990 Part IX line 11d, fees paid to OUTSIDE lobbyists, US dollars. A different measurement from Schedule C, which counts the organisation's own expenditure. The two are never added and neither substitutes for the other.",
    "total_revenue": "Total revenue in US dollars from the return's own core form.",
    "total_expenses": "Total expenses in US dollars from the return's own core form.",
    "schedc_expected": "1 where a Schedule C could exist for this EIN, 0 where none could. A 990-N e-Postcard filer, an EIN with no filing requirement, and an EIN outside the Form 990 universe under IRC 7871 all report no financial detail at all: zero lobbying there is the filing regime and not a finding. Any denominator built without this column is wrong by construction.",
    "source_url": "The document this row was read from: the IRS e-file ZIP archive plus the return's object id, or where no return exists, the IRS index or the funder's own filed Schedule I that names the EIN.",
    "retrieved_date": "Date the return was retrieved.",
    "tier": "A publishes; B is internal only. Tier A means every figure was read from this EIN's own filed return, keyed on the return object id. Tier B rows are statements of absence.",
    "confidence": "What this row does and does not establish, in words, including which absence a blank represents and the explicit statement that no causal link is asserted.",
    "built_date": "Build date.",
}


def step_codebook(rows):
    """Write our variables and RESTORE anything a concurrent write dropped.

    codebook_master.csv is being clobbered by concurrent writes. Procedure:
    back up, re-read immediately before writing, keep every row we did not
    write, and report what was restored.
    """
    log("=== 112 codebook ===")
    p = CLEAN / "codebook_master.csv"
    bak = p.with_suffix(f".csv.bak_{TODAY}_pre112")
    if p.exists() and not bak.exists():
        bak.write_bytes(p.read_bytes())
        log(f"  backup {bak.name}")
    cb = read_csv(p)                     # re-read IMMEDIATELY before writing
    if not cb:
        log("  codebook_master.csv absent - skipping")
        return {}
    fields = list(cb[0].keys())
    ds = "04d_grantee_990_financials"
    kept = [r for r in cb if r.get("dataset") != ds]
    before = {(r.get("dataset"), r.get("variable")) for r in cb}

    n = len(rows)
    for v in FIELDS:
        filled = sum(1 for r in rows if str(r.get(v, "")).strip() != "")
        kept.append({
            "dataset": ds, "variable": v,
            "type": ("number" if v in (
                "lobbying_expenditure", "grassroots_lobbying",
                "direct_lobbying", "partix_line11d_lobbying_fees",
                "total_revenue", "total_expenses", "schedc_filed",
                "schedc_expected", "schedc_501h_election",
                "political_activity")
                else "date" if v in ("retrieved_date", "built_date")
                else "text"),
            "units": ("USD" if v in (
                "lobbying_expenditure", "grassroots_lobbying",
                "direct_lobbying", "partix_line11d_lobbying_fees",
                "total_revenue", "total_expenses") else ""),
            "pct_filled": f"{(100.0 * filled / n if n else 0):.1f}",
            "n_rows": n, "published": "1", "access_tier": "public",
            "description": DESCRIPTIONS[v], "generated": TODAY})

    # Restore anything present in the backup but missing from the file we just
    # read - i.e. rows a concurrent write dropped between the two reads.
    restored = 0
    if bak.exists():
        have = {(r.get("dataset"), r.get("variable")) for r in kept}
        for r in read_csv(bak):
            k = (r.get("dataset"), r.get("variable"))
            if r.get("dataset") == ds:
                continue
            if k not in have:
                kept.append(r)
                have.add(k)
                restored += 1
    write_csv(p, kept, fields)
    log(f"  codebook rows before {len(before):,}, after {len(kept):,}, "
        f"restored from backup {restored:,}, ours {len(FIELDS)}")
    return {"restored": restored, "ours": len(FIELDS), "total": len(kept)}


# ---------------------------------------------------------------------------
# STEP: report
# ---------------------------------------------------------------------------
def step_report():
    log("=== 112 report ===")
    rows = read_csv(OUT)
    idx = read_csv(GRANTEE_RAW / "_index_targets.csv")
    src = target_eins()
    phil = {e for e, s in src.items() if "philanthropy_schedule_i" in s}
    R = []
    a = R.append
    a(f"Cedar Press 112 - grantee 990 pull, {TODAY}")
    a("=" * 72)
    n_idx = len([r for r in idx if r.get("return_type") in SCHEDC_BEARING])
    got = [r for r in rows if r.get("tax_year")]
    a(f"target EINs                          {len(src):,}")
    a(f"  of which philanthropy grantees     {len(phil):,}")
    a(f"Schedule-C-bearing returns indexed   {n_idx:,}")
    a(f"returns retrieved and parsed         {len(got):,} "
      f"({100.0*len(got)/n_idx if n_idx else 0:.1f}% retrieval rate)")
    exp1 = [r for r in rows if str(r.get("schedc_expected")) == "1"]
    exp0 = [r for r in rows if str(r.get("schedc_expected")) == "0"]
    a(f"rows where a Schedule C COULD exist  {len(exp1):,}")
    a(f"rows excluded, NOT zeroed            {len(exp0):,}")
    a(f"Schedule C filed                     "
      f"{sum(1 for r in got if r['schedc_filed'] == '1'):,}")
    a(f"lobbying expenditure > 0             "
      f"{sum(1 for r in got if (numf(r['lobbying_expenditure']) or 0) > 0):,}")
    a(f"Part IX 11d fees > 0                 "
      f"{sum(1 for r in got if (numf(r['partix_line11d_lobbying_fees']) or 0) > 0):,}")
    tot = sum(numf(r["lobbying_expenditure"]) or 0 for r in got)
    a(f"total lobbying expenditure recovered ${tot:,.0f}")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(R), encoding="utf-8")
    print("\n".join(R))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", default="report")
    ap.add_argument("--max-fetch", type=int, default=None)
    ap.add_argument("--years", default=None)
    args = ap.parse_args()
    years = [int(x) for x in args.years.split(",")] if args.years else None
    built = None
    for s in [x.strip() for x in args.steps.split(",") if x.strip()]:
        if s == "index":
            step_index(years)
        elif s == "archives":
            step_archives()
        elif s == "xml":
            step_xml(args.max_fetch)
        elif s == "fetchlog":
            step_fetchlog()
        elif s == "deflate64":
            step_deflate64()
        elif s == "build":
            built = step_build()
        elif s == "passthrough":
            step_passthrough()
        elif s == "codebook":
            step_codebook((built or (read_csv(OUT), None))[0])
        elif s == "report":
            step_report()
        else:
            log(f"unknown step {s}")


if __name__ == "__main__":
    main()
