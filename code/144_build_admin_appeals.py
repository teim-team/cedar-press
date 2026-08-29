#!/usr/bin/env python3
"""144_build_admin_appeals.py -- ROUND 2 item 15: IBIA / IBLA administrative appeals.

Builds the OUTCOME layer: who formally CHALLENGED an Interior action, through
which institutional channel, and which Native entity's matter it touched.

    channel     ADMINISTRATIVE_APPEAL
    class       EventClass.ADVOCACY
    is_lobbying FALSE on every row -- an administrative appeal is advocacy and
                is NOT lobbying. `AdvocacyChannel.ADMINISTRATIVE_APPEAL
                .is_lobbying` is asserted False at import.

=== THE SOURCE ===

The Office of Hearings and Appeals publishes a per-calendar-year chronological
index for each board, 1970-present:

    IBIA  /oha/organization/ibia/cumulative-chronological-index-of-cases/...
    IBLA  /oha/organization/ibla/Finding-IBLA-Decisions/Chronological-Index...

Each index is an HTML table of exactly three columns -- NAME OF CASE, DATE
DECIDED, CITATION/LINK -- with the citation hyperlinked to the decision PDF on
`www.oha.doi.gov`. Every field written by this script is transcribed from that
table. Nothing is inferred from the decision text, because the decision text is
not read here.

`www.oha.doi.gov` is a SECOND host and is not touched by this script at all;
the PDF URL is recorded as published, never fetched. Both facts matter for the
pull-discipline accounting.

=== WHAT IS REFUSED, AND WHY ===

**1. No dataset about private individuals.**

The bulk of the IBIA docket is Indian probate. `Estate of <decedent>` names a
private individual who is not a party of record, and a large share of
non-probate IBIA appellants are individual allottees and heirs appealing about
their own land. Publishing those captions verbatim would build a searchable
register of private persons out of Indian probate -- which is not what this
dataset is for.

So: a party classified as a natural person, and the decedent of an estate, has
`party_name` BLANK with `party_name_withheld_reason` stating why, and the case
caption is published in redacted form. **Nothing is lost for verification** --
the reporter citation IS the record identifier and the PDF URL is keyed by
citation, not by name, so every row remains independently retrievable.

Named individuals ARE published where the source names them in a public
professional capacity: an agency official by title, or a person trading under a
business name (`d/b/a`).

**2. No stance label on an organisation.**

`position_is_addressable()` needs organisation_id + matter_id +
native_entity_id. A position row is emitted only with all three legs, and its
`position` is `UNDETERMINED` on every row, because the caption establishes WHO
appealed and never establishes whether the Interior action being challenged
favoured or harmed the named Native entity. An appellant who challenged one
tribe's trust acquisition has not thereby "opposed Native interests"; that
sentence is not derivable from this source and is not written by this script.

What IS derivable, and is the analytic point: the appellant is named first in
an OHA caption, so `party_role` records who did the challenging. That is
recorded with `party_role_basis = CAPTION_ORDER` and carried at tier B, because
it rests on a reporter convention rather than on a field the source labels.

**3. No tribe link that the caption does not carry.**

Entity resolution is `resolve_entity` from `code/33_apply_party_rulings.py`,
applied to PARTY NAMES ONLY -- never to a substring swept out of a caption.
Where no party resolves, `native_entity_link_basis` says
`NOT_STATED_IN_CAPTION`, which is a property of the index (it publishes three
columns) and not a finding about the case.

Reads  www.doi.gov OHA chronological indices (114 pages, cached to data/raw/)
       data/spine/cedar_entity_spine.csv
Writes data/clean/admin_appeal_decisions.csv
       data/clean/admin_appeal_parties.csv
       data/clean/admin_appeal_positions.csv
       data/clean/source_coverage_admin_appeals.csv
       review/admin_appeal_unresolved_organisations.csv
       review/admin_appeal_entity_link_candidates.csv
"""
from __future__ import annotations

import csv
import datetime as dt
import functools
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "code"
RAW = ROOT / "data" / "raw" / "admin_appeals"
CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
REVIEW = ROOT / "review"
LOGS = ROOT / "logs"
SCRIPT = "code/144_build_admin_appeals.py"
TODAY = dt.date.today().isoformat()

for d in (RAW, CLEAN, REVIEW, LOGS):
    d.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(CODE))
from cedar_domain import (  # noqa: E402
    AdvocacyChannel, EventClass, Position, position_is_addressable, Tier,
)

CH = AdvocacyChannel.ADMINISTRATIVE_APPEAL
assert CH.event_class == EventClass.ADVOCACY
assert CH.is_lobbying is False, "an administrative appeal is not lobbying"

HOST = "www.doi.gov"
UA = ("CedarPress-research/1.0 (+https://cedarpress.co; "
      "elijahsamsonmoreno@gmail.com)")
HEADERS = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"}
GAP = 1.4                      # seconds between requests, one poller
DEADLINE_S = 55 * 60           # wall-clock deadline for the whole fetch phase

