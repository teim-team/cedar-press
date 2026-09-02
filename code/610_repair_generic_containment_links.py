#!/usr/bin/env python3
"""
Cedar Press - 610: A GENERIC NAME CANNOT WIN A CONTAINMENT MATCH.

    py -3 code/610_repair_generic_containment_links.py            # report
    py -3 code/610_repair_generic_containment_links.py --apply    # flag them
    py -3 code/610_repair_generic_containment_links.py verify     # exit 1 if any live

WHY
---
Shard F, 2026-09-01, found $486.8M of the wrong money on one Phoenix clinic.
Verified before this was written:

  Council        <- COUNCIL OF JEWISH ORGANIZATIONS OF CROWN HEIGHTS
  Council        <- COUNCIL OF INDIAN ORGANIZATIONS IN GREATER PHILADELPHIA
  Council        <- COUNCIL FOR WEST INDIAN PLANNING & DEVELOPMENT
  Council        <- COUNCIL FOR TRIBAL EMPLOYMENT RIGHTS
  Council        <- COUNCIL FOR AMERICAN INDIAN MINISTRY
  Native Health  <- WINSLOW INDIAN HEALTH CARE CENTER INC
  Native Health  <- THE FORT DEFIANCE INDIAN HOSPITAL BOARD INCORPORATED
  Native Health  <- 043651340, 208069371

`Council` is a REAL entity - Council, Alaska, a federally recognized Alaska
Native Village in the Bering Straits region, `AKNF-COUNCL-00-BERSTR-KAWRAK`.
A Crown Heights Jewish organisation is keyed to it because both names contain
the word "Council". `Native Health` is a real Phoenix urban Indian clinic
(`UIO-HEALTH-00`); Winslow Indian Health Care Center is separately
`CE-001GJ-0B`, so its dollars were reachable twice.

WHY A DENYLIST IS NOT THE FIX
-----------------------------
`cedar_domain.NAME_TRAPS` already holds 51 words - `modoc`, `oneida`,
`colorado`, `advantage` - and did not hold `council`, `health` or `native`.
That is the shape shard J named this morning: a denylist only refuses a word
somebody already listed. It catches FOND DU LAC YACHT CLUB and never ENVISION
GREATER FOND DU LAC.

State agreement is not the fix either, and this pair proves it. It would kill
all five Council links (Philadelphia, Brooklyn - not Alaska) and NONE of the
Native Health ones: Winslow and Fort Defiance are both in Arizona, and so is
Native Health.

So the rule is structural, and it is the same one added to `503_identity.py`
today for single-token brand aliases:

    AN ENTITY WHOSE ENTIRE DISTINCTIVE TOKEN SET IS GENERIC MAY NOT WIN A
    MATCH THAT RESTS ONLY ON CONTAINMENT.

Containment says "the entity's name appears inside the organisation's name."
For a name made only of words like COUNCIL, HEALTH, NATIVE or CENTER that is
satisfied by thousands of organisations and is evidence of nothing. It is the
same defect `266_apply_gaming_hub_spillover_rulings.py` calls "the textbook
case", and the same one `167` already refuses for NEW links - these nine are
legacy rows from an earlier pass that 167 carries forward.

WHAT THIS DOES NOT DO
---------------------
It does not delete. House rule is flag, never delete: the rows stay, marked,
so the refusal is auditable and reversible. It does not touch the genuine
`Native Health` link (EIN 942540194), which carries no `link_method` at all
and therefore never rested on containment - which is exactly why the rule is
written against the method rather than against the entity.
"""
from __future__ import annotations

import csv
import re
import shutil
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()
HUB = ROOT / "data" / "clean" / "np_ein_entity_hub.csv"

# Words that carry no identifying power on their own. A spine name built ONLY
# from these cannot support a containment match. Deliberately short: this is a
# floor on genericness, not an attempt to enumerate every weak word - the rule
# is "all tokens generic", so adding a word only ever makes it stricter.
GENERIC = {
    "NATIVE", "NATIVES", "AMERICAN", "AMERICANS", "INDIAN", "INDIANS",
    "INDIGENOUS", "ABORIGINAL", "TRIBAL", "TRIBE", "TRIBES", "NATION",
    "NATIONS", "BAND", "PEOPLE", "PEOPLES", "FIRST",
    "HEALTH", "HEALTHCARE", "MEDICAL", "CLINIC", "HOSPITAL", "WELLNESS",
    "COUNCIL", "COUNCILS", "COMMITTEE", "BOARD", "COMMISSION", "AUTHORITY",
    "ASSOCIATION", "ALLIANCE", "COALITION", "CONSORTIUM", "SOCIETY",
    "FOUNDATION", "INSTITUTE", "CENTER", "CENTRE", "SERVICES", "SERVICE",
    "PROGRAM", "PROGRAMS", "PROJECT", "COMMUNITY", "COMMUNITIES",
    "DEVELOPMENT", "ENTERPRISE", "ENTERPRISES", "CORPORATION", "COMPANY",
    "GROUP", "HOLDINGS", "PARTNERS", "SYSTEMS", "SOLUTIONS",
    "THE", "OF", "AND", "FOR", "A", "AN", "INC", "LLC", "LTD", "CO",
}

# Match methods that rest on one name being a substring of another.
CONTAINMENT_METHODS = {"containment", "contain", "official_name_containment"}

FLAG_COL = "generic_containment_refusal"


def toks(s: str) -> set:
    return {t for t in re.sub(r"[^A-Za-z ]", " ", s or "").upper().split() if t}


def offenders(rows: list) -> list:
    out = []
    for r in rows:
        m = (r.get("link_method") or "").strip().lower()
        if m not in CONTAINMENT_METHODS:
            continue
        t = toks(r.get("entity_canonical_name") or "")
        if t and t <= GENERIC:
            out.append(r)
    return out


def main() -> int:
    apply = "--apply" in sys.argv
    verify = "verify" in sys.argv

    with HUB.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        cols = list(rd.fieldnames or [])
        rows = list(rd)

    bad = offenders(rows)
    live = [r for r in bad if not (r.get(FLAG_COL) or "").strip()]

    by_entity = Counter((r.get("entity_canonical_name") or "") for r in bad)
    print(f"  610 generic-containment  hub rows {len(rows):,}   "
          f"offending links {len(bad)}   unflagged {len(live)}")
    for nm, n in by_entity.most_common():
        print(f"    {nm:<24} {n} link(s)")
        for r in bad:
            if (r.get("entity_canonical_name") or "") == nm:
                print(f"        EIN {r.get('ein'):<11} "
                      f"{(r.get('org_name') or '(name not in np_orgs)')[:54]}")

    if verify:
        return 1 if live else 0
    if not apply or not live:
        if not apply:
            print("    (report only - pass --apply to flag)")
        return 0

    shutil.copy2(HUB, HUB.with_name(HUB.name + f".bak_{TODAY}_pre610"))
    if FLAG_COL not in cols:
        cols.append(FLAG_COL)
    for r in live:
        r[FLAG_COL] = (
            "REFUSED_GENERIC_CONTAINMENT: the spine entity's whole name is "
            "generic tokens, so containment is satisfied by thousands of "
            "organisations and is evidence of nothing. Flagged not deleted; "
            f"see code/610 and docs/ENTITY_MATCH_RULES.md. {TODAY}")
    with HUB.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"    FLAGGED {len(live)} link(s); backup written, no row deleted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
