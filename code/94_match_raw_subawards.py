#!/usr/bin/env python3
"""
Cedar Press - 94: Mine the raw FSRS corpus we already hold for Native links the
UEI join could never reach.

WHY THIS EXISTS
---------------
`data/clean/subawards.csv` holds 55,035 rows and thins to 173 / 89 / 120 / 166
in FY2021-2024 against 7,000-8,600 either side. That is not a collapse in Native
subcontracting, and this script was commissioned to close it from data already on
disk.

THE FIRST THING THIS SCRIPT DID WAS MEASURE THE CORPUS, AND THE PREMISE MOVED.

    data/raw/subcontracts/usaspending_subawards_2026-08-05/*.zip
    6,613,471 rows, read end to end 2026-08-07

    FY2001..FY2020   present    5,811,186 rows
    FY2021           0 rows
    FY2022           0 rows
    FY2023           0 rows
    FY2024           0 rows
    FY2025, FY2026   present      802,285 rows

`_state.json` holds 22 finished jobs and none of them is fy2021, fy2022, fy2023
or fy2024. Every row in every zip carries a `subaward_action_date_fiscal_year`
equal to its own job's fiscal year - zero bleed across 6.6M rows - so the missing
years cannot be hiding inside a neighbouring job. And the 548 rows the clean file
does carry for FY2021-2024 come 100% from the inherited HigherGov export and the
funding forward-fill, not from this corpus:

    FY2021  173 highergov
    FY2022   89 highergov
    FY2023   24 highergov + 96 funding_forward_fill
    FY2024  166 funding_forward_fill

**So the FY2021-2024 gap is a PULL gap, not a matching gap.** Those four fiscal
years were never retrieved. No amount of matching creates a row for a year whose
raw data is not on disk. That is recorded here rather than worked around, because
a script that quietly produced "no new FY2021 rows" would look like a matching
failure and send the next agent back down the same hole.

A SECOND HOLE, MEASURED THE SAME WAY: the fy2020 job returned its assistance
member and no contracts member at all - 456,412 assistance rows, 0 contract rows,
against 220,820 contract rows in FY2019 and 128,449 in FY2025. FY2020 contract
subawards are missing from the corpus too, which is most of why FY2020 shows
3,224 clean rows against FY2019's 8,637.

WHAT THIS SCRIPT DOES INSTEAD, AND WHY IT IS STILL WORTH RUNNING
---------------------------------------------------------------
The corpus we DO hold was matched on one route only: `subawardee_uei` /
`prime_awardee_uei` exact against the identifier ledger (script 41, promoted by
script 45). 6.6M rows in, 53,429 out. Two routes were never tried:

  * the DECLARED PARENT identifier. FSRS carries `subawardee_parent_uei` and
    `prime_awardee_parent_uei`. A subsidiary whose own UEI we have never seen
    often declares a parent UEI that is already in the ledger. This is still an
    identifier route - deterministic, no name inference - but it resolves at the
    FAMILY level, so it is tier B by construction. AGENTS.md is explicit: a
    federal parent field is EVIDENCE, never our statement of the hierarchy.

  * the NAME. The spine holds 1,310 entities; the ledger holds identifiers. A
    tribe that contracts under its own name and has no UEI row is invisible to
    an identifier join and completely legible to a human.

CONTAINMENT HAS FAILED SIX INDEPENDENT WAYS, so the name route is fenced
-----------------------------------------------------------------------
The one resolver is `33_apply_party_rulings.resolve_entity` and it is IMPORTED,
never re-implemented (regression rule 8). Everything below is a REFUSAL layer
applied to what it returns - it can only ever reject a match, never invent one.

  guard 1  trap corroboration. The tokens shared between record and entity must
           include at least one token outside `cedar_domain.NAME_TRAPS`. 26 trap
           terms, every one of which cost a real misattribution.
  guard 2  specificity. The record's name must be at least as specific as the
           entity's: entity_core must be a subset of record_core. Blocks the
           `NATIVE VILLAGE OF ELIM -> Elim Native Corporation` direction, where
           containment rewards the shortest spine name.
  guard 3  separate legal person. Where the record adds tokens the entity does
           not have, those tokens must not name a different chartered body -
           school, college, children, housing, authority, clinic, fund. This is
           the Chickasaw Children's Village bug ($2.8B), the Yakama ($917M) and
           Blackfeet ($568M) repeats, and all 148 TDHEs, encoded once.
  guard 4  state agreement. Where both the spine and the record carry a state
           and they disagree, refuse. This is Indian Pueblo Cultural Center (NM)
           -> Makaha Cultural Learning Center (HI), and Sequoyah High School (OK)
           -> Sequoyah Fund Inc. (NC).
  guard 5  country. A name match requires a US subawardee. "Indian" may mean
           India.
  guard 6  ANCSA namesake pair. 77 pairs exist and $27.59B was booked wrong on
           them. A record with no corporate form in its name never resolves to a
           village CORPORATION.

Guards 2 and 3 live HERE, in one dataset's staging pass, and not inside the
resolver. AGENTS.md records that an unrestricted specificity rule was measured
inside the resolver and removed because it cost 582 correct rows to save 190.
This is the fenced version, applied where every result it produces is tier B and
goes to a review queue anyway.

TIERS
-----
  identifier, ledger tier A   -> tier A carried through, as script 45 does
  identifier, ledger tier B   -> tier B
  declared parent identifier  -> tier B, family-level, `bears_ownership` checked
  name only                   -> tier B, ALWAYS, and always to review/

Nothing this script writes is promoted to tier A. Tier A needs a ruling.

THE TWO FILTER COLUMNS ARE COMPUTED ON EVERY ROW AND APPLIED TO NONE
--------------------------------------------------------------------
Spec 9.2: the subaward dataset is reliable about RELATIONSHIPS and unreliable
about AMOUNTS. 5,941 rows across the corpus report a subaward larger than its own
prime award; the worst is a $64,910.88 prime reporting a $794,526,041 subaward,
12,240x, for striping a car park. So `subaward_exceeds_prime_flag` and
`duplicate_status` are written on every appended row, no row is ever dropped for
either, and neither filter is applied here. Totalling requires
`duplicate_status == 'primary' AND subaward_exceeds_prime_flag != 'yes'`.

APPEND-ONLY
-----------
`data/clean/subawards.csv` is opened for READING to index what is already there,
then re-read to verify its header, then opened in APPEND mode. Existing bytes are
never rewritten. A row whose identity key is already present the same number of
times is skipped, not re-added; the count is by multiplicity, because the file
legitimately holds 12,446 `exact_repeat_within_source` rows and collapsing them
would be the MR-7 error again.

Reads  data/raw/subcontracts/usaspending_subawards_2026-08-05/*.zip
       data/clean/cedar_identifier_ledger_final.csv
       data/spine/cedar_entity_spine.csv
       data/clean/subawards.csv                     (index + header check)
Writes data/clean/subawards.csv                     (APPEND ONLY)
       review/subaward_matches_<date>.csv           (every tier B + every refusal)
       logs/94_match_raw_subawards.log

Usage
  py -3 code/94_match_raw_subawards.py --dry-run    # measure, write only review/
  py -3 code/94_match_raw_subawards.py              # measure and append
"""
from __future__ import annotations

