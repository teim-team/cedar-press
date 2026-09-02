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


def _load_declared_removals():
    """{(file, column)} that a script removed ON PURPOSE, with a stated reason.

    Added 2026-09-02. `files_with_columns_lost_vs_backup` compares a live table
    to its newest `.bak_*` and cannot distinguish an intentional removal from
    an accident. Without this the CICD retirement kept the metric red
    permanently, and a permanently red metric is one nobody reads. A
    declaration must name the removing script and the reason; it excuses only
    that column on that file.
    """
    import json as _json
    # Path derived from __file__, not ROOT: this loader runs at import
    # time, before ROOT is bound further down the module.
    p = (Path(__file__).resolve().parent.parent / "docs" / "schema"
         / "declared_column_removals.json")
    if not p.exists():
        return set()
    try:
        d = _json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return set()
    out = set()
    for r in d.get("declarations", []):
        if r.get("file") and r.get("column") and r.get("removed_by") and r.get("why"):
            out.add((r["file"], r["column"]))
    return out


_DECLARED_REMOVALS = _load_declared_removals()

CEDAR = Path(__file__).resolve().parent.parent
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
DIST = CEDAR / "dist"
DOCS = CEDAR / "docs"
RAW = CEDAR / "data" / "raw"
BASELINE = CLEAN / "_regression_baseline.json"
SHIP_CACHE = CLEAN / "_regression_ship_cache.json"
SEM_BASELINE = CLEAN / "_regression_semantic_baseline.json"
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
            # External review F9. A SHIPPABLE table whose row grain, primary
            # key, join key(s) and join cardinality are not declared AND
            # validated cannot be joined safely: the named failure is a
            # buyer joining a table whose real grain is entity x UEI x year
            # on cedar_uid alone and multiplying every award amount.
            #
            # Two metrics, because there are two different defects:
            #   contract_violations              a DECLARED grain the data
            #                                    contradicts. Release-blocking
            #                                    today (MUST_BE_ZERO).
            #   contract_grain_unstated_shippable  never declared at all.
            #                                    Also a release defect, but
            #                                    207 of 210 tables are in it
            #                                    and failing every one today
            #                                    would make this gate a thing
            #                                    to step around - standing
            #                                    rule 15. RATCHETED: the count
            #                                    may only fall, so a NEW
            #                                    shippable table landing
            #                                    without a grain fails the
            #                                    gate the day it lands.
            m["contract_grain_unstated_shippable"] = int(
                _doc.get("n_shippable_grain_unstated", 0))
            m["contract_grain_stated_shippable"] = int(
                _doc.get("n_shippable_grain_stated", 0))
            _un = _doc.get("shippable_grain_unstated", [])
            if _un:
                note(f"{len(_un)} SHIPPABLE table(s) have an UNSTATED row "
                     f"grain - a buyer cannot join them safely. Ratcheted, "
                     f"not waived. First few: "
                     + ", ".join(_un[:6])
                     + f" ... full list in docs/schema/dataset_contracts.json"
                       f" -> shippable_grain_unstated")
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
        # External review round 2, MEASURED critical: a table whose grain is
        # unresolved or which carries literal duplicate rows, AND which
        # carries money columns, is one a buyer will total and get a wrong
        # answer from - and the wrong answer looks completely normal. 517
        # classifies these; this counts them so the exposure can only shrink.
        _es = CLEAN / "cedar_export_safety.csv"
        if _es.exists():
            import csv as _csv3
            with _es.open(encoding="utf-8-sig", newline="") as _fh:
                _rows = list(_csv3.DictReader(_fh))
            m["export_unsafe_money_tables"] = sum(
                1 for _r in _rows
                if _r.get("aggregation_safe") == "0" and _r.get("money_columns"))
            m["export_row_level_only"] = sum(
                1 for _r in _rows if _r.get("aggregation_safe") == "0")

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

        # SOURCE-ROW CONSERVATION (510 I13). Every harvested source row must
        # land in a NAMED bucket: emitted, duplicate, or a rejection with a
        # stated reason. `harvest_rows_unaccounted` is the unnamed
        # disappearance - defect class 2c at the harvest layer - and it is
        # MUST_BE_ZERO. `harvest_source_rows_read` may not fall, because a
        # harvester quietly ceasing to read a table looks exactly like a
        # table that got smaller.
        _cn = CLEAN / "cedar_harvest_conservation.csv"
        if _cn.exists():
            import csv as _csv3
            _in, _un2, _rej = {}, 0, 0
            with _cn.open(encoding="utf-8-sig", newline="") as _fh:
                for _r in _csv3.DictReader(_fh):
                    _in[_r["source_table"]] = int(_r["rows_in"] or 0)
                    if _r["disposition"] == "UNACCOUNTED_FOR":
                        _un2 += int(_r["rows"] or 0)
                    if _r["disposition"].startswith("rejected"):
                        _rej += int(_r["rows"] or 0)
            m["harvest_source_rows_read"] = sum(_in.values())
            m["harvest_rows_unaccounted"] = _un2
            m["harvest_rows_rejected_named"] = _rej
        else:
            note("data/clean/cedar_harvest_conservation.csv missing - run "
                 "510_assertions.py all --apply; source-row conservation NOT "
                 "measured, which is not the same as clean")

        # THE HANDLE CONTRACT (503, external review F6). cedar_uid is the
        # documented join key and a handle is a display label - but only if
        # a retired handle keeps resolving and is never reassigned. 503's
        # own verify_handles() is the authority; this reads its inputs so
        # the gate does not depend on another script being run first.
        _hh2 = SPINE / "cedar_handle_history.csv"
        if _hh2.exists():
            import csv as _csv4
            _bind, _bad, _cur = {}, 0, {}
            with _hh2.open(encoding="utf-8-sig", newline="") as _fh:
                _hrows = list(_csv4.DictReader(_fh))
            for _r in _hrows:
                _h, _u = _r["handle"].strip(), _r["cedar_uid"].strip()
                if _h in _bind and _bind[_h] != _u:
                    _bad += 1
                _bind[_h] = _u
                if _r.get("status") == "current":
                    if _u in _cur and _cur[_u] != _h:
                        _bad += 1
                    _cur[_u] = _h
            m["handle_history_bindings"] = len(_hrows)
            m["handle_history_retired"] = sum(
                1 for _r in _hrows if _r.get("status") == "retired")
            m["handles_reused_or_double_bound"] = _bad
        else:
            note("data/spine/cedar_handle_history.csv missing - run "
                 "503_identity.py mint --apply; the handle contract is NOT "
                 "measured")

        # Phase 4 handoffs (513): a FAILED verification means a claim of
        # completed work was re-executed and DISPROVEN - that is stop-work,
        # not a queue. UNVERIFIED is a queue and only noted.
        _hv = CEDAR / "review" / "handoff_verifications.csv"
        _hh = CEDAR / "review" / "agent_handoffs.csv"
        if _hh.exists():
            import csv as _csv
            with _hh.open(encoding="utf-8-sig", newline="") as _fh:
                _hands = list(_csv.DictReader(_fh))
            _last, _lastfail = {}, {}
            if _hv.exists():
                with _hv.open(encoding="utf-8-sig", newline="") as _fh:
                    for _v in _csv.DictReader(_fh):
                        _last[_v["handoff_id"]] = _v["result"]
                        _lastfail[_v["handoff_id"]] = _v.get("failures", "")

            # THIS GATE MAY NOT BE THE ONLY EVIDENCE AGAINST A HANDOFF.
            #
            # A handoff's verify command list normally includes this script.
            # So when a handoff verification fails ONLY on this gate, the
            # metric below records it, this gate then fails BECAUSE of it,
            # and re-running the verification fails again for the same
            # reason. The gate becomes unable to return to green by any
            # action - the deadlock happened on 2026-08-30, when workstream
            # A's handoff was verified during a window in which an unrelated
            # table was briefly unregistered.
            #
            # A gate that cannot be cleared is a gate people learn to step
            # around, which is standing rule 15 in its worst form. So the
            # self-reference is split out: a verification that failed on any
            # of the WORKSTREAM'S OWN commands is a disproven claim and stays
            # MUST_BE_ZERO. One that failed only on this gate is a stale
            # record - it says the gate was red at the time, which this run
            # is already measuring directly - and is counted, named and
            # ratcheted instead. It clears by re-running
            # `513_handoffs.py verify` once the gate is green.
            _SELF = "62_no_regression_check.py"

            # EXTENDED 2026-08-30 by the integrator, after the deadlock
            # recurred in a shape the first fix could not see.
            #
            # The original rule asked whether every failing command NAMED this
            # gate. Workstream D's verification failed on two commands:
            #
            #   py -3 code/62_no_regression_check.py          <- names it
            #   py -3 review/fixtures_D/fixture_semantic_diff.py  <- does not
            #
            # but the second fails only because it RUNS this gate internally -
            # it is a fixture that proves the gate fires, so it cannot pass
            # while the gate is red. Naming was the wrong test; DEPENDENCE is
            # the right one, and it is statically checkable: read the script
            # the command invokes and look for a call to this gate.
            #
            # The principle, stated so nobody softens it later: a check whose
            # own pass/fail depends on this gate cannot be evidence for
            # whether this gate should fail. Everything else in a failing
            # verification is still a disproven claim and still stop-work.
            _gate_dep_cache = {}

            def _is_gate_derived(cmd):
                if _SELF in cmd:
                    return True
                for tok in cmd.split():
                    if not tok.endswith(".py"):
                        continue
                    if tok not in _gate_dep_cache:
                        f = CEDAR / tok
                        try:
                            _gate_dep_cache[tok] = (
                                _SELF in f.read_text(encoding="utf-8",
                                                     errors="replace"))
                        except OSError:
                            _gate_dep_cache[tok] = False
                    if _gate_dep_cache[tok]:
                        return True
                return False

            def _failed_only_on_this_gate(hid):
                f = (_lastfail.get(hid) or "").strip()
                if not f:
                    return False
                parts = [x.strip() for x in f.split(";") if x.strip()]
                return bool(parts) and all(_is_gate_derived(p) for p in parts)

            _failed = [_h["handoff_id"] for _h in _hands
                       if _last.get(_h["handoff_id"], "").startswith("FAILED")]
            _self_only = [h for h in _failed if _failed_only_on_this_gate(h)]
            m["handoffs_failed_verification"] = len(_failed) - len(_self_only)
            m["handoffs_failed_only_on_this_gate"] = len(_self_only)
            for _h in _self_only:
                note(f"handoff {_h} last verified FAILED, and the only "
                     f"failing command was this gate itself. That is a stale "
                     f"record, not a disproven claim - re-run "
                     f"`py -3 code/513_handoffs.py verify {_h} --by <you>` "
                     f"now that the gate is green.")
            for _h in _failed:
                if _h in _self_only:
                    continue
                note(f"handoff {_h} last verified FAILED on: "
                     f"{_lastfail.get(_h, '(not recorded)')}")
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
        # A DELIBERATE removal is not a regression, and without a way to say so
        # this metric stays red forever and stops being read. A declaration is
        # NOT a waiver: it names the script and the reason, and excuses only
        # that column on that file. See docs/schema/declared_column_removals.json.
        if lost:
            lost = [c for c in lost if (live.name, c) not in _DECLARED_REMOVALS]
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

