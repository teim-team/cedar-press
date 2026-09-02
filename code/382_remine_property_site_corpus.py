#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
Cedar Press - PHASE 1: re-mine the property-site corpus already on disk.
========================================================================

    code/382_remine_property_site_corpus.py            built 2026-08-26

**ZERO NETWORK REQUESTS.** Every byte read by this script was already fetched by
`code/142_build_property_site_observations.py` on 2026-08-12 and is sitting in
`data/raw/external/gaming_property_sites/pages/` - 1,749 pages, 144 hosts,
357 MB. Nothing here contacts a host, reads a robots.txt, or opens a socket.

WHY THIS EXISTS
---------------
142 mined that corpus for exactly one thing: CAPACITY numbers, on ten metrics,
262 rows. It never looked for the four other kinds of fact a casino publishes
about itself, and three of them are things Cedar has nowhere else:

  1. EMPLOYMENT CLAIMS. Measured 2026-08-26: **all 10,122 facility-level
     `employees` rows in `gaming_facility_metrics.csv` are the Casino City
     panel** - 100%, on 323 properties. Casino City is QA-reference-only and
     may never publish. A property's own "we employ 1,200 people" is a PRIMARY,
     NON-VENDOR source and is the only per-property employment evidence in this
     project that can ship.
  2. OPENING / RENOVATION / EXPANSION DATES. 415 gaming dates were carrying
     fabricated day-precision and were downgraded. A property's own
     "serving guests since 1996" is a real re-sourcing lead with a URL.
  3. OWNERSHIP AND OPERATOR STATEMENTS. "Owned and operated by the X Nation" is
     an ownership assertion from a non-federal source, and it feeds the
     certification evidence layer.
  4. LOYALTY PROGRAMME STRUCTURE AND TIERS.

THE MEASUREMENT-TYPE DISCIPLINE IS THE WHOLE JOB
------------------------------------------------
Marketing copy is promotional, not audited. "Over 1,500 slots" is a claim with
puffery and rounding risk; "more than 2,000 employees" is a boast. Two new
`cedar_domain.MeasurementType` terms carry that, written on the pattern
`GAME_FINDER_OBSERVATION` set - a comment saying what one row IS and IS NOT:

    SELF_PUBLISHED_MARKETING_CLAIM     capacity, off the operator's own site
    SELF_PUBLISHED_EMPLOYMENT_CLAIM    employment, off the operator's own site

Both are `is_observed` - the operator did count its own floor and its own
payroll, on a real date. **Both are in `NEVER_PROMOTES_TO_ACTIVE`**, because a
regulator's count and a website's boast are different measurements of different
things and must never be summed, averaged, or silently preferred. The full
reasoning, including the three defects marketing copy carries that a regulator
filing does not, is in `cedar_domain.py` beside the terms.

**A number with no verbatim sentence is unusable and is REFUSED at write.** Not
downgraded - refused. `source_quote` is asserted non-empty on every row before
the file is opened.

WHAT IS DELIBERATELY *NOT* A MeasurementType
--------------------------------------------
Dates, ownership statements and loyalty tiers measure nothing about capacity or
employment. They are written to a separate file with an `assertion_class`
column and an explicit note saying they are outside the count vocabulary - the
same decision 142 made for `LABOR_DEMAND_STATEMENT`, and for the same reason:
a vocabulary that admits everything stops distinguishing anything.

FOUR RULES THIS BUILD HONOURS, EACH ONE PAID FOR ALREADY
--------------------------------------------------------
* **NEVER RULE A HISTORICAL RECORD AGAINST A CURRENT PAGE.** Three gaming
  rulings were withdrawn 2026-08-06 for exactly this - properties that closed in
  2003-2005 ruled "not a casino" against 2026 pages. **The record's own close
  date is checked FIRST.** A facility with a close date earlier than the page
  capture is routed to `review/` with the dates named, never into the claims
  file. And a row that is `current` AND carries a close date is a REOPENED
  property, not a contradiction - 115 such rows exist - so those are kept.
* **A MANAGEMENT BRAND IS NOT OWNERSHIP.** Caesars *manages* Harrah's Cherokee;
  EBCI *owns* it. An ownership sentence is recorded as an ASSERTION with the
  asserted owner verbatim, and compared against the curated `gaming_facilities`
  tribe in `agrees_with_curated_owner`. **Cedar's curated file outranks this
  file always.** Nothing here overwrites an owner and nothing here mints one.
* **NO NEW FACILITY ID IS MINTED.** Asserted per row against
  `gaming_facilities.csv` before write.
* **DETERMINISTIC KEYS ONLY** (class 7). Every id is a sha1 digest of the
  identifying fields - never a positional index, never `hash()`, which Python
  randomises per process.

OUTPUTS - ALL STAGED, NOTHING IN data/clean
--------------------------------------------
`gaming_facility_metrics.csv` has multiple writers and was moving during this
work, so this build writes **nothing** to `data/clean/` and creates **no new
clean table** - which is also why it cannot move any of the five shipping
registration counters `62` is currently failing on for another agent.

    data/staging/gaming_property_self_published_claims_<date>.csv
    data/staging/gaming_property_self_published_assertions_<date>.csv
    data/staging/gaming_property_loyalty_tiers_<date>.csv
    review/gaming_property_claims_refused_382_<date>.csv
    logs/382_summary_<date>.json

    py -3 code/382_remine_property_site_corpus.py
    py -3 code/382_remine_property_site_corpus.py --limit 200   # smoke test
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import importlib.util
import json
import os
import re
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = os.path.join(ROOT, "code")
RAW = os.path.join(ROOT, "data", "raw", "external", "gaming_property_sites")
PAGES = os.path.join(RAW, "pages")
CLEAN = os.path.join(ROOT, "data", "clean")
INTERIM = os.path.join(ROOT, "data", "interim")
STAGING = os.path.join(ROOT, "data", "staging")
REVIEW = os.path.join(ROOT, "review")
LOGS = os.path.join(ROOT, "logs")
for _d in (STAGING, REVIEW, LOGS):
    os.makedirs(_d, exist_ok=True)

TODAY = dt.date.today().isoformat()
SCRIPT = "code/382_remine_property_site_corpus.py"
csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))

CRAWL_CSV = os.path.join(INTERIM, "142_crawl_manifest.csv")
DOMAINS_CSV = os.path.join(INTERIM, "142_property_domains.csv")
FACILITIES = os.path.join(CLEAN, "gaming_facilities.csv")

OUT_CLAIMS = os.path.join(
    STAGING, "gaming_property_self_published_claims_%s.csv" % TODAY)
OUT_ASSERT = os.path.join(
    STAGING, "gaming_property_self_published_assertions_%s.csv" % TODAY)
OUT_LOYALTY = os.path.join(
    STAGING, "gaming_property_loyalty_tiers_%s.csv" % TODAY)
OUT_REFUSED = os.path.join(
    REVIEW, "gaming_property_claims_refused_382_%s.csv" % TODAY)
OUT_LOG = os.path.join(LOGS, "382_summary_%s.json" % TODAY)


