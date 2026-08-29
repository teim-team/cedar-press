#!/usr/bin/env python3
r"""Cedar Press 343 - carry the CT DCP monthly slot series forward, or prove it
cannot be carried forward.

WHY
---
`docs/REFRESH_CADENCE.md` lists CT gaming as **238 days behind and OURS**:
"CT publishes monthly ... currently 8 months behind; this is the cheapest win
in the file." That diagnosis was written against a Cedar file whose CT rows
stopped at 2025-12.

Two things have to be separated before that can be called a win, and this
script exists to keep them apart:

  * **our lag** - the endpoint has months we never pulled; and
  * **the source's lag** - the endpoint itself stops where our file stops.

`REFRESH_CADENCE.md` 1.1 states the rule this turns on: *"Do not diagnose a
source from a stale local file. That is the cheapest error in this whole
document to make and it points every remedy in the wrong direction."* The
mirror of that rule applies here too - you cannot diagnose OUR lag from a
cached copy of the source either. So the endpoint is asked, live and bounded.

WHAT IT DOES
  1. asks data.ct.gov i6ts-ib7c for `count(1)` - the total the SOURCE reports;
  2. pulls the whole series in one Socrata request (it is ~750 rows) and
     compares retrieved against that reported total;
  3. computes the casino-months present at the source and absent from
     `gaming_facility_metrics.csv`, and appends ONLY those, in the exact row
     shape `159_extend_gaming_metrics.py` defined (imported, never restated);
  4. if there are none, records that the residual gap is the SOURCE's and stops
     without touching the file.

WITHHELD, DELIBERATELY: `payout` and `hold`
-------------------------------------------
Already established by 159 and NOT re-derived here: CT changes the units of
those two columns mid-series without changing the column name - `91.45` in
1993-01 against `0.912` in 2025-12, one a percentage and one a fraction. A
series built from them would show 2025 at a 0.9% payout. They are not emitted,
and this script does not re-measure the finding it inherits.

`Mohegan Sun Prior Period Adj.` is likewise not a month of operations. It is
excluded and NAMED in the log, never silently dropped.

HOST DISCIPLINE
  `logs/_HOSTLOCK_data.ct.gov.json` claimed and released; two requests, spaced;
  no retry loop; `.part` then rename on every write.

Reads   data/clean/gaming_facility_metrics.csv
        data/clean/gaming_facilities.csv          (entity keying, exact join)
Writes  data/raw/multistate_gaming_revenue/ct_slot_revenue_monthly_<date>.json
        data/clean/gaming_facility_metrics.csv    (appended, only if new months)
        logs/343_ct_gaming_refresh_<date>.json
"""

import csv
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from collections import Counter
from datetime import date, datetime
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"
RAW = CEDAR / "data" / "raw" / "multistate_gaming_revenue"
LOGS = CEDAR / "logs"
TODAY = date.today().isoformat()

HOST = "data.ct.gov"
HOSTLOCK = LOGS / f"_HOSTLOCK_{HOST}.json"
SCRIPT = "code/343_refresh_ct_gaming_monthly.py"
METRICS = CLEAN / "gaming_facility_metrics.csv"
STATE = LOGS / f"343_ct_gaming_refresh_{TODAY}.json"

COUNT_URL = "https://data.ct.gov/resource/i6ts-ib7c.json?$select=count(1)"

csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))


def out(s=""):
    sys.stdout.write(str(s).encode("ascii", "replace").decode() + "\n")
    sys.stdout.flush()


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, str(CODE / filename))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


M159 = load("m159", "159_extend_gaming_metrics.py")
read_csv, write_csv = M159.read_csv, M159.write_csv


def claim_host(note):
    if HOSTLOCK.exists():
        cur = json.loads(HOSTLOCK.read_text(encoding="utf-8"))
        if cur.get("active") and not cur.get("released"):
            cur.setdefault("queue", []).append(
                {"requested_by": SCRIPT, "requested_at": TODAY, "work": note})
            HOSTLOCK.write_text(json.dumps(cur, indent=1), encoding="utf-8")
            raise SystemExit(f"{HOST} lock held by pid {cur.get('pid')}; queued")
    HOSTLOCK.write_text(json.dumps({
        "host": HOST, "pid": os.getpid(), "script": SCRIPT,
        "claimed_at": datetime.now().isoformat(), "active": True,
        "queue": [note],
        "policy": "two requests, >=2s apart, no retry loop",
        "note": note,
    }, indent=1), encoding="utf-8")


