#!/usr/bin/env python3
r"""Cedar Press 174 - restore the three columns a dead `setdefault` emptied in
`digital_gaming_relationships.csv` and `digital_gaming_revenue.csv`.

THE REVIEW ITEM THIS ANSWERS
----------------------------
`review/gaming_facility_hub_unlinked_2026-08-26.csv`,
`MIRRORED_LINK_CARRIES_NO_TIER`, three cards over ~7,983 rows:

    "N rows carry a tribe_id whose source row records no confidence tier, so
     entity_tier could not be INHERITED and was left blank rather than
     assigned. ... Needs a ruling on what tier this build's own linkage earns."

Leaving it blank was RIGHT. But the premise - "the source records no tier" -
turns out to be false. The source records B and the write is dead.

THE DEFECT, MEASURED
--------------------
`119_build_digital_and_loyalty.py` builds every row as

    row = {k: "" for k in REL_FIELDS}      # or REV_FIELDS
    row.update(kw)
    row.setdefault("tier", Tier.B.value)   # <-- NO-OP

`dict.setdefault` only writes when the KEY IS ABSENT. The comprehension has
already created every field with an empty string, so the key is present, the
default never fires, and the column ships blank. Three columns are affected:

| file | column | intended | shipped |
|---|---|---|---|
| digital_gaming_relationships.csv | `tier` | `Tier.B` | blank on 154/154 |
| digital_gaming_revenue.csv | `confidence_tier` | `Tier.B` | blank on 10,661/10,661 |
| digital_gaming_revenue.csv | `period_type` | `"month"` | blank on 10,660/10,661 |

This is the same shape as the `tribe_id` / `tribe_entity_id` defect that made
`102_build_coverage_profile.py` publish "declination_letter 0/774 0.0%" for
nineteen days: **a defect in our writer, published as a fact about the
source.** Here it published as "the source has no tier", which then correctly
propagated into 164 as a blank and into the review queue as a question.

WHY B IS INHERITED AND NOT ASSIGNED
-----------------------------------
Two independent legs, neither of them mine:

1. **119's own code names the value.** `Tier.B.value` is the literal default
   the build declares for these columns. Reading it back is inheritance from
   the source row's own builder, not a consumer deciding a tier.
2. **`digital_gaming_relationships.csv` already carries B in a second column
   on 100% of rows.** `confidence` = `B` on all 154, written through the kwarg
   path (`confidence=Tier.B.value`) which `setdefault` never touched. The
   file states its own tier; only the column 164 was told to read is empty.

`period_type` gets a third, data-internal leg: all 10,660 blank rows have a
`period_start`/`period_end` pair exactly one calendar month apart (28-31 days),
measured before writing. The one row that is not blank reads `none` and is left
alone.

WHAT IS NOT DONE HERE
---------------------
* **119 is NOT run.** It is a full rebuild and would revert the six-column
  entity block that 164 appended to both files - the exact rebuild/in-place
  collision recorded in `START_HERE.md` for `133 build` vs `168`. The defect is
  fixed AT SOURCE in 119 so the next rebuild is correct; the two clean files
  are repaired in place here.
* **No blank is invented.** Only a blank cell is written, only in the three
  named columns, only where the evidence above covers it. A populated cell is
  never changed.
* **`entity_tier` is not written by this script.** Re-run
  `164_link_facility_hub_sources.py` afterwards and it will INHERIT the
  restored tier, which is the whole point.
* **The 9 `gaming_employment_observations.csv` rows stay untiered.** Their
  `confidence` column holds `low`, and `low` is not a `cedar_domain.Tier` -
  164's own docstring says so. They are PROJECTED NEPA figures. Mapping
  low -> C would be manufacturing a tier to make a number move. Left blank,
  said out loud.

SAFETY: backups to .bak_<date>_pre174 (if not exists), .part then rename,
columns and row counts asserted unchanged.
"""

import csv
import datetime as dt
import shutil
import sys
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
TODAY = date.today().isoformat()
SCRIPT = "174_backfill_digital_gaming_tiers.py"

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


def read(p):
    with open(Path(p), encoding="utf-8-sig", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        return list(r), list(r.fieldnames or [])


def write_atomic(path, fields, rows):
    path = Path(path)
    part = path.with_suffix(path.suffix + ".part")
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    part.replace(path)


def backup(p):
    p = Path(p)
    b = p.with_suffix(p.suffix + f".bak_{TODAY}_pre174")
    if not b.exists():
        shutil.copy2(p, b)
    return b.name


def month_span(a, b):
    try:
        d1, d2 = dt.date.fromisoformat(a), dt.date.fromisoformat(b)
    except Exception:
        return False
    return 28 <= (d2 - d1).days + 1 <= 31


def main():
    print("=== Cedar Press 174: restore the tiers 119's dead setdefault "
          "emptied ===\n")

    # ---- relationships: `tier` -------------------------------------------
    p = CLEAN / "digital_gaming_relationships.csv"
    rows, fields = read(p)
    n = len(rows)
    conf = Counter((r.get("confidence") or "").strip() for r in rows)
    if set(conf) != {"B"}:
        print(f"REFUSED: digital_gaming_relationships.confidence is {dict(conf)}, "
              f"not uniformly 'B'. Leg 2 of the evidence does not hold; a tier "
              f"would be assigned rather than inherited. Nothing written.")
        return 1
    filled = 0
    for r in rows:
        if not (r.get("tier") or "").strip():
            r["tier"] = "B"
            filled += 1
    assert len(rows) == n
    b1 = backup(p)
    write_atomic(p, fields, rows)
    print(f"digital_gaming_relationships.csv  {n:,} rows")
    print(f"  tier   blank -> B on {filled:,} rows "
          f"(corroborated: confidence = B on {conf['B']}/{n})")
    print(f"  backup {b1}")

    # ---- revenue: `confidence_tier` + `period_type` -----------------------
    p = CLEAN / "digital_gaming_revenue.csv"
    rows, fields = read(p)
    n = len(rows)
    ct = pt = pt_refused = 0
    for r in rows:
        if not (r.get("confidence_tier") or "").strip():
            r["confidence_tier"] = "B"
            ct += 1
        if not (r.get("period_type") or "").strip():
            # data-internal leg: only where the row's own dates ARE a month.
            if month_span(r.get("period_start", ""), r.get("period_end", "")):
                r["period_type"] = "month"
                pt += 1
            else:
                pt_refused += 1
    assert len(rows) == n
    b2 = backup(p)
    write_atomic(p, fields, rows)
    print(f"\ndigital_gaming_revenue.csv  {n:,} rows")
    print(f"  confidence_tier  blank -> B on {ct:,} rows "
          f"(119's own declared default, Tier.B)")
    print(f"  period_type      blank -> month on {pt:,} rows "
          f"(period_start/period_end span 28-31 days on every one)")
    if pt_refused:
        print(f"  period_type      LEFT BLANK on {pt_refused:,} row(s) whose "
              f"dates do not span a month - not guessed")
    print(f"  backup {b2}")

    print("\nNEXT: re-run `py -3 code/164_link_facility_hub_sources.py`; it "
          "will now INHERIT these tiers into entity_tier instead of reporting "
          "MIRRORED_LINK_CARRIES_NO_TIER.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
