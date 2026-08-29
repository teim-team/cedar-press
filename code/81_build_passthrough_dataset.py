#!/usr/bin/env python3
"""
Cedar Press - 81: Native-to-Native pass-through, as its own dataset.

ELIJAH, 2026-08-06
------------------
"Native CDFIs get federal funding, i believe that then can go to different
 native entities. i wonder if that is not tracked, like org pass-throughs. i
 wonder if we can track them" ... "if we can reliably track pass-throughs we
 should create that as its own dataset."

We can track ONE hop reliably, and it is worth its own dataset. We cannot track
the hop he is most curious about, and this file says so plainly rather than
implying coverage it does not have.

WHAT IS TRACKABLE
-----------------
FSRS subaward reporting captures the federal-award pass-through: a Native entity
holds a federal prime award and subcontracts or subgrants part of it to another
Native entity. `data/clean/subawards.csv` already flags these as
`direction == 'both_sides_native'` - 1,225 rows, and 855 survive the two filters
that dataset requires.

That is a real, sourced, second hop. Cherokee Nation to its own housing
authority, 65 times. Chugach Federal Solutions to Port Madison Enterprises. STS
Systems Integration and SpecPro subcontracting to each other in both directions.

WHAT IS NOT TRACKABLE, AND WHY
------------------------------
**A Native CDFI's lending is not in federal data at all.** When the CDFI Fund
awards a Native CDFI $2M and that CDFI lends it to twenty tribal businesses, the
federal record ends at the CDFI. The loans are the CDFI's own transactions.

CDFIs do file **Transaction Level Reports** with the CDFI Fund, which are
loan-level - but they are confidential and only aggregates are published. So the
honest position is:

    hop 1  federal -> CDFI          VISIBLE (CDFI Fund awards, USAspending)
    hop 2  CDFI -> borrower         NOT VISIBLE, and not a gap we can close
                                    by pulling harder

The one partial exception: a CDFI that is a 501(c)(3) making GRANTS (not loans)
reports them on **Form 990 Schedule I**. That catches grantmaking and misses
lending, which is most of what a CDFI does.

THE CAVEAT THAT TRAVELS WITH EVERY ROW
--------------------------------------
FSRS is self-reported by the prime with no validation at submission. This
dataset is **reliable about relationships and unreliable about amounts** - 5,941
rows across the parent report a subaward larger than its own prime award. So the
relationship columns are the product; the dollars carry a filter and a warning.

Writes data/clean/native_passthrough.csv
       data/clean/native_passthrough_pairs.csv   entity-to-entity, aggregated
"""

import csv
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
TODAY = date.today().isoformat()


