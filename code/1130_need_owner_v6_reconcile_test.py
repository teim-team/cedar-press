"""Regression tests for code/1130: handle bridge, INTERTRIBAL rules, R3 additions.

    py -3 -B code/1130_need_owner_v6_reconcile_test.py

Every test runs against the repository's 1130 and the real register/alias
tables. Nothing is written anywhere.
"""
import csv
import collections
import importlib.util
import os
import sys
from pathlib import Path

csv.field_size_limit(10_000_000)
REPO = Path(__file__).resolve().parent.parent
SCRATCH = None  # repository suite: no scratch tree
os.chdir(REPO)
sys.path.insert(0, str(REPO / "code"))
spec = importlib.util.spec_from_file_location(
    "t1130", str(REPO / "code" / "1130_need_owner_v6_reconcile.py"))
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

M.REGISTER = str(REPO / "data/spine/cedar_identity_register.csv")
M.ALIASES = str(REPO / "data/clean/entity_aliases.csv")
REG = M.rd(M.REGISTER)
ALIAS = M.load_alias_index()

PASS = FAIL = 0


def check(label, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ok    {label}")
    else:
        FAIL += 1
        print(f"  FAIL  {label}   {detail}")


def resolve(tid, name):
    return M.resolve_intertribal(tid, name, REG, ALIAS)


print("=== INTERTRIBAL resolution rules ===")

# 1. exact organisation-to-organisation match resolves
uid, method, _ = resolve("INTERTRIBAL-ITCA-00", "Inter-Tribal Council of Arizona")
check("exact name resolves via intertribal_exact_name_class",
      uid == "CE-000R1-YS" and method == "intertribal_exact_name_class", f"{uid} {method}")

# 2. a verified acronym suffix resolves
uid, method, _ = resolve("INTERTRIBAL-NCAI-00", "National Congress of American Indians (NCAI)")
check("verified acronym suffix resolves via intertribal_exact_name_class_acronym",
      uid == "CE-000R8-88" and method == "intertribal_exact_name_class_acronym", f"{uid} {method}")

# 3. an acronym that is a registered alias of TWO entities cannot identify one
uid, method, _ = resolve("INTERTRIBAL-NACA-00", "Native American Contractors Association (NACA)")
check("conflicting acronym alias stays unresolved (NACA -> 2 entities)",
      uid == "" and "ACRONYM_AMBIGUOUS" in method, f"{uid} {method}")

# 4. an unregistered trailing token is initials, not evidence
uid, method, _ = resolve("INTERTRIBAL-ZZZZ-00", "National Congress of American Indians (ZZZZ)")
check("unregistered trailing token stays unresolved",
      uid == "" and "ACRONYM" in method, f"{uid} {method}")

# 5. an intertribal value may not resolve to a non-Intertribal class
tribe = next((r for r in REG if (r.get("entity_class") or "") == "Federally recognized tribe"
              and (r.get("canonical_name") or "").strip()), None)
uid, method, _ = resolve("INTERTRIBAL-XXX-00", tribe["canonical_name"])
check("cannot resolve to a tribe or any non-Intertribal class",
      uid == "", f"resolved to {uid} via {method} (target {tribe['cedar_uid']})")

# 6. no target at all stays unresolved
uid, method, _ = resolve("INTERTRIBAL-FNDI-00", "First Nations Development Institute")
check("no registered intertribal target stays unresolved",
      uid == "" and "NOT_IN_REGISTER" in method, f"{uid} {method}")

# 7. token similarity alone cannot resolve
uid, method, _ = resolve("INTERTRIBAL-QQ-00", "Council of Arizona")
check("token similarity alone cannot resolve",
      uid == "", f"resolved to {uid} via {method}")

# 8. INTERTRIBAL never reaches the generic token route
uid, method, _ = M.resolve_parent("INTERTRIBAL-NCAI-00",
                                  "National Congress of American Indians (NCAI)",
                                  {}, {}, REG, ALIAS)
check("resolve_parent routes INTERTRIBAL away from the generic token route",
      method.startswith("intertribal_") or method.startswith("UNRESOLVED_INTERTRIBAL"), method)

print("\n=== R3 dual-role additions: evidence contract ===")
DSBS = M.rd(str(REPO / "data/raw/external/sba_dsbs_native_entities.csv"))
by_name = collections.defaultdict(list)
for r in DSBS:
    by_name[M.norm(r.get("name_clean", ""))].append(r)
R3 = ["CE-001HE-DQ", "CE-001J3-GM", "CE-001JF-R0", "CE-001JQ-88", "CE-001KE-QQ",
      "CE-001NT-93", "CE-001PQ-W8", "CE-001R3-EM", "CE-001RT-RK"]
regby = {(r.get("cedar_uid") or "").strip(): r for r in REG}
for uid in R3:
    r = regby.get(uid, {})
    nm = M.norm(r.get("canonical_name") or "")
    hits = by_name.get(nm, [])
    unique = len(hits) == 1
    has_ids = unique and bool((hits[0].get("uei") or "").strip()) and bool((hits[0].get("cage_code") or "").strip())
    check(f"R3 {uid} has exactly one DSBS exact-legal-name match with UEI and CAGE",
          unique and has_ids, f"hits={len(hits)}")

print("=== registered-full-name + canonical-acronym (NAFOA class) ===")

uid, method, _ = resolve("INTERTRIBAL-NAFOA-00", "Native American Finance Officers Association (NAFOA)")
check("expanded registered alias + canonical acronym resolves under its own method",
      uid == "CE-000S6-16" and method == "intertribal_registered_full_name_plus_canonical_acronym",
      f"{uid} {method}")

_exp = ALIAS.get(M.norm("Native American Finance Officers Association"), set())
_acr = ALIAS.get("nafoa", set())
check("both components map independently and uniquely to the same cedar_uid",
      _exp == {"CE-000S6-16"} and _acr == {"CE-000S6-16"}, f"expanded={_exp} acronym={_acr}")

uid, method, _ = resolve("INTERTRIBAL-NAFOA-00", "Completely Unregistered Expansion (NAFOA)")
check("canonical acronym without a registered expanded-name alias does not resolve",
      uid == "", f"resolved to {uid} via {method}")

uid, method, _ = resolve("INTERTRIBAL-NACA-00", "Native American Contractors Association (NACA)")
check("conflicting multi-entity alias remains unresolved",
      uid == "" and "AMBIGUOUS" in method, f"{uid} {method}")

_dual_path = REPO / "data" / "clean" / "need_entity_dual_role.csv"
if _dual_path.exists():
    _dual = {r["cedar_uid"]: r for r in M.rd(str(_dual_path))}
    _r1 = _dual.get("CE-000S6-16", {})
    check("R1 dual-role row implies no ownership, UEI, CAGE or DSBS registration",
          bool(_r1) and _r1.get("is_need_owner_hub") == "N"
          and str(_r1.get("n_need_enterprises_owned")) in ("0", "")
          and not (_r1.get("own_uei") or "").strip()
          and not (_r1.get("own_cage") or "").strip()
          and "R1_DECLARED_BY_OWNER_DATASET" in (_r1.get("evidence_rungs") or ""),
          str(_r1))
else:
    print("  skip  R1 dual-role row contract (canonical table not generated yet)")


print("=== exact reconciliation instead of an unmatched-count quota ===")
owner = [{"tribe_id": "old", "enterprise_name": "Sample LLC"}]
xwalk = [{"owner_tribe_id": "old", "cedar_uid": "CE-test"}]
need = [{"owner_hub_cedar_uid": "CE-test", "enterprise_name_normalized": "sample", "enterprise_id": "issued"}]
record = {"cedar_uid": "CE-test", "enterprise_name_normalized": "sample", "reconciliation_status": "ALREADY_IN_NEED", "matched_need_enterprise_id": "issued"}
check("zero net-new is valid when every pinned owner key already exists", not M.reconciliation_issues(owner, xwalk, need, [record]))
check("missing owner cluster is refused", bool(M.reconciliation_issues(owner, xwalk, need, [])))
check("duplicate cluster is refused", bool(M.reconciliation_issues(owner, xwalk, need, [record, record])))
check("false net-new is refused", bool(M.reconciliation_issues(owner, xwalk, need, [dict(record, reconciliation_status="NET_NEW_TO_NEED")])))
check("wrong existing ID is refused", bool(M.reconciliation_issues(owner, xwalk, need, [dict(record, matched_need_enterprise_id="other")])))
check("ambiguous parent crosswalk is refused", bool(M.reconciliation_issues(owner, xwalk + [{"owner_tribe_id": "old", "cedar_uid": "CE-other"}], need, [record])))

print("=== evidence family is not evidence of the parent relationship ===")
_s = importlib.util.spec_from_file_location("builder1133", str(REPO / "code/1133_need_owner_v6_builder_input.py"))
_b = importlib.util.module_from_spec(_s)
_s.loader.exec_module(_b)
for _source, _family in [
    ("data/other/tribal_colleges_aihec.csv (AIHEC list)", "compiled_directory"),
    ("https://unverified.example/companies", "unattributed"),
    ("https://www.aihec.org/tcu-roster-and-profiles/", "unattributed"),
    ("https://search.certifications.sba.gov/", "federal_registry"),
    ("https://www.irs.gov/charities", "federal_registry"),
    ("user_final_tribes.dta", "human_ruling"),
]:
    _actual, _basis = M.family_of(_source)
    check("source family: " + _source, _actual == _family, str((_actual, _basis)))
    check("source alone cannot become parent company list: " + _source,
          _b.FAMILY_TO_EVIDENCE_CLASS[_actual][0] != "parent_self_published_company_list")
check("even a legacy self-published family label does not prove the parent relationship",
      _b.FAMILY_TO_EVIDENCE_CLASS["entity_self_published"][0] == "owner_research_dataset_unattributed")

print("=== imported automated affiliation routes fail closed ===")
from types import SimpleNamespace
_stub72 = SimpleNamespace(tidy=lambda x: x.strip(), norm=M.norm, _edge=lambda **kw: kw)
_calls = []
def _known_parent(*args):
    _calls.append(args)
    return "CE-KNOWN", "handle_exact", "known parent is not relationship evidence"
_stub30 = SimpleNamespace(resolve_parent=_known_parent, family_of=M.family_of)
_reg = [{"cedar_uid": "CE-KNOWN", "canonical_name": "Known Parent", "entity_class": "Federally recognized tribe"}]
for _name, _ds, _am in [
    ("Black Mesa Community School", "master_entity_registry", "cluster_v3"),
    ("SAN CARLOS APACHE COLLEGE", "irs_990_bmf_strict", ""),
    ("FOUR CORNER PEST CONTROL LLC", "sba_dsbs_native_entities", ""),
    ("Saginaw Chippewa Tribal College", "aihec_tribal_colleges", ""),
    ("Little Priest Tribal College", "aihec_tribal_colleges", ""),
    ("Known Parent", "aihec_tribal_colleges", ""),
    ("Navajo Times", "ch2_tribal_press_corpus", ""),
    ("Southern Ute Drum", "ch2_tribal_press_corpus", ""),
    ("Char-Koosta News", "ch2_tribal_press_corpus", ""),
]:
    _source = {"tribe_id": "KNOWN", "canonical_name": "Known Parent", "enterprise_name": _name,
               "data_sources": _ds, "attribution_method": _am,
               "verification_source": "https://www.irs.gov/charities"}
    _calls.clear()
    _edges, _refused, _held, _counts, _xwalk = _b.classify(
        [_source], _stub72, _stub30, {}, {}, _reg, {"CE-KNOWN": _reg[0]}, {}, set(), {})
    check("known parent and URL cannot bypass route quarantine: " + _name,
          not _edges and len(_refused) == 1
          and _refused[0]["refusal"] == "AUTOMATED_AFFILIATION_ROUTE_QUARANTINED"
          and _refused[0]["enterprise_name"] == _name and not _calls)
_hand = dict(_source, data_sources="master_entity_registry", attribution_method="hand",
             verification_source="user_final_tribes.dta")
_edges, _refused, _, _, _ = _b.classify(
    [_hand], _stub72, _stub30, {}, {}, _reg, {"CE-KNOWN": _reg[0]}, {}, set(), {})
check("explicit prior hand ruling is not automatically rejected by route quarantine",
      len(_edges) == 1 and not _refused and _edges[0]["source_review_status"] == "reviewed")

print(f"\n{PASS} passed, {FAIL} failed")
raise SystemExit(1 if FAIL else 0)
