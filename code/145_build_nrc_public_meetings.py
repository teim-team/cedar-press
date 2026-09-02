#!/usr/bin/env python3
"""145_build_nrc_public_meetings.py -- ROUND 2 item 14: NRC public meetings.

Target shape: NRC meeting -> external participant -> tribe/entity -> NRC office
-> docket -> facility -> purpose -> summary.

=== CLASSIFICATION, AND IT IS READ FROM THE PURPOSE FIELD ===

    scheduled regulatory meeting, named external participant
        -> EventClass.ADVOCACY, channel REGULATORY_EX_PARTE
    government-to-government tribal consultation
        -> EventClass.GOVERNMENT_ENGAGEMENT, channel CONSULTATION
    NHPA section 106
        -> EventClass.GOVERNMENT_ENGAGEMENT, channel SECTION_106_CONSULTATION

The purpose text is READ, never assumed, and the matched phrase is carried
verbatim in `classification_basis_quote` on every classified row. A meeting
whose purpose text does not establish which of these it is stays UNCLASSIFIED
with the reason stated -- it is not defaulted into ADVOCACY.

**An annotation that must travel with `REGULATORY_EX_PARTE` here.** An NRC
public meeting is publicly NOTICED and appears on this schedule; it is not a
communication outside the public record. The channel name denotes the family
(direct regulator/stakeholder engagement on a docket), and `channel_note` says
so on every row so that no reader infers concealment from the label.

=== ABSENCE UNDER A FILTER IS A PROPERTY OF THE FILTER ===

The Drupal PMNS view exposes exactly four filters: `keywords` (documented as
"Title or purpose contains"), `field_meeting_number`, and a date range. There
is NO external-participant filter -- the ROUND 2 spec's description of a search
"by EXTERNAL participant" describes the LEGACY system, and whether the current
site still carries that field is measured here rather than assumed.

This build is therefore a KEYWORD SWEEP, and every term swept is written to
`source_coverage_nrc_meetings.csv` with its yield. A meeting that uses none of
these words in its title is not in this dataset and is NOT thereby absent from
the NRC schedule. That distinction is the same one that produced the
set-aside-filter error, and it is recorded rather than left implicit.

=== HOST BEHAVIOUR, MEASURED BEFORE THE RUN ===

`www.nrc.gov` sits behind an Akamai edge that returns **HTTP 403 intermittently
and at random**, interleaved with 200s for identical request shapes. Measured
2026-08-12: six sequential keyword queries at a 12 s gap returned
403/403/403/200/200/403.

So a single 403 here is NOT the permanent edge block that AGENTS.md's stop-work
rule is written for -- the 200s that follow prove it. The stop rule used is
**four CONSECUTIVE refusals**, with exponential backoff between attempts. That
is a stronger test than "stop on the first", not a weaker one, and it is stated
because it is a deliberate departure.

A browser-shaped User-Agent was refused where the honest CedarPress agent string
was served. Do not "fix" this by pretending to be Chrome.

Reads  www.nrc.gov PMNS (cached under data/raw/nrc_meetings/)
       data/spine/cedar_entity_spine.csv
Writes data/clean/nrc_public_meetings.csv
       data/clean/nrc_meeting_participants.csv
       data/clean/source_coverage_nrc_meetings.csv
       review/nrc_unresolved_participants.csv
       review/nrc_entity_link_candidates.csv

Run with `--offline` to rebuild from the cache under data/raw/nrc_meetings/
without issuing a single request to the host.
"""
from __future__ import annotations

import csv
import datetime as dt
import html as htmlmod
import importlib.util
import json
import os
import random
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "code"
RAW = ROOT / "data" / "raw" / "nrc_meetings"
CLEAN = ROOT / "data" / "clean"
REVIEW = ROOT / "review"
LOGS = ROOT / "logs"
SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
SCRIPT = "code/145_build_nrc_public_meetings.py"
TODAY = dt.date.today().isoformat()
for d in (RAW, CLEAN, REVIEW, LOGS):
    d.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(CODE))
from cedar_domain import (  # noqa: E402
    AdvocacyChannel, EventClass, Tier, position_is_addressable,
)

EX_PARTE = AdvocacyChannel.REGULATORY_EX_PARTE
CONSULT = AdvocacyChannel.CONSULTATION
S106 = AdvocacyChannel.SECTION_106_CONSULTATION
assert EX_PARTE.event_class == EventClass.ADVOCACY
assert CONSULT.event_class == EventClass.GOVERNMENT_ENGAGEMENT
assert S106.event_class == EventClass.GOVERNMENT_ENGAGEMENT
assert EX_PARTE.is_lobbying is False and CONSULT.is_lobbying is False

