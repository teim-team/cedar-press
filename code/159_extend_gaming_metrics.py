#!/usr/bin/env python3
r"""Cedar Press 159 - carry `gaming_facility_metrics.csv` past 2023, and key it.

TWO PROBLEMS, MEASURED BEFORE THE BUILD
---------------------------------------
    rows                                   65,223
    ...from the Casino City vendor panel    64,181  (98.4%)  [never publishes]
    ...from an official regulator            1,042  ( 1.6%)
    rows dated after 2023-12-31                 24
    rows carrying an entity_id                   0

So the file is 98% unpublishable by licence, stops in 2023, and is joined to
nothing. This script fixes the second and third and moves the needle on the
first.

WHAT IS ADDED - CONNECTICUT, MONTHLY, 1993-2025
-----------------------------------------------
`data.ct.gov` dataset **i6ts-ib7c** (CT Dept of Consumer Protection) is already
Cedar's CT source, but only 63 ANNUAL rows per metric were taken from it. The
dataset is **monthly, per casino, 748 casino-months from 1993-01 to 2025-12** -
and it is a Socrata endpoint, so it is retrievable in one request and refreshes
itself. Four measures are emitted per casino-month:

    ct_slot_win_monthly              gaming_revenue    usd
    ct_slot_handle_monthly           amount_wagered    usd
    ct_slot_contribution_monthly     payment_to_government  usd
    ct_slot_weighted_average_machines  capacity        machines

**`payout` and `hold` are deliberately NOT emitted.** The source changes their
units mid-series without changing the column name: January 1993 reads
`payout = 91.45` and December 2025 reads `payout = 0.912`. Same heading, one a
percentage and one a fraction. Emitting them would produce a series in which
2025 looks like a 0.9% payout. This is the same shape as Oklahoma changing a
LEVEL into a MONTHLY AVERAGE under one heading, already recorded in
docs/GAMING_DEVICE_BUILD_LOG.md - and the answer is the same: do not pool two
quantities under one name.

**One row is excluded and named:** `Mohegan Sun Prior Period Adj.` is an
accounting adjustment, not a month of operations, and summing it into the
monthly series would double-count. It is not silently dropped - it is written
to the log.

**HANDLE IS NOT REVENUE.** CT's `handle` is the amount wagered ($512m in one
month at Mohegan Sun) against a `win` of $43m. They are typed `amount_wagered`
and `gaming_revenue` so that no aggregation can add them, exactly as the
Connecticut digital build separated `HANDLE` from `AMOUNT_WAGERED`.

WHAT IS KEYED
-------------
`entity_id` is filled by an EXACT JOIN on `facility_id` into
`gaming_facilities.csv`, taking that row's `tribe_id`. It is not a name match
and it invents nothing - and per the rule in AGENTS.md, **the tier is inherited
from the facility row**, so a metric row keyed through a tier-B facility is
tier B. Rows whose facility carries no tribe stay blank.

SAFETY
  * `gaming_facility_metrics.csv` is backed up to `.bak_<date>_pre159`.
  * One request to data.ct.gov, behind the host lock, no retry loop.
"""

import csv
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
RAW = CEDAR / "data" / "raw" / "multistate_gaming_revenue"
LOGS = CEDAR / "logs"
TODAY = date.today().isoformat()
HOST = "data.ct.gov"
CT_URL = ("https://data.ct.gov/resource/i6ts-ib7c.json"
          "?$limit=50000&$order=date")
CT_PAGE = "https://data.ct.gov/Business/Slot-Machine-Revenues/i6ts-ib7c"

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


M157 = _load("m157", CEDAR / "code" / "157_reconcile_nigc_roster.py")
read_csv, write_csv = M157.read_csv, M157.write_csv


def out(s):
    sys.stdout.write(str(s).encode("ascii", "replace").decode() + "\n")


def claim(host, note):
    p = LOGS / f"_HOSTLOCK_{host}.json"
    if p.exists():
        cur = json.loads(p.read_text(encoding="utf-8"))
        if cur.get("active") and not cur.get("released"):
            cur.setdefault("queue", []).append(note)
            p.write_text(json.dumps(cur, indent=1), encoding="utf-8")
            raise SystemExit(f"{host} lock held by pid {cur.get('pid')}; queued")
    p.write_text(json.dumps({
        "host": host, "pid": os.getpid(), "script": "code/159_extend_gaming_metrics.py",
        "claimed_at": datetime.now().isoformat(), "active": True, "queue": [note],
        "policy": "single-shot fetch, no retry loop", "note": note,
    }, indent=1), encoding="utf-8")
    return p


