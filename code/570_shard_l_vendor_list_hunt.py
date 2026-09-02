"""
570_shard_l_vendor_list_hunt.py - WORKSTREAM SHARD-L

Hunts published Native-owned / tribally certified BUSINESS LISTS for the first
half (by cedar_uid) of the 297 federally recognised tribes that have never been
checked, per docs/datasets/native-owned-businesses.md.

A "list" is any of: TERO vendor list, Indian-preference list, tribal business
licence register, certified vendor directory, procurement bidder list, tribal
enterprise register, chamber-of-commerce directory.

SELECTION DECLARATION (docs/PULL_DISCIPLINE.md)
    leg used     : KNOWN_IDENTIFIER - the spine's own federally-recognised-tribe
                   class, minus the tribes already in
                   review/tribal_vendor_list_registry_2026-08-26.csv, sorted by
                   cedar_uid, first half.
    leg missing  : no TYPE_FILTER exists for "tribe that publishes a vendor
                   list"; that is precisely what this workstream is measuring.
    population_basis stamped on every registry row: shard_l_frt_unchecked_half1

MODES
    plan     build the target table from data/staging/tribe_web_map/shard_*.csv
             (sibling shards already established hundreds of government hosts
             with evidence quotes - those URLs are REUSED, not rediscovered)
    offline  zero-network mine of the ~2,700 raw bodies siblings already saved
             under data/staging/tribe_harvest/shard_*/raw
    sweep    docs/HIDDEN_DATA_TECHNIQUES.md checklist against each host:
                /wp-json/wp/v2/types            custom post types (vendor CPTs)
                /wp-json/wp/v2/media?mime_type=application/pdf   EVERY PDF,
                                                including ones no page links to
                /wp-json/wp/v2/pages?search=... unlinked pages
                /sitemap_index.xml, /sitemap.xml
    terms    fetch the terms-of-use page for every host holding a candidate,
             BEFORE anything is harvested from it
    fetch    retrieve candidate documents whose host cleared the terms check

BOUNDARY (docs/HIDDEN_DATA_TECHNIQUES.md, non-negotiable)
  * documented public endpoints only; no admin/staging/auth path is requested;
  * robots.txt Disallow honoured per URL;
  * hosts of any source marked TERMS_STATED_RESTRICTIVE in the registry are
    excluded BY NAME below and never requested, by any route including the
    media API and Wayback. Terms are a decision the publisher made.

docs/PULL_DISCIPLINE.md governs throughout: 1 poller, global + per-host delay,
exponential backoff, RUN_DEADLINE, refusal codes recorded as findings.
"""
import collections, csv, glob, hashlib, io, json, os, re, sys, time, urllib.parse
import urllib.robotparser as robotparser
from datetime import date, datetime, timezone

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SL = os.path.join(ROOT, "data", "staging", "tribe_harvest", "shard_l")
RAW = os.path.join(SL, "raw")
os.makedirs(RAW, exist_ok=True)

SPINE = os.path.join(ROOT, "data", "spine", "cedar_identity_register.csv")
REGISTRY = os.path.join(ROOT, "review", "tribal_vendor_list_registry_2026-08-26.csv")
WEBMAP = os.path.join(ROOT, "data", "staging", "tribe_web_map")
TARGETS = os.path.join(SL, "_targets.json")
# Parallel sweep slices write to their own files so two appenders never
# interleave a line; every reader globs the family.
_SFX = os.environ.get("SHARD_L_SLICE", "")
PROBE = os.path.join(SL, f"probe{_SFX}.jsonl")
DOCS = os.path.join(SL, f"documents{_SFX}.jsonl")
TERMS = os.path.join(SL, f"terms{_SFX}.jsonl")
PROBE_ALL = os.path.join(SL, "probe*.jsonl")
DOCS_ALL = os.path.join(SL, "documents*.jsonl")
TERMS_ALL = os.path.join(SL, "terms*.jsonl")


def read_all(pattern):
    for p in sorted(glob.glob(pattern)):
        for line in io.open(p, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue

UA = ("CedarPressResearchBot/1.0 (academic research; "
      "contact elijahsamsonmoreno@gmail.com)")
HEADERS = {"User-Agent": UA,
           "Accept": "application/json,application/xml,text/xml,text/html,*/*"}
BROWSER_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 "
                   "CedarPressResearchBot/1.0 "
                   "(+contact elijahsamsonmoreno@gmail.com)"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"}
GLOBAL_DELAY, PER_HOST_DELAY, TIMEOUT = 1.2, 3.0, 25
RUN_DEADLINE = time.time() + 2 * 3600

# Hosts whose published source states restrictive terms. Never requested.
TERMS_RESTRICTIVE_HOSTS = {
    "navajoeconomy.org", "www.navajoeconomy.org",
    "www.colvilletribes.com", "colvilletribes.com",
    "yakama.com", "www.yakama.com",
    "ctuir.org", "www.ctuir.org",
    "chickasaw.net", "www.chickasaw.net", "chickasawbusinessnetwork.com",
    "fcpotawatomi.com", "www.fcpotawatomi.com", "shop.fcpotawatomi.com",
    "tulaliptero.com", "tulaliptribes-nsn.gov", "www.tulaliptribes-nsn.gov",
    "southernute-nsn.gov", "www.southernute-nsn.gov", "sugf.com",
    "nana.com", "www.nana.com", "akima.com", "www.akima.com",
}

# What makes a document or page look like a LIST rather than a form/ordinance.
LIST_KW = re.compile(
    r"(tero|indian[\W_]{0,3}pref|native[\W_]{0,3}owned|indian[\W_]{0,3}owned|"
    r"certified[\W_]{0,3}(?:business|contractor|firm|vendor|indian)|"
    r"vendor[\W_]{0,3}(?:list|directory|register|roster|report)|"
    r"(?:business|contractor|supplier|bidder)[\W_]{0,3}"
    r"(?:list|directory|register|registry|roster)|"
    r"business[\W_]{0,3}licen|chamber[\W_]{0,3}of[\W_]{0,3}commerce|"
    r"tribal[\W_]{0,3}enterprise|procurement)", re.I)
# Strong signal: the document is a roster, not paperwork about one.
STRONG_KW = re.compile(
    r"((?:vendor|contractor|business|firm|supplier|company|companies)"
    r"[\W_]{0,3}(?:list|directory|registry|register|roster)|"
    r"(?:list|directory|registry|roster)[\W_]{0,3}of[\W_]{0,3}"
    r"(?:vendor|contractor|business|indian|native)|"
    r"certified[\W_]{0,3}(?:indian|native|tero)|"
    r"indian[\W_]{0,3}pref\w*[\W_]{0,3}(?:list|compan|business|contractor|"
    r"vendor|firm|director(?:y|ies))|tero[\W_]{0,3}(?:vendor|director(?:y|ies)|certif|list|ip))",
    re.I)
# Paperwork, not a roster - down-weighted, never auto-promoted.
FORM_KW = re.compile(
    r"(application|app\b|form|ordinance|code\b|regulation|resolution|"
    r"agreement|policy|plan\b|brochure|flyer|complaint|checklist|"
    r"instructions|amendment|bylaw|by-law)", re.I)

_last_global, _last_host, _robots = [0.0], {}, {}
_blocked_cache = {"stamp": None, "set": None}


def _blocked_hosts():
    """ONE source of truth for "we do not request this host", read by the single
    chokepoint every request passes through.

    It is the union of the named TERMS_STATED_RESTRICTIVE hosts and every host
    whose OWN terms page this run recorded as restrictive. A refusal enforced in
    one branch and not another is not a refusal - shard M caught exactly that
    defect on 2026-09-01, where a --deep path read the constant instead of the
    verdict the same script had already written."""
    stamp = tuple(sorted((f, os.path.getmtime(f))
                         for f in glob.glob(TERMS_ALL)))
    if _blocked_cache["stamp"] == stamp and _blocked_cache["set"] is not None:
        return _blocked_cache["set"]
    blocked = set(TERMS_RESTRICTIVE_HOSTS)
    for r in read_all(TERMS_ALL):
        if r.get("restrictive_hit"):
            blocked.add(r["host"])
    _blocked_cache["stamp"], _blocked_cache["set"] = stamp, blocked
    return blocked


def deadline_ok():
    return time.time() < RUN_DEADLINE


def _sleep_for(host):
    now = time.time()
    w = max(GLOBAL_DELAY - (now - _last_global[0]),
            PER_HOST_DELAY - (now - _last_host.get(host, 0.0)), 0.0)
    if w > 0:
        time.sleep(w)
    _last_global[0] = time.time()
    _last_host[host] = time.time()


def robots_ok(url):
    """None = no robots.txt served. False = Disallow. True = allowed."""
    p = urllib.parse.urlparse(url)
    host = p.netloc
    if host not in _robots:
        rp = robotparser.RobotFileParser()
        _sleep_for(host)
        try:
            r = requests.get(f"{p.scheme}://{host}/robots.txt",
                             headers=HEADERS, timeout=15)
            _robots[host] = (rp.parse(r.text.splitlines()) or rp) \
                if r.status_code == 200 else None
        except Exception:
            _robots[host] = None
    rp = _robots[host]
    if rp is None:
        return None
    try:
        return rp.can_fetch(UA, url)
    except Exception:
        return None


def save(url, content, ext):
    h = hashlib.sha1(url.encode()).hexdigest()[:16]
    host = urllib.parse.urlparse(url).netloc or "nohost"
    fn = f"{host}__{h}{ext}"
    with open(os.path.join(RAW, fn), "wb") as f:
        f.write(content)
    return fn


def get(url, host, kind, meta, stream_limit=None):
    """One rate-limited GET. Always returns a record; never raises."""
    rec = {"host": host, "kind": kind, "url": url, "http_status": "",
           "content_type": None, "bytes": None, "raw_file": None, "note": "",
           "checked_date": date.today().isoformat()}
    rec.update(meta)
    if host in _blocked_hosts():
        rec["http_status"] = "EXCLUDED_TERMS"
        rec["note"] = ("host belongs to a source marked TERMS_STATED_RESTRICTIVE, "
                       "or its own terms page states a restriction this run "
                       "recorded; not requested by any route")
        return rec, None
    if not deadline_ok():
        rec["http_status"] = "RUN_DEADLINE"
        return rec, None
    ro = robots_ok(url)
    if ro is False:
        rec["http_status"] = "ROBOTS_DISALLOW"
        rec["note"] = "robots.txt disallows this path for our UA; not fetched"
        return rec, None
    if ro is None:
        rec["note"] = "no robots.txt served; proceeded"
    _sleep_for(host)
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT,
                         allow_redirects=True)
    except Exception as e:
        rec["http_status"] = "TRANSPORT_FAILURE"
        rec["note"] += f"; {type(e).__name__}: {str(e)[:140]}"
        return rec, None
    # A 403/406 from an edge filter is very often a USER-AGENT filter, not a
    # refusal: the same server serves the same bytes to a browser. Speaking
    # HTTP the way a browser does is not a bypass. A robots.txt Disallow, a
    # login wall and TERMS_STATED_RESTRICTIVE stay refusals and are never
    # retried.
    if r.status_code in (403, 406, 501):
        rec["ua_filter_retry"] = True
        _sleep_for(host)
        try:
            r2 = requests.get(url, headers=BROWSER_HEADERS, timeout=TIMEOUT,
                              allow_redirects=True)
            if r2.status_code < 400:
                rec["note"] += (f"; origin returned {r.status_code} to our "
                                f"declared UA and {r2.status_code} to browser "
                                f"headers - a UA filter, not a refusal")
                r = r2
            else:
                rec["note"] += (f"; browser headers also {r2.status_code} - "
                                f"treated as a real refusal")
        except Exception as e:
            rec["note"] += f"; browser-header retry {type(e).__name__}"
    rec["http_status"] = str(r.status_code)
    rec["content_type"] = (r.headers.get("Content-Type") or "").split(";")[0]
    rec["bytes"] = len(r.content or b"")
    rec["final_url"] = r.url
    for h in ("X-WP-Total", "X-WP-TotalPages"):
        if r.headers.get(h):
            rec[h.lower()] = r.headers[h]
    return rec, r


def append(path, rec):
    with io.open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        f.flush()


# --------------------------------------------------------------- plan --------
def cmd_plan():
    spine = list(csv.DictReader(io.open(SPINE, encoding="utf-8-sig")))
    frt = [r for r in spine if r["entity_class"] == "Federally recognized tribe"]
    reg = list(csv.DictReader(io.open(REGISTRY, encoding="utf-8-sig")))
    already = set(r["tribe_id"].strip() for r in reg)
    rem = sorted((r for r in frt if r["handle"].strip() not in already),
                 key=lambda r: r["cedar_uid"])
    half = (len(rem) + 1) // 2          # first half, rounded UP: a duplicate
    mine = rem[:half]                   # row is recoverable, a gap is silent
    wm = {}
    for f in sorted(glob.glob(os.path.join(WEBMAP, "shard_*.csv"))):
        for row in csv.DictReader(io.open(f, encoding="utf-8-sig")):
            wm.setdefault(row["cedar_uid"], []).append(row)
    out = []
    for r in mine:
        ent = wm.get(r["cedar_uid"], [])
        hosts, gov = [], ""
        for e in ent:
            u = (e.get("url") or "").strip()
            if not u.startswith("http"):
                continue
            if e["url_type"] == "casino":
                continue            # a casino site is not the government site
            h = urllib.parse.urlparse(u).netloc.lower()
            if h and h not in hosts:
                hosts.append(h)
            if e["url_type"] == "government" and not gov:
                gov = u
        out.append({"cedar_uid": r["cedar_uid"], "tribe_id": r["handle"],
                    "canonical_name": r["canonical_name"],
                    "official_site": gov, "hosts": hosts,
                    "webmap_rows": len(ent)})
    json.dump(out, io.open(TARGETS, "w", encoding="utf-8"), indent=1)
    hs = sorted({h for o in out for h in o["hosts"]})
    print(f"remaining unchecked FRT: {len(rem)}  shard L: {len(mine)}  "
          f"shard M: {len(rem) - half}")
    print(f"L boundary: first={mine[0]['cedar_uid']} last={mine[-1]['cedar_uid']} "
          f"M starts={rem[half]['cedar_uid']}")
    print(f"tribes with a reused host: {sum(1 for o in out if o['hosts'])}  "
          f"without: {sum(1 for o in out if not o['hosts'])}")
    print(f"distinct hosts: {len(hs)}")


