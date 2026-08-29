#!/usr/bin/env python3
"""
Cedar Press - 392: write the codebook FRAGMENTS for the SHIP set from 391.

WHAT IT WRITES, AND WHAT IT REFUSES TO WRITE
--------------------------------------------
One fragment per table under `data/clean/codebook/<block>.csv`. **Never
`codebook_master.csv`** - a shared mutable file with many writers is the defect
`cedar_codebook.py` exists to remove, and `41_build_codebooks.py` would delete
21 of 43 blocks if it ran. Fold the fragments in afterwards with
`py -3 code/cedar_codebook.py build`.

A DESCRIPTION IS FOUND, NOT COMPOSED
------------------------------------
Four sources, in order, and no fifth:

  1. `41_build_codebooks.DESCRIPTIONS` via its own `describe(col, dataset)` -
     608 hand-written entries, imported rather than copied so the
     dataset-scoped keys keep working (`relationship` means different things
     in Dataset 11 and Dataset 12, and 41 already knows that).
  2. `docs/codebooks/*.md` - the codebooks written as prose and never
     registered, parsed with `cedar_register_codebook.parse_doc`.
  3. The existing codebook corpus, **only where the whole corpus agrees**: a
     column name reused across blocks with exactly ONE distinct description.
     Two different descriptions for one name is the Dataset-11/12 trap and the
     column is left undefined rather than resolved by coin-toss.
  4. Nothing. **A column whose meaning is not established anywhere is written
     `published = 0`, `access_tier = internal`, and its description SAYS SO.**
     That is the `pdf_path` disposition, applied at scale.

Inventing a plausible sentence would clear `87`'s `[undefined]` counter and
`62`'s `codebook_undocumented_public` while making the codebook worse than
blank, because a wrong definition is believed. This script would rather ship
fewer columns.

    HOW MANY IS "TOO FEW"? A table must clear ONE of two floors: at least
    MIN_DEFINED_VARS defined variables, or at least 60% of the columns 41
    would publish. Clearing neither, it is NOT registered - it is named,
    with its exact counts, as a writing task. A notes contract listing two
    of thirty-one columns is a dataset that LOOKS documented.

    The defined-share is recorded for every table, registered or not.
    Registering a block makes a table shippable; it does not make it
    documented, and this project has already confused those two once
    (`nigc_declination_letters.csv`, 45 of 60 variables undefined).

THREE INVARIANTS THIS SCRIPT WILL NOT CROSS
-------------------------------------------
* **DUNS is never publishable.** Any variable whose name contains `duns` is
  forced to `internal`, which is STRICTER than 41's regex - that regex misses
  `pct_with_duns_tribal_rows_only`. `62`'s `duns_marked_publishable` must stay
  at zero.
* **`casino_city_id` is never publishable** - `cedar_codebook.is_licensed_col`.
* **`published = 1` implies a description exists.** `62` counts
  `published == "1" and not description` and it must be zero.

AND ONE COLLISION CHECK, RUN BEFORE ANYTHING IS WRITTEN
-------------------------------------------------------
`87` assigns a file to its BEST-OVERLAPPING block. A new block therefore
competes for every other file in `data/clean`. Two consequences, both checked
in `--check` and again before each write:

  * a new block must not steal an already-assigned file from its own block;
  * a new block must not CAPTURE a table 391 ruled INTERNAL. It can:
    `cedar_identifier_ledger_tiered.csv` has a header identical to
    `cedar_identifier_ledger_final.csv`. Captures are listed, and the fix is
    `cedar_codebook.INTERNAL_TABLES`, not deleting the block.

    py -3 code/392_write_unshipped_codebook_fragments.py --check   # dry run
    py -3 code/392_write_unshipped_codebook_fragments.py           # write
"""

import csv
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
FRAG = CLEAN / "codebook"
DOCS = CEDAR / "docs"
TODAY = date.today().isoformat()

sys.path.insert(0, str(Path(__file__).parent))
import cedar_codebook as CB                                    # noqa: E402
import cedar_register_codebook as RC                           # noqa: E402

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

TRIAGE = DOCS / "UNSHIPPED_TABLE_TRIAGE.json"
REPORT = DOCS / "UNSHIPPED_CODEBOOK_REGISTRATION.json"

FIELDS = ["dataset", "variable", "type", "units", "pct_filled", "n_rows",
          "published", "access_tier", "description", "generated"]

# Two floors; a table must clear one. See the comment at the test itself.
MIN_DEFINED_VARS = 8

