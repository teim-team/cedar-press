#!/usr/bin/env python3
"""
Cedar Press - 1155: the nonprofit place-name collision, measured then demoted.

    py -3 code/1155_np_placename_precision.py sample    # draw the seeded review sample
    py -3 code/1155_np_placename_precision.py report    # measure; no write
    py -3 code/1155_np_placename_precision.py apply     # demote, flag never delete
    py -3 code/1155_np_placename_precision.py audit     # sample the APPLIED set
    py -3 code/1155_np_placename_precision.py codebook  # register the 3 new columns
    py -3 code/1155_np_placename_precision.py verify    # exit 1 if the work did not land
    py -3 code/1155_np_placename_precision.py selftest  # inject each violation, assert RED

WHAT THIS IS ABOUT
------------------
`np_orgs.csv` carries 1,423 rows with BOTH `tribe_id` and `cedar_uid` populated.
That conjunction is the LINKED numerator in `docs/LINKAGE_COVERAGE.md` (11.15%)
and the ratcheted `linkage_nonprofits_*` metric in `62_no_regression_check.py`.

A Native nation's name is very often ALSO an American place name, and the
upstream token matcher treats the token as evidence of Native identity:

    COQUILLE CHESS CLUB          Coquille OR   -> Coquille Indian Tribe
    CHEHALIS BALLET CENTER       Chehalis WA   -> Chehalis Tribe
    SENECA ZOOLOGICAL SOCIETY    Rochester NY  -> Seneca Nation
    SHAKOPEE BAND BOOSTERS       Shakopee MN   -> Shakopee Mdewakanton
    MILLE LACS COUNTY SEARCH & RESCUE TEAM     -> Mille Lacs Band

WHY THE EXISTING GUARD DOES NOT REACH THEM
------------------------------------------
`code/1101_np_keyed_name_support.py` holds 461 of the 1,423 on
`HELD_STATE_DISAGREES`. `docs/ENTITY_MATCH_RULES.md` already warns that state
agreement is a poor gate. On THIS failure mode it is worse than poor: a town
named after a nation is almost always in that nation's own state, so state
agreement is ANTI-correlated with correctness. Every row above is
`keyed_state_agreement = Y` and `key_review_disposition = SUPPORTED`.

THE STRUCTURAL PREDICATE
------------------------
Not a denylist of tribe names - a test of what the shared token is DOING in
this particular record. Two rungs, both computed from data Cedar already holds
(IRS BMF city/state, the org's own name, the spine's official names):

  P1  THE MATCHED TOKEN IS THIS ORGANISATION'S OWN POSTAL PLACE.
      The nation's distinctive token(s) appear in the organisation's BMF CITY.
      If the word that matched is literally the name of the town the filer sits
      in, the word is functioning as an address in that record.
      Data-driven; no list of tribe names anywhere in it.

  P2  THE MATCHED TOKEN IS QUALIFIED AS GEOGRAPHY IN THE NAME ITSELF.
      The token is immediately followed by a US geographic-form noun
      (COUNTY, FALLS, LAKE, VALLEY, BEACH, RIVER, ...). `SENECA COUNTY` and
      `SENECA FALLS` are places; `SENECA NATION` is a people. This is a pattern
      over a closed class of geography words, not a list of entities - the
      distinction `docs/ENTITY_MATCH_RULES.md` draws between a structural
      predicate and a denylist.

  VETO  Either rung is REFUSED where the record carries a positive Native
        signal that outranks it, because blocking on weak evidence is safe in a
        way awarding on it is not, and the reverse must be true too:
          - explicit tribal-purpose language in the organisation's own name
            (rule 7's "the record's own words outrank geography"), or
          - an INDEPENDENT evidence family naming this EIN: a Single Audit
            filed under `entity_type = tribal`, an EIN<->UEI federal-assistance
            bridge row, or a Schedule I grant relationship. `np_ein_entity_hub`
            is NOT independent - it covers 1,416 of the 1,423 and is the same
            name matcher seen twice.
          - THE TOWN IS THE NATION'S OWN SEAT. Zuni NM, Siletz OR, Crow
            Agency MT and Kasaan AK are towns named after a nation because the
            nation is there. This veto gates P1 ONLY: P1 is a geographic
            inference and a seat is geographic evidence against it, while P2
            reads the organisation's OWN NAME, and rule 7 says the record's own
            words outrank geography in both directions.

            Four sources, because no one of them reaches every entity:
              1. `fac_tribal_single_audits`   where a nation's own government
                 files its Single Audit
              2. `fac_native_nontribal_single_audits`  smaller bodies
              3. `gaming_facilities`
              4. the BIA Tribal Leaders Directory, joined by EXACT normalised
                 name against the spine's own published names and used only on
                 a UNIQUE match: 540 of 583 unique, 42 ambiguous, 1 unmatched,
                 all discarded but the 540. A name join may do this because it
                 only ever BLOCKS a refusal.
            1-3 take a DOMINANCE test: a city is the seat only if it holds at
            least half that entity's anchored observations. Two stray 2021-22
            filings that print `CHEHALIS` where fifteen other years print
            `OAKVILLE` would otherwise have vetoed 22 correct refusals.

            All four are FILINGS or a directory, and that is their blind spot: a
            village of sixty people files no Single Audit, runs no casino, and
            gives the BIA a P.O. box in the nearest town. So a fifth route is
            structural rather than evidential - AN ENTITY CLASS THAT IS A PLACE.
            A `Federally recognized Alaska Native Village` sits at the village
            it is named for; that is what the class means. Guarded by state
            agreement, without which `EAGLE BUTTE LAKOTA CHAPEL` in Eagle Butte
            SD reads as sitting in the Native Village of Eagle, ALASKA. NOT
            extended to `Federally recognized tribe`: measured, that would veto
            114 of the refusals, because Coquille OR, Chehalis WA, Shakopee MN
            and Seneca Falls NY bear a nation's name and are NOT its seat.

            The spine's own `city` column cannot serve at all - it is blank on
            all 238 keyed entities.

WHAT IT DOES, AND WHAT IT REFUSES TO DO
---------------------------------------
FLAG AND NEVER DELETE. No row is removed and no `cedar_uid` is minted, reused
or overwritten. A demoted row keeps every column it had, and gains:

    key_review_disposition = REFUSED_PLACE_NAME_IS_THE_ADDRESS
    key_review_basis       = the rung that fired, the token, and the evidence

`REFUSED_*` is an existing value class in this column
(`REFUSED_GENERIC_TOKEN_ONLY`) - the vocabulary this pass joins rather than a
second one. A verdict another pass already recorded is EVIDENCE and is left
standing: only `SUPPORTED` is overwritten, and the 220 rows already reading
`HELD_STATE_DISAGREES` keep `code/1101`'s finding and carry the refusal in the
`placename_refusal_*` columns instead.

THE ONE CROSS-LANE EDIT, AND WHY IT IS NOT OPTIONAL
---------------------------------------------------
`code/cedar_publication.py` is DENY-BY-DEFAULT: a `key_review_disposition`
value its vocabulary has never seen WITHHOLDS the whole row, not the key. So one
line was added to `BLOCKED_STATES["key_review_disposition"]`:

    "REFUSED_PLACE_NAME_IS_THE_ADDRESS": MASK,

MASK is what the three sibling refusal values already do - the IRS record is
real and ships, the contested key does not, and `MASK_COLS` already blanks
`cedar_uid`, `tribe_id`, `tribe_canonical_name`, `cedar_spine_entity_id`,
`cedar_spine_canonical_name` and `cedar_link_key` for this column. **Drop that
line and every demoted filing vanishes from the export.** Invariant I6 below reads
that file and fails if the entry is gone; `selftest` proves I6 fires.

A refusal says ONLY "this is not THAT entity." It is not a finding that the
organisation is not Native. Several demoted rows plainly deserve their own
spine entity.

ONE-WAY. This pass can only WITHDRAW a claim. It may not promote, and it may
not mint tier A - `docs/ENTITY_MATCH_RULES.md` rule 8.
"""
from __future__ import annotations

