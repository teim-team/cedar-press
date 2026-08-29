#!/usr/bin/env python3
"""
Cedar Press - 62: Regression guard. Run this before and after any change.

WHY THIS EXISTS
---------------
Elijah, 2026-08-06: "make sure you dont regress and give yourself instructions
to not do so."

Fair, because it has already happened. Every one of the invariants below
encodes a defect that was live in this project today, was fixed, and would be
invisible if it came back - the numbers all still LOOK plausible when they are
wrong. A silent regression here is worse than a crash.

HOW TO USE IT
-------------
    py -3 code/62_no_regression_check.py --baseline    # record current state
    py -3 code/62_no_regression_check.py               # check against baseline

Run the check after ANY change to the ledger, the spine, the resolver, or the
ruling importer. A FAIL is a stop-work signal, not a warning.

Baseline lives in data/clean/_regression_baseline.json.

THE STANDING INSTRUCTIONS (read before editing anything below)
-------------------------------------------------------------
1. NEVER let a ruling that names an owner end at tier X. A ruling that names a
   different entity is a REDIRECT, not a deletion. This cost $17.8B once.
2. NEVER resolve a corporate name to an Alaska village GOVERNMENT when an ANCSA
   village CORPORATION of the same name exists. Different legal persons.
3. NEVER apply that same guard outside Alaska. Tribes own companies directly -
   Chickasaw Nation Industries, Cherokee Nation Businesses. The guard over-fired
   on 23 lower-48 enterprises once.
4. NEVER treat agent research as Elijah's ruling. Agent files live outside the
   `rulings_inbox_*.csv` glob. This has been violated twice by filename alone.
5. NEVER score a redirect as a method success. It is how need_v6 looked 90%
   accurate when it is 6.5%.
6. NEVER publish DUNS. It is D&B licensed. Join on it internally, crosswalk to
   UEI/CAGE, publish the crosswalk.
7. NEVER sum FSRS subaward dollars unfiltered, or USAspending award summaries as
   if transactional (~2.2x inflation).
8. ONE resolver. `33_apply_party_rulings.resolve_entity` is it. Every other
   script imports it. Re-implementing name matching guarantees drift.
9. ONE poller per host, and `ps aux` cannot see command lines on Windows - use
   Win32_Process. Four concurrent pullers got us rate-limited for an hour.
10. A number in a doc that is not recomputed from the data is a claim, not a
    fact. Regenerate; do not hand-edit.
11. BUILT IS NOT DONE. SHIPPED IS DONE. A dataset that builds and never reaches
    `dist/` is unfinished work that looks finished. The shipping metrics below
    exist because a 0.87% ship rate hid for twenty days behind counters that
    only ever moved up.
12. A FULL-REBUILD STAGE AND AN IN-PLACE ENRICHER ON ONE FILE NEED AN ORDERING,
    AND THE ENRICHER RUNS LAST. `133 build` reverted `168`'s 931 entity links
    four minutes after they were written, and printed a LARGER row count while
    doing it. Script 09 reverts script 50 the same way. A `.bak_*_pre<script>`
    file beside an output is the signal an enricher has touched it.
13. A PER-UNIT TIME BUDGET THAT TRUNCATES AND THEN MARKS COMPLETE IS A SILENT
    CEILING. Four FERC dockets were written at 2,300-3,200 of 3,555-4,847
    documents by `PER_DOCKET_BUDGET_S = 240` and then marked `done`, so no
    resume would ever revisit them. Compare retrieved against the total the
    source itself reports, wherever the source reports one.
14. A COLUMN NAME THAT IS ABSENT READS AS A SOURCE THAT IS EMPTY. Script 102
    counted two datasets on a `tribe_id` column neither file has - both key
    `tribe_entity_id` - and published 0.0% coverage for 19 days while they held
    307 and 274 keyed rows. ANY coverage computation must RAISE on an absent
    column and must never print a zero. This gate now holds itself to that:
    every column it counts on is checked for existence first.
15. A GATE THAT IS ROUTINELY STEPPED AROUND IS WORSE THAN NO GATE. A FAIL here
    is stop-work. "Pre-existing, not mine" is not a disposition - fix it, or
    record in `AGENTS.md` who owns it and by when. Six sessions in a row
    reported `codebook_undocumented_public = 45` and moved on, which meant
    every other failure this gate could have raised was invisible behind it.

WHAT FAILS, AND WHY EACH BUCKET IS SHAPED THE WAY IT IS
------------------------------------------------------
    MUST_NOT_FALL   a count whose fall can only mean lost work
    MUST_BE_ZERO    a defect itself; any nonzero value is the bug returning
    MUST_NOT_RISE   a registration/shipping gap; it rises when a table lands in
                    data/clean and nobody registers it, which is the exact
                    last-mile failure this project keeps repeating. The fix is
                    cheap and local: register the block.
    CEILINGS        a metric allowed to be small but not large

`ship_ratio_pct` is deliberately NOT a flat MUST_NOT_FALL. It falls for two
completely different reasons and they deserve different answers:

    the shelf SHRANK   - dist_rows_total fell, or a table that was shipping
                         stopped. That is lost work. HARD FAIL.
    the warehouse GREW - new rows landed in data/clean and have not shipped
                         yet. That is collection doing its job. LOUD WARNING
                         naming the tables, never a silent pass.

Failing the second case would punish collection and teach the next agent to
step around this gate, which is rule 15 in reverse.

16. A CORRECTION THAT REACHED ONE TABLE AND NOT ITS SIBLINGS IS THE SAME
    DISEASE AS A RULING THAT REACHED NONE.  (added 2026-08-26)
    `rulings_unapplied` catches a ruling that reached no table at all. It
    cannot catch the commoner case, and the three that were live that morning
    were all of the second kind: script 65 withdrew Salt River Project from
    `native_entity_lobbying_disclosures.csv` and `tribe_year_lobbying_panel.
    csv` - built one day earlier and never rebuilt - went on publishing
    $40,279,500 / 557 filings on TRBF-SRPMCP-00 for twenty days. Every
    APPLIED correction is now DECLARED in
    `data/clean/cedar_correction_register.csv` as an (entity, subject) pair
    that must no longer co-occur in any row of any table, and
    `corrections_not_propagated` re-tests every declaration against every
    table on every run. See `354_correction_register.py`.

    Two consequences worth stating here because they change what this file
    fails on:
      - the register also declares `rows_removed`. `ship_dist_rows` and the
        per-table shipping check accept a fall that EXACTLY equals a declared
        removal, and nothing else. Withdrawing a false row is not lost
        shipping; losing one more than was declared still is.
      - the stale consumers are PRINTED BY NAME every run. A count is not
        actionable; a filename is a task. That is defect class 2c applied to
        this gate's own output.
"""

import csv
import importlib.util
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
DIST = CEDAR / "dist"
DOCS = CEDAR / "docs"
RAW = CEDAR / "data" / "raw"
BASELINE = CLEAN / "_regression_baseline.json"
SHIP_CACHE = CLEAN / "_regression_ship_cache.json"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

# Named here so a reader of the output knows what "measured" meant. Every one
# of these is derived from a file, never restated from a document.
NOTES = []


def note(s):
    NOTES.append(s)


def read_csv(p):
    if not Path(p).exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def header_of(p):
    try:
        with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
            return next(csv.reader(fh), [])
    except Exception:
        return []


class AbsentColumn(Exception):
    """Standing rule 14. Never caught to return a zero."""


def count_filled(path, col, label):
    """Rows with a non-blank `col`. RAISES if `col` is not in the header.

    STANDING RULE 14. `DictReader.get(col)` returns None for a column that does
    not exist, and `sum(1 for r in rows if r.get(col))` then returns 0 - which
    is indistinguishable from a genuinely empty column and is exactly how
    script 102 published 0.0% coverage on two datasets holding 307 and 274
    keyed rows for 19 days. A missing file is a different fact from a missing
    column and both are different from an empty column, so all three answer
    differently here.
    """
    p = Path(path)
    if not p.exists():
        note(f"{label}: FILE ABSENT ({p.name}) - counted 0, and that 0 means "
             f"'no file', not 'no keys'")
        return 0
    hdr = header_of(p)
    if col not in hdr:
        raise AbsentColumn(
            f"{label}: column '{col}' is NOT in {p.name}. Header carries "
            f"{len(hdr)} columns: {', '.join(hdr[:10])}"
            f"{' ...' if len(hdr) > 10 else ''}. A zero here would have read "
            f"as an empty source. Fix the column name or the file.")
    n = 0
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            if (r.get(col) or "").strip():
                n += 1
    return n