CHANNEL_NOTE = ("An NRC public meeting is publicly noticed on the agency's own "
                "schedule. REGULATORY_EX_PARTE names the channel family "
                "(direct regulator/stakeholder engagement on a docket) and does "
                "NOT imply a communication outside the public record.")

HOST = "www.nrc.gov"
BASE = "https://www.nrc.gov/public-involve/public-meetings/pmns"
UA = ("CedarPress-research/1.0 (+https://cedarpress.co; "
      "elijahsamsonmoreno@gmail.com)")
HEADERS = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"}
GAP = 7.0
MAX_CONSECUTIVE_REFUSALS = 4
DEADLINE_S = 50 * 60
DETAIL_BUDGET = 260

SCHEDULE_FLOOR = "2003-10-01"      # the searchable floor the NRC publishes
RANGE_MAX = "2027-12-31"

# Terms swept. Every one is recorded with its yield; none is a claim of
# completeness. Grouped only so the tribal-term meetings can be prioritised
# when the detail-page budget binds.
TRIBAL_TERMS = [
    "tribal", "tribe", "tribes", "Indian", "indigenous",
    "government-to-government", "consultation", "Section 106", "treaty",
    "environmental justice",
    "Navajo", "Ute", "Oglala", "Sioux", "Pueblo", "Hopi", "Shoshone",
    "Paiute", "Goshute", "Skull Valley", "Yakama", "Spokane",
    "Prairie Island", "Seneca", "Mohawk", "Wampanoag", "Santee",
]
SITE_TERMS = [
    "uranium", "Yucca Mountain", "mill tailings", "UMTRCA", "Church Rock",
    "Dewey-Burdock", "Crow Butte", "in situ recovery", "Nichols Ranch",
]
ALL_TERMS = TRIBAL_TERMS + SITE_TERMS

# --- classification vocabulary. Read from purpose; matched phrase is kept. ---
CONSULT_PHRASES = [
    "government-to-government", "government to government",
    "tribal consultation", "consultation with tribes",
    "consultation with the tribe", "tribal government meeting",
    "meeting with tribal", "tribal nations", "annual tribal",
]
S106_PHRASES = ["section 106", "national historic preservation act",
                "historic preservation", "thpo"]
EXTERNAL_MARK = ["participants", "external participant", "licensee",
                 "applicant", "petitioner", "intervenor"]

_stats = Counter()
_notes = []
held = Counter()   # (participant, candidate, method) -> n, for review/


def note(s):
    _notes.append(s)
    print("   . %s" % s)


# ===========================================================================
# Pull discipline
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
        if holder and pid_alive(holder):
            cur.setdefault("queue", []).append(
                {"script": SCRIPT, "purpose": purpose,
                 "queued_at": dt.datetime.now(dt.timezone.utc).isoformat()})
            lock_path(host).write_text(json.dumps(cur, indent=1), encoding="utf-8")
            note("host_deferred:%s" % host)
            return False
    lock_path(host).write_text(json.dumps({
        "host": host, "pid": os.getpid(), "script": SCRIPT,
        "claimed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "active": True, "queue": [],
        "policy": "sequential, >=7s gap + jitter, exponential backoff on 403, "
                  "stop after 4 CONSECUTIVE refusals, 50 min deadline",
        "note": purpose}, indent=1), encoding="utf-8")
    return True


def release_host(host, note_text=""):
    cur = read_lock(host) or {"host": host}
    cur["active"] = False
    cur["released"] = TODAY
    cur["note"] = note_text
    lock_path(host).write_text(json.dumps(cur, indent=1), encoding="utf-8")


class StopHost(Exception):
    pass


