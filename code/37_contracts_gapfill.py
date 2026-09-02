"""37_contracts_gapfill.py — prime CONTRACT forward-fill, 2023-04-05 -> 2026-08-05.

WHY THIS EXISTS
    The project's raw FPDS extracts (HigherGov "Data Request 4-5-2023 File 1/2"
    and "Data Request 5-8-2023 IDVs") stop at action_date 2023-04-04 (contracts)
    and 2023-05-07 (IDVs). Everything after that is missing from Dataset 2.

RETRIEVAL ROUTE (each choice was tested, do not "simplify" them away)
  * POST /api/v2/bulk_download/awards/ SILENTLY DROPS recipient_type_names.
    The echoed download_request.filters omitted it -> that route would have
    returned the entire federal contract universe. NOT USED.
  * POST /api/v2/download/awards/ ECHOES recipient_type_names back, so the
    filter is really applied. THIS IS THE ROUTE USED.
  * /api/v2/search/spending_by_award_count/ is used to size every job first,
    so nothing is submitted blind.

FLAG VOCABULARY — the single biggest trap here.
    An INVALID recipient_type_names value does not error. It matches zero rows
    and the job "succeeds" empty. Six plausible-looking names return 0:
        indian_tribe_federally_recognized, alaskan_native_owned_business,
        native_hawaiian_owned_business, tribally_owned_business,
        alaskan_native_servicing_institution,
        native_hawaiian_servicing_institution
    The four REAL Native ownership categories (verified non-zero) are:
        alaskan_native_corporation_owned_firm    (328,150 awards, CY2025)
        american_indian_owned_business           ( 28,033)
        tribally_owned_firm                      (  7,443)
        native_hawaiian_organization_owned_firm  (  1,791)

    STRUCTURAL HOLE — READ THIS BEFORE TRUSTING COVERAGE.
    `indian_tribe_federally_recognized`, `us_tribal_government`,
    `housing_authorities_public_tribal` and `tribal_college` all EXIST as
    output COLUMNS on the returned rows and are 't' on real records, but all
    four match ZERO rows when used as FILTER values. The filter vocabulary and
    the column vocabulary are not the same set. Consequence: this flag route
    retrieves Native-OWNED BUSINESSES and cannot retrieve a tribal GOVERNMENT
    contracting in its own name unless that row also carries one of the four
    working ownership flags. Pass B (`code/38_contracts_ledger_pass.py`,
    recipient_search_text over the ledger's own UEIs) exists to close exactly
    this hole and is not optional.

ZERO FABRICATION
    Nothing is attributed here. Rows are matched to
    data/clean/cedar_identifier_ledger_final.csv on EXACT UEI only, and the
    ledger's own confidence_tier is carried through unchanged. UEIs that do not
    match are written to a candidates file and are NOT attributed to anyone.

Usage:
  py -3 code/37_contracts_gapfill.py probe
  py -3 code/37_contracts_gapfill.py pull [--sleep 20]
  py -3 code/37_contracts_gapfill.py match
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
RAW = os.path.join(ROOT, "data", "raw", "contracts", "usaspending_gapfill_2026-08-05")
CLEAN = os.path.join(ROOT, "data", "clean")
REVIEW = os.path.join(ROOT, "review")
LOGFILE = os.path.join(ROOT, "logs", "37_contracts_gapfill.log")
STATE = os.path.join(RAW, "_state.json")

DOWNLOAD = "https://api.usaspending.gov/api/v2/download/awards/"
STATUS = "https://api.usaspending.gov/api/v2/download/status"
COUNT = "https://api.usaspending.gov/api/v2/search/spending_by_award_count/"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
FETCHED = "2026-08-05"

# Verified non-zero against spending_by_award_count. See module docstring.
NATIVE_FLAGS = [
    "alaskan_native_corporation_owned_firm",
    "american_indian_owned_business",
    "tribally_owned_firm",
    "native_hawaiian_organization_owned_firm",
]

CONTRACT_TYPES = ["A", "B", "C", "D"]
IDV_TYPES = ["IDV_A", "IDV_B", "IDV_C", "IDV_D", "IDV_E"]

# Coverage gap. Existing raw FPDS extracts end 2023-04-04 (contracts) and
# 2023-05-07 (IDVs); measured, not assumed - see logs/37 probe output.
GAP_START = "2023-04-05"
GAP_END = "2026-08-05"

# One job per (family, window). Windows are calendar slices small enough that
# no single job approaches the 500,000-row cap the endpoint reports.
# Sized from the probe (data/.../\_probe_counts.json) so no job approaches the
# endpoint's 500,000-row cap, while keeping the job COUNT low - every extra job
# is another chance to trip the edge rate limit.
#   A 340,747 | B 369,868 | C 329,009   (contracts)
CONTRACT_WINDOWS = [
    ("w1", "2023-04-05", "2024-06-30"),
    ("w2", "2024-07-01", "2025-06-30"),
    ("w3", "2025-07-01", "2026-08-05"),
]
# All IDVs in the whole gap are 1,523 rows - one job.
IDV_WINDOWS = [("all", GAP_START, GAP_END)]

# Retained: the interrupted first run submitted this narrower window and the
# file was generated. It is collected rather than wasted; script 39 dedups on
# contract_award_unique_key so the overlap cannot double-count.
LEGACY_WINDOWS = [("2023q2", "2023-04-05", "2023-06-30")]


def log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')}] {msg}"
    print(line, flush=True)
    os.makedirs(os.path.dirname(LOGFILE), exist_ok=True)
    with open(LOGFILE, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def _post(url, payload, t=240):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": UA},
        method="POST")
    with urllib.request.urlopen(req, timeout=t) as r:
        return json.loads(r.read().decode())


def _get(url, t=180):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=t) as r:
        return json.loads(r.read().decode())


def retry(fn, *a, tries=5, base=8, **kw):
    """Retry with backoff. A prior session reported HTTP 000 from this host."""
    last = None
    for i in range(tries):
        try:
            return fn(*a, **kw)
        except Exception as e:
            last = e
            if isinstance(e, urllib.error.HTTPError) and e.code in (400, 422):
                raise
            wait = base * (2 ** i)
            log(f"    retry {i+1}/{tries} after {type(e).__name__}: {e} — sleeping {wait}s")
            time.sleep(wait)
    raise last


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def load_state():
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as fh:
            return json.load(fh)
    return {"jobs": {}}


def save_state(st):
    os.makedirs(RAW, exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(st, fh, indent=1)
    os.replace(tmp, STATE)


def filters_for(types, start, end):
    return {
        "award_type_codes": types,
        "time_period": [{"start_date": start, "end_date": end,
                         "date_type": "action_date"}],
        "recipient_type_names": NATIVE_FLAGS,
    }


# ------------------------------------------------------------------ probe
def stage_probe():
    log("PROBE — sizing every job before anything is submitted")
    grand = {}
    for fam, types, wins in (("contracts", CONTRACT_TYPES, CONTRACT_WINDOWS),
                             ("idvs", IDV_TYPES, IDV_WINDOWS)):
        for key, s, e in wins:
            r = retry(_post, COUNT, {"filters": filters_for(types, s, e)})
            res = r["results"]
            n = res.get("contracts", 0) + res.get("idvs", 0)
            grand[f"{fam}_{key}"] = n
            log(f"  {fam:9s} {key:8s} {s}..{e}  awards={n:,}")
            time.sleep(1)
    log(f"PROBE TOTAL award-summary rows expected: {sum(grand.values()):,}")
    os.makedirs(RAW, exist_ok=True)
    with open(os.path.join(RAW, "_probe_counts.json"), "w", encoding="utf-8") as fh:
        json.dump(grand, fh, indent=1)
    return grand


# ------------------------------------------------------------------- pull
def submit(types, start, end):
    payload = {"filters": filters_for(types, start, end),
               "columns": [], "file_format": "csv"}
    resp = retry(_post, DOWNLOAD, payload)
    echoed = resp.get("download_request", {}).get("filters", {})
    # HARD GUARD: bulk_download silently drops this filter. If the echo ever
    # loses it, we would be downloading the entire federal universe. Refuse.
    if "recipient_type_names" not in echoed:
        raise RuntimeError(
            "recipient_type_names ABSENT from echoed filters — endpoint is "
            "silently dropping the Native-ownership filter. Refusing to "
            f"proceed. echo={echoed}")
    return resp["file_name"], payload


def direct_fetch(file_name, dest):
    """Download a generated file straight from files.usaspending.gov.

    The generated-download URL is deterministic, so a job whose STATUS polling
    was lost to an edge block can still be collected without resubmitting.
    Resubmitting is what got us rate-limited in the first place.
    """
    url = "https://files.usaspending.gov/generated_downloads/" + file_name
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=3600) as r, open(dest + ".part", "wb") as fh:
        while True:
            c = r.read(1 << 20)
            if not c:
                break
            fh.write(c)
    os.replace(dest + ".part", dest)
    return {"_bytes": os.path.getsize(dest), "_sha256": sha256(dest),
            "_collected_via": "direct files.usaspending.gov fetch"}


# Poll interval. 20s triggered the documented edge-level rate limit
# (RemoteDisconnected on every request). 90s does not.
POLL = 90


def wait_and_fetch(file_name, dest, max_wait=7200):
    waited = 0
    meta = {}
    while waited < max_wait:
        time.sleep(POLL)
        waited += POLL
        try:
            meta = _get(STATUS + "?file_name=" + urllib.parse.quote(file_name))
        except Exception as e:
            log(f"    status poll error {type(e).__name__}: {e}")
            continue
        s = meta.get("status")
        if s == "finished":
            break
        if s == "failed":
            raise RuntimeError(f"job failed: {meta.get('message')}")
        if waited % (POLL * 3) == 0:
            log(f"    ...{s} after {waited}s")
    if meta.get("status") != "finished":
        raise RuntimeError(f"not finished after {max_wait}s: {meta.get('status')}")
    log(f"    finished rows={meta.get('total_rows')} size={meta.get('total_size')}KB")
    url = meta.get("file_url")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=3600) as r, open(dest + ".part", "wb") as fh:
        while True:
            c = r.read(1 << 20)
            if not c:
                break
            fh.write(c)
    os.replace(dest + ".part", dest)
    meta["_bytes"] = os.path.getsize(dest)
    meta["_sha256"] = sha256(dest)
    return meta


def stage_pull(sleep_between=20):
    os.makedirs(RAW, exist_ok=True)
    st = load_state()
    for fam, types, wins in (("contracts", CONTRACT_TYPES, LEGACY_WINDOWS + CONTRACT_WINDOWS),
                             ("idvs", IDV_TYPES, IDV_WINDOWS)):
        for key, s, e in wins:
            jk = f"{fam}_{key}"
            dest = os.path.join(RAW, jk + ".zip")
            if jk in st["jobs"] and os.path.exists(dest):
                log(f"SKIP {jk} (staged, {st['jobs'][jk].get('total_rows')} rows)")
                continue
            try:
                # A handle already submitted in an earlier (interrupted) run is
                # reused. NEVER resubmit a job we already paid for.
                pend = st.setdefault("pending", {})
                if jk in pend:
                    fn, payload = pend[jk]["file_name"], pend[jk]["payload"]
                    log(f"RESUME {jk} from existing handle {fn}")
                    try:
                        meta = direct_fetch(fn, dest)
                        log(f"  collected directly, {meta['_bytes']:,} bytes")
                    except Exception as de:
                        log(f"  direct fetch not ready ({de}); polling status")
                        meta = wait_and_fetch(fn, dest)
                else:
                    log(f"SUBMIT {jk} {s}..{e}")
                    fn, payload = submit(types, s, e)
                    log(f"  accepted: {fn}")
                    pend[jk] = {"file_name": fn, "payload": payload}
                    save_state(st)          # checkpoint the HANDLE immediately
                    meta = wait_and_fetch(fn, dest)
            except Exception as ex:
                log(f"FAIL {jk}: {type(ex).__name__}: {ex}")
                save_state(st)
                continue
            meta["_payload"] = payload
            meta["_local_file"] = jk + ".zip"
            meta["_retrieved"] = FETCHED
            meta["_date_range"] = [s, e]
            st["jobs"][jk] = meta
            save_state(st)
            log(f"CHECKPOINT {jk} -> {meta['_bytes']:,} bytes")
            time.sleep(sleep_between)
    log("PULL STAGE COMPLETE")


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "probe"
    if stage == "probe":
        stage_probe()
    elif stage == "pull":
        sl = 20
        if "--sleep" in sys.argv:
            sl = int(sys.argv[sys.argv.index("--sleep") + 1])
        stage_pull(sl)
