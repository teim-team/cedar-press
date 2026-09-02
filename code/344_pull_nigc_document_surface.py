#!/usr/bin/env python3
r"""Cedar Press 344 - the NIGC document surface, enumerated and then fetched.

WHY THIS SCRIPT EXISTS
----------------------
Cedar holds five NIGC families: GGR-by-region, gaming ordinances, declination
letters, the region roster and the gaming-locations map. Nobody had ever asked
what ELSE the agency publishes, so four whole families were missing and one of
them was already NAMED as missing in our own build log:

    docs/GAMING_TEMPORAL_BUILD_LOG.md section 10.6
    "NIGC management contract approvals - not held, and not asserted absent...
     trace_nigc_management_contract is 0 on all 774 rows"

MEASURED 2026-09-01. Each probe is recorded because each one kills an
explanation (docs/PULL_DISCIPLINE.md):

  GET  /robots.txt                          -> 200. Disallows only /wp-admin/
                                               and /wp-content/uploads/wpforms/.
                                               Everything used here is allowed.
                                               Sitemap declared.
  GET  /wp-sitemap.xml                      -> 200, 14 child sitemaps
  GET  /wp-sitemap-posts-wpdmpro-{1,2,3}    -> 200, 4,071 DOCUMENT urls
  GET  /wp-sitemap-taxonomies-wpdmcategory  -> 200, 72 CATEGORIES
  GET  /wp-json/wp/v2/types                 -> 401 rest_not_logged_in
  GET  /wp-json/wp/v2/wpdmpro?per_page=1    -> 401 rest_not_logged_in
  GET  /wp-json/wp/v2/wpdmcategory          -> 401 rest_not_logged_in

So: **the REST API is closed to anonymous callers** - the same 401 script 155
measured on the map route, from WP's own `rest_authentication_errors` filter,
not a nonce failure. The category LISTING PAGES are server-rendered HTML and
are the only public enumeration. They paginate at 24 items with a
`rel="next"` link, and each item is a clean `<article class="wpdmpro ...">`
carrying its title, its /download/<slug>/ URL and a `datePublished` <time>.

  GET  /downloads/enforcement-actions/      -> 200, 24 articles, rel=next
  GET  /download/<slug>/?wpdmdl=<id>        -> 302 -> the wp-content object

TWO DATE FIELDS AND THEY ARE NOT THE SAME FACT
----------------------------------------------
`datePublished` on the listing is **when NIGC posted the file to the website**.
It is NOT when the enforcement action issued. Iowa Tribe of Kansas and Nebraska
NOV-25-01 carries datePublished 2025-09-26 and resolves to
`.../2025/09/2025.09.24-NOV-25-01-Iowa-KS-NE.pdf` - the action is 2025-09-24.

This script therefore stores THREE separate columns and never collapses them:

    wp_post_date        the website's posting date, always present
    document_date       parsed from the RESOLVED filename, blank when absent
    document_date_basis how document_date was obtained, or why it is blank

An action code (`NOV-25-01`, `SA-02-01`, `CO-02-03`) is also parsed out of the
title where the title states one, and its year is recorded separately as
`action_code_year` - a two-digit year in a code is a claim by NIGC, not a date
we computed. Nothing is inferred from one field into another.

WHAT IT WRITES
--------------
  data/raw/external/nigc_documents/_index/*.html          every listing page
  data/raw/external/nigc_documents/_index/*.xml           the sitemaps
  data/raw/external/nigc_documents/pdf/*                  fetched objects
  data/raw/external/nigc_documents/_SOURCE_MANIFEST.csv   md5 + bytes per object
  data/raw/external/nigc_documents/_state.json            resumable checkpoint

  data/staging/nigc_document_surface_staged.csv           4,000+ docs x category
  data/staging/nigc_indian_lands_opinions_staged.csv      1997-2026
  data/staging/nigc_game_classification_opinions_staged.csv  1992-2024
  data/staging/nigc_enforcement_actions_staged.csv
  data/staging/nigc_management_contract_approvals_staged.csv

  review/nigc_document_surface_unresolved_<date>.csv      names the spine
                                                          could not resolve

STAGING, NOT data/clean, DELIBERATELY. These are new grains. A new clean table
needs a codebook fragment and a declared grain before it can ship
(docs/GAMING_SOURCE_AUDIT_2026-08-26.md is 945 lines about what happens when
that step is skipped). The promotion path is written in
docs/datasets/gaming_sources.md.

RULES HONOURED
--------------
* One poller per host. Claims logs/_HOSTLOCK_www.nigc.gov.json, appends and
  exits if a live holder exists, and releases with the FOUR unambiguous
  outcome fields, not a single any_success flag.
* RUN_DEADLINE of 2h; exponential backoff 30s->8min; stop on first refusal
  when nothing has landed.
* Zero fabrication. Every staged row carries source_url, resolved_url and the
  verbatim source name. Names the spine cannot resolve are queued to review/,
  never guessed - resolve_entity from code/33_apply_party_rulings.py is the
  only matcher used, per AGENTS.md.
* Nothing here is licensed. All of it is US federal agency output published by
  NIGC without a licence term; robots.txt permits every path used.

Usage
  py -3 code/344_pull_nigc_document_surface.py --stage surface
  py -3 code/344_pull_nigc_document_surface.py --stage opinions
  py -3 code/344_pull_nigc_document_surface.py --stage docs
  py -3 code/344_pull_nigc_document_surface.py            (all three, resumable)
"""

