#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
851 - build the ADR-014 constellation `serves` edge layer.

WHY THIS EXISTS
---------------
`record_scope = native_serving` is declared in ADR-010 and used by ZERO rows,
while 8,138 rows across `data/clean/` sit in `record_scope = unresolved`
(measured here, not quoted: 5,561 nonprofit_schedule_c_lobbying + 2,389
native_owned_businesses + 80 gaming_property_self_published_claims + 59
gaming_property_self_published_assertions + 44 nigc_enforcement_actions + 4
nigc_indian_lands_opinions + 1 nigc_management_contract_approvals).
"native-serving" as a CATEGORY says only *we could not tie this to anyone*.
ADR-014 makes affiliation an EDGE with an evidence tier, so a row can read
"serves the Navajo Nation, tier `managed_under_contract`" - specific,
checkable, refutable.

WHAT THIS SCRIPT MEASURED, AND WHY EACH TIER IS WHERE IT IS
-----------------------------------------------------------
Every number below was measured by this script on 2026-09-01, from files
already on disk before it ran (the only network call in the whole build was
the Census TIGER 2024 AIANNH shapefile, 9,149,754 bytes, saved to
`data/raw/external/tiger/tl_2024_us_aiannh.zip`; nothing else was fetched).

* `chartered_by` - the sentence in which a nation charters the institution.
  Source: `data/staging/institution_registry/served_entity_crosswalk.csv`,
  evidence_route = `charter_sentence` (26 rows on disk, all match_confidence
  = high). These are the strongest edges in the file: "BMCC was chartered by
  the Bay Mills Indian Community in 1984" is not an inference.

* `managed_under_contract` - the BIE schools directory publishes
  `Operation_Type`, and the two values are the legal instrument itself:
  `Tribally-Controlled` (129 of 187 schools) means a tribe or tribal school
  board runs the school under a P.L. 100-297 grant or a P.L. 93-638 (ISDEAA)
  contract; `Bureau-Operated` (58) means the federal government runs it. That
  is exactly ADR-014's "a tribe operating a facility it does not own".
  A tribally-controlled school only gets this tier when the HUB is
  independently identified - by the directory's own `Navajo_Operation` field,
  or by the school's official name resolving to exactly one Cedar hub with
  state agreement. Operation type alone names no nation and cannot carry an
  edge.

* `registered_with` - **NOT AN ADR-014 TIER. PROPOSED AMENDMENT.** See the
  section "WHERE ADR-014 IS WRONG" below. 2,240 of the 2,389 unresolved rows
  in `native_owned_businesses.csv` carry a populated
  `certifying_authority_entity_id`: the nation's OWN published TERO registry,
  business-licence report, or Indian-preference vendor list names the
  business. That is a sovereign instrument naming the entity, and none of
  ADR-014's five tiers describes it.

* `declares_service_to` - the entity's own words. Two routes: the official
  NAME the institution chose for itself resolving to exactly one hub with
  state agreement (TCU / Native CDFI / Native financial institution), and IRS
  Form 990 mission text naming a nation next to a governmental word.
  The 990 route is deliberately tiny and that is the finding, not a failure:
  of the 3,745 distinct EINs behind the 5,561 unresolved Schedule C rows,
  2,389 have inclusion_basis `placename_only` and 848 `no_native_signal` -
  they are term-match FALSE POSITIVES (PENOBSCOT BAY YMCA is a bay), not
  Native organisations Cedar failed to key.

* `located_within` - a real geocode, not an assertion. The BIE directory
  carries Latitude/Longitude on 187 of 187 schools; point-in-polygon against
  the 864 Census AIANNH areas puts 165 inside one. The geography vetoes
  itself in a way that is worth recording: Chemawa, Flandreau, Haskell,
  Sherman, SIPI and Santa Fe Indian School - the national off-reservation
  boarding schools, whose names LOOK tribal - all land outside every AIANNH
  polygon. A name matcher would have mis-assigned Flandreau Indian School to
  the Flandreau Santee Sioux Tribe; the polygon refuses it.

* `sole_entity_in_area` - computed, never load-bearing. See rule 2 below.

THE THREE FENCES, IN CODE
-------------------------
1. A `serves` edge is NEVER an ownership claim and money NEVER rolls through
   it. `assert_no_money_columns()` fails the build if any column name in the
   output could hold a dollar figure, and every row carries
   `money_rolls_through = N`. IHS hospital obligations do not become tribal
   revenue because a tribe manages the hospital. Mirrored in
   `docs/MONEY_TOTALLING_RULES.md` between the CONSTELLATION markers.
2. `sole_entity_in_area` may NEVER be the only evidence on an edge.
   `check_sole_entity_never_alone()` fails the build. `verify` mode ALSO
   feeds the checker a synthetic violating row and fails if the checker does
   not fire - a check that cannot fail is not a check.
3. Zero fabrication, flag never delete. Every edge carries
   `evidence_source` + `evidence_excerpt`, both non-empty, enforced. Every
   candidate that did not clear a rung is written to
   `data/clean/cedar_constellation_refusals.csv` with the reason, not
   dropped.

RULE 7 (ENTITY_MATCH_RULES) IS THE ARBITER OF NAME-VS-GEOGRAPHY
---------------------------------------------------------------
Geography is a ladder, not a gate, and the record's own words are the veto.
Implemented two ways. (a) A name-based hub match is REFUSED, not reconciled,
when the resolved hub's state disagrees and the name is not nationally
unique. (b) Where an entity gets both a self-declared edge and a geographic
edge to DIFFERENT hubs, both are written - ADR-014 makes `serves`
many-to-many on purpose - but the geographic one is stamped
`geography_selfdeclaration_conflict = Y` and the self-declared one wins on
tier rank. Forcing such a case onto one attribution is the error the
catch-all was invented to avoid.

