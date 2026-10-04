#!/usr/bin/env python3
"""
1190 - home community: each Cedar entity's home geography, as public codes.

    python3 code/1190_build_home_community.py build      # write outputs + stats
    python3 code/1190_build_home_community.py verify     # re-measure; exit 1 on drift
    python3 code/1190_build_home_community.py selftest   # prove verify and the binding fire

WHY
---
Owner intent, 2026-10-04 (Elijah Moreno): connect an entity to a place, so that
no matter where a deal happens or where a business got a contract, we know the
home community it benefits. For ANCs that is the ANCSA region; for tribes their
reservation or AIAN land, or, without land, their headquarters county, which is
kept whatever else is known. Where something actually happened stays the row's
own geocoded address or place of performance (ADR-015 rule 1). No Cedar place
identifier exists or is created: the home community is an attribute of a `CE-`
entity, made of public Census codes (AIANNH GEOID, ANRC GEOID, county FIPS).

The rules live in ONE place, Lumecon-data `src/lumecon_data/home_community.py`
(the producer); this script only gathers Cedar's inputs and calls it. It never
re-implements a rule, so it needs the pinned producer installed:

    pip install "git+https://github.com/teim-team/Lumecon-data@<LUMECON_DATA_SHA>"

WHAT IT READS
-------------
In Git (always present):
  data/spine/cedar_identity_register.csv   the entity universe (every CE- uid)
  ANRC_REGIONAL_CORPORATIONS below         the twelve ANCSA regional corporations
                                           bound to their Census ANRC areas, by uid,
                                           checked against the register at run time

Workstation only (used when present, counted in the stats either way):
  data/clean/geo_aiannh_dim.csv            873: TIGER 2024 AIANNH areas (classfp)
  data/clean/geo_entity_aiannh_links.csv   reviewed entity -> AIANNH links:
                                           cedar_uid, aiannh_geoid, source_url
  data/clean/geo_entity_hq_county.csv      reviewed HQ county per entity:
                                           cedar_uid, hq_county_fips,
                                           hq_county_name, hq_source_url
  data/clean/geo_entity_anrc_links.csv     reviewed village / village-corporation
                                           -> ANRC links: cedar_uid, anrc_geoid,
                                           source_url
  data/clean/geo_point_aiannh_assignment.csv  873: exact point-in-polygon rows

None of the four workstation link files exists today. They are reviewed
bindings, never fuzzy matches: `data/raw/external/compacts/prior_extractions/
tribe_aiannh_crosswalk_master.csv` (303 gaming-compact tribes) is a NAME match
and is not read here; turning it into `geo_entity_aiannh_links.csv` needs an
exact cedar_uid per row (AGENTS.md: exact approved crosswalks only).

WHAT IT WRITES
--------------
  data/clean/geo_entity_home_community.csv     one row per register entity
  data/clean/geo_benefit_links_in_home_area.csv  in_home_area links from 873
                                                 points (only when 873 is present)
  docs/GEO_HOME_COMMUNITY_STATS.json           measured counts per basis, and
                                               which inputs were present (committed)
"""

import csv
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPINE = os.path.join(ROOT, "data", "spine", "cedar_identity_register.csv")
CLEAN = os.path.join(ROOT, "data", "clean")
IN_DIM = os.path.join(CLEAN, "geo_aiannh_dim.csv")
IN_AIANNH = os.path.join(CLEAN, "geo_entity_aiannh_links.csv")
IN_HQ = os.path.join(CLEAN, "geo_entity_hq_county.csv")
IN_ANRC = os.path.join(CLEAN, "geo_entity_anrc_links.csv")
IN_POINTS = os.path.join(CLEAN, "geo_point_aiannh_assignment.csv")
OUT_HOMES = os.path.join(CLEAN, "geo_entity_home_community.csv")
OUT_LINKS = os.path.join(CLEAN, "geo_benefit_links_in_home_area.csv")
OUT_STATS = os.path.join(ROOT, "docs", "GEO_HOME_COMMUNITY_STATS.json")

