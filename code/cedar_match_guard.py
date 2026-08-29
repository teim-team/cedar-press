#!/usr/bin/env python3
"""
Cedar Press - the central match guard. DRAFT, NOT YET WIRED IN.

SPEC v2 §7.3: "Central containment/specificity guard ... implemented once in the
shared matcher; the four local fixes it replaces become its regression tests."

It is ten now, not four. Every veto below is a defect that reached production
and moved money or misnamed a party. This module is the ONE place they live.

HOW IT IS MEANT TO BE USED
--------------------------
This is a VETO LAYER, not a second matcher. Standing rule 8 says one resolver;
this does not resolve anything. `resolve_entity` proposes, the guard disposes:

    tid, canon, how = resolve_entity(name, spine)
    if tid:
        ok, reason = guard(name, spine_row_for(tid), how, context)
        if not ok:
            tid = None      # refused, with `reason` recorded

`context` carries what the caller knows and the resolver does not - the record's
state, its entity class, whether an owner was named in evidence. More context
means fewer false refusals; with none, the guard is deliberately strict.

THE ONE THING THAT MAKES IT SAFE TO ADOPT
-----------------------------------------
Every veto ships with the real case that caused it, as a test. Wiring this in
is only safe if `python cedar_match_guard.py` passes - which asserts that all
ten historical failures are refused AND that the known-good matches still pass.
A guard that only refuses is easy; the tests are the hard half.

RUN:  py -3 code/cedar_match_guard.py       # self-test, no side effects
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from cedar_domain import NAME_TRAPS, ENTITY_CLASSES, canonical_entity_class
except ImportError:
    NAME_TRAPS = frozenset()
    ENTITY_CLASSES = frozenset()

    def canonical_entity_class(v, strict=False):
        return (v or "").strip()

# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------

# Words `core()` treats as structural. Folding them is what lets
# "Cook Inlet Region, Inc." match "Cook Inlet Region, Incorporated" - correct.
# But see VETO 8: folding them is WRONG when they are the only difference.
STRUCTURAL = {
    "nation", "nations", "tribe", "tribes", "tribal", "band", "bands",
    "pueblo", "community", "communities", "rancheria", "village", "villages",
    "colony", "indians", "indian", "native", "peoples", "people",
    "reservation", "confederated", "of", "the", "and",
    "inc", "incorporated", "llc", "llp", "ltd", "corp", "corporation",
    "company", "co", "group", "holdings", "enterprises", "enterprise",
}

# An institution is a SEPARATE LEGAL PERSON from the tribe it is named for.
INSTITUTION_MARKERS = {
    "school", "schools", "college", "university", "academy", "institute",
    "seminary", "dormitory", "headstart",
    "hospital", "clinic", "health", "medical", "wellness",
    "housing", "authority", "commission", "board", "council", "agency",
    "department", "bureau", "office", "program", "project",
    "foundation", "fund", "trust", "endowment", "charities", "charitable",
    "museum", "library", "cultural", "heritage", "center", "centre",
    "association", "alliance", "coalition", "society", "institute",
    "credit", "bank", "union", "cdfi",
}

# A government is not the tribe whose land it sits on.
MUNICIPAL_MARKERS = {
    "city", "county", "township", "borough", "parish", "municipal",
    "district", "state", "commonwealth", "dept", "department",
    "university", "regents", "trustees",
}

# THE SPLIT THAT MATTERS. `core()` folds both sets, but they are not alike:
#
#   CORPORATE_NOTATION - interchangeable spellings of the same legal form.
#     "Cook Inlet Region, Inc." IS "Cook Inlet Region, Incorporated".
#     Elijah: "it asks is this cook inlet and it literally says cook inlet".
#     Folding these is CORRECT and VETO 2 must not fire on them.
#
#   IDENTITY_WORDS - folded for convenience, but they carry identity.
#     "National Education Association" is NOT "National Indian Education
#     Association". Folding `indian` made two unrelated bodies identical.
#     VETO 2 fires here.
CORPORATE_NOTATION = {
    "inc", "incorporated", "llc", "llp", "ltd", "corp", "corporation",
    "company", "co", "group", "holdings", "enterprises", "enterprise",
    "the", "of", "and",
}
IDENTITY_WORDS = STRUCTURAL - CORPORATE_NOTATION

# Words that are weak ON THEIR OWN even though they are not traps. Distinct
# from NAME_TRAPS, which are names that collide with real places and tribes.
GENERIC_SINGLE_TOKENS = {
    "services", "solutions", "systems", "technologies", "technology",
    "construction", "development", "management", "consulting", "industries",
    "resources", "partners", "ventures", "associates", "contracting",
    "federal", "national", "american", "general", "global", "united",
}

CORPORATE_FORM = re.compile(
    r"\b(inc|incorporated|llc|l\.l\.c|llp|ltd|corp|corporation|company|co)\b",
    re.I)

ADDRESS = re.compile(
    r"\b\d{2,6}\s+\w+.*\b(ave|avenue|st|street|rd|road|blvd|boulevard|dr|"
    r"drive|ln|lane|hwy|highway|pkwy|parkway|suite|ste|po box)\b", re.I)


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def toks(s):
    return set(norm(s).split())


def core(s):
    return frozenset(t for t in norm(s).split() if t not in STRUCTURAL)


# ---------------------------------------------------------------------------
# The guard
# ---------------------------------------------------------------------------

def guard(record_name, entity, how="containment", context=None):
    """Return (allowed, reason). `entity` is a spine row dict.

    `context` may carry: record_state, record_class, owner_named_in_evidence,
    entity_is_only_candidate.
    """
    ctx = context or {}
    rn, en = record_name or "", entity.get("canonical_name", "")
    rt, et = toks(rn), toks(en)
    rc, ec = core(rn), core(en)
    ecls = (entity.get("entity_class") or "").lower()

    # An owner named in retrieved evidence is not a guess. Containment is
    # allowed to CONFIRM it - that is the one use AGENTS.md still permits.
    if ctx.get("owner_named_in_evidence"):
        return True, "owner named in evidence"

    # --- VETO 1: the record is an ADDRESS, not an organisation --------------
    # "2333 Biddle Ave, Wyandotte, MI" -> Wyandotte Nation (earmarks build)
    if ADDRESS.search(rn):
        return False, "record is a postal address, not an organisation name"

    # --- VETO 2: distinguishing token folded away --------------------------
    # core() strips `indian`, so "National Education Association" and
    # "National Indian Education Association" BOTH reduce to
    # {national, education, association} - an exact core match between two
    # unrelated organisations. A structural word that appears in one name and
    # not the other is NOT noise; it is the identity.
    only_in_e = (et - rt) & IDENTITY_WORDS
    only_in_r = (rt - et) & IDENTITY_WORDS
    if (only_in_e or only_in_r) and rc == ec:
        diff = sorted(only_in_e | only_in_r)
        return False, (f"names differ only by folded token(s) {diff} - "
                       f"the folded word is the identity")

    # --- VETO 3: institution named after a tribe is not the tribe ----------
    # Chickasaw Nation -> Chickasaw Children's Village ($2.8B)
    # Sequoyah High School -> Sequoyah Fund Inc.
    # Institute of American Indian Arts Foundation -> the Institute
    r_inst = rt & INSTITUTION_MARKERS
    e_inst = et & INSTITUTION_MARKERS
    if r_inst and not e_inst and ec <= rc:
        return False, (f"record is an institution ({sorted(r_inst)}) named for "
                       f"the entity; a separate legal person")
    if e_inst and not r_inst and rc <= ec:
        return False, (f"entity is an institution ({sorted(e_inst)}); the "
                       f"record names something broader")

    # --- VETO 4: municipal / state body is not a tribe ---------------------
    # "SPOKANE, CITY OF" -> Spokane Tribe; "FL DEPT OF HEALTH" -> Native Health
    if rt & MUNICIPAL_MARKERS and not (et & MUNICIPAL_MARKERS):
        return False, (f"record is a governmental/municipal body "
                       f"({sorted(rt & MUNICIPAL_MARKERS)}), not a Native entity")

    # --- VETO 5: specificity - the record must be at least as specific ------
    # This is the rule AGENTS.md states. A shorter entity name inside a longer
    # record is a DIFFERENT entity unless corroborated.
    if ec < rc and not ctx.get("record_state") and not ctx.get("entity_is_only_candidate"):
        extra = sorted(rc - ec)
        return False, (f"record carries distinguishing tokens the entity does "
                       f"not: {extra[:4]} - and nothing corroborates")

    # --- VETO 6: state disagreement ---------------------------------------
    # Indian Pueblo Cultural Center (NM) -> Makaha (HI)
    #
    # BUT a tribe's SEAT is not the limit of where it operates. Measured
    # 2026-08-07: **Zuni is seated in New Mexico and holds three ARIZONA gaming
    # compacts.** A bare state check refuses that correct resolution. The
    # device build hit this and solved it by reading Cedar's own compacts.csv
    # rather than hard-coding a state.
    #
    # So the caller may pass `entity_operates_in` - any additional states the
    # entity is known to operate in, from compacts, facilities or filings. The
    # veto fires only when the record's state is in NEITHER the seat NOR the
    # operating set.
    rs = (ctx.get("record_state") or "").upper()
    es = (entity.get("state") or "").upper()
    also = {s.strip().upper() for s in (ctx.get("entity_operates_in") or [])}
    if rs and es and rs != es and rs not in also:
        extra = f" (also operates in {sorted(also)})" if also else ""
        return False, f"state disagreement: record {rs} vs entity {es}{extra}"

    # --- VETO 7: corporate form vs Alaska village GOVERNMENT ---------------
    # Only where an ANCSA corporation counterpart exists; NOT in the lower 48,
    # where tribes own companies directly (Chickasaw Nation Industries).
    if (CORPORATE_FORM.search(rn)
            and "alaska native village" in ecls
            and ctx.get("anvc_counterpart_exists")):
        return False, ("corporate name resolving to an Alaska village "
                       "GOVERNMENT while its ANCSA corporation exists")

    # --- VETO 8: trap token carrying the match alone -----------------------
    # United / San / Little / Rancheria / Central / Creek ...
    shared = rc & ec
    if shared and shared <= NAME_TRAPS and not rs:
        return False, (f"match rests only on trap token(s) {sorted(shared)} "
                       f"with no corroborating evidence")

    # --- VETO 9: single GENERIC token ---------------------------------------
    # A short token is not weak because it is short. **Many tribal names are
    # three or four characters** - Zuni, Hopi, Crow, Ute, Kaw, Sac, Yurok - and
    # a blanket length rule refuses every one of them. Drafted that way, this
    # veto killed a correct Zuni resolution.
    #
    # What makes a single token weak is being GENERIC or a known trap, not
    # being short. `NAME_TRAPS` already carries the measured ones: eagle,
    # river, central, united, san, little, indian, native, rancheria...
    only = next(iter(shared), "") if len(shared) == 1 else ""
    if only and (only in NAME_TRAPS or only in GENERIC_SINGLE_TOKENS):
        return False, f"match rests on one generic/trap token {sorted(shared)}"

    # --- VETO 10: nothing distinctive shared at all ------------------------
    if not shared:
        return False, "no distinctive token shared after folding"

    return True, "passed all vetoes"


# ---------------------------------------------------------------------------
# Regression tests - every historical failure, plus the goods that must survive
# ---------------------------------------------------------------------------

#
# THREE THINGS THIS FIXTURE DID WRONG, FIXED 2026-08-26 BY
# `code/442_consolidate_entity_class_vocabulary.py`. All three are the same
# shape - **a test that passes for the wrong reason** - and this project has
# now found that shape three times in one day (here, in `284`, and in FA-02's
# own regression detector).
#
# 1. **The `entity_class` on the Sequoyah case was a string the spine does not
#    have.** It read `Native CDFI`; the spine says
#    `Native Community Development Financial Institution`. Nothing noticed,
#    because nothing in this file ever read that field on that case - the
#    refusal came from VETO 6, the state disagreement, and the class was
#    decoration. `assert_fixture_classes_are_real()` now fails on it.
#
# 2. **Every case recorded WHY it should be refused in a comment, and nothing
#    checked that it was refused for THAT reason.** So a veto could rot away
#    entirely and its case would stay green on the back of an unrelated one.
#    Each case now carries `expect`, a substring of the reason the guard must
#    return, and a case refused by the wrong veto FAILS.
#
# 3. **VETO 7 - the ANCSA corporate-form veto, the one that carries the
#    owner's $24.52B ruling into the matcher - was exercised by NO case at
#    all.** The Elim case looks like it tests VETO 7 and does not: it passes
#    `context={}`, so `anvc_counterpart_exists` is falsy, VETO 7 cannot fire,
#    and the refusal comes from VETO 2 on the folded token `village`. Both
#    readings are now cases, and they are named for the veto each proves.
#
# The self-test also EXITS NON-ZERO now. It counted failures and returned 0,
# so no runner, hook or gate could ever have failed on it.
#


def _e(name, cls="Federally recognized tribe", state=""):
    return {"canonical_name": name, "entity_class": cls, "state": state}


# (record_name, entity, context, expected-reason substring, what it proves)
MUST_REFUSE = [
    ("Chickasaw Children's Village", _e("The Chickasaw Nation"), {},
     "distinguishing tokens", "VETO 5 - institution named for a tribe ($2.8B)"),
    ("Sequoyah High School",
     _e("Sequoyah Fund Inc.",
        "Native Community Development Financial Institution", "NC"),
     {"record_state": "OK"},
     "state disagreement",
     "VETO 6 - cross-state. NOTE the class here does NOT drive the refusal; "
     "it is carried so the fixture-class check has something real to check"),
    ("Indian Pueblo Cultural Center", _e("Makaha Cultural Learning Center", state="HI"),
     {"record_state": "NM"}, "state disagreement", "VETO 6 - cross-state"),
    ("United Tribes Technical College", _e("United Auburn"), {},
     "trap token", "VETO 8 - trap token 'united' carrying the match alone"),
    ("Blackfeet Housing Program", _e("Blackfeet Tribe"), {},
     "is an institution", "VETO 3 - a TDHE is a separate program entity"),
    ("SPOKANE, CITY OF", _e("Spokane Tribe"), {},
     "governmental/municipal", "VETO 4 - municipal body"),
    ("FL DEPT OF HEALTH", _e("Native Health"), {},
     "governmental/municipal", "VETO 4 - state department"),
    ("National Education Association", _e("National Indian Education Association"),
     {}, "folded token", "VETO 2 - 'indian' is the identity, not noise"),
    ("Institute of American Indian Arts Foundation",
     _e("Institute of American Indian Arts"), {},
     "distinguishing tokens", "VETO 5 - a foundation is a separate person"),
    ("2333 Biddle Ave, Wyandotte, MI", _e("Wyandotte Nation"), {},
     "postal address", "VETO 1 - the record is an address"),
    ("Native Village of Elim", _e("Elim Native Corporation",
                                  "Alaska Native Village Corporation"), {},
     "folded token",
     "VETO 2 - and it is worth saying that this case does NOT reach VETO 7: "
     "with no `anvc_counterpart_exists` in context the class is never read"),
    # THE CASE THAT WAS MISSING. VETO 7 is the ANCSA rule inside the matcher -
    # a corporate name resolving onto a village GOVERNMENT while that
    # village's ANCSA corporation exists. docs/ANCSA_OWNERSHIP_RULING.md
    # rule 2: a village government never owns an ANC, in either direction.
    # The record and the entity are chosen so that NO EARLIER VETO CAN FIRE:
    # the cores are equal, the only difference is `corporation`, which is
    # CORPORATE_NOTATION and therefore invisible to VETO 2; there is no
    # institution or municipal marker; and the states agree. If VETO 7 stops
    # working, this case goes green nowhere else and FAILS. The MUST_ALLOW
    # control below is the other half: the same pair WITHOUT
    # `anvc_counterpart_exists` must PASS, which proves the refusal comes from
    # VETO 7 and from nothing in the names.
    ("Chenega Corporation",
     _e("Chenega", "Federally recognized Alaska Native Village", "AK"),
     {"record_state": "AK", "anvc_counterpart_exists": True},
     "Alaska village",
     "VETO 7 - THE ANCSA VETO, previously exercised by no case at all. The "
     "two names are alike BY STATUTE (both are named for the same village, by "
     "43 U.S.C. 1607), so a shared name is not weak evidence of one owner - "
     "it is no evidence at all. docs/ANCSA_OWNERSHIP_RULING.md rule 2"),
]

MUST_ALLOW = [
    ("Zuni Gaming Enterprise", _e("Zuni", state="NM"),
     {"record_state": "AZ", "entity_operates_in": ["AZ"]},
     "a tribe seated in NM holding three ARIZONA compacts - seat is not the limit"),
    ("Cook Inlet Region, Incorporated", _e("Cook Inlet Region, Inc.",
                                           "Alaska Native Regional Corporation"),
     {}, "corporate form folding is CORRECT"),
    ("Chickasaw Nation Industries", _e("The Chickasaw Nation"),
     {"owner_named_in_evidence": True}, "owner named in evidence"),
    ("Cherokee Nation Businesses", _e("Cherokee Nation"),
     {"owner_named_in_evidence": True}, "tribes own companies directly"),
    ("Turning Stone Resort Casino", _e("Oneida", state="NY"),
     {"record_state": "NY", "owner_named_in_evidence": True},
     "named owner, agreeing state"),
    # THE CONTROL FOR VETO 7. Identical to the Chenega refuse-case except that
    # `anvc_counterpart_exists` is absent. It must PASS. Without this half, the
    # refuse-case could be going green on some unrelated veto and nobody would
    # know - which is precisely how `Native CDFI` survived in this file for
    # nineteen days.
    ("Chenega Corporation",
     _e("Chenega", "Federally recognized Alaska Native Village", "AK"),
     {"record_state": "AK"},
     "VETO 7 must fire on the ANCSA counterpart and on nothing else - with no "
     "counterpart recorded, a lower-48 tribe owning a company directly is the "
     "ordinary case (Chickasaw Nation Industries) and must not be refused"),
]


def assert_fixture_classes_are_real():
    """Every `entity_class` in a fixture must be a class the SPINE carries.

    This is the check that would have caught `Native CDFI` the day it was
    typed. A fixture asserting on a class name that does not exist proves
    nothing about the guard and reads exactly like a fixture that does.

    Returns a list of (case_name, bad_class, what_the_spine_says).
    """
    if not ENTITY_CLASSES:      # cedar_domain unavailable; say so, do not pass
        return [("<cedar_domain not importable>", "", "UNMEASURED, NOT CLEAN")]
    bad = []
    for rn, ent, _ctx, *_rest in list(MUST_REFUSE) + list(MUST_ALLOW):
        cls = (ent.get("entity_class") or "").strip()
        if cls and cls not in ENTITY_CLASSES:
            bad.append((rn, cls, canonical_entity_class(cls) or "<no near-miss>"))
    return bad


if __name__ == "__main__":
    print("=== cedar_match_guard self-test (DRAFT, not wired in) ===\n")
    bad = 0

    print("FIXTURE CLASSES ARE REAL SPINE CLASSES:")
    fixture_problems = assert_fixture_classes_are_real()
    for case, cls, real in fixture_problems:
        bad += 1
        print(f"  FAIL <- {case[:40]:42s} entity_class {cls!r} is not in the "
              f"spine; it says {real!r}")
    if not fixture_problems:
        print(f"  ok   all {len(MUST_REFUSE) + len(MUST_ALLOW)} fixture "
              f"entity_class values are declared spine classes")

    print("\nMUST REFUSE  (and for the RIGHT reason):")
    for rn, ent, ctx, expect, why in MUST_REFUSE:
        ok, reason = guard(rn, ent, context=ctx)
        right = (not ok) and expect.lower() in reason.lower()
        mark = "ok  " if right else "FAIL <-"
        if not right:
            bad += 1
        print(f"  {mark} {rn[:38]:40s} -> {ent['canonical_name'][:26]:28s} "
              f"{reason[:52]}")
        if not ok and not right:
            print(f"         refused, but NOT for {expect!r} - a case that "
                  f"passes on an unrelated veto proves nothing. {why}")

    print("\nMUST ALLOW:")
    for rn, ent, ctx, why in MUST_ALLOW:
        ok, reason = guard(rn, ent, context=ctx)
        mark = "ok  " if ok else "FAIL <-"
        if not ok:
            bad += 1
        print(f"  {mark} {rn[:38]:40s} -> {ent['canonical_name'][:26]:28s} "
              f"{reason[:52]}")

    print(f"\n{len(MUST_REFUSE)} refuse-cases, {len(MUST_ALLOW)} allow-cases, "
          f"{len(fixture_problems)} fixture-class problem(s), {bad} FAILURES")
    print("\nNOT WIRED IN. Adopting it means calling guard() after "
          "resolve_entity()\nin the callers, and re-running every build that "
          "keys a dollar.")
    # It counted failures and exited 0 until 2026-08-26, so nothing could ever
    # have failed on it. A self-test that cannot fail a runner is a printout.
    sys.exit(1 if bad else 0)
