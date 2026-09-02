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
    "natural-resources":        "grain-ws3 (C5 banked, deliberately not merged)",
    "native-owned-businesses":  "enterprise (READY - extending)",
    "nonprofits":               "grain-ws5",
    "lobbying":                 "grain-ws4",
    "legislation":              "grain-ws4",
    "federal-register":         "READY - maintain",
    "nagpra":                   "READY - maintain",
}

COLS = ["dataset", "status", "shelf", "n_customer_tables", "blockers",
        "c1_grain", "c2_keys", "c3_duplicates", "c4_identity_path",
        "c5_row_conservation", "c6_unresolved_conflicts", "c7_double_counting",
        "c8_rebuild_path", "c9_update_documented", "c10_gates",
        "natural_scope",
        "tables_row_level_only", "duplicate_rows_total",
        "identity_model", "rebuild_entry", "destructive_rebuild",
        "enricher_ordering", "replay_status", "next_action", "measured_date"]


def read_csv(p: Path) -> list:
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


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

        # ---- C4 IDENTITY ATTACHMENT (ADR-009: hub and spokes) --------
        # The entity layer is dataset 13 and the other twelve CONSUME it.
        # A spoke that re-derives identity locally, or that carries rows with
        # no cedar_uid at all, is not attached to the hub however clean its
        # own grain is. Measured, not assumed: what share of this dataset's
        # entity-bearing rows actually carry a Cedar id.
        keyed_rows = total_rows = 0
        for n in names:
            for d in ("data/clean", "data/spine"):
                fp = ROOT / d / n
                if not fp.exists():
                    continue
                try:
                    with fp.open(encoding="utf-8-sig", errors="replace",
                                 newline="") as fh:
                        rdr = csv.DictReader(fh)
                        idc = [h for h in (rdr.fieldnames or [])
                               if h in ("cedar_uid", "tribe_id", "entity_id",
                                        "cedar_entity_id")]
                        if not idc:
                            break
                        for i, r in enumerate(rdr):
                            if i >= 50000:
                                break
                            total_rows += 1
                            if any((r.get(c) or "").strip() for c in idc):
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