# ------------------------------------------------------------ offline --------
def cmd_offline():
    """Tier 1 of the sweep doctrine: zero requests, re-read what we already own."""
    tg = json.load(io.open(TARGETS, encoding="utf-8"))
    mine = {}
    for o in tg:
        for h in o["hosts"]:
            mine[h] = o
            mine[h.replace("www.", "")] = o
    urlpat = re.compile(r"""https?://[^\s"'<>\\)\]]+?\.(?:pdf|xlsx|xls|csv|docx?)""",
                        re.I)
    seen, n = {}, 0
    # lint-ok: class1 - the promoted table is not the subject here. This mode
    # deliberately re-reads the RAW HTTP BODIES sibling shards already saved
    # (docs/PULL_DISCIPLINE.md tier 1, zero requests); no promoted table holds
    # them, and reading data/clean instead would find nothing.
    for d in glob.glob(os.path.join(ROOT, "data", "staging", "tribe_harvest",
                                    "shard_*", "raw")):
        for fn in os.listdir(d):
            p = os.path.join(d, fn)
            try:
                if os.path.getsize(p) > 25_000_000:
                    continue
                t = io.open(p, encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            n += 1
            for m in set(urlpat.findall(t)):
                u = m.replace("\\/", "/")
                try:
                    h = u.split("/")[2].lower()
                except Exception:
                    continue
                o = mine.get(h)
                if o is None or not LIST_KW.search(u):
                    continue
                seen[u] = {"cedar_uid": o["cedar_uid"], "tribe_id": o["tribe_id"],
                           "canonical_name": o["canonical_name"], "host": h,
                           "document_url": u, "title": "",
                           "discovery_technique":
                               "offline re-read of sibling raw bodies "
                               "(docs/PULL_DISCIPLINE.md tier 1, zero requests)",
                           "found_in": os.path.basename(d.rstrip("/raw")) or d,
                           "strong": bool(STRONG_KW.search(u)),
                           "formish": bool(FORM_KW.search(u)),
                           "checked_date": date.today().isoformat()}
    for r in seen.values():
        append(DOCS, r)
    print(f"scanned {n} sibling raw bodies; {len(seen)} candidate documents on "
          f"shard-L hosts ({sum(1 for r in seen.values() if r['strong'])} strong)")


# -------------------------------------------------------------- sweep --------
WP_PAGES = 6          # /wp/v2/media pages max per host (600 docs)


def _media_rows(o, host, body, endpoint):
    rows = []
    try:
        data = json.loads(body)
    except Exception:
        return rows
    if not isinstance(data, list):
        return rows
    for it in data:
        if not isinstance(it, dict):
            continue
        u = it.get("source_url") or ""
        title = ((it.get("title") or {}).get("rendered") or "")
        if not u:
            continue
        hay = f"{u} {title}"
        if not LIST_KW.search(hay):
            continue
        rows.append({"cedar_uid": o["cedar_uid"], "tribe_id": o["tribe_id"],
                     "canonical_name": o["canonical_name"], "host": host,
                     "media_id": it.get("id"), "document_url": u,
                     "title": title[:200], "mime_type": it.get("mime_type"),
                     "site_recorded_date": it.get("date"),
                     "site_modified_date": it.get("modified"),
                     "discovery_technique":
                         "docs/HIDDEN_DATA_TECHNIQUES.md #3 "
                         "(WordPress REST /wp/v2/media - every uploaded file, "
                         "including ones no page links to)",
                     "source_endpoint": endpoint,
                     "strong": bool(STRONG_KW.search(hay)),
                     "formish": bool(FORM_KW.search(hay)),
                     "checked_date": date.today().isoformat()})
    return rows


def _page_rows(o, host, body, endpoint, kind):
    rows = []
    try:
        data = json.loads(body)
    except Exception:
        return rows
    if not isinstance(data, list):
        return rows
    for it in data:
        if not isinstance(it, dict):
            continue
        link = it.get("link") or ""
        title = ((it.get("title") or {}).get("rendered") or "")
        hay = f"{link} {title}"
        if not LIST_KW.search(hay):
            continue
        rows.append({"cedar_uid": o["cedar_uid"], "tribe_id": o["tribe_id"],
                     "canonical_name": o["canonical_name"], "host": host,
                     "media_id": it.get("id"), "document_url": link,
                     "title": title[:200], "mime_type": "text/html",
                     "site_recorded_date": it.get("date"),
                     "site_modified_date": it.get("modified"),
                     "discovery_technique":
                         f"docs/HIDDEN_DATA_TECHNIQUES.md #3 "
                         f"(WordPress REST {kind})",
                     "source_endpoint": endpoint,
                     "strong": bool(STRONG_KW.search(hay)),
                     "formish": bool(FORM_KW.search(hay)),
                     "checked_date": date.today().isoformat()})
    return rows


def cmd_sweep(only_host=None, shard=None):
    """shard = (i, n): take every n-th host. Slices are DISJOINT BY HOST, so two
    processes never share a host budget (docs/PULL_DISCIPLINE.md rule 1)."""
    tg = json.load(io.open(TARGETS, encoding="utf-8"))
    done = set((r["host"], r["kind"]) for r in read_all(PROBE_ALL))
    host_owner = {}
    for o in tg:
        for h in o["hosts"]:
            host_owner.setdefault(h, o)
    hosts = [h for h in host_owner if (only_host is None or h == only_host)]
    hosts = sorted(hosts)
    if shard:
        i, n = shard
        hosts = [h for k, h in enumerate(hosts) if k % n == i]
    print(f"{len(hosts)} hosts")
    for host in hosts:
        if not deadline_ok():
            print("RUN_DEADLINE reached"); break
        o = host_owner[host]
        base = f"https://{host}"
        wp_alive = None

        # 1. custom post types - a vendor directory is often a CPT
        if (host, "wp_types") not in done:
            rec, r = get(f"{base}/wp-json/wp/v2/types", host, "wp_types",
                         {"cedar_uid": o["cedar_uid"], "tribe_id": o["tribe_id"],
                          "canonical_name": o["canonical_name"],
                          "technique": "docs/HIDDEN_DATA_TECHNIQUES.md #3 "
                                       "(WP REST custom post types)"})
            if r is not None and r.status_code == 200 and "json" in (rec["content_type"] or ""):
                wp_alive = True
                try:
                    d = json.loads(r.text)
                    rec["post_types"] = sorted(d.keys()) if isinstance(d, dict) else []
                    rec["cpt_rest_bases"] = {
                        k: (v or {}).get("rest_base")
                        for k, v in (d.items() if isinstance(d, dict) else [])
                        if isinstance(v, dict) and k not in
                        ("post", "page", "attachment", "nav_menu_item",
                         "wp_block", "wp_template", "wp_template_part",
                         "wp_navigation", "wp_global_styles", "wp_font_family",
                         "wp_font_face", "wp_pattern", "wp_pattern_category")}
                    rec["raw_file"] = save(r.url, r.content, ".json")
                except Exception as e:
                    rec["parse_note"] = f"{type(e).__name__}: {str(e)[:120]}"
            else:
                wp_alive = False
            append(PROBE, rec); done.add((host, "wp_types"))
            print(f"  {rec['http_status']:>18} wp_types       {host} "
                  f"cpt={len(rec.get('cpt_rest_bases') or {})}")

        if wp_alive is False:
            # not WordPress (or WP REST off) - sitemap is the remaining route
            if (host, "sitemap_index") not in done:
                rec, r = get(f"{base}/sitemap_index.xml", host, "sitemap_index",
                             {"cedar_uid": o["cedar_uid"], "tribe_id": o["tribe_id"],
                              "canonical_name": o["canonical_name"],
                              "technique": "docs/HIDDEN_DATA_TECHNIQUES.md #4"})
                if r is not None and r.status_code == 200:
                    locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r.text)
                    rec["n_items"] = len(locs)
                    rec["hits"] = [u for u in locs if LIST_KW.search(u)][:60]
                    rec["sub_sitemaps"] = [u for u in locs
                                           if u.lower().endswith(".xml")][:40]
                    rec["raw_file"] = save(r.url, r.content, ".xml")
                    for u in rec["hits"]:
                        append(DOCS, {
                            "cedar_uid": o["cedar_uid"], "tribe_id": o["tribe_id"],
                            "canonical_name": o["canonical_name"], "host": host,
                            "media_id": None, "document_url": u, "title": "",
                            "mime_type": None, "site_recorded_date": None,
                            "site_modified_date": None,
                            "discovery_technique":
                                "docs/HIDDEN_DATA_TECHNIQUES.md #4 (sitemap)",
                            "source_endpoint": rec["url"],
                            "strong": bool(STRONG_KW.search(u)),
                            "formish": bool(FORM_KW.search(u)),
                            "checked_date": date.today().isoformat()})
                append(PROBE, rec); done.add((host, "sitemap_index"))
                print(f"  {rec['http_status']:>18} sitemap_index  {host} "
                      f"n={rec.get('n_items')} hits={len(rec.get('hits') or [])}")
            continue

        # 2. every uploaded document, paginated
        total_pages = None
        for pg in range(1, WP_PAGES + 1):
            kind = f"wp_media_p{pg}"
            if (host, kind) in done:
                continue
            if total_pages is not None and pg > total_pages:
                break
            url = (f"{base}/wp-json/wp/v2/media?per_page=100&page={pg}"
                   f"&mime_type=application/pdf")
            rec, r = get(url, host, kind,
                         {"cedar_uid": o["cedar_uid"], "tribe_id": o["tribe_id"],
                          "canonical_name": o["canonical_name"],
                          "technique": "docs/HIDDEN_DATA_TECHNIQUES.md #3 "
                                       "(WP REST media, mime_type=application/pdf)"})
            append(PROBE, rec); done.add((host, kind))
            if r is None or r.status_code != 200:
                break
            try:
                total_pages = int(rec.get("x-wp-totalpages") or 1)
            except Exception:
                total_pages = 1
            rows = _media_rows(o, host, r.text, url)
            rec["n_hits"] = len(rows)
            for row in rows:
                append(DOCS, row)
            print(f"  {rec['http_status']:>18} {kind:14} {host} "
                  f"total={rec.get('x-wp-total')} hits={len(rows)}")
            if pg >= (total_pages or 1):
                break

        # 3. unlinked pages naming a vendor list
        for term in ("tero", "vendor", "business"):
            kind = f"wp_pages_{term}"
            if (host, kind) in done:
                continue
            url = f"{base}/wp-json/wp/v2/pages?per_page=100&search={term}"
            rec, r = get(url, host, kind,
                         {"cedar_uid": o["cedar_uid"], "tribe_id": o["tribe_id"],
                          "canonical_name": o["canonical_name"],
                          "technique": "docs/HIDDEN_DATA_TECHNIQUES.md #3 "
                                       "(WP REST pages, incl. pages absent from nav)"})
            append(PROBE, rec); done.add((host, kind))
            if r is None or r.status_code != 200:
                continue
            rows = _page_rows(o, host, r.text, url, f"pages?search={term}")
            rec["n_hits"] = len(rows)
            for row in rows:
                append(DOCS, row)
            if rows:
                print(f"  {rec['http_status']:>18} {kind:14} {host} "
                      f"hits={len(rows)}")


MR_TERMS = ("tero", "vendor", "preference", "contractor", "business")


