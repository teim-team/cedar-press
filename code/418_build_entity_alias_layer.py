#!/usr/bin/env python3
"""
Cedar Press - 418: make the alias layer first-class. IN PLACE, ADDITIVE.

THE FILE THIS BUILD TREATS AS THE TRUTH
---------------------------------------
    data/clean/entity_aliases.csv    - read, enriched in place, re-read
    data/spine/cedar_entity_spine.csv          - the entity universe
    data/clean/federal_recognition_roster.csv  - the RENAME evidence, with FR
                                                 citations

    Elijah, 2026-08-26: "Three Affiliated Tribes is also MHA is also Mandan,
                         Hidatsa and Arikara Nation."

WHY THIS IS THE HIGHEST-LEVERAGE PIECE OF THE IDENTITY LAYER
------------------------------------------------------------
Nearly every misattribution this project has paid for was a NAME problem, not
an id problem: `NATIONAL EDUCATION ASSOCIATION` -> National INDIAN Education
Association because `core()` folded the word that distinguishes; `CHICKASAW
NATION` -> Chickasaw Children's Village carrying $2.8B onto a school; "Boys &
Girls Clubs of Wichita Falls" -> the Wichita Tribe; 7,160 Native assistance
recipients dropped by an exact-string filter because one federal rendering is
missing a space. An id cannot fix any of those. **A complete, typed alias layer
can**, and it is the thing a matcher should consult instead of guessing.

MEASURED BEFORE THIS RUN (code/415_audit_identity_layer.py)
-----------------------------------------------------------
    alias rows                                       5,943
    distinct entities covered                        1,310
    spine entities                                   1,534
    spine entities with NO alias row at all            224   (179 NHO, 45 INF)
    columns 100% blank        start_date, end_date, first_observed_date,
                              last_observed_date
    declared ALIAS_TYPES never used                      9   incl. former_legal

and the owner's own example, verbatim from the file: **`TRBF-MHATAT-00` carries
seven alias rows and not one is "MHA" or "Mandan, Hidatsa and Arikara Nation".**
Four of the seven are machine permutations of "Three Affiliated" at confidence
0.40. The nation's own name for itself is absent while four strings nobody uses
are present.

WHAT THIS ADDS
--------------
  A. COVERAGE. A row for every spine entity that had none - canonical name,
     the pipe-delimited `aliases` cell, and `fr_official_name` where present.
  B. RENAMES, WITH THE CITATION. `federal_recognition_roster.csv` carries
     `previously_listed_as` on 1,436 rows keyed to 172 entities and 203 distinct
     former names, each with an `fr_citation`. **A RENAME NEVER MINTS A NEW
     ID.** "Tolowa Dee-ni' Nation (previously listed as the Smith River
     Rancheria)" and "Yuhaaviatam of San Manuel Nation (previously listed as
     San Manuel Band of Mission Indians)" are the SAME entity under a new name.
     These land as `former_legal`, `alias_role = historical`, tier A, with the
     FR citation in `source_id` and the earliest publication date in `end_date`.
     Nine of the ten `full_form_federal_filing` traps this project has hit came
     from not knowing a former name; this is the fix.
  C. TYPING. `alias_role` (current / historical / unknown) on every row, from
     `cedar_domain.alias_type_role` - so a matcher can prefer a current name
     and still RESOLVE a historical one, which is exactly what a rename
     requires. `alias_type_normalized` maps every spelling onto the one
     vocabulary via `cedar_domain.canonical_alias_type`.
  D. THE OWNER'S NAMED CASE, cited to him. "MHA" and "Mandan, Hidatsa and
     Arikara Nation" are added for `TRBF-MHATAT-00` with
     `source_system = elijah_ruling` and the sentence quoted verbatim. **An
     owner statement is a ruling and this project already treats it as tier A
     evidence.** Nothing else is invented: no alias is generated here.

WHAT IT DOES NOT DO
-------------------
  * It does NOT fill the four blank date columns with the build date. A build
    date in an observation column is defect class 2 and it is how 38 collection
    descriptors got `vintage = 2026-08-26`. **Blank means NOT RECORDED**, and
    the codebook says so. `end_date` is written ONLY where an FR publication
    date evidences it.
  * It does NOT delete, retype or re-tier a single existing row.
  * It does NOT touch `entity_relationships.csv`.

ORDERING - CLASS 6, DECLARED BECAUSE THE DETECTOR CANNOT INFER IT
-----------------------------------------------------------------
    97_build_aliases_and_relationships.py   FULL REBUILD, runs FIRST
    418_build_entity_alias_layer.py         IN-PLACE ENRICHER, RUNS LAST

A `.bak_<date>_pre_418_build_entity_alias_layer` file beside
`entity_aliases.csv` is the signal that the enricher has touched it. **Re-run
418 after any run of 97**, or 97 reverts every row and column added here -
which is exactly what `133 build` did to `168`'s 931 entity links, four minutes
after they were written, while printing a larger row count that read as
progress.

    py -3 code/418_build_entity_alias_layer.py            # dry run
    py -3 code/418_build_entity_alias_layer.py --apply
"""

