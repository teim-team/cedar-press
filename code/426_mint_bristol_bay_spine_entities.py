#!/usr/bin/env python3
"""
Cedar Press - 426: mint spine entities for BBAHC and BBHA. FA-04, step 2.

Reads the finding written by `425_establish_bristol_bay_entities.py` and
APPENDS two rows to `data/spine/cedar_entity_spine.csv` IN PLACE.

    py -3 code/426_mint_bristol_bay_spine_entities.py --check   # write nothing
    py -3 code/426_mint_bristol_bay_spine_entities.py           # apply

WHY AN APPEND AND NEVER A REBUILD
----------------------------------
`01_build_entity_spine.py` is on the never-run list: a full rebuild drops every
appended entity, and that is how the NHOs were lost once. This script re-reads
the spine immediately before writing, appends, writes `.part`, renames, and
then RE-READS FROM DISK to verify - never from its own run log, because two
outputs reverted between runs on this machine on 2026-08-26.

WHERE THE ID COMES FROM, AND WHY IT IS NOT `CEDAR-ENT`
-------------------------------------------------------
`cedar_ids.allocate()` REFUSES a grandfathered entity prefix by design:

    ValueError: SGVF is GRANDFATHERED - existing IDs only, never minted.

That refusal is correct and is not worked around. The concurrent identity pass
rewrote `cedar_ids.py` the same evening and its `CLASS_PREFIX` map is now the
authority on what a NEW entity of a given class gets:

    CLASS_PREFIX["Federal-level self-governance consortium"] = "SGVF"
    CLASS_PREFIX["Intertribal Organization"]                 = "ITO"

So the id is composed the way every other appended spine entity's id was
composed - `<PREFIX>-<TOKEN6>-00` - and the pieces come from the two modules
that already own them, never re-typed here:

  * the PREFIX from `cedar_ids.class_prefix(entity_class)`. Asking the module
    means that when the identity pass lands `docs/CEDAR_ID_SYSTEM.md` and
    changes a mapping, this script follows it instead of contradicting it.
  * the TOKEN from `61_add_nho_intertribal_to_spine.py::token(name, taken)`,
    IMPORTED, not re-implemented - the same function that minted every `ITO-`
    id in the spine. Standing rule 8: re-implementing matching guarantees
    drift. `61` is `__main__`-guarded, so importing it runs nothing.
  * the result is REGISTERED with `cedar_ids.adopt_existing(prefix, [id])`,
    which is the ID service's own route for a grandfathered prefix, so a later
    mint cannot collide with what this pass created.

**Determinism, because `class7` is a tracked gate metric at 42 and must not
rise.** `token()` resolves a collision with a numeric suffix, so the ids depend
on the ORDER the two subjects are minted in. They are minted in sorted order of
`canonical_name`, fixed in code, so a re-run produces the same two ids:

    Bristol Bay Area Health Corporation -> SGVF-BRSTLB-00
    Bristol Bay Housing Authority       -> ITO-BRSTL1-00

`BRSTL1` is the collision form and it is not pretty. It is also the form 60+
existing spine tokens already take (`BLCKF1`, `CHCKS2`, `CRWCR1`), which is
worth more than a prettier token minted by a second, divergent rule.

**No id is ever reused.** Both ids are checked against every id in the live
spine before the write, and against the ledger, and the run aborts on a hit.

WHAT THESE ROWS DELIBERATELY DO NOT CARRY
------------------------------------------
- `parent_native_entity`, `parent_entity_id`, `ultimate_parent_entity_id`:
  **blank, and the blank is a RULING.** Neither organisation is owned by
  anybody - not by BBNC, not by its member tribes. `ownership_basis` says so
  in words, the way the 56 federally operated BIE schools needed.
  `docs/ANCSA_OWNERSHIP_RULING.md` rules 4 and 5, and the ITO taxonomy note
  *"NOT owned by its member tribes"*.
- `ancsa_region_entity_id`: **blank.** Writing `ANRC-BRBYCO-00` there would
  reintroduce, as geography, exactly the association that this whole finding
  is about. `associated_with_region` moved $32.87B wrongly once.
- No relationship edge is written at all. The 29 tribe-side `affiliated_with`
  rows in `entity_relationships.csv` that name 'Bristol Bay HA' with a BLANK
  target and the note *"pending a spine entity"* are now fillable, and that is
  reported here as a follow-up rather than done: filling a blank target is a
  NEW link, not a repoint, and it belongs with whoever owns script 97.

Backup: cedar_entity_spine.csv.bak_<date>_pre_426_mint_bristol_bay_spine_entities
"""

