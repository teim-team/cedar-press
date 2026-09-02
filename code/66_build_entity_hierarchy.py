#!/usr/bin/env python3
"""
Cedar Press - 66: Make the entity hierarchy explicit, and roll up to it.

ELIJAH, 2026-08-06
------------------
"we consolidate to the ultimate parent native entity or native org so you dont
 see like three different entries for chenega companies when its ultimately one
 ... i think thats the advantage that cant be replicated elsewhere"

He is right that it is the advantage, and right that we were not delivering it.

THE HIERARCHY ALREADY EXISTS - IN THE ID, WHERE NOTHING CAN USE IT
------------------------------------------------------------------
The spine's own identifiers encode parentage and no column expresses it:

    CNSF-MINNCH-ML                 Mille Lacs, a component of the Minnesota
                                   Chippewa Tribe (TRBF-MINNCH-00)
    CNSF-PSMQDY-IT                 Passamaquoddy Indian Township, one of the
                                   two Passamaquoddy communities
    AKNF-CHNEGA-00-CHGCCO-CHGCMT   Native Village of Chenega, in the Chugach
                                   region
    ANVC-*                         village corporations, whose regional parent
                                   sits in entity_master's Parent_Entity_ID

So a query could see Mille Lacs and Minnesota Chippewa as unrelated rows, and
three Chenega companies as three entities. This writes the relationship down.

TWO LEVELS, DELIBERATELY
------------------------
`parent_entity_id`          the immediate parent - Mille Lacs -> Minnesota
                            Chippewa; Alutiiq Pacific -> Afognak
`ultimate_parent_entity_id` the top of the chain, which is what a roll-up sums

They are separate because the middle of the chain is real and a subscriber will
want it: RiverTech -> Akima -> NANA is three facts, not one.

WHAT IT REFUSES TO DO
---------------------
It does not roll an ANCSA village corporation up into its regional corporation
as though the region owned it. ANCSA regional and village corporations are
SEPARATE corporations with separate shareholders; the region is a geographic and
statutory relationship, not ownership. That link is recorded as
`ancsa_region_entity_id` and is deliberately NOT the ultimate parent.

Getting that wrong would invent $23.9B of ownership.

THE FEDERAL REGISTER AS THE AUTHORITY ON NAMES
----------------------------------------------
91 FR 4102 (2026-01-30) lists every federally recognised entity and annotates
renames parenthetically. Those annotations are aliases we did not have, and two
of them answer questions that were open in the review queue:

    Mi'kmaq Nation              (previously listed as Aroostook Band of Micmacs)
    Yuhaaviatam of San Manuel   (previously listed as San Manuel Band of
     Nation                      Mission Indians)

Reads  data/spine/cedar_entity_spine.csv, entity_master.csv,
       data/raw/external/fr_recognized/2026-01899_raw.txt
Writes data/spine/cedar_entity_spine.csv          (+ hierarchy columns, aliases)
       data/clean/entity_hierarchy.csv            (the explicit graph)
"""

import csv
import re
import shutil
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE_P = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"
FR_TXT = CEDAR / "data" / "raw" / "external" / "fr_recognized" / "2026-01899_raw.txt"
TODAY = date.today().isoformat()

PAREN_RE = re.compile(
    r"^(.{3,90}?)\s*\((?:previously listed as|formerly|also known as|aka)\s+"
    r"([^)]{3,90})\)", re.M | re.I)


# --- REGENERATE GUARD (ADR-017, 2026-09-02) --------------------------------
def _carry_live_columns(path, canonical):
    """Derive this writer's header instead of declaring it.

    A wholesale writer holding a FIXED `fieldnames` list deletes every column
    an in-place enricher added since - no error, no exception, a diff nobody
    reads. Canonical order first so column order stays stable, then whatever
    the live file already carries. A retired column stays retired because it
    is not on disk; a promoted column survives because it is.

    THIS BUILD CANNOT REPOPULATE AN ENRICHER'S COLUMN. Carried columns are
    written BLANK and NAMED on stdout, which is strictly better than deleted:
    the schema survives and the enricher can refill them. Re-run the enricher
    after this build - `cedar_pipeline.enrichers_to_rerun(<table>)` names it.
    """
    import csv as _csv
    import os as _os
    canonical = list(canonical)
    _p = str(path)
    if not _os.path.exists(_p):
        return canonical
    with open(_p, encoding="utf-8-sig", newline="", errors="replace") as _fh:
        _live = next(_csv.reader(_fh), [])
    _extra = [c for c in _live if c and c not in canonical]
    if _extra:
        print("  [regenerate guard] %s: carrying %d enricher column(s) through "
              "this rebuild, BLANK - re-run the enricher: %s"
              % (_os.path.basename(_p), len(_extra), ", ".join(_extra)))
    return canonical + _extra