# ---------------------------------------------------------------------------
# shared project code. Reuse, never re-implement (standing rule 8).
# ---------------------------------------------------------------------------
def _load(mod_path, name):
    spec = importlib.util.spec_from_file_location(name, mod_path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


sys.path.insert(0, CODE)
cedar_domain = _load(os.path.join(CODE, "cedar_domain.py"), "cedar_domain_382")
_p142 = _load(os.path.join(CODE, "142_build_property_site_observations.py"),
              "property_sites_142")

MT = cedar_domain.MeasurementType
to_text = _p142.to_text
snippet = _p142.snippet
sha = _p142.sha
SEED_PROPERTY_RULINGS = _p142.SEED_PROPERTY_RULINGS

# The two new types must be unpromotable. Asserted at import, like 142 does for
# GAME_FINDER_OBSERVATION, so a later edit to cedar_domain that relaxes the rule
# breaks this build loudly instead of quietly changing what its rows mean.
for _t in (MT.SELF_PUBLISHED_MARKETING_CLAIM, MT.SELF_PUBLISHED_EMPLOYMENT_CLAIM):
    assert _t in cedar_domain.NEVER_PROMOTES_TO_ACTIVE, (
        "%s must never be promotable to ACTIVE_FLOOR_COUNT" % _t.value)
    assert not cedar_domain.may_promote(_t, MT.ACTIVE_FLOOR_COUNT)
    assert _t.is_observed, "%s is an observation of a real population" % _t.value


def digest(*parts):
    """Deterministic key. NEVER hash() - Python randomises string hashing per
    process, so the same row would get a different id every run (class 7)."""
    h = hashlib.sha1("\x1f".join(str(p) for p in parts).encode("utf-8"))
    return h.hexdigest()[:12]


def read_csv(p):
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


# Explicit schemas. Declared rather than inferred from row 0, so an empty run
# still writes a well-formed header and a heterogeneous family (a date
# assertion and an ownership assertion carry different extra columns) cannot
# silently lose a column depending on which row happened to sort first.
BASE_FIELDS = [
    "facility_id", "facility_name", "tribe_id", "tribe_name", "state",
    "entity_id", "site_host", "source_url", "source_quote", "retrieved_at",
    "as_of_date", "as_of_date_precision", "as_of_date_basis", "source_file",
    "source_md5", "attribution_basis", "confidence", "built_by_script",
    "built_date",
]
CLAIM_FIELDS = ["claim_id", "family", "metric", "value", "unit",
                "measurement_type", "measurement_basis", "value_is_bounded",
                "bound_direction", "bound_basis", "population_stated",
                "scope_stated", "vocabulary_status", "not_summable_with",
                "page_class"] + BASE_FIELDS
ASSERT_FIELDS = ["assertion_id", "assertion_class", "assertion_subclass",
                 "assertion_class_note", "asserted_value",
                 "asserted_value_verbatim", "asserted_precision",
                 "asserted_owner_names_tribal_form",
                 "asserted_owner_is_management_brand", "cedar_curated_owner",
                 "agrees_with_curated_owner", "cedar_open_date",
                 "cedar_open_date_precision",
                 "agrees_with_cedar_open_year"] + BASE_FIELDS
LOYALTY_FIELDS = ["loyalty_id", "assertion_class", "assertion_class_note",
                  "programme_name_as_published", "tier_name", "tier_rank",
                  "tier_rank_basis", "n_tiers_found_on_page"] + BASE_FIELDS
REFUSED_FIELDS = ["site_host", "source_url", "family", "metric", "value",
                  "refusal_reason", "source_quote", "retrieved_at",
                  "facility_id", "built_by_script"]


def write_csv(p, rows, fields=None):
    """`.part` then rename - an interruption must not look like a completion."""
    if not fields:
        fields = list(rows[0].keys()) if rows else []
    tmp = p + ".part"
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    if os.path.exists(p):
        os.remove(p)
    os.rename(tmp, p)


# ---------------------------------------------------------------------------
# THE MEASURE VOCABULARY. Reused from gaming_facility_metrics.metric - NOT
# invented here. The ten measures that file already carries are, by row count:
#   gaming_machines, employees, gaming_square_feet, restaurants, parking_spaces,
#   table_games, poker_tables, hotel_rooms, convention_square_feet, bingo_seats
# 142 wrote `meeting_square_feet`, which is a PARALLEL NAME for
# `convention_square_feet`. This build uses the metrics-table name and records
# the divergence rather than propagating a second vocabulary.
# ---------------------------------------------------------------------------
METRICS_TABLE_VOCAB = {
    "gaming_machines", "employees", "gaming_square_feet", "restaurants",
    "parking_spaces", "table_games", "poker_tables", "hotel_rooms",
    "convention_square_feet", "bingo_seats",
}
PARALLEL_NAME_FIX = {"meeting_square_feet": "convention_square_feet"}
# Measures the site corpus carries that the metrics table has no term for. They
# are kept, flagged, and NOT forced into a neighbouring term.
NEW_MEASURES = {"venue_capacity", "bars_lounges", "hotel_suites", "rv_spaces"}

UNITS = {
    "gaming_machines": "machines", "table_games": "tables",
    "poker_tables": "tables", "bingo_seats": "seats",
    "hotel_rooms": "rooms", "hotel_suites": "rooms",
    "gaming_square_feet": "sq_ft", "convention_square_feet": "sq_ft",
    "venue_capacity": "persons", "parking_spaces": "spaces",
    "restaurants": "outlets", "bars_lounges": "outlets",
    "rv_spaces": "spaces", "employees": "persons",
}

NUM = r"([0-9][0-9,]{0,8}(?:\.[0-9]+)?)"

# ---- EMPLOYMENT. The layer where Casino City is 100% of the current series. ----
EMPLOY_PATTERNS = [
    # "employs more than 1,200 people" / "employing over 900 team members"
    re.compile(r"\bemploy(?:s|ing|ed|ee[ds]?)?\b[^.\n]{0,40}?"
               r"\b(?:more than|over|nearly|approximately|about|some|upwards of)?\s*"
               + NUM + r"\+?\s*"
               r"(?:full[- ]time |part[- ]time |dedicated |talented |local |"
               r"tribal |valued )*"
               r"(people|employees|team members|associates|staff members|"
               r"staff|workers|individuals|members|persons)\b", re.I),
    # "1,200 employees" preceded by a counting cue
    re.compile(r"\b(?:more than|over|nearly|approximately|about|some|with|of|"
               r"has|have|and|to|our|home to|provides?|supports?|created?|"
               r"creating|employs)\s+" + NUM + r"\+?\s*"
               r"(?:full[- ]time |part[- ]time |dedicated |talented |local |"
               r"tribal |valued |casino |property |resort )*"
               r"(employees|team members|associates|jobs|positions|"
               r"staff members)\b", re.I),
    # "a workforce of over 2,000" / "a team of 1,500"
    re.compile(r"\b(?:workforce|work force|staff|team|payroll)\s+of\s+"
               r"(?:more than|over|nearly|approximately|about)?\s*" + NUM
               + r"\+?\b", re.I),
]
# A qualitative employment claim with no number. Recorded as an ASSERTION, not
# as a measurement - there is nothing to measure.
EMPLOYER_CLAIM = re.compile(
    r"[^.\n]{0,180}\b(?:one of the |the )?(?:largest|biggest|leading|top)\s+"
    r"(?:private\s+)?employers?\b[^.\n]{0,180}", re.I)

# What population does the sentence actually declare? Blank means UNDECLARED -
# never "all employees".
POP_FULLTIME = re.compile(r"\bfull[- ]time\b", re.I)
POP_PARTTIME = re.compile(r"\bpart[- ]time\b", re.I)
POP_TRIBAL = re.compile(r"\btribal (?:members?|citizens?)\b", re.I)
# The scope trap: "the tribe's enterprises employ 3,000" is NOT this property.
SCOPE_ENTERPRISE = re.compile(
    r"\b(?:enterprises|businesses|operations|properties|divisions|"
    r"subsidiaries|entities|holdings|companies)\b", re.I)
SCOPE_TRIBE_WIDE = re.compile(
    r"\b(?:the\s+)?(?:tribal government|tribe|nation|band|pueblo|community)"
    r"['’]?s?\s+(?:is\s+the\s+|total|combined|overall|employs)"
    r"|\bthe (?:tribal government|tribe|nation) (?:is|employs)\b", re.I)
# Measured on this corpus, three sentence shapes that contain a number and the
# word "employee" and are NOT a headcount claim. Each is named rather than
# counted, so the next reader can see what was dropped and why.
NOT_A_HEADCOUNT = re.compile(
    r"\b(raised?|raising|relay for life|walkathon|donat\w+|volunteer\w+|"
    r"charit\w+|sweepstakes|drawing|are not eligible|not eligible|excluded|"
    r"immediate family|employee plan|employee coverage|employer match|"
    r"employer paid|employee clinic|employee discount|401\(?k\)?|"
    r"employment application|employment office|best employers)\b", re.I)
# A past-tense or job-creation sentence is a real claim about a DIFFERENT
# quantity: what a facility once had, or what a project was said to create.
PAST_TENSE = re.compile(r"\b(employed|had|was|were|formerly|at the time|"
                        r"upon opening|when it opened)\b", re.I)
JOB_CREATION = re.compile(r"\b(created?|creating|will create|generat\w+|"
                          r"added|supports?|sustain\w+)\s+"
                          r"(?:employment|jobs?|positions?)\b", re.I)
# THREE SENTENCE SHAPES THAT LOOK LIKE A HEADCOUNT AND ARE NOT. Each was
# MEASURED on this corpus on the first full pass and each produced a row that
# would have been wrong in a different way, so each is refused with its own
# named reason rather than folded into one counter.
HIRING_CONTEXT = re.compile(
    r"\b(job fair|career fair|hiring event|now hiring|we(?:'| a)re hiring|"
    r"accepting applications|apply (?:today|now|online)|open positions|"
    r"positions available|will hire|to fill|seeking to fill|"
    r"job opportunities)\b", re.I)
# Talking Stick Resort: "...will be accepting applications for more than 300
# positions" - that is LABOR DEMAND (142's own vocabulary), not employment.
BIO_ANOTHER_PROPERTY = re.compile(
    r"\b(prior to|previously|before joining|during (?:his|her|their) time at|"
    r"(?:his|her|their) (?:time|career|tenure) at|worked at|came to us from|"
    r"joins? (?:us )?from)\b", re.I)
# Valley View: "During his time at The Resort at Pelican Hill, Maneesh led a
# [team of 350]" - an executive bio counting a DIFFERENT company's staff.
DEPARTMENT_SUBSET = re.compile(
    r"\b(department|departments|division|divisions|team of|"
    r"direct (?:staff|reports?)|oversees|manages a (?:team|staff)|"
    r"his team|her team|their team)\b", re.I)
# KwaTaqNuk: "300 employees carry out the natural resource protection ...
# including Natural Resources, Forestry, Lands" - a tribal government
# department roster, not a casino headcount.

# ---- CAPACITY. Extra measures 142 has no pattern for. ----
#
# `bars_lounges` WAS BUILT AND REMOVED, MEASURED. On this corpus a number next
# to "bar" or "lounge" is almost always a VENUE NAME ("Bar 7" at Coushatta) or
# a date in an events strip ("...Thursday, August 13 ... Lounge"). Same shape as
# 142's "Fire 88 Slots" defect, in a new place. Precision was too low to keep
# and the yield was 2 rows, so the pattern is deleted rather than shipped with a
# caveat. Recorded here so the next agent does not rebuild it.
EXTRA_METRIC_PATTERNS = [
    ("hotel_suites", re.compile(
        NUM + r"\+?\s*(?:luxury |luxurious |spacious |well-appointed )*"
        r"suites\b", re.I)),
    ("rv_spaces", re.compile(
        NUM + r"\+?\s*(?:full[- ]hookup |paved )*RV (?:spaces|sites|spots|pads)\b",
        re.I)),
]

# ---- DATES. A property's own "since 1996" is a re-sourcing lead. ----
YEAR = r"((?:19|20)\d{2})"
MONTHS = (r"(January|February|March|April|May|June|July|August|September|"
          r"October|November|December)")
DATE_PATTERNS = [
    ("opening", re.compile(
        r"\b(?:opened|opening|first opened|originally opened|open(?:ed)? its doors|"
        r"welcomed its first guests?)\b[^.\n]{0,50}?\b(?:in|on)\s+(?:"
        + MONTHS + r"\s+(?:\d{1,2},?\s+)?)?" + YEAR + r"\b", re.I)),
    ("in_operation_since", re.compile(
        r"\b(?:since|serving[^.\n]{0,30}since|in (?:business|operation) since|"
        r"established in|founded in|opened in)\s+" + YEAR + r"\b", re.I)),
    ("expansion", re.compile(
        r"\b(?:expan\w+|added|opened a new|new tower|new hotel|"
        r"grand re-?opening)\b[^.\n]{0,60}?\b(?:in|completed in|since)\s+"
        + YEAR + r"\b", re.I)),
    ("renovation", re.compile(
        r"\b(?:renovat\w+|remodel\w+|refurbish\w+|redesign\w+|"
        r"transformed)\b[^.\n]{0,60}?\b(?:in|completed in)\s+" + YEAR + r"\b",
        re.I)),
    ("anniversary", re.compile(
        r"\b(?:celebrat\w+|marking|marks)\b[^.\n]{0,40}?\b"
        r"(\d{1,3})(?:st|nd|rd|th)?\s+(?:year )?anniversary\b", re.I)),
]

# ---- OWNERSHIP. An assertion, never a determination. ----
OWNER_TAIL = (r"((?:the\s+)?[A-Z][\w'’.\-]*(?:\s+(?:of|and|the|de|del)?\s*"
              r"[A-Z][\w'’.\-]*){0,7})")
OWNERSHIP_PATTERNS = [
    ("owned_and_operated_by", re.compile(
        r"\bowned\s+and\s+operated\s+by\s+" + OWNER_TAIL)),
    ("owned_by", re.compile(
        r"\b(?:is\s+|are\s+)?(?:wholly[- ]|solely\s+)?owned\s+by\s+"
        + OWNER_TAIL)),
    ("operated_by", re.compile(r"\boperated\s+by\s+" + OWNER_TAIL)),
    ("enterprise_of", re.compile(
        r"\b(?:is\s+an?|an?)\s+(?:wholly[- ]owned\s+)?"
        r"(?:enterprise|entity|instrumentality|division|subsidiary|"
        r"business|corporation|arm|venture)\s+of\s+" + OWNER_TAIL)),
    ("owner_asserts", re.compile(
        OWNER_TAIL + r"\s+(?:proudly\s+)?owns\s+and\s+operates\b")),
]
# A named tribal-government form in the asserted owner is what makes an
# ownership sentence worth keeping. Without one it is usually a management
# brand or a marketing agency.
TRIBAL_FORM = re.compile(
    r"\b(Tribe|Tribes|Tribal|Nation|Band|Pueblo|Community|Rancheria|"
    r"Reservation|Indians?|Village|Corporation|Colony|Confederated|"
    r"Gaming Authority|Gaming Commission|Gaming Enterprise|Development "
    r"Authority|Economic Development)\b")
# A MANAGEMENT BRAND IS NOT OWNERSHIP. Caesars manages Harrah's Cherokee; EBCI
# owns it. These strings appearing as the asserted owner make the row a
# MANAGEMENT assertion, never an ownership one.
# A TOKEN THAT MAKES A NAME A TRIBE IN ONE STRING CAN BE A BRAND IN ANOTHER.
# Measured: Gun Lake Casino's page yielded `owned_by -> "Live Nation"` because
# TRIBAL_FORM matched the word "Nation" inside a concert promoter's name. This
# is `core()` folding `indian` into National Education Association, arriving in
# a third place. The guard is an explicit list, not a cleverer regex - a token
# that appears in one name and not the other is never noise, and the only way
# to know which is which here is to name the brands.
NOT_A_TRIBE = re.compile(
    r"\b(Live Nation|Carnival|One Nation|Nation(?:al|wide|s League)|"
    r"Ticketmaster|AEG|Doordash|Grubhub|First Nations Development|"
    r"Native American Rights Fund|Indian Gaming Association|"
    r"National Indian|The Nation)\b", re.I)
MANAGEMENT_BRANDS = re.compile(
    r"\b(Caesars|Harrah|Hard Rock|Seminole Hard Rock|Station Casinos|"
    r"Warner Gaming|Full House Resorts|Lakes Entertainment|Global Gaming|"
    r"Sodak|Multimedia Games|Marriott|Hilton|Choice Hotels|IHG|Wyndham|"
    r"Delaware North|Aramark|Sodexo)\b", re.I)

# ---- LOYALTY. Programme structure and tiers. ----
LOYALTY_PATH = re.compile(
    r"(rewards?|players?[-_]?club|player[-_]?s[-_]?club|loyalty|"
    r"club[-_]?card|my[-_]?club|winners?[-_]?club|advantage[-_]?club)", re.I)
TIER_TOKENS = [
    "Classic", "Bronze", "Copper", "Silver", "Gold", "Platinum", "Titanium",
    "Diamond", "Black Diamond", "Double Diamond", "Ruby", "Emerald",
    "Sapphire", "Onyx", "Elite", "Premier", "Prestige", "Signature",
    "Select", "Preferred", "Legend", "Legends", "Chairman", "President",
    "Star", "Superstar", "Eagle", "Chief", "Buffalo", "Thunder", "Blue",
    "Red", "Green", "Purple", "Crimson", "Jade", "Pearl", "Opal",
]
TIER_CONTEXT = re.compile(r"\b(tier|tiers|level|levels|status|card|"
                          r"membership|member level)\b", re.I)

# ---- the ticker / game-title guard, sharper than 142's ----
# A "recent winners" ticker is the single richest source of false counts in this
# corpus. Its signature is a personal name with an initial, a dollar amount and
# a slash date, all within one line.
TICKER = re.compile(
    r"(Recent Winners|Latest Winners|Jackpot Winners|"
    r"[A-Z][a-z]+\s+[A-Z]\.\s*[·•|\-]\s*\$|"
    r"\$[\d,]+\.\d\d\s*[·•|\-])")
SLASH_DATE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b")
PRICE = re.compile(r"\$\s*[\d,]+")

BOUND_OVER = re.compile(r"\b(over|more than|upwards of|in excess of|at least|"
                        r"north of|greater than|exceeding)\b", re.I)
BOUND_UNDER = re.compile(r"\b(up to|as many as|as much as|no more than|"
                         r"fewer than|less than|under)\b", re.I)
BOUND_APPROX = re.compile(r"\b(nearly|approximately|about|almost|roughly|"
                          r"around|some|close to|~)\b", re.I)


def bound_of(quote, num_start):
    """Which way does the qualifier point? Read from the 40 characters before
    the number, so a qualifier belonging to a later number in the same sentence
    is not borrowed."""
    before = quote[max(0, num_start - 40):num_start]
    if BOUND_OVER.search(before):
        return "LOWER_BOUND", "the sentence says the true value is at least this"
    if BOUND_UNDER.search(before):
        return "UPPER_BOUND", "the sentence says the true value is at most this"
    if BOUND_APPROX.search(before):
        return "APPROXIMATE", "the sentence marks the figure as approximate"
    return "AS_STATED", "the sentence states the figure without a qualifier"


def tonum(s):
    try:
        return float(str(s).replace(",", "").rstrip("."))
    except Exception:
        return None


PLAUSIBLE = {
    "gaming_machines": (20, 15000), "table_games": (1, 400),
    "poker_tables": (1, 200), "bingo_seats": (20, 5000),
    "hotel_rooms": (5, 4000), "hotel_suites": (1, 1500),
    "gaming_square_feet": (1000, 1200000),
    "convention_square_feet": (500, 1200000),
    "venue_capacity": (50, 100000), "parking_spaces": (20, 30000),
    "restaurants": (1, 60), "bars_lounges": (1, 40), "rv_spaces": (5, 1000),
    "employees": (10, 25000),
}


def plausible(metric, val):
    lo_hi = PLAUSIBLE.get(metric)
    return bool(lo_hi) and val is not None and lo_hi[0] <= val <= lo_hi[1]


def bad_context(quote, num_start):
    """Reasons a number in this sentence is not the count it looks like.
    Returns a refusal reason, or '' to accept."""
    window = quote[max(0, num_start - 90):num_start + 90]
    if TICKER.search(window):
        return ("jackpot / recent-winners ticker: a personal name, a dollar "
                "amount or a slash date sits beside the number")
    if SLASH_DATE.search(quote[max(0, num_start - 18):num_start + 18]):
        return "a slash date sits within 18 characters of the number"
    if re.search(r"\$\s*$", quote[max(0, num_start - 3):num_start]):
        return "the number is a dollar amount, not a count"
    if re.search(r"^\s*(?:%|percent|°)", quote[num_start:num_start + 10]):
        return "the number is a percentage"
    return ""


# ---------------------------------------------------------------------------
# facilities, hosts, and the HISTORICAL guard
# ---------------------------------------------------------------------------
def load_facilities():
    facs = read_csv(FACILITIES)
    by_id = {f["facility_id"]: f for f in facs}
    return facs, by_id


def historical_guard(fac, page_date):
    """NEVER RULE A HISTORICAL RECORD AGAINST A CURRENT PAGE.

    Returns (ok, reason). Checked BEFORE anything is extracted for a facility,
    which is the ordering three withdrawn 2026-08-06 rulings paid for.

    A row that is `current` AND carries a close date is a REOPENED property -
    115 such rows exist in gaming_facilities.csv - and is NOT a contradiction,
    so it passes."""
    if not fac:
        return True, ""
    close = (fac.get("close_date") or "").strip()
    if not close:
        return True, ""
    status = ((fac.get("property_status") or "") + " "
              + (fac.get("property_status_literal") or "")
              + " " + (fac.get("observation_status") or "")).lower()
    if re.search(r"\b(current|open|operating|temporarily closed|"
                 r"under construction)\b", status):
        return True, ("close date %s present with a current status - a REOPENED "
                      "property, not a contradiction" % close)
    close_day = close[:10]
    if close_day and close_day < page_date:
        return False, ("HISTORICAL RECORD, CURRENT PAGE: the Cedar record "
                       "closes this property on %s and the page was captured "
                       "on %s. A %s page cannot testify about a property that "
                       "closed in %s. Routed to review rather than extracted."
                       % (close, page_date, page_date[:4], close_day[:4]))
    return True, ""


# ---------------------------------------------------------------------------
# extraction
# ---------------------------------------------------------------------------
def base_row(fac, host, mrow, quote, url):
    return dict(
        facility_id=fac.get("facility_id", "") if fac else "",
        facility_name=fac.get("facility_name", "") if fac else "",
        tribe_id=fac.get("tribe_id", "") if fac else "",
        tribe_name=fac.get("tribe", "") if fac else "",
        state=fac.get("state", "") if fac else "",
        entity_id=fac.get("entity_id", "") if fac else "",
        site_host=host,
        source_url=url,
        source_quote=quote,
        retrieved_at=mrow.get("fetched_date", ""),
        as_of_date=mrow.get("fetched_date", ""),
        as_of_date_precision="observed_on_retrieval_date",
        as_of_date_basis=("the operator does not date its own marketing copy; "
                          "this is the date Cedar captured the page, and it is "
                          "an upper bound on when the claim was true"),
        source_file=os.path.basename(mrow.get("file", "")),
        built_by_script=SCRIPT,
        built_date=TODAY,
    )


def run(limit=None):
    facs, fac_by_id = load_facilities()
    valid_ids = set(fac_by_id)
    doms = [r for r in read_csv(DOMAINS_CSV) if r.get("verified") == "yes"]
    host_props = defaultdict(list)
    for r in doms:
        if r.get("final_host"):
            host_props[r["final_host"]].append(r)

    man = [r for r in read_csv(CRAWL_CSV) if r.get("file")]
    by_file = {}
    for r in man:
        by_file[r["file"]] = r

    print("=== 382: re-mine the property-site corpus already on disk ===")
    print("  ZERO network requests. Pages on disk: %d"
          % len(os.listdir(PAGES)))
    print("  manifest rows with a file: %d" % len(by_file))
    print("  verified hosts: %d" % len(host_props))

    claims, asserts, loyalty, refused = [], [], [], []
    stats = Counter()
    pages_read = 0
    hosts_seen = set()
    fac_hist_blocked = {}

    items = sorted(by_file.items())
    if limit:
        items = items[:limit]

    for fname, mrow in items:
        fp = os.path.join(PAGES, fname)
        if not os.path.exists(fp):
            stats["page file missing from disk: %s" % fname] += 0
            stats["pages_in_manifest_absent_from_disk"] += 1
            continue
        host = mrow.get("host", "")
        url = mrow.get("url", "")
        page_date = (mrow.get("fetched_date") or TODAY)[:10]
        raw = open(fp, "rb").read()
        # SOFT HYPHENS AND ZERO-WIDTH JOINERS SPLIT A WORD THE PARSER NEEDS.
        # Measured on kwataqnuk.com: "Approxi­mately 300 employees" - the
        # rendered text reads normally and every `\bapproximately\b` pattern
        # misses it. Folding these is punctuation folding, not identity
        # folding: no token that distinguishes anything is removed.
        text = to_text(raw).replace("­", "").replace("​", "") \
                           .replace("‌", "").replace("‍", "") \
                           .replace("﻿", "")
        if len(text) < 300:
            stats["pages_too_short_to_read"] += 1
            continue
        pages_read += 1
        hosts_seen.add(host)
        md5 = sha(raw)

        props = host_props.get(host, [])
        fid, attrib = _p142.attribute(host, props)
        fac = fac_by_id.get(fid) if fid in valid_ids else None
        if fid and fid not in valid_ids:
            # No new facility id is minted anywhere in this build.
            fid, attrib = "", ("facility id %s is not in gaming_facilities.csv "
                               "- refused rather than minted" % fid)

        ok, why = historical_guard(fac, page_date)
        if not ok:
            fac_hist_blocked[fid] = why
            refused.append(dict(
                site_host=host, source_url=url, family="ALL",
                metric="", value="", refusal_reason=why,
                source_quote="", retrieved_at=page_date,
                facility_id=fid, built_by_script=SCRIPT))
            stats["pages_blocked_by_historical_guard"] += 1
            continue

        path = (url.split("?")[0] or "").lower()

        # ---------------- EMPLOYMENT ----------------
        for rx in EMPLOY_PATTERNS:
            for m in rx.finditer(text):
                val = tonum(m.group(1))
                quote = snippet(text, m.start(), m.end())
                rel = m.start(1) - max(0, m.start() - 110)
                rel = max(0, min(rel, len(quote) - 1))
                if not plausible("employees", val):
                    stats["employment_refused_implausible"] += 1
                    refused.append(dict(
                        site_host=host, source_url=url, family="EMPLOYMENT",
                        metric="employees", value=m.group(1),
                        refusal_reason=("outside the plausible band 10-25,000 "
                                        "for a casino property headcount"),
                        source_quote=quote, retrieved_at=page_date,
                        facility_id=fid, built_by_script=SCRIPT))
                    continue
                bad = bad_context(quote, rel)
                if not bad and NOT_A_HEADCOUNT.search(quote):
                    bad = ("the sentence is benefit-plan, promotion-eligibility "
                           "or fundraising boilerplate, not a headcount claim: "
                           + "|".join(sorted({g.lower() for g in
                                              NOT_A_HEADCOUNT.findall(quote)})))
                if not bad and HIRING_CONTEXT.search(quote):
                    bad = ("HIRING language: the sentence says the property "
                           "WANTS to hire N, not that it EMPLOYS N. That is "
                           "LABOR_DEMAND_STATEMENT (script 142's vocabulary) "
                           "and must never be read against an employment "
                           "series")
                if not bad and BIO_ANOTHER_PROPERTY.search(quote):
                    bad = ("EXECUTIVE BIO: the sentence counts staff at a "
                           "DIFFERENT company the person worked for before "
                           "joining. Attributing it to this property would be "
                           "a false attribution with a correct citation")
                if not bad and DEPARTMENT_SUBSET.search(quote):
                    bad = ("DEPARTMENT OR TEAM SUBSET: the sentence counts one "
                           "department, division or manager's team, not the "
                           "property. A subset published as a property total "
                           "understates it invisibly")
                if bad:
                    stats["employment_refused_context"] += 1
                    refused.append(dict(
                        site_host=host, source_url=url, family="EMPLOYMENT",
                        metric="employees", value=m.group(1),
                        refusal_reason=bad, source_quote=quote,
                        retrieved_at=page_date, facility_id=fid,
                        built_by_script=SCRIPT))
                    continue
                bd, bd_why = bound_of(quote, rel)
                pop = []
                if POP_FULLTIME.search(quote):
                    pop.append("full_time_stated")
                if POP_PARTTIME.search(quote):
                    pop.append("part_time_stated")
                if POP_TRIBAL.search(quote):
                    pop.append("tribal_members_stated")
                scope = "this_property_assumed_not_stated"
                if SCOPE_TRIBE_WIDE.search(quote):
                    scope = "TRIBE_WIDE_STATED"
                elif SCOPE_ENTERPRISE.search(quote):
                    scope = "MULTI_ENTERPRISE_LANGUAGE_PRESENT"
                if JOB_CREATION.search(quote):
                    scope += "|JOB_CREATION_CLAIM_not_a_current_headcount"
                elif PAST_TENSE.search(quote[:max(1, rel)]):
                    scope += "|PAST_TENSE_not_a_current_headcount"
                r = base_row(fac or {}, host, mrow, quote, url)
                r.update(
                    claim_id="SPC-" + digest(host, url, "employees",
                                             "%g" % val, quote[:120]),
                    family="EMPLOYMENT",
                    metric="employees",
                    value="%g" % val,
                    unit="persons",
                    measurement_type=MT.SELF_PUBLISHED_EMPLOYMENT_CLAIM.value,
                    measurement_basis=(
                        "a figure the operator publishes about itself in "
                        "marketing or about-us copy on its own website; it is "
                        "NOT an audited headcount and the population it counts "
                        "is undeclared unless population_stated says otherwise"),
                    value_is_bounded="Y" if bd != "AS_STATED" else "N",
                    bound_direction=bd, bound_basis=bd_why,
                    population_stated="|".join(pop),
                    scope_stated=scope,
                    vocabulary_status="IN_gaming_facility_metrics_metric",
                    not_summable_with=(
                        "OSHA_ESTABLISHMENT_REPORTED, "
                        "LODES_BLOCK_WORKPLACE_JOBS, "
                        "FORM5500_ACTIVE_PARTICIPANTS and the Casino City "
                        "employees series - four different populations"),
                    page_class="employment_or_about",
                    attribution_basis=attrib,
                    confidence="B" if fid else "C",
                    source_md5=md5)
                claims.append(r)
                stats["employment_claims"] += 1

        for m in EMPLOYER_CLAIM.finditer(text):
            quote = re.sub(r"\s+", " ", m.group(0)).strip()
            if len(quote) < 25:
                continue
            r = base_row(fac or {}, host, mrow, quote, url)
            r.update(
                assertion_id="SPA-" + digest(host, url, "largest_employer",
                                             quote[:120]),
                assertion_class="SELF_PUBLISHED_EMPLOYER_STANDING_CLAIM",
                assertion_class_note=(
                    "deliberately OUTSIDE cedar_domain.MeasurementType: there "
                    "is no number, so there is nothing to measure. It is a "
                    "RANK claim about a labour market Cedar has not defined "
                    "and cannot verify from this page."),
                asserted_value="", asserted_value_verbatim=quote,
                attribution_basis=attrib,
                confidence="C", source_md5=md5)
            asserts.append(r)
            stats["employer_standing_claims"] += 1

        # ---------------- EXTRA CAPACITY MEASURES ----------------
        for metric, rx in EXTRA_METRIC_PATTERNS:
            for m in rx.finditer(text):
                val = tonum(m.group(1))
                quote = snippet(text, m.start(), m.end())
                rel = max(0, min(m.start(1) - max(0, m.start() - 110),
                                 len(quote) - 1))
                if not plausible(metric, val):
                    # A COUNT IS NOT ACTIONABLE; A FILENAME IS A TASK. This
                    # counter previously incremented and dropped the candidate
                    # with no record of what it dropped - class 2c, and the
                    # linter was right to catch it in a script whose whole
                    # subject is refusals.
                    refused.append(dict(
                        site_host=host, source_url=url, family="CAPACITY",
                        metric=metric, value=m.group(1),
                        refusal_reason=("outside the plausible band %s for %s"
                                        % (PLAUSIBLE.get(metric), metric)),
                        source_quote=quote, retrieved_at=page_date,
                        facility_id=fid, built_by_script=SCRIPT))
                    stats["capacity_refused_implausible"] += 1
                    continue
                # 142's counting-cue guard, imported rather than rebuilt. A
                # number next to a noun is not a count of that noun: Foxwoods
                # publishes "DOUBLE QUEEN DELUXE ROOMS 774" in a table and the
                # bare pattern read 774 suites off it.
                if not _p142.has_counting_cue(text, m):
                    refused.append(dict(
                        site_host=host, source_url=url, family="CAPACITY",
                        metric=metric, value=m.group(1),
                        refusal_reason=("no counting cue before the number "
                                        "(142's guard, imported) - reads as a "
                                        "table cell, a venue name or a date"),
                        source_quote=quote, retrieved_at=page_date,
                        facility_id=fid, built_by_script=SCRIPT))
                    stats["capacity_refused_no_cue"] += 1
                    continue
                bad = bad_context(quote, rel)
                if bad:
                    refused.append(dict(
                        site_host=host, source_url=url, family="CAPACITY",
                        metric=metric, value=m.group(1), refusal_reason=bad,
                        source_quote=quote, retrieved_at=page_date,
                        facility_id=fid, built_by_script=SCRIPT))
                    stats["capacity_refused_context"] += 1
                    continue
                bd, bd_why = bound_of(quote, rel)
                r = base_row(fac or {}, host, mrow, quote, url)
                r.update(
                    claim_id="SPC-" + digest(host, url, metric, "%g" % val,
                                             quote[:120]),
                    family="CAPACITY",
                    metric=metric, value="%g" % val,
                    unit=UNITS.get(metric, ""),
                    measurement_type=MT.SELF_PUBLISHED_MARKETING_CLAIM.value,
                    measurement_basis=(
                        "a capacity figure the operator publishes about itself "
                        "in marketing copy on its own website; promotional, "
                        "not audited"),
                    value_is_bounded="Y" if bd != "AS_STATED" else "N",
                    bound_direction=bd, bound_basis=bd_why,
                    population_stated="", scope_stated="",
                    vocabulary_status=(
                        "IN_gaming_facility_metrics_metric"
                        if metric in METRICS_TABLE_VOCAB else
                        "NEW_MEASURE_no_term_in_gaming_facility_metrics"),
                    not_summable_with=(
                        "the regulator series in gaming_capacity_official.csv "
                        "and the Casino City panel - different measurements"),
                    page_class="property_page",
                    attribution_basis=attrib,
                    confidence="B" if fid else "C",
                    source_md5=md5)
                claims.append(r)
                stats["capacity_claims"] += 1

        # ---------------- DATES ----------------
        for kind, rx in DATE_PATTERNS:
            for m in list(rx.finditer(text))[:8]:
                g = [x for x in m.groups() if x]
                if not g:
                    continue
                yr = g[-1]
                quote = snippet(text, m.start(), m.end())
                if kind == "anniversary":
                    n = tonum(yr)
                    if not n or not (1 <= n <= 120):
                        continue
                    asserted = "%d years as of %s" % (int(n), page_date[:4])
                else:
                    y = tonum(yr)
                    if not y or not (1900 <= y <= int(TODAY[:4]) + 2):
                        continue
                    asserted = str(int(y))
                r = base_row(fac or {}, host, mrow, quote, url)
                r.update(
                    assertion_id="SPA-" + digest(host, url, kind, asserted,
                                                 quote[:120]),
                    assertion_class="SELF_PUBLISHED_DATE_ASSERTION",
                    assertion_class_note=(
                        "deliberately OUTSIDE cedar_domain.MeasurementType: a "
                        "date measures nothing about capacity or employment. "
                        "It is a RE-SOURCING LEAD for the 415 gaming dates "
                        "that were downgraded off fabricated day-precision, "
                        "and its own precision is YEAR - never a day."),
                    assertion_subclass=kind,
                    asserted_value=asserted,
                    asserted_value_verbatim=quote,
                    asserted_precision=("year" if kind != "anniversary"
                                        else "elapsed_years"),
                    cedar_open_date=(fac.get("open_date", "") if fac else ""),
                    cedar_open_date_precision=(
                        fac.get("open_date_precision", "") if fac else ""),
                    agrees_with_cedar_open_year=_year_agree(fac, kind, asserted),
                    attribution_basis=attrib,
                    confidence="B" if fid else "C",
                    source_md5=md5)
                asserts.append(r)
                stats["date_assertions"] += 1

        # ---------------- OWNERSHIP ----------------
        for kind, rx in OWNERSHIP_PATTERNS:
            for m in list(rx.finditer(text))[:6]:
                owner = re.sub(r"\s+", " ", m.group(1)).strip(" .,;:")
                if len(owner) < 4 or len(owner) > 90:
                    continue
                quote = snippet(text, m.start(), m.end())
                is_mgmt = bool(MANAGEMENT_BRANDS.search(owner))
                has_form = bool(TRIBAL_FORM.search(owner))
                if NOT_A_TRIBE.search(owner):
                    refused.append(dict(
                        site_host=host, source_url=url, family="OWNERSHIP",
                        metric=kind, value=owner,
                        refusal_reason=("the tribal-government form token in "
                                        "this string belongs to a non-tribal "
                                        "brand (e.g. 'Nation' inside 'Live "
                                        "Nation') - a token that makes a name "
                                        "a tribe in one string is a brand in "
                                        "another"),
                        source_quote=quote, retrieved_at=page_date,
                        facility_id=fid, built_by_script=SCRIPT))
                    stats["ownership_refused_brand_not_tribe"] += 1
                    continue
                if not has_form and not is_mgmt:
                    refused.append(dict(
                        site_host=host, source_url=url, family="OWNERSHIP",
                        metric=kind, value=owner,
                        refusal_reason=("the asserted owner names no tribal "
                                        "government form and no known "
                                        "management brand - most such matches "
                                        "are a marketing agency or a sentence "
                                        "fragment"),
                        source_quote=quote, retrieved_at=page_date,
                        facility_id=fid, built_by_script=SCRIPT))
                    stats["ownership_refused_no_form"] += 1
                    continue
                cls = ("MANAGEMENT_ASSERTION" if (is_mgmt or kind == "operated_by")
                       else "OWNERSHIP_ASSERTION")
                cur = (fac.get("tribe", "") if fac else "")
                r = base_row(fac or {}, host, mrow, quote, url)
                r.update(
                    assertion_id="SPA-" + digest(host, url, kind, owner,
                                                 quote[:120]),
                    assertion_class="SELF_PUBLISHED_" + cls,
                    assertion_class_note=(
                        "deliberately OUTSIDE cedar_domain.MeasurementType. "
                        "A MANAGEMENT BRAND IS NOT OWNERSHIP - Caesars MANAGES "
                        "Harrah's Cherokee, EBCI OWNS it - so an 'operated by' "
                        "sentence and a known management brand are typed "
                        "MANAGEMENT_ASSERTION and are never ownership "
                        "evidence. Cedar's curated gaming_facilities.csv "
                        "outranks every row in this file; nothing here "
                        "overwrites, mints or promotes an owner."),
                    assertion_subclass=kind,
                    asserted_value=owner,
                    asserted_value_verbatim=quote,
                    asserted_owner_names_tribal_form="Y" if has_form else "N",
                    asserted_owner_is_management_brand="Y" if is_mgmt else "N",
                    cedar_curated_owner=cur,
                    agrees_with_curated_owner=_owner_agree(owner, cur),
                    attribution_basis=attrib,
                    confidence="B" if fid else "C",
                    source_md5=md5)
                asserts.append(r)
                stats["ownership_assertions" if cls == "OWNERSHIP_ASSERTION"
                      else "management_assertions"] += 1

        # ---------------- LOYALTY ----------------
        if LOYALTY_PATH.search(path) or LOYALTY_PATH.search(text[:2000]):
            found = []
            for t in TIER_TOKENS:
                for m in re.finditer(r"\b" + re.escape(t) + r"\b", text):
                    w = text[max(0, m.start() - 80):m.end() + 80]
                    if TIER_CONTEXT.search(w) or LOYALTY_PATH.search(w):
                        found.append((t, re.sub(r"\s+", " ", w).strip()))
                        break
            # A LADDER, not a colour. One tier token is a word; two or more in
            # tier context is a programme structure.
            if len(found) >= 2:
                prog = _programme_name(text, raw)
                for t, w in found:
                    r = base_row(fac or {}, host, mrow, w, url)
                    r.update(
                        # KEYED ON (host, programme, tier) AND NOT ON THE URL.
                        # A tier ladder is a property of the PROGRAMME, and a
                        # site prints it on every rewards page it has. Keying
                        # on the URL wrote the same ladder 19 times for Seven
                        # Clans Red Lake, which would have read as 19 findings.
                        loyalty_id="SPL-" + digest(host, prog, t),
                        assertion_class="SELF_PUBLISHED_LOYALTY_STRUCTURE",
                        assertion_class_note=(
                            "deliberately OUTSIDE "
                            "cedar_domain.MeasurementType: a tier ladder is a "
                            "programme STRUCTURE, not a count of anything. "
                            "Tier ORDER is not asserted - the page's visual "
                            "order is not recoverable from extracted text, so "
                            "no rank is written."),
                        programme_name_as_published=prog,
                        tier_name=t,
                        tier_rank="",
                        tier_rank_basis=("NOT ASSERTED - rank is a visual "
                                         "property of the page, not a textual "
                                         "one"),
                        n_tiers_found_on_page=len(found),
                        attribution_basis=attrib,
                        confidence="C",
                        source_md5=md5)
                    loyalty.append(r)
                stats["loyalty_tier_rows"] += len(found)
                stats["loyalty_pages"] += 1

    # ---- dedupe on the deterministic key ----
    claims = _dedupe(claims, "claim_id")
    asserts = _dedupe(asserts, "assertion_id")
    loyalty = _dedupe(loyalty, "loyalty_id")

    # ---- A ROW WITH NO VERBATIM SENTENCE IS UNUSABLE. Refuse, don't downgrade.
    def has_quote(rows, field="source_quote"):
        keep, dropped = [], 0
        for r in rows:
            if (r.get(field) or "").strip():
                keep.append(r)
            else:
                dropped += 1
        return keep, dropped

    claims, d1 = has_quote(claims)
    asserts, d2 = has_quote(asserts)
    loyalty, d3 = has_quote(loyalty)
    stats["rows_refused_for_empty_verbatim_quote"] = d1 + d2 + d3

    # ---- no new facility id, asserted before write ----
    for r in claims + asserts + loyalty:
        assert (not r.get("facility_id")) or r["facility_id"] in valid_ids, (
            "facility id %s not in gaming_facilities.csv" % r.get("facility_id"))

    write_csv(OUT_CLAIMS, claims, CLAIM_FIELDS)
    write_csv(OUT_ASSERT, asserts, ASSERT_FIELDS)
    write_csv(OUT_LOYALTY, loyalty, LOYALTY_FIELDS)
    write_csv(OUT_REFUSED, refused, REFUSED_FIELDS)

    # ---- verify by RE-READING, not by trusting the run log (rule 4) ----
    back = {p: len(read_csv(p)) for p in
            (OUT_CLAIMS, OUT_ASSERT, OUT_LOYALTY, OUT_REFUSED)}

    summary = dict(
        script=SCRIPT, run_date=TODAY, network_requests=0,
        pages_in_manifest=len(by_file), pages_read=pages_read,
        hosts_read=len(hosts_seen),
        claims_rows=len(claims), assertion_rows=len(asserts),
        loyalty_rows=len(loyalty), refused_rows=len(refused),
        facilities_with_a_claim=len({r["facility_id"] for r in claims
                                     if r.get("facility_id")}),
        facilities_with_an_assertion=len({r["facility_id"] for r in asserts
                                          if r.get("facility_id")}),
        historical_guard_blocked=dict(fac_hist_blocked),
        rows_read_back_from_disk={os.path.basename(k): v
                                  for k, v in back.items()},
        measurement_types_created=[
            MT.SELF_PUBLISHED_MARKETING_CLAIM.value,
            MT.SELF_PUBLISHED_EMPLOYMENT_CLAIM.value],
        counters={k: v for k, v in sorted(stats.items())},
    )
    with open(OUT_LOG, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    print("\n  pages read           : %d on %d hosts" % (pages_read, len(hosts_seen)))
    print("  CLAIMS (measurement) : %d   (%d employment, %d capacity)"
          % (len(claims), stats["employment_claims"], stats["capacity_claims"]))
    print("  ASSERTIONS           : %d   (%d date, %d ownership, %d management,"
          " %d employer-standing)"
          % (len(asserts), stats["date_assertions"],
             stats["ownership_assertions"], stats["management_assertions"],
             stats["employer_standing_claims"]))
    print("  LOYALTY tier rows    : %d on %d pages"
          % (len(loyalty), stats["loyalty_pages"]))
    print("  REFUSED (with reason): %d" % len(refused))
    print("  historical guard blocked %d page(s)"
          % stats["pages_blocked_by_historical_guard"])
    print("\n  read back from disk:")
    for k, v in back.items():
        print("    %-70s %d" % (os.path.basename(k), v))
    print("\n  wrote %s" % os.path.relpath(OUT_LOG, ROOT))
    return summary


def _dedupe(rows, key):
    seen, out = set(), []
    for r in rows:
        k = r.get(key)
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


def _year_agree(fac, kind, asserted):
    if not fac or kind == "anniversary":
        return ""
    cur = (fac.get("open_date") or "")[:4]
    if not cur or not cur.isdigit():
        return "cedar_has_no_open_year"
    if kind not in ("opening", "in_operation_since"):
        return "not_comparable_this_subclass"
    return "AGREES" if cur == asserted else "DIFFERS_%s_vs_%s" % (cur, asserted)


def _owner_agree(owner, curated):
    """Never a match verdict - a REPORT of whether the two strings share a
    distinctive token. Cedar's curated file outranks this either way."""
    if not curated:
        return "cedar_has_no_curated_owner"
    stop = {"the", "of", "and", "tribe", "tribes", "tribal", "nation", "band",
            "pueblo", "community", "indians", "indian", "reservation",
            "rancheria", "village", "corporation", "confederated", "colony"}
    a = {w for w in re.findall(r"[a-z]+", owner.lower()) if w not in stop
         and len(w) > 3}
    b = {w for w in re.findall(r"[a-z]+", curated.lower()) if w not in stop
         and len(w) > 3}
    if not a or not b:
        return "no_distinctive_token_either_side"
    shared = a & b
    if shared:
        return "SHARES_TOKEN:" + "|".join(sorted(shared))
    # The stopword list eats every token of "the Confederated Tribes" against a
    # curated "Confederated Tribes of the Colville Reservation", which reports
    # nothing about two strings that plainly agree. Fall back to a PREFIX
    # report - still a report, still not a verdict.
    ao = re.sub(r"^the\s+", "", owner.strip().lower())
    cu = curated.strip().lower()
    if ao and (cu.startswith(ao) or ao.startswith(cu)):
        return "CURATED_NAME_IS_A_PREFIX_EXTENSION_OF_ASSERTED"
    return "NO_SHARED_DISTINCTIVE_TOKEN"


PROG_TOKEN = (r"(?:Rewards?(?:\s+Club)?|Players?(?:'|’)?s?\s+Club|"
              r"Advantage(?:\s+Club)?|Passport|Loyalty(?:\s+Program\w*)?|"
              r"Club\s+[A-Z][\w'’]*)")


def _programme_name(text, raw=b""):
    """The programme's own name, from the page's <title> where it has one.

    THE FIRST PASS READ THE NAV BAR. Extracting the longest capitalised run
    before the word "Rewards" off the body text produced
    `"Site Catering Careers Rewards Club"` and
    `"Bar Summer Sounds Wayfinder Rewards"` - the site's menu, swept up because
    every nav item is title-cased and adjacent. `<title>` is the one string on
    a page the operator wrote as a NAME, so it is tried first, split on its
    separators, and only the segment carrying a programme token is kept. The
    body fallback is capped at THREE words before the token for the same
    reason."""
    try:
        t = re.search(rb"<title[^>]*>(.{0,300}?)</title>", raw,
                      re.I | re.S)
        if t:
            title = re.sub(r"\s+", " ",
                           t.group(1).decode("utf-8", "replace")).strip()
            for seg in re.split(r"\s*[|–—•·]\s*|\s+-\s+",
                                title):
                seg = seg.strip()
                if re.search(PROG_TOKEN, seg) and len(seg.split()) <= 6:
                    return seg
    except Exception:
        pass
    m = re.search(r"([A-Z][\w'’]*(?:\s+[A-Z][\w'’]*){0,2}\s+" + PROG_TOKEN
                  + r")", text[:6000])
    if not m:
        return ""
    name = re.sub(r"\s+", " ", m.group(1)).strip()
    # A nav bar is a list of unrelated title-cased words. If the run before the
    # programme token contains a known menu word, keep only the token.
    NAV = re.compile(r"\b(Site|Home|Menu|Careers|Catering|Dining|Promotions|"
                     r"Locations|Events|Bar|Hotel|Sports?|Betting|Weekly|"
                     r"Promos|Book|Stay|Play|Eat|About|Contact|Search|"
                     r"English|Spanish|Convention|Facilities|Weddings|With)\b")
    if NAV.search(name):
        m2 = re.search(PROG_TOKEN, name)
        return m2.group(0) if m2 else ""
    return name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    run(limit=a.limit)


if __name__ == "__main__":
    main()
