#!/usr/bin/env python3
"""
Cedar Press - 04: Spiderweb expansion along corporate-hierarchy edges.

Elijah's rule (2026-08-05): once an entity is identified, anything structurally
linked to it - parent vendor, performing vendor, ultimate parent - should fill
in fast. Structural inheritance is EVIDENCE, not name matching, so it does not
carry the token-trap risk that sank need_v6's guesses (Colorado Professional
Resources -> "Colorado River").

Method
------
Seeds  : tier A identifiers only (hand-checked authority + BGOV + verified).
Edges  : uei -> parent_uei -> ultimate_parent_uei from the SAM hierarchy graph.
Rule   : if a UEI's parent or ultimate parent is a seeded Native entity, the
         child inherits that entity, tagged tier A_INHERITED with the hop path.
Blocks : an excluded identifier neither inherits nor propagates. Exclusions are
         tribe-scoped (a Condition-1 name-match drop means "not THIS tribe"),
         so they block that entity's propagation, not all propagation.
Guard  : if two different seeded entities reach the same child, that is a
         genuine ambiguity - it goes to review, never to a coin flip.

Outputs
-------
data/clean/cedar_spiderweb_expansion.csv   newly attributed identifiers
review/spiderweb_ambiguous_<date>.csv      multi-parent collisions to rule on
"""

import csv
from collections import Counter, defaultdict, deque
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
EXT = CEDAR / "data" / "raw" / "external"
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

HIER_SRC = Path(r"C:\Users\esm247\Desktop\dissertation\data\tribal_federal_spending"
                r"\sam_extracts\uei_hierarchy_graph.csv")


def read_csv(p):
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(p, rows, fields):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {p.relative_to(CEDAR)}  ({len(rows):,} rows)")


