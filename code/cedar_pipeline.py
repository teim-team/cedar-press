#!/usr/bin/env python3
"""
Cedar Press - what each script READS, what it WRITES, and what must never run.

THREE FAILURES THIS FILE ENCODES
--------------------------------
**1. A full rebuild silently reverts an in-place enricher.** Twice on
2026-08-26. `133 build` rebuilt `ferc_docket_filings.csv` four minutes after
`168_link_adjudication_hubs.py` had written 931 entity links and nine columns
into it - and printed a LARGER row count, which read as progress. `09` has done
the same to `50`. Nothing warned, because nothing anywhere declared that one
script rebuilds a file another script enriches.

**2. Four scripts must never be run at all**, and that fact lived in prose. A
comment does not stop a command. `41_build_codebooks.py` writes
`codebook_master.csv` in `"w"` mode from a hardcoded 19-group dict and would
delete 21 of the 43 blocks the master now holds; its name does not say so.
`09_import_rulings.py` destroyed 1,327 ledger rows and 451 village-corporation
links on 2026-08-08. `01_build_entity_spine.py` drops every appended entity.
`88_build_deals_taxonomy.py` rebuilds the deals taxonomy from a glob that never
saw the root ledgers.

**3. A number prefix has not implied step order since 2026-08-07** and there
are 38+ collisions. Ordering has to be DECLARED, not inferred from a filename.

    THE ORDERING RULE, IN ONE LINE:
    WHERE A FULL-REBUILD STAGE AND AN IN-PLACE ENRICHER TOUCH ONE FILE,
    THE ENRICHER RUNS LAST - AND SOMETHING MUST CHECK THAT ITS COLUMNS
    SURVIVED.

A `.bak_<date>_pre_<script>` file sitting beside an output is the signal that
an enricher has touched it. `62_no_regression_check.py` already counts
`files_with_an_inplace_enricher_backup` (74 as of 2026-08-26) and
`files_with_columns_lost_vs_backup` (0). This module turns that signal into a
declared dependency the update path can act on BEFORE the damage.

Claimed 2026-08-26 with script numbers 284-292.
"""

import ast
import re
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"


class ForbiddenScript(Exception):
    """Raised by `guard()`. Not catchable-and-ignorable by intent: the whole
    point is that the process stops."""


# ---------------------------------------------------------------------------
# THE HARD GUARDS. These are not comments.
# ---------------------------------------------------------------------------

NEVER_RUN = {
    "41_build_codebooks.py":
        "Writes codebook_master.csv in 'w' mode from a hardcoded 19-group "
        "DATASETS dict. Running it today DELETES 21 OF THE 43 dataset "
        "blocks, including every block registered on 2026-08-26. The single "
        "most destructive command in the repo, and its name does not say so. "
        "Use cedar_codebook.write_fragment() or cedar_register_codebook.py.",
}

#: SCRIPTS THAT USED TO BE IN `NEVER_RUN` AND ARE NOT ANY MORE.
#:
#: They came off the list on 2026-09-01 (workstream C8) because the reason
#: they were on it stopped being true - not because anyone decided the risk
#: was acceptable. All three destroyed for one reason: they opened their
#: output in `"w"` mode and wrote only what they had computed, so every row
#: and column that reached the table from anywhere else was gone. All three
#: now write through `merge_table` below, which cannot drop a row and raises
#: rather than drop a column.
#:
#: THE ORDER MATTERS AND IT IS RECORDED HERE BECAUSE IT IS THE WHOLE POINT.
#: `518_dataset_readiness.py` reads `NEVER_RUN` and reports C8 BLOCKED for any
#: collection a listed script rebuilds - correctly. That gate could have been
#: turned green at any point in the last month by deleting three dict entries,
#: and doing so would have made `py -3 code/build.py run _entity_layer
#: --execute` genuinely delete 868 of 1,555 entities. HUB refused it on
#: 2026-09-01 and wrote down why. The guard came off only after the merge
#: existed AND `812_c8_rebuild_proof.py` proved, by dry run against the live
#: tables, that each rebuild reproduces the census with zero rows and zero
#: columns lost.
RETIRED_FROM_NEVER_RUN = {
    "01_build_entity_spine.py": {
        "was": "A full rebuild DROPPED EVERY APPENDED ENTITY - it built from "
               "canonical_tribe_table.csv alone (687 rows, 12 columns) over a "
               "live hub of 1,555 rows and 44, dropping 868 entities and 32 "
               "columns including cedar_uid.",
        "fixed": "Writes through merge_table keyed on tribe_id (unique on all "
                 "1,555 live rows). Fills blank cells only and overwrites "
                 "nothing - every column it computes is also written by a "
                 "later enricher - so a disagreement is reported to "
                 "review/spine_merge_drift_<date>.csv, not applied.",
        "proof": "812_c8_rebuild_proof.py, 2026-09-01: 1,555 -> 1,555 rows, "
                 "44 -> 44 columns, 0 lost, 512 drift cells held back "
                 "(510 of them an alias separator).",
        "retired": "2026-09-01",
    },
    "09_import_rulings.py": {
        "was": "READ cedar_identifier_ledger_tiered.csv (19,232 rows) and "
               "WROTE cedar_identifier_ledger_final.csv (20,577). Those are "
               "not the same table: _final is _tiered plus 1,345 rows later "
               "scripts appended, 18 of them tier-A owner adjudications - the "
               "one class of fact that cannot be re-derived. A hardcoded "
               "17-column header dropped 5 more columns on top.",
        "fixed": "The base is now LIVE _final, unioned with any _tiered row "
                 "not already in it, and the column set is read off the file "
                 "instead of typed. The write refuses if a row or a column "
                 "would be lost, and any tier-A adjudication that changes "
                 "tier is named.",
        "proof": "812_c8_rebuild_proof.py, 2026-09-01: 20,577 -> 20,577 rows, "
                 "22 -> 22 columns, 0 lost, 269 tier-A adjudications carried "
                 "in and 267 out (the 2 are a genuine ruling-vs-enricher "
                 "disagreement, named in the log, not a loss).",
        "retired": "2026-09-01",
    },
    "88_build_deals_taxonomy.py": {
        "was": "Rebuilt deals_classified.csv in 'w' mode with a header taken "
               "from list(out[0].keys()) - the FIRST row's keys. It dropped "
               "nine columns: seven native_party_* written by 126, cedar_uid "
               "written by 505, and Event_Quarter, which is absent from the "
               "first input file and present in the additions files.",
        "fixed": "merge_table keyed on Deal_ID; the header is the union of "
                 "every row's keys; only the twelve taxonomy columns this "
                 "script authors are refreshed.",
        "proof": "812_c8_rebuild_proof.py, 2026-09-01: 935 -> 935 rows, "
                 "52 -> 52 columns, 0 lost, 0 drift.",
        "retired": "2026-09-01",
    },
}

#: The one escape hatch, and it is deliberately awkward. A human who has read
#: the reason above and still means it passes this exact string.
OVERRIDE_TOKEN = "I-HAVE-READ-THE-REASON-AND-ACCEPT-THE-LOSS"


def guard(script_name, override=None):
    """Refuse to run a forbidden script. Call this FIRST in any runner.

    Raises `ForbiddenScript` unless `override` is exactly OVERRIDE_TOKEN.
    A runner that catches this and continues has reimplemented the comment
    that did not work.
    """
    name = Path(str(script_name)).name
    if name not in NEVER_RUN:
        return True
    if override == OVERRIDE_TOKEN:
        return True
    raise ForbiddenScript(
        f"\n  REFUSED: {name}\n"
        f"  {NEVER_RUN[name]}\n"
        f"  If you have read that and still mean it, pass "
        f"override={OVERRIDE_TOKEN!r}.")


# ---------------------------------------------------------------------------
# DECLARED I/O, read out of the scripts themselves
# ---------------------------------------------------------------------------

