#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
852 - EXTEND the ADR-014 constellation `serves` layer built by 851.

WHAT THIS IS AND WHAT IT IS NOT
-------------------------------
This is not a rebuild. `code/851_build_constellation_edges.py` stays the
library and the verifier: 852 imports it, runs every one of its source
functions unchanged, then adds four new sources, adjudicates one conflict it
inherited, and writes the same two files. `py -3 code/851_... verify` must
still exit 0 afterwards, and it does - 852 introduces no new tier NAME, only
new rows on the existing ladder.

    py -3 code/852_extend_constellation_edges.py            # full build
    py -3 code/852_extend_constellation_edges.py verify     # invariants only
    py -3 code/851_build_constellation_edges.py verify      # must still be 0

851 alone no longer produces the shipped file. Run 852.

WHAT 851 LEFT ON THE TABLE, MEASURED
------------------------------------
Every number below was measured by this script from files already on disk.
No network call is made by 852; the only fetch in the whole constellation
build was 851's Census TIGER AIANNH shapefile, still cached.

A. `registered_with` was refused on 149 rows for a reason that does not
   survive contact with the data. 851 keys the certifying nation off
   `certifying_authority_entity_id`, and refuses the row when that column is
   blank. But on all 149 blank-id rows `certifying_authority_name` IS
   populated - 81 "Confederated Tribes of Grand Ronde" (TERO Indian Owned
   Business list) and 68 "Pokagon Band of Potawatomi Indians" (Mno-Bmadsen
   vendor directory) - and both names resolve to exactly one Cedar hub
   nationally. 149 more unresolved rows convert.

B. `chartered_by` had 21 edges because the charter route read
   `served_entity_crosswalk.csv`, which carries 26 pre-extracted
   charter_sentence rows covering 13 distinct institution-nation pairs. The
   AIHEC TCU Roster and Profiles page those sentences came from is cached in
   full at `data/raw/external/tcu_cdfi/aihec_tcu_roster_2026-08-06.txt`, with
   a ~1,200-character narrative profile for each of 37 TCUs. Re-reading the
   full profiles with an AGENT pattern - the charter verb plus the actor that
   performed it - lifts the TCU charter route to 17 institutions.

C. `managed_under_contract` had 63 edges, all from the BIE directory's
   Operation_Type. Shard F's IHS harvest was never read at all:
   `ihs_selfgov_compacts.jsonl` (147 Title V ISDEAA self-governance
   compact holders, each with its compact year) and
   `org_membership/shard_f.jsonl` (1,047 published member-roster rows across
   85 organisations). Those two files together are the legal instrument and
   the named nation.

D. The register of Urban Indian Organizations was harvested and unused, and
   staying unused is the correct answer - recorded here as 45 explicit
   refusals rather than as silence. See src_ihs_uio_register().

THE FOUR NEW SOURCES
--------------------
1. src_nob_unlinked_authority  -> `registered_with`   (finding A)
2. src_aihec_charter_profiles  -> `chartered_by`      (finding B)
3. src_ihs_compact_programmes  -> `managed_under_contract`
4. src_org_membership_rosters  -> `declares_service_to` /
                                  `managed_under_contract`

Source 4 is the largest and it needed two guards that are worth naming,
because without either one it produces confident nonsense.

    THE PAGE GUARD. Shard F's roster harvest passes a page-level test - at
    least 40% of the member-shaped strings on the page match Cedar's register
    - and that test is necessary and not sufficient. It passed
    `narf.org/resources/tribes-oppose-line-5-pipeline/` at 57%, because a
    page listing 12 tribes that filed an amicus brief against a pipeline is
    tribe-dense and is not a membership roster. Turning those 21 rows into
    `serves` edges would assert that the Native American Rights Fund serves
    Bay Mills, Grand Traverse and Sault Ste. Marie on the evidence of a news
    item. It also passed a Great Plains Tribal Leaders Health Board *news*
    page (14 rows) about a syphilis response effort. So the source page's own
    URL must NAME membership: some path segment must be one of `members`,
    `member-tribes`, `membership`, `tribes`, `tribes-served`, `who-we-serve`,
    `tribal-councils`, `our-communities` and their close relatives, and the
    final segment must not be a headline. This kills NARF (21 rows), the
    Great Plains news page (14), `/meeting-notes/`, `/who-we-are/`,
    `/benefitting-arizona/`, `/tribes-and-climate-change/`,
    `/board-of-directors/` and every `/wp-json/wp/v2/` API root.

    THE RESIDUE GUARD (ENTITY_MATCH_RULES rule 7, second sense). Shard F
    labels 507 of its 1,047 rows `containment`, and rule 9 says containment
    never accepts alone. Re-resolving every published member string
    independently through 851's HubIndex agrees with shard F on 492 rows and
    disagrees on 7 - and on all 7 the shard is wrong (`Flandreau Santee Sioux
    Tribe` -> Santee Sioux; `Catawba Indian Nation` -> Piscataway; `Mashpee
    Wampanoag Tribe` -> Wampanoag). Agreement is therefore a real second
    observation and worth having. But the HubIndex ALONE, with no state to
    gate on, awarded `Grand Portage Band of Lake Superior Chippewa` to
    **Portage Creek, Alaska** and `Southern Indian Health Council, Inc.` to
    **Southern Ute, Colorado**, both on a one-token prefix. So every award
    must also pass rule 7's residue test: subtract the hub's own name union
    (canonical_name + fr_official_name + aliases) from the published string's
    distinctive tokens and require the residue to be EMPTY. `Southern
    Ute` leaves `health` behind; `Portage Creek` leaves `superior chippewa`.
    An institution-form word anywhere in the published string (health,
    clinic, college, board, program...) is a separate veto, because rule 7
    already says a body the nation created is not the nation.

    Cost of the two guards, measured: 1,047 roster rows in, 570 awarded.

ONE ROUTE TRIED AND REFUSED, WITH THE MEASUREMENT
--------------------------------------------------
The obvious way to convert more of the 5,561 unresolved Schedule C rows is
the filer's OWN NAME - `declares_service_to` says "the entity's own words
name the nation", and a 990 filer's legal name is its own words. It was
built, measured, and refused. It resolves 281 EINs covering 641 Schedule C
rows, and the awards are ONONDAGA GOLF AND COUNTRY CLUB, CAYUGA WINE TRAIL
INC, WEST SENECA SOCCER CLUB, ROTARY CLUB OF SEMINOLE CHARITABLE FUND,
ONEIDA-MADISON ELECTRIC COOPERATIVE and MEDICAL SOCIETY OF THE COUNTY OF
ONEIDA. In upstate New York, Oklahoma and Florida the nation's name IS the
county's name, and a filer's name cannot tell the two apart. This confirms
851's finding on the same pile from the other direction and closes the
question: no name-based route converts the Schedule C backlog.
src_990_filer_name_probe() writes all 281 as refusals so the next agent can
see the evidence rather than repeat the experiment.

THE BLACKWATER ADJUDICATION
---------------------------
851 shipped exactly one `geography_selfdeclaration_conflict = Y`:

    Blackwater Community School -> Navajo      managed_under_contract
                                -> Gila River  located_within (conflict)

