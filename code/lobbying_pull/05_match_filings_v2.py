"""
Match Senate LDA filings (raw_filings.jsonl) to canonical Native entities -- v2.

Cedar Press Dataset 4 (Native Influence / Lobbying).
Self-contained: reads and writes only inside `Cedar Press`.

Inputs
  code/lobbying_pull/raw_filings.jsonl               pulled filings (04_pull_lda_v2.py)
  data/raw/external/canonical_tribe_table.csv        687 canonical Native entities
  data/raw/external/anc_tribal_subsidiary_lookup.csv subsidiary -> parent rows

Outputs
  data/clean/native_entity_lobbying_disclosures.csv  one row per matched filing
  data/clean/tribe_year_lobbying_panel.csv           entity x year aggregate
  data/clean/lobbying_unmatched_clients.csv          unmatched clients, ranked by spend
  review/lobbying_ambiguous_2026-08-05.csv           clients needing an Elijah ruling


WHY v2 EXISTS
=============
v1 compared an LDA client name to a canonical alias in one direction only: the
alias had to appear, verbatim and token-aligned, inside the client name. That
is the right instinct and the wrong implementation, because the two sides are
written in different registers:

    LDA client name            canonical_tribe_table
    ---------------            ---------------------
    HOPI TRIBE                 Hopi Tribe of Arizona          (entity_namefull)
    YUROK TRIBE                Yurok Tribe of the Yurok Reservation, California
    MOHEGAN TRIBE OF CT        Mohegan Tribe of Indians of Connecticut
    ST REGIS MOHAWK TRIBE      Saint Regis Mohawk Tribe
    CONFEDERATED TRIBES OF     Confederated Tribes of the Grand Ronde
      THE GRAND RONDE OF OR      Community of Oregon

Every one of these is the same government under two spellings. None of them can
be reached by one-directional containment: the canonical string is LONGER than
the client string, so it is not contained in it, and the short alias that would
be contained ("Hopi", 4 characters, 1 token) is below the >=12-char / >=2-token
containment floor that exists to stop the Cherokee Inc. trap.

v2 normalizes BOTH SIDES to a comparable form and compares token SETS, so the
direction of the extra words stops mattering.


THE NORMALISATION
=================
`norm()`     casefold; & -> and; drop apostrophes (o'odham -> oodham); dashes and
             punctuation -> space; collapse whitespace; expand the abbreviations
             that actually occur (st -> saint, ste -> sainte, ft -> fort,
             mt -> mount); expand a trailing two-letter USPS code ("of OK").

`core()`     norm minus STRUCTURAL tokens (tribe/nation/band/indians/community/
             reservation/rancheria/pueblo/village/confederated/of/the/...) and
             minus a TRAILING state qualifier, peeled iteratively. State words
             are removed only in trailing position, never in leading or medial
             position, because there they are the identity: Colorado River,
             Iowa, Alabama-Coushatta, Delaware. What remains is the stem:

                 HOPI TRIBE                              -> {hopi}
                 Hopi Tribe of Arizona                   -> {hopi}
                 CONFEDERATED TRIBES OF THE GRAND RONDE
                   OF OREGON                             -> {grand, ronde}
                 Confederated Tribes of the Grand Ronde
                   Community of Oregon                   -> {grand, ronde}

Trailing state names are peeled on BOTH sides (symmetric, so it cannot
manufacture a match), and captured separately as `qualifier_states` when they
appear in an identifying position -- after "of"/"in", or trailing. The state is
then available as a TIEBREAKER and only as a tiebreaker.


THE PRECISION GUARDS -- these are the point, not the decoration
==============================================================
Loosening the comparison without loosening the standard of proof requires seven
guards, all of which refuse rather than guess. Each one was written because it
caught a specific wrong answer in the pulled data, not on speculation:

  G1  CONTESTED SINGLE TOKEN. A one-token core is usable only if that token
      appears in the core of at most 2 canonical entities. Measured on the
      687-row table: cherokee = 11 entities, creek = 14, sioux = 13, paiute = 24,
      chippewa = 21 -- all contested, all refused. hopi = 1, mohegan = 1,
      yurok = 2, oneida = 2 -- distinctive, allowed. This is the Cherokee Inc.
      trap and the Berry Creek trap expressed as a measurement on the entity
      table rather than as a hand-maintained blocklist.

  G2  AMBIGUITY REFUSES. If a core resolves to two or more entities, nothing is
      matched. The client is written out with `why_unmatched=ambiguous_multiple`
      and every candidate listed in `competing_entity_ids`, and it is queued for
      an Elijah ruling in review/lobbying_ambiguous_2026-08-05.csv. The state
      tiebreaker is allowed to resolve such a set ONLY when the client name
      itself carries an explicit state qualifier and exactly one candidate sits
      in that state -- ONEIDA TRIBE OF INDIANS OF **WISCONSIN** against Oneida NY
      and Oneida WI. That is decisive evidence in the name, not a coin flip.
      With no state in the name, "ONEIDA NATION" stays unmatched.

  G3  LEADING-QUALIFIER CONFLICT (inherited from v1, retained). A distinctive
      token standing BEFORE the matched stem that belongs to a different
      entity's vocabulary refuses the match: "ABSENTEE Shawnee" is not the
      Shawnee Tribe. Tokens standing AFTER are descriptors and do not refuse.

  G4  Core CONTAINMENT (the loosest tier) requires a core of >=2 tokens. A
      single-token core is only ever matched by exact core-set equality, never
      by containment -- so "NAVAJO NATION WASHINGTON OFFICE" does not silently
      become the Navajo Nation; it goes to the review queue as
      `single_token_core_needs_ruling` with its one candidate named.

  G5  SIBLING FAMILY. A containment alias may resolve to one entity at the
      surface while its STEM is shared by a family of distinct governments.
      "SAC FOX NATION MESKWAKI TRIBE" matched the Sac and Fox Nation of
      OKLAHOMA on the alias "sac fox nation" -- but Meskwaki is the Sac & Fox
      Tribe of the Mississippi in IOWA. The stem {sac, fox} belongs to three
      separate federally recognized tribes, so the match is refused unless the
      client name carries evidence that separates them: an explicit state, or a
      token owned by a proper subset of the family ("WHITE MOUNTAIN **APACHE**"
      against the Alaska village that shares the "white mountain" stem).
      `meskwaki` appears nowhere in the entity table, so nothing separates them
      and the client is queued for a ruling. This guard was added because the
      matcher produced that wrong answer on the real pull, not in the abstract.

  G6  NICKNAME UNDERSPECIFICATION. `canonical_name` and `biatld_nameshort`
      are SHORT FORMS. Matching on one of them can pick the wrong government
      when the short form is a common place name. Live example from the pull:

          client  PUEBLO OF SAN JUAN            (New Mexico -- Ohkay Owingeh,
                                                 renamed from San Juan Pueblo)
          alias   biatld_nameshort "San Juan"
          entity  TRBF-SNJUAN-00 "San Juan Southern Paiute Tribe of ARIZONA"

      Two different tribes in two different states. The check: take the HEAD of
      `entity_namefull` -- everything before its first " of " -- and require
      that the client's stem not be a strict subset of it. The Arizona tribe's
      head is "San Juan Southern Paiute Tribe"; the client said neither
      "southern" nor "paiute", so the match is refused and queued. Hopi, Yurok,
      Mohegan, Grand Ronde, Quechan and Colorado River all pass unchanged,
      because their client stems equal their head stems exactly.

      (The underlying cause is a gap in the entity table: Ohkay Owingeh's row
      carries no `fedreg_nameprev`, so its former name "San Juan Pueblo" is not
      an alias anywhere. The guard turns a silent wrong answer into a question.)

  G7  A SECOND GOVERNMENT NAMED IN THE SAME CLIENT STRING. "PUEBLO OF TESUQUE
      AND PUEBLO OF POJOAQUE" is one client naming two pueblos; the matcher
      booked it to Pojoaque and dropped Tesuque. And "FOND DU LAC BAND OF LAKE
      SUPERIOR CHIPPEWA" booked to the Minnesota Chippewa Tribe while "MILLE
      LACS BAND" was refused by G5 -- the same parent-versus-band question
      answered two different ways, because the parent's entity_namefull
      enumerates its six component bands and so carries their aliases. Both now
      go to the queue. Disjoint token spans keep this from firing on nesting.

Every matched row records `matched_alias` (the exact normalized string that
matched) and `attribution_method` (which tier fired), so every attribution is
reconstructable from the output alone.


SPEND ACCOUNTING (unchanged from v1, LOBBYING_DATA_PLAN.md hygiene note)
LD-2 reports carry EITHER `income` (an outside registrant billing a client) OR
`expenses` (a self-filing entity reporting in-house costs). They are never
summed. `spend_basis` records which field was used; `self_filed` flags filings
where the registrant IS the client.
"""
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent                      # ...\Cedar Press
RAW = HERE / "raw_filings.jsonl"
CANON = ROOT / "data" / "raw" / "external" / "canonical_tribe_table.csv"
SUBS = ROOT / "data" / "raw" / "external" / "anc_tribal_subsidiary_lookup.csv"
OUT_DIR = ROOT / "data" / "clean"
OUT_FILE = OUT_DIR / "native_entity_lobbying_disclosures.csv"
PANEL_FILE = OUT_DIR / "tribe_year_lobbying_panel.csv"
UNMATCHED_FILE = OUT_DIR / "lobbying_unmatched_clients.csv"
REVIEW_FILE = ROOT / "review" / "lobbying_ambiguous_2026-08-05.csv"