def cmd_machine_readable(shard=None):
    """The `no list` bar. A negative recorded from search or navigation alone is
    NOT evidence: a PDF referenced from one RFP, or linked from a page since
    deleted, is invisible to site search, to a search engine and to the nav, and
    is sitting in /wp-json/wp/v2/media. This pass runs, per host:

        /wp-json/wp/v2/media?per_page=100&page=N   ALL media, NOT mime-filtered
                                                   (a .docx vendor list is the
                                                   exact thing a pdf filter drops)
        /wp-json/wp/v2/search?search=<term>        the WP search index
        (custom post types are followed by cmd_cpt)

    Only after these is NOT_PUBLISHED a finding. Before them the honest status
    is NOT_SEARCHED_MACHINE_READABLE, which tells the next agent there is work
    left rather than closing the door."""
    tg = json.load(io.open(TARGETS, encoding="utf-8"))
    host_owner = {}
    for o in tg:
        for h in o["hosts"]:
            host_owner.setdefault(h, o)
    extra = os.path.join(SL, "_extra_hosts.json")
    if os.path.exists(extra):
        for e in json.load(io.open(extra, encoding="utf-8")):
            host_owner.setdefault(e["host"], e)
    done = set((r["host"], r["kind"]) for r in read_all(PROBE_ALL))
    wp_ok = set(r["host"] for r in read_all(PROBE_ALL)
                if r.get("kind") == "wp_types" and r.get("http_status") == "200"
                and (r.get("post_types") or r.get("cpt_rest_bases")))
    hosts = sorted(h for h in host_owner if h in wp_ok)
    if shard:
        i, n = shard
        hosts = [h for k, h in enumerate(hosts) if k % n == i]
    print(f"{len(hosts)} WordPress hosts for the machine-readable pass")
    for host in hosts:
        if not deadline_ok():
            print("RUN_DEADLINE")
            break
        o = host_owner[host]
        base = {"cedar_uid": o.get("cedar_uid", ""), "tribe_id": o["tribe_id"],
                "canonical_name": o.get("canonical_name", "")}
        total_pages = None
        for pg in range(1, 61):
            kind = f"wp_allmedia_p{pg}"
            if (host, kind) in done:
                continue
            if total_pages is not None and pg > total_pages:
                break
            url = f"https://{host}/wp-json/wp/v2/media?per_page=100&page={pg}"
            rec, r = get(url, host, kind, dict(
                base, technique="docs/HIDDEN_DATA_TECHNIQUES.md #3 (WP REST "
                                "media, UNFILTERED - every uploaded file, not "
                                "just PDFs)"))
            append(PROBE, rec)
            done.add((host, kind))
            if r is None or r.status_code != 200:
                break
            try:
                total_pages = int(rec.get("x-wp-totalpages") or 1)
            except Exception:
                total_pages = 1
            rows = _media_rows(o, host, r.text, url)
            rec["n_hits"] = len(rows)
            for row in rows:
                append(DOCS, row)
            if pg == 1 or rows:
                print(f"  {rec['http_status']:>6} {kind:16} {host:36} "
                      f"total={rec.get('x-wp-total')} pages={total_pages} "
                      f"hits={len(rows)}", flush=True)
            if pg >= (total_pages or 1):
                break
        for term in MR_TERMS:
            kind = f"wp_search_{term}"
            if (host, kind) in done:
                continue
            url = f"https://{host}/wp-json/wp/v2/search?search={term}&per_page=100"
            rec, r = get(url, host, kind, dict(
                base, technique="docs/HIDDEN_DATA_TECHNIQUES.md #3 (WP REST "
                                "search index)"))
            append(PROBE, rec)
            done.add((host, kind))
            if r is None or r.status_code != 200:
                continue
            try:
                data = json.loads(r.text)
            except Exception:
                continue
            hits = 0
            for it in (data if isinstance(data, list) else []):
                if not isinstance(it, dict):
                    continue
                hay = f"{it.get('url', '')} {it.get('title', '')}"
                if not LIST_KW.search(hay):
                    continue
                hits += 1
                append(DOCS, {
                    "cedar_uid": base["cedar_uid"], "tribe_id": base["tribe_id"],
                    "canonical_name": base["canonical_name"], "host": host,
                    "media_id": it.get("id"), "document_url": it.get("url"),
                    "title": str(it.get("title"))[:200],
                    "mime_type": it.get("subtype"),
                    "site_recorded_date": None, "site_modified_date": None,
                    "discovery_technique":
                        f"docs/HIDDEN_DATA_TECHNIQUES.md #3 (WP REST search "
                        f"index, search={term})",
                    "source_endpoint": url,
                    "strong": bool(STRONG_KW.search(hay)),
                    "formish": bool(FORM_KW.search(hay)),
                    "checked_date": date.today().isoformat()})
            if hits:
                print(f"  {rec['http_status']:>6} {kind:16} {host:36} "
                      f"hits={hits}", flush=True)


def cmd_cpt():
    """Follow the custom post types the /types call revealed, where the type
    name itself suggests a business/vendor register."""
    tg = {o["tribe_id"]: o for o in json.load(io.open(TARGETS, encoding="utf-8"))}
    want = re.compile(r"(vendor|business|enterprise|compan|contractor|supplier|"
                      r"director|tero|member|licen|procure)", re.I)
    todo = []
    for r in read_all(PROBE_ALL):
        if r.get("kind") != "wp_types":
            continue
        for name, base in (r.get("cpt_rest_bases") or {}).items():
            if base and want.search(name):
                todo.append((r["host"], r["tribe_id"], name, base))
    done = set((r["host"], r["kind"]) for r in read_all(PROBE_ALL))
    print(f"{len(todo)} candidate custom post types")
    for host, tid, name, base in todo:
        kind = f"wp_cpt_{name}"
        # lint-ok: class5 - `done` is the resume set read from every probe*.jsonl
        # at entry; each (host, kind) is requested at most once per run and the
        # loop's own writes go to the file, so re-reading it here would only
        # re-derive what is already loaded.
        if (host, kind) in done or not deadline_ok():
            continue
        o = tg.get(tid) or {"cedar_uid": "", "tribe_id": tid, "canonical_name": ""}
        url = f"https://{host}/wp-json/wp/v2/{base}?per_page=100"
        rec, r = get(url, host, kind,
                     {"cedar_uid": o["cedar_uid"], "tribe_id": tid,
                      "canonical_name": o["canonical_name"],
                      "technique": f"docs/HIDDEN_DATA_TECHNIQUES.md #3 "
                                   f"(WP REST custom post type '{name}')"})
        if r is not None and r.status_code == 200:
            rec["raw_file"] = save(r.url, r.content, ".json")
            try:
                d = json.loads(r.text)
                rec["n_items"] = len(d) if isinstance(d, list) else None
                rec["titles"] = [((x.get("title") or {}).get("rendered") or "")[:120]
                                 for x in d[:30] if isinstance(x, dict)]
            except Exception as e:
                rec["parse_note"] = f"{type(e).__name__}: {str(e)[:120]}"
        append(PROBE, rec)
        print(f"  {rec['http_status']:>18} {kind:26} {host} n={rec.get('n_items')}")


# -------------------------------------------------------------- terms --------
TERMS_PATHS = ["/terms-of-use/", "/terms/", "/terms-and-conditions/",
               "/privacy-policy/", "/legal/", "/disclaimer/"]
RESTRICT_RE = re.compile(
    r"(may not (?:be )?(?:copy|reproduc|redistribut|scrap|extract|harvest|mine)|"
    r"prohibit\w* (?:from )?(?:copying|reproduc|redistribut|scrap|extract|"
    r"harvest|data ?min|automated)|no(?:t)? (?:be )?(?:used|reused) "
    r"(?:for )?(?:any )?commercial|without (?:the )?(?:prior )?(?:express )?"
    r"written (?:permission|consent)|robot|spider|scrap\w+|data ?min\w+|"
    r"automated (?:means|system|tool|process|agent))", re.I)


def cmd_terms(hosts=None):
    """CHECK THE TERMS PAGE BEFORE HARVESTING, NOT AFTER."""
    if hosts is None:
        hosts = sorted({r["host"] for r in read_all(DOCS_ALL)})
    done = {}
    for r in read_all(TERMS_ALL):
        done.setdefault(r["host"], []).append(r.get("url"))
    for host in hosts:
        if not deadline_ok():
            print("RUN_DEADLINE"); break
        if host in _blocked_hosts():
            continue
        found = False
        for path in TERMS_PATHS:
            url = f"https://{host}{path}"
            if url in done.get(host, []):
                continue
            rec, r = get(url, host, "terms", {"path": path})
            if r is not None and r.status_code == 200 and "html" in (rec["content_type"] or ""):
                txt = re.sub(r"<script.*?</script>|<style.*?</style>", " ",
                             r.text, flags=re.S | re.I)
                txt = re.sub(r"<[^>]+>", " ", txt)
                txt = re.sub(r"\s+", " ", txt)
                m = RESTRICT_RE.search(txt)
                rec["terms_present"] = True
                rec["restrictive_hit"] = bool(m)
                if m:
                    i = max(0, m.start() - 220)
                    rec["quote"] = txt[i:m.end() + 260].strip()[:520]
                rec["raw_file"] = save(r.url, r.content, ".html")
                found = True
            append(TERMS, rec)
            if found:
                print(f"  {rec['http_status']:>18} terms {host}{path} "
                      f"restrictive={rec.get('restrictive_hit')}")
                break
        if not found:
            append(TERMS, {"host": host, "kind": "terms", "url": "",
                           "http_status": "NO_TERMS_PAGE_FOUND",
                           "note": "none of " + ",".join(TERMS_PATHS) +
                                   " returned HTML 200",
                           "terms_present": False, "restrictive_hit": False,
                           "checked_date": date.today().isoformat()})
            print(f"  {'NO_TERMS_PAGE':>18} terms {host}")


# -------------------------------------------------------------- fetch --------
def cmd_fetch(strong_only=True):
    """Retrieve candidate documents. Hosts whose terms page came back
    restrictive are skipped and reported, never fetched."""
    blocked = _blocked_hosts()   # the same set get() enforces; see _blocked_hosts
    seen, todo = set(), []
    for r in read_all(DOCS_ALL):
        u = r["document_url"]
        if u in seen:
            continue
        seen.add(u)
        if strong_only and not r.get("strong"):
            continue
        if r.get("formish") and not r.get("strong"):
            continue
        todo.append(r)
    print(f"{len(todo)} documents queued; {len(blocked)} blocked hosts")
    out = os.path.join(SL, f"fetched{_SFX}.jsonl")
    already = set(r["document_url"] for r in read_all(os.path.join(SL, "fetched*.jsonl")))
    for r in todo:
        if r["document_url"] in already or not deadline_ok():
            continue
        host = r["host"]
        if host in blocked:
            append(out, dict(r, http_status="EXCLUDED_TERMS", raw_file=None,
                             note="terms page states a restriction; not fetched"))
            print(f"  {'EXCLUDED_TERMS':>18} {r['document_url'][:110]}")
            continue
        rec, resp = get(r["document_url"], host, "document", dict(r))
        if resp is not None and resp.status_code == 200:
            ext = ".pdf" if "pdf" in (rec["content_type"] or "") else (
                ".html" if "html" in (rec["content_type"] or "") else
                os.path.splitext(urllib.parse.urlparse(r["document_url"]).path)[1]
                or ".bin")
            rec["raw_file"] = save(resp.url, resp.content, ext)
        append(out, rec)
        print(f"  {rec['http_status']:>18} {rec.get('bytes')} "
              f"{r['document_url'][:100]}")


# ------------------------------------------------------------ harvest --------
BR = os.path.join(ROOT, "data", "staging", "business_registry")
os.makedirs(BR, exist_ok=True)

# A legal name that IS a person's name: first + last, no company suffix and no
# trade word. Flagged, never dropped - the flag is what keeps it out of clean.
_COMPANY = re.compile(
    r"\b(llc|l\.l\.c|inc|incorporated|corp|corporation|co|company|ltd|lp|llp|"
    r"enterprises?|services?|solutions?|group|holdings?|partners?|associates?|"
    r"construction|contracting|trucking|farms?|ranch|design|studio|shop|store|"
    r"kitchen|catering|consulting|cleaning|logging|lumber|works?|supply|"
    r"trading|market|salon|barber|productions?|media|creations?|photography|"
    r"institute|academy|alliance|foundation|tribe|tribal|nation|band|pueblo)\b",
    re.I)
_PERSONISH = re.compile(r"^[A-Z][a-z'\-]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z'\-]+"
                        r"(?:\s+(?:Jr|Sr|II|III|IV)\.?,?)?$")


def is_person_name(name):
    n = (name or "").strip()
    if not n or _COMPANY.search(n):
        return False
    return bool(_PERSONISH.match(n))


