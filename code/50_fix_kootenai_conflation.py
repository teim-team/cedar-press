#!/usr/bin/env python3
"""
Cedar Press - 50: Split TRBF-KTNIID-00, which conflates two different tribes.

THE DEFECT
----------
`TRBF-KTNIID-00` is labelled "Kootenai" (Kootenai Tribe of Idaho) and carries
seven tier-A identifier links. Six of them are not that tribe:

    S&K Aerospace, S&K Logistics, S&K Global Solutions, S&K Federal Services,
    Salish Kootenai College, and an entry literally named "Cs&Kt"

"S&K" is Salish & Kootenai. These belong to the **Confederated Salish and
Kootenai Tribes of the Flathead Reservation, Montana** - a separate federally
recognised tribe that already exists in the spine as `TRBF-CSKTFR-00`.

Dollar consequence, measured from prime_contracts.csv:

    $2,825.8M booked to "Kootenai Tribe of Idaho"
    $    0.4M actually belongs to it

A 7,000x overstatement for one tribe and a $2.8B hole in another - at tier A,
which is the publishable tier. This is precisely the failure the project's
prime directive exists to prevent, and it survived because both names contain
the token "Kootenai".

WHY THIS IS A CORRECTION AND NOT A PROMOTION
--------------------------------------------
The links were already tier A. This script does not raise anyone's tier; it
moves existing tier-A links to the entity the evidence names. The evidence is
the company's own website, retrieved 2026-08-05:

    "The S&K Family of Companies is committed to ... deliver the maximum
     dividend to our shareholder, the Confederated Salish and Kootenai Tribes"
    -- https://www.skaerospace.com/  (also: "A Family of Salish & Kootenai
       Tribally Owned Businesses"; address St. Ignatius, MT 59865, on the
       Flathead Reservation)

A SECOND DEFECT IN THE SAME ENTITY
----------------------------------
The tier-B EIN 237641597 reads "BLACKFOOT DROVE 190 IDAHO OF THE BENEVOLENT
P[ROTECTIVE ORDER OF ELKS]" - an Elks lodge in Blackfoot, Idaho. Not a Native
organisation at all. Ruled X.

Reads  data/clean/cedar_identifier_ledger_final.csv
       data/clean/prime_contracts.csv
Writes data/clean/cedar_identifier_ledger_final.csv   (corrected in place)
       data/spine/cedar_rulings.csv                   (appended, evidenced)
       review/kootenai_conflation_correction.csv      (the audit trail)
"""

import csv
import re
import shutil
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

WRONG = "TRBF-KTNIID-00"          # Kootenai Tribe of Idaho
RIGHT = "TRBF-CSKTFR-00"          # Confederated Salish and Kootenai Tribes, MT

EVIDENCE = ('S&K\'s own site: "The S&K Family of Companies is committed to ... '
            'deliver the maximum dividend to our shareholder, the Confederated '
            'Salish and Kootenai Tribes." https://www.skaerospace.com/ '
            f'retrieved {TODAY}. Address St. Ignatius MT 59865, Flathead '
            'Reservation.')

# Belongs to CSKT (Montana). Matched on the legal name, not on a token, because
# "Kootenai" is exactly the token that caused the conflation.
CSKT_RE = re.compile(r"\bs\s*(&|and)\s*k\b|salish|cs\s*&\s*kt|confederated", re.I)

# Belongs to the Idaho tribe. Must be checked FIRST - "Kootenai Tribe of Idaho"
# would otherwise be safe, but making the positive test explicit means a future
# name variant fails loudly rather than drifting to Montana.
IDAHO_RE = re.compile(r"kootenai tribe of idaho", re.I)

# Not Native at all.
NOT_NATIVE_EINS = {"237641597"}


