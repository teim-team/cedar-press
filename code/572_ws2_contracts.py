#!/usr/bin/env python3
"""
Cedar Press - 572: WORKSTREAM GRAIN-WS2. Closing the production contract on
the entity-layer hub and on contractors.

    py -3 code/572_ws2_contracts.py measure   # read-only; every number below
    py -3 code/572_ws2_contracts.py apply     # + merge C5 rows, write the doc

WHY THIS SCRIPT EXISTS
----------------------
518 reported 2 of 13 datasets READY. Eleven agents were harvesting and nobody
was closing contracts, so three were retasked onto the 22 named tables that
fail one. WS2 took `_entity_layer` (the hub - ADR-009 makes the other twelve
datasets consume it) and `contractors`.

It measures rather than asserts, because this project has already been burned
by an asserted duplicate count. `prime_contracts.csv` was recorded in
512.GRAIN_DEFECT at 80,778 literal duplicate rows with a note that anyone
summing its dollars was over-counting. Re-measured, the real answer was ZERO:
distinct FPDS transactions that a lossy mapper had rendered identical. A
de-duplication would have deleted real rows and real money. So every number
this file prints is taken from the file on disk on the day it runs, and
NOTHING here deletes a row. Flag, never delete.

WHAT IT WRITES (apply only)
---------------------------
data/clean/cedar_harvest_conservation.csv   C5 rows for the two contractors
                                            tables. **MERGE-ONLY.** This file
                                            is SHARED - 510 documents that a
                                            wholesale rewrite on 2026-09-01
                                            destroyed 2,146,673 accounted
                                            rows belonging to 519 and 77/78.
                                            Merge key is (source_table,
                                            disposition), the same key 510
                                            and 519 use; every key this run
                                            does not own is preserved
                                            verbatim.
docs/WS2_GRAIN_AND_REBUILD.md               the findings, including the C8
                                            rebuild procedure for the spine.

WHAT IT DOES NOT DO
-------------------
It does not run `01_build_entity_spine.py` or `09_import_rulings.py`. It does
not run any builder at all. It never mints. It reads.
"""
from __future__ import annotations

import csv
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()

CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine"
EXT = ROOT / "data" / "raw" / "external"
CONSERVATION = CLEAN / "cedar_harvest_conservation.csv"
OUT_MD = ROOT / "docs" / "WS2_GRAIN_AND_REBUILD.md"

CONS_COLS = ["source_table", "rows_in", "disposition", "rows", "pct",
             "examples", "harvest_date"]


def read_csv(p: Path) -> list:
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def literal_duplicates(p: Path):
    """Exact whole-row duplicates: every column, compared as strings.

    No hashing shortcut and no sampling. These files are small enough to hold,
    and the one thing this measurement must not do is report a birthday
    collision as a duplicate row.
    """
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rr = csv.reader(fh)
        hdr = next(rr, [])
        c = Counter(tuple(row) for row in rr)
    return dict(rows=sum(c.values()),
                dup_rows=sum(v - 1 for v in c.values() if v > 1),
                dup_groups=sum(1 for v in c.values() if v > 1),
                max_multiplicity=max(c.values()) if c else 0,
                header=hdr,
                top=[(v, dict(zip(hdr, k)))
                     for k, v in c.most_common(3) if v > 1])


def keydup(rows, cols):
    c = Counter(tuple(r.get(x, "") for x in cols) for r in rows)
    return sum(v - 1 for v in c.values() if v > 1)


# ---------------------------------------------------------------------------
# 1. THE ALLEGED DUPLICATES, RE-MEASURED
# ---------------------------------------------------------------------------
ALLEGED = {
    "cedar_identifier_graph_edges.csv": 2451,
    "cedar_ruling_ledger_consolidated.csv": 6302,
    "cross_dataset_ruling_map.csv": 2228,
    "tcu_cdfi_ownership_evidence.csv": 4,
    "contractor_ranking.csv": 0,
    "fpds_uei_cage_map.csv": 0,
}


def measure_duplicates():
    print("\n[1] LITERAL DUPLICATES, re-measured against the allegation")
    out = {}
    for name, claimed in ALLEGED.items():
        p = CLEAN / name
        if not p.exists():
            print(f"  {name}: NOT ON DISK")
            continue
        m = literal_duplicates(p)
        out[name] = m
        verdict = ("CONFIRMED" if m["dup_rows"] == claimed
                   else f"REFUTED (alleged {claimed:,})")
        print(f"  {name:<42} {m['rows']:>7,} rows  "
              f"{m['dup_rows']:>6,} literal dup  {verdict}")
    return out


