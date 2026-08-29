#!/usr/bin/env python3
r"""
Cedar Press - 133: FERC regulatory advocacy (eLibrary docket record).

WHY FERC, AND WHY IT IS DIFFERENT FROM EVERY OTHER SOURCE HERE
--------------------------------------------------------------
FERC is quasi-judicial. Its ex parte rule (18 CFR 385.2201) makes an
off-the-record communication about a contested proceeding either PROHIBITED or
EXEMPT, and either way it must be **placed on the public record**. Almost no
other agency forces private contacts into a citable file. So a FERC docket
sheet is not a summary of a proceeding - it is a roster of everyone who spoke
to the agency about it, with a date and an accession number.

WHAT THIS BUILDS
----------------
    developer / licensee   ->   FERC docket   ->   every filer on that docket
                                              ->   the instrument each filed
                                              ->   the position stated IN the
                                                   document's own title

`ferc_docket_filings.csv` is the row-level asset: one row per document on a
tribal-relevant docket, carrying the filer organisation exactly as FERC
records it (`Affiliation_Organization`), the accession number, the filed date,
and the document description verbatim.

TAXONOMY - NOT NEGOTIABLE (spec, 2026-08-12)
--------------------------------------------
* An ex parte / off-the-record record  -> EventClass.ADVOCACY,
  channel REGULATORY_EX_PARTE.
* A comment, protest, intervention or answer filed into a docket -> ADVOCACY,
  channel ADMINISTRATIVE_COMMENT.
* A rehearing request or appeal        -> ADVOCACY, ADMINISTRATIVE_APPEAL.
* **Section 106 consultation inside a FERC docket is NOT advocacy.** It is
  GOVERNMENT_ENGAGEMENT / SECTION_106_CONSULTATION, it is built by
  `code/130_build_section_106_consultation.py`, and this script does not
  duplicate it - it CROSS-REFERENCES it by docket in `section_106_cross_ref`.
* `is_lobbying` is NARROWER than ADVOCACY. **Not one row here is lobbying.**
  An administrative comment is advocacy and is not lobbying, and saying
  otherwise would be wrong in a way that matters legally. The build asserts
  this against `cedar_domain` and refuses to run if the vocabulary disagrees.

THE POSITION RULE (hard, from the spec)
---------------------------------------
`administrative_record_position` is a SEPARATE observation from
`lobbying_position` and the two are never merged. An organisation can oppose a
project in the administrative record and never file an LDA report; it can lobby
Congress and never comment. They are different processes producing different
facts about different venues.

And the value is only ever read from the document's OWN words. A document
titled "Motion to Intervene in Opposition" states its position; a document
titled "Comments of X" does not, and gets `NOT_STATED_IN_DOCUMENT_TITLE`. We do
not characterise a party's stance - we quote the instrument. Every row carries
`administrative_record_position_quote` with the verbatim substring the value
was read from, or blank.

ABSENCE IS A PROPERTY OF THE DOCKET
-----------------------------------
A party that does not appear on a docket was not necessarily silent: it may
have filed under a name FERC affiliates differently, spoken through counsel,
or acted somewhere that is not FERC. `ferc_source_coverage.csv` records what
was swept, and every docket row carries `documents_retrieved` and the date
window actually queried, so a zero is readable as "swept and found none in
this window", never as "nobody spoke".

WHAT WAS REFUSED, AND WHY (recorded, not hidden)
------------------------------------------------
1. **eLibrary `Search/AdvancedSearch` is unusable anonymously.** It answers
   HTTP 200 `success:true` with `totalHits:0` for EVERY well-formed query -
   including a query by the exact `accessionNumber` of a document this same
   API returns from the docket-sheet endpoint seconds earlier. A search that
   cannot find a document it is simultaneously serving is broken, not empty
   (AGENTS.md: "a broken search is not evidence of absence"). Populating
   `categories`/`libraries` in the shapes the SPA uses makes it answer
   `success:false, "Unable to parse search request."` So docket discovery here
   is SEED-DRIVEN, and the coverage file says so.
2. **The Federal Register leg was DEFERRED, not skipped.** 641 FERC "Records
   Governing Off-the-Record Communications" notices exist in the FR API
   (measured 2026-08-12). `code/130_build_section_106_consultation.py` held an
   ACTIVE lock on www.federalregister.gov at the time of this run, and
   PULL_DISCIPLINE rule 1 is one poller per host, ever. The work is appended to
   that host's lock queue instead of run concurrently.

Reads   data/clean/federal_actions.csv                  (FERC docket seeds)
        data/clean/section_106_consultation_events.csv  (cross-reference seeds)
        data/spine/cedar_entity_spine.csv
Writes  data/clean/ferc_tribal_dockets.csv
        data/clean/ferc_docket_filings.csv
        data/clean/ferc_ex_parte_communications.csv
        data/clean/ferc_source_coverage.csv
        data/raw/advocacy/ferc/*.json

Writes  data/clean/ferc_ex_parte_parties.csv          (the FR leg)
        data/raw/advocacy/ferc/fr_off_the_record_notices/*.txt

RUN:  py -3 code/133_build_ferc_advocacy.py seeds
      py -3 code/133_build_ferc_advocacy.py fetch     # elibrary.ferc.gov
      py -3 code/133_build_ferc_advocacy.py fr        # www.federalregister.gov
      py -3 code/133_build_ferc_advocacy.py build
      py -3 code/133_build_ferc_advocacy.py all

  FERC_DEADLINE_MIN=180 raises the per-stage wall-clock budget from 75.
"""

import csv
import importlib.util
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import requests

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
SPINE_DIR = CEDAR / "data" / "spine"
RAW = CEDAR / "data" / "raw" / "advocacy" / "ferc"
LOGS = CEDAR / "logs"
TODAY = date.today().isoformat()

HOST = "elibrary.ferc.gov"
API = "https://elibrary.ferc.gov/eLibraryWebAPI/api"
SCRIPT = "code/133_build_ferc_advocacy.py"
# Wall clock for the fetch stage. Overridable so a resume run can be given a
# longer budget than the first pass got: FERC_DEADLINE_MIN=180.
DEADLINE_S = int(os.environ.get("FERC_DEADLINE_MIN", "75")) * 60
MIN_GAP = 1.2                 # seconds between requests to this host
MAX_DOCKETS = 400             # hard bound on the sweep

# A STALLED STREAM IS A THIRD FAILURE SHAPE, AND urllib CANNOT SEE IT.
#
# Measured 2026-08-12 on the first pass: two GetSingleDocketSheet requests sat
# MOTIONLESS for 45 and 35 minutes while a cheap probe of the SAME host answered
# HTTP 200 in 0.17s. urllib's single `timeout` is the gap between socket
# operations, so a connection that is open and silent never trips it, and the
# request ate two thirds of a 75-minute budget on its own.
#
# `requests` takes a (connect, read) PAIR. The read leg is the gap between
# bytes, so a motionless stream aborts in READ_TIMEOUT seconds instead of
# hanging until the run deadline. The three shapes are then distinguishable and
# get three different responses:
#
#   ConnectTimeout / instant disconnect (<1s)  edge block   -> exponential backoff
#   HTTP 429                                   throttle     -> honour Retry-After
#   ReadTimeout after >= READ_TIMEOUT          stalled      -> ABANDON, move on
#
# A stall is NOT backed off. Backing off a stall is what burned the first run:
# the host is answering other requests fine, so sleeping 30 minutes buys
# nothing. It is abandoned, recorded on the docket row, and the sweep continues.
CONNECT_TIMEOUT = 15
READ_TIMEOUT = 45
PER_DOCKET_BUDGET_S = 240
_SESSION = requests.Session()

csv.field_size_limit(min(sys.maxsize, 2147483647))

# ---------------------------------------------------------------------------
# THE ONE RESOLVER AND THE SHARED VOCABULARY. Nothing re-declared.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(CEDAR / "code"))
from cedar_domain import (AdvocacyChannel, EventClass, Tier,       # noqa: E402
                          may_promote_event_class)
import cedar_match_guard as guard_mod                              # noqa: E402
from cedar_keys import surrogate_id                                # noqa: E402

# ---------------------------------------------------------------------------
# THE PRIMARY KEY OF ferc_docket_filings.csv, AND WHAT IT IS MADE OF
#
# THIS IS THE ORIGINAL CLASS-7 DEFECT, and the one that named the class.
#
#     "ferc_filing_id": f"FERC-{d}-{sub}-{acc}-{abs(hash(aff)) % 10000:04d}"
#
# `hash()` on a string is randomised per process by PYTHONHASHSEED. MEASURED
# across the 2026-08-12 and 2026-08-26 builds: **4 of 2,534 documents shared
# between them kept their id.** Nothing joined on it, so nothing broke - which
# is exactly why it survived for two weeks. A database keyed on that column
# corrupts on the next rebuild, silently, and the corruption looks like new
# rows rather than like an error.
#
# It is now a deterministic blake2b digest of five columns eLibrary itself
# states. The first three are the workaround `START_HERE.md` already told
# readers to join on; `subdocket` was already inside the old id; and
# `document_description_verbatim` is what separates two filings of the same
# type on one accession.
#
# STATED, NOT HIDDEN: this key is NOT UNIQUE. 769 groups covering 1,758 rows
# collide - 989 excess rows. Every one of them is identical to its twin on
# EVERY OTHER COLUMN of the table up to case and whitespace: the same eLibrary
# document recorded twice. The process hash was MASKING that duplication
# behind 855 collisions of its own. So this column is now a stable CONTENT
# identity, and `ferc_docket_filings.csv` remains what
# `284_audit_nondeterministic_keys.py` already calls it - BLOCKED for a
# primary key until those duplicates are resolved. Do not make it a
# foreign-key target.
#
# The live file was migrated in place on 2026-08-26 by
# `327_migrate_class7_keys_to_digests.py`, which first proved by a full value
# scan of every clean and spine table that these ids appear in exactly ONE
# place: this column. THIS BUILD IS A FULL REBUILD and running it reverts
# `168_link_adjudication_hubs.py`'s in-place enrichment - see the ordering
# rule in AGENTS.md. The edit here is so that a future rebuild reproduces the
# migrated ids; it is not an instruction to run this file.
# ---------------------------------------------------------------------------
FERC_FILING_KEY_COLUMNS = ["docket_number", "subdocket", "accession_number",
                           "filer_organization_as_recorded",
                           "document_description_verbatim"]

#: `section_106_cross_ref` holds a `;`-joined list of consultation event ids
#: under a length cap. The cap must cut at a DELIMITER - see the call site.
#: 400 until 2026-08-26. Raised because 400 was an arbitrary tidiness cap that
#: was already DROPPING REAL REFERENCES - P-001 lost part of its list and kept
#: a half-id - and because a digest id is longer than the positional one it
#: replaced, so more cells would have reached it. The widest real cell is 477
#: characters. The cap stays only as a runaway guard; `_cap_list` is what makes
#: reaching it safe.
S106_XREF_MAX_CHARS = 2000
S106_XREF_SEP = ";"


def _cap_list(items, limit=S106_XREF_MAX_CHARS, sep=S106_XREF_SEP):
    """Join `items` under `limit` characters, dropping WHOLE items.

    A slice of a joined id list produces a half-id that looks like a
    reference and resolves to nothing. When items are dropped the cell says
    so, because a silent truncation is the same shape as the per-unit budget
    that truncates and marks COMPLETE.
    """
    items = [str(x) for x in items if x]
    if not items:
        return ""
    out, used = [], 0
    for x in items:
        add = len(x) + (len(sep) if out else 0)
        if used + add > limit:
            break
        out.append(x)
        used += add
    if len(out) < len(items):
        note = f"{sep}+{len(items) - len(out)}_MORE_NOT_LISTED"
        while out and used + len(note) > limit:
            used -= len(out[-1]) + (len(sep) if len(out) > 1 else 0)
            out.pop()
        return sep.join(out) + note
    return sep.join(out)

_spec = importlib.util.spec_from_file_location(
    "c96", CEDAR / "code" / "96_build_consultation_events.py")
c96 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(c96)

Resolver = c96.Resolver
read_csv = c96.read_csv
write_csv = c96.write_csv
claim_host = c96.claim_host
release_host = c96.release_host
norm = c96.norm

# The vocabulary must agree before a single byte is written.
assert AdvocacyChannel.REGULATORY_EX_PARTE.event_class is EventClass.ADVOCACY
assert AdvocacyChannel.ADMINISTRATIVE_COMMENT.event_class is EventClass.ADVOCACY
assert AdvocacyChannel.ADMINISTRATIVE_APPEAL.event_class is EventClass.ADVOCACY
assert AdvocacyChannel.REGULATORY_EX_PARTE.is_lobbying is False, \
    "cedar_domain calls an ex parte filing lobbying - refusing to build."
assert AdvocacyChannel.ADMINISTRATIVE_COMMENT.is_lobbying is False, \
    "cedar_domain calls an administrative comment lobbying - refusing to build."
assert AdvocacyChannel.SECTION_106_CONSULTATION.event_class is \
    EventClass.GOVERNMENT_ENGAGEMENT
