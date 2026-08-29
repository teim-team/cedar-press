#!/usr/bin/env python3
"""
Cedar Press - 416: reconcile the spine's two id columns. IN PLACE, ADDITIVE.

THE FILE THIS BUILD TREATS AS THE TRUTH
---------------------------------------
    data/spine/cedar_entity_spine.csv    - read, enriched in place, re-read

WHAT WAS WRONG
--------------
`cedar_entity_spine.csv` carries `tribe_id` AND `cedar_entity_id` and they read
like two ids for one concept. Measured by `code/415_audit_identity_layer.py`:

    rows                                          1,534
    tribe_id blank                                    0     distinct 1,534
    cedar_entity_id blank                           525     distinct 1,009
    rows where the two are EQUAL                      0
    cedar_entity_id values that are a Cedar id        0

**They are not two ids for one concept. They are two different concepts under
one misleading name.** `cedar_entity_id` holds `T-0001`, `A-0001`, `N-...`,
`I-...` - the `Entity_ID` column of the upstream `entity_master.csv` register -
and scripts 52, 61, 66 and 163 use it as a DEDUPE KEY against that register
(`if c["Entity_ID"] in have_ceid: skip`). It is a FOREIGN identifier.

Meanwhile `data/clean/entity_evidence_profile.csv` and all ten
`data/clean/views/v_*.csv` carry a column ALSO called `cedar_entity_id` that
holds `TRBF-CRDALN-00` - the canonical id. **One column name, two vocabularies
that do not intersect at all, so a join between them returns silence rather
than an error.** That is the same failure shape as `tribe_id` carrying two
identifier schemes in the assistance table and `extent_competed` carrying two
vocabularies, and it is fixed the same way those were: **DECLARE THE SEAM IN A
COLUMN.**

WHAT THIS SCRIPT DOES - AND WHAT IT DELIBERATELY DOES NOT
---------------------------------------------------------
DOES (additive; no existing column is altered, reordered or removed):

  entity_master_register_id          a copy of `cedar_entity_id` under an
                                     HONEST name. 1,009 rows.
  entity_master_register_id_basis    the sentence saying what it is and which
                                     scripts dedupe on it.
  cedar_entity_id_scheme             per row: ENTITY_MASTER_REGISTER_FK /
                                     ABSENT. Same shape as
                                     `tribe_id_scheme_resolved` in
                                     federal_funding_transactions.csv, which
                                     is the precedent this follows.
  canonical_entity_id_column         the literal string "tribe_id" on every
                                     row. One cell answers "which column is
                                     the key" for any agent reading ONE ROW IN
                                     ISOLATION - which is the owner's stated
                                     criterion.
  constituent_band_of_entity_id      for CNSF-/CNSS- ids, the umbrella entity,
  constituent_band_of_basis          DERIVED FROM THE ID and then VERIFIED
                                     against the spine. Never written where
                                     the umbrella is absent.

DOES NOT: rename `cedar_entity_id`. That is **BLOCKED-ON-CONSUMERS** and the
consumers are enumerated, by evidence, from a full cell-by-cell value scan in
415:

    data/spine/cedar_entity_spine.csv      cedar_entity_id      1,009 cells
    data/clean/entity_name_harvest.csv     matched_entity_id    2,033
    data/clean/intertribal_memberships.csv org_id                 891
    data/clean/nho_ito_spine_crosswalk.csv proposed_id            265
    data/clean/nho_register.csv            proposed_id            210
    data/clean/intertribal_orgs.csv        proposed_id             55
  + code/52, code/61, code/66, code/163 read the column by name
  + code/01 and code/41 write it and are BOTH on the never-run list

and **ten tables were SKIPPED_TOO_LARGE by that scan**, so the enumeration is
not closed. `327_migrate_class7_keys_to_digests.py` aborts a whole key
migration on ONE undeclared location; that discipline is inherited here. A
half-migrated identity layer is worse than none - the bad key at least fails
uniformly.

DOES NOT: touch `tribe_id`, any hierarchy column, or any existing value.
DOES NOT: apply the assistance NEID crosswalk. Scripts 152 and 24 decline in
writing - "the NEID crosswalk is a ruling, not a computation" - and 122 of its
344 candidates rest on the containment matcher AGENTS.md forbids from keying a
dollar. That refusal is honoured.

SAFETY
------
Backup tagged with the FULL SCRIPT NAME (concurrency rule 1), `.part` then
rename (a completion must not be indistinguishable from an interruption), the
row count and the full pre-existing column list asserted before writing, and
the file RE-READ FROM DISK afterwards (concurrency rule 4 - idempotence is not
enough when someone else is writing). Re-running is a no-op that reports it.

    py -3 code/416_reconcile_spine_id_columns.py            # dry run
    py -3 code/416_reconcile_spine_id_columns.py --apply
"""

