#!/usr/bin/env python3
"""
Cedar Press - build.py: one entry point per collection.

    py -3 code/build.py list                    # the collections
    py -3 code/build.py plan gaming             # what WOULD run, in order
    py -3 code/build.py plan gaming --verbose   # with the reason for each step
    py -3 code/build.py run  gaming --execute   # actually run it
    py -3 code/build.py ship --execute          # the 7-step ship chain

WHY THIS EXISTS
---------------
Building a dataset meant knowing which of 377 scripts to run, in what order,
and which pairs silently revert each other. The number prefix has not implied
order since 2026-08-07 and 43 numbers are shared by two or three scripts. That
knowledge lived in people's heads and in prose, and the project has paid for it
repeatedly - 931 FERC entity links discarded four minutes after they were
written, by a rebuild that printed a LARGER row count and read as progress.

THIS FILE CONTAINS NO KNOWLEDGE OF ITS OWN. That is the point. It asks:

    cedar_pipeline.NEVER_RUN        what must never be executed
    cedar_pipeline.all_orderings()  rebuild -> enricher, curated + derived
    500_build_architecture_map      which tables belong to which collection
    293's class6_io_map             which scripts write which table

Adding a dataset means adding one entry to `COLLECTIONS` in
`500_build_architecture_map.py`. It does not mean editing this file.

DRY RUN IS THE DEFAULT, AND `run` STILL REFUSES WITHOUT `--execute`.
A runner that executes by accident is worse than no runner: many of these
scripts fetch from the network for hours, spend metered API quota, or rebuild a
table another agent is concurrently writing. `plan` is the command you want
almost always.

THE ORDERING RULE IT ENFORCES
-----------------------------
The enricher runs LAST. Phase 1 is every full-rebuild writer for the
collection's tables; phase 2 is every in-place enricher. A script that is a
rebuilder for one table and an enricher for another is AMBIGUOUS - it cannot be
in both phases - and is reported as needing a human ordering rather than being
silently placed.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import cedar_pipeline as CP                                        # noqa: E402

LINT = ROOT / "docs" / "lint_bug_classes.json"


def _load_architecture():
    spec = importlib.util.spec_from_file_location(
        "arch500", HERE / "500_build_architecture_map.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)                                     # type: ignore
    return m


def _io_map() -> tuple[dict, dict]:
    """(rebuilders, enrichers) from 293's scan. Empty if it has not been run."""
    try:
        m = json.loads(LINT.read_text(encoding="utf-8"))["class6_io_map"]
        return m.get("rebuilders", {}), m.get("enrichers", {})
    except Exception:
        return {}, {}


# Tables do not all live in data/clean. `cedar_entity_spine.csv` is in
# data/spine, and scanning only data/clean hid `01_build_entity_spine.py` -
# the NEVER_RUN script with FIFTEEN in-place enrichers behind it, the most
# dangerous rebuild in the repo - from every plan. A runner that cannot see
# that is worse than no runner, because it looks complete.
TABLE_DIRS = ("data/clean", "data/spine")


def collection_tables(arch, spec) -> list[str]:
    """Tables this collection claims, as bare filenames, across TABLE_DIRS."""
    import re
    pat = spec.get("tables")
    if not pat:
        return []
    rx = re.compile(pat)
    out = set()
    for d in TABLE_DIRS:
        for p in (ROOT / d).glob("*.csv"):
            if rx.search(p.stem) and ".bak_" not in p.name:
                out.add(p.name)
    return sorted(out)


