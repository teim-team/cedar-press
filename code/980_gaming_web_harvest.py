"""
980_gaming_web_harvest.py — GAMING PROPERTY WEB HARVEST, COORDINATED PER TRIBE

Owner mandate (2026-09-02): *"You should be scraping casino websites... coordinate
per-tribe"* and *"All these website scrapings, check for stuff that's not published
on the website for a user to see, but is in the HTML code."*

ONE PASS PER NATION. For each facility-bearing tribe this takes its casino /
gaming-authority hosts AND its TERO / vendor / procurement surface together,
rather than one pass per dataset.

WHAT IT LOOKS FOR
  * facility identity     — name, address, hours, geo, telephone, property type
  * capacity signals      — gaming positions, table counts, hotel rooms, event
                            space (SELF-PUBLISHED; see the fence below)
  * vendor / procurement / TERO / "doing business with us" pages
  * HIDDEN DATA           — docs/HIDDEN_DATA_TECHNIQUES.md, techniques 1-13

THE FENCE (docs/PUBLICATION_POLICY.md, START_HERE licensing section)
  Every capacity row this writes carries assertion_class =
  SELF_PUBLISHED_OPERATOR_ASSERTION. **A self-published capacity figure is never
  a regulator's figure** and these values must NEVER be summed against NIGC or
  state-regulator numbers. `not_summable_with` says so on every row.

SCOPE BOUNDARY
  A separate agent owns `gaming` dataset promotion in the 960-979 band. This
  script writes ONLY its own files and never edits
  gaming_property_self_published_assertions.csv / _claims.csv in place.

BOUNDARY (docs/HIDDEN_DATA_TECHNIQUES.md — non-negotiable)
  * robots.txt is fetched WITH OUR OWN UA and a 403/404/empty body means
    ALLOWED, not blocked (PULL_DISCIPLINE.md: 22 phantom blocks came from
    urllib.robotparser reading a 403 as disallow_all). A real Disallow matching
    the path is a refusal and stays one.
  * no admin / staging / login path is ever requested. /wp-admin/admin-ajax.php
    is RECORDED WHEN OBSERVED AND NEVER FETCHED — it lives under /wp-admin/.
  * hosts belonging to a TERMS_STATED_RESTRICTIVE source are excluded by every
    route, including the WordPress media API and Wayback. Terms are a decision
    the publisher made, not an obstacle to route around.

SELECTION DECLARATION
  Leg used:    KNOWN_IDENTIFIER (Cedar's own facility + web-map universe).
  Leg missing: TYPE_FILTER — there is no third-party register of "tribal casino
               websites" to filter on, so this pull CANNOT discover a facility
               Cedar does not already hold. population_basis on every row is
               `cedar_gaming_facilities_and_web_map`.

STAGES
  py -3 code/980_gaming_web_harvest.py targets
  py -3 code/980_gaming_web_harvest.py probe   [--limit N] [--deadline-min M]
  py -3 code/980_gaming_web_harvest.py pages   [--limit N] [--deadline-min M]
  py -3 code/980_gaming_web_harvest.py build
  py -3 code/980_gaming_web_harvest.py verify  [--selftest]

FLUSH DISCIPLINE: every stage writes to disk PER ENTITY (per host), never at the
end. Nine shard agents once buffered their maps and ~1,159 rows were nearly lost.
"""
import argparse
import csv
import hashlib
import html
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.robotparser as robotparser
from datetime import date, datetime, timezone

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STG = os.path.join(ROOT, "data", "staging", "gaming_web_harvest")
RAW = os.path.join(STG, "raw")
CLEAN = os.path.join(ROOT, "data", "clean")
LOGS = os.path.join(ROOT, "logs")
for d in (STG, RAW, LOGS):
    os.makedirs(d, exist_ok=True)

TARGETS = os.path.join(STG, "targets.csv")
PROBE = os.path.join(STG, "host_probe.jsonl")
PAGES = os.path.join(STG, "page_fetch.jsonl")
OBS = os.path.join(CLEAN, "gaming_web_harvest_observations.csv")
COV = os.path.join(CLEAN, "gaming_web_harvest_coverage.csv")
HOSTLOCK = os.path.join(LOGS, "_HOSTLOCK_gaming_web_harvest_980.json")

WEB_MAP = os.path.join(ROOT, "data", "staging", "cedar_web_map.csv")
FACILITIES = os.path.join(CLEAN, "gaming_facilities.csv")
VENDOR_REG = os.path.join(ROOT, "review", "tribal_vendor_list_registry_2026-08-26.csv")

UA = ("CedarPressResearchBot/1.0 (+research dataset on Native economic activity; "
      "contact elijahsamsonmoreno@gmail.com)")
BROWSERISH = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "close",
}
TIMEOUT = 25
# Politeness: the binding constraint is PER-HOST. A host never sees more than
# one request every PER_HOST_DELAY seconds and receives ~7 requests in total —
# which is gentler than crawling it. Distinct hosts are interleaved across
# WORKERS threads, each of which owns a DISJOINT set of hosts, so no host is
# ever hit concurrently. GLOBAL_DELAY then bounds our aggregate egress rate.
# (PULL_DISCIPLINE.md's "six concurrent workers tripped it" was six workers
# against ONE host; this is one worker per host across many hosts.)
GLOBAL_DELAY = 0.30         # aggregate, across all hosts
PER_HOST_DELAY = 2.5        # a single host never sees more than 1 req / 2.5s
WORKERS = 6
MAX_BYTES = 8 * 1024 * 1024
READ_BUDGET_S = 40          # hard wall-clock cap on one response body

TODAY = date.today().isoformat()
NOW = datetime.now(timezone.utc).isoformat()

ASSERTION_CLASS = "SELF_PUBLISHED_OPERATOR_ASSERTION"
NOT_SUMMABLE = ("nigc_gross_gaming_revenue;state_regulator_device_counts;"
                "gaming_facility_metrics.official")
POPULATION_BASIS = "cedar_gaming_facilities_and_web_map"

# ---------------------------------------------------------------------------
# TERMS_STATED_RESTRICTIVE — excluded by EVERY route. Sourced from
# review/tribal_vendor_list_registry_2026-08-26.csv (source_terms_status) and
# from the standing list in the workstream mandate. Both are applied.
# ---------------------------------------------------------------------------
RESTRICTED_TRIBE_IDS = {
    "TRBF-NAVAJO-00",   # navajoeconomy.org "All Rights Reserved"
    "TRBF-COLVLL-00",   # Confederated Colville
    "TRBF-YAKAMA-00",   # Yakama
    "TRBF-UMATLL-00",   # CTUIR / Umatilla
    "TRBF-CHKSWN-00",   # Chickasaw — terms name company directories
    "TRBF-FSTCTY-00",   # Forest County Potawatomi
    "TRBF-STHUTE-00",   # Southern Ute
    "ANRC-NANARC-00",   # NANA / Akima
    "TRBF-STLMSH-00",   # Stillaguamish
}
RESTRICTED_NAME_TOKENS = (
    "colville", "yakama", "umatilla", "ctuir", "chickasaw", "nana ",
    "akima", "southern ute", "forest county potawatomi", "stillaguamish",
    "navajo",
)
RESTRICTED_HOST_SUFFIXES = (
    "navajoeconomy.org", "navajo-nsn.gov", "navajocasino.com", "navajocasinos.com",
    "navajogaming.com", "navajogaming.org", "twinarrows.com", "twinarrows.net",
    "twinarrowsnavajocasinoresort.com", "firerockcasino.com", "flowingwatercasino.com",
    "northernedgecasino.com",
    # NOTE: dancingeaglecasino.com was in this list on the first pass and was
    # WRONG — Dancing Eagle is Pueblo of Laguna, not Navajo. Removed 2026-09-02.
    # An over-broad restriction costs a nation its coverage just as surely as a
    # missed one costs the publisher their terms.
    "colvilletribes.com", "colvillecasinos.com",
    "yakama.com", "legendscasino.com",
    "ctuir.org", "wildhorseresort.com",
    "chickasaw.net", "chickasawbusinessnetwork.com", "winstar.com",
    "fcpotawatomi.com", "paysbig.com",
    "southernute-nsn.gov", "sugf.com", "skyutecasino.com",
    "nana.com", "akima.com",
    "stillaguamish.com", "angelofthewinds.com",
)

# Never requested. Not "hidden data" — someone's private infrastructure.
FORBIDDEN_PATH_MARKERS = (
    "/wp-admin", "/wp-login", "/admin", "/administrator", "/.env", "/.git",
    "/backup", "/phpmyadmin", "/xmlrpc.php", "/user/login", "/login",
    "/signin", "/wp-content/debug.log",
)

# Parked / hijacked signals. A guessed domain that returns 200 is fabrication
# with a status code next to it (PULL_DISCIPLINE.md, shard H).
PARKED_MARKERS = (
    "hugedomains", "domain is for sale", "buy this domain", "godaddy.com/domainsearch",
    "sedoparking", "parkingcrew", "this domain may be for sale", "afternic",
    "dan.com", "domain name is available",
)
HIJACK_MARKERS = (
    "situs slot", "slot gacor", "judi bola", "togel", "bandar", "sbobet",
    "pragmatic play", "rtp slot", "แทงบอล", "บาคาร่า", "สล็อต", "카지노",
    "xn--", "free spins no deposit bonus code",
)

HIDDEN_ENDPOINTS = [
    ("wp_types", "/wp-json/wp/v2/types", "3 (WP REST custom post types)"),
    ("wp_media_pdf", "/wp-json/wp/v2/media?per_page=100&mime_type=application/pdf",
     "3 (WP REST media, mime_type=application/pdf)"),
    ("wp_pages", "/wp-json/wp/v2/pages?per_page=100&_fields=id,link,title,date,modified",
     "3 (WP REST pages, including pages absent from the nav)"),
    ("sitemap_index", "/sitemap_index.xml", "4 (sitemap index)"),
    ("sitemap", "/sitemap.xml", "4 (sitemap)"),
    ("feed", "/feed/", "13 (RSS feed)"),
]