import csv
import json
import random
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()

NP = ROOT / "data" / "clean" / "np_orgs.csv"
SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
REVIEW = ROOT / "review"
SAMPLE_OUT = REVIEW / "np_placename_precision_sample_2026-09-02.csv"
LABELS_IN = REVIEW / "np_placename_precision_labels_2026-09-02.csv"
# The stratum POPULATIONS as they stood when the sample was drawn, written by
# `sample` and read by `report`. Without this the weighted figure silently
# re-weights against the post-`apply` strata and drifts - 17.7% became 13.5%
# the first time, which is the whole dataset's own bug class: a number that was
# produced, was plausible, and was about something else.
STRATA_AT_DRAW = REVIEW / "np_placename_precision_strata_2026-09-02.json"

SEED = 20260902
N_SUPPORTED = 150
N_MASKED = 60

DISPOSITION_VALUE = "REFUSED_PLACE_NAME_IS_THE_ADDRESS"

# ---------------------------------------------------------------------------
# Vocabulary. Two closed classes, each doing one job, each stated here so a
# later pass can re-judge without re-deriving.
# ---------------------------------------------------------------------------

# P2: US geographic-form nouns. A word that turns a name into a location.
# Not tribe names, not organisation forms - only the words that make
# "<X> COUNTY" a place. Adding a word only ever makes P2 fire more.
GEO_FORM = {
    "COUNTY", "COUNTIES", "PARISH", "TOWNSHIP", "BOROUGH", "MUNICIPALITY",
    "CITY", "TOWN", "VILLAGE", "HAMLET",
    "FALLS", "LAKE", "LAKES", "RIVER", "CREEK", "BAY", "HARBOR", "HARBOUR",
    "BEACH", "SHORE", "SHORES", "ISLAND", "ISLANDS", "POINT", "POINTE",
    "VALLEY", "HILL", "HILLS", "RIDGE", "MOUNTAIN", "MESA", "BUTTE", "CANYON",
    "SPRINGS", "SPRING", "WOODS", "FOREST", "GROVE", "PARK", "PARKWAY",
    "HEIGHTS", "MEADOWS", "PRAIRIE", "PLAINS", "GARDENS",
    "STREET", "AVENUE", "ROAD", "TRAIL", "PIKE", "SQUARE", "PLAZA",
    "BASIN", "WATERSHED", "ESTUARY", "SOUND", "INLET", "PENINSULA", "MARSH",
}

# The VETO: the organisation's own words claiming a Native identity. Reused
# in spirit from `17_build_nonprofit_990.py::TRIBAL_PURPOSE_RE`, widened to the
# bare identity words, because here it is used only to BLOCK a refusal - never
# to award a match - and over-blocking is the safe direction.
NATIVE_PURPOSE_RE = re.compile(
    r"\b(TRIBE|TRIBES|TRIBAL|NATION|NATIONS|RESERVATION|RANCHERIA|PUEBLO|"
    r"BAND|BANDS|NATIVE|INDIAN|INDIANS|INDIGENOUS|ABORIGINAL|"
    r"ANCESTRAL|SOVEREIGN|POWWOW|POW WOW|IHS|BIA|BIE|"
    r"ALASKA NATIVE|NATIVE HAWAIIAN|FIRST NATION)\b")

# Words that carry no identifying power on their own; the same floor
# `code/610_repair_generic_containment_links.py` uses, so the two passes agree
# about what "distinctive" means.
GENERIC = {
    "THE", "OF", "AND", "FOR", "A", "AN", "INC", "INCORPORATED", "LLC", "LTD",
    "CO", "CORP", "CORPORATION", "COMPANY", "ASSOCIATION", "ASSN", "SOCIETY",
    "FOUNDATION", "INSTITUTE", "CENTER", "CENTRE", "COUNCIL", "COMMITTEE",
    "BOARD", "COMMISSION", "AUTHORITY", "ALLIANCE", "COALITION", "CONSORTIUM",
    "SERVICES", "SERVICE", "PROGRAM", "PROGRAMS", "PROJECT", "COMMUNITY",
    "COMMUNITIES", "DEVELOPMENT", "ENTERPRISE", "ENTERPRISES", "GROUP",
    "HOLDINGS", "PARTNERS", "SYSTEMS", "SOLUTIONS", "CLUB", "TRUST",
    "NATIVE", "NATIVES", "AMERICAN", "AMERICANS", "INDIAN", "INDIANS",
    "INDIGENOUS", "TRIBAL", "TRIBE", "TRIBES", "NATION", "NATIONS", "BAND",
    "PEOPLE", "PEOPLES", "FIRST", "HEALTH", "HEALTHCARE", "MEDICAL",
}


def toks(s: str) -> list:
    return [t for t in re.sub(r"[^A-Za-z0-9 ]", " ", (s or "").upper()).split() if t]


def distinctive(s: str) -> set:
    return {t for t in toks(s) if t not in GENERIC}


def read_csv(p: Path) -> tuple:
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        return list(rd.fieldnames or []), list(rd)


def norm_ein(x) -> str:
    s = str(x or "").strip().replace("-", "")
    return s.zfill(9) if s and s.lower() != "nan" else ""


def ein_set(path: Path, col: str) -> set:
    if not path.exists():
        return set()
    out = set()
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            e = norm_ein(r.get(col))
            if e:
                out.add(e)
    return out


