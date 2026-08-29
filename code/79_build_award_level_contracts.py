#!/usr/bin/env python3
"""
Cedar Press - 79: Award-level contracting view, and a lean published column set.

ELIJAH, 2026-08-06
------------------
"i believe they are obligations and there is a total obligation so we can base
 it on when the contract was first issued and what it was worth, i know there
 are some additional financial fields but paying attention to all the
 modifications and transactions isnt necessarily as helpful ... i also think
 there are a lot of columns and we dont need them all"

Both right. A subscriber asking "what did this tribe win, and when" does not
want 617,142 transaction rows; they want 318,792 contracts with a start date and
a value. The transactions stay as the source of truth because they are what
makes the sum correct - but they are the ledger, not the product.

THE ARITHMETIC, VERIFIED BEFORE BUILDING
----------------------------------------
Two money columns behave in OPPOSITE ways, and treating them alike is how a
contracting dataset ends up inflated:

  total_obligations   TRANSACTIONAL. Measured across 87,863 multi-row
                      contracts: 81,395 vary up and down - modifications and
                      deobligations. SUMMING IS CORRECT.

  total_award_value   PER-CONTRACT CONSTANT. Contract N6871197C3726 carries
                      745,240 on its FY2000 row AND its FY2001 row. It is the
                      ceiling of the award, restated on every transaction.
                      SUMMING DOUBLE-COUNTS - take the maximum.

That distinction is the whole reason this script exists rather than a GROUP BY.

A CAVEAT KEPT VISIBLE
---------------------
768 contracts repeat an IDENTICAL non-zero obligation on every row, and 5,700
rise monotonically. Both are the cumulative-snapshot signature - the pattern
that inflates USAspending award data ~2.2x if summed. They are a small minority
(7.4% of multi-row contracts) and are flagged rather than dropped, because
dropping them would silently lose real money if the pattern is coincidental.

Writes data/clean/prime_contracts_awards.csv    one row per contract
       data/clean/prime_contracts_published.csv lean subscriber column set
"""

import csv
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
TODAY = date.today().isoformat()

SRC = CLEAN / "prime_contracts.csv"

# The lean set. Everything a subscriber needs to answer "who won what, when,
# from whom, and under what preference" - and nothing that only exists to
# support the build.
#
# Dropped and why: parent_contract_number (an internal vehicle reference),
# supersector (a coarser copy of sector), source_file / source_authority /
# built_date / attribution_method / confidence_tier (provenance - real, and
# INTERNAL per the codebook's access tiers, because their values disclose the
# linkage method), place_of_perform_city (kept at state level; city adds noise
# without adding a question anyone asks).
PUBLISHED = [
    "contract_number", "first_award_fy", "last_action_fy", "n_transactions",
    "awardee_name", "awardee_uei", "cage_code",
    "tribe_id", "canonical_name", "ultimate_parent_entity_name",
    "total_obligated_usd", "max_award_value_usd",
    "funding_agency", "defense", "sector",
    "setaside", "reported_8a", "reported_buy_indian", "reported_indian_business",
    "reported_native_preference", "extent_competed",
    "recipient_state_code", "place_of_perform_state",
    "cumulative_snapshot_flag",
]


def read_csv(p):
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def f(v):
    try:
        return float(v or 0)
    except ValueError:
        return 0.0


