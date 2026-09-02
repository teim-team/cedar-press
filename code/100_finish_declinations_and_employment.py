#!/usr/bin/env python3
"""
Cedar Press - 100: finish the NIGC declination layer, and build property
employment observations.

ONE SCRIPT, SWITCHES (project convention):

    ocr [shard n]  OCR the 160 image-only declination PDFs into a text cache.
                   Long-running; shardable; writes only to the cache.
    index          Re-fetch the NIGC declination index and diff it against what
                   is held. Fetch any letter published since the last pull.
    osha           Retrieve OSHA ITA 300A establishment summaries CY2016-CY2025.
    geocode        Resolve gaming facilities to 2020 census BLOCKS.
    lodes          Pull LODES8 WAC block workplace jobs for those blocks.
    build          Verify the declination layer, apply the OCR recovery, write
                   the evidentiary-ladder columns, build the deals-ledger
                   contradiction file, and assemble the employment observations.

WHAT THIS LAYER IS AND IS NOT
-----------------------------
A declination letter proves the NIGC Office of General Counsel REVIEWED
SUBMITTED, UNEXECUTED DOCUMENTS and reached a legal conclusion. In the agency's
own words on its index page: "Documents should be submitted prior to their
execution (unsigned)"; "This review is neither required by [IGRA] nor the NIGC
regulations and is offered by the OGC as a courtesy."

The ladder below is written on every row and is never collapsed:

    NIGC_REVIEWED -> EXECUTION_UNCONFIRMED -> EXECUTED_CONFIRMED
                  -> CLOSED_CONFIRMED -> SUPERSEDED / TERMINATED

This archive can only ever establish the first two rungs. Anything past
EXECUTION_UNCONFIRMED needs a different source, and the column that says so
travels with the row so the caveat cannot be lost in a join.

FIVE LEGAL PERSONS, NOT ONE
---------------------------
Tribe, gaming authority, gaming enterprise, property-owning subsidiary and
operating company are five different legal persons. The letters are frequently
the only public source that distinguishes them, and that distinction is the
asset. Containment matching is refused outright for a claim party - it would
resolve "Twenty-Nine Palms Enterprises Corporation" onto the tribe.

MANY-TO-MANY, ALWAYS
--------------------
A letter is never attached to a property because the enterprise owns that
property. Financings routinely cover several properties, an entire enterprise,
unrestricted assets, or a project that does not exist yet.

EMPLOYMENT: MULTIPLE INDEPENDENT FIGURES ARE A FEATURE
------------------------------------------------------
OSHA establishment-reported employment, LODES block workplace jobs, an
environmental review's projection and a tribe's own reported count measure four
different things. All are retained with their own measurement_type.
`cedar_domain.may_promote()` refuses PROJECTED -> ACTIVE. LODES block jobs are
NOT casino payroll when other employers share the block, and every LODES row
says so in its own note.

NO PROPERTY-LEVEL GAMING REVENUE IS PRODUCED ANYWHERE IN THIS SCRIPT.
"""

import sys as _sys_cd
from pathlib import Path as _Path_cd
_sys_cd.path.insert(0, str(_Path_cd(__file__).resolve().parent))
import cedar_domain as DOM   # noqa: E402  - DEALS_TRUTH, PROMOTED_TABLES

import csv
import glob
import gzip
import hashlib
import html as htmllib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import time
import zipfile
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
RAW = CEDAR / "data" / "raw" / "external" / "nigc_declinations"
OCRDIR = RAW / "_ocr"
OSHA = CEDAR / "data" / "raw" / "external" / "osha_ita"
LODESDIR = CEDAR / "data" / "raw" / "external" / "lodes"
TEXTCACHE = CEDAR / "data" / "raw" / "external" / "_pdf_textcache"
REVIEW = CEDAR / "review"
DOCS = CEDAR / "docs"
LOGS = CEDAR / "logs"
TODAY = date.today().isoformat()

INDEX_URL = ("https://www.nigc.gov/office-of-general-counsel/legal-opinions/"
             "declination-letters/")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# WPDM ids on the index page that are NOT declination letters. Recorded in
# docs/NIGC_DECLINATION_BUILD_LOG.md 1.1: a scraper that takes links from the
# page rather than from inside the table starts with these two.
NON_LETTER_WPDMDL = {"3974", "7374"}

EVIDENTIARY_LADDER = ("NIGC_REVIEWED -> EXECUTION_UNCONFIRMED -> "
                      "EXECUTED_CONFIRMED -> CLOSED_CONFIRMED -> "
                      "SUPERSEDED / TERMINATED")


# --------------------------------------------------------------- utilities
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
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    try:
        rel = p.relative_to(CEDAR)
    except ValueError:
        rel = p
    print(f"  wrote {rel}  ({len(rows):,} rows)")


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def flat(s):
    s = (s or "").replace("\u00ad", "")
    s = s.replace("\u2019", "'").replace("\u2018", "'")
    s = s.replace("\u201c", '"').replace("\u201d", '"')
    return re.sub(r"\s+", " ", s).strip()


# ------------------------------------------------------------ pull discipline
def claim_lock(host, script, note):
    """docs/PULL_DISCIPLINE.md rule 2. True only if we hold the host."""
    LOGS.mkdir(parents=True, exist_ok=True)
    lock = LOGS / f"_HOSTLOCK_{host}.json"
    if lock.exists():
        try:
            cur = json.load(open(lock))
        except Exception:
            cur = {}
        pid = cur.get("pid")
        alive = False
        if pid and pid != os.getpid():
            try:
                out = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     f"(Get-Process -Id {pid} -ErrorAction SilentlyContinue) "
                     f"-ne $null"],
                    capture_output=True, text=True, timeout=60).stdout.strip()
                alive = out.lower().startswith("true")
            except Exception:
                alive = False
        if alive:
            cur.setdefault("queue", []).append(
                {"requested_by": script,
                 "requested_at": datetime.now().isoformat(), "work": note})
            json.dump(cur, open(lock, "w"), indent=1)
            print(f"  HOST {host} held by live pid {pid}; queued and exiting "
                  f"(pull discipline rule 1).")
            return False
    json.dump({"host": host, "pid": os.getpid(), "script": script,
               "started": datetime.now().isoformat(), "active": True,
               "queue": [], "note": note}, open(lock, "w"), indent=1)
    return True


def release_lock(host):
    lock = LOGS / f"_HOSTLOCK_{host}.json"
    if lock.exists():
        try:
            cur = json.load(open(lock))
            if cur.get("pid") == os.getpid():
                cur["active"] = False
                cur["released"] = datetime.now().isoformat()
                json.dump(cur, open(lock, "w"), indent=1)
        except Exception:
            pass


def curl(url, out_path=None, timeout=300):
    """(status, effective_url, body_bytes_or_None). Follows redirects."""
    cmd = ["curl", "-s", "-L", "-A", UA,
           "-H", "Accept: text/html,application/xhtml+xml,application/pdf,*/*;q=0.8",
           "--max-time", str(timeout),
           "-w", "%{http_code}\t%{url_effective}", url]
    if out_path:
        cmd[1:1] = ["-o", str(out_path)]
        p = subprocess.run(cmd, capture_output=True, text=True)
        tail = (p.stdout or "").strip().split("\t")
        status = int(tail[0]) if tail and tail[0].isdigit() else 0
        eff = tail[1] if len(tail) > 1 else ""
        return status, eff, None
    p = subprocess.run(cmd, capture_output=True)
    out = p.stdout
    m = re.search(rb"(\d{3})\t(\S*)$", out)
    if not m:
        return 0, "", out
    return int(m.group(1)), m.group(2).decode("utf-8", "replace"), out[:m.start()]


# =========================================================================
# STEP: ocr
# =========================================================================
# 160 of 327 letters are image-only scans - verified two ways (PyMuPDF and
# pdftotext -layout both return zero characters), so it is NIGC's scanning
# practice, not our extractor. They are concentrated in FY2015-FY2019, which is
# 140 letters of which 5 were readable. Every finding, party and property in the
# first build came from the other 167.
#
# NO OCR ENGINE WAS INSTALLED when the layer was first built, so the work was
# recorded as the highest-value next action rather than half-attempted.
# rapidocr-onnxruntime is a pip-installable ONNX engine needing no system
# binary; it is used here at 220 dpi.
#
# OCR TEXT IS MARKED AS OCR TEXT, FOREVER. The build log records that OCR ate a
# negation on the 2013 Shingle Springs letter and published VIOLATION_FOUND -
# the exact inverse of what the agency wrote. Recovered rows therefore carry
# text_layer_quality = ocr_recovered_rapidocr, findings carry
# finding_evidence_basis = OCR_RECOVERED, and EVERY affirmative finding
# recovered by OCR is staged for a human rather than published.

def step_ocr(shard=0, nshards=1):
    from rapidocr_onnxruntime import RapidOCR
    import fitz

    OCRDIR.mkdir(parents=True, exist_ok=True)
    letters = read_csv(CLEAN / "nigc_declination_letters.csv")
    todo = [r for r in letters
            if r.get("text_layer_quality") == "no_text_layer"
            and r.get("retrieval_status") == "retrieved"]
    todo = [r for i, r in enumerate(todo) if i % nshards == shard]
    print(f"OCR shard {shard}/{nshards}: {len(todo)} image-only letters",
          flush=True)

    eng = RapidOCR()
    t0 = time.time()
    for i, r in enumerate(todo, 1):
        oid = r["cedar_opinion_id"]
        out = OCRDIR / f"{oid}.json"
        if out.exists():
            continue
        pdf = CEDAR / r["pdf_path"]
        if not pdf.exists():
            continue
        try:
            doc = fitz.open(pdf)
        except Exception as e:
            json.dump({"opinion_id": oid, "error": f"open_failed:{e}"},
                      open(out, "w"))
            continue
        pages = []
        for pg in doc:
            try:
                pix = pg.get_pixmap(dpi=220)
                res, _ = eng(pix.tobytes("png"))
                pages.append(" ".join(x[1] for x in res) if res else "")
            except Exception:
                pages.append("")
        doc.close()
        json.dump({"opinion_id": oid, "pdf_md5": r.get("pdf_md5", ""),
                   "engine": "rapidocr_onnxruntime", "dpi": 220,
                   "ocr_date": TODAY, "pages": pages},
                  open(out, "w", encoding="utf-8"))
        print(f"  [{i}/{len(todo)}] {oid} {len(pages)}pp "
              f"{sum(len(p) for p in pages)}ch  {time.time()-t0:.0f}s",
              flush=True)
    print("OCR cache:", len(list(OCRDIR.glob('*.json'))), "files")


# =========================================================================
# STEP: index  - has NIGC published letters since the last pull?
# =========================================================================
# THE DOWNLOAD TRAP, restated because it is the thing that silently succeeds:
# every nigc.gov/download/<slug>/ page carries a sidebar link with the same
# wpdmdl= value, so matching the FIRST wpdmdl= returns the identical PDF every
# time, same byte length, looking like success. Links are taken only from inside
# <table id="tablepress-2">, the two non-letter WPDM ids are refused by name,
# the 302 is resolved so the real FILENAME is known before anything is written,
# and the md5 is compared against every object already held. A distinct URL is
# not evidence of a distinct document; a distinct md5 is.

ROW_RX = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
CELL_RX = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.I)
TAG_RX = re.compile(r"<[^>]+>")
WPDM_RX = re.compile(r"wpdmdl=(\d+)")
DATE_RX = re.compile(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})")


def cell_text(c):
    return flat(htmllib.unescape(TAG_RX.sub(" ", c)))


def parse_index(html):
    m = re.search(r'<table[^>]*id="tablepress-2".*?</table>', html, re.S | re.I)
    if not m:
        return []
    rows = []
    for rr in ROW_RX.findall(m.group(0)):
        cells = CELL_RX.findall(rr)
        if len(cells) < 3:
            continue
        texts = [cell_text(c) for c in cells]
        hrefs = re.findall(r'href="([^"]+)"', " ".join(cells))
        wpdm = url = ""
        for h in hrefs:
            mm = WPDM_RX.search(htmllib.unescape(h))
            if mm and mm.group(1) not in NON_LETTER_WPDMDL:
                wpdm, url = mm.group(1), htmllib.unescape(h)
                break
        if not wpdm:
            continue
        rows.append({"cells": texts, "wpdmdl": wpdm, "url": url})
    return rows


def parse_date(s):
    m = DATE_RX.search(s or "")
    if not m:
        return ""
    mo, dy, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if yr < 100:
        yr += 2000
    try:
        return date(yr, mo, dy).isoformat()
    except ValueError:
        return ""