MIN_SUBSTRING_LEN = 12
CONTESTED_AT = 3          # a core token owned by >= this many entities is unusable alone
MIN_SOLO_TOKEN_LEN = 4

STOPWORDS = {"of", "the", "and", "at", "in", "for", "a", "an", "on"}

# Dropped to form the CORE. These are the words that describe what KIND of thing
# an entity is, not WHICH one it is; they differ freely between the LDA register
# and the Federal Register register and carry no identifying information.
STRUCTURAL = STOPWORDS | {
    "tribe", "tribes", "tribal", "nation", "nations", "band", "bands",
    "indian", "indians", "native", "natives", "american", "americans",
    "people", "peoples", "community", "communities", "reservation",
    "reservations", "reserve", "rancheria", "rancherias", "pueblo", "pueblos",
    "village", "villages", "colony", "colonies", "confederated", "federated",
    "confederate",   # LDA filers type this for "confederated"; no identity
    "council", "councils", "band's", "nations'", "oyate", "state", "states",
}

# Never usable as an alias on its own (kept from v1 for the alias index).
GENERIC_TERMS = STRUCTURAL | {
    "association", "corporation", "corp", "incorporated", "inc", "llc", "lp",
    "company", "co", "group", "consortium", "chairman", "chief",
}

# Carry no identity information for the leading-qualifier guard.
GEO_IGNORE = {
    "usa", "us", "united", "new", "government", "governments", "office",
    "offices", "authority", "agency", "enterprise", "enterprises",
    "development", "holdings", "services", "service", "business", "businesses",
    "industries", "solutions", "gaming", "casino", "resort", "management",
    "health", "housing", "energy",
}

NATIVE_TOKENS = {
    "tribe", "tribes", "tribal", "indian", "indians", "native", "natives",
    "pueblo", "rancheria", "rancherias", "nation", "band", "intertribal",
    "aleut", "inupiat", "yupik", "athabascan", "hawaiian", "chippewa",
    "ojibwe", "ojibwa", "sioux", "lakota", "dakota", "nakota", "apache",
    "navajo", "dine", "cherokee", "choctaw", "chickasaw", "creek", "seminole",
    "shoshone", "paiute", "pomo", "miwok", "yakama", "salish", "kootenai",
    "arapaho", "cheyenne", "comanche", "kiowa", "osage", "ponca", "potawatomi",
    "menominee", "oneida", "mohawk", "seneca", "cayuga", "onondaga",
    "tuscarora", "wampanoag", "passamaquoddy", "penobscot", "lumbee",
    "catawba", "miccosukee", "muscogee", "mohegan", "pequot", "narragansett",
    "anishinaabe", "haudenosaunee", "ancsa", "anc", "nho", "aleutian",
    "tlingit", "haida", "tsimshian", "yupiit", "inuit", "eskimo", "ancsa",
}

USPS = {
    "al": "alabama", "ak": "alaska", "az": "arizona", "ar": "arkansas",
    "ca": "california", "co": "colorado", "ct": "connecticut", "de": "delaware",
    "fl": "florida", "ga": "georgia", "hi": "hawaii", "id": "idaho",
    "il": "illinois", "in": "indiana", "ia": "iowa", "ks": "kansas",
    "ky": "kentucky", "la": "louisiana", "me": "maine", "md": "maryland",
    "ma": "massachusetts", "mi": "michigan", "mn": "minnesota",
    "ms": "mississippi", "mo": "missouri", "mt": "montana", "ne": "nebraska",
    "nv": "nevada", "nh": "new hampshire", "nj": "new jersey",
    "nm": "new mexico", "ny": "new york", "nc": "north carolina",
    "nd": "north dakota", "oh": "ohio", "ok": "oklahoma", "or": "oregon",
    "pa": "pennsylvania", "ri": "rhode island", "sc": "south carolina",
    "sd": "south dakota", "tn": "tennessee", "tx": "texas", "ut": "utah",
    "vt": "vermont", "va": "virginia", "wa": "washington", "wi": "wisconsin",
    "wv": "west virginia", "wy": "wyoming",
}
STATE_TO_USPS = {v: k for k, v in USPS.items()}
# Longest-first so "north dakota" is consumed before "dakota" is ever considered.
STATE_NAMES = sorted(STATE_TO_USPS, key=lambda s: -len(s))
# A state is an identity QUALIFIER when it follows of/in, or ends the name.
QUALIFIER_STATE_RE = re.compile(
    r"(?:\b(?:of|in|for)\s+(?:the\s+)?(?:state\s+of\s+)?(" + "|".join(re.escape(s) for s in STATE_NAMES) + r")\b)"
    r"|(?:(" + "|".join(re.escape(s) for s in STATE_NAMES) + r")\s*$)")

ABBREV = {"st": "saint", "ste": "sainte", "ft": "fort", "mt": "mount",
          # legal-form suffixes: spelling is normalized on BOTH sides, but the
          # suffix is never DELETED on the client side. Deleting it is the
          # Cherokee Inc. trap in its purest form -- "HO-CHUNK INC" minus "INC"
          # is "Ho-Chunk", which is the name of a DIFFERENT tribe (the Ho-Chunk
          # Nation of Wisconsin; Ho-Chunk Inc is the Winnebago Tribe of
          # Nebraska's corporation).
          "incorporated": "inc", "corporation": "corp",
          "limited": "ltd", "company": "co"}

CORP_SUFFIX = {"inc", "corp", "ltd", "co", "llc", "lp", "llp", "plc"}