WHERE ADR-014 IS WRONG, ON THE EVIDENCE OF BUILDING IT
------------------------------------------------------
A. The ladder has no rung for "the NATION's own instrument names the
   entity". Four of five tiers are evidenced by the entity (its charter, its
   contract, its words) or by a polygon. But the largest evidenced pool in
   the whole unresolved backlog - 2,240 rows - is the opposite direction: a
   tribe's TERO office, licence report or Indian-preference vendor list
   publishing the entity's name. `chartered_by`'s stated BASIS ("the
   instrument names the nation") does cover it, but its NAME does not, and
   ADR-014 says "nothing is promoted a tier by resemblance". So this build
   writes them as `registered_with`, ranked 3, and flags every one. Rename
   or delete them with a single filter on `tier`; the headline is reported
   both ways.
B. The edge presumes the `from` side already has a `cedar_uid`. It does not.
   The 8,138 unresolved rows are unresolved precisely BECAUSE no entity was
   established for them. 2,240 TERO businesses are not spine entities and
   minting them is not this script's call. So `from_cedar_uid` is left blank
   on those rows and `from_record_key` + `from_source_table` carry the join
   back to the source row, with `from_is_spine_entity = N`. An edge layer
   that can only speak about entities that already exist cannot, by
   construction, resolve the pile of records that have no entity.
C. `sole_entity_in_area` as written is unreachable from Cedar's data. It
   needs a Native-entity census per geography; what exists is a 303-row
   gaming-compact crosswalk. It is computed here from AIANNH polygons that
   resolve to exactly one Cedar hub, used ONLY as corroboration, and it
   should probably be demoted from "tier" to "corroborator" in the ADR.

SUPERSEDED AS THE BUILD ENTRYPOINT, 2026-09-02
-----------------------------------------------
`code/852_extend_constellation_edges.py` now builds the shipped file. It
imports this module and runs every source function here unchanged, then adds
four more (IHS Title V compacts, published membership rosters, the full AIHEC
charter profiles, and the certifying-authority NAME this script refused when
the ID column was blank) and adjudicates the Blackwater conflict. Running 851
alone still works and still passes, but it writes a SMALLER file - it does not
know about 852's sources. Run 852.

USAGE
    py -3 code/852_extend_constellation_edges.py           # build (use this)
    py -3 code/851_build_constellation_edges.py            # 851's slice only
    py -3 code/851_build_constellation_edges.py verify     # invariants only
Exits 1 when an invariant is broken.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict

BUILT_DATE = "2026-09-01"
SCRIPT = "code/851_build_constellation_edges.py"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EDGES_OUT = os.path.join(ROOT, "data", "clean", "cedar_constellation_edges.csv")
REFUSALS_OUT = os.path.join(ROOT, "data", "clean", "cedar_constellation_refusals.csv")

SPINE = os.path.join(ROOT, "data", "spine", "cedar_entity_spine.csv")
SLICE = os.path.join(ROOT, "data", "staging", "institution_registry", "_slice.csv")
SERVED = os.path.join(ROOT, "data", "staging", "institution_registry",
                      "served_entity_crosswalk.csv")
BIE_JSON = os.path.join(ROOT, "data", "raw", "external", "bie_uio",
                        "bie_schools_featureserver.json")
AIANNH_ZIP = os.path.join(ROOT, "data", "raw", "external", "tiger",
                          "tl_2024_us_aiannh.zip")
AIANNH_XWALK = os.path.join(ROOT, "data", "raw", "external", "compacts",
                            "prior_extractions", "tribe_aiannh_crosswalk_master.csv")
NOB = os.path.join(ROOT, "data", "clean", "native_owned_businesses.csv")
SCHEDC = os.path.join(ROOT, "data", "clean", "nonprofit_schedule_c_lobbying.csv")
MISSION = os.path.join(ROOT, "data", "staging", "np_mission", "mission_text.jsonl")
NP_ORGS = os.path.join(ROOT, "data", "clean", "np_orgs.csv")

# ---------------------------------------------------------------- tiers

# ADR-014's five, strongest first. `tier_rank` is written on every row so a
# consumer can pick the strongest edge without re-deriving the ladder.
ADR014_TIERS = {
    "chartered_by": 1,
    "managed_under_contract": 2,
    # ADOPTED 2026-09-02 by ADR-014 Amendment 1 (docs/ARCHITECTURE_DECISIONS.md,
    # between the ADR-014 markers), on the proposal this script made below
    # under "WHERE ADR-014 IS WRONG" (A). It ranks 3 - below a federal 638 /
    # self-governance instrument, above the entity's own account of itself,
    # because the sovereign's own office is the one body that can say who is
    # certified with it. Rows carrying it now stamp `tier_is_adr014 = Y`.
    "registered_with": 3,
    "declares_service_to": 4,
    "located_within": 5,
    "sole_entity_in_area": 6,
}
# Empty since the amendment landed. Kept, not deleted: the next tier that
# arrives from implementation rather than design goes here first and is
# flagged `tier_is_adr014 = N` until it is argued into the ADR, which is the
# mechanism that got `registered_with` adopted instead of smuggled.
EXTENSION_TIERS = {}
TIER_RANK = dict(ADR014_TIERS)
TIER_RANK.update(EXTENSION_TIERS)

# The one tier ADR-014 forbids from standing alone.
NEVER_ALONE = "sole_entity_in_area"

# Classes that can be the HUB of a constellation: a government or an ANCSA
# corporation. Derived from the data - these are the classes that actually
# appear as `certifying_authority_entity_id` in native_owned_businesses and
# as `parent_entity_id` in the spine, plus the recognised-government classes.
HUB_CLASSES = {
    "Federally recognized tribe",
    "Federally recognized Alaska Native Village",
    "State-recognized tribe",
    "Alaska Native Regional Corporation",
    "Alaska Native Village Corporation",
    "ANCSA Group Corporation",
}

EDGE_COLUMNS = [
    "edge_id",
    "from_cedar_uid",
    "from_name",
    "from_entity_class",
    "from_state",
    "from_is_spine_entity",
    "from_record_key",
    "from_source_table",
    "to_hub_cedar_uid",
    "to_hub_name",
    "to_hub_entity_class",
    "to_hub_state",
    "tier",
    "tier_rank",
    "tier_is_adr014",
    "evidence_basis",
    "evidence_source",
    "evidence_excerpt",
    "hub_resolution_route",
    "corroborating_tiers",
    "geography_selfdeclaration_conflict",
    "state_agreement",
    "converts_unresolved_row",
    "is_ownership_claim",
    "money_rolls_through",
    "asserted_date",
    "built_by_script",
]

REFUSAL_COLUMNS = [
    "refusal_id",
    "from_name",
    "from_cedar_uid",
    "from_record_key",
    "from_source_table",
    "candidate_hub_name",
    "candidate_hub_cedar_uid",
    "attempted_tier",
    "refusal_reason",
    "refusal_detail",
    "evidence_source",
    "was_unresolved_row",
    "asserted_date",
    "built_by_script",
]

# A column whose name matches this may never appear in the edge file. Rule 1
# is not a comment; it is the absence of a place to put a dollar.
MONEY_RE = re.compile(
    r"(usd|dollar|amount|amt|revenue|obligation|outlay|spend|award|value|cost|"
    r"payment|funding|budget|total)", re.I)

# ---------------------------------------------------------------- text

GOV_WORDS = set(
    "nation nations tribe tribes tribal band bands pueblo village community "
    "rancheria colony indian indians reservation nsn council of the and off "
    "trust land".split())
# Single tokens too generic to award a hub on their own.
GENERIC_TOKENS = set(
    "north south east west upper lower new fort saint st lake river valley "
    "mountain creek grand little big old town city county bay island point "
    "springs falls hill park center central white black red green blue "
    # Measured, not guessed: on the first run the single-token core `native`
    # resolved - via an alias of a Cedar hub whose canonical name is
    # `Council` - and swept up ten unrelated national organisations
    # (ASSOCIATION ON AMERICAN INDIAN AFFAIRS, AMERICAN INDIAN CANCER
    # FOUNDATION, INDIAN LAND TENURE FOUNDATION ...). A pan-Indian word can
    # never award a specific nation.
    "native american alaska indian indians council association corporation "
    "village people nations".split())
STATE_WORDS = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine",
    "maryland", "massachusetts", "michigan", "minnesota", "mississippi",
    "missouri", "montana", "nebraska", "nevada", "hampshire", "jersey",
    "mexico", "york", "carolina", "dakota", "ohio", "oklahoma", "oregon",
    "pennsylvania", "rhode", "island", "tennessee", "texas", "utah", "vermont",
    "virginia", "washington", "wisconsin", "wyoming",
}
STATE_ABBR = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT",
    "Delaware": "DE", "Florida": "FL", "Georgia": "GA", "Hawaii": "HI",
    "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA",
    "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME",
    "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI",
    "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT",
    "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH",
    "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH",
    "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA",
    "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
    "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY",
}

CHARTER_VERBS = re.compile(
    r"\b(charter(?:ed|s)?|founded|established|created|organi[sz]ed|"
    r"incorporated by)\b", re.I)