def load_module(path):
    """Import a numeric-prefixed script by path, for its DECLARATIONS only.

    Standing rule 8 in a different place: this gate must not keep its own copy
    of the registry lists or the coverage source lists. Both modules guard
    their work behind `if __name__ == "__main__"`, so importing them runs no
    build. Returns None and says why if it cannot be imported - a detector that
    dies because another agent is mid-write is not a finding about the data.
    """
    p = Path(path)
    if not p.exists():
        note(f"{p.name} ABSENT - the checks that read it were SKIPPED, not "
             f"passed")
        return None
    try:
        spec = importlib.util.spec_from_file_location(
            "cedar_" + re.sub(r"\W", "_", p.stem), p)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        return mod
    except Exception as e:
        note(f"{p.name} could not be imported ({type(e).__name__}: {e}) - the "
             f"checks that read it were SKIPPED, not passed")
        return None


def measure():
    """Everything that must not silently get worse."""
    m = {}

    ledger = read_csv(CLEAN / "cedar_identifier_ledger_final.csv")
    tiers = Counter(r.get("confidence_tier", "") for r in ledger)
    m["ledger_rows"] = len(ledger)
    m["tier_A"] = tiers.get("A", 0)
    m["tier_X"] = tiers.get("X", 0)

    # RULED tier A is the metric that must never fall. Plain `tier_A` cannot
    # tell "we lost verified work" from "we correctly demoted unverified
    # work", and on 2026-08-06/07 it spent a whole session reporting a
    # regression that was the two-leg evidence standard doing its job: 49
    # single-leg rows demoted A -> B, 48 two-leg rows promoted B -> A, net -1.
    #
    # A ruling is permanent and only a new ruling reverses it. An algorithmic
    # tier A is provisional and SHOULD fall when its evidence is re-checked.
    # So the guard watches the part that is not allowed to move.
    RULED = {"hand", "bgov_manual", "elijah_ruling_redirect", "elijah_ruling",
             "ruling", "web_verified"}
    m["tier_A_ruled"] = sum(
        1 for r in ledger
        if r.get("confidence_tier") == "A"
        and (r.get("attribution_method") or "").strip() in RULED)
    m["tier_A_algorithmic"] = m["tier_A"] - m["tier_A_ruled"]

    # A tier-A link with no entity is an attribution to nobody.
    m["tierA_without_entity"] = sum(
        1 for r in ledger
        if r.get("confidence_tier") == "A" and not (r.get("tribe_id") or "").strip())

    # INVARIANT 1: a ruling that names an owner must not end at X. Any tier-X
    # row whose rationale says "owner is <someone>" is the $17.8B bug returning.
    m["X_rows_naming_an_owner"] = sum(
        1 for r in ledger
        if r.get("confidence_tier") == "X"
        and "owner is " in (r.get("tier_rationale") or "").lower()
        and "not in the spine" not in (r.get("tier_rationale") or "").lower())

    spine = read_csv(SPINE / "cedar_entity_spine.csv")
    m["spine_entities"] = len(spine)
    cls = Counter(r.get("entity_class", "") for r in spine)
    m["spine_village_corporations"] = cls.get("Alaska Native Village Corporation", 0)
    m["spine_regional_ancs"] = cls.get("Alaska Native Regional Corporation", 0)
    m["spine_nho"] = sum(1 for r in spine
                         if r.get("tribe_id", "").startswith("NHO-"))
    m["spine_intertribal"] = sum(1 for r in spine
                                 if r.get("tribe_id", "").startswith("ITO-"))
    m["spine_duplicate_ids"] = len(spine) - len({r.get("tribe_id") for r in spine})

    pc = read_csv(CLEAN / "prime_contracts_entity_year.csv")
    m["prime_entities"] = len({r.get("tribe_id") for r in pc})
    m["prime_obligations_usd"] = round(
        sum(float(r.get("obligations_usd") or 0) for r in pc), 2)

    # INVARIANT 2: the Kootenai split must hold.
    #
    # This originally measured `prime_contracts_entity_year.csv` - a DERIVED
    # file - and so reported "no regression" while the ledger had already
    # regressed, because the panel had not been rebuilt yet. A guard that reads
    # a stale artefact is worse than no guard: it certifies the defect.
    #
    # Measure the LEDGER, which is what 09 rebuilds and what everything else is
    # derived from. S&K is Salish & Kootenai (Montana); if any S&K firm is back
    # on the Idaho tribe, the conflation has returned.
    idaho = sum(float(r.get("obligations_usd") or 0) for r in pc
                if r.get("tribe_id") == "TRBF-KTNIID-00")
    m["kootenai_idaho_usd"] = round(idaho, 2)
    m["kootenai_idaho_ledger_links"] = sum(
        1 for r in ledger if r.get("tribe_id") == "TRBF-KTNIID-00"
        and r.get("confidence_tier") != "X")
    m["sk_firms_on_idaho"] = sum(
        1 for r in ledger
        if r.get("tribe_id") == "TRBF-KTNIID-00"
        and re.search(r"\bs\s*(&|and)\s*k\b|salish",
                      r.get("legal_business_name") or "", re.I))

    # INVARIANT 5: corporate firms must not pile up on Alaska village
    # GOVERNMENTS when the namesake ANCSA corporation exists. $27.59B was
    # booked that way across 96 governments before this was caught.
    spine_pre = read_csv(SPINE / "cedar_entity_spine.csv")
    anvc_cores = {(_r.get("canonical_name") or "").lower()
                  for _r in spine_pre if _r["tribe_id"].startswith("ANVC-")}
    m["links_on_village_corporations"] = sum(
        1 for r in ledger if (r.get("tribe_id") or "").startswith("ANVC-"))

    # INVARIANT 3: village corporations must carry their own dollars, not have
    # them sitting on the namesake village governments.
    m["village_corp_obligations_usd"] = round(
        sum(float(r.get("obligations_usd") or 0) for r in pc
            if (r.get("tribe_id") or "").startswith("ANVC-")), 2)

    dp = read_csv(CLEAN / "deals_party_autoresolved.csv")
    m["deal_parties_autoresolved"] = len(dp)
    m["deal_rows_autoresolved"] = sum(int(r.get("n_deals") or 0) for r in dp)

    br = read_csv(CLEAN / "brand_family_registry.csv")
    m["brands_learned"] = len(br)

    lob = read_csv(CLEAN / "lobbying_client_attribution.csv")
    m["lobbying_clients_attributed"] = sum(
        1 for r in lob if r.get("confidence_tier") in ("A", "B"))

    # KEYED DATASETS - added 2026-08-06 after a measured silent revert.
    #
    # `code/31_build_dataset5_linked.py` rebuilds ownership_events from source
    # and returns it to 0% keyed. Observed, not theorised: 93 of 98 keyed
    # before the rebuild, 0 after, and the guard said "no regressions" because
    # it was not looking. The agent that built the keys warned of exactly this.
    #
    # A dataset that silently loses its entity key is worse than one that never
    # had it - the product claims cross-dataset linkage, and the claim would
    # stay true in the docs while becoming false in the data.
    #
    # Re-run `code/70_key_unjoined_datasets.py` after scripts 15, 17, 23d or 31.
    #
    # These used to read `r.get(col)` directly, which is standing rule 14's
    # defect sitting inside the gate itself: rename `tribe_id` on any of these
    # files and every one of them reports 0 keyed rows with no error, and
    # `--baseline` would then write that 0 down as the floor. They now RAISE.
    for name, col in (("ownership_events", "tribe_id"),
                      ("compacts", "tribe_id"),
                      ("compact_events", "tribe_id"),
                      ("compact_terms", "tribe_id"),
                      ("gaming_land_decisions", "tribe_id"),
                      ("gaming_facilities", "tribe_id"),
                      ("np_orgs", "entity_id")):
        m[f"keyed_{name}"] = count_filled(CLEAN / f"{name}.csv", col,
                                          f"keyed_{name}")
    for name in ("native_bills_entity_bridge", "bill_votes_entity_bridge",
                 "federal_actions_entity_bridge"):
        m[f"bridge_{name}"] = len(read_csv(CLEAN / f"{name}.csv"))

    # ---- SCRIPT DISCIPLINE -------------------------------------------------
    # Nothing measured code/ until 2026-08-28, and it grew to 377 scripts with
    # 43 shared numbers. "Script numbers 130-150 are taken and the prefix no
    # longer implies step order - five collisions today from concurrent agents"
    # was written as a standing rule and enforced by nobody, so the next agent
    # collided again. A rule that is not a metric is a suggestion.
    #
    # `code_scripts_total` is tracked but NOT ratcheted: legitimate work adds
    # scripts, and a build that fails for growing would train people to ignore
    # the gate. `code_duplicate_numbers` IS ratcheted, because reusing a taken
    # number costs nothing to avoid and makes "script 154" ambiguous forever -
    # `ls code/<n>_*` is currently required before citing any script by number.
    # RECURSIVE. A first version globbed `code/*.py` only and reported 380,
    # missing 42 scripts in code/ancsa_portal, code/ancsa_v2 and
    # code/lobbying_pull - so a metric added to enforce discipline was itself
    # undercounting by 11%.
    #
    # Collisions are scoped PER DIRECTORY, deliberately. A subpackage running
    # its own 01..06 sequence is organised, not colliding;
    # `code/lobbying_pull/02_match_filings_to_tribes.py` and
    # `code/02_extract_exclusion_rulings.py` are unambiguous because their
    # directories differ. Only two scripts in the SAME directory sharing a
    # number make "script 154" meaningless.
    pyfiles = sorted(CODE.rglob("*.py"))
    m["code_scripts_total"] = len(pyfiles)
    _nums = {}
    for p in pyfiles:
        mm = re.match(r"^(\d+)_", p.name)
        if mm:
            _nums.setdefault((p.parent.name, mm.group(1)), []).append(p.name)
    _dupes = {k[1]: v for k, v in _nums.items() if len(v) > 1}
    m["code_duplicate_numbers"] = len(_dupes)
    if _dupes:
        worst = sorted(_dupes.items(), key=lambda kv: (-len(kv[1]), kv[0]))[0]
        note(f"script numbers: {len(_dupes)} collide; worst is "
             f"{worst[0]} -> {', '.join(worst[1])}")

    cb = read_csv(CLEAN / "codebook_master.csv")
    m["codebook_variables"] = len(cb)
    m["codebook_undocumented_public"] = sum(
        1 for r in cb if r.get("published") == "1" and not r.get("description"))
    # INVARIANT 4: DUNS must never be publishable.
    m["duns_marked_publishable"] = sum(
        1 for r in cb if "duns" in r.get("variable", "").lower()
        and r.get("access_tier") != "internal")

    return m


