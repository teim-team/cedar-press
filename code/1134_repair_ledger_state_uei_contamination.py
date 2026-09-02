#!/usr/bin/env python3
"""
Cedar Press - 1134: THE LEDGER'S `state` COLUMN HOLDS 12,127 UEIs.

    py -3 code/1134_repair_ledger_state_uei_contamination.py report
    py -3 code/1134_repair_ledger_state_uei_contamination.py apply
    py -3 code/1134_repair_ledger_state_uei_contamination.py verify
    py -3 code/1134_repair_ledger_state_uei_contamination.py selftest

WHAT IS WRONG
-------------
`data/spine/cedar_identifier_ledger.csv` has 19,232 rows. On **12,127** of
them the `state` cell holds that row's OWN `identifier` - a 12-character UEI -
instead of a US state. Every one is an `identifier_type = UEI` row sourced
from `master_tribal_entity_registry.csv`; the ledger's 4,937 CAGE rows and
1,104 EIN rows are untouched.

IT IS NOT A COLUMN SHIFT. THE SHIFT WIDTH IS ZERO.
---------------------------------------------------
This was briefed as a column shift travelling in from the owner's enterprise
dataset, and a shift displaces EVERY field past the insertion point, so the
first job was to measure the width before repairing one column and declaring
victory. It is one column, and it is not displaced - it is OVERWRITTEN.

Measured three ways, all agreeing:

1. **Against the clean version of the same source.** 12,127 rows of
   `native_entity_enterprise_dataset_v3.csv` carry the UEI in `hq_state`;
   11,392 of them match a v6 row 1:1 on (uei, name, tribe_id). Across those
   11,392 rows and all 26 columns, the ONLY differences are:

       hq_city    11,391  (all of them v3-blank, filled later by the geocoder)
       hq_state   11,392  (v3 holds the UEI, v6 holds a state)
       hq_zip        909  (all of them v3-blank, same geocoder)
       six others      2  (two rows, an unrelated record correction)

   A shift of width N leaves N columns of debris on one side and a hole on the
   other. There is no debris and there is no hole. Every column but `hq_state`
   is byte-identical to the repaired version.

2. **Against the raw registry Cedar actually reads.**
   `data/raw/external/master_tribal_entity_registry.csv`, 13,191 rows, 12
   columns. Exactly ONE column ever holds a value equal to the row's own UEI:
   `physical_state`, 12,127 times. The neighbours on both sides
   (`verified_date`, `n_transactions_master_prime`) are 100% populated and
   correctly typed on the contaminated rows.

3. **Against the code that wrote it.** The root cause is a named-column
   fallback, not an off-by-one:

       # sam_extracts/build_master_entity_registry.py, line 126
       physical_state=("recipient_location_state_code", "first")
           if "recipient_location_state_code" in prime.columns
           else ("awardee_uei", "first")

   `master prime file.dta` has no `recipient_location_state_code`, so the else
   branch fired and aggregated the UEI into the state field for every UEI
   present in master prime. The 1,064 registry rows that came in by the
   hand-matched path never went through that groupby and carry a real state
   (134) or a blank (929).

   **This is worth more than the repair.** A shift is a parser bug and you fix
   the reader. A fallback that silently substitutes a different column is a
   design that cannot fail loudly, and the same line will do it again on the
   next column whose name changes upstream.

WHAT IS AND IS NOT DOWNSTREAM OF IT
------------------------------------
The brief's largest hypothesis was that `federal_funding_transactions.csv`'s
15,878 `ledger_uei_state_disagreement_withheld` rows - $8,210,723,480.00
withheld across 120 proposed entities - were withheld against a corrupted
state, making the withholdings spurious. **Measured, and it is false.**

`code/115_pull_assistance_archive.py` line 892 builds its comparison state
from `cedar_entity_spine.csv`, keyed on `tribe_id`. It never reads the
identifier ledger's `state` column. The spine's own `state` is clean: 1,492
two-letter states, 63 blanks, zero UEIs across 1,555 rows, and a blank yields
`agree = "unknown"`, which cannot withhold. All 120 proposed entities carry a
real two-letter spine state.

    rows withheld against a corrupted state: 0 of 15,878   ($0.00 of $8.21B)

98 of those 120 entities DO have contaminated ledger rows, which is why the
coincidence reads as causal. It is not. The withholdings stand.

The real downstream reach is smaller and entirely internal:
`03_apply_exclusions_and_tier.py` copies the spine ledger's `state` straight
into `data/clean/cedar_identifier_ledger_tiered.csv`, which feeds
`cedar_identifier_ledger_final.csv`, which ~15 scripts read. Both clean
ledgers are currently clean of UEIs - `71_fix_known_defects.py` defect 5
BLANKED them - but 71 never touched the spine ledger, so the contamination sat
upstream of its own fix and a rerun of 03 would push all 12,127 back in.

AND 71 BLANKED WHAT IT COULD HAVE RECOVERED
--------------------------------------------
71 replaced each rejected value with "". That is safe and it is lossy: v6
holds a real HQ state for 12,019 of the 14,923 blank-state rows in
`cedar_identifier_ledger_tiered.csv` and 12,026 of the 16,250 in
`cedar_identifier_ledger_final.csv`. A shipped column reading "unknown" where
the authority says "VA" is a second defect wearing the first one's clothes, so
this script fills those blanks too - blanks ONLY, never overwriting a value
already there.

THE REPAIR
----------
Authority: `data/raw/external/need_v6_geocoded.csv` (v6, the repaired
version - 18,110 rows, 0 contaminated), keyed on `enterprise_uei`.

A state is written ONLY where v6 supplies exactly one two-letter state for
that UEI. Where v6 gives nothing, or gives more than one, the cell is left
BLANK. Nothing is guessed and nothing is inferred from a name, a ZIP or a
sibling row. Split, measured:

    12,127 contaminated spine rows
      11,943  v6 supplies exactly one state   -> written
         184  v6 row exists, hq_state blank   -> left BLANK
           0  no v6 row
           0  v6 disagrees with itself

WHY `verify` CANNOT PASS ON AN UNTOUCHED FILE
----------------------------------------------
A conservation proof that nothing broke is not a proof that something
happened - that exact mistake shipped a "$1.5B attributed" claim on a table
that attributed nothing. So `verify` asserts a POSITIVE:

  I1  no ledger row anywhere holds its own identifier in `state`   (absence)
  I2  >= 11,943 of the named identifiers now carry THEIR v6 state  (presence)
  I3  no repaired cell disagrees with v6                           (honesty)
  I4  rows and columns unchanged vs the pre-1134 backup, and no
      column other than `state` moved                              (blast radius)

I2 is the one that matters. On the un-repaired file it scores 0 and verify
exits 1. On a file somebody merely BLANKED it also scores 0 and verify still
exits 1 - blanking is not repairing. `selftest` proves both, by running the
real check against a synthetic un-repaired table.
"""
import csv
import json
import os
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cedar_pipeline import clean_state  # noqa: E402