Rule 7's veto says the record's own words outrank the polygon it sits inside.
The question is whose words, and the answer here is nobody's. The Navajo edge
rests on ONE coded administrative field, `Navajo_Operation =
'Tribally-Controlled (Navajo)'`, in a third-party directory. It is not the
school's words about itself, and the same directory row contradicts it three
times over: the school is at 3652 E. Blackwater School Road, Coolidge,
Arizona 85128; its published coordinates (33.0316, -111.5798) fall inside the
Gila River Indian Reservation; and its Education_Resource_Center is
Albuquerque, not one of the five Navajo-region ERCs. Rule 7 ranks a coded
third-party flag BELOW both a geocode and the record's own printed text, so
the Navajo edge is REVOKED and the Gila River edge stops being a conflict.

Blackwater is NOT promoted to `managed_under_contract` on the strength of
Operation_Type = 'Tribally-Controlled' plus a polygon naming one nation.
ADR-014 says nothing is promoted a tier by resemblance; the instrument names
no nation and the polygon is `located_within`-grade evidence. It stays at
`located_within` and says so.

OTHERS OF THE SAME SHAPE - the search, and what it found
---------------------------------------------------------
The generalised detector is internal to the source and needs no outside
knowledge: `Navajo_Operation` claims Navajo, so does the school's
Education_Resource_Center route to a Navajo-region ERC (Shiprock, Tuba City,
Crownpoint, Chinle, Window Rock)? On 187 schools the two fields agree 185
times. The two exceptions are Blackwater and **Pine Hill Schools**, and
geography splits them:

    Pine Hill Schools, Pine Hill NM 87357, ERC Albuquerque - but its
    coordinates fall INSIDE the Navajo Nation polygon, and the school's own
    published website is phswarriors.rnsb.k12.nm.us, the Ramah Navajo School
    Board. Ramah is a non-contiguous part of the Navajo Nation administered
    out of Albuquerque. Two of three signals agree; NO conflict; edge stands.

A second, wider sweep - Navajo_Operation says Navajo but the point is in no
Navajo Nation polygon - returns 12 schools, and 11 of them are the
off-reservation dormitory and border-town system (Flagstaff Bordertown
Dormitory, Winslow, Richfield UT, T'iisyaakin at Holbrook, Navajo
Preparatory at Farmington) or the Eastern Navajo checkerboard (Lake Valley,
Pueblo Pintado, Wingate, Dzilth-Na-O-Dith-Hle, Kinteel). Those land in no
polygon at all, so the geographic route already refused them
(`point_outside_every_aiannh_area`) and no conflict was ever raised. Only
Blackwater lands inside a DIFFERENT nation's reservation. That is why the
conflict count was one, and one is the right answer.

WHAT CONTRADICTS ADR-014, ON THE EVIDENCE OF EXTENDING IT
----------------------------------------------------------
F1. THE HUB CLASS LIST EXCLUDES NATIONS THAT CHARTER THINGS. `HUB_CLASSES`
    admits six spine classes and not `Federal-level constituency entity`, of
    which Cedar holds 22: the six component bands of the Minnesota Chippewa
    Tribe (White Earth, Leech Lake, Bois Forte, Fond du Lac, Grand Portage,
    Mille Lacs), Ramah Navajo Chapter, the five Paiute Indian Tribe of Utah
    bands, four Te-Moak bands, both Passamaquoddy reservations and two
    Shoshone-Bannock bands. Each has its own council. AIHEC prints "The White
    Earth Reservation Tribal Council established the White Earth Tribal and
    Community College in 1997" - a charter sentence naming the nation, the
    strongest evidence ADR-014 defines - and the edge cannot be written
    because the nation is not an allowed hub. Refused here as
    `hub_class_excludes_constituency_entity` rather than quietly widened,
    which is the discipline 851 showed with `registered_with`. Widening the
    list is an owner decision with blast radius across every route.

F2. A FOUR-LETTER NATION IS UNREACHABLE BY NAME. HubIndex refuses to index a
    single-token core shorter than five characters, so `Crow` has no name
    index entry at all, and "LBHC is a public two-year community college
    chartered by the Crow Tribe of Indians in 1980" resolves to nothing. 852
    does not loosen that guard - it is what stops `bay` and `lake` - but adds
    a narrow rule-7 residue rung beneath it: among hubs IN THE SAME STATE,
    accept the one whose own name union leaves an empty residue, if exactly
    one does. `Crow Tribe of Indians` in MT leaves nothing over for Crow and
    leaves `crow` over for everything else. This is corroborated evidence
    (state + full-name accounting), not a loosened token match.

F3. `HubIndex.resolve` TREATS A BLANK STATE AS A MISMATCH. `state_ok()`
    documents the right rule - "Blank state cannot agree or disagree; say so
    rather than guessing" - and `resolve()` does not use it: with state='' it
    compares `hubs[uid]['state'] == ''`, fails, and returns
    REFUSED_state_mismatch. That is what hides finding A: both Grand Ronde
    and Pokagon are nationally unique and both were refused for disagreeing
    with a state that was never stated. 852 fixes this inside its own
    resolver only, so 851's other routes keep their exact prior outcomes.

F4. `sole_entity_in_area` still corroborates and still never carries. 27
    edges cite it; zero rest on it. 851 was right that it should be demoted
    from tier to corroborator in the ADR text.

F5. The `registered_with` amendment landed. See ADR-014 between the markers,
    subsection "Amendment 1". Those 2,216 edges now carry
    `tier_is_adr014 = Y`.

THE THREE RULES, UNCHANGED
--------------------------
1. No money column exists in the output and every row carries
   `money_rolls_through = N` and `is_ownership_claim = N`. A tribe holding an
   ISDEAA Title V compact for a health corporation does not thereby book that
   corporation's revenue, and an intertribal council's member list is not a
   list of its subsidiaries.
2. `sole_entity_in_area` never stands alone; 851's detector is re-run here
   and is still proven against a synthetic violation.
3. Zero fabrication. Every new edge carries evidence_source and
   evidence_excerpt. Every candidate that failed a rung is written to
   `cedar_constellation_refusals.csv` with the rung it failed.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import os
import re
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = "code/852_extend_constellation_edges.py"
BUILT_DATE = "2026-09-02"

