#!/usr/bin/env python3
"""
Cedar Press - 115: the USAspending STATIC ARCHIVE route (files.usaspending.gov).

WHY THIS EXISTS
---------------
`api.usaspending.gov` edge-blocked this project twice on 2026-08-07 and its
`/search/` endpoints returned HTTP 503 through a full exponential backoff
(logs/44_contracts_transactions.log, 18:01-18:32Z and 23:25-23:56Z).

`files.usaspending.gov` is a DIFFERENT HOST serving static S3 objects. It was
probed at 2026-08-07T23:5x and answered HTTP 200. This script uses only that
host. It never touches api.usaspending.gov - not even for a probe.

    Lock: logs/_HOSTLOCK_files.usaspending.gov.json
    A concurrent agent is pulling FY2023-26 CONTRACTS from the same bucket.
    This script fetches ASSISTANCE members only, sequentially, with a pause
    between objects.

WHAT THE ARCHIVE ACTUALLY CONTAINS - MEASURED, NOT ASSUMED
----------------------------------------------------------
Full enumeration of the listing (5 pages, ListObjects v1 `marker` pagination,
IsTruncated at 1,000 keys per page) returned **4,631 objects in exactly 12
filename shapes**:

    2000  FY####_###_Assistance_Full_########.zip     (3-digit agency code)
    2000  FY####_###_Contracts_Full_########.zip
     240  FY####_####_Assistance_Full_########.zip     (4-digit agency code)
     240  FY####_####_Contracts_Full_########.zip
      20  FY####_All_Assistance_Full_########.zip      <- what we use
      20  FY####_All_Contracts_Full_########.zip
      60  FY(All)_###_Contracts_Delta_########.zip
      38  FY(All)_###_Assistance_Delta_########.zip
       8  FY(All)_####_Contracts_Delta_########.zip
       3  FY(All)_####_Assistance_Delta_########.zip
       1  FY(All)_All_Assistance_Delta_########.zip
       1  FY(All)_All_Contracts_Delta_########.zip

**ZERO of the 4,631 keys contain the string "sub" in any case.** The archive
publishes CONTRACTS and ASSISTANCE only. There is no `Subawards` member, no
`FY{year}_All_Subawards_Full_*.zip`, and no subaward file inside an Assistance
or Contracts zip (member lists are recorded per object in the manifest). The
neighbouring paths `subaward_data_archive/`, `subaward_archive/`,
`broker_reference_data/` and `database_download/` return 404, `reference_data/`
returns 403.

So gap 3 - subawards FY2021-FY2024 and the missing FY2020 CONTRACT subawards -
**cannot be closed from this host.** That is a property of the source, recorded
here and in docs/ASSISTANCE_ARCHIVE_PULL_LOG.md, not a failure of the pull. FSRS
subaward data is served only by `api.usaspending.gov`'s
`/api/v2/bulk_download/awards/` with `sub_award_types`, which is the blocked
host. The job stays queued in the api lock.

Every object carries the SAME stamp, 20260706 (max LastModified
2026-07-10T15:38:11Z). There is nothing newer than 20260706 to probe for; the
probe was run and is recorded rather than assumed.

THE POPULATION SEAM - THE THING THAT WOULD SILENTLY CORRUPT THE SERIES
----------------------------------------------------------------------
`federal_funding_transactions.csv` FY2008-FY2023 is NOT full-universe
assistance. Measured over all 476,924 existing rows, USAspending's
`business_types_code` takes exactly three values - I, K, J - i.e. Recipient Type
= "Indian/Native American Tribal Government". The archive files are
FULL UNIVERSE.

Filtering the archive on ledger identifiers ALONE would silently change what the
series counts: it would add ledger-known corporations that carry no tribal
recipient-type code, and drop tribal-coded recipients whose UEI the ledger has
never seen. Nothing in a total, a count or a date range would reveal it.

So this script keeps a row under a UNION of two legs and records which one on
every row in `population_basis`:

    recipient_type   business_types_code contains I, J or K
                     -> reproduces the EXISTING FY2008-2023 population exactly
    ledger_uei       recipient_uei is a tier A/B identifier in
                     cedar_identifier_ledger_final.csv
                     -> the additive Cedar Press leg
    both             both legs fire

A subscriber can reproduce the old series by filtering
`population_basis != 'ledger_uei'`, or take the wider one. The seam is a column,
never a silent adjustment.

**Identifier join only. No name matching.** These are multi-million-row files
and name matching on them is precisely what the containment defect
(AGENTS.md) punishes.

MONEY RULES - MEASURED IN docs/DATA_ODDITIES.md, NOT RE-DERIVED HERE
---------------------------------------------------------------------
* Negative `obligated_usd` is a DEOBLIGATION and belongs in totals (5.3% of
  assistance rows). Zero is an action that moved no money (11.7%). Blank is not
  zero.
* Assistance types 07 (direct loan), 08 (guaranteed/insured loan) and 09
  (insurance) report `federal_action_obligation` as exactly 0.00 BY DESIGN.
  Their money is in `face_value_of_loan` and `original_loan_subsidy_cost`.
  **A loan guarantee is not federal outlay**: face value is the borrower's
  principal, subsidy cost is what it costs the government. This script writes
  them into their OWN columns and never adds either to `obligated_usd`.
* `total_face_value_of_loan` is AWARD-CUMULATIVE and SIGNED. Six rows once
  summed to $271.4M against a true $171.4M. It is carried per row as a snapshot
  and must never be summed across transactions.
* `_real2025` comes from data/clean/inflation_deflator.csv (BEA NIPA 1.1.9,
  2025 base). No second deflator. FY2026 has no factor because 2026 is not a
  complete year - the column is left blank rather than forecast.

GUARDRAILS
----------
* HTTP status AND archive magic bytes are both checked. A 404 body saved under
  a .zip name passes a size test and fails only on read.
* Members are STREAMED (`zipfile.open` -> TextIOWrapper). Nothing is loaded
  whole; the FY2020 assistance object is 3.2 GB compressed.
* Disk is tight (15.2 GB free at start). Each zip is deleted after its rows are
  extracted; its url, HTTP status, byte count and md5 are recorded in
  `_SOURCE_MANIFEST.csv` so the fetch stays reproducible, and the filtered
  extract - full source schema, no columns dropped - is retained as the raw
  artefact.
* Never `taskkill /F /IM python.exe`. Enumerate with Win32_Process, kill by PID.

Run:
    py -3 code/115_pull_assistance_archive.py enumerate
    py -3 code/115_pull_assistance_archive.py fetch 2024 2025 2026
    py -3 code/115_pull_assistance_archive.py fetch 2008..2023      # credit backfill
    py -3 code/115_pull_assistance_archive.py append
    py -3 code/115_pull_assistance_archive.py codebook
"""

import csv
import hashlib
import io
import json
import os
import re
import shutil
import sys
import time
import urllib.parse
import zipfile
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

import requests

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
LOGS = CEDAR / "logs"
RAW = CEDAR / "data" / "raw" / "usaspending_archive_2026-08-07"
ZIPS = RAW / "_zips"
EXTRACT = RAW / "assistance_filtered"
LEDGER = CLEAN / "cedar_identifier_ledger_final.csv"
LOCK = LOGS / "_HOSTLOCK_files.usaspending.gov.json"
MANIFEST = RAW / "_SOURCE_MANIFEST.csv"
TODAY = date.today().isoformat()

