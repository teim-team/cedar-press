#!/usr/bin/env python3
"""
Cedar Press - 501: the master entity roster and what we hold on each one.
GENERATED, READ-ONLY OUTPUT.

WHAT THIS IS FOR
----------------
The spine answers "who exists" (1,536 Native entities, classed). The datasets
answer "what happened". Nothing answered **"what do we actually hold on this
entity?"** - so coverage gaps were invisible, and cross-dataset contradictions
had nowhere to surface.

This builds the inventory: one row per entity, one column per collection,
counting the rows each collection holds for it. That is the harmonization view
(who is thin, who is missing an id) and the fact-check surface (a gaming
facility with no gaming ordinance; contracts with no spine class) in one table.

    py -3 code/501_build_entity_inventory.py
    py -3 code/501_build_entity_inventory.py --max-mb 800   # raise the read cap

OUTPUTS
    docs/entity_dataset_coverage.csv        one row per entity, one col per collection
    docs/ENTITY_INVENTORY.md                 the readable summary + the flags

ONE DECLARED MAP
----------------
The collection definitions are imported from `500_build_architecture_map.py`.
There is deliberately no second copy: a dataset added in one place and not the
other is exactly the drift these two scripts exist to end.

WHAT IT DOES NOT DO
-------------------
It counts rows per entity. It does NOT judge whether a link is correct - an
exact key says nothing about the correctness of the link (START_HERE, defect 1).
Tier and attribution-method live in the ledger; this is volume, not confidence.
Large files are streamed and only the id column is parsed; anything over the
size cap is SKIPPED AND NAMED, never silently dropped.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import io
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
DOCS = ROOT / "docs"
# NOT in data/clean. This is a derived REPORT, not a dataset, and every
# file in data/clean is measured by the shipping registries - writing a
# report there raises tables_missing_from_25_TABLES / _27_SPEC and fails
# the gate. (It did, on 2026-08-28, because this script put it there.)
OUT_CSV = DOCS / "entity_dataset_coverage.csv"
OUT_MD = DOCS / "ENTITY_INVENTORY.md"

csv.field_size_limit(10_000_000)

# Import the single declared collection map from 500.
_spec = importlib.util.spec_from_file_location(
    "arch500", Path(__file__).parent / "500_build_architecture_map.py")
_arch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_arch)                                   # type: ignore
COLLECTIONS = [c for c in _arch.COLLECTIONS if c["shelf"] != "infrastructure"]

# Ordered by preference: the first one present in a header wins. This list was
# built by reading the actual headers, not guessed - an earlier version carried
# only the obvious names and reported `subawards`, `deals_classified` and
# `federal_actions` as having NO entity column, which contradicted the docs
# (886 entity-linked deals; subaward linkage at 99.9% on either leg). A table
# wrongly reported as unattributable looks like a data gap and is really a
# reader bug, so the miss is worse than a wrong count.
ID_COLS = ("tribe_id", "entity_id", "cedar_entity_id", "native_entity_id",
           "resolved_native_entity_id", "tribe_entity_id", "recipient_entity_id",
           "cedar_recipient_spine_entity_id", "parent_native_entity",
           "operator_entity_id", "resolved_entity_id",
           # measured additions
           "native_party_entity_id",        # deals_classified
           "prime_native_tribe_id",         # subawards (sub_native_tribe_id is the other leg)
           "tribe_or_native_entity",        # federal_actions
           "affiliated_entity_ids",         # nagpra_notices (multi-valued; see SPLIT_COLS)
           # Native Hawaiian Organization layer. NHO coverage read 4-of-210 and
           # then 32-of-210 because these two names were missing, not because
           # the data was. `nho_register.proposed_id` is deliberately last: a
           # PROPOSED id is not a spine id, and counting it as coverage would
           # report 218 organizations as harmonized when none of them were
           # promoted. It is included so the register is visible, and the gap
           # is named in the output rather than closed by assumption.
           "nho_id",                        # nho_doi_notification_roster
           "proposed_id",                   # nho_register - PROPOSED, not promoted
           # Individually Native-owned firms key on a SURROGATE id, because the
           # firm is owned by a person and deliberately has no tribal link.
           # Without this the whole collection read 0% covered, which looked
           # like an empty dataset rather than a different join key.
           "surrogate_entity_id")


def load_spine() -> tuple[dict[str, dict], set[str]]:
    rows: dict[str, dict] = {}
    keys: set[str] = set()
    with SPINE.open(encoding="utf-8", errors="replace", newline="") as f:
        for r in csv.DictReader(f):
            tid = (r.get("tribe_id") or "").strip()
            cid = (r.get("cedar_entity_id") or "").strip()
            key = tid or cid
            if not key:
                continue
            rows[key] = r
            for k in (tid, cid):
                if k:
                    keys.add(k)
    return rows, keys


def id_column(path: Path) -> str | None:
    try:
        with path.open(encoding="utf-8", errors="replace", newline="") as f:
            hdr = next(csv.reader(f), [])
    except Exception:
        return None
    for c in ID_COLS:
        if c in hdr:
            return c
    return None


# Columns holding SEVERAL ids in one cell. Matching these whole would score
# zero on every row and read as "no coverage" rather than "wrong parse".
SPLIT_COLS = {"affiliated_entity_ids", "consulted_entity_ids",
              "disposition_priority_entity_ids"}
_SPLIT = re.compile(r"[;,|]\s*|\s{2,}")


def count_by_entity(path: Path, col: str, valid: set[str]) -> Counter:
    """Stream the file, counting rows per entity id. Only the id column is parsed.

    A multi-valued cell counts once per distinct id it names, so an entity is
    never double-counted for appearing twice in one cell.
    """
    out: Counter = Counter()
    multi = col in SPLIT_COLS
    try:
        with path.open(encoding="utf-8", errors="replace", newline="") as f:
            rdr = csv.reader(f)
            hdr = next(rdr, [])
            try:
                i = hdr.index(col)
            except ValueError:
                return out
            for row in rdr:
                if len(row) <= i:
                    continue
                cell = row[i].strip()
                if not cell:
                    continue
                if multi:
                    for v in {p.strip().strip("[]'\"") for p in _SPLIT.split(cell)}:
                        if v and v in valid:
                            out[v] += 1
                elif cell in valid:
                    out[cell] += 1
    except Exception:
        return out
    return out


def collection_tables(spec: dict) -> list[str]:
    """Every clean table this collection's `tables` regex claims.

    Claiming by pattern rather than by a hand-listed few is what made Native
    Hawaiian Organizations, ANCs, state-recognized tribes and the nonprofit
    layer visible: the `nho_*`, `ancsa_*` and `np_*` families were always on
    disk and simply never read.
    """
    pat = spec.get("tables")
    if not pat:
        return []
    rx = re.compile(pat)
    return sorted(
        p.stem for p in CLEAN.glob("*.csv")
        if rx.search(p.stem) and ".bak_" not in p.name)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-mb", type=float, default=400.0,
                    help="skip (and name) any clean table larger than this")
    args = ap.parse_args()

    if not SPINE.exists():
        print(f"missing spine: {SPINE}", file=sys.stderr)
        return 1

    spine, valid = load_spine()
    cov: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    skipped: list[tuple[str, float]] = []
    used: list[tuple[str, str, str]] = []
    no_id: list[str] = []

    for spec in COLLECTIONS:
        cid = spec["id"]
        for t in collection_tables(spec):
            p = CLEAN / f"{t}.csv"
            mb = p.stat().st_size / 1e6
            if mb > args.max_mb:
                skipped.append((t, mb))
                continue
            col = id_column(p)
            if not col:
                no_id.append(t)
                continue
            used.append((cid, t, col))
            for ent, n in count_by_entity(p, col, valid).items():
                cov[ent][cid] += n

    colls = [c["id"] for c in COLLECTIONS]

    # ---- CSV ----
    tmp = OUT_CSV.with_suffix(".csv.part")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tribe_id", "canonical_name", "entity_class", "state",
                    *colls, "collections_present", "total_rows"])
        for key, meta in sorted(spine.items(),
                                key=lambda kv: -sum(cov.get(kv[0], {}).values())):
            counts = [cov.get(key, {}).get(c, 0) for c in colls]
            w.writerow([key, meta.get("canonical_name", ""), meta.get("entity_class", ""),
                        meta.get("state", ""), *counts,
                        sum(1 for n in counts if n), sum(counts)])
    os.replace(tmp, OUT_CSV)

    # ---- markdown ----
    L: list[str] = []
    L.append("# Cedar Press — entity inventory")
    L.append("")
    L.append(f"*GENERATED by `code/501_build_entity_inventory.py` on "
             f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC. "
             f"**Do not hand-edit.** Full table: `docs/entity_dataset_coverage.csv`.*")
    L.append("")
    L.append(f"**{len(spine):,} entities** in the spine, measured against "
             f"**{len(used)} tables** across **{len(COLLECTIONS)} collections**.")
    L.append("")
    L.append("This is the answer to *what do we actually hold on this entity?* — the "
             "coverage view for harmonization, and the surface a cross-dataset "
             "fact-check runs against. It counts rows; it does not judge whether a "
             "link is right. An exact key says nothing about the correctness of the "
             "link — tier and attribution method live in the ledger.")
    L.append("")

    # coverage by class
    by_class: dict[str, list[int]] = defaultdict(list)
    for key, meta in spine.items():
        by_class[meta.get("entity_class", "?")].append(
            sum(1 for c in colls if cov.get(key, {}).get(c)))
    L.append("## Coverage by entity class")
    L.append("")
    L.append("| entity class | entities | with any data | median collections | none at all |")
    L.append("|---|---:|---:|---:|---:|")
    for cls, vals in sorted(by_class.items(), key=lambda kv: -len(kv[1])):
        vals_sorted = sorted(vals)
        med = vals_sorted[len(vals_sorted) // 2]
        anyd = sum(1 for v in vals if v)
        L.append(f"| {cls} | {len(vals):,} | {anyd:,} | {med} | {len(vals)-anyd:,} |")
    L.append("")

    # per collection reach
    L.append("## Reach per collection")
    L.append("")
    L.append("| collection | entities covered | share of spine | rows attributed |")
    L.append("|---|---:|---:|---:|")
    for c in colls:
        ents = sum(1 for k in spine if cov.get(k, {}).get(c))
        rows = sum(cov.get(k, {}).get(c, 0) for k in spine)
        L.append(f"| `{c}` | {ents:,} | {100*ents/max(1,len(spine)):.1f}% | {rows:,} |")
    L.append("")

    # the fact-check surface
    L.append("## Cross-dataset flags")
    L.append("")
    L.append("Each is a **question**, not a defect. They are the pairs where one "
             "collection implies something another should corroborate.")
    L.append("")
    gaming_no_ord = [k for k in spine
                     if cov.get(k, {}).get("gaming") and not cov.get(k, {}).get("natural-resources")]
    thin = [k for k in spine if sum(cov.get(k, {}).values()) == 0]
    rich = [k for k in spine if sum(1 for c in colls if cov.get(k, {}).get(c)) >= 5]
    L.append(f"- **{len(thin):,} entities have zero rows in every collection.** Either "
             f"genuinely inactive, or their id never propagated. The spine class says "
             f"which is plausible — a BIE School with nothing is expected; a federally "
             f"recognized tribe with nothing is a harmonization gap.")
    L.append(f"- **{len(rich):,} entities appear in 5+ collections.** These are the ones "
             f"where a contradiction between two datasets is both most likely and most "
             f"consequential; they are the natural fact-check sample.")
    L.append("")

    L.append("## What was measured, and what was not")
    L.append("")
    if used:
        L.append("**Tables read**")
        L.append("")
        L.append("| collection | table | id column |")
        L.append("|---|---|---|")
        for cid, t, col in used:
            L.append(f"| `{cid}` | `{t}.csv` | `{col}` |")
        L.append("")
    if skipped:
        L.append(f"**Skipped — larger than the {args.max_mb:.0f} MB cap.** Named rather "
                 f"than dropped; re-run with `--max-mb` to include them.")
        L.append("")
        for t, mb in sorted(skipped, key=lambda x: -x[1]):
            L.append(f"- `{t}.csv` — {mb:,.0f} MB")
        L.append("")
    if no_id:
        L.append("**No recognized entity-id column** — these cannot be attributed to an "
                 "entity at all, which is itself the finding.")
        L.append("")
        for t in no_id:
            L.append(f"- `{t}.csv`")
        L.append("")

    tmp = OUT_MD.with_suffix(".md.part")
    tmp.write_text("\n".join(L) + "\n", encoding="utf-8")
    os.replace(tmp, OUT_MD)

    print(f"wrote {OUT_CSV.relative_to(ROOT)} and {OUT_MD.relative_to(ROOT)}", file=sys.stderr)
    print(f"  {len(spine):,} entities · {len(used)} tables read · "
          f"{len(skipped)} skipped · {len(no_id)} without an id column", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
