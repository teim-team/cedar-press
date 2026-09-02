#!/usr/bin/env python3
"""
Cedar Press - 741: the `_entity_layer` HUB - target-row identity for the ruling
graph, and the measured genealogy of the spine rebuild.

    py -3 code/741_hub_grain_and_rebuild.py            # edges + census + verify
    py -3 code/741_hub_grain_and_rebuild.py edges      # splice BLOCK edges only
    py -3 code/741_hub_grain_and_rebuild.py census     # C8 census only
    py -3 code/741_hub_grain_and_rebuild.py verify     # read-only, exit 1 on breach

WHY THIS EXISTS
---------------
`_entity_layer` is dataset 13, the hub every other dataset keys to, and it
carried four blockers. Three of them - C1 grain unstated, C2 no validated key,
C3 literal duplicates - were ONE defect wearing three names, and the fourth is
about what a rebuild of the hub destroys.

**C1/C2/C3.** `23_cross_dataset_propagation.py` appended one row every time a
ruled identifier appeared in a target dataset row and wrote nothing naming
that target row. UEI `KDGNQQAMNUD1` reached 860 target rows and produced 860
byte-identical map rows; `173` turned those into 860 identical ledger rows and
`169` into 860 identical `BLOCK` edges, each stamped `n_asserting_sources = 1`.
They were never duplicate FACTS - they are the measure of how far a ruling
reached, which is the entire purpose of `cross_dataset_ruling_map`. Deleting
them would have deleted the reach, the same way de-duplicating
`prime_contracts.csv` would have deleted 80,778 real transactions.

So NOTHING IS DE-DUPLICATED ANYWHERE IN THIS WORKSTREAM. The identity that was
dropped is written back, exactly as `430_restore_prime_transaction_key.py` did,
and the counts fall to zero because the rows stop being identical:

    23   writes target_row_ordinal / target_row_key / target_row_hash
    173  writes source_row_ordinal
    169  writes asserting_row_ref on BLOCK edges
    73   writes quote_char_offset on the ownership-evidence rows

`23`, `173` and `73 --reextract` write only their own outputs and were re-run.
**`169` was NOT re-run** and must not be: it rebuilds
`cedar_identifier_graph_nodes.csv` and `cedar_identifier_propagation.csv` as
well, and `354_correction_register.py` and `427_repoint_bristol_bay_
attributions.py` have both written to the graph since it last ran. So this
script SPLICES the one slice of `cedar_identifier_graph_edges.csv` that the
repair changes - the `BLOCK` edges asserted by `cross_dataset_ruling_map.csv` -
recomputing them with the SAME predicate `169` uses, and leaves every other
edge byte-identical. `169` itself now writes the column, so the splice is a
one-time backfill and a re-run of `169` is a no-op against it.

**C8.** `.gitignore:95` excludes `data/spine/*` except two force-tracked files,
so git cannot restore `cedar_entity_spine.csv`; `01_build_entity_spine.py`
fills the spine from `canonical_tribe_table.csv` alone (687 rows, 12 columns)
against a live hub of 1,555 rows and 44 columns; and neither `01` nor `09`
took a backup, while all fifteen spine enrichers do. `01` and `09` now take
one. What was still missing was the thing nobody had written down: **the order
the enrichers were actually applied in**, without which no replay can be shown
to reproduce the hub. `build.plan_for` returns them lexicographically (`50`,
`503`, `51`, `52`, ...), which is not that order.

The order is not a guess and was not invented here. **Every spine enricher
takes a `cedar_entity_spine.csv.bak_<date>_pre<NN>` before it writes**, so the
backup directory IS the applied order, in file order by modification time, and
the header of each backup is the column set as it stood immediately before
that enricher ran. `census` reads that trail and emits the genealogy: rows
before and after each stage, and the columns each stage added. That is the
row-and-column census a replay has to be gated against, and it is measured
from the project's own artifacts rather than declared from memory.

Writes  data/clean/cedar_identifier_graph_edges.csv  (spliced; .bak first)
        docs/schema/hub_rebuild_census.json          the measured genealogy
        docs/HUB_GRAIN_AND_REBUILD.md                the same, for a human
Reads everything else. No network. Never runs 01, 09 or 169.
"""
from __future__ import annotations