def log(msg):
    print(msg, flush=True)


def norm(s, tight=False):
    """Casefold, expand abbreviations, punctuation -> space, collapse."""
    if not s:
        return ""
    s = s.lower().strip()
    s = s.replace("&", " and ")
    s = s.replace("'", "").replace("’", "")          # o'odham -> oodham
    s = re.sub(r"[‐‑‒–—―\-]", "" if tight else " ", s)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = " ".join(ABBREV.get(t, t) for t in s.split())
    # trailing two-letter USPS code: "eastern shawnee tribe of ok",
    # "kickapoo tribe in ks", "ewiaapaayp tribe of ca"
    m = re.search(r"\b(?:of|in) (?:the )?([a-z]{2})$", s)
    if m and m.group(1) in USPS:
        s = s[:m.start(1)] + USPS[m.group(1)]
    return s


def glue_initials(n):
    """
    Merge a stray single-letter token into the one after it.

    Apostrophes are removed during normalization, which turns "Coeur d'Alene"
    into "coeur d alene" on one side and leaves "coeur dalene" on the other
    depending on how the filer typed it. LDA filers type both. A single-letter
    token never carries identity, so gluing it forward is safe and it is applied
    to both sides.
    """
    toks = n.split()
    out = []
    i = 0
    while i < len(toks):
        if len(toks[i]) == 1 and i + 1 < len(toks):
            out.append(toks[i] + toks[i + 1])
            i += 2
        else:
            out.append(toks[i])
            i += 1
    return " ".join(out)


def skeleton(n):
    return " ".join(t for t in n.split() if t not in STOPWORDS)


def qualifier_states(n):
    """USPS codes for states appearing in an identifying position in `n`."""
    out = set()
    for m in QUALIFIER_STATE_RE.finditer(n):
        name = m.group(1) or m.group(2)
        if name:
            out.add(STATE_TO_USPS[name])
    return out


TRAILING_CONNECTIVES = {"and", "of", "in", "the", "a", "for", "on", "at", "or"}
_STATE_PARTS = [s.split() for s in STATE_NAMES]      # already longest-first


def strip_trailing_geo(n):
    """
    Iteratively remove a TRAILING state qualifier and the connectives holding it on.

    Position matters, and stripping states everywhere is wrong. A state name in
    trailing position is a jurisdictional qualifier ("Hopi Tribe OF ARIZONA");
    the same word in leading or medial position is part of the identity:

        COLORADO RIVER INDIAN TRIBES   -> {colorado, river}   NOT {river}
        IOWA TRIBE OF KANSAS AND NEBRASKA -> {iowa}           NOT {}
        ALABAMA-COUSHATTA TRIBE OF TEXAS  -> {alabama, coushatta}
        DELAWARE NATION                   -> {delaware}       NOT {}

    An earlier draft of this function stripped every state name anywhere in the
    string. It silently emptied the core of every tribe whose own name is a
    state word -- Colorado River, Iowa, Alabama-Coushatta, Delaware -- which is
    a large and completely invisible class of false negatives.

    Iterating matters too: "Navajo Nation, Arizona, New Mexico, & Utah" peels
    utah -> and -> new mexico -> arizona and lands on "navajo nation".
    """
    toks = n.split()
    changed = True
    while changed and toks:
        changed = False
        for parts in _STATE_PARTS:
            k = len(parts)
            if len(toks) > k and toks[-k:] == parts:
                del toks[-k:]
                changed = True
                break
        if changed:
            continue
        if len(toks) > 1 and toks[-1] in TRAILING_CONNECTIVES:
            toks.pop()
            changed = True
    return " ".join(toks)


def core_tokens(n):
    """Identifying stem: normalized name minus trailing geography minus STRUCTURAL."""
    return frozenset(t for t in strip_trailing_geo(n).split()
                     if t not in STRUCTURAL and len(t) > 1)


TYPE_WORDS = {"tribe", "tribes", "nation", "nations", "band", "bands",
              "community", "communities", "village", "villages", "pueblo",
              "rancheria", "colony", "corporation", "association"}


def _name_head(full):
    """
    The identifying head of a legal name: everything up to and including the
    first entity-TYPE word, or up to the first " of " if that comes sooner.

    G6 originally cut at " of " alone. That reads
    "Metlakatla Indian Community, Annette Island Reserve" as having the whole
    string for a head, so the client `METLAKATLA INDIAN COMMUNITY` -- which is
    the entity's exact official name, just without the reserve clause -- looked
    like an underspecified nickname and was refused. Cutting at the type word
    gives the head "Metlakatla Indian Community", which the client matches
    exactly.

    "San Juan Southern Paiute Tribe of Arizona" still yields the head
    "San Juan Southern Paiute Tribe", so `PUEBLO OF SAN JUAN` is still refused.
    """
    toks = norm(full).split()
    for i, t in enumerate(toks):
        if t in TYPE_WORDS:
            return " ".join(toks[:i + 1])
        if t == "of":
            return " ".join(toks[:i])
    return full


def _strip_geo_tail(raw_name):
    """
    Drop a trailing comma-qualifier ONLY when it is purely geographic.

    An unconditional "drop everything after the last comma" is not safe on this
    table. `entity_namefull` for CNSF-NAVAJO-RM is
        "Navajo Nation, Arizona, New Mexico, & Utah - Ramah Navajo Chapter"
    and the unconditional strip turns it into "Navajo Nation, Arizona,
    New Mexico" -- i.e. it manufactures a "Navajo Nation" alias for the Ramah
    Navajo CHAPTER, a constituency entity inside the Navajo Nation. That
    fabricated alias then collides with the real Navajo Nation row and sends the
    single largest tribal filer in the data to the ambiguity queue.

    So the tail is only removed when every token in it is a state name or a
    structural filler -- which is the only case the rule was ever meant for
    ("Yurok Tribe of the Yurok Reservation, California").
    """
    prev = None
    cur = raw_name
    while cur != prev and "," in cur:
        prev = cur
        head, _, tail = cur.rpartition(",")
        toks = norm(tail).split()
        if toks and all(t in STATE_TO_USPS or t in STRUCTURAL for t in toks):
            cur = head
    return cur


def name_forms(raw_name):
    """Safe, meaning-preserving surface forms of one entity name."""
    out = set()
    geo_stripped = _strip_geo_tail(raw_name)
    for tight in (False, True):
        base = norm(raw_name, tight)
        if base:
            out.add(base)
            out.add(glue_initials(base))
            # ENTITY SIDE ONLY: a variant with trailing legal-form suffixes
            # dropped, so "NANA Regional Corporation, Incorporated" can be
            # reached by "NANA REGIONAL CORPORATION". Requires >=2 tokens to
            # remain, which is what stops the dangerous collapses:
            # "Koniag, Incorporated"/"Sealaska Corporation"/"Aleut Corporation"
            # would reduce to a single bare token and are refused here.
            toks = base.split()
            while len(toks) > 1 and toks[-1] in CORP_SUFFIX:
                toks.pop()
            if toks and len(toks) < len(base.split()):
                out.add(" ".join(toks))
        if geo_stripped != raw_name:              # trailing ", Montana" qualifier
            t = norm(geo_stripped, tight)
            if t:
                out.add(t)
        if "(" in raw_name:                       # "Muscogee (Creek) Nation"
            t = norm(re.sub(r"\([^)]*\)", " ", raw_name), tight)
            if t:
                out.add(t)
    return {o for o in out if o}


def usable_alias(n):
    if not n or len(n) < 4:
        return False
    return not set(n.split()).issubset(GENERIC_TERMS)