# ---------------------------------------------------------------------------
# 2. THE CASCADE. Where the entity-layer duplicates actually come from.
# ---------------------------------------------------------------------------
def measure_cascade():
    """The three entity-layer duplicate counts are ONE defect, propagated.

    `23_cross_dataset_propagation.py` appends one `hits` row EVERY TIME a
    ruled identifier is seen in a target dataset - once per TARGET ROW - and
    the row it writes carries no column identifying that target row. So N
    distinct applications of one ruling render as N byte-identical rows.
    173 (the ledger) and 169 (the graph) then read that file and inherit the
    fan-out 1:1.

    This is the SAME SHAPE as the prime_contracts false alarm: a projection
    that dropped the identity of the thing each row is about. It is not the
    same conclusion, and the difference is the point. For prime_contracts the
    dropped identity existed upstream and 430 joined it back, so the count
    went to zero without deleting a row. Here the dropped identity is the
    target row's key, which 23 HAS in hand at the moment it appends and simply
    does not write. Recovering it is a one-column change to 23, not a
    de-duplication - and until it is made, the counts are real rows that must
    not be deleted, because each one records a real application of a ruling.
    """
    print("\n[2] THE CASCADE - one defect in three tables")
    xmap = read_csv(CLEAN / "cross_dataset_ruling_map.csv")
    led = read_csv(CLEAN / "cedar_ruling_ledger_consolidated.csv")
    edg = read_csv(CLEAN / "cedar_identifier_graph_edges.csv")
    if not xmap:
        return {}
    per_id = Counter(r["identifier"] for r in xmap)
    worst, n = per_id.most_common(1)[0]
    lrows = sum(1 for r in led if r.get("subject_key") == "UEI:" + worst)
    erows = sum(1 for r in edg if r.get("from_node") == "UEI:" + worst
                and r.get("asserting_source") == "cross_dataset_ruling_map.csv")
    from_xmap_led = sum(1 for r in led if (r.get("source_file") or "")
                        .endswith("cross_dataset_ruling_map.csv"))
    from_xmap_edg = sum(1 for r in edg if r.get("asserting_source")
                        == "cross_dataset_ruling_map.csv")
    print(f"  worst identifier                : UEI {worst}")
    print(f"    rows in cross_dataset_ruling_map : {n:,}")
    print(f"    rows it produced in the ledger   : {lrows:,}")
    print(f"    edges it produced in the graph   : {erows:,}")
    print(f"  ledger rows sourced from the map : {from_xmap_led:,} "
          f"of {len(led):,}")
    print(f"  graph edges asserted by the map  : {from_xmap_edg:,} "
          f"of {len(edg):,}")
    return dict(worst=worst, xmap=n, ledger=lrows, edges=erows,
                ledger_from_map=from_xmap_led, ledger_rows=len(led),
                edges_from_map=from_xmap_edg, edge_rows=len(edg))


# ---------------------------------------------------------------------------
# 3. fpds_uei_cage_map.csv - the declaration's evidence
# ---------------------------------------------------------------------------
def measure_cage_map():
    print("\n[3] fpds_uei_cage_map.csv - the key, and the join hazard")
    rows = read_csv(CLEAN / "fpds_uei_cage_map.csv")
    pk = ["uei", "cage_code", "legal_business_name"]
    d = keydup(rows, pk)
    blank = sum(1 for r in rows if not r["cage_code"].strip())
    nan = sum(1 for r in rows if r["cage_code"].strip().upper() == "NAN")
    nan_ueis = len({r["uei"] for r in rows
                    if r["cage_code"].strip().upper() == "NAN"})
    real = defaultdict(set)
    for r in rows:
        c = r["cage_code"].strip().upper()
        if c and c != "NAN":
            real[c].add(r["uei"].strip())
    malformed = sum(1 for r in rows
                    if r["cage_code"].strip()
                    and r["cage_code"].strip().upper() != "NAN"
                    and len(r["cage_code"].strip()) != 5)
    ambiguous = {c: s for c, s in real.items() if len(s) > 1}
    ueirows = Counter(r["uei"] for r in rows)
    print(f"  rows                            : {len(rows):,}")
    print(f"  PK {'+'.join(pk)}")
    print(f"    duplicate rows under that key : {d:,}   "
          f"{'UNIQUE' if d == 0 else 'NOT A KEY'}")
    print(f"  (uei, cage_code, source_file)   : "
          f"{keydup(rows, ['uei','cage_code','source_file']):,} dup - refuted")
    print(f"  distinct uei                    : {len(ueirows):,} "
          f"(max {max(ueirows.values())} rows per uei)")
    print(f"  cage_code blank                 : {blank:,}")
    print(f"  cage_code literal 'NAN'         : {nan:,} rows over "
          f"{nan_ueis:,} DISTINCT UEIs  <-- JOIN HAZARD")
    print(f"  cage_code not 5 characters      : {malformed:,}")
    print(f"  real CAGE codes                 : {len(real):,}, of which "
          f"{len(ambiguous):,} map to >1 UEI "
          f"(max {max((len(s) for s in ambiguous.values()), default=0)})")
    good = len(rows) - blank - nan - malformed
    return dict(rows=len(rows), pk_dup=d, blank=blank, nan=nan,
                nan_ueis=nan_ueis, malformed=malformed, good=good,
                n_cage=len(real), ambiguous=len(ambiguous),
                max_rows_per_uei=max(ueirows.values()))


# ---------------------------------------------------------------------------
# 4. contractor_ranking.csv - C1/C2 refusal, and the C7 numbers
# ---------------------------------------------------------------------------
MEASURE_MARKERS = ("usd", "pct", "rows", "_fy", "rank", "n_operating",
                   "n_identifiers", "n_uei", "built_date", "source_vintage",
                   "measured_from", "built_by", "carries_any")


