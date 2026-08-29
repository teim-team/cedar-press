#!/usr/bin/env python3
r"""Cedar Press 160 - carry the 158 corrections into the PUBLISHED property view.

`data/clean/gaming_properties.csv` is the 774-row view that ships. It carries
its own copy of `open_date`, `open_date_basis` and `close_date`, so the day
precision withdrawn from `gaming_facilities.csv` by `code/158` is still sitting
in the shipping file until it is propagated. **Fixing the internal file and
leaving the published one wrong is worse than not fixing it**, because the
disclosure and the artefact then live in different files.

This script does not rebuild the view (script 82 does that, from a stale
upstream). It patches the three date fields IN PLACE by an exact join on
`facility_id`, and appends the rows 158 added so the two files hold the same
universe.

Nothing else in the view is touched.
"""

import csv
import importlib.util
import shutil
import sys
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
TODAY = date.today().isoformat()
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

spec = importlib.util.spec_from_file_location(
    "m157", str(CEDAR / "code" / "157_reconcile_nigc_roster.py"))
M157 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M157)


def main():
    src = CLEAN / "gaming_properties.csv"
    bak = CLEAN / f"gaming_properties.csv.bak_{TODAY}_pre160"
    if not bak.exists():
        shutil.copy2(src, bak)
        print(f"backed up -> {bak.name}")

    view = M157.read_csv(src)
    fields = list(view[0].keys())
    fac = {f["facility_id"]: f for f in M157.read_csv(CLEAN / "gaming_facilities.csv")}
    seen = {v["facility_id"] for v in view}

    stats = Counter()
    for v in view:
        f = fac.get(v["facility_id"])
        if not f:
            stats["no_matching_facility_row"] += 1
            continue
        for fld in ("open_date", "close_date"):
            if (v.get(fld) or "") != (f.get(fld) or ""):
                v[fld] = f.get(fld, "")
                stats[f"{fld}_retyped"] += 1
        if (v.get("open_date_basis") or "") != (f.get("open_date_basis") or ""):
            v["open_date_basis"] = f.get("open_date_basis", "")
            stats["open_date_basis_updated"] += 1

    added = 0
    for fid, f in fac.items():
        if fid in seen:
            continue
        row = {k: "" for k in fields}
        for k in fields:
            if k in f:
                row[k] = f[k]
        row["facility_id"] = fid
        row["entity"] = f.get("tribe_canonical_name", "")
        row["built_date"] = TODAY
        view.append(row)
        added += 1

    M157.write_csv(src, view, fields)
    print(f"gaming_properties.csv: {len(view) - added} -> {len(view)} rows "
          f"({added} appended from gaming_facilities.csv)")
    for k, n in sorted(stats.items()):
        print(f"  {k}: {n}")
    lens = Counter(len(v["open_date"]) for v in view)
    print(f"  open_date value lengths now: {dict(sorted(lens.items()))} "
          f"(4 = year, 7 = month, 10 = day)")


if __name__ == "__main__":
    main()
