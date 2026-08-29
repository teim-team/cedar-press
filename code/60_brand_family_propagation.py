#!/usr/bin/env python3
"""
Cedar Press - 60: Learn brand families from settled rulings and propagate them.

ELIJAH, 2026-08-06
------------------
"subsidiaries we have identified like Alutiiq we know is owned by Afognak
 Village Corp so even if its Alutiiq Company, Alutiiq Federal Services etc its
 unclear why you aren't able to match this... i should be reviewing only truly
 unambiguous cases"

He is describing the core inefficiency. ANC and tribal subsidiaries are named
by BRAND, not by owner: Afognak trades as Alutiiq, UIC as Bowhead, NANA as
Akima and TKC, Choggiung as Bristol, Calista as Yulista. Ruling one Alutiiq
company taught us nothing about the next eleven, so the same fact was asked
again and again.

HOW A BRAND IS LEARNED, NOT GUESSED
-----------------------------------
Only from attributions that are already settled - Elijah's rulings and tier-A
ledger rows. For each, take the LEADING token of the firm name, which is where
a brand sits ("Alutiiq Pacific, LLC", "Bowhead Mission Solutions"). A token
becomes a brand only when:

  1. at least MIN_FIRMS settled firms share it, and
  2. every one of them resolves to the SAME entity, and
  3. it is not a bare tribal/place word already known to be a trap.

Condition 2 is the whole safety argument. `cherokee` appears under Cherokee
Nation AND under Doyon (Cherokee General Corporation is a Doyon subsidiary), so
it never becomes a brand. `creek`, `colorado`, `ojibwe` and the rest of the
name-trap registry fail the same test on their own evidence rather than because
they are hard-coded.

WHAT IT PRODUCES
----------------
Proposals at tier B - visible, never published. A brand match is strong
evidence, not proof: a firm can share a brand and be a joint venture, or a
divested company. So this shrinks Elijah's queue by pre-filling the obvious and
leaves him ruling the genuinely open ones.

Reads  data/clean/cedar_identifier_ledger_final.csv
       review/rulings_inbox_*.csv, review/agent_rulings_*.csv
Writes data/clean/brand_family_registry.csv     brand -> entity, with evidence
       data/clean/brand_family_proposals.csv    unattributed firms it explains
"""

import csv
import glob
import sys
import importlib.util
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

MIN_FIRMS = 2          # a brand must be demonstrated, not inferred from one row

# Words that can never be a brand: they are corporate furniture, or they are
# geography, or they are the generic vocabulary of Indian Country.
NEVER_BRAND = {
    "the", "a", "of", "and", "native", "american", "indian", "indians",
    "tribal", "tribe", "nation", "national", "alaska", "alaskan", "north",
    "south", "east", "west", "northern", "southern", "eastern", "western",
    "first", "new", "great", "united", "global", "federal", "general",
    "professional", "advanced", "premier", "integrated", "total", "quality",
    "pacific", "atlantic", "mountain", "river", "lake", "valley", "island",
    "inc", "incorporated", "llc", "corp", "corporation", "company", "ltd",
    "limited", "group", "services", "solutions", "systems", "technologies",
    "enterprises", "holdings", "partners", "associates", "consulting",
    # Added after the first run made "brands" of ordinary business vocabulary:
    # `city` -> Pueblo of Acoma and `contractors` -> Bristol Bay Native
    # Corporation both cleared the two-firm bar purely because two settled firms
    # happened to start with the same generic word. A brand has to be a NAME.
    "city", "town", "county", "state", "contractors", "contracting",
    "construction", "development", "management", "aerospace", "defense",
    "environmental", "engineering", "energy", "logistics", "security",
    "industries", "industrial", "resources", "resource", "capital",
    "ventures", "venture", "alliance", "agile", "gaming", "casino",
    "housing", "health", "medical", "education", "transport", "aviation",
    "marine", "network", "networks", "communications", "telecom", "data",
    "digital", "information", "operations", "support", "supply", "staffing",
    "manufacturing", "products", "trading", "investment", "investments",
    "properties", "property", "realty", "insurance", "financial", "finance",
    "black", "white", "red", "blue", "green", "gold", "silver",
}