FIRST_YEAR, LAST_YEAR = 1970, 2026

IBIA_YEAR_URL = ("https://www.doi.gov/oha/organization/ibia/"
                 "cumulative-chronological-index-of-cases/%s")
IBLA_YEAR_URL = ("https://www.doi.gov/oha/organization/ibla/"
                 "Finding-IBLA-Decisions/Chronological-Index-of-Decisions/%s")

# The site changed its slug casing at 2013 (IBIA) / 2013 (IBLA). Both spellings
# are tried; which one answered is recorded per year in the coverage table.
IBIA_SLUGS = ["cases-decided-in-calendar-year-%d", "Cases-Decided-in-Calendar-Year-%d"]
IBLA_SLUGS = ["calendar-year-%d", "Calendar-Year-%d"]

INDEX_HUB = {
    "IBIA": "https://www.doi.gov/oha/organization/ibia/Chronological-Index-of-Decisions",
    "IBLA": ("https://www.doi.gov/oha/organization/ibla/Finding-IBLA-Decisions/"
             "Chronological-Index-of-Decisions"),
}

_stats = Counter()
_notes = []
ECLASS = {}          # tribe_id -> entity_class, filled from the spine
held = Counter()     # (party, candidate, method, hold_kind) -> n


def note(s):
    _notes.append(s)
    print("   . %s" % s)


# ===========================================================================
# Pull discipline -- one poller per host, claimed in logs/_HOSTLOCK_<host>.json
# ===========================================================================
def lock_path(host):
    return LOGS / ("_HOSTLOCK_%s.json" % host)


def read_lock(host):
    p = lock_path(host)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def pid_alive(pid):
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "if (Get-Process -Id %d -ErrorAction SilentlyContinue) {'Y'} "
             "else {'N'}" % int(pid)],
            capture_output=True, text=True, timeout=25).stdout
        return "Y" in out
    except Exception:
        return False


def claim_host(host, purpose):
    cur = read_lock(host)
    if cur and cur.get("active") and not cur.get("released"):
        holder = cur.get("pid")
        age_h = 99.0
        try:
            t = cur.get("claimed_at") or cur.get("started") or ""
            t0 = dt.datetime.fromisoformat(t.replace("Z", "+00:00"))
            if t0.tzinfo is None:
                t0 = t0.replace(tzinfo=dt.timezone.utc)
            age_h = (dt.datetime.now(dt.timezone.utc) - t0).total_seconds() / 3600
        except Exception:
            pass
        if holder and (pid_alive(holder) or age_h < 6):
            cur.setdefault("queue", []).append(
                {"script": SCRIPT, "purpose": purpose,
                 "queued_at": dt.datetime.now(dt.timezone.utc).isoformat()})
            lock_path(host).write_text(json.dumps(cur, indent=1), encoding="utf-8")
            note("host_deferred:%s (an existing poller holds it)" % host)
            return False
    lock_path(host).write_text(json.dumps({
        "host": host, "pid": os.getpid(), "script": SCRIPT,
        "claimed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "active": True, "queue": [],
        "policy": "sequential, >=1.4s gap, stop on first edge refusal, "
                  "55 min wall-clock deadline",
        "note": purpose}, indent=1), encoding="utf-8")
    return True


def release_host(host, note_text=""):
    cur = read_lock(host) or {"host": host}
    cur["active"] = False
    cur["released"] = TODAY
    cur["note"] = note_text or cur.get("note", "")
    lock_path(host).write_text(json.dumps(cur, indent=1), encoding="utf-8")


class EdgeRefusal(Exception):
    """Transport failure or 403 from the edge. Stop-work, NOT a fact about the
    object. A 0 is never recorded as 'not published' (AGENTS.md 2026-08-08)."""


def fetch(url, session, started):
    """Return (status, text). Raises EdgeRefusal on transport failure/403."""
    if time.time() - started > DEADLINE_S:
        raise EdgeRefusal("wall-clock deadline reached")
    t0 = time.time()
    try:
        r = session.get(url, headers=HEADERS, timeout=(15, 60))
    except Exception as e:
        raise EdgeRefusal("transport:%s after %.1fs" % (type(e).__name__,
                                                        time.time() - t0))
    if r.status_code == 403:
        raise EdgeRefusal("http_403 (edge denial) after %.1fs" % (time.time() - t0))
    if r.status_code == 429:
        raise EdgeRefusal("http_429 throttle")
    time.sleep(GAP)
    return r.status_code, r.text


# ===========================================================================
# Parsing the chronological index table
# ===========================================================================
TAG = re.compile(r"<[^>]+>")
WS = re.compile(r"\s+")


def untag(s):
    s = s.replace("&nbsp;", " ").replace("&amp;", "&")
    s = s.replace("&#39;", "'").replace("&quot;", '"')
    s = TAG.sub(" ", s)
    return WS.sub(" ", s).strip()


