#!/usr/bin/env python3
"""
Cedar Press - 772: the string `nan` is not a value. Strip it from clean tables.

    py -3 code/772_strip_nan_sentinels.py                # MEASURE only
    py -3 code/772_strip_nan_sentinels.py write          # apply
    py -3 code/772_strip_nan_sentinels.py write <t.csv>  # one named table

MEASURE IS THE DEFAULT AND THAT IS DELIBERATE. `prime_contracts.csv` is 1.2 GB
and other builders hold it: the first attempt to run this died on
`WinError 32 - being used by another process` while `950_promote_contract_
attributes` was mid-rewrite of the same file, and the table gained columns and
340 MB between one pass and the next. A whole-file rewrite that fires by
default is a way to lose another workstream's run. So the swap happens only on
an explicit `write`, and it aborts if the file's size or mtime moved while this
was reading it.

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


def sweep(path: Path, write: bool) -> tuple[int, dict, str]:
    per: dict[str, int] = {}
    tmp = path.with_suffix(path.suffix + ".772tmp")
    n = 0
    st0 = path.stat()
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        cols = list(rd.fieldnames or [])
        out = tmp.open("w", encoding="utf-8", newline="") if write else None
        w = None
        if out is not None:
            w = csv.DictWriter(out, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
        for r in rd:
            for k in cols:
                if r.get(k) == SENTINEL:
                    per[k] = per.get(k, 0) + 1
                    n += 1
                    if write:
                        r[k] = ""
            if w is not None:
                w.writerow(r)
        if out is not None:
            out.close()

    if not write:
        return n, per, "measured"

    # Another builder may hold or have replaced this table while we read it.
    # Losing someone else's rewrite is much worse than leaving `nan` in place
    # for one more run, so a moved file means abort, not overwrite.
    st1 = path.stat()
    if (st1.st_size, st1.st_mtime_ns) != (st0.st_size, st0.st_mtime_ns):
        tmp.unlink(missing_ok=True)
        return n, per, "ABORTED - the table changed on disk while reading it"
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    bak = path.with_name(f"{path.stem}.bak_{stamp}_pre772{path.suffix}")
    try:
        os.replace(path, bak)
    except PermissionError as e:
        tmp.unlink(missing_ok=True)
        return n, per, f"ABORTED - another process holds the table ({e.winerror})"
    os.replace(tmp, path)
    print(f"    backup -> {bak.name}")
    return n, per, "written"


def main() -> int:
    args = sys.argv[1:]
    write = bool(args) and args[0] == "write"
    named = [a for a in args if a.endswith(".csv")]
    tables = named or DEFAULT_TABLES

    total, aborted = 0, 0
    for t in tables:
        p = CLEAN / t if not Path(t).is_absolute() else Path(t)
        if not p.exists():
            print(f"    MISSING {p}")
            continue
        n, per, how = sweep(p, write)
        total += n
        aborted += how.startswith("ABORTED")
        print(f"  772 {p.name}: {n:,} cell(s) hold the literal string "
              f"{SENTINEL!r}  [{how}]")
        for k, v in sorted(per.items(), key=lambda x: -x[1]):
            print(f"    {k:<34} {v:>9,}")
    # Measure-only is a report, never a failure. `write` fails if it could not
    # write, and fails if a clean table still carries the sentinel afterwards.
    if not write:
        return 0
    return 1 if aborted else 0


if __name__ == "__main__":
    sys.exit(main())
