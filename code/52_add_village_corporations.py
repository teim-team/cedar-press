#!/usr/bin/env python3
"""
Cedar Press - 52: Add ANCSA village and group corporations to the spine.

THE GAP THIS CLOSES
-------------------
The spine held 12 ANC REGIONAL corporations and zero VILLAGE corporations, while
Elijah's taxonomy is explicit that "ANCs include Regional and Village
corporations." Every village-corporation party therefore had nothing correct to
match, and the matcher resolved it to the nearest thing sharing the place name -
the village GOVERNMENT.

That is a category error with money attached. `Ukpeagvik Inupiat Corporation` is
an ANCSA corporation with shareholders; the `Native Village of Barrow` is a
federally recognised tribal government. Different legal persons, different
balance sheets, and a contract award to one is not revenue to the other.

The defect was visible in Elijah's rulings before it was visible in the data -
six village corporations named outright in a single review batch:

    Etolin Strait Government Services  -> NIMA Corporation
    Alaska Solutions Alliance          -> Tyonek Native Corporation
    Goldbelt Nighthawk                 -> Goldbelt, Incorporated
    Bold Cape Information Technologies -> The King Cove Corporation
    Emmonak Taluyaq                    -> Emmonak Corporation
    Harbor View Technical Services     -> Old Harbor Native Corporation

SOURCE
------
`entity_master.csv` already carries 173 village corporations and 6 ANCSA group
corporations with `A-` identifiers, state, aliases, and a `Parent_Entity_ID`
pointing at the regional corporation. Nothing needs to be invented; it needs to
be joined.

WHAT THIS DOES NOT DO
---------------------
It does not merge a village corporation onto its namesake village government,
and it does not delete or alter any existing spine row. The two coexist as
separate entities, which is the entire point. A tribe_id collision aborts the
run rather than overwriting.

Reads  entity_master.csv
       data/spine/cedar_entity_spine.csv
Writes data/spine/cedar_entity_spine.csv   (village corps appended)
       review/village_corp_namesake_pairs.csv  (corp/government pairs to watch)
"""

import csv
import re
import shutil
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
SPINE = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"
MASTER = CEDAR / "entity_master.csv"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

WANTED = ("alaska native village corporation", "ancsa group corporation")

CLASS_MAP = {
    "alaska native village corporation": "Alaska Native Village Corporation",
    "ancsa group corporation": "ANCSA Group Corporation",
}

STOP = {"the", "inc", "incorporated", "corporation", "corp", "company", "llc",
        "ltd", "limited", "native", "alaska", "of", "and"}


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def token(name, taken):
    """Deterministic 6-character id token, in the style the spine already uses
    (ANRC-AHTNAI-00, ANRC-BERSTR-00). Collisions get a numeric suffix rather
    than a silent merge."""
    words = [w for w in norm(name).split() if w not in STOP]
    if not words:
        words = norm(name).split() or ["entity"]
    base = "".join(words)
    # Prefer consonants so the token stays legible, as the existing ids do.
    cons = re.sub(r"[aeiou]", "", base)
    cand = (cons if len(cons) >= 6 else base)[:6].upper().ljust(6, "X")
    if cand not in taken:
        return cand
    for i in range(1, 100):
        alt = (cand[:5] + str(i))[:6]
        if alt not in taken:
            return alt
    raise SystemExit(f"cannot mint a unique token for {name}")