# The seat anchor. Tables that carry a Cedar entity key AND an address, none of
# them np_orgs - an instrument may never scan its own output
# (`docs/AGENT_FIELD_GUIDE.md` rule 10).
#
# The first two are federal FILINGS, and that is their weakness: a village of
# 60 people files no Single Audit and runs no casino, so they systematically
# miss the population where the town and the nation share a name most often.
# `KASAAN HAIDA HERITAGE FOUNDATION`, in Kasaan AK, seat of the Organized
# Village of Kasaan, was refused for exactly that reason. Two sources were
# added and both were measured before adoption - see `docs/NP_PLACENAME_
# PRECISION_1155.md` -10.
SEAT_SOURCES = [
    ("fac_tribal_single_audits.csv", "entity_id", "auditee_city", "auditee_state"),
    ("gaming_facilities.csv", "tribe_id", "city", "state"),
    # `fac_native_nontribal_single_audits` reaches bodies too small for the
    # tribal-audit table.
    ("fac_native_nontribal_single_audits.csv", "entity_id",
     "auditee_city", "auditee_state"),
]
SEAT_DOMINANCE = 0.50

# The BIA Tribal Leaders Directory publishes an address for every federally
# recognized tribe, including the small Alaska villages no filing reaches. It
# carries no Cedar key, so it is joined by EXACT normalised name against the
# spine's own published names and a row is used only where the match is UNIQUE:
# 540 of 583 unique, 42 ambiguous and 1 unmatched, all discarded but the 540.
# A name join may do this because it only ever BLOCKS a refusal.
TLD = "bia_tribal_leaders_directory.csv"
TLD_NAME_DROP = {
    "THE", "OF", "A", "AN", "AND", "INDIANS", "INDIAN", "TRIBE", "TRIBES",
    "NATION", "NATIONS", "BAND", "BANDS", "COMMUNITY", "RESERVATION",
    "PUEBLO", "RANCHERIA", "VILLAGE", "NATIVE", "TRIBAL", "GOVERNMENT",
    "COUNCIL", "INC", "CONFEDERATED", "FEDERATED",
}

# An entity class that IS a place. A village government sits at the village it
# is named for - that is what the class means, and it needs no filing to
# establish. Deliberately NOT extended to `Federally recognized tribe`:
# measured, that would veto 114 of the 293 refusals, because Coquille OR,
# Chehalis WA, Shakopee MN, Seneca Falls NY and West Seneca NY are towns that
# bear a nation's name and are NOT that nation's seat. The class distinction is
# load-bearing and the measurement is in the doc.
SEAT_BY_CLASS = {"Federally recognized Alaska Native Village"}


def _tld_key(s: str) -> str:
    return " ".join(t for t in toks(s) if t not in TLD_NAME_DROP)


_CLEAN_STATE_FN = []


def _clean_state(v: str) -> str:
    """`cedar_pipeline.clean_state`, so this pass and 01/71 agree what a state is.

    The TLD writes `Alaska` where the BMF writes `AK`; comparing them raw is a
    silent no-match. Imported rather than copied - two copies of a validator is
    how the two of them drift apart, which is what that module's own comment
    says about why it lives there.
    """
    if not _CLEAN_STATE_FN:
        import importlib.util
        sp = importlib.util.spec_from_file_location(
            "cedar_pipeline_for_1155", ROOT / "code" / "cedar_pipeline.py")
        m = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(m)
        _CLEAN_STATE_FN.append(m.clean_state)
    return _CLEAN_STATE_FN[0](v)[0]


def seat_places(spine: dict) -> dict:
    """entity_id -> {(CITY, STATE)} that source says is that entity's own seat.

    `spine` is tribe_id -> spine row. Two independent routes, unioned:
    a DOMINANT address across the filing tables, and the BIA directory's
    published address for a uniquely-matched tribe.
    """
    obs = defaultdict(Counter)
    for fname, idk, ck, sk in SEAT_SOURCES:
        p = ROOT / "data" / "clean" / fname
        if not p.exists():
            continue
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            for r in csv.DictReader(fh):
                t = (r.get(idk) or "").strip()
                c = (r.get(ck) or "").strip().upper()
                s = _clean_state(r.get(sk))
                if t and c:
                    obs[t][(c, s)] += 1
    out = {}
    for t, c in obs.items():
        n = sum(c.values())
        out[t] = {k for k, v in c.items() if v / n >= SEAT_DOMINANCE}

    # -- the BIA directory, joined by unique exact normalised name
    idx = defaultdict(set)
    for tid, s in spine.items():
        for nm in ([s.get("canonical_name"), s.get("fr_official_name")]
                   + (s.get("aliases") or "").split("|")):
            k = _tld_key(nm)
            if k:
                idx[k].add(tid)
    p = ROOT / "data" / "clean" / TLD
    if p.exists():
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            for r in csv.DictReader(fh):
                cands = set()
                for nm in (r.get("tribefullname"), r.get("tribe"),
                           r.get("tribealternatename")):
                    cands |= idx.get(_tld_key(nm), set())
                if len(cands) != 1:
                    continue          # ambiguous or unmatched: discarded
                tid = next(iter(cands))
                for ck, sk in (("city", "state"),
                               ("mailingaddresscity", "mailingaddressstate")):
                    c = (r.get(ck) or "").strip().upper()
                    s = _clean_state(r.get(sk))
                    if c:
                        out.setdefault(tid, set()).add((c, s))
                        break

    return out


def seat_by_class(spine_row: dict, city: str, state: str) -> bool:
    """The class rule, evaluated per row: is this filer IN the village?

    True when the keyed entity is a village government, every distinctive token
    of its own name is in the filer's city, and the states agree. State
    agreement is not decoration - without it `EAGLE BUTTE LAKOTA CHAPEL`, Eagle
    Butte SD, would be read as sitting in the Native Village of Eagle, ALASKA.
    """
    if spine_row.get("entity_class") not in SEAT_BY_CLASS:
        return False
    own = distinctive(spine_row.get("canonical_name"))
    if not own or not own <= set(toks(city)):
        return False
    return ((state or "").strip().upper()
            == (spine_row.get("state") or "").strip().upper())


# ---------------------------------------------------------------------------
# The evidence bundle every subcommand shares
# ---------------------------------------------------------------------------
def load():
    cols, rows = read_csv(NP)
    _, spine_rows = read_csv(SPINE)
    spine = {}
    for s in spine_rows:
        tid = (s.get("tribe_id") or "").strip()
        if tid:
            spine[tid] = s

    clean = ROOT / "data" / "clean"
    # INDEPENDENT evidence families only. `np_ein_entity_hub` is deliberately
    # absent: it names 1,416 of the 1,423 keyed EINs, so it is the same name
    # matcher seen a second time, not a second witness.
    fams = {
        "fac_tribal_single_audit": ein_set(clean / "fac_tribal_single_audits.csv", "auditee_ein"),
        "ein_uei_federal_assistance_bridge": ein_set(clean / "np_ein_uei_bridge.csv", "ein"),
        "schedule_i_grant_recipient": ein_set(clean / "np_schedule_i_grants.csv", "recipient_ein"),
        "schedule_i_grant_filer": ein_set(clean / "np_schedule_i_grants.csv", "filer_ein"),
        "grantmaker_flow_recipient": ein_set(clean / "grantmaker_funding_flows.csv", "recipient_ein"),
    }

    seats = seat_places(spine)
    linked = [r for r in rows
              if (r.get("tribe_id") or "").strip() and (r.get("cedar_uid") or "").strip()]
    for r in linked:
        e = norm_ein(r.get("EIN"))
        tid = (r.get("tribe_id") or "").strip()
        hits = sorted(k for k, s in fams.items() if e in s)
        r["_corroborators"] = hits
        s = spine.get(tid, {})
        r["_spine_state"] = (s.get("state") or "").strip()
        r["_spine_city"] = (s.get("city") or "").strip()
        r["_spine_class"] = (s.get("entity_class") or "").strip()
        r["_spine_official"] = " ".join([
            s.get("canonical_name") or "", s.get("fr_official_name") or "",
            (s.get("aliases") or "").replace("|", " ")])
        r["_seats"] = seats.get(tid, set())
        r["_seat_by_class"] = seat_by_class(s, r.get("city"), r.get("state"))
    return cols, rows, linked