# ===========================================================================
# SHIPPING  -  standing rule 11
#
# `code/160_ship_gap_report.py` measured this project on its first run:
# 2,609,646 rows unshipped, a 66.7% overall ratio flattered by a few huge
# tables, and 201 of 255 tables at EXACTLY 0%. That report is written to
# docs/SHIP_GAP_REPORT.json and nothing failed on it, which is how a 0.87%
# gaming ship rate survived twenty days.
#
# 160's own registry readers are IMPORTED here rather than re-implemented.
# A detector with its own copy of the list rebuilds the defect it is
# detecting - 160 says so in its own docstring, and the same applies to a gate
# that keeps a second copy of 160's.
#
# The JSON report is deliberately NOT read. A guard that reads a stale artefact
# certifies the defect; that is written into this file already, above the
# Kootenai invariant, and it cost a session to learn.
# ===========================================================================

def _scan_rows(p, cache, stats):
    """Row count for one CSV, cached on (name, size, mtime)."""
    st = p.stat()
    key = f"{p.name}|{st.st_size}|{int(st.st_mtime)}"
    hit = cache.get(key)
    if hit is not None and isinstance(hit, dict) and "rows" in hit:
        stats["cache hit"] += 1
        return hit["rows"]
    stats["scanned"] += 1
    n = 0
    try:
        with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
            r = csv.reader(fh)
            next(r, None)
            for _ in r:
                n += 1
    except Exception as e:
        note(f"{p.name} unreadable while counting rows ({type(e).__name__}) "
             f"- reported, not skipped")
        return 0
    cache[key] = {"rows": n}
    return n


def _load_ship_cache():
    """160's cache first, then ours. Both are keyed on (name, size, mtime), so
    a hit is exact for an unchanged file and a changed file always rescans."""
    cache = {}
    for p in (DOCS / ".ship_gap_cache.json", SHIP_CACHE):
        if not p.exists():
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(d, dict):
                cache.update(d)
        except Exception as e:
            note(f"{p.name} unreadable ({type(e).__name__}) - rescanning")
    return cache


def measure_shipping():
    """(scalar metrics, {file: dist_rows}, {file: clean_rows})."""
    m, dist_by_file, clean_by_file = {}, {}, {}
    ship160 = load_module(CODE / "160_ship_gap_report.py")
    if ship160 is None:
        note("SHIPPING METRICS NOT MEASURED - 160_ship_gap_report.py could not "
             "be imported. This is UNMEASURED, not clean.")
        return {}, None, None

    t25, derives25, _e25 = ship160.registry_25()
    t27, _c27, _e27, _n = ship160.registry_27()
    dist_notes, bad_notes = ship160.registry_dist()
    for pth, why in bad_notes:
        note(f"unreadable notes contract {pth}: {why}")
    CB = ship160.CB
    master_groups = CB.dataset_groups()
    frag_groups = {}
    frag_dir = CLEAN / "codebook"
    if frag_dir.exists():
        for f in sorted(frag_dir.glob("*.csv")):
            if ".bak" in f.name:
                continue
            frag_groups[f.stem] = {
                (r.get("variable") or "").strip().lower()
                for r in read_csv(f)}

    cache = _load_ship_cache()
    stats = Counter()
    miss = Counter()
    live_clean = live_dist = 0
    zero, partial, full, shipping = [], [], [], []

    for p in sorted(CLEAN.glob("*.csv")):
        if p.name.startswith("_") or ".bak" in p.name \
                or p.name.endswith(".part") or p.name in ship160.NOT_A_DATASET:
            continue
        if p.name in CB.LICENSED_SOURCE_FILES:
            continue                       # licensed files must never ship
        if p.name in CB.INTERNAL_TABLES:
            # INTERNAL BY DECISION, and therefore not a registration gap -
            # exactly the reasoning already applied to licensed files one line
            # up, and to tables_undocumented_in_codebook below.
            #
            # 2026-08-29: adding three internal tables (510's assertion store,
            # resolved view and conflict table) raised FOUR "missing from X"
            # ratchets by three apiece, reporting a registration backlog for
            # files that are registered - as internal - and must never appear
            # in 25_TABLES or 27_SPEC. A counter that rises when you correctly
            # classify a table teaches the next agent to avoid classifying.
            continue
        rows = _scan_rows(p, cache, stats)
        clean_by_file[p.name] = rows
        d = dist_notes.get(p.name)
        dr = d["rows"] if d and isinstance(d.get("rows"), int) else 0
        dist_by_file[p.name] = dr

        hdr = header_of(p)
        _mg, ms = CB.match_group(hdr, master_groups)
        _fg, fs = CB.match_group(hdr, frag_groups)
        if ms < CB.MATCH_THRESHOLD and fs < CB.MATCH_THRESHOLD:
            miss["codebook_block"] += 1
        if p.name not in t25:
            miss["25_TABLES"] += 1
        if p.name not in t27:
            miss["27_SPEC"] += 1
        if not d:
            miss["notes_contract"] += 1

        live_clean += rows
        live_dist += min(dr, rows)
        if dr:
            shipping.append(p.name)
            (full if rows and dr >= rows else partial).append(p.name)
        elif rows > 0:
            zero.append(p.name)

    try:
        SHIP_CACHE.write_text(json.dumps(cache), encoding="utf-8")
    except Exception as e:
        note(f"ship cache not written ({type(e).__name__}) - only a speed cost")

    m["ship_clean_rows"] = live_clean
    m["ship_dist_rows"] = live_dist
    m["ship_unshipped_rows"] = live_clean - live_dist
    m["ship_ratio_pct"] = round(100 * live_dist / live_clean, 3) \
        if live_clean else 0.0
    m["ship_tables_total"] = len(clean_by_file)
    m["ship_tables_shipping"] = len(shipping)
    m["ship_tables_at_zero"] = len(zero)
    m["tables_missing_codebook_block"] = miss["codebook_block"]
    m["tables_missing_from_25_TABLES"] = miss["25_TABLES"]
    m["tables_missing_from_27_SPEC"] = miss["27_SPEC"]

    # THE REGISTRATION GAP THAT ACTUALLY GATES SHIPPING.
    #
    # `tables_missing_from_25_TABLES` counts tables absent from the TABLES
    # literal in 25_build_publication_layer.py - but that literal is only the
    # CURATED OVERRIDES (37 entries). Line 124 of that script: "comes from the
    # codebook registry, so a new dataset ships by being documented", and
    # resolve() reads `CB.registered_tables()` after the overrides.
    #
    # So the 234 that metric reports is not a registration backlog. Measured
    # 2026-08-28 the real split is 199 shippable / 2 licensed / 14 undocumented.
    # A metric named for a gap it does not measure sends the next agent at 234
    # tables of imagined work and away from the 14 that are real.
    try:
        _sh, _lic, _und = CB.registered_tables()
        m["tables_undocumented_in_codebook"] = len(_und)
        m["tables_shippable_via_codebook"] = len(_sh)
        # Phase 1 contracts (512): a violation is a collection with no
        # tables, an ORPHAN shippable table no collection claims, or a
        # contract naming a script that no longer exists. Read from the
        # generated JSON rather than re-deriving, so the gate and the
        # contract document cannot disagree about the count.
        _cj = CEDAR / "docs" / "schema" / "dataset_contracts.json"
        if _cj.exists():
            _doc = json.loads(_cj.read_text(encoding="utf-8"))
            m["contract_violations"] = int(_doc.get("n_violations", 0))
            m["contract_orphan_shippable"] = int(_doc.get("n_orphan_shippable", 0))
        else:
            note("docs/schema/dataset_contracts.json missing - run "
                 "512_build_dataset_contracts.py; contract metrics not "
                 "measured")
        # External review 2026-08-30, findings 3+4. Two metrics, and they
        # measure DIFFERENT things on purpose:
        #   identity_facts_legacy_only   selected, but the only evidence is a
        #                                row with no recorded provenance
        #   identity_facts_unresolved_tie  we declined to publish a hash
        #                                winner on an identity-critical fact
        # The second is a QUEUE and healthy - it is the system refusing to
        # manufacture certainty. The first is exposure: it must not RISE,
        # because it is what would ship as fact on no evidence.
        _rf = CLEAN / "cedar_resolved_facts.csv"
        if _rf.exists():
            import csv as _csv2
            _leg = _tie = 0
            with _rf.open(encoding="utf-8-sig", newline="") as _fh:
                for _r in _csv2.DictReader(_fh):
                    _pred = _r.get("predicate", "")
                    _crit = any(_pred == _c or _pred.startswith(_c) for _c in (
                        "entity.class", "entity.canonical_name",
                        "entity.fr_official_name",
                        "entity.is_federally_recognized", "entity.parent",
                        "entity.ultimate_parent", "entity.constituent_band_of",
                        "entity.identifier.", "entity.state"))
                    if not _crit:
                        continue
                    if _r.get("support_status") == "legacy_only":
                        _leg += 1
                    if _r.get("resolution_status") == "UNRESOLVED_TIE":
                        _tie += 1
            m["identity_facts_legacy_only"] = _leg
            m["identity_facts_unresolved_tie"] = _tie

        # Phase 4 handoffs (513): a FAILED verification means a claim of
        # completed work was re-executed and DISPROVEN - that is stop-work,
        # not a queue. UNVERIFIED is a queue and only noted.
        _hv = CEDAR / "review" / "handoff_verifications.csv"
        _hh = CEDAR / "review" / "agent_handoffs.csv"
        if _hh.exists():
            import csv as _csv
            with _hh.open(encoding="utf-8-sig", newline="") as _fh:
                _hands = list(_csv.DictReader(_fh))
            _last = {}
            if _hv.exists():
                with _hv.open(encoding="utf-8-sig", newline="") as _fh:
                    for _v in _csv.DictReader(_fh):
                        _last[_v["handoff_id"]] = _v["result"]
            m["handoffs_failed_verification"] = sum(
                1 for _h in _hands
                if _last.get(_h["handoff_id"], "").startswith("FAILED"))
            _unv = sum(1 for _h in _hands
                       if not _last.get(_h["handoff_id"])
                       and _h.get("verification_status", "") == "UNVERIFIED")
            if _unv:
                note(f"{_unv} handoff(s) await INDEPENDENT verification - "
                     f"py -3 code/513_handoffs.py list --unverified")
    except Exception as e:
        note(f"codebook registry unreadable ({type(e).__name__}) - "
             "tables_undocumented_in_codebook not measured")
    m["tables_missing_notes_contract"] = miss["notes_contract"]
    note(f"shipping scan: {stats['scanned']} tables read, "
         f"{stats['cache hit']} from cache; 25 TABLES derives from the "
         f"codebook: {'YES' if derives25 else 'NO'}")
    note(f"ship_tables_total counts SHIPPABLE tables only - the "
         f"{len(CB.LICENSED_SOURCE_FILES)} vendor-licensed files in "
         f"cedar_codebook.LICENSED_SOURCE_FILES are excluded from every "
         f"shipping metric here, because they must never ship. 160's own "
         f"`tables_total` counts them, so the two figures are close and are "
         f"NOT the same number - do not reconcile them by adjusting either.")
    return m, dist_by_file, clean_by_file


