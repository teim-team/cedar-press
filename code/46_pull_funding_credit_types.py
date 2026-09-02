#!/usr/bin/env python3
"""
Cedar Press - 46: Dataset 3 credit programmes (assistance types 07, 08, 09).

WHAT IS MISSING AND WHY IT MATTERS
----------------------------------
The Dataset 3 spine holds 7 of USAspending's 10 assistance types. Measured over
all 476,924 rows, `assistance_type_code` takes exactly seven values:

    06 188,824 · 04 112,915 · 02 71,028 · 03 68,643 · 05 19,096 · 10 10,084 · 11 6,334

Absent: 07 direct loan, 08 guaranteed/insured loan, 09 insurance. All three are
CREDIT programmes. That is a real gap for Native economy coverage, because
loan guarantees are how much tribal housing, business and infrastructure
financing actually flows.

Window: FY2007-10-01 .. today. (The spine begins FY2008; FY2007 is requested so
the floor is MEASURED rather than assumed. A zero return for FY2007 is a
finding, and is recorded as one.)

WHAT THIS SCRIPT WILL NOT DO
----------------------------
It will not run while another process holds api.usaspending.gov. Rule 1 of
docs/PULL_DISCIPLINE.md - one poller per host, ever. `ps aux` CANNOT see
command lines on Windows, so the check uses Win32_Process.CommandLine. Four
concurrent pullers earned a ~62-minute IP cooldown on 2026-08-05.

THE POPULATION FILTER - REPRODUCED, NOT INVENTED
------------------------------------------------
The spine is NOT full-universe assistance. Across all 476,924 rows
`business_types_code` takes exactly three values (I 427,596 · K 46,666 ·
J 2,662) = USAspending Recipient Type "tribal". The API equivalent is
`recipient_type_names: ["indian_native_american_tribal_government"]`, which
works on `download/transactions/` but NOT on `bulk_download/awards/`. A blind
full-universe pull would create a population mismatch that no total, count or
date range would reveal.

THE TRAP THIS SCRIPT IS BUILT AROUND
------------------------------------
`recipient_type_names` does NOT validate its input. A bogus value returns HTTP
200 with an EMPTY result set, not an error. An empty result is not evidence of
absence - it may be evidence of a typo. Since credit rows are expected to be
RARE (the 2026-08-05 forward fill returned 6 across 3.3 years), a near-empty
result is exactly what a silent filter failure also looks like. The two are
distinguished by GATE 2 below, which proves the filter restricts by comparing
against an UNFILTERED count on the same window.

GATES - all enforced in code, before any download job is submitted
------------------------------------------------------------------
GATE 1  ROUTE. Re-count two years we ALREADY hold, through this exact endpoint
        and filter, using the seven spine award types. FY2022 must land near
        44,297 and FY2021 near 43,604 (the spine's own counts). The prior
        forward fill measured +0.11% and +0.40%; tolerance here is 2%, and the
        delta must be POSITIVE (later corrections accrue, they do not vanish).
        A negative delta means a narrower population, not a later snapshot.

GATE 2  THE FILTER RESTRICTS. Same window, same credit award types, counted
        WITH and WITHOUT `recipient_type_names`. Unfiltered must be materially
        larger. If filtered == unfiltered the filter is being ignored; if both
        are 0 the probe is uninformative and cannot license a conclusion.

GATE 3  THE FILTER STRING IS LIVE. The tribal filter must return non-zero on
        grant types over the same window (established by GATE 1). This is what
        separates "this population genuinely has few loans" from "the filter
        value is a typo returning HTTP 200 and nothing".

Only when 1-3 pass does the script submit download jobs.

DOLLARS - read code/24_generate_dataset_docs.py SPEC["03_funding"] first
-----------------------------------------------------------------------
Loan amounts are NOT obligations and must never be summed with them. Credit
rows carry `federal_action_obligation` = 0.00 (all 6 retrieved so far do) and
report money in `face_value_of_loan` and `original_loan_subsidy_cost` instead.
`total_face_value_of_loan` / `total_loan_subsidy_cost` are AWARD-CUMULATIVE and
must never be summed across transactions. All of these fields are SIGNED.
This script reports the three money fields separately and never pools them.

ATTRIBUTION
-----------
Exact `recipient_uei` against data/clean/cedar_identifier_ledger_final.csv only.
Tier C is NOT an attribution (`tribe_id` is blank on nearly all tier-C rows);
counting tier C once fabricated 285 links where the truth was 113. Tier X is an
exclusion ruling - a ledger hit, never a Native match. A and B are reported
separately.

Run:
    py -3 code/46_pull_funding_credit_types.py gates    # cheap probes only, no download job
    py -3 code/46_pull_funding_credit_types.py pull     # gates, then download jobs
    py -3 code/46_pull_funding_credit_types.py build    # offline: counts, attribution, _SOURCE.md
"""