# ---------------------------------------------------------------------------
# The predicate
# ---------------------------------------------------------------------------
def matched_tokens(row) -> set:
    """The distinctive tokens the org name and the keyed nation actually share."""
    org = distinctive(row.get("org_name"))
    nat = distinctive(row.get("_spine_official") or row.get("tribe_canonical_name"))
    return org & nat


def classify(row) -> tuple:
    """-> (fires: bool, rung: str, basis: str). One-way: refusal or nothing."""
    shared = matched_tokens(row)
    if not shared:
        return False, "", "no shared distinctive token with the keyed entity"

    name_t = toks(row.get("org_name"))
    city_t = set(toks(row.get("city")))
    org_up = (row.get("org_name") or "").upper()

    # ---- the veto, evaluated first: a refusal is never awarded over a
    # positive Native signal in the organisation's own record.
    purpose = NATIVE_PURPOSE_RE.search(org_up)
    if purpose:
        return False, "", (f"VETO tribal-purpose language in the organisation's own "
                           f"name ('{purpose.group(0)}')")
    if row["_corroborators"]:
        return False, "", ("VETO corroborated by an independent evidence family: "
                           + ", ".join(row["_corroborators"]))

    # ---- P1: the matched token IS this filer's own postal place.
    # The SEAT veto gates this rung and only this rung. P1 is a geographic
    # inference and a seat is geographic evidence against it; P2 is a reading of
    # the organisation's OWN NAME, and rule 7 says the record's own words
    # outrank geography in both directions. Measured: gating P2 as well would
    # have preserved `COWLITZ VALLEY LODGE 530`, whose own name says Cowlitz
    # VALLEY, because the tribe's BIA address is in the same town.
    p1 = sorted(shared & city_t)
    if p1:
        here = ((row.get("city") or "").strip().upper(),
                (row.get("state") or "").strip().upper())
        if here in row["_seats"]:
            return False, "", (
                f"VETO {here[0]} {here[1]} is the keyed entity's own seat - a "
                f"dominant address across its federally-filed Single Audits and "
                f"gaming facilities, or the address the BIA Tribal Leaders "
                f"Directory publishes for it. A town named after a nation "
                f"because the nation is there is not a collision")
        if row["_seat_by_class"]:
            return False, "", (
                f"VETO the keyed entity is a {row['_spine_class']} and this filer "
                f"is in the village it is named for ({here[0]} {here[1]}). A "
                f"village government is located at its village; no filing is "
                f"needed to establish that, which matters because a village this "
                f"size files none")
        return True, "P1_TOKEN_IS_THE_FILERS_OWN_CITY", (
            f"the token(s) {'+'.join(p1)} that matched "
            f"{row.get('tribe_canonical_name')} are the name of this filer's own "
            f"IRS BMF city, {row.get('city')} {row.get('state')}; the word is an "
            f"address in this record, not a claim of Native identity")

    # ---- P2: the matched token is qualified as geography in the name itself.
    # The geographic-form word must not be part of the keyed entity's OWN name:
    # `TURTLE MOUNTAIN` is a nation, `SENECA COUNTY` is a county.
    nat_all = set(toks(row.get("_spine_official") or row.get("tribe_canonical_name")))
    for i, t in enumerate(name_t[:-1]):
        nxt = name_t[i + 1]
        if t in shared and nxt in GEO_FORM and nxt not in nat_all:
            return True, "P2_TOKEN_QUALIFIED_AS_GEOGRAPHY_IN_THE_NAME", (
                f"the organisation's own name reads '{t} {nxt}' - the token that "
                f"matched {row.get('tribe_canonical_name')} is qualified by a "
                f"geographic-form noun the entity's own name does not carry, so "
                f"it names a place")
    return False, "", "neither rung fires"


# ---------------------------------------------------------------------------
# sample
# ---------------------------------------------------------------------------
SAMPLE_COLS = ["stratum", "EIN", "org_name", "city", "state", "ntee_code",
               "tribe_id", "tribe_canonical_name", "spine_state", "spine_city",
               "disposition", "key_review_disposition", "keyed_state_agreement",
               "placename_risk_flag", "keyed_name_match_residue",
               "corroborating_families", "cedar_uid",
               "hand_label", "hand_label_reason"]


def cmd_sample() -> int:
    _, _, linked = load()
    sup = sorted([r for r in linked
                  if (r.get("key_review_disposition") or "").strip() == "SUPPORTED"],
                 key=lambda r: r["EIN"])
    msk = sorted([r for r in linked
                  if (r.get("key_review_disposition") or "").strip() != "SUPPORTED"],
                 key=lambda r: r["EIN"])
    print(f"  population LINKED (tribe_id AND cedar_uid both non-blank): {len(linked):,}")
    print(f"    stratum SUPPORTED  {len(sup):,}   sampling {N_SUPPORTED}")
    print(f"    stratum MASKED     {len(msk):,}   sampling {N_MASKED}")

    rng = random.Random(SEED)
    pick = rng.sample(sup, N_SUPPORTED) + rng.sample(msk, N_MASKED)

    REVIEW.mkdir(exist_ok=True)
    STRATA_AT_DRAW.write_text(json.dumps(
        {"seed": SEED, "drawn": TODAY, "linked": len(linked),
         "SUPPORTED": len(sup), "MASKED": len(msk)}, indent=1), encoding="utf-8")
    with SAMPLE_OUT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=SAMPLE_COLS)
        w.writeheader()
        for r in pick:
            w.writerow({
                "stratum": ("SUPPORTED"
                            if (r.get("key_review_disposition") or "").strip() == "SUPPORTED"
                            else "MASKED"),
                "EIN": r["EIN"], "org_name": r.get("org_name", ""),
                "city": r.get("city", ""), "state": r.get("state", ""),
                "ntee_code": r.get("ntee_code", ""),
                "tribe_id": r.get("tribe_id", ""),
                "tribe_canonical_name": r.get("tribe_canonical_name", ""),
                "spine_state": r["_spine_state"], "spine_city": r["_spine_city"],
                "disposition": r.get("disposition", ""),
                "key_review_disposition": r.get("key_review_disposition", ""),
                "keyed_state_agreement": r.get("keyed_state_agreement", ""),
                "placename_risk_flag": r.get("placename_risk_flag", ""),
                "keyed_name_match_residue": r.get("keyed_name_match_residue", ""),
                "corroborating_families": "|".join(r["_corroborators"]),
                "cedar_uid": r.get("cedar_uid", ""),
                "hand_label": "", "hand_label_reason": "",
            })
    print(f"  seed {SEED}; wrote {len(pick)} rows -> {SAMPLE_OUT.relative_to(ROOT)}")
    print("  fill hand_label with TRUE / FALSE / UNKNOWN, then run `report`.")
    return 0


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------
def _precision(labels: list) -> str:
    c = Counter(labels)
    n = len(labels)
    if not n:
        return "n=0"
    t, f, u = c.get("TRUE", 0), c.get("FALSE", 0), c.get("UNKNOWN", 0)
    return (f"n={n}  TRUE={t} ({100 * t / n:.1f}%)  FALSE={f} ({100 * f / n:.1f}%)  "
            f"UNKNOWN={u}  [strict precision {100 * t / n:.1f}%, "
            f"upper bound {100 * (t + u) / n:.1f}%]")