def step_index():
    host = "www.nigc.gov"
    if not claim_lock(host, "code/100_finish_declinations_and_employment.py",
                      "declination index refresh"):
        return
    try:
        IDX = RAW / "_index"
        IDX.mkdir(parents=True, exist_ok=True)
        status, eff, body = curl(INDEX_URL)
        print(f"  index HTTP {status}")
        if status != 200:
            print("  refusing to parse a non-200 body (AGENTS.md: check the "
                  "status, not the file)")
            return
        html = body.decode("utf-8", "replace")
        (IDX / f"declination_letters_index_{TODAY}.html").write_text(
            html, encoding="utf-8")
        rows = parse_index(html)
        print(f"  index rows in tablepress-2: {len(rows)}")

        held = read_csv(CLEAN / "nigc_declination_letters.csv")
        held_ids = set()
        for r in held:
            m = WPDM_RX.search(r.get("source_url", "") or "")
            if m:
                held_ids.add(m.group(1))
        held_md5 = {r.get("pdf_md5", "") for r in held}

        new = []
        for r in rows:
            if r["wpdmdl"] in held_ids:
                continue
            d = ""
            for c in r["cells"]:
                d = parse_date(c)
                if d:
                    break
            new.append({"wpdmdl": r["wpdmdl"], "url": r["url"],
                        "opinion_date": d, "cells": " | ".join(r["cells"])})
        print(f"  index rows NOT already held: {len(new)}")

        PDFDIR = RAW / "pdf"
        for n in new:
            tmp = PDFDIR / f"_tmp_{n['wpdmdl']}.pdf"
            st, eff, _ = curl(n["url"], out_path=tmp)
            fn = eff.rsplit("/", 1)[-1].split("?")[0] or f"{n['wpdmdl']}.pdf"
            if st != 200 or not tmp.exists():
                n["retrieval_status"] = f"not_retrieved_http_{st}"
                continue
            h = md5_of(tmp)
            n.update(resolved_filename=fn, pdf_md5=h)
            n["retrieval_status"] = ("retrieved" if h not in held_md5
                                     else "duplicate_md5_of_held_object")
            if h in held_md5:
                tmp.unlink(missing_ok=True)
            else:
                tmp.replace(PDFDIR / fn)
            time.sleep(2.0)

        write_csv(IDX / f"index_refresh_{TODAY}.csv", new,
                  ["wpdmdl", "url", "opinion_date", "cells",
                   "resolved_filename", "pdf_md5", "retrieval_status"])
        json.dump({"checked": TODAY, "index_rows": len(rows),
                   "held_letters": len(held), "new_rows": len(new)},
                  open(IDX / f"index_refresh_{TODAY}.json", "w"), indent=1)
    finally:
        release_lock(host)


# =========================================================================
# STEP: osha  - ITA 300A establishment summaries
# =========================================================================
# What OSHA ITA employment IS: an establishment's own annual average number of
# employees, reported on the OSHA Form 300A summary it submits electronically.
# It is a filing, at establishment level, by an employer meeting the electronic
# submission thresholds.
#
# What it IS NOT: a census of casinos. Coverage depends on the submission rule,
# on whether the operator files under the property's own name or the
# enterprise's, and on the tribe's posture toward OSHA jurisdiction over tribal
# enterprises - which is contested and varies by circuit. ABSENCE FROM ITA IS A
# PROPERTY OF ITA.

OSHA_FILES = [
    ("2016", "https://www.osha.gov/sites/default/files/ITA%20Data%20CY%202016.zip"),
    ("2017", "https://www.osha.gov/sites/default/files/ITA%20Data%20CY%202017.zip"),
    ("2018", "https://www.osha.gov/sites/default/files/ITA%20Data%20CY%202018.zip"),
    ("2019", "https://www.osha.gov/sites/default/files/ITA%20Data%20CY%202019.zip"),
    ("2020", "https://www.osha.gov/sites/default/files/ITA-Data-CY-2020.zip"),
    ("2021", "https://www.osha.gov/sites/default/files/ITA-data-cy2021.zip"),
    ("2022", "https://www.osha.gov/sites/default/files/ITA-data-cy2022.zip"),
    ("2023", "https://www.osha.gov/sites/default/files/ITA_300A_Summary_Data_2023_through_12-31-2024.zip"),
    ("2024", "https://www.osha.gov/sites/default/files/ITA_300A_Summary_Data_2024_through_12-31-2025.zip"),
    ("2025", "https://www.osha.gov/sites/default/files/ITA_300A_Summary_Data_2025_through_03-15-2026_v2.csv"),
]
OSHA_PAGE = "https://www.osha.gov/itadata"


def step_osha():
    host = "www.osha.gov"
    if not claim_lock(host, "code/100_finish_declinations_and_employment.py",
                      "OSHA ITA 300A establishment summaries CY2016-CY2025"):
        return
    try:
        OSHA.mkdir(parents=True, exist_ok=True)
        man = []
        for yr, url in OSHA_FILES:
            ext = ".csv" if url.endswith(".csv") else ".zip"
            dest = OSHA / f"ita_300a_{yr}{ext}"
            if dest.exists() and dest.stat().st_size > 1000:
                man.append({"year": yr, "url": url, "path": str(dest),
                            "status": "already_held",
                            "bytes": dest.stat().st_size,
                            "md5": md5_of(dest), "fetched_date": TODAY})
                continue
            st, eff, _ = curl(url, out_path=dest, timeout=900)
            ok = st == 200 and dest.exists() and dest.stat().st_size > 1000
            print(f"  {yr} HTTP {st} "
                  f"{dest.stat().st_size if dest.exists() else 0:,}B")
            man.append({"year": yr, "url": url, "path": str(dest),
                        "status": "retrieved" if ok else f"http_{st}",
                        "bytes": dest.stat().st_size if dest.exists() else 0,
                        "md5": md5_of(dest) if ok else "",
                        "fetched_date": TODAY})
            time.sleep(2.0)
        write_csv(OSHA / "_SOURCE_MANIFEST.csv", man,
                  ["year", "url", "path", "status", "bytes", "md5",
                   "fetched_date"])
    finally:
        release_lock(host)


def osha_gambling_rows():
    """Every ITA 300A row in a gambling or casino-hotel NAICS, all years."""
    cache = OSHA / "_gambling_naics_rows.csv"
    if cache.exists():
        return read_csv(cache)
    out = []
    for p in sorted(glob.glob(str(OSHA / "ita_300a_*"))):
        handles = []
        if p.endswith(".zip"):
            z = zipfile.ZipFile(p)
            for n in z.namelist():
                if n.lower().endswith(".csv"):
                    handles.append((os.path.basename(p) + "::" + n,
                                    io.BytesIO(z.read(n))))
        else:
            handles.append((os.path.basename(p), open(p, "rb")))
        for tag, fh in handles:
            txt = io.TextIOWrapper(fh, encoding="latin-1", newline="")
            for r in csv.DictReader(txt):
                nc = (r.get("naics_code") or "").strip()
                if nc.startswith("7132") or nc.startswith("721120"):
                    r["_file"] = tag
                    out.append(r)
    if out:
        write_csv(cache, out, list(out[0].keys()))
    return out


# =========================================================================
# STEP: geocode  - facility lat/lon -> 2020 census BLOCK
# =========================================================================
# LODES is published at BLOCK level and the spec is explicit that block, not
# tract, is the unit to use. A tract is large enough that "jobs in the tract"
# says almost nothing about a single employer; a block is tight enough to be
# informative and STILL is not casino payroll whenever another employer shares
# it. Both facts are carried on every LODES row produced below.

GEOCODER = ("https://geocoding.geo.census.gov/geocoder/geographies/coordinates"
            "?x={lon}&y={lat}&benchmark=Public_AR_Current"
            "&vintage=Census2020_Current&format=json&layers=10")


def step_geocode():
    host = "geocoding.geo.census.gov"
    if not claim_lock(host, "code/100_finish_declinations_and_employment.py",
                      "gaming facility lat/lon -> 2020 census block"):
        return
    try:
        LODESDIR.mkdir(parents=True, exist_ok=True)
        out_path = LODESDIR / "facility_blocks.csv"
        done = {r["facility_id"]: r for r in read_csv(out_path)}
        fac = read_csv(CLEAN / "gaming_facilities.csv")
        todo = [f for f in fac
                if f.get("latitude") and f.get("longitude")
                and f["facility_id"] not in done]
        print(f"  geocoding {len(todo)} facilities ({len(done)} already held)")
        for i, f in enumerate(todo, 1):
            url = GEOCODER.format(lon=f["longitude"], lat=f["latitude"])
            st, eff, body = curl(url, timeout=60)
            rec = {"facility_id": f["facility_id"], "latitude": f["latitude"],
                   "longitude": f["longitude"], "state": f.get("state", ""),
                   "coords_basis": f.get("coords_basis", ""),
                   "http_status": st, "block_geoid": "", "block_pop100": "",
                   "block_hu100": "", "source_url": url,
                   "fetched_date": TODAY}
            if st == 200 and body:
                try:
                    g = json.loads(body)["result"]["geographies"]["Census Blocks"]
                    if g:
                        rec["block_geoid"] = g[0]["GEOID"]
                        rec["block_pop100"] = g[0].get("POP100", "")
                        rec["block_hu100"] = g[0].get("HU100", "")
                except Exception:
                    pass
            done[f["facility_id"]] = rec
            if i % 25 == 0:
                print(f"    {i}/{len(todo)}", flush=True)
                write_csv(out_path, list(done.values()),
                          list(next(iter(done.values())).keys()))
            time.sleep(0.35)
        write_csv(out_path, list(done.values()),
                  list(next(iter(done.values())).keys()))
    finally:
        release_lock(host)


# =========================================================================
# STEP: lodes  - block workplace jobs
# =========================================================================
# LODES8 does not publish every state for every year. Alaska has never
# participated in LEHD at all, and MICHIGAN stops at 2021 - a 404 on
# mi_wac_S000_JT00_2022 while 2021, 2020 and 2019 all return 200. Michigan
# holds 39 Cedar properties, so treating one national vintage as universal
# would silently drop them. The pull walks back to the newest year each state
# actually publishes and records which year it used.
LODES_YEARS = ["2022", "2021", "2020"]
LODES_URL = ("https://lehd.ces.census.gov/data/lodes/LODES8/{st}/wac/"
             "{st}_wac_S000_JT00_{yr}.csv.gz")


def step_lodes():
    host = "lehd.ces.census.gov"
    if not claim_lock(host, "code/100_finish_declinations_and_employment.py",
                      "LODES8 WAC block workplace jobs"):
        return
    try:
        LODESDIR.mkdir(parents=True, exist_ok=True)
        blocks = read_csv(LODESDIR / "facility_blocks.csv")
        want = defaultdict(set)
        for b in blocks:
            g = b.get("block_geoid") or ""
            if len(g) == 15:
                want[b["state"].lower()].add(g)
        print(f"  {sum(len(v) for v in want.values())} blocks across "
              f"{len(want)} states")
        rows, man = [], []
        for st in sorted(want):
            for yr in LODES_YEARS:   # newest first; stop at the first that exists
                url = LODES_URL.format(st=st, yr=yr)
                dest = LODESDIR / f"{st}_wac_S000_JT00_{yr}.csv.gz"
                if not dest.exists() or dest.stat().st_size < 1000:
                    code, eff, _ = curl(url, out_path=dest, timeout=900)
                    time.sleep(1.5)
                else:
                    code = 200
                # CHECK THE STATUS AND THE MAGIC BYTES, NOT THE FILE SIZE.
                # AGENTS.md: a 404 body still has content. LODES8 does not
                # publish Alaska at all, and its 404 page saved as a .gz is
                # 32 KB - large enough to pass any size test, and it fails only
                # when gzip tries to read it. Two independent checks, because
                # "the file has content" is not evidence of anything.
                magic = b""
                if dest.exists():
                    with open(dest, "rb") as fh:
                        magic = fh.read(2)
                ok = (code == 200 and dest.exists()
                      and dest.stat().st_size > 1000 and magic == b"\x1f\x8b")
                if not ok and dest.exists():
                    bad = dest.with_suffix(".gz.NOT_A_GZIP")
                    bad.unlink(missing_ok=True)
                    dest.rename(bad)
                man.append({"state": st, "year": yr, "url": url,
                            "http_status": code,
                            "gzip_magic_ok": magic == b"\x1f\x8b",
                            "bytes": dest.stat().st_size if dest.exists() else 0,
                            "md5": md5_of(dest) if ok else "",
                            "fetched_date": TODAY})
                print(f"    {st} {yr} HTTP {code} ok={ok}", flush=True)
                if not ok:
                    continue
                with gzip.open(dest, "rt", encoding="utf-8", newline="") as fh:
                    for r in csv.DictReader(fh):
                        if r["w_geocode"] in want[st]:
                            rows.append({"state": st, "year": yr,
                                         "w_geocode": r["w_geocode"],
                                         "C000": r["C000"],
                                         "CNS17": r.get("CNS17", ""),
                                         "CNS18": r.get("CNS18", ""),
                                         "source_url": url,
                                         "fetched_date": TODAY})
                break    # this state's newest published vintage; do not stack years
        write_csv(LODESDIR / "block_wac.csv", rows,
                  ["state", "year", "w_geocode", "C000", "CNS17", "CNS18",
                   "source_url", "fetched_date"])
        write_csv(LODESDIR / "_SOURCE_MANIFEST.csv", man,
                  ["state", "year", "url", "http_status", "gzip_magic_ok",
                   "bytes", "md5", "fetched_date"])
    finally:
        release_lock(host)


