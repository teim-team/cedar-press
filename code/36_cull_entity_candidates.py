#!/usr/bin/env python3
"""
Cedar Press - 36: Cull the entity-candidate register down to real proposals.

The harvest emitted 3,919 "candidates". Inspection showed roughly 2,700 are not
entity names at all - they are prose fragments the suffix-anchored extractor
pulled out of Federal Register titles:

    "Treatment of Indian Tribes"
    "EPA, States, Territories, Tribes"
    "Delegated and Cooperative Activities With States and Indian Tribes"
    "Federal Acknowledgment of Tribes"

An entity register that contains those is worse than one that omits them,
because it makes the real gaps invisible. This script rejects them by shape,
records WHY each was rejected, and keeps the rejects in a separate file so the
cull is auditable rather than a silent deletion.

Outputs
-------
data/clean/entity_candidates_new.csv        culled - real proposals only
data/clean/entity_candidates_rejected.csv   what was removed, with the reason
"""

import csv
import re
import shutil
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
TODAY = date.today().isoformat()

SRC = CLEAN / "entity_candidates_new.csv"

# Each pattern is a shape that cannot be an entity name, with a stated reason.
REJECT = [
    (re.compile(r"\b(EPA|USDA|HHS|HUD|DOI|BIA|IHS|AmeriCorps|FEMA|NOAA)\b"),
     "names a federal agency, not a Native entity"),
    (re.compile(r"\b(States?|Territories|Federal Agencies)\b.*\bTribes?\b", re.I),
     "enumerates governments in prose ('States, Territories, Tribes')"),
    (re.compile(r"^(Treatment|Delegated|Assisting|Against|Regarding|Concerning|"
                r"Notice|Proposed|Final|Reconsidered|Summary|Extension|Renewal)\b", re.I),
     "begins with a rulemaking verb - a document title, not a name"),
    (re.compile(r"\b(Federal Acknowledgment|Acknowledgment of)\b", re.I),
     "Federal Register proceeding label, not an entity"),
    (re.compile(r"\b(Activities|Consultation|Cooperative Agreements?|Guidelines|"
                r"Regulations?|Provisions?|Requirements?|Amendments?)\b", re.I),
     "rulemaking vocabulary - fragment of a document title"),
    (re.compile(r"\b(Museum|Park|Monument|Historic Site|Trail)\b.*,\s*[A-Z]{2}\b"),
     "a place with a state abbreviation - a location, not an entity"),
    (re.compile(r"\b(and the|with the|of the|for the|between)\s+\w+$", re.I),
     "truncated mid-phrase - the extractor cut a sentence"),
    (re.compile(r"^\W*$"), "no alphanumeric content"),
    (re.compile(r"\b(Company|Corporation|Service|Administration)\s+and\s+the\b", re.I),
     "two parties joined in prose, not one entity"),
]

# A name this short and generic is a fragment, not an entity.
TOO_GENERIC = {
    "iowa tribe", "fox tribe", "mississippi band", "mowa band", "burt lake band",
    "indian tribes", "indian tribe", "the pueblo", "tribes", "tribe", "nation",
    "the tribe", "the nation", "indian nations", "native american tribes",
}


def read_csv(p):
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(p, rows, fields):
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {p.relative_to(CEDAR)}  ({len(rows):,} rows)")


# "Indian" and "tribe" are heavily overloaded English words. These are the
# non-Native senses that flooded the BMF-sourced candidates.
WRONG_SENSE = [
    (re.compile(r"\b(Israel|Judah|Biblical|Scripture|Assembly of God|Church of|"
                r"Ministries|Gospel|Baptist|Methodist)\b", re.I),
     "biblical or church sense of 'tribes', not Native"),
    (re.compile(r"\b(Hindu|Sikh|Bengali|Tamil|Telugu|Gujarati|Punjabi|Marathi|"
                r"Bollywood|Diwali|Aarambh|Kannada|Malayalam|Odia)\b", re.I),
     "South Asian Indian, not American Indian"),
    (re.compile(r"\bIndian\s+(Dance|Classical|Music|Cuisine|Restaurant|Film|"
                r"Cultural Center of|Students?)\b", re.I),
     "South Asian Indian cultural organization"),
    (re.compile(r"\bIndians?\s+American\b|\bIndo-American\b", re.I),
     "word order tell: 'Indian American' is South Asian, not 'American Indian'"),
    (re.compile(r"^(A |The )?TRIBE CALLED\b", re.I),
     "wordplay on 'tribe', not a Native entity"),
]