assert may_promote_event_class(EventClass.ACCESS, EventClass.ADVOCACY) is False

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# WHERE THE DRAFT GUARD MAY FIRE, AND WHERE IT MUST NOT.
#
# `code/96_build_consultation_events.py::Resolver` is the project's GUARDED
# wrapper around `33::resolve_entity` - it already applies class, specificity,
# trap-token, state and head-rule guards internally and labels the tier it used.
# `cedar_match_guard` is a separate DRAFT written for the RAW containment tier
# and its own docstring says it is not wired in.
#
# Stacking it on the Resolver's strong tiers was tried and MEASURED here on
# 2026-08-12. It refused, among others:
#
#     Yurok Tribe                    -> Yurok            (fr_official_name)
#     Nez Perce Tribe                -> Nez Perce        (fr_official_name)
#     The Klamath Tribes             -> Klamath          (government_class_core)
#     Standing Rock Sioux Tribe      -> Standing Rock    (name_head)
#     Mississippi Band of Choctaw..  -> Mississippi Choctaw
#
# Every one is correct. VETO 2 fired because `tribe` is a folded token, but a
# record whose name IS the entity's Federal Register official name is the
# strongest evidence this project has. AGENTS.md, 2026-08-07: two builds
# reported a "resolve_entity defect" that was not one, and patching it would
# have broken a correct component. Test against the raw spine before blaming
# the matcher - which is what the measurement above is.
#
# So the draft guard is applied ONLY to the tier it was written for.
DRAFT_GUARD_APPLIES_TO = frozenset({
    "resolve_entity_containment", "resolve_entity_core",
    "resolve_entity_containment_guarded", "resolve_entity_core_guarded",
})

_CTX = ssl.create_default_context()
MANIFEST = []
_last_hit = [0.0]
_START = [time.time()]


# ===========================================================================
# HTTP - sequential, spaced, backed off, deadline-bounded.
# ===========================================================================

def _request(url, payload=None, timeout=None, tries=4):
    """Return (http_status, text).

    Status vocabulary, unchanged from the first pass:
      200/4xx  a fact about the OBJECT
      0        transport failure - stop-work, never "not published"
      -1       our own run deadline
      -2       STALLED STREAM - the request was abandoned, not refused. This is
               a fact about the REQUEST and says nothing about the docket.

    AGENTS.md, 2026-08-08: `head()` returning 0 for both a genuine 404 and a
    dropped connection let a caller read "not published" off a block. -2 exists
    for the same reason: a stall that reused 0 would be indistinguishable from
    a host refusal, and the two need opposite responses.
    """
    delay = 60.0
    to = timeout or (CONNECT_TIMEOUT, READ_TIMEOUT)
    for attempt in range(tries):
        if time.time() - _START[0] > DEADLINE_S:
            return -1, "RUN_DEADLINE"
        gap = MIN_GAP - (time.time() - _last_hit[0])
        if gap > 0:
            time.sleep(gap)
        _last_hit[0] = time.time()
        hdrs = {"User-Agent": UA, "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9", "Connection": "close",
                "Referer": "https://elibrary.ferc.gov/eLibrary/search"}
        if payload is not None:
            hdrs["Content-Type"] = "application/json"
        t0 = time.time()
        try:
            if payload is not None:
                r = _SESSION.post(url, json=payload, headers=hdrs, timeout=to)
            else:
                r = _SESSION.get(url, headers=hdrs, timeout=to)
            raw = r.content
            MANIFEST.append({"url": url, "http_status": r.status_code,
                             "bytes": len(raw), "fetched_date": TODAY})
            if r.status_code == 200:
                return 200, raw.decode("utf-8", "replace")
            if r.status_code in (403, 404):
                return r.status_code, ""       # a fact about the object
            if r.status_code == 429:
                ra = r.headers.get("Retry-After")
                time.sleep(float(ra) if ra and ra.isdigit() else delay)
            else:
                time.sleep(delay)
        except requests.exceptions.ReadTimeout:
            # STALLED. The host is answering other requests; this stream is
            # silent. Abandon it - do NOT back off, that is what cost the first
            # run 80 minutes of a 75-minute budget.
            elapsed = time.time() - t0
            print(f"    [stalled_stream] silent {elapsed:.0f}s - abandoned",
                  flush=True)
            MANIFEST.append({"url": url, "http_status": 0, "bytes": 0,
                             "fetched_date": TODAY})
            return -2, "STALLED_STREAM"
        except Exception as e:                          # transport
            elapsed = time.time() - t0
            shape = "edge_block" if elapsed < 1.0 else "slow_or_timeout"
            print(f"    [{shape}] {type(e).__name__} after {elapsed:.1f}s",
                  flush=True)
            MANIFEST.append({"url": url, "http_status": 0, "bytes": 0,
                             "fetched_date": TODAY})
            # PULL_DISCIPLINE: check the deadline BEFORE the sleep as well as
            # before the attempt, or a 30-minute backoff carries you straight
            # past it.
            if time.time() + delay - _START[0] > DEADLINE_S:
                return -1, "RUN_DEADLINE"
            time.sleep(delay)
        delay = min(delay * 2, 1800)
    return 0, ""


def save_manifest(name="_SOURCE_MANIFEST.csv"):
    # PER-HOST MANIFEST FILES. The eLibrary and Federal Register legs are
    # different hosts and may run at the same time; a single shared manifest
    # is a read-modify-write race in which the second writer silently discards
    # the first one's provenance rows.
    RAW.mkdir(parents=True, exist_ok=True)
    p = RAW / name
    old = read_csv(p)
    seen = {r["url"] for r in old}
    write_csv(p, old + [r for r in MANIFEST if r["url"] not in seen],
              ["url", "http_status", "bytes", "fetched_date"])


# ===========================================================================
# STAGE 1 - SEEDS. Which FERC dockets are tribal-relevant, and how we know.
# ===========================================================================

# A docket number as FERC writes it. P = hydropower licence, CP/PF = gas
# certificate and pre-filing, CD = dam safety, EL/ER/EC = electric, RP = gas
# rates, RM = rulemaking, IS/OR = oil.
DOCKET_RE = re.compile(
    r"\b((?:P|CP|PF|RP|ER|EL|CD|RM|AD|OR|IS|DI|EC|ES|QF|PL|IN|TX|TS)"
    r"\d{0,2}-\d{1,5})(?:-(\d{3}))?\b")
PROJECT_RE = re.compile(r"[Pp]roject\s+No\.?s?\.?\s*([\d,\s\-]{3,60})")

# Terms that make a FERC document tribal-relevant. Deliberately conservative:
# every one of these names a tribe, a tribal institution, or the statutory
# machinery of tribal consultation. Generic land words are NOT here - AGENTS.md
# already records `reservation` catching 8,000 unrelated FERC filings.
TRIBAL_TERMS = [
    "tribe", "tribes", "tribal", "indian", "native american", "thpo",
    "tribal historic preservation", "rancheria", "pueblo", "nsn.gov",
    "band of", "confederated", "shoshone", "paiute", "yurok", "karuk",
    "klamath tribes", "navajo", "hopi", "sioux", "chippewa", "ojibwe",
    "apache", "cherokee", "seminole", "nez perce", "umatilla", "yakama",
    "warm springs", "colville", "spokane tribe", "skokomish", "swinomish",
    "lummi", "makah", "quinault", "hoopa", "standing rock", "osage",
    "quechan", "cocopah", "chemehuevi", "southern ute", "ute indian",
    "wind river", "arapaho", "blackfeet", "kootenai", "salish",
    "penobscot", "passamaquoddy", "mohegan", "mashantucket", "oneida nation",
    "seneca nation", "mohawk", "akwesasne", "catawba", "lumbee", "choctaw",
    "chickasaw", "muscogee", "creek nation", "shawnee", "miccosukee",
    "coeur d'alene", "kalispel", "nooksack", "tulalip", "muckleshoot",
    "puyallup", "squaxin", "suquamish", "grand ronde", "siletz", "coquille",
    "cow creek", "burns paiute", "shoshone-bannock", "fort mojave",
    "colorado river indian", "gila river", "tohono o'odham", "san carlos",
    "white mountain", "jicarilla", "mescalero", "zuni", "acoma", "laguna",
    "taos", "santa clara", "cochiti", "isleta", "sandia", "jemez",
]
TRIBAL_RE = re.compile("|".join(re.escape(t) for t in TRIBAL_TERMS), re.I)


def _norm_docket(d, sub=None):
    d = re.sub(r"\s+", "", (d or "")).upper()
    if not d:
        return None, None
    return d, (sub or "000")


def _dockets_in(text):
    """Every FERC docket number in a string, as (docket, subdocket)."""
    out = set()
    if not text:
        return out
    for m in DOCKET_RE.finditer(text):
        d, s = _norm_docket(m.group(1), m.group(2))
        if d:
            out.add((d, s))
    for m in PROJECT_RE.finditer(text):
        for num in re.findall(r"\d{2,5}", m.group(1)):
            out.add(("P-" + num, "000"))
    return out


