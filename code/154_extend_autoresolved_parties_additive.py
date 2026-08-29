#!/usr/bin/env python3
"""
Cedar Press - 154: add the base-ledger parties to deals_party_autoresolved.csv,
ADDITIVELY. Never a rebuild.

WHY NOT JUST RE-RUN 57
----------------------
THE TRUTH for the deal universe is `data/clean/deals_classified.csv`
(`cedar_domain.DEALS_TRUTH`), 935 rows. This script reads no deals file at all -
it works on `deals_party_autoresolved.csv` - and the mention below is a
description of a defect, not a read. It is stated here so the promoted-table
scan in `160_ship_gap_report.py` section 3h reports this script as a consumer
that knows where the truth is, rather than leaving a reader to check.

Script 57's input glob was `deals_*_additions.csv`, so the 76 verified 2026 YTD
parties and the 2020-2025 historical parties were never offered to the resolver
(same defect as script 88, fixed in both on 2026-08-26; 57 now reads the
promoted table). The obvious fix is to
widen the glob and re-run 57. **That was tried on 2026-08-26 and REJECTED**,
because 57 rewrites its whole output from the CURRENT spine, and the spine has
grown since 57 last ran on 2026-08-06 - 37 tribal colleges among the additions.
Measured on the rejected run, kept at
`data/clean/deals_party_autoresolved.csv.rerun57_2026-08-26_REJECTED`:

    Confederated Salish and Kootenai Tribes  TRBF-CSKTFR-00 -> TCU-SLSHKT-00
    Confederated Tribes of Warm Springs      TRBF-FSCWSA-00 -> TRBF-WRMSPR-00
    Keweenaw Bay Indian Community            TRBF-KWNWBY-00 -> TCU-KWNWB1-00
    United South & Eastern Tribes, Inc.      TRBS-ECSIUT-00 -> ITO-NTDSTH-00

    4 parties LOST outright, 4 silently repointed - two of them from a tribal
    government onto that tribe's COLLEGE.

That is the rebuild-from-a-changed-upstream hazard AGENTS.md records for
`09_import_rulings.py` and `01_build_entity_spine.py`, arriving through a third
script. So: the previous file is authoritative for every party it already
holds, and this script may only ADD parties it does not hold.

THREE PROPOSALS REFUSED BY HAND
-------------------------------
The rejected run's 55 new parties were read one at a time against the spine.
Three are the containment defect and are NOT written:

  Riverside San Bernardino County Indian Health Inc -> UIO-HEALTH-00
      UIO-HEALTH-00 is "Native Health", an ARIZONA urban Indian organisation.
      The party is a CALIFORNIA one. This is the exact cross-state failure
      AGENTS.md names ("Denver Indian Health -> Native Health").

  Department of Hawaiian Home Lands -> NHO-HAWAII-00
      NHO-HAWAII-00 is "Hawaiian Native Corporation". DHHL is a department of
      the State of Hawaii. Two different legal persons sharing the word
      "Hawaiian".

  "Nine tribal applicants incl. Dena' Nena' Henash, Cheyenne & Arapaho Tribes,
  Barona Band" -> TRBF-CHYARP-00
      The party string is an AGGREGATE of nine applicants. Keying it to one of
      them would attribute a nine-recipient award to a single tribe.

Reads  data/clean/deals_party_autoresolved.csv                (authoritative)
       data/clean/deals_party_autoresolved.csv.rerun57_*_REJECTED  (proposals)
Writes data/clean/deals_party_autoresolved.csv   (.part then rename, backup)
       review/deals_party_refused_2026-08-26.csv
"""

import csv
import shutil
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
TARGET = CLEAN / "deals_party_autoresolved.csv"
PROPOSALS = CLEAN / "deals_party_autoresolved.csv.rerun57_2026-08-26_REJECTED"
TODAY = date.today().isoformat()