import csv
import datetime
import json
import os
import subprocess
import sys
import time
import zipfile

import requests

csv.field_size_limit(10_000_000)

CEDAR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(CEDAR, "data", "raw", "federal_funding",
                      "usaspending_credit_2026-08-06")
LOGDIR = os.path.join(CEDAR, "logs")
REVIEW = os.path.join(CEDAR, "review")
LEDGER = os.path.join(CEDAR, "data", "clean", "cedar_identifier_ledger_final.csv")
LOCKFILE = os.path.join(LOGDIR, "_HOSTLOCK_api.usaspending.gov.json")

API = "https://api.usaspending.gov"
HOST = "api.usaspending.gov"
UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
    "Content-Type": "application/json",
}

CREDIT_TYPES = ["07", "08", "09"]
SPINE_TYPES = ["02", "03", "04", "05", "06", "10", "11"]
RECIPIENT_TYPE = "indian_native_american_tribal_government"
TRIBAL_BUSINESS_TYPES = ("I", "J", "K")
PULL_DATE = "2026-08-06"

# Spine's own transaction counts, from a streaming scan of the spine (recorded
# in data/raw/federal_funding/usaspending_2023_2026/_SOURCE.md §3). GATE 1
# targets. These are measurements, not estimates.
GATE1_TARGETS = {
    "fy2022": {"start": "2021-10-01", "end": "2022-09-30", "spine": 44297},
    "fy2021": {"start": "2020-10-01", "end": "2021-09-30", "spine": 43604},
}
GATE1_TOLERANCE = 0.02          # 2%; prior route measured +0.11% and +0.40%

# One chunk per fiscal year. `download/transactions/` has been run at one-year
# granularity throughout this project; keep it, so a failure costs one year.
def _chunks():
    out = [("fy2007", "2006-10-01", "2007-09-30")]
    for fy in range(2008, 2023):
        out.append((f"fy{fy}", f"{fy-1}-10-01", f"{fy}-09-30"))
    # FY2023 up to the spine's last action_date; 2023-04-06 onward already held.
    out.append(("fy2023_to_spine_cut", "2022-10-01", "2023-04-05"))
    return out


CHUNKS = _chunks()

os.makedirs(OUTDIR, exist_ok=True)
os.makedirs(LOGDIR, exist_ok=True)
LOGPATH = os.path.join(LOGDIR, "46_funding_credit_types.log")
_logf = open(LOGPATH, "a", encoding="utf-8")


def log(msg):
    line = f"[{datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M:%S}Z] {msg}"
    print(line, flush=True)
    _logf.write(line + "\n")
    _logf.flush()


# ---------------------------------------------------------------------------
# Rule 1 - one poller per host. This must run before ANY request, including a
# probe. `ps aux` on Windows cannot see command lines and returns 0 pullers
# while four are live; a check that cannot observe what it claims to check is
# worse than no check, because it manufactures confidence.
# ---------------------------------------------------------------------------
PULLER_MARKERS = ("usaspending", "_pull", "wait_and_pull", "wait_then_pull",
                  "resume_subaward", "funding_forward_fill", "pull_contracts")


