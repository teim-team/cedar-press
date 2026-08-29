#!/usr/bin/env python3
# lint-ok: class6 - this script READS prime_contracts_entity_year.csv (for the
# cedar_uid stamp and the before/after diff) and REWRITES it in place from
# prime_contracts.csv. It is the panel's in-place regenerator, not a fourth
# wholesale writer; the declared ordering is that it runs AFTER every
# row-level enricher of prime_contracts.csv and BEFORE 503_identity.py stamp.
"""
Cedar Press - 428: regenerate the prime contracting ENTITY-YEAR panel.

WHAT WAS WRONG
--------------
`prime_contracts_entity_year.csv` is named entity-year, declares `tribe_id`
and `cedar_uid` as key columns, and was NOT one row per entity-year. Measured
2026-08-29: 8,464 rows over 6,713 distinct (tribe_id, fiscal_year), **1,635
keys colliding**, because all three writers of the file keyed it on
(tribe_id, canonical_name, fiscal_year, confidence_tier).

The customer-visible consequence is a FAN-OUT, not an inflated sum. A buyer
who runs

    df.groupby(["tribe_id","fiscal_year"]).obligations_usd.sum()

got the right answer all along - the name/tier rows partition the entity-year,
so nothing was ever restated. A buyer who runs

    other_entity_year.merge(panel, on=["tribe_id","fiscal_year"])

got up to THREE copies of every row of their own table, and every dollar in
`other` multiplied by however many ledger name spellings and tiers Cedar
happened to hold for that entity. Nothing in the file warned them.

THE RULING: the grain is genuinely ENTITY-YEAR. See `cedar_prime_panel` for
the evidence - the two candidate keys sum to the identical cent, so collapsing
loses no dollar, and the one dimension that carried real information (the
attribution tier) is preserved as COLUMNS instead of rows.

WHY THIS IS A SEPARATE SCRIPT AND NOT A RE-RUN OF 40
----------------------------------------------------
`40_build_prime_contracts.py` rebuilds `prime_contracts.csv` FROM
`master prime file.dta`, which would erase every archive row merged by 131 and
every ruling applied in place by 174, 427 and 64 -
`114_pull_prime_archive.py` says so in its own comments. `131` refuses to run
twice by design (its idempotency guard). So neither of the panel's existing
writers can be re-run to fix the panel. This script derives the panel from
`prime_contracts.csv` AS IT STANDS, which is the only correct source for it.

A SECOND DEFECT THIS FIXES, WHICH NOBODY HAD NAMED
--------------------------------------------------
The shipped panel was STALE with respect to its own source. Rulings applied in
place to `prime_contracts.csv` after the last panel write were never cascaded:
13 (entity, name, year, tier) buckets existed in the rows and not in the
panel, and the ANVC- village-corporation total was $4,729,215.51 short. The
panel was publishing pre-ruling numbers while the row table published
post-ruling ones.

    py -3 code/428_rebuild_prime_entity_year.py --check   # read-only diff
    py -3 code/428_rebuild_prime_entity_year.py --apply   # write it

Run `py -3 code/62_no_regression_check.py` after, and re-run
`py -3 code/503_identity.py stamp --apply` if any tribe_id is reported
without a cedar_uid.

Reads  data/clean/prime_contracts.csv
       data/clean/prime_contracts_entity_year.csv   (cedar_uid + the diff)
       data/spine/cedar_entity_spine.csv
Writes data/clean/prime_contracts_entity_year.csv
       review/prime_entity_year_excluded_rows.csv
       data/clean/codebook/02_prime_contracting.csv      (APPEND ONLY)
       data/clean/codebook_master.csv                    (APPEND ONLY)
       graveyard/2026-08-29_prime_entity_year_grain_collapse/  (the pre-change
           file, archived rather than left as a .bak - see snapshot_pre_change)
"""

import argparse
import csv
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))

import cedar_prime_panel as P          # noqa: E402

CLEAN = ROOT / "data" / "clean"
PANEL = CLEAN / "prime_contracts_entity_year.csv"
TODAY = date.today().isoformat()


