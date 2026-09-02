#!/usr/bin/env python3
"""FIXTURE - the semantic diff in 62_no_regression_check.py (gate item).

The claim under test: a rebuild that keeps every aggregate count identical
but changes WHICH entity each fact is about must fail the gate. Every metric
in 62 before this was an aggregate, and an aggregate cannot see a re-keying.

Three injections, each with the ROW COUNTS DELIBERATELY UNCHANGED:

  A. mass winner change - rewrite object_value on 900 resolved facts.
     Row count identical. Must breach the sem_facts_winner_changed ceiling.
  B. mass re-keying     - rotate cedar_uid across resolved facts. Row count
     identical, uid set identical. Must be caught.
  C. uid reassignment   - point one handle at a different uid in the identity
     register. Row count identical. MUST_BE_ZERO, so any single one fails.

Run:  py -3 review/fixtures_D/fixture_semantic_diff.py
"""
import csv
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "data" / "clean" / "cedar_resolved_facts.csv"
REG = ROOT / "data" / "spine" / "cedar_identity_register.csv"
GATE = [sys.executable, str(ROOT / "code" / "62_no_regression_check.py")]
csv.field_size_limit(10_000_000)


def run():
    p = subprocess.run(GATE, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def load(p):
    with p.open(encoding="utf-8-sig", newline="") as fh:
        r = csv.DictReader(fh)
        rows = list(r)
        return rows, r.fieldnames


def save(p, rows, cols):
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, restval="",
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


rc0, out0 = run()
if rc0 != 0:
    print("PRECONDITION FAILED: the gate is not green before the fixture runs")
    print(out0[-4000:])
    sys.exit(1)

shutil.copy2(R, str(R) + ".fixturebak")
shutil.copy2(REG, str(REG) + ".fixturebak")
res = {}
try:
    # ---- A: 900 winners rewritten, row count unchanged ----------------
    rows, cols = load(R)
    n_before = len(rows)
    for r in rows[:900]:
        r["object_value"] = (r["object_value"] or "") + " [FIXTURE]"
    save(R, rows, cols)
    assert len(load(R)[0]) == n_before
    rcA, outA = run()
    res["A"] = (rcA, [l for l in outA.splitlines()
                      if "sem_facts_winner_changed" in l and "ceiling" in l])

    # ---- B: rotate the uid on every fact ------------------------------
    shutil.copy2(str(R) + ".fixturebak", R)
    rows, cols = load(R)
    uids = sorted({r["cedar_uid"] for r in rows})
    rot = {u: uids[(i + 1) % len(uids)] for i, u in enumerate(uids)}
    for r in rows:
        r["cedar_uid"] = rot[r["cedar_uid"]]
    save(R, rows, cols)
    assert len(load(R)[0]) == n_before
    rcB, outB = run()
    res["B"] = (rcB, [l for l in outB.splitlines()
                      if "sem_facts_" in l and ("ceiling" in l or "must" in l)])

    # ---- C: one handle repointed at another uid -----------------------
    shutil.copy2(str(R) + ".fixturebak", R)
    rrows, rcols = load(REG)
    rrows[0]["cedar_uid"] = rrows[1]["cedar_uid"] + ""
    # keep it a VALID-looking uid that already exists, so nothing else trips
    save(REG, rrows, rcols)
    rcC, outC = run()
    res["C"] = (rcC, [l for l in outC.splitlines()
                      if "sem_entities_uid_reassigned" in l and "must be 0" in l])
finally:
    shutil.move(str(R) + ".fixturebak", R)
    shutil.move(str(REG) + ".fixturebak", REG)

rc2, out2 = run()

fails = []
for k, (rc, lines) in res.items():
    if rc != 1 or not lines:
        fails.append(f"case {k}: expected exit 1 with a named semantic "
                     f"failure, got exit {rc} and {len(lines)} matching lines")
if rc2 != 0:
    fails.append(f"restore did not return the gate to green (exit {rc2})")

print()
if fails:
    print("FIXTURE FAILED:")
    for f in fails:
        print("  !! " + f)
    sys.exit(1)
print("FIXTURE PASSED - semantic diff")
print(f"  clean                                  -> exit {rc0}")
for k, label in (("A", "900 winners rewritten, rows unchanged"),
                 ("B", "every fact re-keyed, rows unchanged"),
                 ("C", "one handle repointed at another uid")):
    rc, lines = res[k]
    print(f"  {label:38s} -> exit {rc}  {lines[0].strip()[:110]}")
print(f"  restored                               -> exit {rc2}")
sys.exit(0)
