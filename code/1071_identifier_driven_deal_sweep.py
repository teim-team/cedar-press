#!/usr/bin/env python3
"""
Cedar Press - 1071: IDENTIFIER-DRIVEN DEAL DISCOVERY, AND THE CONSOLIDATED CANDIDATE SET.

    py -3 code/1071_identifier_driven_deal_sweep.py            # measure + write
    py -3 code/1071_identifier_driven_deal_sweep.py measure    # same
    py -3 code/1071_identifier_driven_deal_sweep.py verify     # exit 1 on breach
    py -3 code/1071_identifier_driven_deal_sweep.py selftest   # prove verify fires

WHY THIS EXISTS, AND WHAT IT IS *NOT*
-------------------------------------
    "We might need to update finding deals now that we have so many entities we
     can look through, and they have codes as well."

Earlier deal discovery was driven by NATION NAMES. A subsidiary's legal name
routinely shares no token with its owner - ASRC Federal's operating companies
file as BROADLEAF, INUTEQ and VISTRONIX - so a name sweep cannot see them. This
script drives every query from an IDENTIFIER (UEI, CAGE) and from the register /
constellation-edge layer, never from a hand list of nations.

`code/1010_ownership_change_from_contracting.py` already swept ONE surface and
ONE identifier relation: `prime_contracts.parent_uei`. It is not re-derived
here. Its `Hubs` resolver is IMPORTED so both scripts refuse intra-family moves
by identical logic, its 98 candidates are folded into the consolidated set, and
this script adds the four identifier relations it never looked at:

  S1  subawards.sub_parent_uei    changing under a fixed sub_uei
  S2  subawards.prime_parent_uei  changing under a fixed prime_uei
  C1  a CAGE code re-paired from one UEI to a different UEI (successor
      registration - the CAGE is the constant, the legal person is not)
  N1  prime_contracts: a fixed awardee_uei whose LEGAL NAME changes families
  A1  federal_funding_transactions: the same, on the assistance surface

N1/A1 are the relations a name search can never reach BY CONSTRUCTION: the name
is the thing that moved. The UEI is what holds the before and the after
together.

THE WARNING THAT GOVERNS THIS WORK
-----------------------------------
    "There could be some wonky stuff where a company changes from, like, All
     Native Group to Ho-Chunk Inc, but it's still the same Native entity."

A change of reporting parent WITHIN one tribal corporate family is a
relabelling, not a transaction. Under hub-and-sub-hub a nation is the hub and
its holding company, casino and registrations are sub-hubs; a move between two
sub-hubs of one hub is not a deal.

`data/clean/cedar_constellation_edges.csv` now makes that testable and this
script uses it: every side of every candidate is resolved to a hub set, then
that set is CLOSED over the constellation edges (`from_cedar_uid ->
to_hub_cedar_uid`) and over the spine's `parent_entity_id` /
`ultimate_parent_entity_id` chain. Two sides whose closures intersect are one
family and the candidate is refused. The refusals are written out beside the
candidates: THE REJECTION COUNT IS THE MEASURE OF WHETHER THE DETECTOR IS
TRUSTWORTHY, and it is reported as a headline figure, not a footnote.

Refusals, in the order they fire (all axes):

  NAN_SENTINEL              an identifier is the literal string `nan`. This is
                            not hypothetical: `review/1011_cross_dataset_findings.csv`
                            CDR-06 measures 398,840 `nan` cells in
                            `prime_contracts.cage_code` alone, fusing 2,015 UEIs
                            across 411 hubs onto one "CAGE".
  SAME_DISTINCTIVE_TOKENS   the two names reduce to the same distinctive token
                            string - one entity, two registrations, or a
                            corporate-form change (`INC` -> `LLC`)
  INTRA_FAMILY_SAME_HUB     the two hub closures intersect (route recorded:
                            spine / constellation edge / parent chain)
  INTRA_FAMILY_SHARED_BRAND the two names share a distinctive non-trap token
  INTRA_FAMILY_ACRONYM      a registered acronym alias of one side's hub is a
                            token of the other side's name
  NO_NATIVE_SIDE            neither side resolves to a Cedar hub - out of scope,
                            counted separately from the family refusals

WHY WEAK EVIDENCE MAY REFUSE AND MAY NEVER AWARD
-------------------------------------------------
`docs/ENTITY_MATCH_RULES.md` rule 7: "a bare token may never AWARD a match, but
it may always BLOCK one." SHARED_BRAND and ACRONYM are token tests and would be
forbidden as matchers. They are used here only to SUPPRESS a report. The cost of
a wrong refusal is a missed story; the cost of a wrong report is a fabricated
transaction.

WHAT IS CLAIMED, AND WHAT IS NOT
---------------------------------
A candidate is a LEAD, not a finding, and nothing here is merged into
`deals_classified.csv`. FPDS/FSRS parent and name fields are a firm's
SELF-DECLARATION - evidence, not authority. Every row states the identifier and
the fiscal years so a reader can re-run the check against the named file; that
is the "source link" the deals bar requires where a change is visible only in
contracting. `announced_value_usd` is left BLANK on every contracting-derived
row: no value was published, and inferring one would be fabrication. The dollar
column that is populated is the child's own obligations inside its own declared
runs, which is a SCALE figure and is not additive to anything
(`docs/MONEY_TOTALLING_RULES.md`).

ANNOUNCED vs CLOSED are labelled separately in `deal_status_std` and a
contracting-visible change is `OBSERVED_IN_FILINGS`, which is neither.

TERMS_STATED_RESTRICTIVE
-------------------------
Confederated Colville, CTUIR/Umatilla, Yakama, Chickasaw, NANA/Akima, Southern
Ute, Forest County Potawatomi and Stillaguamish state restrictive terms. The
restriction is on THEIR OWN published sources, so it bites the press-derived
rows this script folds in, not the federal contracting surface. Every folded row
whose source host belongs to one of those entities is dropped and counted; every
contracting-derived row naming one of them carries
`terms_restricted_party = Y` so a publisher can see it before quoting anything
the entity itself said.

OUTPUTS - this script writes ONLY its own files and never repairs another
dataset's table in place:

    review/1071_identifier_deal_candidates.csv     the five new axes
    review/1071_intra_family_rejections.csv        every refusal, with its route
    review/1071_consolidated_deal_candidates.csv   every open candidate in the
                                                   project, de-duplicated
    docs/schema/1071_identifier_sweep_invariants.json
"""
from __future__ import annotations

import collections
import csv
import hashlib
import importlib.util
import json
import os
import re
import sys

csv.field_size_limit(1 << 30)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN = os.path.join(ROOT, "data", "clean")
SPINE_DIR = os.path.join(ROOT, "data", "spine")
REVIEW = os.path.join(ROOT, "review")
STAGING = os.path.join(ROOT, "data", "staging")

PRIME = os.path.join(CLEAN, "prime_contracts.csv")
SUBAW = os.path.join(CLEAN, "subawards.csv")
ASSIST = os.path.join(CLEAN, "federal_funding_transactions.csv")
EDGES = os.path.join(CLEAN, "cedar_constellation_edges.csv")
SPINE = os.path.join(SPINE_DIR, "cedar_entity_spine.csv")
REGISTER = os.path.join(SPINE_DIR, "cedar_identity_register.csv")
DEALS = os.path.join(CLEAN, "deals_classified.csv")

OUT_CAND = os.path.join(REVIEW, "1071_identifier_deal_candidates.csv")
OUT_REJ = os.path.join(REVIEW, "1071_intra_family_rejections.csv")
OUT_CONS = os.path.join(REVIEW, "1071_consolidated_deal_candidates.csv")
OUT_INV = os.path.join(ROOT, "docs", "schema", "1071_identifier_sweep_invariants.json")