VENDOR_URL_TOKENS = (
    "tero", "vendor", "procure", "purchasing", "bid", "rfp", "rfq", "solicitation",
    "doing-business", "do-business", "dobusiness", "supplier", "contracting",
    "business-license", "business-licence", "tribal-employment-rights",
)
CAPACITY_URL_TOKENS = (
    "casino", "gaming", "hotel", "rooms", "stay", "resort", "meeting", "event",
    "convention", "conference", "banquet", "slots", "table-games", "poker",
    "bingo", "about", "fact-sheet", "factsheet", "press", "media",
)

import threading

_last_global = [0.0]
_last_host = {}
_robots_cache = {}
_global_lock = threading.Lock()
_io_lock = threading.Lock()
_print_lock = threading.Lock()


def log(*a):
    with _print_lock:
        print(*a, flush=True)


def sleep_for(host):
    """Two independent gates: aggregate egress, and this host's own cadence."""
    while True:
        with _global_lock:
            now = time.time()
            w = GLOBAL_DELAY - (now - _last_global[0])
            if w <= 0:
                _last_global[0] = now
                break
        time.sleep(max(w, 0.01))
    hw = PER_HOST_DELAY - (time.time() - _last_host.get(host, 0.0))
    if hw > 0:
        time.sleep(hw)
    _last_host[host] = time.time()


def is_restricted_host(host):
    h = (host or "").lower()
    return any(h == s or h.endswith("." + s) for s in RESTRICTED_HOST_SUFFIXES)


def is_restricted_tribe(tribe_id, name):
    if (tribe_id or "") in RESTRICTED_TRIBE_IDS:
        return True
    n = (name or "").lower()
    return any(t in n for t in RESTRICTED_NAME_TOKENS)


def forbidden_path(url):
    p = urllib.parse.urlparse(url).path.lower()
    return any(m in p for m in FORBIDDEN_PATH_MARKERS)


def robots_verdict(scheme, host):
    """Fetch robots.txt with OUR declared UA. 403/404/empty == ALLOWED.

    PULL_DISCIPLINE.md: urllib.robotparser.read() fetches with Python-urllib and
    reads a 403 as disallow_all; 22 hosts were lost to that. Never let .read()
    do the fetch.
    """
    key = host
    if key in _robots_cache:
        return _robots_cache[key]
    rp = None
    note = ""
    sleep_for(host)
    try:
        r = requests.get(f"{scheme}://{host}/robots.txt", headers=BROWSERISH,
                         timeout=15, allow_redirects=True)
        if r.status_code == 200 and (r.text or "").strip():
            rp = robotparser.RobotFileParser()
            rp.parse(r.text.splitlines())
            note = "robots.txt parsed"
        else:
            note = f"robots.txt http {r.status_code} or empty -> treated as ALLOWED"
    except Exception as e:
        note = f"robots.txt {type(e).__name__} -> treated as ALLOWED"
    _robots_cache[key] = (rp, note)
    return _robots_cache[key]


def robots_ok(url):
    p = urllib.parse.urlparse(url)
    rp, note = robots_verdict(p.scheme or "https", p.netloc)
    if rp is None:
        return True, note
    try:
        return bool(rp.can_fetch(UA, url)), note
    except Exception:
        return True, note + "; can_fetch raised -> allowed"


def fetch(url, accept=None):
    """One request. Returns a dict; never raises."""
    hdr = dict(BROWSERISH)
    if accept:
        hdr["Accept"] = accept
    host = urllib.parse.urlparse(url).netloc
    sleep_for(host)
    out = {"url": url, "http_status": "", "content_type": "", "bytes": 0,
           "final_url": "", "text": "", "content": b"", "note": ""}
    try:
        r = requests.get(url, headers=hdr, timeout=(10, TIMEOUT), allow_redirects=True,
                         stream=True)
        # WALL-CLOCK BUDGET. requests' read timeout is PER SOCKET READ: a server
        # that trickles a few bytes every 20s never trips it. On 2026-09-02 that
        # hung a worker for seven minutes with no error and no output. A timeout
        # that cannot bound the total is not a timeout.
        started = time.time()
        chunks, got, truncated, timed_out = [], 0, False, False
        for chunk in r.iter_content(chunk_size=65536, decode_unicode=False):
            if chunk:
                chunks.append(chunk)
                got += len(chunk)
            if got > MAX_BYTES:
                truncated = True
                break
            if time.time() - started > READ_BUDGET_S:
                timed_out = True
                break
        raw = b"".join(chunks)[:MAX_BYTES]
        out["http_status"] = str(r.status_code)
        out["content_type"] = (r.headers.get("Content-Type") or "").split(";")[0].strip()
        out["bytes"] = len(raw)
        out["final_url"] = r.url
        out["content"] = raw
        out["headers"] = {k: v for k, v in r.headers.items()
                          if k.lower() in ("x-wp-total", "x-wp-totalpages", "last-modified",
                                           "server", "x-powered-by")}
        if truncated:
            # A truncated read must report TRUNCATED, never "no content".
            out["note"] = f"TRUNCATED at {MAX_BYTES} bytes"
        elif timed_out:
            out["note"] = (f"READ_BUDGET_EXCEEDED after {READ_BUDGET_S}s; "
                           f"{got} bytes received, body is PARTIAL")
        enc = r.encoding or "utf-8"
        try:
            out["text"] = raw.decode(enc, errors="replace")
        except Exception:
            out["text"] = raw.decode("utf-8", errors="replace")
        r.close()
    except Exception as e:
        out["http_status"] = "TRANSPORT_FAILURE"
        out["note"] = f"{type(e).__name__}: {str(e)[:160]}"
    return out


def save_raw(url, content, ext):
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
    host = re.sub(r"[^A-Za-z0-9._-]", "_", urllib.parse.urlparse(url).netloc)
    fn = f"{host}__{h}{ext}"
    with open(os.path.join(RAW, fn), "wb") as f:
        f.write(content)
    return fn, hashlib.md5(content).hexdigest()


def appendl(path, rec):
    """Flush per entity, not at the end. Nine shard agents once buffered their
    maps and only 1 of 9 had written anything when they were interrupted."""
    line = json.dumps(rec, ensure_ascii=False) + "\n"
    with _io_lock:
        with io.open(path, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())


def load_done(path, keyfn):
    done = set()
    if os.path.exists(path):
        for line in io.open(path, encoding="utf-8"):
            try:
                done.add(keyfn(json.loads(line)))
            except Exception:
                pass
    return done


# ===========================================================================
# STAGE 1 — targets, coordinated per tribe
# ===========================================================================
def stage_targets():
    fac = list(csv.DictReader(io.open(FACILITIES, encoding="utf-8-sig")))
    wm = list(csv.DictReader(io.open(WEB_MAP, encoding="utf-8-sig")))

    by_tribe = {}
    for f in fac:
        tid = (f.get("tribe_id") or "").strip()
        if not tid:
            continue
        d = by_tribe.setdefault(tid, {
            "tribe_id": tid,
            "cedar_uid": (f.get("cedar_uid") or "").strip(),
            "tribe_name": (f.get("tribe_canonical_name") or f.get("tribe") or "").strip(),
            "facility_ids": [], "facility_names": [], "states": set(),
        })
        d["facility_ids"].append(f.get("facility_id") or "")
        d["facility_names"].append(f.get("facility_name") or "")
        if f.get("state"):
            d["states"].add(f["state"])

    uid_to_tribe = {}
    for tid, d in by_tribe.items():
        if d["cedar_uid"]:
            uid_to_tribe[d["cedar_uid"]] = tid

    keep_types = {"casino", "gaming_authority", "unverified_casino",
                  "government", "tero", "procurement", "business_licence",
                  "corporate", "subsidiary_list"}
    rows = []
    seen = set()
    for r in wm:
        uid = (r.get("cedar_uid") or "").strip()
        tid = uid_to_tribe.get(uid)
        if not tid:
            continue
        ut = (r.get("url_type") or "").strip()
        if ut not in keep_types:
            continue
        url = (r.get("url") or "").strip()
        m = re.match(r"https?://([^/]+)", url)
        if not m:
            continue
        host = m.group(1).lower()
        status = (r.get("http_status") or "").strip()
        # only carry hosts that answered, or that were never actually fetched
        if status.isdigit() and int(status) >= 400:
            continue
        if status in ("0", "no_url_established", "NOT_ESTABLISHED",
                      "ROBOTS_DISALLOWED", "TERMS_RESTRICTED_DO_NOT_HARVEST",
                      "DOMAIN_HIJACKED_DO_NOT_LINK"):
            continue
        d = by_tribe[tid]
        key = (tid, host, ut)
        if key in seen:
            continue
        seen.add(key)
        restricted = is_restricted_tribe(tid, d["tribe_name"]) or is_restricted_host(host)
        rows.append({
            "tribe_id": tid,
            "cedar_uid": d["cedar_uid"],
            "tribe_name": d["tribe_name"],
            "host": host,
            "seed_url": url,
            "url_type": ut,
            "surface": "gaming" if ut in ("casino", "gaming_authority", "unverified_casino")
                       else "tribe",
            "n_facilities": len(d["facility_ids"]),
            "facility_ids": ";".join(x for x in d["facility_ids"] if x)[:900],
            "facility_names": ";".join(x for x in d["facility_names"] if x)[:900],
            "states": ";".join(sorted(d["states"])),
            "terms_restricted": "Y" if restricted else "N",
            "population_basis": POPULATION_BASIS,
        })

    rows.sort(key=lambda r: (r["tribe_name"].lower(), r["surface"], r["host"]))
    cols = list(rows[0].keys())
    tmp = TARGETS + ".part"
    with io.open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, TARGETS)

    tribes_with_target = len({r["tribe_id"] for r in rows if r["terms_restricted"] == "N"})
    log(f"targets: {len(rows)} rows | "
        f"{len({r['host'] for r in rows})} hosts | "
        f"{tribes_with_target} facility-bearing tribes reachable | "
        f"{len([r for r in rows if r['terms_restricted']=='Y'])} rows terms-restricted (excluded) | "
        f"{len(by_tribe)} facility-bearing tribes in gaming_facilities.csv")
    return rows