REGIONAL_CLASS = "Alaska Native Regional Corporation"
# One regional corporation per ANCSA region (43 U.S.C. 1606(a)); the ANRC GEOID
# is Census's (TIGERweb ANRC table, lumecon_data.home_community.TIGER_ANRC_URL).
# Keyed by register uid; the canonical name is checked, so a renamed or
# reclassified register row stops the build instead of binding silently.
ANRC_REGIONAL_CORPORATIONS = {
    "CE-00076-76": ("Ahtna, Incorporated", "0200590"),
    "CE-00077-DZ": ("Aleut Corporation", "0201570"),
    "CE-00078-KR": ("Arctic Slope Regional Corporation", "0203950"),
    "CE-00079-SH": ("Bering Straits Native Corporation", "0206370"),
    "CE-0007A-ZA": ("Bristol Bay Native Corporation", "0209040"),
    "CE-0007B-53": ("Calista Corporation", "0209800"),
    "CE-0007C-BW": ("Chugach Alaska Corporation", "0214410"),
    "CE-0007D-HN": ("Cook Inlet Region, Incorporated", "0217140"),
    "CE-0007E-QE": ("Doyon, Limited", "0220010"),
    "CE-0007F-X7": ("Koniag, Incorporated", "0241640"),
    "CE-0007G-30": ("NANA Regional Corporation, Incorporated", "0252120"),
    "CE-0007H-9S": ("Sealaska Corporation", "0267940"),
}


def _producer():
    try:
        from lumecon_data import home_community
    except ImportError:
        raise SystemExit(
            "[1190] lumecon_data is not installed. Install the pinned producer:\n"
            '  pip install "git+https://github.com/teim-team/Lumecon-data@<LUMECON_DATA_SHA>"'
        )
    return home_community


