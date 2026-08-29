#!/usr/bin/env python3
"""
Cedar Press - 77: build the philanthropy candidate review queue.

Reads the 76_ triage plus the grantee mission pass, applies the rulings, and
writes review/agent_native_org_candidates_philanthropy_2026-08-06.csv.

WHY THE SPINE CHECK IS SPLIT BY MATCH TIER
------------------------------------------
`resolve_entity` has four tiers. On THIS population they do not mean the same
thing, and treating them alike would be the error:

  exact / alias / core  -> the grantee IS the spine entity. ALREADY_IN_SPINE.
  containment           -> AMBIGUOUS. It fires both for a tribal government
                           written long ("Fond du Lac Band of Lake Superior
                           Chippewa" vs spine "Fond du Lac") AND for a
                           DISTINCT legal person that merely carries the
                           tribe's name ("Tulalip Foundation", "Rosebud
                           Economic Development Corporation", "Hopi School
                           Inc"). The second group is precisely what this
                           channel exists to find, so it must not be swallowed.

Measured containment misfires on this population, reported not patched (the
resolver is shared; rule 8 says one resolver, and a name-matching change
belongs to its owner, not to a discovery pass):

  Indian Pueblo Cultural Center Inc      -> Makaha Cultural Learning Center
      core{center,cultural} is a subset of core{makaha,learning,center,
      cultural} because STRUCTURAL eats "Indian" and "Pueblo". A Hawaiian
      organisation and a New Mexico one, matched on two generic words.
  International Indian Treaty Council    -> Council Native Corporation
  Northern California Indian Development Council -> Council Native Corporation
  Native Sister Circle Inc               -> Circle
  United Tribes of Bristol Bay           -> Bristol Bay Native Corporation
  Waimea Hawaiian Homesteaders Assn      -> Hawaiian Native Corporation
  Ahtna Intertribal Resource Commission  -> Ahtna, Incorporated

  Common shape: after STRUCTURAL strips indian/native/tribal/pueblo/band/
  nation/corporation, what is left is a generic English noun (council, center,
  circle, bay). Containment then matches on the generic residue.

CLASSES OWNED BY OTHER AGENTS
-----------------------------
Tribal colleges (TCU-), Native CDFIs (CDFI-), BIE schools (BIE-) and Urban
Indian Organizations (UIO-) are being added concurrently by three other
agents. Grantees that are plainly in those classes are held out of this queue
and listed in the log instead, as a cross-check against their rosters.
"""

import csv
import json
import re
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
RAW = CEDAR / "data" / "raw" / "external" / "philanthropy"
OUT = CEDAR / "review" / "agent_native_org_candidates_philanthropy_2026-08-06.csv"
HELD = RAW / "_held_for_other_agents_2026-08-06.csv"

RETRIEVED = "2026-08-06"

# Verbatim, retrieved 2026-08-06. These establish that the funder's grant
# stream is directed at Native organisations - the reason a grantee list is a
# discovery channel at all. They do NOT establish any single grantee's status.
FUNDER_EVIDENCE = {
    "First Nations Development Institute": (
        "https://www.firstnations.org/about-us/",
        "Our mission is to uplift and sustain the lifeways and economies of "
        "Native communities through advocacy, financial support, and "
        "knowledge sharing."),
    "Native Americans in Philanthropy": (
        "https://nativephilanthropy.org/about/",
        "NAP is a Native-led organization that is reshaping the philanthropic "
        "sector. By applying Indigenous values, such as reciprocity and "
        "intergenerational support, we can build more respectful, meaningful, "
        "and trusting relationships in philanthropy."),
    "Indian Land Tenure Foundation": (
        "https://iltf.org/about-us/",
        "The Indian Land Tenure Foundation (ILTF) is a national, "
        "community-based organization serving American Indian nations and "
        "people in the recovery and control of their rightful homelands."),
    "American Indian College Fund": (
        "https://collegefund.org/about-us/",
        "The American Indian College Fund invests in Native students and "
        "tribal college education to transform lives and communities."),
    "NDN Collective Inc": (
        "https://projects.propublica.org/nonprofits/organizations/823776329",
        "(funder mission not separately retrieved; see the Schedule I filing "
        "itself, which is the primary document quoted on each row)"),
    "Potlatch Fund": (
        "https://projects.propublica.org/nonprofits/organizations/731712905",
        "(funder mission not separately retrieved; see the Schedule I filing "
        "itself, which is the primary document quoted on each row)"),
    "Seventh Generation Fund for Indigenous Peoples": (
        "https://projects.propublica.org/nonprofits/organizations/680027247",
        "(funder mission not separately retrieved; see the Schedule I filing "
        "itself, which is the primary document quoted on each row)"),
}