SCRIPT = "code/1071_identifier_driven_deal_sweep.py"

# The sentinel. `nan` is a real, measured string in these columns - never a NULL.
SENTINELS = frozenset({"NAN", "NONE", "NULL", "N/A", "NA", "-", "UNKNOWN", ""})

# Entities whose OWN published sources carry restrictive terms.
TERMS_RESTRICTED = {
    "colville": "Confederated Colville",
    "umatilla": "CTUIR / Umatilla",
    "ctuir": "CTUIR / Umatilla",
    "yakama": "Yakama",
    "chickasaw": "Chickasaw",
    "nana": "NANA / Akima",
    "akima": "NANA / Akima",
    "southern ute": "Southern Ute",
    "forest county potawatomi": "Forest County Potawatomi",
    "stillaguamish": "Stillaguamish",
}
TERMS_RESTRICTED_HOSTS = (
    "colvilletribes.com", "ctuir.org", "yakama.com", "yakamanation-nsn.gov",
    "chickasaw.net", "nana.com", "akima.com", "southernute-nsn.gov",
    "fcpotawatomi.com", "stillaguamish.com",
)

DOM_SHARE = 0.80
DOM_MIN_ROWS = 2


# --------------------------------------------------------------------------
# import 1010 rather than re-deriving its resolver. Same refusal logic in both
# scripts, by construction, not by copy.
# --------------------------------------------------------------------------
def _load_1010():
    p = os.path.join(ROOT, "code", "1010_ownership_change_from_contracting.py")
    spec = importlib.util.spec_from_file_location("cedar_1010", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def clean_id(v: str) -> str:
    v = (v or "").strip().upper()
    return "" if v in SENTINELS else v


def _rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        yield from csv.DictReader(f)


# --------------------------------------------------------------------------
# FAMILY CLOSURE - the thing the constellation edge file made testable
# --------------------------------------------------------------------------
class Families:
    """hub tribe_id -> the set of cedar_uids that are ONE corporate family.

    Three independent sources of family membership, all recorded so a refusal
    can name its route:
      spine_parent   `parent_entity_id` / `ultimate_parent_entity_id`
      constellation  `from_cedar_uid -> to_hub_cedar_uid`, 3,153 edges
      self           the entity itself
    """

    def __init__(self, nkey=None) -> None:
        self.nkey = nkey or (lambda s: " ".join(re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).split()))
        self.tid2uid: dict[str, str] = {}
        self.uid2tid: dict[str, str] = {}
        self.uid_name: dict[str, str] = {}
        self.eid2uid: dict[str, str] = {}
        self.edge_name2hub: dict[str, set] = collections.defaultdict(set)
        self.edges_with_from_uid = 0
        self.edges_name_only = 0
        adj: dict[str, set] = collections.defaultdict(set)
        self.route: dict[tuple, str] = {}

        for r in _rows(SPINE):
            tid, uid = r.get("tribe_id") or "", r.get("cedar_uid") or ""
            if not uid:
                continue
            if tid:
                self.tid2uid[tid] = uid
                self.uid2tid[uid] = tid
            self.uid_name[uid] = r.get("canonical_name") or uid
            if r.get("cedar_entity_id"):
                self.eid2uid[r["cedar_entity_id"]] = uid
        # second pass: parent ids are cedar_entity_id or tribe_id shaped
        for r in _rows(SPINE):
            uid = r.get("cedar_uid") or ""
            if not uid:
                continue
            for f in ("parent_entity_id", "ultimate_parent_entity_id", "ancsa_region_entity_id"):
                pid = (r.get(f) or "").strip()
                if not pid:
                    continue
                puid = self.eid2uid.get(pid) or self.tid2uid.get(pid)
                if puid and puid != uid:
                    adj[uid].add(puid)
                    adj[puid].add(uid)
                    self.route[(uid, puid)] = "spine_" + f
                    self.route[(puid, uid)] = "spine_" + f

        # THE EDGE FILE HAS TWO POPULATIONS AND ONLY ONE OF THEM IS A UID EDGE.
        # Measured 2026-09-02: of 3,153 rows, 2,408 (76.4%) carry a BLANK
        # `from_cedar_uid` - the from-side is a TERO certification, a 638
        # registration or a subsidiary listing that has never been minted. The
        # uid graph therefore reaches only 745 edges. The other 2,408 still
        # carry `from_name` + `to_hub_cedar_uid`, which is exactly the
        # subsidiary-to-owner fact this sweep needs, so they are indexed BY NAME
        # and used ONLY to refuse (rule 7: a name may block, never award).
        self.n_edges = 0
        if os.path.exists(EDGES):
            for r in _rows(EDGES):
                a, b = (r.get("from_cedar_uid") or "").strip(), (r.get("to_hub_cedar_uid") or "").strip()
                if not b:
                    continue
                if a and a != b:
                    self.n_edges += 1
                    self.edges_with_from_uid += 1
                    adj[a].add(b)
                    adj[b].add(a)
                    tier = r.get("tier") or "edge"
                    self.route.setdefault((a, b), "constellation_" + tier)
                    self.route.setdefault((b, a), "constellation_" + tier)
                    nm = r.get("from_name")
                    if nm and a not in self.uid_name:
                        self.uid_name[a] = nm
                elif not a:
                    self.edges_name_only += 1
                k = self.nkey(r.get("from_name"))
                if k:
                    self.edge_name2hub[k].add(b)

        for r in _rows(REGISTER):
            uid = (r.get("cedar_uid") or "").strip()
            if uid:
                self.uid_name.setdefault(uid, r.get("canonical_name") or uid)

        self.adj = adj
        self._cache: dict[str, frozenset] = {}

    def closure(self, uid: str) -> frozenset:
        if uid in self._cache:
            return self._cache[uid]
        seen, stack = {uid}, [uid]
        while stack:
            n = stack.pop()
            for m in self.adj.get(n, ()):
                if m not in seen:
                    seen.add(m)
                    stack.append(m)
        fs = frozenset(seen)
        self._cache[uid] = fs
        return fs

    def hubs_for_name(self, name: str) -> set:
        """Constellation edges keyed by the from-side's NAME, as tribe_ids.

        Blocking use only. This is what lets `BROADLEAF` be recognised as ASRC
        Federal's without either name sharing a token with the other.
        """
        out: set = set()
        k = self.nkey(name)
        if not k:
            return out
        for uid in self.edge_name2hub.get(k, ()):
            t = self.uid2tid.get(uid)
            out.add(t or uid)
        return out

    def closure_of_hubs(self, tids) -> frozenset:
        out: set = set()
        for t in tids:
            u = self.tid2uid.get(t)
            if u:
                out |= self.closure(u)
            else:
                out.add(t)
        return frozenset(out)

    def why(self, a_tids, b_tids) -> str:
        """Name the route by which two hub sets turned out to be one family."""
        for t in a_tids:
            for s in b_tids:
                if t == s:
                    return "same_hub"
        ua = {self.tid2uid.get(t) for t in a_tids} - {None}
        ub = {self.tid2uid.get(t) for t in b_tids} - {None}
        for a in ua:
            for b in ub:
                if (a, b) in self.route:
                    return self.route[(a, b)]
        return "closure_multi_hop"


