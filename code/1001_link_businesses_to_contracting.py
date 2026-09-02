#!/usr/bin/env python3
"""Join the Native-owned business directory to the federal contracting universe.

WHY THIS EXISTS
---------------
`data/clean/native_owned_businesses.csv` holds 2,393 firms certified by 18
tribal authorities. `business_entity_id` is populated on FOUR of them. The
directory and the contracting tables are both built and cannot be joined to
each other, so no customer can ask "what did the firms this nation certified
actually win?"

WHAT IT DOES
------------
Assembles every (name -> UEI/CAGE) observation Cedar already holds on the
federal side - prime_contracts, subawards, fpds_uei_cage_map, and the SAM
FY2000-2007 backfill - groups them by UEI, and matches the directory against
that universe.

MATCHING IS IDENTIFIER-FIRST IN SPIRIT AND NAME-WITH-CORROBORATION IN
PRACTICE, because the tribal directories publish NO federal identifiers at
all (measured: `code/1000_harvest_business_identifiers.py sweep`). The
federal side is what carries the UEI; the directory carries the name and,
often, the city and state. So the join runs name-exact and then climbs the
owner's ladder for corroboration:

    address (city+state) -> state -> nation's home state -> uniqueness -> stop

`docs/ENTITY_MATCH_RULES.md` governs:
  * rule 1  - an entity whose whole distinctive token set is generic may not
              win a name-only match. Enforced structurally (token count and a
              generic-set test), not by a denylist.
  * rule 7  - where the record has an address, geography is a LADDER not a
              gate. The rungs below are that ladder.
  * veto    - a state DISAGREEMENT refuses the match outright. Weak evidence
              may always BLOCK; it may never AWARD.
  * rule 5  - method and evidence are recorded on the row.
  * rule 6  - unmatched is an honest outcome and is written down as one.

NO FABRICATION: every UEI and CAGE written here was read from a Cedar
contracting table, never inferred. Structural validation (UEI 12 alnum, CAGE
5 alnum) rejects malformed values rather than storing them.

OUTPUTS (this script owns these files; it never rewrites the directory)
    data/clean/native_business_contract_links.csv   one row per directory firm
    data/clean/native_business_identifier_crosswalk.csv  (appended; 1000 seeds)
    review/native_business_link_holds_2026-09-02.csv     ambiguous / conflicted

ORDER. `1000 web` (network) -> `1000 promote` (jsonl -> crosswalk) ->
`1001 build`. Both scripts write the shared crosswalk with
`open_crosswalk()`, which keeps the rows it did not author - but they must
not run CONCURRENTLY, because two processes holding the same file open is a
race no keep-the-other-rows logic can survive. Run them in order; `promote`
makes the whole chain deterministic and re-runnable with no network.

USAGE
    py -3 code/1001_link_businesses_to_contracting.py build
    py -3 code/1001_link_businesses_to_contracting.py verify
    py -3 code/1001_link_businesses_to_contracting.py verify --synthetic
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

csv.field_size_limit(1 << 30)

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"

DIRECTORY = CLEAN / "native_owned_businesses.csv"
LINKS = CLEAN / "native_business_contract_links.csv"
CROSSWALK = CLEAN / "native_business_identifier_crosswalk.csv"
HOLDS = REVIEW / "native_business_link_holds_2026-09-02.csv"
BY_NATION = CLEAN / "native_business_contracting_by_nation.csv"
SUMMARY = CLEAN / "_1001_summary.json"

BUILT_BY = "code/1001_link_businesses_to_contracting.py"
BUILT_DATE = "2026-09-02"

# --------------------------------------------------------------------------
# Structural identifier validation. Reject, never store, a malformed value.
# --------------------------------------------------------------------------
# The letters I and O are never used in a CAGE code or a UEI (DLA / GSA both
# exclude them), and a UEI never begins with 0. Verified against Cedar's own
# `fpds_uei_cage_map.csv`: 8,886 CAGE codes and 34,601 UEIs, none containing
# I or O, none starting 0. See code/1000 for what this rule caught.
UEI_RE = re.compile(r"^(?!0)(?![A-Z0-9]*[IO])[A-Z0-9]{12}$")
CAGE_RE = re.compile(r"^(?![A-Z0-9]*[IO])[A-Z0-9]{5}$")
# Values that are present, well-formed-looking and mean nothing.
NULL_TOKENS = {"", "NAN", "NONE", "NULL", "N/A", "NA", "UNKNOWN", "00000",
               "000000000000", "-", "--"}


def clean_uei(v):
    v = (v or "").strip().upper()
    if v in NULL_TOKENS:
        return ""
    return v if UEI_RE.match(v) else ""


def clean_cage(v):
    v = (v or "").strip().upper()
    if v in NULL_TOKENS:
        return ""
    return v if CAGE_RE.match(v) else ""


# --------------------------------------------------------------------------
# Name normalisation.
# --------------------------------------------------------------------------
LEGAL_SUFFIX = {
    "INC", "INCORPORATED", "LLC", "LLP", "LP", "LTD", "LIMITED", "CORP",
    "CORPORATION", "CO", "COMPANY", "PC", "PLLC", "PA", "PLC", "LC", "LLLP",
    "THE", "DBA",
}
# Words that carry no distinguishing power on their own. Used ONLY to compute
# the distinctive token set for rule 1 - never as a denylist that decides a
# match.
GENERIC_TOKENS = {
    "AND", "OF", "FOR", "SERVICES", "SERVICE", "CONSTRUCTION", "ENTERPRISE",
    "ENTERPRISES", "GROUP", "SOLUTIONS", "CONSULTING", "CONTRACTING",
    "CONTRACTORS", "CONTRACTOR", "BUILDERS", "BUILDING", "SUPPLY", "TRUCKING",
    "TRANSPORT", "TRANSPORTATION", "CLEANING", "CLEANERS", "MAINTENANCE",
    "PAINTING", "PLUMBING", "ELECTRIC", "ELECTRICAL", "ROOFING", "EXCAVATING",
    "EXCAVATION", "LANDSCAPING", "CATERING", "DESIGN", "DESIGNS", "STUDIO",
    "STUDIOS", "CONSULTANTS", "ASSOCIATES", "PARTNERS", "HOLDINGS", "VENTURES",
    "INDUSTRIES", "SYSTEMS", "TECHNOLOGIES", "TECHNOLOGY", "MANAGEMENT",
    "DEVELOPMENT", "PRODUCTS", "PRODUCTIONS", "WORKS", "SHOP", "STORE",
    "COMPANY", "NATIVE", "AMERICAN", "INDIAN", "TRIBAL", "GENERAL",
    "PROFESSIONAL", "QUALITY", "CUSTOM", "CREATIONS", "DESIGNS", "ART",
    "ARTS", "CRAFTS", "CONSULTANT", "LLC", "INC",
}
DBA_SPLIT = re.compile(r"\b(?:D\s*/?\s*B\s*/?\s*A|DOING\s+BUSINESS\s+AS)\b")


def name_variants(raw):
    """Every normalized form a name should be indexed under.

    A directory row `Corporate Image, Inc. dba Eagle Wing` is two names, and
    the federal side may carry either one. Returning both is not fuzziness -
    each variant is still matched EXACTLY.
    """
    s = (raw or "").upper().replace("&", " AND ")
    parts = DBA_SPLIT.split(s) if DBA_SPLIT.search(s) else [s]
    out = []
    for p in parts:
        p = re.sub(r"[^A-Z0-9 ]+", " ", p)
        toks = [t for t in p.split() if t and t not in LEGAL_SUFFIX]
        n = " ".join(toks)
        if n and n not in out:
            out.append(n)
    return out


CONTRACT_TOKEN = re.compile(r"^[A-Z0-9][A-Z0-9-]{6,}$")


def contract_tokens(value):
    """Contract numbers printed by the directory, as tokens.

    `federal_contract_number` is free text: `47QTCA19D00FN; HHSN316201200127W`,
    `HHSN316201200151W & HHSN316201200087W`,
    `47QRCA25DU031, Domains: Management`. Split wide and keep only tokens that
    look like a PIID; a word like `Domains` cannot survive the shape test.
    """
    out = []
    for t in re.split(r"[;,&/\s]+", (value or "").upper()):
        t = t.strip(".;,")
        if CONTRACT_TOKEN.match(t) and not t.isalpha():
            out.append(t)
    return out


def distinctive(norm_name):
    return [t for t in norm_name.split() if t not in GENERIC_TOKENS]


def name_can_carry_a_match(norm_name):
    """ENTITY_MATCH_RULES rule 1, written structurally.

    A name may found a match only if what is left after removing generic and
    organisational words is at least one token AND the whole name is at least
    two tokens. `EDWARDS CONSTRUCTION` keeps `EDWARDS` and passes; `NATIVE
    CONSTRUCTION` keeps nothing and fails; `SUPPORTING STRATEGIES` keeps both
    and passes on length.
    """
    toks = norm_name.split()
    if len(toks) < 2:
        return False, "single_token_name"
    if not distinctive(norm_name):
        return False, "all_tokens_generic"
    return True, ""


# --------------------------------------------------------------------------
# State normalisation. The directory carries truncations ('Ariz', 'Uta',
# 'Alas') from PDF column clipping. A prefix that is ambiguous stays UNKNOWN -
# guessing a state would manufacture the corroboration this whole script
# depends on.
# --------------------------------------------------------------------------
STATE_NAMES = {
    "ALABAMA": "AL", "ALASKA": "AK", "ARIZONA": "AZ", "ARKANSAS": "AR",
    "CALIFORNIA": "CA", "COLORADO": "CO", "CONNECTICUT": "CT",
    "DELAWARE": "DE", "FLORIDA": "FL", "GEORGIA": "GA", "HAWAII": "HI",
    "IDAHO": "ID", "ILLINOIS": "IL", "INDIANA": "IN", "IOWA": "IA",
    "KANSAS": "KS", "KENTUCKY": "KY", "LOUISIANA": "LA", "MAINE": "ME",
    "MARYLAND": "MD", "MASSACHUSETTS": "MA", "MICHIGAN": "MI",
    "MINNESOTA": "MN", "MISSISSIPPI": "MS", "MISSOURI": "MO", "MONTANA": "MT",
    "NEBRASKA": "NE", "NEVADA": "NV", "NEW HAMPSHIRE": "NH",
    "NEW JERSEY": "NJ", "NEW MEXICO": "NM", "NEW YORK": "NY",
    "NORTH CAROLINA": "NC", "NORTH DAKOTA": "ND", "OHIO": "OH",
    "OKLAHOMA": "OK", "OREGON": "OR", "PENNSYLVANIA": "PA",
    "RHODE ISLAND": "RI", "SOUTH CAROLINA": "SC", "SOUTH DAKOTA": "SD",
    "TENNESSEE": "TN", "TEXAS": "TX", "UTAH": "UT", "VERMONT": "VT",
    "VIRGINIA": "VA", "WASHINGTON": "WA", "WEST VIRGINIA": "WV",
    "WISCONSIN": "WI", "WYOMING": "WY", "DISTRICT OF COLUMBIA": "DC",
}
ABBREVS = set(STATE_NAMES.values())


def plausible_states(v, widen=False):
    """Every state the recorded value could mean. AMBIGUITY WIDENS, NEVER PICKS.

    The directory carries PDF column-clipping truncations - `Ariz`, `Uta`,
    `Alas`, and `Ne` on 14 Navajo rows whose cities are Gallup, Shiprock and
    Albuquerque, i.e. New Mexico. Read `Ne` as the Nebraska abbreviation and
    every one of those rows produces a FALSE state conflict and silently loses
    a real link. Read it as New Mexico and you have guessed.

    So neither: on a source whose state column is demonstrably truncation-prone
    (`source_state_column_is_truncated` below measures that from the data, not
    from a list), `Ne` returns {NE, NV, NH, NJ, NM, NY} and corroboration on
    ANY member counts - at a tier that records the geography as ambiguous. Six
    candidate states is still a strong veto (it refuses Oklahoma) and a weak
    award, which is what the evidence actually supports.
    """
    s = re.sub(r"[^A-Z ]", "", (v or "").upper()).strip()
    if not s:
        return frozenset()
    out = set()
    if s in ABBREVS:
        out.add(s)
    if s in STATE_NAMES:
        out.add(STATE_NAMES[s])
    if widen or not out:
        out |= {a for n, a in STATE_NAMES.items() if n.startswith(s)}
    return frozenset(out)


def source_state_column_is_truncated(rows):
    """Which sources clip their state column, measured rather than listed.

    A source is truncation-prone if ANY of its state values is neither a
    standard abbreviation nor a full state name - `Ariz`, `Uta`, `Okl`. On
    such a source a two-letter value may itself be a clipped word, so every
    value from it is read as a prefix.
    """
    prone = set()
    for r in rows:
        s = re.sub(r"[^A-Z ]", "", (r["state_province"] or "").upper()).strip()
        if s and s not in ABBREVS and s not in STATE_NAMES:
            prone.add(r["source_id"])
    return prone


def norm_city(v):
    s = (v or "").upper()
    s = re.sub(r"\bFT\.?\b", "FORT", s)
    s = re.sub(r"\bST\.?\b", "SAINT", s)
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# The certifying nation's own footprint. A CORROBORATOR, never a gate, and
# never a claim about where the firm is: it is only used where the directory
# row carries no usable state of its own, and it can only lift a match to
# tier B.
NATION_STATES = {
    "Cherokee Nation": {"OK"},
    "Navajo Nation": {"AZ", "NM", "UT"},
    "Muscogee (Creek) Nation": {"OK"},
    "Lummi Nation": {"WA"},
    "Three Affiliated Tribes (MHA Nation)": {"ND"},
    "Confederated Salish & Kootenai Tribes": {"MT"},
    "Calista Corporation": {"AK"},
    "Confederated Tribes of Grand Ronde": {"OR"},
    "Eastern Band of Cherokee Indians": {"NC"},
    "Pokagon Band of Potawatomi Indians": {"MI", "IN"},
    "Tulalip Tribes": {"WA"},
    "Oneida Nation (Wisconsin)": {"WI"},
    "Blackfeet Nation": {"MT"},
    "Arctic Slope Regional Corporation": {"AK"},
    "Tohono O'odham Nation": {"AZ"},
    "Poarch Band of Creek Indians": {"AL"},
    "Doyon, Limited": {"AK"},
    "Menominee Indian Tribe of Wisconsin": {"WI"},
}
NATION_STATES_BASIS = (
    "hand-entered from each certifying authority's own service area; "
    "used only as a tier-B corroborator where the directory row has no "
    "usable state, never as a gate and never published as a firm address"
)


# --------------------------------------------------------------------------
# The federal side.
# --------------------------------------------------------------------------
class FedEntity:
    __slots__ = ("uei", "cages", "names", "states", "cities", "prime_oblig",
                 "prime_rows", "sub_amount", "sub_rows", "sources",
                 "first_fy", "last_fy", "restricted_name_only",
                 "sam_backfill_oblig", "sam_backfill_rows",
                 "prime_oblig_already_attributed", "parents")

    def __init__(self, uei):
        self.uei = uei
        self.cages = Counter()
        self.names = Counter()
        self.states = Counter()
        self.cities = Counter()
        self.prime_oblig = 0.0
        self.prime_rows = 0
        self.sam_backfill_oblig = 0.0
        self.sam_backfill_rows = 0
        self.prime_oblig_already_attributed = 0.0
        # The parent the FIRM ITSELF declares in FPDS. Independent of the
        # tribal directory's claim and of Cedar's own attribution, so where
        # the two agree it is a genuine second source (ASSERTION_LAYER: a
        # copy of a source is not a corroboration; a different filer is).
        self.parents = Counter()
        self.sub_amount = 0.0
        self.sub_rows = 0
        self.sources = set()
        self.first_fy = ""
        self.last_fy = ""
        self.restricted_name_only = True   # cleared by any unrestricted name


def _merge_entities(group):
    """One firm's successor entities, added up. Never used to merge across a
    geography disagreement - the caller has already proved a shared city."""
    m = FedEntity(group[0].uei)
    for e in group:
        m.cages.update(e.cages)
        m.names.update(e.names)
        m.states.update(e.states)
        m.cities.update(e.cities)
        m.prime_oblig += e.prime_oblig
        m.prime_rows += e.prime_rows
        m.sam_backfill_oblig += e.sam_backfill_oblig
        m.sam_backfill_rows += e.sam_backfill_rows
        m.prime_oblig_already_attributed += e.prime_oblig_already_attributed
        m.parents.update(e.parents)
        m.sub_amount += e.sub_amount
        m.sub_rows += e.sub_rows
        m.sources |= e.sources
        m.first_fy = _fy(m.first_fy, e.first_fy, True)
        m.last_fy = _fy(m.last_fy, e.last_fy, False)
        m.restricted_name_only = m.restricted_name_only and             e.restricted_name_only
    return m


def _fy(cur, v, lo):
    v = (v or "").strip()[:4]
    if not v.isdigit():
        return cur
    if not cur:
        return v
    return min(cur, v) if lo else max(cur, v)


def build_federal_universe(verbose=True, want_contracts=frozenset()):
    """Every (UEI -> names, geography, money) Cedar already holds.

    Entities with no UEI are keyed `NOUEI:<cage>` or dropped: a match that
    cannot hand back an identifier is not the thing this script is for.
    """
    ents = {}
    # contract_number -> Counter(uei). Only the numbers the DIRECTORY printed,
    # so this costs nothing on a 1.2M-row scan.
    contracts = defaultdict(Counter)

    def ent(uei):
        e = ents.get(uei)
        if e is None:
            e = ents[uei] = FedEntity(uei)
        return e

    # --- prime_contracts: the money column ---------------------------------
    p = CLEAN / "prime_contracts.csv"
    t0 = time.time()
    with open(p, encoding="utf-8-sig", newline="") as fh:
        r = csv.reader(fh)
        ix = {c: i for i, c in enumerate(next(r))}
        for row in r:
            uei = clean_uei(row[ix["awardee_uei"]])
            if not uei:
                continue
            e = ent(uei)
            e.sources.add("prime_contracts")
            e.restricted_name_only = False
            nm = row[ix["awardee_name"]].strip()
            for v in name_variants(nm):
                e.names[v] += 1
            cg = clean_cage(row[ix["cage_code"]])
            if cg:
                e.cages[cg] += 1
            st = row[ix["recipient_state_code"]].strip().upper()
            if st in ABBREVS:
                e.states[st] += 1
            ct = norm_city(row[ix["recipient_city_name"]])
            if ct:
                e.cities[ct] += 1
            try:
                v = float(row[ix["total_obligations"]] or 0)
            except ValueError:
                v = 0.0
            e.prime_oblig += v
            # Was this dollar ALREADY attributed to a Cedar entity before this
            # join existed? The distinction decides what the headline means:
            # money already keyed to Arctic Slope is not new revenue Cedar can
            # see, it is money that can now also be seen THROUGH the firm and
            # the nation that certified it. Money that was unattributed is new
            # attribution surface.
            if row[ix["attributed_flag"]].strip() == "1":
                e.prime_oblig_already_attributed += v
            pu = clean_uei(row[ix["parent_uei"]])
            if pu and pu != uei:
                pn = row[ix["parent_name"]].strip()
                e.parents[(pu, pn)] += 1
            e.prime_rows += 1
            e.first_fy = _fy(e.first_fy, row[ix["fiscal_year"]], True)
            e.last_fy = _fy(e.last_fy, row[ix["fiscal_year"]], False)
            if want_contracts:
                for col in ("contract_number", "parent_contract_number"):
                    v = row[ix[col]].strip().upper()
                    if v in want_contracts:
                        contracts[v][uei] += 1
    if verbose:
        print(f"  prime_contracts   {len(ents):6d} UEIs  "
              f"{time.time() - t0:.0f}s", flush=True)

    # --- subawards ---------------------------------------------------------
    p = CLEAN / "subawards.csv"
    if p.exists():
        with open(p, encoding="utf-8-sig", newline="") as fh:
            r = csv.reader(fh)
            ix = {c: i for i, c in enumerate(next(r))}
            for row in r:
                uei = clean_uei(row[ix["sub_uei"]])
                if not uei:
                    continue
                e = ent(uei)
                e.sources.add("subawards")
                e.restricted_name_only = False
                for v in name_variants(row[ix["sub_name"]]):
                    e.names[v] += 1
                cg = clean_cage(row[ix["sub_cage"]])
                if cg:
                    e.cages[cg] += 1
                st = row[ix["sub_state"]].strip().upper()
                if st in ABBREVS:
                    e.states[st] += 1
                try:
                    e.sub_amount += float(row[ix["subaward_amount"]] or 0)
                except ValueError:
                    pass
                e.sub_rows += 1
    if verbose:
        print(f"  + subawards       {len(ents):6d} UEIs", flush=True)

    # --- fpds_uei_cage_map: name breadth, no money -------------------------
    # AGENTS/ENTITY_MATCH_RULES: this file carries the literal string 'NAN'
    # in cage_code on 2,196 rows across 2,193 UEIs. clean_cage() drops it.
    p = CLEAN / "fpds_uei_cage_map.csv"
    if p.exists():
        with open(p, encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                uei = clean_uei(row.get("uei"))
                if not uei:
                    continue
                e = ent(uei)
                e.sources.add("fpds_uei_cage_map")
                e.restricted_name_only = False
                for v in name_variants(row.get("legal_business_name")):
                    e.names[v] += 1
                cg = clean_cage(row.get("cage_code"))
                if cg:
                    e.cages[cg] += 1
    if verbose:
        print(f"  + fpds_uei_cage   {len(ents):6d} UEIs", flush=True)

    # --- SAM FY2000-2007 ---------------------------------------------------
    # LICENSING: the names and addresses on this file are D&B Open Data and
    # may not be disseminated in bulk (START_HERE, LICENSING). They are used
    # here as MATCH EVIDENCE only. Where a UEI is known to Cedar by no other
    # name, `evidence_licence` says so and the crosswalk never carries the
    # D&B string.
    p = CLEAN / "sam_prime_contracts_fy2000_2007.csv"
    if p.exists():
        with open(p, encoding="utf-8-sig", newline="") as fh:
            r = csv.reader(fh)
            ix = {c: i for i, c in enumerate(next(r))}
            for row in r:
                uei = clean_uei(row[ix["awardee_uei"]])
                if not uei:
                    continue
                e = ent(uei)
                e.sources.add("sam_fy2000_2007")
                for col in ("dnb_awardee_legal_name", "dnb_awardee_name",
                            "dnb_awardee_dba_name"):
                    for v in name_variants(row[ix[col]]):
                        e.names[v] += 1
                cg = clean_cage(row[ix["cage_code"]])
                if cg:
                    e.cages[cg] += 1
                st = row[ix["dnb_awardee_state"]].strip().upper()
                if st in ABBREVS:
                    e.states[st] += 1
                ct = norm_city(row[ix["dnb_awardee_city"]])
                if ct:
                    e.cities[ct] += 1
                # DO NOT ADD THIS TO prime_oblig. `double_count_risk = 1` on
                # 179,050 of 269,312 rows worth $750B - those PIID-FY pairs
                # are ALREADY in prime_contracts.csv, and folding them in
                # inflated the first draft of this build's headline by $5.7B.
                # The backfill's genuinely new rows ride in their own column.
                if row[ix["double_count_risk"]].strip() != "1":
                    try:
                        e.sam_backfill_oblig += float(
                            row[ix["total_action_obligation"]] or 0)
                    except ValueError:
                        pass
                    e.sam_backfill_rows += 1
                e.first_fy = _fy(e.first_fy, row[ix["fiscal_year"]], True)
                e.last_fy = _fy(e.last_fy, row[ix["fiscal_year"]], False)
    if verbose:
        print(f"  + sam_fy2000_07   {len(ents):6d} UEIs", flush=True)

    index = defaultdict(set)
    cage_index = defaultdict(set)
    for uei, e in ents.items():
        for nm in e.names:
            index[nm].add(uei)
        for cg in e.cages:
            cage_index[cg].add(uei)
    if verbose:
        print(f"  name index        {len(index):6d} distinct normalized names",
              flush=True)
        if want_contracts:
            print(f"  contract index    {len(contracts):6d} of "
                  f"{len(want_contracts)} directory contract numbers found",
                  flush=True)
    return ents, index, contracts, cage_index


# --------------------------------------------------------------------------
# The ladder.
# --------------------------------------------------------------------------
LINK_COLUMNS = [
    "business_source_id", "source_id", "certifying_authority_name",
    "business_name_raw", "business_name_matched_form",
    "link_status", "link_tier", "link_method", "link_rung",
    "matched_uei", "matched_uei_all", "matched_cage",
    "n_candidate_ueis", "candidate_ueis",
    "corroboration", "directory_state", "directory_city",
    "federal_states", "federal_cities",
    "prime_obligations_usd", "prime_obligations_already_attributed_usd",
    "prime_transaction_rows",
    "sam_fy2000_2007_netnew_usd", "sam_fy2000_2007_netnew_rows",
    "subaward_amount_usd", "subaward_rows",
    "first_fiscal_year", "last_fiscal_year", "federal_sources",
    "federal_declared_parent_uei", "federal_declared_parent_name",
    "business_name_is_person_name", "identifier_publish_gate",
    "identifier_publish_gate_basis",
    "evidence_licence", "directory_publishable", "source_terms_status",
    "no_match_reason", "built_by", "built_date",
]

CROSSWALK_COLUMNS = [
    "business_source_id", "source_id", "certifying_authority_name",
    "business_name_raw", "identifier_type", "identifier_value",
    "identifier_tier", "identifier_method", "identifier_evidence",
    "identifier_source_url", "may_publish", "may_publish_basis",
    "built_by", "built_date",
]


def open_crosswalk(built_by):
    """Open the shared crosswalk, dropping only THIS script's previous rows.

    1000 (self-published identifiers) and 1001 (identifiers matched from the
    federal side) both write here. A plain append duplicates on every re-run;
    a plain overwrite lets whichever ran last delete the other's work - the
    rebuild-reverts-the-enricher trap START_HERE records four separate times.
    So each writer rewrites the file keeping every row it did not author.
    """
    kept = []
    if CROSSWALK.exists():
        with open(CROSSWALK, encoding="utf-8-sig", newline="") as fh:
            kept = [r for r in csv.DictReader(fh)
                    if r.get("built_by") != built_by]
    fh = open(CROSSWALK, "w", encoding="utf-8", newline="")
    w = csv.DictWriter(fh, fieldnames=CROSSWALK_COLUMNS)
    w.writeheader()
    for r in kept:
        w.writerow({c: r.get(c, "") for c in CROSSWALK_COLUMNS})
    fh.flush()
    return fh, w


def read_self_published_identifiers():
    """What `code/1000` harvested from the firms' own websites.

    Optional input. If 1000 has not run, this returns {} and the ladder is
    unchanged - the two scripts are independent and either order works.
    """
    out = defaultdict(list)
    if not CROSSWALK.exists():
        return out
    with open(CROSSWALK, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            if r.get("identifier_method") != "self_published_on_firm_website":
                continue
            out[r["business_source_id"]].append(
                (r["identifier_type"], r["identifier_value"],
                 r.get("identifier_source_url", "")))
    return out


def gate_for(name_is_person):
    """cedar_domain.may_publish_individual_native_field, inlined and named.

    THE TENSION, STATED RATHER THAN RESOLVED HERE. The owner's rule is that a
    firm's NAME is not PII even when the firm is named after its owner. Cedar's
    coded policy is narrower and is about the IDENTIFIER, not the name: SAM's
    public entity search resolves a UEI to a name and a street address, so for
    a firm whose legal name is a person's the UEI is a pointer to that
    person's front door. Both can be true. This script therefore writes the
    identifier in every case and marks the gate, so the row is a finding the
    owner can rule on rather than a deletion nobody can see.
    """
    v = str(name_is_person).strip().upper()
    if v in {"0", "FALSE", "NO"}:
        return "PUBLISH", "firm_name_is_not_a_person_name"
    if v in {"1", "TRUE", "YES"}:
        return "WITHHOLD_PENDING_RULING", \
            "cedar_domain.INDIVIDUAL_NATIVE_WITHHELD_FIELDS::awardee_uei"
    return "WITHHOLD_PENDING_RULING", "name_is_person_name_UNKNOWN_fails_closed"


def build(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args(argv)

    biz = list(csv.DictReader(open(DIRECTORY, encoding="utf-8-sig")))
    want_contracts = frozenset(
        t for b in biz for t in contract_tokens(b["federal_contract_number"]))

    print("assembling the federal identifier universe", flush=True)
    ents, index, contracts, cage_index = build_federal_universe(
        want_contracts=want_contracts)
    self_pub = read_self_published_identifiers()
    print(f"self-published identifiers harvested by 1000: "
          f"{sum(len(v) for v in self_pub.values())} on {len(self_pub)} firms",
          flush=True)

    truncated_sources = source_state_column_is_truncated(biz)
    if args.limit:
        biz = biz[:args.limit]
    print(f"directory rows: {len(biz)}", flush=True)
    print(f"sources with a truncated state column: "
          f"{sorted(truncated_sources)}", flush=True)

    REVIEW.mkdir(exist_ok=True)
    lf = open(LINKS, "w", encoding="utf-8", newline="")
    lw = csv.DictWriter(lf, fieldnames=LINK_COLUMNS)
    lw.writeheader()
    xf, xw = open_crosswalk(BUILT_BY)
    hf = open(HOLDS, "w", encoding="utf-8", newline="")
    hw = csv.DictWriter(hf, fieldnames=LINK_COLUMNS)
    hw.writeheader()

    stats = Counter()
    money = Counter()
    linked_ueis = set()
    publishable_ueis = set()
    linked_firm_rows = set()

    for b in biz:
        raw = b["business_name_raw"]
        variants = name_variants(raw)
        dstates = plausible_states(b["state_province"],
                                   widen=b["source_id"] in truncated_sources)
        dstate_ambiguous = len(dstates) > 1
        dcity = norm_city(b["city"])
        nation = b["certifying_authority_name"]
        nstates = NATION_STATES.get(nation, set())
        gate, gate_basis = gate_for(b["business_name_is_person_name"])

        rec = {c: "" for c in LINK_COLUMNS}
        rec.update({
            "business_source_id": b["business_source_id"],
            "source_id": b["source_id"],
            "certifying_authority_name": nation,
            "business_name_raw": raw,
            "directory_state": "|".join(sorted(dstates)),
            "directory_city": dcity,
            "business_name_is_person_name": b["business_name_is_person_name"],
            "identifier_publish_gate": gate,
            "identifier_publish_gate_basis": gate_basis,
            "directory_publishable": b["publishable"],
            "source_terms_status": b["source_terms_status"],
            "built_by": BUILT_BY,
            "built_date": BUILT_DATE,
        })

        # ------------------------------------------------------------------
        # RUNG 0 - THE DIRECTORY PRINTED A FEDERAL CONTRACT NUMBER.
        #
        # This is the only genuinely identifier-first route the directory
        # side offers, and it is worth more than every name rung combined:
        # it resolves BROADLEAF, VISTRONIX, INUTEQ and HIGHLAND TECHNOLOGY -
        # the ASRC Federal operating companies the mandate names precisely
        # because their legal names share no token with their owner and no
        # name matcher can ever reach them.
        #
        # A contract number is only accepted when it resolves to EXACTLY ONE
        # UEI in prime_contracts. A multi-award IDV lists many awardees under
        # one parent PIID - `HC104719D2034` carries two - and taking the
        # largest would be a guess. Two rungs:
        #   0a  a token resolving to one UEI over >= 2 transaction rows
        #   0b  the token's UEIs intersected with the name match, size 1
        # 0a needs two rows because a single stray row under a shared IDV
        # would otherwise look unique.
        # ------------------------------------------------------------------
        toks = contract_tokens(b["federal_contract_number"])
        cn_unique, cn_all = set(), set()
        cn_evidence = []
        for t in toks:
            hits = contracts.get(t)
            if not hits:
                continue
            cn_all |= set(hits)
            if len(hits) == 1:
                only, n = next(iter(hits.items()))
                if n >= 2:
                    cn_unique.add(only)
                    cn_evidence.append(f"{t}->{only}({n} rows)")

        # rule 1 - can this name found a match at all?
        usable = []
        why_not = ""
        for v in variants:
            ok, reason = name_can_carry_a_match(v)
            if ok:
                usable.append(v)
            else:
                why_not = why_not or reason
        cands = set()
        matched_form = ""
        for v in usable:
            hit = index.get(v)
            if hit:
                cands |= hit
                matched_form = matched_form or v

        # ------------------------------------------------------------------
        # RUNG -1 - THE FIRM PUBLISHED ITS OWN UEI OR CAGE.
        # An identifier beats every name method (ENTITY_MATCH_RULES rule 4),
        # and a firm's own capabilities page is the authority on its own
        # identifiers. A published UEI is used directly; a published CAGE is
        # resolved through `fpds_uei_cage_map` and accepted only where it
        # points at ONE UEI.
        # ------------------------------------------------------------------
        sp_ueis, sp_evidence = set(), []
        for typ, val, url in self_pub.get(b["business_source_id"], []):
            if typ == "UEI" and val in ents:
                sp_ueis.add(val)
                sp_evidence.append(f"self_published_UEI={val} <{url}>")
            elif typ == "CAGE":
                hit = cage_index.get(val) or set()
                if len(hit) == 1:
                    sp_ueis |= hit
                    sp_evidence.append(
                        f"self_published_CAGE={val}->{next(iter(hit))} <{url}>")

        rung0 = None
        if len(sp_ueis) == 1:
            rung0 = ("-1_self_published_identifier",
                     "self_published_identifier_resolved_in_contracting",
                     sp_ueis)
        elif len(cn_unique) == 1:
            rung0 = ("0a_published_federal_contract_number",
                     "published_federal_contract_number", cn_unique)
        elif cn_all and len(cn_all & cands) == 1:
            rung0 = ("0b_contract_number_and_name",
                     "name_exact+published_federal_contract_number",
                     cn_all & cands)
        if rung0:
            rung, method, cands = rung0
            tier = "A"
            corrob = (sp_evidence[:3] if rung[0] == "-" else
                      ["contract_number="
                       + (";".join(cn_evidence[:3])
                          or "intersects_the_name_match")])
            merged, geo_note = False, ""
            group = sorted(cands, key=lambda x: -ents[x].prime_oblig)
            u = group[0]
            e = ents[u]
            rec["business_name_matched_form"] = matched_form
            rec["n_candidate_ueis"] = len(group)
            rec["candidate_ueis"] = ";".join(group)
            stats["rung_minus1_self_published"
                  if rung[0] == "-" else "rung0_contract_number"] += 1
        else:
            if not usable:
                rec["link_status"] = "NO_MATCH"
                rec["no_match_reason"] = f"name_cannot_found_a_match:{why_not}"
                stats["refused_generic_name"] += 1
                lw.writerow(rec)
                lf.flush()
                continue
            if not cands:
                rec["link_status"] = "NO_MATCH"
                rec["no_match_reason"] = "no_federal_recipient_of_this_name"
                stats["no_federal_name"] += 1
                lw.writerow(rec)
                lf.flush()
                continue

            rec["business_name_matched_form"] = matched_form
            rec["n_candidate_ueis"] = len(cands)
            rec["candidate_ueis"] = ";".join(sorted(cands))

            # THE VETO, before the ladder. The record's own geography outranks
            # everything: if the directory says a state and a candidate is
            # recorded in a DIFFERENT one, the name collision is with some other
            # firm and the match is refused rather than reconciled.
            #
            # ABSENCE IS NOT DISAGREEMENT. A candidate Cedar knows only from
            # `fpds_uei_cage_map.csv` carries no state at all, and an empty
            # federal state read as a conflict refused 8 of the first 16
            # refusals on evidence that did not exist. A silent candidate falls
            # to a lower rung; it is never vetoed.
            geo_note = ""
            if dstates:
                agreeing = {u for u in cands if dstates & set(ents[u].states)}
                silent = {u for u in cands if not ents[u].states}
                if agreeing:
                    cands = agreeing
                elif silent:
                    cands = silent
                    geo_note = "federal_side_records_no_state_for_this_uei"
                else:
                    rec["link_status"] = "REFUSED"
                    rec["no_match_reason"] = (
                        "state_conflict:directory="
                        + "|".join(sorted(dstates)) + ";federal="
                        + ",".join(sorted({s for u in cands
                                           for s in ents[u].states}))[:80])
                    stats["refused_state_conflict"] += 1
                    lw.writerow(rec)
                    hw.writerow(rec)
                    lf.flush()
                    hf.flush()
                    continue

            # Narrow on the city before deciding the name is ambiguous.
            if len(cands) > 1 and dcity:
                bycity = {u for u in cands if dcity in ents[u].cities}
                if bycity:
                    cands = bycity

            # SUCCESSOR ENTITIES ARE ONE FIRM, NOT AN AMBIGUITY.
            # cedar_ids.mapping_is_defect notes that MANY identifiers per entity
            # is expected - "the 8(a) nine-year term mints successor entities
            # sharing a name and an address." Elite Laundry & Dry Cleaners holds
            # two UEIs, both Gallup NM, $11.2M and $19.0M. Holding that as
            # "ambiguous" throws away $30.2M of a firm Cedar can see perfectly
            # well. So: candidates that share BOTH a city and a state are merged
            # into one link carrying every UEI. Candidates that do not - Arctic
            # Slope Technical Services across NM, CO, AK, AL and MD - stay held.
            merged = False
            if len(cands) > 1:
                common_city = set.intersection(*[set(ents[u].cities)
                                                 for u in cands])
                common_state = set.intersection(*[set(ents[u].states)
                                                  for u in cands])
                if common_city and common_state:
                    merged = True

            # THE LADDER
            rung = tier = method = ""
            corrob = []
            if len(cands) == 1 or merged:
                group = sorted(cands, key=lambda u: -ents[u].prime_oblig)
                u = group[0]
                e = _merge_entities([ents[x] for x in group]) if merged else ents[u]
                agree = dstates & set(e.states)
                if dcity and agree and dcity in e.cities:
                    # Rung 1. Two independent geographic signals on one firm.
                    # An ambiguous recorded state does not weaken this: the city
                    # is doing the work and the state is only not contradicting.
                    rung, tier, method = "1_city_and_state", "A", \
                        "name_exact+city+state"
                    corrob = [f"city={dcity}", "state=" + ",".join(sorted(agree))]
                elif dcity and dcity in e.cities:
                    rung, tier, method = "1b_city_only", "B", "name_exact+city"
                    corrob = [f"city={dcity}"]
                elif agree:
                    # Rung 2. One geographic signal. An ambiguous recorded state
                    # that happens to contain the federal state is weaker evidence
                    # than an unambiguous one and is tiered accordingly.
                    rung = "2_state" if not dstate_ambiguous \
                        else "2b_state_ambiguous_recorded_value"
                    tier = "A" if not dstate_ambiguous else "B"
                    method = "name_exact+state" if not dstate_ambiguous \
                        else "name_exact+state_from_truncated_value"
                    corrob = ["state=" + ",".join(sorted(agree))
                              + ("" if not dstate_ambiguous
                                 else ";recorded_value_was_truncated")]
                elif not dstates and nstates & set(e.states):
                    rung, tier, method = "3_nation_home_state", "B", \
                        "name_exact+certifying_nation_state"
                    corrob = ["nation_state="
                              + ",".join(sorted(nstates & set(e.states)))]
                elif len(distinctive(matched_form)) >= 2:
                    rung, tier, method = "4_unique_distinctive_name", "C", \
                        "name_exact_unique_no_geography"
                    corrob = ["unique_in_federal_universe"]
                else:
                    rung, tier, method = "5_stop", "X", "name_exact_uncorroborated"
                    corrob = ["no_corroborating_signal"]
            else:
                # More than one federal entity answers to this name even after
                # the state filter. mapping_is_defect(): one name over many
                # entities is exactly the shape that must go to review, not to a
                # dollar.
                best = sorted(cands, key=lambda u: -ents[u].prime_oblig)
                rec["link_status"] = "HOLD_AMBIGUOUS"
                rec["link_tier"] = "X"
                rec["link_method"] = "name_exact_multiple_federal_entities"
                rec["link_rung"] = "5_stop"
                rec["no_match_reason"] = (
                    f"{len(cands)} federal entities share this name; "
                    "identifier-first adjudication required")
                rec["candidate_ueis"] = ";".join(best)
                stats["hold_ambiguous"] += 1
                lw.writerow(rec)
                hw.writerow(rec)
                lf.flush()
                hf.flush()
                continue

        cage = e.cages.most_common(1)[0][0] if e.cages else ""
        if merged:
            method += "+successor_entities_merged"
            corrob.append(f"n_ueis={len(group)}")
        if geo_note:
            corrob.append(geo_note)
        rec.update({
            "link_status": "LINKED" if tier in {"A", "B"} else "PROPOSED",
            "link_tier": tier,
            "link_method": method,
            "link_rung": rung,
            "matched_uei": u,
            "matched_uei_all": ";".join(group),
            "matched_cage": cage,
            "n_candidate_ueis": len(group),
            "candidate_ueis": ";".join(group),
            "corroboration": ";".join(corrob),
            "federal_states": ",".join(s for s, _ in e.states.most_common(4)),
            "federal_cities": ",".join(c for c, _ in e.cities.most_common(3)),
            "prime_obligations_usd": f"{e.prime_oblig:.2f}",
            "prime_obligations_already_attributed_usd":
                f"{e.prime_oblig_already_attributed:.2f}",
            "prime_transaction_rows": e.prime_rows,
            "sam_fy2000_2007_netnew_usd": f"{e.sam_backfill_oblig:.2f}",
            "sam_fy2000_2007_netnew_rows": e.sam_backfill_rows,
            "subaward_amount_usd": f"{e.sub_amount:.2f}",
            "subaward_rows": e.sub_rows,
            "first_fiscal_year": e.first_fy,
            "last_fiscal_year": e.last_fy,
            "federal_sources": ";".join(sorted(e.sources)),
            "federal_declared_parent_uei":
                (e.parents.most_common(1)[0][0][0] if e.parents else ""),
            "federal_declared_parent_name":
                (e.parents.most_common(1)[0][0][1] if e.parents else ""),
            "evidence_licence": ("DNB_OPEN_DATA_RESTRICTED_NAME_EVIDENCE"
                                 if e.restricted_name_only else "OPEN"),
        })
        lw.writerow(rec)
        if tier in {"C", "X"}:
            hw.writerow(rec)
            hf.flush()
        lf.flush()

        stats[f"link_tier_{tier}"] += 1
        if tier in {"A", "B"}:
            stats["linked_rows"] += 1
            # DOLLARS ARE SUMMED PER UEI, NEVER PER DIRECTORY ROW. Tiger
            # Natural Gas is certified by BOTH Cherokee Nation and Muscogee
            # (Creek) Nation and iina' ba' appears three times in the Navajo
            # list under three spellings. Summing rows would report $908M
            # twice and $19.7M three times - the double-count is invisible in
            # a total and obvious in a per-UEI ledger.
            for one in group:
                if one not in linked_ueis:
                    linked_ueis.add(one)
                    money["prime"] += ents[one].prime_oblig
                    money["prime_already_attributed"] +=                         ents[one].prime_oblig_already_attributed
                    money["sam_netnew"] += ents[one].sam_backfill_oblig
                    money["sub"] += ents[one].sub_amount
            if b["publishable"] == "Y":
                stats["linked_publishable_rows"] += 1
                for one in group:
                    if one not in publishable_ueis:
                        publishable_ueis.add(one)
                        money["prime_publishable"] += ents[one].prime_oblig
                        money["sam_netnew_publishable"] +=                             ents[one].sam_backfill_oblig
                        money["sub_publishable"] += ents[one].sub_amount

        # crosswalk rows - one per identifier, flushed per entity
        for typ, val in ([("UEI", x) for x in group]
                         + [("CAGE", cage)]):
            if not val:
                continue
            xw.writerow({
                "business_source_id": b["business_source_id"],
                "source_id": b["source_id"],
                "certifying_authority_name": nation,
                "business_name_raw": raw,
                "identifier_type": typ,
                "identifier_value": val,
                "identifier_tier": tier,
                "identifier_method": method,
                "identifier_evidence": (
                    "read from Cedar federal contracting tables ("
                    + ";".join(sorted(e.sources)) + "); corroborated by "
                    + (";".join(corrob) or "nothing")),
                "identifier_source_url": "",
                "may_publish": ("Y" if (gate == "PUBLISH"
                                        and tier in {"A", "B"}
                                        and b["publishable"] == "Y")
                                else "N"),
                "may_publish_basis": (
                    f"gate={gate};tier={tier};"
                    f"directory_publishable={b['publishable']}"),
                "built_by": BUILT_BY,
                "built_date": BUILT_DATE,
            })
        xf.flush()

    lf.close()
    xf.close()
    hf.close()

    # ---- the customer-facing rollup -------------------------------------
    # One row per certifying authority. Dollars are per DISTINCT UEI within
    # the nation, so a firm certified by two nations counts once in each
    # nation's own figure and once in the project total - the two are
    # different questions and the column names say which.
    nat = {}
    seen_by_nation = {}
    for r in csv.DictReader(open(LINKS, encoding="utf-8-sig")):
        n = r["certifying_authority_name"]
        d = nat.setdefault(n, Counter())
        d["firms_certified"] += 1
        d["publishable_rows"] += 1 if r["directory_publishable"] == "Y" else 0
        st = r["link_status"]
        d[f"status_{st.lower()}"] += 1
        if st == "LINKED":
            d["firms_linked_to_contracting"] += 1
            for one in (r["matched_uei_all"] or r["matched_uei"]).split(";"):
                if one and one not in seen_by_nation.setdefault(n, set()):
                    seen_by_nation[n].add(one)
                    d["distinct_ueis"] += 1
    for n in nat:
        nat[n]["prime_obligations_usd"] = 0.0
        nat[n]["sam_fy2000_2007_netnew_usd"] = 0.0
        nat[n]["subaward_amount_usd"] = 0.0
    counted = {}
    for r in csv.DictReader(open(LINKS, encoding="utf-8-sig")):
        if r["link_status"] != "LINKED":
            continue
        n = r["certifying_authority_name"]
        for one in (r["matched_uei_all"] or r["matched_uei"]).split(";"):
            if not one or one in counted.setdefault(n, set()):
                continue
            counted[n].add(one)
            nat[n]["prime_obligations_usd"] += ents[one].prime_oblig
            nat[n]["sam_fy2000_2007_netnew_usd"] += ents[one].sam_backfill_oblig
            nat[n]["subaward_amount_usd"] += ents[one].sub_amount
    cols = ["certifying_authority_name", "firms_certified", "publishable_rows",
            "firms_linked_to_contracting", "distinct_ueis",
            "prime_obligations_usd", "sam_fy2000_2007_netnew_usd",
            "subaward_amount_usd",
            "status_no_match", "status_refused", "status_hold_ambiguous",
            "status_proposed", "link_rate_pct", "built_by", "built_date"]
    with open(BY_NATION, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for n in sorted(nat, key=lambda k: -nat[k]["prime_obligations_usd"]):
            d = nat[n]
            row = {c: d.get(c, 0) for c in cols}
            row["certifying_authority_name"] = n
            row["prime_obligations_usd"] = f"{d['prime_obligations_usd']:.2f}"
            row["sam_fy2000_2007_netnew_usd"] =                 f"{d['sam_fy2000_2007_netnew_usd']:.2f}"
            row["subaward_amount_usd"] = f"{d['subaward_amount_usd']:.2f}"
            row["link_rate_pct"] = round(
                100.0 * d["firms_linked_to_contracting"]
                / max(1, d["firms_certified"]), 1)
            row["built_by"] = BUILT_BY
            row["built_date"] = BUILT_DATE
            w.writerow(row)
            fh.flush()

    # ---- reconcile against the OTHER matcher ------------------------------
    # `code/953_nob_federal_identifier_candidates.py` (the 950-959 agent) wrote
    # `federal_uei_candidate` onto the directory itself, by a different method:
    # name-only, no geography, refusing person names and ambiguity. Two
    # matchers over the same evidence is not two SOURCES (ASSERTION_LAYER:
    # evidence lineage), so agreement is not corroboration - but DISAGREEMENT
    # is a finding, and it is the cheapest defect detector either pass has.
    recon = Counter()
    if "federal_uei_candidate" in (biz[0] if biz else {}):
        mine = {r["business_source_id"]:
                (r["matched_uei"] if r["link_status"] == "LINKED" else "")
                for r in csv.DictReader(open(LINKS, encoding="utf-8-sig"))}
        for b2 in biz:
            a = (b2.get("federal_uei_candidate") or "").strip().upper()
            m = mine.get(b2["business_source_id"], "")
            if a and m:
                recon["both_matched_agree" if a == m
                      else "BOTH_MATCHED_DISAGREE"] += 1
            elif a:
                recon["only_953_matched"] += 1
            elif m:
                recon["only_1001_matched"] += 1
            else:
                recon["neither_matched"] += 1

    summary = {
        "built_by": BUILT_BY,
        "built_date": BUILT_DATE,
        "directory_rows": len(biz),
        "federal_ueis_indexed": len(ents),
        "stats": dict(stats),
        "distinct_ueis_linked": len(linked_ueis),
        "distinct_ueis_linked_publishable": len(publishable_ueis),
        "prime_obligations_exposed_usd": round(money["prime"], 2),
        "prime_of_which_already_attributed_to_a_cedar_entity_usd":
            round(money["prime_already_attributed"], 2),
        "prime_of_which_previously_unattributed_usd":
            round(money["prime"] - money["prime_already_attributed"], 2),
        "prime_obligations_exposed_publishable_usd":
            round(money["prime_publishable"], 2),
        "sam_fy2000_2007_netnew_exposed_usd": round(money["sam_netnew"], 2),
        "sam_fy2000_2007_netnew_exposed_publishable_usd":
            round(money["sam_netnew_publishable"], 2),
        "subaward_amount_exposed_usd": round(money["sub"], 2),
        "subaward_amount_exposed_publishable_usd":
            round(money["sub_publishable"], 2),
        "dollar_grain": "summed once per distinct UEI, never per directory "
                        "row - 8 firms are certified by two nations and 3 "
                        "Navajo spellings resolve to one firm",
        "reconciliation_vs_953_matcher": dict(recon),
        "reconciliation_note": (
            "two matchers over the SAME evidence - agreement is not "
            "corroboration (docs/ASSERTION_LAYER.md, evidence lineage); "
            "disagreement is a defect signal in one of them"),
        "nation_states_basis": NATION_STATES_BASIS,
    }
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


# --------------------------------------------------------------------------
# verify - the invariants. Exits 1 when one breaks.
# --------------------------------------------------------------------------
def verify(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true",
                    help="prove the invariants fire on injected violations")
    args = ap.parse_args(argv)

    fails = []

    def check(name, ok, detail=""):
        print(f"  {'PASS' if ok else 'FAIL'}  {name}"
              + (f"  {detail}" if detail else ""))
        if not ok:
            fails.append(name)

    if args.synthetic:
        print("SYNTHETIC VIOLATIONS - each of these MUST be caught")
        bad = [
            {"business_source_id": "SYN:1", "matched_uei": "TOOSHORT",
             "matched_cage": "", "link_tier": "A", "link_status": "LINKED",
             "identifier_publish_gate": "PUBLISH", "corroboration": "state=OK",
             "n_candidate_ueis": "1"},
            {"business_source_id": "SYN:2", "matched_uei": "ABCDEFGH1234",
             "matched_cage": "TOOLONGCAGE", "link_tier": "A",
             "link_status": "LINKED", "identifier_publish_gate": "PUBLISH",
             "corroboration": "state=OK", "n_candidate_ueis": "1"},
            {"business_source_id": "SYN:3", "matched_uei": "ABCDEFGH1234",
             "matched_cage": "", "link_tier": "A", "link_status": "LINKED",
             "identifier_publish_gate": "PUBLISH", "corroboration": "",
             "n_candidate_ueis": "1"},
            {"business_source_id": "SYN:4", "matched_uei": "ABCDEFGH1234",
             "matched_cage": "", "link_tier": "A", "link_status": "LINKED",
             "identifier_publish_gate": "PUBLISH", "corroboration": "state=OK",
             "n_candidate_ueis": "3"},
        ]
        caught = _invariants(bad)
        check("synthetic malformed UEI caught", "malformed_uei" in caught)
        check("synthetic malformed CAGE caught", "malformed_cage" in caught)
        check("synthetic tier-A without corroboration caught",
              "tier_A_without_corroboration" in caught)
        check("synthetic linked-but-ambiguous caught",
              "linked_with_multiple_candidates" in caught)
        # rule 1 must refuse an all-generic name
        ok, _ = name_can_carry_a_match("NATIVE CONSTRUCTION")
        check("synthetic all-generic name refused", not ok)
        ok, _ = name_can_carry_a_match("EDWARDS CONSTRUCTION")
        check("distinctive name still accepted", ok)
        check("ambiguous truncation widens rather than picking",
              plausible_states("Ne", widen=True)
              == frozenset({"NE", "NV", "NH", "NJ", "NM", "NY"}))
        check("unambiguous truncation resolves",
              plausible_states("Ariz") == frozenset({"AZ"}))
        check("a plain abbreviation is read as itself",
              plausible_states("AL") == frozenset({"AL"}))
        check("truncation-prone source detected from the data",
              source_state_column_is_truncated(
                  [{"source_id": "X", "state_province": "Ariz"},
                   {"source_id": "Y", "state_province": "AZ"}]) == {"X"})
        check("'NAN' cage rejected", clean_cage("NAN") == "")
        check("a CAGE containing O is rejected", clean_cage("JONES") == "")
        check("a UEI containing I is rejected",
              clean_uei("ABCDEFGHI234") == "")
        check("a well-formed UEI survives",
              clean_uei("HZN6BEYJP5G6") == "HZN6BEYJP5G6")
        return 1 if fails else 0

    if not LINKS.exists():
        print("FAIL  links file absent - run `build` first")
        return 1

    rows = list(csv.DictReader(open(LINKS, encoding="utf-8-sig")))
    dirn = sum(1 for _ in csv.reader(open(DIRECTORY, encoding="utf-8-sig"))) - 1

    check("row conservation: one link row per directory row",
          len(rows) == dirn, f"{len(rows)} vs {dirn}")

    caught = _invariants(rows)
    for k in ("malformed_uei", "malformed_cage", "tier_A_without_corroboration",
              "linked_with_multiple_candidates", "linked_without_identifier"):
        check(f"no {k}", k not in caught, caught.get(k, ""))

    # restricted sources must never be marked publishable in the crosswalk
    if CROSSWALK.exists():
        xr = list(csv.DictReader(open(CROSSWALK, encoding="utf-8-sig")))
        bad = [r for r in xr if r["may_publish"] == "Y"
               and r["identifier_type"] == "DUNS"]
        check("no DUNS marked publishable", not bad, str(len(bad)))
        restricted_sids = {r["source_id"] for r in
                           csv.DictReader(open(DIRECTORY, encoding="utf-8-sig"))
                           if r["source_terms_status"]
                           == "TERMS_STATED_RESTRICTIVE"}
        bad = [r for r in xr if r["may_publish"] == "Y"
               and r["source_id"] in restricted_sids]
        check("no TERMS_STATED_RESTRICTIVE source marked publishable",
              not bad, str(len(bad)))

    print("\nVERIFY " + ("FAILED: " + ", ".join(fails) if fails else "OK"))
    return 1 if fails else 0


def _invariants(rows):
    """Returns {invariant_name: example}. Empty dict means clean."""
    out = {}
    for r in rows:
        u = (r.get("matched_uei") or "").strip()
        c = (r.get("matched_cage") or "").strip()
        tier = (r.get("link_tier") or "").strip()
        status = (r.get("link_status") or "").strip()
        sid = r.get("business_source_id", "?")
        for one in [u] + (r.get("matched_uei_all") or "").split(";"):
            one = one.strip()
            if one and not UEI_RE.match(one):
                out.setdefault("malformed_uei", f"{sid}:{one}")
        if c and not CAGE_RE.match(c):
            out.setdefault("malformed_cage", f"{sid}:{c}")
        if tier == "A" and status == "LINKED" and not (
                r.get("corroboration") or "").strip():
            out.setdefault("tier_A_without_corroboration", sid)
        if status == "LINKED":
            try:
                n = int(r.get("n_candidate_ueis") or 0)
            except ValueError:
                n = 0
            if n > 1 and "successor_entities_merged" not in (
                    r.get("link_method") or ""):
                out.setdefault("linked_with_multiple_candidates", sid)
            if not u:
                out.setdefault("linked_without_identifier", sid)
    return out


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in {"build", "verify"}:
        print(__doc__)
        return 2
    return build(sys.argv[2:]) if sys.argv[1] == "build" \
        else verify(sys.argv[2:])


if __name__ == "__main__":
    sys.exit(main())