def norm_name(n):
    n = re.sub(r"[^a-z0-9 ]+", " ", (n or "").lower())
    n = re.sub(r"\b(llc|inc|corp|co|ltd|lp|llp|the)\b", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def emit(source_id, fname, rows, meta):
    """Write one harvest file. Owner names, phones, emails and addresses stay
    HERE, in staging, and are named in withheld_fields so the promotion step
    cannot carry them forward by accident."""
    out = os.path.join(BR, fname)
    n = 0
    with io.open(out, "w", encoding="utf-8") as f:
        for i, r in enumerate(rows, 1):
            rec = {
                # lint-ok: class7 - this is NOT an identity mint. The ordinal is
                # the position WITHIN ONE captured document and is scoped by
                # source_id; it is the key shape already in
                # data/clean/native_owned_businesses.csv (e.g. TBD-046:1), so
                # changing it here would fork the schema. Nothing resolves on
                # it: `business_entity_id` is null on every row and stays null
                # (shard L never mints or resolves identity), and the stable
                # join key is `record_hash`, taken over the row's intrinsic
                # content with the timestamps excluded.
                "business_source_id": f"{source_id}:{i}",
                "source_id": source_id,
                "source_business_key": str(i),
                "business_entity_id": None,
                "nation_id": meta["nation_id"],
                "business_name_raw": r["business_name_raw"],
                "business_name_normalized": norm_name(r["business_name_raw"]),
                "business_name_is_person_name":
                    is_person_name(r["business_name_raw"]),
                "dba_name": None,
                "owner_name_raw": r.get("owner_name_raw"),
                "owner_name_present": bool(r.get("owner_name_raw")),
                "n_owners_named": r.get("n_owners_named"),
                "directory_type": meta["directory_type"],
                "identity_scope": r.get("identity_scope", meta["identity_scope"]),
                "identity_claim_text": r.get("identity_claim_text",
                                             meta["identity_claim_text"]),
                "assertion_class": meta["assertion_class"],
                "record_scope": meta.get("record_scope", "BUSINESS"),
                "inclusion_basis": r.get("inclusion_basis",
                                         meta.get("inclusion_basis")),
                "ownership_percent": r.get("ownership_percent"),
                "ownership_threshold_min": r.get("ownership_threshold_min",
                                                 meta.get("ownership_threshold_min")),
                "control_requirement": meta.get("control_requirement"),
                "tribal_affiliation_raw": r.get("tribal_affiliation_raw"),
                "verification_basis": meta["verification_basis"],
                "certification_number": None,
                "certification_tier": r.get("certification_tier"),
                "certification_start": r.get("certification_start"),
                "certification_expiration": r.get("certification_expiration"),
                "business_license_number": r.get("business_license_number"),
                "service_category_raw": r.get("service_category_raw"),
                "naics": None,
                "description_raw": r.get("description_raw"),
                "address_raw": r.get("address_raw"),
                "city": r.get("city"), "state_province": r.get("state_province"),
                "postal_code": None,
                "phone": r.get("phone"), "email": r.get("email"),
                "website": r.get("website"),
                "federal_contract_number": None,
                "source_url": meta["source_url"],
                "source_edition": meta.get("source_edition"),
                "source_last_updated": meta.get("source_last_updated"),
                "harvest_date": date.today().isoformat(),
                "first_seen": f"{date.today().isoformat()}T00:00:00Z",
                "last_seen": f"{date.today().isoformat()}T00:00:00Z",
                "is_current": True,
                "withheld_fields": "owner_name_raw;phone;email;address_raw",
                "validation_flags": r.get("validation_flags", [])
                                    + meta.get("validation_flags", []),
                "ingestion_method": meta["ingestion_method"],
                "ocr_mean_confidence": None,
                "chars_extracted": meta.get("chars_extracted"),
                "raw_snapshot_uri": meta["raw_snapshot_uri"],
                "source_terms_status": meta["source_terms_status"],
                "source_terms_quote": meta.get("source_terms_quote"),
                "consent_status": "UNRESOLVED",
                "suppression_key": f"SUPPRESS::{meta['tribe_id']}",
                "publishable": "N",
                "refresh_run_id": "run-2026-09-01-shard-L",
                "relationship_basis_raw": r.get("relationship_basis_raw"),
                "relationship_basis": meta.get("relationship_basis",
                                               "unspecified"),
                "certification_event_status": meta.get(
                    "certification_event_status", "not_a_certification"),
                "source_priority_class": "tribal_primary",
                "cross_reference_only": False,
                "assertion_precedence_rank": 1,
                "discovery_technique": meta["discovery_technique"],
                "built_by_script": "570_shard_l_vendor_list_hunt.py",
            }
            rec["record_hash"] = "sha256:" + hashlib.sha256(
                json.dumps({k: v for k, v in rec.items()
                            if k not in ("first_seen", "last_seen",
                                         "harvest_date")},
                           sort_keys=True, default=str).encode()).hexdigest()
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    print(f"  {source_id}: {n} rows -> {fname}")
    return n


def _soup(fn):
    return __import__("bs4").BeautifulSoup(
        io.open(os.path.join(RAW, fn), encoding="utf-8", errors="ignore").read(),
        "html.parser")


def _clean(s):
    s = re.sub(r"\s+", " ", (s or "")).strip()
    return s or None


def harvest_hoopa():
    """Hoopa Valley Tribe 'Active Business License' - a tribal BUSINESS LICENCE
    register. It states NO ownership requirement, so identity_scope is
    `unknown`: the tribe licenses these firms, it does not certify them as
    Native-owned, and recording them as Native-owned would be an invention."""
    fn = "www.hoopa-nsn.gov__1acaa7fed57bd714.html"
    tbl = _soup(fn).find("table")
    rows = []
    for tr in tbl.find_all("tr"):
        c = [_clean(td.get_text(" ", strip=True))
             for td in tr.find_all("td", recursive=False)]
        if not (1 < len(c) <= 5) or (c[0] or "").startswith("Hoopa Active"):
            continue
        owner = c[2] if len(c) > 2 else None
        pct = None
        mp = re.findall(r"(\d{1,3})\s*%", owner or "")
        if mp:
            pct = float(mp[0])
        rows.append({"business_name_raw": c[0],
                     "service_category_raw": c[1] if len(c) > 1 else None,
                     "owner_name_raw": owner,
                     "n_owners_named": (len(re.split(r"[,&]| and ", owner))
                                        if owner else 0),
                     "ownership_percent": pct,
                     "phone": c[3] if len(c) > 3 else None,
                     "validation_flags": (["ownership_split_stated_in_owner_field"]
                                          if pct else [])})
    return emit("TBD-L01", "TBD-L01_hoopa_valley_active_business_licence.jsonl", rows, {
        "tribe_id": "TRBF-HOOPAV-00", "nation_id": "bia:hoopa-valley-tribe",
        "directory_type": "business_licence", "identity_scope": "unknown",
        "identity_claim_text":
            "Hoopa Valley Tribe Business Licenses - 'Hoopa Active Business "
            "Names'. The register states NO ownership threshold, NO tribal "
            "membership requirement and NO certification. It is the Tribe's "
            "list of businesses holding an active licence on its reservation; "
            "it is NOT an assertion that the firms are Native-owned.",
        "assertion_class": "LICENCE", "verification_basis": "tribal_licence_issued",
        "relationship_basis": "licensed_by_tribe",
        "source_url": "https://www.hoopa-nsn.gov/active-business-license/",
        "ingestion_method": "html_table",
        "raw_snapshot_uri": f"tribe_harvest/shard_l/raw/{fn}",
        "source_terms_status": "SILENT",
        "validation_flags": ["owner_personal_names_present_staging_only"],
        "discovery_technique":
            "docs/HIDDEN_DATA_TECHNIQUES.md #3 - WordPress REST "
            "/wp/v2/pages?search=business surfaced /active-business-license/, "
            "which is not in the site navigation"})


def harvest_badriver():
    """Bad River 'Business Directory' - TWO tables, and they are NOT the same
    claim: table 1 is 'Tribal Owned Businesses', table 2 is area businesses.
    Flattening them would turn local non-Native firms into Native-owned ones."""
    fn = "www.badriver-nsn.gov__b7cf0cc773a33c84.html"
    s = _soup(fn)
    tbls = s.find_all("table")
    heads = [_clean(h.get_text(" ", strip=True))
             for h in s.find_all(["h1", "h2", "h3", "h4"])]
    rows = []
    for ti, tbl in enumerate(tbls):
        tribal = (ti == 0)
        for tr in tbl.find_all("tr"):
            c = [_clean(td.get_text(" ", strip=True)) for td in tr.find_all("td")]
            c = [x for x in c if x is not None] or []
            if len(c) < 2 or c[0] == "Business Name":
                continue
            desc = c[1] if len(c) > 1 else None
            owner = None
            mo = re.match(r"Owner:\s*(.+)$", desc or "")
            if mo:
                owner, desc = mo.group(1), None
            rows.append({
                "business_name_raw": c[0], "description_raw": desc,
                "address_raw": c[2] if len(c) > 2 else None,
                "phone": c[3] if len(c) > 3 else None,
                "website": c[4] if len(c) > 4 and c[4] != "N/A" else None,
                "email": c[5] if len(c) > 5 else None,
                "owner_name_raw": owner,
                "n_owners_named": 1 if owner else 0,
                "identity_scope": "citizen" if tribal else "vendor_relationship",
                "inclusion_basis": ("listed under the heading 'Tribal Owned "
                                    "Businesses'" if tribal else
                                    "listed under the directory's SECOND table, "
                                    "the area/local business section - NOT under "
                                    "'Tribal Owned Businesses'"),
                "identity_claim_text":
                    "Bad River Band 'Business Directory - Tribal Owned and Local "
                    "Businesses', published by its Sustainable Business Program. "
                    "The page carries TWO separate tables. Section: " +
                    ("TRIBAL OWNED BUSINESSES." if tribal else
                     "LOCAL/AREA BUSINESSES - this section asserts NO tribal "
                     "ownership and its rows must never be read as Native-owned."),
                "validation_flags": ([] if tribal else
                                     ["local_section_not_a_native_ownership_claim"])})
    return emit("TBD-L02", "TBD-L02_bad_river_business_directory.jsonl", rows, {
        "tribe_id": "TRBF-BADRVR-00", "nation_id": "bia:bad-river-band",
        "directory_type": "vendor_list", "identity_scope": "mixed",
        "identity_claim_text": "see per-row identity_claim_text",
        "assertion_class": "OWNERSHIP",
        "verification_basis": "self_reported_to_tribal_programme",
        "source_url": "https://www.badriver-nsn.gov/business-directory/",
        "ingestion_method": "html_table",
        "raw_snapshot_uri": f"tribe_harvest/shard_l/raw/{fn}",
        "source_terms_status": "NO_TERMS_PAGE_SERVED",
        "validation_flags": ["two_sections_with_different_claims_not_flattened"],
        "discovery_technique":
            "docs/HIDDEN_DATA_TECHNIQUES.md #3 - WordPress REST "
            "/wp/v2/pages?search=business"})


def _para_blocks(container):
    """LTBB and Aquinnah both render each firm as <p><strong>Name</strong></p>
    followed by unlabelled <p> lines. Group on the bold line."""
    out, cur = [], None
    for p in container.find_all("p"):
        b = p.find(["strong", "b"])
        txt = _clean(p.get_text(" ", strip=True))
        if not txt:
            continue
        if b and _clean(b.get_text(" ", strip=True)) == txt:
            if cur:
                out.append(cur)
            cur = {"name": txt, "lines": [],
                   "links": [a.get("href") for a in p.find_all("a")]}
        elif cur is not None:
            cur["lines"].append(txt)
            cur["links"] += [a.get("href") for a in p.find_all("a")]
    if cur:
        out.append(cur)
    return out


_CITYST = re.compile(r"^(.+?),\s*([A-Z]{2})$")
_PHONE = re.compile(r"^[\d\-\(\)\s\.\+xX]{7,}$|^1-\d{3}-\w+$")
_EMAIL = re.compile(r"[\w\.\-\+]+@[\w\.\-]+\.\w+")


def _fields_from_lines(lines):
    d = {"service_category_raw": None, "city": None, "state_province": None,
         "phone": None, "email": None, "website": None, "description_raw": None}
    for ln in lines:
        if _EMAIL.search(ln) and not d["email"]:
            d["email"] = _EMAIL.search(ln).group(0); continue
        m = _CITYST.match(ln)
        if m and not d["city"]:
            d["city"], d["state_province"] = m.group(1), m.group(2); continue
        if _PHONE.match(ln) and not d["phone"]:
            d["phone"] = ln; continue
        if re.match(r"^(https?://|www\.)", ln) and not d["website"]:
            d["website"] = ln; continue
        if not d["service_category_raw"]:
            d["service_category_raw"] = ln
        elif not d["description_raw"]:
            d["description_raw"] = ln
    return d


def harvest_ltbb():
    fn = "ltbbodawa-nsn.gov__b922e76a2902b504.html"
    s = _soup(fn)
    rows, cat = [], None
    for el in s.find_all(["h3", "div"]):
        if el.name == "h3":
            t = _clean(el.get_text(" ", strip=True))
            if t and "Directory" not in t:
                cat = t
            continue
        if "wpb_wrapper" not in (el.get("class") or []):
            continue
        for blk in _para_blocks(el):
            if not blk["lines"]:
                continue
            f = _fields_from_lines(blk["lines"])
            rows.append(dict(business_name_raw=blk["name"],
                             tribal_affiliation_raw=cat, **f))
    seen, ded = set(), []
    for r in rows:
        k = (r["business_name_raw"], r["service_category_raw"])
        if k in seen:
            continue
        seen.add(k); ded.append(r)
    return emit("TBD-L03", "TBD-L03_ltbb_tribal_citizen_owned_business_directory.jsonl",
                ded, {
        "tribe_id": "TRBF-LTRVRS-00",
        "nation_id": "bia:little-traverse-bay-bands-odawa",
        "directory_type": "vendor_list", "identity_scope": "citizen",
        "identity_claim_text":
            "'LTBB Tribal Citizen-owned Business Directory', published by the "
            "Little Traverse Bay Bands of Odawa Indians Department of Commerce. "
            "The directory's own title states the scope: businesses owned by "
            "LTBB TRIBAL CITIZENS. No ownership percentage and no certification "
            "or expiry is published, so this is a citizen-ownership assertion, "
            "not a certification.",
        "assertion_class": "OWNERSHIP",
        "verification_basis": "self_reported_to_tribal_department",
        "source_url": "https://ltbbodawa-nsn.gov/departments/department-of-"
                      "commerce/ltbb-tribal-citizen-owned-business-directory/",
        "ingestion_method": "html_paragraph_blocks",
        "raw_snapshot_uri": f"tribe_harvest/shard_l/raw/{fn}",
        "source_terms_status": "NO_TERMS_PAGE_SERVED",
        "validation_flags": ["no_ownership_percent_published",
                             "no_certification_or_expiry_published"],
        "discovery_technique":
            "docs/HIDDEN_DATA_TECHNIQUES.md #3 - WordPress REST "
            "/wp/v2/pages?search=business"})


def harvest_aquinnah():
    fn = "wampanoagtribe-nsn.gov__a9299ef702b196fc.html"
    s = _soup(fn)
    rows, cat = [], None
    for el in s.find_all(["h1", "h2", "h3", "h4", "div"]):
        if el.name in ("h1", "h2", "h3", "h4"):
            t = _clean(el.get_text(" ", strip=True))
            if t and "Business Directory" not in t and len(t) < 60:
                cat = t
            continue
        if "sqs-html-content" not in (el.get("class") or []):
            continue
        for p in el.find_all("p"):
            b = p.find(["strong", "b"])
            if not b:
                continue
            name = _clean(b.get_text(" ", strip=True))
            if not name or len(name) > 120:
                continue
            parts = [_clean(x) for x in p.get_text("\n", strip=True).split("\n")]
            parts = [x for x in parts if x and x != name]
            f = _fields_from_lines(parts)
            a = p.find("a")
            if a and a.get("href", "").startswith("http") and not f["website"]:
                f["website"] = a["href"]
            rows.append(dict(business_name_raw=name,
                             tribal_affiliation_raw=cat, **f))
    seen, ded = set(), []
    for r in rows:
        if r["business_name_raw"] in seen:
            continue
        seen.add(r["business_name_raw"]); ded.append(r)
    return emit("TBD-L04", "TBD-L04_aquinnah_wampanoag_business_listing.jsonl",
                ded, {
        "tribe_id": "TRBF-AQNNAH-00", "nation_id": "bia:wampanoag-gay-head-aquinnah",
        "directory_type": "vendor_list",
        # The tribe's own wording is "individuals OR THEIR FAMILIES", which is
        # the member-or-relative claim, not a member-ownership claim. Vocabulary
        # borrowed from data/clean/native_owned_businesses.csv, where this value
        # already carries exactly that meaning (Calista: "Shareholders,
        # Descendants and their spouses"). See validation_flags.
        "identity_scope": "shareholder_descendant_or_spouse",
        "identity_claim_text":
            "Wampanoag Tribe of Gay Head (Aquinnah) 'Business Directory': "
            "\"This is a listing of businesses owned by Aquinnah Wampanoag "
            "individuals or their families. This is presented as a service to "
            "the Tribe's citizens and those that may wish to connect with them, "
            "but is not an endorsement of any particular business.\" The scope "
            "is CITIZEN OR FAMILY MEMBER - weaker than citizen-owned, and the "
            "Tribe explicitly disclaims endorsement.",
        "assertion_class": "OWNERSHIP", "verification_basis": "self_submitted",
        "relationship_basis": "self_submitted_to_planning_department",
        "source_url": "https://wampanoagtribe-nsn.gov/business-listing",
        "ingestion_method": "html_paragraph_blocks",
        "raw_snapshot_uri": f"tribe_harvest/shard_l/raw/{fn}",
        "source_terms_status": "NO_TERMS_PAGE_SERVED",
        "validation_flags": [
            "identity_scope_vocabulary_borrowed:the tribe says 'individuals or "
            "their families', not shareholders; the value is reused because it "
            "is the existing vocabulary point for member-or-relative and carries "
            "the right warning, and a family-owned firm is NOT a Native-owned firm",
            "tribe_disclaims_endorsement",
            "self_submitted_no_verification_stated"],
        "discovery_technique":
            "WebSearch discovery of the tribal government site, then the "
            "published /business-listing page"})


def harvest_delaware():
    """WordPress CUSTOM POST TYPE `tribalbusiness` - a tribal enterprise
    register that exists only as a CPT endpoint (HIDDEN_DATA #3)."""
    fn, data = None, None
    for f in sorted(os.listdir(RAW)):
        if not (f.startswith("delawaretribe.org__") and f.endswith(".json")):
            continue
        try:
            d = json.load(io.open(os.path.join(RAW, f), encoding="utf-8"))
        except Exception:
            continue
        if isinstance(d, list) and d and isinstance(d[0], dict) and "title" in d[0]:
            fn, data = f, d
            break
    if data is None:
        print("  TBD-L05: CPT json not on disk"); return 0
    fn = [fn]
    rows = []
    for it in data:
        nm = _clean(re.sub(r"<[^>]+>", " ",
                           (it.get("title") or {}).get("rendered") or ""))
        if not nm:
            continue
        desc = _clean(re.sub(r"<[^>]+>", " ",
                             (it.get("excerpt") or {}).get("rendered") or ""))
        rows.append({"business_name_raw": nm, "description_raw": desc,
                     "website": it.get("link"),
                     "source_last_updated": it.get("modified")})
    return emit("TBD-L05", "TBD-L05_delaware_tribe_tribal_business_register.jsonl",
                rows, {
        "tribe_id": "TRBF-DELAWT-00", "nation_id": "bia:delaware-tribe-of-indians",
        "directory_type": "subsidiary_directory",
        "identity_scope": "tribally_owned_entity",
        "identity_claim_text":
            "Delaware Tribe of Indians publishes these as its own tribal "
            "businesses, in a WordPress custom post type named "
            "'tribalbusiness'. The Tribe asserts them as tribal enterprises; "
            "no ownership percentage is stated because the asserted owner is "
            "the Tribe itself.",
        "assertion_class": "OWNERSHIP", "verification_basis": "publisher_is_the_tribe",
        "relationship_basis": "tribally_owned",
        "source_url": "https://delawaretribe.org/wp-json/wp/v2/tribalbusiness"
                      "?per_page=100",
        "ingestion_method": "wp_rest_custom_post_type",
        "raw_snapshot_uri": f"tribe_harvest/shard_l/raw/{fn[0]}",
        "source_terms_status": "TERMS_STATED_COPYRIGHT_ONLY",
        "source_terms_quote":
            "Official Site of the Delaware Tribe of Indians, All Rights "
            "Reserved (copyright notice only; no scraping, reuse or automated-"
            "access restriction stated on /copyright-notice/ or /privacy-policy/)",
        "validation_flags": ["small_register_n_lt_10"],
        "discovery_technique":
            "docs/HIDDEN_DATA_TECHNIQUES.md #3 - /wp-json/wp/v2/types revealed "
            "a custom post type 'tribalbusiness'; the register exists ONLY as "
            "that CPT endpoint and is not a page on the site"})


def harvest_cvmt():
    fn = "californiavalleymiwok.us__76d55c736d6670b0.html"
    s = _soup(fn)
    txt = re.sub(r"\s+", " ", s.get_text(" ", strip=True))
    rows = []
    for nm in ["MIWOK Global Inc", "MIWOK Construction LLC", "FAR Solutions LLC"]:
        if nm.split()[0].lower() in txt.lower():
            rows.append({"business_name_raw": nm})
    return emit("TBD-L06", "TBD-L06_california_valley_miwok_sba_8a_enterprises.jsonl",
                rows, {
        "tribe_id": "TRBF-CAVLLY-00", "nation_id": "bia:california-valley-miwok",
        "directory_type": "subsidiary_directory",
        "identity_scope": "tribally_owned_entity",
        "identity_claim_text":
            "California Valley Miwok Tribe /sba-8a/ page names its own tribally "
            "owned operating companies under the SBA 8(a) programme. This is a "
            "TRIBAL ENTERPRISE REGISTER of three firms, not an open vendor "
            "directory: no outside business can appear on it.",
        "assertion_class": "OWNERSHIP", "verification_basis": "publisher_is_the_tribe",
        "relationship_basis": "tribally_owned",
        "source_url": "https://californiavalleymiwok.us/sba-8a/",
        "ingestion_method": "html_text",
        "raw_snapshot_uri": f"tribe_harvest/shard_l/raw/{fn}",
        "source_terms_status": "TERMS_STATED_COPYRIGHT_ONLY",
        "source_terms_quote":
            "(c) 2001-2026 California Valley Miwok Tribe. All Rights Reserved "
            "(copyright only; /legal/ states no reuse or scraping restriction)",
        "validation_flags": ["small_register_n_lt_10",
                             "closed_register_not_an_open_vendor_directory"],
        "discovery_technique":
            "WebSearch discovery of the tribal government site, then its "
            "published /sba-8a/ page"})


def harvest_chehalis():
    """Chehalis Tribal Enterprises names its family of enterprises in prose.
    Two of them are PASSIVE INVESTMENT HOLDINGS, which is a different claim
    from an operated tribal enterprise and is kept separate."""
    fn = "www.chehalistribe.org__410c38f769c23000.html"
    body = _soup(fn).get_text(" ", strip=True)
    operated = ["End of The Trail Convenience Stores",
                "Confederated Construction Company",
                "Talking Cedar Brewery & Distillery", "Talking Cedar Restaurant",
                "Oaksridge Golf Course", "Black River Blues Blueberry Farm",
                "Soaring Eagle Distribution", "Chehalis Tobacco Products"]
    passive = ["Flying J Travel Center", "Fairfield Inn & Suites by Marriott"]
    rows = []
    for nm in operated + passive:
        probe = nm.split(" &")[0].split(" by ")[0]
        if probe.lower() not in body.lower():
            continue
        is_p = nm in passive
        rows.append({
            "business_name_raw": nm,
            "identity_scope": "tribally_owned_entity",
            "relationship_basis_raw": ("passive investment holding"
                                       if is_p else "managed enterprise"),
            "inclusion_basis": ("named on the page as a PASSIVE INVESTMENT "
                                "HOLDING of Chehalis Tribal Enterprises"
                                if is_p else
                                "named on the page as an enterprise actively "
                                "managed by Chehalis Tribal Enterprises"),
            "validation_flags": (["passive_investment_not_an_operated_enterprise"]
                                 if is_p else [])})
    return emit("TBD-L07", "TBD-L07_chehalis_tribal_enterprises.jsonl", rows, {
        "tribe_id": "TRBF-CHEHLS-00", "nation_id": "bia:confederated-chehalis",
        "directory_type": "subsidiary_directory",
        "identity_scope": "tribally_owned_entity",
        "identity_claim_text":
            "\"Chehalis Tribal Enterprises (CTE), the enterprise arm of The "
            "Confederated Tribes of the Chehalis Reservation, actively manages "
            "a family of tribal business enterprises...\" CTE also states "
            "PASSIVE INVESTMENT HOLDINGS, which are a weaker claim than an "
            "operated enterprise and are flagged per row.",
        "assertion_class": "OWNERSHIP", "verification_basis": "publisher_is_the_tribe",
        "relationship_basis": "tribally_owned",
        "source_url": "https://www.chehalistribe.org/businesses/"
                      "chehalis-tribal-enterprises/",
        "ingestion_method": "html_prose_named_entities",
        "raw_snapshot_uri": f"tribe_harvest/shard_l/raw/{fn}",
        "source_terms_status": "TERMS_STATED_COPYRIGHT_ONLY",
        "source_terms_quote":
            "Copyright (c) 2023 The Chehalis Tribe All Rights Reserved "
            "(/terms-of-use/ states no reuse, scraping or automated-access "
            "restriction)",
        "validation_flags": ["enterprise_names_extracted_from_prose_not_a_table"],
        "discovery_technique":
            "docs/HIDDEN_DATA_TECHNIQUES.md #3 - WordPress REST "
            "/wp/v2/pages?search=business"})


def harvest_citizen_potawatomi():
    """Citizen Potawatomi Nation publishes its tribal enterprises as a
    WordPress CUSTOM POST TYPE named `enterprise`. It is not a page and no
    navigation link reaches the endpoint (HIDDEN_DATA #3)."""
    fn, data = None, None
    for f in sorted(os.listdir(RAW)):
        if not (f.startswith("www.potawatomi.org__") and f.endswith(".json")):
            continue
        try:
            d = json.load(io.open(os.path.join(RAW, f), encoding="utf-8"))
        except Exception:
            continue
        if isinstance(d, list) and d and isinstance(d[0], dict) \
                and d[0].get("type") == "enterprise":
            fn, data = f, d
            break
    if data is None:
        print("  TBD-L08: enterprise CPT json not on disk")
        return 0
    rows = []
    for it in data:
        nm = _clean(re.sub(r"<[^>]+>", " ",
                           (it.get("title") or {}).get("rendered") or ""))
        nm = (nm or "").replace("&#038;", "&").replace("&amp;", "&")
        if not nm:
            continue
        rows.append({"business_name_raw": nm,
                     "website": it.get("link"),
                     "service_category_raw": ";".join(
                         str(x) for x in (it.get("enterprise_category") or []))
                         or None,
                     "source_last_updated": it.get("modified")})
    return emit("TBD-L08",
                "TBD-L08_citizen_potawatomi_enterprise_register.jsonl", rows, {
        "tribe_id": "TRBF-CITIZN-00", "nation_id": "bia:citizen-potawatomi-nation",
        "directory_type": "subsidiary_directory",
        "identity_scope": "tribally_owned_entity",
        "identity_claim_text":
            "Citizen Potawatomi Nation publishes these as its own tribal "
            "enterprises, in a WordPress custom post type named 'enterprise'. "
            "The asserted owner is the Nation itself, so no ownership "
            "percentage is stated. This is a TRIBAL ENTERPRISE REGISTER, not "
            "an open vendor directory: no outside firm can appear on it.",
        "assertion_class": "OWNERSHIP",
        "verification_basis": "publisher_is_the_tribe",
        "relationship_basis": "tribally_owned",
        "source_url": "https://www.potawatomi.org/wp-json/wp/v2/enterprise"
                      "?per_page=100",
        "ingestion_method": "wp_rest_custom_post_type",
        "raw_snapshot_uri": f"tribe_harvest/shard_l/raw/{fn}",
        "source_terms_status": "SILENT",
        "validation_flags": ["closed_register_not_an_open_vendor_directory"],
        "discovery_technique":
            "docs/HIDDEN_DATA_TECHNIQUES.md #3 - /wp-json/wp/v2/types revealed "
            "a custom post type 'enterprise'; the register exists only as that "
            "endpoint"})


def harvest_shoshone_bannock():
    """Shoshone-Bannock Tribes 'TERO Certified Indian Preference Business
    Directory', Issue Date September 2022. Found ONLY through the WordPress
    media index: nothing on the site links it, and four editions of it
    (Mar 2021, Jun 2021, Jun 2022, Sep 2022) sit in the media library."""
    import pdfplumber
    fn = "www.sbtribes.com__d9db8c89abe591f4.pdf"
    path = os.path.join(RAW, fn)
    text, npages = "", 0
    with pdfplumber.open(path) as pdf:
        npages = len(pdf.pages)
        for pg in pdf.pages:
            text += (pg.extract_text() or "") + "\n"
    chars = len(text)
    if chars < 200:
        print(f"  TBD-L09: CAPTURED_NOT_PARSED - {npages} pages, {chars} chars "
              f"extracted; no text layer and no OCR available")
        return 0
    text = text.replace("\u2010", "-")
    lines = [l.rstrip() for l in text.split("\n")]
    CATS = {"CONSTRUCTION", "SERVICES", "SUPPLIES", "PROFESSIONAL SERVICES",
            "TRANSPORTATION", "OTHER", "CONSULTING", "SUPPLIERS"}
    SKIP = re.compile(r"^(The Shoshone|Issue Date|P\.O\. Box 306|Phone: \(208\)|"
                      r"Email: tero@|All previous|TERO Certified|"
                      r"Indian Preference Business|Fort Hall, Idaho)")
    keep = [l.strip() for l in lines
            if l.strip() and not l.strip().isdigit() and not SKIP.match(l.strip())]
    # A firm-name line is the line IMMEDIATELY BEFORE an owner line. That is
    # structural, not typographic: keying on ALL-CAPS alone drops
    # 'RTHawk Housing Alliance, LLC'.
    rows, cur, cat, expect_name = [], None, None, True
    for t in keep:
        if t.upper() in CATS:
            cat = t.upper()
            expect_name = True
            continue
        if t.startswith("Certification Expires:"):
            if cur:
                cur["certification_expiration"] = t.split(":", 1)[1].strip()
            expect_name = True          # the record just ended
            continue
        if expect_name:
            cur = {"business_name_raw": t, "service_category_raw": cat,
                   "_lines": [], "certification_expiration": None}
            rows.append(cur)
            expect_name = False
            continue
        if cur is not None:
            cur["_lines"].append(t)
    out = []
    for r in rows:
        ls = r.pop("_lines", [])
        r.pop("_closed", None)
        owner, affil, addr, phone, email, desc = None, None, None, None, None, []
        for i, ln in enumerate(ls):
            if _EMAIL.search(ln) and not email:
                email = _EMAIL.search(ln).group(0)
                continue
            if re.match(r"^[\(\d][\d\s\-\.\(\)]{7,}$", ln) and not phone:
                phone = ln
                continue
            if i == 0 and ("Owner" in ln or "," in ln):
                owner = ln
                mo = re.search(r"Owner,\s*(.+)$", ln)
                affil = (mo.group(1).strip() if mo else
                         (ln.split(",", 1)[1].strip() if "," in ln else None))
                continue
            if re.search(r"\b[A-Z]{2}\s+\d{5}\b|PO Box|P\.O\. Box", ln) and not addr:
                addr = ln
                continue
            desc.append(ln)
        n_owners = (len(re.findall(r"Owner", owner)) if owner else 0) or \
                   (1 if owner else 0)
        out.append({
            "business_name_raw": r["business_name_raw"],
            "service_category_raw": r["service_category_raw"],
            "owner_name_raw": owner, "n_owners_named": n_owners,
            "tribal_affiliation_raw": affil,
            "address_raw": addr, "phone": phone, "email": email,
            "description_raw": " ".join(desc)[:600] or None,
            "certification_expiration": r.get("certification_expiration"),
            # No affiliation printed means the row's claim is not stated -
            # defaulting it to `citizen` would invent a Shoshone-Bannock
            # membership the document does not assert.
            "identity_scope": ("unknown" if not affil else
                               ("citizen" if "shoshone" in affil.lower()
                                else "enrolled_member_other_federally_recognized")),
            "inclusion_basis":
                "TERO-certified Indian preference firm; the directory names the "
                "owner's tribe per row, so a Shoshone-Bannock owner and an "
                "owner enrolled elsewhere are recorded as different claims",
            "validation_flags": (["certification_expired_before_capture"]
                                 if (r.get("certification_expiration") or "")
                                 .endswith("2022") else [])})
    return emit("TBD-L09",
                "TBD-L09_shoshone_bannock_tero_indian_preference_directory.jsonl",
                out, {
        "tribe_id": "TRBF-FTHALL-00", "nation_id": "bia:shoshone-bannock-tribes",
        "directory_type": "tero", "identity_scope": "mixed",
        "identity_claim_text":
            "'The Shoshone-Bannock Tribes TERO Certified Indian Preference "
            "Business Directory', Issue Date September 2022, which states on "
            "its own cover: 'All previous directories are obsolete!' Every row "
            "carries the owner's name, the owner's TRIBE, and a certification "
            "expiry date. Owners are enrolled in several different nations "
            "(Shoshone-Bannock, Chippewa Cree, Sault Ste Marie Chippewa, "
            "Paiute, Pokagon Band of Potawatomi), so the list is NOT a "
            "single-nation membership claim.",
        "assertion_class": "OWNERSHIP", "verification_basis": "TERO_certification",
        "relationship_basis": "tero_certified",
        "certification_event_status": "approved",
        "source_url": "https://www.sbtribes.com/wp-content/uploads/2022/09/"
                      "September-2022-TERO-Indian-Preference-Business-Directory.pdf",
        "source_edition": "September 2022",
        "source_last_updated": "2022-09-13",
        "ingestion_method": "pdf_text_layer",
        "chars_extracted": chars,
        "raw_snapshot_uri": f"tribe_harvest/shard_l/raw/{fn}",
        "source_terms_status": "SILENT",
        "validation_flags": [
            "edition_is_2022_and_the_tribe_says_previous_editions_are_obsolete:"
            "this is the LATEST edition published, not a current-as-of-2026 list",
            "owner_personal_names_present_staging_only",
            f"pdf_text_layer_{chars}_chars_from_{npages}_pages"],
        "discovery_technique":
            "docs/HIDDEN_DATA_TECHNIQUES.md #3 - WordPress REST /wp/v2/media "
            "UNFILTERED; the directory is linked from nothing on the site and "
            "four editions of it sit in the media library"})


def harvest_chitimacha():
    """Chitimacha Tribe of Louisiana publishes one page per tribal enterprise
    under /tribal-enterprises/. The set is enumerable only from the site's own
    sitemap - the index page renders the nav, not the list."""
    urls, host = set(), "chitimacha.gov"
    for d in read_all(DOCS_ALL):
        u = d.get("document_url") or ""
        if "chitimacha.gov/tribal-enterprises/" in u:
            urls.add(u.split("://", 1)[1].split("#")[0])
    rows = []
    for u in sorted(urls):
        slug = u.rstrip("/").rsplit("/", 1)[-1]
        nm = " ".join(w.upper() if w.lower() in ("llc",) else w.capitalize()
                      for w in slug.replace("-", " ").split())
        rows.append({"business_name_raw": nm,
                     "website": "https://" + u,
                     "inclusion_basis": "published as its own page under "
                                        "/tribal-enterprises/ on the Tribe's "
                                        "government site",
                     "validation_flags":
                         ["name_derived_from_published_page_slug:the slug is "
                          "the Tribe's own, but it is not the firm's legal name"]})
    if not rows:
        print("  TBD-L10: no chitimacha enterprise URLs on disk")
        return 0
    return emit("TBD-L10", "TBD-L10_chitimacha_tribal_enterprises.jsonl", rows, {
        "tribe_id": "TRBF-CHTMCH-00", "nation_id": "bia:chitimacha-tribe-of-louisiana",
        "directory_type": "subsidiary_directory",
        "identity_scope": "tribally_owned_entity",
        "identity_claim_text":
            "Chitimacha Tribe of Louisiana publishes these as its own Tribal "
            "Enterprises, one page each under /tribal-enterprises/. The "
            "asserted owner is the Tribe, so no ownership percentage is "
            "stated. This is a closed tribal enterprise register, not an open "
            "vendor directory.",
        "assertion_class": "OWNERSHIP", "verification_basis": "publisher_is_the_tribe",
        "relationship_basis": "tribally_owned",
        "source_url": "https://chitimacha.gov/tribal-enterprises",
        "ingestion_method": "sitemap_enumeration",
        "raw_snapshot_uri": "tribe_harvest/shard_l/raw/ (sitemap + index page)",
        "source_terms_status": "NOT_CHECKED",
        "validation_flags": ["closed_register_not_an_open_vendor_directory",
                             "names_taken_from_page_slugs_not_legal_names"],
        "discovery_technique":
            "docs/HIDDEN_DATA_TECHNIQUES.md #4 - the site publishes no REST "
            "API; its sitemap enumerates one page per enterprise while the "
            "index page renders only navigation"})


def harvest_kalispel():
    fn = "kalispeltribe.com__34f7fbe59e21c41e.html"
    body = _soup(fn).get_text(" ", strip=True)
    # The page's nav mixes enterprises with government bodies. The Tribal
    # Court and the Natural Resources Department are government functions, not
    # businesses, and are excluded rather than counted as enterprises.
    names = ["Camas Center Clinic", "Camas Center", "Camas Path",
             "Kalispel Utilities", "Northern Quest", "Kalispel Casino",
             "Kalispel RV Park", "Kalispel Fresh Market", "Kalispel Storage",
             "Kalispel Auto Sales", "Kalispel Tribal Economic Authority",
             "Camas Foundation"]
    rows = [{"business_name_raw": n,
             "inclusion_basis": "named on the Tribe's own /our-enterprises page"}
            for n in names
            if n.replace(" ", "").lower() in body.replace(" ", "").lower()]
    return emit("TBD-L11", "TBD-L11_kalispel_tribal_enterprises.jsonl", rows, {
        "tribe_id": "TRBF-KALSPL-00", "nation_id": "bia:kalispel-tribe",
        "directory_type": "subsidiary_directory",
        "identity_scope": "tribally_owned_entity",
        "identity_claim_text":
            "\"The Kalispel Tribe owns and operates more than a dozen "
            "businesses and enterprises in and around the Pend Oreille area.\" "
            "The /our-enterprises page names them. Closed tribal enterprise "
            "register, not an open vendor directory.",
        "assertion_class": "OWNERSHIP", "verification_basis": "publisher_is_the_tribe",
        "relationship_basis": "tribally_owned",
        "source_url": "https://kalispeltribe.com/our-enterprises",
        "ingestion_method": "html_named_entities",
        "raw_snapshot_uri": f"tribe_harvest/shard_l/raw/{fn}",
        "source_terms_status": "NOT_CHECKED",
        "validation_flags": [
            "closed_register_not_an_open_vendor_directory",
            "the_page_says_more_than_a_dozen_and_names_them_by_website_so_the_"
            "count_here_may_undercount_unnamed_enterprises"],
        "discovery_technique":
            "docs/HIDDEN_DATA_TECHNIQUES.md #4 - sitemap of a non-WordPress "
            "host surfaced /our-enterprises"})


def cmd_harvest(which=None):
    fns = {"hoopa": harvest_hoopa, "badriver": harvest_badriver,
           "ltbb": harvest_ltbb, "aquinnah": harvest_aquinnah,
           "delaware": harvest_delaware, "cvmt": harvest_cvmt,
           "chehalis": harvest_chehalis,
           "cpn": harvest_citizen_potawatomi,
           "sbt": harvest_shoshone_bannock,
           "chitimacha": harvest_chitimacha,
           "kalispel": harvest_kalispel}
    total = 0
    for k, fn in fns.items():
        if which and k != which:
            continue
        try:
            total += fn() or 0
        except Exception as e:
            print(f"  {k}: FAILED {type(e).__name__}: {e}")
    print("total harvested rows:", total)


# ----------------------------------------------------------- registry --------
VERDICTS = os.path.join(SL, "_verdicts.jsonl")
POP_BASIS = "shard_l_frt_unchecked_half1"


def slugify(name):
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return s


# ------------------------------------------------------- identifiers --------
# An identifier beats every name method there is. Shard E linked seven ASRC
# Federal operating companies - $5.43B - through CAGE codes on the parent's own
# site; not one of those legal names shares a token with "Arctic Slope".
FPDS_MAP = os.path.join(ROOT, "data", "clean", "fpds_uei_cage_map.csv")
ID_PATHS = ["", "/capabilities/", "/capability-statement/", "/capabilities",
            "/about/", "/about-us/", "/government/", "/contracting/",
            "/certifications/", "/gov/"]
# UEI: 12 alphanumeric, no I and no O, and never all digits.
RE_UEI = re.compile(r"\b(?:UEI|Unique Entity ID(?:entifier)?)\D{0,20}"
                    r"([A-HJ-NP-Z0-9]{12})\b", re.I)
RE_CAGE = re.compile(r"\bCAGE(?:\s*(?:code|#|no\.?))?\D{0,12}([0-9A-Z]{5})\b", re.I)
RE_DUNS = re.compile(r"\bDUNS(?:\s*(?:number|#|no\.?))?\D{0,12}"
                     r"(\d{2}-?\d{3}-?\d{4}|\d{9})\b", re.I)
RE_EIN = re.compile(r"\b(?:EIN|Employer Identification (?:Number|No\.?))"
                    r"\D{0,12}(\d{2}-\d{7})\b", re.I)
RE_NAICS = re.compile(r"\bNAICS\D{0,20}((?:\d{6}[,;/\s]{0,3}){1,20})", re.I)
RE_SAM = re.compile(r"([^.]{0,120}\bSAM(?:\.gov)?\b[^.]{0,160}\.)", re.I)


def _idhits(text, url):
    out = []
    flat = re.sub(r"\s+", " ", text)
    for kind, rx in (("UEI", RE_UEI), ("CAGE", RE_CAGE), ("DUNS", RE_DUNS),
                     ("EIN", RE_EIN), ("NAICS", RE_NAICS)):
        for m in rx.finditer(flat):
            v = m.group(1).strip()
            if kind == "UEI" and v.isdigit():
                continue            # 12 digits is not a UEI
            i = max(0, m.start() - 90)
            out.append({"identifier_type": kind,
                        "identifier_value": v.replace("-", "")
                                            if kind == "DUNS" else v,
                        "source_url": url,
                        "quote": flat[i:m.end() + 90].strip()[:300]})
    m = RE_SAM.search(flat)
    if m:
        out.append({"identifier_type": "SAM_REGISTRATION_STATEMENT",
                    "identifier_value": None, "source_url": url,
                    "quote": m.group(1).strip()[:300]})
    return out


def cmd_sitefallback(shard=None):
    """The machine-readable bar for a host with NO WordPress REST API.

    There is no media index to enumerate, so the equivalent evidence is: the
    sitemap the site itself publishes (found at /sitemap.xml, /sitemap_index.xml
    or named in robots.txt), plus a link scan of the homepage. Without at least
    one of those the verdict stays NOT_SEARCHED_MACHINE_READABLE."""
    tg = json.load(io.open(TARGETS, encoding="utf-8"))
    host_owner = {}
    for o in tg:
        for h in o["hosts"]:
            host_owner.setdefault(h, o)
    probes = list(read_all(PROBE_ALL))
    by_host = {}
    for r in probes:
        by_host.setdefault(r["host"], []).append(r)
    todo = []
    for h, rs in by_host.items():
        if h not in host_owner:
            continue
        wp = any(r["kind"].startswith("wp_types") and r["http_status"] == "200"
                 and (r.get("post_types") or r.get("cpt_rest_bases")) for r in rs)
        sm = any(r["kind"].startswith("sitemap") and r["http_status"] == "200"
                 for r in rs)
        refused = any(r["http_status"] in ("ROBOTS_DISALLOW", "EXCLUDED_TERMS")
                      for r in rs)
        if not wp and not sm and not refused:
            todo.append(h)
    todo.sort()
    if shard:
        i, n = shard
        todo = [h for k, h in enumerate(todo) if k % n == i]
    print(f"{len(todo)} non-WordPress hosts needing the sitemap/link bar")
    done = set((r["host"], r["kind"]) for r in probes)
    for host in todo:
        if not deadline_ok():
            print("RUN_DEADLINE")
            break
        o = host_owner[host]
        base = {"cedar_uid": o.get("cedar_uid", ""), "tribe_id": o["tribe_id"],
                "canonical_name": o.get("canonical_name", "")}
        sitemaps = [f"https://{host}/sitemap.xml",
                    f"https://{host}/sitemap_index.xml",
                    f"https://{host}/sitemap-index.xml",
                    f"https://{host}/wp-sitemap.xml"]
        rb = robots_ok(f"https://{host}/")
        rp = _robots.get(host)
        if rp is not None and getattr(rp, "site_maps", None):
            try:
                sitemaps = list(rp.site_maps()) + sitemaps
            except Exception:
                pass
        got = False
        for k, sm in enumerate(sitemaps[:5]):
            kind = f"sitemap_fb{k}"
            if (host, kind) in done:
                continue
            rec, r = get(sm, host, kind, dict(
                base, technique="docs/HIDDEN_DATA_TECHNIQUES.md #4 (sitemap - "
                                "the machine-readable inventory a non-WordPress "
                                "site publishes about itself)"))
            if r is not None and r.status_code == 200 and "<loc" in r.text:
                locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r.text)
                subs = [u for u in locs if u.lower().endswith(".xml")][:8]
                for su in subs:
                    rec2, r2 = get(su, host, f"{kind}_sub{subs.index(su)}", base)
                    append(PROBE, rec2)
                    if r2 is not None and r2.status_code == 200:
                        locs += re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r2.text)
                rec["n_items"] = len(locs)
                hits = [u for u in locs if LIST_KW.search(u)]
                rec["hits"] = hits[:60]
                rec["raw_file"] = save(r.url, r.content, ".xml")
                for u in hits:
                    append(DOCS, {
                        "cedar_uid": base["cedar_uid"], "tribe_id": base["tribe_id"],
                        "canonical_name": base["canonical_name"], "host": host,
                        "media_id": None, "document_url": u, "title": "",
                        "mime_type": None, "site_recorded_date": None,
                        "site_modified_date": None,
                        "discovery_technique":
                            "docs/HIDDEN_DATA_TECHNIQUES.md #4 (sitemap)",
                        "source_endpoint": sm,
                        "strong": bool(STRONG_KW.search(u)),
                        "formish": bool(FORM_KW.search(u)),
                        "checked_date": date.today().isoformat()})
                got = True
            append(PROBE, rec)
            done.add((host, kind))
            if got:
                break
        kind = "homepage_linkscan"
        if (host, kind) not in done:
            rec, r = get(f"https://{host}/", host, kind, dict(
                base, technique="homepage link scan - the fallback where a site "
                                "publishes neither a REST API nor a sitemap"))
            if r is not None and r.status_code == 200:
                links = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
                                   r.text, re.S | re.I)
                hits = []
                for href, lbl in links:
                    lbl = re.sub(r"<[^>]+>", " ", lbl)
                    if LIST_KW.search(href + " " + lbl):
                        hits.append(urllib.parse.urljoin(r.url, href))
                rec["n_items"] = len(links)
                rec["hits"] = sorted(set(hits))[:40]
                # A domain-name match is not evidence. Require the page to name
                # the tribe before anything from it is treated as that tribe's.
                nm = re.sub(r"[^a-z ]", " ", (base["canonical_name"] or "").lower())
                toks = [t for t in nm.split() if len(t) > 3]
                body = re.sub(r"<[^>]+>", " ", r.text).lower()
                rec["names_the_tribe"] = bool(toks) and any(t in body for t in toks)
                if not rec["names_the_tribe"]:
                    rec["note"] += ("; UNRELATED_DOMAIN? the served page does not "
                                    "contain any token of the tribe's name - not "
                                    "treated as this tribe's site")
                for u in (rec["hits"] if rec["names_the_tribe"] else []):
                    append(DOCS, {
                        "cedar_uid": base["cedar_uid"], "tribe_id": base["tribe_id"],
                        "canonical_name": base["canonical_name"], "host": host,
                        "media_id": None, "document_url": u, "title": "",
                        "mime_type": None, "site_recorded_date": None,
                        "site_modified_date": None,
                        "discovery_technique": "homepage link scan",
                        "source_endpoint": rec["url"],
                        "strong": bool(STRONG_KW.search(u)),
                        "formish": bool(FORM_KW.search(u)),
                        "checked_date": date.today().isoformat()})
            append(PROBE, rec)
            print(f"  {rec['http_status']:>6} {host:38} sitemap={got} "
                  f"links={rec.get('n_items')} hits={len(rec.get('hits') or [])} "
                  f"names_tribe={rec.get('names_the_tribe')}", flush=True)