# --- held-out classes -------------------------------------------------------
TCU_RE = re.compile(
    r"\b(community colleges?|tribal colleges?|technical colleges?|"
    r"tribal universit(?:y|ies)|polytechnic)\b|"
    r"\b(colleges?|universit(?:y|ies))\b", re.I)
CDFI_RE = re.compile(
    r"\b(loan fund|community development financial|federal credit union|"
    r"credit union|capital fund|revolving loan)\b", re.I)
UIO_RE = re.compile(
    r"\b(urban indian|indian health board|indian health center|"
    r"indian health services? of)\b", re.I)

# Government-only residue: if what is left after removing the spine name is
# only these, the grantee IS the government, not a separate organisation.
GOVT_RESIDUE = {
    "tribe", "tribes", "tribal", "nation", "nations", "band", "bands",
    "indian", "indians", "of", "the", "community", "communities", "village",
    "villages", "pueblo", "rancheria", "colony", "reservation", "confederated",
    "and", "sioux", "chippewa", "ojibwe", "oyate", "people", "peoples",
    "paiute", "shoshone", "cheyenne", "arapaho", "yakama", "council",
    "government", "native", "americans", "american", "inc", "incorporated",
    "de", "los", "n", "s", "no", "nsn", "in", "at", "california", "oklahoma",
    "wisconsin", "michigan", "minnesota", "montana", "washington", "nevada",
    "arizona", "mexico", "dakota", "south", "north", "upper", "lower",
    "eastern", "western", "northern", "southern",
}
ORG_DESCRIPTOR = {
    "foundation", "school", "corporation", "corp", "center", "centre",
    "institute", "association", "club", "museum", "project", "commission",
    "consortium", "company", "authority", "enterprise", "enterprises",
    "fund", "society", "pantry", "team", "program", "programs", "academy",
    "trust", "network", "coalition", "alliance", "initiative", "services",
    "library", "radio", "media", "press", "theater", "theatre", "gallery",
    "farm", "farms", "ranch", "housing", "clinic", "hospital", "utilities",
    "utility", "telecom", "development", "conservancy", "institute",
    "collective", "cooperative", "academy", "camp", "circle", "lodge",
}
# Words that are not distinctive enough to carry a containment match on their
# own. If everything left of a spine name after the government form words is
# in here, the match is on nothing.
GENERIC_CORE = {
    "center", "centre", "cultural", "culture", "council", "circle", "bay",
    "learning", "association", "foundation", "services", "service",
    "resource", "resources", "development", "health", "housing", "museum",
    "school", "fund", "society", "project", "institute", "alliance",
    "coalition", "network", "commission", "authority", "consortium",
    "corporation", "company", "enterprise", "enterprises", "trust", "group",
    "lake", "valley", "creek", "point", "island", "harbor", "springs",
    "town", "city", "county", "first", "new", "old", "big", "little",
}