def load_m33():
    spec = importlib.util.spec_from_file_location(
        "m33", CEDAR / "code" / "33_apply_party_rulings.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def read_csv(p):
    if not Path(p).exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def lead_token(name, m):
    """The brand token: the first meaningful word of the firm name."""
    for t in m.norm(name).split():
        if t not in NEVER_BRAND and len(t) >= 4 and not t.isdigit():
            return t
    return ""


def main():
    print("=== Cedar Press 60: brand family propagation ===\n")
    m = load_m33()
    spine = read_csv(SPINE / "cedar_entity_spine.csv")
    ledger = read_csv(CLEAN / "cedar_identifier_ledger_final.csv")

    # ---- 1. learn brands from settled attributions ----------------------
    evidence = defaultdict(list)          # brand -> [(entity, firm, source)]
    for r in ledger:
        if r.get("confidence_tier") != "A":
            continue
        firm = (r.get("legal_business_name") or "").strip()
        canon = (r.get("canonical_name") or "").strip()
        if not firm or not canon:
            continue
        b = lead_token(firm, m)
        # A firm whose brand IS its owner's name teaches nothing new.
        if not b or b in m.core(canon):
            continue
        evidence[b].append((canon, firm, r.get("identifier", "")))

    # Compare owners by SPINE ID, not by name string.
    #
    # The first run refused `aanikoosing`, `advancia` and `allnative` as
    # "mapping to more than one entity" when the conflicts were
    # "Keweenaw | Keweenaw Bay Indian Community", "Forest County | Forest County
    # Potawatomi" and "Winnebago | Winnebago Tribe of Nebraska" - each ONE
    # entity carrying two name variants in the ledger. Comparing strings
    # manufactured a conflict and threw away a valid brand; comparing resolved
    # ids is the only test that means what it says.
    id_cache = {}

    def owner_id(name):
        if name not in id_cache:
            tid, canon, _how = m.resolve_entity(name, spine)
            id_cache[name] = (tid or f"UNRESOLVED::{name}", canon or name)
        return id_cache[name]

    registry, rejected = [], []
    for b, rows in sorted(evidence.items()):
        owners = {owner_id(e)[0] for e, _f, _i in rows}
        if len(rows) < MIN_FIRMS:
            continue
        if len(owners) > 1:
            # This is the safety property doing its job. `cherokee` fails here
            # because Cherokee General Corporation is Doyon's while Cherokee
            # Nation Businesses is the Nation's.
            rejected.append({"brand": b, "n_firms": len(rows),
                             "conflicting_owners": " | ".join(
                                 sorted({owner_id(e)[1] for e, _f, _i in rows})),
                             "reason": "brand maps to more than one spine entity"})
            continue
        tid = owners.pop()
        canon = owner_id(rows[0][0])[1]
        if tid.startswith("UNRESOLVED::"):
            tid = ""
        registry.append({
            "brand": b, "canonical_name": canon or owner, "tribe_id": tid or "",
            "n_confirmed_firms": len(rows),
            "example_firms": " | ".join(f for _e, f, _i in rows[:4]),
            "learned_from": "tier-A attributions already settled",
            "built_date": TODAY,
        })

    print(f"brands learned : {len(registry)}")
    print(f"brands refused : {len(rejected)}  (map to >1 entity - the guard working)")
    for r in registry[:14]:
        print(f"    {r['brand']:14s} -> {r['canonical_name'][:38]:38s} "
              f"({r['n_confirmed_firms']} firms)")
    if rejected:
        print("  refused:")
        for r in rejected[:6]:
            print(f"    {r['brand']:14s} {r['conflicting_owners'][:64]}")

    # ---- 2. propagate to unattributed firms -----------------------------
    by_brand = {r["brand"]: r for r in registry}
    proposals = []
    for r in ledger:
        if r.get("confidence_tier") in ("A", "X"):
            continue
        firm = (r.get("legal_business_name") or "").strip()
        if not firm:
            continue
        b = lead_token(firm, m)
        hit = by_brand.get(b)
        if not hit or not hit["tribe_id"]:
            continue
        if r.get("canonical_name") == hit["canonical_name"]:
            continue                       # already says the right thing
        proposals.append({
            "identifier_type": r.get("identifier_type", ""),
            "identifier": r.get("identifier", ""),
            "legal_business_name": firm,
            "brand": b,
            "proposed_tribe_id": hit["tribe_id"],
            "proposed_canonical_name": hit["canonical_name"],
            "current_canonical_name": r.get("canonical_name", ""),
            "current_tier": r.get("confidence_tier", ""),
            "n_confirmed_siblings": hit["n_confirmed_firms"],
            "basis": (f"Brand '{b}' resolves to {hit['canonical_name']} across "
                      f"{hit['n_confirmed_firms']} already-settled firms."),
            # Tier B on purpose: a shared brand is strong evidence, not proof.
            # A joint venture or a divested company can carry the brand and not
            # the owner.
            "proposed_tier": "B",
            "built_date": TODAY,
        })

    for path, rows, label in (
        (CLEAN / "brand_family_registry.csv", registry, "brands"),
        (CLEAN / "brand_family_proposals.csv", proposals, "proposals"),
    ):
        if not rows:
            continue
        with open(path, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"\n  wrote {path.relative_to(CEDAR)}  ({len(rows):,} {label})")

    if rejected:
        p = REVIEW / "brand_family_refused.csv"
        with open(p, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rejected[0].keys()))
            w.writeheader()
            w.writerows(rejected)
        print(f"  wrote {p.relative_to(CEDAR)}  ({len(rejected)} refused)")

    hit_ent = Counter(p["proposed_canonical_name"] for p in proposals)
    print(f"\nunattributed firms a learned brand explains: {len(proposals):,}")
    for k, v in hit_ent.most_common(12):
        print(f"    {v:4d}  {k[:44]}")


if __name__ == "__main__":
    main()