import csv
import importlib.util
import json
import os
import shutil
import sys
from datetime import date
from pathlib import Path

csv.field_size_limit(min(sys.maxsize, 2147483647))

CEDAR = Path(__file__).resolve().parent.parent
SPINE = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"
LEDGER = CEDAR / "data" / "clean" / "cedar_identifier_ledger_final.csv"
EVIDENCE = CEDAR / "docs" / "BRISTOL_BAY_ENTITY_EVIDENCE.json"
TODAY = date.today().isoformat()
SCRIPT = Path(__file__).name

IHS_URL = "https://www.ihs.gov/alaska/tribalhealthorganizations/"
HUD_URL = ("https://www.hud.gov/sites/dfiles/PIH/documents/"
           "AK-Tribe-TDHE-Assignments.pdf")
FAC_URL = "https://api.fac.gov/general?report_id=eq."

#: Per subject: the columns whose values are FACTS, with the source that
#: states each one. Anything not here is left blank on purpose.
ROW_EVIDENCE = {
    "BBAHC": {
        "entity_source_url": IHS_URL,
        "entity_source_quote":
            "Indian Health Service, Alaska Area, 'Alaska Area Tribal Health "
            "Organizations': 'Below is a list of THOs that have Title I "
            "contracts and one Title V compact with separate tribal funding "
            "agreements with Indian Health Service.' Bristol Bay Area Health "
            "Corporation is listed under the heading 'Alaska Title V "
            "Compactors'. Corroborated by the Federal Audit Clearinghouse "
            "(auditee EIN 920044965, UEI NL5HNWNUFMK4, Dillingham AK, "
            "cognizant agency 93) and by 244 CFDA 93.210 'Tribal "
            "Self-Governance Program: IHS Compacts/Funding Agreements' "
            "assistance rows.",
        "evidence_tier": "A",
        "evidence_grade": "TWO_INDEPENDENT_FEDERAL_SOURCES",
        "verification_route": "ihs_alaska_title_v_roster+fac_single_audit_ein",
        "serves_native_entities": "1",
    },
    "BBHA": {
        "entity_source_url": HUD_URL,
        "entity_source_quote":
            "HUD Office of Native American Programs, 'AK Tribe/TDHE "
            "Assignments': 'Bristol Bay HA' is printed as the tribally "
            "designated housing entity for 29 subjects - 28 Alaska Native "
            "villages (Aleknagik, Chignik Lagoon, Chignik Lake, Chignik "
            "Native, Clarks Point, Curyung (Dillingham), Ekuk, Ekwok, "
            "Igiugig, Iliamna, Ivanof Bay, Kanatak, King Salmon, Kokhanok, "
            "Koliganek, Levelock, Manokotak, Naknek, New Stuyahok, Newhalen, "
            "Perryville, Pilot Point, Port Heiden, Portage Creek "
            "(Ohgsenakale), South Naknek, Togiak, Twin Hills, Ugashik) plus "
            "Bristol Bay Native Corporation. Corroborated by 47 CFDA 14.867 "
            "'Indian Housing Block Grants' assistance rows on UEI "
            "KJKZSSS83DD9, Dillingham AK.",
        "evidence_tier": "A",
        "evidence_grade": "TWO_INDEPENDENT_FEDERAL_SOURCES",
        "verification_route": "hud_onap_tdhe_assignment_list+cfda_14867",
        "serves_native_entities": "1",
    },
}

OWNERSHIP_BASIS = (
    "NO OWNER, and the blank is a RULING rather than unfinished research. "
    "This organisation is not owned by Bristol Bay Native Corporation, which "
    "is a separate ANCSA regional corporation with a separate EIN, and it is "
    "not owned by its member tribes either - membership is affiliated_with / "
    "member_of, both inside cedar_domain.NEVER_OWNERSHIP. "
    "docs/ANCSA_OWNERSHIP_RULING.md rules 4 and 5. No dollar rolls up from "
    "this entity to any other."
)

