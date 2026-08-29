#!/usr/bin/env python3
"""FIXTURE - external review F9, grain validation in 512, gated by 62.

Two injections, each restored:

  A. PRIMARY KEY NOT UNIQUE. Duplicate one row of a table whose grain is
     declared. `512 verify` must exit 1 naming the table and the key.
  B. SILENT FAN-OUT. The declared join cardinality on cedar_uid for the
     entity spine is ONE row per value - a lookup. Duplicate one entity's
     uid and 512 must report the fan-out explicitly, because this is the
     failure that multiplies a buyer's award amounts.

Both surface in 62 through `contract_violations`, which is MUST_BE_ZERO, so
a declared grain the data contradicts is release-blocking.

Run:  py -3 review/fixtures_D/fixture_F9_grain_validation.py
"""
import csv
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLAIMS = ROOT / "data" / "clean" / "gaming_source_claims.csv"
SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
V512 = [sys.executable, str(ROOT / "code" / "512_build_dataset_contracts.py"),
        "verify"]
csv.field_size_limit(10_000_000)


def run():
    p = subprocess.run(V512, capture_output=True, text=True, cwd=str(ROOT))
    return p.returncode, p.stdout + p.stderr


def dup_last_row(p):
    with p.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))
    with p.open("a", encoding="utf-8", newline="") as fh:
        csv.writer(fh).writerow(rows[-1])


rc0, out0 = run()
if rc0 != 0:
    print("PRECONDITION FAILED: 512 verify is not green before the fixture")
    print(out0)
    sys.exit(1)

res = {}
for label, path, needle in (("A", CLAIMS, "is NOT unique"),
                            ("B", SPINE, "silent fan-out")):
    shutil.copy2(path, str(path) + ".fixturebak")
    try:
        dup_last_row(path)
        rc, out = run()
        res[label] = (rc, [l for l in out.splitlines() if needle in l])
    finally:
        shutil.move(str(path) + ".fixturebak", path)

rc2, out2 = run()

fails = []
for k, (rc, lines) in res.items():
    if rc != 1 or not lines:
        fails.append(f"case {k}: expected exit 1 with a named grain "
                     f"violation, got exit {rc} and {len(lines)} lines")
if rc2 != 0:
    fails.append(f"restore did not return 512 verify to green (exit {rc2})")

print()
if fails:
    print("FIXTURE FAILED:")
    for f in fails:
        print("  !! " + f)
    sys.exit(1)
print("FIXTURE PASSED - F9 grain validation")
print(f"  clean                       -> exit {rc0}")
print(f"  duplicate primary key       -> exit {res['A'][0]}  "
      f"{res['A'][1][0].strip()[:130]}")
print(f"  cedar_uid fan-out on a hub  -> exit {res['B'][0]}  "
      f"{res['B'][1][0].strip()[:130]}")
print(f"  restored                    -> exit {rc2}")
sys.exit(0)