def cmd_identifiers():
    """Walk every EXTERNAL business website named in the shard-L harvest and
    record UEI / CAGE / DUNS / EIN / NAICS with the verbatim quote, then check
    each against data/clean/fpds_uei_cage_map.csv.

    The map carries the literal string NAN in cage_code on 2,196 rows spanning
    2,193 distinct UEIs; it is EXCLUDED here, because keying on it would fuse
    2,193 unrelated entities.

    Nothing is resolved and nothing is minted: this records the identifier, the
    source and whether it matched. 503/510 own resolution."""
    tribal_hosts = set()
    for o in json.load(io.open(TARGETS, encoding="utf-8")):
        tribal_hosts.update(o.get("hosts") or [])
    biz = {}
    for f in sorted(glob.glob(os.path.join(BR, "TBD-L*.jsonl"))):
        for line in io.open(f, encoding="utf-8"):
            r = json.loads(line)
            w = (r.get("website") or "").strip()
            if not w:
                continue
            if not w.startswith("http"):
                w = "http://" + w
            h = urllib.parse.urlparse(w).netloc.lower()
            if not h or h in tribal_hosts or "wp-json" in w:
                continue
            biz.setdefault(h, {"host": h, "url": w,
                               "business_source_id": r["business_source_id"],
                               "source_id": r["source_id"],
                               "business_name_raw": r["business_name_raw"],
                               "nation_id": r["nation_id"]})
    print(f"{len(biz)} external business hosts")
    out = os.path.join(BR, "TBD-L00_business_identifiers.jsonl")
    seen = set()
    for r in read_all(out):
        seen.add((r["host"], r.get("probe_path")))
    fh = io.open(out, "a", encoding="utf-8")
    nhit = 0
    for h, b in sorted(biz.items()):
        if not deadline_ok():
            print("RUN_DEADLINE")
            break
        found_any = False
        for path in ID_PATHS:
            if (h, path) in seen:
                continue
            url = f"https://{h}{path}"
            rec, resp = get(url, h, "biz_id", {})
            row = {"host": h, "probe_path": path, "url": url,
                   "http_status": rec["http_status"],
                   "business_source_id": b["business_source_id"],
                   "source_id": b["source_id"],
                   "business_name_raw": b["business_name_raw"],
                   "nation_id": b["nation_id"],
                   "retrieved_date": date.today().isoformat(),
                   "identifiers": [], "note": rec.get("note", "")}
            if resp is not None and resp.status_code == 200 and \
                    "html" in (rec["content_type"] or ""):
                txt = re.sub(r"<script.*?</script>|<style.*?</style>", " ",
                             resp.text, flags=re.S | re.I)
                txt = re.sub(r"<[^>]+>", " ", txt)
                row["chars_extracted"] = len(txt)
                row["identifiers"] = _idhits(txt, url)
                if row["identifiers"]:
                    found_any = True
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            fh.flush()
            seen.add((h, path))
            if row["identifiers"]:
                nhit += len(row["identifiers"])
                print(f"  {h}{path}: "
                      + ", ".join(f"{i['identifier_type']}={i['identifier_value']}"
                                  for i in row["identifiers"][:6]))
            if path == "" and rec["http_status"] not in ("200", "202"):
                break        # the site itself is not answering; stop probing it
            if found_any and path != "":
                break        # one page with identifiers is enough
    fh.close()
    print("identifier observations:", nhit)
    cmd_identifier_match()