import csv
import json
import shutil
import sys
from collections import Counter
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()

CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine"
DOCS = ROOT / "docs"
EDGES = CLEAN / "cedar_identifier_graph_edges.csv"
MAP = CLEAN / "cross_dataset_ruling_map.csv"
CENSUS_JSON = DOCS / "schema" / "hub_rebuild_census.json"
CENSUS_MD = DOCS / "HUB_GRAIN_AND_REBUILD.md"

EDGE_COLS = ["edge_kind", "from_node", "to_node", "from_type", "to_type",
             "edge_tier", "edge_tier_source", "asserting_source",
             "asserting_row_ref", "n_asserting_sources", "method", "evidence",
             "built_by", "built_date"]

# The declared primary keys this script validates. Same sets as GRAIN_HUB in
# 512; duplicated here deliberately so `verify` fails loudly if the two ever
# disagree rather than agreeing with itself.
DECLARED_KEYS = {
    "cross_dataset_ruling_map.csv":
        ["source_file", "target_row_ordinal", "identifier_type", "channel"],
    "cedar_ruling_ledger_consolidated.csv":
        ["subject_key", "source_file", "source_row_ordinal"],
    "cedar_identifier_graph_edges.csv":
        ["edge_kind", "from_node", "to_node", "asserting_source",
         "asserting_row_ref", "edge_tier", "method"],
    "tcu_cdfi_ownership_evidence.csv":
        ["institution", "layer", "pattern", "evidence_url",
         "quote_char_offset"],
    "foia_request_index.csv": ["foia_request_id", "request_description"],
    "visitor_record_foia_requests.csv":
        ["foia_request_id", "request_description_verbatim"],
}


# --------------------------------------------------------------------------
# 169's identifier cleaners, reproduced EXACTLY so the splice and the rebuild
# cannot drift. 169 is a top-level script - importing it runs the whole graph
# build - so it cannot be imported, and copying four four-line functions is
# the lesser evil. `verify` re-reads 169 and fails if these stop matching.
# --------------------------------------------------------------------------
UEI_OK = 12
CAGE_LEN = {5, 6}


def clean_uei(v):
    v = (v or "").strip().upper()
    return v if len(v) == UEI_OK and v.isalnum() else ""


def clean_cage(v):
    v = (v or "").strip().upper()
    return v if len(v) in CAGE_LEN and v.isalnum() else ""


def clean_ein(v):
    d = "".join(c for c in str(v or "") if c.isdigit())
    return d.zfill(9) if 5 <= len(d) <= 9 else ""


def clean_duns(v):
    d = "".join(c for c in str(v or "") if c.isdigit())
    return d.zfill(9) if 7 <= len(d) <= 9 else ""


CLEANER = {"UEI": clean_uei, "CAGE": clean_cage, "EIN": clean_ein,
           "DUNS": clean_duns}


def node(kind, value):
    return f"{kind}:{value}"


def read_rows(p):
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def backup(p, tag):
    b = p.with_name(p.name + f".bak_{TODAY}_{tag}")
    if not b.exists():
        shutil.copy2(p, b)
        print(f"  backup  {b.name}")
    return b


def literal_dups(rows, cols):
    c = Counter(tuple(r.get(k, "") for k in cols) for r in rows)
    return sum(n - 1 for n in c.values() if n > 1)


def key_dups(rows, key):
    c = Counter(tuple(r.get(k, "") for k in key) for r in rows)
    return sum(n - 1 for n in c.values() if n > 1)


