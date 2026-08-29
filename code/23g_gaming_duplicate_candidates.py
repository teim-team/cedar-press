#!/usr/bin/env python3
"""Cedar Press 23g - candidate duplicate facility rows in gaming_facilities.csv.

WHY THIS EXISTS
---------------
`gaming_facilities.csv` reports 774 rows and, before this pass, 56 of them were
undated with reason "no source located". That looked like a research gap. It is
substantially something else: **49 of those 56 carry `duplicate_risk = 1`** -
they are `votingpatterns_only_no_exact_casino_city_match` rows - and 43 of the
49 sit in the same city as an ALREADY-DATED row for what is very likely the same
property.

The 2026-08-06 research sweep proved it empirically rather than by assertion.
Researching the undated `VP-` rows from scratch returned dates that the file
already held on a `CCP-` twin:

    VP-0185 Kiowa Casino Red River  researched -> 2007-05-23
    CCP-773800 Kiowa Casino & Hotel  already held  2007-05-23   IDENTICAL

    VP-0134 Cherokee Casino West Siloam Springs  researched -> 1994
    CCP-408300 Cherokee Casino & Hotel West Siloam Springs  held 1994-12-31

    VP-0170 7 Clans First Council Casino  researched -> 2008-03 (month)
    CCP-843900 7 Clans First Council Casino Hotel  held 2008-02-29

Two independent routes to the same date for two rows is duplication, not
coincidence. So the honest reading of the undated count is that some of it is a
DEDUPLICATION problem, and researching it harder produces a second dated row for
one property - which then double-counts in any openings-by-year series. That is
worse than leaving it undated.

WHAT THIS SCRIPT DOES, AND WHAT IT REFUSES TO DO
------------------------------------------------
It emits CANDIDATES for a human ruling. It does NOT merge, delete, re-point or
re-date anything, and it does not write to data/clean/. The project's matching
rules forbid exactly the automated leap that would be tempting here: name
similarity is not identity ("Cherokee Inc." trap), a tribe can run several
casinos in one city, and `Osage Casino Tulsa` vs `River Spirit Casino Resort` in
Tulsa are different properties owned by different nations.

So the output is a review queue in the project's established reconcile format,
with a blank YOUR_RULING column, ordered by how strong the evidence is.

Scoring is deliberately crude and legible - a token-overlap ratio on normalised
names plus exact-city and same-tribe agreement - because a subscriber-facing
merge must be defensible by reading the row, not by trusting a similarity score.

Writes review/gaming_facility_duplicate_candidates_<date>.csv
"""

import csv
import re
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

# Words that carry no identity information for a casino name. Dropping them is
# what lets "Kiowa Casino Red River" reach "Kiowa Casino & Hotel".
STOP = {"casino", "casinos", "hotel", "resort", "gaming", "center", "centre",
        "the", "and", "at", "of", "a", "inc", "llc", "lodge", "spa",
        "conference", "travel", "plaza", "gasino", "bingo", "nation",
        "tribe", "tribal", "indian", "small", "main", "additional"}


def norm_tokens(name):
    toks = re.split(r"[^a-z0-9]+", str(name).lower())
    return {t for t in toks if t and t not in STOP}


PROPERTY_TYPES = ("travel plaza", "travel center", "smoke shop",
                  "trading post", "truck stop", "gaming parlor", "riverboat")


def disagreeing_property_type(a, b):
    """Return a description when exactly one of the two names declares a
    distinct property type. Both declaring it, or neither, is agreement."""
    a, b = str(a).lower(), str(b).lower()
    for t in PROPERTY_TYPES:
        if (t in a) != (t in b):
            return f"one side is a {t}"
    return ""