def _rule_of_three(n_errors: int, n: int) -> str:
    """The honest way to state a precision measured with zero observed errors.

    0/n does not mean 100%. With no errors seen, the 95% upper bound on the
    error rate is about 3/n, so the claim is a FLOOR.
    """
    if n == 0:
        return "UNMEASURED (n=0)"
    if n_errors:
        return (f"{100 * (n - n_errors) / n:.1f}% "
                f"({n - n_errors} of {n}; {n_errors} wrong)")
    return (f">= {100 * (1 - 3 / n):.1f}% at 95% confidence "
            f"(0 errors in {n}; rule of three - 0/{n} is not 100%)")


def _applied_audit() -> None:
    """Precision of the refusals THAT WERE APPLIED - a different number.

    The scored-set figure below is measured on whichever rows of the original
    population sample the predicate happens to refuse. It is a fair random
    subsample of the POPULATION but it is not a sample of the APPLIED SET, and
    a reviewer will ask for that separately - correctly, because the one wrong
    refusal an independent hand-check found (`KASAAN HAIDA HERITAGE FOUNDATION`)
    sat outside the scored subset.
    """
    strata = REVIEW / "np_placename_precision_applied_strata_2026-09-02.json"
    if not (AUDIT_LABELS.exists() and strata.exists()):
        print("\n  [applied-set precision UNMEASURED - run `audit`, label it, "
              "and re-run `report`]")
        return
    at = json.loads(strata.read_text(encoding="utf-8"))
    _, lab = read_csv(AUDIT_LABELS)
    lab = [r for r in lab if (r.get("hand_label") or "").strip()]
    c = Counter(r["hand_label"].strip() for r in lab)
    scored = c["REFUSAL_CORRECT"] + c["REFUSAL_WRONG"]
    print(f"\n  === APPLIED-SET PRECISION, its own random sample "
          f"(seed {at['seed']}, {len(lab)} of {at['applied']:,} applied) ===")
    print(f"    REFUSAL_CORRECT {c['REFUSAL_CORRECT']}   "
          f"REFUSAL_WRONG {c['REFUSAL_WRONG']}   UNKNOWN {c['UNKNOWN']}")
    print(f"    precision of the APPLIED refusals: "
          f"{_rule_of_three(c['REFUSAL_WRONG'], scored)}")
    print("    Read this next to the scored-set figure, not instead of it, and "
          "note the shared-mind caveat in docs/NP_PLACENAME_PRECISION_1155.md "
          "section 11: the same judgement drew both the rule and the labels.")


def cmd_report() -> int:
    cols, rows, linked = load()
    n_rows = len(rows)
    print(f"  np_orgs.csv rows {n_rows:,}   LINKED {len(linked):,} "
          f"({100 * len(linked) / n_rows:.2f}%)")

    fires, rung_c = [], Counter()
    for r in linked:
        ok, rung, basis = classify(r)
        r["_fires"], r["_rung"], r["_basis"] = ok, rung, basis
        if ok:
            fires.append(r)
            rung_c[rung] += 1
    print(f"\n  1155 predicate fires on {len(fires):,} of {len(linked):,} live keys "
          f"({100 * len(fires) / len(linked):.1f}%)")
    for k, v in rung_c.most_common():
        print(f"      {v:>5,}  {k}")
    print("    by the key_review_disposition they carry today:")
    for k, v in Counter((r.get("key_review_disposition") or "(blank)")
                        for r in fires).most_common():
        print(f"      {v:>5,}  {k}")
    print("    by the disposition they carry today:")
    for k, v in Counter((r.get("disposition") or "(blank)") for r in fires).most_common():
        print(f"      {v:>5,}  {k}")
    print("    top keyed entities:")
    for k, v in Counter((r.get("tribe_canonical_name") or "") for r in fires).most_common(12):
        print(f"      {v:>5,}  {k}")

    masked_now = sum(1 for r in linked
                     if (r.get("key_review_disposition") or "") not in ("SUPPORTED", ""))
    still_sup = sum(1 for r in fires
                    if (r.get("key_review_disposition") or "") == "SUPPORTED")
    print(f"\n  AS THE TABLE STANDS RIGHT NOW: {masked_now:,} of {len(linked):,} live "
          f"keys are masked at publication; {len(linked) - masked_now:,} still ship.")
    print(f"  of the {len(fires):,} rows this predicate refuses, {still_sup:,} still "
          f"read SUPPORTED - run `apply` if that is not zero.")

    if not LABELS_IN.exists():
        print(f"\n  [no hand labels at {LABELS_IN.relative_to(ROOT)} - "
              f"precision UNMEASURED, not clean]")
        return 0

    _, lab = read_csv(LABELS_IN)
    lab = [r for r in lab if (r.get("hand_label") or "").strip()]
    by_ein = {r["EIN"]: r for r in lab}
    print(f"\n  === MEASURED PRECISION, hand-labelled seeded sample "
          f"(seed {SEED}, n={len(lab)}) ===")
    for st in ("SUPPORTED", "MASKED"):
        s = [r["hand_label"].strip() for r in lab if r["stratum"] == st]
        print(f"    stratum {st:<10} {_precision(s)}")
    allv = [r["hand_label"].strip() for r in lab]
    print(f"    unweighted        {_precision(allv)}")

    # Weighted against the DRAW-TIME strata, never today's. `apply` moves rows
    # between strata, and re-weighting against the post-apply sizes silently
    # answers a different question.
    if not STRATA_AT_DRAW.exists():
        print("    [no draw-time strata recorded - the weighted figure is "
              "UNMEASURED, not clean. Re-run `sample`.]")
    else:
        at = json.loads(STRATA_AT_DRAW.read_text(encoding="utf-8"))
        n_sup, n_msk, n_all = at["SUPPORTED"], at["MASKED"], at["linked"]
        sup_l = [r["hand_label"].strip() for r in lab if r["stratum"] == "SUPPORTED"]
        msk_l = [r["hand_label"].strip() for r in lab if r["stratum"] == "MASKED"]
        if sup_l and msk_l:
            print(f"    weighted against the strata AS DRAWN {at['drawn']} "
                  f"(SUPPORTED {n_sup:,}, MASKED {n_msk:,}, total {n_all:,}):")
            for name in ("TRUE", "FALSE", "UNKNOWN"):
                p = (n_sup * sup_l.count(name) / len(sup_l)
                     + n_msk * msk_l.count(name) / len(msk_l)) / n_all
                print(f"      {name:<8} {100 * p:.1f}%")

    _applied_audit()

    # the predicate scored against the hand labels
    tp = fp = fn = tn = 0
    for r in linked:
        h = by_ein.get(r["EIN"])
        if not h:
            continue
        lbl = h["hand_label"].strip()
        if lbl == "UNKNOWN":
            continue
        if r["_fires"] and lbl == "FALSE":
            tp += 1
        elif r["_fires"] and lbl == "TRUE":
            fp += 1
        elif not r["_fires"] and lbl == "FALSE":
            fn += 1
        else:
            tn += 1
    if tp + fp + fn + tn:
        print(f"\n  === THE PREDICATE, SCORED AGAINST THOSE LABELS "
              f"(UNKNOWN excluded, n={tp + fp + fn + tn}) ===")
        print(f"    caught a hand-FALSE      {tp}")
        print(f"    hit a hand-TRUE (COST)   {fp}")
        print(f"    missed a hand-FALSE      {fn}")
        print(f"    correctly left a TRUE    {tn}")
        if tp + fp:
            print(f"    precision of the refusal  {_rule_of_three(fp, tp + fp)}")
        if tp + fn:
            print(f"    recall over hand-FALSE    {100 * tp / (tp + fn):.1f}%")
    return 0


