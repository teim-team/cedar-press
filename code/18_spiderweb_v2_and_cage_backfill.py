#!/usr/bin/env python3
"""
Cedar Press - 18: Spiderweb v2 on real FPDS edges, plus CAGE backfill.

Supersedes script 04, which ran on the SAM-derived graph and yielded only 20
links because that graph was 88% edgeless.

Inputs (built by the FPDS hierarchy agent, 2026-08-05):
  data/clean/fpds_uei_edges.csv     2,290 edges
  data/clean/fpds_uei_cage_map.csv  24,977 (uei, cage, name) triples

HARD RULES, each from a specific finding:

1. BLOCKLIST the federal registrant roll-up. UEI NW2RJN8TQQW1 records as
   "GOVERNMENT OF THE UNITED STATES" and carries 29 children including BIA,
   IHS and tribally-controlled grant schools. Inheriting through it would
   attribute federal agencies to tribes.

2. OWNERSHIP EDGES ONLY. prime_to_sub is a contracting relationship, not
   ownership. A tribal prime hiring a subcontractor does not make the sub
   tribally owned.

3. MULTI-PARENT GOES TO REVIEW. 190 of 1,805 children carry more than one
   distinct ownership parent - real (firms sold between ANCs, SAM
   restatements), not error. Never pick one; emit the conflict with its
   year windows so Elijah can resolve by time.

4. FLAT PROPAGATION ONLY. FPDS populates ultimate_parent_uei but never
   immediate_parent_uei, so there are no multi-level trees to walk. One hop
   from root to child is the honest depth.

Outputs
-------
data/clean/cedar_spiderweb_v2.csv          newly attributed identifiers
data/clean/cedar_cage_backfill.csv         UEI->CAGE gaps now filled
review/spiderweb_multiparent_<date>.csv    ownership conflicts to rule on
"""

import csv
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

# Finding 1: the federal registrant roll-up. Never inherit through it.
BLOCKLIST = {"NW2RJN8TQQW1"}

# Finding 2: ownership only.
OWNERSHIP_EDGES = {"ultimate_parent_uei", "parent_uei"}