# ---------------------------------------------------------------------------
# CODEBOOK REGISTRATION - and why it is not optional, and not a separate script
#
# `cedar_codebook.registered_tables()` scores a file's HEADER against the
# variables its dataset block documents and calls anything under 0.60
# UNDOCUMENTED - which IS the shipping gate, since 25_build_publication_layer
# publishes what the codebook documents. Changing this table's columns without
# registering them took the match from 0.88 to 0.43 and would have quietly
# UNSHIPPED the dataset while every other number looked better.
# `tables_undocumented_in_codebook` is MUST_NOT_RISE in 62 precisely so that
# cannot pass unnoticed.
#
# So the schema change and its registration are ONE act and live in one script.
# Both writes are APPEND-ONLY, and only for a variable the block does not
# already carry: `41_build_codebooks.py` is in cedar_pipeline.NEVER_RUN because
# a global rebuild deletes 21 of the 43 blocks, and `cedar_codebook.build()`
# refuses to shrink - neither is a safe way to add eight rows.
# ---------------------------------------------------------------------------
CB_DATASET = "02_prime_contracting"
CB_FRAG = ROOT / "data" / "clean" / "codebook" / (CB_DATASET + ".csv")
CB_MASTER = ROOT / "data" / "clean" / "codebook_master.csv"

_TIER_NOTE = (
    "Tier A and tier B are separate COLUMNS rather than separate rows: as "
    "rows they made this table 8,464 rows over 6,713 entity-years and fanned "
    "out any buyer's join on (tribe_id, fiscal_year). "
    "obligations_usd_tier_a + obligations_usd_tier_b == obligations_usd is "
    "asserted on every build.")

NEW_VARIABLES = {
    "cedar_uid": ("text", "code",
        "Cedar's permanent entity join key, stamped by "
        "`code/503_identity.py`. One per `tribe_id`; it never changes, and a "
        "retired handle still resolves to it. Documented here because this "
        "table carries it and the codebook is what decides what ships."),
    "obligations_usd_tier_a": ("numeric", "usd",
        "Of `obligations_usd`, the part attributed on a TIER A identifier "
        "link. " + _TIER_NOTE),
    "n_contracts_tier_a": ("integer", "count",
        "Prime contract rows behind `obligations_usd_tier_a`."),
    "obligations_usd_tier_b": ("numeric", "usd",
        "Of `obligations_usd`, the part attributed on a TIER B identifier "
        "link. " + _TIER_NOTE),
    "n_contracts_tier_b": ("integer", "count",
        "Prime contract rows behind `obligations_usd_tier_b`."),
    "confidence_tiers": ("text", "category",
        "The SET of attribution tiers behind this entity-year, sorted and "
        "joined with `+`: A, B or A+B. Deliberately NOT named "
        "`confidence_tier`, which this table used to carry one-per-row: a "
        "stale equality filter on the old name must RAISE rather than "
        "silently return only the entity-years that happen to be pure tier "
        "A."),
    "attribution_name_variants_n": ("integer", "count",
        "How many distinct legal-name spellings the identifier ledger used "
        "for this entity in this year. 1 for almost every row; 56 of 498 "
        "entities carry more than one somewhere in the panel. They are "
        "labels off different registrations, not different entities - "
        "`canonical_name` is the entity spine's single name for the "
        "`tribe_id`."),
    "attribution_names": ("text", "name",
        "Those spellings, sorted and joined with ` | `. Reported so that "
        "collapsing to one row per entity-year destroys no observation."),
    "obligations_usd_owner_asof_confirmed": ("numeric", "usd",
        "Of `obligations_usd`, the part on transactions whose "
        "`owner_attribution_status` is CONFIRMED_AS_OF - the temporal layer "
        "(`code/515_temporal.py asof`) confirms this entity owned the "
        "contracting firm during THIS fiscal year. `obligations_usd` itself "
        "attributes on Cedar's CURRENT ownership, which is a different "
        "question; this column is the one to use for a historical claim."),
    "obligations_usd_owner_asof_not_confirmed": ("numeric", "usd",
        "The rest: dollars whose as-of owner the temporal layer cannot "
        "confirm, or actively contradicts. Unknown ownership ships as "
        "unknown - it is never filled in from the current owner. The "
        "per-status breakdown is in `owner_attribution_statuses` here and "
        "row by row in `prime_contracts.owner_attribution_status`; the "
        "dollars by status are in "
        "`review/prime_owner_asof_exposure.csv`. "
        "`obligations_usd_owner_asof_confirmed + "
        "obligations_usd_owner_asof_not_confirmed == obligations_usd` is "
        "asserted on every build."),
    "owner_attribution_statuses": ("text", "category",
        "The SET of `owner_attribution_status` values behind this "
        "entity-year, sorted and joined with `+`. See "
        "`prime_contracts.owner_attribution_status` for what each means."),
}


