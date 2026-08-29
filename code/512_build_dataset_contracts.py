#!/usr/bin/env python3
"""
Cedar Press - 512: dataset BUILD CONTRACTS. Mission Phase 1.

    py -3 code/512_build_dataset_contracts.py           # generate + verify
    py -3 code/512_build_dataset_contracts.py verify    # read-only, exit 1 on breach

WHAT A CONTRACT IS
------------------
One machine-readable statement per collection of what the collection IS: which
tables it owns, who rebuilds each, who enriches each and in what order, which
key columns a consumer may join on, and which invariants must hold. The
mission spec's Phase 1, arriving after Phases 0/2/3 because those built the
facts this file merely assembles.

DERIVED, NOT DECLARED - THE DESIGN RULE
---------------------------------------
Almost nothing here is typed by hand, because this project has already paid
for hand-maintained registries three times (87/25/27 each had their own
universe and all three disagreed - see cedar_codebook.py). A contract field
is DERIVED from the system that already owns the fact:

    which tables exist per collection   500_build_architecture_map.COLLECTIONS
    shippable / internal / licensed     cedar_codebook (the ONE registry)
    who rebuilds, who enriches, order   cedar_pipeline.all_orderings (293 scan)
    key columns                         header intersection with the join keys
                                        25_build_publication_layer indexes
    never-run warnings                  cedar_pipeline.NEVER_RUN

The one DECLARED block is `GRAIN`, because a table's row-grain is a design
intention no scan can recover - and it is declared ONLY where an owner or a
build log has actually stated it. An unstated grain is recorded as unstated,
never guessed: a wrong grain in a contract is worse than a missing one,
because consumers write joins against it.

Writes
------
docs/schema/dataset_contracts.json    the contracts, machine-readable
docs/DATASET_CONTRACTS.md             the same, for humans
Both derived; regenerate rather than hand-edit.

`verify` re-derives everything and exits 1 when the world no longer satisfies
the contracts: a collection with zero tables, a shippable table no collection
claims (an ORPHAN - it would ship with no owner, no plan and no contract), a
rebuild script a contract names that no longer exists, or a declared key
column missing from a table's header. 62_no_regression_check gates on the
violation count in the JSON.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()

OUT_JSON = ROOT / "docs" / "schema" / "dataset_contracts.json"
OUT_MD = ROOT / "docs" / "DATASET_CONTRACTS.md"

import cedar_codebook as CB              # noqa: E402
import cedar_pipeline as CP              # noqa: E402
from build import TABLE_DIRS, _load_architecture, collection_tables  # noqa: E402

# Join keys a consumer may rely on, in preference order - the same list
# 25_build_publication_layer indexes, so the contract and the database agree.
JOIN_KEYS = ("tribe_id", "cedar_uid", "entity_id", "facility_id",
             "property_id", "compact_id", "uei", "ein", "cage_code",
             "administrative_region_id")

# ---------------------------------------------------------------------------
# DECLARED GRAIN - only where an owner ruling or a build log has stated it.
# The absence of a table here means its grain is UNSTATED, and the contract
# says so. Do not fill this in from a guess; that is the one way this file
# can lie.
# ---------------------------------------------------------------------------
GRAIN = {
    "cedar_entity_spine.csv":
        "one row per canonical Native entity (hub). Sub-hubs (registrations, "
        "facilities) are NEVER rows here - IDENTIFIER_STANDARD.md",
    "cedar_identity_register.csv":
        "one row per permanent cedar_uid, append-only, never re-minted",
    "cedar_identifier_ledger_final.csv":
        "one row per (identifier, entity, evidence) claim; tier X rows are "
        "REFUTATIONS and must not be dropped by consumers",
    "fpds_uei_edges.csv":
        "one row per DECLARED (child_uei, parent_uei, edge_type) - literal "
        "pairs observed on transactions; connections, not a verified tree",
    "federal_funding_transactions.csv":
        "one row per federal award transaction",
    "cedar_assertions.csv":
        "one row per (subject, predicate, object, source, polarity) claim - "
        "append-only",
    "cedar_resolved_facts.csv":
        "one row per (cedar_uid, predicate) for single-valued predicates; one "
        "per (cedar_uid, predicate, value) for multi-valued",
    "gaming_source_claims.csv":
        "one row per claim extracted from one source document",
}


def build_contracts():
    arch = _load_architecture()
    shippable, licensed, undocumented = CB.registered_tables()
    ship_names = {p.name for p, _, _ in shippable}
    lic_names = set(CB.LICENSED_SOURCE_FILES)
    int_names = set(CB.INTERNAL_TABLES)
    und_names = {p.name for p, _, _ in undocumented}

    def status_of(name):
        if name in lic_names:
            return "licensed-never-ships"
        if name in int_names:
            return "internal-by-decision"
        if name in ship_names:
            return "shippable"
        if name in und_names:
            return "UNDOCUMENTED"
        return "unregistered"

    headers = {}

    def header_of(name):
        if name not in headers:
            for d in TABLE_DIRS:
                p = ROOT / d / name
                if p.exists():
                    try:
                        with p.open(encoding="utf-8-sig", errors="replace",
                                    newline="") as fh:
                            headers[name] = next(csv.reader(fh), [])
                    except Exception:
                        headers[name] = []
                    break
            else:
                headers[name] = []
        return headers[name]

    contracts, violations = [], []
    claimed = set()

    for spec in arch.COLLECTIONS:
        cid = spec["id"]
        tables = collection_tables(arch, spec)
        claimed.update(tables)
        if not tables:
            violations.append(f"collection {cid} claims ZERO tables - its "
                              f"regex matches nothing on disk")
        rows = []
        for name in tables:
            hdr = [h.strip() for h in header_of(name)]
            keys = [k for k in JOIN_KEYS if k in hdr]
            orderings = CP.all_orderings(name)
            rebuilds = sorted({o.get("rebuild", "") for o in orderings
                               if o.get("rebuild")})
            enrichers = sorted({o.get("enricher", "") for o in orderings
                                if o.get("enricher")})
            for s in rebuilds + enrichers:
                # 293's io map records scripts by BARE NAME wherever they live
                # under code/ (lobbying_pull/05_match_filings_v2.py appears as
                # 05_match_filings_v2.py). Resolve recursively; the first
                # version checked only the top level and reported two live
                # scripts as missing.
                if s and not (HERE / s).exists()                         and not list(HERE.glob(f"*/{s}")):
                    violations.append(f"{name}: ordering names {s}, which "
                                      f"does not exist anywhere under code/")
            never = [s for s in rebuilds if s in CP.NEVER_RUN]
            rows.append(dict(
                table=name,
                status=status_of(name),
                key_columns=keys,
                grain=GRAIN.get(name, "UNSTATED - no owner ruling or build "
                                      "log has declared this table's grain"),
                rebuilt_by=rebuilds,
                enriched_by=enrichers,
                never_run_warning=[
                    f"{s}: {CP.NEVER_RUN[s][:120]}..." for s in never],
            ))
        contracts.append(dict(
            collection=cid,
            name=spec.get("name", ""),
            shelf=spec.get("shelf", ""),
            rebuild_command=f"py -3 code/build.py run {cid} --execute",
            n_tables=len(tables),
            tables=rows,
        ))

    # ORPHANS: shippable tables no collection claims. These would ship with
    # no owner, no plan and no contract - the exact gap that let 47 gaming
    # tables ship at 0.87% coverage before the codebook registry existed.
    orphans = sorted(ship_names - claimed)
    for o in orphans:
        violations.append(f"ORPHAN shippable table: {o} - registered in the "
                          f"codebook but claimed by NO collection")

    return dict(
        built_date=TODAY,
        derivation="500.COLLECTIONS + cedar_codebook + cedar_pipeline; "
                   "GRAIN declared, everything else derived",
        n_collections=len(contracts),
        n_tables_claimed=len(claimed),
        n_orphan_shippable=len(orphans),
        orphans=orphans,
        n_violations=len(violations),
        violations=violations,
        contracts=contracts,
    )


def write_md(doc):
    L = ["# Dataset contracts - generated, do not hand-edit",
         "",
         f"*Generated {doc['built_date']} by `code/512_build_dataset_contracts.py`"
         f" (mission Phase 1). Regenerate rather than edit; `verify` exits 1 "
         f"when the world breaks a contract, and 62 gates on it.*",
         "",
         f"**{doc['n_collections']} collections, {doc['n_tables_claimed']} "
         f"tables claimed, {doc['n_orphan_shippable']} orphaned shippable "
         f"tables, {doc['n_violations']} violations.**",
         ""]
    if doc["violations"]:
        L.append("## VIOLATIONS - the contract the world currently breaks")
        L.append("")
        for v in doc["violations"]:
            L.append(f"- {v}")
        L.append("")
    for c in doc["contracts"]:
        L.append(f"## {c['name']}  (`{c['collection']}`, shelf: {c['shelf'] or '-'})")
        L.append("")
        L.append(f"Rebuild: `{c['rebuild_command']}` — {c['n_tables']} tables.")
        L.append("")
        L.append("| table | status | keys | rebuilt by | enriched by |")
        L.append("|---|---|---|---|---|")
        for t in c["tables"]:
            L.append("| `{}` | {} | {} | {} | {} |".format(
                t["table"], t["status"],
                " ".join(f"`{k}`" for k in t["key_columns"]) or "—",
                " ".join(f"`{s}`" for s in t["rebuilt_by"]) or "—",
                " ".join(f"`{s}`" for s in t["enriched_by"]) or "—"))
        L.append("")
        stated = [t for t in c["tables"] if not t["grain"].startswith("UNSTATED")]
        if stated:
            L.append("Declared grain:")
            L.append("")
            for t in stated:
                L.append(f"- `{t['table']}` — {t['grain']}")
            L.append("")
        warned = [t for t in c["tables"] if t["never_run_warning"]]
        for t in warned:
            for w in t["never_run_warning"]:
                L.append(f"> **NEVER RUN** for `{t['table']}`: {w}")
                L.append("")
    OUT_MD.write_text("\n".join(L), encoding="utf-8")


def main() -> int:
    verify_only = len(sys.argv) > 1 and sys.argv[1] == "verify"
    doc = build_contracts()
    if not verify_only:
        OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        OUT_JSON.write_text(json.dumps(doc, indent=1), encoding="utf-8")
        write_md(doc)
        print(f"  wrote {OUT_JSON.relative_to(ROOT)} and "
              f"{OUT_MD.relative_to(ROOT)}")
    print(f"  {doc['n_collections']} collections, "
          f"{doc['n_tables_claimed']} tables claimed, "
          f"{doc['n_orphan_shippable']} orphan shippable, "
          f"{doc['n_violations']} violations")
    for v in doc["violations"][:15]:
        print(f"    !! {v}")
    if doc["n_violations"] and len(doc["violations"]) > 15:
        print(f"    ... and {len(doc['violations']) - 15} more")
    return 1 if doc["n_violations"] else 0


if __name__ == "__main__":
    sys.exit(main())