SERVICE_VERBS = re.compile(
    r"\b(serve[sd]?|serving|for the (?:members|people|citizens|community)|"
    r"members of|on behalf of|benefit(?:ing|s)? the)\b", re.I)

# The 990 predicates, curated after reading all 59 candidate windows the
# first run produced. Only 7 cleared the generic SERVICE_VERBS regex, and the
# misses were not marginal: "provides wellness and diabetes programs TO the
# Alamo Navajo Reservation" and "to enhance the WELL BEING OF the Houlton
# Band" are declarations of service in anyone's reading. The three groups
# below are kept separate because they license different claims, and the
# group that fired is written into `evidence_basis`, so a reviewer can
# re-judge one class at a time instead of the whole route.
SERVE_PRED = re.compile(
    r"\b(serve[sd]?|serving|provid(?:e|es|ing)[^.]{0,60}?\b(?:to|for)\b|"
    r"programs?[^.]{0,40}?\b(?:for|to|throughout|across)\b|"
    r"members of|citizens of|residents of|children of|youth of|families of|"
    r"elders of|students of|well[- ]?being of|quality of life for|"
    r"strengthen|revitali[sz]|on behalf of|benefit(?:ing|s)? the|"
    r"loans? to|assistance to|services? (?:to|for))\b", re.I)
# The entity's own filing placing itself on the nation's land. These are the
# entity's WORDS, not a geocode, so they stay at `declares_service_to` and are
# never labelled `located_within`.
LOC_PRED = re.compile(
    r"\b(located (?:on|in|within)|based (?:on|in)|situated (?:on|in)|"
    r"campus (?:on|in)|(?:on|near) (?:and near )?the)\b", re.I)
# Anything else is a MENTION, not a declaration - "events such as the Miami
# Tribe", "45 miles from the San Carlos Reservation" - and is refused.


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())).strip()


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def mkid(prefix, *parts):
    """Deterministic, content-addressed, NON-POSITIONAL key (lint class 7)."""
    h = hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()
    return "%s-%s" % (prefix, h[:12].upper())


def excerpt(s, n=400):
    s = re.sub(r"\s+", " ", (s or "").strip())
    return s[:n]


# ---------------------------------------------------------------- hub index

class HubIndex(object):
    """Distinctive-core index over hub-class spine entities.

    ENTITY_MATCH_RULES step 1: compute the distinctive token set - the name
    minus generic and organisational words. An empty core cannot support a
    name-only match, so it is not indexed at all.

    Two things this index learned the hard way on this build.

    PREFIXES ARE INDEXED, not only the whole core. A Federal Register name is
    `<distinctive name> <governmental suffix> of the <place>, <state>`, so
    "White Mountain Apache Tribe of the Fort Apache Reservation, Arizona"
    reduces to the core `white mountain apache fort` - and the string a
    filing actually prints, "the White Mountain Apache Tribe", matched none
    of it. The first run therefore fell through to the one-token core
    `apache` and attributed FORT APACHE HERITAGE FOUNDATION (Arizona) to the
    **Apache Tribe of Oklahoma**. Indexing every leading prefix of the core
    lets the longest, right answer win before a bare token is ever reached.

    A HUB HAS A SET OF STATES, not one. `state` on the spine is a single
    value, but the FR official name spells the rest out - "Navajo Nation,
    Arizona, New Mexico & Utah" - and a single-state gate refused true
    matches for every reservation that spans a line.
    """

    def __init__(self, spine):
        self.hubs = {r["cedar_uid"]: r for r in spine
                     if r["entity_class"] in HUB_CLASSES and r["cedar_uid"]}
        self.core2uid = defaultdict(set)
        self.states = defaultdict(set)
        word2abbr = {k.split()[-1].lower(): v for k, v in STATE_ABBR.items()}
        word2abbr.update({k.lower(): v for k, v in STATE_ABBR.items()})
        for uid, r in self.hubs.items():
            if r.get("state"):
                self.states[uid].add(r["state"])
            names = [r.get("canonical_name"), r.get("fr_official_name")]
            names += (r.get("aliases") or "").split("|")
            for f in names:
                n = norm(f)
                if not n:
                    continue
                for w in n.split():
                    if w in STATE_WORDS and w in word2abbr:
                        self.states[uid].add(word2abbr[w])
                toks = [t for t in n.split()
                        if t not in GOV_WORDS and t not in STATE_WORDS]
                if not toks:
                    continue
                for L in range(1, len(toks) + 1):
                    core = " ".join(toks[:L])
                    if len(core) < 4:
                        continue
                    if L == 1 and (toks[0] in GENERIC_TOKENS or len(toks[0]) < 5):
                        continue
                    self.core2uid[core].add(uid)

    def state_ok(self, uid, state):
        """Blank state cannot agree or disagree; say so rather than guessing."""
        if not state:
            return None
        return state in self.states.get(uid, set())

    def resolve(self, text, state, allow_national_unique=False):
        """Return (uid, route). Route names the rung that fired, or the refusal.

        Rung order, longest core first so `crow creek` beats `crow`:
          unique_and_state_agrees  - one hub nationally AND its state matches
          unique_within_state      - several hubs share the core, one is in state
          unique_nationally        - one hub nationally, state disagrees. Only
                                     offered when the caller passes
                                     allow_national_unique=True, which the
                                     GEOCODED route does and the NAME route
                                     does not: a reservation legitimately
                                     spans states (Navajo AZ/NM/UT), a name
                                     coincidence does not get that excuse.
          REFUSED_state_mismatch / REFUSED_ambiguous / no_match
        """
        n = norm(text)
        toks = n.split()
        if not toks:
            return None, "no_match"
        for L in range(min(6, len(toks)), 0, -1):
            for i in range(len(toks) - L + 1):
                core = " ".join(toks[i:i + L])
                if core not in self.core2uid:
                    continue
                uids = self.core2uid[core]
                in_state = [u for u in uids if self.hubs[u].get("state") == state]
                if len(uids) == 1:
                    only = next(iter(uids))
                    if self.hubs[only].get("state") == state:
                        return only, "unique_and_state_agrees"
                    if allow_national_unique:
                        return only, "unique_nationally"
                    return None, "REFUSED_state_mismatch"
                if len(in_state) == 1:
                    return in_state[0], "unique_within_state"
                return None, "REFUSED_ambiguous"
        return None, "no_match"


# ---------------------------------------------------------------- builder