def distinctive(tokens):
    return {t for t in tokens
            if t not in GENERIC_TERMS and t not in GEO_IGNORE
            and t not in STATE_TO_USPS and len(t) > 2}


class Index:
    def __init__(self):
        self.exact = defaultdict(set)        # normalized full alias -> ids
        self.skel = defaultdict(set)         # stopword-stripped alias -> ids
        self.core = defaultdict(set)         # frozenset core -> ids
        self.core_src = {}                   # (core, id) -> the alias it came from
        self.token_vocab = defaultdict(set)  # distinctive token -> ids
        self.core_token_vocab = defaultdict(set)
        self.head_core = {}                  # id -> stem of entity_namefull head
        self.meta = {}

    def add(self, entity_id, raw_name):
        for form in name_forms(raw_name):
            if usable_alias(form):
                self.exact[form].add(entity_id)
                sk = skeleton(form)
                if usable_alias(sk):
                    self.skel[sk].add(entity_id)
                for t in distinctive(form.split()):
                    self.token_vocab[t].add(entity_id)
            c = core_tokens(form)
            if c:
                self.core[c].add(entity_id)
                self.core_src.setdefault((c, entity_id), form)
                for t in c:
                    self.core_token_vocab[t].add(entity_id)

    def longest_contained(self, n):
        padded = f" {skeleton(n)} "
        best = None
        for alias, ids in self.skel.items():
            if len(alias) < MIN_SUBSTRING_LEN or " " not in alias:
                continue
            if f" {alias} " not in padded:
                continue
            if best is None or len(alias) > len(best[0]):
                best = (alias, ids)
        return best if best else (None, None)

    def contested(self, token):
        return len(self.core_token_vocab.get(token, ())) >= CONTESTED_AT


def build_canonical_index():
    idx = Index()
    with CANON.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            tid = (row.get("tribe_id") or "").strip()
            if not tid:
                continue
            idx.meta[tid] = {
                "canonical_name": row.get("canonical_name", ""),
                "entity_type": row.get("entity_type", ""),
                "entity_state": (row.get("entity_state") or "").strip().lower(),
            }
            full = (row.get("entity_namefull") or "").strip()
            if full:
                hc = core_tokens(norm(_name_head(full))) or core_tokens(norm(full))
                if hc:
                    idx.head_core[tid] = hc
            for fld in ("canonical_name", "entity_namefull", "fedreg_nameaka",
                        "fedreg_nameprev", "biatld_nameshort"):
                v = (row.get(fld) or "").strip()
                if not v:
                    continue
                for part in re.split(r"[;|/]", v):
                    part = part.strip()
                    if part:
                        idx.add(tid, part)
    return idx


_PARENT_REMAP = {}
_PARENT_UNRESOLVED = {}


def build_subsidiary_index(canon_idx):
    """Subsidiary name -> parent entity id (columns are parent_entity_id /
    parent_entity_name, not parent_tribe_id -- the v1 bug)."""
    idx = Index()
    if not SUBS.exists():
        log(f"  WARNING: {SUBS} missing; subsidiary tier disabled")
        return idx
    with SUBS.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            name = (row.get("subsidiary_name") or "").strip()
            pid = (row.get("parent_entity_id") or "").strip()
            pname = (row.get("parent_entity_name") or "").strip()
            if not name or not pid:
                continue
            if pid not in canon_idx.meta:
                # `anc_tribal_subsidiary_lookup.csv` asserts parent ids that are
                # not in the entity spine -- TRBF-WBGNON-00 "Winnebago Tribe of
                # Nebraska" against the spine's TRBF-WNNBGO-00 "Winnebago",
                # TRBF-CHCNAO-00 against TRBF-CTWNAT-00, and so on. Left alone,
                # Ho-Chunk Inc books to a phantom id while the Winnebago Tribe
                # itself books to the real one, splitting one government across
                # two ids in the panel and quietly halving both.
                #
                # Resolve the parent NAME through this same matcher rather than
                # hand-mapping ids. If it resolves to exactly one spine entity,
                # remap; otherwise keep the asserted id and record it.
                resolved = match_client(pname, canon_idx, Index())["entity_id"]
                if resolved:
                    _PARENT_REMAP[pid] = (resolved, pname)
                    pid = resolved
                else:
                    _PARENT_UNRESOLVED[pid] = pname
                    canon_idx.meta[pid] = {
                        "canonical_name": pname,
                        "entity_type": row.get("parent_entity_type", ""),
                        "entity_state": "",
                    }
            elif pid in _PARENT_REMAP:
                pid = _PARENT_REMAP[pid][0]
            idx.meta[pid] = canon_idx.meta[pid]
            idx.add(pid, name)
    return idx


def _spans(hay_tokens, needle_tokens):
    """Token-index spans where needle appears token-aligned inside hay."""
    k = len(needle_tokens)
    return [(i, i + k) for i in range(len(hay_tokens) - k + 1)
            if hay_tokens[i:i + k] == needle_tokens]


def co_named_entities(norm_client, matched_alias, entity_id, canon_idx):
    """
    G7: is a SECOND government named in this same client string?

    Two shapes, both found in the pulled data.

    (a) JOINT FILINGS. `PUEBLO OF TESUQUE AND PUEBLO OF POJOAQUE` is one LDA
        client naming two separate pueblos. The matcher took the longest alias,
        booked the whole filing to Pojoaque, and silently dropped Tesuque. The
        test is whether another entity's alias also appears in the client
        string in a span DISJOINT from the matched one. Disjointness is what
        keeps this from firing on nesting: "shawnee tribe" sits inside
        "eastern shawnee tribe of oklahoma", but it overlaps, so it is nesting
        rather than a second entity and does not refuse.

    (b) PARENT vs CONSTITUENT BAND. The entity ids encode this:
        `TRBF-MINNCH-00` is the Minnesota Chippewa Tribe and `CNSF-MINNCH-FL`
        is its Fond du Lac component band -- same middle segment, different
        prefix. `TRBF-MINNCH-00`'s own `entity_namefull` enumerates its six
        component bands, so the parent picks up aliases that ARE the bands.
        `FOND DU LAC BAND OF LAKE SUPERIOR CHIPPEWA` therefore booked to the
        parent while `MILLE LACS BAND OF OJIBWE INDIANS` was refused by G5 --
        the same question answered two different ways. Whether a band's filing
        belongs to the band or the tribe is a real attribution question with a
        real answer, and it is one ruling that settles all six bands at once.

    Returns the competing ids, or an empty set.
    """
    ctoks = skeleton(norm_client).split()
    ccore = core_tokens(norm_client)
    matched_spans = _spans(ctoks, matched_alias.split())
    others = set()

    for alias, ids in canon_idx.skel.items():
        if len(alias) < MIN_SUBSTRING_LEN or " " not in alias:
            continue
        if entity_id in ids:
            continue
        sp = _spans(ctoks, alias.split())
        if not sp:
            continue
        if any(not (b <= c or d <= a) for (a, b) in sp for (c, d) in matched_spans):
            continue                      # overlaps the matched alias: nesting
        others |= ids

    mid = entity_id.split("-")[1] if entity_id.count("-") >= 2 else None
    if mid:
        for other in canon_idx.meta:
            if other == entity_id or not other.startswith(("CNSF-", "CNSS-")):
                continue
            if other.split("-")[1] != mid:
                continue
            ocore = min((c for c, ids in canon_idx.core.items() if other in ids),
                        key=len, default=None)
            if ocore and len(ocore) >= 2 and ocore <= ccore:
                others.add(other)
    return others


