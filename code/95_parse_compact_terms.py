#!/usr/bin/env python3
"""
Cedar Press - 95: parse the 707 tribal-state gaming compacts into structured
terms, and harvest the reporting obligations they impose.

WHAT THIS ADDS OVER 15c/15d/15e
-------------------------------
15d/15e produced `compact_terms.csv`: 1,311 rows over eight term types, keyed to
a version, each carrying a verbatim quote and a PDF page. That layer is correct
and is NOT rebuilt here. This script is the wide-vocabulary pass it deferred:

  * the digital-gaming fields that did not exist when the earlier enum was set
    (sports/event wagering, internet gaming, mobile scope),
  * the non-rate money terms (minimum payment, per-device payment, flat state
    payment, hotel-tax equivalent, other mitigation),
  * table and facility caps alongside device caps,
  * effective-date ranges on every term, so an amendment never overwrites the
    term it replaced,
  * and the reporting obligations, which are the reason to do this at all.

WHY A REPORTING OBLIGATION IS THE VALUABLE OUTPUT
-------------------------------------------------
A compact that orders a tribe to file a quarterly net-win certification with a
named state agency is telling us that a state agency HOLDS a quarterly net-win
series. That is a map to a public dataset nobody has pulled. So every such
clause is emitted to `compact_required_reports.csv` with its recipient, its
frequency, the fields it enumerates, and whatever the compact says about
disclosure - never an assumption that the file is public.

THE TWO RULES THIS FILE ENFORCES IN CODE
----------------------------------------
1. A CAP IS AN AUTHORISATION, NEVER A COUNT.
   Every cap row is stamped `measurement_type = AUTHORIZED_MAXIMUM`, and
   `cedar_domain.may_promote()` is asserted at startup to refuse
   AUTHORIZED_MAXIMUM -> ACTIVE_FLOOR_COUNT. A property authorised for 2,500
   devices may operate 900. The two numbers are not the same fact and this file
   must never let one become the other.

2. COMPACT-DERIVED REVENUE IS EXACT ARITHMETIC ONLY IF THE CONCEPT SURVIVES.
   Where a single flat rate applies to one defined base, `payment / rate` is a
   fact, and the row carries `formula_invertibility = INVERTIBLE_FLAT_RATE`.
   But the answer is revenue OF THE CONCEPT THE COMPACT NAMES. If the base is
   "Class III Net Win" the quotient is Class III electronic net win, not total
   casino revenue, so `revenue_concept` is copied verbatim from the compact and
   never generalised. Where a progressive schedule, a minimum, or a floor means
   the amount cannot be uniquely solved, the row is NOT invertible and carries a
   `bound_basis` naming what blocks the inversion. A factual bound is not a
   confidence interval; no interval is computed anywhere in this file.

   Scope matters as much as concept: a compact formula is almost always a
   TRIBE-level obligation. It becomes property-level evidence only where the
   clause itself is facility-scoped. `revenue_evidence_class` records which.

   No modelled property revenue is produced. That remains banned.

EVERY TERM CARRIES A VERBATIM QUOTE. A term that cannot be quoted is not
emitted - it goes to the unresolved review file with the reason.

TIERING
-------
Every term row is `confidence_tier = B`. These are algorithmic extractions with
receipts, not human rulings, and spec 10.1 lands automated results at B pending
review. The ENTITY keying is separate and inherits the tier already established
on `compacts.csv`.

Reads   data/clean/compacts.csv, compact_versions.csv
        data/raw/external/compacts/pdf/*.pdf   (page-wise, via PyMuPDF)
        data/spine/cedar_entity_spine.csv
Writes  data/clean/compact_structured_terms.csv
        data/clean/compact_required_reports.csv
        review/compact_parse_unresolved_<date>.csv
        docs/COMPACT_TERMS_BUILD_LOG.md
"""

import argparse
import csv
import importlib.util
import io
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import fitz  # PyMuPDF

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
INTERIM = CEDAR / "data" / "interim"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
DOCS = CEDAR / "docs"
EXT = CEDAR / "data" / "raw" / "external" / "compacts"
PDFDIR = EXT / "pdf"
PAGECACHE = INTERIM / "compact_pages"

TODAY = date.today().isoformat()

# The PDFs are local copies. The manifest records the copy date; the BIA index
# is the origin. Neither is invented, so both travel with every row.
FETCHED_DATE = "2026-08-05"

csv.field_size_limit(min(sys.maxsize, 2_000_000_000))

sys.path.insert(0, str(CEDAR / "code"))
from cedar_domain import (  # noqa: E402
    MeasurementType,
    REVENUE_EVIDENCE,
    Tier,
    may_promote,
)

_M33 = None


def resolve_entity(name, spine):
    """Delegate to the ONE resolver (AGENTS.md standing rule).

    Never re-implement name matching here: 33's version carries the diacritic
    fold, the corporate-form guard, and the containment guard that five
    measured misattributions paid for.
    """
    global _M33
    if _M33 is None:
        spec = importlib.util.spec_from_file_location(
            "m33", CEDAR / "code" / "33_apply_party_rulings.py")
        _M33 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_M33)
    return _M33.resolve_entity(name, spine)


# ---------------------------------------------------------------------------
# Startup self-checks. These are the project's two hard rules; if the shared
# vocabulary ever stops enforcing them, this build must not run at all.
# ---------------------------------------------------------------------------

def assert_guards():
    assert not may_promote(MeasurementType.AUTHORIZED_MAXIMUM,
                           MeasurementType.ACTIVE_FLOOR_COUNT), \
        "promotion guard is broken: AUTHORIZED_MAXIMUM must never reach ACTIVE_FLOOR_COUNT"
    assert not may_promote(MeasurementType.DERIVED_BOUND,
                           MeasurementType.ACTIVE_FLOOR_COUNT)
    assert "EXACT_DERIVED_PROPERTY_REVENUE" in REVENUE_EVIDENCE
    assert "BOUNDED_DERIVED_REVENUE" in REVENUE_EVIDENCE
    assert "TRIBE_LEVEL_REVENUE" in REVENUE_EVIDENCE
    assert "NO_REVENUE_OBSERVATION" in REVENUE_EVIDENCE


# ---------------------------------------------------------------------------
# Text helpers. The TOC guard, the approval-letter zoning and the fraction
# normaliser are carried over from 15d, where each one was paid for by a
# measured false positive on the 30-document adjudicated pilot.
# ---------------------------------------------------------------------------

def norm(s):
    return re.sub(r"[ \t]+", " ", (s or "").replace("\u00a0", " "))


DOTS = re.compile(r"\.{5,}|\. \. \. \.|\u00b7{5,}")
PAGENUM = re.compile(r"\s\d{1,3}\s*(?:\n|$)")


def page_toc_signals(page_text):
    """Page-level table-of-contents signals, computed ONCE per page.

    These used to be recomputed inside every match test. On a 600 KB
    instrument with thousands of candidate matches that turned a linear scan
    into a quadratic one and cost 14 seconds on a single document - the whole
    corpus went from minutes to hours on this one line."""
    return (page_text.count(".") > 0.18 * max(len(page_text), 1),
            bool(re.search(r"TABLE\s+OF\s+CONTENTS", page_text[:2500], re.I)))


def is_toc(window, signals):
    """A table-of-contents line looks like a provision and is not one. This was
    the dominant failure mode of the first pilot."""
    dotty, has_header = signals
    if dotty:
        return True
    if DOTS.search(window):
        return True
    if len(PAGENUM.findall(window)) >= 3:
        return True
    if (has_header and len(window) < 600
            and len(re.findall(r"\b\d{1,3}\b", window)) >= 4):
        return True
    return False


LETTER = re.compile(
    r"(Sincerely|Assistant Secretary\s*[-\u2013]?\s*Indian Affairs|"
    r"Principal Deputy Assistant Secretary|"
    r"Dear (Chairman|Chairwoman|President|Governor|Chairperson))", re.I)
BODY = re.compile(
    r"(WITNESSETH|^\s*RECITALS|TABLE\s+OF\s+CONTENTS|"
    r"^\s*(SECTION|ARTICLE|PART)\s+(1|I|ONE)\b|^\s*PREAMBLE)", re.I | re.M)


def letter_pages(pages):
    """The Secretary's transmittal letter is the LEADING run of pages before the
    instrument begins. Zoning matters because one 1997 approval letter states the
    compact does NOT provide substantial exclusivity - read as instrument text
    that sentence would have been recorded as exclusivity present."""
    first_body = None
    for i, p in enumerate(pages[:40]):
        if BODY.search(p):
            first_body = i
            break
    if first_body is None:
        last = -1
        for i, p in enumerate(pages[:10]):
            if LETTER.search(p):
                last = i
        return set(range(0, last + 1)) if last >= 0 else set()
    if not any(LETTER.search(p) for p in pages[:max(first_body, 1)]):
        return set()
    return set(range(0, first_body))


def num(s):
    """'2-1/2' -> 2.5 ; '12' -> 12 ; '7.5' -> 7.5"""
    s = (s or "").strip().replace(",", "")
    for frac, add in (("1/2", 0.5), ("1/4", 0.25), ("3/4", 0.75)):
        m = re.match(r"^(\d+)\s*[-\s]\s*" + re.escape(frac) + r"$", s)
        if m:
            return float(m.group(1)) + add
    try:
        f = float(s)
        return int(f) if f == int(f) else f
    except ValueError:
        return None


WORDNUM = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve "
    "thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split())}


def wordnum(s):
    return WORDNUM.get((s or "").strip().lower())


def ctx(t, m, before=220, after=300):
    a = max(0, m.start() - before)
    b = min(len(t), m.end() + after)
    return norm(t[a:b]).replace("\n", " ").strip()


def flat(s):
    """One-line value. A term value with an embedded newline breaks every
    consumer that reads the CSV with a naive splitter, and the newline carries
    no information - the verbatim record is `source_quote`, not `value`."""
    return re.sub(r"\s+", " ", (s or "")).strip()


def qkey(s):
    """Collapse a quote to its comparable core.

    BIA bundles frequently contain the same instrument twice - a scanned
    execution copy and a clean copy - and the two OCR slightly differently. Byte
    comparison sees two clauses; a human sees one. Folding to alphanumerics
    makes the duplicate visible without merging genuinely different clauses."""
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())[:220]


