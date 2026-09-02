#!/usr/bin/env python3
"""FIXTURE - invariant I13, source-row conservation, in 510 verify.

Two separate breaches, each injected and each restored:

  A. AN UNNAMED DISAPPEARANCE. Inflate one table's rows_in so the
     dispositions no longer reconcile - the shape of a `continue` added to a
     harvest loop with no counter behind it.
  B. AN UNNAMED REASON. Relabel a disposition to "rejected:other". A count
     with no reason is defect class 2c and I13 refuses it by name.

Run:  py -3 review/fixtures_D/fixture_I13_row_conservation.py
"""
import csv
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
C = ROOT / "data" / "clean" / "cedar_harvest_conservation.csv"
VERIFY = [sys.executable, str(ROOT / "code" / "510_assertions.py"), "verify"]


def run():
    p = subprocess.run(VERIFY, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def load():
    with C.open(encoding="utf-8-sig", newline="") as fh:
        r = csv.DictReader(fh)
        return list(r), r.fieldnames


def save(rows, cols):
    with C.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


rc0, out0 = run()
if rc0 != 0:
    print("PRECONDITION FAILED: verify is not green before the fixture runs")
    print(out0)
    sys.exit(1)

shutil.copy2(C, str(C) + ".fixturebak")
results = {}
try:
    rows, cols = load()
    tab = rows[0]["source_table"]

    # ---- A: rows_in inflated, nothing named for the difference --------
    for r in rows:
        if r["source_table"] == tab:
            r["rows_in"] = str(int(r["rows_in"]) + 17)
    save(rows, cols)
    rcA, outA = run()
    results["A"] = (rcA, [l for l in outA.splitlines() if "I13" in l])

    # ---- B: a rejection with no reason --------------------------------
    shutil.copy2(str(C) + ".fixturebak", C)
    rows, cols = load()
    for r in rows:
        if r["disposition"].startswith("rejected:"):
            r["disposition"] = "rejected:other"
            break
    save(rows, cols)
    rcB, outB = run()
    results["B"] = (rcB, [l for l in outB.splitlines() if "I13" in l])
finally:
    shutil.move(str(C) + ".fixturebak", C)

rc2, out2 = run()

fails = []
for k, (rc, lines) in results.items():
    if rc != 1 or not lines:
        fails.append(f"case {k}: expected exit 1 with an I13 line, got exit "
                     f"{rc} and {len(lines)} I13 lines")
if rc2 != 0:
    fails.append(f"restore did not return verify to green (exit {rc2})")

print()
if fails:
    print("FIXTURE FAILED:")
    for f in fails:
        print("  !! " + f)
    sys.exit(1)
print("FIXTURE PASSED - I13")
print(f"  clean                      -> exit {rc0}")
print(f"  A rows vanish unaccounted  -> exit {results['A'][0]}  "
      f"{results['A'][1][0].strip()}")
print(f"  B rejection reason 'other' -> exit {results['B'][0]}  "
      f"{results['B'][1][0].strip()}")
print(f"  restored                   -> exit {rc2}")
sys.exit(0)