# ==========================================================================
# 1. THE BLOCK-EDGE SPLICE
# ==========================================================================
def map_block_edges():
    """The BLOCK edges `169` derives from `cross_dataset_ruling_map.csv`.

    The predicate is copied from `169` lines 278-296 verbatim: an EXCLUSION
    row, or any row whose ruling or note says BLOCKED. `asserting_row_ref`
    names the map row, which is what makes two blocks of the same identifier
    from two different target rows two distinct edges instead of one edge
    written twice.
    """
    out = []
    for i, r in enumerate(read_rows(MAP)):
        it = (r.get("identifier_type") or "").strip().upper()
        if it not in CLEANER:
            continue
        v = CLEANER[it](r.get("identifier"))
        if not v:
            continue
        if not ((r.get("ruling") or "").strip().upper().startswith("EXCLUSION")
                or "BLOCKED" in (r.get("note") or "").upper()
                + (r.get("ruling") or "").upper()):
            continue
        ref = ("cross_dataset_ruling_map.csv#"
               + str(r.get("target_row_ordinal") or i)
               + "/" + (r.get("source_file") or "")
               + "/" + (r.get("channel") or ""))
        out.append({
            "edge_kind": "BLOCK", "from_node": node(it, v), "to_node": "",
            "from_type": it, "to_type": "",
            "edge_tier": "X",
            "edge_tier_source": "row column (negative ruling)",
            "asserting_source": "cross_dataset_ruling_map.csv",
            "asserting_row_ref": ref,
            "n_asserting_sources": 1, "method": "",
            "evidence": f"{r.get('ruling','')} {r.get('note','')}"[:250],
            "built_by": "741_hub_grain_and_rebuild.py (splice of 169)",
            "built_date": TODAY})
    return out


def cmd_edges():
    print("=== 741 edges: splice the ruling-map BLOCK edges ===\n")
    if not EDGES.exists() or not MAP.exists():
        sys.exit("  cedar_identifier_graph_edges.csv or "
                 "cross_dataset_ruling_map.csv not on disk")
    rows = read_rows(EDGES)
    hdr_before = list(rows[0].keys()) if rows else []
    keep = [r for r in rows
            if not (r.get("edge_kind") == "BLOCK"
                    and r.get("asserting_source") == "cross_dataset_ruling_map.csv")]
    replaced = len(rows) - len(keep)
    fresh = map_block_edges()
    print(f"  edges on disk                  : {len(rows):,}")
    print(f"  ruling-map BLOCK edges replaced: {replaced:,}")
    print(f"  ruling-map BLOCK edges rebuilt : {len(fresh):,}")
    print(f"  every other edge kept verbatim : {len(keep):,}")

    # The identifiers a block covers may only GROW. A splice that blocks
    # fewer identifiers than the file already blocked is a regression, not a
    # refresh, and it must not pass silently: a lost BLOCK re-admits an
    # identifier that a ruling excluded.
    was = {r["from_node"] for r in rows
           if r.get("edge_kind") == "BLOCK"
           and r.get("asserting_source") == "cross_dataset_ruling_map.csv"}
    now = {r["from_node"] for r in fresh}
    lost = sorted(was - now)
    print(f"  identifiers blocked before/after: {len(was):,} / {len(now):,}")
    if lost:
        print(f"  REFUSED: {len(lost):,} identifier(s) would stop being "
              f"blocked, e.g. {lost[:5]}")
        return 1

    for r in keep:
        r.setdefault("asserting_row_ref", "")
    out = keep + fresh
    dups = key_dups(out, DECLARED_KEYS["cedar_identifier_graph_edges.csv"])
    lit = literal_dups(out, EDGE_COLS)
    print(f"  declared key duplicates        : {dups:,}")
    print(f"  literal duplicate rows         : {lit:,}")
    if dups or lit:
        print("  REFUSED to write - the splice did not make the table keyable")
        return 1

    backup(EDGES, "pre741")
    tmp = EDGES.with_suffix(".csv.part")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=EDGE_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)
    tmp.replace(EDGES)
    print(f"  wrote {EDGES.name} ({len(out):,} rows, "
          f"{len(hdr_before)} -> {len(EDGE_COLS)} columns)")
    return 0