def plan_for(cid: str):
    arch = _load_architecture()
    specs = {c["id"]: c for c in arch.COLLECTIONS}
    if cid not in specs:
        sys.exit(f"unknown collection {cid!r}. Try: py -3 code/build.py list")
    spec = specs[cid]
    tables = collection_tables(arch, spec)
    rebuilders, enrichers = _io_map()

    rb: dict[str, list[str]] = {}
    en: dict[str, list[str]] = {}
    for t in tables:
        for s in rebuilders.get(t, []):
            rb.setdefault(s, []).append(t)
        for s in enrichers.get(t, []):
            en.setdefault(s, []).append(t)

    # A DECLARED ORDERING RESOLVES AMBIGUITY.
    #
    # A script that rebuilds one table and enriches another cannot be placed
    # automatically - but if a person has declared it as the ENRICHER in
    # cedar_pipeline.KNOWN_ORDERINGS for a table in this collection, that is a
    # human statement that it runs last, and it outranks the automatic guess.
    # Without this, declaring an ordering changed nothing in the plan and the
    # declarations were decoration. `131_merge_archive_backfill.py` is the case
    # that showed it: declared to run after 40, still reported ambiguous.
    declared_enrichers = set()
    for t in tables:
        for o in CP.all_orderings(t):
            declared_enrichers.add(o["enricher"])

    ambiguous = sorted((set(rb) & set(en)) - declared_enrichers)
    en = {s: v for s, v in en.items()}
    for s in (set(rb) & set(en)) & declared_enrichers:
        rb.pop(s, None)                    # placed as an enricher, by decree
    phase1 = sorted(set(rb) - set(ambiguous))
    phase2 = sorted(set(en) - set(ambiguous))
    blocked = sorted(s for s in set(phase1) | set(phase2) | set(ambiguous)
                     if s in CP.NEVER_RUN)
    phase1 = [s for s in phase1 if s not in blocked]
    phase2 = [s for s in phase2 if s not in blocked]

    return {"id": cid, "name": spec["name"], "shelf": spec["shelf"],
            "tables": tables, "phase1": phase1, "phase2": phase2,
            "ambiguous": ambiguous, "blocked": blocked, "rb": rb, "en": en}


def cmd_list(_args) -> int:
    arch = _load_architecture()
    rebuilders, enrichers = _io_map()
    print(f"{'collection':28} {'shelf':14} {'tables':>7} {'build':>6} {'enrich':>7}")
    print("-" * 68)
    for c in arch.COLLECTIONS:
        p = plan_for(c["id"])
        print(f"{c['id']:28} {c['shelf']:14} {len(p['tables']):7} "
              f"{len(p['phase1']):6} {len(p['phase2']):7}")
    if not rebuilders:
        print("\nWARN: docs/lint_bug_classes.json not found - run "
              "`py -3 code/293_lint_bug_classes.py` first, or every plan is empty.",
              file=sys.stderr)
    return 0


def cmd_plan(args) -> int:
    p = plan_for(args.collection)
    print(f"\n{p['name']}  ·  {p['id']}  ·  {p['shelf']} shelf")
    print(f"{len(p['tables'])} clean tables\n")

    if p["blocked"]:
        print("REFUSED - on the NEVER_RUN list, excluded from the plan:")
        for s in p["blocked"]:
            print(f"  !! {s}")
            print(f"     {CP.NEVER_RUN[s][:150]}")
        print()

    print(f"PHASE 1 - full rebuilds ({len(p['phase1'])}):")
    for s in p["phase1"] or ["  (none)"]:
        if args.verbose and s in p["rb"]:
            print(f"  {s}\n      writes: {', '.join(p['rb'][s][:4])}")
        else:
            print(f"  {s}")

    print(f"\nPHASE 2 - in-place enrichers, these run LAST ({len(p['phase2'])}):")
    for s in p["phase2"] or ["  (none)"]:
        if args.verbose and s in p["en"]:
            print(f"  {s}\n      enriches: {', '.join(p['en'][s][:4])}")
        else:
            print(f"  {s}")

    if p["ambiguous"]:
        print(f"\nAMBIGUOUS ({len(p['ambiguous'])}) - a rebuilder for one table and an "
              f"enricher for another.\nThese cannot be placed automatically and are "
              f"NOT in the plan. Order them by hand:")
        for s in p["ambiguous"]:
            print(f"  ?? {s}")
            print(f"     rebuilds: {', '.join(p['rb'].get(s, [])[:3])}")
            print(f"     enriches: {', '.join(p['en'].get(s, [])[:3])}")

    stale = []
    for t in p["tables"]:
        if CP.enricher_backups_for(t):
            stale.append(t)
    if stale:
        print(f"\nENRICHER BACKUPS PRESENT on {len(stale)} table(s) - an in-place "
              f"enricher has touched them since the last build. Re-run it AFTER "
              f"any rebuild or its work is reverted:")
        for t in stale[:8]:
            print(f"  {t}  ->  re-run {', '.join(CP.enrichers_to_rerun(t)[:3]) or 'unknown'}")

    print("\nDRY RUN. Nothing was executed.")
    print(f"To execute: py -3 code/build.py run {p['id']} --execute")
    return 0


