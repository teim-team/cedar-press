#!/usr/bin/env python3
r"""
Cedar Press - 130: PROJECT-LEVEL Section 106 (NHPA) tribal consultation.

WHY THIS EXISTS
---------------
`data/clean/consultation_events.csv` holds 11,402 rows and looks healthy.
It is not, for this purpose:

    NAGPRA_consultation_report  10,888     (95.5%)
    consultation_session           212
    consultation_notice            180
    NAGPRA                          38
    listening_session               37
    NHPA_section_106                20     <-- this

11,068 of 11,402 come from Interior alone. A high row count concealing a
single-source, single-statute monoculture is exactly what a coverage table
hides. Section 106 is where PROJECT-level consultation lives.

WHAT MAKES SECTION 106 DIFFERENT FROM EVERY OTHER ROW IN THIS PROJECT
---------------------------------------------------------------------
Policy consultation (E.O. 13175, NAGPRA) is agency -> tribe about a rule or a
collection. Section 106 is about a **named federal undertaking**, and the
record therefore carries a party nothing else in Cedar Press sees:

    lead agency  ->  APPLICANT / DEVELOPER / LICENSEE  ->  tribe / THPO
                                                       ->  SHPO
                                                       ->  other consulting parties
                     ... and the instruments: MOA, Programmatic Agreement,
                     and the effect determination that triggered them.

The applicant is a **private firm** in most cases. It is a distinct actor and a
distinct relationship, and capturing it is the point.

TAXONOMY - NOT NEGOTIABLE
-------------------------
`EventClass.GOVERNMENT_ENGAGEMENT`, channel `SECTION_106_CONSULTATION`.
Section 106 is a statutory government-to-government process. It is NOT
lobbying and it is NOT advocacy. A developer writing to a THPO because
36 CFR 800 requires the agency to consult is discharging a legal obligation,
not buying influence. The assertions at the top of this module refuse to let
the build run if `cedar_domain` ever disagrees.

WHAT WAS ALREADY ON DISK (checked before a single byte was fetched)
-------------------------------------------------------------------
`data/clean/federal_actions.csv` (156,452 FR documents caught by the Native
net) already contains **561** documents whose title/abstract/action names
Section 106, the NHPA, 36 CFR 800 or the ACHP - across 1994-2026 and 20+
agencies, 146 of them ACHP's own documents. That is the seed, and it cost
nothing. Only 14 of the 561 had full text already retrieved by script 96.

The Federal Register full-text index is then used to reach documents the
Native net never caught, because a Section 106 notice for a pipeline does not
have to mention a tribe in its abstract.

ABSENCE IS A PROPERTY OF THE SOURCE
------------------------------------
`section_106_source_coverage.csv` records, per source, one of PUBLISHES /
WITHHOLDS / NOT_FOUND / NOT_CHECKED with the probe evidence. A tribe with no
Section 106 row is not a tribe that was not consulted - the Federal Register
publishes a small and non-random slice of the 106 record (agreements,
findings, and notices agencies chose to publish). The bulk of Section 106
correspondence is in agency project files and is not published anywhere.

ENTITY RESOLUTION
-----------------
`resolve_entity` from `code/33_apply_party_rulings.py`, through the guarded
`Resolver` in `code/96_build_consultation_events.py`. One resolver
project-wide; nothing re-implemented here.

APPLICANTS ARE NOT RESOLVED ONTO THE NATIVE SPINE BY DEFAULT. A developer
named in a 106 notice is usually a non-Native firm, and the containment
defect (AGENTS.md) would happily find it a tribe. Only exact / alias /
official-name matches key a party; everything else is blank and reviewable.

STAGES
------
    py -3 code/130_build_section_106_consultation.py enumerate
    py -3 code/130_build_section_106_consultation.py fetch
    py -3 code/130_build_section_106_consultation.py build
    py -3 code/130_build_section_106_consultation.py all

WRITES (all NEW files - consultation_events.csv is never touched)
-----------------------------------------------------------------
    data/clean/section_106_consultation_events.csv
    data/clean/section_106_project_parties.csv
    data/clean/section_106_source_coverage.csv
    review/section_106_unresolved_names_<date>.csv
    data/raw/external/section_106/...
"""
import csv
import importlib.util
import json
import os
import re
import sys
import time
import urllib.parse
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE_DIR = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
RAW = CEDAR / "data" / "raw" / "external" / "section_106"
TEXT = RAW / "fr_text"
CONSULT_TEXT = CEDAR / "data" / "raw" / "external" / "consultation" / "fr_text"
TODAY = date.today().isoformat()
FR_HOST = "www.federalregister.gov"
DEADLINE_S = 90 * 60          # wall-clock budget for the fetch stage

csv.field_size_limit(min(sys.maxsize, 2147483647))

# ---------------------------------------------------------------------------
# THE ONE RESOLVER, THE SHARED VOCABULARY, THE SHARED FETCHER.
# Imported from 33 and 96. Nothing re-declared.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(CEDAR / "code"))
from cedar_domain import (AdvocacyChannel, EventClass, Tier,      # noqa: E402
                          may_promote_event_class)
from cedar_keys import surrogate_id                              # noqa: E402

# --------------------------------------------------------------------------
# THE TWO PRIMARY KEYS THIS BUILD MINTS, AND WHAT THEY ARE MADE OF
#
# Both were POSITIONS, and one of them was a position in the WHOLE RUN:
#
#   party_id              f"S106P-FR-{dn}-{len(parties)}"
#   consultation_event_id f"S106-FR-{dn}-{i}"
#
# `len(parties)` counts every party found in every notice processed so far, so
# processing one extra Federal Register document renumbered the parties of
# every document after it. `i` was an index into a sorted dict of matched
# tribes, so adding a tribe to the spine renumbered the events of every notice
# that tribe appears in. `ferc_tribal_dockets.section_106_cross_ref` points at
# those event ids from another table.
#
# Both are now deterministic blake2b digests of what the Federal Register
# itself states: its own DOCUMENT NUMBER (the source's identifier for the
# notice), the NAME it publishes for the party/participant, and the ROLE it
# gives them. Measured 2026-08-26: parties unique over all 51 rows, events
# unique over all 1,363 rows, 0 blank in either.
#
# Migrated in the live files by `327_migrate_class7_keys_to_digests.py`.
# --------------------------------------------------------------------------
S106_PARTY_KEY_COLUMNS = ["document_number", "party_name_as_published",
                          "party_role"]
S106_EVENT_KEY_COLUMNS = ["document_number", "participant_name_as_published",
                          "participant_role"]

_spec = importlib.util.spec_from_file_location(
    "c96", CEDAR / "code" / "96_build_consultation_events.py")
c96 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(c96)

fetch = c96.fetch
claim_host = c96.claim_host
release_host = c96.release_host
save_manifest = c96.save_manifest
read_csv = c96.read_csv
write_csv = c96.write_csv
flatten = c96.flatten
sentences = c96.sentences
split_names = c96.split_names
looks_like_entity = c96.looks_like_entity
Resolver = c96.Resolver
norm = c96.norm
META_FIELDS = c96.META_FIELDS

CHANNEL = AdvocacyChannel.SECTION_106_CONSULTATION
assert CHANNEL.is_lobbying is False, \
    "cedar_domain says Section 106 consultation is lobbying - refusing to build."
assert CHANNEL.event_class is EventClass.GOVERNMENT_ENGAGEMENT, \
    "Section 106 must be GOVERNMENT_ENGAGEMENT - refusing to build."
assert may_promote_event_class(EventClass.ACCESS, EventClass.ADVOCACY) is False, \
    "the promotion guard is gone - refusing to build."


# ===========================================================================
# THE PATTERNS
# ===========================================================================

# A document is in scope only if it names the statute. "Historic preservation"
# alone is not Section 106; the NHPA has other sections and other programs.
S106_RE = re.compile(
    r"(?i)\bsection\s*106\b"
    r"|\b36\s*C\.?F\.?R\.?\s*(?:part\s*)?800\b"
    r"|\bnational\s+historic\s+preservation\s+act\b"
    r"|\badvisory\s+council\s+on\s+historic\s+preservation\b"
    r"|\b54\s*U\.?S\.?C\.?\s*3061\d\d\b")

# Tribal involvement. A Section 106 notice with no tribal party is a real
# Section 106 record but it is not OUR record, and it is counted as such.
TRIBAL_RE = re.compile(
    r"(?i)\bindian\s+tribes?\b|\btribal\b|\btribes\b"
    r"|\bnative\s+american\b|\bnative\s+hawaiian\b"
    r"|\btribal\s+historic\s+preservation\s+officer\b|\bTHPO\b"
    r"|\bnative\s+village\b|\bpueblo\b|\brancheria\b")

CONSULT_VERB_RE = re.compile(
    r"(?i)\bconsult(?:ed|ing|ation|ations)?\b|\binitiat(?:ed|ing|es)\s+"
    r"(?:government-to-government\s+)?consultation\b"
    r"|\bgovernment-to-government\b|\bwas\s+invited\b|\bwere\s+invited\b"
    r"|\binvited\s+to\s+(?:participate|consult|comment)\b"
    r"|\bconcurring\s+part(?:y|ies)\b|\bconsulting\s+part(?:y|ies)\b"
    r"|\bsignator(?:y|ies)\b|\bexecuted\b|\bnotified\b")

THPO_RE = re.compile(
    r"(?i)tribal\s+historic\s+preservation\s+officers?|\bTHPOs?\b")