def parse_index(html):
    """-> list of (case_name, date_decided, citation, pdf_url)."""
    out = []
    for tab in re.findall(r"<table.*?</table>", html, re.S):
        for rw in re.findall(r"<tr[^>]*>(.*?)</tr>", tab, re.S):
            cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", rw, re.S)
            if len(cells) < 3:
                continue
            name = untag(cells[0])
            date_s = untag(cells[1])
            cite = untag(cells[2])
            href = re.search(r'href="([^"]+)"', cells[2])
            if not name or name.upper().startswith("NAME OF CASE"):
                continue
            if not cite:
                continue
            out.append((name, date_s, cite, (href.group(1) if href else "")))
    return out


DATE_RX = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{2,4})")


def parse_date(s):
    m = DATE_RX.search(s or "")
    if not m:
        return "", ""
    mo, da, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if yr < 100:
        yr += 1900 if yr > 50 else 2000
    try:
        return dt.date(yr, mo, da).isoformat(), "EXACT"
    except ValueError:
        return "", ""


CITE_RX = re.compile(r"(\d+)\s*(IBIA|IBLA)\s*(\d+)", re.I)


def parse_cite(s):
    m = CITE_RX.search((s or "").replace(" ", " "))
    if not m:
        return "", "", ""
    return m.group(1), m.group(2).upper(), m.group(3)


# ===========================================================================
# Party typing. The whole private-individual refusal lives here.
# ===========================================================================
AGENCY_MARKERS = (
    "bureau of indian affairs", "bureau of land management", "regional director",
    "superintendent", "assistant secretary", "office of the special trustee",
    "office of natural resources revenue", "minerals management service",
    "office of surface mining", "national park service", "fish and wildlife",
    "bureau of reclamation", "united states", "department of the interior",
    "field manager", "state director", "area director", "deputy commissioner",
    "commissioner of indian affairs", "director, office", "acting director",
    "bia ", "blm ", "u.s. forest service", "forest service",
    # added after reading the first position rows: two BIA offices were typed
    # ORGANISATION and acquired position rows they cannot hold. An Interior
    # official is not an outside organisation with a stance.
    "line officer", "agency, office", "office of indian education",
    "education programs", "indian agency", "osmre", "office of surface",
)

ORG_MARKERS = (
    "tribe", "tribes", "tribal", "nation", "band", "pueblo", "rancheria",
    "village", "community", "council", "confederated", "colony", "reservation",
    "inc.", "inc", "l.l.c", "llc", "corp", "corporation", "company", "co.",
    "ltd", "l.p.", "lp", "partnership", "association", "assn", "society",
    "foundation", "institute", "trust", "coalition", "alliance", "committee",
    "county", "city of", "town of", "state of", "district", "authority",
    "commission", "board", "department", "agency", "school", "university",
    "college", "church", "ranch", "ranches", "farms", "mining", "minerals",
    "energy", "resources", "oil", "gas", "petroleum", "exploration",
    "development", "enterprises", "holdings", "group", "partners", "fund",
    "cooperative", "co-op", "union", "club", "center", "centre", "museum",
    "hospital", "clinic", "housing", "utilities", "water", "irrigation",
    "electric", "telephone", "railroad", "railway", "airlines", "bank",
    "insurance", "realty", "properties", "land & cattle", "livestock",
    "outfitters", "watersheds", "conservancy", "wilderness", "environmental",
    "et al.", "et al", "u.s.a.", "usa", "america", "american", "national",
)

DBA_RX = re.compile(r"\b(d/?b/?a/?|doing business as)\b", re.I)
ESTATE_RX = re.compile(r"^\s*(estate|estates)\s+of\b", re.I)
# "In re", "Petition of", "Appeal of" -- caption forms that carry no adversary
NO_ADVERSARY_RX = re.compile(r"^\s*(in re\b|petition of\b|appeal of\b|"
                             r"request of\b|application of\b)", re.I)

SPLIT_RX = re.compile(r"\s+(?:v\.|vs\.|versus)\s+", re.I)
# IBLA captions append the docket in two shapes: "Name/IBLA 2018-0094" and the
# bare "Name/2017-0214". Both must go, and the bare form is the one that put
# "GOM Shelf, LLC/2017-0214" through the natural-person branch on the first
# pass -- the trailing digits broke the token "llc" and the row would have had
# a real company's name withheld as if it were a private individual.
DOCKET_TAIL_RX = re.compile(
    r"\s*/\s*((?:IB[LI]A[\s\-]?)?\d{4}[\s\-]\d+.*)$", re.I)

_TOKEN_RX = re.compile(r"[^a-z0-9&]+")


def _tokens(name):
    return set(t for t in _TOKEN_RX.split((name or "").lower()) if t)