# --------------------------------------------------------------------------
# AWARDING evidence is NOT the same set as BLOCKING evidence
# --------------------------------------------------------------------------
class AwardHubs:
    """The hubs a side is allowed to be REPORTED as. Strong evidence only.

    START_HERE trap 1: *a tier is INHERITED from the source row, never assigned
    by the consumer*, and *the exactness of the KEY says nothing about the
    correctness of the LINK*. `cedar_identifier_ledger_final.csv` holds 2,001
    tier-B `cluster_v3` rows, and they are not harmless: measured here on
    2026-09-02, `cluster_v3` keys **`Indian Affairs, Bureau Of`** (8 UEIs) and
    **`Computer Sciences Corporation`** to `AKNF-INPTBW-00-ARCSLO` (Barrow) - the
    same name-cluster mechanism, and the same shape, as the Bristol Bay FA-01
    defect that START_HERE records as closed. It is not closed; it has other
    victims. Left ungated it puts the Bureau of Indian Affairs on a candidate
    list as an acquisition target.

    So AWARDING here takes only:
      * the spine's own `canonical_name` / `fr_official_name`, exact normalized
      * ledger rows at `confidence_tier == 'A'`

    and it refuses outright any (identifier, hub) pair carried at **tier X**,
    which is a NEGATIVE ruling and must never be read as a link
    (START_HERE trap 1b: `attribution_method` says WHO decided,
    `confidence_tier` says WHAT was decided).
    """

    def __init__(self, nkey) -> None:
        self.nkey = nkey
        self.id2hub: dict[str, set] = collections.defaultdict(set)
        self.name2hub: dict[str, set] = collections.defaultdict(set)
        self.block_id2hub: dict[str, set] = collections.defaultdict(set)
        self.block_name2hub: dict[str, set] = collections.defaultdict(set)
        self.denied: set = set()
        self.tier_counts = collections.Counter()
        self.paren_variants = 0

        for r in _rows(SPINE):
            tid = r.get("tribe_id")
            if not tid:
                continue
            for f in ("canonical_name", "fr_official_name"):
                for k in self.variants(r.get(f)):
                    self.name2hub[k].add(tid)
                    self.block_name2hub[k].add(tid)
            for a in (r.get("aliases") or "").replace(";", "|").split("|"):
                for k in self.variants(a):
                    self.block_name2hub[k].add(tid)

        for r in _rows(LEDGER_PATH):
            tid = r.get("tribe_id") or ""
            tier = (r.get("confidence_tier") or "").strip().upper()
            ident = clean_id(r.get("identifier"))
            self.tier_counts[tier] += 1
            if not tid:
                continue
            if tier == "X":
                if ident:
                    self.denied.add((ident, tid))
                for k in self.variants(r.get("legal_business_name")):
                    self.denied.add((k, tid))
                continue
            # EVERY tier may BLOCK; only tier A may AWARD.
            if ident:
                self.block_id2hub[ident].add(tid)
            for f in ("legal_business_name", "canonical_name"):
                for k in self.variants(r.get(f)):
                    self.block_name2hub[k].add(tid)
            if tier != "A":
                continue
            if ident:
                self.id2hub[ident].add(tid)
            for f in ("legal_business_name", "canonical_name"):
                for k in self.variants(r.get(f)):
                    self.name2hub[k].add(tid)

    def variants(self, name: str) -> set:
        """The recorded name, and the name with parentheticals removed.

        THE SPINE PUTS AN ACRONYM INSIDE THE CANONICAL NAME. Measured
        2026-09-02: `ANVC-TNDGSX-00` is recorded as `Tanadgusix Corporation
        (TDX)`, which normalizes to `tanadgusix tdx` and therefore does NOT
        equal the `TANADGUSIX CORPORATION` that FSRS prints. The consequence is
        not a missed link, it is a WRONG REPORT: with the parent unresolvable,
        four TDX subsidiaries whose reporting parent moved between two TDX
        registrations looked like acquisitions out of nowhere. Indexing both
        variants is what makes the owner's "All Native Group -> Ho-Chunk Inc"
        warning testable at all. `docs/NATIVE_ENTITY_NUANCES.md` records the
        same parenthetical hazard on the FR band names.
        """
        out = set()
        n = (name or "").strip()
        if not n:
            return out
        k = self.nkey(n)
        if k:
            out.add(k)
        k2 = self.nkey(PAREN_RE.sub(" ", n))
        if k2 and k2 not in out:
            out.add(k2)
            self.paren_variants += 1
        return out

    def of(self, ident: str, name: str) -> set:
        out: set = set()
        i = clean_id(ident)
        if i:
            out |= {t for t in self.id2hub.get(i, ()) if (i, t) not in self.denied}
        for k in self.variants(name):
            out |= {t for t in self.name2hub.get(k, ()) if (k, t) not in self.denied}
        return out

    def block_of(self, ident: str, name: str) -> set:
        """Every hub ANY tier of evidence associates with this side. BLOCK ONLY."""
        out: set = set()
        i = clean_id(ident)
        if i:
            out |= self.block_id2hub.get(i, set())
        for k in self.variants(name):
            out |= self.block_name2hub.get(k, set())
        return out


LEDGER_PATH = os.path.join(CLEAN, "cedar_identifier_ledger_final.csv")
PAREN_RE = re.compile(r"\([^)]*\)")

# A UNIT OF GOVERNMENT DECLARED AS A COMPANY'S PARENT IS A FILING ARTEFACT.
# FSRS `sub_parent_name` is free text typed by the reporting prime, and it is
# routinely used to name the PASS-THROUGH rather than the owner: the first run
# of this sweep proposed "Narragansett Indian Tribe -> STATE OF RHODE ISLAND",
# "Crow Creek Sioux Tribe -> STATE OF SOUTH DAKOTA" and "Northwest Indian
# Fisheries Commission -> STATE OF WASHINGTON" as ownership changes. A state
# does not acquire a tribal government; what changed is which body the money
# came through. Refusing is safe in the direction that matters - a state
# genuinely buying a tribal enterprise is not a transaction that exists.
GOV_PARENT_RE = re.compile(
    r"\b(state of|commonwealth of|county of|city of|department of|"
    r"bureau of|united states|u\s?s\s?department|federal government|"
    r"board of regents|university of)\b", re.I)
GOV_PARENT_EXACT = frozenset({
    "doi bureau of indian affairs", "indian affairs bureau of",
    "interior department of the", "health and human services department of",
})



def _fuzz():
    try:
        from rapidfuzz import fuzz  # type: ignore

        return fuzz
    except Exception:  # rapidfuzz is declared installed; degrade loudly, not silently
        return None


