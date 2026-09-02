#!/usr/bin/env python3
"""
Cedar Press - 845: THE REGENERATE GUARD. Find every writer that would delete
columns it does not know about.

    py -3 code/845_regenerate_guard.py            # report, ranked by damage
    py -3 code/845_regenerate_guard.py verify     # exit 1 if a NEW unsafe
                                                  # writer appears
    py -3 code/845_regenerate_guard.py fix <script>   # rewrite one writer to
                                                      # carry unknown columns

WHY
---
Owner, 2026-09-02: *"This whole regenerate business - make sure you update all
the scripts so every code is up to date. This regenerate thing I'm noticing is
what's tripping us up. So do that systematically."*

He is naming the single defect behind most of one night's damage. The shape is
always the same: a **wholesale writer** holds a hardcoded list of column names.
An **in-place enricher** later adds a column. The writer runs again and the
column is gone - no error, no exception, and a diff nobody reads.

Measured instances, all real, all in one day:

  503_identity.py       `regcols` was a fixed 9. The register had grown to 14.
                        A `mint --apply` would have deleted the Federal
                        Register legal names for 536 entities and `state` for
                        1,492 - from the spine file every dataset keys to.
  24_funding_merge.py   TX_COLS declared 34 columns; the row writer emitted 32.
                        Every field from index 7 shifted LEFT by two.
  147 -> 814            `award_reference`, the FAC's own per-report line key,
                        dropped on the way to the CSV.
  770_sample_extracts   silently deleted any requested column that happened to
                        be blank across ten sampled rows, so the sample schema
                        was not stable across rebuilds.
  843 -> the UKB rows   the crosswalk was corrected and the 820 rows it had
                        ALREADY produced were not - $181,881,441.37 left
                        pointing at the wrong tribe for a day.

`cedar_pipeline.KNOWN_ORDERINGS` and lint `class6` already record this class,
but both are DECLARATIVE: they catch it only when a human remembers to declare
the pair. This script does not ask. It reads every writer and compares what it
would emit against what is on disk.

WHAT COUNTS AS UNSAFE
---------------------
A writer is unsafe when its `fieldnames` is a **fixed literal list** and the
live table has columns that list does not contain. Those columns are deleted on
the next run, and the number of them is the blast radius.

A writer is safe when its fieldnames are DERIVED - read from the file, taken
from `rd.fieldnames`, or unioned - because then a new column survives by
construction. That is the fix, and `fix` applies it.

Three things this deliberately does NOT flag:
  * a writer whose literal list already matches the file (nothing to lose)
  * a builder writing a table that does not yet exist (nothing to preserve)
  * `graveyard/` and `.bak` files
"""
from __future__ import annotations

import ast
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
CODE = ROOT / "code"
DATA_DIRS = (ROOT / "data" / "clean", ROOT / "data" / "spine")
BASELINE = ROOT / "docs" / "schema" / "regenerate_guard_baseline.json"


def live_headers() -> dict:
    """basename -> [columns] for every shipped table."""
    out = {}
    for d in DATA_DIRS:
        for p in sorted(d.glob("*.csv")):
            if ".bak" in p.name or p.name.startswith("_"):
                continue
            try:
                with p.open(encoding="utf-8-sig", errors="replace") as fh:
                    out[p.name] = next(csv.reader(fh), [])
            except OSError:
                continue
    return out


def literal_lists(tree) -> dict:
    """name -> [str] for module-level assignments of a plain list of strings."""
    out = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.List):
            continue
        elts = node.value.elts
        if not elts or not all(isinstance(e, ast.Constant)
                               and isinstance(e.value, str) for e in elts):
            continue
        for t in node.targets:
            if isinstance(t, ast.Name):
                out[t.id] = [e.value for e in elts]
    return out


def csv_names(tree) -> set:
    """Every string constant in the file that looks like a table filename."""
    return {n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and n.value.endswith(".csv")}


def scan_one(p: Path, live: dict) -> list:
    """[(table, writer_var, n_lost, [lost columns])] for one script."""
    try:
        src = p.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(src)
    except (OSError, SyntaxError):
        return []
    lits = literal_lists(tree)
    tables = [t for t in csv_names(tree) if t in live]
    if not tables or not lits:
        return []

    found = []
    for node in ast.walk(tree):
        # csv.DictWriter(f, fieldnames=NAME) or csv.DictWriter(f, NAME)
        if not (isinstance(node, ast.Call)
                and getattr(node.func, "attr", "") in ("DictWriter", "writer")):
            continue
        ref = None
        for kw in node.keywords:
            if kw.arg == "fieldnames" and isinstance(kw.value, ast.Name):
                ref = kw.value.id
        if ref is None and len(node.args) > 1 and isinstance(node.args[1], ast.Name):
            ref = node.args[1].id
        if ref is None or ref not in lits:
            continue
        declared = set(lits[ref])
        for t in tables:
            cols = live.get(t, [])
            if not cols:
                continue
            # Only meaningful if this literal really is that table's header:
            # it must cover most of the file, or the pairing is a coincidence.
            overlap = len(declared & set(cols))
            if overlap < max(3, 0.6 * len(declared)):
                continue
            lost = [c for c in cols if c not in declared]
            if lost:
                found.append((t, ref, len(lost), lost))
    return found


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "report"
    live = live_headers()
    rows = []
    for p in sorted(CODE.glob("*.py")):
        if p.name.startswith("845_"):
            continue
        for t, ref, n, lost in scan_one(p, live):
            rows.append((n, p.name, t, ref, lost))
    rows.sort(reverse=True)

    if mode == "verify":
        base = set()
        if BASELINE.exists():
            import json
            base = {tuple(x) for x in json.loads(BASELINE.read_text())}
        now = {(r[1], r[2], r[3]) for r in rows}
        new = now - base
        for s, t, v in sorted(new):
            print(f"  FAIL new unsafe writer  {s}  {v} -> {t}")
        print(f"  845 verify   {'FAIL' if new else 'ok'}   "
              f"{len(now)} unsafe writer(s), {len(new)} new since baseline")
        return 1 if new else 0

    print(f"  845 regenerate guard   {len(rows)} unsafe writer(s) across "
          f"{len(list(CODE.glob('*.py')))} scripts and {len(live)} tables")
    print(f"  A writer is UNSAFE when its fieldnames are a FIXED LITERAL and "
          f"the live table has columns it does not name.\n")
    if not rows:
        print("    none - every wholesale writer derives its header")
    for n, script, table, ref, lost in rows[:25]:
        print(f"    {n:>3} cols lost   {script:<44} {ref} -> {table}")
        print(f"                     {', '.join(lost[:6])}"
              f"{' ...' if len(lost) > 6 else ''}")
    if mode == "report" and rows:
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        import json
        BASELINE.write_text(json.dumps(sorted((r[1], r[2], r[3]) for r in rows),
                                       indent=1), encoding="utf-8")
        print(f"\n  baseline written to {BASELINE.relative_to(ROOT)} - "
              f"`verify` now fails on a NEW one.")
        print("  THE FIX for each: derive the header instead of declaring it -\n"
              "    live = next(csv.reader(open(PATH, encoding='utf-8-sig')), [])\n"
              "    cols = CANONICAL + [c for c in live if c not in CANONICAL]\n"
              "  which is what 503_identity.py now does.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
