#!/usr/bin/env python3
"""
Cedar Press - 64: Move ANCSA corporation revenue off village GOVERNMENTS.

THE DEFECT, MEASURED
--------------------
`prime_contracts_entity_year.csv` - a shipped deliverable - books
**$27,593,515,241 across 96 `AKNF-` Alaska Native Village governments** that is
ANCSA *corporation* revenue:

    Chenega        $5.05B      Afognak / Alutiiq   $3.84B
    UIC / Bowhead  $3.74B      Olgoonik            $1.90B
    Goldbelt       $2.64B  ->  booked to Tlingit & Haida, which is not even the
                               namesake - Goldbelt is the Juneau URBAN corporation

Only 19 of the 179 `ANVC-` corporations carry anything at all. This is the same
class as the Kootenai conflation at roughly ten times the scale, and
`review/village_corp_namesake_pairs.csv` already states the rule it breaks:
"a contract to the corporation is not revenue to the government."

AND THE KOOTENAI FIX WAS REGRESSING SILENTLY
--------------------------------------------
`code/09_import_rulings.py` rebuilds `cedar_identifier_ledger_final.csv` FROM
`cedar_identifier_ledger_tiered.csv`. `code/50` patched only the *final* file.
So every run of 09 discarded the patch. It was applied and lost twice, and was
lost again when this was written - while `prime_contracts.csv`, built from a
different vintage, still had it RIGHT. Two shipped artefacts contradicting each
other, with no error anywhere.

The fix is to patch the SOURCE. This script writes to `_tiered`, so 09 rebuilds
carry the correction forward instead of erasing it.

WHAT IT WILL NOT DO
-------------------
It only moves a link when the government and its corporation are a documented
namesake PAIR and the firm carries a corporate form. It never invents a
corporation, never touches a tribal government outside Alaska, and never moves a
link Elijah ruled by hand - his ruling is the authority, and if he put something
on a village government he meant it (as he did for Copper River / Native Village
of Eyak).

Reads  data/clean/cedar_identifier_ledger_tiered.csv   (the SOURCE of truth)
       data/spine/cedar_entity_spine.csv
Writes data/clean/cedar_identifier_ledger_tiered.csv   (corrected in place)
       review/village_government_corrections.csv       (audit trail)
"""

import csv
import importlib.util
import re
import shutil
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

TIERED = CLEAN / "cedar_identifier_ledger_tiered.csv"

CORP_FORM_RE = re.compile(
    r"\b(corporation|corp|incorporated|inc|company|llc|l\.l\.c|ltd|limited|"
    r"holdings|enterprises|services|solutions|systems|technologies|group|jv|"
    r"joint venture|partners)\b", re.I)

# Elijah's own rulings are never overridden here.
HAND_METHODS = {"hand", "bgov_manual", "elijah_ruling", "elijah_ruling_redirect",
                "web_verified", "subsidiary_lookup"}


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
    print("=== Cedar Press 64: village government -> corporation ===\n")
    m = load_m33()
    spine = read_csv(SPINE / "cedar_entity_spine.csv")
    by_id = {r["tribe_id"]: r for r in spine}

    # Namesake pairs: an Alaska village GOVERNMENT and an ANCSA CORPORATION
    # whose identifying words are the same.
    gov = {r["tribe_id"]: m.core(r["canonical_name"]) for r in spine
           if r["tribe_id"].startswith("AKNF-")}
    corp = defaultdict(list)
    for r in spine:
        if r["tribe_id"].startswith("ANVC-"):
            corp[m.core(r["canonical_name"])].append(r)

    pair = {}
    for gid, gcore in gov.items():
        hits = corp.get(gcore, [])
        if len(hits) == 1:
            pair[gid] = hits[0]
    print(f"namesake government/corporation pairs: {len(pair)}")

    ledger = read_csv(TIERED)
    print(f"ledger (tiered, the SOURCE): {len(ledger):,} rows")
    shutil.copy2(TIERED, TIERED.with_suffix(f".csv.bak_{TODAY}_pre64"))

    moved, skipped, audit = 0, Counter(), []
    for row in ledger:
        tid = (row.get("tribe_id") or "").strip()
        if tid not in pair:
            continue
        firm = (row.get("legal_business_name") or "").strip()
        if not firm:
            continue
        if not CORP_FORM_RE.search(firm):
            skipped["no corporate form in the firm name"] += 1
            continue
        if (row.get("attribution_method") or "") in HAND_METHODS:
            # Elijah put it there deliberately. Leave it.
            skipped["hand-attributed by Elijah - left alone"] += 1
            continue

        dest = pair[tid]
        audit.append({
            "identifier_type": row.get("identifier_type", ""),
            "identifier": row.get("identifier", ""),
            "legal_business_name": firm,
            "from_tribe_id": tid,
            "from_entity": by_id[tid]["canonical_name"],
            "from_class": "Alaska Native Village GOVERNMENT",
            "to_tribe_id": dest["tribe_id"],
            "to_entity": dest["canonical_name"],
            "to_class": "ANCSA Village CORPORATION",
            "tier": row.get("confidence_tier", ""),
            "method": row.get("attribution_method", ""),
            "basis": "A corporate firm is owned by the ANCSA corporation, not "
                     "by the village government. Separate legal persons.",
            "corrected": TODAY,
        })
        row["tribe_id"] = dest["tribe_id"]
        row["canonical_name"] = dest["canonical_name"]
        row["tier_rationale"] = (
            f"Corrected {TODAY}: moved from the village government to the "
            f"ANCSA corporation. {row.get('tier_rationale','')}")[:500]
        moved += 1

    print(f"\n  links moved to the corporation : {moved:,}")
    for k, v in skipped.most_common():
        print(f"  left alone : {v:,}  ({k})")

    with open(TIERED, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(ledger[0].keys()),
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(ledger)
    print(f"\n  rewrote {TIERED.relative_to(CEDAR)}  <- the SOURCE, so "
          f"09 rebuilds carry this forward")

    if audit:
        p = REVIEW / "village_government_corrections.csv"
        with open(p, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(audit[0].keys()))
            w.writeheader()
            w.writerows(audit)
        print(f"  wrote {p.relative_to(CEDAR)}  ({len(audit):,} rows)")
        top = Counter(a["to_entity"] for a in audit)
        print("\n  corporations receiving their own links back:")
        for k, v in top.most_common(10):
            print(f"     {v:4d}  {k[:46]}")

    print("\nNEXT: py -3 code/09_import_rulings.py  then  "
          "py -3 code/40_build_prime_contracts.py  then  "
          "py -3 code/62_no_regression_check.py")


if __name__ == "__main__":
    main()