# ===========================================================================
# HIDDEN-DATA EXTRACTION from an HTML body
# ===========================================================================
JSONLD_RE = re.compile(
    r'<script[^>]+type\s*=\s*["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.S | re.I)
STATE_RE = re.compile(
    r'(__NEXT_DATA__|__NUXT__|__INITIAL_STATE__|__APOLLO_STATE__|window\.__data|'
    r'__PRELOADED_STATE__|drupalSettings|Drupal\.settings)', re.I)
COMMENT_RE = re.compile(r"<!--(.*?)-->", re.S)
DATA_ATTR_RE = re.compile(r'\sdata-([a-zA-Z0-9_-]{2,40})\s*=\s*["\']([^"\']{0,180})["\']')
META_RE = re.compile(
    r'<meta[^>]+(?:property|name)\s*=\s*["\']([^"\']+)["\'][^>]+content\s*=\s*["\']([^"\']*)["\']',
    re.I)
ARCGIS_RE = re.compile(
    r'https?://[^"\'\s<>]+/(?:rest/services|arcgis/rest)[^"\'\s<>]*?/(?:Feature|Map)Server[^"\'\s<>]*',
    re.I)
GSHEET_RE = re.compile(
    r'https?://docs\.google\.com/spreadsheets/d/(?:e/)?[A-Za-z0-9_-]{20,}[^"\'\s<>]*', re.I)
SELECT_RE = re.compile(r"<select[^>]*>(.*?)</select>", re.S | re.I)
OPTION_RE = re.compile(r"<option[^>]*>(.*?)</option>", re.S | re.I)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)
AJAX_RE = re.compile(r'["\'](/?[^"\'\s<>]*(?:admin-ajax\.php|/api/|/wp-json/[a-z0-9/_-]+|'
                     r'\.json\?|/graphql))["\']', re.I)


def strip_tags(s):
    s = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def extract_hidden(body_text):
    """Run the docs/HIDDEN_DATA_TECHNIQUES.md checklist over one HTML body."""
    out = {
        "jsonld_blocks": 0, "jsonld_types": [], "jsonld_org": None,
        "app_state_markers": [], "html_comment_blocks": 0, "html_comment_samples": [],
        "data_attr_keys": [], "meta_tags": {}, "arcgis_endpoints": [],
        "google_sheets": [], "select_vocabularies": [], "ajax_endpoints": [],
        "generator": None, "title": None,
    }
    m = TITLE_RE.search(body_text)
    if m:
        out["title"] = strip_tags(m.group(1))[:200]

    # 1. JSON-LD
    for blk in JSONLD_RE.findall(body_text):
        out["jsonld_blocks"] += 1
        try:
            data = json.loads(blk.strip())
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        for it in items:
            if not isinstance(it, dict):
                continue
            graph = it.get("@graph") if isinstance(it.get("@graph"), list) else [it]
            for g in graph:
                if not isinstance(g, dict):
                    continue
                t = g.get("@type")
                t = t if isinstance(t, str) else (t[0] if isinstance(t, list) and t else None)
                if t:
                    out["jsonld_types"].append(t)
                if out["jsonld_org"] is None and t and t.lower() in (
                        "organization", "localbusiness", "casino", "hotel", "resort",
                        "place", "lodgingbusiness", "entertainmentbusiness",
                        "touristattraction", "restaurant", "corporation"):
                    addr = g.get("address") if isinstance(g.get("address"), dict) else {}
                    geo = g.get("geo") if isinstance(g.get("geo"), dict) else {}
                    out["jsonld_org"] = {
                        "type": t,
                        "name": g.get("name"),
                        "legalName": g.get("legalName"),
                        "parentOrganization": (g.get("parentOrganization") or {}).get("name")
                            if isinstance(g.get("parentOrganization"), dict)
                            else g.get("parentOrganization"),
                        "streetAddress": addr.get("streetAddress"),
                        "addressLocality": addr.get("addressLocality"),
                        "addressRegion": addr.get("addressRegion"),
                        "postalCode": addr.get("postalCode"),
                        "telephone": g.get("telephone"),
                        "latitude": geo.get("latitude"),
                        "longitude": geo.get("longitude"),
                        "openingHours": g.get("openingHours") or g.get("openingHoursSpecification"),
                        "foundingDate": g.get("foundingDate"),
                        "url": g.get("url"),
                    }
    out["jsonld_types"] = sorted(set(x for x in out["jsonld_types"] if x))[:25]

    # 2. embedded application state
    out["app_state_markers"] = sorted(set(m.group(1) for m in STATE_RE.finditer(body_text)))[:10]

    # 7. HTML comments
    comments = [c.strip() for c in COMMENT_RE.findall(body_text)]
    real = [c for c in comments if len(c) > 40 and not c.lower().startswith(("[if", "<![", "/"))]
    out["html_comment_blocks"] = len(real)
    out["html_comment_samples"] = [re.sub(r"\s+", " ", c)[:220] for c in real[:6]]

    # 6. data-* attributes
    keys = {}
    for k, v in DATA_ATTR_RE.findall(body_text):
        keys.setdefault(k.lower(), v[:80])
    out["data_attr_keys"] = sorted(keys.keys())[:60]

    # 12. meta / OpenGraph
    for k, v in META_RE.findall(body_text):
        kl = k.lower()
        if kl in ("og:title", "og:url", "og:site_name", "og:description", "description",
                  "generator", "twitter:title", "geo.position", "geo.placename",
                  "article:published_time", "og:latitude", "og:longitude"):
            out["meta_tags"][kl] = strip_tags(v)[:300]
    out["generator"] = out["meta_tags"].get("generator")

    # 9. ArcGIS map services
    out["arcgis_endpoints"] = sorted(set(ARCGIS_RE.findall(body_text)))[:10]

    # 10. embedded Google Sheets
    out["google_sheets"] = sorted(set(GSHEET_RE.findall(body_text)))[:10]

    # 5. select option vocabularies
    for sel in SELECT_RE.findall(body_text)[:12]:
        opts = [strip_tags(o) for o in OPTION_RE.findall(sel)]
        opts = [o for o in opts if o and len(o) < 90]
        if len(opts) >= 4:
            out["select_vocabularies"].append(opts[:60])
    out["select_vocabularies"] = out["select_vocabularies"][:6]

    # 8. AJAX sources — RECORDED, and /wp-admin/ paths are never fetched
    aj = sorted(set(a for a in AJAX_RE.findall(body_text)))
    out["ajax_endpoints"] = [a for a in aj if len(a) < 200][:20]
    return out


def classify_page(host, body_text, hidden, facility_names):
    """Parked / hijacked detection. A domain name is never evidence."""
    low = (body_text or "")[:400000].lower()
    title = (hidden.get("title") or "").lower()
    for m in PARKED_MARKERS:
        if m in low:
            return "PARKED_DOMAIN", f"parking marker in body: {m!r}"
    for m in HIJACK_MARKERS:
        if m in low or m in title:
            return "DOMAIN_SUSPECT", f"off-topic/hijack marker present: {m!r}"
    # canonical / og:url must sit on the same apex
    ogu = hidden.get("meta_tags", {}).get("og:url") or ""
    if ogu:
        oh = urllib.parse.urlparse(ogu).netloc.lower()
        apex = ".".join(host.split(".")[-2:])
        if oh and apex and not oh.endswith(apex):
            return "DOMAIN_SUSPECT", f"og:url host {oh!r} is off-apex from {host!r}"
    # a distinctive facility-name token should appear in the title
    toks = set()
    for fn in facility_names:
        for t in re.findall(r"[A-Za-z]{5,}", fn or ""):
            tl = t.lower()
            if tl not in ("casino", "resort", "hotel", "tribal", "tribes", "nation",
                          "gaming", "indian", "community", "center", "travel", "lodge"):
                toks.add(tl)
    if toks and title and not any(t in title or t in host for t in toks):
        return "NAME_TOKEN_ABSENT", ("no distinctive facility-name token in <title> or host; "
                                     f"title={title[:80]!r}")
    return "OK", ""


# ===========================================================================
# STAGE 2 — per-host probe (homepage + hidden endpoints)
# ===========================================================================
def claim_lock(hosts, stage):
    rec = {"host": "gaming_web_harvest_980 (multi-host workstream)",
           "pid": os.getpid(), "script": "code/980_gaming_web_harvest.py",
           "stage": stage, "started": NOW,
           "n_hosts_claimed": len(hosts),
           "downloaded_this_run": False, "already_on_disk_skipped": 0,
           "refused_by_host": [], "accepted_then_failed_server_side": 0,
           "policy": (f"sequential; >={PER_HOST_DELAY}s per host, >={GLOBAL_DELAY}s global; "
                      "no retry loop; robots.txt honoured with our own UA; "
                      "TERMS_STATED_RESTRICTIVE hosts never requested"),
           "hosts_sample": sorted(hosts)[:25]}
    with io.open(HOSTLOCK, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=1)
    return rec


def release_lock(rec, **kw):
    rec.update(kw)
    rec["released"] = datetime.now(timezone.utc).isoformat()
    with io.open(HOSTLOCK, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=1)