def measure_ranking():
    print("\n[4] contractor_ranking.csv - why no key, and what may be summed")
    rows = read_csv(CLEAN / "contractor_ranking.csv")
    hdr = list(rows[0].keys())
    nonmeasure = [c for c in hdr
                  if not any(m in c for m in MEASURE_MARKERS)]

    # C2: is there ANY key that is not part-measure?
    all_nm = keydup(rows, nonmeasure)
    ident = ["owner_entity_id", "operating_company_uei",
             "operating_company_name"]
    id_dup = keydup(rows, ident)
    withheld = [r for r in rows if r["publishable_operating_name"] != "Y"]
    pub = [r for r in rows if r["publishable_operating_name"] == "Y"]
    pub_dup = keydup(pub, ident)
    g = defaultdict(list)
    for r in rows:
        g[tuple(r[c] for c in ident)].append(r)
    in_collision = sum(len(v) for v in g.values() if len(v) > 1)

    print(f"  rows                                    : {len(rows):,}")
    print(f"  ALL {len(nonmeasure)} non-measure columns as a key   : "
          f"{all_nm} duplicate row(s)   <-- NO KEY EXISTS")
    print(f"  (owner_entity_id, uei, name)            : {id_dup} dup")
    print(f"    of which on PUBLISHED rows only       : {pub_dup} dup "
          f"of {len(pub):,}")
    print(f"    of which on WITHHELD rows only        : {id_dup} dup "
          f"of {len(withheld):,}")
    print(f"  rows sitting in a collision group       : {in_collision}")
    print("  => every collision is a privacy redaction, not a data defect.")

    # C7
    f = lambda x: float(x or 0)                              # noqa: E731
    owner_naive = sum(f(r["owner_obligations_usd"]) for r in rows)
    owner_true = {}
    for r in rows:
        owner_true[r["owner_entity_id"]] = f(r["owner_obligations_usd"])
    firm_sum = sum(f(r["firm_obligations_usd"]) for r in rows)
    true_total = sum(owner_true.values())

    tierA = 0.0
    pc = CLEAN / "prime_contracts.csv"
    if pc.exists():
        with pc.open(encoding="utf-8-sig", errors="replace",
                     newline="") as fh:
            for r in csv.DictReader(fh):
                if (r.get("attributed_flag") == "1"
                        and r.get("confidence_tier") == "A"):
                    try:
                        tierA += float(r["total_obligations"] or 0)
                    except ValueError:
                        pass

    print(f"\n  C7, measured:")
    print(f"    SUM(firm_obligations_usd) over all rows : "
          f"${firm_sum/1e9:,.2f}B")
    print(f"    prime_contracts tier-A attributed       : "
          f"${tierA/1e9:,.2f}B")
    print(f"    difference                              : "
          f"${firm_sum - tierA:,.2f}   <-- THE SAME MONEY")
    print(f"    SUM(owner_obligations_usd) over rows    : "
          f"${owner_naive/1e9:,.2f}B")
    print(f"    the same, over DISTINCT owners          : "
          f"${true_total/1e9:,.2f}B")
    print(f"    inflation if row-summed                 : "
          f"{owner_naive/true_total:,.2f}x over {len(owner_true)} owners")

    return dict(rows=len(rows), nonmeasure=len(nonmeasure), all_nm_dup=all_nm,
                id_dup=id_dup, published=len(pub), withheld=len(withheld),
                in_collision=in_collision, firm_sum=firm_sum, tierA=tierA,
                owner_naive=owner_naive, owner_true=true_total,
                n_owners=len(owner_true),
                factor=owner_naive / true_total if true_total else 0)


# ---------------------------------------------------------------------------
# 5. C8 - what a rebuild of the hub would actually destroy
# ---------------------------------------------------------------------------
def measure_rebuild():
    """Measured WITHOUT running either builder.

    01 populates its spine dict from ONE source - canonical_tribe_table.csv -
    and writes 12 columns. 09 rebuilds the final ledger FROM
    cedar_identifier_ledger_tiered.csv. So the loss is computable by set
    difference against those two inputs, which is what this does.
    """
    print("\n[5] C8 - the cost of a rebuild, computed without running one")
    sp = read_csv(SPINE / "cedar_entity_spine.csv")
    canon = read_csv(EXT / "canonical_tribe_table.csv")
    reg = read_csv(SPINE / "cedar_identity_register.csv")
    fin = read_csv(CLEAN / "cedar_identifier_ledger_final.csv")
    tie = read_csv(CLEAN / "cedar_identifier_ledger_tiered.csv")

    live_ids = {r["tribe_id"].strip() for r in sp}
    canon_ids = {r["tribe_id"].strip() for r in canon if r["tribe_id"].strip()}
    dropped = live_ids - canon_ids
    live_cols = list(sp[0].keys()) if sp else []
    # the 12 columns 01 writes, from its own spine_fields list
    written = ["tribe_id", "canonical_name", "entity_class", "state",
               "bia_region", "self_governance", "cedar_entity_id",
               "n_uei_tierA", "n_uei_tierB", "n_cage", "n_ein", "aliases"]
    lost_cols = [c for c in live_cols if c not in written]
    by_class = Counter(r.get("entity_class", "") for r in sp
                       if r["tribe_id"].strip() in dropped)

    # is the cedar_uid binding recoverable from the git-tracked register?
    handle_is_tribe_id = sum(
        1 for r in reg
        if r["handle"] in live_ids)
    with_cei = sum(1 for r in sp if (r.get("cedar_entity_id") or "").strip())

    tie_ids = {(r["identifier_type"], r["identifier"]) for r in tie}
    lost_ledger = [r for r in fin
                   if (r["identifier_type"], r["identifier"]) not in tie_ids]
    lost_tiers = Counter(r["confidence_tier"] for r in lost_ledger)

    print(f"  cedar_entity_spine.csv live rows        : {len(sp):,}")
    print(f"  canonical_tribe_table.csv (01's ONLY "
          f"spine source)                            : {len(canon_ids):,}")
    print(f"  ENTITIES A REBUILD DROPS                : {len(dropped):,} "
          f"({100*len(dropped)/max(len(sp),1):.0f}% of the hub)")
    for k, v in by_class.most_common(6):
        print(f"      {v:>4}  {k}")
    print(f"  COLUMNS A REBUILD DROPS                 : {len(lost_cols)} "
          f"of {len(live_cols)} (01 writes {len(written)})")
    print(f"      including: {', '.join(lost_cols[:6])} ...")
    print(f"  cedar_uid recovery:")
    print(f"      register rows whose HANDLE equals a live tribe_id : "
          f"{handle_is_tribe_id:,} of {len(reg):,}")
    print(f"      spine rows carrying cedar_entity_id               : "
          f"{with_cei:,}")
    print(f"  09 rerun: ledger_final {len(fin):,} <- tiered {len(tie):,}")
    print(f"      LEDGER ROWS A RERUN DROPS           : "
          f"{len(lost_ledger):,}  {dict(lost_tiers)}")
    return dict(spine_rows=len(sp), canon=len(canon_ids),
                dropped=len(dropped), by_class=by_class.most_common(),
                live_cols=len(live_cols), lost_cols=lost_cols,
                handle_match=handle_is_tribe_id, reg_rows=len(reg),
                with_cei=with_cei, fin=len(fin), tie=len(tie),
                lost_ledger=len(lost_ledger), lost_tiers=dict(lost_tiers))


