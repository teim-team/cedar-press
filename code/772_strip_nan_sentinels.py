#!/usr/bin/env python3
"""
Cedar Press - 772: the string `nan` is not a value. Strip it from clean tables.

    py -3 code/772_strip_nan_sentinels.py                # write
    py -3 code/772_strip_nan_sentinels.py verify         # exit 1 if any remain
    py -3 code/772_strip_nan_sentinels.py <table.csv>    # one table

HOW THIS WAS FOUND, WHICH IS THE POINT
--------------------------------------
Codex reviewed the shipped contracting sample and said the `contract_number`
column is not a key: four of ten rows read `0098`, `0006`, `0003`, `SBA0001`.
It was right - those are FPDS modification PIIDs, and 290,525 rows (23.9%)
carry six characters or fewer. The fix was to ship `parent_contract_number`
beside it, on the documented ground that it is "populated on all 1,217,768
rows".

**It is not.** Three of the ten rows then came back reading `nan`, and the
measurement behind the claim had counted a non-empty cell rather than a value.
`parent_contract_number` carries the literal three-character string `nan` on
**262,773 rows (21.6%)**, and once counted properly the same leak is in eleven
more columns of the same table:

    cage_code               398,840   32.75%
    parent_contract_number  262,773   21.58%
    place_of_perform_city    88,269    7.25%
    place_of_perform_state   87,068    7.15%
    award_type               71,134    5.84%
    funding_agency           33,263    2.73%
    extent_competed           9,411    0.77%
    naics_code                2,773    0.23%
    recipient_state_code        202    0.02%
    parent_uei / recipient_city_name / parent_name   52 between them
                                     --------
                                      953,785 cells

That is a pandas `float('nan')` written through `str()` on the way to CSV. It
is worse than a blank, because a blank reads as absent and `nan` reads as
present - a `COUNT(parent_contract_number)` returns 1,217,768 and every one of
those 262,773 is a lie by three characters.

AND THE TWO COLUMNS TOGETHER ARE THE KEY
----------------------------------------
Worth recording because it answers Codex's finding properly rather than just
patching the display. Cross-tabbing the two contract identifiers:

    parent real, child full PIID   664,470   54.56%
    parent real, child a mod       290,525   23.86%
    parent absent, child full PIID 262,773   21.58%
    parent absent, child a mod           0    0.00%   <- EMPTY, and that is the finding

**No row is missing both.** A row with no parent is a standalone award whose
own PIID is complete; a row with a stub child is a modification under an IDV
that is named. So neither column alone is a key and the PAIR always is, which
is what the sample and the codebook now say.

WHAT IS REPLACED, AND WHAT IS DELIBERATELY NOT
----------------------------------------------
Only a cell whose ENTIRE content is the exact lowercase string `nan` becomes
empty. Not `NaN`, not `None`, not `NA`, and never a substring - `Nanticoke`,
`Nanakuli` and `NANA` are real values in this project and a substring rule
would eat all three. `None reported` is a real `setaside` value and is
untouched. No column is dropped, no row is added or deleted, and the original
is kept as a timestamped `.bak_` beside the file.
"""
from __future__ import annotations

import csv
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
CLEAN = ROOT / "data" / "clean"

#: Exact, whole-cell, case-sensitive. See the docstring for why this is not a
#: set of every sentinel spelling.
SENTINEL = "nan"

DEFAULT_TABLES = ["prime_contracts.csv"]


def sweep(path: Path, verify: bool) -> tuple[int, dict]:
    per: dict[str, int] = {}
    tmp = path.with_suffix(path.suffix + ".772tmp")
    n = 0
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        cols = list(rd.fieldnames or [])
        out = None
        w = None
        if not verify:
            out = tmp.open("w", encoding="utf-8", newline="")
            w = csv.DictWriter(out, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
        for r in rd:
            for k in cols:
                if r.get(k) == SENTINEL:
                    per[k] = per.get(k, 0) + 1
                    n += 1
                    if not verify:
                        r[k] = ""
            if w is not None:
                w.writerow(r)
        if out is not None:
            out.close()

    if not verify:
        stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        bak = path.with_name(f"{path.stem}.bak_{stamp}{path.suffix}")
        os.replace(path, bak)
        os.replace(tmp, path)
        print(f"    backup -> {bak.name}")
    return n, per


def main() -> int:
    args = sys.argv[1:]
    verify = bool(args) and args[0] == "verify"
    named = [a for a in args if a.endswith(".csv")]
    tables = named or DEFAULT_TABLES

    total = 0
    for t in tables:
        p = CLEAN / t if not Path(t).is_absolute() else Path(t)
        if not p.exists():
            print(f"    MISSING {p}")
            continue
        n, per = sweep(p, verify)
        total += n
        verb = "still carry" if verify else "cleared"
        print(f"  772 {p.name}: {n:,} cell(s) {verb} the literal string "
              f"{SENTINEL!r}")
        for k, v in sorted(per.items(), key=lambda x: -x[1]):
            print(f"    {k:<34} {v:>9,}")
    return 1 if (verify and total) else 0


if __name__ == "__main__":
    sys.exit(main())