def read_csv(p):
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def main():
    print("=== Cedar Press 81: Native-to-Native pass-through ===\n")
    spine = {r["tribe_id"]: r for r in
             read_csv(CEDAR / "data" / "spine" / "cedar_entity_spine.csv")}
    rows = read_csv(CLEAN / "subawards.csv")
    print(f"subaward rows: {len(rows):,}")

    pt = [r for r in rows if r.get("direction") == "both_sides_native"]
    print(f"both sides Native: {len(pt):,}")

    out, stats = [], Counter()
    for r in pt:
        pid = (r.get("prime_native_tribe_id") or "").strip()
        sid = (r.get("sub_native_tribe_id") or "").strip()
        if not pid or not sid:
            stats["dropped: one side unresolved"] += 1
            continue

        # The two filters the parent dataset requires before any dollar is
        # summed. Kept as COLUMNS rather than applied destructively, so a
        # subscriber can reproduce or disagree with our totals.
        primary = r.get("duplicate_status") == "primary"
        sane = r.get("subaward_exceeds_prime_flag") != "yes"
        if primary and sane:
            stats["countable"] += 1
        else:
            stats["relationship only - amount not countable"] += 1

        # Self-dealing is a real and interesting category, not an error: a
        # tribe subcontracting to its own housing authority or enterprise.
        # Cherokee Nation -> Housing Authority of the Cherokee Nation, 65 times.
        same_entity = pid == sid
        same_family = (spine.get(pid, {}).get("ultimate_parent_entity_id") ==
                       spine.get(sid, {}).get("ultimate_parent_entity_id")
                       and spine.get(pid, {}).get("ultimate_parent_entity_id"))

        out.append({
            "subaward_number": r.get("subaward_number", ""),
            "prime_award_id": r.get("prime_award_id", ""),
            "fiscal_year": r.get("fiscal_year", ""),
            "subaward_date": r.get("subaward_date", ""),
            "from_tribe_id": pid,
            "from_entity": spine.get(pid, {}).get("canonical_name", ""),
            "from_firm": r.get("prime_name", ""),
            "to_tribe_id": sid,
            "to_entity": spine.get(sid, {}).get("canonical_name", ""),
            "to_firm": r.get("sub_name", ""),
            "amount_usd": r.get("subaward_amount", ""),
            "amount_countable": int(primary and sane),
            "award_kind": r.get("award_kind", ""),
            "prime_top_awarding_agency": r.get("prime_top_awarding_agency", ""),
            "naics_title": r.get("naics_title", ""),
            "relationship": ("same_entity" if same_entity else
                             "same_ultimate_parent" if same_family else
                             "different_entities"),
            "reliability_note": ("FSRS is self-reported by the prime with no "
                                 "validation. The RELATIONSHIP is reliable; the "
                                 "AMOUNT is countable only where "
                                 "amount_countable = 1."),
            "built_date": TODAY,
        })

    p1 = CLEAN / "native_passthrough.csv"
    with open(p1, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    print(f"\n  wrote {p1.relative_to(CEDAR)}  ({len(out):,} rows)")
    for k, v in stats.most_common():
        print(f"     {v:5,}  {k}")

    # ---- entity-to-entity aggregate --------------------------------------
    agg = defaultdict(lambda: {"n": 0, "usd": 0.0, "years": set(), "kind": Counter()})
    for r in out:
        k = (r["from_tribe_id"], r["from_entity"], r["to_tribe_id"], r["to_entity"])
        a = agg[k]
        a["n"] += 1
        a["years"].add(r["fiscal_year"])
        a["kind"][r["award_kind"]] += 1
        if r["amount_countable"]:
            try:
                a["usd"] += float(r["amount_usd"] or 0)
            except ValueError:
                pass

    pairs = [{
        "from_tribe_id": k[0], "from_entity": k[1],
        "to_tribe_id": k[2], "to_entity": k[3],
        "n_subawards": v["n"],
        "countable_usd": round(v["usd"], 2),
        "first_year": min(v["years"]) if v["years"] else "",
        "last_year": max(v["years"]) if v["years"] else "",
        "award_kinds": "|".join(sorted(v["kind"])),
        "built_date": TODAY,
    } for k, v in agg.items()]
    pairs.sort(key=lambda r: -r["countable_usd"])

    p2 = CLEAN / "native_passthrough_pairs.csv"
    with open(p2, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(pairs[0].keys()))
        w.writeheader()
        w.writerows(pairs)
    print(f"  wrote {p2.relative_to(CEDAR)}  ({len(pairs):,} entity pairs)")

    tot = sum(p["countable_usd"] for p in pairs)
    ents = {p["from_tribe_id"] for p in pairs} | {p["to_tribe_id"] for p in pairs}
    rel = Counter(r["relationship"] for r in out)
    print(f"\n  distinct entities involved : {len(ents)}")
    print(f"  countable pass-through     : ${tot/1e6:,.1f}M")
    print(f"  relationship types         : {dict(rel)}")
    print("\n  largest flows:")
    for p in pairs[:6]:
        print(f"     ${p['countable_usd']/1e6:8.1f}M  {p['from_entity'][:26]:26s} "
              f"-> {p['to_entity'][:26]}")


if __name__ == "__main__":
    main()
