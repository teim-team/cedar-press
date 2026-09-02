#!/usr/bin/env python3
"""cedar_check.py - THE ONE COMMAND. Runs the right detectors, in the right
order, and prints ONE verdict.

    py -3 code/cedar_check.py            # the standing check: 284 -> 293 -> 160 -> 62
    py -3 code/cedar_check.py --fast     # 293 -> 62 only. Skips the two slow probes.
    py -3 code/cedar_check.py --full     # adds 227 (anomaly) and 301 (freshness)
    py -3 code/cedar_check.py --list     # print the graph and what each tool owns
    py -3 code/cedar_check.py --only 293 # one tool, through this runner

WHY THIS EXISTS
---------------
Six detectors grew up separately and three of them already CONSUME each other:

    284_audit_nondeterministic_keys.py   publishes lint_key_stability()
        |                                 -> class 7
    293_lint_bug_classes.py              publishes count_by_class(),
        |                                 new_since_baseline()
        |    160_ship_gap_report.py      publishes registry_25/27/dist()
        |        |
        +--------+--> 62_no_regression_check.py   THE GATE

`62` already imports 160 and 293 rather than restating their counts, and 293
already imports 284. So the graph was correct; what was missing was an ORDER
and a single verdict. Run 284 and 293 and 160 first and each writes its own
artefact fresh; then 62 reads a current picture instead of yesterday's.

Precedent this follows: `248_audit_tier_inheritance_patterns.py` was a SECOND
detector for one defect class and was RETIRED into 293, because two detectors
for one class drift and a drifted detector is worse than none - it is trusted.
This runner is the same move one level up: one entry point, the individual
tools all still runnable exactly as before.

WHAT THIS DOES NOT DO
---------------------
**It does not weaken `62`.** `62` remains THE GATE and it runs LAST and its
verdict is final: if 62 fails, cedar_check fails, whatever else passed. There
is no flag that makes a 62 failure non-fatal, and `--fast` still runs 62.
Nothing here re-baselines anything - `--baseline` is not forwarded, because a
baseline is a floor and not an acknowledgement button (standing rule 15).

It runs each tool as a SUBPROCESS with this interpreter. It never imports a
build script and never executes one of the NEVER-RUN scripts; the denylist
below is checked before any command is built.

NETWORK: none. 301 is invoked without `--probe-net`.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "code"

# Present and forbidden. Never deleted - a guard you can still see is the guard.
# Mirrors docs/DEPENDENCY_MANIFEST.md "Never run these, ever".
NEVER_RUN = {
    "01_build_entity_spine.py",
    "09_import_rulings.py",
    "41_build_codebooks.py",
    "88_build_deals_taxonomy.py",
    "101_build_lodes_block_employment.py",
    "119_build_digital_and_loyalty.py",
}

# (key, filename, args, what it owns, seconds-ish, lanes it belongs to)
TOOLS = [
    (
        "284",
        "284_audit_nondeterministic_keys.py",
        [],
        "key stability - is any primary key positional, ranked or hash()-derived? "
        "Publishes lint_key_stability(); 293 consumes it as class 7.",
        60,
        {"standing", "full"},
    ),
    (
        "293",
        "293_lint_bug_classes.py",
        [],
        "the linter - EIGHT named defect classes over code/, each against a "
        "recorded floor. THE single lint entry point (248 was folded in here).",
        45,
        {"standing", "fast", "full"},
    ),
    (
        "160",
        "160_ship_gap_report.py",
        [],
        "the ship gap - built-but-never-plumbed. Publishes registry_25/27/dist(), "
        "which 62 imports for every shipping metric. ~2.5 min.",
        150,
        {"standing", "full"},
    ),
    (
        "227",
        "227_anomaly_sweep.py",
        [],
        "year-over-year anomalies across every collection. Slow; periodic, not "
        "per-change.",
        600,
        {"full"},
    ),
    (
        "301",
        "301_source_freshness_probe.py",
        ["--no-snapshot"],
        "source freshness - how long after a period ends does that period stop "
        "growing. Periodic. Run WITHOUT --probe-net here: no network.",
        300,
        {"full"},
    ),
    (
        "62",
        "62_no_regression_check.py",
        [],
        "THE GATE. Imports 160's registries and 293's counts rather than "
        "restating them. A FAIL IS STOP-WORK. Always runs, always last.",
        120,
        {"standing", "fast", "full"},
    ),
]

BY_KEY = {t[0]: t for t in TOOLS}
GATE = "62"


def print_graph() -> None:
    print("cedar_check - the detector graph\n")
    for key, fname, args, owns, secs, lanes in TOOLS:
        star = "  <- THE GATE" if key == GATE else ""
        print(f"  {key:>4}  {fname}{star}")
        print(f"        {owns}")
        print(f"        ~{secs}s | lanes: {','.join(sorted(lanes))}"
              + (f" | args: {' '.join(args)}" if args else ""))
        print()
    print("  order: 284 -> 293 -> 160 -> 62   (each writes the artefact the next reads)")
    print("  full adds 227 and 301 before the gate.")
    print("\n  every tool above is still runnable on its own, unchanged:")
    print("      py -3 code/293_lint_bug_classes.py --class 7")
    print("      py -3 code/62_no_regression_check.py")


def run_one(key: str) -> tuple[int, float, str]:
    _k, fname, args, _owns, _secs, _lanes = BY_KEY[key]
    if fname in NEVER_RUN:  # belt and braces; none of these are detectors
        return 99, 0.0, f"REFUSED - {fname} is on the NEVER-RUN list"
    path = CODE / fname
    if not path.exists():
        return 98, 0.0, f"ABSENT - {path.name} is not in code/"
    t0 = time.time()
    proc = subprocess.run(
        [sys.executable, str(path), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        errors="replace",
    )
    dt = time.time() - t0
    tail = (proc.stdout or "").rstrip().splitlines()
    err = (proc.stderr or "").rstrip().splitlines()
    last = tail[-1] if tail else (err[-1] if err else "")
    return proc.returncode, dt, last[:160]


def main(argv: list[str]) -> int:
    if "--list" in argv:
        print_graph()
        return 0

    if "--only" in argv:
        key = argv[argv.index("--only") + 1]
        if key not in BY_KEY:
            print(f"unknown tool {key!r}; known: {', '.join(BY_KEY)}")
            return 2
        keys = [key]
        lane = f"only {key}"
    elif "--fast" in argv:
        keys = [t[0] for t in TOOLS if "fast" in t[5]]
        lane = "fast"
    elif "--full" in argv:
        keys = [t[0] for t in TOOLS if "full" in t[5]]
        lane = "full"
    else:
        keys = [t[0] for t in TOOLS if "standing" in t[5]]
        lane = "standing"

    # The gate is last, always, and is never dropped from a lane that has it.
    keys = [k for k in keys if k != GATE] + ([GATE] if GATE in keys else [])

    print(f"=== cedar_check ({lane}) : {' -> '.join(keys)} ===\n")
    results: list[tuple[str, int, float, str]] = []
    for k in keys:
        print(f"  running {k} ...", flush=True)
        rc, dt, last = run_one(k)
        results.append((k, rc, dt, last))
        verdict = "ok" if rc == 0 else f"FAIL(rc={rc})"
        print(f"  {k:>4}  {verdict:<12} {dt:6.1f}s  {last}")
    print()

    gate_rc = next((rc for k, rc, _d, _l in results if k == GATE), None)
    failed = [k for k, rc, _d, _l in results if rc != 0]

    print("=== ONE VERDICT ===")
    for k, rc, dt, _l in results:
        _, fname, _, owns, _, _ = BY_KEY[k]
        mark = "PASS" if rc == 0 else "FAIL"
        print(f"  {mark}  {k:>4}  {fname:<38} {dt:6.1f}s")
    print()

    if gate_rc is not None and gate_rc != 0:
        print("  VERDICT: STOP-WORK. The gate (62) failed.")
        print("  A gate failure is not a disposition. Either fix it, or name it")
        print("  AND ITS OWNER in AGENTS.md before continuing. Do not re-baseline.")
        print("  Detail:  py -3 code/62_no_regression_check.py")
        return 1
    if failed:
        print(f"  VERDICT: FAIL in {', '.join(failed)} - the gate passed but a")
        print("  detector did not. Read that tool's own output before continuing.")
        return 1
    print("  VERDICT: PASS - every detector in this lane is clean.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
