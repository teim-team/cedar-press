#!/usr/bin/env python3
# lint-ok: class6 - EVERY PHASE HERE IS AN IN-PLACE ENRICHER BY DESIGN, and
# `all` runs them in the only correct order. Orderings are declared in
# cedar_pipeline.KNOWN_ORDERINGS against 24, 152 and 01. Any rebuild of a
# touched table drops what this wrote; re-run `503_identity.py all` after.
"""
Cedar Press - 503: THE IDENTITY LAYER. One script, four phases.

    py -3 code/503_identity.py all --apply     # reconcile -> mint -> stamp
    py -3 code/503_identity.py reconcile       # legacy CICD ids -> Cedar handles
    py -3 code/503_identity.py mint            # permanent cedar_uid register
    py -3 code/503_identity.py stamp           # materialise uid onto 125 tables
    py -3 code/503_identity.py verify          # coverage + validity, read-only

WHY ONE SCRIPT
--------------
These were three files (503/504/505) written the same afternoon, and that was
the script-proliferation this project already guards against with
`code_duplicate_numbers`. They are not three jobs: they are one job - "make
every row say which Native entity it is about" - in dependency order. Splitting
them meant three docstrings, three arg parsers, and three chances to run them
out of order. `all` is now the only ordering anyone needs to remember.

    reconcile  a legacy integer or a filed NAME  -> a Cedar handle (TRBF-...)
    mint       a Cedar handle                    -> a permanent cedar_uid
    stamp      every dataset row                 -> its cedar_uid, in the file

The originals are in graveyard/2026-08-29_identity_consolidation/ with their
build history. Nothing here changed except the entry point.

PHASE DOCS follow inline, each keeping the reasoning that earned it.
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import re
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
TODAY = date.today().isoformat()
csv.field_size_limit(10_000_000)


# ===================== PHASE 1: RECONCILE =====================


import csv
import io
import os
import re
import sys
from datetime import date
from pathlib import Path

SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
ALIASES = ROOT / "data" / "clean" / "entity_aliases.csv"
XWALK = ROOT / "data" / "spine" / "legacy" / "assistance_tribe_id_crosswalk.csv"
TABLE = ROOT / "data" / "clean" / "federal_funding_transactions.csv"
BASIS_TAG = "503_reconcile_assistance_to_cedar_ids"

GOV = {"Federally recognized tribe",
       "Federally recognized Alaska Native Village",
       "State-recognized tribe",
       "Federal-level self-governance consortium",
       # MCT constituent bands (Leech Lake, Mille Lacs, Bois Forte, Grand
       # Portage), Pleasant Point and their kin are CONSTITUENCY-class in the
       # spine. They are governments that receive assistance in their own name;
       # excluding them left $1.5B+ of obvious matches "unmatched".
       "Federal-level constituency entity",
       "State-level constituency entity"}

# Generic vocabulary: words that name WHAT a government is, not WHICH one.
# State and place words are deliberately absent - OKLAHOMA is what separates
# the Seminole Nation of Oklahoma from the Seminole Tribe of Florida.
GENERIC = {"THE", "OF", "AND", "A", "AN", "IN", "AT", "DU", "DE", "LA",
           "NATION", "NATIONS", "TRIBE", "TRIBES", "TRIBAL", "BAND", "BANDS",
           "INDIAN", "INDIANS", "NATIVE", "VILLAGE", "COMMUNITY", "COMMUNITIES",
           "RESERVATION", "RANCHERIA", "PUEBLO", "COLONY", "TOWN",
           "GOVERNMENT", "COUNCIL", "COMMITTEE", "BUSINESS", "EXECUTIVE",
           "INC", "INCORPORATED", "ORGANIZATION"}

CANON_FIX = {"STE": "SAINTE", "ST": "SAINT", "MT": "MOUNT", "FT": "FORT"}


def clean(s: str) -> str:
    s = (s or "").upper().replace("&", " AND ")
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = re.sub(r"MC ([A-Z])", r"MC", s)      # FT MC DOWELL -> MCDOWELL
    return " ".join(CANON_FIX.get(w, w) for w in s.split())


def light(s: str) -> str:
    words = [w for w in clean(s).split() if w != "THE"]
    # trailing government-suffix noise
    while words and words[-1] in ("GOVERNMENT",):
        words.pop()
    return " ".join(words)


def tokens(s: str) -> frozenset:
    return frozenset(w for w in clean(s).split() if w not in GENERIC)


# =====================================================================
# THE LOOSE-PATH REFUSAL GUARDS
#
# WHY THEY EXIST, MEASURED 2026-09-01 (workstream I, code/522_mine_rulings.py
# `guards`). `resolve()`'s last resort is a DISTINCTIVE-TOKEN SUBSET test -
# a spine entity wins if every one of its distinctive tokens appears in the
# filed name. For the ~400 spine entities whose distinctive set is a SINGLE
# token that is also an American place name (Wichita, Klamath, Taos, Laguna,
# Osage, Onondaga, Tuscarora, Cowlitz, Umatilla, Robinson, Peoria), that test
# is satisfied by any organisation in the county. Swept over every name a
# human has ever REFUSED in this project - 5,197 distinct subjects from
# `cedar_ruling_ledger_consolidated.csv` (verdict NEGATIVE) and
# `nonprofit_exclusion_rulings.csv` - `resolve()` returned a tribe for
# **2,458 of them, 47%**:
#
#     ONONDAGA GOLF AND COUNTRY CLUB      -> TRBF-ONNDGA-00
#     TUSCARORA SOCCER CLUB               -> TRBF-TSCARA-00
#     COWLITZ COUNTY AUXILIARY COMMS      -> TRBF-COWLTZ-00
#     ST. AUGUSTINE DISTILLERY            -> TRBF-AGSTNE-00
#     OTTEN JOHNSON ROBINSON NEFF         -> TRBF-ROBNSN-00
#
# These are not hypotheticals: every one is a name a human already refused.
#
# THE TWO GUARDS, AND WHY THEY ARE RULES RATHER THAN BLOCKLISTS
# -------------------------------------------------------------
# G1 ADMIN-GEOGRAPHY, and it is CANONICAL-AWARE. A US administrative or
#    settlement-geography word in the filed name means the tribal token is
#    naming a PLACE - unless the entity's OWN canonical name carries the same
#    word, which is what keeps the FOREST COUNTY POTAWATOMI COMMUNITY, COLD
#    SPRINGS RANCHERIA and the CONFEDERATED TRIBES OF WARM SPRINGS resolving.
#    This is the "Wichita Falls rule" in NATIVE_ENTITY_NUANCES.md, coded.
#    TOWNSHIP, VILLAGE and CITY are DELIBERATELY ABSENT: Kayenta Township is
#    the Navajo Nation's own municipal government and Indian Township is a
#    Passamaquoddy reservation government - both settled by owner rulings in
#    review/ruling_vs_table_contradictions_2026-08-26.csv.
#
# G2 CIVIC FORM. A congregation, a sports club, a service club, a PTO, a
#    sheriff's association or a cemetery association is a civic body that
#    borrowed the county's name. Every token below was selected on a measured
#    criterion, not taste: it must appear in ZERO of the 1,952 names a human
#    ruled TO an entity and ZERO of the 1,536 spine canonical names.
#    MUSEUM and LIONS were in the first draft and were REMOVED by a HELD-OUT
#    control the fitting never saw - the owner's own 2021 BGOV crosswalk,
#    which contains MAKAH MUSEUM, SOUTHERN UTE CULTURAL CENTER & MUSEUM and
#    the NATIVE VILLAGE OF PORT LIONS. HOSPITAL, FOUNDATION, ASSOCIATION,
#    SCHOOL, CENTER, PARK and MEMORIAL were considered and REJECTED: each
#    occurs on real spine entities or real owner-ruled Native organisations.
#
# BOTH GUARDS FIRE ONLY ON THE LOOSE TOKEN-SUBSET PATH. A declared
# equivalence, an exact canonical name and an exact alias all resolve EARLIER
# in `resolve()` and are untouched - so a spine entity that really is called
# "... Cemetery Association" still resolves by its own name.
#
# BLAST RADIUS, measured before and after on the real corpus:
#   refused-name false resolutions   2,458 -> 1,046   (-1,412, -57%)
#   owner-ruled entity names resolved 1,117 -> 1,117  (unchanged)
#   spine canonical names resolved    1,532 -> 1,532  (unchanged)
#   503 reconcile legacy ids          359/361 -> 359/361 (unchanged)
# Re-measure any time with: py -3 code/522_mine_rulings.py guards
# =====================================================================

# G1. Administrative and settlement geography. Canonical-aware: see above.
ADMIN_GEOGRAPHY = {
    "COUNTY", "COUNTIES", "PARISH", "BOROUGH", "MUNICIPALITY", "MUNICIPAL",
    "METROPOLITAN", "FALLS", "HEIGHTS", "JUNCTION", "BEACH", "DOWNTOWN",
    "ESTATES", "BLUFF", "SUBDIVISION", "UNINCORPORATED",
}

# G2. Civic organisational forms. Zero occurrences in 1,952 owner-ruled
# entity names and zero in 1,536 spine canonical names, measured 2026-09-01.
CIVIC_FORM = {
    # congregations and religious bodies
    "BAPTIST", "CHRISTIAN", "CHRIST", "MINISTRIES", "MINISTRY", "MINISTERIAL",
    "BIBLE", "CATHOLIC", "METHODIST", "LUTHERAN", "PRESBYTERIAN",
    "EVANGELICAL", "GOSPEL", "CALVARY", "CHAPEL", "FOURSQUARE", "TEMPLE",
    "SYNAGOGUE", "ISLAMIC", "BUDDHIST", "BAHAIS", "CONGREGATION", "CHURCH",
    "CHURCHES",
    # sport and recreation
    "GOLF", "SOCCER", "BASEBALL", "SOFTBALL", "BASKETBALL", "FOOTBALL",
    "HOCKEY", "LACROSSE", "VOLLEYBALL", "TENNIS", "WRESTLING", "CHEER",
    "ATHLETIC", "ATHLETICS", "SPORTS", "AMATEUR", "YACHT", "ROWING",
    "CYCLING", "SKI", "KENNEL", "BOOSTERS", "BOOSTER",
    # service clubs and fraternal orders  (LIONS excluded: Port Lions, AK)
    "ROTARY", "KIWANIS", "ELKS", "LEGION", "SCOUTS", "SCOUTING", "YMCA",
    "YWCA", "AUXILIARY", "POSSE", "MASONIC", "CLUB", "CLUBS",
    # school-adjacent volunteer bodies  (SCHOOL excluded: 160 BIE spine rows)
    "PTO", "PTA", "TEACHER", "TEACHERS", "MONTESSORI", "ALUMNI", "ALUMNAE",
    # arts, heritage and letters  (MUSEUM excluded: Makah Museum)
    "SYMPHONY", "ORCHESTRA", "CHORALE", "OPERA", "THEATRE", "THEATER",
    "GUILD", "LIBRARY", "HISTORICAL", "GENEALOGICAL", "AUDUBON", "SOCIETY",
    # public safety, municipal services, chambers
    "SHERIFF", "SHERIFFS", "FIREFIGHTERS", "FIREFIGHTER", "POLICE", "DEPUTY",
    "CEMETERY", "HOSPICE", "HUMANE", "CHAMBER",
}


# G3. Utility and civic-event forms. A federally recognized tribe is
# essentially never the filer of one of these. Exempted whenever the filed
# name carries a Native term, so a tribal utility keeps resolving.
# HEALTHCARE / HOSPITAL / MEDICAL / CLINIC / FIRE are deliberately ABSENT:
# tribes run all of those.
CIVIC_UTILITY = {
    "ELECTRIC", "ELECTRICAL", "COOPERATIVE", "COOP", "HOSE",
    "MOTORSPORTS", "SNOWMOBILE", "FESTIVAL", "FESTIVALS", "FIREWORKS",
    "FAIRGROUNDS", "AUDUBON", "HUMANE", "SPCA", "REALTORS", "QUILT",
    "GENEALOGICAL", "CEMETERY", "LIBRARY", "LIBRARIES",
}

# Terms by which a filed name claims Native status for itself. Presence of any
# one exempts the CIVIC_UTILITY refusal - "Navajo Tribal Utility Authority"
# must keep resolving.
NATIVE_TERM = {
    "TRIBE", "TRIBES", "TRIBAL", "NATION", "NATIONS", "BAND", "BANDS",
    "PUEBLO", "PUEBLOS", "RANCHERIA", "INDIAN", "INDIANS", "NATIVE",
    "NATIVES", "NSN", "ANISHINAABE",
}


def loose_path_refusal(filed: str, canonical: str) -> str:
    """Why the loose token-subset path must NOT claim `filed`, or ''.

    `canonical` is the spine name that would have won. The admin-geography
    test is canonical-aware so that an entity whose own name carries the word
    (Forest County Potawatomi) is never refused by it.
    """
    ft = set(clean(filed).split())
    hit = ft & ADMIN_GEOGRAPHY
    if hit and not (hit & set(clean(canonical).split())):
        return ("REFUSED_ADMIN_GEOGRAPHY:" + ",".join(sorted(hit))
                + " - a US place name, not the nation it is named for")
    hit = ft & CIVIC_FORM
    if hit:
        return ("REFUSED_CIVIC_FORM:" + ",".join(sorted(hit))
                + " - a civic organisation carrying a place name")
    # G3. UTILITY AND CIVIC-EVENT FORMS, exempted by any Native term.
    #
    # 06_nonprofit.md has named Umatilla Electric Co-op ($592M) as a tier-A
    # leak since August. Measured 2026-09-01: it STILL resolves, live, via
    # this path - "gov-class distinctive-token match on 'Umatilla Tribe'".
    # So did SENECA HOSE CO NO 1 (a volunteer fire company), TAOS VOLUNTEER
    # FIRE DEPARTMENT and ONEIDA HEALTHCARE SYSTEMS (a 101-bed hospital).
    # The doc recorded the symptom; nothing had measured that the mechanism
    # was still firing.
    #
    # Two rules were tested against all 1,750 loose-path resolutions in
    # np_orgs.csv before this one was chosen:
    #
    #   "filed name carries no Native term"  refused 1,489 of 1,750 - far too
    #     blunt. It would have thrown away Chickasaw Development Corporation,
    #     San Carlos Apache Healthcare Foundation, Tonto Apache School, Karuk
    #     New Markets and Tlingit & Haida Foundation, all correct.
    #   "org state disagrees with tribe state"  refused 1,067 - a strong
    #     signal (it catches the AL/AR "Cherokee" groups and Laguna Woods CA
    #     vs Laguna Pueblo NM) but too broad to apply blind, and it cannot see
    #     Umatilla Electric, which is genuinely in Oregon. Queued for the
    #     owner rather than applied here.
    #
    # This set is deliberately narrow: forms a federally recognized tribe is
    # essentially never the filer of. HEALTHCARE, HOSPITAL, MEDICAL, CLINIC
    # and FIRE are DELIBERATELY EXCLUDED - tribes run all of those, and San
    # Carlos Apache Healthcare Foundation is a real tribal foundation that an
    # earlier draft of this guard wrongly refused.
    #
    # Measured effect: 34 refusals out of 1,750, and every one inspected is a
    # false positive - rural electric co-ops, volunteer hose companies, arts
    # festivals, realtor boards, a cooperative nursery. Zero true matches lost.
    hit = ft & CIVIC_UTILITY
    if hit and not (ft & NATIVE_TERM):
        return ("REFUSED_CIVIC_UTILITY:" + ",".join(sorted(hit))
                + " - a utility or civic-event body carrying a place name,"
                + " and the filed name claims no Native status")
    return ""


# Filed names that are the SAME entity under an older or variant name,
# verified against the spine 2026-08-28 (rename, spelling, or full legal name).
# These are equivalences, not matches - the spine row already exists.
# NOT here on purpose: BARONA (-> CNSF-CPTNGR-BA?), BATTLE MOUNTAIN
# (-> CNSF-TEMOAK-BT?), PLEASANT POINT (-> Passamaquoddy constituent?) - those
# are CONSTITUENT identifications, held for an owner ruling.
RESOLUTIONS = {
    "SAN MANUEL BAND OF MISSION INDIANS": ("TRBF-YHVTSM-00", "renamed: Yuhaaviatam of San Manuel Nation"),
    "FT MC DOWELL YAVAPAI NATION": ("TRBF-FMCDWL-00", "spelling: Fort McDowell"),
    "SOKAOGAN CHIPPEWA COMMUNITY": ("TRBF-SOKGON-00", "spelling: Sokaogon"),
    "FORT SILL APACHE TRIBE": ("TRBF-FSCWSA-00", "full name: Fort Sill-Chiricahua-Warm Springs Apache"),
    "COLUSA INDIAN COMMUNITY COUNCIL": ("TRBF-CACHLD-00", "legal name: Cachil DeHe Band of Wintun Indians of the Colusa Indian Community"),
    "AROOSTOOK MICMAC COUNCIL": ("TRBF-MIKMAQ-00", "renamed: Mi'kmaq Nation"),
    "NORTHFORK RANCHERIA OF MONO INDIANS": ("TRBF-NORFRK-00", "spelling: North Fork Rancheria"),
    # --- researched edge cases, 2026-08-28 (owner directive: resolve them) ---
    # FR-combined-listing constituents and joint tribes, each grounded in the
    # spine's own modeling of the Federal Register parentheticals:
    "ONEIDA NATION": ("TRBF-ONDAWI-00",
        "state evidence: 2,208 of 2,210 rows and $890M of $890M are WI"),
    "SHOSHONE-BANNOCK TRIBES OF THE FORT HALL RESERVATION OF IDAHO": ("TRBF-FTHALL-00",
        "the FR lists ONE tribe; money to the joint government, not a band"),
    "PLEASANT POINT INDIAN RESERVATION": ("CNSF-PSMQDY-PP",
        "Sipayik/Pleasant Point constituent of the Passamaquoddy Tribe"),
    "BARONA BAND OF MISSION INDIANS": ("CNSF-CPTNGR-BA",
        "Barona Group of the Capitan Grande combined FR listing"),
    "BATTLE MOUNTAIN BAND COUNCIL": ("CNSF-TEMOAK-BT",
        "Battle Mountain Band, one of Te-Moak's four FR-parenthetical bands"),
    "BISHOP INDIAN TRIBAL COUNCIL": ("TRBF-BISHOP-00", "Bishop Paiute Tribe"),
    # Te-Moak's other three FR-parenthetical bands (Battle Mountain above):
    "ELKO BAND COUNCIL": ("CNSF-TEMOAK-EK", "Elko Band of the Te-Moak Tribe"),
    "SOUTH FORK BAND ENVIRONMENTAL": ("CNSF-TEMOAK-SF", "South Fork Band of the Te-Moak Tribe"),
    "WELLS BAND COUNCIL": ("CNSF-TEMOAK-WL", "Wells Band of the Te-Moak Tribe"),
    # Paiute Indian Tribe of Utah's FR-parenthetical bands:
    "SHIVWITS BAND OF PAIUTES": ("CNSF-PTTRUT-SW", "Shivwits Band, Paiute Indian Tribe of Utah"),
    "KANOSH BAND OF PAIUTE INDIAN": ("CNSF-PTTRUT-KN", "Kanosh Band, Paiute Indian Tribe of Utah"),
    "INDIAN PEAKS BAND OF UTAH PAIUTES": ("CNSF-PTTRUT-IP", "Indian Peaks Band, Paiute Indian Tribe of Utah"),
    # renames the filings predate:
    "NORTHWESTERN BAND OF THE SHOSHON NATION": ("TRBF-NWSSHN-00", "Northwestern Band of the Shoshone Nation (filed with a typo)"),
    "YOMBA TRIBAL COUNCIL INC": ("TRBF-YOMBAT-00", "Yomba Shoshone Tribe"),
    "CORTINA BAND OF WINTUN INDIANS": ("TRBF-KLTSLD-00", "renamed: Kletsel Dehe Wintun Nation"),
    "STEWARTS POINT RANCHERIA": ("TRBF-KASHIA-00", "Kashia Band of Pomo Indians of the Stewarts Point Rancheria"),
    # a tribally-owned ENTERPRISE, attributed to its ultimate owner per the
    # hub model - Suh'dutsing ('cedar' in Paiute) is the Cedar Band's company:
    "SUH'DUTSING TECHNOLOGIES, LLC": ("CNSF-PTTRUT-CD", "enterprise of the Cedar Band of Paiutes (ultimate-owner attribution)"),
    # NOT NATIVE - an Ohio county housing authority that carries a Delaware-
    # origin place name. Excluded, never mapped:
    "TUSCARAWAS METROPOLITAN HOUSING": (None, "EXCLUDED: Tuscarawas County OH metropolitan housing authority - not a Native entity"),
}


def build_index():
    exact = {}
    gov = []           # (distinctive tokens, tid, canonical) - gov-class only
    state_of = {}      # tid -> spine state, for the AGENTS state-agreement guard
    class_of = {}      # tid -> spine entity_class. THE SPINE IS THE AUTHORITY
    #                    ON CLASS, and nothing else may be read for it.
    with SPINE.open(encoding="utf-8", errors="replace", newline="") as f:
        for r in csv.DictReader(f):
            tid = (r.get("tribe_id") or "").strip()
            cls = r.get("entity_class", "")
            class_of[tid] = cls
            names = [r.get("canonical_name", "")] + (r.get("aliases") or "").split(";")
            for nm in names:
                k = light(nm)
                if k:
                    exact.setdefault(k, set()).add((tid, cls))
            state_of[tid] = (r.get("state") or "").strip().upper()
            if cls in GOV:
                t = tokens(r.get("canonical_name", ""))
                if t:
                    gov.append((t, tid, r.get("canonical_name", "")))
    if ALIASES.exists():
        # A CLASS-LESS CANDIDATE DEFEATS EVERY CLASS GUARD DOWNSTREAM.
        #
        # This block read `r.get("entity_class", "")` from entity_aliases.csv,
        # WHICH HAS NO SUCH COLUMN - its header is alias_id, entity_id,
        # alias_name, ... and no class anywhere. So every alias-sourced
        # candidate arrived with cls = "" and the gov-class filter in
        # `resolve()`, `g = {t for t, cl in c if cl in GOV}`, could never
        # match one. Two consequences, both measured 2026-08-30:
        #
        #   * "Native Village of Elim" went AMBIGUOUS_EXACT rather than
        #     resolving to the village GOVERNMENT - the guard that exists
        #     precisely for that case could not see the candidate.
        #   * Three ANCSA village CORPORATIONS carried a Federal Register
        #     roster name as a spine alias, so `resolve()` returned them
        #     UNIQUELY, no ambiguity ever arose, the gov-class tiebreak never
        #     ran, and 510 recorded `entity.is_federally_recognized = yes` on
        #     them at tier A with winning_source = fr_tribal_list. The FR
        #     roster lists GOVERNMENTS and cannot name a corporation; the
        #     system was attesting that a federal authority vouched for a
        #     claim that authority never made.
        #
        # The class now comes from the SPINE, keyed by tribe_id - the one
        # place that owns it - and never from a column on the alias row.
        # A tid the spine does not know contributes no candidate at all,
        # because a candidate we cannot class is a candidate no guard can
        # refuse.
        unknown = {}
        brand_solo = {}
        with ALIASES.open(encoding="utf-8", errors="replace", newline="") as f:
            for r in csv.DictReader(f):
                tid = (r.get("entity_id") or r.get("tribe_id") or "").strip()
                nm = r.get("alias") or r.get("alias_name") or r.get("name") or ""
                k = light(nm)
                if not (tid and k):
                    continue
                if tid not in class_of:
                    unknown[tid] = unknown.get(tid, 0) + 1
                    continue
                # A SINGLE-TOKEN BRAND WORD IS NOT AN ENTITY NAME.
                #
                # Measured 2026-09-01 by shard J: entity_aliases.csv holds 104
                # rows at alias_type='brand' and EVERY ONE is a single token.
                # Among them: advantage, ancillary, applied, broadband,
                # colorado, cultural, door, feet, field, fire, indigenous,
                # link, managed, media, nexus, peak, program, research. These
                # are fragments of company names, not names. `cultural`
                # resolved to Southern Ute; `indigenous` to Delaware Nation.
                #
                # 541 already refuses all 104 and names them. Nothing else did,
                # and this index is what `resolve()` matches against - so the
                # hub itself was carrying them.
                #
                # Live exposure when this guard was added was ONE: `Alutiiq` is
                # both the register canonical name of the Afognak village
                # corporation and a brand alias pointing at a different entity.
                # Small, because `clean()` does not strip INC/LLC, so only a
                # record whose WHOLE normalized name is the bare token can
                # collide. It is fixed here anyway: the surface grows with every
                # harvest, nine entity shards are landing new business names as
                # this is written, and a latent identity defect fires on data
                # that has not arrived yet. This is the Enterprise Rancheria
                # shape (NATIVE_ENTITY_NUANCES) living in the brand registry.
                #
                # Multi-token brand aliases are kept - "Ho-Chunk Inc" is a real
                # trading name and refusing it would lose true matches.
                if (r.get("alias_type") or "").strip() == "brand" \
                        and len(k.split()) == 1:
                    brand_solo[k] = tid
                    continue
                exact.setdefault(k, set()).add((tid, class_of[tid]))
        if unknown:
            top = sorted(unknown.items(), key=lambda kv: -kv[1])[:5]
            print(f"  build_index: {sum(unknown.values()):,} alias row(s) name "
                  f"{len(unknown):,} entity id(s) the spine does not carry - "
                  f"contributed NO candidate, because a candidate with no "
                  f"class is one no class guard can refuse. Worst: "
                  + ", ".join(f"{t} x{n}" for t, n in top))
        if brand_solo:
            sample = ", ".join(sorted(brand_solo)[:8])
            print(f"  build_index: refused {len(brand_solo):,} single-token "
                  f"alias_type='brand' row(s) - a brand fragment is not an "
                  f"entity name. e.g. {sample}")
    return exact, gov, state_of


def resolve(filed: str, exact, gov, state_of, top_states=""):
    hit = RESOLUTIONS.get(clean(filed).replace(" THE", "").strip()) or RESOLUTIONS.get((filed or "").strip().upper())
    if hit:
        if hit[0] is None:
            return None, f"EXCLUDED: {hit[1]}"
        return hit[0], f"declared equivalence: {hit[1]}"
    k = light(filed)
    c = exact.get(k, set())
    if len(c) == 1:
        return next(iter(c))[0], "exact normalized name/alias, unique"
    if len(c) > 1:
        g = {t for t, cl in c if cl in GOV}
        if len(g) == 1:
            return next(iter(g)), "exact normalized, unique among government-class"
        # AGENTS state-agreement guard: the filing's own states break the tie
        # (Oneida NY vs Oneida WI is undecidable from the name and decided by
        # the state on the money).
        st = {x.strip().upper() for x in (top_states or "").replace(";", ",").split(",") if x.strip()}
        g2 = {t for t in (g or {x for x, _ in c}) if state_of.get(t) in st}
        if len(g2) == 1:
            return next(iter(g2)), "exact normalized + state agreement (AGENTS guard)"
        return None, "AMBIGUOUS_EXACT:" + ",".join(sorted(t for t, _ in c)[:4])
    ft = tokens(filed)
    if not ft:
        return None, "no distinctive tokens"
    hits = {(tid, canon) for t, tid, canon in gov if t and t <= ft}
    # THE LOOSE-PATH GUARDS. Everything below this line reaches its answer by
    # "the spine entity's tokens are a subset of the filed name", which for a
    # single-token entity whose token is a US place name is satisfied by every
    # organisation in the county. 2,458 names a human already refused resolved
    # through here before this ran. See ADMIN_GEOGRAPHY / CIVIC_FORM above.
    if hits:
        kept = {(tid, cn) for tid, cn in hits
                if not loose_path_refusal(filed, cn)}
        if not kept:
            return None, loose_path_refusal(filed, sorted(hits)[0][1])
        hits = kept
    # prefer the most specific candidate: drop any hit whose tokens are a
    # strict subset of another hit's tokens (e.g. 'Seminole' loses to
    # 'Seminole Oklahoma' when both are subsets of the filed name)
    if len(hits) > 1:
        toks = {tid: t for t, tid, _ in gov}
        hits = {(tid, cn) for tid, cn in hits
                if not any(o != tid and toks.get(tid, frozenset()) < toks.get(o, frozenset())
                           for o, _ in hits)}
    if len(hits) == 1:
        tid, canon = next(iter(hits))
        return tid, f"gov-class distinctive-token match on {canon!r}, unique"
    if len(hits) > 1:
        st = {x.strip().upper() for x in (top_states or "").replace(";", ",").split(",") if x.strip()}
        h2 = {(tid, cn) for tid, cn in hits if state_of.get(tid) in st}
        if len(h2) == 1:
            tid, canon = next(iter(h2))
            return tid, f"gov-class token match on {canon!r} + state agreement (AGENTS guard)"
        # coverage: the candidate whose canonical explains strictly more of the
        # filed name wins (CSKT covers CONFEDERATED+SALISH+KOOTENAI; Kootenai
        # Idaho covers one). Runs AFTER the state guard so a same-coverage,
        # different-state pair is already settled.
        pool = h2 if h2 else hits
        toks = {tid: t for t, tid, _ in gov}
        best = sorted(pool, key=lambda h: -len(toks.get(h[0], frozenset()) & ft))
        if len(best) >= 2:
            c0 = len(toks.get(best[0][0], frozenset()) & ft)
            c1 = len(toks.get(best[1][0], frozenset()) & ft)
            if c0 > c1:
                tid, canon = best[0]
                return tid, f"gov-class token match on {canon!r}, covers {c0} vs {c1} filed tokens"
        # leading-token rule: in "X Band of Y Indians", X names the tribe.
        # (Ramona Band of Cahuilla -> Ramona, not Cahuilla Band.)
        lead = clean(filed).split()
        lead = next((w for w in lead if w not in GENERIC), None)
        if lead:
            h3 = {(tid, cn) for tid, cn in pool if lead in toks.get(tid, frozenset())}
            if len(h3) == 1:
                tid, canon = next(iter(h3))
                return tid, f"gov-class token match on {canon!r}, leading filed token"
        # parent/constituent rule: when the candidates share an id stem and one
        # is the parent (-00) of the other, the filed name naming the
        # constituent's own tokens decides for the constituent.
        # (MINNESOTA CHIPPEWA TRIBE - WHITE EARTH BAND -> CNSF-MINNCH-WE.)
        stems = {}
        for tid, cn in pool:
            stems.setdefault(tid.split("-")[1] if "-" in tid else tid, []).append((tid, cn))
        if len(stems) == 1:
            fam = next(iter(stems.values()))
            kids = [(t, c) for t, c in fam if not t.endswith("-00")]
            if len(kids) == 1 and toks.get(kids[0][0], frozenset()) & ft:
                tid, canon = kids[0]
                return tid, f"constituent of same family named in filing ({canon!r})"
        return None, "AMBIGUOUS_TOKEN:" + ",".join(sorted(t for t, _ in hits)[:4])
    return None, "no candidate"


STATE_CACHE = ROOT / "data" / "interim" / "assistance_legacy_state_map.json"


def legacy_states():
    """legacy integer -> set of recipient states, measured from the table.

    The crosswalk's top_states column is blank on the rows that need the
    state-agreement guard most (CSKT, Oneida, Flandreau), so the evidence comes
    from the money itself: recipient_state_code on the lineageA-keyed rows.
    Cached; delete the cache after any rebuild of the table.
    """
    import json
    if STATE_CACHE.exists():
        return {k: set(v) for k, v in json.loads(STATE_CACHE.read_text(encoding="utf-8")).items()}
    out = {}
    with TABLE.open(encoding="utf-8", errors="replace", newline="") as f:
        for row in csv.DictReader(f):
            # RENAMED 2026-09-01 by 843: tribe_id_scheme_resolved ->
            # attribution_status. Reading the dead name returned None on every
            # row, so this cache silently wrote {} and the state-agreement
            # guard - the thing that stops CSKT/Oneida/Flandreau being matched
            # across state lines - had no evidence at all.
            if row.get("attribution_status") != "lineageA_dofile_integer":
                continue
            t = (row.get("tribe_id") or "").strip()
            st = (row.get("recipient_state_code") or "").strip().upper()
            if t and st:
                out.setdefault(t, set()).add(st)
    STATE_CACHE.parent.mkdir(parents=True, exist_ok=True)
    STATE_CACHE.write_text(json.dumps({k: sorted(v) for k, v in out.items()}), encoding="utf-8")
    return out


def phase_reconcile(argv) -> int:
    apply = "--apply" in argv
    exact, gov, state_of = build_index()
    lstates = legacy_states()

    rows = list(csv.DictReader(XWALK.open(encoding="utf-8", errors="replace", newline="")))
    mapping = {}
    resolved, ambiguous, none_ = [], [], []
    for r in rows:
        st = ",".join(lstates.get(r["legacy_tribe_id"].strip(), r.get("top_states", "").split(",")))
        tid, basis = resolve(r["legacy_name_as_filed"], exact, gov, state_of, st)
        if tid:
            mapping[r["legacy_tribe_id"].strip()] = (tid, basis)
            r["proposed_cedar_tribe_id"] = tid
            r["confidence_tier"] = "A"
            r["match_basis"] = basis
            resolved.append(r)
        elif basis.startswith("AMBIGUOUS"):
            r["match_basis"] = basis
            ambiguous.append(r)
        else:
            none_.append(r)

    dd = lambda L: sum(float(x["obligated_usd"] or 0) for x in L)
    T = dd(rows) or 1
    print(f"  {len(rows)} legacy ids:")
    print(f"    RESOLVED : {len(resolved):>4}  ${dd(resolved)/1e9:6.2f}B  ({100*dd(resolved)/T:.1f}%)")
    print(f"    ambiguous: {len(ambiguous):>4}  ${dd(ambiguous)/1e9:6.2f}B")
    print(f"    unmatched: {len(none_):>4}  ${dd(none_)/1e9:6.2f}B  <- spine gaps, list below")
    for r in sorted(ambiguous, key=lambda x: -float(x["obligated_usd"] or 0))[:6]:
        print(f"      AMBIG ${float(r['obligated_usd'])/1e9:5.2f}B  {r['legacy_name_as_filed'][:44]:46} {r['match_basis'][:56]}")
    for r in sorted(none_, key=lambda x: -float(x["obligated_usd"] or 0))[:12]:
        print(f"      NONE  ${float(r['obligated_usd'])/1e9:5.2f}B  {r['legacy_name_as_filed'][:60]}")

    if not apply:
        print("\n  DRY RUN - pass --apply to write the crosswalk and the table.")
        return 0

    # ---- crosswalk, in place ----
    import shutil
    bak = str(XWALK) + f".bak_{TODAY}_pre503"
    if not os.path.exists(bak):
        shutil.copy2(XWALK, bak)
    tmp = str(XWALK) + ".part"
    with io.open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, XWALK)
    print(f"\n  crosswalk updated ({len(resolved)} resolved rows), backup at {os.path.basename(bak)}")

    # ---- the big table, streamed ----
    bak2 = str(TABLE) + f".bak_{TODAY}_pre503"
    if not os.path.exists(bak2):
        shutil.copy2(TABLE, bak2)
    tmp2 = str(TABLE) + ".part"
    n_upd = 0
    with TABLE.open(encoding="utf-8", errors="replace", newline="") as fin, \
         io.open(tmp2, "w", encoding="utf-8", newline="") as fout:
        rdr = csv.DictReader(fin)
        w = csv.DictWriter(fout, fieldnames=rdr.fieldnames)
        w.writeheader()
        # UEI pass (owner directive 2026-08-28: a row with a code is not
        # unattributable). The ledger row's TIER TRAVELS - the key being exact
        # says nothing about the link:
        #   A -> attribute;  X -> EXCLUDE (owner ruled NOT native - attributing
        #   these is the 317-exclusions-published-as-attributions defect);
        #   B/C -> proposals only, in the columns built for proposals.
        led = {}
        with (ROOT / "data" / "clean" / "cedar_identifier_ledger_final.csv").open(
                encoding="utf-8", errors="replace", newline="") as lf:
            for lr in csv.DictReader(lf):
                if lr.get("identifier_type") == "UEI":
                    led[(lr.get("identifier") or "").strip().upper()] = (
                        lr.get("tribe_id"), lr.get("confidence_tier"),
                        lr.get("attribution_method"))
        n_uei_a = n_uei_x = n_uei_prop = 0
        n_native = 0
        legacy_col_present = "tribe_id" in (rdr.fieldnames or [])
        for row in rdr:
            sch = row.get("attribution_status")
            if sch == "lineageA_dofile_integer" and legacy_col_present:
                hit = mapping.get((row.get("tribe_id") or "").strip())
                if hit:
                    tid, basis = hit
                    row["tribe_id_neid"] = tid
                    row["attribution_status"] = "cedar_neid"
                    row["attribution_basis"] = f"{basis} [{BASIS_TAG} {TODAY}]"
                    n_upd += 1
            elif (sch == "cedar_neid" and legacy_col_present
                  and not (row.get("tribe_id_neid") or "").strip()):
                # THE INVARIANT: scheme cedar_neid => tribe_id_neid holds the
                # Cedar ID, on every row. The pre-503 rows kept theirs in
                # tribe_id with tribe_id_neid blank; the 503-promoted rows keep
                # the legacy integer in tribe_id. Without this backfill the one
                # scheme label covered two layouts and a consumer grouping on
                # either column silently mixed keys.
                row["tribe_id_neid"] = (row.get("tribe_id") or "").strip()
                n_native += 1
            elif sch == "unattributed":
                u = (row.get("recipient_uei") or "").strip().upper()
                hit = led.get(u)
                if hit:
                    tid, tier, method = hit
                    if tier == "A":
                        row["tribe_id_neid"] = tid
                        row["attribution_status"] = "cedar_neid"
                        row["attribution_basis"] = (
                            f"UEI {u} in ledger, tier A via {method} [{BASIS_TAG} {TODAY}]")
                        n_uei_a += 1
                    elif tier == "X":
                        row["attribution_status"] = "excluded_not_native"
                        row["attribution_basis"] = (
                            f"UEI {u} owner-ruled NOT native (tier X via {method}) [{BASIS_TAG} {TODAY}]")
                        n_uei_x += 1
                    elif not (row.get("tribe_id_neid_proposed") or "").strip():
                        row["tribe_id_neid_proposed"] = tid
                        row["tribe_id_neid_proposed_tier"] = tier
                        row["tribe_id_neid_proposed_basis"] = (
                            f"UEI {u} in ledger via {method} [{BASIS_TAG} {TODAY}]")
                        n_uei_prop += 1
            w.writerow(row)
    os.replace(tmp2, TABLE)
    print(f"  federal_funding_transactions: {n_upd:,} rows moved to cedar_neid, "
          f"{n_native:,} native backfills; UEI pass: {n_uei_a:,} tier-A attributed, "
          f"{n_uei_x:,} excluded-not-native, {n_uei_prop:,} B/C proposals; "
          f"backup at {os.path.basename(bak2)}")
    print("  legacy integers preserved in `tribe_id` as provenance.")
    return 0



# ===================== PHASE 2: MINT ==========================


import csv
import io
import os
import sys
from datetime import date
from pathlib import Path

SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
REGISTER = ROOT / "data" / "spine" / "cedar_identity_register.csv"
XWALK = ROOT / "data" / "spine" / "legacy" / "assistance_tribe_id_crosswalk.csv"

# =====================================================================
# THE HANDLE CONTRACT - external review 2026-08-30, finding F6.
# =====================================================================
# `cedar_uid` is the stable external join key. A handle (TRBF-MIKMAQ-00) is a
# DISPLAY identifier and it changes on reclassification, which
# IDENTIFIER_STANDARD.md §0 has said since the day uids were minted.
#
# The policy was written and the code did not implement it. Before this
# change `phase_mint` keyed the existing-uid lookup on the HANDLE alone:
#
#   existing = {handle -> uid}          rebuilt from the register every run
#   uid = existing.get(handle)          a changed handle misses
#   if not uid: mint a NEW uid          <- the uid was not permanent either
#
# So a reclassification did three wrong things at once: it minted a second
# uid for an entity that already had one, it dropped the old handle from the
# register entirely (the register is documented as append-only), and a buyer
# who had joined on the handle silently lost their historical rows with no
# way to discover it. The contract is now enforced rather than described:
#
#   1. cedar_uid is permanent and is the only documented join key.
#   2. Handles are display identifiers, and an OLD handle always resolves to
#      the SAME uid - forever, through cedar_handle_history.csv.
#   3. A RETIRED HANDLE IS NEVER REUSED. Reassigning one to a different uid
#      is refused as a hard error, not warned about, because the failure is
#      silent at every later stage.
#   4. The history table retains (handle, cedar_uid, valid_from, valid_to,
#      status, change_reason) so the rebinding is auditable.
HANDLE_HISTORY = ROOT / "data" / "spine" / "cedar_handle_history.csv"
HANDLE_HISTORY_COLS = ["handle", "cedar_uid", "valid_from", "valid_to",
                       "status", "change_reason", "recorded_date"]


class HandleReuse(Exception):
    """A retired handle was pointed at a different entity. Never recoverable
    in place: whoever wrote it must pick a new handle."""


def read_handle_history():
    if not HANDLE_HISTORY.exists():
        return []
    with HANDLE_HISTORY.open(encoding="utf-8-sig", errors="replace",
                             newline="") as f:
        return list(csv.DictReader(f))


def handle_resolution_map():
    """EVERY handle ever issued -> its uid, retired ones included.

    This is what makes rule 2 above true. A buyer or an old panel that still
    carries `TRBF-MIKMAQ-00` after a reclassification resolves to the same
    entity it always did."""
    m = {}
    for r in read_handle_history():
        h = (r.get("handle") or "").strip()
        if h:
            m[h] = (r.get("cedar_uid") or "").strip()
    return m


def verify_handles():
    """The handle contract, checked rather than described. Returns a list of
    failure strings; empty means the contract holds.

    H1  a handle is bound to exactly one uid, forever
    H2  a retired handle still resolves (it is present in the history)
    H3  every uid in the history is still in the register - a uid is never
        dropped, even when its entity leaves the spine
    H4  at most one CURRENT handle per uid
    H5  every register handle appears in the history
    """
    out = []
    hist = read_handle_history()
    if not hist:
        return ["H0 no cedar_handle_history.csv - run "
                "`py -3 code/503_identity.py mint --apply`"]
    bind = {}
    current = {}
    for r in hist:
        h = (r.get("handle") or "").strip()
        u = (r.get("cedar_uid") or "").strip()
        if not h or not u:
            out.append(f"H1 history row with a blank handle or uid: {r}")
            continue
        if h in bind and bind[h] != u:
            out.append(f"H1 handle {h} is bound to TWO uids: {bind[h]} and "
                       f"{u}. A retired handle is never reused.")
        bind[h] = u
        if (r.get("status") or "") == "current":
            if u in current and current[u] != h:
                out.append(f"H4 uid {u} has two CURRENT handles: "
                           f"{current[u]} and {h}")
            current[u] = h
        elif not (r.get("valid_to") or "").strip():
            out.append(f"H2 handle {h} is not current and has no valid_to - "
                       f"a retirement with no date is not auditable")
    reg = {}
    if REGISTER.exists():
        with REGISTER.open(encoding="utf-8", errors="replace", newline="") as f:
            for r in csv.DictReader(f):
                reg[(r.get("handle") or "").strip()] = r["cedar_uid"]
    missing_uid = {u for u in bind.values()} - set(reg.values())
    if missing_uid:
        out.append(f"H3 {len(missing_uid)} uid(s) in the handle history are "
                   f"NOT in the identity register - a uid was dropped: "
                   f"{sorted(missing_uid)[:3]}")
    for h, u in reg.items():
        if h not in bind:
            out.append(f"H5 register handle {h} has no history row")
        elif bind[h] != u:
            out.append(f"H1 register binds {h} -> {u}; history binds it to "
                       f"{bind[h]}")
    return out


# Crockford base32: no I, L, O, U. A valid uid cannot contain an ambiguous glyph.
B32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

# Dated former names, from docs/NATIVE_ENTITY_NUANCES.md (verified 2026-08-28).
FORMER = {
    "TRBF-YHVTSM-00": "San Manuel Band of Mission Indians (until 2022)",
    "TRBF-KLTSLD-00": "Cortina Band of Wintun Indians (until 2021)",
    "TRBF-KASHIA-00": "Stewarts Point Rancheria (historical filings)",
    "TRBF-MIKMAQ-00": "Aroostook Band of Micmacs (until 2021)",
    "TRBF-OKYOWG-00": "San Juan Pueblo (until 2005)",
    "TRBF-MHATAT-00": "MHA Nation; Mandan, Hidatsa and Arikara Nation",
    "TRBF-FSCWSA-00": "Fort Sill Apache Tribe (short form)",
    "TRBF-CACHLD-00": "Colusa Indian Community (short form)",
    "TRBF-NORFRK-00": "Northfork Rancheria (spelling variant)",
    "TRBF-SOKGON-00": "Sokaogan Chippewa Community (spelling variant)",
    "TRBF-FMCDWL-00": "Ft. McDowell Yavapai Nation (spelling variant)",
    "TRBF-NWSSHN-00": "Northwestern Band of the Shoshon Nation (filing typo)",
}


def encode(n: int) -> str:
    """Sequential int -> 5-char Crockford payload."""
    s = ""
    for _ in range(5):
        s = B32[n % 32] + s
        n //= 32
    return s


# TWO check characters, from two INDEPENDENT weightings.
#
# A single mod-32 character misses ~1 in 32 substitutions - measured 2026-08-28
# on 400 real uids: 382/400 caught, 95.5%. For an identifier a customer will
# transcribe, that is not good enough, and it costs nothing to fix while the
# uids exist only in our own files. Two characters over different weight
# sequences take random-substitution miss rate to ~1/1024, and because the
# second weighting is non-linear (squares) it catches transpositions the linear
# one is blind to.
_W1 = (2, 3, 4, 5, 6)          # linear positional
_W2 = (1, 4, 9, 16, 25)        # quadratic - different null space


def check_chars(payload: str) -> str:
    v = [B32.index(c) for c in payload]
    a = sum(w * x for w, x in zip(_W1, v)) % 32
    b = sum(w * x for w, x in zip(_W2, v)) % 32
    return B32[a] + B32[b]


def check_char(payload: str) -> str:      # kept: older callers/tests
    return check_chars(payload)


def mint(n: int) -> str:
    p = encode(n)
    return f"CE-{p}-{check_chars(p)}"


def valid(uid: str) -> bool:
    try:
        _, p, c = uid.split("-")
        return len(p) == 5 and all(ch in B32 for ch in p) and check_chars(p) == c
    except ValueError:
        return False


def selftest() -> None:
    a = mint(1234)
    assert valid(a), "mint/valid roundtrip"
    p = a.split("-")[1]
    # substitution caught
    bad = p[:2] + B32[(B32.index(p[2]) + 1) % 32] + p[3:]
    assert check_char(bad) != a.split("-")[2], "substitution must break the check"
    # transposition caught
    if p[1] != p[2]:
        tp = p[0] + p[2] + p[1] + p[3:]
        assert check_char(tp) != a.split("-")[2], "transposition must break the check"
    # the zero-for-O error is UNREPRESENTABLE: O is not in the alphabet
    assert "O" not in B32 and "I" not in B32 and "L" not in B32 and "U" not in B32
    print("  self-test OK: check digit catches substitution + transposition; "
          "O/I/L/U cannot appear in a valid uid")


def legacy_map():
    """RETIRED 2026-09-01. handle -> legacy CICD integers, from the crosswalk.

    The owner retired the CICD scheme outright: *"no one uses CICD data, so
    it's not like we have to link ours to theirs. They should link ours to
    ours."* Its `gov-class distinctive-token match` had merged United
    Keetoowah Band into Cherokee Nation (820 rows, $181.9M) and filed an
    Ohio county housing authority as a tribe.

    Kept as a function because `152` still builds the crosswalk and the
    rebuild path reads it - but the register no longer carries the result.
    Nothing calls this. See `code/843_retire_cicd_scheme.py`."""
    out = {}
    if not XWALK.exists():
        return out
    for r in csv.DictReader(XWALK.open(encoding="utf-8", errors="replace", newline="")):
        tid = (r.get("proposed_cedar_tribe_id") or "").strip()
        if tid:
            out.setdefault(tid, []).append(r["legacy_tribe_id"].strip())
    return {k: ",".join(sorted(set(v))) for k, v in out.items()}


def phase_mint(argv) -> int:
    apply = "--apply" in argv
    verify = "--verify" in argv
    selftest()

    rows = list(csv.DictReader(SPINE.open(encoding="utf-8", errors="replace", newline="")))
    handles = [(r.get("tribe_id") or "").strip() or (r.get("cedar_entity_id") or "").strip()
               for r in rows]
    assert all(handles), "spine row without any handle"
    assert len(set(handles)) == len(handles), "duplicate handles in spine"

    # APPEND-ONLY: existing register assignments are immutable.
    existing, eid_uid, prior = {}, {}, []
    if REGISTER.exists():
        for r in csv.DictReader(REGISTER.open(encoding="utf-8", errors="replace", newline="")):
            prior.append(r)
            existing[r["handle"]] = r["cedar_uid"]
            eid = (r.get("cedar_entity_id") or "").strip()
            if eid:
                eid_uid.setdefault(eid, r["cedar_uid"])

    # THE HANDLE CONTRACT (F6). History first: a handle that was retired
    # years ago must still resolve, and the register only ever carries the
    # CURRENT handle.
    history = read_handle_history()
    hist_uid = handle_resolution_map()
    hist_status = {(r.get("handle") or "").strip(): (r.get("status") or "")
                   for r in history}
    current_handle_of = {}
    for r in history:
        if (r.get("status") or "") == "current":
            current_handle_of[(r.get("cedar_uid") or "").strip()] = \
                (r.get("handle") or "").strip()
    for h, u in existing.items():
        hist_uid.setdefault(h, u)
        current_handle_of.setdefault(u, h)

    # decode payloads to find max sequence
    def seq(uid):
        p = uid.split("-")[1]
        n = 0
        for ch in p:
            n = n * 32 + B32.index(ch)
        return n
    next_n = 1 + max((seq(u) for u in
                      list(existing.values()) + list(hist_uid.values())),
                     default=0)

    lm = legacy_map()
    register, minted = [], 0
    rebound, reused = [], []
    for r in sorted(rows, key=lambda x: (x.get("tribe_id") or x.get("cedar_entity_id") or "")):
        h = (r.get("tribe_id") or "").strip() or (r.get("cedar_entity_id") or "").strip()
        eid = (r.get("cedar_entity_id") or "").strip()
        e_uid = eid_uid.get(eid) if eid else ""
        # RULE 3, CHECKED BEFORE THE HANDLE IS HONOURED. A retired handle
        # reappearing in the spine is either the same entity coming back
        # (fine, same uid) or a NEW entity taking a dead name (never fine).
        # This is checked first because the lookup below would otherwise hand
        # the newcomer the retired entity's uid and every downstream join
        # would silently point at the wrong entity.
        if hist_status.get(h) == "retired":
            if not e_uid:
                raise HandleReuse(
                    f"retired handle {h!r} reappears in the spine on a row "
                    f"with no cedar_entity_id, so there is nothing to prove "
                    f"it is the same entity that retired it "
                    f"({hist_uid.get(h)}). A retired handle is never reused.")
            if e_uid != hist_uid.get(h):
                raise HandleReuse(
                    f"retired handle {h!r} was bound to {hist_uid.get(h)} and "
                    f"the spine now points it at {e_uid}. A retired handle is "
                    f"never reused - see docs/IDENTIFIER_STANDARD.md 'THE "
                    f"RECLASSIFICATION RULE'. Pick a new handle.")
        uid = hist_uid.get(h) or existing.get(h)
        if not uid and eid:
            # THE RECLASSIFICATION CASE. The handle is new but the entity is
            # not: follow it by cedar_entity_id and KEEP ITS UID. Before this
            # branch existed the row minted a second uid for an entity that
            # already had one, and the old handle vanished from the register.
            uid = e_uid
            if uid:
                rebound.append((current_handle_of.get(uid, "?"), h, uid))
        if not uid:
            uid = mint(next_n); next_n += 1; minted += 1
        if hist_uid.get(h) and hist_uid[h] != uid:
            reused.append((h, hist_uid[h], uid))
        register.append({
            "cedar_uid": uid,
            "handle": h,
            "cedar_entity_id": eid,
            "canonical_name": r.get("canonical_name", ""),
            "entity_class": r.get("entity_class", ""),
            "class_since_basis": "as recorded at first mint 2026-08-28; a "
                                 "reclassification updates this attribute and "
                                 "retires the handle to an alias - the uid "
                                 "never changes",
            "former_names": FORMER.get(h, ""),
            "minted": existing.get(h) and "" or TODAY,
            "register_status": "active",
        })

    if reused:
        raise HandleReuse(
            f"{len(reused)} handle(s) are bound to a DIFFERENT uid than the "
            f"handle history records: "
            + "; ".join(f"{h}: {was} -> {now}" for h, was, now in reused[:5]))

    # A UID IS NEVER DROPPED. An entity leaving the spine keeps its register
    # row, marked retired, because a buyer's historical rows still carry it.
    # The register is documented as append-only and, until this change, was
    # silently rebuilt from the spine every run.
    live = {x["cedar_uid"] for x in register}
    retired_rows = 0
    for r in prior:
        if r["cedar_uid"] in live:
            continue
        r = dict(r)
        r["register_status"] = "retired_no_longer_in_spine"
        register.append(r)
        retired_rows += 1

    uids = [x["cedar_uid"] for x in register]
    assert len(set(uids)) == len(uids), "uid collision"
    assert all(valid(u) for u in uids), "invalid uid minted"
    print(f"  {len(register):,} register rows -> {minted:,} new uids minted "
          f"({len(existing):,} preserved from existing register, "
          f"{retired_rows:,} retained for entities no longer in the spine)")
    if rebound:
        print(f"  {len(rebound)} handle(s) REBOUND to their existing uid "
              f"(reclassification, uid unchanged):")
        for was, now, u in rebound[:10]:
            print(f"      {was} -> {now}   {u}")
    print(f"  sample: {register[0]['cedar_uid']} = {register[0]['handle']} "
          f"({register[0]['canonical_name'][:30]})")
    print(f"  with former names: {sum(1 for x in register if x['former_names'])}")
    # `same_as_legacy_cicd` was dropped from the register by 843 on 2026-09-01.
    # This line was still reading it and `503 mint` DIED HERE with a KeyError -
    # the identity service's own mint phase, and therefore `503 all --apply`
    # and the C8 rebuild path, could not run at all.

    if verify:
        by_handle = {x["handle"]: x["cedar_uid"] for x in register}
        for table, col in [("federal_funding_transactions.csv", "tribe_id_neid"),
                           ("gaming_facilities.csv", "tribe_id")]:
            p = ROOT / "data" / "clean" / table
            n = hit = 0
            with p.open(encoding="utf-8", errors="replace", newline="") as f:
                for row in csv.DictReader(f):
                    v = (row.get(col) or "").strip()
                    if v:
                        n += 1
                        if v in by_handle:
                            hit += 1
            print(f"  TRANSITIVE: {table}.{col}: {hit:,}/{n:,} "
                  f"({100*hit/max(n,1):.1f}%) resolve to a permanent uid")
        return 0

    if not apply:
        print("\n  DRY RUN - pass --apply to write the register and enrich the spine.")
        return 0

    import shutil
    tmp = str(REGISTER) + ".part"
    regcols = ["cedar_uid", "handle", "cedar_entity_id", "canonical_name",
               "entity_class", "class_since_basis", "former_names",
               "minted", "register_status"]   # `same_as_legacy_cicd` retired by 843
    with io.open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=regcols, restval="",
                           extrasaction="ignore")
        w.writeheader(); w.writerows(register)
    os.replace(tmp, REGISTER)
    print(f"  wrote {REGISTER.relative_to(ROOT)}")

    # ---- the handle <-> uid history table (F6, rule 4) ----------------
    # Append-only. A handle row is closed (valid_to, status=retired) rather
    # than deleted, so an old handle keeps resolving and the rebinding is
    # auditable by the buyer it would otherwise have broken.
    hist_rows, seen_pairs = [], set()
    now_current = {x["cedar_uid"]: x["handle"] for x in register
                   if x.get("register_status") == "active"}
    for r in history:
        h, u = (r.get("handle") or "").strip(), (r.get("cedar_uid") or "").strip()
        seen_pairs.add((h, u))
        if r.get("status") == "current" and now_current.get(u) not in (h, None):
            r = dict(r)
            r["status"] = "retired"
            r["valid_to"] = TODAY
            r["change_reason"] = (
                r.get("change_reason") or
                f"handle changed to {now_current.get(u)} on {TODAY}; the uid "
                f"is unchanged and this handle still resolves to it")
        hist_rows.append(r)
    for x in register:
        h, u = x["handle"], x["cedar_uid"]
        if (h, u) in seen_pairs:
            continue
        hist_rows.append({
            "handle": h, "cedar_uid": u,
            "valid_from": x.get("minted") or TODAY, "valid_to": "",
            "status": ("current" if x.get("register_status") == "active"
                       else "retired"),
            "change_reason": ("first recorded binding" if not history else
                              "handle issued or first observed on this run"),
            "recorded_date": TODAY})
    tmp = str(HANDLE_HISTORY) + ".part"
    with io.open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HANDLE_HISTORY_COLS, restval="",
                           extrasaction="ignore")
        w.writeheader(); w.writerows(hist_rows)
    os.replace(tmp, HANDLE_HISTORY)
    n_ret = sum(1 for r in hist_rows if r.get("status") == "retired")
    print(f"  wrote {HANDLE_HISTORY.relative_to(ROOT)} - {len(hist_rows):,} "
          f"handle bindings, {n_ret:,} retired and still resolving")

    by_handle = {x["handle"]: x["cedar_uid"] for x in register}
    bak = str(SPINE) + f".bak_{TODAY}_pre504"
    if not os.path.exists(bak):
        shutil.copy2(SPINE, bak)
    fields = list(rows[0].keys())
    if "cedar_uid" not in fields:
        fields.append("cedar_uid")
    tmp = str(SPINE) + ".part"
    with io.open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            h = (r.get("tribe_id") or "").strip() or (r.get("cedar_entity_id") or "").strip()
            r["cedar_uid"] = by_handle.get(h, "")
            w.writerow(r)
    os.replace(tmp, SPINE)
    print(f"  spine enriched with cedar_uid (backup {os.path.basename(bak)})")
    print("  every dataset that joins tribe_id -> spine now resolves to the "
          "permanent identity transitively. Run --verify.")
    return 0



# ===================== PHASE 3: STAMP =========================


import csv
import io
import os
import shutil
import sys
from datetime import date
from pathlib import Path

CLEAN = ROOT / "data" / "clean"
REGISTER = ROOT / "data" / "spine" / "cedar_identity_register.csv"


# Preference order: the first present in a header is the entity column.
ID_COLS = ("cedar_uid_source", "tribe_id_neid", "tribe_id", "entity_id",
           "cedar_entity_id", "native_entity_id", "resolved_native_entity_id",
           "tribe_entity_id", "recipient_entity_id",
           "cedar_recipient_spine_entity_id", "operator_entity_id",
           "resolved_entity_id", "native_party_entity_id",
           "prime_native_tribe_id", "surrogate_entity_id", "nho_id",
           "acquirer_tribe_id", "parent_native_entity")


def register_map():
    """handle -> uid.

    UNTIL 2026-09-01 this also resolved the legacy CICD integers, because two
    panels (federal_funding_tribe_year_panel, entity_evidence_profile) still
    keyed on them. Both were re-measured on 2026-09-02 and NEITHER DOES: 843
    dropped `tribe_id` from the panel, and entity_evidence_profile keys on
    `cedar_entity_id` on all 1,313 rows. The register column the resolution
    read (`same_as_legacy_cicd`) is gone too, so the block below was resolving
    nothing while the docstring said it was load-bearing. Retired, not deleted:
    the crosswalk still lives at data/spine/legacy/ if a legacy integer ever
    has to be resolved by hand.
    """
    m, legacy = {}, {}
    # RETIRED HANDLES RESOLVE TOO (F6, rule 2). A dataset row or a buyer's
    # join key written before a reclassification must keep pointing at the
    # same entity; the history table is what makes that true, and it is read
    # FIRST so the current register can only ever confirm it.
    for h, u in handle_resolution_map().items():
        if h and u:
            m[h] = u
    with REGISTER.open(encoding="utf-8", errors="replace", newline="") as f:
        for r in csv.DictReader(f):
            uid = r["cedar_uid"]
            for k in ("handle", "cedar_entity_id"):
                v = (r.get(k) or "").strip()
                if v:
                    m[v] = uid
            # legacy CICD integers: retired 2026-09-01, see the docstring
    contested = []
    for old, uids in legacy.items():
        if len(uids) == 1:
            m.setdefault(old, next(iter(uids)))
        else:
            contested.append((old, sorted(uids)))
    for old, uids in sorted(contested):
        print(f"  legacy integer {old!r} claimed by {len(uids)} entities "
              f"({', '.join(uids[:3])}) - left unresolved, never first-wins")
    return m


def entity_col(path: Path):
    try:
        with path.open(encoding="utf-8", errors="replace", newline="") as f:
            hdr = next(csv.reader(f), [])
    except Exception:
        return None, []
    for c in ID_COLS:
        if c in hdr:
            return c, hdr
    return None, hdr


def phase_stamp(argv) -> int:
    apply = "--apply" in argv
    verify = "--verify" in argv
    try:
        import cedar_codebook as CB
        licensed = set(CB.LICENSED_SOURCE_FILES)
    except Exception:
        licensed = set()

    reg = register_map()
    print(f"  register: {len(set(reg.values())):,} entities, {len(reg):,} handles\n")

    stamped = 0
    skipped: list[str] = []
    rows_total = rows_hit = 0
    unknown_examples = {}
    report = []

    for p in sorted(CLEAN.glob("*.csv")):
        if ".bak_" in p.name or p.name.endswith(".part") or p.name in licensed:
            continue
        col, hdr = entity_col(p)
        if not col:
            skipped.append(p.name)
            continue
        # cedar_uid is DERIVED, so an existing column is re-stamped, never
        # skipped. Skipping would freeze a stale uid into a shipped dataset the
        # first time the register legitimately changes - which happened the same
        # day it was built, when the check character went from one char to two.

        n = hit = 0
        unk = set()
        try:
            if apply:
                bak = str(p) + f".bak_{TODAY}_pre505"
                if not os.path.exists(bak):
                    shutil.copy2(p, bak)
                tmp = str(p) + ".part"
                with p.open(encoding="utf-8", errors="replace", newline="") as fin, \
                     io.open(tmp, "w", encoding="utf-8", newline="") as fout:
                    rdr = csv.DictReader(fin)
                    fields = list(rdr.fieldnames or [])
                    if "cedar_uid" not in fields:
                        fields.append("cedar_uid")
                    w = csv.DictWriter(fout, fieldnames=fields)
                    w.writeheader()
                    for row in rdr:
                        v = (row.get(col) or "").strip()
                        if v:
                            n += 1
                            uid = reg.get(v)
                            if uid:
                                row["cedar_uid"] = uid; hit += 1
                            else:
                                row["cedar_uid"] = ""
                                if len(unk) < 3:
                                    unk.add(v)
                        else:
                            row["cedar_uid"] = ""
                        w.writerow(row)
                os.replace(tmp, p)
            else:
                with p.open(encoding="utf-8", errors="replace", newline="") as f:
                    for row in csv.DictReader(f):
                        v = (row.get(col) or "").strip()
                        if v:
                            n += 1
                            if reg.get(v):
                                hit += 1
                            elif len(unk) < 3:
                                unk.add(v)
        except Exception as e:
            report.append((p.name, col, -2, -2))
            print(f"    ERROR {p.name}: {type(e).__name__}")
            continue

        stamped += 1
        rows_total += n
        rows_hit += hit
        if unk:
            unknown_examples[p.name] = sorted(unk)
        report.append((p.name, col, n, hit))

    print(f"  tables carrying an entity column : {stamped:,}")
    print(f"  tables with none (skipped)       : {len(skipped):,}")
    print(f"  entity-bearing rows              : {rows_total:,}")
    print(f"  resolved to a permanent uid      : {rows_hit:,} "
          f"({100*rows_hit/max(rows_total,1):.1f}%)")
    print()
    worst = sorted((r for r in report if r[2] > 0 and r[3] < r[2]),
                   key=lambda r: (r[3] / r[2]))[:10]
    if worst:
        print("  lowest coverage - handles not in the register (blank, never guessed):")
        for name, col, n, hit in worst:
            ex = ", ".join(unknown_examples.get(name, [])[:2])
            print(f"    {name[:44]:46} {col:22} {hit:>7,}/{n:<7,} "
                  f"{100*hit/n:5.1f}%  e.g. {ex[:40]}")
    if apply:
        print(f"\n  stamped {stamped} tables. Backups: *.bak_{TODAY}_pre505")
    elif not verify:
        print("\n  DRY RUN - pass --apply to stamp.")
    return 0




def main() -> int:
    ap = argparse.ArgumentParser(description="Cedar identity layer")
    ap.add_argument("phase", choices=["all", "reconcile", "mint", "stamp", "verify"])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--max-mb", type=float, default=1200.0)
    a, extra = ap.parse_known_args()
    argv = sys.argv[:]

    if a.phase == "verify":
        hf = verify_handles()
        for f in hf:
            print(f"  FAIL  {f}")
        if not hf:
            _h = read_handle_history()
            print(f"  handle contract OK - {len(_h):,} bindings, "
                  f"{sum(1 for r in _h if r.get('status') == 'retired'):,} "
                  f"retired and still resolving, 0 reused")
        rc = phase_mint(["--verify"]) or phase_stamp(["--verify"])
        return 1 if hf else rc
    if a.phase == "reconcile":
        return phase_reconcile(argv)
    if a.phase == "mint":
        return phase_mint(argv)
    if a.phase == "stamp":
        return phase_stamp(argv)

    # all: the only correct order, and the reason this is one script
    for name, fn in (("reconcile", phase_reconcile), ("mint", phase_mint),
                     ("stamp", phase_stamp)):
        print("")
        print("=== " + name.upper() + " ===")
        rc = fn(argv)
        if rc:
            return rc
    return 0


if __name__ == "__main__":
    sys.exit(main())
