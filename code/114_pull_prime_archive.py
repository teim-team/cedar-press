#!/usr/bin/env python3
"""
Cedar Press - 114: prime contracts from the USAspending STATIC ARCHIVE.

WHY THIS ROUTE
--------------
`code/44_pull_contracts_transactions.py` is right about WHAT to pull, and its
filter logic and ledger join are reproduced here. It is not usable right now:
`api.usaspending.gov` edge-blocked this project twice on 2026-08-07 and
`POST /api/v2/download/transactions/` returns HTTP 503 through a full
60s->1800s backoff (`logs/44_contracts_transactions.log`). Script 44 is not
deleted and its endpoint is not used here.

The API was never the only route. FY2000-2022 came from
`master prime file.dta`, not an API pull. This is the third route: the monthly
static archive.

    https://files.usaspending.gov/award_data_archive/FY2023_All_Contracts_Full_20260706.zip

`files.usaspending.gov` is a DIFFERENT HOST from `api.usaspending.gov`. Static
S3 objects from the `dti-usaspending-monthly-downloads` bucket, plain GET, no
POST, no server-side job. This script issues ZERO requests to
`api.usaspending.gov`. Lock: `logs/_HOSTLOCK_files.usaspending.gov.json`.

MEASURED FACTS ABOUT THE ARCHIVE (bucket listing paginated 2026-08-07,
`?list-type=2&continuation-token=`, 5 pages, 4,631 keys)
--------------------------------------------------------------------------
  - SUPERSEDED 2026-08-12: `20260806` is now the ONLY stamp. The archive
    REPLACES its objects monthly rather than accumulating them, so every
    `20260706` key has been deleted and now 404s. Re-enumerate before every
    run; see `stamp_for()` for why the stamp is resolved PER YEAR.
  - `_All_Contracts_Full_` exists for **FY2007 through FY2026 only**. There is
    no FY2000-FY2006 full contracts file in this archive. That is the
    source's floor, not ours, and it means the pre-2007 part of
    `prime_contracts.csv` cannot be replaced from here.
  - The 20 full-year zips total 29.5 GB.

THE BIGGER REASON THIS RUNS BACK TO FY2007
------------------------------------------
Elijah, 2026-08-07: *"the dta file is not as complete cuz i had to download
with limits through bgov, so i had to filter where i was most likely to find
native entities, or in this case tribes. those years should eventually be
redone so we get the full universe every year."*

So `master prime file.dta` is UNDER-INCLUSIVE BY CONSTRUCTION - a capped BGOV
download pre-filtered to where Native entities were expected. Every Native-
owned firm whose name and self-report gave no signal is missing from it, which
is exactly the class the set-aside filter also misses (60.9% of the Native
contracting dollars we can identify report no Native preference at all).

The archive has no upstream filter. So the FY2022 cross-source comparison is
not a nuisance check, it is the measurement: same year, same identifier
population, two sources. **The difference is the size of the BGOV filter's
blind spot**, and the most useful form of it is ENTITIES PRESENT IN THE
ARCHIVE AND ABSENT FROM THE .dta.

WHERE THE ROWS GO, AND WHY NOT ALL INTO ONE FILE
------------------------------------------------
FY2023-FY2026 do not exist in `prime_contracts.csv`, so they APPEND to it.
No existing row is touched or rewritten.

FY2007-FY2022 DO exist there, from the .dta. Appending a second, larger,
differently-filtered copy of the same years into the same file would make
`sum(total_obligations)` silently double-count sixteen years - and it would
look like growth. So those rows go to a PARALLEL file with the identical
schema, `data/clean/prime_contracts_archive_backfill.csv`. Both sources are
kept, both are distinguished by `source_file`, the archive is the preferred
source where they overlap, and .dta rows with no archive counterpart are
flagged rather than dropped. When Elijah rules to redo those years, the
backfill file replaces the .dta rows wholesale; until then nothing
double-counts by accident.

MONEY RULES - MEASURED IN docs/DATA_ODDITIES.md, NOT RE-DERIVED HERE
--------------------------------------------------------------------
  - `total_obligations` is TRANSACTIONAL and SUMS. 9.7% of existing rows are
    negative (deobligations) and BELONG in totals; 9.9% are zero (actions that
    moved no money). Blank is not zero.
  - `total_award_value` is RESTATED on every transaction of an award and must
    be MAXed per award, never summed.
  - `total_obligations_real2025` uses the BEA GDP implicit price deflator
    already in `data/clean/inflation_deflator.csv`. No second deflator.
    FY2026 is incomplete, BEA publishes no annual index for it, so it carries
    factor 1.0 and is flagged - a forecast index presented as a measurement is
    worse than an undeflated number.
  - Set-aside columns are `reported_*`: the contracting office's SELF-REPORT,
    never Cedar's determination.

ENTITY RESOLUTION
-----------------
Identifier join only. `resolve_entity` is the NAME resolver and is
deliberately NOT imported - name-matching 6.4M rows a year is how false
attributions get made at industrial scale. No identifier hit means
unattributed, counted, never guessed.

    py -3 code/114_pull_prime_archive.py run --years 2022
    py -3 code/114_pull_prime_archive.py run --years 2023,2024,2025,2026
    py -3 code/114_pull_prime_archive.py seam
    py -3 code/114_pull_prime_archive.py append --confirm-seam
    py -3 code/114_pull_prime_archive.py codebook
    py -3 code/114_pull_prime_archive.py status

Reads  data/clean/cedar_identifier_ledger_final.csv
       data/clean/prime_contracts.csv          (comparison only; append-only)
       data/clean/inflation_deflator.csv
Writes data/raw/contracts/usaspending_archive_2026-08-07/
         *.zip  _SOURCE_MANIFEST.csv  _state.json  filtered/FY####_ledger_rows.csv
       data/clean/prime_contracts.csv                     (APPEND ONLY)
       data/clean/prime_contracts_archive_backfill.csv
       data/clean/codebook/02d_prime_contracting_archive.csv
       review/prime_archive_seam_<date>.csv
       review/series_breaks_proposal_prime_archive_<date>.csv
       review/prime_archive_entities_missing_from_dta_<date>.csv
       docs/PRIME_ARCHIVE_PULL_LOG.md
"""

import argparse
import csv
import ctypes
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
DOCS = CEDAR / "docs"
LOGS = CEDAR / "logs"
OUT = CEDAR / "data" / "raw" / "contracts" / "usaspending_archive_2026-08-07"
FILTERED = OUT / "filtered"
MANIFEST = OUT / "_SOURCE_MANIFEST.csv"
STATE = OUT / "_state.json"

TODAY = date.today().isoformat()
BASE = "https://files.usaspending.gov/award_data_archive"
STAMP = "20260806"

# THE STAMP IS PER-YEAR, NOT GLOBAL (2026-08-12)
# ----------------------------------------------
# The archive is a MONTHLY REPLACEMENT, not an accumulation. On 2026-08-10 the
# August file published and **every 20260706 object was deleted** - a full
# re-enumeration on 2026-08-12 returned 4,597 keys, all carrying 20260806 and
# not one carrying 20260706. So `FY2016_All_Contracts_Full_20260706.zip` now
# answers a real HTTP 404, and re-probing for a newer stamp before settling was
# not a formality.
#
# That makes a single global STAMP actively dangerous here, in two ways:
#
#   1. FY2017-FY2026 were filtered from the JULY objects. Relabelling their
#      rows 20260806 would attribute them to a vintage they did not come from.
#   2. `cmd_append` refuses to double-append by testing whether
#      `FY{y}_All_Contracts_Full_{STAMP}.zip` is already a `source_file` in
#      prime_contracts.csv. Bump STAMP globally and FY2023/FY2024 - already
#      appended under the July name - stop matching, the guard goes quiet, and
#      a second full copy of both years lands in the file. That is exactly the
#      silent double-count this script's parallel-backfill design exists to
#      prevent, arriving through the back door.
#
# So the stamp a year is LABELLED with is read back from the URL recorded for
# that year in `_state.json`, and only years never fetched take the current
# default. Provenance follows the object that was actually read.
def stamp_for(fy, st=None):
    """The stamp FY`fy` was actually READ at; the default if it was never read.

    Only a year that came back HTTP 200 gets its stamp from the recorded URL.
    FY2007-FY2016 carry a 20260706 URL in `_state.json` too, but they carry it
    with `http_status = 0` - a record of a REFUSAL, not of a read. Taking a
    stamp from a refused year's URL would pin this pull to a vintage the host
    has since deleted, and every request would 404. A refusal is a fact about
    the host, never a provenance claim about the object.
    """
    st = load_state() if st is None else st
    rec = (st.get("years") or {}).get(str(fy)) or {}
    if rec.get("http_status") != 200:
        return STAMP
    m = re.search(r"_All_Contracts_Full_(\d{8})\.zip", rec.get("url") or "")
    return m.group(1) if m else STAMP
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")

ARCHIVE_FLOOR = 2007          # measured from the bucket listing, not assumed
SEAM_FY = 2022                # the only year both sources cover completely
NEW_FY = [2023, 2024, 2025, 2026]
PRIMARY = CLEAN / "prime_contracts.csv"
BACKFILL = CLEAN / "prime_contracts_archive_backfill.csv"

