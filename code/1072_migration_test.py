#!/usr/bin/env python3
"""Tests for the controlled NEST-to-NEED migration in code/1072.

    py -3 -B code/1072_migration_test.py

Every test runs in a temporary directory against a copy of the real legacy
register. Nothing under data/ is read for writing and nothing is ever written
outside the temporary directory.
"""
import csv
import importlib.util
import os
import shutil
import sys
import tempfile
from pathlib import Path

csv.field_size_limit(10_000_000)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
sys.dont_write_bytecode = True

spec = importlib.util.spec_from_file_location(
    "m1072", str(ROOT / "code" / "1072_tribally_owned_enterprises.py"))
M = importlib.util.module_from_spec(spec)
sys.modules["m1072"] = M
spec.loader.exec_module(M)

LEGACY = ROOT / "data" / "spine" / "cedar_nest_id_register.csv"
PASS = FAIL = 0


def check(label, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ok    {label}")
    else:
        FAIL += 1
        print(f"  FAIL  {label}   {detail}")


def rows_of(p):
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def sandbox():
    """A temp tree with the real legacy register and redirected outputs."""
    d = Path(tempfile.mkdtemp())
    (d / "spine").mkdir()
    (d / "clean").mkdir()
    (d / "staging").mkdir()
    shutil.copy2(LEGACY, d / "spine" / "cedar_nest_id_register.csv")
    M.LEGACY_IDREG = d / "spine" / "cedar_nest_id_register.csv"
    M.IDREG = d / "spine" / "cedar_need_id_register.csv"
    M.OUT_ENT = d / "clean" / "need_enterprises.csv"
    M.OUT_EDGE = d / "clean" / "need_enterprise_relations.csv"
    M.EDGES_STAGED = d / "staging" / "ownership_edges_staged.jsonl"
    M.LEGACY_EDGES = ROOT / "data" / "staging" / "nest" / "ownership_edges_staged.jsonl"
    return d


legacy_rows = rows_of(LEGACY)
LEGACY_IDS = {r["enterprise_id"] for r in legacy_rows}
print(f"legacy register: {len(legacy_rows):,} rows, {len(LEGACY_IDS):,} ids\n")

print("=== migration baseline ===")

# 1. a missing canonical register cannot trigger mass reminting: the migration
#    seeds it, and seeding mints nothing.
d = sandbox()
minted = []
_real_alloc = None
try:
    import cedar_ids
    _real_alloc = cedar_ids.allocate

    def _refuse(prefix, n=1, note=""):
        minted.append((prefix, n))
        raise AssertionError("allocate() called during migration")

    cedar_ids.allocate = _refuse
    rc = M.stage_migrate_legacy([])
finally:
    if _real_alloc:
        cedar_ids.allocate = _real_alloc
check("migrate-legacy exits 0", rc == 0, f"rc={rc}")
check("zero ids minted during the migration baseline", not minted, str(minted))

# 2. all bindings preserved
new_rows = rows_of(M.IDREG)
new_ids = {r["enterprise_id"] for r in new_rows}
check(f"all {len(LEGACY_IDS):,} bindings preserved",
      new_ids == LEGACY_IDS and len(new_rows) == len(legacy_rows),
      f"{len(new_ids)} vs {len(LEGACY_IDS)}")

# 3. every field preserved exactly
by_id_old = {r["enterprise_id"]: r for r in legacy_rows}
by_id_new = {r["enterprise_id"]: r for r in new_rows}
check("every field of every binding preserved exactly",
      all(by_id_old[i] == by_id_new[i] for i in LEGACY_IDS))

# 4. register-only historical bindings survive
ent_path = ROOT / "data" / "clean" / "nest_enterprises.csv"
if ent_path.exists():
    live = {r["enterprise_id"] for r in rows_of(ent_path)}
    hist = LEGACY_IDS - live
    check(f"all {len(hist)} register-only historical bindings survive",
          hist and hist <= new_ids, f"{len(hist & new_ids)}/{len(hist)}")
else:
    check("register-only historical bindings survive (legacy table absent)", True)

# 5. idempotent
rc2 = M.stage_migrate_legacy([])
again = rows_of(M.IDREG)
check("a second migration is a no-op", rc2 == 0 and again == new_rows, f"rc={rc2}")

# 6. a canonical register that DIFFERS is refused, never overwritten
drop = new_rows[:-1]
with open(M.IDREG, "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(new_rows[0].keys()))
    w.writeheader()
    w.writerows(drop)
before = rows_of(M.IDREG)
rc3 = M.stage_migrate_legacy([])
check("a differing canonical register is refused", rc3 == 1, f"rc={rc3}")
check("the differing register is left untouched", rows_of(M.IDREG) == before)

# 7. a conflicting owner/name binding is refused
d = sandbox()
bad = legacy_rows[:50]
clash = dict(bad[0])
clash["enterprise_id"] = "CEDAR-NEST-999999-ZZ"
with open(M.LEGACY_IDREG, "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(legacy_rows[0].keys()))
    w.writeheader()
    w.writerows(bad + [clash])
rc4 = M.stage_migrate_legacy([])
check("a conflicting owner/name binding is refused", rc4 == 1, f"rc={rc4}")
check("no canonical register is written on refusal", not M.IDREG.exists())

print("\n=== build input discipline ===")

# 8. an ordinary build cannot silently use a missing NEED staged input
d = sandbox()
rc5 = M.stage_build([])
check("ordinary build fails closed on missing staged edges", rc5 == 1, f"rc={rc5}")
check("a failed build writes no enterprise table", not M.OUT_ENT.exists())

# 9. the legacy-staging build refuses without a canonical register
d = sandbox()
rc6 = M.stage_build(["--from-legacy-staging"])
check("--from-legacy-staging refuses before migrate-legacy has run",
      rc6 == 1 and not M.OUT_ENT.exists(), f"rc={rc6}")

# 10. preserved legacy evidence cannot bypass the systemic affiliation hold.
import json
for label, observation in [
    ("known token attribution", {"source_id": "OWNERV6", "quote": "attribution_method=cluster_v3 data_sources=sam_master"}),
    ("missing original matching provenance", {"source_id": "OWNERV6"}),
    ("prior reviewed observation still needs a qualified staging release", {"source_id": "OWNERV6", "source_review_status": "reviewed"}),
]:
    d = sandbox()
    shutil.copy2(M.LEGACY_IDREG, M.IDREG)
    M.LEGACY_EDGES = d / "staging" / "legacy.jsonl"
    M.LEGACY_EDGES.write_text(json.dumps(observation) + "\n", encoding="utf-8")
    binding_before = M.IDREG.read_bytes()
    rc = M.stage_build(["--from-legacy-staging"])
    check("legacy quarantine: " + label, rc == 1 and not M.OUT_ENT.exists()
          and not M.OUT_EDGE.exists() and M.IDREG.read_bytes() == binding_before)

print(f"\n{PASS} passed, {FAIL} failed")
raise SystemExit(1 if FAIL else 0)