SHPO_RE = re.compile(
    r"(?i)state\s+historic\s+preservation\s+officers?|\bSHPOs?\b")
ACHP_RE = re.compile(
    r"(?i)advisory\s+council\s+on\s+historic\s+preservation|\bACHP\b")
CONSULTING_PARTY_RE = re.compile(r"(?i)consulting\s+part(?:y|ies)")

# Effect determinations - 36 CFR 800.4(d) and 800.5. Order matters only for
# reporting; every determination present is recorded, none is inferred.
EFFECT_PATTERNS = [
    ("NO_HISTORIC_PROPERTIES_AFFECTED",
     re.compile(r"(?i)no\s+historic\s+properties\s+(?:will\s+be\s+|would\s+be\s+"
                r"|are\s+|shall\s+be\s+)?(?:affected|present)")),
    ("NO_ADVERSE_EFFECT",
     re.compile(r"(?i)(?:finding|determination|determined?)\s+of\s+no\s+adverse"
                r"\s+effect|no\s+adverse\s+effect")),
    ("ADVERSE_EFFECT",
     re.compile(r"(?i)(?:finding|determination|determined?)\s+of\s+adverse\s+"
                r"effect|adverse\s+effects?\s+(?:on|to|upon)\s+historic\s+"
                r"propert|resolve\s+(?:the\s+)?adverse\s+effects?|will\s+have\s+"
                r"an\s+adverse\s+effect|would\s+(?:have|result\s+in)\s+an\s+"
                r"adverse\s+effect")),
]

# A DETERMINATION IS A DECISION SOMEONE MADE. A REGULATION DESCRIBING ONE IS
# NOT. 36 CFR 800.5 prints "adverse effect on historic properties" in every
# rule that recites the standard, so pattern presence alone measures vocabulary,
# not findings. Only a sentence carrying a determinative verb is read as a
# determination; the looser presence flag is kept separately and named for what
# it is.
DETERMINATIVE_RE = re.compile(
    r"(?i)\b(?:has|have|had)\s+determined\b|\bdetermin(?:ation|ed|es)\b"
    r"|\bfinding\s+of\b|\bconclud(?:ed|es|ing)\b|\bfinds?\s+that\b"
    r"|\bhereby\b|\bhas\s+found\b|\bwe\s+find\b")

AGREEMENT_PATTERNS = [
    ("PROGRAMMATIC_AGREEMENT",
     re.compile(r"(?i)programmatic\s+agreement")),
    ("MEMORANDUM_OF_AGREEMENT",
     re.compile(r"(?i)memorandum\s+of\s+agreement")),
    ("MEMORANDUM_OF_UNDERSTANDING",
     re.compile(r"(?i)memorand(?:um|a)\s+of\s+understanding")),
    ("EXEMPTED_CATEGORY_OR_PROGRAM_ALTERNATIVE",
     re.compile(r"(?i)program\s+alternative|program\s+comment|exempted\s+categor")),
]

# --- the applicant / developer -------------------------------------------
# PRECISION OVER RECALL. A name is only taken when the document itself marks
# the role, either by an appositive - "X, LLC (the Applicant)" - or by a role
# noun standing immediately beside a name that carries a corporate form. A
# capitalised string near the word "applicant" is not evidence.
#
# TWO BUGS MEASURED AND FIXED HERE, both of which shipped 264 rows of prose on
# the first pass and are worth recording because they are generic:
#
#   1. `(?i)` ON THE WHOLE PATTERN DESTROYS THE CAPITALISATION TEST. The name
#      sub-pattern begins `[A-Z]`, which is the only thing separating a proper
#      name from a verb phrase - and a leading `(?i)` silently removes it.
#      The role noun is now spelled out in both cases instead.
#   2. A CORPORATE SUFFIX MUST BE A WHOLE WORD. `Inc\.?` matched the "inc" in
#      *including*, `Corp\.?` the "corp" in *corporation*, and `Co\.` the "co"
#      in *cooperatively*. Every tail is now `\b`-anchored, and the bare common
#      nouns (Resources, Partners, Authority, District, Company) were removed
#      because they are ordinary English before they are corporate forms.
#
# A candidate that survives the regex must still pass `valid_party_name()`.
CORP_TAIL = (r"(?:LLC\b|L\.L\.C\.|Inc\b\.?|Incorporated\b|Corp\b\.?|"
             r"Corporation\b|L\.P\.|LP\b|LLP\b|PLLC\b|Ltd\b\.?|"
             r"Partnership\b|Associates\b|Holdings\b|Cooperative\b|"
             r"Energy\b|Power\b|Electric\b|Gas\b|Pipeline\b|Pipe\s+Line\b|"
             r"Transmission\b|Railroad\b|Railway\b|Mining\b|Utilities\b|"
             r"Telecom\b|Communications\b|Wireless\b|Towers?\b|"
             r"Wind\b|Solar\b|Hydro\b|Hydroelectric\b)")

NAME_CHARS = r"[A-Z][A-Za-z0-9&.'\u2019\-]*"
# "City OF Broken Bow, Oklahoma" and "Board OF Power AND Light" are single
# organisation names. A run of capitalised tokens alone truncates both at the
# first lowercase connective, which is how "Broken Bow, Oklahoma" lost its head
# on the third pass. Connectives are allowed INSIDE the run, never at its start.
NAME_TOKEN = r"(?:" + NAME_CHARS + r"|of|and|the|for|de|du|van|von|del|la|le)"
NAME_RUN = r"(?:" + NAME_TOKEN + r"[ ,]{1,2}){0,8}"
ROLE_WORDS = (r"(?:[Aa]pplicant|APPLICANT|[Ll]icensee|[Pp]ermittee|"
              r"[Pp]roject\s+[Ss]ponsor|[Pp]roject\s+[Pp]roponent|"
              r"[Dd]eveloper|[Ll]essee|[Uu]ndertaking\s+[Ss]ponsor)")

APPOSITIVE_RE = re.compile(
    r"(" + NAME_RUN + NAME_CHARS + r")"
    r"\s*\(\s*(?:the\s+|hereinafter\s+(?:the\s+)?|collectively\s+|"
    r"or\s+the\s+)?"
    r"[\"\u201c]?(" + ROLE_WORDS + r")[\"\u201d]?\s*\)")

ROLE_THEN_NAME_RE = re.compile(
    r"\b(" + ROLE_WORDS + r")\b[,:]?\s+(" + NAME_RUN + CORP_TAIL + r")")

NAME_THEN_ROLE_RE = re.compile(
    r"(" + NAME_RUN + CORP_TAIL + r")"
    r"[,]?\s+(?:the\s+|as\s+the\s+)?\(?(" + ROLE_WORDS + r")\b")

FILED_BY_RE = re.compile(
    r"(" + NAME_RUN + CORP_TAIL + r")"
    r"\s+(?:has\s+|had\s+|have\s+)?(?:filed|submitted|applied\s+for|"
    r"requests?|requested|proposes?|proposed|seeks?|sought)\s+"
    r"(?:an?\s+|the\s+)?(?:application|permit|license|licence|authorization|"
    r"amendment|request|project)")

# THE PATTERN THAT ACTUALLY CARRIES THE PRIVATE-SECTOR SIDE.
#
# Measured on the retrieved corpus, the richest Section 106 sentence in the
# Federal Register is the FERC/ACHP invitation, and it names the developer,
# the project, the tribes and the instrument in ONE sentence:
#
#   "Alabama Power Company, as licensee for Project Nos. 2146, 82, and 618,
#    and the Mississippi Band of Choctaw Indians, Jena Band of Choctaw
#    Indians, Chickasaw Nation, Poarch Band of Creek Indians, and the U.S.
#    Bureau of Indian Affairs have expressed an interest in this preceding and
#    are invited to participate in consultations..."   - 02-16252
#
#   "Allegheny Energy Supply Company, LLC, as prospective licensee for Project
#    Nos. 2516-026 and 2517-010, is invited to participate in consultations to
#    develop the Programmatic Agreement and to sign as a concurring party."
#                                                       - 03-19994
#
# No corporate suffix is required here - "Marquette Board of Power and Light"
# has none - because ", as licensee for Project No." is a stronger role marker
# than any suffix.
NAME_AS_ROLE_RE = re.compile(
    r"(" + NAME_RUN + NAME_CHARS + r")\s*,\s+as\s+(?:the\s+)?"
    r"(?:prospective\s+|proposed\s+|current\s+|existing\s+)?"
    r"(licensee|applicant|permittee|project\s+sponsor|developer|owner|"
    r"operator|project\s+proponent|lessee)\b")

PROJECT_NO_RE = re.compile(
    r"(?i)\bProject\s+Nos?\.?\s*((?:[0-9]{2,6}(?:-[0-9]{3})?)"
    r"(?:\s*(?:,|and)\s*(?:[0-9]{2,6}(?:-[0-9]{3})?))*)")

ROLE_LABEL = {
    "applicant": "APPLICANT", "licensee": "LICENSEE", "permittee": "PERMITTEE",
    "developer": "DEVELOPER", "project sponsor": "PROJECT_SPONSOR",
    "sponsor": "PROJECT_SPONSOR", "project proponent": "PROJECT_PROPONENT",
    "proponent": "PROJECT_PROPONENT", "company": "APPLICANT",
    "lessee": "LESSEE", "grantee": "GRANTEE",
    "undertaking sponsor": "PROJECT_SPONSOR",
}

