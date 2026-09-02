#!/usr/bin/env python3
"""FIXTURE - invariant I14 in 510 verify: federal recognition is a property
of a GOVERNMENT.

This is not a hypothetical. On 2026-08-30 three ANCSA village CORPORATIONS
carried `entity.is_federally_recognized = yes` at tier A with
support_status = authoritative and winning_source = fr_tribal_list:

    CE-000AW-TW  The English Bay Corporation
    CE-000BP-VP  Russian Mission Native Corporation
    CE-000CB-YK  St. Mary's Native Corporation

Every existing guard passed, because the Federal Register GOVERNMENT name had
been written onto the corporation's spine row as an alias, so 503.resolve()
returned it UNIQUELY - no ambiguity, so the gov-class tiebreak never ran.

The fixture re-injects exactly those three facts and shows verify exits 1,
then restores and shows it exits 0. It also asserts that the three are NOT
present in the live table any more, so it fails if the cause is ever undone.

Run:  py -3 review/fixtures_D/fixture_I14_recognition_class.py
"""
import csv
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
A = ROOT / "data" / "clean" / "cedar_assertions.csv"
R = ROOT / "data" / "clean" / "cedar_resolved_facts.csv"
SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
VERIFY = [sys.executable, str(ROOT / "code" / "510_assertions.py"), "verify"]
BAD = ["CE-000AW-TW", "CE-000BP-VP", "CE-000CB-YK"]
PRED = "entity.is_federally_recognized"


def run():
    p = subprocess.run(VERIFY, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def append(path, rows):
    with path.open(encoding="utf-8-sig", newline="") as fh:
        cols = next(csv.reader(fh))
    with path.open("a", encoding="utf-8", newline="") as fh:
        csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore",
                       restval="").writerows(rows)


# ---- the cause must be fixed, not the symptom hidden ------------------
cls = {}
with SPINE.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
    for r in csv.DictReader(fh):
        if r.get("cedar_uid"):
            cls[r["cedar_uid"]] = r.get("entity_class", "")
live = []
with R.open(encoding="utf-8-sig", newline="") as fh:
    for r in csv.DictReader(fh):
        if r["cedar_uid"] in BAD and r["predicate"] == PRED:
            live.append(r["cedar_uid"])
if live:
    print(f"FIXTURE FAILED: the three bad facts are STILL LIVE: {live}")
    sys.exit(1)

rc0, out0 = run()
if rc0 != 0:
    print("PRECONDITION FAILED: verify is not green before the fixture runs")
    print(out0)
    sys.exit(1)

shutil.copy2(A, str(A) + ".fixturebak")
shutil.copy2(R, str(R) + ".fixturebak")
try:
    arows, rrows = [], []
    for i, uid in enumerate(BAD):
        arows.append(dict(
            assertion_id=f"CA-FIXTUREI14{i:04d}", cedar_uid=uid,
            subject_qualifier="", predicate=PRED, polarity="affirm",
            object_value="yes", object_norm="yes",
            source_id="fr_tribal_list",
            lineage_root_id="LR_FEDERAL_REGISTER",
            lineage_ancestry="LR_FEDERAL_REGISTER",
            independence_is_unverified="0", confidence_tier="A",
            attribution_method="federal_register_roster",
            tier_rationale="fixture", evidence_url="", supporting_quote="",
            verified_date="2026-01-01", origin_table="(fixture)",
            asserted_date="2026-08-30"))
        rrows.append(dict(
            cedar_uid=uid, subject_qualifier="", predicate=PRED,
            object_value="yes", support_status="authoritative",
            resolution_status="RESOLVED", decided_by_rule="R08",
            decided_by_rule_name="UNCONTESTED",
            resolution_policy="STABLE_LEGAL_STATUS", n_assertions="1",
            n_candidate_values="1", n_independent_families="1",
            n_independent_families_current="1", decided_by_coinflip="0",
            conflict="0", competing_values="",
            winning_source="fr_tribal_list", winning_tier="A",
            winning_lineage_root="LR_FEDERAL_REGISTER", evidence_url="",
            resolution_note="", resolved_date="2026-08-30"))
    append(A, arows)
    append(R, rrows)
    rc1, out1 = run()
    i14 = [ln for ln in out1.splitlines() if "I14" in ln]
finally:
    shutil.move(str(A) + ".fixturebak", A)
    shutil.move(str(R) + ".fixturebak", R)

rc2, out2 = run()

fails = []
if rc1 != 1 or not i14:
    fails.append(f"expected exit 1 with an I14 line, got exit {rc1} and "
                 f"{len(i14)} I14 lines")
if rc2 != 0:
    fails.append(f"restore did not return verify to green (exit {rc2})")

print()
if fails:
    print("FIXTURE FAILED:")
    for f in fails:
        print("  !! " + f)
    print(out1[-3000:])
    sys.exit(1)
print("FIXTURE PASSED - I14")
print("  the three real cases are GONE from the live table because the "
      "mechanism was fixed:")
for uid in BAD:
    print(f"    {uid}  [{cls.get(uid, '?')}]  no {PRED} fact")
print(f"  clean                       -> exit {rc0}")
print(f"  re-inject the three facts   -> exit {rc1}")
for ln in i14:
    print("      " + ln.strip()[:160])
print(f"  restored                    -> exit {rc2}")
sys.exit(0)
