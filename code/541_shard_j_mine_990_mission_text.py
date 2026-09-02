#!/usr/bin/env python3
"""541 - shard J. Mine the LOCAL IRS 990 XML corpus for WHY a nonprofit is in Cedar.

This is a READ of `data/raw/external/irs990_grantee|irs990_grantmakers|irs990_schedc`.
It downloads nothing and it writes nothing outside `data/staging/np_mission/`.

Why this script exists
----------------------
`data/clean/np_orgs.csv` carries 12,764 EINs whose *reason for being in Cedar*
is, for most rows, a name-token collision.  `docs/datasets/06_nonprofit.md`
records the cost: tier A leaks Umatilla Electric Co-op ($592M) and Yavapai
Community Hospital ($497M), and hundreds of tier-A rows sit unruled because
nothing cheaper than a human read existed to settle them.

An organisation's own Form 990 states its mission in its own words.  That text
is the cheapest available evidence for ADR-013's `inclusion_basis`, and it is
already on disk.

What it produces
----------------
    data/staging/np_mission/mission_text.jsonl     one row per np_orgs EIN with a local return
    data/staging/np_mission/inclusion_basis.jsonl  one row per EIN, the basis + the QUOTE
    data/staging/np_mission/mint_proposal.csv      ranked candidates, PROPOSAL ONLY
    data/staging/np_mission/corpus_inventory.json  what the local corpus actually holds

It does NOT mint, does NOT touch the spine, and does NOT edit `np_orgs.csv`.
Only Elijah's rulings promote (`docs/datasets/06_nonprofit.md`).

Never-fabricate rules honoured here
-----------------------------------
* Every basis carries a verbatim quote from the filing.  No quote, no basis.
* NTEE codes are never read.  06_nonprofit.md: weak signal, never for Native status.
* A name is never evidence.  The placename defect IS that error already made once.
* Single-token entity matches are guarded (`docs/NATIVE_ENTITY_NUANCES.md`,
  the Wichita Falls / Enterprise Rancheria rule): one common token is not
  distinctive, so a lone token may only win with independent Native context.
* "Indian" often means India; "Indigenous" is not AIAN.  Both are guarded.

Usage
-----
    py -3 code/541_shard_j_mine_990_mission_text.py            full pass
    py -3 code/541_shard_j_mine_990_mission_text.py --inventory-only
    py -3 code/541_shard_j_mine_990_mission_text.py --resolver-exposure
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "external"
CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine"
OUT = ROOT / "data" / "staging" / "np_mission"
REVIEW = ROOT / "review"

CORPUS_DIRS = ("irs990_grantee", "irs990_grantmakers", "irs990_schedc")
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2_000_000_000))


def log(msg: str) -> None:
    print(msg, flush=True)


# ---------------------------------------------------------------------------
# text normalisation
# ---------------------------------------------------------------------------

_PUNCT = re.compile(r"[^a-z0-9]+")
_WS = re.compile(r"\s+")


def norm(s: str) -> str:
    """Lowercase, strip every non-alphanumeric to a single space."""
    if not s:
        return ""
    # The apostrophe is DELETED, not spaced. Spacing it turns "St. Mary's" into
    # three tokens and lets a two-token name pass a three-token confidence test -
    # measured: PEORIA SYMPHONY ORCHESTRA keyed to St. Mary's (Algaaciq) off
    # "ST. MARY'S CATHEDRAL". It also protects ʻokina names (Papahanaumokuakea).
    s = s.replace("ʻ", "").replace("‘", "").replace("’", "").replace("'", "")
    toks = [t for t in _WS.sub(" ", _PUNCT.sub(" ", s.lower())).split()
            if len(t) > 1 or t.isdigit()]
    return " ".join(toks)


def clip(text: str, needle: str, width: int = 260) -> str:
    """Return a readable excerpt of `text` centred on `needle`.

    The quote is taken from the ORIGINAL filing text, never reconstructed.
    """
    if not text:
        return ""
    lo = text.lower()
    i = lo.find(needle.lower())
    if i < 0:
        return _WS.sub(" ", text[:width]).strip()
    a = max(0, i - width // 3)
    b = min(len(text), i + len(needle) + (2 * width) // 3)
    out = _WS.sub(" ", text[a:b]).strip()
    return ("..." if a > 0 else "") + out + ("..." if b < len(text) else "")


# ---------------------------------------------------------------------------
# vocabularies.  Every term below is a phrase found in filing text, not a code.
# ---------------------------------------------------------------------------

# "Indian" is only Native when it is one of these phrases.  Bare "indian"
# is left out on purpose: ST GEORGE INDIAN ORTHODOX CENTER is not Alaska.
INDIAN_PHRASES = (
    "american indian", "american indians", "indian tribe", "indian tribes",
    "indian country", "indian reservation", "indian reservations",
    "indian health", "indian child welfare", "indian education",
    "indian affairs", "indian community", "indian communities",
    "indian nation", "indian nations", "indian people", "indian peoples",
    "indian center", "indian centers", "indian housing", "indian gaming",
    "indian self determination", "indian students", "indian youth",
    "indian elders", "indian women", "indian families", "indian law",
    "indian art", "indian arts", "indian culture", "indian heritage",
    "urban indian", "indian boarding school", "indian territory",
)

NATIVE_PHRASES = (
    "alaska native", "alaska natives", "native american", "native americans",
    "native hawaiian", "native hawaiians", "native peoples", "native people",
    "native communities", "native community", "native youth",
    "native students", "native families", "native elders", "native women",
    "native artists", "native culture", "native language", "native languages",
    "native nations", "native village", "native villages", "native corporation",
    "first americans", "aian", "tribal", "tribes", "tribe", "tribally",
    "pueblo", "pueblos", "rancheria", "navajo nation", "indigenous",
    "iwi", "haudenosaunee", "anishinaabe", "dine college", "indian country",
)

# first-person community language.  "OUR culture", "OUR people" in an org whose
# own name carries a nation name is NOT settleable as a place-name coincidence -
# it may be the nation talking about itself.  It blocks a confident
# `placename_only`, and on its own it proves nothing either way.
FIRST_PERSON_COMMUNITY = (
    "our culture", "our people", "our community", "our communities",
    "our tribe", "our tribal", "our nation", "our members", "our heritage",
    "our language", "our ancestors", "our traditions", "our elders",
    "our youth", "our village", "our band", "our citizens",
)

# Guards.  These do NOT prove a negative on their own - they only strip the
# weakest signals ("indian", "indigenous") of their Native reading.
SOUTH_ASIA = (
    "india", "hindu", "punjabi", "gujarati", "telugu", "malayali", "malayalam",
    "tamil", "sikh", "kerala", "bengali", "marathi", "kannada", "hyderabad",
    "asian indian", "indian orthodox", "sindhi", "urdu", "gurdwara", "bharat",
    "ayurved", "east indian", "indo american", "indo-american",
)

NON_US_INDIGENOUS = (
    "first nation", "first nations", "british columbia", "saskatchewan",
    "manitoba", "guatemala", "oaxaca", "chiapas", "peru", "bolivia", "ecuador",
    "amazon", "aboriginal", "maori", "aotearoa", "sami", "adivasi",
    "papua", "torres strait",
)

PROGRAM_AUTHORITY = (
    "public law 93 638", "pl 93 638", "p l 93 638", "93 638",
    "indian self determination and education assistance",
    "indian self determination act", "isdeaa", "self governance compact",
    "638 contract", "638 contracts", "title v compact",
    "indian health service", "indian health care improvement act",
    "urban indian health program", "urban indian organization",
    "native american housing assistance and self determination",
    "nahasda", "indian housing block grant", "ihbg",
    "administration for native americans", "native american programs act",
    "indian child welfare act", "icwa",
    "bureau of indian affairs", "bureau of indian education",
    "tribally controlled schools act", "tribally controlled college",
    "tribally controlled community college", "tribal college",
    "johnson o malley", "johnson omalley",
    "indian education act", "title vii indian education",
    "indian gaming regulatory act", "national indian gaming commission",
    "indian reorganization act", "section 17 corporation",
    "tribal employment rights", "indian preference",
    "native american graves protection", "nagpra",
    "indian arts and crafts act", "indian trust", "treaty rights",
    "federally recognized tribe", "federally recognized tribes",
    "sovereign tribal nation", "government to government",
)

GEOGRAPHIC = (
    "indian reservation", "the reservation", "on the reservation",
    "reservation communities", "reservation community", "reservation residents",
    "off reservation", "on or near the reservation",
    "trust land", "trust lands", "tribal land", "tribal lands",
    "ancsa region", "alaska native village", "native village of",
    "rancheria", "pueblo of", "checkerboard", "indian lands",
    "tribal service area", "tribal jurisdiction", "aleutian", "yukon kuskokwim",
)

# affirmative Native CONTROL language - the closest a 990 gets to stating it
CONTROL_PHRASES = (
    "chartered by", "charter of", "an instrumentality of",
    "instrumentality of the", "wholly owned by", "owned by the",
    "established by the", "created by the", "a program of the",
    "arm of the", "governed by a board of tribal", "tribally chartered",
    "tribally controlled", "tribally owned", "tribally operated",
    "board of directors is composed of tribal",
    "section 17 corporation", "authorized by tribal resolution",
    "under the authority of the", "component unit of the",
)

SERVES_PHRASES = (
    "serving", "serves", "to serve", "provides services to",
    "in service to", "on behalf of", "for the benefit of", "benefiting",
)

BROAD_POPULATION = (
    "regardless of race", "general public", "all residents", "all people",
    "the community at large", "without regard to race", "all persons",
    "underserved populations", "low income individuals", "diverse populations",
    "minority populations", "people of all backgrounds", "anyone in need",
    "residents of the county", "residents of the region",
)

CIVIC_ACTIVITY = (
    "electric cooperative", "rural electric", "electric membership",
    "member owned utility", "telephone cooperative", "water district",
    "irrigation district", "school district", "chamber of commerce",
    "volunteer fire", "fire department", "fire protection district",
    "cemetery association", "rotary", "lions club", "kiwanis",
    "little league", "youth soccer", "booster club", "4 h", "grange",
    "soil and water conservation", "public library", "credit union",
    "homeowners association", "historical society", "humane society",
    "ambulance service", "emergency medical service", "county fair",
    "chamber orchestra", "senior citizens center", "food pantry",
    "acute care hospital", "critical access hospital", "medical center",
)

# proposed entity class, derived from the org's OWN words
CLASS_HINTS = (
    ("tribally controlled college", "Tribal College or University"),
    ("tribal college", "Tribal College or University"),
    ("community development financial institution", "Native Community Development Financial Institution"),
    ("cdfi", "Native Community Development Financial Institution"),
    ("native cdfi", "Native Community Development Financial Institution"),
    ("urban indian health", "Urban Indian Organization"),
    ("urban indian", "Urban Indian Organization"),
    ("intertribal", "Intertribal Organization"),
    ("inter tribal", "Intertribal Organization"),
    ("consortium of tribes", "Intertribal Organization"),
    ("tribal consortium", "Intertribal Organization"),
    ("native hawaiian", "Native Hawaiian Organization"),
    ("loan fund", "Native Financial Institution"),
)


# ---------------------------------------------------------------------------
# spine phrase index (named_entity matching)
# ---------------------------------------------------------------------------

GENERIC_TOKENS = {
    "tribe", "tribes", "tribal", "nation", "nations", "band", "bands",
    "indian", "indians", "of", "the", "and", "a", "an", "at", "in", "for",
    "community", "communities", "village", "villages", "native", "natives",
    "american", "alaska", "alaskan", "pueblo", "rancheria", "reservation",
    "colony", "group", "council", "corporation", "corp", "inc", "incorporated",
    "association", "organization", "organisation", "people", "peoples",
    "confederated", "consolidated", "united", "new", "north", "south", "east",
    "west", "upper", "lower", "big", "little", "great", "fort", "port",
    "school", "schools", "college", "center", "centre", "company", "llc",
    "government", "governing", "board", "authority", "agency", "district",
    "county", "city", "town", "township", "state", "federal", "national",
    "society", "institute", "foundation", "fund", "services", "service",
    "enterprise", "enterprises", "development", "resources", "resource",
    "creek", "river", "lake", "valley", "hill", "hills", "rock", "springs",
    "grand", "white", "black", "red", "blue", "green", "gray", "brown",
    "wells", "marsh", "muddy", "old", "young", "st", "saint", "santa", "san",
}

# tokens that are ALSO ordinary English words or common American place names.
# A lone one of these may never win a match (Enterprise Rancheria; the
# Wichita Falls rule; "Marsh Creek"; "Old Crow Rudy").
DANGEROUS_SOLO = {
    "enterprise", "eagle", "hope", "liberty", "union", "victory", "friendly",
    "independence", "franklin", "jackson", "lincoln", "madison", "monroe",
    "washington", "jefferson", "houston", "dallas", "phoenix", "sacramento",
    "columbia", "delaware", "kansas", "iowa", "utah", "dakota", "wichita",
    "peoria", "omaha", "miami", "seneca", "oneida", "erie", "huron",
    "yavapai", "umatilla", "tuscarawas", "muskogee", "cherokee", "creek",
    "seminole", "mohawk", "chippewa", "shawnee", "cheyenne", "kiowa",
    "pawnee", "ottawa", "kickapoo", "modoc", "ponca", "otoe", "sauk",
    "winnebago", "manhattan", "brooklyn", "chelsea", "clinton", "greenwich",
    "kayenta", "shiprock", "tucson", "yuma", "salinas", "napa", "sonoma",
    "chinook", "klamath", "malheur", "tillamook", "wallowa", "walla",
    "natchez", "biloxi", "mobile", "tampa", "sarasota", "ocala", "chattanooga",
    "roanoke", "shenandoah", "susquehanna", "allegheny", "monongahela",
    "potomac", "wabash", "sandusky", "toledo", "canton", "akron", "lima",
    "hiawatha", "pocahontas", "sequoia", "sequoyah", "tahoe", "shasta",
    "yosemite", "olympia", "spokane", "yakima", "cowlitz", "chehalis",
    "puyallup", "nisqually", "skagit", "okanogan", "wenatchee", "methow",
    # surnames and ordinary words the owner has already had to rule against -
    # "Old Crow Rudy", "Creek Ronald", "Wells Timothy Michael", and the
    # Robinson Rancheria / freight-brokerage collision ruled four times.
    "robinson", "augustine", "beaver", "wrangell", "holy", "cross", "marys",
    "simpson", "patrick", "avery", "chelsea", "crow", "ronald", "rudy",
    "mille", "lacs", "laguna", "rincon", "tulalip", "bridgeport",
}

# Ordinary English words that appear in the alias layer as if they were names.
# Measured 2026-09-01: `entity_aliases.csv` holds 104 alias_type='brand' rows,
# EVERY ONE of them a single token, and among them "advantage", "applied",
# "ancillary", "corporate", "cultural", "door", "feet", "field", "fire",
# "indigenous", "link", "managed", "media", "nexus", "peak", "program",
# "research". That is the Enterprise Rancheria defect living in the brand
# registry. Brand aliases are excluded from entity matching below; this set
# is the second line of defence for any other layer that grows the same shape.
COMMON_ENGLISH = {
    "advantage", "applied", "ancillary", "corporate", "cultural", "culture",
    "door", "feet", "field", "fire", "indigenous", "link", "managed", "media",
    "nexus", "peak", "program", "research", "productions", "consultants",
    "broadband", "remediations", "stampede", "protege", "portico", "strata",
    "abide", "avery", "jade", "simpson", "patrick", "colorado", "minnesota",
    "heritage", "legacy", "alliance", "partners", "solutions", "systems",
    "holdings", "ventures", "capital", "energy", "health", "housing",
    "education", "justice", "future", "unity", "circle", "bridge", "summit",
    "horizon", "pathways", "beacon", "harvest", "gathering", "council",
}


def load_spine_phrases():
    """canonical + alias names -> phrase index keyed on the rarest token."""
    phrases = {}

    def add(name, uid, canonical, klass, src):
        n = norm(name)
        if not n or len(n) < 4:
            return
        toks = n.split()
        distinct = [t for t in toks
                    if t not in GENERIC_TOKENS and len(t) >= 4]
        if not distinct:
            return
        prev = phrases.get(n)
        if prev is None or (not prev["cedar_uid"] and uid):
            phrases[n] = {
                "phrase": n, "cedar_uid": uid or "", "canonical": canonical,
                "entity_class": klass, "source": src,
                "n_tokens": len(toks), "distinct": distinct,
            }

    reg = SPINE / "cedar_identity_register.csv"
    with reg.open(encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        need = {"cedar_uid", "canonical_name", "entity_class"}
        if not need.issubset(set(rd.fieldnames or [])):
            raise SystemExit(f"{reg} is missing one of {sorted(need)} - refusing "
                             f"to guess; found {rd.fieldnames}")
        n_reg = 0
        for r in rd:
            n_reg += 1
            add(r["canonical_name"], r["cedar_uid"], r["canonical_name"],
                r["entity_class"], "register_canonical")
            for fn in (r.get("former_names") or "").split(";"):
                if fn.strip():
                    add(fn, r["cedar_uid"], r["canonical_name"],
                        r["entity_class"], "register_former_name")

    ali = CLEAN / "entity_aliases.csv"
    uid_class = {p["cedar_uid"]: p["entity_class"] for p in phrases.values()
                 if p["cedar_uid"]}
    n_ali = 0
    brand_dropped = []
    with ali.open(encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        if "alias_name" not in (rd.fieldnames or []):
            raise SystemExit(f"{ali} has no alias_name column: {rd.fieldnames}")
        for r in rd:
            n_ali += 1
            uid = (r.get("cedar_uid") or "").strip()
            if (r.get("alias_type") or "").strip() == "brand":
                # A brand word is not an entity name (NATIVE_ENTITY_NUANCES:
                # "a tribal name inside an enterprise name is a BRAND, not an
                # owner"). Named here so the drop is a task, not a count.
                brand_dropped.append(
                    f"{r['alias_name']} -> {r.get('entity_id') or uid}")
                continue
            add(r["alias_name"], uid, r.get("alias_name", ""),
                uid_class.get(uid, ""), "alias")

    index = defaultdict(list)
    for p in phrases.values():
        key = min(p["distinct"], key=lambda t: (len(t), t))
        index[key].append(p)
    log(f"  spine phrase index: {n_reg:,} register rows + {n_ali:,} alias rows "
        f"-> {len(phrases):,} distinct phrases over {len(index):,} keys")
    log(f"  brand aliases refused as entity names ({len(brand_dropped)}), e.g.: "
        + "; ".join(sorted(brand_dropped)[:6]))
    return index, brand_dropped


# ---------------------------------------------------------------------------
# corpus index
# ---------------------------------------------------------------------------

def load_corpus_index():
    """object_id -> return metadata, for every XML actually present on disk."""
    on_disk = {}
    for d in CORPUS_DIRS:
        xdir = RAW / d / "xml"
        if not xdir.is_dir():
            raise SystemExit(f"expected local corpus at {xdir} - not found")
        for fn in os.listdir(xdir):
            if fn.endswith(".xml"):
                on_disk.setdefault(fn[:-4], xdir / fn)

    by_ein = defaultdict(list)
    index_rows = 0
    unindexed = dict(on_disk)
    for d in CORPUS_DIRS:
        tgt = RAW / d / "_index_targets.csv"
        with tgt.open(encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                index_rows += 1
                oid = (r.get("object_id") or "").strip()
                path = on_disk.get(oid)
                if path is None:
                    continue
                unindexed.pop(oid, None)
                by_ein[(r.get("ein") or "").strip().zfill(9)].append({
                    "object_id": oid,
                    "tax_period": (r.get("tax_period") or "").strip(),
                    "return_type": (r.get("return_type") or "").strip(),
                    "taxpayer_name": (r.get("taxpayer_name") or "").strip(),
                    "corpus_dir": d,
                    "path": path,
                })
    return on_disk, by_ein, index_rows, unindexed


# ---------------------------------------------------------------------------
# XML extraction
# ---------------------------------------------------------------------------

PROG_DESC_PARENTS = {
    "IRS990", "ProgSrvcAccomActy2Grp", "ProgSrvcAccomActy3Grp",
    "ProgSrvcAccomActyOtherGrp", "ProgramSrvcAccomplishmentGrp",
}

MONEY_TAGS = {
    "CYTotalRevenueAmt": "total_revenue",
    "TotalRevenueAmt": "total_revenue",
    "CYTotalExpensesAmt": "total_expenses",
    "TotalExpensesAmt": "total_expenses",
    "TotalAssetsEOYAmt": "total_assets_eoy",
    "TotalEmployeeCnt": "employee_cnt",
    "TotalVolunteersCnt": "volunteer_cnt",
}

# Schedule C carries the SAME quantity under two different shapes, and reading
# only one of them reports $0 for half the filers:
#   501(h) electing filers -> Part II-A, a <...Grp> wrapping FilingOrganizationsTotalAmt
#   non-electing filers    -> Part II-B, a flat <...Amt>
SCHEDC_GRP_AMOUNTS = (
    "TotalLobbyingExpendGrp", "TotalGrassrootsLobbyingGrp",
    "TotalDirectLobbyingGrp", "TotalExemptPurposeExpendGrp",
    "LobbyingNontaxableAmountGrp", "GrassrootsNontaxableGrp",
)
SCHEDC_FLAT_AMOUNTS = (
    "TotalLobbyingExpendituresAmt", "PoliticalExpendituresAmt",
    "LobbyingCeilingAmt", "GrassrootsCeilingAmt",
    "DuesNondeductibleLobbyPltclAmt", "TotalDuesAssessmentsAmt",
)


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


SCHEDC_ACTIVITY_INDS = (
    "VolunteersInd", "PaidStaffOrManagementInd", "MediaAdvertisementsInd",
    "MailingsMembersInd", "PublicationsOrBroadcastInd",
    "GrantsOtherOrganizationsInd", "DirectContactLegislatorsInd",
    "RalliesDemonstrationsInd", "OtherActivitiesInd",
)


def read_schedule_c(sc_el, out: dict) -> None:
    """Read Part I/II/III from the Schedule C subtree ONLY.

    ExplanationTxt is read here and not from the whole return: the same tag
    carries Schedule O narrative everywhere else in a 990, and scooping it up
    would report general supplemental text as lobbying disclosure.
    """
    for el in sc_el.iter():
        t = local(el.tag)
        txt = (el.text or "").strip()
        if t in SCHEDC_GRP_AMOUNTS:
            for c in el:
                if local(c.tag) == "FilingOrganizationsTotalAmt" and (c.text or "").strip():
                    out["schedc_amounts"][t] = c.text.strip()
                    break
        elif t in SCHEDC_FLAT_AMOUNTS and txt:
            out["schedc_amounts"].setdefault(t, txt)
        elif t in SCHEDC_ACTIVITY_INDS and txt in ("X", "true", "1"):
            out["schedc_activity_flags"].append(t[:-3])
        elif t == "ExplanationTxt" and len(txt) > 40:
            out["schedc_explanations"].append(txt)
        elif t == "FormAndLineReferenceDesc" and txt:
            out["schedc_line_refs"].append(txt)


def parse_return(path: Path) -> dict | None:
    try:
        root = ET.parse(str(path)).getroot()
    except ET.ParseError as exc:
        return {"_parse_error": f"{path.name}: {exc}"}

    out = {
        "filer_ein": "", "filer_name": "", "tax_year": "",
        "tax_period_end": "", "return_type": "",
        "mission_desc": "", "activity_desc": "", "primary_exempt_purpose": "",
        "program_descs": [],
        "schedc_present": 0, "schedc_amounts": {}, "schedc_activity_flags": [],
        "schedc_explanations": [], "schedc_line_refs": [],
        "schedi_org_grants": 0, "schedi_grant_purposes": 0,
        "schedi_recipient_eins": 0,
        "officer_cnt": 0, "website": "",
        "money": {},
    }

    for el in root.iter():
        t = local(el.tag)
        txt = (el.text or "").strip()

        if t == "Filer":
            # The FIRST <EIN> and <BusinessNameLine1Txt> in a return belong to
            # the PREPARER FIRM, not the filer. Taking them in document order
            # put MOSS ADAMS LLP, RSM US LLP and BAKER TILLY at the top of the
            # Schedule C lobbying table. Read the Filer block explicitly.
            for c in el.iter():
                ct = local(c.tag)
                cx = (c.text or "").strip()
                if ct == "EIN" and cx and not out["filer_ein"]:
                    out["filer_ein"] = cx.zfill(9)
                elif ct == "BusinessNameLine1Txt" and cx and not out["filer_name"]:
                    out["filer_name"] = cx
        elif t == "TaxYr" and not out["tax_year"]:
            out["tax_year"] = txt
        elif t == "TaxPeriodEndDt" and not out["tax_period_end"]:
            out["tax_period_end"] = txt
        elif t == "ReturnTypeCd" and not out["return_type"]:
            out["return_type"] = txt
        elif t == "WebsiteAddressTxt" and not out["website"]:
            out["website"] = txt
        elif t == "MissionDesc" and txt and len(txt) > len(out["mission_desc"]):
            out["mission_desc"] = txt
        elif t == "ActivityOrMissionDesc" and txt:
            if len(txt) > len(out["activity_desc"]):
                out["activity_desc"] = txt
        elif t in ("PrimaryExemptPurposeTxt", "PrimaryActivitiesTxt") and txt:
            if len(txt) > len(out["primary_exempt_purpose"]):
                out["primary_exempt_purpose"] = txt
        elif t == "DescriptionProgramSrvcAccomTxt" and txt:
            out["program_descs"].append(txt)
        elif t == "IRS990ScheduleC":
            out["schedc_present"] = 1
            read_schedule_c(el, out)
        elif t in ("RecipientTable", "GrantsOtherAsstToDomesticOrgGrp",
                   "RecipientEIN"):
            if t == "RecipientEIN":
                out["schedi_recipient_eins"] += 1
            else:
                out["schedi_org_grants"] += 1
        elif t in ("PurposeOfGrantTxt", "GrantOrContributionPurposeTxt"):
            if txt:
                out["schedi_grant_purposes"] += 1
        elif t == "PersonNm":
            out["officer_cnt"] += 1
        elif t in MONEY_TAGS and txt:
            out["money"].setdefault(MONEY_TAGS[t], txt)

        if t in PROG_DESC_PARENTS:
            for c in el:
                if local(c.tag) == "Desc" and (c.text or "").strip():
                    out["program_descs"].append(c.text.strip())

    seen, uniq = set(), []
    for d in out["program_descs"]:
        k = d[:200]
        if k not in seen:
            seen.add(k)
            uniq.append(d)
    out["program_descs"] = uniq
    return out


# ---------------------------------------------------------------------------
# classification
# ---------------------------------------------------------------------------

def match_named_entities(blob_norm, blob_raw, index, native_context):
    """Phrase-match against the spine.  Guarded per NATIVE_ENTITY_NUANCES."""
    toks = set(blob_norm.split())
    seen, results = set(), []
    for tok in toks:
        for p in index.get(tok, ()):
            if p["phrase"] in seen:
                continue
            if p["phrase"] not in blob_norm:
                continue
            # "Solo" is counted on DISTINCTIVE tokens, never on total tokens.
            # Measured: "Fond du Lac" is three tokens but only ONE distinctive
            # one ("du"/"lac" are too short to distinguish anything), and it
            # keyed the Fond du Lac Yacht Club, Rotary, County Farm Bureau,
            # High School Hockey and eleven more Wisconsin civic bodies to the
            # Minnesota Ojibwe band. Counting total tokens let a one-token name
            # skip the one-token guard - the Tuscarawas rule with a longer name.
            solo = len(p["distinct"]) == 1
            if solo:
                d = p["distinct"][0]
                if (d in DANGEROUS_SOLO or d in COMMON_ENGLISH
                        or len(d) < 6 or not native_context):
                    continue
                conf = "medium"
            else:
                conf = "high" if p["n_tokens"] >= 3 else "medium"
            seen.add(p["phrase"])
            results.append({
                "phrase": p["phrase"],
                "matched_entity_name": p["canonical"],
                "candidate_cedar_uid": p["cedar_uid"],
                "matched_entity_class": p["entity_class"],
                "match_source": p["source"],
                "match_confidence": conf,
                # quote on the longest distinctive token: the full phrase often
                # will not `find` in the raw text, which carries the punctuation
                # normalisation removed.
                "quote": clip(blob_raw, max(p["distinct"], key=len)),
            })
    results.sort(key=lambda r: (r["match_confidence"] != "high",
                                -len(r["phrase"])))
    return results


def relation_to_entity(blob_norm: str, phrase: str) -> str:
    """Does the org say it IS the entity's, or that it SERVES the entity?"""
    i = blob_norm.find(phrase)
    if i < 0:
        return "mentions"
    window = blob_norm[max(0, i - 90):i]
    for c in CONTROL_PHRASES:
        if c in window:
            return "self"
    for s in SERVES_PHRASES:
        if s in window:
            return "serves"
    return "mentions"