def _read(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def _sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _inputs():
    seen = {}
    for name, path in (
        ("register", SPINE),
        ("aiannh_dim", IN_DIM),
        ("entity_aiannh_links", IN_AIANNH),
        ("entity_hq_county", IN_HQ),
        ("entity_anrc_links", IN_ANRC),
        ("point_aiannh_assignment", IN_POINTS),
    ):
        seen[name] = (
            {"path": os.path.relpath(path, ROOT), "sha256": _sha(path)}
            if os.path.exists(path)
            else None
        )
    return seen


def compute(register_rows, anrc_table=None):
    """Entity homes and in_home_area links from whatever inputs are present."""
    hc = _producer()
    anrc_table = ANRC_REGIONAL_CORPORATIONS if anrc_table is None else anrc_table
    register = {row["cedar_uid"]: row for row in register_rows}
    regional = sorted(u for u, r in register.items() if r["entity_class"] == REGIONAL_CLASS)
    if sorted(anrc_table) != regional:
        raise SystemExit(f"[1190] regional corporations in the register {regional} "
                         f"differ from the bound table {sorted(anrc_table)}")
    for uid, (name, _geoid) in anrc_table.items():
        if register[uid]["canonical_name"] != name:
            raise SystemExit(f"[1190] {uid}: register name {register[uid]['canonical_name']!r}"
                             f" is not the bound {name!r}")

    hq = {}
    if os.path.exists(IN_HQ):
        for row in _read(IN_HQ):
            hq[row["cedar_uid"]] = row
    entities = []
    for uid in sorted(register):
        row = hq.get(uid)
        entities.append(
            hc.EntityGeography(uid, row["hq_county_fips"], row["hq_county_name"],
                               row["hq_source_url"])
            if row else hc.EntityGeography(uid)
        )

    dim = {}
    if os.path.exists(IN_DIM):
        dim = {row["aiannh_geoid"]: row for row in _read(IN_DIM)}
    aiannh = []
    if os.path.exists(IN_AIANNH):
        if not dim:
            raise SystemExit("[1190] entity AIANNH links need data/clean/geo_aiannh_dim.csv")
        for row in _read(IN_AIANNH):
            area = dim.get(row["aiannh_geoid"])
            if area is None:
                raise SystemExit(f"[1190] {row['cedar_uid']}: AIANNH {row['aiannh_geoid']} "
                                 "is not in the 873 dimension")
            aiannh.append(hc.AiannhHome(row["cedar_uid"], row["aiannh_geoid"],
                                        area["aiannh_name"], area["classfp"],
                                        row.get("source_url") or hc.TIGER_AIANNH_URL))

    anrc = [hc.AnrcHome(uid, geoid) for uid, (_n, geoid) in sorted(anrc_table.items())]
    if os.path.exists(IN_ANRC):
        for row in _read(IN_ANRC):
            anrc.append(hc.AnrcHome(row["cedar_uid"], row["anrc_geoid"],
                                    row.get("source_url") or hc.TIGER_ANRC_URL))

    homes = hc.build_entity_homes(entities, aiannh, anrc)
    links = []
    if os.path.exists(IN_POINTS):
        links = hc.benefit_links(
            homes, assignments=[hc.point_assignment_from_873(r) for r in _read(IN_POINTS)]
        )
    return hc, register, homes, links


def stats_for(hc, register, homes, links):
    by_class = {}
    for uid, home in homes.items():
        cls = register[uid]["entity_class"]
        by_class.setdefault(cls, {b: 0 for b in hc.BASES})[home.basis] += 1
    return {
        "script": "1190_build_home_community.py",
        "producer_policy": hc.POLICY,
        "entities": len(homes),
        "home_community_basis": hc.basis_counts(homes),
        "by_entity_class": dict(sorted(by_class.items())),
        "in_home_area_links": len(links),
        "in_home_area_shared_area_links": sum(1 for x in links if x.shared_area),
        "inputs": _inputs(),
        "note": "Counts are measured from the inputs listed; an absent workstation input "
        "leaves its entities at a weaker basis, never a guessed one. The 13th Regional "
        "Corporation is not in the register and has no Census ANRC area.",
    }


def build():
    hc, register, homes, links = compute(_read(SPINE))
    stats = stats_for(hc, register, homes, links)
    if os.path.isdir(CLEAN):
        with open(OUT_HOMES, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, ["cedar_uid", *hc.ENTITY_COLUMNS])
            w.writeheader()
            for uid, home in homes.items():
                w.writerow({"cedar_uid": uid, **home.columns()})
        if links:
            with open(OUT_LINKS, "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, ["row_id", *hc.LINK_COLUMNS])
                w.writeheader()
                for link in links:
                    w.writerow({"row_id": link.row_id, **link.columns()})
        print(f"[1190] wrote {os.path.relpath(OUT_HOMES, ROOT)}")
    else:
        print("[1190] data/clean is absent (not a workstation): only the stats are written")
    with open(OUT_STATS, "w", encoding="utf-8") as fh:
        json.dump(stats, fh, indent=2, sort_keys=False)
        fh.write("\n")
    print(json.dumps(stats["home_community_basis"]))
    return 0


def verify(stats_path=OUT_STATS, anrc_table=None):
    hc, register, homes, links = compute(_read(SPINE), anrc_table)
    want = stats_for(hc, register, homes, links)
    with open(stats_path, encoding="utf-8") as fh:
        have = json.load(fh)
    if have != want:
        print("[1190 verify] FAIL: docs/GEO_HOME_COMMUNITY_STATS.json is stale")
        return 1
    if len(homes) != len(register):
        print("[1190 verify] FAIL: not one home row per register entity")
        return 1
    print(f"[1190 verify] ok  {json.dumps(want['home_community_basis'])}")
    return 0


def selftest():
    import tempfile

    with open(OUT_STATS, encoding="utf-8") as fh:
        stats = json.load(fh)
    stats["home_community_basis"]["anrc_region"] += 1
    with tempfile.TemporaryDirectory() as tmp:
        corrupt = os.path.join(tmp, "stats.json")
        with open(corrupt, "w", encoding="utf-8") as fh:
            json.dump(stats, fh)
        if verify(corrupt) != 1:
            print("[1190 selftest] FAIL: verify accepted corrupted stats")
            return 1
    renamed = dict(ANRC_REGIONAL_CORPORATIONS)
    renamed["CE-00076-76"] = ("Ahtna Corporation", "0200590")
    try:
        compute(_read(SPINE), renamed)
    except SystemExit:
        pass
    else:
        print("[1190 selftest] FAIL: a mismatched regional-corporation binding was accepted")
        return 1
    print("[1190 selftest] ok: verify fires on drift; a wrong binding stops the build")
    return 0


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "build"
    sys.exit({"build": build, "verify": verify, "selftest": selftest}[mode]())