# A standard-form state compact (Arizona 2003/2021 is the clearest case) prints
# EVERY signatory tribe's allocation inside EVERY tribe's copy: "If the Tribe is
# the Ak-Chin Indian Community, the Tribe may operate a maximum of one (1)
# Gaming Facility". Read naively, the Yavapai-Apache compact yields Ak-Chin's
# cap. This is a REJECTION filter only - it never links a term to the named
# tribe, it only refuses to key it to the WRONG one.
COND_TRIBE = re.compile(
    r"[Ii]f\s+the\s+Tribe\s+is\s+(?:the\s+)?"
    r"([A-Z][\w'’\-\.]*(?:\s+[A-Z][\w'’\-\.]*){0,5})")
_STRUCT = {"tribe", "tribes", "nation", "nations", "band", "bands", "pueblo",
           "community", "indian", "indians", "of", "the", "and", "reservation",
           "rancheria", "colony", "village", "confederated", "tribal"}


def _toks(s):
    return {t for t in re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).split()
            if t and t not in _STRUCT}


def other_tribes_clause(q, tribe_name):
    """True when the window's terms are conditioned on a DIFFERENT tribe."""
    mine = _toks(tribe_name)
    for m in COND_TRIBE.finditer(q):
        if not (_toks(m.group(1)) & mine):
            return True
    return False


# ---------------------------------------------------------------------------
# Shared fragments.
# ---------------------------------------------------------------------------

DEVICE = (r"(?:gaming\s+devices?|gaming\s+machines?|slot\s+machines?|"
          r"video\s+lottery\s+terminals?|electronic\s+gaming\s+devices?|"
          r"player\s+terminals?|video\s+gaming\s+machines?|"
          r"electronic\s+games?\s+of\s+chance)")
TABLEGAME = (r"(?:table\s+games?|gaming\s+tables?|card\s+tables?|"
             r"house-?banked\s+(?:card\s+)?games?|banked\s+card\s+games?|"
             r"blackjack\s+tables?|card\s+games?\s+tables?)")
FACILITYNOUN = (r"(?:gaming\s+facilit(?:y|ies)|gaming\s+establishments?|"
                r"gaming\s+operations?|gaming\s+sites?|casinos?)")
PCT = r"(\d{1,2}(?:\.\d{1,3})?|\d{1,2}\s*[-\s]\s*(?:1/2|1/4|3/4))"
MONEY = r"\$\s*([\d][\d,]{0,15}(?:\.\d{1,2})?)"

STATE_PAY_ANCHOR = re.compile(
    r"(pay\s+(?:to\s+)?the\s+(?:State|Commonwealth)|payments?\s+to\s+the\s+State|"
    r"contribut\w+\s+to\s+the\s+State|tribal\s+contribution|revenue[- ]shar\w+|"
    r"state[\'\u2019]?s?\s+share|remit\w*\s+to\s+the\s+State|"
    r"shall\s+pay\s+the\s+State|revenue\s+sharing\s+trust\s+fund|"
    r"general\s+fund\s+of\s+the\s+State|"
    r"consideration\s+for\s+the\s+substantial\s+exclusivity)", re.I)

# Payout percentages, jackpot odds, installment fractions and money flowing FROM
# the state are not revenue shares. Every clause here was a measured v2 error.
RATE_REJECT = re.compile(
    r"(pay\s*out|payout|theoretical|amount\s+wagered|jackpot|"
    r"return\s+to\s+the\s+player|prize|odds|withhold|w-?2g|"
    r"interest|penalt|probability|hold\s+percentage|payback|"
    r"reduce[d]?\s+by|reduction\s+of|increase[d]?\s+by|"
    r"of\s+the\s+estimated|monthly\s+payment\s+shall\s+be|"
    r"payment\s+from\s+the\s+State|State\s+shall\s+pay|"
    r"to\s+eligible\s+tribes|any\s+increase\s+in)", re.I)

NEGATION = re.compile(
    r"(shall\s+not|may\s+not|is\s+not\s+authorized|are\s+not\s+authorized|"
    r"does\s+not\s+authorize|no\s+authority\s+to|prohibit\w*|"
    r"is\s+forbidden|unlawful|shall\s+be\s+unlawful|"
    r"nothing\s+(?:in\s+this|herein)\s+[^.]{0,60}authoriz)", re.I)

CONDITIONAL = re.compile(
    r"(in\s+the\s+event\s+(?:that\s+)?the\s+State|if\s+the\s+State\s+"
    r"(?:authorizes|legalizes|permits)|should\s+the\s+State\s+"
    r"(?:authorize|legalize|permit)|upon\s+enactment\s+of|"
    r"the\s+parties\s+(?:shall|will|agree\s+to)\s+(?:re)?negotiat)", re.I)

# ---------------------------------------------------------------------------
# CAP EXTRACTORS. All three stamp AUTHORIZED_MAXIMUM.
# ---------------------------------------------------------------------------

CAP_RX = [
    re.compile(r"(?:authorized\s+to\s+operate|may\s+operate|shall\s+(?:not\s+)?operate|"
               r"operate\s+no\s+more\s+than|limited\s+to|shall\s+not\s+exceed|"
               r"not\s+to\s+exceed|maximum\s+of|no\s+more\s+than|up\s+to)"
               r"\s+(?:a\s+total\s+of\s+)?([\d][\d,]{1,7})"
               r"\s*(?:\([^)]{0,30}\)\s*)?" + DEVICE, re.I),
    re.compile(r"(?:total\s+(?:number\s+of\s+)?|aggregate\s+(?:number\s+of\s+)?|"
               r"maximum\s+number\s+of\s+)" + DEVICE +
               r"[^.]{0,60}?(?:shall\s+not\s+exceed|is|shall\s+be)\s+([\d][\d,]{1,7})", re.I),
]
CAP_ANCHOR = re.compile(
    r"(authorized\s+to\s+operate|may\s+operate|number\s+of\s+gaming\s+devices|"
    r"gaming\s+device\s+allocation|authorized\s+number|maximum\s+number|"
    r"scope\s+of\s+gaming|shall\s+not\s+operate|slots\s+only)", re.I)
CAP_REJECT = re.compile(
    r"(transfer|payments?\s+shall\s+be\s+based|schedule\s+based\s+on|"
    r"so\s+long\s+as\s+the\s+tribe\s+operates[^.]{0,120}payment|"
    r"if\s+the\s+tribe\s+is\s+(?:the\s+)?navajo|"
    r"non-?tribal|racino|commercial\s+(?:casino|operator)|card\s?room|"
    r"pari-?mutuel\s+permit|"
    r"WHEREAS|\b(?:19|20)\d{2}\s+Compact\b|previously\s+authorized|"
    r"under\s+the\s+prior)", re.I)
CAP_SUBJECT = re.compile(
    r"(the\s+Tribes?\b[^.]{0,80}?(?:is|are|shall\s+be)\s+authorized|"
    r"the\s+Tribes?\s+(?:may|shall)\s+(?:not\s+)?operate|"
    r"the\s+(?:Tribes?|Pueblo|Nation|Band|Community)\b[^.]{0,60}?"
    r"(?:authorized\s+to\s+operate|may\s+operate|shall\s+operate)|"
    r"authorized\s+number\s+of\s+gaming\s+devices|"
    r"gaming\s+device\s+allocation)", re.I)

TABLECAP_RX = [
    re.compile(r"(?:authorized\s+to\s+operate|may\s+operate|shall\s+not\s+exceed|"
               r"not\s+to\s+exceed|maximum\s+of|no\s+more\s+than|limited\s+to|up\s+to)"
               r"\s+(?:a\s+total\s+of\s+)?([\d][\d,]{0,5})"
               r"\s*(?:\([^)]{0,30}\)\s*)?" + TABLEGAME, re.I),
    re.compile(r"(?:total\s+number\s+of\s+|maximum\s+number\s+of\s+|number\s+of\s+)"
               + TABLEGAME +
               r"[^.]{0,60}?(?:shall\s+not\s+exceed|shall\s+be\s+limited\s+to|shall\s+be)"
               r"\s+([\d][\d,]{0,5})", re.I),
]

FACCAP_RX = [
    re.compile(r"(?:may\s+(?:operate|establish|conduct\s+gaming\s+at)|"
               r"authorized\s+to\s+(?:operate|establish|conduct\s+gaming\s+at)|"
               r"shall\s+not\s+(?:operate|establish|exceed)|no\s+more\s+than|"
               r"not\s+to\s+exceed|limited\s+to|maximum\s+of)"
               r"\s+(?:a\s+total\s+of\s+)?(\d{1,2}|one|two|three|four|five|six|seven|"
               r"eight|nine|ten|eleven|twelve)"
               r"\s*(?:\(\s*\d{1,2}\s*\)\s*)?" + FACILITYNOUN, re.I),
    re.compile(r"(?:number\s+of\s+)" + FACILITYNOUN +
               r"[^.]{0,60}?(?:shall\s+not\s+exceed|shall\s+be\s+limited\s+to|shall\s+be)"
               r"\s+(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten)", re.I),
]
FACCAP_ANCHOR = re.compile(
    r"(the\s+Tribes?\b|the\s+(?:Pueblo|Nation|Band|Community)\b)", re.I)
FACCAP_REJECT = re.compile(
    r"(WHEREAS|non-?tribal|racino|commercial|square\s+feet|miles?\b|"
    r"class\s+II\s+only|per\s+facility|each\s+facility|"
    r"days?\b|years?\b|copies)", re.I)

# ---------------------------------------------------------------------------
# REVENUE-SHARE EXTRACTORS.
# ---------------------------------------------------------------------------

RATE_RX = [
    re.compile(r"(?:pay|contribute|remit|transfer)[^.]{0,140}?" + PCT
               + r"\s*(?:%|percent)", re.I),
    re.compile(PCT + r"\s*(?:%|percent)\s*\)?\s*(?:\([^)]{0,20}\)\s*)?"
               r"of\s+(?:the\s+|its\s+)?(?:annual\s+|quarterly\s+|adjusted\s+)?"
               r"(net\s+win|net\s+revenues?|gross\s+(?:gaming\s+)?revenues?|"
               r"adjusted\s+gross\s+(?:gaming\s+)?(?:receipts|revenues?)|"
               r"class\s+I{2,3}\s+net\s+win)", re.I),
]

