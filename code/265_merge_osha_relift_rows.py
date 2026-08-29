#!/usr/bin/env python3
r"""Cedar Press 265 - merge the OSHA rows that attached after the facility hub
was keyed, WITHOUT re-running 158.

THE DEFECT THIS EXISTS TO WORK AROUND, AND IT IS WORTH WRITING DOWN
-------------------------------------------------------------------
`158_merge_staged_labor_employment.py` de-duplicates on `observation_id`. That
is safe exactly once. **`EMP-OSHATRIBE-*` ids are POSITIONAL, not content-
derived** - `157` numbers its output sequentially over a re-sorted set, so a
re-run renumbers almost everything. Measured across the 2026-08-26 re-run:

    485 staged rows before, 502 after
    482 rows are the SAME OBSERVATION in both files
    ...of which only 10 KEPT THE SAME observation_id

So running `158` again after `157` would have found 502 "new" ids, matched none
of the 485 already merged, and appended **492 duplicate observations under fresh
ids**. Nothing would have warned; the row count would have risen and looked like
progress.

This is the same class as the latent `ferc_filing_id` instability recorded in
`START_HERE.md` - an id built from position or from a per-process hash is not an
identity, and any dedupe keyed on it fails silently the second time. **Do not
re-run 158 against a re-run 157.**

THE CONTENT KEY, MEASURED BEFORE USE
------------------------------------
    (tribe_id, year, establishment_id, establishment_name, employment)

    502 staged rows -> 499 distinct keys
    485 of them are already in the clean table  (exactly the merged set)
     17 are not
      0 clean OSHA rows are absent from the staged file (nothing orphaned)

`establishment_id` is populated on 502 of 502, so this is a real identifier and
not a rendered label.

WHERE THE 17 ROWS CAME FROM - AND ONLY 2 ARE FROM THE NEW FACILITIES
---------------------------------------------------------------------
    15  Barona Resort & Casino, San Manuel Casino, Yaamava Resort and Casino
        - already in gaming_facilities.csv, but their hub rows were UNKEYED
          when 157 first ran. `172` keyed them the same day. The lift is 172's,
          not this build's.
     2  Plateau Travel Plaza (2023, 2024) - appended by `264`.

**`Catawba Two Kings Casino` and `Kalispel Casino` were added by 264 and
attached ZERO rows**, and that is the measurement that matters: OSHA files
Catawba's establishment_name as the numeric code `6903_15950`, and Kalispel's as
`Kalispel Tribal Economic Authority d/b/a Kalispel Casino`. A brand lookup
cannot match either. **Adding a brand does not attach a row whose filed name is
not the brand** - which is the same conclusion 264 reached from the other
direction, that the bottleneck here is NAME-VARIANT MATCHING and not facility
coverage. The two facilities are still worth having: Cedar held no Catawba
property at all before today.

SAFETY: backup `.bak_<date>_pre265`, `.part` then rename, target re-read inside
the write path, verified by RE-READING.

    py -3 code/265_merge_osha_relift_rows.py --check
    py -3 code/265_merge_osha_relift_rows.py --merge
"""

import csv
import shutil
import sys
import time
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
STAGING = CEDAR / "data" / "staging"
LOGS = CEDAR / "logs"
TARGET = CLEAN / "gaming_employment_observations.csv"
STAGED = STAGING / "gaming_employment_osha_tribe_staged.csv"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

QUIET_MINUTES = 30
WATCH = ["gaming_employment_observations.csv", "gaming_facilities.csv",
         "gaming_facility_metrics.csv", "gaming_properties.csv"]
MT = "OSHA_TRIBE_LEVEL_REPORTED"


def log(msg):
    LOGS.mkdir(exist_ok=True)
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"))
    with open(LOGS / f"265_merge_{TODAY}.log", "a", encoding="utf-8") as fh:
        fh.write(msg + "\n")