csv.field_size_limit(10 ** 9)

ROOT = Path(__file__).resolve().parents[1]
SPINE = ROOT / "data" / "spine"
CLEAN = ROOT / "data" / "clean"
EXT = ROOT / "data" / "raw" / "external"

V6 = EXT / "need_v6_geocoded.csv"
SPINE_LEDGER = SPINE / "cedar_identifier_ledger.csv"
TIERED = CLEAN / "cedar_identifier_ledger_tiered.csv"
FINAL = CLEAN / "cedar_identifier_ledger_final.csv"
# FOUND BY SWEEPING THE CLASS, NOT THE INSTANCE. The brief named one table.
# Checking every table in data/spine/ and data/clean/ that carries BOTH an
# `identifier` and a `state` column turned up a fourth: this one, 1,577 rows,
# EVERY ROW tier A and publishable, 699 of them holding the row's own UEI in
# `state` and the other 878 holding an unnormalised full state name - so not
# one row of the most customer-facing copy of the ledger carries a usable
# state. It is written by 03 from the spine ledger and 71 never saw it.
PUBID = CLEAN / "cedar_publishable_identifiers.csv"

TODAY = "2026-09-02"
BUILT_BY = "1134_repair_ledger_state_uei_contamination.py"
BAK_TAG = f".bak_{TODAY}_pre_1134_repair_ledger_state_uei_contamination"
MANIFEST = ROOT / "docs" / "LEDGER_STATE_REPAIR_1134.json"
# The per-cell table lives OUTSIDE docs/ on purpose. `.gitignore` re-includes
# `docs/**/*.csv`, and 38,603 dispositions is 8.4 MB against a 38.8 MB source
# repo - an audit record that big does not belong in git history when the
# `.bak_*_pre_1134_*` copy beside every table already holds the before state
# byte for byte. docs/ keeps the SUMMARY and the one short exception list,
# which is the part a reader actually needs.
CELLS = ROOT / "review" / "ledger_state_repair_1134_cells.csv"