import csv
import importlib.util
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from functools import lru_cache

csv.field_size_limit(1 << 27)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = os.path.join(ROOT, "code")
CLEAN = os.path.join(ROOT, "data", "clean")
SPINE = os.path.join(ROOT, "data", "spine")
REVIEW = os.path.join(ROOT, "review")
STAGE = os.path.join(ROOT, "data", "staging", "subawards_raw_match")
LOGFILE = os.path.join(ROOT, "logs", "94_match_raw_subawards.log")

OUT = os.path.join(CLEAN, "subawards.csv")
TODAY = date.today().isoformat()

# FSRS did not exist before FFATA. Rows dated earlier are misdated filings, and
# the current file documents 47 of them. They are flagged, never dropped, and
# never counted as coverage.
FFATA_FLOOR_FY = 2010


def log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')}] {msg}"
    print(line, flush=True)
    os.makedirs(os.path.dirname(LOGFILE), exist_ok=True)
    with open(LOGFILE, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, os.path.join(CODE, filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# THE ONE RESOLVER, and the schema, imported rather than restated.
m33 = _load("m33", "33_apply_party_rulings.py")          # resolve_entity, norm, core
m41 = _load("m41", "41_match_subawards_to_ledger.py")    # load_ledger, iter_subawards
m45 = _load("m45", "45_promote_subawards.py")            # COLS, blank_row, qc, keys

# `resolve_entity` re-normalises all 1,310 spine names on every call - roughly
# 5,000 unicode folds per name asked. Over a 6.6M-row corpus that is the whole
# runtime. `norm` and `core` are pure functions of a string, so wrapping them in
# a cache changes NOTHING about what the resolver answers; it only stops it
# recomputing the same 1,310 answers. Patched before any call so `core`, which
# looks `norm` up on the module, picks up the cached one.
m33.norm = lru_cache(maxsize=None)(m33.norm)
m33.core = lru_cache(maxsize=None)(m33.core)

sys.path.insert(0, CODE)
from cedar_domain import NAME_TRAPS, Tier, bears_ownership  # noqa: E402

# The edge a declared federal parent stands for. Asserted rather than assumed:
# if this ever stops bearing ownership the family route must stop carrying
# dollars, and the failure should be loud.
PARENT_EDGE = "subsidiary_of"
assert bears_ownership(PARENT_EDGE), "parent route must traverse an ownership edge"

# ---------------------------------------------------------------------------
# GUARD 3 - tokens that mean a DIFFERENT chartered body, not a variant name.
# Every term here is a measured failure, not a precaution:
#   children/childrens  Chickasaw Nation -> Chickasaw Children's Village, $2.8B
#   school/college      Sequoyah High School -> Sequoyah Fund Inc. (NC CDFI)
#   housing/authority   all 148 TDHEs resolved onto their own tribes
#   health/clinic       tribal health boards are members, not owners
# ---------------------------------------------------------------------------
SEPARATE_LEGAL_PERSON = frozenset({
    "school", "schools", "college", "colleges", "university", "academy",
    "children", "childrens", "child", "youth", "student", "students",
    "hospital", "clinic", "clinics", "health", "healthcare", "medical",
    "housing", "authority", "authorities", "program", "programs", "project",
    "fund", "funds", "foundation", "center", "centers", "centre", "museum",
    "institute", "institution", "library", "headstart", "daycare",
    "district", "chapter", "department", "agency", "commission", "board",
    "association", "society", "church", "ministry", "conference", "consortium",
    "coalition", "alliance", "network", "institutefor",
})

CORP_FORM_RE = m33.CORP_FORM_RE

# GUARD 8 - USAspending files general-purpose local governments in an inverted
# form: `SPOKANE, CITY OF`, `WASHOE, COUNTY OF`, `MASHPEE TOWN OF`. A county or
# a municipality is never a tribe, however much of the name they share, and the
# shared part is usually the tribe's own homeland. `village of` is deliberately
# NOT here: "Village of Sleetmute" is a documented full-form federal variant of
# a real Alaska Native village government (spec 5.3).
GOV_UNIT_RE = re.compile(
    r"\b(county|city|town|township|borough|parish|state|commonwealth|"
    r"municipality)\s+of$")
GOV_UNIT_PREFIXES = tuple(
    f"{w} of " for w in ("county", "city", "town", "township", "borough",
                         "parish", "state", "commonwealth", "municipality"))

DIR_A, DIR_B, DIR_BOTH = m45.DIR_A, m45.DIR_B, m45.DIR_BOTH

ROUTE_UEI = "usaspending_fsrs_pull"                    # existing enum value
ROUTE_PARENT = "usaspending_fsrs_parent_cluster"       # new, internal column
ROUTE_NAME = "usaspending_fsrs_name_match"             # new, internal column
POPULATION = "full_federal_subaward_universe"


# ---------------------------------------------------------------------------
# spine index. A PRE-FILTER ONLY. It decides which names are worth asking the
# resolver about; it never decides a match. Without it the resolver would be
# called 13.2M times over 1,310 entities.
# ---------------------------------------------------------------------------

def build_spine_index(spine):
    """token -> spine rows, exact-normalised name -> present, and each entity's
    core. Used ONLY to decide which names are worth asking the resolver about."""
    idx = defaultdict(set)
    by_id, cores = {}, {}
    core_list = []
    exact = set()
    anvc_cores = set()
    for i, r in enumerate(spine):
        by_id[r["tribe_id"]] = r
        c = m33.core(r["canonical_name"])
        cores[r["tribe_id"]] = c
        core_list.append(c)
        if r["tribe_id"].startswith("ANVC-"):
            anvc_cores.add(frozenset(c))
        names = [r["canonical_name"]] + [
            a for a in (r.get("aliases") or "").split("|") if a.strip()]
        for nm in names:
            exact.add(m33.norm(nm))
            for t in m33.core(nm):
                idx[t].add(i)
    return idx, by_id, cores, anvc_cores, core_list, exact


STATE_RE = re.compile(r"^[A-Z]{2}$")


def name_route(raw_name, rec_state, rec_country, spine, idx, by_id, cores,
               anvc_cores, core_list, exact):
    """Ask the ONE resolver, then refuse on six guards.

    Returns (tribe_id, canonical_name, how) on success, or (None, None, reason).
    This function can only ever narrow the resolver's answer.
    """
    if not raw_name or len(raw_name.strip()) < 4:
        return None, None, "name_too_short"
    if rec_country and rec_country.strip().upper() not in ("USA", "UNITED STATES", ""):
        return None, None, f"guard5_non_us_country:{rec_country.strip().upper()}"

    n = m33.norm(raw_name)
    # guard 8 - a general-purpose local government is not a tribal government
    if GOV_UNIT_RE.search(n) or n.startswith(GOV_UNIT_PREFIXES):
        return None, None, "guard8_municipal_or_county_government"

    c = m33.core(raw_name)
    if not c:
        return None, None, "no_core_tokens"

    # PRE-FILTER, not a decision. Some spine entity must share a non-trap token
    # AND either normalise identically to this name or have a core the name
    # already contains. Those are exactly the four states the resolver can
    # return (exact / alias / core / containment-passing-guard-2), so a name
    # failing this could not have survived the guards anyway - and skipping it
    # keeps the resolver from being asked 13.2M questions.
    reach = set()
    for t in (c - NAME_TRAPS):
        reach |= idx.get(t, set())
    if not reach:
        return None, None, "no_spine_token"
    if n not in exact and not any(core_list[i] <= c for i in reach):
        return None, None, "prefilter_no_entity_contained"

    tid, canon, how = m33.resolve_entity(raw_name, spine)
    if not tid:
        return None, None, f"resolver:{how}"

    ent = by_id[tid]
    ec = cores.get(tid) or m33.core(ent["canonical_name"])

    # guard 1 - trap corroboration
    shared = ec & c
    if not (shared - NAME_TRAPS):
        return None, None, ("guard1_trap_token_only:"
                            + "|".join(sorted(shared)))

    # Guards 2 and 3 police CONTAINMENT, which is the tier that failed six ways.
    # An exact or verified-alias hit is name EQUALITY, not containment: the
    # record is already exactly as specific as the entity, and an alias's extra
    # words are the entity's own registered ones. Applying a specificity or
    # separate-body test to those would refuse correct matches for the sake of
    # a guard aimed at a different failure.
    if how == "containment":
        # guard 2 - the record must be at least as specific as the entity
        if not ec <= c:
            return None, None, ("guard2_record_less_specific:missing="
                                + "|".join(sorted(ec - c)))
        # guard 3 - extra tokens must not name a separate chartered body
        bad = (c - ec) & SEPARATE_LEGAL_PERSON
        if bad:
            return None, None, ("guard3_separate_legal_person:"
                                + "|".join(sorted(bad)))

    # guard 7 - specificity floor for anything short of name equality. A core
    # hit is containment modulo corporate forms (`MICCOSUKEE CORPORATION` ->
    # Miccosukee rests on one token); a containment hit is worse. An entity
    # whose whole distinguishing core is ONE non-trap word cannot be told apart
    # from a company that happens to share it - Hamilton, Elem, Enterprise,
    # Craig, Spokane and "Native Health" all reached this route on real rows.
    if how in ("core", "containment") and len(ec - NAME_TRAPS) < 2:
        return None, None, ("guard7_single_token_core:" + "|".join(sorted(ec)))

    # guard 4 - state agreement where both sides carry one
    est = (ent.get("state") or "").strip().upper()
    rst = (rec_state or "").strip().upper()
    if STATE_RE.match(est) and STATE_RE.match(rst) and est != rst:
        return None, None, f"guard4_state_mismatch:{est}!={rst}"

    # guard 6 - ANCSA namesake pair, the direction the resolver does not cover.
    # The resolver refuses a CORPORATE name landing on a village GOVERNMENT.
    # The mirror image is a government-shaped name landing on the CORPORATION,
    # which is how Native Village of Elim reached Elim Native Corporation.
    if tid.startswith("ANVC-") and not CORP_FORM_RE.search(raw_name):
        return None, None, "guard6_village_corp_needs_corporate_form"
    if (ent.get("entity_class") == "Federally recognized Alaska Native Village"
            and CORP_FORM_RE.search(raw_name)
            and frozenset(ec) in anvc_cores):
        return None, None, "guard6_namesake_village_corporation_exists"

    # AND FOR CONTAINMENT, SEVEN GUARDS ARE STILL NOT ENOUGH. Measured 2026-08-07
    # on the first 600,000 raw rows: with every guard above satisfied, the
    # containment tier still produced `SPOKANE, CITY OF` -> Spokane Tribe (19
    # subawards), `ONONDAGA, COUNTY OF` -> Onondaga Nation, `HABITAT FOR HUMANITY
    # OF OMAHA` -> Omaha Tribe (64), `LAS VEGAS, CITY OF` -> Las Vegas Paiute,
    # `COMMUNITY BASED CARE OF SEMINOLE` -> Seminole Tribe (59). Same state, more
    # specific record, no institution marker in the extra tokens - every guard
    # passed, every answer wrong, because the spine stores SHORT names and a
    # short tribal name is usually also the name of the place.
    #
    # So containment does not link here. It is returned as a CANDIDATE; the
    # caller banks it for review and attributes nothing. Spec 3: "Containment is
    # not a match." This is the seventh face of that one bug, and the first one
    # caught before it booked a dollar.
    return tid, canon, how


# ---------------------------------------------------------------------------
# row construction - the published schema comes from script 45, unmodified
# ---------------------------------------------------------------------------

def build_row(r, kind, chunk, attribution, source_dataset):
    """attribution = (p_tid, p_tier, s_tid, s_tier). At least one side is set."""
    p_tid, p_tier, s_tid, s_tier = attribution
    pl, sl = bool(p_tid), bool(s_tid)
    direction = DIR_BOTH if (pl and sl) else (DIR_B if sl else DIR_A)

    fy = (r.get("subaward_action_date_fiscal_year") or "").strip()
    amt = m45.fnum(r.get("subaward_amount"))
    pamt = m45.fnum(r.get("prime_award_amount"))
    ratio, exceeds = m45.qc(amt, pamt)

    row = m45.blank_row()
    row.update({
        "sub_uei": (r.get("subawardee_uei") or "").strip().upper(),
        "sub_name": r.get("subawardee_name", ""),
        "sub_state": r.get("subawardee_state_code", ""),
        "prime_uei": (r.get("prime_awardee_uei") or "").strip().upper(),
        "prime_name": r.get("prime_awardee_name", ""),
        "prime_award_id": (r.get("prime_award_piid") or r.get("prime_award_fain") or ""),
        "subaward_amount": r.get("subaward_amount", ""),
        "subaward_date": r.get("subaward_action_date", ""),
        "fiscal_year": fy,
        "naics": r.get("prime_award_naics_code", ""),
        "naics_title": r.get("prime_award_naics_description", ""),
        "description": (r.get("subaward_description", "") or "")[:400],
        "direction": direction,
        "source_file": chunk,
        "fetched_date": m45.FETCHED,
        "subaward_number": r.get("subaward_number", ""),
        "source_url": r.get("usaspending_permalink", ""),
        "sub_parent_uei": r.get("subawardee_parent_uei", ""),
        "sub_parent_name": r.get("subawardee_parent_name", ""),
        "prime_parent_uei": r.get("prime_awardee_parent_uei", ""),
        "prime_parent_name": r.get("prime_awardee_parent_name", ""),
        "prime_top_awarding_agency": r.get("prime_award_awarding_agency_name", ""),
        "pre_2000_flag": "1" if (fy.isdigit() and int(fy) < 2000) else "",
        "floor_basis_field": "subaward_date",
        "source_dataset": source_dataset,
        "source_population": POPULATION,
        "award_kind": kind,
        "subaward_type": r.get("subaward_type", ""),
        "prime_award_unique_key": r.get("prime_award_unique_key", ""),
        "prime_award_amount": r.get("prime_award_amount", ""),
        "subaward_to_prime_ratio": ratio,
        "subaward_exceeds_prime_flag": exceeds,
        "action_date_precedes_ffata_flag": "yes" if (
            fy.isdigit() and int(fy) < FFATA_FLOOR_FY) else "",
        "subaward_sam_report_year": r.get("subaward_sam_report_year", ""),
        "prime_native_tribe_id": p_tid or "",
        "prime_native_tier": p_tier or "",
        "sub_native_tribe_id": s_tid or "",
        "sub_native_tier": s_tier or "",
        "sub_business_types": r.get("subawardee_business_types", ""),
        "prime_awarding_sub_agency": r.get("prime_award_awarding_sub_agency_name", ""),
        "promoted_date": TODAY,
    })
    return row


def is_link(m):
    return (m is not None and m.get("confidence_tier") in ("A", "B")
            and bool((m.get("tribe_id") or "").strip()))


def parent_ok(raw_name, tid, by_id, cores):
    """The declared-parent route is deterministic on an identifier, but the
    identifier it is deterministic on is SELF-DECLARED by the filer and FPDS
    does not update it retroactively. Two refusals, both measured on real rows:

      `WASHOE, COUNTY OF` declared a parent UEI that the ledger maps to the
      Washoe Tribe. A county is not a tribe whatever SAM says.

      `CHIEF DULL KNIFE COLLEGE, INC` declared a parent that maps to the
      Northern Cheyenne Tribe. The college is its own spine entity and a TCU;
      rolling it into the tribe is the college-onto-tribe failure with a
      federal field standing in for the bad name match.
    """
    n = m33.norm(raw_name)
    if GOV_UNIT_RE.search(n) or n.startswith(GOV_UNIT_PREFIXES):
        return False, "guard8_municipal_or_county_government"
    ent = by_id.get(tid, {})
    ec = cores.get(tid, frozenset())
    bad = (m33.core(raw_name) - ec) & SEPARATE_LEGAL_PERSON
    if bad and ent.get("entity_class") not in (
            "BIE School", "Tribal College or University",
            "Urban Indian Organization",
            "Native Community Development Financial Institution"):
        return False, "guard3_separate_legal_person:" + "|".join(sorted(bad))
    return True, ""


def read_existing_index():
    """Multiset of identity keys already in the file, plus the header as written."""
    keys = Counter()
    header = None
    n = 0
    if not os.path.exists(OUT):
        return keys, header, n
    with open(OUT, encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        header = rd.fieldnames
        for r in rd:
            n += 1
            keys[m45.identity_key(r)] += 1
    return keys, header, n


def main() -> int:
    dry = "--dry-run" in sys.argv
    os.makedirs(REVIEW, exist_ok=True)

    log("=== 94: mine the raw FSRS corpus already on disk ===")

    spine = m33.read_csv(os.path.join(SPINE, "cedar_entity_spine.csv"))
    idx, by_id, cores, anvc_cores, core_list, exact = build_spine_index(spine)
    log(f"spine: {len(spine):,} entities, {len(idx):,} distinct index tokens")

    by_uei, _tiers, _names = m41.load_ledger()

    existing_keys, header, n_existing = read_existing_index()
    log(f"existing subawards.csv: {n_existing:,} rows, "
        f"{len(existing_keys):,} distinct identity keys")
    if header is not None and header != m45.COLS:
        raise SystemExit("subawards.csv header does not match the promoted schema; "
                         "refusing to append")

    # ---------------------------------------------------------------- pass
    # New rows STREAM to a staging file rather than accumulating in a list. The
    # first attempt at this run held them in memory and was killed on a box
    # already running eleven other agent processes; 6.6M input rows is not the
    # place to find out how much RAM a list of 49-key dicts wants.
    os.makedirs(STAGE, exist_ok=True)
    stage_path = os.path.join(STAGE, f"subawards_raw_match_{TODAY}.csv")
    fstage = open(stage_path, "w", newline="", encoding="utf-8")
    wstage = csv.DictWriter(fstage, fieldnames=m45.COLS, extrasaction="ignore")
    wstage.writeheader()
    n_new = 0
    usd_new = 0.0
    fy_new, dup_new, dir_new = Counter(), Counter(), Counter()
    n_pre_ffata = n_exceeds = 0
    ents_new = set()
    memo = {}                      # raw name -> (tid, canon, how) | (None,None,reason)
    seen_new = Counter()
    n_read = 0
    fy_raw = Counter()
    route_rows = Counter()
    route_entities = defaultdict(set)
    refusals = Counter()
    # review aggregation: (route, side, record_name, tribe_id) -> stats
    q = defaultdict(lambda: {"n": 0, "usd": 0.0, "fy": set(), "ueis": set(),
                             "states": set(), "prime": "", "how": "",
                             "canon": "", "cls": "", "ent_state": "",
                             "parent_uei": ""})
    refused_q = defaultdict(lambda: {"n": 0, "usd": 0.0, "reason": "",
                                     "fy": set(), "ueis": set(), "states": set()})
    # containment candidates: banked for a human, never attributed
    cand_q = defaultdict(lambda: {"n": 0, "usd": 0.0, "fy": set(), "ueis": set(),
                                  "states": set()})

    def bank_candidate(side, nm, tid, st, uei, fy, amt):
        d = cand_q[(side, (nm or "").strip().upper(), tid)]
        d["n"] += 1
        d["usd"] += amt
        d["fy"].add(fy)
        if st:
            d["states"].add(st)
        if uei:
            d["ueis"].add(uei)

    def resolve_name(nm, st, cc):
        # keyed on name AND state AND country, because guards 4 and 5 read them:
        # the same name in two states is not the same question.
        k = ((nm or "").strip().upper(), (st or "").strip().upper(),
             (cc or "").strip().upper())
        hit = memo.get(k)
        if hit is None:
            if len(memo) > 800_000:
                memo.clear()       # a cache, not state: cheaper to recompute

            hit = name_route(nm, st, cc, spine, idx, by_id, cores, anvc_cores,
                             core_list, exact)
            memo[k] = hit
        return hit

    limit = 0
    for a in sys.argv:
        if a.startswith("--limit="):
            limit = int(a.split("=", 1)[1])

    for chunk, kind, r in m41.iter_subawards():
        n_read += 1
        if limit and n_read > limit:
            log(f"--limit={limit:,} reached; this is a SMOKE TEST, not a build")
            break
        fy = (r.get("subaward_action_date_fiscal_year") or "").strip()
        fy_raw[fy] += 1
        if n_read % 250_000 == 0:
            log(f"  ...{n_read:,} raw rows read, {n_new:,} new rows staged, "
                f"{len(memo):,} distinct names resolved")

        puei = (r.get("prime_awardee_uei") or "").strip().upper()
        suei = (r.get("subawardee_uei") or "").strip().upper()
        pm, sm = by_uei.get(puei), by_uei.get(suei)
        pl, sl = is_link(pm), is_link(sm)

        p_tid = pm.get("tribe_id") if pl else ""
        p_tier = pm.get("confidence_tier") if pl else ""
        s_tid = sm.get("tribe_id") if sl else ""
        s_tier = sm.get("confidence_tier") if sl else ""
        route = ROUTE_UEI if (pl or sl) else ""

        # ---- route 2: DECLARED PARENT identifier, family level, tier B ----
        if not pl:
            ppar = (r.get("prime_awardee_parent_uei") or "").strip().upper()
            pmm = by_uei.get(ppar)
            if ppar and ppar != puei and is_link(pmm):
                ok, why = parent_ok(r.get("prime_awardee_name", ""),
                                    pmm.get("tribe_id"), by_id, cores)
                if ok:
                    p_tid, p_tier = pmm.get("tribe_id"), Tier.B.value
                    route = route or ROUTE_PARENT
                else:
                    refusals[f"prime_parent|{why.split(':')[0]}"] += 1
        if not sl:
            spar = (r.get("subawardee_parent_uei") or "").strip().upper()
            smm = by_uei.get(spar)
            if spar and spar != suei and is_link(smm):
                ok, why = parent_ok(r.get("subawardee_name", ""),
                                    smm.get("tribe_id"), by_id, cores)
                if ok:
                    s_tid, s_tier = smm.get("tribe_id"), Tier.B.value
                    route = route or ROUTE_PARENT
                else:
                    refusals[f"sub_parent|{why.split(':')[0]}"] += 1

        # ---- route 3: NAME, tier B always, guarded seven ways --------------
        # A containment answer NEVER attributes. It is banked as a candidate for
        # a human and the row carries on as if the name had resolved to nothing.
        p_name_how = s_name_how = ""
        if not p_tid:
            tid, canon, how = resolve_name(
                r.get("prime_awardee_name", ""),
                r.get("prime_awardee_state_code", ""),
                r.get("prime_awardee_country_code", ""))
            if tid and how == "containment":
                bank_candidate("prime", r.get("prime_awardee_name", ""), tid,
                               r.get("prime_awardee_state_code", ""), "", fy,
                               m45.fnum(r.get("subaward_amount")))
                tid = None
            if tid:
                p_tid, p_tier, p_name_how = tid, Tier.B.value, how
                route = route or ROUTE_NAME
            elif how and not how.startswith(("no_spine_token", "no_core",
                                             "name_too_short", "prefilter_",
                                             "resolver:no_spine_match")):
                refusals[f"prime|{how.split(':')[0]}"] += 1
        if not s_tid:
            tid, canon, how = resolve_name(
                r.get("subawardee_name", ""),
                r.get("subawardee_state_code", ""),
                r.get("subawardee_country_code", ""))
            if tid and how == "containment":
                bank_candidate("sub", r.get("subawardee_name", ""), tid,
                               r.get("subawardee_state_code", ""), suei, fy,
                               m45.fnum(r.get("subaward_amount")))
                tid = None
            if tid:
                s_tid, s_tier, s_name_how = tid, Tier.B.value, how
                route = route or ROUTE_NAME
            elif how and not how.startswith(("no_spine_token", "no_core",
                                             "name_too_short", "prefilter_",
                                             "resolver:no_spine_match")):
                refusals[f"sub|{how.split(':')[0]}"] += 1
                # bounded: the refusal list is an audit trail, not a second corpus
                rq_key = (r.get("subawardee_name", "") or "").strip().upper()
                if rq_key in refused_q or len(refused_q) < 60_000:
                    d = refused_q[rq_key]
                    d["n"] += 1
                    d["usd"] += m45.fnum(r.get("subaward_amount"))
                    d["reason"] = d["reason"] or how
                    d["fy"].add(fy)
                    if suei:
                        d["ueis"].add(suei)
                    if r.get("subawardee_state_code"):
                        d["states"].add(r["subawardee_state_code"])

        if not (p_tid or s_tid):
            continue

        # THE WEAKEST ROUTE USED LABELS THE ROW. A row whose prime came from the
        # ledger and whose subawardee came from a name is a name-quality row;
        # labelling it by its strongest leg would launder the weak one.
        if p_name_how or s_name_how:
            route = ROUTE_NAME
        elif route == ROUTE_UEI and (
                (p_tid and p_tier == Tier.B.value and not pl)
                or (s_tid and s_tier == Tier.B.value and not sl)):
            route = ROUTE_PARENT
        row = build_row(r, kind, chunk, (p_tid, p_tier, s_tid, s_tier), route)

        ik = m45.identity_key(row)
        seen_new[ik] += 1
        if seen_new[ik] <= existing_keys.get(ik, 0):
            continue                      # already in the file, at this multiplicity
        row["duplicate_status"] = ("primary" if seen_new[ik] -
                                   existing_keys.get(ik, 0) == 1
                                   else "exact_repeat_within_source")
        wstage.writerow(row)
        n_new += 1
        route_rows[route] += 1
        fy_new[row["fiscal_year"]] += 1
        dup_new[row["duplicate_status"]] += 1
        dir_new[row["direction"]] += 1
        if row["action_date_precedes_ffata_flag"] == "yes":
            n_pre_ffata += 1
        if row["subaward_exceeds_prime_flag"] == "yes":
            n_exceeds += 1
        elif row["duplicate_status"] == "primary":
            usd_new += m45.fnum(row["subaward_amount"])
        for tid in (p_tid, s_tid):
            if tid:
                route_entities[route].add(tid)
                ents_new.add(tid)

        # ---- review queue ------------------------------------------------
        amt = m45.fnum(row["subaward_amount"])
        if route in (ROUTE_NAME, ROUTE_PARENT):
            for side, tid, nm, how, uei, st, par in (
                    ("prime", p_tid, row["prime_name"], p_name_how,
                     row["prime_uei"], "", row["prime_parent_uei"]),
                    ("sub", s_tid, row["sub_name"], s_name_how,
                     row["sub_uei"], row["sub_state"], row["sub_parent_uei"])):
                if not tid:
                    continue
                if route == ROUTE_NAME and not how:
                    continue          # this side came from the ledger, not a name
                ent = by_id.get(tid, {})
                d = q[(route, side, (nm or "").strip().upper(), tid)]
                d["n"] += 1
                d["usd"] += amt
                d["fy"].add(row["fiscal_year"])
                if uei:
                    d["ueis"].add(uei)
                if st:
                    d["states"].add(st)
                d["prime"] = d["prime"] or row["prime_award_id"]
                d["how"] = d["how"] or (how or "declared_parent_uei")
                d["canon"] = ent.get("canonical_name", "")
                d["cls"] = ent.get("entity_class", "")
                d["ent_state"] = ent.get("state", "")
                d["parent_uei"] = d["parent_uei"] or par

    fstage.close()
    log(f"READ {n_read:,} raw rows")
    log("raw rows by fiscal year: " + json.dumps(dict(sorted(fy_raw.items()))))
    log(f"NEW rows staged -> {stage_path}: {n_new:,}")
    log("  by route: " + json.dumps(dict(route_rows)))
    log("  distinct entities by route: "
        + json.dumps({k: len(v) for k, v in route_entities.items()}))
    log("guard refusals (a refusal is the guard working): "
        + json.dumps(dict(refusals.most_common(25))))

    # -------------------------------------------------------------- review
    rpath = os.path.join(REVIEW, f"subaward_matches_{TODAY}.csv")
    with open(rpath, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["status", "route", "side", "record_name", "record_states",
                    "record_ueis", "record_parent_uei", "tribe_id",
                    "canonical_name", "entity_class", "entity_state",
                    "resolver_how", "confidence_tier", "n_subawards",
                    "total_usd_UNFILTERED", "fiscal_years",
                    "example_prime_award_id", "match_basis", "YOUR_RULING"])
        for (route, side, nm, tid), d in sorted(
                q.items(), key=lambda kv: -kv[1]["usd"]):
            w.writerow([
                "STAGED_TIER_B", route, side, nm,
                "|".join(sorted(d["states"]))[:60],
                "|".join(sorted(d["ueis"]))[:200], d["parent_uei"], tid,
                d["canon"], d["cls"], d["ent_state"], d["how"], Tier.B.value,
                d["n"], round(d["usd"], 2),
                "|".join(sorted(x for x in d["fy"] if x)), d["prime"],
                "name resolved through 33_apply_party_rulings.resolve_entity and "
                "passed six refusal guards; NO identifier evidence"
                if route == ROUTE_NAME else
                "subawardee/prime declared a parent UEI that is in the identifier "
                "ledger; family-level, not a legal-entity match",
                ""])
        for (side, nm, tid), d in sorted(cand_q.items(),
                                         key=lambda kv: -kv[1]["usd"]):
            ent = by_id.get(tid, {})
            w.writerow([
                "CANDIDATE_NOT_APPENDED", ROUTE_NAME, side, nm,
                "|".join(sorted(d["states"]))[:60],
                "|".join(sorted(d["ueis"]))[:200], "", tid,
                ent.get("canonical_name", ""), ent.get("entity_class", ""),
                ent.get("state", ""), "containment", "", d["n"],
                round(d["usd"], 2),
                "|".join(sorted(x for x in d["fy"] if x)), "",
                "containment survived guards 1-6 and STILL attributes nothing. "
                "Spec 3: containment is not a match. A human decides.", ""])
        for nm, d in sorted(refused_q.items(), key=lambda kv: -kv[1]["usd"])[:4000]:
            w.writerow(["REFUSED_BY_GUARD", ROUTE_NAME, "sub", nm,
                        "|".join(sorted(d["states"]))[:60],
                        "|".join(sorted(d["ueis"]))[:200], "", "", "", "", "",
                        d["reason"], "", d["n"], round(d["usd"], 2),
                        "|".join(sorted(x for x in d["fy"] if x)), "",
                        "the resolver produced a candidate and a guard refused it; "
                        "listed so the refusal is auditable, not silent", ""])
    log(f"WROTE {rpath} - {len(q):,} staged tier-B decisions, "
        f"{len(cand_q):,} containment candidates attributed to nobody, "
        f"{min(len(refused_q), 4000):,} guard refusals")

    # ------------------------------------------------------------- summary
    summary = {
        "run_date": TODAY,
        "raw_rows_read": n_read,
        "raw_rows_by_fiscal_year": dict(sorted(fy_raw.items())),
        "FY2021_2024_raw_rows_on_disk": {y: fy_raw.get(y, 0)
                                         for y in ("2021", "2022", "2023", "2024")},
        "existing_rows": n_existing,
        "new_rows": n_new,
        "new_rows_by_route": dict(route_rows),
        "new_rows_by_fiscal_year": dict(sorted(fy_new.items())),
        "new_rows_pre_ffata_flagged": n_pre_ffata,
        "new_rows_flagged_subaward_exceeds_prime": n_exceeds,
        "new_rows_duplicate_status": dict(dup_new),
        "new_rows_by_direction": dict(dir_new),
        "distinct_entities_touched_by_new_rows": len(ents_new),
        "distinct_entities_by_route": {k: len(v) for k, v in route_entities.items()},
        "usd_new_after_both_filters": round(usd_new, 2),
        "containment_candidates_banked_not_attributed": len(cand_q),
        "guard_refusals": dict(refusals),
        "staging_file": stage_path,
    }
    log("SUMMARY " + json.dumps(summary, indent=1))
    with open(os.path.join(REVIEW, f"_94_summary_{TODAY}.json"), "w",
              encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1)

    if dry:
        log("--dry-run: nothing appended to data/clean/subawards.csv")
        return 0
    if not n_new:
        log("no new rows; data/clean/subawards.csv untouched")
        return 0

    # ------------------------------------------------------------- append
    # Re-read the header IMMEDIATELY before writing so a concurrent agent that
    # changed the schema cannot be clobbered.
    with open(OUT, encoding="utf-8-sig", newline="") as fh:
        head_now = next(csv.reader(fh))
    if head_now != m45.COLS:
        raise SystemExit("subawards.csv header changed under us; refusing to append")

    n_appended = 0
    with open(stage_path, encoding="utf-8-sig", newline="") as src, \
            open(OUT, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=m45.COLS, extrasaction="ignore")
        for r in csv.DictReader(src):
            w.writerow({c: r.get(c, "") for c in m45.COLS})
            n_appended += 1
    log(f"APPENDED {n_appended:,} rows to {OUT} "
        f"({n_existing:,} -> {n_existing + n_appended:,})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
