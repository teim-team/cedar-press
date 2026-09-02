#!/usr/bin/env python3
"""FIXTURE - the other two failure modes finding F10 raised.

    (a) an OLD equal-tier deny permanently suppressing a NEWER affirmation.
        R06 RECENCY sits near last and is never reached once a value is out
        of contention, so without a policy the refutation is permanent.
    (b) THREE STALE DIRECTORIES beating ONE CURRENT SOURCE on a predicate
        that changes without any legal act.

Both are policy dimensions, not special cases: deny_may_be_older_than_affirm
and corroboration_horizon_days. Each is run against a predicate that DOES
declare it and one that does NOT, so the fixture proves the dimension is
doing the work rather than some global change.

Run:  py -3 review/fixtures_D/fixture_F10b_policy_dimensions.py
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
fails = []


def a(pred, source_id, polarity, tier, value, verified):
    root = M.SOURCES[source_id]["lineage_root"]
    return dict(
        assertion_id=M.aid(UID + "|", pred, M.norm(value), source_id,
                           polarity) + verified.replace("-", ""),
        cedar_uid=UID, subject_qualifier="", predicate=pred, polarity=polarity,
        object_value=value, object_norm=M.norm(value), source_id=source_id,
        lineage_root_id=root,
        lineage_ancestry="|".join(sorted(M.ancestry(root))),
        independence_is_unverified=M.LINEAGE_ROOTS[root][
            "independence_is_unverified"],
        confidence_tier=tier, attribution_method=source_id, tier_rationale="",
        evidence_url="", supporting_quote="", verified_date=verified,
        origin_table="(fixture)", asserted_date="2026-08-30")


def one(rows):
    resolved, conflicts = M.phase_resolve(rows, apply=False)
    return [x for x in resolved if x["cedar_uid"] == UID], conflicts


# =====================================================================
# (a) A STALE DENY MAY NOT SUPPRESS A NEWER AFFIRMATION
#     entity.parent -> OWNERSHIP_AND_STRUCTURE (deny_may_be_older = 0)
#     entity.alias  -> IDENTIFIER_BINDING      (deny_may_be_older = 1)
# =====================================================================
for pred, expect in (("entity.parent", "RESOLVED"),
                     ("entity.alias", "REFUTED_NO_SURVIVOR")):
    rows = [a(pred, "sam_registration", "affirm", "B", "ACME", "2026-06-01"),
            a(pred, "agent_research", "deny", "B", "ACME", "2019-01-01")]
    res, _ = one(rows)
    got = res[0]["resolution_status"] if res else "(nothing resolved)"
    if got != expect:
        fails.append(f"(a) {pred}: expected {expect}, got {got}")

# =====================================================================
# (b) THREE STALE FAMILIES MAY NOT OUT-CORROBORATE ONE CURRENT SOURCE
#     entity.city -> CONTACT_LOCATION (horizon 1095 days, recency above
#                                      tier and families)
#     entity.state -> OWNERSHIP_AND_STRUCTURE (no horizon, families above
#                                      recency)  -> the stale trio wins
# =====================================================================
STALE = "2016-01-01"
FRESH = "2026-06-01"
for pred, expect in (("entity.city", "NEWTOWN"), ("entity.state", "OLDTOWN")):
    rows = [
        a(pred, "bie_school_directory", "affirm", "B", "OLDTOWN", STALE),
        a(pred, "irs_bmf", "affirm", "B", "OLDTOWN", STALE),
        a(pred, "nigc", "affirm", "B", "OLDTOWN", STALE),
        a(pred, "sam_registration", "affirm", "B", "NEWTOWN", FRESH),
    ]
    res, _ = one(rows)
    got = res[0]["object_value"] if res else "(nothing resolved)"
    if got != expect:
        fails.append(f"(b) {pred}: expected {expect}, got {got} "
                     f"(rule {res[0]['decided_by_rule'] if res else '-'})")
    if pred == "entity.city" and res:
        # the honest full family count must still be reported, so I6 and
        # support_status are unaffected by the ranking horizon
        if res[0]["n_independent_families"] != 1:
            fails.append("(b) the reported family count must be the honest "
                         "one for the WINNING value, not the horizoned one")

print()
if fails:
    print("FIXTURE FAILED:")
    for f in fails:
        print("  !! " + f)
    sys.exit(1)
print("FIXTURE PASSED - F10 policy dimensions")
print("  (a) a 2019 deny does NOT suppress a 2026 affirmation on "
      "entity.parent (OWNERSHIP_AND_STRUCTURE), and DOES on entity.alias "
      "(IDENTIFIER_BINDING, where a refutation is the withdrawal mechanism)")
print("  (b) three 2016 families lose to one 2026 source on entity.city "
      "(CONTACT_LOCATION, horizon 1095d) and win on entity.state "
      "(OWNERSHIP_AND_STRUCTURE, no horizon)")
sys.exit(0)
