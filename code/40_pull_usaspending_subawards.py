"""40_pull_usaspending_subawards.py — fresh FSRS subaward pull, USAspending bulk_download.

Dataset 2b's prior source (the 2023 HigherGov export `subcontract-05-09-23-22-23-37.csv`,
998 rows) was mined to exhaustion and yielded 0 net-new identifiers. This script replaces
it with a first-party pull straight from USAspending.

    POST https://api.usaspending.gov/api/v2/bulk_download/awards/
      filters.sub_award_types = ["procurement", "grant"]
      filters.date_type       = "action_date"      -> filters SUBAWARD action date (verified)
      filters.date_range      = one fiscal year per job
      file_format             = csv        (no `columns` filter -> full as-shipped schema)

Verified 2026-08-05 against a 2015-10-01..2015-10-02 probe: every returned row had
`subaward_action_date` inside the requested window, on both the contracts file (118 cols)
and the assistance file (113 cols). `date_type=action_date` therefore keys on the SUBAWARD
action date, not the prime's.

DESIGN CONSTRAINTS (inherited from 30_funding_pre2008.py, learned the hard way):
  * Every job is checkpointed to _state.json the moment its zip lands. Rerunning `pull`
    resumes from exactly where it stopped and re-downloads nothing.
  * Transient failures get bounded retries with exponential backoff; a hard failure stops
    that worker without discarding checkpoints.
  * Zips are kept compressed and stream-read. Nothing is ever extracted to disk.
  * Nothing is fabricated. An unretrieved fiscal year is simply absent and is named in
    the build log.

TEMPORAL FLOOR. Cedar Press applies a floor of 2000 to every dataset. FSRS subaward
reporting began under FFATA in 2010, so 2010 is the real data floor here. Two probe jobs
(FY2001-2009 and FY2010) are submitted anyway so the floor is DEMONSTRATED from the source
rather than asserted from documentation.

Usage:
  py -3 code/40_pull_usaspending_subawards.py pull [--workers 3] [--only fy2013,fy2014]
  py -3 code/40_pull_usaspending_subawards.py status
  py -3 code/40_pull_usaspending_subawards.py manifest
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw", "subcontracts", "usaspending_subawards_2026-08-05")
# Two puller processes must never share a state file — each holds the whole dict in
# memory and its save_state would clobber the other's checkpoints. CEDAR_SUBAWARD_STATE
# lets a second process (e.g. the pre-2010 probes) run concurrently against its own file;
# `merge-state` folds them back together afterwards.
STATE = os.environ.get("CEDAR_SUBAWARD_STATE") or os.path.join(RAW, "_state.json")
LOGFILE = os.path.join(ROOT, "logs", "40_subaward_pull_2026-08-05.log")

API = "https://api.usaspending.gov/api/v2/bulk_download/awards/"
STATUS = "https://api.usaspending.gov/api/v2/download/status"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
FETCHED = "2026-08-05"

SUB_TYPES = ["procurement", "grant"]

# One job per fiscal year. FY2001-FY2010 are the below-the-floor probes: they
# demonstrate the FFATA start empirically instead of asserting it from documentation.
# The endpoint rejects any date_range spanning more than a year
# ("Invalid Parameter: date_range total days must be within a year", observed
# 2026-08-05 on a 2000-10-01..2009-09-30 request), so the probes cannot be batched.
CHUNKS = [(f"fy{fy}", f"{fy-1}-10-01", f"{fy}-09-30") for fy in range(2001, 2027)]

_lock = threading.Lock()


def log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')}] {msg}"
    with _lock:
        print(line, flush=True)
        os.makedirs(os.path.dirname(LOGFILE), exist_ok=True)
        with open(LOGFILE, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")


# ---------------------------------------------------------------- http helpers

def _post(url: str, payload: dict, timeout: int = 300):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json", "User-Agent": UA},
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _get(url: str, timeout: int = 180):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def retry(fn, what: str, tries: int = 6, base: float = 20.0):
    """Bounded exponential backoff. Re-raises the last error after `tries`."""
    last = None
    for i in range(1, tries + 1):
        try:
            return fn()
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:400]
            if 400 <= e.code < 500 and e.code not in (408, 429):
                raise RuntimeError(f"{what}: HTTP {e.code} {detail}") from e
            last = f"HTTP {e.code} {detail}"
        except Exception as e:                       # noqa: BLE001 transient
            last = f"{type(e).__name__}: {e}"
        wait = base * (2 ** (i - 1))
        log(f"  retry {i}/{tries} {what} after {last} — sleeping {wait:.0f}s")
        time.sleep(wait)
    raise RuntimeError(f"{what} failed after {tries} tries: {last}")


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------- state io

def load_state() -> dict:
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as fh:
            return json.load(fh)
    return {"jobs": {}}


def save_state(st: dict) -> None:
    os.makedirs(RAW, exist_ok=True)
    with _lock:
        tmp = STATE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(st, fh, indent=1)
        os.replace(tmp, STATE)


# ----------------------------------------------------------------- pull stage

def build_payload(start: str, end: str) -> dict:
    return {
        "filters": {
            "sub_award_types": SUB_TYPES,
            "date_type": "action_date",
            "date_range": {"start_date": start, "end_date": end},
        },
        "file_format": "csv",
    }


def run_chunk(key: str, start: str, end: str, st: dict) -> None:
    dest_dir = RAW
    os.makedirs(dest_dir, exist_ok=True)

    rec = st["jobs"].get(key)
    if rec and rec.get("_local_file") and os.path.exists(
            os.path.join(ROOT, rec["_local_file"])):
        log(f"SKIP {key} (already staged, {rec.get('total_rows')} rows)")
        return

    payload = build_payload(start, end)
    log(f"SUBMIT {key}: subawards {start}..{end}")
    resp = retry(lambda: _post(API, payload), f"submit {key}")
    file_name = resp.get("file_name")
    if not file_name:
        raise RuntimeError(f"{key}: no file_name in response: {resp}")
    log(f"  {key} accepted -> {file_name}")

    # poll
    su = STATUS + "?file_name=" + urllib.parse.quote(file_name)
    meta, waited, max_wait = {}, 0, 4 * 3600
    while waited < max_wait:
        time.sleep(30)
        waited += 30
        meta = retry(lambda: _get(su), f"status {key}", tries=8)
        s = meta.get("status")
        if s == "finished":
            break
        if s == "failed":
            raise RuntimeError(f"{key}: job failed: {meta.get('message')}")
        if waited % 300 == 0:
            log(f"  {key} ...{s} rows_so_far={meta.get('total_rows')} after {waited}s")
    if meta.get("status") != "finished":
        raise RuntimeError(f"{key}: not finished after {max_wait}s ({meta.get('status')})")

    log(f"  {key} FINISHED rows={meta.get('total_rows')} cols={meta.get('total_columns')} "
        f"size={meta.get('total_size')}KB elapsed={meta.get('seconds_elapsed')}s")

    url = meta.get("file_url")
    if not url:
        raise RuntimeError(f"{key}: finished job has no file_url: {meta}")
    # ORIGINAL FILENAME, as required by project convention.
    fname = os.path.basename(urllib.parse.urlparse(url).path)
    dest = os.path.join(dest_dir, fname)

    def _dl():
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        tmp = dest + ".part"
        with urllib.request.urlopen(req, timeout=3600) as r, open(tmp, "wb") as fh:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                fh.write(chunk)
        os.replace(tmp, dest)
    retry(_dl, f"download {key}", tries=5)

    meta["_local_file"] = os.path.relpath(dest, ROOT).replace("\\", "/")
    meta["_bytes"] = os.path.getsize(dest)
    meta["_sha256"] = sha256(dest)
    meta["_chunk_key"] = key
    meta["_date_range"] = [start, end]
    meta["_endpoint"] = API
    meta["_payload"] = payload
    meta["_retrieved"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    st["jobs"][key] = meta
    save_state(st)
    log(f"CHECKPOINT {key} -> {meta['_local_file']} ({meta['_bytes']:,} bytes)")


def stage_pull(only=None, workers: int = 3) -> None:
    st = load_state()
    st.setdefault("jobs", {})
    todo = [c for c in CHUNKS if not only or c[0] in only]
    todo = [c for c in todo
            if not (st["jobs"].get(c[0], {}).get("_local_file")
                    and os.path.exists(os.path.join(
                        ROOT, st["jobs"][c[0]]["_local_file"])))]
    if not todo:
        log("PULL: nothing to do, all chunks already staged")
        return
    log(f"PULL: {len(todo)} chunks outstanding, {workers} workers")

    queue = list(todo)
    qlock = threading.Lock()
    failures = []

    def worker(wid: int):
        while True:
            with qlock:
                if not queue:
                    return
                key, start, end = queue.pop(0)
            try:
                run_chunk(key, start, end, st)
            except Exception as e:                    # noqa: BLE001
                log(f"FAIL {key}: {type(e).__name__}: {e}")
                with qlock:
                    failures.append(key)
            time.sleep(15)

    threads = [threading.Thread(target=worker, args=(i,), daemon=False)
               for i in range(workers)]
    for i, t in enumerate(threads):
        t.start()
        time.sleep(10)          # stagger submissions
    for t in threads:
        t.join()

    save_state(st)
    log(f"PULL STAGE COMPLETE. staged={len(st['jobs'])} failures={failures}")


def stage_recover(pairs: str) -> None:
    """Adopt jobs that were SUBMITTED but whose download was lost to an edge block.

    A submitted job keeps generating server-side even when our IP is being refused, and
    the generated file stays retrievable by its `file_name`. Re-submitting instead would
    both waste the completed work and add load to the edge that is already refusing us.
    Handles are recoverable from logs/40_subaward_pull_2026-08-05.log ("<key> accepted -> <file>").

    pairs: "fy2012=All_Subawards_..._1.zip,fy2013=All_Subawards_..._2.zip"
    """
    st = load_state()
    st.setdefault("jobs", {})
    for pair in pairs.split(","):
        key, _, file_name = pair.partition("=")
        key, file_name = key.strip(), file_name.strip()
        if not key or not file_name:
            log(f"recover: unparseable pair {pair!r}, skipped")
            continue
        rng = next((c for c in CHUNKS if c[0] == key), None)
        if rng is None:
            log(f"recover: unknown chunk {key}, skipped")
            continue
        rec = st["jobs"].get(key)
        if rec and rec.get("_local_file") and os.path.exists(
                os.path.join(ROOT, rec["_local_file"])):
            log(f"recover: {key} already staged, skipped")
            continue
        su = STATUS + "?file_name=" + urllib.parse.quote(file_name)
        try:
            meta = retry(lambda: _get(su), f"recover-status {key}", tries=8)
        except Exception as e:                        # noqa: BLE001
            log(f"recover FAIL {key}: {type(e).__name__}: {e}")
            continue
        if meta.get("status") != "finished":
            log(f"recover: {key} status={meta.get('status')} "
                f"rows_so_far={meta.get('total_rows')} — not ready, try again later")
            continue
        url = meta.get("file_url")
        fname = os.path.basename(urllib.parse.urlparse(url).path)
        dest = os.path.join(RAW, fname)

        def _dl():
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=3600) as r, open(dest + ".part", "wb") as fh:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    fh.write(chunk)
            os.replace(dest + ".part", dest)
        try:
            retry(_dl, f"recover-download {key}", tries=5)
        except Exception as e:                        # noqa: BLE001
            log(f"recover FAIL {key} during download: {type(e).__name__}: {e}")
            continue
        meta["_local_file"] = os.path.relpath(dest, ROOT).replace("\\", "/")
        meta["_bytes"] = os.path.getsize(dest)
        meta["_sha256"] = sha256(dest)
        meta["_chunk_key"] = key
        meta["_date_range"] = [rng[1], rng[2]]
        meta["_endpoint"] = API
        meta["_payload"] = build_payload(rng[1], rng[2])
        meta["_retrieved"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        meta["_recovered_handle"] = file_name
        st["jobs"][key] = meta
        save_state(st)
        log(f"RECOVERED {key} -> {meta['_local_file']} ({meta['_bytes']:,} bytes, "
            f"{meta.get('total_rows')} rows)")


def stage_status() -> None:
    st = load_state()
    tot_rows = tot_bytes = 0
    for key, _, _ in CHUNKS:
        m = st["jobs"].get(key)
        if not m:
            print(f"{key:14s} NOT PULLED")
            continue
        print(f"{key:14s} rows={m.get('total_rows'):>10} "
              f"bytes={m.get('_bytes'):>12,} {m.get('_local_file')}")
        tot_rows += int(m.get("total_rows") or 0)
        tot_bytes += int(m.get("_bytes") or 0)
    print(f"{'TOTAL':14s} rows={tot_rows:>10,} bytes={tot_bytes:>12,}")


def stage_manifest() -> None:
    import csv as _csv
    st = load_state()
    out = os.path.join(RAW, "_SOURCE_MANIFEST_usaspending_subawards.csv")
    cols = ["local_file", "chunk_key", "source_url", "endpoint", "date_range_start",
            "date_range_end", "sub_award_types", "date_type", "rows", "columns",
            "bytes", "sha256", "retrieved_utc", "fetched_date"]
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = _csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for key, start, end in CHUNKS:
            m = st["jobs"].get(key)
            if not m:
                continue
            w.writerow({
                "local_file": os.path.basename(m.get("_local_file", "")),
                "chunk_key": key,
                "source_url": m.get("file_url", ""),
                "endpoint": API,
                "date_range_start": start,
                "date_range_end": end,
                "sub_award_types": "|".join(SUB_TYPES),
                "date_type": "action_date",
                "rows": m.get("total_rows", ""),
                "columns": m.get("total_columns", ""),
                "bytes": m.get("_bytes", ""),
                "sha256": m.get("_sha256", ""),
                "retrieved_utc": m.get("_retrieved", ""),
                "fetched_date": FETCHED,
            })
    log(f"manifest -> {out}")


def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else "pull"
    only = None
    workers = 3
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
    if "--workers" in sys.argv:
        workers = int(sys.argv[sys.argv.index("--workers") + 1])
    if stage == "merge-state":
        # Fold every _state*.json in RAW into the primary _state.json.
        primary = os.path.join(RAW, "_state.json")
        merged = {"jobs": {}}
        if os.path.exists(primary):
            merged = json.load(open(primary, encoding="utf-8"))
        merged.setdefault("jobs", {})
        for fn in sorted(os.listdir(RAW)):
            if not (fn.startswith("_state") and fn.endswith(".json")) or fn == "_state.json":
                continue
            other = json.load(open(os.path.join(RAW, fn), encoding="utf-8"))
            for k, v in other.get("jobs", {}).items():
                if k in merged["jobs"]:
                    log(f"merge: {k} already present, keeping primary")
                    continue
                merged["jobs"][k] = v
                log(f"merge: +{k} from {fn}")
        with open(primary, "w", encoding="utf-8") as fh:
            json.dump(merged, fh, indent=1)
        log(f"merge-state: {len(merged['jobs'])} jobs in {primary}")
        return
    if stage == "pull":
        stage_pull(only, workers)
        stage_manifest()
    elif stage == "recover":
        stage_recover(sys.argv[2])
    elif stage == "status":
        stage_status()
    elif stage == "manifest":
        stage_manifest()
    else:
        raise SystemExit(f"unknown stage {stage}")


if __name__ == "__main__":
    main()