HOST = "files.usaspending.gov"
BASE = f"https://{HOST}/award_data_archive/"
UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/126.0.0.0 Safari/537.36")}
# STAMP bumped 20260706 -> 20260806 on 2026-08-12. The archive REPLACES its
# objects monthly rather than accumulating them: a full re-enumeration on
# 2026-08-12 returned 4,597 keys, every one stamped 20260806 and NOT ONE
# stamped 20260706, and `FY2016_All_Contracts_Full_20260706.zip` now answers a
# real HTTP 404 in 0.5s. The July objects this build's first half read are gone
# from the host.
#
# Safe to bump globally HERE, unlike in script 114: `fetch_year` skips any year
# whose extract already exists, so FY2007/2024/2025/2026 are never re-read, and
# each row carries the stamp it was written with in `source_archive_stamp` -
# the July rows keep saying 20260706. `append()` dedupes on
# `assistance_transaction_unique_key`, which is stamp-independent, so a vintage
# change cannot produce a double-append.
STAMP = "20260806"
ZIP_MAGIC = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
TRIBAL_BUSINESS_TYPES = ("I", "J", "K")
CREDIT_TYPES = ("07", "08", "09")

for d in (RAW, ZIPS, EXTRACT, REVIEW, LOGS):
    d.mkdir(parents=True, exist_ok=True)

LOGPATH = LOGS / "115_assistance_archive.log"
_logf = open(LOGPATH, "a", encoding="utf-8")


def log(msg):
    line = f"[{datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ}] {msg}"
    print(line, flush=True)
    _logf.write(line + "\n")
    _logf.flush()


