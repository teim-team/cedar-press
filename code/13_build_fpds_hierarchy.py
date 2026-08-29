#!/usr/bin/env python3
"""
13_build_fpds_hierarchy.py
==========================
Rebuild the corporate-hierarchy edge list for Cedar Press directly from the raw
FPDS / FSRS transaction extracts.

WHY
---
The derived graph at data/raw/external/uei_hierarchy_graph.csv is ~88% edgeless
(most nodes are self-parented). The real parent/child relationships are carried
on every FPDS transaction row in the SAM-sourced entity block:

    uei_id / uei_legal_business_name
    immediate_parent_uei  / immediate_parent_uei_name
    domestic_parent_uei   / domestic_parent_uei_name
    ultimate_parent_uei   / ultimate_parent_uei_name
    cage_code

PRIME DIRECTIVE: ZERO FABRICATION.
Every emitted edge is a literal (child, parent) pair that appears on at least one
observed transaction row. No name matching, no fuzzy inference, no transitive
closure. Self-edges (child == parent) are dropped because they carry no
information; they are counted and reported, not silently discarded.

OUTPUTS
-------
  data/clean/fpds_uei_edges.csv
      child_uei, child_name, parent_uei, parent_name, edge_type,
      source_file, n_observations, first_year, last_year
  data/clean/fpds_uei_cage_map.csv
      uei, cage_code, legal_business_name, n_observations,
      first_year, last_year, source_file

EDGE TYPES
----------
  parent_uei           immediate/direct corporate parent (FPDS immediate_parent_uei,
                       USAspending "Parent UEI" / "Sub Awardee Parent UEI" /
                       "Prime Awardee Parent UEI")
  ultimate_parent_uei  top of the corporate family (FPDS ultimate_parent_uei)
  domestic_parent_uei  highest US-domiciled parent (FPDS domestic_parent_uei).
                       NOT in the original 3-type spec but it is real, observed
                       data and is materially useful for ANC/tribal families, so
                       it is emitted and clearly labeled. Filter it out if you
                       only want the three specified types.
  prime_to_sub         subawardee -> prime on the same subaward (FSRS).
                       *** THIS IS A CONTRACTING RELATIONSHIP, NOT OWNERSHIP. ***
                       Do NOT propagate Native-entity ownership along these edges
                       in the spiderweb step.

USAGE
-----
  py -3 code/13_build_fpds_hierarchy.py
  py -3 code/13_build_fpds_hierarchy.py --limit 50000     # smoke test
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import time
from collections import Counter, defaultdict

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(PROJECT, "data", "raw", "esm_hci", "ESM", "raw")
CLEAN = os.path.join(PROJECT, "data", "clean")
LOGS = os.path.join(PROJECT, "logs")
DOCS = os.path.join(PROJECT, "docs")

EDGES_OUT = os.path.join(CLEAN, "fpds_uei_edges.csv")
CAGE_OUT = os.path.join(CLEAN, "fpds_uei_cage_map.csv")
LOG_PATH = os.path.join(LOGS, "13_fpds_hierarchy_2026-08-05.log")
OLD_GRAPH = os.path.join(PROJECT, "data", "raw", "external", "uei_hierarchy_graph.csv")
BUILD_LOG_MD = os.path.join(DOCS, "FPDS_HIERARCHY_BUILD_LOG_2026-08-05.md")

csv.field_size_limit(1 << 30)

UEI_RE = re.compile(r"^[A-Z0-9]{12}$")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
_logfh = None


def log(msg: str) -> None:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {msg}"
    print(line, flush=True)
    if _logfh is not None:
        _logfh.write(line + "\n")
        _logfh.flush()


# ---------------------------------------------------------------------------
# File specs.  Columns are referenced BY NAME where names are unique, and BY
# INDEX for the FSRS subaward file, which ships two columns both literally
# named "CAGE Code" (positions 22 and 23).
# ---------------------------------------------------------------------------
FPDS_BIG = {
    "kind": "fpds",
    "uei": "uei_id",
    "uei_name": "uei_legal_business_name",
    "fallback_name": "recipient_name",
    "cage": "cage_code",
    "year": "action_date_fiscal_year",
    "date": "action_date",
    "parents": [
        ("parent_uei", "immediate_parent_uei", "immediate_parent_uei_name"),
        ("domestic_parent_uei", "domestic_parent_uei", "domestic_parent_uei_name"),
        ("ultimate_parent_uei", "ultimate_parent_uei", "ultimate_parent_uei_name"),
    ],
}

FILES = [
    # ADDED 2026-08-30. The assistance side was never harvested: the original
    # build read only the CONTRACT extracts, so the 2,290 edges skewed toward
    # 8(a) contractors and missed assistance-heavy organisations entirely -
    # measured: Bristol Bay Area Health Corporation, 695 transactions in the
    # clean table, ZERO edges here. recipient_parent_uei in this file is the
    # same SAM-sourced entity block the FPDS files carry, public and
    # unmetered - the systematic alternative to the SAM Entity API, whose key
    # measured out at 10 calls/day with the hierarchy section hidden.
    # The absolute path is honoured by os.path.join(RAW, fname), which
    # returns an absolute second argument unchanged; this file lives outside
    # RAW and is not copied, because 600 MB has one home on this machine.
    (str(__import__("pathlib").Path(PROJECT) / "Federal Spending" / "raw" /
         "Assistance_PrimeTransactions_2023-04-09_H19M53S53_1.csv"),
     {
        "kind": "usaspending_assistance",
        "uei": "recipient_uei",
        "uei_name": "recipient_name",
        "fallback_name": "recipient_name_raw",
        "cage": None,                      # assistance carries no CAGE
        "year": "action_date_fiscal_year",
        "date": "action_date",
        "parents": [
            ("parent_uei", "recipient_parent_uei", "recipient_parent_name"),
        ],
     }),
    ("Data Request 4-5-2023 File 1.csv", FPDS_BIG),
    ("Data Request 4-5-2023 File 2.csv", FPDS_BIG),
    ("Data Request 5-8-2023 IDVs.csv", FPDS_BIG),
    (
        "contract-03-18-23-19-40-24.csv",
        {
            "kind": "usaspending_contract",
            "uei": "Awardee UEI",
            "uei_name": "Awardee Name",
            "fallback_name": None,
            "cage": "Awardee Cage Code",
            "year": "Most Recent Action Date Fiscal Year",
            "date": "Most Recent Action Date",
            "parents": [("parent_uei", "Parent UEI", "Awardee Parent Name")],
            "parent_cage": ("Parent UEI", "Parent CAGE Code", "Awardee Parent Name"),
        },
    ),
    (
        "subcontract-05-09-23-22-23-37.csv",
        {
            "kind": "fsrs_subaward",
            # positional because of the duplicated "CAGE Code" header
            "i_sub_uei": 3,
            "i_sub_name": 1,
            "i_sub_cage": 5,
            "i_sub_parent_uei": 4,
            "i_sub_parent_name": 2,
            "i_sub_parent_cage": 6,
            "i_prime_uei": 20,
            "i_prime_name": 18,
            "i_prime_cage": 22,
            "i_prime_parent_uei": 21,
            "i_prime_parent_name": 19,
            "i_prime_parent_cage": 23,
            "i_year": 10,
            "i_date": 9,
        },
    ),
]

# ---------------------------------------------------------------------------
# Accumulators
# ---------------------------------------------------------------------------
# (child_uei, parent_uei, edge_type) -> dict
edges: dict[tuple[str, str, str], dict] = {}
# (uei, cage, legal_name) -> dict
cages: dict[tuple[str, str, str], dict] = {}

stats = defaultdict(int)
per_file_stats: list[dict] = []
all_ueis: set[str] = set()
malformed_uei: set[str] = set()
# uei -> Counter(name -> observations); used to pick the MODAL recorded name
uei_names: dict[str, Counter] = defaultdict(Counter)
# diagnostics per (file, parent column): how often it was populated at all
col_diag: dict[tuple[str, str], dict] = {}


def norm(v) -> str:
    if v is None:
        return ""
    return v.strip()


def norm_uei(v) -> str:
    u = norm(v).upper()
    if u and not UEI_RE.match(u):
        malformed_uei.add(u)
    return u


def year_of(fy: str, date: str) -> int | None:
    fy = norm(fy)
    if fy[:4].isdigit():
        return int(fy[:4])
    d = norm(date)
    if len(d) >= 4 and d[:4].isdigit():
        return int(d[:4])
    return None


def note_name(uei: str, name: str) -> None:
    """Tally every legal name literally recorded for this UEI, so the output can
    report the MODAL recorded name rather than whichever row happened to be read
    first. Some UEIs (notably federal registrants) appear under several names."""
    if uei and name:
        uei_names[uei][name] += 1


def modal_name(uei: str, fallback: str = "") -> str:
    c = uei_names.get(uei)
    if not c:
        return fallback
    return c.most_common(1)[0][0]


def add_edge(child, child_name, parent, parent_name, etype, src, yr):
    """Record one literally-observed (child -> parent) pair."""
    note_name(child, child_name)
    note_name(parent, parent_name)
    if not child or not parent:
        stats["edge_rows_missing_side"] += 1
        return
    if child == parent:
        stats["self_edges_dropped"] += 1
        return
    key = (child, parent, etype)
    e = edges.get(key)
    if e is None:
        e = edges[key] = {
            "child_name": child_name,
            "parent_name": parent_name,
            "n": 0,
            "first_year": yr,
            "last_year": yr,
            "sources": set(),
        }
    e["n"] += 1
    e["sources"].add(src)
    if not e["child_name"] and child_name:
        e["child_name"] = child_name
    if not e["parent_name"] and parent_name:
        e["parent_name"] = parent_name
    if yr is not None:
        if e["first_year"] is None or yr < e["first_year"]:
            e["first_year"] = yr
        if e["last_year"] is None or yr > e["last_year"]:
            e["last_year"] = yr


def add_cage(uei, cage, name, src, yr):
    note_name(uei, name)
    if not uei:
        return
    key = (uei, cage, name)
    c = cages.get(key)
    if c is None:
        c = cages[key] = {"n": 0, "first_year": yr, "last_year": yr, "sources": set()}
    c["n"] += 1
    c["sources"].add(src)
    if yr is not None:
        if c["first_year"] is None or yr < c["first_year"]:
            c["first_year"] = yr
        if c["last_year"] is None or yr > c["last_year"]:
            c["last_year"] = yr


# ---------------------------------------------------------------------------
# Streaming reader
# ---------------------------------------------------------------------------
def stream_file(fname: str, spec: dict, limit: int | None) -> dict:
    path = os.path.join(RAW, fname)
    size_gb = os.path.getsize(path) / 1e9
    log(f"--- scanning {fname} ({size_gb:.2f} GB, kind={spec['kind']})")

    fst = {
        "file": fname,
        "rows": 0,
        "bad_rows": 0,
        "short_rows": 0,
        "parse_errors": 0,
        "edges_added": 0,
        "ueis": set(),
    }
    t0 = time.time()
    edges_before = len(edges)

    fh = open(path, "r", newline="", encoding="utf-8", errors="replace")
    reader = csv.reader(fh)
    try:
        header = next(reader)
    except StopIteration:
        log(f"    EMPTY FILE: {fname}")
        fh.close()
        fst["ueis"] = set()
        return fst

    ncol = len(header)
    idx = {}
    for i, c in enumerate(header):
        idx.setdefault(c.strip(), i)  # first occurrence wins for duplicate names

    if spec["kind"] in ("fpds", "usaspending_contract", "usaspending_assistance"):
        need = [spec["uei"], spec["uei_name"], spec["year"], spec["date"]]
        if spec.get("cage"):               # assistance files carry no CAGE
            need.append(spec["cage"])
        need += [p[1] for p in spec["parents"]] + [p[2] for p in spec["parents"]]
        if spec.get("fallback_name"):
            need.append(spec["fallback_name"])
        missing = [c for c in need if c not in idx]
        if missing:
            log(f"    !! MISSING COLUMNS in {fname}: {missing}")
            fh.close()
            return fst

    while True:
        try:
            row = next(reader)
        except StopIteration:
            break
        except csv.Error as exc:
            fst["parse_errors"] += 1
            stats["parse_errors"] += 1
            if fst["parse_errors"] <= 5:
                log(f"    csv.Error (skipped, #{fst['parse_errors']}): {exc}")
            continue

        fst["rows"] += 1
        if limit and fst["rows"] > limit:
            fst["rows"] -= 1
            break

        if len(row) < ncol:
            # ragged / truncated line: too short to trust column positions
            fst["short_rows"] += 1
            fst["bad_rows"] += 1
            continue

        try:
            if spec["kind"] in ("fpds", "usaspending_contract",
                                "usaspending_assistance"):
                uei = norm_uei(row[idx[spec["uei"]]])
                name = norm(row[idx[spec["uei_name"]]])
                if not name and spec.get("fallback_name"):
                    name = norm(row[idx[spec["fallback_name"]]])
                cage = (norm(row[idx[spec["cage"]]]).upper()
                        if spec.get("cage") else "")
                yr = year_of(row[idx[spec["year"]]], row[idx[spec["date"]]])

                if uei:
                    fst["ueis"].add(uei)
                    add_cage(uei, cage, name, fname, yr)

                for etype, pcol, pncol in spec["parents"]:
                    puei = norm_uei(row[idx[pcol]])
                    pname = norm(row[idx[pncol]])
                    d = col_diag.setdefault(
                        (fname, pcol), {"nonblank": 0, "nonself": 0, "etype": etype}
                    )
                    if puei:
                        d["nonblank"] += 1
                        fst["ueis"].add(puei)
                        if puei != uei:
                            d["nonself"] += 1
                    add_edge(uei, name, puei, pname, etype, fname, yr)

                pc = spec.get("parent_cage")
                if pc:
                    ppuei = norm_uei(row[idx[pc[0]]])
                    ppcage = norm(row[idx[pc[1]]]).upper()
                    ppname = norm(row[idx[pc[2]]])
                    if ppuei:
                        add_cage(ppuei, ppcage, ppname, fname, yr)

            elif spec["kind"] == "fsrs_subaward":
                yr = year_of(row[spec["i_year"]], row[spec["i_date"]])

                sub = norm_uei(row[spec["i_sub_uei"]])
                sub_n = norm(row[spec["i_sub_name"]])
                sub_c = norm(row[spec["i_sub_cage"]]).upper()
                subp = norm_uei(row[spec["i_sub_parent_uei"]])
                subp_n = norm(row[spec["i_sub_parent_name"]])
                subp_c = norm(row[spec["i_sub_parent_cage"]]).upper()

                pri = norm_uei(row[spec["i_prime_uei"]])
                pri_n = norm(row[spec["i_prime_name"]])
                pri_c = norm(row[spec["i_prime_cage"]]).upper()
                prip = norm_uei(row[spec["i_prime_parent_uei"]])
                prip_n = norm(row[spec["i_prime_parent_name"]])
                prip_c = norm(row[spec["i_prime_parent_cage"]]).upper()

                for u in (sub, subp, pri, prip):
                    if u:
                        fst["ueis"].add(u)

                add_cage(sub, sub_c, sub_n, fname, yr)
                add_cage(subp, subp_c, subp_n, fname, yr)
                add_cage(pri, pri_c, pri_n, fname, yr)
                add_cage(prip, prip_c, prip_n, fname, yr)

                # corporate parents (ownership)
                add_edge(sub, sub_n, subp, subp_n, "parent_uei", fname, yr)
                add_edge(pri, pri_n, prip, prip_n, "parent_uei", fname, yr)
                # contracting relationship (NOT ownership)
                add_edge(sub, sub_n, pri, pri_n, "prime_to_sub", fname, yr)

        except IndexError:
            fst["bad_rows"] += 1
            stats["bad_rows"] += 1
            continue

        if fst["rows"] % 250_000 == 0:
            el = time.time() - t0
            log(
                f"    {fst['rows']:,} rows | {len(edges):,} distinct edges | "
                f"{len(cages):,} cage triples | {el/60:.1f} min"
            )

    fh.close()
    fst["edges_added"] = len(edges) - edges_before
    el = time.time() - t0
    log(
        f"    DONE {fname}: {fst['rows']:,} rows in {el/60:.1f} min | "
        f"bad/short rows skipped={fst['bad_rows']:,} | csv parse errors={fst['parse_errors']:,} | "
        f"distinct UEIs seen={len(fst['ueis']):,} | new distinct edge keys=+{fst['edges_added']:,}"
    )
    all_ueis.update(fst["ueis"])
    return fst


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------
def write_edges(limit=0) -> None:
    os.makedirs(CLEAN, exist_ok=True)
    if limit:
        # A --limit run is a SMOKE TEST, and on 2026-08-30 one overwrote the
        # shipping edge table with a 2,000-rows-per-file sample: 2,290 edges
        # became 841 in data/clean with nothing marking them partial. A test
        # mode that writes production output is the FERC class4 disease in a
        # new coat - partial state presented as the real thing. Truncated
        # runs now write nothing and say so.
        log(f"--limit {limit} run: outputs NOT written (smoke test only)")
        return
    with open(EDGES_OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "child_uei",
                "child_name",
                "parent_uei",
                "parent_name",
                "edge_type",
                "source_file",
                "n_observations",
                "first_year",
                "last_year",
            ]
        )
        for (child, parent, etype) in sorted(edges):
            e = edges[(child, parent, etype)]
            w.writerow(
                [
                    child,
                    modal_name(child, e["child_name"]),
                    parent,
                    modal_name(parent, e["parent_name"]),
                    etype,
                    ";".join(sorted(e["sources"])),
                    e["n"],
                    e["first_year"] if e["first_year"] is not None else "",
                    e["last_year"] if e["last_year"] is not None else "",
                ]
            )
    log(f"wrote {EDGES_OUT} ({len(edges):,} rows)")


def write_cages(limit=0) -> None:
    if limit:
        log(f"--limit {limit} run: cage map NOT written (smoke test only)")
        return
    with open(CAGE_OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "uei",
                "cage_code",
                "legal_business_name",
                "n_observations",
                "first_year",
                "last_year",
                "source_file",
            ]
        )
        for (uei, cage, name) in sorted(cages):
            c = cages[(uei, cage, name)]
            w.writerow(
                [
                    uei,
                    cage,
                    name,
                    c["n"],
                    c["first_year"] if c["first_year"] is not None else "",
                    c["last_year"] if c["last_year"] is not None else "",
                    ";".join(sorted(c["sources"])),
                ]
            )
    log(f"wrote {CAGE_OUT} ({len(cages):,} rows)")


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def load_old_graph():
    """Old derived graph -> set of non-self (child,parent) pairs, by type."""
    old_pairs = set()
    old_nodes = set()
    old_by_type = defaultdict(set)
    if not os.path.exists(OLD_GRAPH):
        log(f"!! old graph not found at {OLD_GRAPH}")
        return old_pairs, old_nodes, old_by_type, 0
    n = 0
    with open(OLD_GRAPH, newline="", encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            n += 1
            u = norm(r.get("uei", "")).upper()
            if u:
                old_nodes.add(u)
            for col, et in (("parent_uei", "parent_uei"), ("ultimate_parent_uei", "ultimate_parent_uei")):
                p = norm(r.get(col, "")).upper()
                if u and p and p != u:
                    old_pairs.add((u, p))
                    old_by_type[et].add((u, p))
    return old_pairs, old_nodes, old_by_type, n


def build_report(t_start: float) -> None:
    by_type = defaultdict(int)
    for (_, _, et) in edges:
        by_type[et] += 1

    # ownership edges only (exclude the contracting relationship)
    OWN = {"parent_uei", "domestic_parent_uei", "ultimate_parent_uei"}
    children_of = defaultdict(set)          # ownership, any type
    children_of_ult = defaultdict(set)      # ultimate_parent_uei only
    parent_names = {}
    for (child, parent, et), e in edges.items():
        if et in OWN:
            children_of[parent].add(child)
            parent_names[parent] = modal_name(parent, e["parent_name"])
        if et == "ultimate_parent_uei":
            children_of_ult[parent].add(child)

    # UEIs recorded under more than one distinct legal name (federal registrants
    # and post-merger renames both do this). Purely descriptive.
    multi_named = {u: c for u, c in uei_names.items() if len(c) > 1}
    FED_STR = "GOVERNMENT OF THE UNITED STATES"
    fed_parents = sorted(
        ((p, len(ch)) for p, ch in children_of.items()
         if FED_STR in (parent_names.get(p, "") or "").upper()),
        key=lambda kv: -kv[1],
    )

    multi = {p: c for p, c in children_of.items() if len(c) > 1}
    multi_ult = {p: c for p, c in children_of_ult.items() if len(c) > 1}
    top = sorted(children_of.items(), key=lambda kv: -len(kv[1]))[:20]

    # children recorded under more than one distinct ownership parent (real:
    # ownership changes hands, and SAM records get restated)
    parents_of = defaultdict(set)
    for (child, parent, et) in edges:
        if et in OWN:
            parents_of[child].add(parent)
    multi_parent_children = {c: p for c, p in parents_of.items() if len(p) > 1}

    old_pairs, old_nodes, old_by_type, old_rows = load_old_graph()
    new_pairs = {(c, p) for (c, p, et) in edges if et in OWN}
    truly_new = new_pairs - old_pairs
    old_not_found = old_pairs - new_pairs
    new_nodes = all_ueis - old_nodes

    total_rows = sum(f["rows"] for f in per_file_stats)
    total_bad = sum(f["bad_rows"] for f in per_file_stats)
    total_perr = sum(f["parse_errors"] for f in per_file_stats)

    nonempty_cage = sum(1 for (u, c, n) in cages if c)
    ueis_with_cage = len({u for (u, c, n) in cages if c})

    log("")
    log("=" * 72)
    log(f"TOTAL rows scanned            : {total_rows:,}")
    log(f"TOTAL bad/short rows skipped  : {total_bad:,}")
    log(f"TOTAL csv parse errors        : {total_perr:,}")
    log(f"Distinct UEIs observed        : {len(all_ueis):,}")
    log(f"Distinct edges (all types)    : {len(edges):,}")
    for et in sorted(by_type):
        log(f"   {et:<22}: {by_type[et]:,}")
    log(f"Self-edges dropped (rows)     : {stats['self_edges_dropped']:,}")
    log(f"Ownership parents w/ >1 child : {len(multi):,}")
    log(f"NEW ownership pairs vs old    : {len(truly_new):,}")
    log("=" * 72)

    # ---------------- markdown build log ----------------
    os.makedirs(DOCS, exist_ok=True)
    L = []
    A = L.append
    A("# FPDS Corporate-Hierarchy Rebuild — Build Log")
    A("")
    A("**Date:** 2026-08-05  ")
    A("**Script:** `code/13_build_fpds_hierarchy.py`  ")
    A("**Log:** `logs/13_fpds_hierarchy_2026-08-05.log`  ")
    A(f"**Runtime:** {(time.time()-t_start)/60:.1f} minutes")
    A("")
    A("## Purpose")
    A("")
    A("Rebuild the UEI parent/child edge list from raw FPDS + FSRS transaction rows so")
    A("that spiderweb attribution can propagate a verified Native-entity owner across a")
    A("whole corporate family. The previously used derived graph")
    A("(`data/raw/external/uei_hierarchy_graph.csv`) is almost entirely edgeless.")
    A("")
    A("**Zero fabrication.** Every edge below is a literal (child, parent) pair present")
    A("on at least one observed transaction row. No name matching, no inference, no")
    A("transitive closure. Self-edges (child == parent) are dropped as uninformative and")
    A("counted separately.")
    A("")
    A("## Identifier columns found in each source")
    A("")
    A("| File | Rows | Child UEI col | Parent cols | CAGE col | Year col |")
    A("|---|---:|---|---|---|---|")
    A("| `Data Request 4-5-2023 File 1.csv` | {:,} | `uei_id` (`uei_legal_business_name`) | `immediate_parent_uei`, `domestic_parent_uei`, `ultimate_parent_uei` (+ `_name`) | `cage_code` | `action_date_fiscal_year` |".format(per_file_stats[0]["rows"]))
    A("| `Data Request 4-5-2023 File 2.csv` | {:,} | same (316 cols, identical schema) | same | `cage_code` | `action_date_fiscal_year` |".format(per_file_stats[1]["rows"]))
    A("| `Data Request 5-8-2023 IDVs.csv` | {:,} | same (300 cols) | same | `cage_code` | `action_date_fiscal_year` |".format(per_file_stats[2]["rows"]))
    A("| `contract-03-18-23-19-40-24.csv` | {:,} | `Awardee UEI` (`Awardee Name`) | `Parent UEI` (`Awardee Parent Name`) | `Awardee Cage Code`, `Parent CAGE Code` | `Most Recent Action Date Fiscal Year` |".format(per_file_stats[3]["rows"]))
    A("| `subcontract-05-09-23-22-23-37.csv` | {:,} | `Sub Awardee UEI`, `Prime Awardee UEI` | `Sub Awardee Parent UEI`, `Prime Awardee Parent UEI` | `Sub Awardee Cage Code`, `Sub Awardee Parent Cage Code`, `CAGE Code` (x2, positional) | `Subaward Action Date Fiscal Year` |".format(per_file_stats[4]["rows"]))
    A("")
    A("Notes on schema gotchas:")
    A("")
    A("- There is **no** `parent_uei` / `recipient_uei` / `awardee_uei` column in the three big")
    A("  FPDS extracts. The entity block is `uei_id` + `immediate_parent_uei` +")
    A("  `domestic_parent_uei` + `ultimate_parent_uei`, each with a paired `_name`.")
    A("- Legacy `recipient_duns` / `recipient_parent_duns` / `recipient_parent_name` also exist")
    A("  but are DUNS-era and are not used for UEI edges.")
    A("- `subcontract-05-09-23-22-23-37.csv` has **two columns both literally named `CAGE Code`**")
    A("  (positions 22 and 23 = prime CAGE and prime-parent CAGE). They are read positionally;")
    A("  a `pandas` name-based read would mangle them.")
    A("")
    A("## Rows scanned per file")
    A("")
    A("| File | Rows scanned | Bad/short rows skipped | csv parse errors | Distinct UEIs | New distinct edge keys |")
    A("|---|---:|---:|---:|---:|---:|")
    for f in per_file_stats:
        A("| `{}` | {:,} | {:,} | {:,} | {:,} | {:,} |".format(
            f["file"], f["rows"], f["bad_rows"], f["parse_errors"], len(f["ueis"]), f["edges_added"]))
    A("| **TOTAL** | **{:,}** | **{:,}** | **{:,}** | **{:,} (union)** | **{:,}** |".format(
        total_rows, total_bad, total_perr, len(all_ueis), len(edges)))
    A("")
    if total_bad or total_perr:
        A(f"Malformed-row handling: {total_bad:,} rows were shorter than the header and were")
        A(f"skipped rather than positionally misread; {total_perr:,} rows raised a `csv.Error`.")
        A("Both counts are reported here rather than silently dropped.")
    else:
        A("No malformed rows encountered: every data row parsed to the full header width.")
    A("")
    A("## How often each parent column was actually populated")
    A("")
    A("This is the key coverage fact for the rebuild. In the three big FPDS extracts the")
    A("`immediate_parent_uei` and `domestic_parent_uei` columns are present in the schema but")
    A("almost never filled; virtually all FPDS-side hierarchy comes from `ultimate_parent_uei`.")
    A("")
    A("| File | Column | Rows with a value | Rows where value != child UEI |")
    A("|---|---|---:|---:|")
    for (fn, col), d in sorted(col_diag.items()):
        A(f"| `{fn}` | `{col}` | {d['nonblank']:,} | {d['nonself']:,} |")
    A("")
    A("## Distinct edges by type")
    A("")
    A("| edge_type | distinct edges | meaning |")
    A("|---|---:|---|")
    A(f"| `parent_uei` | {by_type.get('parent_uei',0):,} | immediate/direct corporate parent |")
    A(f"| `domestic_parent_uei` | {by_type.get('domestic_parent_uei',0):,} | highest US-domiciled parent (extra type, see note) |")
    A(f"| `ultimate_parent_uei` | {by_type.get('ultimate_parent_uei',0):,} | top of the corporate family |")
    A(f"| `prime_to_sub` | {by_type.get('prime_to_sub',0):,} | subawardee -> prime (CONTRACTING, not ownership) |")
    A(f"| **TOTAL** | **{len(edges):,}** | |")
    A("")
    A(f"Self-edges dropped (row-level occurrences): {stats['self_edges_dropped']:,}.")
    A(f"Rows where one side of a candidate edge was blank: {stats['edge_rows_missing_side']:,}.")
    A("")
    A("> `domestic_parent_uei` was not in the original three-type spec. It is real observed")
    A("> data and is retained because it distinguishes a US-domiciled intermediate holding")
    A("> company from a foreign ultimate parent. Filter on `edge_type` if you want only the")
    A("> three specified types.")
    A("")
    A("> `prime_to_sub` is a **contracting** relationship, not ownership. Do **not** propagate")
    A("> Native-entity ownership along `prime_to_sub` edges during spiderweb expansion.")
    A("")
    A("## Corporate families (ownership edges only)")
    A("")
    A(f"- Distinct parents with at least one child: **{len(children_of):,}**")
    A(f"- Parents with **more than one child**: **{len(multi):,}**")
    A(f"- Parents with >1 child under `ultimate_parent_uei` alone: **{len(multi_ult):,}**")
    A(f"- Distinct children carrying at least one ownership parent: **{len(parents_of):,}**")
    A(f"- Children recorded under **more than one** ownership parent: **{len(multi_parent_children):,}**")
    A("")
    A("The last figure matters for spiderweb attribution. A subsidiary can legitimately appear")
    A("under two parents because ownership changed hands (e.g. a firm sold from one ANC to")
    A("another) or because SAM restated the record. Both edges are emitted with their own")
    A("`first_year`/`last_year`, so resolve conflicts by the observation window and")
    A("`n_observations` rather than assuming a single parent.")
    A("")
    A("### 20 largest corporate families by distinct child count")
    A("")
    A("| # | parent_uei | parent_name | distinct children |")
    A("|---:|---|---|---:|")
    for i, (p, ch) in enumerate(top, 1):
        A("| {} | `{}` | {} | {:,} |".format(i, p, parent_names.get(p, "").replace("|", "/"), len(ch)))
    A("")
    A("Names shown are the **modal** name recorded for that UEI (the name appearing on the most")
    A(f"transaction rows). {len(multi_named):,} UEIs were recorded under more than one distinct")
    A("legal name across the corpus; no name was invented or normalized beyond whitespace trim.")
    A("")
    A("### CAUTION — federal registrants appear as ultimate parents")
    A("")
    if fed_parents:
        A("These parent UEIs carry the recorded parent name `GOVERNMENT OF THE UNITED STATES`.")
        A("They are federal registrant roll-ups (BIA, IHS, Army, tribally-controlled grant")
        A("schools filing under a federal umbrella), **not** corporate owners. Do NOT propagate")
        A("Native-entity ownership through them in the spiderweb step — a single one of these")
        A("would contaminate every child beneath it.")
        A("")
        A("| parent_uei | modal parent_name | distinct children |")
        A("|---|---|---:|")
        for p, n in fed_parents[:10]:
            A(f"| `{p}` | {parent_names.get(p,'')} | {n:,} |")
    else:
        A("None found in this run.")
    A("")
    A("## Comparison against the old derived graph")
    A("")
    A(f"Old graph: `data/raw/external/uei_hierarchy_graph.csv` — {old_rows:,} rows / nodes.")
    A("")
    A("| Metric | Old graph | This rebuild |")
    A("|---|---:|---:|")
    A(f"| Nodes (distinct UEIs) | {len(old_nodes):,} | {len(all_ueis):,} |")
    A(f"| Non-self ownership pairs | {len(old_pairs):,} | {len(new_pairs):,} |")
    A(f"| ... of which `parent_uei` | {len(old_by_type['parent_uei']):,} | {by_type.get('parent_uei',0):,} |")
    A(f"| ... of which `ultimate_parent_uei` | {len(old_by_type['ultimate_parent_uei']):,} | {by_type.get('ultimate_parent_uei',0):,} |")
    A("")
    A(f"- **NEW ownership pairs found by this rebuild (not in the old graph): {len(truly_new):,}**")
    A(f"- Ownership pairs in the old graph not reproduced here: {len(old_not_found):,}")
    A(f"- UEIs observed here that are absent from the old graph: {len(new_nodes):,}")
    A(f"- Old-graph UEIs not observed in these raw files: {len(old_nodes - all_ueis):,}")
    A("")
    A("The old graph's coverage gap is structural: it carried one row per node with a mostly")
    A("blank `parent_uei` and a self-referential `ultimate_parent_uei`, so it encoded almost no")
    A("edges. The rebuild reads the parent columns off every transaction, so a child is linked")
    A("to its parent whenever any single transaction recorded that parent.")
    A("")
    A("## UEI -> CAGE map")
    A("")
    A(f"`data/clean/fpds_uei_cage_map.csv` — {len(cages):,} distinct (uei, cage_code,")
    A("legal_business_name) triples.")
    A("")
    A(f"- Triples with a non-empty CAGE code: {nonempty_cage:,}")
    A(f"- Distinct UEIs with at least one CAGE code: {ueis_with_cage:,} of {len(all_ueis):,} observed UEIs")
    A("")
    A("Triples with a blank CAGE are retained deliberately: they document that FPDS observed the")
    A("UEI under that legal name but recorded no CAGE, which is itself a coverage fact. Filter on")
    A("`cage_code != ''` for a pure crosswalk.")
    A("")
    A("Legal names are stored exactly as recorded, including casing, so the same UEI+CAGE pair")
    A("can appear on more than one row (`HCI MANAGEMENT SERVICES COMPANY` vs `HCI Management")
    A("Services Company`). Join on `uei` (+ `cage_code`); treat the name as a label, not a key.")
    A("")
    A("## Outputs")
    A("")
    A("| Path | Rows |")
    A("|---|---:|")
    A(f"| `data/clean/fpds_uei_edges.csv` | {len(edges):,} |")
    A(f"| `data/clean/fpds_uei_cage_map.csv` | {len(cages):,} |")
    A("")
    A("Nothing under `data/spine/`, `data/clean/cedar_*`, or `review/` was read or modified.")
    A("")

    with open(BUILD_LOG_MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    log(f"wrote {BUILD_LOG_MD}")

    # console summary of top families
    log("")
    log("Top 20 corporate families by distinct child count:")
    for i, (p, ch) in enumerate(top, 1):
        log(f"  {i:2d}. {p}  {len(ch):6,d} children  {parent_names.get(p,'')}")
    log("")
    log(f"CAUTION: {len(fed_parents)} parent UEI(s) recorded as GOVERNMENT OF THE UNITED STATES "
        f"(federal registrant roll-ups, not owners) - do not propagate ownership through these:")
    for p, n in fed_parents[:10]:
        log(f"    {p}  {n:,} children  {parent_names.get(p,'')}")


# ---------------------------------------------------------------------------
def main() -> None:
    global _logfh
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="max rows per file (smoke test)")
    args = ap.parse_args()

    os.makedirs(LOGS, exist_ok=True)
    _logfh = open(LOG_PATH, "a", encoding="utf-8")

    t0 = time.time()
    log("=" * 72)
    log("13_build_fpds_hierarchy.py START" + (f"  (--limit {args.limit})" if args.limit else ""))
    log("=" * 72)

    for fname, spec in FILES:
        path = os.path.join(RAW, fname)
        if not os.path.exists(path):
            log(f"!! MISSING SOURCE FILE: {path}")
            per_file_stats.append(
                {"file": fname, "rows": 0, "bad_rows": 0, "short_rows": 0,
                 "parse_errors": 0, "edges_added": 0, "ueis": set()}
            )
            continue
        per_file_stats.append(stream_file(fname, spec, args.limit))

    write_edges(args.limit)
    write_cages(args.limit)
    build_report(t0)

    log(f"DONE in {(time.time()-t0)/60:.1f} minutes")
    _logfh.close()


if __name__ == "__main__":
    main()