def sibling_family(alias, canon_idx):
    """
    G5: the set of entities whose CORE equals the core of a containment alias.

    A containment alias can resolve to exactly one entity at the surface level
    while its identifying STEM is shared by a whole family of distinct
    governments. Live example from the pulled data:

        client  SAC FOX NATION MESKWAKI TRIBE
        alias   "sac fox nation"   -> uniquely TRBF-SCFXOK-00 (Oklahoma)
        stem    {sac, fox}         -> TRBF-SCFXMO-00, TRBF-SCFXMS-00, TRBF-SCFXOK-00

    Meskwaki is the Sac & Fox Tribe of the Mississippi in IOWA, not the Sac and
    Fox Nation of Oklahoma -- two separate federally recognized governments. The
    leading-qualifier guard cannot catch it: "meskwaki" stands AFTER the alias
    and does not appear anywhere in the canonical table's vocabulary, so there
    is nothing for it to conflict with.

    The family test does catch it, because it asks the right question: is this
    stem shared? If it is, only an explicit state qualifier may select a member;
    otherwise the client is genuinely ambiguous and goes to Elijah.
    """
    return canon_idx.core.get(core_tokens(alias), set())


def leading_conflict(n, alias_tokens, entity_id, canon_idx, meta):
    """G3: distinctive token BEFORE the stem belonging to another entity."""
    toks = skeleton(n).split()
    atoks = list(alias_tokens)
    start = None
    for i in range(len(toks)):
        if toks[i] in atoks:
            start = i
            break
    hits = {}
    if start:
        for t in distinctive(set(toks[:start])):
            owners = canon_idx.token_vocab.get(t)
            if owners and entity_id not in owners:
                hits[t] = owners
    if not hits and meta:
        qs = qualifier_states(n)
        ent_st = meta.get("entity_state") or ""
        if qs and ent_st and ent_st not in qs:
            hits[f"of_{sorted(qs)[0]}"] = set()
    return hits


def match_client(client_name, canon_idx, sub_idx):
    def out(eid=None, method="", alias="", conf="", reason="", competing=""):
        return {"entity_id": eid, "method": method, "alias": alias,
                "confidence": conf, "reason": reason, "competing": competing}

    forms = []
    for tight in (False, True):
        v = norm(client_name, tight)
        for cand in (v, glue_initials(v)):
            if cand and cand not in forms:
                forms.append(cand)
    if not forms:
        return out(reason="blank_client_name")

    qs = set()
    for f in forms:
        qs |= qualifier_states(f)

    def family_ok(alias, eid, canon_idx, form):
        """
        G5: refuse a containment match whose stem is shared by sibling
        governments, UNLESS the client name itself carries evidence that picks
        one member out of the family. Two admissible kinds of evidence, both of
        which must be present in the client name AND in the entity table:

          * an explicit state qualifier  ("...OF TEXAS" -> Kickapoo of Texas)
          * a discriminating token owned by a proper subset of the family
            ("WHITE MOUNTAIN **APACHE** TRIBE": `apache` belongs to the Arizona
            tribe's vocabulary and not to the Alaska village that shares the
            "white mountain" stem)

        "SAC FOX NATION MESKWAKI TRIBE" survives neither test -- `meskwaki`
        appears in no entity's vocabulary at all -- so it is refused and queued.
        Evidence narrows; absence of evidence never does.
        """
        fam = sibling_family(alias, canon_idx)
        if len(fam) <= 1 or eid not in fam:
            return None
        cand = set(fam)
        if qs:
            narrowed = {e for e in cand
                        if (canon_idx.meta.get(e, {}).get("entity_state") or "") in qs}
            if len(narrowed) == 1:
                cand = narrowed
        if len(cand) > 1:
            for t in distinctive(set(skeleton(form).split())):
                owners = canon_idx.token_vocab.get(t, set()) & fam
                if owners and owners != fam and cand & owners:
                    cand &= owners
        if len(cand) == 1 and next(iter(cand)) == eid:
            return None
        return out(reason="ambiguous_sibling_family", alias=alias,
                   competing="|".join(sorted(fam)))

    def resolve(ids, method, alias, conf):
        """Shared ambiguity/tiebreak policy (G2)."""
        ids = set(ids)
        if len(ids) == 1:
            return out(next(iter(ids)), method, alias, conf)
        if qs:
            narrowed = {e for e in ids
                        if (canon_idx.meta.get(e, {}).get("entity_state") or "") in qs}
            if len(narrowed) == 1:
                return out(next(iter(narrowed)), method + "_plus_state_qualifier",
                           alias, conf)
        return out(reason="ambiguous_multiple", alias=alias,
                   competing="|".join(sorted(ids)))

    # ---- T1 exact normalized equality -------------------------------------
    for form in forms:
        ids = canon_idx.exact.get(form)
        if ids:
            return resolve(ids, "exact_normalized", form, "high")

    # ---- T2 stopword-stripped equality ------------------------------------
    for form in forms:
        ids = canon_idx.skel.get(skeleton(form))
        if ids:
            return resolve(ids, "exact_normalized_skeleton", skeleton(form), "high")

    # ---- T3 CORE TOKEN-SET EQUALITY (the v2 fix) --------------------------
    for form in forms:
        c = core_tokens(form)
        if not c:
            continue
        ids = canon_idx.core.get(c)
        if not ids:
            continue
        # G1: a lone core token must be distinctive on the entity table --
        # UNLESS an explicit state qualifier in the client name picks exactly
        # one of the entities carrying that core ("KICKAPOO TRIBE OF TX").
        if len(c) == 1:
            tok = next(iter(c))
            if canon_idx.contested(tok) or len(tok) < MIN_SOLO_TOKEN_LEN:
                narrowed = {e for e in ids
                            if (canon_idx.meta.get(e, {}).get("entity_state") or "") in qs} if qs else set()
                if len(narrowed) != 1:
                    return out(reason="generic_single_token",
                               alias=tok,
                               competing="|".join(sorted(canon_idx.core_token_vocab.get(tok, ()))))
        r = resolve(ids, "core_token_set", " ".join(sorted(c)), "high")
        if r["entity_id"]:
            hc = canon_idx.head_core.get(r["entity_id"])
            if hc and c < hc:
                return out(reason="nickname_alias_underspecified",
                           alias=" ".join(sorted(c)),
                           competing=r["entity_id"])
            conflicts = leading_conflict(form, c, r["entity_id"], canon_idx,
                                         canon_idx.meta.get(r["entity_id"]))
            if conflicts:
                return out(reason=("state_conflict"
                                   if all(k.startswith("of_") for k in conflicts)
                                   else "qualifier_conflict"),
                           alias=f"{' '.join(sorted(c))} [uncovered: {','.join(sorted(conflicts))}]",
                           competing="|".join(sorted(
                               {e for o in conflicts.values() for e in o})))
        return r

    # ---- T4 exact subsidiary name -----------------------------------------
    for form in forms:
        for table, key in ((sub_idx.exact, form), (sub_idx.skel, skeleton(form))):
            ids = table.get(key)
            if ids:
                if len(ids) == 1:
                    return out(next(iter(ids)), "exact_subsidiary", key, "high")
                return out(reason="ambiguous_subsidiary", alias=key,
                           competing="|".join(sorted(ids)))
    for form in forms:
        c = core_tokens(form)
        if c and c in sub_idx.core:
            ids = sub_idx.core[c]
            if len(ids) == 1 and not (len(c) == 1 and canon_idx.contested(next(iter(c)))):
                return out(next(iter(ids)), "core_token_set_subsidiary",
                           " ".join(sorted(c)), "high")

    # ---- T5 longest contained canonical alias (v1 tier, retained) ---------
    for form in forms:
        alias, ids = canon_idx.longest_contained(form)
        if not alias:
            continue
        if len(ids) > 1:
            return out(reason="ambiguous_multiple", alias=alias,
                       competing="|".join(sorted(ids)))
        eid = next(iter(ids))
        conflicts = leading_conflict(form, alias.split(), eid, canon_idx,
                                     canon_idx.meta.get(eid))
        if conflicts:
            return out(reason=("state_conflict"
                               if all(k.startswith("of_") for k in conflicts)
                               else "qualifier_conflict"),
                       alias=f"{alias} [uncovered: {','.join(sorted(conflicts))}]",
                       competing="|".join(sorted({e for o in conflicts.values() for e in o})))
        refused = family_ok(alias, eid, canon_idx, form)
        if refused:
            return refused
        co = co_named_entities(form, alias, eid, canon_idx)
        if co:
            return out(reason="multiple_entities_named", alias=alias,
                       competing="|".join(sorted(co | {eid})))
        return out(eid, "contains_canonical", alias, "medium")

    # ---- T6 CORE CONTAINMENT, >=2 distinctive core tokens only (G4) -------
    best = None
    for form in forms:
        cc = core_tokens(form)
        if len(cc) < 2:
            continue
        for ecore, ids in canon_idx.core.items():
            if len(ecore) < 2 or not ecore <= cc:
                continue
            if best is None or len(ecore) > len(best[0]):
                best = (ecore, ids, form)
    if best:
        ecore, ids, form = best
        r = resolve(ids, "core_containment", " ".join(sorted(ecore)), "medium")
        if r["entity_id"]:
            conflicts = leading_conflict(form, ecore, r["entity_id"], canon_idx,
                                         canon_idx.meta.get(r["entity_id"]))
            if conflicts:
                return out(reason=("state_conflict"
                                   if all(k.startswith("of_") for k in conflicts)
                                   else "qualifier_conflict"),
                           alias=f"{' '.join(sorted(ecore))} [uncovered: {','.join(sorted(conflicts))}]",
                           competing="|".join(sorted({e for o in conflicts.values() for e in o})))
            refused = family_ok(" ".join(sorted(ecore)), r["entity_id"], canon_idx, form)
            if refused:
                return refused
            co = co_named_entities(form, " ".join(sorted(ecore)), r["entity_id"], canon_idx)
            if co:
                return out(reason="multiple_entities_named",
                           alias=" ".join(sorted(ecore)),
                           competing="|".join(sorted(co | {r["entity_id"]})))
        return r

    # ---- T7 contained subsidiary alias ------------------------------------
    for form in forms:
        alias, ids = sub_idx.longest_contained(form)
        if not alias:
            continue
        if len(ids) > 1:
            return out(reason="ambiguous_subsidiary", alias=alias,
                       competing="|".join(sorted(ids)))
        eid = next(iter(ids))
        conflicts = leading_conflict(form, alias.split(), eid, canon_idx,
                                     canon_idx.meta.get(eid))
        if conflicts:
            return out(reason="qualifier_conflict",
                       alias=f"{alias} [uncovered: {','.join(sorted(conflicts))}]",
                       competing="|".join(sorted({e for o in conflicts.values() for e in o})))
        return out(eid, "contains_subsidiary", alias, "medium")

    # ---- G4 near-miss: exactly one entity whose 1-token core sits inside ---
    for form in forms:
        cc = core_tokens(form)
        if not cc:
            continue
        cands = set()
        for ecore, ids in canon_idx.core.items():
            if len(ecore) == 1 and ecore <= cc:
                tok = next(iter(ecore))
                if not canon_idx.contested(tok) and len(tok) >= MIN_SOLO_TOKEN_LEN:
                    cands |= ids
        if cands:
            return out(reason="single_token_core_needs_ruling",
                       alias=" ".join(sorted(cc)),
                       competing="|".join(sorted(cands)))

    return out(reason="no_alias_hit")