def cmd_identifier_match():
    out = os.path.join(BR, "TBD-L00_business_identifiers.jsonl")
    if not os.path.exists(out):
        print("no identifier file")
        return
    uei2, cage2 = {}, {}
    for r in csv.DictReader(io.open(FPDS_MAP, encoding="utf-8-sig")):
        u, c = (r["uei"] or "").strip().upper(), (r["cage_code"] or "").strip().upper()
        if u:
            uei2[u] = r
        # THE NAN TRAP: 2,196 rows carry the literal string 'NAN' in cage_code
        # across 2,193 distinct UEIs. Keying on it fuses them all.
        if c and c != "NAN":
            cage2.setdefault(c, []).append(r)
    res, hits = [], 0
    for r in read_all(out):
        for i in r.get("identifiers") or []:
            v = (i.get("identifier_value") or "").upper()
            m = None
            if i["identifier_type"] == "UEI" and v in uei2:
                m = {"matched": True, "match_on": "uei",
                     "fpds_uei": v, "fpds_cage": uei2[v]["cage_code"],
                     "fpds_legal_business_name": uei2[v]["legal_business_name"],
                     "fpds_first_year": uei2[v]["first_year"],
                     "fpds_last_year": uei2[v]["last_year"]}
            elif i["identifier_type"] == "CAGE" and v in cage2:
                cands = cage2[v]
                m = {"matched": True, "match_on": "cage",
                     "fpds_uei": ";".join(sorted({c["uei"] for c in cands})),
                     "fpds_cage": v,
                     "fpds_legal_business_name":
                         ";".join(sorted({c["legal_business_name"] for c in cands})),
                     "n_uei_for_this_cage": len(set(c["uei"] for c in cands))}
            res.append(dict(r, **{k: v2 for k, v2 in [("identifier", i)]},
                            **(m or {"matched": False})))
            hits += 1 if m else 0
    mp = os.path.join(BR, "TBD-L00_business_identifier_fpds_match.jsonl")
    with io.open(mp, "w", encoding="utf-8") as f:
        for r in res:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{len(res)} identifier observations, {hits} matched "
          f"data/clean/fpds_uei_cage_map.csv (NAN cage codes excluded)")


