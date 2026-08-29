#!/usr/bin/env python3
"""
Cedar Press - 22: Apply the 2000 temporal floor across built datasets.

Policy (Elijah, 2026-08-05): every dataset targets 2000-present. Where a source
reaches further back we still stop at 2000 for the published product, because
consistency across datasets beats depth in one and pre-2000 web sourcing is
materially thinner.

IMPLEMENTATION: FLAG, NEVER DELETE.
Cedar Press has a standing never-drop rule, and the floor's rationale is about
*web-sourced* material. A 1987 roll-call vote from Voteview or a 1994 Federal
Register notice is not less reliable than its 2007 equivalent - it is simply
outside the published window. So pre-2000 rows are retained with
`pre_2000_flag = 1` and excluded from the default published view.

Consumers should filter `pre_2000_flag != 1` for the shipped product, and can
opt into the deeper history deliberately.

Outputs: each target file gains `pre_2000_flag` and `floor_basis_field`,
with a .bak_<date> alongside.
"""

import csv
import re
import shutil
import time
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
TODAY = date.today().isoformat()
FLOOR = 2000

YEAR_RE = re.compile(r"(1[89]\d{2}|20\d{2})")

# (file, ordered candidate date/year columns - first one populated wins)
TARGETS = [
    ("federal_actions.csv", ["publication_date", "effective_on"]),
    ("native_bills.csv", ["introduced_date", "congress"]),
    ("bill_votes.csv", ["date"]),
    ("compacts.csv", ["original_effective_date"]),
    ("compact_versions.csv", ["approval_date"]),
    ("fpds_uei_edges.csv", ["first_year"]),
    ("subawards.csv", ["subaward_date", "fiscal_year"]),
]


def year_of(value, column):
    """Extract a 4-digit year. `congress` is an ordinal, not a year."""
    v = (value or "").strip()
    if not v:
        return None
    if column == "congress":
        try:
            # Congress N convened in 1789 + 2*(N-1).
            return 1789 + 2 * (int(float(v)) - 1)
        except ValueError:
            return None
    m = YEAR_RE.search(v)
    return int(m.group(1)) if m else None


def main():
    print("=== Cedar Press: apply 2000 temporal floor ===")
    print("    flag, never delete\n")

    for fname, cols in TARGETS:
        path = CLEAN / fname
        if not path.exists():
            print(f"  SKIP (not built yet): {fname}")
            continue

        # Stream: some of these are 240 MB.
        tmp = path.with_suffix(path.suffix + ".tmp")
        counts = Counter()
        years = []
        with open(path, encoding="utf-8-sig", newline="") as fin, \
             open(tmp, "w", encoding="utf-8", newline="") as fout:
            rd = csv.DictReader(fin)
            usable = [c for c in cols if c in (rd.fieldnames or [])]
            if not usable:
                print(f"  SKIP (no date column of {cols}): {fname}")
                fout.close()
                tmp.unlink(missing_ok=True)
                continue
            fields = list(rd.fieldnames) + [c for c in ("pre_2000_flag", "floor_basis_field")
                                            if c not in rd.fieldnames]
            wr = csv.DictWriter(fout, fieldnames=fields, extrasaction="ignore")
            wr.writeheader()
            for row in rd:
                yr, basis = None, ""
                for c in usable:
                    yr = year_of(row.get(c), c)
                    if yr:
                        basis = c
                        break
                if yr is None:
                    row["pre_2000_flag"] = ""
                    row["floor_basis_field"] = ""
                    counts["undated"] += 1
                else:
                    years.append(yr)
                    row["pre_2000_flag"] = "1" if yr < FLOOR else ""
                    row["floor_basis_field"] = basis
                    counts["pre_2000" if yr < FLOOR else "in_window"] += 1
                wr.writerow(row)

        # Concurrency: agents may hold a large file open while this runs.
        # Windows refuses os.replace on a locked target. Retry briefly, then
        # SKIP that file with a clear message rather than failing the whole
        # pipeline - the flag is idempotent and the next run will apply it.
        replaced = False
        for attempt in range(5):
            try:
                shutil.copy2(path, path.with_suffix(path.suffix + ".bak_" + TODAY))
                tmp.replace(path)
                replaced = True
                break
            except PermissionError:
                time.sleep(2 * (attempt + 1))
        if not replaced:
            tmp.unlink(missing_ok=True)
            print(f"  LOCKED (skipped, will apply next run): {fname}")
            continue

        total = sum(counts.values())
        span = f"{min(years)}-{max(years)}" if years else "n/a"
        pct = (counts['pre_2000'] / total * 100) if total else 0
        print(f"  {fname}")
        print(f"      rows {total:>9,}   span {span:<11} "
              f"pre-2000 {counts['pre_2000']:>7,} ({pct:.1f}%)   "
              f"undated {counts['undated']:,}")

    print(f"\n  Published view = filter `pre_2000_flag != 1`.")
    print(f"  Nothing deleted; the deeper history stays available on request.")


if __name__ == "__main__":
    main()