class Build(object):

    def __init__(self):
        self.edges = []
        self.refusals = []
        self.notes = []

    def edge(self, from_name, hub_uid, tier, evidence_basis, evidence_source,
             evidence_excerpt, hub_resolution_route, hubs,
             from_cedar_uid="", from_entity_class="", from_state="",
             from_record_key="", from_source_table="",
             corroborating_tiers="", conflict="N", converts_unresolved="N"):
        hub = hubs[hub_uid]
        eid = mkid("CONST", from_source_table, from_record_key or from_cedar_uid,
                   from_name, hub_uid, tier, evidence_basis)
        hub_state = hub.get("state") or ""
        self.edges.append({
            "edge_id": eid,
            "from_cedar_uid": from_cedar_uid,
            "from_name": from_name,
            "from_entity_class": from_entity_class,
            "from_state": from_state,
            "from_is_spine_entity": "Y" if from_cedar_uid else "N",
            "from_record_key": from_record_key,
            "from_source_table": from_source_table,
            "to_hub_cedar_uid": hub_uid,
            "to_hub_name": hub.get("canonical_name") or "",
            "to_hub_entity_class": hub.get("entity_class") or "",
            "to_hub_state": hub_state,
            "tier": tier,
            "tier_rank": TIER_RANK[tier],
            "tier_is_adr014": "Y" if tier in ADR014_TIERS else "N",
            "evidence_basis": evidence_basis,
            "evidence_source": evidence_source,
            "evidence_excerpt": excerpt(evidence_excerpt),
            "hub_resolution_route": hub_resolution_route,
            "corroborating_tiers": corroborating_tiers,
            "geography_selfdeclaration_conflict": conflict,
            "state_agreement": ("Y" if from_state and hub_state == from_state
                                else ("N" if from_state and hub_state else "")),
            "converts_unresolved_row": converts_unresolved,
            # Rule 1, on every single row, in the data and not only in prose.
            "is_ownership_claim": "N",
            "money_rolls_through": "N",
            "asserted_date": BUILT_DATE,
            "built_by_script": SCRIPT,
        })

    def refuse(self, from_name, reason, detail, source, attempted_tier="",
               from_cedar_uid="", from_record_key="", from_source_table="",
               cand_name="", cand_uid="", was_unresolved="N"):
        self.refusals.append({
            "refusal_id": mkid("CREF", from_source_table,
                               from_record_key or from_cedar_uid, from_name,
                               reason, cand_uid),
            "from_name": from_name,
            "from_cedar_uid": from_cedar_uid,
            "from_record_key": from_record_key,
            "from_source_table": from_source_table,
            "candidate_hub_name": cand_name,
            "candidate_hub_cedar_uid": cand_uid,
            "attempted_tier": attempted_tier,
            "refusal_reason": reason,
            "refusal_detail": detail,
            "evidence_source": source,
            "was_unresolved_row": was_unresolved,
            "asserted_date": BUILT_DATE,
            "built_by_script": SCRIPT,
        })


# ---------------------------------------------------------------- sources

def src_charter_sentences(b, hubs, idx):
    """`chartered_by` - the nation's chartering sentence, quoted."""
    if not os.path.exists(SERVED):
        b.notes.append("served_entity_crosswalk.csv ABSENT - chartered_by skipped")
        return
    seen = set()
    for r in read_csv(SERVED):
        if r["evidence_route"] != "charter_sentence":
            continue
        uid = r["candidate_cedar_uid"]
        quote = r["source_quote"]
        if not uid or uid not in hubs:
            b.refuse(r["canonical_name"], "hub_not_in_hub_class",
                     "candidate %r is absent from the hub-class spine" % uid,
                     r["source_url"], "chartered_by",
                     from_cedar_uid=r["cedar_uid"],
                     from_source_table="institution_registry/served_entity_crosswalk")
            continue
        if not CHARTER_VERBS.search(quote or ""):
            b.refuse(r["canonical_name"], "no_chartering_verb_in_quote",
                     "route says charter_sentence but the quoted sentence "
                     "carries no chartering/founding verb",
                     r["source_url"], "chartered_by",
                     from_cedar_uid=r["cedar_uid"], cand_uid=uid,
                     cand_name=r["candidate_canonical_name"],
                     from_source_table="institution_registry/served_entity_crosswalk")
            continue
        key = (r["cedar_uid"], uid)
        if key in seen:
            continue
        seen.add(key)
        b.edge(r["canonical_name"], uid, "chartered_by",
               "charter_or_founding_sentence_names_the_nation",
               r["source_url"] or "institution_registry/served_entity_crosswalk.csv",
               quote, "quoted_instrument", hubs,
               from_cedar_uid=r["cedar_uid"],
               from_entity_class=r["entity_class"],
               from_source_table="institution_registry/served_entity_crosswalk")


def src_spine_serves_text(b, hubs, idx, spine):
    """Spine `serves_native_entities` free text - chartered_by or declares."""
    for r in spine:
        txt = (r.get("serves_native_entities") or "").strip()
        if not txt or txt in ("0", "1"):
            continue
        if r["entity_class"] in HUB_CLASSES:
            continue
        state = r.get("state") or ""
        # Urban Indian Organizations say, in this very field, that they have
        # no single tribal hub. Refusing them is the honest outcome; ADR-014
        # is many-to-many but the text names no nation to be many OF.
        if "no single tribal owner" in txt:
            b.refuse(r["canonical_name"], "entity_declares_no_single_hub",
                     excerpt(txt, 200), r.get("entity_source_url") or SPINE,
                     "declares_service_to", from_cedar_uid=r["cedar_uid"],
                     from_source_table="spine/cedar_entity_spine")
            continue
        uid, route = idx.resolve(txt, state)
        if not uid:
            b.refuse(r["canonical_name"], route,
                     "serves_native_entities text did not resolve to one hub",
                     SPINE, "declares_service_to",
                     from_cedar_uid=r["cedar_uid"],
                     from_source_table="spine/cedar_entity_spine")
            continue
        if CHARTER_VERBS.search(txt):
            tier, basis = ("chartered_by",
                           "self_published_history_states_the_nation_chartered_it")
        elif SERVICE_VERBS.search(txt):
            tier, basis = ("declares_service_to",
                           "entitys_own_published_statement_of_who_it_serves")
        else:
            b.refuse(r["canonical_name"], "no_charter_or_service_verb",
                     excerpt(txt, 200), SPINE, "declares_service_to",
                     from_cedar_uid=r["cedar_uid"], cand_uid=uid,
                     from_source_table="spine/cedar_entity_spine")
            continue
        b.edge(r["canonical_name"], uid, tier, basis,
               r.get("entity_source_url") or SPINE, txt, route, hubs,
               from_cedar_uid=r["cedar_uid"], from_entity_class=r["entity_class"],
               from_state=state, from_source_table="spine/cedar_entity_spine")


def src_institution_names(b, hubs, idx):
    """`declares_service_to` from the official NAME a non-BIE institution chose.

    Restricted to Tribal Colleges, Native CDFIs and Native financial
    institutions. BIE schools are excluded here on purpose: a Bureau-Operated
    school's name is chosen by the federal government and reflects the town
    it stands in, which is how a name matcher hands Flandreau Indian School
    to the Flandreau Santee Sioux Tribe. BIE schools are handled by
    src_bie_schools(), which gates on Operation_Type.
    """
    if not os.path.exists(SLICE):
        b.notes.append("_slice.csv ABSENT - institution name route skipped")
        return
    for r in read_csv(SLICE):
        if r["entity_class"] == "BIE School":
            continue
        uid, route = idx.resolve(r["canonical_name"], r["state"])
        if not uid:
            b.refuse(r["canonical_name"], route,
                     "official name did not resolve to exactly one hub with "
                     "state agreement", SLICE, "declares_service_to",
                     from_cedar_uid=r["cedar_uid"],
                     from_source_table="institution_registry/_slice")
            continue
        b.edge(r["canonical_name"], uid, "declares_service_to",
               "official_name_the_entity_chose_names_the_nation",
               r.get("spine_source_url") or SLICE,
               "Institution official name: %r (state %s). Resolved to exactly "
               "one Cedar hub, %s." % (r["canonical_name"], r["state"],
                                       hubs[uid]["canonical_name"]),
               route, hubs, from_cedar_uid=r["cedar_uid"],
               from_entity_class=r["entity_class"], from_state=r["state"],
               from_source_table="institution_registry/_slice")


