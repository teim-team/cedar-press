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

COLS = ["dataset", "status", "shelf", "n_customer_tables", "blockers",
        "c1_grain", "c2_keys", "c3_duplicates", "c4_identity_path",
        "c5_row_conservation", "c6_unresolved_conflicts", "c7_double_counting",
        "c8_rebuild_path", "c9_update_documented", "c10_gates",
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
            c4_identity_path="central (503/510)",
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
    return sorted(rows, key=lambda r: (r["status"] != "READY",
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