# ---------------------------------------------------------------------------
# apply / verify
# ---------------------------------------------------------------------------
NEW_COLS = ["placename_refusal_rung", "placename_refusal_basis",
            "placename_refusal_date"]

# `key_review_disposition` values this pass is allowed to overwrite. A verdict
# another pass already recorded is EVIDENCE and is left standing - the refusal
# is still written, in its own columns. HELD_STATE_DISAGREES already MASKs in
# `cedar_publication.py`, so nothing is published either way.
OVERWRITABLE = {"SUPPORTED", ""}


def cmd_apply() -> int:
    cols, rows, linked = load()
    fires, fire_ein = [], set()
    for r in linked:
        ok, rung, basis = classify(r)
        if ok:
            r["_rung"], r["_basis"] = rung, basis
            fires.append(r)
            fire_ein.add(r["EIN"])
    todo = [r for r in fires if not (r.get("placename_refusal_rung") or "").strip()]
    # Reversible in both directions. When the predicate is tightened - a seat
    # source widened, a veto added - a row it used to refuse must LOSE the
    # refusal, or the table keeps a verdict no rule now supports. Two rows went
    # this way when the BIA directory and the village-class rule were added.
    stale = [r for r in rows
             if (r.get("placename_refusal_rung") or "").strip()
             and r["EIN"] not in fire_ein]
    if not todo and not stale:
        print("  nothing to do - the table already matches the predicate")
        return 0

    shutil.copy2(NP, NP.with_name(NP.name + f".bak_{TODAY}_pre_1155_np_placename_precision"))
    for c in NEW_COLS:
        if c not in cols:
            cols.append(c)

    n_demoted = 0
    for r in todo:
        r["placename_refusal_rung"] = r["_rung"]
        r["placename_refusal_basis"] = (
            f"{DISPOSITION_VALUE} [{r['_rung']}]: {r['_basis']}. The key is "
            f"WITHDRAWN, not the row: nothing deleted, cedar_uid untouched, and "
            f"this says only that the organisation is not THAT entity - it is NOT "
            f"a finding that the organisation is not Native. code/1155, "
            f"docs/ENTITY_MATCH_RULES.md. {TODAY}")
        r["placename_refusal_date"] = TODAY
        prior = (r.get("key_review_disposition") or "").strip()
        if prior in OVERWRITABLE:
            r["key_review_disposition"] = DISPOSITION_VALUE
            r["key_review_basis"] = (
                f"{DISPOSITION_VALUE}: {r['_basis']} [{r['_rung']}]. Prior value "
                f"{prior or '(blank)'}; see placename_refusal_basis. {TODAY}")
            n_demoted += 1

    n_reverted = 0
    for r in stale:
        r["placename_refusal_rung"] = ""
        r["placename_refusal_basis"] = ""
        r["placename_refusal_date"] = ""
        if (r.get("key_review_disposition") or "").strip() == DISPOSITION_VALUE:
            r["key_review_disposition"] = "SUPPORTED"
            r["key_review_basis"] = (
                f"Refusal WITHDRAWN {TODAY} by code/1155: the widened seat evidence "
                f"shows this filer is at the keyed entity's own seat, so the "
                f"place-name refusal no longer holds. Restored to SUPPORTED.")
            n_reverted += 1

    for r in rows:
        for k in list(r):
            if k.startswith("_"):
                del r[k]
        for c in NEW_COLS:
            r.setdefault(c, "")

    with NP.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  refusal recorded on {len(todo):,} live keys; of those {n_demoted:,} "
          f"had a publishable disposition and were demoted to {DISPOSITION_VALUE}")
    print(f"  {len(todo) - n_demoted:,} already carried another pass's verdict "
          f"(left standing; already masked at publication)")
    print(f"  refusal WITHDRAWN from {len(stale):,} row(s) the predicate no longer "
          f"refuses; {n_reverted:,} restored to SUPPORTED")
    print(f"  np_orgs.csv rewritten: {len(rows):,} rows, {len(cols)} columns; "
          f"backup .bak_{TODAY}_pre_1155_np_placename_precision")
    return 0


