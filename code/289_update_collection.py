#!/usr/bin/env python3
"""
289 - THE UPDATE PATH. One command, from new source data to a shippable
      collection, with preconditions, guards and rollback.

    py -3 code/289_update_collection.py                 # DRY RUN (default)
    py -3 code/289_update_collection.py --go            # actually run it
    py -3 code/289_update_collection.py --go --only deals
    py -3 code/289_update_collection.py --rollback <snapshot-dir>

WHY THIS EXISTS AS CODE AND NOT AS PROSE
----------------------------------------
`docs/SHIPPING_RUNBOOK.md` already holds the right chain -
`cedar_codebook build` -> 62 -> 87 -> 102 -> 110 -> 25 -> 27 - and it opens
by recording that **the chain is STAGED, NOT RUN**, and that the last time it
went unrun the gaming collection shipped **912 of 104,412 rows, 0.87%**, for
twenty days. The runbook was not wrong. It was prose, and prose does not run.

Worse, the runbook's most important line is a NEGATIVE one: *"NEVER run
`41_build_codebooks.py`"*, because it would delete 21 of the 43 codebook
blocks. **A comment does not stop a command.** Four scripts are in that
category - `01`, `09`, `41`, `88` - and here they are hard guards in
`cedar_pipeline.guard()`, which raises. Not a warning. Not a prompt.

WHAT IT DOES, IN ORDER, AND WHY THE ORDER IS THAT
-------------------------------------------------
    0  PRECONDITIONS   nobody else is mid-write; the codebook is whole
    1  SNAPSHOT        graveyard/<date>_pre_ship_<time>/ - the rollback target
    2  PRE-FLIGHT      has an in-place enricher touched a file we rebuild?
    3  cedar_codebook.py build     fragments -> master.  MUST say ADDS.
    4  62_no_regression_check.py   the gate. A FAIL is STOP-WORK.
    5  87_build_dataset_notes.py   notes contract. Read SHIP RATE.
    6  102 / 110                   coverage profile, harmonised views
    7  25_build_publication_layer  the DB. Read the [licensed] drops.
    8  27_build_dataset_manifests  app manifests
    9  284 / 285                   keys + typed schema, regenerated
   10  287                         dependency manifest + survival check
   11  288                         collection descriptors
   12  62 AGAIN                    the gate, after. Compare with step 4.

**Why 3 first.** `87` reads `codebook_master.csv`. A stale master silently
skips every dataset registered since - the original defect.

**Why 4 before 5.** A notes contract ASSERTS row counts. Asserting counts
that have regressed publishes the regression.

**Why 12 at all.** Step 4 says the state was clean before. Only step 12 says
this run did not break it. A chain that gates itself only on entry is a
chain that can do damage and report success.

ROLLBACK
--------
Step 1 writes a snapshot before anything else moves, and prints its path.
`--rollback <dir>` restores `dist/`, `codebook_master.csv` and the codebook
fragments from it BY EXACT FILENAME. **Never by glob** - an agent restoring
its own run with `*.bak_2026-08-26_pre163` reverted seven files belonging to
two other agents and dropped the ledger from 20,577 rows to 20,559.

Claimed 2026-08-26 with script numbers 284-292.
"""

import json
import shutil
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cedar_pipeline as CP           # noqa: E402

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"
DIST = CEDAR / "dist"
LOGS = CEDAR / "logs"
GRAVEYARD = CEDAR / "graveyard"
TODAY = date.today().isoformat()

QUIET_MINUTES = 30
PY = ["py", "-3"]

#: (label, argv, what to read in the output, is a hard gate)
CHAIN = [
    ("codebook master <- fragments",
     ["code/cedar_codebook.py", "build"],
     "must print `master rebuilt`, NEVER `REFUSING`", True),
    ("the gate, BEFORE",
     ["code/62_no_regression_check.py"], "any FAIL stops the chain", True),
    ("dataset notes contract",
     ["code/87_build_dataset_notes.py"],
     "`SHIP RATE:`, the `NOT SHIPPED` list, and "
     "`LICENCE GATE - 2 file(s) REFUSED`", False),
    ("source coverage profile",
     ["code/102_build_coverage_profile.py"], "-", False),
    ("harmonised views",
     ["code/110_build_harmonized_views.py"], "-", False),
    ("publication layer (cedar_press.db, xlsx)",
     ["code/25_build_publication_layer.py"],
     "`SHIP RATE:`, every `[licensed] ... dropping` line, zero FAIL sanity "
     "checks", False),
    ("app manifests",
     ["code/27_build_dataset_manifests.py"],
     "`NO MANIFEST` list and `manifest coverage:`", False),
    ("primary-key audit",
     ["code/284_audit_nondeterministic_keys.py"],
     "FIXTURE SELF-TEST must PASS; note any NEW cross-reference", False),
    ("typed schema",
     ["code/285_build_table_schemas.py"],
     "INGEST-READY count and the LICENCE GATE refusals", False),
    ("dependency manifest + survival check",
     ["code/287_build_dependency_manifest.py"],
     "`0 tables lost columns` - anything else is a rebuild revert", False),
    ("collection descriptors",
     ["code/288_build_collection_descriptors.py"],
     "VINTAGE HONESTY, and the refused period labels", False),
    ("the gate, AFTER",
     ["code/62_no_regression_check.py"],
     "compare against the BEFORE run - this is what says the chain did no "
     "harm", True),
]