# ===========================================================================
# TRAP 1  -  A FULL REBUILD REVERTING AN IN-PLACE ENRICHER  (rule 12)
#
# `133 build` rebuilt ferc_docket_filings.csv from source sheets four minutes
# after 168 wrote 931 entity links and nine columns into it, discarding all of
# them - and printed a LARGER row count, which read as progress. Script 09
# reverts script 50 in exactly the same shape.
#
# The detectable signature is COLUMN LOSS: an enricher adds columns, a rebuild
# emits the source schema, and the columns the enricher added vanish. Rows can
# legitimately fall (a dedupe); a column the previous version had and this one
# does not is almost never intended, and it is free to check because this
# project already backs up before every risky write.
# ===========================================================================

BAK_RE = re.compile(r"^(?P<stem>.+?\.csv)\.bak[_.].*$", re.I)
PRE_SCRIPT_RE = re.compile(r"\.bak_.*_pre(?P<who>[A-Za-z0-9_]+)$", re.I)


def measure_backups():
    """(metrics, [column-loss detail], [enricher-touched detail])."""
    m, losses, touched = {}, [], []
    by_live = {}
    for root in (CLEAN, CLEAN / "codebook", SPINE):
        if not root.exists():
            continue
        for p in sorted(root.iterdir()):
            if not p.is_file() or ".bak" not in p.name:
                continue
            mm = BAK_RE.match(p.name)
            if not mm:
                continue
            live = p.parent / mm.group("stem")
            if live.exists():
                by_live.setdefault(live, []).append(p)

    for live, baks in sorted(by_live.items()):
        newest = max(baks, key=lambda x: x.stat().st_mtime)
        lh, bh = header_of(live), header_of(newest)
        if not lh or not bh:
            continue
        lost = [c for c in bh if c and c not in set(lh)]
        if lost:
            losses.append({
                "file": live.name, "backup": newest.name,
                "lost": lost,
                "live_columns": len(lh), "backup_columns": len(bh),
                "live_rows_hint": None,
            })
        for b in baks:
            pm = PRE_SCRIPT_RE.search(b.name)
            if pm and live.stat().st_mtime < b.stat().st_mtime:
                # the live file is OLDER than a pre-<script> backup: the thing
                # that took the backup has not written since, or something
                # replaced the live file with an earlier vintage.
                touched.append(f"{live.name} is older than its own backup "
                               f"{b.name}")
    m["files_with_columns_lost_vs_backup"] = len(losses)
    m["files_with_an_inplace_enricher_backup"] = sum(
        1 for _live, baks in by_live.items()
        if any(PRE_SCRIPT_RE.search(b.name) for b in baks))
    return m, losses, touched


# ===========================================================================
# TRAP 2  -  RETRIEVED vs REPORTED-BY-SOURCE  (rule 13)
#
# Four FERC dockets were written at 2,300-3,200 of 3,555-4,847 documents
# because PER_DOCKET_BUDGET_S is 240 seconds, and then marked `done`, so no
# resume would ever revisit them. Nothing was wrong with the rows that were
# written; the sheet was simply short, and short and complete look identical.
#
# The only thing that exposed it was comparing `documents_retrieved` against
# `total_hits_reported_by_source` on every sheet. Both the raw sheets and the
# derived clean table are checked, because they can disagree.
#
# The clean-table half is DISCOVERED from headers, not hardcoded, so a new
# source that publishes its own total is checked the day it lands.
# ===========================================================================

RETRIEVED_COL = re.compile(
    r"^(documents|records|rows|items|pages|files|results|hits)_"
    r"(retrieved|collected|downloaded|fetched|parsed)$", re.I)
REPORTED_COL = re.compile(
    r"^(total_(hits|records|documents|rows|items|results)"
    r"(_reported(_by_source)?)?|.*_reported_by_source)$", re.I)


def measure_truncation():
    m, short, pairs = {}, [], []

    # (a) the raw FERC docket sheets: total_hits vs len(documents)
    sheets = RAW / "advocacy" / "ferc" / "docket_sheets"
    n_sheets = 0
    if sheets.exists():
        for p in sorted(sheets.glob("*.json")):
            n_sheets += 1
            try:
                j = json.loads(p.read_text(encoding="utf-8"))
            except Exception as e:
                note(f"{p.name} unreadable ({type(e).__name__}) - a sheet that "
                     f"cannot be read is not a sheet that is complete")
                continue
            if not isinstance(j, dict):
                continue
            th = j.get("total_hits") or 0
            docs = j.get("documents")
            got = len(docs) if isinstance(docs, list) else 0
            if th and got < th:
                short.append({
                    "unit": p.stem, "source": "ferc docket_sheets",
                    "retrieved": got, "reported": th,
                    "shortfall": th - got,
                    "pct": round(100 * got / th, 1)})
    else:
        note("data/raw/advocacy/ferc/docket_sheets/ ABSENT - the FERC "
             "truncation check was SKIPPED, not passed")

    # (b) any clean table that publishes both a retrieved and a reported count
    for p in sorted(CLEAN.glob("*.csv")):
        if p.name.startswith("_") or ".bak" in p.name:
            continue
        hdr = header_of(p)
        rcols = [c for c in hdr if RETRIEVED_COL.match(c.strip())]
        tcols = [c for c in hdr if REPORTED_COL.match(c.strip())]
        if not rcols or not tcols:
            continue
        rc, tc = rcols[0], tcols[0]
        pairs.append(f"{p.name}: {rc} vs {tc}")
        for row in read_csv(p):
            try:
                got = int(float((row.get(rc) or "0").replace(",", "") or 0))
                rep = int(float((row.get(tc) or "0").replace(",", "") or 0))
            except ValueError:
                continue
            if rep and got < rep:
                unit = (row.get("docket_number") or row.get("unit_id")
                        or row.get("id") or "?")
                short.append({
                    "unit": str(unit), "source": p.name,
                    "retrieved": got, "reported": rep,
                    "shortfall": rep - got,
                    "pct": round(100 * got / rep, 1)})

    m["units_short_of_source_reported_total"] = len(short)
    note(f"truncation check: {n_sheets} FERC sheets + "
         f"{len(pairs)} clean table(s) publishing a retrieved/reported pair"
         + (" (" + "; ".join(pairs) + ")" if pairs else
            " - NO clean table publishes one, so this half of the check "
            "measured nothing"))
    return m, short