# TAXONOMY (Elijah, 2026-08-05). Two categories, and the distinction is
# structural rather than cosmetic:
#
#   NATIVE ENTITY  - ANCs, NHOs, and tribes (state and federal). These are the
#                    sovereign / quasi-sovereign bodies and ANCSA corporations.
#                    Attribution ROLLS UP TO these. `parent_native_entity` must
#                    always resolve to one.
#
#   NATIVE ORG     - intertribal organizations, Native-focused nonprofits, and
#                    tribal enterprises and subsidiaries. These are actors in
#                    their own right but are NOT roll-up targets. An enterprise
#                    has a parent ENTITY; an intertribal org has member
#                    ENTITIES, not a parent; a nonprofit may have neither.
#
# Getting this wrong would let a consortium's contracts roll up to one member,
# or an enterprise become its own attribution target.
# Native entities are the TOP LEVEL - they have no parent, they are what
# things roll up to. Native organizations may be OWNED by an entity, and when
# they are, that entity is recorded as parent_native_entity. Some have no
# parent at all, and that is a real answer rather than a gap:
#
#   E-  enterprise/subsidiary  -> parent REQUIRED. An enterprise exists because
#       an entity owns it. An E- row with no parent is an INCOMPLETE RECORD,
#       and closing those is the attribution work itself.
#   I-  intertribal org        -> NO parent by nature. It has MEMBER entities,
#       not an owner. Recording a parent here would let a consortium's activity
#       roll up to a single member, which is the Northern Pueblos error.
#   NP- Native nonprofit       -> parent OPTIONAL. May be tribally controlled
#       (has a parent) or independently Native-controlled (genuinely none).
CLASS = {
    "T-":  ("tribes (federal + state)",          "native_entity",       "none_top_level"),
    "A-":  ("ANCs (regional + village corps)",   "native_entity",       "none_top_level"),
    "N-":  ("Native Hawaiian Organizations",     "native_entity",       "none_top_level"),
    "E-":  ("tribal enterprises + subsidiaries", "native_organization", "REQUIRED"),
    "I-":  ("intertribal organizations",         "native_organization", "none_has_members"),
    "NP-": ("Native-focused nonprofits",         "native_organization", "optional"),
}


def judge(row):
    name = (row.get("candidate_name") or "").strip()
    low = name.lower().strip()
    src = row.get("source_datasets", "")

    if low in TOO_GENERIC:
        return "generic fragment, not a specific entity"
    for pat, why in WRONG_SENSE:
        if pat.search(name):
            return why
    for pat, why in REJECT:
        if pat.search(name):
            return why

    # The Federal Register IS the most comprehensive source for entity
    # mentions - which is why matching against it works so well (97-98% on
    # compact and gaming tribe fields). But it should CONFIRM and DATE known
    # entities, not PROPOSE new ones out of prose. A title fragment naming a
    # real tribe ("Federal Recognition of the Lumbee Tribe") is a match signal,
    # not a new entity, because that tribe is already in the spine.
    if "anchored_suffix" in src:
        return ("extracted from document prose - FR/bills text confirms and dates "
                "known entities, it does not define new ones")
    if len(name) < 6:
        return "too short to identify an entity"
    return None


