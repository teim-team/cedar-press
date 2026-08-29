#!/usr/bin/env python3
"""
Cedar Press - 69: Give the spine the FULL official names from 91 FR 4102.

ELIJAH, 2026-08-06 - the diagnosis was his, in four notes
--------------------------------------------------------
    Asa'carsarmiut  -> "Asa'carsarmiut Tribe"
    Orutsararmiut   -> "Orutsararmiut Traditional Native Council"
    Pitka's Point   -> "Pitka's Point Traditional Council"
    Sleetmute       -> "Village of Sleetmute"
                       "alaska native tribes have more unique names"

The spine stores SHORT names. Federal systems - SAM, FPDS, USAspending, IRS -
carry the full official one. So an entity named "Sleetmute" in our spine is
being matched against "Village of Sleetmute" in every dataset and failing, and
we recorded that as "no federal activity" when it is a name-length problem.

That is why 273 entities look unreconciled. Most are not missing; they are
mis-keyed.

THE PARENTHESES CASES ELIJAH KEPT NAMING
----------------------------------------
The FR notice uses parentheses for three genuinely different things, and they
must not be treated alike:

  (previously listed as X)   a RENAME. X is an alias of the same entity.
      Mi'kmaq Nation (previously listed as Aroostook Band of Micmacs)

  (See Y)                    a CROSS-REFERENCE. This name is not its own
      entity; Y is. "Arctic Village (See Native Village of Venetie Tribal
      Government)" means Arctic Village files under Venetie.

  (A; B)                     CONSTITUENT parts listed under one parent.
      Capitan Grande Band of Diegueno Mission Indians of California
        (Barona Group ...; Viejas (Baron Long) Group ...)
      Pribilof Islands Aleut Communities of St. Paul & St. George Islands
        (St. George Island and Saint Paul Island)

Collapsing a cross-reference into an alias would merge two entities. Collapsing
constituents would erase the sub-tribe layer Elijah asked for.

PARSING
-------
The raw FR text wraps lines, and a wrapped line ends with a trailing space
while a complete entry does not. That is the whole rule.

Reads  data/raw/external/fr_recognized/2026-01899_raw.txt
       data/spine/cedar_entity_spine.csv
Writes data/spine/cedar_entity_spine.csv        (aliases enriched)
       data/clean/fr_recognized_entities.csv    (the parsed roster)
       review/fr_unmatched_entries.csv          (FR entries with no spine row)
"""

import csv
import importlib.util
import re
import shutil
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
SPINE_P = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"
FR_TXT = CEDAR / "data" / "raw" / "external" / "fr_recognized" / "2026-01899_raw.txt"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

PREV_RE = re.compile(r"\(previously listed as\s+(?P<prev>[^)]+)\)", re.I)
SEE_RE = re.compile(r"\(\s*See\s+(?P<target>[^)]+)\)", re.I)