TIER_RX = [
    re.compile(PCT + r"\s*(?:%|percent)\s+of\s+the\s+(first|next|last|remaining)"
               r"\s*\$?\s*([\d][\d,\.]{0,15})\s*(million|billion)?", re.I),
    re.compile(r"(?:in\s+excess\s+of|exceed(?:ing|s)?|over)\s+\$?\s*"
               r"([\d][\d,\.]{0,15})\s*(million|billion)?[^.]{0,60}?" + PCT
               + r"\s*(?:%|percent)", re.I),
    # Bracket amounts are often SPELLED OUT: New Mexico's "Three Percent (3%)
    # of the first Four Million Dollars ($4,000,000) of net win at each Gaming
    # Facility ... and Five Percent (5%) of the net win over the first Four
    # Million Dollars". Both digit-anchored forms above miss it, and the miss
    # is not cosmetic - without the tier row the instrument reads as a single
    # flat rate and gets marked INVERTIBLE, which would licence exact division
    # against a two-bracket schedule. Any bracket phrase counts.
    re.compile(PCT + r"\s*(?:%|percent)\s*\)?\s*(?:\([^)]{0,20}\)\s*)?"
               r"of\s+the\s+(first|next|last|remaining)\s+([^,;.]{1,70})", re.I),
]

BASE_RX = [
    re.compile(r"\"?(net\s+win|net\s+revenues?|gross\s+gaming\s+revenues?|"
               r"adjusted\s+gross\s+(?:gaming\s+)?(?:receipts|revenues?)|"
               r"class\s+I{2,3}\s+net\s+win)\"?\s*"
               r"(?:means|shall\s+mean|is\s+defined)", re.I),
]

# The base named alongside a rate. This is what `revenue_concept` records - the
# compact's own words, never a generalisation to "casino revenue".
CONCEPT_RX = re.compile(
    r"(class\s+I{2,3}\s+(?:electronic\s+)?net\s+win|net\s+win|"
    r"adjusted\s+net\s+win|adjusted\s+gross\s+(?:gaming\s+)?(?:receipts|revenues?)|"
    r"gross\s+gaming\s+revenues?|gross\s+revenues?|net\s+revenues?|"
    r"win\s+from\s+(?:gaming\s+devices?|class\s+I{2,3}\s+gaming))", re.I)

_CONCEPT_CORE = (r"(?:class\s+I{2,3}\s+)?(?:adjusted\s+)?(?:net\s+win|"
                 r"gross\s+(?:gaming\s+)?(?:revenues?|receipts)|net\s+revenues?)")
# A rate is PROPERTY-level evidence only when the REVENUE BASE is the property's
# own win. Nearby facility words are not enough, and getting this wrong is the
# whole risk of the exercise: Michigan's "two percent (2%) of the annual Net Win
# to the local units of government located in the immediate vicinity of each
# tribal casino" is a TRIBE-level base paid to local recipients, but every
# generic facility signal in the sentence points at "each tribal casino". Only a
# base phrase that itself binds the revenue to a facility qualifies.
#
# The determiner must be distributive (each / any / every / per) and the noun
# must be a PLACE. "the" and bare "operation" both had to go: California's
# "six percent (6.0%) of its Net Win from the operation of Gaming Devices"
# matched "the ... operation" and was wrongly promoted to property-level
# evidence, when "operation" there is the ACTIVITY of running devices across
# everything the tribe owns. Michigan's "two percent (2%) of the net win at
# each casino" is the real thing, and only the distributive form separates them.
_FAC_PLACE = r"(?:gaming\s+)?(?:facility|facilities|casino|casinos|establishment)"
FACILITY_SCOPED_BASE = re.compile(
    r"(" + _CONCEPT_CORE + r"\s+(?:of|at|from|generated\s+(?:at|by)|derived\s+from)"
    r"\s+(?:each|any|every|per)\s+(?:such\s+)?" + _FAC_PLACE + r"|"
    r"(?:each|any|every|per)\s+(?:such\s+)?" + _FAC_PLACE + r"[\'’]s\s+"
    + _CONCEPT_CORE + r"|"
    r"(?:facility|casino|establishment)[- ]level\s+" + _CONCEPT_CORE + r"|"
    + _CONCEPT_CORE + r"\s+(?:for|at)\s+(?:each|every|any|per)\s+"
    + _FAC_PLACE + r")", re.I)

MINPAY_RX = [
    re.compile(r"(?:minimum\s+(?:annual\s+|quarterly\s+|monthly\s+)?"
               r"(?:payment|contribution|amount|guarantee)[^.]{0,80}?" + MONEY + r")", re.I),
    re.compile(r"(?:not\s+less\s+than|no\s+less\s+than|at\s+least)\s+" + MONEY
               + r"[^.]{0,80}?(?:per\s+(?:year|annum|quarter|month)|annually|"
                 r"each\s+(?:year|quarter))", re.I),
]
MINPAY_ANCHOR = STATE_PAY_ANCHOR

DEVICEFEE_RX = [
    re.compile(MONEY + r"\s*(?:\([^)]{0,30}\)\s*)?(?:per|for\s+each|for\s+every)"
               r"\s+(?:authorized\s+|licensed\s+|additional\s+)?" + DEVICE, re.I),
    re.compile(r"(?:per|for\s+each|for\s+every)\s+(?:authorized\s+|licensed\s+)?"
               + DEVICE + r"[^.]{0,60}?" + MONEY, re.I),
]

FLATPAY_RX = [
    re.compile(r"(?:shall\s+pay|shall\s+remit|shall\s+transfer|shall\s+contribute)"
               r"[^.]{0,120}?" + MONEY, re.I),
]

HOTELTAX_RX = [
    re.compile(r"((?:in\s+lieu\s+of|equivalent\s+to|equal\s+to|comparable\s+to)"
               r"[^.]{0,110}?(?:transient\s+(?:occupancy|lodging)\s+tax|"
               r"hotel\s+(?:occupancy\s+)?tax|room\s+tax|lodging\s+tax|"
               r"bed\s+tax))", re.I),
    re.compile(r"((?:transient\s+(?:occupancy|lodging)\s+tax|hotel\s+(?:occupancy\s+)?tax|"
               r"room\s+tax|lodging\s+tax|bed\s+tax)[^.]{0,120}?"
               r"(?:shall\s+pay|payment|remit|amount\s+equal))", re.I),
]

MITIGATION_RX = [
    re.compile(r"((?:problem|compulsive|pathological)\s+gambl\w+[^.]{0,140}?"
               r"(?:fund|payment|contribut\w+|\$))", re.I),
    re.compile(r"((?:regulatory\s+(?:fee|cost|costs|assessment|expenses)|"
               r"cost\s+of\s+regulation|costs\s+of\s+regulat\w+)[^.]{0,140}?"
               r"(?:reimburs\w+|shall\s+pay|paid\s+by\s+the\s+Tribe|\$))", re.I),
    re.compile(r"((?:reimburse|reimbursement\s+of)[^.]{0,80}?"
               r"(?:State|Agency|Commission)[^.]{0,110}?"
               r"(?:cost|costs|expenses)[^.]{0,60}?(?:regulat|oversight|monitor))", re.I),
]

LOCAL_RX = [
    re.compile(r"((?:local\s+revenue\s+sharing\s+board|county|municipal|city|"
               r"local\s+government)[^.]{0,160}?(?:shall\s+(?:receive|be\s+paid)|"
               r"payment\s+of|semi-?annual\s+payment|shall\s+pay|"
               r"mitigation\s+(?:payment|fund)))", re.I),
    re.compile(r"((?:mitigation|impact)\s+(?:payment|fund|agreement)[^.]{0,120}?"
               r"(?:county|city|local|municipal))", re.I),
]

# ---------------------------------------------------------------------------
# SCOPE / DIGITAL EXTRACTORS.
# ---------------------------------------------------------------------------

SCOPE_RX = [
    re.compile(r"(?:may\s+(?:lawfully\s+)?(?:conduct|operate|engage\s+in)|"
               r"is\s+authorized\s+to\s+(?:conduct|operate|offer|engage\s+in)|"
               r"shall\s+have\s+the\s+right\s+to\s+operate)"
               r"[^.]{0,90}?(?:the\s+)?following[^.]{0,60}?(?:class\s+I{2,3}\s+)?gam\w+", re.I),
]

# Enumeration is new here and is only ever read out of the retained quote, so a
# reader can check every token against the words on the page.
GAME_TOKENS = [
    ("gaming_devices", r"gaming\s+devices?|slot\s+machines?|electronic\s+gaming\s+devices?|"
                       r"video\s+lottery\s+terminals?|player\s+terminals?"),
    ("blackjack", r"blackjack|twenty-?one"),
    ("poker", r"\bpoker\b|pai\s?gow\s+poker"),
    ("table_games", r"table\s+games?|banked\s+card\s+games?|house-?banked"),
    ("craps", r"\bcraps\b"),
    ("roulette", r"roulette"),
    ("baccarat", r"baccarat"),
    ("keno", r"\bkeno\b"),
    ("bingo", r"\bbingo\b"),
    ("lottery", r"\blotter(?:y|ies)\b"),
    ("pari_mutuel", r"pari-?mutuel"),
    ("off_track_wagering", r"off-?track"),
    ("horse_racing", r"horse\s+rac\w+"),
    ("dog_racing", r"dog\s+rac\w+|greyhound"),
    ("sports_wagering", r"sports\s+(?:wagering|betting|pool|book)|event\s+wagering"),
    ("fantasy_sports", r"fantasy\s+sports"),
]
GAME_TOKENS = [(k, re.compile(v, re.I)) for k, v in GAME_TOKENS]

CLASS3_RX = [
    re.compile(r"(?:may|is\s+authorized\s+to|shall\s+be\s+authorized\s+to|"
               r"shall\s+have\s+the\s+right\s+to)\s+(?:lawfully\s+)?"
               r"(?:conduct|operate|offer|engage\s+in|use)[^.]{0,80}?" + DEVICE, re.I),
    re.compile(DEVICE + r"[^.]{0,60}?(?:are|is)\s+(?:hereby\s+)?authorized", re.I),
]

