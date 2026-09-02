#!/usr/bin/env python3
r"""
Cedar Press - 1090: HARVEST Dear Tribal Leader letters from the agencies that
publish them, which is NOT the Federal Register.

    py -3 code/1090_dtll_agency_harvest.py harvest
    py -3 code/1090_dtll_agency_harvest.py codebook   # register the table
    py -3 code/1090_dtll_agency_harvest.py verify
    py -3 code/1090_dtll_agency_harvest.py --selftest # prove the invariants FIRE

WHY THIS EXISTS
---------------
`consultation_events.csv` carries **6** rows typed `dear_tribal_leader_letter`.
`code/962_probe_dear_tribal_leader_letters.py` established on 2026-09-02 that
the Federal Register itself holds only **46** documents containing the phrase
(14 of them Interior's), so the six is a faithful reading of the FR and the FR
is the WRONG CEILING: **DTLLs are published on agency websites, not in the
Federal Register.** 962 was a probe and wrote no letter rows. This is the
acquisition.

962 left two leads and one open wound:

  * bia.gov enumerates **10** DTLL URLs in its own sitemap - a FLOOR.
  * **ihs.gov answered HTTP 406 and was recorded `NOT_CHECKED`.**

THE 406 WAS A HEADER SHAPE, NOT A REFUSAL
------------------------------------------
`docs/BLOCKED_SOURCE_BYPASS_2026-08-26.md` says the discriminator is the header
**shape**, not the User-Agent string. Measured 2026-09-02 with the full
navigation header set (`Accept`, `Accept-Language`, `Sec-Fetch-*`,
`Upgrade-Insecure-Requests`, brotli):

    https://www.ihs.gov/robots.txt    HTTP 200   184 B   ->  "User-agent: *"
                                                             "Disallow:"      (EMPTY = allow all)
    https://www.ihs.gov/sitemap.xml   HTTP 200    86 KB   ->  6,481 URLs

and inside those 6,481 URLs:

    /newsroom/triballeaderletters/{2000..2026}letters/     27 year index pages
    /newsroom/urbanleaderletters/{...}                     13 year index pages

**IHS publishes Dear Tribal Leader Letters as a dated series going back to
2000, and the 406 was hiding the whole of it.** The 2025 index alone lists more
letters than Cedar holds for the entire federal government since 1994.

WHAT IS HARVESTED, AND WHAT IS NOT
-----------------------------------
HARVESTED (one row per letter):
  * `www.ihs.gov/newsroom/triballeaderletters/<year>letters/` - the publisher's
    own year indexes. Each letter is a `<p class="ihs_leaderLetters_date">`
    carrying the date IN WORDS, followed by an `<a>` whose text is IHS's own
    one-sentence summary and whose href is the letter PDF.
  * `www.bia.gov` DTLL URLs under robots-allowed `/news/`, enumerated from
    bia.gov's own paginated sitemap (not guessed - see below).

NOT HARVESTED, and each absence is a recorded state, never a silence:
  * **The PDFs themselves.** The row is built from the index page, which states
    the date and the subject in the publisher's own words. Downloading ~400
    PDFs to re-read a date the index already states is not an acquisition, it
    is bandwidth. `document_url` is on every row for anyone who wants one.
  * **Urban Indian Organization leader letters** (`DUIOLL`). A letter addressed
    to Urban Indian Organizations is not a letter to tribal leaders. They are
    COUNTED and reported as an adjacent series; rows are emitted only where
    IHS's own filename says the letter went to tribal leaders too
    (`DTLL_...`, `DTLL_DUIOLL_...`). `addressed_to` records which.
  * **Enclosures.** `Enclosure_...pdf` is an attachment to a letter, not a
    letter. Flagged `is_enclosure=1` and excluded from the letter count.
  * **Other departments.** Probed only, at most `MAX_CHILD` sitemap shards per
    host, and recorded as `REPORTED_FLOOR_PARTIAL_INDEX` or `UNMEASURED` with
    the shard count. **A partly-walked index is not an absence** and this
    script will not let one print as one.

WHY A NEW TABLE AND NOT A ROW IN `consultation_events.csv`
-----------------------------------------------------------
`code/96_build_consultation_events.py` OWNS that file and rebuilds it from its
own two FR inputs. Anything appended from outside is dropped on its next run -
the `09_import_rulings.py` shape named in `AGENTS.md`, and the same reason
`docs/methodology/federal-register.md` recommends a THIRD file rather than
merging Section 106 into it. So this writes its own table and never touches
96's. `consultation_events.csv` keeps its 6 FR-sourced rows; the letters that
were never FR documents live where they can survive a rebuild.

TERMS AND ROBOTS
----------------
Every host's `robots.txt` is fetched **with the same headers used for content**
(`docs/PULL_DISCIPLINE.md`: `RobotFileParser.read()` fetches with
`Python-urllib` and reads a 403 as `disallow_all`). A non-200 robots.txt is
recorded as "no rule read", never as a refusal. Only a literal `Disallow`
matching the path stops a fetch. Every host here is a federal publisher; none
is on the eight-source hard list in `docs/PUBLICATION_POLICY.md`.

READS   nothing in data/clean (it only counts consultation_events.csv for the
        before/after figure, and never writes it)
WRITES  data/clean/dear_tribal_leader_letters.csv
        data/clean/dtll_source_coverage.csv
        data/raw/external/dtll/**              (page cache, .part then rename)
        docs/DEAR_TRIBAL_LEADER_HARVEST.json   (every request, every count)

INVARIANTS - exit 1
-------------------
  INV-DTLL-DATE      every letter row carries a `letter_date` that is a
                     reformatting of `letter_date_verbatim`, which is the
                     publisher's own string. A date that cannot be traced to
                     the page is not written at all.
  INV-DTLL-URL       every letter row carries a `document_url` and a
                     `source_index_url`, and its source index returned 200.
  INV-DTLL-ABSENCE   no coverage row says `NOT_IN_SOURCE` unless that source
                     returned HTTP 200 AND its index was walked in full.
                     A refusal, a 406 and a partly-walked sitemap index are
                     `NOT_CHECKED` / `REPORTED_FLOOR_PARTIAL_INDEX`.
  INV-DTLL-DUP       no two rows share a `document_url`.
"""
from __future__ import annotations

import csv
import datetime as dt
import html as htmlmod
import json
import os
import random
import re
import sys
import time
import urllib.parse
from collections import Counter, defaultdict
from pathlib import Path

import requests

CEDAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CEDAR / "code"))
CLEAN = CEDAR / "data" / "clean"
RAW = CEDAR / "data" / "raw" / "external" / "dtll"
LOGS = CEDAR / "logs"
DOCS = CEDAR / "docs"
SCRIPT = "code/1090_dtll_agency_harvest.py"
TODAY = dt.date.today().isoformat()

from cedar_keys import stable_digest          # noqa: E402

OUT_LETTERS = CLEAN / "dear_tribal_leader_letters.csv"
OUT_COVERAGE = CLEAN / "dtll_source_coverage.csv"
OUT_JSON = DOCS / "DEAR_TRIBAL_LEADER_HARVEST.json"