# =========================================================================
# BUILD
# =========================================================================
def load_m91():
    """Script 91 holds the readers this layer was built with. Reuse them; a
    second extractor would be a second definition of what a finding is."""
    spec = importlib.util.spec_from_file_location(
        "cedar91", CEDAR / "code" / "91_build_nigc_declinations.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["cedar91"] = m
    spec.loader.exec_module(m)
    return m


def load_domain():
    spec = importlib.util.spec_from_file_location(
        "cedar_domain", CEDAR / "code" / "cedar_domain.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["cedar_domain"] = m
    spec.loader.exec_module(m)
    return m


def backup(path):
    """Snapshot once, then RESTORE FROM THE SNAPSHOT on every later run.

    This build adds columns and rows to files it does not own the history of.
    Re-running it against its own output would layer a second pass on top of a
    first - re_line cut twice, events appended to events. Restoring from the
    pre-100 snapshot makes the step deterministic: the same inputs always
    produce the same file, and the snapshot is the only thing that has to be
    protected.
    """
    path = Path(path)
    b = path.with_name(path.name + f".bak_{TODAY}_pre100")
    if b.exists():
        path.write_bytes(b.read_bytes())
        print(f"  restored {path.name} from the pre-100 snapshot")
    elif path.exists():
        b.write_bytes(path.read_bytes())


# ---------------------------------------------------------------- 1. verify
def verify_declinations():
    print("\n=== 1. VERIFY the declination layer as held ===")
    letters = read_csv(CLEAN / "nigc_declination_letters.csv")
    claims = read_csv(CLEAN / "gaming_source_claims.csv")
    events = read_csv(CLEAN / "gaming_financing_events.csv")
    checks = []

    def chk(name, ok, detail):
        checks.append({"check": name, "result": "PASS" if ok else "FAIL",
                       "detail": detail})
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")

    chk("letters_row_count", len(letters) == 327, f"{len(letters)} rows")
    ids = [r["cedar_opinion_id"] for r in letters]
    chk("letter_ids_unique", len(set(ids)) == len(ids),
        f"{len(set(ids))} distinct of {len(ids)}")

    # md5 re-verified on disk, not trusted from the file.
    ok = bad = missing = 0
    for r in letters:
        if r.get("retrieval_status") != "retrieved":
            continue
        p = CEDAR / r["pdf_path"]
        if not p.exists():
            missing += 1
        elif md5_of(p) == r["pdf_md5"]:
            ok += 1
        else:
            bad += 1
    chk("pdf_md5_reverified", bad == 0 and missing == 0,
        f"{ok} objects match their recorded md5, {bad} differ, {missing} absent")

    md5s = [r["pdf_md5"] for r in letters if r.get("pdf_md5")]
    dupes = len(md5s) - len(set(md5s))
    chk("md5_collisions_are_disclosed", dupes <= 1,
        f"{dupes} duplicated md5 - the disclosed Yavapai-Apache / Tunica "
        f"Biloxi case, retained with retrieval_status recording it")

    chk("claims_row_count", len(claims) == 113, f"{len(claims)} rows")
    blank_txt = sum(1 for c in claims if not (c.get("supporting_text") or "").strip())
    chk("every_claim_has_verbatim_text", blank_txt == 0,
        f"{blank_txt} claims with empty supporting_text")
    blank_url = sum(1 for c in claims if not (c.get("source_url") or "").strip())
    chk("every_claim_has_source_url", blank_url == 0,
        f"{blank_url} claims with empty source_url")
    orphan = sum(1 for c in claims if c.get("source_record_id") not in set(ids))
    chk("claims_link_to_a_held_letter", orphan == 0, f"{orphan} orphans")

    chk("events_row_count", len(events) == 145, f"{len(events)} rows")
    orphan_e = sum(1 for e in events if e.get("cedar_opinion_id") not in set(ids))
    chk("events_link_to_a_held_letter", orphan_e == 0, f"{orphan_e} orphans")
    amt = sum(1 for e in events if (e.get("principal_amount_usd") or "").strip())
    chk("no_dollar_amounts_published", amt == 0,
        f"{amt} events carry a principal amount (loan amounts live in the "
        f"unexecuted drafts, not the opinion letter)")
    exs = {e.get("execution_status") for e in events}
    chk("execution_status_never_claims_execution",
        exs <= {"UNEXECUTED_DRAFTS_REVIEWED"}, f"values: {sorted(exs)}")

    # revenue: this layer must contain none, at any level.
    rev = [c for r in (letters + events + claims) for c in r
           if re.search(r"revenue|ggr|net win", c, re.I)]
    chk("no_revenue_column_anywhere", not rev,
        f"{len(set(rev))} revenue-named columns")

    idxj = RAW / "_index" / f"index_refresh_{TODAY}.json"
    if idxj.exists():
        d = json.load(open(idxj))
        chk("index_refreshed_today",
            d["index_rows"] == 327 and d["new_rows"] == 0,
            f"NIGC index still publishes {d['index_rows']} rows; "
            f"{d['new_rows']} not already held")

    write_csv(REVIEW / f"declination_verification_{TODAY}.csv", checks,
              ["check", "result", "detail"])
    return letters, claims, events


# ------------------------------------------------------- 2. OCR recovery
def apply_ocr(letters, events):
    print("\n=== 2. OCR RECOVERY of the image-only letters ===")
    m91 = load_m91()
    cache = sorted(OCRDIR.glob("*.json"))
    print(f"  OCR cache: {len(cache)} letters")
    if not cache:
        return letters, events, [], []

    by_id = {r["cedar_opinion_id"]: r for r in letters}
    recovered = affirm = 0
    ocr_claims, new_events = [], []
    ev_ids = {e["financing_event_id"] for e in events}

    for p in cache:
        d = json.load(open(p, encoding="utf-8"))
        oid = d.get("opinion_id")
        r = by_id.get(oid)
        if not r or "pages" not in d:
            continue
        pages = m91.strip_running_matter(d["pages"])
        text = "\n".join(pages)
        if len(text.strip()) < 200:
            r["text_recovery_status"] = "ocr_returned_too_little_text"
            continue

        concs = m91.conclusion_sentences(text)
        mc, mcq = m91.read_finding(concs, m91.RE_MC_ANY, m91.RE_MC_NEG,
                                   m91.RE_MC_POS)
        ap, apq = m91.read_finding(concs, m91.RE_APPROVAL_ANY,
                                   m91.RE_APPROVAL_NEG, m91.RE_APPROVAL_POS)
        sp, spq = m91.read_finding(concs, m91.RE_SPI_ANY, m91.RE_SPI_NEG,
                                   m91.RE_SPI_POS)

        r["text_layer_quality"] = "ocr_recovered_rapidocr"
        r["text_recovery_status"] = "ocr_recovered"
        r["ocr_engine"] = "rapidocr_onnxruntime"
        r["ocr_dpi"] = d.get("dpi", "")
        r["ocr_date"] = d.get("ocr_date", TODAY)
        r["ocr_text_chars"] = len(text)
        r["ocr_common_word_ratio"] = m91.common_word_ratio(text)
        r["n_conclusion_sentences"] = len(concs)
        r["finding_evidence_basis"] = "OCR_RECOVERED"
        r["ocr_caution"] = (
            "Findings on this row are read from OCR text, not from a publisher "
            "text layer. OCR has been measured on this archive to eat negations "
            "('noi:' for 'not'), and an eaten negation INVERTS the finding. The "
            "negation tests are OCR-tolerant and every affirmative finding is "
            "staged for a human, but a quote from this row should be checked "
            "against the PDF before it is published as the agency's words.")

        if mc == "NO":
            r["is_management_contract"] = "NO_NOT_A_MANAGEMENT_CONTRACT"
        elif mc == "YES":
            r["is_management_contract"] = "YES_IS_A_MANAGEMENT_CONTRACT_HELD_FOR_REVIEW"
            affirm += 1
        elif mc:
            r["is_management_contract"] = "STATED_BUT_DIRECTION_NOT_PARSED"
        else:
            r["is_management_contract"] = "NOT_STATED_IN_OCR_TEXT"
        r["finding_quote"] = mcq

        r["chair_approval_required"] = (
            "NO" if ap == "NO" else
            "YES_HELD_FOR_REVIEW" if ap == "YES" else
            "STATED_BUT_DIRECTION_NOT_PARSED" if ap else "NOT_STATED_IN_OCR_TEXT")
        r["chair_approval_quote"] = apq

        if sp == "NO":
            r["sole_proprietary_interest_analysis"] = "NO_VIOLATION_FOUND"
        elif sp == "YES":
            r["sole_proprietary_interest_analysis"] = "VIOLATION_FOUND_HELD_FOR_REVIEW"
            affirm += 1
        elif sp:
            r["sole_proprietary_interest_analysis"] = "ADDRESSED_BUT_NOT_IN_A_CONCLUSION_SENTENCE"
        else:
            r["sole_proprietary_interest_analysis"] = "NOT_ADDRESSED_IN_OCR_TEXT"
        r["sole_proprietary_interest_quote"] = spq

        r["finding_is_conditional"] = "1" if (
            mcq and m91.RE_CONDITIONAL.search(mcq)) else "0"
        r["material_change_quote"] = m91.first(m91.RE_MATERIAL, text)
        r["material_change_warning"] = "1" if r["material_change_quote"] else "0"
        r["scope_limitation_quote"] = m91.first(m91.RE_SCOPE_LIMIT, text)
        r["documents_unexecuted_quote"] = m91.first(m91.RE_UNEXECUTED, text)

        # OCR output has no line breaks, so a "Re:" capture that runs to the
        # end of the line swallows the salutation and the whole opening
        # paragraph. It is cut at the salutation, and hard-capped.
        mre = re.search(r"\bRe:\s*([^\n]{5,300})", "\n".join(d["pages"]))
        if mre and not (r.get("re_line") or "").strip():
            rl = flat(mre.group(1))
            rl = re.split(r"\bDear\b|\bThis letter responds\b", rl)[0].strip()
            r["re_line"] = rl[:200].strip(" .,:;-")

        types = [name for name, rx in m91.AGREEMENT_TYPES
                 if re.search(rx, text, re.I)]
        r["agreement_type"] = "; ".join(types)
        r["agreement_type_basis"] = "ocr_recovered_text"
        ma = m91.RE_AMEND_NUM.search(text) or m91.RE_AMEND_ORD.search(text)
        if ma:
            g = ma.group(1).lower()
            r["amendment_number"] = str(m91.ORD.get(g, g))
            r["amendment_quote"] = flat(ma.group(0))
        r["prior_financing_reference"] = m91.first(m91.RE_PRIOR, text)
        rels = [k for k, rx in (("REFINANCES", m91.RE_REFI),
                                ("RESTATES", m91.RE_RESTATE),
                                ("EXTENDS", m91.RE_EXTEND),
                                ("SUPERSEDES", m91.RE_SUPERSEDE))
                if rx.search(text)]
        r["lineage_relations_in_text"] = "; ".join(rels)
        recovered += 1

        # --- financing events, which the 160 image-only letters produced none of
        if any(t in types for t in ("loan_or_credit_agreement",
                                    "note_indenture_or_bond",
                                    "security_or_collateral_agreement")):
            eid = f"NIGCDL-FIN-{oid}"
            if eid not in ev_ids:
                ev = {"financing_event_id": eid, "cedar_opinion_id": oid,
                      "opinion_date": r["opinion_date"],
                      "tribe_entity_id": r.get("tribe_entity_id", ""),
                      "tribe_canonical_name": r.get("tribe_canonical_name", ""),
                      "index_tribe_string": r.get("index_tribe_string", ""),
                      "index_company_string": r.get("index_company_string", ""),
                      "re_line": r.get("re_line", ""),
                      "agreement_type": r["agreement_type"],
                      "amendment_number": r.get("amendment_number", ""),
                      "amendment_quote": r.get("amendment_quote", ""),
                      "prior_financing_reference": r.get("prior_financing_reference", ""),
                      "lineage_relations_in_text": r["lineage_relations_in_text"],
                      "principal_amount_usd": "",
                      "principal_amount_basis":
                          "NOT PUBLISHED. Loan amounts live in the reviewed "
                          "drafts, not reliably in the opinion letter, and the "
                          "drafts are unexecuted.",
                      "execution_status": "UNEXECUTED_DRAFTS_REVIEWED",
                      "execution_status_basis":
                          r.get("documents_unexecuted_quote") or
                          "NIGC index page: 'Documents should be submitted "
                          "prior to their execution (unsigned) as the General "
                          "Counsel will not provide a declination letter for "
                          "executed documents.'",
                      "source_url": r.get("source_url", ""),
                      "pdf_path": r.get("pdf_path", ""),
                      "fetched_date": r.get("fetched_date", ""),
                      "built_date": TODAY,
                      "text_basis": "OCR_RECOVERED"}
                new_events.append(ev)
                ev_ids.add(eid)

        # --- party claims, held for review rather than published
        # A claim asserts a legal relationship between two named persons. From
        # OCR text the NAMES are the fragile part, so these are staged, not
        # merged: precision over recall, and a garbled party name is exactly
        # the kind of false attribution this project has already paid for.
        for rx, pred in ((m91.RE_WHOLLY_BY, "wholly_owned_by"),
                         (m91.RE_WHOLLY_ARM, "wholly_owned_by"),
                         (m91.RE_INSTRUMENTALITY, "instrumentality_of"),
                         (m91.RE_SUBSIDIARY, "subsidiary_of")):
            for mm in rx.finditer(text):
                gs = [g for g in mm.groups() if g]
                if len(gs) < 2:
                    continue
                subj, obj = m91.tidy_party(gs[0]), m91.tidy_party(gs[-1])
                if not subj or not obj or len(subj) < 4 or len(obj) < 4:
                    continue
                ocr_claims.append({
                    "candidate_claim_id": f"OCRCLM-{len(ocr_claims)+1:05d}",
                    "source_record_id": oid, "opinion_date": r["opinion_date"],
                    "subject_value": subj, "predicate": pred,
                    "object_value": obj,
                    "supporting_text": flat(mm.group(0)),
                    "source_url": r.get("source_url", ""),
                    "text_basis": "OCR_RECOVERED",
                    "why_held":
                        "Party names read from OCR text. A garbled name is a "
                        "false attribution, so this is staged for a ruling and "
                        "is NOT written into gaming_source_claims.csv.",
                    "YOUR_RULING": "", "built_date": TODAY})

    print(f"  letters recovered from OCR: {recovered}")
    print(f"  affirmative findings held for review: {affirm}")
    print(f"  new financing events from recovered letters: {len(new_events)}")
    print(f"  candidate party claims staged: {len(ocr_claims)}")
    return letters, events + new_events, ocr_claims, new_events


# ------------------------------------------------- 3. the evidentiary ladder
def apply_ladder(letters, events, claims):
    """The ladder is a COLUMN, not a note in a document nobody reads on a join."""
    print("\n=== 3. EVIDENTIARY LADDER ===")
    for r in letters:
        r["evidentiary_stage"] = "NIGC_REVIEWED"
        r["evidentiary_ladder"] = EVIDENTIARY_LADDER
        r["evidentiary_stage_basis"] = (
            "NIGC OGC reviewed submitted, unexecuted documents and issued a "
            "written legal opinion. NIGC's own index: 'Documents should be "
            "submitted prior to their execution (unsigned) as the General "
            "Counsel will not provide a declination letter for executed "
            "documents.'")
        r["what_this_does_not_establish"] = (
            "Execution, closing, construction, opening, continued operation, "
            "land status, or gaming eligibility. None of these is in evidence "
            "here and none may be inferred from the letter.")
        r["what_would_advance_the_stage"] = (
            "EXECUTED_CONFIRMED needs an executed instrument or a filing that "
            "recites one (SEC, EMMA, UCC, county recorder). CLOSED_CONFIRMED "
            "needs a funding or closing record. SUPERSEDED/TERMINATED needs a "
            "later instrument naming this one.")
    stages = defaultdict(int)
    for e in events:
        e["evidentiary_stage"] = "EXECUTION_UNCONFIRMED"
        e["evidentiary_ladder"] = EVIDENTIARY_LADDER
        e["evidentiary_stage_basis"] = (
            "A financing event here is a financing whose DRAFTS NIGC reviewed. "
            "The event is evidenced; its execution is not.")
        e["property_attachment_caution"] = (
            "Never attach this financing to a property because the enterprise "
            "owns that property. Financings routinely cover several properties, "
            "the whole enterprise, unrestricted assets, or a future project. "
            "The letter-to-property relation is many-to-many and a matched "
            "property means only that the property was NAMED.")
        stages[e["evidentiary_stage"]] += 1
    for c in claims:
        c["evidentiary_stage"] = "NIGC_REVIEWED"
        c["evidentiary_ladder"] = EVIDENTIARY_LADDER
        c["claim_scope_caution"] = (
            "This claim states what the letter says about a named legal person. "
            "Tribe, gaming authority, gaming enterprise, property-owning "
            "subsidiary and operating company are five different persons and "
            "are not interchangeable.")
    print(f"  letters -> NIGC_REVIEWED: {len(letters)}")
    print(f"  events  -> EXECUTION_UNCONFIRMED: {len(events)}")
    print(f"  claims  -> NIGC_REVIEWED: {len(claims)}")
    return letters, events, claims


# ------------------------------------------- 4. against the deals ledger
# The six rulings, and what each requires:
#
#   CONFIRMED_BY_NIGC_DOCUMENT              a federal document establishes the
#                                           deal ledger's claim as written
#   PARTIALLY_CONFIRMED                     parties/instrument/timing confirmed,
#                                           the ledger's further claims are not
#   CONSISTENT_BUT_EXECUTION_UNCONFIRMED    nothing conflicts, and the letter
#                                           cannot speak to execution
#   CONTRADICTED                            the letter's legal conclusion is
#                                           incompatible with the ledger's
#                                           characterisation of the SAME
#                                           arrangement
#   NOT_ESTABLISHED                         the archive cannot speak to it
#   POSSIBLE_SAME_TRANSACTION               a candidate pair, unruled
#
# THE ASYMMETRY THAT MAKES CONTRADICTED RARE AND VALUABLE
# --------------------------------------------------------
# A document that IS a management contract goes to the NIGC CHAIR for approval
# under 25 U.S.C. 2711. A document a tribe hopes is NOT one goes to OGC for a
# declination. So this archive is, by construction, the set of arrangements the
# agency found were NOT management contracts. It can therefore never confirm a
# management contract, and it CAN contradict a press characterisation that
# calls a counterparty the casino's manager - which is the one direction in
# which a federal legal opinion fact-checks our own ledger.

# Words that are not evidence of anything when two documents share them.
# "certain" appearing in both an OCR'd letter and a deal description is not a
# project match, and it produced a false CONTRADICTED before this list existed.
COMMON_ENGLISH = set("""certain collectively pursuant thereto herein whether
respect approval require required requires including between among various
several submitted request response opinion counsel general national commission
indian regulatory chairman chairwoman chair transaction transactions documents
document agreement agreements amended restated dated effective million billion
company companies limited liability partnership association proprietary
interest management contract contracts letter review reviewed provided related
under above below other others their there these those which while would could
should""".split())

BANK_GENERIC = set("""bank banking national association na n.a nationalassociation
trust company co inc llc lp llp the of and & first second third fourth financial
capital markets group holdings holding corp corporation securities
partners fund funds lenders lender syndicate""".split())

# A WIND-DOWN IS NOT A CONTRADICTION, AND THIS IS THE TRAP THAT LOOKS MOST LIKE ONE
# ---------------------------------------------------------------------------------
# ND-2013-003 records Shingle Springs paying $57.1M to extinguish Lakes
# Entertainment debt and END the Red Hawk Casino management agreement.
# NIGC-DL-20130801-01 finds the Tribe's AMENDED agreement with Lakes
# KAR-Shingle Springs is not a management contract. Same parties, four weeks
# apart, and it reads as a flat contradiction. It is not one: a tribe can have
# had a Chair-approved management contract AND a later amended or terminating
# instrument that is not one - that is the ordinary way such a relationship
# winds down, and the deal row says so in its own words ("approved by the
# National Indian Gaming Commission on July 19, 2004 - were terminated").
# Publishing that as CONTRADICTED would be a false and very quotable claim.
WIND_DOWN = re.compile(
    r"\bterminat|\bextinguish|\bbuys? out\b|\bbuy-?out\b|\bends? the\b|"
    r"\bapproved by the National Indian Gaming Commission\b|"
    r"\btook full (?:ownership|control)\b|\brevert", re.I)

# A LENDER IS NEVER THE ALLEGED CASINO MANAGER, AND CONFUSING THEM MANUFACTURES
# A CONTRADICTION
# -----------------------------------------------------------------------------
# ND-2016-003 records Jamul's $460M credit facilities and, in the same row,
# describes Penn National's development, management and branding role. The NIGC
# letter for the same month is about the 2016 Transaction Documents and its
# counterparty is CITIZENS BANK. Token overlap on "citizens" plus manager
# language anywhere in the row produced a CONTRADICTED - against a bank, about a
# role a different company was said to hold. Two guards follow: the matched
# counterparty may not be a lender, and the manager language must sit NEAR the
# matched company's name in the ledger text rather than merely in the same row.
LENDER_RX = re.compile(
    r"\bbank\b|bancorp|bokf|wells fargo|citizens|keybank|key bank|\bpnc\b|"
    r"u\.?s\.? bank|arvest|capital one|western alliance|umpqua|\bbmo\b|"
    r"jpmorgan|goldman|credit union|financial|securities|santander|"
    r"credit suisse|\blender\b|capital markets|\bd\.a\. davidson\b|"
    r"note purchasers|bookrunner|arrangers?\b", re.I)

MANAGER_LANGUAGE = re.compile(
    r"\bcasino manager\b|\bmanages the casino\b|\bmanaged by\b|"
    r"\bmanagement (?:contract|agreement)\b|\bas manager\b|\bthe manager\b|"
    r"\bmanage,? operate\b|\bright and obligation to manage\b|"
    r"\bdevelopment and management agreement\b|\bmanagement fees?\b|"
    r"\boperator of the casino\b|\bmanagement and branding\b", re.I)
FINANCING_LANGUAGE = re.compile(
    r"\bcredit facilit|\bterm loan\b|\brevolv|\bsenior notes\b|\brefinanc|"
    r"\bnote (?:purchase|offering|issuance)\b|\bfinancing\b|\bbond", re.I)


def sig_tokens(s):
    t = re.findall(r"[a-z0-9]+", (s or "").lower())
    return {x for x in t if x not in BANK_GENERIC and len(x) > 2}


GOV_CLASSES = {"Federally recognized tribe",
               "Federally recognized Alaska Native Village",
               "State-recognized tribe",
               "Federal-level constituency entity",
               "State-level constituency entity"}


def deal_party_resolver(m91):
    """Resolve a deals-ledger Native_Party to a spine tribe id.

    Route 1 is the attribution the deals build ALREADY made and ruled
    (`deals_party_attribution.csv`, `deals_party_autoresolved.csv`). Re-deriving
    it here would be a second name matcher, which AGENTS.md forbids.

    Route 2 is `resolve_entity` with the TRIBE guard from the declination build:
    containment is accepted only toward a government-class spine row whose name
    tokens are a SUBSET of the record's. Ungoverned containment is what resolved
    `N/A` onto Native American Bank.
    """
    ruled = {}
    for p in ("deals_party_attribution.csv", "deals_party_autoresolved.csv"):
        for r in read_csv(CLEAN / p):
            if r.get("native_party") and r.get("tribe_id"):
                ruled.setdefault(m91.norm(r["native_party"]),
                                 (r["tribe_id"], r.get("canonical_name", ""),
                                  "deals_ledger_ruling"))
    spine = read_csv(CEDAR / "data" / "spine" / "cedar_entity_spine.csv")
    by_id = {r["tribe_id"]: r for r in spine}
    cache = {}

    def resolve(name):
        name = (name or "").strip()
        if not name:
            return "", "", "empty"
        if name in cache:
            return cache[name]
        hit = ruled.get(m91.norm(name))
        if hit:
            cache[name] = hit
            return hit
        # The deals ledger writes "Tribe / Enterprise"; try the tribe side too.
        parts = [name] + [p.strip() for p in re.split(r"\s*/\s*", name) if p.strip()]
        for cand in parts:
            hit = ruled.get(m91.norm(cand))
            if hit:
                cache[name] = hit
                return hit
        for cand in parts:
            tid, cname, how = m91.resolve_entity(cand, spine)
            if not tid:
                continue
            if how == "containment":
                row = by_id.get(tid, {})
                if row.get("entity_class") not in GOV_CLASSES:
                    continue
                if not m91.core(cname).issubset(m91.core(cand)):
                    continue
            cache[name] = (tid, cname, how)
            return cache[name]
        cache[name] = ("", "", "unresolved")
        return cache[name]

    return resolve


def build_contradictions(letters):
    print("\n=== 4. AGAINST THE DEALS LEDGER ===")
    m91 = load_m91()
    resolve_deal_party = deal_party_resolver(m91)
    deals = []
    # THE TRUTH: data/clean/deals_classified.csv (cedar_domain.DEALS_TRUTH).
    # Assembled the parts by hand until 2026-08-26; the parts do not honour
    # `review/deals_withdrawn_duplicates.csv`, so a contradiction could be
    # raised against MA2020-008, a row that was withdrawn as a duplicate.
    # See `cedar_domain.PROMOTED_TABLES`.
    for p in [str(CEDAR / DOM.DEALS_TRUTH)]:
        for r in read_csv(p):
            if r.get("Deal_ID"):
                r["_src"] = os.path.basename(p)
                deals.append(r)
    print(f"  deal rows read: {len(deals)}")

    def dtext(d):
        return " ".join(str(d.get(k) or "") for k in
                        ("Deal_Title", "Description", "Notes", "Industry",
                         "Deal_Category", "Counterparty_or_Funder"))

    gaming = [d for d in deals
              if re.search(r"casino|gaming|gambl|bingo", dtext(d), re.I)]
    print(f"  gaming-related deal rows: {len(gaming)}")

    # tribe side: the ONE resolver, with the containment guard the build log
    # records - a containment hit is accepted only toward a government-class
    # spine row whose tokens are a SUBSET of the record's.
    letters_by_tribe = defaultdict(list)
    for r in letters:
        if r.get("tribe_entity_id"):
            letters_by_tribe[r["tribe_entity_id"]].append(r)

    out = []
    for d in gaming:
        eid, _cn, _how = resolve_deal_party(d.get("Native_Party", ""))
        cands = letters_by_tribe.get(eid, [])
        dt = dtext(d)
        deal_says_manager = bool(MANAGER_LANGUAGE.search(dt))
        deal_is_financing = bool(FINANCING_LANGUAGE.search(dt))
        ddate = (d.get("Event_Date") or "")[:10]

        if not cands:
            out.append({
                "pair_id": f"DLC-{len(out)+1:04d}", "deal_id": d["Deal_ID"],
                "deal_source_file": d["_src"], "deal_date": ddate,
                "deal_native_party": d.get("Native_Party", ""),
                "deal_counterparty": d.get("Counterparty_or_Funder", ""),
                "deal_title": d.get("Deal_Title", ""),
                "deal_characterises_counterparty_as_manager":
                    "1" if deal_says_manager else "0",
                "cedar_opinion_id": "", "opinion_date": "",
                "letter_tribe_string": "", "letter_company_string": "",
                "letter_re_line": "", "letter_finding": "",
                "letter_finding_quote": "",
                "counterparty_token_overlap": "", "project_token_overlap": "",
                "days_between": "", "ruling": "NOT_ESTABLISHED",
                "ruling_basis":
                    "No declination letter in the archive resolves to this "
                    "deal's Native party. OGC review is voluntary and its "
                    "archive is not a gaming census, so this is a property of "
                    "the archive and NOT evidence that no such document exists.",
                "contradiction_candidate": "0",
                "what_would_settle_it":
                    "A letter for this tribe naming this counterparty, or an "
                    "executed instrument from SEC/EMMA/UCC.",
                "built_date": TODAY})
            continue

        for L in cands:
            # Overlap is computed on the COUNTERPARTY strings only, and the
            # tribe's own name tokens are removed from both sides. An earlier
            # version included the letter's Re: line, which carries the tribe
            # name, and "Shingle Springs" then matched "Shingle Springs" - a
            # counterparty match manufactured out of the tribe's name.
            tribe_toks = (sig_tokens(L.get("index_tribe_string", ""))
                          | sig_tokens(d.get("Native_Party", "")))
            ov = ((sig_tokens(d.get("Counterparty_or_Funder", ""))
                   & sig_tokens(L.get("index_company_string", "")))
                  - tribe_toks)
            days = ""
            if ddate and L.get("opinion_date"):
                try:
                    days = (date.fromisoformat(ddate)
                            - date.fromisoformat(L["opinion_date"])).days
                except Exception:
                    days = ""
            # A financing letter often names the PROJECT rather than the
            # lender - "Review of Financing Agreements for New Casino Resort in
            # Beloit Wisconsin" against a ledger row reading "Ho-Chunk Nation
            # closes $610M financing for Beloit casino resort". The lender
            # strings agree on nothing ("Lender" vs "KeyBanc"), but the place
            # does, and the place is the more specific token of the two. Only
            # tokens the tribe's name does not already supply are used.
            GENERIC_PROJ = {"review", "casino", "resort", "gaming", "loan",
                            "documents", "document", "financing", "agreement",
                            "agreements", "credit", "tribe", "tribal", "band",
                            "nation", "indians", "indian", "new", "for", "the",
                            "and", "of", "revised", "updated"}
            proj = ((sig_tokens(L.get("re_line", "")) - tribe_toks
                     - GENERIC_PROJ)
                    & (sig_tokens(d.get("Deal_Title", "") + " "
                                  + (d.get("Description") or "")) - tribe_toks))
            proj = {t for t in proj if len(t) > 4 and t not in COMMON_ENGLISH}
            finding = L.get("is_management_contract", "")
            # A shared PROJECT word is evidence the two records concern the same
            # deal. It is NOT evidence about who the parties are, so it may
            # support PARTIALLY_CONFIRMED and must never support CONTRADICTED -
            # a contradiction is a claim about a named company's legal role and
            # has to be established on the party names themselves.
            same_party = bool(ov)
            same_project = bool(ov) or bool(proj)
            near = isinstance(days, int) and -400 <= days <= 400

            # Is the ledger's manager language ABOUT the company the overlap
            # matched? Require it within 250 characters of an occurrence of one
            # of the overlapping tokens, and require that company not to be a
            # lender.
            manager_about_this_party = False
            if deal_says_manager and ov and not LENDER_RX.search(
                    L.get("index_company_string", "")):
                low = dt.lower()
                for t in ov:
                    for mt in re.finditer(re.escape(t), low):
                        w = low[max(0, mt.start() - 250): mt.end() + 250]
                        if MANAGER_LANGUAGE.search(w):
                            manager_about_this_party = True
                            break
                    if manager_about_this_party:
                        break

            if manager_about_this_party and finding.startswith("NO_NOT"):
                if WIND_DOWN.search(dt):
                    ruling = "CONSISTENT_BUT_EXECUTION_UNCONFIRMED"
                    basis = (
                        "READS AS A CONTRADICTION AND IS NOT ONE. The ledger "
                        "row describes a management relationship being wound "
                        "down - terminated, bought out or extinguished - and "
                        "the letter opines on the amending or terminating "
                        "instrument. A tribe can have had a Chair-approved "
                        "management contract AND a later amended agreement "
                        "that is not one; that is the ordinary shape of a "
                        "wind-down. Publishing this as CONTRADICTED would be a "
                        "false and very quotable claim, so it is left for a "
                        "human with contradiction_candidate = 1.")
                    cand = "1"
                else:
                    ruling = ("CONTRADICTED" if near
                              else "POSSIBLE_SAME_TRANSACTION")
                    basis = (
                        "The deals ledger characterises this counterparty as "
                        "managing or holding a management agreement over the "
                        "tribe's gaming operation; the NIGC Office of General "
                        "Counsel reviewed documents between these same parties "
                        "and concluded they do NOT constitute a management "
                        "contract requiring the Chair's approval. If both "
                        "describe the same arrangement the ledger's "
                        "characterisation is wrong in federal law."
                        + ("" if near else " Dates are more than 400 days "
                           "apart, so the SAME-ARRANGEMENT test is not met and "
                           "this stays a candidate rather than a ruling."))
                    cand = "1"
            elif same_project and deal_is_financing and near:
                ruling = "PARTIALLY_CONFIRMED"
                basis = (
                    "A federal legal opinion independently establishes that "
                    "these parties negotiated this financing and that NIGC "
                    "reviewed its documents in this window. It does NOT "
                    "establish that the financing closed on the ledger's date "
                    "or terms - the reviewed documents were unexecuted by rule.")
                cand = "0"
            elif same_project:
                ruling = "CONSISTENT_BUT_EXECUTION_UNCONFIRMED"
                basis = (
                    "Same parties, nothing in conflict, and the letter cannot "
                    "speak to execution because NIGC will not review executed "
                    "documents.")
                cand = "0"
            elif near:
                ruling = "POSSIBLE_SAME_TRANSACTION"
                basis = ("Same tribe and a compatible date, but no counterparty "
                         "token in common. Name overlap and date proximity "
                         "alone cannot establish that two records describe one "
                         "transaction.")
                cand = "0"
            else:
                continue

            out.append({
                "pair_id": f"DLC-{len(out)+1:04d}", "deal_id": d["Deal_ID"],
                "deal_source_file": d["_src"], "deal_date": ddate,
                "deal_native_party": d.get("Native_Party", ""),
                "deal_counterparty": d.get("Counterparty_or_Funder", ""),
                "deal_title": d.get("Deal_Title", ""),
                "deal_characterises_counterparty_as_manager":
                    "1" if deal_says_manager else "0",
                "cedar_opinion_id": L["cedar_opinion_id"],
                "opinion_date": L["opinion_date"],
                "letter_tribe_string": L.get("index_tribe_string", ""),
                "letter_company_string": L.get("index_company_string", ""),
                "letter_re_line": L.get("re_line", ""),
                "letter_finding": finding,
                "letter_finding_quote": L.get("finding_quote", ""),
                "counterparty_token_overlap": "; ".join(sorted(ov)),
                "project_token_overlap": "; ".join(sorted(proj)),
                "days_between": days, "ruling": ruling, "ruling_basis": basis,
                "contradiction_candidate": cand,
                "what_would_settle_it":
                    "Whether the ledger's arrangement and the letter's reviewed "
                    "documents are the SAME agreement. That needs the executed "
                    "instrument or the tribe's own statement.",
                "built_date": TODAY})

    for r in out:
        r["comparison_side"] = "DEALS_LEDGER"
        r["public_characterisation_to_check"] = ""

    # ------------------------------------------------------------------
    # THE CONTRADICTION-READY SURFACE
    # ------------------------------------------------------------------
    # The deals ledger's gaming rows are almost entirely FINANCE - credit
    # facilities, notes, refinancings - because that is where SEC and EMMA
    # filings are. It carries very few rows characterising a company as a
    # casino's manager or operator, which is why so few contradictions can be
    # found in it today. That is a coverage property of the ledger, not a limit
    # of the letters.
    #
    # Where the letters ARE decisive is the subset whose counterparty is an
    # OPERATOR-type company rather than a lender: a consultant, a developer, a
    # sportsbook, a gaming-services firm, another tribe's enterprise. For each
    # of those the agency has answered, in writing, the exact question a press
    # description of "the casino's manager" implicitly asserts. Those rows are
    # emitted here so that the next time any source calls one of these
    # companies a manager, the federal answer is already on file and joined.
    surf = 0
    dealt_companies = " ".join(
        (d.get("Counterparty_or_Funder") or "") + " " + (d.get("Description") or "")
        for d in deals).lower()
    for L in letters:
        co = (L.get("index_company_string") or "").strip()
        if not co or LENDER_RX.search(co):
            continue
        toks = sig_tokens(co) - sig_tokens(L.get("index_tribe_string", ""))
        if not toks:
            continue
        in_ledger = any(t in dealt_companies for t in toks if len(t) > 4)
        surf += 1
        out.append({
            "pair_id": f"DLC-{len(out)+1:04d}", "deal_id": "",
            "deal_source_file": "", "deal_date": "",
            "deal_native_party": "", "deal_counterparty": "",
            "deal_title": "",
            "deal_characterises_counterparty_as_manager": "",
            "cedar_opinion_id": L["cedar_opinion_id"],
            "opinion_date": L["opinion_date"],
            "letter_tribe_string": L.get("index_tribe_string", ""),
            "letter_company_string": co,
            "letter_re_line": L.get("re_line", ""),
            "letter_finding": L.get("is_management_contract", ""),
            "letter_finding_quote": L.get("finding_quote", ""),
            "counterparty_token_overlap": "", "project_token_overlap": "",
            "days_between": "",
            "ruling": "NOT_ESTABLISHED",
            "ruling_basis":
                "No deals-ledger row characterises this company's role at this "
                "tribe's gaming operation, so there is nothing yet to confirm "
                "or contradict. The letter's answer is recorded here in "
                "advance." + ("" if not in_ledger else
                              " A token of this company's name DOES appear "
                              "somewhere in the deals ledger - check by hand."),
            "contradiction_candidate": "0",
            "what_would_settle_it":
                "Any source describing this company as managing or operating "
                "the tribe's gaming facility. If the arrangement it describes "
                "is the one NIGC reviewed, and NIGC found it is not a "
                "management contract, the description is wrong in federal law.",
            "comparison_side": "LETTER_COUNTERPARTY_SURFACE",
            "public_characterisation_to_check":
                f"Is {co} publicly described as managing or operating the "
                f"gaming facility of {L.get('index_tribe_string','')}?",
            "built_date": TODAY})
    print(f"  contradiction-ready operator counterparties: {surf}")

    fields = ["pair_id", "comparison_side", "deal_id", "deal_source_file",
              "deal_date",
              "deal_native_party", "deal_counterparty", "deal_title",
              "deal_characterises_counterparty_as_manager", "cedar_opinion_id",
              "opinion_date", "letter_tribe_string", "letter_company_string",
              "letter_re_line", "letter_finding", "letter_finding_quote",
              "counterparty_token_overlap", "project_token_overlap",
              "days_between", "ruling",
              "ruling_basis", "contradiction_candidate",
              "what_would_settle_it", "public_characterisation_to_check",
              "built_date"]
    write_csv(REVIEW / f"declination_contradictions_{TODAY}.csv", out, fields)
    tally = defaultdict(int)
    for r in out:
        tally[r["ruling"]] += 1
    for k in sorted(tally, key=lambda x: -tally[x]):
        print(f"    {k:42s} {tally[k]}")
    return out


# =========================================================================
# 5. EMPLOYMENT OBSERVATIONS
# =========================================================================
EMP_FIELDS = [
    "observation_id", "facility_id", "tribe_id", "year", "employment",
    "measurement_type", "geographic_level", "source_url", "source_quote",
    "fetched_date", "confidence", "built_date",
    # context, after the required columns
    "source_name", "source_record", "measurement_note", "match_rule",
    "name_in_source", "state", "flags",
]

SUFFIX = re.compile(r"\b(inc|llc|l l c|lp|llp|ltd|corp|corporation|company|co|"
                    r"the|a tribal enterprise|enterprises?)\b")


def nkey(s):
    s = str(s or "").lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = SUFFIX.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def employment_osha(fac, out):
    """OSHA ITA 300A -> OSHA_ESTABLISHMENT_REPORTED."""
    rows = osha_gambling_rows()
    print(f"  OSHA gambling-NAICS establishment-years: {len(rows)}")
    if not rows:
        return
    # exact normalised name equality AND state agreement. No fuzzy matching,
    # no containment - containment is what booked $2.8B onto a school.
    by_name = defaultdict(list)
    by_tokens = defaultdict(list)
    for f in fac:
        st = (f.get("state") or "").upper()
        by_name[(nkey(f["facility_name"]), st)].append(f)
        # Token-set EQUALITY, not containment. "Casino Resort Barona" and
        # "Barona Resort & Casino" are the same multiset of words; containment
        # would also accept "Barona", which is a different claim entirely.
        by_tokens[(frozenset(nkey(f["facility_name"]).split()), st)].append(f)

    # A distinctive token shared with some Cedar property is what makes an
    # unmatched ITA row worth a human's time. ITA's gambling universe is the
    # WHOLE US industry - Las Vegas, riverboats, racinos - so most unmatched
    # rows were never candidates and staging them all would bury the near
    # misses that are the actual work.
    GENERIC_PROP = {"casino", "resort", "hotel", "gaming", "bingo", "club",
                    "lodge", "inn", "center", "centre", "the", "and", "at",
                    "grand", "palace", "star", "gold", "silver", "river",
                    "lake", "valley", "hills", "creek", "mountain", "sky",
                    "eagle", "rock", "spirit", "sun", "north", "south", "east",
                    "west", "new", "las", "vegas", "downs", "park", "plaza"}
    facility_tokens = set()
    for f in fac:
        facility_tokens |= {t for t in nkey(f["facility_name"]).split()
                            if t not in GENERIC_PROP and len(t) > 3}

    # the same figure filed under two property names of one enterprise is ONE
    # enterprise figure, not two property counts. Detected, flagged, kept.
    seen = defaultdict(list)
    matched = held = out_of_universe = 0
    rule_used = defaultdict(int)
    staged = []
    for r in rows:
        st = (r.get("state") or "").upper()
        nm = nkey(r.get("establishment_name"))
        hits = by_name.get((nm, st), [])
        rule = "exact_normalised_establishment_name_and_state"
        if len(hits) != 1:
            hits = by_tokens.get((frozenset(nm.split()), st), [])
            rule = "token_set_equality_and_state"
        emp = (r.get("annual_average_employees") or "").strip()
        if not emp or not emp.replace(".", "").isdigit():
            continue
        yr = (r.get("year_filing_for") or "").split(".")[0]
        quote = "; ".join(
            f'{c}="{(r.get(c) or "")}"' for c in
            ("establishment_name", "company_name", "street_address", "city",
             "state", "naics_code", "annual_average_employees",
             "year_filing_for"))
        if len(hits) != 1:
            shared = {t for t in nm.split()
                      if t not in GENERIC_PROP and len(t) > 3} & facility_tokens
            if not shared:
                out_of_universe += 1
                continue
            held += 1
            staged.append({"establishment_name": r.get("establishment_name"),
                           "city": r.get("city"), "state": r.get("state"),
                           "naics_code": r.get("naics_code"),
                           "annual_average_employees": emp,
                           "year_filing_for": yr,
                           "n_cedar_facilities_matched": len(hits),
                           "distinctive_tokens_shared": "; ".join(sorted(shared)),
                           "why_held": ("shares a distinctive token with a "
                                        "Cedar property but no exact name+state "
                                        "match" if not hits else
                                        "matches more than one Cedar facility"),
                           "YOUR_RULING": "", "built_date": TODAY})
            continue
        f = hits[0]
        matched += 1
        rule_used[rule] += 1
        seen[(f.get("tribe_id", ""), yr, emp)].append(f["facility_id"])
        out.append({
            "observation_id": f"EMP-OSHA-{len(out)+1:06d}",
            "facility_id": f["facility_id"], "tribe_id": f.get("tribe_id", ""),
            "year": yr, "employment": emp,
            "measurement_type": "OSHA_ESTABLISHMENT_REPORTED",
            "geographic_level": "establishment",
            "source_url": OSHA_PAGE, "source_quote": quote,
            "fetched_date": TODAY, "confidence": "high",
            "built_date": TODAY,
            "source_name": "OSHA Injury Tracking Application, Form 300A "
                           "establishment summary",
            "source_record": r.get("_file", ""),
            "measurement_note":
                "The establishment's OWN reported annual average number of "
                "employees on its Form 300A. It is a filing, not an audited "
                "count, and ITA covers only employers meeting the electronic "
                "submission rule. Absence from ITA is a property of ITA.",
            "match_rule": rule,
            "name_in_source": r.get("establishment_name", ""),
            "state": r.get("state", ""), "flags": ""})

    # flag enterprise-level figures filed under several property names
    dupes = 0
    for (tid, yr, emp), fids in seen.items():
        if tid and len(set(fids)) > 1:
            for o in out:
                if (o["measurement_type"] == "OSHA_ESTABLISHMENT_REPORTED"
                        and o["tribe_id"] == tid and o["year"] == yr
                        and o["employment"] == emp):
                    o["flags"] = ("IDENTICAL_VALUE_FILED_UNDER_"
                                  f"{len(set(fids))}_PROPERTY_NAMES_SAME_TRIBE_"
                                  "YEAR - probably ONE enterprise-level figure "
                                  "filed under each property name, not "
                                  "independent property counts. Retained, not "
                                  "merged and not divided.")
                    dupes += 1
    print(f"  OSHA rows attached to exactly one facility: {matched}")
    for k, v in rule_used.items():
        print(f"    by {k}: {v}")
    print(f"  OSHA rows held for a ruling (near miss): {held}")
    print(f"  OSHA rows outside the Cedar property universe entirely: "
          f"{out_of_universe} - ITA covers the WHOLE US gambling industry, so "
          f"most of it is commercial and was never a candidate")
    print(f"  observations flagged as one enterprise figure filed twice: {dupes}")
    # One ruling per ESTABLISHMENT, not per establishment-year. The same
    # casino files every year; asking for the same ruling ten times is how a
    # review queue stops being used.
    collapsed = {}
    for s in staged:
        k = (s["establishment_name"], s["state"])
        c = collapsed.setdefault(k, dict(s, years=[], values=[]))
        c["years"].append(s["year_filing_for"])
        c["values"].append(s["annual_average_employees"])
    for c in collapsed.values():
        yrs = sorted(y for y in c.pop("years") if y)
        vals = c.pop("values")
        c["year_filing_for"] = f"{yrs[0]}-{yrs[-1]}" if yrs else ""
        c["annual_average_employees"] = "; ".join(vals)
        c["n_filings"] = len(vals)
    rows = list(collapsed.values())
    write_csv(REVIEW / f"employment_osha_unmatched_{TODAY}.csv", rows,
              list(rows[0].keys()) if rows else ["establishment_name"])


def employment_lodes(fac, out):
    """LODES8 WAC -> LODES_BLOCK_WORKPLACE_JOBS. BLOCK, never tract."""
    blocks = {b["facility_id"]: b
              for b in read_csv(LODESDIR / "facility_blocks.csv")}
    wac = defaultdict(list)
    for w in read_csv(LODESDIR / "block_wac.csv"):
        wac[w["w_geocode"]].append(w)
    if not wac:
        print("  LODES: no block_wac.csv yet - run the lodes step")
        return
    facd = {f["facility_id"]: f for f in fac}
    n = zero = 0
    for fid, b in blocks.items():
        g = b.get("block_geoid") or ""
        if len(g) != 15:
            continue
        f = facd.get(fid, {})
        hits = wac.get(g, [])
        if not hits:
            # A block absent from WAC has NO jobs allocated to it in that
            # vintage. For a casino block that is a finding, not a gap: either
            # the property genuinely reports no workplace jobs in this block,
            # or - far more likely - the geocoded point falls in a neighbouring
            # block (a parking lot, a right of way) and the jobs sit next door.
            # It is recorded as an absence, not written as a zero.
            zero += 1
            continue
        for w in hits:
            n += 1
            out.append({
                "observation_id": f"EMP-LODES-{n:06d}",
                "facility_id": fid, "tribe_id": f.get("tribe_id", ""),
                "year": w["year"], "employment": w["C000"],
                "measurement_type": "LODES_BLOCK_WORKPLACE_JOBS",
                "geographic_level": "census_block_2020",
                "source_url": w["source_url"],
                "source_quote": f'w_geocode="{g}"; C000="{w["C000"]}"; '
                                f'CNS17="{w.get("CNS17","")}"; '
                                f'CNS18="{w.get("CNS18","")}"',
                "fetched_date": TODAY, "confidence": "medium",
                "built_date": TODAY,
                "source_name": f"Census LEHD LODES8 WAC S000 JT00 {w['year']}",
                "source_record": f"{b['state']}_wac_S000_JT00_{w['year']}.csv.gz",
                "measurement_note":
                    "TOTAL JOBS WHOSE WORKPLACE IS THIS CENSUS BLOCK. This is "
                    "NOT casino payroll. Any other employer in the same block "
                    "is counted here, and a large property may span more than "
                    "one block, in which case this UNDER-counts it. LODES is "
                    "also noise-infused by design for disclosure avoidance. "
                    "Use it as an independent order-of-magnitude observation, "
                    "never as the property's employment. CNS17 (Arts, "
                    "Entertainment and Recreation) and CNS18 (Accommodation "
                    "and Food Services) are carried so the industry mix of the "
                    "block is visible rather than assumed.",
                "match_rule": "facility_lat_lon_geocoded_to_2020_block",
                "name_in_source": "", "state": b.get("state", ""),
                "flags": "BLOCK_JOBS_ARE_NOT_PROPERTY_PAYROLL"})
    print(f"  LODES block observations: {n}")
    print(f"  facilities whose block carries NO jobs in LODES: {zero} "
          f"(recorded as an absence, never written as a zero)")


# --- environmental reviews and official documents ------------------------
PROJ_WORDS = re.compile(
    r"\bexpected to\b|\banticipat|\bproject(?:ed|s)?\b|\bestimat|\bwould\b|"
    r"\bwill (?:create|employ|generate|provide)\b|\bproposed\b|\bupon opening\b|"
    r"\bat build[- ]out\b|\bis expected\b", re.I)
NOW_WORDS = re.compile(r"\bemploys\b|\bemployed\b|\bcurrently employs\b|"
                       r"\bhas a workforce of\b|\bemploying\b", re.I)
EXCLUDE_WORDS = re.compile(
    r"\bconstruction\b|\bindirect\b|\binduced\b|\btemporary\b|\bone-time\b|"
    r"\bin[- ]migrat|\bunemploy|\bschool\b|\bregional economy\b", re.I)
ENV_DOC = re.compile(r"environmental|assessment|\beis\b|\bea\b|fonsi|record of "
                     r"decision|\brod\b|nepa|two[- ]part|section 20", re.I)
NUMPAT = re.compile(
    r"(?:employs?|employing|employ)\s+(?:approximately\s+|about\s+|"
    r"more than\s+|over\s+|nearly\s+)?([\d,]{2,7})"
    r"|([\d,]{2,7})\s+(?:full[- ]time\s+|part[- ]time\s+|permanent\s+|direct\s+|"
    r"new\s+|additional\s+)*(?:jobs|employees|positions|individuals|people|"
    r"persons|workers|full[- ]time equivalents?|FTEs?)")
SENT = re.compile(
    r"[^.]{0,250}\b(?:employ(?:s|ee|ees|ment|ing|ed)|jobs|workforce|"
    r"full[- ]time equivalent)\b[^.]{0,250}\.", re.I)
NAMED_PROPERTY = re.compile(
    r"\b((?:[A-Z][A-Za-z'-]{1,15}\s+){1,4}(?:Casino|Resort|Bingo|Gaming\s+Center|Gaming\s+Facility))\b")
PROPWORD = re.compile(r"casino|resort|gaming facilit|bingo|travel plaza", re.I)


def employment_documents(fac, out):
    """Environmental reviews and other official documents already on disk.

    A PROJECTED figure is not an operating one. cedar_domain.may_promote()
    refuses PROJECTED -> ACTIVE_FLOOR_COUNT and the refusal is asserted below
    rather than trusted.
    """
    import fitz
    dom = load_domain()
    assert not dom.may_promote(dom.MeasurementType.PROJECTED,
                               dom.MeasurementType.ACTIVE_FLOOR_COUNT)
    assert not dom.may_promote(dom.MeasurementType.ENVIRONMENTAL_REVIEW_COUNT,
                               dom.MeasurementType.ACTIVE_FLOOR_COUNT)

    GENERIC_PROP = {"casino", "resort", "hotel", "gaming", "bingo", "club",
                    "lodge", "inn", "center", "centre", "the", "and", "at",
                    "grand", "palace", "star", "gold", "silver", "hall",
                    "travel", "plaza", "card", "room", "facility"}
    by_name = defaultdict(list)
    for f in fac:
        by_name[nkey(f["facility_name"])].append(f)

    # The BIA two-part determinations, RODs and EAs on disk are named for the
    # tribe they concern - `..._keweenaw_bay_letter_to_governor...`,
    # `..._north_fork_rancheria_governors_letter...`. That slug is a tribe
    # attribution the document itself supplies, and it lets a projection for a
    # project with no built property still be keyed to the right nation. The
    # tribe guard from the declination build applies: a containment hit is
    # accepted only toward a government-class spine row whose tokens are a
    # SUBSET of the slug's.
    spine = read_csv(CEDAR / "data" / "spine" / "cedar_entity_spine.csv")
    m91 = load_m91()
    by_idc = {r["tribe_id"]: r for r in spine}
    DROP = re.compile(r"\b(508|compliant|redacted|letter|to|governor|governors|"
                      r"fings|of|fact|record|decision|rod|fonsi|final|draft|ea|"
                      r"eis|notice|availability|signed|pdf|the|and|for|section|"
                      r"two|part|determination|dea|noa|report|appendix)\b")

    def tribe_from_filename(base):
        slug = re.sub(r"[^a-z ]", " ", base.lower())
        slug = re.sub(r"\s+", " ", DROP.sub(" ", slug)).strip()
        if len(slug) < 5:
            return ""
        tid, cname, how = m91.resolve_entity(slug, spine)
        if not tid:
            return ""
        if how == "containment":
            row = by_idc.get(tid, {})
            if row.get("entity_class") not in GOV_CLASSES:
                return ""
            if not m91.core(cname).issubset(m91.core(slug)):
                return ""
        return tid

    TEXTCACHE.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(set(glob.glob(str(CEDAR / "data/raw/external/gaming*/**/*.pdf"),
                                recursive=True)))
    print(f"  scanning {len(pdfs)} official PDFs already on disk")
    staged, n = [], 0
    for p in pdfs:
        cachep = TEXTCACHE / (hashlib.md5(
            os.path.relpath(p, CEDAR).encode()).hexdigest() + ".txt")
        if cachep.exists():
            text = cachep.read_text(encoding="utf-8", errors="replace")
        else:
            try:
                doc = fitz.open(p)
                text = "".join(pg.get_text() for pg in doc)
                doc.close()
            except Exception:
                continue
            cachep.write_text(text, encoding="utf-8", errors="replace")
        base = os.path.basename(p)
        dm = re.search(r"(19|20)\d{2}[.\-_](\d{2})[.\-_](\d{2})", base) \
            or re.search(r"\b(19|20)\d{2}\b", base)
        docyear = dm.group(0)[:4] if dm else ""
        is_env = bool(ENV_DOC.search(base) or ENV_DOC.search(text[:4000]))
        doc_tribe = tribe_from_filename(base)
        for m in SENT.finditer(text):
            s = flat(m.group(0))
            if not PROPWORD.search(s) or EXCLUDE_WORDS.search(s):
                continue
            # PRECISION GUARDS, each one bought by a bad row in an earlier pass.
            #  - "$647,995 $0 GAMING HOTEL FOOD & OTHER DEPT ADMIN ... WAGES"
            #    is a chart's axis labels, extracted as prose. Money symbols and
            #    unusual glyphs mark table and figure furniture, not sentences.
            #  - "Creation of 315 to 1,298 new jobs" is a RANGE, and taking the
            #    upper bound publishes the most flattering number in the source
            #    as if the source had stated it alone.
            #  - More than one multi-digit number in a sentence means the
            #    attachment of the number to the noun is a guess.
            if "$" in s or re.search(r"[■∴□▪●]", s):
                continue
            if re.search(r"\d[\d,]*\s+(?:to|-|through|and)\s+\d[\d,]*", s):
                continue
            allnums = re.findall(r"\b\d[\d,]{1,8}\b", s)
            allnums = [x for x in allnums
                       if not re.fullmatch(r"(19|20)\d{2}", x.replace(",", ""))]
            if len(allnums) != 1:
                continue
            nums = [g for mm in NUMPAT.finditer(s) for g in mm.groups() if g]
            if len(nums) != 1:
                continue
            val = nums[0].replace(",", "")
            if not val.isdigit() or not (10 <= int(val) <= 20000):
                continue
            projected = bool(PROJ_WORDS.search(s))
            operating = bool(NOW_WORDS.search(s))
            if projected:
                mt = "PROJECTED"
            elif operating:
                mt = "ENVIRONMENTAL_REVIEW_COUNT" if is_env else "PROPERTY_REPORTED_COUNT"
            else:
                continue
            # PROPERTY ATTRIBUTION
            # -------------------
            # The WHOLE facility name must appear in the sentence, and at least
            # one of its tokens must be distinctive. "The Ojibwa Casino Resort
            # employs 359 individuals" attaches to the facility "Ojibwa Casino"
            # because every token of the facility name is in the sentence and
            # `ojibwa` is not a generic gaming word. The opposite direction is
            # refused: a sentence saying only "the Casino" attaches to nothing,
            # and a facility whose only matching token is `casino` attaches to
            # nothing. This is the AGENTS.md guard that the RECORD must be at
            # least as specific as the ENTITY, applied to property names.
            stoks = set(nkey(s).split())
            fid = tid = pname = ""
            best = None
            for k, fs in by_name.items():
                kt = set(k.split())
                if not kt or len(fs) != 1 or not kt <= stoks:
                    continue
                if not any(t not in GENERIC_PROP and len(t) > 3 for t in kt):
                    continue
                if best is None or len(kt) > len(best[0]):
                    best = (kt, fs[0])
            if best:
                fid = best[1]["facility_id"]
                tid = best[1].get("tribe_id", "")
                pname = best[1]["facility_name"]
            # A DOCUMENT'S TRIBE IS NOT THE SENTENCE'S TRIBE
            # ----------------------------------------------
            # "Legends Casino employs over 700 people" appears inside a
            # COLVILLE environmental document as a comparison case. Legends is
            # Yakama's. Falling back to the document's tribe booked another
            # nation's casino to Colville. So the fallback is allowed only when
            # the sentence names NO specific property: if it names one and that
            # name did not resolve to a Cedar facility, the row is held instead.
            named = NAMED_PROPERTY.search(m.group(0))
            if not fid and named:
                staged.append({
                    "employment": val, "measurement_type": mt,
                    "year": docyear, "source_quote": s,
                    "source_record": os.path.relpath(p, CEDAR),
                    "why_held": f"names a specific property "
                                f"('{flat(named.group(1))}') that did not "
                                f"resolve to a Cedar facility; the document's "
                                f"own tribe was NOT substituted",
                    "YOUR_RULING": "", "built_date": TODAY})
                continue
            if not tid:
                tid = doc_tribe
            row = {
                "observation_id": f"EMP-DOC-{n+1:06d}",
                "facility_id": fid, "tribe_id": tid, "year": docyear,
                "employment": val, "measurement_type": mt,
                "geographic_level": "property" if fid else "named_project",
                "source_url": "", "source_quote": s,
                "fetched_date": TODAY, "confidence": "medium" if fid else "low",
                "built_date": TODAY,
                "source_name": base,
                "source_record": os.path.relpath(p, CEDAR),
                "measurement_note":
                    ("A PROJECTED figure from a planning document. It is not an "
                     "operating count and never becomes one: "
                     "cedar_domain.may_promote() refuses PROJECTED -> "
                     "ACTIVE_FLOOR_COUNT. The project may have been built at a "
                     "different size, later, or not at all."
                     if mt == "PROJECTED" else
                     "An employment figure stated in an official document about "
                     "an operating property. It is the document's number, on "
                     "the document's date, and is not reconciled against any "
                     "other source."),
                "match_rule": ("exact_normalised_property_name_in_sentence"
                               if fid else "no_property_name_matched"),
                "name_in_source": pname, "state": "", "flags":
                    "" if fid else "NO_CEDAR_FACILITY_MATCHED_ON_NAME"}
            if fid or tid:
                row["confidence"] = "medium" if fid else "low"
                row["geographic_level"] = "property" if fid else "named_project"
                out.append(row)
                n += 1
            else:
                staged.append({**{k: row[k] for k in
                                  ("employment", "measurement_type", "year",
                                   "source_quote", "source_record")},
                               "why_held": "no Cedar facility name appears in "
                                           "the sentence",
                               "YOUR_RULING": "", "built_date": TODAY})
    print(f"  document observations attached to a facility or tribe: {n}")
    print(f"  document figures held for a ruling: {len(staged)}")
    if staged:
        write_csv(REVIEW / f"employment_document_unmatched_{TODAY}.csv", staged,
                  list(staged[0].keys()))


def employment_projections(fac, out):
    """The projections already parsed from environmental reviews (script 82)."""
    rows = read_csv(CLEAN / "gaming_projections.csv")
    keep = [r for r in rows if re.search(
        r"^(operational_jobs|operational_jobs_direct|employment_full|"
        r"employment_net)$", r.get("metric", ""))]
    pf = {r["project_id"]: r for r in read_csv(CLEAN / "gaming_project_facilities.csv")} \
        if (CLEAN / "gaming_project_facilities.csv").exists() else {}
    n = 0
    for r in keep:
        val = (r.get("value") or "").replace(",", "")
        if not val.replace(".", "").isdigit():
            continue
        link = pf.get(r.get("project_id", ""), {})
        n += 1
        out.append({
            "observation_id": f"EMP-EA-{n:06d}",
            "facility_id": link.get("facility_id", ""),
            "tribe_id": link.get("tribe_id", ""),
            "year": (r.get("source_document_date") or "")[:4],
            "employment": val, "measurement_type": "PROJECTED",
            "geographic_level": r.get("geography", "") or "named_project",
            "source_url": r.get("source_url", ""),
            "source_quote":
                "; ".join(f'{k}="{r.get(k, "")}"' for k in
                          ("metric", "value", "unit", "impact_type",
                           "geography", "time_period", "source_document",
                           "page")),
            "fetched_date": TODAY, "confidence": r.get("confidence", "medium"),
            "built_date": TODAY,
            "source_name": r.get("source_document", ""),
            "source_record": f"gaming_projections.csv::{r.get('project_id','')}",
            "measurement_note":
                "A projection from an environmental review, for a project that "
                "may not exist. PROJECTED never becomes ACTIVE. The unit is "
                "carried verbatim because 'full-time equivalent', 'full and "
                "part-time' and 'permanent direct' are three different things.",
            "match_rule": "gaming_projections_project_id",
            "name_in_source": r.get("tribe", ""), "state": "",
            "flags": "PROJECTION_NOT_AN_OPERATING_COUNT"})
    print(f"  environmental-review projections carried: {n}")


def build_employment():
    print("\n=== 5. EMPLOYMENT OBSERVATIONS ===")
    fac = read_csv(CLEAN / "gaming_facilities.csv")
    out = []
    employment_osha(fac, out)
    employment_lodes(fac, out)
    employment_documents(fac, out)
    employment_projections(fac, out)

    # Casino City carries an `employees` column on gaming_facilities.csv. It is
    # a LICENSED vendor value: QA only, never published. It is deliberately NOT
    # a source here, and the count of what it would have added is recorded so
    # the omission is visible rather than silent.
    vend = sum(1 for f in fac if (f.get("employees") or "").strip())
    print(f"  NOT USED: {vend} vendor (Casino City) employee values - licensed, "
          f"internal QA only, may never publish")

    for i, r in enumerate(out, 1):
        r["observation_id"] = r["observation_id"]
    write_csv(CLEAN / "gaming_employment_observations.csv", out, EMP_FIELDS)

    bysrc = defaultdict(int)
    for r in out:
        bysrc[r["measurement_type"]] += 1
    print("  by measurement_type:")
    for k in sorted(bysrc, key=lambda x: -bysrc[x]):
        print(f"    {k:34s} {bysrc[k]}")
    permt = defaultdict(set)
    for r in out:
        if r["facility_id"]:
            permt[r["facility_id"]].add(r["measurement_type"])
    multi = [f for f, s in permt.items() if len(s) >= 2]
    print(f"  facilities with an employment observation: {len(permt)}")
    print(f"  facilities with 2+ INDEPENDENT measurement types: {len(multi)}")
    return out, multi


# ------------------------------------------------------------- codebook
def write_codebook(emp_rows):
    cb = DOCS / "codebooks" / "07c_gaming_employment.md"
    cb.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Codebook - `data/clean/gaming_employment_observations.csv`",
        "",
        "*Variables only. One row is one employment figure from one source for "
        "one year. Multiple figures for one property-year are expected and are "
        "NOT reconciled.*",
        "",
        "| variable | type | definition |",
        "|---|---|---|",
        "| `observation_id` | string | Cedar id. `EMP-OSHA-`, `EMP-LODES-`, "
        "`EMP-DOC-`, `EMP-EA-` by source family. |",
        "| `facility_id` | string | Cedar property id (`CCP-`/`VP-`/`TPL-`). "
        "Blank where the figure could not be attached to one property. |",
        "| `tribe_id` | string | Cedar entity id of the tribe, from "
        "`gaming_facilities.csv`. Never inferred from the source's own naming. |",
        "| `year` | integer | Year the figure refers to: OSHA "
        "`year_filing_for`, the LODES vintage, or the document's own date. "
        "Blank if the source carries no date. |",
        "| `employment` | integer | The figure exactly as the source states it. "
        "Never rounded, scaled, deflated or reconciled. |",
        "| `measurement_type` | enum | `OSHA_ESTABLISHMENT_REPORTED`, "
        "`LODES_BLOCK_WORKPLACE_JOBS`, `ENVIRONMENTAL_REVIEW_COUNT`, "
        "`PROJECTED`, `PROPERTY_REPORTED_COUNT`. From `cedar_domain."
        "MeasurementType`. `PROJECTED` and `ENVIRONMENTAL_REVIEW_COUNT` are in "
        "`NEVER_PROMOTES_TO_ACTIVE`. |",
        "| `geographic_level` | enum | What the number is measured over: "
        "`establishment`, `census_block_2020`, `property`, `named_project`, or "
        "the document's own geography string. |",
        "| `source_url` | string | The publisher's URL. Populated on every row "
        "whose source is a web object. |",
        "| `source_quote` | string | Verbatim support. For prose sources, the "
        "sentence as printed (whitespace collapsed, nothing else changed). For "
        "tabular sources, the source's own field names and values quoted "
        "exactly, because a CSV row has no sentence. |",
        "| `fetched_date` | date | When Cedar retrieved the object. |",
        "| `confidence` | enum | `high` / `medium` / `low`. Not a probability "
        "and not an interval. |",
        "| `built_date` | date | When this row was written. |",
        "| `source_name` | string | Human-readable source, e.g. *OSHA Injury "
        "Tracking Application, Form 300A establishment summary*. |",
        "| `source_record` | string | The exact file the row came from. |",
        "| `measurement_note` | string | What this measurement is and is not. "
        "Travels with the row so a join cannot lose it. |",
        "| `match_rule` | string | How the figure was attached to the property. "
        "Exact normalised name equality only; no containment, no fuzzy match. |",
        "| `name_in_source` | string | The property/establishment name as the "
        "source writes it. A regulator using a different name is an ALIAS, not "
        "a second property. |",
        "| `state` | string | State as the source records it. |",
        "| `flags` | string | Machine-readable cautions, e.g. "
        "`BLOCK_JOBS_ARE_NOT_PROPERTY_PAYROLL`, "
        "`IDENTICAL_VALUE_FILED_UNDER_n_PROPERTY_NAMES_SAME_TRIBE_YEAR`. |",
        "",
    ]
    cb.write_text("\n".join(lines), encoding="utf-8")
    print(f"  wrote {cb.relative_to(CEDAR)}")

    add = [
        "",
        "## Variables added 2026-08-07 (script 100)",
        "",
        "### `nigc_declination_letters.csv`",
        "",
        "| variable | type | definition |",
        "|---|---|---|",
        "| `evidentiary_stage` | enum | Always `NIGC_REVIEWED` on a letter. The "
        "letter proves review of submitted unexecuted documents and nothing "
        "further. |",
        "| `evidentiary_ladder` | string | `" + EVIDENTIARY_LADDER + "` |",
        "| `evidentiary_stage_basis` | string | The agency's own sentence "
        "supporting the stage. |",
        "| `what_this_does_not_establish` | string | Execution, closing, "
        "construction, opening, continued operation, land status, gaming "
        "eligibility. |",
        "| `what_would_advance_the_stage` | string | The document class that "
        "would move the row to the next rung. |",
        "| `text_recovery_status` | enum | `ocr_recovered`, "
        "`ocr_returned_too_little_text`, or blank where a publisher text layer "
        "existed. |",
        "| `ocr_engine` / `ocr_dpi` / `ocr_date` | string | Provenance of the "
        "recovered text. |",
        "| `ocr_text_chars` / `ocr_common_word_ratio` | integer / float | Volume "
        "and plausibility of the recovered text. |",
        "| `finding_evidence_basis` | enum | `OCR_RECOVERED` where the finding "
        "was read from OCR rather than a text layer. |",
        "| `ocr_caution` | string | Why an OCR-derived finding is weaker: a "
        "negation eaten by OCR inverts the finding. |",
        "",
        "### `gaming_financing_events.csv`",
        "",
        "| variable | type | definition |",
        "|---|---|---|",
        "| `evidentiary_stage` | enum | Always `EXECUTION_UNCONFIRMED`. |",
        "| `evidentiary_ladder` | string | As above. |",
        "| `evidentiary_stage_basis` | string | Why the event is evidenced but "
        "its execution is not. |",
        "| `property_attachment_caution` | string | A financing is never "
        "attached to a property because the enterprise owns it. |",
        "| `text_basis` | enum | `OCR_RECOVERED` on events derived from a "
        "recovered image-only letter. |",
        "",
        "### `gaming_source_claims.csv`",
        "",
        "| variable | type | definition |",
        "|---|---|---|",
        "| `evidentiary_stage` | enum | Always `NIGC_REVIEWED`. |",
        "| `evidentiary_ladder` | string | As above. |",
        "| `claim_scope_caution` | string | Tribe, gaming authority, gaming "
        "enterprise, property-owning subsidiary and operating company are five "
        "different legal persons. |",
        "",
    ]
    # NOT appended to docs/codebooks/07_gaming.md. That file is REGENERATED by
    # script 24, and a concurrent agent overwrote an append to it within the
    # hour - the append was made, verified, and gone twenty minutes later.
    # Variables this build owns live in a file this build owns.
    g = DOCS / "codebooks" / "07d_nigc_declination_variables.md"
    g.write_text("# Codebook - NIGC declination layer\n"
                 "\n*Variables only. Written by "
                 "`code/100_finish_declinations_and_employment.py`.*\n"
                 + "\n".join(add), encoding="utf-8")
    print(f"  wrote {g.relative_to(CEDAR)}")


# ------------------------------------------------------------------- build
def step_build():
    REVIEW.mkdir(parents=True, exist_ok=True)
    # Restore BEFORE reading. Restoring after would verify one vintage of the
    # file and then build on another - which is how a rerun quietly stacked a
    # second pass of financing events on top of the first.
    backup(CLEAN / "nigc_declination_letters.csv")
    backup(CLEAN / "gaming_financing_events.csv")
    backup(CLEAN / "gaming_source_claims.csv")

    letters, claims, events = verify_declinations()

    letters, events, ocr_claims, new_events = apply_ocr(letters, events)
    letters, events, claims = apply_ladder(letters, events, claims)

    lf = list(dict.fromkeys(
        [k for r in letters for k in r.keys()]))
    write_csv(CLEAN / "nigc_declination_letters.csv", letters, lf)
    ef = list(dict.fromkeys([k for r in events for k in r.keys()]))
    write_csv(CLEAN / "gaming_financing_events.csv", events, ef)
    cf = list(dict.fromkeys([k for r in claims for k in r.keys()]))
    write_csv(CLEAN / "gaming_source_claims.csv", claims, cf)
    if ocr_claims:
        write_csv(REVIEW / f"nigc_declination_ocr_claims_{TODAY}.csv",
                  ocr_claims, list(ocr_claims[0].keys()))
    affirm = [r for r in letters
              if "HELD_FOR_REVIEW" in (r.get("is_management_contract", "")
                                       + r.get("chair_approval_required", "")
                                       + r.get("sole_proprietary_interest_analysis", ""))]
    if affirm:
        write_csv(REVIEW / f"nigc_declination_ocr_affirmative_{TODAY}.csv",
                  affirm, ["cedar_opinion_id", "opinion_date",
                           "index_tribe_string", "index_company_string",
                           "is_management_contract", "finding_quote",
                           "chair_approval_required", "chair_approval_quote",
                           "sole_proprietary_interest_analysis",
                           "sole_proprietary_interest_quote", "ocr_caution",
                           "pdf_path"])

    build_contradictions(letters)
    emp, multi = build_employment()
    write_codebook(emp)
    print("\nDone.")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "ocr":
        shard = int(sys.argv[2]) if len(sys.argv) > 3 else 0
        nsh = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        step_ocr(shard, nsh)
    elif cmd == "index":
        step_index()
    elif cmd == "osha":
        step_osha()
    elif cmd == "geocode":
        step_geocode()
    elif cmd == "lodes":
        step_lodes()
    elif cmd == "build":
        step_build()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