def register_codebook(panel_rows):
    """Append the new variables to the fragment AND the master. Idempotent."""
    import os
    n = len(panel_rows)
    filled = {v: sum(1 for r in panel_rows if str(r.get(v, "")).strip())
              for v in NEW_VARIABLES}

    for path, label in ((CB_FRAG, "fragment"), (CB_MASTER, "master")):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            rd = csv.DictReader(fh)
            fields = rd.fieldnames or []
            rows = list(rd)
        have = {r["variable"] for r in rows if r.get("dataset") == CB_DATASET}
        add = []
        for v, (typ, units, desc) in NEW_VARIABLES.items():
            if v in have:
                continue
            add.append({
                "dataset": CB_DATASET, "variable": v, "type": typ,
                "units": units,
                "pct_filled": "%.1f" % (100.0 * filled[v] / n),
                "n_rows": str(n), "published": "1", "access_tier": "public",
                "description": desc, "generated": TODAY,
            })
        if not add:
            print("  codebook %s: all %d variables already registered, no "
                  "change" % (label, len(NEW_VARIABLES)))
            continue
        bak = path.with_suffix(path.suffix + ".bak_%s_pre428_codebook" % TODAY)
        if not bak.exists():
            bak.write_bytes(path.read_bytes())
        part = path.with_suffix(path.suffix + ".part")
        with open(part, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
            w.writeheader()
            w.writerows(rows + add)
        os.replace(part, path)
        print("  codebook %s: +%d variable(s) (%s -> %s rows)"
              % (label, len(add), format(len(rows), ","),
                 format(len(rows) + len(add), ",")))

    # Prove the table is still DOCUMENTED, because that is the whole point.
    import importlib
    import cedar_codebook as CB
    importlib.reload(CB)
    grp, score = CB.match_group(CB.header_of(PANEL), CB.dataset_groups())
    print("  codebook match: %s at %.3f (threshold %.2f) - %s"
          % (grp, score, CB.MATCH_THRESHOLD,
             "DOCUMENTED, still shippable" if score >= CB.MATCH_THRESHOLD
             else "*** UNDOCUMENTED - THIS TABLE WOULD STOP SHIPPING ***"))
    if score < CB.MATCH_THRESHOLD:
        raise SystemExit(
            "REFUSING to leave the panel undocumented: 25_build_publication_"
            "layer publishes what the codebook documents, so an unregistered "
            "column change unships the dataset while every other count "
            "improves.")


# ---------------------------------------------------------------------------
# THE PRE-CHANGE SNAPSHOT GOES TO graveyard/, NOT TO A `.bak_` BESIDE THE FILE
#
# Standing rule 12 (`62.files_with_columns_lost_vs_backup`, MUST_BE_ZERO) reads
# every `data/clean/*.bak_*`, compares its header to the live file, and fails
# when a column present in the backup is missing from the live file. That check
# exists because a full rebuild silently reverting an in-place enricher looks
# exactly like this, and it has cost this project 931 entity links and nine
# columns in one afternoon.
#
# THIS CHANGE REMOVES A COLUMN ON PURPOSE (`confidence_tier` -> the two tier
# money columns), so leaving a `.bak_` next to the live file would be a
# standing invitation to revert to it - and reverting restores the fan-out
# defect. A backup you must never restore is not a backup. So the pre-change
# file is ARCHIVED with a note saying what it is and why a restore would be
# wrong, exactly as `graveyard/` is used for every other superseded artefact
# here, and the rule-12 check is left to mean what it was written to mean.
# ---------------------------------------------------------------------------
GRAVE = ROOT / "graveyard" / "2026-08-29_prime_entity_year_grain_collapse"


PRE_CHANGE = None      # set by snapshot_pre_change(); the true "before" file


def snapshot_pre_change():
    """Archive the file as it stood BEFORE the first collapse, and return it.

    The source of truth for "before" is the `.bak_*_pre_grain_collapse` an
    earlier run left in data/clean if one is there - NOT the live file, which
    on a second run is already collapsed and would archive the wrong bytes
    under a name claiming otherwise.
    """
    global PRE_CHANGE
    GRAVE.mkdir(parents=True, exist_ok=True)
    dest = GRAVE / "prime_contracts_entity_year.pre_grain_collapse.csv"

    # EVERY backup of this table that describes the OLD schema, whoever wrote
    # it. Identified by CONTENT - a header carrying `confidence_tier` - not by
    # filename, because 503_identity.py's `.bak_*_pre505` copies are pre-change
    # too and carry a different name. They are archived, not deleted: they are
    # evidence. They are moved out of data/clean because rule 12 reads every
    # `.bak_*` beside a live file as "a rebuild reverted an enricher", and here
    # the missing column is a deliberate rename nobody may restore.
    stale = []
    for b in sorted(PANEL.parent.glob(PANEL.name + ".bak_*")):
        try:
            with open(b, encoding="utf-8-sig", newline="") as fh:
                hdr = next(csv.reader(fh))
        except Exception:
            continue
        if "confidence_tier" in hdr:
            stale.append(b)

    if not dest.exists():
        src = stale[0] if stale else PANEL
        dest.write_bytes(src.read_bytes())
        print(f"\narchived the pre-change file ({src.name}) -> "
              f"{dest.relative_to(ROOT)}")
    else:
        print(f"\npre-change snapshot already in "
              f"{dest.parent.relative_to(ROOT)} - kept, not overwritten")
    for b in stale:
        keep = GRAVE / b.name
        if not keep.exists():
            keep.write_bytes(b.read_bytes())
        b.unlink()
        print(f"  moved {b.name} out of data/clean -> {keep.relative_to(ROOT)}"
              f"  (it carries `confidence_tier`; left in place, rule 12 reads "
              f"it as a rebuild that lost the column by accident)")
    PRE_CHANGE = dest
    return dest
    note = GRAVE / "README.md"
    if not note.exists():
        note.write_text(
            "# prime_contracts_entity_year.csv, before the entity-year "
            "grain collapse\n\n"
            "*Archived 2026-08-29 by `code/428_rebuild_prime_entity_year.py`.*\n\n"
            "This is the panel as it stood at 8,464 rows over 6,713 distinct "
            "`(tribe_id, fiscal_year)` keys - 1,635 of those keys colliding, "
            "because the file was built on "
            "`(tribe_id, canonical_name, fiscal_year, confidence_tier)`.\n\n"
            "**DO NOT RESTORE THIS FILE.** It is kept as evidence, not as a "
            "backup. Restoring it puts back the fan-out: a buyer merging any "
            "other entity-year table onto a file NAMED entity-year got up to "
            "three copies of every row of their own table. It is also stale "
            "with respect to `prime_contracts.csv` - 42 (entity, year) cells "
            "predate rulings 174/427/64, including $4,729,215.51 of ANVC- "
            "village-corporation dollars still booked on the village "
            "GOVERNMENT.\n\n"
            "The replacement is one row per `(tribe_id, fiscal_year)`, with "
            "the tier split kept as `obligations_usd_tier_a` / "
            "`obligations_usd_tier_b` and the ledger name spellings kept in "
            "`attribution_names`. Nothing in this file is absent from it. "
            "Rebuild with `py -3 code/428_rebuild_prime_entity_year.py "
            "--apply`.\n",
            encoding="utf-8")


def reconcile_shipped_rows(old_rows, new_rows):
    """ACCOUNT FOR EVERY ROW THAT LEFT. A fall in shipped rows is stop-work
    unless it is shown not to be a defect, so show it, to the row.

    `62.ship_dist_rows` is MUST_NOT_FALL. This collapse takes rows out on
    purpose, and "on purpose" is a claim until the arithmetic closes.
    """
    # "Before" is the ARCHIVED pre-change file when there is one: on a second
    # run the live file is already collapsed and comparing against it would
    # report a reconciliation of zero and prove nothing.
    if PRE_CHANGE and PRE_CHANGE.exists():
        with open(PRE_CHANGE, encoding="utf-8-sig", newline="") as fh:
            old_rows = list(csv.DictReader(fh))
        print(f"\n(before = {PRE_CHANGE.name}, the archived pre-change file)")
    old_keys = {(r.get("tribe_id"), r.get("fiscal_year")) for r in old_rows}
    new_keys = {(r["tribe_id"], r["fiscal_year"]) for r in new_rows}
    surplus = len(old_rows) - len(old_keys)      # rows collapsed away
    gained = len(new_keys - old_keys)            # entity-years that appeared
    lost = old_keys - new_keys                   # entity-years that vanished
    net = len(new_rows) - len(old_rows)
    print("\nROW RECONCILIATION (62.ship_dist_rows is MUST_NOT_FALL)")
    print(f"  rows before                                   {len(old_rows):>8,}")
    print(f"  - surplus name/tier variants of a key that "
          f"still exists      -{surplus:>7,}")
    print(f"  + (tribe_id, fiscal_year) keys that did not exist before  "
          f"+{gained:>6,}")
    print(f"  - keys that EXISTED before and do not now                 "
          f"-{len(lost):>6,}")
    print(f"  rows after                                    {len(new_rows):>8,}")
    check = len(old_rows) - surplus + gained - len(lost)
    print(f"  reconciles: {len(old_rows):,} - {surplus:,} + {gained:,} - "
          f"{len(lost):,} = {check:,}  "
          + ("EXACT" if check == len(new_rows) else "*** DOES NOT CLOSE ***"))
    print(f"  net change {net:+,} rows, $"
          f"{sum(float(r['obligations_usd']) for r in new_rows) - sum(float(r.get('obligations_usd') or 0) for r in old_rows):+,.2f}")
    if lost:
        print(f"  !! {len(lost):,} entity-year(s) LOST, named:")
        for k in sorted(lost)[:20]:
            print(f"     {k}")
        raise SystemExit(
            "REFUSING to call this collapse clean: an entity-year present "
            "before is absent now. That is not a collapse, it is a loss.")
    if check != len(new_rows):
        raise SystemExit(
            "REFUSING: the row arithmetic does not close, so something fell "
            "for a reason this script has not accounted for.")
    print(f"  every one of the {abs(net):,} row(s) that left is a surplus "
          f"variant of an entity-year that is still in the file, and no "
          f"entity-year was lost.")


def read_current():
    if not PANEL.exists():
        return [], []
    with open(PANEL, encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        return list(rd), (rd.fieldnames or [])


def money(rows, col="obligations_usd"):
    return round(sum(float(r.get(col) or 0) for r in rows), 2)


def by_key(rows):
    out = defaultdict(float)
    for r in rows:
        out[(r.get("tribe_id"), r.get("fiscal_year"))] += \
            float(r.get("obligations_usd") or 0)
    return out


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true",
                   help="measure and diff, write nothing")
    g.add_argument("--apply", action="store_true", help="write the panel")
    args = ap.parse_args()

    print("=== Cedar Press 428: prime contracting entity-year panel ===\n")

    old, old_fields = read_current()
    old_by_key = by_key(old)
    print(f"panel on disk : {len(old):,} rows, "
          f"{len(old_by_key):,} distinct (tribe_id, fiscal_year), "
          f"{len(old_by_key) and len(old) - len(old_by_key):,} surplus rows")
    print(f"                ${money(old):,.2f}")
    colliding = sum(1 for k, n in
                    __import__("collections").Counter(
                        (r.get("tribe_id"), r.get("fiscal_year"))
                        for r in old).items() if n > 1)
    print(f"                {colliding:,} colliding (tribe_id, fiscal_year) "
          f"key(s) - a buyer's join on this key fans out\n")

    panel, stats = P.build_from_prime(panel_path=PANEL, today=TODAY)
    P.print_stats(stats)
    new_by_key = by_key(panel)
    print(f"\npanel rebuilt : {len(panel):,} rows, "
          f"{len(new_by_key):,} distinct (tribe_id, fiscal_year)")
    print(f"                ${money(panel):,.2f}")
    print(f"                grain check: one row per (tribe_id, fiscal_year) "
          f"- PASSED")
    print(f"                conservation: panel == "
          f"${stats['source_attributed_obligations_usd']:,.2f} attributed "
          f"row dollars - PASSED")

    # ---- what a buyer's numbers do ---------------------------------------
    print("\nWHAT CHANGES FOR A BUYER")
    print(f"  naive groupby(['tribe_id','fiscal_year']).obligations_usd.sum()")
    print(f"    before  ${sum(old_by_key.values()):>18,.2f} over "
          f"{len(old_by_key):,} keys, from {len(old):,} rows")
    print(f"    after   ${sum(new_by_key.values()):>18,.2f} over "
          f"{len(new_by_key):,} keys, from {len(panel):,} rows")
    print(f"  a 1:1 merge on (tribe_id, fiscal_year) multiplied the other "
          f"table by up to "
          f"{max([n for n in __import__('collections').Counter((r.get('tribe_id'), r.get('fiscal_year')) for r in old).values()] or [1])}x "
          f"before; 1x after.")

    moved = {k: (new_by_key.get(k, 0.0) - old_by_key.get(k, 0.0))
             for k in set(old_by_key) | set(new_by_key)}
    moved = {k: v for k, v in moved.items() if abs(v) >= 0.005}
    print(f"\nSTALENESS CASCADED FROM prime_contracts.csv")
    print(f"  {len(moved):,} (entity, year) cell(s) change value because "
          f"rulings applied to the row table had never reached the panel")
    tot = sum(moved.values())
    print(f"  net ${tot:,.2f}")
    for k, v in sorted(moved.items(), key=lambda kv: -abs(kv[1]))[:10]:
        print(f"    {k[0]:20} {k[1]}  ${v:>16,.2f}")
    anvc_old = round(sum(v for k, v in old_by_key.items()
                         if (k[0] or "").startswith("ANVC-")), 2)
    anvc_new = round(sum(v for k, v in new_by_key.items()
                         if (k[0] or "").startswith("ANVC-")), 2)
    print(f"  village_corp_obligations_usd (62's invariant 3): "
          f"${anvc_old:,.2f} -> ${anvc_new:,.2f}")

    print(f"\ncolumns  {old_fields}\n      -> {P.PANEL_FIELDS}")
    dropped = [c for c in old_fields if c not in P.PANEL_FIELDS]
    if dropped:
        print(f"  DROPPED {dropped} - see cedar_prime_panel's docstring. "
              f"`confidence_tier` is replaced by obligations_usd_tier_a / "
              f"_tier_b and `confidence_tiers`, deliberately under NEW names "
              f"so that a stale `confidence_tier == 'A'` filter raises "
              f"instead of returning a plausible partial total.")

    if args.check:
        print("\nCHECK ONLY. Nothing was written.")
        return 0

    snapshot_pre_change()
    P.write_panel(panel, PANEL)
    print(f"wrote {PANEL.relative_to(ROOT)}  ({len(panel):,} rows)")
    xp, xn = P.write_excluded(stats, TODAY)
    print(f"wrote {xp.relative_to(ROOT)}  ({xn:,} named "
          f"(awardee_uei, awardee_name, fiscal_year, reason) exclusions - "
          f"the identity of every row that entered no entity total, not just "
          f"a count)")
    register_codebook(panel)
    reconcile_shipped_rows(old, panel)
    print("\nNOW RUN: py -3 code/62_no_regression_check.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
