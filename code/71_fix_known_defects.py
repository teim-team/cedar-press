#!/usr/bin/env python3
"""
Cedar Press - 71: Fix every known open defect, and stop each from recurring.

Each entry below was found by an agent or by the regression guard, verified
against the spine, and left open. This closes them in one pass and - more
importantly - adds the ALIAS that caused each, so the same name never fails
again.

Fixes applied to BOTH ledgers. `09_import_rulings.py` rebuilds `_final` from
`_tiered`, so a fix written only to `_final` is discarded on the next import.
That is exactly how the Kootenai correction was lost three times.

  1. 16 tier-A rows with no entity. Every one is a NAME the spine holds under a
     different spelling. Not missing entities - missing aliases.
  2. 29 rows whose tribe_id is not a spine id at all.
  3. Two universities attributed to tribes.
  4. A spine typo.
"""

import csv
import shutil
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
SPINE_P = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"
TODAY = date.today().isoformat()

# name as it appears in the data -> the spine entity it is
NAME_FIX = {
    # The spine calls Fort Belknap by its constituent peoples.
    "Fort Belknap Indian Community": "TRBF-BELKNP-00",
    # Source misspelling: Ildelfonso for Ildefonso.
    "Pueblo of San Ildelfonso": "TRBF-SILDFN-00",
    # Fallon (NV) - NOT Shoshone-Paiute of Duck Valley. Word order alone cannot
    # separate these two; the place name is what does it.
    "Fallon Paiute-Shoshone Tribe": "TRBF-FALLON-00",
    # 91 FR 4102: Mi'kmaq Nation (previously listed as Aroostook Band of Micmacs)
    "Aroostook Band of Micmac Indians": "TRBF-MIKMAQ-00",
    "Confederated Tribes of the Grande Ronde Community of Oregon": "TRBF-GRNRND-00",
    # Spine spells it Timbi-sha.
    "Death Valley Timbisha Shoshone Tribe": "TRBF-TIMBSH-00",
    # The PARENT tribe, not either of its two constituent bands - the source
    # names the tribe, and choosing a band would invent a distinction.
    "Shoshone Bannock Tribes of the Fort Hall Reservation": "TRBF-FTHALL-00",
}

# broken id -> real id. Typos and near-misses that were never caught.
ID_FIX = {
    "TRBF-FCPCMM-00": "TRBF-FSTCTY-00",   # Forest County Potawatomi
    "SGVF-TLNGHD-00": "AKNF-TLNGHD-00-SEALSK",  # Tlingit & Haida
    "TRBF-CHKSAW-00": "TRBF-CHKSWN-00",   # Chickasaw
    "TRBF-CSAKT-00":  "TRBF-CSKTFR-00",   # CSKT
    "TRBF-OHKAYO-00": "TRBF-OKYOWG-00",   # Ohkay Owingeh
    # The Ho-Chunk / Winnebago gold standard: one government was split across
    # two ids, TRBF-WBGNON-00 being a phantom.
    "TRBF-WBGNON-00": "TRBF-WNNBGO-00",
}

# NHO-MANUKAI-00 is NOT remapped. It is absent from the spine AND the NHO
# research found it conflates seventeen or more unrelated organisations,
# including one that is a separate intertribal entity. Picking any single owner
# would be a fabrication, so its links are unattributed and flagged.
CONFLATED = {"NHO-MANUKAI-00"}

# Universities are barred by organisation type - the same rule that withdrew
# $39.43M of lobbying attribution.
BARRED_FIRMS = {
    "NPM2J7MSCF61": "Pennsylvania State University is a university, not a tribal entity",
    "EADLFP7Z72E5": "George Mason University is a university, not a tribal entity",
}

SPINE_TYPO = {"TRBF-WRMSPR-00": ("Warms Springs Tribe", "Warm Springs Tribe")}


