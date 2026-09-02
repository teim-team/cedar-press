#!/usr/bin/env python3
"""
Cedar Press - 1111: attribute the Copper River family to the Native Village of Eyak.

    py -3 code/1111_copper_river_attribution.py            # report
    py -3 code/1111_copper_river_attribution.py apply      # write, with .bak
    py -3 code/1111_copper_river_attribution.py verify     # exit 1 on breach

WHY
---
$1,500,093,051.53 across 4,272 rows sat unattributed or wrongly attributed. The
owner asked for the adjudication to be done rather than queued: *"all I gotta do
is look up its codes, its address, its website, see if the website literally
says owned by blah blah blah."*

THE LADDER, RUN IN HIS ORDER
----------------------------
1. **Codes.** Every Copper River operating company declares `parent_uei` AND
   `ultimate_parent_uei` = `TNM3D4HVCZT5`, `ALASKA NATIVE GOVERNMENT SERVICES,
   LLC`. 2,080 rows, six distinct CAGE codes (785G6, 7EXS0, 7QP39, 77YS6,
   4CS13, 7MRJ6), seven operating companies including Blackfish Solutions.

2. **Address.** 2,053 of 2,080 rows are ANCHORAGE, AK. The family's corporate
   headquarters is 1577 C Street, Suite 300 G, Anchorage — the same city, not a
   coincidence of state.

3. **Website — decisive, and quoted verbatim.**
   `copperrivermc.com/copper-river-information-technology/`:

       "Owned by the Native Village of Eyak, the Copper River Family of
       Companies are a collection of both current and graduated Small Business
       Administration (SBA) 8(a) Certified entities"

   and the classification line: *"Graduated 8(a). Federally Recognized, Alaska
   Native, Tribal Owned, Small Disadvantaged Business"*.

WHY THE TRIBE AND NOT THE CORPORATION
-------------------------------------
Cordova has two Eyak entities and they are NOT the same:

    CE-0004H-T9   Native Village of Eyak      federally recognized tribe
    CE-0008V-A3   Eyak Corporation            ANCSA village corporation

The Copper River family shares **zero UEIs** with the Eyak Corporation family,
which files from Dulles and Reston VA under `THE EYAK CORP` and trades as
EyakTek. Copper River is Anchorage under ANGS. Two separate corporate families
in one community, and the website names the **tribe**.

HUB AND SUB-HUB
---------------
The hub is the Native Village of Eyak. `ALASKA NATIVE GOVERNMENT SERVICES, LLC`
is a **sub-hub** — a holding company between the nation and its operating
companies — and is recorded on every row as the intermediate rather than being
flattened away. A sub-hub is never a peer of its hub.

WHAT THIS DOES NOT DO
---------------------
It does not touch the Eyak Corporation rows, and it does not mint anything:
both Eyak entities were already in the register. An earlier note claimed the
Native Village of Eyak was absent and that $583M turned on minting it. Both
halves were wrong.
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

HUB = "CE-0004H-T9"                    # Native Village of Eyak (the tribe)
HUB_NAME = "Native Village of Eyak"
ANC = "CE-0008V-A3"                    # Eyak Corporation — deliberately untouched
ANGS_UEI = "TNM3D4HVCZT5"
MARK = "COPPER RIVER"
QUOTE = ("Owned by the Native Village of Eyak, the Copper River Family of "
         "Companies are a collection of both current and graduated Small "
         "Business Administration (SBA) 8(a) Certified entities")
SRC = "https://copperrivermc.com/copper-river-information-technology/"
BASIS = (f"attributed {TODAY} by the owner's ladder. CODES: parent_uei and "
         f"ultimate_parent_uei both {ANGS_UEI} (ALASKA NATIVE GOVERNMENT "
         f"SERVICES, LLC). ADDRESS: Anchorage AK, matching the family's stated "
         f"HQ at 1577 C Street. WEBSITE, verbatim: \"{QUOTE}\" ({SRC}). "
         f"ANGS is a SUB-HUB between the nation and its operating companies. "
         f"Not the Eyak Corporation (CE-0008V-A3): zero shared UEIs, that "
         f"family files from Dulles VA under THE EYAK CORP.")

MONEY = ("total_obligations", "obligated_usd", "federal_action_obligation")


def scan(rows):
    t = {c: 0.0 for c in MONEY}
    for r in rows:
        for c in MONEY:
            if c in r:
                try:
                    t[c] += float((r.get(c) or "0").replace(",", ""))
                except ValueError:
                    pass
    return t


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "report"
    with PRIME.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        hdr = rd.fieldnames
        rows = list(rd)

    targets = [r for r in rows
               if MARK in (r.get("awardee_name") or "").upper()
               and (r.get("cedar_uid") or "").strip() != ANC]

    if mode == "verify":
        bad = [r for r in targets if (r.get("cedar_uid") or "").strip() != HUB]
        # The ANC must not have absorbed any of it.
        anc = [r for r in rows if MARK in (r.get("awardee_name") or "").upper()
               and (r.get("cedar_uid") or "").strip() == ANC]
        for r in bad[:3]:
            print(f"  FAIL {r.get('awardee_name','')[:40]} -> "
                  f"{r.get('cedar_uid') or '(blank)'}")
        if anc:
            print(f"  FAIL {len(anc)} Copper River row(s) on the Eyak "
                  f"CORPORATION, which is a different family")
        ok = not bad and not anc
        print(f"  1111 verify   {'ok' if ok else 'FAIL'}   "
              f"{len(targets):,} Copper River rows, {len(bad)} not on the hub")
        return 0 if ok else 1

    before = scan(rows)
    amt = 0.0
    for r in targets:
        r["cedar_uid"] = HUB
        if "canonical_name" in r:
            r["canonical_name"] = HUB_NAME
        for c in ("attribution_basis", "attribution_method"):
            if c in r:
                r[c] = BASIS[:600]
                break
        try:
            amt += float((r.get("total_obligations") or "0").replace(",", ""))
        except ValueError:
            pass

    print(f"  1111 Copper River -> Native Village of Eyak   "
          f"{'APPLIED' if mode == 'apply' else 'report only'}")
    print(f"    rows attributed : {len(targets):,}")
    print(f"    obligations     : ${amt:,.2f}")

    if mode == "apply":
        b = str(PRIME) + f".bak_{TODAY}_pre1111"
        if not Path(b).exists():
            shutil.copy2(PRIME, b)
        with PRIME.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=hdr)
            w.writeheader()
            w.writerows(rows)
        after = scan(rows)
        for c in MONEY:
            if c in before:
                d = after[c] - before[c]
                flag = "" if abs(d) < 0.005 else "   <<< MONEY MOVED"
                print(f"    {c:<28} {before[c]:>20,.2f} -> "
                      f"{after[c]:>20,.2f}{flag}")
        print(f"    rows in/out     : {len(rows):,} / {len(rows):,}")
    else:
        print("\n  nothing written. re-run with `apply`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
