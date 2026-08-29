#!/usr/bin/env python3
"""
Cedar Press - 92: What blocks the identifier registry migration.

SPEC v2, SECTION 5.2
--------------------
"one UEI never silently maps to two active entities; conflicting CAGEs need
 review"

That rule cannot be enforced until the existing violations are adjudicated. This
finds them, plus the duplicate spine entities that Section 5.9's merge/redirect
needs, and stages both for review.

WHY THIS RUNS BEFORE THE MIGRATION
----------------------------------
Migrating a ledger that violates its own uniqueness rule would either silently
drop rows or carry the conflict into the new registry. Either way the conflict
survives and nobody sees it again. Adjudicate first, migrate clean.

Writes review/identifier_conflicts_<date>.csv
       review/spine_duplicate_candidates_<date>.csv
"""

import csv
import re
import sys
from collections import defaultdict, Counter
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

RULED = {"hand", "bgov_manual", "elijah_ruling_redirect", "elijah_ruling",
         "ruling", "web_verified"}


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def read(p):
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def main():
    print("=== Cedar Press 92: conflicts blocking the registry migration ===\n")
    led = read(CLEAN / "cedar_identifier_ledger_final.csv")
    spine = {r["tribe_id"]: r for r in read(SPINE / "cedar_entity_spine.csv")}

    # ---- one identifier -> two entities ---------------------------------
    by = defaultdict(list)
    for r in led:
        i = (r.get("identifier") or "").strip().upper()
        e = (r.get("tribe_id") or "").strip()
        t = (r.get("confidence_tier") or "").strip()
        if i and e and t in ("A", "B"):
            by[(r.get("identifier_type", ""), i)].append(r)

    rows = []
    for (ityp, ival), v in by.items():
        ents = {x["tribe_id"] for x in v}
        if len(ents) < 2:
            continue
        ruled = [x for x in v
                 if (x.get("attribution_method") or "").strip() in RULED]
        # A ruling outranks everything (spec hard constraint 3). If exactly one
        # side is ruled, the answer is already known and this is not a question
        # for Elijah - it is a cleanup.
        auto = "RULED_SIDE_WINS" if len({x["tribe_id"] for x in ruled}) == 1 \
               and ruled else ""
        rows.append({
            "identifier_type": ityp,
            "identifier": ival,
            "n_entities": len(ents),
            "entities": " | ".join(sorted(
                f"{spine.get(e, {}).get('canonical_name', e)} [{e}]"
                for e in ents)),
            "tiers": " | ".join(sorted({x.get("confidence_tier", "") for x in v})),
            "methods": " | ".join(sorted({(x.get("attribution_method") or "")
                                          for x in v})),
            "legal_names": " | ".join(sorted({(x.get("legal_business_name") or "")[:40]
                                              for x in v if x.get("legal_business_name")}))[:200],
            "states": " | ".join(sorted({(x.get("state") or "") for x in v if x.get("state")})),
            "auto_resolution": auto,
            "why_it_blocks": ("Spec 5.2: one identifier never maps to two "
                              "active entities. The registry migration cannot "
                              "enforce uniqueness until this is settled."),
            "YOUR_RULING": "",
        })
    rows.sort(key=lambda r: (r["auto_resolution"] != "", -r["n_entities"]))

    p = REVIEW / f"identifier_conflicts_{TODAY}.csv"
    if rows:
        with open(p, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    print(f"identifier conflicts: {len(rows)}")
    auto = sum(1 for r in rows if r["auto_resolution"])
    print(f"  auto-resolvable (one side is a RULING, which outranks): {auto}")
    print(f"  need Elijah: {len(rows)-auto}")
    if rows:
        print(f"  wrote {p.relative_to(CEDAR)}")

    # ---- duplicate spine entities (Section 5.9 merge/redirect) ----------
    byn = defaultdict(list)
    for tid, r in spine.items():
        byn[norm(r.get("canonical_name", ""))].append(r)
    dups = []
    for k, v in byn.items():
        if len(k) < 4 or len(v) < 2:
            continue
        classes = {x.get("entity_class", "") for x in v}
        states = {x.get("state", "") for x in v}
        # Village corp vs village government with the same name is a KNOWN
        # legitimate pair (77 of them) - never a merge candidate.
        is_namesake = any("Corporation" in c for c in classes) and \
                      any("Village" in c or "tribe" in c.lower() for c in classes)
        dups.append({
            "normalized_name": k,
            "n": len(v),
            "entity_ids": " | ".join(x["tribe_id"] for x in v),
            "names": " | ".join(x.get("canonical_name", "") for x in v),
            "classes": " | ".join(sorted(classes)),
            "states": " | ".join(sorted(s for s in states if s)),
            "likely_legitimate_namesake_pair": int(is_namesake),
            "note": ("Village corporation and village government sharing a "
                     "name are DIFFERENT legal persons - 77 such pairs exist. "
                     "Not a merge." if is_namesake else
                     "Same normalized name, same class - candidate merge under "
                     "spec 5.9 (deprecate + redirect, never delete)."),
            "YOUR_RULING": "",
        })
    dups.sort(key=lambda r: (r["likely_legitimate_namesake_pair"], -r["n"]))
    p2 = REVIEW / f"spine_duplicate_candidates_{TODAY}.csv"
    if dups:
        with open(p2, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(dups[0].keys()))
            w.writeheader()
            w.writerows(dups)
    real = sum(1 for d in dups if not d["likely_legitimate_namesake_pair"])
    print(f"\nduplicate spine names: {len(dups)}")
    print(f"  likely legitimate namesake pairs (corp vs government): "
          f"{len(dups)-real}")
    print(f"  genuine merge candidates: {real}")
    if dups:
        print(f"  wrote {p2.relative_to(CEDAR)}")
        for d in dups[:8]:
            if not d["likely_legitimate_namesake_pair"]:
                print(f"     {d['names'][:56]:56s} {d['classes'][:36]}")


if __name__ == "__main__":
    main()
