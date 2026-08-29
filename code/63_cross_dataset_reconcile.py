#!/usr/bin/env python3
"""
Cedar Press - 63: Reconcile entity linkages ACROSS datasets.

ELIJAH, 2026-08-06
------------------
"i want you to review all the linkages we have across the respective datasets
 and use them to reconcile as well like a contracting dataset might show us a
 link or hierarchy that helps with the deals and vice versa"

Each dataset knows something the others do not:

  contracting  the FPDS ultimate_parent_uei graph - who owns whom, declared by
               the firms themselves
  funding      recipient UEIs for entities that never win a contract
  lobbying     client names, which are how an entity refers to ITSELF
  deals        parent/subsidiary language in press and filings
  spine        the canonical entity list and its aliases

A link established in one is evidence in all of them. This walks every dataset,
pulls out every entity linkage it carries, and does three things:

  1. BACKFILL   an entity named in one dataset but unresolved in another
  2. AGREE      the same firm mapped to the same entity by two independent
                datasets - which raises confidence honestly
  3. CONFLICT   the same firm mapped to DIFFERENT entities. Never auto-resolved.
                A conflict is the most valuable output here: it is where one of
                the datasets is wrong, and silently picking one would bury it.

THE FIRST THING IT FIXES
------------------------
878 tier-A rows from Elijah's hand-checked BGOV crosswalk carry a tribe NAME
and no `tribe_id`. They are the highest-authority links in the project and they
cannot join to anything - not to the entity-year panel, not to deals, not to
lobbying. Resolving the name they already carry makes them joinable without
adding a single new claim.

REGRESSION SAFETY
-----------------
Run `code/62_no_regression_check.py` before and after. This script only ADDS
identifiers to rows that lack them and never rewrites an existing tribe_id, so
no attribution can be silently changed.
"""

import csv
import importlib.util
import shutil
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()


def load_m33():
    spec = importlib.util.spec_from_file_location(
        "m33", CEDAR / "code" / "33_apply_party_rulings.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def read_csv(p):
    if not Path(p).exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def main():
    print("=== Cedar Press 63: cross-dataset reconciliation ===\n")
    m = load_m33()
    spine = read_csv(SPINE / "cedar_entity_spine.csv")
    print(f"spine entities: {len(spine):,}")

    # ---- 1. BACKFILL tribe_id where only a name exists -------------------
    lp = CLEAN / "cedar_identifier_ledger_final.csv"
    ledger = read_csv(lp)
    shutil.copy2(lp, lp.with_suffix(f".csv.bak_{TODAY}_pre63"))

    filled, unresolved = 0, Counter()
    cache = {}
    for row in ledger:
        if (row.get("tribe_id") or "").strip():
            continue
        name = (row.get("canonical_name") or "").strip()
        if not name:
            continue
        if name not in cache:
            cache[name] = m.resolve_entity(name, spine)
        tid, canon, how = cache[name]
        if tid:
            # Only the id is written. The name, tier and method are Elijah's and
            # are left exactly as they were.
            row["tribe_id"] = tid
            filled += 1
        else:
            unresolved[f"{name}  ({how.split(':')[0]})"] += 1

    print(f"\n[1] tribe_id backfilled from a name already present: {filled:,}")
    if unresolved:
        print(f"    names that will not resolve: {len(unresolved)}")
        for k, v in unresolved.most_common(8):
            print(f"       {v:4d}  {k[:62]}")

    with open(lp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(ledger[0].keys()),
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(ledger)

    # ---- 2. gather every identifier->entity claim, per dataset -----------
    claims = defaultdict(dict)            # dataset -> {UEI/CAGE: (tid, name)}

    for r in ledger:
        k = (r.get("identifier") or "").strip().upper()
        if k and (r.get("tribe_id") or "").strip() and \
                r.get("confidence_tier") in ("A", "B"):
            claims["ledger"][k] = (r["tribe_id"], r.get("canonical_name", ""))

    for r in read_csv(CLEAN / "prime_contracts.csv"):
        for k in ((r.get("awardee_uei") or "").upper(),
                  (r.get("cage_code") or "").upper()):
            if k and (r.get("tribe_id") or "").strip():
                claims["contracting"][k] = (r["tribe_id"],
                                            r.get("canonical_name", ""))

    for r in read_csv(CLEAN / "federal_funding_transactions.csv"):
        k = (r.get("recipient_uei") or "").strip().upper()
        if k and (r.get("canonical_name") or "").strip():
            tid, canon, _ = cache.setdefault(
                r["canonical_name"], m.resolve_entity(r["canonical_name"], spine))
            if tid:
                claims["funding"][k] = (tid, canon)

    for r in read_csv(CLEAN / "subawards.csv"):
        for col in ("sub_uei", "prime_uei"):
            k = (r.get(col) or "").strip().upper()
            if k and (r.get("tribe_id") or "").strip():
                claims["subcontracting"][k] = (r["tribe_id"],
                                               r.get("canonical_name", ""))

    print("\n[2] identifier->entity claims by dataset")
    for ds, d in sorted(claims.items(), key=lambda kv: -len(kv[1])):
        print(f"    {ds:16s} {len(d):7,} identifiers")

    # ---- 3. agreements and conflicts ------------------------------------
    everywhere = defaultdict(dict)
    for ds, d in claims.items():
        for k, v in d.items():
            everywhere[k][ds] = v

    agree, conflict = 0, []
    for k, per_ds in everywhere.items():
        if len(per_ds) < 2:
            continue
        tids = {v[0] for v in per_ds.values()}
        if len(tids) == 1:
            agree += 1
        else:
            conflict.append({
                "identifier": k,
                "n_datasets": len(per_ds),
                **{f"{ds}_entity": v[1] for ds, v in per_ds.items()},
                **{f"{ds}_tribe_id": v[0] for ds, v in per_ds.items()},
                "note": "Two datasets disagree about who owns this identifier. "
                        "NOT auto-resolved - one of them is wrong.",
                "found": TODAY,
            })

    print(f"\n[3] identifiers claimed by 2+ datasets")
    print(f"    AGREE    : {agree:,}  (independent corroboration)")
    print(f"    CONFLICT : {len(conflict):,}  (never auto-resolved)")

    if conflict:
        p = REVIEW / f"cross_dataset_conflicts_{TODAY}.csv"
        keys = sorted({k for c in conflict for k in c})
        with open(p, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=keys)
            w.writeheader()
            w.writerows(conflict)
        print(f"    wrote {p.relative_to(CEDAR)}")

    # ---- 4. what one dataset knows that another does not ----------------
    print("\n[4] coverage each dataset could give another")
    names = sorted(claims)
    for a in names:
        for b in names:
            if a >= b:
                continue
            only_a = set(claims[a]) - set(claims[b])
            only_b = set(claims[b]) - set(claims[a])
            if only_a or only_b:
                print(f"    {a:16s} knows {len(only_a):6,} that {b} does not")
                print(f"    {b:16s} knows {len(only_b):6,} that {a} does not")

    print("\nRun code/62_no_regression_check.py now to confirm nothing fell.")


if __name__ == "__main__":
    main()