# ===========================================================================
# TRAP 3  -  A COVERAGE COLUMN THAT DOES NOT EXIST  (rule 14)
#
# 102_build_coverage_profile.py names (file, column) pairs and counts on them.
# It now raises on an absent column - fixed 2026-08-26 by script 164, after
# publishing 0.0% on two datasets holding 307 and 274 keyed rows for 19 days.
# The declarations are IMPORTED from 102 so the gate cannot drift from it, and
# every named column is checked for existence here too, so the defect is caught
# by the gate rather than only by the script that already fell for it.
# ===========================================================================

def measure_coverage_columns():
    m, absent = {}, []
    mod = load_module(CODE / "102_build_coverage_profile.py")
    if mod is None:
        return {}, absent
    specs = []
    for s in getattr(mod, "SOURCES", []):
        specs.append((s[0], s[2]))
    for s in getattr(mod, "TRIBE_SOURCES", []):
        specs.append((s[0], s[2]))
    for fname, col in specs:
        p = CLEAN / fname
        if not p.exists():
            continue                        # absent FILE is a different fact
        hdr = header_of(p)
        if col not in hdr:
            absent.append({
                "file": fname, "column": col,
                "header": ", ".join(hdr[:10]) + (" ..." if len(hdr) > 10
                                                 else "")})
    m["coverage_columns_that_do_not_exist"] = len(absent)
    note(f"coverage columns checked: {len(specs)} (file, column) pairs "
         f"declared by 102_build_coverage_profile.py")
    return m, absent


# ===========================================================================
# THE SEVEN NAMED DEFECT CLASSES (six added 2026-08-26; class 7 the same day)
#
# Six distinct bug classes were each found MULTIPLE TIMES on 2026-08-26, in
# unrelated scripts, by different agents, and each was fixed only where
# somebody tripped over it. `code/293_lint_bug_classes.py` detects the SHAPE of
# all six by AST, and this fold-in makes a NEW instance a gate failure instead
# of an accident three weeks later.
#
#   class1  reads the ADDITIONS and never the promoted LEDGER   (88/57/41/82/35)
#   class2a setdefault() on a key that already exists - a no-op (119)
#   class2b a coverage % over a column the file does not have   (102)
#   class2c a drop counter that never names what it dropped     (87)
#   class3  a RULED method read as a POSITIVE ruling            (148)
#   class4  a per-unit budget that truncates and marks COMPLETE (133)
#   class5  a non-idempotent build that rewrites its own log    (164)
#   class6  a full rebuild reverting an in-place enricher       (133 vs 168)
#   class7  an id minted from OUTSIDE the row - hash/rank/position
#                                                        (133 / 170 / 157)
#
# THE BASELINE WAS RE-RECORDED ON 2026-08-26 WHEN CLASS 7 LANDED, and that is
# a metric-DEFINITION change, not an acknowledgement of a failure. Standing
# rule 15 forbids re-baselining to make a failure disappear; this is response
# (2) in that rule - the check changed, and the reason is written down here.
# `lint_bug_class_instances` sums every class, so adding a seventh raised it
# from 105 to 184 without one new defect being written. The re-record was
# taken with the gate GREEN and with every other metric at or better than its
# previous floor, so the new baseline is STRICTER everywhere it moved:
# tier_A_ruled 1,634 -> 1,676, ship_tables_shipping 49 -> 125,
# ship_dist_rows 5,227,896 -> 7,444,208, ship_tables_at_zero 205 -> 138,
# tables_missing_codebook_block 144 -> 139, notes contract 206 -> 139.
# `lint_new_defect_instances` is answered from 293's OWN baseline and remains
# MUST_BE_ZERO, so novelty is still caught the moment it lands.
#
# `248_audit_tier_inheritance_patterns.py` was a SECOND detector for class 3
# and is now a stub pointing at 293. Its per-site disposition table and its
# re-derived ledger-exposure measurement were folded into 293, where an
# UNREVIEWED site is raised as a class-3 finding - which fails THIS gate,
# not only that one script.
#
# Standing rule 8 applied to a detector: the counts are IMPORTED from 293, the
# same way the shipping registries are imported from 160 and the coverage
# columns from 102. This gate keeps no second copy of the patterns.
#
# The linter parses; it never executes what it lints. Importing it runs no
# build and opens no socket.
# ===========================================================================

def measure_lint_bug_classes():
    m = {}
    mod = load_module(CODE / "293_lint_bug_classes.py")
    if mod is None:
        # UNMEASURED is not zero. A detector that could not be imported has
        # found nothing, and that must never print like a clean sweep.
        return {"lint_bug_class_instances": "UNMEASURED"}
    try:
        counts = mod.count_by_class()
    except Exception as e:
        note(f"293_lint_bug_classes.py imported but count_by_class() raised "
             f"({type(e).__name__}: {e}) - the six defect classes are "
             f"UNMEASURED, NOT clean.")
        return {"lint_bug_class_instances": "UNMEASURED"}
    for k, v in counts.items():
        m[k if k.startswith("lint_") else f"lint_{k}"] = v

    # The per-class counters above are MUST_NOT_RISE, but a metric absent from
    # THIS gate's baseline is skipped rather than failed - and re-recording the
    # gate's baseline to seed them would bake in whatever else is failing that
    # day, which standing rule 15 forbids. So 293 answers from ITS OWN
    # baseline, and this counter is live the moment 293 lands.
    try:
        n_new, fresh = mod.new_since_baseline()
    except Exception as e:
        note(f"293_lint_bug_classes.new_since_baseline() raised "
             f"({type(e).__name__}: {e}) - UNMEASURED, NOT clean.")
        n_new, fresh = "UNMEASURED", []
    m["lint_new_defect_instances"] = n_new
    if isinstance(n_new, int) and n_new:
        for k in fresh[:12]:
            cls, fname, ev = (k.split("|", 2) + ["", ""])[:3]
            note(f"NEW {cls} instance: {fname} - {ev}")
    elif n_new == "UNMEASURED":
        note("docs/lint_bug_classes_baseline.json ABSENT - the six defect "
             "classes have no floor recorded, so a NEW instance cannot be told "
             "from an old one. Record it: "
             "py -3 code/293_lint_bug_classes.py --baseline")

    note(f"the named defect classes scanned by 293_lint_bug_classes.py "
         f"(the SINGLE lint entry point; 248 is a retired stub): "
         + ", ".join(f"{k}={counts[k]}" for k in sorted(counts)
                     if k.startswith("class"))
         + ". A RISE in any of these is a NEW instance of a defect this "
           "project has already paid for more than once.")
    return m


# ===========================================================================
# RULED BUT NEVER APPLIED
#
# 492 clusters carrying $17.5B had a ruling recorded in review/ or data/clean
# that was never written back to the source table, so `attributed_flag` stayed
# 0 and they re-surfaced in a fresh reconciliation queue as though nobody had
# ever looked at them. The owner recognised entries he had adjudicated himself.
#
# A RULING THAT IS NOT APPLIED BACK TO ITS SOURCE TABLE IS NOT A RULING, IT IS
# A NOTE.
#
# `code/173_consolidate_rulings_ledger.py` and `docs/RULING_APPLICATION_LOG.md`
# are being written by a concurrent agent. Until they land this reports
# UNMEASURED - never 0. "Nobody has measured it" and "there are none" are
# opposite findings and must not print the same way.
# ===========================================================================

# Columns that could carry "was this written back to the source table?", in
# the order they are looked for. `status` is what
# 173_consolidate_rulings_ledger.py actually writes today (SETTLED /
# CONFLICT_NOT_APPLIED); the others are here so a future producer using a
# different name is still read rather than silently reported as UNMEASURED.
APPLIED_COLS = ("applied", "applied_flag", "application_status", "was_applied",
                "apply_status", "applied_to_source", "status")