def classify(rec, np_row, index):
    """Assign ONE primary inclusion_basis plus every supporting basis found."""
    parts = [rec["mission_desc"], rec["activity_desc"],
             rec["primary_exempt_purpose"]] + rec["program_descs"]
    blob_raw = "  ".join(p for p in parts if p)
    bn = norm(blob_raw)

    indian_hits = [(t, clip(blob_raw, t)) for t in INDIAN_PHRASES if t in bn]
    native_hits = [(t, clip(blob_raw, t)) for t in NATIVE_PHRASES if t in bn]
    south_asia = [t for t in SOUTH_ASIA if t in bn]
    non_us = [t for t in NON_US_INDIGENOUS if t in bn]

    # "indigenous" alone, with a non-US marker and nothing else, is not AIAN
    strong_native = [h for h in native_hits if h[0] != "indigenous"]
    if south_asia and not strong_native:
        indian_hits = []
    if non_us and not strong_native and not indian_hits:
        native_hits = [h for h in native_hits if h[0] != "indigenous"]

    native_context = bool(indian_hits or native_hits)

    prog_hits = [(t, clip(blob_raw, t)) for t in PROGRAM_AUTHORITY if t in bn]
    geo_hits = [(t, clip(blob_raw, t)) for t in GEOGRAPHIC if t in bn]
    broad_hits = [(t, clip(blob_raw, t)) for t in BROAD_POPULATION if t in bn]
    civic_hits = [(t, clip(blob_raw, t)) for t in CIVIC_ACTIVITY if t in bn]

    ents = match_named_entities(bn, blob_raw, index, native_context) if bn else []

    # Is the matched entity the FILER ITSELF? Then this is not a mint - the
    # organisation is already in the register and only its EIN is missing.
    # Substring containment is NOT identity: "MILLE LACS RAIDERS WRESTLING CLUB"
    # contains "mille lacs". The test is that the org name adds no distinctive
    # word of its own beyond the entity's name.
    org_norm = norm(np_row.get("org_name") or "")
    org_distinct = {t for t in org_norm.split()
                    if t not in GENERIC_TOKENS and len(t) >= 3}
    for e in ents:
        ph_toks = set(e["phrase"].split())
        e["self_match"] = bool(org_norm) and (
            org_norm == e["phrase"] or (bool(org_distinct)
                                        and org_distinct <= ph_toks))

    bases = {}
    if ents:
        e = ents[0]
        bases["named_entity"] = dict(e, entity_relation=relation_to_entity(bn, e["phrase"]))
    if prog_hits:
        bases["program_authority"] = {
            "matched_entity_name": "", "candidate_cedar_uid": "",
            "match_confidence": "high" if len(prog_hits) > 1 else "medium",
            "quote": prog_hits[0][1], "terms": [t for t, _ in prog_hits][:6]}
    if geo_hits:
        bases["geographic"] = {
            "matched_entity_name": "", "candidate_cedar_uid": "",
            "match_confidence": "medium",
            "quote": geo_hits[0][1], "terms": [t for t, _ in geo_hits][:6]}
    if native_context:
        first = (indian_hits or native_hits)[0]
        bases["subject_classification"] = {
            "matched_entity_name": "", "candidate_cedar_uid": "",
            "match_confidence": "high" if len(indian_hits) + len(strong_native) > 1
                                else "medium",
            "quote": first[1],
            "terms": [t for t, _ in (indian_hits + native_hits)][:6]}

    # native-serving-not-native-controlled: Native named among a broad
    # population, with NO control language anywhere in the filing.
    control = [c for c in CONTROL_PHRASES if c in bn]
    n_native_mentions = len(indian_hits) + len(strong_native)
    if native_context and broad_hits and not control and n_native_mentions <= 2:
        bases["native_serving_not_native_controlled"] = {
            "matched_entity_name": "", "candidate_cedar_uid": "",
            "match_confidence": "low",
            "quote": broad_hits[0][1],
            "terms": [t for t, _ in broad_hits][:4]}

    # placename explanation, from np_orgs' OWN flags - never from the name text
    placename_explained = bool(
        (np_row.get("review_flag") or "").strip() == "civic_or_place_descriptor_in_name"
        or (np_row.get("placename_risk_flag") or "").strip() in ("HIGH", "REVIEW")
        or (np_row.get("canonical_name_token_match") or "").strip())

    first_person = [t for t in FIRST_PERSON_COMMUNITY if t in bn]

    if not native_context and not prog_hits and not geo_hits:
        if bn and placename_explained:
            # Three bands, because they are three different amounts of evidence.
            #   high   - the filing states a plainly non-Native purpose
            #   medium - no Native word anywhere, no civic marker either
            #   low    - the filing speaks of "our culture / our people", so the
            #            org may BE the nation talking about itself. Not settleable.
            if first_person:
                conf, q = "low", clip(blob_raw, first_person[0])
                terms = first_person[:4]
            elif civic_hits:
                conf, q = "high", civic_hits[0][1]
                terms = [t for t, _ in civic_hits][:4]
            else:
                conf, q = "medium", clip(blob_raw, blob_raw[:1])
                terms = []
            bases["placename_only"] = {
                "matched_entity_name": (np_row.get("canonical_name_token_match") or ""),
                "candidate_cedar_uid": "", "match_confidence": conf,
                "quote": q, "terms": terms}
        elif bn:
            bases["no_native_signal"] = {
                "matched_entity_name": "", "candidate_cedar_uid": "",
                "match_confidence": "medium",
                "quote": clip(blob_raw, blob_raw[:1]), "terms": []}

    # native_serving sits ABOVE subject_classification because it is the more
    # specific claim: it requires the Native term AND an explicit broad-
    # population statement AND no control language. Below it, it could never
    # win - every native_serving row also satisfies subject_classification.
    order = ("named_entity", "program_authority", "geographic",
             "native_serving_not_native_controlled", "subject_classification",
             "placename_only", "no_native_signal")
    primary = next((b for b in order if b in bases), "no_mission_text")
    if primary == "no_mission_text":
        bases["no_mission_text"] = {
            "matched_entity_name": "", "candidate_cedar_uid": "",
            "match_confidence": "none",
            "quote": "", "terms": []}

    # a named entity that the org only SERVES is not a claim that the org is it
    if primary == "named_entity" and \
            bases["named_entity"]["entity_relation"] == "serves" and \
            "native_serving_not_native_controlled" in bases:
        primary = "native_serving_not_native_controlled"

    # NOTE for whoever reads this tier: a Form 990 does not disclose who
    # CONTROLS the filer. `native_serving_not_native_controlled` is therefore
    # only ever assigned on affirmative evidence of a broad non-Native
    # constituency stated in the filing itself, never inferred from silence.
    # Absence of this basis is NOT evidence that an org is Native-controlled.

    return primary, bases, ents, blob_raw, {
        "n_indian_phrases": len(indian_hits), "n_native_phrases": len(native_hits),
        "n_program_authority": len(prog_hits), "n_geographic": len(geo_hits),
        "n_control_phrases": len(control), "n_civic_activity": len(civic_hits),
        "south_asia_guard": south_asia[:3], "non_us_guard": non_us[:3],
        "placename_explained": placename_explained,
        "first_person_community": first_person[:3],
    }