# A definition that says the column does not publish. See the tier guard.
WITHHELD_RE = __import__("re").compile(
    r"\bWITHHELD\b|\bnever publish", __import__("re").I)

UNDEFINED = ("INTERNAL - no definition for this column was established from "
             "the file, from docs/codebooks, or from the existing codebook "
             "corpus. Withheld rather than guessed at (391/392, {date}).")


def load41():
    """Import 41 for its tiering and description rules. IMPORT ONLY - 41 is on
    the do-not-run list and its module level is constants and defs behind a
    `__main__` guard, which is why importing it is safe and running it is
    not."""
    spec = importlib.util.spec_from_file_location(
        "cedar41", Path(__file__).parent / "41_build_codebooks.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def header_of(p):
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return next(csv.reader(fh), [])


def profile(p):
    """type / pct_filled / n_rows, STREAMED.

    `cedar_register_codebook.profile` reads the whole file into a list. Two of
    the tables here are 83 MB and 62 MB, so this one holds counters instead.
    """
    hdr = header_of(p)
    filled = Counter()
    numeric = Counter()
    integral = {c: True for c in hdr}
    n = 0
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        r = csv.DictReader(fh)
        for row in r:
            n += 1
            for c in hdr:
                v = (row.get(c) or "").strip()
                if not v:
                    continue
                filled[c] += 1
                try:
                    f = float(v.replace(",", "").replace("$", ""))
                except ValueError:
                    continue
                numeric[c] += 1
                if not float(f).is_integer():
                    integral[c] = False
    prof = {}
    for c in hdr:
        if not filled[c]:
            t = "empty"
        elif numeric[c] == filled[c]:
            t = "integer" if integral[c] else "numeric"
        else:
            t = "text"
        prof[c] = {"type": t, "n_rows": n,
                   "pct_filled": round(100.0 * filled[c] / n, 1) if n else 0.0}
    return hdr, prof, n


def doc_descriptions():
    """Every `| \\`col\\` | ... | definition |` row in docs/codebooks/*.md.

    Restricted to that directory ON PURPOSE. Sweeping all of docs/*.md finds
    1,714 candidate rows and some of them are not definitions at all -
    `CLASS7_KEY_MIGRATION_LOG.md` would have supplied
    `allocation_id -> "tribe_name, effective_start, measurement_type"`, which
    is a key COMPOSITION, and it would have looked like a description.
    """
    out, src = {}, {}
    for p in sorted((DOCS / "codebooks").glob("*.md")):
        if ".bak" in p.name:
            continue
        for k, v in RC.parse_doc(p).items():
            if k not in out:
                out[k], src[k] = v, p.name
    return out, src


def corpus(exclude_blocks):
    """What the EXISTING codebook says about each column name.

    Returns (description, contested, internal_everywhere).

    `exclude_blocks` is this script's OWN blocks. They must be left out or a
    re-run reads back its own answers and counts them as corroboration - the
    codebook equivalent of citing yourself. Once `cedar_codebook.py build` has
    folded the fragments in, they are in the master too.

    `internal_everywhere` is the important one, and it is the tier-inheritance
    rule from the top of AGENTS.md turned on the codebook itself: **A TIER IS
    INHERITED FROM THE SOURCE ROW, NEVER ASSIGNED BY THE CONSUMER.** The
    measured case that forced it: `identifier` is `access_tier = internal` in
    ALL EIGHT blocks that carry it, and its written definition begins
    "WITHHELD from publication". `41.access_tier("identifier")` nevertheless
    returns `public`, because the bare name does not match its
    IDENTIFIER_COLS regex. Left alone, this script would have shipped a column
    the repo withholds everywhere - carrying a description that says it is
    withheld.
    """
    seen, tiers, where = defaultdict(set), defaultdict(set), defaultdict(set)

    def take(rows):
        for r in rows:
            if r.get("dataset") in exclude_blocks:
                continue
            k = (r.get("variable") or "").strip().lower()
            if not k:
                continue
            tiers[k].add((r.get("access_tier") or "").strip() or "public")
            d = (r.get("description") or "").strip()
            if d:
                seen[k].add(d)
                where[k].add(r.get("dataset"))

    take(CB.read(CLEAN / "codebook_master.csv"))
    for f in sorted(FRAG.glob("*.csv")):
        if ".bak" in f.name:
            continue
        take(CB.read(f))
    return ({k: next(iter(v)) for k, v in seen.items() if len(v) == 1},
            {k: sorted(where[k]) for k, v in seen.items() if len(v) > 1},
            {k for k, v in tiers.items() if v == {"internal"}})


def build_rows(block, path, m41, docdesc, docsrc, corpusdesc,
               internal_all):
    hdr, prof, n = profile(path)
    rows, provenance, shape = [], Counter(), Counter()
    for c in hdr:
        lc = c.strip().lower()
        pr = prof[c]

        d, why = m41.describe(c, block)[0], "41_DESCRIPTIONS"
        if not d:
            d, why = docdesc.get(lc, ""), f"docs/codebooks/{docsrc.get(lc)}"
        if not d:
            d, why = (corpusdesc.get(lc, ""),
                      "codebook corpus (unambiguous)")

        tier = m41.access_tier(c)
        rule_internal = tier == "internal"
        # STRICTER THAN 41, DELIBERATELY. 41's LICENSED_COLS regex anchors on
        # the end of the name and therefore misses `pct_with_duns_tribal_
        # rows_only`. `duns_marked_publishable` is a MUST_BE_ZERO gate metric
        # and a near-miss on a regex is not a reason to ship a licensed
        # identifier.
        if "duns" in lc or CB.is_licensed_col(c):
            tier = "internal"
            rule_internal = True
        if lc in internal_all:
            # EVERY existing block that carries this column tiers it
            # internal. Inherit that tier; do not overrule it here.
            tier = "internal"
            rule_internal = True
        if d and WITHHELD_RE.search(d):
            # A DEFINITION AND A TIER MUST NOT CONTRADICT EACH OTHER.
            # `identifier` is tiered internal in eight blocks and public in
            # one, so it is not unanimous and the rule above does not fire -
            # but the definition the repo wrote for it BEGINS "WITHHELD from
            # publication", and 41's access_tier() returns `public` because
            # the bare name misses its IDENTIFIER_COLS regex. Publishing a
            # column whose own description says it is withheld is a defect
            # that would ship looking like documentation. The prose wins:
            # somebody wrote it deliberately, and a regex did not.
            tier = "internal"
            rule_internal = True
        if not d:
            tier = "internal"
            d = UNDEFINED.format(date=TODAY)
            why = "UNDEFINED"

        published = "1" if (tier != "internal" and m41.is_published(c)) else "0"
        provenance[why] += 1
        if not rule_internal:
            shape["publishable_by_rule"] += 1
            shape["defined" if why != "UNDEFINED" else "undefined"] += 1
        rows.append({
            "dataset": block, "variable": c, "type": pr["type"],
            "units": RC.units_for(c, pr["type"]),
            "pct_filled": pr["pct_filled"], "n_rows": pr["n_rows"],
            "published": published, "access_tier": tier,
            "description": d, "generated": TODAY,
        })
    return rows, provenance, n, shape


def simulate(new_groups):
    """What would 87 assign every clean file to, with the new blocks in play?

    Returns {filename: (group, score)} for the CURRENT registry and for the
    registry plus `new_groups`, so the two can be diffed.

    ORDER MATTERS AND IS REPRODUCED EXACTLY. `CB.match_group` keeps the FIRST
    block at the maximum overlap (`ov > score`), so a tie is broken by
    iteration order. After `cedar_codebook.build()` the master is the
    fragments concatenated in FILENAME order, and 87 reads the master top to
    bottom - so the winner of a tie is the alphabetically-first block. The
    `after` dict is therefore assembled sorted by block name, or this
    simulation would predict a different winner than the real run.

    That is not academic: `fr_consultation_referenced.csv` scores 1.0 against
    BOTH `09i_fr_consultation_referenced` and `11b_fr_nagpra_title_index`,
    because its five generic columns are a subset of the NAGPRA index's ten.
    `09i` wins only because it sorts first.
    """
    base = CB.dataset_groups()
    for p in sorted(FRAG.glob("*.csv")):
        if ".bak" in p.name:
            continue
        for r in CB.read(p):
            base.setdefault(r.get("dataset"), set()).add(
                (r.get("variable") or "").strip().lower())
    merged = {k: set(v) for k, v in base.items()}
    for k, v in new_groups.items():
        merged[k] = set(v)
    after = {k: merged[k] for k in sorted(merged)}
    before_map, after_map = {}, {}
    for p in sorted(CLEAN.glob("*.csv")):
        if p.name.startswith("_") or p.name in ("codebook_master.csv",
                                                "series_breaks.csv"):
            continue
        h = header_of(p)
        before_map[p.name] = CB.match_group(h, base)
        after_map[p.name] = CB.match_group(h, after)
    return before_map, after_map


def main():
    check_only = "--check" in sys.argv
    print(f"=== Cedar Press 392: codebook fragments for the SHIP set "
          f"{'(DRY RUN)' if check_only else ''} ===\n")
    if not TRIAGE.exists():
        print("no docs/UNSHIPPED_TABLE_TRIAGE.json - run 391 first")
        return 2
    triage = json.loads(TRIAGE.read_text(encoding="utf-8"))
    ship = [t for t in triage["tables"] if t["verdict"] == "SHIP"]
    not_ship = {t["file"]: t["verdict"] for t in triage["tables"]
                if t["verdict"] != "SHIP"}
    print(f"  triage of {triage['generated']}: {len(ship)} SHIP, "
          f"{len(not_ship)} not\n")

    m41 = load41()
    docdesc, docsrc = doc_descriptions()
    own_blocks = {t['block'] for t in ship if t['block']}
    corpusdesc, contested, internal_all = corpus(own_blocks)
    print(f"  description sources: 41 {len(m41.DESCRIPTIONS)} entries · "
          f"docs/codebooks {len(docdesc)} columns · corpus {len(corpusdesc)} "
          f"unambiguous ({len(contested)} contested and therefore refused)\n")

    print(f"  {len(internal_all)} column name(s) are tiered internal by "
          f"EVERY existing block that carries them; that tier is "
          f"INHERITED here, never re-decided\n")

    # A block with a FRAGMENT has an owner and is untouchable. A block that
    # exists only in `codebook_master.csv` has no owner at all - it is one of
    # the master-only blocks `cedar_register_codebook.py reconcile` exists to
    # give a fragment to, and writing that fragment from the FILE'S OWN HEADER
    # is reconcile done from the data rather than from a stale master row.
    #
    # A FRAGMENT FILE NAME IS NOT A BLOCK KEY. `05b_identifier_graph.csv`
    # carries three datasets (`_edges`, `_nodes`, `_propagation`) and
    # `16_digital_gaming.csv` carries four. Deriving ownership from file stems
    # therefore MISSES sixteen live blocks and would have had this script
    # create `16d_loyalty_program_property.csv` while the same block already
    # lived inside `16_digital_gaming.csv` - two fragments claiming one
    # dataset, and `cedar_codebook.build()` concatenates both.
    owned_blocks = {f.stem for f in FRAG.glob("*.csv") if ".bak" not in f.name}
    for f in FRAG.glob("*.csv"):
        if ".bak" in f.name:
            continue
        for r in CB.read(f):
            owned_blocks.add(r.get("dataset"))
    master_only = set(CB.dataset_groups()) - owned_blocks

    built, skipped_thin, skipped_collision, missing = {}, [], [], []
    completed_stubs = []
    prov_total = Counter()
    for t in ship:
        p = CLEAN / t["file"]
        block = t["block"]
        if not p.exists():
            missing.append(t["file"])
            continue
        if block in owned_blocks:
            skipped_collision.append((t["file"], block))
            continue
        if block in master_only:
            completed_stubs.append((t["file"], block))
        rows, prov, n, shape = build_rows(
            block, p, m41, docdesc, docsrc, corpusdesc, internal_all)
        n_pub = sum(1 for r in rows if r["published"] == "1")
        # THE TEST IS NOT "how many columns are published". Most of the
        # withheld ones are withheld BY RULE - `_basis`, `_method`,
        # `_rationale` and the rest disclose the recipe and 41 has always
        # tiered them internal. Counting those as a documentation failure
        # would refuse the best-documented tables in the set.
        #
        # The test is: OF THE COLUMNS 41 WOULD PUBLISH, how many did we find a
        # definition for? The threshold is 0.60, the same number 87 uses to
        # decide whether a block describes a file well enough to ship it.
        by_rule = shape["publishable_by_rule"]
        defined = shape["defined"]
        share = (defined / by_rule) if by_rule else 0.0
        # A table must clear ONE of two bars, and neither alone is enough on
        # its own terms:
        #
        #   MIN_DEFINED_VARS  an absolute floor. A 65-column table with 30
        #                     defined columns is a usable codebook even though
        #                     that is only 46% of it.
        #   0.60 share        the proportional floor, and the same number 87
        #                     uses to decide a block describes a file. A
        #                     three-column table needs two of them.
        #
        # A table clearing NEITHER is not registered. It is named below with
        # its exact counts, which turns it from an invisible gap into a
        # writing task. THE SHARE IS RECORDED FOR EVERY TABLE, REGISTERED OR
        # NOT - registering a block makes a table shippable and does not make
        # it documented, and those two must not be allowed to blur.
        if defined < MIN_DEFINED_VARS and share < CB.MATCH_THRESHOLD:
            skipped_thin.append((t["file"], defined, by_rule, len(rows), n,
                                 round(share, 3)))
            continue
        built[block] = (t["file"], rows, n, n_pub, prov,
                        defined, by_rule, round(share, 3))
        prov_total.update(prov)

    # ---- the collision simulation, BEFORE a single write --------------------
    new_groups = {b: {r["variable"].strip().lower() for r in rs}
                  for b, (_f, rs, *_rest) in built.items()}
    before_map, after_map = simulate(new_groups)
    own_block = {f: b for b, (f, *_r) in built.items()}
    stolen, moved_to_own, misrouted, captured = [], [], [], []
    for name, (g0, s0) in before_map.items():
        g1, s1 = after_map[name]
        mine = own_block.get(name)
        if mine and g1 != mine:
            # A SHIP table that did not land in the block written FOR it. The
            # block it landed in describes a different table, so its notes
            # contract would carry someone else's definitions.
            misrouted.append((name, mine, g1, round(s1, 3)))
        elif s0 >= CB.MATCH_THRESHOLD and g1 != g0:
            (moved_to_own if mine else stolen).append(
                (name, g0, round(s0, 3), g1, round(s1, 3)))
        if s0 < CB.MATCH_THRESHOLD and s1 >= CB.MATCH_THRESHOLD and \
                g1 != mine:
            captured.append((name, not_ship.get(name, "?"), g1, round(s1, 3)))

    if stolen or misrouted:
        for name, g0, s0, g1, s1 in stolen:
            print(f"  !! {name} would be TAKEN from a block it already has: "
                  f"{g0} ({s0}) -> {g1} ({s1})")
        for name, mine, g1, s1 in misrouted:
            print(f"  !! {name} would land in {g1} ({s1}), not in {mine}, "
                  f"which was written for it")
        print("     Nothing written. Rename or narrow the offending block.")
        return 1

    if moved_to_own:
        print(f"  {len(moved_to_own)} table(s) move OUT of a block that did "
              f"not describe them and INTO one written from their own header. "
              f"Delete the stale notes contract in the old dist/ directory "
              f"after the chain runs:")
        for name, g0, s0, g1, s1 in moved_to_own:
            print(f"       {name}: {g0} ({s0}) -> {g1} ({s1})")

    if captured:
        unguarded = [c for c in captured if c[0] not in CB.INTERNAL_TABLES]
        print(f"  {len(captured)} table(s) NOT in the SHIP set would be picked "
              f"up by a new block because their header is a SUBSET of a "
              f"shipped sibling's - a back door onto the shelf that needs no "
              f"block of its own:")
        for name, verdict, g, sc in captured:
            guard = ("blocked by cedar_codebook.INTERNAL_TABLES"
                     if name in CB.INTERNAL_TABLES
                     else "!! UNGUARDED - add it to INTERNAL_TABLES")
            print(f"       {name:52s} [{verdict}] via {g} at {sc}  {guard}")
        if unguarded:
            print("     Nothing written. An unguarded capture ships a table "
                  "that was ruled not to ship.")
            return 1

    print(f"\n  {len(built)} block(s) ready:")
    for block, (fname, rows, n, n_pub, _prov, dfn, byr, shr) in sorted(
            built.items(), key=lambda kv: -kv[1][2]):
        tiers = Counter(r["access_tier"] for r in rows)
        print(f"     {n:>8,} rows  {fname:52s} -> {block}")
        print(f"                    {len(rows):>3} vars, {n_pub} published, "
              f"{dfn} of {byr} publishable defined ({shr:.0%}), "
              f"tiers {dict(tiers)}")

    if skipped_thin:
        # NAME them. A documentation gap that is only counted is invisible.
        print(f"\n  {len(skipped_thin)} table(s) REFUSED - under "
              f"{CB.MATCH_THRESHOLD:.0%} of the columns 41 would publish have "
              f"an established definition, so a notes contract would look "
              f"documented and would not be:")
        for fname, defined, by_rule, n_col, n, share in sorted(
                skipped_thin, key=lambda r: -r[4]):
            print(f"       {n:>8,} rows  {fname:52s} {defined} of {by_rule} "
                  f"publishable columns defined ({share:.0%}), {n_col} "
                  f"columns total")
    if completed_stubs:
        print(f"\n  {len(completed_stubs)} block(s) exist in "
              f"codebook_master.csv with NO fragment. Writing one is the "
              f"reconcile step, and it is written from the file's own header "
              f"rather than the master's stale row:")
        for fname, block in completed_stubs:
            print(f"       {block} <- {fname}")
    if skipped_collision:
        print(f"\n  {len(skipped_collision)} block key(s) already registered "
              f"by another writer - skipped rather than overwritten:")
        for fname, block in skipped_collision:
            print(f"       {fname} -> {block}")
    if missing:
        print(f"\n  {len(missing)} SHIP table(s) no longer in data/clean:")
        for fname in missing:
            print(f"       {fname}")

    print(f"\n  where the definitions came from:")
    for k, v in prov_total.most_common():
        print(f"     {v:>5}  {k}")

    written = []
    if not check_only:
        print()
        for block, (fname, rows, n, _np, _pv, _d, _b, _s) in sorted(
                built.items()):
            target = FRAG / f"{block}.csv"
            if target.exists():
                # A file that appeared between the check and the write is
                # another agent's. Never overwrite it.
                skipped_collision.append((fname, block))
                print(f"  SKIP {block}: fragment appeared since the check")
                continue
            CB.write_fragment(block, rows, FIELDS)
            back = CB.read(target)
            if len(back) != len(rows):
                print(f"  !! {block}: re-read got {len(back)} rows, wrote "
                      f"{len(rows)}")
                continue
            written.append(block)
        print(f"  wrote and re-read {len(written)} fragment(s) under "
              f"{FRAG.relative_to(CEDAR)}")
        undoc = sum(1 for b in written
                    for r in CB.read(FRAG / f"{b}.csv")
                    if r.get("published") == "1"
                    and not (r.get("description") or "").strip())
        duns = sum(1 for b in written
                   for r in CB.read(FRAG / f"{b}.csv")
                   if "duns" in (r.get("variable") or "").lower()
                   and r.get("access_tier") != "internal")
        print(f"  INVARIANTS re-read from disk: "
              f"published-with-no-description = {undoc} (must be 0) · "
              f"duns not internal = {duns} (must be 0)")
        if undoc or duns:
            return 1

    out = {
        "generated": TODAY,
        "generated_by": "code/392_write_unshipped_codebook_fragments.py",
        "dry_run": check_only,
        "blocks_written": written,
        "blocks_ready": {b: {"file": f, "rows": n, "variables": len(rs),
                             "published_variables": np_,
                             "defined_variables": dfn,
                             "publishable_by_rule": byr,
                             "defined_share": shr}
                         for b, (f, rs, n, np_, _p, dfn, byr, shr)
                         in built.items()},
        "refused_thin_documentation": [
            {"file": f, "defined": a, "publishable_by_rule": b,
             "columns": c, "rows": d, "defined_share": s}
            for f, a, b, c, d, s in skipped_thin],
        "block_key_collisions": [{"file": f, "block": b}
                                 for f, b in skipped_collision],
        "would_capture_non_ship_tables": [
            {"file": f, "verdict": v, "via_block": g, "score": s}
            for f, v, g, s in captured],
        "definition_provenance": dict(prov_total),
        "rows_registered": sum(v[2] for v in built.values()),
        "undefined_columns_tiered_internal": prov_total.get("UNDEFINED", 0),
    }
    # A DRY RUN MUST NOT OVERWRITE THE RECORD OF A REAL ONE. Learned here, the
    # expensive way: a `--check` after the write replaced `blocks_written`
    # with `[]`, and the list of exactly which fragments this script had
    # created - the only safe way to remove them by exact filename, never by
    # glob - was gone. `--check` writes its own file.
    target = REPORT if not check_only else REPORT.with_name(
        REPORT.stem + "_DRYRUN.json")
    tmp = target.with_suffix(".json.part")
    tmp.write_text(json.dumps(out, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    tmp.replace(target)
    print(f"\n  -> {target.relative_to(CEDAR)}")
    print(f"  {out['rows_registered']:,} rows of clean data now have a "
          f"codebook block staged.")
    print("\n  NEXT: py -3 code/cedar_codebook.py build   (fragments -> "
          "master), then 62 -> 87 -> 102 -> 110 -> 25 -> 27, in a quiet "
          "window. See docs/SHIPPING_RUNBOOK.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