SPORTS = (r"(?:sports\s+(?:wagering|betting|book|pool|pools)|event\s+wagering|"
          r"sports\s+event\s+wagering|athletic\s+event\s+wagering|"
          r"sports\s+pool\s+wagering)")
SPORTS_RX = [
    re.compile(r"(?:may|is\s+authorized\s+to|shall\s+be\s+authorized\s+to|"
               r"is\s+permitted\s+to|shall\s+have\s+the\s+right\s+to)"
               r"\s+(?:lawfully\s+)?(?:conduct|operate|offer|accept|engage\s+in)"
               r"[^.]{0,90}?" + SPORTS, re.I),
    re.compile(SPORTS + r"[^.]{0,70}?(?:is|are)\s+(?:hereby\s+)?"
               r"(?:authorized|permitted|allowed)", re.I),
]
SPORTS_MENTION = re.compile(SPORTS, re.I)

INET = (r"(?:internet\s+(?:gaming|gambling|wagering)|i-?gaming|"
        r"online\s+(?:gaming|gambling|wagering)|interactive\s+gaming)")
INET_RX = [
    re.compile(r"(?:may|is\s+authorized\s+to|shall\s+be\s+authorized\s+to|"
               r"is\s+permitted\s+to)\s+(?:lawfully\s+)?"
               r"(?:conduct|operate|offer|engage\s+in)[^.]{0,80}?" + INET, re.I),
    re.compile(INET + r"[^.]{0,70}?(?:is|are)\s+(?:hereby\s+)?"
               r"(?:authorized|permitted|prohibited|not\s+authorized)", re.I),
    re.compile(r"(?:shall\s+not|may\s+not|is\s+prohibited\s+from)[^.]{0,80}?" + INET, re.I),
]
INET_MENTION = re.compile(INET, re.I)

MOBILE = (r"(?:mobile\s+(?:wagering|gaming|betting|sports\s+betting|application|device)|"
          r"remote\s+wagering|off-?premises\s+wagering|"
          r"wagers?\s+placed\s+(?:remotely|by\s+mobile))")
# Anchor on the term itself and let ctx() supply the window. An inline
# `[^.]{0,150}?` prefix produced the same quotes an order of magnitude slower.
MOBILE_RX = [re.compile(MOBILE, re.I)]
SCOPE_ONLAND = re.compile(
    r"(on\s+(?:its|the\s+Tribe[\'\u2019]?s|Indian)\s+lands|within\s+the\s+"
    r"(?:exterior\s+)?boundaries\s+of|on\s+the\s+Reservation|on-?reservation|"
    r"located\s+on\s+Indian\s+lands|physically\s+located\s+on)", re.I)
SCOPE_STATEWIDE = re.compile(
    r"(statewide|anywhere\s+(?:in|within)\s+the\s+State|throughout\s+the\s+State|"
    r"from\s+any\s+location\s+(?:in|within)\s+the\s+State)", re.I)
# Arizona 2021 lets tribes into a mobile market that is expressly OFF Indian
# lands and licensed by the State. "off-reservation" next to a mobile clause is
# a distinct scope, not a variant of on-lands - collapsing them would report a
# statewide commercial licence as reservation gaming.
SCOPE_OFFRES = re.compile(
    r"(off-?reservation|outside\s+(?:of\s+)?(?:its\s+|the\s+)?Indian\s+lands|"
    r"outside\s+the\s+(?:exterior\s+)?boundaries)", re.I)

EXPIRE_RX = [
    re.compile(r"(?:this|these)\s+(?:Compact|Agreement|Procedures)\s+shall\s+"
               r"(?:expire|terminate)\s+on\s+(?:the\s+)?"
               r"(\w+\s+\d{1,2},\s*\d{4}|\d{1,2}/\d{1,2}/\d{2,4})", re.I),
    re.compile(r"(?:shall\s+be\s+in\s+(?:full\s+force\s+and\s+)?effect|"
               r"shall\s+remain\s+in\s+effect)[^.]{0,70}?until\s+"
               r"(\w+\s+\d{1,2},\s*\d{4}|\d{1,2}/\d{1,2}/\d{2,4})", re.I),
]
EXPIRE_REJECT = re.compile(r"(automatically\s+be\s+extended|may\s+be\s+extended\s+to)", re.I)

CONFID_RX = [
    re.compile(r"(shall\s+be\s+(?:kept\s+|held\s+|maintained\s+as\s+)?confidential|"
               r"treated\s+as\s+confidential|exempt\s+from\s+(?:public\s+)?disclosure|"
               r"not\s+subject\s+to\s+(?:public\s+)?disclosure|"
               r"not\s+be\s+disclosed\s+to\s+the\s+public|"
               r"confidential\s+and\s+proprietary)", re.I),
]

# ---------------------------------------------------------------------------
# REPORTING OBLIGATIONS. The discovery mechanism.
# ---------------------------------------------------------------------------

REPORT_RX = [
    re.compile(r"(?:shall|will|must)\s+(?:cause\s+to\s+be\s+)?"
               r"(?:submit|provide|furnish|deliver|file|transmit|forward|render|"
               r"report|supply|make\s+available)"
               r"[^.]{0,220}?\b(report|reports|statement|statements|accounting|"
               r"certification|audit|audited\s+financial\s+statements|"
               r"records|data)\b", re.I),
    re.compile(r"\b(monthly|quarterly|annual|annually|semi-?annual(?:ly)?|weekly)\s+"
               r"(?:written\s+)?(report|statement|certification|accounting|audit)"
               r"[^.]{0,200}", re.I),
]
REPORT_REJECT = re.compile(
    r"(TABLE\s+OF\s+CONTENTS|Sincerely|report\s+of\s+the\s+committee|"
    r"news\s+report|police\s+report|credit\s+report)", re.I)

FREQ_RX = [
    ("monthly", re.compile(r"\b(monthly|each\s+(?:calendar\s+)?month|"
                           r"every\s+month|per\s+month)\b", re.I)),
    ("quarterly", re.compile(r"\b(quarterly|each\s+(?:calendar\s+)?quarter|"
                             r"every\s+quarter|per\s+quarter)\b", re.I)),
    ("semiannual", re.compile(r"\b(semi-?annual(?:ly)?|twice\s+(?:each|per)\s+year|"
                              r"every\s+six\s+months)\b", re.I)),
    ("annual", re.compile(r"\b(annual(?:ly)?|each\s+(?:calendar\s+|fiscal\s+)?year|"
                          r"every\s+year|per\s+annum)\b", re.I)),
    ("weekly", re.compile(r"\bweekly\b", re.I)),
    ("daily", re.compile(r"\bdaily\b", re.I)),
]
ONDEMAND_RX = re.compile(r"(upon\s+request|upon\s+(?:the\s+)?written\s+request|"
                         r"as\s+requested|from\s+time\s+to\s+time)", re.I)

AGENCY_RX = re.compile(
    r"(State\s+Gaming\s+Agency|State\s+Gaming\s+Regulator|"
    r"[A-Z][A-Za-z\.\-]*(?:\s+[A-Z][A-Za-z\.\-]*){0,3}\s+Gaming\s+"
    r"(?:Commission|Agency|Board|Control\s+Board|Authority|Division)|"
    r"Gaming\s+Control\s+Board|Gambling\s+Commission|Racing\s+Commission|"
    r"Lottery\s+Commission|Division\s+of\s+Gaming|Gaming\s+Enforcement\s+Division|"
    r"National\s+Indian\s+Gaming\s+Commission|"
    r"Department\s+of\s+[A-Z][A-Za-z]*(?:\s+(?:and\s+)?[A-Z][A-Za-z]*){0,3}|"
    r"Attorney\s+General|State\s+Treasurer|Office\s+of\s+the\s+Governor|"
    r"Secretary\s+of\s+State|Tribal\s+Gaming\s+(?:Commission|Agency|Authority))")

TRIBAL_AGENCY = re.compile(r"(Tribal\s+Gaming|Tribe[\'\u2019]?s?\s+Gaming\s+"
                           r"(?:Commission|Agency))", re.I)
FEDERAL_AGENCY = re.compile(r"(National\s+Indian\s+Gaming\s+Commission|NIGC|"
                            r"Department\s+of\s+the\s+Interior|"
                            r"Secretary\s+of\s+the\s+Interior)", re.I)

FIELDS_RX = re.compile(
    r"(net\s+win|gross\s+(?:gaming\s+)?revenue|drop|handle|hold|"
    r"number\s+of\s+gaming\s+devices|device\s+count|gaming\s+positions?|"
    r"number\s+of\s+(?:table\s+games?|tables)|"
    r"win\s+per\s+(?:unit|device)|amounts?\s+wagered|coin[- ]in|"
    r"licens(?:e|es|ing)|employee|vendor|surveillance|"
    r"financial\s+statements?|balance\s+sheet|income\s+statement|"
    r"revenue\s+sharing\s+(?:calculation|payment)|contribution)", re.I)

PUBLIC_RX = re.compile(r"(shall\s+be\s+(?:a\s+)?public\s+record|"
                       r"available\s+to\s+the\s+public|subject\s+to\s+"
                       r"(?:the\s+)?(?:state\s+)?public\s+records)", re.I)
CONFID_NEAR = re.compile(r"(confidential|exempt\s+from\s+(?:public\s+)?disclosure|"
                         r"not\s+subject\s+to\s+(?:public\s+)?disclosure|"
                         r"proprietary|trade\s+secret)", re.I)

FACILITY_LEVEL = re.compile(
    r"(each\s+(?:Gaming\s+)?Facilit\w+|per\s+(?:Gaming\s+)?Facilit\w+|"
    r"for\s+each\s+(?:Gaming\s+)?(?:Facility|Operation|Establishment|location|site)|"
    r"facility-?by-?facility|each\s+such\s+facilit\w+|at\s+each\s+"
    r"(?:casino|premises|location))", re.I)
TRIBE_LEVEL = re.compile(
    r"(the\s+Tribe[\'\u2019]?s?\s+(?:total|aggregate|combined|overall)|"
    r"all\s+(?:of\s+)?the\s+Tribe[\'\u2019]?s?\s+(?:Gaming\s+)?"
    r"(?:Facilities|Operations)|tribe-?wide|in\s+the\s+aggregate)", re.I)