# ---- the header SHAPE, not just the UA. This is what fixed the ihs.gov 406.
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}
GAP = 1.3
DEADLINE_S = 40 * 60
MAX_CHILD = 6                    # sitemap shards walked per PROBE host
_START = [time.time()]
_LEDGER: list[dict] = []
_ROBOTS_SITEMAPS: dict[str, list] = {}
_REQ_BY_HOST: Counter = Counter()
MAX_REQ_PER_HOST = 60

LETTER_COLS = [
    "letter_id", "channel", "agency", "agency_code", "series",
    "letter_date", "letter_date_verbatim", "letter_date_basis",
    "index_listing_count", "also_listed_under_dates",
    "subject_as_published", "addressed_to", "addressed_to_basis",
    "document_url", "document_format", "record_kind", "is_enclosure",
    "linked_pdf_count",
    "source_index_url", "source_index_http_status", "source_index_year",
    "harvest_method", "tier", "confidence", "fetched_date", "built_date",
    "built_by_script",
]

COVERAGE_COLS = [
    "coverage_id", "source_host", "agency", "series", "url", "http_status",
    "response_bytes", "index_shards_total", "index_shards_walked",
    "letters_found", "coverage_status", "verdict", "probed_date",
    "probed_by_script",
]

# ---------------------------------------------------------------- host lock


def lock_path(host):
    return LOGS / f"_HOSTLOCK_{host}.json"


def pid_alive(pid):
    try:
        import subprocess
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"(Get-CimInstance Win32_Process -Filter \"ProcessId={int(pid)}\")"
             f".CommandLine"], capture_output=True, text=True, timeout=60)
        if out.returncode != 0:
            return True          # cannot measure -> assume held, the safe way
        return bool(out.stdout.strip())
    except Exception:
        return True


def claim_host(host, purpose):
    cur = None
    if lock_path(host).exists():
        try:
            cur = json.loads(lock_path(host).read_text(encoding="utf-8"))
        except Exception:
            cur = None
    if cur and cur.get("active") and cur.get("pid") and pid_alive(cur["pid"]):
        cur.setdefault("queue", []).append(
            {"script": SCRIPT, "purpose": purpose, "queued_at": TODAY})
        lock_path(host).write_text(json.dumps(cur, indent=1), encoding="utf-8")
        print(f"  [1090] host {host} held by {cur.get('script')} - queued, "
              f"nothing fetched")
        return False
    lock_path(host).write_text(json.dumps({
        "host": host, "pid": os.getpid(), "script": SCRIPT,
        "claimed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "active": True, "queue": (cur or {}).get("queue", []),
        "policy": f"sequential, >={GAP}s gap, <={MAX_REQ_PER_HOST} requests "
                  f"per host, {DEADLINE_S // 60} min wall-clock deadline, "
                  f"stop on first edge refusal",
        "note": purpose,
        "downloaded_this_run": [], "already_on_disk_skipped": [],
        "refused_by_host": []}, indent=1), encoding="utf-8")
    return True


def release_host(host, note, downloaded, skipped, refused):
    cur = {}
    if lock_path(host).exists():
        try:
            cur = json.loads(lock_path(host).read_text(encoding="utf-8"))
        except Exception:
            cur = {}
    cur.update({"host": host, "active": False, "released": TODAY,
                "released_by": SCRIPT, "note": note,
                "downloaded_this_run": downloaded,
                "already_on_disk_skipped": skipped,
                "refused_by_host": refused,
                "requests_made": _REQ_BY_HOST[host]})
    lock_path(host).write_text(json.dumps(cur, indent=1), encoding="utf-8")


# ---------------------------------------------------------------- fetching


class EdgeRefusal(Exception):
    pass


def robots_allows(sess, host, path):
    """Fetch robots.txt with OUR headers. A non-200 is 'no rule read'."""
    url = f"https://{host}/robots.txt"
    try:
        r = sess.get(url, headers=HEADERS, timeout=(15, 60))
    except Exception as e:
        return True, f"robots.txt unreachable ({type(e).__name__}); no rule read"
    _REQ_BY_HOST[host] += 1
    _LEDGER.append({"url": url, "http_status": r.status_code,
                    "bytes": len(r.content)})
    time.sleep(GAP)
    if r.status_code != 200:
        return True, (f"robots.txt HTTP {r.status_code}; no rule read - a host "
                      f"that will not serve its robots file is not a host that "
                      f"forbids you")
    active, dis = False, []
    _ROBOTS_SITEMAPS[host] = []
    for line in r.text.splitlines():
        s = line.split("#", 1)[0].strip()
        if not s:
            continue
        k, _, v = s.partition(":")
        k, v = k.strip().lower(), v.strip()
        if k == "user-agent":
            active = (v == "*")
        elif k == "disallow" and active and v:
            dis.append(v)
        elif k == "sitemap":
            _ROBOTS_SITEMAPS[host].append(s.split(":", 1)[1].strip())
    for d in dis:
        if path.startswith(d):
            return False, f"robots.txt Disallow: {d}"
    return True, f"robots.txt read, {len(dis)} Disallow rules, none matches {path}"


def cache_path(url):
    p = urllib.parse.urlparse(url)
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", (p.path + ("?" + p.query if p.query else "")))
    slug = slug.strip("_") or "root"
    if len(slug) > 120:
        slug = slug[:100] + "_" + stable_digest((url,))
    return RAW / p.netloc / (slug + ".html")


def get(sess, url, use_cache=True):
    """Returns (status, text, bytes, from_cache)."""
    host = urllib.parse.urlparse(url).netloc
    cp = cache_path(url)
    if use_cache and cp.exists() and cp.stat().st_size > 0:
        return 200, cp.read_text(encoding="utf-8", errors="replace"), \
            cp.stat().st_size, True
    if time.time() - _START[0] > DEADLINE_S:
        raise SystemExit("[1090] wall-clock deadline reached; stopping")
    if _REQ_BY_HOST[host] >= MAX_REQ_PER_HOST:
        raise SystemExit(f"[1090] per-host request cap hit on {host}; stopping")
    try:
        r = sess.get(url, headers=HEADERS, timeout=(15, 120))
    except Exception as e:
        _REQ_BY_HOST[host] += 1
        _LEDGER.append({"url": url, "http_status": 0, "bytes": 0,
                        "error": type(e).__name__})
        raise EdgeRefusal(f"{type(e).__name__} on {url}")
    _REQ_BY_HOST[host] += 1
    _LEDGER.append({"url": url, "http_status": r.status_code,
                    "bytes": len(r.content)})
    time.sleep(GAP + random.uniform(0, 0.4))
    if r.status_code != 200:
        return r.status_code, None, len(r.content), False
    cp.parent.mkdir(parents=True, exist_ok=True)
    part = cp.with_suffix(cp.suffix + ".part")
    part.write_text(r.text, encoding="utf-8")
    part.replace(cp)             # .part-then-rename: an interruption cannot
    return 200, r.text, len(r.content), False   # look like a completion


# ---------------------------------------------------------------- parsing

MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"], 1)}
DATE_WORDS = re.compile(
    r"^\s*(" + "|".join(MONTHS) + r")\.?\s+(\d{1,2})\s*,\s*(\d{4})\s*$", re.I)

# the publisher's own date element, then the anchors that follow it
IHS_BLOCK = re.compile(
    r'<p class="ihs_leaderLetters_date">(.*?)</p>(.*?)(?=<p class="ihs_leaderLetters_date">|\Z)',
    re.S | re.I)
ANCHOR = re.compile(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S | re.I)
TAGS = re.compile(r"<[^>]+>")


def clean_text(s):
    s = TAGS.sub(" ", s)
    s = htmlmod.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def iso_from_words(verbatim):
    """ISO date, or '' - NEVER a guess. The words must parse completely."""
    m = DATE_WORDS.match(clean_text(verbatim))
    if not m:
        return ""
    mo = MONTHS.get(m.group(1).lower())
    d, y = int(m.group(2)), int(m.group(3))
    if not mo or not (1 <= d <= 31) or not (1990 <= y <= 2035):
        return ""
    try:
        return dt.date(y, mo, d).isoformat()
    except ValueError:
        return ""


# IHS's own per-year document folder: .../display_objects/[documents/]2014_Letters/
# This is the discriminator for "the publisher filed this under its letters for
# that year", and it is what excludes the site-chrome PDF that appears in the
# footer of all 27 pages (NoticePrivacyPracticePamphlet.pdf, /sites/HIPAA/) and
# the five govinfo Federal Register PDFs a letter happens to link to.
IHS_LETTER_PATH = re.compile(r"_letters?/", re.I)

# IHS labels an attachment in its own link text, and names it in its own file
# name. Either is the publisher saying so.
ENCLOSURE_LABEL = re.compile(
    r"^\s*(enclosure|attachment|exhibit|tab\b|appendix)", re.I)
ENCLOSURE_FILE = re.compile(
    r"^(enclosure|attachment|exhibit|manualexhibit|tab[-_ ])", re.I)


def addressed_to_from_filename(fname, default="tribal_leaders"):
    """Refine the SECTION's own claim using IHS's own filename abbreviation.

    The page is `/newsroom/triballeaderletters/<year>letters/`, so the section
    is the publisher saying these went to tribal leaders. The filename only
    adds whether Urban Indian Organization leaders were addressed as well
    (`DUIOLL` / `DTUIOLL`).
    """
    f = re.sub(r"^(enclosure|attachment|exhibit)[-_ ]*", "", fname, flags=re.I)
    f = f.upper()
    if re.match(r"D?T?UIOLL", f) and "DUIOLL" not in f and "DTUIOLL" not in f:
        pass
    if "DUIOLL" in f or "DTUIOLL" in f:
        return ("tribal_leaders_and_urban_indian_organization_leaders",
                "document filename abbreviation published by IHS")
    return (default, "the publisher's own index section, "
                     "/newsroom/triballeaderletters/")


def parse_ihs_year_page(text, index_url, year):
    """One row per (date block, PDF anchor). Nothing is inferred."""
    rows = []
    for m in IHS_BLOCK.finditer(text):
        verbatim = clean_text(m.group(1))
        iso = iso_from_words(verbatim)
        for href, label in ANCHOR.findall(m.group(2)):
            url = htmlmod.unescape(href.strip())
            if not url.lower().endswith(".pdf"):
                continue
            url = urllib.parse.urljoin(index_url, url)
            fname = urllib.parse.unquote(url.rsplit("/", 1)[-1])
            if not IHS_LETTER_PATH.search(url):
                rows.append({"_skip": "not_under_the_publisher_year_folder",
                             "document_url": url})
                continue
            lab = clean_text(label)
            addressed, addr_basis = addressed_to_from_filename(fname)
            rows.append({
                "letter_id": "DTLL-" + stable_digest((url,)),
                "channel": "CONSULTATION",
                "agency": "Indian Health Service",
                "agency_code": "HHS-IHS",
                "series": "IHS Dear Tribal Leader Letters",
                "letter_date": iso,
                "letter_date_verbatim": verbatim,
                "letter_date_basis": "ihs_leaderLetters_date element on the "
                                     "publisher's own year index",
                "subject_as_published": lab[:900],
                "addressed_to": addressed,
                "addressed_to_basis": addr_basis,
                "document_url": url,
                "document_format": "pdf",
                "record_kind": ("enclosure"
                                if (ENCLOSURE_LABEL.match(lab)
                                    or ENCLOSURE_FILE.match(fname))
                                else "letter"),
                "is_enclosure": int(bool(ENCLOSURE_LABEL.match(lab))
                                    or bool(ENCLOSURE_FILE.match(fname))),
                "linked_pdf_count": "",
                "source_index_url": index_url,
                "source_index_http_status": 200,
                "source_index_year": year,
                "harvest_method": "publisher_year_index",
                "tier": "B",
                "confidence": "high",
                "fetched_date": TODAY,
                "built_date": TODAY,
                "built_by_script": SCRIPT,
            })
    return rows


BIA_JSONLD = re.compile(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})')
BIA_TIME_ATTR = re.compile(r'<time[^>]*datetime="(\d{4}-\d{2}-\d{2})')
BIA_TIME_TEXT = re.compile(r"<time[^>]*>\s*([A-Z][a-z]+ \d{1,2}, \d{4})\s*<")
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)


def parse_bia_news_page(text, url, agency="Bureau of Indian Affairs",
                        agency_code="DOI-BIA", series=None, index_url=None):
    """Indian Affairs Drupal news node (bia.gov and bie.edu run the same CMS).
    The date comes from the page's own structured markup, never from the URL."""
    iso, verbatim, basis = "", "", ""
    m = BIA_JSONLD.search(text)
    if m:
        iso = verbatim = m.group(1)
        basis = 'schema.org "datePublished" in the page\'s own JSON-LD'
    if not iso:
        m = BIA_TIME_ATTR.search(text)
        if m:
            iso = verbatim = m.group(1)
            basis = "<time datetime> attribute"
    if not iso:
        m = BIA_TIME_TEXT.search(text)
        if m:
            verbatim = m.group(1)
            iso = iso_from_words(verbatim)
            basis = "<time> element text"
    n_pdf = len({h for h in re.findall(r'href="([^"]+\.[Pp][Dd][Ff])"', text)})
    title = ""
    tm = TITLE_RE.search(text)
    if tm:
        title = clean_text(tm.group(1))
        title = re.sub(r"\s*\|\s*(Indian Affairs|Bureau of Indian Education)"
                       r"\s*$", "", title)
    return {
        "letter_id": "DTLL-" + stable_digest((url,)),
        "channel": "CONSULTATION",
        "agency": agency,
        "agency_code": agency_code,
        "series": series or "BIA news: Dear Tribal Leader letters",
        "letter_date": iso,
        "letter_date_verbatim": verbatim,
        "letter_date_basis": basis,
        "index_listing_count": 1,
        "also_listed_under_dates": "",
        "subject_as_published": title[:900],
        "addressed_to": "tribal_leaders",
        "addressed_to_basis": "the phrase 'Dear Tribal Leader'/'DTLL' in the "
                              "publisher's own URL slug",
        "document_url": url,
        "document_format": "html",
        # A page with no date of its own that links letter PDFs is the
        # publisher's INDEX of letters, not a letter. Counting an index as a
        # letter would inflate the total by one and hide the N letters it
        # names, so it is typed as what it is and its link count is recorded
        # as the measured, un-promoted remainder.
        "record_kind": ("publisher_index_page"
                        if (not iso and n_pdf > 0) else "letter"),
        "is_enclosure": 0,
        "linked_pdf_count": n_pdf,
        "source_index_url": index_url or "https://www.bia.gov/sitemap.xml",
        "source_index_http_status": 200,
        "source_index_year": iso[:4] if iso else "",
        "harvest_method": "publisher_sitemap_enumeration",
        "tier": "B",
        "confidence": "high",
        "fetched_date": TODAY,
        "built_date": TODAY,
        "built_by_script": SCRIPT,
    }


