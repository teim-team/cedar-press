#!/usr/bin/env python3
"""
287 - THE DEPENDENCY MANIFEST, and the rebuild-vs-enricher ordering.

    py -3 code/287_build_dependency_manifest.py
    py -3 code/287_build_dependency_manifest.py --check <table.csv>

WHAT WENT WRONG, TWICE IN ONE DAY
---------------------------------
`133 build` is a FULL REBUILD of `ferc_docket_filings.csv`.
`168_link_adjudication_hubs.py` had, **four minutes earlier**, written 931
entity links and nine columns into that same file IN PLACE. The rebuild
discarded all of it - and **printed a LARGER row count, which read as
progress.** `09` has done the same to `50`. A third instance was a PARTIAL
restore, which left 102,615 filings drawn from 307 dockets described by a
docket table listing 183, and neither file looked wrong on its own.

Nothing warned, for one structural reason: **nowhere did anything declare
that one script rebuilds a file another script enriches.** The number prefix
has not implied step order since 2026-08-07 and there are 38+ collisions, so
order cannot be read off a filename either.

    THE RULE:
    WHERE A FULL-REBUILD STAGE AND AN IN-PLACE ENRICHER TOUCH ONE FILE,
    THE ENRICHER RUNS LAST - AND SOMETHING CHECKS THAT ITS COLUMNS
    SURVIVED.

WHAT THIS EMITS
---------------
    docs/schema/dependency_manifest.json   reads/writes/classification per script
    docs/DEPENDENCY_MANIFEST.md            the readable ordering, contested files first

and it runs the SURVIVAL CHECK: for every clean table that has a
`.bak_<date>_pre_<script>` beside it - the signal that an in-place enricher
touched it - compare the live columns against the backup's. A column present
in the backup and absent from the live file IS a rebuild revert, caught
without needing to have watched it happen.

`62_no_regression_check.py` already counts this as
`files_with_columns_lost_vs_backup` and holds it at 0. This script says WHICH
enricher must be re-run when it is not 0, which is the part that turns the
metric into an action.

Read-only outside `docs/`. `--check <table>` is the pre-flight an update path
runs BEFORE a rebuild, not the post-mortem after one.

Claimed 2026-08-26 with script numbers 284-292.
"""

import json
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cedar_pipeline as CP           # noqa: E402

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"
SCHEMA_DIR = CEDAR / "docs" / "schema"
OUT_JSON = SCHEMA_DIR / "dependency_manifest.json"
OUT_MD = CEDAR / "docs" / "DEPENDENCY_MANIFEST.md"
TODAY = date.today().isoformat()


def check_table(table, verbose=True):
    """Pre-flight for ONE table. Returns (safe, report).

    Answers the question a rebuild should ask before it runs: has an in-place
    enricher touched this file since the last build, and if so what has to be
    re-run afterwards?
    """
    t = Path(str(table)).name
    live = CLEAN / t
    rep = {"table": t, "exists": live.exists()}
    if not live.exists():
        return True, rep
    baks = CP.enricher_backups_for(live)
    rep["enricher_backups"] = [b.name for b in baks[:6]]
    lost, src = CP.columns_lost_vs_backup(t)
    rep["columns_lost_vs_newest_backup"] = lost
    rep["compared_against"] = src
    orderings = [o for o in CP.KNOWN_ORDERINGS if o["file"] == t]
    rep["declared_orderings"] = orderings
    rep["enrichers_to_rerun_after_a_rebuild"] = sorted(
        {o["enricher"] for o in orderings})
    safe = not lost
    if verbose:
        print(f"\n  {t}")
        print(f"    enricher backups beside it: "
              f"{len(baks)}"
              f"{' -> ' + baks[0].name if baks else ''}")
        if lost:
            print(f"    !! {len(lost)} COLUMN(S) LOST vs {src}:")
            print(f"       {', '.join(lost)}")
            print(f"    A rebuild reverted an in-place enricher. Re-run: "
                  f"{', '.join(rep['enrichers_to_rerun_after_a_rebuild']) or 'unknown'}")
        else:
            print("    no columns lost against the newest backup")
        for o in orderings:
            print(f"    DECLARED ORDER: {o['rebuild']}  THEN  {o['enricher']}")
            print(f"      cost of getting it wrong: {o['cost']}")
    return safe, rep


