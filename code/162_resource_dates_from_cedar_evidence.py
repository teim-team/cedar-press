#!/usr/bin/env python3
r"""Cedar Press 162 - re-source a downgraded date from evidence Cedar already holds.

`code/158` withdrew day precision from 415 values. Some of those properties are
ALSO carried on a second Cedar row that was hand-researched on 2026-08-06 and
carries a day-precision date WITH a citable URL. Where the two rows describe the
same property, the sourced date can replace the vendor's placeholder - and it is
then a free, citable date rather than a vendor one.

THE GUARD IS THE POINT. The sourced date is accepted only when it falls inside
the interval the vendor row itself supports (`open_date_not_before` ..
`open_date_not_after`). Measured on this data, that test refuses more than it
accepts, and every refusal is a real distinction:

    Vee Quiva              vendor 1997-12   sourced 2013-07-02  REFUSED
    Soboba Casino          vendor 1996      sourced 2019-02-20  REFUSED
    Inn of the Mountain Gods vendor 1991    sourced 2005-03-15  REFUSED
    Charging Horse         vendor 1992      sourced 2002-01-17  REFUSED
    Oneida Mason Street    vendor 2000-09   sourced 2001-04-19  REFUSED

Those are not disagreements to average. They are the `open_date_postdates_
observation` case the codebook already names: the sourced date is a REBUILD or a
RE-OPENING, and writing it over the original opening would silently redate the
property by up to sixteen years. Without the interval test this script would
have looked twice as productive and been wrong five times.

Grouping is `core_key(facility_name)` + state - equality on the distinctive
tokens, never containment.
"""

import csv
import importlib.util
import shutil
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
TODAY = date.today().isoformat()
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

spec = importlib.util.spec_from_file_location(
    "m157", str(CEDAR / "code" / "157_reconcile_nigc_roster.py"))
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


def out(s):
    sys.stdout.write(str(s).encode("ascii", "replace").decode() + "\n")


def main():
    src = CLEAN / "gaming_facilities.csv"
    bak = CLEAN / f"gaming_facilities.csv.bak_{TODAY}_pre162"
    if not bak.exists():
        shutil.copy2(src, bak)
    fac = M.read_csv(src)
    fields = list(fac[0].keys())

    groups = defaultdict(list)
    for f in fac:
        groups[(M.core_key(f["facility_name"]), f.get("state", ""))].append(f)

    fixed, refused = [], []
    for _, rows in groups.items():
        donors = [r for r in rows
                  if r.get("open_date_source_url")
                  and r.get("open_date_precision") == "day"
                  and len(r.get("open_date", "")) == 10]
        needy = [r for r in rows
                 if r.get("open_date_source_value_verbatim")
                 and not r.get("open_date_source_url")]
        for q in needy:
            best = None
            for d in donors:
                nb, na = q.get("open_date_not_before"), q.get("open_date_not_after")
                if nb and na and nb <= d["open_date"] <= na:
                    best = d
                    break
                refused.append((q["facility_id"], q["facility_name"],
                                q["open_date"], d["facility_id"], d["open_date"]))
            if not best:
                continue
            q["open_date"] = best["open_date"]
            q["open_date_precision"] = "day"
            q["open_date_source_url"] = best["open_date_source_url"]
            q["open_date_basis"] = (
                f"RE-SOURCED {TODAY} from Cedar row {best['facility_id']} "
                f"({best['facility_name']}), which describes the same property "
                f"and carries a day-precision date with a citable URL. Accepted "
                f"only because {best['open_date']} falls inside the interval the "
                f"original value supported "
                f"({q['open_date_not_before']}..{q['open_date_not_after']}); a "
                f"sourced date outside that interval is a rebuild or a "
                f"re-opening and is refused. Prior value: "
                f"{q['open_date_source_value_verbatim']} "
                f"({q.get('open_date_basis', '')[:120]})")
            q["open_date_evidence"] = (
                q.get("open_date_evidence", "") +
                f" | day precision restored {TODAY} from {best['facility_id']}")
            q["open_date_evidence_url"] = best["open_date_source_url"]
            fixed.append((q["facility_id"], q["facility_name"], q["open_date"]))

    M.write_csv(src, fac, fields)
    out(f"re-sourced to day precision: {len(fixed)}")
    for r in fixed:
        out(f"  {r[0]} {r[1]} -> {r[2]}")
    out(f"refused by the interval guard: {len(refused)}")
    for r in refused:
        out(f"  {r[0]} {r[1]} vendor {r[2]} vs sourced {r[4]} on {r[3]}")


if __name__ == "__main__":
    main()