def measure_ledger_state_column():
    """RULE 18: a `state` column may never hold the row's own identifier.

    This is not a hypothetical. `data/spine/cedar_identifier_ledger.csv` held
    the row's own 12-character UEI in `state` on 12,127 of 19,232 rows (63%)
    for as long as the file existed, and nothing noticed - a buyer filtering
    the ledger by state got silence for most of it and never learned why.

    It survived a fix, which is why it is a GATE and not a comment.
    `71_fix_known_defects.py` defect 5 cleaned the two CLEAN ledgers in
    `data/clean/` and never touched the spine ledger they are built FROM, so
    the defect sat upstream of its own repair, invisible to anyone who checked
    the shipped table. Repaired by
    `1134_repair_ledger_state_uei_contamination.py` (11,943 states recovered
    from the owner's v6, 184 left blank, nothing guessed); guarded at the
    writers in `01_build_entity_spine.py` and `03_apply_exclusions_and_tier.py`.

    Measured on every table that carries both an `identifier` and a `state`,
    not just the three known ones - the class is what is being watched, not
    the instance.
    """
    m, hits = {}, []
    seen = 0
    for p in sorted(list(SPINE.glob("*.csv")) + list(CLEAN.glob("*.csv"))):
        hdr = header_of(p)
        if "state" not in hdr or "identifier" not in hdr:
            continue
        seen += 1
        n = 0
        try:
            with open(p, encoding="utf-8-sig", errors="replace",
                      newline="") as fh:
                for r in csv.DictReader(fh):
                    s = (r.get("state") or "").strip()
                    if s and s == (r.get("identifier") or "").strip():
                        n += 1
        except OSError:
            continue
        if n:
            hits.append((p.name, n))
            note(f"RULE 18 {p.name}: {n:,} rows hold the row's own identifier "
                 f"in `state`. Repair: py -3 code/"
                 f"1134_repair_ledger_state_uei_contamination.py apply")
    m["ledger_state_holds_own_identifier"] = sum(n for _f, n in hits)
    note(f"rule 18 state-column check: {seen} table(s) carry both "
         f"`identifier` and `state`; {len(hits)} contaminated")
    return m


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
# ===========================================================================
# TRAP 5  -  A SILENT MASS RE-KEYING THAT EVERY COUNT ABOVE CALLS GREEN
#
# Row counts staying stable is not evidence that nothing happened. Every
# metric in this file is an AGGREGATE, and an aggregate cannot see a rebuild
# that keeps 32,551 facts and 1,536 entities while changing WHICH entity each
# fact is about. That is the failure mode that matters commercially: a buyer
# joined on cedar_uid last month, the mapping moved this month, and nothing
# above says a word about it because both months have the same totals.
#
# So this compares the CONTENT of the identity-bearing fields against a
# snapshot recorded alongside the numeric baseline:
#
#   resolved facts   winner value, support_status, resolution_status,
#                    winning source, per (uid, qualifier, predicate)
#   entities         handle -> uid, class, parent, ultimate parent
#
# `sem_entities_uid_reassigned` is MUST_BE_ZERO: a handle pointing at a
# different uid than it did at the baseline is a re-keying, and there is no
# benign version of it - the handle contract in 503 exists to make it
# impossible, and this is the independent check that it did.
# The rest are CEILINGS: change is normal, MASS change is a stop-work, and
# the changed keys are PRINTED BY NAME rather than counted.
# ===========================================================================
SEM_FACTS = CLEAN / "cedar_resolved_facts.csv"
SEM_SPINE = SPINE / "cedar_entity_spine.csv"
SEM_REGISTER = SPINE / "cedar_identity_register.csv"