# ---------------------------------------------------------------------------
# applies_to - facility-scoped vs tribe-wide. Never propagate a facility-
# specific term tribewide; when the signals conflict, leave it UNSET.
# ---------------------------------------------------------------------------

FACILITY_SIG = re.compile(
    r"(per\s+(?:gaming\s+)?facilit\w+|at\s+each\s+(?:gaming\s+)?facilit\w+|"
    r"in\s+any\s+one\s+(?:gaming\s+)?facilit\w+|each\s+such\s+facilit\w+|"
    r"per\s+(?:casino|establishment|premise|location)|at\s+any\s+premise|"
    r"any\s+single\s+(?:gaming\s+)?facilit\w+|per\s+(?:gaming\s+)?site)", re.I)
STATEWIDE_SIG = re.compile(
    r"(in\s+the\s+aggregate|total\s+of|aggregate\s+number|total\s+number|"
    r"all\s+(?:of\s+the\s+)?(?:tribe|tribal)[\'\u2019]?s?\s+(?:gaming\s+)?facilit\w+|"
    r"tribe\s+is\s+authorized\s+to\s+operate|the\s+tribe\s+may\s+operate)", re.I)
SINGLE_SITE = re.compile(
    r"(in\s+a\s+(?:tribal\s+)?(?:establishment|facility|casino)|"
    r"located\s+in\s+the\s+|located\s+(?:at|on|within)\s+|"
    r"at\s+the\s+[A-Z][A-Za-z\']+\s+(?:Casino|Facility|Center))")


def applies_to(q, local=""):
    """`local` is the matched span itself. A cap that says "500 Gaming Devices
    per Gaming Facility location" IN THE MATCH is facility-scoped even though
    the surrounding sentence also says "the Tribe is authorized to operate";
    without the local read those two signals cancel and the scope is lost."""
    if local and FACILITY_SIG.search(local):
        return "facility"
    if SINGLE_SITE.search(q):
        return "facility"
    f, s = FACILITY_SIG.search(q), STATEWIDE_SIG.search(q)
    if f and not s:
        return "facility"
    if f and s:
        return ""          # ambiguous - do not guess
    if s:
        return "tribe_wide"
    return ""


# ---------------------------------------------------------------------------
# Page extraction with an on-disk cache. The 2.0 GB PDF corpus is re-read only
# when the cache is absent, so iterating on the parser costs seconds not minutes.
# ---------------------------------------------------------------------------

PAGE_SEP = "\n\x0c<<<CEDAR_PAGE_BREAK>>>\x0c\n"


def pages_for(pdf_name):
    if not pdf_name:
        return None
    cache = PAGECACHE / (Path(pdf_name).stem + ".pages.txt")
    if cache.exists():
        return cache.read_text(encoding="utf-8", errors="replace").split(PAGE_SEP)
    src = PDFDIR / pdf_name
    if not src.exists():
        return None
    try:
        doc = fitz.open(src)
        pages = [doc[i].get_text() for i in range(len(doc))]
        doc.close()
    except Exception:
        return None
    PAGECACHE.mkdir(parents=True, exist_ok=True)
    cache.write_text(PAGE_SEP.join(pages), encoding="utf-8", errors="replace")
    return pages


# ---------------------------------------------------------------------------
# Term extraction per document.
# ---------------------------------------------------------------------------

# One statement of a boolean is the whole fact. Repeating "the Tribe is
# authorized to operate Gaming Devices" on 40 pages does not make it 40 facts.
SINGLETON_FIELDS = {"class_iii_devices_authorized", "sports_wagering_authorized",
                    "internet_wagering_authorized", "mobile_wagering_scope"}


def extract_terms(pages, letters, tribe_name=""):
    """Return a list of raw term dicts and a list of unresolved notes."""
    out, unresolved, seen, singles = [], [], set(), set()

    def add(field, value, unit, q, page, zone, local="", **extra):
        value = flat(str(value))
        key = (field, value, zone, qkey(q))
        if key in seen:
            return
        seen.add(key)
        if field in SINGLETON_FIELDS:
            skey = (field, value, zone)
            if skey in singles:
                return
            singles.add(skey)
        row = dict(term_field=field, value=value, unit=unit,
                   source_quote=q, source_page=page, doc_zone=zone,
                   applies_to=applies_to(q, local))
        row.update(extra)
        out.append(row)

    def note(field, reason, q, page, zone):
        unresolved.append(dict(term_field=field, reason=reason,
                               source_quote=q[:600], source_page=page,
                               doc_zone=zone))

    OTHER_TRIBE_REASON = (
        "the clause is conditioned on a DIFFERENT named tribe (standard-form "
        "state compact printing every signatory's allocation) - keying it to "
        "this compact would attribute another tribe's term")

    for pi, raw in enumerate(pages):
        pt = norm(raw)
        if not pt.strip():
            continue
        sig = page_toc_signals(pt)
        zone = "approval_letter" if pi in letters else "instrument_text"
        page = pi + 1

        # ---- device cap ------------------------------------------------
        for rx in CAP_RX:
            for m in rx.finditer(pt):
                q = ctx(pt, m)
                if is_toc(q, sig) or not CAP_ANCHOR.search(q):
                    continue
                if CAP_REJECT.search(q) or not CAP_SUBJECT.search(q):
                    continue
                v = num(m.group(1))
                if v is None or v < 5 or v > 100000:
                    continue
                if other_tribes_clause(q, tribe_name):
                    note("device_caps", OTHER_TRIBE_REASON, q, page, zone)
                    continue
                add("device_caps", int(v), "devices", q, page, zone,
                    local=m.group(0),
                    measurement_type=MeasurementType.AUTHORIZED_MAXIMUM.value,
                    value_numeric=int(v))

        # ---- table cap -------------------------------------------------
        for rx in TABLECAP_RX:
            for m in rx.finditer(pt):
                q = ctx(pt, m)
                if is_toc(q, sig) or CAP_REJECT.search(q):
                    continue
                if not CAP_SUBJECT.search(q) and not CAP_ANCHOR.search(q):
                    continue
                v = num(m.group(1))
                if v is None or v < 1 or v > 1000:
                    continue
                if other_tribes_clause(q, tribe_name):
                    note("table_caps", OTHER_TRIBE_REASON, q, page, zone)
                    continue
                add("table_caps", int(v), "tables", q, page, zone,
                    local=m.group(0),
                    measurement_type=MeasurementType.AUTHORIZED_MAXIMUM.value,
                    value_numeric=int(v))

        # ---- facility cap ----------------------------------------------
        for rx in FACCAP_RX:
            for m in rx.finditer(pt):
                q = ctx(pt, m)
                if is_toc(q, sig) or FACCAP_REJECT.search(q):
                    continue
                if not FACCAP_ANCHOR.search(q):
                    continue
                g = m.group(1)
                v = wordnum(g)
                if v is None:
                    v = num(g)
                if v is None or v < 1 or v > 30:
                    continue
                if other_tribes_clause(q, tribe_name):
                    note("facility_caps", OTHER_TRIBE_REASON, q, page, zone)
                    continue
                add("facility_caps", int(v), "facilities", q, page, zone,
                    local=m.group(0),
                    measurement_type=MeasurementType.AUTHORIZED_MAXIMUM.value,
                    value_numeric=int(v))

        # ---- class III device authorisation ----------------------------
        for rx in CLASS3_RX:
            for m in rx.finditer(pt):
                q = ctx(pt, m)
                if is_toc(q, sig) or NEGATION.search(q):
                    continue
                add("class_iii_devices_authorized", "yes", "boolean", q, page, zone)
                break

        # ---- gaming types ----------------------------------------------
        for rx in SCOPE_RX:
            for m in rx.finditer(pt):
                q = ctx(pt, m, before=120, after=520)
                if is_toc(q, sig):
                    continue
                games = [k for k, r in GAME_TOKENS if r.search(q)]
                if not games:
                    note("gaming_types_authorized",
                         "authorisation section located but no game token inside "
                         "the retained quote", q, page, zone)
                    continue
                add("gaming_types_authorized", "|".join(games), "game_list",
                    q, page, zone)

        # ---- sports wagering -------------------------------------------
        hit = False
        for rx in SPORTS_RX:
            for m in rx.finditer(pt):
                q = ctx(pt, m)
                if is_toc(q, sig):
                    continue
                if NEGATION.search(q):
                    add("sports_wagering_authorized", "prohibited", "enum",
                        q, page, zone)
                elif CONDITIONAL.search(q):
                    add("sports_wagering_authorized", "conditional", "enum",
                        q, page, zone)
                else:
                    add("sports_wagering_authorized", "authorized", "enum",
                        q, page, zone)
                hit = True
        if not hit:
            for m in SPORTS_MENTION.finditer(pt):
                q = ctx(pt, m)
                if is_toc(q, sig):
                    continue
                note("sports_wagering_authorized",
                     "sports/event wagering named but no authorisation verb in "
                     "the window - mention is not authorisation", q, page, zone)
                break

        # ---- internet wagering -----------------------------------------
        hit = False
        for rx in INET_RX:
            for m in rx.finditer(pt):
                q = ctx(pt, m)
                if is_toc(q, sig):
                    continue
                if NEGATION.search(q):
                    val = "prohibited"
                elif CONDITIONAL.search(q):
                    val = "conditional"
                else:
                    val = "authorized"
                add("internet_wagering_authorized", val, "enum", q, page, zone)
                hit = True
        if not hit:
            for m in INET_MENTION.finditer(pt):
                q = ctx(pt, m)
                if is_toc(q, sig):
                    continue
                note("internet_wagering_authorized",
                     "internet/online gaming named without an authorising or "
                     "prohibiting verb in the window", q, page, zone)
                break

        # ---- mobile scope ----------------------------------------------
        for rx in MOBILE_RX:
            for m in rx.finditer(pt):
                q = ctx(pt, m)
                if is_toc(q, sig):
                    continue
                onland = bool(SCOPE_ONLAND.search(q))
                statewide = bool(SCOPE_STATEWIDE.search(q))
                offres = bool(SCOPE_OFFRES.search(q))
                if offres and not statewide:
                    val = "off_reservation"
                elif statewide and not onland:
                    val = "statewide"
                elif onland and not statewide and not offres:
                    val = "on_indian_lands"
                elif onland and statewide:
                    val = "statewide_server_on_indian_lands"
                else:
                    note("mobile_wagering_scope",
                         "mobile/remote wagering named but the window mixes or "
                         "omits geographic scope", q, page, zone)
                    continue
                add("mobile_wagering_scope", val, "enum", q, page, zone)

        # ---- revenue-share base ----------------------------------------
        for rx in BASE_RX:
            for m in rx.finditer(pt):
                q = ctx(pt, m)
                if is_toc(q, sig):
                    continue
                add("revenue_sharing_base", m.group(1).strip(), "defined_term",
                    q, page, zone, revenue_concept=m.group(1).strip())

        # ---- revenue-share rate ----------------------------------------
        for rx in RATE_RX:
            for m in rx.finditer(pt):
                q = ctx(pt, m)
                if is_toc(q, sig) or not STATE_PAY_ANCHOR.search(q):
                    continue
                if RATE_REJECT.search(q):
                    continue
                g = [x for x in m.groups() if x and re.match(r"^[\d]", x)]
                if not g:
                    continue
                v = num(g[0])
                if v is None or v <= 0 or v > 60:
                    continue
                cm = CONCEPT_RX.search(q)
                if not cm:
                    note("revenue_sharing_rate",
                         "rate anchored to a state payment but the window names "
                         "no revenue base - concept cannot be preserved, so the "
                         "rate is not invertible", q, page, zone)
                    continue
                if other_tribes_clause(q, tribe_name):
                    note("revenue_sharing_rate", OTHER_TRIBE_REASON, q, page, zone)
                    continue
                fsb = bool(FACILITY_SCOPED_BASE.search(q))
                if applies_to(q, m.group(0)) == "facility" and not fsb:
                    note("revenue_sharing_rate",
                         "the clause names a facility but the REVENUE BASE is "
                         "not bound to it - recorded as a tribe-level "
                         "obligation; a property-level reading needs a hand "
                         "check of the base definition", q, page, zone)
                add("revenue_sharing_rate", v, "percent", q, page, zone,
                    local=m.group(0), value_numeric=v,
                    revenue_concept=flat(cm.group(0)),
                    base_scope="facility" if fsb else "tribe")

        # ---- progressive schedule --------------------------------------
        for rx in TIER_RX:
            for m in rx.finditer(pt):
                q = ctx(pt, m)
                if is_toc(q, sig) or not STATE_PAY_ANCHOR.search(q):
                    continue
                if RATE_REJECT.search(q):
                    continue
                if other_tribes_clause(q, tribe_name):
                    note("progressive_rate_schedule", OTHER_TRIBE_REASON,
                         q, page, zone)
                    continue
                val = " | ".join(x for x in m.groups() if x)
                cm = CONCEPT_RX.search(q)
                add("progressive_rate_schedule", val, "percent_of_bracket",
                    q, page, zone, local=m.group(0),
                    revenue_concept=flat(cm.group(0)) if cm else "",
                    base_scope=("facility"
                                if FACILITY_SCOPED_BASE.search(q) else "tribe"))

        # ---- minimum payment -------------------------------------------
        for rx in MINPAY_RX:
            for m in rx.finditer(pt):
                q = ctx(pt, m)
                if is_toc(q, sig) or not MINPAY_ANCHOR.search(q):
                    continue
                g = [x for x in m.groups() if x and re.match(r"^[\d]", x)]
                if not g:
                    continue
                v = num(g[0])
                if v is None or v < 1000:
                    continue
                if other_tribes_clause(q, tribe_name):
                    note("minimum_payment", OTHER_TRIBE_REASON, q, page, zone)
                    continue
                add("minimum_payment", v, "usd", q, page, zone,
                    local=m.group(0), value_numeric=v)

        # ---- per-device payment ----------------------------------------
        for rx in DEVICEFEE_RX:
            for m in rx.finditer(pt):
                q = ctx(pt, m)
                if is_toc(q, sig):
                    continue
                g = [x for x in m.groups() if x and re.match(r"^[\d]", x)]
                if not g:
                    continue
                v = num(g[0])
                if v is None or v <= 0 or v > 100000:
                    continue
                if other_tribes_clause(q, tribe_name):
                    note("machine_based_payment", OTHER_TRIBE_REASON, q, page, zone)
                    continue
                add("machine_based_payment", v, "usd_per_device", q, page, zone,
                    local=m.group(0), value_numeric=v)

        # ---- flat state payment ----------------------------------------
        for rx in FLATPAY_RX:
            for m in rx.finditer(pt):
                q = ctx(pt, m)
                if is_toc(q, sig) or not STATE_PAY_ANCHOR.search(q):
                    continue
                if RATE_REJECT.search(q) or re.search(r"per\s+(?:gaming\s+)?device", q, re.I):
                    continue
                v = num(m.group(1))
                if v is None or v < 1000:
                    continue
                if other_tribes_clause(q, tribe_name):
                    note("state_payment", OTHER_TRIBE_REASON, q, page, zone)
                    continue
                add("state_payment", v, "usd", q, page, zone,
                    local=m.group(0), value_numeric=v)

        # ---- local payment ---------------------------------------------
        for rx in LOCAL_RX:
            for m in rx.finditer(pt):
                q = ctx(pt, m)
                if is_toc(q, sig):
                    continue
                add("local_payment", m.group(1).strip()[:200], "text", q, page, zone)

        # ---- hotel tax equivalent --------------------------------------
        for rx in HOTELTAX_RX:
            for m in rx.finditer(pt):
                q = ctx(pt, m)
                if is_toc(q, sig):
                    continue
                add("hotel_tax_equivalent", m.group(1).strip()[:200], "text",
                    q, page, zone)

        # ---- other mitigation ------------------------------------------
        for rx in MITIGATION_RX:
            for m in rx.finditer(pt):
                q = ctx(pt, m)
                if is_toc(q, sig):
                    continue
                add("other_mitigation_payments", m.group(1).strip()[:200], "text",
                    q, page, zone)

        # ---- expiration -------------------------------------------------
        for rx in EXPIRE_RX:
            for m in rx.finditer(pt):
                q = ctx(pt, m)
                if is_toc(q, sig) or EXPIRE_REJECT.search(q):
                    continue
                add("expiration_date", m.group(1).strip(), "date", q, page, zone)

        # ---- confidentiality --------------------------------------------
        for rx in CONFID_RX:
            for m in rx.finditer(pt):
                q = ctx(pt, m)
                if is_toc(q, sig):
                    continue
                add("confidentiality_provision", m.group(0), "text",
                    q, page, zone)

    return out, unresolved