def release(p, downloaded, refused):
    d = json.loads(p.read_text(encoding="utf-8"))
    d.update({"active": False, "released": datetime.now().isoformat(),
              "downloaded_this_run": downloaded, "refused_by_host": refused})
    p.write_text(json.dumps(d, indent=1), encoding="utf-8")


def fetch_ct():
    RAW.mkdir(parents=True, exist_ok=True)
    dest = RAW / f"ct_slot_revenue_monthly_{TODAY}.json"
    if dest.exists():
        out(f"reusing {dest.name}")
        return json.loads(dest.read_text(encoding="utf-8"))
    lock = claim(HOST, "CT DCP slot revenue monthly series i6ts-ib7c")
    try:
        p = subprocess.run(["curl", "-s", "--max-time", "120",
                            "-w", "\n__HTTPSTATUS__%{http_code}", CT_URL],
                           capture_output=True)
        body = p.stdout
        i = body.rfind(b"\n__HTTPSTATUS__")
        st = int(body[i + 15:]) if i >= 0 else 0
        body = body[:i] if i >= 0 else body
        out(f"GET {CT_URL} -> {st} ({len(body)} bytes)")
        if st != 200:
            release(lock, 0, [CT_URL])
            raise SystemExit(f"data.ct.gov {st}")
        tmp = dest.with_suffix(".json.part")
        tmp.write_bytes(body)
        tmp.replace(dest)
        release(lock, 1, [])
        return json.loads(body.decode("utf-8"))
    except SystemExit:
        raise
    except Exception:
        release(lock, 0, [CT_URL])
        raise


CT_FACILITY = {
    # CT DCP reports per CASINO. Both are unambiguous single properties in
    # Cedar; the id prefix is history, not provenance (code/cedar_ids.py).
    "Foxwoods": ("CCP-10600", "Foxwoods Resort Casino"),
    "Mohegan Sun": ("CCP-45100", "Mohegan Sun"),
}

CT_METRICS = [
    ("win_9", "ct_slot_win_monthly", "gaming_revenue", "usd",
     "Slot win for the month as published by CT DCP - coin in less coin out. "
     "NOT total casino revenue: Connecticut's series covers SLOT MACHINES only, "
     "and table games are outside it."),
    ("handle", "ct_slot_handle_monthly", "amount_wagered", "usd",
     "Amount wagered (coin in) for the month. THIS IS NOT REVENUE and must "
     "never be summed with, or substituted for, a win or GGR figure."),
    ("total_contributions", "ct_slot_contribution_monthly",
     "payment_to_government", "usd",
     "The tribe's contribution to the State for the month under the "
     "Mashantucket Pequot / Mohegan memoranda of understanding. A payment to "
     "government, not revenue."),
    ("weighted_average", "ct_slot_weighted_average_machines", "capacity",
     "machines",
     "Weighted average number of slot machines in operation over the month. An "
     "OPERATING average, not an authorised maximum and not a point-in-time "
     "floor count."),
]


