#!/usr/bin/env python3
"""
Cedar Press - 710: A CONTENT KEY FOR faads_entity_attribution.csv.

    py -3 code/710_faads_attribution_content_key.py            # report
    py -3 code/710_faads_attribution_content_key.py --apply
    py -3 code/710_faads_attribution_content_key.py verify     # exit 1 if not unique

WHY - a time bomb with a fuse already lit
-----------------------------------------
`faads_entity_attribution.csv` keys 29,594 attributions to `faads_row_id`,
which is the **row POSITION** in `faads_transactions_all_agencies.csv`:

    73_faads_name_attribution.py:525    for i, r in enumerate(rd):

GRAIN-WS1 found it and named the consequence. A re-extract of that source is
already queued - it has to happen, because the mapper dropped
`assistance_transaction_unique_key` and that column is what makes both faads
tables declarable. **The re-extract will re-order the file, and every one of
those 29,594 attributions will silently re-point to a different transaction.**
Nothing errors. Nothing fails a gate. The numbers stay plausible.

This is the same shape as the `cedar_uid` drop in `admin_appeal_positions.csv`
earlier the same day: a rebuild wearing the costume of an upgrade.

THE FIX IS TO KEY ON CONTENT, NOT POSITION
------------------------------------------
The attribution rows already carry everything needed to re-find their
transaction: FAIN, fiscal year, action date, recipient name, obligated amount,
CFDA programme. They never needed the ordinal.

Measured before writing this:

    natural key (fain, fy, action_date, recipient, amount)   29,500 distinct
      collisions                                                 94

and, following the rule this project has now learned four times, the 94 were
interrogated rather than de-duplicated:

    groups where EVERY column matches (true duplicates)           0
    groups differing only on faads_row_id                        88
    groups also differing on cfda_program                         6

So there are no duplicates here at all. 88 are genuinely distinct source
transactions that agree on every published field, exactly like the 740 UC
Irvine modifications and the 80,778 phantom FPDS duplicates. `cfda_program`
belongs in the key on its own merits and resolves 6 of them; the remaining 88
need an occurrence ordinal, which is a fact about the source file and not a
defect in it.

ORDINAL STABILITY, STATED HONESTLY
----------------------------------
The ordinal is assigned by sorting the members of a collision group on every
remaining content column, so it is deterministic given the same set of rows.
It is NOT stable if the re-extract changes a member's content - and it cannot
be, because at that point they are different rows. That is the correct
behaviour: the key follows the content.

`faads_row_id` is KEPT. It is a true record of what the 2026 build saw, and
deleting it would destroy the only evidence of how the current attributions
were made. It simply stops being the join key.
"""
from __future__ import annotations

import csv
import hashlib
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()
T = ROOT / "data" / "clean" / "faads_entity_attribution.csv"

# What identifies the underlying assistance transaction, independent of where
# it happened to sit in the file.
NATURAL = ("award_id_fain", "fiscal_year", "action_date",
           "recipient_name", "obligated_usd", "cfda_program")

# Never part of the key: our own attribution decision, which can change without
# the transaction changing.
OURS = {"tribe_id", "canonical_name", "entity_class", "spine_state",
        "state_check", "state_check_passed", "match_method", "match_pool",
        "confidence_tier", "tier_rationale", "attributed_date", "cedar_uid",
        "faads_row_id"}

KEY_COL = "faads_attribution_key"


def natural(r: dict) -> tuple:
    return tuple((r.get(c) or "").strip() for c in NATURAL)


def build(rows: list, cols: list) -> tuple:
    groups = defaultdict(list)
    for r in rows:
        groups[natural(r)].append(r)

    # Deterministic ordinal: sort a collision group on every column that is
    # about the TRANSACTION, never on our attribution, then on faads_row_id as
    # the final tiebreak so the assignment is total.
    content = [c for c in cols if c not in OURS and c not in NATURAL]
    collisions = 0
    for k, members in groups.items():
        if len(members) > 1:
            collisions += len(members) - 1
            members.sort(key=lambda r: (
                tuple((r.get(c) or "") for c in content),
                (r.get("faads_row_id") or "")))
        for i, r in enumerate(members):
            h = hashlib.sha1(("|".join(k) + f"|{i}").encode("utf-8"))
            r[KEY_COL] = "FAT-" + h.hexdigest()[:12].upper()
    return groups, collisions


def main() -> int:
    apply = "--apply" in sys.argv
    verify = "verify" in sys.argv

    with T.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        cols = list(rd.fieldnames or [])
        rows = list(rd)

    groups, collisions = build(rows, cols)
    keys = Counter(r[KEY_COL] for r in rows)
    dupes = sum(v - 1 for v in keys.values() if v > 1)

    print(f"  710 faads attribution key   rows {len(rows):,}   "
          f"natural-key groups {len(groups):,}   "
          f"ordinal needed on {collisions}   "
          f"final key collisions {dupes}")

    if dupes:
        print("    REFUSING: the content key is not unique. Do not apply.")
        return 1
    if verify:
        live = [r for r in rows if not (r.get(KEY_COL) or "").strip()]
        # rows read back from disk carry the column only after --apply
        with T.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            on_disk = list(csv.DictReader(fh))
        missing = sum(1 for r in on_disk if not (r.get(KEY_COL) or "").strip())
        print(f"    on disk: {len(on_disk) - missing:,} of {len(on_disk):,} "
              f"rows carry {KEY_COL}")
        return 1 if missing else 0
    if not apply:
        print("    (report only - pass --apply)")
        return 0

    shutil.copy2(T, T.with_name(T.name + f".bak_{TODAY}_pre710"))
    if KEY_COL not in cols:
        cols.insert(0, KEY_COL)
    with T.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"    APPLIED. faads_row_id KEPT as the record of the 2026 build; "
          f"{KEY_COL} is the join key from here.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