STATE2 = re.compile(r"^[A-Z]{2}$")

# Measured 2026-09-02, before any write. verify asserts against these, so a
# repair that lands on fewer rows than it claimed cannot pass quietly.
EXPECT_CONTAMINATED = 12127
EXPECT_RECOVERABLE = 11943
EXPECT_BLANK = 184


def rd(p):
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        rdr = csv.DictReader(fh)
        return [dict(r) for r in rdr], list(rdr.fieldnames or [])


def wr(p, rows, fields):
    tmp = Path(str(p) + ".part1134")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, p)


def v6_states():
    """{UEI: state} for every UEI v6 gives exactly ONE two-letter state.

    A UEI v6 disagrees with itself about is deliberately ABSENT from this map,
    not resolved by taking the first - picking one would invent a headquarters
    the source never claimed (the same rule `cedar_pipeline.clean_state`
    applies to a multi-state string).
    """
    seen = defaultdict(set)
    rows, _ = rd(V6)
    for r in rows:
        u = (r.get("enterprise_uei") or "").strip().upper()
        s = (r.get("hq_state") or "").strip().upper()
        if u and STATE2.match(s):
            seen[u].add(s)
    return {u: next(iter(v)) for u, v in seen.items() if len(v) == 1}, len(rows)


def contaminated(r):
    s = (r.get("state") or "").strip()
    return bool(s) and s == (r.get("identifier") or "").strip()


def scan(rows):
    c = Counter()
    for r in rows:
        s = (r.get("state") or "").strip()
        if contaminated(r):
            c["state_holds_own_identifier"] += 1
        elif not s:
            c["blank"] += 1
        elif STATE2.match(s.upper()):
            c["real_state"] += 1
        else:
            c["other"] += 1
    return c


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------
def report():
    v6, n_v6 = v6_states()
    print("=== 1134 report ===\n")
    print(f"authority: {V6.relative_to(ROOT).as_posix()}  "
          f"{n_v6:,} rows, {len(v6):,} UEIs with exactly one state\n")

    for p in (SPINE_LEDGER, TIERED, FINAL, PUBID):
        if not p.exists():
            print(f"{p.relative_to(ROOT).as_posix()}: ABSENT")
            continue
        rows, fields = rd(p)
        c = scan(rows)
        print(f"{p.relative_to(ROOT).as_posix()}: {len(rows):,} rows")
        for k in ("state_holds_own_identifier", "real_state", "blank", "other"):
            print(f"    {k:28s} {c[k]:6,}")
        bad = [r for r in rows if contaminated(r)]
        blanks = [r for r in rows
                  if not (r.get("state") or "").strip()
                  and (r.get("identifier_type") or "").strip().upper() == "UEI"]
        rec = sum(1 for r in bad
                  if v6.get((r.get("identifier") or "").strip().upper()))
        recb = sum(1 for r in blanks
                   if v6.get((r.get("identifier") or "").strip().upper()))
        if bad:
            print(f"    -> of {len(bad):,} contaminated: {rec:,} recoverable "
                  f"from v6, {len(bad) - rec:,} must go BLANK")
        if recb:
            print(f"    -> {recb:,} blank UEI rows v6 could fill "
                  f"(of {len(blanks):,} blank UEI rows)")
        print()

    rows, _ = rd(SPINE_LEDGER)
    bad = [r for r in rows if contaminated(r)]
    byt = Counter((r.get("identifier_type") or "") for r in bad)
    bys = Counter((r.get("source_file") or "") for r in bad)
    print(f"contaminated spine rows by identifier_type: {dict(byt)}")
    print(f"contaminated spine rows by source_file    : {dict(bys)}")
    print(f"distinct identifiers among them           : "
          f"{len({r['identifier'] for r in bad}):,}")
    return 0