def src_bie_schools(b, hubs, idx):
    """`managed_under_contract` / `located_within` for the BIE directory.

    Operation_Type is the legal instrument. Navajo_Operation and the school's
    official name are the two routes to a HUB; neither tier is awarded
    without one.
    """
    if not os.path.exists(BIE_JSON):
        b.notes.append("bie_schools_featureserver.json ABSENT - BIE route skipped")
        return {}
    feats = [x["attributes"] for x in
             json.load(open(BIE_JSON, encoding="utf-8"))["features"]]
    slice_by_name = {}
    if os.path.exists(SLICE):
        for r in read_csv(SLICE):
            if r["entity_class"] == "BIE School":
                slice_by_name[norm(r["canonical_name"])] = r
    navajo_uid, _ = idx.resolve("Navajo Nation", "AZ")
    name_hub = {}
    for a in feats:
        name = a["School_Name"]
        st = STATE_ABBR.get(a.get("State") or "", a.get("State") or "")
        sp = slice_by_name.get(norm(name), {})
        cuid = sp.get("cedar_uid", "")
        op = a.get("Operation_Type") or ""
        nav = a.get("Navajo_Operation") or ""
        quote = ("BIE Schools Directory row: School_Name=%s; Operation_Type=%s; "
                 "Navajo_Operation=%s; City=%s; State=%s"
                 % (name, op, nav, a.get("City"), a.get("State")))
        src = ("https://www.bie.edu/schools -> https://services1.arcgis.com/"
               "UxqqIfhng71wUT9x/arcgis/rest/services/BIE_Schools_Directory/"
               "FeatureServer/0")
        # Hub route 1: the directory's own Navajo_Operation field.
        hub_uid, route = None, None
        if nav.startswith("Tribally-Controlled (Navajo)") or \
           nav.startswith("Bureau-Operated (Navajo)"):
            hub_uid, route = navajo_uid, "bie_directory_navajo_operation_field"
        # Hub route 2: the official name, ONLY for tribally-controlled schools.
        if hub_uid is None and op == "Tribally-Controlled":
            hub_uid, route = idx.resolve(name, st)
            if hub_uid is None:
                b.refuse(name, route,
                         "tribally-controlled school; official name did not "
                         "resolve to one hub with state agreement", src,
                         "managed_under_contract", from_cedar_uid=cuid,
                         from_source_table="bie_schools_featureserver")
        if hub_uid is None:
            if op == "Bureau-Operated":
                b.refuse(name, "bureau_operated_no_named_hub",
                         "federally operated and the directory names no "
                         "nation; a name match here is the Flandreau trap",
                         src, "managed_under_contract", from_cedar_uid=cuid,
                         from_source_table="bie_schools_featureserver")
            continue
        if op == "Tribally-Controlled":
            tier = "managed_under_contract"
            basis = ("bie_operation_type_tribally_controlled__PL100-297_grant_"
                     "or_PL93-638_ISDEAA_contract")
        else:
            tier = "located_within"
            basis = "bie_navajo_administrative_area_designation"
        b.edge(name, hub_uid, tier, basis, src, quote, route, hubs,
               from_cedar_uid=cuid, from_entity_class="BIE School",
               from_state=st, from_source_table="bie_schools_featureserver")
        name_hub.setdefault(norm(name), set()).add(hub_uid)
    return name_hub


def src_geocode_aiannh(b, hubs, idx, name_hub):
    """`located_within` - a real point-in-polygon, plus the sole-entity check.

    165 of 187 BIE schools sit inside one of the 864 Census AIANNH areas. The
    22 that do not are, correctly, the off-reservation boarding schools.
    """
    if not os.path.exists(AIANNH_ZIP):
        b.notes.append("AIANNH shapefile ABSENT - located_within geocode skipped")
        return
    try:
        import geopandas as gpd
        from shapely.geometry import Point
    except ImportError:
        b.notes.append("geopandas/shapely ABSENT - located_within geocode skipped")
        return
    if not os.path.exists(BIE_JSON):
        return
    areas = gpd.read_file("zip://" + AIANNH_ZIP.replace("\\", "/"))
    feats = [x["attributes"] for x in
             json.load(open(BIE_JSON, encoding="utf-8"))["features"]]
    pts = [a for a in feats if a.get("Latitude") and a.get("Longitude")]
    slice_by_name = {}
    if os.path.exists(SLICE):
        for r in read_csv(SLICE):
            if r["entity_class"] == "BIE School":
                slice_by_name[norm(r["canonical_name"])] = r

    # sole_entity_in_area, computed and used ONLY as corroboration: how many
    # Cedar hubs does this AIANNH area's own name resolve to, nationally?
    sole = {}
    for _, a in areas.iterrows():
        cores = idx.core2uid.get(norm(a["NAME"]), set())
        sole[a["GEOID"]] = (len(cores) == 1)

    gdf = gpd.GeoDataFrame(
        [{"name": a["School_Name"],
          "st": STATE_ABBR.get(a.get("State") or "", a.get("State") or "")}
         for a in pts],
        geometry=[Point(a["Longitude"], a["Latitude"]) for a in pts],
        crs="EPSG:4269")
    joined = gpd.sjoin(gdf, areas[["GEOID", "NAME", "NAMELSAD", "geometry"]],
                       how="left", predicate="within")
    src = ("Census TIGER/Line 2024 American Indian/Alaska Native/Native "
           "Hawaiian Areas, tl_2024_us_aiannh.zip; point-in-polygon against "
           "the BIE Schools Directory Latitude/Longitude")
    for _, row in joined.iterrows():
        geoid = row.get("GEOID")
        name = row["name"]
        st = row["st"]
        sp = slice_by_name.get(norm(name), {})
        if geoid is None or (isinstance(geoid, float)):
            b.refuse(name, "point_outside_every_aiannh_area",
                     "the school's published coordinates fall in no AIANNH "
                     "polygon; for the off-reservation boarding schools this "
                     "is the correct answer and it refutes a name match",
                     src, "located_within", from_cedar_uid=sp.get("cedar_uid", ""),
                     from_source_table="bie_schools_featureserver")
            continue
        uid, route = idx.resolve(row["NAME"], st, allow_national_unique=True)
        if not uid:
            b.refuse(name, route,
                     "inside AIANNH area %r but the area name did not resolve "
                     "to one Cedar hub" % row["NAMELSAD"], src,
                     "located_within", from_cedar_uid=sp.get("cedar_uid", ""),
                     from_source_table="bie_schools_featureserver")
            continue
        prior = name_hub.get(norm(name), set())
        conflict = "Y" if prior and uid not in prior else "N"
        corr = NEVER_ALONE if sole.get(geoid) else ""
        if prior and uid in prior:
            # Already carries a stronger, self-declared or contractual edge
            # to this same hub. Writing the weaker duplicate adds noise.
            b.refuse(name, "duplicate_of_stronger_tier",
                     "geocode agrees with an edge already written at a "
                     "stronger tier to hub %s" % uid, src, "located_within",
                     from_cedar_uid=sp.get("cedar_uid", ""), cand_uid=uid,
                     from_source_table="bie_schools_featureserver")
            continue
        b.edge(name, uid, "located_within",
               "geocoded_inside_a_named_aiannh_area", src,
               "BIE school %r at its published coordinates falls inside Census "
               "AIANNH area %r (GEOID %s)." % (name, row["NAMELSAD"], geoid),
               route, hubs, from_cedar_uid=sp.get("cedar_uid", ""),
               from_entity_class="BIE School", from_state=st,
               from_source_table="bie_schools_featureserver",
               corroborating_tiers=corr, conflict=conflict)