import csv
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import cedar_domain as D                                    # noqa: E402
import cedar_ids as IDS                                     # noqa: E402
from cedar_keys import normalise                            # noqa: E402

CEDAR = Path(__file__).resolve().parent.parent
ALIAS = CEDAR / "data" / "clean" / "entity_aliases.csv"
SPINE = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"
FR = CEDAR / "data" / "clean" / "federal_recognition_roster.csv"
TODAY = date.today().isoformat()
SCRIPT = "418_build_entity_alias_layer"
BAK = ALIAS.with_name(ALIAS.name + f".bak_{TODAY}_pre_{SCRIPT}")

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

NEW_COLUMNS = ["alias_type_normalized", "alias_role", "alias_layer_basis"]

BLANK_DATE_NOTE = (
    "start_date / end_date / first_observed_date / last_observed_date are "
    "BLANK unless a source dates them. BLANK MEANS NOT RECORDED, never 'the "
    "name was never used'. They are deliberately NOT filled with the build "
    "date: a build date in an observation column is what set 38 collection "
    "descriptors to vintage 2026-08-26.")

OWNER_ALIASES = [
    # (entity_id, alias_name, alias_type, the owner's words)
    ("TRBF-MHATAT-00", "MHA", "acronym",
     'Elijah, 2026-08-26: "Three Affiliated Tribes is also MHA is also '
     'Mandan, Hidatsa and Arikara Nation."'),
    ("TRBF-MHATAT-00", "Mandan, Hidatsa and Arikara Nation", "common",
     'Elijah, 2026-08-26: "Three Affiliated Tribes is also MHA is also '
     'Mandan, Hidatsa and Arikara Nation."'),
    # ---------------------------------------------------------------------
    # A SURFACE FORM THAT COST A NEAR-DUPLICATE ENTITY, 2026-08-27.
    #
    # The owner-rulings agent (scripts 433-440) had `Hana Group` on a list of
    # 15 possible SPINE GAPS. Fourteen resolved. The fifteenth did not, and
    # the honest reading of "no_spine_match" would have been `allocate
    # ("CEDAR-ENT")` - **minting a SECOND Native Hawaiian Organization for an
    # organisation Cedar already holds.** That is the one-identifier-to-many-
    # entities defect, self-inflicted, and it would have looked like progress.
    #
    # It is not a spine gap. `NHO-HUIOHA-00` (Hui O Hana Pono) already carries
    # four alias rows including `The Hana Group` at tier A, and
    # `nho_register.csv::N-0019` records the same two forms. The resolver
    # missed on ONE WORD: every recorded form carries a leading "The" and the
    # owner wrote it without.
    #
    # **A MISSING SURFACE FORM IS INDISTINGUISHABLE FROM A MISSING ENTITY, AND
    # THE CHEAPER ERROR IS TO MINT.** That is the whole argument for the alias
    # layer being first-class rather than a lookup table, and it arrived as a
    # live near-miss from another agent rather than as a hypothetical.
    # ---------------------------------------------------------------------
    ("NHO-HUIOHA-00", "Hana Group", "shortened",
     'Surface form requested 2026-08-27 by the owner-rulings agent (433-440) '
     'after `Hana Group` returned no_spine_match while `The Hana Group` '
     'resolves. Evidenced by data/clean/nho_register.csv N-0019 aliases = '
     '"The Hana Group|Hui o Hana Pono dba The Hana Group" and by the spine\'s '
     'own aliases cell on NHO-HUIOHA-00. NOT a new entity.'),
]


def g(r, c):
    return (r.get(c) or "").strip()


def read(p):
    if not Path(p).exists():
        return [], []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        return list(rd), list(rd.fieldnames or [])