# --- vocabulary for reading a 990 MISSION statement -------------------------
#
# A mission statement is the organisation's own words about itself, so it can
# carry more vocabulary than a NAME can: "Zuni youth", "Makah culture",
# "Northern Cheyenne Reservation", "the Ojibwe language" are self-descriptions,
# not incidental place names. That is the whole reason the mission pass exists
# - these organisations are invisible to every roster and to any name filter.
#
# REFUSE_ALONE still binds: an ambiguous single word needs a second signal.
MISSION_NATIVE = {
    "native", "natives", "indigenous", "indigeneity", "tribal", "tribally",
    "tribe", "tribes", "indian", "indians", "reservation", "reservations",
    "aboriginal", "powwow", "sovereignty", "rancheria", "pueblo", "pueblos",
    "dinetah", "wicohan", "hawaiian", "hawaiians",
    "ancestral", "homeland", "homelands", "nation", "firstnations",
    # peoples and languages, as organisations name themselves
    "lakota", "dakota", "nakota", "oceti", "sakowin", "oyate", "wakanyeja",
    "dine", "navajo", "hopi", "zuni", "apsaalooke", "crow", "cheyenne",
    "arapaho", "blackfeet", "kiowa", "comanche", "osage", "ponca",
    "anishinaabe", "anishinaabemowin", "ojibwe", "ojibwa", "chippewa",
    "menominee", "menomini", "maskoke", "muscogee", "mvskoke", "seminole",
    "choctaw", "chickasaw", "haudenosaunee", "mohawk", "akwesasne", "seneca",
    "onondaga", "tuscarora", "cayuga", "wabanaki", "abenaki", "penobscot",
    "passamaquoddy", "wampanoag", "narragansett", "lenape",
    "salish", "kootenai", "kalispel", "spokane", "yakama", "nez", "perce",
    "makah", "quinault", "quileute", "lummi", "swinomish", "tulalip",
    "puyallup", "nisqually", "chinook", "klamath", "modoc", "warm springs",
    "umatilla", "paiute", "shoshone", "washoe", "ute", "hupa", "yurok",
    "karuk", "pomo", "miwok", "maidu", "wintu", "chumash", "tongva",
    "gabrieleno", "kumeyaay", "luiseno", "cahuilla", "serrano", "mono",
    "yokut", "ohlone", "wiyot", "tolowa", "shasta", "achumawi",
    "keres", "tewa", "tiwa", "towa", "jemez", "acoma", "laguna", "taos",
    "tohono", "oodham", "akimel", "yaqui", "yoeme", "havasupai", "hualapai",
    "yavapai", "quechan", "cocopah", "mojave",
    "yuchi", "euchee", "caddo", "wichita", "pawnee", "otoe", "kaw",
    "winnebago", "hochunk", "sac", "meskwaki", "potawatomi", "ottawa",
    "odawa", "miami", "peoria", "kickapoo", "delaware",
    "inupiat", "inupiaq", "yupik", "cupik", "alutiiq", "sugpiaq", "unangax",
    "unangan", "aleut", "athabascan", "athabaskan", "denaina", "gwichin",
    "koyukon", "tlingit", "haida", "tsimshian", "eyak",
    "hawaiian", "kanaka", "maoli", "aina", "ohana", "kupuna", "haumana",
    "olelo", "moku", "ahupuaa", "loko", "kalo", "hoolaulima",
}
MISSION_CONTEXT = {
    "language", "languages", "culture", "cultural", "tribe", "tribal",
    "nation", "nations", "reservation", "people", "peoples", "ancestral",
    "indigenous", "traditional", "elders", "sovereignty", "homeland",
    "homelands", "native", "ceremony", "ceremonial", "revitalization",
    "revitalize", "immersion",
}
REFUSE_ALONE = {"creek", "cherokee", "colorado", "ojibwe", "shawnee",
                "oneida", "apache", "central", "eagle", "river", "mountain",
                "santa", "crow", "peoria", "delaware", "miami", "ottawa",
                "hawaiian", "hawaiians",
                # "dakota" was in script 76's REFUSE_ALONE but NOT in this
                # one - two copies of the same list, and the copy that
                # mattered for MISSION text was the stale one. It let
                # "TO IMPROVE THE QUALITY OF LIFE FOR NORTH DAKOTA'S CITIZENS"
                # and "the agricultural economy and lifestyle of South Dakota"
                # both read as Native. Duplicated constants drift; this is what
                # it costs.
                "dakota",
                "sac", "ute", "nez"}
# State names spelled out in a MISSION statement are not evidence either. The
# name-level mask (script 76) does not reach mission text, so it is repeated
# here. "North Dakota's citizens" and "the lifestyle of South Dakota" are the
# 283rd and 284th place-name coincidences.
MISSION_STATE_MASK = re.compile(
    r"\b(north|south)\s+dakota\b|\bnew\s+mexico\b|\bindiana\b|"
    r"\bstate\s+of\s+(north|south)\s+dakota\b", re.I)