REFUSE = {
    "Riverside San Bernardino County Indian Health Inc":
        "UIO-HEALTH-00 is 'Native Health', an ARIZONA urban Indian "
        "organisation; this party is a CALIFORNIA one. Cross-state "
        "containment match - the named 'Denver Indian Health -> Native "
        "Health' failure in AGENTS.md.",
    "Department of Hawaiian Home Lands":
        "NHO-HAWAII-00 is 'Hawaiian Native Corporation'. DHHL is a department "
        "of the State of Hawaii. Different legal persons sharing the word "
        "'Hawaiian'.",
    "Nine tribal applicants incl. Dena' Nena' Henash, Cheyenne & Arapaho "
    "Tribes, Barona Band":
        "The party string is an AGGREGATE of nine applicants. Keying it to "
        "TRBF-CHYARP-00 would attribute a nine-recipient award to one tribe.",
    "Federally recognized tribes and tribal health organisations "
    "(aggregate, 8 projects)":
        "Proposed as UIO-HEALTH-00 ('Native Health', an Arizona urban Indian "
        "organisation) purely because the phrase 'health organisations' "
        "contains its name. The party is an AGGREGATE of eight IHS Quarters "
        "Program recipients across several states (ND-2026-083). Two "
        "independent failures in one match: a containment hit on a generic "
        "word, and an aggregate keyed to a single entity.",
}


def load(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def main():
    print("=== 154: extend autoresolved parties, additive only ===\n")
    keep = load(TARGET)
    if not keep:
        print("  authoritative file missing - refusing")
        return
    proposals = load(PROPOSALS)
    if not proposals:
        print(f"  proposals file missing: {PROPOSALS.name} - refusing")
        return

    have = {r["native_party"] for r in keep}
    fields = list(keep[0])
    print(f"  authoritative : {len(keep):,} parties (never modified)")
    print(f"  proposals     : {len(proposals):,}")

    add, refused, stats = [], [], Counter()
    for r in proposals:
        p = r["native_party"]
        if p in have:
            stats["already held - proposal ignored"] += 1
            continue
        if p in REFUSE:
            refused.append({"native_party": p,
                            "proposed_tribe_id": r["tribe_id"],
                            "proposed_canonical_name": r["canonical_name"],
                            "proposed_method": r["match_method"],
                            "n_deals": r.get("n_deals", ""),
                            "refused_date": TODAY,
                            "reason": REFUSE[p],
                            "YOUR_RULING": ""})
            stats["REFUSED by hand"] += 1
            continue
        add.append({k: r.get(k, "") for k in fields})
        stats["added"] += 1

    for k, v in stats.most_common():
        print(f"    {v:4d}  {k}")

    if refused:
        dest = REVIEW / f"deals_party_refused_{TODAY}.csv"
        with open(dest, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(refused[0]))
            w.writeheader()
            w.writerows(refused)
        print(f"\n  wrote {dest.name}  ({len(refused)} refusals, for ruling)")
        for r in refused:
            print(f"    {r['native_party'][:58]:60s} !-> "
                  f"{r['proposed_tribe_id']}")

    if not add:
        print("\n  nothing to add - already applied")
        return

    bak = TARGET.with_suffix(f".csv.bak_{TODAY}_pre154")
    if not bak.exists():
        shutil.copy2(TARGET, bak)
        print(f"\n  backed up -> {bak.name}")

    out = keep + add
    part = TARGET.with_suffix(".csv.part")
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore",
                           restval="")
        w.writeheader()
        w.writerows(out)
    part.replace(TARGET)
    print(f"  wrote {TARGET.name}  ({len(keep):,} -> {len(out):,} parties)")

    # ---- guard: nothing lost, nothing repointed ---------------------------
    after = {r["native_party"]: r["tribe_id"] for r in load(TARGET)}
    before = {r["native_party"]: r["tribe_id"] for r in keep}
    lost = [p for p in before if p not in after]
    moved = [p for p in before if p in after and before[p] != after[p]]
    print(f"\n  GUARD  lost: {len(lost)}   repointed: {len(moved)}")
    if lost or moved:
        print("  FELL - restore from the backup")
    print("\n  now run:  py -3 code/126_apply_deal_party_attribution.py")


if __name__ == "__main__":
    main()