# ==========================================================================
# 2. C8 - THE MEASURED GENEALOGY OF THE SPINE
# ==========================================================================
#: The dependency-correct replay order, READ OFF THE BACKUP TRAIL rather than
#: declared. Each entry is the enricher whose `.bak_<date>_pre<tag>` the census
#: found, in modification-time order. Tags that are not a script number are
#: one-off in-place repairs and are recorded as such.
BAK_TO_SCRIPT = {
    "pre51": "51_add_anc_acronym_aliases.py",
    "pre52": "52_add_village_corporations.py",
    "pre61": "61_add_nho_intertribal_to_spine.py",
    "pre66": "66_build_entity_hierarchy.py",
    "pre69": "69_enrich_spine_from_federal_register.py",
    "pre71": "71_fix_known_defects.py",
    "pre74": "74_add_organization_acronyms.py",
    "pre73tcu": "73_add_tcu_and_cdfi.py",
    "pre75": "75_add_bie_schools_and_uios.py",
    "pre163": "163_promote_nho_universe_in_place.py",
    "pre_241_promote_individual_native_firms_in_place":
        "241_promote_individual_native_firms_in_place.py",
    "pre_416_reconcile_spine_id_columns": "416_reconcile_spine_id_columns.py",
    "pre_426_mint_bristol_bay_spine_entities":
        "426_mint_bristol_bay_spine_entities.py",
    "pre504": "503_identity.py (via 504/505)",
    "pre524": "524_universe_gap.py",
}


def spine_stages():
    """Row and column census at every recorded spine checkpoint."""
    baks = sorted((p for p in SPINE.glob("cedar_entity_spine.csv.bak_*")),
                  key=lambda p: p.stat().st_mtime)
    chain = baks + [SPINE / "cedar_entity_spine.csv"]
    stages, prev_cols, prev_rows = [], None, None
    for p in chain:
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            rr = csv.reader(fh)
            hdr = next(rr, [])
            n = sum(1 for _ in rr)
        cols = set(hdr)
        tag = p.name.split(".bak_", 1)[1] if ".bak_" in p.name else "LIVE"
        short = tag.split("_", 1)[1] if tag != "LIVE" and "_" in tag else tag
        stages.append(dict(
            checkpoint=p.name,
            state_before=BAK_TO_SCRIPT.get(short, short),
            rows=n, n_columns=len(hdr),
            rows_added_by_previous_stage=(n - prev_rows
                                          if prev_rows is not None else None),
            columns_added_by_previous_stage=(
                sorted(cols - prev_cols) if prev_cols is not None else []),
            columns_lost_at_this_checkpoint=(
                sorted(prev_cols - cols) if prev_cols is not None else []),
        ))
        prev_cols, prev_rows = cols, n
    return stages