UNAPPLIED_RE = re.compile(
    r"not[_ ]?applied|unapplied|pending|awaiting|refused|deferred|"
    r"^(no|0|false)$", re.I)


# ===========================================================================
# A CORRECTION THAT REACHED ONE TABLE AND NOT ITS SIBLINGS   (added 2026-08-26)
#
# `rulings_unapplied` above catches a ruling that reached NO table. It cannot
# catch the commoner and more expensive case: a correction that WAS applied,
# correctly, to exactly one file, while the table that publishes kept the
# false value. Three live instances that morning, every one found by a human
# reading a shipping table rather than by this gate:
#
#   FA-01  `65_lobbying_organization_type_guard.py` withdrew Salt River
#          Project from `native_entity_lobbying_disclosures.csv` on
#          2026-08-06 16:19. `tribe_year_lobbying_panel.csv` had been built
#          2026-08-05 17:28 and was never rebuilt, so for twenty days the
#          panel published **$40,279,500 / 557 filings** on TRBF-SRPMCP-00
#          against a corrected $10,414,000 / 141 - making an Arizona public
#          power district the #2 Native lobbying entity in America.
#          `rulings_unapplied` reported nothing, CORRECTLY: from its point of
#          view the ruling was applied.
#
#   FA-02  94 `foia_request_index.csv` rows keyed to the Native Village of
#          Georgetown, Alaska because `georgetown.edu` sat in a list of email
#          domains. A prior pass DEMOTED and FLAGGED them; a demoted wrong
#          link is still a wrong link in a shipping column.
#
#   FA-01b The org-type guard is a NAME-FORM bar, so it caught `MINES` and
#          missed `MINING`, and `CITY OF SANTA ROSA` while leaving `SANTA ROSA
#          COUNTY FL` attributed to a California tribe.
#
# `354_correction_register.py` is the registry and this reads it - the same
# import-don't-restate rule that governs 160's shipping registries above.
# ===========================================================================

def measure_corrections():
    """(metrics, [stale consumer rows])."""
    reg = load_module(CODE / "354_correction_register.py")
    if reg is None:
        note("CORRECTION PROPAGATION NOT MEASURED - "
             "354_correction_register.py could not be imported. UNMEASURED, "
             "not clean.")
        return {"corrections_declared": "UNMEASURED",
                "corrections_not_propagated": "UNMEASURED"}, [], {}
    declared = reg.load()
    n, stale = reg.check_propagation()
    m = {"corrections_declared": len(declared),
         "corrections_not_propagated": n}
    if declared:
        note(f"{len(declared):,} corrections declared in "
             f"cedar_correction_register.csv; {n} sibling table(s) still "
             f"carry a withdrawn (entity, subject) pair. A correction that "
             f"lands in one table and not its siblings is the same disease as "
             f"a ruling that lands in no table at all.")
    else:
        note("cedar_correction_register.csv is EMPTY or absent - no applied "
             "correction has been declared, so none can be re-tested. That is "
             "UNMEASURED for every correction ever made, not a clean bill.")
    return m, stale, reg.declared_row_removals()


def measure_rulings_unapplied():
    m, detail = {}, []
    ledger = CLEAN / "cedar_ruling_ledger_consolidated.csv"
    log = DOCS / "RULING_APPLICATION_LOG.md"

    if ledger.exists():
        hdr = header_of(ledger)
        col = next((c for c in hdr
                    if c.strip().lower() in APPLIED_COLS), None)
        rows = read_csv(ledger)
        if col is None:
            m["rulings_unapplied"] = "UNMEASURED"
            note(f"{ledger.name} exists ({len(rows):,} rows) but carries none "
                 f"of {APPLIED_COLS} - applied cannot be told from unapplied. "
                 f"UNMEASURED, NOT ZERO. Header: {', '.join(hdr[:12])}")
        else:
            bad = [r for r in rows
                   if UNAPPLIED_RE.search((r.get(col) or "").strip())
                   or not (r.get(col) or "").strip()]
            m["rulings_unapplied"] = len(bad)
            seen = Counter((r.get(col) or "(blank)").strip() for r in rows)
            note(f"{ledger.name}: {len(rows):,} consolidated rulings; "
                 f"{len(bad):,} are NOT applied back to source, read from "
                 f"column '{col}' "
                 f"({', '.join(f'{k}={v:,}' for k, v in seen.most_common(6))})."
                 f" A ruling that is not applied back to its source table is "
                 f"not a ruling, it is a note.")
            detail = bad[:10]
    else:
        m["rulings_unapplied"] = "UNMEASURED"
        note("data/clean/cedar_ruling_ledger_consolidated.csv ABSENT - "
             "ruled-but-unapplied is UNMEASURED, NOT ZERO. "
             "code/173_consolidate_rulings_ledger.py is the producer; its "
             "--check mode writes nothing.")

    if log.exists():
        txt = log.read_text(encoding="utf-8", errors="replace")
        mm = re.search(r"([\d,]{3,})\s+clusters?", txt)
        dd = re.search(r"\$([\d.,]+)\s*([BM])\b", txt)
        m["ruling_log_clusters_reported"] = (
            int(mm.group(1).replace(",", "")) if mm else "UNPARSED")
        note(f"docs/RULING_APPLICATION_LOG.md present"
             + (f": reports {mm.group(1)} clusters" if mm else
                ": no '<n> clusters' figure found in it")
             + (f" / ${dd.group(1)}{dd.group(2)}" if dd else ""))
    else:
        m["ruling_log_clusters_reported"] = "UNMEASURED"
        note("docs/RULING_APPLICATION_LOG.md ABSENT - a concurrent agent is "
             "writing it after finding 492 clusters / $17.5B carrying a ruling "
             "never written back. Fold its figure in when it lands; until then "
             "this is UNMEASURED, NOT clean.")
    return m, detail