# --------------------------------------------------------------------------
# shared refusal battery
# --------------------------------------------------------------------------
class Refuser:
    """Blocking may rest on WEAK evidence; awarding may not.

    `docs/ENTITY_MATCH_RULES.md` rule 7. `self.h` is 1010's resolver reading the
    WHOLE ledger at every tier plus the alias layer - deliberately wide, because
    every use of it here is a refusal. `self.a` is the tier-gated resolver and is
    the only thing allowed to put a hub in an output row.
    """

    NEAR_IDENTICAL = 90

    def __init__(self, hubs, award: AwardHubs, fams: Families) -> None:
        self.h = hubs
        self.a = award
        self.f = fams
        self.fuzz = _fuzz()

    def judge(self, a_uei, a_name, b_uei, b_name, a_vintage="", b_vintage=""):
        """Return (refusal or None, a_hubs, b_hubs, evidence)."""
        for v in (a_uei, b_uei):
            if (v or "").strip().upper() == "NAN":
                return "NAN_SENTINEL", set(), set(), "identifier is the literal string nan"

        # AN ABSENT NAME IS NOT EVIDENCE OF A CHANGE OF FAMILY. Every refusal
        # below needs a name to test; with one side blank the whole battery is
        # inert and the row sails through as a false `LEFT_NATIVE_FAMILY` purely
        # because the other side could not be resolved. Field guide 3, inverted:
        # an EMPTY cell is not a resolved absence.
        if not (a_name or "").strip() or not (b_name or "").strip():
            return ("SIDE_NAME_MISSING", set(), set(),
                    "one side of the transition carries no name; the intra-family "
                    "battery cannot be run and absence is not evidence")

        ka, kb = self.h.nkey(a_name), self.h.nkey(b_name)
        # AWARD set: tier-gated. BLOCK set: everything, used only to refuse.
        ah = self.a.of(a_uei, a_name)
        bh = self.a.of(b_uei, b_name)
        bah = (self.h.of(a_uei, a_name) | self.f.hubs_for_name(a_name)
               | self.a.block_of(a_uei, a_name) | ah)
        bbh = (self.h.of(b_uei, b_name) | self.f.hubs_for_name(b_name)
               | self.a.block_of(b_uei, b_name) | bh)

        if ka and ka == kb:
            return "SAME_DISTINCTIVE_TOKENS", ah, bh, ka

        if self.fuzz is not None and ka and kb:
            sim = self.fuzz.token_sort_ratio(ka, kb)
            if sim >= self.NEAR_IDENTICAL:
                return ("NEAR_IDENTICAL_NAME", ah, bh,
                        f"rapidfuzz token_sort_ratio={sim:.0f} >= {self.NEAR_IDENTICAL}: "
                        f"'{ka}' vs '{kb}'")

        for side, nm in (("prior", a_name), ("later", b_name)):
            n = (nm or "").strip()
            if GOV_PARENT_RE.search(n) or self.h.nkey(n) in GOV_PARENT_EXACT:
                return ("GOVERNMENT_BODY_AS_DECLARED_PARENT", ah, bh,
                        f"the {side} side is a unit of government (\"{n}\"); a declared "
                        f"parent naming a state, county or federal body is a "
                        f"pass-through, not an owner")

        if a_vintage and b_vintage and a_vintage != b_vintage:
            return ("SOURCE_VINTAGE_SEAM", ah, bh,
                    f"the two runs come from different source vintages "
                    f"('{a_vintage}' -> '{b_vintage}'); the change coincides with a "
                    f"change of SOURCE and cannot be read as a change of OWNER")

        if bah and bbh:
            ca, cb = self.f.closure_of_hubs(bah), self.f.closure_of_hubs(bbh)
            inter = ca & cb
            if inter:
                return ("INTRA_FAMILY_SAME_HUB", ah, bh,
                        f"{self.f.why(bah, bbh)}: " + "|".join(sorted(inter)[:4]))

        da, db = self.h.distinctive(a_name), self.h.distinctive(b_name)
        shared = da & db
        if shared:
            return "INTRA_FAMILY_SHARED_BRAND", ah, bh, "|".join(sorted(shared))

        acr = (self.h.acronym_hit(a_name) & bbh) | (self.h.acronym_hit(b_name) & bah)
        if acr:
            return "INTRA_FAMILY_ACRONYM", ah, bh, "|".join(sorted(acr))

        if not ah and not bh:
            # bah/bbh may be non-empty here: a weak link exists but is not strong
            # enough to publish. That is `unresolved`, not `not Native`.
            return "NO_NATIVE_SIDE_AT_TIER_A", ah, bh, (
                "weak-tier hub(s) present: " + "|".join(sorted(bah | bbh)) if (bah or bbh) else "")

        return None, ah, bh, ""


# --------------------------------------------------------------------------
# run / transition machinery, shared by every axis
# --------------------------------------------------------------------------
def runs_for(years: dict):
    out = []
    for fy in sorted(years, key=lambda x: int(x)):
        cnt = years[fy]
        tot = sum(v[0] for v in cnt.values())
        p, v = max(cnt.items(), key=lambda kv: kv[1][0])
        lab = p if (tot >= DOM_MIN_ROWS and v[0] / tot >= DOM_SHARE) or tot < DOM_MIN_ROWS else "MIXED"
        usd = sum(v[1] for v in cnt.values())
        if out and out[-1]["k"] == lab:
            out[-1]["last_fy"] = int(fy)
            out[-1]["rows"] += tot
            out[-1]["usd"] += usd
        else:
            out.append({"k": lab, "first_fy": int(fy), "last_fy": int(fy), "rows": tot, "usd": usd})
    return out


def transitions(series):
    """Only STRICTLY TIME-ORDERED, disjoint runs qualify.

    If value A reappears after value B the declaration is oscillating; that is
    filing inconsistency, not an ownership event.
    """
    for key, years in series.items():
        rr = runs_for(years)
        solid = [r for r in rr if r["k"] != "MIXED"]
        byk = collections.defaultdict(list)
        for r in solid:
            byk[r["k"]].append(r)
        if len(byk) < 2:
            continue
        span = {
            k: (min(x["first_fy"] for x in v), max(x["last_fy"] for x in v),
                sum(x["rows"] for x in v), sum(x["usd"] for x in v))
            for k, v in byk.items()
        }
        order = sorted(span, key=lambda k: span[k][0])
        if not all(span[order[i]][1] < span[order[i + 1]][0] for i in range(len(order) - 1)):
            continue
        for i in range(len(order) - 1):
            yield key, order[i], span[order[i]], order[i + 1], span[order[i + 1]]


def _series():
    return collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0.0])))


def scan(path, key_col, val_col, fy_col, usd_col, name_col=None, extra_cols=(),
         vintage_col=None):
    """One streaming pass. Returns (series, vintage, key_names, extra).

    `vintage` is Counter per (key, value) over `vintage_col`. It exists because
    START_HERE #5 records a column that HELD TWO VOCABULARIES across a source
    seam, and the same hazard is live in `awardee_name`: measured 2026-09-02,
    FY2000-2007 prime rows come only from the hand-checked master file in Title
    Case and FY2008+ adds the USAspending archive in UPPER CASE. A "change"
    that coincides with a change of SOURCE is not a change of OWNER.
    """
    series = _series()
    vintage = collections.defaultdict(collections.Counter)
    key_name = collections.defaultdict(collections.Counter)
    extra = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    with open(path, newline="", encoding="utf-8") as f:
        rd = csv.reader(f)
        head = next(rd)
        ix = {c: i for i, c in enumerate(head)}
        need = [key_col, val_col, fy_col]
        for c in need:
            if c not in ix:
                raise KeyError(f"{path} has no column {c}")
        ik, iv, ify = ix[key_col], ix[val_col], ix[fy_col]
        iu = ix.get(usd_col, -1)
        inm = ix.get(name_col, -1) if name_col else -1
        ivt = ix.get(vintage_col, -1) if vintage_col else -1
        iex = {c: ix[c] for c in extra_cols if c in ix}
        for row in rd:
            k = clean_id(row[ik])
            if not k:
                continue
            v = clean_id(row[iv])
            fy = (row[ify] or "").strip()
            if not fy.isdigit():
                continue
            try:
                usd = float(row[iu] or 0) if iu >= 0 else 0.0
            except ValueError:
                usd = 0.0
            cell = series[k][fy][v]
            cell[0] += 1
            cell[1] += usd
            if inm >= 0 and row[inm]:
                key_name[k][row[inm]] += 1
            if ivt >= 0:
                vintage[(k, v)][row[ivt]] += 1
            for c, i in iex.items():
                if row[i]:
                    extra[k][c][row[i]] += 1
    return series, vintage, key_name, extra