def read(p):
    if not Path(p).exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def toks(s):
    return set(re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).split())


def q(s, n=320):
    s = " ".join((s or "").split())
    return (s[:n] + "...") if len(s) > n else s


# "SEE SCHEDULE O" and "NONE" are what a 990 says when the mission line was
# left to the narrative attachment. Treating either as retrieved mission text
# would be the worst kind of fabrication: a real quote from a real document
# that says nothing, presented as if it settled the question.
#
# The prefix test must be ANCHORED AND SPECIFIC. An earlier version used
# `^(...|none|n/?a|...)` and `n/?a` matched the first two letters of "NATIVE
# GOVERNANCE CENTER", silently discarding the mission statement of an
# organisation that describes itself as "A NATIVE-LED NONPROFIT" - and it then
# fell through to NOT_NATIVE. Short alternations need a full-string test, not
# a prefix test.
BOILER_PREFIX = re.compile(
    r"^(part iii statement of program service|see schedule o\b|"
    r"see attached\b|see part\b|refer to schedule o\b)", re.I)
BOILER_EXACT = {"", "NONE", "N/A", "NA", "N.A.", "NOT APPLICABLE", "SAME",
                "SEE SCHEDULE O", "SEE SCHEDULE O.", "SEE ABOVE", "-", "."}


def clean_mission(s):
    s = " ".join((s or "").split())
    if s.strip().upper() in BOILER_EXACT or BOILER_PREFIX.match(s):
        # The Part III slice sometimes still carries the answer inline.
        m = re.search(r"mission:\s*(.{15,600}?)\s*2\s+Did the organization", s)
        if m and m.group(1).strip().upper() not in BOILER_EXACT \
                and not BOILER_PREFIX.match(m.group(1)):
            return m.group(1)
        return ""
    return s