def main():
    print("=== Cedar Press 79: award-level contracts ===\n")
    hier = {r["tribe_id"]: r.get("ultimate_parent_entity_name", "")
            for r in read_csv(CEDAR / "data" / "spine" / "cedar_entity_spine.csv")}

    by_contract = defaultdict(list)
    n = 0
    with open(SRC, encoding="utf-8-sig", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            n += 1
            cn = (r.get("contract_number") or "").strip()
            if cn:
                by_contract[cn].append(r)
    print(f"transactions in : {n:,}")
    print(f"distinct awards : {len(by_contract):,}")

    awards, stats = [], Counter()
    for cn, rows in by_contract.items():
        rows.sort(key=lambda r: int(r["fiscal_year"]))
        first, last = rows[0], rows[-1]
        obl = [f(r.get("total_obligations")) for r in rows]

        # The snapshot test, applied per contract rather than assumed.
        snap = ""
        if len(rows) > 1:
            if len(set(obl)) == 1 and obl[0] != 0:
                snap = "identical_every_row"
            elif obl == sorted(obl) and len(set(obl)) > 1:
                snap = "monotonically_rising"
        if snap:
            stats[f"flagged: {snap}"] += 1

        # Attribution: prefer any row that carries an entity. A contract can be
        # attributed on one transaction and not another when the ledger gained
        # the identifier partway through the build.
        attr = next((r for r in rows if (r.get("tribe_id") or "").strip()), first)
        tid = (attr.get("tribe_id") or "").strip()

        awards.append({
            "contract_number": cn,
            "first_award_fy": first["fiscal_year"],
            "last_action_fy": last["fiscal_year"],
            "n_transactions": len(rows),
            "awardee_name": first.get("awardee_name", ""),
            "awardee_uei": first.get("awardee_uei", ""),
            "cage_code": first.get("cage_code", ""),
            "parent_name": first.get("parent_name", ""),
            "parent_uei": first.get("parent_uei", ""),
            "tribe_id": tid,
            "canonical_name": attr.get("canonical_name", ""),
            "ultimate_parent_entity_name": hier.get(tid, ""),
            # SUM - obligations are transactional.
            "total_obligated_usd": round(sum(obl), 2),
            # MAX - award value is restated on every transaction.
            "max_award_value_usd": round(
                max(f(r.get("total_award_value")) for r in rows), 2),
            "funding_agency": first.get("funding_agency", ""),
            "defense": first.get("defense", ""),
            "sector": first.get("sector", ""),
            "supersector": first.get("supersector", ""),
            "setaside": first.get("setaside", ""),
            "reported_8a": first.get("reported_8a", "0"),
            "reported_buy_indian": first.get("reported_buy_indian", "0"),
            "reported_indian_business": first.get("reported_indian_business", "0"),
            "reported_native_preference": first.get("reported_native_preference", "0"),
            "extent_competed": first.get("extent_competed", ""),
            "recipient_state_code": first.get("recipient_state_code", ""),
            "place_of_perform_state": first.get("place_of_perform_state", ""),
            "confidence_tier": attr.get("confidence_tier", "C"),
            "attributed_flag": int(bool(tid)),
            "cumulative_snapshot_flag": snap,
            "built_date": TODAY,
        })

    p1 = CLEAN / "prime_contracts_awards.csv"
    with open(p1, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(awards[0].keys()))
        w.writeheader()
        w.writerows(awards)
    print(f"\n  wrote {p1.relative_to(CEDAR)}  ({len(awards):,} awards, "
          f"{len(awards[0])} columns)")

    p2 = CLEAN / "prime_contracts_published.csv"
    with open(p2, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=PUBLISHED, extrasaction="ignore")
        w.writeheader()
        w.writerows(awards)
    print(f"  wrote {p2.relative_to(CEDAR)}  ({len(PUBLISHED)} columns, "
          f"down from 34)")

    tot = sum(a["total_obligated_usd"] for a in awards)
    att = sum(a["total_obligated_usd"] for a in awards if a["attributed_flag"])
    mx = sum(a["max_award_value_usd"] for a in awards)
    print(f"\n  obligated (summed, correct) : ${tot/1e9:,.2f}B")
    print(f"    of which attributed        : ${att/1e9:,.2f}B "
          f"({att/tot*100:.1f}%)")
    print(f"  award CEILING (max, not summed): ${mx/1e9:,.2f}B")
    print(f"    ^ a different quantity - potential value, not money moved")
    for k, v in stats.most_common():
        print(f"  {v:6,}  {k}")

    yr = Counter(a["first_award_fy"] for a in awards)
    print(f"\n  awards by first-issued year: {min(yr)}-{max(yr)}, "
          f"{len(yr)} years, no gaps: "
          f"{all(str(y) in yr for y in range(int(min(yr)), int(max(yr))+1))}")


if __name__ == "__main__":
    main()
