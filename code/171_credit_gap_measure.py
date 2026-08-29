#!/usr/bin/env python3
"""
Cedar Press - 171: MEASURE the assistance credit-instrument gap. READ ONLY.

Zero network. Zero writes to any clean file. It exists so that "the credit gap
closed" is a measurement taken the same way before and after
`115_pull_assistance_archive.py append`, rather than two numbers produced by
two different ad-hoc queries.

WHAT IT COUNTS, AND WHY THE THREE MONEY FIELDS STAY APART
---------------------------------------------------------
A credit row is `assistance_type` in {07, 08, 09}. `credit_instrument_flag` is
NOT used as the definition, because it is blank on every row written by the
pre-archive API route - using it would report the API-era years as having no
credit instruments when what they have is no flag column.

Three money fields, never summed into one figure:

    obligated_usd                 the grant/outlay concept
    face_value_of_loan            the BORROWER'S principal - not federal outlay
    original_loan_subsidy_cost    what the instrument costs the government

`total_face_value_of_loan` is AWARD-CUMULATIVE and is deliberately NOT summed
here (six rows once summed to $271.4M against a true $171.4M).

FINDING 5 IS MEASURED AGAINST, NOT ASSUMED
------------------------------------------
docs/DATA_ODDITIES.md rules that types 07/08/09 all report `obligated_usd` as
exactly 0.00 by design. Confirmed three times independently for 07 and 08 and
CONTRADICTED for 09. This script prints every 07/08/09 row carrying a non-zero
obligation so the contradiction stays visible and is never edited away.

    py -3 code/171_credit_gap_measure.py
"""

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
TARGET = CEDAR / "data" / "clean" / "federal_funding_transactions.csv"
CREDIT_TYPES = ("07", "08", "09")


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else TARGET
    rows_by_fy = Counter()
    credit_by_fy = Counter()
    credit_by_fy_type = defaultdict(Counter)
    money = defaultdict(lambda: defaultdict(float))
    nonzero_obl = []
    total = 0

    with open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        for r in rd:
            total += 1
            fy = (r.get("fiscal_year") or "").strip()
            try:
                fy = str(int(float(fy)))
            except (TypeError, ValueError):
                fy = fy or "(blank)"
            rows_by_fy[fy] += 1
            at = (r.get("assistance_type") or "").strip()
            if at not in CREDIT_TYPES:
                continue
            credit_by_fy[fy] += 1
            credit_by_fy_type[fy][at] += 1
            obl = num(r.get("obligated_usd"))
            money[(fy, at)]["obl"] += obl
            money[(fy, at)]["face"] += num(r.get("face_value_of_loan"))
            money[(fy, at)]["subsidy"] += num(r.get("original_loan_subsidy_cost"))
            if obl != 0.0:
                nonzero_obl.append(
                    (fy, at, r.get("action_date", ""), obl,
                     num(r.get("face_value_of_loan")),
                     r.get("recipient_name", ""),
                     r.get("population_basis", "")))

    print(f"file   : {path}")
    print(f"rows   : {total:,}\n")

    print(f"{'FY':>8} {'rows':>10} {'credit':>8}  by type")
    for fy in sorted(rows_by_fy):
        bt = dict(sorted(credit_by_fy_type[fy].items()))
        print(f"{fy:>8} {rows_by_fy[fy]:>10,} {credit_by_fy[fy]:>8,}  "
              f"{bt if bt else ''}")
    print(f"{'TOTAL':>8} {total:>10,} {sum(credit_by_fy.values()):>8,}")

    print("\ncredit money by FY x type - THREE FIELDS, NEVER POOLED")
    print(f"{'FY':>6} {'type':>5} {'rows':>7} {'obligation':>18} "
          f"{'face_value':>20} {'subsidy_cost':>18}")
    tot = Counter()
    for (fy, at) in sorted(money):
        m = money[(fy, at)]
        n = credit_by_fy_type[fy][at]
        print(f"{fy:>6} {at:>5} {n:>7,} {m['obl']:>18,.2f} "
              f"{m['face']:>20,.2f} {m['subsidy']:>18,.2f}")
        tot[at + "_rows"] += n
        tot[at + "_obl"] += m["obl"]
        tot[at + "_face"] += m["face"]
        tot[at + "_subsidy"] += m["subsidy"]
    print()
    for at in CREDIT_TYPES:
        if tot[at + "_rows"]:
            print(f"  ALL {at}: {int(tot[at+'_rows']):,} rows  "
                  f"obligation {tot[at+'_obl']:,.2f}  "
                  f"face {tot[at+'_face']:,.2f}  "
                  f"subsidy {tot[at+'_subsidy']:,.2f}")

    print(f"\nFINDING 5 CHECK - credit rows with a NON-ZERO obligation: "
          f"{len(nonzero_obl)}")
    print("DATA_ODDITIES.md rules 07/08/09 all report 0.00. Any row below "
          "contradicts that rule and is REPORTED, never edited away.")
    for fy, at, ad, obl, face, name, basis in sorted(nonzero_obl)[:40]:
        print(f"  FY{fy} type {at}  {ad}  obl {obl:>15,.2f}  face {face:>12,.2f}"
              f"  {name[:44]}  [{basis}]")
    if len(nonzero_obl) > 40:
        print(f"  ... {len(nonzero_obl)-40} more")


if __name__ == "__main__":
    main()