LOC = re.compile(r"<loc>\s*(.*?)\s*</loc>", re.S | re.I)
# `dear-tribal-leader` alone MISSES bia.gov/service/progress-act/dtll, which is
# the tenth URL 962 counted and this script's first pass did not. Measured, not
# guessed: widening the pattern to the abbreviation and to the
# `tribal-leader-letter` form recovers exactly that one URL and no other.
DTLL_URL = re.compile(
    r"(dear[-_]?tribal[-_]?leader|tribal[-_]?leader[-_]?letter|(?<![a-z])dtll(?![a-z]))",
    re.I)


def sitemap_locs(text):
    return [htmlmod.unescape(x) for x in LOC.findall(text or "")]


def is_sitemap_index(text):
    return "<sitemapindex" in (text or "").lower()


# ---------------------------------------------------------------- harvest


def harvest_ihs(sess, letters, coverage):
    host = "www.ihs.gov"
    if not claim_host(host, "IHS Dear Tribal Leader Letters year indexes"):
        coverage.append(cov_row(host, "Indian Health Service",
                                "IHS Dear Tribal Leader Letters", "", "", "",
                                "", "", "", "NOT_CHECKED",
                                "host held by another poller; deferred"))
        return
    downloaded, skipped, refused = [], [], []
    try:
        ok, why = robots_allows(sess, host, "/newsroom/triballeaderletters/")
        if not ok:
            coverage.append(cov_row(
                host, "Indian Health Service", "IHS Dear Tribal Leader Letters",
                f"https://{host}/robots.txt", "", "", "", "", "",
                "ROBOTS_FORBIDDEN", why))
            return
        st, sm, nb, cached = get(sess, f"https://{host}/sitemap.xml")
        if st != 200:
            coverage.append(cov_row(
                host, "Indian Health Service", "IHS Dear Tribal Leader Letters",
                f"https://{host}/sitemap.xml", st, nb, "", "", "",
                "NOT_CHECKED",
                f"HTTP {st} on the sitemap. NOT an absence - a refused index "
                f"says nothing about what the agency publishes"))
            return
        (skipped if cached else downloaded).append("sitemap.xml")
        locs = sitemap_locs(sm)
        year_pages = sorted(u for u in locs
                            if "/newsroom/triballeaderletters/" in u
                            and re.search(r"/\d{4}-?letters/$", u))
        urban = [u for u in locs if "/newsroom/urbanleaderletters/" in u
                 and re.search(r"/\d{4}-?letters/$", u)]
        print(f"  [1090] ihs.gov sitemap: {len(locs):,} URLs, "
              f"{len(year_pages)} tribal-leader-letter year indexes, "
              f"{len(urban)} urban-leader-letter year indexes")
        n_before = len(letters)
        skipped_kinds = Counter()
        for u in year_pages:
            ym = re.search(r"/(\d{4})-?letters/$", u)
            year = ym.group(1) if ym else ""
            st, txt, nb, cached = get(sess, u)
            if st != 200:
                coverage.append(cov_row(
                    host, "Indian Health Service",
                    f"IHS Dear Tribal Leader Letters {year}", u, st, nb,
                    "", "", "", "NOT_CHECKED",
                    f"HTTP {st} on a year index the publisher's own sitemap "
                    f"enumerates; NOT an absence"))
                refused.append(u)
                continue
            (skipped if cached else downloaded).append(u)
            got = parse_ihs_year_page(txt, u, year)
            kept = [r for r in got if "_skip" not in r]
            for r in got:
                if "_skip" in r:
                    skipped_kinds[r["_skip"]] += 1
            letters.extend(kept)
            coverage.append(cov_row(
                host, "Indian Health Service",
                f"IHS Dear Tribal Leader Letters {year}", u, 200, nb,
                1, 1, len(kept), "ENUMERATED_IN_FULL",
                f"{len(kept)} letter(s) addressed to tribal leaders on the "
                f"publisher's own {year} index"))
        print(f"  [1090] IHS letters: {len(letters) - n_before}; "
              f"skipped by IHS's own filename prefix: {dict(skipped_kinds)}")
    except EdgeRefusal as e:
        refused.append(str(e))
        coverage.append(cov_row(
            host, "Indian Health Service", "IHS Dear Tribal Leader Letters",
            f"https://{host}/", 0, 0, "", "", "", "NOT_CHECKED",
            f"edge refusal: {e}. Stopped rather than retry into a block"))
    finally:
        release_host(host, "IHS DTLL year indexes", downloaded, skipped, refused)