def to_float(v):
    if v in (None, "", "null"):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def extract(rec):
    client = rec.get("client") or {}
    registrant = rec.get("registrant") or {}
    codes, texts, gov = [], [], set()
    for act in (rec.get("lobbying_activities") or []):
        c = act.get("general_issue_code")
        if c:
            codes.append(c)
        t = act.get("description")
        if t:
            texts.append(t.strip())
        for ge in (act.get("government_entities") or []):
            n = ge.get("name") if isinstance(ge, dict) else str(ge)
            if n:
                gov.add(n)
    affiliated = []
    for ao in (rec.get("affiliated_organizations") or []):
        n = ao.get("name") if isinstance(ao, dict) else str(ao)
        if n:
            affiliated.append(n.strip())
    income = to_float(rec.get("income"))
    expenses = to_float(rec.get("expenses"))
    if income is not None and income > 0:
        spend, basis = income, "income"
    elif expenses is not None and expenses > 0:
        spend, basis = expenses, "expenses"
    else:
        spend, basis = 0.0, "none_reported"
    cname = client.get("name") or ""
    rname = registrant.get("name") or ""
    return {
        "filing_uuid": rec.get("filing_uuid") or "",
        "filing_year": rec.get("filing_year") or "",
        "filing_period": rec.get("filing_period") or "",
        "filing_type": rec.get("filing_type") or "",
        "filing_type_display": rec.get("filing_type_display") or "",
        "dt_posted": rec.get("dt_posted") or "",
        "termination_date": rec.get("termination_date") or "",
        "income": income,
        "expenses": expenses,
        "spend": spend,
        "spend_basis": basis,
        "client_name": cname,
        "client_id": client.get("id") or "",
        "client_state": client.get("state") or "",
        "registrant_name": rname,
        "registrant_id": registrant.get("id") or "",
        "registrant_state": registrant.get("state") or "",
        "self_filed": 1 if (cname and norm(cname) == norm(rname)) else 0,
        "issue_codes": "|".join(sorted(set(codes))),
        "specific_issues_text": " ||| ".join(texts)[:4000],
        "government_entities": "|".join(sorted(gov)),
        "gov_list": sorted(gov),
        "affiliated_organizations": "|".join(sorted(set(affiliated))),
        "filing_url": rec.get("filing_document_url") or rec.get("url") or "",
        "_pull_keyword": rec.get("_pull_keyword", ""),
    }


def native_token_hit(client_name):
    return 1 if set(norm(client_name).split()) & NATIVE_TOKENS else 0


REVIEW_REASONS = {
    "ambiguous_multiple": "Which entity is this client? Two or more canonical entities fit the normalized name equally well.",
    "ambiguous_subsidiary": "Which parent does this subsidiary name belong to?",
    "generic_single_token": "Name reduces to one generic token shared by many entities (the Cherokee Inc. trap). Is there a specific entity, or is this a non-tribal / individually-owned firm?",
    "nickname_alias_underspecified": "The client name matches only a SHORT alias of this entity; the entity's full legal name carries additional identifying words the client never says. Same government, or a different one the table lacks an alias for?",
    "multiple_entities_named": "More than one government is named in this single client string -- a joint filing, or a component band named alongside its parent tribe. Which entity should the filing be booked to, or should it be split?",
    "ambiguous_sibling_family": "The identifying stem is shared by a family of sibling governments and nothing in the client name separates them. Which one is this?",
    "single_token_core_needs_ruling": "One candidate fits, but only via a single-token stem plus extra words. Confirm or reject.",
    "qualifier_conflict": "A leading qualifier points at a different government than the stem does. Which is correct?",
    "state_conflict": "The state in the client name contradicts the candidate entity's state. Which is correct?",
}