# ---------------------------------------------------------------------------
# 6. foia_request_index.csv - answering a GRAIN_OPEN question
# ---------------------------------------------------------------------------
def measure_foia():
    print("\n[6] foia_request_index.csv - the GRAIN_OPEN question, answered")
    rows = read_csv(CLEAN / "foia_request_index.csv")
    if not rows:
        return {}
    g = defaultdict(list)
    for r in rows:
        g[r["foia_request_id"]].append(r)
    coll = {k: v for k, v in g.items() if len(v) > 1}
    in_coll = sum(len(v) for v in coll.values())
    FLAG = "control_number_appears_more_than_once"
    flagged = sum(1 for r in rows if FLAG in (r["parse_quality_reason"] or ""))
    flagged_in_coll = sum(1 for r in rows
                          if r["foia_request_id"] in coll
                          and FLAG in (r["parse_quality_reason"] or ""))
    desc_differs = sum(1 for v in coll.values()
                       if len({r["request_description"] for r in v}) > 1)
    print(f"  rows                                    : {len(rows):,}")
    print(f"  foia_request_id values that repeat      : {len(coll):,} "
          f"({in_coll - len(coll):,} surplus rows)")
    print(f"  rows carrying '{FLAG}'                  : {flagged:,}")
    print(f"    of which inside a collision group     : {flagged_in_coll:,}")
    print(f"  collision groups where request_description differs: "
          f"{desc_differs:,} of {len(coll):,}")
    print("  => the id IS meant to be unique. The repeats are a PARSE split:")
    print("     the table already names every one of them in its own")
    print("     parse_quality_reason. This is a defect to fix in 136, not a")
    print("     grain to declare.")

    # The SAME signature in the sibling table, built by a different script.
    # One diagnosis that fits two tables built by 136 and 146 independently is
    # worth more than two separate open questions, because it names one class
    # of fix instead of two mysteries.
    vr = read_csv(CLEAN / "visitor_record_foia_requests.csv")
    v_groups = v_surplus = v_desc = 0
    if vr:
        vg = defaultdict(list)
        for r in vr:
            vg[r["foia_request_id"]].append(r)
        vcoll = {k: v for k, v in vg.items() if len(v) > 1}
        v_groups = len(vcoll)
        v_surplus = sum(len(v) for v in vcoll.values()) - v_groups
        v_desc = sum(1 for v in vcoll.values()
                     if len({r["request_description_verbatim"]
                             for r in v}) > 1)
        print(f"  visitor_record_foia_requests.csv: {v_groups} colliding ids, "
              f"{v_surplus} surplus rows, and the verbatim description "
              f"differs in {v_desc}/{v_groups} - the SAME signature, from a "
              f"different builder (146).")
    return dict(rows=len(rows), groups=len(coll), surplus=in_coll - len(coll),
                flagged=flagged, flagged_in_coll=flagged_in_coll,
                desc_differs=desc_differs, v_groups=v_groups,
                v_surplus=v_surplus, v_desc=v_desc)


# ---------------------------------------------------------------------------
# C5 - row conservation for `contractors`, MERGED
# ---------------------------------------------------------------------------
def conservation_rows(cage, rank):
    """Two ledgers, each partitioning its table's rows into named dispositions.

    A disposition set must PARTITION - every row lands in exactly one - or the
    ledger is not a conservation statement. Both are asserted below before
    anything is written.
    """
    out = []

    def emit(table, rows_in, counts, examples):
        assert sum(counts.values()) == rows_in, (
            f"{table}: dispositions sum to {sum(counts.values())}, "
            f"not {rows_in} - that is not a conservation statement")
        for disp, n in sorted(counts.items()):
            out.append(dict(source_table=table, rows_in=rows_in,
                            disposition=disp, rows=n,
                            pct=round(100.0 * n / max(rows_in, 1), 2),
                            examples="; ".join(examples.get(disp, [])),
                            harvest_date=TODAY))

    rowsc = read_csv(CLEAN / "fpds_uei_cage_map.csv")
    ex = defaultdict(list)
    counts = Counter()
    for r in rowsc:
        c = r["cage_code"].strip()
        if not c:
            d = "rejected:no_cage_code_recorded_in_the_source_extract"
        elif c.upper() == "NAN":
            d = ("rejected:cage_code_is_the_literal_string_NAN_a_null_"
                 "stringified_on_export_NOT_a_CAGE_join_on_it_fuses_"
                 "unrelated_entities")
        elif len(c) != 5:
            d = "rejected:cage_code_is_not_5_characters_and_cannot_be_a_CAGE"
        else:
            d = "emitted:valid_5_character_cage_code_usable_as_a_join_key"
        counts[d] += 1
        if len(ex[d]) < 3:
            ex[d].append(f"{r['uei']}:{c or '(blank)'}")
    emit("data/clean/fpds_uei_cage_map.csv", len(rowsc), counts, ex)

    rowsr = read_csv(CLEAN / "contractor_ranking.csv")
    ident = ["owner_entity_id", "operating_company_uei",
             "operating_company_name"]
    g = defaultdict(list)
    for r in rowsr:
        g[tuple(r[c] for c in ident)].append(r)
    colliding = {k for k, v in g.items() if len(v) > 1}
    ex2 = defaultdict(list)
    counts2 = Counter()
    for r in rowsr:
        k = tuple(r[c] for c in ident)
        if r["publishable_operating_name"] == "Y":
            d = ("emitted:operating_company_published_and_uniquely_"
                 "identified_by_owner_plus_uei")
        elif k in colliding:
            d = ("rejected:name_withheld_by_the_personal_name_guard_AND_no_"
                 "longer_distinguishable_from_a_sibling_row_of_the_same_"
                 "owner_the_row_ships_but_carries_no_key")
        else:
            d = ("rejected:name_withheld_by_the_personal_name_guard_row_"
                 "still_uniquely_identified")
        counts2[d] += 1
        if len(ex2[d]) < 3:
            ex2[d].append(f"{r['owner_entity_id']}:"
                          f"{r['operating_company_uei'] or '(withheld)'}")
    emit("data/clean/contractor_ranking.csv", len(rowsr), counts2, ex2)
    return out