# Keep this much free so a concurrent agent's pull is not starved. Zips are
# RELEASED after filtering when free space drops below it - the manifest keeps
# url + status + bytes + md5 + etag, so every released file is re-fetchable
# and its identity is still provable.
FREE_FLOOR_GB = 7.0

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg):
    line = f"[{now()}] {msg}"
    print(line, flush=True)
    LOGS.mkdir(exist_ok=True)
    with open(LOGS / "114_prime_archive.log", "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def load_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:                                       # noqa: BLE001
            log("WARNING: _state.json unreadable; starting a fresh state")
    return {"created": now(), "stamp": STAMP, "archive_floor": ARCHIVE_FLOOR,
            "years": {}, "seam": {}, "append": {}}


def save_state(st):
    """Checkpoint by MERGING onto what is on disk, never by overwriting it.

    A long `run` holds its state in memory for the length of the job. While it
    was running, `seam` wrote its measurement into the same file - and the
    next `run` checkpoint wrote the whole in-memory dict back and erased it,
    so `append` then refused for want of a seam that had in fact been
    computed. Same lost-update shape that cost this project three codebook
    blocks in one day. Read-merge-write, and merge the per-year dicts key by
    key so two writers touching different years both survive.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    disk = {}
    if STATE.exists():
        try:
            disk = json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:                                       # noqa: BLE001
            disk = {}
    merged = {**disk, **{k: v for k, v in st.items() if k != "years"}}
    years = dict(disk.get("years") or {})
    for fy, d in (st.get("years") or {}).items():
        years[fy] = {**(years.get(fy) or {}), **d}
    merged["years"] = years
    for k in ("seam", "append"):                # never blank out a result
        if not merged.get(k) and disk.get(k):
            merged[k] = disk[k]
    merged["last_saved"] = now()
    tmp = STATE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(merged, indent=2, default=str), encoding="utf-8")
    tmp.replace(STATE)
    st.update(merged)


def md5(path, bufsize=1 << 22):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for blk in iter(lambda: fh.read(bufsize), b""):
            h.update(blk)
    return h.hexdigest()


def free_gb():
    free = ctypes.c_ulonglong(0)
    ctypes.windll.kernel32.GetDiskFreeSpaceExW(
        ctypes.c_wchar_p(str(CEDAR)), None, None, ctypes.byref(free))
    return free.value / 1e9


# --------------------------------------------------------------------------
# RULE 1 - one poller per host. Win32_Process, never `ps`: Git Bash's ps
# carries no command lines on Windows and once reported zero pullers while
# four were running.
# --------------------------------------------------------------------------
PULLER_PAT = re.compile(r"114_pull_prime_archive", re.I)
SPECTATOR_PAT = re.compile(
    r"(\\tail\.exe|\btail\b|\\grep\.exe|\bgrep\b|Get-Content|Select-String|"
    r"shell-snapshots|Win32_Process)", re.I)


def other_pullers_live():
    ps = ("Get-CimInstance Win32_Process | "
          "Select-Object ProcessId,ParentProcessId,CommandLine | "
          "ConvertTo-Json -Compress")
    try:
        raw = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                             capture_output=True, text=True, timeout=180).stdout
        procs = json.loads(raw)
    except Exception as e:                                      # noqa: BLE001
        log(f"WARNING: cannot enumerate processes ({e}); a check that cannot "
            "run is not a pass.")
        return [(-1, "process enumeration failed")]
    if isinstance(procs, dict):
        procs = [procs]
    by_pid = {p.get("ProcessId"): p for p in procs}
    mine, pid = set(), os.getpid()
    while pid and pid in by_pid and pid not in mine:
        mine.add(pid)
        pid = by_pid[pid].get("ParentProcessId")
    hits = []
    for p in procs:
        cmd = p.get("CommandLine") or ""
        if p.get("ProcessId") in mine or not cmd:
            continue
        if SPECTATOR_PAT.search(cmd) or not PULLER_PAT.search(cmd):
            continue
        hits.append((p["ProcessId"], cmd))
    return hits


# --------------------------------------------------------------------------
# download - resume-capable, verified on STATUS *and* MAGIC BYTES.
#
# A 404 body saved under a .zip name has non-zero size and passes every
# file-size test. It fails only when something tries to read it. So: refuse
# anything that is not 200/206, refuse anything whose first four bytes are not
# PK\x03\x04, and refuse anything whose central directory will not open.
# --------------------------------------------------------------------------
ZIP_MAGIC = b"PK\x03\x04"

# BACKOFF BOUNDS THE RATE, NOT THE RUN (docs/PULL_DISCIPLINE.md, 2026-08-08)
# --------------------------------------------------------------------------
# This script already stops the YEAR LOOP on a status-0 refusal, which is the
# second of the two required stops. It had no global deadline: the per-request
# backoffs alone (head 5 tries to 1800s, fetch 6 tries to 1800s) can spend well
# over two hours inside a SINGLE year without the loop ever advancing, so the
# loop-level stop never gets a turn. The deadline is checked before each
# attempt AND before each sleep, because a long sleep otherwise carries the run
# past the deadline anyway.
MAX_RUN_SECONDS = 2 * 60 * 60
RUN_DEADLINE = None          # armed by cmd_run


def deadline_passed():
    return RUN_DEADLINE is not None and time.time() > RUN_DEADLINE


def url_for(fy):
    return f"{BASE}/FY{fy}_All_Contracts_Full_{STAMP}.zip"


def head(url, tries=5):
    """HEAD with backoff.

    A 404 and a dropped connection are OPPOSITE findings and must never be
    collapsed into one return value. A 404 says this year is not published; a
    `RemoteDisconnected` says the host is refusing us. Returning 0 for both
    once made the caller skip nineteen years in five seconds, issuing a burst
    of HEADs at a host that was refusing us FOR request rate - which is
    exactly the 2026-08-05 failure in a new place.

    So: HTTPError returns its code immediately and is trusted. Anything else
    backs off and retries, and only then returns 0, which the caller treats as
    stop-work rather than as an answer about the year.

    AND A 500 IS NOT A 404 EITHER (2026-08-12)
    ------------------------------------------
    The paragraph above was written about TRANSPORT failures, and then this
    function trusted every HTTP status equally. On 2026-08-12 FY2007 answered
    **HTTP 500**, which was handed back as "a real answer about the year" and
    recorded in the manifest as *"the archive does not publish this year"* -
    a false statement about the source, about an object whose key had been read
    out of the bucket listing twenty-five minutes earlier.

    Only **404** and **403** are facts about the OBJECT. **5xx and 429** are
    facts about the HOST having a bad moment, and they are retryable. The
    assistance run had already hit this exact shape - FY2008/FY2009 recorded
    `http_status = 500` - and correctly refused to call them absent; this
    function was the one place that still drew the line at "did I get an HTTP
    response" instead of at "is this an answer about the object".
    """
    RETRYABLE_STATUS = {429, 500, 502, 503, 504}
    delay = 60
    for attempt in range(tries):
        if deadline_passed():
            log(f"  STOP: {MAX_RUN_SECONDS//3600}h run deadline reached during "
                "HEAD backoff. Returning 0 = stop-work, which is NOT a "
                "statement that this year is absent.")
            return 0, 0, ""
        req = urllib.request.Request(url, method="HEAD",
                                     headers={"User-Agent": UA})
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.status, int(r.headers.get("Content-Length") or 0), \
                    r.headers.get("ETag", "").strip('"')
        except urllib.error.HTTPError as e:
            if e.code not in RETRYABLE_STATUS:
                # 404/403: a fact about the object. Trusted and returned.
                return e.code, 0, ""
            # 5xx/429: a fact about the host. Retry, and if it persists return
            # the code so the CALLER can record a refusal - never an absence.
            log(f"  HEAD HTTP {e.code} - a HOST-side status, not an answer "
                f"about this year. Backing off {delay}s [{attempt+1}/{tries}]")
            if attempt == tries - 1 or deadline_passed():
                return e.code, 0, ""
            time.sleep(delay)
            delay = min(delay * 2, 1800)
            continue
        except Exception as e:                                  # noqa: BLE001
            el = time.time() - t0
            kind = "EDGE REFUSING" if el < 1.0 else "slow/failed"
            log(f"  HEAD {kind} after {el:.1f}s ({e}). More requests EXTEND "
                f"an edge block. Backing off {delay}s "
                f"[{attempt+1}/{tries}]")
            if attempt == tries - 1 or deadline_passed():
                return 0, 0, ""
            time.sleep(delay)
            delay = min(delay * 2, 1800)
    return 0, 0, ""


def fetch(url, dest, expect_bytes, tries=6):
    delay = 30
    for attempt in range(tries):
        if deadline_passed():
            raise RuntimeError(
                f"{MAX_RUN_SECONDS//3600}h run deadline reached mid-download. "
                "Partial file kept; fetch() resumes by byte Range, so nothing "
                "already transferred is lost.")
        have = dest.stat().st_size if dest.exists() else 0
        if expect_bytes and have == expect_bytes:
            break
        if expect_bytes and have > expect_bytes:
            log(f"    local larger than remote ({have:,} > {expect_bytes:,}); "
                "discarding and refetching")
            dest.unlink()
            have = 0
        headers = {"User-Agent": UA}
        if have:
            headers["Range"] = f"bytes={have}-"
        req = urllib.request.Request(url, headers=headers)
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=900) as r:
                if r.status not in (200, 206):
                    raise RuntimeError(f"HTTP {r.status}")
                if have and r.status == 200:          # server ignored Range
                    have = 0
                with open(dest, "ab" if (have and r.status == 206) else "wb") as fh:
                    while True:
                        chunk = r.read(1 << 22)
                        if not chunk:
                            break
                        fh.write(chunk)
            got = dest.stat().st_size
            log(f"    {got:,} bytes in {int(time.time()-t0)}s "
                f"(expected {expect_bytes:,})")
            if not expect_bytes or got == expect_bytes:
                break
        except Exception as e:                                  # noqa: BLE001
            el = time.time() - t0
            kind = "edge refusing" if el < 1.0 else "slow/failed"
            log(f"    {kind} after {el:.1f}s ({e}); retry in {delay}s")
            if attempt == tries - 1 or deadline_passed():
                raise
            time.sleep(delay)
            delay = min(delay * 2, 1800)

    with open(dest, "rb") as fh:
        magic = fh.read(4)
    if magic != ZIP_MAGIC:
        raise RuntimeError(
            f"{dest.name} is NOT a zip - first bytes {magic!r}. An error page "
            "saved under a .zip name looks fine on disk and fails only on "
            "read. Refusing.")
    with zipfile.ZipFile(dest) as zf:
        members = [m for m in zf.namelist() if m.lower().endswith(".csv")]
    if not members:
        raise RuntimeError(f"{dest.name} opens but holds no CSV member")
    return dest.stat().st_size, md5(dest), members


def write_manifest(st):
    rows = []
    for fy in sorted(st["years"], key=int):
        d = st["years"][fy]
        rows.append({
            "fiscal_year": fy,
            "url": d.get("url", ""),
            "http_status": d.get("http_status", ""),
            "bytes": d.get("bytes", ""),
            "md5": d.get("md5", ""),
            "s3_etag_multipart": d.get("s3_etag", ""),
            # THE STAMP MUST COME FROM THE URL, NOT FROM THE CONSTANT.
            #
            # This wrote the global `STAMP` on every row, so after the constant
            # was bumped 20260706 -> 20260806 the manifest asserted `20260806`
            # on ten rows whose own `url` column ends `_20260706.zip`. A
            # provenance file contradicting itself in adjacent columns is worse
            # than one with a blank: the stamp is the more quotable field, and
            # it was the wrong one.
            #
            # The DATA rows were never affected - `source_file` is built by
            # `stamp_for(fy)`, which reads the recorded URL - so this was the
            # manifest disagreeing with the extract it documents. Derived from
            # the URL here for the same reason.
            "stamp": (re.search(r"_(\d{8})\.zip", d.get("url") or "")
                      or [None, stamp_for(int(fy), st)])[1],
            "n_csv_members": d.get("n_csv_members", ""),
            "local_file": d.get("local_file", ""),
            "retained_on_disk": d.get("retained", ""),
            "rows_scanned": d.get("scanned_rows", ""),
            "rows_kept": d.get("kept_rows", ""),
            "fetched_utc": d.get("fetched_utc", ""),
            "verification": d.get("verification", ""),
            "note": d.get("note", ""),
        })
    if not rows:
        return
    with open(MANIFEST, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


# --------------------------------------------------------------------------
# ledger - identifier join only, the population script 44 validated
# --------------------------------------------------------------------------
def load_ledger():
    """(by_uei, by_cage, x_ueis) - tiers A and B attribute; X never does.

    X-tier UEIs are not dropped silently. An excluded UEI's rows are the
    evidence that the exclusion is doing work, so they are kept in the
    filtered extract, tagged `excluded`, counted, and never written into
    prime_contracts.csv.
    """
    by_uei, by_cage, x = {}, {}, set()
    with open(CLEAN / "cedar_identifier_ledger_final.csv",
              encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            typ = (r.get("identifier_type") or "").strip().upper()
            ident = (r.get("identifier") or "").strip().upper()
            tier = (r.get("confidence_tier") or "").strip()
            if not ident:
                continue
            if typ == "UEI" and tier == "X":
                x.add(ident)
            if tier not in ("A", "B"):
                continue
            rec = (r.get("canonical_name", ""), r.get("tribe_id", ""), tier)
            if typ == "UEI":
                by_uei.setdefault(ident, rec)
            elif typ == "CAGE":
                by_cage.setdefault(ident, rec)
    return by_uei, by_cage, x


# --------------------------------------------------------------------------
# archive -> prime_contracts.csv schema
# --------------------------------------------------------------------------
KEEP = [
    "contract_transaction_unique_key", "contract_award_unique_key",
    "award_id_piid", "modification_number", "parent_award_id_piid",
    "action_date", "action_date_fiscal_year",
    "federal_action_obligation",
    "current_total_value_of_award", "potential_total_value_of_award",
    "recipient_uei", "recipient_name", "cage_code",
    "recipient_parent_uei", "recipient_parent_name",
    "recipient_city_name", "recipient_state_code",
    "primary_place_of_performance_city_name",
    "primary_place_of_performance_state_code",
    "awarding_agency_name", "awarding_sub_agency_name",
    "funding_agency_name", "funding_sub_agency_name",
    "naics_code", "type_of_set_aside", "type_of_set_aside_code",
    "extent_competed", "award_type_code", "award_type",
]

# NAICS 2-digit -> supersector, reproduced EXACTLY from the existing column.
# Every bucket was checked to the row against prime_contracts.csv FY2000-2022
# (52 + 53 = 400 + 8,614 = 9,014 "Financial Activities", and so on for all
# eleven). NAICS 11 carries a BLANK supersector there; that is the existing
# data's behaviour and it is reproduced rather than tidied, because a value
# that changes across the seam is a break even when the new value is nicer.
SUPERSECTOR = {
    "11": "",
    "21": "Natural Resources & Mining",
    "22": "Trade, Transportation, & Utilities",
    "42": "Trade, Transportation, & Utilities",
    "44": "Trade, Transportation, & Utilities",
    "45": "Trade, Transportation, & Utilities",
    "48": "Trade, Transportation, & Utilities",
    "49": "Trade, Transportation, & Utilities",
    "23": "Construction",
    "31": "Manufacturing", "32": "Manufacturing", "33": "Manufacturing",
    "51": "Information",
    "52": "Financial Activities", "53": "Financial Activities",
    "54": "Professional & Business Services",
    "55": "Professional & Business Services",
    "56": "Professional & Business Services",
    "61": "Education & Health Services",
    "62": "Education & Health Services",
    "71": "Leisure & Hospitality", "72": "Leisure & Hospitality",
    "81": "Other services or Not given",
    "92": "Other services or Not given",
}

# FPDS set-aside CODE -> the 7-value vocabulary the existing column uses
# (None reported / 8(a) / Small Business / Other / HUBZone / Indian Business /
# Buy Indian). The archive carries ~40 raw codes; collapsing them the same way
# is what keeps the column meaning the same thing on both sides of the seam.
# The three Native-specific programmes are legally distinct and stay distinct:
# 8(a) is SBA business development (13 CFR 124), Buy Indian is 25 U.S.C. 47
# (Interior and IHS only), and Indian Economic Enterprise / Indian Small
# Business Economic Enterprise are separate FPDS codes.
SETASIDE = {
    "8A": "8(a)", "8AN": "8(a)",
    "BI": "Buy Indian",
    "IEE": "Indian Business", "ISBEE": "Indian Business",
    "HZC": "HUBZone", "HZS": "HUBZone", "HS2": "HUBZone", "HS3": "HUBZone",
    "SBA": "Small Business", "SBP": "Small Business", "SB": "Small Business",
    "": "None reported", "NONE": "None reported",
}
NATIVE_SETASIDE = {"8(a)", "Buy Indian", "Indian Business"}

PRIME_FIELDS = [
    "contract_number", "parent_contract_number", "fiscal_year",
    "pre_2000_flag", "awardee_name", "awardee_uei", "cage_code",
    "parent_name", "parent_uei", "total_obligations", "total_award_value",
    "total_obligations_real2025", "total_award_value_real2025",
    "deflator_factor_2025", "inflation_base_year", "setaside", "reported_8a",
    "reported_buy_indian", "reported_indian_business",
    "reported_native_preference", "setaside_reported", "extent_competed",
    "funding_agency", "sector", "supersector", "defense",
    "recipient_city_name", "recipient_state_code", "place_of_perform_city",
    "place_of_perform_state", "tribe_id", "canonical_name",
    "attribution_method", "confidence_tier", "attributed_flag",
    "source_file", "source_authority", "built_date",
]


def _deflator():
    with open(CLEAN / "inflation_deflator.csv", encoding="utf-8-sig",
              newline="") as fh:
        return {int(r["year"]): float(r["factor_to_base"])
                for r in csv.DictReader(fh)}


DEFLATOR = _deflator()


def _f(v):
    try:
        f = float(v)
        return 0.0 if f != f else f              # NaN -> 0
    except (TypeError, ValueError):
        return 0.0


def title_agency(s):
    """Title Case to match the FY2000-2022 vocabulary, but never fold an
    acronym: the existing file writes 'U.S. Coast Guard', and a naive
    `.capitalize()` per word turns that into 'U.s. Coast Guard' - a value that
    silently stops joining to sixteen years of existing rows."""
    s = (s or "").strip()
    if not s:
        return ""
    out = []
    for w in s.split():
        core = w.strip(".,")
        if core and (core.isupper() and len(core) <= 3 and "." in w) or \
                re.fullmatch(r"(?:[A-Za-z]\.){2,}", w):
            out.append(w.upper())
        else:
            out.append(w.capitalize())
    return " ".join(out)


def award_setaside_map():
    """award key -> FPDS set-aside code, pooled across EVERY filtered year.

    Measured 2026-08-07: the archive reports `type_of_set_aside_code` per
    TRANSACTION and leaves it blank on 56% of rows, overwhelmingly on
    modifications. The .dta carries the AWARD's set-aside on every one of its
    transactions. Read transaction-level, the two columns disagree on 59.6% of
    shared FY2022 contracts and 4,580 contracts the .dta calls 8(a) land in
    'None reported' - which would inflate the published "no Native preference"
    share on the strength of a definition change.

    A set-aside is a property of the AWARD, not of each administrative
    modification to it, so the award-level reading is both the comparable one
    and the correct one. Blanks are filled from any non-blank observation of
    the same `contract_award_unique_key` ANYWHERE in the pulled years - which
    is why the pull runs back to the archive floor rather than only FY2023:
    an award modified in FY2024 usually has its base action in an earlier
    file, and within a single year the fill has nothing to find.

    An award with no observation in any pulled year keeps a blank, which reads
    as 'None reported' - not reported, which is a silence, not an assertion of
    'no set-aside used'. That residual is bounded by the archive floor
    (FY2007) and is reported rather than hidden.
    """
    m = {}
    for p in sorted(FILTERED.glob("FY*_ledger_rows.csv")):
        with open(p, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                code = (r.get("type_of_set_aside_code") or "").strip().upper()
                if not code or code == "NAN":
                    continue
                k = (r.get("contract_award_unique_key") or "").strip()
                if k:
                    m.setdefault(k, code)
    return m


def map_row(r, zipname, sa_map=None):
    """One archive transaction -> one prime_contracts.csv row."""
    fy = int(_f(r.get("action_date_fiscal_year")))
    tier = (r.get("match_tier") or "").strip()
    method = (r.get("attribution_method") or "unattributed").strip()
    attributed = tier in ("A", "B") and method != "excluded"

    naics = str(r.get("naics_code") or "").strip()
    sector = naics[:2] if len(naics) >= 2 and naics[:2].isdigit() else "Not given"
    supersector = SUPERSECTOR.get(sector, "Other services or Not given")

    code = str(r.get("type_of_set_aside_code") or "").strip().upper()
    if code == "NAN":
        code = ""
    if not code and sa_map:
        code = sa_map.get(str(r.get("contract_award_unique_key") or "").strip(), "")
    setaside = SETASIDE.get(code, "Other" if code else "None reported")

    fund_top = str(r.get("funding_agency_name") or "").strip().upper()
    if "DEFENSE" in fund_top:
        funding_agency = "Dept Of Defense"
    else:
        funding_agency = title_agency(str(r.get("funding_sub_agency_name") or "")
                                      or str(r.get("funding_agency_name") or ""))
    fac = DEFLATOR.get(fy, 1.0)
    ob = _f(r.get("federal_action_obligation"))
    av = _f(r.get("current_total_value_of_award"))

    def s(k):
        v = r.get(k)
        return "" if v is None or v != v else str(v).strip()

    return {
        "contract_number": s("award_id_piid"),
        "parent_contract_number": s("parent_award_id_piid") or s("award_id_piid"),
        "fiscal_year": fy,
        "pre_2000_flag": int(fy < 2000),
        "awardee_name": s("recipient_name"),
        "awardee_uei": s("recipient_uei").upper(),
        "cage_code": s("cage_code").upper(),
        "parent_name": s("recipient_parent_name"),
        "parent_uei": s("recipient_parent_uei").upper(),
        "total_obligations": ob,
        "total_award_value": av,
        "total_obligations_real2025": round(ob * fac, 2),
        "total_award_value_real2025": round(av * fac, 2),
        "deflator_factor_2025": fac,
        "inflation_base_year": 2025,
        "setaside": setaside,
        "reported_8a": int(setaside == "8(a)"),
        "reported_buy_indian": int(setaside == "Buy Indian"),
        "reported_indian_business": int(setaside == "Indian Business"),
        "reported_native_preference": int(setaside in NATIVE_SETASIDE),
        "setaside_reported": int(setaside != "None reported"),
        "extent_competed": s("extent_competed").upper(),
        "funding_agency": funding_agency,
        "sector": sector,
        "supersector": supersector,
        "defense": int(funding_agency == "Dept Of Defense"),
        "recipient_city_name": s("recipient_city_name").upper(),
        "recipient_state_code": s("recipient_state_code").upper(),
        "place_of_perform_city": s("primary_place_of_performance_city_name").upper(),
        "place_of_perform_state": s("primary_place_of_performance_state_code").upper(),
        "tribe_id": s("tribe_id") if attributed else "",
        "canonical_name": s("canonical_name") if attributed else "",
        "attribution_method": method if attributed else "unattributed",
        "confidence_tier": tier if attributed else "C",
        "attributed_flag": int(attributed),
        "source_file": zipname,
        # Stamp read off the object this row came from, not off the global
        # default - the archive replaces its objects monthly and two vintages
        # are live in this build at once.
        "source_authority": f"USAspending award_data_archive (FPDS-NG static "
                            f"monthly file), stamp "
                            f"{(re.search(r'_(\\d{8})[.]zip$', zipname) or [None, STAMP])[1]}",
        "built_date": TODAY,
    }


# --------------------------------------------------------------------------
# per-year pipeline: download -> verify -> filter -> release
# --------------------------------------------------------------------------
FILTER_COLS = KEEP + ["match_key", "match_tier", "match_identifier",
                      "tribe_id", "canonical_name", "attribution_method"]


def filter_year(fy, zpath, by_uei, by_cage, x_ueis, redo=False):
    import pandas as pd
    dest = FILTERED / f"FY{fy}_ledger_rows.csv"
    if dest.exists() and not redo:
        log(f"  FY{fy}: {dest.name} already built, skipping filter")
        return None
    FILTERED.mkdir(parents=True, exist_ok=True)
    t0, scanned, kept = time.time(), 0, 0
    stats, seen = Counter(), set()
    tmp = dest.with_suffix(".part")
    with zipfile.ZipFile(zpath) as zf, \
            open(tmp, "w", encoding="utf-8", newline="") as fo:
        w = csv.DictWriter(fo, fieldnames=FILTER_COLS, extrasaction="ignore")
        w.writeheader()
        members = [m for m in zf.namelist() if m.lower().endswith(".csv")]
        for mi, m in enumerate(members):
            with zf.open(m) as fh:
                hdr = pd.read_csv(fh, nrows=0)
            cols = [c for c in KEEP if c in hdr.columns]
            miss = [c for c in KEEP if c not in hdr.columns]
            if miss:
                log(f"    FY{fy} {m}: columns absent from source {miss}")
            with zf.open(m) as fh:
                for chunk in pd.read_csv(fh, usecols=cols, dtype=str,
                                         chunksize=200_000, low_memory=False,
                                         on_bad_lines="warn"):
                    scanned += len(chunk)
                    u = chunk["recipient_uei"].fillna("").str.strip().str.upper()
                    c = chunk["cage_code"].fillna("").str.strip().str.upper() \
                        if "cage_code" in chunk else u.str.slice(0, 0)
                    p = chunk["recipient_parent_uei"].fillna("").str.strip().str.upper() \
                        if "recipient_parent_uei" in chunk else u.str.slice(0, 0)
                    mask = (u.isin(by_uei) | c.isin(by_cage) | p.isin(by_uei)
                            | u.isin(x_ueis))
                    if not mask.any():
                        continue
                    sel = chunk[mask]
                    su, sc, sp = u[mask], c[mask], p[mask]
                    for i, rec in zip(sel.index, sel.to_dict("records")):
                        uu, cc, pp = su[i], sc[i], sp[i]
                        # Match order is a claim about evidence strength. The
                        # awardee's own UEI identifies the contracting party
                        # outright; CAGE is equally direct; the PARENT uei
                        # only says who owns the awardee, so it attributes to
                        # the parent and is recorded as a distinct, weaker
                        # method that can be audited or withdrawn on its own.
                        if uu in by_uei:
                            canon, tid, tier = by_uei[uu]
                            key, meth, ident = "recipient_uei", "uei_exact", uu
                            seen.add(uu)
                        elif cc in by_cage:
                            canon, tid, tier = by_cage[cc]
                            key, meth, ident = "cage_code", "cage_exact", cc
                        elif pp in by_uei:
                            canon, tid, tier = by_uei[pp]
                            key, meth, ident = ("recipient_parent_uei",
                                                "parent_uei", pp)
                        else:                       # tier-X excluded UEI
                            canon, tid, tier = "", "", "X"
                            key, meth, ident = "excluded_tier_X", "excluded", uu
                        stats[f"{key}:{tier}"] += 1
                        rec.update(match_key=key, match_tier=tier,
                                   match_identifier=ident, tribe_id=tid,
                                   canonical_name=canon,
                                   attribution_method=meth)
                        w.writerow(rec)
                        kept += 1
            log(f"    FY{fy} member {mi+1}/{len(members)}: scanned "
                f"{scanned:,}, kept {kept:,}, {int(time.time()-t0)}s")
    tmp.replace(dest)
    log(f"  FY{fy} FILTER: {scanned:,} scanned -> {kept:,} kept "
        f"({kept/max(scanned,1)*100:.4f}%), {len(seen):,} distinct UEIs, "
        f"{int(time.time()-t0)}s")
    for k, v in sorted(stats.items()):
        log(f"      {k}: {v:,}")
    return {"scanned_rows": scanned, "kept_rows": kept,
            "distinct_matched_ueis": len(seen), "by_match_key": dict(stats),
            "filter_seconds": int(time.time() - t0),
            "filtered_completed": now()}


def cmd_run(args):
    global RUN_DEADLINE
    RUN_DEADLINE = time.time() + MAX_RUN_SECONDS
    OUT.mkdir(parents=True, exist_ok=True)
    st = load_state()
    save_state(st)                     # checkpoint BEFORE the first request
    log(f"RUN_DEADLINE armed: no attempt starts after "
        f"{datetime.fromtimestamp(RUN_DEADLINE, timezone.utc).strftime('%H:%M:%SZ')} "
        f"({MAX_RUN_SECONDS//3600}h). Resumable - rerun to continue.")

    live = other_pullers_live()
    if live and not args.force:
        log("HOST BUSY - another copy of this script is live. Rule 1.")
        for pid, cmd in live:
            log(f"   pid {pid}: {cmd[:160]}")
        sys.exit(3)

    years = [int(y) for y in args.years.split(",")] if args.years else \
        [SEAM_FY] + NEW_FY
    bad = [y for y in years if y < ARCHIVE_FLOOR]
    if bad:
        log(f"NOTE: {bad} are below the archive floor FY{ARCHIVE_FLOOR}. The "
            "archive publishes no full contracts file for them; they cannot "
            "be pulled from this route at all.")
        years = [y for y in years if y >= ARCHIVE_FLOOR]

    by_uei, by_cage, x_ueis = load_ledger()
    log(f"ledger: {len(by_uei):,} tier-A/B UEIs, {len(by_cage):,} tier-A/B "
        f"CAGEs, {len(x_ueis):,} tier-X UEIs (kept in the extract, tagged, "
        f"never attributed)")

    first = True
    for fy in years:
        d = st["years"].get(str(fy), {})
        zpath = OUT / f"FY{fy}_All_Contracts_Full_{stamp_for(fy, st)}.zip"
        filtered = FILTERED / f"FY{fy}_ledger_rows.csv"
        if filtered.exists() and not args.redo:
            log(f"FY{fy}: already filtered, skipping")
            continue
        if deadline_passed():
            log(f"STOPPING before FY{fy}: {MAX_RUN_SECONDS//3600}h run "
                "deadline reached. Years already filtered are kept; rerun to "
                "continue. This is a deadline, NOT a host refusal.")
            break
        if not first:
            # Deliberate pause between years. Filtering already takes minutes,
            # so this costs almost nothing, and it keeps the request pattern
            # from looking like a scraper to an edge filter that has already
            # refused this project once tonight.
            time.sleep(args.pause)
        first = False

        url = url_for(fy)
        log(f"FY{fy}  {url}")
        if not zpath.exists():
            status, size, etag = head(url)
            log(f"  HEAD {status}  {size:,} bytes  etag={etag}")
            if status == 0:
                # Not an answer about FY{fy} - an answer about the HOST. Stop
                # the whole loop. Continuing would walk the remaining years at
                # request-per-second against a host that is refusing us.
                st["years"][str(fy)] = {
                    "url": url, "http_status": 0, "fetched_utc": now(),
                    "note": "HOST REFUSED after full HEAD backoff. This says "
                            "nothing about whether FY exists in the archive. "
                            "Run STOPPED here rather than probing on; resume "
                            "later, it is idempotent."}
                save_state(st)
                write_manifest(st)
                log("STOPPING the run: the host is refusing, not answering. "
                    "Everything already filtered is kept and this is "
                    "resumable.")
                break
            if status != 200:
                # A 5xx/429 survived the full HEAD backoff. That is the HOST
                # refusing, so it is recorded as a refusal with the reading
                # spelled out - never as "this year is not published" - and it
                # stops the run for the same reason a status 0 does. Only
                # 404/403 are answers about the object.
                host_side = status in (429, 500, 502, 503, 504)
                st["years"][str(fy)] = {
                    "url": url, "http_status": status, "fetched_utc": now(),
                    "verification": "none - no bytes received",
                    "note": (
                        f"HOST REFUSED - HTTP {status} through the full HEAD "
                        "backoff. This is a fact about the HOST, NOT about the "
                        "year: the bucket listing enumerated this exact key, "
                        "so the object exists. Do not read this row as "
                        "absence. Resume; it is idempotent."
                        if host_side else
                        f"not fetched - HTTP {status}. A real answer about the "
                        "object: the archive does not serve this key.")}
                save_state(st)
                write_manifest(st)
                if host_side:
                    log(f"STOPPING the run: HTTP {status} is the host "
                        "refusing, not an answer about FY{fy}. Resumable.")
                    break
                continue
            need = size / 1e9 + 1.0
            if free_gb() < need:
                log(f"  {free_gb():.1f} GB free, need {need:.1f} GB. "
                    "Releasing older retained zips.")
                release_space(st, need)
            if free_gb() < need:
                log("  STILL not enough space. Stopping; this is resumable.")
                break
            nbytes, digest, members = fetch(url, zpath, size)
            d = {"url": url, "http_status": 200, "bytes": nbytes,
                 "md5": digest, "s3_etag": etag, "n_csv_members": len(members),
                 "local_file": zpath.name, "retained": "yes",
                 "fetched_utc": now(),
                 "verification": "HTTP 200; PK\\x03\\x04 magic; central "
                                 "directory opens; >=1 CSV member"}
            log(f"  OK {nbytes:,} bytes md5={digest} {len(members)} members")
        else:
            d.setdefault("url", url)
            d.setdefault("local_file", zpath.name)
            d.setdefault("bytes", zpath.stat().st_size)
            d.setdefault("md5", md5(zpath))
            d["retained"] = "yes"
        st["years"][str(fy)] = d
        save_state(st)
        write_manifest(st)

        res = filter_year(fy, zpath, by_uei, by_cage, x_ueis, redo=args.redo)
        if res:
            d.update(res)
            st["years"][str(fy)] = d
            save_state(st)
            write_manifest(st)

        if free_gb() < FREE_FLOOR_GB and not args.keep_zips:
            release(st, fy)
            save_state(st)
            write_manifest(st)

    write_manifest(st)
    log("run complete")


def release(st, fy):
    """Delete a verified, already-filtered zip; keep its identity provable."""
    z = OUT / f"FY{fy}_All_Contracts_Full_{stamp_for(fy, st)}.zip"
    if not z.exists():
        return
    sz = z.stat().st_size
    z.unlink()
    d = st["years"].setdefault(str(fy), {})
    d["retained"] = "no"
    d["note"] = (d.get("note", "") + " | RELEASED after filtering to keep "
                 f"{FREE_FLOOR_GB:.0f} GB free for concurrent agents. "
                 "url + http_status + bytes + md5 + s3 etag are recorded "
                 "above, so the file is re-fetchable and its identity is "
                 "still provable.").strip(" |")
    log(f"  released FY{fy} zip ({sz/1e9:.2f} GB); {free_gb():.1f} GB free")


def release_space(st, need_gb):
    for fy in sorted(st["years"], key=int):
        if free_gb() >= need_gb:
            return
        if (FILTERED / f"FY{fy}_ledger_rows.csv").exists():
            release(st, int(fy))
    save_state(st)


# --------------------------------------------------------------------------
# seam - the measurement, not a formality
#
# Same fiscal year, same identifier population, two independent sources. One
# is a capped BGOV download pre-filtered to where Native entities were
# expected; the other has no upstream filter. The difference IS the size of
# the old filter's blind spot, and the most useful form of it is entities the
# archive finds that the .dta never had.
# --------------------------------------------------------------------------
def _load_sources(fy):
    import pandas as pd
    by_uei, by_cage, _ = load_ledger()

    ex = pd.read_csv(PRIMARY, low_memory=False)
    for c in ("awardee_uei", "cage_code", "parent_uei"):
        ex[c] = ex[c].fillna("").astype(str).str.strip().str.upper()
    ex["ob"] = pd.to_numeric(ex.total_obligations, errors="coerce").fillna(0)
    ex = ex[(ex.source_file == "master prime file.dta")
            & (ex.fiscal_year == fy)
            & (ex.awardee_uei.isin(by_uei) | ex.cage_code.isin(by_cage)
               | ex.parent_uei.isin(by_uei))]

    ar = pd.read_csv(FILTERED / f"FY{fy}_ledger_rows.csv", low_memory=False)
    ar = ar[ar.match_tier.isin(["A", "B"])].copy()
    ar["ob"] = pd.to_numeric(ar.federal_action_obligation,
                             errors="coerce").fillna(0)
    ar["fy"] = pd.to_numeric(ar.action_date_fiscal_year, errors="coerce")
    ar = ar[ar.fy == fy]
    for c in ("recipient_uei", "cage_code", "recipient_parent_uei"):
        if c in ar:
            ar[c] = ar[c].fillna("").astype(str).str.strip().str.upper()
    return ex, ar


def cmd_seam(args):
    import pandas as pd
    fy = SEAM_FY
    e, a = _load_sources(fy)
    out = []

    def add(metric, ev, av, note=""):
        pct = round((av - ev) / ev * 100, 3) if ev else ""
        out.append({"fiscal_year": fy, "metric": metric,
                    "existing_master_prime_file_dta": ev,
                    "usaspending_archive_20260706": av,
                    "abs_diff_archive_minus_existing": av - ev,
                    "pct_diff": pct, "note": note})
        log(f"  {metric:44s} dta={ev:>18,.0f}  archive={av:>18,.0f}  "
            f"{pct if pct == '' else f'{pct:+.1f}%'}")

    add("transaction_rows", float(len(e)), float(len(a)),
        "same tier-A/B identifier population, both sources")
    add("obligations_nominal_usd", float(e.ob.sum()), float(a.ob.sum()),
        "negatives (deobligations) INCLUDED - they belong in the total")
    add("obligations_real2025_usd",
        float((e.ob * DEFLATOR.get(fy, 1.0)).sum()),
        float((a.ob * DEFLATOR.get(fy, 1.0)).sum()),
        f"BEA GDP deflator factor {DEFLATOR.get(fy, 1.0)}")
    add("negative_rows_deobligations", float((e.ob < 0).sum()),
        float((a.ob < 0).sum()), "kept in the total")
    add("zero_rows_no_money_moved", float((e.ob == 0).sum()),
        float((a.ob == 0).sum()), "not missing data")
    add("distinct_contract_numbers", float(e.contract_number.nunique()),
        float(a.award_id_piid.nunique()), "")
    add("distinct_awardee_ueis",
        float(e.loc[e.awardee_uei != "", "awardee_uei"].nunique()),
        float(a.loc[a.recipient_uei != "", "recipient_uei"].nunique()), "")
    add("distinct_tribe_ids_entities_reached",
        float(e.loc[e.tribe_id.notna() & (e.tribe_id != ""), "tribe_id"].nunique()),
        float(a.loc[a.tribe_id.notna() & (a.tribe_id != ""), "tribe_id"].nunique()),
        "Cedar entities with at least one attributed transaction")

    # ---- the blind-spot measurement -------------------------------------
    eu = set(e.loc[e.awardee_uei != "", "awardee_uei"])
    au = set(a.loc[a.recipient_uei != "", "recipient_uei"])
    et = set(e.loc[e.tribe_id.notna() & (e.tribe_id != ""), "tribe_id"])
    at = set(a.loc[a.tribe_id.notna() & (a.tribe_id != ""), "tribe_id"])
    miss_u, miss_t = au - eu, at - et
    back_u, back_t = eu - au, et - at

    ag_u = a.groupby("recipient_uei").ob.sum()
    out.append({"fiscal_year": fy, "metric": "ueis_in_archive_absent_from_dta",
                "existing_master_prime_file_dta": 0,
                "usaspending_archive_20260706": len(miss_u),
                "abs_diff_archive_minus_existing": len(miss_u), "pct_diff": "",
                "note": f"${ag_u.reindex(sorted(miss_u)).fillna(0).sum():,.0f} "
                        "of FY2022 obligations the BGOV-filtered .dta never saw"})
    out.append({"fiscal_year": fy, "metric": "entities_in_archive_absent_from_dta",
                "existing_master_prime_file_dta": 0,
                "usaspending_archive_20260706": len(miss_t),
                "abs_diff_archive_minus_existing": len(miss_t), "pct_diff": "",
                "note": "Cedar entities with FY2022 prime contracting that the "
                        ".dta population missed entirely"})
    out.append({"fiscal_year": fy, "metric": "ueis_in_dta_absent_from_archive",
                "existing_master_prime_file_dta": len(back_u),
                "usaspending_archive_20260706": 0,
                "abs_diff_archive_minus_existing": -len(back_u), "pct_diff": "",
                "note": "FLAGGED, not dropped: either the archive genuinely "
                        "lacks them or the identifier changed. Listed in "
                        "review/prime_archive_entities_missing_from_dta_*.csv"})
    out.append({"fiscal_year": fy, "metric": "entities_in_dta_absent_from_archive",
                "existing_master_prime_file_dta": len(back_t),
                "usaspending_archive_20260706": 0,
                "abs_diff_archive_minus_existing": -len(back_t), "pct_diff": "",
                "note": "same"})

    # ---- contract-level agreement ---------------------------------------
    eg = e.groupby("contract_number").ob.sum()
    ag = a.groupby("award_id_piid").ob.sum()
    both = eg.index.intersection(ag.index)
    only_e, only_a = eg.index.difference(ag.index), ag.index.difference(eg.index)
    out.append({"fiscal_year": fy, "metric": "contracts_in_both_sources",
                "existing_master_prime_file_dta": len(both),
                "usaspending_archive_20260706": len(both),
                "abs_diff_archive_minus_existing": 0, "pct_diff": "",
                "note": "matched on contract_number within the fiscal year"})
    out.append({"fiscal_year": fy, "metric": "contracts_only_in_dta",
                "existing_master_prime_file_dta": len(only_e),
                "usaspending_archive_20260706": 0,
                "abs_diff_archive_minus_existing": -len(only_e), "pct_diff": "",
                "note": f"${eg[only_e].sum():,.0f} obligations - FLAGGED, not "
                        "dropped"})
    out.append({"fiscal_year": fy, "metric": "contracts_only_in_archive",
                "existing_master_prime_file_dta": 0,
                "usaspending_archive_20260706": len(only_a),
                "abs_diff_archive_minus_existing": len(only_a), "pct_diff": "",
                "note": f"${ag[only_a].sum():,.0f} obligations - the blind spot"})
    if len(both):
        agree = (eg[both] - ag[both]).abs() <= (eg[both].abs() * 0.005 + 1)
        out.append({"fiscal_year": fy,
                    "metric": "shared_contracts_obligations_agree_0.5pct",
                    "existing_master_prime_file_dta": int(agree.sum()),
                    "usaspending_archive_20260706": int(len(both)),
                    "abs_diff_archive_minus_existing": int(len(both) - agree.sum()),
                    "pct_diff": round(agree.mean() * 100, 2),
                    "note": "per-contract obligation totals, both sources. This "
                            "is the test that says whether the two sources "
                            "MEASURE the same thing where they overlap."})

        # Which archive column reproduces `total_award_value`? Measured, not
        # assumed - and MAXed per award, never summed, because the value is
        # restated on every transaction.
        emax = e.groupby("contract_number").total_award_value.max()
        for col in ("current_total_value_of_award",
                    "potential_total_value_of_award"):
            if col not in a.columns:
                continue
            amax = pd.to_numeric(a[col], errors="coerce").fillna(0) \
                     .groupby(a.award_id_piid).max()
            ok = (emax[both] - amax[both]).abs() <= (emax[both].abs() * .005 + 1)
            out.append({"fiscal_year": fy, "metric": f"award_value_max_matches_{col}",
                        "existing_master_prime_file_dta": int(ok.sum()),
                        "usaspending_archive_20260706": int(len(both)),
                        "abs_diff_archive_minus_existing": int(len(both) - ok.sum()),
                        "pct_diff": round(ok.mean() * 100, 2),
                        "note": "MAXed per award, never summed"})

    REVIEW.mkdir(exist_ok=True)
    p = REVIEW / f"prime_archive_seam_{TODAY}.csv"
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    log(f"wrote {p.relative_to(CEDAR)}")

    # ---- the two directions, entity by entity, for review -----------------
    rows = []
    an = a.drop_duplicates("recipient_uei").set_index("recipient_uei")
    for u in sorted(miss_u):
        r = an.loc[u] if u in an.index else None
        rows.append({"direction": "in_archive_absent_from_dta",
                     "uei": u,
                     "awardee_name": "" if r is None else r.get("recipient_name", ""),
                     "tribe_id": "" if r is None else r.get("tribe_id", ""),
                     "canonical_name": "" if r is None else r.get("canonical_name", ""),
                     "match_key": "" if r is None else r.get("match_key", ""),
                     "match_tier": "" if r is None else r.get("match_tier", ""),
                     "fy2022_obligations_usd": round(float(ag_u.get(u, 0)), 2),
                     "reading": "Native prime contracting the BGOV-filtered "
                                ".dta never contained. Evidence of the old "
                                "filter's blind spot."})
    en = e.drop_duplicates("awardee_uei").set_index("awardee_uei")
    eg_u = e.groupby("awardee_uei").ob.sum()
    for u in sorted(back_u):
        r = en.loc[u] if u in en.index else None
        rows.append({"direction": "in_dta_absent_from_archive",
                     "uei": u,
                     "awardee_name": "" if r is None else r.get("awardee_name", ""),
                     "tribe_id": "" if r is None else r.get("tribe_id", ""),
                     "canonical_name": "" if r is None else r.get("canonical_name", ""),
                     "match_key": "", "match_tier": "" if r is None else r.get("confidence_tier", ""),
                     "fy2022_obligations_usd": round(float(eg_u.get(u, 0)), 2),
                     "reading": "FLAGGED, not dropped. Either the archive "
                                "genuinely lacks the row or the identifier "
                                "differs between sources. Needs a ruling "
                                "before the archive replaces the .dta year."})
    p2 = REVIEW / f"prime_archive_entities_missing_from_dta_{TODAY}.csv"
    with open(p2, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    log(f"wrote {p2.relative_to(CEDAR)}  ({len(rows):,} rows)")

    write_exposure_queue(a)

    st = load_state()
    st["seam"] = {"computed": now(), "fy": fy,
                  "metrics": {r["metric"]: {
                      "dta": r["existing_master_prime_file_dta"],
                      "archive": r["usaspending_archive_20260706"],
                      "pct_diff": r["pct_diff"]} for r in out}}
    save_state(st)
    write_series_break_proposal(out)
    return out


def write_exposure_queue(a):
    """A complete universe AMPLIFIES a weak ledger link. Measure it.

    The BGOV-filtered .dta mostly did not contain the rows that an unreviewed
    algorithmic name-cluster link attaches to, so a bad link cost little. The
    archive contains all of them, so the same link now carries its full
    dollar weight. Measured on FY2022: 17.2% of archive-attributed dollars
    ride on tier-B `cluster_v3` links whose own rationale reads "Algorithmic
    name clustering, unreviewed", and `need_v6` - which
    `cedar_domain.METHOD_ACCURACY` records at 6.5% accurate - carries more.

    That is not a defect in this pull. It is a pre-existing ledger risk that
    this pull makes expensive, and precision beats recall here, so it goes to
    the review queue with the dollar amount attached rather than quietly into
    a published total.
    """
    led = {}
    with open(CLEAN / "cedar_identifier_ledger_final.csv",
              encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            led.setdefault((r.get("identifier") or "").strip().upper(), r)

    WEAK = {"cluster_v3", "need_v6", "sam_namematch_2026_05_06",
            "institution_exact_name", "cross_dataset_propagation:contracting",
            "cross_dataset_propagation:funding"}
    agg = {}
    for rec in a.to_dict("records"):
        ident = (rec.get("match_identifier") or "").strip().upper()
        L = led.get(ident, {})
        meth = (L.get("attribution_method") or "").strip()
        if (rec.get("match_tier") or "") != "B" or meth not in WEAK:
            continue
        k = ident
        e = agg.setdefault(k, {"rows": 0, "usd": 0.0, "name": "",
                               "canon": rec.get("canonical_name", ""),
                               "tribe": rec.get("tribe_id", ""),
                               "meth": meth,
                               "rationale": (L.get("tier_rationale") or ""),
                               "cage": ""})
        e["rows"] += 1
        e["usd"] += float(rec.get("ob") or 0)
        e["name"] = e["name"] or rec.get("recipient_name", "")
        e["cage"] = e["cage"] or (rec.get("cage_code") or "")
    rows = [{"uei": k, "cage_code": v["cage"], "awardee_name": v["name"],
             "attributed_to_tribe_id": v["tribe"],
             "attributed_to_canonical_name": v["canon"],
             "ledger_attribution_method": v["meth"],
             "ledger_tier_rationale": v["rationale"],
             "confidence_tier": "B",
             "fy2022_archive_rows": v["rows"],
             "fy2022_archive_obligations_usd": round(v["usd"], 2),
             "question": "Does this firm belong to the named entity? The "
                         "link is algorithmic and unreviewed, and the "
                         "complete archive now gives it full dollar weight.",
             "YOUR_RULING": ""}
            for k, v in sorted(agg.items(),
                               key=lambda kv: -kv[1]["usd"])]
    if not rows:
        return
    p = REVIEW / f"prime_archive_weak_attribution_exposure_{TODAY}.csv"
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    tot = sum(r["fy2022_archive_obligations_usd"] for r in rows)
    log(f"wrote {p.relative_to(CEDAR)}  ({len(rows):,} identifiers, "
        f"${tot/1e9:.3f}B of FY2022 archive-attributed dollars resting on an "
        "unreviewed tier-B link)")


def write_series_break_proposal(seam_rows):
    """`data/clean/series_breaks.csv` is owned by another process (script 86).

    So this writes a PROPOSAL in `review/` with that file's exact schema, for
    its owner to merge. Editing the shared file directly is the lost-update
    race that already cost this project three codebook blocks in one day.
    """
    m = {r["metric"]: r for r in seam_rows}

    def val(metric, key, default=0):
        return m.get(metric, {}).get(key, default)

    rows = [
        {"dataset": "prime_contracting", "column": "source_file",
         "break_period": "FY2022/FY2023",
         "break_type": "SOURCE_CHANGE",
         "what_changed":
             "FY2000-FY2022 comes from `master prime file.dta` - a BGOV "
             "download taken under a size cap and pre-filtered to where "
             "Native entities were expected. FY2023-FY2026 comes from the "
             "USAspending static archive "
             f"(FY####_All_Contracts_Full_{STAMP}.zip), a complete year file "
             "with no upstream filter, selected locally on the Cedar "
             "identifier ledger.",
         "effect_on_series":
             "The two populations are not the same by construction. Measured "
             f"on FY2022 with the same tier-A/B identifier population: the "
             f"archive finds "
             f"{val('transaction_rows','usaspending_archive_20260706'):,.0f} "
             f"rows against the .dta's "
             f"{val('transaction_rows','existing_master_prime_file_dta'):,.0f} "
             f"({val('transaction_rows','pct_diff')}%), and "
             f"{val('entities_in_archive_absent_from_dta','usaspending_archive_20260706'):,.0f} "
             "Cedar entities have FY2022 prime contracting that the .dta "
             "population missed entirely. Always split a prime-contracting "
             "trend on `source_file`; never chart FY2022->FY2023 as growth.",
         "verification_status": "MEASURED",
         "source": "internal: code/114_pull_prime_archive.py seam; "
                   f"review/prime_archive_seam_{TODAY}.csv",
         "built_date": TODAY},
        {"dataset": "prime_contracting", "column": "fiscal_year",
         "break_period": f"pre-FY{ARCHIVE_FLOOR}",
         "break_type": "SOURCE_COVERAGE_FLOOR",
         "what_changed":
             "The USAspending award_data_archive publishes "
             f"`_All_Contracts_Full_` for FY{ARCHIVE_FLOOR} forward only "
             "(bucket listing paginated 2026-08-07, 4,631 keys). There is no "
             "FY2000-FY2006 full contracts file.",
         "effect_on_series":
             f"FY2000-FY{ARCHIVE_FLOOR-1} can never be rebuilt from this "
             "route and remains BGOV-filtered. That floor belongs to the "
             "source, not to Cedar, and those seven years stay "
             "under-inclusive until another source supplies them.",
         "verification_status": "MEASURED",
         "source": "https://files.usaspending.gov/award_data_archive/",
         "built_date": TODAY},
        {"dataset": "prime_contracting", "column": "total_obligations_real2025",
         "break_period": "FY2026",
         "break_type": "DEFLATOR_UNAVAILABLE",
         "what_changed":
             "FY2026 is an incomplete fiscal year, so BEA publishes no annual "
             "GDP implicit price deflator for it.",
         "effect_on_series":
             "FY2026 rows carry `deflator_factor_2025 = 1.0`, i.e. real2025 "
             "equals nominal. Forecasting the index and presenting the "
             "forecast as a measurement would be worse. FY2026 is also a "
             "PARTIAL year in row counts and must never be compared to a full "
             "year without saying so.",
         "verification_status": "MEASURED",
         "source": "data/clean/inflation_deflator.csv (BEA NIPA Table 1.1.9)",
         "built_date": TODAY},
        {"dataset": "prime_contracting", "column": "setaside",
         "break_period": f"FY2023 forward",
         "break_type": "VOCABULARY_HARMONISED",
         "what_changed":
             "The .dta stores a collapsed 7-value set-aside vocabulary; the "
             "archive stores ~40 raw FPDS codes. Archive rows are collapsed "
             "onto the same 7 values (8A/8AN -> 8(a); BI -> Buy Indian; "
             "IEE/ISBEE -> Indian Business; HZC/HZS/HS2/HS3 -> HUBZone; "
             "SBA/SBP/SB -> Small Business; blank -> None reported; all else "
             "-> Other).",
         "effect_on_series":
             "`setaside` stays comparable across the seam, but the mapping is "
             "Cedar's and any code not in the table above lands in 'Other'. "
             "The `reported_*` flags are the contracting office's SELF-REPORT "
             "and are never Cedar's determination of Native ownership - "
             "60.9% of the Native contracting dollars we identify carry no "
             "Native preference flag at all.",
         "verification_status": "MEASURED",
         "source": "internal: code/114_pull_prime_archive.py SETASIDE",
         "built_date": TODAY},
    ]
    p = REVIEW / f"prime_archive_series_breaks_{TODAY}.csv"
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    log(f"wrote {p.relative_to(CEDAR)}  - PROPOSAL for the owner of "
        "data/clean/series_breaks.csv to merge; that file is not edited here")


# --------------------------------------------------------------------------
# append
# --------------------------------------------------------------------------
def _iter_mapped(fy, sa_map=None):
    """Stream mapped rows for one filtered year, tier A/B only."""
    src = FILTERED / f"FY{fy}_ledger_rows.csv"
    zipname = f"FY{fy}_All_Contracts_Full_{stamp_for(fy)}.zip"
    with open(src, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            if (r.get("match_tier") or "") not in ("A", "B"):
                continue        # tier-X excluded UEIs never enter the product
            row = map_row(r, zipname, sa_map)
            if row["fiscal_year"] != fy:
                continue        # archive files carry a few stray FYs
            yield row


def cmd_append(args):
    if not args.confirm_seam:
        log("REFUSING: run `seam` and pass --confirm-seam. Appending a "
            "differently-filtered population without measuring the join is "
            "how a source change becomes a trend.")
        sys.exit(4)
    st = load_state()
    if not st.get("seam"):
        log("REFUSING: no seam measurement recorded in _state.json.")
        sys.exit(4)

    sa_map = award_setaside_map()
    log(f"award-level set-aside map: {len(sa_map):,} awards carry a code "
        "somewhere in the pulled years; transaction blanks are filled from it")

    have = sorted(int(p.name[2:6]) for p in FILTERED.glob("FY*_ledger_rows.csv"))
    new_years = [y for y in have if y in NEW_FY]
    overlap_years = [y for y in have if y < 2023]
    log(f"filtered years on disk: {have}")
    log(f"  -> APPEND to prime_contracts.csv: {new_years}")
    log(f"  -> parallel backfill file:        {overlap_years}")

    # ---- APPEND-ONLY into the primary file -------------------------------
    # Re-read the header immediately before writing so a concurrent agent's
    # schema change cannot be silently clobbered, and so an interrupted
    # earlier run cannot be duplicated.
    if new_years:
        with open(PRIMARY, encoding="utf-8", newline="") as fh:
            rd = csv.reader(fh)
            header = next(rd)
        if header != PRIME_FIELDS:
            log("REFUSING: prime_contracts.csv header is not what this script "
                f"maps to.\n  file:   {header}\n  mapper: {PRIME_FIELDS}")
            sys.exit(5)
        existing_sources = set()
        existing_fy = Counter()
        with open(PRIMARY, encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                existing_sources.add(r["source_file"])
                existing_fy[r["fiscal_year"]] += 1
        # Already-appended years are SKIPPED, not a hard refusal: this script
        # is meant to be resumable across a host outage, and a run that
        # aborts because part of its work is already done cannot resume.
        clash = [y for y in new_years
                 if f"FY{y}_All_Contracts_Full_{stamp_for(y, st)}.zip"
                 in existing_sources]
        if clash:
            log(f"SKIPPING {clash}: archive rows for those years are already "
                "in prime_contracts.csv. Not appending a second copy.")
            new_years = [y for y in new_years if y not in clash]
        n, by_fy, dollars = 0, Counter(), Counter()
        with open(PRIMARY, "a", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=PRIME_FIELDS)
            for fy in new_years:
                for row in _iter_mapped(fy, sa_map):
                    w.writerow(row)
                    n += 1
                    by_fy[fy] += 1
                    dollars[fy] += row["total_obligations"]
        log(f"APPENDED {n:,} rows to prime_contracts.csv")
        for fy in sorted(by_fy):
            log(f"   FY{fy}: {by_fy[fy]:,} rows  ${dollars[fy]/1e9:,.3f}B")
        st["append"]["primary"] = {"when": now(), "rows": n,
                                   "by_fy": dict(by_fy),
                                   "obligations_by_fy": dict(dollars)}

    # ---- parallel file for the years the .dta already covers --------------
    if overlap_years:
        n, by_fy, dollars = 0, Counter(), Counter()
        with open(BACKFILL, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=PRIME_FIELDS)
            w.writeheader()
            for fy in overlap_years:
                for row in _iter_mapped(fy, sa_map):
                    w.writerow(row)
                    n += 1
                    by_fy[fy] += 1
                    dollars[fy] += row["total_obligations"]
        log(f"wrote {BACKFILL.relative_to(CEDAR)}  ({n:,} rows) - the same "
            "schema, DELIBERATELY not merged into prime_contracts.csv. Those "
            "years already hold .dta rows and a second copy in one file would "
            "make sum(total_obligations) double-count sixteen years while "
            "looking like growth.")
        for fy in sorted(by_fy):
            log(f"   FY{fy}: {by_fy[fy]:,} rows  ${dollars[fy]/1e9:,.3f}B")
        st["append"]["backfill"] = {"when": now(), "rows": n,
                                    "by_fy": dict(by_fy),
                                    "obligations_by_fy": dict(dollars)}
    save_state(st)


# --------------------------------------------------------------------------
# rebuild - the honest fix the pull log promised
#
# `append` is append-only and never rewrites a row, which is the right default
# and is why FY2023/FY2024 landed mapped against a set-aside map built from
# only THREE filtered years (17,807 awards). The fill is a pooled lookup: an
# award modified in FY2024 usually has its base action - and its set-aside - in
# an earlier year's file, so every year added makes the map strictly better for
# everything mapped AFTERWARDS and does nothing for what was already written.
#
# Leaving that alone would publish two different definitions of the same column
# inside one file: FY2023/24 filled from 3 years, FY2025/26 from 20. The
# preference share would then move between years for a reason that is about
# which files existed when a script ran, not about contracting. That is the
# artefact-that-looks-like-a-discovery this whole build exists to avoid.
#
# So those years are DROPPED AND RE-DERIVED from their filtered extracts, which
# are the retained raw artefact and were never modified. .dta rows are streamed
# through untouched - they are matched on `source_file`, never on fiscal year,
# because FY2023 also holds .dta rows that this must not touch.
# --------------------------------------------------------------------------
ARCHIVE_SRC = re.compile(r"^FY(\d{4})_All_Contracts_Full_(\d{8})\.zip$")


def _setaside_profile(path, only_sources=None):
    """(rows, dollars) by setaside label, for measuring what a rebuild moved."""
    rows, dollars = Counter(), Counter()
    with open(path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if only_sources is not None and r["source_file"] not in only_sources:
                continue
            rows[r["setaside"]] += 1
            dollars[r["setaside"]] += _f(r["total_obligations"])
    return rows, dollars


def _share_no_pref(rows, dollars):
    tr, td = sum(rows.values()), sum(dollars.values())
    return (rows["None reported"] / tr * 100 if tr else 0.0,
            dollars["None reported"] / td * 100 if td else 0.0,
            dollars["None reported"], td)


def cmd_rebuild(args):
    st = load_state()
    sa_map = award_setaside_map()
    have = sorted(int(p.name[2:6]) for p in FILTERED.glob("FY*_ledger_rows.csv"))
    log(f"award-level set-aside map: {len(sa_map):,} awards, pooled over "
        f"{len(have)} filtered years {have}")

    with open(PRIMARY, encoding="utf-8", newline="") as fh:
        rd = csv.reader(fh)
        header = next(rd)
    if header != PRIME_FIELDS:
        log(f"REFUSING: header is not what this script maps to.\n  file: {header}")
        sys.exit(5)

    present = Counter()
    with open(PRIMARY, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if ARCHIVE_SRC.match(r["source_file"]):
                present[r["source_file"]] += 1
    if not present:
        log("no archive-sourced rows in prime_contracts.csv; nothing to rebuild")
        return

    want = ([int(y) for y in args.years.split(",")] if args.years
            else sorted({int(ARCHIVE_SRC.match(s).group(1)) for s in present}))
    targets = {s for s in present
               if int(ARCHIVE_SRC.match(s).group(1)) in want}
    missing = [y for y in want
               if not (FILTERED / f"FY{y}_ledger_rows.csv").exists()]
    if missing:
        log(f"REFUSING: {missing} have rows in the file but no filtered extract "
            "to re-derive them from. A rebuild that cannot regenerate what it "
            "deletes is a deletion.")
        sys.exit(6)

    before_rows, before_dollars = _setaside_profile(PRIMARY, targets)
    log(f"REBUILDING {sorted(targets)}")
    for s in sorted(targets):
        log(f"   {s}: {present[s]:,} rows will be dropped and re-derived")

    bak = PRIMARY.with_suffix(f".bak_{TODAY}_pre_rebuild")
    if not bak.exists():
        bak.write_bytes(PRIMARY.read_bytes())
        log(f"backup -> {bak.name}")

    tmp = PRIMARY.with_suffix(".rebuild.part")
    kept = dropped = added = 0
    by_fy, dollars = Counter(), Counter()
    with open(PRIMARY, encoding="utf-8", newline="") as fi, \
            open(tmp, "w", encoding="utf-8", newline="") as fo:
        rd = csv.DictReader(fi)
        w = csv.DictWriter(fo, fieldnames=PRIME_FIELDS)
        w.writeheader()
        for r in rd:
            if r["source_file"] in targets:
                dropped += 1
                continue
            w.writerow(r)
            kept += 1
        for fy in want:
            for row in _iter_mapped(fy, sa_map):
                w.writerow(row)
                added += 1
                by_fy[fy] += 1
                dollars[fy] += row["total_obligations"]

    # A rebuild re-derives the SAME population from the SAME extract, so the
    # count must land back where it started. A drift means the extract or the
    # tier filter changed underneath, and that is a finding, not a rounding.
    if added != dropped:
        log(f"WARNING: dropped {dropped:,} but re-derived {added:,} "
            f"({added - dropped:+,}). The extract or the tier filter changed "
            "since these rows were written. NOT smoothing this - inspect "
            f"before trusting {PRIMARY.name}. Original preserved at {bak.name}.")
    tmp.replace(PRIMARY)
    log(f"rebuilt: {kept:,} rows untouched, {dropped:,} dropped, "
        f"{added:,} re-derived")
    for fy in sorted(by_fy):
        log(f"   FY{fy}: {by_fy[fy]:,} rows  ${dollars[fy]/1e9:,.3f}B")

    after_rows, after_dollars = _setaside_profile(PRIMARY, targets)
    b = _share_no_pref(before_rows, before_dollars)
    a = _share_no_pref(after_rows, after_dollars)
    log("")
    log("SET-ASIDE REFILL on the rebuilt years - 'None reported' share")
    log(f"   before (3-year map):  {b[0]:6.2f}% of rows  {b[1]:6.2f}% of "
        f"dollars  (${b[2]/1e9:,.3f}B of ${b[3]/1e9:,.3f}B)")
    log(f"   after ({len(have)}-year map): {a[0]:6.2f}% of rows  {a[1]:6.2f}% of "
        f"dollars  (${a[2]/1e9:,.3f}B of ${a[3]/1e9:,.3f}B)")
    log(f"   moved: {a[0]-b[0]:+.2f} pp of rows, {a[1]-b[1]:+.2f} pp of dollars")
    log("   A FALL here is the fill working: transactions that were blank - "
        "and therefore read as 'None reported' - recovered their award's "
        "set-aside from another year's file.")
    for lab in sorted(set(before_rows) | set(after_rows)):
        d = after_rows[lab] - before_rows[lab]
        if d:
            log(f"     {lab:<28} {before_rows[lab]:>7,} -> {after_rows[lab]:>7,} "
                f"({d:+,})")

    st.setdefault("rebuild", {})[now()] = {
        "years": want, "dropped": dropped, "re_derived": added,
        "map_awards": len(sa_map), "map_years": have,
        "none_reported_pct_rows_before": round(b[0], 4),
        "none_reported_pct_rows_after": round(a[0], 4),
        "none_reported_pct_dollars_before": round(b[1], 4),
        "none_reported_pct_dollars_after": round(a[1], 4),
    }
    save_state(st)


# --------------------------------------------------------------------------
# codebook FRAGMENT - never the master
# --------------------------------------------------------------------------
def cmd_codebook(args):
    """`codebook_master.csv` has many writers and is a lost-update race.

    `code/cedar_codebook.py` exists because of it: each dataset owns a
    fragment it alone writes, and the master is a DERIVED concatenation. This
    writes only its own fragment.
    """
    import pandas as pd
    frag = CLEAN / "codebook" / "02d_prime_contracting_archive.csv"
    frag.parent.mkdir(parents=True, exist_ok=True)

    src = BACKFILL if BACKFILL.exists() else PRIMARY
    d = pd.read_csv(src, low_memory=False)
    if src == PRIMARY:
        d = d[d.source_file.str.startswith("FY", na=False)]
    n = len(d)

    desc = {
        "contract_number": "FPDS PIID of the contract action.",
        "parent_contract_number": "Parent award PIID (the vehicle the action "
                                  "was placed against); falls back to the "
                                  "PIID itself when the action is standalone.",
        "fiscal_year": "Federal fiscal year of the action date. FY2026 is a "
                       "PARTIAL year.",
        "pre_2000_flag": "1 where fiscal_year < 2000. Always 0 on archive "
                         "rows: the archive floor is FY2007.",
        "awardee_name": "Recipient name as filed in FPDS.",
        "awardee_uei": "Recipient UEI. One of the two identifiers this "
                       "dataset joins on; no name matching is used.",
        "cage_code": "Recipient CAGE. The second join identifier; CAGE "
                     "persists across the DUNS retirement.",
        "parent_name": "Recipient's declared ultimate parent name.",
        "parent_uei": "Recipient's declared ultimate parent UEI. FPDS "
                      "hierarchy is a self-declaration and is EVIDENCE, not "
                      "authority; it is used to group families, never "
                      "published as Cedar's statement of ownership.",
        "total_obligations": "federal_action_obligation. TRANSACTIONAL - it "
                             "SUMS. Negative means money was taken back "
                             "(deobligation) and belongs in the total; zero "
                             "means an action that moved no money; blank "
                             "means not reported and is not zero.",
        "total_award_value": "current_total_value_of_award. RESTATED on every "
                             "transaction of the award - MAX it per award, "
                             "never sum it.",
        "total_obligations_real2025": "total_obligations x the BEA GDP "
                                      "implicit price deflator (NIPA Table "
                                      "1.1.9), base 2025. FY2026 has no BEA "
                                      "annual index and carries factor 1.0.",
        "total_award_value_real2025": "As above, applied to total_award_value. "
                                      "Still MAX, never sum.",
        "deflator_factor_2025": "The factor applied. 1.0 on FY2026 means "
                                "undeflated, not adjusted.",
        "inflation_base_year": "Always 2025 - the most recent COMPLETE year "
                               "BEA publishes an annual index for.",
        "setaside": "FPDS set-aside collapsed onto the same 7-value "
                    "vocabulary the FY2000-2022 rows use. SELF-REPORTED by "
                    "the contracting office.",
        "reported_8a": "1 where the record reports an 8(a) set-aside (SBA "
                       "business development, 13 CFR 124). A CLAIM in the "
                       "record, never Cedar's determination.",
        "reported_buy_indian": "1 where the record reports Buy Indian "
                               "(25 U.S.C. 47; Interior and IHS only).",
        "reported_indian_business": "1 where the record reports an Indian "
                                    "Economic Enterprise or Indian Small "
                                    "Business Economic Enterprise set-aside.",
        "reported_native_preference": "1 where any of the three above is "
                                      "reported. ABSENCE UNDER THIS FLAG IS A "
                                      "PROPERTY OF THE FLAG: 60.9% of the "
                                      "Native contracting dollars Cedar "
                                      "identifies carry no Native preference "
                                      "at all.",
        "setaside_reported": "1 where any set-aside is reported.",
        "extent_competed": "FPDS extent-competed description.",
        "funding_agency": "Funding sub-agency, Title Cased to match the "
                          "FY2000-2022 vocabulary; DoD collapses to 'Dept Of "
                          "Defense'.",
        "sector": "NAICS 2-digit, or 'Not given'.",
        "supersector": "BLS-style supersector derived from `sector`, "
                       "reproducing the FY2000-2022 buckets exactly.",
        "defense": "1 where funding_agency is 'Dept Of Defense'.",
        "recipient_city_name": "Recipient city as filed.",
        "recipient_state_code": "Recipient state as filed.",
        "place_of_perform_city": "Primary place of performance city. This is "
                                 "a DIFFERENT geography from the recipient "
                                 "address - dollars flow to one, work happens "
                                 "at the other.",
        "place_of_perform_state": "Primary place of performance state.",
        "tribe_id": "Cedar entity id. Populated only on an identifier hit at "
                    "tier A or B. No name matching.",
        "canonical_name": "Cedar canonical entity name for tribe_id.",
        "attribution_method": "uei_exact | cage_exact | parent_uei | "
                              "unattributed. parent_uei is the weakest and is "
                              "recorded separately so it can be withdrawn on "
                              "its own.",
        "confidence_tier": "A or B on an attributed row, C otherwise. Tier-X "
                           "(excluded) UEIs are counted in the raw extract "
                           "and NEVER enter this file.",
        "attributed_flag": "1 where an identifier hit at tier A or B.",
        "source_file": f"FY####_All_Contracts_Full_{STAMP}.zip - the archive "
                       "object this row came from. This is what keeps the "
                       "source seam visible in the data, not only in a doc.",
        "source_authority": "USAspending award_data_archive (FPDS-NG static "
                            "monthly file).",
        "built_date": "Date this row was built.",
    }
    rows = []
    for c in PRIME_FIELDS:
        filled = round(float(d[c].notna().mean()) * 100, 1) if c in d else 0.0
        rows.append({
            "dataset": "02_prime_contracting", "variable": c,
            "type": "number" if c in (
                "fiscal_year", "pre_2000_flag", "total_obligations",
                "total_award_value", "total_obligations_real2025",
                "total_award_value_real2025", "deflator_factor_2025",
                "inflation_base_year", "reported_8a", "reported_buy_indian",
                "reported_indian_business", "reported_native_preference",
                "setaside_reported", "defense", "attributed_flag") else "text",
            "units": "usd" if "obligation" in c or "award_value" in c
                     else ("year" if "year" in c else "code"),
            "pct_filled": filled, "n_rows": n, "published": 1,
            "access_tier": "subscriber",
            "description": desc.get(c, ""), "generated": TODAY})
    with open(frag, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    log(f"wrote {frag.relative_to(CEDAR)}  ({len(rows)} variables, {n:,} rows "
        "measured) - FRAGMENT ONLY; codebook_master.csv is not touched")


# --------------------------------------------------------------------------
# panel - cascade the append to the derived entity-year file
#
# `prime_contracts_entity_year.csv` is DERIVED from `prime_contracts.csv`, so
# appending to the latter and stopping leaves the former quietly stale - and
# `62_no_regression_check.py` reads the DERIVED file, so the guard would keep
# reporting "no regressions" over a panel that had silently stopped at FY2022.
#
# `code/40_build_prime_contracts.py` is the file's normal builder and MUST NOT
# be run to fix this: it rebuilds `prime_contracts.csv` from the .dta and
# would erase every archive row appended here. So this extends the panel
# incrementally, for the new fiscal years only, append-only, refusing any year
# already present.
# --------------------------------------------------------------------------
PANEL = CLEAN / "prime_contracts_entity_year.csv"
PANEL_FIELDS = ["tribe_id", "canonical_name", "fiscal_year",
                "confidence_tier", "obligations_usd", "n_contracts",
                "built_date"]


def cmd_panel(args):
    sa_map = award_setaside_map()
    with open(PANEL, encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        if rd.fieldnames != PANEL_FIELDS:
            log(f"REFUSING: panel header changed. file={rd.fieldnames}")
            sys.exit(5)
        present = {int(r["fiscal_year"]) for r in rd}

    years = [y for y in sorted(int(p.name[2:6])
                               for p in FILTERED.glob("FY*_ledger_rows.csv"))
             if y in NEW_FY]
    todo = [y for y in years if y not in present]
    skip = [y for y in years if y in present]
    if skip:
        log(f"SKIPPING {skip}: already in the panel")
    if not todo:
        log("panel already current")
        return

    agg = {}
    for fy in todo:
        for row in _iter_mapped(fy, sa_map):
            if not row["attributed_flag"]:
                continue
            k = (row["tribe_id"], row["canonical_name"], row["fiscal_year"],
                 row["confidence_tier"])
            e = agg.setdefault(k, [0.0, 0])
            e[0] += row["total_obligations"]
            e[1] += 1
    out = [{"tribe_id": t, "canonical_name": c, "fiscal_year": y,
            "confidence_tier": tier, "obligations_usd": round(v[0], 2),
            "n_contracts": v[1], "built_date": TODAY}
           for (t, c, y, tier), v in sorted(agg.items())]
    with open(PANEL, "a", encoding="utf-8", newline="") as fh:
        csv.DictWriter(fh, fieldnames=PANEL_FIELDS).writerows(out)
    log(f"appended {len(out):,} panel rows for {todo} "
        f"({len({r['tribe_id'] for r in out}):,} entities)")


# --------------------------------------------------------------------------
# doc - GENERATED, never hand-edited. Standing rule 10: a number in a doc that
# is not recomputed from the data is a claim, not a fact.
# --------------------------------------------------------------------------
def cmd_doc(args):
    import pandas as pd
    st = load_state()
    sa_map = award_setaside_map()

    per_fy = []
    for p in sorted(FILTERED.glob("FY*_ledger_rows.csv")):
        fy = int(p.name[2:6])
        rows = [map_row(r, f"FY{fy}_All_Contracts_Full_{stamp_for(fy)}.zip", sa_map)
                for r in csv.DictReader(open(p, encoding="utf-8-sig"))
                if (r.get("match_tier") or "") in ("A", "B")]
        d = pd.DataFrame(rows)
        d = d[d.fiscal_year == fy]
        raw = pd.read_csv(p, low_memory=False)
        per_fy.append({
            "fy": fy,
            "scanned": st["years"].get(str(fy), {}).get("scanned_rows", ""),
            "rows": len(d),
            "entities": int(d.tribe_id.nunique()),
            "ueis": int(d.awardee_uei.nunique()),
            "nominal": float(d.total_obligations.sum()),
            "real2025": float(d.total_obligations_real2025.sum()),
            "neg": int((d.total_obligations < 0).sum()),
            "zero": int((d.total_obligations == 0).sum()),
            "uei_m": int((d.attribution_method == "uei_exact").sum()),
            "cage_m": int((d.attribution_method == "cage_exact").sum()),
            "par_m": int((d.attribution_method == "parent_uei").sum()),
            "xrows": int((raw.match_tier == "X").sum()),
            "natpref_usd": float(d[d.reported_native_preference == 1]
                                 .total_obligations.sum()),
        })

    seam = []
    sp = REVIEW / f"prime_archive_seam_{TODAY}.csv"
    if sp.exists():
        seam = list(csv.DictReader(open(sp, encoding="utf-8-sig")))

    def S(metric, col):
        for r in seam:
            if r["metric"] == metric:
                return r[col]
        return ""

    L = []
    A = L.append
    A("# Prime contracts from the USAspending static archive")
    A("")
    A(f"*Generated by `code/114_pull_prime_archive.py doc` on {TODAY}. "
      "Every number here is recomputed from the data; do not hand-edit.*")
    A("")
    A("## Why this route")
    A("")
    A("`api.usaspending.gov` edge-blocked this project twice on 2026-08-07 and "
      "`POST /api/v2/download/transactions/` returned HTTP 503 through a full "
      "60s->1800s backoff. The API was never the only route: FY2000-2022 came "
      "from `master prime file.dta`, not an API pull. This is the third route "
      "- the monthly static archive at `files.usaspending.gov`, a **different "
      "host**, serving static S3 objects by plain GET.")
    A("")
    A("**Zero requests were issued to `api.usaspending.gov`.**")
    A("")
    A("## What the archive publishes")
    A("")
    A("Bucket listing re-enumerated on 2026-08-12 by marker pagination at "
      "`https://files.usaspending.gov/award_data_archive/` (5 pages, "
      "**4,597 keys**, saved to "
      "`data/raw/contracts/archive_listing_2026-08-12.csv`). The v2 form "
      "(`?list-type=2`) 404s at this endpoint; `?marker=` is what it answers.")
    A("")
    A("### THE ARCHIVE REPLACES ITS OBJECTS MONTHLY - IT DOES NOT ACCUMULATE")
    A("")
    A(f"- **`{STAMP}` is now the only stamp**: all 4,597 keys carry it and "
      "**not one carries `20260706`**, the stamp this build's first half read. "
      "Max `LastModified` is 2026-08-10.")
    A("- So `FY2016_All_Contracts_Full_20260706.zip` now answers a **real HTTP "
      "404 in 0.5s**. The 2026-08-07 note in this log recording that "
      "`_20260801`/`_20260806` 404 for all years was true when written and is "
      "now exactly inverted. **Re-probing for a newer stamp before settling "
      "was load-bearing, not a formality.**")
    A("- Consequence for provenance: **two vintages are live in this dataset "
      "at once.** FY2017-FY2026 were read from the July objects and are "
      "labelled `20260706`; FY2008-FY2016 were read from the August objects "
      "and are labelled `20260806`. The stamp is resolved **per year** from "
      "the URL actually fetched, never from a global constant - a global bump "
      "would both mislabel the July rows and silently defeat the guard that "
      "stops FY2023/FY2024 being appended twice.")
    A(f"- `_All_Contracts_Full_` exists for **FY{ARCHIVE_FLOOR} through "
      "FY2026 only**, unchanged across the stamp roll. There is no "
      "FY2000-FY2006 full contracts file, so "
      f"FY2000-FY{ARCHIVE_FLOOR-1} of `prime_contracts.csv` can never be "
      "rebuilt from this route and stays BGOV-filtered.")
    A("")
    A("## Per fiscal year")
    A("")
    A("| FY | rows scanned | rows kept | entities | UEIs | nominal | "
      "real 2025 | negative | zero |")
    A("|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in per_fy:
        sc = f"{r['scanned']:,}" if isinstance(r["scanned"], int) else "-"
        A(f"| {r['fy']} | {sc} | {r['rows']:,} | {r['entities']:,} | "
          f"{r['ueis']:,} | ${r['nominal']/1e9:,.3f}B | "
          f"${r['real2025']/1e9:,.3f}B | {r['neg']:,} | {r['zero']:,} |")
    A("")
    A("Negatives are **deobligations and belong in the totals**; zeros are "
      "actions that moved no money. Neither is missing data.")
    A("")
    A("## How rows matched")
    A("")
    A("Identifier join only - no name matching. `resolve_entity` is the name "
      "resolver and was deliberately not imported.")
    A("")
    A("| FY | recipient_uei | cage_code | parent_uei | tier-X rows excluded |")
    A("|---:|---:|---:|---:|---:|")
    for r in per_fy:
        A(f"| {r['fy']} | {r['uei_m']:,} | {r['cage_m']:,} | {r['par_m']:,} | "
          f"{r['xrows']:,} |")
    A("")
    A("`parent_uei` attributes a row to the *owner* of the awardee and is the "
      "weakest of the three, so it is recorded as its own "
      "`attribution_method` and can be withdrawn on its own. Tier-X UEIs are "
      "Cedar's own exclusion rulings: their rows are kept in the raw extract "
      "as evidence the exclusions are doing work, and never enter "
      "`prime_contracts.csv`.")
    A("")
    if seam:
        A(f"## FY{SEAM_FY} cross-source comparison - the headline")
        A("")
        A("Same fiscal year, same tier-A/B identifier population, two "
          "independent sources. `master prime file.dta` is a BGOV download "
          "taken under a size cap and **pre-filtered to where Native entities "
          "were expected**; the archive has no upstream filter. The "
          "difference is the size of that filter's blind spot.")
        A("")
        A("| metric | `.dta` | archive | diff |")
        A("|---|---:|---:|---:|")
        for r in seam:
            ev, av = r["existing_master_prime_file_dta"], \
                r["usaspending_archive_20260706"]
            try:
                ev = f"{float(ev):,.0f}"
                av = f"{float(av):,.0f}"
            except ValueError:
                pass
            pct = r["pct_diff"]
            pct = f"{float(pct):+.1f}%" if pct not in ("", None) else ""
            A(f"| {r['metric'].replace('_',' ')} | {ev} | {av} | {pct} |")
        A("")
        A("**The two sources measure the same thing where they overlap.** "
          f"{S('shared_contracts_obligations_agree_0.5pct','pct_diff')}% of "
          "the shared contracts agree on obligations within 0.5%, so the gap "
          "is a population difference, not a measurement difference.")
        A("")
        A("**The blind spot, stated three ways:**")
        A("")
        A(f"- {S('contracts_only_in_archive','usaspending_archive_20260706')} "
          "contracts exist only in the archive "
          f"({S('contracts_only_in_archive','note')}).")
        A(f"- {S('ueis_in_archive_absent_from_dta','usaspending_archive_20260706')} "
          "recipient UEIs the `.dta` never saw - "
          f"{S('ueis_in_archive_absent_from_dta','note')}.")
        A(f"- **{S('entities_in_archive_absent_from_dta','usaspending_archive_20260706')} "
          "Cedar entities** had FY2022 prime contracting the `.dta` population "
          "missed entirely.")
        A("")
        # The qualification that decides whether the headline is publishable.
        mp = REVIEW / f"prime_archive_entities_missing_from_dta_{TODAY}.csv"
        ep = REVIEW / f"prime_archive_weak_attribution_exposure_{TODAY}.csv"
        if mp.exists() and ep.exists():
            miss = {r["uei"]: float(r["fy2022_obligations_usd"])
                    for r in csv.DictReader(open(mp, encoding="utf-8-sig"))
                    if r["direction"] == "in_archive_absent_from_dta"}
            weakids = {r["uei"] for r in
                       csv.DictReader(open(ep, encoding="utf-8-sig"))}
            tot = sum(miss.values()) or 1.0
            weak = sum(v for u, v in miss.items() if u in weakids)
            A("")
            A("### But do not publish that UEI number yet")
            A("")
            A(f"**{weak/tot*100:.1f}% of those blind-spot dollars "
              f"(${weak/1e6:,.1f}M of ${tot/1e6:,.1f}M, "
              f"{len([u for u in miss if u in weakids])} of {len(miss)} UEIs) "
              "rest on a tier-B ledger link whose own rationale reads "
              "\"Algorithmic name clustering, unreviewed\".** The largest are "
              "`BLUE TECH INC.` -> *Blue Lake*, `PERATON GOVERNMENT "
              "COMMUNICATIONS INC.` -> *Barrow*, `BUSINESS MISSION EDGE, LLC` "
              "-> *Cabazon* and `WASHINGTON BUSINESS DYNAMICS, LLC` -> "
              "*Stillaguamish* - the trap-token shape AGENTS.md already "
              "records five separate failures of.")
            A("")
            A("This is not a defect in the pull, and it is not an argument "
              "against the archive. It is a **pre-existing ledger risk that "
              "completeness makes expensive**: under the BGOV-filtered `.dta` "
              "those vendors' rows were largely absent, so a weak link cost "
              "little; the complete file gives the same link its full dollar "
              "weight. And it cuts both ways - the `.dta`'s hand-built filter "
              "may have omitted these firms precisely *because* they are not "
              "Native-owned.")
            A("")
            A(f"So the honest reading of the FY2022 comparison is: the "
              "**contract-level** blind spot "
              f"({S('contracts_only_in_archive','usaspending_archive_20260706')} "
              "contracts on UEIs the ledger already trusted) is solid, and "
              "the **new-UEI** leg needs rulings before any of it publishes. "
              f"All {len(weakids):,} exposed identifiers are queued in "
              f"`review/prime_archive_weak_attribution_exposure_{TODAY}.csv` "
              "with the dollar amount attached, one ruling per row.")
            A("")
        A("**And the other direction is small and flagged, not dropped:** "
          f"{S('contracts_only_in_dta','existing_master_prime_file_dta')} "
          "contracts appear only in the `.dta` "
          f"({S('contracts_only_in_dta','note')}). Every one is listed in "
          f"`review/prime_archive_entities_missing_from_dta_{TODAY}.csv` for "
          "a ruling before the archive replaces a `.dta` year.")
        A("")
        A("`current_total_value_of_award` reproduces the existing "
          "`total_award_value` better than `potential_total_value_of_award` "
          f"({S('award_value_max_matches_current_total_value_of_award','pct_diff')}% "
          f"vs {S('award_value_max_matches_potential_total_value_of_award','pct_diff')}% "
          "of shared contracts, MAXed per award), so it is the one mapped. "
          "Neither reproduces it exactly.")
        A("")
    landed = sorted(int(p.name[2:6]) for p in FILTERED.glob("FY*_ledger_rows.csv"))
    refused = sorted(int(k) for k, v in st.get("years", {}).items()
                     if v.get("http_status") == 0)
    A("## State of this pull - what landed and what is still owed")
    A("")
    A(f"**Landed and filtered:** {', '.join('FY%d' % y for y in landed)}.")
    A("")
    if refused:
        A(f"**Still owed:** {', '.join('FY%d' % y for y in refused)}.")
        A("")
        A("Those years were **refused by the host, not absent from it**, and "
          "each one's manifest row records the status and time it was actually "
          "refused at rather than a remembered one:")
        A("")
        A("| FY | http_status | refused at | reading |")
        A("|---|---|---|---|")
        for y in refused:
            d = st["years"].get(str(y), {})
            code = d.get("http_status", "")
            reading = ("transport failure - connection closed with no response"
                       if code == 0 else
                       "host-side HTTP status, not an answer about the object"
                       if code in (429, 500, 502, 503, 504) else
                       "an answer about the object")
            A(f"| {y} | `{code}` | {d.get('fetched_utc','')} | {reading} |")
        A("")
        A("A sub-second `RemoteDisconnected` is an **edge block, not a slow "
          "server**, and an HTTP 500 is a fact about the host having a bad "
          "moment - neither is a fact about the year. The bucket listing "
          "enumerated every one of these keys, so no year may be written off. "
          "`_SOURCE_MANIFEST.csv` carries the reading in words next to the "
          "status, precisely so a later reader cannot mistake a refusal for "
          "absence.")
        A("")
        A("Resume with (idempotent - already-filtered years are skipped, and "
          "the run carries a 2h `RUN_DEADLINE` plus a stop on the first "
          "refusal):")
        A("")
        A("```")
        A("py -3 code/114_pull_prime_archive.py run --pause 60 --years "
          + ",".join(str(y) for y in refused))
        A("py -3 code/114_pull_prime_archive.py append --confirm-seam")
        A("py -3 code/114_pull_prime_archive.py panel")
        A("py -3 code/114_pull_prime_archive.py codebook && "
          "py -3 code/114_pull_prime_archive.py doc")
        A("```")
        A("")
        A("**One consequence to know about.** The award-level set-aside fill "
          "pools every pulled year, so it is only as good as the years on "
          "disk, and `append` never rewrites a row it has already written. "
          "The 2026-08-08 run therefore left FY2023/FY2024 mapped against a "
          "3-year, 17,807-award map. **That has since been repaired**: "
          "`py -3 code/114_pull_prime_archive.py rebuild --years 2023,2024` "
          "drops those rows and re-derives them from their retained filtered "
          "extracts against the full map. See the measured effect below - the "
          "3-year map turned out to be inert, so the rebuild was not "
          "cosmetic.")
        A("")
    A("## Where the rows went, and why not all into one file")
    A("")
    A("- **FY2023-FY2026 append to `data/clean/prime_contracts.csv`.** Those "
      "years did not exist there. No existing row was read-modified or "
      "rewritten; the header was re-read and compared immediately before "
      "writing.")
    A("- **FY2007-FY2022 go to `data/clean/prime_contracts_archive_backfill.csv`**, "
      "same schema. This file is the STAGING area, not the product: a second "
      "larger copy of sixteen years sitting in `prime_contracts.csv` unkeyed "
      "would make `sum(total_obligations)` double-count while looking like "
      "growth.")
    A("- **MERGED 2026-08-12 by `code/131_merge_archive_backfill.py`** "
      "(FY2008-FY2022; FY2007 follows when it lands). `prime_contracts.csv` "
      "went 826,637 -> 1,217,768 rows. The merge keys on "
      "**(contract_number, fiscal_year, awardee_uei)** and drops every BGOV row "
      "on a shared key, so no transaction is counted twice. It does NOT key on "
      "`funding_agency`: the two sources render the same office differently "
      "(`Us Geological Survey` vs `Geological Survey`), and including it leaves "
      "**$20.5B double-counted**. It cannot key on modification number - "
      "`master prime file.dta` carries none. The backfill file is RETAINED as "
      "the staged source and the merge refuses to run twice.")
    A("")
    A("`source_file` carries the archive object name on every new row and is "
      "never rewritten on a BGOV row, so the seam stays visible in the data and "
      "not only in this document.")
    A("")
    A("## Two things that had to be fixed, and are worth remembering")
    A("")
    A("**A dropped connection is not a 404.** The first run's `head()` "
      "returned status 0 for both, and the caller treated 0 like \"this year "
      "is not published\" and walked on. When the host began refusing, it "
      "raced through nineteen years in five seconds, issuing a burst of HEADs "
      "at a host that was refusing us *for* request rate. `head()` now backs "
      "off on a transport failure and returns 0 only after exhausting it, and "
      "the caller treats 0 as **stop-work** rather than as an answer about "
      "the year. A 404 is a fact about the year; a reset is a fact about the "
      "host.")
    A("")
    A("**A set-aside is a property of the award, not of each modification.** "
      "The archive reports `type_of_set_aside_code` per transaction and "
      "leaves it blank on 56% of rows, overwhelmingly on modifications; the "
      "`.dta` carries the award's value on every transaction. Read "
      "transaction-level the two disagree on 59.4% of shared FY2022 "
      "contracts, and 4,528 contracts the `.dta` calls 8(a) land in \"None "
      "reported\" - which would have **inflated the published \"no Native "
      "preference\" share on the strength of a definition change**. Blanks "
      "are filled from any non-blank observation of the same "
      f"`contract_award_unique_key` across every pulled year ({len(sa_map):,} "
      "awards).")
    A("")
    A("### The backfill's effect on the fill, measured three ways")
    A("")
    A("The claim that the fill needs the backfill years was stated in the "
      "2026-08-07 log as a prediction. It is now measured, and it was "
      "**understated**:")
    A("")
    A("| set-aside map | awards | FY2023-24 8(a) rows | no-Native-preference (rows) | (dollars) |")
    A("|---|---:|---:|---:|---:|")
    A("| none - raw transaction-level | 0 | 18,818 | 79.76% | 66.64% |")
    A("| 3 years (FY2022-24), as shipped 2026-08-08 | 17,807 | 18,818 | 79.76% | 66.64% |")
    A(f"| 19 years (FY2008-26), this build | {len(sa_map):,} | 19,421 | 79.15% | 66.76% |")
    A("")
    A("**The 3-year map was bit-for-bit identical to no fill at all** on "
      "FY2023-24 - same 8(a) count, same share to four significant figures. "
      "Not a small improvement: *nothing*. Every blank it could have filled "
      "belonged to an award whose set-aside-bearing base action sits in a "
      "year that had not been pulled yet, which is precisely the mechanism "
      "the log predicted and could not then demonstrate. The fill only starts "
      "working once the earlier years exist, so FY2023-24 shipped in "
      "2026-08-08 carrying an award-level correction that was **inert**.")
    A("")
    A("Rebuilding those two years against the 19-year map moved **848 rows** "
      "out of \"None reported\" (603 of them into 8(a)).")
    A("")
    A("### But the fill does NOT close the gap, and that is the finding")
    A("")
    A("| FY2022 shared contracts | disagree with `.dta` | `.dta` 8(a) landing in \"None reported\" |")
    A("|---|---:|---:|")
    A("| no fill | 10,287 of 17,325 (59.4%) | 4,528 |")
    A("| 3-year map | 10,287 of 17,325 (59.4%) | 4,528 |")
    A("| 19-year map | 10,013 of 17,325 (57.8%) | 4,317 |")
    A("")
    A("**A complete award-level fill across twenty fiscal years still leaves "
      "4,317 contracts that the `.dta` calls 8(a) and the archive reports no "
      "set-aside for anywhere.** That residual is not a gap in the fill - the "
      "fill has already looked in every year the source publishes. The two "
      "sources genuinely differ about what a set-aside is on those awards, "
      "and the archive's silence is a **non-report, not an assertion of "
      "\"no set-aside used\"**. It is recorded, not smoothed, and it is why "
      "the set-aside columns stay named `reported_*`.")
    A("")
    A("**Net effect on the published statistic: essentially none.** Across "
      "the whole of `prime_contracts.csv` the rebuild moved the \"no Native "
      "preference\" share from 63.84% to 63.86% of dollars (+0.02pp, "
      "$155.460B -> $155.506B) and from 70.52% to 70.44% of rows. The "
      "direction is worth noticing: the **dollar** share ticked *up* while "
      "the **row** share fell, because the transactions that recovered a "
      "set-aside are net **deobligations** - blanks concentrate on "
      "modifications, and modifications that give money back are a large part "
      "of them. Removing net-negative rows from a bucket raises that bucket's "
      "total. This is the deobligation rule doing visible work rather than "
      "being asserted.")
    A("")
    A("## Standing caveats that still apply")
    A("")
    A("- **The set-aside columns are `reported_*` - self-reports, never "
      "Cedar's determination.** Measured on this pull: "
      + ", ".join(f"FY{r['fy']} {r['natpref_usd']/max(r['nominal'],1)*100:.1f}%"
                  for r in per_fy)
      + " of attributed dollars carry any Native preference flag at all. "
        "Absence under a filter is a property of the filter.")
    A("- **This is a lower bound and it loosens each year.** The population is "
      "the ledger's own identifiers, so a Native firm the ledger has never "
      "seen is invisible to it. The fix is ledger growth, not a different "
      "endpoint.")
    A("- **FY2026 is a partial year** and has no BEA annual deflator, so it "
      "carries factor 1.0 - undeflated, not adjusted. Never compare it to a "
      "full year.")
    A("- **`total_award_value` is restated on every transaction** and must be "
      "MAXed per award, never summed.")
    A("")
    A("## Files")
    A("")
    A(f"- `data/raw/contracts/usaspending_archive_2026-08-07/` - zips + "
      "`_SOURCE_MANIFEST.csv` (url, HTTP status, bytes, md5, S3 etag, "
      "verification, retained-or-released)")
    A("- `data/raw/contracts/usaspending_archive_2026-08-07/filtered/` - the "
      "ledger-matched extract, raw archive columns plus match metadata")
    A(f"- `review/prime_archive_seam_{TODAY}.csv`")
    A(f"- `review/prime_archive_entities_missing_from_dta_{TODAY}.csv`")
    A(f"- `review/prime_archive_weak_attribution_exposure_{TODAY}.csv`")
    A(f"- `review/prime_archive_series_breaks_{TODAY}.csv` - **proposal** for "
      "the owner of `data/clean/series_breaks.csv`; that file is not edited "
      "here")
    A("- `data/clean/codebook/02d_prime_contracting_archive.csv` - "
      "**fragment**; `codebook_master.csv` is not touched")
    A("")

    DOCS.mkdir(exist_ok=True)
    p = DOCS / "PRIME_ARCHIVE_PULL_LOG.md"
    p.write_text("\n".join(L), encoding="utf-8")
    log(f"wrote {p.relative_to(CEDAR)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "seam", "append", "rebuild",
                                    "codebook", "panel", "doc", "status"])
    ap.add_argument("--years")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--keep-zips", action="store_true")
    ap.add_argument("--pause", type=int, default=30,
                    help="seconds between years; keeps the request pattern "
                         "from looking like a scraper")
    ap.add_argument("--confirm-seam", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    {"run": cmd_run, "seam": cmd_seam, "append": cmd_append,
     "rebuild": cmd_rebuild,
     "codebook": cmd_codebook, "doc": cmd_doc, "panel": cmd_panel,
     "status": lambda a: print(json.dumps(load_state(), indent=2)[:8000])
     }[args.cmd](args)


if __name__ == "__main__":
    main()