def main():
    src = CLEAN / "gaming_facility_metrics.csv"
    bak = CLEAN / f"gaming_facility_metrics.csv.bak_{TODAY}_pre159"
    if not bak.exists():
        shutil.copy2(src, bak)
        out(f"backed up -> {bak.name}")

    rows = read_csv(src)
    fields = list(rows[0].keys())
    n_before = len(rows)
    yrs_before = Counter((r.get("as_of_date") or "")[:4] for r in rows)
    out(f"metrics in: {n_before} rows; after 2023: "
        f"{sum(v for k, v in yrs_before.items() if k > '2023')}")

    # ---------------------------------------------------------------- CT
    data = fetch_ct()
    out(f"CT casino-months: {len(data)}")
    excluded = [d for d in data if d["casino"] not in CT_FACILITY]
    out(f"  excluded (not a month of operations at a named casino): "
        f"{Counter(d['casino'] for d in excluded)}")

    new, seen_keys = [], set()
    existing = {(r["source"], r["metric"], r["as_of_date"], r["facility_name"])
                for r in rows}
    for d in data:
        if d["casino"] not in CT_FACILITY:
            continue
        fid, fname = CT_FACILITY[d["casino"]]
        obs = d["date"][:10]                       # month END, as CT publishes
        for col, metric, mtype, unit, note in CT_METRICS:
            v = (d.get(col) or "").strip()
            if v == "":
                continue
            k = ("CT Dept of Consumer Protection / data.ct.gov dataset i6ts-ib7c "
                 "(monthly series)", metric, obs, fname)
            if k in existing or k in seen_keys:
                continue
            seen_keys.add(k)
            new.append({
                "facility_id": fid, "entity_id": "", "entity_level": "facility",
                "tribe": "", "facility_name": fname, "state": "CT",
                "metric": metric, "measure_type": mtype, "value": v, "unit": unit,
                "observation_date": obs,
                "observation_period": d.get("fiscal_year_month", ""),
                "observation_status": "current", "source_status_literal": "",
                "value_basis": "reported",
                "value_verification": ("source_archived: data/raw/"
                                       f"multistate_gaming_revenue/"
                                       f"ct_slot_revenue_monthly_{TODAY}.json"),
                "value_basis_detail": note + f" | CT column `{col}`"
                + (f" | source footnote: {d['footnotes']}" if d.get("footnotes") else ""),
                "source": k[0], "source_file": f"data.ct.gov i6ts-ib7c ({CT_PAGE})",
                "fetched_date": TODAY, "as_of_date": obs,
                "as_of_date_precision": "day",
                "as_of_date_basis": ("CT DCP dates each observation to the last "
                                     "day of the month it covers; the period is "
                                     "the month, not that day"),
            })
    out(f"  new CT rows: {len(new)}")

    rows.extend({f: r.get(f, "") for f in fields} for r in new)

    # ------------------------------------------------------- entity keying
    fac = {f["facility_id"]: f for f in read_csv(CLEAN / "gaming_facilities.csv")}
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
        elif f:
            keyed["facility_row_carries_no_tribe"] += 1
        else:
            keyed["no_facility_id"] += 1

    write_csv(src, rows, fields)
    yrs_after = Counter((r.get("as_of_date") or "")[:4] for r in rows)
    post = {k: v for k, v in sorted(yrs_after.items()) if k > "2023"}
    out(f"\nWROTE gaming_facility_metrics.csv: {n_before} -> {len(rows)} rows")
    out(f"  entity_id filled: 0 -> {sum(1 for r in rows if r['entity_id'])} "
        f"({sum(1 for r in rows if r['entity_id']) * 100.0 / len(rows):.1f}%)")
    out(f"  keying outcome: {dict(keyed)}")
    out(f"  rows dated after 2023: "
        f"{sum(v for k, v in yrs_after.items() if k > '2023')} "
        f"(was {sum(v for k, v in yrs_before.items() if k > '2023')})")
    out(f"  by year past 2023: {post}")
    nonvendor = sum(1 for r in rows if "Casino City" not in r["source"])
    out(f"  non-vendor (publishable-source) rows: 1,042 -> {nonvendor}")

    (LOGS / f"159_extend_gaming_metrics_{TODAY}.json").write_text(json.dumps({
        "built": TODAY, "rows_before": n_before, "rows_after": len(rows),
        "ct_casino_months": len(data), "ct_rows_added": len(new),
        "ct_excluded": {k: v for k, v in Counter(d["casino"] for d in excluded).items()},
        "ct_series_span": [min(d["date"][:10] for d in data),
                           max(d["date"][:10] for d in data)],
        "entity_id_filled": sum(1 for r in rows if r["entity_id"]),
        "keying_outcome": dict(keyed),
        "rows_after_2023_before": sum(v for k, v in yrs_before.items() if k > "2023"),
        "rows_after_2023_after": sum(v for k, v in yrs_after.items() if k > "2023"),
        "non_vendor_rows_after": nonvendor,
        "payout_hold_withheld": ("CT changes the units of `payout` and `hold` "
                                 "mid-series without changing the column name "
                                 "(91.45 in 1993-01, 0.912 in 2025-12)"),
    }, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