REVIEW_SPEND_FLOOR = 1_000_000

NO_CANDIDATE_Q = ("Native-sounding client with reported spend and NO canonical "
                  "candidate. Is this a misspelling of a listed entity, an aka "
                  "the entity table lacks, an intertribal organization that is "
                  "not a single tribal government, or not Native at all?")


def main():
    if not RAW.exists():
        log(f"ERROR: {RAW} not found. Run 04_pull_lda_v2.py first.")
        sys.exit(1)

    log(f"Alias index from {CANON.name}")
    canon_idx = build_canonical_index()
    amb = sum(1 for ids in canon_idx.exact.values() if len(ids) > 1)
    amb_core = sum(1 for ids in canon_idx.core.values() if len(ids) > 1)
    contested = sum(1 for t in canon_idx.core_token_vocab if canon_idx.contested(t))
    log(f"  {len(canon_idx.exact)} surface aliases over {len(canon_idx.meta)} entities "
        f"({amb} ambiguous)")
    log(f"  {len(canon_idx.core)} distinct cores ({amb_core} shared by >1 entity); "
        f"{contested} contested core tokens blocked as solo aliases")

    log(f"Subsidiary index from {SUBS.name}")
    sub_idx = build_subsidiary_index(canon_idx)
    log(f"  {len(sub_idx.exact)} subsidiary aliases")
    if _PARENT_REMAP:
        log(f"  {len(_PARENT_REMAP)} asserted parent ids absent from the entity "
            f"spine, resolved by name to a spine entity:")
        for old, (new, nm) in sorted(_PARENT_REMAP.items()):
            log(f"      {old} -> {new}   ({nm})")
    if _PARENT_UNRESOLVED:
        log(f"  {len(_PARENT_UNRESOLVED)} asserted parent ids absent from the "
            f"spine and NOT resolvable by name (kept as asserted, flagged): "
            + ", ".join(f"{k} ({v})" for k, v in sorted(_PARENT_UNRESOLVED.items())))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REVIEW_FILE.parent.mkdir(parents=True, exist_ok=True)
    fout = OUT_FILE.open("w", encoding="utf-8", newline="")
    cw = csv.writer(fout)
    cw.writerow([
        "filing_uuid", "entity_id", "canonical_name", "entity_type", "entity_state",
        "client_name", "client_id", "client_state",
        "registrant_name", "registrant_id", "registrant_state", "self_filed",
        "filing_year", "filing_period", "filing_type", "filing_type_display",
        "income_usd", "expenses_usd", "spend_usd", "spend_basis",
        "lobbying_issues_codes", "specific_issues_text", "government_entities",
        "affiliated_organizations", "dt_posted", "termination_date", "filing_url",
        "attribution_method", "match_confidence", "matched_alias", "pull_keyword",
    ])

    panel = defaultdict(lambda: {
        "spend": 0.0, "n_filings": 0, "n_self_filed": 0,
        "spend_income": 0.0, "spend_expenses": 0.0,
        "registrants": set(), "codes": defaultdict(int), "gov": defaultdict(int),
    })
    unmatched = defaultdict(lambda: {
        "n_filings": 0, "spend": 0.0, "years": set(), "registrants": defaultdict(int),
        "reason": "", "competing": "", "alias": "", "codes": defaultdict(int),
        "keywords": set(),
    })

    n_total = n_matched = n_unmatched = dup_lines = 0
    seen_uuid = set()
    method_counts = defaultdict(int)
    reason_counts = defaultdict(int)
    years = set()
    gov_entities = defaultdict(int)
    gov_entities_matched = defaultdict(int)
    registrants = defaultdict(lambda: {"n": 0, "spend": 0.0, "clients": set()})
    cache = {}

    for line in RAW.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        f = extract(rec)
        if not f["filing_uuid"] or f["filing_uuid"] in seen_uuid:
            dup_lines += 1
            continue
        seen_uuid.add(f["filing_uuid"])
        n_total += 1
        if f["filing_year"]:
            years.add(int(f["filing_year"]))

        key = f["client_name"]
        if key not in cache:
            cache[key] = match_client(key, canon_idx, sub_idx)
        m = cache[key]

        for g in f["gov_list"]:
            gov_entities[g] += 1

        if not m["entity_id"]:
            n_unmatched += 1
            reason_counts[m["reason"]] += 1
            u = unmatched[f["client_name"].strip() or "(blank)"]
            u["n_filings"] += 1
            u["spend"] += f["spend"]
            if f["filing_year"]:
                u["years"].add(int(f["filing_year"]))
            if f["registrant_name"]:
                u["registrants"][f["registrant_name"]] += 1
            for c in f["issue_codes"].split("|"):
                if c:
                    u["codes"][c] += 1
            if f["_pull_keyword"]:
                u["keywords"].add(f["_pull_keyword"])
            u["reason"] = m["reason"]
            u["competing"] = m["competing"]
            u["alias"] = m["alias"]
            continue

        n_matched += 1
        method_counts[m["method"]] += 1
        eid = m["entity_id"]
        meta = canon_idx.meta.get(eid, {})
        for g in f["gov_list"]:
            gov_entities_matched[g] += 1
        if f["registrant_name"]:
            r = registrants[f["registrant_name"]]
            r["n"] += 1
            r["spend"] += f["spend"]
            r["clients"].add(f["client_name"])
        cw.writerow([
            f["filing_uuid"], eid, meta.get("canonical_name", ""),
            meta.get("entity_type", ""), (meta.get("entity_state", "") or "").upper(),
            f["client_name"], f["client_id"], f["client_state"],
            f["registrant_name"], f["registrant_id"], f["registrant_state"], f["self_filed"],
            f["filing_year"], f["filing_period"], f["filing_type"], f["filing_type_display"],
            "" if f["income"] is None else f["income"],
            "" if f["expenses"] is None else f["expenses"],
            round(f["spend"], 2), f["spend_basis"],
            f["issue_codes"], f["specific_issues_text"], f["government_entities"],
            f["affiliated_organizations"], f["dt_posted"], f["termination_date"],
            f["filing_url"],
            m["method"], m["confidence"], m["alias"], f["_pull_keyword"],
        ])

        p = panel[(eid, f["filing_year"])]
        p["spend"] += f["spend"]
        p["n_filings"] += 1
        p["n_self_filed"] += f["self_filed"]
        if f["spend_basis"] == "income":
            p["spend_income"] += f["spend"]
        elif f["spend_basis"] == "expenses":
            p["spend_expenses"] += f["spend"]
        if f["registrant_name"]:
            p["registrants"].add(f["registrant_name"])
        for c in f["issue_codes"].split("|"):
            if c:
                p["codes"][c] += 1
        for g in f["gov_list"]:
            p["gov"][g] += 1

    fout.close()

    with PANEL_FILE.open("w", encoding="utf-8", newline="") as pf:
        pw = csv.writer(pf)
        pw.writerow([
            "entity_id", "canonical_name", "entity_type", "entity_state", "filing_year",
            "total_lobbying_spend_usd", "spend_from_client_income_usd",
            "spend_from_registrant_expenses_usd", "n_filings", "n_self_filed_filings",
            "n_unique_registrants", "top_lobbying_issue_codes", "top_government_entities",
        ])
        for (eid, year), p in sorted(panel.items(), key=lambda x: (x[0][0], str(x[0][1]))):
            meta = canon_idx.meta.get(eid, {})
            top_codes = "|".join(f"{c}:{n}" for c, n in
                                 sorted(p["codes"].items(), key=lambda x: (-x[1], x[0]))[:5])
            top_gov = "|".join(f"{g}:{n}" for g, n in
                               sorted(p["gov"].items(), key=lambda x: (-x[1], x[0]))[:5])
            pw.writerow([
                eid, meta.get("canonical_name", ""), meta.get("entity_type", ""),
                (meta.get("entity_state", "") or "").upper(), year,
                round(p["spend"], 2), round(p["spend_income"], 2),
                round(p["spend_expenses"], 2), p["n_filings"], p["n_self_filed"],
                len(p["registrants"]), top_codes, top_gov,
            ])

    with UNMATCHED_FILE.open("w", encoding="utf-8", newline="") as uf:
        uw = csv.writer(uf)
        uw.writerow([
            "client_name", "n_filings", "total_spend_usd", "first_year", "last_year",
            "top_registrant", "n_registrants", "top_issue_codes",
            "native_token_hit", "why_unmatched", "competing_entity_ids",
            "nearest_alias_considered", "pull_keywords",
        ])
        for client, u in sorted(unmatched.items(), key=lambda x: (-x[1]["spend"], x[0])):
            top_reg = sorted(u["registrants"].items(), key=lambda x: (-x[1], x[0]))
            top_codes = "|".join(f"{c}:{n}" for c, n in
                                 sorted(u["codes"].items(), key=lambda x: (-x[1], x[0]))[:5])
            uw.writerow([
                client, u["n_filings"], round(u["spend"], 2),
                min(u["years"]) if u["years"] else "", max(u["years"]) if u["years"] else "",
                top_reg[0][0] if top_reg else "", len(top_reg), top_codes,
                native_token_hit(client), u["reason"], u["competing"],
                u["alias"], "|".join(sorted(u["keywords"])),
            ])

    # ---- review queue: only the clients that need a human ruling ----------
    n_review = 0
    with REVIEW_FILE.open("w", encoding="utf-8", newline="") as rf:
        rw = csv.writer(rf)
        rw.writerow([
            "client_name", "total_spend_usd", "n_filings", "first_year", "last_year",
            "issue_type", "competing_entity_ids", "competing_entity_names",
            "normalized_stem", "question", "YOUR_RULING",
        ])
        for client, u in sorted(unmatched.items(), key=lambda x: (-x[1]["spend"], x[0])):
            # Two things belong in front of Elijah. (1) Clients the matcher could
            # have resolved but refused to, because a guard fired -- these carry
            # candidates. (2) Clients carrying Native tokens and real money that
            # produced NO candidate at all: LDA typos ("SAULTE STE MARIE",
            # "MICCOUSUKEE", "PUEBLO OF POJAQUE"), akas absent from the entity
            # table ("GUN LAKE TRIBE" = Match-e-be-nash-she-wish Band), and
            # intertribal organizations that are not single tribal governments.
            # No fuzzy matcher should guess at any of those; a person should say.
            if u["reason"] not in REVIEW_REASONS:
                # Native-token clients with any money, AND any client above the
                # material-spend floor regardless of token. The second half
                # matters: the keyword net's prefix matching drags in genuinely
                # non-Native firms (PALANTIR arrives via the "pala" net), but it
                # also surfaces real Native entities whose names carry no Native
                # token at all -- NANA DEVELOPMENT CORPORATION, DOYON UTILITIES,
                # KAMEHAMEHA SCHOOLS, TUBA CITY REGIONAL HEALTH CARE. Those are
                # exactly the "tribally owned firm with a non-obvious name"
                # undercount named in AGENTS.md, and a token test cannot find
                # them. Spend can. Ruling PALANTIR out costs a human two
                # seconds; missing NANA Development costs the dataset $4.9M.
                if not (u["reason"] == "no_alias_hit"
                        and ((native_token_hit(client) and u["spend"] > 0)
                             or u["spend"] >= REVIEW_SPEND_FLOOR)):
                    continue
            ids = [i for i in u["competing"].split("|") if i]
            names = "|".join(canon_idx.meta.get(i, {}).get("canonical_name", i) for i in ids)
            rw.writerow([
                client, round(u["spend"], 2), u["n_filings"],
                min(u["years"]) if u["years"] else "", max(u["years"]) if u["years"] else "",
                u["reason"], u["competing"], names, u["alias"],
                REVIEW_REASONS.get(u["reason"], NO_CANDIDATE_Q), "",
            ])
            n_review += 1

    matched_spend = sum(p["spend"] for p in panel.values())
    unmatched_spend = sum(u["spend"] for u in unmatched.values())
    native_flagged = sum(1 for c in unmatched if native_token_hit(c))

    log("\n=== SUMMARY ===")
    log(f"  filings processed (unique uuid): {n_total}"
        + (f"  [{dup_lines} duplicate/blank lines skipped]" if dup_lines else ""))
    if years:
        log(f"  filing years: {min(years)}-{max(years)}")
    log(f"  matched to an entity:            {n_matched} ({n_matched / max(n_total, 1):.1%} of filings)")
    log(f"  distinct clients seen:           {len(cache)}")
    log(f"  distinct clients matched:        {len(cache) - len(unmatched)} "
        f"({(len(cache) - len(unmatched)) / max(len(cache), 1):.1%} of clients)")
    log(f"  unmatched filings:               {n_unmatched}")
    log(f"  distinct entities in panel:      {len(set(k[0] for k in panel))}")
    log(f"  panel rows (entity x year):      {len(panel)}")
    log(f"  matched spend:                   ${matched_spend:,.0f}")
    log(f"  unmatched spend:                 ${unmatched_spend:,.0f}")
    log(f"  unmatched distinct clients:      {len(unmatched)} "
        f"({native_flagged} carry Native tokens)")
    nt_unm_f = sum(u["n_filings"] for c, u in unmatched.items() if native_token_hit(c))
    nt_tot = n_matched + nt_unm_f
    log(f"  match rate among filings whose client carries a Native token: "
        f"{n_matched}/{nt_tot} ({n_matched / max(nt_tot, 1):.1%})")
    log(f"  queued for Elijah ruling:        {n_review}")
    log("  match methods: " + ", ".join(f"{k}={v}" for k, v in
                                        sorted(method_counts.items(), key=lambda x: -x[1])))
    log("  unmatched reasons: " + ", ".join(f"{k}={v}" for k, v in
                                            sorted(reason_counts.items(), key=lambda x: -x[1])))
    log(f"\n  DISTINCT GOVERNMENT ENTITIES LOBBIED (LD-2 agencies-contacted):")
    log(f"    across all pulled filings : {len(gov_entities)}")
    log(f"    across MATCHED filings    : {len(gov_entities_matched)}")
    for g, n in sorted(gov_entities_matched.items(), key=lambda x: (-x[1], x[0]))[:20]:
        log(f"      {n:6d}  {g}")
    log(f"\n  TOP REGISTRANTS BY MATCHED NATIVE-CLIENT FILINGS:")
    for r, v in sorted(registrants.items(), key=lambda x: (-x[1]["n"], x[0]))[:20]:
        log(f"      {v['n']:5d} filings  ${v['spend']:>13,.0f}  {len(v['clients']):3d} clients  {r}")

    log(f"\n  -> {OUT_FILE}")
    log(f"  -> {PANEL_FILE}")
    log(f"  -> {UNMATCHED_FILE}")
    log(f"  -> {REVIEW_FILE}")


if __name__ == "__main__":
    main()