def read_csv(p):
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def main():
    print("=== Cedar Press 50: split the Kootenai conflation ===\n")

    # PATCH THE SOURCE, NOT THE DERIVED FILE.
    #
    # This script used to write `cedar_identifier_ledger_final.csv`. But
    # `09_import_rulings.py` REBUILDS that file from
    # `cedar_identifier_ledger_tiered.csv` on every run, so every import
    # silently discarded this correction. It was applied and lost twice, and was
    # lost again during a fact-check - while `prime_contracts.csv`, built from a
    # different vintage, still had it RIGHT. Two shipped artefacts contradicting
    # each other, and nothing raised an error.
    #
    # Writing the source makes the fix survive rebuilds.
    lp = CLEAN / "cedar_identifier_ledger_tiered.csv"
    ledger = read_csv(lp)
    shutil.copy2(lp, lp.with_suffix(f".csv.bak_{TODAY}_pre50"))

    # Confirm the destination exists rather than inventing an entity.
    spine = read_csv(SPINE / "cedar_entity_spine.csv")
    dest = next((r for r in spine if r["tribe_id"] == RIGHT), None)
    if not dest:
        raise SystemExit(f"ABORT: {RIGHT} is not in the spine. Refusing to "
                         f"attribute to an entity that does not exist.")
    print(f"destination: {RIGHT}  {dest['canonical_name']} ({dest['state']})")

    audit, moved, kept, killed = [], 0, 0, 0
    for row in ledger:
        if row.get("tribe_id") != WRONG:
            continue
        name = (row.get("legal_business_name") or "").strip()
        ident = row.get("identifier", "")
        before = row.get("confidence_tier", "")

        if ident in NOT_NATIVE_EINS:
            row["confidence_tier"] = "X"
            row["tier_rationale"] = (f"Corrected {TODAY}: Elks lodge in "
                                     f"Blackfoot ID, not a Native organisation")
            action, killed = "ruled_not_native", killed + 1
        elif IDAHO_RE.search(name):
            action, kept = "kept_idaho", kept + 1
        elif CSKT_RE.search(name):
            row["tribe_id"] = RIGHT
            row["canonical_name"] = dest["canonical_name"]
            row["tier_rationale"] = (f"Corrected {TODAY}: S&K family is owned "
                                     f"by CSKT (Montana), not the Kootenai "
                                     f"Tribe of Idaho. {EVIDENCE}")
            action, moved = "moved_to_cskt", moved + 1
        else:
            # Neither test fired. Do not guess which tribe it is.
            row["confidence_tier"] = "B"
            row["tier_rationale"] = (f"Held {TODAY}: sits under a conflated "
                                     f"entity and matches neither tribe by "
                                     f"name. Needs a ruling.")
            action = "held_for_ruling"

        audit.append({"identifier_type": row.get("identifier_type", ""),
                      "identifier": ident, "legal_business_name": name,
                      "tier_before": before,
                      "tier_after": row.get("confidence_tier", ""),
                      "tribe_id_before": WRONG,
                      "tribe_id_after": row.get("tribe_id", ""),
                      "action": action, "evidence": EVIDENCE,
                      "corrected": TODAY})

    print(f"\n  moved to CSKT (Montana) : {moved}")
    print(f"  kept on Kootenai (Idaho): {kept}")
    print(f"  ruled not Native        : {killed}")
    print(f"  held for a ruling       : "
          f"{sum(1 for a in audit if a['action']=='held_for_ruling')}")

    with open(lp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(ledger[0].keys()),
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(ledger)
    print(f"\n  rewrote {lp.relative_to(CEDAR)}")

    p = REVIEW / "kootenai_conflation_correction.csv"
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(audit[0].keys()))
        w.writeheader()
        w.writerows(audit)
    print(f"  wrote {p.relative_to(CEDAR)}  ({len(audit)} rows)")

    # ---- restate the dollars ------------------------------------------
    moved_ids = {a["identifier"] for a in audit if a["action"] == "moved_to_cskt"}
    tot = defaultdict(float)
    pc = CLEAN / "prime_contracts.csv"
    if pc.exists():
        with open(pc, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                if r.get("tribe_id") != WRONG:
                    continue
                key = ("CSKT" if (r.get("awardee_uei") in moved_ids
                                  or r.get("cage_code") in moved_ids
                                  or CSKT_RE.search(r.get("awardee_name", "")))
                       else "Idaho")
                tot[key] += float(r.get("total_obligations") or 0)
        print("\nprime obligations, restated")
        for k, v in sorted(tot.items(), key=lambda kv: -kv[1]):
            print(f"  {k:6s}  ${v/1e6:,.1f}M")
        print("\n  Rebuild with `py -3 code/40_build_prime_contracts.py` to "
              "carry the corrected tribe_id into the contract rows and panel.")


if __name__ == "__main__":
    main()