def harvest_indian_affairs_drupal(sess, host, agency, agency_code, series,
                                  letters, coverage):
    """bia.gov and bie.edu run the same Indian Affairs Drupal install and both
    enumerate their Dear Tribal Leader letters in their own sitemap."""
    if not claim_host(host, f"{agency} Dear Tribal Leader letters from its sitemap"):
        coverage.append(cov_row(host, agency, series, "", "", "", "", "", "",
                                "NOT_CHECKED",
                                "host held by another poller; deferred"))
        return
    downloaded, skipped, refused = [], [], []
    try:
        ok, why = robots_allows(sess, host, "/news")
        if not ok:
            coverage.append(cov_row(
                host, agency, series, f"https://{host}/robots.txt", "", "", "",
                "", "", "ROBOTS_FORBIDDEN", why))
            return
        st, sm, nb, cached = get(sess, f"https://{host}/sitemap.xml")
        if st != 200:
            coverage.append(cov_row(
                host, agency, series, f"https://{host}/sitemap.xml", st, nb,
                "", "", "", "NOT_CHECKED",
                f"HTTP {st} on the sitemap; NOT an absence"))
            return
        (skipped if cached else downloaded).append("sitemap.xml")
        # THE ?page=N LOOP FAILS OPEN on this CMS: page=3..20 return the INDEX
        # itself, HTTP 200, two <loc>s each. The first pass of this script
        # counted 2,448 bia.gov URLs "over 20 pages" from exactly that - the
        # same fail-open shape as FPDS `AGENCY_CODE:` in docs/PULL_DISCIPLINE.md.
        # Walk the index's own children and nothing else.
        all_locs, shards = [], []
        if is_sitemap_index(sm):
            shards = sitemap_locs(sm)
            for c in shards:
                st, txt, nb, cached = get(sess, c)
                if st != 200 or txt is None or is_sitemap_index(txt):
                    refused.append(c)
                    continue
                (skipped if cached else downloaded).append(c)
                all_locs += sitemap_locs(txt)
        else:
            shards = [f"https://{host}/sitemap.xml"]
            all_locs += sitemap_locs(sm)
        hits = sorted({u for u in all_locs if DTLL_URL.search(u)})
        print(f"  [1090] {host} sitemap: {len(all_locs):,} URLs over "
              f"{len(shards)} shard(s), {len(hits)} DTLL URL(s)")
        found = 0
        for u in hits:
            st, txt, nb, cached = get(sess, u)
            if st != 200 or txt is None:
                refused.append(u)
                continue
            (skipped if cached else downloaded).append(u)
            letters.append(parse_bia_news_page(
                txt, u, agency=agency, agency_code=agency_code, series=series,
                index_url=f"https://{host}/sitemap.xml"))
            found += 1
        coverage.append(cov_row(
            host, agency, series, f"https://{host}/sitemap.xml", 200, nb,
            len(shards), len(shards), found, "REPORTED_FLOOR",
            f"{found} letter(s) from {len(hits)} DTLL URL(s) across "
            f"{len(all_locs):,} sitemap URLs in {len(shards)} shard(s). "
            f"A FLOOR: a Drupal sitemap need not carry every node"))
    except EdgeRefusal as e:
        refused.append(str(e))
        coverage.append(cov_row(host, agency, series, f"https://{host}/", 0, 0,
                                "", "", "", "NOT_CHECKED",
                                f"edge refusal: {e}"))
    finally:
        release_host(host, f"{agency} DTLL sitemap enumeration", downloaded,
                     skipped, refused)


PROBE_HOSTS = [
    ("www.doi.gov", "Department of the Interior"),
    ("www.hhs.gov", "Department of Health and Human Services"),
    ("www.hud.gov", "Department of Housing and Urban Development"),
    ("www.epa.gov", "Environmental Protection Agency"),
    ("www.usda.gov", "Department of Agriculture"),
    ("www.ed.gov", "Department of Education"),
]


def probe_host(sess, host, agency, coverage):
    """Bounded sitemap probe. Never prints an absence it did not measure."""
    if not claim_host(host, "Dear Tribal Leader letter enumeration probe"):
        coverage.append(cov_row(host, agency, "agency DTLL series", "", "", "",
                                "", "", "", "NOT_CHECKED",
                                "host held by another poller; deferred"))
        return
    downloaded, skipped, refused = [], [], []
    try:
        ok, why = robots_allows(sess, host, "/sitemap.xml")
        if not ok:
            coverage.append(cov_row(host, agency, "agency DTLL series",
                                    f"https://{host}/robots.txt", "", "", "",
                                    "", "", "ROBOTS_FORBIDDEN", why))
            return
        # `/sitemap.xml` is a convention, not a contract. Where it does not
        # answer, robots.txt's own `Sitemap:` directive is the publisher
        # TELLING you where the index is, and a 403/404 on a guessed path is
        # not a fact about the publisher.
        candidates = [f"https://{host}/sitemap.xml"] + \
            [u for u in _ROBOTS_SITEMAPS.get(host, [])
             if u != f"https://{host}/sitemap.xml"]
        sm, sm_url, st, nb = None, "", 0, 0
        tried = []
        for cand in candidates[:3]:
            st, body, nb, cached = get(sess, cand)
            tried.append(f"{cand} -> HTTP {st}")
            if st == 200 and body:
                sm, sm_url = body, cand
                (skipped if cached else downloaded).append(cand)
                break
        if sm is None:
            coverage.append(cov_row(
                host, agency, "agency DTLL series",
                candidates[0], st, nb, "", "", "",
                "NOT_CHECKED",
                f"no index served: {'; '.join(tried)}. NOT an absence - a "
                f"refused or missing index says nothing about what the agency "
                f"publishes"))
            return
        # A sitemap index may be NESTED - doi.gov's /doi-news/sitemap.xml is
        # itself an index. Counting a nested index as "walked" would report a
        # shard measured that contributed nothing, so it is expanded instead,
        # to a bounded depth and a bounded budget.
        hits, shards_total, shards_walked = set(), 1, 1
        if is_sitemap_index(sm):
            frontier = [(c, 0) for c in sitemap_locs(sm)]
            shards_total = len(frontier)
            shards_walked = 0
            budget = MAX_CHILD
            seen_sm = {sm_url}
            while frontier and budget > 0:
                pri = [x for x in frontier
                       if re.search(r"news|press|page|node|content|document"
                                    r"|letter", x[0], re.I)]
                nxt = (pri or frontier)[0]
                frontier.remove(nxt)
                c, depth = nxt
                if c in seen_sm:
                    continue
                seen_sm.add(c)
                budget -= 1
                st, txt, nb, cached = get(sess, c)
                # a shard that hands back the SAME index is the ?page fail-open
                if st != 200 or txt is None:
                    continue
                (skipped if cached else downloaded).append(c)
                if is_sitemap_index(txt):
                    if depth >= 2:
                        continue
                    kids = [(k, depth + 1) for k in sitemap_locs(txt)
                            if k not in seen_sm]
                    frontier += kids
                    shards_total += len(kids)
                    continue
                shards_walked += 1
                hits |= {u for u in sitemap_locs(txt) if DTLL_URL.search(u)}
        else:
            hits |= {u for u in sitemap_locs(sm) if DTLL_URL.search(u)}
        complete = (shards_walked >= shards_total)
        if complete and not hits:
            status = "NOT_IN_PUBLISHED_INDEX"
            verdict = (f"the publisher's own sitemap ({shards_walked} of "
                       f"{shards_total} shard(s), walked in full) enumerates 0 "
                       f"URL whose slug names a Dear Tribal Leader letter. "
                       f"This is a fact about the INDEX, not about whether the "
                       f"agency writes such letters")
        elif complete:
            status = "REPORTED_FLOOR"
            verdict = (f"{len(hits)} DTLL URL(s) in a sitemap walked in full. "
                       f"A FLOOR: a sitemap need not carry every node")
        else:
            status = "REPORTED_FLOOR_PARTIAL_INDEX"
            verdict = (f"{len(hits)} DTLL URL(s) from {shards_walked} of "
                       f"{shards_total} sitemap shard(s). "
                       f"UNMEASURED beyond those shards - this is NOT an "
                       f"absence and must never be read as one")
        coverage.append(cov_row(host, agency, "agency DTLL series",
                                sm_url, 200, nb,
                                shards_total, shards_walked, len(hits),
                                status, verdict))
        if hits:
            print(f"  [1090] {host}: {len(hits)} DTLL URL(s) "
                  f"({shards_walked}/{shards_total} shards)")
            for u in sorted(hits)[:5]:
                print(f"           {u}")
    except EdgeRefusal as e:
        refused.append(str(e))
        coverage.append(cov_row(host, agency, "agency DTLL series",
                                f"https://{host}/", 0, 0, "", "", "",
                                "NOT_CHECKED", f"edge refusal: {e}"))
    finally:
        release_host(host, "DTLL enumeration probe", downloaded, skipped,
                     refused)