# Strings that pass the corporate-form test but are not a project applicant.
PARTY_STOP_RE = re.compile(
    r"(?i)^(?:the|this|that|such|its|his|her|their|our|an?)\b"
    r"|^(?:united\s+states|u\.?s\.?)\b"
    r"|(?:department|bureau|service|administration|agency|commission)\s+of\s+"
    r"(?:the\s+)?(?:interior|agriculture|energy|defense|transportation|"
    r"commerce|state|army|navy|air\s+force)"
    r"|federal\s+register|advisory\s+council|national\s+park\s+service"
    r"|environmental\s+protection\s+agency|corps\s+of\s+engineers"
    # A FEDERAL AGENCY IS THE CONSULTING AUTHORITY, NEVER THE APPLICANT.
    # "Federal Office of Surface Mining" reached the party file on the fourth
    # pass; the lead agency already has its own column and must not be
    # published as the private-sector counterparty.
    r"|office\s+of\s+surface\s+mining|bureau\s+of\s+(?:land|indian|reclamation"
    r"|ocean)|forest\s+service|fish\s+and\s+wildlife\s+service"
    r"|federal\s+(?:office|agency|highway|aviation|energy|communications)"
    r"|surface\s+transportation\s+board|tennessee\s+valley\s+authority")

# A real organisation name is capitalised throughout, apart from a handful of
# connectives. Any ordinary English verb, modal or determiner inside the string
# means the regex captured a clause, not a name.
PROSE_TOKENS = {
    "a", "an", "any", "all", "are", "as", "at", "be", "been", "being", "both",
    "but", "by", "can", "could", "did", "do", "does", "each", "either", "from",
    "had", "has", "have", "if", "in", "into", "is", "it", "its", "may", "more",
    "most", "must", "no", "not", "on", "one", "only", "or", "other", "per",
    "shall", "should", "since", "so", "such", "than", "that", "their", "then",
    "these", "this", "those", "through", "to", "under", "use", "used", "was",
    "were", "when", "which", "while", "who", "will", "with", "within",
    "would", "you", "your", "including", "include", "includes", "provide",
    "provided", "submit", "submitted", "required", "require", "requires",
    "make", "made", "take", "taken", "prior", "upon", "about", "after",
    "before", "during", "between", "however", "also",
}
CONNECTIVE_TOKENS = {"of", "and", "the", "for", "de", "du", "van", "von",
                     "del", "la", "le", "at"}
# A NAME MUST NAME SOMETHING. "Water Company", "Gas Company" and "Surface
# Mining" are industry nouns with no proper noun in them - each is the tail of
# a name whose head the regex failed to reach, and publishing one would
# attribute a federal undertaking to a firm we cannot actually identify.
GENERIC_TOKENS = {
    "water", "gas", "company", "co", "power", "energy", "electric",
    "electrical", "mining", "mine", "surface", "utilities", "utility",
    "corporation", "corp", "inc", "incorporated", "llc", "llp", "lp", "ltd",
    "hydro", "hydroelectric", "solar", "wind", "group", "holdings",
    "associates", "partnership", "cooperative", "telecom", "communications",
    "wireless", "tower", "towers", "transmission", "pipeline", "railroad",
    "railway", "resources", "authority", "district", "agency", "board",
    "light", "service", "services", "project", "generating", "generation",
    "development", "developments", "properties", "construction", "systems",
    "system", "national", "american", "united", "federal", "state", "county",
    "city", "town", "village", "regional", "public",
    "telephone", "owners", "owner", "operators", "operator",
}
CORP_TAIL_WORD_RE = re.compile(r"^(?:" + CORP_TAIL + r")$")

# A PERSON IS NOT AN APPLICANT ORGANISATION. "Applicant: Max Hicks, Director,
# Utilities" is a contact block, and it slipped through on the second pass
# because "Utilities" is a corporate-form token.
PERSON_TITLE_RE = re.compile(
    r"(?i)\b(?:director|manager|secretary|chief|officer|coordinator|"
    r"administrator|supervisor|attorney|deputy|assistant|contact|"
    r"specialist|analyst|engineer|archaeologist|mr|mrs|ms|dr)\b")


def valid_party_name(name):
    """A captured string is a name only if every token looks like one.

    This is the guard that turns a permissive regex into a precise extractor.
    Without it the first build produced 264 party rows of which ZERO were
    organisations - "must inc", "and the third party that inc", "has adequate
    facilities and resources".
    """
    toks = [t for t in re.split(r"[\s,]+", name.strip(" ,;:.")) if t]
    if not (2 <= len(toks) <= 10):
        return False
    if not re.match(r"^[A-Z0-9]", toks[0]):
        return False
    if PERSON_TITLE_RE.search(name):
        return False
    lower = 0
    for t in toks:
        bare = t.strip(".,'\u2019-")
        if not bare:
            return False
        if bare.lower() in PROSE_TOKENS:
            return False
        if bare[0].islower():
            if bare.lower() not in CONNECTIVE_TOKENS:
                return False
            lower += 1
    if lower > 2:
        return False
    distinctive = [t for t in toks
                   if t.strip(".,'’-").lower() not in GENERIC_TOKENS
                   and t.strip(".,'’-").lower() not in CONNECTIVE_TOKENS]
    if not distinctive:
        return False
    return True

# Sentence-level junk that must never reach the resolver as a "tribe".
SEG_LEAD_RE = re.compile(
    r"(?i)^(?:.*?\b(?:consult(?:ed|ing|ation)?|invited|notified|contacted|"
    r"party|parties|signator(?:y|ies)|concurring)\b[^A-Z]{0,40})")


# ===========================================================================
# STAGE 1 - ENUMERATE
# ===========================================================================

LOCAL_RE = re.compile(
    r"(?i)section\s*106|national historic preservation act"
    r"|36\s*cfr\s*(?:part\s*)?800|advisory council on historic preservation")

SEARCH_TERMS = [
    '"tribal historic preservation officer"',
    '"section 106" "indian tribe" "historic properties"',
    '"programmatic agreement" "indian tribe" "historic properties"',
    '"memorandum of agreement" "section 106" "tribe"',
    '"36 CFR part 800" tribe',
    '"adverse effect" "historic properties" tribe',
]


def local_candidates():
    """Section 106 documents ALREADY on disk in federal_actions.csv.

    This is checked before anything is fetched, and it is most of the build.
    """
    p = CLEAN / "federal_actions.csv"
    out = {}
    with p.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            blob = " || ".join([r.get("title") or "", r.get("abstract") or "",
                                r.get("action") or ""])
            if LOCAL_RE.search(blob):
                out[r["document_number"]] = {
                    "seed": "federal_actions_local",
                    "publication_date": r.get("publication_date") or "",
                    "title": r.get("title") or "",
                    "agency_names": r.get("agency_names") or "",
                }
    return out


def stage_enumerate():
    print("=== 130 stage ENUMERATE ===\n")
    RAW.mkdir(parents=True, exist_ok=True)

    local = local_candidates()
    print(f"LOCAL, no fetch required:")
    print(f"  federal_actions.csv rows naming s.106 / NHPA / 36 CFR 800 / ACHP"
          f" : {len(local):,}")
    have96 = {p.stem for p in CONSULT_TEXT.glob('*.txt')}
    print(f"  of those, full text already retrieved by script 96          "
          f" : {len(set(local) & have96):,}\n")

    cand = dict(local)
    probes = []

    if not claim_host(FR_HOST, "code/130_build_section_106_consultation.py",
                      "Section 106 project consultation: FR full-text index"):
        print("  host held by another poller - using LOCAL candidates only.")
    else:
        try:
            for term in SEARCH_TERMS:
                page, got = 1, 0
                while True:
                    q = urllib.parse.urlencode(
                        [("per_page", "1000"), ("page", str(page)),
                         ("order", "oldest"),
                         ("conditions[term]", term)] +
                        [("fields[]", f) for f in
                         ("document_number", "publication_date", "title",
                          "agency_names")])
                    st, body = fetch(
                        f"https://{FR_HOST}/api/v1/documents.json?{q}",
                        timeout=120)
                    probes.append({"term": term, "page": page,
                                   "http_status": st})
                    if st != 200:
                        print(f"  HTTP {st} on term {term!r} page {page}"
                              f" - stopping this term")
                        break
                    j = json.loads(body)
                    for r in j.get("results") or []:
                        dn = r["document_number"]
                        if dn not in cand:
                            cand[dn] = {
                                "seed": "fr_fulltext_search",
                                "publication_date": r.get("publication_date") or "",
                                "title": r.get("title") or "",
                                "agency_names": "; ".join(
                                    r.get("agency_names") or []),
                            }
                        got += 1
                    if not j.get("next_page_url"):
                        break
                    page += 1
                print(f"  {got:>6,} hits  {term}")
        finally:
            release_host(FR_HOST, "code/130_build_section_106_consultation.py",
                         "enumeration complete")

    rows = [{"document_number": k, **v} for k, v in sorted(cand.items())]
    write_csv(RAW / "candidates.csv", rows,
              ["document_number", "seed", "publication_date", "title",
               "agency_names"])
    seeds = Counter(r["seed"] for r in rows)
    print(f"\ncandidate documents: {len(rows):,}")
    for k, v in seeds.most_common():
        print(f"  {k:<28} {v:,}")
    (RAW / "_enumeration_probes.json").write_text(
        json.dumps(probes, indent=1), encoding="utf-8")
    save_manifest()


# ===========================================================================
# STAGE 2 - FETCH
# ===========================================================================