# ---------------------------------------------------------------------------
# 0. host lock. One poller per host (docs/PULL_DISCIPLINE.md rule 1).
#    We hold files.usaspending.gov; we must never reach for api.usaspending.gov.
# ---------------------------------------------------------------------------
def touch_lock(**kw):
    try:
        d = json.loads(LOCK.read_text(encoding="utf-8")) if LOCK.exists() else {}
    except Exception:                                            # noqa: BLE001
        d = {}
    d["host"] = HOST
    d["last_updated"] = f"{datetime.now(timezone.utc):%Y-%m-%dT%H:%MZ}"
    d.update(kw)
    LOCK.write_text(json.dumps(d, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. enumerate. The listing is ListObjects v1: MaxKeys 1000, IsTruncated, and
#    pagination by `marker`. (`list-type=2` + `continuation-token` is the v2
#    form; this endpoint answers v1, so the marker form is what actually
#    paginates. Recorded because the difference is invisible until page 2.)
# ---------------------------------------------------------------------------
KEY_RE = re.compile(r"<Key>(.*?)</Key>.*?<LastModified>(.*?)</LastModified>"
                    r".*?<Size>(\d+)</Size>", re.S)


def _listing_get(url, tries=5):
    """One listing page, with a bounded backoff.

    A SINGLE DROPPED CONNECTION MUST NOT KILL THE ENUMERATION (2026-08-12)
    ---------------------------------------------------------------------
    `enumerate_archive` had no retry at all: one bare `requests.get`, and any
    transport failure propagated straight out of `main()` as a traceback.
    Measured today - page 0 raised `RemoteDisconnected`, the whole command
    died, and a single timed re-probe 90 seconds later answered **HTTP 200 in
    1.46s**. So the host was fine and the enumeration was lost to one dropped
    connection.

    That is worse here than anywhere else in this script, because the
    enumeration is what establishes the CURRENT STAMP. Without it the only
    remaining source of a stamp is the hardcoded constant - which is precisely
    the thing the stamp roll proved you cannot trust. A crashed enumerator
    silently forces every caller back onto a pinned stamp.

    Only 404/403 are facts about the object. A 5xx, a 429 or a transport
    failure is a fact about the moment, so they back off; a 404 does not.
    """
    delay = 30
    for attempt in range(tries):
        t0 = time.time()
        try:
            r = requests.get(url, headers=UA, timeout=(15, 180))
            if r.status_code in (404, 403):
                return r
            if r.status_code == 200:
                return r
            log(f"  listing HTTP {r.status_code} in {time.time()-t0:.2f}s "
                f"- a fact about the host, not the listing; "
                f"attempt {attempt+1}/{tries}")
        except requests.exceptions.RequestException as e:
            log(f"  listing transport failure in {time.time()-t0:.2f}s: "
                f"{type(e).__name__} - attempt {attempt+1}/{tries}")
        if attempt < tries - 1:
            log(f"  backing off {delay}s")
            time.sleep(delay)
            delay = min(delay * 2, 900)
    raise SystemExit("listing failed after a full backoff - the HOST is "
                     "refusing. This is NOT evidence about what the archive "
                     "publishes. Retry later.")


def enumerate_archive():
    touch_lock(current_action="enumerate")
    keys, marker = [], ""
    for page in range(40):
        url = BASE + (f"?marker={urllib.parse.quote(marker)}" if marker else "")
        r = _listing_get(url)
        log(f"listing page {page}: HTTP {r.status_code}, {len(r.text):,} bytes")
        if r.status_code != 200:
            raise SystemExit(f"listing failed HTTP {r.status_code}")
        found = KEY_RE.findall(r.text)
        keys += [{"key": k, "last_modified": lm, "size": int(sz)}
                 for k, lm, sz in found]
        if "<IsTruncated>true</IsTruncated>" not in r.text:
            break
        nm = re.search(r"<NextMarker>(.*?)</NextMarker>", r.text)
        marker = nm.group(1) if nm else found[-1][0]
        time.sleep(2)

    p = RAW / "_archive_listing.csv"
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["key", "last_modified", "size"])
        w.writeheader()
        w.writerows(keys)

    shapes = Counter(re.sub(r"\d", "#", k["key"]) for k in keys)
    stamps = Counter(m.group(1) for m in
                     (re.search(r"_(\d{8})\.zip$", k["key"]) for k in keys) if m)
    subs = [k for k in keys if "sub" in k["key"].lower()]
    log(f"{len(keys):,} objects, {len(shapes)} filename shapes, "
        f"stamps={dict(stamps)}")
    log(f"objects whose key contains 'sub': {len(subs)}  "
        f"<- 0 means the archive publishes NO subaward file")
    for s, n in shapes.most_common():
        log(f"   {n:5d}  {s}")

    newest = max(stamps) if stamps else None
    if newest and newest > STAMP:
        log(f"!! a stamp NEWER than {STAMP} exists: {newest}. Update STAMP.")
    else:
        log(f"no stamp newer than {STAMP} exists on this host (probed, not assumed)")
    touch_lock(current_action=None,
               enumerated={"objects": len(keys), "stamps": dict(stamps),
                           "subaward_objects": len(subs),
                           "probed_utc": f"{datetime.now(timezone.utc):%Y-%m-%dT%H:%MZ}"})
    return keys


# ---------------------------------------------------------------------------
# 2. ledger
# ---------------------------------------------------------------------------
def load_ledger():
    order = {"A": 0, "B": 1, "C": 2, "X": 3}
    by_uei = {}
    with open(LEDGER, encoding="utf-8-sig", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            if (r.get("identifier_type") or "").strip().upper() != "UEI":
                continue
            u = (r.get("identifier") or "").strip().upper()
            if not u:
                continue
            t = (r.get("confidence_tier") or "").strip().upper()
            prev = by_uei.get(u)
            if prev is None or order.get(t, 9) < order.get(prev["tier"], 9):
                by_uei[u] = {"tier": t,
                             "tribe_id": (r.get("tribe_id") or "").strip(),
                             "canonical_name": (r.get("canonical_name") or "").strip()}
    return by_uei


def load_deflator():
    d = {}
    p = CLEAN / "inflation_deflator.csv"
    with open(p, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            d[int(r["year"])] = float(r["factor_to_base"])
    return d


# ---------------------------------------------------------------------------
# 3. fetch + stream-filter one fiscal year
# ---------------------------------------------------------------------------
def manifest_append(row):
    fields = ["fetched_utc", "url", "http_status", "bytes", "md5",
              "content_type", "magic_ok", "members", "kept_rows",
              "scanned_rows", "zip_retained", "note"]
    new = not MANIFEST.exists()
    with open(MANIFEST, "a", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in fields})


def _download_once(url, dest):
    """One GET, streamed to disk, verified on length as well as magic bytes.

    A STALLED STREAM IS A THIRD FAILURE SHAPE (measured 2026-08-12)
    --------------------------------------------------------------
    `timeout=1800` reads as "give up after 30 minutes" and does not mean that.
    In requests it is the *read* timeout - the maximum gap between two chunks -
    so a connection the host has quietly stopped feeding sits here for a full
    30 minutes per attempt, six attempts deep, and eats the entire 2h
    RUN_DEADLINE without issuing a single useful request. Measured on FY2011:
    the stream died at **exactly 20,971,520 bytes** (20 MB, a round number,
    which is the shape of a server-side cutoff rather than a network drop) and
    the process then sat motionless.

    This is neither of the two failure shapes `download()` knows about. It is
    not a refusal - the request was accepted and served 200 - and it is not a
    slow server, because no bytes are arriving at all. A 2-minute silence on a
    CDN that had just been delivering 40 MB/s is a dead socket, so that is what
    the read timeout now says.

    And the length is now checked. A truncated object still starts with PK, so
    the magic-byte test passes on a file that is half an archive; only the
    central-directory read downstream would have caught it, and reporting it
    there as "not a zip" would have blamed the object for a transport failure.
    """
    h = hashlib.md5()
    n = 0
    # (connect, read). Read gap, NOT total download time - a 900 MB object may
    # legitimately take many minutes so long as bytes keep arriving.
    with requests.get(url, headers=UA, timeout=(30, 120), stream=True) as r:
        status = r.status_code
        ctype = r.headers.get("Content-Type", "")
        if status != 200:
            return status, 0, "", ctype, False
        expect = int(r.headers.get("Content-Length") or 0)
        with open(dest, "wb") as fh:
            for chunk in r.iter_content(1 << 22):
                if chunk:
                    fh.write(chunk)
                    h.update(chunk)
                    n += len(chunk)
    if expect and n != expect:
        # Raise rather than return: this is a transport failure, so it belongs
        # on the retry path with the connection errors, not on the "the host
        # answered and here is what it said" path.
        raise IOError(
            f"TRUNCATED: received {n:,} of {expect:,} bytes ({n/expect*100:.1f}%). "
            "The stream ended early. This is a transport failure, NOT a "
            "statement that the object is short or malformed.")
    with open(dest, "rb") as fh:
        head = fh.read(4)
    return status, n, h.hexdigest(), ctype, head in ZIP_MAGIC or head[:2] == b"PK"


# MEASURED 2026-08-08T00:55Z: after six large objects in twelve minutes with a
# 15s pause between them, this host began answering HTTP 500 in under a second
# and then closing the connection without a response. Both are EDGE-BLOCK
# signatures (docs/PULL_DISCIPLINE.md), not "the object is missing" - the
# listing proves FY2008 and FY2009 exist. A refusal recorded here is therefore
# a fact about the HOST, and the year must be retried, never written off.
#
# Backoff is exponential, 60s doubling to 30 min, and the inter-object pause is
# long. To an edge filter a metronome looks exactly like the traffic that earned
# the block.
#
# AND IT IS BOUNDED. docs/PULL_DISCIPLINE.md: back off exponentially, "stop at
# ~2h". Without a global deadline this loop would grind 16 years x 6 attempts
# against a host that is refusing, which is the runaway the discipline exists to
# prevent - a blocked host does not become less blocked by being asked more
# often. Two independent stops:
#
#   RUN_DEADLINE          no attempt starts more than MAX_RUN_SECONDS after the
#                         run began.
#   stop-on-first-failure a year that exhausts its backoff while NO year has
#                         succeeded in this run means the HOST is refusing, not
#                         that one object is bad. Trying the next 15 years is
#                         just 15 more ways to learn the same fact.
MAX_RUN_SECONDS = 2 * 60 * 60
RUN_DEADLINE = None          # set by fetch()


def _deadline_passed():
    return RUN_DEADLINE is not None and time.time() > RUN_DEADLINE


def download(url, dest, tries=6):
    delay, last = 60, None
    for k in range(tries):
        if _deadline_passed():
            log(f"  STOP: {MAX_RUN_SECONDS//3600}h run deadline reached. "
                f"A blocked host is a finding, not something to out-wait with "
                f"more requests.")
            return 0, 0, "", "", False
        t0 = time.time()
        try:
            out = _download_once(url, dest)
            if out[0] == 200 and out[4]:
                return out
            last = f"HTTP {out[0]}"
            if out[0] == 429:
                last += " (throttle)"
        except Exception as e:                                   # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
        fast = time.time() - t0 < 2
        log(f"  attempt {k+1}/{tries}: {last}"
            + ("   <-- sub-second failure = EDGE BLOCK, not a slow server"
               if fast else ""))
        if k == tries - 1:
            break
        if _deadline_passed():
            continue
        log(f"  backing off {delay}s")
        time.sleep(delay)
        delay = min(delay * 2, 1800)
    return 0, 0, "", "", False


COLMAP_CANDIDATES = {
    "tx_key": ["assistance_transaction_unique_key"],
    "award_key": ["assistance_award_unique_key"],
    "fain": ["award_id_fain", "fain"],
    "action_date": ["action_date"],
    "fy": ["action_date_fiscal_year", "fiscal_year"],
    "obl": ["federal_action_obligation"],
    "face": ["face_value_of_loan", "face_value_loan_guarantee"],
    "subsidy": ["original_loan_subsidy_cost"],
    "total_face": ["total_face_value_of_loan", "total_face_value_loan_guarantee"],
    "total_subsidy": ["total_loan_subsidy_cost", "original_loan_subsidy_cost_amount"],
    "atype": ["assistance_type_code"],
    "atype_desc": ["assistance_type_description"],
    "cfda": ["assistance_listing_number", "cfda_number"],
    "cfda_title": ["assistance_listing_title", "cfda_title"],
    "agency": ["awarding_agency_name"],
    "subagency": ["awarding_sub_agency_name"],
    "uei": ["recipient_uei"],
    "duns": ["recipient_duns"],
    "name": ["recipient_name"],
    "city": ["recipient_city_name"],
    "state": ["recipient_state_code"],
    "btypes": ["business_types_code"],
    "btypes_desc": ["business_types_description"],
}


def resolve_cols(fieldnames):
    lower = {c.lower(): c for c in fieldnames}
    out = {}
    for k, cands in COLMAP_CANDIDATES.items():
        for c in cands:
            if c in lower:
                out[k] = lower[c]
                break
    return out


OUT_FIELDS = [
    # source-schema facts
    "assistance_transaction_unique_key", "assistance_award_unique_key",
    "award_id_fain", "action_date", "fiscal_year", "fy_partial_flag",
    "obligated_usd", "face_value_of_loan", "original_loan_subsidy_cost",
    "total_face_value_of_loan", "total_loan_subsidy_cost",
    "assistance_type", "assistance_type_description",
    "credit_instrument_flag",
    "cfda", "cfda_title", "awarding_agency_name", "awarding_sub_agency_name",
    "recipient_uei", "recipient_duns", "recipient_name",
    "recipient_city_name", "recipient_state_code",
    "business_types_code", "business_types_description",
    # cedar attribution
    "tribe_id", "canonical_name", "attribution_method", "confidence_tier",
    "attributed_flag", "excluded_flag",
    # provenance / population
    "population_basis", "source_file", "source_archive_stamp", "fetched_date",
]


def fy_url(year):
    return f"{BASE}FY{year}_All_Assistance_Full_{STAMP}.zip"


ARCHIVE_LISTING = (CEDAR / "data" / "raw" / "contracts"
                   / "archive_listing_2026-08-12.csv")

# Free space to leave BEYOND the object being fetched, so a concurrent agent's
# write does not fail because of this pull. Overridable with --headroom because
# the right value depends on what else is running, and the per-agency fallback
# it gates costs 112 requests instead of 1 - an expensive thing to trigger on a
# margin that is merely cautious rather than necessary.
HEADROOM_GB = 1.2


def objects_for_year(year, headroom_gb=1.2):
    """Which archive objects to read for one FY, and why.

    THE `_All_` OBJECT IS NOT THE ONLY ROUTE TO A FULL YEAR (2026-08-12)
    -------------------------------------------------------------------
    The archive publishes each fiscal year twice: once as a single
    `FY####_All_Assistance_Full_` object, and once as ~112 per-AGENCY objects
    `FY####_<3-digit agency>_Assistance_Full_`. The union of the agency objects
    is the same universe as the `_All_` object - it is the same extract, cut by
    awarding agency instead of served whole.

    That matters because this machine ran out of disk, not out of source.
    FY2020's `_All_` object is **3.15 GB** against **1.5 GB free**, so the
    complete-year route was unavailable for a purely local reason. Recorded
    naively that would have read as "FY2020 could not be obtained", which is
    the same category error as reading a block as an absence: the object was
    there and the host was serving it.

    Cut by agency the same year is 112 objects totalling 3.06 GB whose
    LARGEST member is 1.99 GB, so peak disk is one object rather than the
    whole year. Slower and more requests, but it fits, and it is the same data.

    Sizes come from the saved bucket listing, so this decision is made against
    measured bytes rather than a guess.
    """
    all_name = f"FY{year}_All_Assistance_Full_{STAMP}.zip"
    sizes = {}
    if ARCHIVE_LISTING.exists():
        with open(ARCHIVE_LISTING, encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                sizes[r["key"]] = int(r["size_bytes"] or 0)
    all_bytes = sizes.get(all_name, 0)
    free = shutil.disk_usage(str(CEDAR)).free / 1e9
    if not all_bytes or all_bytes / 1e9 + headroom_gb <= free:
        return [(BASE + all_name, all_name, "all")]

    pat = re.compile(rf"FY{year}_\d+_Assistance_Full_{STAMP}\.zip$")
    parts = sorted(k for k in sizes if pat.match(k))
    if not parts:
        log(f"FY{year}: {all_bytes/1e9:.2f} GB object vs {free:.2f} GB free, "
            "and no per-agency objects are listed. Cannot proceed on disk.")
        return []
    biggest = max(sizes[k] for k in parts)
    log(f"FY{year}: the _All_ object is {all_bytes/1e9:.2f} GB but only "
        f"{free:.2f} GB is free. Falling back to {len(parts)} PER-AGENCY "
        f"objects ({sum(sizes[k] for k in parts)/1e9:.2f} GB total, largest "
        f"{biggest/1e9:.2f} GB) - same universe, one object on disk at a time. "
        "This is a LOCAL DISK constraint, not a host refusal and not absence.")
    if biggest / 1e9 + headroom_gb > free:
        log(f"FY{year}: WARNING - even the largest per-agency object "
            f"({biggest/1e9:.2f} GB) may not fit in {free:.2f} GB.")
    return [(BASE + k, k, "agency") for k in parts]


def fetch_year(year, by_uei, keep_zip=False):
    """Download one FY assistance object, stream-filter it, write the extract.

    Returns "skip" if the extract already exists, True on success, False if the
    host refused it after a full backoff.
    """
    outp = EXTRACT / f"FY{year}_assistance_filtered.csv"
    # A PARTIAL EXTRACT MUST NEVER BE SKIPPABLE (measured 2026-08-12)
    # ---------------------------------------------------------------
    # The extract was written straight to its final name, and the skip above
    # is a bare `exists()`. So any interruption between the first row and the
    # last - a stalled download, a kill, a full disk - left a partial file at
    # the path that means "this year is done", and every later run skipped it.
    # Measured: FY2011 stalled mid-download, and a 126,628-byte extract was
    # left behind next to ~20 MB neighbours. Nothing would ever have looked at
    # it again; the year would simply have been ~1% complete forever, and the
    # row count would have looked like a real fact about FY2011.
    #
    # This is the same shape as "a block must not look like an absence",
    # one layer down: an INTERRUPTION must not look like a COMPLETION.
    # Script 114 already writes `.part` and renames; this now does too.
    part = EXTRACT / f"FY{year}_assistance_filtered.csv.part"
    if part.exists():
        log(f"FY{year}: discarding {part.stat().st_size:,}-byte partial "
            "extract from an interrupted run")
        part.unlink()
    if outp.exists():
        log(f"FY{year}: extract already on disk -- skip")
        return "skip"

    touch_lock(current_action=f"fetch FY{year}")
    objects = objects_for_year(year, headroom_gb=HEADROOM_GB)
    if not objects:
        return False
    nbytes_total = 0
    kept = scanned = 0
    stats = Counter()
    by_type = defaultdict(Counter)
    unresolved = defaultdict(lambda: [0, 0.0, ""])
    members = []

    with open(part, "w", encoding="utf-8", newline="") as ofh:
        w = csv.DictWriter(ofh, fieldnames=OUT_FIELDS)
        w.writeheader()
        for oi, (url, zname, cut) in enumerate(objects):
            zp = ZIPS / zname
            # The 2026-08-08 block came from SIX large objects in twelve
            # minutes. The per-agency route trades one big request for 112
            # small ones, and 112 back-to-back requests is the OTHER shape an
            # edge filter reacts to. So objects within a year are paced as
            # well - the 180s between-years pause does not cover them.
            if oi:
                time.sleep(8)
            log(f"FY{year}: GET {url}  [{oi+1}/{len(objects)}]")
            status, nbytes, md5, ctype, magic = download(url, zp)
            if status != 200 or not magic:
                manifest_append({"fetched_utc": f"{datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ}",
                                 "url": url, "http_status": status, "bytes": nbytes,
                                 "md5": md5, "content_type": ctype,
                                 "magic_ok": int(bool(magic)), "members": "",
                                 "kept_rows": 0, "scanned_rows": 0, "zip_retained": 0,
                                 "note": ("REFUSED after full backoff - not HTTP 200 or "
                                          "not a zip archive. The object IS in the "
                                          "listing, so this is a HOST refusal, not a "
                                          "missing file. RETRY LATER; do not write the "
                                          "year off.")})
                if zp.exists():
                    zp.unlink()
                log(f"FY{year}: REFUSED after backoff (status={status}, "
                    f"magic_ok={magic}). The listing contains this object, so this is a "
                    f"host refusal, NOT absence. A 404 page saved under a .zip name "
                    f"passes a size test, which is why magic bytes are checked.")
                return False
            nbytes_total += nbytes
            log(f"FY{year}: {zname} {nbytes/1e6:,.1f} MB, md5={md5}, magic ok")

            with zipfile.ZipFile(zp) as z:
                mem_names = [m for m in z.namelist() if m.lower().endswith(".csv")]
                members += mem_names
                for mem in mem_names:
                    # STREAM. The FY2020 object is 3.2 GB compressed; nothing here
                    # may call .read() on a whole member.
                    with z.open(mem) as raw:
                        txt = io.TextIOWrapper(raw, encoding="utf-8",
                                               errors="replace", newline="")
                        rd = csv.DictReader(txt)
                        cols = resolve_cols(rd.fieldnames or [])
                        missing = [k for k in ("uei", "obl", "atype", "btypes")
                                   if k not in cols]
                        if missing:
                            log(f"  !! {mem}: schema missing {missing}; "
                                f"first cols {(rd.fieldnames or [])[:12]}")
                        for r in rd:
                            scanned += 1
                            bt = (r.get(cols.get("btypes", ""), "") or "").upper()
                            uei = (r.get(cols.get("uei", ""), "") or "").strip().upper()
                            hit = by_uei.get(uei) if uei else None
                            leg_type = any(c in bt for c in TRIBAL_BUSINESS_TYPES)
                            leg_led = bool(hit and hit["tier"] in ("A", "B"))
                            if not (leg_type or leg_led):
                                continue
                            kept += 1
                            basis = ("both" if leg_type and leg_led else
                                     "recipient_type" if leg_type else "ledger_uei")
                            stats[basis] += 1

                            atype = (r.get(cols.get("atype", ""), "") or "").strip()
                            credit = int(atype in CREDIT_TYPES)
                            obl = r.get(cols.get("obl", ""), "")
                            face = r.get(cols.get("face", ""), "") if "face" in cols else ""
                            subs = r.get(cols.get("subsidy", ""), "") if "subsidy" in cols else ""
                            by_type[atype]["rows"] += 1
                            by_type[atype]["obl"] += _num(obl)
                            by_type[atype]["face"] += _num(face)
                            by_type[atype]["subsidy"] += _num(subs)
                            if credit:
                                stats["credit_rows"] += 1
                                if _num(obl):
                                    stats["credit_rows_with_NONZERO_obligation"] += 1

                            if hit and hit["tier"] in ("A", "B"):
                                tid, canon = hit["tribe_id"], hit["canonical_name"]
                                tier, meth, attributed, excluded = hit["tier"], "uei_exact_archive", 1, 0
                            elif hit and hit["tier"] == "X":
                                tid = canon = ""
                                tier, meth, attributed, excluded = "X", "ledger_exclusion", 0, 1
                                stats["ledger_tier_X_excluded"] += 1
                            else:
                                tid = canon = ""
                                tier, meth, attributed, excluded = "", "unattributed", 0, 0
                                if leg_type:
                                    k = uei or f"[BLANK UEI] {r.get(cols.get('name',''),'')}"
                                    unresolved[k][0] += 1
                                    unresolved[k][1] += _num(obl)
                                    unresolved[k][2] = r.get(cols.get("name", ""), "")

                            w.writerow({
                                "assistance_transaction_unique_key": r.get(cols.get("tx_key", ""), ""),
                                "assistance_award_unique_key": r.get(cols.get("award_key", ""), ""),
                                "award_id_fain": r.get(cols.get("fain", ""), ""),
                                "action_date": r.get(cols.get("action_date", ""), ""),
                                "fiscal_year": r.get(cols.get("fy", ""), "") or year,
                                "fy_partial_flag": int(year >= 2026),
                                "obligated_usd": obl,
                                "face_value_of_loan": face,
                                "original_loan_subsidy_cost": subs,
                                "total_face_value_of_loan":
                                    r.get(cols.get("total_face", ""), "") if "total_face" in cols else "",
                                "total_loan_subsidy_cost":
                                    r.get(cols.get("total_subsidy", ""), "") if "total_subsidy" in cols else "",
                                "assistance_type": atype,
                                "assistance_type_description": r.get(cols.get("atype_desc", ""), ""),
                                "credit_instrument_flag": credit,
                                "cfda": r.get(cols.get("cfda", ""), ""),
                                "cfda_title": r.get(cols.get("cfda_title", ""), ""),
                                "awarding_agency_name": r.get(cols.get("agency", ""), ""),
                                "awarding_sub_agency_name": r.get(cols.get("subagency", ""), ""),
                                "recipient_uei": uei,
                                "recipient_duns": r.get(cols.get("duns", ""), "") if "duns" in cols else "",
                                "recipient_name": r.get(cols.get("name", ""), ""),
                                "recipient_city_name": r.get(cols.get("city", ""), ""),
                                "recipient_state_code": r.get(cols.get("state", ""), ""),
                                "business_types_code": bt,
                                "business_types_description": r.get(cols.get("btypes_desc", ""), ""),
                                "tribe_id": tid,
                                "canonical_name": canon,
                                "attribution_method": meth,
                                "confidence_tier": tier,
                                "attributed_flag": attributed,
                                "excluded_flag": excluded,
                                "population_basis": basis,
                                "source_file": zp.name,
                                "source_archive_stamp": STAMP,
                                "fetched_date": TODAY,
                            })

            # Release each object the moment its rows are consumed. The
            # per-agency route exists to keep peak disk at ONE object, and
            # holding them would defeat that. Identity stays provable:
            # url + bytes + md5 are in _SOURCE_MANIFEST.csv.
            if not keep_zip:
                zp.unlink(missing_ok=True)

    # Every member was streamed to the end without raising, so the extract is
    # complete. ONLY NOW does it take the name that means "this year is done".
    part.replace(outp)

    zip_retained = 0
    if keep_zip:
        zip_retained = 1
    else:
        zp.unlink(missing_ok=True)

    manifest_append({
        "fetched_utc": f"{datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ}",
        "url": url, "http_status": status, "bytes": nbytes, "md5": md5,
        "content_type": ctype, "magic_ok": 1, "members": "|".join(members),
        "kept_rows": kept, "scanned_rows": scanned, "zip_retained": zip_retained,
        "note": ("zip deleted after streaming; md5 + byte count preserve "
                 "reproducibility, filtered extract retained at full source "
                 "schema" if not zip_retained else "zip retained"),
    })

    json.dump({"year": year, "scanned": scanned, "kept": kept,
               "population_basis": dict(stats),
               "by_assistance_type": {k: dict(v) for k, v in by_type.items()}},
              open(EXTRACT / f"FY{year}_stats.json", "w", encoding="utf-8"),
              indent=2)

    with open(EXTRACT / f"FY{year}_unresolved.csv", "w", encoding="utf-8",
              newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["recipient_uei", "recipient_name", "rows", "obligated_usd"])
        for k, v in sorted(unresolved.items(), key=lambda kv: -abs(kv[1][1])):
            w.writerow([k, v[2], v[0], round(v[1], 2)])

    log(f"FY{year}: scanned {scanned:,}, kept {kept:,}  {dict(stats)}")
    log(f"FY{year}: unresolved recipient-type UEIs: {len(unresolved):,}")
    # 15s was measured to be too fast: six objects at that pace earned an edge
    # block. A contracts agent shares this host, so the pause is theirs too.
    time.sleep(180)
    return True


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


# ---------------------------------------------------------------------------
# 4. append into the clean file
#
#    The clean file gains COLUMNS it never had (source_file, the two credit
#    money columns, the real2025 pair, population_basis). Adding a column is a
#    header change, so the file is rewritten - but EVERY EXISTING ROW KEEPS
#    EVERY EXISTING VALUE UNCHANGED and the new columns are appended at the end.
#    No existing row is edited, reordered or dropped. The file is re-read
#    immediately before writing and swapped in atomically so a concurrent agent
#    cannot be clobbered mid-write.
# ---------------------------------------------------------------------------
NEW_COLS = ["face_value_of_loan", "original_loan_subsidy_cost",
            "total_face_value_of_loan", "total_loan_subsidy_cost",
            "credit_instrument_flag", "business_types_code",
            "business_types_description",
            "obligated_usd_real2025", "deflator_factor_2025",
            "inflation_base_year", "population_basis",
            "state_agreement", "ledger_proposed_tribe_id",
            "source_file", "source_archive_stamp", "fetched_date"]


# ---------------------------------------------------------------------------
# THE STATE-AGREEMENT GUARD - added mid-build, because the first FY2024 extract
# proved it was needed.
#
# The identifier ledger's UEI leg proposes attributions that are wrong in the
# exact way AGENTS.md documents, and they are not small:
#
#   SANTA CLARA COUNTY HOUSING AUTHORITY (CA) -> Pueblo of Santa Clara (NM)
#       $535,577,279 over 152 FY2024 rows
#   SANTA ANA, CITY OF (CA)              -> Pueblo of Santa Ana (NM)     $68.1M
#   HOUSING AUTHORITY OF THE CITY OF OMAHA (NE) -> Omaha Tribe            $60.1M
#   MANCHESTER HOUSING & REDEVELOPMENT AUTHORITY (NH) -> "Manchester"     $36.9M
#   PEORIA HOUSING AUTH (IL)             -> Peoria Tribe of Oklahoma      $20.5M
#
# Every one is a short-name collision of the kind AGENTS.md records 161 of in
# the spine, and every one would have shipped as Native federal funding.
#
# AGENTS.md names the guard that works: "require a state agreement". This is
# NOT name matching and it is NOT used to DETECT a match - it is used to REFUSE
# one the ledger already proposed, which is the only direction that file permits.
#
# It is applied ASYMMETRICALLY, on purpose:
#   * where the ledger UEI is the ONLY evidence (population_basis ledger_uei),
#     a state disagreement WITHHOLDS the attribution. The row is kept, the
#     proposed entity is preserved in `ledger_proposed_tribe_id` so the ruling
#     is auditable, and the dollars go to the review queue.
#   * where USAspending independently codes the recipient as a tribal
#     government or tribally designated organisation (population_basis `both`),
#     the disagreement is RECORDED in `state_agreement` and nothing is
#     withheld. Tribes operate across state lines and a second, independent
#     federal leg is real evidence.
# ---------------------------------------------------------------------------
def load_spine_states():
    p = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"
    out = {}
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            out[(r.get("tribe_id") or "").strip()] = (r.get("state") or "").strip().upper()
    return out


def append():
    defl = load_deflator()
    spine_state = load_spine_states()
    target = CLEAN / "federal_funding_transactions.csv"

    extracts = sorted(EXTRACT.glob("FY*_assistance_filtered.csv"))
    if not extracts:
        raise SystemExit("no extracts - run `fetch` first")

    # Re-read the target IMMEDIATELY before writing, and STREAM it - existing
    # plus added is well over a million rows and holding them as dicts is
    # gigabytes for no reason.
    with open(target, encoding="utf-8-sig", errors="replace", newline="") as fh:
        base_fields = list(csv.DictReader(fh).fieldnames)
    fields = base_fields + [c for c in NEW_COLS if c not in base_fields]

    have_keys = set()
    ents_before = set()
    n_existing = 0
    added = dupes = 0
    fy_type = defaultdict(Counter)
    fy_money = defaultdict(Counter)
    ents_new = set()
    unresolved = defaultdict(lambda: [0, 0.0, "", set()])
    withheld = defaultdict(lambda: [0, 0.0, None])

    tmp = target.with_suffix(".csv.tmp115")
    ofh = open(tmp, "w", encoding="utf-8", newline="")
    w = csv.DictWriter(ofh, fieldnames=fields, extrasaction="ignore")
    w.writeheader()

    # ---- pass 1: existing rows, values UNCHANGED, new columns appended -----
    with open(target, encoding="utf-8-sig", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            n_existing += 1
            have_keys.add(r.get("assistance_transaction_unique_key", ""))
            if (r.get("tribe_id") or "").strip():
                ents_before.add(r["tribe_id"])
            y = _int(r.get("fiscal_year"))
            f = defl.get(y)
            obl = _num(r.get("obligated_usd"))
            r["obligated_usd_real2025"] = round(obl * f, 2) if f else ""
            r["deflator_factor_2025"] = f if f else ""
            r["inflation_base_year"] = 2025 if f else ""
            r["population_basis"] = r.get("population_basis") or "recipient_type"
            r["source_file"] = r.get("source_file") or \
                "Assistance_PrimeTransactions_2023-04-09_H19M53S53_1.csv"
            w.writerow(r)
    log(f"existing clean rows carried through unchanged: {n_existing:,}")

    # ---- pass 2: archive extracts, appended -------------------------------
    for p in extracts:
        with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
            for r in csv.DictReader(fh):
                k = r.get("assistance_transaction_unique_key", "")
                if k and k in have_keys:
                    dupes += 1
                    continue
                have_keys.add(k)
                y = _int(r.get("fiscal_year"))
                f = defl.get(y)
                obl = _num(r.get("obligated_usd"))

                # ---- state-agreement guard (see the block above) ----------
                tid = (r.get("tribe_id") or "").strip()
                basis = r.get("population_basis", "")
                meth = r.get("attribution_method", "")
                attributed = r.get("attributed_flag", "")
                proposed = ""
                est = spine_state.get(tid, "")
                rst = (r.get("recipient_state_code") or "").strip().upper()
                if not tid:
                    agree = ""
                elif est and rst:
                    agree = "agree" if est == rst else "disagree"
                else:
                    agree = "unknown"
                if agree == "disagree" and basis == "ledger_uei":
                    proposed, tid = tid, ""
                    meth = "ledger_uei_state_disagreement_withheld"
                    attributed = 0
                    basis = "ledger_uei_withheld"
                    withheld[proposed + "|" + (r.get("recipient_uei") or "")][0] += 1
                    withheld[proposed + "|" + (r.get("recipient_uei") or "")][1] += obl
                    withheld[proposed + "|" + (r.get("recipient_uei") or "")][2] = \
                        (proposed, r.get("canonical_name", ""), est,
                         r.get("recipient_uei", ""), r.get("recipient_name", ""), rst)

                row = {c: "" for c in fields}
                row.update({
                    "assistance_transaction_unique_key": k,
                    "assistance_award_unique_key": r.get("assistance_award_unique_key", ""),
                    "award_id_fain": r.get("award_id_fain", ""),
                    "action_date": r.get("action_date", ""),
                    "fiscal_year": r.get("fiscal_year", ""),
                    "fy_partial_flag": r.get("fy_partial_flag", ""),
                    "obligated_usd": r.get("obligated_usd", ""),
                    "assistance_type": r.get("assistance_type", ""),
                    "assistance_type_description": r.get("assistance_type_description", ""),
                    "cfda": r.get("cfda", ""),
                    "cfda_title": r.get("cfda_title", ""),
                    "awarding_agency_name": r.get("awarding_agency_name", ""),
                    "awarding_sub_agency_name": r.get("awarding_sub_agency_name", ""),
                    "recipient_uei": r.get("recipient_uei", ""),
                    "recipient_duns": r.get("recipient_duns", ""),
                    "recipient_name": r.get("recipient_name", ""),
                    "recipient_city_name": r.get("recipient_city_name", ""),
                    "recipient_state_code": r.get("recipient_state_code", ""),
                    "tribe_id": tid,
                    "canonical_name": r.get("canonical_name", "") if not proposed else "",
                    "attribution_method": meth,
                    # tier X is preserved: it is an exclusion RULING, and
                    # erasing it would let the excluded entity resurface later
                    # as merely unknown. Only a WITHHELD tier is blanked.
                    "confidence_tier": r.get("confidence_tier", "") if not proposed else "",
                    "attributed_flag": attributed,
                    "excluded_flag": r.get("excluded_flag", ""),
                    "state_agreement": agree,
                    "ledger_proposed_tribe_id": proposed,
                    # the credit columns - NEVER pooled with obligated_usd
                    "face_value_of_loan": r.get("face_value_of_loan", ""),
                    "original_loan_subsidy_cost": r.get("original_loan_subsidy_cost", ""),
                    "total_face_value_of_loan": r.get("total_face_value_of_loan", ""),
                    "total_loan_subsidy_cost": r.get("total_loan_subsidy_cost", ""),
                    "credit_instrument_flag": r.get("credit_instrument_flag", ""),
                    "business_types_code": r.get("business_types_code", ""),
                    "business_types_description": r.get("business_types_description", ""),
                    "obligated_usd_real2025": round(obl * f, 2) if f else "",
                    "deflator_factor_2025": f if f else "",
                    "inflation_base_year": 2025 if f else "",
                    "population_basis": basis,
                    "source_file": r.get("source_file", ""),
                    "source_archive_stamp": r.get("source_archive_stamp", ""),
                    "fetched_date": r.get("fetched_date", ""),
                })
                w.writerow(row)
                added += 1
                fyy = r.get("fiscal_year", "")
                atype = r.get("assistance_type", "")
                fy_type[fyy][atype] += 1
                if r.get("credit_instrument_flag") == "1":
                    # THREE MONEY FIELDS, NEVER POOLED. obligation is the grant
                    # concept; face value is the borrower's principal; subsidy
                    # cost is the federal cost of the guarantee.
                    fy_money[fyy]["credit_rows"] += 1
                    fy_money[fyy]["credit_obligation"] += obl
                    fy_money[fyy]["credit_face_value"] += \
                        _num(r.get("face_value_of_loan"))
                    fy_money[fyy]["credit_subsidy_cost"] += \
                        _num(r.get("original_loan_subsidy_cost"))
                else:
                    fy_money[fyy]["grant_obligation"] += obl
                if row["tribe_id"]:
                    ents_new.add(row["tribe_id"])
                elif basis == "recipient_type":
                    u = r.get("recipient_uei", "")
                    unresolved[u][0] += 1
                    unresolved[u][1] += obl
                    unresolved[u][2] = r.get("recipient_name", "")
                    unresolved[u][3].add(fyy)

    ofh.close()
    tmp.replace(target)
    log(f"federal_funding_transactions.csv: {n_existing:,} -> "
        f"{n_existing + added:,} rows (+{added:,}); "
        f"{dupes:,} duplicate transaction keys skipped")

    print("\nrows added by FY x assistance_type")
    for y in sorted(fy_type):
        print(f"  FY{y}: {dict(sorted(fy_type[y].items()))}")

    print("\nmoney by FY - obligation and the two CREDIT columns, kept apart")
    print(f"{'FY':6s} {'grant_obl':>18s} {'cr_rows':>8s} {'cr_obl':>10s} "
          f"{'face_value':>18s} {'subsidy_cost':>16s}")
    for y in sorted(fy_money):
        c = fy_money[y]
        print(f"{y:6s} {c['grant_obligation']:>18,.2f} "
              f"{int(c['credit_rows']):>8,} {c['credit_obligation']:>10,.2f} "
              f"{c['credit_face_value']:>18,.2f} "
              f"{c['credit_subsidy_cost']:>16,.2f}")
    print("Face value is the BORROWER'S principal and subsidy cost is the "
          "government's cost. Neither is ever added to grant obligations.")

    newly = ents_new - ents_before
    print(f"\nentities newly reached: {len(newly)}")
    json.dump({"rows_added": added, "dupes_skipped": dupes,
               "rows_before": n_existing, "rows_after": n_existing + added,
               "by_fy_type": {y: dict(c) for y, c in fy_type.items()},
               "by_fy_money": {y: dict(c) for y, c in fy_money.items()},
               "entities_newly_reached": sorted(newly),
               "unresolved_ueis": len(unresolved)},
              open(RAW / "_append_summary.json", "w", encoding="utf-8"), indent=2)

    rp = REVIEW / f"assistance_archive_unresolved_{TODAY}.csv"
    with open(rp, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["recipient_uei", "recipient_name", "rows", "obligated_usd",
                    "fiscal_years", "note", "YOUR_RULING"])
        for u, v in sorted(unresolved.items(), key=lambda kv: -abs(kv[1][1])):
            w.writerow([u, v[2], v[0], round(v[1], 2), "|".join(sorted(v[3])),
                        "DISCOVERY POOL, NOT AN ATTRIBUTION. USAspending codes "
                        "this recipient business_types_code in {I,J,K} "
                        "(tribal recipient type); its UEI is absent from "
                        "cedar_identifier_ledger_final.csv tiers A/B. The "
                        "recipient-type code admits false positives. Rule on "
                        "each row's own evidence.", ""])
    log(f"wrote {rp.relative_to(CEDAR)} ({len(unresolved):,} unresolved UEIs)")

    # ---- the withheld ledger attributions --------------------------------
    wp = REVIEW / f"assistance_archive_ledger_state_disagreement_{TODAY}.csv"
    with open(wp, "w", encoding="utf-8", newline="") as fh:
        w2 = csv.writer(fh)
        w2.writerow(["ledger_proposed_tribe_id", "ledger_proposed_entity",
                     "entity_state_in_spine", "recipient_uei", "recipient_name",
                     "recipient_state_code", "rows", "obligated_usd_withheld",
                     "note", "YOUR_RULING"])
        tot = 0.0
        for _k, v in sorted(withheld.items(), key=lambda kv: -abs(kv[1][1])):
            if not v[2]:
                continue
            tid, canon, est, uei, rname, rst = v[2]
            tot += v[1]
            w2.writerow([tid, canon, est, uei, rname, rst, v[0], round(v[1], 2),
                         "ATTRIBUTION WITHHELD. The identifier ledger maps this "
                         "UEI to the named entity, but the recipient files from a "
                         "different state and USAspending does NOT independently "
                         "code it as a tribal recipient. AGENTS.md: containment "
                         "may resolve an owner already named in evidence, never "
                         "detect a match. Rule it in or out on the firm's own "
                         "ownership evidence.", ""])
    log(f"wrote {wp.relative_to(CEDAR)} "
        f"({len(withheld):,} withheld ledger attributions, "
        f"${tot/1e6:,.1f}M held out of Native totals)")
    print(f"\nledger attributions WITHHELD on state disagreement: "
          f"{len(withheld):,} recipients, ${tot/1e6:,.1f}M")
    return newly


def _int(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return -1


# ---------------------------------------------------------------------------
# 5. codebook FRAGMENT. Never touch codebook_master.csv - it is a shared
#    read-modify-write file and that race has already cost three agents' rows.
# ---------------------------------------------------------------------------
def codebook():
    sys.path.insert(0, str(CEDAR / "code"))
    import cedar_codebook

    # The fragment schema is the codebook's own, read from a sibling fragment
    # rather than assumed: dataset, variable, type, units, pct_filled, n_rows,
    # published, access_tier, description, generated.
    fields = ["dataset", "variable", "type", "units", "pct_filled", "n_rows",
              "published", "access_tier", "description", "generated"]

    # pct_filled and n_rows are MEASURED on the file as it now stands. Standing
    # rule 10: a number in a doc that is not recomputed from the data is a
    # claim, not a fact.
    target = CLEAN / "federal_funding_transactions.csv"
    filled, n = Counter(), 0
    with open(target, encoding="utf-8-sig", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            n += 1
            for c in NEW_COLS:
                if (r.get(c) or "").strip() != "":
                    filled[c] += 1

    def row(var, desc, typ="text", units="code", access_tier="public",
            published="1"):
        return {"dataset": "03_federal_funding", "variable": var, "type": typ,
                "units": units,
                "pct_filled": round(filled[var] / n * 100, 1) if n else 0.0,
                "n_rows": n, "published": published, "access_tier": access_tier,
                "description": desc, "generated": TODAY}

    rows = [
        row("face_value_of_loan",
            "Face value of a direct/guaranteed loan on this transaction "
            "(assistance types 07/08/09). This is the BORROWER'S PRINCIPAL, not "
            "federal outlay. NEVER add it to obligated_usd. Signed.",
            typ="numeric", units="USD"),
        row("original_loan_subsidy_cost",
            "What the loan or guarantee costs the government on this "
            "transaction. This, not face value, is the federal cost concept. "
            "Signed. Never summed with obligated_usd.",
            typ="numeric", units="USD"),
        row("total_face_value_of_loan",
            "AWARD-CUMULATIVE snapshot of face value, restated on every "
            "transaction of the same award. MUST NOT be summed across rows - "
            "six rows once summed to $271.4M against a true $171.4M.",
            typ="numeric", units="USD"),
        row("total_loan_subsidy_cost",
            "Award-cumulative snapshot of subsidy cost. Same rule as "
            "total_face_value_of_loan: snapshot, never summed.",
            typ="numeric", units="USD"),
        row("credit_instrument_flag",
            "1 where assistance_type is 07 (direct loan), 08 "
            "(guaranteed/insured loan) or 09 (insurance). These rows report "
            "obligated_usd as exactly 0.00 BY DESIGN; a zero here is money in a "
            "different column, not an absence of money.",
            typ="flag", units="0/1"),
        row("business_types_code",
            "USAspending recipient business type. I = federally recognized "
            "tribal government, J = other tribal government, K = tribally "
            "designated organization. The FY2008-2023 series is defined by this "
            "field taking a value in {I,J,K} and nothing else."),
        row("business_types_description",
            "Text form of business_types_code as reported at source."),
        row("obligated_usd_real2025",
            "obligated_usd deflated to 2025 dollars with the BEA GDP implicit "
            "price deflator (NIPA Table 1.1.9), data/clean/inflation_deflator.csv. "
            "BLANK for FY2026 because 2026 is not a complete year and BEA "
            "publishes no annual index for it - a forecast is not a measurement.",
            typ="numeric", units="USD (2025)"),
        row("deflator_factor_2025",
            "The factor applied to obtain obligated_usd_real2025. Blank where "
            "no published annual index exists for the year.",
            typ="numeric", units="ratio"),
        row("inflation_base_year",
            "Base year of every _real column on this row. Always 2025.",
            typ="numeric", units="year"),
        row("population_basis",
            "WHICH FILTER PUT THIS ROW IN THE DATASET. 'recipient_type' = "
            "business_types_code in {I,J,K}, which is exactly how the FY2008-2023 "
            "series was defined. 'ledger_uei' = recipient_uei is a tier A/B "
            "identifier in the Cedar Press identifier ledger. 'both' = both. "
            "Filter to != 'ledger_uei' to reproduce the original series; the "
            "seam between the two populations is a column, never a silent "
            "adjustment. 'ledger_uei_withheld' = the ledger proposed an entity "
            "but the state-agreement guard refused it; the row is retained, "
            "carries NO tribe_id, and is in the review queue."),
        row("state_agreement",
            "Does the recipient's filing state match the state the entity "
            "spine records for the attributed entity? 'agree' / 'disagree' / "
            "'unknown' (one side blank) / blank (no attribution). This is a "
            "REFUSAL test on an attribution the ledger already proposed, never "
            "a way to detect one."),
        row("ledger_proposed_tribe_id",
            "Where the state-agreement guard withheld an attribution, the "
            "entity the identifier ledger had proposed - preserved so the "
            "refusal is auditable and reversible rather than a silent drop. "
            "Blank on every row that was not withheld. It is NOT an "
            "attribution and must never be joined as one."),
        row("source_archive_stamp",
            "Publication stamp of the static archive object (YYYYMMDD). All "
            f"4,631 objects on files.usaspending.gov carry {STAMP}; enumeration "
            "confirmed no newer stamp exists. Blank on rows that came from the "
            "earlier API route - that blank IS the seam between the two "
            "sources, and source_file names which is which."),
    ]
    # `source_file` and `fetched_date` are already documented in the
    # 03_federal_funding fragment, which another build owns. Documenting them
    # again here would put two rows for the same variable into the rebuilt
    # master. Their archive-specific meaning is recorded in
    # docs/ASSISTANCE_ARCHIVE_PULL_LOG.md instead.
    written = cedar_codebook.write_fragment("03_federal_funding_archive",
                                            rows, fields)
    print(f"wrote codebook fragment 03_federal_funding_archive.csv "
          f"({written} variables, measured over {n:,} rows). "
          f"codebook_master.csv NOT touched.")


# ---------------------------------------------------------------------------
def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "enumerate"
    if cmd == "enumerate":
        enumerate_archive()
    elif cmd == "fetch":
        years = []
        for a in sys.argv[2:]:
            if ".." in a:
                lo, hi = a.split("..")
                years += list(range(int(lo), int(hi) + 1))
            elif a.isdigit():
                years.append(int(a))
        if not years:
            raise SystemExit("usage: fetch 2024 2025 2026 | fetch 2008..2023")
        global RUN_DEADLINE, HEADROOM_GB
        for a in sys.argv[2:]:
            if a.startswith("--headroom="):
                HEADROOM_GB = float(a.split("=", 1)[1])
                log(f"disk headroom set to {HEADROOM_GB:.2f} GB")
        RUN_DEADLINE = time.time() + MAX_RUN_SECONDS
        by_uei = load_ledger()
        log(f"ledger: {len(by_uei):,} UEIs; run deadline in "
            f"{MAX_RUN_SECONDS//3600}h")
        any_ok, refused, skipped = False, [], []
        for y in years:
            r = fetch_year(y, by_uei, keep_zip="--keep-zip" in sys.argv)
            if r == "skip":
                skipped.append(y)
            elif r is True:
                any_ok = True
            elif r is False:
                refused.append(y)
                # STOP ON THE FIRST REFUSAL WHEN NOTHING HAS SUCCEEDED. A year
                # that exhausts its backoff while no year has landed means the
                # HOST is refusing, not that one object is bad. Walking the
                # remaining years is fifteen more ways to learn the same fact,
                # and every one of them extends the block for the contracts
                # agent sharing this host.
                if not any_ok:
                    log(f"STOP: FY{y} exhausted its backoff and no year has "
                        f"succeeded in this run. That is a HOST refusal, not a "
                        f"bad object. Remaining years NOT attempted: "
                        f"{[x for x in years if x > y]}")
                    break
            if _deadline_passed():
                log("STOP: run deadline reached.")
                break
        touch_lock(current_action=None,
                   last_fetch_result={
                       "at": f"{datetime.now(timezone.utc):%Y-%m-%dT%H:%MZ}",
                       "downloaded_this_run": any_ok,
                       "already_on_disk_skipped": skipped,
                       "refused_by_host": refused,
                       "requested": years,
                       "note": ("`downloaded_this_run` false with an empty "
                                "`refused_by_host` means every requested year "
                                "was already on disk - it is NOT a failure and "
                                "NOT evidence of a block.")})
        if refused and not any_ok:
            log("A block is a finding, not a failure. Reported with the probe "
                "evidence; retry later, and do not write any year off.")
            sys.exit(2)
    elif cmd == "append":
        append()
    elif cmd == "codebook":
        codebook()
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
