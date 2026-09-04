#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cedar Press — stage 35: entity NAME harvest and candidate register.
One-time universe-completion job.

WHAT THIS DOES
    Harvests every distinct Native-entity-shaped NAME that appears anywhere in the
    Cedar Press corpus, normalizes it, matches it against the existing spine
    (NEID / canonical_tribe_table / entity_master / cedar_entity_spine), and emits
    three registers plus a build log.

WHAT THIS DOES NOT DO
    It does NOT mint IDs. The spine is NEID + the Entity_Master series
    (T- tribes, A- ANCs, E- enterprises, N- NHOs). New entities EXTEND those
    series; docs/plans/INFLUENCE_DATASET_PLAN.md reserves I- for intertribal / inter-Native
    organizations. NP- is proposed only for Native nonprofits that are not
    Hawaiian, where N- would genuinely collide (see the log).
    Every proposal carries a blank YOUR_RULING column. Elijah rules; a later
    script assigns.

OUTPUTS
    data/clean/entity_name_harvest.csv
    data/clean/entity_candidates_new.csv
    review/entity_candidates_ambiguous.csv
    docs/ENTITY_HARVEST_LOG.md
    logs/35_entity_harvest.log

READ-ONLY GUARANTEE
    Touches nothing in data/spine/, no data/clean/cedar_*, not entity_master.csv,
    not review/cedar_review*.html.
