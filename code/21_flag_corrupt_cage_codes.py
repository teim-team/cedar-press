#!/usr/bin/env python3
"""
Cedar Press - 21: Flag Excel-corrupted CAGE codes across every CAGE-bearing file.

Found by the subcontracting build, 2026-08-05: the HigherGov export was opened
in Excel somewhere upstream, which silently mangled CAGE codes two ways.

  * LEADING ZERO STRIPPED - Boeing's CAGE 03953 stored as 3953. Recoverable by
    zero-padding, but this script FLAGS rather than repairs: a 4-char value
    could in principle be a genuine truncation of something else, and Cedar
    Press does not silently rewrite identifiers.
  * SCIENTIFIC NOTATION - values like 7.80E+09 and 6.90E+25. Unrecoverable;
    the original digits are gone.

Why it matters: `fpds_uei_cage_map.csv` carries these values UNFLAGGED, and
`cedar_cage_backfill.csv` was derived from it (4,362 rows). A CAGE join on
"7.80E+09" silently under-joins and nobody sees a failure.

A valid CAGE is exactly 5 alphanumeric characters.

Outputs (in place, with backups)
-------
data/clean/fpds_uei_cage_map.csv      + cage_malformed_flag, cage_issue
data/clean/cedar_cage_backfill.csv    + cage_malformed_flag, cage_issue
review/corrupt_cage_codes_<date>.csv  the affected rows, for repair upstream
"""

import csv
import re
import shutil
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

VALID_CAGE = re.compile(r"^[A-Z0-9]{5}$")
SCI_NOTATION = re.compile(r"^\d+\.\d+E[+-]\d+$", re.IGNORECASE)

TARGETS = [
    ("fpds_uei_cage_map.csv", "cage_code"),
    ("cedar_cage_backfill.csv", "cage_code"),
]


def classify(cage: str):
    """Return (flag, issue). Empty flag means the value is well-formed."""
    c = (cage or "").strip().upper()
    if not c:
        return "", ""
    if VALID_CAGE.match(c):
        return "", ""
    if SCI_NOTATION.match(c):
        return "UNRECOVERABLE", ("Excel scientific notation - original digits lost. "
                                 "Do not join on this value.")
    if len(c) == 4 and c.isdigit():
        return "LEADING_ZERO_STRIPPED", (f"Likely true CAGE 0{c}. Excel dropped the "
                                          f"leading zero. NOT auto-repaired.")
    if len(c) < 5 and c.isdigit():
        return "LEADING_ZERO_STRIPPED", (f"Likely zero-padded to 5 chars: "
                                          f"{c.zfill(5)}. NOT auto-repaired.")
    if len(c) > 5:
        return "TOO_LONG", f"{len(c)} characters; a CAGE is exactly 5."
    return "MALFORMED", f"Not 5 alphanumeric characters (got {len(c)})."


def read_csv(p):
    if not p.exists():
        return None
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def main():
    print("=== Cedar Press: flag Excel-corrupted CAGE codes ===\n")
    affected = []

    for fname, col in TARGETS:
        path = CLEAN / fname
        rows = read_csv(path)
        if rows is None:
            print(f"  MISSING: {fname}")
            continue
        shutil.copy2(path, path.with_suffix(path.suffix + ".bak_" + TODAY))

        counts = Counter()
        for r in rows:
            flag, issue = classify(r.get(col, ""))
            r["cage_malformed_flag"] = flag
            r["cage_issue"] = issue
            if flag:
                counts[flag] += 1
                affected.append({
                    "source_file": fname,
                    "cage_code": (r.get(col) or "").strip(),
                    "uei": (r.get("uei") or "").strip(),
                    "legal_business_name": (r.get("legal_business_name") or "").strip(),
                    "flag": flag,
                    "issue": issue,
                })

        fields = list(rows[0].keys())
        for extra in ("cage_malformed_flag", "cage_issue"):
            if extra not in fields:
                fields.append(extra)
        with open(path, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)

        total_flagged = sum(counts.values())
        print(f"  {fname}: {len(rows):,} rows, {total_flagged} flagged")
        for k, v in counts.most_common():
            print(f"      {v:>4}  {k}")

    if affected:
        # Dedupe on the identifier pair so the review file lists each once.
        seen, uniq = set(), []
        for a in affected:
            key = (a["cage_code"], a["uei"])
            if key in seen:
                continue
            seen.add(key)
            uniq.append(a)
        REVIEW.mkdir(parents=True, exist_ok=True)
        out = REVIEW / f"corrupt_cage_codes_{TODAY}.csv"
        with open(out, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["source_file", "cage_code", "uei",
                                               "legal_business_name", "flag", "issue"])
            w.writeheader()
            w.writerows(uniq)
        print(f"\n  wrote {out.relative_to(CEDAR)}  ({len(uniq)} distinct)")
        print("\n  Distinct corrupted CAGEs:")
        for a in uniq:
            print(f"    {a['cage_code']:<12} {a['flag']:<22} {a['legal_business_name'][:40]}")

    print("\n  Flagged, not repaired. Cedar Press does not silently rewrite identifiers.")


if __name__ == "__main__":
    main()
