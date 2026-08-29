#!/usr/bin/env python3
"""
Cedar Press - 19: Rebuild the NHO layer on corrected logic.

SUPERSEDES script 06, whose central inference was WRONG.

Script 06 treated an active SBA 8(a) certification as proof of NHO ownership.
Elijah disproved it on 2026-08-05 with HALOA CONSTRUCTION LLC (UEI GM3RZPQQQCN1,
CAGE 9GV43) - 8(a) certified, and a FAMILY-OWNED business with no NHO parent.

Why the inference fails: 8(a) admits BOTH entity-owned firms (NHO / tribal /
ANC owned) AND firms owned by socially and economically disadvantaged
INDIVIDUALS. Native Hawaiians qualify as socially disadvantaged individuals,
so a Native Hawaiian family firm can hold 8(a) with no NHO anywhere in its
ownership. This is the individually-owned vs institutionally-owned distinction
that Elijah's Cherokee drops in hci_analysis.do were about, transposed to
Hawaii.

Corrected tiering:
  A  - Elijah has ruled the parent NHO. His ruling is the verification.
  B  - 8(a) certified, ownership class UNRESOLVED. Not publishable as NHO.
  X  - Elijah has ruled it NOT NHO-owned (individually/family owned).

Nothing is called an NHO firm on 8(a) evidence alone, ever again.

Output
------
data/clean/nho_verified_entities.csv   (rewritten on corrected logic)
data/clean/nho_parents.csv             (the NHO parent roster Elijah has ruled)
"""

import csv
import re
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
EXT = CEDAR / "data" / "raw" / "external"
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

EIGHT_A = re.compile(r"8\(?a\)?", re.IGNORECASE)
NOT_NHO = re.compile(r"not\s+nho|family\s+owned|individually", re.IGNORECASE)

# Entity classes that are NOT NHOs even when the parent is Native.
ANC_HINT = re.compile(r"native corporation|regional corporation|,\s*inc(orporated)?$",
                      re.IGNORECASE)


def read_csv(p):
    if not p.exists():
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
    print("=== Cedar Press: NHO layer rebuild (corrected logic) ===\n")

    cands = read_csv(EXT / "hawaii_nho_candidates.csv")
    print(f"Hawaii SAM registrants : {len(cands):,}")

    # Elijah's rulings are the ONLY verification of NHO parentage.
    ruled = {}
    for p in sorted(REVIEW.glob("rulings_inbox_*.csv")):
        for r in read_csv(p):
            rid = (r.get("review_id") or "").strip()
            ruling = (r.get("YOUR_RULING") or "").strip()
            note = (r.get("YOUR_NOTE") or "").strip()
            if not rid.startswith("UEI:") or not ruling:
                continue
            ruled[rid.split(":", 1)[1].upper()] = (ruling, note)
    print(f"Elijah rulings on file : {len(ruled):,}")

    eight_a = [r for r in cands
               if EIGHT_A.search(r.get("Active SBA certifications") or "")]
    print(f"8(a)-certified firms   : {len(eight_a):,}")

    out, parents = [], {}
    for r in eight_a:
        uei = (r.get("uei") or "").strip().upper()
        firm = (r.get("name_clean") or "").strip()
        ruling, note = ruled.get(uei, ("", ""))

        # "UNSURE" is a deferral, not an answer. It must never become a parent
        # entity, and the firm stays unresolved until a real ruling arrives.
        if ruling.strip().upper() in {"UNSURE", "UNKNOWN", "TBD", ""}:
            ruling = ""

        if ruling and NOT_NHO.search(ruling):
            tier, cls, parent = "X", "INDIVIDUAL_OR_FAMILY_OWNED", ""
            basis = (f"Elijah ruled {TODAY}: not NHO-owned. 8(a) reflects "
                     f"individual disadvantaged-business status, not entity ownership.")
        elif ruling:
            parent = ruling
            # A ruled parent may be an ANC rather than an NHO - honour that.
            cls = "ANC" if ANC_HINT.search(parent) and "foundation" not in parent.lower() \
                  else "NHO"
            tier = "A"
            basis = f"Elijah ruled the parent {TODAY}. Ruling is the verification."
            parents.setdefault(parent.upper(), {
                "parent_name": parent, "parent_class": cls,
                "n_subsidiaries": 0, "first_ruled": TODAY,
            })
            parents[parent.upper()]["n_subsidiaries"] += 1
        else:
            tier, cls, parent = "B", "UNRESOLVED", ""
            deferred = uei in ruled and ruled[uei][0].strip().upper() in {
                "UNSURE", "UNKNOWN", "TBD"}
            basis = (("Elijah reviewed and DEFERRED - needs research. " if deferred else "")
                     + "8(a) certified, ownership class UNRESOLVED. 8(a) admits both "
                       "entity-owned and individually-owned firms, so it does not "
                       "establish NHO ownership.")

        out.append({
            "firm_name": firm,
            "uei": uei,
            "cage_code": (r.get("cage_code") or "").strip(),
            "city": (r.get("City") or "").strip(),
            "state": (r.get("State") or "").strip(),
            "sba_certifications": (r.get("Active SBA certifications") or "").strip(),
            "parent_native_entity": parent,
            "parent_entity_class": cls,
            "confidence_tier": tier,
            "verification_basis": basis,
            "elijah_note": note,
            "source_file": "hawaii_nho_candidates.csv + rulings_inbox",
            "rebuilt_date": TODAY,
        })

    write_csv(CLEAN / "nho_verified_entities.csv", out,
              ["firm_name", "uei", "cage_code", "city", "state",
               "sba_certifications", "parent_native_entity", "parent_entity_class",
               "confidence_tier", "verification_basis", "elijah_note",
               "source_file", "rebuilt_date"])

    write_csv(CLEAN / "nho_parents.csv",
              sorted(parents.values(), key=lambda x: -x["n_subsidiaries"]),
              ["parent_name", "parent_class", "n_subsidiaries", "first_ruled"])

    tiers = Counter(r["confidence_tier"] for r in out)
    print("\n=== SUMMARY ===")
    print(f"  tier A (parent ruled)      : {tiers['A']}")
    print(f"  tier B (class unresolved)  : {tiers['B']}")
    print(f"  tier X (not NHO-owned)     : {tiers['X']}")
    print(f"\n  NHO/ANC parents identified : {len(parents)}")
    for p in sorted(parents.values(), key=lambda x: -x["n_subsidiaries"]):
        print(f"    {p['n_subsidiaries']:>2}  {p['parent_name']}  [{p['parent_class']}]")
    print(f"\n  CORRECTION: script 06 called all {len(eight_a)} of these NHO-verified.")
    print(f"  Only {tiers['A']} are, and only because Elijah ruled them.")


if __name__ == "__main__":
    main()