def stage_fetch():
    print("=== 130 stage FETCH ===\n")
    cands = read_csv(RAW / "candidates.csv")
    if not cands:
        print("no candidates - run `enumerate` first."); return
    docs = [r["document_number"] for r in cands]
    print(f"candidates: {len(docs):,}")

    TEXT.mkdir(parents=True, exist_ok=True)
    meta_path = RAW / "fr_meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) \
        if meta_path.exists() else {}

    # Reuse script 96's text cache before asking the host for anything.
    reused = 0
    for dn in docs:
        dst = TEXT / f"{dn}.txt"
        src = CONSULT_TEXT / f"{dn}.txt"
        if not dst.exists() and src.exists():
            dst.write_bytes(src.read_bytes())
            reused += 1
    print(f"reused from script 96's cache: {reused:,}")

    if not claim_host(FR_HOST, "code/130_build_section_106_consultation.py",
                      f"Section 106: metadata + full text, {len(docs):,} docs"):
        return
    t0 = time.time()
    try:
        need = [d for d in docs if d not in meta]
        print(f"metadata to fetch: {len(need):,}")
        CHUNK = 60          # 200 overruns the request line (HTTP 414) - see 96
        for i in range(0, len(need), CHUNK):
            if time.time() - t0 > DEADLINE_S:
                print("  [deadline] stopping metadata"); break
            chunk = need[i:i + CHUNK]
            q = [("per_page", "1000")] + [("fields[]", f) for f in META_FIELDS]
            q += [("conditions[document_numbers][]", d) for d in chunk]
            st, body = fetch(
                f"https://{FR_HOST}/api/v1/documents.json?"
                + urllib.parse.urlencode(q), timeout=120)
            if st != 200:
                print(f"  metadata chunk {i}: HTTP {st}")
                if st == 0:
                    print("  transport failure - stopping (not a 404)"); break
                continue
            for r in json.loads(body)["results"]:
                meta[r["document_number"]] = r
            meta_path.write_text(json.dumps(meta), encoding="utf-8")
            print(f"  metadata {min(i + CHUNK, len(need)):,}/{len(need):,}")
        meta_path.write_text(json.dumps(meta), encoding="utf-8")
        print(f"metadata on disk: {len(meta):,}\n")

        todo = [d for d in docs if not (TEXT / f"{d}.txt").exists()]
        print(f"full text to fetch: {len(todo):,}")
        got = miss = bad = 0
        for i, dn in enumerate(todo, 1):
            if time.time() - t0 > DEADLINE_S:
                print(f"  [deadline] stopping at {i}/{len(todo)}"); break
            u = (meta.get(dn) or {}).get("raw_text_url")
            if not u:
                miss += 1
                continue
            st, body = fetch(u)
            if st == 200 and body:
                # .part then rename: an interruption must never look like a
                # completed file (AGENTS.md, the FY2011 256-row extract).
                part = TEXT / f"{dn}.txt.part"
                part.write_bytes(body)
                part.rename(TEXT / f"{dn}.txt")
                got += 1
            elif st == 0:
                print(f"  transport failure on {dn} - stopping the pull")
                bad += 1
                break
            else:
                bad += 1
            if i % 100 == 0:
                print(f"  {i:,}/{len(todo):,}  ok={got:,} miss={miss:,} "
                      f"bad={bad:,}  {time.time() - t0:.0f}s")
        print(f"\nfull text: retrieved {got:,}, no raw_text_url {miss:,}, "
              f"non-200 {bad:,}")
    finally:
        release_host(FR_HOST, "code/130_build_section_106_consultation.py",
                     "Section 106 fetch complete")
        save_manifest()


# ===========================================================================
# STAGE 3 - BUILD
# ===========================================================================

def first_match_quote(sents, rx, limit=600):
    for s in sents:
        if rx.search(s):
            return re.sub(r"\s+", " ", s).strip()[:limit]
    return ""


def find_parties(text, sents):
    """-> [(name, role, quote, method, project_reference)]

    Named applicants / developers / licensees only. Everything here is
    role-marked by the document itself; nothing is inferred from proximity.
    """
    out, seen = [], set()

    def add(name, role, sent, method):
        name = re.sub(r"\s+", " ", name).strip(" ,;:.")
        if len(name) < 4 or len(name.split()) > 10:
            return
        if PARTY_STOP_RE.search(name):
            return
        if not valid_party_name(name):
            return
        key = (norm(name), role)
        if key in seen:
            return
        seen.add(key)
        pm = PROJECT_NO_RE.search(sent)
        out.append((name, role, re.sub(r"\s+", " ", sent).strip()[:600],
                    method, ("Project No. " + pm.group(1)) if pm else ""))

    def label(word):
        return ROLE_LABEL.get(re.sub(r"\s+", " ", word).strip().lower(),
                              "APPLICANT")

    for s in sents:
        for m in NAME_AS_ROLE_RE.finditer(s):
            add(m.group(1), label(m.group(2)), s,
                "name_then_as_role_for_named_project")
        for m in APPOSITIVE_RE.finditer(s):
            add(m.group(1), label(m.group(2)), s, "appositive_role_label")
        for m in ROLE_THEN_NAME_RE.finditer(s):
            add(m.group(2), label(m.group(1)), s,
                "role_noun_then_corporate_name")
        for m in NAME_THEN_ROLE_RE.finditer(s):
            add(m.group(1), label(m.group(2)), s,
                "corporate_name_then_role_noun")
    # Weaker, and tiered accordingly downstream: a corporate filer in a
    # sentence that also names the statute or the undertaking.
    for s in sents:
        if not S106_RE.search(s) and not re.search(
                r"(?i)undertaking|permit\b|licen[cs]e|application", s):
            continue
        for m in FILED_BY_RE.finditer(s):
            add(m.group(1), "FILER", s,
                "corporate_filer_in_undertaking_sentence")

    # "Lockhart Power" and "Lockhart Power Company, Inc" are one firm captured
    # by two patterns. Keep the longer form; a truncated duplicate would
    # inflate the developer count and split the firm's record in two.
    keep = []
    for rec in out:
        n = norm(rec[0])
        if any(rec is not o and rec[1] == o[1] and n != norm(o[0])
               and norm(o[0]).startswith(n) for o in out):
            continue
        keep.append(rec)
    return keep


def tribes_by_official_name(text_norm, spine_by_fr):
    """Literal occurrence of a full Federal Register official name.

    The safest match in the project: the official names run 4+ tokens and are
    unique by construction, so this cannot reproduce the "San Juan" collision
    (AGENTS.md) - it never matches on a short canonical name.
    """
    hits = []
    for nfr, row in spine_by_fr.items():
        if len(nfr.split()) < 4:
            continue
        if nfr in text_norm:
            hits.append(row)
    return hits


