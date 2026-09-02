#!/usr/bin/env python3
r"""
523_spiderweb_harvest.py
========================
Workstream J, pass 3 (2026-09-01). Owns: this file, the review tables it
writes, and docs/SPIDERWEB_LEARNING_PLAN.md. Touches nothing else.

WHAT THIS IS
------------
`data/clean/fpds_uei_edges.csv` holds 5,167 (child, parent) pairs that
registrants DECLARED on FPDS / USAspending transactions under FAR 4.18 /
52.204-17. Cedar reads them today only to look a parent up. This script reads
them the other way round: where ONE end of a declared edge is already keyed to
a Cedar entity, the OTHER end is a named firm that a filer put inside that
entity's corporate family, and we are throwing that identification away.

Phase 1 (`harvest`) turns those edges into CANDIDATES.
Phase 2 (`mine`)    turns the 115,471-node / 46,051-edge identifier graph into
                    four ranked work queues.
`verify`            re-reads the outputs and asserts the invariants below.
`fixtures`          proves each invariant actually fires.
`validate`          draws a deterministic random sample for hand checking.

THE FIVE INVARIANTS (checked by `verify`, proven by `fixtures`)
---------------------------------------------------------------
I1  TIER B, NEVER A. A declaration proves a CONNECTION, not Native ownership.
    docs/NATIVE_ENTITY_NUANCES.md: the declared highest owner is routinely the
    highest *incorporated* owner - Ho-Chunk, Inc., not the Winnebago Tribe of
    Nebraska - and that last hop is Cedar's, never SAM's. Any candidate
    emitted at tier A is a false claim of proof.

I2  NO TRANSITIVE CLOSURE. Every emitted candidate's (child_uei, parent_uei)
    pair must appear LITERALLY in fpds_uei_edges.csv. If A->B and B->C are
    declared we do NOT assert A->C; chains break at holdcos and inventing the
    closure is how a spiderweb becomes a fabrication.

I3  BLOCKLISTED ROLL-UP PARENTS NEVER PROPAGATE. Registrants recorded as
    GOVERNMENT OF THE UNITED STATES carry BIA, IHS and tribally-controlled
    grant schools as "children". Inheriting through them attributes federal
    agencies to tribes. The set is DERIVED from the recorded parent name on
    every run, not enumerated: the source column flags only one of them, and
    the 2026-09-01 source expansion added two more that no list contained.

I4  PRIME-TO-SUB IS NOT OWNERSHIP. `13_build_fpds_hierarchy.py` says so in
    capitals in its own docstring. A subaward is a contracting relationship.

I5  EVERY SOURCE EDGE IS ACCOUNTED FOR. accepted + declined == the source
    row count, and every decline sits in a NAMED bucket with a count. No
    unnamed drops.

WHAT THIS SCRIPT DOES NOT DO
-----------------------------
* It does not mint a spine entity. Candidates only. The promotion path exists
  (`241_promote_individual_native_firms_in_place.py`) and is deliberately not
  invoked: a candidate is a question, a ruling is evidence.
* It does not write to data/clean/. The outputs are REVIEW material and live
  in review/, which is where Cedar already keeps queues, and which the
  shipping ratchets in 62 correctly do not scan.
* It does not edit the spine, the identifier ledger, 503, 510, 512, 62 or
  build.py.

USAGE
-----
  py -3 code/523_spiderweb_harvest.py all
  py -3 code/523_spiderweb_harvest.py harvest
  py -3 code/523_spiderweb_harvest.py mine
  py -3 code/523_spiderweb_harvest.py verify
  py -3 code/523_spiderweb_harvest.py fixtures
  py -3 code/523_spiderweb_harvest.py validate --sample 20 --seed 20260901
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import shutil
import sys
import math
import unicodedata
from collections import Counter, defaultdict

csv.field_size_limit(min(sys.maxsize, 2_147_483_647))

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN = os.path.join(PROJECT, "data", "clean")
SPINE = os.path.join(PROJECT, "data", "spine")
REVIEW = os.path.join(PROJECT, "review")

EDGES_IN = os.path.join(CLEAN, "fpds_uei_edges.csv")
CAGEMAP_IN = os.path.join(CLEAN, "fpds_uei_cage_map.csv")
LEDGER_IN = os.path.join(CLEAN, "cedar_identifier_ledger_final.csv")
GNODES_IN = os.path.join(CLEAN, "cedar_identifier_graph_nodes.csv")
GEDGES_IN = os.path.join(CLEAN, "cedar_identifier_graph_edges.csv")
SPINE_IN = os.path.join(SPINE, "cedar_entity_spine.csv")
AWARDS_IN = os.path.join(CLEAN, "prime_contracts_awards.csv")
SUBS_IN = os.path.join(CLEAN, "subawards.csv")

CAND_OUT = os.path.join(REVIEW, "523_spiderweb_ownership_candidates.csv")
FIRMS_OUT = os.path.join(REVIEW, "523_spiderweb_candidate_firms.csv")
DECL_OUT = os.path.join(REVIEW, "523_spiderweb_declines.csv")
BACKFILL_OUT = os.path.join(REVIEW, "523_identifier_backfill_candidates.csv")
Q1_OUT = os.path.join(REVIEW, "523_idgraph_q1_cooccurrence.csv")
Q2_OUT = os.path.join(REVIEW, "523_idgraph_q2_name_clusters.csv")
Q3_OUT = os.path.join(REVIEW, "523_idgraph_q3_unkeyed_by_dataset_count.csv")
Q4_OUT = os.path.join(REVIEW, "523_idgraph_q4_split_entity_suspects.csv")
SAMPLE_OUT = os.path.join(REVIEW, "523_validation_sample.csv")
ANCHOR_OUT = os.path.join(REVIEW, "523_suspect_keyed_anchors.csv")
SUMMARY_OUT = os.path.join(REVIEW, "_523_summary.json")
STATE_CACHE = os.path.join(REVIEW, "_523_uei_state_cache.json")

BUILT_BY = "523_spiderweb_harvest.py"
BUILT_DATE = "2026-09-01"

# I3. Three layers, because each one alone has already failed:
#
#   a) the `blocklisted_parent` column - flags ONE of the three roll-ups that
#      existed on 2026-08-31, so on its own it leaked two edges;
#   b) this hard-coded set - correct on 2026-08-31 and immediately stale: the
#      2026-09-01 source expansion surfaced V425F7L4X4R1 and FVP4QBB76J19,
#      two MORE registrants recorded as GOVERNMENT OF THE UNITED STATES;
#   c) FED_NAME below, which recognises the SHAPE rather than the instance and
#      is the only layer that survives the next extract.
#
# A hard-coded identifier list is a snapshot of a moving set. It is kept as a
# floor, not as the mechanism.
BLOCKLISTED_PARENT_UEIS = {"GK1ECPGZV897", "NW2RJN8TQQW1", "R8U7S9K184F6",
                           "V425F7L4X4R1", "FVP4QBB76J19"}
FED_NAME = "GOVERNMENT OF THE UNITED STATES"
BLOCKLIST_REASON = (
    "federal_registrant_rollup: recorded as GOVERNMENT OF THE UNITED STATES; "
    "its children include BIA, IHS and tribally-controlled grant schools"
)


def federal_rollup_ueis(edges):
    """Every parent UEI ever recorded under the federal roll-up name, plus the
    hard-coded floor. Derived on every run so a new extract cannot open a hole."""
    s = set(BLOCKLISTED_PARENT_UEIS)
    for r in edges:
        if FED_NAME in (r.get("parent_name") or "").upper():
            s.add((r.get("parent_uei") or "").strip().upper())
        if (r.get("blocklisted_parent") or "").strip() == "1":
            s.add((r.get("parent_uei") or "").strip().upper())
    s.discard("")
    return s

# I4.
NOT_OWNERSHIP_EDGE_TYPES = {"prime_to_sub"}

# THE ANCHOR-QUALITY GUARD, added 2026-09-01 after hand-validation.
#
# A candidate is only as good as the keyed end it hangs from. Three of the
# twenty rows checked by hand hung from ONE bad anchor:
#
#   AKNF-INPTBW-00-ARCSLO (Barrow) holds 103 UEIs. 58 arrived by `cluster_v3`
#   with the rationale "Algorithmic name clustering, unreviewed", and reading
#   their legal names shows what the clustering matched on:
#
#       Ho'olaulima GOVERNMENT Solutions      A+ GOVERNMENT Solutions
#       ATI GOVERNMENT Solutions              GOVERNMENT & Industrial Supply
#       Qayaq GOVERNMENT Solutions            GOVERNMENT Technical Services
#       Koman Propper GOVERNMENT Apparel      GOVERNMENT Systems Inc
#       Computer Sciences Corporation         Copper River Enterprise Services
#
#   Barrow's real subsidiary is UIC GOVERNMENT Services LLC. The cluster keyed
#   on the word "government" - a stopword in federal contracting - and swept
#   in General Dynamics IT's parent along the way.
#
# This script cannot fix the ledger (it does not own it) but it MUST NOT
# propagate the defect. So an anchor is refused when BOTH hold:
#   * its attribution is unreviewed and algorithmic, AND
#   * its legal name shares no DISTINCTIVE token with the entity it is keyed to
# and the refusals are written out by name so the ledger's owner can act on a
# list rather than on an anecdote.
GENERIC_TOKENS = {
    "GOVERNMENT", "SOLUTIONS", "SERVICES", "SERVICE", "TECHNOLOGY",
    "TECHNOLOGIES", "TECH", "SYSTEMS", "SYSTEM", "ENTERPRISE", "ENTERPRISES",
    "GROUP", "HOLDINGS", "HOLDING", "INDUSTRIES", "INDUSTRIAL", "MANAGEMENT",
    "CONSULTING", "CONSULTANTS", "CONTRACTING", "CONTRACTORS", "CONSTRUCTION",
    "FEDERAL", "INTERNATIONAL", "GLOBAL", "AMERICAN", "AMERICA", "NATIONAL",
    "GENERAL", "PROFESSIONAL", "SPECIALTY", "SUPPORT", "SUPPLY", "PARTNERS",
    "ASSOCIATES", "VENTURES", "DEVELOPMENT", "OPERATIONS", "RESOURCES",
    "SECURITY", "DEFENSE", "AEROSPACE", "ENGINEERING", "LOGISTICS",
    "INFORMATION", "DATA", "NETWORK", "NETWORKS", "PROJECT", "PROJECTS",
    "BUSINESS", "COMMERCIAL", "INDUSTRY", "MANUFACTURING", "PRODUCTS",
    # identity words that describe the CLASS, never the entity
    "NATIVE", "INDIAN", "TRIBAL", "TRIBE", "TRIBES", "NATION", "VILLAGE",
    "CORPORATION", "COMPANY", "ALASKA", "ALASKAN", "AND", "OF", "THE", "FOR",
    # government FORM words. Added after a hand check found COUNTY OF MOULTRIE
    # (Illinois) keyed to Forest County Potawatomi on the shared token COUNTY.
    "COUNTY", "CITY", "TOWN", "TOWNSHIP", "BOROUGH", "PARISH", "DISTRICT",
    "STATE", "AUTHORITY", "COMMISSION", "BOARD", "COUNCIL", "DEPARTMENT",
    "OFFICE", "BUREAU", "AGENCY", "PUBLIC", "MUNICIPAL", "REGIONAL", "AREA",
    "CENTER", "CENTRE", "INSTITUTE", "FOUNDATION", "ASSOCIATION", "SOCIETY",
    "UNIVERSITY", "COLLEGE", "SCHOOL", "HOSPITAL", "CLINIC", "MEDICAL",
    "HOUSING", "COMMUNITY", "BAND", "PUEBLO", "RANCHERIA", "RESERVATION",
}
UNREVIEWED_METHODS = {"cluster_v3", "need_v6", "identifier_graph_resolution"}

# A PLACE NAMED FOR A TRIBE IS NOT THE TRIBE - the Tuscarawas precedent in
# docs/NATIVE_ENTITY_NUANCES.md, met twice in one hand check:
#
#   KLAMATH 9-1-1 EMERGENCY COMMUNICATIONS DISTRICT -> TRBF-KLAMTH-00
#   COUNTY OF MOULTRIE                              -> TRBF-FSTCTY-00
#
# Both share a token with the entity they are keyed to, so token overlap alone
# clears them. But a county emergency-services district is a unit of STATE
# government and a tribe does not own one. When an unreviewed link's legal
# name announces itself as a local-government body, the shared place name is
# the whole of the evidence, and that is not enough.
GOV_BODY_WORDS = {
    "COUNTY", "CITY", "TOWN", "TOWNSHIP", "BOROUGH", "PARISH", "MUNICIPAL",
    "SHERIFF", "POLICE", "ATTORNEY", "ATTORNEYS", "PROSECUTOR", "MARSHAL",
    "EMERGENCY", "FIRE", "AMBULANCE", "TRANSIT", "SANITATION",
    "COMMISSIONERS", "SUPERVISORS", "TREASURER", "ASSESSOR", "CLERK",
    "PUBLIC", "STATE", "COMMONWEALTH", "MUNICIPALITY",
}


def distinctive(s):
    return {t for t in norm_name(s).split() if t not in GENERIC_TOKENS
            and len(t) > 2}

TIER = "B"
TIER_REASON = (
    "FAR 4.18 / 52.204-17 self-certified ownership declaration filed through "
    "SAM and reported on an FPDS/USAspending transaction. Evidence of a "
    "declared CONNECTION, not proof of Native ownership: the declared highest "
    "owner is routinely the highest INCORPORATED owner and the last hop to "
    "the tribe is Cedar's, not SAM's."
)

LEGAL_SUFFIX = re.compile(
    r"\b(INC|INCORPORATED|LLC|L L C|LLP|LP|CORP|CORPORATION|CO|COMPANY|"
    r"LTD|LIMITED|LIABILITY|PLLC|PC|THE|A JV|JV|JOINT VENTURE)\b"
)


def norm_name(s: str) -> str:
    # FOLD DIACRITICS FIRST. The spine writes Ukpeagvik Inupiat Corporation
    # with a dotted g and a tilde n; blanking non-ASCII split UKPEAGVIK into
    # two tokens, so the corporation's own second UEI failed to match its own
    # entity and was published as a holding company above itself. Decomposing
    # and dropping the combining marks keeps the token whole.
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.upper()
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = LEGAL_SUFFIX.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def same_registrant(a_norm, b_norm):
    """One legal person written two ways - NOT a parent and a child.

    Token sets after legal-form words are removed: equal, or one contained in
    the other with only CLASS words as the difference.

        TEPA EC LIMITED LIABILITY COMPANY  ==  TEPA EC LLC
        CENTRAL COUNCIL TLINGIT AND HAIDA INDIAN TRIBES OF ALASKA
                                           ==  CENTRAL COUNCIL TLINGIT
                                               AND HAIDA INDIAN

    COUNTER-EXAMPLE that sets the bound, and the reason the difference must be
    class words ONLY: `TEPA EC, LLC` and `TEPA LLC` differ by {EC}, which is
    not a class word. They are a real subsidiary and its real parent, and a
    plain prefix test would have merged them.
    """
    A, B = set(a_norm.split()), set(b_norm.split())
    if not A or not B:
        return False
    if not (A <= B or B <= A):
        return False
    return not (A ^ B) - GENERIC_TOKENS


def read_csv(path):
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    tmp = path + ".part"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    os.replace(tmp, path)
    return len(rows)


# ---------------------------------------------------------------------------
# keyed-ness
# ---------------------------------------------------------------------------
def load_keying():
    """Return uei -> dict(entity_id, name, tier, via).

    TWO sources disagree about what "keyed" means and the difference is the
    single biggest correction this pass makes to the plan's headline number:

      cedar_identifier_ledger_final.csv   4,074 UEIs   the ledger, tiered
      cedar_identifier_graph_nodes.csv    4,904 UEIs   169's resolution

    1,222 UEIs are resolved in the graph and absent from the ledger. Counting
    only the ledger reports 1,102 one-ended edges; counting the union reports
    559. The other 543 are RE-DISCOVERY of an entity the graph already knows,
    not new identification, and shipping them as new would inflate the harvest
    by roughly 2x. They are declined into their own named bucket instead, and
    that bucket is itself a ledger-backfill opportunity.
    """
    keyed = {}
    for r in read_csv(GNODES_IN):
        if r.get("identifier_type") != "UEI":
            continue
        ent = (r.get("resolved_entity") or "").strip()
        if not ent:
            continue
        u = (r.get("identifier") or "").strip().upper()
        if not u:
            continue
        keyed[u] = {
            "entity_id": ent,
            "name": (r.get("observed_name") or "").strip(),
            "legal_name": (r.get("observed_name") or "").strip(),
            "method": "identifier_graph_resolution",
            "rationale": "resolved by 169_build_identifier_graph.py at %s hop(s)"
                         % (r.get("resolution_hops") or "?"),
            "tier": (r.get("resolved_tier") or "").strip(),
            "via": "identifier_graph",
        }
    spine_name = {}
    for r in read_csv(SPINE_IN):
        spine_name[r["tribe_id"]] = r.get("canonical_name") or ""
    # the ledger wins where both speak: it is the tiered, ruled surface
    for r in read_csv(LEDGER_IN):
        if r.get("identifier_type") != "UEI":
            continue
        ent = (r.get("tribe_id") or "").strip()
        u = (r.get("identifier") or "").strip().upper()
        if not ent or not u:
            continue
        keyed[u] = {
            "entity_id": ent,
            "name": (r.get("canonical_name") or "").strip(),
            "legal_name": (r.get("legal_business_name") or "").strip(),
            "method": (r.get("attribution_method") or "").strip(),
            "rationale": (r.get("tier_rationale") or "").strip(),
            "tier": (r.get("confidence_tier") or "").strip(),
            "via": "identifier_ledger",
            "cedar_uid": (r.get("cedar_uid") or "").strip(),
        }
    # cedar_uid for graph-only keyings, from the spine
    spine_uid = {r["tribe_id"]: (r.get("cedar_uid") or "")
                 for r in read_csv(SPINE_IN)}
    for u, d in keyed.items():
        d.setdefault("cedar_uid", spine_uid.get(d["entity_id"], ""))
        if not d["name"]:
            d["name"] = spine_name.get(d["entity_id"], "")
    return keyed, spine_uid, spine_name


def load_blocked_identifiers():
    """UEIs carrying a tier-X negative ruling in the identifier graph."""
    blocked = {}
    for r in read_csv(GEDGES_IN):
        if r.get("edge_kind") != "BLOCK":
            continue
        n = r.get("from_node") or ""
        if n.startswith("UEI:"):
            blocked[n[4:].strip().upper()] = (r.get("evidence") or "")[:200]
    for r in read_csv(GNODES_IN):
        if r.get("identifier_type") == "UEI" and (r.get("blocked") or "").strip():
            blocked.setdefault((r.get("identifier") or "").strip().upper(),
                               r.get("block_reason") or "blocked node")
    return blocked


def load_spine_names():
    idx = defaultdict(set)
    for r in read_csv(SPINE_IN):
        n = norm_name(r.get("canonical_name"))
        if n:
            idx[n].add(r["tribe_id"])
        for a in (r.get("aliases") or "").split("|"):
            n = norm_name(a)
            if n:
                idx[n].add(r["tribe_id"])
    return idx


def load_uei_attributes(needed):
    """CAGE / state / city for a bounded set of UEIs.

    Cached, because two of the three sources are 133 MB and 60 MB and the
    needed set is a few hundred rows.
    """
    needed = {u.upper() for u in needed}
    cache = {}
    if os.path.exists(STATE_CACHE):
        try:
            cache = json.load(open(STATE_CACHE, encoding="utf-8"))
        except Exception:
            cache = {}
    if needed <= set(cache):
        return {u: cache[u] for u in needed}

    attrs = {u: {"cage": "", "state": "", "n_award_rows": 0} for u in needed}
    for r in read_csv(CAGEMAP_IN):
        u = (r.get("uei") or "").strip().upper()
        if u in attrs and not attrs[u]["cage"]:
            attrs[u]["cage"] = (r.get("cage_code") or "").strip()

    def stream(path, uei_col, cage_col, state_col):
        if not os.path.exists(path):
            return
        with open(path, newline="", encoding="utf-8", errors="replace") as f:
            for r in csv.DictReader(f):
                u = (r.get(uei_col) or "").strip().upper()
                if u not in attrs:
                    continue
                a = attrs[u]
                a["n_award_rows"] += 1
                if not a["state"]:
                    a["state"] = (r.get(state_col) or "").strip()
                if not a["cage"]:
                    a["cage"] = (r.get(cage_col) or "").strip()

    stream(AWARDS_IN, "awardee_uei", "cage_code", "recipient_state_code")
    stream(SUBS_IN, "sub_uei", "sub_cage", "sub_state")

    cache.update(attrs)
    try:
        with open(STATE_CACHE, "w", encoding="utf-8") as f:
            json.dump(cache, f)
    except Exception:
        pass
    return attrs


# ---------------------------------------------------------------------------
# PHASE 1
# ---------------------------------------------------------------------------
def harvest(quiet=False):
    edges = read_csv(EDGES_IN)
    n_source = len(edges)
    blocklist = federal_rollup_ueis(edges)
    keyed, spine_uid, spine_name = load_keying()
    gnode = {}
    for r in read_csv(GNODES_IN):
        if r.get("identifier_type") == "UEI":
            gnode[(r.get("identifier") or "").strip().upper()] = r
    blocked = load_blocked_identifiers()
    spine_idx = load_spine_names()

    ledger_keyed = set()
    for r in read_csv(LEDGER_IN):
        if r.get("identifier_type") == "UEI" and (r.get("tribe_id") or "").strip():
            ledger_keyed.add((r.get("identifier") or "").strip().upper())

    _spine_rows = read_csv(SPINE_IN)
    entity_tokens = defaultdict(set)
    for row in _spine_rows:
        entity_tokens[row["tribe_id"]] |= distinctive(row.get("canonical_name"))
        for al in (row.get("aliases") or "").split("|"):
            entity_tokens[row["tribe_id"]] |= distinctive(al)
    suspect_anchor = {}

    # THE SUBSET RULE AND THE COUNTER-EXAMPLE THAT BOUNDS IT.
    #
    # The spine stores SHORT canonical names ("Gila River"); registrants file
    # LONG legal ones ("GILA RIVER INDIAN COMMUNITY"). A hand check found
    # GILA RIVER TELECOMMUNICATIONS declaring its parent as GILA RIVER INDIAN
    # COMMUNITY - the keyed entity itself, under a UEI the ledger lacks -
    # and the string-equality test missed it. So: same entity when the
    # entity's distinctive tokens are all present in the declared name and
    # every EXTRA token is a class word (INDIAN, COMMUNITY, TRIBE...).
    #
    # COUNTER-EXAMPLE, and the reason this rule carries a uniqueness test:
    # `Delaware Nation` and `Delaware Tribe of Indians` are TWO SOVEREIGNS and
    # both reduce to the single distinctive token {DELAWARE}. Applying the
    # subset rule to either would recreate the exact contamination that
    # `354_correction_register.py` is still chasing through the ledgers. So
    # the rule fires only when that token set belongs to ONE spine entity.
    _tokens_to_entities = defaultdict(set)
    for row in _spine_rows:
        t = frozenset(distinctive(row.get("canonical_name")))
        if t:
            _tokens_to_entities[t].add(row["tribe_id"])

    def same_entity_by_tokens(unkeyed_norm, tid):
        ent = entity_tokens.get(tid, set())
        if not ent:
            return False
        if len(_tokens_to_entities.get(frozenset(ent), ())) != 1:
            return False          # ambiguous token set - the Delaware guard
        got = set(unkeyed_norm.split())
        if not ent <= got:
            return False
        return not (got - ent - GENERIC_TOKENS)

    def bad_anchor(kd, uei):
        m = (kd.get("method") or "")
        if m not in UNREVIEWED_METHODS and not m.startswith(
                "cross_dataset_propagation"):
            return False
        ln = kd.get("legal_name") or kd.get("name") or ""
        if not ln:
            return False
        if not (distinctive(ln) & entity_tokens.get(kd["entity_id"], set())):
            return True
        # the Tuscarawas case: a local-government body sharing only a place
        # name with the tribe it has been keyed to
        return bool(set(norm_name(ln).split()) & GOV_BODY_WORDS)

    declines = Counter()
    decline_note = {}

    def decline(bucket, note):
        declines[bucket] += 1
        decline_note[bucket] = note

    # --- pass A: filter to harvestable ownership edges -------------------
    live = []
    seen_edge = set()
    for r in edges:
        c = (r.get("child_uei") or "").strip().upper()
        p = (r.get("parent_uei") or "").strip().upper()
        et = (r.get("edge_type") or "").strip()

        if not c or not p:
            decline("blank_uei_on_one_end",
                    "an edge with no identifier on one end identifies nothing")
            continue
        if c == p:
            decline("self_edge_carries_no_information",
                    "child == parent; 13 already drops these, kept as a guard")
            continue
        if et in NOT_OWNERSHIP_EDGE_TYPES:
            decline("edge_type_prime_to_sub_is_contracting_not_ownership",
                    "I4: a subaward is a contracting relationship. "
                    "13_build_fpds_hierarchy.py forbids propagating ownership "
                    "along these in capitals in its own docstring.")
            continue
        if p in blocklist:
            decline("blocklisted_federal_rollup_parent", "I3: " + BLOCKLIST_REASON)
            continue

        ck, pk = c in keyed, p in keyed
        if ck and pk:
            if (c in ledger_keyed) != (p in ledger_keyed):
                decline("both_ends_keyed_but_one_only_via_identifier_graph",
                        "not a harvest: the 'unkeyed' end is already resolved "
                        "by 169_build_identifier_graph.py and is simply absent "
                        "from cedar_identifier_ledger_final.csv. This is a "
                        "LEDGER BACKFILL opportunity, not a new firm.")
            else:
                decline("both_ends_keyed_nothing_to_identify",
                        "both ends already resolve to a Cedar entity")
            continue
        if not ck and not pk:
            decline("neither_end_keyed_no_anchor",
                    "no keyed end means no family to attach to; these need a "
                    "different route (Q3 of the identifier-graph queues ranks "
                    "the ones that at least carry dataset presence)")
            continue

        key_end = "parent" if pk else "child"
        keyed_uei = p if pk else c
        unkeyed_uei = c if pk else p
        kd = keyed[keyed_uei]

        if (kd.get("tier") or "").upper() == "X":
            decline("keyed_end_is_a_tier_X_refutation",
                    "the keyed end's attribution has been REFUTED; inheriting "
                    "from a refuted link re-imports the defect")
            continue
        if bad_anchor(kd, keyed_uei):
            suspect_anchor[keyed_uei] = kd
            decline("keyed_end_anchor_is_an_unreviewed_name_cluster",
                    "the keyed end reached its entity by unreviewed "
                    "algorithmic name clustering and its legal name shares NO "
                    "distinctive token with that entity - the generic-token "
                    "cluster defect (58 UEIs keyed to Barrow on the word "
                    "'government'). Listed by name in "
                    "523_suspect_keyed_anchors.csv; the anchor must be ruled "
                    "on before anything can hang from it.")
            continue
        if unkeyed_uei in blocked:
            decline("unkeyed_end_carries_a_negative_ruling",
                    "the unkeyed identifier already has a tier-X BLOCK in the "
                    "identifier graph; a declared edge does not overturn a ruling")
            continue

        sig = (c, p, et)
        if sig in seen_edge:
            decline("duplicate_child_parent_edge_type_across_source_files",
                    "the same declaration observed in more than one extract")
            continue
        seen_edge.add(sig)
        live.append((r, key_end, keyed_uei, unkeyed_uei, kd))

    # --- topology, computed on the OWNERSHIP edge set only ----------------
    own = [r for r in edges
           if (r.get("edge_type") or "") not in NOT_OWNERSHIP_EDGE_TYPES
           and (r.get("parent_uei") or "").strip().upper() not in blocklist]
    is_parent_somewhere = {(r.get("parent_uei") or "").strip().upper() for r in own}
    is_child_somewhere = {(r.get("child_uei") or "").strip().upper() for r in own}
    children_of = defaultdict(set)
    for r in own:
        children_of[(r.get("parent_uei") or "").strip().upper()].add(
            (r.get("child_uei") or "").strip().upper())

    # which keyed entities does each unkeyed firm attach to?
    fam = defaultdict(set)
    for (_r, key_end, ku, uu, kd) in live:
        fam[uu].add(kd["entity_id"])

    attrs = load_uei_attributes(
        {uu for (_r, _k, _ku, uu, _kd) in live} | set(fam))

    rows = []
    # THE DEFECT THE HAND-VALIDATION FOUND, AND THE FIX.
    #
    # A random sample of 20 candidates checked by hand on 2026-09-01 stood up
    # 8 times out of 20. Nothing was FABRICATED - every row cited a real
    # declared edge - but 11 were MISCLASSIFIED, and the same way each time:
    #
    #     KOMAN CONSTRUCTION, LLC  ->  KOMAN CONSTRUCTION LLC
    #     GILA RIVER INDIAN COMMUNITY -> GILA RIVER INDIAN COMMUNITY
    #     ONEIDA NATION -> ONEIDA NATION
    #     FLATWATER, INCORPORATED -> FLATWATER  INCORPORATED
    #     TATITLEK TECHNOLOGIES -> TATITLEK CORPORATION   (= ANVC-TATITL-00)
    #     NORTH WIND SOLUTIONS -> COOK INLET REGION INC   (= ANRC-CKINLT-00)
    #
    # These are not holding companies. They are ONE registrant holding TWO
    # UEIs, or an entity we already hold whose own top-level UEI is missing
    # from the ledger. `13` drops a self-edge only when child_uei ==
    # parent_uei, so a renewed or reassigned UEI survives as a "parent".
    # Calling that an intermediate holdco is a false ownership statement, and
    # at 26% + 30% of the table it was the dominant error mode.
    #
    # They are not dropped - they are the single most useful thing in the
    # harvest, because each one is a UEI the identifier ledger is missing for
    # an entity Cedar already holds. They are routed to their own table with
    # their own evidence kind, and the two kinds are kept apart because their
    # strength is not the same:
    #
    #   identical_declared_name_on_the_same_edge   both ends of ONE row carry
    #       the same legal name. Within-row string equality, no spine lookup,
    #       no Bristol Bay exposure.
    #   matches_the_keyed_entitys_own_spine_name   a name match against the
    #       spine. `cluster_v3` keyed BRISTOL BAY AREA HEALTH CORPORATION to
    #       the ANCSA regional this way. REVIEW, never auto-apply.
    backfill = []
    # A parenthetical ACRONYM is decoration; a parenthetical PLACE is the
    # discriminator. "Tanadgusix Corporation (TDX)" and "TANADGUSIX
    # CORPORATION" are one entity, and the declared parent of BSET, LLC is
    # exactly that - a hand check caught it slipping through as a holdco.
    # "Oneida Nation (Wisconsin)" and "Oneida Nation (New York)" are TWO
    # SOVEREIGNS and stripping their parenthetical merges them, which is why
    # IDENTIFIER_STANDARD forbids dropping state tokens. So the paren-stripped
    # form is added ONLY when what is inside looks like an acronym.
    _ACRONYM = re.compile(r"^\(([A-Z]{2,5})\)$")
    _STATE_ISH = re.compile(r"[A-Z]{2}")

    def _paren_alias(nm):
        m = re.search(r"\(([^)]*)\)\s*$", nm or "")
        if not m:
            return None
        inner = m.group(1).strip()
        if not inner or len(inner) > 5 or " " in inner:
            return None
        if not inner.isupper() or not inner.isalpha():
            return None
        if len(inner) == 2:        # a two-letter all-caps token is a US state
            return None
        return norm_name(nm[:m.start()])

    _spine_rows = read_csv(SPINE_IN)
    spine_names_of = defaultdict(set)
    for row in _spine_rows:
        cn = row.get("canonical_name") or ""
        spine_names_of[row["tribe_id"]].add(norm_name(cn))
        pa = _paren_alias(cn)
        if pa:
            spine_names_of[row["tribe_id"]].add(pa)
        for al in (row.get("aliases") or "").split("|"):
            if al.strip():
                spine_names_of[row["tribe_id"]].add(norm_name(al))
                pa = _paren_alias(al)
                if pa:
                    spine_names_of[row["tribe_id"]].add(pa)
    for k in spine_names_of:
        spine_names_of[k].discard("")

    def add_backfill(r, kd, uu, unkeyed_name, kind, disputed, note):
        a = attrs.get(uu, {})
        g = gnode.get(uu, {})
        nm = sorted(spine_idx.get(norm_name(unkeyed_name), ()))
        backfill.append({
            "unkeyed_uei": uu,
            "declared_name": unkeyed_name,
            "cage": a.get("cage", ""),
            "state": a.get("state", ""),
            "usd_observed": round(float(g.get("usd_observed") or 0), 2),
            "n_datasets": int(g.get("n_datasets") or 0),
            "evidence_kind": kind,
            "paired_keyed_uei": kd["_ku"],
            "paired_keyed_tribe_id": kd["entity_id"],
            "paired_keyed_name": kd.get("name", ""),
            "paired_keyed_tier": kd.get("tier", ""),
            "declared_edge": "%s (%s) -> %s (%s) [%s]" % (
                r.get("child_name"), r.get("child_uei"),
                r.get("parent_name"), r.get("parent_uei"),
                r.get("edge_type")),
            "n_observations": r.get("n_observations", ""),
            "years": "%s-%s" % (r.get("first_year"), r.get("last_year")),
            "proposed_backfill_tribe_id": ("" if disputed else kd["entity_id"]),
            "name_match_tribe_ids": "|".join(nm),
            "target_disputed": "Y" if disputed else "",
            "dispute_note": note,
            "tier": TIER,
            "action": ("Add this UEI to cedar_identifier_ledger_final.csv "
                       "for the proposed entity at tier B - it is not a new "
                       "firm. DISPUTED rows need a ruling first."),
            "built_by": BUILT_BY,
            "built_date": BUILT_DATE,
        })

    for (r, key_end, ku, uu, kd) in live:
        kd = dict(kd)
        kd["_ku"] = ku
        unkeyed_name = (r.get("child_name") if key_end == "parent"
                        else r.get("parent_name")) or ""
        cn, pn = norm_name(r.get("child_name")), norm_name(r.get("parent_name"))
        un = norm_name(unkeyed_name)

        if not un:
            decline("unkeyed_end_has_no_declared_name",
                    "the declaration names an identifier and no legal name; a "
                    "candidate with no name identifies nothing and cannot be "
                    "ruled on")
            continue
        if cn and pn and same_registrant(cn, pn):
            nm = sorted(spine_idx.get(un, ()))
            disputed = bool(nm) and kd["entity_id"] not in nm
            add_backfill(r, kd, uu, unkeyed_name,
                         "identical_declared_name_on_the_same_edge", disputed,
                         ("the declared name resolves to %s, not to the keyed "
                          "end's entity %s" % ("|".join(nm), kd["entity_id"]))
                         if disputed else "")
            decline("unkeyed_end_is_the_SAME_REGISTRANT_under_a_second_uei",
                    "both ends of the row carry the same legal name: one "
                    "registrant with two UEIs, not an ownership relationship. "
                    "NOT dropped - routed to "
                    "523_identifier_backfill_candidates.csv, where it is a "
                    "missing ledger row for an entity Cedar already holds.")
            continue
        if un in spine_names_of.get(kd["entity_id"], ())                 or same_entity_by_tokens(un, kd["entity_id"]):
            add_backfill(r, kd, uu, unkeyed_name,
                         "matches_the_keyed_entitys_own_spine_name", False, "")
            decline("unkeyed_end_name_is_the_keyed_entitys_own_spine_name",
                    "the declared parent/child IS the keyed entity under a "
                    "second UEI, by name match against the spine. NOT dropped "
                    "- routed to 523_identifier_backfill_candidates.csv for "
                    "REVIEW, because a spine name match is exactly how "
                    "BRISTOL BAY AREA HEALTH CORPORATION was keyed to the "
                    "ANCSA regional.")
            continue

        conflict = len(fam[uu]) > 1
        if key_end == "parent":
            direction = "keyed_is_parent__unkeyed_firm_sits_BELOW_a_known_entity"
            if conflict:
                cls = "unclear"
            elif uu in is_parent_somewhere and children_of[uu]:
                cls = "intermediate_holdco"
            else:
                cls = "subsidiary_of"
        else:
            direction = "keyed_is_child__unkeyed_firm_sits_ABOVE_a_known_entity"
            cls = "unclear" if conflict else "intermediate_holdco"

        nn = norm_name(unkeyed_name)
        nm = sorted(spine_idx.get(nn, ()))
        flags = []
        if conflict:
            flags.append("attaches_to_%d_distinct_keyed_entities" % len(fam[uu]))
        if (kd.get("tier") or "").upper() == "C":
            flags.append("keyed_end_is_tier_C")
        if kd.get("via") == "identifier_graph":
            flags.append("keyed_end_resolved_by_graph_not_ledger")
        import difflib
        if difflib.SequenceMatcher(None, cn, pn).ratio() >= 0.80:
            flags.append("declared_names_are_NEAR_DUPLICATES_possible_typo_"
                         "of_one_registrant")
        if int(r.get("n_observations") or 0) <= 1:
            flags.append("single_observation_declaration")
        if nm:
            flags.append("declared_name_normalises_to_a_spine_entity")
            if kd["entity_id"] not in nm:
                flags.append("NAME_MATCH_DISAGREES_WITH_DECLARED_FAMILY")
        a = attrs.get(uu, {})
        rows.append({
            "candidate_id": "SPW-%s-%s-%s" % (r.get("child_uei"),
                                              r.get("parent_uei"),
                                              (r.get("edge_type") or "")[:4]),
            "attachment_class": cls,
            "direction": direction,
            "keyed_cedar_uid": kd.get("cedar_uid", ""),
            "keyed_tribe_id": kd["entity_id"],
            "keyed_canonical_name": kd.get("name") or spine_name.get(kd["entity_id"], ""),
            "keyed_uei": ku,
            "keyed_end_tier": kd.get("tier", ""),
            "keyed_end_source": kd.get("via", ""),
            "unkeyed_uei": uu,
            "unkeyed_declared_name": unkeyed_name,
            "unkeyed_cage": a.get("cage", ""),
            "unkeyed_state": a.get("state", ""),
            "unkeyed_award_rows_observed": a.get("n_award_rows", 0),
            "unkeyed_is_declared_top_of_family":
                "N" if uu in is_child_somewhere else "Y",
            "unkeyed_has_declared_children": "Y" if children_of[uu] else "N",
            "declared_edge_type": r.get("edge_type", ""),
            "declared_child_uei": r.get("child_uei", ""),
            "declared_child_name": r.get("child_name", ""),
            "declared_parent_uei": r.get("parent_uei", ""),
            "declared_parent_name": r.get("parent_name", ""),
            "hops_from_keyed_entity": 1,
            "tier": TIER,
            "tier_reason": TIER_REASON,
            "n_observations": r.get("n_observations", ""),
            "first_year": r.get("first_year", ""),
            "last_year": r.get("last_year", ""),
            "source_file": r.get("source_file", ""),
            "name_match_tribe_ids": "|".join(nm),
            "review_flags": "|".join(flags),
            "disposition": "CANDIDATE_AWAITING_RULING",
            "built_by": BUILT_BY,
            "built_date": BUILT_DATE,
        })

    # --- sibling_under_same_parent ---------------------------------------
    # An unkeyed firm U and a keyed firm K that declare THE SAME third parent
    # P. This is NOT an ownership assertion about K -> U; it is the literal
    # fact that two filers named the same parent. hops = 2, and the class name
    # says so. It is emitted because a shared declared parent is the strongest
    # thing we hold about the 974 edges where neither end is keyed.
    sib_seen = set()
    sib_rows = []
    for p, kids in children_of.items():
        if p in keyed or p in blocklist:
            continue
        keyed_kids = sorted(k for k in kids if k in keyed
                            and (keyed[k].get("tier") or "").upper() != "X"
                            # an anchor refused at hops 1 is not fit to anchor
                            # a sibling at hops 2 either: General Dynamics IT
                            # arrived here through Barrow's 'government'
                            # cluster and was published as a Barrow sibling.
                            and not bad_anchor(keyed[k], k))
        if not keyed_kids:
            continue
        unkeyed_kids = sorted(k for k in kids if k not in keyed
                              and k not in blocked)
        if not unkeyed_kids:
            continue
        ents = {keyed[k]["entity_id"] for k in keyed_kids}
        for uu in unkeyed_kids:
            if (uu, p) in sib_seen:
                continue
            sib_seen.add((uu, p))
            anchor = keyed[keyed_kids[0]]
            src = next((r for r in own
                        if (r.get("child_uei") or "").strip().upper() == uu
                        and (r.get("parent_uei") or "").strip().upper() == p), None)
            if src is None:
                continue
            # the same three filters the hops-1 path applies: no name, or the
            # same registrant twice, is not a sibling either.
            _un = norm_name(src.get("child_name"))
            if not _un:
                continue
            if _un == norm_name(src.get("parent_name")):
                continue
            if _un in spine_names_of.get(anchor["entity_id"], ()):
                continue
            flags = ["hops_2_shared_declared_parent_NOT_an_ownership_assertion"]
            if len(ents) > 1:
                flags.append("shared_parent_spans_%d_keyed_entities" % len(ents))
            a = attrs.get(uu, {})
            sib_rows.append({
                "candidate_id": "SPW-SIB-%s-%s" % (uu, p),
                "attachment_class": "sibling_under_same_parent",
                "direction": "shared_declared_parent__unkeyed_firm_is_a_SIBLING_of_a_known_entity",
                "keyed_cedar_uid": anchor.get("cedar_uid", ""),
                "keyed_tribe_id": anchor["entity_id"],
                "keyed_canonical_name": anchor.get("name", ""),
                "keyed_uei": keyed_kids[0],
                "keyed_end_tier": anchor.get("tier", ""),
                "keyed_end_source": anchor.get("via", ""),
                "unkeyed_uei": uu,
                "unkeyed_declared_name": (src.get("child_name") or ""),
                "unkeyed_cage": a.get("cage", ""),
                "unkeyed_state": a.get("state", ""),
                "unkeyed_award_rows_observed": a.get("n_award_rows", 0),
                "unkeyed_is_declared_top_of_family": "N",
                "unkeyed_has_declared_children": "Y" if children_of.get(uu) else "N",
                "declared_edge_type": src.get("edge_type", ""),
                "declared_child_uei": src.get("child_uei", ""),
                "declared_child_name": src.get("child_name", ""),
                "declared_parent_uei": src.get("parent_uei", ""),
                "declared_parent_name": src.get("parent_name", ""),
                "hops_from_keyed_entity": 2,
                "tier": TIER,
                "tier_reason": TIER_REASON + " SIBLING: the shared parent is "
                               "itself unkeyed, so this row says only that two "
                               "filers named the same parent.",
                "n_observations": src.get("n_observations", ""),
                "first_year": src.get("first_year", ""),
                "last_year": src.get("last_year", ""),
                "source_file": src.get("source_file", ""),
                "name_match_tribe_ids": "|".join(sorted(spine_idx.get(
                    norm_name(src.get("child_name")), ()))),
                "review_flags": "|".join(flags),
                "disposition": "CANDIDATE_AWAITING_RULING",
                "built_by": BUILT_BY,
                "built_date": BUILT_DATE,
            })

    # sibling rows come from the neither-keyed bucket, which is already
    # declined and counted. Emitting them does not change the accounting: the
    # decline is about the EDGE, this is a derived row about the FIRM.
    all_rows = rows + sib_rows

    # --- RANKING -----------------------------------------------------------
    # A flat list of several hundred candidates is a chore. What a human wants
    # to rule on first is: real money, seen in several datasets, declared many
    # times, unambiguous. Each of those is measured, none is invented, and the
    # score's inputs are written on the row so a reviewer can disagree with the
    # weighting without re-deriving the evidence.
    CLASS_STRENGTH = {
        "subsidiary_of": 1.00,          # keyed parent declares this firm a child
        "intermediate_holdco": 0.80,    # a holdco directly above/below a known entity
        "sibling_under_same_parent": 0.45,   # 2 hops, shared parent only
        "unclear": 0.35,                # attaches to more than one family
    }
    for r in all_rows:
        g = gnode.get(r["unkeyed_uei"], {})
        usd = float(g.get("usd_observed") or 0)
        nds = int(g.get("n_datasets") or 0)
        nobs = int(r.get("n_observations") or 0)
        # usd_observed can be NEGATIVE: a de-obligation year nets below zero.
        # Magnitude is what ranks work, so the score uses abs() and the sign is
        # preserved on the row for the reviewer.
        r["unkeyed_usd_observed"] = round(usd, 2)
        usd = abs(usd)
        r["unkeyed_n_datasets"] = nds
        unamb = (r["attachment_class"] != "unclear"
                 and int(r["hops_from_keyed_entity"]) == 1
                 and "NAME_MATCH_DISAGREES_WITH_DECLARED_FAMILY" not in r["review_flags"]
                 and "NEAR_DUPLICATES" not in r["review_flags"]
                 # ONE observation is a filing, not a pattern. A hand check
                 # found OKLAHOMA STATE UNIVERSITY MEDICAL AUTHORITY declaring
                 # CHOCTAW NATION OF OKLAHOMA as its parent on exactly one 2026
                 # row. Real data, wrong conclusion - it must never reach the
                 # owner queue labelled obvious.
                 and nobs > 1
                 and (r["keyed_end_tier"] or "").upper() in ("A", "B"))
        r["unambiguous"] = "Y" if unamb else ""
        # log-scaled money and observation count so one $3B firm does not bury
        # forty $10M ones; dataset presence is a small integer and used raw.
        score = (CLASS_STRENGTH.get(r["attachment_class"], 0.3)
                 * (math.log10(usd + 1) * 3.0
                    + nds * 2.0
                    + math.log10(nobs + 1) * 1.5
                    + (2.0 if unamb else 0.0)))
        r["priority_score"] = round(score, 3)
        r["priority_basis"] = ("class_strength x (3*log10(usd) + 2*n_datasets "
                               "+ 1.5*log10(n_observations) + 2 if unambiguous)")
    all_rows.sort(key=lambda r: (-r["priority_score"], r["unkeyed_uei"]))
    for i, r in enumerate(all_rows, 1):
        r["priority_rank"] = i
        r["rule_first"] = "Y" if i <= 50 else ""

    lead = ["priority_rank", "rule_first", "priority_score", "unambiguous"]
    fields = lead + [k for k in all_rows[0] if k not in lead] if all_rows else []
    write_csv(CAND_OUT, all_rows, fields)

    # --- firm-level rollup -------------------------------------------------
    byfirm = defaultdict(list)
    for r in all_rows:
        byfirm[r["unkeyed_uei"]].append(r)
    firm_rows = []
    for uu, rs in sorted(byfirm.items()):
        ents = sorted({r["keyed_tribe_id"] for r in rs})
        classes = sorted({r["attachment_class"] for r in rs})
        best = min(rs, key=lambda r: (int(r["hops_from_keyed_entity"]),
                                      -int(r.get("n_observations") or 0)))
        firm_rows.append({
            "unkeyed_uei": uu,
            "unkeyed_declared_name": best["unkeyed_declared_name"],
            "unkeyed_cage": best["unkeyed_cage"],
            "unkeyed_state": best["unkeyed_state"],
            "n_candidate_edges": len(rs),
            "n_distinct_keyed_entities": len(ents),
            "keyed_tribe_ids": "|".join(ents),
            "attachment_classes": "|".join(classes),
            "best_hops": best["hops_from_keyed_entity"],
            "max_observations": max(int(r.get("n_observations") or 0) for r in rs),
            "name_match_tribe_ids": best["name_match_tribe_ids"],
            "review_flags": best["review_flags"],
            "tier": TIER,
            "built_by": BUILT_BY,
            "built_date": BUILT_DATE,
        })
    firm_rows.sort(key=lambda r: (-r["max_observations"], r["unkeyed_uei"]))
    write_csv(FIRMS_OUT, firm_rows, list(firm_rows[0].keys()) if firm_rows else [])

    # --- identifier-backfill candidates ------------------------------------
    # deduplicate to one row per (uei, evidence_kind, paired entity), keeping
    # the most-observed declaration.
    bf = {}
    for b in backfill:
        k = (b["unkeyed_uei"], b["evidence_kind"], b["paired_keyed_tribe_id"])
        prev = bf.get(k)
        if prev is None or int(b["n_observations"] or 0) > int(prev["n_observations"] or 0):
            bf[k] = b
    backfill_rows = sorted(bf.values(),
                           key=lambda b: (-abs(b["usd_observed"]),
                                          -int(b["n_observations"] or 0)))
    for i, b in enumerate(backfill_rows, 1):
        b["priority_rank"] = i
    _bl = ["priority_rank"]
    write_csv(BACKFILL_OUT, backfill_rows,
              _bl + [k for k in backfill_rows[0] if k not in _bl]
              if backfill_rows else [])

    # --- suspect keyed anchors ---------------------------------------------
    arows = []
    for uei, kd in sorted(suspect_anchor.items()):
        arows.append({
            "keyed_uei": uei,
            "keyed_tribe_id": kd["entity_id"],
            "entity_canonical_name": spine_name.get(kd["entity_id"], ""),
            "ledger_legal_business_name": kd.get("legal_name", ""),
            "attribution_method": kd.get("method", ""),
            "tier": kd.get("tier", ""),
            "tier_rationale": kd.get("rationale", ""),
            "distinctive_tokens_in_legal_name":
                "|".join(sorted(distinctive(kd.get("legal_name") or ""))),
            "distinctive_tokens_in_entity_name":
                "|".join(sorted(entity_tokens.get(kd["entity_id"], set()))),
            "finding": ("no distinctive token in common: the link rests on "
                        "generic contracting vocabulary"),
            "action": ("rule on this identifier-to-entity link before any "
                       "declared edge is allowed to hang from it"),
            "found_by": BUILT_BY,
            "found_date": BUILT_DATE,
        })
    arows.sort(key=lambda r: (r["keyed_tribe_id"], r["keyed_uei"]))
    write_csv(ANCHOR_OUT, arows, list(arows[0].keys()) if arows else [])

    # --- decline ledger (I5) ----------------------------------------------
    n_accepted_edges = len(rows)
    total_declined = sum(declines.values())
    drows = [{"bucket": b, "n_edges": n, "why": decline_note[b]}
             for b, n in sorted(declines.items(), key=lambda kv: -kv[1])]
    drows.append({"bucket": "ACCEPTED_as_one_ended_ownership_candidates",
                  "n_edges": n_accepted_edges,
                  "why": "exactly one end keyed; emitted as tier-B candidates"})
    write_csv(DECL_OUT, drows, ["bucket", "n_edges", "why"])

    if n_accepted_edges + total_declined != n_source:
        print("FAIL I5: %d accepted + %d declined != %d source edges"
              % (n_accepted_edges, total_declined, n_source))
        return 1

    summary = {
        "source_edges": n_source,
        "accepted_one_ended_edges": n_accepted_edges,
        "declined_edges": total_declined,
        "declines": dict(declines),
        "candidate_rows": len(all_rows),
        "sibling_rows": len(sib_rows),
        "by_class": dict(Counter(r["attachment_class"] for r in all_rows)),
        "distinct_candidate_firms": len(byfirm),
        "entities_gaining_a_subsidiary": len({
            r["keyed_tribe_id"] for r in all_rows
            if r["attachment_class"] in ("subsidiary_of", "intermediate_holdco")
            and r["direction"].startswith("keyed_is_parent")}),
        "entities_gaining_a_parent": len({
            r["keyed_tribe_id"] for r in all_rows
            if r["direction"].startswith("keyed_is_child")}),
        "entities_touched": len({r["keyed_tribe_id"] for r in all_rows}),
        "identifier_backfill_candidates": len(backfill_rows),
        "identifier_backfill_distinct_ueis": len({b["unkeyed_uei"]
                                                  for b in backfill_rows}),
        "identifier_backfill_by_evidence": dict(Counter(
            b["evidence_kind"] for b in backfill_rows)),
        "identifier_backfill_disputed": sum(
            1 for b in backfill_rows if b["target_disputed"]),
        "suspect_keyed_anchors": len(arows),
        "suspect_keyed_anchor_entities": len({a["keyed_tribe_id"]
                                              for a in arows}),
        "keyed_uei_ledger": len(ledger_keyed),
        "keyed_uei_union_with_graph": len(keyed),
    }
    _merge_summary(summary)
    if not quiet:
        print("PHASE 1 - harvest")
        print("  source edges                        %6d" % n_source)
        for b, n in sorted(declines.items(), key=lambda kv: -kv[1]):
            print("  declined: %-52s %5d" % (b, n))
        print("  ACCEPTED one-ended ownership edges  %6d" % n_accepted_edges)
        print("  candidate rows (incl. %d sibling)   %6d"
              % (len(sib_rows), len(all_rows)))
        for c, n in sorted(summary["by_class"].items(), key=lambda kv: -kv[1]):
            print("      %-32s %5d" % (c, n))
        print("  distinct candidate firms            %6d" % len(byfirm))
        print("  Cedar entities touched              %6d" % summary["entities_touched"])
        print("  -> %s" % CAND_OUT)
        print("  -> %s" % FIRMS_OUT)
        print("  identifier-backfill candidates      %6d  (%d distinct UEIs, "
              "%d disputed)"
              % (len(backfill_rows), summary["identifier_backfill_distinct_ueis"],
                 summary["identifier_backfill_disputed"]))
        for k, v in sorted(summary["identifier_backfill_by_evidence"].items()):
            print("      %-52s %5d" % (k, v))
        print("  -> %s" % DECL_OUT)
        print("  suspect keyed anchors refused       %6d  (%d entities)"
              % (len(arows), summary["suspect_keyed_anchor_entities"]))
        print("  -> %s" % BACKFILL_OUT)
        print("  -> %s" % ANCHOR_OUT)
    return 0


# ---------------------------------------------------------------------------
# PHASE 2
# ---------------------------------------------------------------------------
def mine(quiet=False):
    nodes = read_csv(GNODES_IN)
    gedges = read_csv(GEDGES_IN)
    keyed_ent = {}
    for r in nodes:
        if (r.get("resolved_entity") or "").strip():
            keyed_ent[r["node"]] = r["resolved_entity"].strip()
    # THE GRAPH IS NOT THE ONLY KEYING SURFACE, and asking only the graph made
    # Q3's headline wrong: UEI:HZ8CHGL3B3S6 (ONEIDA NATION, $1.1B) ranked #2 on
    # the "carries no entity" queue while sitting in the identifier ledger
    # keyed to TRBF-ONDAWI-00 the whole time. A work queue that sends a
    # reviewer at work already done is worse than no queue.
    for r in read_csv(LEDGER_IN):
        _id = (r.get("identifier") or "").strip()
        _t = (r.get("tribe_id") or "").strip()
        if _id and _t:
            keyed_ent.setdefault("%s:%s" % (r.get("identifier_type"), _id), _t)
    nodeidx = {r["node"]: r for r in nodes}
    spine_name = {r["tribe_id"]: r.get("canonical_name", "")
                  for r in read_csv(SPINE_IN)}

    ident = [r for r in gedges if r.get("edge_kind") == "IDENTITY"]

    # ---- Q1: unkeyed identifiers co-occurring with keyed ones ------------
    nbr = defaultdict(set)
    ev = {}
    for r in ident:
        a, b = r["from_node"], r["to_node"]
        nbr[a].add(b)
        nbr[b].add(a)
        ev[(a, b)] = ev[(b, a)] = (r.get("method", ""), r.get("evidence", "")[:180],
                                   r.get("n_asserting_sources", ""), r.get("edge_tier", ""))
    q1 = []
    for n, links in nbr.items():
        if n in keyed_ent:
            continue
        hits = sorted({keyed_ent[l] for l in links if l in keyed_ent})
        if not hits:
            continue
        nd = nodeidx.get(n, {})
        best = sorted((l for l in links if l in keyed_ent),
                      key=lambda l: -int(ev[(n, l)][2] or 0))[0]
        m, e, ns, tr = ev[(n, best)]
        q1.append({
            "identifier_node": n,
            "identifier_type": nd.get("identifier_type", n.split(":")[0]),
            "observed_name": nd.get("observed_name", ""),
            "n_datasets": int(nd.get("n_datasets") or 0),
            "rows_observed": int(float(nd.get("rows_observed") or 0)),
            "usd_observed": float(nd.get("usd_observed") or 0),
            "n_keyed_cooccurring_entities": len(hits),
            "cooccurring_entity_ids": "|".join(hits),
            "cooccurring_entity_names": "|".join(spine_name.get(h, "") for h in hits),
            "strongest_link_node": best,
            "cooccurrence_method": m,
            "cooccurrence_evidence": e,
            "n_asserting_sources": ns,
            "link_tier": tr,
            "ambiguous": "Y" if len(hits) > 1 else "",
            "queue_rank_basis": "unambiguous first, then dollars then rows",
        })
    q1.sort(key=lambda r: (r["n_keyed_cooccurring_entities"] > 1,
                           -r["usd_observed"], -r["rows_observed"]))
    for i, r in enumerate(q1, 1):
        r["queue_rank"] = i
    write_csv(Q1_OUT, q1, ["queue_rank"] + [k for k in q1[0] if k != "queue_rank"]
              if q1 else [])

    # ---- Q2: names clustering to identifiers -----------------------------
    # (identifier, observed name) pairs from every surface that records one.
    name_ids = defaultdict(set)
    name_raw = defaultdict(set)

    def add(nm, node):
        n = norm_name(nm)
        if len(n) < 4:
            return
        name_ids[n].add(node)
        name_raw[n].add((nm or "").strip())

    for r in nodes:
        if r.get("observed_name"):
            add(r["observed_name"], r["node"])
    for r in read_csv(LEDGER_IN):
        node = "%s:%s" % (r.get("identifier_type"), (r.get("identifier") or "").strip())
        add(r.get("legal_business_name"), node)
        add(r.get("canonical_name"), node)
    for r in read_csv(CAGEMAP_IN):
        add(r.get("legal_business_name"), "UEI:%s" % (r.get("uei") or "").strip())
    for r in read_csv(EDGES_IN):
        add(r.get("child_name"), "UEI:%s" % (r.get("child_uei") or "").strip())
        add(r.get("parent_name"), "UEI:%s" % (r.get("parent_uei") or "").strip())

    q2 = []
    for n, ids in name_ids.items():
        if len(ids) < 2:
            continue
        ents = sorted({keyed_ent[i] for i in ids if i in keyed_ent})
        unkeyed = sorted(i for i in ids if i not in keyed_ent)
        risk = ("CONTAMINATION_RISK_one_name_two_entities" if len(ents) > 1
                else "ALIAS_MATERIAL_name_reaches_unkeyed_identifiers"
                if ents and unkeyed else "unkeyed_cluster_only")
        q2.append({
            "normalised_name": n,
            "observed_spellings": " || ".join(sorted(name_raw[n])[:6]),
            "n_identifiers": len(ids),
            "n_distinct_entities": len(ents),
            "entity_ids": "|".join(ents),
            "entity_names": "|".join(spine_name.get(e, "") for e in ents),
            "n_unkeyed_identifiers": len(unkeyed),
            "unkeyed_identifiers": "|".join(unkeyed[:12]),
            "verdict": risk,
            "action": ("REVIEW BEFORE ANY USE - a CAGE legal alias already "
                       "equated Delaware Tribe of Indians with Delaware "
                       "Nation, two distinct sovereigns. Never auto-apply."),
        })
    order = {"CONTAMINATION_RISK_one_name_two_entities": 0,
             "ALIAS_MATERIAL_name_reaches_unkeyed_identifiers": 1,
             "unkeyed_cluster_only": 2}
    q2.sort(key=lambda r: (order[r["verdict"]], -r["n_distinct_entities"],
                           -r["n_unkeyed_identifiers"], r["normalised_name"]))
    for i, r in enumerate(q2, 1):
        r["queue_rank"] = i
    write_csv(Q2_OUT, q2, ["queue_rank"] + [k for k in q2[0] if k != "queue_rank"]
              if q2 else [])

    # ---- Q3: present in many datasets, carrying no entity ----------------
    q3 = []
    for r in nodes:
        if r["node"] in keyed_ent:      # graph resolution OR ledger row
            continue
        if (r.get("blocked") or "").strip():
            continue
        nds = int(r.get("n_datasets") or 0)
        if nds < 1:
            continue
        q3.append({
            "identifier_node": r["node"],
            "identifier_type": r.get("identifier_type", ""),
            "observed_name": r.get("observed_name", ""),
            "n_datasets": nds,
            "datasets": r.get("datasets", ""),
            "rows_observed": int(float(r.get("rows_observed") or 0)),
            "usd_observed": float(r.get("usd_observed") or 0),
            "degree_in_identifier_graph": int(r.get("degree") or 0),
            "has_cooccurring_keyed_identifier":
                "Y" if any(l in keyed_ent for l in nbr.get(r["node"], ())) else "",
        })
    q3.sort(key=lambda r: (-r["n_datasets"], -r["usd_observed"], -r["rows_observed"]))
    for i, r in enumerate(q3, 1):
        r["queue_rank"] = i
    write_csv(Q3_OUT, q3, ["queue_rank"] + [k for k in q3[0] if k != "queue_rank"]
              if q3 else [])

    # ---- Q4: one entity, identifiers that never co-occur -----------------
    ent_nodes = defaultdict(set)
    for n, e in keyed_ent.items():
        ent_nodes[e].add(n)
    q4 = []
    for e, ns in ent_nodes.items():
        if len(ns) < 2:
            continue
        seen, comps = set(), []
        for s in sorted(ns):
            if s in seen:
                continue
            stack, comp = [s], set()
            while stack:
                x = stack.pop()
                if x in comp:
                    continue
                comp.add(x)
                for y in nbr.get(x, ()):
                    if y in ns and y not in comp:
                        stack.append(y)
            seen |= comp
            comps.append(sorted(comp))
        if len(comps) < 2:
            continue
        stems = []
        usd = []
        for c in comps:
            names = {norm_name(nodeidx.get(x, {}).get("observed_name", ""))
                     for x in c}
            names.discard("")
            stems.append(sorted(names)[:3])
            usd.append(sum(float(nodeidx.get(x, {}).get("usd_observed") or 0)
                           for x in c))
        heads = [set(s[0].split()[:2]) if s else set() for s in stems]
        overlap = any(a & b for i, a in enumerate(heads)
                      for b in heads[i + 1:])
        live = [u for u in usd if u > 0]
        q4.append({
            "entity_id": e,
            "entity_name": spine_name.get(e, ""),
            "n_identifiers": len(ns),
            "n_components_that_never_cooccur": len(comps),
            "component_sizes": "|".join(str(len(c)) for c in comps),
            "component_usd": "|".join("%.0f" % u for u in usd),
            "min_live_component_usd": min(live) if len(live) > 1 else 0.0,
            "component_name_stems": " || ".join(", ".join(s) for s in stems[:6]),
            "name_stems_overlap": "Y" if overlap else "",
            "verdict": ("EXPECTED_a_family_holds_many_unlinked_identifiers"
                        if overlap or len(live) < 2 else
                        "REVIEW_dollar_bearing_islands_with_no_shared_name"),
            "caveat": ("A tribe legitimately holds differently-named "
                       "subsidiaries, so this shape is NOT itself a defect. "
                       "The ranking says where a two-entities-merged-under-one-"
                       "uid error is most findable; it asserts none."),
            "sample_nodes": "|".join(c[0] for c in comps[:8]),
        })
    q4.sort(key=lambda r: (r["verdict"].startswith("EXPECTED"),
                           -r["min_live_component_usd"],
                           -r["n_components_that_never_cooccur"]))
    for i, r in enumerate(q4, 1):
        r["queue_rank"] = i
    write_csv(Q4_OUT, q4, ["queue_rank"] + [k for k in q4[0] if k != "queue_rank"]
              if q4 else [])

    summary = {
        "q1_unkeyed_identifiers_cooccurring_with_keyed": len(q1),
        "q1_unambiguous_single_entity": sum(1 for r in q1 if not r["ambiguous"]),
        "q2_name_clusters": len(q2),
        "q2_contamination_risk": sum(
            1 for r in q2 if r["verdict"].startswith("CONTAMINATION")),
        "q2_alias_material": sum(
            1 for r in q2 if r["verdict"].startswith("ALIAS")),
        "q3_unkeyed_with_dataset_presence": len(q3),
        "q3_in_2_or_more_datasets": sum(1 for r in q3 if r["n_datasets"] >= 2),
        "q3_usd_at_stake": round(sum(r["usd_observed"] for r in q3), 2),
        "q4_entities_with_noncooccurring_identifiers": len(q4),
        "q4_review_splits": sum(
            1 for r in q4 if r["verdict"].startswith("REVIEW")),
    }
    _merge_summary(summary)
    if not quiet:
        print("PHASE 2 - identifier graph")
        for k, v in summary.items():
            print("  %-52s %s" % (k, v))
        for p in (Q1_OUT, Q2_OUT, Q3_OUT, Q4_OUT):
            print("  -> %s" % p)
    return 0


def _merge_summary(d):
    cur = {}
    if os.path.exists(SUMMARY_OUT):
        try:
            cur = json.load(open(SUMMARY_OUT, encoding="utf-8"))
        except Exception:
            cur = {}
    cur.update(d)
    with open(SUMMARY_OUT, "w", encoding="utf-8") as f:
        json.dump(cur, f, indent=2, sort_keys=True)


# ---------------------------------------------------------------------------
# VERIFY - the five invariants
# ---------------------------------------------------------------------------
def verify(quiet=False):
    if not os.path.exists(CAND_OUT):
        print("FAIL: no candidate table; run `harvest` first")
        return 1
    cands = read_csv(CAND_OUT)
    src = read_csv(EDGES_IN)
    literal = {((r.get("child_uei") or "").strip().upper(),
                (r.get("parent_uei") or "").strip().upper(),
                (r.get("edge_type") or "").strip()) for r in src}
    keyed, _su, _sn = load_keying()
    fails = []

    bad = [r for r in cands if (r.get("tier") or "").strip().upper() != "B"]
    if bad:
        fails.append("I1 tier: %d candidate(s) not at tier B, first %s"
                     % (len(bad), bad[0]["candidate_id"]))

    bad = [r for r in cands
           if ((r["declared_child_uei"].strip().upper(),
                r["declared_parent_uei"].strip().upper(),
                r["declared_edge_type"].strip()) not in literal)]
    if bad:
        fails.append("I2 closure: %d candidate(s) cite a (child,parent,type) "
                     "triple that is not literally in fpds_uei_edges.csv, "
                     "first %s" % (len(bad), bad[0]["candidate_id"]))

    bad = [r for r in cands
           if r["declared_parent_uei"].strip().upper() in federal_rollup_ueis(src)]
    if bad:
        fails.append("I3 blocklist: %d candidate(s) propagate through a "
                     "GOVERNMENT OF THE UNITED STATES roll-up, first %s"
                     % (len(bad), bad[0]["candidate_id"]))

    bad = [r for r in cands
           if r["declared_edge_type"].strip() in NOT_OWNERSHIP_EDGE_TYPES]
    if bad:
        fails.append("I4 prime_to_sub: %d candidate(s) built on a subaward "
                     "edge, which is contracting and not ownership, first %s"
                     % (len(bad), bad[0]["candidate_id"]))

    if os.path.exists(DECL_OUT):
        d = read_csv(DECL_OUT)
        tot = sum(int(r["n_edges"]) for r in d)
        if tot != len(src):
            fails.append("I5 conservation: decline ledger sums to %d, source "
                         "has %d edges" % (tot, len(src)))
        unnamed = [r for r in d if not (r.get("bucket") or "").strip()
                   or not (r.get("why") or "").strip()]
        if unnamed:
            fails.append("I5 naming: %d decline bucket(s) with no name or no "
                         "reason" % len(unnamed))
    else:
        fails.append("I5: decline ledger missing")

    # an emitted candidate must not have BOTH ends keyed at hops 1
    bad = [r for r in cands
           if r["hops_from_keyed_entity"] == "1"
           and r["unkeyed_uei"].strip().upper() in keyed]
    if bad:
        fails.append("I0 one-endedness: %d hops-1 candidate(s) whose 'unkeyed' "
                     "end is in fact keyed, first %s"
                     % (len(bad), bad[0]["candidate_id"]))

    if fails:
        print("VERIFY FAILED (%d):" % len(fails))
        for f in fails:
            print("  !! " + f)
        return 1
    if not quiet:
        print("VERIFY OK - %d candidates; I1 tier-B, I2 no closure, "
              "I3 blocklist, I4 no prime_to_sub, I5 %d edges conserved"
              % (len(cands), len(src)))
    return 0


# ---------------------------------------------------------------------------
# FIXTURES - prove each invariant fires
# ---------------------------------------------------------------------------
def fixtures():
    if not os.path.exists(CAND_OUT):
        print("run `harvest` first")
        return 1
    backup = CAND_OUT + ".fixture_bak"
    dbackup = DECL_OUT + ".fixture_bak"
    shutil.copy2(CAND_OUT, backup)
    shutil.copy2(DECL_OUT, dbackup)
    results = []
    try:
        base = read_csv(CAND_OUT)
        fields = list(base[0].keys())

        def poison(mut, label):
            rows = [dict(r) for r in base]
            mut(rows)
            write_csv(CAND_OUT, rows, fields)
            rc = verify(quiet=True)
            results.append((label, rc))
            shutil.copy2(backup, CAND_OUT)

        def f1(rows):
            rows[0]["tier"] = "A"
        poison(f1, "I1 a candidate emitted at tier A")

        def f2(rows):
            rows[0]["declared_child_uei"] = "ZZZZZZZZZZZZ"
        poison(f2, "I2 a candidate citing an edge that is not in the source")

        def f3(rows):
            rows[0]["declared_parent_uei"] = "NW2RJN8TQQW1"
        poison(f3, "I3 a candidate inheriting through the federal roll-up")

        def f4(rows):
            rows[0]["declared_edge_type"] = "prime_to_sub"
        poison(f4, "I4 a candidate built on a prime-to-sub edge")

        # I5 lives in the decline ledger
        d = read_csv(DECL_OUT)
        dd = [dict(r) for r in d]
        dd[0]["n_edges"] = str(int(dd[0]["n_edges"]) - 1)
        write_csv(DECL_OUT, dd, list(d[0].keys()))
        results.append(("I5 a decline ledger that loses an edge", verify(quiet=True)))
        shutil.copy2(dbackup, DECL_OUT)

        dd = [dict(r) for r in d]
        dd[0]["bucket"] = ""
        write_csv(DECL_OUT, dd, list(d[0].keys()))
        results.append(("I5 an UNNAMED decline bucket", verify(quiet=True)))
        shutil.copy2(dbackup, DECL_OUT)

        def f0(rows):
            k = next(iter(load_keying()[0]))
            rows[0]["unkeyed_uei"] = k
            rows[0]["hops_from_keyed_entity"] = "1"
        poison(f0, "I0 a hops-1 candidate whose unkeyed end is keyed")
    finally:
        shutil.copy2(backup, CAND_OUT)
        shutil.copy2(dbackup, DECL_OUT)
        os.remove(backup)
        os.remove(dbackup)

    clean = verify(quiet=True)
    ok = all(rc == 1 for _l, rc in results) and clean == 0
    print("FIXTURES")
    for l, rc in results:
        print("  %-58s injected -> exit %d  %s"
              % (l, rc, "PASS" if rc == 1 else "FAIL (should have caught it)"))
    print("  %-58s restored -> exit %d  %s"
          % ("clean state", clean, "PASS" if clean == 0 else "FAIL"))
    return 0 if ok else 1


# ---------------------------------------------------------------------------
# VALIDATE - deterministic random sample for hand checking
# ---------------------------------------------------------------------------
def validate(n=20, seed=20260901):
    # Spine names carry diacritics (Ukpeagvik Inupiat's U+0121 among them) and
    # a Windows console is cp1252. Printing must never be the thing that fails
    # a validation run.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    cands = read_csv(CAND_OUT)
    rnd = random.Random(seed)
    samp = rnd.sample(cands, min(n, len(cands)))
    spine = {r["tribe_id"]: r for r in read_csv(SPINE_IN)}
    src = read_csv(EDGES_IN)
    idx = defaultdict(list)
    for r in src:
        idx[((r.get("child_uei") or "").strip().upper(),
             (r.get("parent_uei") or "").strip().upper())].append(r)
    out = []
    for i, c in enumerate(samp, 1):
        e = spine.get(c["keyed_tribe_id"], {})
        srcrows = idx[(c["declared_child_uei"].strip().upper(),
                       c["declared_parent_uei"].strip().upper())]
        out.append({
            "n": i,
            "candidate_id": c["candidate_id"],
            "attachment_class": c["attachment_class"],
            "direction": c["direction"],
            "keyed_tribe_id": c["keyed_tribe_id"],
            "spine_canonical_name": e.get("canonical_name", "ENTITY NOT IN SPINE"),
            "spine_entity_class": e.get("entity_class", ""),
            "spine_state": e.get("state", ""),
            "keyed_uei": c["keyed_uei"],
            "keyed_end_tier": c["keyed_end_tier"],
            "keyed_end_source": c["keyed_end_source"],
            "unkeyed_uei": c["unkeyed_uei"],
            "unkeyed_declared_name": c["unkeyed_declared_name"],
            "unkeyed_state": c["unkeyed_state"],
            "declared_edge": "%s (%s) -> %s (%s) [%s]" % (
                c["declared_child_name"], c["declared_child_uei"],
                c["declared_parent_name"], c["declared_parent_uei"],
                c["declared_edge_type"]),
            "source_edge_rows_found": len(srcrows),
            "n_observations": c["n_observations"],
            "years": "%s-%s" % (c["first_year"], c["last_year"]),
            "review_flags": c["review_flags"],
            "hand_verdict": "",
            "hand_note": "",
        })
    write_csv(SAMPLE_OUT, out, list(out[0].keys()) if out else [])
    print("VALIDATION SAMPLE n=%d seed=%d -> %s" % (len(out), seed, SAMPLE_OUT))
    for r in out:
        print("\n[%02d] %s  class=%s" % (r["n"], r["candidate_id"], r["attachment_class"]))
        print("     keyed  : %s = %s (%s, %s) tier %s via %s"
              % (r["keyed_tribe_id"], r["spine_canonical_name"],
                 r["spine_entity_class"], r["spine_state"],
                 r["keyed_end_tier"], r["keyed_end_source"]))
        print("     unkeyed: %s  %s  [%s]"
              % (r["unkeyed_uei"], r["unkeyed_declared_name"], r["unkeyed_state"]))
        print("     edge   : %s  n_obs=%s %s  (source rows %d)"
              % (r["declared_edge"], r["n_observations"], r["years"],
                 r["source_edge_rows_found"]))
        if r["review_flags"]:
            print("     flags  : %s" % r["review_flags"])
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["harvest", "mine", "verify",
                                        "fixtures", "validate", "all"])
    ap.add_argument("--sample", type=int, default=20)
    ap.add_argument("--seed", type=int, default=20260901)
    a = ap.parse_args()
    os.makedirs(REVIEW, exist_ok=True)
    if a.command == "harvest":
        return harvest()
    if a.command == "mine":
        return mine()
    if a.command == "verify":
        return verify()
    if a.command == "fixtures":
        return fixtures()
    if a.command == "validate":
        return validate(a.sample, a.seed)
    rc = harvest()
    if rc:
        return rc
    rc = mine()
    if rc:
        return rc
    return verify()


if __name__ == "__main__":
    sys.exit(main())