SNAPSHOT_ITEMS = [
    ("data/clean/codebook_master.csv", "file"),
    ("data/clean/codebook", "dir"),
    ("dist", "dir"),
    ("docs/schema", "dir"),
]


def hr(t=""):
    print("\n" + "=" * 78)
    if t:
        print(t)
        print("=" * 78)


def preconditions():
    """Cheap, and every one of them is a rule paid for by an incident."""
    hr("0  PRECONDITIONS")
    ok = True

    # a. is anyone else mid-write? Ten-plus agents ran here on 2026-08-26.
    now = time.time()
    recent = []
    for p in CLEAN.glob("*.csv"):
        age = (now - p.stat().st_mtime) / 60.0
        if age < QUIET_MINUTES:
            recent.append((age, p.name))
    recent.sort()
    if recent:
        ok = False
        print(f"  !! {len(recent)} table(s) in data/clean written in the "
              f"last {QUIET_MINUTES} minutes:")
        for age, n in recent[:8]:
            print(f"       {n:52s} {age:5.1f} min ago")
        print("     ANOTHER AGENT IS WRITING. Rebuilding dist/ from data "
              "that is\n     concurrently changing is how this project lost "
              "work before.")
    else:
        print(f"  data/clean quiet for >{QUIET_MINUTES} min")

    # b. is a puller holding a host?
    locks = sorted(LOGS.glob("_HOSTLOCK_*.json"))
    live = []
    for L in locks:
        if (now - L.stat().st_mtime) / 60.0 < QUIET_MINUTES:
            live.append(L.name)
    print(f"  {len(locks)} host lock file(s); {len(live)} touched in the "
          f"last {QUIET_MINUTES} min")
    for n in live[:6]:
        print(f"       {n}")

    # c. is the codebook whole? Read-only; must print SAFE.
    r = subprocess.run(PY + ["code/cedar_codebook.py", "check"],
                       cwd=CEDAR, capture_output=True, text=True)
    safe = "SAFE - a rebuild loses nothing" in r.stdout
    print(f"  codebook check: {'SAFE' if safe else 'NOT SAFE'}")
    if not safe:
        ok = False
        for line in r.stdout.splitlines()[-6:]:
            print(f"       {line}")
        print("     A rebuild would LOSE codebook rows. Run "
              "`py -3 code/cedar_register_codebook.py reconcile` first.")

    # d. the never-run guards are armed.
    armed = 0
    for s in CP.NEVER_RUN:
        try:
            CP.guard(s)
            print(f"  !! GUARD NOT ARMED for {s}")
            ok = False
        except CP.ForbiddenScript:
            armed += 1
    print(f"  never-run guards armed: {armed} of {len(CP.NEVER_RUN)} "
          f"({', '.join(sorted(CP.NEVER_RUN))})")
    return ok


def preflight():
    """Which enrichers must run AFTER which rebuilds, and did one already
    get reverted?"""
    hr("2  PRE-FLIGHT: rebuild-vs-enricher ordering")
    bad = []
    for o in CP.KNOWN_ORDERINGS:
        lost, src = CP.columns_lost_vs_backup(o["file"])
        mark = "OK" if not lost else f"LOST {len(lost)}"
        print(f"  {o['file']:40s} {mark:10s} "
              f"{o['rebuild']} THEN {o['enricher']}")
        if lost:
            bad.append((o, lost, src))
    for o, lost, src in bad:
        print(f"\n  !! {o['file']} lost {', '.join(lost)} vs {src}")
        print(f"     A rebuild reverted an in-place enricher. RE-RUN "
              f"{o['enricher']} before shipping.")
    if not bad:
        print("\n  no enricher columns missing. Safe to proceed.")
    return not bad


def snapshot():
    hr("1  SNAPSHOT - the rollback target, written before anything moves")
    d = GRAVEYARD / f"{TODAY}_pre_ship_{datetime.now():%H%M%S}"
    d.mkdir(parents=True, exist_ok=True)
    manifest = []
    for rel, kind in SNAPSHOT_ITEMS:
        src = CEDAR / rel
        if not src.exists():
            print(f"  (absent, nothing to snapshot: {rel})")
            continue
        dst = d / rel.replace("/", "__")
        if kind == "dir":
            shutil.copytree(src, dst, dirs_exist_ok=True)
            n = sum(1 for _ in dst.rglob("*") if _.is_file())
        else:
            shutil.copy2(src, dst)
            n = 1
        manifest.append({"source": rel, "snapshot": dst.name, "files": n})
        print(f"  {rel:34s} -> {dst.name}  ({n} file(s))")
    (d / "_MANIFEST.json").write_text(json.dumps({
        "created": datetime.now().isoformat(timespec="seconds"),
        "created_by": "289_update_collection.py",
        "items": manifest,
        "restore": f"py -3 code/289_update_collection.py --rollback {d}",
    }, indent=1), encoding="utf-8")
    print(f"\n  ROLLBACK:  py -3 code/289_update_collection.py "
          f"--rollback {d}")
    return d