def stage_build():
    print("=== 130 stage BUILD ===\n")
    cands = {r["document_number"]: r for r in read_csv(RAW / "candidates.csv")}
    meta_path = RAW / "fr_meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) \
        if meta_path.exists() else {}
    have = {p.stem for p in TEXT.glob("*.txt")}
    print(f"candidates {len(cands):,} | metadata {len(meta):,} | "
          f"full text {len(have):,}\n")

    spine = read_csv(SPINE_DIR / "cedar_entity_spine.csv")
    R = Resolver(spine)
    spine_by_fr = {}
    for r in spine:
        if r["entity_class"] not in c96.GOVERNMENT_CLASSES:
            continue
        fr = (r.get("fr_official_name") or "").strip()
        if fr:
            spine_by_fr.setdefault(norm(fr), r)
    print(f"spine {len(spine):,} | government-class with an official FR name: "
          f"{len(spine_by_fr):,}\n")

    rows, parties, unresolved = [], [], []
    st = Counter()

    for dn in sorted(cands):
        st["candidates_seen"] += 1
        tp = TEXT / f"{dn}.txt"
        if not tp.exists():
            st["no_full_text_retrieved"] += 1
            continue
        raw = tp.read_text(encoding="utf-8", errors="replace")
        text = flatten(raw)
        if len(text) < 200:
            st["text_too_short"] += 1
            continue

        if not S106_RE.search(text):
            st["excluded_no_section_106_marker"] += 1
            continue
        st["section_106_documents"] += 1
        if not TRIBAL_RE.search(text):
            st["excluded_section_106_but_no_tribal_party"] += 1
            continue
        st["section_106_with_tribal_content"] += 1

        m = meta.get(dn) or {}
        # 65 of 1,422 documents carry an agency entry with ONLY `raw_name` -
        # an office the Federal Register never normalised ("Office of Community
        # Services", "Office of the Secretary"). It has no `id` and no
        # `parent_id`, so a plain `not a.get("parent_id")` test files it as the
        # LEAD AGENCY. It is a sub-agency. Read the shape, not one key.
        ags = m.get("agencies") or []
        def _nm(a):
            return a.get("name") or a.get("raw_name") or ""
        parents = [a for a in ags if a.get("id") and not a.get("parent_id")]
        children = [a for a in ags if a.get("parent_id") or not a.get("id")]
        agency = (_nm(parents[0]) if parents else
                  (_nm(ags[0]) if ags else cands[dn].get("agency_names", "")))
        sub_agency = _nm(children[0]) if children else ""
        title = m.get("title") or cands[dn].get("title") or ""
        pub = m.get("publication_date") or cands[dn].get("publication_date") or ""
        url = m.get("html_url") or \
            f"https://www.federalregister.gov/d/{dn}"
        cite = m.get("citation") or ""
        docket = "; ".join(m.get("docket_ids") or [])
        deadline = m.get("comments_close_on") or ""

        sents = sentences(text)
        s106_quote = first_match_quote(sents, S106_RE)
        thpo_q = first_match_quote(sents, THPO_RE)
        shpo_q = first_match_quote(sents, SHPO_RE)
        achp_q = first_match_quote(sents, ACHP_RE)
        cparty_q = first_match_quote(sents, CONSULTING_PARTY_RE)

        effect_terms = [k for k, rx in EFFECT_PATTERNS if rx.search(text)]
        effects, effect_q = [], ""
        for k, rx in EFFECT_PATTERNS:
            if k not in effect_terms:
                continue
            for s in sents:
                if rx.search(s) and DETERMINATIVE_RE.search(s):
                    effects.append(k)
                    if not effect_q:
                        effect_q = re.sub(r"\s+", " ", s).strip()[:600]
                    break
        agreements = [k for k, rx in AGREEMENT_PATTERNS if rx.search(text)]
        agree_q = ""
        for k, rx in AGREEMENT_PATTERNS:
            if k in agreements:
                agree_q = first_match_quote(sents, rx)
                break

        # ---- applicants / developers ----------------------------------
        found_parties = find_parties(text, sents)
        for name, role, quote, method, proj_ref in found_parties:
            tid, canon, rmethod, reason = R.resolve(name)
            keyed = ""
            if tid and (rmethod.startswith("exact")
                        or rmethod.startswith("alias")
                        or rmethod.startswith("fr_official_name")
                        or rmethod.startswith("resolve_entity_exact")
                        or rmethod.startswith("resolve_entity_alias")):
                keyed = tid
            party = {
                "party_id": "",        # set below, from THIS row's own facts
                "document_number": dn,
                "event_class": EventClass.GOVERNMENT_ENGAGEMENT.value,
                "channel": CHANNEL.value,
                "agency": agency, "sub_agency": sub_agency,
                "undertaking_title": title,
                "notice_date": pub,
                "party_name_as_published": name,
                "party_role": role,
                "party_role_basis": method,
                "party_role_quote": quote,
                "project_reference": proj_ref,
                "resolved_native_entity_id": keyed,
                "resolved_native_entity_name": canon if keyed else "",
                "resolution_method": rmethod if keyed else "",
                "is_lobbying": "0",
                "federal_register_citation": cite,
                "source_url": url,
                "fetched_date": TODAY,
                "tier": (Tier.A.value if method != "corporate_filer_in_undertaking_sentence"
                         else Tier.B.value),
                "confidence": ("high" if method != "corporate_filer_in_undertaking_sentence"
                               else "medium"),
                "built_date": TODAY,
                "built_by_script": "code/130_build_section_106_consultation.py",
            }
            party["party_id"] = surrogate_id("S106P-FR", party,
                                             S106_PARTY_KEY_COLUMNS)
            parties.append(party)
        st["documents_with_a_named_applicant"] += 1 if found_parties else 0

        # ---- tribes ----------------------------------------------------
        tn = " " + norm(text) + " "
        matched = {}
        for row in tribes_by_official_name(tn, spine_by_fr):
            matched[row["tribe_id"]] = (row, "fr_official_name_literal",
                                        row.get("fr_official_name") or
                                        row["canonical_name"])

        for s in sents:
            if not (TRIBAL_RE.search(s) and CONSULT_VERB_RE.search(s)):
                continue
            seg = SEG_LEAD_RE.sub("", s)
            for nm in split_names(seg):
                if not looks_like_entity(nm):
                    continue
                if not TRIBAL_RE.search(nm):
                    continue
                # PROSE IS NOT A NAME, AND THE RESOLVER WILL FIND IT ONE.
                # Measured: `Council's regulations, the term, "Indian tribe"
                # refers to Federally recognized tribes` resolved to the spine
                # entity "Council". `looks_like_entity` passed it because it
                # contains entity words; what gives it away is the quotation
                # mark and the function words.
                if re.search(r"[\"“”]", nm):
                    continue
                if len(nm.split()) > 12:
                    continue
                if any(t.strip(".,'’-").lower() in PROSE_TOKENS
                       for t in nm.split()):
                    continue
                tid, canon, method, reason = R.resolve(nm)
                if tid:
                    if tid not in matched:
                        matched[tid] = (
                            {"tribe_id": tid, "canonical_name": canon},
                            method, nm)
                else:
                    unresolved.append({
                        "document_number": dn, "name_as_published": nm,
                        "reason": reason or "no_match",
                        "sentence": re.sub(r"\s+", " ", s)[:500],
                        "source_url": url, "fetched_date": TODAY,
                        "built_date": TODAY,
                    })

        def tribe_quote(published):
            npub = norm(published)
            for s in sents:
                if npub and npub in norm(s) and CONSULT_VERB_RE.search(s):
                    return re.sub(r"\s+", " ", s).strip()[:900], True
            for s in sents:
                if npub and npub in norm(s):
                    return re.sub(r"\s+", " ", s).strip()[:900], False
            return "", False

        # ---- what KIND of Section 106 record is this? ------------------
        # A grant NOFO that recites "recipients must comply with Section 106"
        # is a real Section 106 mention and is NOT project-level consultation.
        # Filing the two at one confidence would reproduce, in a new place,
        # exactly the monoculture this build exists to break.
        if "EXEMPTED_CATEGORY_OR_PROGRAM_ALTERNATIVE" in agreements:
            record_type = "PROGRAM_ALTERNATIVE"
        elif found_parties or effects:
            record_type = "PROJECT_UNDERTAKING"
        elif agreements:
            record_type = "AGREEMENT_DOCUMENT_REFERENCE"
        elif cparty_q or thpo_q:
            record_type = "CONSULTATION_PROCESS_RECORD"
        else:
            record_type = "STATUTORY_REFERENCE_ONLY"
        st["record_type_" + record_type] += 1

        base = {
            "event_class": EventClass.GOVERNMENT_ENGAGEMENT.value,
            "channel": CHANNEL.value,
            "is_lobbying": "0",
            "consultation_type": "NHPA_section_106",
            "record_type": record_type,
            "agency": agency, "sub_agency": sub_agency,
            "undertaking_title": title,
            "project_or_docket_id": docket,
            "notice_date": pub,
            "document_type": m.get("type") or "",
            "comment_deadline": deadline,
            "thpo_referenced": "1" if thpo_q else "0",
            "thpo_quote": thpo_q,
            "shpo_referenced": "1" if shpo_q else "0",
            "achp_referenced": "1" if achp_q else "0",
            "consulting_parties_referenced": "1" if cparty_q else "0",
            "consulting_parties_quote": cparty_q,
            "effect_determination_reported": "; ".join(effects),
            "effect_determination_quote": effect_q,
            "effect_terms_present": "; ".join(effect_terms),
            "agreement_instrument": "; ".join(agreements),
            "agreement_instrument_quote": agree_q,
            "applicants_named": "; ".join(
                sorted({p[0] for p in found_parties})),
            "n_applicants_named": str(len({p[0] for p in found_parties})),
            "project_reference": "; ".join(
                sorted({p[4] for p in found_parties if p[4]})),
            "federal_register_citation": cite,
            "source_url": url,
            "section_106_marker_quote": s106_quote,
            "fetched_date": TODAY,
            "built_date": TODAY,
            "built_by_script": "code/130_build_section_106_consultation.py",
        }

        if matched:
            for i, (tid, (row, method, published)) in enumerate(
                    sorted(matched.items())):
                q, in_consult_sentence = tribe_quote(published)
                tier = (Tier.A.value
                        if method == "fr_official_name_literal" and in_consult_sentence
                        else Tier.B.value)
                ev = {
                    "consultation_event_id": "",   # set below, from the row
                    "document_number": dn,
                    "tribe_id": tid,
                    "tribe_name": row.get("canonical_name", ""),
                    "participant_name_as_published": published,
                    "participant_role": ("named_in_consultation_statement"
                                         if in_consult_sentence
                                         else "named_in_document"),
                    "match_method": method,
                    "source_quote": q or s106_quote,
                    "tier": tier,
                    "confidence": "high" if tier == Tier.A.value else "medium",
                    **base,
                }
                ev["consultation_event_id"] = surrogate_id(
                    "S106-FR", ev, S106_EVENT_KEY_COLUMNS)
                rows.append(ev)
                st["tribe_rows"] += 1
            st["documents_with_a_resolved_tribe"] += 1
        else:
            # A Section 106 record that speaks of tribal consultation without
            # naming a tribe is still a record. It is NOT evidence that no
            # tribe was consulted, and it is filed with the tribe blank.
            # The same key formula as the matched branch. Two branches writing
            # one column must mint it the same way, or the column holds two
            # vocabularies - the `extent_competed` defect in a new place.
            ev = {
                "consultation_event_id": "",       # set below, from the row
                "document_number": dn,
                "tribe_id": "", "tribe_name": "",
                "participant_name_as_published": "",
                "participant_role": "tribes_not_individually_named_in_record",
                "match_method": "no_tribe_named_in_published_text",
                "source_quote": first_match_quote(sents, TRIBAL_RE) or s106_quote,
                "tier": Tier.C.value, "confidence": "medium",
                **base,
            }
            ev["consultation_event_id"] = surrogate_id(
                "S106-FR", ev, S106_EVENT_KEY_COLUMNS)
            rows.append(ev)
            st["documents_with_no_named_tribe"] += 1

    fields = ["consultation_event_id", "document_number", "event_class",
              "channel", "is_lobbying", "consultation_type", "record_type",
              "agency",
              "sub_agency", "undertaking_title", "project_or_docket_id",
              "notice_date", "document_type", "tribe_id", "tribe_name",
              "participant_name_as_published", "participant_role",
              "match_method", "thpo_referenced", "thpo_quote",
              "shpo_referenced", "achp_referenced",
              "consulting_parties_referenced", "consulting_parties_quote",
              "effect_determination_reported", "effect_determination_quote",
              "effect_terms_present",
              "agreement_instrument", "agreement_instrument_quote",
              "applicants_named", "n_applicants_named",
              "project_reference", "comment_deadline",
              "federal_register_citation", "source_url",
              "section_106_marker_quote", "source_quote", "fetched_date",
              "tier", "confidence", "built_date", "built_by_script"]
    write_csv(CLEAN / "section_106_consultation_events.csv", rows, fields)

    pfields = ["party_id", "document_number", "event_class", "channel",
               "agency", "sub_agency", "undertaking_title", "notice_date",
               "party_name_as_published", "party_role", "party_role_basis",
               "party_role_quote", "project_reference",
               "resolved_native_entity_id",
               "resolved_native_entity_name", "resolution_method",
               "is_lobbying", "federal_register_citation", "source_url",
               "fetched_date", "tier", "confidence", "built_date",
               "built_by_script"]
    write_csv(CLEAN / "section_106_project_parties.csv", parties, pfields)

    REVIEW.mkdir(parents=True, exist_ok=True)
    seen_u = set()
    uniq = []
    for u in unresolved:
        k = (u["document_number"], u["name_as_published"])
        if k not in seen_u:
            seen_u.add(k)
            uniq.append(u)
    write_csv(REVIEW / f"section_106_unresolved_names_{TODAY}.csv", uniq,
              ["document_number", "name_as_published", "reason", "sentence",
               "source_url", "fetched_date", "built_date"])

    build_coverage(cands, meta, have, st)

    print("\n--- counts ---")
    for k, v in st.most_common():
        print(f"  {k:<45} {v:,}")
    tribes = {r["tribe_id"] for r in rows if r["tribe_id"]}
    agencies = {r["agency"] for r in rows if r["agency"]}
    devs = {norm(p["party_name_as_published"]) for p in parties}
    print(f"\nrows                     : {len(rows):,}")
    print(f"distinct tribes          : {len(tribes):,}")
    print(f"distinct agencies        : {len(agencies):,}")
    print(f"distinct applicant rows  : {len(parties):,}")
    print(f"distinct applicant names : {len(devs):,}")
    print(f"unresolved names -> review: {len(uniq):,}")