def party_type(name: str) -> str:
    """Tokenised, so trailing punctuation and docket digits cannot hide a
    corporate form. Falling through means WITHHOLDING the name, so the safe
    direction is the default."""
    raw = (name or "").strip()
    if ESTATE_RX.match(raw):
        return "ESTATE"
    if DBA_RX.search(raw):
        return "BUSINESS_DBA"
    flat = " " + _TOKEN_RX.sub(" ", raw.lower()).strip() + " "
    toks = _tokens(raw)
    for m in AGENCY_MARKERS:
        # tokenise the MARKER too -- "director, office" must match the
        # punctuation-stripped "director office", or an Interior official is
        # typed ORGANISATION and acquires a position row they cannot have.
        if (" " + _TOKEN_RX.sub(" ", m.lower()).strip() + " ") in flat:
            return "AGENCY_OFFICIAL"
    for m in ORG_MARKERS:
        m = m.strip()
        if " " in m or "." in m:
            if (" " + _TOKEN_RX.sub(" ", m.lower()).strip() + " ") in flat:
                return "ORGANISATION"
        elif _TOKEN_RX.sub(" ", m.lower()).strip() in toks:
            return "ORGANISATION"
    return "NATURAL_PERSON"


WITHHOLD_REASON = {
    "NATURAL_PERSON": (
        "Natural person. Cedar Press does not publish a register of private "
        "individuals built out of Indian probate and allotment appeals. The "
        "reporter citation is the record identifier and the decision remains "
        "retrievable at decision_pdf_url."),
    "ESTATE": (
        "Decedent in an Indian probate matter. The decedent is not a party of "
        "record and is a private individual; the name is withheld. The "
        "reporter citation is the record identifier."),
}


def redact(caption: str, parties) -> tuple:
    """Return (published_caption, was_redacted)."""
    out, red = caption, False
    for raw, ptype in parties:
        if ptype in WITHHOLD_REASON:
            if ptype == "ESTATE":
                repl = re.sub(r"^(\s*[Ee]states?\s+of\s+).*$",
                              r"\1[name withheld]", raw)
            else:
                repl = "[name withheld]"
            if raw and raw in out:
                out = out.replace(raw, repl)
                red = True
    return out, red


def split_parties(caption: str):
    """-> list of (name, role, ptype). Role from CAPTION ORDER (tier B)."""
    cap = DOCKET_TAIL_RX.sub("", caption or "").strip()
    if ESTATE_RX.match(cap):
        return [(cap, "ESTATE_SUBJECT", "ESTATE")]
    if NO_ADVERSARY_RX.match(cap):
        return [(cap, "PETITIONER", party_type(cap))]
    parts = [p.strip(" ,;.") for p in SPLIT_RX.split(cap) if p.strip(" ,;.")]
    if len(parts) < 2:
        # A single-party caption at OHA is the APPEAL captioned by its
        # appellant -- "Interwest Exploration, Inc." is an appeal from a BLM
        # decision, not a party of unknown role. Same basis as the two-party
        # case: caption order, carried at tier B.
        return [(cap, "APPELLANT", party_type(cap))]
    out = [(parts[0], "APPELLANT", party_type(parts[0]))]
    for p in parts[1:]:
        out.append((p, "APPELLEE", party_type(p)))
    return out


def docket_no(caption: str) -> str:
    m = DOCKET_TAIL_RX.search(caption or "")
    return WS.sub(" ", m.group(1)).strip() if m else ""


# ---------------------------------------------------------------------------
# WHICH RESOLVER TIERS MAY BECOME A PUBLISHED ENTITY LINK
#
# AGENTS.md, THE CONTAINMENT DEFECT: "Until it is fixed centrally, containment
# may be used only to resolve an owner ALREADY NAMED IN EVIDENCE -- never to
# detect a match." Sweeping 20,027 case-caption parties for tribes is exactly
# detection, so containment cannot key a link here.
#
# Measured on the first full run of this script, 602 of 1,000 resolved party
# rows came from the containment tier, and reading them one at a time shows
# both good and bad in the same list:
#
#   good  White Mountain Apache Tribe  -> White Mountain     (the short-name
#         Turtle Mountain Band ...     -> Turtle Mountain     expansion the
#         Hoopa Valley Tribe           -> Hoopa               tier exists for)
#   bad   Jackson County, Kansas       -> Jackson            (a PLACE)
#         Western Watersheds Project   -> The NATIVE Project (token "project")
#         READ & STEVENS, INC.         -> Stevens Village
#         Eagle Butte, South Dakota, City of -> Eagle
#         Ramah Navajo School Board    -> Navajo             (program entity)
#
# The bad ones are indistinguishable from the good ones without a human, which
# is what a review queue is for. Containment matches are HELD: the party row
# carries the candidate and its reason, the published entity link stays blank.
# ---------------------------------------------------------------------------
LINKING_METHODS = frozenset({"exact", "core", "alias"})

CORP_FORM_RX = re.compile(
    r"\b(inc|inc\.|incorporated|corp|corp\.|corporation|llc|l\.l\.c|company|"
    r"co\.|ltd|limited|lp|l\.p\.)\b", re.I)
GOVERNMENT_CLASSES = frozenset({
    "Federally recognized tribe", "Federally recognized Alaska Native Village",
    "State-recognized tribe"})