"""

from __future__ import annotations

import csv
import glob
import os
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cedar_domain as DOM   # noqa: E402  - DEALS_TRUTH, PROMOTED_TABLES

csv.field_size_limit(1 << 30)

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
RAWX = CEDAR / "data" / "raw" / "external"
REVIEW = CEDAR / "review"
DOCS = CEDAR / "docs"
LOGS = CEDAR / "logs"
TODAY = date.today().isoformat()

LOGFH = None


def log(msg: str = "") -> None:
    print(msg)
    if LOGFH:
        LOGFH.write(msg + "\n")
        LOGFH.flush()


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------
# Hawaiian okina / glottal marks and assorted typographic apostrophes are
# stripped, not converted to a letter: Paepae o He`eia == Paepae o Heeia.
APOSTROPHES = "\u02bb\u02bc\u02bd\u2018\u2019\u02be\u02bf\u2032'`\u00b4"

CORP_FORMS = [
    "incorporated", "inc", "llc", "l l c", "llp", "lp", "plc", "pllc",
    "corporation", "corp", "company", "co", "ltd", "limited", "lc",
    "the corporation", "a corporation",
]
# Trailing forms that are dropped for the *normalized key* only. Foundation /
# association / institute are dropped per the brief, but they are ALSO recorded
# as class signals before stripping, so nothing is lost.
TRAILING_DROP = CORP_FORMS + ["foundation", "association", "assn", "assoc"]

STATE_NAMES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine",
    "maryland", "massachusetts", "michigan", "minnesota", "mississippi",
    "missouri", "montana", "nebraska", "nevada", "hampshire", "jersey",
    "mexico", "york", "carolina", "dakota", "ohio", "oklahoma", "oregon",
    "pennsylvania", "rhode", "tennessee", "texas", "utah", "vermont",
    "virginia", "washington", "wisconsin", "wyoming",
}
# Second half of a compound state name. "Standing Rock Sioux Tribe of North &
# South Dakota" must reduce to {standing, rock, sioux} — so a direction word
# is dropped only when it is actually pointing at a state stem within three
# tokens. "North Fork Rancheria" keeps its "north"; "Northern Cheyenne" is
# never touched, because "northern" is not "north".
STATE_STEMS = {"dakota", "carolina", "virginia", "york", "mexico",
               "hampshire", "jersey", "island"}
DIRECTIONS = {"north", "south", "east", "west", "new", "rhode"}

# Tokens carrying no discriminating power. Applied identically to BOTH sides,
# so key equality survives; the only risk is two DIFFERENT spine entities
# collapsing to one key, and that is caught and routed to the ambiguous file.
STOP_TOKENS = {
    "the", "of", "a", "an", "and", "in", "at", "for", "to", "on",
    "tribe", "tribes", "tribal", "tribally",
    "band", "bands", "nation", "nations", "nations'",
    "indian", "indians", "indias",
    "community", "communities", "council", "councils",
    "reservation", "reservations", "rancheria", "rancherias",
    "pueblo", "pueblos", "colony", "people", "peoples",
    "native", "natives", "aka", "previously", "listed", "as", "formerly",
}

# Single tokens that are simultaneously tribe names and US place names. A name
# whose entire Native-ness rests on ONE of these never matches. Seeded from
# code/20_fix_nonprofit_authority.py PLACE_TOKENS and extended with every
# collision named in the brief and in the 990 exclusion rules.
AMBIGUOUS_TOKENS = {
    "cherokee", "creek", "seneca", "cayuga", "mohawk", "chippewa", "ottawa",
    "miami", "peoria", "wyandotte", "pontiac", "shawnee", "sioux", "yavapai",
    "umatilla", "klamath", "modoc", "ponca", "kiowa", "comanche", "osage",
    "caddo", "natchez", "tuscarora", "oneida", "onondaga", "huron", "erie",
    "illini", "kickapoo", "winnebago", "menominee", "houma", "santee",
    "catawba", "lumbee", "pamunkey", "nottoway", "cheyenne", "apache",
    "navajo", "pawnee", "wichita", "dakota", "seminole", "choctaw",
    "chickasaw", "muskogee", "shoshone", "paiute", "maricopa", "pima",
    "mohegan", "penobscot", "acoma", "salish", "mojave", "mohave", "micmac",
    "miwok", "delaware", "kansa", "otoe", "iowa", "peoria", "quapaw",
    "tonkawa", "yuma", "hopi", "zuni", "taos", "laguna", "cochiti",
    "bannock", "chehalis", "cowlitz", "nez", "walla", "spokane", "colville",
    "yakima", "yakama", "tulalip", "makah", "quinault", "chinook", "siletz",
    "tillamook", "wallowa", "cayuse", "arapaho", "arapahoe", "kaw",
    "sac", "fox", "omaha", "missouria", "biloxi", "tunica", "natchitoches",
    "alabama", "coushatta", "chitimacha", "calusa", "timucua", "powhatan",
    "occaneechi", "saponi", "monacan", "mattaponi", "chickahominy",
    "nansemond", "meherrin", "waccamaw", "pee", "cheraw", "yamasee",
    "guale", "apalachee", "yuchi", "shawano", "oconee", "keokuk",
}

# Tokens permitted as *extras* when a spine alias appears as a contiguous
# phrase inside a longer candidate name. Anything outside this list blocks the
# containment match — this is the guard that keeps "Absentee Shawnee Tribe of
# Oklahoma" from collapsing into "Shawnee Tribe".
ALLOWED_EXTRAS = {
    "business", "businesses", "enterprise", "enterprises", "holding",
    "holdings", "industry", "industries", "service", "services", "solution",
    "solutions", "technology", "technologies", "tech", "construction",
    "development", "developments", "authority", "authorities", "housing",
    "health", "healthcare", "gaming", "casino", "casinos", "resort",
    "resorts", "hotel", "hotels", "entertainment", "group", "groups",
    "management", "energy", "utility", "utilities", "telecom",
    "telecommunications", "systems", "system", "contracting", "contractors",
    "ventures", "venture", "capital", "partners", "partnership", "trust",
    "fund", "funds", "education", "educational", "school", "schools",
    "college", "department", "office", "division", "farms", "farm", "ranch",
    "bank", "credit", "media", "transportation", "environmental", "security",
    "staffing", "logistics", "defense", "aerospace", "mission", "support",
    "professional", "consulting", "consultants", "international", "global",
    "usa", "us", "operations", "operating", "manufacturing", "engineering",
    "federal", "government", "commission", "commissions", "board",
    "properties", "property", "realty", "real", "estate", "insurance",
    "financial", "finance", "investment", "investments", "supply", "products",
    "industries", "network", "networks", "communications", "data",
    "information", "research", "laboratories", "labs", "clinic", "clinics",
    "hospital", "center", "centre", "centers", "services",
}

TOKEN_RE = re.compile(r"[a-z0-9]+")
EM_ID_RE = re.compile(r"^[TAENI]-\d+$|^NP-\d+$")


def strip_marks(s: str) -> str:
    """Casefold, drop diacritics and glottal marks, ASCII-fold."""
    if not s:
        return ""
    for ch in APOSTROPHES:
        s = s.replace(ch, "")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.encode("ascii", "ignore").decode("ascii")
    return s.lower()


PAREN_RE = re.compile(r"\(([^)]*)\)")
INNER_PAREN_RE = re.compile(r"\(([^()]*)\)")

# Two-letter USPS state codes, expanded ONLY when they sit at the very end of
# a name ("Coushatta Tribe of LA"). Never applied mid-string, where "OK", "IN",
# "OR", "ME", "LA" and "DE" are ordinary words.
STATE_ABBR = {
    "al": "alabama", "ak": "alaska", "az": "arizona", "ar": "arkansas",
    "ca": "california", "co": "colorado", "ct": "connecticut",
    "de": "delaware", "fl": "florida", "ga": "georgia", "hi": "hawaii",
    "id": "idaho", "il": "illinois", "in": "indiana", "ia": "iowa",
    "ks": "kansas", "ky": "kentucky", "la": "louisiana", "me": "maine",
    "md": "maryland", "ma": "massachusetts", "mi": "michigan",
    "mn": "minnesota", "ms": "mississippi", "mo": "missouri",
    "mt": "montana", "ne": "nebraska", "nv": "nevada",
    "nh": "new hampshire", "nj": "new jersey", "nm": "new mexico",
    "ny": "new york", "nc": "north carolina", "nd": "north dakota",
    "oh": "ohio", "ok": "oklahoma", "or": "oregon", "pa": "pennsylvania",
    "ri": "rhode island", "sc": "south carolina", "sd": "south dakota",
    "tn": "tennessee", "tx": "texas", "ut": "utah", "vt": "vermont",
    "va": "virginia", "wa": "washington", "wi": "wisconsin",
    "wv": "west virginia", "wy": "wyoming",
}


def normalize(raw: str) -> str:
    """Casefold, de-punctuate, drop leading 'the', drop trailing corporate forms."""
    s = strip_marks(raw or "")
    s = s.replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if s.startswith("the "):
        s = s[4:]
    # peel trailing corporate/collective forms repeatedly
    changed = True
    while changed and s:
        changed = False
        for form in TRAILING_DROP:
            if s.endswith(" " + form):
                s = s[: -(len(form) + 1)].strip()
                changed = True
        # a stray trailing 'dba'/'the'
        for tail in (" dba", " the"):
            if s.endswith(tail):
                s = s[: -len(tail)].strip()
                changed = True
    return s


# True corporate-form synonyms. Collapsed only for the "are these two spine
# records literally the same organization?" test. Association / Foundation /
# Consortium are deliberately NOT here: Bristol Bay Native *Corporation* (an
# ANC) and Bristol Bay Native *Association* (a tribal consortium) are two
# different organizations sharing a place name, and collapsing them would be
# exactly the class of error this job exists to prevent.
CORP_SYNONYM = {"inc": "corp", "incorporated": "corp", "corp": "corp",
                "corporation": "corp", "co": "corp", "company": "corp",
                "llc": "corp", "l l c": "corp", "ltd": "corp",
                "limited": "corp"}


def identity_key(raw: str) -> str:
    """Normalized name with trailing corporate forms RETAINED (only true
    synonyms collapsed). Used solely to test spine-record identity."""
    s = strip_marks(raw or "")
    s = s.replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if s.startswith("the "):
        s = s[4:]
    parts = s.split()
    return " ".join(CORP_SYNONYM.get(p, p) for p in parts)


def toks(norm: str) -> list[str]:
    return TOKEN_RE.findall(norm)


def key_full(norm: str) -> frozenset:
    return frozenset(t for t in toks(norm) if t not in STOP_TOKENS)


def key_nostate(norm: str) -> frozenset:
    """Distinctive tokens with the state qualifier treated as optional,
    compound state names included."""
    tl = toks(norm)
    drop = set()
    for i, t in enumerate(tl):
        if t in STATE_NAMES or t in STATE_STEMS:
            drop.add(i)
        if t in DIRECTIONS and any(x in STATE_STEMS for x in tl[i + 1:i + 4]):
            drop.add(i)
    return frozenset(t for i, t in enumerate(tl)
                     if i not in drop and t not in STOP_TOKENS)


# ---------------------------------------------------------------------------
# Trap guards
# ---------------------------------------------------------------------------
# Hard place/civic noise. A place-named organization is not a Native entity.
PLACE_CIVIC_RE = re.compile(
    r"\b("
    r"county|counties|city of|town of|township|borough of|parish of|"
    r"school district|public schools?|unified school|independent school|"
    r"state university|university of|state college|"
    r"chamber of commerce|rotary|kiwanis|lions club|elks|moose lodge|"
    r"american legion|vfw|veterans of foreign|jaycees|shriners?|shrine|"
    r"masonic|freemason|odd fellows|knights of columbus|"
    r"little league|booster|boosters|pta|pto|4 h|ffa|"
    r"boy scouts?|girl scouts?|ymca|ywca|"
    r"cemetery|volunteer fire|fire department|fire district|"
    r"electric cooperative|electric membership|rural electric|"
    r"telephone cooperative|farm bureau|"
    r"soil and water|water district|sanitation district|irrigation district|"
    r"county fair|fairgrounds|"
    r"saddle club|ski club|golf club|snowmobile|quilt|garden club|"
    r"softball|baseball|soccer club|bowling|rifle club|gun club|"
    r"clay busters|jazz|bebop|symphony|opera|"
    r"alumni|fraternity|sorority|"
    r"falls|heights|junction|springs|valley chamber"
    r")\b"
)

# Weaker civic signal: reviewed, not auto-excluded (tribal colleges, tribal
# libraries and tribal historical societies are real).
SOFT_CIVIC_RE = re.compile(
    r"\b(library|libraries|historical society|arts council|museum|"
    r"community college|technical college|senior center|food pantry|"
    r"habitat for humanity|united way|humane society|animal shelter)\b"
)

# "Pueblo" is Spanish for village. El Pueblo de Abiquiu Library is not a
# Pueblo nation.
SPANISH_PUEBLO_RE = re.compile(
    r"\bpueblo\b(?!\s+of\b)(?=.*\b(de|del|la|las|los|el|viejo|nuevo|nuestra|"
    r"senora|dominicana|bonito|colorado|nuevo)\b)|"
    r"\b(el|la|los|las)\s+pueblo\b"
)

# A NATIVE SIGNAL, for candidacy purposes only. Bare "nation" is deliberately
# absent — it fires on every carnation, donation and First Nation Bank. Bare
# "indian" is present but is disarmed by INDIAN_PLACE_RE below.
NATIVE_SIGNAL_RE = re.compile(
    r"\b("
    r"tribe|tribes|tribal|tribally|"
    r"indian|indians|american indian|"
    r"native american|native alaskan|alaska native|alaskan native|"
    r"native hawaiian|indigenous|aboriginal|first nations|"
    r"rancheria|pueblo of|band of|confederated|"
    r"inter tribal|intertribal|"
    r"native village|native corporation|ancsa|"
    r"nation of|nsn|"
    r"aihec|ncai|niga|nafoa|uset|atni|ncaied|nhoa"
    r")\b"
)

# "Indian" attached to a landform, plant or subdivision is a US place name,
# not a Native entity: Indian Creek, Indian Harbor, Indian Paintbrush,
# Indian Head, Indian Trail, Indian River.
INDIAN_PLACE_RE = re.compile(
    r"\bindian\s+(creek|harbor|harbour|paintbrush|springs?|river|lake|lakes|"
    r"hills?|trail|trails|head|point|rock|rocks|valley|mound|mounds|town|"
    r"wells|gap|run|hollow|prairie|orchard|ridge|bend|island|shores?|"
    r"meadows?|garden|gardens|oaks?|pines?|summer|grove|park|beach|"
    r"mountain|mountains|pass|ford|fields?|acres|estates|heights|"
    r"school|schools|road|street|avenue|lane|way|drive|hill)\b"
)

# "Indian" also means South Asian. Hindu Temple & Indian Cultural Center,
# North American Indian Muslim Association and the campus Indian Student
# Association are not Native entities. Note the word-order tell: "American
# Indian" is Native, "Indian American" is South Asian.
SOUTH_ASIAN_RE = re.compile(
    r"\b(hindu|temple|muslim|islamic|sikh|gurdwara|jain|"
    r"telugu|tamil|gujarati|bengali|punjabi|marathi|kannada|malayalee|"
    r"kerala|hyderabad|bollywood|diwali|garba|"
    r"indian american|indo.american|asian indian|india association|"
    r"association of india|india cultural|india house|indians in america)\b"
    r"|(?<!american )(?<!native )\bindian students? association\b"
)

# Federal agencies and programme offices are not Native entities.
FEDERAL_AGENCY_RE = re.compile(
    r"\b(bureau of indian|indian affairs|indian health service|"
    r"department of|united states|"
    r"u s department|national park service|forest service|army corps|"
    r"office of (the )?(assistant )?secretary|general services administration|"
    r"office of (direct service|self.governance|trust|indian|tribal|"
    r"management and budget|justice|public)|division of|"
    r"internal revenue|social security administration|"
    r"federal (bureau|highway|aviation|emergency)|"
    r"centers for disease|environmental protection agency|"
    r"national institutes? of health|congress of the united states)\b"
)

# Tokens strongly indicating a Hawaiian organization. Bare place names
# (hawaii, hilo, maui, kona) are OUT — "Action Roofing Hawaii LLC" is not
# an NHO. Hawaiian-language stems stay in; they are high-precision.
HAWAIIAN_SIGNAL_RE = re.compile(
    r"\b(hawaiian|kanaka|maoli|ohana|kupuna|keiki|aina|"
    r"papa ?ola|lokahi|kamehameha|"
    r"nakupuna|alakaina|alakai|makua|punana|"
    r"paepae|heeia|hookahua|hoolaulima|liliuokalani|"
    r"hoolina|pono|kakoo|kupa|halau|kula|imi|hoola)\b"
)

ALASKA_ANC_SIGNAL_RE = re.compile(
    r"\b(native corporation|village corporation|regional corporation|"
    r"ancsa|alaska native|inupiat|inupiaq|yupik|yup ?ik|athabascan|"
    r"aleut|alutiiq|unangan|tlingit|haida|tsimshian|"
    r"koniag|calista|doyon|sealaska|ahtna|chugach|bering straits|"
    r"nana|cook inlet|bristol bay|arctic slope|aleutian)\b"
)

INTERTRIBAL_SIGNAL_RE = re.compile(
    r"\b("
    r"national congress|national indian|national council|national tribal|"
    r"national native|national american indian|"
    r"inter ?tribal|intertribal|affiliated tribes|united tribes|"
    r"association of|associations|alliance|coalition|consortium|consortia|"
    r"federation|conference of|congress of|"
    r"tribal health board|health board|"
    r"gaming association|gaming commission association|"
    r"self governance|self-governance|"
    r"tribal chairmen|tribal chairman|tribal leaders|"
    r"commission on|caucus|network of|societies of|"
    r"united [a-z]{0,12} ?[a-z]{0,12} ?tribes"
    r")\b"
)

# Named collective vehicles from docs/plans/INFLUENCE_DATASET_PLAN.md's I- layer. These
# are recognized outright, because they are the population the I- series was
# reserved for.
KNOWN_I_ORG_RE = re.compile(
    r"\b(national congress of american indians|ncai|"
    r"national indian gaming association|niga|"
    r"native american finance officers|nafoa|"
    r"national center for american indian enterprise|ncaied|"
    r"national indian health board|national indian education|niea|"
    r"national american indian housing council|naihc|"
    r"alaska federation of natives|"
    r"native hawaiian organizations? association|nhoa|"
    r"ancsa regional association|"
    r"native american contractors association|"
    r"united south and eastern tribes|uset|"
    r"affiliated tribes of northwest indians|"
    r"inter.?tribal council of arizona|"
    r"great plains tribal chairmen|"
    r"midwest alliance of sovereign tribes|"
    r"columbia river inter.?tribal fish commission|"
    r"northwest indian fisheries commission|"
    r"american indian higher education consortium|aihec|"
    r"national council of urban indian health|"
    r"native cdfi network|native americans in philanthropy|"
    r"first nations development institute|"
    r"tribal (self.governance|health) (board|consortium|advisory))\b"
)

NONPROFIT_SIGNAL_RE = re.compile(
    r"\b(foundation|institute|fund|society|ministries|ministry|church|"
    r"mission|charities|"
    r"charitable|endowment|philanthropy|scholarship|nonprofit|"
    r"community development financial|cdfi|land trust)\b"
)

ENTERPRISE_SIGNAL_RE = re.compile(
    r"\b(llc|l l c|inc|incorporated|corporation|corp|company|holdings|"
    r"enterprises|enterprise|industries|ventures|group|partners|"
    r"casino|gaming|resort|solutions|technologies|services|construction|"
    r"development corporation|development authority|contracting)\b"
)

TRIBAL_FORM_RE = re.compile(
    r"\b(tribe|tribes|tribal|nation|nations|band|bands|pueblo|rancheria|"
    r"native village|indian community|indian colony|tribal council|indians|"
    r"confederated)\b"
)

# Token immediately following a matched alias phrase that turns the match into
# a place name.
PLACE_NEXT_TOKENS = {
    "county", "falls", "valley", "city", "lake", "lakes", "street", "park",
    "trail", "heights", "junction", "hills", "river", "creek", "springs",
    "bay", "township", "borough", "parish", "college", "university",
    "school", "district", "avenue", "road", "state",
}


# ---------------------------------------------------------------------------
# Spine / alias corpus
# ---------------------------------------------------------------------------
def read_csv(p: Path) -> list[dict]:
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def split_aliases(v: str, delims=";|") -> list[str]:
    if not v:
        return []
    out = [v]
    for d in delims:
        nxt = []
        for piece in out:
            nxt.extend(piece.split(d))
        out = nxt
    return [x.strip() for x in out if x and x.strip()]


class Spine:
    def __init__(self):
        self.canon_name: dict[str, str] = {}      # entity_id -> canonical name
        self.entity_class: dict[str, str] = {}
        self.neid_to_em: dict[str, str] = {}      # NEID -> Entity_Master ID
        self.exact: dict[str, set] = defaultdict(set)      # norm string -> ids
        self.kfull: dict[frozenset, set] = defaultdict(set)
        self.knost: dict[frozenset, set] = defaultdict(set)
        self.phrases: dict[str, set] = defaultdict(set)    # norm phrase -> ids
        self.n_alias_strings = 0
        self.sources = Counter()
        # inverted indexes, built once by finalise()
        self.trig: dict[str, list] = {}        # first token -> [(tuple, phrase)]
        self.tok_keys: dict[str, list] = {}    # token -> [(key, ids)]
        self.prefix: dict[str, list] = {}      # first token -> [(phrase, ids)]

    # -- id resolution: prefer the Entity_Master series, fall back to NEID ---
    def resolve(self, eid: str) -> str:
        return self.neid_to_em.get(eid, eid)

    def add(self, eid: str, name: str, source: str, depth: int = 0):
        if not eid or not name:
            return
        # Spine names carry parenthetical band/village qualifiers:
        # "Minnesota Chippewa Tribe, Minnesota (Bois Forte Band (Nett Lake))".
        # Register the paren-stripped form and each inner chunk as aliases too
        # — that is what tells Bois Forte apart from Leech Lake.
        if depth == 0 and "(" in name:
            stripped = name
            inners = []
            while "(" in stripped and ")" in stripped:
                found = INNER_PAREN_RE.findall(stripped)
                if not found:
                    break
                inners.extend(found)
                stripped = INNER_PAREN_RE.sub(" ", stripped)
            self.add(eid, re.sub(r"\s+", " ", stripped).strip(" ,;-"),
                     source + "[paren_stripped]", 1)
            for chunk in inners:
                if len(key_full(normalize(chunk))) >= 2:
                    self.add(eid, chunk, source + "[paren_inner]", 1)
        n = normalize(name)
        if not n or len(n) < 3:
            return
        eid = self.resolve(eid)
        self.exact[n].add(eid)
        kf = key_full(n)
        if kf:
            self.kfull[kf].add(eid)
        kn = key_nostate(n)
        if kn:
            self.knost[kn].add(eid)
        self.phrases[n].add(eid)
        self.n_alias_strings += 1
        self.sources[source] += 1

    def finalise(self):
        """Inverted indexes so containment matching stays linear in the number
        of candidate tokens instead of quadratic in the alias corpus."""
        trig = defaultdict(list)
        for phrase in self.phrases:
            pt = toks(phrase)
            if len(pt) < 2:
                continue
            trig[pt[0]].append((tuple(pt), phrase))
        for k in trig:
            trig[k].sort(key=lambda x: -len(x[0]))
        self.trig = dict(trig)

        pre = defaultdict(list)
        for phrase, ids in self.phrases.items():
            pt = toks(phrase)
            if pt:
                pre[pt[0]].append((phrase, ids))
        self.prefix = dict(pre)

        tk = defaultdict(list)
        for key, ids in self.knost.items():
            if len(key) < 2:
                continue
            for t in key:
                tk[t].append((key, ids))
        self.tok_keys = dict(tk)


def build_spine() -> Spine:
    sp = Spine()
    log("\n=== STEP 1: build the alias corpus ===")

    em = read_csv(CEDAR / "entity_master.csv")
    for r in em:
        eid = (r.get("Entity_ID") or "").strip()
        neid = (r.get("NEID (CICD connector)") or "").strip()
        if eid and neid:
            sp.neid_to_em[neid] = eid
    log(f"  entity_master.csv                 {len(em):>6} rows  "
        f"({len(sp.neid_to_em)} NEID->Entity_ID links)")

    for r in em:
        eid = (r.get("Entity_ID") or "").strip()
        cn = (r.get("Canonical_Name") or "").strip()
        if not eid:
            continue
        sp.canon_name.setdefault(eid, cn)
        sp.entity_class.setdefault(eid, (r.get("Entity_Type") or "").strip())
        sp.add(eid, cn, "entity_master.Canonical_Name")
        for a in split_aliases(r.get("Aliases") or "", ";"):
            sp.add(eid, a, "entity_master.Aliases")

    ct = read_csv(RAWX / "canonical_tribe_table.csv")
    for r in ct:
        tid = (r.get("tribe_id") or "").strip()
        if not tid:
            continue
        eid = sp.resolve(tid)
        sp.canon_name.setdefault(eid, (r.get("entity_namefull") or
                                       r.get("canonical_name") or "").strip())
        sp.entity_class.setdefault(eid, (r.get("entity_type") or "").strip())
        for col in ("canonical_name", "entity_namefull", "fedreg_nameaka",
                    "fedreg_nameprev", "biatld_nameshort"):
            for a in split_aliases(r.get(col) or "", ";"):
                sp.add(tid, a, f"canonical_tribe_table.{col}")
    log(f"  canonical_tribe_table.csv         {len(ct):>6} rows")

    for p in (SPINE / "cedar_entity_spine.csv", CLEAN / "cedar_entity_spine.csv"):
        rows = read_csv(p)
        if not rows:
            continue
        for r in rows:
            tid = (r.get("tribe_id") or "").strip()
            if not tid:
                continue
            eid = sp.resolve(tid)
            sp.canon_name.setdefault(eid, (r.get("canonical_name") or "").strip())
            sp.entity_class.setdefault(eid, (r.get("entity_class") or "").strip())
            sp.add(tid, r.get("canonical_name") or "", "cedar_entity_spine.canonical_name")
            for a in split_aliases(r.get("aliases") or "", "|;"):
                sp.add(tid, a, "cedar_entity_spine.aliases")
        log(f"  {p.name:<33} {len(rows):>6} rows  [{p.parent.name}/]")

    sp.finalise()
    ents = set()
    for s in (sp.exact, sp.kfull, sp.knost):
        for v in s.values():
            ents |= v
    log(f"  -> {len(ents):,} distinct spine entities, "
        f"{sp.n_alias_strings:,} alias strings, "
        f"{len(sp.exact):,} distinct normalized alias keys")
    return sp


# ---------------------------------------------------------------------------
# Matcher
# ---------------------------------------------------------------------------
class MatchResult:
    __slots__ = ("ids", "method", "confidence", "note")

    def __init__(self, ids=(), method="", confidence="none", note=""):
        self.ids = sorted(set(ids))
        self.method = method
        self.confidence = confidence
        self.note = note


OBO_SPLIT_RE = re.compile(
    r"[\s(]+(?:obo|o/b/o|on behalf of|dba|d/b/a|fka|f/k/a|aka|a/k/a|"
    r"formerly|previously)[\s)]+", re.IGNORECASE)


def name_variants(raw: str) -> list[str]:
    """Alternate readings of one observed string, tried only after the string
    itself fails. The full name is always tried FIRST, so 'Muscogee (Creek)
    Nation' still matches as written and is never reduced to 'Creek'."""
    out = []

    def push(x):
        n = normalize(x)
        if n and len(n) >= 3 and n not in out:
            out.append(n)

    # registrant-on-behalf-of-client and DBA/FKA constructions
    if OBO_SPLIT_RE.search(raw):
        for part in OBO_SPLIT_RE.split(raw):
            push(part)
    # parenthetical qualifiers: "(a federally-recognized Indian tribe)",
    # "(STOFI)", "(Gun Lake Tribe)"
    if "(" in raw:
        push(PAREN_RE.sub("", raw).strip(" ,;-"))
        for inner in PAREN_RE.findall(raw):
            push(inner)
            # "(OBO Chickahominy Indian Tribe)" — the client is inside
            for part in OBO_SPLIT_RE.split(inner):
                push(part)
    # two parties joined with a slash
    if "/" in raw:
        for part in raw.split("/"):
            push(part)
    # trailing USPS state code: "Coushatta Tribe of LA"
    tl = toks(normalize(raw))
    if len(tl) >= 3 and tl[-1] in STATE_ABBR:
        push(" ".join(tl[:-1]))
        push(" ".join(tl[:-1]) + " " + STATE_ABBR[tl[-1]])
    return out