def main():
    print("=== Cedar Press: cull entity candidates ===\n")
    rows = read_csv(SRC)
    shutil.copy2(SRC, SRC.with_suffix(".csv.bak_" + TODAY))
    print(f"  input candidates: {len(rows):,}")

    keep, drop = [], []
    for r in rows:
        why = judge(r)
        if why:
            r["reject_reason"] = why
            drop.append(r)
        else:
            keep.append(r)

    # Elijah, 2026-08-05: the spine covers ALL Native entities and orgs - ANCs,
    # NHOs, federal AND state tribes, intertribal orgs, and Native-focused
    # nonprofits. So splitting on PRIORITY was the wrong axis: it demoted real
    # Native nonprofits ("American Indian Relief Inc", "Northwest Indian Bar
    # Association") to a discovery pool purely because their SOURCE was the IRS
    # BMF rather than a Native-by-construction roster. Source quality belongs
    # in a confidence column, not in whether something is a candidate at all.
    #
    # Everything that survives the wrong-sense and prose filters is a proposal,
    # organized by the class it would join.
    for r in keep:
        pfx = r.get("proposed_prefix", "")
        meta = CLASS.get(pfx, ("", "", ""))
        r["entity_category"] = meta[1]
        r["roll_up_target"] = "yes" if meta[1] == "native_entity" else "no"
        r["parent_requirement"] = meta[2]
        # OWNERSHIP. Who owns it. Drives attribution and roll-up.
        r["parent_native_entity"] = ""
        # SERVICE. Who it serves. A separate fact entirely, and often the only
        # one that is knowable: Cherokee Elders Council serves Cherokee people
        # whether or not Cherokee Nation owns it; Akwesasne Boys & Girls Club
        # serves St Regis Mohawk; California Rural Indian Health Board serves
        # many tribes and is owned by none of them. Collapsing "serves" into
        # "owned by" would invent ownership out of a mission statement.
        # Pipe-delimited - an org can serve several entities.
        r["serves_native_entities"] = ""
        r["serves_basis"] = ""      # mission_statement | service_area | name | roster
        r["record_complete"] = "" if meta[2] == "REQUIRED" else "yes"

    fields = [c for c in rows[0].keys()] + [
        "entity_category", "roll_up_target", "parent_requirement",
        "parent_native_entity", "serves_native_entities", "serves_basis",
        "record_complete"]
    keep.sort(key=lambda r: (r.get("entity_category", ""),
                             r.get("proposed_prefix", ""),
                             {"HIGH": 0, "MEDIUM": 1}.get(r.get("priority"), 2),
                             -int(r.get("n_occurrences") or 0)))
    write_csv(SRC, keep, fields)
    write_csv(CLEAN / "entity_candidates_rejected.csv", drop,
              fields + ["reject_reason"])
    # Retire the pool file if an earlier run created one.
    (CLEAN / "entity_discovery_pool.csv").unlink(missing_ok=True)

    print("\n=== SUMMARY ===")
    print(f"  kept     : {len(keep):,}")
    print(f"  rejected : {len(drop):,}  ({len(drop)/max(len(rows),1)*100:.0f}%)")
    print("\n  kept by priority:")
    for k, v in Counter(r.get("priority", "") for r in keep).most_common():
        print(f"    {k or '(none)':<8} {v:>5}")
    print("\n  proposals by spine class:")
    for k, v in Counter(r.get("proposed_prefix", "") for r in keep).most_common():
        print(f"    {k or '(none)':<5} {v:>5}   {CLASS.get(k,('',''))[0]:<34} "
              f"[{CLASS.get(k,('',''))[1]}]")
    print("\n  by category:")
    for k, v in Counter(r.get("entity_category", "") for r in keep).most_common():
        print(f"    {k:<22} {v:>5}")
    incomplete = [r for r in keep if r.get("parent_requirement") == "REQUIRED"]
    print(f"\n  INCOMPLETE RECORDS (org requires a parent entity, none resolved):"
          f" {len(incomplete):,}")
    print("    Every one is an enterprise that must ultimately belong to a tribe,")
    print("    ANC or NHO. Resolving these IS the attribution work.")
    print("\n  top reject reasons:")
    for k, v in Counter(r["reject_reason"] for r in drop).most_common(6):
        print(f"    {v:>5}  {k}")


if __name__ == "__main__":
    main()