def src_native_owned_businesses(b, hubs, idx):
    """`registered_with` - the NATION's own register names the business.

    PROPOSED ADR-014 AMENDMENT. See "WHERE ADR-014 IS WRONG" (A). Every row
    here is `tier_is_adr014 = N`.
    """
    if not os.path.exists(NOB):
        b.notes.append("native_owned_businesses.csv ABSENT")
        return
    for r in read_csv(NOB):
        unres = "Y" if r["record_scope"] == "unresolved" else "N"
        key = r["business_source_id"]
        name = r["business_name_raw"]
        uid = r["certifying_authority_entity_id"]
        # entity_id here is a handle (TRBF-...), not a cedar_uid. Map it.
        hub_uid = HANDLE2UID.get(uid, "")
        if not uid:
            b.refuse(name, "no_certifying_authority_on_the_row",
                     "the source directory names no certifying nation",
                     r["source_url"], "registered_with", from_record_key=key,
                     from_source_table="native_owned_businesses",
                     was_unresolved=unres)
            continue
        if hub_uid not in hubs:
            b.refuse(name, "certifying_authority_not_a_hub_class_entity",
                     "certifying_authority_entity_id=%s does not resolve to a "
                     "hub-class spine entity" % uid, r["source_url"],
                     "registered_with", from_record_key=key,
                     from_source_table="native_owned_businesses",
                     was_unresolved=unres)
            continue
        if r["directory_type"] == "subsidiary_directory":
            # A parent asserting a subsidiary is an OWNS edge. ADR-014 leaves
            # ownership unchanged; routing it through `serves` would blur the
            # exact relation the constellation was built to sit beside.
            b.refuse(name, "ownership_relation_not_a_serves_edge",
                     "directory_type=subsidiary_directory is a parent "
                     "asserting ownership; belongs to the OWNS layer",
                     r["source_url"], "registered_with", from_record_key=key,
                     cand_uid=hub_uid, cand_name=r["certifying_authority_name"],
                     from_source_table="native_owned_businesses",
                     was_unresolved=unres)
            continue
        basis = {
            "tero": "tero_certification_by_the_nations_own_office",
            "certification_notice": "tribal_certification_notice",
            "business_licence": "tribal_business_licence_register",
            "indian_preference": "indian_preference_vendor_list",
            "shareholder_vendor": "ancsa_shareholder_business_directory",
            "vendor_list": "tribally_published_vendor_list",
            "vendor": "tribally_published_vendor_list",
        }.get(r["directory_type"], "tribally_published_register")
        quote = ("%s | %s | source programme: %s | certification_number=%s | "
                 "verification_basis=%s"
                 % (name, r["identity_claim_text"], r["programme_name"],
                    r["certification_number"], r["verification_basis"]))
        b.edge(name, hub_uid, "registered_with", basis, r["source_url"], quote,
               "certifying_authority_named_on_the_source_row", hubs,
               from_cedar_uid=r["business_entity_id"] and "" or "",
               from_entity_class=r["business_entity_class"],
               from_state=r["state_province"], from_record_key=key,
               from_source_table="native_owned_businesses",
               converts_unresolved=unres)


def src_nonprofit_missions(b, hubs, idx):
    """`declares_service_to` from IRS Form 990 mission text.

    The yield is small and the reason is the finding. Of the 3,745 distinct
    EINs behind the 5,561 unresolved Schedule C rows, the nonprofit
    workstream's own inclusion_basis pass puts 2,389 at `placename_only` and
    848 at `no_native_signal`. Those EINs are on Cedar's target list because
    a placename matched, and their own mission text explains the placename
    (PENOBSCOT BAY YMCA is a bay in Maine). Rule 7's veto - the record's own
    words outrank the geography - refuses them, and refusing them is right.
    """
    if not (os.path.exists(SCHEDC) and os.path.exists(MISSION)):
        b.notes.append("Schedule C or mission_text.jsonl ABSENT - 990 route skipped")
        return
    rows = read_csv(SCHEDC)
    unresolved_rows = [r for r in rows if r["record_scope"] == "unresolved"]
    unres_eins = set(r["ein"] for r in unresolved_rows)
    rows_by_ein = defaultdict(list)
    for r in unresolved_rows:
        rows_by_ein[r["ein"]].append(r["schedule_c_row_id"])
    state_by_ein = {}
    if os.path.exists(NP_ORGS):
        for r in read_csv(NP_ORGS):
            state_by_ein[r["EIN"]] = r.get("state") or ""
    gov = (r"(?:nation|nations|tribe|tribes|tribal|band|pueblo|rancheria|"
           r"reservation|indian community|native village)")
    pat = re.compile(r"([a-z0-9' ]{3,45}?)\s+" + gov + r"\b")
    awarded = set()
    for line in open(MISSION, encoding="utf-8"):
        d = json.loads(line)
        ein = d["ein"]
        if ein not in unres_eins:
            continue
        org = d.get("org_name") or ""
        blob = " ".join([d.get("mission_desc") or "", d.get("activity_desc") or "",
                         d.get("primary_exempt_purpose") or ""]
                        + (d.get("program_descs") or []))
        nb = norm(blob)
        state = state_by_ein.get(ein, "")
        hit = None
        for m in pat.finditer(nb):
            phrase = m.group(1).strip()
            toks = [t for t in phrase.split()
                    if t not in GOV_WORDS and t not in STATE_WORDS]
            for k in range(min(4, len(toks)), 0, -1):
                core = " ".join(toks[-k:])
                if len(core) < 5:
                    continue
                if len(core.split()) == 1 and core in GENERIC_TOKENS:
                    continue
                uids = idx.core2uid.get(core)
                if not uids or len(uids) != 1:
                    continue
                uid = next(iter(uids))
                # RULE 7 VETO: the filer's OWN name explaining the token as a
                # place - PENOBSCOT BAY, PENOBSCOT COUNTY - blocks the award.
                # A bare token may never AWARD a match but may always BLOCK.
                on = norm(org)
                if core in on and re.search(
                        re.escape(core) + r"\s+(bay|county|river|valley|"
                        r"harbor|harbour|lake|township|area|region|hills?)",
                        on):
                    b.refuse(org, "rule7_veto_placename_explained_by_own_name",
                             "the filer's own name qualifies %r as a "
                             "geographic feature" % core,
                             d.get("source_file") or MISSION,
                             "declares_service_to", from_record_key=ein,
                             cand_uid=uid, from_source_table="np_mission",
                             was_unresolved="Y")
                    hit = "vetoed"
                    break
                # The mention has to sit next to a statement of service; a
                # nation merely NAMED in a programme description is a
                # mention, not a declaration.
                # Offsets come from `nb`, so the window must be cut from
                # `nb`. Cutting it from `blob` silently misaligns - norm()
                # collapses punctuation and whitespace - and that bug cost
                # this route 61 of its 65 candidate EINs on the first run.
                window = nb[max(0, m.start() - 200):m.end() + 200]
                if CHARTER_VERBS.search(window):
                    tier = "chartered_by"
                    basis = "form_990_text_states_the_nation_chartered_it"
                elif SERVE_PRED.search(window):
                    tier = "declares_service_to"
                    basis = "form_990_mission_text_declares_service_to_the_nation"
                elif LOC_PRED.search(window):
                    tier = "declares_service_to"
                    basis = ("form_990_text_declares_the_entity_operates_on_"
                             "the_nations_land")
                else:
                    continue
                hit = (uid, m.group(0).strip(), window, tier, basis)
                break
            if hit:
                break
        if not hit:
            b.refuse(org, "no_nation_named_with_a_service_statement",
                     "990 mission/programme text names no Cedar hub next to a "
                     "statement of who it serves",
                     d.get("source_file") or MISSION, "declares_service_to",
                     from_record_key=ein, from_source_table="np_mission",
                     was_unresolved="Y")
            continue
        if hit == "vetoed":
            continue
        uid, matched, window, tier, basis = hit
        if (ein, uid) in awarded:
            continue
        awarded.add((ein, uid))
        b.edge(org, uid, tier, basis,
               d.get("source_file") or MISSION,
               "EIN %s, tax period %s. Matched %r. Filing text: %s"
               % (ein, d.get("tax_period"), matched, excerpt(window, 300)),
               "mission_text_core_unique_nationally", hubs,
               from_state=state, from_record_key=ein,
               from_source_table="np_mission", converts_unresolved="Y")