def other_pullers():
    """Live processes whose command line looks like a USAspending puller.

    Self and OUR OWN ANCESTORS are excluded by walking ParentProcessId. Without
    that walk this guard blocks itself: `py -3 code/46_...py pull` leaves the
    py.exe launcher and the invoking shell holding this script's name on their
    own command lines, and the guard reads them as a competing puller. Observed,
    not theorised - the first version of this function returned 8 hits, of which
    4 were its own ancestry.

    Everything else errs toward refusing to pull. A false positive costs a
    deferral; a false negative costs an hour of IP cooldown for every agent on
    this machine.
    """
    ps = ("Get-CimInstance Win32_Process | "
          "Select-Object ProcessId,ParentProcessId,CommandLine | "
          "ConvertTo-Json -Compress")
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-NonInteractive",
                              "-Command", ps],
                             capture_output=True, text=True, timeout=120).stdout
        procs = json.loads(out) if out.strip() else []
    except Exception as e:                                       # noqa: BLE001
        raise RuntimeError(
            f"Cannot enumerate processes ({type(e).__name__}: {e}). Refusing to "
            f"pull: an unverifiable host lock is not a free host.") from e
    if not isinstance(procs, list):
        procs = [procs]
    parent = {p.get("ProcessId"): p.get("ParentProcessId")
              for p in procs if p}

    # our own ancestry, so we never mistake our launcher for a rival
    mine, cur = set(), os.getpid()
    while cur and cur not in mine:
        mine.add(cur)
        cur = parent.get(cur)

    hits = []
    for p in procs:
        cl = (p or {}).get("CommandLine") or ""
        pid = (p or {}).get("ProcessId")
        if pid is None or pid in mine:
            continue
        low = cl.lower()
        if not (".py" in low or ".sh" in low):
            continue
        if os.path.basename(__file__).lower() in low or \
                any(m in low for m in PULLER_MARKERS):
            hits.append((pid, cl))
    return hits


def require_free_host():
    hits = other_pullers()
    if hits:
        log(f"HOST HELD - {len(hits)} live puller process(es):")
        for pid, cl in hits:
            log(f"    PID {pid}: {cl.strip()[:160]}")
        log("Rule 1 (docs/PULL_DISCIPLINE.md): one poller per host, ever.")
        log(f"Appending to {os.path.basename(LOCKFILE)} queue and exiting. "
            f"ZERO requests issued.")
        _append_to_lock(hits)
        sys.exit(0)
    log("host free - no other USAspending puller visible via Win32_Process")


def _append_to_lock(hits):
    try:
        d = json.load(open(LOCKFILE, encoding="utf-8")) \
            if os.path.exists(LOCKFILE) else {"host": HOST}
    except Exception:                                            # noqa: BLE001
        return
    d.setdefault("queue_appended_by_dataset3_federal_funding", [])
    d["queue_appended_by_dataset3_federal_funding"].append({
        "job": "funding_credit_programmes_fy2007_fy2023",
        "runner": "code/46_pull_funding_credit_types.py",
        "award_types": CREDIT_TYPES,
        "deferred_at": datetime.datetime.now(datetime.timezone.utc)
                               .strftime("%Y-%m-%dT%H:%MZ"),
        "blocked_by": [f"PID {p}" for p, _ in hits],
        "requests_issued": 0,
    })
    json.dump(d, open(LOCKFILE, "w", encoding="utf-8"), indent=2)


# ---------------------------------------------------------------------------
# Requests. Back off exponentially (60s doubling to 30 min), never on a fixed
# metronome - to an edge filter a metronome looks exactly like the traffic that
# earned the block.
# ---------------------------------------------------------------------------
def post(url, body, tries=5, timeout=180):
    delay, last = 60, None
    for k in range(tries):
        t0 = time.time()
        try:
            r = requests.post(url, json=body, headers=UA, timeout=timeout)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                ra = int(r.headers.get("Retry-After", delay))
                log(f"  429 throttle; honouring Retry-After={ra}s")
                time.sleep(ra)
                continue
            last = f"HTTP {r.status_code}: {r.text[:300]}"
        except Exception as e:                                   # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
            if time.time() - t0 < 1:
                last += "  <-- sub-second failure = EDGE BLOCK, not a slow server"
        log(f"  attempt {k+1}/{tries}: {last}")
        time.sleep(delay)
        delay = min(delay * 2, 1800)
    raise RuntimeError(f"POST {url} failed after {tries} tries. Last: {last}")


def tx_count(start, end, types, with_filter=True):
    """Cheapest endpoint that answers 'how many transactions'. Never the real job."""
    filt = {"time_period": [{"start_date": start, "end_date": end,
                             "date_type": "action_date"}],
            "award_type_codes": types}
    if with_filter:
        filt["recipient_type_names"] = [RECIPIENT_TYPE]
    r = post(f"{API}/api/v2/search/spending_by_transaction_count/",
             {"filters": filt})
    res = r.get("results", {}) or {}
    # assistance buckets: grants, direct_payments, loans, other
    return sum(v for v in res.values() if isinstance(v, (int, float))), res