def release_host(downloaded, refused, note):
    if not HOSTLOCK.exists():
        return
    d = json.loads(HOSTLOCK.read_text(encoding="utf-8"))
    d.update({"active": False, "released": datetime.now().isoformat(),
              "released_by": SCRIPT, "downloaded_this_run": downloaded,
              "refused_by_host": refused, "note": note})
    HOSTLOCK.write_text(json.dumps(d, indent=1), encoding="utf-8")


def get(url):
    p = subprocess.run(["curl", "-s", "--max-time", "120",
                        "-w", "\n__HTTPSTATUS__%{http_code}", url],
                       capture_output=True)
    body = p.stdout
    i = body.rfind(b"\n__HTTPSTATUS__")
    st = int(body[i + 15:]) if i >= 0 else 0
    body = body[:i] if i >= 0 else body
    out(f"GET {url} -> {st} ({len(body):,} bytes)")
    return st, body


def main():
    rows = read_csv(METRICS)
    fields = list(rows[0].keys())
    n_before = len(rows)
    held_keys = {(r.get("source", ""), r.get("metric", ""),
                  r.get("as_of_date", ""), r.get("facility_name", ""))
                 for r in rows}
    ct_monthly_metrics = {m[1] for m in M159.CT_METRICS}
    ct_held = sorted({r["as_of_date"] for r in rows
                      if r.get("metric") in ct_monthly_metrics
                      and "i6ts-ib7c" in (r.get("source") or "")})
    out(f"metrics file: {n_before:,} rows; CT monthly observations held "
        f"{len(ct_held)} distinct month-ends, newest {max(ct_held)}")

    RAW.mkdir(parents=True, exist_ok=True)
    dest = RAW / f"ct_slot_revenue_monthly_probe_{TODAY}.json"
    claim_host("CT DCP slot revenue monthly series i6ts-ib7c - forward refresh")
    reported_total, data, refused = None, None, []
    try:
        st, body = get(COUNT_URL)
        if st != 200:
            refused.append(COUNT_URL)
            raise SystemExit(f"data.ct.gov count -> HTTP {st}")
        reported_total = int(json.loads(body.decode("utf-8"))[0]["count_1"])
        out(f"  source-reported row total: {reported_total:,}")
        time.sleep(2.0)
        st, body = get(M159.CT_URL)
        if st != 200:
            refused.append(M159.CT_URL)
            raise SystemExit(f"data.ct.gov series -> HTTP {st}")
        part = dest.with_suffix(".json.part")
        part.write_bytes(body)
        part.replace(dest)
        data = json.loads(body.decode("utf-8"))
    finally:
        release_host(0 if data is None else 1, refused,
                     "i6ts-ib7c forward refresh")

    out(f"  retrieved {len(data):,} rows against {reported_total:,} reported")
    if len(data) != reported_total:
        STATE.write_text(json.dumps({
            "built": TODAY, "script": SCRIPT, "run_status": "INCOMPLETE",
            "source_reported_total": reported_total,
            "records_retrieved": len(data),
            "merge_refused_because": (
                "the Socrata response is short of the count the source itself "
                "reports. A truncated series merged forward would look like a "
                "complete refresh and would silently define the newest month.")
        }, indent=2), encoding="utf-8")
        raise SystemExit("INCOMPLETE: retrieved != reported; nothing merged")

    excluded = Counter(d["casino"] for d in data
                       if d["casino"] not in M159.CT_FACILITY)
    out(f"  excluded (not a month of operations at a named casino): "
        f"{dict(excluded)}")
    source_span = [min(d["date"][:10] for d in data),
                   max(d["date"][:10] for d in data)]
    out(f"  source span: {source_span[0]} .. {source_span[1]}")

    new, minted = [], set()
    for d in data:
        if d["casino"] not in M159.CT_FACILITY:
            continue
        fid, fname = M159.CT_FACILITY[d["casino"]]
        obs = d["date"][:10]
        for col, metric, mtype, unit, note in M159.CT_METRICS:
            v = (d.get(col) or "").strip()
            if v == "":
                continue
            k = ("CT Dept of Consumer Protection / data.ct.gov dataset "
                 "i6ts-ib7c (monthly series)", metric, obs, fname)
            if k in held_keys or k in minted:
                continue
            minted.add(k)
            new.append({
                "facility_id": fid, "entity_id": "", "entity_level": "facility",
                "tribe": "", "facility_name": fname, "state": "CT",
                "metric": metric, "measure_type": mtype, "value": v,
                "unit": unit, "observation_date": obs,
                "observation_period": d.get("fiscal_year_month", ""),
                "observation_status": "current", "source_status_literal": "",
                "value_basis": "reported",
                "value_verification": ("source_archived: data/raw/"
                                       "multistate_gaming_revenue/"
                                       f"{dest.name}"),
                "value_basis_detail": note + f" | CT column `{col}`"
                + (f" | source footnote: {d['footnotes']}"
                   if d.get("footnotes") else ""),
                "source": k[0],
                "source_file": f"data.ct.gov i6ts-ib7c ({M159.CT_PAGE})",
                "fetched_date": TODAY, "as_of_date": obs,
                "as_of_date_precision": "day",
                "as_of_date_basis": ("CT DCP dates each observation to the last "
                                     "day of the month it covers; the period is "
                                     "the month, not that day"),
            })

    report = {
        "built": TODAY, "script": SCRIPT, "run_status": "COMPLETE",
        "endpoint": M159.CT_URL,
        "source_reported_total": reported_total,
        "records_retrieved": len(data),
        "source_span": source_span,
        "cedar_ct_monthly_span_before": [min(ct_held), max(ct_held)],
        "excluded_not_a_month_of_operations": dict(excluded),
        "payout_hold_withheld": (
            "inherited from 159, not re-derived: CT changes the units of "
            "`payout` and `hold` mid-series without changing the column name "
            "(91.45 in 1993-01, 0.912 in 2025-12)"),
        "rows_before": n_before,
        "new_rows": len(new),
    }

    if not new:
        report["finding"] = (
            "The endpoint holds NO casino-month later than "
            f"{source_span[1]}, which is exactly where Cedar's CT monthly "
            "series already stops. The 238-day gap in REFRESH_CADENCE.md is "
            "therefore the SOURCE's, not ours: it survives because CT DCP has "
            "published no month after that date, not because we have not "
            "pulled. Whose lag it is changes the remedy - there is nothing to "
            "fetch and the collection is current with its source.")
        STATE.write_text(json.dumps(report, indent=2), encoding="utf-8")
        out("\nno casino-month at the source that Cedar does not hold.")
        out("  the residual gap is the SOURCE's. metrics file untouched.")
        return 0

    mtime_before = METRICS.stat().st_mtime_ns
    bak = METRICS.with_suffix(
        METRICS.suffix + f".bak_{TODAY}_pre_343_refresh_ct_gaming_monthly")
    if not bak.exists():
        shutil.copy2(METRICS, bak)
    rows.extend({f: r.get(f, "") for f in fields} for r in new)

    fac = {f["facility_id"]: f
           for f in read_csv(CLEAN / "gaming_facilities.csv")}
    keyed = Counter()
    for r in rows:
        if r.get("entity_id"):
            continue
        f = fac.get(r.get("facility_id", ""))
        if f and f.get("tribe_id"):
            r["entity_id"] = f["tribe_id"]
            if not r.get("tribe"):
                r["tribe"] = f.get("tribe_canonical_name", "")
            keyed[f.get("entity_tier", "?")] += 1

    part = METRICS.with_suffix(METRICS.suffix + ".part")
    write_csv(part, rows, fields)
    if METRICS.stat().st_mtime_ns != mtime_before:
        part.unlink(missing_ok=True)
        raise SystemExit("ABORT: gaming_facility_metrics.csv changed under us")
    part.replace(METRICS)

    report.update({"rows_after": len(rows), "keying_outcome": dict(keyed),
                   "new_month_ends": sorted({r["as_of_date"] for r in new})})
    STATE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    out(f"\nWROTE gaming_facility_metrics.csv: {n_before:,} -> {len(rows):,}")
    out(f"  new month-ends: {report['new_month_ends']}")

    check = read_csv(METRICS)
    out(f"  re-read: {len(check):,} rows")
    if len(check) != len(rows):
        raise SystemExit("ABORT: re-read does not match what was written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