_spec = importlib.util.spec_from_file_location(
    "cedar851", os.path.join(ROOT, "code", "851_build_constellation_edges.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

norm = M.norm
read_csv = M.read_csv
mkid = M.mkid
excerpt = M.excerpt

SHARD_F = os.path.join(ROOT, "data", "staging", "tribe_harvest", "shard_f")
COMPACTS = os.path.join(SHARD_F, "ihs_selfgov_compacts.jsonl")
UIO = os.path.join(SHARD_F, "ihs_uio_register.jsonl")
ROSTERS = os.path.join(ROOT, "data", "staging", "org_membership", "shard_f.jsonl")
AIHEC_TXT = os.path.join(ROOT, "data", "raw", "external", "tcu_cdfi",
                         "aihec_tcu_roster_2026-08-06.txt")
AIHEC_JSON = os.path.join(ROOT, "data", "raw", "external", "tcu_cdfi",
                          "_aihec_parsed.json")
AIHEC_URL = "https://www.aihec.org/tcu-roster-and-profiles/ (cached 2026-08-06)"

# ------------------------------------------------------------------ vocab

# Page chrome that a roster scraper picks up around the names. These may
# never AWARD anything; they are only permitted to be ABSENT from a residue.
CHROME = set("member members membership current former our view more learn "
             "read about tribal tribes tribe nation nations".split())

# ENTITY_MATCH_RULES rule 7: "an institution form - SCHOOL, AUTHORITY,
# COLLEGE, UTILITY, HOUSING - a body the nation created -> HOLD". Extended to
# the forms that actually appear in these two registers.
INSTITUTION_FORMS = set("""
health clinic hospital college university school academy board program
programs center centers centre centres services service authority housing
utility utilities enterprise enterprises corporation corp incorporated inc
llc company foundation association consortium project department agency
office bureau institute fund coalition alliance commission
""".split())

# The five Education Resource Centers the BIE routes its Navajo-region
# schools through. Measured from the directory itself, not assumed: on 187
# schools Navajo_Operation and this list agree 185 times.
NAVAJO_ERCS = {"Shiprock, NM", "Tuba City, AZ", "Crownpoint, NM",
               "Chinle, AZ", "Window Rock, AZ"}

# A source page must NAME membership. Matched against each path segment.
ROSTER_SEGMENT = re.compile(
    r"^(members?|membership|member[-_][a-z0-9-]*tribes?[-_a-z0-9]*|"
    r"tribal[-_]members?|member[-_]tribal[-_]nations?|"
    r"membership[-_]profiles?|tribes|tribes[-_]served|tribes[-_]we[-_]serve|"
    r"who[-_]we[-_]serve|tribal[-_]councils?|tribal[-_]council[-_]list|"
    r"[a-z]*[-_]?tribal[-_]nations?|communities|our[-_]communities|"
    r"tribal[-_]health[-_]programs?|connectedcommunities)$")

# The charter verb plus the actor that performed it. Anything that names a
# nation WITHOUT an actor relation is a mention, and "they established Fort
# Belknap College" is why: the nation is in the college's own name, which is
# the Turtle Mountain trap ENTITY_MATCH_RULES rule 7 exists to refuse.
CHARTER_AGENT_AFTER = re.compile(
    r"\b(?:chartered|founded|established|created|organi[sz]ed|incorporated)\b"
    r"(?:[^.;]{0,45}?)\b(?:by|under (?:the )?(?:sovereign )?(?:governmental )?"
    r"authority of|under a charter (?:from|of))\s+([^.;]{3,90})", re.I)
CHARTER_AGENT_BEFORE = re.compile(
    r"\b((?:[Tt]he\s+)?[A-Z][^.;]{3,80}?)\s+"
    r"(?:chartered|founded|established|created)\b")

# Rule 7's veto in its placename form, reused from 851's 990 route.
GEO_QUALIFIER = (r"\s+(bay|county|river|valley|harbor|harbour|lake|township|"
                 r"area|region|hills?|creek|falls|springs|island|mountains?|"
                 r"sound|pass|trail|road|street|city|park)\b")


def path_segments(url):
    u = re.sub(r"^https?://web\.archive\.org/web/\d+/", "", url or "")
    u = re.sub(r"^https?://[^/]+", "", u)
    u = u.split("#")[0].split("?")[0]
    return [s for s in u.lower().split("/") if s]


def page_names_membership(url):
    """The page's own address must say it is a membership list."""
    segs = path_segments(url)
    if not segs:
        return False, "url has no path; a site root is not a roster page"
    if not any(ROSTER_SEGMENT.match(s) for s in segs):
        return False, ("no path segment names membership: %s"
                       % "/".join(segs))
    last = segs[-1]
    if not ROSTER_SEGMENT.match(last) and last.count("-") >= 3:
        return False, ("final path segment %r reads as a headline, not a "
                       "roster" % last)
    return True, "/".join(segs)


# ------------------------------------------------------------------ resolver

class Resolver(object):
    """851's HubIndex plus the two narrow rungs findings F2 and F3 name.

    Everything here sits BENEATH 851's ladder: the prefix index is tried
    first and unchanged, and these rungs only run when it returns nothing.
    """

    def __init__(self, idx, hubs):
        self.idx = idx
        self.hubs = hubs
        self.tokens = {}
        self.by_state = defaultdict(list)
        for uid, r in hubs.items():
            s = set()
            for f in ([r.get("canonical_name"), r.get("fr_official_name")]
                      + (r.get("aliases") or "").split("|")):
                s |= set(norm(f).split())
            s.discard("")
            self.tokens[uid] = s
            if r.get("state"):
                self.by_state[r["state"]].append(uid)

    def distinctive(self, text):
        return [t for t in norm(text).split()
                if t not in M.GOV_WORDS and t not in CHROME
                and not t.isdigit() and len(t) > 2]

    def residue(self, text, uid):
        """Rule 7: what the hub's own name union does not account for."""
        return [t for t in self.distinctive(text)
                if t not in self.tokens[uid]
                and t not in M.STATE_WORDS and t not in M.GENERIC_TOKENS]

    def has_institution_form(self, text):
        return [t for t in self.distinctive(text) if t in INSTITUTION_FORMS]

    def resolve(self, text, state, allow_national_unique=False):
        """(uid, route). Rungs, strongest first."""
        uid, route = self.idx.resolve(text, state,
                                      allow_national_unique=allow_national_unique)
        if uid:
            return uid, route
        # F3: a state that was never stated cannot disagree with anything.
        if route == "REFUSED_state_mismatch" and not state:
            u2, _ = self.idx.resolve(text, state, allow_national_unique=True)
            if u2:
                return u2, "unique_nationally_state_not_stated"
        # F2: rule 7 residue, gated on the state, for cores the prefix index
        # refuses to hold (a four-letter nation such as Crow).
        if state and route in ("no_match", "REFUSED_state_mismatch",
                               "REFUSED_ambiguous"):
            zero = [u for u in self.by_state.get(state, [])
                    if not self.residue(text, u)]
            if len(zero) == 1:
                return zero[0], "rule7_zero_residue_unique_in_state"
        return None, route

    def award_ok(self, text, uid):
        """The guard every name-derived award in 852 must pass."""
        inst = self.has_institution_form(text)
        if inst:
            return False, ("rule7_institution_form_word", ", ".join(inst))
        res = self.residue(text, uid)
        if res:
            return False, ("rule7_residue_not_empty", ", ".join(res))
        return True, ("", "")


# ------------------------------------------------------------------ sources

def src_nob_unlinked_authority(b, hubs, rs):
    """`registered_with` where 851 refused on a blank ID but a NAME is there.

    Finding A. 851 refuses `no_certifying_authority_on_the_row` when
    `certifying_authority_entity_id` is blank. On every one of those rows
    `certifying_authority_name` is populated and resolves.
    """
    if not os.path.exists(M.NOB):
        b.notes.append("native_owned_businesses.csv ABSENT - finding A skipped")
        return
    n = 0
    for r in read_csv(M.NOB):
        if r.get("certifying_authority_entity_id"):
            continue                      # 851 already handled these
        name_auth = (r.get("certifying_authority_name") or "").strip()
        key = r["business_source_id"]
        name = r["business_name_raw"]
        unres = "Y" if r["record_scope"] == "unresolved" else "N"
        if not name_auth:
            continue                      # 851's refusal stands, correctly
        if r["directory_type"] == "subsidiary_directory":
            continue                      # ownership, not `serves`
        state = r.get("state_province") or ""
        uid, route = rs.resolve(name_auth, state)
        if not uid or uid not in hubs:
            b.refuse(name, "certifying_authority_name_did_not_resolve",
                     "certifying_authority_entity_id is blank and the printed "
                     "name %r resolved as %s" % (name_auth, route),
                     r["source_url"], "registered_with", from_record_key=key,
                     from_source_table="native_owned_businesses",
                     was_unresolved=unres)
            continue
        ok, (why, detail) = rs.award_ok(name_auth, uid)
        if not ok:
            b.refuse(name, why,
                     "certifying authority %r against hub %s: %s"
                     % (name_auth, hubs[uid].get("canonical_name"), detail),
                     r["source_url"], "registered_with", from_record_key=key,
                     cand_uid=uid, from_source_table="native_owned_businesses",
                     was_unresolved=unres)
            continue
        basis = {
            "tero": "tero_certification_by_the_nations_own_office",
            "vendor_list": "tribally_published_vendor_list",
            "business_licence": "tribal_business_licence_register",
            "indian_preference": "indian_preference_vendor_list",
        }.get(r["directory_type"], "tribally_published_register")
        quote = ("%s | certifying authority as printed by the source: %r | "
                 "programme: %s | %s"
                 % (name, name_auth, r["programme_name"],
                    r["identity_claim_text"]))
        b.edge(name, uid, "registered_with", basis, r["source_url"], quote,
               "certifying_authority_NAME_on_the_source_row__" + route, hubs,
               from_entity_class=r["business_entity_class"],
               from_state=state, from_record_key=key,
               from_source_table="native_owned_businesses",
               converts_unresolved=unres)
        n += 1
    b.notes.append("finding A: %d registered_with edges recovered from a "
                   "printed certifying-authority NAME" % n)


def _aihec_blocks():
    """One narrative profile block per TCU, anchored on `Name (ACRONYM)`.

    Anchoring on the bare name is wrong and was measured to be wrong: several
    college names recur in a locations list further down the page, so
    `rfind` put the Bay Mills charter sentence inside the Aaniiih Nakoda
    block and lost it.
    """
    if not (os.path.exists(AIHEC_TXT) and os.path.exists(AIHEC_JSON)):
        return []
    t = re.sub(r"\s+", " ", open(AIHEC_TXT, encoding="utf-8").read())
    prof = json.load(open(AIHEC_JSON, encoding="utf-8"))
    anch = []
    for x in prof:
        a = x.get("acronym") or ""
        i = t.find("%s (%s)" % (x["name"], a)) if a else -1
        if i < 0:
            i = t.rfind(x["name"])
        if i >= 0:
            anch.append((i, x))
    anch.sort()
    out = []
    for k, (i, x) in enumerate(anch):
        j = anch[k + 1][0] if k + 1 < len(anch) else len(t)
        out.append((x, t[i:j]))
    return out


def src_aihec_charter_profiles(b, hubs, rs, slice_by_name):
    """`chartered_by` from the full AIHEC TCU profile prose. Finding B."""
    blocks = _aihec_blocks()
    if not blocks:
        b.notes.append("AIHEC roster text ABSENT - charter profile route skipped")
        return
    n = 0
    for x, blk in blocks:
        name, st = x["name"], x.get("state") or ""
        sp = slice_by_name.get(norm(name), {})
        got = None
        for pat, which in ((CHARTER_AGENT_AFTER, "charter_verb_then_actor"),
                           (CHARTER_AGENT_BEFORE, "actor_then_charter_verb")):
            for mm in pat.finditer(blk):
                agent = mm.group(1).strip()
                uid, route = rs.resolve(agent, st)
                if not uid or uid not in hubs:
                    continue
                ok, (why, detail) = rs.award_ok(agent, uid)
                if not ok:
                    b.refuse(name, why,
                             "charter agent %r against hub %s: %s"
                             % (agent, hubs[uid].get("canonical_name"), detail),
                             AIHEC_URL, "chartered_by",
                             from_cedar_uid=sp.get("cedar_uid", ""),
                             cand_uid=uid,
                             from_source_table="tcu_cdfi/aihec_tcu_roster")
                    continue
                got = (uid, route, which, mm.group(0).strip())
                break
            if got:
                break
        if not got:
            # Distinguish "the nation is not an allowed hub" from "no charter
            # sentence" - finding F1 is invisible if both read the same.
            f1 = _constituency_charter_probe(blk, st)
            if f1:
                b.refuse(name, "hub_class_excludes_constituency_entity",
                         "AIHEC prints a charter sentence naming %s, a "
                         "`Federal-level constituency entity`, which "
                         "HUB_CLASSES does not admit. Quote: %s"
                         % (f1[1], excerpt(f1[2], 200)),
                         AIHEC_URL, "chartered_by",
                         from_cedar_uid=sp.get("cedar_uid", ""), cand_uid=f1[0],
                         cand_name=f1[1],
                         from_source_table="tcu_cdfi/aihec_tcu_roster")
            else:
                b.refuse(name, "no_charter_sentence_with_a_named_actor",
                         "the AIHEC profile carries no charter/founding verb "
                         "with an actor that resolves to one Cedar hub",
                         AIHEC_URL, "chartered_by",
                         from_cedar_uid=sp.get("cedar_uid", ""),
                         from_source_table="tcu_cdfi/aihec_tcu_roster")
            continue
        uid, route, which, sentence = got
        b.edge(name, uid, "chartered_by",
               "aihec_profile_charter_sentence_names_the_chartering_nation__"
               + which, AIHEC_URL,
               "AIHEC TCU Roster and Profiles, %s: “%s”"
               % (name, sentence), route, hubs,
               from_cedar_uid=sp.get("cedar_uid", ""),
               from_entity_class="Tribal College or University",
               from_state=st,
               from_source_table="tcu_cdfi/aihec_tcu_roster")
        n += 1
    b.notes.append("finding B: %d chartered_by edges from AIHEC full profiles"
                   % n)


_CONSTITUENCY = {}


def _constituency_charter_probe(blk, st):
    """Is the charter actor a nation HUB_CLASSES refuses to admit? (F1)"""
    for pat in (CHARTER_AGENT_AFTER, CHARTER_AGENT_BEFORE):
        for mm in pat.finditer(blk):
            agent = norm(mm.group(1))
            for uid, (nm, state, toks) in _CONSTITUENCY.items():
                if state and st and state != st:
                    continue
                core = [t for t in norm(nm).split()
                        if t not in M.GOV_WORDS and len(t) > 3]
                if core and all(t in agent for t in core):
                    return uid, nm, mm.group(0)
    return None


def src_ihs_compact_programmes(b, hubs, rs):
    """`managed_under_contract` from the IHS Title V compact register.

    IHS prints some entries as `Nation - Programme`. That row is the ISDEAA
    instrument naming both the compacting nation and the facility operated
    under it, which is precisely ADR-014's rank-2 basis. Where the entry is
    the nation alone the edge would point at itself and is refused; where it
    is an organisation, the register names no nation and the organisation's
    own roster is the only thing that can - see src_org_membership_rosters.
    """
    if not os.path.exists(COMPACTS):
        b.notes.append("ihs_selfgov_compacts.jsonl ABSENT - compact route skipped")
        return {}
    rows = [json.loads(x) for x in open(COMPACTS, encoding="utf-8")]
    holders = {}
    n = 0
    for r in rows:
        listed = r["name_as_listed"]
        # IHS separates nation from programme with an en dash; the cached
        # text carries it as U+2013 or as a replacement char.
        head = re.split(r"[–—�-]", listed)[0].strip()
        holders[norm(head)] = r
        parent = (r.get("parent_tribe_as_listed") or "").strip()
        prog = (r.get("program_as_listed") or "").strip()
        src = r["source_url"]
        quote = ("IHS Office of Tribal Self-Governance register of Tribes and "
                 "Tribal Organizations with a Title V compact, %s Area: "
                 "“%s (%s)”. Authority, per the IHS landing page: %s"
                 % (r["ihs_area"], listed, r["compact_year"],
                    r["authorizing_basis_quote"]))
        if not (parent and prog):
            uid, route = rs.resolve(head, "", allow_national_unique=True)
            if uid and uid in hubs:
                b.refuse(listed, "self_edge_compactor_is_the_nation_itself",
                         "the compact holder resolves to hub %s; a nation "
                         "does not hold a `serves` edge to itself"
                         % hubs[uid].get("canonical_name"), src,
                         "managed_under_contract", cand_uid=uid,
                         from_source_table="shard_f/ihs_selfgov_compacts")
            else:
                b.refuse(listed, "compact_register_names_no_member_nation",
                         "the entry is an organisation and the register names "
                         "no nation it compacts on behalf of; only the "
                         "organisation's own roster can supply that", src,
                         "managed_under_contract",
                         from_source_table="shard_f/ihs_selfgov_compacts")
            continue
        uid, route = rs.resolve(parent, "", allow_national_unique=True)
        if not uid or uid not in hubs:
            b.refuse(prog, "compact_parent_nation_did_not_resolve",
                     "IHS prints the compacting nation as %r, which resolved "
                     "as %s" % (parent, route), src, "managed_under_contract",
                     from_source_table="shard_f/ihs_selfgov_compacts")
            continue
        ok, (why, detail) = rs.award_ok(parent, uid)
        if not ok:
            b.refuse(prog, why, "compact parent %r against hub %s: %s"
                     % (parent, hubs[uid].get("canonical_name"), detail),
                     src, "managed_under_contract", cand_uid=uid,
                     from_source_table="shard_f/ihs_selfgov_compacts")
            continue
        b.edge(prog, uid, "managed_under_contract",
               "ihs_title_v_isdeaa_selfgovernance_compact_register__"
               "programme_operated_under_the_nations_compact",
               src, quote, "ihs_register_prints_nation_dash_programme", hubs,
               from_entity_class="", from_state="",
               from_record_key=listed,
               from_source_table="shard_f/ihs_selfgov_compacts")
        n += 1
    b.notes.append("IHS compact register: %d managed_under_contract edges from "
                   "nation-dash-programme entries; %d holders indexed for the "
                   "roster route" % (n, len(holders)))
    return holders


def src_ihs_uio_register(b):
    """The Title V UIO register, accounted for as refusals rather than silence.

    IHS's own sentence is the reason: the contract is between the Urban
    Indian Organization and the INDIAN HEALTH SERVICE. The register names a
    city and an IHS area; it names no nation. Cedar's spine says the same
    thing in the entities' own words, which 851 already refuses with
    `entity_declares_no_single_hub`.
    """
    if not os.path.exists(UIO):
        return
    rows = [json.loads(x) for x in open(UIO, encoding="utf-8")]
    for r in rows:
        b.refuse(r["org_name_as_listed"],
                 "title_v_contract_is_with_ihs_and_names_no_nation",
                 "IHS register: Location=%s, IHS Area=%s, Service Level=%s. "
                 "The instrument is a contract with the Indian Health "
                 "Service, not with a nation; a `serves` edge needs a hub and "
                 "this register supplies none."
                 % (r.get("location_city"), r.get("ihs_area"),
                    r.get("service_level")),
                 r["source_url"], "managed_under_contract",
                 from_source_table="shard_f/ihs_uio_register")
    b.notes.append("IHS UIO register: %d organisations recorded as refusals "
                   "(the register names no nation)" % len(rows))


def src_org_membership_rosters(b, hubs, rs, compact_holders, spine_by_uid):
    """`declares_service_to` / `managed_under_contract` from published rosters.

    The organisation's own membership page naming a nation is the entity's
    own words about who it serves - ADR-014 rank 4, exactly as defined. Where
    that same organisation also appears in the IHS Title V self-governance
    compact register, the instrument is on the record too and the edge is
    written at rank 2, with BOTH sources in the excerpt so a reviewer can
    split them again with one filter on `evidence_basis`.
    """
    if not os.path.exists(ROSTERS):
        b.notes.append("org_membership/shard_f.jsonl ABSENT - roster route skipped")
        return
    rows = [json.loads(x) for x in open(ROSTERS, encoding="utf-8")]
    page_ok = {}
    n_serve = n_contract = 0
    for r in rows:
        member = (r.get("member_name_raw") or "").strip()
        org = r.get("org_name") or ""
        org_uid = r.get("org_cedar_uid") or ""
        src = r.get("source_url") or ""
        if not member:
            continue
        if src not in page_ok:
            page_ok[src] = page_names_membership(src)
        ok_page, page_note = page_ok[src]
        if not ok_page:
            b.refuse(member, "source_page_does_not_name_membership", page_note,
                     src, "declares_service_to", from_cedar_uid=org_uid,
                     from_source_table="org_membership/shard_f")
            continue
        inst = rs.has_institution_form(member)
        if inst:
            b.refuse(member, "rule7_institution_form_word",
                     "published member string carries %s; a body the nation "
                     "created is not the nation" % ", ".join(inst),
                     src, "declares_service_to", from_cedar_uid=org_uid,
                     from_source_table="org_membership/shard_f")
            continue
        uid, route = rs.resolve(member, "", allow_national_unique=True)
        if not uid or uid not in hubs:
            b.refuse(member, "roster_name_did_not_resolve_to_one_hub",
                     "published by %s; resolved as %s" % (org, route),
                     src, "declares_service_to", from_cedar_uid=org_uid,
                     from_source_table="org_membership/shard_f")
            continue
        res = rs.residue(member, uid)
        if res:
            b.refuse(member, "rule7_residue_not_empty",
                     "against hub %s the published string leaves %s "
                     "unaccounted for" % (hubs[uid].get("canonical_name"),
                                          ", ".join(res)),
                     src, "declares_service_to", from_cedar_uid=org_uid,
                     cand_uid=uid, from_source_table="org_membership/shard_f")
            continue
        # Second independent observation, where shard F offered one.
        shard_uid = (r.get("candidate_cedar_uid") or "")
        shard_method = r.get("match_method") or ""
        if (shard_uid and shard_uid in hubs and shard_uid != uid
                and "AMBIG" not in shard_method and not shard_method.startswith("fuzzy")):
            b.refuse(member, "two_matchers_disagree_on_the_hub",
                     "shard F (%s) says %s; the rule-7 resolver says %s. Rule "
                     "13 holds a name collision rather than picking one."
                     % (shard_method, r.get("candidate_canonical_name"),
                        hubs[uid].get("canonical_name")),
                     src, "declares_service_to", from_cedar_uid=org_uid,
                     cand_uid=shard_uid, from_source_table="org_membership/shard_f")
            continue
        compact = compact_holders.get(norm(org))
        org_row = spine_by_uid.get(org_uid, {})
        if compact:
            tier = "managed_under_contract"
            basis = ("isdeaa_title_v_selfgovernance_compact_holder__member_"
                     "nation_named_on_the_organisations_own_roster")
            quote = ("%s publishes %r as a member on %s. The same "
                     "organisation holds an IHS Title V ISDEAA "
                     "self-governance compact entered %s (%s Area), per %s: "
                     "“%s”"
                     % (org, member, src, compact["compact_year"],
                        compact["ihs_area"], compact["source_url"],
                        compact["authorizing_basis_quote"]))
            n_contract += 1
        else:
            tier = "declares_service_to"
            basis = "organisations_own_published_membership_roster"
            quote = ("%s publishes %r on its own membership page. Shard F "
                     "page test: %s"
                     % (org, member, r.get("page_is_roster_basis") or "n/a"))
            n_serve += 1
        corr = ""
        if shard_uid == uid:
            corr = ""   # not a TIER, so it does not belong in corroborating_tiers
            basis += "__corroborated_by_shard_f_" + (shard_method or "match")
        b.edge(org, uid, tier, basis, src, quote,
               route + "__page_names_membership", hubs,
               from_cedar_uid=org_uid,
               from_entity_class=r.get("org_entity_class") or "",
               from_state=org_row.get("state") or "",
               from_source_table="org_membership/shard_f",
               corroborating_tiers=corr)
    b.notes.append("rosters: %d declares_service_to + %d managed_under_contract"
                   % (n_serve, n_contract))


def src_990_filer_name_probe(b, hubs, rs):
    """Tried, measured, refused. See the module docstring.

    Written as refusals ON PURPOSE. An experiment whose result is "do not do
    this" is worth exactly as much as one that yields edges, and it is only
    worth that if the evidence survives in the file.
    """
    if not (os.path.exists(M.SCHEDC) and os.path.exists(M.MISSION)):
        return
    unres = [r for r in read_csv(M.SCHEDC) if r["record_scope"] == "unresolved"]
    unres_eins = set(r["ein"] for r in unres)
    rows_by_ein = Counter(r["ein"] for r in unres)
    state_by_ein = {}
    if os.path.exists(M.NP_ORGS):
        for r in read_csv(M.NP_ORGS):
            state_by_ein[r["EIN"]] = r.get("state") or ""
    seen = set()
    n = rows = 0
    for line in open(M.MISSION, encoding="utf-8"):
        d = json.loads(line)
        ein = d["ein"]
        if ein not in unres_eins or ein in seen:
            continue
        seen.add(ein)
        org = d.get("org_name") or ""
        uid, route = rs.idx.resolve(org, state_by_ein.get(ein, ""))
        if not uid or uid not in hubs:
            continue
        on = norm(org)
        veto = False
        for c in sorted((t for t in rs.tokens[uid] if len(t) >= 5),
                        key=len, reverse=True):
            if c in on and re.search(re.escape(c) + GEO_QUALIFIER, on):
                veto = True
                break
        if veto:
            continue
        n += 1
        rows += rows_by_ein[ein]
        b.refuse(org, "filer_name_route_refused_placename_indistinguishable",
                 "the filer's own legal name resolves to hub %s (%s), but in "
                 "the filer's state the nation's name is also the county's or "
                 "the lake's. The route was built and measured; across the "
                 "unresolved Schedule C backlog it awards ONONDAGA GOLF AND "
                 "COUNTRY CLUB, CAYUGA WINE TRAIL INC and WEST SENECA SOCCER "
                 "CLUB, so it is refused wholesale rather than per row."
                 % (hubs[uid].get("canonical_name"), route),
                 d.get("source_file") or M.MISSION, "declares_service_to",
                 from_record_key=ein, cand_uid=uid,
                 from_source_table="np_mission", was_unresolved="Y")
    b.notes.append("990 filer-name route REFUSED wholesale: it would have "
                   "awarded %d EINs covering %d Schedule C rows" % (n, rows))


# ------------------------------------------------------- BIE adjudication

def bie_navajo_field_audit():
    """Return the BIE rows where the directory contradicts itself, plus the
    polygon each school's own coordinates fall in.

    Two internal fields, no outside knowledge: Navajo_Operation claims Navajo
    and Education_Resource_Center routes the school somewhere. Then the
    geocode breaks the tie.
    """
    if not os.path.exists(M.BIE_JSON):
        return [], {}
    feats = [x["attributes"] for x in
             json.load(open(M.BIE_JSON, encoding="utf-8"))["features"]]
    poly = {}
    try:
        import geopandas as gpd
        from shapely.geometry import Point
    except ImportError:
        gpd = None
    if gpd is not None and os.path.exists(M.AIANNH_ZIP):
        areas = gpd.read_file("zip://" + M.AIANNH_ZIP.replace("\\", "/"))
        pts = [a for a in feats if a.get("Latitude") and a.get("Longitude")]
        gdf = gpd.GeoDataFrame(
            [{"n": a["School_Name"]} for a in pts],
            geometry=[Point(a["Longitude"], a["Latitude"]) for a in pts],
            crs="EPSG:4269")
        j = gpd.sjoin(gdf, areas[["GEOID", "NAMELSAD", "geometry"]],
                      how="left", predicate="within")
        for _, row in j.iterrows():
            nm = row.get("NAMELSAD")
            poly[norm(row["n"])] = nm if isinstance(nm, str) else ""
    flagged = []
    for a in feats:
        if "(Navajo)" not in (a.get("Navajo_Operation") or ""):
            continue
        erc = a.get("Education_Resource_Center") or ""
        if erc in NAVAJO_ERCS:
            continue
        nm = poly.get(norm(a["School_Name"]), "")
        flagged.append({
            "school": a["School_Name"],
            "navajo_operation": a["Navajo_Operation"],
            "erc": erc,
            "city": a.get("City"), "state": a.get("State"),
            "zip": a.get("Zip_Code"), "street": a.get("Street_Address"),
            "website": a.get("website"),
            "lat": a.get("Latitude"), "lon": a.get("Longitude"),
            "polygon": nm,
            "polygon_is_navajo": ("Navajo Nation" in nm),
        })
    return flagged, poly


def adjudicate_bie_navajo_field(b, edges, hubs):
    """Revoke a Navajo edge whose only support is the contradicted flag.

    The rule, generalised so it is not a hand-patch of one row: refuse the
    `Navajo_Operation`-derived edge when BOTH of the directory's own
    corroborators point away - the Education_Resource_Center is not a
    Navajo-region ERC AND the school's published coordinates fall inside a
    DIFFERENT nation's AIANNH polygon. One contradicting signal is a reason
    to look; two is a finding.
    """
    flagged, _ = bie_navajo_field_audit()
    revoke = set()
    lines = []
    for f in flagged:
        if f["polygon"] and not f["polygon_is_navajo"]:
            revoke.add(norm(f["school"]))
            lines.append("REVOKE  %s: ERC %s is not a Navajo-region ERC and "
                         "the coordinates fall in %s"
                         % (f["school"], f["erc"], f["polygon"]))
        elif f["polygon_is_navajo"]:
            lines.append("CONFIRM %s: ERC %s is anomalous but the coordinates "
                         "fall in %s, so two of three signals agree"
                         % (f["school"], f["erc"], f["polygon"]))
        else:
            lines.append("HOLD    %s: ERC %s is anomalous and the coordinates "
                         "fall in no AIANNH polygon (border-town dormitory or "
                         "Eastern Navajo checkerboard); the geographic route "
                         "already refused it, so no edge rests on this"
                         % (f["school"], f["erc"]))
    kept = []
    for e in edges:
        if (e["from_source_table"] == "bie_schools_featureserver"
                and e["hub_resolution_route"] == "bie_directory_navajo_operation_field"
                and norm(e["from_name"]) in revoke):
            b.refuse(e["from_name"],
                     "bie_navajo_operation_field_contradicted_by_two_"
                     "corroborators_in_the_same_row",
                     "ENTITY_MATCH_RULES rule 7 ranks a coded third-party "
                     "administrative flag below both a geocode and the "
                     "record's own printed text. `Navajo_Operation` is the "
                     "only support for this edge and the same directory row "
                     "contradicts it twice. REVOKED by ruling 852-1.",
                     e["evidence_source"], e["tier"],
                     from_cedar_uid=e["from_cedar_uid"], cand_uid=e["to_hub_cedar_uid"],
                     cand_name=e["to_hub_name"],
                     from_source_table=e["from_source_table"])
            continue
        kept.append(e)
    return kept, lines


def reconcile_conflict_flags(edges):
    """`geography_selfdeclaration_conflict` must be EARNED, every run.

    851 stamps the flag when a geographic edge disagrees with a stronger
    self-declared or contractual edge for the same entity. Once the stronger
    edge is revoked there is nothing to disagree with, and a stale Y would
    read as an unresolved dispute that no longer exists. Recomputed here from
    the surviving rows rather than patched.
    """
    strong = defaultdict(set)
    for e in edges:
        if int(e["tier_rank"]) < 5:
            strong[norm(e["from_name"])].add(e["to_hub_cedar_uid"])
    cleared = []
    for e in edges:
        peers = strong.get(norm(e["from_name"]), set())
        want = "Y" if (peers and e["to_hub_cedar_uid"] not in peers
                       and int(e["tier_rank"]) >= 5) else "N"
        if e["geography_selfdeclaration_conflict"] != want:
            cleared.append("%s -> %s: conflict %s -> %s"
                           % (e["from_name"], e["to_hub_name"],
                              e["geography_selfdeclaration_conflict"], want))
            e["geography_selfdeclaration_conflict"] = want
    return cleared


# ------------------------------------------------------------------ checks

def check_no_self_edge(rows):
    bad = []
    for r in rows:
        if r.get("from_cedar_uid") and r["from_cedar_uid"] == r.get("to_hub_cedar_uid"):
            bad.append("SELF-EDGE: %s serves itself (%s)"
                       % (r.get("edge_id"), r["from_cedar_uid"]))
    return bad


def check_conflict_flag_is_earned(rows):
    """A conflict flag with nothing to conflict with is a stale assertion."""
    strong = defaultdict(set)
    for r in rows:
        if int(r["tier_rank"]) < 5:
            strong[norm(r["from_name"])].add(r["to_hub_cedar_uid"])
    bad = []
    for r in rows:
        if r.get("geography_selfdeclaration_conflict") != "Y":
            continue
        peers = strong.get(norm(r["from_name"]), set())
        if not peers or r["to_hub_cedar_uid"] in peers:
            bad.append("UNEARNED CONFLICT FLAG on edge %s: no stronger-tier "
                       "edge from %r names a different hub"
                       % (r.get("edge_id"), r.get("from_name")))
    return bad


def check_registered_with_adopted(rows):
    """The ADR-014 amendment landed, in the data and not only in the prose."""
    bad = []
    for r in rows:
        if r.get("tier") == "registered_with" and r.get("tier_is_adr014") != "Y":
            bad.append("ADR-014 AMENDMENT NOT APPLIED: edge %s is "
                       "`registered_with` but tier_is_adr014=%r"
                       % (r.get("edge_id"), r.get("tier_is_adr014")))
    return bad


def self_test_852_checkers():
    """A check that cannot fail is not a check. Three synthetic violations."""
    fails = []

    v = [{"edge_id": "SYN-SELF", "from_cedar_uid": "CE-X", "to_hub_cedar_uid": "CE-X"}]
    if not check_no_self_edge(v):
        fails.append("SELF-TEST FAILED: check_no_self_edge() did not fire on a "
                     "synthetic self-edge.")
    if check_no_self_edge([{"edge_id": "SYN-OK", "from_cedar_uid": "CE-X",
                            "to_hub_cedar_uid": "CE-Y"}]):
        fails.append("SELF-TEST FAILED: check_no_self_edge() fired on a valid edge.")

    v = [{"edge_id": "SYN-CONF", "from_name": "Ghost School", "tier_rank": "5",
          "to_hub_cedar_uid": "CE-A", "geography_selfdeclaration_conflict": "Y"}]
    if not check_conflict_flag_is_earned(v):
        fails.append("SELF-TEST FAILED: check_conflict_flag_is_earned() did not "
                     "fire on a conflict flag with no opposing edge.")
    ok = [{"edge_id": "SYN-C1", "from_name": "Ghost School", "tier_rank": "2",
           "to_hub_cedar_uid": "CE-B", "geography_selfdeclaration_conflict": "N"},
          {"edge_id": "SYN-C2", "from_name": "Ghost School", "tier_rank": "5",
           "to_hub_cedar_uid": "CE-A", "geography_selfdeclaration_conflict": "Y"}]
    if check_conflict_flag_is_earned(ok):
        fails.append("SELF-TEST FAILED: check_conflict_flag_is_earned() fired on "
                     "a genuinely conflicting pair.")

    v = [{"edge_id": "SYN-REG", "tier": "registered_with", "tier_is_adr014": "N"}]
    if not check_registered_with_adopted(v):
        fails.append("SELF-TEST FAILED: check_registered_with_adopted() did not "
                     "fire on an unadopted registered_with edge.")
    if check_registered_with_adopted([{"edge_id": "SYN-REG2",
                                       "tier": "registered_with",
                                       "tier_is_adr014": "Y"}]):
        fails.append("SELF-TEST FAILED: check_registered_with_adopted() fired on "
                     "an adopted edge.")
    return fails


def run_all_checks_852(rows, hubs, columns):
    fails = M.run_all_checks(rows, hubs, columns)
    fails += check_no_self_edge(rows)
    fails += check_conflict_flag_is_earned(rows)
    fails += check_registered_with_adopted(rows)
    fails += self_test_852_checkers()
    return fails


# ------------------------------------------------------------------ report

def unresolved_universe():
    """Measured with csv.reader, and NOT over the backup files.

    851's version globs `data/clean/*.csv`, which now also matches
    `native_owned_businesses.bak_2026-09-02_010526.csv` and its twin, written
    by a concurrent workstream. That triple-counted 2,389 rows and reported
    the universe as 12,916 instead of 8,138, deflating its own headline.
    """
    import glob
    per, total = {}, 0
    for p in sorted(glob.glob(os.path.join(ROOT, "data", "clean", "*.csv"))):
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


def rows_converted(edges):
    """Row-grain conversion of data/clean record_scope=unresolved rows."""
    eins, nobs = set(), set()
    for e in edges:
        if e["converts_unresolved_row"] != "Y":
            continue
        if e["from_source_table"] == "np_mission":
            eins.add(e["from_record_key"])
        elif e["from_source_table"] == "native_owned_businesses":
            nobs.add(e["from_record_key"])
    n = len(nobs)
    if os.path.exists(M.SCHEDC):
        for r in read_csv(M.SCHEDC):
            if r["record_scope"] == "unresolved" and r["ein"] in eins:
                n += 1
    return n


def column_diff(path, new_cols):
    if not os.path.exists(path):
        return "new file"
    with open(path, encoding="utf-8-sig", newline="") as fh:
        old = next(csv.reader(fh))
    gained = [c for c in new_cols if c not in old]
    lost = [c for c in old if c not in new_cols]
    return "gained %r, lost %r" % (gained, lost)


# ------------------------------------------------------------------ main

def main(argv):
    mode = argv[1] if len(argv) > 1 else "build"

    spine = read_csv(M.SPINE)
    hubs = {r["cedar_uid"]: r for r in spine
            if r["entity_class"] in M.HUB_CLASSES and r["cedar_uid"]}
    spine_by_uid = {r["cedar_uid"]: r for r in spine}

    if mode == "verify":
        rows = read_csv(M.EDGES_OUT)
        with open(M.EDGES_OUT, encoding="utf-8-sig", newline="") as fh:
            columns = next(csv.reader(fh))
        fails = run_all_checks_852(rows, hubs, columns)
        print("852 verify: %d edges, %d invariant failures" % (len(rows), len(fails)))
        for f in fails:
            print("  FAIL " + f)
        if fails:
            return 1
        print("852 verify: OK - 851's rules 1/2/3 hold, plus no self-edge, no "
              "unearned conflict flag, and the registered_with amendment is "
              "applied. All three new detectors were proven to fire on "
              "synthetic violations.")
        return 0

    M.HANDLE2UID = {r["tribe_id"]: r["cedar_uid"] for r in spine if r.get("tribe_id")}
    M.HANDLE2UID.update({r["cedar_entity_id"]: r["cedar_uid"]
                         for r in spine if r.get("cedar_entity_id")})
    global _CONSTITUENCY
    _CONSTITUENCY = {r["cedar_uid"]: (r["canonical_name"], r.get("state") or "", None)
                     for r in spine
                     if r["entity_class"] == "Federal-level constituency entity"}

    idx = M.HubIndex(spine)
    rs = Resolver(idx, hubs)
    b = M.Build()

    # ---- 851's sources, unchanged --------------------------------------
    M.src_charter_sentences(b, hubs, idx)
    M.src_spine_serves_text(b, hubs, idx, spine)
    M.src_institution_names(b, hubs, idx)
    name_hub = M.src_bie_schools(b, hubs, idx)
    M.src_geocode_aiannh(b, hubs, idx, name_hub or {})
    M.src_native_owned_businesses(b, hubs, idx)
    M.src_nonprofit_missions(b, hubs, idx)
    M.src_refuse_wrong_instrument(b)
    n851 = len(b.edges)

    # ---- 852's sources --------------------------------------------------
    slice_by_name = {}
    if os.path.exists(M.SLICE):
        for r in read_csv(M.SLICE):
            slice_by_name[norm(r["canonical_name"])] = r

    src_nob_unlinked_authority(b, hubs, rs)
    src_aihec_charter_profiles(b, hubs, rs, slice_by_name)
    holders = src_ihs_compact_programmes(b, hubs, rs)
    src_ihs_uio_register(b)
    src_org_membership_rosters(b, hubs, rs, holders, spine_by_uid)
    src_990_filer_name_probe(b, hubs, rs)

    # ---- de-duplicate, then adjudicate ---------------------------------
    best = {}
    for e in b.edges:
        k = e["edge_id"]
        if k not in best or e["tier_rank"] < best[k]["tier_rank"]:
            best[k] = e
    edges = list(best.values())

    edges, ruling_lines = adjudicate_bie_navajo_field(b, edges, hubs)
    flag_changes = reconcile_conflict_flags(edges)

    edges.sort(key=lambda e: (e["tier_rank"], e["to_hub_name"], e["from_name"]))

    fails = run_all_checks_852(edges, hubs, M.EDGE_COLUMNS)
    if fails:
        print("BUILD ABORTED - invariants broken, nothing written:")
        for f in fails:
            print("  FAIL " + f)
        return 1

    # ---- write, with backup and a column diff --------------------------
    for path, cols, rows in [(M.EDGES_OUT, M.EDGE_COLUMNS, edges),
                             (M.REFUSALS_OUT, M.REFUSAL_COLUMNS, b.refusals)]:
        print("column diff for %s: %s"
              % (os.path.basename(path), column_diff(path, cols)))
        if os.path.exists(path):
            bak = path + ".bak_%s_pre852" % BUILT_DATE
            with open(path, "rb") as s, open(bak, "wb") as d:
                d.write(s.read())
            print("backed up %s -> %s" % (os.path.basename(path),
                                          os.path.basename(bak)))
        with open(path, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        print("wrote %s (%d rows, %d columns)" % (path, len(rows), len(cols)))

    # ---- report ---------------------------------------------------------
    total, per = unresolved_universe()
    print("\n=== ADR-014 CONSTELLATION, EXTENDED (852) ===")
    print("unresolved universe measured now (backups excluded): %d rows across "
          "%d clean tables" % (total, len(per)))
    for k, v in sorted(per.items(), key=lambda x: -x[1]):
        print("    %6d  %s" % (v, k))

    print("\nedges written: %d   (851's sources contributed %d before dedup)"
          % (len(edges), n851))
    by_tier = Counter(e["tier"] for e in edges)
    for t in sorted(by_tier, key=lambda t: M.TIER_RANK[t]):
        flag = "" if t in M.ADR014_TIERS else "   <-- NOT AN ADR-014 TIER"
        print("    %-24s %6d   (rank %d)%s"
              % (t, by_tier[t], M.TIER_RANK[t], flag))

    src = Counter(e["from_source_table"] for e in edges)
    print("\nedges by source table:")
    for k, v in src.most_common():
        print("    %6d  %s" % (v, k))

    conv = rows_converted(edges)
    print("\nHEADLINE - unresolved ROWS converted: %d of %d (%.1f%%)"
          % (conv, total, 100.0 * conv / max(total, 1)))

    print("\ndistinct entities on the `from` side: %d   distinct hubs: %d"
          % (len({(e["from_source_table"], e["from_record_key"] or e["from_cedar_uid"]
                   or e["from_name"]) for e in edges}),
             len({e["to_hub_cedar_uid"] for e in edges})))

    print("\nrefusals written: %d" % len(b.refusals))
    for k, v in Counter(r["refusal_reason"] for r in b.refusals).most_common(25):
        print("    %6d  %s" % (v, k))

    print("\n--- RULING 852-1, the BIE Navajo_Operation audit ---")
    for l in ruling_lines:
        print("    " + l)
    print("\n--- conflict flags recomputed ---")
    for l in flag_changes or ["    (none changed)"]:
        print("    " + l)
    conf = [e for e in edges if e["geography_selfdeclaration_conflict"] == "Y"]
    print("geography-vs-self-declaration conflicts surviving: %d" % len(conf))
    for e in conf:
        print("    %s -> %s (%s)" % (e["from_name"], e["to_hub_name"], e["tier"]))

    corr = [e for e in edges if M.NEVER_ALONE in (e["corroborating_tiers"] or "")]
    print("\nedges corroborated by %s: %d (standing alone on it: 0, enforced)"
          % (M.NEVER_ALONE, len(corr)))

    for n in b.notes:
        print("NOTE: " + n)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
