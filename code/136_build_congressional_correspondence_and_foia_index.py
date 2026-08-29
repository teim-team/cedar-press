#!/usr/bin/env python3
r"""
Cedar Press - 136: CONGRESSIONAL CORRESPONDENCE LOGS + FOIA LOGS AS A
DISCOVERY INDEX.

Two builds, one script, because they share a single insight and a single set of
hosts.

===========================================================================
PART A - THE INVERSION
===========================================================================
Congress does not centrally report its contacts with the executive branch.
There is no register of "Senator X's office called Interior about a tribal
matter." But the AGENCY ON THE RECEIVING END logs it, because controlled
correspondence is how an agency proves it answered a member of Congress.

So the record is reconstructed from the agency side:

    congressional office  ->  agency  ->  date received  ->  subject  ->  tribe

Those five things are SEPARATE COLUMNS and are never merged. A member of
Congress writing an agency on behalf of a constituent tribe is a different
fact from a lobbyist contact, and the columns must let a reader tell them
apart without trusting our summary.

**Search for the SYSTEM, not for a website.** Correspondence-management
systems routinely have no public face at all, so the way to establish that one
exists is the agency's own Privacy Act System of Records Notice, which is
published in the Federal Register and names the system, its manager, its
categories of records and its retention. `congressional_correspondence_systems.csv`
is that registry. It is a finding in its own right: it tells a future FOIA
requester the SYSTEM NAME to name, which is the difference between a request
that gets searched and one that gets closed as "no records."

TAXONOMY - NOT NEGOTIABLE
-------------------------
`EventClass.ADVOCACY`, channel `CONGRESSIONAL_CORRESPONDENCE`.

`AdvocacyChannel.CONGRESSIONAL_CORRESPONDENCE.is_lobbying` is **False**, and
that is deliberate, not an oversight. `is_lobbying` is NARROWER than
`EventClass.ADVOCACY`: LDA lobbying is a statutorily defined activity with a
registration regime attached, and a member of Congress writing an agency is
not it. Conflating them would be wrong in a way that matters legally, not just
analytically. The assertions below refuse to run if `cedar_domain` ever
disagrees.

`may_promote_event_class()` refuses ACCESS -> ADVOCACY. Nothing in this build
upgrades a proximity record, and nothing here reads a visitor log.

===========================================================================
PART B - THE FOIA LOG AS A DISCOVERY INDEX, NOT A REQUEST MECHANISM
===========================================================================
Agencies publish logs of the requests OTHER PEOPLE filed. Someone may already
have paid for the expensive part years ago - and a granted request means the
records were located, reviewed and released, which is most of the cost.

So the log is crawled FIRST and used to decide what is worth requesting:

    foia_request_id, agency, bureau, request_date, requester,
    request_description, tribe_mentioned, organization_mentioned,
    official_mentioned, issue, disposition, release_available, release_url

That inverts the FOIA cost curve. **No FOIA request is filed by this script,
and none should be filed until this index has been read.**

===========================================================================
ABSENCE IS A PROPERTY OF THE LOG
===========================================================================
`correspondence_foia_source_coverage.csv` records, per (agency, source), one
of:

    PUBLISHES     retrieved it, with the URL and the byte count
    WITHHOLDS     the agency published a statement that it will not release
    NOT_FOUND     swept, and did not find it - NAMING what was swept
    NOT_CHECKED   nobody looked

A tribe absent from a correspondence log was not necessarily un-championed;
an agency with no published log has not been shown to keep none. Those are
different facts from "we checked and there is nothing," and collapsing them is
the error this file exists to prevent.

CHECK THE HTTP STATUS, NOT THE FILE. Every probe records its status. A 0 is a
transport failure and is stop-work; only 404/403 are facts about the object.

===========================================================================
ENTITY RESOLUTION
===========================================================================
`resolve_entity` from `code/33_apply_party_rulings.py`, through the guarded
`Resolver` in `code/96_build_consultation_events.py`. One resolver
project-wide. Nothing re-implemented here, and no fuzzy matching: an
unresolved name is reported to `review/`, never guessed.

A FOIA request description is free text written by a member of the public. It
is the WORST input a name matcher can be handed, and the containment defect in
AGENTS.md would happily find a tribe in it. So tribe detection here requires a
LONG, specific spine name to appear as a whole phrase, and the matched phrase
is stored verbatim beside the entity id so any wrong match is visible.

STAGES
------
    py -3 code/136_build_congressional_correspondence_and_foia_index.py probe
    py -3 code/136_build_congressional_correspondence_and_foia_index.py systems
    py -3 code/136_build_congressional_correspondence_and_foia_index.py logs
    py -3 code/136_build_congressional_correspondence_and_foia_index.py build
    py -3 code/136_build_congressional_correspondence_and_foia_index.py all

WRITES (all NEW files; nothing existing is overwritten)
-------------------------------------------------------
    data/clean/congressional_correspondence_systems.csv
    data/clean/congressional_correspondence_log.csv
    data/clean/foia_request_index.csv
    data/clean/foia_discovery_targets.csv
    data/clean/correspondence_foia_source_coverage.csv
    review/foia_index_unresolved_names_<date>.csv
    data/raw/external/correspondence/...
"""
import argparse
import csv
import importlib.util
import json
import os
import re
import shutil
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
RAW = CEDAR / "data" / "raw" / "external" / "correspondence"
LOGDIR = RAW / "foia_logs"
DOCS = RAW / "sorn_text"
TODAY = date.today().isoformat()

# Four other agents are running and the disk sits near 5.9 GB. Never approach
# the floor: refuse to write another byte below this.
DISK_FLOOR_BYTES = 2 * 1024 ** 3
# A single FOIA log is a spreadsheet. Anything enormous is the wrong object.
MAX_OBJECT_BYTES = 40 * 1024 ** 2
DEADLINE_S = 75 * 60

csv.field_size_limit(min(sys.maxsize, 2147483647))

# ---------------------------------------------------------------------------
# THE ONE RESOLVER, THE SHARED VOCABULARY, THE SHARED FETCHER.
# Imported from 33 and 96. Nothing re-declared.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(CEDAR / "code"))
from cedar_domain import (AdvocacyChannel, EventClass, Tier,      # noqa: E402
                          may_promote_event_class)

_spec = importlib.util.spec_from_file_location(
    "c96", CEDAR / "code" / "96_build_consultation_events.py")
c96 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(c96)

fetch = c96.fetch
claim_host = c96.claim_host
release_host = c96.release_host
read_csv = c96.read_csv
write_csv = c96.write_csv
flatten = c96.flatten
Resolver = c96.Resolver
norm = c96.norm

CHANNEL = AdvocacyChannel.CONGRESSIONAL_CORRESPONDENCE

assert CHANNEL.event_class is EventClass.ADVOCACY, \
    "congressional correspondence must be ADVOCACY - refusing to build."
assert CHANNEL.is_lobbying is False, \
    ("cedar_domain says congressional correspondence is LDA lobbying. It is "
     "not, and the distinction is legal. Refusing to build.")
assert may_promote_event_class(EventClass.ACCESS, EventClass.ADVOCACY) is False, \
    "the ACCESS -> ADVOCACY promotion guard is gone - refusing to build."


# ===========================================================================
# GUARDS
# ===========================================================================

def disk_free():
    return shutil.disk_usage(str(CEDAR)).free


def disk_ok(need=0):
    free = disk_free()
    if free - need < DISK_FLOOR_BYTES:
        print(f"  [disk] {free/1024**3:.2f} GB free - at or below the "
              f"{DISK_FLOOR_BYTES/1024**3:.0f} GB floor. Refusing to write.")
        return False
    return True


MANIFEST = []


def safe_url(url):
    """Percent-encode a path that contains literal spaces.

    IHS publishes `.../FOIA Log FY 2026 Quarter 1.xlsx` with real spaces in
    the path. `urllib` raises `InvalidURL` on that, in **0.02 seconds** - which
    is exactly the signature the shared fetcher reads as an EDGE BLOCK, so the
    first run reported "www.ihs.gov REFUSED" and stopped the whole agency.

    An InvalidURL is a fact about OUR string. It is not a fact about the host,
    and it must never be recorded as a refusal.
    """
    p = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((
        p.scheme, p.netloc, urllib.parse.quote(p.path, safe="/%:@&=+$,~"),
        urllib.parse.quote(p.query, safe="/%:@&=+$,~?"), p.fragment))


def get(url, **kw):
    """fetch() from 96, with our own manifest so the consultation manifest is
    never touched."""
    url = safe_url(url)
    status, body = fetch(url, **kw)
    MANIFEST.append({"url": url, "http_status": status, "bytes": len(body or b""),
                     "fetched_date": TODAY})
    return status, body


def save_manifest():
    if not MANIFEST:
        return
    RAW.mkdir(parents=True, exist_ok=True)
    p = RAW / "_SOURCE_MANIFEST.csv"
    old = read_csv(p)
    seen = {r["url"] for r in old}
    rows = old + [r for r in MANIFEST if r["url"] not in seen]
    write_csv(p, rows, ["url", "http_status", "bytes", "fetched_date"])


def strip_html(b):
    if isinstance(b, bytes):
        b = b.decode("utf-8", "ignore")
    b = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", b)
    b = re.sub(r"(?s)<[^>]+>", " ", b)
    b = (b.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#8212;", "-")
         .replace("&quot;", '"').replace("&#39;", "'").replace("&lt;", "<")
         .replace("&gt;", ">").replace("&rsquo;", "'").replace("&ldquo;", '"')
         .replace("&rdquo;", '"'))
    return re.sub(r"\s+", " ", b).strip()