def stage_seeds():
    print("=== 133 stage SEEDS ===\n")
    RAW.mkdir(parents=True, exist_ok=True)
    seeds = {}          # (docket, sub) -> dict

    def add(d, s, why, quote, url, title):
        k = (d, s)
        r = seeds.setdefault(k, {
            "docket_number": d, "subdocket": s,
            "docket_prefix": re.match(r"^[A-Z]+", d).group(0),
            "discovery_sources": set(), "discovery_quotes": [],
            "seed_source_urls": set(), "seed_titles": set()})
        r["discovery_sources"].add(why)
        if quote:
            r["discovery_quotes"].append(quote[:300])
        if url:
            r["seed_source_urls"].add(url)
        if title:
            r["seed_titles"].add(title[:140])

    # --- seed 1: Federal Register FERC documents already on disk ------------
    fa = CLEAN / "federal_actions.csv"
    n_ferc = n_hit = 0
    with open(fa, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            if "federal-energy-regulatory-commission" not in \
                    (row.get("agency_slugs") or ""):
                continue
            n_ferc += 1
            blob = " ".join([row.get("title") or "", row.get("abstract") or "",
                             row.get("docket_ids") or "",
                             row.get("action") or ""])
            m = TRIBAL_RE.search(blob)
            if not m:
                continue
            n_hit += 1
            i = max(0, m.start() - 90)
            quote = re.sub(r"\s+", " ", blob[i:m.end() + 130]).strip()
            for d, s in _dockets_in(blob):
                add(d, s, "federal_register_ferc_notice", quote,
                    row.get("html_url") or row.get("source_url"),
                    row.get("title"))
    print(f"  federal_actions.csv: {n_ferc:,} FERC documents, "
          f"{n_hit:,} carry a tribal term")

    # --- seed 2: the Section 106 build, CROSS-REFERENCED not rebuilt --------
    n106 = 0
    for row in read_csv(CLEAN / "section_106_consultation_events.csv"):
        if "Energy Regulatory" not in (row.get("sub_agency") or "") \
                and "Energy Regulatory" not in (row.get("agency") or ""):
            continue
        n106 += 1
        blob = " ".join([row.get("project_or_docket_id") or "",
                         row.get("project_reference") or "",
                         row.get("undertaking_title") or "",
                         row.get("source_quote") or ""])
        for d, s in _dockets_in(blob):
            add(d, s, "section_106_cross_reference",
                (row.get("source_quote") or "")[:300],
                row.get("source_url"), row.get("undertaking_title"))
    print(f"  section_106_consultation_events.csv: {n106:,} FERC rows "
          f"(cross-referenced, NOT rebuilt)")

    # --- seed 3: the ex parte repository docket ----------------------------
    # FERC files every off-the-record communication record under RM98-1,
    # the docket of Order No. 607 which established the ex parte rules.
    add("RM98-1", "000", "ferc_ex_parte_repository_docket",
        "FERC files its Records Governing Off-the-Record Communications "
        "under Docket No. RM98-1-000.", "", "Records Governing "
        "Off-the-Record Communications")

    rows = []
    for k in sorted(seeds):
        r = seeds[k]
        rows.append({
            "docket_number": r["docket_number"], "subdocket": r["subdocket"],
            "docket_prefix": r["docket_prefix"],
            "discovery_source": ";".join(sorted(r["discovery_sources"])),
            "discovery_quote": r["discovery_quotes"][0]
            if r["discovery_quotes"] else "",
            "seed_source_url": sorted(r["seed_source_urls"])[0]
            if r["seed_source_urls"] else "",
            "seed_title": sorted(r["seed_titles"])[0]
            if r["seed_titles"] else "",
            "fetched_date": TODAY,
        })
    (RAW / "docket_seeds.json").write_text(
        json.dumps(rows, indent=1), encoding="utf-8")
    print(f"\n  {len(rows):,} distinct tribal-relevant FERC dockets seeded")
    print("  by prefix:", Counter(r["docket_prefix"] for r in rows).most_common())
    return rows


# ===========================================================================
# STAGE 2 - FETCH. One poller, one host, sequential, deadline-bounded.
# ===========================================================================

def stage_fetch():
    print("=== 133 stage FETCH ===\n")
    _START[0] = time.time()
    seeds = json.loads((RAW / "docket_seeds.json").read_text(encoding="utf-8"))
    if not claim_host(HOST, SCRIPT, f"FERC eLibrary docket sheets, "
                                    f"{len(seeds)} dockets, <= {MAX_DOCKETS}"):
        print("  deferring to the existing poller. Nothing fetched.")
        return

    sheets_dir = RAW / "docket_sheets"
    sheets_dir.mkdir(parents=True, exist_ok=True)
    state_p = RAW / "_fetch_state.json"
    state = json.loads(state_p.read_text(encoding="utf-8")) \
        if state_p.exists() else {"done": [], "refused": [], "applicants": {}}
    done = set(state["done"])

    # Checkpoint BEFORE the first request (PULL_DISCIPLINE rule 6).
    state_p.write_text(json.dumps(state, indent=1), encoding="utf-8")

    any_success = False
    refused = []
    # PRIORITY ORDER, because the wall-clock budget will not cover 307 dockets.
    #
    # Measured 2026-08-12: a docket sheet averages ~100 seconds against this
    # host once it returns real rows, so a 75-minute budget buys roughly 45
    # dockets, not 307. Alphabetical order would have spent the whole budget on
    # AD/CD/CP electric-rate dockets and never reached a single hydro
    # relicensing - which is where tribes actually file.
    #
    # So the queue is ordered by evidentiary value, and the file that is left
    # behind is left behind DELIBERATELY and recorded, not lost to sort order:
    #   1. RM98-1  - the docket FERC files every off-the-record communication in
    #   2. dockets the Section 106 build already found tribal consultation on
    #   3. P-  hydropower licensing and relicensing
    #   4. CP/PF - gas certificate, LNG and pipeline
    #   5. everything else
    def _priority(s):
        d = s["docket_number"]
        src = s.get("discovery_source", "")
        if d == "RM98-1":
            return (0, d)
        if "section_106_cross_reference" in src:
            return (1, d)
        if d.startswith("P-"):
            return (2, d)
        if d.startswith("CP") or d.startswith("PF"):
            return (3, d)
        return (4, d)

    todo = sorted([s for s in seeds
                   if f"{s['docket_number']}-{s['subdocket']}" not in done],
                  key=_priority)[:MAX_DOCKETS]
    print(f"  {len(todo):,} dockets to fetch "
          f"({len(done):,} already on disk)\n")

    for i, s in enumerate(todo, 1):
        if time.time() - _START[0] > DEADLINE_S:
            print("  RUN_DEADLINE reached - stopping cleanly.")
            break
        d, sub = s["docket_number"], s["subdocket"]
        key = f"{d}-{sub}"
        pages, total = [], None
        page = 1
        # PER-DOCKET BUDGET. Measured 2026-08-12: one docket sheet request sat
        # motionless for 45 minutes while a cheap probe of the SAME host
        # answered HTTP 200 in 0.17s. That is a stalled stream, not a block -
        # AGENTS.md already records the shape - and urllib's `timeout` is the
        # gap between socket operations, not a total. A budget is the only
        # thing that bounds it, and truncation stays VISIBLE because
        # `documents_retrieved` and `total_hits_reported_by_source` are both
        # published on every docket row.
        t_docket = time.time()
        # `pageNumber` IS ZERO-BASED, AND PAGE 1 SILENTLY DROPS THE FIRST PAGE.
        #
        # This is the single most dangerous defect found in this source, and it
        # looks exactly like a fact about the docket. Measured 2026-08-12 on
        # CD20-2-000 (4 documents) and P-12470-000 (45 documents):
        #
        #     numHits 100, pageNumber 1  ->  0 rows,  totalHits 4 / 45
        #     numHits 100, pageNumber 0  ->  4 rows,  45 rows
        #
        # The server offsets by numHits * pageNumber, so a caller starting at
        # page 1 - which every pagination API in this project starts at - loses
        # the first `numHits` records, and loses ALL of them whenever the
        # docket is smaller than one page. A first pass at pageNumber=1
        # produced **124 dockets that looked EMPTY and were not**, including
        # live hydro and pipeline proceedings. Published, that would have been
        # evidence that nobody filed anything.
        #
        # The step-down over page sizes below is retained as a belt-and-braces
        # check: if a first page still comes back empty against a nonzero
        # total, try a smaller page rather than record a zero.
        st = None
        got_200 = False
        stalls = 0
        for size in (100, 25, 10):
            pages, page = [], 0
            stalled_here = False
            while True:
                if time.time() - t_docket > PER_DOCKET_BUDGET_S:
                    refused.append({"docket": key, "http_status": 200,
                                    "reading": "per-docket time budget "
                                               "reached; row is truncated "
                                               "and says so"})
                    break
                st, txt = _request(
                    f"{API}/Docket/GetSingleDocketSheet",
                    {"dockets": d, "subdockets": sub,
                     "filed_date_beg": "01-01-1990",
                     "filed_date_end": "12-31-2026",
                     "complete_flag": "N", "numHits": size,
                     "pageNumber": page})
                if st == -1:
                    break
                if st == -2:
                    # STALLED, NOT REFUSED. The only retry that makes sense is
                    # a smaller page - a smaller response is a shorter stream.
                    # It is NOT backed off and it does NOT trip the stop-work
                    # rule, because the host is demonstrably serving others.
                    stalls += 1
                    stalled_here = True
                    break
                if st != 200:
                    refused.append({"docket": key, "http_status": st,
                                    "reading": "transport failure - stop-work"
                                    if st == 0 else "fact about the object"})
                    break
                try:
                    j = json.loads(txt)
                except Exception:
                    refused.append({"docket": key, "http_status": st,
                                    "reading": "200 with unparseable body"})
                    break
                any_success = True
                got_200 = True
                dl = j.get("DataList") or []
                total = ((j.get("Page") or {}).get("totalHits")) \
                    or total or 0
                pages.extend(dl)
                if not dl or len(pages) >= (total or 0) or page > 60:
                    break
                page += 1
            if pages:
                print(f"      pages fetched at numHits={size}: "
                      f"{len(pages)}/{total}", flush=True)
            if pages or st == -1:
                break
            if stalled_here:
                continue      # step down and try the smaller stream
            # step down only when the FIRST page came back empty against a
            # nonzero total - that is the silent-truncation signature.
            if not total:
                break

        # PULL_DISCIPLINE: stop on FIRST refusal when nothing has succeeded.
        # ONLY a transport 0 or an HTTP refusal counts. A stall does not - it
        # is a property of one request, and treating it as a host refusal is
        # what would abandon 265 dockets over one silent socket.
        if not any_success and any(r.get("http_status") == 0 for r in refused):
            print("  first object refused and nothing has landed - the HOST is "
                  "refusing, not this docket. Stopping.")
            break

        # A DOCKET WE NEVER GOT A 200 FOR IS NOT WRITTEN AND IS NOT MARKED DONE.
        #
        # Writing an empty sheet here would publish `documents_retrieved = 0`
        # for a docket nobody actually swept, and `done` would stop any resume
        # from ever retrying it. That is the AGENTS.md "dropped connection is
        # not a 404" failure with a file on disk to make it look authoritative.
        if not got_200:
            if st == -1:
                print(f"  [{i}/{len(todo)}] {key:16s} RUN_DEADLINE before this "
                      f"docket landed - left in the queue", flush=True)
                break
            refused.append({"docket": key, "http_status": -2,
                            "reading": f"STALLED_STREAM x{stalls} - the request "
                                       f"went silent for {READ_TIMEOUT}s at "
                                       f"every page size tried and was "
                                       f"abandoned. NOTHING WAS RETRIEVED: this "
                                       f"is a fact about the request, not about "
                                       f"the docket, and the docket stays in "
                                       f"the queue unfetched."})
            state["refused"] = refused
            state_p.write_text(json.dumps(state, indent=1), encoding="utf-8")
            print(f"  [{i}/{len(todo)}] {key:16s} STALLED - not written, "
                  f"left unfetched", flush=True)
            continue

        st2, txt2 = _request(f"{API}/Docket/getApplicantDetails/{d}")
        applicant = ""
        if st2 == 200:
            try:
                applicant = "; ".join(
                    re.sub(r"<[^>]+>", " ", x).strip()
                    for x in (json.loads(txt2).get("DataList") or []) if x)
                applicant = re.sub(r"\s+", " ", applicant).strip("; ")
            except Exception:
                applicant = ""
        state["applicants"][key] = applicant

        (sheets_dir / f"{key}.json").write_text(
            json.dumps({"docket": d, "subdocket": sub, "applicant": applicant,
                        "total_hits": total, "documents": pages,
                        "fetched_date": TODAY}, indent=1), encoding="utf-8")
        done.add(key)
        state["done"] = sorted(done)
        state["refused"] = refused
        state_p.write_text(json.dumps(state, indent=1), encoding="utf-8")
        print(f"  [{i}/{len(todo)}] {key:16s} {len(pages):5,}/{total or 0:,} docs  "
              f"applicant={applicant[:48]}", flush=True)

    save_manifest()
    release_host(HOST, SCRIPT,
                 f"docket sheets: {len(done)} dockets on disk, "
                 f"{len(refused)} refused")
    print(f"\n  downloaded_this_run={len(todo) and len(done)}  "
          f"refused_by_host={len(refused)}")


# ===========================================================================
# STAGE 2b - THE FEDERAL REGISTER LEG.
#
# WHY THIS EXISTS: eLibrary HAS THE INVENTORY AND CANNOT NAME THE PARTIES.
# ---------------------------------------------------------------------------
# `ferc_ex_parte_communications.csv` came out of eLibrary docket RM98-1-000
# with 704 rows and `communicating_parties_basis` saying, on every one of them,
# that the parties are not in that source. eLibrary publishes the NOTICE - a
# document description like "Public Notice re Records Governing Off-the-Record
# Communications under RM98-1." The names, the dockets each communication was
# about, and the prohibited/exempt determination are all INSIDE the notice
# text, which FERC prints in the Federal Register.
#
# THE JOIN, AND WHY IT IS EXACT
# -----------------------------
# Each FR notice signs off "Dated: <date>." That date is the date FERC issued
# the notice, and it is the eLibrary `filed_date` of the same notice. Verified
# on five notices spanning 2003-2026 before a line of this was written:
#
#     FR 2026-15543 "Dated: July 28, 2026"      -> eLibrary 20260728-3028
#     FR 2025-18976 "Dated: September 25, 2025" -> eLibrary filed 2025-09-25
#     FR 2016-25880 "Dated: October 18, 2016"   -> eLibrary filed 2016-10-18
#     FR 03-8094    "March 28, 2003."           -> eLibrary filed 2003-03-28
#
# So this leg does NOT create rows. It fills the field the eLibrary leg said it
# could not fill, on the rows that already exist, keyed by a date printed in
# both sources.
#
# THE COUNT 641 IS NOT 641 NOTICES
# --------------------------------
# The FR query is a TERM search - `conditions[term]="off-the-record
# communications"` - so it returns every FERC document containing the phrase.
# Measured: it includes Order No. 607 itself (the 1999 final rule, 117 KB), a
# 1994 marketing-affiliate rehearing order, Sunshine Act meeting notices, and
# the 2003 Policy Statement on Consultation With Indian Tribes. Reading 641 as
# "641 ex parte notices" would be the same error as reading a broken search's
# zero as absence, in the opposite direction.
#
# Documents are therefore typed from their BODY, not their title: a notice in
# this series says "This constitutes notice, in accordance with 18 CFR
# 385.2201" and carries a "Presenter or requester" table. Title matching alone
# would also have dropped the two 2001 notices the FR titled "Regulations
# Governing Off-the-ROAD Communications" - a typo in the source, and a real
# notice underneath it.
#
# WHERE THE PARTY ACTUALLY IS, WHEN THE PRESENTER IS "FERC STAFF"
# --------------------------------------------------------------
# A large share of modern rows print `FERC Staff.\1\` in the presenter column,
# and the footnote is where the outside party is named:
#
#     \1\ Memorandum dated 08/20/2025 with Texas Eastern Transmission, LP.
#     \3\ Letter dated 09/12/25 from Governor of Michigan Gretchen Whitmer.
#
# Both are published, verbatim and separately. The footnote is NOT parsed into
# a "real party" field - "with", "from" and "forwarding comments of" are three
# different relationships and picking one would be authoring a fact. The quote
# carries the relationship in FERC's own words.
# ===========================================================================

FR_HOST = "www.federalregister.gov"
FR_DOCS_API = "https://www.federalregister.gov/api/v1/documents.json"
FR_RAW = RAW / "fr_off_the_record_notices"
FR_UA = "CedarPress-research/1.0"
FR_MIN_GAP = 0.9
_fr_last = [0.0]

# The series' own statement of what it is. Read from the body, not the title.
# THE CITATION IN THIS SENTENCE IS MISPRINTED IN FOUR DIFFERENT WAYS.
# Measured across the 641 retrieved documents:
#
#     18 CFR 385.2201(h)   the correct form
#     18 CFR 385.220(h)    FR 01-303   - digit dropped
#     18 CFR 285.2201(h)   FR 99-30750 - part number wrong
#     18 CAR 385.2201(h)   FR 02-20289 - "CAR" for "CFR"
#     18 CFR 385 Sec.      FR 03-22111 - section spelled out
#
# Anchoring on the correct citation typed four real notices, carrying 27 named
# communications between them, as not being part of the series. A typo in the
# source is not a fact about the document's class - the same reasoning that
# keeps the two "Off-the-ROAD Communications" notices. The distinctive part of
# the sentence is its opening, so that is what is matched.
FR_NOTICE_BODY_RE = re.compile(
    r"constitutes\s+notice,?\s+in\s+accordance\s+with\s+18\s+C", re.I)
# The trailing period is not reliable: FR E4-1703 (2004) heads the column
# "Docket No" with no full stop, and requiring one dropped that notice's eight
# communications while the parser reported no table at all.
FR_TABLE_HDR_RE = re.compile(
    r"Docket\s+Nos?\.?(?=\s|$)", re.I)
# The date column has been headed at least five ways across the series:
# "File date", "Date filed", "Date received", a two-line "Date / received",
# and a two-line "Communication / date". Matching only the first two dropped
# whole years of tables silently - FR E6-11651 (2006) and FR 2012-4183 both
# reported a table and zero communications while printing four and sixteen.
# The header line must also carry "Docket No", so a bare \bdate\b is safe.
FR_DATECOL_RE = re.compile(
    r"File\s+date|Date\s+filed|Date\s+received|\breceived\b|\bdate\b", re.I)

# THE PRE-2002 NOTICES HAVE NO TABLE AT ALL - they run the three fields inline,
# comma-delimited, under a bare "Exempt" or "Prohibited" line:
#
#     Exempt
#         1. Project No. 1895-000, 10-30-01, Nicholas Jayjack.
#         2. Project No. 1494-232, 10-30-01, Mike Brady (Duck Creek
#         Homeowners).
#
# A fixed-width parser reports these notices as naming nobody, which is the
# same shape of false absence the zero-based pageNumber defect produced on the
# eLibrary side. They are parsed by their own branch and flagged as such.
FR_INLINE_ROW_RE = re.compile(
    r"^\s*(\d+)\.\s+(.+?),\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}),\s*(.+?)\s*$")
# And the 2000-era notices use a double-hyphen delimiter instead of commas:
#     1. CP00-114-000--9-5-00--Dorothy Watson
FR_INLINE_DASH_RE = re.compile(
    r"^\s*(\d+)\.\s+(.+?)--+\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s*--+\s*"
    r"(.+?)\s*$")
FR_SECTION_BARE_RE = re.compile(r"^\s*(Prohibited|Exempt)\s*:?\s*$", re.I)
FR_SECTION_RE = re.compile(r"^\s*(Prohibited|Exempt)\s*:?\s*$", re.I)
# The 2003-era table pads BOTH columns with leader dots -
#   `1. CP03-1-000...........  3-10-03..........  Jennifer Kerrigan.`
# - so the run after the file date is dots, not whitespace. Requiring
# whitespace there matched nothing, the loop then read the first row as "not
# part of the table", and the notice parsed as zero communications while
# reporting that it had found a table. Measured on FR 03-8094.
FR_ROW_RE = re.compile(
    r"^(\s*)(\d+)\.\s+(.*?)\s{2,}(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})[\s.]+"
    r"(.*?)\s*$")
FR_NONE_RE = re.compile(r"^\s*None[\s.]*$", re.I)
FR_FOOTNOTE_RE = re.compile(r"^\s*\\(\d+)\\\s*(.*)$")
FR_RULE_RE = re.compile(r"^\s*-{5,}\s*$")
FR_PAGE_RE = re.compile(r"^\s*\[\[Page\s+[^\]]+\]\]\s*$")
FR_END_RE = re.compile(r"^\s*(Dated:|\[FR Doc\.|BILLING CODE)", re.I)
# "Dated: July 28, 2026." is the usual form. Also measured in the series:
# "Dated: November 9. 2023." (a full stop where the comma belongs, FR
# 2023-25342) and "Issued: October 7, 2025." (FR 2025-21729). Each variant
# that is not matched costs a whole notice its join to eLibrary.
FR_DATED_RE = re.compile(
    r"(?:Dated|Issued):\s*([A-Z][a-z]+\.?\s+\d{1,2}[,.]\s+\d{4})", re.I)
# The pre-2004 notices print a bare issuance date on its own line instead.
FR_BARE_DATE_RE = re.compile(
    r"^\s*([A-Z][a-z]+\.?\s+\d{1,2},\s+\d{4})\.\s*$")
FR_MARKER_RE = re.compile(r"\\(\d+)\\")
_MONTHS = {m: i + 1 for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"])}


def _fr_get(url, params=None, tries=4):
    """Same status vocabulary as `_request`. Separate host, separate clock."""
    delay = 60.0
    for _ in range(tries):
        if time.time() - _START[0] > DEADLINE_S:
            return -1, "RUN_DEADLINE"
        gap = FR_MIN_GAP - (time.time() - _fr_last[0])
        if gap > 0:
            time.sleep(gap)
        _fr_last[0] = time.time()
        try:
            r = _SESSION.get(url, params=params, headers={"User-Agent": FR_UA},
                             timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
            MANIFEST.append({"url": r.url, "http_status": r.status_code,
                             "bytes": len(r.content), "fetched_date": TODAY})
            if r.status_code == 200:
                return 200, r.text
            if r.status_code in (403, 404):
                return r.status_code, ""
            if r.status_code == 429:
                ra = r.headers.get("Retry-After")
                time.sleep(float(ra) if ra and ra.isdigit() else delay)
            else:
                time.sleep(delay)
        except requests.exceptions.ReadTimeout:
            print("    [stalled_stream] FR request abandoned", flush=True)
            return -2, "STALLED_STREAM"
        except Exception as e:
            print(f"    [transport] {type(e).__name__}", flush=True)
            MANIFEST.append({"url": url, "http_status": 0, "bytes": 0,
                             "fetched_date": TODAY})
            if time.time() + delay - _START[0] > DEADLINE_S:
                return -1, "RUN_DEADLINE"
            time.sleep(delay)
        delay = min(delay * 2, 1800)
    return 0, ""


def _fr_plain(html_text):
    """FR 'raw text' is HTML-wrapped. Strip tags, keep the fixed-width table."""
    t = html_text
    t = re.sub(r"(?is)<script.*?</script>", " ", t)
    t = re.sub(r"(?is)<style.*?</style>", " ", t)
    t = re.sub(r"<[^>]+>", "", t)
    import html as _html
    t = _html.unescape(t)
    return t.replace("\xa0", " ").replace("\r\n", "\n")


def _fr_iso(s):
    m = re.match(r"([A-Za-z]+)\.?\s+(\d{1,2})[,.]\s+(\d{4})", (s or "").strip())
    if not m:
        return ""
    mo = _MONTHS.get(m.group(1).lower())
    if not mo and len(m.group(1)) >= 3:
        for name, num in _MONTHS.items():
            if name.startswith(m.group(1).lower()[:3]):
                mo = num
                break
    return f"{m.group(3)}-{mo:02d}-{int(m.group(2)):02d}" if mo else ""


def _fr_comm_date(s):
    """A table 'File date' as FERC prints it: 3-10-03, 07-24-2026, 1-29-09."""
    m = re.match(r"(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})", (s or "").strip())
    if not m:
        return ""
    mo, dy, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if yr < 100:
        yr += 1900 if yr >= 90 else 2000
    try:
        return f"{yr:04d}-{mo:02d}-{dy:02d}"
    except Exception:
        return ""


def _parse_fr_inline(lines, out):
    """The pre-2002 comma-delimited layout. Sets out['items'] in place."""
    section = ""
    items, cur = [], None
    for ln in lines:
        if FR_END_RE.match(ln):
            break
        sec = FR_SECTION_BARE_RE.match(ln)
        if sec:
            section = sec.group(1).upper()
            cur = None
            continue
        rm = FR_INLINE_DASH_RE.match(ln) or FR_INLINE_ROW_RE.match(ln)
        if rm:
            cur = {"item_number": rm.group(1),
                   "prohibited_or_exempt": section or "NOT_STATED_IN_NOTICE",
                   "dockets_as_printed": re.sub(
                       r"^(Docket|Project)\s+Nos?\.?\s*", "",
                       rm.group(2).strip(), flags=re.I).strip(". "),
                   "file_date_as_printed": rm.group(3),
                   "presenter_as_printed": rm.group(4).strip(),
                   "row_quote": re.sub(r"\s+", " ", ln.strip()),
                   "layout": "PRE_2002_INLINE_COMMA_DELIMITED"}
            items.append(cur)
            continue
        if cur is not None and ln.startswith(" ") and ln.strip() \
                and not FR_RULE_RE.match(ln):
            frag = ln.strip()
            cur["presenter_as_printed"] = (
                cur["presenter_as_printed"].rstrip() + " " + frag).strip()
            cur["row_quote"] = cur["row_quote"] + " " + frag
            continue
        cur = None
    for it in items:
        it["footnote_markers"] = ""
        it["footnote_text"] = ""
        it["presenter_as_printed"] = it["presenter_as_printed"].strip(" ,.")
        it["file_date_iso"] = _fr_comm_date(it["file_date_as_printed"])
    if items:
        out["items"] = items
        out["table_found"] = True
        out["layout"] = "PRE_2002_INLINE_COMMA_DELIMITED"


def parse_fr_notice(plain):
    """Return the notice's own statement of itself. No inference anywhere.

    `is_notice` is read from the body's 18 CFR 385.2201 sentence, never from
    the title. `items` are transcribed table rows. `footnotes` are transcribed
    verbatim and never resolved into a party.
    """
    out = {"is_notice": bool(FR_NOTICE_BODY_RE.search(plain)),
           "notice_date": "", "notice_date_quote": "",
           "table_found": False, "items": [], "footnotes": {},
           "sections_seen": [], "numbered_lines_in_text": 0}

    m = FR_DATED_RE.search(plain)
    if m:
        out["notice_date"] = _fr_iso(m.group(1))
        out["notice_date_quote"] = f"Dated: {m.group(1)}"
    lines = plain.split("\n")
    if not out["notice_date"]:
        # pre-2004 style: a bare issuance date line just under the title.
        for ln in lines[:80]:
            b = FR_BARE_DATE_RE.match(ln)
            if b and _fr_iso(b.group(1)):
                out["notice_date"] = _fr_iso(b.group(1))
                out["notice_date_quote"] = b.group(1).strip()
                break

    # THE ONE INVARIANT ACROSS EVERY LAYOUT IS THE PAIR "Docket No" +
    # "requester". The date column alone has been headed "File date", "Date
    # filed", "Date received", "Communication date" and a bare "filed" under a
    # "Date" on the line above - five spellings, and keying the header on that
    # column dropped tables in 2002, 2006 and 2012 while reporting success.
    hdr = -1
    for i, ln in enumerate(lines):
        if FR_TABLE_HDR_RE.search(ln) and re.search(
                r"requester|presenter", ln, re.I):
            hdr = i
            break
    if hdr < 0:
        for i, ln in enumerate(lines):
            if FR_TABLE_HDR_RE.search(ln) and FR_DATECOL_RE.search(ln):
                hdr = i
                break
            if FR_TABLE_HDR_RE.search(ln) and i + 1 < len(lines) \
                    and FR_DATECOL_RE.search(lines[i + 1]):
                hdr = i + 1
                break
    # A COUNT OF WHAT THE PARSER COULD SEE BUT DID NOT TRANSCRIBE.
    # Published beside the item count so a parse shortfall can never be read
    # as a notice that named nobody. Any line shaped like a numbered table row
    # anywhere in the notice counts here.
    out["numbered_lines_in_text"] = sum(
        1 for ln in lines if re.match(r"^\s*\d+\.\s+\S", ln))
    if hdr < 0:
        _parse_fr_inline(lines, out)
        if out["items"]:
            return out
        # A THIRD SHAPE: a fixed-width table WHOSE HEADER ROW IS BLANK.
        # FR 00-9171 and FR 01-22499 print the two horizontal rules with an
        # empty line between them where "Docket No. / Date filed / Presenter"
        # should be, then the section label and the rows. There is nothing to
        # key a header on, and both notices parsed as naming nobody while
        # printing sixteen and two named communications. The rows are still
        # unambiguous, so the scan is anchored on the FIRST ROW instead.
        first = next((i for i, ln in enumerate(lines)
                      if FR_ROW_RE.match(ln)), -1)
        if first < 0:
            return out
        start = max(0, first - 2)
        out["layout"] = "FIXED_WIDTH_TABLE_WITH_BLANK_HEADER_ROW"
    else:
        start = hdr + 1
    out["table_found"] = True

    # The 2003-era notices put the section word at the END of the paragraph
    # before the table ("...contact (202)502-8659.Exempt:"), not in the table.
    # Two shapes above the table: "...contact (202)502-8659.Exempt:" glued to
    # the end of the preceding paragraph (2003), and a bare centred "Exempt"
    # on its own line above the rule (2002, 2006). Both are the notice
    # stating which determination the table below carries.
    section = ""
    if hdr >= 0:
        for ln in lines[max(0, hdr - 6):hdr]:
            b = FR_SECTION_BARE_RE.match(ln)
            if b:
                section = b.group(1).capitalize()
        if not section:
            pm = re.findall(r"(Prohibited|Exempt)\s*:",
                            "\n".join(lines[max(0, hdr - 6):hdr]), re.I)
            if pm:
                section = pm[-1].capitalize()

    items, footnotes = [], {}
    cur, pres_col, in_notes = None, 0, False
    for ln in lines[start:]:
        if FR_RULE_RE.match(ln) or FR_PAGE_RE.match(ln) or not ln.strip():
            continue
        fn = FR_FOOTNOTE_RE.match(ln)
        if fn:
            in_notes = True
            cur = None
            footnotes[fn.group(1)] = fn.group(2).strip()
            last_fn = fn.group(1)
            continue
        if in_notes:
            if FR_END_RE.match(ln):
                break
            if ln.startswith(" ") and footnotes:
                footnotes[last_fn] = (footnotes[last_fn] + " "
                                      + ln.strip()).strip()
                continue
            break
        if FR_END_RE.match(ln):
            break
        sec = FR_SECTION_RE.match(ln)
        if sec:
            section = sec.group(1).capitalize()
            out["sections_seen"].append(section)
            cur = None
            continue
        if FR_NONE_RE.match(ln):
            cur = None
            continue
        rm = FR_ROW_RE.match(ln)
        if rm:
            pres_col = rm.start(5)
            cur = {"item_number": rm.group(2),
                   "prohibited_or_exempt": section.upper()
                   or "NOT_STATED_IN_NOTICE",
                   "dockets_as_printed": rm.group(3).strip().strip(". "),
                   "file_date_as_printed": rm.group(4),
                   "presenter_as_printed": rm.group(5).lstrip(". ").strip(),
                   "row_quote": re.sub(r"\s+", " ", ln.strip())}
            items.append(cur)
            continue
        if cur is not None and ln.startswith("  "):
            indent = len(ln) - len(ln.lstrip())
            frag = ln.strip()
            if indent >= max(4, pres_col - 6):
                cur["presenter_as_printed"] = (
                    cur["presenter_as_printed"] + " " + frag).strip()
            else:
                cur["dockets_as_printed"] = (
                    cur["dockets_as_printed"].rstrip(". ") + frag).strip(". ")
            cur["row_quote"] = (cur["row_quote"] + " "
                                + re.sub(r"\s+", " ", frag))
            continue
        # anything else ends the table
        if not ln.startswith(" "):
            break

    for it in items:
        marks = FR_MARKER_RE.findall(it["presenter_as_printed"])
        it["footnote_markers"] = ";".join(marks)
        it["footnote_text"] = " | ".join(
            footnotes.get(k, "") for k in marks if footnotes.get(k))
        it["presenter_as_printed"] = FR_MARKER_RE.sub(
            "", it["presenter_as_printed"]).strip().strip(".").strip()
        it["file_date_iso"] = _fr_comm_date(it["file_date_as_printed"])
    out["items"] = items
    out["footnotes"] = footnotes
    return out


def stage_fr():
    """Fetch and parse the FR notice series. Writes a cache; builds nothing.

    Kept separate from stage_build DELIBERATELY: the build regenerates all
    three CSVs from disk, so if this leg wrote into them directly the next
    build would silently wipe it. The parsed cache is an INPUT to the build,
    which makes the two stages order-independent.
    """
    print("=== 133 stage FR (Federal Register off-the-record notices) ===\n")
    _START[0] = time.time()
    FR_RAW.mkdir(parents=True, exist_ok=True)
    if not claim_host(FR_HOST, SCRIPT,
                      "FERC 'Records Governing Off-the-Record Communications' "
                      "notice series: index + full text, to name the "
                      "communicating parties on the 704 eLibrary rows"):
        print("  deferring to the existing poller. Nothing fetched.")
        return

    st, txt = _fr_get(FR_DOCS_API, {
        "conditions[agencies][]": "federal-energy-regulatory-commission",
        "conditions[term]": '"off-the-record communications"',
        "per_page": 1000, "order": "oldest",
        "fields[]": ["document_number", "title", "publication_date",
                     "raw_text_url", "html_url", "citation", "type"]})
    if st != 200:
        release_host(FR_HOST, SCRIPT, f"index request returned {st}")
        print(f"  index request returned {st} - nothing fetched.")
        return
    index = json.loads(txt)
    results = index.get("results") or []
    print(f"  FR term search count={index.get('count')} returned={len(results)}")

    parsed, n_new, n_cached, n_refused = {}, 0, 0, 0
    not_notice = []
    for i, d in enumerate(results, 1):
        if time.time() - _START[0] > DEADLINE_S:
            print("  RUN_DEADLINE reached - stopping cleanly.")
            break
        dn = d["document_number"]
        p = FR_RAW / f"{dn}.txt"
        if p.exists() and p.stat().st_size > 200:
            raw = p.read_text(encoding="utf-8", errors="replace")
            n_cached += 1
        else:
            sst, raw = _fr_get(d["raw_text_url"])
            if sst != 200:
                n_refused += 1
                print(f"  [{i}/{len(results)}] {dn} status={sst}", flush=True)
                continue
            p.write_text(raw, encoding="utf-8")
            n_new += 1
        rec = parse_fr_notice(_fr_plain(raw))
        rec.update({"document_number": dn, "title": d.get("title", ""),
                    "publication_date": d.get("publication_date", ""),
                    "citation": d.get("citation", ""),
                    "html_url": d.get("html_url", ""),
                    "raw_text_url": d.get("raw_text_url", ""),
                    "retrieved_at": TODAY})
        if not rec["is_notice"]:
            not_notice.append({"document_number": dn,
                               "publication_date": rec["publication_date"],
                               "title": rec["title"]})
        parsed[dn] = rec
        if i % 50 == 0:
            print(f"  [{i}/{len(results)}] fetched={n_new} cached={n_cached} "
                  f"refused={n_refused}", flush=True)
            (RAW / "_fr_parsed.json").write_text(
                json.dumps(parsed, indent=1), encoding="utf-8")

    (RAW / "_fr_parsed.json").write_text(json.dumps(parsed, indent=1),
                                         encoding="utf-8")
    notices = [r for r in parsed.values() if r["is_notice"]]
    with_table = [r for r in notices if r["table_found"]]
    n_items = sum(len(r["items"]) for r in notices)
    dated = [r for r in notices if r["notice_date"]]
    (RAW / "_fr_state.json").write_text(json.dumps({
        "checked_date": TODAY,
        "term_search_count": index.get("count"),
        "documents_retrieved": len(parsed),
        "documents_refused": n_refused,
        "is_notice_by_body_text": len(notices),
        "not_the_notice_series": len(not_notice),
        "not_the_notice_series_examples": not_notice[:20],
        "notices_with_a_party_table": len(with_table),
        "notices_carrying_a_notice_date": len(dated),
        "communication_items_transcribed": n_items,
    }, indent=1), encoding="utf-8")

    save_manifest("_SOURCE_MANIFEST_FEDERALREGISTER.csv")
    release_host(FR_HOST, SCRIPT,
                 f"FERC off-the-record notice series: {len(parsed)} FR "
                 f"documents retrieved, {len(notices)} are the notice series, "
                 f"{n_items} communications transcribed")
    print(f"\n  FR documents retrieved      {len(parsed):,}")
    print(f"  of those, the notice series {len(notices):,}")
    print(f"  NOT the notice series       {len(not_notice):,}")
    print(f"  notices with a party table  {len(with_table):,}")
    print(f"  communications transcribed  {n_items:,}")


# ===========================================================================
# STAGE 3 - BUILD.
# ===========================================================================

# --- the instrument the document IS, read from its own description ---------
# Order matters: the more specific instrument wins.
INSTRUMENTS = [
    ("REHEARING_OR_APPEAL", AdvocacyChannel.ADMINISTRATIVE_APPEAL,
     re.compile(r"\breheari?ng\b|request for rehearing|petition for review|"
                r"\bappeal(s|ed|ing)?\b", re.I)),
    ("PROTEST", AdvocacyChannel.ADMINISTRATIVE_COMMENT,
     re.compile(r"\bprotest(s|ing)?\b", re.I)),
    ("MOTION_TO_INTERVENE", AdvocacyChannel.ADMINISTRATIVE_COMMENT,
     re.compile(r"interven(e|tion|or)", re.I)),
    ("COMMENTS", AdvocacyChannel.ADMINISTRATIVE_COMMENT,
     re.compile(r"\bcomments?\b|\brecommendations?\b|\bterms and conditions\b",
                re.I)),
    ("ANSWER_OR_REPLY", AdvocacyChannel.ADMINISTRATIVE_COMMENT,
     re.compile(r"\banswer\b|\breply\b|\bresponse to\b", re.I)),
    ("SECTION_106_CONSULTATION_MATERIAL",
     AdvocacyChannel.SECTION_106_CONSULTATION,
     re.compile(r"section 106|36 cfr 800|national historic preservation|"
                r"programmatic agreement|historic properties management plan|"
                r"tribal historic preservation", re.I)),
]

# Position, read ONLY from the document's own words. Never inferred.
POSITION_PATTERNS = [
    ("OPPOSITION_STATED_IN_DOCUMENT",
     re.compile(r"in opposition|opposing|opposes|opposition to", re.I)),
    ("SUPPORT_STATED_IN_DOCUMENT",
     re.compile(r"in support of|supporting|supports the", re.I)),
    ("PROTEST_INSTRUMENT_FILED", re.compile(r"\bprotest(s|ing)?\b", re.I)),
]

# A PHRASE IN A TITLE IS NOT A STANCE UNTIL YOU KNOW WHOSE IT IS.
#
# MEASURED 2026-08-12 on the resume build, and every one of these was already
# written to ferc_docket_filings.csv:
#
#  1. NOUN PHRASE, NOT A STANCE. Six rows recorded the Confederated Tribes of
#     Warm Springs as SUPPORT because Portland General Electric filed a
#     "Supporting Technical Information Document" on P-2030. "Supporting" is
#     part of the document's NAME. Two more recorded Yurok as SUPPORT off
#     "supporting comments and supporting information".
#
#  2. SOMEONE ELSE'S STANCE. P-13889 recorded the Seneca Nation as SUPPORT
#     from: "...Answer the Purported 'Answer' Filed by FirstEnergy Generation
#     Corp. in Support of Its Petition..." - the support is FirstEnergy's, and
#     the Seneca document is an answer AGAINST it. The recorded value is not
#     merely unsupported, it is backwards.
#
#  3. THE STANCE OF THE DOCUMENT BEING ANSWERED. P-12710 recorded the
#     Passamaquoddy Tribe as OPPOSITION from "...in response to answer in
#     opposition to late motion to intervene of the Passamaquoddy..." - the
#     opposition is in the answer the tribe is responding TO.
#
# All three attribute a stance to a NAMED tribe that the document does not
# state, which is the single thing this build exists not to do. Three guards
# follow, and the count they refuse is reported.
POSITION_NOUN_PHRASE_RE = re.compile(
    r"support(?:ing)?\s+(?:technical|informational?|documents?|documentation|"
    r"statements?|data|materials?|evidence|exhibits?|comments?|testimony|"
    r"analys[ie]s|studies|study)", re.I)
# The stance belongs to the instrument being answered, not to this filer.
POSITION_BORROWED_RE = re.compile(
    r"\b(answer|answers|answered|response|responses|reply|replies|purported|"
    r"opposition)\b[\W\s]{0,12}$", re.I)
# Tokens that identify nobody. A filer name reduced to these is not evidence
# that the filer is the party named before the phrase.
POSITION_GENERIC_TOKENS = frozenset("""
tribe tribes tribal nation nations band bands indian indians pueblo community
communities council inc incorporated llc llp company co corp corporation the
of and for at in a an group association alliance coalition society club trust
foundation federation league district authority commission department bureau
office state states united us usa county city town village project committee
partnership limited holdings energy power water river lake valley mountain
north south east west upper lower new old fish game natural resources
""".split())


def _filer_named_before(filer, pre):
    """Does the filer's own name appear in the text before the phrase?"""
    toks = [t for t in re.split(r"[^A-Za-z0-9']+", filer or "")
            if len(t) >= 4 and t.lower() not in POSITION_GENERIC_TOKENS]
    low = pre.lower()
    return any(t.lower() in low for t in toks)

TRIBAL_FILER_RE = re.compile(
    r"\btribe\b|\btribes\b|\btribal\b|\bindian\b|\bnation\b|\bpueblo\b|"
    r"\brancheria\b|\bband\b|\bnative\b|\bcommunity of\b|\bcolony\b", re.I)

# Filer names that are governments or NGOs, not the project sponsor. Used only
# to TYPE a filer, never to judge its stance.
ORG_TYPE_PATTERNS = [
    ("FEDERAL_AGENCY", re.compile(
        r"\bU\.?S\.?\b|United States|Department of|Bureau of|Forest Service|"
        r"Fish and Wildlife|National Park|Army Corps|Environmental Protection "
        r"Agency|NOAA|Marine Fisheries", re.I)),
    ("STATE_AGENCY", re.compile(
        r"\bState of\b|Department of Natural Resources|Department of "
        r"Environmental|Water Resources Control|Public Utilit|Commission of|"
        r"State Historic Preservation", re.I)),
    ("LOCAL_GOVERNMENT", re.compile(
        r"\bCounty\b|\bCity of\b|\bTown of\b|\bBorough\b|\bMunicipal\b|"
        r"\bIrrigation District\b|\bWater District\b|\bConservation District\b",
        re.I)),
    ("NGO_OR_ASSOCIATION", re.compile(
        r"\bAssociation\b|\bAlliance\b|\bCoalition\b|\bSociety\b|\bClub\b|"
        r"\bTrust\b|\bFoundation\b|\bCouncil\b|\bFederation\b|\bLeague\b|"
        r"\bRiverkeeper\b|\bWatershed\b|\bLandowners?\b|\bTaxpayers?\b", re.I)),
    ("LAW_FIRM_OR_CONSULTANT", re.compile(
        r"\bLLP\b|\bPLLC\b|\bLaw Offices?\b|\bAttorneys?\b|\bConsult", re.I)),
]


EXPARTE_RE = re.compile(r"off[- ]the[- ]record|ex[- ]parte", re.I)

# A FILING **ABOUT** THE EX PARTE RULE IS NOT AN EX PARTE COMMUNICATION.
#
# Docket RM98-1 is where FERC MADE the off-the-record rule (Order No. 607) AND
# where it files the biweekly "Records Governing Off-the-Record
# Communications" notices. Both sit in the same docket, and both contain the
# words "off-the-record". Measured 2026-08-12: of 749 documents on RM98-1, 687
# contain the phrase - and the 1998 tranche is *comments on the proposed rule*
# from Wisconsin Public Power, the California Electricity Oversight Board and
# the Executive Office of the President.
#
# Typing those as ex parte communications would record the State of California
# as having made an off-the-record contact when it had filed a public comment
# on a rulemaking. That is a false attribution about a named party, which is
# the one thing this project must never produce.
# MEASURED 2026-08-12 (resume run): THIS GUARD LEAKED NINE ROWS.
#
# The first pass shipped nine RM98-1 documents as ex parte communications that
# are filings ABOUT the rule, exactly the failure the block above describes:
#
#   State of Louisiana Dept of Wildlife & Fisheries "responds to proposed
#     rulemaking on regulations governing off-the-record communications"
#   US Department of Interior "submits comments & recommendations re..."
#   Bonneville Power Administration's "comments to FERC's proposed
#     Regulations Governing Off-the-Record Communications"
#   Order 607; Final rule ... (x2)
#   Letters from the FERC Chair informing GAO, Rep. Hastert and A. Gore that
#     the rule had issued (x3)
#   Order Granting Rehearing For Further Consideration
#
# Each of those had recorded a NAMED party - a state agency, a federal
# department, a power marketing administration, the Commission's own Chair -
# as having made an off-the-record contact when the document is a public
# comment on a rulemaking, the rule itself, or a notification letter. The
# original patterns missed them because they anchor "comments" at the start of
# the string, and none of these start that way ("...responds to proposed
# rulemaking", "...submits comments & recommendations re", "X's comments to").
FILING_ON_THE_RULE_RE = re.compile(
    r"^\s*(?:comments?|notice of intervention|intervention|protest|answer|"
    r"reply|motion|petition|request for rehearing|brief|errata|erratum)\b|"
    r"\bcomments? of\b|\bexpresses support\b|\bre proposed\b|"
    r"\bnotice of proposed rulemaking\b|"
    r"\bresponds? to (?:the )?proposed rulemaking\b|"
    r"\bsubmits comments\b|\bcomments? (?:to|on|re) (?:the )?(?:ferc|"
    r"commission|proposed|regulations|regs)\b|'s comments\b|"
    r"\border (?:no\.?\s*)?#?\s*607\b|\bfinal rule\b|"
    r"\border granting rehearing\b|\brule issued\b|"
    r"\binforming of rule\b", re.I)


def classify_instrument(desc):
    d = desc or ""
    xp = EXPARTE_RE.search(d)
    if xp and not FILING_ON_THE_RULE_RE.search(d):
        i = max(0, xp.start() - 70)
        return ("EX_PARTE_RECORD_SERIES_NOTICE",
                AdvocacyChannel.REGULATORY_EX_PARTE,
                re.sub(r"\s+", " ", d[i:xp.end() + 90]).strip())
    for name, ch, rx in INSTRUMENTS:
        m = rx.search(d)
        if m:
            i = max(0, m.start() - 70)
            return name, ch, re.sub(r"\s+", " ", d[i:m.end() + 90]).strip()
    return "OTHER_DOCKET_DOCUMENT", None, ""


def classify_position(desc, filer="", counters=None):
    """A stance only where the document states it AND states it as the filer's.

    Returns (value, verbatim_quote). Every refusal is counted so the guards
    can be argued with rather than trusted.
    """
    d = desc or ""
    c = counters if counters is not None else Counter()
    for name, rx in POSITION_PATTERNS:
        for m in rx.finditer(d):
            if POSITION_NOUN_PHRASE_RE.match(d[m.start():m.start() + 60]):
                c["position_refused_noun_phrase_not_stance"] += 1
                continue
            pre = d[max(0, m.start() - 90):m.start()]
            if POSITION_BORROWED_RE.search(pre):
                c["position_refused_stance_of_the_answered_document"] += 1
                continue
            # The phrase must either open the title - in which case it
            # characterises this document - or follow the filer's own name.
            if len(pre.strip()) >= 25 and not _filer_named_before(filer, pre):
                c["position_refused_another_party_named_before_phrase"] += 1
                continue
            i = max(0, m.start() - 70)
            return name, re.sub(r"\s+", " ", d[i:m.end() + 90]).strip()
    return "NOT_STATED_IN_DOCUMENT_TITLE", ""


def org_type(name):
    for t, rx in ORG_TYPE_PATTERNS:
        if rx.search(name or ""):
            return t
    return "OTHER_ORGANIZATION"


def _iso(d):
    if not d or d.startswith("0001"):
        return ""
    return d[:10]


def apply_fr_to_exparte(exparte_rows, R, spine_rows):
    """Name the parties on rows that already exist. Creates no notice rows.

    Returns (party_rows, stats). Every eLibrary notice row matched to an FR
    notice by the date BOTH sources print keeps its identity; the field that
    said "NOT_IN_THIS_SOURCE" is replaced with the names and the basis says
    where they came from. Unmatched rows keep the original basis - an unnamed
    party here is an unmatched notice, never a notice with no parties.
    """
    stats = Counter()
    party_rows = []
    p = RAW / "_fr_parsed.json"
    if not p.exists():
        return party_rows, stats
    parsed = json.loads(p.read_text(encoding="utf-8"))
    notices = [r for r in parsed.values() if r.get("is_notice")]
    by_date = defaultdict(list)
    for r in notices:
        if r.get("notice_date"):
            by_date[r["notice_date"]].append(r)

    rows_by_date = defaultdict(list)
    for row in exparte_rows:
        if row.get("filed_date"):
            rows_by_date[row["filed_date"]].append(row)
    unmatched, undated = [], []
    for r in notices:
        if not r.get("notice_date"):
            undated.append({"document_number": r["document_number"],
                            "publication_date": r.get("publication_date", ""),
                            "communications": len(r.get("items") or [])})
        elif r["notice_date"] not in rows_by_date:
            unmatched.append({"document_number": r["document_number"],
                              "notice_date": r["notice_date"],
                              "publication_date": r.get("publication_date", ""),
                              "communications": len(r.get("items") or [])})

    for d, recs in sorted(by_date.items()):
        rows = rows_by_date.get(d) or []
        if not rows:
            # NOT A REASON TO DROP THE PARTIES. eLibrary's RM98-1 sheet was
            # retrieved in full (749 of 749), so a notice with no row on its
            # date is a notice FERC published in the Federal Register and did
            # not file into that docket. The parties are named in a primary
            # federal source and are published; only the LINK is absent, and
            # the row says so instead of the parties vanishing.
            stats["fr_notice_with_no_elibrary_row"] += 1
        # THE SERIES IS NOT ONE NOTICE PER DATE. FR published two notices dated
        # 2003-11-07 (E3-00283 and E3-00309) and two dated 2002-06-21. Taking
        # the first and dropping the rest would lose named communications
        # silently, so every notice on the date is carried and each party row
        # keeps its own FR document number.
        rec = recs[0]
        if len(recs) > 1:
            stats["dates_carrying_more_than_one_fr_notice"] += 1
        stats["fr_notices_matched_to_an_elibrary_row"] += len(recs)
        items = [it for r in recs for it in (r.get("items") or [])]
        parties = []
        for it in items:
            nm = (it.get("presenter_as_printed") or "").strip()
            if nm and nm not in parties:
                parties.append(nm)
        dockets = []
        for it in items:
            for dk in re.split(r"[,;]", it.get("dockets_as_printed") or ""):
                dk = dk.strip().strip(".")
                if dk and dk not in dockets:
                    dockets.append(dk)
        n_pro = sum(1 for it in items
                    if it.get("prohibited_or_exempt") == "PROHIBITED")
        n_exe = sum(1 for it in items
                    if it.get("prohibited_or_exempt") == "EXEMPT")

        for row in rows:
            row["fr_document_number"] = "; ".join(
                r["document_number"] for r in recs)
            row["fr_citation"] = "; ".join(
                r.get("citation", "") for r in recs)
            row["fr_publication_date"] = "; ".join(
                r.get("publication_date", "") for r in recs)
            row["fr_source_url"] = "; ".join(
                r.get("html_url", "") for r in recs)
            row["fr_notice_date_quote"] = rec.get("notice_date_quote", "")
            row["fr_join_basis"] = (
                "EXACT DATE PRINTED IN BOTH SOURCES: the Federal Register "
                "notice's own sign-off date equals the eLibrary filed_date of "
                "the notice document. No fuzzy or nearest-date matching.")
            row["off_the_record_communications_in_notice"] = str(len(items))
            row["prohibited_communications_in_notice"] = str(n_pro)
            row["exempt_communications_in_notice"] = str(n_exe)
            row["dockets_named_in_notice"] = "; ".join(dockets)[:900]
            if parties:
                row["communicating_parties_named_in_notice_text"] = \
                    "; ".join(parties)[:1500]
                row["communicating_parties_basis"] = (
                    "NAMED IN THE FEDERAL REGISTER NOTICE TEXT, 'Presenter or "
                    f"requester' column, FR {rec.get('citation','')} "
                    f"({rec.get('publication_date','')}), FR Doc "
                    f"{rec['document_number']}. Transcribed verbatim; "
                    "row-level detail with each party's docket, file date and "
                    "prohibited/exempt determination is in "
                    "ferc_ex_parte_parties.csv.")
                stats["elibrary_rows_that_gained_named_parties"] += 1
            else:
                row["communicating_parties_named_in_notice_text"] = ""
                row["communicating_parties_basis"] = (
                    "FEDERAL REGISTER NOTICE RETRIEVED AND PARSED, AND IT "
                    "NAMES NO PARTY. "
                    + ("The notice's table reads 'None' under both headings - "
                       "a biweekly notice is published whether or not any "
                       "communication was received."
                       if rec.get("table_found") else
                       "No 'Presenter or requester' table was found in this "
                       "notice's text; the shortfall is a parse limit, not a "
                       "statement that nobody communicated.")
                    + f" FR Doc {rec['document_number']}, "
                      f"{rec.get('citation','')}.")
                stats["fr_notice_names_no_party"] += 1

        anchor = rows[0] if rows else None
        for src, it in [(r, it) for r in recs for it in (r.get("items") or [])]:
            nm = (it.get("presenter_as_printed") or "").strip()
            tid = canon = method = ""
            if nm and TRIBAL_FILER_RE.search(nm):
                res = R.resolve(nm)
                if res and res[0]:
                    tid, canon, method = res[0], res[1], res[2]
                    if method in DRAFT_GUARD_APPLIES_TO:
                        ok, why = guard_mod.guard(
                            nm, spine_rows.get(tid, {}), method, {})
                        if not ok:
                            tid = canon = ""
                            method = f"refused_by_draft_guard:{why[:60]}"
                            stats["party_draft_guard_refused"] += 1
            if tid:
                stats["party_rows_resolved_to_a_native_entity"] += 1
            dks = [x.strip().strip(".") for x in
                   re.split(r"[,;]", it.get("dockets_as_printed") or "")
                   if x.strip().strip(".")]
            party_rows.append({
                "ferc_ex_parte_party_id":
                    f"FERCXPP-{src['document_number']}-"
                    f"{it.get('item_number','0')}-"
                    f"{(it.get('prohibited_or_exempt') or 'NS')[:3]}",
                "linked_ferc_ex_parte_id":
                    anchor["ferc_ex_parte_id"] if anchor else "",
                "linked_accession_number":
                    anchor["accession_number"] if anchor else "",
                "elibrary_link_basis":
                    "LINKED to the eLibrary RM98-1 notice document filed on "
                    "the same date the notice prints as its own."
                    if anchor else
                    "NO eLIBRARY NOTICE ROW ON THIS DATE. eLibrary docket "
                    "RM98-1-000 was retrieved complete (749 of 749 documents "
                    "reported by the source), so this is a notice FERC "
                    "published in the Federal Register without a corresponding "
                    "RM98-1 docket entry - not a document this sweep missed. "
                    "The communication and its named party are published; "
                    "only the eLibrary cross-reference is unavailable.",
                "notice_date": src["notice_date"],
                "fr_document_number": src["document_number"],
                "fr_citation": src.get("citation", ""),
                "fr_publication_date": src.get("publication_date", ""),
                "item_number": it.get("item_number", ""),
                "prohibited_or_exempt": it.get("prohibited_or_exempt", ""),
                "docket_numbers_as_printed": it.get("dockets_as_printed", ""),
                "primary_docket_number": dks[0] if dks else "",
                "communication_file_date": it.get("file_date_iso", ""),
                "communication_file_date_as_printed":
                    it.get("file_date_as_printed", ""),
                "presenter_or_requester_as_printed": nm,
                "presenter_or_requester_type": org_type(nm) if nm
                                               else "NOT_NAMED_IN_RECORD",
                # THE FEDERAL REGISTER NAMES PRIVATE INDIVIDUALS HERE, AND
                # CEDAR PRESS DOES NOT PUBLISH DATASETS ABOUT PRIVATE
                # INDIVIDUALS. The IBIA/IBLA build blanked 10,077 natural
                # persons for exactly this reason. The difference is that FERC
                # does not redact - the presenter column prints "Todd Mattson"
                # beside "U.S. Department of Transportation" - so the name is
                # kept, because it is the record and it is what makes the row
                # verifiable, and the rows that match no organisation pattern
                # carry this caution instead of a guess about who is a person.
                "natural_person_caution":
                    ("MAY BE A NATURAL PERSON. This presenter matched none of "
                     "the organisation patterns (agency, state, local "
                     "government, association, law firm). FERC publishes the "
                     "name; Cedar Press does not publish datasets about "
                     "private individuals, so this row is retained for "
                     "verification and must be filtered or aggregated before "
                     "any public release. No inference is recorded here about "
                     "whether the presenter IS an individual."
                     if nm and org_type(nm) == "OTHER_ORGANIZATION" else ""),
                "footnote_markers": it.get("footnote_markers", ""),
                "footnote_text_verbatim": it.get("footnote_text", ""),
                "footnote_reading":
                    ("THE PRESENTER COLUMN NAMES FERC'S OWN STAFF AND THE "
                     "FOOTNOTE NAMES THE OUTSIDE PARTY. The footnote is "
                     "published verbatim and is NOT parsed into a party field: "
                     "'with X', 'from X' and 'forwarding comments of X' are "
                     "three different relationships and choosing one would be "
                     "authoring a fact FERC did not state."
                     if re.search(r"ferc staff", nm, re.I)
                     and it.get("footnote_text") else ""),
                "event_class": EventClass.ADVOCACY.value,
                "channel": AdvocacyChannel.REGULATORY_EX_PARTE.value,
                "is_lobbying": "0",
                "resolved_native_entity_id": tid,
                "resolved_native_entity_name": canon,
                "resolution_method": method,
                "position_relative_to_native_interest": "",
                "position_basis":
                    "NOT_STATED_IN_SOURCE - an off-the-record notice records "
                    "that a named party communicated about a named docket on a "
                    "named date. It states no stance, and energy dockets are "
                    "precisely where coalition lines cross: an environmental "
                    "group may oppose a project a tribe sponsors, and two "
                    "tribes may sit on opposite sides of one docket. A "
                    "position is a property of an OBSERVATION and requires "
                    "organisation + matter + native entity together "
                    "(cedar_domain.position_is_addressable); this source "
                    "supplies no stance leg.",
                "table_row_quote": (it.get("row_quote") or "")[:400],
                "rule_basis": "18 CFR 385.2201 - prohibited and exempt "
                              "off-the-record communications are placed in the "
                              "public file and noticed in the Federal Register",
                "source_url": src.get("html_url", ""),
                "raw_text_url": src.get("raw_text_url", ""),
                "retrieved_at": src.get("retrieved_at", TODAY),
                "confidence_tier": Tier.A.value if tid else Tier.B.value,
                "built_date": TODAY, "built_by_script": SCRIPT,
            })
        stats["communication_items"] += len(items)

    (RAW / "_fr_match_state.json").write_text(json.dumps({
        "checked_date": TODAY,
        "fr_notices_with_a_notice_date": len(by_date),
        "elibrary_rows_total": len(exparte_rows),
        "elibrary_rows_that_gained_named_parties":
            stats["elibrary_rows_that_gained_named_parties"],
        "party_rows": len(party_rows),
        "fr_notices_with_no_elibrary_row": len(unmatched),
        "fr_notices_with_no_elibrary_row_communications":
            sum(x["communications"] for x in unmatched),
        "fr_notices_with_no_parsable_notice_date": len(undated),
        "unmatched_examples": unmatched[:25],
        "undated_examples": undated[:10],
    }, indent=1), encoding="utf-8")

    write_csv(CLEAN / "ferc_ex_parte_parties.csv", party_rows, [
        "ferc_ex_parte_party_id", "linked_ferc_ex_parte_id",
        "linked_accession_number", "elibrary_link_basis",
        "notice_date", "fr_document_number",
        "fr_citation", "fr_publication_date", "item_number",
        "prohibited_or_exempt", "docket_numbers_as_printed",
        "primary_docket_number", "communication_file_date",
        "communication_file_date_as_printed",
        "presenter_or_requester_as_printed", "presenter_or_requester_type",
        "natural_person_caution", "footnote_markers", "footnote_text_verbatim", "footnote_reading",
        "event_class", "channel", "is_lobbying", "resolved_native_entity_id",
        "resolved_native_entity_name", "resolution_method",
        "position_relative_to_native_interest", "position_basis",
        "table_row_quote", "rule_basis", "source_url", "raw_text_url",
        "retrieved_at", "confidence_tier", "built_date", "built_by_script"])
    return party_rows, stats


def stage_build():
    print("=== 133 stage BUILD ===\n")
    seeds = {(s["docket_number"], s["subdocket"]): s
             for s in json.loads(
                 (RAW / "docket_seeds.json").read_text(encoding="utf-8"))}
    sheets_dir = RAW / "docket_sheets"
    files = sorted(sheets_dir.glob("*.json")) if sheets_dir.exists() else []
    print(f"  docket sheets on disk: {len(files):,}")

    spine = read_csv(SPINE_DIR / "cedar_entity_spine.csv")
    R = Resolver(spine)
    spine_rows = {r["tribe_id"]: r for r in spine}
    print(f"  spine: {len(spine):,} entities\n")

    # Section 106 cross-reference index, by docket. NOT rebuilt here.
    s106 = defaultdict(set)
    for row in read_csv(CLEAN / "section_106_consultation_events.csv"):
        blob = " ".join([row.get("project_or_docket_id") or "",
                         row.get("project_reference") or ""])
        for d, sub in _dockets_in(blob):
            s106[(d, sub)].add(row.get("consultation_event_id") or "")

    docket_rows, filing_rows, exparte_rows = [], [], []
    st = Counter()
    tribes_seen, applicants_seen, opposing = set(), set(), set()

    for p in files:
        try:
            j = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            # A sheet being written by a concurrent fetch is half a file, not
            # an empty docket. Skipped and COUNTED, never read as zero.
            st[f"docket_sheet_unreadable:{type(e).__name__}"] += 1
            print(f"  [skip] {p.name} unreadable ({type(e).__name__}) - "
                  f"counted, not treated as an empty docket", flush=True)
            continue
        d, sub = j["docket"], j["subdocket"]
        seed = seeds.get((d, sub), {})
        docs = j.get("documents") or []
        n_tribal = n_exparte = n_comment = 0

        for entry in docs:
            for doc in (entry.get("DocumentsItem") or []):
                st["documents_seen"] += 1
                desc = (doc.get("doc_desc") or "").strip()
                affs = [a.strip() for a in
                        (doc.get("Affiliation_Organization") or []) if a
                        and a.strip()]
                if not affs:
                    affs = [""]
                inst, chan, inst_quote = classify_instrument(desc)
                acc = doc.get("accession_no") or ""
                filed = _iso(doc.get("filed_date") or "")
                issued = _iso(doc.get("issued_date") or "")
                cat = doc.get("category") or ""
                doc_url = (f"https://elibrary.ferc.gov/eLibrary/filelist?"
                           f"accession_number={acc}") if acc else \
                          f"https://elibrary.ferc.gov/eLibrary/docketsheet"

                if inst == "EX_PARTE_RECORD_SERIES_NOTICE":
                    n_exparte += 1
                if chan is AdvocacyChannel.ADMINISTRATIVE_COMMENT:
                    n_comment += 1

                for aff in affs:
                    st["filer_rows"] += 1
                    # POSITION IS PER FILER, NOT PER DOCUMENT. A docket sheet
                    # entry can carry several affiliations; "in support of"
                    # somewhere in the title is not every one of their stances.
                    pos, pos_quote = classify_position(desc, aff, st)
                    tid = canon = method = ""
                    if aff and TRIBAL_FILER_RE.search(aff):
                        res = R.resolve(aff)
                        if res and res[0]:
                            tid, canon, method = res[0], res[1], res[2]
                            if method in DRAFT_GUARD_APPLIES_TO:
                                ok, why = guard_mod.guard(
                                    aff, spine_rows.get(tid, {}), method, {})
                                if not ok:
                                    st["draft_guard_refused"] += 1
                                    tid = canon = ""
                                    method = f"refused_by_draft_guard:{why[:60]}"
                        elif res:
                            st[f"unresolved:{(res[3] or 'no_reason').split(':')[0]}"] += 1
                    if tid:
                        tribes_seen.add(tid)
                        n_tribal += 1
                        st["tribal_filer_rows"] += 1

                    # An ex parte record and a Section 106 document are
                    # different classes and must never share a channel.
                    # `is_lobbying` IS 0 ON EVERY ROW, INCLUDING UNTYPED
                    # ONES. Nothing filed into a FERC docket is a lobbying
                    # disclosure under the LDA; leaving it blank where the
                    # instrument did not classify would read as "unknown"
                    # about a question that has a known answer.
                    lob = "0"
                    if chan is None:
                        ec = ""
                        chan_v = ""
                    else:
                        ec = chan.event_class.value
                        chan_v = chan.value
                        assert chan.is_lobbying is False

                    otype = org_type(aff) if aff else "NOT_NAMED_IN_RECORD"
                    if (pos == "OPPOSITION_STATED_IN_DOCUMENT"
                            and aff and not tid):
                        opposing.add(aff)

                    filing = {
                        # set below, from THIS row's own stated columns -
                        # see FERC_FILING_KEY_COLUMNS at the top of the file.
                        "ferc_filing_id": "",
                        "docket_number": d, "subdocket": sub,
                        "accession_number": acc,
                        "filed_date": filed, "issued_date": issued,
                        "category": cat,
                        "instrument_type": inst,
                        "instrument_quote": inst_quote,
                        "event_class": ec, "channel": chan_v,
                        "is_lobbying": lob,
                        "filer_organization_as_recorded": aff,
                        "filer_organization_type": otype,
                        "filer_is_tribal_entity": "1" if tid else "0",
                        "resolved_native_entity_id": tid,
                        "resolved_native_entity_name": canon,
                        "resolution_method": method,
                        "administrative_record_position": pos,
                        "administrative_record_position_quote": pos_quote,
                        "lobbying_position": "",
                        "lobbying_position_basis":
                            "NOT_OBSERVED_IN_THIS_SOURCE - the administrative "
                            "record and the LDA record are separate "
                            "observations and are never merged",
                        "document_description_verbatim": desc[:600],
                        "source_url": doc_url,
                        "api_endpoint": f"{API}/Docket/GetSingleDocketSheet",
                        "fetched_date": j.get("fetched_date") or TODAY,
                        "confidence_tier": (Tier.A.value if tid else
                                            Tier.C.value),
                        "built_date": TODAY, "built_by_script": SCRIPT,
                    }
                    filing["ferc_filing_id"] = surrogate_id(
                        "FERCFIL", filing, FERC_FILING_KEY_COLUMNS)
                    filing_rows.append(filing)

                    if inst == "EX_PARTE_RECORD_SERIES_NOTICE":
                        exparte_rows.append({
                            "ferc_ex_parte_id":
                                f"FERCXP-{d}-{sub}-{acc}",
                            "docket_number": d, "subdocket": sub,
                            "accession_number": acc,
                            "filed_date": filed, "issued_date": issued,
                            "event_class": EventClass.ADVOCACY.value,
                            "channel":
                                AdvocacyChannel.REGULATORY_EX_PARTE.value,
                            "is_lobbying": "0",
                            "filed_or_issued_by_as_recorded": aff,
                            "filed_or_issued_by_type": otype,
                            "communicating_parties_named_in_notice_text": "",
                            "communicating_parties_basis":
                                "NOT_IN_THIS_SOURCE - eLibrary publishes the "
                                "NOTICE; the parties, their dockets and the "
                                "prohibited/exempt determination are inside "
                                "the notice text, which FERC also prints in "
                                "the Federal Register (641 notices, deferred "
                                "to the federalregister.gov lock holder).",
                            "resolved_native_entity_id": tid,
                            "resolved_native_entity_name": canon,
                            "ex_parte_quote": inst_quote,
                            "document_description_verbatim": desc[:600],
                            "rule_basis":
                                "18 CFR 385.2201 - off-the-record "
                                "communications are placed in the public file",
                            "source_url": doc_url,
                            "fetched_date": j.get("fetched_date") or TODAY,
                            "confidence_tier": Tier.A.value if tid
                                               else Tier.C.value,
                            "built_date": TODAY, "built_by_script": SCRIPT,
                        })

        app = (j.get("applicant") or "").strip()
        if app:
            applicants_seen.add(app)
        docket_rows.append({
            "docket_number": d, "subdocket": sub,
            "docket_prefix": seed.get("docket_prefix",
                                      re.match(r"^[A-Z]+", d).group(0)),
            "docket_program": DOCKET_PROGRAM.get(
                re.match(r"^[A-Z]+", d).group(0), "other FERC proceeding"),
            "applicant_or_licensee_as_recorded": app,
            "documents_retrieved": sum(
                len(e.get("DocumentsItem") or []) for e in docs),
            "total_hits_reported_by_source": j.get("total_hits") or 0,
            "date_window_queried": "1990-01-01..2026-12-31",
            "tribal_filer_documents": n_tribal,
            "ex_parte_documents": n_exparte,
            "comment_or_protest_documents": n_comment,
            # A LENGTH CAP ON A DELIMITED LIST MUST CUT AT A DELIMITER.
            # This was `";".join(...)[:400]`, which sliced mid-id: docket
            # P-001 carries a cross-reference reading `S1` - half of an id,
            # pointing at nothing, and indistinguishable from a real
            # reference to a reader. Found 2026-08-26 while migrating
            # `consultation_event_id` to a digest (327), which is longer than
            # the old positional id and so made more cells reach the cap.
            # `_cap_list` drops whole ids and says how many it dropped.
            "section_106_cross_ref": _cap_list(
                sorted(x for x in s106.get((d, sub), set()) if x)),
            "discovery_source": seed.get("discovery_source", ""),
            "discovery_quote": seed.get("discovery_quote", ""),
            "seed_source_url": seed.get("seed_source_url", ""),
            "source_url": "https://elibrary.ferc.gov/eLibrary/docketsheet",
            "fetched_date": j.get("fetched_date") or TODAY,
            "confidence_tier": Tier.A.value,
            "built_date": TODAY, "built_by_script": SCRIPT,
        })

    write_csv(CLEAN / "ferc_tribal_dockets.csv", docket_rows, [
        "docket_number", "subdocket", "docket_prefix", "docket_program",
        "applicant_or_licensee_as_recorded", "documents_retrieved",
        "total_hits_reported_by_source", "date_window_queried",
        "tribal_filer_documents", "ex_parte_documents",
        "comment_or_protest_documents", "section_106_cross_ref",
        "discovery_source", "discovery_quote", "seed_source_url",
        "source_url", "fetched_date", "confidence_tier", "built_date",
        "built_by_script"])
    write_csv(CLEAN / "ferc_docket_filings.csv", filing_rows, [
        "ferc_filing_id", "docket_number", "subdocket", "accession_number",
        "filed_date", "issued_date", "category", "instrument_type",
        "instrument_quote", "event_class", "channel", "is_lobbying",
        "filer_organization_as_recorded", "filer_organization_type",
        "filer_is_tribal_entity", "resolved_native_entity_id",
        "resolved_native_entity_name", "resolution_method",
        "administrative_record_position",
        "administrative_record_position_quote", "lobbying_position",
        "lobbying_position_basis", "document_description_verbatim",
        "source_url", "api_endpoint", "fetched_date", "confidence_tier",
        "built_date", "built_by_script"])
    # THE FEDERAL REGISTER LEG NAMES THE PARTIES ON THE ROWS THAT EXIST.
    # It runs here, before the write, so a rebuild can never wipe it and so
    # the two stages are order-independent.
    party_rows, fr_stats = apply_fr_to_exparte(exparte_rows, R, spine_rows)

    write_csv(CLEAN / "ferc_ex_parte_communications.csv", exparte_rows, [
        "ferc_ex_parte_id", "docket_number", "subdocket", "accession_number",
        "filed_date", "issued_date", "event_class", "channel", "is_lobbying",
        "filed_or_issued_by_as_recorded", "filed_or_issued_by_type",
        "communicating_parties_named_in_notice_text",
        "communicating_parties_basis", "resolved_native_entity_id", "resolved_native_entity_name",
        "ex_parte_quote", "document_description_verbatim", "rule_basis",
        "source_url", "fetched_date", "confidence_tier", "built_date",
        "built_by_script",
        "off_the_record_communications_in_notice",
        "prohibited_communications_in_notice",
        "exempt_communications_in_notice", "dockets_named_in_notice",
        "fr_document_number", "fr_citation", "fr_publication_date",
        "fr_source_url", "fr_notice_date_quote", "fr_join_basis"])
    write_coverage(len(files), len(docket_rows), len(filing_rows),
                   len(exparte_rows))

    print()
    for k, v in st.most_common():
        print(f"  {k:32s} {v:>8,}")
    print(f"\n  dockets            {len(docket_rows):,}")
    print(f"  filings            {len(filing_rows):,}")
    print(f"  ex parte records   {len(exparte_rows):,}")
    print(f"  distinct tribes    {len(tribes_seen):,}")
    print(f"  distinct applicants{len(applicants_seen):,}")
    print(f"  non-tribal filers stating opposition in the document itself: "
          f"{len(opposing):,}")
    if fr_stats:
        print(f"\n  --- Federal Register leg ---")
        for k, v in fr_stats.most_common():
            print(f"  {k:44s} {v:>7,}")
        print(f"  ex parte party rows written                  "
              f"{len(party_rows):>7,}")


DOCKET_PROGRAM = {
    "P": "hydropower licence / relicensing (FPA Part I)",
    "CP": "natural gas certificate, LNG and pipeline (NGA section 3/7)",
    "PF": "natural gas pre-filing",
    "RP": "natural gas rates",
    "ER": "electric rates and transmission",
    "EL": "electric complaints and declaratory orders",
    "EC": "electric merger / disposition of facilities",
    "CD": "dam safety",
    "RM": "rulemaking",
    "AD": "administrative / policy",
    "QF": "qualifying facility",
    "OR": "oil pipeline rates", "IS": "oil pipeline tariffs",
    "DI": "declaration of intent", "ES": "securities",
    "PL": "policy statement", "IN": "investigation",
    "TX": "transmission service", "TS": "transmission service",
}


FR_URL = ("https://www.federalregister.gov/api/v1/documents.json"
          "?conditions[agencies][]=federal-energy-regulatory-commission"
          "&conditions[term]=%22off-the-record+communications%22")


def _fr_state():
    p = RAW / "_fr_state.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _fr_coverage_row():
    s = _fr_state()
    if not s:
        return {
            "source": "Federal Register - FERC 'Records Governing "
                      "Off-the-Record Communications'",
            "url": FR_URL, "status": "NOT_CHECKED",
            "what_was_swept": "count probe only (1 request)",
            "probe_evidence": "HTTP 200, count=641 across 1994-2026. "
                              "DEFERRED, not skipped: another script held an "
                              "ACTIVE lock on www.federalregister.gov and "
                              "PULL_DISCIPLINE rule 1 is one poller per host.",
            "reading": "The FR notices remain to be parsed. Their absence "
                       "here is a scheduling fact, not a source gap.",
            "checked_date": TODAY}
    return {
        "source": "Federal Register - FERC 'Records Governing Off-the-Record "
                  "Communications'",
        "url": FR_URL, "status": "PUBLISHES",
        "what_was_swept": f"every document the term search returns "
                          f"({s['term_search_count']}), full text each, "
                          f"1994-2026",
        "probe_evidence": f"HTTP 200. {s['documents_retrieved']} documents "
                          f"retrieved, {s['documents_refused']} refused. "
                          f"{s['is_notice_by_body_text']} are the notice "
                          f"series by BODY TEXT (the 18 CFR 385.2201 "
                          f"sentence), {s['notices_with_a_party_table']} carry "
                          f"a 'Presenter or requester' table, and "
                          f"{s['communication_items_transcribed']} individual "
                          f"communications were transcribed from those "
                          f"tables.",
        "reading": "THIS IS THE LAYER THAT NAMES THE PARTIES. eLibrary "
                   "publishes the notice document; the Federal Register "
                   "prints its contents. The join is the date both sources "
                   "print - the FR 'Dated:' sign-off equals the eLibrary "
                   "filed_date - so no notice row was created or duplicated; "
                   "the existing rows gained a field they previously recorded "
                   "as unavailable.",
        "checked_date": s["checked_date"]}


def _fr_series_typing_row():
    s = _fr_state()
    if not s:
        return {"source": "Federal Register term search - WHAT 641 COUNTS",
                "url": FR_URL, "status": "NOT_CHECKED",
                "what_was_swept": "nothing", "probe_evidence": "",
                "reading": "", "checked_date": TODAY}
    ex = "; ".join(f"{d['publication_date']} {d['title'][:60]}"
                   for d in s.get("not_the_notice_series_examples", [])[:6])
    return {
        "source": "Federal Register term search - WHAT THE COUNT 641 ACTUALLY "
                  "COUNTS",
        "url": FR_URL, "status": "PUBLISHES",
        "what_was_swept": f"all {s['term_search_count']} results, typed from "
                          f"body text rather than title",
        "probe_evidence": f"{s['not_the_notice_series']} of "
                          f"{s['documents_retrieved']} retrieved documents are "
                          f"NOT the biweekly notice series. Examples: {ex}",
        "reading": "641 IS A COUNT OF FERC DOCUMENTS CONTAINING THE PHRASE, "
                   "NOT A COUNT OF NOTICES. It includes Order No. 607 itself, "
                   "Sunshine Act meeting notices and the 2003 Policy "
                   "Statement on Consultation With Indian Tribes. Typing is "
                   "read from the body's 18 CFR 385.2201 sentence, which also "
                   "keeps the two notices the Federal Register titled "
                   "'Off-the-ROAD Communications' - a source typo over a real "
                   "notice.",
        "checked_date": s["checked_date"]}


def _fr_join_row():
    p = RAW / "_fr_match_state.json"
    if not p.exists():
        return {"source": "Federal Register notice -> eLibrary notice join",
                "url": FR_URL, "status": "NOT_CHECKED",
                "what_was_swept": "nothing", "probe_evidence": "",
                "reading": "", "checked_date": TODAY}
    s = json.loads(p.read_text(encoding="utf-8"))
    ex = "; ".join(f"{x['notice_date']} {x['document_number']} "
                   f"({x['communications']} comms)"
                   for x in s.get("unmatched_examples", [])[:8])
    return {
        "source": "Federal Register notice -> eLibrary notice join, and the "
                  "GAP IT EXPOSES IN eLIBRARY",
        "url": FR_URL, "status": "PUBLISHES",
        "what_was_swept": f"{s['fr_notices_with_a_notice_date']} FR notices "
                          f"carrying a sign-off date against "
                          f"{s['elibrary_rows_total']} eLibrary notice rows",
        "probe_evidence": f"{s['elibrary_rows_that_gained_named_parties']} "
                          f"eLibrary rows gained named parties; "
                          f"{s['party_rows']} party rows written. "
                          f"{s['fr_notices_with_no_elibrary_row']} FR notices "
                          f"carrying "
                          f"{s['fr_notices_with_no_elibrary_row_communications']}"
                          f" named communications have NO eLibrary row on "
                          f"their date. Examples: {ex}. "
                          f"{s['fr_notices_with_no_parsable_notice_date']} "
                          f"notices print no sign-off date at all and cannot "
                          f"be joined.",
        "reading": "THE FEDERAL REGISTER SERIES IS MORE COMPLETE THAN THE "
                   "eLIBRARY RM98-1 DOCKET SHEET. RM98-1-000 was retrieved in "
                   "full (749 of 749 documents reported by the source), so "
                   "these are notices FERC published in the Federal Register "
                   "and did not file into the RM98-1 docket, not documents "
                   "this sweep missed. They are named here rather than "
                   "silently dropped, and their communications ARE published "
                   "in ferc_ex_parte_parties.csv only where a notice row "
                   "exists to carry them - the unmatched ones are the open "
                   "item on this leg.",
        "checked_date": s["checked_date"]}


def write_coverage(n_files, n_dockets, n_filings, n_exparte):
    rows = [
        {"source": "FERC eLibrary Docket/GetSingleDocketSheet",
         "url": f"{API}/Docket/GetSingleDocketSheet",
         "status": "PUBLISHES" if n_files else "NOT_CHECKED",
         "what_was_swept": f"{n_dockets} seeded tribal-relevant dockets, "
                           f"filed 1990-01-01..2026-12-31, 200 documents/page",
         "probe_evidence": f"HTTP 200; {n_filings:,} filer rows returned; "
                           f"payload {{dockets, subdockets, filed_date_beg, "
                           f"filed_date_end, complete_flag, numHits, "
                           f"pageNumber}}; `subdockets` MUST be a STRING - "
                           f"passing an array returns Page:null and zero rows",
         "reading": "Every document filed on the docket in the window, with "
                    "the filer organisation as FERC affiliates it.",
         "checked_date": TODAY},
        {"source": "FERC eLibrary docket sheet - ZERO-BASED pageNumber",
         "url": f"{API}/Docket/GetSingleDocketSheet",
         "status": "PUBLISHES",
         "what_was_swept": "CD20-2-000 (4 documents) and P-12470-000 (45 "
                           "documents) at pageNumber 0 and 1 and at numHits "
                           "200/100/50/25/10/5/4/3/2/1",
         "probe_evidence": "pageNumber is ZERO-BASED. numHits=100 with "
                           "pageNumber=1 returns DataList:[] for CD20-2 and "
                           "for P-12470 while reporting totalHits 4 and 45; "
                           "the identical request with pageNumber=0 returns "
                           "4 and 45 rows. The server offsets by "
                           "numHits*pageNumber, so a caller starting at page "
                           "1 loses the first numHits records and loses ALL "
                           "of them when the docket is smaller than one page. "
                           "Corroborated at small page sizes: numHits=25 "
                           "page 1 returned exactly 45-25=20 rows.",
         "reading": "AN EMPTY PAGE IS NOT AN EMPTY DOCKET. A first pass "
                    "starting at pageNumber=1 produced 124 dockets that "
                    "looked EMPTY and were not, including live hydro and "
                    "pipeline proceedings. Published unexamined, that would "
                    "have been evidence that nobody filed anything. Every "
                    "docket row publishes documents_retrieved beside "
                    "total_hits_reported_by_source so any residual shortfall "
                    "stays visible.",
         "checked_date": TODAY},
        {"source": "FERC eLibrary Docket/getApplicantDetails",
         "url": f"{API}/Docket/getApplicantDetails/<docket>",
         "status": "PUBLISHES",
         "what_was_swept": "one call per seeded docket",
         "probe_evidence": "HTTP 200; P-2082 returns '<br>PacifiCorp'",
         "reading": "The applicant/licensee FERC records for the docket.",
         "checked_date": TODAY},
        {"source": "FERC eLibrary Search/AdvancedSearch",
         "url": f"{API}/Search/AdvancedSearch",
         "status": "NOT_FOUND",
         "what_was_swept": "seven well-formed POSTs: by searchText, by "
                           "docketSearches, by classTypes, by accessionNumber, "
                           "with and without dateSearches, with and without a "
                           "session cookie",
         "probe_evidence": "EVERY one returned HTTP 200 "
                           "success:true totalHits:0 - including a query for "
                           "accessionNumber 20240412-5142, a document the "
                           "docket-sheet endpoint on the same host returns "
                           "seconds earlier. Populating categories/libraries "
                           "in the SPA's own object shapes returns "
                           "success:false 'Unable to parse search request.'",
         "reading": "A BROKEN SEARCH IS NOT EVIDENCE OF ABSENCE (AGENTS.md). "
                    "This endpoint's zero is a fact about the endpoint. It is "
                    "why docket discovery here is seed-driven and why the "
                    "docket set is not the universe of tribal FERC dockets.",
         "checked_date": TODAY},
        _fr_coverage_row(),
        _fr_series_typing_row(),
        _fr_join_row(),
        {"source": "FERC eLibrary docket sweep - COVERAGE OF THE SEED SET",
         "url": f"{API}/Docket/GetSingleDocketSheet",
         "status": "NOT_FOUND",
         "what_was_swept": f"{n_dockets} of 307 seeded dockets, in priority "
                           f"order: RM98-1 (the off-the-record docket), then "
                           f"dockets the Section 106 build already found "
                           f"tribal consultation on, then P- hydropower, then "
                           f"CP/PF gas",
         "probe_evidence": "The host answers a cheap probe "
                           "(Search/GetClassTypes) in 0.17s, so it is not "
                           "blocking - but a populated docket sheet averages "
                           "~100 seconds and two individual requests sat "
                           "MOTIONLESS for 45 and 35 minutes. urllib's "
                           "timeout is the gap between socket operations, not "
                           "a total, so a dribbling stream is not a timeout. "
                           "The run was stopped at its wall-clock budget "
                           "rather than left polling.",
         "reading": "THE DOCKET SET HERE IS NOT THE UNIVERSE OF TRIBAL FERC "
                    "DOCKETS AND IS NOT EVEN ALL OF THE SEED SET. The "
                    "remaining seeds are on disk in docket_seeds.json and the "
                    "fetch stage is resumable - `_fetch_state.json` carries "
                    "what is done. A tribe or an organisation absent from "
                    "these rows may simply be on a docket not yet pulled.",
         "checked_date": TODAY},
        {"source": "FERC eLibrary document full text",
         "url": f"{API}/Filedownload/...",
         "status": "NOT_CHECKED",
         "what_was_swept": "nothing - deliberately",
         "probe_evidence": "Disk on this machine stood at 5.9 GB free with "
                           "five other agents running; the floor is 2 GB. "
                           "Document PDFs were not downloaded.",
         "reading": "Filing metadata only. The body of each filing - which is "
                    "where a stated position actually argues its case - has "
                    "not been read.",
         "checked_date": TODAY},
    ]
    write_csv(CLEAN / "ferc_source_coverage.csv", rows,
              ["source", "url", "status", "what_was_swept", "probe_evidence",
               "reading", "checked_date"])


if __name__ == "__main__":
    stage = (sys.argv[1] if len(sys.argv) > 1 else "all").lower()
    if stage in ("seeds", "all"):
        stage_seeds()
    if stage in ("fetch", "all"):
        stage_fetch()
    if stage in ("fr", "all"):
        stage_fr()
    if stage in ("build", "all"):
        stage_build()