def match_name(norm: str, raw: str, sp: Spine) -> MatchResult:
    base = _match_name_core(norm, raw, sp)
    if base.confidence != "none":
        return base
    for v in name_variants(raw):
        if v == norm:
            continue
        alt = _match_name_core(v, v, sp)
        if alt.confidence != "none":
            alt.method += f" | via variant '{v}'"
            return alt
    return base


def _match_name_core(norm: str, raw: str, sp: Spine) -> MatchResult:
    if not norm or len(norm) < 3:
        return MatchResult(method="too_short", note="name shorter than 3 chars")

    # ---- TRAP: place / civic collision ------------------------------------
    if PLACE_CIVIC_RE.search(norm):
        return MatchResult(method="blocked_place_or_civic", confidence="none",
                           note="place/civic token present; a place-named "
                                "organization is not a Native entity")

    # ---- TRAP: 'Indian <landform>' is a US place name ---------------------
    if INDIAN_PLACE_RE.search(norm):
        return MatchResult(method="blocked_indian_placename", confidence="none",
                           note="'Indian' attached to a landform/plant/"
                                "subdivision is a US place name")

    # ---- TRAP: 'Indian' also means South Asian ----------------------------
    if SOUTH_ASIAN_RE.search(norm):
        return MatchResult(method="blocked_south_asian_indian", confidence="none",
                           note="'Indian' here reads as South Asian, not "
                                "American Indian")

    # ---- Federal agencies are not Native entities -------------------------
    if FEDERAL_AGENCY_RE.search(norm):
        return MatchResult(method="blocked_federal_agency", confidence="none",
                           note="federal agency or programme office")

    # ---- TRAP: Spanish 'pueblo' -------------------------------------------
    if SPANISH_PUEBLO_RE.search(norm):
        return MatchResult(method="blocked_spanish_pueblo", confidence="none",
                           note="'pueblo' used in its Spanish sense (village), "
                                "not a Pueblo nation")

    kf = key_full(norm)
    kn = key_nostate(norm)

    # ---- TRAP: single generic token ---------------------------------------
    if len(kf) == 1:
        only = next(iter(kf))
        if only in AMBIGUOUS_TOKENS and not TRIBAL_FORM_RE.search(norm):
            return MatchResult(
                method="blocked_single_generic_token", confidence="none",
                note=f"'{only}' alone is a tribe word and a place word; a bare "
                     f"token never reaches a spine entity")

    # ---- Tier 1: exact normalized string ----------------------------------
    if norm in sp.exact:
        ids = sp.exact[norm]
        return MatchResult(ids, "exact_normalized_string",
                           "exact" if len(ids) == 1 else "none",
                           "" if len(ids) == 1 else "multiple entities share "
                           "this exact normalized name")

    # ---- Tier 2a: distinctive token set, states retained ------------------
    if kf and kf in sp.kfull:
        ids = sp.kfull[kf]
        return MatchResult(ids, "alias_token_set_with_state",
                           "alias" if len(ids) == 1 else "none",
                           "" if len(ids) == 1 else "token set shared by "
                           "multiple spine entities")

    # ---- Tier 2b: distinctive token set, state qualifier dropped ----------
    if kn and kn in sp.knost:
        ids = sp.knost[kn]
        return MatchResult(ids, "alias_token_set_state_optional",
                           "alias" if len(ids) == 1 else "none",
                           "" if len(ids) == 1 else "token set shared by "
                           "multiple spine entities once the state qualifier "
                           "is treated as optional")

    # ---- Tier 3: contiguous alias phrase inside a longer name -------------
    # Longest alias phrase wins. Every uncovered token must be an ALLOWED
    # EXTRA — this is what stops "Absentee Shawnee Tribe of Oklahoma" from
    # collapsing into "Shawnee Tribe".
    best_len, best_ids, best_phrase = 0, set(), ""
    ntoks = toks(norm)
    L = len(ntoks)
    for pos, w in enumerate(ntoks):
        for pt, phrase in sp.trig.get(w, ()):
            m = len(pt)
            if pos + m > L or tuple(ntoks[pos:pos + m]) != pt:
                continue
            nxt = ntoks[pos + m] if pos + m < L else ""
            if nxt in PLACE_NEXT_TOKENS:
                break                     # Chippewa Falls, Cherokee County...
            extras = kf - key_full(phrase)
            if extras and not extras <= ALLOWED_EXTRAS:
                break                     # qualified name; do not collapse
            ids = sp.phrases[phrase]
            if m > best_len:
                best_len, best_ids, best_phrase = m, set(ids), phrase
            elif m == best_len:
                best_ids |= set(ids)
            break                         # longest phrase at this position
    if best_ids:
        return MatchResult(
            best_ids,
            f"containment_alias_phrase[{best_phrase}]",
            "containment" if len(best_ids) == 1 else "none",
            "" if len(best_ids) == 1 else
            "the same contained phrase belongs to multiple spine entities")

    # ---- Tier 3b: candidate is a PREFIX of a longer spine alias -----------
    # "Sisseton-Wahpeton Oyate" -> "Sisseton-Wahpeton Oyate of the Lake
    # Traverse Reservation, South Dakota". Prefix-only is the guard: "Shawnee
    # Tribe" sits inside "Absentee Shawnee Tribe of Indians of Oklahoma" but
    # is NOT its prefix, so the Absentee collapse still cannot happen.
    if len(kf) >= 2:
        pref_ids = set()
        for phrase, ids in sp.prefix.get(ntoks[0], ()):
            pt = toks(phrase)
            if len(pt) <= len(ntoks):
                continue
            if pt[:len(ntoks)] == ntoks:
                pref_ids |= set(ids)
        if pref_ids:
            return MatchResult(
                pref_ids, "prefix_of_longer_spine_alias",
                "containment" if len(pref_ids) == 1 else "none",
                "" if len(pref_ids) == 1 else
                "this short form prefixes more than one spine name")

    # ---- Tier 4: plausible-parent detection for the ambiguous register ----
    # Not a match. If two or more spine keys sit inside this name, Elijah rules.
    plausible = set()
    if len(kf) >= 2:
        seen_keys = set()
        for t in kf:
            for k, ids in sp.tok_keys.get(t, ()):
                if k in seen_keys:
                    continue
                seen_keys.add(k)
                if k < kf:
                    plausible |= set(ids)
    if len(plausible) >= 2:
        return MatchResult(plausible, "multiple_plausible_parents", "none",
                           "two or more spine entities are contained in this "
                           "name; never pick")

    return MatchResult(method="no_alias_hit", confidence="none")