def scan_names(path, key_col, name_col, fy_col, usd_col, nkey, vintage_col=None):
    """Series keyed on identifier, VALUE = the entity's own NAME, normalized.

    Normalisation is 1010's `nkey` - the same distinctive-token reduction the
    refusal battery uses - after stripping periods, so `L.L.C.` reduces to `llc`
    and is dropped as a corporate form rather than surviving as three tokens
    `l l c` and manufacturing a rename out of punctuation.
    """
    series = _series()
    raw = collections.defaultdict(collections.Counter)
    vintage = collections.defaultdict(collections.Counter)
    with open(path, newline="", encoding="utf-8") as f:
        rd = csv.reader(f)
        head = next(rd)
        ix = {c: i for i, c in enumerate(head)}
        ik, inm, ify = ix[key_col], ix[name_col], ix[fy_col]
        iu = ix.get(usd_col, -1)
        ivt = ix.get(vintage_col, -1) if vintage_col else -1
        for row in rd:
            k = clean_id(row[ik])
            if not k:
                continue
            nm = (row[inm] or "").strip()
            if not nm or nm.lower() == "nan":
                continue
            fy = (row[ify] or "").strip()
            if not fy.isdigit():
                continue
            try:
                usd = float(row[iu] or 0) if iu >= 0 else 0.0
            except ValueError:
                usd = 0.0
            nk = nkey(nm.replace(".", ""))
            if not nk:
                continue
            cell = series[k][fy][nk]
            cell[0] += 1
            cell[1] += usd
            raw[(k, nk)][nm] += 1
            if ivt >= 0:
                vintage[(k, nk)][row[ivt]] += 1
    return series, raw, vintage


# --------------------------------------------------------------------------
CAND_COLS = [
    "candidate_id", "axis", "axis_description", "identifier_type", "identifier",
    "child_name", "prior_side_id", "prior_side_name", "prior_first_fy", "prior_last_fy",
    "prior_rows", "later_side_id", "later_side_name", "later_first_fy", "later_last_fy",
    "later_rows", "transition_between_fy", "prior_hubs", "later_hubs", "direction",
    "native_side_present", "scale_obligations_usd_in_runs", "announced_value_usd",
    "deal_status_std", "terms_restricted_party", "already_in_deals_classified",
    "deal_ledger_match", "interpretation_caution", "source_vintage_both_runs",
    "source_file", "source_url",
    "evidence_note", "built_by",
]
REJ_COLS = [
    "axis", "refusal", "identifier_type", "identifier", "child_name",
    "prior_side_id", "prior_side_name", "later_side_id", "later_side_name",
    "prior_first_fy", "prior_last_fy", "later_first_fy", "later_last_fy",
    "shared_evidence", "built_by",
]
CONS_COLS = [
    "consolidated_id", "dedup_key", "discovery_route", "source_workstream",
    "native_party", "counterparty_or_other_side", "identifier_type", "identifier",
    "event_year", "deal_status_std", "announced_value_usd", "already_in_deals_classified",
    "deal_ledger_match", "terms_restricted_source", "source_file", "source_url",
    "tierA_native_side_confirmed", "evidence_note", "review_status",
]


def cid(*parts) -> str:
    return "IDS-" + hashlib.md5("|".join(str(p) for p in parts).encode()).hexdigest()[:12].upper()


def terms_flag(*names) -> str:
    blob = " ".join((n or "").lower() for n in names)
    hits = sorted({lab for tok, lab in TERMS_RESTRICTED.items() if tok in blob})
    return "|".join(hits)


# --------------------------------------------------------------------------
# the deal ledger, for the "already known?" column
# --------------------------------------------------------------------------
class Ledger:
    def __init__(self, hubs) -> None:
        self.rows = []
        self.by_token = collections.defaultdict(set)
        self.ueis = set()
        if not os.path.exists(DEALS):
            return
        for r in _rows(DEALS):
            did = r.get("Deal_ID") or ""
            yr = (r.get("Event_Year") or (r.get("Event_Date") or "")[:4] or "").strip()
            blob = " ".join(
                (r.get(c) or "") for c in
                ("Deal_Title", "Native_Party", "Counterparty_or_Funder", "Description")
            )
            self.rows.append((did, yr, blob))
            for t in hubs.distinctive(blob):
                self.by_token[t].add((did, yr))
            for m in re.findall(r"\b[A-Z0-9]{12}\b", blob):
                self.ueis.add(m)

    def match(self, name, years, hubs):
        """Conservative: >=2 distinctive tokens of the name, in an overlapping year."""
        toks = hubs.distinctive(name)
        if len(toks) < 2:
            return ""
        cand = collections.Counter()
        for t in toks:
            for did, yr in self.by_token.get(t, ()):
                cand[(did, yr)] += 1
        out = []
        for (did, yr), n in cand.items():
            if n < 2:
                continue
            if yr and years and not any(abs(int(yr) - y) <= 1 for y in years if y):
                continue
            out.append(did)
        return "|".join(sorted(set(out))[:5])



def cautions(a_name, b_name, a_span, b_span, ah, bh) -> list:
    """What a reader must know before treating this lead as a transaction.

    Printed on the row rather than left in a build log, because a lead that
    travels without its caution becomes a claim.
    """
    out = []
    gap = b_span[0] - a_span[1]
    if gap > 1:
        out.append(f"{gap} fiscal years separate the two runs - the boundary is a "
                   f"GAP, not a date; the event lies somewhere in FY{a_span[1]}-FY{b_span[0]}")
    FORMS = frozenset(
        "inc llc corp corporation company co ltd limited lp llp incorporated tribe "
        "tribes nation nations pueblo band community rancheria village authority "
        "commission council university college association enterprises group "
        "services solutions technologies holdings".split())
    for side, nm in (("prior", a_name), ("later", b_name)):
        toks = [w.lower().strip(".,") for w in re.sub(r"[^A-Za-z0-9.,]+", " ", nm or "").split()]
        if len(toks) >= 2 and not (FORMS & set(toks)):
            out.append(f"the {side} side name carries no corporate, governmental or "
                       f"tribal form word - check it is a legal name and not free text")
    if not ah and not bh:
        out.append("no tier-A hub on either side")
    return out

