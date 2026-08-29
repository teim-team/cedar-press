#!/usr/bin/env python3
"""
Cedar Press - 51: Give ANC regional corporations their trading acronyms.

WHY
---
`BSNC REGIONAL SERVICES, LLC` was proposed as Arctic Slope Regional
Corporation. BSNC is Bering Straits Native Corporation, and the firm says so in
its own name - but no spine entity carried the acronym, so the matcher had
nothing to hit and fell through to a weaker signal.

Elijah's rule, verbatim: "when you see abbreviations like BSNC it is likely
(and in this case is) bering straits regional corp."

ANC subsidiaries are named by acronym far more often than by the parent's full
legal name, so this gap is systematic rather than a one-off.

WHICH ACRONYMS QUALIFY
----------------------
Only ones that are BOTH in genuine trading use AND distinctive enough that a
false hit is implausible. Two are deliberately excluded:

    The Aleut Corporation  -> "TAC"   too generic; TAC collides with ordinary
                                      business vocabulary
    Chugach Alaska Corp    -> "CAC"   same problem

Missing an attribution is recoverable. Attributing a stray "CAC" to Chugach is
not, and that asymmetry decides the list. Each acronym is also checked against
every other spine name before being written, so a future addition cannot
silently create a collision.

Reads/writes data/spine/cedar_entity_spine.csv  (aliases column)
"""

import csv
import re
import shutil
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
SPINE = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"
TODAY = date.today().isoformat()

# tribe_id -> acronyms and common trading names
ACRONYMS = {
    "ANRC-ARCSLO-00": ["ASRC"],
    "ANRC-BERSTR-00": ["BSNC"],
    "ANRC-BRBYCO-00": ["BBNC"],
    "ANRC-CKINLT-00": ["CIRI"],
    "ANRC-NANARC-00": ["NANA"],
    "ANRC-AHTNAI-00": ["Ahtna"],
    "ANRC-ALEUTC-00": ["The Aleut Corporation"],
    "ANRC-SEALSK-00": ["Sealaska"],
    "ANRC-KONIAG-00": ["Koniag"],
    "ANRC-CALSTA-00": ["Calista"],
    "ANRC-DOYONL-00": ["Doyon"],
    "ANRC-CHGCCO-00": ["Chugach Alaska"],
}


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def main():
    print("=== Cedar Press 51: ANC acronym aliases ===\n")
    with open(SPINE, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
        fields = list(rows[0].keys())

    shutil.copy2(SPINE, SPINE.with_suffix(f".csv.bak_{TODAY}_pre51"))

    by_id = {r["tribe_id"]: r for r in rows}
    added = skipped = 0

    for tid, acs in ACRONYMS.items():
        row = by_id.get(tid)
        if not row:
            print(f"  !! {tid} not in spine - skipped, not created")
            continue
        existing = [a.strip() for a in (row.get("aliases") or "").split("|")
                    if a.strip()]
        have = {norm(a) for a in existing}

        for ac in acs:
            n = norm(ac)
            if n in have:
                continue
            # Collision guard: refuse an alias that already names, or is a
            # whole token of, some OTHER entity.
            clash = [r for r in rows
                     if r["tribe_id"] != tid
                     and (norm(r["canonical_name"]) == n
                          or n in norm(r["canonical_name"]).split())]
            if clash:
                print(f"  !! '{ac}' collides with {clash[0]['canonical_name']} "
                      f"- refused")
                skipped += 1
                continue
            existing.append(ac)
            have.add(n)
            added += 1
            print(f"  + {ac:24s} -> {row['canonical_name'][:44]}")
        row["aliases"] = "|".join(existing)

    with open(SPINE, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    print(f"\n  aliases added: {added}   refused on collision: {skipped}")
    print(f"  wrote {SPINE.relative_to(CEDAR)}")


if __name__ == "__main__":
    main()