import argparse
import csv
import hashlib
import html as htmllib
import importlib.util
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
RAW = CEDAR / "data" / "raw" / "external" / "nigc_documents"
IDX = RAW / "_index"
PDF = RAW / "pdf"
STAGING = CEDAR / "data" / "staging"
REVIEW = CEDAR / "review"
SPINE = CEDAR / "data" / "spine"
LOGS = CEDAR / "logs"
TODAY = date.today().isoformat()

HOST = "www.nigc.gov"
BASE = f"https://{HOST}"
LOCK = LOGS / f"_HOSTLOCK_{HOST}.json"
STATE = RAW / "_state.json"
MANIFEST = RAW / "_SOURCE_MANIFEST.csv"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

RUN_DEADLINE_S = 2 * 60 * 60
POLITE_S = 1.2
STARTED = time.time()

# Categories whose OBJECTS this script downloads. The index covers all 72; the
# objects are fetched only where Cedar holds nothing and the family is small
# enough to be a bounded pull. gaming-ordinances (1,417 files) and
# declination-letters are ALREADY HELD and are deliberately not re-fetched.
FETCH_CATEGORIES = [
    "enforcement-actions",
    "approved-management-contracts",
]

ALREADY_HELD = {
    "gaming-ordinances": "data/raw/external/nigc_ordinances/ (1,417 files, code/118)",
    "declination-letters": "data/raw/external/nigc_declinations/ (490 files, code/90)",
    "gross-gaming-revenue-reports": "data/raw/external/nigc/ggr_reports/ (code/84)",
    "gaming-locations": "data/raw/external/nigc/locations/ (code/155)",
}

# The two legal-opinion families are TABLEPRESS indexes, not wpdm categories.
# They are fully structured in the HTML - tribe, parcel, legal theory, outcome,
# date - so the index alone is a dataset before any PDF is opened.
TABLEPRESS_INDEXES = {
    "indian_lands_opinions": {
        "url": f"{BASE}/office-of-general-counsel/legal-opinions/indian-lands-opinions/",
        "table_id": "10",
        "columns": ["source_name_verbatim", "parcel", "legal_theory",
                    "theory_accepted", "opinion_date"],
    },
    "game_classification_opinions": {
        "url": f"{BASE}/office-of-general-counsel/legal-opinions/game-classification-opinions/",
        "table_id": "9",
        "columns": ["game_title", "class_ii_iii", "bingo", "card_games",
                    "card_games_state", "pull_tabs", "internet_gaming",
                    "other", "opinion_date"],
    },
}

SITEMAPS = [
    "wp-sitemap.xml",
    "wp-sitemap-taxonomies-wpdmcategory-1.xml",
    "wp-sitemap-posts-wpdmpro-1.xml",
    "wp-sitemap-posts-wpdmpro-2.xml",
    "wp-sitemap-posts-wpdmpro-3.xml",
    "wp-sitemap-posts-page-1.xml",
]


# ------------------------------------------------------------------ resolver
# AGENTS.md: code/33_apply_party_rulings.py holds the ONE resolver. Import
# resolve_entity; never write another name matcher.
_spec = importlib.util.spec_from_file_location(
    "party_rulings", str(CEDAR / "code" / "33_apply_party_rulings.py"))
_pr = importlib.util.module_from_spec(_spec)
sys.modules["party_rulings"] = _pr
_spec.loader.exec_module(_pr)
resolve_entity = _pr.resolve_entity