# ---------------------------------------------------------------------------
# GATES
# ---------------------------------------------------------------------------
def gates():
    require_free_host()
    report = {"probed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "gate1": {}, "gate2": {}, "verdict": None}
    ok = True

    log("GATE 1 - route validation against years already held")
    for tag, t in GATE1_TARGETS.items():
        n, buckets = tx_count(t["start"], t["end"], SPINE_TYPES, with_filter=True)
        delta = (n - t["spine"]) / t["spine"]
        good = abs(delta) <= GATE1_TOLERANCE and delta >= 0
        log(f"  {tag}: API {n:,} vs spine {t['spine']:,}  "
            f"delta {delta:+.2%}  {'PASS' if good else 'FAIL'}  {buckets}")
        report["gate1"][tag] = {"api": n, "spine": t["spine"],
                                "delta": round(delta, 5), "pass": good,
                                "buckets": buckets}
        ok &= good
        time.sleep(10)

    log("GATE 2 - prove recipient_type_names actually RESTRICTS")
    for tag, t in GATE1_TARGETS.items():
        f_n, _ = tx_count(t["start"], t["end"], CREDIT_TYPES, with_filter=True)
        time.sleep(10)
        u_n, _ = tx_count(t["start"], t["end"], CREDIT_TYPES, with_filter=False)
        restricts = u_n > 0 and f_n < u_n
        log(f"  {tag} credit types: filtered {f_n:,} vs unfiltered {u_n:,}  "
            f"{'PASS - filter restricts' if restricts else 'FAIL'}")
        if u_n == 0:
            log("    unfiltered is 0 - probe is UNINFORMATIVE; a zero filtered "
                "result here licenses no conclusion about absence")
        report["gate2"][tag] = {"filtered": f_n, "unfiltered": u_n,
                                "restricts": restricts}
        ok &= restricts
        time.sleep(10)

    report["verdict"] = "PASS" if ok else "FAIL"
    json.dump(report, open(os.path.join(OUTDIR, "_gates.json"), "w",
                           encoding="utf-8"), indent=2)
    log(f"GATES {report['verdict']} -> {OUTDIR}/_gates.json")
    if not ok:
        log("STOP. Do not submit download jobs on a failed gate. Report the "
            "failure with the probe evidence - a failed gate is a finding.")
    return ok


# ---------------------------------------------------------------------------
# PULL
# ---------------------------------------------------------------------------
def payload_for(start, end):
    return {"filters": {"time_period": [{"start_date": start, "end_date": end,
                                         "date_type": "action_date"}],
                        "award_type_codes": CREDIT_TYPES,
                        "recipient_type_names": [RECIPIENT_TYPE]},
            "columns": [], "file_format": "csv"}


def _state_path():
    return os.path.join(OUTDIR, "_state.json")


def pull():
    # Rule 6: checkpoint BEFORE the first request, not after the last.
    state = json.load(open(_state_path(), encoding="utf-8")) \
        if os.path.exists(_state_path()) else {}
    state.setdefault("_meta", {}).update(
        {"script": "code/46_pull_funding_credit_types.py",
         "award_types": CREDIT_TYPES, "recipient_type_names": [RECIPIENT_TYPE],
         "endpoint": f"{API}/api/v2/download/transactions/",
         "chunks_planned": [c[0] for c in CHUNKS],
         "checkpoint_written_utc":
             datetime.datetime.now(datetime.timezone.utc).isoformat()})
    json.dump(state, open(_state_path(), "w", encoding="utf-8"), indent=2)

    if not gates():
        sys.exit(1)

    for tag, start, end in CHUNKS:
        rec = state.get(tag) or {}
        if rec.get("members"):
            log(f"{tag}: already on disk -- skip")
            continue
        require_free_host()          # re-check between years, not just at start

        # Rule 5: never re-submit a job the server already accepted.
        rp = os.path.join(OUTDIR, f"response_{tag}.json")
        if os.path.exists(rp):
            resp = json.load(open(rp, encoding="utf-8"))
            log(f"{tag}: reusing already-accepted job {resp.get('file_name')}")
        else:
            body = payload_for(start, end)
            json.dump({"endpoint": f"{API}/api/v2/download/transactions/",
                       "method": "POST",
                       "requested_utc":
                           datetime.datetime.now(datetime.timezone.utc).isoformat(),
                       "payload": body},
                      open(os.path.join(OUTDIR, f"request_{tag}.json"), "w",
                           encoding="utf-8"), indent=2)
            log(f"{tag}: POST download/transactions {start} .. {end}")
            resp = post(f"{API}/api/v2/download/transactions/", body)
            json.dump(resp, open(rp, "w", encoding="utf-8"), indent=2)

        file_name = resp.get("file_name")
        status_url = resp.get("status_url") or \
            f"{API}/api/v2/download/status/?file_name={file_name}"
        t0, status, s = time.time(), None, {}
        while time.time() - t0 < 10800:
            time.sleep(120)
            try:
                s = requests.get(status_url,
                                 headers={"User-Agent": UA["User-Agent"]},
                                 timeout=120).json()
            except Exception as e:                               # noqa: BLE001
                log(f"  poll dropped ({type(e).__name__}) - flaky, not fatal; "
                    f"the job keeps generating server-side")
                continue
            status = s.get("status")
            log(f"  {tag} status={status} rows={s.get('total_rows')} "
                f"elapsed={int(time.time()-t0)}s")
            if status in ("finished", "failed"):
                break
        if status != "finished":
            log(f"{tag}: not finished; job token PERSISTED in response_{tag}.json "
                f"- resume, do not resubmit")
            continue

        url = s.get("file_url") or \
            f"https://files.usaspending.gov/generated_downloads/{file_name}"
        r = requests.get(url, headers={"User-Agent": UA["User-Agent"]},
                         timeout=600, stream=True)
        zp = os.path.join(OUTDIR, file_name)
        with open(zp, "wb") as fh:
            for ch in r.iter_content(1 << 20):
                fh.write(ch)
        members = []
        with zipfile.ZipFile(zp) as z:
            for nm in z.namelist():
                z.extract(nm, OUTDIR)
                members.append(nm)
        log(f"{tag}: extracted {members}")
        state.setdefault(tag, {}).update(
            {"start": start, "end": end, "zip": file_name, "members": members,
             "status_json": s, "total_rows_reported": s.get("total_rows")})
        json.dump(state, open(_state_path(), "w", encoding="utf-8"), indent=2)
        time.sleep(60)               # be a good neighbour

    log("pull complete")


# ---------------------------------------------------------------------------
# BUILD - fully offline
# ---------------------------------------------------------------------------
def _read_ledger():
    order = {"A": 0, "B": 1, "C": 2, "X": 3}
    uei2 = {}
    with open(LEDGER, newline="", encoding="utf-8-sig", errors="replace") as fh:
        for row in csv.DictReader(fh):
            if (row.get("identifier_type") or "").strip().upper() != "UEI":
                continue
            v = (row.get("identifier") or "").strip().upper()
            if not v:
                continue
            t = (row.get("confidence_tier") or "").strip().upper()
            prev = uei2.get(v)
            if prev is None or order.get(t, 9) < order.get(prev["tier"], 9):
                uei2[v] = {"tier": t, "tribe_id": row.get("tribe_id") or "",
                           "canonical_name": row.get("canonical_name") or ""}
    return uei2


def build():
    import collections
    if not os.path.exists(_state_path()):
        sys.exit("no _state.json -- run `pull` first")
    state = json.load(open(_state_path(), encoding="utf-8"))
    uei2 = _read_ledger()
    led_mtime = datetime.datetime.fromtimestamp(
        os.path.getmtime(LEDGER)).strftime("%Y-%m-%d %H:%M:%S")

    # Three money fields, kept apart. Pooling them is the defect this whole
    # script exists to avoid.
    fy = collections.defaultdict(lambda: collections.Counter())
    fytype = collections.defaultdict(lambda: collections.Counter())
    bt = collections.Counter()
    tier_rows = collections.Counter()
    tier_face = collections.Counter()
    tier_subs = collections.Counter()
    new_ueis = collections.Counter()
    new_uei_face = collections.Counter()
    new_uei_name = {}
    award_snapshots = collections.defaultdict(set)
    blank_uei = collections.Counter()
    schemas = {}
    nonzero_obl_rows = []

    def num(x):
        try:
            return float(x or 0)
        except ValueError:
            return 0.0

    for tag, _s, _e in CHUNKS:
        rec = state.get(tag) or {}
        prime = [m for m in (rec.get("members") or [])
                 if m.lower().endswith(".csv") and "PrimeTransactions" in m]
        if not prime:
            log(f"{tag}: NO FILE")
            continue
        path = os.path.join(OUTDIR, prime[0])
        with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
            rd = csv.DictReader(fh)
            schemas[tag] = {"ncol": len(rd.fieldnames), "cols": rd.fieldnames}
            n = 0
            for r in rd:
                n += 1
                y = r.get("action_date_fiscal_year", "")
                t = (r.get("assistance_type_code") or "").strip()
                obl = num(r.get("federal_action_obligation"))
                face = num(r.get("face_value_of_loan"))
                subs = num(r.get("original_loan_subsidy_cost"))
                fy[y]["rows"] += 1
                fy[y]["obligation"] += obl
                fy[y]["face_value"] += face
                fy[y]["subsidy_cost"] += subs
                fytype[(y, t)]["rows"] += 1
                fytype[(y, t)]["face_value"] += face
                fytype[(y, t)]["subsidy_cost"] += subs
                fytype[(y, t)]["obligation"] += obl
                if obl:
                    nonzero_obl_rows.append(
                        (r.get("action_date"), t, r.get("recipient_name"), obl))
                bt[r.get("business_types_code", "")] += 1
                award_snapshots[r.get("assistance_award_unique_key", "")].add(
                    num(r.get("total_face_value_of_loan")))
                u = (r.get("recipient_uei") or "").strip().upper()
                if not u:
                    blank_uei["rows"] += 1
                    blank_uei["face_value"] += face
                    continue
                hit = uei2.get(u)
                if hit:
                    tier_rows[hit["tier"]] += 1
                    tier_face[hit["tier"]] += face
                    tier_subs[hit["tier"]] += subs
                else:
                    new_ueis[u] += 1
                    new_uei_face[u] += face
                    new_uei_name.setdefault(u, r.get("recipient_name", ""))
        log(f"{tag}: {n:,} rows, {schemas[tag]['ncol']} cols")

    print("\n=== BY FISCAL YEAR AND TYPE - three money fields, NEVER pooled ===")
    print(f"{'FY':6s} {'type':5s} {'rows':>7s} {'obligation':>16s} "
          f"{'face_value':>20s} {'subsidy_cost':>18s}")
    for (y, t) in sorted(fytype):
        c = fytype[(y, t)]
        print(f"{y:6s} {t:5s} {c['rows']:>7,} {c['obligation']:>16,.2f} "
              f"{c['face_value']:>20,.2f} {c['subsidy_cost']:>18,.2f}")

    print("\n=== LEDGER ATTRIBUTION - A and B reported SEPARATELY ===")
    print("Tier C is NOT an attribution. Tier X is an exclusion ruling, not a match.")
    for t in ("A", "B", "C", "X"):
        print(f"  tier {t}: rows {tier_rows[t]:,}  "
              f"face_value {tier_face[t]:,.2f}  subsidy {tier_subs[t]:,.2f}")
    print(f"  UEI not in ledger: {len(new_ueis):,} distinct, "
          f"{sum(new_ueis.values()):,} rows, face {sum(new_uei_face.values()):,.2f}")
    print(f"  BLANK recipient_uei: {blank_uei['rows']:,} rows, "
          f"face {blank_uei['face_value']:,.2f}  <-- structurally unattributable")

    print(f"\nbusiness_types_code: {dict(bt)}")
    outside = sum(v for k, v in bt.items()
                  if not any(c in (k or '') for c in TRIBAL_BUSINESS_TYPES))
    print(f"rows outside {{I,J,K}}: {outside:,}")
    if nonzero_obl_rows:
        print(f"\nNOTE: {len(nonzero_obl_rows):,} credit rows carry a NON-ZERO "
              f"federal_action_obligation. Every credit row retrieved before "
              f"today carried exactly 0.00. Inspect before pooling anything:")
        for r in nonzero_obl_rows[:10]:
            print("   ", r)

    dbl = {k: sorted(v) for k, v in award_snapshots.items() if len(v) > 1}
    print(f"\nawards whose total_face_value_of_loan snapshot VARIES across its "
          f"transactions: {len(dbl):,} (these are award-cumulative fields; "
          f"never sum them across rows)")

    ledger_ueis = sum(tier_rows[t] for t in ("A", "B"))
    summary = {
        "pull_date": PULL_DATE,
        "award_types": CREDIT_TYPES,
        "recipient_type_names": [RECIPIENT_TYPE],
        "ledger_mtime": led_mtime,
        "by_fy": {k: dict(v) for k, v in fy.items()},
        "by_fy_type": {f"{y}|{t}": dict(c) for (y, t), c in fytype.items()},
        "tier_rows": dict(tier_rows),
        "tier_face_value": {k: round(v, 2) for k, v in tier_face.items()},
        "tier_subsidy_cost": {k: round(v, 2) for k, v in tier_subs.items()},
        "attributed_rows_tier_A_plus_B": ledger_ueis,
        "new_ueis": len(new_ueis),
        "blank_uei_rows": blank_uei["rows"],
        "business_types_code": dict(bt),
        "schemas": {k: v["ncol"] for k, v in schemas.items()},
        "nonzero_obligation_credit_rows": len(nonzero_obl_rows),
    }
    json.dump(summary, open(os.path.join(OUTDIR, "_summary.json"), "w",
                            encoding="utf-8"), indent=2)

    os.makedirs(REVIEW, exist_ok=True)
    with open(os.path.join(REVIEW, "funding_credit_new_ueis_2026-08-06.csv"),
              "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["recipient_uei", "recipient_name", "rows",
                    "face_value_of_loan", "note", "YOUR_RULING"])
        for u, c in sorted(new_ueis.items(), key=lambda kv: -new_uei_face[kv[0]]):
            w.writerow([u, new_uei_name.get(u, ""), c, f"{new_uei_face[u]:.2f}",
                        "DISCOVERY POOL, NOT AN ATTRIBUTION. USAspending "
                        "recipient_type_names=indian_native_american_tribal_government; "
                        "UEI absent from cedar_identifier_ledger_final.csv. The "
                        "recipient-type filter admits false positives (GLENCORE LTD. "
                        "is coded K). Rule on each row's own evidence.", ""])
    log("build complete -- _summary.json and review queue written")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "gates"

    # --years 2020,2021,2022
    #
    # ADDED 2026-08-26. This script was written 2026-08-06, BEFORE the assistance
    # archive backfill of 2026-08-07/08 and 2026-08-12 landed credit types 07/08/09
    # in data/clean/federal_funding_transactions.csv. Measured today, the archive
    # route is a STRICT SUPERSET of this route on every year it covered - the
    # archive keeps rows under a UNION (recipient_type OR ledger_uei) while this
    # script keeps recipient_type ONLY:
    #
    #     FY      this route (API)   clean file (archive)   delta
    #     2011              761                     816       -55
    #     2018               19                      21        -2
    #     2023                2                      15       -13
    #     2020                7                       0        +7   <-- the gap
    #     2021                9                       0        +9   <-- the gap
    #     2022               34                       0       +34   <-- the gap
    #
    # So re-pulling FY2007-2019 and FY2023 would issue sixteen server-side jobs to
    # obtain FEWER rows than are already on disk. Only FY2020-FY2022 hold zero
    # credit rows, because those three archive objects were never fetched (local
    # disk, not the host - see docs/ASSISTANCE_ARCHIVE_PULL_LOG.md "Still owed").
    # Restricting is the same discipline as "a 404 is a fact about the object":
    # spend requests only where the gap is measured, not where it is assumed.
    if "--years" in sys.argv:
        want = {f"fy{y.strip()}" for y in
                sys.argv[sys.argv.index("--years") + 1].split(",")}
        CHUNKS = [c for c in CHUNKS if c[0] in want]
        if not CHUNKS:
            sys.exit("--years matched no chunk")
        log(f"--years restricts this run to {[c[0] for c in CHUNKS]}")

    if cmd == "gates":
        gates()
    elif cmd == "pull":
        pull()
    elif cmd == "build":
        build()
    else:
        sys.exit(__doc__)