def summarise_endpoint(kind, text):
    out = {"n_items": None, "pdf_urls": [], "post_types": [], "sitemap_locs": [],
           "page_links": [], "feed_items": [], "parse_note": None}
    try:
        if kind == "wp_media_pdf":
            data = json.loads(text)
            if isinstance(data, list):
                out["n_items"] = len(data)
                for it in data:
                    u = it.get("source_url") or ""
                    if u:
                        out["pdf_urls"].append({
                            "url": u,
                            "title": ((it.get("title") or {}).get("rendered") or "")[:180],
                            "date": it.get("date")})
        elif kind == "wp_types":
            data = json.loads(text)
            if isinstance(data, dict):
                out["post_types"] = sorted(data.keys())
                out["n_items"] = len(out["post_types"])
        elif kind == "wp_pages":
            data = json.loads(text)
            if isinstance(data, list):
                out["n_items"] = len(data)
                for it in data:
                    if isinstance(it, dict) and it.get("link"):
                        out["page_links"].append({
                            "url": it["link"],
                            "title": ((it.get("title") or {}).get("rendered") or "")[:180],
                            "modified": it.get("modified")})
        elif kind.startswith("sitemap"):
            locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", text)
            out["sitemap_locs"] = locs[:600]
            out["n_items"] = len(locs)
        elif kind == "feed":
            items = re.findall(r"<item>(.*?)</item>", text, re.S)
            out["n_items"] = len(items)
            for it in items[:10]:
                t = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", it, re.S)
                d = re.search(r"<pubDate>(.*?)</pubDate>", it, re.S)
                out["feed_items"].append({
                    "title": strip_tags(t.group(1))[:180] if t else None,
                    "pubDate": d.group(1).strip() if d else None})
    except Exception as e:
        out["parse_note"] = f"{type(e).__name__}: {str(e)[:160]}"
    return out


def stage_probe(limit=None, deadline_min=110, only_surface=None):
    rows = list(csv.DictReader(io.open(TARGETS, encoding="utf-8-sig")))
    if only_surface:
        rows = [r for r in rows if r["surface"] == only_surface]
    hosts = {}
    for r in rows:
        hosts.setdefault(r["host"], r)
    done_all = load_done(PROBE, lambda r: (r["host"], r["endpoint_kind"]))
    deadline = time.time() + deadline_min * 60
    lock = claim_lock(set(hosts), "probe")

    items = sorted(hosts.items(), key=lambda kv: kv[0])
    if limit:
        items = items[:limit]
    # each worker owns a DISJOINT set of hosts -> no host is ever hit concurrently
    buckets = [items[i::WORKERS] for i in range(WORKERS)]
    counters = {"hosts": 0, "req": 0, "hidden": 0}
    refused = []
    cl = threading.Lock()

    def worker(bucket):
        for host, r in bucket:
            if time.time() > deadline:
                log("RUN_DEADLINE reached; stopping cleanly.")
                return
            try:
                nh, nr, refs = probe_one_host(host, r, done_all)
            except Exception as e:
                log(f"  worker error on {host}: {type(e).__name__}: {e}")
                continue
            with cl:
                counters["hosts"] += nh
                counters["req"] += nr
                refused.extend(refs)
                if nh:
                    log(f"[{counters['hosts']:>4}/{len(items)}] {host:44} "
                        f"total_req={counters['req']}")

    threads = [threading.Thread(target=worker, args=(b,), daemon=True) for b in buckets]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    release_lock(lock, downloaded_this_run=(counters["req"] > 0),
                 refused_by_host=sorted(set(refused)),
                 n_hosts_done=counters["hosts"], n_requests=counters["req"], active=False)
    log(f"probe done: hosts={counters['hosts']} requests={counters['req']}")


def probe_one_host(host, r, done):
    """One nation's one host, start to finish, flushed per endpoint."""
    n_hosts = n_req = n_hidden = 0
    refused = []
    if True:
        if r["terms_restricted"] == "Y" or is_restricted_host(host):
            if (host, "ALL") not in done:
                appendl(PROBE, {
                    "tribe_id": r["tribe_id"], "cedar_uid": r["cedar_uid"],
                    "tribe_name": r["tribe_name"], "host": host, "surface": r["surface"],
                    "endpoint_kind": "ALL", "url": "",
                    "http_status": "EXCLUDED_TERMS_STATED_RESTRICTIVE",
                    "note": ("source_terms_status = TERMS_STATED_RESTRICTIVE; excluded by "
                             "EVERY route including Wayback and the WP media API. "
                             "review/tribal_vendor_list_registry_2026-08-26.csv"),
                    "checked_date": TODAY})
                done.add((host, "ALL"))
            return 0, 0, []
        if (host, "ALL") in done and (host, "home") in done:
            return 0, 0, []
        n_hosts += 1
        base = f"https://{host}"

        # ---- homepage (techniques 1,2,5,6,7,8,9,10,12) ----
        if (host, "home") not in done:
            url = r["seed_url"] if r["seed_url"].startswith("http") else base + "/"
            ok, rnote = robots_ok(url)
            rec = {"tribe_id": r["tribe_id"], "cedar_uid": r["cedar_uid"],
                   "tribe_name": r["tribe_name"], "host": host, "surface": r["surface"],
                   "url_type": r["url_type"], "facility_ids": r["facility_ids"],
                   "facility_names": r["facility_names"],
                   "endpoint_kind": "home", "url": url, "checked_date": TODAY,
                   "robots_note": rnote,
                   "technique": "docs/HIDDEN_DATA_TECHNIQUES.md #1,2,5,6,7,8,9,10,12"}
            if not ok:
                rec["http_status"] = "ROBOTS_DISALLOW"
                rec["note"] = "robots.txt Disallow matches this path for our UA; not fetched"
                appendl(PROBE, rec)
                done.add((host, "home"))
                refused.append(host)
            else:
                res = fetch(url)
                n_req += 1
                rec.update({"http_status": res["http_status"],
                            "content_type": res["content_type"], "bytes": res["bytes"],
                            "final_url": res["final_url"], "note": res["note"],
                            "resp_headers": res.get("headers", {})})
                if res["http_status"] == "200" and res["bytes"] > 200:
                    fn, md5 = save_raw(res["final_url"] or url, res["content"], ".html")
                    rec["raw_file"], rec["md5"] = fn, md5
                    hid = extract_hidden(res["text"])
                    verdict, why = classify_page(
                        host, res["text"], hid,
                        (r["facility_names"] or "").split(";"))
                    rec["page_verdict"], rec["page_verdict_basis"] = verdict, why
                    rec["hidden"] = hid
                    rec["text_chars_extracted"] = len(strip_tags(res["text"]))
                    if hid["jsonld_blocks"] or hid["app_state_markers"] or \
                       hid["arcgis_endpoints"] or hid["google_sheets"]:
                        n_hidden += 1
                elif res["http_status"] in ("403", "406", "429"):
                    refused.append(host)
                appendl(PROBE, rec)
                done.add((host, "home"))

        # ---- machine-readable endpoints (techniques 3,4,13) ----
        wp_alive = None
        for kind, path, tech in HIDDEN_ENDPOINTS:
            if (host, kind) in done:
                if kind == "wp_types":
                    wp_alive = None
                continue
            if kind.startswith("wp_") and wp_alive is False:
                appendl(PROBE, {"tribe_id": r["tribe_id"], "cedar_uid": r["cedar_uid"],
                                "tribe_name": r["tribe_name"], "host": host,
                                "surface": r["surface"], "endpoint_kind": kind,
                                "url": base + path, "http_status": "SKIPPED_NOT_WORDPRESS",
                                "note": "/wp-json/wp/v2/types did not answer JSON on this host",
                                "checked_date": TODAY, "technique": tech})
                done.add((host, kind))
                continue
            if kind == "sitemap" and (host, "sitemap_index") in done:
                pass  # still try plain sitemap.xml; index may 404
            url = base + path
            ok, rnote = robots_ok(url)
            rec = {"tribe_id": r["tribe_id"], "cedar_uid": r["cedar_uid"],
                   "tribe_name": r["tribe_name"], "host": host, "surface": r["surface"],
                   "endpoint_kind": kind, "url": url, "checked_date": TODAY,
                   "robots_note": rnote,
                   "technique": "docs/HIDDEN_DATA_TECHNIQUES.md #" + tech}
            if not ok:
                rec["http_status"] = "ROBOTS_DISALLOW"
                rec["note"] = "robots.txt Disallow matches this path for our UA; not fetched"
                appendl(PROBE, rec)
                done.add((host, kind))
                continue
            res = fetch(url, accept="application/json,application/xml,text/xml,*/*")
            n_req += 1
            rec.update({"http_status": res["http_status"], "content_type": res["content_type"],
                        "bytes": res["bytes"], "final_url": res["final_url"],
                        "note": res["note"]})
            for h, v in (res.get("headers") or {}).items():
                if h.lower().startswith("x-wp-"):
                    rec[h.lower()] = v
            if kind == "wp_types":
                wp_alive = (res["http_status"] == "200" and "json" in (res["content_type"] or ""))
            if res["http_status"] == "200" and res["bytes"] > 40:
                ext = (".json" if "json" in (res["content_type"] or "")
                       else ".xml" if "xml" in (res["content_type"] or "") else ".txt")
                fn, md5 = save_raw(res["final_url"] or url, res["content"], ext)
                rec["raw_file"], rec["md5"] = fn, md5
                rec.update(summarise_endpoint(kind, res["text"]))
                if (rec.get("n_items") or 0) > 0:
                    n_hidden += 1
            appendl(PROBE, rec)
            done.add((host, kind))

        appendl(PROBE, {"host": host, "endpoint_kind": "ALL", "http_status": "HOST_COMPLETE",
                        "tribe_id": r["tribe_id"], "cedar_uid": r["cedar_uid"],
                        "tribe_name": r["tribe_name"], "surface": r["surface"],
                        "checked_date": TODAY, "note": "all endpoints attempted"})
        done.add((host, "ALL"))
    return n_hosts, n_req, refused


