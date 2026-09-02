#!/usr/bin/env python3
"""
Cedar Press - 158: MERGE the staged labor-employment layers into
`data/clean/gaming_employment_observations.csv`.

WRITTEN 2026-08-26 AND DELIBERATELY NOT RUN. Read `WHY THIS EXISTS` before
running it, then run it.

WHY THIS EXISTS
---------------
This project's repeated failure mode is that work gets built and then never
plumbed. `code/101_build_lodes_block_employment.py` was written and never run.
Script 46 the same. An OCR merge step was promised in a docstring and never
written. Staging two files and leaving a question in a chat message is the same
shape - so the merge is written NOW, while the reasoning is fresh, rather than
left as an intention.

It is not run because a concurrent agent was actively rebuilding the gaming
collection at the time of writing (verified 2026-08-26 17:16: gaming_facility_
metrics.csv 17:12, gaming_properties.csv 17:15, 07n_gaming_employment.csv 17:16,
gaming_facilities.csv grown 774 -> 784, and 121_pull_subawards_api.py live). A
concurrent write to a shared gaming table is exactly the clobbering AGENTS.md
records this project losing work to.

    py -3 code/158_merge_staged_labor_employment.py --check     # safe, read-only
    py -3 code/158_merge_staged_labor_employment.py --merge

`--check` refuses nothing and writes nothing; it reports whether the coast is
clear. `--merge` refuses to run if it is not.

WHAT IT MERGES
--------------
    data/staging/gaming_employment_form5500_staged.csv    2,046 rows (script 156)
    data/staging/gaming_employment_osha_tribe_staged.csv    485 rows (script 157)

into `data/clean/gaming_employment_observations.csv` (769 rows today).

THE FIVE THINGS THIS MERGE MUST GET RIGHT
------------------------------------------
1. BACK UP FIRST. 769 is asserted in docs/GAMING_EMPLOYMENT_LOG.md and in the
   dataset tables. AGENTS.md: back up an output before re-running a build whose
   counts are asserted elsewhere.

2. RE-READ THE TARGET IMMEDIATELY BEFORE WRITING. Another agent may have
   appended between the check and the write. The target is read inside the write
   path, never cached from earlier in the run.

3. NEVER SUM THE TRIBE-LEVEL OSHA ROWS WITH THE FACILITY-LEVEL ONES. 317 of the
   485 staged OSHA rows are the SAME 300A filing the existing 364-row layer
   already carries at facility grain, flagged `already_facility_attached = 1`.
   They are kept (a tribe-level view is a different question from a facility-
   level one) but they carry the flag, and any consumer that adds
   `measurement_type IN (OSHA_ESTABLISHMENT_REPORTED, OSHA_TRIBE_LEVEL_REPORTED)`
   double-counts 317 filings unless it filters on it.

4. `entity_level` IS A NEW COLUMN ON THIS TABLE. Existing 769 rows get
   `entity_level = "facility"` where facility_id is populated and `"tribe"`
   where it is not - which is the same convention gaming_facility_metrics.csv
   already uses on its 1,039 blank-facility rows.

5. `fte_2080` IS DERIVED, NOT FILED. It travels as its own column and must never
   enter `employment`. `employment` on an OSHA row is the filed
   `annual_average_employees` headcount.

AFTER RUNNING
-------------
    py -3 code/62_no_regression_check.py
Restore from the backup on any FELL line. Note that as of 2026-08-26 the gate
already fails on `codebook_undocumented_public = 65`, which belongs to
07o_nigc_declinations (45) and 04d_fr_ex_parte_* (20) - another agent's
datasets, not this one. Do not read that as caused by this merge; compare the
metric before and after.
"""

import csv
import shutil
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
STAGING = CEDAR / "data" / "staging"
LOGS = CEDAR / "logs"
TARGET = CLEAN / "gaming_employment_observations.csv"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

STAGED = [
    ("form5500", STAGING / "gaming_employment_form5500_staged.csv"),
    ("osha_tribe", STAGING / "gaming_employment_osha_tribe_staged.csv"),
]