def load(name):
    with open(CLEAN / name, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def main():
    fac = load("gaming_facilities.csv")
    REVIEW.mkdir(exist_ok=True)

    undated = [r for r in fac
               if r.get("open_date_class") == "absent"
               and "no source located" in (r.get("open_date_absent_reason") or "")]
    dated = [r for r in fac if r.get("open_date_class") in ("exact", "bounded")]

    rows = []
    for u in undated:
        ut = norm_tokens(u["facility_name"])
        ucity = (u.get("city") or "").strip().lower()
        best = []
        for d in dated:
            if (d.get("state") or "") != (u.get("state") or ""):
                continue
            dcity = (d.get("city") or "").strip().lower()
            dt = norm_tokens(d["facility_name"])
            if not ut or not dt:
                continue
            overlap = len(ut & dt)
            if not overlap:
                continue
            score = overlap / max(1, min(len(ut), len(dt)))
            same_city = int(bool(ucity) and ucity == dcity)
            same_tribe = int((u.get("tribe") or "").strip().lower()
                             == (d.get("tribe") or "").strip().lower())
            best.append((score, same_city, same_tribe, d, sorted(ut & dt)))
        if not best:
            rows.append(dict(
                facility_id=u["facility_id"], facility_name=u["facility_name"],
                tribe=u.get("tribe", ""), city=u.get("city", ""),
                state=u.get("state", ""),
                candidate_id="", candidate_name="", candidate_open_date="",
                candidate_open_date_class="",
                name_token_overlap="", shared_tokens="",
                same_city="", same_tribe="", strength="no candidate",
                evidence="No dated row in the same state shares a "
                         "meaningful name token.",
                YOUR_RULING=""))
            continue
        best.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
        for score, same_city, same_tribe, d, shared in best[:3]:
            # PROPERTY-TYPE GUARD. The stop-word list deliberately drops
            # `travel`, `plaza`, `casino` and friends so that
            # "Kiowa Casino Red River" can reach "Kiowa Casino & Hotel". The
            # cost is that it also makes "Choctaw Casino Atoka" look identical
            # to "Choctaw Travel Plaza - Atoka", which are two DIFFERENT
            # properties in one town - and several tribal travel plazas
            # genuinely host gaming, so this is not a distinction the file can
            # afford to blur. Where exactly one side is a travel plaza / smoke
            # shop / trading post, the pair is demoted rather than dropped.
            ptype = disagreeing_property_type(u["facility_name"],
                                              d["facility_name"])
            if ptype:
                strength = (f"weak - property TYPE differs ({ptype}); "
                            "probably distinct properties in one town")
            elif score >= 0.99 and same_city and same_tribe:
                strength = "STRONG - same tribe, same city, name tokens identical"
            elif score >= 0.5 and same_city and same_tribe:
                strength = "likely - same tribe and city, most name tokens shared"
            elif same_city and same_tribe:
                strength = "weak - same tribe and city, names diverge"
            else:
                strength = "weak - review by hand"
            rows.append(dict(
                facility_id=u["facility_id"], facility_name=u["facility_name"],
                tribe=u.get("tribe", ""), city=u.get("city", ""),
                state=u.get("state", ""),
                candidate_id=d["facility_id"],
                candidate_name=d["facility_name"],
                candidate_open_date=d.get("open_date", ""),
                candidate_open_date_class=d.get("open_date_class", ""),
                name_token_overlap=f"{score:.2f}",
                shared_tokens=" ".join(shared),
                same_city=same_city, same_tribe=same_tribe,
                strength=strength,
                evidence="Candidate only. Name similarity is NOT identity and "
                         "one tribe can run several casinos in one city. "
                         "Confirm against a source before merging.",
                YOUR_RULING=""))

    out = REVIEW / f"gaming_facility_duplicate_candidates_{TODAY}.csv"
    fields = list(rows[0].keys())
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    from collections import Counter
    c = Counter(r["strength"].split(" -")[0] for r in rows)
    print(f"undated rows examined : {len(undated)}")
    print(f"candidate pairs written: {len(rows)} -> {out.name}")
    for k, v in c.most_common():
        print(f"   {v:4d}  {k}")
    uniq = len({r['facility_id'] for r in rows
                if r['strength'].startswith(('STRONG', 'likely'))})
    print(f"undated rows with a STRONG or likely twin: {uniq} of {len(undated)}")


if __name__ == "__main__":
    main()
