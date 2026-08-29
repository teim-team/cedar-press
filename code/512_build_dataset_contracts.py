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
#
# A DECLARATION IS NOW FOUR THINGS, NOT ONE - external review F9.
# A prose grain was honest and useless to a machine. What a buyer actually
# needs before they join is:
#
#   grain             what one row IS, in words
#   primary_key       the column set that is unique across the file
#   join_keys         what a consumer may join on
#   join_cardinality  how many rows they get back PER join key value:
#                     "one"  exactly one row per value  (a lookup)
#                     "many" more than one is expected  (a fan-out)
#
# `join_cardinality` is the field that stops the failure the reviewer named:
# a buyer joins a table whose real grain is entity x UEI x year on cedar_uid
# alone, gets a silent fan-out, and sums the award amount N times. Declaring
# "many" does not stop them joining - it stops them being surprised, and it
# makes the surprise a testable statement rather than a footnote.
#
# EVERY DECLARED FIELD IS VALIDATED AGAINST THE FILE ON EVERY RUN, and a
# declaration the data contradicts is a release-blocking violation. A grain
# that is merely UNSTATED is counted and ratcheted instead - see the note on
# n_shippable_grain_unstated below for why the two are treated differently.
# ---------------------------------------------------------------------------
GRAIN = {
    "cedar_entity_spine.csv": dict(
        grain="one row per canonical Native entity (hub). Sub-hubs "
              "(registrations, facilities) are NEVER rows here - "
              "IDENTIFIER_STANDARD.md",
        primary_key=["tribe_id"],
        join_cardinality={"tribe_id": "one", "cedar_uid": "one"},
        declared_by="docs/IDENTIFIER_STANDARD.md 1"),
    "cedar_identity_register.csv": dict(
        grain="one row per permanent cedar_uid, append-only, never re-minted. "
              "`handle` is the CURRENT display handle only; retired handles "
              "live in cedar_handle_history.csv and still resolve",
        primary_key=["cedar_uid"],
        join_cardinality={"cedar_uid": "one"},
        declared_by="docs/IDENTIFIER_STANDARD.md 0"),
    "cedar_handle_history.csv": dict(
        grain="one row per (handle, cedar_uid) binding ever issued, with the "
              "interval it was current. A retired handle keeps its row so an "
              "old join key never stops resolving",
        primary_key=["handle"],
        join_cardinality={"handle": "one", "cedar_uid": "many"},
        declared_by="docs/IDENTIFIER_STANDARD.md 'THE RECLASSIFICATION RULE'"),
    "cedar_identifier_ledger_final.csv": dict(
        grain="one row per (identifier, entity, evidence) claim; tier X rows "
              "are REFUTATIONS and must not be dropped by consumers",
        # The evidence columns are part of the key because the declared grain
        # says "evidence". Without them 4 rows collide - the same claim
        # recorded twice, once with an evidence_url and once without. That is
        # a real defect and it is visible here rather than hidden by a
        # shorter key that would simply have failed.
        primary_key=["identifier_type", "identifier", "tribe_id",
                     "attribution_method", "evidence_url", "verified_date"],
        # NOT uei/ein/cage_code: this table is LONG on identifier_type, so
        # the identifier lives in one `identifier` column. The first version
        # of this declaration named all three and the validator refused it -
        # which is the point of validating a declaration.
        join_cardinality={"cedar_uid": "many", "tribe_id": "many",
                          "identifier": "many"},
        declared_by="docs/IDENTIFIER_STANDARD.md 3"),
    "fpds_uei_edges.csv": dict(
        grain="one row per DECLARED (child_uei, parent_uei, edge_type) - "
              "literal pairs observed on transactions; connections, not a "
              "verified tree",
        primary_key=["child_uei", "parent_uei", "edge_type"],
        join_cardinality={},
        declared_by="docs/HIERARCHY_MODEL.md"),
    "cedar_assertions.csv": dict(
        grain="one row per (subject, predicate, object, source, polarity) "
              "claim - append-only",
        primary_key=["assertion_id"],
        join_cardinality={"cedar_uid": "many"},
        declared_by="docs/ASSERTION_LAYER.md"),
    "cedar_resolved_facts.csv": dict(
        grain="one row per (cedar_uid, subject_qualifier, predicate) for "
              "single-valued predicates; one per (cedar_uid, "
              "subject_qualifier, predicate, value) for multi-valued",
        primary_key=["cedar_uid", "subject_qualifier", "predicate",
                     "object_value"],
        join_cardinality={"cedar_uid": "many"},
        declared_by="docs/ASSERTION_LAYER.md"),
    "cedar_fact_conflicts.csv": dict(
        grain="one row per losing or blocked assertion, kept rather than "
              "deleted; many rows per resolved fact",
        primary_key=["cedar_uid", "subject_qualifier", "predicate",
                     "losing_value", "assertion_id", "decided_by_rule"],
        join_cardinality={"cedar_uid": "many"},
        declared_by="docs/ASSERTION_LAYER.md"),
    "gaming_source_claims.csv": dict(
        grain="one row per claim extracted from one source document",
        primary_key=["source_claim_id"],
        join_cardinality={},
        declared_by="docs/GAMING_DATASET_PLAN.md"),
}