def cmd_derive():
    """Turn the probe log into a verdict per tribe, and hold every negative to
    the machine-readable bar.

    A tribe gets NO_LIST_FOUND only when, on at least one of its hosts, ALL of
    these ran and came back empty:
        * /wp-json/wp/v2/media UNFILTERED and paginated to X-WP-TotalPages
        * /wp-json/wp/v2/search for tero|vendor|preference|contractor|business
        * /wp-json/wp/v2/types, and the endpoint of any custom post type
      -- or, where the REST API is absent, sitemap.xml / sitemap_index.xml.

    Otherwise the verdict is NOT_SEARCHED_MACHINE_READABLE, which says there is
    work left rather than closing the door. Hand-written verdicts in
    _verdicts.jsonl always win; this only fills the rest."""
    tg = json.load(io.open(TARGETS, encoding="utf-8"))
    hand = set()
    if os.path.exists(VERDICTS):
        hand = set(r["tribe_id"] for r in read_all(VERDICTS))
    probes = list(read_all(PROBE_ALL))
    docs = list(read_all(DOCS_ALL))
    by_host = {}
    for r in probes:
        by_host.setdefault(r["host"], []).append(r)
    docs_by_tribe = {}
    for d in docs:
        docs_by_tribe.setdefault(d["tribe_id"], []).append(d)

    def host_bar(host):
        """(met, missing[]) for one host."""
        rs = by_host.get(host, [])
        st = {r["kind"]: r for r in rs}
        miss = []
        wp_live = any(k.startswith("wp_types") and r["http_status"] == "200"
                      and (r.get("post_types") or r.get("cpt_rest_bases"))
                      for k, r in st.items())
        if wp_live:
            am = [r for k, r in st.items() if k.startswith("wp_allmedia")]
            if not am:
                miss.append("wp/v2/media unfiltered")
            else:
                tot = max((int(r.get("x-wp-totalpages") or 1)) for r in am)
                if len(am) < min(tot, 60):
                    miss.append(f"wp/v2/media paginated ({len(am)}/{tot} pages)")
            if not all(f"wp_search_{t}" in st for t in MR_TERMS):
                miss.append("wp/v2/search")
            cpts = {}
            for k, r in st.items():
                if k.startswith("wp_types"):
                    cpts.update(r.get("cpt_rest_bases") or {})
            want = [c for c in cpts
                    if re.search(r"(vendor|business|enterprise|compan|contractor"
                                 r"|supplier|director|tero|licen|procure)", c, re.I)]
            if any(f"wp_cpt_{c}" not in st for c in want):
                miss.append("custom post type endpoints")
        else:
            sm_ok = any(k.startswith("sitemap") and r["http_status"] == "200"
                        for k, r in st.items())
            scan = st.get("homepage_linkscan")
            scan_ok = bool(scan) and scan.get("http_status") == "200"
            if not (sm_ok or scan_ok):
                miss.append("sitemap or homepage link scan (host is not "
                            "WordPress-REST reachable)")
        refused = [r["http_status"] for r in rs
                   if r["http_status"] in ("ROBOTS_DISALLOW", "EXCLUDED_TERMS")]
        return (not miss), miss, refused

    out, counts = [], collections.Counter()
    for o in sorted(tg, key=lambda x: x["cedar_uid"]):
        tid = o["tribe_id"]
        if tid in hand:
            counts["hand_written"] += 1
            continue
        hosts = o.get("hosts") or []
        if not hosts:
            counts["NO_SITE_FOUND"] += 1
            out.append({"tribe_id": tid, "verdict": "NO_SITE_FOUND",
                        "harvest_status": "NO_SITE_ESTABLISHED",
                        "types_published": "NONE_FOUND",
                        "searched": "no government host was established for this "
                                    "tribe by any sibling shard or by search",
                        "notes": "Absence of a list is a property of the search "
                                 "surface, not a finding about the tribe."})
            continue
        met_any, miss_all, refused_all = False, [], []
        for h in hosts:
            met, miss, refused = host_bar(h)
            refused_all += refused
            if met:
                met_any = True
            else:
                miss_all += [f"{h}: {x}" for x in miss]
        # recompute the strength flag rather than trusting what was stored:
        # the pattern has been tightened since collection ("TERO Director" is
        # a job posting, not a directory), and a stale flag would manufacture
        # a candidate that does not exist.
        d = [x for x in docs_by_tribe.get(tid, [])
             if STRONG_KW.search(f"{x.get('document_url','')} "
                                 f"{x.get('title','') or ''}")]
        if d:
            counts["CANDIDATE_UNREVIEWED"] += 1
            out.append({"tribe_id": tid, "verdict": "CANDIDATE_FOUND_UNREVIEWED",
                        "list_url": d[0]["document_url"],
                        "harvest_status": "CANDIDATE_NOT_YET_PARSED",
                        "searched": "; ".join(sorted({x["discovery_technique"]
                                                      for x in d}))[:900],
                        "notes": "A strong list-shaped candidate was found and "
                                 "has NOT been opened. Not a LIST_FOUND and not "
                                 "a NO_LIST_FOUND: "
                                 + "; ".join(x["document_url"] for x in d[:5])})
            continue
        if met_any:
            counts["NO_LIST_FOUND"] += 1
            out.append({
                "tribe_id": tid, "verdict": "NO_LIST_FOUND",
                "verdict_certification": "NO_LIST_FOUND",
                "verdict_vendor_relationship": "NO_LIST_FOUND",
                "verdict_business_licence": "NO_LIST_FOUND",
                "types_published": "NONE_FOUND", "list_type": "NONE",
                "assertion_class": "NONE", "list_format": "NONE",
                "harvest_status": "NO_LIST_TO_HARVEST",
                "harvest_route_rung": "machine-readable bar met; nothing to harvest",
                "harvest_technique": "docs/HIDDEN_DATA_TECHNIQUES.md #3 + #4",
                "hidden_route_sweep_2026-09-01":
                    "wp/v2/media (unfiltered, paginated) + wp/v2/search x5 + "
                    "wp/v2/types + custom post types + sitemap: no list",
                "searched":
                    "MACHINE-READABLE BAR MET on " + ";".join(hosts[:4]) +
                    " - /wp-json/wp/v2/media unfiltered and paginated to "
                    "X-WP-TotalPages, /wp-json/wp/v2/search for tero, vendor, "
                    "preference, contractor and business, /wp-json/wp/v2/types "
                    "and every business-shaped custom post type it named, and "
                    "the sitemap where the REST API was absent",
                "notes": "A negative that clears the bar: nav and search alone "
                         "would not have been evidence."})
        else:
            counts["NOT_SEARCHED_MACHINE_READABLE"] += 1
            out.append({
                "tribe_id": tid, "verdict": "NOT_SEARCHED_MACHINE_READABLE",
                "types_published": "UNKNOWN", "list_type": "NONE",
                "assertion_class": "NONE", "list_format": "NONE",
                "harvest_status": ("EXCLUDED_ROBOTS" if "ROBOTS_DISALLOW"
                                   in refused_all else
                                   "NOT_SEARCHED_MACHINE_READABLE"),
                "harvest_route_rung": "bar not met; see searched",
                "searched": "BAR NOT MET - still to run: "
                            + "; ".join(sorted(set(miss_all))[:8]),
                "notes": "NOT a NO_LIST_FOUND. The endpoints that would make a "
                         "negative evidence have not all answered on this "
                         "tribe's hosts, so the honest status is that the "
                         "machine-readable surface has not been searched."})
    with io.open(os.path.join(SL, "_verdicts_auto.jsonl"), "w",
                 encoding="utf-8") as f:
        for r in out:
            r.setdefault("checked_by", "shard-L acquisition pass 2026-09-01")
            r.setdefault("publishable", "N")
            r.setdefault("source_terms_status", "NOT_CHECKED")
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(dict(counts))
    return counts


