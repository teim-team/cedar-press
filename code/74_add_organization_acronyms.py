#!/usr/bin/env python3
"""
Cedar Press - 74: Give organisations their acronyms as aliases.

ELIJAH, 2026-08-06
------------------
"you also need to add known abbreviations to orgs like NCAI and national
 congress of american indians"

Intertribal organisations, NHOs and consortia are referred to by acronym far
more often than by legal name - in lobbying filings, in press, in grant
records. `NCAI` appears where `National Congress of American Indians` does not,
so a matcher keyed only on the legal name misses the row entirely.

This is the same defect the ANC acronyms had: `BSNC REGIONAL SERVICES` was
proposed as Arctic Slope because no spine entity carried "BSNC".

HOW AN ACRONYM IS ACCEPTED
--------------------------
Derived from the initials of the significant words, then subjected to three
guards. All three exist because a bad acronym is worse than a missing one - it
matches confidently and wrongly.

  1. LENGTH. Two letters is not an identifier. `AI` would match anything.
  2. COLLISION. If the acronym is already a name, an alias, or the acronym of
     any OTHER spine entity, it is refused. `NIC` derived twice is `NIC`
     matching nothing safely.
  3. COMMON WORD. An acronym that spells an ordinary English word or a known
     trap token is refused - `ACT`, `AIM`, `CARE`, `EAGLE`, `RIVER`. A firm
     called "Eagle Systems" must not resolve to an organisation whose initials
     happen to be EAGLE.

Everything refused is written out with its reason, so the refusals are
reviewable rather than invisible.
"""

import csv
import re
import shutil
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
SPINE_P = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

# Classes that are referred to by acronym. A tribe is not - nobody writes
# "CTUIR" expecting it to be unambiguous in a dataset of 952 entities, and
# tribal names carry their own identity.
ACRONYM_CLASSES = {
    "Intertribal Organization",
    "Federal-level self-governance consortium",
    "Native Hawaiian Organization",
    "Tribal College or University",
    "Native Community Development Financial Institution",
}

# Words that carry no initial. "of", "the", "and" are obvious; "inc" and
# "incorporated" are corporate furniture.
SKIP = {"of", "the", "and", "for", "in", "on", "at", "a", "an", "to",
        "inc", "incorporated", "corp", "corporation", "llc", "ltd", "limited",
        "company", "co"}

# An acronym that spells one of these is refused. Ordinary words and the
# project's standing trap tokens.
COMMON = {
    "act", "aim", "care", "cat", "cap", "can", "art", "arm", "ash", "aid",
    "all", "and", "ant", "ape", "arc", "are", "ban", "bar", "bat", "bay",
    "cab", "car", "cot", "cow", "cup", "cut", "dam", "day", "den", "dig",
    "eagle", "river", "mountain", "creek", "central", "santa", "oneida",
    "ice", "ink", "inn", "ion", "its", "jam", "jar", "job", "joy", "key",
    "lab", "law", "leg", "lip", "log", "lot", "low", "man", "map", "mat",
    "net", "new", "nit", "nod", "nor", "not", "now", "nut", "oak", "oil",
    "one", "our", "out", "own", "pan", "pat", "paw", "pay", "pen", "pet",
    "pit", "pot", "put", "ram", "rat", "raw", "ray", "red", "rib", "rid",
    "rim", "rip", "rob", "rod", "rot", "row", "rub", "rug", "run", "sat",
    "saw", "say", "sea", "set", "she", "shy", "sir", "sit", "six", "ski",
    "sky", "son", "sow", "spa", "spy", "sum", "sun", "tab", "tag", "tan",
    "tap", "tar", "tax", "tea", "ten", "tie", "tin", "tip", "toe", "ton",
    "top", "tow", "toy", "try", "tub", "tug", "two", "use", "van", "vat",
    "via", "vow", "war", "was", "wax", "way", "web", "wet", "who", "why",
    "wig", "win", "wit", "won", "yes", "yet", "you", "zip", "zoo",
}


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def acronym(name):
    """Initials of the significant words."""
    # Strip apostrophes and okina BEFORE taking initials. Keeping them made
    # "Ke Kumu 'Ulu" produce "KK'" and "Na 'Oiwi Kane" produce "N'K" - an
    # acronym with punctuation in it matches nothing and looks like a defect.
    cleaned = re.sub(r"[ʻʼ‘’'`´]", "", name)
    words = [w for w in re.split(r"[^A-Za-z]+", cleaned)
             if w and w.lower() not in SKIP]
    if len(words) < 2:
        return ""
    return "".join(w[0].upper() for w in words)


def main():
    print("=== Cedar Press 74: organisation acronyms ===\n")
    with open(SPINE_P, encoding="utf-8-sig", newline="") as fh:
        spine = list(csv.DictReader(fh))
    fields = list(spine[0].keys())

    # Everything already claimed, so a new acronym cannot collide with it.
    claimed = defaultdict(set)
    for r in spine:
        claimed[norm(r["canonical_name"])].add(r["tribe_id"])
        for a in (r.get("aliases") or "").split("|"):
            if a.strip():
                claimed[norm(a)].add(r["tribe_id"])

    proposed = defaultdict(set)
    for r in spine:
        if r.get("entity_class") not in ACRONYM_CLASSES:
            continue
        ac = acronym(r["canonical_name"])
        if ac:
            proposed[norm(ac)].add(r["tribe_id"])

    added, refused = 0, []
    by_id = {r["tribe_id"]: r for r in spine}

    for r in spine:
        if r.get("entity_class") not in ACRONYM_CLASSES:
            continue
        ac = acronym(r["canonical_name"])
        n = norm(ac)
        if not ac:
            continue
        if len(ac) < 3:
            refused.append((r["canonical_name"], ac, "under three letters"))
            continue
        if n in COMMON:
            refused.append((r["canonical_name"], ac, "spells a common word or trap token"))
            continue
        owners = claimed.get(n, set())
        if owners and owners != {r["tribe_id"]}:
            refused.append((r["canonical_name"], ac,
                            f"already names {by_id[list(owners)[0]]['canonical_name'][:34]}"))
            continue
        if len(proposed.get(n, set())) > 1:
            refused.append((r["canonical_name"], ac,
                            f"{len(proposed[n])} entities derive the same acronym"))
            continue

        al = [a.strip() for a in (r.get("aliases") or "").split("|") if a.strip()]
        if n not in {norm(a) for a in al}:
            al.append(ac)
            r["aliases"] = "|".join(al)
            claimed[n].add(r["tribe_id"])
            added += 1
            if added <= 18:
                print(f"  + {ac:9s} -> {r['canonical_name'][:52]}")

    shutil.copy2(SPINE_P, SPINE_P.with_suffix(f".csv.bak_{TODAY}_pre74"))
    with open(SPINE_P, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(spine)

    print(f"\n  acronyms added : {added}")
    print(f"  refused        : {len(refused)}")
    if refused:
        p = REVIEW / "acronym_refusals.csv"
        with open(p, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["canonical_name", "acronym", "refused_because", "date"])
            for a, b, c in refused:
                w.writerow([a, b, c, TODAY])
        print(f"  wrote {p.relative_to(CEDAR)}")
        for a, b, c in refused[:8]:
            print(f"     {b:9s} {c[:46]:46s} {a[:34]}")
    print(f"\n  wrote {SPINE_P.relative_to(CEDAR)}")


if __name__ == "__main__":
    main()
