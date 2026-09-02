"""30_funding_pre2008.py — FY2001-2007 assistance backfill, all major agencies.

Extends the Interior-only FY2001-2007 slice (data/clean/faads_transactions.csv,
built by the prior FAADS feasibility run) to the other major federal funders of
Indian Country, using the route that run proved:

    POST https://api.usaspending.gov/api/v2/bulk_download/awards/
    prime_award_types 02..11, date_type=action_date, awarding toptier=<agency>

The search index floor of FY2008 does not apply to bulk_download, which reaches
2000-10-01. Pre-2008 rows come back in the identical modern assistance schema.

DESIGN CONSTRAINTS (all learned the hard way, do not remove):
  * The API edge rate-limits by IP and the block does not clear quickly. Every
    job is therefore checkpointed to state.json the moment it lands, and the
    script is fully resumable: rerun it and it skips what is already on disk.
  * Jobs are submitted ONE at a time with a deliberate inter-job sleep.
  * Nothing is fabricated. If an agency-year is not retrieved it simply is not
    in the output, and it is named in the build log.
  * tribe_id is BLANK on every row. No name matching. Tier C.

STAGES
  pull      submit/poll/download bulk jobs, agency by agency (resumable)
  build     extract staged zips -> data/clean/faads_transactions_all_agencies.csv
  coverage  -> data/clean/faads_identifier_coverage_by_agency_year.csv
  manifest  update data/raw/external/faads/_SOURCE_MANIFEST_faads.csv

Usage:
  py -3 code/30_funding_pre2008.py pull [--only slug,slug] [--sleep 90]
  py -3 code/30_funding_pre2008.py build
  py -3 code/30_funding_pre2008.py coverage
  py -3 code/30_funding_pre2008.py manifest
  py -3 code/30_funding_pre2008.py all
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw", "external", "faads")
AGENCY_DIR = os.path.join(RAW, "agencies")
CLEAN = os.path.join(ROOT, "data", "clean")
LOGFILE = os.path.join(ROOT, "logs", "30_funding_pre2008.log")
STATE = os.path.join(AGENCY_DIR, "_state.json")
MANIFEST = os.path.join(RAW, "_SOURCE_MANIFEST_faads.csv")

API = "https://api.usaspending.gov/api/v2/bulk_download/awards/"
STATUS = "https://api.usaspending.gov/api/v2/bulk_download/status/"
UA = "CedarPress-research/1.0"
FETCHED = "2026-08-05"

FY_FIRST, FY_LAST = 2001, 2007
PRIME_TYPES = ["02", "03", "04", "05", "06", "07", "08", "09", "10", "11"]

# Priority order set by the task brief. Names must match USAspending toptier
# agency names exactly; verified at runtime against /references/toptier_agencies/.
AGENCIES = [
    ("hhs", "Department of Health and Human Services"),
    ("ed", "Department of Education"),
    ("hud", "Department of Housing and Urban Development"),
    ("usda", "Department of Agriculture"),
    ("doj", "Department of Justice"),
    ("dol", "Department of Labor"),
    ("epa", "Environmental Protection Agency"),
    ("dot", "Department of Transportation"),
    ("doe", "Department of Energy"),
    ("doc", "Department of Commerce"),
]

# Column subset requested from the API. 20 of the 112 columns — everything the
# Cedar Press output schema needs plus the two identifier fields the open
# question turns on. Keeps USDA/HHS-scale files to a size this disk can hold.
COLUMNS = [
    "action_date_fiscal_year",
    "action_date",
    "cfda_number",
    "cfda_title",
    "awarding_agency_name",
    "awarding_sub_agency_name",
    "recipient_name",
    "recipient_city_name",
    "recipient_state_code",
    "recipient_zip_code",
    "recipient_duns",
    "recipient_uei",
    "business_types_code",
    "business_types_description",
    "federal_action_obligation",
    "assistance_type_code",
    "assistance_type_description",
    "award_id_fain",
    "record_type_code",
    "usaspending_permalink",
    # THE ROOT CAUSE OF THE MISSING TRANSACTION KEY, fixed 2026-09-01 (faads).
    # `to_out_row` was taught to carry `assistance_transaction_unique_key` on
    # 2026-08-29, but the FY2001-2006 bulk jobs were REQUESTED with this
    # 20-column subset and the key was not in it, so the staged zips for those
    # years physically do not contain it and no re-extract can recover it.
    # (The FY2007 `*_archive.zip` objects and the seven DOI seam zips are full
    # 112-column downloads and DO carry it - that is why FY2007 and Interior
    # come back keyed and FY2001-2006 for the other nine agencies do not.)
    # Any future pull now asks for it. See docs/FAADS_TRANSACTION_KEY_LOG.md.
    "assistance_transaction_unique_key",
    "modification_number",
]

OUT_COLS = [
    "fiscal_year", "cfda_program", "agency", "recipient_name", "recipient_type",
    "recipient_city", "recipient_state", "recipient_zip", "recipient_duns",
    "obligated_usd", "assistance_type", "action_date", "source_url",
    "fetched_date", "tribe_id", "recipient_uei", "recipient_type_description",
    "cfda_title", "assistance_type_description", "awarding_sub_agency",
    "award_id_fain", "record_type", "api_endpoint", "source_file",
    # `cedar_uid` is stamped by 503_identity.py and is BLANK on every row of
    # both faads tables (tribe_id is blank here by design - tier C, no name
    # matching). It is carried anyway, in its original position, because a
    # rebuild that silently narrows a shipped header is the defect this
    # project has paid for most often; 62's
    # `files_with_columns_lost_vs_backup` exists to catch exactly this.
    "cedar_uid",
    # THE TRANSACTION IDENTITY. Added 2026-08-29 - see `to_out_row`. The bulk
    # download is a TRANSACTION feed; without these two columns two distinct
    # assistance actions on one FAIN are one indistinguishable row, which is
    # what 179,259 "literal duplicate rows" in this table actually are.
    "assistance_transaction_unique_key", "modification_number",
]

#: The 24-column schema this file had before the transaction identity was
#: added. The prior Interior slice on disk is still in it, and a rebuild must
#: carry those rows forward with the two new columns BLANK rather than refuse -
#: an empty transaction key is honest about a row whose source did not record
#: one here, and refusing would mean the schema fix could never be applied.
OUT_COLS_PRE_TRANSACTION_KEY = [
    c for c in OUT_COLS
    if c not in ("assistance_transaction_unique_key", "modification_number")
]

#: And the schema BEFORE 503 stamped `cedar_uid`. Both older shapes are
#: accepted on read and widened on write; neither is ever written back.
OUT_COLS_PRE_CEDAR_UID = [
    c for c in OUT_COLS_PRE_TRANSACTION_KEY if c != "cedar_uid"
]

#: Every accepted shape of the prior Interior slice, widest first.
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


PRIOR_SCHEMAS = (OUT_COLS, OUT_COLS_PRE_TRANSACTION_KEY, OUT_COLS_PRE_CEDAR_UID)

# If an agency-slice exceeds this many rows, only the source-flagged tribal rows
# (business_types_code containing 'I') are written to the combined transactions
# file. The full raw zip is still staged and the coverage table is still computed
# on the FULL universe, so nothing is lost and no statistic is degraded.
TRIBAL_ONLY_ROW_THRESHOLD = 3_000_000


def log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')}] {msg}"
    print(line, flush=True)
    os.makedirs(os.path.dirname(LOGFILE), exist_ok=True)
    with open(LOGFILE, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


# ---------------------------------------------------------------- http helpers

def _post(url: str, payload: dict, timeout: int = 180):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json", "User-Agent": UA},
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _get(url: str, timeout: int = 120):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def api_available() -> bool:
    try:
        _get("https://api.usaspending.gov/api/v2/references/agency/020/", timeout=40)
        return True
    except urllib.error.HTTPError:
        return True          # edge is answering; that is all we are testing
    except Exception:
        return False


def verify_agency_names() -> dict:
    """Confirm every configured toptier name exists. Fail loudly, never guess."""
    d = _get("https://api.usaspending.gov/api/v2/references/toptier_agencies/")
    have = {r["agency_name"]: r.get("toptier_code") for r in d["results"]}
    out, missing = {}, []
    for slug, name in AGENCIES:
        if name in have:
            out[slug] = (name, have[name])
        else:
            missing.append((slug, name))
    if missing:
        log(f"FATAL agency names not found in USAspending toptier list: {missing}")
        cand = [n for n in have if "Department" in n or "Agency" in n]
        log("available (first 40): " + "; ".join(sorted(cand)[:40]))
        raise SystemExit(2)
    return out


# ------------------------------------------------------------------- state io

def load_state() -> dict:
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as fh:
            return json.load(fh)
    return {"jobs": {}, "range_mode": None}


def save_state(st: dict) -> None:
    os.makedirs(AGENCY_DIR, exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(st, fh, indent=1)
    os.replace(tmp, STATE)


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ----------------------------------------------------------------- pull stage

def build_payload(agency_name: str, start: str, end: str) -> dict:
    return {
        "filters": {
            "prime_award_types": PRIME_TYPES,
            "date_type": "action_date",
            "date_range": {"start_date": start, "end_date": end},
            "agencies": [{"type": "awarding", "tier": "toptier", "name": agency_name}],
        },
        "columns": COLUMNS,
        "file_format": "csv",
    }


def submit(key: str, agency_name: str, start: str, end: str) -> str:
    """Submit one bulk job. Returns the generated file_name (the job handle).

    Falls back to the full 112-column schema if the column subset is rejected,
    so a schema quibble never costs us an agency.
    """
    log(f"  SUBMIT {key}: {agency_name} {start}..{end}")
    payload = build_payload(agency_name, start, end)
    try:
        resp = _post(API, payload)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:500]
        if e.code == 400 and "columns" in detail.lower():
            log(f"  column subset rejected ({detail}); retrying with full schema")
            payload.pop("columns", None)
            resp = _post(API, payload)
        else:
            raise
    file_name = resp.get("file_name")
    if not file_name:
        raise RuntimeError(f"no file_name in response: {resp}")
    log(f"  job accepted: {file_name}")
    return file_name


def wait_and_fetch(key: str, file_name: str, agency_name: str, start: str,
                   end: str, dest: str, max_wait: int = 3600) -> dict:
    """Poll a submitted job to completion and stream the zip to dest."""
    meta, waited = {}, 0
    while waited < max_wait:
        time.sleep(20)
        waited += 20
        meta = _get(STATUS + "?file_name=" + urllib.parse.quote(file_name))
        s = meta.get("status")
        if s == "finished":
            break
        if s == "failed":
            raise RuntimeError(f"job failed: {meta.get('message')}")
        if waited % 120 == 0:
            log(f"  ...{s} after {waited}s")
    if meta.get("status") != "finished":
        raise RuntimeError(f"job not finished after {max_wait}s: {meta.get('status')}")

    log(f"  finished: rows={meta.get('total_rows')} cols={meta.get('total_columns')} "
        f"size={meta.get('total_size')}KB elapsed={meta.get('seconds_elapsed')}s")

    url = meta.get("file_url")
    if not url:
        raise RuntimeError(f"finished job has no file_url: {meta}")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    tmp = dest + ".part"
    with urllib.request.urlopen(req, timeout=1800) as r, open(tmp, "wb") as fh:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            fh.write(chunk)
    os.replace(tmp, dest)
    meta["_local_file"] = os.path.relpath(dest, ROOT).replace("\\", "/")
    meta["_bytes"] = os.path.getsize(dest)
    meta["_sha256"] = sha256(dest)
    meta["_agency_name"] = agency_name
    meta["_date_range"] = [start, end]
    meta["_retrieved"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log(f"  saved {meta['_local_file']} ({meta['_bytes']:,} bytes)")
    return meta


def missing_years(slug: str, st: dict) -> list:
    """Fiscal years for this agency not already on disk from either route.

    The Award Data Archive's assistance coverage starts at FY2007, so it
    supplies FY2007 free for every agency and the generated-job budget only has
    to cover FY2001-2006. Never spend a job on data already held.
    """
    out = []
    for fy in range(FY_FIRST, FY_LAST + 1):
        akey = f"{slug}_fy{fy}_archive"
        if akey in st.get("archive", {}) and os.path.exists(
                os.path.join(AGENCY_DIR, akey + ".zip")):
            continue
        jkey = f"{slug}_fy{fy}"
        if jkey in st.get("jobs", {}) and os.path.exists(
                os.path.join(AGENCY_DIR, jkey + ".zip")):
            continue
        out.append(fy)
    return out


def units_for(slug: str, mode: str, st: dict):
    fys = missing_years(slug, st)
    if not fys:
        return []
    if mode == "multi":
        lo, hi = min(fys), max(fys)
        return [(f"{slug}_fy{lo}_{hi}", f"{lo-1}-10-01", f"{hi}-09-30")]
    return [(f"{slug}_fy{fy}", f"{fy-1}-10-01", f"{fy}-09-30") for fy in fys]


def stage_pull(only=None, sleep_between=90) -> None:
    if not api_available():
        log("PULL ABORTED — api.usaspending.gov is not answering (edge block still "
            "active). Nothing submitted. Rerun this stage when the probe clears.")
        raise SystemExit(3)

    names = verify_agency_names()
    log("agency names verified against /references/toptier_agencies/: "
        + ", ".join(f"{s}={c}" for s, (n, c) in names.items()))

    os.makedirs(AGENCY_DIR, exist_ok=True)
    st = load_state()
    todo = [(s, n) for s, n in AGENCIES if not only or s in only]
    if not todo:
        log("nothing to do")
        return

    # Establish once whether a single job can span FY2001-2007 or whether the
    # endpoint caps date_range at one year. The probe IS the first real job, so
    # no request is wasted either way.
    mode = st.get("range_mode")
    first_handle = None
    first_key = None
    if not mode:
        slug0, name0 = todo[0]
        fys0 = missing_years(slug0, st)
        lo, hi = (min(fys0), max(fys0)) if fys0 else (FY_FIRST, FY_LAST)
        first_key = f"{slug0}_fy{lo}_{hi}"
        try:
            first_handle = submit(first_key, name0, f"{lo-1}-10-01", f"{hi}-09-30")
            mode = "multi"
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:400]
            log(f"  multi-year range rejected (HTTP {e.code}): {detail}")
            mode = "year"
        st["range_mode"] = mode
        save_state(st)
        log(f"RANGE MODE = {mode}")

    for slug, agency_name in todo:
        units = units_for(slug, mode, st)
        if not units:
            log(f"AGENCY COMPLETE: {slug} (all FY{FY_FIRST}-{FY_LAST} already held)")
            continue
        for key, start, end in units:
            dest = os.path.join(AGENCY_DIR, key + ".zip")
            if key in st["jobs"] and os.path.exists(dest):
                log(f"SKIP {key} (already staged, {st['jobs'][key].get('total_rows')} rows)")
                continue
            # Already retrieved via the static Award Data Archive? Then this
            # agency-year costs no generated job. The request budget is the
            # binding constraint; never spend it twice on the same data.
            akey = key + "_archive"
            if akey in st.get("archive", {}) and os.path.exists(
                    os.path.join(AGENCY_DIR, akey + ".zip")):
                log(f"SKIP {key} (already held from Award Data Archive)")
                continue
            try:
                handle = first_handle if key == first_key else None
                first_handle = None
                if handle is None:
                    handle = submit(key, agency_name, start, end)
                meta = wait_and_fetch(key, handle, agency_name, start, end, dest)
            except Exception as e:
                log(f"FAIL {key}: {type(e).__name__}: {e}")
                log("STOPPING. Progress is checkpointed; rerun `pull` to resume "
                    "from exactly here. No partial or invented rows were written.")
                save_state(st)
                raise SystemExit(4)
            st["jobs"][key] = meta
            save_state(st)          # checkpoint immediately
            log(f"CHECKPOINT {key} written to state.json")
            time.sleep(sleep_between)
        log(f"AGENCY COMPLETE: {slug}")
    log("PULL STAGE COMPLETE")


# ------------------------------------------------- alternate route: archive

ARCHIVE = "https://files.usaspending.gov/award_data_archive/"


def archive_index() -> list:
    """List the pre-generated Award Data Archive files.

    These are static per-agency, per-fiscal-year assistance files USAspending
    publishes itself. They cost no job generation, which is the resource the
    edge rate-limits, so they are the gentler route when it is available.
    """
    req = urllib.request.Request(ARCHIVE, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        html = r.read().decode(errors="replace")
    import re
    # Agency codes are NOT uniformly 3 digits — Labor is 1601, and a \d{3}
    # pattern silently drops it. Match 3-4 digits.
    return sorted(set(re.findall(r'(FY\d{4}_\d{3,4}_Assistance_Full_\d+\.zip)', html)))


def stage_pull_archive(only=None, sleep_between=30) -> None:
    """Fallback puller: static archive files instead of generated bulk jobs."""
    if not api_available():
        log("ARCHIVE PULL ABORTED — usaspending edge not answering.")
        raise SystemExit(3)
    names = verify_agency_names()
    try:
        files = archive_index()
    except Exception as e:
        log(f"archive index unavailable: {type(e).__name__}: {e}")
        raise SystemExit(3)
    log(f"archive index: {len(files)} assistance files listed")

    os.makedirs(AGENCY_DIR, exist_ok=True)
    st = load_state()
    st.setdefault("archive", {})
    for slug, agency_name in AGENCIES:
        if only and slug not in only:
            continue
        code = names[slug][1]
        for fy in range(FY_FIRST, FY_LAST + 1):
            want = [f for f in files if f.startswith(f"FY{fy}_{code}_")]
            if not want:
                log(f"  archive has no FY{fy} file for {slug} ({code})")
                continue
            fn = want[-1]
            key = f"{slug}_fy{fy}_archive"
            dest = os.path.join(AGENCY_DIR, key + ".zip")
            if key in st["archive"] and os.path.exists(dest):
                log(f"SKIP {key}")
                continue
            try:
                req = urllib.request.Request(ARCHIVE + fn, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=1800) as r, open(dest + ".part", "wb") as fh:
                    while True:
                        chunk = r.read(1 << 20)
                        if not chunk:
                            break
                        fh.write(chunk)
                os.replace(dest + ".part", dest)
            except Exception as e:
                log(f"FAIL {key}: {type(e).__name__}: {e}")
                save_state(st)
                raise SystemExit(4)
            st["archive"][key] = {
                "_local_file": os.path.relpath(dest, ROOT).replace("\\", "/"),
                "_bytes": os.path.getsize(dest), "_sha256": sha256(dest),
                "_agency_name": agency_name, "_source": ARCHIVE + fn,
                "_retrieved": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            }
            save_state(st)
            log(f"CHECKPOINT {key}: {st['archive'][key]['_bytes']:,} bytes")
            time.sleep(sleep_between)
    log("ARCHIVE PULL COMPLETE")


# ---------------------------------------------------------------- build stage

def iter_zip_rows(path: str):
    """Yield dict rows from every CSV member of a bulk-download zip."""
    with zipfile.ZipFile(path) as z:
        for member in z.namelist():
            if not member.lower().endswith(".csv"):
                continue
            with z.open(member) as fh:
                rd = csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8-sig"))
                for row in rd:
                    yield row


def estimate_rows(path: str) -> int:
    """Estimate row count from uncompressed size and a sampled mean line length.

    Used only to decide whether a slice is too large to carry in full; it never
    touches a reported statistic.
    """
    with zipfile.ZipFile(path) as z:
        members = [zi for zi in z.infolist() if zi.filename.lower().endswith(".csv")]
        if not members:
            return 0
        total = sum(zi.file_size for zi in members)
        with z.open(members[0]) as fh:
            t = io.TextIOWrapper(fh, encoding="utf-8-sig")
            t.readline()                      # header
            lens = [len(t.readline()) for _ in range(200)]
        lens = [n for n in lens if n > 0]
        avg = (sum(lens) / len(lens)) if lens else 1000
    return int(total / max(avg, 1))


def to_out_row(r: dict, source_file: str) -> dict:
    """One bulk-download assistance transaction -> one output row.

    CARRIES THE TRANSACTION IDENTITY. Added 2026-08-29, and here is what its
    absence cost.

    `faads_transactions_all_agencies.csv` was recorded in
    `docs/GRAIN_AUDIT.md` as holding **179,259 literal duplicate rows of
    2,769,748 (6.5%)**, with the note that "the pre-2008 assistance pull has no
    transaction key at all, so nothing in the pipeline can notice a page
    fetched twice". Measured 2026-08-29 by hashing every row:

      * **174,348 of the 179,259 - 97% - come from ONE staged object,
        `ed_fy2007_archive.zip`**, and 174,957 of the surplus rows are FY2007.
        A page fetched twice does not concentrate like that in one agency-year
        while leaving 40 other agency-years almost clean.
      * Every one of the 179,259 carries an `award_id_fain`.
      * The staged zip carries **`assistance_transaction_unique_key` and
        `modification_number` among its 112 columns**, and this function took
        neither.

    So these are almost certainly distinct assistance TRANSACTIONS on the same
    FAIN - the same shape proved exactly for the prime contracting archive in
    `code/430_restore_prime_transaction_key.py`, where 80,778 apparent
    duplicates resolved to 80,778 distinct FPDS transactions and the count went
    to zero without deleting a row or a dollar.

    Taking the key here means the next `build` can state a grain and validate a
    key instead of shipping a table a buyer is told not to aggregate. It does
    NOT retro-fix the file on disk: that needs a re-extract of the staged zips
    (`py -3 code/30_funding_pre2008.py build`), which is a full rebuild of a
    2.77M-row shipped table and is queued for an owner rather than run at the
    end of a session. Until then the duplication remains DIAGNOSED, not
    repaired, and `review/OWNER_DECISION_QUEUE.md` says so.
    """
    obl = r.get("federal_action_obligation") or ""
    try:
        obl = f"{float(obl):.2f}"
    except (TypeError, ValueError):
        obl = ""
    return {
        "fiscal_year": r.get("action_date_fiscal_year", ""),
        "cfda_program": r.get("cfda_number", ""),
        "agency": r.get("awarding_agency_name", ""),
        "recipient_name": r.get("recipient_name", ""),
        "recipient_type": r.get("business_types_code", ""),
        "recipient_city": r.get("recipient_city_name", ""),
        "recipient_state": r.get("recipient_state_code", ""),
        "recipient_zip": r.get("recipient_zip_code", ""),
        "recipient_duns": r.get("recipient_duns", ""),
        "obligated_usd": obl,
        "assistance_type": r.get("assistance_type_code", ""),
        "action_date": r.get("action_date", ""),
        "source_url": r.get("usaspending_permalink", ""),
        "fetched_date": FETCHED,
        "tribe_id": "",                       # BLANK ALWAYS — tier C, no matching
        "recipient_uei": r.get("recipient_uei", ""),
        "recipient_type_description": r.get("business_types_description", ""),
        "cfda_title": r.get("cfda_title", ""),
        "assistance_type_description": r.get("assistance_type_description", ""),
        "awarding_sub_agency": r.get("awarding_sub_agency_name", ""),
        "award_id_fain": r.get("award_id_fain", ""),
        "record_type": r.get("record_type_code", ""),
        "api_endpoint": API,
        "source_file": source_file,
        # The transaction identity. See the docstring: without it two distinct
        # assistance transactions on one FAIN become one indistinguishable row,
        # and 179,259 rows were miscounted as duplicates because of it.
        "assistance_transaction_unique_key":
            r.get("assistance_transaction_unique_key", ""),
        "modification_number": r.get("modification_number", ""),
    }


def _blank(v) -> bool:
    return v is None or str(v).strip() == ""


def stage_build() -> None:
    """Interior rows (already built) + every staged agency zip -> combined file."""
    out_path = os.path.join(CLEAN, "faads_transactions_all_agencies.csv")
    cov_path = os.path.join(CLEAN, "faads_identifier_coverage_by_agency_year.csv")
    prior = os.path.join(CLEAN, "faads_transactions.csv")

    # agency -> fy -> counters, computed over the FULL retrieved universe
    cov = {}

    def bump(agency, fy, r_duns, r_uei, biz, rectype, obl):
        d = cov.setdefault((agency, fy), {
            "n_rows": 0, "n_duns": 0, "n_uei": 0, "n_tribal": 0,
            "n_tribal_duns": 0, "n_record_type_1": 0, "n_biztype_X": 0,
            "obligated_usd": 0.0, "obligated_usd_tribal": 0.0})
        d["n_rows"] += 1
        # 'X' = OTHER. A high share means the agency has stopped using the
        # substantive business-type codes that year, which silently disables the
        # tribal flag. Without this column a collapse in n_tribal_flagged reads
        # as a funding change when it is a coding change.
        if (biz or "").strip().upper() == "X":
            d["n_biztype_X"] += 1
        has_duns = not _blank(r_duns)
        if has_duns:
            d["n_duns"] += 1
        if not _blank(r_uei):
            d["n_uei"] += 1
        if "I" in (biz or "").upper():
            d["n_tribal"] += 1
            if has_duns:
                d["n_tribal_duns"] += 1
            try:
                d["obligated_usd_tribal"] += float(obl)
            except (TypeError, ValueError):
                pass
        if str(rectype).strip() == "1":
            d["n_record_type_1"] += 1
        try:
            d["obligated_usd"] += float(obl)
        except (TypeError, ValueError):
            pass

    written = 0
    per_agency_written = {}
    os.makedirs(CLEAN, exist_ok=True)
    tmp_out = out_path + ".tmp"
    _out_cols = _carry_live_columns(out_path, OUT_COLS)
    with open(tmp_out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=_out_cols, extrasaction="ignore",
                           restval="")
        w.writeheader()

        # 1. carry the prior Interior slice verbatim (same 24 columns already)
        if os.path.exists(prior):
            with open(prior, newline="", encoding="utf-8") as pf:
                rd = csv.DictReader(pf)
                if list(rd.fieldnames or []) not in [list(x) for x in PRIOR_SCHEMAS]:
                    raise SystemExit(
                        "prior file schema drift:" + chr(10)
                        + f" {rd.fieldnames}" + chr(10)
                        + " vs" + chr(10) + f" {OUT_COLS}")
                # WIDEN, NEVER NARROW. A column the prior shape does not have
                # is written BLANK and NAMED in the log; a column it does have
                # is carried through untouched. Blank means "the source object
                # we hold for these rows did not record it", never "there was
                # only one transaction" and never "this column went away".
                widened = [c for c in _out_cols if c not in (rd.fieldnames or [])]
                if widened:
                    log(f"prior Interior slice widened with blank {widened}")
                for row in rd:
                    for c in widened:
                        row[c] = ""
                    w.writerow(row)
                    written += 1
                    per_agency_written[row["agency"]] = per_agency_written.get(row["agency"], 0) + 1
                    bump(row["agency"], row["fiscal_year"], row["recipient_duns"],
                         row["recipient_uei"], row["recipient_type"],
                         row["record_type"], row["obligated_usd"])
            log(f"carried {written:,} rows from data/clean/faads_transactions.csv (Interior)")
            # Regression guard: the prior run's published Interior slice.
            # 60,661 transactions / $9,348,473,200.00 / 7,646 tribal-flagged rows
            # (docs/FAADS_FEASIBILITY_2026-08-05.md sec.6). Drift here means the
            # inherited file changed and every downstream number is suspect.
            di = sum(v["n_rows"] for (a, _), v in cov.items() if a == "Department of the Interior")
            dd = sum(v["obligated_usd"] for (a, _), v in cov.items() if a == "Department of the Interior")
            dt = sum(v["n_tribal"] for (a, _), v in cov.items() if a == "Department of the Interior")
            if (di, round(dd, 2), dt) != (60661, 9348473200.00, 7646):
                raise SystemExit(
                    f"REGRESSION: Interior slice is {di} rows / ${dd:,.2f} / {dt} tribal, "
                    f"expected 60,661 / $9,348,473,200.00 / 7,646")
            log("regression guard PASSED: Interior 60,661 rows / $9,348,473,200.00 / "
                "7,646 tribal-flagged")

        # 2. every staged agency zip (generated bulk jobs + archive files)
        st = load_state()
        staged = dict(st.get("jobs", {}))
        staged.update(st.get("archive", {}))
        # An agency-year must be counted from exactly ONE staged file. The two
        # retrieval routes can overlap (the archive supplies FY2007; a bulk job
        # asked for a range that includes it), and double counting an agency-year
        # would silently inflate both rows and dollars. Archive files are the
        # full 112-column originals, so they claim first.
        order = ([k for k in sorted(staged) if k.endswith("_archive")]
                 + [k for k in sorted(staged) if not k.endswith("_archive")])
        claimed = {}
        for key in order:
            meta = staged[key]
            path = os.path.join(AGENCY_DIR, key + ".zip")
            if not os.path.exists(path):
                log(f"WARN staged job {key} has no zip on disk; skipped")
                continue
            # archive entries carry no row count; estimate it from the zip
            total = int(meta.get("total_rows") or 0) or estimate_rows(path)
            tribal_only = total > TRIBAL_ONLY_ROW_THRESHOLD
            n_in = n_out = n_dupe = 0
            for r in iter_zip_rows(path):
                n_in += 1
                fy = r.get("action_date_fiscal_year", "")
                if fy and not (str(FY_FIRST) <= str(fy) <= str(FY_LAST)):
                    continue          # defensive: keep the declared window only
                agency = r.get("awarding_agency_name", "")
                owner = claimed.setdefault((agency, fy), key)
                if owner != key:
                    n_dupe += 1
                    continue          # this agency-year belongs to another file
                bump(agency, fy, r.get("recipient_duns"), r.get("recipient_uei"),
                     r.get("business_types_code"), r.get("record_type_code"),
                     r.get("federal_action_obligation"))
                if tribal_only and "I" not in (r.get("business_types_code") or "").upper():
                    continue
                w.writerow(to_out_row(r, key + ".zip"))
                n_out += 1
                written += 1
                per_agency_written[agency] = per_agency_written.get(agency, 0) + 1
            log(f"built {key}: read {n_in:,} rows, wrote {n_out:,}"
                + (f", skipped {n_dupe:,} already claimed by another file" if n_dupe else "")
                + (" (TRIBAL-FLAGGED ONLY — see build log)" if tribal_only else ""))
    # Windows will refuse the rename while a scanner or another reader holds the
    # target open. Retry rather than lose a completed build.
    for attempt in range(12):
        try:
            os.replace(tmp_out, out_path)
            break
        except PermissionError as e:
            if attempt == 11:
                raise
            log(f"rename blocked ({e.winerror}); retrying in 10s")
            time.sleep(10)
    log(f"WROTE {out_path} — {written:,} rows")
    for a in sorted(per_agency_written):
        log(f"   {a}: {per_agency_written[a]:,} rows")

    # coverage table
    with open(cov_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["agency", "fiscal_year", "n_rows", "pct_with_duns",
                    "pct_with_uei", "n_tribal_flagged",
                    "pct_with_duns_tribal_rows_only", "pct_business_type_other_X",
                    "n_record_type_1", "obligated_usd",
                    "obligated_usd_tribal_flagged"])
        for (agency, fy) in sorted(cov):
            d = cov[(agency, fy)]
            n = d["n_rows"] or 1
            nt = d["n_tribal"]
            w.writerow([agency, fy, d["n_rows"],
                        round(100.0 * d["n_duns"] / n, 1),
                        round(100.0 * d["n_uei"] / n, 1),
                        nt,
                        round(100.0 * d["n_tribal_duns"] / nt, 1) if nt else "",
                        round(100.0 * d["n_biztype_X"] / n, 1),
                        d["n_record_type_1"],
                        round(d["obligated_usd"], 2),
                        round(d["obligated_usd_tribal"], 2)])
    log(f"WROTE {cov_path} — {len(cov)} agency-year rows")
    return out_path, cov_path


# ------------------------------------------------------------- manifest stage

def stage_manifest() -> None:
    st = load_state()
    staged = dict(st.get("jobs", {}))
    staged.update(st.get("archive", {}))
    if not staged:
        log("manifest: no new agency jobs staged; manifest unchanged")
        return
    with open(MANIFEST, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
        cols = rows[0].keys() if rows else None
    have = {r["local_file"] for r in rows}
    added = 0
    for key in sorted(staged):
        meta = staged[key]
        lf = meta.get("_local_file", "").replace("data/raw/external/faads/", "")
        if not lf or lf in have:
            continue
        s, e = meta.get("_date_range", ["", ""])
        if meta.get("_source"):          # static Award Data Archive file
            src = meta["_source"]
            desc = (f"USAspending Award Data Archive, pre-generated assistance "
                    f"prime-transaction file for {meta.get('_agency_name')}, "
                    f"{os.path.basename(src)}. Full 112-column assistance schema.")
        else:                            # generated bulk_download job
            src = API
            desc = (f"USAspending assistance prime transactions, awarding "
                    f"toptier={meta.get('_agency_name')}, prime_award_types 02-11, "
                    f"date_type=action_date, date_range {s}..{e}. "
                    f"20-column subset of the 112-column assistance schema.")
        rows.append({
            "local_file": lf,
            "source_url": src,
            "description": desc,
            "bytes": meta.get("_bytes", ""),
            "rows": meta.get("total_rows", ""),
            "sha256": meta.get("_sha256", ""),
            "retrieved_date": meta.get("_retrieved", FETCHED),
        })
        added += 1
    with open(MANIFEST, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(cols))
        w.writeheader()
        w.writerows(rows)
    log(f"manifest: +{added} rows -> {MANIFEST}")


def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    only = None
    sleep_between = 90
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
    if "--sleep" in sys.argv:
        sleep_between = int(sys.argv[sys.argv.index("--sleep") + 1])
    if stage in ("pull", "all"):
        stage_pull(only, sleep_between)
    if stage == "pull_archive":
        stage_pull_archive(only, sleep_between)
    if stage in ("build", "coverage", "all"):
        stage_build()
    if stage in ("manifest", "all"):
        stage_manifest()


if __name__ == "__main__":
    main()