def load_m33():
    spec = importlib.util.spec_from_file_location(
        "m33", CEDAR / "code" / "33_apply_party_rulings.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def read_csv(p):
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def parse_fr():
    """Rejoin wrapped lines. A wrapped line ends with a space; an entry does not."""
    t = FR_TXT.read_text(encoding="utf-8", errors="replace")
    i = t.find("Alabama-Coushatta")
    if i < 0:
        raise SystemExit("could not find the start of the FR list")
    seg = t[i:]
    # Stop at the signature block if present.
    for end in ("\nDated:", "\nBILLING CODE", "\n[FR Doc"):
        j = seg.find(end)
        if j > 0:
            seg = seg[:j]
    out, buf = [], ""
    for raw in seg.split("\n"):
        if not raw.strip():
            continue
        buf += raw if raw.endswith(" ") else raw
        if raw.endswith(" "):
            continue
        out.append(re.sub(r"\s+", " ", buf).strip())
        buf = ""
    if buf.strip():
        out.append(re.sub(r"\s+", " ", buf).strip())
    return [o for o in out if len(o) > 3 and o[0].isupper()]


def main():
    print("=== Cedar Press 69: enrich spine from 91 FR 4102 ===\n")
    m = load_m33()
    entries = parse_fr()
    print(f"FR entries parsed: {len(entries)}")

    roster, kinds = [], Counter()
    for e in entries:
        prev = PREV_RE.search(e)
        see = SEE_RE.search(e)
        base = PREV_RE.sub("", e)
        base = SEE_RE.sub("", base).strip().rstrip(",").strip()
        kind = ("cross_reference" if see else
                "rename" if prev else "entity")
        kinds[kind] += 1
        roster.append({
            "fr_name": base,
            "kind": kind,
            "previously_listed_as": prev.group("prev").strip() if prev else "",
            "see_instead": see.group("target").strip() if see else "",
            "raw_entry": e,
            "citation": "91 FR 4102 (2026-01-30)",
            "parsed": TODAY,
        })
    print(f"  entities        : {kinds['entity']}")
    print(f"  renames         : {kinds['rename']}   (alias of the same entity)")
    print(f"  cross-references: {kinds['cross_reference']}   "
          f"(a DIFFERENT entity - never merged)")

    with open(CLEAN / "fr_recognized_entities.csv", "w", encoding="utf-8",
              newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(roster[0].keys()))
        w.writeheader()
        w.writerows(roster)
    print(f"\n  wrote data/clean/fr_recognized_entities.csv ({len(roster)} rows)")

    # ---- match each FR entry to a spine row and lengthen its aliases ------
    spine = read_csv(SPINE_P)
    shutil.copy2(SPINE_P, SPINE_P.with_suffix(f".csv.bak_{TODAY}_pre69"))
    by_id = {r["tribe_id"]: r for r in spine}

    added, matched, unmatched = 0, 0, []
    for r in roster:
        if r["kind"] == "cross_reference":
            # "Arctic Village (See Native Village of Venetie)" - the entry is a
            # pointer, not an entity. Recorded in the roster, never merged.
            continue
        tid, canon, how = m.resolve_entity(r["fr_name"], spine)
        if not tid:
            unmatched.append({"fr_name": r["fr_name"], "reason": how,
                              "raw_entry": r["raw_entry"][:160]})
            continue
        matched += 1
        row = by_id[tid]
        al = [a.strip() for a in (row.get("aliases") or "").split("|") if a.strip()]
        low = {m.norm(a) for a in al}
        for name in (r["fr_name"], r["previously_listed_as"]):
            if name and m.norm(name) not in low:
                al.append(name)
                low.add(m.norm(name))
                added += 1
        row["aliases"] = "|".join(al)
        # The FULL official name is what federal systems carry. Record it so a
        # matcher can prefer it without overwriting the short canonical name
        # everything else already keys on.
        if "fr_official_name" not in row or not row.get("fr_official_name"):
            row["fr_official_name"] = r["fr_name"]

    fields = list(spine[0].keys())
    if "fr_official_name" not in fields:
        fields.append("fr_official_name")
    for row in spine:
        row.setdefault("fr_official_name", "")

    with open(SPINE_P, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(spine)

    print(f"\n  FR entries matched to a spine row : {matched}")
    print(f"  aliases added                     : {added}")
    print(f"  FR entries with NO spine row      : {len(unmatched)}")
    if unmatched:
        p = REVIEW / "fr_unmatched_entries.csv"
        with open(p, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(unmatched[0].keys()))
            w.writeheader()
            w.writerows(unmatched)
        print(f"  wrote {p.relative_to(CEDAR)}")
        for u in unmatched[:8]:
            print(f"     {u['fr_name'][:56]:56s} {u['reason'][:26]}")

    # Did it fix the cases Elijah named?
    print("\ncases Elijah named:")
    for probe in ["Sleetmute", "Asa'carsarmiut", "Orutsararmiut", "Pitka's Point"]:
        hit = next((r for r in spine
                    if m.norm(probe) in m.norm(r["canonical_name"] + " " +
                                               (r.get("aliases") or ""))), None)
        if hit:
            print(f"  {probe:18s} -> official: "
                  f"{hit.get('fr_official_name') or '(none found)'}")


if __name__ == "__main__":
    main()