def propose_class(blob_norm: str, matched_class: str) -> str:
    for term, klass in CLASS_HINTS:
        if term in blob_norm:
            return klass
    if matched_class in ("Federally recognized tribe",
                         "Federally recognized Alaska Native Village",
                         "State-recognized tribe"):
        return "Tribal nonprofit (no register class exists yet)"
    return "Native nonprofit (no register class exists yet)"


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# resolver exposure - the mission text as an INDEPENDENT test of 503.resolve()
# ---------------------------------------------------------------------------

def resolver_exposure() -> int:
    """Cross `503.resolve()` against what each filer says it does.

    Why this is worth measuring separately. `503`'s loose path wins on
    "the spine entity's distinctive tokens are a subset of the filed name",
    and its two guards (`ADMIN_GEOGRAPHY`, `CIVIC_FORM`) are DENYLISTS of
    words - COUNTY, YACHT, ROTARY, GOLF. A denylist can only refuse a civic
    form somebody has already thought of. `FOND DU LAC YACHT CLUB` is caught;
    `ENVISION GREATER FOND DU LAC`, `FOND DU LAC FESTIVALS` and
    `FOND DU LAC ADULT LITERACY SERVICES` are not, because no word in them is
    on either list.

    The mission text is the ORTHOGONAL test, and it is positive rather than
    negative: instead of asking whether the filed NAME looks civic, it asks
    what the organisation says it does. A 990 that reads "we are a volunteer
    fire company" contradicts a resolution to a tribe no matter which words
    the name happens to contain.

    This function READS `503_identity.py` and calls `resolve()`. It writes
    nothing to it, never runs `--apply`, and writes only into
    `data/staging/np_mission/`.
    """
    import importlib.util

    log("== 541 --resolver-exposure ==")
    src = ROOT / "code" / "503_identity.py"
    spec = importlib.util.spec_from_file_location("cedar_id503", src)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load {src}")
    m = importlib.util.module_from_spec(spec)
    sys.modules["cedar_id503"] = m
    spec.loader.exec_module(m)
    exact, gov, state_of = m.build_index()
    log(f"  503 index: {len(exact):,} exact keys, {len(gov):,} gov-class entities")

    bpath = OUT / "inclusion_basis.jsonl"
    if not bpath.exists():
        raise SystemExit(f"{bpath} not found - run the full pass first")
    basis = {}
    with bpath.open(encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            basis[r["ein"]] = r

    with (CLEAN / "np_orgs.csv").open(encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        for req in ("EIN", "org_name", "state"):
            if req not in (rd.fieldnames or []):
                raise SystemExit(f"np_orgs.csv has no {req!r} column")
        np_rows = list(rd)

    cross = Counter()
    rows = []
    for r in np_rows:
        ein = (r["EIN"] or "").strip().replace("-", "").zfill(9)
        b = basis.get(ein)
        if b is None:
            continue
        tid, why = m.resolve(r["org_name"], exact, gov, state_of,
                             r.get("state", ""))
        cross[(b["inclusion_basis"], tid is not None)] += 1
        if tid is None:
            continue
        agree = "n/a"
        if b["inclusion_basis"] == "named_entity" and b["candidate_cedar_uid"]:
            agree = "mission_names_an_entity_too"
        verdict = "REVIEW"
        if b["inclusion_basis"] == "placename_only" and                 b["match_confidence"] == "high":
            verdict = "CONTRADICTED_BY_FILING"
        rows.append({
            "ein": ein,
            "org_name": r["org_name"],
            "resolver_entity_id": tid,
            "resolver_basis": why,
            "mission_inclusion_basis": b["inclusion_basis"],
            "mission_match_confidence": b["match_confidence"],
            "mission_names_entity": b["matched_entity_name"],
            "mission_agreement": agree,
            "verdict": verdict,
            "civic_purpose_term": "|".join(b.get("supporting_terms") or []),
            "quote_from_filing": b["quote"],
            "source_file": b["source_file"],
            "evidence_basis": ("IRS Form 990 mission/program text as filed; "
                               "503.resolve() called read-only"),
            "built_date": TODAY,
        })

    rows.sort(key=lambda x: (x["verdict"] != "CONTRADICTED_BY_FILING",
                             x["resolver_entity_id"], x["org_name"]))
    out = OUT / "resolver_exposure.csv"
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else
                           ["ein", "org_name", "verdict"])
        w.writeheader()
        w.writerows(rows)

    hard = [x for x in rows if x["verdict"] == "CONTRADICTED_BY_FILING"]
    ents = Counter(x["resolver_entity_id"] for x in hard)
    log(f"  wrote {out.name}: {len(rows):,} orgs that 503 keys and that have "
        f"a local 990")
    log("  --- 503 keys it x what the filing says ---")
    for (b, keyed), n in sorted(cross.items()):
        log(f"    {b:42s} keyed={str(keyed):5s} {n:6,}")
    log(f"  CONTRADICTED BY THE FILING: {len(hard)} orgs over {len(ents)} "
        f"spine entities")
    for tid, n in ents.most_common(12):
        log(f"    {n:3d}  {tid}")
    for x in hard[:8]:
        log(f"    {x['org_name'][:46]:46s} -> {x['resolver_entity_id']}  "
            f"[{x['civic_purpose_term']}]")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inventory-only", action="store_true",
                    help="measure the corpus and stop; write no jsonl")
    ap.add_argument("--resolver-exposure", action="store_true",
                    help="cross the mission-text evidence against 503.resolve() "
                         "and write resolver_exposure.csv; reads 503, never "
                         "writes to it and never runs --apply")
    args = ap.parse_args()

    if args.resolver_exposure:
        return resolver_exposure()

    OUT.mkdir(parents=True, exist_ok=True)

    log("== 541 shard J - mining the LOCAL 990 corpus ==")
    log(f"   root {ROOT}")

    on_disk, by_ein, index_rows, unindexed = load_corpus_index()
    log(f"  XML on disk (distinct object_id): {len(on_disk):,}")
    log(f"  index rows across {len(CORPUS_DIRS)} dirs: {index_rows:,}")
    log(f"  EINs with >=1 local return: {len(by_ein):,}")
    if unindexed:
        log(f"  XML present but named by NO index row ({len(unindexed)}): "
            + ", ".join(sorted(unindexed)[:5]))

    np_path = CLEAN / "np_orgs.csv"
    with np_path.open(encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        np_cols = set(rd.fieldnames or [])
        for req in ("EIN", "org_name", "tier", "confidence_tier",
                    "classification_ruling", "review_flag",
                    "placename_risk_flag", "canonical_name_token_match"):
            if req not in np_cols:
                raise SystemExit(f"np_orgs.csv has no column {req!r} - refusing "
                                 f"to classify against a schema I cannot read")
        np_rows = list(rd)
    np_by_ein = {}
    for r in np_rows:
        np_by_ein[(r["EIN"] or "").strip().replace("-", "").zfill(9)] = r
    log(f"  np_orgs.csv: {len(np_rows):,} rows, {len(np_by_ein):,} distinct EIN")

    targets = sorted(set(np_by_ein) & set(by_ein))
    log(f"  np_orgs EINs with a local return: {len(targets):,}")

    filing = {e for e, r in np_by_ein.items()
              if (r.get("tier") or "").strip() in ("full_990", "990_EZ")}
    log(f"  np_orgs EINs whose BMF tier is full_990/990_EZ: {len(filing):,} "
        f"({len(filing & set(by_ein)):,} of them have a local return)")

    inventory = {
        "measured": TODAY,
        "xml_files_on_disk": sum(
            len([f for f in os.listdir(RAW / d / "xml") if f.endswith(".xml")])
            for d in CORPUS_DIRS),
        "xml_distinct_object_id": len(on_disk),
        "index_rows": index_rows,
        "index_eins_with_local_xml": len(by_ein),
        "np_orgs_rows": len(np_rows),
        "np_orgs_distinct_ein": len(np_by_ein),
        "np_orgs_ein_with_local_return": len(targets),
        "np_orgs_tier_full990_or_ez": len(filing),
        "np_orgs_tier_full990_or_ez_with_local_return": len(filing & set(by_ein)),
        "xml_not_named_by_any_index_row": len(unindexed),
        "by_corpus_dir": {},
    }
    for d in CORPUS_DIRS:
        inventory["by_corpus_dir"][d] = len(
            [f for f in os.listdir(RAW / d / "xml") if f.endswith(".xml")])

    if args.inventory_only:
        (OUT / "corpus_inventory.json").write_text(
            json.dumps(inventory, indent=2), encoding="utf-8")
        log(json.dumps(inventory, indent=2))
        return 0

    index, brand_dropped = load_spine_phrases()
    inventory["brand_aliases_refused_as_entity_names"] = len(brand_dropped)

    # ------------------------------------------------------------------
    # pass 1 - extract mission text for the np_orgs EINs
    # ------------------------------------------------------------------
    log("  pass 1: extracting mission text ...")
    mission_rows = []
    parse_errors = []
    no_text = []
    for i, ein in enumerate(targets, 1):
        if i % 500 == 0:
            log(f"    {i:,}/{len(targets):,}")
        rets = sorted(by_ein[ein], key=lambda r: r["tax_period"], reverse=True)
        chosen, rec = None, None
        for cand in rets:
            got = parse_return(cand["path"])
            if got and got.get("_parse_error"):
                parse_errors.append(got["_parse_error"])
                continue
            if got is None:
                continue
            has_text = bool(got["mission_desc"] or got["activity_desc"]
                            or got["primary_exempt_purpose"] or got["program_descs"])
            if chosen is None:
                chosen, rec = cand, got
            if has_text:
                chosen, rec = cand, got
                break
        if rec is None:
            no_text.append(f"{ein} ({np_by_ein[ein]['org_name']}) all "
                           f"{len(rets)} local returns failed to parse")
            continue
        row = {
            "ein": ein,
            "org_name": np_by_ein[ein]["org_name"],
            "filer_name_as_filed": rec["filer_name"],
            "tax_period": chosen["tax_period"],
            "tax_period_end": rec["tax_period_end"],
            "return_type": rec["return_type"] or chosen["return_type"],
            "object_id": chosen["object_id"],
            "source_file": str(chosen["path"].relative_to(ROOT)).replace("\\", "/"),
            "corpus_dir": chosen["corpus_dir"],
            "mission_desc": rec["mission_desc"],
            "activity_desc": rec["activity_desc"],
            "primary_exempt_purpose": rec["primary_exempt_purpose"],
            "program_descs": rec["program_descs"],
            "n_periods_available": len(rets),
            "tax_periods_available": sorted({r["tax_period"] for r in rets}),
            "website_as_filed": rec["website"],
            "schedc_present": rec["schedc_present"],
            "schedi_org_grant_blocks": rec["schedi_org_grants"],
        }
        if not (row["mission_desc"] or row["activity_desc"]
                or row["primary_exempt_purpose"] or row["program_descs"]):
            no_text.append(f"{ein} ({row['org_name']}) filed "
                           f"{row['return_type']} {row['tax_period']} with no "
                           f"mission/activity/program text")
        mission_rows.append(row)

    with (OUT / "mission_text.jsonl").open("w", encoding="utf-8") as fh:
        for r in mission_rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    log(f"  wrote mission_text.jsonl: {len(mission_rows):,} EINs")
    if parse_errors:
        log(f"  XML that would not parse ({len(parse_errors)}): "
            + "; ".join(parse_errors[:5]))
    if no_text:
        log(f"  EINs whose most recent local return carries NO mission text "
            f"({len(no_text)}), e.g.: " + "; ".join(no_text[:3]))

    # ------------------------------------------------------------------
    # pass 2 - classify the reason
    # ------------------------------------------------------------------
    log("  pass 2: classifying inclusion_basis ...")
    basis_rows = []
    hist = Counter()
    for row in mission_rows:
        npr = np_by_ein[row["ein"]]
        rec = {"mission_desc": row["mission_desc"],
               "activity_desc": row["activity_desc"],
               "primary_exempt_purpose": row["primary_exempt_purpose"],
               "program_descs": row["program_descs"]}
        primary, bases, ents, blob_raw, sig = classify(rec, npr, index)
        hist[primary] += 1
        b = bases[primary]
        basis_rows.append({
            "ein": row["ein"],
            "org_name": row["org_name"],
            "inclusion_basis": primary,
            "matched_entity_name": b.get("matched_entity_name", ""),
            "candidate_cedar_uid": b.get("candidate_cedar_uid", ""),
            "matched_entity_class": b.get("matched_entity_class", ""),
            "entity_relation": b.get("entity_relation", ""),
            "entity_is_the_filer_itself": bool(b.get("self_match")),
            "match_confidence": b.get("match_confidence", ""),
            "quote": b.get("quote", ""),
            "source_file": row["source_file"],
            "tax_period": row["tax_period"],
            "n_signals": len([k for k in bases
                              if k not in ("no_native_signal", "no_mission_text")]),
            "all_bases": sorted(k for k in bases
                                if k not in ("no_native_signal", "no_mission_text")),
            "supporting_terms": b.get("terms", []),
            "other_entity_matches": [
                {"name": e["matched_entity_name"],
                 "cedar_uid": e["candidate_cedar_uid"],
                 "confidence": e["match_confidence"]} for e in ents[1:4]],
            "np_tier": npr.get("tier", ""),
            "np_confidence_tier": npr.get("confidence_tier", ""),
            "np_classification_ruling": npr.get("classification_ruling", ""),
            "np_review_flag": npr.get("review_flag", ""),
            "np_placename_risk_flag": npr.get("placename_risk_flag", ""),
            "n_periods_available": row["n_periods_available"],
            "signals": sig,
            "built_date": TODAY,
        })

    with (OUT / "inclusion_basis.jsonl").open("w", encoding="utf-8") as fh:
        for r in basis_rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    log(f"  wrote inclusion_basis.jsonl: {len(basis_rows):,} EINs")
    log("  --- inclusion_basis histogram ---")
    for k, v in hist.most_common():
        log(f"    {k:42s} {v:6,}")

    # tier-A cohort
    tierA_unruled = {e for e, r in np_by_ein.items()
                     if (r.get("confidence_tier") or "").strip() == "A"
                     and (r.get("classification_ruling") or "").strip() == "UNRULED"}
    byein_basis = {r["ein"]: r for r in basis_rows}
    settled = {e: byein_basis[e] for e in tierA_unruled if e in byein_basis}
    tierA_hist = Counter(v["inclusion_basis"] for v in settled.values())
    log(f"  --- tier-A UNRULED cohort: {len(tierA_unruled):,}; "
        f"{len(settled):,} have local mission text ---")
    for k, v in tierA_hist.most_common():
        log(f"    {k:42s} {v:6,}")

    # ------------------------------------------------------------------
    # pass 3 - mint PROPOSAL (never a mint)
    # ------------------------------------------------------------------
    rank = {"named_entity": 0, "program_authority": 1, "geographic": 2,
            "subject_classification": 3}
    conf_rank = {"high": 0, "medium": 1, "low": 2, "none": 3}
    cands = [r for r in basis_rows if r["inclusion_basis"] in rank]
    cands.sort(key=lambda r: (rank[r["inclusion_basis"]],
                              conf_rank.get(r["match_confidence"], 9),
                              -r["n_signals"], r["org_name"]))

    fields = ["rank", "ein", "org_name", "proposed_action",
              "proposed_entity_class",
              "inclusion_basis", "match_confidence", "entity_relation",
              "entity_is_the_filer_itself",
              "matched_entity_name", "candidate_cedar_uid",
              "n_signals", "all_bases", "np_tier", "np_confidence_tier",
              "np_classification_ruling", "np_placename_risk_flag",
              "tax_period", "n_periods_available", "quote", "source_file",
              "proposal_caveat", "built_date"]
    caveat = ("PROPOSAL ONLY. Evidence is the organisation's own Form 990 "
              "mission text. Only Elijah's ruling promotes (06_nonprofit.md). "
              "A named entity in a mission is not proof of control - read "
              "entity_relation.")
    with (OUT / "mint_proposal.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for i, r in enumerate(cands, 1):
            bn = norm(r["quote"])
            if r["entity_is_the_filer_itself"] and r["candidate_cedar_uid"]:
                action = ("ATTACH EIN to existing register entity "
                          f"{r['candidate_cedar_uid']} - do NOT mint a duplicate")
            elif r["inclusion_basis"] == "named_entity":
                action = "MINT as a new nonprofit entity, keyed to the named entity"
            else:
                action = ("KEY BY BASIS, do not mint - no entity is named, "
                          "the basis is the claim")
            w.writerow({
                "rank": i, "ein": r["ein"], "org_name": r["org_name"],
                "proposed_action": action,
                "proposed_entity_class": propose_class(bn, r["matched_entity_class"]),
                "inclusion_basis": r["inclusion_basis"],
                "match_confidence": r["match_confidence"],
                "entity_relation": r["entity_relation"],
                "entity_is_the_filer_itself": int(r["entity_is_the_filer_itself"]),
                "matched_entity_name": r["matched_entity_name"],
                "candidate_cedar_uid": r["candidate_cedar_uid"],
                "n_signals": r["n_signals"],
                "all_bases": "|".join(r["all_bases"]),
                "np_tier": r["np_tier"],
                "np_confidence_tier": r["np_confidence_tier"],
                "np_classification_ruling": r["np_classification_ruling"],
                "np_placename_risk_flag": r["np_placename_risk_flag"],
                "tax_period": r["tax_period"],
                "n_periods_available": r["n_periods_available"],
                "quote": r["quote"], "source_file": r["source_file"],
                "proposal_caveat": caveat, "built_date": TODAY,
            })
    log(f"  wrote mint_proposal.csv: {len(cands):,} ranked candidates")

    # ------------------------------------------------------------------
    # corpus inventory - Schedule C / Schedule I, over the WHOLE local corpus
    # ------------------------------------------------------------------
    log("  pass 4: measuring Schedule C / Schedule I across the whole corpus ...")
    sc = {"returns_scanned": 0, "schedc_present": 0, "schedc_with_amount": 0,
          "schedc_total_lobbying_usd": 0, "schedc_political_usd": 0,
          "schedc_in_np_orgs": 0, "schedc_narrative_blocks": 0,
          "schedc_narrative_chars": 0, "schedc_electing_501h": 0,
          "schedc_nonelecting": 0, "activity_flags": Counter(),
          "schedi_returns_with_grants": 0, "schedi_grant_blocks": 0,
          "schedi_recipient_ein_blocks": 0, "schedi_purpose_blocks": 0,
          "returns_with_purpose_narrative": 0, "officer_name_blocks": 0,
          "unparsed": 0}
    schedc_rows = []
    for d in CORPUS_DIRS:
        xdir = RAW / d / "xml"
        for fn in sorted(os.listdir(xdir)):
            if not fn.endswith(".xml"):
                continue
            rec = parse_return(xdir / fn)
            if rec is None or rec.get("_parse_error"):
                sc["unparsed"] += 1
                log(f"    unparsed XML: {d}/{fn}")
                continue
            sc["returns_scanned"] += 1
            if rec["mission_desc"] or rec["activity_desc"] or rec["program_descs"]:
                sc["returns_with_purpose_narrative"] += 1
            sc["officer_name_blocks"] += rec["officer_cnt"]
            if rec["schedc_present"]:
                sc["schedc_present"] += 1
                in_np = rec["filer_ein"] in np_by_ein
                if in_np:
                    sc["schedc_in_np_orgs"] += 1
                a = rec["schedc_amounts"]
                grp = a.get("TotalLobbyingExpendGrp", "")
                flat = a.get("TotalLobbyingExpendituresAmt", "")
                pol = a.get("PoliticalExpendituresAmt", "")
                if grp:
                    sc["schedc_electing_501h"] += 1
                if flat:
                    sc["schedc_nonelecting"] += 1
                total = grp or flat
                try:
                    if total:
                        sc["schedc_total_lobbying_usd"] += int(float(total))
                        sc["schedc_with_amount"] += 1
                except ValueError:
                    log(f"    non-numeric Schedule C total in {d}/{fn}: {total!r}")
                try:
                    if pol:
                        sc["schedc_political_usd"] += int(float(pol))
                except ValueError:
                    log(f"    non-numeric political amount in {d}/{fn}: {pol!r}")
                sc["schedc_narrative_blocks"] += len(rec["schedc_explanations"])
                sc["schedc_narrative_chars"] += sum(
                    len(x) for x in rec["schedc_explanations"])
                for f in rec["schedc_activity_flags"]:
                    sc["activity_flags"][f] += 1
                npr = np_by_ein.get(rec["filer_ein"], {})
                schedc_rows.append({
                    "ein": rec["filer_ein"],
                    "filer_name_as_filed": rec["filer_name"],
                    "np_orgs_name": npr.get("org_name", ""),
                    "filer_in_np_orgs": int(in_np),
                    "np_classification_ruling": npr.get("classification_ruling", ""),
                    "np_confidence_tier": npr.get("confidence_tier", ""),
                    "tax_year": rec["tax_year"],
                    "tax_period_end": rec["tax_period_end"],
                    "return_type": rec["return_type"],
                    "object_id": fn[:-4],
                    "source_file": f"data/raw/external/{d}/xml/{fn}",
                    "election_501h": "electing" if grp else
                                     ("non_electing" if flat else "unstated"),
                    "total_lobbying_usd": total,
                    "direct_lobbying_usd": a.get("TotalDirectLobbyingGrp", ""),
                    "grassroots_lobbying_usd": a.get("TotalGrassrootsLobbyingGrp", ""),
                    "exempt_purpose_expend_usd": a.get("TotalExemptPurposeExpendGrp", ""),
                    "lobbying_nontaxable_usd": a.get("LobbyingNontaxableAmountGrp", ""),
                    "political_expenditures_usd": pol,
                    "dues_nondeductible_usd": a.get("DuesNondeductibleLobbyPltclAmt", ""),
                    "activity_flags": "|".join(sorted(set(rec["schedc_activity_flags"]))),
                    "n_narrative_blocks": len(rec["schedc_explanations"]),
                    "narrative": " || ".join(rec["schedc_explanations"])[:6000],
                    "line_refs": " || ".join(sorted(set(rec["schedc_line_refs"])))[:1000],
                    "inclusion_basis_source": "irs_form_990_schedule_c_as_filed",
                    "built_date": TODAY,
                })
            if rec["schedi_org_grants"]:
                sc["schedi_returns_with_grants"] += 1
                sc["schedi_grant_blocks"] += rec["schedi_org_grants"]
            sc["schedi_recipient_ein_blocks"] += rec["schedi_recipient_eins"]
            sc["schedi_purpose_blocks"] += rec["schedi_grant_purposes"]
    sc["activity_flags"] = dict(sc["activity_flags"])

    if schedc_rows:
        scf = sorted(schedc_rows[0].keys())
        order = ["ein", "filer_name_as_filed", "np_orgs_name", "filer_in_np_orgs",
                 "tax_year", "election_501h", "total_lobbying_usd"]
        scf = order + [c for c in scf if c not in order]
        with (OUT / "schedule_c_lobbying.csv").open(
                "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=scf)
            w.writeheader()
            for r in sorted(schedc_rows,
                            key=lambda x: (x["ein"], x["tax_year"])):
                w.writerow(r)
        log(f"  wrote schedule_c_lobbying.csv: {len(schedc_rows):,} returns")
    inventory["schedule_c_and_i"] = sc
    inventory["inclusion_basis_histogram"] = dict(hist)
    inventory["tier_a_unruled_total"] = len(tierA_unruled)
    inventory["tier_a_unruled_settled"] = len(settled)
    inventory["tier_a_unruled_histogram"] = dict(tierA_hist)
    inventory["mint_proposal_rows"] = len(cands)
    (OUT / "corpus_inventory.json").write_text(
        json.dumps(inventory, indent=2, default=str), encoding="utf-8")
    log("  wrote corpus_inventory.json")
    log(json.dumps(sc, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