def read_csv(p):
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def main():
    print("=== Cedar Press 52: add ANCSA village + group corporations ===\n")

    spine = read_csv(SPINE)
    fields = list(spine[0].keys())
    master = read_csv(MASTER)

    corps = [r for r in master
             if r.get("Entity_Type", "").strip().lower() in WANTED]
    print(f"entity_master village/group corporations : {len(corps)}")
    print(f"spine entities before                    : {len(spine)}")

    have_names = {norm(r["canonical_name"]) for r in spine}
    have_ids = {r["tribe_id"] for r in spine}
    have_ceid = {r.get("cedar_entity_id", "") for r in spine if r.get("cedar_entity_id")}
    taken = {r["tribe_id"].split("-")[1] for r in spine if "-" in r["tribe_id"]}

    # Regional-corp lookup so a village corp can name its parent.
    reg_by_ceid = {r.get("cedar_entity_id", ""): r["canonical_name"]
                   for r in spine if "Regional Corp" in r.get("entity_class", "")}
    master_name = {r["Entity_ID"]: r["Canonical_Name"] for r in master}

    added, skipped, pairs = [], Counter(), []

    for c in corps:
        name = c["Canonical_Name"].strip()
        n = norm(name)
        if n in have_names:
            skipped["already in spine by name"] += 1
            continue
        if c["Entity_ID"] in have_ceid:
            skipped["already in spine by cedar_entity_id"] += 1
            continue

        tok = token(name, taken)
        taken.add(tok)
        tid = f"ANVC-{tok}-00"
        if tid in have_ids:
            raise SystemExit(f"ABORT: {tid} already exists. Refusing to "
                             f"overwrite an existing spine entity.")

        pid = (c.get("Parent_Entity_ID") or "").strip()
        parent = reg_by_ceid.get(pid) or master_name.get(pid, "")

        aliases = [a.strip() for a in
                   re.split(r"[;|]", c.get("Aliases") or "") if a.strip()]
        if name not in aliases:
            aliases.insert(0, name)

        row = {f: "" for f in fields}
        row.update({
            "tribe_id": tid,
            "canonical_name": name,
            "entity_class": CLASS_MAP[c["Entity_Type"].strip().lower()],
            "state": c.get("State", "AK"),
            "cedar_entity_id": c["Entity_ID"],
            "aliases": "|".join(aliases),
        })
        for k in ("n_uei_tierA", "n_uei_tierB", "n_cage", "n_ein"):
            if k in row:
                row[k] = "0"
        if "parent_native_entity" in fields:
            row["parent_native_entity"] = parent
        added.append(row)
        have_ids.add(tid)

        # A namesake village GOVERNMENT is the trap. Record the pair so the
        # collision is documented rather than rediscovered.
        core = {w for w in norm(name).split() if w not in STOP}
        for s in spine:
            if "Alaska Native Village" not in s.get("entity_class", ""):
                continue
            sc = {w for w in norm(s["canonical_name"]).split() if w not in STOP}
            if sc and (sc <= core or core <= sc):
                pairs.append({
                    "corporation": name, "corporation_tribe_id": tid,
                    "government": s["canonical_name"],
                    "government_tribe_id": s["tribe_id"],
                    "warning": "Separate legal persons. A contract to the "
                               "corporation is not revenue to the government.",
                })

    print(f"\n  to add   : {len(added)}")
    for k, v in skipped.most_common():
        print(f"  skipped  : {v}  ({k})")

    if added:
        shutil.copy2(SPINE, SPINE.with_suffix(f".csv.bak_{TODAY}_pre52"))
        with open(SPINE, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(spine + added)
        print(f"\n  wrote {SPINE.relative_to(CEDAR)}  "
              f"({len(spine)} -> {len(spine)+len(added)} entities)")

    if pairs:
        p = REVIEW / "village_corp_namesake_pairs.csv"
        with open(p, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(pairs[0].keys()))
            w.writeheader()
            w.writerows(pairs)
        print(f"  wrote {p.relative_to(CEDAR)}  ({len(pairs)} corp/government "
              f"name pairs - each one a live confusion risk)")

    # Did we actually fix the cases the rulings named?
    print("\ncases from Elijah's rulings, now resolvable:")
    names = {norm(r["canonical_name"]): r["tribe_id"] for r in added}
    for probe in ["nima corporation", "tyonek native corporation",
                  "goldbelt incorporated", "emmonak corporation",
                  "old harbor native corporation",
                  "ukpeagvik inupiat corporation"]:
        hit = next((v for k, v in names.items()
                    if probe in k or k in probe), None)
        print(f"  {probe:34s} {hit or 'STILL MISSING'}")


if __name__ == "__main__":
    main()