def read_csv(p):
    if not Path(p).exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def main():
    print("=== Cedar Press 66: entity hierarchy + roll-up ===\n")
    spine = read_csv(SPINE_P)
    master = {r["Entity_ID"]: r for r in read_csv(CEDAR / "entity_master.csv")}
    by_id = {r["tribe_id"]: r for r in spine}
    print(f"spine entities: {len(spine):,}")

    fields = list(spine[0].keys())
    for c in ("parent_entity_id", "parent_entity_name",
              "ultimate_parent_entity_id", "ultimate_parent_entity_name",
              "ancsa_region_entity_id", "hierarchy_basis"):
        if c not in fields:
            fields.append(c)

    # ---- 1. immediate parents, derived from the id scheme ----------------
    # CNSF-<PARENT>-<SUFFIX> is a constituent community of TRBF-<PARENT>-00.
    stats = Counter()
    for r in spine:
        tid = r["tribe_id"]
        for c in ("parent_entity_id", "parent_entity_name",
                  "ultimate_parent_entity_id", "ultimate_parent_entity_name",
                  "ancsa_region_entity_id", "hierarchy_basis"):
            r.setdefault(c, "")

        if tid.startswith("CNSF-"):
            parts = tid.split("-")
            if len(parts) >= 3:
                cand = f"TRBF-{parts[1]}-00"
                if cand in by_id:
                    r["parent_entity_id"] = cand
                    r["parent_entity_name"] = by_id[cand]["canonical_name"]
                    r["hierarchy_basis"] = (
                        "constituent community of a federally recognised tribe; "
                        "derived from the spine identifier")
                    stats["constituent -> parent tribe"] += 1

        elif tid.startswith("ANVC-"):
            # Regional corporation is a STATUTORY REGION, not an owner.
            ce = r.get("cedar_entity_id", "")
            pid = (master.get(ce, {}) or {}).get("Parent_Entity_ID", "")
            reg = next((s["tribe_id"] for s in spine
                        if s.get("cedar_entity_id") == pid
                        and s["tribe_id"].startswith("ANRC-")), "")
            if reg:
                r["ancsa_region_entity_id"] = reg
                r["hierarchy_basis"] = (
                    "ANCSA village corporation; the regional corporation is a "
                    "statutory region, NOT an owner - never rolled up")
                stats["village corp -> ANCSA region (not ownership)"] += 1

        elif tid.startswith("AKNF-"):
            # AKNF-<VILLAGE>-00-<REGION>[-<CONSORTIUM>]
            parts = tid.split("-")
            if len(parts) >= 4:
                reg = f"ANRC-{parts[3]}-00"
                if reg in by_id:
                    r["ancsa_region_entity_id"] = reg
                    r["hierarchy_basis"] = (
                        "Alaska Native village government; ANCSA region is "
                        "geographic, not ownership")
                    stats["village government -> ANCSA region"] += 1

    # ---- 2. ultimate parent: walk the immediate-parent chain --------------
    def ultimate(tid, seen=None):
        seen = seen or set()
        if tid in seen:
            return tid                      # cycle guard
        seen.add(tid)
        p = by_id.get(tid, {}).get("parent_entity_id", "")
        return ultimate(p, seen) if p and p in by_id else tid

    for r in spine:
        top = ultimate(r["tribe_id"])
        if top != r["tribe_id"]:
            r["ultimate_parent_entity_id"] = top
            r["ultimate_parent_entity_name"] = by_id[top]["canonical_name"]
            stats["has an ultimate parent"] += 1
        else:
            # An entity that is its own top. Stated, not left blank, so a
            # roll-up can group on this column unconditionally.
            r["ultimate_parent_entity_id"] = r["tribe_id"]
            r["ultimate_parent_entity_name"] = r["canonical_name"]

    # ---- 3. Federal Register renames become aliases ----------------------
    added_alias = 0
    if FR_TXT.exists():
        txt = FR_TXT.read_text(encoding="utf-8", errors="replace")
        pairs = [(re.sub(r"\s+", " ", a).strip(), re.sub(r"\s+", " ", b).strip())
                 for a, b in PAREN_RE.findall(txt)]
        print(f"\nFR 91 FR 4102 rename annotations: {len(pairs)}")
        idx = {norm(r["canonical_name"]): r for r in spine}
        for current, previous in pairs:
            hit = idx.get(norm(current))
            if not hit:
                # Try the previous name - the spine may still carry the old one.
                hit = idx.get(norm(previous))
            if not hit:
                continue
            al = [a.strip() for a in (hit.get("aliases") or "").split("|")
                  if a.strip()]
            for name in (current, previous):
                if name and norm(name) not in {norm(x) for x in al}:
                    al.append(name)
                    added_alias += 1
            hit["aliases"] = "|".join(al)
            print(f"   {current[:44]:44s} <- {previous[:38]}")

    print(f"\nhierarchy derived")
    for k, v in stats.most_common():
        print(f"  {v:5d}  {k}")
    print(f"  {added_alias:5d}  aliases added from the Federal Register")

    shutil.copy2(SPINE_P, SPINE_P.with_suffix(f".csv.bak_{TODAY}_pre66"))
    with open(SPINE_P, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(spine)
    print(f"\n  rewrote {SPINE_P.relative_to(CEDAR)}")

    rows = [{"tribe_id": r["tribe_id"], "canonical_name": r["canonical_name"],
             "entity_class": r["entity_class"],
             "parent_entity_id": r["parent_entity_id"],
             "parent_entity_name": r["parent_entity_name"],
             "ultimate_parent_entity_id": r["ultimate_parent_entity_id"],
             "ultimate_parent_entity_name": r["ultimate_parent_entity_name"],
             "ancsa_region_entity_id": r["ancsa_region_entity_id"],
             "hierarchy_basis": r["hierarchy_basis"], "built_date": TODAY}
            for r in spine]
    p = CLEAN / "entity_hierarchy.csv"
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=_carry_live_columns(p, list(rows[0].keys())),
                           restval="", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {p.relative_to(CEDAR)}")

    fam = defaultdict(list)
    for r in spine:
        if r["ultimate_parent_entity_id"] != r["tribe_id"]:
            fam[r["ultimate_parent_entity_name"]].append(r["canonical_name"])
    print(f"\nentities that now roll up ({len(fam)} families):")
    for k, v in sorted(fam.items(), key=lambda kv: -len(kv[1]))[:8]:
        print(f"   {k[:34]:34s} <- {', '.join(v)[:62]}")


if __name__ == "__main__":
    main()