# ---------------------------------------------------------------------------
# Harvest sources
# ---------------------------------------------------------------------------
# (label, path, [(field, native_by_construction)], year_field, year_slice)
def yr(v: str) -> str:
    v = (v or "").strip()
    m = re.search(r"(19|20)\d{2}", v)
    return m.group(0) if m else ""


class Harvest:
    def __init__(self):
        # normalized -> record
        self.rec: dict[str, dict] = {}

    def add(self, raw: str, source: str, rowref: str, year: str = "",
            native_by_construction: bool = False, n: int = 1,
            prior_excluded: bool = False):
        raw = (raw or "").strip()
        if not raw or len(raw) < 3:
            return
        if raw.lower() in ("n/a", "na", "none", "unknown", "not applicable",
                           "not named", "various", "multiple", "tbd"):
            return
        norm = normalize(raw)
        if not norm or len(norm) < 3:
            return
        r = self.rec.get(norm)
        if r is None:
            r = self.rec[norm] = {
                "normalized_name": norm,
                "raw_forms": Counter(),
                "n_occurrences": 0,
                "sources": Counter(),
                "example_source_row": rowref,
                "years": [],
                "native_by_construction": False,
                "prior_excluded": False,
            }
        r["raw_forms"][raw] += n
        r["n_occurrences"] += n
        r["sources"][source] += n
        if native_by_construction:
            r["native_by_construction"] = True
        if prior_excluded:
            r["prior_excluded"] = True
        if year:
            r["years"].append(year)


PARENTHETICAL_SOURCES = {"deals"}


def harvest_tabular(h: Harvest) -> Counter:
    """Every source but federal_actions (streamed separately)."""
    per_source = Counter()

    def run(label, path, fields, year_field=None, native=(), extra_filter=None,
            excluded_fn=None):
        p = Path(path)
        if not p.exists():
            log(f"  [MISSING] {p}")
            return
        n_rows = 0
        n_names = 0
        with open(p, encoding="utf-8-sig", newline="") as fh:
            rd = csv.DictReader(fh)
            for i, row in enumerate(rd, start=2):
                n_rows += 1
                if extra_filter and not extra_filter(row):
                    continue
                y = yr(row.get(year_field, "")) if year_field else ""
                excl = bool(excluded_fn(row)) if excluded_fn else False
                for f in fields:
                    v = (row.get(f) or "").strip()
                    if not v:
                        continue
                    src = f"{label}.{f}"
                    nb = f in native
                    pieces = [v]
                    # Deal parties carry "Subsidiary (Parent Tribe)" — split so
                    # both the operating company and the parent are harvested.
                    if label.startswith("deals"):
                        inner = PAREN_RE.findall(v)
                        outer = PAREN_RE.sub("", v).strip(" ,;-")
                        pieces = [x for x in [outer] + inner if x]
                        # "Doyon, Limited / Huna Totem Corporation" is two
                        # parties on one row.
                        split = []
                        for piece in pieces:
                            split.extend(piece.split(" / ") if " / " in piece
                                         else [piece])
                        pieces = [x.strip() for x in split if x.strip()]
                    # BIA index cells sometimes list several tribes.
                    if label in ("compacts", "gaming_land_decisions"):
                        split = []
                        for piece in pieces:
                            split.extend(re.split(r"\s*;\s*", piece))
                        pieces = [x.strip() for x in split if x.strip()]
                    for piece in pieces:
                        h.add(piece, src, f"{p.name}:row{i}", y, nb,
                              prior_excluded=excl)
                        n_names += 1
        per_source[label] = n_names
        log(f"  {label:<34} {n_rows:>7,} rows  ->  {n_names:>7,} name observations")

    log("\n=== STEP 2: harvest tabular sources ===")

    # -- deals ---------------------------------------------------------------
    # THE TRUTH: data/clean/deals_classified.csv (cedar_domain.DEALS_TRUTH).
    #
    # This globbed `deals_*.csv` across data/clean plus the two root ledgers.
    # The glob DID happen to catch the promoted table, so this was never the
    # B-1 undercount - but it also caught every by-product that starts with
    # `deals_` (party queues, matches, attribution files, the source index)
    # and, worse, the BACKUPS: the `.bak` guard below tests `endswith(".bak")`
    # and `deals_classified.bak_2026-08-12_pre126` does not end in `.bak`. A
    # name harvest was therefore reading a two-week-old vintage of the ledger
    # as if it were a source. Named explicitly now.
    # See `cedar_domain.PROMOTED_TABLES`.
    deal_files = [str(CEDAR / DOM.DEALS_TRUTH)]
    for dp in deal_files:
        if not os.path.exists(dp) or dp.endswith(".bak"):
            continue
        run(f"deals[{Path(dp).stem}]", dp,
            ["Native_Party", "Counterparty_or_Funder"],
            year_field="Event_Year", native={"Native_Party"})

    # -- lobbying ------------------------------------------------------------
    run("lobbying_disclosures", CLEAN / "native_entity_lobbying_disclosures.csv",
        ["client_name"], year_field="filing_year", native={"client_name"})
    run("lobbying_unmatched", CLEAN / "lobbying_unmatched_clients.csv",
        ["client_name"], year_field="first_year")

    # -- nonprofit -----------------------------------------------------------
    # Existing nonprofit exclusion rulings are honoured: a name already ruled
    # out (excluded_by_prior_ruling / tier X) is still harvested for the
    # occurrence record but can never re-surface as a new candidate.
    run("np_orgs", CLEAN / "np_orgs.csv", ["org_name"],
        year_field="bmf_tax_period",
        excluded_fn=lambda r: (r.get("excluded_by_prior_ruling") == "1"
                               or r.get("confidence_tier") == "X"))

    # -- compacts ------------------------------------------------------------
    run("compacts", CLEAN / "compacts.csv", ["tribe", "bia_tribes_column"],
        year_field="original_effective_date",
        native={"tribe", "bia_tribes_column"})

    # -- gaming --------------------------------------------------------------
    run("gaming_land_decisions", CLEAN / "gaming_land_decisions.csv",
        ["tribe", "tribe_from_title"], year_field="decision_date",
        native={"tribe", "tribe_from_title"})
    run("gaming_facilities", CLEAN / "gaming_facilities.csv",
        ["tribe", "company", "facility_name"], year_field="open_date",
        native={"tribe"})

    # -- subawards -----------------------------------------------------------
    run("subawards", CLEAN / "subawards.csv", ["sub_name", "prime_name"],
        year_field="fiscal_year")

    # -- identifier ledger ---------------------------------------------------
    run("identifier_ledger", CLEAN / "cedar_identifier_ledger_final.csv",
        ["legal_business_name"])

    # -- rosters -------------------------------------------------------------
    run("anc_ceiling_roster", CLEAN / "anc_ceiling_roster.csv",
        ["corporation_name"], native={"corporation_name"})
    run("nho_doi_roster", CLEAN / "nho_doi_notification_roster.csv",
        ["organization_name"], native={"organization_name"})
    run("nho_parents", CLEAN / "nho_parents.csv", ["parent_name"],
        native={"parent_name"})

    return per_source


# Tokens that mark a phrase in running prose as naming a Native entity rather
# than a place. Required in a +/-3 token window around any alias phrase that
# does not already contain one — otherwise "Las Vegas" in a Federal Register
# notice about the city matches the Las Vegas Tribe of Paiute Indians, which
# it did on 295 documents before this guard existed.
PROSE_TRIBAL_MARKERS = {
    "tribe", "tribes", "tribal", "tribally", "nation", "nations", "band",
    "bands", "indian", "indians", "pueblo", "pueblos", "rancheria",
    "rancherias", "village", "villages", "colony", "community", "native",
    "natives", "reservation", "reservations", "confederated", "corporation",
    "council", "nsn", "ancsa", "aleut", "inupiat", "yupik", "athabascan",
}

TRIBAL_SUFFIX = (r"(?:Tribes?|Nation|Bands?|Rancheria|Pueblo|Tribal Council|"
                 r"Native Village|Indian Community|Indian Colony|"
                 r"Indian Reservation|Village Corporation|Native Corporation)")