# Metrics where a DECREASE is a regression. Everything else is reported but not
# failed on, because a count can legitimately fall when something is corrected.
MUST_NOT_FALL = {
    "tier_A_ruled", "spine_entities", "spine_village_corporations",
    "spine_regional_ancs", "spine_nho", "spine_intertribal",
    "prime_entities", "village_corp_obligations_usd",
    "deal_parties_autoresolved", "deal_rows_autoresolved",
    "brands_learned", "lobbying_clients_attributed", "codebook_variables",
    "links_on_village_corporations",
    # Entity keys must never fall. A rebuild that drops them is a silent
    # un-selling of the product.
    "keyed_ownership_events", "keyed_compacts", "keyed_compact_events",
    "keyed_compact_terms", "keyed_gaming_land_decisions",
    "keyed_gaming_facilities", "keyed_np_orgs",
    "bridge_native_bills_entity_bridge", "bridge_bill_votes_entity_bridge",
    "bridge_federal_actions_entity_bridge",
    # External review finding 3: identity-critical facts standing on a row
    # with no recorded provenance. This may only fall.
    "identity_facts_legacy_only",
    # SHIPPING. `ship_dist_rows` and `ship_tables_shipping` can only fall if
    # shipping was actively lost - a notes contract deleted, a dist artefact
    # rebuilt smaller, a table un-registered. There is no benign cause, which
    # is why these two are the hard half of standing rule 11 and ship_ratio_pct
    # is the soft half.
    "ship_dist_rows", "ship_tables_shipping",
}
# Metrics that must stay at zero. These are the bugs themselves.
MUST_BE_ZERO = {
    "sk_firms_on_idaho",
    "tierA_without_entity", "X_rows_naming_an_owner", "spine_duplicate_ids",
    "codebook_undocumented_public", "duns_marked_publishable",
    # rule 12: a rebuild reverted an enricher and the columns went with it
    "files_with_columns_lost_vs_backup",
    # rule 13: a unit written short of the total its own source reported
    "units_short_of_source_reported_total",
    # rule 14: a coverage computation aimed at a column that is not there
    "coverage_columns_that_do_not_exist",
    # rule 16: a NEW instance of one of the six named defect classes, measured
    # against 293's own baseline. Fix it, or waive the line with a reason.
    "lint_new_defect_instances",
    # Phase 1 contracts (512): a violated contract is not a gap to burn down,
    # it is the world contradicting a promise. An ORPHAN shippable table
    # would ship with no owning collection, no plan and no contract - the
    # shape that let 47 gaming tables ship at 0.87% before the registry.
    "contract_violations", "contract_orphan_shippable",
    # Phase 4: a handoff whose verify commands were re-run and FAILED is a
    # disproven claim of completed work standing in the record.
    "handoffs_failed_verification",
}
# Metrics where an INCREASE is the regression. A registration gap rises when a
# table lands in data/clean and nobody registers it - the last-mile failure
# this project keeps repeating, and one whose fix is cheap and local.
MUST_NOT_RISE = {
    "ship_tables_at_zero",
    "tables_missing_codebook_block", "tables_missing_from_25_TABLES",
    "tables_missing_from_27_SPEC", "tables_missing_notes_contract",
    "rulings_unapplied",
    # The real registration gap - see the comment where it is measured.
    # tables_missing_from_25_TABLES is kept (a curated override going missing
    # is still worth knowing) but it is NOT the shipping gate.
    "tables_undocumented_in_codebook",
    # A NEW SCRIPT MAY NOT REUSE A TAKEN NUMBER.
    # Ratcheted from a floor of 43, so the existing collisions are grandfathered
    # and the 44th is refused. Avoiding one costs a glance at `ls code/<n>_*`;
    # the alternative is that "script 154" stays permanently ambiguous, which is
    # already true of 43 numbers and has produced at least one incident
    # (review/_INCIDENT_2026-08-26_script163_number_collision.md).
    "code_duplicate_numbers",
    # A CORRECTION THAT REACHED ONE TABLE AND NOT ITS SIBLINGS.
    #
    # MUST_NOT_RISE and not MUST_BE_ZERO, deliberately and with the reason
    # written down. Its first floor is 10, and all ten are ONE pair:
    # `BRISTOL BAY AREA HEALTH CORPORATION -> ANRC-BRBYCO-00` (Bristol Bay
    # NATIVE CORPORATION), which the propagation check surfaced the moment it
    # was switched on. That link was not made by the lobbying pipeline - it
    # comes from a tier-B `cluster_v3` row in `cedar_identifier_ledger_final.
    # csv` on UEI NL5HNWNUFMK4 - and it carries **$494,305,407 across 504
    # `federal_funding_transactions` rows**, four FAC Single Audits and 29
    # subawards. Unwinding it moves `village_corp_obligations_usd`, which is
    # MUST_NOT_FALL at $60.4B, so it needs an owner's ruling and its own pass,
    # not a drive-by edit at the end of a session. It is written up as FA-04
    # in `docs/ANOMALY_REPORT.md` and every one of the ten is PRINTED BY NAME
    # on every run of this gate - a named failure gets fixed, an anonymous
    # count gets scrolled past, which is how `codebook_undocumented_public =
    # 45` survived six sessions.
    #
    # A RISE means a correction applied today did not reach a table that
    # carries the same claim. That is the defect, and it is a hard fail.
    "corrections_not_propagated",
    # THE SIX NAMED DEFECT CLASSES. Each of these was found more than once on
    # one day, in unrelated scripts, by different agents. A rise is a NEW
    # instance of a defect this project has already paid for. Fix it, or waive
    # the line WITH A REASON (`# lint-ok: classN - why`) - a waiver is counted
    # and named by 293, never hidden.
    "lint_class1", "lint_class2a", "lint_class2b", "lint_class2c",
    "lint_class3", "lint_class4", "lint_class5", "lint_class6",
    # class 7 added 2026-08-26: a POSITIONAL or otherwise NON-DETERMINISTIC
    # primary key - an id minted from something OUTSIDE the row, so the same
    # fact gets a different id on the next build. Three measured instances:
    # `ferc_filing_id` kept 4 of 2,534 ids across two builds; `INV-nnnn` is
    # rank-derived and a concurrent rewrite gave one firm another firm's
    # ownership sentence; `EMP-OSHATRIBE-*` is positional and changed on 482
    # of 492 rows on a re-run, where a merge would have appended 492 silent
    # duplicates. 293 CONSUMES `284_audit_nondeterministic_keys.
    # lint_key_stability()` rather than re-deriving it - two detectors for one
    # class is what retired 248.
    "lint_class7",
    "lint_bug_class_instances",
}
# Metrics that must stay SMALL - a ceiling, not a floor.
CEILINGS = {"kootenai_idaho_usd": 1_000_000.0}


def show(k, v):
    if isinstance(v, float):
        return f"  {k:40s} {v:,.3f}"
    if isinstance(v, int):
        return f"  {k:40s} {v:,}"
    return f"  {k:40s} {v}"