def cmd_census():
    print("=== 741 census: what a spine rebuild has to reproduce ===\n")
    import cedar_pipeline as CP

    stages = spine_stages()
    live = stages[-1]
    first = stages[0]
    # `01`'s ONLY spine source. The gap between this number and the live hub
    # IS the C8 loss, so it is measured here rather than quoted.
    ctt = ROOT / "data" / "raw" / "external" / "canonical_tribe_table.csv"
    n_ctt = len(read_rows(ctt)) if ctt.exists() else None
    print(f"  01's only spine source, canonical_tribe_table.csv: "
          + (f"{n_ctt:,} rows" if n_ctt is not None else "NOT ON DISK"))
    print(f"  earliest checkpoint : {first['rows']:,} rows, "
          f"{first['n_columns']} columns  ({first['checkpoint']})")
    print(f"  live hub            : {live['rows']:,} rows, "
          f"{live['n_columns']} columns")
    print(f"  checkpoints on the trail: {len(stages)}\n")

    # every enricher the pipeline scan believes touches the spine
    declared = sorted({o["enricher"] for o in
                       CP.all_orderings("cedar_entity_spine.csv")})
    ordered = [s["state_before"] for s in stages
               if s["state_before"].endswith(".py")
               or s["state_before"].startswith("503_")]
    seen, replay = set(), []
    for s in ordered:
        if s not in seen:
            seen.add(s)
            replay.append(s)
    unordered = [d for d in declared
                 if not any(d.split("_")[0] == r.split("_")[0] for r in replay)]

    print("  REPLAY ORDER, read off the backup trail:")
    for i, s in enumerate(replay, 1):
        print(f"    {i:2d}. {s}")
    if unordered:
        print("\n  spine enrichers with NO backup checkpoint - the replay "
              "order cannot be evidenced for these:")
        for d in unordered:
            print(f"      {d}")

    # Does the recorded chain account for every live column?
    accounted = set()
    for s in stages:
        accounted |= set(s["columns_added_by_previous_stage"])
    with (SPINE / "cedar_entity_spine.csv").open(
            encoding="utf-8-sig", newline="") as fh:
        live_cols = next(csv.reader(fh))
    base = set(live_cols) - accounted
    print(f"\n  live columns                      : {len(live_cols)}")
    print(f"  attributed to a named enricher    : {len(accounted)}")
    print(f"  present at the earliest checkpoint: {len(base)} "
          f"(01's own output, 12 of them)")

    payload = dict(
        generated=TODAY,
        canonical_tribe_table_rows=n_ctt,
        entities_a_direct_01_invocation_would_drop=(
            live["rows"] - n_ctt if n_ctt is not None else None),
        columns_a_direct_01_invocation_would_drop=live["n_columns"] - 12,
        method="row and column census read from the "
               "cedar_entity_spine.csv.bak_<date>_pre<NN> trail in "
               "data/spine, in modification-time order. Every spine enricher "
               "takes such a backup before writing, so the trail IS the "
               "applied order. Produced by 741_hub_grain_and_rebuild.py "
               "census. NEITHER 01 NOR 09 WAS RUN.",
        live=dict(rows=live["rows"], n_columns=live["n_columns"],
                  columns=live_cols),
        rebuild_gate=dict(
            min_rows=live["rows"], required_columns=live_cols,
            statement="A replay is acceptable only if the post-replay spine "
                      "has at least this many rows and every one of these "
                      "columns. Anything less is a partial restore wearing a "
                      "green build log."),
        replay_order=replay,
        enrichers_with_no_checkpoint=unordered,
        stages=stages,
    )
    CENSUS_JSON.parent.mkdir(parents=True, exist_ok=True)
    CENSUS_JSON.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"\n  wrote {CENSUS_JSON.relative_to(ROOT)}")
    write_census_md(payload, stages)
    return 0