def semantic_snapshot():
    """The identity-bearing content, keyed so a re-keying cannot hide."""
    facts = {}
    if SEM_FACTS.exists():
        with SEM_FACTS.open(encoding="utf-8-sig", errors="replace",
                            newline="") as fh:
            for r in csv.DictReader(fh):
                k = "\t".join((r.get("cedar_uid", ""),
                               r.get("subject_qualifier", ""),
                               r.get("predicate", "")))
                facts.setdefault(k, []).append("|".join((
                    (r.get("object_value") or "")[:80],
                    r.get("support_status", ""),
                    r.get("resolution_status", ""),
                    r.get("winning_source", ""))))
    ent = {}
    if SEM_SPINE.exists():
        with SEM_SPINE.open(encoding="utf-8-sig", errors="replace",
                            newline="") as fh:
            for r in csv.DictReader(fh):
                uid = (r.get("cedar_uid") or "").strip()
                if uid:
                    ent[uid] = "|".join((
                        r.get("entity_class", ""),
                        r.get("parent_entity_id", ""),
                        r.get("ultimate_parent_entity_id", "")))
    handles = {}
    if SEM_REGISTER.exists():
        with SEM_REGISTER.open(encoding="utf-8-sig", errors="replace",
                               newline="") as fh:
            for r in csv.DictReader(fh):
                h = (r.get("handle") or "").strip()
                if h:
                    handles[h] = r.get("cedar_uid", "")
    return {"facts": {k: sorted(v) for k, v in facts.items()},
            "entities": ent, "handles": handles}