def main():
    apply = "--apply" in sys.argv
    alias, cols = read(ALIAS)
    spine, _ = read(SPINE)
    n_before, cols_before = len(alias), list(cols)
    print(f"alias layer: {n_before:,} rows, {len(cols)} columns")
    print(f"spine:       {len(spine):,} entities")

    meta = {g(r, "tribe_id"): r for r in spine}
    covered = {g(r, "entity_id") for r in alias if g(r, "entity_id")}
    # (entity, normalised name) already present - never write a duplicate
    have = {(g(r, "entity_id"), normalise(g(r, "alias_name"))) for r in alias}

    stats = Counter()

    # ------------------------------------------------- C. type every existing
    for r in alias:
        t = g(r, "alias_type")
        norm_t = D.canonical_alias_type(t)
        if not norm_t:
            stats["existing_row_with_UNRECOGNISED_alias_type"] += 1
        r["alias_type_normalized"] = norm_t or t
        r["alias_role"] = D.alias_type_role(norm_t or t)
        r["alias_layer_basis"] = r.get("alias_layer_basis") or BLANK_DATE_NOTE
        stats[f"role_{r['alias_role']}"] += 1

    added = []

    def add(entity_id, name, atype, source_system, verification, tier,
            confidence, source_id, basis, end_date=""):
        key = (entity_id, normalise(name))
        if not name or key in have:
            return False
        have.add(key)
        norm_t = D.canonical_alias_type(atype) or atype
        row = {c: "" for c in cols_before}
        row.update({
            "entity_id": entity_id,
            "alias_name": name,
            "normalized_alias": normalise(name),
            "alias_type": norm_t,
            "alias_type_normalized": norm_t,
            "alias_role": D.alias_type_role(norm_t),
            "source_system": source_system,
            "verification_status": verification,
            "tier": tier,
            "confidence": confidence,
            "source_id": source_id,
            "created_at": TODAY,
            "end_date": end_date,
            "alias_layer_basis": basis,
        })
        added.append(row)
        return True

    # ---------------------------------------------------------- A. coverage
    missing = [r for r in spine if g(r, "tribe_id") not in covered]
    print(f"\n[A] spine entities with NO alias row: {len(missing)}")
    by_class = Counter(g(r, "entity_class") for r in missing)
    for k, v in by_class.most_common():
        print(f"      {v:>5}  {k}")
    for r in missing:
        t = g(r, "tribe_id")
        # ------------------------------------------------------------------
        # REFUSED, AND THE REFUSAL IS THE POINT.
        #
        # 45 of the 224 uncovered entities are the class
        # `Individually Native-owned business`, and
        # `cedar_domain.INDIVIDUAL_NATIVE_WITHHELD_FIELDS` withholds
        # `canonical_name`, `legal_business_name`, `dba_name` and `owner_name`
        # for every one of them absent recorded OPTED_IN consent -
        # `consent_status` is `NOT_ASKED` on all 45.
        #
        # `entity_aliases.csv` is a NAME INDEX in `data/clean`. Minting a sole
        # proprietor's legal name into it would take a name the publication
        # policy withholds and put it in the one table whose whole purpose is
        # to make names findable, under a different column heading. That is
        # the D&B carve-out defeated by a rename, and it is the same shape as
        # the UEI one-hop: SAM's public search resolves the identifier to the
        # person, so the identifier is withheld; a name index resolves the
        # name to the entity, so the name must be too.
        #
        # These entities are not left unresolvable - the spine still carries
        # their names for internal matching. What they are denied is a row in
        # a published index. The refusal is COUNTED and NAMED here rather than
        # being a silent skip, because this project counts what it drops.
        # ------------------------------------------------------------------
        if g(r, "entity_class") == D.INDIVIDUAL_NATIVE_CLASS:
            stats["REFUSED_individual_native_privacy"] += 1
            continue
        if add(t, g(r, "canonical_name"), "legal", "cedar_spine",
               "SPINE_CANONICAL", "A", "0.99",
               "cedar_entity_spine.csv::canonical_name",
               "Coverage row: this entity had no alias at all before "
               "code/418. " + BLANK_DATE_NOTE):
            stats["added_canonical_coverage"] += 1
        if g(r, "fr_official_name"):
            if add(t, g(r, "fr_official_name"), "legal", "federal_register",
                   "OFFICIAL", "A", "0.98",
                   "cedar_entity_spine.csv::fr_official_name",
                   "The Federal Register's own name for this entity. "
                   + BLANK_DATE_NOTE):
                stats["added_fr_official"] += 1
        for a in g(r, "aliases").split("|"):
            a = a.strip()
            if a and add(t, a, "common", "cedar_spine", "RECORDED", "A",
                         "0.90", "cedar_entity_spine.csv::aliases",
                         "Recorded on the spine row. " + BLANK_DATE_NOTE):
                stats["added_from_spine_aliases_cell"] += 1

    # -------------------------------------------------- B. renames from the FR
    fr, _ = read(FR)
    renames = defaultdict(dict)      # entity -> former_name -> (cite, date)
    unkeyed = 0
    for r in fr:
        prev, e = g(r, "previously_listed_as"), g(r, "tribe_id")
        if not prev:
            continue
        if not e:
            unkeyed += 1
            continue
        cite, pub = g(r, "fr_citation"), g(r, "publication_date")
        cur = renames[e].get(prev)
        # Keep the EARLIEST notice: the first list that carried the
        # parenthetical is the one that dates the change.
        if cur is None or (pub and cur[1] and pub < cur[1]):
            renames[e][prev] = (cite, pub)
    print(f"\n[B] Federal Register renames: {sum(len(v) for v in renames.values())} "
          f"(entity, former name) pairs over {len(renames)} entities; "
          f"{unkeyed} roster rows carry a former name but no entity id")
    for e, names in renames.items():
        if e not in meta:
            stats["rename_for_an_entity_not_in_the_spine"] += 1
            continue
        for prev, (cite, pub) in names.items():
            prev_clean = prev.rstrip(") ").strip()
            if add(e, prev_clean, "former_legal", "federal_register",
                   "OFFICIAL", "A", "0.98",
                   cite or "federal_recognition_roster.csv",
                   f"FORMER LEGAL NAME. The Federal Register list carries "
                   f"'(previously listed as {prev_clean})' against this "
                   f"entity at {cite or 'an uncited notice'}"
                   f"{', published ' + pub if pub else ''}. **A RENAME DOES "
                   f"NOT MINT A NEW ID** - same entity, new name, one Cedar "
                   f"id, and the old name must keep resolving forever. "
                   + BLANK_DATE_NOTE,
                   end_date=pub):
                stats["added_former_legal"] += 1

    # ------------------------------------------------- D. the owner's example
    print("\n[D] owner-named aliases")
    for e, name, atype, quote in OWNER_ALIASES:
        if e not in meta:
            print(f"      SKIP {e} - not in the spine")
            continue
        ok = add(e, name, atype, "elijah_ruling", "RULED", "A", "0.99",
                 "AGENTS.md / owner statement 2026-08-26",
                 f"{quote} An owner statement is a RULING and this project "
                 f"already treats one as tier-A evidence. Measured before "
                 f"this run: {e} carried seven alias rows and NOT ONE was "
                 f"'MHA' or 'Mandan, Hidatsa and Arikara Nation' - four of "
                 f"the seven were machine permutations of 'Three Affiliated' "
                 f"at confidence 0.40. " + BLANK_DATE_NOTE)
        print(f"      {'added' if ok else 'already present'}: "
              f"{e} <- {name!r} ({atype})")
        if ok:
            stats["added_owner_ruled"] += 1

    # -------------------------------------------------------------- mint ids
    if added:
        new_ids = IDS.allocate("CEDAR-ALIAS", len(added),
                               note=f"code/{SCRIPT}.py {TODAY}")
        for r, i in zip(added, new_ids):
            r["alias_id"] = i

    print()
    for k, v in sorted(stats.items()):
        print(f"  {k:46s} {v:>6,}")
    print(f"\n  rows to add: {len(added):,}  ->  {n_before + len(added):,}")

    out_cols = cols_before + [c for c in NEW_COLUMNS if c not in cols_before]
    assert all(c in out_cols for c in cols_before), "a column would be LOST"
    ids_after = {g(r, "entity_id") for r in alias} | {
        g(r, "entity_id") for r in added}
    refused_n = stats["REFUSED_individual_native_privacy"]
    print(f"  entities covered after: {len(ids_after):,} of {len(meta):,} "
          f"(+{refused_n} REFUSED on privacy, not missed - see the block in "
          f"section A)")
    assert len(ids_after) + refused_n == len(meta), (
        "coverage does not close: every spine entity must be covered or "
        "explicitly refused")

    if not apply:
        print("\nDRY RUN - nothing written. Re-run with --apply.")
        return

    if not BAK.exists():
        BAK.write_bytes(ALIAS.read_bytes())
        print(f"\nbacked up -> {BAK.name}")
    else:
        print(f"\nbackup already exists, kept: {BAK.name}")

    tmp = ALIAS.with_suffix(".csv.part")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, out_cols, extrasaction="ignore")
        w.writeheader()
        for r in alias + added:
            w.writerow({c: r.get(c, "") for c in out_cols})
    tmp.replace(ALIAS)

    # Concurrency rule 4: verify by RE-READING, not by trusting the run log.
    back, back_cols = read(ALIAS)
    lost = [c for c in cols_before if c not in back_cols]
    assert not lost, f"COLUMNS LOST: {lost}"
    assert len(back) == n_before + len(added), \
        f"expected {n_before + len(added)}, read {len(back)}"
    assert len({g(r, 'alias_id') for r in back}) == len(back), \
        "alias_id is not unique on re-read"
    cov = len({g(r, "entity_id") for r in back if g(r, "entity_id")})
    print(f"re-read OK: {len(back):,} rows ({n_before:,} + {len(added):,}), "
          f"{len(cols_before)} -> {len(back_cols)} columns, 0 lost, "
          f"alias_id unique")
    print(f"  entities covered      {cov:,} of {len(meta):,}")
    print(f"  former_legal rows     "
          f"{sum(1 for r in back if g(r, 'alias_type') == 'former_legal'):,}")
    print(f"  role=historical       "
          f"{sum(1 for r in back if g(r, 'alias_role') == 'historical'):,}")


if __name__ == "__main__":
    main()