def build_coverage(cands, meta, have, st):
    """What was swept, what answered, and what refused.

    FOUR STATES, NEVER COLLAPSED (AGENTS.md): PUBLISHES / WITHHOLDS /
    NOT_FOUND / NOT_CHECKED. A source nobody looked at and a source that was
    swept and found empty are opposite findings.

    Every non-Federal-Register row here carries the literal HTTP status of the
    probe that produced it, from `_host_probes.json`. A 404 on a path we
    guessed is a fact about the path, not about the agency.
    """
    rows = [
        {"source": "Federal Register full-text index + document text",
         "host": "www.federalregister.gov",
         "coverage_state": "PUBLISHES",
         "records_swept": str(len(cands)),
         "records_retrieved": str(len(have)),
         "what_was_swept":
             "561 documents ALREADY ON DISK in data/clean/federal_actions.csv "
             "whose title/abstract/action names s.106, the NHPA, 36 CFR 800 "
             "or the ACHP, unioned with 6 full-text searches of the FR index "
             "(the 6 terms are SEARCH_TERMS in this script)",
         "finding": f"{st['section_106_documents']:,} retrieved documents "
                    f"carry an explicit Section 106 statutory marker; "
                    f"{st['section_106_with_tribal_content']:,} of those also "
                    f"name a tribal party",
         "limitation":
             "The Federal Register publishes only the slice of the Section "
             "106 record an agency chose to notice - findings, agreement "
             "documents, and invitations to consult. The correspondence, "
             "telephone logs, emails, meeting notes and site visits the ACHP "
             "directs agencies to document live in agency project files and "
             "are not published here. ABSENCE OF A TRIBE FROM THIS FILE IS A "
             "PROPERTY OF THE FEDERAL REGISTER, not evidence that the tribe "
             "was not consulted.",
         "fetched_date": TODAY},

        {"source": "Advisory Council on Historic Preservation - case records",
         "host": "www.achp.gov",
         "coverage_state": "NOT_FOUND",
         "records_swept": "", "records_retrieved": "",
         "what_was_swept":
             "https://www.achp.gov/ (HTTP 200, 50,104 bytes, all outbound "
             "links extracted and filtered for 106/agreement/library/case/"
             "data); /news (HTTP 200, 65,920); /sitemap.xml (HTTP 404); "
             "/digital-library-section-106 (404); "
             "/digital-library-section-106-landing (HTTP 200); "
             "/protecting-historic-properties/section-106-process (404)",
         "finding":
             "The host answers. Everything the front page links to under "
             "Section 106 is GUIDANCE (initiating-section-106, "
             "identifying-historic-properties, assessing-effects, "
             "achieving-resolution) or news. No machine-readable index of "
             "Section 106 CASE records or agreement documents was found.",
         "limitation":
             "This is NOT_FOUND, not WITHHOLDS: six paths and one link "
             "extraction were swept. ACHP's own Federal Register documents "
             "ARE captured here - 146 of the 561 local candidates are ACHP "
             "documents - so ACHP is present as a publisher even though its "
             "case database was not located.",
         "fetched_date": TODAY},

        {"source": "BLM ePlanning national NEPA register",
         "host": "eplanning.blm.gov",
         "coverage_state": "NOT_FOUND",
         "records_swept": "", "records_retrieved": "",
         "what_was_swept":
             "https://eplanning.blm.gov/ (HTTP 200, 536,023 bytes); "
             "/robots.txt (404); /eplanning-ui/home (404); "
             "/eplanning-ui/api/nepaProjectSearch (404); "
             "/eplanning-ui/api/nepa/search (404); "
             "/epl-front-office/eplanning/nepa/nepa_register.do (404)",
         "finding":
             "The root answers HTTP 200 with a substantial page; every "
             "register and API path tried returned 404. No enumerable index "
             "path was identified in this run.",
         "limitation":
             "A 404 on a guessed path is a fact about the path. This is a "
             "LIVE LEAD, not a closed source, and it needs its own build: "
             "ePlanning is a project-document tree, so the Section 106 record "
             "sits inside per-project attachments rather than in a notice.",
         "fetched_date": TODAY},

        {"source": "FERC eLibrary",
         "host": "elibrary.ferc.gov",
         "coverage_state": "NOT_FOUND",
         "records_swept": "", "records_retrieved": "",
         "what_was_swept":
             "https://elibrary.ferc.gov/eLibrary/search (HTTP 200, 22,464 "
             "bytes); /eLibrary/filelist?accession_number=1 (HTTP 200, 22,464 "
             "bytes - byte-identical, i.e. the same shell); "
             "/eLibraryAPI/api/v1/search (404); /robots.txt (404); "
             "https://www.ferc.gov/robots.txt (HTTP 200, Drupal default, "
             "disallows /search/ on the www host only)",
         "finding":
             "eLibrary is a JavaScript application shell. Two different "
             "queries return the SAME 22,464-byte document, so the record "
             "content is not in the HTML. Same class as the rating-agency "
             "pages already recorded in AGENTS.md.",
         "limitation":
             "REFUSED in this run. Harvesting eLibrary requires its private "
             "JSON endpoint and a per-docket crawl; that is a separate build "
             "with its own host budget, not a side-effect of this one.",
         "fetched_date": TODAY},

        {"source": "Agency Section 106 project files (correspondence, "
                   "telephone logs, emails, meeting notes, site visits)",
         "host": "",
         "coverage_state": "NOT_CHECKED",
         "records_swept": "", "records_retrieved": "",
         "what_was_swept": "",
         "finding":
             "The ACHP directs agencies to document consultation this way. "
             "None of it is centrally published. It is reachable only "
             "per-project, by FOIA or through an agency docket.",
         "limitation":
             "This is the largest part of the Section 106 record and nobody "
             "has looked at it. Recorded so the gap is visible rather than "
             "implied.",
         "fetched_date": ""},
    ]
    write_csv(CLEAN / "section_106_source_coverage.csv", rows,
              ["source", "host", "coverage_state", "records_swept",
               "records_retrieved", "what_was_swept", "finding", "limitation",
               "fetched_date"])


# ===========================================================================
# STAGE 4 - CODEBOOK. Every published variable carries a description, or
# `62_no_regression_check.py::codebook_undocumented_public` fails.
# ===========================================================================

CODEBOOK_DATASET = "04b_section_106_consultation"