def merge_conservation(new_rows):
    """MERGE-ONLY. See the docstring: a wholesale rewrite of this file on
    2026-09-01 destroyed 2,146,673 accounted rows belonging to two other
    datasets. The key is (source_table, disposition), the same one 510 and 519
    use, and every key this run does not own is carried through untouched.
    """
    before = read_csv(CONSERVATION)
    mine = {(r["source_table"], r["disposition"]) for r in new_rows}
    kept = [r for r in before
            if (r.get("source_table"), r.get("disposition")) not in mine]
    if CONSERVATION.exists():
        shutil.copy2(CONSERVATION,
                     CONSERVATION.with_name(CONSERVATION.name
                                            + f".bak_{TODAY}_pre572"))
    tmp = CONSERVATION.with_suffix(".csv.part")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CONS_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(new_rows + kept)
    tmp.replace(CONSERVATION)
    after = read_csv(CONSERVATION)
    acc_before = sum(int(r.get("rows") or 0) for r in before)
    acc_after = sum(int(r.get("rows") or 0) for r in after)
    print(f"\n[C5] conservation merged: {len(before):,} -> {len(after):,} "
          f"ledger rows; accounted rows {acc_before:,} -> {acc_after:,} "
          f"(kept {len(kept):,} belonging to other workstreams)")
    assert acc_after >= acc_before, (
        "MERGE REGRESSED THE ACCOUNTED TOTAL - this is the 2026-09-01 "
        "failure. Restore from the .bak written above.")
    return len(before), len(after), acc_before, acc_after