def log(msg):
    line = f"{datetime.now().isoformat(timespec='seconds')} {msg}"
    sys.stdout.write(line.encode("ascii", "replace").decode("ascii") + "\n")
    sys.stdout.flush()
    LOGS.mkdir(parents=True, exist_ok=True)
    with open(LOGS / "344_nigc_document_surface.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ---------------------------------------------------------------- host lock
def claim_lock(note):
    LOGS.mkdir(parents=True, exist_ok=True)
    if LOCK.exists():
        try:
            cur = json.loads(LOCK.read_text(encoding="utf-8"))
        except Exception:
            cur = {}
        if cur.get("active") and not cur.get("released"):
            log(f"HOSTLOCK held by pid {cur.get('pid')} ({cur.get('script')}); "
                "appending to queue and exiting.")
            cur.setdefault("queue", []).append(note)
            LOCK.write_text(json.dumps(cur, indent=1), encoding="utf-8")
            sys.exit(3)
    LOCK.write_text(json.dumps({
        "host": HOST, "pid": os.getpid(),
        "script": "code/344_pull_nigc_document_surface.py",
        "started": datetime.now().isoformat() + "Z", "active": True,
        "queue": [note], "note": note,
        "downloaded_this_run": 0, "already_on_disk_skipped": 0,
        "refused_by_host": [], "accepted_then_failed_server_side": 0,
    }, indent=1), encoding="utf-8")


def release_lock(downloaded, skipped, refused):
    try:
        d = json.loads(LOCK.read_text(encoding="utf-8"))
    except Exception:
        d = {"host": HOST}
    d["active"] = False
    d["released"] = datetime.now().isoformat() + "Z"
    d["downloaded_this_run"] = downloaded
    d["already_on_disk_skipped"] = skipped
    d["refused_by_host"] = refused
    d["accepted_then_failed_server_side"] = 0
    LOCK.write_text(json.dumps(d, indent=1), encoding="utf-8")


# ---------------------------------------------------------------- fetching
class Refused(Exception):
    pass


_any_success = [False]
_refused = []


def fetch(url, binary=False, attempts=4):
    """GET with exponential backoff. Distinguishes the three failure shapes."""
    delay = 30
    for i in range(attempts):
        if time.time() - STARTED > RUN_DEADLINE_S:
            raise Refused(f"RUN_DEADLINE exceeded before attempt on {url}")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                body = r.read()
                _any_success[0] = True
                return r.status, r.geturl(), (body if binary else
                                              body.decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                ra = e.headers.get("Retry-After")
                wait = int(ra) if (ra or "").isdigit() else delay
                log(f"  HTTP {e.code} on {url}; honouring wait {wait}s")
                time.sleep(wait)
                delay = min(delay * 2, 480)
                continue
            return e.code, url, (b"" if binary else "")
        except Exception as e:
            shape = "edge_block" if "RemoteDisconnected" in repr(e) else "error"
            log(f"  {shape} {e!r} on {url}; attempt {i+1}/{attempts}")
            if not _any_success[0] and i >= 1:
                raise Refused(f"host refusing and nothing has landed: {url}")
            if time.time() - STARTED + delay > RUN_DEADLINE_S:
                raise Refused(f"RUN_DEADLINE would be crossed sleeping for {url}")
            time.sleep(delay)
            delay = min(delay * 2, 480)
    _refused.append(url)
    return 0, url, (b"" if binary else "")


def load_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"categories_done": [], "objects_done": {}, "runs": []}


def save_state(s):
    RAW.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(s, indent=1), encoding="utf-8")