# Must START at a capitalised word \u2014 otherwise the capture is a sentence
# fragment ("of the Nation", "and Indian Tribes", "States and Tribes").
# Lowercase particles and abbreviations that sit INSIDE real names and would
# otherwise truncate the capture: Ysleta *del* Sur Pueblo, Coeur *d'*Alene
# Tribe, Sault *Ste.* Marie Tribe, "Mandan, Hidatsa and Arikara Nation".
_WORD = r"(?:[A-Z][\w'\u2019\u02bb-]*\.?|[a-z]'[A-Z][\w'\u2019\u02bb-]*)"
ANCHORED_NAME_RE = re.compile(
    r"\b(" + _WORD + r",?"
    r"(?:\s+(?:" + _WORD + r",?|of|the|and|de|du|del|la|le|dos|des)){0,7}\s+"
    + TRIBAL_SUFFIX + r")\b")


def anchored_ok(cap: str) -> bool:
    """Cheap gate applied at capture time so the harvest file is not flooded
    with grammar. The full name-shape gate runs later at the candidate stage."""
    if len(cap) > 90 or len(cap.split()) < 2:
        return False
    n = normalize(cap)
    k = key_full(n)
    return bool(k) and not (k <= GENERIC_CAPTURE_TOKENS)


def harvest_federal_actions(h: Harvest, sp: Spine) -> tuple:
    """
    STREAMED. 156k rows / 240 MB, read one row at a time.

    Two bounded extractors, both by design NOT open-ended NER:
      (a) alias-corpus phrase matcher — every multi-token spine alias phrase,
          matched contiguously against the normalized title+abstract token
          stream, with a trigger-token index so the scan stays linear;
      (b) suffix-anchored capture — capitalised phrases ENDING in a tribal form
          word (Tribe / Nation / Band / Rancheria / Pueblo / Native Village...).
          Anchored and length-bounded, so it can surface an un-spined tribe
          without hallucinating entities out of ordinary prose.
    """
    p = CLEAN / "federal_actions.csv"
    log("\n=== STEP 3: stream federal_actions.csv ===")
    if not p.exists():
        log(f"  [MISSING] {p}")
        return 0, 0, 0, 0

    trig = sp.trig      # built once in Spine.finalise()
    log(f"  alias phrase index: {sum(len(v) for v in trig.values()):,} phrases "
        f"on {len(trig):,} trigger tokens")

    t0 = time.time()
    n_rows = 0
    n_alias_hits = 0
    n_anchor = 0
    n_prose_blocked = 0
    with open(p, encoding="utf-8", newline="") as fh:
        rd = csv.DictReader(fh)
        for i, row in enumerate(rd, start=2):
            n_rows += 1
            title = row.get("title") or ""
            abstract = row.get("abstract") or ""
            if not title and not abstract:
                continue
            year = (row.get("publication_date") or "")[:4]
            blob = title + ". " + abstract

            # (a) alias phrase matcher on the normalized token stream
            nt = TOKEN_RE.findall(strip_marks(blob))
            L = len(nt)
            seen_here = set()
            for j, w in enumerate(nt):
                cands = trig.get(w)
                if not cands:
                    continue
                for pt, phrase in cands:
                    m = len(pt)
                    if j + m > L or tuple(nt[j:j + m]) != pt:
                        continue
                    nxt = nt[j + m] if j + m < L else ""
                    if nxt in PLACE_NEXT_TOKENS:
                        break
                    # the phrase must read as a Native entity in context
                    if not (set(pt) & PROSE_TRIBAL_MARKERS):
                        window = set(nt[max(0, j - 3):j]) | \
                            set(nt[j + m:j + m + 3])
                        if not (window & PROSE_TRIBAL_MARKERS):
                            n_prose_blocked += 1
                            break
                    if phrase not in seen_here:
                        seen_here.add(phrase)
                    break                       # longest phrase wins at j
            for phrase in seen_here:
                h.add(phrase, "federal_actions.title_abstract[alias_phrase]",
                      f"federal_actions.csv:row{i}", year, True)
                n_alias_hits += 1

            # (b) suffix-anchored capture
            for m in ANCHORED_NAME_RE.finditer(blob):
                cap = m.group(1).strip()
                if not anchored_ok(cap):
                    continue
                h.add(cap, "federal_actions.title_abstract[anchored_suffix]",
                      f"federal_actions.csv:row{i}", year, False)
                n_anchor += 1

            if n_rows % 25000 == 0:
                log(f"    ... {n_rows:,} rows  ({time.time()-t0:.0f}s)")

    log(f"  {n_rows:,} rows streamed in {time.time()-t0:.0f}s")
    log(f"  alias-phrase observations {n_alias_hits:,} | "
        f"suffix-anchored observations {n_anchor:,}")
    log(f"  alias phrases rejected for lacking a tribal marker in context "
        f"(place-name reading): {n_prose_blocked:,}")
    return n_rows, n_alias_hits, n_anchor, n_prose_blocked


def harvest_bills(h: Harvest) -> int:
    """native_bills.affected_entities is empty in the current build; titles are
    scanned with the same suffix-anchored extractor."""
    p = CLEAN / "native_bills.csv"
    log("\n=== STEP 4: native_bills.csv ===")
    rows = read_csv(p)
    if not rows:
        log("  [MISSING]")
        return 0
    nonblank_ae = sum(1 for r in rows if (r.get("affected_entities") or "").strip())
    log(f"  {len(rows):,} bills | affected_entities populated on "
        f"{nonblank_ae} rows")
    n = 0
    for i, r in enumerate(rows, start=2):
        y = yr(r.get("introduced_date", ""))
        for a in split_aliases(r.get("affected_entities") or "", "|;"):
            h.add(a, "native_bills.affected_entities", f"native_bills.csv:row{i}",
                  y, True)
            n += 1
        for m in ANCHORED_NAME_RE.finditer(r.get("title") or ""):
            cap = m.group(1).strip()
            if not anchored_ok(cap):
                continue
            h.add(cap, "native_bills.title[anchored_suffix]",
                  f"native_bills.csv:row{i}", y, False)
            n += 1
    log(f"  -> {n:,} name observations")
    return n


# ---------------------------------------------------------------------------
# Classification of unmatched names
# ---------------------------------------------------------------------------
# A candidate must read like a NAME, not like a sentence fragment lifted out
# of a Federal Register abstract or a roster header row.
SENTENCE_JUNK_RE = re.compile(
    r"\b(a compilation|compilation of|settlement act|pursuant to|shall be|"
    r"notice of|ordinance|amendment|amendments|regulations?|rulemaking|"
    r"class iii|class ii|compact between|agreement between|between the|"
    r"under the|for the purpose|information about|list of|"
    r"application|petition|proposed|final rule|request for|"
    r"availability|record of decision|environmental impact|"
    r"funding agreement|agreements|negotiated|to be |reallotment|"
    r"solicitation|memorandum|guidelines|eligible to receive|"
    r"recipients|awardees|grantees|tdhes|and \d+)\b"
)

# Distinctive tokens that carry no entity identity on their own. A capture
# whose entire distinctive content sits in here is grammar, not a name.
GENERIC_CAPTURE_TOKENS = {
    "state", "states", "united", "federal", "government", "governments",
    "american", "americans", "certain", "various", "other", "others",
    "all", "some", "each", "several", "three", "two", "four", "five",
    "mhz", "ghz", "khz", "band", "bands", "class", "part", "title",
    "section", "subpart", "act", "public", "law", "code", "chapter",
    "affected", "eligible", "participating", "interested", "individual",
    "member", "members", "local", "regional", "national", "area", "areas",
    "list", "notice", "program", "programs", "service", "services",
    "office", "bureau", "department", "secretary", "agency", "agencies",
    # class nouns lifted out of Federal Register prose
    "federally", "recognized", "recognized", "confederated", "self",
    "governance", "eastern", "western", "northern", "southern",
    "alaska", "alaskan", "hawaii", "corporations", "entities",
    "organizations", "organizations", "villages", "pueblos", "rancherias",
    "groups", "recognition", "identified", "village", "urban", "regional",
    "territories", "territory", "possessions", "insular",
}

# A reservation is a geography. "Fort Hall Indian Reservation" is a place the
# Shoshone-Bannock Tribes govern, not an organization with an entity ID.
RESERVATION_GEOGRAPHY_RE = re.compile(r"\breservations?\s*$")

# A federal programme, grant vehicle or statute is not an entity:
# "Tribal Broadband Connectivity Program", "HUD Office of Native American
# Programs", "Thomasina E. Jordan Indian Tribes of Virginia Recognition Act".
PROGRAM_OR_STATUTE_RE = re.compile(
    r"\b(programs?|initiative|act|grant program|"
    r"connectivity program|demonstration|set.aside|"
    r"office of native american|hud office)\b")


def looks_like_a_name(raw: str, norm: str) -> bool:
    """Gate on the harvested string before it can become a candidate."""
    if len(raw) > 75 or len(raw.split()) > 10:
        return False
    if "|" in raw or "\t" in raw:
        return False        # scrape artefact, e.g. a nav breadcrumb
    if not raw[:1].isalpha() and not raw[:1].isdigit():
        return False
    # a capture that starts with a lowercase connective is a sentence fragment
    first = raw.split()[0]
    if first[:1].islower():
        return False
    if SENTENCE_JUNK_RE.search(norm):
        return False
    if RESERVATION_GEOGRAPHY_RE.search(norm):
        return False        # a reservation is a place, not an organization
    if PROGRAM_OR_STATUTE_RE.search(norm):
        return False        # a programme or statute is not an entity
    kf = key_full(norm)
    if not kf or kf <= GENERIC_CAPTURE_TOKENS:
        return False
    return True