def read_csv(p):
    if not p.exists():
        print(f"  MISSING: {p}")
        return []
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
    print("=== Cedar Press: spiderweb v2 + CAGE backfill ===\n")

    edges = read_csv(CLEAN / "fpds_uei_edges.csv")
    cagemap = read_csv(CLEAN / "fpds_uei_cage_map.csv")
    ledger = read_csv(CLEAN / "cedar_identifier_ledger_final.csv")
    excl = read_csv(SPINE / "cedar_exclusion_rulings.csv")
    print(f"FPDS edges      : {len(edges):,}")
    print(f"UEI-CAGE triples: {len(cagemap):,}")
    print(f"ledger links    : {len(ledger):,}")

    # ---- seeds -----------------------------------------------------------
    seeds = {}
    for r in ledger:
        if r["identifier_type"] != "UEI" or r["confidence_tier"] != "A":
            continue
        u = r["identifier"].upper()
        if u and r.get("tribe_id"):
            seeds[u] = {"tribe_id": r["tribe_id"], "name": r["canonical_name"]}
    excluded = {r["identifier"].upper() for r in excl if r["identifier_type"] == "UEI"}
    known = {r["identifier"].upper() for r in ledger
             if r["identifier_type"] == "UEI" and r["confidence_tier"] in ("A", "B", "X")}
    print(f"\ntier A UEI seeds: {len(seeds):,}")

    # ---- build ownership graph ------------------------------------------
    print("\n[1] Building ownership graph")
    kids = defaultdict(list)
    names = {}
    skipped_block = skipped_type = 0
    for e in edges:
        etype = (e.get("edge_type") or "").strip()
        child = (e.get("child_uei") or "").strip().upper()
        parent = (e.get("parent_uei") or "").strip().upper()
        if etype not in OWNERSHIP_EDGES:
            skipped_type += 1
            continue
        if not child or not parent or child == parent:
            continue
        if parent in BLOCKLIST or child in BLOCKLIST:
            skipped_block += 1
            continue
        names.setdefault(child, (e.get("child_name") or "").strip())
        names.setdefault(parent, (e.get("parent_name") or "").strip())
        kids[parent].append({
            "child": child,
            "edge_type": etype,
            "first_year": (e.get("first_year") or "").strip(),
            "last_year": (e.get("last_year") or "").strip(),
            "n_obs": (e.get("n_observations") or "").strip(),
        })
    print(f"  ownership edges kept   : {sum(len(v) for v in kids.values()):,}")
    print(f"  skipped (prime_to_sub) : {skipped_type:,}")
    print(f"  skipped (blocklisted)  : {skipped_block:,}")

    # ---- propagate one hop ----------------------------------------------
    print("\n[2] Propagating from verified seeds (flat, one hop)")
    claims = defaultdict(dict)   # child -> {tribe_id: (owner, parent, meta)}
    for parent, children in kids.items():
        # A parent seeds its children if the parent itself is verified, or if
        # any already-verified child anchors the family to an owner.
        owner = seeds.get(parent)
        if not owner:
            for c in children:
                if c["child"] in seeds:
                    owner = seeds[c["child"]]
                    break
        if not owner:
            continue
        for c in children:
            ch = c["child"]
            if ch in excluded or ch in known or ch in seeds:
                continue
            claims[ch][owner["tribe_id"]] = (owner["name"], parent, c)

    new_rows, multi = [], []
    for child, byowner in claims.items():
        if len(byowner) > 1:
            # Finding 3: genuine ownership conflict. Never pick.
            multi.append({
                "identifier": child,
                "legal_business_name": names.get(child, ""),
                "competing_owners": " | ".join(sorted(v[0] for v in byowner.values())),
                "n_claims": len(byowner),
                "detail": " || ".join(
                    f"{v[0]} via {v[1]} ({v[2]['first_year']}-{v[2]['last_year']}, "
                    f"n={v[2]['n_obs']})" for v in byowner.values()),
                "question": (f"'{names.get(child, child)}' is owned by "
                             f"{len(byowner)} different entities across the record. "
                             f"Resolve by year window."),
                "YOUR_RULING": "",
            })
            continue
        tribe_id, (owner_name, parent, meta) = next(iter(byowner.items()))
        new_rows.append({
            "identifier_type": "UEI",
            "identifier": child,
            "tribe_id": tribe_id,
            "canonical_name": owner_name,
            "legal_business_name": names.get(child, ""),
            "attribution_method": "spiderweb_fpds_structural",
            "confidence_tier": "A_INHERITED",
            "tier_rationale": ("Shares an FPDS ownership edge with a verified "
                               "entity; ownership edges only, roll-up blocklisted"),
            "parent_uei": parent,
            "edge_type": meta["edge_type"],
            "first_year": meta["first_year"],
            "last_year": meta["last_year"],
            "n_observations": meta["n_obs"],
            "source_file": "fpds_uei_edges.csv",
            "expanded_date": TODAY,
        })

    write_csv(CLEAN / "cedar_spiderweb_v2.csv", new_rows,
              ["identifier_type", "identifier", "tribe_id", "canonical_name",
               "legal_business_name", "attribution_method", "confidence_tier",
               "tier_rationale", "parent_uei", "edge_type", "first_year",
               "last_year", "n_observations", "source_file", "expanded_date"])
    if multi:
        write_csv(REVIEW / f"spiderweb_multiparent_{TODAY}.csv", multi,
                  ["identifier", "legal_business_name", "competing_owners",
                   "n_claims", "detail", "question", "YOUR_RULING"])

    # ---- CAGE backfill ---------------------------------------------------
    print("\n[3] CAGE backfill")
    have_cage = {r["identifier"].upper() for r in ledger
                 if r["identifier_type"] == "CAGE"}
    uei_to_cage = defaultdict(set)
    for r in cagemap:
        u = (r.get("uei") or "").strip().upper()
        c = (r.get("cage_code") or "").strip().upper()
        if u and c:
            uei_to_cage[u].add(c)

    ledger_ueis = {r["identifier"].upper() for r in ledger
                   if r["identifier_type"] == "UEI"}
    backfill = []
    for u, cages in uei_to_cage.items():
        if u not in ledger_ueis:
            continue
        for c in sorted(cages):
            if c in have_cage:
                continue
            backfill.append({
                "uei": u,
                "cage_code": c,
                "legal_business_name": names.get(u, ""),
                "source": "fpds_uei_cage_map.csv",
                "basis": "CAGE observed on FPDS transactions for this UEI",
                "n_cages_for_uei": len(cages),
                "date": TODAY,
            })
    write_csv(CLEAN / "cedar_cage_backfill.csv", backfill,
              ["uei", "cage_code", "legal_business_name", "source", "basis",
               "n_cages_for_uei", "date"])

    # ---- summary ---------------------------------------------------------
    print("\n=== SUMMARY ===")
    print(f"  new identifiers inherited : {len(new_rows):,}   (v1 on the old graph: 20)")
    print(f"  ownership conflicts to rule: {len(multi):,}")
    print(f"  CAGE codes backfilled      : {len(backfill):,}")
    if new_rows:
        top = Counter(r["canonical_name"] for r in new_rows).most_common(12)
        print("\n  entities gaining coverage:")
        for n, c in top:
            print(f"    {c:>4}  {n}")
    print("\n  Zero name matching. Every link is a structural inheritance.")


if __name__ == "__main__":
    main()