def cmd_registry():
    """Append one row per shard-L tribe to the vendor-list registry, in its
    existing column order. APPEND ONLY - shard M is appending to the same file,
    so the header is read from disk and never rewritten, and each row is
    flushed as it is written.

    Input is _verdicts.jsonl: one object per tribe carrying the fields this
    workstream determined. A tribe with no verdict object gets a NOT_CHECKED
    row, because a tribe that was never looked at must not be indistinguishable
    from one that was looked at and had nothing."""
    with io.open(REGISTRY, encoding="utf-8-sig", newline="") as f:
        cols = next(csv.reader(f))
    existing = set()
    for r in csv.DictReader(io.open(REGISTRY, encoding="utf-8-sig")):
        existing.add(r["tribe_id"].strip())
    tg = {o["tribe_id"]: o for o in json.load(io.open(TARGETS, encoding="utf-8"))}
    ver = {}
    for r in read_all(os.path.join(SL, "_verdicts_auto.jsonl")):
        ver[r["tribe_id"]] = r
    if os.path.exists(VERDICTS):
        for r in read_all(VERDICTS):
            ver[r["tribe_id"]] = r        # hand-written verdict always wins
    today = date.today().isoformat()
    written = 0
    with io.open(REGISTRY, "a", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore",
                           lineterminator="\r\n")
        for tid, o in sorted(tg.items(), key=lambda kv: kv[1]["cedar_uid"]):
            if tid in existing:
                print(f"  SKIP already in registry: {tid}")
                continue
            v = ver.get(tid, {})
            row = {c: "" for c in cols}
            row.update({
                "tribe_id": tid,
                "canonical_name": o["canonical_name"],
                "entity_class": "Federally recognized tribe",
                "priority_group": POP_BASIS,
                "why_chosen": ("Never checked for a published vendor or "
                               "Native-owned-business list. Selected as the "
                               "first half by cedar_uid of the 297 federally "
                               "recognised tribes absent from this registry "
                               "on 2026-08-26."),
                "roster_built_date": today,
                "roster_built_by": "570_shard_l_vendor_list_hunt.py",
                "official_site": v.get("official_site", o.get("official_site", "")),
                "hosts": ";".join(o.get("hosts") or []),
                "publisher_relationship": "SELF",
                "consent_status": "UNRESOLVED",
                "suppression_key": f"SUPPRESS::{tid}",
                "checked_date": today,
                "checked_by": "shard-L acquisition pass 2026-09-01",
            })
            for k in ("state", "bia_region", "verdict", "verdict_certification",
                      "verdict_vendor_relationship", "verdict_business_licence",
                      "types_published", "list_url", "list_type",
                      "assertion_class", "list_format", "entry_count_approx",
                      "identifiers_present", "update_frequency",
                      "vendor_relationship_url", "vendor_relationship_note",
                      "business_licence_url", "business_licence_note",
                      "robots_note", "wayback_priority",
                      "wayback_excluded_reason", "source_terms_status",
                      "source_terms_quote", "publishable", "searched", "notes",
                      "harvest_date", "harvest_rows", "harvest_source_id",
                      "harvest_status", "harvest_route_rung",
                      "harvest_technique", "newsletter_url",
                      "hidden_route_sweep_2026-09-01"):
                if v.get(k) not in (None, ""):
                    row[k] = v[k]
            if not row["verdict"]:
                row["verdict"] = "NOT_CHECKED"
            if not row["harvest_status"]:
                row["harvest_status"] = ("NO_LIST_TO_HARVEST"
                                         if row["verdict"].startswith("NO_LIST")
                                         else "NOT_ATTEMPTED")
            if not row["publishable"]:
                row["publishable"] = "N"
            if not row["source_terms_status"]:
                row["source_terms_status"] = "NOT_CHECKED"
            w.writerow(row)
            fh.flush()
            written += 1
    print(f"appended {written} rows to {os.path.basename(REGISTRY)}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "plan"
    if cmd == "sitefallback":
        arg = sys.argv[2] if len(sys.argv) > 2 else None
        if arg and re.fullmatch(r"\d+/\d+", arg):
            i, n = arg.split("/")
            cmd_sitefallback((int(i), int(n)))
        else:
            cmd_sitefallback()
        raise SystemExit(0)
    if cmd == "ids":
        cmd_identifiers()
        raise SystemExit(0)
    if cmd == "idmatch":
        cmd_identifier_match()
        raise SystemExit(0)
    if cmd == "derive":
        cmd_derive()
        raise SystemExit(0)
    if cmd == "registry":
        cmd_registry()
        raise SystemExit(0)
    if cmd == "harvest":
        cmd_harvest(sys.argv[2] if len(sys.argv) > 2 else None)
        raise SystemExit(0)
    if cmd == "plan":
        cmd_plan()
    elif cmd == "offline":
        cmd_offline()
    elif cmd == "sweep":
        arg = sys.argv[2] if len(sys.argv) > 2 else None
        if arg and re.fullmatch(r"\d+/\d+", arg):
            i, n = arg.split("/")
            cmd_sweep(None, (int(i), int(n)))
        else:
            cmd_sweep(arg)
    elif cmd == "mr":
        arg = sys.argv[2] if len(sys.argv) > 2 else None
        if arg and re.fullmatch(r"\d+/\d+", arg):
            i, n = arg.split("/")
            cmd_machine_readable((int(i), int(n)))
        else:
            cmd_machine_readable()
    elif cmd == "cpt":
        cmd_cpt()
    elif cmd == "terms":
        cmd_terms(sys.argv[2:] or None)
    elif cmd == "fetch":
        cmd_fetch(strong_only=("--all" not in sys.argv))
    else:
        raise SystemExit(f"unknown mode {cmd}")