def measure_semantic_diff():
    """(metrics, [named changes]). Returns the snapshot too, so --baseline
    writes exactly what was compared."""
    snap = semantic_snapshot()
    m = {"sem_facts_tracked": len(snap["facts"]),
         "sem_entities_tracked": len(snap["entities"]),
         "sem_handles_tracked": len(snap["handles"])}
    named = []
    if not SEM_BASELINE.exists():
        note("NO SEMANTIC BASELINE ON FILE - a mass re-keying that keeps the "
             "row counts stable CANNOT be detected until one is recorded: "
             "py -3 code/62_no_regression_check.py --baseline. UNMEASURED is "
             "not clean.")
        return m, named, snap
    try:
        base = json.loads(SEM_BASELINE.read_text(encoding="utf-8"))
    except Exception as e:
        note(f"semantic baseline unreadable ({type(e).__name__}) - the "
             f"semantic diff was SKIPPED, not passed")
        return m, named, snap

    bf, nf = base.get("facts", {}), snap["facts"]
    win = sup = stat = 0
    for k, nv in nf.items():
        bv = bf.get(k)
        if bv is None:
            continue
        b_parts = [x.split("|") for x in bv]
        n_parts = [x.split("|") for x in nv]
        if sorted(p[0] for p in b_parts) != sorted(p[0] for p in n_parts):
            win += 1
            if len(named) < 40:
                named.append(("winner", k, "; ".join(p[0] for p in b_parts),
                              "; ".join(p[0] for p in n_parts)))
        if sorted(p[1] for p in b_parts) != sorted(p[1] for p in n_parts):
            sup += 1
        if sorted(p[2] for p in b_parts) != sorted(p[2] for p in n_parts):
            stat += 1
    m["sem_facts_winner_changed"] = win
    m["sem_facts_support_changed"] = sup
    m["sem_facts_status_changed"] = stat
    m["sem_facts_added"] = len(set(nf) - set(bf))
    m["sem_facts_removed"] = len(set(bf) - set(nf))

    be, ne = base.get("entities", {}), snap["entities"]
    cls = par = 0
    for uid, nv in ne.items():
        bv = be.get(uid)
        if bv is None:
            continue
        b, n = bv.split("|"), nv.split("|")
        if b[0] != n[0]:
            cls += 1
            if len(named) < 60:
                named.append(("class", uid, b[0], n[0]))
        if b[1:] != n[1:]:
            par += 1
            if len(named) < 60:
                named.append(("parent", uid, "/".join(b[1:]), "/".join(n[1:])))
    m["sem_entities_class_changed"] = cls
    m["sem_entities_parent_changed"] = par
    m["sem_entities_removed"] = len(set(be) - set(ne))

    bh, nh = base.get("handles", {}), snap["handles"]
    reassigned = 0
    for h, nu in nh.items():
        bu = bh.get(h)
        if bu is not None and bu != nu:
            reassigned += 1
            named.append(("UID REASSIGNED", h, bu, nu))
    m["sem_entities_uid_reassigned"] = reassigned
    m["sem_handles_retired"] = len(set(bh) - set(nh))
    return m, named, snap


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
    # F9: a table that HAD a declared+validated grain must not lose it.
    "contract_grain_stated_shippable",
    # F6: the handle history is append-only. A binding is retired, never
    # deleted, because a buyer's old join key must keep resolving forever.
    "handle_history_bindings",
    # 510 I13: a harvester that quietly stops reading a table looks exactly
    # like a table that got smaller. Neither is allowed to be silent.
    "harvest_source_rows_read",
    # SHIPPING. `ship_dist_rows` and `ship_tables_shipping` can only fall if
    # shipping was actively lost - a notes contract deleted, a dist artefact
    # rebuilt smaller, a table un-registered. There is no benign cause, which
    # is why these two are the hard half of standing rule 11 and ship_ratio_pct
    # is the soft half.
    "ship_dist_rows", "ship_tables_shipping",
}
# Metrics that must stay at zero. These are the bugs themselves.
# ===========================================================================
# RULE 17 - THE REGENERATE DEFECT, ENFORCED WITHOUT ANYONE REMEMBERING
# (added 2026-09-02, workstream REGEN / ADR-017)
#
# `cedar_pipeline.KNOWN_ORDERINGS` and lint `class6` already record this
# class - a full rebuild reverting an in-place enricher - but both are
# DECLARATIVE. They fire only where a human remembered to declare the pair,
# and 51 unsafe CSV writers existed on the day class6 was green.
#
# `code/845_regenerate_guard.py` does not ask. It reads every writer and
# compares what it would emit against what is on disk, and it covers the
# markdown half of the same defect: a generator that rewrites a whole `.md`
# over a paragraph a human wrote. 574 deleted exactly such a paragraph -
# written to close a reviewer finding - within hours of it being written.
#
# It covers THREE classes, and the third is why the count is trustworthy:
#   class1  a FIXED literal header, run after an enricher added a column
#   class2  a generator rewriting a whole .md over a paragraph a human wrote
#   class3  `fieldnames=list(rows[0].keys())` - looks derived, and is not: it
#           derives from the row THIS BUILD built, not from the file on disk.
#           114 sites, 10 that measurably lost a column. The other 104 build a
#           table they own outright or are read-modify-write on the file being
#           rewritten, which is the CORRECT idiom. Only the 10 are debt, and a
#           blanket rewrite of 114 would have been 104 edits for nothing.
#
# `regenerate_unsafe_writers` is MUST_NOT_RISE, not MUST_BE_ZERO: classes 1 and
# 3 are at 0 and the 4 remaining markdown entries are pre-existing, each an
# UPPER BOUND that needs `845 regen <doc>` to settle - eight were settled that
# way on 2026-09-02 and are recorded in 845's MD_PROVEN_SAFE with evidence. Zeroing it by fiat would be a
# waiver wearing a ratchet's clothes.
# `regenerate_new_unsafe_writers` IS MUST_BE_ZERO and is answered from 845's
# OWN baseline, the same arrangement as 293 - so a NEW instance fails the gate
# the moment it lands, whatever the standing total happens to be.
#
# Importing 845 parses; it never executes what it scans and opens no socket.
# ===========================================================================