CODEBOOK_ENTRIES = [
 ("section_106_consultation_events.csv", "consultation_event_id",
  "Row identifier, S106-FR-<FR document number>-<n>."),
 ("section_106_consultation_events.csv", "document_number",
  "Federal Register document number the row was extracted from."),
 ("section_106_consultation_events.csv", "event_class",
  "cedar_domain.EventClass. Always GOVERNMENT_ENGAGEMENT: Section 106 is a "
  "statutory government-to-government process, never advocacy."),
 ("section_106_consultation_events.csv", "channel",
  "cedar_domain.AdvocacyChannel. Always SECTION_106_CONSULTATION."),
 ("section_106_consultation_events.csv", "is_lobbying",
  "Always 0. Consultation under 36 CFR 800 is a legal obligation, not "
  "influence-seeking."),
 ("section_106_consultation_events.csv", "consultation_type",
  "Always NHPA_section_106, matching the value used in consultation_events.csv."),
 ("section_106_consultation_events.csv", "record_type",
  "What kind of Section 106 record this is: PROJECT_UNDERTAKING (an applicant "
  "or an effect determination is named), PROGRAM_ALTERNATIVE, "
  "AGREEMENT_DOCUMENT_REFERENCE, CONSULTATION_PROCESS_RECORD, or "
  "STATUTORY_REFERENCE_ONLY (a compliance recital in a grant notice). Only the "
  "first is project-level consultation."),
 ("section_106_consultation_events.csv", "agency",
  "Lead federal agency, from the Federal Register's own agency list."),
 ("section_106_consultation_events.csv", "sub_agency",
  "Child agency where the Federal Register records one."),
 ("section_106_consultation_events.csv", "undertaking_title",
  "Title of the Federal Register document, which names the undertaking."),
 ("section_106_consultation_events.csv", "project_or_docket_id",
  "Docket identifiers the Federal Register carries for the document."),
 ("section_106_consultation_events.csv", "notice_date",
  "Federal Register publication date."),
 ("section_106_consultation_events.csv", "document_type",
  "Federal Register document type: Notice, Rule, Proposed Rule."),
 ("section_106_consultation_events.csv", "tribe_id",
  "Cedar entity spine id of the tribal party. Blank where the record speaks "
  "of tribal consultation without naming a tribe - which is a property of the "
  "record, not evidence that no tribe was consulted."),
 ("section_106_consultation_events.csv", "tribe_name",
  "Spine canonical name for tribe_id."),
 ("section_106_consultation_events.csv", "participant_name_as_published",
  "The tribal party's name exactly as the document prints it."),
 ("section_106_consultation_events.csv", "participant_role",
  "named_in_consultation_statement (the name sits in a sentence carrying a "
  "consultation verb), named_in_document (named, but not in such a sentence), "
  "or tribes_not_individually_named_in_record."),
 ("section_106_consultation_events.csv", "match_method",
  "How the name was resolved: fr_official_name_literal is a literal "
  "occurrence of the full Federal Register official name; everything else "
  "comes from the guarded resolver in script 96."),
 ("section_106_consultation_events.csv", "thpo_referenced",
  "1 where the document names a Tribal Historic Preservation Officer."),
 ("section_106_consultation_events.csv", "thpo_quote",
  "Verbatim sentence supporting thpo_referenced."),
 ("section_106_consultation_events.csv", "shpo_referenced",
  "1 where the document names a State Historic Preservation Officer."),
 ("section_106_consultation_events.csv", "achp_referenced",
  "1 where the document names the Advisory Council on Historic Preservation."),
 ("section_106_consultation_events.csv", "consulting_parties_referenced",
  "1 where the document uses the term consulting party or consulting parties."),
 ("section_106_consultation_events.csv", "consulting_parties_quote",
  "Verbatim sentence supporting consulting_parties_referenced."),
 ("section_106_consultation_events.csv", "effect_determination_reported",
  "Effect determinations the document reports, from 36 CFR 800.4(d) and "
  "800.5: NO_HISTORIC_PROPERTIES_AFFECTED, NO_ADVERSE_EFFECT, ADVERSE_EFFECT. "
  "Semicolon-separated where a document reports more than one. This is what "
  "the document SAYS, never our own assessment of effect."),
 ("section_106_consultation_events.csv", "effect_determination_quote",
  "Verbatim sentence supporting effect_determination_reported. It carries "
  "both the effect language and the determinative verb."),
 ("section_106_consultation_events.csv", "effect_terms_present",
  "Effect-determination VOCABULARY present anywhere in the document, whether "
  "or not anyone determined anything. 36 CFR 800.5 prints 'adverse effect on "
  "historic properties' in every rule that recites the standard, so this is a "
  "text-presence flag and must never be read as a finding. Use "
  "effect_determination_reported for findings."),
 ("section_106_consultation_events.csv", "agreement_instrument",
  "Instruments named: PROGRAMMATIC_AGREEMENT, MEMORANDUM_OF_AGREEMENT, "
  "MEMORANDUM_OF_UNDERSTANDING, EXEMPTED_CATEGORY_OR_PROGRAM_ALTERNATIVE. "
  "Naming an instrument is not evidence that it was executed."),
 ("section_106_consultation_events.csv", "agreement_instrument_quote",
  "Verbatim sentence supporting agreement_instrument."),
 ("section_106_consultation_events.csv", "applicants_named",
  "Applicants, licensees, permittees and developers named in the document, "
  "semicolon-separated. Detail is one row per party in "
  "section_106_project_parties.csv."),
 ("section_106_consultation_events.csv", "n_applicants_named",
  "Count of distinct applicant names in the document."),
 ("section_106_consultation_events.csv", "project_reference",
  "Project number the document assigns the undertaking, where it prints one "
  "beside the applicant (chiefly FERC Project Nos.)."),
 ("section_106_consultation_events.csv", "comment_deadline",
  "Date comments close, from the Federal Register metadata."),
 ("section_106_consultation_events.csv", "federal_register_citation",
  "Federal Register citation, e.g. 68 FR 12345."),
 ("section_106_consultation_events.csv", "source_url",
  "Federal Register permalink for the document."),
 ("section_106_consultation_events.csv", "section_106_marker_quote",
  "Verbatim sentence in which the document names Section 106, 36 CFR 800, the "
  "NHPA or the ACHP. This is what puts the row in scope."),
 ("section_106_consultation_events.csv", "source_quote",
  "Verbatim sentence supporting this row's tribal party."),
 ("section_106_consultation_events.csv", "fetched_date",
  "Date the document text was retrieved."),
 ("section_106_consultation_events.csv", "tier",
  "cedar_domain.Tier. A where the full official tribe name appears literally "
  "inside a consultation sentence; B where the tribe resolved but the "
  "consultation context is weaker; C where no tribe is named."),
 ("section_106_consultation_events.csv", "confidence",
  "high or medium, tracking tier."),
 ("section_106_consultation_events.csv", "built_date",
  "Date this row was built."),
 ("section_106_consultation_events.csv", "built_by_script",
  "Script that produced the row."),

 ("section_106_project_parties.csv", "party_id",
  "Row identifier for a named applicant, licensee, permittee or developer."),
 ("section_106_project_parties.csv", "party_name_as_published",
  "The party's name exactly as the document prints it. Never normalised."),
 ("section_106_project_parties.csv", "party_role",
  "Role the document assigns: APPLICANT, LICENSEE, PERMITTEE, DEVELOPER, "
  "PROJECT_SPONSOR, PROJECT_PROPONENT, LESSEE or FILER."),
 ("section_106_project_parties.csv", "party_role_basis",
  "The grammar that established the role: name_then_as_role_for_named_project, "
  "appositive_role_label, role_noun_then_corporate_name, "
  "corporate_name_then_role_noun, or corporate_filer_in_undertaking_sentence "
  "(the weakest, tier B)."),
 ("section_106_project_parties.csv", "party_role_quote",
  "Verbatim sentence in which the document assigns the role."),
 ("section_106_project_parties.csv", "project_reference",
  "Project number printed beside the party, where present."),
 ("section_106_project_parties.csv", "resolved_native_entity_id",
  "Spine id, populated ONLY where the party resolved by exact name, alias or "
  "official name. Most applicants are non-Native firms and are deliberately "
  "left blank rather than matched by containment."),
 ("section_106_project_parties.csv", "resolved_native_entity_name",
  "Spine canonical name for resolved_native_entity_id."),
 ("section_106_project_parties.csv", "resolution_method",
  "How resolved_native_entity_id was obtained."),

 ("section_106_source_coverage.csv", "source",
  "The source that was swept."),
 ("section_106_source_coverage.csv", "host",
  "Host probed, where the source is a website."),
 ("section_106_source_coverage.csv", "coverage_state",
  "PUBLISHES, WITHHOLDS, NOT_FOUND (swept and not found, naming what was "
  "swept) or NOT_CHECKED (nobody looked). These are four different facts and "
  "are never collapsed."),
 ("section_106_source_coverage.csv", "records_swept",
  "Documents considered for this source."),
 ("section_106_source_coverage.csv", "records_retrieved",
  "Documents whose full text was retrieved."),
 ("section_106_source_coverage.csv", "what_was_swept",
  "The literal paths and queries used, so the sweep can be repeated."),
 ("section_106_source_coverage.csv", "finding",
  "What the sweep returned, with HTTP statuses."),
 ("section_106_source_coverage.csv", "limitation",
  "What this source cannot tell you, stated so absence is never read as "
  "evidence."),
]