# ===========================================================================
# STAGE 3 — targeted page fetch (capacity + vendor/TERO surfaces)
# ===========================================================================
CAP_PATTERNS = [
    ("gaming_machines", re.compile(
        r"\b(?:over|nearly|more than|almost|approximately|about)?\s*([\d][\d,\.]{1,7})\s*\+?\s*"
        r"(?:of the (?:hottest|newest|latest)\s+)?"
        r"(?:slot machines|slots|electronic gaming machines|gaming machines|"
        r"video gaming machines|gaming devices|reel and video slots|class ii machines|"
        r"class iii machines|electronic games|gaming positions)\b", re.I)),
    ("table_games", re.compile(
        r"\b(?:over|nearly|more than|almost|approximately|about)?\s*([\d][\d,]{0,5})\s*\+?\s*"
        r"(?:table games|gaming tables|live table games|blackjack tables)\b", re.I)),
    ("poker_tables", re.compile(
        r"\b(?:over|nearly|more than|almost|approximately|about)?\s*([\d][\d,]{0,4})\s*\+?\s*"
        r"(?:poker tables|table poker room)\b", re.I)),
    ("bingo_seats", re.compile(
        r"\b(?:over|nearly|more than|almost|approximately|about)?\s*([\d][\d,]{0,5})\s*\+?\s*"
        r"(?:bingo seats|seat bingo|bingo hall seats)\b", re.I)),
    ("hotel_rooms", re.compile(
        r"\b(?:over|nearly|more than|almost|approximately|about)?\s*([\d][\d,]{0,5})\s*\+?\s*"
        r"(?:hotel rooms|guest rooms|guestrooms|rooms and suites|luxurious rooms|"
        r"well-appointed rooms|rooms & suites)\b", re.I)),
    ("gaming_square_feet", re.compile(
        r"\b([\d][\d,]{2,9})\s*(?:\+)?\s*(?:square feet|square-feet|sq\.?\s?ft\.?|sf)\s*"
        r"(?:of\s+)?(?:gaming|casino|gambling)", re.I)),
    ("convention_square_feet", re.compile(
        r"\b([\d][\d,]{2,9})\s*(?:\+)?\s*(?:square feet|square-feet|sq\.?\s?ft\.?|sf)\s*"
        r"(?:of\s+)?(?:meeting|event|convention|conference|banquet|flexible)", re.I)),
    ("restaurants", re.compile(
        r"\b([\d][\d,]{0,3})\s*\+?\s*(?:restaurants|dining (?:options|venues|outlets)|"
        r"food and beverage outlets)\b", re.I)),
    ("employees", re.compile(
        r"\b(?:over|nearly|more than|approximately|about|employs)?\s*([\d][\d,]{1,7})\s*\+?\s*"
        r"(?:employees|team members|associates|staff members)\b", re.I)),
    ("parking_spaces", re.compile(
        r"\b([\d][\d,]{2,7})\s*\+?\s*(?:parking spaces|parking spots|covered parking spaces)\b",
        re.I)),
]
BOUNDING_WORDS = re.compile(r"\b(over|nearly|more than|almost|approximately|about|up to)\b", re.I)
HOURS_RE = re.compile(
    r"(open\s+24\s*(?:hours|/7|hours a day)[^.]{0,60}|"
    r"open\s+(?:daily|every day)\s+[\d]{1,2}(?::\d{2})?\s*(?:am|pm)[^.]{0,60}|"
    r"hours[:\s]{1,3}(?:mon|sun|daily)[^.]{0,80})", re.I)


# Ranked, not merely matched. The first pass ordered candidates by URL depth and
# spent requests on /author-sitemap.xml and /careers/ while /casino/ waited.
CAP_SCORE = [
    (("fact-sheet", "factsheet", "fact_sheet", "press-kit", "media-kit"), 100),
    (("/casino", "casino/", "gaming", "slots", "table-games", "poker", "bingo"), 80),
    (("/about", "about-us", "our-story", "who-we-are"), 70),
    (("hotel", "rooms", "suites", "accommodation", "stay/", "lodging"), 65),
    (("meeting", "convention", "conference", "event-space", "banquet", "ballroom"), 60),
    (("resort", "property", "amenities", "entertainment"), 40),
]
VEND_SCORE = [
    (("tero", "tribal-employment-rights"), 100),
    (("vendor", "supplier"), 90),
    (("procure", "purchasing", "solicitation"), 85),
    (("doing-business", "do-business", "dobusiness"), 80),
    (("rfp", "rfq", "/bid", "bids"), 70),
    (("business-license", "business-licence", "contracting"), 60),
]
NEGATIVE_TOKENS = ("sitemap", "/feed", "/tag/", "/category/", "/author/", "/wp-content/",
                   ".xml", ".jpg", ".png", ".gif", ".css", ".js", "/page/", "?replytocom")


def _score(url, table):
    ul = url.lower()
    best = 0
    for toks, s in table:
        if any(t in ul for t in toks):
            best = max(best, s)
    if best:
        best -= min(20, 4 * max(0, ul.rstrip("/").count("/") - 3))
    return best