import csv
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import cedar_ids as IDS                                     # noqa: E402

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
SPINE = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"
TODAY = date.today().isoformat()
SCRIPT = "416_reconcile_spine_id_columns"
BAK = SPINE.with_name(SPINE.name + f".bak_{TODAY}_pre_{SCRIPT}")
REVIEW = CEDAR / "review" / f"spine_id_reconciliation_{TODAY}.csv"

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

LEGACY_RE = re.compile(r"^[TANIE](?:P)?-\d{3,5}$")

NEW_COLUMNS = [
    "canonical_entity_id_column",
    "cedar_entity_id_scheme",
    "entity_master_register_id",
    "entity_master_register_id_basis",
    "constituent_band_of_entity_id",
    "constituent_band_of_basis",
]

REGISTER_BASIS = (
    "entity_master.csv::Entity_ID - the UPSTREAM register's identifier, NOT a "
    "Cedar id. Carried in the spine column named `cedar_entity_id`, which is "
    "a misnomer: in data/clean that same column name holds the CANONICAL id "
    "(TRBF-...). Scripts 52/61/66/163 dedupe against this value. Renaming the "
    "column is BLOCKED-ON-CONSUMERS - see the docstring of "
    "code/416_reconcile_spine_id_columns.py and docs/CEDAR_ID_SYSTEM.md.")

BAND_BASIS = (
    "Derived from the constituent-band id itself (CNSF-<UMBRELLA>-<BAND>) and "
    "then VERIFIED present in the spine; never written where the umbrella is "
    "absent. cedar_domain.NEVER_OWNERSHIP contains `constituent_band_of`, so "
    "this edge carries NO dollar in either direction. It exists so the "
    "CONSTITUENT_BAND_VS_UMBRELLA_TRIBE rows in "
    "review/identifier_one_to_many_defects_2026-08-26.csv can be TYPED rather "
    "than guessed at.")


def g(r, c):
    return (r.get(c) or "").strip()