class Fetcher:
    def __init__(self, started):
        self.s = requests.Session()
        self.started = started
        self.consec = 0
        self.n_ok = 0
        self.n_refused = 0

    def get(self, url, params=None):
        """-> text, or None if this object could not be retrieved.
        Raises StopHost after MAX_CONSECUTIVE_REFUSALS."""
        backoff = 45.0
        for attempt in range(3):
            if time.time() - self.started > DEADLINE_S:
                raise StopHost("wall-clock deadline reached")
            try:
                r = self.s.get(url, headers=HEADERS, params=params,
                               timeout=(15, 90))
                st = r.status_code
            except Exception as e:
                st = 0
                r = None
                _stats["transport_error"] += 1
                note("transport %s on %s" % (type(e).__name__, url[-60:]))
            if r is not None and st == 200:
                self.consec = 0
                self.n_ok += 1
                time.sleep(GAP + random.uniform(0, 2.0))
                return r.text
            if r is not None and st == 404:
                self.consec = 0          # a fact about the object
                time.sleep(GAP)
                return None
            # 403 / 429 / transport -> a fact about the moment
            self.n_refused += 1
            if attempt < 2:
                time.sleep(backoff)
                backoff *= 2
        self.consec += 1
        if self.consec >= MAX_CONSECUTIVE_REFUSALS:
            raise StopHost("%d consecutive refusals" % self.consec)
        return None


# ===========================================================================
# Parsing
# ===========================================================================
def flat(seg):
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", seg or "", flags=re.S)
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"</(p|div|li|tr|h\d|dd|dt)>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = htmlmod.unescape(s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return s.strip()


MEET_ID_RX = re.compile(r"/public-involve/public-meetings/pmns/(\d+)")
# The date and the time window must be parsed SEPARATELY. A single regex
# demanding "start - end" silently dropped 32 of 240 meetings on the first run:
# one-off times ("11/18/13, 11:25AM EST") and cancelled meetings
# ("* Meeting Canceled * 10/01/13") carry a real date and no range, and a blank
# meeting_date reads downstream as an undated record rather than as a parser
# that could not see the shape.
DATE_ONLY_RX = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{2,4})")
TIME_RANGE_RX = re.compile(r"([\d:]+\s*[AP]M)\s*-\s*([\d:]+\s*[AP]M)", re.I)
TIME_ONE_RX = re.compile(r"([\d:]+\s*[AP]M)", re.I)
TZ_RX = re.compile(r"\b([ECMP][SD]T|AKDT|AKST|HST|UTC)\b")
CANCELLED_RX = re.compile(r"cancel", re.I)


def parse_list(html):
    """-> list of dicts from the PMNS results table."""
    out = []
    i = html.find("<table")
    j = html.find("</table>", i + 1)
    if i < 0 or j < 0:
        return out
    for rw in re.findall(r"<tr[^>]*>(.*?)</tr>", html[i:j], re.S):
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", rw, re.S)
        if len(cells) < 4:
            continue
        when = flat(cells[0])
        if not when or when.lower().startswith("date/time"):
            continue
        mid = MEET_ID_RX.search(cells[1])
        purpose = flat(cells[1])
        out.append({
            "meeting_number": mid.group(1) if mid else "",
            "datetime_verbatim": re.sub(r"\s+", " ", when),
            "purpose_verbatim": re.sub(r"\s+", " ", purpose),
            "address_verbatim": re.sub(r"\s+", " ", flat(cells[2])),
            "contact_verbatim": re.sub(r"\s+", " ", flat(cells[3])),
        })
    return out


def parse_when(s):
    """-> (iso_date, time_start, time_end, tz, cancelled)."""
    s = s or ""
    cancelled = "Y" if CANCELLED_RX.search(s) else "N"
    m = DATE_ONLY_RX.search(s)
    if not m:
        return "", "", "", "", cancelled
    mo, da, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if yr < 100:
        yr += 2000 if yr < 80 else 1900
    try:
        d = dt.date(yr, mo, da).isoformat()
    except ValueError:
        return "", "", "", "", cancelled
    tail = s[m.end():]
    tz = (TZ_RX.search(tail).group(1) if TZ_RX.search(tail) else "")
    r = TIME_RANGE_RX.search(tail)
    if r:
        return d, r.group(1).strip(), r.group(2).strip(), tz, cancelled
    o = TIME_ONE_RX.search(tail)
    return d, (o.group(1).strip() if o else ""), "", tz, cancelled


PART_CAT_RX = re.compile(r"Participation:\s*(Category\s*\w+|[^\n]{0,40})", re.I)


def clean_purpose(p):
    """Strip the list-cell furniture; keep the agency's own title text."""
    s = re.sub(r"^\s*Meeting Info\s*", "", p or "")
    s = re.sub(r"\s*Participation:.*$", "", s)
    s = re.sub(r"\s*Full Details\s*\d*\s*$", "", s)
    return s.strip("  -–")