def pick_pages(host, probe_rows, max_per_host=6):
    """Choose a small, bounded, RANKED set of on-site pages worth a request."""
    urls = {}
    for rec in probe_rows:
        for loc in (rec.get("sitemap_locs") or []):
            urls.setdefault(loc, "sitemap")
        for p in (rec.get("page_links") or []):
            urls.setdefault(p["url"], "wp_pages")
    cap, vend = [], []
    for u, src in urls.items():
        if urllib.parse.urlparse(u).netloc.lower() != host:
            continue
        if forbidden_path(u):
            continue
        ul = u.lower()
        if any(t in ul for t in NEGATIVE_TOKENS):
            continue
        vs = _score(u, VEND_SCORE)
        if vs:
            vend.append((-vs, u, src, "vendor_procurement_tero"))
            continue
        cs = _score(u, CAP_SCORE)
        if cs:
            cap.append((-cs, u, src, "capacity_identity"))
    vend.sort()
    cap.sort()
    n_vend = min(len(vend), max(2, max_per_host // 2))
    out = [t[1:] for t in vend[:n_vend]]
    out += [t[1:] for t in cap[:max_per_host - len(out)]]
    return out


def child_sitemaps(host, probe_rows, limit=3):
    """A sitemap INDEX lists child sitemaps, not pages. Follow a bounded few."""
    kids = []
    for rec in probe_rows:
        for loc in (rec.get("sitemap_locs") or []):
            if not loc.lower().endswith(".xml"):
                continue
            if urllib.parse.urlparse(loc).netloc.lower() != host:
                continue
            ll = loc.lower()
            if any(t in ll for t in ("author", "category", "tag", "-tax", "taxonom",
                                     "image", "attachment", "product")):
                continue
            score = 2 if any(t in ll for t in ("page", "post-sitemap", "posts")) else 1
            kids.append((-score, loc))
    kids.sort()
    seen, out = set(), []
    for _, u in kids:
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
        if len(out) >= limit:
            break
    return out


def stage_pages(limit=None, deadline_min=110):
    by_host = {}
    for line in io.open(PROBE, encoding="utf-8"):
        try:
            rec = json.loads(line)
        except Exception:
            continue
        by_host.setdefault(rec.get("host"), []).append(rec)
    targets = {r["host"]: r for r in csv.DictReader(io.open(TARGETS, encoding="utf-8-sig"))}
    done = load_done(PAGES, lambda r: r["url"])
    deadline = time.time() + deadline_min * 60
    lock = claim_lock(set(by_host), "pages")

    work = []
    for host, recs in sorted(by_host.items()):
        if not host or host not in targets:
            continue
        t = targets[host]
        if t["terms_restricted"] == "Y" or is_restricted_host(host):
            continue
        work.append((host, t, recs))
    if limit:
        work = work[:limit]
    buckets = [work[i::WORKERS] for i in range(WORKERS)]
    counters = {"hosts": 0, "req": 0}
    cl = threading.Lock()

    def worker(bucket):
        for host, t, recs in bucket:
            if time.time() > deadline:
                log("RUN_DEADLINE reached; stopping cleanly.")
                return
            try:
                nr = pages_one_host(host, t, recs, done)
            except Exception as e:
                log(f"  worker error on {host}: {type(e).__name__}: {e}")
                continue
            with cl:
                counters["hosts"] += 1
                counters["req"] += nr
                log(f"[{counters['hosts']:>4}/{len(work)}] pages {host:40} "
                    f"total_req={counters['req']}")

    threads = [threading.Thread(target=worker, args=(b,), daemon=True) for b in buckets]
    for t_ in threads:
        t_.start()
    for t_ in threads:
        t_.join()
    release_lock(lock, downloaded_this_run=(counters["req"] > 0),
                 n_hosts_done=counters["hosts"], n_requests=counters["req"], active=False)
    log(f"pages done: hosts={counters['hosts']} requests={counters['req']}")


def pages_one_host(host, t, recs, done):
    n_req = 0
    # A sitemap INDEX lists child sitemaps, not pages. Expand a bounded few
    # first, so the ranked page picker has real URLs to choose from.
    if len([1 for r in recs for _ in (r.get("page_links") or [])]) < 5:
        for cs in child_sitemaps(host, recs):
            if ("CS:" + cs) in done:
                continue
            ok, _rn = robots_ok(cs)
            if not ok:
                done.add("CS:" + cs)
                continue
            res = fetch(cs, accept="application/xml,text/xml,*/*")
            n_req += 1
            rec = {"tribe_id": t["tribe_id"], "cedar_uid": t["cedar_uid"],
                   "tribe_name": t["tribe_name"], "host": host, "surface": t["surface"],
                   "url": "CS:" + cs, "discovered_via": "sitemap_index",
                   "page_class": "child_sitemap", "checked_date": TODAY,
                   "http_status": res["http_status"], "bytes": res["bytes"],
                   "technique": "docs/HIDDEN_DATA_TECHNIQUES.md #4 (sitemap index -> child)"}
            if res["http_status"] == "200" and res["bytes"] > 40:
                locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", res["text"])
                rec["sitemap_locs"] = locs[:600]
                rec["n_items"] = len(locs)
                recs = recs + [{"sitemap_locs": locs[:600]}]
            appendl(PAGES, rec)
            done.add("CS:" + cs)
    picks = pick_pages(host, recs)
    if True:
        for url, src, page_class in picks:
            if url in done or forbidden_path(url):
                continue
            ok, rnote = robots_ok(url)
            rec = {"tribe_id": t["tribe_id"], "cedar_uid": t["cedar_uid"],
                   "tribe_name": t["tribe_name"], "host": host, "surface": t["surface"],
                   "facility_ids": t["facility_ids"], "facility_names": t["facility_names"],
                   "url": url, "discovered_via": src, "page_class": page_class,
                   "checked_date": TODAY, "robots_note": rnote}
            if not ok:
                rec["http_status"] = "ROBOTS_DISALLOW"
                appendl(PAGES, rec)
                done.add(url)
                continue
            res = fetch(url)
            n_req += 1
            rec.update({"http_status": res["http_status"], "content_type": res["content_type"],
                        "bytes": res["bytes"], "final_url": res["final_url"],
                        "note": res["note"]})
            if res["http_status"] == "200" and res["bytes"] > 200:
                fn, md5 = save_raw(res["final_url"] or url, res["content"], ".html")
                rec["raw_file"], rec["md5"] = fn, md5
                hid = extract_hidden(res["text"])
                rec["hidden"] = hid
                text = strip_tags(res["text"])
                rec["text_chars_extracted"] = len(text)
                if not text:
                    rec["text_not_extractable"] = True
                rec["capacity_hits"] = harvest_capacity(text)
                hh = HOURS_RE.search(text)
                if hh:
                    rec["hours_quote"] = hh.group(1)[:200]
            appendl(PAGES, rec)
            done.add(url)
    return n_req


def harvest_capacity(text):
    hits = []
    for metric, rx in CAP_PATTERNS:
        for m in rx.finditer(text):
            raw = m.group(1)
            try:
                val = int(raw.replace(",", "").split(".")[0])
            except Exception:
                continue
            if val <= 0 or val > 5_000_000:
                continue
            s = max(0, m.start() - 110)
            quote = text[s:m.end() + 110].strip()
            bounded = bool(BOUNDING_WORDS.search(text[max(0, m.start() - 30):m.end()]))
            hits.append({"metric": metric, "value": val, "value_verbatim": m.group(0).strip()[:120],
                         "quote": quote[:400], "value_is_bounded": bounded,
                         "bound_direction": "at_least" if bounded else ""})
    # de-duplicate on (metric, value)
    seen, out = set(), []
    for h in hits:
        k = (h["metric"], h["value"])
        if k in seen:
            continue
        seen.add(k)
        out.append(h)
    return out[:40]


# ===========================================================================
# STAGE 4 — build the two output tables
# ===========================================================================
OBS_COLS = [
    "observation_id", "observation_kind", "assertion_class", "assertion_class_note",
    "not_summable_with", "metric", "value", "value_verbatim", "unit",
    "value_is_bounded", "bound_direction", "text_value",
    "tribe_id", "cedar_uid", "tribe_name", "facility_ids", "facility_names",
    "n_facilities_for_tribe", "facility_attribution_status", "state",
    "site_host", "source_url", "source_quote", "page_class", "discovered_via",
    "technique", "retrieved_at", "as_of_date", "as_of_date_precision", "as_of_date_basis",
    "source_file", "source_md5", "http_status", "page_verdict", "page_verdict_basis",
    "population_basis", "inclusion_basis", "confidence", "built_by", "built_date",
]
COV_COLS = [
    "tribe_id", "cedar_uid", "tribe_name", "n_facilities", "facility_ids", "states",
    "site_host", "surface", "url_type", "seed_url", "harvest_status",
    "home_http_status", "page_verdict", "robots_note",
    "wp_rest_available", "wp_custom_post_types", "n_wp_pdf_documents",
    "n_sitemap_urls", "n_wp_pages", "n_feed_items",
    "jsonld_present", "jsonld_types", "app_state_markers", "arcgis_endpoints",
    "google_sheets", "n_html_comment_blocks", "n_data_attr_keys",
    "ajax_endpoints_observed_not_fetched",
    "n_pages_fetched", "n_capacity_observations", "n_identity_observations",
    "vendor_tero_urls_found", "checked_and_absent", "terms_restricted",
    "population_basis", "checked_date", "built_by",
]


def _oid(*parts):
    return "GWH-" + hashlib.md5("||".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:16]


def stage_build():
    targets = list(csv.DictReader(io.open(TARGETS, encoding="utf-8-sig")))
    tmap = {}
    for t in targets:
        tmap.setdefault(t["host"], t)

    probe_by_host = {}
    for line in io.open(PROBE, encoding="utf-8"):
        try:
            rec = json.loads(line)
        except Exception:
            continue
        probe_by_host.setdefault(rec.get("host"), []).append(rec)

    pages_by_host = {}
    if os.path.exists(PAGES):
        for line in io.open(PAGES, encoding="utf-8"):
            try:
                rec = json.loads(line)
            except Exception:
                continue
            pages_by_host.setdefault(rec.get("host"), []).append(rec)

    obs, cov = [], []
    for host, t in sorted(tmap.items()):
        precs = probe_by_host.get(host, [])
        pgs = pages_by_host.get(host, [])
        home = next((r for r in precs if r.get("endpoint_kind") == "home"), None)
        excl = next((r for r in precs
                     if r.get("http_status") == "EXCLUDED_TERMS_STATED_RESTRICTIVE"), None)

        def ep(kind):
            return next((r for r in precs if r.get("endpoint_kind") == kind), None)

        wp_types = ep("wp_types") or {}
        wp_pdf = ep("wp_media_pdf") or {}
        wp_pages = ep("wp_pages") or {}
        smi = ep("sitemap_index") or {}
        sm = ep("sitemap") or {}
        feed = ep("feed") or {}

        hid = (home or {}).get("hidden") or {}
        n_sitemap = max((smi.get("n_items") or 0), (sm.get("n_items") or 0))

        vendor_urls = []
        for rec in precs:
            for loc in (rec.get("sitemap_locs") or []):
                if any(x in loc.lower() for x in VENDOR_URL_TOKENS):
                    vendor_urls.append(loc)
            for p in (rec.get("page_links") or []):
                if any(x in (p.get("url") or "").lower() for x in VENDOR_URL_TOKENS):
                    vendor_urls.append(p["url"])
        for d in (wp_pdf.get("pdf_urls") or []):
            blob = ((d.get("title") or "") + " " + (d.get("url") or "")).lower()
            if any(x in blob for x in VENDOR_URL_TOKENS):
                vendor_urls.append(d["url"])
        vendor_urls = sorted(set(vendor_urls))[:40]

        n_cap = n_ident = 0
        state = (t.get("states") or "").split(";")[0]
        fac_ids = t.get("facility_ids") or ""
        n_fac = int(t.get("n_facilities") or 0)
        attr_status = ("SINGLE_FACILITY_TRIBE" if n_fac == 1
                       else "TRIBE_LEVEL_MULTI_FACILITY_NOT_DISAMBIGUATED")

        # ---- identity from JSON-LD (technique 1) ----
        org = hid.get("jsonld_org")
        if org and (home or {}).get("page_verdict") in ("OK", "NAME_TOKEN_ABSENT"):
            for field, val in (("legal_or_published_name", org.get("name")),
                               ("legal_name", org.get("legalName")),
                               ("street_address", org.get("streetAddress")),
                               ("city", org.get("addressLocality")),
                               ("state", org.get("addressRegion")),
                               ("postal_code", org.get("postalCode")),
                               ("telephone", org.get("telephone")),
                               ("latitude", org.get("latitude")),
                               ("longitude", org.get("longitude")),
                               ("parent_organization", org.get("parentOrganization")),
                               ("founding_date", org.get("foundingDate")),
                               ("property_type_schema_org", org.get("type"))):
                if val in (None, "", [], {}):
                    continue
                if isinstance(val, (dict, list)):
                    val = json.dumps(val, ensure_ascii=False)[:400]
                obs.append({
                    "observation_id": _oid(host, "jsonld", field),
                    "observation_kind": "FACILITY_IDENTITY",
                    "assertion_class": ASSERTION_CLASS,
                    "assertion_class_note": ("operator's own structured markup; not a "
                                             "regulator determination"),
                    "not_summable_with": "", "metric": field, "value": "",
                    "value_verbatim": "", "unit": "",
                    "value_is_bounded": "", "bound_direction": "",
                    "text_value": str(val)[:400],
                    "tribe_id": t["tribe_id"], "cedar_uid": t["cedar_uid"],
                    "tribe_name": t["tribe_name"], "facility_ids": fac_ids,
                    "facility_names": t["facility_names"],
                    "n_facilities_for_tribe": n_fac,
                    "facility_attribution_status": attr_status, "state": state,
                    "site_host": host, "source_url": home.get("final_url") or home.get("url"),
                    "source_quote": json.dumps({k: v for k, v in org.items()
                                                if v not in (None, "", [], {})},
                                               ensure_ascii=False)[:900],
                    "page_class": "homepage", "discovered_via": "json_ld",
                    "technique": "docs/HIDDEN_DATA_TECHNIQUES.md #1 (JSON-LD / schema.org)",
                    "retrieved_at": NOW, "as_of_date": home.get("checked_date"),
                    "as_of_date_precision": "day",
                    "as_of_date_basis": "date the page was retrieved; page states no as-of date",
                    "source_file": home.get("raw_file") or "", "source_md5": home.get("md5") or "",
                    "http_status": home.get("http_status") or "",
                    "page_verdict": home.get("page_verdict") or "",
                    "page_verdict_basis": home.get("page_verdict_basis") or "",
                    "population_basis": POPULATION_BASIS,
                    "inclusion_basis": ("cedar_observation: harvested from the operator's own "
                                        "published page by code/980_gaming_web_harvest.py"),
                    "confidence": "medium", "built_by": "code/980_gaming_web_harvest.py",
                    "built_date": TODAY})
                n_ident += 1

        # ---- capacity from fetched pages ----
        for pg in pgs:
            if pg.get("http_status") != "200":
                continue
            for h in (pg.get("capacity_hits") or []):
                unit = ("square_feet" if h["metric"].endswith("square_feet")
                        else "count")
                # "450+ Slots" is a LOWER BOUND and the word-based detector misses
                # it. A bound recorded as an exact value is the same defect as a
                # self-published figure recorded as a regulator's.
                if not h["value_is_bounded"] and "+" in (h.get("value_verbatim") or ""):
                    h["value_is_bounded"] = True
                    h["bound_direction"] = "at_least"
                    h["bound_basis"] = "trailing '+' in the operator's own wording"
                obs.append({
                    "observation_id": _oid(host, pg["url"], h["metric"], h["value"]),
                    "observation_kind": "CAPACITY_SIGNAL",
                    "assertion_class": ASSERTION_CLASS,
                    "assertion_class_note": (
                        "SELF-PUBLISHED BY THE OPERATOR. Never a regulator's figure; "
                        "must not be summed against NIGC or state-regulator numbers."),
                    "not_summable_with": NOT_SUMMABLE,
                    "metric": h["metric"], "value": h["value"],
                    "value_verbatim": h["value_verbatim"], "unit": unit,
                    "value_is_bounded": "Y" if h["value_is_bounded"] else "N",
                    "bound_direction": h["bound_direction"], "text_value": "",
                    "tribe_id": pg["tribe_id"], "cedar_uid": pg["cedar_uid"],
                    "tribe_name": pg["tribe_name"], "facility_ids": fac_ids,
                    "facility_names": pg.get("facility_names") or "",
                    "n_facilities_for_tribe": n_fac,
                    "facility_attribution_status": attr_status, "state": state,
                    "site_host": host, "source_url": pg.get("final_url") or pg["url"],
                    "source_quote": h["quote"],
                    "page_class": pg.get("page_class") or "",
                    "discovered_via": pg.get("discovered_via") or "",
                    "technique": ("docs/HIDDEN_DATA_TECHNIQUES.md #4 (sitemap) / #3 (WP REST "
                                  "pages) -> page text"),
                    "retrieved_at": NOW, "as_of_date": pg.get("checked_date"),
                    "as_of_date_precision": "day",
                    "as_of_date_basis": "date the page was retrieved; page states no as-of date",
                    "source_file": pg.get("raw_file") or "", "source_md5": pg.get("md5") or "",
                    "http_status": pg.get("http_status") or "",
                    "page_verdict": "", "page_verdict_basis": "",
                    "population_basis": POPULATION_BASIS,
                    "inclusion_basis": ("cedar_observation: regex-extracted from the operator's "
                                        "own page text, verbatim quote retained"),
                    "confidence": "low_needs_review",
                    "built_by": "code/980_gaming_web_harvest.py", "built_date": TODAY})
                n_cap += 1
            if pg.get("hours_quote"):
                obs.append({
                    "observation_id": _oid(host, pg["url"], "operating_hours"),
                    "observation_kind": "FACILITY_IDENTITY",
                    "assertion_class": ASSERTION_CLASS,
                    "assertion_class_note": "operator's own published hours",
                    "not_summable_with": "", "metric": "operating_hours", "value": "",
                    "value_verbatim": "", "unit": "", "value_is_bounded": "",
                    "bound_direction": "", "text_value": pg["hours_quote"],
                    "tribe_id": pg["tribe_id"], "cedar_uid": pg["cedar_uid"],
                    "tribe_name": pg["tribe_name"], "facility_ids": fac_ids,
                    "facility_names": pg.get("facility_names") or "",
                    "n_facilities_for_tribe": n_fac,
                    "facility_attribution_status": attr_status, "state": state,
                    "site_host": host, "source_url": pg.get("final_url") or pg["url"],
                    "source_quote": pg["hours_quote"], "page_class": pg.get("page_class") or "",
                    "discovered_via": pg.get("discovered_via") or "",
                    "technique": "page text", "retrieved_at": NOW,
                    "as_of_date": pg.get("checked_date"), "as_of_date_precision": "day",
                    "as_of_date_basis": "date the page was retrieved",
                    "source_file": pg.get("raw_file") or "", "source_md5": pg.get("md5") or "",
                    "http_status": pg.get("http_status") or "", "page_verdict": "",
                    "page_verdict_basis": "", "population_basis": POPULATION_BASIS,
                    "inclusion_basis": "cedar_observation: operator's published hours",
                    "confidence": "medium", "built_by": "code/980_gaming_web_harvest.py",
                    "built_date": TODAY})
                n_ident += 1

        # ---- coverage row: found / harvested / checked-and-absent ----
        absent = []
        if excl:
            status = "EXCLUDED_TERMS_STATED_RESTRICTIVE"
        elif home is None:
            status = "UNTOUCHED"
        elif home.get("http_status") == "ROBOTS_DISALLOW":
            status = "REFUSED_ROBOTS_DISALLOW"
        elif home.get("http_status") != "200":
            status = f"UNREACHABLE_{home.get('http_status')}"
        elif home.get("page_verdict") in ("PARKED_DOMAIN", "DOMAIN_SUSPECT"):
            status = "REACHED_BUT_" + home["page_verdict"]
        elif n_cap or n_ident:
            status = "HARVESTED"
        else:
            status = "TOUCHED_NOTHING_FOUND"

        if home and home.get("http_status") == "200":
            if not hid.get("jsonld_blocks"):
                absent.append("json_ld")
            if not hid.get("app_state_markers"):
                absent.append("embedded_app_state")
            if not hid.get("arcgis_endpoints"):
                absent.append("arcgis_feature_service")
            if not hid.get("google_sheets"):
                absent.append("embedded_google_sheet")
            if not (hid.get("html_comment_blocks") or 0):
                absent.append("substantive_html_comments")
        if wp_types.get("http_status") and wp_types.get("http_status") != "200":
            absent.append("wordpress_rest_api")
        if (wp_pdf.get("n_items") or 0) == 0 and wp_pdf.get("http_status") == "200":
            absent.append("wp_media_pdfs")
        if n_sitemap == 0 and (smi.get("http_status") or sm.get("http_status")):
            absent.append("sitemap")
        if (feed.get("n_items") or 0) == 0 and feed.get("http_status") == "200":
            absent.append("rss_feed")
        if not vendor_urls:
            absent.append("vendor_procurement_tero_pages")

        cov.append({
            "tribe_id": t["tribe_id"], "cedar_uid": t["cedar_uid"],
            "tribe_name": t["tribe_name"], "n_facilities": n_fac,
            "facility_ids": fac_ids, "states": t.get("states") or "",
            "site_host": host, "surface": t["surface"], "url_type": t["url_type"],
            "seed_url": t["seed_url"], "harvest_status": status,
            "home_http_status": (home or {}).get("http_status") or "",
            "page_verdict": (home or {}).get("page_verdict") or "",
            "robots_note": (home or {}).get("robots_note") or "",
            "wp_rest_available": "Y" if wp_types.get("http_status") == "200" else "N",
            "wp_custom_post_types": ";".join(
                [p for p in (wp_types.get("post_types") or [])
                 if p not in ("post", "page", "attachment", "nav_menu_item",
                              "wp_block", "wp_template", "wp_template_part",
                              "wp_navigation", "wp_global_styles")])[:400],
            "n_wp_pdf_documents": len(wp_pdf.get("pdf_urls") or []),
            "n_sitemap_urls": n_sitemap,
            "n_wp_pages": wp_pages.get("n_items") or 0,
            "n_feed_items": feed.get("n_items") or 0,
            "jsonld_present": "Y" if hid.get("jsonld_blocks") else "N",
            "jsonld_types": ";".join(hid.get("jsonld_types") or [])[:300],
            "app_state_markers": ";".join(hid.get("app_state_markers") or []),
            "arcgis_endpoints": ";".join(hid.get("arcgis_endpoints") or [])[:600],
            "google_sheets": ";".join(hid.get("google_sheets") or [])[:600],
            "n_html_comment_blocks": hid.get("html_comment_blocks") or 0,
            "n_data_attr_keys": len(hid.get("data_attr_keys") or []),
            "ajax_endpoints_observed_not_fetched": ";".join(
                [a for a in (hid.get("ajax_endpoints") or []) if "admin-ajax" in a.lower()])[:300],
            "n_pages_fetched": len([p for p in pgs if p.get("http_status") == "200"
                                    and p.get("page_class") != "child_sitemap"]),
            "n_capacity_observations": n_cap, "n_identity_observations": n_ident,
            "vendor_tero_urls_found": ";".join(vendor_urls)[:1500],
            "checked_and_absent": ";".join(sorted(set(absent))),
            "terms_restricted": t["terms_restricted"],
            "population_basis": POPULATION_BASIS,
            "checked_date": TODAY, "built_by": "code/980_gaming_web_harvest.py",
        })

    write_csv(OBS, OBS_COLS, obs)
    write_csv(COV, COV_COLS, cov)
    log(f"build: {len(obs)} observations -> {OBS}")
    log(f"build: {len(cov)} coverage rows -> {COV}")
    st = {}
    for c in cov:
        st[c["harvest_status"]] = st.get(c["harvest_status"], 0) + 1
    for k in sorted(st, key=lambda x: -st[x]):
        log(f"   {st[k]:>5}  {k}")


def write_csv(path, cols, rows):
    tmp = path + ".part"
    with io.open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    os.replace(tmp, path)


# ===========================================================================
# STAGE 5 — verify. Exits 1 when an invariant breaks.
# ===========================================================================
def _read(path):
    if not os.path.exists(path):
        return []
    return list(csv.DictReader(io.open(path, encoding="utf-8-sig")))


def verify(obs_path=OBS, cov_path=COV, probe_path=PROBE):
    fails = []
    obs = _read(obs_path)
    cov = _read(cov_path)

    # I1 — every observation carries provenance a customer can check
    for r in obs:
        if not (r.get("source_url") or "").startswith("http"):
            fails.append(f"I1 no source_url: {r.get('observation_id')}")
            break
    for r in obs:
        if not (r.get("source_quote") or "").strip():
            fails.append(f"I1b empty source_quote: {r.get('observation_id')}")
            break

    # I2 — THE FENCE. Every capacity row is classed self-published and says what
    # it may not be summed against.
    for r in obs:
        if r.get("observation_kind") == "CAPACITY_SIGNAL":
            if r.get("assertion_class") != ASSERTION_CLASS:
                fails.append(f"I2 capacity row not classed self-published: {r.get('observation_id')}")
                break
            if not (r.get("not_summable_with") or "").strip():
                fails.append(f"I2b capacity row missing not_summable_with: {r.get('observation_id')}")
                break

    # I3 — no observation, and no fetched probe row, from a restricted source
    for r in obs:
        if is_restricted_host(r.get("site_host", "")) or \
           is_restricted_tribe(r.get("tribe_id"), r.get("tribe_name")):
            fails.append(f"I3 observation from TERMS_STATED_RESTRICTIVE source: "
                         f"{r.get('site_host')} / {r.get('tribe_name')}")
            break
    if os.path.exists(probe_path):
        for line in io.open(probe_path, encoding="utf-8"):
            try:
                p = json.loads(line)
            except Exception:
                continue
            if (p.get("http_status") or "").isdigit() and is_restricted_host(p.get("host", "")):
                fails.append(f"I3b fetched a TERMS_STATED_RESTRICTIVE host: {p.get('host')}")
                break

    # I4 — no admin / login path was ever requested
    if os.path.exists(probe_path):
        for path in (probe_path, PAGES):
            if not os.path.exists(path):
                continue
            bad = None
            for line in io.open(path, encoding="utf-8"):
                try:
                    p = json.loads(line)
                except Exception:
                    continue
                u = p.get("url") or ""
                if u and forbidden_path(u) and (p.get("http_status") or "").isdigit():
                    bad = u
                    break
            if bad:
                fails.append(f"I4 requested a forbidden path: {bad}")

    # I5 — the identical-md5 ceiling: N objects must not be N copies of one file
    md5s, kinds = {}, {}
    for path in (probe_path, PAGES):
        if not os.path.exists(path):
            continue
        for line in io.open(path, encoding="utf-8"):
            try:
                p = json.loads(line)
            except Exception:
                continue
            if p.get("md5"):
                k = p.get("endpoint_kind") or p.get("page_class") or "page"
                kinds.setdefault(k, []).append(p["md5"])
                md5s[p["md5"]] = md5s.get(p["md5"], 0) + 1
    for k, v in kinds.items():
        if len(v) >= 10 and len(set(v)) < max(2, len(v) // 4):
            fails.append(f"I5 IDENTICAL_MD5_CEILING on {k}: {len(v)} objects, "
                         f"{len(set(v))} distinct hashes")

    # I6 — coverage must separate 'touched, nothing found' from 'untouched'
    allowed = {"HARVESTED", "TOUCHED_NOTHING_FOUND", "UNTOUCHED",
               "EXCLUDED_TERMS_STATED_RESTRICTIVE", "REFUSED_ROBOTS_DISALLOW",
               "REACHED_BUT_PARKED_DOMAIN", "REACHED_BUT_DOMAIN_SUSPECT"}
    for c in cov:
        s = c.get("harvest_status") or ""
        if s not in allowed and not s.startswith("UNREACHABLE_"):
            fails.append(f"I6 unknown harvest_status {s!r} on {c.get('site_host')}")
            break

    # I7 — every observation's host has a coverage row (no orphan observations)
    covhosts = {c.get("site_host") for c in cov}
    for r in obs:
        if r.get("site_host") not in covhosts:
            fails.append(f"I7 observation host with no coverage row: {r.get('site_host')}")
            break

    log(f"verify: {len(obs)} observations, {len(cov)} coverage rows, "
        f"{len(fails)} invariant failures")
    for f in fails:
        log("  FAIL " + f)
    return fails


def selftest():
    """Prove the invariants FIRE on a synthetic violation."""
    import tempfile
    d = tempfile.mkdtemp(prefix="gwh_selftest_")
    o = os.path.join(d, "obs.csv")
    c = os.path.join(d, "cov.csv")
    p = os.path.join(d, "probe.jsonl")

    good_cov = [{col: "" for col in COV_COLS}]
    good_cov[0].update({"site_host": "example-casino.com", "harvest_status": "HARVESTED"})
    write_csv(c, COV_COLS, good_cov)

    def obs_row(**kw):
        r = {col: "" for col in OBS_COLS}
        r.update({"observation_id": "GWH-test", "observation_kind": "CAPACITY_SIGNAL",
                  "assertion_class": ASSERTION_CLASS, "not_summable_with": NOT_SUMMABLE,
                  "source_url": "https://example-casino.com/gaming",
                  "source_quote": "1,200 slot machines", "site_host": "example-casino.com",
                  "tribe_id": "TRBF-TESTNG-00", "tribe_name": "Test Nation"})
        r.update(kw)
        return r

    cases = [
        ("I1  missing source_url", obs_row(source_url=""), None),
        ("I1b missing source_quote", obs_row(source_quote=""), None),
        ("I2  capacity not classed self-published",
         obs_row(assertion_class="NIGC_OFFICIAL"), None),
        ("I2b capacity missing not_summable_with", obs_row(not_summable_with=""), None),
        ("I3  observation from a restricted host",
         obs_row(site_host="colvilletribes.com"), None),
        ("I7  orphan observation host", obs_row(site_host="orphan-host.com"), None),
    ]
    ok = True
    for label, row, _ in cases:
        write_csv(o, OBS_COLS, [row])
        io.open(p, "w", encoding="utf-8").close()
        f = verify(o, c, p)
        fired = len(f) > 0
        log(f"  selftest {'PASS' if fired else 'DID NOT FIRE'}: {label}")
        ok = ok and fired

    # I3b — a fetched restricted host in the probe log
    write_csv(o, OBS_COLS, [obs_row()])
    with io.open(p, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"host": "yakama.com", "endpoint_kind": "home",
                             "http_status": "200", "url": "https://yakama.com/"}) + "\n")
    fired = any(x.startswith("I3b") for x in verify(o, c, p))
    log(f"  selftest {'PASS' if fired else 'DID NOT FIRE'}: I3b fetched a restricted host")
    ok = ok and fired

    # I4 — a forbidden path that was actually requested
    with io.open(p, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"host": "example-casino.com", "endpoint_kind": "x",
                             "http_status": "200",
                             "url": "https://example-casino.com/wp-admin/admin-ajax.php"}) + "\n")
    fired = any(x.startswith("I4") for x in verify(o, c, p))
    log(f"  selftest {'PASS' if fired else 'DID NOT FIRE'}: I4 forbidden path requested")
    ok = ok and fired

    # I5 — 12 objects, 1 distinct hash
    with io.open(p, "w", encoding="utf-8") as fh:
        for i in range(12):
            fh.write(json.dumps({"host": f"h{i}.com", "endpoint_kind": "home",
                                 "http_status": "200", "md5": "deadbeef" * 4,
                                 "url": f"https://h{i}.com/"}) + "\n")
    fired = any(x.startswith("I5") for x in verify(o, c, p))
    log(f"  selftest {'PASS' if fired else 'DID NOT FIRE'}: I5 identical-md5 ceiling")
    ok = ok and fired

    # I6 — an unknown harvest_status
    io.open(p, "w", encoding="utf-8").close()
    bad_cov = [dict(good_cov[0])]
    bad_cov[0]["harvest_status"] = "SOMETHING_ELSE"
    write_csv(c, COV_COLS, bad_cov)
    fired = any(x.startswith("I6") for x in verify(o, c, p))
    log(f"  selftest {'PASS' if fired else 'DID NOT FIRE'}: I6 unknown harvest_status")
    ok = ok and fired

    # and the clean case must PASS
    write_csv(c, COV_COLS, good_cov)
    clean = verify(o, c, p)
    log(f"  selftest {'PASS' if not clean else 'FALSE POSITIVE'}: clean input produces 0 failures")
    ok = ok and not clean
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["targets", "probe", "pages", "build", "verify"])
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--deadline-min", type=int, default=110)
    ap.add_argument("--surface", default=None, choices=[None, "gaming", "tribe"])
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.stage == "targets":
        stage_targets()
    elif a.stage == "probe":
        stage_probe(a.limit, a.deadline_min, a.surface)
    elif a.stage == "pages":
        stage_pages(a.limit, a.deadline_min)
    elif a.stage == "build":
        stage_build()
    elif a.stage == "verify":
        if a.selftest:
            ok = selftest()
            sys.exit(0 if ok else 1)
        fails = verify()
        sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