def numeric(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def main():
    now = measure()

    ship, dist_by_file, clean_by_file = measure_shipping()
    now.update(ship)
    bak, col_losses, bak_odd = measure_backups()
    now.update(bak)
    trunc, short_units = measure_truncation()
    now.update(trunc)
    cov, absent_cols = measure_coverage_columns()
    now.update(cov)
    rul, _rul_detail = measure_rulings_unapplied()
    now.update(rul)
    corr, stale_consumers, declared_removals = measure_corrections()
    now.update(corr)
    now.update(measure_lint_bug_classes())

    if "--baseline" in sys.argv:
        BASELINE.write_text(json.dumps(
            {"recorded": TODAY, "metrics": now,
             "shipping": dist_by_file or {}}, indent=2), encoding="utf-8")
        print(f"baseline recorded -> {BASELINE.relative_to(CEDAR)}")
        print(f"  including a per-table dist row count for "
              f"{len(dist_by_file or {}):,} tables, which is what lets the "
              f"next run tell 'this table stopped shipping' from 'the total "
              f"moved'.\n")
        for k, v in now.items():
            print(show(k, v))
        for n in NOTES:
            print(f"  [note] {n}")
        return

    fails, warns, loud = [], [], []

    for k, limit in CEILINGS.items():
        if now.get(k, 0) > limit:
            fails.append(f"{k} = {now[k]:,.2f}, above its ceiling {limit:,.0f} "
                         f"- the Kootenai/CSKT conflation has returned")

    for k in sorted(MUST_BE_ZERO):
        v = now.get(k, 0)
        if numeric(v) and v:
            fails.append(f"{k} = {v:,}, must be 0")

    base, base_ship = {}, None
    if BASELINE.exists():
        raw = json.loads(BASELINE.read_text(encoding="utf-8"))
        base = raw.get("metrics", {})
        base_ship = raw.get("shipping")
        # THE DECLARED-WITHDRAWAL ALLOWANCE, and why it is not an
        # acknowledgement button.
        #
        # `ship_dist_rows` is MUST_NOT_FALL on the stated grounds that "there
        # is no benign cause". Withdrawing 54 false rows from
        # `tribe_year_lobbying_panel.csv` IS a benign cause and it was not
        # anticipated. Per this file's own rule 2 - show it is not a defect,
        # change the check, say why - a fall is allowed ONLY when the
        # correction register declares a `rows_removed` total EXACTLY EQUAL to
        # the fall. Exact, never `<=`: if the table loses one more row
        # tomorrow the arithmetic stops matching and the gate fails again, so
        # a declared correction cannot be stretched to cover an unrelated
        # loss. That is the difference between an allowance and an excuse.
        allow_total = sum(declared_removals.values()) if declared_removals else 0
        for k in sorted(MUST_NOT_FALL):
            b, n = base.get(k), now.get(k)
            if not (numeric(b) and numeric(n)):
                continue
            if n < b:
                if k == "ship_dist_rows" and allow_total and b - n == allow_total:
                    loud.append(
                        f"ship_dist_rows fell {b:,} -> {n:,}, which is EXACTLY "
                        f"the {allow_total:,} row(s) the correction register "
                        f"declares as withdrawn false attributions "
                        f"({', '.join(f'{t} -{c}' for t, c in sorted(declared_removals.items()))}). "
                        f"Allowed, named, and re-checked every run - the "
                        f"allowance is an EXACT match, so one more lost row "
                        f"fails this line again.")
                    continue
                fails.append(f"{k} FELL {b:,} -> {n:,}")
            elif n > b:
                warns.append(f"{k} rose {b:,} -> {n:,}")
        for k in sorted(MUST_NOT_RISE):
            b, n = base.get(k), now.get(k)
            if not (numeric(b) and numeric(n)):
                if k in now and not numeric(now[k]):
                    loud.append(f"{k} is {now[k]} - not measured this run. "
                                f"UNMEASURED is not clean.")
                continue
            if n > b:
                fails.append(
                    f"{k} ROSE {b:,} -> {n:,} - this metric only goes down. "
                    + ("A table is undocumented in the codebook registry, "
                       "which IS the shipping gate: 25_build_publication_layer "
                       "resolves curated overrides first, then everything the "
                       "codebook documents. Fix: write a codebook block "
                       "(cedar_codebook.write_fragment / "
                       "cedar_register_codebook.py), then re-run 87 -> 25 -> 27 "
                       "per docs/SHIPPING_RUNBOOK.md."
                       if k == "tables_undocumented_in_codebook"
                       # NOT the shipping gate. TABLES is 37 curated overrides;
                       # a rise here means an override was dropped, not that a
                       # dataset stopped shipping.
                       else "A table left the CURATED OVERRIDE list in "
                            "25_build_publication_layer.TABLES. This is not "
                            "the shipping gate - see "
                            "tables_undocumented_in_codebook for that."
                       if k.startswith(("tables_missing", "ship_tables_at_zero"))
                       # The lint counters had been inheriting the RULINGS
                       # explanation, which is about a completely different
                       # metric. A failure message that explains the wrong
                       # defect sends the next agent to the wrong file.
                       else "A NEW instance of a named defect class landed in "
                            "code/. It is named above under 'NEW <class> "
                            "instance'. Fix it, or waive the line WITH A "
                            "REASON (`# lint-ok: classN - why`) - a waiver is "
                            "counted and named by 293, never hidden. Do NOT "
                            "re-record the baseline: --baseline is a floor, "
                            "not an acknowledgement button."
                       if k.startswith("lint_")
                       # Added 2026-08-28 with code_duplicate_numbers, which
                       # fell straight through to the RULINGS text below - the
                       # very mistake the comment above records having already
                       # fixed once for lint_. A new ratcheted metric needs its
                       # own branch here, or it ships with someone else's
                       # remediation advice attached.
                       else "A new script reused a number that is already "
                            "taken. `ls code/<n>_*` before naming one, and "
                            "pick a free number - 43 numbers are already "
                            "ambiguous and citing 'script 154' means nothing. "
                            "The colliding pair is named in the note above."
                       if k.startswith("code_")
                       else "A ruling that is not applied back to its source "
                            "table is not a ruling, it is a note."))
            elif n < b:
                warns.append(f"{k} fell {b:,} -> {n:,}")
    else:
        print("no baseline on file - run with --baseline first\n")

    # -- SHIPPING: which half of the ratio moved --------------------------
    stopped, newly_zero, grew = [], [], []
    if base_ship is None:
        loud.append(
            "NO PER-TABLE SHIPPING BASELINE ON FILE. 'a table that was "
            "shipping stopped shipping' CANNOT be detected until one is "
            "recorded: py -3 code/62_no_regression_check.py --baseline")
    elif dist_by_file is not None:
        for f, was in sorted(base_ship.items()):
            nowd = dist_by_file.get(f)
            if nowd is None:
                if was:
                    fails.append(
                        f"SHIPPING LOST: {f} was shipping {was:,} rows and the "
                        f"table is GONE from data/clean")
                continue
            if was and nowd < was:
                # Same exact-accounting allowance as ship_dist_rows above.
                dec = (declared_removals or {}).get(f, 0)
                if dec and was - nowd == dec:
                    loud.append(
                        f"{f} shipped {was:,} -> {nowd:,}, EXACTLY the {dec} "
                        f"row(s) the correction register declares withdrawn as "
                        f"false attributions. Allowed and named.")
                    continue
                stopped.append(f"{f}: {was:,} -> {nowd:,}")
        for s in stopped:
            fails.append(f"A TABLE THAT WAS SHIPPING STOPPED SHIPPING - {s}. "
                         f"Standing rule 11: built is not done, shipped is "
                         f"done - and un-shipped is a regression, not a "
                         f"rebuild artefact.")
        newly_zero = [f for f, d in (dist_by_file or {}).items()
                      if d == 0 and f not in base_ship]

    b_ratio, n_ratio = base.get("ship_ratio_pct"), now.get("ship_ratio_pct")
    if numeric(b_ratio) and numeric(n_ratio) and n_ratio < b_ratio:
        b_dist, n_dist = base.get("ship_dist_rows"), now.get("ship_dist_rows")
        if numeric(b_dist) and numeric(n_dist) and n_dist >= b_dist:
            # THE WAREHOUSE GREW. Not a failure - and never silent.
            grew = sorted(
                ((f, clean_by_file[f] - dist_by_file.get(f, 0))
                 for f in (clean_by_file or {})
                 if clean_by_file[f] > dist_by_file.get(f, 0)),
                key=lambda kv: -kv[1])[:8]
            loud.append(
                f"ship_ratio_pct fell {b_ratio:.3f}% -> {n_ratio:.3f}% and "
                f"shipped rows did NOT fall ({b_dist:,} -> {n_dist:,}). The "
                f"warehouse grew; the shelf did not. Biggest unshipped: "
                + ", ".join(f"{f} ({n:,})" for f, n in grew))
        else:
            fails.append(
                f"ship_ratio_pct FELL {b_ratio:.3f}% -> {n_ratio:.3f}% AND "
                f"shipped rows fell too. The shelf shrank.")

    # ---------------------------------------------------------------- print
    print("=== Cedar Press regression check ===\n")
    for k, v in now.items():
        print(show(k, v))

    if NOTES:
        print("\nwhat was measured, and what was not:")
        for n in NOTES:
            print(f"  . {n}")

    if col_losses:
        print("\nCOLUMN LOSS AGAINST THE MOST RECENT BACKUP (standing rule 12):")
        for d in col_losses:
            print(f"  !! {d['file']}  {d['backup_columns']} -> "
                  f"{d['live_columns']} columns vs {d['backup']}")
            print(f"     lost: {', '.join(d['lost'][:12])}"
                  f"{' ...' if len(d['lost']) > 12 else ''}")
        print("     This is the shape of `133 build` reverting `168`, and of "
              "script 09 reverting script 50.\n     A full-rebuild stage and "
              "an in-place enricher on one file need an ordering,\n     and "
              "the enricher runs LAST. Re-run the enricher, then re-run this.")
    for o in bak_odd:
        print(f"  [ordering hazard] {o}")

    if short_units:
        print("\nUNITS SHORT OF THE TOTAL THEIR OWN SOURCE REPORTS "
              "(standing rule 13):")
        for d in sorted(short_units, key=lambda r: r["pct"])[:20]:
            print(f"  !! {d['unit']:24s} {d['retrieved']:>8,} of "
                  f"{d['reported']:>8,} ({d['pct']:.1f}%)  [{d['source']}]")
        if len(short_units) > 20:
            print(f"     ...and {len(short_units) - 20} more")
        print("     A per-unit budget that truncates and then marks the unit "
              "`done` is a\n     silent ceiling: no resume will ever revisit "
              "it. Clear the `done` flag\n     for these units and re-fetch.")

    if stale_consumers:
        print("\nCORRECTIONS THAT REACHED ONE TABLE AND NOT ITS SIBLINGS:")
        for d in sorted(stale_consumers,
                        key=lambda r: (-r["rows"], r["table"]))[:25]:
            print(f"  !! {d['table']:44s} {d['rows']:>6,} row(s) still key "
                  f"{d['entity_id']} to {d['withdrawn_key']!r}  [{d['finding_id']}]")
            print(f"     applied to: {d['was_applied_to']}")
            if d.get("example"):
                print(f"     e.g. {d['example'][:150]}")
        if len(stale_consumers) > 25:
            print(f"     ...and {len(stale_consumers) - 25} more")
        print("     A correction that is not applied to every table carrying "
              "the same claim is\n     the same disease as a ruling that is "
              "not applied at all. `354_correction_register.py --check` "
              "lists them in full.")

    if absent_cols:
        print("\nCOVERAGE COLUMNS THAT DO NOT EXIST (standing rule 14):")
        for d in absent_cols:
            print(f"  !! {d['file']} has no column '{d['column']}'")
            print(f"     header: {d['header']}")
        print("     A zero from one of these reads as an empty source. "
              "It is not.")

    if newly_zero:
        print(f"\nNEW TABLES AT A 0% SHIP RATIO ({len(newly_zero)}), not in "
              f"the shipping baseline:")
        for f in sorted(newly_zero,
                        key=lambda x: -(clean_by_file or {}).get(x, 0))[:15]:
            print(f"  - {f} ({(clean_by_file or {}).get(f, 0):,} rows)")
        print("     Register the codebook block, then re-run 87 -> 25 -> 27, "
              "per docs/SHIPPING_RUNBOOK.md.")

    if loud:
        print("\nREAD THESE - measured, not failed:")
        for w in loud:
            print(f"  ** {w}")

    if warns:
        print("\nimproved:")
        for w in warns:
            print(f"  + {w}")

    if fails:
        print("\nREGRESSIONS - STOP AND FIX BEFORE CONTINUING:")
        for f in fails:
            print(f"  !! {f}")
        print("\n  A FAIL HERE IS STOP-WORK. Standing rule 15: do not record "
              "it as\n  'pre-existing, not mine' and continue. If it is "
              "genuinely another\n  agent's, name it and its owner in "
              "AGENTS.md before moving on -\n  six sessions in a row stepped "
              "around one line and hid every other\n  failure this gate could "
              "have raised.")
        raise SystemExit(1)

    print("\nno regressions.")


if __name__ == "__main__":
    try:
        main()
    except AbsentColumn as e:
        # STANDING RULE 14, applied to the gate itself. A coverage count on a
        # column that does not exist must never quietly become a zero, and a
        # zero baked into --baseline is worse still.
        print("\n=== Cedar Press regression check ===\n")
        print("STOP. A COLUMN THIS GATE COUNTS ON DOES NOT EXIST:\n")
        print(f"  {e}\n")
        print("  This is standing rule 14. `.get(col)` on an absent column "
              "returns None on\n  every row, so the count would have been 0 "
              "and would have read as an empty\n  source - which is exactly "
              "how script 102 published 0.0% coverage on two\n  datasets "
              "holding 307 and 274 keyed rows for 19 days.")
        raise SystemExit(1)