def main():
    started = datetime.now()
    if "--check" in sys.argv:
        i = sys.argv.index("--check")
        tables = sys.argv[i + 1:]
        if not tables:
            print("usage: --check <table.csv> [table.csv ...]")
            return 2
        print("=" * 78)
        print("287  PRE-FLIGHT: has an in-place enricher touched this file?")
        print("=" * 78)
        allsafe = True
        for t in tables:
            ok, _ = check_table(t)
            allsafe = allsafe and ok
        print(f"\n  {'SAFE TO REBUILD' if allsafe else 'NOT SAFE - RE-RUN THE ENRICHER AFTER'}")
        return 0 if allsafe else 1

    print("=" * 78)
    print("287  DEPENDENCY MANIFEST")
    print("=" * 78)

    scripts, writers, readers = {}, defaultdict(set), defaultdict(set)
    for p in sorted(CODE.glob("*.py")):
        io = CP.declared_io(p)
        kind, ev = CP.classify(p)
        scripts[p.name] = {
            "reads": io["reads"], "writes": io["writes"],
            "read_modify_write": io["read_modify_write"],
            "templated": io["templated"], "unknown": io["unknown"],
            "classification": kind, "evidence": ev,
            "never_run": p.name in CP.NEVER_RUN,
            "never_run_reason": CP.NEVER_RUN.get(p.name),
            "mtime": datetime.fromtimestamp(
                p.stat().st_mtime).isoformat(timespec="seconds"),
        }
        # SETS, not lists: a script that both reads and writes a file
        # appended its own name twice and the printed manifest looked like
        # two agents were fighting over a file only one touches.
        for w in io["writes"] + io["read_modify_write"]:
            writers[w].add(p.name)
        for r in io["reads"]:
            readers[r].add(p.name)

    kinds = defaultdict(int)
    for v in scripts.values():
        kinds[v["classification"]] += 1
    print(f"\n  {len(scripts)} scripts classified")
    for k, n in sorted(kinds.items(), key=lambda kv: -kv[1]):
        print(f"    {k:10s} {n:>4}")

    print("\n  NEVER-RUN GUARDS (hard, in cedar_pipeline.guard):")
    for s, why in sorted(CP.NEVER_RUN.items()):
        print(f"    {s}")
        print(f"      {why[:130]}")

    # --- contested files ----------------------------------------------------
    contested = {}
    for f, ws in writers.items():
        if not (CLEAN / f).exists():
            continue
        rebuilders = [w for w in ws
                      if scripts[w]["classification"] in ("rebuild", "both")]
        enrichers = [w for w in ws
                     if f in scripts[w]["read_modify_write"]
                     or scripts[w]["classification"] == "enricher"]
        if rebuilders and enrichers and set(rebuilders) != set(enrichers):
            contested[f] = {"rebuilders": sorted(rebuilders),
                            "enrichers": sorted(enrichers)}
    print(f"\n  CONTESTED FILES - a full rebuild AND an in-place enricher "
          f"both write them ({len(contested)})")
    print("  These are where work gets silently reverted. Enricher runs LAST.")
    for f, v in sorted(contested.items())[:20]:
        print(f"    {f}")
        print(f"      rebuild:  {', '.join(v['rebuilders'][:4])}")
        print(f"      enrich:   {', '.join(v['enrichers'][:4])}")
    if len(contested) > 20:
        print(f"    ... and {len(contested) - 20} more, in the JSON")

    # --- survival check -----------------------------------------------------
    print("\n  SURVIVAL CHECK - did a rebuild revert an enricher's columns?")
    with_baks, reverted = 0, {}
    for p in sorted(CLEAN.glob("*.csv")):
        if not CP.enricher_backups_for(p):
            continue
        with_baks += 1
        lost, src = CP.columns_lost_vs_backup(p.name)
        if lost:
            reverted[p.name] = {"columns_lost": lost, "compared_against": src}
    print(f"    {with_baks} clean table(s) carry a `.bak_*` from an in-place "
          f"enricher")
    if reverted:
        print(f"    !! {len(reverted)} TABLE(S) LOST COLUMNS. This is a "
              f"rebuild revert, live, right now:")
        for t, v in sorted(reverted.items()):
            rerun = sorted({o["enricher"] for o in CP.KNOWN_ORDERINGS
                            if o["file"] == t})
            print(f"       {t}: lost {', '.join(v['columns_lost'][:6])}")
            print(f"         vs {v['compared_against']}")
            print(f"         re-run: {', '.join(rerun) or 'the enricher '
                                                        'that wrote them'}")
    else:
        print("    0 tables lost columns against their newest backup. "
              "Matches `62`'s\n    `files_with_columns_lost_vs_backup = 0`.")

    # --- write --------------------------------------------------------------
    doc = {"generated": TODAY,
           "generated_at": started.isoformat(timespec="seconds"),
           "produced_by": "287_build_dependency_manifest.py",
           "never_run": CP.NEVER_RUN,
           "known_orderings": CP.KNOWN_ORDERINGS,
           "contested_files": contested,
           "columns_lost_vs_backup": reverted,
           "tables_with_enricher_backup": with_baks,
           "writers": {k: sorted(v) for k, v in sorted(writers.items())},
           "readers": {k: sorted(v) for k, v in sorted(readers.items())},
           "scripts": scripts}
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = OUT_JSON.with_suffix(".json.part")
    tmp.write_text(json.dumps(doc, indent=1, sort_keys=True, default=str),
                   encoding="utf-8")
    tmp.replace(OUT_JSON)
    json.loads(OUT_JSON.read_text(encoding="utf-8"))

    md = [
        "# Dependency manifest\n",
        f"*Generated {TODAY} by `code/287_build_dependency_manifest.py`. "
        f"Regenerate; do not edit.*\n",
        "The number prefix has not implied step order since 2026-08-07 and "
        "there are 38+\ncollisions, so **order is declared here, never "
        "inferred from a filename**.\n",
        "## Never run these, ever\n",
        "Enforced in code by `cedar_pipeline.guard()`, not by comment.\n",
        "| script | why |", "|---|---|"]
    for s, why in sorted(CP.NEVER_RUN.items()):
        md.append(f"| `{s}` | {why} |")
    md += ["\n## Declared orderings\n",
           "The enricher runs **last**. Each row is a measured loss.\n",
           "| file | rebuild | then enricher | what it cost |",
           "|---|---|---|---|"]
    for o in CP.KNOWN_ORDERINGS:
        md.append(f"| `{o['file']}` | `{o['rebuild']}` | `{o['enricher']}` "
                  f"| {o['cost']} |")
    md += [f"\n## Contested files ({len(contested)})\n",
           "A full rebuild and an in-place enricher both write these. This "
           "is the list\nof places the 133/168 collision can happen again.\n",
           "| file | rebuilders | enrichers |", "|---|---|---|"]
    for f, v in sorted(contested.items()):
        md.append(f"| `{f}` | {', '.join('`%s`' % x for x in v['rebuilders'])} "
                  f"| {', '.join('`%s`' % x for x in v['enrichers'])} |")
    md += ["\n## Survival check\n",
           f"`{with_baks}` clean tables carry an enricher backup. "
           f"**{len(reverted)}** have lost columns against it.\n"]
    if reverted:
        md += ["| table | columns lost | compared against |", "|---|---|---|"]
        for t, v in sorted(reverted.items()):
            md.append(f"| `{t}` | {', '.join(v['columns_lost'])} "
                      f"| `{v['compared_against']}` |")
    md += ["\n## Pre-flight before any rebuild\n",
           "```\npy -3 code/287_build_dependency_manifest.py --check "
           "<table.csv>\n```\n",
           "Exit 0 means no enricher columns are missing. Exit 1 names the "
           "enricher to\nre-run **after** the rebuild.\n"]
    tmp = OUT_MD.with_suffix(".md.part")
    tmp.write_text("\n".join(md) + "\n", encoding="utf-8")
    tmp.replace(OUT_MD)
    OUT_MD.read_text(encoding="utf-8")

    print(f"\n  wrote docs/schema/dependency_manifest.json "
          f"({OUT_JSON.stat().st_size:,} bytes, re-read OK)")
    print(f"  wrote docs/DEPENDENCY_MANIFEST.md "
          f"({OUT_MD.stat().st_size:,} bytes, re-read OK)")
    print(f"\n  {(datetime.now() - started).total_seconds():.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