#: How a path literal is being used, inferred from the call around it.
#: Every project here grows its own write helper - `write_csv`, `write_atomic`,
#: `wr`, `emit`, `save`. Naming them one at a time is how the FERC pair stayed
#: invisible, so match the SHAPE (`write*(`, `save*(`, `dump*(`) as well as
#: the stdlib calls.
_WRITE_HINTS = re.compile(
    r"\b(to_csv|write\w*\(|save\w*\(|emit\w*\(|dump\w*\(|DictWriter|writer\("
    r"|open\([^)]*['\"][wax]|backup\(|replace\(|rename\(|copy2?\()", re.I)

_READ_HINTS = re.compile(
    r"\b(read\w*\(|rd\(|load\w*\(|DictReader|reader\(|glob\(|exists\("
    r"|open\([^)]*['\"]r|fieldnames_of\(|header_of\()", re.I)

_CSV_LIT = re.compile(r"[A-Za-z0-9_./\\-]+\.(csv|json|db|xlsx|md|parquet)$")


def _literals(tree):
    """Every string constant in the module, with its line number."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield node.lineno, node.value
        elif isinstance(node, ast.JoinedStr):
            # f-string: keep the literal fragments so 'foo_{y}.csv' still
            # registers as a csv write, marked as templated.
            parts = [v.value for v in node.values
                     if isinstance(v, ast.Constant)
                     and isinstance(v.value, str)]
            if parts:
                yield node.lineno, "{}".join(parts)


def declared_io(path):
    """(reads, writes, unknown) file basenames a script names.

    Heuristic and honest about it: a literal on a line whose text carries a
    write verb is a write, one that does not is a read, and a literal built
    by an f-string is reported under `templated` rather than guessed at.
    Anything this cannot classify goes in `unknown` and is NOT silently
    dropped - a silent counter is the bug this project keeps finding.
    """
    p = Path(path)
    try:
        src = p.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(src)
    except (SyntaxError, OSError) as e:
        # Same key set as the success path. A partial dict on the error path
        # is how a caller gets a KeyError instead of an error message.
        return {"reads": [], "writes": [], "read_modify_write": [],
                "templated": [], "unknown": [],
                "error": f"{type(e).__name__}: {e}"}
    lines = src.splitlines()
    reads, writes, templated, unknown = set(), set(), set(), set()

    # A path literal is usually BOUND TO A NAME and used far away:
    #     FILINGS = CLEAN / "ferc_docket_filings.csv"
    #     ...300 lines later...
    #     write_atomic(FILINGS, rows)
    # A window around the literal sees only the assignment, so an earlier
    # version of this function classified BOTH `133_build_ferc_advocacy.py`
    # and `168_link_adjudication_hubs.py` as `unknown` for
    # `ferc_docket_filings.csv` - and therefore did NOT report the single
    # most expensive ordering collision in the repo. Follow the binding.
    bound = {}          # variable name -> basename
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        t = node.targets[0]
        if not isinstance(t, ast.Name):
            continue
        for _, val in _literals(node.value):
            b = val.strip().replace("\\", "/").rsplit("/", 1)[-1]
            if _CSV_LIT.search(b) and len(b) <= 120:
                bound[t.id] = b

    def _classify_text(text, base):
        if _WRITE_HINTS.search(text):
            writes.add(base)
            return True
        if _READ_HINTS.search(text):
            reads.add(base)
            return True
        return False

    for name, base in bound.items():
        uses = "\n".join(ln for ln in lines
                         if re.search(r"\b" + re.escape(name) + r"\b", ln))
        got_w = bool(_WRITE_HINTS.search(uses))
        got_r = bool(_READ_HINTS.search(uses))
        if got_w:
            writes.add(base)
        if got_r:
            reads.add(base)
        if not (got_w or got_r):
            unknown.add(base)

    for lineno, val in _literals(tree):
        v = val.strip().replace("\\", "/")
        base = v.rsplit("/", 1)[-1]
        if not _CSV_LIT.search(base) or len(base) > 120:
            continue
        if base in writes or base in reads:
            continue
        window = "\n".join(lines[max(0, lineno - 3):lineno + 3])
        if "{}" in base:
            templated.add(base)
        elif not _classify_text(window, base):
            unknown.add(base)
    unknown -= (reads | writes)
    # A basename appearing as both is a read-modify-write: an ENRICHER.
    both = reads & writes
    return {"reads": sorted(reads), "writes": sorted(writes),
            "read_modify_write": sorted(both),
            "templated": sorted(templated), "unknown": sorted(unknown),
            "error": None}


# ---------------------------------------------------------------------------
# REBUILD vs ENRICHER
# ---------------------------------------------------------------------------

#: A script that opens an output in 'w' mode, or writes the whole table from a
#: raw directory, is a REBUILD. One that reads the table it writes is an
#: ENRICHER. The distinction is the whole ordering problem.
_REBUILD_SIGNS = re.compile(
    r"open\([^)]*,\s*['\"]w['\"]|mode=['\"]w['\"]|"
    r"\.to_csv\([^)]*mode=['\"]w['\"]|"
    r"glob\(['\"][^'\"]*raw|data/raw|rebuild|from scratch", re.I)

_ENRICHER_SIGNS = re.compile(
    r"in.?place|enrich|backfill|link_|apply_.*_in_place|additive|"
    r"\.bak_.*pre|merge on|honours? (an? )?existing", re.I)


def classify(path):
    """'rebuild' | 'enricher' | 'both' | 'unknown', with the evidence.

    'both' is the dangerous one and is reported as such rather than resolved:
    `133_build_ferc_advocacy.py` fetches AND rebuilds AND has a build
    subcommand, and calling it either name alone is what made the collision
    invisible.
    """
    p = Path(path)
    try:
        src = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "unknown", []
    io = declared_io(p)
    ev = []
    rebuild = bool(_REBUILD_SIGNS.search(src))
    enrich = bool(io["read_modify_write"]) or bool(_ENRICHER_SIGNS.search(src))
    if rebuild:
        ev.append("writes in 'w' mode or builds from data/raw")
    if io["read_modify_write"]:
        ev.append("read-modify-writes: " + ", ".join(io["read_modify_write"]))
    elif enrich:
        ev.append("names itself an in-place enricher")
    if rebuild and enrich:
        return "both", ev
    if rebuild:
        return "rebuild", ev
    if enrich:
        return "enricher", ev
    return "unknown", ev


#: Ordering pairs that were paid for in lost work. `after` must run AFTER
#: `before` whenever `before` runs, or `before`'s columns are gone.
KNOWN_ORDERINGS = [
    # --- subcontracting, added 2026-09-02 by workstream SUBAWARD-FUNDING ----
    # `subawards.csv` has a PRIMARY KEY for the first time -
    # (source_dataset, subaward_source_record_id) - and both halves are
    # written by enrichers that run AFTER the promotion, not by it. A
    # promotion that stops before them leaves the new rows keyless, which
    # `910 verify` and `512`'s primary-key validation both fail on. Registered
    # here so `build.py`, `62`'s enricher check and `293` class6 all know the
    # order instead of each rediscovering it.
    {"rebuild": "121_pull_subawards_api.py",
     "enricher": "910_subaward_report_id_backfill.py",
     "file": "subawards.csv",
     "cost": "a promotion that stops here leaves the appended rows with a "
             "BLANK subaward_source_record_id, and blank collides with blank "
             "- the table loses the only primary key it has ever had",
     "enricher_columns": ["subaward_sam_report_id", "subaward_source_record_id",
                          "subaward_source_record_id_basis",
                          "subaward_sam_report_id_basis"]},
    {"rebuild": "121_pull_subawards_api.py",
     "enricher": "911_subaward_sub_leg_cedar_uid.py",
     "file": "subawards.csv",
     "cost": "the SUBAWARDEE leg loses its Cedar id on every appended row - "
             "56% of this table's Native attachment lives on that leg and "
             "nothing else in the file carries it",
     "enricher_columns": ["prime_cedar_uid", "sub_cedar_uid"]},
    {"rebuild": "121_pull_subawards_api.py",
     "enricher": "871_promote_geo_keys_contracts.py",
     "file": "subawards.csv",
     "cost": "the ten geo_* columns are blank on every appended row. "
             "Registered by workstream SUBAWARD-FUNDING on the geography "
             "workstream's behalf: without it 121's schema guard classes all "
             "ten as unfillable and refuses to run at all",
     "enricher_columns": ["geo_prime_award_recipient_county_fips",
                          "geo_prime_award_pop_county_fips", "geo_key_tier"]},
    {"rebuild": "121_pull_subawards_api.py",
     "enricher": "81_build_passthrough_dataset.py",
     "file": "native_passthrough.csv",
     "cost": "native_passthrough.csv is a 1:1 projection of the "
             "both_sides_native slice of subawards.csv and inherits its key; "
             "leaving it un-rebuilt after a promotion makes the two files "
             "describe different universes, which is the shape of the FERC "
             "102,615-filings-from-307-dockets-described-by-183 defect",
     "enricher_columns": ["source_dataset", "subaward_source_record_id",
                          "duplicate_status", "subaward_exceeds_prime_flag"]},
    # -----------------------------------------------------------------------
    {"rebuild": "133_build_ferc_advocacy.py",
     "enricher": "168_link_adjudication_hubs.py",
     "file": "ferc_docket_filings.csv",
     "cost": "931 entity links and 9 columns discarded on 2026-08-26; the "
             "rebuild printed a LARGER row count and read as progress",
     "enricher_columns": ["filer_entity_id", "filer_entity_link_tier"]},
    {"rebuild": "133_build_ferc_advocacy.py",
     "enricher": "175_restore_ferc_docket_table_after_rebuild_revert.py",
     "file": "ferc_tribal_dockets.csv",
     "cost": "a PARTIAL restore left 102,615 filings from 307 dockets "
             "described by a docket table listing 183; neither file looked "
             "wrong on its own",
     "enricher_columns": ["documents_retrieved",
                          "total_hits_reported_by_source"]},
    {"rebuild": "09_import_rulings.py",
     "enricher": "50_fix_kootenai_conflation.py",
     "file": "cedar_identifier_ledger_final.csv",
     "cost": "09 reverted 50's patches by rebuilding _final from the stale "
             "_tiered. Fixed 2026-09-01 (C8): 09 now re-tiers LIVE _final in "
             "place, so it no longer reverts 50 - but 50 still runs after it",
     "enricher_columns": []},
    {"rebuild": "01_build_entity_spine.py",
     "enricher": "61_add_nho_intertribal_to_spine.py",
     "file": "cedar_entity_spine.csv",
     "cost": "a rebuild drops every entity appended by 52, 61, 73 and 75",
     "enricher_columns": []},
    # Declared 2026-08-28 when the superseded v1 chain (01/02/03) was archived
    # to graveyard/2026-08-28_lobbying_v1_chain. Retiring the duplicate writer
    # left 05 as the sole rebuild of these two tables, which 65 enriches in
    # place - an ordering that had been invisible while two rebuilders were
    # fighting over the same output and masking it.
    {"rebuild": "05_match_filings_v2.py",
     "enricher": "65_lobbying_organization_type_guard.py",
     "file": "native_entity_lobbying_disclosures.csv",
     "cost": "not yet paid - declared on retirement of the v1 chain, before a "
             "rebuild could revert the guard",
     "enricher_columns": []},
    {"rebuild": "05_match_filings_v2.py",
     "enricher": "65_lobbying_organization_type_guard.py",
     "file": "tribe_year_lobbying_panel.csv",
     "cost": "not yet paid - see the sibling entry above. 351 rebuilt this "
             "panel in place on 2026-08-28 (5,051 -> 4,997 rows); a straight "
             "05 rebuild would revert that correction",
     "enricher_columns": []},
    {"rebuild": "01_build_entity_spine.py",
     "enricher": "503_identity.py",
     "file": "cedar_entity_spine.csv",
     "cost": "not yet paid - a spine rebuild drops cedar_uid, which every "
             "dataset now materialises. 01 append-merges since 2026-09-01, so a "
             "rerun no longer drops appended entities; even so, "
             "re-run 504 then 505",
     "enricher_columns": ["cedar_uid"]},
    {"rebuild": "114_pull_prime_archive.py",
     "enricher": "430_restore_prime_transaction_key.py",
     "file": "prime_contracts_archive_backfill.csv",
     "cost": "NONE, and writing that down is the point: 114's `map_row` and "
             "`PRIME_FIELDS` now emit `contract_transaction_unique_key` "
             "themselves, so a re-pull WRITES the column rather than "
             "dropping it. 430 is a ONE-TIME backfill for the 631,507 rows "
             "pulled before the mapper was fixed - the 60,919 apparent "
             "literal duplicates that were distinct FPDS transactions all "
             "along - and is a no-op on a fresh pull",
     "enricher_columns": ["contract_transaction_unique_key"]},
    # THE 2026-08-29 CORRECTNESS PASS. Three enrichers whose columns a rebuild
    # of prime_contracts.csv silently removes - and each of them is a column a
    # buyer's correctness depends on, not a convenience.
    {"rebuild": "40_build_prime_contracts.py",
     "enricher": "429_apply_asof_ownership_status.py",
     "file": "prime_contracts.csv",
     "cost": "not yet paid - declared at creation. A rebuild drops "
             "`owner_attribution_status`, and the file then presents Cedar's "
             "CURRENT owner on twenty-six years of dated transactions with "
             "nothing saying whether the temporal layer confirms it. 81.4% of "
             "$244.766B is not confirmed and $2.074B is actively "
             "CONTRADICTED, so the missing column is the difference between "
             "'unknown, and it says so' and 'definite, and it is wrong'",
     "enricher_columns": ["owner_attribution_status",
                          "owner_as_of_transaction_cedar_uid"]},
    {"rebuild": "40_build_prime_contracts.py",
     "enricher": "430_restore_prime_transaction_key.py",
     "file": "prime_contracts.csv",
     "cost": "not yet paid - declared at creation. A rebuild drops "
             "`contract_transaction_unique_key` and 80,778 distinct FPDS "
             "transactions become byte-identical rows again. The danger is "
             "not the duplication, it is that the next reader believes the "
             "grain audit and DELETES them - they carry real dollars, and "
             "97% of them are $0 administrative modifications whose loss "
             "would silently change every contract-count in the dataset",
     "enricher_columns": ["contract_transaction_unique_key"]},
    {"rebuild": "40_build_prime_contracts.py",
     "enricher": "428_rebuild_prime_entity_year.py",
     "file": "prime_contracts_entity_year.csv",
     "cost": "not yet paid - declared at creation. 40 rebuilds the panel from "
             "the .dta and 428 re-derives it from prime_contracts.csv AS IT "
             "STANDS. Only 428 sees the archive merge (131), the rulings "
             "(174/427/64) and the as-of stamp (429). Skipping it left the "
             "panel 42 (entity, year) cells stale and $4,729,215.51 of "
             "village-corporation dollars booked on the village GOVERNMENT "
             "after the row table had already been corrected",
     "enricher_columns": ["obligations_usd_owner_asof_confirmed",
                          "obligations_usd_owner_asof_not_confirmed",
                          "owner_attribution_statuses",
                          "obligations_usd_tier_a", "obligations_usd_tier_b"]},
    {"rebuild": "24_funding_merge.py",
     "enricher": "503_identity.py",
     "file": "federal_funding_transactions.csv",
     "cost": "not yet paid - 505 runs LAST of all enrichers; any rebuild of a "
             "stamped table drops cedar_uid and ships a dataset a customer "
             "cannot join",
     "enricher_columns": ["cedar_uid"]},
    {"rebuild": "152_build_assistance_id_crosswalk.py",
     "enricher": "503_identity.py",
     # MOVED 2026-09-01 by 843 out of data/clean/ - it is a build input,
     # not a dataset.
     "file": "graveyard/cicd/assistance_tribe_id_crosswalk.csv",
     "cost": "not yet paid - declared at creation, same day as the "
             "reconciliation it protects",
     "enricher_columns": ["proposed_cedar_tribe_id", "confidence_tier",
                          "match_basis"]},
    {"rebuild": "24_funding_merge.py",
     "enricher": "503_identity.py",
     "file": "federal_funding_transactions.csv",
     "cost": "not yet paid - declared at creation. A 24 rebuild reverts the "
             "owner-directed Cedar-ID reconciliation of 350,465 rows "
             "(96.8% of lineageA dollars). The recovery chain CHANGED on "
             "2026-09-01: 843 dropped `tribe_id`, so 335 and 336 both derive "
             "from a column that is gone and now REFUSE by design. Re-run "
             "503 alone; 335/336 are retired for this file",
     # Renamed 2026-09-01 by 843. The old names here meant the survival check
     # was looking for two columns that cannot exist, so a 24 rebuild would
     # have read as having lost them on every future run.
     "enricher_columns": ["tribe_id_neid", "attribution_status",
                          "attribution_basis"]},
    # Declared 2026-08-28, the last Type-A collision (two wholesale writers of
    # one table, no declared order). Not a v1/v2 pair: 40 BUILDS the panel from
    # the BGOV export, then 131 merges the 631,507-row USAspending archive
    # backfill into prime_contracts.csv and REGENERATES the panel from the
    # merged data - which is why it backs up first. Running 40 after 131
    # rebuilds the panel from the pre-backfill table and silently drops the
    # archive rows, while printing a row count that reads as a normal build.
    #
    # Full chain for prime_contracts.csv:  40  ->  131  ->  207
    {"rebuild": "40_build_prime_contracts.py",
     "enricher": "131_merge_archive_backfill.py",
     "file": "prime_contracts_entity_year.csv",
     "cost": "not yet paid - declared before a 40 re-run could revert the "
             "FY2008-FY2022 archive backfill out of the panel",
     "enricher_columns": []},
    {"rebuild": "40_build_prime_contracts.py",
     "enricher": "207_normalize_extent_competed.py",
     "file": "prime_contracts.csv",
     "cost": "extent_competed_normalized and its _basis column are written "
             "in place; START_HERE.md records that a rebuild of "
             "prime_contracts.csv reverts it and 207 must be re-run",
     "enricher_columns": ["extent_competed_normalized",
                          "extent_competed_normalized_basis"]},
    # Declared 2026-09-02 by workstream PROMOTE (ADR-016). Same shape as 207:
    # nine columns written IN PLACE onto prime_contracts.csv from the local
    # archive extract and gapfill corpus. A 40 rebuild reverts all nine.
    # 950 is idempotent - it strips its own columns and rewrites them, and the
    # md5 of the 47 base fields is asserted unchanged - so re-running it after
    # any rebuild or after another in-place enricher is safe.
    {"rebuild": "40_build_prime_contracts.py",
     "enricher": "950_promote_contract_attributes.py",
     "file": "prime_contracts.csv",
     "cost": "not yet paid - declared before a rebuild could revert the "
             "6-digit NAICS, PSC, award description and action_date that "
             "prime_contracts.csv had never carried",
     "enricher_columns": ["contract_award_unique_key", "naics_code",
                          "naics_description", "action_date", "award_type",
                          "product_or_service_code",
                          "product_or_service_code_description",
                          "award_base_description",
                          "award_attributes_basis"]},
    # Declared 2026-08-29 by the `nagpra` closure pass, contract point C8.
    #
    # `build.py plan nagpra` printed "ENRICHER BACKUPS PRESENT on 2 table(s)
    # -> re-run unknown". "Unknown" is not a plan, so both backups were run to
    # ground and they turn out to be two different things.
    #
    # THE REAL ONE. 503 discovers its tables at RUNTIME - it stamps cedar_uid
    # into every data/clean CSV carrying one of 18 entity-id columns - so no
    # static io scan can attribute it and the plan listed zero phase-2
    # enrichers for a table 503 demonstrably edited. This ordering has been
    # PAID: 503 stamped the bridge on 2026-08-28 (the .bak_2026-08-28_pre505
    # is the receipt) and the 2026-08-29 rebuild reverted it. The released
    # bridge today has 14 columns and no cedar_uid, and the reason its replay
    # is byte-identical is that the enricher's work is currently ABSENT, not
    # that the plan reproduces it. `columns_lost_vs_backup` cannot see this:
    # the newest backup is the PRE-505 state, so the live table matches it.
    {"rebuild": "77_build_nagpra_dataset.py",
     "enricher": "503_identity.py",
     "file": "nagpra_notice_entity_bridge.csv",
     "cost": "PAID 2026-08-29 - a rebuild dropped the cedar_uid 503 stamped "
             "on 2026-08-28, and the shipped bridge lost the column a buyer "
             "joins the entity layer on. Re-run `503_identity.py stamp "
             "--apply` after any 77 build",
     "enricher_columns": ["cedar_uid"]},
    # AND THE ONE THAT IS NOT AN ENRICHER AT ALL, recorded because the next
    # agent will otherwise re-investigate it: `*.bak_2026-08-26_pre_342_
    # nagpra_refresh` beside BOTH nagpra tables is a hand-taken safety copy,
    # not an enricher's backup. 342_pull_federal_register_incremental.py names
    # its own backups `pre_342_pull_federal_register_incremental`, never
    # mentions NAGPRA, and writes only federal_actions*.csv. nagpra_notices.csv
    # carries no entity-id column either, so 503 skips it. Nothing enriches
    # nagpra_notices.csv, and no ordering is declared for it.
    #
    # 78 is the other rebuilder in nagpra's plan and it writes 18 tables, only
    # three of which belong to this collection. A full 78 run rewrites
    # lobbying_issue_families_filing.csv from scratch and drops five columns it
    # does not produce. The nagpra rebuild path therefore uses
    # `78_content_analysis.py --nagpra-only`, which holds those writes back;
    # the ordering below is what a FULL 78 run would owe.
    {"rebuild": "78_content_analysis.py",
     "enricher": "503_identity.py",
     "file": "lobbying_issue_families_filing.csv",
     "cost": "not yet paid - 78 is in the `nagpra` plan but rebuilds a "
             "`lobbying` table. Use `78_content_analysis.py --nagpra-only` "
             "for a nagpra rebuild; a full 78 run must be followed by 353 "
             "then 503",
     "enricher_columns": ["cedar_uid"]},
    {"rebuild": "78_content_analysis.py",
     "enricher": "353_propagate_lobbying_corrections_to_consumers.py",
     "file": "lobbying_issue_families_filing.csv",
     "cost": "not yet paid - see the sibling entry above. 353 writes the four "
             "entity_id_withdrawn* columns in place; a full 78 run reverts a "
             "correction, which is the disease corrections exist to cure",
     "enricher_columns": ["entity_id_withdrawn", "entity_id_withdrawn_reason",
                          "entity_id_withdrawn_by_script",
                          "entity_id_withdrawn_date"]},

    # ---- federal-register, declared 2026-08-29 during dataset closure ------
    # THE ONE THAT IS IN THE DOCUMENTED REBUILD COMMAND. `build.py run
    # federal-register --execute` puts `11_classify_federal_actions.py` in
    # phase 1, and 11 is a FULL REBUILD of federal_actions.csv from
    # federal_actions_raw.csv. That file carries two columns 11 does not write
    # - `pre_2000_flag` and `floor_basis_field`, put there IN PLACE by
    # `22_apply_temporal_floor.py`. So the collection's own rebuild command
    # silently drops the flag the published view filters on.
    #
    # This was not guessed at. `342_pull_federal_register_incremental.py` says
    # it in its own docstring - "**11 IS NOT RUN HERE**" - and 342 is the
    # script that actually refreshed this corpus on 2026-08-26 (its
    # `.bak_2026-08-26_pre_342_pull_federal_register_incremental` sits beside
    # both tables and is a hand-taken safety copy, NOT an enricher backup;
    # `columns_lost_vs_backup` is [] for both, so nothing is owed on those two
    # receipts and the next agent need not re-investigate them).
    {"rebuild": "11_classify_federal_actions.py",
     "enricher": "22_apply_temporal_floor.py",
     "file": "federal_actions.csv",
     "cost": "not yet paid, but it is inside `build.py run federal-register "
             "--execute`: 11 rebuilds this table from the raw pull and writes "
             "31 of its 33 columns. pre_2000_flag and floor_basis_field are "
             "22's, and the shipped view filters on pre_2000_flag. Prefer "
             "342_pull_federal_register_incremental.py, which appends and "
             "never runs 11; if 11 is run, re-run 22 immediately after",
     "enricher_columns": ["pre_2000_flag", "floor_basis_field"]},
    # SEVEN customer tables of the `federal-register` collection carry
    # `cedar_uid` and a `.bak_2026-08-28_pre505` receipt beside them. 503
    # discovers its tables at RUNTIME - it stamps every data/clean CSV carrying
    # one of 18 entity-id columns - so no static io scan can attribute it, and
    # `build.py plan federal-register` printed "ENRICHER BACKUPS PRESENT on 9
    # table(s) -> re-run unknown" for all of them. "Unknown" is not a plan.
    #
    # The cost is measured, not imagined. `dist/cedar_press.db` - the shipped
    # release - carries these seven tables WITHOUT cedar_uid: 28 columns where
    # the live consultation_events.csv has 29. The release predates the stamp,
    # so the state a rebuild would return them to is the state a buyer is
    # holding right now, and it is a table that joins to nothing.
    #
    # `70_key_unjoined_datasets.py` is here for a second reason as well. It is
    # the ONLY writer of federal_actions_entity_bridge.csv, and 293's io scan
    # cannot see it: the write is `wr(CLEAN / "federal_actions_entity_bridge.
    # csv", bridge)` and `wr(` matches no write hint, so the table has no
    # rebuilder in the io map and `build.py plan federal-register` omits 70
    # entirely. Declaring the ordering at least puts the script's name in the
    # contract, where the next agent will find it.
    {"rebuild": "96_build_consultation_events.py",
     "enricher": "503_identity.py",
     "file": "consultation_events.csv",
     "cost": "not yet paid HERE, but paid on the identical shape in nagpra on "
             "2026-08-29. The shipped release already has this table without "
             "cedar_uid (28 cols vs 29 live); a rebuild returns it there. "
             "Re-run `503_identity.py stamp --apply` after any 96 build",
     "enricher_columns": ["cedar_uid"]},
    {"rebuild": "70_key_unjoined_datasets.py",
     "enricher": "503_identity.py",
     "file": "federal_actions_entity_bridge.csv",
     "cost": "not yet paid - and 70 is invisible to `build.py plan` because "
             "293's io scan does not recognise its `wr(` write helper, so a "
             "planned rebuild of this collection leaves the bridge stale "
             "rather than reverting it. Run 70 by hand after 11, then 503",
     "enricher_columns": ["cedar_uid"]},
    {"rebuild": "154_build_fr_ex_parte_notices.py",
     "enricher": "503_identity.py",
     "file": "fr_ex_parte_parties.csv",
     "cost": "not yet paid - declared on the pre505 receipt beside the table",
     "enricher_columns": ["cedar_uid"]},
    {"rebuild": "154_build_fr_ex_parte_notices.py",
     "enricher": "503_identity.py",
     "file": "fr_ex_parte_party_entity_links.csv",
     "cost": "not yet paid - declared on the pre505 receipt beside the table",
     "enricher_columns": ["cedar_uid"]},
    {"rebuild": "134_build_nepa_eplanning.py",
     "enricher": "503_identity.py",
     "file": "nepa_administrative_record_parties.csv",
     "cost": "not yet paid - declared on the pre505 receipt beside the table",
     "enricher_columns": ["cedar_uid"]},
    {"rebuild": "130_build_section_106_consultation.py",
     "enricher": "503_identity.py",
     "file": "section_106_consultation_events.csv",
     "cost": "not yet paid - declared on the pre505 receipt beside the table. "
             "130 is also AMBIGUOUS to build.py (it rebuilds "
             "section_106_source_coverage.csv and enriches this file), so it "
             "is not in the plan at all and must be run by hand - see "
             "docs/datasets/federal-register.md",
     "enricher_columns": ["cedar_uid"]},
    {"rebuild": "130_build_section_106_consultation.py",
     "enricher": "503_identity.py",
     "file": "section_106_project_parties.csv",
     "cost": "not yet paid - declared on the pre505 receipt beside the table",
     "enricher_columns": ["cedar_uid"]},
    # Declared 2026-09-01 by the GRAIN-HUB workstream, and the same shape as
    # the 114 -> 430 entry above: a ONE-TIME BACKFILL, not a standing
    # dependency, and saying so is the point.
    {"rebuild": "169_build_identifier_graph.py",
     "enricher": "741_hub_grain_and_rebuild.py",
     "file": "cedar_identifier_graph_edges.csv",
     "cost": "NONE. 169 now writes `asserting_row_ref` on BLOCK edges "
             "itself, so a rebuild WRITES the column rather than dropping it. "
             "741 is a one-time splice of the ruling-map BLOCK slice for the "
             "rows built before that change - the 2,451 apparent literal "
             "duplicates that were distinct applications of a negative ruling "
             "to distinct target rows all along - and is a no-op on a fresh "
             "169 build. 169 was deliberately NOT re-run: it also rebuilds "
             "cedar_identifier_graph_nodes.csv and "
             "cedar_identifier_propagation.csv, and 354 and 427 have written "
             "to the graph since it last ran",
     "enricher_columns": ["asserting_row_ref"]},
    # Declared 2026-09-02 by the GRAIN-LEGISLATION workstream. `bill_votes.csv`
    # had NO declared ordering at all - `enrichers_to_rerun('bill_votes.csv')`
    # returned an empty list - while carrying TWO in-place enrichers against
    # one wholesale writer. 14 does `v.to_csv(CLEAN / "bill_votes.csv")`, which
    # is a full rewrite; 73 and 890 both read the live file and write it back.
    # This is the ferc_docket_filings.csv shape exactly, and the only reason it
    # has not cost anything yet is that 14 has not been re-run.
    {"rebuild": "14_build_bills_votes.py",
     "enricher": "73_bills_votes_completion.py",
     "file": "bill_votes.csv",
     "cost": "not yet paid - declared 2026-09-02 on discovering the file had "
             "no ordering. 73 writes the official-verification join, the "
             "anti-tribal direction fields and the pre-2000 floor back into "
             "the live table in place (it backs up first, which is the "
             "signal); a 14 rebuild reverts all of it",
     "enricher_columns": ["bill_link_status", "official_source_url",
                          "official_question", "official_result",
                          "counts_agree_with_official", "question_family"]},
    {"rebuild": "14_build_bills_votes.py",
     "enricher": "890_bill_votes_threshold_and_titles.py",
     "file": "bill_votes.csv",
     "cost": "not yet paid - declared at creation. A rebuild drops "
             "`threshold_required`, and the sixteen votes recorded as "
             "failures on a majority tally go back to looking like data "
             "errors - one of them, H105-0482 (229-176, Failed), sits in the "
             "shipped 10-row sample. It also drops `bill_title`, which is the "
             "only thing on the row that says what was voted on. 890 must run "
             "AFTER 73, because it reads `question` and `result` as 73 leaves "
             "them and cross-checks them against the official record 73 "
             "joined",
     "enricher_columns": ["bill_title", "bill_title_source",
                          "threshold_required", "threshold_required_source",
                          "threshold_required_basis",
                          "threshold_derived_from_question",
                          "threshold_agrees_with_official",
                          "result_reconciles_with_threshold"]},
    # WORKSTREAM INT-READY, 2026-09-02. Two enrichers declared at creation.
    {"rebuild": "23d_build_gaming_facilities.py",
     "enricher": "960_promote_gaming_facility_class_and_revenue_reach.py",
     "file": "gaming_facilities.csv",
     "cost": "not yet paid - declared at creation. Any rebuild of the "
             "facility table drops the eleven columns 960 appends, and with "
             "them the only path from a facility to "
             "`gaming_revenue_bounds.csv` (694 of 787 facilities), the only "
             "statement of Class II / Class III on the record (684 of 787), "
             "and the quoted statute or compact clause that explains why 174 "
             "facilities in seven states can never carry a revenue figure. "
             "Re-run 960 after any facility rebuild; the "
             "`.bak_<date>_pre960` beside the table is the signal",
     "enricher_columns": ["gaming_class_ii_authorized",
                          "gaming_class_iii_authorized",
                          "gaming_class_basis", "gaming_class_source_url",
                          "has_revenue_bound",
                          "n_revenue_bound_fiscal_years",
                          "revenue_bound_strongest_status",
                          "revenue_bound_basis",
                          "revenue_bound_absent_reason",
                          "state_revenue_disclosure_status",
                          "state_revenue_disclosure_basis"]},
    {"rebuild": "503_identity.py",
     "enricher": "961_promote_register_legal_names_and_state.py",
     "file": "cedar_identity_register.csv",
     "cost": "not yet paid - declared at creation. 503 rewrites the register "
             "from a FIXED ten-column list and drops all five of 961's "
             "columns, including the Federal Register legal name for 536 "
             "entities that 510 buyers cannot otherwise search for. "
             "SEPARATELY AND WORSE: that same fixed list still names "
             "`same_as_legacy_cicd`, which 843 deliberately retired from the "
             "data on 2026-09-01, so a 503 rebuild REINTRODUCES a retired "
             "identifier scheme. Recorded in docs/KNOWN_ISSUES.md; not fixed "
             "here because 503 is identity-critical and owned elsewhere",
     "enricher_columns": ["federal_register_legal_name",
                          "federal_register_legal_name_basis",
                          "federal_register_legal_name_url",
                          "state", "minted_basis"]},
]


# ---------------------------------------------------------------------------
# DECLARED REPLAY ORDERS - the SEQUENCE, where KNOWN_ORDERINGS only has PAIRS
# ---------------------------------------------------------------------------
#: `KNOWN_ORDERINGS` says "B must run after A". That is enough to stop a
#: rebuild reverting one enricher, and it is NOT enough to rebuild a table from
#: nothing: for that you need the whole sequence, in order, and `plan_for`
#: returns the enrichers LEXICOGRAPHICALLY (`50`, `503`, `51`, `52`, ...),
#: which is not the order anything was applied in.
#:
#: That gap was the whole of the `_entity_layer` C8 blocker: not the backups -
#: every spine enricher takes one, and as of 2026-09-01 so do `01` and `09` -
#: but the fact that nobody could state what a replay must RUN, or prove that
#: running it reproduces the 1,555 rows and 44 columns on disk.
#:
#: THE ORDER BELOW WAS NOT DECLARED FROM MEMORY. Every spine enricher writes a
#: `cedar_entity_spine.csv.bak_<date>_pre<NN>` before it touches the file, so
#: `data/spine` in modification-time order IS the applied order, and each
#: backup's header is the column set as it stood immediately before that
#: enricher ran. `741_hub_grain_and_rebuild.py census` reads that trail and
#: emits the row-and-column genealogy to `docs/schema/hub_rebuild_census.json`
#: - 687 rows / 12 columns at the earliest checkpoint, 1,555 / 44 live, with
#: all 32 added columns attributed to a named stage.
#:
#: `two_of_these_mint`: 426 mints spine entities outright and 503 mints
#: cedar_uids. 503 re-uses an existing uid keyed on the handle and `handle`
#: equals `tribe_id` on all 1,555 of 1,555 rows, so it is safe to replay; 426
#: must be checked against the append-only register FIRST, because a wrong
#: replay cannot be undone by deleting rows from a register.
REPLAY_ORDERS = {
    "cedar_entity_spine.csv": {
        "rebuild": "01_build_entity_spine.py",
        "order": [
            "51_add_anc_acronym_aliases.py",
            "52_add_village_corporations.py",
            "61_add_nho_intertribal_to_spine.py",
            "66_build_entity_hierarchy.py",
            "69_enrich_spine_from_federal_register.py",
            "71_fix_known_defects.py",
            "74_add_organization_acronyms.py",
            "73_add_tcu_and_cdfi.py",
            "75_add_bie_schools_and_uios.py",
            "163_promote_nho_universe_in_place.py",
            "241_promote_individual_native_firms_in_place.py",
            "416_reconcile_spine_id_columns.py",
            "426_mint_bristol_bay_spine_entities.py",
            "503_identity.py",
            "524_universe_gap.py",
        ],
        "mints": ["426_mint_bristol_bay_spine_entities.py",
                  "503_identity.py"],
        "gate": "the post-replay spine must have >= 1,555 rows and all 44 "
                "columns listed in docs/schema/hub_rebuild_census.json. "
                "Anything less is a partial restore wearing a green build log",
        "evidence": "read off the cedar_entity_spine.csv.bak_<date>_pre<NN> "
                    "trail in data/spine by "
                    "741_hub_grain_and_rebuild.py census, 2026-09-01",
        "no_checkpoint": ["08_build_review_page.py",
                          "115_pull_assistance_archive.py"],
        "warning": "01 came off NEVER_RUN on 2026-09-01 because it now "
                   "append-merges: it still computes only 687 rows and 12 "
                   "columns from canonical_tribe_table.csv, but it can no "
                   "longer drop the other 868 entities or the other 32 "
                   "columns - merge_table raises instead. This order is still "
                   "how you REPLAY the hub after a restore; it is not a "
                   "reason to take it apart",
    },
}


def replay_order(table):
    """The declared full replay sequence for `table`, or None.

    Distinct from `all_orderings(table)`, which returns unordered PAIRS.
    """
    return REPLAY_ORDERS.get(Path(str(table)).name)


LINT_REPORT = CEDAR / "docs" / "lint_bug_classes.json"


def derived_orderings():
    """Rebuild->enricher orderings DERIVED from 293's class6 scan.

    `KNOWN_ORDERINGS` above is the curated set: five pairs, each carrying a
    measured `cost` a person wrote after paying it. But 293 finds THIRTY-TWO
    class6 tables, so twenty-seven orderings existed only as a lint finding -
    real, detected, and invisible to anything that wanted to RUN a build in the
    right order.

    Hand-typing the missing twenty-seven would have created a second list to
    keep in sync with the detector, which is the same disease as a
    hand-maintained count. So they are derived from the detector's own
    `class6_io_map` instead, and marked `source: "derived"` with an empty
    `cost`: a machine can tell you the ordering exists, it cannot tell you what
    ignoring it cost. Promote an entry into KNOWN_ORDERINGS by hand once
    someone has paid for it and can write that sentence.

    Returns [] rather than raising if the lint report is absent or stale -
    this module is imported by `guard()` on every script start, and an import
    that can fail is an import that gets removed.
    """
    try:
        import json
        m = json.loads(LINT_REPORT.read_text(encoding="utf-8"))["class6_io_map"]
        rebuilders = m.get("rebuilders", {})
        enrichers = m.get("enrichers", {})
    except Exception:
        return []
    curated = {(o["file"], o["rebuild"], o["enricher"]) for o in KNOWN_ORDERINGS}
    out = []
    for table in sorted(set(rebuilders) & set(enrichers)):
        for rb in sorted(rebuilders[table]):
            for en in sorted(enrichers[table]):
                if rb == en or (table, rb, en) in curated:
                    continue
                out.append({"rebuild": rb, "enricher": en, "file": table,
                            "cost": "", "enricher_columns": [],
                            "source": "derived"})
    return out


def all_orderings(table=None):
    """Every known ordering: curated first, then derived. Optionally one table.

    This is what a build runner should consume. Curated entries come first so a
    caller that takes the first match gets the human-written one.
    """
    rows = [dict(o, source=o.get("source", "curated")) for o in KNOWN_ORDERINGS]
    rows += derived_orderings()
    if table is not None:
        t = Path(str(table)).name
        rows = [o for o in rows if o["file"] == t]
    return rows


def enrichers_to_rerun(table):
    """Every enricher that must run AFTER a rebuild of `table`, curated+derived.

    The ordering rule this project keeps paying for: the enricher runs LAST.
    """
    return sorted({o["enricher"] for o in all_orderings(table)})


def enricher_backups_for(table):
    """The `.bak_<date>_pre_<script>` files sitting beside a clean table.

    Their existence is the signal that an in-place enricher has touched it.
    Returns newest-first.
    """
    t = Path(str(table)).name
    return sorted(CLEAN.glob(t + ".bak_*"),
                  key=lambda p: p.stat().st_mtime, reverse=True)


def columns_of(path):
    import csv
    import sys
    csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))
    try:
        with open(path, encoding="utf-8-sig", errors="replace",
                  newline="") as fh:
            return [c.strip() for c in next(csv.reader(fh), [])]
    except OSError:
        return []


def columns_lost_vs_backup(table):
    """Columns present in the newest enricher backup but ABSENT from the live
    table. Non-empty means a rebuild reverted an enricher.

    This is the check that would have caught the 133/168 collision at the
    moment it happened instead of four hours later.
    """
    t = CLEAN / Path(str(table)).name
    baks = enricher_backups_for(t)
    if not t.exists() or not baks:
        return [], None
    live = set(columns_of(t))
    bak = columns_of(baks[0])
    return [c for c in bak if c not in live], baks[0].name


if __name__ == "__main__":
    print("=== cedar_pipeline self-test ===\n")
    for s in sorted(NEVER_RUN):
        try:
            guard(s)
            print(f"  !! {s} WAS NOT REFUSED - the guard is broken")
        except ForbiddenScript:
            print(f"  refused: {s}")
    print(f"\n  override accepted: {guard('41_build_codebooks.py', OVERRIDE_TOKEN)}")
    print(f"  ordinary script:   {guard('62_no_regression_check.py')}")
    print("\n  classify:")
    for s in ("133_build_ferc_advocacy.py", "168_link_adjudication_hubs.py",
              "207_normalize_extent_competed.py"):
        p = CODE / s
        if p.exists():
            k, ev = classify(p)
            print(f"    {s:52s} {k:9s} {ev[:1]}")
    print("\n  enricher backups beside ferc_docket_filings.csv:")
    for b in enricher_backups_for("ferc_docket_filings.csv")[:3]:
        print(f"    {b.name}")
    lost, src = columns_lost_vs_backup("ferc_docket_filings.csv")
    print(f"\n  columns lost vs {src}: {lost or 'none'}")

# =====================================================================
# STATE VALIDATION - shared, because two scripts need the same answer.
# =====================================================================
# Lives here rather than in 71_fix_known_defects.py because 01 needs it
# too, and a module whose name starts with a digit cannot be imported by
# name. Two copies of a validator is how the two of them drift apart.
US_STATES = set(
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS "
    "MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV "
    "WI WY DC PR VI GU AS MP".split())

_STATE_NAME = {
    "ALABAMA": "AL", "ALASKA": "AK", "ARIZONA": "AZ", "ARKANSAS": "AR",
    "CALIFORNIA": "CA", "COLORADO": "CO", "CONNECTICUT": "CT",
    "DELAWARE": "DE", "FLORIDA": "FL", "GEORGIA": "GA", "HAWAII": "HI",
    "IDAHO": "ID", "ILLINOIS": "IL", "INDIANA": "IN", "IOWA": "IA",
    "KANSAS": "KS", "KENTUCKY": "KY", "LOUISIANA": "LA", "MAINE": "ME",
    "MARYLAND": "MD", "MASSACHUSETTS": "MA", "MICHIGAN": "MI",
    "MINNESOTA": "MN", "MISSISSIPPI": "MS", "MISSOURI": "MO", "MONTANA": "MT",
    "NEBRASKA": "NE", "NEVADA": "NV", "NEW HAMPSHIRE": "NH",
    "NEW JERSEY": "NJ", "NEW MEXICO": "NM", "NEW YORK": "NY",
    "NORTH CAROLINA": "NC", "NORTH DAKOTA": "ND", "OHIO": "OH",
    "OKLAHOMA": "OK", "OREGON": "OR", "PENNSYLVANIA": "PA",
    "RHODE ISLAND": "RI", "SOUTH CAROLINA": "SC", "SOUTH DAKOTA": "SD",
    "TENNESSEE": "TN", "TEXAS": "TX", "UTAH": "UT", "VERMONT": "VT",
    "VIRGINIA": "VA", "WASHINGTON": "WA", "WEST VIRGINIA": "WV",
    "WISCONSIN": "WI", "WYOMING": "WY", "DISTRICT OF COLUMBIA": "DC",
    "PUERTO RICO": "PR",
}


def clean_state(raw, own_uei=""):
    """Return (value, verdict). A state column may only hold a state.

    Verdicts NAME what was rejected rather than counting it - the class2c
    defect in 293 is a refusal counter that never says what it refused, and a
    silent blanking of 12,127 rows is precisely that defect at scale.

    A multi-state string is NOT split into a first state. 'ARIZONA;
    CALIFORNIA; COLORADO' is a registrant operating in three places, and
    picking the first would invent a headquarters the source never claimed.
    """
    v = (raw or "").strip().upper()
    if not v:
        return "", "empty"
    if v in US_STATES:
        return v, "kept"
    if v in _STATE_NAME:
        return _STATE_NAME[v], "normalised from full name"
    if own_uei and v == (own_uei or "").strip().upper():
        return "", "REJECTED: held this row's own UEI"
    if ";" in v:
        return "", "REJECTED: multi-state string, no single state claimed"
    if len(v) == 12 and v.isalnum():
        return "", "REJECTED: looks like a UEI"
    return "", f"REJECTED: not a state ({v[:24]})"


# =====================================================================
# APPEND-MERGE - the C8 machinery, shared because three builders need it
# =====================================================================
# WHY THIS EXISTS, IN ONE PARAGRAPH
# ---------------------------------
# `NEVER_RUN` above named four scripts that destroy on rerun. Three of them
# destroy for exactly ONE reason: they open their output in "w" mode and write
# only what they themselves computed, so every row and every column that
# reached the table from somewhere else is gone. That is not a property of
# what they compute - 01's 687 canonical entities are all correct - it is a
# property of HOW THEY WRITE. Fixing the write fixes all three, and a shared
# implementation is the only way the three do not drift apart the way two
# copies of a state validator would.
#
# THE CONTRACT merge_table ENFORCES (2026-09-01, workstream C8)
# -------------------------------------------------------------
#   1. NO ROW IS EVER LOST. Every live row survives, in its original order.
#      A rebuilt row whose key is unseen is APPENDED after them.
#   2. NO COLUMN IS EVER LOST. Live column order is preserved and columns the
#      builder introduces are appended on the right. This is the project's
#      single most repeated defect - it hit admin_appeal_positions.csv, two
#      gaming tables and four Federal Register tables on 2026-08-31 alone -
#      so it is an assertion here, not a convention.
#   3. A BUILDER MAY NOT SILENTLY OVERWRITE. On a row that already exists it
#      fills BLANK cells only. Where the live cell is non-blank and differs
#      from what the rebuild computed, the LIVE value stands and the pair is
#      recorded as drift. `refresh` names the columns the builder genuinely
#      owns and may overwrite; naming a column there is a claim that no other
#      script writes it, and that claim should be checked with a grep before
#      it is made.
#   4. DRIFT IS REPORTED, NEVER DISCARDED. MergeReport.drift carries every
#      (key, column, live, rebuilt) triple the merge declined to apply. A
#      rebuild that would have changed 4,000 cells and a rebuild that would
#      have changed none must not look the same in the log.
#
# WHAT THIS DOES NOT DO. It does not make a builder correct, and it is not a
# licence to rebuild casually. It makes a rebuild ADDITIVE, which is the
# precondition C8 asks for: "ONE documented rebuild path reproduces the tables
# without destroying later enrichment".

import csv as _csv
import shutil as _shutil
from datetime import date as _date


class MergeReport:
    """What a merge did, in numbers a gate can assert on."""

    def __init__(self, path):
        self.path = str(path)
        self.rows_before = 0
        self.rows_after = 0
        self.rows_appended = 0
        self.rows_matched = 0
        self.rows_lost = 0          # MUST be 0
        self.cols_before = []
        self.cols_after = []
        self.cols_lost = []         # MUST be empty
        self.cols_added = []
        self.cells_filled = 0       # blank live cell -> rebuilt value
        self.cells_refreshed = 0    # builder-owned column overwritten
        self.drift = []             # (key, column, live_value, rebuilt_value)

    @property
    def ok(self):
        return self.rows_lost == 0 and not self.cols_lost

    def as_dict(self):
        return {
            "path": self.path,
            "rows_before": self.rows_before,
            "rows_after": self.rows_after,
            "rows_appended": self.rows_appended,
            "rows_matched": self.rows_matched,
            "rows_lost": self.rows_lost,
            "n_cols_before": len(self.cols_before),
            "n_cols_after": len(self.cols_after),
            "cols_lost": self.cols_lost,
            "cols_added": self.cols_added,
            "cells_filled": self.cells_filled,
            "cells_refreshed": self.cells_refreshed,
            "n_drift_cells": len(self.drift),
            "ok": self.ok,
        }

    def __str__(self):
        return (f"{Path(self.path).name}: "
                f"{self.rows_before:,} -> {self.rows_after:,} rows "
                f"(+{self.rows_appended:,} new, {self.rows_matched:,} matched, "
                f"{self.rows_lost} lost), "
                f"{len(self.cols_before)} -> {len(self.cols_after)} cols "
                f"(lost {self.cols_lost or 'none'}), "
                f"{self.cells_filled:,} blanks filled, "
                f"{self.cells_refreshed:,} refreshed, "
                f"{len(self.drift):,} drift cells held back")


def read_table(path):
    """(rows, fieldnames). A missing file is ([], []) - not an error."""
    p = Path(path)
    if not p.exists():
        return [], []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        rdr = _csv.DictReader(fh)
        rows = [dict(r) for r in rdr]
        return rows, list(rdr.fieldnames or [])


def ordinal_key(key_cols):
    """A key function that appends an occurrence ordinal.

    Three rows of cedar_identifier_ledger.csv share (identifier_type,
    identifier, tribe_id, source_file) and 86 (identifier_type, identifier)
    pairs recur in cedar_identifier_ledger_final.csv. A merge keyed on a
    non-unique tuple would collapse them, which is a row loss wearing the
    word 'deduplication'. Ordinal-within-key makes the key total, and it is
    the same repair HUB applied to the ruling map on 2026-09-01.
    """
    seen = {}

    def kf(row):
        base = tuple((row.get(c) or "").strip().upper() for c in key_cols)
        seen[base] = seen.get(base, 0) + 1
        return base + (seen[base],)

    return kf


def write_table(path, rows, fields, backup_tag=None):
    """Backup-then-write. The backup is unconditional where a tag is given;
    see .gitignore line 95 - data/spine/* is not in git and git cannot
    restore it."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and backup_tag:
        b = path.with_name(
            f"{path.name}.bak_{_date.today().isoformat()}_{backup_tag}")
        if not b.exists():
            _shutil.copy2(path, b)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = _csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return path


def merge_table(path, rebuilt_rows, rebuilt_fields, key_cols,
                refresh=(), dry_run=False, backup_tag=None,
                drift_report=None):
    """Append-merge `rebuilt_rows` into the live table at `path`.

    Returns (merged_rows, merged_fields, MergeReport). Writes nothing when
    `dry_run` is true, which is how 812_c8_rebuild_proof.py proves the merge
    reproduces the census WITHOUT touching a live table.
    """
    path = Path(path)
    rep = MergeReport(path)
    refresh = set(refresh)

    live_rows, live_fields = read_table(path)
    rep.rows_before = len(live_rows)
    rep.cols_before = list(live_fields)

    # -- column union, live order first ---------------------------------
    fields = list(live_fields)
    for c in rebuilt_fields:
        if c not in fields:
            fields.append(c)
    rep.cols_after = fields
    rep.cols_added = [c for c in fields if c not in live_fields]
    rep.cols_lost = [c for c in live_fields if c not in fields]   # always []

    if not live_rows:
        # First build. Nothing to preserve, nothing to protect.
        out = [{c: (r.get(c) or "") for c in fields} for r in rebuilt_rows]
        rep.rows_after = len(out)
        rep.rows_appended = len(out)
        if not dry_run:
            write_table(path, out, fields, backup_tag=backup_tag)
        return out, fields, rep

    kf_live = ordinal_key(key_cols)
    index = {}
    out = []
    for r in live_rows:
        row = {c: (r.get(c) or "") for c in fields}
        index[kf_live(r)] = row
        out.append(row)

    kf_new = ordinal_key(key_cols)
    for r in rebuilt_rows:
        k = kf_new(r)
        tgt = index.get(k)
        if tgt is None:
            row = {c: (r.get(c) or "") for c in fields}
            out.append(row)
            index[k] = row
            rep.rows_appended += 1
            continue
        rep.rows_matched += 1
        for c in rebuilt_fields:
            new = (r.get(c) or "")
            if new == "":
                continue                      # a rebuild never blanks a cell
            cur = tgt.get(c, "")
            if cur == "":
                tgt[c] = new
                rep.cells_filled += 1
            elif cur != new:
                if c in refresh:
                    tgt[c] = new
                    rep.cells_refreshed += 1
                else:
                    rep.drift.append((" | ".join(str(x) for x in k[:-1]),
                                      c, cur, new))

    rep.rows_after = len(out)
    rep.rows_lost = rep.rows_before - sum(1 for r in out[:rep.rows_before]
                                          if r is not None)

    if rep.cols_lost:
        raise RuntimeError(
            f"merge_table would drop columns from {path.name}: {rep.cols_lost}")

    if drift_report and rep.drift and not dry_run:
        Path(drift_report).parent.mkdir(parents=True, exist_ok=True)
        with open(drift_report, "w", encoding="utf-8", newline="") as fh:
            w = _csv.writer(fh)
            w.writerow(["key", "column", "live_value_kept",
                        "rebuild_value_declined"])
            w.writerows(rep.drift)

    if not dry_run:
        write_table(path, out, fields, backup_tag=backup_tag)
    return out, fields, rep