def cov_row(host, agency, series, url, st, nb, shards_total, shards_walked,
            found, status, verdict):
    return {
        "coverage_id": "DTLLCOV-" + stable_digest((host, series, url)),
        "source_host": host, "agency": agency, "series": series, "url": url,
        "http_status": st, "response_bytes": nb,
        "index_shards_total": shards_total, "index_shards_walked": shards_walked,
        "letters_found": found, "coverage_status": status, "verdict": verdict,
        "probed_date": TODAY, "probed_by_script": SCRIPT,
    }


# ---------------------------------------------------------------- invariants


def check_invariants(letters, coverage):
    """Returns list of (invariant, message). Empty == clean."""
    bad = []
    for r in letters:
        if r.get("letter_date"):
            if iso_from_words(r.get("letter_date_verbatim", "")) != r["letter_date"] \
                    and r.get("letter_date_verbatim", "") != r["letter_date"]:
                bad.append(("INV-DTLL-DATE",
                            f"{r.get('letter_id')}: letter_date "
                            f"{r['letter_date']!r} does not reduce from "
                            f"letter_date_verbatim "
                            f"{r.get('letter_date_verbatim')!r}"))
                break
    for r in letters:
        if not r.get("document_url") or not r.get("source_index_url"):
            bad.append(("INV-DTLL-URL",
                        f"{r.get('letter_id')}: missing document_url or "
                        f"source_index_url"))
            break
        if str(r.get("source_index_http_status")) != "200":
            bad.append(("INV-DTLL-URL",
                        f"{r.get('letter_id')}: source index status "
                        f"{r.get('source_index_http_status')} is not 200"))
            break
    for c in coverage:
        if c.get("coverage_status") in ("NOT_IN_SOURCE", "NOT_IN_PUBLISHED_INDEX"):
            if str(c.get("http_status")) != "200":
                bad.append(("INV-DTLL-ABSENCE",
                            f"{c.get('coverage_id')}: NOT_IN_SOURCE on HTTP "
                            f"{c.get('http_status')} - a refusal is not an "
                            f"absence"))
                break
            if c.get("index_shards_walked") != c.get("index_shards_total"):
                bad.append(("INV-DTLL-ABSENCE",
                            f"{c.get('coverage_id')}: NOT_IN_SOURCE with "
                            f"{c.get('index_shards_walked')} of "
                            f"{c.get('index_shards_total')} shards walked"))
                break
    seen = {}
    for r in letters:
        u = r.get("document_url")
        if u in seen:
            bad.append(("INV-DTLL-DUP", f"duplicate document_url {u}"))
            break
        seen[u] = 1
    return bad


def collapse_repeat_listings(letters):
    """Grain is one row per DOCUMENT. A publisher may list the same document
    under more than one date - IHS does it 8 times in 783 documents, mostly an
    enclosure re-attached to a later letter, once a 2009 letter carried into
    the 2010 index. Collapsing on `document_url` and DROPPING the other dates
    would delete something the publisher said, so the earliest stated date is
    the row's date and every other stated date is preserved verbatim in
    `also_listed_under_dates`. Nothing is invented and nothing is discarded.
    """
    by_url = {}
    order = []
    for r in letters:
        u = r["document_url"]
        if u not in by_url:
            by_url[u] = dict(r)
            by_url[u]["index_listing_count"] = 1
            by_url[u]["_dates"] = [r.get("letter_date_verbatim", "")]
            order.append(u)
            continue
        keep = by_url[u]
        keep["index_listing_count"] += 1
        keep["_dates"].append(r.get("letter_date_verbatim", ""))
        a, b = keep.get("letter_date", ""), r.get("letter_date", "")
        if b and (not a or b < a):
            keep["letter_date"] = b
            keep["letter_date_verbatim"] = r.get("letter_date_verbatim", "")
            keep["source_index_url"] = r.get("source_index_url", "")
            keep["source_index_year"] = r.get("source_index_year", "")
    out = []
    for u in order:
        r = by_url[u]
        dates = [d for d in dict.fromkeys(r.pop("_dates")) if d]
        others = [d for d in dates if d != r.get("letter_date_verbatim")]
        r["also_listed_under_dates"] = "; ".join(others)
        out.append(r)
    return out