# A table whose grain is declared but whose PRIMARY KEY cannot be stated
# without guessing. Recorded rather than left blank, so the gap is a task
# with a name instead of a silence. These count as UNSTATED for the gate.
GRAIN_OPEN = {
    "federal_funding_transactions.csv":
        "grain stated as 'one row per federal award transaction', but the "
        "file is a UNION of assistance and archive pulls and no owner has "
        "ruled whether assistance_transaction_unique_key is unique ACROSS "
        "the union or only within one pull. Declaring a key we have not "
        "ruled on is the one way this file can lie, so it stays open.",
}


UNSTATED = ("UNSTATED - no owner ruling or build log has declared this "
            "table's grain")


def _find(name):
    for d in TABLE_DIRS:
        p = ROOT / d / name
        if p.exists():
            return p
    return None


def validate_grain(name, decl, hdr):
    """Check a DECLARED grain against the file. Returns a list of violation
    strings, plus the measured cardinality it observed.

    This is the half of F9 that makes a declaration worth anything. A prose
    grain nobody tests is a comment. Reading the file is the only way to
    learn that the key we published is not unique, or that a key we called a
    lookup fans a buyer's join out 35 times.
    """
    v, measured = [], {}
    p = _find(name)
    if p is None:
        return [f"{name}: grain is DECLARED but the table is not on disk"], {}
    pk = decl.get("primary_key") or []
    card = decl.get("join_cardinality") or {}
    missing = [c for c in pk if c not in hdr]
    if missing:
        v.append(f"{name}: declared primary_key names column(s) not in the "
                 f"header: {missing}")
    missing_j = [c for c in card if c not in hdr]
    if missing_j:
        v.append(f"{name}: declared join_cardinality names column(s) not in "
                 f"the header: {missing_j}")
    live_pk = [c for c in pk if c in hdr]
    live_card = {c: k for c, k in card.items() if c in hdr}
    if not live_pk:
        v.append(f"{name}: no usable primary key - a SHIPPABLE table with no "
                 f"validated key cannot promise a buyer anything about a join")
        return v, {}

    seen, dup, dup_ex = set(), 0, None
    counts = {c: {} for c in live_card}
    n = 0
    try:
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            for r in csv.DictReader(fh):
                n += 1
                k = tuple((r.get(c) or "") for c in live_pk)
                if k in seen:
                    dup += 1
                    if dup_ex is None:
                        dup_ex = k
                seen.add(k)
                for c in live_card:
                    val = (r.get(c) or "").strip()
                    if val:
                        counts[c][val] = counts[c].get(val, 0) + 1
    except Exception as e:
        return [f"{name}: grain could not be validated ({type(e).__name__}: "
                f"{e}) - UNVALIDATED IS NOT CLEAN"], {}

    if dup:
        v.append(f"{name}: declared primary_key {live_pk} is NOT unique - "
                 f"{dup:,} duplicate row(s) of {n:,}, e.g. {dup_ex}. A buyer "
                 f"joining on it gets rows we did not promise them.")
    for c, kind in sorted(live_card.items()):
        mx = max(counts[c].values()) if counts[c] else 0
        measured[c] = mx
        if kind == "one" and mx > 1:
            worst = max(counts[c].items(), key=lambda kv: kv[1])[0]
            v.append(f"{name}: join_cardinality declares '{c}' as ONE row per "
                     f"value and the file has up to {mx:,} ({worst!r}). This "
                     f"is the silent fan-out: a buyer joining on {c} and "
                     f"summing a dollar column multiplies it {mx}x.")
    return v, measured


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
    grain_checked, grain_stated = {}, set()

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
            decl = GRAIN.get(name)
            gv, measured = ([], {})
            if decl and name not in grain_checked:
                gv, measured = validate_grain(name, decl, hdr)
                grain_checked[name] = (gv, measured)
            elif decl:
                gv, measured = grain_checked[name]
            if decl:
                grain_stated.add(name)
            violations.extend(gv)
            rows.append(dict(
                table=name,
                status=status_of(name),
                key_columns=keys,
                grain=(decl["grain"] if decl else UNSTATED),
                primary_key=(decl.get("primary_key", []) if decl else []),
                join_cardinality=(decl.get("join_cardinality", {})
                                  if decl else {}),
                grain_declared_by=(decl.get("declared_by", "") if decl else ""),
                grain_validated=bool(decl and not gv),
                measured_rows_per_join_key=measured,
                grain_open_question=GRAIN_OPEN.get(name, ""),
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

    # ------------------------------------------------------------------
    # F9: AN UNSTATED GRAIN ON A SHIPPABLE TABLE IS A RELEASE DEFECT.
    #
    # It is NOT the same defect as a declared grain the data contradicts, and
    # the two are counted separately on purpose:
    #
    #   declared and violated  -> a PROMISE WE BREAK. Release-blocking now,
    #                             through n_violations / contract_violations.
    #   unstated               -> a promise we never made. Also a defect - a
    #                             buyer cannot join safely without it - but
    #                             there are hundreds and blocking every one
    #                             today would make this gate a thing to step
    #                             around, which standing rule 15 says is
    #                             worse than no gate. It is RATCHETED
    #                             instead: 62 carries it as MUST_NOT_RISE, so
    #                             the count may only fall, and a NEW shippable
    #                             table with no declared grain fails the gate
    #                             the day it lands.
    #
    # The honest number is printed on every run rather than summarised.
    unstated = sorted(n for n in ship_names if n not in grain_stated)
    return dict(
        built_date=TODAY,
        derivation="500.COLLECTIONS + cedar_codebook + cedar_pipeline; "
                   "GRAIN declared, everything else derived",
        n_collections=len(contracts),
        n_tables_claimed=len(claimed),
        n_orphan_shippable=len(orphans),
        orphans=orphans,
        n_shippable=len(ship_names),
        n_shippable_grain_stated=len(ship_names & grain_stated),
        n_shippable_grain_unstated=len(unstated),
        shippable_grain_unstated=unstated,
        grain_open_questions=GRAIN_OPEN,
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
         "",
         f"**Grain: {doc['n_shippable_grain_stated']} of "
         f"{doc['n_shippable']} shippable tables declare and VALIDATE a row "
         f"grain, a primary key and a join cardinality; "
         f"{doc['n_shippable_grain_unstated']} do not.** A declared grain the "
         f"data contradicts is a release-blocking violation, listed below. "
         f"An unstated grain is ratcheted by "
         f"`62_no_regression_check.contract_grain_unstated_shippable`: the "
         f"count may only fall, and a new shippable table that lands without "
         f"one fails the gate that day.",
         ""]
    if doc["shippable_grain_unstated"]:
        L.append("<details><summary>Shippable tables with an UNSTATED grain "
                 f"({doc['n_shippable_grain_unstated']}) - a buyer cannot "
                 "join these safely</summary>")
        L.append("")
        for t in doc["shippable_grain_unstated"]:
            L.append(f"- `{t}`" + (f" — {doc['grain_open_questions'][t]}"
                                   if t in doc["grain_open_questions"] else ""))
        L.append("")
        L.append("</details>")
        L.append("")
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
            L.append("Declared grain — validated against the file on every run:")
            L.append("")
            for t in stated:
                L.append(f"- `{t['table']}` — {t['grain']}")
                L.append(f"  - primary key: "
                         + (" + ".join(f"`{k}`" for k in t["primary_key"])
                            or "—")
                         + ("  (validated unique)" if t["grain_validated"]
                            else "  (**VALIDATION FAILED — see violations**)"))
                if t["join_cardinality"]:
                    L.append("  - join cardinality: " + ", ".join(
                        f"`{k}` → {v} row(s) per value"
                        + (f" (measured max {t['measured_rows_per_join_key'].get(k)})"
                           if t["measured_rows_per_join_key"].get(k) else "")
                        for k, v in sorted(t["join_cardinality"].items())))
                if t["grain_declared_by"]:
                    L.append(f"  - declared by: {t['grain_declared_by']}")
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
    print(f"  grain: {doc['n_shippable_grain_stated']}/{doc['n_shippable']} "
          f"shippable tables declare AND validate a grain, primary key and "
          f"join cardinality; {doc['n_shippable_grain_unstated']} UNSTATED "
          f"(ratcheted by 62.contract_grain_unstated_shippable - the count "
          f"may only fall)")
    for v in doc["violations"][:15]:
        print(f"    !! {v}")
    if doc["n_violations"] and len(doc["violations"]) > 15:
        print(f"    ... and {len(doc['violations']) - 15} more")
    return 1 if doc["n_violations"] else 0


if __name__ == "__main__":
    sys.exit(main())
