#!/usr/bin/env python3
"""
1145_cosponsor_harvest.py - who BACKED a Native bill, not just who wrote it.

Cedar Press collection `legislation`. Builds two NEW tables:

    data/clean/native_bill_cosponsors.csv          one row per (bill, cosponsor)
    data/clean/native_bill_cosponsor_coverage.csv  one row per bill in
                                                   native_bills.csv, naming the
                                                   outcome of the look-up

SOURCE
------
Congress.gov API v3 (Library of Congress), `/v3/bill/{congress}/{billType}/
{billNumber}/cosponsors`.  Key: `CONGRESS_API_KEY`, resolved by
`code/cedar_keys_env.py` (never written into this repo).  U.S. Government work,
no redistribution restriction stated; `https://api.congress.gov/` terms are
"free to use", rate limited at 5,000 requests/hour with a key.  Requests are
paced well below that and the host is claimed with the standard
`logs/_HOSTLOCK_api.congress.gov.json` per `docs/PULL_DISCIPLINE.md` rule 2.

WHY THIS TABLE DID NOT EXIST
----------------------------
`native_bills.csv` has carried a `cosponsor_count` since 2026-08-05 - a NUMBER.
Who those cosponsors were was fetched for **275 of 3,069 bills** by an earlier,
unnumbered pass and left in `data/clean/_cosponsors.csv`, a leading-underscore
file that matches no `COLLECTIONS` pattern in
`code/500_build_architecture_map.py`, reaches no dataset contract in `512`, and
is in no codebook.  It was ON_DISK_NOT_PROMOTED (5,318 rows / 162 bills) sitting
next to a NOT_ACQUIRED gap of 2,794 bills.  This script closes both: it promotes
the legacy rows with their provenance intact and fetches the rest.

THE LEGACY ROWS ARE NOT RE-FETCHED AND NOT TRUSTED BLINDLY.  Every legacy row is
carried with `record_basis = legacy__cosponsors_csv`; where this pass also
fetched the same bill, the fetched roster wins and the legacy roster is compared
- disagreements are counted and printed, never silently resolved.

WHAT IS DELIBERATELY NOT DONE
-----------------------------
* No `middleName`/`firstName`/`lastName` split is published beyond `full_name`
  and `bioguide_id`; a member of Congress is a public role, and only the
  role-facing fields the API publishes are carried.  No address, no contact.
* `bill_type` values that are not canonical congress.gov slugs (`hre`, `hjr`,
  `treatydoc`, `treatydocno` - 8 rows) are NOT coerced into something that would
  return a 200 for the wrong bill.  They are recorded
  `SOURCE_DOES_NOT_PUBLISH_ON_BILL_ENDPOINT`.  `code/1092` already established
  that treaty documents are not on `/bill` at all.

RUN
---
    py -3 code/1145_cosponsor_harvest.py report     # no network. the gap.
    py -3 code/1145_cosponsor_harvest.py fetch      # hostlock, paced, resumable
    py -3 code/1145_cosponsor_harvest.py apply      # build the two tables
    py -3 code/1145_cosponsor_harvest.py verify     # exits 1 if it did not land
    py -3 code/1145_cosponsor_harvest.py selftest   # proves verify FIRES

`fetch` is checkpointed per bill: one JSON object per bill under
`data/raw/external/congress_gov/1145_cosponsors/`, plus an append-only
`_fetch_log.jsonl`.  Re-running it downloads nothing it already holds.

VERIFY FAILS WHEN THE WORK DID NOT HAPPEN (AGENT_FIELD_GUIDE rule 5).  It is not
a conservation check.  It asserts the intended DELTA with floors: the table
exists, carries >= MIN_ROWS rows over >= MIN_BILLS bills, every `bill_id` is a
real `native_bills.csv` key, the coverage table accounts for all 3,069 bills,
and the primary key is unique.  `selftest` injects each breach and asserts the
named invariant fires.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from cedar_keys_env import get_key, mask
except Exception:  # pragma: no cover
    get_key = None
    mask = lambda s: "?"  # noqa: E731

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
LOGS = ROOT / "logs"
RAW = ROOT / "data" / "raw" / "external" / "congress_gov" / "1145_cosponsors"
FETCHLOG = RAW / "_fetch_log.jsonl"

NATIVE_BILLS = CLEAN / "native_bills.csv"
LEGACY = CLEAN / "_cosponsors.csv"
LEGACY_LOG = CLEAN / "_cosponsor_fetch_log.csv"

OUT_ROWS = CLEAN / "native_bill_cosponsors.csv"
OUT_COV = CLEAN / "native_bill_cosponsor_coverage.csv"

HOST = "api.congress.gov"
HOSTLOCK = LOGS / f"_HOSTLOCK_{HOST}.json"
BASE = f"https://{HOST}/v3/bill"
UA = "CedarPress/1.0 (research data collection; elijahsamsonmoreno@gmail.com)"

# Pace. The keyed budget is 5,000/hour = 1.39/s. 0.45s between requests is
# 2.2/s peak but the ceiling that matters is the hourly one, and the run is
# ~2,800 requests, so this finishes inside a single hourly window with ~44%
# of the budget unspent. A 429 doubles the sleep for the rest of the run.
SLEEP_S = 0.45
MAX_RUN_S = 3 * 3600           # hard stop. Backoff bounds the rate, not the run.
MAX_ATTEMPTS = 4
PAGE = 250

# Canonical congress.gov bill_type slugs. Anything else is not on /bill.
CANONICAL = {"hr", "s", "hres", "sres", "hjres", "sjres", "hconres", "sconres"}

# Verify floors. Set from the measured outcome of the first full run; a floor
# is a claim that the work landed, so it is deliberately just under the
# measurement and never re-baselined to clear a red gate.
MIN_ROWS = 20000
MIN_BILLS = 1500

BUILD_DATE = datetime.now(timezone.utc).strftime("%Y-%m-%d")
SOURCE_URL_TMPL = ("https://api.congress.gov/v3/bill/{congress}/{bill_type}/"
                   "{number}/cosponsors")

OUT_COLS = [
    "bill_id", "congress", "chamber", "bill_type", "bill_number",
    "cosponsor_bioguide_id", "cosponsor_full_name", "cosponsor_party",
    "cosponsor_state", "cosponsor_district",
    "sponsorship_date", "is_original_cosponsor",
    "sponsorship_withdrawn_date",
    "record_basis", "source_url", "fetched_date",
]
COV_COLS = [
    "bill_id", "congress", "chamber", "bill_type", "bill_number",
    "cosponsor_lookup_status", "n_cosponsors_retrieved",
    "n_cosponsors_reported_by_source", "cosponsor_count_in_native_bills",
    "count_agrees_with_native_bills",
    "cosponsor_lookup_basis", "source_url", "fetched_date",
]

# ---------------------------------------------------------------------------
# small io helpers
# ---------------------------------------------------------------------------


def read_csv(p: Path) -> list[dict]:
    csv.field_size_limit(10 ** 9)
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(p: Path, cols: list[str], rows: list[dict]) -> None:
    """.part then rename, so a killed process never leaves a half table."""
    part = p.with_suffix(p.suffix + ".part")
    with open(part, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    os.replace(part, p)


def backup(p: Path, stem: str) -> None:
    """Snapshot before an overwrite. A same-day snapshot whose size no longer
    matches the live file is STALE and is superseded (871's incident rule)."""
    if not p.exists():
        return
    bak = p.with_name(p.name + f".bak_{BUILD_DATE}_pre_{stem}")
    if bak.exists() and bak.stat().st_size == p.stat().st_size:
        return
    shutil.copy2(p, bak)
    print(f"  backup -> {bak.name}")


def norm_type(bt: str) -> str:
    return (bt or "").strip().lower().replace(".", "")


def chamber_of(bt: str) -> str:
    t = norm_type(bt)
    if t.startswith("h"):
        return "House"
    if t.startswith("s"):
        return "Senate"
    return ""


def bill_key(r: dict) -> tuple[str, str, str]:
    return (str(r.get("congress", "")).strip(),
            norm_type(r.get("bill_type", "")),
            str(r.get("number", "")).strip())


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------


def load_targets() -> list[dict]:
    nb = read_csv(NATIVE_BILLS)
    out = []
    for r in nb:
        cg, bt, num = bill_key(r)
        out.append({
            "bill_id": r["bill_id"], "congress": cg, "bill_type": bt,
            "number": num, "chamber": r.get("chamber", "") or chamber_of(bt),
            "cosponsor_count": (r.get("cosponsor_count") or "").strip(),
        })
    return out


def cache_path(t: dict) -> Path:
    return RAW / t["congress"] / f"{t['bill_type']}{t['number']}.json"


def cmd_report() -> int:
    targets = load_targets()
    cached = sum(1 for t in targets if cache_path(t).exists())
    noncanon = [t for t in targets if t["bill_type"] not in CANONICAL]
    legacy_rows = read_csv(LEGACY) if LEGACY.exists() else []
    legacy_bills = {r["bill_id"] for r in legacy_rows}
    legacy_log = read_csv(LEGACY_LOG) if LEGACY_LOG.exists() else []

    print("=" * 74)
    print("1145 report - Native bill cosponsors. No network in this subcommand.")
    print("=" * 74)
    print(f"  native_bills.csv                 {len(targets):>7,} bills "
          f"({len({t['bill_id'] for t in targets}):,} distinct bill_id)")
    print(f"  ...with a canonical bill_type    {len(targets) - len(noncanon):>7,}")
    print(f"  ...NOT on the /bill endpoint     {len(noncanon):>7,}  "
          f"{sorted({t['bill_type'] for t in noncanon})}")
    print(f"  legacy data/clean/_cosponsors.csv{len(legacy_rows):>7,} rows over "
          f"{len(legacy_bills):,} bills   ORPHAN: matches no COLLECTIONS pattern")
    print(f"  legacy fetch log                 {len(legacy_log):>7,} bills logged")
    print(f"  1145 cache on disk               {cached:>7,} bills")
    todo = [t for t in targets
            if t["bill_type"] in CANONICAL and not cache_path(t).exists()]
    print(f"  STILL TO FETCH                   {len(todo):>7,} bills")
    if OUT_ROWS.exists():
        cur = read_csv(OUT_ROWS)
        print(f"  live {OUT_ROWS.name}: {len(cur):,} rows / "
              f"{len({r['bill_id'] for r in cur}):,} bills")
    else:
        print(f"  live {OUT_ROWS.name}: ABSENT")
    return 0


# ---------------------------------------------------------------------------
# fetch
# ---------------------------------------------------------------------------


def take_hostlock(queue: list[str]) -> bool:
    LOGS.mkdir(exist_ok=True)
    if HOSTLOCK.exists():
        try:
            cur = json.loads(HOSTLOCK.read_text(encoding="utf-8"))
        except Exception:
            cur = {}
        if not cur.get("released"):
            started = cur.get("started", "")
            stale = False
            try:
                age = (datetime.now(timezone.utc)
                       - datetime.fromisoformat(started.replace("Z", "+00:00")))
                stale = age.total_seconds() > 6 * 3600
            except Exception:
                pass
            if not stale:
                print(f"  HOSTLOCK {HOST} HELD by {cur.get('script')!r} "
                      f"(pid {cur.get('pid')}, started {started}). "
                      f"Appending to its queue and exiting - PULL_DISCIPLINE rule 1.")
                cur.setdefault("queue", []).extend(queue)
                HOSTLOCK.write_text(json.dumps(cur, indent=2), encoding="utf-8")
                return False
            print(f"  HOSTLOCK {HOST} is older than 6h ({started}) - taking over.")
    HOSTLOCK.write_text(json.dumps({
        "host": HOST, "pid": os.getpid(),
        "script": "code/1145_cosponsor_harvest.py",
        "started": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "queue": queue, "released": False,
    }, indent=2), encoding="utf-8")
    return True


def release_hostlock() -> None:
    if not HOSTLOCK.exists():
        return
    try:
        cur = json.loads(HOSTLOCK.read_text(encoding="utf-8"))
    except Exception:
        cur = {}
    if cur.get("pid") == os.getpid():
        cur["released"] = True
        cur["released_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        HOSTLOCK.write_text(json.dumps(cur, indent=2), encoding="utf-8")


def api_get(url: str, key: str) -> tuple[int, dict | None, str]:
    """Return (http_status, parsed_json_or_None, note). Never raises on HTTP."""
    full = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(
        {"format": "json", "api_key": key})
    req = urllib.request.Request(full, headers={"User-Agent": UA,
                                                "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode("utf-8")), ""
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")[:300]
        except Exception:
            pass
        return e.code, None, body
    except Exception as e:
        return 0, None, f"{type(e).__name__}: {e}"


def cmd_fetch(limit: int | None) -> int:
    if get_key is None:
        print("  UNMEASURED: cedar_keys_env unavailable.")
        return 1
    key = get_key("CONGRESS_API_KEY", required=False)
    if not key:
        print("  UNMEASURED: no CONGRESS_API_KEY resolvable. Nothing fetched, "
              "and this is NOT evidence the source lacks the data.")
        return 1
    print(f"  key {mask(key)}")

    targets = load_targets()
    todo = [t for t in targets
            if t["bill_type"] in CANONICAL and not cache_path(t).exists()]
    if limit:
        todo = todo[:limit]
    print(f"  {len(todo):,} bills to fetch (of {len(targets):,}); "
          f"pacing {SLEEP_S}s, hard stop {MAX_RUN_S}s")
    if not todo:
        print("  nothing to do.")
        return 0

    if not take_hostlock([t["bill_id"] for t in todo]):
        return 0

    RAW.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    sleep_s = SLEEP_S
    n_ok = n_zero = n_absent = n_err = 0
    try:
        for i, t in enumerate(todo, 1):
            if time.time() - t0 > MAX_RUN_S:
                print(f"  HARD STOP at {MAX_RUN_S}s. {i-1} done, "
                      f"{len(todo)-i+1} left. Re-run `fetch` to resume.")
                break
            url = SOURCE_URL_TMPL.format(**t)
            rows: list[dict] = []
            reported = None
            status = "ok"
            note = ""
            offset = 0
            for attempt in range(1, MAX_ATTEMPTS + 1):
                u = url + f"?limit={PAGE}&offset={offset}"
                code, data, body = api_get(u, key)
                if code == 200 and data is not None:
                    pag = data.get("pagination") or {}
                    reported = pag.get("count")
                    rows.extend(data.get("cosponsors") or [])
                    if reported is not None and len(rows) < int(reported):
                        offset += PAGE
                        time.sleep(sleep_s)
                        continue
                    break
                if code == 404:
                    status, note = "no_api_record", "HTTP 404 on /cosponsors"
                    break
                if code == 429:
                    sleep_s = min(sleep_s * 2, 8.0)
                    wait = min(60 * (2 ** (attempt - 1)), 900)
                    print(f"    429 - backing off {wait}s, pace now {sleep_s}s")
                    time.sleep(wait)
                    continue
                if attempt == MAX_ATTEMPTS:
                    status = "attempt_failed"
                    note = f"HTTP {code} {body[:120]}"
                else:
                    time.sleep(min(30 * (2 ** (attempt - 1)), 300))
            if status == "ok" and not rows:
                status = "zero_cosponsors_reported"
            if status == "ok":
                n_ok += 1
            elif status == "zero_cosponsors_reported":
                n_zero += 1
            elif status == "no_api_record":
                n_absent += 1
            else:
                n_err += 1

            obj = {"bill_id": t["bill_id"], "congress": t["congress"],
                   "bill_type": t["bill_type"], "number": t["number"],
                   "status": status, "note": note,
                   "count_reported": reported,
                   "fetched_utc": datetime.now(timezone.utc).isoformat(),
                   "source_url": url, "cosponsors": rows}
            if status != "attempt_failed":
                p = cache_path(t)
                p.parent.mkdir(parents=True, exist_ok=True)
                tmp = p.with_suffix(".json.part")
                tmp.write_text(json.dumps(obj), encoding="utf-8")
                os.replace(tmp, p)
            with open(FETCHLOG, "a", encoding="utf-8") as f:
                f.write(json.dumps({k: v for k, v in obj.items()
                                    if k != "cosponsors"}) + "\n")
            if i % 100 == 0 or i == len(todo):
                el = time.time() - t0
                print(f"  [{i:>5,}/{len(todo):,}] {el/60:5.1f} min  "
                      f"ok {n_ok:,} zero {n_zero:,} absent {n_absent:,} "
                      f"err {n_err:,}  rate {i/max(el,1):.2f}/s", flush=True)
            time.sleep(sleep_s)
    finally:
        release_hostlock()
    print(f"  fetch done. ok {n_ok:,} / zero {n_zero:,} / absent {n_absent:,} "
          f"/ err {n_err:,}")
    return 0


# ---------------------------------------------------------------------------
# apply
# ---------------------------------------------------------------------------


def cmd_apply() -> int:
    targets = load_targets()
    by_id = {t["bill_id"]: t for t in targets}

    fetched: dict[str, dict] = {}
    for p in sorted(RAW.rglob("*.json")):
        if p.name.startswith("_"):
            continue
        try:
            o = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  SKIP unreadable {p.name}: {e}")
            continue
        if o.get("bill_id") in by_id:
            fetched[o["bill_id"]] = o
    print(f"  cache read: {len(fetched):,} bill objects")

    legacy_by_bill: dict[str, list[dict]] = {}
    if LEGACY.exists():
        for r in read_csv(LEGACY):
            legacy_by_bill.setdefault(r["bill_id"], []).append(r)
    legacy_log = {r["bill_id"]: r for r in read_csv(LEGACY_LOG)} \
        if LEGACY_LOG.exists() else {}
    print(f"  legacy read: {sum(len(v) for v in legacy_by_bill.values()):,} rows "
          f"over {len(legacy_by_bill):,} bills")

    rows: list[dict] = []
    cov: list[dict] = []
    agree = disagree = 0
    disagree_examples: list[str] = []

    for t in targets:
        bid = t["bill_id"]
        base = {"bill_id": bid, "congress": t["congress"],
                "chamber": t["chamber"], "bill_type": t["bill_type"],
                "bill_number": t["number"]}
        url = SOURCE_URL_TMPL.format(**t)
        o = fetched.get(bid)
        leg = legacy_by_bill.get(bid, [])

        if o is not None:
            src_rows = o.get("cosponsors") or []
            for c in src_rows:
                rows.append(dict(base, **{
                    "cosponsor_bioguide_id": c.get("bioguideId", "") or "",
                    "cosponsor_full_name": c.get("fullName", "") or "",
                    "cosponsor_party": c.get("party", "") or "",
                    "cosponsor_state": c.get("state", "") or "",
                    "cosponsor_district": ("" if c.get("district") in (None, "")
                                           else str(c.get("district"))),
                    "sponsorship_date": c.get("sponsorshipDate", "") or "",
                    "is_original_cosponsor": (
                        "Y" if c.get("isOriginalCosponsor") is True
                        else ("N" if c.get("isOriginalCosponsor") is False else "")),
                    "sponsorship_withdrawn_date":
                        c.get("sponsorshipWithdrawnDate", "") or "",
                    "record_basis": "congress_gov_api_v3_cosponsors_1145",
                    "source_url": url,
                    "fetched_date": (o.get("fetched_utc") or "")[:10],
                }))
            status = o.get("status", "ok")
            reported = o.get("count_reported")
            basis = ("congress.gov /v3/bill/{congress}/{bill_type}/{number}"
                     "/cosponsors, HTTP 200".format(**t)
                     if status in ("ok", "zero_cosponsors_reported")
                     else o.get("note", ""))
            # legacy cross-check: same bill seen twice, by two passes
            if leg:
                a = {r["bioguide_id"] for r in leg if r.get("bioguide_id")}
                b = {r.get("bioguideId", "") for r in src_rows}
                b.discard("")
                if a and b:
                    if a == b:
                        agree += 1
                    else:
                        disagree += 1
                        if len(disagree_examples) < 8:
                            disagree_examples.append(
                                f"{bid}: legacy {len(a)} vs fetched {len(b)}, "
                                f"symmetric difference {len(a ^ b)}")
            n_ret = len(src_rows)
        elif leg:
            for r in leg:
                rows.append(dict(base, **{
                    "cosponsor_bioguide_id": r.get("bioguide_id", "") or "",
                    "cosponsor_full_name": r.get("full_name", "") or "",
                    "cosponsor_party": r.get("party", "") or "",
                    "cosponsor_state": r.get("state", "") or "",
                    "cosponsor_district": r.get("district", "") or "",
                    "sponsorship_date": r.get("sponsorship_date", "") or "",
                    "is_original_cosponsor": (
                        "Y" if str(r.get("is_original", "")).lower() == "true"
                        else ("N" if str(r.get("is_original", "")).lower() == "false"
                              else "")),
                    "sponsorship_withdrawn_date": "",
                    "record_basis": "legacy__cosponsors_csv",
                    "source_url": url,
                    "fetched_date": "",
                }))
            status = "ok_legacy_only"
            reported = (legacy_log.get(bid, {}) or {}).get("n_cosponsors")
            basis = ("data/clean/_cosponsors.csv, an unnumbered earlier pass "
                     "promoted by 1145; not re-fetched")
            n_ret = len(leg)
        else:
            lg = legacy_log.get(bid)
            if t["bill_type"] not in CANONICAL:
                status = "SOURCE_DOES_NOT_PUBLISH_ON_BILL_ENDPOINT"
                basis = (f"bill_type {t['bill_type']!r} is not a canonical "
                         f"congress.gov slug; /bill has no such path "
                         f"(established by code/1092)")
            elif lg:
                status = lg.get("status", "") or "NEVER_CHECKED"
                basis = "data/clean/_cosponsor_fetch_log.csv, earlier pass"
            else:
                status = "NEVER_CHECKED"
                basis = "no artefact records an attempt"
            reported = (lg or {}).get("n_cosponsors")
            n_ret = 0

        nb_count = t["cosponsor_count"]
        nbc = ""
        try:
            nbc = str(int(float(nb_count))) if nb_count not in ("", "nan") else ""
        except Exception:
            nbc = ""
        rep = "" if reported in (None, "", "nan") else str(reported)
        if nbc and rep:
            ag = "Y" if nbc == rep else "N"
        else:
            ag = "NOT_TESTABLE"
        cov.append(dict(base, **{
            "cosponsor_lookup_status": status,
            "n_cosponsors_retrieved": n_ret,
            "n_cosponsors_reported_by_source": rep,
            "cosponsor_count_in_native_bills": nbc,
            "count_agrees_with_native_bills": ag,
            "cosponsor_lookup_basis": basis,
            "source_url": url,
            "fetched_date": BUILD_DATE,
        }))

    backup(OUT_ROWS, "1145_cosponsor_harvest")
    backup(OUT_COV, "1145_cosponsor_harvest")
    write_csv(OUT_ROWS, OUT_COLS, rows)
    write_csv(OUT_COV, COV_COLS, cov)

    bills = {r["bill_id"] for r in rows}
    from collections import Counter
    st = Counter(c["cosponsor_lookup_status"] for c in cov)
    basis_ct = Counter(r["record_basis"] for r in rows)
    ag_ct = Counter(c["count_agrees_with_native_bills"] for c in cov)
    print(f"  WROTE {OUT_ROWS.name}: {len(rows):,} rows over {len(bills):,} bills")
    print(f"  WROTE {OUT_COV.name}: {len(cov):,} rows (one per native bill)")
    print(f"  record_basis: {dict(basis_ct)}")
    print(f"  lookup_status: {dict(st)}")
    print(f"  count agrees with native_bills.cosponsor_count: {dict(ag_ct)}")
    print(f"  legacy vs fetched roster on the same bill: "
          f"{agree} agree, {disagree} disagree")
    for e in disagree_examples:
        print(f"    {e}")
    return 0


# ---------------------------------------------------------------------------
# verify  - FAILS when the work did not land
# ---------------------------------------------------------------------------


def _fail(inv: str, msg: str) -> None:
    print(f"  FAIL {inv}: {msg}")


def cmd_verify(quiet: bool = False) -> int:
    bad = 0
    if not OUT_ROWS.exists():
        _fail("CS-1", f"{OUT_ROWS.name} does not exist. The work did not land.")
        return 1
    if not OUT_COV.exists():
        _fail("CS-2", f"{OUT_COV.name} does not exist.")
        return 1
    rows = read_csv(OUT_ROWS)
    cov = read_csv(OUT_COV)
    nb = read_csv(NATIVE_BILLS)
    nb_ids = {r["bill_id"] for r in nb}

    # CS-1  the intended DELTA, with a floor. Not a conservation check.
    bills = {r["bill_id"] for r in rows}
    if len(rows) < MIN_ROWS:
        _fail("CS-1", f"{len(rows):,} cosponsor rows < floor {MIN_ROWS:,}. "
                      f"The harvest did not land or was reverted.")
        bad += 1
    if len(bills) < MIN_BILLS:
        _fail("CS-1b", f"{len(bills):,} bills covered < floor {MIN_BILLS:,}.")
        bad += 1

    # CS-2  every bill_id is a real native_bills key
    orphan = bills - nb_ids
    if orphan:
        _fail("CS-2", f"{len(orphan)} bill_id values are not in "
                      f"native_bills.csv, e.g. {sorted(orphan)[:5]}")
        bad += 1

    # CS-3  coverage accounts for EVERY native bill, exactly once
    cov_ids = [c["bill_id"] for c in cov]
    if set(cov_ids) != nb_ids or len(cov_ids) != len(set(cov_ids)):
        _fail("CS-3", f"coverage has {len(cov_ids):,} rows / "
                      f"{len(set(cov_ids)):,} distinct against "
                      f"{len(nb_ids):,} native bills")
        bad += 1

    # CS-4  primary key unique
    seen: dict[tuple, int] = {}
    for r in rows:
        k = (r["bill_id"], r["cosponsor_bioguide_id"], r["sponsorship_date"])
        seen[k] = seen.get(k, 0) + 1
    dupes = {k: v for k, v in seen.items() if v > 1}
    if dupes:
        _fail("CS-4", f"{len(dupes)} duplicate (bill_id, bioguide_id, "
                      f"sponsorship_date) keys, e.g. {list(dupes)[:3]}")
        bad += 1

    # CS-5  no row without an identifier for the cosponsor
    nobio = sum(1 for r in rows if not r["cosponsor_bioguide_id"].strip())
    if nobio:
        _fail("CS-5", f"{nobio:,} rows carry no cosponsor_bioguide_id")
        bad += 1

    # CS-6  every row declares where it came from
    nobasis = sum(1 for r in rows if not r["record_basis"].strip())
    if nobasis:
        _fail("CS-6", f"{nobasis:,} rows carry no record_basis")
        bad += 1

    if not quiet:
        from collections import Counter
        st = Counter(c["cosponsor_lookup_status"] for c in cov)
        print(f"  rows {len(rows):,} / bills {len(bills):,} / coverage "
              f"{len(cov):,} / native_bills {len(nb_ids):,}")
        print(f"  status: {dict(st)}")
        print("  " + ("VERIFY OK" if bad == 0 else f"VERIFY FAILED ({bad})"))
    return 1 if bad else 0


def cmd_selftest() -> int:
    """Inject each breach, assert exit 1 AND the named invariant fires,
    restore from a literal path, assert exit 0."""
    if not OUT_ROWS.exists():
        print("  UNMEASURED: run `apply` first; selftest needs a live table.")
        return 1
    if cmd_verify(quiet=True) != 0:
        print("  UNMEASURED: the live table is already failing verify; "
              "selftest cannot distinguish its own injection.")
        return 1
    bak_r = OUT_ROWS.with_suffix(".csv.selftest_bak")
    bak_c = OUT_COV.with_suffix(".csv.selftest_bak")
    shutil.copy2(OUT_ROWS, bak_r)
    shutil.copy2(OUT_COV, bak_c)
    ok = True
    try:
        rows = read_csv(OUT_ROWS)
        cov = read_csv(OUT_COV)

        cases = [
            ("CS-1", lambda: write_csv(OUT_ROWS, OUT_COLS, rows[:10])),
            ("CS-2", lambda: write_csv(
                OUT_ROWS, OUT_COLS,
                rows + [dict(rows[0], bill_id="999-zz-999999")])),
            ("CS-3", lambda: write_csv(OUT_COV, COV_COLS, cov[:-1])),
            ("CS-4", lambda: write_csv(OUT_ROWS, OUT_COLS, rows + [rows[0]])),
            ("CS-5", lambda: write_csv(
                OUT_ROWS, OUT_COLS,
                rows + [dict(rows[0], cosponsor_bioguide_id="")])),
            ("CS-6", lambda: write_csv(
                OUT_ROWS, OUT_COLS, rows + [dict(rows[0], record_basis="")])),
        ]
        for inv, inject in cases:
            shutil.copy2(bak_r, OUT_ROWS)
            shutil.copy2(bak_c, OUT_COV)
            inject()
            buf = io.StringIO()
            real, sys.stdout = sys.stdout, buf
            try:
                rc = cmd_verify(quiet=True)
            finally:
                sys.stdout = real
            out = buf.getvalue()
            fired = (rc == 1) and (inv in out or inv + "b" in out)
            print(f"  {inv}: exit {rc}, "
                  f"{'FIRED' if fired else 'DID NOT FIRE'}"
                  f"{'' if fired else '  <-- selftest failure'}")
            ok = ok and fired
    finally:
        shutil.copy2(bak_r, OUT_ROWS)
        shutil.copy2(bak_c, OUT_COV)
        bak_r.unlink(missing_ok=True)
        bak_c.unlink(missing_ok=True)
    rc = cmd_verify(quiet=True)
    print(f"  restored, verify exit {rc}")
    ok = ok and rc == 0
    print("  SELFTEST " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    if cmd == "report":
        return cmd_report()
    if cmd == "fetch":
        return cmd_fetch(limit)
    if cmd == "apply":
        return cmd_apply()
    if cmd == "verify":
        return cmd_verify()
    if cmd == "selftest":
        return cmd_selftest()
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
