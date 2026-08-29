#!/usr/bin/env python3
"""
Cedar Press - 20: Correct two defects in the nonprofit layer.

DEFECT 1 - authority inflation.
`nonprofit_exclusion_rulings.csv` holds 4,656 rows presented as "exclusion
rulings". They are NOT rulings in the sense the rest of Cedar Press uses that
word. The 123 per-UEI drops in hci_analysis.do are hand rulings, each with a
cage.dla.mil / GAO / OpenCorporates citation. These 4,656 fired from regex
filters. Same filename convention, very different authority - and a future
maintainer would reasonably treat them as equivalent.

Fix: stamp `authority_class` on every row.
  hand_ruling      - a person ruled it, with evidence
  automated_filter - a rule fired; reversible, lower authority

DEFECT 2 - a known-wrong exclusion.
EIN 850303705 NAVAJO TECHNICAL COLLEGE is excluded, but sits in the ledger as
TRIBAL_COLLEGE. A tribal college is exactly the kind of institution this
dataset exists to capture. Reinstated with a note; the original ruling is kept
for audit rather than deleted.

Also flags tier-A rows whose names read as place-names, because the tier-A
revenue aggregate leaks organizations like Umatilla Electric Cooperative and
Yavapai Community Hospital that are named for places rather than owned by
tribes.

Outputs (in place, with backups)
-------
data/spine/nonprofit_exclusion_rulings.csv   + authority_class, + reinstated
data/clean/np_orgs.csv                       + placename_risk_flag
review/np_placename_risk_<date>.csv          tier-A rows to rule on
"""

import csv
import re
import shutil
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
SPINE = CEDAR / "data" / "spine"
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

REINSTATE = {
    "850303705": ("NAVAJO TECHNICAL COLLEGE",
                  "Tribal college. Present in the ledger as TRIBAL_COLLEGE. The "
                  "exclusion is the error, not the ledger entry."),
}

# Tokens that are simultaneously tribe names and US place names. An org whose
# Native-ness rests only on one of these needs a human look.
PLACE_TOKENS = re.compile(
    r"\b(cherokee|seneca|cayuga|mohawk|chippewa|ottawa|miami|peoria|wyandotte|"
    r"pontiac|shawnee|sioux|yavapai|umatilla|klamath|modoc|ponca|kiowa|comanche|"
    r"osage|caddo|natchez|tuscarora|oneida|onondaga|huron|erie|illini|kickapoo|"
    r"winnebago|menominee|houma|santee|catawba|lumbee|pamunkey|nottoway)\b",
    re.IGNORECASE)

# Corporate forms that are almost never tribally controlled instrumentalities.
NON_TRIBAL_FORM = re.compile(
    r"\b(cooperative|co-?op|electric|telephone|community hospital|county|"
    r"chamber of commerce|school district|rotary|kiwanis|lions club|"
    r"united way|habitat for humanity|little league)\b", re.IGNORECASE)


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
    print("=== Cedar Press: nonprofit layer corrections ===\n")

    # ---- DEFECT 1 + 2 -----------------------------------------------------
    src = SPINE / "nonprofit_exclusion_rulings.csv"
    rows = read_csv(src)
    if not rows:
        print(f"  MISSING: {src}")
        return
    shutil.copy2(src, src.with_suffix(".bak_" + TODAY))

    reinstated = 0
    for r in rows:
        r["authority_class"] = "automated_filter"
        r["authority_note"] = ("Fired from a regex/rule filter, not a hand ruling. "
                               "Reversible. Lower authority than the per-UEI drops in "
                               "hci_analysis.do, which carry citations.")
        ein = (r.get("ein") or "").strip()
        if ein in REINSTATE:
            name, why = REINSTATE[ein]
            r["reinstated"] = "YES"
            r["reinstated_date"] = TODAY
            r["reinstated_reason"] = why
            reinstated += 1
        else:
            r.setdefault("reinstated", "")
            r.setdefault("reinstated_date", "")
            r.setdefault("reinstated_reason", "")

    fields = list(rows[0].keys())
    for extra in ("authority_class", "authority_note", "reinstated",
                  "reinstated_date", "reinstated_reason"):
        if extra not in fields:
            fields.append(extra)
    write_csv(src, rows, fields)
    print(f"  stamped authority_class on {len(rows):,} rows (all automated_filter)")
    print(f"  reinstated {reinstated} known-wrong exclusion(s)")

    # ---- DEFECT 3: place-name risk in tier A ------------------------------
    orgs = read_csv(CLEAN / "np_orgs.csv")
    if not orgs:
        print("\n  np_orgs.csv missing - skipping place-name pass")
        return
    shutil.copy2(CLEAN / "np_orgs.csv",
                 CLEAN / ("np_orgs.csv.bak_" + TODAY))

    namecol = "org_name" if "org_name" in orgs[0] else list(orgs[0])[1]
    tiercol = "confidence_tier" if "confidence_tier" in orgs[0] else None
    # np_orgs uses uppercase EIN. Resolve case-insensitively rather than
    # guessing - a blank identifier silently produced unusable review rows
    # (review_id came through as "EIN:" with nothing after it).
    eincol = next((c for c in orgs[0] if c.lower() == "ein"), None)
    if not eincol:
        raise SystemExit("np_orgs.csv has no EIN column - cannot build review rows")

    risky = []
    for r in orgs:
        name = r.get(namecol, "")
        place = bool(PLACE_TOKENS.search(name))
        form = bool(NON_TRIBAL_FORM.search(name))
        if form:
            r["placename_risk_flag"] = "HIGH"
        elif place:
            r["placename_risk_flag"] = "REVIEW"
        else:
            r["placename_risk_flag"] = ""
        if r["placename_risk_flag"] and tiercol and r.get(tiercol) == "A":
            risky.append({
                "ein": r.get(eincol, ""),
                "org_name": name,
                "risk": r["placename_risk_flag"],
                "state": r.get("state", ""),
                "question": (f"Is '{name}' a Native-controlled organization, or an "
                             f"organization merely named for a place?"),
                "YOUR_RULING": "",
            })

    ofields = list(orgs[0].keys())
    if "placename_risk_flag" not in ofields:
        ofields.append("placename_risk_flag")
    write_csv(CLEAN / "np_orgs.csv", orgs, ofields)

    if risky:
        risky.sort(key=lambda x: (x["risk"] != "HIGH", x["org_name"]))
        write_csv(REVIEW / f"np_placename_risk_{TODAY}.csv", risky,
                  ["ein", "org_name", "risk", "state", "question", "YOUR_RULING"])

    counts = Counter(r["placename_risk_flag"] for r in orgs if r["placename_risk_flag"])
    print(f"\n  place-name risk flagged: {dict(counts)}")
    print(f"  tier-A rows needing a ruling: {len(risky):,}")
    print("\n  Until these are ruled, the tier-A revenue aggregate is not quotable.")


if __name__ == "__main__":
    main()
