#!/usr/bin/env python3
"""
Cedar Press - 123: census the ESM.zip raw contract files.

WHY
---
`data/clean/prime_contracts.csv` FY2000-2022 came from
`ESM/clean/master prime file.dta`, which was itself derived from the raw
CSVs inside ESM.zip. The raw is UPSTREAM of the file we ship.

The open question this answers: do FY2000-2007 rows exist in the raw and get
dropped during cleaning? If so, the FY2000-2007 prime gap - which the
USAspending static archive CANNOT close, because it begins at FY2008 - may be
closeable locally, with no network access at all.

Reads directly from inside the zip. Nothing is extracted; disk is at ~3 GB.
"""

import collections
import csv
import io
import sys
import zipfile
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
ESM = CEDAR / "data" / "raw" / "esm_hci" / "ESM"   # extracted; ESM.zip deleted 2026-08-12 as a verified duplicate

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

FILES = [
    "ESM/raw/Data Request 4-5-2023 File 1.csv",
    "ESM/raw/Data Request 4-5-2023 File 2.csv",
    "ESM/raw/Data Request 5-8-2023 IDVs.csv",
]

UEI_COLS = ("recipient_uei", "awardee_or_recipient_uei",
            "recipient_duns", "awardee_or_recipient_uniqu")


def main():
    grand = collections.Counter()
    uei, piid = set(), set()

    for name in FILES:
        fp = CEDAR / "data" / "raw" / "esm_hci" / name
        if not fp.exists():
            print(f"MISSING {name}", flush=True)
            continue
        yrs = collections.Counter()
        rows = 0
        with open(fp, encoding="utf-8", errors="replace", newline="") as t:
            r = csv.DictReader(t)
            for row in r:
                rows += 1
                y = (row.get("action_date_fiscal_year") or "").strip()[:4]
                if not y.isdigit():
                    y = (row.get("action_date") or "").strip()[:4]
                if y.isdigit() and 1990 < int(y) < 2030:
                    yrs[int(y)] += 1
                    grand[int(y)] += 1
                for c in UEI_COLS:
                    v = (row.get(c) or "").strip()
                    if v:
                        uei.add(v)
                        break
                p = (row.get("award_id_piid") or "").strip()
                if p:
                    piid.add(p)
                if rows % 500000 == 0:
                    print(f"    ...{rows:,}", flush=True)
        print(f"\n=== {name}  rows={rows:,} ===", flush=True)
        for y in sorted(yrs):
            print(f"   {y}  {yrs[y]:>9,}", flush=True)

    print("\n=== GRAND TOTAL by FY ===", flush=True)
    for y in sorted(grand):
        print(f"   {y}  {grand[y]:>9,}", flush=True)
    print(f"\ntotal rows {sum(grand.values()):,}  "
          f"distinct recipient id {len(uei):,}  distinct PIID {len(piid):,}",
          flush=True)

    # the comparison that matters: raw vs what we actually ship
    pc = CEDAR / "data" / "clean" / "prime_contracts.csv"
    if pc.exists():
        have = collections.Counter()
        with open(pc, encoding="utf-8-sig", errors="replace", newline="") as fh:
            for row in csv.DictReader(fh):
                y = (row.get("fiscal_year") or "").strip()[:4]
                if y.isdigit():
                    have[int(y)] += 1
        print("\n=== RAW (ESM) vs SHIPPED (prime_contracts.csv) ===", flush=True)
        print(f"{'FY':6}{'raw':>12}{'shipped':>12}   note")
        for y in range(2000, 2024):
            r_, s_ = grand.get(y, 0), have.get(y, 0)
            note = ""
            if r_ and not s_:
                note = "<-- IN RAW, NOT SHIPPED"
            elif r_ > s_ * 1.2 and s_:
                note = "<-- raw materially larger"
            print(f"{y:<6}{r_:>12,}{s_:>12,}   {note}")


if __name__ == "__main__":
    main()