# ---------------------------------------------------------------------------
# apply
# ---------------------------------------------------------------------------
def _repair_file(p, v6, fill_blanks):
    """Returns (n_written, n_left_blank, n_blanks_filled, n_normalised,
    n_left_alone, manifest_rows)."""
    rows, fields = rd(p)
    if "state" not in fields:
        raise SystemExit(f"{p} has no `state` column - refusing to guess one")
    # NEVER overwrite an existing pre-1134 backup. It is the baseline I4
    # measures the blast radius against, and a second `apply` that refreshed
    # it would compare the repaired file with itself and score clean.
    bak = Path(str(p) + BAK_TAG)
    if not bak.exists():
        shutil.copy2(p, bak)

    wrote = left = filled = normed = alone = 0
    man = []
    for r in rows:
        ident = (r.get("identifier") or "").strip().upper()
        itype = (r.get("identifier_type") or "").strip().upper()
        cur = (r.get("state") or "").strip()
        if contaminated(r):
            true_state = v6.get(ident, "")
            r["state"] = true_state
            if true_state:
                wrote += 1
            else:
                left += 1
            man.append({"identifier": ident, "identifier_type": itype,
                        "was": "SELF_IDENTIFIER", "now": true_state,
                        "disposition": "recovered" if true_state else "blank"})
        elif fill_blanks and not cur and itype == "UEI":
            true_state = v6.get(ident, "")
            if true_state:
                r["state"] = true_state
                filled += 1
        elif cur and not STATE2.match(cur.upper()):
            # `Oklahoma` -> `OK`. LOSSLESS, and it is the same rule
            # cedar_pipeline.clean_state applies, so the spine ledger stops
            # disagreeing with its own clean children about what a state is.
            #
            # A multi-state string (`Alabama; Texas`, 48 rows) and a junk
            # value (`BRUNEI & MUARA`, `-`, 3 rows) are LEFT EXACTLY AS THEY
            # ARE. clean_state would blank them and 71 did blank them in the
            # clean ledgers; blanking is a deletion of evidence with no
            # recovery behind it, and this script's rule is flag, never
            # delete. They are counted and named in `report`.
            val, verdict = clean_state(cur, ident)
            if verdict == "normalised from full name":
                r["state"] = val
                normed += 1
            else:
                alone += 1
    wr(p, rows, fields)
    return wrote, left, filled, normed, alone, man


def manifest_from_backup(p):
    """Every `state` cell this repair moved, read off the pre-1134 backup.

    Derived, so a rerun that repairs nothing still writes the true record.
    """
    bak = Path(str(p) + BAK_TAG)
    if not bak.exists():
        return []
    before, _ = rd(bak)
    after, _ = rd(p)
    if len(before) != len(after):
        return []
    out = []
    for a, b in zip(before, after):
        was = (a.get("state") or "").strip()
        now = (b.get("state") or "").strip()
        if was == now:
            continue
        ident = (b.get("identifier") or "").strip().upper()
        out.append({
            "table": p.name,
            "identifier": ident,
            "identifier_type": (b.get("identifier_type") or "").strip().upper(),
            "was": "SELF_IDENTIFIER" if was == ident else (was or "BLANK"),
            "now": now,
            "disposition": ("recovered" if was == ident and now
                            else "blank" if was == ident
                            else "blank_filled" if not was
                            else "normalised")})
    return out