def src_refuse_wrong_instrument(b):
    """Rows a `serves` edge is the wrong tool for - recorded, not silently left.

    NIGC unresolved rows need a SUBJECT key ("Final IOWA KS-NE NIGC Settlement
    Agreement" is the Iowa Tribe of Kansas and Nebraska), which is an
    attribution, not an affiliation; an affiliation edge would misdescribe an
    enforcement action as service. The gaming self-published claims are
    already stamped "host serves 3 Cedar properties or none"; a many-to-many
    edge does not resolve a capacity figure that belongs to exactly one site.
    """
    for path, keycol, namecol, reason in [
        (os.path.join(ROOT, "data", "clean", "nigc_enforcement_actions.csv"),
         "action_id", "tribe_name_as_published",
         "needs_a_subject_key_not_an_affiliation_edge"),
        (os.path.join(ROOT, "data", "clean", "nigc_indian_lands_opinions.csv"),
         None, None, "needs_a_subject_key_not_an_affiliation_edge"),
        (os.path.join(ROOT, "data", "clean",
                      "nigc_management_contract_approvals.csv"),
         None, None, "needs_a_subject_key_not_an_affiliation_edge"),
        (os.path.join(ROOT, "data", "clean",
                      "gaming_property_self_published_claims.csv"),
         "claim_id", "site_host",
         "single_site_metric_cannot_take_a_many_to_many_edge"),
        (os.path.join(ROOT, "data", "clean",
                      "gaming_property_self_published_assertions.csv"),
         None, None, "single_site_metric_cannot_take_a_many_to_many_edge"),
    ]:
        if not os.path.exists(path):
            continue
        rows = read_csv(path)
        if not rows:
            continue
        cols = rows[0].keys()
        kc = keycol if keycol in cols else next(iter(cols))
        nc = namecol if namecol in cols else kc
        table = os.path.splitext(os.path.basename(path))[0]
        for r in rows:
            if r.get("record_scope") != "unresolved":
                continue
            b.refuse(r.get(nc) or "", reason,
                     "record_scope=unresolved, but ADR-014's `serves` edge is "
                     "not the instrument this row needs",
                     r.get("source_url") or r.get("document_url") or path,
                     "", from_record_key=r.get(kc) or "",
                     from_source_table=table, was_unresolved="Y")


# ---------------------------------------------------------------- checks

def assert_no_money_columns(columns):
    """RULE 1, mechanically: there is no column here to put a dollar in."""
    bad = [c for c in columns if MONEY_RE.search(c)]
    if bad:
        return ["RULE 1 VIOLATION: the constellation edge file may never carry "
                "a monetary column; found %r" % bad]
    return []


def check_sole_entity_never_alone(rows):
    """RULE 2, mechanically. Returns a list of failure strings."""
    bad = []
    for r in rows:
        if r.get("tier") != NEVER_ALONE:
            continue
        corr = (r.get("corroborating_tiers") or "").strip()
        others = [t for t in corr.split(";") if t and t != NEVER_ALONE]
        if not others:
            bad.append("RULE 2 VIOLATION: edge %s rests on %s alone"
                       % (r.get("edge_id"), NEVER_ALONE))
    return bad


def check_evidence_present(rows):
    bad = []
    for r in rows:
        if not (r.get("evidence_source") or "").strip():
            bad.append("RULE 3 VIOLATION: edge %s has no evidence_source"
                       % r.get("edge_id"))
        if not (r.get("evidence_excerpt") or "").strip():
            bad.append("RULE 3 VIOLATION: edge %s has no evidence_excerpt"
                       % r.get("edge_id"))
    return bad


def check_tiers_and_money(rows):
    bad = []
    for r in rows:
        if r.get("tier") not in TIER_RANK:
            bad.append("UNKNOWN TIER %r on edge %s" % (r.get("tier"), r.get("edge_id")))
        if r.get("money_rolls_through") != "N":
            bad.append("RULE 1 VIOLATION: edge %s has money_rolls_through=%r"
                       % (r.get("edge_id"), r.get("money_rolls_through")))
        if r.get("is_ownership_claim") != "N":
            bad.append("RULE 1 VIOLATION: edge %s asserts ownership"
                       % r.get("edge_id"))
    return bad


def check_hub_resolves(rows, hubs):
    bad = []
    for r in rows:
        if r.get("to_hub_cedar_uid") not in hubs:
            bad.append("edge %s points at hub %r, absent from the hub-class "
                       "spine" % (r.get("edge_id"), r.get("to_hub_cedar_uid")))
    return bad


def check_unique_ids(rows):
    c = Counter(r["edge_id"] for r in rows)
    return ["duplicate edge_id %s (x%d)" % (k, v) for k, v in c.items() if v > 1]


def self_test_the_checker():
    """A check that cannot fail is not a check. Prove rule 2's detector fires."""
    synthetic = [{"edge_id": "SYNTHETIC", "tier": NEVER_ALONE,
                  "corroborating_tiers": ""}]
    if not check_sole_entity_never_alone(synthetic):
        return ["SELF-TEST FAILED: check_sole_entity_never_alone() did not "
                "fire on a synthetic edge resting on %s alone. The rule-2 "
                "guard is inert." % NEVER_ALONE]
    ok = [{"edge_id": "SYNTHETIC2", "tier": NEVER_ALONE,
           "corroborating_tiers": "located_within;" + NEVER_ALONE}]
    if check_sole_entity_never_alone(ok):
        return ["SELF-TEST FAILED: check_sole_entity_never_alone() fired on a "
                "corroborated edge. The rule-2 guard is over-broad."]
    return []


def run_all_checks(rows, hubs, columns):
    fails = []
    fails += assert_no_money_columns(columns)
    fails += check_sole_entity_never_alone(rows)
    fails += check_evidence_present(rows)
    fails += check_tiers_and_money(rows)
    fails += check_hub_resolves(rows, hubs)
    fails += check_unique_ids(rows)
    fails += self_test_the_checker()
    return fails


# ---------------------------------------------------------------- reporting

