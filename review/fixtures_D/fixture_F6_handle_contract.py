#!/usr/bin/env python3
"""FIXTURE - external review F6, the handle contract in 503_identity.py.

Three claims, each proven against the real mint phase on a copy of the real
spine, and every touched file restored in a finally block:

  1. A RECLASSIFICATION KEEPS THE UID. Rename a spine handle (TRBF-... ->
     TRBS-...) and the entity's cedar_uid must not move. Before this change
     `phase_mint` keyed on the handle, missed, and MINTED A SECOND UID.
  2. THE OLD HANDLE STILL RESOLVES. It is retired in
     cedar_handle_history.csv with valid_to set, and `register_map()` -
     the map `stamp` uses to key every dataset - still returns the same uid
     for it.
  3. A RETIRED HANDLE IS NEVER REUSED. Pointing the retired handle at a
     different entity must RAISE, not warn.

Run:  py -3 review/fixtures_D/fixture_F6_handle_contract.py
"""
import csv
import importlib.util
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "cedar_503", ROOT / "code" / "503_identity.py")
M = importlib.util.module_from_spec(spec)
sys.modules["cedar_503"] = M
spec.loader.exec_module(M)

SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
REG = ROOT / "data" / "spine" / "cedar_identity_register.csv"
HIST = ROOT / "data" / "spine" / "cedar_handle_history.csv"
TOUCHED = [SPINE, REG, HIST]
fails = []


def rows(p):
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as f:
        return list(csv.DictReader(f)), csv.DictReader(
            p.open(encoding="utf-8-sig", newline="")).fieldnames


def rewrite_spine(mutate):
    rs, cols = rows(SPINE)
    mutate(rs)
    with SPINE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, restval="",
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(rs)


for p in TOUCHED:
    shutil.copy2(p, str(p) + ".fixturebak")
try:
    reg0, _ = rows(REG)
    victim = next(r for r in reg0 if r["handle"].startswith("TRBF-"))
    OLD, UID = victim["handle"], victim["cedar_uid"]
    NEW = "TRBS-" + OLD.split("-", 1)[1]

    # ---- 1 + 2: reclassify -------------------------------------------
    def to_new(rs):
        for r in rs:
            if (r.get("tribe_id") or "").strip() == OLD:
                r["tribe_id"] = NEW
                r["entity_class"] = "State-recognized tribe"

    rewrite_spine(to_new)
    M.phase_mint(["--apply"])

    reg1, _ = rows(REG)
    now = {r["handle"]: r["cedar_uid"] for r in reg1}
    if now.get(NEW) != UID:
        fails.append(f"1. the uid MOVED on reclassification: {OLD}={UID} -> "
                     f"{NEW}={now.get(NEW)}")
    if len(reg1) != len(reg0):
        fails.append(f"1. the register changed size {len(reg0)} -> {len(reg1)}"
                     f" - a reclassification must not add or drop an entity")

    hist, _ = rows(HIST)
    old_row = [h for h in hist if h["handle"] == OLD]
    if not old_row:
        fails.append("2. the old handle has NO history row - it no longer "
                     "resolves and a buyer joined on it loses their rows")
    else:
        h = old_row[0]
        if h["status"] != "retired" or not h["valid_to"]:
            fails.append(f"2. the old handle is not properly retired: "
                         f"status={h['status']!r} valid_to={h['valid_to']!r}")
        if h["cedar_uid"] != UID:
            fails.append("2. the retired handle resolves to a different uid")
    if M.handle_resolution_map().get(OLD) != UID:
        fails.append("2. handle_resolution_map() does not resolve the "
                     "retired handle")
    if M.register_map().get(OLD) != UID:
        fails.append("2. register_map() - the map `stamp` keys every dataset "
                     "with - does not resolve the retired handle")
    hv = M.verify_handles()
    if hv:
        fails.append(f"2. verify_handles() failed after a legal "
                     f"reclassification: {hv[:2]}")

    # ---- 3: reuse the retired handle for a DIFFERENT entity -----------
    other = next(r for r in reg1
                 if r["cedar_uid"] != UID and r["handle"].startswith("TRBF-"))

    def reuse(rs):
        for r in rs:
            if (r.get("tribe_id") or "").strip() == other["handle"]:
                r["tribe_id"] = OLD

    rewrite_spine(reuse)
    try:
        M.phase_mint(["--apply"])
        fails.append("3. reusing a RETIRED handle for a different entity was "
                     "ACCEPTED - it must raise HandleReuse")
    except M.HandleReuse as e:
        reuse_msg = str(e)[:150]
finally:
    for p in TOUCHED:
        shutil.move(str(p) + ".fixturebak", p)

print()
if fails:
    print("FIXTURE FAILED:")
    for f in fails:
        print("  !! " + f)
    sys.exit(1)
print("FIXTURE PASSED - F6 handle contract")
print(f"  1. {OLD} -> {NEW}: cedar_uid stayed {UID}")
print(f"  2. {OLD} is retired with a valid_to and still resolves to {UID} "
      f"through register_map()")
print(f"  3. reusing it raised HandleReuse: {reuse_msg}")
print("  every touched file restored from *.fixturebak")
sys.exit(0)