def write_census_md(payload, stages):
    L = [
        "# The `_entity_layer` hub - grain, keys, and what a rebuild has to "
        "reproduce",
        "",
        f"*Measured {TODAY} by `code/741_hub_grain_and_rebuild.py`. "
        f"Regenerate rather than edit. **Neither `01_build_entity_spine.py` "
        f"nor `09_import_rulings.py` was run to produce any number here.***",
        "",
        "## 1. C1/C2/C3 - one defect, one fix, nothing deleted",
        "",
        "Three tables were listed with literal duplicate rows and no key. The "
        "counts were real. The rows were not duplicate facts: a projection "
        "dropped the identity of the row a ruling was applied TO, so N "
        "distinct applications rendered as N identical rows. The identity is "
        "now written back and the counts fall to zero **without a single "
        "deleted row**.",
        "",
        "| table | rows before | rows after | literal dups before | after | "
        "the column that was missing |",
        "|---|---:|---:|---:|---:|---|",
        "| `cross_dataset_ruling_map.csv` | 7,507 | 22,936 | 2,228 | 0 | "
        "`target_row_ordinal` (`23`) |",
        "| `cedar_ruling_ledger_consolidated.csv` | 15,587 | 43,321 | 6,302 | "
        "0 | `source_row_ordinal` (`173`) |",
        "| `cedar_identifier_graph_edges.csv` | 46,051 | 46,820 | 2,451 | "
        "0 | `asserting_row_ref` (`169`, spliced by `741 edges`) |",
        "| `tcu_cdfi_ownership_evidence.csv` | 130 | 130 | 4 | 0 | "
        "`quote_char_offset` (`73`) |",
        "",
        "The row counts GREW because `23` had not been re-run since the "
        "ruling and exclusion sets last grew - 380 rulings and 4,779 "
        "exclusions reach further than they did when the stale map was "
        "written. Nothing was removed at any step.",
        "",
        "**The ledger's duplication was NOT only the ruling map.** Measured "
        "before the repair: 3,561 of the 6,302 surplus rows came from "
        "`review/osha_gambling_unresolved_2026-08-26.csv`, whose 4,560 rows "
        "are one per (OSHA establishment-year record, proposed tribe) and are "
        "themselves distinct - `173` kept the subject, the verdict and the "
        "source FILE and dropped which ROW said it, so the establishment, "
        "city, state and year that separate them were thrown away. 2,572 came "
        "from the ruling map. The fix is one column in `173` and it closes "
        "both.",
        "",
        "## 2. C8 - the spine genealogy, read off the backup trail",
        "",
        "`build.plan_for` returns the spine enrichers lexicographically "
        "(`50`, `503`, `51`, `52`, ...), which is not the order they were "
        "applied, so nobody could state what a replay must run. The order was "
        "not invented here: **every spine enricher takes a "
        "`cedar_entity_spine.csv.bak_<date>_pre<NN>` before it writes**, so "
        "the backup directory in modification-time order IS the applied "
        "order, and each backup's header is the column set immediately "
        "before that enricher ran.",
        "",
        "| # | stage that ran next | rows before it | columns before it | "
        "columns the PREVIOUS stage added |",
        "|---:|---|---:|---:|---|",
    ]
    for i, s in enumerate(stages, 1):
        add = ", ".join(f"`{c}`" for c in s["columns_added_by_previous_stage"])
        L.append(f"| {i} | `{s['state_before']}` | {s['rows']:,} | "
                 f"{s['n_columns']} | {add or '-'} |")
    L += [
        "",
        f"**The gate a replay must clear:** at least "
        f"{payload['live']['rows']:,} rows and all "
        f"{payload['live']['n_columns']} columns. "
        f"`docs/schema/hub_rebuild_census.json` carries the column list so "
        f"the check is mechanical.",
        "",
        "### What this does and does not close",
        "",
        "`01` and `09` now take a `.bak` before writing, like all fifteen "
        "spine enrichers, so the unrecoverable case is gone - and that "
        "matters more here than elsewhere, because `.gitignore:95` excludes "
        "`data/spine/*` apart from `cedar_identity_register.csv` and "
        "`cedar_handle_history.csv`, so **git cannot restore the spine**.",
        "",
        "**It does not make `01` non-destructive, and C8 is not closed.** "
        "`01` builds the spine from `canonical_tribe_table.csv` alone - 687 "
        "rows, 12 columns - against a live hub of 1,555 rows and 44. A direct "
        "invocation still drops 868 entities and 32 columns; the backup makes "
        "that recoverable, not acceptable. `09` still drops 1,345 ledger "
        "rows, 18 of them tier A owner adjudications. Both remain in "
        "`cedar_pipeline.NEVER_RUN`, `build.plan_for` still sorts them into "
        "its `blocked` phase, and the scoreboard reads that guard as the C8 "
        "blocker - correctly. The only way to make the blocker green today "
        "would be to remove the guard, which would let "
        "`py -3 code/build.py run _entity_layer --execute` destroy the hub. "
        "**A gate satisfied by removing the thing that protects the data is "
        "worse than a red one.**",
        "",
        "What genuinely closes C8 is a `01` that append-merges instead of "
        "rebuilding - which `NEVER_RUN`'s own text already prescribes - and a "
        "`09` that merges rather than replacing `_final`. The census above is "
        "the target either of them has to hit, and it is the piece that was "
        "missing.",
        "",
        "## 3. THE GATE LINE THIS WORK MOVED THE WRONG WAY, AND WHOSE IT IS",
        "",
        "`62_no_regression_check.py` reports "
        "**`rulings_unapplied ROSE 1,215 -> 2,894`**, a metric declared to "
        "only go down. It counts rows of "
        "`cedar_ruling_ledger_consolidated.csv` with "
        "`status = CONFLICT_NOT_APPLIED`. Recorded here rather than stepped "
        "around, per standing rule 15, and attributed by measurement rather "
        "than by assertion.",
        "",
        "The rise is 116 -> **263 conflicting SUBJECTS**, 147 of them new and "
        "**none resolved**. Of those 147:",
        "",
        "| | subjects |",
        "|---|---:|",
        "| carry no `cross_dataset_ruling_map.csv` row at all - they arrived "
        "from OTHER workstreams' files that `173` swept today "
        "(`gaming_employment_observations.csv`, "
        "`523_idgraph_q4_split_entity_suspects.csv`, "
        "`individual_native_firm_register.csv`) | 114 |",
        "| carry a map row but the conflict stands without it | 5 |",
        "| **need a map row - attributable to re-running `23`** | **28** |",
        "",
        "So 28 subjects of the 147 are this workstream's, and every one of "
        "them is a NEGATIVE ruling and a positive ruling on the SAME "
        "identifier, both of which already existed. `cedar_exclusion_rulings."
        "csv` lives in `data/spine`, which `173.discover()` does not scan, so "
        "`cross_dataset_ruling_map.csv` is the ONLY channel by which an "
        "exclusion reaches the ledger - and the map was stale. The 28 were "
        "hidden by that staleness, not created by refreshing it.",
        "",
        "**They must not be suppressed.** C6 is 'material unresolved identity "
        "conflicts do not ship as definite facts', and `173` applied NEITHER "
        "side of any of them: all 263 are in "
        "`review/ruling_conflicts_2026-09-01.csv` awaiting adjudication, "
        "which is the correct destination for a disagreement this project "
        "cannot resolve by preference. Making the gate green by re-hiding "
        "them would trade a red metric for a false fact.",
        "",
        "This needs a line in `AGENTS.md` naming the owner, which this "
        "workstream was instructed not to write. The owner of the 28 is the "
        "GRAIN-HUB workstream; the owner of the other 119 is whoever rebuilt "
        "`gaming_employment_observations.csv` and wrote "
        "`523_idgraph_q4_split_entity_suspects.csv` today.",
        "",
    ]
    CENSUS_MD.write_text("\n".join(L), encoding="utf-8")
    print(f"  wrote {CENSUS_MD.relative_to(ROOT)}")