def main():
    apply = "--apply" in sys.argv
    with open(SPINE, encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        cols = list(rd.fieldnames or [])
        rows = list(rd)

    n_before = len(rows)
    print(f"spine: {n_before:,} rows, {len(cols)} columns")

    if "tribe_id" not in cols:
        raise SystemExit("FATAL: spine has no `tribe_id` column. Refusing - "
                         "a coverage computation must RAISE on a missing "
                         "column, never write a plausible zero.")

    already = [c for c in NEW_COLUMNS if c in cols]
    if already:
        print(f"  already present: {', '.join(already)} "
              f"- this is a RE-RUN and it is a no-op by design")

    ids = {g(r, "tribe_id") for r in rows}
    audit, stats = [], {
        "register_id_present": 0, "register_id_absent": 0,
        "band_ids": 0, "band_umbrella_resolved": 0,
        "band_umbrella_NOT_in_spine": 0,
        "register_id_that_is_a_cedar_id": 0,
        "register_id_of_unexpected_shape": 0,
    }

    for r in rows:
        t = g(r, "tribe_id")
        reg = g(r, "cedar_entity_id")

        r["canonical_entity_id_column"] = "tribe_id"

        if reg:
            stats["register_id_present"] += 1
            if IDS.is_canonical_entity_id(reg):
                # Would mean the column had started carrying Cedar ids too.
                stats["register_id_that_is_a_cedar_id"] += 1
                scheme = "CANONICAL_CEDAR_ENTITY_ID"
            elif LEGACY_RE.match(reg):
                scheme = "ENTITY_MASTER_REGISTER_FK"
            else:
                stats["register_id_of_unexpected_shape"] += 1
                scheme = "UNRECOGNISED_SHAPE"
                audit.append({"tribe_id": t, "finding": "UNRECOGNISED_SHAPE",
                              "detail": reg})
            r["entity_master_register_id"] = reg
            r["entity_master_register_id_basis"] = REGISTER_BASIS
        else:
            stats["register_id_absent"] += 1
            scheme = "ABSENT"
            r["entity_master_register_id"] = ""
            r["entity_master_register_id_basis"] = ""
        r["cedar_entity_id_scheme"] = scheme

        # CNSF- bands sit under a FEDERALLY recognised tribe, CNSS- bands
        # under a STATE-recognised one. Try the prefix the class implies
        # first, then the other, and record which candidates were tried -
        # a blank with no candidate list is indistinguishable from a blank
        # nobody looked at.
        parsed = IDS.parse_entity_id(t)
        order = (("TRBS", "TRBF") if parsed and parsed["prefix"] == "CNSS"
                 else ("TRBF", "TRBS"))
        cands = [IDS.umbrella_id_for_band(t, p) for p in order]
        cands = [c for c in cands if c]
        umb = next((c for c in cands if c in ids), None if cands else None)
        if not cands:
            r["constituent_band_of_entity_id"] = ""
            r["constituent_band_of_basis"] = ""
            continue
        stats["band_ids"] += 1
        if umb:
            stats["band_umbrella_resolved"] += 1
            r["constituent_band_of_entity_id"] = umb
            r["constituent_band_of_basis"] = BAND_BASIS
            declared = g(r, "parent_entity_id")
            if declared and declared != umb:
                audit.append({"tribe_id": t,
                              "finding": "BAND_UMBRELLA_DISAGREES_WITH_PARENT",
                              "detail": f"derived={umb} parent={declared}"})
        else:
            stats["band_umbrella_NOT_in_spine"] += 1
            r["constituent_band_of_entity_id"] = ""
            r["constituent_band_of_basis"] = ""
            audit.append({"tribe_id": t,
                          "finding": "BAND_UMBRELLA_NOT_IN_SPINE",
                          "detail": f"candidates tried: {', '.join(cands)} - "
                                    f"none in the spine, so LEFT BLANK. Blank "
                                    f"means NOT ESTABLISHED, never NO "
                                    f"UMBRELLA. This is a spine gap: the "
                                    f"umbrella entity does not exist as a "
                                    f"row."})

    print()
    for k, v in stats.items():
        print(f"  {k:38s} {v:>6,}")
    print()
    if audit:
        print(f"  {len(audit)} finding(s) staged to "
              f"{REVIEW.relative_to(CEDAR)}:")
        for a in audit[:12]:
            print(f"    {a['tribe_id']:26s} {a['finding']}  {a['detail'][:70]}")

    out_cols = cols + [c for c in NEW_COLUMNS if c not in cols]
    assert len(rows) == n_before, "row count moved - refusing to write"
    assert all(c in out_cols for c in cols), "a column would be LOST"

    if not apply:
        print("\nDRY RUN - nothing written. Re-run with --apply.")
        return

    if audit:
        REVIEW.parent.mkdir(parents=True, exist_ok=True)
        tmp = REVIEW.with_suffix(".csv.part")
        with open(tmp, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, ["tribe_id", "finding", "detail"])
            w.writeheader()
            w.writerows(audit)
        tmp.replace(REVIEW)

    if not BAK.exists():
        BAK.write_bytes(SPINE.read_bytes())
        print(f"\nbacked up -> {BAK.name}")
    else:
        print(f"\nbackup already exists, kept: {BAK.name}")

    tmp = SPINE.with_suffix(".csv.part")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, out_cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in out_cols})
    tmp.replace(SPINE)

    # Concurrency rule 4: verify by RE-READING, not by trusting the run log.
    with open(SPINE, encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        back_cols = list(rd.fieldnames or [])
        back = list(rd)
    lost = [c for c in cols if c not in back_cols]
    assert not lost, f"COLUMNS LOST: {lost}"
    assert len(back) == n_before, f"rows {n_before} -> {len(back)}"
    filled = sum(1 for r in back if g(r, "entity_master_register_id"))
    bands = sum(1 for r in back if g(r, "constituent_band_of_entity_id"))
    print(f"re-read OK: {len(back):,} rows, {len(cols)} -> {len(back_cols)} "
          f"columns, 0 lost")
    print(f"  entity_master_register_id populated   {filled:,}")
    print(f"  constituent_band_of_entity_id written {bands:,}")
    print(f"  canonical_entity_id_column            "
          f"{sum(1 for r in back if g(r, 'canonical_entity_id_column')):,}")


if __name__ == "__main__":
    main()