def cmd_run(args) -> int:
    if not args.execute:
        print("run REQUIRES --execute. Showing the plan instead.\n", file=sys.stderr)
        return cmd_plan(args)
    p = plan_for(args.collection)
    if p["blocked"]:
        sys.exit(f"refusing: {len(p['blocked'])} NEVER_RUN script(s) in scope. "
                 f"Resolve by hand: {', '.join(p['blocked'])}")

    order = [("rebuild", s) for s in p["phase1"]] + \
            [("enrich", s) for s in p["phase2"]]
    print(f"executing {len(order)} steps for {p['id']}\n")
    for i, (phase, s) in enumerate(order, 1):
        print(f"[{i}/{len(order)}] {phase:8} {s}", flush=True)
        r = subprocess.run([sys.executable, str(HERE / s)], cwd=str(ROOT))
        if r.returncode != 0:
            # Stopping is the point. Continuing past a failed rebuild runs the
            # enrichers against a half-written table, which is how a partial
            # restore became a rebuild revert wearing a different hat.
            sys.exit(f"\nSTOPPED at step {i} ({s}) - exit {r.returncode}. "
                     f"Nothing after this ran.")
    print("\ndone. Now ship: see docs/SHIPPING_RUNBOOK.md (87 -> 25 -> 27)")
    return 0


# The ship chain, exactly as docs/SHIPPING_RUNBOOK.md part 1 declares it.
# NOT "87 -> 25 -> 27" - that three-step shorthand appears in 62's failure text
# and in several docs, and it omits the codebook build, the gate, the coverage
# profile and the harmonised views. Shipping with a stale codebook is how the
# gaming collection shipped 912 of 104,412 rows.
SHIP_CHAIN = [
    ("cedar_codebook.py", ["build"], "fragments -> codebook_master.csv",
     "must print ADDS, never REFUSING"),
    ("62_no_regression_check.py", [], "the gate",
     "any FAIL stops the chain - nothing ships past a regression"),
    ("87_build_dataset_notes.py", [], "notes contract per dataset",
     "watch SHIP RATE: and the NOT SHIPPED list"),
    ("102_build_coverage_profile.py", [], "source coverage profile", ""),
    ("110_build_harmonized_views.py", [], "harmonised views", ""),
    ("25_build_publication_layer.py", [], "cedar_press.db, .xlsx, sanity",
     "watch SHIP RATE:, [licensed] drops, FAIL sanity checks"),
    ("27_build_dataset_manifests.py", [], "app manifests",
     "watch the NO MANIFEST list and manifest coverage:"),
]