def propose_class(norm: str, raw: str, sources: str, native_by_construction: bool):
    """Return (prefix, class_label, evidence_list) or (None, None, why_not)."""
    ev = []
    src = sources.lower()

    if "anc_ceiling_roster" in src:
        return "A-", "ANCSA corporation (ceiling roster)", \
            ["listed on the ANCSA 8(a) ceiling roster"]
    if "nho_doi_roster" in src or "nho_parents" in src:
        return "N-", "Native Hawaiian Organization", \
            ["listed on a DOI NHO notification roster / NHO parent list"]

    known_i = KNOWN_I_ORG_RE.search(norm)
    if known_i:
        return "I-", "Intertribal / inter-Native organization", \
            [f"named in docs/plans/INFLUENCE_DATASET_PLAN.md's I- layer "
             f"('{known_i.group(0)}')"]

    haw = HAWAIIAN_SIGNAL_RE.search(norm)
    ak = ALASKA_ANC_SIGNAL_RE.search(norm)
    inter = INTERTRIBAL_SIGNAL_RE.search(norm)
    npf = NONPROFIT_SIGNAL_RE.search(raw.lower())
    ent = ENTERPRISE_SIGNAL_RE.search(raw.lower())
    trib = TRIBAL_FORM_RE.search(norm)
    nat = NATIVE_SIGNAL_RE.search(norm)

    if haw:
        ev.append(f"Hawaiian-language / Hawaiian-place token '{haw.group(0)}'")
        return "N-", "Native Hawaiian Organization", ev
    if ak and ("corporation" in raw.lower() or "native corporation" in norm
               or "village corporation" in norm or "ancsa" in norm):
        ev.append(f"Alaska Native corporate token '{ak.group(0)}'")
        return "A-", "Alaska Native corporation / village corporation", ev
    # A collective-vehicle word ONLY counts alongside an explicit Native
    # signal. Without that rule "Association of Old Crows" and "South Dakota
    # Congress of Parents and Teachers" become intertribal organizations.
    if inter and (nat or haw or native_by_construction):
        ev.append(f"collective-vehicle token '{inter.group(0)}' "
                  f"alongside a Native signal")
        return "I-", "Intertribal / inter-Native organization", ev
    if trib and not ent:
        # A tribal-government form word plus business vocabulary reads as an
        # arm of a government, not the government: "Navajo Tribal Utility
        # Authority", "Miami Tribal Systems Integrators".
        biz = key_full(norm) & ALLOWED_EXTRAS
        if biz:
            ev.append(f"tribal form '{trib.group(0)}' plus business vocabulary "
                      f"({', '.join(sorted(biz))}) — reads as an arm of a "
                      f"government, not the government")
            return "E-", "Enterprise or subsidiary", ev
        ev.append(f"tribal-government form '{trib.group(0)}'")
        return "T-", "Tribal government (recognition status unruled)", ev
    if npf and (nat or native_by_construction):
        ev.append(f"nonprofit form '{npf.group(0)}' with a Native signal")
        return "NP-", "Native nonprofit (non-Hawaiian)", ev
    if ent and (nat or native_by_construction):
        ev.append(f"corporate form '{ent.group(0)}' with a Native signal")
        return "E-", "Enterprise or subsidiary", ev
    if nat:
        ev.append(f"Native signal '{nat.group(0)}'")
        return "E-", "Unclassified Native-signalled organization", ev
    if native_by_construction:
        ev.append("appears in a field that is Native by construction")
        return "E-", "Unclassified Native-signalled organization", ev
    return None, None, ["no Native signal in the name and no Native-by-"
                        "construction source"]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    global LOGFH
    LOGS.mkdir(parents=True, exist_ok=True)
    LOGFH = open(LOGS / "35_entity_harvest.log", "w", encoding="utf-8")
    log("=" * 78)
    log("Cedar Press stage 35 — entity NAME harvest / candidate register")
    log(f"run {TODAY}")
    log("NO IDS ARE MINTED. Proposals only; YOUR_RULING is blank on every row.")
    log("=" * 78)

    sp = build_spine()

    h = Harvest()
    per_source = harvest_tabular(h)
    fr_rows, fr_alias, fr_anchor, fr_prose = harvest_federal_actions(h, sp)
    harvest_bills(h)

    log(f"\n=== STEP 5: deduplicate + match ({len(h.rec):,} distinct "
        f"normalized names) ===")

    harvest_rows = []
    ambiguous_rows = []
    candidate_rows = []
    conf_counter = Counter()
    method_counter = Counter()
    noise_counter = Counter()
    ambiguity_type_counter = Counter()
    gate_counter = Counter()
    priority_counter = Counter()

    t0 = time.time()
    for k, (norm, r) in enumerate(sorted(h.rec.items())):
        if k and k % 5000 == 0:
            log(f"    ... matched {k:,}/{len(h.rec):,} ({time.time()-t0:.0f}s)")
        raw = r["raw_forms"].most_common(1)[0][0]
        mr = match_name(norm, raw, sp)
        years = sorted(y for y in r["years"] if y)
        srcs = "|".join(sorted(r["sources"]))
        matched_id = mr.ids[0] if (mr.confidence != "none" and len(mr.ids) == 1) else ""

        conf_counter[mr.confidence] += 1
        method_counter[mr.method.split(" | ")[0].split("[")[0]] += 1
        if mr.method.startswith("blocked_") or mr.method == "too_short":
            noise_counter[mr.method] += 1

        harvest_rows.append({
            "raw_name": raw,
            "normalized_name": norm,
            "n_occurrences": r["n_occurrences"],
            "source_datasets": srcs,
            "example_source_row": r["example_source_row"],
            "first_year_seen": years[0] if years else "",
            "last_year_seen": years[-1] if years else "",
            "matched_entity_id": matched_id,
            "matched_entity_name": sp.canon_name.get(matched_id, "") if matched_id else "",
            "match_method": mr.method + (f" | {mr.note}" if mr.note else ""),
            "match_confidence": mr.confidence,
            "n_raw_variants": len(r["raw_forms"]),
            "native_by_construction": "1" if r["native_by_construction"] else "",
            "prior_ruling_excluded": "1" if r["prior_excluded"] else "",
        })

        # ---- ambiguous register -------------------------------------------
        if mr.confidence == "none" and len(mr.ids) >= 2:
            em_ids = [e for e in mr.ids if EM_ID_RE.match(e)]
            neids = [e for e in mr.ids if not EM_ID_RE.match(e)]
            # A single Entity_Master row facing a single NEID is not an entity
            # ambiguity — it is the known, open NEID<->Entity_Master crosswalk
            # gap (AGENTS.md queue item 4: ~215 links still need a manual pass;
            # 250 entity_master rows carry a blank NEID today). Labeled, never
            # silently merged.
            identity_tier = (mr.method.startswith("exact_")
                             or mr.method.startswith("alias_token_set")
                             or mr.method.startswith("prefix_of_longer"))
            same_name = (len(em_ids) == 1 and len(neids) == 1
                         and identity_key(sp.canon_name.get(em_ids[0], "x"))
                         == identity_key(sp.canon_name.get(neids[0], "y")))
            if identity_tier and same_name:
                atype = "possible_unlinked_spine_pair"
                question = (f"'{raw}' hits BOTH {em_ids[0]} "
                            f"({sp.canon_name.get(em_ids[0],'')}) and NEID "
                            f"{neids[0]} ({sp.canon_name.get(neids[0],'')}), "
                            f"whose canonical names are identical. Likely one "
                            f"entity whose entity_master NEID cell is blank — "
                            f"confirm the crosswalk link, or say they are "
                            f"distinct organizations that share a name.")
                ambiguity_type_counter["possible_unlinked_spine_pair"] += 1
            else:
                atype = "competing_entities"
                question = (f"'{raw}' resolves equally well to "
                            f"{len(mr.ids)} spine entities ({mr.method}). "
                            f"Which one — or is it a distinct entity that "
                            f"needs its own ID?")
                ambiguity_type_counter["competing_entities"] += 1
            harvest_rows[-1]["match_method"] = atype + " | " + \
                harvest_rows[-1]["match_method"]
            ambiguous_rows.append({
                "candidate_name": raw,
                "normalized_name": norm,
                "ambiguity_type": atype,
                "competing_entity_ids": "|".join(mr.ids),
                "competing_names": "|".join(sp.canon_name.get(e, e) for e in mr.ids),
                "n_occurrences": r["n_occurrences"],
                "source_datasets": srcs,
                "example_source_row": r["example_source_row"],
                "question": question,
                "YOUR_RULING": "",
            })
            continue

        # ---- new-candidate register ---------------------------------------
        if mr.confidence == "none" and not mr.ids:
            if mr.method.startswith("blocked_") or mr.method == "too_short":
                continue
            if r["prior_excluded"]:
                gate_counter["prior_ruling_excluded"] += 1
                continue
            if not looks_like_a_name(raw, norm):
                gate_counter["not_name_shaped"] += 1
                continue
            prefix, klass, ev = propose_class(norm, raw, srcs,
                                              r["native_by_construction"])
            if not prefix:
                gate_counter["no_native_signal"] += 1
                continue
            if SOFT_CIVIC_RE.search(norm):
                ev = list(ev) + ["REVIEW: also carries a civic/institutional "
                                 "token (library/museum/college) — tribal "
                                 "versions of these are real, place-named ones "
                                 "are not"]
            # Triage order for the ruling session. HIGH = the name came from a
            # field that is Native by construction, or recurs often enough that
            # a wrong attribution would move money. LOW = a single sighting in
            # a discovery pool built to over-capture.
            srcset = set(r["sources"])
            extraction_only = srcset and all("anchored_suffix" in x
                                             for x in srcset)
            if r["native_by_construction"]:
                priority = "HIGH"
            elif extraction_only:
                # A suffix-anchored capture can still be a truncated phrase
                # ("Sur Pueblo" out of "Ysleta del Sur Pueblo"). Occurrence
                # count does NOT promote these — a common fragment is still a
                # fragment.
                priority = "LOW"
            elif (srcset and all(x.startswith("np_orgs") for x in srcset)
                  and r["n_occurrences"] < 3):
                priority = "LOW"
            else:
                priority = "MEDIUM"
            priority_counter[priority] += 1
            candidate_rows.append({
                "candidate_name": raw,
                "normalized_name": norm,
                "proposed_prefix": prefix,
                "proposed_class": klass,
                "priority": priority,
                "evidence": "; ".join(ev),
                "n_occurrences": r["n_occurrences"],
                "source_datasets": srcs,
                "example_source_row": r["example_source_row"],
                "first_year_seen": years[0] if years else "",
                "last_year_seen": years[-1] if years else "",
                "YOUR_RULING": "",
            })

    # -----------------------------------------------------------------------
    log("\n=== STEP 6: write outputs ===")
    CLEAN.mkdir(parents=True, exist_ok=True)
    REVIEW.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)