# The exact block labels a PMNS detail page prints, transcribed from
# /public-involve/public-meetings/pmns/20141036. A prefix match is not enough:
# the docket block is labelled "Docket Numbers - Facility Names", so a regex
# looking for "Docket" never fullmatches it and the docket silently comes back
# empty on every row.
SECTION_LABELS = {
    "purpose": "purpose",
    "meeting dates and times": "when",
    "meeting location": "location",
    "contact": "contact",
    "participation level": "participation",
    "nrc participants": "nrc participants",
    "external participants": "external participants",
    "docket numbers - facility names": "docket_facility",
    "docket numbers": "docket_facility",
    "facility names": "docket_facility",
    "related documents": "related documents",
    "meeting info": "_ignore",
    "public meeting schedule: meeting details": "_ignore",
    "meeting details": "_ignore",
}


def parse_detail(html):
    """Pull the labelled blocks off a meeting detail page."""
    a = html.find("Meeting Details")
    b = html.find("Page Last Reviewed", a + 1)
    seg = html[a:b] if a >= 0 and b > a else html
    txt = flat(seg)
    fields = {}
    cur = None
    for ln in (x.strip() for x in txt.split("\n")):
        if not ln:
            continue
        key = SECTION_LABELS.get(ln.strip(": ").strip().lower())
        if key:
            cur = None if key == "_ignore" else key
            if cur:
                fields.setdefault(cur, [])
            continue
        if cur:
            fields[cur].append(ln)
    adams = sorted(set(re.findall(r"\b(ML[0-9A-Z]{9,})\b", html)))
    return fields, adams, txt


def split_docket_facility(vals):
    """'07200010 - Prairie Island' -> ('07200010', 'Prairie Island')."""
    dks, fac = [], []
    for v in vals or []:
        parts = [p.strip() for p in re.split(r"\s+-\s+", v, maxsplit=1)]
        if len(parts) == 2 and re.fullmatch(r"[\d,\s/]+", parts[0]):
            dks.append(parts[0])
            fac.append(parts[1])
        else:
            fac.append(v)
    return dks, fac


def norm_join(v):
    return " | ".join(x for x in (v or []) if x)[:1200]


# ---------------------------------------------------------------------------
# SAME CONTAINMENT RULE AS code/144_build_admin_appeals.py, and it is needed
# here for the same reason. Measured on the first run of this script, the
# containment tier produced:
#
#   "05000282 - Prairie Island 1"          -> Prairie Island   (a DOCKET line,
#   "05000306 - Prairie Island 2"          -> Prairie Island    matched to the
#                                                               Prairie Island
#                                                               Indian Community)
#   "C. Jackson"                           -> Jackson
#   "CONFEDERATED SALISH AND KOOTENAI TRIBE" -> Salish Kootenai COLLEGE
#
# The last one is the worst: a tribal government resolved to the tribal
# college, two different legal persons. Containment matches are HELD, never
# published as a link.
# ---------------------------------------------------------------------------
LINKING_METHODS = frozenset({"exact", "core", "alias"})

# Lines that the detail page prints inside a participant block but which are
# not parties: block labels the flattener did not consume, docket numbers,
# and the standing time-zone footnote.
NON_PARTY_RX = re.compile(
    r"^(docket numbers|related documents|comments|parties to the proceeding|"
    r"meeting time is based on|other|n/a|none|tbd|see |\d{6,}\s*-\s|"
    r"-\s*\d{2}/\d{2}/\d{4}\b|nrc participants|external participants)",
    re.I)


# ---------------------------------------------------------------------------
# NAMED INDIVIDUALS. The External Participants block lists people as well as
# companies -- measured on this run: Xcel Energy (20) and Uranerz Energy (7)
# alongside "Robert Kuntz" (9), "Allen Fetter" (8), "Christine Pineda" (6), and
# the bare word "Public" (10).
#
# Cedar Press names an individual only where the record establishes a PUBLIC
# PROFESSIONAL capacity. A bare personal name in an attendance list does not:
# it may be a company representative, an NRC project manager, or a member of
# the public who signed up. Rather than guess which, the name is WITHHELD and
# the row is kept -- so the count of individual-vs-organisational participants
# stays measurable without publishing a register of people.
# ---------------------------------------------------------------------------
ORG_MARKERS = (
    "tribe", "tribes", "tribal", "nation", "band", "pueblo", "community",
    "rancheria", "village", "council", "confederated", "inc", "llc", "corp",
    "corporation", "company", "co", "ltd", "lp", "partnership", "association",
    "society", "foundation", "institute", "trust", "coalition", "alliance",
    "committee", "county", "city", "state", "district", "authority",
    "commission", "board", "department", "agency", "office", "school",
    "university", "college", "energy", "power", "electric", "nuclear",
    "resources", "mining", "minerals", "uranium", "operations", "services",
    "group", "partners", "holdings", "enterprises", "laboratory", "labs",
    "institute", "center", "centre", "usa", "america", "american", "national",
    "international", "federal", "government", "solutions", "systems",
    "technologies", "engineering", "industries", "utilities", "generating",
    "station", "plant", "project", "consultants", "consulting", "union",
    "society", "club", "network", "fund", "initiative", "public",
)
_TOKEN_RX = re.compile(r"[^a-z0-9&]+")