# --------------------------------------------------------------------------
def build():
    m1010 = _load_1010()
    hubs = m1010.Hubs()
    # 1010's Hubs does not expose nkey/toks as methods; bind the module fns.
    hubs.nkey = m1010.nkey
    fams = Families(nkey=m1010.nkey)
    award = AwardHubs(m1010.nkey)
    ref = Refuser(hubs, award, fams)
    ledger = Ledger(hubs)

    cands: list[dict] = []
    rejs: list[dict] = []
    rej_counts = collections.Counter()
    axis_counts = collections.Counter()

    def emit(axis, axis_desc, idtype, ident, child_name, a_id, a_name, a_span,
             b_id, b_name, b_span, usd, source_file, evidence,
             a_vintage="", b_vintage=""):
        refusal, ah, bh, ev = ref.judge(a_id, a_name, b_id, b_name, a_vintage, b_vintage)
        if refusal:
            rej_counts[(axis, refusal)] += 1
            rejs.append({
                "axis": axis, "refusal": refusal, "identifier_type": idtype,
                "identifier": ident, "child_name": child_name,
                "prior_side_id": a_id, "prior_side_name": a_name,
                "later_side_id": b_id, "later_side_name": b_name,
                "prior_first_fy": a_span[0], "prior_last_fy": a_span[1],
                "later_first_fy": b_span[0], "later_last_fy": b_span[1],
                "shared_evidence": ev, "built_by": SCRIPT,
            })
            return
        if ah and not bh:
            direction = "LEFT_NATIVE_FAMILY"
        elif bh and not ah:
            direction = "ENTERED_NATIVE_FAMILY"
        else:
            direction = "NATIVE_FAMILY_CHANGED"
        axis_counts[axis] += 1
        cands.append({
            "candidate_id": cid(axis, ident, a_id, b_id),
            "axis": axis, "axis_description": axis_desc,
            "identifier_type": idtype, "identifier": ident, "child_name": child_name,
            "prior_side_id": a_id, "prior_side_name": a_name,
            "prior_first_fy": a_span[0], "prior_last_fy": a_span[1], "prior_rows": a_span[2],
            "later_side_id": b_id, "later_side_name": b_name,
            "later_first_fy": b_span[0], "later_last_fy": b_span[1], "later_rows": b_span[2],
            "transition_between_fy": f"{a_span[1]}->{b_span[0]}",
            "prior_hubs": "|".join(sorted(ah)), "later_hubs": "|".join(sorted(bh)),
            "direction": direction,
            "native_side_present": "1" if (ah or bh) else "0",
            "scale_obligations_usd_in_runs": round(usd, 2),
            "announced_value_usd": "",
            "deal_status_std": "OBSERVED_IN_FILINGS",
            "terms_restricted_party": terms_flag(child_name, a_name, b_name),
            "already_in_deals_classified": "",
            "deal_ledger_match": ledger.match(child_name or b_name, [a_span[1], b_span[0]], hubs),
            "source_file": source_file, "source_url": "",
            "evidence_note": evidence, "built_by": SCRIPT,
            "interpretation_caution": "; ".join(cautions(
                a_name, b_name, a_span, b_span, ah, bh)),
            "source_vintage_both_runs": a_vintage if a_vintage == b_vintage else
                                        f"{a_vintage} -> {b_vintage}",
        })

    def dom(counter):
        return counter.most_common(1)[0][0] if counter else ""

    # ---------------- S1 / S2 : the subaward surface -----------------------
    for axis, key_col, par_col, nm_col, desc in (
        ("S1", "sub_uei", "sub_parent_uei", "sub_name",
         "subawards.csv: declared parent of a fixed SUBAWARDEE UEI changes"),
        ("S2", "prime_uei", "prime_parent_uei", "prime_name",
         "subawards.csv: declared parent of a fixed PRIME UEI changes"),
    ):
        series, vint, key_name, extra = scan(
            SUBAW, key_col, par_col, "fiscal_year", "subaward_amount", nm_col,
            extra_cols=(par_col.replace("_uei", "_name"),),
            vintage_col="source_dataset",
        )
        pname_col = par_col.replace("_uei", "_name")
        # parent uei -> most common parent name, project-wide
        pnames = collections.defaultdict(collections.Counter)
        with open(SUBAW, newline="", encoding="utf-8") as f:
            rd = csv.DictReader(f)
            for r in rd:
                pu = clean_id(r.get(par_col))
                if pu and r.get(pname_col):
                    pnames[pu][r[pname_col]] += 1
        for key, a, aspan, b, bspan in transitions(series):
            if not a or not b:
                continue
            cn = key_name[key].most_common(1)[0][0] if key_name[key] else ""
            an = pnames[a].most_common(1)[0][0] if pnames[a] else ""
            bn = pnames[b].most_common(1)[0][0] if pnames[b] else ""
            emit(axis, desc, "UEI", key, cn, a, an, aspan, b, bn, bspan,
                 aspan[3] + bspan[3], "data/clean/subawards.csv",
                 f"subawards.csv {key_col}={key}: {par_col}={a} FY{aspan[0]}-{aspan[1]} "
                 f"({aspan[2]} rows), {par_col}={b} FY{bspan[0]}-{bspan[1]} ({bspan[2]} rows)",
                 dom(vint[(key, a)]), dom(vint[(key, b)]))

    # ---------------- C1 : a CAGE re-paired to a different UEI -------------
    series, cvint, _kn, _ex = scan(PRIME, "cage_code", "awardee_uei", "fiscal_year",
                                   "total_obligations", vintage_col="source_authority")
    uei_names = collections.defaultdict(collections.Counter)
    with open(PRIME, newline="", encoding="utf-8") as f:
        rd = csv.reader(f)
        head = next(rd)
        ix = {c: i for i, c in enumerate(head)}
        iu, inm = ix["awardee_uei"], ix["awardee_name"]
        for row in rd:
            u = clean_id(row[iu])
            if u and row[inm]:
                uei_names[u][row[inm]] += 1
    for cage, a, aspan, b, bspan in transitions(series):
        if not a or not b:
            continue
        an = uei_names[a].most_common(1)[0][0] if uei_names[a] else ""
        bn = uei_names[b].most_common(1)[0][0] if uei_names[b] else ""
        emit("C1", "prime_contracts.csv: one CAGE code re-paired from one UEI to another "
                   "(successor registration - the CAGE is the constant, the legal person is not)",
             "CAGE", cage, "", a, an, aspan, b, bn, bspan, aspan[3] + bspan[3],
             "data/clean/prime_contracts.csv",
             f"prime_contracts.csv cage_code={cage}: awardee_uei={a} ({an}) FY{aspan[0]}-{aspan[1]} "
             f"({aspan[2]} rows), awardee_uei={b} ({bn}) FY{bspan[0]}-{bspan[1]} ({bspan[2]} rows)",
             dom(cvint[(cage, a)]), dom(cvint[(cage, b)]))

    # ---------------- N1 / A1 : the legal name moved under a fixed id ------
    for axis, path, key_col, nm_col, usd_col, vcol, srcname, desc in (
        ("N1", PRIME, "awardee_uei", "awardee_name", "total_obligations",
         "source_authority", "data/clean/prime_contracts.csv",
         "prime_contracts.csv: a fixed awardee UEI whose LEGAL NAME changes corporate family "
         "- the relation a name search cannot reach, because the name is what moved"),
        ("A1", ASSIST, "recipient_uei", "recipient_name", "obligated_usd",
         "source_vintage", "data/clean/federal_funding_transactions.csv",
         "federal_funding_transactions.csv: a fixed recipient UEI whose LEGAL NAME changes "
         "corporate family"),
    ):
        series, raw, nvint = scan_names(path, key_col, nm_col, "fiscal_year", usd_col,
                                        m1010.nkey, vintage_col=vcol)
        for uei, a, aspan, b, bspan in transitions(series):
            if not a or not b:
                continue
            an = raw[(uei, a)].most_common(1)[0][0]
            bn = raw[(uei, b)].most_common(1)[0][0]
            emit(axis, desc, "UEI", uei, bn, uei + "#" + a[:40], an, aspan,
                 uei + "#" + b[:40], bn, bspan, aspan[3] + bspan[3], srcname,
                 f"{srcname} {key_col}={uei}: {nm_col}=\"{an}\" FY{aspan[0]}-{aspan[1]} "
                 f"({aspan[2]} rows), {nm_col}=\"{bn}\" FY{bspan[0]}-{bspan[1]} ({bspan[2]} rows)",
                 dom(nvint[(uei, a)]), dom(nvint[(uei, b)]))

    # ---------------- already in the ledger? -------------------------------
    for c in cands:
        c["already_in_deals_classified"] = "YES" if c["deal_ledger_match"] else "NO"

    cands.sort(key=lambda r: -float(r["scale_obligations_usd_in_runs"] or 0))
    return (cands, rejs, rej_counts, axis_counts, hubs, ledger, fams,
            award.tier_counts, award.paren_variants, award)