def apply_():
    v6, _ = v6_states()
    print("=== 1134 apply ===\n")

    rows, _ = rd(SPINE_LEDGER)
    n_bad = sum(1 for r in rows if contaminated(r))
    if n_bad == 0:
        print("  spine ledger already holds 0 contaminated rows - nothing to "
              "repair there. Continuing to the clean ledgers.")

    wrote, left, _f, normed, alone, man = _repair_file(
        SPINE_LEDGER, v6, fill_blanks=True)
    print(f"  {SPINE_LEDGER.relative_to(ROOT).as_posix()}")
    print(f"    contaminated repaired with a v6 state : {wrote:,}")
    print(f"    contaminated left BLANK (v6 silent)   : {left:,}")
    print(f"    full state names normalised to 2-char : {normed:,}")
    print(f"    non-state values LEFT ALONE, not blanked: {alone:,}")

    for p in (TIERED, FINAL, PUBID):
        if not p.exists():
            continue
        w2, l2, f2, n2, a2, m2 = _repair_file(p, v6, fill_blanks=True)
        man.extend(m2)
        print(f"  {p.relative_to(ROOT).as_posix()}")
        print(f"    contaminated repaired                 : {w2:,}")
        print(f"    contaminated left BLANK               : {l2:,}")
        print(f"    blank UEI rows filled from v6         : {f2:,}")
        print(f"    full state names normalised           : {n2:,}")
        print(f"    non-state values LEFT ALONE           : {a2:,}")

    # THE MANIFEST IS DERIVED FROM THE BACKUP, NOT FROM THIS RUN'S COUNTERS.
    # A second `apply` legitimately repairs 0 rows, and the first version of
    # this wrote a 0-disposition manifest over a 12,127-disposition one - the
    # audit record erased by the idempotent rerun of the script that made it.
    man = manifest_from_backup(SPINE_LEDGER)
    n_bad = sum(1 for m in man if m["was"] == "SELF_IDENTIFIER")
    wrote = sum(1 for m in man if m["disposition"] == "recovered")
    left = sum(1 for m in man if m["disposition"] == "blank")
    for q in (TIERED, FINAL, PUBID):
        if q.exists():
            man.extend(manifest_from_backup(q))

    MANIFEST.write_text(json.dumps(
        {"built_by": BUILT_BY, "built_date": TODAY,
         "authority": V6.relative_to(ROOT).as_posix(),
         "authority_rule": ("hq_state written only where v6 gives exactly one "
                            "two-letter state for that enterprise_uei; "
                            "otherwise BLANK. Nothing is inferred."),
         "shift_width_columns": 0,
         "root_cause": ("sam_extracts/build_master_entity_registry.py:126 "
                        "aggregates awardee_uei into physical_state when "
                        "recipient_location_state_code is absent from the "
                        "master prime file"),
         "spine_contaminated_rows": n_bad,
         "spine_recovered": wrote, "spine_left_blank": left,
         "cells_changed_total": len(man),
         "cells_by_table_and_disposition": {
             f"{k[0]}|{k[1]}": v for k, v in sorted(Counter(
                 (m["table"], m["disposition"]) for m in man).items())},
         # The one list a reader needs BY NAME rather than by count: the
         # identifiers the authority could not speak for, which are the rows
         # now honestly blank. Short. The full per-cell table is the CSV.
         "left_blank_because_v6_had_no_state": sorted(
             {m["identifier"] for m in man if m["disposition"] == "blank"}),
         "cells_table": CELLS.relative_to(ROOT).as_posix()},
        indent=2) + "\n", encoding="utf-8")
    if man:
        CELLS.parent.mkdir(parents=True, exist_ok=True)
        with open(CELLS, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(man[0].keys()))
            w.writeheader()
            w.writerows(man)
    print(f"\n  manifest -> {MANIFEST.relative_to(ROOT).as_posix()} (summary)")
    print(f"  cells    -> {CELLS.relative_to(ROOT).as_posix()} "
          f"({len(man):,} dispositions)")
    return verify()


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------
def _verify_table(p, v6, strict_presence):
    """Returns (list_of_failures, list_of_notes)."""
    fails, notes = [], []
    rows, fields = rd(p)
    try:
        name = p.relative_to(ROOT).as_posix()
    except ValueError:
        name = p.name          # selftest runs on a temp copy

    # I1 - absence
    n_bad = sum(1 for r in rows if contaminated(r))
    if n_bad:
        fails.append(f"I1 {name}: {n_bad:,} rows still hold their own "
                     f"identifier in `state`")
    else:
        notes.append(f"I1 {name}: 0 rows hold their own identifier")

    # I2 - PRESENCE. The check that fails on an untouched OR merely-blanked
    # file. Counted over UEI rows whose UEI v6 can speak to.
    speakable = [r for r in rows
                 if (r.get("identifier_type") or "").strip().upper() == "UEI"
                 and v6.get((r.get("identifier") or "").strip().upper())]
    agree = sum(1 for r in speakable
                if (r.get("state") or "").strip().upper()
                == v6[(r.get("identifier") or "").strip().upper()])
    # Two thresholds, and the SECOND is the one that generalises: EVERY row
    # v6 can speak to must carry v6's answer. A floor alone can be met by a
    # table that was already partly right; equality cannot.
    floor = strict_presence if isinstance(strict_presence, int) else 1
    if agree < floor or (speakable and agree != len(speakable)):
        fails.append(f"I2 {name}: {agree:,} of {len(speakable):,} v6-speakable "
                     f"UEI rows carry their v6 state (floor {floor:,}). "
                     f"THE WORK HAS NOT LANDED. A blanked-but-unrepaired "
                     f"table scores 0 here and that is the point - a "
                     f"conservation proof that nothing broke is not a proof "
                     f"that something happened.")
    elif not speakable:
        fails.append(f"I2 {name}: v6 can speak to 0 rows of this table, so "
                     f"the repair is UNPROVABLE here, which is not the same "
                     f"as done.")
    else:
        notes.append(f"I2 {name}: {agree:,} of {len(speakable):,} v6-speakable "
                     f"UEI rows carry their v6 state")

    # I3 - honesty
    wrong = [((r.get("identifier") or ""), (r.get("state") or ""),
              v6[(r.get("identifier") or "").strip().upper()])
             for r in speakable
             if (r.get("state") or "").strip()
             and (r.get("state") or "").strip().upper()
             != v6[(r.get("identifier") or "").strip().upper()]]
    if wrong:
        notes.append(f"I3 {name}: {len(wrong):,} UEI rows carry a state v6 "
                     f"disagrees with. These were NOT written by this script "
                     f"(it only ever writes v6's own value) - they are "
                     f"pre-existing values this script left standing. "
                     f"e.g. {wrong[:3]}")

    # I4 - blast radius, against this script's own backup
    bak = Path(str(p) + BAK_TAG)
    if bak.exists():
        brows, bfields = rd(bak)
        if len(brows) != len(rows):
            fails.append(f"I4 {name}: rows {len(brows):,} -> {len(rows):,}")
        elif bfields != fields:
            fails.append(f"I4 {name}: columns changed {bfields} -> {fields}")
        else:
            moved = Counter()
            for a, b in zip(brows, rows):
                for c in fields:
                    if (a.get(c) or "") != (b.get(c) or ""):
                        moved[c] += 1
            other = {c: n for c, n in moved.items() if c != "state"}
            if other:
                fails.append(f"I4 {name}: columns other than `state` changed: "
                             f"{other}")
            else:
                notes.append(f"I4 {name}: {len(rows):,} rows and "
                             f"{len(fields)} columns unchanged; "
                             f"{moved['state']:,} `state` cells moved and "
                             f"nothing else")
    else:
        notes.append(f"I4 {name}: no {BAK_TAG} backup - blast radius "
                     f"UNMEASURED, which is not the same as clean")
    return fails, notes