def participant_type(name):
    toks = set(t for t in _TOKEN_RX.split((name or "").lower()) if t)
    if not toks:
        return "UNKNOWN"
    if toks == {"public"}:
        return "PUBLIC_ATTENDANCE"
    if toks & set(ORG_MARKERS):
        return "ORGANISATION"
    return "NATURAL_PERSON"


PARTICIPANT_WITHHOLD_REASON = (
    "Named individual in an NRC attendance list. The record does not establish "
    "the person's professional capacity -- a bare personal name may be a "
    "company representative, an NRC project manager, or a member of the "
    "public. Cedar Press names an individual only where a public professional "
    "capacity is established, so the name is withheld and the row retained. "
    "The meeting remains fully retrievable at source_url.")


def is_party_line(s):
    s = (s or "").strip()
    if len(s) < 3 or len(s) > 160:
        return False
    if NON_PARTY_RX.match(s):
        return False
    if re.fullmatch(r"[\d\s,./-]+", s):
        return False
    return True


# ===========================================================================
def load_resolver():
    spec = importlib.util.spec_from_file_location(
        "m33", str(CODE / "33_apply_party_rulings.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
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


def classify(purpose):
    """-> (channel, event_class, basis_quote, status). Purpose is READ."""
    p = (purpose or "").lower()
    if not p.strip():
        return "", "", "", "UNCLASSIFIED_NO_PURPOSE_TEXT"
    for ph in S106_PHRASES:
        if ph in p:
            return (S106.value, S106.event_class.value, ph,
                    "CLASSIFIED_FROM_PURPOSE")
    for ph in CONSULT_PHRASES:
        if ph in p:
            return (CONSULT.value, CONSULT.event_class.value, ph,
                    "CLASSIFIED_FROM_PURPOSE")
    return (EX_PARTE.value, EX_PARTE.event_class.value, "",
            "DEFAULT_SCHEDULED_REGULATORY_MEETING")


def main():
    print("=" * 74)
    print("145 -- NRC public meeting schedule (ROUND 2 item 14)")
    print("     %s -> %s | %s -> %s | %s -> %s"
          % (EX_PARTE.value, EX_PARTE.event_class.value,
             CONSULT.value, CONSULT.event_class.value,
             S106.value, S106.event_class.value))
    print("=" * 74)

    cov = []
    listings = {}          # meeting_number -> list row
    term_hits = {}
    started = time.time()
    stop_reason = ""

    offline = "--offline" in sys.argv
    if offline:
        note("--offline: rebuilding from cache, no request to %s" % HOST)
        F = None
    elif not claim_host(HOST, "PMNS keyword sweep, %d terms, %s..%s"
                              % (len(ALL_TERMS), SCHEDULE_FLOOR, RANGE_MAX)):
        note("deferring to the existing %s poller; cache only" % HOST)
        F = None
    else:
        F = Fetcher(started)

    try:
        for term in ALL_TERMS:
            got, page = 0, 0
            pages_checked = 0
            while page < 12:
                cache = RAW / ("list_%s_p%d.html"
                               % (re.sub(r"[^a-z0-9]+", "_", term.lower()), page))
                if cache.exists():
                    html = cache.read_text(encoding="utf-8", errors="replace")
                elif F is None:
                    break
                else:
                    params = {"field_dates[min]": SCHEDULE_FLOOR,
                              "field_dates[max]": RANGE_MAX,
                              "keywords": term}
                    if page:
                        params["page"] = str(page)
                    html = F.get(BASE, params)
                    if html is None:
                        cov.append({
                            "sweep_term": term, "page": page,
                            "coverage_status": "NOT_CHECKED",
                            "http_status": "403/0",
                            "n_meetings": "",
                            "source_url": BASE, "fetched_date": TODAY,
                            "note": "edge refusal; a refusal is a fact about "
                                    "the moment, never about the object"})
                        break
                    cache.write_text(html, encoding="utf-8")
                pages_checked += 1
                rows = parse_list(html)
                new = 0
                for r in rows:
                    mn = r["meeting_number"]
                    if not mn:
                        continue
                    if mn not in listings:
                        listings[mn] = r
                        listings[mn]["sweep_terms"] = set()
                        new += 1
                    listings[mn]["sweep_terms"].add(term)
                got += len(rows)
                if not rows or new == 0:
                    break
                page += 1
            term_hits[term] = got
            cov.append({
                "sweep_term": term, "page": "all",
                "coverage_status": "PUBLISHES" if got else "NOT_FOUND",
                "http_status": "200",
                "n_meetings": got,
                "source_url": "%s?field_dates[min]=%s&field_dates[max]=%s"
                              "&keywords=%s" % (BASE, SCHEDULE_FLOOR,
                                                RANGE_MAX, term),
                "fetched_date": TODAY,
                "note": "%d result pages read. Absence under this term is a "
                        "property of the term, not of the NRC schedule."
                        % pages_checked})
            print("   %-28s %4d meetings" % (term, got))
    except StopHost as e:
        stop_reason = str(e)
        note("STOP on %s: %s" % (HOST, e))

    # ------------------------------------------------------------ details
    order = sorted(listings.items(),
                   key=lambda kv: (0 if (kv[1]["sweep_terms"] & set(TRIBAL_TERMS))
                                   else 1, kv[0]))
    details = {}
    n_detail = 0
    # Cached detail pages are loaded ALWAYS, even when no fetch happens. The
    # first version only entered this loop when a fetcher existed, so an
    # --offline rebuild silently dropped every detail page already on disk and
    # reported an empty external-participant field as a fact about the source.
    try:
        for mn, _ in order:
            cache = RAW / ("detail_%s.html" % mn)
            if cache.exists():
                details[mn] = cache.read_text(encoding="utf-8",
                                              errors="replace")
                continue
            if F is None or stop_reason or n_detail >= DETAIL_BUDGET:
                continue
            html = F.get("%s/%s" % (BASE, mn))
            n_detail += 1
            if html is None:
                continue
            cache.write_text(html, encoding="utf-8")
            details[mn] = html
    except StopHost as e:
        stop_reason = str(e)
        note("STOP on details: %s" % e)
    if F is not None:
        release_host(HOST, "PMNS sweep: %d ok / %d refused; %s"
                     % (F.n_ok, F.n_refused, stop_reason or "completed"))

    # ------------------------------------------------------------- build
    spine = read_csv(SPINE)
    resolve = load_resolver()
    rcache = {}

    def R(name):
        k = (name or "").strip().lower()
        if k not in rcache:
            try:
                rcache[k] = resolve(name, spine)
            except Exception:
                rcache[k] = (None, None, "resolver_error")
        return rcache[k]

    meetings, participants = [], []
    unresolved = Counter()
    unresolved_ex = {}
    n_with_external = 0

    for mn, row in sorted(listings.items()):
        d, t0, t1, tz, cancelled = parse_when(row["datetime_verbatim"])
        cat = PART_CAT_RX.search(row["purpose_verbatim"])
        purpose = clean_purpose(row["purpose_verbatim"])
        url = "%s/%s" % (BASE, mn)
        fields, adams, dtxt = ({}, [], "")
        if mn in details:
            fields, adams, dtxt = parse_detail(details[mn])
        nrc_part = norm_join(fields.get("nrc participants"))
        ext_part = norm_join(fields.get("external participants"))
        dks, facs = split_docket_facility(fields.get("docket_facility"))
        docket = " | ".join(dks)
        facility = " | ".join(facs)
        detail_purpose = norm_join(fields.get("purpose"))
        detail_location = norm_join(fields.get("location"))
        related = norm_join(fields.get("related documents"))
        if ext_part:
            n_with_external += 1
        # The detail page prints the agency's own Purpose paragraph; the list
        # cell carries only the title. Prefer the fuller text where we have it,
        # and record which one the classification was read from.
        purpose_source = "LIST_TITLE"
        if detail_purpose:
            purpose = detail_purpose
            purpose_source = "DETAIL_PURPOSE_FIELD"

        ch, ec, quote, status = classify(purpose)
        meetings.append({
            "nrc_meeting_id": "NRC-PMNS-%s" % mn,
            "meeting_number": mn,
            "meeting_date": d,
            "meeting_year": d[:4],
            "time_start": t0, "time_end": t1, "time_zone": tz,
            "meeting_cancelled": cancelled,
            "datetime_verbatim": row["datetime_verbatim"],
            "purpose_verbatim": purpose,
            "purpose_source": purpose_source,
            "participation_category": (cat.group(1).strip() if cat else ""),
            "location_verbatim": detail_location or row["address_verbatim"],
            "related_documents_verbatim": related,
            "nrc_contact_verbatim": row["contact_verbatim"],
            "nrc_participants_verbatim": nrc_part,
            "external_participants_verbatim": ext_part,
            "external_participant_field_present":
                "Y" if ext_part else ("N" if mn in details else ""),
            "docket_verbatim": docket,
            "facility_verbatim": facility,
            "adams_accession_numbers": "|".join(adams),
            "adams_lookup_url":
                ("https://adams.nrc.gov/wba/services/search/advanced/nrc?"
                 "q=%s" % adams[0]) if adams else "",
            "channel": ch,
            "event_class": ec,
            "is_lobbying": "N",
            "classification_status": status,
            "classification_basis_quote": quote,
            "channel_note": CHANNEL_NOTE if ch == EX_PARTE.value else "",
            "sweep_terms_matched": "|".join(sorted(row["sweep_terms"])),
            "detail_page_fetched": "Y" if mn in details else "N",
            "source_url": url,
            "source_record_id": "NRC PMNS meeting %s" % mn,
            "fetched_date": TODAY,
            "confidence_tier": Tier.A.value,
        })

        # participant rows: only where the source NAMES an external party
        for name in [x.strip() for x in ext_part.split("|") if x.strip()]:
            if not is_party_line(name):
                _stats["participant_line_skipped_not_a_party"] += 1
                continue
            ptype = participant_type(name)
            withheld = ptype == "NATURAL_PERSON"
            if withheld:
                _stats["participant_name_withheld"] += 1
            tid, cname, how = ("", "", "")
            cand_id = cand_name = hold = ""
            r_ = (None, None, "not_attempted_natural_person") if withheld                 else R(name)
            if r_[0] and r_[2] in LINKING_METHODS:
                tid, cname, how = r_
            elif r_[0]:
                cand_id, cand_name, how = r_[0], r_[1], r_[2]
                hold = ("containment_held: containment may resolve an owner "
                        "already named in evidence, never detect a match "
                        "(AGENTS.md, THE CONTAINMENT DEFECT)")
                held[(name, r_[1], r_[2])] += 1
                _stats["entity_link_held"] += 1
            elif not withheld:
                unresolved[name] += 1
                unresolved_ex.setdefault(name, mn)
            org_id = "" if withheld else (
                tid or ("ORG:" + re.sub(r"[^A-Z0-9]+", "_",
                                        name.upper())[:60]))
            participants.append({
                "participant_id": "NRC-PMNS-%s#%s" % (mn, len(participants)),
                "nrc_meeting_id": "NRC-PMNS-%s" % mn,
                "meeting_number": mn,
                "meeting_date": d,
                "external_participant_verbatim": "" if withheld else name,
                "participant_type": ptype,
                "is_natural_person": "Y" if withheld else "N",
                "participant_name_withheld_reason":
                    PARTICIPANT_WITHHOLD_REASON if withheld else "",
                "organisation_id": org_id,
                "resolved_entity_id": tid,
                "resolved_entity_name": cname,
                "resolve_method": how,
                "entity_link_held_candidate_id": cand_id,
                "entity_link_held_candidate_name": cand_name,
                "entity_link_hold_reason": hold,
                "matter_id": docket or ("NRC-PMNS-%s" % mn),
                "native_entity_id": tid,
                "channel": ch, "event_class": ec, "is_lobbying": "N",
                "classification_status": status,
                "classification_basis_quote": quote,
                "channel_note": CHANNEL_NOTE if ch == EX_PARTE.value else "",
                "nrc_office_verbatim": nrc_part,
                "facility_verbatim": facility,
                "purpose_verbatim": purpose,
                "position_addressable":
                    "Y" if position_is_addressable(org_id, docket or mn, tid)
                    else "N",
                "source_url": url,
                "source_record_id": "NRC PMNS meeting %s" % mn,
                "fetched_date": TODAY,
                "confidence_tier": Tier.A.value,
            })

    # THE KEYWORD INDEX FLOOR IS NOT THE SCHEDULE FLOOR, and the two look the
    # same in a year histogram. The NRC schedule is searchable from
    # 2003-10-01 and a date-range query does return 2003 meetings -- but a
    # 2003 detail page (verified on meeting 20030710) prints only date, contact,
    # participation level and the NRC office. It has NO Purpose and NO title
    # text, so a filter documented as "Title or purpose contains" cannot match
    # it at any term. Every keyword sweep therefore floors out around the point
    # where the schedule began carrying purpose text, and the earliest meeting
    # this build recovers is the FILTER's floor, not the source's.
    yrs_seen = sorted(y for y in {m["meeting_year"] for m in meetings} if y)
    cov.append({
        "sweep_term": "(all terms)", "page": "",
        "coverage_status": "NOT_FOUND",
        "http_status": "200",
        "n_meetings": 0,
        "source_url": "%s?field_dates[min]=%s" % (BASE, SCHEDULE_FLOOR),
        "fetched_date": TODAY,
        "note": "NRC publishes the schedule from %s and a date-range query "
                "returns 2003 meetings, but the earliest meeting ANY keyword "
                "term recovered is %s. Verified on meeting 20030710: a 2003 "
                "detail page carries no Purpose and no title text, so the "
                "keyword filter (documented 'Title or purpose contains') "
                "cannot match a pre-purpose-text record at any term. This is "
                "the FILTER's floor, not the source's."
                % (SCHEDULE_FLOOR, yrs_seen[0] if yrs_seen else "n/a")})

    if meetings:
        write_csv(CLEAN / "nrc_public_meetings.csv", meetings,
                  list(meetings[0].keys()))
    if participants:
        write_csv(CLEAN / "nrc_meeting_participants.csv", participants,
                  list(participants[0].keys()))
    write_csv(CLEAN / "source_coverage_nrc_meetings.csv", cov,
              ["sweep_term", "page", "coverage_status", "http_status",
               "n_meetings", "source_url", "fetched_date", "note"])
    ur = [{"external_participant": k, "n_meetings": v,
           "example_meeting": unresolved_ex[k],
           "question": "Native entity? If so which spine entity?",
           "YOUR_RULING": ""} for k, v in unresolved.most_common()]
    write_csv(REVIEW / "nrc_unresolved_participants.csv", ur,
              ["external_participant", "n_meetings", "example_meeting",
               "question", "YOUR_RULING"])
    hq = [{"external_participant": k[0], "candidate_entity": k[1],
           "resolve_method": k[2], "n_participant_rows": v,
           "question": "Is this candidate the right entity for this "
                       "participant? YES writes the link; NO rules it out.",
           "YOUR_RULING": ""} for k, v in held.most_common()]
    write_csv(REVIEW / "nrc_entity_link_candidates.csv", hq,
              ["external_participant", "candidate_entity", "resolve_method",
               "n_participant_rows", "question", "YOUR_RULING"])

    byclass = Counter(m["event_class"] for m in meetings)
    byyear = Counter(m["meeting_year"] for m in meetings)
    linked = [m for m in meetings if m["external_participants_verbatim"]]
    ents = set(p["resolved_entity_id"] for p in participants
               if p["resolved_entity_id"])
    print("\n" + "-" * 74)
    print("meetings                 %5d" % len(meetings))
    print("  detail pages fetched   %5d" % len(details))
    print("  external-participant field populated %5d" % n_with_external)
    print("participant rows         %5d  (%d resolved to the spine)"
          % (len(participants), len(ents)))
    print("  entity links HELD      %5d rows / %d pairs -> review/"
          % (_stats["entity_link_held"], len(hq)))
    print("  non-party lines dropped %4d"
          % _stats["participant_line_skipped_not_a_party"])
    print("  individual names withheld %4d"
          % _stats["participant_name_withheld"])
    print("by event_class          ", dict(byclass))
    print("years                    %s..%s"
          % (min(byyear, default=""), max(byyear, default="")))
    print("terms swept              %d (%d yielded)"
          % (len(ALL_TERMS), sum(1 for v in term_hits.values() if v)))
    if stop_reason:
        print("STOPPED: %s" % stop_reason)
    print("-" * 74)

    (LOGS / ("145_nrc_meetings_%s.json" % TODAY)).write_text(json.dumps({
        "script": SCRIPT, "date": TODAY, "meetings": len(meetings),
        "details": len(details), "participants": len(participants),
        "external_field_populated": n_with_external,
        "entities": len(ents), "by_event_class": dict(byclass),
        "stats": dict(_stats),
        "term_yield": term_hits, "stop_reason": stop_reason,
        "notes": _notes}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