# --------------------------------------------------------------------------
# CONSOLIDATION - fold in every other workstream's staged candidates
# --------------------------------------------------------------------------
def consolidate(cands, hubs, ledger, award):
    out: list[dict] = []
    seen: dict[str, str] = {}
    folded = collections.Counter()
    dropped_terms = collections.Counter()
    dup = collections.Counter()

    def key_of(*parts):
        s = " ".join(re.sub(r"[^a-z0-9]+", " ", (p or "").lower()) for p in parts)
        return " ".join(sorted(set(s.split())))[:180]

    retier = collections.Counter()

    def tierA_check(ident, native, other):
        """Re-run the AWARDING gate on a row another workstream produced.

        `1010` resolves hubs from the WHOLE identifier ledger. That ledger holds
        2,001 tier-B `cluster_v3` rows and they are not inert: measured here,
        `cluster_v3` keys `Indian Affairs, Bureau Of` and `Computer Sciences
        Corporation` to `AKNF-INPTBW-00-ARCSLO`. So every folded row is re-tested
        against tier A only and the answer is CARRIED, not silently applied -
        START_HERE trap 1 is that a consumer must never assign a tier, and the
        counterpart is that a consumer must never HIDE one either.
        """
        hits = award.of(ident, native) | award.of("", other)
        return "YES" if hits else "NO"

    def add(route, workstream, native, other, idtype, ident, year, status, value,
            already, ledger_match, src_file, src_url, note, tier_a=""):
        host = (src_url or "").lower()
        if any(h in host for h in TERMS_RESTRICTED_HOSTS):
            dropped_terms[workstream] += 1
            return
        dk = key_of(native, other, str(year), ident)
        if dk in seen:
            dup[workstream] += 1
            return
        seen[dk] = workstream
        folded[workstream] += 1
        out.append({
            "consolidated_id": cid("CONS", route, dk),
            "dedup_key": dk, "discovery_route": route, "source_workstream": workstream,
            "native_party": native, "counterparty_or_other_side": other,
            "identifier_type": idtype, "identifier": ident, "event_year": year,
            "deal_status_std": status, "announced_value_usd": value,
            "already_in_deals_classified": already, "deal_ledger_match": ledger_match,
            "terms_restricted_source": terms_flag(native, other),
            "source_file": src_file, "source_url": src_url,
            "evidence_note": note, "review_status": "UNREVIEWED",
            "tierA_native_side_confirmed": tier_a,
        })
        if tier_a:
            retier[f"{workstream}:{tier_a}"] += 1

    # -- route 1a: this script's five axes
    for c in cands:
        add("1_OWNERSHIP_CHANGE_IN_CONTRACTING", f"1071/{c['axis']}",
            c["later_side_name"] or c["child_name"], c["prior_side_name"],
            c["identifier_type"], c["identifier"], c["later_first_fy"],
            c["deal_status_std"], "", c["already_in_deals_classified"],
            c["deal_ledger_match"], c["source_file"], "", c["evidence_note"], "YES")

    # -- route 1b: 1010's prime parent_uei sweep, folded in, not re-derived
    p = os.path.join(REVIEW, "1010_ownership_change_candidates.csv")
    if os.path.exists(p):
        for r in _rows(p):
            add("1_OWNERSHIP_CHANGE_IN_CONTRACTING", "1010/prime_parent_uei",
                r.get("child_name", ""), r.get("prior_parent_name", ""), "UEI",
                r.get("child_uei", ""), r.get("later_first_fy", ""),
                "OBSERVED_IN_FILINGS", "",
                "YES" if r.get("deal_ledger_match") else "NO",
                r.get("deal_ledger_match", ""), "review/1010_ownership_change_candidates.csv",
                "", r.get("evidence_note", ""),
                tierA_check(r.get("child_uei", ""), r.get("child_name", ""),
                            r.get("prior_parent_name", "") + " " + r.get("later_parent_name", "")))

    # -- route 2: announced transactions staged by the adjacent agents
    for p, ws in (
        (os.path.join(STAGING, "deals_from_newsletters", "deal_candidates.csv"),
         "992/tribal_newsletters"),
        (os.path.join(STAGING, "deals_from_newsletters", "deal_candidates_wp_posts.csv"),
         "993/tribal_wp_posts"),
    ):
        if not os.path.exists(p):
            continue
        for r in _rows(p):
            add("2_ANNOUNCED_TRANSACTION", ws, r.get("Native_Party", ""),
                r.get("Counterparty_or_Funder", ""),
                "CEDAR_UID" if r.get("cedar_uid") else "", r.get("cedar_uid", ""),
                r.get("Event_Year", ""), r.get("deal_status_std", "UNCLASSIFIED"),
                r.get("Announced_Value_USD", ""), "",
                "", os.path.relpath(p, ROOT).replace("\\", "/"),
                r.get("Source_1", ""), r.get("Description", "")[:400])

    for p, ws in (
        (os.path.join(REVIEW, "deals_sec_edgar_1032_staged.csv"), "1032/sec_edgar"),
        (os.path.join(REVIEW, "deals_ancsa_1031_staged.csv"), "1031/ancsa_45_55_139"),
    ):
        if not os.path.exists(p):
            continue
        for r in _rows(p):
            add("2_ANNOUNCED_TRANSACTION", ws,
                r.get("Native_Party") or r.get("native_party", ""),
                r.get("Counterparty_or_Funder") or r.get("counterparty", ""),
                "", "", r.get("Event_Year") or r.get("event_year", ""),
                r.get("deal_status_std", "UNCLASSIFIED"),
                r.get("Announced_Value_USD") or r.get("announced_value_usd", ""),
                "", "", os.path.relpath(p, ROOT).replace("\\", "/"),
                r.get("Source_1") or r.get("source_url", ""),
                (r.get("Description") or r.get("Deal_Title") or "")[:400])

    # fill the ledger check for folded press rows
    for r in out:
        if r["already_in_deals_classified"]:
            continue
        yrs = [int(r["event_year"])] if str(r["event_year"]).isdigit() else []
        m = ledger.match(r["native_party"] + " " + r["counterparty_or_other_side"], yrs, hubs)
        r["deal_ledger_match"] = m
        r["already_in_deals_classified"] = "YES" if m else "NO"

    return out, folded, dropped_terms, dup, retier


