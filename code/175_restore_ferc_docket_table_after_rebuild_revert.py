#!/usr/bin/env python3
"""
Cedar Press - 175: restore the 124 FERC dockets that a partial revert dropped
out of `data/clean/ferc_tribal_dockets.csv`, without losing the entity links
that were written on top of the truncated file.

    py -3 code/175_restore_ferc_docket_table_after_rebuild_revert.py --check
    py -3 code/175_restore_ferc_docket_table_after_rebuild_revert.py

HOW IT WAS FOUND
----------------
`code/62_no_regression_check.py` grew a retrieved-vs-reported check on
2026-08-26 (standing rule 13) and failed on its first run:

    P-2232   2,308 of 4,838 (47.7%)
    P-2146   2,404 of 4,847 (49.6%)
    P-1971   3,004 of 4,241 (70.8%)
    P-2082   3,200 of 3,555 (90.0%)

Those are the four dockets `START_HERE.md` records as having been TOPPED UP on
2026-08-26 after `PER_DOCKET_BUDGET_S = 240` truncated them. The raw sheets
agree they were: all 307 sheets under
`data/raw/advocacy/ferc/docket_sheets/` are complete, 0 short. The clean table
was not.

WHAT ACTUALLY HAPPENED, FROM THE FILE TIMES AND THE BACKUPS
-----------------------------------------------------------
    17:31  ferc_tribal_dockets.csv.bak_2026-08-26_pre163            183 x 20
    17:37  ferc_tribal_dockets.csv.bak_2026-08-26_post133rebuild    307 x 20
    17:50  ferc_tribal_dockets.csv.bak_..._pre168_link_...          183 x 20
    17:50  ferc_tribal_dockets.csv                        (live)    183 x 30

The `133 build` rebuild produced the correct 307-docket table at 17:37 with the
topped-up counts on it. By 17:50 the live file was the 183-row PRE-rebuild
vintage again - fetched_date 2026-08-12, truncated counts intact - and
`168_link_adjudication_hubs.py` then enriched THAT, adding its ten entity-link
columns to the stale table.

`ferc_docket_filings.csv` did NOT revert: it is 102,615 rows x 38 columns, the
full rebuild plus the links. So the two files disagree with each other -
102,615 filings drawn from 307 dockets, described by a docket table that lists
183. Nothing printed a number that would have shown it, which is the same
sentence this project has now written four times.

START_HERE.md's line **"`ferc_tribal_dockets.csv` 183 -> 307"** is FALSE
against the file as it stands. That is corrected there rather than left.

THE REPAIR, AND WHY IT IS ADDITIVE RATHER THAN A RE-RUN
-------------------------------------------------------
Measured, not assumed: the 307-row post-rebuild snapshot contains EVERY key in
the live file (307 keys, 183 live keys, 0 live-only). So:

    base   = the 307-row post133rebuild snapshot   (complete, correct counts)
    + the 10 entity-link columns from the live file, keyed on
      (docket_number, subdocket), for the 183 rows that have them

Nothing is dropped and nothing is recomputed. `168` is NOT re-run here: it is
another agent's script and it was writing this directory sixty seconds before
this ran. The 124 recovered dockets therefore carry BLANK entity-link columns,
which is the honest state - blank means "not yet linked", not "no link
exists". Re-running `168_link_adjudication_hubs.py` (zero network calls,
honours a pre-existing link, never re-litigates one) will fill them and is the
correct next step for whoever owns that file.

SAFETY
------
mtime is captured before the read and re-checked before the write, so a
concurrent writer aborts this rather than being clobbered. Backup first,
`.part` then rename.
"""

import csv
import os
import shutil
import sys
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
LIVE = CLEAN / "ferc_tribal_dockets.csv"
BASE = CLEAN / "ferc_tribal_dockets.csv.bak_2026-08-26_post133rebuild"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

KEY = ("docket_number", "subdocket")


def load(p):
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        return list(rd), list(rd.fieldnames or [])


def key_of(r):
    return tuple((r.get(k) or "").strip() for k in KEY)


def main():
    check = "--check" in sys.argv
    print("=" * 74)
    print("175 - restoring ferc_tribal_dockets.csv after a partial revert")
    print("=" * 74)

    for p in (LIVE, BASE):
        if not p.exists():
            print(f"  ABSENT: {p.name} - nothing done.")
            return 1

    mtime_before = LIVE.stat().st_mtime
    live, live_cols = load(LIVE)
    base, base_cols = load(BASE)
    extra = [c for c in live_cols if c not in base_cols]

    print(f"\n  live  {LIVE.name:52s} {len(live):>5,} rows x "
          f"{len(live_cols)} cols")
    print(f"  base  {BASE.name:52s} {len(base):>5,} rows x "
          f"{len(base_cols)} cols")
    print(f"  columns only on the live file (the 168 enrichment): "
          f"{len(extra)}")
    for c in extra:
        print(f"     {c}")

    by_key = {}
    for r in live:
        by_key[key_of(r)] = r
    base_keys = {key_of(r) for r in base}
    live_only = [k for k in by_key if k not in base_keys]
    if live_only:
        # A key the base does not have would be LOST by this merge. Refuse
        # rather than lose it - that is the entire defect being repaired.
        print(f"\n  REFUSED: {len(live_only)} key(s) exist on the live file "
              f"and NOT in the base snapshot:")
        for k in live_only[:10]:
            print(f"     {k}")
        print("  Merging would drop them. Nothing written.")
        return 1

    out_cols = base_cols + extra
    merged, enriched = [], 0
    for r in base:
        row = dict(r)
        src = by_key.get(key_of(r))
        for c in extra:
            row[c] = (src or {}).get(c, "")
        if src:
            enriched += 1
        merged.append(row)

    recovered = len(merged) - len(live)
    short_before = short_after = 0
    for rows, which in ((live, "before"), (merged, "after")):
        n = 0
        for r in rows:
            try:
                got = int(float(r.get("documents_retrieved") or 0))
                rep = int(float(r.get("total_hits_reported_by_source") or 0))
            except ValueError:
                continue
            if rep and got < rep:
                n += 1
        if which == "before":
            short_before = n
        else:
            short_after = n

    print(f"\n  merged            {len(merged):>5,} rows x {len(out_cols)} cols")
    print(f"  dockets recovered {recovered:>5,}")
    print(f"  rows carrying the 168 enrichment  {enriched:,} of {len(merged):,}"
          f"  ({len(merged) - enriched} recovered dockets are unlinked - blank "
          f"means NOT YET LINKED)")
    print(f"  units short of their source's reported total: "
          f"{short_before} -> {short_after}")

    if check:
        print("\n  --check: nothing written.")
        return 0

    if LIVE.stat().st_mtime != mtime_before:
        print("\n  ABORTED: ferc_tribal_dockets.csv changed while this ran. "
              "A concurrent\n  writer owns it. Nothing written.")
        return 1

    bak = LIVE.with_name(LIVE.name + f".bak_{TODAY}_pre175")
    if not bak.exists():
        shutil.copy2(LIVE, bak)
        print(f"\n  backed up -> {bak.name}")

    tmp = LIVE.with_suffix(LIVE.suffix + ".part")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=out_cols, extrasaction="ignore")
        w.writeheader()
        for r in merged:
            w.writerow(r)
    os.replace(tmp, LIVE)
    print(f"  wrote {LIVE.name} (.part then rename)")
    print("\n  NEXT: re-run code/168_link_adjudication_hubs.py to link the "
          f"{len(merged) - enriched} recovered dockets.\n  It makes no network "
          "calls and honours every link already on the file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