def cmd_verify() -> int:
    """FAILS when the work did not land. Not a conservation check."""
    cols, rows, linked = load()
    bad = []

    should = [r for r in linked if classify(r)[0]]
    got = [r for r in rows if (r.get("placename_refusal_rung") or "").strip()]
    demoted = [r for r in rows
               if (r.get("key_review_disposition") or "").strip() == DISPOSITION_VALUE]
    print(f"  predicate fires on {len(should):,} live keys; rows carrying a refusal "
          f"rung: {len(got):,}; rows demoted to {DISPOSITION_VALUE}: {len(demoted):,}")

    # I1 - the intended delta, on the intended column, with a floor. The failure
    # this exists to catch is a no-op that conserves rows and dollars perfectly.
    RUNG_FLOOR, DEMOTE_FLOOR = 400, 200
    if len(got) < RUNG_FLOOR:
        bad.append(f"I1a only {len(got):,} rows carry a refusal rung; floor "
                   f"{RUNG_FLOOR}. The write did not land.")
    if len(demoted) < DEMOTE_FLOOR:
        bad.append(f"I1b only {len(demoted):,} rows read {DISPOSITION_VALUE}; floor "
                   f"{DEMOTE_FLOOR}. Recording a rung without withdrawing the claim "
                   f"is not the work.")
    # I2 - every firing row carries the refusal
    miss = [r["EIN"] for r in should if not (r.get("placename_refusal_rung") or "").strip()]
    if miss:
        bad.append(f"I2 {len(miss)} rows fire the predicate and carry no refusal, "
                   f"e.g. {miss[:5]}")
    # I3 - every refused row states its rung AND its basis
    for r in got:
        if DISPOSITION_VALUE not in (r.get("placename_refusal_basis") or ""):
            bad.append(f"I3 EIN {r.get('EIN')} carries a rung with no basis")
            break
    # I4 - flag never delete, never mint, never erase an identifier
    if len(rows) != 12764:
        bad.append(f"I4a np_orgs.csv is {len(rows):,} rows, expected 12,764 - "
                   f"a row was added or dropped")
    blank_uid = sum(1 for r in got if not (r.get("cedar_uid") or "").strip())
    if blank_uid:
        bad.append(f"I4b {blank_uid} refused rows have no cedar_uid; the key is "
                   f"withdrawn by the disposition, the identifier is never erased")
    # I5 - one-way. This pass may only withdraw.
    if any((r.get("placename_refusal_rung") or "").strip() and
           (r.get("key_review_disposition") or "").strip() == "SUPPORTED" for r in rows):
        bad.append("I5a a row carries a refusal rung and still reads SUPPORTED")
    if any((r.get("key_review_disposition") or "").strip() == DISPOSITION_VALUE and
           not (r.get("placename_refusal_rung") or "").strip() for r in rows):
        bad.append("I5b a row reads the refusal disposition with no rung behind it")
    # I7 - no refusal outlives the rule behind it. When the predicate is
    # tightened, a row it no longer refuses must not keep the verdict.
    fire = {r["EIN"] for r in should}
    orphan = [r["EIN"] for r in rows
              if (r.get("placename_refusal_rung") or "").strip()
              and r["EIN"] not in fire]
    if orphan:
        bad.append(f"I7 {len(orphan)} row(s) carry a refusal the predicate no longer "
                   f"makes, e.g. {orphan[:5]} - re-run `apply`")
    # I6 - THE CROSS-LANE DEPENDENCY, asserted rather than assumed.
    # `cedar_publication.py` is deny-by-default: a `key_review_disposition`
    # value its vocabulary has never seen WITHHOLDS the whole row. If this entry
    # is ever dropped, 293 real IRS filings vanish from the export instead of
    # their keys being masked, and nothing else in the repo would say so.
    pub = (ROOT / "code" / "cedar_publication.py").read_text(encoding="utf-8")
    if f'"{DISPOSITION_VALUE}": MASK' not in pub:
        bad.append(f"I6 cedar_publication.BLOCKED_STATES['key_review_disposition'] "
                   f"does not enumerate {DISPOSITION_VALUE} as MASK. Deny-by-default "
                   f"would WITHHOLD {len(demoted):,} real filings. Restore the entry.")

    for b in bad:
        print("  FAIL " + b)
    if not bad:
        print("  PASS I1a I1b I2 I3 I4a I4b I5a I5b I6 I7")
    return 1 if bad else 0


# ---------------------------------------------------------------------------
# audit - the APPLIED-SET precision, which is a different number from the
# scored-set precision and a reviewer will ask for both.
#
# The scored figure comes from the rows of the ORIGINAL 210-row sample that the
# predicate happens to refuse: a random subsample of the population, but only
# 80 rows, and it says nothing about the refusals that fall outside it. The
# coordinator's hand-check found `KASAAN HAIDA HERITAGE FOUNDATION` exactly
# there - outside the scored subset. So the applied set gets its own random
# sample, drawn from the rows whose claim this pass actually WITHDREW.
# ---------------------------------------------------------------------------
AUDIT_SEED = 20260902_2
N_AUDIT = 60
AUDIT_OUT = REVIEW / "np_placename_precision_applied_audit_2026-09-02.csv"
AUDIT_LABELS = REVIEW / "np_placename_precision_applied_audit_labels_2026-09-02.csv"
AUDIT_COLS = ["EIN", "org_name", "city", "state", "ntee_code", "tribe_id",
              "tribe_canonical_name", "spine_state", "spine_entity_class",
              "refusal_rung", "disposition", "hand_label", "hand_label_reason"]


def cmd_audit() -> int:
    _, rows, _ = load()
    pool = sorted([r for r in rows
                   if (r.get("key_review_disposition") or "").strip() == DISPOSITION_VALUE],
                  key=lambda r: r["EIN"])
    print(f"  applied set (claims this pass WITHDREW): {len(pool):,}")
    if not pool:
        print("  nothing applied - run `apply` first")
        return 1
    n = min(N_AUDIT, len(pool))
    pick = random.Random(AUDIT_SEED).sample(pool, n)
    REVIEW.mkdir(exist_ok=True)
    (REVIEW / "np_placename_precision_applied_strata_2026-09-02.json").write_text(
        json.dumps({"seed": AUDIT_SEED, "drawn": TODAY, "applied": len(pool),
                    "sampled": n}, indent=1), encoding="utf-8")
    with AUDIT_OUT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=AUDIT_COLS)
        w.writeheader()
        for r in pick:
            w.writerow({
                "EIN": r["EIN"], "org_name": r.get("org_name", ""),
                "city": r.get("city", ""), "state": r.get("state", ""),
                "ntee_code": r.get("ntee_code", ""),
                "tribe_id": r.get("tribe_id", ""),
                "tribe_canonical_name": r.get("tribe_canonical_name", ""),
                "spine_state": r.get("_spine_state", ""),
                "spine_entity_class": r.get("_spine_class", ""),
                "refusal_rung": r.get("placename_refusal_rung", ""),
                "disposition": r.get("disposition", ""),
                "hand_label": "", "hand_label_reason": "",
            })
    print(f"  seed {AUDIT_SEED}; wrote {n} rows -> {AUDIT_OUT.relative_to(ROOT)}")
    print("  label each REFUSAL_CORRECT / REFUSAL_WRONG / UNKNOWN, then `report`.")
    return 0


FRAGMENT = ROOT / "data" / "clean" / "codebook" / "06_nonprofit.csv"

