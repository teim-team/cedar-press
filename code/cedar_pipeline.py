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
    "01_build_entity_spine.py":
        "A full rebuild DROPS EVERY APPENDED ENTITY - the village "
        "corporations, NHOs, TCUs, CDFIs, BIE schools and UIOs added by "
        "scripts 52, 61, 73 and 75. Safe to IMPORT, never to RUN. "
        "Append-merge instead, re-reading the spine immediately before "
        "writing so a concurrent agent is not clobbered.",
    "09_import_rulings.py":
        "Rebuilds cedar_identifier_ledger_final.csv FROM the stale "
        "cedar_identifier_ledger_tiered.csv, which does not carry rows later "
        "scripts appended directly to _final. Running it on 2026-08-08 "
        "destroyed 1,327 ledger rows and 451 village-corporation links, 121 "
        "of them tier A - lost, not moved. Use "
        "124_apply_rulings_in_place.py.",
    "41_build_codebooks.py":
        "Writes codebook_master.csv in 'w' mode from a hardcoded 19-group "
        "DATASETS dict. Running it today DELETES 21 OF THE 43 dataset "
        "blocks, including every block registered on 2026-08-26. The single "
        "most destructive command in the repo, and its name does not say so. "
        "Use cedar_codebook.write_fragment() or cedar_register_codebook.py.",
    "88_build_deals_taxonomy.py":
        "Rebuilds the deals taxonomy. Its glob read deals_*_additions.csv "
        "and never saw the 131 rows in the two root ledgers - the miscount "
        "that propagated as '790 deals' for three weeks. The glob was "
        "repaired at source, but a full taxonomy rebuild still discards the "
        "party rulings 33/53/57/154 wrote in place.",
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
     "cost": "09 reverts 50's patches; 09 is in NEVER_RUN for this and worse",
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
             "dataset now materialises. 01 is NEVER_RUN; if it is ever forced, "
             "re-run 504 then 505",
     "enricher_columns": ["cedar_uid"]},
    {"rebuild": "24_funding_merge.py",
     "enricher": "503_identity.py",
     "file": "federal_funding_transactions.csv",
     "cost": "not yet paid - 505 runs LAST of all enrichers; any rebuild of a "
             "stamped table drops cedar_uid and ships a dataset a customer "
             "cannot join",
     "enricher_columns": ["cedar_uid"]},
    {"rebuild": "152_build_assistance_id_crosswalk.py",
     "enricher": "503_identity.py",
     "file": "assistance_tribe_id_crosswalk.csv",
     "cost": "not yet paid - declared at creation, same day as the "
             "reconciliation it protects",
     "enricher_columns": ["proposed_cedar_tribe_id", "confidence_tier",
                          "match_basis"]},
    {"rebuild": "24_funding_merge.py",
     "enricher": "503_identity.py",
     "file": "federal_funding_transactions.csv",
     "cost": "not yet paid - declared at creation. A 24 rebuild reverts the "
             "owner-directed Cedar-ID reconciliation of 350,465 rows "
             "(96.8% of lineageA dollars); re-run 335 -> 336 -> 503 after",
     "enricher_columns": ["tribe_id_neid", "tribe_id_scheme_resolved",
                          "tribe_id_scheme_resolved_basis"]},
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
]


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
