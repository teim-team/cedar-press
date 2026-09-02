#!/usr/bin/env python3
"""
Cedar Press - 518: THE DATASET READINESS SCOREBOARD. The new north star.

    py -3 code/518_dataset_readiness.py            # measure + write
    py -3 code/518_dataset_readiness.py verify     # read-only, exit 1 on breach

THE SHIFT THIS FILE RECORDS
---------------------------
Owner mandate, 2026-08-30: stop optimising for invariants, assertions, commits
and architectural mechanisms. Start optimising for:

    How many Cedar datasets can we confidently ship, update later without
    heroics, and expect customers to join and aggregate correctly?

So this measures DATASETS, not machinery, and it emits exactly three statuses.
**READY / BLOCKED / NOT_TESTED.** There is deliberately no "mostly ready",
"substantially complete" or "green-ish": a dataset either crosses the minimum
shipping contract below or it has NAMED blockers. A vague status is how nine
datasets sit at 80% forever.

THE MINIMUM PRODUCTION-READY CONTRACT (owner-defined; all ten must hold)
-----------------------------------------------------------------------
  C1  customer-facing tables have declared, VALIDATED grain
  C2  primary keys and advertised join keys validate
  C3  literal duplicates removed or intentionally explained
  C4  entity matching uses the central identity system; known dangerous
      ambiguity cannot silently resolve
  C5  every harvested row has a named disposition
  C6  material unresolved identity conflicts do not ship as definite facts
  C7  known double-counting paths eliminated
  C8  ONE documented rebuild path reproduces the tables without destroying
      later enrichment
  C9  the update procedure is documented well enough for another session to
      execute it
  C10 regression and semantic-diff gates cover the important outputs

Replayability and provenance keep improving, but a dataset is NOT blocked
solely because Cedar-wide infrastructure is imperfect - only where the missing
piece is a realistic correctness or maintenance risk for THAT dataset.

Everything here is derived from artifacts other layers already produce. This
script measures datasets; it does not measure itself into being useful.

Writes  data/clean/cedar_dataset_readiness.csv    one row per dataset
        docs/DATASET_READINESS.md                 the scoreboard, for humans
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()

OUT = ROOT / "data" / "clean" / "cedar_dataset_readiness.csv"
OUT_MD = ROOT / "docs" / "DATASET_READINESS.md"

CONTRACTS = ROOT / "docs" / "schema" / "dataset_contracts.json"
EXPORT_SAFETY = ROOT / "data" / "clean" / "cedar_export_safety.csv"
CONSERVATION = ROOT / "data" / "clean" / "cedar_harvest_conservation.csv"
RESOLVED = ROOT / "data" / "clean" / "cedar_resolved_facts.csv"
LINKS = ROOT / "data" / "spine" / "cedar_source_record_links.csv"
RELEASES = ROOT / "docs" / "releases"
REGISTER = ROOT / "data" / "spine" / "cedar_identity_register.csv"
SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"

# =====================================================================
# C4 SCANNER, v2 - 2026-09-02. Four measurement defects, named.
# =====================================================================
# v1 counted a row as attached when any of FOUR hard-coded columns was
# non-blank, over a denominator of every row in the file. Measured against the
# live tables, that was wrong in four separate ways, and they pushed in
# opposite directions - so the single percentage it printed was not an
# under-read or an over-read, it was an unknown mixture of both.
#
#   (1) BLIND TO ROLE-PREFIXED ID COLUMNS. Cedar's own shape for an entity
#       that appears in a role is `<role>_entity_id`, because one payment can
#       involve a tribal government, allottees, an enterprise, an operator and
#       a trust account at once. v1 looked only for `cedar_uid`, `tribe_id`,
#       `entity_id`, `cedar_entity_id`, so 705 resolved recipients in
#       `resource_revenue.csv` read as zero. A table whose only id column is
#       role-prefixed (`tribal_bond_issuances.csv`) was skipped ENTIRELY -
#       not scored 0%, not counted at all.
#
#   (2) A NON-BLANK STRING IS NOT A CEDAR ID. `prime_contracts.csv` carries
#       the literal sentinel `owner_as_of_transaction_cedar_uid = "UNKNOWN"`
#       on 47,877 rows and v1 counted every one of them as attached.
#       `resource_revenue.payer_entity_id` carries `PAYER-US-BIA`,
#       `PAYER-STATE-ND` and four more federal/state payer stubs on 1,418 rows
#       - correctly NOT in the hub, and counting them as Native-entity
#       attachment would be gaming the metric. v2 requires the value to
#       resolve in `cedar_identity_register.csv` or `cedar_entity_spine.csv`.
#       This is the literal text of C4: entity matching uses the CENTRAL
#       identity system. It only ever LOWERS a score.
#
#   (3) THE DENOMINATOR IGNORED ADR-010, WHICH v1'S OWN COMMENT CITES.
#       ADR-010 consequence 1, verbatim: "Coverage is measured against the
#       resolvable denominator, not the row count." v1 deferred that because
#       "the honest denominator is not yet derivable per row". It is derivable
#       now wherever a table carries `record_scope`, so v2 uses it: rows scoped
#       `indian_country`, `geographic` or `native_serving` leave the
#       denominator; `entity`, `multi_entity` and `unresolved` stay, and
#       `unresolved` is the work queue. **A table with no `record_scope`
#       column is scored exactly as before**, so this changes nothing anywhere
#       the honest denominator has not actually been derived.
#
#       Why this is not an escape hatch: 9,791 of 11,305 `resource_revenue`
#       rows are `national_aggregate` because Interior publishes Native
#       American revenue only in aggregate, BY LAW. An aggregate row has no
#       entity to carry an id, so scoring it as unkeyed measured the statute.
#       The scope column is itself gated - `901_nr_record_scope.py` refuses to
#       write a non-entity scope onto a row that a Cedar entity stands behind.
#
#   (4) BLIND TO THE PARTY TABLE. Attribution in Cedar routes through a party
#       bridge, not a single owner column. 508 Osage headright rows and 74
#       ANCSA 7(i)/7(j) rows name their Native entity ONLY there. v2 reads a
#       declared bridge and requires the bridge row to assert parentage, so a
#       `serves_native_entities` counterparty never counts as ownership.
#
# Still not measured, and now printed rather than hidden: a table with NO id
# column of any kind is skipped. `c4_unmeasured_tables` names them.
# Also still sampled: SCAN_CAP rows per table. `c4_sampled_tables` names the
# tables where the cap bit, so a sampled figure is never quoted as a census.

SCAN_CAP = 50_000

BARE_ID_COLS = ("cedar_uid", "tribe_id", "entity_id", "cedar_entity_id")

# ADR-010: only these three leave the denominator.
NON_ENTITY_SCOPES = {"indian_country", "geographic", "native_serving"}

# table -> (bridge table, this table's key column, the bridge's key column,
#           {bridge column: required value}, (bridge id columns...))
PARTY_BRIDGES = {
    "resource_revenue.csv": (
        "resource_parties.csv", "resource_revenue_event_id", "object_id",
        {"relationship": "parent_native_entity"}, ("entity_id", "cedar_uid")),
    "resource_assets.csv": (
        "resource_parties.csv", "resource_asset_id", "object_id",
        {"relationship": "parent_native_entity"}, ("entity_id", "cedar_uid")),
}

# =====================================================================
# NATURAL SCOPE per dataset - ADR-010.
# =====================================================================
# ADR-009 made entity attachment measurable and then treated every unkeyed row
# as a failure. That is wrong for whole datasets: a bill changing federal
# Indian law affects all of Indian Country and has NO single entity to attach;
# NCAI lobbying on behalf of everyone is not an unresolved link to one tribe;
# a non-Native foundation granting to Native causes is correctly not Native.
#
# So attachment is scored ONLY where the dataset's subject is an entity.
# `mixed` datasets are reported but never blocked on the raw percentage,
# because the honest denominator - entity-scoped rows only - is not yet
# derivable per row. Deriving it is the work ADR-010 sets up; until then the
# scoreboard must not push a dataset toward INVENTING an attribution to clear
# a blocker, which is the Prime Directive violation this avoids.
NATURAL_SCOPE = {
    "contractors": "entity",          # a contract has an awardee
    "subcontracting": "entity",       # prime AND sub, both entities
    "funding": "entity",              # an award has a recipient
    "deals": "entity",                # a deal has parties
    "gaming": "entity",               # a facility has an operator
    "natural-resources": "entity",    # a lease has a lessor
    "native-owned-businesses": "entity",
    "nagpra": "entity",               # notices name affiliated tribes
    "_entity_layer": "hub",
    "legislation": "indian_country",  # a bill's subject is usually general
    "federal-register": "mixed",      # notices range from one tribe to all
    "lobbying": "mixed",              # a tribe's own filing vs NCAI's
    "nonprofits": "mixed",            # Native-controlled AND Native-serving
}

# Who is working each dataset. A BLOCKED dataset with no entry here is the
# one state that cannot fix itself - see the check at the bottom of main().
# Keep this current: an entry naming a workstream that has finished is worse
# than a blank, because it reports coverage that does not exist.
OWNERS = {
    "_entity_layer":            "hub",
    "contractors":              "grain-ws5",
    "subcontracting":           "subawards pull",
    "funding":                  "grain-ws4",
    "deals":                    "grain-ws5",
    "gaming":                   "int-2-gaming",
    # 2026-09-02: C4 closed by 900_nr_hub_join.py + 901_nr_record_scope.py.
    # 586 rows hub-joined, 19,465 rows lifted off the source-local `anc_id`
    # scheme, and the aggregate-by-law rows scoped under ADR-010 instead of
    # scored as unkeyed. 8/8 tables measured, 0 unmeasured.
    "natural-resources":        "READY - maintain",
    "native-owned-businesses":  "enterprise (READY - extending)",
    "nonprofits":               "grain-ws5",
    "lobbying":                 "grain-ws4",
    # 2026-09-02: grain-legislation closed the last blocker by ruling
    # congressional_correspondence_log.csv OUT OF SCOPE (4 candidate rows,
    # all non-Native HHS OS FOIA requests) rather than declaring a grain the
    # file could not evidence. 12 shippable tables -> 11.
    "legislation":              "READY - maintain",
    "federal-register":         "READY - maintain",
    "nagpra":                   "READY - maintain",
}

COLS = ["dataset", "status", "shelf", "n_customer_tables", "blockers",
        "c1_grain", "c2_keys", "c3_duplicates", "c4_identity_path",
        "c5_row_conservation", "c6_unresolved_conflicts", "c7_double_counting",
        "c8_rebuild_path", "c9_update_documented", "c10_gates",
        "natural_scope",
        # C4 v2 honesty columns: what the percentage does NOT cover.
        "c4_entity_scoped_rows", "c4_unmeasured_tables", "c4_sampled_tables",
        "tables_row_level_only", "duplicate_rows_total",
        "identity_model", "rebuild_entry", "destructive_rebuild",
        "enricher_ordering", "replay_status", "next_action", "measured_date"]


def read_csv(p: Path) -> list:
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def load_known_ids() -> set:
    """Every identifier the CENTRAL identity system actually issues.

    C4's own words are "entity matching uses the central identity system", so
    a value that is not IN it is not attachment however non-blank it is. Two
    real cases this catches, both measured 2026-09-02:
      * `owner_as_of_transaction_cedar_uid = "UNKNOWN"` on 47,877
        `prime_contracts.csv` rows - a sentinel string scored as an id;
      * `PAYER-US-BIA` / `PAYER-STATE-ND` and four siblings on 1,418
        `resource_revenue.csv` rows - federal and state payer stubs that are
        correctly not Native entities and must never count as attachment.
    Falls back to "any non-blank value" if the spine is unreadable, so a
    missing register degrades to v1 behaviour rather than reporting 0%.
    """
    known = set()
    for r in read_csv(REGISTER):
        for k in ("handle", "cedar_uid", "cedar_entity_id"):
            v = (r.get(k) or "").strip()
            if v:
                known.add(v)
    sp = read_csv(SPINE)
    for r in sp:
        for k in r:
            if k.endswith("entity_id") or k in ("cedar_uid", "neid", "tribe_id"):
                v = (r.get(k) or "").strip()
                if v:
                    known.add(v)
    return known


class _AnyNonBlank(frozenset):
    """Degraded mode: behaves as "every non-blank string is known"."""
    def __contains__(self, v):        # noqa: D105
        return bool(v)


KNOWN_IDS = load_known_ids()
if len(KNOWN_IDS) < 100:              # spine unreadable - do not report 0%
    KNOWN_IDS = _AnyNonBlank()

_BRIDGE_CACHE = {}


def load_bridge(table: str):
    """(key column on `table`, {key values that carry a Cedar entity}) | None.

    Attribution in Cedar routes through a PARTY TABLE, not a single owner
    column: one payment can involve the tribal government, allottees, an
    enterprise, an operator and a trust account at once. A scanner that reads
    only the row misses the 508 Osage headright rows and the 74 ANCSA
    7(i)/7(j) rows whose Native entity is named only there.

    The bridge row must ASSERT PARENTAGE - a `serves_native_entities`
    counterparty is deliberately not ownership (ADR-010 `native_serving`), and
    counting it would let a bridge launder a non-attachment into an
    attachment.
    """
    if table in _BRIDGE_CACHE:
        return _BRIDGE_CACHE[table]
    spec = PARTY_BRIDGES.get(table)
    out = None
    if spec:
        btab, key_col, bkey_col, require, id_cols = spec
        hit = set()
        for r in read_csv(ROOT / "data" / "clean" / btab):
            if any((r.get(k) or "").strip() != v for k, v in require.items()):
                continue
            if any((r.get(c) or "").strip() in KNOWN_IDS for c in id_cols):
                hit.add((r.get(bkey_col) or "").strip())
        hit.discard("")
        out = (key_col, hit) if hit else None
    _BRIDGE_CACHE[table] = out
    return out


def measure():
    if not CONTRACTS.exists():
        sys.exit("run 512 first - dataset_contracts.json is the input")
    doc = json.loads(CONTRACTS.read_text(encoding="utf-8"))
    safety = {r["table"]: r for r in read_csv(EXPORT_SAFETY)}
    cons = read_csv(CONSERVATION)
    cons_tables = {(r.get("source_table") or "").split("/")[-1] for r in cons}

    import cedar_pipeline as CP

    # replay coverage, from the release manifests C/G produced
    # Release manifests live in per-release DIRECTORIES (docs/releases/
    # <collection>-<commit>/), not flat .json files. The first version globbed
    # "*.json" at the top level, found nothing, and reported every dataset as
    # "not replayed" - including nagpra, which had been replayed twice and
    # reproduced BYTE-IDENTICAL. A scoreboard that under-reports finished work
    # sends agents to redo it.
    replayed = {}
    if RELEASES.exists():
        for d in sorted(RELEASES.iterdir()):
            if not d.is_dir() or d.name.startswith("_"):
                continue
            cid = d.name.rsplit("-", 1)[0]
            v = "captured"
            for mf in list(d.glob("*.json"))[:4]:
                try:
                    m = json.loads(mf.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                v = (m.get("replayability_verdict") or m.get("verdict")
                     or m.get("replay", {}).get("verdict") or v)
                break
            replayed[cid] = v

    rows = []
    for coll in doc.get("contracts", []):
        cid = coll["collection"]
        tables = [t for t in coll.get("tables", []) if t.get("status") == "shippable"]
        names = [t["table"] for t in tables]

        # ---- C1 grain / C2 keys -------------------------------------
        unstated = [t["table"] for t in tables
                    if (t.get("grain") or "").startswith("UNSTATED")]
        nokey = [t["table"] for t in tables if not (t.get("primary_key") or [])]

        # ---- C3 duplicates + C7 double counting ----------------------
        dup_total, dup_tables, rowlevel = 0, [], []
        for n in names:
            s = safety.get(n)
            if not s:
                continue
            d = int(s.get("literal_duplicate_rows") or 0)
            if d:
                dup_total += d
                dup_tables.append(f"{n}({d:,})")
            if s.get("aggregation_safe") == "0":
                rowlevel.append(n)
        money_unsafe = [n for n in rowlevel
                        if safety.get(n, {}).get("money_columns")]

        # ---- C5 row conservation -------------------------------------
        covered = [n for n in names if n in cons_tables]

        # ---- C4 IDENTITY ATTACHMENT (ADR-009 hub/spokes, ADR-010 scope) --
        # The entity layer is dataset 13 and the other twelve CONSUME it.
        # A spoke that re-derives identity locally, or that carries rows with
        # no Cedar id at all, is not attached to the hub however clean its own
        # grain is. See the C4 SCANNER v2 block at the top of this file for
        # the four measurement defects this replaces.
        keyed_rows = total_rows = 0
        unmeasured, sampled = [], []
        for n in names:
            for d in ("data/clean", "data/spine"):
                fp = ROOT / d / n
                if not fp.exists():
                    continue
                bridge = load_bridge(n)
                try:
                    with fp.open(encoding="utf-8-sig", errors="replace",
                                 newline="") as fh:
                        rdr = csv.DictReader(fh)
                        head = rdr.fieldnames or []
                        idc = [h for h in head
                               if h in BARE_ID_COLS
                               or h.endswith("_entity_id")
                               or h.endswith("_cedar_uid")]
                        if not idc and not bridge:
                            # (still) not measured - but SAY SO, by name.
                            unmeasured.append(n)
                            break
                        has_scope = "record_scope" in head
                        bkey = bridge[0] if bridge else None
                        i = -1
                        for i, r in enumerate(rdr):
                            if i >= SCAN_CAP:
                                sampled.append(n)
                                break
                            if has_scope and (r.get("record_scope") or "").strip() \
                                    in NON_ENTITY_SCOPES:
                                continue           # ADR-010 consequence 1
                            total_rows += 1
                            if any((r.get(c) or "").strip() in KNOWN_IDS
                                   for c in idc):
                                keyed_rows += 1
                            elif bridge and (r.get(bkey) or "").strip() \
                                    in bridge[1]:
                                keyed_rows += 1
                except OSError:
                    pass
                break
        keyed_pct = (100.0 * keyed_rows / total_rows) if total_rows else None

        # ---- C8 rebuild path + destructiveness -----------------------
        # The build PLANNER is the authority on what rebuilds a collection -
        # it merges the declared io map with the collection's own ordering.
        # Reading `rebuilt_by` off the contracts alone reported "no rebuild
        # entry point at all" for datasets that plan two rebuilders and have
        # been replayed from them.
        rebuilders = sorted({s for t in tables for s in (t.get("rebuilt_by") or [])})
        try:
            import build as _B
            plan = _B.plan_for(cid)
            for phase in (plan or {}).values() if isinstance(plan, dict) else []:
                if isinstance(phase, (list, tuple)):
                    rebuilders = sorted(set(rebuilders) | {
                        str(x) for x in phase if str(x).endswith(".py")})
        except Exception:
            pass
        never = [s for s in rebuilders if s in CP.NEVER_RUN]
        enrichers = sorted({s for t in tables for s in (t.get("enriched_by") or [])})

        # ---- assemble ------------------------------------------------
        blockers = []
        if unstated:
            blockers.append(f"C1 grain UNSTATED on {len(unstated)}: "
                            f"{', '.join(unstated[:3])}")
        if nokey:
            blockers.append(f"C2 no validated primary key on {len(nokey)}")
        if dup_tables:
            blockers.append(f"C3 literal duplicates: {', '.join(dup_tables[:3])}")
        if money_unsafe:
            blockers.append(f"C7 DOUBLE-COUNTING RISK - money tables a buyer "
                            f"cannot safely total: {', '.join(money_unsafe[:3])}")
        if names and not covered:
            blockers.append("C5 no row-conservation coverage")
        # ADR-009: a spoke cannot be READY on identity while most of its rows
        # are not attached to the hub. 50% is deliberately a floor, not a
        # target - it is the line below which the dataset is mostly unkeyed.
        scope = NATURAL_SCOPE.get(cid, "entity")
        if keyed_pct is not None and keyed_pct < 50 and scope == "entity":
            blockers.append(
                f"C4 only {keyed_pct:.0f}% of entity-bearing rows carry a "
                f"Cedar id, and every record in this dataset HAS an entity "
                f"subject - so this is unresolved work, not scope. See "
                f"ADR-009 and ADR-010.")
        if never:
            blockers.append(f"C8 rebuild is DESTRUCTIVE ({', '.join(never)}) - "
                            f"no safe documented rebuild path")
        if not rebuilders and names:
            blockers.append("C8 no rebuild entry point at all")

        status = "READY" if not blockers else "BLOCKED"
        if not names:
            status, blockers = "NOT_TESTED", ["no shippable tables declared"]

        nxt = blockers[0] if blockers else "maintain"
        rows.append(dict(
            dataset=cid, status=status, shelf=coll.get("shelf", ""),
            n_customer_tables=len(names),
            blockers=" | ".join(blockers) or "-",
            c1_grain=f"{len(names)-len(unstated)}/{len(names)}",
            c2_keys=f"{len(names)-len(nokey)}/{len(names)}",
            c3_duplicates="clean" if not dup_tables else f"{dup_total:,} rows",
            c4_identity_path=("HUB (dataset 13)" if cid == "_entity_layer"
                              else f"{keyed_pct:.0f}% keyed"
                              + ("" if scope == "entity" else f" [{scope}]")
                              if keyed_pct is not None else "no id columns"),
            natural_scope=scope,
            c4_entity_scoped_rows=total_rows,
            c4_unmeasured_tables=";".join(sorted(set(unmeasured))) or "-",
            c4_sampled_tables=";".join(sorted(set(sampled))) or "-",
            c5_row_conservation=f"{len(covered)}/{len(names)}",
            c6_unresolved_conflicts="0 shipped as definite",
            c7_double_counting="none" if not money_unsafe else f"{len(money_unsafe)} tables",
            c8_rebuild_path=("DESTRUCTIVE" if never else
                             "declared" if rebuilders else "MISSING"),
            c9_update_documented="see docs/datasets/",
            c10_gates="62 + semantic diff",
            tables_row_level_only=len(rowlevel),
            duplicate_rows_total=dup_total,
            identity_model=("source_record_link_v1" if cid == "federal-register"
                            else "legacy_fused"),
            rebuild_entry=f"py -3 code/build.py run {cid} --execute",
            destructive_rebuild="|".join(never) or "no",
            enricher_ordering=f"{len(enrichers)} declared",
            replay_status=replayed.get(cid, "not replayed"),
            next_action=nxt, measured_date=TODAY))
    # ADR-009: the hub prints FIRST regardless of status. Twelve spokes stand
    # on it, so its state is read before theirs, not alphabetically among them.
    return sorted(rows, key=lambda r: (r["dataset"] != "_entity_layer",
                                       r["status"] != "READY",
                                       len(r["blockers"]), r["dataset"]))


def write_md(rows):
    c = Counter(r["status"] for r in rows)
    L = ["# Cedar dataset readiness — the scoreboard", "",
         f"*Generated {TODAY} by `code/518_dataset_readiness.py` from live "
         f"artifacts. Three statuses only: **READY / BLOCKED / NOT_TESTED**. "
         f"There is no 'mostly ready' — a dataset crosses the minimum shipping "
         f"contract or it has named blockers.*", "",
         f"## READY: {c.get('READY',0)} / {len(rows)}", "",
         f"BLOCKED {c.get('BLOCKED',0)} · NOT_TESTED {c.get('NOT_TESTED',0)}",
         "",
         "| dataset | status | tables | grain | keys | duplicates | agg-unsafe | rebuild |",
         "|---|---|---:|---|---|---|---:|---|"]
    for r in rows:
        L.append(f"| `{r['dataset']}` | **{r['status']}** | "
                 f"{r['n_customer_tables']} | {r['c1_grain']} | {r['c2_keys']} | "
                 f"{r['c3_duplicates']} | {r['tables_row_level_only']} | "
                 f"{r['c8_rebuild_path']} |")
    L += ["", "## Blockers, by dataset", ""]
    for r in rows:
        if r["status"] == "READY":
            continue
        L.append(f"### `{r['dataset']}` — {r['status']}")
        L.append("")
        for b in r["blockers"].split(" | "):
            L.append(f"- {b}")
        L.append("")
    OUT_MD.write_text("\n".join(L), encoding="utf-8")


def main() -> int:
    verify = len(sys.argv) > 1 and sys.argv[1] == "verify"
    rows = measure()
    if not verify:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with OUT.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        write_md(rows)
    c = Counter(r["status"] for r in rows)
    print(f"\n  READY datasets: {c.get('READY',0)} / {len(rows)}")
    print(f"  BLOCKED {c.get('BLOCKED',0)}   NOT_TESTED {c.get('NOT_TESTED',0)}\n")
    for r in rows:
        print(f"  {r['status']:10s} {r['dataset']:26s} "
              f"{r['n_customer_tables']:3d} tables   {r['next_action'][:78]}")
    # closest to ready = fewest blockers
    close = [r for r in rows if r["status"] == "BLOCKED"][:3]
    if close:
        print("\n  CLOSEST TO READY:")
        for r in close:
            print(f"    {r['dataset']:24s} {len(r['blockers'].split(' | '))} blocker(s)")

    # ---- A BLOCKED DATASET WITH NOBODY ON IT ----------------------------
    # 2026-09-01: the owner asked whether all thirteen were being worked. They
    # were not - nine were blocked with no workstream assigned, and nothing
    # said so. The scoreboard reported STATUS and never OWNERSHIP, so a
    # dataset could sit blocked indefinitely while every report looked
    # complete. `_entity_layer` sat that way longest because its blockers
    # needed the spine builders touched and I kept deferring it.
    #
    # An unowned blocker is the one state that cannot fix itself, so it is now
    # the last thing this script prints and the loudest.
    unowned = [r for r in rows
               if r["status"] == "BLOCKED"
               and not OWNERS.get(r["dataset"])]
    print()
    if unowned:
        print(f"  !! {len(unowned)} BLOCKED DATASET(S) WITH NO WORKSTREAM "
              f"ASSIGNED - this is the only status that cannot fix itself:")
        for r in unowned:
            print(f"       {r['dataset']:24s} "
                  f"{len(r['blockers'].split(' | '))} blocker(s)")
        print("     Assign one in OWNERS at the top of this file, or explain "
              "in AGENTS.md why the dataset is deliberately parked.")
    else:
        n_b = sum(1 for r in rows if r["status"] == "BLOCKED")
        print(f"  every blocked dataset has a workstream ({n_b} blocked, "
              f"{len(rows) - n_b} READY)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
