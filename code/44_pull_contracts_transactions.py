#!/usr/bin/env python3
"""
Cedar Press - 44: FY2023-2026 prime contract forward-fill, TRANSACTION level,
restricted to the UEIs the Cedar Press identifier ledger already knows.

WHY THIS SCRIPT EXISTS
----------------------
`data/clean/prime_contracts.csv` is transaction level and stops at FY2022.
Two earlier attempts to extend it failed for reasons that are now measured and
must not be re-litigated:

1. `POST /api/v2/download/awards/` returns AWARD SUMMARIES. 83.9% of its
   dollars sit on awards spanning several fiscal years with no per-FY
   obligation column, and 77.5% sit on awards whose base FY is 2022 or
   earlier - inside what the spine already covers. Appending it double-counts.
   See `data/raw/contracts/usaspending_gapfill_2026-08-05/_SOURCE.md` addendum A.
   THIS script uses `POST /api/v2/download/transactions/`.

2. No `recipient_type_names` flag combination reproduces the spine population.
   Best measured is +4.56% against a +0.11% bar, and the divergence is
   two-directional (40,685 filtered contracts vs 41,285 in the spine), so it is
   a population mismatch, not a calibratable offset. The spine's population is
   `hci_analysis.do`'s hand-built tribe-name match plus per-UEI exclusion
   rulings - a curated list, not a queryable attribute. See addendum B.

So this script does not chase the full spine. It selects by IDENTITY: the
ledger's own identifiers. That is a defined, reproducible, re-runnable
population.

SELECTION DECLARATION  (required by docs/PULL_DISCIPLINE.md, 2026-08-26)
------------------------------------------------------------------------
    legs used   : KNOWN_IDENTIFIER only
                  (ledger_uei | ledger_cage_resolved | ledger_parent_declared)
    leg missing : TYPE_FILTER
    every row this pull yields is population_basis = `ledger_identifier`
    per-UEI leg provenance ships beside the zips in `_pull_universe.csv`

**THE LIMITATION THAT FOLLOWS, AND IT IS NOT SMALL.** An identifier-seeded
pull cannot discover an entity we do not already know. Measured 2026-08-26 by
`code/276_measure_discovery_gap.py`, on two independent instruments that agree
to within 0.7 pp:

    prime, HigherGov flag-at-award extract, 1,101,796 rows
        12,643 entities carry a federal Native business-type flag
        9,719 of them - 76.87%, $70.96B - are outside this script's
        selection set

    assistance, 115's archive extracts, 701,458 rows, both legs run per row
        6,390 recipient entities in the union
        4,866 - 76.15% - are visible ONLY because a type filter ran

So this forward-fill is a LOWER BOUND, and the bound is roughly a QUARTER of
the entity universe rather than the "declining coverage" the section below
describes. It must be published as one. **The complement is not this script's
job to fix and must not be bolted on here** - it is the periodic discovery
sweep in `docs/PULL_DISCIPLINE.md`. What this script owes is the honest label.

THE THREE LEGS - AND THE ONE THAT WAS MISSING UNTIL 2026-08-26
---------------------------------------------------------------
This script selected on UEI alone while `114_pull_prime_archive.py`, pulling
the same universe from the static archive, matched on uei OR cage OR
parent_uei and recorded which in `match_key`. Measured against 114's own kept
rows, a UEI-only selection loses **75,303 of 904,282 rows across FY2007-2026
(8.33%)** - 31,336 to CAGE and 43,967 to a declared parent - and the loss
RISES steeply: 0.23% in FY2014, 12.66% in FY2025 (5,985 rows to CAGE alone),
**68.3% in FY2026**. See `pull_universe()` for the fix and for why the gate
was scoring this script against a target its own selection could never reach.

WHAT THIS ROUTE DOES AND DOES NOT REPRODUCE  (measured offline 2026-08-06)
--------------------------------------------------------------------------
The ledger-UEI population equals the spine's ATTRIBUTED rows, not the whole
spine. Restricting `prime_contracts.csv` to ledger tier-A+B UEIs and CAGEs
reproduces `attributed_flag == 1` to within 0.1%:

    FY      ledger-selected      full spine      share
    2019    $10.456B             $14.319B        73.0%
    2020    $11.999B             $16.626B        72.2%
    2021    $13.651B             $18.271B        74.7%
    2022    $13.644B             $19.974B        68.3%

Therefore the validation target below is the ATTRIBUTED series. Comparing a
ledger pull against the FULL spine total would show a false ~-30% failure.

And note the trend: ledger coverage of the spine is DECLINING (74.7% -> 68.3%).
FY2023-26 coverage will be lower still, because vendors enter that the ledger
has never seen. This forward-fill is a LOWER BOUND that loosens each year and
must be published as one. The fix is ledger growth, not a different endpoint.

IDVs ARE EXCLUDED, and that is measured, not assumed
----------------------------------------------------
Only 40 of the 18,251 distinct IDV PIIDs in
`Data Request 5-8-2023 IDVs.csv` appear in `prime_contracts.csv` - 0.2%. The
spine is contracts-only. Award types are ["A","B","C","D"]; adding IDV_A..E
would append a population FY2000-2022 never contained and break the seam.

HOST DISCIPLINE
---------------
`docs/PULL_DISCIPLINE.md` is binding. ONE worker. This script:
  - refuses to start if another puller holds `api.usaspending.gov`
    (checks Win32_Process CommandLine - NOT `ps`, which cannot see command
    lines on Windows and once reported zero pullers while four were running);
  - checkpoints `_state.json` BEFORE the first request;
  - never re-submits a job the server already accepted (handles are persisted
    and recovered);
  - backs off exponentially and distinguishes edge block / throttle / slow.

Reads  data/clean/cedar_identifier_ledger_final.csv
       data/clean/prime_contracts.csv          (validation targets only)
Writes data/raw/contracts/usaspending_transactions_2026-08-06/
         _state.json  _SOURCE.md  _filter_validation.json  *.zip
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
OUT = CEDAR / "data" / "raw" / "contracts" / "usaspending_transactions_2026-08-06"
LOGS = CEDAR / "logs"
LOCK = LOGS / "_HOSTLOCK_api.usaspending.gov.json"
STATE = OUT / "_state.json"

API = "https://api.usaspending.gov/api/v2"
FILES = "https://files.usaspending.gov/generated_downloads"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")

AWARD_TYPES = ["A", "B", "C", "D"]          # contracts only - see docstring
UEI_BATCH = 250                              # UEIs per job
POLL = 90                                    # seconds between status polls
MAX_WAIT = 10800                             # 3h per server-side job

# Validation targets are COMPUTED AT RUNTIME, never hardcoded.
#
# `prime_contracts.csv`'s `attributed_flag` is a SNAPSHOT of the ledger as it
# stood when code/40 last ran, and the ledger is live. It was rewritten at
# 2026-08-06T18:13:42Z during this very build: tier-A UEIs went 823 -> 781 and
# tier-A links 1,740 -> 1,699, which moved 13,945 rows and ~3.3% of attributed
# dollars. Gating a fresh pull against a stale flag would bake that drift in as
# a permanent -3% error. So the target is recomputed by applying the CURRENT
# ledger to the spine, and the ledger's fingerprint is recorded in _state.json
# alongside the result.
GATE_TOLERANCE = 0.05        # 5% - looser than the funding pull's 0.11% bar
                             # because this is a different population by
                             # construction (see docstring), not a replication.

FISCAL_YEARS = {
    2021: ("2020-10-01", "2021-09-30"),
    2022: ("2021-10-01", "2022-09-30"),
    2023: ("2022-10-01", "2023-09-30"),
    2024: ("2023-10-01", "2024-09-30"),
    2025: ("2024-10-01", "2025-09-30"),
    2026: ("2025-10-01", "2026-08-06"),      # partial - flagged in _SOURCE.md
}


# --------------------------------------------------------------------------
# logging / io
# --------------------------------------------------------------------------
def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg):
    line = f"[{now()}] {msg}"
    print(line, flush=True)
    LOGS.mkdir(exist_ok=True)
    with open(LOGS / "44_contracts_transactions.log", "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"created": now(), "jobs": {}, "filter_validated": False,
            "gate_passed": False, "notes": []}


def save_state(st):
    OUT.mkdir(parents=True, exist_ok=True)
    st["last_saved"] = now()
    tmp = STATE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(st, indent=2), encoding="utf-8")
    tmp.replace(STATE)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


# --------------------------------------------------------------------------
# RULE 1 - one poller per host, checked the only way that works on Windows
# --------------------------------------------------------------------------
PULLER_PAT = re.compile(
    r"(4[03]_pull_usaspending|43_resume_subaward|37_wait_then_pull|"
    r"37_contracts_gapfill|30_wait_and_pull|43_funding_forward_fill|"
    r"44_pull_contracts_transactions)",
    re.I)

# A process that merely MENTIONS a puller is not a puller. `tail -f` on a
# puller's log, and a shell sourcing a snapshot, both matched the naive
# pattern and would have blocked this script forever on a free host.
SPECTATOR_PAT = re.compile(
    r"(\\tail\.exe|\btail\b|\\grep\.exe|\bgrep\b|Get-Content|Select-String|"
    r"shell-snapshots|Win32_Process)", re.I)


def other_pullers_live():
    """Return [(pid, cmdline)] of live processes pulling api.usaspending.gov.

    `ps aux` CANNOT answer this on Windows - Git Bash's ps carries no command
    lines. On 2026-08-05 it returned zero while four pullers were running and
    an agent was told the host was free on the strength of it.
    """
    import os
    ps = ("Get-CimInstance Win32_Process | "
          "Select-Object ProcessId,ParentProcessId,CommandLine | "
          "ConvertTo-Json -Compress")
    try:
        raw = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                             capture_output=True, text=True, timeout=120).stdout
        procs = json.loads(raw)
    except Exception as e:                                # noqa: BLE001
        log(f"WARNING: could not enumerate processes ({e}). "
            "Refusing to start - a check that cannot run is not a pass.")
        return [(-1, "process enumeration failed")]

    # Walk up from self so the py.exe launcher that started THIS process is
    # not mistaken for a competing copy of this script.
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
        if SPECTATOR_PAT.search(cmd):
            continue
        if PULLER_PAT.search(cmd):
            hits.append((p["ProcessId"], cmd))
    return hits


def guard_host(force=False):
    live = other_pullers_live()
    if live and not force:
        log("HOST BUSY - refusing to start. Rule 1: one poller per host.")
        for pid, cmd in live:
            log(f"   pid {pid}: {cmd[:150]}")
        log(f"Append your work to {LOCK.name} 'queue' and wait. "
            "Re-run this script when the host is clear.")
        sys.exit(3)
    if live and force:
        log("--force given; proceeding DESPITE live pullers. This is how the "
            "2026-08-05 edge block happened. You had better have a reason.")


# --------------------------------------------------------------------------
# http with the three failure shapes distinguished
# --------------------------------------------------------------------------
class EdgeBlock(Exception):
    pass


def _post(url, payload, timeout=240):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _get(url, timeout=180):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def retry(fn, *a, tries=6, base=60, **kw):
    """Exponential backoff: 60s, 120s, 240s ... capped at 30 min.

    A fixed interval is not backoff - it is a metronome, and to an edge filter
    it looks exactly like the traffic that earned the block.
    """
    delay = base
    for i in range(tries):
        t0 = time.time()
        try:
            return fn(*a, **kw)
        except urllib.error.HTTPError as e:
            if e.code == 429:                                   # THROTTLE
                wait = int(e.headers.get("Retry-After", delay))
                log(f"  HTTP 429; honouring Retry-After={wait}s")
                time.sleep(wait)
            elif e.code >= 500:                                 # SERVER
                log(f"  HTTP {e.code}; retry in {delay}s")
                time.sleep(delay)
                delay = min(delay * 2, 1800)
            else:
                raise
        except Exception as e:                                  # noqa: BLE001
            elapsed = time.time() - t0
            if elapsed < 1.0:                                   # EDGE BLOCK
                log(f"  edge refusing after {elapsed:.2f}s ({e}). "
                    f"Backing off {delay}s. More requests EXTEND this.")
            else:
                log(f"  slow/failed after {elapsed:.0f}s ({e}); retry in {delay}s")
            if i == tries - 1:
                raise EdgeBlock(str(e)) from e
            time.sleep(delay)
            delay = min(delay * 2, 1800)
    raise EdgeBlock("retries exhausted")


# --------------------------------------------------------------------------
# ledger
# --------------------------------------------------------------------------
def ledger_ueis():
    import csv
    a, b, x = set(), set(), set()
    with open(CLEAN / "cedar_identifier_ledger_final.csv",
              encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            if (r.get("identifier_type") or "").strip().upper() != "UEI":
                continue
            u = (r.get("identifier") or "").strip().upper()
            if len(u) != 12:
                continue
            t = (r.get("confidence_tier") or "").strip()
            {"A": a, "B": b, "X": x}.get(t, set()).add(u)
    # X never publishes, but we still PULL them: an excluded UEI's rows are
    # evidence the exclusion is doing work, and dropping them at pull time
    # would make the exclusion unauditable. They are tagged, not omitted.
    return a, b, x


def ledger_cages():
    """Tier A/B/X CAGE codes. The ledger holds 5,966 CAGE rows and this script
    used NONE of them at selection time until 2026-08-26."""
    import csv
    out = {}
    with open(CLEAN / "cedar_identifier_ledger_final.csv",
              encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            if (r.get("identifier_type") or "").strip().upper() != "CAGE":
                continue
            c = (r.get("identifier") or "").strip().upper()
            t = (r.get("confidence_tier") or "").strip()
            if c and t in ("A", "B", "X"):
                out.setdefault(c, t)
    return out


def pull_universe():
    """THE THREE IDENTIFIER LEGS, AND WHY THIS FUNCTION EXISTS.

    Measured 2026-08-26 by `code/276_measure_discovery_gap.py` against the
    archive rows `code/114_pull_prime_archive.py` actually kept, which recorded
    WHICH identifier matched in `match_key`. A UEI-only selection - what this
    script did until today - does not reproduce them:

        FY      rows a UEI-only pull loses        of        entities lost
        2017    1,013                             43,695    85
        2019    2,800                             44,845    135
        2022    3,155                             46,634    153
        2023    3,501                             46,727    188
        2024    4,714                             53,966    233
        2025    6,301  (5,985 of them CAGE)       49,789    275
        2026    42,463 (39,004 declared-parent)   62,168    252

    The loss is not stable and it is not small. It runs 0.23% in FY2014 and
    68.3% in FY2026, and it RISES - which is the same direction as the
    ledger-coverage decline this script's own docstring already warns about.
    A forward-fill that loses two thirds of FY2026 is not a lower bound that
    "loosens each year"; it is a different population each year.

    The asymmetry that made this a real defect rather than a design choice:
    `gate_targets()` below computes its validation target as
    `awardee_uei IN ledger OR cage_code IN ledger` - UEI *or* CAGE - while the
    pull selected on UEI alone. The gate therefore asked this script to
    reproduce rows its own selection could never fetch, and every run was
    scored against a target it was built to miss.

    Three legs, all resolved OFFLINE, zero network calls:

      ledger_uei              identifier_type == 'UEI', tier A/B/X
      ledger_cage_resolved    identifier_type == 'CAGE', tier A/B/X, mapped to
                              a UEI through data/clean/fpds_uei_cage_map.csv
                              (24,977 triples, 7,465 with a CAGE, on disk since
                              2026-08-05, no network)
      ledger_parent_declared  a UEI whose DECLARED parent UEI is a ledger UEI,
                              harvested from the sources' own parent columns

    The endpoint filters on the RECIPIENT, so a CAGE and a parent's UEI both
    have to be turned into a recipient UEI before they can be sent. That is
    what this function does, and it is why the fix is a resolution step rather
    than an extra filter key.

    A leg is recorded per UEI in `_pull_universe.csv`. Per docs/PULL_DISCIPLINE
    doctrine, a puller that selects on identifiers alone must SAY SO and must
    record which leg fired, so a merge can stamp `population_basis` and a later
    reader can reproduce either population. This script cannot stamp the rows
    itself - it retrieves server-built zips - so it ships the provenance
    beside them.

    TIER IS INHERITED, NEVER ASSIGNED. A UEI reached through the parent leg
    carries the leg, not the parent's tier. Whoever merges these rows applies
    the ledger's own tier to the entity it resolves to; this file says only
    HOW the UEI entered the pull set.
    """
    import csv
    a, b, x = ledger_ueis()
    prov = {}
    for u in a | b | x:
        prov[u] = "ledger_uei"

    # ---- leg 2: CAGE -> UEI, offline ------------------------------------
    cages = ledger_cages()
    n_cage = 0
    xw = CLEAN / "fpds_uei_cage_map.csv"
    if xw.exists():
        with open(xw, encoding="utf-8-sig", errors="replace",
                  newline="") as fh:
            for r in csv.DictReader(fh):
                c = (r.get("cage_code") or "").strip().upper()
                u = (r.get("uei") or "").strip().upper()
                if c in cages and len(u) == 12 and u not in prov:
                    prov[u] = "ledger_cage_resolved"
                    n_cage += 1
    else:
        log("  WARNING: fpds_uei_cage_map.csv absent - the CAGE leg is OFF. "
            "That is a fact about this run and it goes in _state.json.")

    # ---- leg 3: declared parent -----------------------------------------
    # An absent column reads as an empty source (AGENTS.md rule 8), so each
    # source asserts its columns and RAISES rather than contributing zero.
    known = set(prov)
    n_parent = 0
    sources = [
        (CEDAR / "data" / "raw" / "contracts"
         / "usaspending_archive_2026-08-07" / "filtered",
         "FY*_ledger_rows.csv", "recipient_uei", "recipient_parent_uei"),
    ]
    for d, pat, child_col, parent_col in sources:
        if not d.exists():
            continue
        for p in sorted(d.glob(pat)):
            with open(p, encoding="utf-8-sig", errors="replace",
                      newline="") as fh:
                rd = csv.DictReader(fh)
                cols = rd.fieldnames or []
                for c in (child_col, parent_col):
                    if c not in cols:
                        raise SystemExit(
                            f"{p.name}: column {c!r} absent. An absent column "
                            f"reads as an empty source - refusing to build a "
                            f"parent leg that silently contributes nothing.")
                for r in rd:
                    ch = (r.get(child_col) or "").strip().upper()
                    pa = (r.get(parent_col) or "").strip().upper()
                    if len(ch) == 12 and pa in known and ch not in prov:
                        prov[ch] = "ledger_parent_declared"
                        n_parent += 1

    pc = CLEAN / "prime_contracts.csv"
    if pc.exists():
        with open(pc, encoding="utf-8-sig", errors="replace",
                  newline="") as fh:
            rd = csv.DictReader(fh)
            cols = rd.fieldnames or []
            if "awardee_uei" not in cols or "parent_uei" not in cols:
                raise SystemExit(
                    "prime_contracts.csv: awardee_uei/parent_uei absent - "
                    "refusing to contribute a silent zero to the parent leg.")
            for r in rd:
                ch = (r.get("awardee_uei") or "").strip().upper()
                pa = (r.get("parent_uei") or "").strip().upper()
                if len(ch) == 12 and pa in known and ch not in prov:
                    prov[ch] = "ledger_parent_declared"
                    n_parent += 1

    OUT.mkdir(parents=True, exist_ok=True)
    up = OUT / "_pull_universe.csv"
    part = up.with_suffix(".csv.part")
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["uei", "selection_leg"])
        for u in sorted(prov):
            w.writerow([u, prov[u]])
    part.replace(up)

    log(f"pull universe: {len(a)} tier-A + {len(b)} tier-B + {len(x)} tier-X "
        f"ledger UEIs, + {n_cage} resolved from {len(cages)} ledger CAGEs, "
        f"+ {n_parent} whose declared parent is a ledger UEI "
        f"= {len(prov)} UEIs to pull "
        f"(was {len(a | b | x)} before 2026-08-26)")
    return set(prov), prov, {"ledger_uei": len(a | b | x),
                             "ledger_cage_resolved": n_cage,
                             "ledger_parent_declared": n_parent,
                             "ledger_cages_available": len(cages)}


# --------------------------------------------------------------------------
# filter validation - the filter key must be proven to RESTRICT
# --------------------------------------------------------------------------
def filters_for(start, end, ueis=None, key="recipient_search_text"):
    f = {"award_type_codes": AWARD_TYPES,
         "time_period": [{"start_date": start, "end_date": end,
                          "date_type": "action_date"}]}
    if ueis:
        f[key] = sorted(ueis)
    return f


def tx_count(filters):
    r = retry(_post, f"{API}/search/spending_by_transaction_count/",
              {"filters": filters})
    return r.get("results", {}).get("contracts", 0)


def validate_filter(st):
    """Prove the recipient filter restricts BEFORE pulling at scale.

    Project memory: `recipient_uei` as a filter key has been IGNORED by this
    API. And a bogus filter value returns HTTP 200 with an empty result set,
    not an error - so an empty result is not evidence of absence, it may be
    evidence of a typo. Both failure modes are tested here.
    """
    a, _, _ = ledger_ueis()
    probe = sorted(a)[:5]
    start, end = FISCAL_YEARS[2022]
    res = {"probed": now(), "fy": 2022, "probe_ueis": probe}

    unfiltered = tx_count(filters_for(start, end))
    res["unfiltered_contract_transactions"] = unfiltered
    log(f"  FY2022 unfiltered contract transactions: {unfiltered:,}")

    chosen = None
    for key in ("recipient_search_text", "recipient_uei"):
        n = tx_count(filters_for(start, end, probe, key=key))
        res[f"{key}_count"] = n
        log(f"  {key}: {n:,}")
        if n == 0:
            log(f"  {key} returned ZERO - bogus-value signature, not a filter.")
            continue
        if n >= unfiltered:
            log(f"  {key} did NOT restrict ({n:,} >= {unfiltered:,}) - IGNORED "
                "by the API. This is the documented recipient_uei failure.")
            continue
        chosen = key
        break

    # Negative control: a syntactically valid but non-existent UEI must return
    # ~0. If it returns the full universe, the key is being dropped.
    if chosen:
        bogus = tx_count(filters_for(start, end, ["ZZZZZZZZZZZZ"], key=chosen))
        res["bogus_uei_count"] = bogus
        log(f"  negative control (bogus UEI): {bogus:,}")
        if bogus > unfiltered * 0.01:
            log("  NEGATIVE CONTROL FAILED - a nonexistent UEI matched real "
                "volume. The filter is being dropped. ABORTING.")
            chosen = None

    res["chosen_key"] = chosen
    (OUT / "_filter_validation.json").write_text(
        json.dumps(res, indent=2), encoding="utf-8")
    st["filter_validation"] = res
    st["filter_validated"] = bool(chosen)
    save_state(st)
    if not chosen:
        log("No recipient filter key restricts. STOPPING rather than pulling "
            "an unrestricted universe presented as a Native-entity pull.")
        sys.exit(4)
    return chosen


# --------------------------------------------------------------------------
# submit / collect
# --------------------------------------------------------------------------
def submit(filters, tag):
    payload = {"filters": filters, "columns": [], "file_format": "csv"}
    r = retry(_post, f"{API}/download/transactions/", payload)

    # Always diff the echoed filters against what was sent.
    # `bulk_download/awards/` once accepted recipient_type_names, returned 200,
    # and echoed the filter REMOVED - which would have delivered the entire
    # federal contract universe labelled as a Native-entity pull.
    echoed = (r.get("download_request") or {}).get("filters") or {}
    for k in filters:
        if k not in echoed:
            raise RuntimeError(
                f"{tag}: server DROPPED filter '{k}' from the echo. "
                f"sent={sorted(filters)} echoed={sorted(echoed)}. "
                "Refusing to collect - this job would be the wrong universe.")
    return r["file_name"], r.get("file_url"), echoed


def collect(file_name, dest):
    """Poll, then fetch. Never re-submits: the handle is already persisted."""
    t0 = time.time()
    while time.time() - t0 < MAX_WAIT:
        s = retry(_get, f"{API}/download/status/?file_name={file_name}")
        status = s.get("status")
        if status == "finished":
            break
        if status == "failed":
            raise RuntimeError(f"server-side job failed: {s.get('message')}")
        log(f"    {file_name[:40]} ...{status} rows={s.get('total_rows')} "
            f"after {int(time.time()-t0)}s")
        time.sleep(POLL)
    else:
        raise TimeoutError(f"{file_name} still running after {MAX_WAIT}s")

    # Deterministic URL, so a job whose status polling was lost is recoverable.
    url = f"{FILES}/{file_name}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    part = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(req, timeout=3600) as r, open(part, "wb") as fh:
        while chunk := r.read(1 << 20):
            fh.write(chunk)
    part.replace(dest)
    return dest


def batches(seq, n):
    seq = sorted(seq)
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def run_fy(st, fy, key, ueis):
    start, end = FISCAL_YEARS[fy]
    for bi, batch in enumerate(batches(ueis, UEI_BATCH)):
        tag = f"fy{fy}_b{bi:02d}"
        job = st["jobs"].get(tag, {})
        if job.get("done"):
            continue

        filters = filters_for(start, end, batch, key=key)

        if not job.get("file_name"):
            n = tx_count(filters)                       # size before submit
            if n == 0:
                st["jobs"][tag] = {"done": True, "rows": 0, "sized": 0,
                                   "note": "no transactions in window"}
                save_state(st)
                continue
            fn, _, echoed = submit(filters, tag)
            job = {"file_name": fn, "sized": n, "submitted": now(),
                   "payload_filters": filters, "echoed_filters": echoed,
                   "done": False}
            st["jobs"][tag] = job
            save_state(st)                              # BEFORE collecting
            log(f"  {tag} accepted -> {fn} (sized {n:,})")

        dest = OUT / f"{tag}.zip"
        if not dest.exists():
            collect(job["file_name"], dest)
        job.update(done=True, bytes=dest.stat().st_size,
                   sha256=sha256(dest), collected=now())
        st["jobs"][tag] = job
        save_state(st)
        log(f"  {tag} collected {dest.stat().st_size:,} bytes")


def measure(fy):
    """Row count and obligations for one FY from the collected zips."""
    import csv as _csv
    import io
    rows, oblig = 0, 0.0
    for z in sorted(OUT.glob(f"fy{fy}_b*.zip")):
        with zipfile.ZipFile(z) as zf:
            for m in zf.namelist():
                if not m.lower().endswith(".csv") or "Subawards" in m:
                    continue
                with zf.open(m) as fh:
                    rd = _csv.DictReader(io.TextIOWrapper(fh, "utf-8-sig"))
                    for r in rd:
                        rows += 1
                        try:
                            oblig += float(r.get("federal_action_obligation") or 0)
                        except ValueError:
                            pass
    return rows, oblig


def compute_targets():
    """Apply the CURRENT ledger to the spine to get the like-for-like target.

    Returns {fy: {rows, obligations}} plus a fingerprint of the ledger used.
    """
    # THE GATE AND THE PULL MUST SELECT THE SAME POPULATION.
    # Until 2026-08-26 this function's mask was `awardee_uei IN ledger OR
    # cage_code IN ledger` while the pull sent UEIs alone. The gate therefore
    # asked the pull to reproduce rows it could not fetch, and scored every run
    # against a target it was built to miss. The pull now resolves CAGE and
    # declared-parent to recipient UEIs (see pull_universe), so the mask uses
    # that same universe - plus the direct cage_code match on the spine, which
    # is strictly better here because the spine carries the CAGE itself and
    # needs no crosswalk.
    import pandas as pd
    a, b, x = ledger_ueis()
    universe, _prov, _legs = pull_universe()
    cages = set(ledger_cages())

    d = pd.read_csv(CLEAN / "prime_contracts.csv", low_memory=False)
    d["awardee_uei"] = d.awardee_uei.astype(str).str.strip().str.upper()
    d["cage_code"] = d.cage_code.astype(str).str.strip().str.upper()
    d["ob"] = pd.to_numeric(d.total_obligations, errors="coerce").fillna(0)
    m = d.awardee_uei.isin(universe) | d.cage_code.isin(cages)
    sel = d[m]
    tgt = {}
    for fy in (2021, 2022):
        s = sel[sel.fiscal_year == fy]
        tgt[fy] = {"rows": int(len(s)), "obligations": float(s.ob.sum())}
    fp = {"ledger_sha256": sha256(CLEAN / "cedar_identifier_ledger_final.csv"),
          "ledger_mtime": datetime.fromtimestamp(
              (CLEAN / "cedar_identifier_ledger_final.csv").stat().st_mtime,
              timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
          "tier_A_ueis": len(a), "tier_B_ueis": len(b), "tier_X_ueis": len(x),
          "tier_AB_cages": len(cages)}
    return tgt, fp


def gate(st):
    """Refuse FY2023+ unless FY2021 and FY2022 land near the ATTRIBUTED spine."""
    ok = True
    targets, fp = compute_targets()
    st["gate"] = {}
    st["gate_ledger_fingerprint"] = fp
    log(f"  gate targets recomputed from live ledger "
        f"(A={fp['tier_A_ueis']} B={fp['tier_B_ueis']} UEIs, "
        f"mtime {fp['ledger_mtime']})")
    for fy in (2021, 2022):
        rows, oblig = measure(fy)
        tgt = targets[fy]
        dr = (rows - tgt["rows"]) / tgt["rows"]
        do = (oblig - tgt["obligations"]) / tgt["obligations"]
        st["gate"][fy] = {"pulled_rows": rows, "pulled_obligations": oblig,
                          "target_rows": tgt["rows"],
                          "target_obligations": tgt["obligations"],
                          "row_delta_pct": round(dr * 100, 2),
                          "obligation_delta_pct": round(do * 100, 2)}
        log(f"  GATE FY{fy}: rows {rows:,} vs {tgt['rows']:,} ({dr:+.2%}) | "
            f"${oblig/1e9:.3f}B vs ${tgt['obligations']/1e9:.3f}B ({do:+.2%})")
        if abs(do) > GATE_TOLERANCE:
            ok = False
    st["gate_passed"] = ok
    save_state(st)
    if not ok:
        log("GATE FAILED. The pulled population does not match the spine's "
            "attributed population. STOPPING - do not append a mismatched "
            "population. Report the percentages and investigate.")
        sys.exit(5)
    log("GATE PASSED.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["pull", "validate", "targets", "status"])
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    st = load_state()
    save_state(st)                       # rule 6: checkpoint BEFORE request 1

    if args.cmd == "targets":
        tgt, fp = compute_targets()
        print(json.dumps({"targets": tgt, "ledger": fp}, indent=2))
        return

    if args.cmd == "status":
        print(json.dumps(st, indent=2)[:4000])
        return

    guard_host(args.force)

    if args.cmd == "validate":
        validate_filter(st)
        return

    a, b, x = ledger_ueis()
    ueis, prov, legs = pull_universe()
    log(f"ledger: {len(a)} tier-A, {len(b)} tier-B, {len(x)} tier-X UEIs "
        f"-> {len(ueis)} to pull, in {-(-len(ueis)//UEI_BATCH)} batches/FY")
    st["selection"] = {
        "doctrine": "docs/PULL_DISCIPLINE.md - TYPE_FILTER OR KNOWN_IDENTIFIER",
        "legs_used": ["ledger_uei", "ledger_cage_resolved",
                      "ledger_parent_declared"],
        "leg_NOT_used": "type_filter",
        "leg_not_used_reason":
            "no recipient_type/business-type filter on this endpoint "
            "reproduces the spine population - measured +4.56% against a "
            "+0.11% bar, two-directional (see docstring). The type leg is "
            "therefore carried by the periodic discovery sweep, not by this "
            "puller.",
        "population_basis_for_every_row_this_pull_yields": "ledger_identifier",
        "per_uei_provenance": "_pull_universe.csv",
        "counts": legs,
        "universe_size": len(ueis),
    }
    save_state(st)

    key = st.get("filter_validation", {}).get("chosen_key")
    if not key:
        key = validate_filter(st)
    log(f"filter key: {key}")

    for fy in (2021, 2022):              # validation years FIRST
        log(f"FY{fy} (validation year)")
        run_fy(st, fy, key, ueis)
    gate(st)

    for fy in (2023, 2024, 2025, 2026):
        log(f"FY{fy}")
        run_fy(st, fy, key, ueis)

    log("done")


if __name__ == "__main__":
    main()