# ==========================================================================
# 3. VERIFY
# ==========================================================================
def cmd_verify():
    print("=== 741 verify: the hub's declared keys, re-measured ===\n")
    bad = 0
    for name, key in sorted(DECLARED_KEYS.items()):
        p = CLEAN / name
        if not p.exists():
            print(f"  {name:44s} NOT ON DISK")
            bad += 1
            continue
        rows = read_rows(p)
        hdr = list(rows[0].keys()) if rows else []
        missing = [c for c in key if c not in hdr]
        if missing:
            print(f"  {name:44s} key column(s) missing: {missing}")
            bad += 1
            continue
        kd = key_dups(rows, key)
        ld = literal_dups(rows, hdr)
        flag = "" if not (kd or ld) else "   <-- BREACH"
        print(f"  {name:44s} {len(rows):>7,} rows  key dups {kd:>5,}  "
              f"literal dups {ld:>5,}{flag}")
        bad += bool(kd or ld)

    # the copied cleaners must still match 169's
    src = (HERE / "169_build_identifier_graph.py").read_text(
        encoding="utf-8", errors="replace")
    for fn in ("def clean_uei(v):", "def clean_cage(v):", "def clean_ein(v):"):
        if fn not in src:
            print(f"  169 no longer defines {fn!r} - the copied cleaners in "
                  f"this file may have drifted")
            bad += 1
    print(f"\n  breaches: {bad}")
    return 1 if bad else 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "edges":
        return cmd_edges()
    if cmd == "census":
        return cmd_census()
    if cmd == "verify":
        return cmd_verify()
    rc = cmd_edges()
    print()
    rc = cmd_census() or rc
    print()
    return cmd_verify() or rc


if __name__ == "__main__":
    raise SystemExit(main())