def rollback(dirpath):
    d = Path(dirpath)
    man = d / "_MANIFEST.json"
    hr(f"ROLLBACK from {d}")
    if not man.exists():
        print("  no _MANIFEST.json here. Refusing to guess what to restore.")
        print("  RESTORE BY EXACT FILENAME, NEVER BY GLOB - a glob restore "
              "once\n  reverted seven files belonging to two other agents.")
        return 1
    items = json.loads(man.read_text(encoding="utf-8"))["items"]
    for it in items:
        src = d / it["snapshot"]
        dst = CEDAR / it["source"]
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        print(f"  restored {it['source']} ({it['files']} file(s))")
    print("\n  Restored by exact path from the manifest. data/clean was "
          "never\n  snapshotted and is NOT touched by a rollback - the chain "
          "does not write it.")
    return 0


def run_step(i, label, argv, read_this, gate, dry):
    name = Path(argv[0]).name
    hr(f"{i}  {label}")
    print(f"  $ py -3 {' '.join(argv)}")
    print(f"  READ: {read_this}")
    try:
        CP.guard(name)
    except CP.ForbiddenScript as e:
        print(f"{e}")
        print("  THE CHAIN STOPS. This script is in NEVER_RUN and the guard "
              "is not\n  advisory.")
        return False, None
    if dry:
        print("  [dry run - not executed]")
        return True, None
    t0 = time.time()
    logf = LOGS / f"289_{name.replace('.py', '')}_{TODAY}.log"
    r = subprocess.run(PY + argv, cwd=CEDAR, capture_output=True, text=True)
    logf.write_text(r.stdout + "\n" + r.stderr, encoding="utf-8")
    tail = [ln for ln in r.stdout.splitlines() if ln.strip()][-14:]
    for ln in tail:
        print(f"    {ln[:150]}")
    print(f"  exit {r.returncode} in {time.time() - t0:.1f}s "
          f"-> logs/{logf.name}")
    if r.returncode != 0 and gate:
        print("\n  !! THIS IS A GATE AND IT FAILED. STOP-WORK.")
        print("     Standing rule 15: do not record it as 'pre-existing, "
              "not mine'\n     and continue. Fix it, show the check is "
              "wrong and say why in the\n     script's docstring, or name "
              "the failure and its OWNER in AGENTS.md\n     before doing "
              "anything else.")
        return False, r
    return True, r


def main():
    dry = "--go" not in sys.argv
    if "--rollback" in sys.argv:
        i = sys.argv.index("--rollback")
        return rollback(sys.argv[i + 1]) if i + 1 < len(sys.argv) else 2

    hr("289  UPDATE A COLLECTION" + ("   [DRY RUN]" if dry else ""))
    print("  New source data -> a shippable collection.")
    print("  Default is a DRY RUN. Pass --go to execute.")
    print(f"  Never-run guards: {', '.join(sorted(CP.NEVER_RUN))}")

    ok = preconditions()
    if not ok and not dry:
        print("\n  PRECONDITIONS FAILED. Not starting.")
        print("  Wait for the other agent, or fix the codebook, then re-run.")
        return 1
    if not ok:
        print("\n  (dry run continues so the plan is visible; a real run "
              "would stop here)")

    snap = None if dry else snapshot()
    if dry:
        hr("1  SNAPSHOT")
        print("  [dry run] would snapshot: "
              f"{', '.join(r for r, _ in SNAPSHOT_ITEMS)}")

    preflight()

    for i, (label, argv, read_this, gate) in enumerate(CHAIN, start=3):
        cont, _ = run_step(i, label, argv, read_this, gate, dry)
        if not cont:
            hr("CHAIN STOPPED")
            if snap:
                print(f"  ROLLBACK: py -3 code/289_update_collection.py "
                      f"--rollback {snap}")
            return 1

    hr("DONE")
    if dry:
        print("  Dry run complete. Nothing was executed.")
        print("  Run it for real:  py -3 code/289_update_collection.py --go")
        return 0
    print(f"  Snapshot: {snap}")
    print(f"  Rollback: py -3 code/289_update_collection.py --rollback {snap}")
    print("\n  WHAT TO CHECK BEFORE CALLING IT SHIPPED")
    print("   - the two `62` runs agree, or the AFTER run is better")
    print("   - `87` printed `LICENCE GATE - 2 file(s) REFUSED, by name`")
    print("   - `25` printed every `[licensed] ... dropping` line")
    print("   - `287` printed `0 tables lost columns`")
    print("   - `288`'s vintages are YTD where the period is not complete")
    print("\n  The descriptors are in dist/collections/. NOTHING IS PUSHED "
          "from here:\n  the product repo takes a `claude/*` branch into a "
          "PR, never a direct push.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