def read_csv(p):
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def main():
    print("=== Cedar Press 71: fix known defects ===\n")
    spine = read_csv(SPINE_P)
    by_id = {r["tribe_id"]: r for r in spine}
    valid = set(by_id)
    stats = Counter()

    # ---- 1. spine: typo + the aliases that caused the failures -----------
    shutil.copy2(SPINE_P, SPINE_P.with_suffix(f".csv.bak_{TODAY}_pre71"))
    for tid, (wrong, right) in SPINE_TYPO.items():
        r = by_id.get(tid)
        if r and r["canonical_name"] == wrong:
            r["canonical_name"] = right
            al = [a.strip() for a in (r.get("aliases") or "").split("|") if a.strip()]
            if wrong not in al:
                al.append(wrong)          # keep the old spelling as an alias
            r["aliases"] = "|".join(al)
            stats["spine typo corrected"] += 1
            print(f"  spine: '{wrong}' -> '{right}'")

    for name, tid in NAME_FIX.items():
        r = by_id.get(tid)
        if not r:
            print(f"  !! {tid} not in spine - skipping {name}")
            continue
        al = [a.strip() for a in (r.get("aliases") or "").split("|") if a.strip()]
        if name.lower() not in {a.lower() for a in al}:
            al.append(name)
            r["aliases"] = "|".join(al)
            stats["aliases added"] += 1

    with open(SPINE_P, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(spine[0].keys()),
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(spine)
    print(f"  wrote {SPINE_P.relative_to(CEDAR)}")

    # ---- 2. both ledgers -------------------------------------------------
    for fname in ("cedar_identifier_ledger_tiered.csv",
                  "cedar_identifier_ledger_final.csv"):
        p = CLEAN / fname
        if not p.exists():
            continue
        rows = read_csv(p)
        shutil.copy2(p, str(p) + f".bak_{TODAY}_pre71")
        for r in rows:
            ident = (r.get("identifier") or "").strip().upper()
            tid = (r.get("tribe_id") or "").strip()
            nm = (r.get("canonical_name") or "").strip()

            if ident in BARRED_FIRMS:
                r["confidence_tier"] = "X"
                r["tribe_id"] = ""
                r["tier_rationale"] = (f"Withdrawn {TODAY}: {BARRED_FIRMS[ident]}. "
                                       f"Organisation type bars the match.")
                stats["universities withdrawn"] += 1
                continue

            if tid in CONFLATED:
                r["confidence_tier"] = "C"
                r["tribe_id"] = ""
                r["tier_rationale"] = (
                    f"Unattributed {TODAY}: {tid} conflates seventeen or more "
                    f"unrelated organisations and is not a spine entity. "
                    f"Naming one owner would be a fabrication.")
                stats["conflated NHO unattributed"] += 1
                continue

            if tid in ID_FIX:
                r["tribe_id"] = ID_FIX[tid]
                r["canonical_name"] = by_id[ID_FIX[tid]]["canonical_name"]
                r["tier_rationale"] = (f"Corrected {TODAY}: {tid} was not a spine "
                                       f"id. {r.get('tier_rationale','')}")[:500]
                stats["broken ids remapped"] += 1
                continue

            if not tid and nm in NAME_FIX:
                r["tribe_id"] = NAME_FIX[nm]
                r["canonical_name"] = by_id[NAME_FIX[nm]]["canonical_name"]
                stats["tier-A rows given their entity"] += 1

        with open(p, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()),
                               extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        print(f"  wrote {p.relative_to(CEDAR)}")

    print("\nfixed")
    for k, v in stats.most_common():
        print(f"  {v:5d}  {k}")

    # ---- 3. prove it -----------------------------------------------------
    rows = read_csv(CLEAN / "cedar_identifier_ledger_final.csv")
    a_no_ent = sum(1 for r in rows if r["confidence_tier"] == "A"
                   and not (r.get("tribe_id") or "").strip())
    bad = sum(1 for r in rows if (r.get("tribe_id") or "").strip()
              and r["tribe_id"] not in valid | set(ID_FIX.values()))
    print(f"\n  tier A with no entity  : {a_no_ent}   (was 16)")
    print(f"  non-spine tribe_ids    : {bad}   (was 29)")


if __name__ == "__main__":
    main()