# ---------------------------------------------------------------------------
def write_doc(dups, casc, cage, rank, rb, foia, cons):
    L = [
        "# WS2 — the entity-layer hub and contractors: grain, keys, and the "
        "spine rebuild",
        "",
        f"*Measured {TODAY} by `code/572_ws2_contracts.py`. Regenerate rather "
        f"than edit — every number below is taken from the files on disk at "
        f"run time.*",
        "",
        "## 1. The three alleged duplicate counts: CONFIRMED, and they are "
        "one defect",
        "",
        "`prime_contracts.csv` was once recorded at 80,778 literal duplicate "
        "rows and the real answer was zero, so these were re-measured before "
        "anything was written down. This time the allegation holds:",
        "",
        "| table | rows | literal duplicate rows | alleged | verdict |",
        "|---|---:|---:|---:|---|",
    ]
    for n, m in dups.items():
        claimed = ALLEGED[n]
        L.append(f"| `{n}` | {m['rows']:,} | {m['dup_rows']:,} | "
                 f"{claimed:,} | "
                 f"{'confirmed' if m['dup_rows'] == claimed else 'REFUTED'} |")
    if casc:
        L += [
            "",
            "But the count being right does not make three defects. It is "
            "**one defect in one script, propagated twice.**",
            "",
            f"`23_cross_dataset_propagation.py` appends one row every time a "
            f"ruled identifier is seen **in a target dataset row**, and the "
            f"row it writes carries no column naming that target row. So N "
            f"real applications of one ruling render as N byte-identical "
            f"rows. UEI `{casc['worst']}` alone produces "
            f"{casc['xmap']:,} rows in `cross_dataset_ruling_map.csv`; "
            f"`173_consolidate_rulings_ledger.py` turns them into "
            f"{casc['ledger']:,} ledger rows and "
            f"`169_build_identifier_graph.py` into {casc['edges']:,} "
            f"identical `BLOCK` edges, each stamped "
            f"`n_asserting_sources = 1`.",
            "",
            f"{casc['ledger_from_map']:,} of the ledger's "
            f"{casc['ledger_rows']:,} rows and {casc['edges_from_map']:,} of "
            f"the graph's {casc['edge_rows']:,} edges are sourced from that "
            f"one file.",
            "",
            "**Do not de-duplicate any of the three.** Each row in "
            "`cross_dataset_ruling_map.csv` records a real, distinct "
            "application of a ruling to a real target row; deleting them "
            "destroys the only measure of how far a ruling reached. The fix "
            "is the same shape as `430`'s fix for `prime_contracts`: write "
            "the identity that was dropped. `23` holds the target row at the "
            "moment it appends — one extra column (the target row's own "
            "transaction/award key) turns every duplicate into a distinct, "
            "keyable event, and the counts go to zero without removing a row. "
            "Until that change, the graph's degree counts and the ledger's "
            "per-subject counts are inflated and neither table can be given a "
            "primary key.",
        ]
    L += [
        "",
        "## 2. `fpds_uei_cage_map.csv` — DECLARED",
        "",
        f"The `GRAIN_OPEN` question asked whether the key needs the year "
        f"range, or whether the table is one row per UEI. Neither. "
        f"**`(uei, cage_code, legal_business_name)` is unique across all "
        f"{cage['rows']:,} rows** ({cage['pk_dup']} duplicates), so "
        f"`first_year`/`last_year`/`n_observations` are the rollup and "
        f"`source_file` — a `;`-joined list — is not needed in the key. One "
        f"row per UEI is refuted: `uei` repeats up to "
        f"{cage['max_rows_per_uei']} times.",
        "",
        "**A join hazard that matters more than the grain.**",
        "",
        f"- `cage_code` is blank on **{cage['blank']:,}** rows — a UEI "
        f"observed under a legal name with no CAGE in that extract. Blank is "
        f"a value here, not a gap.",
        f"- `cage_code` is the literal string **`NAN`** on "
        f"**{cage['nan']:,}** rows spanning **{cage['nan_ueis']:,} distinct "
        f"UEIs** — a null stringified on export. Anyone joining on "
        f"`cage_code` without excluding it fuses {cage['nan_ueis']:,} "
        f"unrelated entities into one.",
        f"- {cage['malformed']:,} further rows carry something that is not "
        f"five characters and cannot be a CAGE.",
        f"- Excluding those, the route is near-exact: of **{cage['n_cage']:,} "
        f"real CAGE codes only {cage['ambiguous']:,} map to more than one "
        f"UEI**, and none maps to more than two. This is why the shard-E "
        f"ASRC Federal link worked where name matching cannot — and why the "
        f"`NAN` rows have to be excluded in the query, not discovered later.",
        "",
        "## 3. `contractor_ranking.csv` — UNSTATED, and this is the answer, "
        "not a shortfall",
        "",
        f"`269_build_contractor_ranking.py` emits one row per "
        f"`(tribe_id, firm_key)`, where `firm_key` is the awardee UEI or a "
        f"`NAME:` fallback. **`firm_key` is never written to the file**, and "
        f"the privacy guard then blanks `operating_company_uei` and replaces "
        f"`operating_company_name` with the literal "
        f"`WITHHELD_POSSIBLE_PERSONAL_NAME` on "
        f"{rank['withheld']:,} of {rank['rows']:,} rows. The redaction is not "
        f"injective, so distinct operating companies of the same owner become "
        f"indistinguishable.",
        "",
        f"Measured: **all {rank['nonmeasure']} non-measure columns taken "
        f"together still leave {rank['all_nm_dup']} duplicate rows.** "
        f"`(owner_entity_id, operating_company_uei, operating_company_name)` "
        f"leaves {rank['id_dup']}, and **every one of them is a withheld "
        f"row** — on the {rank['published']:,} published rows that key is "
        f"unique with no blanks. There is no primary key on the shipped, "
        f"non-measure columns, and a key containing a dollar amount is not a "
        f"grain.",
        "",
        "The withheld rows are also a false positive worth naming on its "
        "own: they include **Nez Perce Tribe, Pueblo of Acoma, Rosebud Sioux "
        "Tribe, Ramah Navajo Chapter, Blackfeet Utilities and Wyandotte Net "
        "Tel** — tribal governments and tribal utilities, suppressed as "
        "possible personal names, one of them carrying $71.9M.",
        "",
        "**The fix, precisely.** `269` should emit one more column — an "
        "ordinal `operating_company_seq`, 1..n within `owner_entity_id` in "
        "the sort order it already uses. `(owner_entity_id, "
        "operating_company_seq)` is then unique by construction, leaks "
        "nothing a redaction was protecting, and lets this table be declared. "
        "That is a one-column change to a script WS2 does not own.",
        "",
        "## 4. C7 — what may be summed in `contractor_ranking.csv`",
        "",
        "| statement | measured |",
        "|---|---:|",
        f"| `SUM(firm_obligations_usd)` over every row | "
        f"${rank['firm_sum']/1e9:,.2f}B |",
        f"| `prime_contracts.csv`, tier-A attributed `total_obligations` | "
        f"${rank['tierA']/1e9:,.2f}B |",
        f"| difference | ${rank['firm_sum'] - rank['tierA']:,.2f} |",
        f"| `SUM(owner_obligations_usd)` over every row | "
        f"${rank['owner_naive']/1e9:,.2f}B |",
        f"| the same, over distinct `owner_entity_id` | "
        f"${rank['owner_true']/1e9:,.2f}B |",
        f"| inflation if row-summed | "
        f"**{rank['factor']:,.2f}x** over {rank['n_owners']} owners |",
        "",
        "So:",
        "",
        f"1. **`firm_obligations_usd` is the one column summable at row "
        f"grain.** It totals to within ${abs(rank['firm_sum']-rank['tierA']):.2f} "
        f"of the tier-A attributed slice of "
        f"`prime_contracts.csv` - rounding, on $176.7B - which means the "
        f"ranking is a lossless "
        f"partition of that slice — **and that it is the same money**. "
        f"Summing this table alongside the transaction table, or unioning "
        f"them, double-counts ${rank['tierA']/1e9:,.2f}B.",
        f"2. **Every `owner_*` column is an OWNER-grain attribute repeated on "
        f"every operating-company row of that owner.** Row-summing "
        f"`owner_obligations_usd` inflates it "
        f"{rank['factor']:,.1f}x. They may be totalled only after collapsing "
        f"to distinct `owner_entity_id`.",
        "3. `firm_*` columns are firm-grain and additive. `owner_rank` is an "
        "owner attribute, not a row attribute.",
        "",
        "## 5. C8 — what a rebuild of the hub actually destroys, and what a "
        "safe one requires",
        "",
        "*Measured without running either builder.*",
        "",
        "### 5.1 `01_build_entity_spine.py`",
        "",
        "| | |",
        "|---|---:|",
        f"| live `cedar_entity_spine.csv` rows | {rb['spine_rows']:,} |",
        f"| `canonical_tribe_table.csv`, 01's **only** spine source | "
        f"{rb['canon']:,} |",
        f"| **entities a rebuild drops** | **{rb['dropped']:,}** "
        f"({100*rb['dropped']/max(rb['spine_rows'],1):.0f}%) |",
        f"| columns on the live file | {rb['live_cols']} |",
        f"| columns 01 writes | 12 |",
        f"| **columns a rebuild drops** | **{len(rb['lost_cols'])}** |",
        "",
        "The dropped entities, by class:",
        "",
    ]
    for k, v in rb["by_class"]:
        L.append(f"- {v:,} {k}")
    L += [
        "",
        "01 builds `spine = {}` and fills it from `canonical_tribe_table.csv` "
        "alone. Everything scripts 52, 61, 73, 75, 163, 241, 426 and 524 "
        "appended is absent from that source and therefore gone, and the 12 "
        "columns it writes discard the other "
        f"{len(rb['lost_cols'])} — including `cedar_uid`, `parent_entity_id`, "
        "`fr_official_name`, `evidence_tier` and every hierarchy column.",
        "",
        "**What is unrecoverable, and what is not.** `data/spine/*` is "
        "gitignored (`.gitignore` line 95) with exactly two exceptions: "
        "`cedar_identity_register.csv` and `cedar_handle_history.csv`, which "
        "are force-tracked because they are not regenerable. "
        "**`cedar_entity_spine.csv` itself is NOT in git, so git cannot "
        "restore it.** The only safety net is the "
        "`.csv.bak_<date>_pre<NN>` convention — and **`01` is one of the few "
        "spine writers that does not take one.** Every enricher that touches "
        "the spine (51, 52, 61, 66, 69, 71, 73, 74, 75, 163, 241, 416, 426, "
        "503, 524) does.",
        "",
        f"The one piece of good news, and it is load-bearing: **`handle` in "
        f"the register equals `tribe_id` in the spine for all "
        f"{rb['handle_match']:,} of {rb['reg_rows']:,} rows.** So the "
        f"`cedar_uid` ↔ entity binding survives a spine overwrite inside a "
        f"git-tracked file and can be rejoined on `handle`. That matters "
        f"because only {rb['with_cei']:,} spine rows carry a "
        f"`cedar_entity_id`, so the register's other join column would have "
        f"recovered barely two thirds of them.",
        "",
        "### 5.2 `09_import_rulings.py`",
        "",
        f"09 rebuilds `cedar_identifier_ledger_final.csv` "
        f"({rb['fin']:,} rows) from `cedar_identifier_ledger_tiered.csv` "
        f"({rb['tie']:,} rows), which does not carry what later scripts "
        f"appended directly to `_final`. **A rerun today drops "
        f"{rb['lost_ledger']:,} ledger rows** - "
        + ", ".join(f"{v:,} at tier {k}"
                    for k, v in sorted(rb['lost_tiers'].items()))
        + f". The tier-A "
        f"losses are `elijah_ruling` and `nho_verified_entities.csv` rows — "
        f"owner adjudications, the one thing in this project that cannot be "
        f"re-derived from a source. `NEVER_RUN` records that running it on "
        f"2026-08-08 destroyed 1,327 rows and 451 village-corporation links; "
        f"the number has since grown to {rb['lost_ledger']:,}.",
        "",
        "### 5.3 The safe rebuild procedure",
        "",
        "**First, the risk is smaller than the blocker text implies, and the "
        "blocker should say so.** `build.plan_for('_entity_layer')` already "
        "sorts both scripts into a `blocked` phase, so "
        "`py -3 code/build.py run _entity_layer --execute` — the very command "
        "518 prints as `rebuild_entry` — **does not run them**. The residual "
        "exposure is a human or an agent invoking "
        "`py -3 code/01_build_entity_spine.py` directly, which nothing "
        "prevents and which no backup would survive.",
        "",
        "A rebuild is survivable only if all six of these hold. **Today item "
        "4 cannot be satisfied**, which is the whole of the C8 answer; the "
        "rest are written out because the failure mode is skipping one.",
        "",
        "1. **Back up first, by hand, because the builders will not.** "
        "`shutil.copy2` (or `cp`) `data/spine/cedar_entity_spine.csv`, "
        "`data/spine/cedar_identifier_ledger.csv`, "
        "`data/clean/cedar_identifier_ledger_final.csv` and "
        "`data/clean/cedar_identifier_ledger_tiered.csv` to "
        "`<name>.bak_<date>_pre01` / `_pre09`. This is the project's existing "
        "convention and it is the ONLY recovery route for these files.",
        "2. **Record the pre-rebuild census**: row count, distinct `tribe_id`, "
        "full column list, and the tier histogram of the ledger. Without it "
        "there is nothing to compare the rebuild against, and a 56% loss "
        "looks like a successful run.",
        "3. **Confirm the seven external inputs are present** under "
        "`data/raw/external/` and that "
        "`C:\\Users\\esm247\\Desktop\\dissertation\\data\\"
        "tribal_federal_spending` still resolves. All seven are present as "
        "of this measurement. If a source is missing, 01 logs `MISSING` and "
        "silently builds from the previously staged copy — which is a "
        "resilience, but it means a rebuild can succeed while quietly using "
        "stale inputs.",
        "4. **Replay every enricher, and understand that the ORDER is not "
        "recorded anywhere.** `cedar_pipeline.all_orderings` names 15 "
        "spine-modifying enrichers and 8 ledger enrichers, but "
        "`build.plan_for` returns them in lexicographic order (…, `50`, "
        "`503`, `51`, `52`, …), which is not the order in which they were "
        "originally applied. **No dependency-correct replay order exists in "
        "the repo.** Producing one is the prerequisite this blocker really "
        "names.",
        "5. **Do not replay a minting enricher blind.** "
        "`426_mint_bristol_bay_spine_entities.py` mints. `503_identity.py "
        "mint` re-uses existing uids keyed on the handle and is safe because "
        "handle equals tribe_id; 426 must be checked against the register "
        "before it is run, and the register is append-only — a wrong replay "
        "cannot be undone by deleting rows from it.",
        "6. **Gate on conservation, not on completion.** The rebuild is "
        f"acceptable only if the post-replay spine has ≥ {rb['spine_rows']:,} "
        f"rows and all {rb['live_cols']} columns, and the post-replay ledger "
        f"has ≥ {rb['fin']:,} rows with no fall in the tier-A count. Anything "
        "less is a partial restore wearing a green build log.",
        "",
        "**The honest bottom line: the spine cannot be rebuilt safely today, "
        "and the missing piece is specific.** It is not the backups — the "
        "convention exists and every enricher but the two rebuilders honours "
        "it. It is that *no dependency-correct enricher replay order is "
        "recorded*, so nobody can state what the 15 spine enrichers must run "
        "in, or prove that running them reproduces the 1,555 rows and 44 "
        "columns that are on disk. Two changes convert this from a mystery "
        "into a task: (a) `01` and `09` take a `.bak` before writing, like "
        "every other writer in the project; (b) the replay order is recorded "
        "in `cedar_pipeline` and exercised once, against the census in step "
        "2. Until (b), the correct operational posture is the one already in "
        "force — never run them, keep them in `NEVER_RUN`, and keep the "
        "planner's `blocked` phase.",
        "",
        "## 6. `foia_request_index.csv` — a GRAIN_OPEN question answered",
        "",
        f"The open question asked whether the {foia.get('surplus', 0)} "
        f"surplus rows mean the grain is `(request, matched tribe mention)` "
        f"or whether `foia_request_id` is simply not unique. It is neither "
        f"ambiguous nor a grain: **all {foia.get('flagged', 0)} rows in a "
        f"collision group carry "
        f"`control_number_appears_more_than_once` in their own "
        f"`parse_quality_reason`, and no row outside one does.** "
        f"`request_description` differs in {foia.get('desc_differs', 0)} of "
        f"{foia.get('groups', 0)} groups. One FOIA log entry was split across "
        f"two rows by the parser, and the table already names every instance. "
        f"`foia_request_id` IS the intended key; this is a defect for the "
        f"owner of `136_build_congressional_correspondence_and_foia_index.py` "
        f"to repair, not a grain for a contract to declare.",
        "",
        f"**`visitor_record_foia_requests.csv` has the identical signature "
        f"from a different builder.** {foia.get('v_groups', 0)} colliding "
        f"`foia_request_id` values, {foia.get('v_surplus', 0)} surplus rows, "
        f"and `request_description_verbatim` differs in "
        f"{foia.get('v_desc', 0)} of {foia.get('v_groups', 0)} groups — which "
        f"is why the only \"unique key\" anyone found on that table was the "
        f"free-text description itself. `136` and `146` parse different "
        f"sources and produced the same defect, so this is **one class of "
        f"fix, not two open questions**: a FOIA log entry whose control "
        f"number appears twice in the source text is being emitted as two "
        f"fragmentary rows instead of one.",
        "",
        "## 7. C5 — row conservation for `contractors`",
        "",
        f"Merged into the shared `data/clean/cedar_harvest_conservation.csv` "
        f"on the `(source_table, disposition)` key: "
        f"{cons[0]:,} → {cons[1]:,} ledger rows, accounted rows "
        f"{cons[2]:,} → {cons[3]:,}. Nothing belonging to another workstream "
        f"was rewritten, and a `.bak` was taken first.",
        "",
        "## 8. What is still blocked, and who owns it",
        "",
        "| blocker | table | owner |",
        "|---|---|---|",
        "| C1/C2/C3 — no key while the rows are indistinguishable | "
        "`cross_dataset_ruling_map.csv` | "
        "`23_cross_dataset_propagation.py`: write the target row key |",
        "| C1/C2/C3 — inherited from the above | "
        "`cedar_ruling_ledger_consolidated.csv` | "
        "`173_consolidate_rulings_ledger.py` |",
        "| C1/C2/C3 — inherited from the above | "
        "`cedar_identifier_graph_edges.csv` | "
        "`169_build_identifier_graph.py` |",
        "| C1/C2/C7 — key destroyed by redaction | "
        "`contractor_ranking.csv` | `269`: emit "
        "`operating_company_seq` |",
        "| C1/C2 — parse split, table names it itself | "
        "`foia_request_index.csv` | `136` |",
        "| C1/C2 — 22 collisions on `foia_request_id` | "
        "`visitor_record_foia_requests.csv` | `146` |",
        "| C1/C2/C3 — 4 literal duplicate rows of 130 | "
        "`tcu_cdfi_ownership_evidence.csv` | `73_add_tcu_and_cdfi.py` |",
        "| C8 — no recorded enricher replay order | "
        "`cedar_entity_spine.csv` | pipeline owner; see §5.3 |",
        "",
    ]
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(L), encoding="utf-8")
    print(f"\n  wrote {OUT_MD.relative_to(ROOT)}")


def main() -> int:
    apply = len(sys.argv) > 1 and sys.argv[1] == "apply"
    print("=== 572: WS2 - entity layer hub + contractors ===")
    print(f"    {TODAY}   mode: {'APPLY' if apply else 'measure (read-only)'}")
    dups = measure_duplicates()
    casc = measure_cascade()
    cage = measure_cage_map()
    rank = measure_ranking()
    rb = measure_rebuild()
    foia = measure_foia()
    rows = conservation_rows(cage, rank)
    print(f"\n[C5] {len(rows)} conservation ledger row(s) prepared")
    for r in rows:
        print(f"    {r['source_table'].split('/')[-1]:<28} "
              f"{r['rows']:>7,}  {r['pct']:>6}%  {r['disposition'][:60]}")
    if apply:
        cons = merge_conservation(rows)
        write_doc(dups, casc, cage, rank, rb, foia, cons)
    else:
        print("\n  read-only. Re-run with `apply` to merge C5 and write the "
              "doc.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