# A gaming table written more recently than this means somebody else is working.
QUIET_MINUTES = 30
WATCH = ["gaming_employment_observations.csv", "gaming_facilities.csv",
         "gaming_facility_metrics.csv", "gaming_properties.csv"]


def log(msg):
    LOGS.mkdir(exist_ok=True)
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"))
    with open(LOGS / f"158_merge_{TODAY}.log", "a", encoding="utf-8") as fh:
        fh.write(msg + "\n")


def read_csv(p):
    if not Path(p).exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def coast_is_clear():
    """Read-only. True when no watched gaming table moved recently."""
    now, busy = time.time(), []
    for name in WATCH:
        p = CLEAN / name
        if not p.exists():
            continue
        age_min = (now - p.stat().st_mtime) / 60.0
        log(f"  {name:38} last written {age_min:6.1f} min ago")
        if age_min < QUIET_MINUTES:
            busy.append(name)
    if busy:
        log(f"  NOT CLEAR - {len(busy)} table(s) written in the last "
            f"{QUIET_MINUTES} min: {', '.join(busy)}")
        return False
    log(f"  CLEAR - nothing written in the last {QUIET_MINUTES} min")
    return True


def merge():
    if not coast_is_clear():
        log("REFUSING TO MERGE. Re-run --check later.")
        return 2

    # (2) re-read the target INSIDE the write path, never cached
    existing = read_csv(TARGET)
    if not existing:
        log(f"FATAL: {TARGET} is empty or missing")
        return 1
    log(f"target holds {len(existing):,} rows")

    # (1) back up first
    bak = TARGET.with_suffix(f".csv.bak_{TODAY}_pre158")
    shutil.copy2(TARGET, bak)
    log(f"backed up -> {bak.name}")

    ids = {r.get("observation_id") for r in existing}

    # (4) entity_level on the incumbent rows
    for r in existing:
        r.setdefault("entity_level",
                     "facility" if r.get("facility_id") else "tribe")

    added, skipped = [], 0
    for label, path in STAGED:
        rows = read_csv(path)
        if not rows:
            log(f"  {label}: nothing staged at {path.name} - skipping")
            continue
        n_new = 0
        for r in rows:
            if r.get("observation_id") in ids:
                skipped += 1
                continue
            ids.add(r.get("observation_id"))
            added.append(r)
            n_new += 1
        log(f"  {label}: {n_new:,} new rows from {path.name}")

    if not added:
        log("nothing to add; target untouched")
        return 0

    fields = list(existing[0].keys())
    for r in existing + added:
        for k in r:
            if k not in fields:
                fields.append(k)

    out = existing + added
    part = TARGET.with_suffix(".csv.part")
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)
    part.replace(TARGET)

    log("")
    log(f"MERGED: {len(existing):,} + {len(added):,} = {len(out):,} rows "
        f"({skipped:,} already present, skipped)")
    log(f"  columns {len(existing[0].keys())} -> {len(fields)}")
    by = Counter(r.get("measurement_type", "") for r in out)
    for k, v in by.most_common():
        log(f"    {k:34} {v:6,}")
    dup = sum(1 for r in out if r.get("already_facility_attached") == "1")
    log("")
    log(f"  {dup:,} rows carry already_facility_attached=1. A consumer that "
        f"sums OSHA_ESTABLISHMENT_REPORTED and OSHA_TRIBE_LEVEL_REPORTED "
        f"together WITHOUT filtering on that flag double-counts {dup:,} "
        f"filings.")
    log("")
    log(f"NOW RUN: py -3 code/62_no_regression_check.py  "
        f"(restore {bak.name} on any FELL line)")
    return 0


def main():
    log(f"=== Cedar Press 158: merge staged labor employment ({TODAY}) ===")
    if "--merge" in sys.argv:
        return merge()
    log("--check (read-only). Nothing will be written.")
    clear = coast_is_clear()
    for label, path in STAGED:
        rows = read_csv(path)
        log(f"  staged {label:12} {len(rows):6,} rows  {path.name}")
    log(f"  target        {len(read_csv(TARGET)):6,} rows  {TARGET.name}")
    log("")
    log("run with --merge when clear" if clear
        else "DO NOT MERGE YET - another agent is writing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
