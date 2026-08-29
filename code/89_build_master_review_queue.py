#!/usr/bin/env python3
"""
Cedar Press - 89: One review queue, ranked by what a ruling is worth.

ELIJAH, 2026-08-07
------------------
"give me an updated queue of native entities you need me to review and link so i
 can work on that as you are building these datasets"

There are 44 review files holding ~35,000 rows. That is a pile, not a queue.
Nobody can work a pile, and the highest-value ruling in the project is currently
sitting somewhere in the middle of it.

RANKED BY WHAT THE RULING IS WORTH, NOT BY WHEN IT WAS WRITTEN
--------------------------------------------------------------
Four things make one ruling worth more than another:

  DOLLARS      an attribution that moves money outranks one that does not
  FAMILY       a ruling that settles a brand or a parent settles its siblings
               too - one ruling once settled 9 firms via `alutiiq`
  CONFLICT     two sources disagreeing, or two of Elijah's own rulings
               disagreeing, blocks publication until it is settled
  BLOCKING     an item a dataset cannot ship without

An item with none of these is real work but it is not urgent, and it should not
sit above an item with all four.

WHAT THIS FILE IS NOT
---------------------
It does not replace the source review files - those keep their evidence, their
columns and their context. This is an INDEX with a ruling column, so the work
can be done in one place and applied back by `09_import_rulings.py`.

Writes review/MASTER_QUEUE_<date>.csv
"""

import csv
import glob
import os
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

# Files that are OUTPUT (already ruled, or pure logs), not input needing a
# ruling. Keeping them out is the difference between a queue and an archive.
SKIP = re.compile(
    r"applied|_log|MASTER_QUEUE|coverage_verification|"
    r"refusals|refused|unparsed|_decisions_", re.I)

NAME_COLS = ("entity_name", "canonical_name", "name", "recipient_name",
             "awardee_name", "legal_business_name", "Native_Party",
             "vendor_name", "facility_name", "org_name", "client_name",
             "tribe", "candidate_name", "prime_name", "sub_name")
ID_COLS = ("cage", "cage_code", "uei", "awardee_uei", "identifier",
           "ein", "facility_id", "Deal_ID", "tribe_id")
DOLLAR_COLS = ("dollars", "obligations", "total_obligations", "amount",
               "amount_usd", "prime_dollars_M", "value", "usd",
               "Announced_Value_USD", "dollars_at_stake", "subaward_amount")
RULING_COLS = ("YOUR_RULING", "your_ruling", "RULING", "ruling")


def pick(row, cands):
    for c in cands:
        for k in row:
            if k and k.lower() == c.lower() and (row.get(k) or "").strip():
                return row[k].strip()
    return ""


def money(row):
    for c in DOLLAR_COLS:
        for k in row:
            if k and c.lower() in k.lower():
                v = (row.get(k) or "").replace("$", "").replace(",", "").strip()
                try:
                    f = float(v)
                except ValueError:
                    continue
                # `prime_dollars_M` is already in millions.
                return f * 1e6 if "_M" in k else f
    return 0.0


def main():
    print("=== Cedar Press 89: master review queue ===\n")
    items, per_file = [], Counter()

    for path in sorted(REVIEW.glob("*.csv")):
        if SKIP.search(path.name):
            continue
        try:
            with open(path, encoding="utf-8-sig", errors="replace",
                      newline="") as fh:
                rows = list(csv.DictReader(fh))
        except Exception:
            continue
        if not rows:
            continue
        has_ruling = any(c in rows[0] for c in RULING_COLS)

        for r in rows:
            # Already ruled in its own file - do not ask twice.
            if has_ruling and any((r.get(c) or "").strip() for c in RULING_COLS):
                continue
            nm = pick(r, NAME_COLS)
            if not nm:
                continue
            usd = money(r)
            blob = " ".join(str(v) for v in r.values()).lower()

            # ---- the four things that make a ruling worth more -----------
            family = bool(re.search(
                r"spiderweb|brand|family|parent|sibling|cluster", blob)) or \
                bool(re.search(r"spiderweb|brand|family", path.name, re.I))
            conflict = bool(re.search(
                r"conflict|disagree|ambiguous|contradict|two rulings|"
                r"vs\.? |both sides", blob)) or \
                bool(re.search(r"conflict|ambiguous", path.name, re.I))
            blocking = bool(re.search(
                r"unreconciled|blocking|cannot ship|must resolve", blob)) or \
                bool(re.search(r"unreconciled", path.name, re.I))

            score = 0.0
            if usd > 0:
                score += min(usd / 1e6, 500)          # capped so one giant
                                                      # row cannot own the top
            if family:
                score += 60
            if conflict:
                score += 120                          # a conflict blocks
                                                      # publication
            if blocking:
                score += 90
            if not (usd or family or conflict or blocking):
                score += 1                            # real work, not urgent

            items.append({
                "rank_score": round(score, 1),
                "entity_name": nm[:80],
                "identifier": pick(r, ID_COLS),
                "dollars_at_stake": round(usd, 2) if usd else "",
                "why_it_matters": " · ".join(filter(None, [
                    "CONFLICT" if conflict else "",
                    "FAMILY - settles siblings" if family else "",
                    "BLOCKING a dataset" if blocking else "",
                    f"${usd/1e6:,.1f}M" if usd >= 1e6 else "",
                ])) or "routine",
                "question": (pick(r, ("question", "issue", "note", "reason",
                                      "tier_rationale", "evidence")) or "")[:220],
                "evidence_url": pick(r, ("evidence_url", "source_url", "url",
                                         "Source_1")),
                "source_file": path.name,
                "YOUR_RULING": "",
            })
            per_file[path.name] += 1

    items.sort(key=lambda x: -x["rank_score"])
    out = REVIEW / f"MASTER_QUEUE_{TODAY}.csv"
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(items[0].keys()))
        w.writeheader()
        w.writerows(items)

    print(f"  wrote {out.relative_to(CEDAR)}  ({len(items):,} items needing a "
          f"ruling)\n")

    tiers = Counter()
    for i in items:
        w_ = i["why_it_matters"]
        tiers["CONFLICT" if "CONFLICT" in w_ else
              "FAMILY" if "FAMILY" in w_ else
              "BLOCKING" if "BLOCKING" in w_ else
              "has dollars" if i["dollars_at_stake"] else "routine"] += 1
    for k, v in tiers.most_common():
        print(f"   {v:6,}  {k}")

    usd = sum(float(i["dollars_at_stake"]) for i in items
              if i["dollars_at_stake"])
    print(f"\n  total dollars sitting behind an unmade ruling: ${usd/1e9:,.2f}B")
    print(f"\n  top 15 by value of the ruling:")
    for i in items[:15]:
        print(f"   {i['rank_score']:7.1f}  {i['entity_name'][:44]:44s} "
              f"{i['why_it_matters'][:38]}")

    print(f"\n  contributing files:")
    for f, n in per_file.most_common(12):
        print(f"   {n:6,}  {f}")


if __name__ == "__main__":
    main()