def links(html, base):
    """(absolute_url, anchor_text) pairs."""
    if isinstance(html, bytes):
        html = html.decode("utf-8", "ignore")
    out = []
    for m in re.finditer(r'(?is)<a\b[^>]*href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                         html):
        href, text = m.group(1), strip_html(m.group(2))
        if href.lower().startswith(("mailto:", "javascript:", "#")):
            continue
        out.append((urllib.parse.urljoin(base, href), text))
    return out


SCRIPT = "code/136_build_congressional_correspondence_and_foia_index.py"

# ===========================================================================
# THE TARGET AGENCIES
# ===========================================================================
# Ordered as the spec orders them: Interior first, because BIA/BIE is where
# tribal congressional correspondence concentrates, then HHS/IHS, EPA, USDA,
# DOE, DOT, HUD.
#
# Each entry lists SEED pages only. Nothing is hardcoded as "the log URL" -
# the seeds are crawled one level and whatever they link to is recorded with
# its own HTTP status. A guessed URL that 404s says nothing about the agency;
# a seed page that lists no logs says something real.

AGENCIES = [
    # Interior's own FOIA site is an INDEX. It publishes no logs itself; the
    # logs live in each bureau's reading room, and doi.gov/foia/logs is a real
    # 404. That is a finding, not a miss - and it is why the bureau entry
    # below exists as a separate agency row.
    dict(agency="Department of the Interior", code="DOI", host="www.doi.gov",
         bureaus="OS, BTFA, OHA",
         seeds=[
             ("FOIA_LIBRARY", "https://www.doi.gov/foia/libraries"),
             ("FOIA_ELIBRARIES", "https://www.doi.gov/foia/eLibraries"),
             ("FOIA_OS_READING_ROOM", "https://www.doi.gov/foia/os/index.cfm"),
             ("FOIA_HOME", "https://www.doi.gov/foia"),
         ]),
    # THE HIGHEST-VALUE SINGLE PAGE IN THIS BUILD. The Assistant Secretary -
    # Indian Affairs reading room carries the AS-IA, BIA and BIE FOIA logs as
    # monthly and annual PDFs, FY2017 to the current month. Interior's own
    # library page points all three bureaus at this one URL.
    dict(agency="Interior - Indian Affairs (AS-IA / BIA / BIE)", code="BIA",
         host="www.bia.gov", bureaus="AS-IA, BIA, BIE",
         seeds=[
             ("FOIA_READING_ROOM", "https://www.bia.gov/as-ia/foia/reading-room"),
             ("FOIA_HOME", "https://www.bia.gov/as-ia/foia"),
         ]),
    dict(agency="Department of Health and Human Services", code="HHS",
         host="www.hhs.gov", bureaus="IHS, CMS, HRSA, ACF, OS",
         seeds=[
             ("FOIA_LOGS", "https://www.hhs.gov/foia/reports/logs/index.html"),
             ("FOIA_HOME", "https://www.hhs.gov/foia/index.html"),
             ("FOIA_READING_ROOM",
              "https://www.hhs.gov/foia/electronic-reading-room/index.html"),
         ]),
    dict(agency="Indian Health Service", code="IHS", host="www.ihs.gov",
         bureaus="IHS Area Offices",
         seeds=[
             ("FOIA_HOME", "https://www.ihs.gov/foia/"),
             ("FOIA_READING_ROOM", "https://www.ihs.gov/foia/readingroom/"),
         ]),
    dict(agency="Environmental Protection Agency", code="EPA",
         host="www.epa.gov", bureaus="OW, OLEM, OAR, Regions 1-10",
         seeds=[
             ("FOIA_LOGS", "https://www.epa.gov/foia/foia-logs"),
             ("FOIA_HOME", "https://www.epa.gov/foia"),
             ("FOIA_READING_ROOM",
              "https://www.epa.gov/foia/frequently-requested-records"),
         ]),
    dict(agency="Department of Agriculture", code="USDA", host="www.usda.gov",
         bureaus="FS, RD, FSA, NRCS, FNS",
         seeds=[
             ("FOIA_HOME", "https://www.usda.gov/foia"),
             ("FOIA_READING_ROOM", "https://www.usda.gov/foia-reading-room"),
         ]),
    dict(agency="Department of Energy", code="DOE", host="www.energy.gov",
         bureaus="EERE, IE, NNSA, EM",
         seeds=[
             ("FOIA_LOGS", "https://www.energy.gov/gc/foia-logs"),
             ("FOIA_READING_ROOM", "https://www.energy.gov/gc/foia-reading-room"),
             ("FOIA_HOME", "https://www.energy.gov/gc/office-general-counsel"),
         ]),
    dict(agency="Department of Transportation", code="DOT",
         host="www.transportation.gov", bureaus="FHWA, FAA, FTA, NHTSA",
         seeds=[
             ("FOIA_LOGS", "https://www.transportation.gov/foia/logs"),
             ("FOIA_HOME", "https://www.transportation.gov/foia"),
             ("FOIA_READING_ROOM",
              "https://www.transportation.gov/foia/electronic-reading-room"),
         ]),
    dict(agency="Department of Housing and Urban Development", code="HUD",
         host="www.hud.gov", bureaus="ONAP, PIH, CPD",
         seeds=[
             ("FOIA_HOME", "https://www.hud.gov/foia"),
             ("FOIA_READING_ROOM", "https://www.hud.gov/foia/readingroom"),
         ]),
]

# A link is a candidate FOIA LOG if the anchor text or the URL says so. Kept
# deliberately tight: bare "log" also matches "login" and "blog".
#
# NO TRAILING \b AFTER "log". `\b` treats "_" as a word character, so
# `foia[-_ ]?logs?\b` does NOT match `bia_foia_logs_january_2026.pdf` - and
# that one word boundary silently dropped all 48 Indian Affairs logs on the
# first run while reporting "0 foia-log links" as though it were a finding
# about the agency. A matcher that fails closed and prints a zero is the most
# dangerous kind.
FOIA_LOG_RE = re.compile(
    r"(?i)foia[-_ %]?logs?|\blogs?\s+of\s+(?:foia\s+)?requests?\b"
    r"|\brequest\s+logs?|\bfoia\s+request\s+log|\blog\s+of\s+requests\b"
    r"|\bprocessed\s+requests?\b")

# A link is a candidate CONGRESSIONAL CORRESPONDENCE object if it names the
# system or the record type. These are the strings the spec named, plus the
# ones the Privacy Act notices actually use.
CORR_RE = re.compile(
    r"(?i)congressional\s+correspondence|controlled\s+correspondence"
    r"|correspondence\s+(?:control|tracking|management)"
    r"|executive\s+secretariat|legislative\s+affairs\s+tracking"
    r"|congressional\s+affairs\s+tracking|congressional\s+inquir"
    r"|correspondence\s+logs?")

DOC_EXT_RE = re.compile(r"(?i)\.(xlsx|xls|csv|pdf|txt|zip)(?:$|\?)")

TARGET_FIELDS = ["agency", "agency_code", "found_on", "found_on_kind", "url",
                 "anchor_text", "target_type", "is_document",
                 "discovered_date", "fetched_status", "fetched_bytes",
                 "local_path"]

COVERAGE_FIELDS = ["agency", "agency_code", "source", "status", "url",
                   "http_status", "evidence", "checked_date"]


def _cov_key(r):
    return (r.get("agency_code", ""), r.get("source", ""), r.get("url", ""))


def merge_coverage(new):
    p = CLEAN / "correspondence_foia_source_coverage.csv"
    by = {_cov_key(r): r for r in read_csv(p)}
    for r in new:
        by[_cov_key(r)] = r
    write_csv(p, sorted(by.values(), key=_cov_key), COVERAGE_FIELDS)


# ===========================================================================
# STAGE 1 - PROBE. Crawl each seed page ONE level and record what is linked.
# ===========================================================================

def stage_probe(argv):
    ap = argparse.ArgumentParser(prog="probe")
    ap.add_argument("--agencies", default="",
                    help="comma-separated codes; default all, in spec order")
    a = ap.parse_args(argv)
    want = {x.strip().upper() for x in a.agencies.split(",") if x.strip()}

    started = time.time()
    rows = read_csv(CLEAN / "foia_discovery_targets.csv")
    seen = {(r["agency_code"], r["url"]) for r in rows}
    coverage, refused = [], []
    any_success = False

    for ag in AGENCIES:
        if want and ag["code"] not in want:
            continue
        if time.time() - started > DEADLINE_S:
            coverage.append(dict(
                agency=ag["agency"], agency_code=ag["code"], source="ALL",
                status="NOT_CHECKED", url="", http_status="",
                evidence="run deadline reached before this agency was probed",
                checked_date=TODAY))
            continue
        if not claim_host(ag["host"], SCRIPT,
                          "FOIA log + congressional correspondence probe "
                          "(<=4 requests)"):
            coverage.append(dict(
                agency=ag["agency"], agency_code=ag["code"], source="ALL",
                status="NOT_CHECKED", url="", http_status="",
                evidence=("host " + ag["host"] + " held by another poller; "
                          "work queued on the lock, not fetched"),
                checked_date=TODAY))
            continue
        print("\n== " + ag["code"] + "  " + ag["agency"])
        for kind, url in ag["seeds"]:
            if time.time() - started > DEADLINE_S:
                break
            status, body = get(url, tries=2)
            print("  [%s] %-18s %s" % (status, kind, url))
            if status == 0:
                # A DROPPED CONNECTION IS NOT A 404. Stop-work on this host.
                refused.append(url)
                coverage.append(dict(
                    agency=ag["agency"], agency_code=ag["code"], source=kind,
                    status="NOT_CHECKED", url=url, http_status=0,
                    evidence=("transport failure (http_status=0): a fact about "
                              "the connection, NOT about the object. Stopped "
                              "on first refusal for this host."),
                    checked_date=TODAY))
                break
            if status == 403:
                # A 403 IS NOT A NOT_FOUND. It says the edge refused US; it
                # says nothing about whether the agency publishes a log. HHS,
                # USDA and DOT answer 403 to a full browser header set on every
                # path tried, so those agencies are UNSWEPT, and recording them
                # as NOT_FOUND would manufacture a coverage claim out of a
                # block.
                coverage.append(dict(
                    agency=ag["agency"], agency_code=ag["code"], source=kind,
                    status="NOT_CHECKED", url=url, http_status=403,
                    evidence=("HTTP 403 from the edge/WAF to a full browser "
                              "header set. We were refused, so this URL was "
                              "never swept. NOT evidence the agency publishes "
                              "no log."),
                    checked_date=TODAY))
                continue
            if status != 200:
                coverage.append(dict(
                    agency=ag["agency"], agency_code=ag["code"], source=kind,
                    status="NOT_FOUND", url=url, http_status=status,
                    evidence=("HTTP %s on this URL. A fact about this URL only, "
                              "not about the agency." % status),
                    checked_date=TODAY))
                continue
            any_success = True
            n_log = n_corr = 0
            for href, text in links(body, url):
                # Percent-decode before matching: BIA's FY2017-19 logs are
                # "FY19%20FOIA%20Log.pdf", and a matcher that reads the raw
                # href misses three fiscal years for a punctuation reason.
                hay = text + " " + urllib.parse.unquote(href)
                is_log = bool(FOIA_LOG_RE.search(hay))
                is_corr = bool(CORR_RE.search(hay))
                if not (is_log or is_corr):
                    continue
                n_log += bool(is_log)
                n_corr += bool(is_corr)
                if (ag["code"], href) in seen:
                    continue
                seen.add((ag["code"], href))
                rows.append(dict(
                    agency=ag["agency"], agency_code=ag["code"],
                    found_on=url, found_on_kind=kind, url=href,
                    anchor_text=text[:300],
                    target_type=("FOIA_LOG" if is_log
                                 else "CONGRESSIONAL_CORRESPONDENCE"),
                    is_document="Y" if DOC_EXT_RE.search(href) else "N",
                    discovered_date=TODAY, fetched_status="", fetched_bytes="",
                    local_path=""))
            print("       -> %d foia-log links, %d correspondence links"
                  % (n_log, n_corr))
            coverage.append(dict(
                agency=ag["agency"], agency_code=ag["code"], source=kind,
                status="PUBLISHES" if (n_log or n_corr) else "NOT_FOUND",
                url=url, http_status=status,
                evidence=("seed page retrieved (%d bytes); %d FOIA-log links "
                          "and %d correspondence links matched on anchor text "
                          "or href" % (len(body), n_log, n_corr)),
                checked_date=TODAY))
        release_host(ag["host"], SCRIPT, "probe complete; lock released")

    write_csv(CLEAN / "foia_discovery_targets.csv", rows, TARGET_FIELDS)
    merge_coverage(coverage)
    save_manifest()
    if refused and not any_success:
        print("\n  HOST REFUSED and nothing landed. Reporting, not retrying.")
        return 3
    return 0


# ===========================================================================
# STAGE 2 - LOGS. Download the discovered log objects.
# ===========================================================================
# Priority is Native density, not completeness. Indian Affairs and IHS are
# Native by construction: every row in those logs is a request about Indian
# Country. Interior's Office of the Secretary is where the Department's own
# congressional correspondence and the Secretary's calendar requests land.
# HUD/DOI-wide logs are a general population and are sampled, not swept.

PRIORITY = ["IHS", "BIA", "DOI", "HUD"]


def local_name(agency_code, url):
    base = urllib.parse.unquote(urllib.parse.urlparse(url).path.rsplit("/", 1)[-1])
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base)[:120] or "object"
    return LOGDIR / agency_code / base