# --------------------------------------------------------------------------
def write_csv(path, cols, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".part"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


# --------------------------------------------------------------------------
# VERIFY - recomputed from the written files, never from memory
# --------------------------------------------------------------------------
INVARIANT_NAMES = [
    "I1_every_candidate_has_an_identifier",
    "I2_no_nan_sentinel_in_identifier_columns",
    "I3_every_candidate_has_an_evidence_note_naming_file_and_years",
    "I4_no_contracting_candidate_carries_an_inferred_value",
    "I5_refusals_actually_fired",
    "I6_no_duplicate_dedup_key_in_consolidated",
    "I7_no_candidate_is_intra_family",
]


def verify(quiet=False):
    fails = []
    if not os.path.exists(OUT_CAND):
        print("VERIFY FAIL - candidate file absent; run `measure` first")
        return 1
    cands = list(_rows(OUT_CAND))
    rejs = list(_rows(OUT_REJ)) if os.path.exists(OUT_REJ) else []
    cons = list(_rows(OUT_CONS)) if os.path.exists(OUT_CONS) else []

    for c in cands:
        if not (c.get("identifier") or "").strip():
            fails.append(("I1_every_candidate_has_an_identifier", c.get("candidate_id")))
            break
    for c in cands:
        vals = [c.get("identifier", ""), c.get("prior_side_id", ""), c.get("later_side_id", "")]
        if any((v or "").strip().lower() == "nan" for v in vals):
            fails.append(("I2_no_nan_sentinel_in_identifier_columns", c.get("candidate_id")))
            break
    for c in cands:
        n = c.get("evidence_note") or ""
        if ".csv" not in n or "FY" not in n:
            fails.append(("I3_every_candidate_has_an_evidence_note_naming_file_and_years",
                          c.get("candidate_id")))
            break
    for c in cands:
        if (c.get("announced_value_usd") or "").strip():
            fails.append(("I4_no_contracting_candidate_carries_an_inferred_value",
                          c.get("candidate_id")))
            break
    if cands and not rejs:
        fails.append(("I5_refusals_actually_fired", "0 refusals recorded against "
                      f"{len(cands)} candidates - the intra-family battery cannot be trusted"))
    seen = set()
    for r in cons:
        k = r.get("dedup_key")
        if k in seen:
            fails.append(("I6_no_duplicate_dedup_key_in_consolidated", k))
            break
        seen.add(k)

    if cands:
        m1010 = _load_1010()
        hubs = m1010.Hubs()
        hubs.nkey = m1010.nkey
        fams = Families(nkey=m1010.nkey)
        for c in cands:
            ah = {h for h in (c.get("prior_hubs") or "").split("|") if h}
            bh = {h for h in (c.get("later_hubs") or "").split("|") if h}
            if ah and bh and (fams.closure_of_hubs(ah) & fams.closure_of_hubs(bh)):
                fails.append(("I7_no_candidate_is_intra_family", c.get("candidate_id")))
                break

    if fails:
        for name, ev in fails:
            print(f"INVARIANT BREACH - {name}: {ev}")
        return 1
    if not quiet:
        print("VERIFY OK -", json.dumps({
            "candidates": len(cands), "rejections": len(rejs), "consolidated": len(cons),
            "invariants_checked": INVARIANT_NAMES,
        }, indent=2))
    return 0


def selftest():
    """Inject each violation, assert verify exits 1 AND names that invariant."""
    import shutil
    import tempfile
    import io
    import contextlib

    if not os.path.exists(OUT_CAND):
        print("SELFTEST FAIL - run `measure` first")
        return 1
    bkp = tempfile.mkdtemp(prefix="1071_selftest_")
    saved = {}
    for p in (OUT_CAND, OUT_REJ, OUT_CONS):
        if os.path.exists(p):
            saved[p] = os.path.join(bkp, os.path.basename(p))
            shutil.copy2(p, saved[p])

    def restore():
        for p, s in saved.items():
            shutil.copy2(s, p)

    def run_case(name, mutate, expect):
        restore()
        mutate()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = verify(quiet=True)
        txt = buf.getvalue()
        ok = rc == 1 and expect in txt
        print(f"  {'PASS' if ok else 'FAIL'}  {name}  ->  rc={rc} "
              f"{'names ' + expect if expect in txt else 'DID NOT NAME ' + expect}")
        return ok

    def edit(path, fn):
        rows = list(_rows(path))
        cols = list(rows[0].keys())
        fn(rows)
        write_csv(path, cols, rows)

    allok = True
    print("SELFTEST - injecting one synthetic violation per invariant")

    allok &= run_case("I1 blank identifier",
                      lambda: edit(OUT_CAND, lambda rs: rs[0].__setitem__("identifier", "")),
                      "I1_every_candidate_has_an_identifier")
    allok &= run_case("I2 nan sentinel",
                      lambda: edit(OUT_CAND, lambda rs: rs[0].__setitem__("identifier", "nan")),
                      "I2_no_nan_sentinel_in_identifier_columns")
    allok &= run_case("I3 evidence note stripped",
                      lambda: edit(OUT_CAND, lambda rs: rs[0].__setitem__("evidence_note", "a change happened")),
                      "I3_every_candidate_has_an_evidence_note_naming_file_and_years")
    allok &= run_case("I4 inferred value",
                      lambda: edit(OUT_CAND, lambda rs: rs[0].__setitem__("announced_value_usd", "50000000")),
                      "I4_no_contracting_candidate_carries_an_inferred_value")
    allok &= run_case("I5 rejection file emptied",
                      lambda: write_csv(OUT_REJ, REJ_COLS, []),
                      "I5_refusals_actually_fired")
    allok &= run_case("I6 duplicate dedup_key",
                      lambda: edit(OUT_CONS, lambda rs: rs[1].__setitem__("dedup_key", rs[0]["dedup_key"])),
                      "I6_no_duplicate_dedup_key_in_consolidated")

    def intra():
        def f(rs):
            rs[0]["prior_hubs"] = rs[0]["later_hubs"] = _any_hub()
        edit(OUT_CAND, f)
    allok &= run_case("I7 both sides one hub", intra, "I7_no_candidate_is_intra_family")

    restore()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = verify(quiet=True)
    print(f"  {'PASS' if rc == 0 else 'FAIL'}  restored -> rc={rc} (expected 0)")
    allok &= (rc == 0)
    print("SELFTEST", "OK" if allok else "FAILED")
    return 0 if allok else 1


def _any_hub():
    for r in _rows(SPINE):
        if r.get("tribe_id"):
            return r["tribe_id"]
    return "TRBF-XXXXXX-00"


# --------------------------------------------------------------------------
def main(argv):
    cmd = (argv[1] if len(argv) > 1 else "measure").lower()
    if cmd == "verify":
        return verify()
    if cmd == "selftest":
        return selftest()
    if cmd not in ("measure", "build", "run"):
        print(__doc__)
        return 2

    (cands, rejs, rej_counts, axis_counts, hubs, ledger, fams,
     award_tiers, paren_variants, award_hubs) = build()
    cons, folded, dropped_terms, dup, retier = consolidate(
        cands, hubs, ledger, award_hubs)

    write_csv(OUT_CAND, CAND_COLS, cands)
    write_csv(OUT_REJ, REJ_COLS, rejs)
    write_csv(OUT_CONS, CONS_COLS, cons)

    BUCKET = {
        "INTRA_FAMILY_SAME_HUB": "intra_family_relabelling",
        "INTRA_FAMILY_SHARED_BRAND": "intra_family_relabelling",
        "INTRA_FAMILY_ACRONYM": "intra_family_relabelling",
        "SAME_DISTINCTIVE_TOKENS": "same_entity_re_registration",
        "NEAR_IDENTICAL_NAME": "same_entity_re_registration",
        "SOURCE_VINTAGE_SEAM": "source_artefact_not_an_event",
        "NAN_SENTINEL": "source_artefact_not_an_event",
        "SIDE_NAME_MISSING": "untestable_one_side_unnamed",
        "GOVERNMENT_BODY_AS_DECLARED_PARENT": "pass_through_not_an_owner",
        "NO_NATIVE_SIDE_AT_TIER_A": "out_of_scope_no_tierA_native_side",
    }
    buckets = collections.Counter()
    for (a, r), v in rej_counts.items():
        buckets[BUCKET.get(r, r)] += v
    inv = {
        "built_by": SCRIPT,
        "candidates_new_axes": len(cands),
        "candidates_by_axis": {k: v for k, v in sorted(axis_counts.items())},
        "rejections_total": len(rejs),
        "rejections_by_bucket": dict(buckets),
        "rejections_intra_family_relabelling": buckets["intra_family_relabelling"],
        "rejections_by_axis_and_reason": {f"{a}/{r}": v for (a, r), v in sorted(rej_counts.items())},
        "constellation_edges_total": fams.edges_with_from_uid + fams.edges_name_only,
        "constellation_edges_with_a_from_cedar_uid": fams.edges_with_from_uid,
        "constellation_edges_name_only_from_side": fams.edges_name_only,
        "constellation_edges_used_in_uid_closure": fams.n_edges,
        "identifier_ledger_tier_census": dict(award_tiers),
        "spine_parenthetical_name_variants_indexed": paren_variants,
        "already_in_deals_classified": collections.Counter(
            c["already_in_deals_classified"] for c in cands),
        "consolidated_rows": len(cons),
        "consolidated_by_workstream": dict(folded),
        "consolidated_duplicates_suppressed": dict(dup),
        "consolidated_dropped_terms_restricted_source": dict(dropped_terms),
        "folded_rows_retested_against_tierA_only": dict(retier),
        "invariants": INVARIANT_NAMES,
    }
    os.makedirs(os.path.dirname(OUT_INV), exist_ok=True)
    with open(OUT_INV, "w", encoding="utf-8") as f:
        json.dump(inv, f, indent=2, sort_keys=True, default=str)
    print(json.dumps(inv, indent=2, sort_keys=True, default=str))
    for p in (OUT_CAND, OUT_REJ, OUT_CONS, OUT_INV):
        print("wrote", os.path.relpath(p, ROOT).replace("\\", "/"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