RECON_NOTE = (
    "Minted {today} by {script} to discharge ANOMALY_REPORT FA-04: this "
    "organisation had no spine entity, so an unreviewed cluster_v3 row keyed "
    "it to ANRC-BRBYCO-00 (Bristol Bay Native Corporation) and ten tables "
    "inherited the error. Evidence: docs/BRISTOL_BAY_ENTITY_EVIDENCE.json and "
    "review/bristol_bay_entity_evidence_{today}.csv."
)


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, CEDAR / "code" / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_csv(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8-sig", errors="replace") as fh:
        return list(csv.DictReader(fh))


def main():
    check = "--check" in sys.argv
    print(f"=== Cedar Press 426: mint the Bristol Bay spine entities "
          f"(FA-04) ===\n")

    if not EVIDENCE.exists():
        raise SystemExit(f"  {EVIDENCE.name} absent - run "
                         f"425_establish_bristol_bay_entities.py first. "
                         f"A mint without a written finding is the drive-by "
                         f"edit this pass exists to avoid.")
    finding = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    subjects = finding["subjects"]
    print(f"  finding    : {finding['finding_id']} established "
          f"{finding['established_date']} by {finding['established_by_script']}")
    print(f"  subjects   : {', '.join(sorted(subjects))}")

    ids_mod = load_module("cedar_ids", "cedar_ids.py")
    m61 = load_module("m61", "61_add_nho_intertribal_to_spine.py")
    print("  prefix     : cedar_ids.class_prefix()  (never a literal here)")
    print("  token      : 61_add_nho_intertribal_to_spine.token()  (imported)")

    # The ID service's own refusal, printed rather than hidden, so the next
    # reader knows the grandfathered route was taken deliberately.
    try:
        ids_mod.allocate("SGVF", 1)
        print("  !! cedar_ids.allocate('SGVF') SUCCEEDED - the prefix is no "
              "longer grandfathered. STOP and re-read cedar_ids.py before "
              "trusting this script's id scheme.")
        return 2
    except ValueError as e:
        print(f"  allocate() correctly refuses a grandfathered prefix:\n"
              f"      {e}")

    spine = read_csv(SPINE)
    if not spine:
        raise SystemExit("  spine empty or missing - refusing")
    fields = list(spine[0])
    taken_ids = {(r.get("tribe_id") or "").strip() for r in spine}
    taken_tokens = set()
    for r in spine:
        parts = (r.get("tribe_id") or "").split("-")
        if len(parts) > 1:
            taken_tokens.add(parts[1])
    print(f"\n  spine before: {len(spine):,} entities, {len(fields)} columns")

    minted, rows_new = [], []
    for key in sorted(subjects, key=lambda k: subjects[k]["canonical_name"]):
        s = subjects[key]
        cls = s["entity_class"]
        prefix = ids_mod.class_prefix(cls)
        if not prefix:
            raise SystemExit(
                f"  cedar_ids.class_prefix({cls!r}) returned None. An "
                f"undeclared class must not silently acquire a prefix. STOP.")
        tok = m61.token(s["canonical_name"], taken_tokens)
        taken_tokens.add(tok)
        eid = f"{prefix}-{tok}-00"
        if eid in taken_ids:
            raise SystemExit(f"  {eid} already exists in the spine. An id is "
                             f"NEVER reused. STOP.")
        taken_ids.add(eid)
        minted.append((key, s, prefix, eid))
        print(f"    {s['canonical_name']:38s} {cls:44s} -> {eid}")

    # An id is never reused, including one some earlier pass retired.
    led = read_csv(LEDGER)
    led_ids = {(r.get("tribe_id") or "").strip() for r in led}
    clash = [e for _k, _s, _p, e in minted if e in led_ids]
    if clash:
        raise SystemExit(f"  {clash} already appear in the identifier ledger - "
                         f"these ids are not free. STOP.")
    print(f"  checked against {len(taken_ids):,} spine ids and "
          f"{len(led_ids):,} ledger ids: both free")

    for key, s, prefix, eid in minted:
        e = ROW_EVIDENCE[key]
        row = {k: "" for k in fields}
        row["tribe_id"] = eid
        row["canonical_name"] = s["canonical_name"]
        row["entity_class"] = s["entity_class"]
        row["state"] = s["state"]
        row["city"] = s["city"]
        row["bia_region"] = "Alaska"
        row["fr_official_name"] = s["canonical_name"]
        row["aliases"] = "|".join(sorted({
            s["canonical_name"].upper(),
            "BRISTOL BAY AREA HEALTH CORPORATION AND SUBSIDIARY"
            if key == "BBAHC" else "BRISTOL BAY HA",
        }))
        row["ownership_basis"] = OWNERSHIP_BASIS
        row["serves_native_entities"] = e["serves_native_entities"]
        row["entity_source_url"] = e["entity_source_url"]
        row["entity_source_quote"] = e["entity_source_quote"]
        row["source_url"] = e["entity_source_url"]
        row["source_quote"] = e["entity_source_quote"]
        row["evidence_tier"] = e["evidence_tier"]
        row["evidence_grade"] = e["evidence_grade"]
        row["verification_route"] = e["verification_route"]
        row["evidence_url"] = e["entity_source_url"]
        row["built_by_script"] = f"code/{SCRIPT}"
        row["reconciliation_status"] = "MINTED_TO_DISCHARGE_FA-04"
        row["reconciliation_note"] = RECON_NOTE.format(today=TODAY,
                                                       script=SCRIPT)
        # row["cicd_verified"] = "0"  # CICD nuked 2026-09-02 (844)
        # cedar_entity_id is the upstream entity_master register code, NOT a
        # Cedar id (cedar_ids.ENTITY_ID_COLUMN_MEANINGS). These entities are
        # not in that register, so it stays blank rather than acquiring a
        # value that would look like a foreign key and join to nothing.
        for blank in ("parent_entity_id", "parent_entity_name",
                      "ultimate_parent_entity_id", "ultimate_parent_entity_name",
                      "ancsa_region_entity_id", "parent_native_entity",
                      "cedar_entity_id", "hierarchy_basis"):
            if blank in row:
                row[blank] = ""
        rows_new.append(row)

    print("\n  the columns each new row carries:")
    for row in rows_new:
        print(f"    {row['tribe_id']}")
        for k in fields:
            if row.get(k):
                v = row[k]
                print(f"        {k:26s} = {v[:96]}{'...' if len(v) > 96 else ''}")
        print(f"        parent/ultimate/ancsa_region = BLANK, and the blank "
              f"is a ruling (see ownership_basis)")

    if check:
        print("\n  --check: nothing written, and the id registry was NOT "
              "touched.")
        return 0

    # ---- write, under the concurrency rules -------------------------------
    before_stat = SPINE.stat()
    live = read_csv(SPINE)
    if len(live) != len(spine):
        raise SystemExit(f"  spine changed under us ({len(spine):,} -> "
                         f"{len(live):,}) while this run was deciding. "
                         f"REFUSING to write. Re-run.")
    live_fields = list(live[0])
    if live_fields != fields:
        raise SystemExit("  spine column set changed under us. REFUSING.")

    bak = SPINE.with_name(SPINE.name + f".bak_{TODAY}_pre_{SCRIPT[:-3]}")
    if not bak.exists():
        shutil.copy2(SPINE, bak)
        print(f"\n  backed up -> {bak.name}")

    part = SPINE.with_suffix(SPINE.suffix + ".part")
    with open(part, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in live + rows_new:
            w.writerow({k: r.get(k, "") for k in fields})
    after_stat = SPINE.stat()
    if (after_stat.st_mtime_ns, after_stat.st_size) != \
            (before_stat.st_mtime_ns, before_stat.st_size):
        part.unlink(missing_ok=True)
        raise SystemExit("  the spine moved between read and rename - another "
                         "agent is writing it. REFUSED, nothing changed.")
    os.replace(part, SPINE)

    for _k, _s, prefix, eid in minted:
        ids_mod.adopt_existing(prefix, [eid])
    print(f"  registered {len(minted)} id(s) with cedar_ids.adopt_existing so "
          f"a later mint cannot collide")

    # ---- verify by RE-READING, never from the run log ---------------------
    back = read_csv(SPINE)
    got = {(r.get("tribe_id") or ""): r for r in back}
    for _k, _s, _p, eid in minted:
        if eid not in got:
            raise SystemExit(f"  {eid} is NOT in the file after the write. "
                             f"Restore from {bak.name}.")
    print(f"\n  re-read from disk: {len(back):,} entities "
          f"({len(back) - len(live):+d}), {len(list(back[0]))} columns")
    for _k, _s, _p, eid in minted:
        print(f"    {eid}  {got[eid]['canonical_name']}  "
              f"[{got[eid]['entity_class']}]")

    print("\n  FOLLOW-UP, deliberately NOT done here: entity_relationships.csv "
          "carries 29\n  tribe-side `affiliated_with` rows naming the TDHE "
          "'Bristol Bay HA' with a BLANK\n  target_entity_id and the note "
          "'pending a spine entity'. The entity now exists.\n  Filling a blank "
          "target is a NEW link, not a repoint, and belongs to script 97.")
    print("\n  next:  py -3 code/427_repoint_bristol_bay_attributions.py --check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