def write_csv(path, cols, rows):
    part = path.with_suffix(path.suffix + ".part")
    with open(part, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    part.replace(path)


def count_existing_dtll():
    p = CLEAN / "consultation_events.csv"
    if not p.exists():
        return None
    n = 0
    with open(p, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("consultation_type") == "dear_tribal_leader_letter":
                n += 1
    return n


# ---------------------------------------------------------------- selftest


def selftest():
    """Prove each invariant FIRES on an injected violation and not otherwise."""
    base = {
        "letter_id": "DTLL-x", "letter_date": "2025-01-07",
        "letter_date_verbatim": "January 7, 2025",
        "document_url": "https://h/a.pdf", "source_index_url": "https://h/i",
        "source_index_http_status": 200}
    clean_cov = [cov_row("h", "a", "s", "https://h/sitemap.xml", 200, 1, 3, 3,
                         0, "NOT_IN_SOURCE", "walked in full")]
    fired = []
    assert not check_invariants([dict(base)], clean_cov), \
        "selftest: the clean fixture must pass"

    b = dict(base); b["letter_date"] = "2024-01-07"
    got = check_invariants([b], [])
    assert got and got[0][0] == "INV-DTLL-DATE", got
    fired.append("INV-DTLL-DATE")

    b = dict(base); b["source_index_http_status"] = 406
    got = check_invariants([b], [])
    assert got and got[0][0] == "INV-DTLL-URL", got
    fired.append("INV-DTLL-URL")

    for status in ("NOT_IN_SOURCE", "NOT_IN_PUBLISHED_INDEX"):
        # a REFUSAL called an absence
        c = [cov_row("h", "a", "s", "u", 406, 1, 1, 1, 0, status, "x")]
        got = check_invariants([], c)
        assert got and got[0][0] == "INV-DTLL-ABSENCE", (status, got)
        # a PARTLY WALKED index called an absence
        c = [cov_row("h", "a", "s", "u", 200, 1, 9, 2, 0, status, "x")]
        got = check_invariants([], c)
        assert got and got[0][0] == "INV-DTLL-ABSENCE", (status, got)
    fired.append("INV-DTLL-ABSENCE")

    got = check_invariants([dict(base), dict(base)], [])
    assert got and got[0][0] == "INV-DTLL-DUP", got
    fired.append("INV-DTLL-DUP")

    # the date parser must REFUSE rather than guess
    assert iso_from_words("Spring 2025") == ""
    assert iso_from_words("January 2025") == ""
    assert iso_from_words("February 30, 2025") == ""
    assert iso_from_words("January 7, 2025") == "2025-01-07"
    # the SECTION is the claim; IHS's own filename abbreviation refines it
    assert addressed_to_from_filename("DTLL_01072025.pdf")[0] == "tribal_leaders"
    assert addressed_to_from_filename("12-14-2000_Letter.pdf")[0] == \
        "tribal_leaders", "an old-style filename is still a letter on the page"
    assert addressed_to_from_filename("DTLL_DUIOLL_1205.pdf")[0] == \
        "tribal_leaders_and_urban_indian_organization_leaders"
    assert addressed_to_from_filename("DTUIOLL_02222022.pdf")[0] == \
        "tribal_leaders_and_urban_indian_organization_leaders"
    # the publisher's own year folder is the include rule, and the HIPAA
    # footer PDF that appears on all 27 index pages is outside it
    assert IHS_LETTER_PATH.search(
        "https://www.ihs.gov/sites/newsroom/themes/responsive2017/"
        "display_objects/documents/2025_Letters/DTLL_01072025.pdf")
    assert not IHS_LETTER_PATH.search(
        "https://www.ihs.gov/sites/HIPAA/documents/"
        "NoticePrivacyPracticePamphlet.pdf")
    # the tenth bia.gov URL, the one the first pass missed
    assert DTLL_URL.search("https://www.bia.gov/service/progress-act/dtll")
    assert DTLL_URL.search("https://www.bia.gov/news/dear-tribal-leader-letter")
    assert not DTLL_URL.search("https://www.bia.gov/news/tribal-leaders-meet")

    assert not check_invariants([dict(base)], clean_cov), \
        "selftest: restore must return the fixture to clean"
    print("SELFTEST OK - invariants that FIRED on an injected violation: "
          + ", ".join(fired))
    print("           and the restored fixture passes, exit 0")
    return 0


# ---------------------------------------------------------------- main


def run_harvest(probe_only=False):
    RAW.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    before = count_existing_dtll()
    print(f"[1090] BEFORE: consultation_events.csv carries {before} row(s) "
          f"typed dear_tribal_leader_letter")
    letters, coverage = [], []
    sess = requests.Session()
    if not probe_only:
        harvest_ihs(sess, letters, coverage)
        harvest_indian_affairs_drupal(
            sess, "www.bia.gov", "Bureau of Indian Affairs", "DOI-BIA",
            "BIA news: Dear Tribal Leader letters", letters, coverage)
        harvest_indian_affairs_drupal(
            sess, "www.bie.edu", "Bureau of Indian Education", "DOI-BIE",
            "BIE news: Dear Tribal Leader letters", letters, coverage)
    for host, agency in PROBE_HOSTS:
        probe_host(sess, host, agency, coverage)

    letters = collapse_repeat_listings(letters)

    bad = check_invariants(letters, coverage)
    if bad:
        for inv, msg in bad:
            print(f"FAIL {inv}: {msg}")
        return 1

    letters.sort(key=lambda r: (r.get("letter_date") or "9999",
                                r.get("document_url") or ""))
    write_csv(OUT_LETTERS, LETTER_COLS, letters)
    write_csv(OUT_COVERAGE, COVERAGE_COLS, coverage)

    real = [r for r in letters if r["record_kind"] == "letter"]
    by_kind = Counter(r["record_kind"] for r in letters)
    by_agency = Counter(r["agency"] for r in real)
    by_year = Counter((r["letter_date"] or "unknown")[:4] for r in real)
    no_date = sum(1 for r in real if not r["letter_date"])
    OUT_JSON.write_text(json.dumps({
        "harvested_date": TODAY, "script": SCRIPT,
        "cedar_before": {"consultation_events_dear_tribal_leader_letter": before},
        "cedar_after": {
            "dear_tribal_leader_letters_rows": len(letters),
            "letters": len(real),
            "by_record_kind": dict(by_kind),
            "letters_with_no_date_the_publisher_stated": no_date,
            "by_agency": dict(by_agency),
            "by_year": dict(sorted(by_year.items())),
        },
        "coverage": coverage,
        "request_ledger": _LEDGER,
        "requests_by_host": dict(_REQ_BY_HOST),
    }, indent=1), encoding="utf-8")

    print(f"[1090] AFTER : {len(letters)} row(s) -> {OUT_LETTERS.name} "
          f"{dict(by_kind)}")
    for a, n in by_agency.most_common():
        print(f"           {a:38s} {n:5d}")
    print(f"[1090] letters with no date the publisher stated: {no_date} "
          f"(left BLANK; the blank means the source did not say)")
    print(f"[1090] coverage rows: {len(coverage)} -> {OUT_COVERAGE.name}")
    for c in coverage:
        if c["coverage_status"] not in ("ENUMERATED_IN_FULL",):
            print(f"           {c['source_host']:22s} "
                  f"{c['coverage_status']:30s} {c['verdict'][:90]}")
    print(f"[1090] requests: {sum(_REQ_BY_HOST.values())} across "
          f"{len(_REQ_BY_HOST)} host(s) {dict(_REQ_BY_HOST)}")
    return 0


def verify():
    if not OUT_LETTERS.exists():
        print("UNMEASURED: dear_tribal_leader_letters.csv does not exist; "
              "run `harvest` first")
        return 1
    letters = list(csv.DictReader(open(OUT_LETTERS, newline="",
                                       encoding="utf-8")))
    coverage = list(csv.DictReader(open(OUT_COVERAGE, newline="",
                                        encoding="utf-8"))) \
        if OUT_COVERAGE.exists() else []
    for c in coverage:
        for k in ("index_shards_total", "index_shards_walked"):
            c[k] = int(c[k]) if str(c[k]).strip().isdigit() else c[k]
    bad = check_invariants(letters, coverage)
    if bad:
        for inv, msg in bad:
            print(f"FAIL {inv}: {msg}")
        return 1
    real = [r for r in letters if r["record_kind"] == "letter"]
    print(f"VERIFY OK  {len(letters)} rows, "
          f"{dict(Counter(r['record_kind'] for r in letters))}, "
          f"{len(set(r['document_url'] for r in letters))} distinct URLs")
    print(f"           agencies: {dict(Counter(r['agency'] for r in real))}")
    print(f"           date range: "
          f"{min((r['letter_date'] for r in real if r['letter_date']), default='')}"
          f" .. "
          f"{max((r['letter_date'] for r in real if r['letter_date']), default='')}")
    return 0


# ===========================================================================
# STAGE `codebook` - register the table so it can ship
# ===========================================================================
# A clean table that no `codebook_master.csv` block documents is invisible to
# `87_build_dataset_notes.py`, to `512`'s shippable list and therefore to
# `518`'s scoreboard. Two writes, the shape `1072` established: the fragment
# this dataset owns, and an APPEND to the master, because
# `41_build_codebooks.py` rewrites the master wholesale and is the one script
# on NEVER_RUN.
CB_FIELDS = ["dataset", "variable", "type", "units", "pct_filled", "n_rows",
             "published", "access_tier", "description", "generated"]
CB_BLOCK = "09d_dear_tribal_leader_letters"

CB_DESC = {
    "letter_id": "THE KEY. `DTLL-` plus a stable digest of the document URL, "
                 "so the same document keeps the same id across rebuilds and "
                 "no id is ever positional.",
    "channel": "Always CONSULTATION. A Dear Tribal Leader letter is an agency "
               "discharging a government-to-government obligation, never "
               "lobbying.",
    "agency": "The agency that published the letter, in its own name.",
    "agency_code": "HHS-IHS, DOI-BIA or DOI-BIE.",
    "series": "The publisher's own name for the series this document sits in.",
    "letter_date": "The date the PUBLISHER states for the letter. BLANK MEANS "
                   "THE PUBLISHER DID NOT STATE ONE - never that the document "
                   "is undated in reality.",
    "letter_date_verbatim": "That date exactly as the publisher printed it "
                            "(`January 7, 2025`, or an ISO date from JSON-LD). "
                            "`letter_date` must reduce from this string or the "
                            "build fails (INV-DTLL-DATE).",
    "letter_date_basis": "Which element of the publisher's page the date came "
                         "from.",
    "index_listing_count": "How many times the publisher's own index lists "
                           "this document. 799 of 807 rows are 1.",
    "also_listed_under_dates": "Where the publisher listed the same document "
                               "under more than one date, the other dates, "
                               "verbatim. The row's own date is the earliest. "
                               "Nothing the publisher said is discarded.",
    "subject_as_published": "The publisher's own one-line description of the "
                            "letter, verbatim from the index link text (IHS) "
                            "or the page title (BIA/BIE). NOT Cedar's summary.",
    "addressed_to": "`tribal_leaders`, or "
                    "`tribal_leaders_and_urban_indian_organization_leaders` "
                    "where the publisher's own filename says the letter also "
                    "went to Urban Indian Organization leaders (DUIOLL / "
                    "DTUIOLL). Letters addressed ONLY to urban leaders are a "
                    "different series and are not in this table.",
    "addressed_to_basis": "What said so - the index section, or the "
                          "publisher's filename abbreviation.",
    "document_url": "The letter itself, at the publisher. One row per URL; "
                    "the build fails on a repeat (INV-DTLL-DUP).",
    "document_format": "pdf or html, as the publisher serves it.",
    "record_kind": "`letter` 597, `enclosure` 209, `publisher_index_page` 1. "
                   "COUNTING ROWS COUNTS DOCUMENTS, NOT LETTERS - filter "
                   "`record_kind = 'letter'` for a letter count. An enclosure "
                   "is an attachment the publisher labelled as one; a "
                   "publisher_index_page is a page that lists letters and is "
                   "not itself one.",
    "is_enclosure": "1 where record_kind is `enclosure`. Kept for consumers "
                    "that only need the binary split.",
    "linked_pdf_count": "For an HTML page, how many PDFs it links. On a "
                        "`publisher_index_page` this is the measured, "
                        "un-promoted remainder: that many letters the page "
                        "names and this table does not yet carry as rows.",
    "source_index_url": "The publisher's own index this row was enumerated "
                        "from. Every row has one and it returned HTTP 200, or "
                        "the build fails (INV-DTLL-URL).",
    "source_index_http_status": "Always 200. A non-200 index yields a "
                                "coverage row in `dtll_source_coverage.csv`, "
                                "never a letter row.",
    "source_index_year": "The year the publisher filed the letter under.",
    "harvest_method": "`publisher_year_index` or "
                      "`publisher_sitemap_enumeration`. Both are the "
                      "publisher's OWN enumeration; no URL here was guessed. "
                      "962's first draft tried three guessed bia.gov paths, "
                      "collected three 404s and was about to record "
                      "NOT_IN_SOURCE - concluding from three guesses that a "
                      "publisher does not publish.",
    "tier": "B on every row: a machine reading of a published index, never "
            "hand-ruled.",
    "confidence": "The harvester's confidence in the row.",
    "fetched_date": "When Cedar retrieved the index page.",
    "built_date": "When this row was built.",
    "built_by_script": "code/1090_dtll_agency_harvest.py.",
}
CB_GENERIC = ("Column of dear_tribal_leader_letters.csv. See "
              "docs/DEAR_TRIBAL_LEADER_HARVEST.json for the full request "
              "ledger behind every row.")


def _cb_type(vals):
    v = [x for x in vals if str(x or "").strip()]
    if not v:
        return "text"
    if all(re.match(r"^-?\d+$", str(x)) for x in v):
        return "integer"
    if all(re.match(r"^\d{4}-\d{2}-\d{2}$", str(x)) for x in v):
        return "date"
    return "text"


def stage_codebook():
    if not OUT_LETTERS.exists():
        print("  ! run `harvest` first")
        return 1
    rows = list(csv.DictReader(open(OUT_LETTERS, newline="", encoding="utf-8")))
    if not rows:
        print("  ! dear_tribal_leader_letters.csv has no rows")
        return 1
    cols = list(rows[0].keys())
    frag_dir = CLEAN / "codebook"
    frag_dir.mkdir(parents=True, exist_ok=True)
    frag = []
    for col in cols:
        vals = [r.get(col, "") for r in rows]
        filled = sum(1 for x in vals if str(x or "").strip())
        frag.append({
            "dataset": CB_BLOCK, "variable": col, "type": _cb_type(vals),
            "units": "code" if col.endswith(("_id", "_code", "_status"))
                     else "date" if col.endswith(("_date",))
                     else "text",
            "pct_filled": round(100.0 * filled / len(rows), 1),
            "n_rows": len(rows), "published": 1,
            # Federal agency publications, every one. No licensed field and
            # no terms-restricted source: docs/PUBLICATION_POLICY.md's eight
            # hard-listed sources are tribal publishers and none is here.
            "access_tier": "public",
            "description": CB_DESC.get(col, CB_GENERIC),
            "generated": TODAY,
        })
    write_csv(frag_dir / (CB_BLOCK + ".csv"), CB_FIELDS, frag)
    master = CLEAN / "codebook_master.csv"
    existing = list(csv.DictReader(
        open(master, newline="", encoding="utf-8"))) if master.exists() else []
    have = {(r["dataset"], r["variable"]) for r in existing}
    new = [r for r in frag if (r["dataset"], r["variable"]) not in have]
    if new:
        bak = master.with_suffix(f".csv.bak_{TODAY}_pre_1090_dtll_agency_harvest")
        if not bak.exists():
            bak.write_bytes(master.read_bytes())
        with master.open("a", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=CB_FIELDS, extrasaction="ignore")
            for r in new:
                w.writerow(r)
        print(f"  appended {len(new)} rows to codebook_master.csv "
              f"({len(existing)} -> {len(existing) + len(new)}); "
              f"backup {bak.name}")
    else:
        print("  codebook_master.csv already carries this block")
    print(f"  {CB_BLOCK}: {len(frag)} variables documented, {len(rows):,} rows")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--selftest" in args:
        raise SystemExit(selftest())
    cmd = args[0] if args else "harvest"
    if cmd == "harvest":
        raise SystemExit(run_harvest())
    if cmd == "probe":
        raise SystemExit(run_harvest(probe_only=True))
    if cmd == "verify":
        raise SystemExit(verify())
    if cmd == "codebook":
        raise SystemExit(stage_codebook())
    raise SystemExit(f"unknown command {cmd!r}; "
                     f"use harvest | probe | codebook | verify | --selftest")