CODEBOOK_ROWS = [
    ("placename_refusal_rung", "text", "category",
     "Which structural test found the keyed entity's name to be functioning as "
     "a PLACE in this record, blank where neither fired. Two values. "
     "`P1_TOKEN_IS_THE_FILERS_OWN_CITY` - the token that matched the nation is "
     "the name of the filer's own IRS BMF city (COQUILLE CHESS CLUB in "
     "Coquille OR). `P2_TOKEN_QUALIFIED_AS_GEOGRAPHY_IN_THE_NAME` - the token "
     "is immediately followed by a geographic-form noun the entity's own "
     "official name does not carry, so SENECA COUNTY is a county while TURTLE "
     "MOUNTAIN stays a nation. Refused where the organisation's own name "
     "carries Native-purpose language, where an independent evidence family "
     "names the EIN, or where the town is the nation's own seat. **This is a "
     "statement about which ENTITY, never about Native status** - 21 of the "
     "161 hand-classified wrong keys are genuine Native organisations pointed "
     "at the wrong entity. Written by `code/1155`; measured precision of the "
     "refusal 100% (0 wrong in 79) on a hand-labelled seeded sample, so at "
     "least 96.2% at 95% confidence."),
    ("placename_refusal_basis", "text", "provenance",
     "The token, the evidence and the rung behind `placename_refusal_rung`, on "
     "the row, plus the standing statement that the key is withdrawn and the "
     "row is not. Never blank where the rung is set."),
    ("placename_refusal_date", "date", "date",
     "When `code/1155` recorded the refusal. Blank where no refusal was made."),
]


def cmd_codebook() -> int:
    """Upsert this pass's three columns into the nonprofit codebook fragment.

    Read-modify-write on a fragment other passes also write, so it UPSERTS by
    variable name and refuses to shrink. `cedar_codebook.write_fragment` writes
    a whole fragment; handing it three rows would delete the other 112.
    """
    _, rows, _ = load()
    n = len(rows)
    frag = list(csv.DictReader(FRAGMENT.open(encoding="utf-8-sig", errors="replace")))
    before = len(frag)
    cols = list(frag[0].keys())
    by_var = {r["variable"]: r for r in frag}
    for var, typ, units, desc in CODEBOOK_ROWS:
        filled = sum(1 for r in rows if (r.get(var) or "").strip())
        rec = {"dataset": "06_nonprofit", "variable": var, "type": typ,
               "units": units, "pct_filled": f"{100 * filled / n:.1f}",
               "n_rows": str(n), "published": "1", "access_tier": "subscriber",
               "description": desc, "generated": TODAY}
        if var in by_var:
            by_var[var].update({k: v for k, v in rec.items() if k in cols})
        else:
            frag.append({k: rec.get(k, "") for k in cols})
        print(f"  {var:<26} {filled:>6,} of {n:,} filled ({100 * filled / n:.1f}%)")
    if len(frag) < before:
        print("  REFUSING: the fragment would shrink")
        return 1
    shutil.copy2(FRAGMENT, FRAGMENT.with_name(
        FRAGMENT.name + f".bak_{TODAY}_pre_1155_np_placename_precision"))
    with FRAGMENT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(frag)
    print(f"  06_nonprofit fragment {before} -> {len(frag)} rows "
          f"(run `py -3 code/cedar_codebook.py build` to fold into the master)")
    return 0


def _inject_orphan(text: str) -> str:
    """Give a refusal rung to a row the predicate leaves alone, so I7 must fire."""
    import io
    nl = chr(10)
    lines = text.split(nl)
    hdr = lines[0].split(",")
    i_rung = hdr.index("placename_refusal_rung")
    i_basis = hdr.index("placename_refusal_basis")
    i_uid = hdr.index("cedar_uid")
    for n, ln in enumerate(lines[1:], start=1):
        if not ln.strip():
            continue
        cells = next(csv.reader([ln]))
        if (len(cells) == len(hdr) and not cells[i_rung].strip()
                and cells[i_uid].strip()):
            cells[i_rung] = "P1_TOKEN_IS_THE_FILERS_OWN_CITY"
            cells[i_basis] = DISPOSITION_VALUE + ": injected by selftest"
            buf = io.StringIO()
            csv.writer(buf, lineterminator="").writerow(cells)
            lines[n] = buf.getvalue()
            break
    return nl.join(lines)


def cmd_selftest() -> int:
    """Inject each violation into a COPY, assert verify goes red, restore, assert green.

    A check that has never failed on purpose is not known to work
    (`docs/AGENT_FIELD_GUIDE.md` rule 1).
    """
    import subprocess
    me = [sys.executable, str(Path(__file__).resolve()), "verify"]

    def run():
        p = subprocess.run(me, capture_output=True, text=True, cwd=str(ROOT))
        return p.returncode, p.stdout + p.stderr

    rc, out = run()
    if rc != 0:
        print("  selftest cannot start: verify is already RED\n" + out)
        return 1
    print("  baseline verify GREEN")

    np_bak = NP.read_bytes()
    pub_path = ROOT / "code" / "cedar_publication.py"
    pub_bak = pub_path.read_bytes()
    fails = []
    try:
        for name, mutate in [
            ("I1b/I5b strip every refusal disposition",
             lambda t: t.replace(DISPOSITION_VALUE + ",", "SUPPORTED,")),
            ("I2/I1a strip every refusal rung",
             lambda t: re.sub(r"P1_TOKEN_IS_THE_FILERS_OWN_CITY|"
                              r"P2_TOKEN_QUALIFIED_AS_GEOGRAPHY_IN_THE_NAME", "", t)),
            ("I7 put a rung on a row the predicate does not refuse", _inject_orphan),
        ]:
            NP.write_text(mutate(np_bak.decode("utf-8", "replace")),
                          encoding="utf-8", newline="")
            rc, out = run()
            named = any(k in out for k in ("I1a", "I1b", "I2", "I5b", "I7"))
            print(f"    {'RED ' if rc else 'GREEN'} {'named' if named else 'UNNAMED'}"
                  f"  <- {name}")
            if rc == 0 or not named:
                fails.append(name)
            NP.write_bytes(np_bak)

        pub_path.write_text(
            pub_bak.decode("utf-8").replace(f'"{DISPOSITION_VALUE}": MASK,', ""),
            encoding="utf-8", newline="")
        rc, out = run()
        print(f"    {'RED ' if rc else 'GREEN'} {'named' if 'I6' in out else 'UNNAMED'}"
              f"  <- I6 remove the publication vocabulary entry")
        if rc == 0 or "I6" not in out:
            fails.append("I6")
        pub_path.write_bytes(pub_bak)
    finally:
        NP.write_bytes(np_bak)
        pub_path.write_bytes(pub_bak)

    rc, out = run()
    print(f"  restored: verify {'GREEN' if rc == 0 else 'RED'}")
    if rc != 0:
        fails.append("restore")
    if fails:
        print("  SELFTEST FAILED: " + "; ".join(fails))
        return 1
    print("  SELFTEST PASSED: every injected violation went RED and named itself")
    return 0


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    return {"sample": cmd_sample, "report": cmd_report, "apply": cmd_apply,
            "verify": cmd_verify, "codebook": cmd_codebook, "audit": cmd_audit,
            "selftest": cmd_selftest}[cmd]()


if __name__ == "__main__":
    sys.exit(main())