# ---------------------------------------------------------------------------
# Reporting obligations.
# ---------------------------------------------------------------------------

def extract_reports(pages, letters):
    out, seen = [], set()
    for pi, raw in enumerate(pages):
        pt = norm(raw)
        if not pt.strip():
            continue
        sig = page_toc_signals(pt)
        zone = "approval_letter" if pi in letters else "instrument_text"
        for rx in REPORT_RX:
            for m in rx.finditer(pt):
                q = ctx(pt, m, before=200, after=420)
                if is_toc(q, sig) or REPORT_REJECT.search(q):
                    continue

                freq = ""
                for name, frx in FREQ_RX:
                    if frx.search(q):
                        freq = name
                        break
                if not freq and ONDEMAND_RX.search(q):
                    freq = "on_request"
                if not freq:
                    # The numeral must actually be the day count. A loose
                    # "\(?(\d{1,3})\)?" swallowed section numbers such as
                    # "4.070" and produced "within_0_days".
                    mdays = re.search(
                        r"within\s+(?:\w+\s+)?\(?\s*(\d{1,3})\s*\)?\s+"
                        r"(?:calendar\s+|business\s+|working\s+)?days", q, re.I)
                    d = int(mdays.group(1)) if mdays else 0
                    freq = f"within_{d}_days" if 0 < d <= 365 else "unspecified"

                agencies = [a.group(0).strip() for a in AGENCY_RX.finditer(q)]
                # Keep the first named recipient; record the rest so a reader can
                # see the clause named more than one.
                recipient = agencies[0] if agencies else ""
                if recipient:
                    if FEDERAL_AGENCY.search(recipient):
                        side = "federal"
                    elif TRIBAL_AGENCY.search(recipient):
                        side = "tribal"
                    else:
                        side = "state"
                else:
                    side = "unspecified"

                fields = sorted({f.group(0).lower().strip()
                                 for f in FIELDS_RX.finditer(q)})

                if FACILITY_LEVEL.search(q):
                    level = "facility"
                elif TRIBE_LEVEL.search(q):
                    level = "tribe"
                else:
                    level = "unspecified"

                # Disclosure: only what the compact itself says. Whether the
                # agency in fact publishes the file is a separate question that
                # this source cannot answer.
                if CONFID_NEAR.search(q):
                    pub = "CONFIDENTIAL_PER_COMPACT"
                elif PUBLIC_RX.search(q):
                    pub = "PUBLIC_PER_COMPACT"
                else:
                    pub = "NOT_STATED_IN_COMPACT"

                key = (freq, recipient, level, zone, qkey(q))
                if key in seen:
                    continue
                seen.add(key)
                out.append(dict(
                    obligation_type="REQUIRED_REPORT_EXISTS",
                    is_instrument_language=("yes" if zone == "instrument_text"
                                            else "no"),
                    frequency=freq, recipient_agency=flat(recipient),
                    recipient_side=side,
                    other_agencies_named="|".join(agencies[1:][:4]),
                    fields_required="|".join(fields),
                    report_subject_level=level,
                    public_availability=pub,
                    source_page=pi + 1, doc_zone=zone,
                    source_quote=q))
    return out


# ---------------------------------------------------------------------------
# Invertibility. The only place a revenue number could ever come from.
# ---------------------------------------------------------------------------