def count_unresolved_universe():
    """Measure the 8,138 with csv.reader rather than trusting any docstring."""
    import glob
    per = {}
    total = 0
    for p in sorted(glob.glob(os.path.join(ROOT, "data", "clean", "*.csv"))):
        # A backup is not part of the universe. Concurrent workstreams leave
        # `<table>.bak_<stamp>.csv` in data/clean, and globbing them in
        # triple-counted native_owned_businesses and reported the universe as
        # 12,916 rows instead of 8,138 - deflating this script's own headline.
        base = os.path.basename(p)
        if ".bak" in base or base.startswith("_"):
            continue
        try:
            with open(p, encoding="utf-8-sig", newline="") as fh:
                rd = csv.reader(fh)
                head = next(rd)
                if "record_scope" not in head:
                    continue
                i = head.index("record_scope")
                n = sum(1 for row in rd if len(row) > i and row[i] == "unresolved")
        except (StopIteration, OSError, UnicodeDecodeError):
            continue
        if n:
            per[base] = n
            total += n
    return total, per


def report(edges, refusals):
    total, per = count_unresolved_universe()
    print("\n=== ADR-014 CONSTELLATION `serves` LAYER ===")
    print("unresolved universe measured now: %d rows across %d clean tables"
          % (total, len(per)))
    for k, v in sorted(per.items(), key=lambda x: -x[1]):
        print("    %6d  %s" % (v, k))
    print("\nedges written: %d" % len(edges))
    by_tier = Counter(e["tier"] for e in edges)
    for t in sorted(by_tier, key=lambda t: TIER_RANK[t]):
        flag = "" if t in ADR014_TIERS else "   <-- NOT AN ADR-014 TIER"
        print("    %-24s %6d   (rank %d)%s" % (t, by_tier[t], TIER_RANK[t], flag))
    conv = [e for e in edges if e["converts_unresolved_row"] == "Y"]
    print("\nedges that convert a record_scope=unresolved row: %d" % len(conv))
    adr_only = [e for e in conv if e["tier_is_adr014"] == "Y"]
    print("    of which on an ADR-014 tier only: %d" % len(adr_only))
    # Row-level conversion: an edge on an EIN converts every unresolved row
    # for that EIN, so count rows, not edges.
    rows_conv = conversion_rowcount(conv)
    print("\nHEADLINE - unresolved ROWS converted: %d of %d (%.1f%%)"
          % (rows_conv["all"], total, 100.0 * rows_conv["all"] / max(total, 1)))
    print("           on ADR-014 tiers alone:    %d of %d (%.1f%%)"
          % (rows_conv["adr014"], total,
             100.0 * rows_conv["adr014"] / max(total, 1)))
    print("\nrefusals written: %d" % len(refusals))
    for k, v in Counter(r["refusal_reason"] for r in refusals).most_common(20):
        print("    %6d  %s" % (v, k))
    conf = [e for e in edges if e["geography_selfdeclaration_conflict"] == "Y"]
    print("\ngeography-vs-self-declaration conflicts: %d" % len(conf))
    for e in conf[:20]:
        print("    %s -> %s (%s, geography) while a stronger tier names "
              "another hub" % (e["from_name"], e["to_hub_name"], e["tier"]))
    corr = [e for e in edges if NEVER_ALONE in (e["corroborating_tiers"] or "")]
    print("\nedges corroborated by %s: %d (standing alone on it: 0 by "
          "construction)" % (NEVER_ALONE, len(corr)))


def conversion_rowcount(conv_edges):
    """Rows in data/clean that these edges actually resolve.

    Counted at ROW grain, because a 990 edge keyed on an EIN converts every
    Schedule C row for that EIN, and a TERO edge converts exactly one row.
    """
    out = {"all": 0, "adr014": 0}
    ein_all, ein_adr = set(), set()
    nob_all, nob_adr = set(), set()
    for e in conv_edges:
        if e["from_source_table"] == "np_mission":
            ein_all.add(e["from_record_key"])
            if e["tier_is_adr014"] == "Y":
                ein_adr.add(e["from_record_key"])
        elif e["from_source_table"] == "native_owned_businesses":
            nob_all.add(e["from_record_key"])
            if e["tier_is_adr014"] == "Y":
                nob_adr.add(e["from_record_key"])
    if os.path.exists(SCHEDC):
        for r in read_csv(SCHEDC):
            if r["record_scope"] != "unresolved":
                continue
            if r["ein"] in ein_all:
                out["all"] += 1
            if r["ein"] in ein_adr:
                out["adr014"] += 1
    out["all"] += len(nob_all)
    out["adr014"] += len(nob_adr)
    return out


# ---------------------------------------------------------------- main

HANDLE2UID = {}


def main(argv):
    mode = argv[1] if len(argv) > 1 else "build"

    spine = read_csv(SPINE)
    hubs = {r["cedar_uid"]: r for r in spine
            if r["entity_class"] in HUB_CLASSES and r["cedar_uid"]}
    global HANDLE2UID
    HANDLE2UID = {r["tribe_id"]: r["cedar_uid"] for r in spine if r.get("tribe_id")}
    HANDLE2UID.update({r["cedar_entity_id"]: r["cedar_uid"]
                       for r in spine if r.get("cedar_entity_id")})

    if mode == "verify":
        if not os.path.exists(EDGES_OUT):
            print("VERIFY FAILED: %s does not exist" % EDGES_OUT)
            return 1
        rows = read_csv(EDGES_OUT)
        with open(EDGES_OUT, encoding="utf-8-sig", newline="") as fh:
            columns = next(csv.reader(fh))
        fails = run_all_checks(rows, hubs, columns)
        print("verify: %d edges, %d invariant failures" % (len(rows), len(fails)))
        for f in fails:
            print("  FAIL " + f)
        if fails:
            return 1
        print("verify: OK - rules 1, 2 and 3 hold, and the rule-2 detector "
              "was proven to fire on a synthetic violation")
        return 0

    idx = HubIndex(spine)
    b = Build()
    src_charter_sentences(b, hubs, idx)
    src_spine_serves_text(b, hubs, idx, spine)
    src_institution_names(b, hubs, idx)
    name_hub = src_bie_schools(b, hubs, idx)
    src_geocode_aiannh(b, hubs, idx, name_hub or {})
    src_native_owned_businesses(b, hubs, idx)
    src_nonprofit_missions(b, hubs, idx)
    src_refuse_wrong_instrument(b)

    # De-duplicate: keep the strongest tier per (from, hub, basis).
    best = {}
    for e in b.edges:
        k = e["edge_id"]
        if k not in best or e["tier_rank"] < best[k]["tier_rank"]:
            best[k] = e
    edges = sorted(best.values(),
                   key=lambda e: (e["tier_rank"], e["to_hub_name"], e["from_name"]))

    fails = run_all_checks(edges, hubs, EDGE_COLUMNS)
    if fails:
        print("BUILD ABORTED - invariants broken, nothing written:")
        for f in fails:
            print("  FAIL " + f)
        return 1

    for path, cols, rows in [(EDGES_OUT, EDGE_COLUMNS, edges),
                             (REFUSALS_OUT, REFUSAL_COLUMNS, b.refusals)]:
        if os.path.exists(path):
            bak = path + ".bak_%s_pre851" % BUILT_DATE
            with open(path, "rb") as s, open(bak, "wb") as d:
                d.write(s.read())
            print("backed up %s -> %s" % (os.path.basename(path),
                                          os.path.basename(bak)))
        with open(path, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        print("wrote %s (%d rows, %d columns)"
              % (path, len(rows), len(cols)))

    for n in b.notes:
        print("NOTE: " + n)
    report(edges, b.refusals)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
