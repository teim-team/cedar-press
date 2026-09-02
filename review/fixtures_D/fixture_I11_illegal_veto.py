#!/usr/bin/env python3
"""FIXTURE - invariant I11 in 510_assertions.py verify.

I11 recomputes every veto that ACTUALLY happened and fails if any of them
removed a value its predicate's policy protects. It is the check that stops
the F10 ordering bug from being silently reintroduced, because a deleted
value leaves no trace in the resolved table.

Method: inject a synthetic illegal veto into the live assertion and conflict
tables, show `verify` exits 1 naming I11, restore, show it exits 0.
The originals are copied to *.fixturebak and restored in a finally block.

Run:  py -3 review/fixtures_D/fixture_I11_illegal_veto.py
"""
import csv
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
A = ROOT / "data" / "clean" / "cedar_assertions.csv"
C = ROOT / "data" / "clean" / "cedar_fact_conflicts.csv"
VERIFY = [sys.executable, str(ROOT / "code" / "510_assertions.py"), "verify"]

# A real uid, so I4 (subject must exist in the identity register) still holds
# and the only thing this fixture breaks is I11.
REG = ROOT / "data" / "spine" / "cedar_identity_register.csv"
with REG.open(encoding="utf-8-sig", newline="") as fh:
    UID = next(csv.DictReader(fh))["cedar_uid"]
PRED = "entity.is_federally_recognized"


def run():
    p = subprocess.run(VERIFY, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def append(path, rows):
    with path.open(encoding="utf-8-sig", newline="") as fh:
        cols = next(csv.reader(fh))
    with path.open("a", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writerows(rows)


rc0, out0 = run()
if rc0 != 0:
    print("PRECONDITION FAILED: verify is not green before the fixture runs")
    print(out0)
    sys.exit(1)

shutil.copy2(A, str(A) + ".fixturebak")
shutil.copy2(C, str(C) + ".fixturebak")
try:
    # The Federal Register affirms recognition at tier A (it is authority_for
    # this predicate). An owner ruling - authority for NOTHING - denies it at
    # the same tier. STABLE_LEGAL_STATUS forbids that veto.
    affirm = dict(
        assertion_id="CA-FIXTUREAFFIRM01", cedar_uid=UID, subject_qualifier="",
        predicate=PRED, polarity="affirm", object_value="yes",
        object_norm="yes", source_id="fr_tribal_list",
        lineage_root_id="LR_FEDERAL_REGISTER",
        lineage_ancestry="LR_FEDERAL_REGISTER",
        independence_is_unverified="0", confidence_tier="A",
        attribution_method="fixture", tier_rationale="fixture",
        evidence_url="", supporting_quote="", verified_date="2026-01-01",
        origin_table="(fixture)", asserted_date="2026-08-30")
    deny = dict(affirm, assertion_id="CA-FIXTUREDENY0001", polarity="deny",
                source_id="elijah_ruling", lineage_root_id="LR_HUMAN_OWNER",
                lineage_ancestry="LR_HUMAN_OWNER")
    conflict = dict(
        cedar_uid=UID, subject_qualifier="", predicate=PRED,
        losing_value="yes", losing_source="(refuted)", losing_tier="X",
        losing_lineage_root="LR_HUMAN_OWNER", winning_value="",
        winning_source="", decided_by_rule="R01",
        decided_by_rule_name="DENY_VETO",
        assertion_id="CA-FIXTUREDENY0001", evidence_url="",
        note="fixture: an illegal veto of an authoritative affirmation",
        resolved_date="2026-08-30")

    append(A, [affirm, deny])
    append(C, [conflict])

    rc1, out1 = run()
    i11 = [ln for ln in out1.splitlines() if "I11" in ln]
    ok_break = rc1 == 1 and i11
finally:
    shutil.move(str(A) + ".fixturebak", A)
    shutil.move(str(C) + ".fixturebak", C)

rc2, out2 = run()

print()
if not ok_break:
    print(f"FIXTURE FAILED: injected an illegal veto and verify exited {rc1} "
          f"without an I11 line")
    print(out1)
    sys.exit(1)
if rc2 != 0:
    print(f"FIXTURE FAILED: restore did not return verify to green (exit {rc2})")
    print(out2)
    sys.exit(1)
print("FIXTURE PASSED - I11")
print(f"  clean          -> exit {rc0}")
print(f"  illegal veto   -> exit {rc1}  {i11[0].strip()}")
print(f"  restored       -> exit {rc2}")
sys.exit(0)
