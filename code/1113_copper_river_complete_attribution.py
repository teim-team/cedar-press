#!/usr/bin/env python3
"""
Cedar Press - 1113: finish the Copper River attribution I left half-done.

    py -3 code/1113_copper_river_complete_attribution.py            # report
    py -3 code/1113_copper_river_complete_attribution.py apply
    py -3 code/1113_copper_river_complete_attribution.py verify

WHY THIS EXISTS
---------------
`1123` announced "$1.5B attributed" and the table attributed nothing. The
quarantine workstream caught it and was right on every count. Measured:

    4,272 Copper River rows
      tribe_id blank ................ 4,266   (6 still say ANVC-SLDVSS-00)
      attributed_flag = 0 ........... 4,266
      attribution_method ............ an English sentence, on all 4,272

`1123` wrote `cedar_uid` and `canonical_name` and stopped. Those two are not
what this table attributes with: `40_build_prime_contracts.py` keys on
`tribe_id`, gates on `attributed_flag`, and reads `attribution_method` as a
CONTROLLED VOCABULARY — `unattributed` / `uei_exact` / `cage_exact` /
`parent_uei` / `ruling_applied`. Writing prose into it did three things:

  1. left every row reading `attributed_flag = 0`, so the table's own answer to
     "is this attributed?" was still no;
  2. left 6 rows self-contradicting — `canonical_name` Eyak, `tribe_id`
     Seldovia;
  3. **broke a neighbouring pass's leg detection**, because 1,486 rows suddenly
     carried a method outside the vocabulary it switches on.

A rebuild would have reverted all of it, and the commit message would still
have said $1.5B.

THE LESSON, WHICH IS THE SAME ONE AGAIN
---------------------------------------
I checked conservation — rows and dollars, to the cent — and conservation was
never the risk. Nothing moved because nothing was attributed. **A proof that
nothing broke is not a proof that something happened.** The check to write is
the one that fails when the work did not land.

WHAT THIS DOES
--------------
Completes the attribution on the columns the table actually uses, keeps the
evidence, and restores the vocabulary:

    tribe_id            -> AKNF-NVEYAK-00-CHGCCO-CHGCMT
    attributed_flag     -> 1
    attribution_method  -> ruling_applied          (a valid term; this IS a ruling)
    attribution_source_line -> the verbatim website quote and URL

The ruling itself is unchanged and rests on the owner's ladder: parent_uei AND
ultimate_parent_uei both TNM3D4HVCZT5 (Alaska Native Government Services, LLC);
2,053 of 2,080 rows in Anchorage matching the family's stated HQ; and
copperrivermc.com stating verbatim *"Owned by the Native Village of Eyak, the
Copper River Family of Companies are a collection of both current and graduated
Small Business Administration (SBA) 8(a) Certified entities."*

Not the Eyak Corporation (CE-0008V-A3): zero shared UEIs, that family files
from Dulles VA under THE EYAK CORP.
"""
from __future__ import annotations

import csv
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()
PRIME = ROOT / "data" / "clean" / "prime_contracts.csv"

HUB_UID = "CE-0004H-T9"
HUB_HANDLE = "AKNF-NVEYAK-00-CHGCCO-CHGCMT"
HUB_NAME = "Native Village of Eyak"
ANC_UID = "CE-0008V-A3"
METHOD = "ruling_applied"
VOCAB = {"unattributed", "uei_exact", "cage_exact", "parent_uei",
         "ruling_applied"}
MARK = "COPPER RIVER"
LINE = ('copperrivermc.com: "Owned by the Native Village of Eyak, the Copper '
        'River Family of Companies are a collection of both current and '
        'graduated Small Business Administration (SBA) 8(a) Certified '
        'entities"; parent_uei=ultimate_parent_uei=TNM3D4HVCZT5 (Alaska Native '
        'Government Services, LLC, sub-hub); Anchorage AK matches stated HQ')


def rows_of():
    with PRIME.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        return rd.fieldnames, list(rd)


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "report"
    hdr, rows = rows_of()
    tgt = [r for r in rows
           if MARK in (r.get("awardee_name") or "").upper()
           and (r.get("cedar_uid") or "").strip() != ANC_UID]

    if mode == "verify":
        bad = []
        blank_tid = sum(1 for r in tgt if not (r.get("tribe_id") or "").strip())
        unattr = sum(1 for r in tgt if (r.get("attributed_flag") or "") != "1")
        wrong = sum(1 for r in tgt
                    if (r.get("tribe_id") or "").strip() not in ("", HUB_HANDLE))
        # the vocabulary must be intact ACROSS THE WHOLE TABLE, not just here
        offvocab = sum(1 for r in rows
                       if (r.get("attribution_method") or "") not in VOCAB)
        if blank_tid:
            bad.append(f"{blank_tid} target rows have a blank tribe_id")
        if unattr:
            bad.append(f"{unattr} target rows are not attributed_flag=1")
        if wrong:
            bad.append(f"{wrong} target rows carry a foreign tribe_id")
        if offvocab:
            bad.append(f"{offvocab} rows table-wide hold an attribution_method "
                       f"outside the controlled vocabulary")
        for b in bad:
            print("  FAIL " + b)
        print(f"  1113 verify   {'ok' if not bad else 'FAIL'}   "
              f"{len(tgt):,} Copper River rows")
        return 1 if bad else 0

    fixed = seldovia = revocab = 0
    for r in rows:
        m = r.get("attribution_method") or ""
        is_tgt = (MARK in (r.get("awardee_name") or "").upper()
                  and (r.get("cedar_uid") or "").strip() != ANC_UID)
        if is_tgt:
            if (r.get("tribe_id") or "").strip() and \
               (r.get("tribe_id") or "").strip() != HUB_HANDLE:
                seldovia += 1
            r["tribe_id"] = HUB_HANDLE
            r["cedar_uid"] = HUB_UID
            if "canonical_name" in r:
                r["canonical_name"] = HUB_NAME
            if "attributed_flag" in r:
                r["attributed_flag"] = "1"
            r["attribution_method"] = METHOD
            if "attribution_source_line" in r:
                r["attribution_source_line"] = LINE
            fixed += 1
        elif m and m not in VOCAB:
            # prose written by 1111 onto rows it then withdrew
            r["attribution_method"] = "unattributed"
            revocab += 1

    print(f"  1113 finish Copper River   "
          f"{'APPLIED' if mode == 'apply' else 'report only'}")
    print(f"    rows completed on tribe_id/attributed_flag : {fixed:,}")
    print(f"    of which had a foreign tribe_id            : {seldovia}")
    print(f"    non-target rows restored to the vocabulary : {revocab:,}")

    if mode == "apply":
        b = str(PRIME) + f".bak_{TODAY}_pre1113"
        if not Path(b).exists():
            shutil.copy2(PRIME, b)
        with PRIME.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=hdr)
            w.writeheader()
            w.writerows(rows)
        print(f"    rows in/out : {len(rows):,} / {len(rows):,}")
    else:
        print("\n  nothing written. re-run with `apply`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
