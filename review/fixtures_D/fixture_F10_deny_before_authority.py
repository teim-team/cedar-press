#!/usr/bin/env python3
"""FIXTURE - external review F10. Proof, not assertion.

Builds the exact scenario the reviewer named, in memory, and runs the REAL
resolver over it twice:

    the Federal Register (authority_for entity.is_federally_recognized)
    affirms  yes  at tier A
    an owner ruling (authority_for NOTHING) denies  yes  at tier A

Under the OLD global order (R01 DENY_VETO before R02 AUTHORITY) the
authoritative affirmation is deleted and the fact resolves to
REFUTED_NO_SURVIVOR with an empty value. Under the shipped per-predicate
policy STABLE_LEGAL_STATUS (deny_may_veto_authority = 0) the affirmation
survives and the deny is kept as an R01-BLOCKED contest.

Run:  py -3 review/fixtures_D/fixture_F10_deny_before_authority.py
Exit 0 = both halves behaved as described.
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "cedar_510", ROOT / "code" / "510_assertions.py")
M = importlib.util.module_from_spec(spec)
sys.modules["cedar_510"] = M
spec.loader.exec_module(M)

UID = "CE-FIXTURE-00"
PRED = "entity.is_federally_recognized"


def a(source_id, polarity, tier, value="yes", verified="2026-01-01"):
    root = M.SOURCES[source_id]["lineage_root"]
    return dict(
        assertion_id=M.aid(UID + "|", PRED, M.norm(value), source_id, polarity),
        cedar_uid=UID, subject_qualifier="", predicate=PRED, polarity=polarity,
        object_value=value, object_norm=M.norm(value), source_id=source_id,
        lineage_root_id=root,
        lineage_ancestry="|".join(sorted(M.ancestry(root))),
        independence_is_unverified=M.LINEAGE_ROOTS[root][
            "independence_is_unverified"],
        confidence_tier=tier, attribution_method=source_id, tier_rationale="",
        evidence_url="", supporting_quote="", verified_date=verified,
        origin_table="(fixture)", asserted_date="2026-08-30")


ROWS = [a("fr_tribal_list", "affirm", "A"),
        a("elijah_ruling", "deny", "A")]

fails = []


def run(label):
    resolved, conflicts = M.phase_resolve(list(ROWS), apply=False)
    r = [x for x in resolved if x["cedar_uid"] == UID][0]
    return label, r, conflicts


# ---- 1. THE DEFECT, reproduced by permitting the veto ------------------
M.POLICIES["STABLE_LEGAL_STATUS"]["deny_may_veto_authority"] = True
_, r_old, c_old = run("old")
if r_old["resolution_status"] != "REFUTED_NO_SURVIVOR" or r_old["object_value"]:
    fails.append("the OLD behaviour did not reproduce: expected the "
                 "authoritative affirmation to be deleted, got "
                 f"{r_old['resolution_status']}={r_old['object_value']!r}")

# ---- 2. THE FIX, as shipped -------------------------------------------
M.POLICIES["STABLE_LEGAL_STATUS"]["deny_may_veto_authority"] = False
_, r_new, c_new = run("new")
if r_new["resolution_status"] != "RESOLVED" or r_new["object_value"] != "yes":
    fails.append("the FIX did not hold: expected the authoritative "
                 f"affirmation to survive, got {r_new['resolution_status']}"
                 f"={r_new['object_value']!r}")
if r_new["decided_by_rule"] != "R08":
    fails.append(f"expected R08 UNCONTESTED once the deny is blocked, got "
                 f"{r_new['decided_by_rule']}")
blocked = [c for c in c_new if c["decided_by_rule"] == "R01-BLOCKED"]
if len(blocked) != 1:
    fails.append(f"the blocked deny must be KEPT as a contest; found "
                 f"{len(blocked)} R01-BLOCKED conflict rows, expected 1")
elif "authority_not_yet_consulted" not in blocked[0]["note"]:
    fails.append("the R01-BLOCKED row does not name WHY it was blocked")

# ---- 3. the AUTHORITY retracting ITSELF must still be able to veto -----
M.SOURCES["fr_tribal_list"]["authority_for"].append("__fixture_probe__")
self_deny = [a("fr_tribal_list", "affirm", "A"),
             a("fr_tribal_list", "deny", "A")]
resolved3, _ = M.phase_resolve(self_deny, apply=False)
r3 = [x for x in resolved3 if x["cedar_uid"] == UID][0]
M.SOURCES["fr_tribal_list"]["authority_for"].remove("__fixture_probe__")
if r3["resolution_status"] != "REFUTED_NO_SURVIVOR":
    fails.append("a delisting BY THE AUTHORITY ITSELF must still veto; got "
                 f"{r3['resolution_status']}")

print()
if fails:
    print("FIXTURE FAILED:")
    for f in fails:
        print("  !! " + f)
    sys.exit(1)
print("FIXTURE PASSED - F10")
print(f"  old order (deny before authority): {r_old['resolution_status']} "
      f"value={r_old['object_value']!r}   <- the authoritative fact is GONE")
print(f"  shipped policy STABLE_LEGAL_STATUS: {r_new['resolution_status']} "
      f"value={r_new['object_value']!r} decided_by={r_new['decided_by_rule']}")
print(f"  the blocked deny is kept: {len(blocked)} R01-BLOCKED conflict row")
print(f"  authority retracting itself still vetoes: "
      f"{r3['resolution_status']}")
sys.exit(0)