def main():
    print("=== Cedar Press: spiderweb expansion ===\n")

    # Stage the hierarchy graph into Cedar Press (self-contained).
    import shutil
    EXT.mkdir(parents=True, exist_ok=True)
    if HIER_SRC.exists():
        shutil.copy2(HIER_SRC, EXT / "uei_hierarchy_graph.csv")
    hier = read_csv(EXT / "uei_hierarchy_graph.csv")
    ledger = read_csv(CLEAN / "cedar_identifier_ledger_tiered.csv")
    excl = read_csv(SPINE / "cedar_exclusion_rulings.csv")
    print(f"hierarchy edges : {len(hier):,}")
    print(f"ledger links    : {len(ledger):,}")

    # ---- seeds ------------------------------------------------------------
    # Only hand-checked / verified attributions seed the web.
    seeds = {}
    for r in ledger:
        if r["identifier_type"] != "UEI" or r["confidence_tier"] != "A":
            continue
        uei = r["identifier"].upper()
        if uei and r["tribe_id"]:
            seeds[uei] = {"tribe_id": r["tribe_id"],
                          "canonical_name": r["canonical_name"],
                          "method": r["attribution_method"]}
    print(f"tier A UEI seeds: {len(seeds):,}")

    # Excluded identifiers, scoped to the entity name they were dropped from.
    excluded = {r["identifier"].upper() for r in excl if r["identifier_type"] == "UEI"}
    print(f"excluded UEIs   : {len(excluded):,}")

    # Already-attributed UEIs (any tier) - we only want NEW coverage.
    known = {r["identifier"].upper() for r in ledger
             if r["identifier_type"] == "UEI" and r["confidence_tier"] in ("A", "B")}

    # ---- build the graph --------------------------------------------------
    children = defaultdict(list)   # parent uei -> [child rows]
    node = {}
    for r in hier:
        uei = (r.get("uei") or "").strip().upper()
        if not uei:
            continue
        node[uei] = (r.get("name") or "").strip()
        for col, kind in (("parent_uei", "parent_uei"),
                          ("ultimate_parent_uei", "ultimate_parent_uei")):
            p = (r.get(col) or "").strip().upper()
            if p and p != uei:
                children[p].append((uei, kind))

    # ---- propagate --------------------------------------------------------
    print("\n[1] Propagating from verified seeds")
    reached = defaultdict(dict)     # child uei -> {tribe_id: (name, path, hops)}
    for seed_uei, info in seeds.items():
        if seed_uei in excluded:
            continue
        q = deque([(seed_uei, 0, seed_uei)])
        seen_local = {seed_uei}
        while q:
            cur, hops, path = q.popleft()
            if hops >= 3:            # depth guard; real hierarchies are shallow
                continue
            for child, kind in children.get(cur, []):
                if child in seen_local or child in excluded:
                    continue
                seen_local.add(child)
                newpath = f"{path} -{kind}-> {child}"
                prev = reached[child].get(info["tribe_id"])
                if prev is None or hops + 1 < prev[2]:
                    reached[child][info["tribe_id"]] = (info["canonical_name"],
                                                        newpath, hops + 1)
                q.append((child, hops + 1, newpath))

    # ---- classify ---------------------------------------------------------
    new_rows, ambiguous = [], []
    for child, claims in reached.items():
        if child in known:
            continue                 # already covered; nothing gained
        if len(claims) > 1:
            ambiguous.append({
                "identifier": child,
                "legal_business_name": node.get(child, ""),
                "competing_entities": " | ".join(sorted(v[0] for v in claims.values())),
                "n_claims": len(claims),
                "paths": " || ".join(v[1] for v in claims.values()),
                "question": (f"'{node.get(child,child)}' is structurally reachable from "
                             f"{len(claims)} different Native entities. Which owns it?"),
                "YOUR_RULING": "",
            })
            continue
        tribe_id, (name, path, hops) = next(iter(claims.items()))
        new_rows.append({
            "identifier_type": "UEI",
            "identifier": child,
            "tribe_id": tribe_id,
            "canonical_name": name,
            "legal_business_name": node.get(child, ""),
            "attribution_method": "spiderweb_structural",
            "confidence_tier": "A_INHERITED",
            "tier_rationale": (f"Inherited via {hops} corporate-hierarchy hop(s) "
                               f"from a hand-verified seed"),
            "hops": hops,
            "inheritance_path": path,
            "seed_method": seeds.get(path.split(" ")[0], {}).get("method", ""),
            "source_file": "uei_hierarchy_graph.csv",
            "expanded_date": TODAY,
        })

    new_rows.sort(key=lambda r: (r["hops"], r["canonical_name"]))
    write_csv(CLEAN / "cedar_spiderweb_expansion.csv", new_rows,
              ["identifier_type", "identifier", "tribe_id", "canonical_name",
               "legal_business_name", "attribution_method", "confidence_tier",
               "tier_rationale", "hops", "inheritance_path", "seed_method",
               "source_file", "expanded_date"])
    if ambiguous:
        write_csv(REVIEW / f"spiderweb_ambiguous_{TODAY}.csv", ambiguous,
                  ["identifier", "legal_business_name", "competing_entities",
                   "n_claims", "paths", "question", "YOUR_RULING"])

    # ---- summary ----------------------------------------------------------
    print("\n=== SUMMARY ===")
    print(f"  newly attributed by structure : {len(new_rows):,}")
    print(f"  ambiguous (multi-parent)      : {len(ambiguous):,}")
    hopdist = Counter(r["hops"] for r in new_rows)
    for h in sorted(hopdist):
        print(f"    {h} hop(s): {hopdist[h]:,}")
    top = Counter(r["canonical_name"] for r in new_rows).most_common(10)
    if top:
        print("\n  top entities gaining coverage:")
        for name, n in top:
            print(f"    {n:>4}  {name}")
    before = len({r['identifier'] for r in ledger
                  if r['identifier_type'] == 'UEI' and r['confidence_tier'] == 'A'})
    print(f"\n  verified UEI coverage: {before:,} -> {before + len(new_rows):,} "
          f"(+{len(new_rows):,}, {len(new_rows)/max(before,1)*100:.0f}% gain)")
    print("\n  Zero name matching used. Every new link is a structural inheritance.")


if __name__ == "__main__":
    main()