def strip_tags(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    return htmllib.unescape(s).replace(" ", " ").strip()


def slug_of(url):
    return url.rstrip("/").split("/")[-1]


# --------------------------------------------------------- STAGE 1: surface
ARTICLE_RE = re.compile(
    r'<article class="wpdmpro[^"]*"\s+aria-label="(?P<label>.*?)"'
    r'.*?<a class="entry-title-link"[^>]*href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>'
    r'.*?<time class="entry-time"[^>]*datetime="(?P<dt>[^"]+)"',
    re.S)


def stage_surface(state):
    IDX.mkdir(parents=True, exist_ok=True)
    fetched = 0

    for sm in SITEMAPS:
        p = IDX / sm
        if p.exists():
            continue
        st, _, body = fetch(f"{BASE}/{sm}")
        if st == 200:
            p.write_text(body, encoding="utf-8")
            fetched += 1
        else:
            log(f"  sitemap {sm} -> HTTP {st}")
        time.sleep(POLITE_S)

    cat_xml = IDX / "wp-sitemap-taxonomies-wpdmcategory-1.xml"
    cats = [slug_of(u) for u in
            re.findall(r"<loc>(.*?)</loc>", cat_xml.read_text(encoding="utf-8"))]
    log(f"SURFACE: {len(cats)} wpdm categories declared by the sitemap")

    rows = []
    for cat in cats:
        page = 1
        while True:
            if page == 1:
                url = f"{BASE}/downloads/{cat}/"
                fn = IDX / f"cat_{cat}_p1.html"
            else:
                url = f"{BASE}/downloads/{cat}/page/{page}/"
                fn = IDX / f"cat_{cat}_p{page}.html"

            if fn.exists():
                body = fn.read_text(encoding="utf-8")
                st = 200
            else:
                st, _, body = fetch(url)
                if st == 200:
                    fn.write_text(body, encoding="utf-8")
                    fetched += 1
                    time.sleep(POLITE_S)

            if st != 200:
                log(f"  {cat} page {page} -> HTTP {st}")
                break

            found = list(ARTICLE_RE.finditer(body))
            for m in found:
                rows.append({
                    "wpdm_category": cat,
                    "document_title": strip_tags(m.group("title")) or
                                      htmllib.unescape(m.group("label")),
                    "document_url": m.group("url"),
                    "document_slug": slug_of(m.group("url")),
                    "wp_post_date": m.group("dt")[:10],
                    "listing_page": url,
                    "listing_page_number": page,
                })
            nxt = re.search(r'rel="next" href="([^"]+)"', body)
            if not nxt or not found:
                break
            page += 1
            if page > 200:
                log(f"  {cat}: pagination cap 200 hit - RECORDED, not silent")
                break
        if cat not in state["categories_done"]:
            state["categories_done"].append(cat)
        save_state(state)

    # dedupe on (category, slug); a doc may sit in several categories and each
    # membership is a fact, so we key on the pair rather than the slug alone.
    seen, out = set(), []
    for r in rows:
        k = (r["wpdm_category"], r["document_slug"])
        if k in seen:
            continue
        seen.add(k)
        out.append(r)

    # every document in the sitemap that no category listing surfaced
    sm_urls = set()
    for n in (1, 2, 3):
        p = IDX / f"wp-sitemap-posts-wpdmpro-{n}.xml"
        if p.exists():
            sm_urls |= set(re.findall(r"<loc>(.*?)</loc>",
                                      p.read_text(encoding="utf-8")))
    listed = {r["document_url"].rstrip("/") + "/" for r in out}
    orphans = sorted(u for u in sm_urls if u.rstrip("/") + "/" not in listed)
    for u in orphans:
        out.append({
            "wpdm_category": "_UNCATEGORISED_IN_LISTINGS",
            "document_title": "",
            "document_url": u,
            "document_slug": slug_of(u),
            "wp_post_date": "",
            "listing_page": "wp-sitemap-posts-wpdmpro-*.xml",
            "listing_page_number": "",
        })

    STAGING.mkdir(parents=True, exist_ok=True)
    dest = STAGING / "nigc_document_surface_staged.csv"
    cols = ["wpdm_category", "document_title", "document_url", "document_slug",
            "wp_post_date", "listing_page", "listing_page_number",
            "cedar_holds_this_family", "source_host", "fetched_date",
            "retrieved_by"]
    with open(dest, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in out:
            r["cedar_holds_this_family"] = ALREADY_HELD.get(r["wpdm_category"], "")
            r["source_host"] = HOST
            r["fetched_date"] = TODAY
            r["retrieved_by"] = "code/344_pull_nigc_document_surface.py"
            w.writerow(r)
    log(f"SURFACE: {len(out)} rows -> {dest.relative_to(CEDAR)} "
        f"({len(sm_urls)} docs in sitemap, {len(orphans)} surfaced by no listing)")
    return fetched


# -------------------------------------------------------- STAGE 2: opinions
CELL_RE = re.compile(r'<td class="column-\d+">(.*?)</td>', re.S)
ROW_RE = re.compile(r'<tr class="row-(\d+)[^"]*">(.*?)</tr>', re.S)


def cell_value(c):
    checked = re.search(r"<input[^>]*type=\"checkbox\"[^>]*>", c)
    if checked:
        return "Y" if "checked" in checked.group(0) else "N"
    return strip_tags(c)


def stage_opinions(state, spine):
    IDX.mkdir(parents=True, exist_ok=True)
    fetched, unresolved = 0, []

    for name, spec in TABLEPRESS_INDEXES.items():
        fn = IDX / f"{name}.html"
        if fn.exists():
            body = fn.read_text(encoding="utf-8")
        else:
            st, _, body = fetch(spec["url"])
            if st != 200:
                log(f"  {name} -> HTTP {st}; UNREACHED, recorded not assumed")
                continue
            fn.write_text(body, encoding="utf-8")
            fetched += 1
            time.sleep(POLITE_S)

        m = re.search(r'<table id="tablepress-' + spec["table_id"] + r'".*?</table>',
                      body, re.S)
        if not m:
            log(f"  {name}: tablepress-{spec['table_id']} NOT FOUND in the page - "
                "the index shape changed; refusing to parse rather than guess")
            continue
        table = m.group(0)

        rows = []
        for rid, tr in ROW_RE.findall(table):
            cells = CELL_RE.findall(tr)
            if not cells:
                continue
            link = re.search(r'href="([^"]+)"', cells[0])
            rec = {"source_row": rid,
                   "document_url": htmllib.unescape(link.group(1)) if link else ""}
            for i, col in enumerate(spec["columns"]):
                rec[col] = cell_value(cells[i]) if i < len(cells) else ""
            rows.append(rec)

        if name == "indian_lands_opinions":
            for r in rows:
                nm = r["source_name_verbatim"]
                tid, cname, how = resolve_entity(nm, spine)
                r["tribe_entity_id"] = tid or ""
                r["tribe_canonical_name"] = cname or ""
                r["tribe_match_method"] = how or ""
                if not tid:
                    unresolved.append({"table": name, "source_name_verbatim": nm,
                                       "reason": how or "no_spine_match",
                                       "document_url": r["document_url"]})

        for r in rows:
            r["source_index_url"] = spec["url"]
            r["source_host"] = HOST
            r["fetched_date"] = TODAY
            r["retrieved_by"] = "code/344_pull_nigc_document_surface.py"
            r["opinion_date_basis"] = (
                "verbatim from the Date column of the NIGC index table"
                if r.get("opinion_date") else "blank in the source table")

        STAGING.mkdir(parents=True, exist_ok=True)
        dest = STAGING / f"nigc_{name}_staged.csv"
        cols = ["source_row"] + spec["columns"] + [
            c for c in ("tribe_entity_id", "tribe_canonical_name",
                        "tribe_match_method") if c in (rows[0] if rows else {})
        ] + ["opinion_date_basis", "document_url", "source_index_url",
             "source_host", "fetched_date", "retrieved_by"]
        with open(dest, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        dates = sorted(r["opinion_date"] for r in rows if r.get("opinion_date"))
        log(f"OPINIONS: {name} {len(rows)} rows "
            f"{dates[0] if dates else '-'}..{dates[-1] if dates else '-'} "
            f"-> {dest.relative_to(CEDAR)}")

    if unresolved:
        REVIEW.mkdir(parents=True, exist_ok=True)
        rp = REVIEW / f"nigc_document_surface_unresolved_{TODAY}.csv"
        with open(rp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(unresolved[0].keys()))
            w.writeheader()
            w.writerows(unresolved)
        log(f"OPINIONS: {len(unresolved)} names NOT resolved -> "
            f"{rp.relative_to(CEDAR)} (held, never guessed)")
    return fetched


# ------------------------------------------------------------ STAGE 3: docs
# NIGC's own action codes. The separator between the two number groups is
# OPTIONAL because the archive carries BOTH `NOV-02-01.pdf` and `NOV0102.pdf`
# for the same shape; requiring a separator lost over a hundred codes on the
# first pass. `NDO` is in the archive and was missing from that pass too, which
# is why the prefix list is written out from the filenames rather than guessed.
ACTION_CODE_RE = re.compile(
    r"\b(NOV|SA|CO|TCO|CFA|NDO)[\s\-_.]?(\d{2})[\s\-_.]?(\d{2,3})\b", re.I)
# Two date shapes occur in resolved filenames - `2026.01.12-...` and
# `20240905_...`. Both are read; NOTHING ELSE in a filename is read as a date.
FILENAME_DATE_RE = re.compile(
    r"(20\d{2}|19\d{2})[.\-_](\d{2})[.\-_](\d{2})"
    r"|(?<!\d)(20\d{2}|19\d{2})(\d{2})(\d{2})(?!\d)")


def parse_document_date(resolved_url):
    base = resolved_url.split("/")[-1]
    m = FILENAME_DATE_RE.search(base)
    if m:
        g = [x for x in m.groups() if x is not None]
        y, mo, d = g[0], g[1], g[2]
        try:
            datetime(int(y), int(mo), int(d))
            return f"{y}-{mo}-{d}", "parsed from the resolved filename"
        except ValueError:
            return "", f"filename carried an impossible date {m.group(0)}"
    m = re.search(r"/wp-content/uploads/(20\d{2})/(\d{2})/", resolved_url)
    if m:
        return "", (f"no date in the filename; the upload path says "
                    f"{m.group(1)}-{m.group(2)} but an UPLOAD MONTH IS NOT A "
                    "DOCUMENT DATE and is not promoted")
    return "", "no date in the resolved URL"


def md5_of(b):
    h = hashlib.md5()
    h.update(b)
    return h.hexdigest()


# -------- THE DEFECT THIS SECTION EXISTS TO PREVENT, measured 2026-09-01 -----
# A first version of this stage fetched `<landing>/?wpdmdl=` - the parameter
# present and EMPTY. WP Download Manager answered **HTTP 200 with a valid PDF**
# every single time, and it was the SAME PDF every single time: NIGC's generic
# "Helpful Hints: Requesting a Game Classification Opinion", md5
# a917db80b6027b0ffd8a8b233eb8331a. **302 enforcement actions were "downloaded"
# and 302 of them were that one file.** Nothing in the response said so - right
# status, right content type, right magic bytes, plausible size.
#
# It is the `AN ACCEPTED TOKEN IS NOT A WORKING JOB` failure in a new costume
# (docs/PULL_DISCIPLINE.md, 2026-08-12): the transport succeeded and the
# CONTENT was wrong. Two things now stand between this script and a repeat:
#
#   1. the download URL is READ OFF THE LANDING PAGE and must contain the
#      package's own slug, so a site-navigation `?wpdmdl=` link - the trap that
#      makes an empty parameter look reasonable - cannot match; and
#   2. IDENTICAL_MD5_CEILING. If one md5 comes back for more than a handful of
#      distinct slugs the run STOPS. A duplicate is normal in this corpus
#      (NIGC re-posts the same letter under two slugs); three hundred are not.
IDENTICAL_MD5_CEILING = 6
_seen_md5 = {}

# The real link lives in the file-list widget and always carries the package's
# own slug plus a `filename=` naming the object. A mega-menu link is
# `https://www.nigc.gov/?wpdmdl=3974` - no slug - and is excluded by construction.
DL_LINK_RE_T = (r'href="(https://www\.nigc\.gov/download/{slug}/'
                r'\?wpdmdl=\d+[^"]*)"')


def resolve_download_link(landing_url, slug):
    """Return (http_status, real download URL or '') for one /download/ page."""
    st, _, body = fetch(landing_url)
    if st != 200 or not body:
        return st, ""
    m = re.search(DL_LINK_RE_T.format(slug=re.escape(slug)), body)
    if not m:
        return st, ""
    time.sleep(POLITE_S)
    return st, htmllib.unescape(m.group(1))


def stage_docs(state, spine):
    PDF.mkdir(parents=True, exist_ok=True)
    surface = STAGING / "nigc_document_surface_staged.csv"
    if not surface.exists():
        log("DOCS: no surface index on disk; run --stage surface first")
        return 0, 0

    rows = list(csv.DictReader(open(surface, encoding="utf-8-sig")))
    targets = [r for r in rows if r["wpdm_category"] in FETCH_CATEGORIES]
    log(f"DOCS: {len(targets)} objects across {len(FETCH_CATEGORIES)} categories")

    man = []
    if MANIFEST.exists():
        man = list(csv.DictReader(open(MANIFEST, encoding="utf-8-sig")))
    have = {m["source_url"]: m for m in man}
    by_md5 = {m["md5"]: m["local_name"] for m in man if m.get("md5")}

    downloaded = skipped = 0
    skipped_slugs = []
    staged = {c: [] for c in FETCH_CATEGORIES}

    def local_stem(row):
        return re.sub(r"[^A-Za-z0-9._-]", "_",
                      row["wpdm_category"] + "__" + row["document_slug"])

    # RESUME WITHOUT RE-DOWNLOADING. The manifest is written once, at the end,
    # so a run stopped by RUN_DEADLINE leaves the objects on disk and no
    # manifest. Recovering them from the FILESYSTEM as well as the manifest is
    # what makes rule 6 of PULL_DISCIPLINE true here - a killed poller must
    # lose nothing, or stopping it is not free.
    on_disk = {}
    for row in targets:
        stem = local_stem(row)
        for cand in PDF.glob(stem + ".*"):
            on_disk[row["document_url"]] = cand
            break

    for r in targets:
        url = r["document_url"]
        if url not in have and url in on_disk:
            p = on_disk[url]
            body = p.read_bytes()
            have[url] = {"resolved_url": "", "local_name": p.name,
                         "http_status": "200_prior_run", "bytes": str(len(body)),
                         "md5": md5_of(body)}
            man.append({
                "local_path": f"data/raw/external/nigc_documents/pdf/{p.name}",
                "local_name": p.name, "wpdm_category": r["wpdm_category"],
                "source_host": HOST, "source_url": url, "resolved_url": "",
                "index_title": r["document_title"],
                "wp_post_date": r["wp_post_date"],
                "bytes": len(body), "md5": md5_of(body),
                "md5_duplicate_of": "",
                "http_status": "200_prior_run", "fetched_date": TODAY,
                "retrieved_by": "code/344_pull_nigc_document_surface.py",
            })
        if url in have:
            # NAMED, not just counted. This is an idempotent skip rather than a
            # drop - the object is on disk and its row is still written below -
            # but a bare counter is unactionable either way, which is the whole
            # lesson of script 87's twenty silent days. Every skipped slug is
            # named in _state.json, and the log prints the first few.
            skipped += 1
            skipped_slugs.append(r["document_slug"])
            m = have[url]
            resolved = m.get("resolved_url", "")
            local = m.get("local_name", "")
            status = m.get("http_status", "")
            nbytes = m.get("bytes", "")
            digest = m.get("md5", "")
        else:
            st, dl = resolve_download_link(url, r["document_slug"])
            if not dl:
                log(f"  NO DOWNLOAD LINK on {url} (landing page HTTP {st}) - "
                    "recorded as unreached, NOT guessed")
                _refused.append(url)
                continue
            st, resolved, body = fetch(dl, binary=True)
            if st != 200 or not body:
                log(f"  UNREACHED {dl} -> HTTP {st}")
                _refused.append(url)
                continue
            digest_probe = md5_of(body)
            if digest_probe in _seen_md5 and _seen_md5[digest_probe] != 1:
                pass  # counted below; the guard runs on the accumulated count
            _seen_md5[digest_probe] = _seen_md5.get(digest_probe, 0) + 1
            if _seen_md5[digest_probe] > IDENTICAL_MD5_CEILING:
                raise Refused(
                    f"SAME-OBJECT GUARD FIRED: md5 {digest_probe} has now come "
                    f"back for {_seen_md5[digest_probe]} distinct slugs. The "
                    f"host is serving one document for many requests. Stopping "
                    f"rather than writing more of it. Last url: {dl}")
            ext = ".pdf" if body[:4] == b"%PDF" else \
                  os.path.splitext(resolved.split("?")[0])[1] or ".bin"
            local = re.sub(r"[^A-Za-z0-9._-]", "_",
                           r["wpdm_category"] + "__" + r["document_slug"]) + ext
            digest = md5_of(body)
            (PDF / local).write_bytes(body)
            nbytes, status = len(body), st
            downloaded += 1
            man.append({
                "local_path": f"data/raw/external/nigc_documents/pdf/{local}",
                "local_name": local, "wpdm_category": r["wpdm_category"],
                "source_host": HOST, "source_url": url, "resolved_url": resolved,
                "index_title": r["document_title"], "wp_post_date": r["wp_post_date"],
                "bytes": nbytes, "md5": digest,
                "md5_duplicate_of": by_md5.get(digest, ""),
                "http_status": status, "fetched_date": TODAY,
                "retrieved_by": "code/344_pull_nigc_document_surface.py",
            })
            by_md5.setdefault(digest, local)
            time.sleep(POLITE_S)

        doc_date, basis = parse_document_date(resolved or "")
        if not doc_date and not resolved:
            # resumed run: the interrupted run did not persist the resolved URL.
            # NIGC slugs frequently carry the same date the filename does, so
            # try the slug - under its OWN basis string, because a slug is the
            # website's naming and the filename is the document's.
            doc_date, sbasis = parse_document_date("x/" + r["document_slug"])
            basis = (f"resolved URL not persisted by an earlier interrupted "
                     f"run; {sbasis} of the /download/ slug"
                     if doc_date else
                     "resolved URL not persisted by an earlier interrupted run, "
                     "and the slug carries no date")
        am = ACTION_CODE_RE.search(r["document_title"]) or \
            ACTION_CODE_RE.search(resolved or "")
        staged[r["wpdm_category"]].append({
            "source_name_verbatim": r["document_title"],
            "wpdm_category": r["wpdm_category"],
            "action_code": (am.group(0).upper().replace("_", "-").replace(".", "-")
                            if am else ""),
            "action_type": (am.group(1).upper() if am else ""),
            "action_code_year": (am.group(2) if am else ""),
            "action_code_year_basis": (
                "two-digit year as printed inside NIGC's own action code; NOT "
                "expanded to four digits and NOT used as a date" if am else ""),
            "document_date": doc_date,
            "document_date_basis": basis,
            "wp_post_date": r["wp_post_date"],
            "wp_post_date_basis": "the website's posting date, not the action date",
            "document_url": url, "resolved_url": resolved,
            "local_path": f"data/raw/external/nigc_documents/pdf/{local}" if local else "",
            "bytes": nbytes, "md5": digest, "http_status": status,
            "source_host": HOST, "fetched_date": TODAY,
            "retrieved_by": "code/344_pull_nigc_document_surface.py",
        })

    unresolved = []
    for cat, recs in staged.items():
        for rec in recs:
            tid, cname, how = resolve_entity(rec["source_name_verbatim"], spine)
            if not tid:
                # enforcement titles carry an action code after the name
                stem = re.split(r"\s+(?:NOV|SA|CO|TCO|CFA|NDO)[\s\-]",
                                rec["source_name_verbatim"], maxsplit=1)[0]
                stem = re.sub(r"^\d{4}[.\-]\d{2}[.\-]\d{2}[_\s]*", "", stem).strip()
                if stem and stem != rec["source_name_verbatim"]:
                    tid, cname, how = resolve_entity(stem, spine)
            rec["tribe_entity_id"] = tid or ""
            rec["tribe_canonical_name"] = cname or ""
            rec["tribe_match_method"] = how or ""
            if not tid:
                unresolved.append({"table": cat,
                                   "source_name_verbatim": rec["source_name_verbatim"],
                                   "reason": how or "no_spine_match",
                                   "document_url": rec["document_url"]})

    STAGING.mkdir(parents=True, exist_ok=True)
    outname = {"enforcement-actions": "nigc_enforcement_actions_staged.csv",
               "approved-management-contracts":
                   "nigc_management_contract_approvals_staged.csv"}
    for cat, recs in staged.items():
        if not recs:
            continue
        dest = STAGING / outname[cat]
        cols = list(recs[0].keys())
        with open(dest, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(recs)
        keyed = sum(1 for x in recs if x["tribe_entity_id"])
        dd = sorted(x["document_date"] for x in recs if x["document_date"])
        log(f"DOCS: {cat} {len(recs)} rows, {keyed} keyed to the spine, "
            f"document_date {dd[0] if dd else '-'}..{dd[-1] if dd else '-'} "
            f"-> {dest.relative_to(CEDAR)}")

    if man:
        cols = ["local_path", "local_name", "wpdm_category", "source_host",
                "source_url", "resolved_url", "index_title", "wp_post_date",
                "bytes", "md5", "md5_duplicate_of", "http_status",
                "fetched_date", "retrieved_by"]
        with open(MANIFEST, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(man)
        log(f"DOCS: manifest {len(man)} objects -> {MANIFEST.relative_to(CEDAR)}")

    if skipped_slugs:
        state["objects_done"] = sorted(set(
            state.get("objects_done", []) if isinstance(
                state.get("objects_done"), list) else []) | set(skipped_slugs))
        save_state(state)
        log(f"DOCS: {len(skipped_slugs)} object(s) already on disk, NAMED in "
            f"_state.json['objects_done'] - first: "
            f"{', '.join(skipped_slugs[:5])}"
            + (" ..." if len(skipped_slugs) > 5 else ""))

    if unresolved:
        REVIEW.mkdir(parents=True, exist_ok=True)
        rp = REVIEW / f"nigc_documents_unresolved_{TODAY}.csv"
        with open(rp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(unresolved[0].keys()))
            w.writeheader()
            w.writerows(unresolved)
        log(f"DOCS: {len(unresolved)} names NOT resolved -> {rp.relative_to(CEDAR)}")

    return downloaded, skipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["surface", "opinions", "docs", "all"],
                    default="all")
    a = ap.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    claim_lock(f"nigc_document_surface:{a.stage}")
    state = load_state()
    spine = list(csv.DictReader(
        open(SPINE / "cedar_entity_spine.csv", encoding="utf-8-sig")))
    log(f"344 NIGC document surface, stage={a.stage}, spine={len(spine)} entities")

    downloaded = skipped = 0
    try:
        if a.stage in ("surface", "all"):
            downloaded += stage_surface(state)
        if a.stage in ("opinions", "all"):
            downloaded += stage_opinions(state, spine)
        if a.stage in ("docs", "all"):
            d, s = stage_docs(state, spine)
            downloaded += d
            skipped += s
    except Refused as e:
        log(f"STOPPED: {e}")
        state.setdefault("runs", []).append(
            {"date": TODAY, "stage": a.stage, "stopped": str(e)})
        save_state(state)
        release_lock(downloaded, skipped, _refused or [str(e)])
        sys.exit(4)

    state.setdefault("runs", []).append(
        {"date": TODAY, "stage": a.stage, "downloaded": downloaded,
         "skipped": skipped, "refused": _refused})
    save_state(state)
    release_lock(downloaded, skipped, _refused)
    log(f"DONE downloaded={downloaded} already_on_disk_skipped={skipped} "
        f"refused={len(_refused)}")


if __name__ == "__main__":
    main()