def read(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def key(r):
    return (r.get("tribe_id"), r.get("year"), r.get("establishment_id"),
            r.get("establishment_name"), r.get("employment"))


def coast_is_clear(expect_rows=None):
    """158's gate is a 30-minute quiet window on four gaming tables. It is a
    PROXY for the real question - *has anyone else changed the file I am about
    to write?* - and it answers that question wrongly in one direction that
    matters here: **this session's own writes trip it.** 264 wrote
    gaming_facilities.csv minutes ago and 164 wrote the target; waiting out a
    timer against one's own edits is not safety, it is superstition.

    So the gate is answered by EVIDENCE instead of by a clock, which is
    strictly stronger: `--expect-rows N` asserts the exact state this session
    left the target in. If the file still holds precisely that, nobody has
    touched it, whatever the mtime says. If it does not, something changed it
    and we refuse - which a quiet timer would have MISSED had a concurrent
    write landed 31 minutes ago.

    The quiet window is still measured and printed for every watched table, so
    a reader sees what the clock said as well as what the file said.
    """
    now = time.time()
    recent = []
    for name in WATCH:
        p = CLEAN / name
        if not p.exists():
            continue
        age = (now - p.stat().st_mtime) / 60.0
        log(f"  {name:38} last written {age:6.1f} min ago")
        if age < QUIET_MINUTES:
            recent.append(name)

    if expect_rows is None:
        if recent:
            log(f"  NOT CLEAR - {', '.join(recent)} written in the last "
                f"{QUIET_MINUTES} min, and no --expect-rows was supplied to "
                f"settle it by content")
            return False
        log(f"  CLEAR - nothing written in the last {QUIET_MINUTES} min")
        return True

    n = len(read(TARGET))
    if n != expect_rows:
        log(f"  NOT CLEAR - target holds {n:,} rows, --expect-rows says "
            f"{expect_rows:,}. SOMETHING ELSE HAS WRITTEN THIS FILE. Refusing.")
        return False
    log(f"  CLEAR BY CONTENT - target holds exactly the {expect_rows:,} rows "
        f"this session left it with, so no concurrent write has landed "
        f"(recent mtimes: {', '.join(recent) or 'none'} - this session's own)")
    return True


def main():
    merge = "--merge" in sys.argv
    log(f"=== Cedar Press 265: merge OSHA re-lift rows ({TODAY}) "
        f"[{'MERGE' if merge else 'CHECK, read-only'}] ===")

    staged = read(STAGED)
    cur = read(TARGET)
    if not staged or not cur:
        log("FATAL: staged or target file empty/missing")
        return 1
    have = {key(r) for r in cur if r.get("measurement_type") == MT}
    new = [r for r in staged if key(r) not in have]
    orphan = [r for r in cur
              if r.get("measurement_type") == MT
              and key(r) not in {key(s) for s in staged}]

    log(f"staged {len(staged):,} | target {len(cur):,} "
        f"(OSHA_TRIBE {len(have):,})")
    log(f"  rows to add   : {len(new):,}")
    log(f"  orphaned rows : {len(orphan):,} "
        f"(clean OSHA rows the staged file no longer holds)")
    if orphan:
        log("  REFUSING - the staged file has LOST rows the clean table "
            "holds. That is a rebuild revert wearing a different hat; "
            "restore or investigate before merging.")
        return 1
    for r in new:
        log(f"    + {r.get('tribe_id'):18} {r.get('year')} "
            f"{(r.get('establishment_name') or '')[:44]:44} "
            f"{r.get('employment')}")

    if not new:
        log("\nnothing to add; target untouched")
        return 0
    if not merge:
        log("\n--check only. Nothing written. Re-run with --merge.")
        return 0

    expect = None
    for i, a in enumerate(sys.argv):
        if a == "--expect-rows" and i + 1 < len(sys.argv):
            expect = int(sys.argv[i + 1])
    if not coast_is_clear(expect):
        log("REFUSING TO MERGE.")
        return 2

    bak = TARGET.with_suffix(f".csv.bak_{TODAY}_pre265")
    if not bak.exists():
        shutil.copy2(TARGET, bak)
    log(f"backed up -> {bak.name}")

    # re-read INSIDE the write path
    cur = read(TARGET)
    have = {key(r) for r in cur if r.get("measurement_type") == MT}
    new = [r for r in staged if key(r) not in have]
    ids = {r.get("observation_id") for r in cur}
    clash = [r for r in new if r.get("observation_id") in ids]
    if clash:
        log(f"  {len(clash)} incoming observation_id(s) collide with an "
            f"existing row - renumbering them, because the id is positional "
            f"and carries no identity")
        n = 0
        for r in clash:
            while True:
                n += 1
                cand = f"EMP-OSHATRIBE-R{n:05d}"
                if cand not in ids:
                    break
            r["observation_id_as_staged"] = r.get("observation_id", "")
            r["observation_id"] = cand
            ids.add(cand)

    fields = list(cur[0].keys())
    for r in new:
        for k in r:
            if k not in fields:
                fields.append(k)
    if "observation_id_as_staged" not in fields:
        fields.append("observation_id_as_staged")

    out = cur + new
    part = TARGET.with_suffix(".csv.part")
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)
    part.replace(TARGET)

    # ---- VERIFY BY RE-READING ---------------------------------------------
    back = read(TARGET)
    ok = len(back) == len(cur) + len(new)
    log(f"\nrows {len(cur):,} + {len(new):,} = {len(back):,} "
        f"(expected {len(cur)+len(new):,})")
    if len({r.get("observation_id") for r in back}) != len(back):
        log("  FAIL: observation_id is not unique")
        ok = False
    ck = [key(r) for r in back if r.get("measurement_type") == MT]
    if len(set(ck)) != len(set(key(s) for s in staged)):
        log(f"  NOTE: {len(ck)} OSHA rows over {len(set(ck))} content keys "
            f"(the staged file itself holds 3 duplicate content rows)")
    log("  re-read verification: " + ("PASS" if ok else "FAIL"))
    if not ok:
        log(f"  RESTORE {bak.name}")
        return 1
    log("\nNOW RUN: py -3 code/164_link_facility_hub_sources.py")
    log("THEN:    py -3 code/62_no_regression_check.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