def verify():
    v6, _ = v6_states()
    print("\n=== 1134 verify ===")
    fails, notes = [], []
    for p, strict in ((SPINE_LEDGER, EXPECT_RECOVERABLE), (TIERED, 1),
                      (FINAL, 1), (PUBID, 1)):
        if not p.exists():
            notes.append(f"{p.relative_to(ROOT).as_posix()}: ABSENT")
            continue
        f, n = _verify_table(p, v6, strict)
        fails += f
        notes += n
    if not MANIFEST.exists():
        fails.append(f"I0: {MANIFEST.relative_to(ROOT).as_posix()} absent - "
                     f"no record of what was repaired")
    for n in notes:
        print(f"  ok   {n}")
    for f in fails:
        print(f"  FAIL {f}")
    print(f"\n  {len(fails)} failure(s)")
    return 1 if fails else 0


# ---------------------------------------------------------------------------
# selftest - prove verify FAILS when the work has not landed
# ---------------------------------------------------------------------------
def selftest():
    v6 = {"AAAAAAAAAAAA": "VA", "BBBBBBBBBBBB": "MD"}
    fields = ["identifier_type", "identifier", "state"]

    def table(states):
        return [{"identifier_type": "UEI", "identifier": u, "state": s}
                for u, s in states]

    global EXPECT_RECOVERABLE
    keep = EXPECT_RECOVERABLE
    EXPECT_RECOVERABLE = 2
    try:
        import tempfile
        d = Path(tempfile.mkdtemp())
        cases = [
            ("untouched (state holds the UEI)",
             [("AAAAAAAAAAAA", "AAAAAAAAAAAA"), ("BBBBBBBBBBBB", "BBBBBBBBBBBB")],
             True),
            ("BLANKED but not repaired - 71's outcome",
             [("AAAAAAAAAAAA", ""), ("BBBBBBBBBBBB", "")], True),
            ("repaired",
             [("AAAAAAAAAAAA", "VA"), ("BBBBBBBBBBBB", "MD")], False),
        ]
        allok = True
        for label, states, want_fail in cases:
            p = d / "t.csv"
            wr(p, table(states), fields)
            f, _n = _verify_table(p, v6, strict_presence=True)
            got_fail = bool(f)
            mark = "OK " if got_fail == want_fail else "BAD"
            if got_fail != want_fail:
                allok = False
            print(f"  {mark} {label:44s} -> "
                  f"{'FAIL' if got_fail else 'pass'} "
                  f"(expected {'FAIL' if want_fail else 'pass'})")
            for x in f:
                print(f"        {x.splitlines()[0][:100]}")
        # I4 must catch a change outside `state`
        p = d / "u.csv"
        wr(p, table([("AAAAAAAAAAAA", "VA"), ("BBBBBBBBBBBB", "MD")]), fields)
        shutil.copy2(p, str(p) + BAK_TAG)
        rows, _ = rd(p)
        rows[0]["identifier_type"] = "CAGE"
        wr(p, rows, fields)
        f, _n = _verify_table(p, v6, strict_presence=False)
        i4 = [x for x in f if x.startswith("I4")]
        print(f"  {'OK ' if i4 else 'BAD'} I4 catches a change outside "
              f"`state`{'' if i4 else ' - IT DID NOT'}")
        allok = allok and bool(i4)
        shutil.rmtree(d, ignore_errors=True)
    finally:
        EXPECT_RECOVERABLE = keep
    print("\n  selftest " + ("OK" if allok else "FAILED"))
    return 0 if allok else 1


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "report"
    if arg == "report":
        return report()
    if arg == "apply":
        return apply_()
    if arg == "verify":
        return verify()
    if arg == "selftest":
        return selftest()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