# --- REGENERATE GUARD (ADR-017, 2026-09-02) --------------------------------
def _carry_live_columns(path, canonical):
    """Derive this writer's header instead of declaring it.

    A wholesale writer holding a FIXED `fieldnames` list deletes every column
    an in-place enricher added since - no error, no exception, a diff nobody
    reads. Canonical order first so column order stays stable, then whatever
    the live file already carries. A retired column stays retired because it
    is not on disk; a promoted column survives because it is.

    THIS BUILD CANNOT REPOPULATE AN ENRICHER'S COLUMN. Carried columns are
    written BLANK and NAMED on stdout, which is strictly better than deleted:
    the schema survives and the enricher can refill them. Re-run the enricher
    after this build - `cedar_pipeline.enrichers_to_rerun(<table>)` names it.
    """
    import csv as _csv
    import os as _os
    canonical = list(canonical)
    _p = str(path)
    if not _os.path.exists(_p):
        return canonical
    with open(_p, encoding="utf-8-sig", newline="", errors="replace") as _fh:
        _live = next(_csv.reader(_fh), [])
    _extra = [c for c in _live if c and c not in canonical]
    if _extra:
        print("  [regenerate guard] %s: carrying %d enricher column(s) through "
              "this rebuild, BLANK - re-run the enricher: %s"
              % (_os.path.basename(_p), len(_extra), ", ".join(_extra)))
    return canonical + _extra


    def write(p: Path, rows, fields):
        # REGENERATE GUARD (ADR-017, 2026-09-02): derive the header, do not declare it.
        fields = _carry_live_columns(p, fields)
        with open(p, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        log(f"  wrote {p.relative_to(CEDAR)}  ({len(rows):,} rows)")

    harvest_rows.sort(key=lambda r: (-r["n_occurrences"], r["normalized_name"]))
    PRI = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    candidate_rows.sort(key=lambda r: (PRI[r["priority"]], r["proposed_prefix"],
                                       -r["n_occurrences"]))
    ambiguous_rows.sort(key=lambda r: -r["n_occurrences"])

    write(CLEAN / "entity_name_harvest.csv", harvest_rows,
          ["raw_name", "normalized_name", "n_occurrences", "source_datasets",
           "example_source_row", "first_year_seen", "last_year_seen",
           "matched_entity_id", "matched_entity_name", "match_method",
           "match_confidence", "n_raw_variants", "native_by_construction",
           "prior_ruling_excluded"])
    write(CLEAN / "entity_candidates_new.csv", candidate_rows,
          ["candidate_name", "proposed_prefix", "proposed_class", "priority",
           "evidence", "n_occurrences", "source_datasets",
           "example_source_row", "first_year_seen", "last_year_seen",
           "normalized_name", "YOUR_RULING"])
    write(REVIEW / "entity_candidates_ambiguous.csv", ambiguous_rows,
          ["candidate_name", "competing_entity_ids", "competing_names",
           "n_occurrences", "question", "ambiguity_type", "source_datasets",
           "example_source_row", "normalized_name", "YOUR_RULING"])

    # -----------------------------------------------------------------------
    stats = {
        "distinct": len(harvest_rows),
        "conf": conf_counter,
        "method": method_counter,
        "noise": noise_counter,
        "candidates": candidate_rows,
        "ambiguous": ambiguous_rows,
        "harvest": harvest_rows,
        "per_source": per_source,
        "fr": (fr_rows, fr_alias, fr_anchor, fr_prose),
        "spine": sp,
        "atype": ambiguity_type_counter,
        "gate": gate_counter,
        "priority": priority_counter,
    }
    write_md(stats)

    matched = sum(v for k, v in conf_counter.items() if k != "none")
    log("\n=== SUMMARY ===")
    log(f"  distinct normalized names harvested : {len(harvest_rows):,}")
    log(f"  matched to a single spine entity    : {matched:,} "
        f"({matched/max(1,len(harvest_rows)):.1%})")
    for c in ("exact", "alias", "containment", "none"):
        log(f"    {c:<12} {conf_counter[c]:>7,}")
    nbc = [r for r in harvest_rows if r["native_by_construction"]]
    nbc_m = sum(1 for r in nbc if r["match_confidence"] != "none")
    log(f"  --- restricted to Native-by-construction fields ---")
    log(f"    distinct names                    : {len(nbc):,}")
    log(f"    matched                           : {nbc_m:,} "
        f"({nbc_m/max(1,len(nbc)):.1%})")
    log(f"  candidate gate rejections:")
    for k, v in gate_counter.most_common():
        log(f"    {k:<24} {v:>7,}")
    log(f"  new candidates proposed             : {len(candidate_rows):,}")
    for k in ("HIGH", "MEDIUM", "LOW"):
        log(f"    {k:<24} {priority_counter[k]:>7,}")
    log(f"  ambiguities for Elijah              : {len(ambiguous_rows):,}")
    for k, v in ambiguity_type_counter.most_common():
        log(f"    {k:<24} {v:>7,}")
    log("\nNo IDs were minted. Every proposal awaits YOUR_RULING.")
    LOGFH.close()


def md(x) -> str:
    """Escape a value for a markdown table cell."""
    return " ".join(str(x).replace("|", " / ").split())


def write_md(s: dict):
    sp: Spine = s["spine"]
    hr = s["harvest"]
    total = len(hr)
    conf = s["conf"]
    matched = sum(v for k, v in conf.items() if k != "none")
    cand = s["candidates"]
    amb = s["ambiguous"]
    noise = s["noise"]

    by_prefix = Counter(c["proposed_prefix"] for c in cand)
    by_class = Counter(c["proposed_class"] for c in cand)

    # per-source rollup off the harvest rows
    src_names = Counter()
    src_matched = Counter()
    for r in hr:
        for sname in r["source_datasets"].split("|"):
            base = sname.split(".")[0]
            src_names[base] += 1
            if r["match_confidence"] != "none":
                src_matched[base] += 1

    blocked = sum(noise.values())
    unmatched = conf["none"]
    # place-name noise estimate: hard-blocked + unmatched-with-no-Native-signal
    no_signal = 0
    for r in hr:
        if r["match_confidence"] != "none":
            continue
        if r["match_method"].startswith("blocked_"):
            continue
        if not NATIVE_SIGNAL_RE.search(r["normalized_name"]):
            no_signal += 1
    noise_est = blocked + max(0, unmatched - blocked - len(amb) - len(cand))

    L = []
    A = L.append
    A("# Entity Name Harvest — build log")
    A("")
    A(f"*Stage 35. Run {TODAY}. Script `code/35_entity_harvest.py`, "
      f"log `logs/35_entity_harvest.log`.*")
    A("")
    A("One-time universe-completion job: every distinct Native-entity-shaped "
      "name appearing anywhere in the Cedar Press corpus, normalized, "
      "deduplicated, and matched against the spine.")
    A("")
    A("## The rule this job obeyed")
    A("")
    A("**No parallel ID system was minted.** The spine is NEID (CICD connector, "
      "687 entities) plus the `Entity_Master` series — `T-` 588 federally "
      "recognized tribes, `A-` 191 ANCs and village corporations, `E-` 29 "
      "enterprises and subsidiaries, `N-` 7 Native Hawaiian Organizations. "
      "Every proposal in this build **extends** one of those series or the "
      "`I-` series that docs/plans/INFLUENCE_DATASET_PLAN.md reserves for intertribal and "
      "inter-Native organizations. Nothing here is assigned; "
      "`entity_candidates_new.csv` and `entity_candidates_ambiguous.csv` both "
      "carry a blank `YOUR_RULING` column and a later script does the minting.")
    A("")
    A("**On `NP-`.** It is proposed, sparingly, for Native nonprofits that are "
      "*not* Hawaiian. `N-` is already in use for Native Hawaiian "
      "Organizations — all 7 current `N-` rows are NHOs, and the DOI NHO "
      "roster is the population behind them. Putting a Minnesota Native CDFI "
      "or a national Native philanthropy under `N-` would make the prefix mean "
      "two different things and would silently corrupt every NHO count taken "
      "off a prefix filter, including the 190-row DOI roster ceiling in "
      "docs/handoffs/STATE_OF_BUILD.md. That is a genuine collision, so `NP-` is proposed "
      "rather than forced into `N-`. If Elijah prefers, the alternative is to "
      "keep one `N-` series with a mandatory subclass column; the register is "
      "written so either ruling is a one-line change.")
    A("")
    A("## Alias corpus")
    A("")
    A("| Source | Alias strings contributed |")
    A("|---|---:|")
    for k, v in sp.sources.most_common():
        A(f"| `{k}` | {v:,} |")
    A(f"| **total** | **{sp.n_alias_strings:,}** |")
    A("")
    A(f"Collapsed to {len(sp.exact):,} distinct normalized alias keys. Both "
      "sides of every comparison are normalized identically: casefold, "
      "diacritics and Hawaiian glottal marks stripped, punctuation removed, "
      "leading *The* dropped, trailing corporate forms "
      "(Inc/LLC/Corp/Corporation/Foundation/Association) peeled, and "
      "`of <State>` treated as optional via a second state-dropped key.")
    A("")
    A("## Names harvested per source")
    A("")
    A("| Source dataset | Distinct names | Matched to spine | Match rate |")
    A("|---|---:|---:|---:|")
    for k in sorted(src_names, key=lambda x: -src_names[x]):
        n = src_names[k]
        m = src_matched[k]
        A(f"| `{k}` | {n:,} | {m:,} | {m/n:.0%} |")
    A("")
    A(f"`federal_actions.csv` was **streamed** — {s['fr'][0]:,} rows / 240 MB "
      "read one row at a time, never loaded. Two bounded extractors ran on "
      "`title` + `abstract`: the alias-corpus phrase matcher "
      f"({s['fr'][1]:,} observations) and a suffix-anchored capture that only "
      "takes capitalised phrases *ending* in a tribal form word — Tribe, "
      "Nation, Band, Rancheria, Pueblo, Native Village, Indian Community "
      f"({s['fr'][2]:,} observations). No open-ended NER was attempted.")
    A("")
    A(f"An alias phrase matched in running prose must also carry a tribal "
      f"marker — *tribe*, *band*, *Indian*, *pueblo*, *village*, *native*, "
      f"*reservation* — either inside the phrase or within three tokens of "
      f"it. **{s['fr'][3]:,} phrase hits were rejected by that rule.** "
      "Without it, *Las Vegas* in a Federal Register notice about the city "
      "matched the Las Vegas Tribe of Paiute Indians on 295 documents, and "
      "*Bristol Bay* matched the ANC every time the fishery was mentioned.")
    A("")
    A("`native_bills.affected_entities` is empty on all 3,037 rows in the "
      "current build, so bill titles were run through the same suffix-anchored "
      "extractor. Fixing `affected_entities` upstream would materially improve "
      "this source.")
    A("")
    A("## Match rate against the spine")
    A("")
    A("| Confidence | Names | Share |")
    A("|---|---:|---:|")
    for c in ("exact", "alias", "containment", "none"):
        A(f"| {c} | {conf[c]:,} | {conf[c]/max(1,total):.1%} |")
    A(f"| **total** | **{total:,}** | |")
    A("")
    A(f"**{matched:,} of {total:,} distinct names ({matched/max(1,total):.1%}) "
      "matched a single spine entity.**")
    A("")
    nbc = [r for r in hr if r["native_by_construction"]]
    nbc_m = sum(1 for r in nbc if r["match_confidence"] != "none")
    A("That headline rate is close to meaningless on its own, because the "
      "denominator is dominated by two sources that are *supposed* to be "
      "mostly non-Native: the IRS BMF candidate pool in `np_orgs` and every "
      "UEI legal name in the contracting ledger. The rate that actually "
      "measures spine coverage is the one restricted to fields that are "
      "**Native by construction**:")
    A("")
    A("| Scope | Distinct names | Matched | Rate |")
    A("|---|---:|---:|---:|")
    A(f"| All sources | {total:,} | {matched:,} | {matched/max(1,total):.1%} |")
    A(f"| Native-by-construction fields only | {len(nbc):,} | {nbc_m:,} | "
      f"{nbc_m/max(1,len(nbc)):.1%} |")
    A("")
    A("Native-by-construction fields are: `anc_ceiling_roster."
      "corporation_name`, `nho_doi_notification_roster.organization_name`, "
      "`nho_parents.parent_name`, `deals.Native_Party`, `compacts.tribe` and "
      "`bia_tribes_column`, `gaming_land_decisions.tribe`, "
      "`gaming_facilities.tribe`, `native_entity_lobbying_disclosures."
      "client_name`, and the federal-actions alias-phrase hits. A name in one "
      "of those that reaches no spine entity is a real coverage question, not "
      "noise — which is why it is the HIGH-priority bucket in the candidate "
      "register.")
    A("")
    A("Method breakdown:")
    A("")
    A("| Method | Names |")
    A("|---|---:|")
    for k, v in s["method"].most_common():
        A(f"| `{k}` | {v:,} |")
    A("")
    A("## New candidates by proposed class")
    A("")
    A("| Prefix | Meaning | Candidates |")
    A("|---|---|---:|")
    PREFIX_MEANING = {
        "T-": "tribal government (recognition status unruled)",
        "A-": "ANC / village corporation",
        "E-": "enterprise or subsidiary",
        "N-": "Native Hawaiian Organization",
        "I-": "intertribal / inter-Native organization",
        "NP-": "Native nonprofit (non-Hawaiian)",
    }
    for p_, n in by_prefix.most_common():
        A(f"| `{p_}` | {PREFIX_MEANING.get(p_,'')} | {n:,} |")
    A(f"| **total** | | **{len(cand):,}** |")
    A("")
    A("Proposed class detail:")
    A("")
    A("| Proposed class | Candidates |")
    A("|---|---:|")
    for k, v in by_class.most_common():
        A(f"| {k} | {v:,} |")
    A("")
    if cand:
        A("### Triage")
        A("")
        A("`entity_candidates_new.csv` carries a `priority` column so the "
          "ruling session has an order:")
        A("")
        A("| Priority | Candidates | Rule |")
        A("|---|---:|---|")
        A(f"| HIGH | {s['priority']['HIGH']:,} | the name came out of a field "
          "that is Native **by construction** — ANC ceiling roster, DOI NHO "
          "roster, NHO parents, deal `Native_Party`, compact `tribe`, gaming "
          "`tribe`, attributed lobbying `client_name`. If it is real and "
          "unmatched, the spine has a hole. |")
        A(f"| MEDIUM | {s['priority']['MEDIUM']:,} | a Native signal in the "
          "name, from a mixed source such as the identifier ledger or the "
          "unmatched lobbying clients. |")
        A(f"| LOW | {s['priority']['LOW']:,} | single sightings in a discovery "
          "pool built to over-capture (`np_orgs`), or suffix-anchored captures "
          "out of Federal Register prose. Occurrence count does **not** "
          "promote a capture: a frequently repeated fragment is still a "
          "fragment. |")
        A("")
        A("Highest-occurrence HIGH-priority candidates (full list in "
          "`data/clean/entity_candidates_new.csv`):")
        A("")
        A("| Candidate | Prefix | Occurrences | Evidence |")
        A("|---|---|---:|---|")
        for c in sorted([x for x in cand if x["priority"] == "HIGH"],
                        key=lambda r: -r["n_occurrences"])[:25]:
            A(f"| {md(c['candidate_name'])} | `{c['proposed_prefix']}` | "
              f"{c['n_occurrences']:,} | {md(c['evidence'])[:110]} |")
        A("")
    A("## Ambiguities")
    A("")
    at = s["atype"]
    A(f"**{len(amb):,} names** reach two or more spine records. None was "
      "picked. `review/entity_candidates_ambiguous.csv` carries the competing "
      "IDs, the competing canonical names, the question and a blank ruling "
      "column. They are two different problems, so the file has an "
      "`ambiguity_type` column:")
    A("")
    A("| Type | Names | What it means |")
    A("|---|---:|---|")
    A(f"| `competing_entities` | {at['competing_entities']:,} | genuinely two "
      "or more distinct entities are plausible — the Oneida NY / Oneida WI "
      "class of problem. Needs a substantive ruling. |")
    A(f"| `possible_unlinked_spine_pair` | {at['possible_unlinked_spine_pair']:,} | one "
      "`Entity_Master` row and one NEID that look like the same entity, "
      "because `entity_master`'s NEID cell is blank on 250 of 815 rows. Not an "
      "entity ambiguity — it is the open crosswalk gap AGENTS.md lists as "
      "queue item 4 (\"finish NEID fuzzy pass, ~215\"). Restricted to pairs "
      "whose canonical names are *identical* once true corporate-form "
      "synonyms (Inc/Corp/Ltd) are collapsed. Association, Foundation and "
      "Consortium are NOT treated as synonyms of Corporation, so Bristol Bay "
      "Native Corporation and Bristol Bay Native Association stay apart. |")
    A("")
    A("**Byproduct worth taking:** the `possible_unlinked_spine_pair` rows are a "
      "ready-made worklist for that queue item. Ruling them closes the "
      "crosswalk gap and raises the true match rate without any new data pull.")
    A("")
    comp = [a_ for a_ in amb if a_["ambiguity_type"] == "competing_entities"]
    if comp:
        A("Substantive ambiguities, highest occurrence first:")
        A("")
        A("| Candidate | Competing | Occurrences |")
        A("|---|---|---:|")
        for a_ in comp[:25]:
            A(f"| {md(a_['candidate_name'])} | "
              f"{md(a_['competing_names'])[:110]} | "
              f"{a_['n_occurrences']:,} |")
        A("")
    A("## Traps enforced")
    A("")
    A("Each of these has already cost the project once, so each is a hard rule "
      "in the matcher, not a heuristic:")
    A("")
    A("1. **Never match on a single generic token.** A name whose entire "
      "distinctive content is one token from the tribe-word/place-word "
      "collision list (`cherokee`, `creek`, `oneida`, `seminole`, …) and which "
      "carries no tribal form word never reaches a spine entity. Bare "
      "*Cherokee* cannot reach Cherokee Nation; bare *Creek* cannot reach "
      "Berry Creek — the error SBA DSBS made three times.")
    A("2. **Never collapse qualified names.** Containment matching requires the "
      "spine alias to appear as a *contiguous phrase* and every uncovered "
      "token to sit in an explicit allow-list of corporate/programme words. "
      "*Absentee* is not in that list, so **Absentee Shawnee Tribe of "
      "Oklahoma** cannot collapse into **Shawnee Tribe**. Three distinct "
      "governments stay three.")
    A("3. **Oneida NY and Oneida WI.** The full token key retains the state "
      "qualifier and is tried *before* the state-dropped key. Where a name is "
      "genuinely state-ambiguous, both entities compete and the row goes to "
      "the ambiguous register unpicked. The $716M mis-split cannot recur "
      "through this matcher.")
    A("4. **`Pueblo` is Spanish for village.** Names using *pueblo* in its "
      "Spanish sense — *el/la/los pueblo*, *pueblo de*, *Pueblo Viejo* — are "
      "blocked before matching. El Pueblo de Abiquiu Library and PUEBLO VIEJO "
      "DOMINICANA CORPORATION are both caught.")
    A("5. **`Indian` also means South Asian.** Hindu Temple & Indian "
      "Cultural Center, North American Indian Muslim Association and the "
      "campus Indian Student Association are blocked. The word-order tell is "
      "encoded: *American Indian* is Native, *Indian American* is South "
      "Asian.")
    A("6. **`Indian <landform>` is a US place name.** Indian Creek, Indian "
      "Harbor, Indian Paintbrush, Indian Head, Indian River — blocked before "
      "matching.")
    A("7. **Federal agencies and programmes are not entities.** Bureau of "
      "Indian Affairs, Indian Health Service, HUD Office of Native American "
      "Programs, the Tribal Broadband Connectivity Program and the statutes "
      "named after people are all rejected.")
    A("8. **County and town names.** A place/civic regex (county, city of, "
      "school district, chamber of commerce, electric cooperative, volunteer "
      "fire, booster, little league, Falls, Heights, Junction …) blocks the "
      "name outright, and a following-token guard kills *Chippewa Falls*, "
      "*Cherokee County*, *Mohawk Valley*. A softer regex (library, museum, "
      "community college) only *flags*, because tribal colleges and tribal "
      "libraries are real.")
    A("")
    A("## How much of this is noise — honest statement")
    A("")
    A(f"Of {total:,} distinct names, **{unmatched:,} did not match the "
      f"spine** ({unmatched/max(1,total):.1%}). That number is *not* "
      f"{unmatched:,} missing entities. Decomposing it:")
    A("")
    gate = s["gate"]
    rest = unmatched - blocked - len(amb) - len(cand)
    A("The buckets below are mutually exclusive and sum to the unmatched "
      "total:")
    A("")
    A("| Bucket | Names | Share of unmatched |")
    A("|---|---:|---:|")
    A(f"| Hard-blocked by a trap rule (place/civic, `Indian <landform>`, "
      f"South Asian, federal agency, Spanish *pueblo*, bare generic token) | "
      f"{blocked:,} | {blocked/max(1,unmatched):.0%} |")
    A(f"| Competing spine entities — ambiguous, not missing | {len(amb):,} | "
      f"{len(amb)/max(1,unmatched):.0%} |")
    A(f"| Proposed as genuine new entities | {len(cand):,} | "
      f"{len(cand)/max(1,unmatched):.0%} |")
    A(f"| Rejected at the candidate gate | {rest:,} | "
      f"{rest/max(1,unmatched):.0%} |")
    A("")
    A("Gate rejection reasons:")
    A("")
    A("| Reason | Names |")
    A("|---|---:|")
    A(f"| no Native signal in the name and no Native-by-construction source | "
      f"{gate['no_native_signal']:,} |")
    A(f"| already ruled out by an existing nonprofit exclusion ruling | "
      f"{gate['prior_ruling_excluded']:,} |")
    A(f"| not name-shaped (sentence fragment, programme, statute, "
      f"reservation geography, scrape artefact) | "
      f"{gate['not_name_shaped']:,} |")
    A("")
    A(f"**Estimate: roughly {noise_est/max(1,unmatched):.0%} of the unmatched "
      f"harvest — about {noise_est:,} names — is place-name noise, "
      "non-Native counterparties, or ordinary corporate names, not real Native "
      f"entities.** The dominant sources of that noise are "
      "`np_orgs` (an IRS BMF candidate pool built to over-capture), "
      "`identifier_ledger.legal_business_name` (every UEI legal name in the "
      "contracting corpus, most of them non-Native primes and vendors), "
      "`subawards.prime_name`, and `deals.Counterparty_or_Funder` — which is "
      "*supposed* to be mostly non-Native, since it records banks, buyers and "
      "federal agencies on the other side of the deal.")
    A("")
    A(f"The {len(cand):,} proposed candidates are the residue after all of "
      "that: names carrying an explicit Native signal, or drawn from a field "
      "that is Native by construction (ANC ceiling roster, DOI NHO roster, "
      "deal `Native_Party`, compact `tribe`, gaming `tribe`, attributed "
      "lobbying `client_name`), which nonetheless reach no spine entity. Even "
      "there, expect a meaningful minority to be DBAs, subsidiaries of "
      "entities already on the spine, or historical name variants rather than "
      "new governments — which is exactly why they are proposals with a blank "
      "ruling column and not minted IDs. Minting an ID for something that "
      "turns out to be a county fair committee is worse than leaving it "
      "unassigned.")
    A("")
    A("## Files written")
    A("")
    A("| File | Rows | What it is |")
    A("|---|---:|---|")
    A(f"| `data/clean/entity_name_harvest.csv` | {total:,} | every distinct "
      "normalized name observed, with occurrence counts, sources, year range "
      "and match verdict |")
    A(f"| `data/clean/entity_candidates_new.csv` | {len(cand):,} | matched "
      "nothing, looks genuinely Native, proposed prefix and class, blank "
      "`YOUR_RULING` |")
    A(f"| `review/entity_candidates_ambiguous.csv` | {len(amb):,} | two or "
      "more spine entities plausible; never picked |")
    A("| `logs/35_entity_harvest.log` | — | full run trace |")
    A("")
    A("This stage writes only those four files. Nothing in `data/spine/`, no "
      "`data/clean/cedar_*`, not `entity_master.csv`, not "
      "`review/cedar_review*.html` was opened for writing. The existing "
      "nonprofit exclusion rulings are read and **honoured** — a name already "
      "ruled out can never resurface as a new candidate.")
    A("")

    p = DOCS / "ENTITY_HARVEST_LOG.md"
    p.write_text("\n".join(L), encoding="utf-8")
    log(f"  wrote {p.relative_to(CEDAR)}")


if __name__ == "__main__":
    main()