def cmd_ship(args) -> int:
    """Run the documented ship chain. Dry run unless --execute."""
    print("\nSHIP CHAIN - docs/SHIPPING_RUNBOOK.md part 1\n")
    for i, (script, argv, what, watch) in enumerate(SHIP_CHAIN, 1):
        print(f"  {i}. {script} {' '.join(argv)}")
        print(f"       {what}")
        if watch:
            print(f"       ^ {watch}")
    print()

    # Step 0 from the runbook: is anyone else still writing?
    recent = sorted(
        ((p.stat().st_mtime, p.name) for p in (ROOT / "data" / "clean").glob("*.csv")),
        reverse=True)[:3]
    print("  most recently written clean tables (step 0 - is anyone still writing?):")
    for ts, n in recent:
        print(f"    {datetime.fromtimestamp(ts):%Y-%m-%d %H:%M}  {n}")
    # A LOCK FILE IS NOT A HELD LOCK. There are 534 `_HOSTLOCK_*.json` on disk
    # and essentially all are released: the runner writes `active: false` when
    # it finishes rather than deleting the file, so the file is a history, not
    # a claim. Refusing on the file count would refuse forever, and a guard
    # that always fires is a guard the next person deletes. Only `active: true`
    # blocks. (WORK_QUEUE records exactly this being misread once already:
    # a lock reported as stale-and-blocking had in fact been released.)
    # ...AND `active: true` IS NOT A HELD LOCK EITHER. The claimant can die
    # without releasing. Measured 2026-08-28: _HOSTLOCK_eaglemountaincasino.com
    # read active:true, pid 10456, claimed 2026-08-27T01:15 - and that process
    # was gone. WORK_QUEUE records the same shape blocking two queue items for
    # NINETEEN DAYS on a dead pid. So liveness decides, and a stale lock is
    # named for cleanup rather than silently obeyed.
    def _alive(pid):
        if not isinstance(pid, int):
            return None                    # unknown - do not block on it
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"Get-Process -Id {pid} -ErrorAction SilentlyContinue | "
                 f"Select-Object -ExpandProperty Id"],
                capture_output=True, text=True, timeout=20)
            return bool(r.stdout.strip())
        except Exception:
            return None

    lock_files = list((ROOT / "logs").glob("_HOSTLOCK_*.json")) if (ROOT / "logs").exists() else []
    claimed, locks, stale = [], [], []
    for lp in lock_files:
        try:
            d = json.loads(lp.read_text(encoding="utf-8"))
        except Exception:
            continue                       # unreadable lock is not a held lock
        if d.get("active") is not True:
            continue
        claimed.append(lp)
        if _alive(d.get("pid")) is False:
            stale.append((lp, d))
        else:
            locks.append((lp, d))
    print(f"  host lock files: {len(lock_files)}   claiming active: {len(claimed)}"
          f"   genuinely held: {len(locks)}   STALE (dead pid): {len(stale)}")
    for lp, d in stale[:5]:
        print(f"    stale -> {lp.name}  pid {d.get('pid')} gone, claimed "
              f"{str(d.get('claimed_at'))[:16]} by {d.get('script','?')}")
    for lp, d in locks[:5]:
        print(f"    HELD  -> {lp.name}  pid {d.get('pid')} alive")

    if not args.execute:
        print("\nDRY RUN. Nothing was executed.")
        print("To execute: py -3 code/build.py ship --execute")
        return 0

    if locks:
        sys.exit(f"refusing: {len(locks)} host lock(s) genuinely held by a live "
                 f"process. Rebuilding dist/ from data that is concurrently "
                 f"changing is how this project lost work before. "
                 f"Stale locks (dead pid) do NOT block and are named above.")

    for i, (script, argv, what, _watch) in enumerate(SHIP_CHAIN, 1):
        print(f"\n[{i}/{len(SHIP_CHAIN)}] {script} {' '.join(argv)}", flush=True)
        r = subprocess.run([sys.executable, str(HERE / script), *argv], cwd=str(ROOT))
        if r.returncode != 0:
            sys.exit(f"\nSTOPPED at step {i} ({script}) - exit {r.returncode}. "
                     f"Nothing after this ran. {_watch or ''}")
    print("\nship chain complete. Check SHIP RATE in the 87 and 25 output above.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="the collections and their script counts").set_defaults(func=cmd_list)
    sh = sub.add_parser("ship", help="run the documented ship chain (7 steps)")
    sh.add_argument("--execute", action="store_true",
                    help="actually run it; without this you get the chain")
    sh.set_defaults(func=cmd_ship)
    for name, fn in (("plan", cmd_plan), ("run", cmd_run)):
        q = sub.add_parser(name, help=f"{name} one collection")
        q.add_argument("collection")
        q.add_argument("--verbose", action="store_true")
        if name == "run":
            q.add_argument("--execute", action="store_true",
                           help="actually run it; without this you get the plan")
        q.set_defaults(func=fn)
    args = ap.parse_args()
    if not hasattr(args, "verbose"):
        args.verbose = False
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