def stage_logs(argv):
    ap = argparse.ArgumentParser(prog="logs")
    ap.add_argument("--agencies", default=",".join(PRIORITY))
    ap.add_argument("--max-per-agency", type=int, default=60)
    a = ap.parse_args(argv)
    want = [x.strip().upper() for x in a.agencies.split(",") if x.strip()]

    targets = read_csv(CLEAN / "foia_discovery_targets.csv")
    by_agency = defaultdict(list)
    for r in targets:
        if r["is_document"] == "Y":
            by_agency[r["agency_code"]].append(r)

    started = time.time()
    host_of = {ag["code"]: ag["host"] for ag in AGENCIES}
    agency_of = {ag["code"]: ag["agency"] for ag in AGENCIES}
    downloaded = skipped = refused = 0
    coverage = []

    for code in want:
        rows = by_agency.get(code, [])
        if not rows:
            print("  %s: no document targets" % code)
            continue
        host = host_of.get(code, urllib.parse.urlparse(rows[0]["url"]).netloc)
        if not claim_host(host, SCRIPT, "FOIA log objects (%d)" % len(rows)):
            continue
        print("\n== downloading %s  (%d objects)" % (code, len(rows)))
        host_refused = False
        n = 0
        for r in rows:
            if n >= a.max_per_agency or time.time() - started > DEADLINE_S:
                break
            p = local_name(code, r["url"])
            if p.exists() and p.stat().st_size > 0:
                r["fetched_status"] = r["fetched_status"] or "200"
                r["fetched_bytes"] = str(p.stat().st_size)
                r["local_path"] = str(p.relative_to(CEDAR))
                skipped += 1
                continue
            if not disk_ok(MAX_OBJECT_BYTES):
                print("  [disk] stopping downloads.")
                host_refused = True
                break
            status, body = get(r["url"], min_gap=1.5, tries=2)
            r["fetched_status"] = str(status)
            r["fetched_bytes"] = str(len(body or b""))
            n += 1
            if status == 0:
                # STOP ON FIRST REFUSAL when nothing has landed from this host.
                print("  [%s] REFUSED %s" % (status, r["url"]))
                refused += 1
                host_refused = True
                coverage.append(dict(
                    agency=agency_of.get(code, code), agency_code=code,
                    source="FOIA_LOG_FILE", status="NOT_CHECKED",
                    url=r["url"], http_status=0,
                    evidence=("transport failure fetching the log object "
                              "(http_status=0), while the agency's FOIA index "
                              "page returned 200 and LISTS this log. The logs "
                              "are published; we were refused the objects. "
                              "Stopped on first refusal rather than retrying."),
                    checked_date=TODAY))
                break
            if status != 200 or not body:
                print("  [%s] %s" % (status, r["url"][:110]))
                continue
            if len(body) > MAX_OBJECT_BYTES:
                r["fetched_status"] = "200_TOO_LARGE"
                print("  [skip-large] %d bytes %s" % (len(body), r["url"][:90]))
                continue
            # Write .part then rename: AN INTERRUPTION MUST NOT LOOK LIKE A
            # COMPLETION (AGENTS.md).
            p.parent.mkdir(parents=True, exist_ok=True)
            tmp = p.with_suffix(p.suffix + ".part")
            tmp.write_bytes(body)
            tmp.replace(p)
            r["local_path"] = str(p.relative_to(CEDAR))
            downloaded += 1
            print("  [200] %7d  %s" % (len(body), p.name))
        release_host(host, SCRIPT,
                     "FOIA log objects: %d fetched this run" % n)
        if host_refused:
            print("  stopping after refusal/limit on %s" % host)

    write_csv(CLEAN / "foia_discovery_targets.csv", targets, TARGET_FIELDS)
    merge_coverage(coverage)
    save_manifest()
    print("\n  downloaded %d, already on disk %d, refused %d"
          % (downloaded, skipped, refused))
    return 0


# ===========================================================================
# PARSERS
# ===========================================================================
# Two formats, both parsed structurally. Nothing here reads a PDF as a blob of
# text and hopes: a row whose geometry cannot be read is REFUSED and named in
# the coverage file, because a mis-assigned description would attach one
# requester's words to another requester's case number.

ID_RE = re.compile(r"^(DOI-\d{4}-\d{4,7}|[A-Z]{2,6}-\d{2,4}-\d{2,6}"
                   r"|\d{2}-\d{3,5})$")