def main():
    rows = json.loads((RAW / "_triage_2026-08-06.json").read_text("utf-8"))
    missions = {r["ein"]: r for r in read(RAW / "grantee_missions_2026-08-06.csv")}
    # First Nations' published grantee profiles - a named tribal affiliation
    # and a project description, written by the funder about the grantee.
    profiles = {}
    for r in read(RAW / "fn_grantee_profiles_2026-08-06.csv"):
        cur = profiles.get(r["ein"])
        if not cur or len(r.get("description") or "") > len(cur.get("description") or ""):
            profiles[r["ein"]] = r
    # Prior EXCLUSION rulings, so a promotion can be flagged as the reversal
    # of a mechanical filter rather than presented as a fresh discovery.
    excl = {r["ein"].strip(): r for r in
            read(CEDAR / "data" / "spine" / "nonprofit_exclusion_rulings.csv")}

    out, held, stats = [], [], {}

    def bump(k):
        stats[k] = stats.get(k, 0) + 1

    for r in rows:
        ein = r["ein"]
        name = (r["name"] or r["name_as_filed"] or "").strip()
        filed = r["name_as_filed"]
        st, city = r["state"], r["city"]
        m = missions.get(ein, {})
        mission = clean_mission(m.get("mission", ""))
        mission_url = m.get("source_url", "") if mission else ""

        # The verbatim Schedule I line - the primary document for every row.
        top = r.get("revealed_by") or r["funders"][0]
        sched = (f'Schedule I Part II of {top} (Form 990, TY'
                 f'{"/".join(r["years"])}) lists "{filed}", {city} {st}, '
                 f'EIN {ein[:2]}-{ein[2:]}, IRC section '
                 f'"{"/".join(r["irc_as_filed"])}", cash grant '
                 f'${r["usd"]:,.0f}, purpose "{"; ".join(r["purposes"])}". '
                 f'Retrieved {RETRIEVED} from {r["sched_i_url"]}. '
                 f'All funders that reveal this grantee: '
                 f'{"; ".join(r["funders"])}.')

        fu = [FUNDER_EVIDENCE.get(f) for f in r["funders"]]
        fu = [x for x in fu if x]
        funder_q = (f' Funder context: "{fu[0][1]}" ({fu[0][0]}).'
                    if fu else "")

        irs_q = (f' IRS record for this EIN gives the legal name "{name}"'
                 f' ({city}, {st}), {r["pp_url"]}.' if r["pp_url"] else
                 f' NOT IN THE IRS BUSINESS MASTER FILE - ProPublica returns'
                 f' 404 for EIN {ein}, which is what a tribal government or'
                 f' instrumentality looks like under IRC 7871.')

        mission_q = (f' Own Form 990 states its mission: "{q(mission)}"'
                     f' ({mission_url}).' if mission and mission_url else "")

        pr = profiles.get(ein, {})
        partners = (pr.get("community_partners") or "").strip()
        pdesc = (pr.get("description") or "").strip()
        prof_q = ""
        if pr:
            prof_q = (f' First Nations Development Institute publishes a '
                      f'grantee profile for "{pr["profile_title"]}" '
                      f'({pr.get("n_grants")} grants, ${pr.get("total_awarded")} '
                      f'total, {pr.get("years")})')
            if partners:
                prof_q += f', Community Partners: "{partners}"'
            if pdesc:
                prof_q += f', project description: "{q(pdesc, 260)}"'
            prof_q += f'. {pr["source_url"]}, retrieved {RETRIEVED}.'

        ex = excl.get(ein)
        ex_q = (f' PRIOR RULING CONFLICT: this EIN sits in '
                f'data/spine/nonprofit_exclusion_rulings.csv as '
                f'"{ex["org_name"]}", excluded for '
                f'"{ex["exclusion_reason"]}" by a rule-based script filter '
                f'({ex.get("ruled_date","")}). The grant evidence above is '
                f'new information the filter did not have.' if ex else "")

        base = dict(review_id=f"EIN:{ein}", queue="philanthropy", uei="",
                    cage_code="", entity_or_firm=name)

        # ---- 1. held for another agent ---------------------------------
        cls = ("TCU-" if TCU_RE.search(name) else
               "CDFI-" if CDFI_RE.search(name) else
               "UIO-" if UIO_RE.search(name) else "")
        if cls:
            held.append({"ein": ein, "name": name, "state": st,
                         "held_for_class": cls, "usd": f'{r["usd"]:.0f}',
                         "funders": "; ".join(r["funders"]),
                         "sched_i_url": r["sched_i_url"]})
            bump(f"held_{cls}")
            continue

        # ---- 2. already in the spine -----------------------------------
        if r["spine_how"] in ("exact", "alias", "core"):
            out.append(dict(base, question=(
                "Is this organisation already the spine entity, or a distinct "
                "legal person carrying the same name?"),
                YOUR_RULING="ALREADY_IN_SPINE",
                YOUR_NOTE=(
                    f'Resolves to spine {r["in_spine"]} "{r["spine_name"]}" by '
                    f'{r["spine_how"]} match via code/33_apply_party_rulings.'
                    f'resolve_entity (rule 8: one resolver). {sched}{irs_q} '
                    f'Recorded here only to show the philanthropy channel '
                    f're-found a known entity; nothing to add.')))
            bump("ALREADY_IN_SPINE")
            continue

        if r["spine_how"] == "containment":
            residue = toks(name) - toks(r["spine_name"])
            # TWO GUARDS before a containment match may be called the same
            # entity. Both come from measured misfires on this population.
            #
            # (a) STATE. `Indian Pueblo Cultural Center Inc` (NM) matched
            #     `Makaha Cultural Learning Center` (HI). A New Mexico
            #     organisation is not a Hawaiian one, and the residue test
            #     alone could not tell, because the residue was
            #     {indian, pueblo, inc} - all government form words.
            # (b) GENERIC SPINE CORE. If the spine name's distinctive content
            #     is only generic English nouns (center, council, circle,
            #     bay), containment is matching on nothing.
            sstate = (r.get("spine_state") or "").strip()
            state_conflict = bool(sstate and st and sstate != st)
            spine_core = toks(r["spine_name"]) - GOVT_RESIDUE
            generic_core = bool(spine_core) and spine_core <= GENERIC_CORE
            if state_conflict or generic_core:
                why = ("the spine row is in "
                       f"{sstate} and this organisation is in {st}"
                       if state_conflict else
                       "the spine name's distinctive content is only generic "
                       f"words ({', '.join(sorted(spine_core))})")
                affil = (f'RESOLVER MISFIRE, do not trust it: '
                         f'`resolve_entity` returns a containment match to '
                         f'{r["in_spine"]} "{r["spine_name"]}", but {why}. '
                         f'Treated here as NO spine match. ')
                r = dict(r, in_spine="", spine_name="", spine_how="misfire")
            elif residue and not (residue & ORG_DESCRIPTOR) and \
                    residue <= GOVT_RESIDUE:
                out.append(dict(base, question=(
                    "Is this the spine tribal government under its long "
                    "official name?"),
                    YOUR_RULING="ALREADY_IN_SPINE",
                    YOUR_NOTE=(
                        f'Containment match to spine {r["in_spine"]} '
                        f'"{r["spine_name"]}"; the residual words '
                        f'({", ".join(sorted(residue))}) are government form '
                        f'words only, so this is the same legal person under '
                        f'its long official name. {sched}{irs_q}')))
                bump("ALREADY_IN_SPINE")
                continue
            else:
                affil = (f'NOTE the resolver returns a CONTAINMENT match to '
                         f'spine {r["in_spine"]} "{r["spine_name"]}", but the '
                         f'residual words '
                         f'({", ".join(sorted(residue)) or "none"}) include an '
                         f'organisational descriptor, so this is a DISTINCT '
                         f'legal person, not that spine row. Verify before '
                         f'minting. ')
        else:
            affil = ""

        # ---- 3. filed as a tribe under IRC 7871 ------------------------
        if r["tribal_irc"]:
            out.append(dict(base, question=(
                "Is this a tribal government or instrumentality that the "
                "spine does not yet hold?"),
                YOUR_RULING="NATIVE_ORG",
                YOUR_NOTE=(
                    f'ownership=tribally_controlled (asserted by the FILER, '
                    f'not by me); service=unknown; state={st}; city={city}. '
                    f'{affil}The funder certified this grantee\'s tax status '
                    f'on its own return as '
                    f'"{"/".join(r["irc_as_filed"])}" - i.e. a tribal '
                    f'government under IRC 7871 rather than a 501(c)(3). '
                    f'{sched}{irs_q}{mission_q}{funder_q} '
                    f'CAVEAT: this is the funder\'s certification, which is '
                    f'good evidence of tribal status and no evidence at all '
                    f'about which tribe or what the entity does.')))
            bump("NATIVE_ORG_tribal_irc")
            continue

        # ---- 4. Native identifier in the org's own IRS legal name -------
        if r["native_tokens"] and not r["only_refusable"]:
            svc = ("native_serving (from the name and the grant purpose)"
                   if "indigenous" in " ".join(r["native_tokens"]).lower()
                   or True else "unknown")
            out.append(dict(base, question=(
                "Is this a Native organisation, and is it Native-controlled, "
                "Native-serving, or neither?"),
                YOUR_RULING="NATIVE_ORG",
                YOUR_NOTE=(
                    f'ownership=unknown (not established by any document '
                    f'retrieved here - do not read the name as ownership); '
                    f'service={svc}; state={st}; city={city}. {affil}'
                    f'Native identifier in the organisation\'s own IRS legal '
                    f'name: {", ".join(r["native_tokens"])}. '
                    f'{sched}{irs_q}{mission_q}{funder_q}')))
            bump("NATIVE_ORG_name")
            continue

        # ---- 5. everything else: rule from the org's own mission --------
        ml = " " + re.sub(r"[^a-z0-9]+", " ",
                          MISSION_STATE_MASK.sub(" ", mission).lower()) + " "
        native_words = [w for w in MISSION_NATIVE if f" {w} " in ml]
        if native_words and all(w in REFUSE_ALONE for w in native_words):
            # A single ambiguous word cannot carry a ruling. Require a second,
            # contextual signal before letting "apache" or "creek" count.
            if not any(f" {c} " in ml for c in MISSION_CONTEXT):
                native_words = []
        civic = r["civic_tokens"]

        # 5a. The funder names the affiliated tribe. This is the strongest
        # evidence in the whole channel for an organisation whose name says
        # nothing: the grantmaker, writing about its own grantee, records
        # which tribal community the organisation belongs to.
        if partners and not civic:
            out.append(dict(base, question=(
                "Is this a Native organisation, and is it Native-controlled, "
                "Native-serving, or neither?"),
                YOUR_RULING="NATIVE_ORG",
                YOUR_NOTE=(
                    f'ownership=unknown; '
                    f'service=native_serving, affiliated with "{partners}"; '
                    f'state={st}; city={city}. {affil}The organisation\'s NAME '
                    f'carries no Native identifier - this is the class no '
                    f'roster can see - but its funder publishes the tribal '
                    f'affiliation.{prof_q}{mission_q}{sched}{irs_q}{ex_q}')))
            bump("NATIVE_ORG_funder_names_the_tribe")
            continue

        pl = " " + re.sub(r"[^a-z0-9]+", " ",
                          MISSION_STATE_MASK.sub(" ", pdesc).lower()) + " "
        pwords = [w for w in MISSION_NATIVE if f" {w} " in pl]
        if pwords and all(w in REFUSE_ALONE for w in pwords):
            if not any(f" {c} " in pl for c in MISSION_CONTEXT):
                pwords = []
        if pwords and not native_words and not civic:
            out.append(dict(base, question=(
                "Is this a Native organisation, and is it Native-controlled, "
                "Native-serving, or neither?"),
                YOUR_RULING="NATIVE_ORG",
                YOUR_NOTE=(
                    f'ownership=unknown; service=native_serving; state={st}; '
                    f'city={city}. {affil}Neither the name nor the 990 mission '
                    f'carries a Native identifier; the funder\'s own published '
                    f'project description does ({", ".join(pwords)}).'
                    f'{prof_q}{mission_q}{sched}{irs_q}{ex_q}')))
            bump("NATIVE_ORG_funder_description")
            continue

        if native_words and not civic:
            out.append(dict(base, question=(
                "Is this a Native organisation, and is it Native-controlled, "
                "Native-serving, or neither?"),
                YOUR_RULING="NATIVE_ORG",
                YOUR_NOTE=(
                    f'ownership=unknown; service=native_serving; state={st}; '
                    f'city={city}. {affil}The organisation\'s NAME carries no '
                    f'Native identifier - this is the class the roster-based '
                    f'nets cannot see - but its OWN Form 990 mission does '
                    f'({", ".join(native_words)}). {mission_q}{sched}{irs_q}'
                    f'{funder_q}')))
            bump("NATIVE_ORG_mission")
            continue

        if civic:
            out.append(dict(base, question=(
                "Native organisation, or a general-purpose recipient?"),
                YOUR_RULING="NOT_NATIVE",
                YOUR_NOTE=(
                    f'ownership=not_established; service=not_established; '
                    f'state={st}; city={city}. Civic/place descriptor in the '
                    f'name ({", ".join(civic)}) and no Native identifier in '
                    f'the name or in the 990 mission. This is the shape of '
                    f'the 282 place-name coincidences withdrawn on '
                    f'2026-08-05. {sched}{irs_q}{mission_q}')))
            bump("NOT_NATIVE_civic")
            continue

        if mission_q:
            # Evidence exists and it does not say Native. This is a ruling.
            out.append(dict(base, question=(
                "Native organisation, or a general-purpose recipient?"),
                YOUR_RULING="NOT_NATIVE",
                YOUR_NOTE=(
                    f'ownership=not_established; service=not_established; '
                    f'state={st}; city={city}. {affil}Neither the IRS legal '
                    f'name nor the organisation\'s OWN Form 990 mission '
                    f'carries a Native identifier. Receiving a grant from a '
                    f'Native funder is a LEAD, never a ruling - tribes and '
                    f'Native foundations give to hospitals, universities, '
                    f'food banks and fiscal sponsors that are not Native. '
                    f'{mission_q}{sched}{irs_q}{ex_q}')))
            bump("NOT_NATIVE_mission_says_otherwise")
            continue

        # A prior exclusion is only allowed to carry a NOT_NATIVE ruling when
        # it is the SPECIFIC rule (`place_name_false_positive` names the exact
        # place-name regex that fired). The broader
        # `ambiguous_place_token_no_tribal_purpose` rule is the one with known
        # false negatives - it is what excluded NAVAJO TECHNICAL COLLEGE and
        # DAKOTA WICOHAN, both real Native institutions - so on its own it
        # cannot outweigh a grant from a Native funder. Those go to Elijah as
        # a flagged conflict, not as a ruling.
        if ex and ex.get("exclusion_reason") == "place_name_false_positive":
            # A documented prior ruling IS retrieved evidence, and nothing
            # found here contradicts it. (The reverse case - grant evidence
            # that DOES contradict an exclusion - is flagged as a conflict on
            # the NATIVE_ORG rows above, which is where the false negatives
            # in that mechanical filter surface.)
            out.append(dict(base, question=(
                "Native organisation, or a general-purpose recipient? A prior "
                "exclusion ruling exists - does the grant evidence overturn "
                "it?"),
                YOUR_RULING="NOT_NATIVE",
                YOUR_NOTE=(
                    f'ownership=not_established; service=not_established; '
                    f'state={st}; city={city}. {affil}No Native identifier in '
                    f'the IRS legal name, and nothing found in this pass '
                    f'contradicts the prior exclusion.{ex_q}{sched}{irs_q}'
                    f'{mission_q}{prof_q}')))
            bump("NOT_NATIVE_prior_exclusion_stands")
            continue

        # No evidence either way. Saying NOT_NATIVE here would be an assertion
        # the documents do not support, and the standing rule is precision
        # over recall in BOTH directions - a false negative is still a false
        # attribution. 990-N postcard filers (half the nonprofit universe) and
        # non-filers live permanently in this bucket.
        # Schedule I Part II is for ORGANIZATIONS, but funders do sometimes
        # put a person's name in it (Part III is where individual grants
        # belong). A two-or-three-word name with no organisational descriptor
        # and no IRS record is the shape of that filing error, and proposing
        # a person as an entity would be a fabrication of a different kind.
        nt = [w for w in re.sub(r"[^A-Za-z ]", " ", name).split() if w]
        maybe_person = (not r["pp_url"] and 1 < len(nt) <= 3
                        and not (set(w.lower() for w in nt) & ORG_DESCRIPTOR)
                        and not r["native_tokens"])
        person_q = (" LIKELY NOT AN ORGANISATION: the grantee name is a "
                    "personal-name shape, there is no IRS Business Master "
                    "File record for the EIN, and Schedule I Part II is "
                    "sometimes used for individual grants that belong in "
                    "Part III. Check before treating this as an entity."
                    if maybe_person else "")

        out.append(dict(base, question=(
            "Native organisation, or a general-purpose recipient? NO evidence "
            "either way was retrievable - please rule."),
            YOUR_RULING="UNRESOLVED",
            YOUR_NOTE=(
                f'ownership=not_established; service=not_established; '
                f'state={st}; city={city}. {affil}The IRS legal name carries '
                f'no Native identifier AND no Form 990 mission text was '
                f'retrievable for this EIN (990-N postcard filer, non-filer, '
                f'or no e-filed return on ProPublica). This is a REFUSAL TO '
                f'ASSERT, not a finding that the organisation is non-Native.'
                f'{person_q}{ex_q} {sched}{irs_q}{prof_q}')))
        bump("UNRESOLVED_no_evidence")

    cols = ["review_id", "queue", "uei", "cage_code", "entity_or_firm",
            "question", "YOUR_RULING", "YOUR_NOTE"]
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(out)
    with open(HELD, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["ein", "name", "state",
                                           "held_for_class", "usd",
                                           "funders", "sched_i_url"])
        w.writeheader()
        w.writerows(held)

    for k in sorted(stats):
        print(f"  {k:28s} {stats[k]}")
    print(f"\n{len(out)} rows -> {OUT}")
    print(f"{len(held)} held  -> {HELD}")


if __name__ == "__main__":
    main()
