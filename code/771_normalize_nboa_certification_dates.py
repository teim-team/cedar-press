#!/usr/bin/env python3
"""
Cedar Press - 771: put `native_owned_businesses` certification dates on ISO.

    py -3 code/771_normalize_nboa_certification_dates.py            # write
    py -3 code/771_normalize_nboa_certification_dates.py verify     # exit 1
                                                                    # if not ISO

THE DEFECT
----------
`certification_expiration` shipped in SIX date formats. Measured on the live
table before this ran - 623 populated values:

    ####-##-##   346      ##/##/####   144      #/##/####    86
    #/#/####      33      ##/#/####     13      #/##/##       1

Nothing sorted, nothing parsed, and `04/29/2027` sat two rows from
`4/16/2027`. **The ISO plurality was not the customer's half.** All 346 ISO
values are `publishable = N` - Navajo's NBOA list, which is
`TERMS_STATED_RESTRICTIVE` and never ships. Every one of the 277 dates that
actually reaches a buyer was in an un-normalised US format.

WHY THIS SCRIPT EXISTS AS WELL AS THE FIX IN 330
------------------------------------------------
`330_build_native_owned_businesses.py` now calls `iso_date()` at its single
promote-phase write point, so a rebuild produces ISO. That is the fix that
survives. But 330 is a 2,600-line harvester across eighteen authorities and
re-running it to correct a date format would re-derive far more than the two
columns at issue, against sources that have moved since. This applies the same
function to the live file, on those two columns only - the narrow in-place
write that `251_apply_np_ein_exclusions_to_np_orgs.py` establishes as the
smaller risk.

The two must not drift, so the function is IMPORTED from 330 rather than
restated here.

WHAT IS AND IS NOT CHANGED
--------------------------
Changed: `certification_start` and `certification_expiration`, and only where
the value parses as a date. Nothing else on the row, no row added, no row
deleted, and a value the parser cannot read is left EXACTLY as the source
printed it - an unparseable date is a fact about the source and a guess at it
would be the worse error. A timestamped backup is taken first.
"""
from __future__ import annotations

import csv
import importlib.util
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)

SRC = ROOT / "data" / "clean" / "native_owned_businesses.csv"
COLS = ("certification_start", "certification_expiration")

_spec = importlib.util.spec_from_file_location(
    "b330", ROOT / "code" / "330_build_native_owned_businesses.py")
_m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_m)
iso_date = _m.iso_date

ISO = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")


def shape(s: str) -> str:
    return re.sub(r"\d", "#", s)


def main() -> int:
    verify = len(sys.argv) > 1 and sys.argv[1] == "verify"
    if not SRC.exists():
        sys.exit(f"missing {SRC}")

    with SRC.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        cols = list(rd.fieldnames or [])
        rows = list(rd)

    missing = [c for c in COLS if c not in cols]
    if missing:
        sys.exit(f"table does not carry {missing}")

    changed = 0
    refused: list[tuple[str, str, str]] = []
    before: dict[str, dict[str, int]] = {c: {} for c in COLS}
    for r in rows:
        for c in COLS:
            v = (r.get(c) or "").strip()
            if not v:
                continue
            before[c][shape(v)] = before[c].get(shape(v), 0) + 1
            new = str(iso_date(v))
            if new != v:
                if not verify:
                    r[c] = new
                changed += 1
            elif not ISO.match(v):
                refused.append((r.get("business_source_id", ""), c, v))

    if not verify:
        stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        bak = SRC.with_name(f"{SRC.stem}.bak_{stamp}{SRC.suffix}")
        shutil.copy2(SRC, bak)
        with SRC.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        print(f"  771 backup -> {bak.name}")

    print(f"  771 certification dates   {changed} value(s) normalised to ISO   "
          f"{len(refused)} left verbatim as unparseable")
    for c in COLS:
        pop = sum(before[c].values())
        print(f"    {c:<26} {pop:>4} populated, {len(before[c])} format(s) "
              f"before: "
              + ", ".join(f"{k}x{v}" for k, v in
                          sorted(before[c].items(), key=lambda x: -x[1])))
    for bid, c, v in refused[:20]:
        print(f"    UNPARSEABLE  {bid}  {c} = {v!r}  (left as printed)")

    # After the write every populated value must be ISO or on the refused list.
    if verify:
        bad = 0
        for r in rows:
            for c in COLS:
                v = (r.get(c) or "").strip()
                if v and not ISO.match(v):
                    bad += 1
        print(f"  771 verify: {bad} populated value(s) not ISO")
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