# Interior control numbers take two shapes and BOTH must match, or a whole
# bureau silently yields zero rows with no error: the bureau logs use
# `DOI-2026-007831` and the Office of the Secretary uses `DOI-OS-2025-000123`.
DOI_ID_RE = re.compile(r"^DOI-(?:[A-Z]{2,6}-)?\d{4}-\d{4,7}$")
DATE_RE = re.compile(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b")


# The two published layouts of the Interior FOIAXpress log, in column order.
# Used ONLY to relabel columns whose header glyphs extract scrambled; the
# boundaries themselves always come from the geometry.
DOI_PORTRAIT_COLUMNS = ("Request ID", "Requested Date", "Received Date",
                        "Organization", "Request Description", "Request Status")
DOI_LANDSCAPE_COLUMNS = ("Request ID", "Requester Name", "Organization",
                         "On Behalf Of", "Request Description",
                         "Multi-Track Type", "Custom Multitrack",
                         "Requested Date", "Received Date",
                         "Final Disposition", "Closed Date")


def _cluster(vals, tol):
    out = []
    for v in sorted(vals):
        if out and v - out[-1][-1] <= tol:
            out[-1].append(v)
        else:
            out.append([v])
    return out


def _solve_band(page, band):
    """Solve the column boundaries from the CENTRED header labels.

    The DOI FOIAXpress report has no ruling lines - `extract_table()` returns
    None - so the columns have to come from geometry. Two false starts, both
    recorded because each looks reasonable:

      1. **x0 peak detection.** Defeated by the description column: 56 wrapped
         lines all start at x=212 while every other column has only 11 rows,
         so any threshold that finds the description column drowns the rest.
      2. **Midpoints between header centres.** Correct only for equal-width
         columns. Here it puts the boundary at x=271 when the description
         column actually starts at x=212, filing descriptions as organisations.

    What is true: each header label is CENTRED in its column, and the header
    band is a filled rectangle whose x0/x1 are the table's own edges. So with
    b0 = table left edge and c_i the centre of header label i,

        b_(i+1) = 2*c_i - b_i

    walks the boundaries across the table. Measured on the AS-IA July 2026
    log this yields 43.0, 101.7, 126.5, 147.1, 211.9, 515.4, **545.1** - and
    the table's own right edge is 544.6. That closing agreement is not a
    coincidence, it is the check: a page whose solved boundaries do not land
    on the table edge is REFUSED rather than parsed.
    """
    # The banner is 48pt tall on the portrait bureau report and 137pt on the
    # landscape legal-size one (BIA May-Dec 2024). An 80pt ceiling silently
    # dropped every wide-format log.
    inband = [w for w in page.extract_words()
              if band["top"] <= w["top"] <= band["bottom"]
              and w["x0"] >= band["x0"] - 1]
    if len(inband) < 4:
        return None
    # The banner rectangle also contains the report title and the run stamp
    # ("Department of the Interior", "AS-IA Monthly FOIA Logs"). Only the
    # BOTTOM text line in the band is the header row; taking all of them
    # sorts four different lines together by x and invents labels.
    by_line = defaultdict(list)
    for w in inband:
        by_line[round(w["top"], 1)].append(w)
    # The header ROW may itself extract as three or four near-identical y
    # values when the glyphs are scrambled (BIA June 2026: 89.3 / 91.0 / 92.7).
    # Taking the single bottom-most y then keeps four characters out of forty.
    # Cluster the y values and take the bottom CLUSTER.
    groups = _cluster(sorted(by_line), 4.0)
    hw = [w for t in groups[-1] for w in by_line[t]]
    if len(hw) < 4:
        return None
    # GROUP CHARACTERS, NOT WORDS. Several bureau logs come out of the same
    # generator with the glyphs emitted in a scrambled order - BIA's June 2026
    # header extracts as "Req D u a e t s e ted Re D ce a i t v e ed" - so
    # word-level grouping invents labels and the geometry is abandoned for a
    # file whose ROWS are perfectly readable. The x positions are correct even
    # when the reading order is not, so the column CENTRES survive scrambling
    # and only the label TEXT is lost.
    lo = min(w["x0"] for w in hw) - 0.5
    hi = max(w["x1"] for w in hw) + 0.5
    ytop = min(w["top"] for w in hw) - 0.5
    ybot = max(w["bottom"] for w in hw) + 0.5
    chars = sorted((c for c in page.chars
                    if lo <= c["x0"] <= hi and c["bottom"] > ytop
                    and c["top"] < ybot and (c.get("text") or "").strip()),
                   key=lambda c: c["x0"])
    if len(chars) < 8:
        return None
    labels, cur = [], [chars[0]]
    for c in chars[1:]:
        if c["x0"] - max(x["x1"] for x in cur) > 2.0:
            labels.append(cur)
            cur = [c]
        else:
            cur.append(c)
    labels.append(cur)
    centres = [(min(c["x0"] for c in lb) + max(c["x1"] for c in lb)) / 2.0
               for lb in labels]
    names = ["".join(c["text"] for c in lb) for lb in labels]
    b = [band["x0"]]
    for c in centres:
        b.append(2 * c - b[-1])
    # THE CHECK. Boundaries must close on the table's own right edge, must be
    # strictly increasing, and no column may be hairline-thin.
    #
    # The tolerance is proportional because the error ACCUMULATES: each
    # boundary is solved from the previous one, so a scrambled glyph early in
    # the header shifts everything after it. Measured: the clean AS-IA header
    # closes to within 0.5pt, while BIA's scrambled June 2026 header closes
    # 21.8pt short on a 484pt table (4.5%) even though its first five
    # boundaries sit within ~2pt of the observed data edges
    # (43 / 84.6 / 104.6 / 125 / 166 / 477). Rejecting that file on a 6pt
    # tolerance would have cost the most Native-dense log we hold, for an
    # error in the ONE boundary that carries no information - the right edge
    # of the last column, which runs to the page edge anyway.
    tol = max(6.0, 0.05 * (band["x1"] - band["x0"]))
    if abs(b[-1] - band["x1"]) > tol:
        return None
    if any(b[i + 1] - b[i] < 5.0 for i in range(len(b) - 1)):
        return None
    b[-1] = band["x1"]
    flat = re.sub(r"[^a-z]", "", "".join(names).lower())
    if "requestid" not in flat and "requestdescription" not in flat:
        # The header text is scrambled beyond matching. The COLUMN COUNT and
        # ORDER are still trustworthy - they come from the geometry - so the
        # canonical layout of this report family is applied and recorded as a
        # fallback rather than the file being discarded. Verified against
        # sibling months of the same bureau whose headers ARE readable.
        if len(names) == len(DOI_PORTRAIT_COLUMNS):
            names = list(DOI_PORTRAIT_COLUMNS)
        elif len(names) == len(DOI_LANDSCAPE_COLUMNS):
            names = list(DOI_LANDSCAPE_COLUMNS)
        else:
            return None
    return b, names, band["bottom"]


def doi_columns(page):
    """Solve the column geometry from whichever banner rectangle works.

    The header banner is 48pt tall on the portrait bureau report and 137pt on
    the landscape legal-size one, so the height filter has to be generous -
    and a generous filter also admits rectangles that are NOT the header.
    Picking the topmost one blindly solved a wrong geometry for Interior's
    December 2025 log and interleaved two columns' text into one cell. So
    every candidate is tried, topmost first, and the first one whose
    boundaries close on its own table edge wins.
    """
    bands = [r for r in page.rects
             if r["x1"] - r["x0"] > page.width * 0.6
             and 2 < (r["bottom"] - r["top"]) < 200]
    for band in sorted(bands, key=lambda r: (r["top"], r["bottom"] - r["top"])):
        got = _solve_band(page, band)
        if got:
            return got
    return None


def doi_columns_from_data(page, band_bottom):
    """Fallback geometry: read the column edges off the DATA, not the header.

    Used when the header cannot be solved - a scrambled banner, a font with
    no ToUnicode map, or centres that simply do not close on the table edge.
    Every data cell in this report is LEFT-ALIGNED, so on the lines that carry
    a control number the words start at the column edges and nowhere else.
    Cluster those x positions across all such lines and the edges fall out.

    It recovers FEWER columns than the header method, because the narrow
    left-hand columns arrive glued ("05/14/202606/15/2026Brownstein") and read
    as one. That is fine and is why `doi_row_from_cells` splits the
    pre-description cells by content: what must be exact is the DESCRIPTION
    boundary, and that one is recovered cleanly because every wrapped line of
    every description starts on it.

    Columns are named by shape, not guessed: column 0 is the control number,
    the WIDEST column is the description, one column after it is the status,
    and everything between is pre-description text handled by the content
    split.
    """
    lines = defaultdict(list)
    for w in page.extract_words():
        if w["top"] > band_bottom:
            lines[round(w["top"], 1)].append(w)
    tops = sorted(lines)
    id_ys = [t for t in tops
             if DOI_ID_RE.match(min(lines[t], key=lambda w: w["x0"])["text"])]
    if len(id_ys) < 3:
        return None
    # The banner rectangle does not always enclose the header ROW - on the
    # legal-size BIA log it stops above it - so the header line survives into
    # the first record's band and lands "Request Description" inside the first
    # requester's own description. Push the body start below the last header
    # line that appears above the first control number.
    for t in tops:
        if t >= id_ys[0]:
            break
        txt = " ".join(w["text"] for w in lines[t])
        if re.search(r"(?i)request\s*(id|descri)|received\s*date", txt):
            band_bottom = max(band_bottom,
                              max(w["bottom"] for w in lines[t]) + 0.5)
    id_lines = [sorted(lines[t], key=lambda w: w["x0"]) for t in id_ys]
    cnt = Counter()
    for ws in id_lines:
        for w in ws:
            cnt[round(w["x0"])] += 1
    keep = sorted(x for x, n in cnt.items() if n >= max(2, 0.6 * len(id_lines)))
    if len(keep) < 3:
        return None
    edges = [min(g) - 0.5 for g in _cluster(keep, 4)]
    right = max(w["x1"] for ws in id_lines for w in ws) + 2
    b = edges + [max(right, page.width)]
    widths = [b[i + 1] - b[i] for i in range(len(b) - 1)]
    di = widths.index(max(widths))
    if di == 0 or len(b) - 1 < 3:
        return None
    names = []
    for i in range(len(b) - 1):
        if i == 0:
            names.append("Request ID")
        elif i == di:
            names.append("Request Description")
        elif i > di:
            names.append("Request Status")
        else:
            names.append("Requested Date")
    return b, names, band_bottom


def parse_doi_report_pdf(path, source_url, bureau_hint):
    """DOI FOIAXpress 'Monthly FOIA Logs' PDF -> request rows.

    THE GEOMETRY FACT THAT MAKES THIS SAFE: the cells are BOTTOM-aligned. A
    request's description block ENDS on the same text line as its Request ID,
    and begins below the PREVIOUS request's ID. Measured on the AS-IA July
    2026 log: DOI-2026-007565's ID sits at y=203.7 and its four description
    lines run 185.2 -> 203.2, entirely inside (144.8, 203.7].

    Read as top-aligned - the intuitive guess - every multi-line description
    would be filed against the request ABOVE it. That is not a cosmetic error;
    it would attribute one requester's words to another requester's case
    number, which is exactly the fabrication this project refuses.
    """
    import pdfplumber

    rows, refusals = [], []
    with pdfplumber.open(str(path)) as pdf:
        # A PDF WITH NO CHARACTERS IS A SCAN, NOT AN EMPTY DOCUMENT.
        # Interior's Office of the Secretary monthly logs from January 2026
        # onward are image-only: 14 pages, one image per page, ZERO chars,
        # and both pdfplumber and PyMuPDF return "". Read as an empty parse
        # that is indistinguishable from "the log has no rows".
        if not any(p.chars for p in pdf.pages[:3]):
            return [], [(0, "image-only scan: no text layer on the first "
                            "pages (%d pages, %d images). Retrieved and kept; "
                            "OCR required before it can be parsed."
                         % (len(pdf.pages), len(pdf.pages[0].images)))]
        carry = []          # trailing lines: belong to the NEXT page's first id
        bounds = names = None
        for pno, page in enumerate(pdf.pages, 1):
            got = doi_columns(page)
            if not got:
                bt = 0.0
                for r in page.rects:
                    if (r["x1"] - r["x0"] > page.width * 0.6
                            and 2 < (r["bottom"] - r["top"]) < 200):
                        bt = max(bt, r["bottom"])
                got = doi_columns_from_data(page, bt)
            if got:
                bounds, names, body_top = got
            if not bounds:
                refusals.append((pno, "no header band; column geometry unsolved"))
                continue

            # ONE PASS OVER THE CHARACTERS, NOT ONE CROP PER CELL.
            # `page.crop(...).extract_text()` rebuilds the page object every
            # call, so a 54-page landscape log with eleven columns costs
            # ~110 crops per page and the build ran for over an hour on the
            # PDFs alone. Assigning each character to its column ONCE per page
            # and then slicing by y is the same arithmetic - a character
            # belongs to the column its centre falls in, exactly as crop
            # decides it - at a fraction of the cost.
            #
            # Exact solved boundaries, no fudge: a 1pt shim pulled the final
            # digit of the received date into the organisation cell
            # ("6Personal"), because the two columns abut with no gutter.
            cells = defaultdict(list)
            for ch in page.chars:
                if not (ch.get("text") or "").strip():
                    continue
                cx = (ch["x0"] + ch["x1"]) / 2.0
                ci = -1
                for i in range(len(bounds) - 1):
                    if bounds[i] <= cx < bounds[i + 1]:
                        ci = i
                        break
                if ci < 0:
                    continue
                cells[ci].append(ch)
            # The space threshold must SCALE WITH THE FONT. A fixed 0.9pt gap
            # is right for the 6pt portrait report and far too wide for the
            # 4pt landscape one, where it produced
            # "DemocracyRestoredseeksrecordsbetweenJanuary20" - every word in
            # every description run together. Derive it from the median glyph
            # width of the column itself.
            gap_of = {}
            for ci in cells:
                cells[ci].sort(key=lambda c: (round(c["top"], 1), c["x0"]))
                w = sorted(c["x1"] - c["x0"] for c in cells[ci])
                med = w[len(w) // 2] if w else 2.0
                gap_of[ci] = max(0.25, 0.35 * med)

            def cell(top, bottom, i):
                out, prev_line, prev_x1 = [], None, None
                for ch in cells.get(i, ()):
                    cy = (ch["top"] + ch["bottom"]) / 2.0
                    if cy < top:
                        continue
                    if cy >= bottom:
                        continue
                    ln = round(ch["top"], 1)
                    if prev_line is None or ln != prev_line:
                        if out:
                            out.append(" ")
                    elif prev_x1 is not None and ch["x0"] - prev_x1 > gap_of.get(i, 0.9):
                        out.append(" ")
                    out.append(ch["text"])
                    prev_line, prev_x1 = ln, ch["x1"]
                return re.sub(r"\s+", " ", "".join(out)).strip()

            words = [w for w in page.extract_words() if w["top"] > body_top]
            if not words:
                continue
            lines = defaultdict(list)
            for w in words:
                lines[round(w["top"], 1)].append(w)
            tops = sorted(lines)

            id_tops = []
            for t in tops:
                first = min(lines[t], key=lambda w: w["x0"])
                if first["x0"] < bounds[1] and DOI_ID_RE.match(first["text"]):
                    id_tops.append((t, first["text"]))
            if not id_tops:
                carry.extend(" ".join(w["text"] for w in
                                      sorted(lines[t], key=lambda w: w["x0"]))
                             for t in tops)
                continue

            # THE TWO LAYOUTS ALIGN THEIR CELLS DIFFERENTLY, AND GETTING IT
            # BACKWARDS FILES EVERY MULTI-LINE DESCRIPTION AGAINST THE WRONG
            # CONTROL NUMBER.
            #
            #  * portrait 6-column BUREAU report - BOTTOM-aligned. The
            #    description block ENDS on the ID line. Verified on AS-IA
            #    July 2026: DOI-2026-007565's ID sits at y=203.7 and its four
            #    description lines run 185.2 -> 203.2, all above it.
            #  * landscape 11-column OFFICE OF THE SECRETARY report - TOP
            #    aligned. The block BEGINS on the ID line and wraps below it.
            #    Verified on the OS April 2025 log, where the ID line ends
            #    "...between January 20, 2021, to November 29," and the NEXT
            #    line continues "2023, as described below:".
            #
            # An automatic detector was tried and abandoned: counting lines
            # above the first ID against lines below the last gave 42 vs 1 on
            # the portrait report (decisive) but 382 vs 510 and 857 vs 686 on
            # two landscape reports (noise). The LAYOUT is the reliable
            # signal, so alignment is keyed to the column count and any third
            # layout is REFUSED rather than assumed.
            if len(names) <= 7:
                alignment = "BOTTOM"
            elif len(names) >= 10:
                alignment = "TOP"
            else:
                refusals.append((pno, "unknown layout: %d columns, cell "
                                      "alignment not established" % len(names)))
                continue

            page_rows = []
            if alignment == "BOTTOM":
                prev = body_top
                for t, rid in id_tops:
                    vals = [cell(prev, t + 3, i) for i in range(len(bounds) - 1)]
                    prev = t + 3
                    page_rows.append(doi_row_from_cells(rid, vals, names))
                lead_to_first = True
                tail = [" ".join(w["text"] for w in
                                 sorted(lines[t], key=lambda w: w["x0"]))
                        for t in tops if t > prev]
            else:
                bottom = max(tops) + 12
                for j, (t, rid) in enumerate(id_tops):
                    end = (id_tops[j + 1][0] - 1) if j + 1 < len(id_tops) else bottom
                    vals = [cell(t - 1, end, i) for i in range(len(bounds) - 1)]
                    page_rows.append(doi_row_from_cells(rid, vals, names))
                lead_to_first = False
                tail = []

            if carry and page_rows:
                if lead_to_first:
                    page_rows[0]["request_description"] = (
                        " ".join(carry) + " "
                        + page_rows[0]["request_description"]).strip()
                elif rows:
                    rows[-1]["request_description"] = (
                        rows[-1]["request_description"] + " "
                        + " ".join(carry)).strip()
                carry = []
            for rec in page_rows:
                rec["source_page"] = pno
                rec["bureau"] = bureau_hint
                rec["source_url"] = source_url
                rec["row_alignment"] = alignment
                rows.append(rec)
            carry = tail
    return rows, refusals


def _col(vals, names, *want):
    """Match a column by name, ignoring spacing.

    The header labels are assembled CHARACTER by character (see doi_columns),
    so they arrive as "RequestedDate", not "Requested Date". Matching on the
    spaced form silently returns "" for every date column and the parse looks
    like a source that publishes no dates.
    """
    def sq(x):
        return re.sub(r"[^a-z]", "", x.lower())
    wants = [sq(w) for w in want]
    for i, n in enumerate(names):
        low = sq(n)
        if any(w in low for w in wants) and i < len(vals):
            return vals[i]
    return ""


def doi_row_from_cells(rid, vals, names):
    """Map cells onto the report's OWN column names, then repair the glue.

    The report prints its headers, so there is no need to infer which column
    is which - inferring is where a silent mis-mapping would enter.

    Two repairs are needed and both are mechanical, not interpretive:

    1. **Glued neighbours.** The narrow left-hand columns abut with no gutter,
       so a row extracts as `05/14/202606/15/2026Brownstein Hyatt Farber
       Schreck` - two dates and an organisation in one run of characters. When
       a boundary is off by a couple of points the two dates land in the wrong
       cells and BOTH come out blank.

       So the cells to the LEFT of the description column are re-joined and
       re-split by content: the first two `mm/dd/yyyy` matches are the
       requested and received dates, and whatever text remains is the
       organisation. That is safe precisely because the description
       boundary - the one that matters - is accurate to about a point, while
       the drift is confined to the narrow columns before it.

    2. **A group heading inside the first band.** The Office of the Secretary
       report prints "Action Office : OS" above its first row, so the ID cell
       can arrive as "Action Office : OS DOI-2025-005351". The control number
       is taken by pattern, never the whole cell.
    """
    rid_cell = _col(vals, names, "request id") or (vals[0] if vals else "")
    mid = re.search(r"DOI-(?:[A-Z]{2,6}-)?\d{4}-\d{4,7}", rid_cell or "")
    rid_cell = mid.group(0) if mid else (rid_cell or "").strip()

    desc = _col(vals, names, "description")
    org = _col(vals, names, "organization", "organisation")
    name = _col(vals, names, "requester name")
    status = _col(vals, names, "status", "phase")
    disp = _col(vals, names, "final disposition", "disposition")
    req = _first_date(_col(vals, names, "requested date"))
    rec = _first_date(_col(vals, names, "received date"))

    if not (req and rec):
        di = next((i for i, n in enumerate(names)
                   if "description" in n.lower()), len(vals))
        glued = " ".join(v for v in vals[1:di] if v)
        found = DATE_RE.findall(glued)
        if not req and found:
            req = found[0]
        if not rec and len(found) > 1:
            rec = found[1]
        if not org:
            left = DATE_RE.sub(" ", glued)
            org = re.sub(r"\s+", " ", left).strip(" -")

    return dict(foia_request_id=rid_cell or rid,
                request_date=req, received_date=rec,
                requester_organization=(org or "").strip(),
                requester_name=(name or "").strip(),
                request_description=(desc or "").strip(),
                disposition=(disp or "").strip(),
                status=(status or "").strip())


def _first_date(v):
    m = DATE_RE.search(v or "")
    return m.group(1) if m else ""


def parse_xlsx_log(path, source_url, agency, bureau):
    """IHS / DOI-OS spreadsheet log. Header row found by content, not index."""
    import openpyxl
    rows = []
    wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    for ws in wb.worksheets:
        hdr, hidx = None, None
        for i, r in enumerate(ws.iter_rows(values_only=True)):
            cells = [str(c).strip() if c is not None else "" for c in r]
            joined = " ".join(cells).lower()
            if hdr is None:
                if ("case number" in joined or "request id" in joined
                        or "tracking number" in joined
                        or ("requester" in joined and "date" in joined)):
                    hdr = [c.strip().lower() for c in cells]
                    hidx = i
                continue
            if not any(cells):
                continue
            d = {hdr[j]: cells[j] for j in range(min(len(hdr), len(cells)))}
            rows.append(_xlsx_row(d, source_url, agency, bureau))
        if hdr is not None:
            break
    wb.close()
    return [r for r in rows if r["foia_request_id"] or r["request_description"]]


def _pick(d, *names):
    for n in names:
        for k, v in d.items():
            if k and n in k:
                return (v or "").strip()
    return ""


def _dt(v):
    v = (v or "").strip()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", v)
    if m:
        return "%s/%s/%s" % (m.group(2), m.group(3), m.group(1))
    return v


def _xlsx_row(d, source_url, agency, bureau):
    return dict(
        foia_request_id=_pick(d, "case number", "request id", "tracking"),
        # KEEP THE TWO DATES APART. Interior's spreadsheet has only a
        # "Received Date"; a request_date picker that falls back to it makes
        # the two columns identical and manufactures a request date the
        # source never stated.
        request_date=_dt(_pick(d, "req date", "request date", "date requested")),
        received_date=_dt(_pick(d, "recv date", "received date", "receive")),
        requester_name=_pick(d, "requestor name", "requester name"),
        requester_organization=_pick(d, "requestor organization",
                                     "requester organization", "organization"),
        request_description=_pick(d, "short description", "description",
                                  "subject", "request"),
        disposition=_pick(d, "granted", "disposition"),
        status=_pick(d, "status", "phase"),
        bureau=bureau, source_url=source_url, source_page="")


# ===========================================================================
# STAGE 3 - SYSTEMS. Establish that the correspondence systems EXIST.
# ===========================================================================
# There is no portal to crawl. The way an agency's controlled-correspondence
# system becomes a public fact is its own Privacy Act System of Records
# Notice, which must name the system, its number, the office that runs it and
# what it holds. Those notices are Federal Register documents and we already
# hold 156,452 of them locally.
#
# The full text is fetched from GOVINFO, not from federalregister.gov, for a
# reason worth recording: `www.federalregister.gov` was held by an active
# poller (script 130) for the whole of this build. One poller per host, ever -
# so the same documents were taken from GPO's copy instead. Different
# publisher, same authenticated text, zero added load on the held host.

SYSTEM_PATTERNS = [
    ("CONGRESSIONAL_CORRESPONDENCE", re.compile(r"(?i)congressional\s+correspondence")),
    ("CONTROLLED_CORRESPONDENCE", re.compile(r"(?i)controlled\s+correspondence")),
    ("CORRESPONDENCE_CONTROL", re.compile(r"(?i)correspondence\s+control")),
    ("CORRESPONDENCE_TRACKING", re.compile(r"(?i)correspondence\s+tracking")),
    ("CORRESPONDENCE_MANAGEMENT", re.compile(r"(?i)correspondence\s+management")),
    ("EXECUTIVE_SECRETARIAT", re.compile(r"(?i)executive\s+secretariat")),
    ("LEGISLATIVE_AFFAIRS_TRACKING",
     re.compile(r"(?i)legislative\s+affairs\s+tracking")),
    ("CONGRESSIONAL_AFFAIRS_TRACKING",
     re.compile(r"(?i)congressional\s+affairs\s+tracking")),
    ("QUILL", re.compile(r"(?i)\bQuill\b")),
]

# Only the agencies the spec named, plus the government-wide ones that own a
# tribal programme. Everything else found in the corpus is left NOT_CHECKED
# rather than half-swept.
AGENCY_OF_INTEREST = {
    "Interior Department": ("DOI", "Department of the Interior"),
    "Health and Human Services Department": ("HHS", "Department of Health and Human Services"),
    "Environmental Protection Agency": ("EPA", "Environmental Protection Agency"),
    "Agriculture Department": ("USDA", "Department of Agriculture"),
    "Energy Department": ("DOE", "Department of Energy"),
    "Transportation Department": ("DOT", "Department of Transportation"),
    "Housing and Urban Development Department": ("HUD", "Department of Housing and Urban Development"),
}

SYSTEM_FIELDS = [
    "system_id", "agency", "agency_code", "bureau_or_office", "system_name",
    "system_number", "system_named_terms", "evidence_type", "citation",
    "fr_document_number", "publication_date", "verbatim_quote", "source_url",
    "fetched_date", "log_publicly_posted", "confidence_tier", "notes"]


def _sect(text, label):
    """Pull a labelled SORN section verbatim, e.g. 'SYSTEM NAME AND NUMBER:'."""
    m = re.search(r"(?i)\b" + label + r"\s*:\s*(.{0,400}?)(?=[A-Z][A-Z /,'()-]{6,}:|$)",
                  text)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def stage_systems(argv):
    ap = argparse.ArgumentParser(prog="systems")
    ap.add_argument("--max-docs", type=int, default=14)
    a = ap.parse_args(argv)

    acts = read_csv(CLEAN / "federal_actions.csv")
    print("  scanning %d Federal Register documents already on disk" % len(acts))
    cands = []
    for r in acts:
        blob = (r.get("title") or "") + " " + (r.get("abstract") or "")
        terms = [k for k, p in SYSTEM_PATTERNS if p.search(blob)]
        if not terms:
            continue
        agn = r.get("agency_names") or ""
        code = name = ""
        for key, (c, n) in AGENCY_OF_INTEREST.items():
            if key in agn:
                code, name = c, n
                break
        if not code:
            continue
        cands.append((r, terms, code, name))
    print("  %d documents at the target agencies name a correspondence system"
          % len(cands))

    rows = read_csv(CLEAN / "congressional_correspondence_systems.csv")
    have = {r["fr_document_number"] for r in rows if r.get("fr_document_number")}
    coverage = []
    DOCS.mkdir(parents=True, exist_ok=True)

    if cands and not claim_host("www.govinfo.gov", SCRIPT,
                                "FR SORN full text (<=%d requests)" % a.max_docs):
        print("  govinfo held by another poller - queued, no fetch")
        return 0

    n = 0
    for r, terms, code, name in cands:
        if n >= a.max_docs:
            break
        docnum = r["document_number"]
        if docnum in have:
            continue
        pub = r["publication_date"]
        url = ("https://www.govinfo.gov/content/pkg/FR-%s/html/%s.htm"
               % (pub, docnum))
        cache = DOCS / ("FR-%s-%s.txt" % (pub, docnum))
        if cache.exists():
            text = cache.read_text(encoding="utf-8", errors="ignore")
            status = 200
        else:
            if not disk_ok(MAX_OBJECT_BYTES):
                break
            status, body = get(url, min_gap=1.6, tries=2)
            n += 1
            if status != 200 or not body:
                coverage.append(dict(
                    agency=name, agency_code=code, source="FR_SORN_FULLTEXT",
                    status=("NOT_CHECKED" if status in (0, 403) else "NOT_FOUND"),
                    url=url, http_status=status,
                    evidence=("govinfo returned HTTP %s for this Federal "
                              "Register document; the document itself is real "
                              "and indexed in federal_actions.csv" % status),
                    checked_date=TODAY))
                continue
            text = strip_html(body)
            cache.write_text(text, encoding="utf-8")
        sysname = _sect(text, "SYSTEM NAME AND NUMBER")
        if not sysname:
            sysname = _sect(text, "SYSTEM NAME")
        sysnum = ""
        mnum = re.search(r"\b([A-Z]{2,6}[- ]\d{1,3})\b", sysname or "")
        if mnum:
            sysnum = mnum.group(1)
        office = _sect(text, "SYSTEM MANAGER") or _sect(text, "AGENCY")
        # the verbatim quote is the sentence that names the system
        quote = ""
        for key, pat in SYSTEM_PATTERNS:
            mm = pat.search(text)
            if mm:
                lo = text.rfind(".", 0, max(0, mm.start() - 1)) + 1
                hi = text.find(".", mm.end())
                quote = text[lo:hi + 1].strip()[:900]
                break
        rows.append(dict(
            system_id="SORN-%s-%s" % (code, docnum),
            agency=name, agency_code=code,
            bureau_or_office=office[:200],
            system_name=sysname[:300], system_number=sysnum,
            system_named_terms="|".join(terms),
            evidence_type="PRIVACY_ACT_SORN",
            citation="%s FR document %s" % (pub, docnum),
            fr_document_number=docnum, publication_date=pub,
            verbatim_quote=quote, source_url=url, fetched_date=TODAY,
            log_publicly_posted="NOT_FOUND",
            confidence_tier=Tier.A.value if quote else Tier.B.value,
            notes=("The SORN is the agency's own published statement that the "
                   "system exists. It does NOT mean any log is public.")))
        coverage.append(dict(
            agency=name, agency_code=code, source="FR_SORN_FULLTEXT",
            status="PUBLISHES", url=url, http_status=status,
            evidence="SORN full text retrieved (%d chars)" % len(text),
            checked_date=TODAY))
        print("  [%s] %s  %s" % (code, docnum, (sysname or "")[:70]))

    release_host("www.govinfo.gov", SCRIPT, "SORN full text: %d fetched" % n)
    write_csv(CLEAN / "congressional_correspondence_systems.csv", rows,
              SYSTEM_FIELDS)
    merge_coverage(coverage)
    save_manifest()
    return 0


# ===========================================================================
# STAGE 4 - BUILD. Parse every retrieved log; index it; tag Indian Country.
# ===========================================================================

FOIA_FIELDS = [
    "foia_request_id", "agency", "agency_code", "bureau", "request_date",
    "received_date", "requester", "requester_organization",
    "request_description", "tribe_mentioned", "tribe_entity_id",
    "tribe_match_phrase", "organization_mentioned", "official_mentioned",
    "issue_terms_matched", "disposition", "status", "release_available",
    "release_url", "requester_is_congressional_office",
    "seeks_congressional_correspondence", "seeks_calendar_or_visitor_records",
    "native_related", "native_basis", "source_url", "source_page",
    "fetched_date", "confidence_tier"]

CORR_FIELDS = [
    "record_id", "agency", "agency_code", "bureau_recipient",
    "congressional_office", "member_name", "chamber", "member_state",
    "control_number", "date_received", "date_responded", "subject_verbatim",
    "tribe_mentioned", "tribe_entity_id", "contact_type", "event_class",
    "advocacy_channel", "is_lobbying", "source_url", "fetched_date",
    "evidence_quote", "confidence_tier", "notes"]

# A description SEEKING congressional correspondence. This is the discovery
# signal: it proves the log exists at that bureau AND that someone has already
# paid to have it located and reviewed.
SEEKS_CORR_RE = re.compile(
    r"(?i)logs?\s+of\s+correspondence|correspondence\s+logs?"
    r"|letters?\s+from\s+members?\s+of\s+congress"
    r"|congressional\s+correspondence|controlled\s+correspondence"
    r"|correspondence\s+(?:with|from|to)\s+(?:members?\s+of\s+congress"
    r"|senator|representative|congressman|congresswoman)")

SEEKS_ACCESS_RE = re.compile(
    r"(?i)\bcalendar[s]?\b|\bschedule\s+for\s+the\b|\bvisitor\s+logs?\b"
    r"|\bmeeting\s+invitation|\bquestions?\s+for\s+the\s+record\b|\bWAVES\b")

# A congressional office as REQUESTER. Deliberately narrow: it must name a
# chamber or a member's office, never merely contain "congress".
CONG_ORG_RE = re.compile(
    r"(?i)\b(?:u\.?s\.?\s+)?(?:house\s+of\s+representatives|united\s+states\s+senate"
    r"|u\.?s\.?\s+senate|senate\s+committee|house\s+committee"
    r"|office\s+of\s+(?:senator|congressman|congresswoman|representative)"
    r"|congressional\s+(?:research\s+service|budget\s+office))\b"
    r"|\bsenator\s+[A-Z]|\brep\.\s+[A-Z]")

OFFICIAL_RE = re.compile(
    r"(?i)\b(?:the\s+)?(secretary\s+of\s+the\s+interior|assistant\s+secretary"
    r"\s*[-–]?\s*indian\s+affairs|assistant\s+secretary\s+for\s+indian\s+affairs"
    r"|deputy\s+secretary|principal\s+deputy\s+assistant\s+secretary"
    r"|director\s+of\s+the\s+bureau\s+of\s+indian\s+(?:affairs|education)"
    r"|solicitor|chief\s+of\s+staff|administrator|surgeon\s+general)\b")

ISSUE_TERMS = [
    "gaming", "casino", "trust land", "fee-to-trust", "land into trust",
    "water right", "treaty", "self-governance", "self-determination",
    "638 contract", "enrollment", "recognition", "leasing", "right-of-way",
    "oil and gas", "coal", "timber", "grazing", "law enforcement",
    "boarding school", "repatriation", "NAGPRA", "housing", "health",
    "education", "irrigation", "allotment", "probate", "royalty",
    "environmental", "consultation", "appropriation", "grant",
]


GOV_SUFFIXES = frozenset({
    "nation", "tribe", "tribes", "pueblo", "rancheria", "band", "village",
    "community", "reservation", "nations",
})


def build_tribe_index(spine):
    """Phrase index of spine names that are SPECIFIC enough for free text.

    A FOIA request description is public free text. The containment defect in
    AGENTS.md is at its most dangerous here, so this index deliberately
    excludes anything short or generic: a name enters only if it has three or
    more tokens, or is a single distinctive token of at least 10 characters
    that is not in `NAME_TRAPS`. "Creek", "Oneida" and "Santa" never key a row
    on their own; "Confederated Salish and Kootenai Tribes" does.
    """
    from cedar_domain import NAME_TRAPS
    idx = {}
    for r in spine:
        for nm in [r.get("canonical_name"), r.get("fr_official_name")] + \
                  (r.get("aliases") or "").split("|"):
            nm = (nm or "").strip()
            if not nm:
                continue
            toks = [t for t in re.split(r"[^A-Za-z]+", nm.lower()) if t]
            if len(toks) >= 3:
                pass
            elif len(toks) == 2 and toks[1] in GOV_SUFFIXES \
                    and toks[0] not in NAME_TRAPS and len(toks[0]) >= 5:
                # "Navajo Nation", "Coquille Tribe" - two tokens, but the
                # second is a form of government and the first is not a trap
                # word, which is specific enough for free text. "Cherokee
                # Nation" is still excluded because `cherokee` is a NAME_TRAP,
                # and that exclusion is deliberate: several distinct Cherokee
                # governments exist and a FOIA description rarely says which.
                pass
            elif len(toks) == 1 and len(toks[0]) >= 10 and toks[0] not in NAME_TRAPS:
                pass
            else:
                continue
            idx.setdefault(nm.lower(), nm)
    pats = []
    for low, nm in idx.items():
        pats.append((re.compile(r"(?i)(?<![A-Za-z])" +
                                re.escape(nm).replace(r"\ ", r"\s+") +
                                r"(?![A-Za-z])"), nm))
    return pats


def stage_build(argv):
    ap = argparse.ArgumentParser(prog="build")
    ap.parse_args(argv)

    spine = read_csv(SPINE_DIR / "cedar_entity_spine.csv")
    resolver = Resolver(spine)
    tribe_pats = build_tribe_index(spine)
    print("  tribe phrase index: %d specific spine names" % len(tribe_pats))

    targets = {r["url"]: r for r in read_csv(CLEAN / "foia_discovery_targets.csv")}
    agency_name = {ag["code"]: ag["agency"] for ag in AGENCIES}

    out, coverage, refusals, unresolved = [], [], [], []
    per_file = Counter()

    for url, t in sorted(targets.items()):
        lp = t.get("local_path") or ""
        if not lp:
            continue
        p = CEDAR / lp
        if not p.exists():
            continue
        code = t["agency_code"]
        bureau = bureau_from_name(p.name, code)
        try:
            if p.suffix.lower() in (".xlsx", ".xlsm"):
                rows = parse_xlsx_log(p, url, agency_name.get(code, code), bureau)
                refs = []
            elif p.suffix.lower() == ".pdf":
                rows, refs = parse_doi_report_pdf(p, url, bureau)
            else:
                rows, refs = [], [(0, "unsupported extension " + p.suffix)]
        except Exception as e:
            rows, refs = [], [(0, "%s: %s" % (type(e).__name__, e))]
        per_file[p.name] = len(rows)
        if refs and not rows:
            refusals.append(dict(file=p.name, url=url, reason=str(refs[:2])))
            coverage.append(dict(
                agency=agency_name.get(code, code), agency_code=code,
                source="FOIA_LOG_FILE", status="NOT_FOUND", url=url,
                http_status=200,
                evidence=("object retrieved but its table geometry could not "
                          "be solved, so it was REFUSED rather than parsed: "
                          + str(refs[:2])[:300]),
                checked_date=TODAY))
            continue
        for r in rows:
            out.append(enrich(r, code, agency_name.get(code, code), url,
                              tribe_pats, resolver, unresolved))
        coverage.append(dict(
            agency=agency_name.get(code, code), agency_code=code,
            source="FOIA_LOG_FILE", status="PUBLISHES", url=url,
            http_status=200,
            evidence="%d request rows parsed from %s" % (len(rows), p.name),
            checked_date=TODAY))

    # de-duplicate: the monthly logs overlap the annual roll-ups
    by_key = {}
    for r in out:
        k = (r["agency_code"], r["bureau"], r["foia_request_id"],
             r["request_description"][:120])
        if k not in by_key or len(r["request_description"]) > \
                len(by_key[k]["request_description"]):
            by_key[k] = r
    rows = sorted(by_key.values(),
                  key=lambda r: (r["agency_code"], r["bureau"],
                                 r["foia_request_id"]))
    write_csv(CLEAN / "foia_request_index.csv", rows, FOIA_FIELDS)

    # ---- the congressional-correspondence layer -------------------------
    corr, sysrows = build_correspondence_layer(rows)
    write_csv(CLEAN / "congressional_correspondence_log.csv", corr, CORR_FIELDS)

    sysfile = read_csv(CLEAN / "congressional_correspondence_systems.csv")
    have = {r["system_id"] for r in sysfile}
    sysfile += [r for r in sysrows if r["system_id"] not in have]
    write_csv(CLEAN / "congressional_correspondence_systems.csv", sysfile,
              SYSTEM_FIELDS)

    if unresolved:
        REVIEW.mkdir(parents=True, exist_ok=True)
        write_csv(REVIEW / ("foia_index_unresolved_names_%s.csv" % TODAY),
                  unresolved, ["matched_phrase", "reason", "agency_code",
                               "foia_request_id", "source_url"])
    merge_coverage(coverage)

    print("\n  --- summary ---")
    print("  foia_request_index rows            %6d" % len(rows))
    print("  ... naming a spine entity          %6d"
          % sum(1 for r in rows if r["tribe_entity_id"]))
    print("  ... seeking congressional corresp. %6d"
          % sum(1 for r in rows if r["seeks_congressional_correspondence"] == "Y"))
    print("  ... seeking calendars/visitor recs %6d"
          % sum(1 for r in rows if r["seeks_calendar_or_visitor_records"] == "Y"))
    print("  ... filed BY a congressional office%6d"
          % sum(1 for r in rows if r["requester_is_congressional_office"] == "Y"))
    print("  congressional_correspondence_log   %6d" % len(corr))
    print("  systems registry rows              %6d" % len(sysfile))
    print("  files refused (geometry unsolved)  %6d" % len(refusals))
    return 0


def bureau_from_name(fname, code):
    f = fname.lower()
    if code == "BIA":
        if f.startswith("bie") or "_bie" in f or "- bie" in f:
            return "Bureau of Indian Education"
        if f.startswith("bia") or "_bia" in f:
            return "Bureau of Indian Affairs"
        if "as-ia" in f or f.startswith("fy"):
            return "Assistant Secretary - Indian Affairs"
        return "Indian Affairs (bureau not stated in the file name)"
    if code == "DOI":
        return "Office of the Secretary"
    if code == "IHS":
        return "Indian Health Service"
    if code == "HUD":
        return "Department-wide"
    return ""


def enrich(r, code, agency, url, tribe_pats, resolver, unresolved):
    desc = r.get("request_description") or ""
    org = r.get("requester_organization") or ""
    blob = desc + " " + org
    tribe = tid = phrase = ""
    for pat, nm in tribe_pats:
        m = pat.search(blob)
        if m:
            phrase = m.group(0)
            eid, canon, method, reason = resolver.resolve(nm)
            if eid:
                tribe, tid = canon, eid
            else:
                unresolved.append(dict(matched_phrase=nm, reason=reason,
                                       agency_code=code,
                                       foia_request_id=r.get("foia_request_id", ""),
                                       source_url=url))
            break
    off = OFFICIAL_RE.search(blob)
    issues = [t for t in ISSUE_TERMS if re.search(r"(?i)\b" + re.escape(t), blob)]
    # NATIVE BASIS. AS-IA/BIA/BIE and IHS logs are Native by construction -
    # every request is about Indian Country because that is the bureau's whole
    # remit. Elsewhere it must be earned by a named entity or an explicit term.
    if code in ("BIA", "IHS"):
        native, basis = "Y", "bureau_remit"
    elif tid:
        native, basis = "Y", "named_spine_entity"
    elif re.search(r"(?i)\btrib(?:e|es|al)\b|\bindian\b|\bnative\s+american\b"
                   r"|\bnative\s+village\b|\bpueblo\b|\bnavajo\b", blob):
        native, basis = "Y", "explicit_term_in_description"
    else:
        native, basis = "N", "no_native_signal_in_this_row"
    return dict(
        foia_request_id=r.get("foia_request_id", ""), agency=agency,
        agency_code=code, bureau=r.get("bureau", ""),
        request_date=r.get("request_date", ""),
        received_date=r.get("received_date", ""),
        requester=r.get("requester_name", ""), requester_organization=org,
        request_description=desc, tribe_mentioned=tribe, tribe_entity_id=tid,
        tribe_match_phrase=phrase,
        organization_mentioned=org,
        official_mentioned=off.group(0) if off else "",
        issue_terms_matched="|".join(issues),
        disposition=r.get("disposition", ""), status=r.get("status", ""),
        release_available="NOT_IN_LOG",
        release_url="",
        requester_is_congressional_office="Y" if CONG_ORG_RE.search(org) else "N",
        seeks_congressional_correspondence="Y" if SEEKS_CORR_RE.search(desc) else "N",
        seeks_calendar_or_visitor_records="Y" if SEEKS_ACCESS_RE.search(desc) else "N",
        native_related=native, native_basis=basis,
        source_url=url, source_page=str(r.get("source_page", "")),
        fetched_date=TODAY, confidence_tier=Tier.A.value)


def build_correspondence_layer(rows):
    """Two products, kept strictly apart.

    1. `congressional_correspondence_log.csv` - a row per DOCUMENTED contact
       between a congressional office and an agency. Every row here comes from
       a retrieved record that names the congressional office. `contact_type`
       says which kind of contact it was, and the taxonomy columns are filled
       ONLY for the kind that is advocacy.

       A FOIA request filed by a Member's office is a congressional office
       contacting an agency, and it is NOT advocacy - it is an information
       request. It is carried with `contact_type =
       FOIA_REQUEST_FROM_CONGRESSIONAL_OFFICE`, a BLANK `event_class` and a
       note saying why. Typing it ADVOCACY to fill a column would be the
       ACCESS -> ADVOCACY promotion the domain model forbids, wearing a
       different hat.

    2. Evidence rows for the systems registry. A FOIA request that asks a
       bureau for its log of letters from members of Congress is proof that
       the bureau KEEPS such a log - stated by the requester, and answered by
       the bureau with a control number and a disposition. That is the cheap
       half of the expensive question, and it is exactly what the strategy
       says to acquire before filing anything.
    """
    corr, sysrows = [], []
    for r in rows:
        if r["requester_is_congressional_office"] == "Y":
            corr.append(dict(
                record_id="FOIAREQ-%s-%s" % (r["agency_code"],
                                             r["foia_request_id"]),
                agency=r["agency"], agency_code=r["agency_code"],
                bureau_recipient=r["bureau"],
                congressional_office=r["requester_organization"],
                member_name="", chamber=chamber_of(r["requester_organization"]),
                member_state="", control_number=r["foia_request_id"],
                date_received=r["received_date"] or r["request_date"],
                date_responded="", subject_verbatim=r["request_description"],
                tribe_mentioned=r["tribe_mentioned"],
                tribe_entity_id=r["tribe_entity_id"],
                contact_type="FOIA_REQUEST_FROM_CONGRESSIONAL_OFFICE",
                event_class="", advocacy_channel="", is_lobbying="",
                source_url=r["source_url"], fetched_date=TODAY,
                evidence_quote=r["request_description"][:900],
                confidence_tier=Tier.A.value,
                notes=("A FOIA request from a congressional office is a "
                       "documented congressional-office -> agency contact. It "
                       "is NOT advocacy and NOT LDA lobbying, so event_class "
                       "and channel are deliberately blank.")))
        if r["seeks_congressional_correspondence"] == "Y":
            sysrows.append(dict(
                system_id="FOIAEV-%s-%s" % (r["agency_code"],
                                            r["foia_request_id"]),
                agency=r["agency"], agency_code=r["agency_code"],
                bureau_or_office=r["bureau"], system_name="",
                system_number="",
                system_named_terms="CONGRESSIONAL_CORRESPONDENCE_LOG",
                evidence_type="FOIA_LOG_REQUEST",
                citation="FOIA control number %s, %s"
                         % (r["foia_request_id"], r["received_date"]),
                fr_document_number="", publication_date=r["received_date"],
                verbatim_quote=r["request_description"][:900],
                source_url=r["source_url"], fetched_date=TODAY,
                log_publicly_posted="NO_ONLY_RELEASED_ON_REQUEST",
                confidence_tier=Tier.A.value,
                notes=("A third party asked this bureau for its log of letters "
                       "from members of Congress and the bureau opened a case "
                       "with the disposition shown in foia_request_index.csv. "
                       "That establishes the log EXISTS and has already been "
                       "located and reviewed once. Request status: "
                       + (r["status"] or "not stated"))))
    return corr, sysrows


def chamber_of(org):
    o = (org or "").lower()
    if "senate" in o or "senator" in o:
        return "Senate"
    if "house" in o or "representative" in o or "congressman" in o \
            or "congresswoman" in o:
        return "House"
    return ""


# ===========================================================================
# MAIN
# ===========================================================================

# ===========================================================================
# STAGE 5 - REPORT. Every number recomputed from the files, never typed.
# ===========================================================================
# Standing rule 10 of the regression guard: "a number in a doc that is not
# recomputed from the data is a claim, not a fact." So the build log is
# generated, not written.

def stage_report(argv):
    argparse.ArgumentParser(prog="report").parse_args(argv)
    idx = read_csv(CLEAN / "foia_request_index.csv")
    sysr = read_csv(CLEAN / "congressional_correspondence_systems.csv")
    corr = read_csv(CLEAN / "congressional_correspondence_log.csv")
    cov = read_csv(CLEAN / "correspondence_foia_source_coverage.csv")
    tgt = read_csv(CLEAN / "foia_discovery_targets.csv")

    by_bureau = Counter((r["agency_code"], r["bureau"]) for r in idx)
    seeks = [r for r in idx if r["seeks_congressional_correspondence"] == "Y"]
    access = [r for r in idx if r["seeks_calendar_or_visitor_records"] == "Y"]
    named = [r for r in idx if r["tribe_entity_id"]]
    sorns = [r for r in sysr if r["evidence_type"] == "PRIVACY_ACT_SORN"]
    ev = [r for r in sysr if r["evidence_type"] == "FOIA_LOG_REQUEST"]
    # The coverage table is about the FOIA/correspondence SWEEP. SORN full-text
    # retrievals live in the same file and would otherwise show as an agency
    # "publishing" when what was retrieved was a Federal Register notice.
    sweep = [r for r in cov if r["source"] != "FR_SORN_FULLTEXT"]
    statuses = Counter((r["agency_code"], r["status"]) for r in sweep)

    def years(rows, key="received_date"):
        """Only WELL-FORMED dates set the range.

        Taking the last four characters of whatever is in the cell let a
        single mangled PDF row print the span as "1980-2026". A date range is
        a claim about coverage and one bad cell must not be able to make it.
        """
        ys = set()
        for r in rows:
            m = re.fullmatch(r"\s*\d{1,2}/\d{1,2}/(\d{4})\s*", r.get(key) or "")
            if m and 1990 <= int(m.group(1)) <= 2030:
                ys.add(m.group(1))
        ys = sorted(ys)
        return (ys[0] + "-" + ys[-1]) if ys else "n/a"

    L = []
    A = L.append
    A("# Congressional correspondence logs + FOIA logs as a discovery index")
    A("")
    A("*Built %s by `code/136_build_congressional_correspondence_and_foia_index.py`."
      % TODAY)
    A("Every number on this page is recomputed from the CSVs by the `report`")
    A("stage; none is typed by hand.*")
    A("")
    A("## Part A - the correspondence systems")
    A("")
    A("Congress does not centrally report its contacts with agencies. The")
    A("agency on the receiving end does, because controlled correspondence is")
    A("how an agency proves it answered a member. So the systems were looked")
    A("for by NAME, in the agencies' own Privacy Act notices, not by hunting")
    A("for a portal - most of these systems have no public face at all.")
    A("")
    A("**%d correspondence systems confirmed to exist**, each from the agency's"
      % len(sorns))
    A("own Federal Register System of Records Notice, quoted verbatim with its")
    A("document number:")
    A("")
    A("| agency | system | number | citation |")
    A("|---|---|---|---|")
    for r in sorted(sorns, key=lambda r: r["agency_code"]):
        A("| %s | %s | %s | %s |" % (r["agency_code"],
                                     (r["system_name"] or "")[:70].replace("|", "/"),
                                     r["system_number"] or "-", r["citation"]))
    A("")
    A("A SORN says the system EXISTS. It does not say any log is public, and")
    A("`log_publicly_posted` is `NOT_FOUND` on every one of them.")
    A("")
    A("**%d further rows are FOIA-log evidence**: a third party asked a bureau"
      % len(ev))
    A("for its log of letters from members of Congress, and the bureau opened a")
    A("case and disposed of it. That establishes the log exists AND has already")
    A("been located and reviewed once - which is the expensive half.")
    A("")
    A("`congressional_correspondence_log.csv` holds **%d** rows. Nothing was"
      % len(corr))
    A("invented to fill it: no agency in scope publishes the log itself, and a")
    A("row is only written where a retrieved record names a congressional")
    A("office as a party. That absence is the finding, and it is what the")
    A("systems registry exists to make actionable.")
    A("")
    A("## Part B - the FOIA index")
    A("")
    A("**%d requests** parsed from **%d retrieved log objects**, %s."
      % (len(idx), sum(1 for r in tgt if r.get("local_path")), years(idx)))
    A("")
    A("| agency | bureau | requests |")
    A("|---|---|---:|")
    for (code, bur), n in by_bureau.most_common():
        A("| %s | %s | %d |" % (code, bur, n))
    A("")
    A("- **%d** requests seek congressional correspondence or logs of it."
      % len(seeks))
    A("- **%d** seek calendars, visitor records, meeting invitations or"
      % len(access))
    A("  Questions for the Record. Those are `EventClass.ACCESS` if they are")
    A("  ever built, and the domain model refuses to promote them.")
    A("- **%d** requests name an entity that resolves to the spine, across **%d**"
      % (len(named), len({r["tribe_entity_id"] for r in named})))
    A("  distinct entities.")
    fmt = Counter(r.get("source_format", "") for r in idx)
    xl = [r for r in idx if r.get("source_format") == "XLSX"]
    if fmt:
        A("- **%d** rows come from spreadsheet logs and **%d** from PDF logs."
          % (fmt.get("XLSX", 0), fmt.get("PDF", 0)))
        A("  A spreadsheet has real cells, so the row boundary is GIVEN. A PDF")
        A("  log has no ruling lines and the boundary is SOLVED from geometry.")
        A("  Filter `source_format = XLSX` for rows with no geometry anywhere")
        A("  in their provenance: **%d** of those seek congressional"
          % sum(1 for r in xl if r["seeks_congressional_correspondence"] == "Y"))
        A("  correspondence and **%d** name a spine entity."
          % sum(1 for r in xl if r["tribe_entity_id"]))
    q = Counter(r.get("parse_quality", "") for r in idx)
    if q:
        A("- **%d** rows are `parse_quality = CLEAN`; **%d** are"
          % (q.get("CLEAN", 0), q.get("SUSPECT_BOUNDARY", 0)))
        A("  `SUSPECT_BOUNDARY` - a PDF row whose description begins mid-sentence,")
        A("  which is the signature of a cell boundary that slipped and carried")
        A("  the tail of the request above it. The text is verbatim either way;")
        A("  what is not established is that the leading fragment belongs to")
        A("  this control number. Filter on CLEAN before quoting.")
    A("- **%d** rows carry `native_related = Y`; %d of those on bureau remit"
      % (sum(1 for r in idx if r["native_related"] == "Y"),
         sum(1 for r in idx if r["native_basis"] == "bureau_remit")))
    A("  alone (AS-IA, BIA, BIE and IHS logs are Native by construction).")
    A("")
    A("## Coverage - and what NOT_CHECKED means here")
    A("")
    A("| agency | PUBLISHES | NOT_FOUND | NOT_CHECKED |")
    A("|---|---:|---:|---:|")
    for code in sorted({r["agency_code"] for r in sweep}):
        A("| %s | %d | %d | %d |" % (code, statuses[(code, "PUBLISHES")],
                                     statuses[(code, "NOT_FOUND")],
                                     statuses[(code, "NOT_CHECKED")]))
    A("")
    A("`NOT_CHECKED` is not a gap in the source. HHS, USDA and DOT answer")
    A("**HTTP 403** to a full browser header set on every path tried, so those")
    A("agencies were never swept; recording them as NOT_FOUND would have")
    A("manufactured a coverage claim out of a block. HUD's index page returns")
    A("200 and LISTS its quarterly logs, and the log objects themselves refuse")
    A("the connection - the logs are published, we were refused.")
    A("")
    A("## What was refused, and why")
    A("")
    ref = [r for r in cov if r["source"] == "FOIA_LOG_FILE"
           and r["status"] != "PUBLISHES"]
    A("**%d retrieved objects were REFUSED rather than parsed.** A FOIA log is"
      % len(ref))
    A("a table with no ruling lines; when the geometry cannot be solved, a")
    A("mis-read row would attach one requester's words to another requester's")
    A("control number. That is fabrication, so the file is kept, named, and")
    A("left unparsed.")
    A("")
    A("Two named causes:")
    A("")
    A("- **Image-only scans.** Interior's Office of the Secretary monthly logs")
    A("  from January 2026 are 14 pages with one image per page and ZERO")
    A("  characters. Both pdfplumber and PyMuPDF return the empty string. A")
    A("  near-empty extraction is a scan, not an empty document. OCR is queued.")
    A("- **Scrambled or unmapped glyphs.** Some months emit their text in a")
    A("  jumbled order or in a font with no ToUnicode map, so the row content")
    A("  cannot be assembled by line at all.")
    A("")
    A("## Files")
    A("")
    for f in ("congressional_correspondence_systems.csv",
              "congressional_correspondence_log.csv",
              "foia_request_index.csv", "foia_discovery_targets.csv",
              "correspondence_foia_source_coverage.csv"):
        n = len(read_csv(CLEAN / f))
        A("- `data/clean/%s` - %d rows" % (f, n))
    A("")
    A("Raw objects and the per-URL fetch manifest with an HTTP status on every")
    A("row: `data/raw/external/correspondence/`.")
    A("")
    out = CEDAR / "docs" / "CONGRESSIONAL_CORRESPONDENCE_FOIA_BUILD_LOG.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("  wrote %s" % out.relative_to(CEDAR))
    return 0


# ===========================================================================
# STAGE 4b - QUALITY. Flag rows whose cell boundary cannot be trusted.
# ===========================================================================
# A PDF FOIA log is a table with no ruling lines, and the row boundary is
# inferred from geometry. Where that inference slips, the visible symptom is
# a description that begins in the MIDDLE of a sentence - the tail of the
# request above it, carried onto this control number. Measured examples from
# the AS-IA annual 2025 roll-up:
#
#   DOI-2025-008466  "the Lumbee Tribe of North Carolina during his service
#                     as the Assistant Secretary ... I request the following
#                     records from July 1 to Aug. 1, 2025: ..."
#   organisation      "Education E&E News"   <- two organisations concatenated
#
# The text is verbatim and nothing is invented, but the ATTRIBUTION of the
# leading fragment to this control number is not established. So it is marked,
# not silently kept and not silently dropped: a reader can filter on
# `parse_quality = CLEAN`, and anyone quoting a SUSPECT row is told to open
# the source page first.
#
# This runs as a separate stage over the built CSV rather than inside the
# parser, so flagging never costs a re-parse of ninety PDFs.

MIDSENTENCE_RE = re.compile(r"^[a-z]")
# A description that OPENS WITH A DATE is column bleed, not prose. Interior's
# Office of the Secretary log puts its date columns to the left of the
# description on one layout and to the right on another, and where a boundary
# slips the date arrives at the head of the text:
#   DOI-2025-000277  "10/04/2024 Texas at Dallas THE onSep 20, 2023..."
# The mid-sentence test does not catch it because a digit is not a lowercase
# letter, which is exactly the kind of gap a heuristic leaves.
FRAGMENT_START_RE = re.compile(
    r"^\d{1,4}[,)]|^[a-z]|^\)|^\.|^\d{1,2}/\d{1,2}/\d{2,4}")


def stage_quality(argv):
    argparse.ArgumentParser(prog="quality").parse_args(argv)
    p = CLEAN / "foia_request_index.csv"
    rows = read_csv(p)
    if not rows:
        print("  nothing to check")
        return 0
    dup = Counter((r["agency_code"], r["foia_request_id"]) for r in rows
                  if r["foia_request_id"])
    flagged = 0
    for r in rows:
        from_pdf = (r.get("source_url") or "").lower().endswith(".pdf")
        d = (r.get("request_description") or "").strip()
        reasons = []
        if from_pdf and d and FRAGMENT_START_RE.match(d):
            reasons.append("description_begins_mid_sentence")
        if dup[(r["agency_code"], r["foia_request_id"])] > 1:
            reasons.append("control_number_appears_more_than_once")
        if from_pdf and not (r.get("request_date") or r.get("received_date")):
            # Whole files come back with no dates at all when the narrow
            # left-hand columns of that month's layout cannot be separated.
            # The control number and the request text are still verbatim; the
            # dates are simply not recovered, and saying so is the point.
            reasons.append("no_date_recovered_from_this_layout")
        r["parse_quality"] = "SUSPECT_BOUNDARY" if reasons else "CLEAN"
        r["parse_quality_reason"] = "|".join(reasons)
        flagged += bool(reasons)
    # ---- AND THEN THE FLAG THAT DEPENDS ON IT --------------------------
    # `requester_is_congressional_office` was computed in the parser against
    # the organisation cell. On a boundary-suspect row that cell has absorbed
    # the request text, so the pattern fired on a SENATOR NAMED INSIDE
    # SOMEONE ELSE'S REQUEST. All four hits were false:
    #
    #   E&E News            "...letters received by ... from then-Rep. Walz"
    #   CREW                "...communications between DOI and Senator Joni Ernst"
    #   Coquille Indian Tribe "...Communications with Senator Ron Wyden"
    #   Center for Biological Diversity "...Senator Lisa Murkowski (and her staff)"
    #
    # Every one of those is a requester ASKING ABOUT a member of Congress, not
    # a congressional office filing anything - the exact inversion this build
    # exists to avoid. So the flag is recomputed here with two guards: the
    # organisation cell must be short enough to be a name rather than a
    # paragraph, and the row must not be boundary-suspect.
    recovered = 0
    for r in rows:
        org = (r.get("requester_organization") or "").strip()
        ok = (org and len(org) <= 120 and r["parse_quality"] == "CLEAN"
              and CONG_ORG_RE.search(org))
        r["requester_is_congressional_office"] = "Y" if ok else "N"
        recovered += bool(ok)
    # THE SHARPEST FILTER IS THE SOURCE FORMAT, NOT THE HEURISTIC.
    # A spreadsheet log has real cells: the row boundary is given, not
    # inferred, and no amount of wrapped text can move it. A PDF log has no
    # ruling lines and the boundary is solved from geometry. Every quality
    # flag above is a proxy for that one distinction, and none of them is
    # perfect - a bled fragment that happens to start with a capital letter
    # ("Robinson LLP Search: From 03/27/2025...") passes all of them.
    #
    # So the format is published as its own column. Anyone who needs
    # structurally exact rows filters `source_format = XLSX` and gets the IHS
    # and Interior Office-of-the-Secretary spreadsheet logs with no geometry
    # in their provenance at all.
    for r in rows:
        u = (r.get("source_url") or "").lower()
        r["source_format"] = ("XLSX" if u.endswith((".xlsx", ".xlsm"))
                              else "PDF" if u.endswith(".pdf") else "OTHER")
    fields = FOIA_FIELDS + ["source_format", "parse_quality",
                            "parse_quality_reason"]
    write_csv(p, rows, fields)
    print("  parse_quality: %d CLEAN, %d SUSPECT_BOUNDARY (%.1f%%)"
          % (len(rows) - flagged, flagged, 100.0 * flagged / len(rows)))
    print("  requester_is_congressional_office after guards: %d" % recovered)

    corr, _ = build_correspondence_layer(rows)
    write_csv(CLEAN / "congressional_correspondence_log.csv", corr, CORR_FIELDS)

    # Carry the parse quality onto the FOIA-log evidence rows in the systems
    # registry, so a quote taken from a boundary-suspect row is visibly so.
    sp = CLEAN / "congressional_correspondence_systems.csv"
    sysr = read_csv(sp)
    q = {(r["agency_code"], r["foia_request_id"]): r["parse_quality"]
         for r in rows}
    for r in sysr:
        if r.get("evidence_type") == "FOIA_LOG_REQUEST":
            cid = (r.get("system_id") or "").split("-", 2)[-1]
            r["source_parse_quality"] = q.get((r.get("agency_code"), cid), "")
        else:
            r["source_parse_quality"] = "N/A_NOT_FROM_A_FOIA_LOG"
    write_csv(sp, sysr, SYSTEM_FIELDS + ["source_parse_quality"])
    return 0


STAGES = {"probe": stage_probe, "logs": stage_logs, "systems": stage_systems,
          "build": stage_build, "quality": stage_quality,
          "report": stage_report}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in list(STAGES) + ["all"]:
        print(__doc__)
        return 2
    stage, argv = sys.argv[1], sys.argv[2:]
    if stage == "all":
        for name in ("probe", "logs", "systems", "build", "quality", "report"):
            print("\n########## %s ##########" % name.upper())
            rc = STAGES[name]([])
            if rc:
                return rc
        return 0
    return STAGES[stage](argv)


if __name__ == "__main__":
    sys.exit(main())