def measure_regenerate_guard():
    mod = load_module(CODE / "845_regenerate_guard.py")
    if mod is None:
        # UNMEASURED is not zero.
        return {"regenerate_unsafe_writers": "UNMEASURED",
                "regenerate_new_unsafe_writers": "UNMEASURED"}
    try:
        live = mod.live_headers()
        rows, memory = mod.collect_csv(live)
        try:
            mrows = mod.scan_md()
        except RuntimeError as e:
            # The markdown half needs git history and says so rather than
            # scoring every doc clean. Report the CSV half and name the gap.
            note(f"845 markdown half UNMEASURED: {e}")
            mrows = None
        now_keys = mod._key(rows, mrows or [], memory)
    except Exception as e:
        note(f"845_regenerate_guard.py imported but scanning raised "
             f"({type(e).__name__}: {e}) - the regenerate defect is "
             f"UNMEASURED, NOT clean.")
        return {"regenerate_unsafe_writers": "UNMEASURED",
                "regenerate_new_unsafe_writers": "UNMEASURED"}
    base = set()
    if mod.BASELINE.exists():
        try:
            base = {tuple(x) for x in json.loads(
                mod.BASELINE.read_text(encoding="utf-8"))}
        except (ValueError, OSError):
            base = set()
        new = now_keys - base
    else:
        note("docs/schema/regenerate_guard_baseline.json ABSENT - a new "
             "unsafe writer cannot be told from an old one. Record it: "
             "py -3 code/845_regenerate_guard.py baseline")
        new = set()
    for s_, t_, v_ in sorted(new)[:12]:
        note(f"NEW unsafe wholesale writer: {s_}  {v_} -> {t_}")
    csv_n = len({(r[1], r[2], r[3]) for r in rows})
    mem_bad = [m for m in memory if m[5] in ("LOSES", "UNDETERMINED")]
    if mrows is None:
        note("845 regenerate guard: %d unsafe CSV writer(s). The MARKDOWN "
             "half is UNMEASURED, not clean - run "
             "`py -3 code/845_regenerate_guard.py md` by hand." % csv_n)
        return {"regenerate_unsafe_writers": "UNMEASURED",
                "regenerate_new_unsafe_writers": "UNMEASURED"}
    md_n = len(now_keys) - csv_n
    note(f"845 regenerate guard: class1 {csv_n} unsafe CSV writer(s) with a "
         f"FIXED literal header; class2 {md_n} markdown doc(s) a rebuild could "
         f"overwrite; class3 {len(mem_bad)} of {len(memory)} writer(s) whose "
         f"header comes from the row this build just built rather than from "
         f"the file on disk AND that measurably lose a column (the rest build "
         f"a table they own outright, or are read-modify-write on the file "
         f"being rewritten, which is correct). THE FIX for all three is to "
         f"derive: cols = CANONICAL + [c for c in live if c not in CANONICAL].")
    return {"regenerate_unsafe_writers": len(now_keys),
            "regenerate_new_unsafe_writers": len(new)}


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
    # rule 17: a NEW wholesale writer that would delete a column or a
    # paragraph nobody declared. Answered from 845's own baseline.
    "regenerate_new_unsafe_writers",
    # rule 18: a `state` column holding the row's own identifier. 12,127 rows
    # of the spine ledger did, upstream of the fix that cleaned the tables
    # built from it, so the shipped copy looked clean while the source was
    # not. Zero is the only acceptable value in any table carrying both
    # columns - see measure_ledger_state_column().
    "ledger_state_holds_own_identifier",
    # Phase 1 contracts (512): a violated contract is not a gap to burn down,
    # it is the world contradicting a promise. An ORPHAN shippable table
    # would ship with no owning collection, no plan and no contract - the
    # shape that let 47 gaming tables ship at 0.87% before the registry.
    "contract_violations", "contract_orphan_shippable",
    # Phase 4: a handoff whose verify commands were re-run and FAILED is a
    # disproven claim of completed work standing in the record.
    "handoffs_failed_verification",
    # NOT "handoffs_failed_only_on_this_gate" - deliberately, and this is the
    # second time the deadlock had to be pushed a level down.
    #
    # That metric counts handoff records that failed ONLY because this gate
    # was red when they ran. Such a record clears by re-running
    # `513_handoffs.py verify`, which runs this gate - so gating on it
    # recreates exactly the loop the split was written to break, one level up:
    # the ratchet fails the gate, the red gate makes re-verification fail, the
    # failure keeps the ratchet raised. Measured 2026-08-30: it did.
    #
    # It is therefore NAMED AND COUNTED in the notes, where it is fully
    # actionable, and never gates. The failure that actually matters - a claim
    # re-executed and DISPROVEN on the workstream's own commands - stays
    # MUST_BE_ZERO above and is unaffected.
    # 510 I13: an unnamed disappearance. A source row that left the harvest
    # with no disposition is defect class 2c at the layer where it does the
    # most damage - nobody downstream can even tell it arrived.
    "harvest_rows_unaccounted",
    # F6: a handle bound to two uids, or a uid with two current handles.
    # There is no benign version: every downstream join is wrong and nothing
    # later can detect it.
    "handles_reused_or_double_bound",
    # TRAP 5: a handle that points at a different uid than it did at the
    # baseline. This is the silent mass re-keying the aggregate counts above
    # cannot see, and it is why the semantic snapshot exists.
    "sem_entities_uid_reassigned",
}
# Metrics where an INCREASE is the regression. A registration gap rises when a
# table lands in data/clean and nobody registers it - the last-mile failure
# this project keeps repeating, and one whose fix is cheap and local.
MUST_NOT_RISE = {
    # rule 17: the standing total. The CSV half is 0; the markdown entries are
    # upper bounds awaiting `845 regen <doc>`. It may fall, never rise.
    "regenerate_unsafe_writers",
    # External review finding F3: identity-critical facts standing on a row
    # with no recorded provenance. A RISE is new unsupported exposure and is
    # the regression; a FALL is the pay-down F3 asked for.
    #
    # INSTALLED BACKWARDS on 2026-08-30 by the integrator - it sat in
    # MUST_NOT_FALL, so the gate failed the FIRST TIME anything improved the
    # number (workstream F's IRS harvest, 4,100 -> 4,089). Found independently
    # by workstreams E and F within the hour, each of whom proved it was not
    # their work: E by reverting every file of its own task and reproducing
    # the failure, F by checking sem_facts_removed = 0 on the same run. Two
    # agents refusing to step around a red gate is the process working;
    # the integrator writing a ratchet without a fixture that proves its
    # direction is how it was needed.
    "identity_facts_legacy_only",
    # Money tables a buyer must not aggregate. May only fall.
    "export_unsafe_money_tables",
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
    # class 8 added 2026-08-29, and it is debt **D1** from
    # docs/RELEASE_REPLAY_LOG.md rather than a new idea: the absolute project
    # root written into the source as a literal. 298 of 414 scripts carried it;
    # the sweep took it to 0 (1 waived, in 516, which needs the string to
    # rewrite it in a replay worktree). This is the only lint class with a
    # measured instance of DATA LOSS: a replay worktree ran a script A1 had not
    # rewritten, it addressed the LIVE tree, and four live files were written -
    # RELEASE_REPLAY_LOG.md II.10.G3. A rise here means somebody has re-armed
    # that gun. Fix is one line: Path(__file__).resolve().parent.parent.
    "lint_class8",
    "lint_bug_class_instances",
    # F9: a SHIPPABLE table whose row grain, primary key and join cardinality
    # are not declared and validated. 207 of 210 today. Ratcheted rather than
    # zeroed, with the reason written where it is measured - a gate that
    # fails on every table on day one is a gate everyone learns to step
    # around, and standing rule 15 says that is worse than no gate.
    "contract_grain_unstated_shippable",
    # A handoff verification that failed ONLY on this gate. Stale, not
    # disproven - see the reasoning where it is measured. It may only fall,
    # and it falls by re-running the verification while the gate is green.
}
# Metrics that must stay SMALL - a ceiling, not a floor.
#
# THE SEMANTIC CEILINGS (trap 5). These are not defects at 1 and are
# stop-work at 500: facts do legitimately change winner when a source is
# re-harvested, and entities do get reclassified. What no legitimate change
# looks like is HUNDREDS at once while every count above stays green. When
# one of these fires, look at the names printed under "SEMANTIC CHANGES"
# before touching --baseline: re-recording the baseline is how a mass
# re-keying becomes the new normal.
CEILINGS = {"kootenai_idaho_usd": 1_000_000.0,
            "sem_facts_winner_changed": 500.0,
            "sem_facts_status_changed": 500.0,
            "sem_facts_removed": 500.0,
            "sem_entities_class_changed": 50.0,
            "sem_entities_parent_changed": 50.0,
            "sem_entities_removed": 10.0}


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
    now.update(measure_ledger_state_column())
    now.update(measure_lint_bug_classes())
    now.update(measure_regenerate_guard())
    sem, sem_named, sem_snap = measure_semantic_diff()
    now.update(sem)

    if "--baseline" in sys.argv:
        BASELINE.write_text(json.dumps(
            {"recorded": TODAY, "metrics": now,
             "shipping": dist_by_file or {}}, indent=2), encoding="utf-8")
        SEM_BASELINE.write_text(json.dumps(sem_snap), encoding="utf-8")
        print(f"baseline recorded -> {BASELINE.relative_to(CEDAR)}")
        print(f"  and a SEMANTIC snapshot -> "
              f"{SEM_BASELINE.relative_to(CEDAR)}: "
              f"{len(sem_snap['facts']):,} resolved facts, "
              f"{len(sem_snap['entities']):,} entities and "
              f"{len(sem_snap['handles']):,} handle bindings, recorded by "
              f"CONTENT. This is what lets the next run tell 'the totals held "
              f"and everything got re-keyed' from 'nothing happened'.")
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

    # A FAILURE MESSAGE THAT EXPLAINS THE WRONG DEFECT SENDS THE NEXT AGENT
    # TO THE WRONG FILE. This loop used to append the Kootenai/CSKT sentence
    # to every ceiling, which was fine while there was one ceiling and became
    # actively misleading the moment the semantic ceilings were added - the
    # same mistake recorded above for the lint_ and code_ metrics.
    CEILING_WHY = {
        "kootenai_idaho_usd": "the Kootenai/CSKT conflation has returned",
        "sem_facts_winner_changed":
            "facts changed WINNER in bulk while the row counts stayed green. "
            "The changed keys are named under SEMANTIC CHANGES above. This is "
            "a resolver or harvest change, and it is only safe if you can say "
            "which one",
        "sem_facts_status_changed":
            "resolution_status changed in bulk - facts moved between "
            "RESOLVED, REFUTED and UNRESOLVED_TIE without the counts moving",
        "sem_facts_removed":
            "facts present at the baseline are GONE. A fact leaving the "
            "resolved table is a fact a buyer was joining to",
        "sem_entities_class_changed":
            "entities were RECLASSIFIED in bulk. Class drives the handle "
            "prefix, the gov-class guards and eligibility",
        "sem_entities_parent_changed":
            "parentage moved in bulk - this re-keys ownership and every "
            "roll-up built on it",
        "sem_entities_removed":
            "entities present at the baseline are gone from the spine",
    }
    for k, limit in CEILINGS.items():
        if now.get(k, 0) > limit:
            fails.append(f"{k} = {now[k]:,.2f}, above its ceiling {limit:,.0f}"
                         f" - {CEILING_WHY.get(k, 'no reason recorded for '
                                                  'this ceiling')}")

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
        # THE ALLOWANCE WORKED EXACTLY ONCE, and a correctness workstream
        # proved it on 2026-08-30 rather than re-baselining around it.
        #
        # It summed EVERY removal the register has ever declared. The baseline
        # has already absorbed the older ones, so the sum drifts permanently
        # above any single fall: 1,804 declared against a legitimate fall of
        # 1,749, unmatchable by any correct action. An allowance that can only
        # fire once is worse than none - the second person to need it
        # re-baselines instead, which is the habit this whole gate exists to
        # break.
        #
        # The per-table form twenty lines below was written correctly all
        # along (`declared_removals.get(f, 0)`), so the aggregate is now
        # COMPOSED from it: count a table's declared removal only when that
        # table's shipped rows actually fell by exactly that amount THIS run.
        # Self-limiting, consumable, and it cannot be stretched to cover an
        # unrelated loss - which was the original intent, and is preserved.
        allow_total = 0
        if declared_removals and base_ship:
            for _f, _dec in declared_removals.items():
                _was = base_ship.get(_f)
                if _was is None:
                    continue
                # ship_dist_rows is SUM(min(dist_rows, clean_rows)), so a
                # regrain that shrinks the CLEAN file lowers the metric while
                # dist still holds the old count until the next publish. The
                # first version of this compared dist-to-dist and therefore
                # never fired for exactly the case it was written for.
                # Compare against the same effective figure the metric uses.
                _d = dist_by_file.get(_f)
                _c = clean_by_file.get(_f)
                if _d is None and _c is None:
                    continue
                _now = min(x for x in (_d, _c) if x is not None)
                if _was - _now == _dec:
                    allow_total += _dec
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
                    # The message used to say "GONE from data/clean" while the
                    # check reads the DIST manifest. On 2026-09-02
                    # advocacy_passthrough_2026-08-07.csv was reported gone and
                    # was sitting in data/clean with all 1,620 rows — it had
                    # only dropped out of the shipping set. A failure that
                    # names the wrong location sends the reader to the wrong
                    # place; say which surface actually lost it.
                    # CEDAR, not ROOT — this module's root constant is CEDAR
                    # (line 161). I wrote ROOT out of habit from other scripts
                    # and crashed the whole gate at the one line that only runs
                    # when a table stops shipping, so it sat latent until a
                    # table did. The corroboration workstream found it, and
                    # noted something worse: the SHELL REPORTED EXIT 0 WHILE THE
                    # TRACEBACK SAT IN THE OUTPUT, so a crash reads as a pass to
                    # anyone checking the return code. That is rule 9 — an
                    # absence of evidence printing as evidence of absence.
                    _live = (CEDAR / "data" / "clean" / f).exists()
                    fails.append(
                        f"SHIPPING LOST: {f} was shipping {was:,} rows and is "
                        f"no longer in the dist manifest"
                        + (" (the table IS still in data/clean — this is a "
                           "shipping-set regression, not data loss; usually a "
                           "missing codebook block, see "
                           "tables_undocumented_in_codebook)" if _live
                           else " AND the table is absent from data/clean too"))
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
        elif allow_total and b_dist - n_dist == allow_total:
            # The shelf shrank by EXACTLY the rows the register declares
            # withdrawn, which ship_dist_rows above has already allowed and
            # named. Failing the ratio for the same fall would make the
            # allowance unusable - one metric grants it, the next revokes it.
            # The condition is deliberately the same exact match, not `<=`.
            loud.append(
                f"ship_ratio_pct fell {b_ratio:.3f}% -> {n_ratio:.3f}%, "
                f"driven by the SAME {allow_total:,} declared-withdrawn row(s) "
                f"already allowed on ship_dist_rows above. Allowed for the "
                f"same reason and re-checked every run.")
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

    if sem_named:
        print(f"\nSEMANTIC CHANGES since the baseline ({len(sem_named)} named "
              f"of {sum(now.get(k, 0) for k in ('sem_facts_winner_changed', 'sem_entities_class_changed', 'sem_entities_parent_changed', 'sem_entities_uid_reassigned')):,} "
              f"total) - the aggregate counts above cannot see these:")
        for kind, key, was, isnow in sem_named[:40]:
            print(f"  {kind:>14}  {key}")
            print(f"                  was: {str(was)[:110]}")
            print(f"                  now: {str(isnow)[:110]}")
        if len(sem_named) > 40:
            print(f"     ...and {len(sem_named) - 40} more")
        print("     A count is not actionable; a key is a task. If this list "
              "is long and every\n     number above is green, that is the "
              "silent mass re-keying this check exists\n     for - do NOT "
              "re-record the baseline until you know why.")

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