def link_verdict(party_name, method, entity_class):
    """-> (may_link, hold_reason). Read the tier, then one narrow guard."""
    if method not in LINKING_METHODS:
        return False, ("containment_held: containment may resolve an owner "
                       "already named in evidence, never detect a match "
                       "(AGENTS.md, THE CONTAINMENT DEFECT)")
    if CORP_FORM_RX.search(party_name or "") and entity_class in GOVERNMENT_CLASSES:
        # Measured miss: "CIRCLE L. INC." -> the Native Village of Circle,
        # because core() drops the corporate form and leaves one token. Tribes
        # DO own companies directly, so this is a hold for a human, not a
        # refusal -- AGENTS.md records that the broad version of this rule was
        # wrong outside Alaska.
        return False, ("corp_form_on_government_held: a corporate-form party "
                       "name resolved to a tribal or village GOVERNMENT on a "
                       "single shared token")
    return True, ""


# ===========================================================================
# Resolver -- THE one resolver (standing rule 8). Never re-implemented.
# ===========================================================================
def load_resolver():
    spec = importlib.util.spec_from_file_location(
        "m33", str(CODE / "33_apply_party_rulings.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    # PERFORMANCE ONLY, and it changes no answer. `norm` and `core` are pure
    # functions of one string, and `resolve_entity` recomputes both for all
    # 1,310 spine rows on EVERY call -- 15,882 captions makes that ~80M
    # redundant normalisations. Memoising them leaves the matching semantics
    # byte-identical; `core` returns a frozenset, so a shared return value
    # cannot be mutated by a caller.
    m.norm = functools.lru_cache(maxsize=None)(m.norm)
    m.core = functools.lru_cache(maxsize=None)(m.core)
    return m.resolve_entity


def read_csv(p):
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    tmp = str(path) + ".part"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    os.replace(tmp, str(path))
    return len(rows)


# ===========================================================================
def year_urls(board, year):
    if board == "IBIA":
        return [IBIA_YEAR_URL % (s % year) for s in IBIA_SLUGS]
    return [IBLA_YEAR_URL % (s % year) for s in IBLA_SLUGS]


def cache_path(board, year):
    return RAW / ("%s_%d.html" % (board.lower(), year))


def fetch_phase():
    """Fetch every year index, cached. Returns coverage rows."""
    cov = []
    if not claim_host(HOST, "OHA IBIA/IBLA chronological indices, "
                            "%d-%d, two boards" % (FIRST_YEAR, LAST_YEAR)):
        note("deferring to the existing %s poller; using cache only" % HOST)
        for board in ("IBIA", "IBLA"):
            for y in range(FIRST_YEAR, LAST_YEAR + 1):
                p = cache_path(board, y)
                cov.append({"board": board, "year": y,
                            "coverage_status": "PUBLISHES" if p.exists()
                            else "NOT_CHECKED",
                            "http_status": "" if p.exists() else "",
                            "source_url": "", "fetched_date": TODAY,
                            "note": "cache" if p.exists()
                            else "host held by another poller"})
        return cov

    started = time.time()
    session = requests.Session()
    stopped = False
    try:
        for board in ("IBIA", "IBLA"):
            for y in range(LAST_YEAR, FIRST_YEAR - 1, -1):
                p = cache_path(board, y)
                if p.exists() and p.stat().st_size > 2000:
                    cov.append({"board": board, "year": y,
                                "coverage_status": "PUBLISHES",
                                "http_status": "200(cached)",
                                "source_url": "", "fetched_date": TODAY,
                                "note": "already on disk"})
                    continue
                if stopped:
                    cov.append({"board": board, "year": y,
                                "coverage_status": "NOT_CHECKED",
                                "http_status": "", "source_url": "",
                                "fetched_date": TODAY,
                                "note": "run stopped on an earlier refusal"})
                    continue
                got = None
                for u in year_urls(board, y):
                    try:
                        st, txt = fetch(u, session, started)
                    except EdgeRefusal as e:
                        note("EDGE REFUSAL on %s %d: %s -- stopping this host"
                             % (board, y, e))
                        cov.append({"board": board, "year": y,
                                    "coverage_status": "NOT_CHECKED",
                                    "http_status": "0",
                                    "source_url": u, "fetched_date": TODAY,
                                    "note": "transport/edge refusal: %s. A 0 is "
                                            "a fact about the moment, never "
                                            "about the object." % e})
                        stopped = True
                        got = "STOP"
                        break
                    if st == 200 and "<table" in txt:
                        p.write_text(txt, encoding="utf-8")
                        got = (u, st)
                        break
                    if st == 200:
                        got = (u, "200_no_table")
                if got == "STOP":
                    break
                if got and isinstance(got, tuple) and got[1] == 200:
                    cov.append({"board": board, "year": y,
                                "coverage_status": "PUBLISHES",
                                "http_status": "200", "source_url": got[0],
                                "fetched_date": TODAY, "note": ""})
                elif got and isinstance(got, tuple):
                    cov.append({"board": board, "year": y,
                                "coverage_status": "NOT_FOUND",
                                "http_status": str(got[1]),
                                "source_url": got[0], "fetched_date": TODAY,
                                "note": "page served but carries no decision "
                                        "table"})
                else:
                    cov.append({"board": board, "year": y,
                                "coverage_status": "NOT_FOUND",
                                "http_status": "404",
                                "source_url": year_urls(board, y)[0],
                                "fetched_date": TODAY,
                                "note": "both slug spellings 404"})
            if stopped:
                break
    finally:
        release_host(HOST, "IBIA/IBLA indices: %d year pages resolved"
                     % len([c for c in cov if c["coverage_status"] == "PUBLISHES"]))
    return cov


# ===========================================================================
def main():
    print("=" * 74)
    print("144 -- IBIA / IBLA administrative appeals (ROUND 2 item 15)")
    print("     channel=%s  class=%s  is_lobbying=%s"
          % (CH.value, CH.event_class.value, CH.is_lobbying))
    print("=" * 74)

    cov = fetch_phase()
    have = sum(1 for c in cov if c["coverage_status"] == "PUBLISHES")
    print("\n   year indices available: %d of %d"
          % (have, 2 * (LAST_YEAR - FIRST_YEAR + 1)))

    spine = read_csv(SPINE)
    resolve = load_resolver()
    ECLASS.update({r["tribe_id"]: r.get("entity_class", "") for r in spine})
    print("   spine: %d entities; resolver imported from "
          "33_apply_party_rulings.py" % len(spine))

    resolve_cache = {}

    def R(name):
        k = (name or "").strip().lower()
        if k not in resolve_cache:
            try:
                resolve_cache[k] = resolve(name, spine)
            except Exception:
                resolve_cache[k] = (None, None, "resolver_error")
        return resolve_cache[k]

    decisions, parties, positions = [], [], []
    unresolved = Counter()
    unresolved_ex = {}
    seen_cite = {}
    held.clear()

    for board in ("IBIA", "IBLA"):
        hub = INDEX_HUB[board]
        for y in range(FIRST_YEAR, LAST_YEAR + 1):
            p = cache_path(board, y)
            if not p.exists():
                continue
            html = p.read_text(encoding="utf-8", errors="replace")
            src = ""
            for u in year_urls(board, y):
                src = u
                break
            rows = parse_index(html)
            _stats["index_rows_%s" % board] += len(rows)
            for (name, date_s, cite, pdf) in rows:
                vol, rep, page = parse_cite(cite)
                if not rep:
                    _stats["skipped_uncitable"] += 1
                    continue
                citation = "%s %s %s" % (vol, rep, page)
                ddate, dbasis = parse_date(date_s)
                if not ddate:
                    _stats["skipped_undated"] += 1
                    continue
                did = "%s-%s-%s" % (rep, vol, page)
                if did in seen_cite:
                    _stats["duplicate_citation_rows"] += 1
                    continue
                seen_cite[did] = citation

                plist = split_parties(name)
                pub_caption, was_red = redact(
                    DOCKET_TAIL_RX.sub("", name).strip(),
                    [(a, c) for a, _, c in plist])

                # --- party rows -----------------------------------------
                ent_ids, ent_names, org_ids = [], [], []
                cand_ids, cand_names = [], []
                for i, (pname, role, ptype) in enumerate(plist):
                    withheld = ptype in WITHHOLD_REASON
                    tid = cname = how = ""
                    cand_id = cand_name = hold = ""
                    if not withheld and ptype in ("ORGANISATION", "BUSINESS_DBA"):
                        tid_, cname_, how_ = R(pname)
                        if tid_:
                            may, hold = link_verdict(pname, how_,
                                                     ECLASS.get(tid_, ""))
                            if may:
                                tid, cname, how = tid_, cname_, how_
                                if tid_ not in ent_ids:
                                    ent_ids.append(tid_)
                                    ent_names.append(cname_)
                            else:
                                cand_id, cand_name, how = tid_, cname_, how_
                                held[(pname, cname_, how_, hold.split(":")[0])] += 1
                                _stats["entity_link_held"] += 1
                                if tid_ not in cand_ids:
                                    cand_ids.append(tid_)
                                    cand_names.append(cname_)
                        else:
                            unresolved[pname] += 1
                            unresolved_ex.setdefault(pname, (citation, board))
                    org_id = ""
                    if ptype in ("ORGANISATION", "BUSINESS_DBA"):
                        org_id = tid or ("ORG:" + re.sub(r"[^A-Z0-9]+", "_",
                                                         pname.upper())[:60])
                        if org_id not in org_ids:
                            org_ids.append(org_id)
                    if not withheld:
                        pub_name = pname
                    else:
                        pub_name = ""
                    parties.append({
                        "party_id": "%s#%d" % (did, i),
                        "decision_id": did,
                        "board": board,
                        "citation": citation,
                        "decision_date": ddate,
                        "party_role": role,
                        "party_role_basis": "CAPTION_ORDER",
                        "party_role_tier": Tier.B.value,
                        "party_name": pub_name,
                        "party_name_withheld_reason":
                            WITHHOLD_REASON.get(ptype, ""),
                        "party_type": ptype,
                        "is_natural_person": "Y" if withheld else "N",
                        "organisation_id": org_id,
                        "resolved_entity_id": tid,
                        "resolved_entity_name": cname,
                        "resolve_method": how,
                        "entity_link_held_candidate_id": cand_id,
                        "entity_link_held_candidate_name": cand_name,
                        "entity_link_hold_reason": hold,
                        # A caption cell that carries BOTH an agency marker and
                        # a corporate form names more than one party in one
                        # string -- "OSMRE and PEABODY COAL CO". Typing it
                        # AGENCY_OFFICIAL is right for the first party and
                        # loses the company, and splitting on " and " would
                        # break "Assiniboine and Sioux Tribes". Flagged for a
                        # human rather than guessed, so nothing is lost
                        # silently.
                        "compound_party_caption":
                            "Y" if (ptype == "AGENCY_OFFICIAL"
                                    and CORP_FORM_RX.search(pname or "")) else "N",
                        "channel": CH.value,
                        "event_class": CH.event_class.value,
                        "is_lobbying": "N",
                        "source_url": src,
                        "source_record_id": citation,
                        "decision_pdf_url": pdf,
                        "fetched_date": TODAY,
                        "confidence_tier": Tier.A.value,
                    })

                appellant = next((a for a, r, c in plist if r == "APPELLANT"), "")
                appellant_type = next((c for a, r, c in plist if r == "APPELLANT"), "")
                appellee = next((a for a, r, c in plist if r == "APPELLEE"), "")
                if plist[0][2] == "ESTATE":
                    cat = "PROBATE_ESTATE"
                elif appellee:
                    cat = "ADVERSARIAL_CAPTION"
                elif appellant:
                    # An OHA appeal captioned by its appellant alone, which is
                    # the normal IBLA form. Not adversarial on its face; the
                    # respondent is the bureau whose decision was appealed and
                    # the caption does not name it.
                    cat = "SINGLE_PARTY_CAPTION"
                else:
                    cat = "NON_ADVERSARIAL_CAPTION"

                decisions.append({
                    "decision_id": did,
                    "board": board,
                    "board_name": ("Interior Board of Indian Appeals" if board == "IBIA"
                                   else "Interior Board of Land Appeals"),
                    "citation": citation,
                    "reporter": rep,
                    "volume": vol,
                    "page": page,
                    "case_name_published": pub_caption,
                    "case_name_redacted": "Y" if was_red else "N",
                    "docket_number": docket_no(name),
                    "decision_date": ddate,
                    "decision_date_basis": dbasis,
                    "decision_year": ddate[:4],
                    "case_category": cat,
                    "appellant_type": appellant_type,
                    "appellee_is_interior_agency":
                        "Y" if appellee and party_type(appellee) == "AGENCY_OFFICIAL"
                        else ("N" if appellee else ""),
                    "n_parties": len(plist),
                    "n_organisation_parties": len(org_ids),
                    "native_entity_ids": "|".join(ent_ids),
                    "native_entity_names": "|".join(ent_names),
                    "native_entity_link_basis":
                        "PARTY_NAME_RESOLVED" if ent_ids
                        else ("CANDIDATE_HELD_FOR_RULING" if cand_ids
                              else "NOT_STATED_IN_CAPTION"),
                    "native_entity_candidate_ids": "|".join(cand_ids),
                    "native_entity_candidate_names": "|".join(cand_names),
                    "disposition": "",
                    "disposition_basis": "NOT_IN_INDEX",
                    "channel": CH.value,
                    "event_class": CH.event_class.value,
                    "is_lobbying": "N",
                    "decision_pdf_url": pdf,
                    "source_url": src,
                    "source_page_title": "%s chronological index, calendar year %d"
                                         % (board, y),
                    "source_index_hub": hub,
                    "source_record_id": citation,
                    "fetched_date": TODAY,
                    "confidence_tier": Tier.A.value,
                })

                # --- position rows: three legs or nothing ----------------
                for (pname, role, ptype) in plist:
                    if ptype not in ("ORGANISATION", "BUSINESS_DBA"):
                        continue
                    tid_, _, how_ = R(pname)
                    if tid_ and not link_verdict(pname, how_,
                                                 ECLASS.get(tid_, ""))[0]:
                        tid_ = None          # a held candidate is not a link
                    org_id = tid_ or ("ORG:" + re.sub(r"[^A-Z0-9]+", "_",
                                                      pname.upper())[:60])
                    for ne, nen in zip(ent_ids, ent_names):
                        if ne == tid_:
                            continue          # an entity has no position on itself
                        if not position_is_addressable(org_id, citation, ne):
                            _stats["position_refused_missing_leg"] += 1
                            continue
                        positions.append({
                            "position_id": "%s#%s#%s" % (did, org_id, ne),
                            "organisation_id": org_id,
                            "organisation_name": pname,
                            "matter_id": citation,
                            "matter_type": "ADMINISTRATIVE_APPEAL",
                            "native_entity_id": ne,
                            "native_entity_name": nen,
                            "party_role": role,
                            "position": Position.UNDETERMINED.value,
                            "position_basis":
                                "The chronological index publishes case name, "
                                "date and citation only. It establishes WHO "
                                "appealed; it does not establish whether the "
                                "Interior action under challenge favoured or "
                                "harmed the named Native entity. Direction is "
                                "not derivable from this source and is not "
                                "asserted.",
                            "channel": CH.value,
                            "event_class": CH.event_class.value,
                            "is_lobbying": "N",
                            "decision_date": ddate,
                            "source_url": src,
                            "source_record_id": citation,
                            "decision_pdf_url": pdf,
                            "fetched_date": TODAY,
                            "confidence_tier": Tier.B.value,
                        })

    # ---------------------------------------------------------------- write
    dfields = list(decisions[0].keys()) if decisions else []
    pfields = list(parties[0].keys()) if parties else []
    qfields = list(positions[0].keys()) if positions else []
    if decisions:
        write_csv(CLEAN / "admin_appeal_decisions.csv", decisions, dfields)
    if parties:
        write_csv(CLEAN / "admin_appeal_parties.csv", parties, pfields)
    if positions:
        write_csv(CLEAN / "admin_appeal_positions.csv", positions, qfields)
    write_csv(CLEAN / "source_coverage_admin_appeals.csv", cov,
              ["board", "year", "coverage_status", "http_status",
               "source_url", "fetched_date", "note"])

    ur = [{"organisation_name": k, "n_decisions": v,
           "example_citation": unresolved_ex[k][0],
           "board": unresolved_ex[k][1],
           "question": "Is this a Native entity? If so, which spine entity?",
           "YOUR_RULING": ""}
          for k, v in unresolved.most_common()]
    write_csv(REVIEW / "admin_appeal_unresolved_organisations.csv", ur,
              ["organisation_name", "n_decisions", "example_citation", "board",
               "question", "YOUR_RULING"])

    hq = [{"party_name": k[0], "candidate_entity": k[1], "resolve_method": k[2],
           "hold_kind": k[3], "n_party_rows": v,
           "question": "Is this candidate the right entity for this party? "
                       "YES writes the link; NO rules it out permanently.",
           "YOUR_RULING": ""}
          for k, v in held.most_common()]
    write_csv(REVIEW / "admin_appeal_entity_link_candidates.csv", hq,
              ["party_name", "candidate_entity", "resolve_method", "hold_kind",
               "n_party_rows", "question", "YOUR_RULING"])

    # ---------------------------------------------------------------- report
    byb = Counter(d["board"] for d in decisions)
    linked = [d for d in decisions if d["native_entity_ids"]]
    ents = set()
    for d in linked:
        ents.update(d["native_entity_ids"].split("|"))
    withheld = sum(1 for p in parties if p["is_natural_person"] == "Y")
    cats = Counter(d["case_category"] for d in decisions)

    print("\n" + "-" * 74)
    print("decisions               %6d   (IBIA %d / IBLA %d)"
          % (len(decisions), byb["IBIA"], byb["IBLA"]))
    print("parties                 %6d" % len(parties))
    print("  natural persons withheld %5d  (%.1f%% of parties)"
          % (withheld, 100.0 * withheld / max(1, len(parties))))
    print("captions redacted       %6d"
          % sum(1 for d in decisions if d["case_name_redacted"] == "Y"))
    print("decisions tribe-linked  %6d   (%.1f%%)"
          % (len(linked), 100.0 * len(linked) / max(1, len(decisions))))
    print("distinct spine entities %6d" % len(ents))
    print("entity links HELD       %6d party rows / %d distinct pairs -> review/"
          % (_stats["entity_link_held"], len(hq)))
    print("position rows           %6d   (all UNDETERMINED, three legs each)"
          % len(positions))
    print("unresolved organisations%6d  -> review/" % len(ur))
    print("case categories        ", dict(cats))
    print("year coverage           %d PUBLISHES / %d NOT_FOUND / %d NOT_CHECKED"
          % (sum(1 for c in cov if c["coverage_status"] == "PUBLISHES"),
             sum(1 for c in cov if c["coverage_status"] == "NOT_FOUND"),
             sum(1 for c in cov if c["coverage_status"] == "NOT_CHECKED")))
    print("stats                  ", dict(_stats))
    print("-" * 74)

    (LOGS / ("144_admin_appeals_%s.json" % TODAY)).write_text(json.dumps({
        "script": SCRIPT, "date": TODAY,
        "decisions": len(decisions), "parties": len(parties),
        "positions": len(positions), "by_board": dict(byb),
        "tribe_linked": len(linked), "entities": len(ents),
        "natural_persons_withheld": withheld,
        "unresolved_organisations": len(ur),
        "categories": dict(cats), "stats": dict(_stats),
        "notes": _notes}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