def classify_invertibility(version_terms):
    """Decide, per version, whether `payment / rate` uniquely solves.

    INVERTIBLE_FLAT_RATE requires: exactly one distinct rate, no progressive
    schedule, no minimum payment and no per-device payment in the same
    instrument. Any of those means more than one revenue level produces the same
    payment, so the honest output is a bound with a stated basis - never a point
    estimate and never an interval.
    """
    # The Secretary's approval letter DESCRIBES the compact; it is not the
    # compact. A rate read out of the letter must never decide whether the
    # instrument's formula inverts.
    body = [t for t in version_terms if t["doc_zone"] == "instrument_text"]
    rates = {t["value"] for t in body
             if t["term_field"] == "revenue_sharing_rate"}
    tiers = [t for t in body if t["term_field"] == "progressive_rate_schedule"]
    mins = [t for t in body if t["term_field"] == "minimum_payment"]
    perdev = [t for t in body if t["term_field"] == "machine_based_payment"]

    if not rates and not tiers:
        return "NO_RATE_FOUND", ""
    blockers = []
    if tiers:
        blockers.append("progressive_rate_schedule_present")
    if not rates:
        # A bracket schedule with no flat rate anywhere is still a bound, and a
        # bound with no stated basis is indistinguishable from an estimate.
        blockers.append("no_flat_rate_stated_only_a_bracket_schedule")
    if len(rates) > 1:
        blockers.append(f"{len(rates)}_distinct_rates_in_instrument")
    if mins:
        blockers.append("minimum_payment_floor_present")
    if perdev:
        blockers.append("per_device_payment_component_present")
    if blockers:
        return "NOT_INVERTIBLE", ";".join(blockers)
    return "INVERTIBLE_FLAT_RATE", ""


def revenue_evidence_class(field, invertibility, base_scope):
    """What a derived figure WOULD be, if a payment were later joined in.

    `base_scope` is NOT where the clause is located - it is whether the compact
    binds the REVENUE BASE to a single property. A compact obligation is a
    tribe-level obligation by default, and a tribe total is not a property
    revenue figure. The two must never be published at the same level.
    """
    # Only a RATE can be inverted. A revenue-share BASE is a definition, and a
    # minimum, per-device or flat payment is money moving the other way - none
    # of them is a revenue observation, and labelling them as one would invite
    # exactly the arithmetic this dataset refuses to do.
    if field not in ("revenue_sharing_rate", "progressive_rate_schedule"):
        return ""
    if field == "revenue_sharing_rate" and invertibility == "INVERTIBLE_FLAT_RATE":
        return ("EXACT_DERIVED_PROPERTY_REVENUE" if base_scope == "facility"
                else "TRIBE_LEVEL_REVENUE")
    return ("BOUNDED_DERIVED_REVENUE" if base_scope == "facility"
            else "TRIBE_LEVEL_REVENUE")


# ---------------------------------------------------------------------------
# I/O helpers.
# ---------------------------------------------------------------------------

def read_csv(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


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


def write_csv(p, rows, fields):
    # REGENERATE GUARD (ADR-017, 2026-09-02): derive the header, do not declare it.
    fields = _carry_live_columns(p, fields)
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"  wrote {p.relative_to(CEDAR)}  ({len(rows):,} rows)")


TERM_FIELDS = [
    "term_id", "compact_id", "version_id", "amendment_number", "version_seq",
    "version_role", "doc_kind",
    "tribe_id", "tribe_canonical_name", "entity_id", "tribe", "state",
    "term_field", "value", "value_numeric", "unit", "applies_to",
    "measurement_type", "revenue_concept", "base_scope",
    "formula_invertibility", "bound_basis", "revenue_evidence_class",
    "effective_from", "effective_from_basis", "effective_to", "effective_to_basis",
    "confidence_tier", "is_instrument_language", "doc_zone", "source_page",
    "source_pdf", "source_url", "source_quote", "fetched_date",
    "extraction_method", "entity_match_method", "entity_tier", "built_by_script",
]

REPORT_FIELDS = [
    "report_id", "compact_id", "version_id", "amendment_number", "version_role",
    "tribe_id", "tribe_canonical_name", "entity_id", "tribe", "state",
    "obligation_type", "frequency", "recipient_agency", "recipient_side",
    "other_agencies_named", "fields_required", "report_subject_level",
    "public_availability", "version_has_confidentiality_provision",
    "confidence_tier", "is_instrument_language",
    "effective_from", "effective_from_basis", "effective_to", "effective_to_basis",
    "doc_zone", "source_page", "source_pdf", "source_url", "source_quote",
    "fetched_date", "extraction_method", "built_by_script",
]

UNRESOLVED_FIELDS = [
    "review_id", "compact_id", "version_id", "tribe", "state", "term_field",
    "reason", "source_page", "doc_zone", "source_pdf", "source_url",
    "source_quote", "flagged_date",
]

EXTRACTION_METHOD = ("regex v5 (95_parse_compact_terms.py); page-wise PyMuPDF "
                     "re-extraction; TOC and approval-letter zoning guards; "
                     "verbatim quote and PDF page retained on every row")


# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0,
                    help="parse only the first N versions (development)")
    args = ap.parse_args()

    assert_guards()
    print("=== Cedar Press 95: compact terms + required reports ===\n")
    log = io.StringIO()

    def say(*a):
        s = " ".join(str(x) for x in a)
        print(s)
        log.write(s + "\n")

    compacts = read_csv(CLEAN / "compacts.csv")
    versions = read_csv(CLEAN / "compact_versions.csv")
    spine = read_csv(SPINE / "cedar_entity_spine.csv")
    cby = {c["compact_id"]: c for c in compacts}
    say(f"compacts {len(compacts):,} | versions {len(versions):,} | "
        f"spine {len(spine):,}")

    # --- entity keying ----------------------------------------------------
    # compacts.csv already carries a keyed tribe_id for 702 of 707. The five
    # blanks go through the ONE resolver; anything it refuses stays blank and is
    # reported, never guessed.
    resolved_here = 0
    unkeyed = []
    for c in compacts:
        if c.get("tribe_id"):
            continue
        tid, canon, how = resolve_entity(c.get("tribe", ""), spine)
        if tid:
            c["tribe_id"], c["tribe_canonical_name"] = tid, canon
            c["entity_id"] = tid
            c["entity_match_method"] = f"resolver_{how}"
            c["entity_tier"] = Tier.B.value
            resolved_here += 1
        else:
            unkeyed.append((c["compact_id"], c.get("tribe", ""), how))
    say(f"entity keying: {resolved_here} resolved here, {len(unkeyed)} still unkeyed")

    # --- version ordering, for effective-date ranges ----------------------
    by_compact = defaultdict(list)
    for v in versions:
        by_compact[v["compact_id"]].append(v)

    def vseq(v):
        try:
            return int(v.get("version_seq") or 0)
        except ValueError:
            return 0

    for cid in by_compact:
        by_compact[cid].sort(key=lambda v: (v.get("approval_date") or "9999",
                                            vseq(v)))

    # --- parse ------------------------------------------------------------
    todo = list(versions)
    if args.limit:
        todo = todo[:args.limit]

    raw_terms = {}          # version_id -> [term dicts]
    raw_reports = {}        # version_id -> [report dicts]
    unresolved = []
    n_no_pdf = n_no_text = n_no_terms = 0

    for i, v in enumerate(todo, 1):
        if i % 100 == 0:
            print(f"    ... {i}/{len(todo)} versions")
        pdf = v.get("source_pdf") or ""
        pages = pages_for(pdf)
        if pages is None:
            n_no_pdf += 1
            unresolved.append(dict(
                review_id=f"CPU-{v['version_id']}-NOPDF",
                compact_id=v["compact_id"], version_id=v["version_id"],
                tribe=cby.get(v["compact_id"], {}).get("tribe", ""),
                state=cby.get(v["compact_id"], {}).get("state", ""),
                term_field="", reason="no readable PDF for this version",
                source_page="", doc_zone="", source_pdf=pdf,
                source_url=v.get("source_url", ""), source_quote="",
                flagged_date=TODAY))
            continue
        if not any(p.strip() for p in pages):
            n_no_text += 1
            unresolved.append(dict(
                review_id=f"CPU-{v['version_id']}-NOTEXT",
                compact_id=v["compact_id"], version_id=v["version_id"],
                tribe=cby.get(v["compact_id"], {}).get("tribe", ""),
                state=cby.get(v["compact_id"], {}).get("state", ""),
                term_field="",
                reason="PDF opens but yields no text layer (image-only scan)",
                source_page="", doc_zone="", source_pdf=pdf,
                source_url=v.get("source_url", ""), source_quote="",
                flagged_date=TODAY))
            continue

        letters = letter_pages(pages)
        terms, notes = extract_terms(
            pages, letters, cby.get(v["compact_id"], {}).get("tribe", ""))
        reports = extract_reports(pages, letters)
        raw_terms[v["version_id"]] = terms
        raw_reports[v["version_id"]] = reports

        c = cby.get(v["compact_id"], {})
        for n in notes:
            unresolved.append(dict(
                review_id=f"CPU-{v['version_id']}-{n['term_field']}-{n['source_page']}",
                compact_id=v["compact_id"], version_id=v["version_id"],
                tribe=c.get("tribe", ""), state=c.get("state", ""),
                term_field=n["term_field"], reason=n["reason"],
                source_page=n["source_page"], doc_zone=n["doc_zone"],
                source_pdf=pdf, source_url=v.get("source_url", ""),
                source_quote=n["source_quote"], flagged_date=TODAY))

        if not terms and not reports:
            n_no_terms += 1
            unresolved.append(dict(
                review_id=f"CPU-{v['version_id']}-EMPTY",
                compact_id=v["compact_id"], version_id=v["version_id"],
                tribe=c.get("tribe", ""), state=c.get("state", ""),
                term_field="",
                reason=("text present but no term and no reporting obligation "
                        "matched - re-read by hand before concluding the "
                        "instrument carries none"),
                source_page="", doc_zone=v.get("doc_kind", ""), source_pdf=pdf,
                source_url=v.get("source_url", ""), source_quote="",
                flagged_date=TODAY))

    # --- effective-date ranges -------------------------------------------
    # A term stands from its own instrument's approval date until a later
    # version of the same compact restates the SAME field. Nothing is
    # overwritten; the superseded row keeps its dates and its quote.
    def eff_from(v):
        c = cby.get(v["compact_id"], {})
        if str(v.get("version_seq") or "") == "1" and c.get("original_effective_date"):
            return c["original_effective_date"], "compact original_effective_date"
        if v.get("approval_date"):
            return v["approval_date"], "version approval_date"
        if c.get("original_effective_date"):
            return c["original_effective_date"], "compact original_effective_date (version undated)"
        return "", "no dated basis available"

    def eff_to(v, field, is_report=False):
        c = cby.get(v["compact_id"], {})
        sibs = by_compact.get(v["compact_id"], [])
        try:
            idx = sibs.index(v)
        except ValueError:
            idx = -1
        if idx >= 0:
            for later in sibs[idx + 1:]:
                if is_report:
                    restates = bool(raw_reports.get(later["version_id"]))
                else:
                    restates = any(t["term_field"] == field
                                   for t in raw_terms.get(later["version_id"], []))
                if restates:
                    d = later.get("approval_date") or ""
                    if d:
                        return d, f"superseded by {later['version_id']}"
        if c.get("term_end"):
            return c["term_end"], "compact term_end"
        return "", "open - no stated end and no superseding instrument"

    # --- assemble term rows -----------------------------------------------
    term_rows = []
    n_terms = 0
    for v in versions:
        terms = raw_terms.get(v["version_id"])
        if not terms:
            continue
        inv, bound = classify_invertibility(terms)
        c = cby.get(v["compact_id"], {})
        ef, efb = eff_from(v)
        for j, t in enumerate(terms, 1):
            n_terms += 1
            field = t["term_field"]
            et, etb = eff_to(v, field)
            mt = t.get("measurement_type", "")
            # Rule 1, enforced rather than remembered.
            if mt:
                assert mt != MeasurementType.ACTIVE_FLOOR_COUNT.value, \
                    "a compact cap may never be stamped ACTIVE_FLOOR_COUNT"
            is_rev = field in ("revenue_sharing_rate", "progressive_rate_schedule")
            if t["doc_zone"] == "approval_letter":
                # Sourced and kept, but it is DOI's characterisation of the
                # instrument, so it may never drive a derived revenue figure.
                inv_here = "NOT_APPLICABLE_APPROVAL_LETTER"
                rev_class = ""
            else:
                inv_here = inv
                rev_class = revenue_evidence_class(field, inv,
                                                   t.get("base_scope", ""))
            term_rows.append(dict(
                term_id=f"CTM-{v['version_id']}-{j:04d}",
                compact_id=v["compact_id"], version_id=v["version_id"],
                amendment_number=v.get("amendment_number", ""),
                version_seq=v.get("version_seq", ""),
                version_role=v.get("version_role", ""),
                doc_kind=v.get("doc_kind", ""),
                tribe_id=c.get("tribe_id", ""),
                tribe_canonical_name=c.get("tribe_canonical_name", ""),
                entity_id=c.get("entity_id", ""),
                tribe=c.get("tribe", ""), state=c.get("state", ""),
                term_field=field, value=t["value"],
                value_numeric=t.get("value_numeric", ""),
                unit=t["unit"], applies_to=t.get("applies_to", ""),
                measurement_type=mt,
                revenue_concept=t.get("revenue_concept", ""),
                base_scope=t.get("base_scope", ""),
                formula_invertibility=inv_here if is_rev else "",
                bound_basis=(bound if (is_rev and inv_here == "NOT_INVERTIBLE")
                             else ""),
                revenue_evidence_class=rev_class,
                is_instrument_language=("yes" if t["doc_zone"] == "instrument_text"
                                        else "no"),
                effective_from=ef, effective_from_basis=efb,
                effective_to=et, effective_to_basis=etb,
                confidence_tier=Tier.B.value,
                doc_zone=t["doc_zone"], source_page=t["source_page"],
                source_pdf=v.get("source_pdf", ""),
                source_url=v.get("source_url", ""),
                source_quote=t["source_quote"], fetched_date=FETCHED_DATE,
                extraction_method=EXTRACTION_METHOD,
                entity_match_method=c.get("entity_match_method", ""),
                entity_tier=c.get("entity_tier", ""),
                built_by_script="95_parse_compact_terms.py"))

    # --- assemble report rows ---------------------------------------------
    report_rows = []
    for v in versions:
        reps = raw_reports.get(v["version_id"])
        if not reps:
            continue
        c = cby.get(v["compact_id"], {})
        ef, efb = eff_from(v)
        et, etb = eff_to(v, "", is_report=True)
        # `public_availability` is what the REPORTING clause itself says. A
        # confidentiality section elsewhere in the same instrument is a
        # different fact and is carried separately rather than folded in - a
        # general confidentiality clause does not necessarily reach the
        # revenue-sharing certification, and assuming it does would suppress a
        # public series that in fact exists.
        has_conf = "yes" if any(
            t["term_field"] == "confidentiality_provision"
            for t in raw_terms.get(v["version_id"], [])) else "no"
        for j, r in enumerate(reps, 1):
            report_rows.append(dict(
                report_id=f"CRR-{v['version_id']}-{j:04d}",
                version_has_confidentiality_provision=has_conf,
                compact_id=v["compact_id"], version_id=v["version_id"],
                amendment_number=v.get("amendment_number", ""),
                version_role=v.get("version_role", ""),
                tribe_id=c.get("tribe_id", ""),
                tribe_canonical_name=c.get("tribe_canonical_name", ""),
                entity_id=c.get("entity_id", ""),
                tribe=c.get("tribe", ""), state=c.get("state", ""),
                confidence_tier=Tier.B.value,
                effective_from=ef, effective_from_basis=efb,
                effective_to=et, effective_to_basis=etb,
                source_pdf=v.get("source_pdf", ""),
                source_url=v.get("source_url", ""),
                fetched_date=FETCHED_DATE,
                extraction_method=EXTRACTION_METHOD,
                built_by_script="95_parse_compact_terms.py",
                **r))

    # --- write -------------------------------------------------------------
    write_csv(CLEAN / "compact_structured_terms.csv", term_rows, TERM_FIELDS)
    write_csv(CLEAN / "compact_required_reports.csv", report_rows, REPORT_FIELDS)
    write_csv(REVIEW / f"compact_parse_unresolved_{TODAY}.csv",
              unresolved, UNRESOLVED_FIELDS)

    # --- summarise ---------------------------------------------------------
    parsed_versions = sorted(set(list(raw_terms) + list(raw_reports)))
    parsed_compacts = {v["compact_id"] for v in versions
                       if v["version_id"] in set(parsed_versions)}
    term_compacts = {r["compact_id"] for r in term_rows}
    rep_compacts = {r["compact_id"] for r in report_rows}
    states = {r["state"] for r in term_rows if r["state"]}

    inv_by_version = {}
    for r in term_rows:
        if r["formula_invertibility"]:
            inv_by_version[r["version_id"]] = r["formula_invertibility"]
    inv_versions = [k for k, x in inv_by_version.items()
                    if x == "INVERTIBLE_FLAT_RATE"]
    inv_compacts = {v["compact_id"] for v in versions
                    if v["version_id"] in set(inv_versions)}

    say("")
    say(f"versions attempted        {len(todo):,}")
    say(f"  no readable PDF         {n_no_pdf:,}")
    say(f"  no text layer           {n_no_text:,}")
    say(f"  text but nothing found  {n_no_terms:,}")
    say(f"term rows                 {len(term_rows):,}")
    say(f"report obligations        {len(report_rows):,}")
    say(f"compacts with >=1 term    {len(term_compacts):,} of {len(compacts):,}")
    say(f"compacts with >=1 report  {len(rep_compacts):,}")
    say(f"states covered            {len(states)}")
    say(f"compacts w/ invertible flat-rate formula  {len(inv_compacts):,}")
    say(f"unresolved rows           {len(unresolved):,}")
    say("")
    say("term_field counts:")
    for k, n in Counter(r["term_field"] for r in term_rows).most_common():
        say(f"  {k:34s} {n:6,}  compacts={len({r['compact_id'] for r in term_rows if r['term_field']==k}):4,}")
    say("")
    say("report frequency:")
    for k, n in Counter(r["frequency"] for r in report_rows).most_common(12):
        say(f"  {k:22s} {n:6,}")
    say("report recipient side:")
    for k, n in Counter(r["recipient_side"] for r in report_rows).most_common():
        say(f"  {k:22s} {n:6,}")
    say("disclosure as stated in the compact:")
    for k, n in Counter(r["public_availability"] for r in report_rows).most_common():
        say(f"  {k:30s} {n:6,}")
    say("")
    say("reporting obligations by state, against what we can already show the "
        "state regulator publishes:")
    # A compact ordering a report proves the STATE HOLDS the series. It does not
    # prove the state PUBLISHES it. The only honest evidence of publication is a
    # published file we have actually read - so the check is against
    # gaming_capacity_official.csv, whose every row carries a live source_url.
    published = defaultdict(set)
    for r in read_csv(CLEAN / "gaming_capacity_official.csv"):
        u = r.get("source_url", "")
        s = (r.get("state") or "").strip()
        if s and u and "bia.gov" not in u and "sec.gov" not in u:
            published[s].add(u.split("/")[2] if "//" in u else u[:40])
    ABBR = {"Arizona": "AZ", "California": "CA", "Colorado": "CO",
            "Connecticut": "CT", "Florida": "FL", "Idaho": "ID",
            "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Louisiana": "LA",
            "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
            "Mississippi": "MS", "Montana": "MT", "Nebraska": "NE",
            "Nevada": "NV", "New Mexico": "NM", "New York": "NY",
            "North Carolina": "NC", "North Dakota": "ND", "Oklahoma": "OK",
            "Oregon": "OR", "Rhode Island": "RI", "South Dakota": "SD",
            "Washington": "WA", "Wisconsin": "WI", "Wyoming": "WY"}
    st = defaultdict(set)
    for r in report_rows:
        st[r["state"]].add(r["compact_id"])
    for k, s in sorted(st.items(), key=lambda x: -len(x[1])):
        hosts = published.get(ABBR.get(k, k), set())
        ev = ("regulator file already held: " + ", ".join(sorted(hosts)[:3])
              if hosts else "NO published regulator file held yet")
        say(f"  {k:18s} {len(s):4,} compacts   {ev}")

    (INTERIM / "95_run_summary.txt").write_text(log.getvalue(), encoding="utf-8")
    print(f"\n  summary -> data/interim/95_run_summary.txt")


if __name__ == "__main__":
    main()
