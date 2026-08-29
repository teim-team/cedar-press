#!/usr/bin/env python3
"""
Cedar Press - 133: raise entity linkage on resource revenue, honestly.

THE SITUATION, MEASURED 2026-08-12
----------------------------------
`resource_revenue.csv` holds 10,482 rows and only **607 (6%)** carry a
`recipient_entity_id`. That looks like a resolution failure. It is mostly not:

    9,516 unlinked rows carry NO recipient name at all
      of those, 9,238 are ONRR_NRRD_monthly_revenue

ONRR publishes **no tribe-name field for any land class**, 0 of 9,238 Native
rows carry geography, and "Osage" appears zero times in the whole feed despite
that estate having a single owner. Those rows are `WITHHOLDS` - unlinkable by
anyone outside ONRR, permanently. Chasing them is wasted effort.

**359 rows DO carry a name and no id.** Those are the real, closeable gap, and
they come from four sources: UT_COBI fund financials, Osage headright payment
history, Osage quarterly newsletters, and ANCSA 7(i)/7(j) annual reports.

WHAT THIS DOES
--------------
Resolves the named-but-unlinked rows through the SHARED resolver, and writes a
PROPOSAL file. It does not edit `resource_revenue.csv`.

WHAT IT REFUSES
---------------
- **"Holders of Osage headrights (individuals)" is NOT the Osage Nation.** The
  Nation's own auditor states the royalty distributions "are not received by the
  Nation." Attributing headright payments to the tribal government would be a
  category error worth six figures a year. Typed `INDIVIDUAL_BENEFICIARIES` and
  refused a tribe link.
- **Multi-party recipients get no single entity.** "Village corporations and
  at-large shareholders", "The other ANCSA regional corporations" - these name a
  CLASS, not an entity. Splitting a payment across an unnamed class invents rows
  nobody reported. Typed `MULTI_PARTY_CLASS` and refused.
- **A fund is not its beneficiary tribe unless the instrument says so.** The
  Uintah Basin and Navajo Revitalization Funds are state-created funds; the link
  is proposed at tier B with the reason stated, never asserted at A.

    py -3 code/133_link_resource_revenue_entities.py
"""

import csv
import importlib.util
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
SPINE = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"
SRC = CLEAN / "resource_revenue.csv"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

# Names that describe a CLASS of recipients, never one entity.
MULTI_PARTY = re.compile(
    r"village corporations|other ancsa|at-large shareholders|shareholders$", re.I)
# Names that describe individual beneficiaries, not a government.
INDIVIDUALS = re.compile(r"headright|individuals\)|allottee", re.I)


def load(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def main():
    spec = importlib.util.spec_from_file_location(
        "m33", CEDAR / "code" / "33_apply_party_rulings.py")
    m33 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m33)

    spine = load(SPINE)
    rows = load(SRC)
    print(f"=== 133: resource revenue entity linkage ===\n")
    print(f"  rows                 : {len(rows):,}")
    linked_before = sum(1 for r in rows if (r.get("recipient_entity_id") or "").strip())
    print(f"  linked before        : {linked_before:,} "
          f"({100*linked_before/len(rows):.1f}%)")

    named = [r for r in rows
             if (r.get("recipient_entity_name") or "").strip()
             and not (r.get("recipient_entity_id") or "").strip()]
    nameless = [r for r in rows
                if not (r.get("recipient_entity_name") or "").strip()
                and not (r.get("recipient_entity_id") or "").strip()]
    src_nameless = Counter((r.get("source_system") or "?") for r in nameless)
    print(f"  named but unlinked   : {len(named):,}  <- the closeable gap")
    print(f"  nameless             : {len(nameless):,}  <- mostly ONRR, WITHHELD")
    for k, v in src_nameless.most_common(3):
        print(f"      {v:>6,}  {k}")

    props, stats = [], Counter()
    for r in named:
        nm = (r.get("recipient_entity_name") or "").strip()
        base = {
            "resource_revenue_event_id": r.get("resource_revenue_event_id", ""),
            "source_system": r.get("source_system", ""),
            "recipient_entity_name": nm,
            "amount_usd": r.get("amount_usd", ""),
            "payment_date": r.get("payment_date", ""),
            "revenue_type": r.get("revenue_type", ""),
            "built_date": TODAY,
        }
        if INDIVIDUALS.search(nm):
            props.append({**base, "proposed_entity_id": "", "proposed_name": "",
                          "recipient_class": "INDIVIDUAL_BENEFICIARIES",
                          "confidence_tier": "",
                          "basis": "REFUSED - headright/allottee payments run to "
                                   "individuals, not the tribal government; the "
                                   "Nation's own auditor states these are not "
                                   "received by the Nation"})
            stats["REFUSED individual beneficiaries"] += 1
            continue
        if MULTI_PARTY.search(nm):
            props.append({**base, "proposed_entity_id": "", "proposed_name": "",
                          "recipient_class": "MULTI_PARTY_CLASS",
                          "confidence_tier": "",
                          "basis": "REFUSED - names a class of recipients, not "
                                   "one entity; splitting would invent rows"})
            stats["REFUSED multi-party class"] += 1
            continue

        tid, cname, how = m33.resolve_entity(nm, spine)
        if tid:
            props.append({**base, "proposed_entity_id": tid,
                          "proposed_name": cname,
                          "recipient_class": "SINGLE_ENTITY",
                          "confidence_tier": "A",
                          "basis": f"spine resolver matched ({how})"})
            stats["resolved -> A"] += 1
        elif re.search(r"\bfund\b", nm, re.I):
            props.append({**base, "proposed_entity_id": "", "proposed_name": "",
                          "recipient_class": "STATUTORY_FUND",
                          "confidence_tier": "B",
                          "basis": "a state-created fund; beneficiary tribe is "
                                   "implied but the instrument was not read - "
                                   "needs a ruling, never asserted at A"})
            stats["fund -> B, needs ruling"] += 1
        else:
            props.append({**base, "proposed_entity_id": "", "proposed_name": "",
                          "recipient_class": "UNRESOLVED",
                          "confidence_tier": "",
                          "basis": f"resolver could not match ({how})"})
            stats["unresolved"] += 1

    print("\n[outcomes]")
    for k, v in stats.most_common():
        print(f"  {k:40s} {v:>5}")

    would = linked_before + stats["resolved -> A"]
    print(f"\n  linkage if A-tier applied: {linked_before:,} -> {would:,} "
          f"({100*would/len(rows):.1f}%)")
    print(f"  CEILING, honestly        : {len(rows)-len(nameless):,} rows "
          f"({100*(len(rows)-len(nameless))/len(rows):.1f}%) - the rest is "
          f"ONRR withholding, not our gap")

    dest = REVIEW / f"resource_revenue_entity_proposals_{TODAY}.csv"
    if props:
        with open(dest, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(props[0]))
            w.writeheader()
            w.writerows(props)
        print(f"\n  wrote {dest.relative_to(CEDAR)}  ({len(props)} proposals)")
    print("  resource_revenue.csv NOT modified")


if __name__ == "__main__":
    main()