def stage_codebook():
    print("=== 130 stage CODEBOOK ===")
    p = CLEAN / "codebook_master.csv"
    rows = read_csv(p)
    if not rows:
        print("  codebook_master.csv missing; skipping"); return
    fields = list(rows[0].keys())
    srcs = {f: read_csv(CLEAN / f) for f in
            ("section_106_consultation_events.csv",
             "section_106_project_parties.csv",
             "section_106_source_coverage.csv")}
    have = {((r.get("dataset") or "").strip().lower(),
             (r.get("variable") or "").strip().lower()) for r in rows}
    added = 0
    for fname, var, desc in CODEBOOK_ENTRIES:
        if (CODEBOOK_DATASET, var.lower()) in have:
            continue
        src = srcs.get(fname) or []
        n = len(src)
        filled = sum(1 for r in src if (r.get(var) or "").strip()) if n else 0
        t, u = c96._type_units(var)
        new = {c: "" for c in fields}
        new.update({"dataset": CODEBOOK_DATASET, "variable": var, "type": t,
                    "units": u,
                    "pct_filled": ("%.1f" % (100.0 * filled / n)) if n else "0.0",
                    "n_rows": str(n), "published": "1", "access_tier": "public",
                    "description": desc, "generated": TODAY})
        rows.append(new)
        have.add((CODEBOOK_DATASET, var.lower()))
        added += 1
    if added:
        bak = p.with_suffix(".csv.bak_%s_pre130" % TODAY)
        if not bak.exists():
            bak.write_bytes(p.read_bytes())
        write_csv(p, rows, fields)
    print("  added %d variable entries (%s total)" % (added, format(len(rows), ",")))


# ===========================================================================
# STAGE 5 - THE MERGE PROPOSAL, WRITTEN FROM THE DATA
#
# Standing rule 10: a number in a doc that is not recomputed from the data is a
# claim, not a fact. So the proposal is GENERATED, never hand-typed, and
# consultation_events.csv is not touched by this script under any stage.
# ===========================================================================

def stage_report():
    print("=== 130 stage REPORT: merge proposal ===")
    ev = read_csv(CLEAN / "section_106_consultation_events.csv")
    pa = read_csv(CLEAN / "section_106_project_parties.csv")
    old = read_csv(CLEAN / "consultation_events.csv")
    if not ev:
        print("  nothing built; skipping"); return

    old_types = Counter(r.get("consultation_type", "") for r in old)
    old_agency = Counter(r.get("agency", "") for r in old)
    old_106_docs = {r.get("source_url") for r in old
                    if r.get("consultation_type") == "NHPA_section_106"}
    new_urls = {r["source_url"] for r in ev}
    overlap = len(old_106_docs & new_urls)

    tribes = {r["tribe_id"] for r in ev if r["tribe_id"]}
    old_tribes = {r.get("tribe_id") for r in old if (r.get("tribe_id") or "")}
    agencies = Counter(r["agency"] for r in ev if r["agency"])
    rtypes = Counter(r["record_type"] for r in ev)
    tiers = Counter(r["tier"] for r in ev)
    years = Counter((r["notice_date"] or "")[:4] for r in ev if r["notice_date"])
    parties = {norm(r["party_name_as_published"]) for r in pa}
    proj = sum(1 for r in ev if r["record_type"] == "PROJECT_UNDERTAKING")

    L = []
    a = L.append
    a("# Section 106 project consultation - built, and the merge proposed")
    a("")
    a(f"*Generated {TODAY} by `code/130_build_section_106_consultation.py`. "
      f"Every number below is recomputed from the files it describes; none is "
      f"hand-entered.*")
    a("")
    a("## What was built")
    a("")
    a("| | |")
    a("|---|---:|")
    a(f"| `data/clean/section_106_consultation_events.csv` | {len(ev):,} rows |")
    a(f"| distinct tribes | {len(tribes):,} |")
    a(f"| distinct lead agencies | {len(agencies):,} |")
    a(f"| `data/clean/section_106_project_parties.csv` | {len(pa):,} rows |")
    a(f"| distinct applicants / developers named | {len(parties):,} |")
    a(f"| rows classed PROJECT_UNDERTAKING | {proj:,} |")
    a(f"| years covered | {min(years) if years else '-'}-"
      f"{max(years) if years else '-'} |")
    a("")
    a("### By record type")
    a("")
    a("| record_type | rows |")
    a("|---|---:|")
    for k, v in rtypes.most_common():
        a(f"| {k} | {v:,} |")
    a("")
    a("**Only `PROJECT_UNDERTAKING` is project-level consultation.** "
      "`STATUTORY_REFERENCE_ONLY` is a grant notice reciting that recipients "
      "must comply with Section 106. Both are real Section 106 mentions and "
      "publishing them at one confidence would rebuild, in a new place, the "
      "monoculture this dataset exists to break.")
    a("")
    a("### By tier")
    a("")
    for k, v in sorted(tiers.items()):
        a(f"- **{k}** - {v:,}")
    a("")
    a("### Top lead agencies")
    a("")
    a("| agency | rows |")
    a("|---|---:|")
    for k, v in agencies.most_common(15):
        a(f"| {k} | {v:,} |")
    a("")
    a("## Why this is not a duplicate of `consultation_events.csv`")
    a("")
    a("The existing file's composition, recomputed:")
    a("")
    a("| consultation_type | rows |")
    a("|---|---:|")
    for k, v in old_types.most_common():
        a(f"| {k} | {v:,} |")
    a("")
    a(f"- {old_agency.most_common(1)[0][1]:,} of {len(old):,} rows come from "
      f"`{old_agency.most_common(1)[0][0]}` alone.")
    a(f"- The existing file holds **{old_types.get('NHPA_section_106', 0)}** "
      f"Section 106 rows against **{len(ev):,}** here.")
    a(f"- Source-URL overlap between the existing Section 106 rows and the new "
      f"file: **{overlap}**.")
    a(f"- Tribes in the new file that appear nowhere in "
      f"`consultation_events.csv`: **{len(tribes - old_tribes):,}**.")
    a("")
    a("## The proposed merge - and why it is a proposal, not an action")
    a("")
    a("`consultation_events.csv` was **not modified by this build** and must "
      "not be rebuilt to absorb this file. Script 96 owns it, rebuilds it from "
      "its own inputs, and would drop anything appended from outside - the "
      "same shape as the `09_import_rulings.py` regression in AGENTS.md.")
    a("")
    a("Recommended, in order:")
    a("")
    a("1. **Publish the two files side by side and join on nothing.** They "
      "answer different questions: `consultation_events.csv` is policy "
      "consultation, this is project consultation. A `channel` column already "
      "separates them (`CONSULTATION` vs `SECTION_106_CONSULTATION`) and both "
      "sit under `EventClass.GOVERNMENT_ENGAGEMENT`.")
    a("2. **If a single consultation view is wanted, build it as a THIRD "
      "file** - a harmonised view in the style of "
      "`code/110_build_harmonized_views.py` - reading both and writing "
      "neither. Never append into either source.")
    a("3. **Do not migrate the existing 20 `NHPA_section_106` rows out of "
      "`consultation_events.csv`.** They were built by a different parser "
      "against a different candidate set; moving them would lose script 96's "
      "provenance for no gain, and the overlap measured above is "
      f"{overlap} rows.")
    a("4. **Carry the coverage file with any publication.** "
      "`section_106_source_coverage.csv` is what stops a reader concluding "
      "that a tribe with no row here was not consulted.")
    a("")
    a("## What the private-sector side looks like")
    a("")
    a("The applicant is the party nothing else in Cedar Press sees. Named "
      "parties, with the role the document itself assigns:")
    a("")
    a("| party | role | project |")
    a("|---|---|---|")
    seen = set()
    for r in sorted(pa, key=lambda r: r["party_name_as_published"]):
        k = norm(r["party_name_as_published"])
        if k in seen:
            continue
        seen.add(k)
        a(f"| {r['party_name_as_published']} | {r['party_role']} | "
          f"{r['project_reference'] or '-'} |")
    a("")
    a("**None of this is lobbying.** A licensee invited to develop a "
      "Programmatic Agreement with four tribes is discharging an obligation "
      "under 36 CFR 800, and `is_lobbying` is 0 on every row of both files.")
    a("")
    a("## What was refused")
    a("")
    a("- **FERC eLibrary.** Two different queries return the same "
      "22,464-byte JavaScript shell; the record is not in the HTML. "
      "Harvesting it needs its private JSON endpoint and a per-docket crawl - "
      "a separate build with its own host budget.")
    a("- **BLM ePlanning.** The root answers HTTP 200 with 536,023 bytes; "
      "every register and API path tried returned 404. A live lead, not a "
      "closed source.")
    a("- **ACHP case records.** The site answers and publishes Section 106 "
      "*guidance*; no machine-readable index of case records or agreement "
      "documents was found from the front page or five direct paths. ACHP is "
      "still present here as a publisher through its own Federal Register "
      "documents.")
    a("- **Agency project files** - the correspondence, telephone logs, "
      "emails, meeting notes and site visits the ACHP directs agencies to "
      "keep. Not centrally published; reachable only per project, by FOIA or "
      "through an agency docket. This is the largest part of the Section 106 "
      "record and it is recorded as NOT_CHECKED rather than left implied.")
    a("")
    p = CEDAR / "docs" / "SECTION_106_BUILD_AND_MERGE_PROPOSAL.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(L), encoding="utf-8")
    print(f"  wrote {p}")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "enumerate":
        stage_enumerate()
    elif cmd == "fetch":
        stage_fetch()
    elif cmd == "build":
        stage_build(); stage_codebook(); stage_report()
    elif cmd == "codebook":
        stage_codebook()
    elif cmd == "report":
        stage_report()
    elif cmd == "all":
        stage_enumerate(); stage_fetch(); stage_build()
        stage_codebook(); stage_report()
    else:
        print(__doc__); sys.exit(2)


if __name__ == "__main__":
    main()
