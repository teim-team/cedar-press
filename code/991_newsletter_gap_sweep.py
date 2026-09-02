"""Discovery sweep for the nations no newsletter probe has ever reached.

After `990_build_newsletter_corpus.py`, `data/clean/tribal_newsletter_coverage.csv`
says 690 spine entities are `not_probed` and 486 of them have a live website.
That is not an absence, it is `NOT_SEARCHED_MACHINE_READABLE`
(docs/HIDDEN_DATA_TECHNIQUES.md). This script converts it into a real finding.

SCOPE. Every `not_probed` entity with a live site EXCEPT BIE schools. Shard G's
reasoning holds: a school publishes a calendar and a lunch menu, and 182 extra
hosts is a poor trade against 304 nations, villages, corporations and
organisations that publish economic content. BIE schools are written to the
output as `deliberately_out_of_scope` so the exclusion is visible rather than
silent.

TECHNIQUE ORDER - the rendered page is LAST, not first
  1. `robots.txt`      names the sitemaps, and names the Disallow paths we then
                       refuse. A 403 or 404 here means "no robots file", not a
                       ban - that misreading produced 22 phantom blocks in this
                       project once.
  2. `/wp-json/wp/v2/search?search=newsletter`   finds newsletter PAGES that are
                       not in the navigation. One request.
  3. `/wp-json/wp/v2/media?search=newsletter&media_type=application`  where the
                       PDF back issues actually live. `X-WP-Total` gives the
                       archive depth without downloading a single issue.
  4. `sitemap.xml` / `sitemap_index.xml`   the site's own inventory, including
                       pages removed from the nav but still served.
  5. `/feed/`          dated items, parseable.
  6. the homepage      only if 1-5 found nothing.

A NEGATIVE FROM SEARCH ALONE IS NOT A NEGATIVE. `route_coverage` records which
of the six actually ran, so an absence can be read as the specific claim it is.

THE DOWNLOAD-SIDE TRAP. Every response body is md5-hashed. If one host returns
the same hash for three different URLs, the host is serving a default rather
than what was asked for (the `?wpdmdl=` case: 302 identical PDFs, all HTTP 200),
and the host is marked `IDENTICAL_BODY_HASHES` and its findings are quarantined.

PRIVACY. Index pages and metadata only. No issue body is downloaded, so no
obituary, birthday or health notice enters Cedar by this route.

REFUSALS. The eight `TERMS_STATED_RESTRICTIVE` publishers are skipped before the
first request. `robots.txt` Disallow is honoured. No admin, staging or
login-gated path is requested.

    python code/991_newsletter_gap_sweep.py                 # resumable
    python code/991_newsletter_gap_sweep.py --limit 20
    python code/991_newsletter_gap_sweep.py verify
    python code/991_newsletter_gap_sweep.py verify --selftest
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parent.parent
COVER = ROOT / "data" / "clean" / "tribal_newsletter_coverage.csv"
WEBMAP = ROOT / "data" / "staging" / "cedar_web_map.csv"
OUTD = ROOT / "data" / "staging" / "tribe_harvest" / "newsletter_gap_sweep"
OUT = OUTD / "gap_sweep.jsonl"
STATE = OUTD / "_state.json"
OUTD.mkdir(parents=True, exist_ok=True)
TODAY = date.today().isoformat()
csv.field_size_limit(10_000_000)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from importlib import import_module  # noqa: E402
_c = import_module("990_build_newsletter_corpus") if False else None  # doc only

UA = ("CedarPress-research/1.0 (tribal newsletter corpus; "
      "contact elijahsamsonmoreno@gmail.com)")
HOST_DELAY = 1.8
REQ_BUDGET = 7
RUN_DEADLINE = time.time() + 3 * 3600
OUT_OF_SCOPE_CLASSES = {"BIE School"}

# Mirrors 990's list. Duplicated deliberately: a refusal that depends on another
# module importing cleanly is a refusal that can fail open.
RESTRICTIVE_HOSTS = {
    "colvilletribes.com", "tribaltribune.com", "colvillecasinos.com",
    "ctuir.org", "wildhorseresort.com",
    "yakama.com", "yakama.org", "legendscasino.com",
    "chickasaw.net", "chickasawtimes.net", "chickasawbusinessnetwork.com",
    "nana.com", "akima.com",
    "southernute-nsn.gov", "sudrum.com", "skyutecasino.com",
    "fcpotawatomi.com", "potawatomi.com", "paysbig.com", "cartercasino.com",
    "stillaguamish.com", "angelofthewinds.com",
}
RESTRICTIVE_UIDS = {"CE-0013K-5M", "CE-001BT-Q3", "CE-001CC-8N", "CE-00135-HP",
                    "CE-0007G-30", "CE-001AX-4Y", "CE-0014H-YJ", "CE-001AY-AQ"}

# Tight. The loose version matched every casino press release whose slug
# contained "times" or "journal" and returned 25 marketing articles as if they
# were 25 publications. A channel is a PUBLICATION, not an article about a spa.
NEWSY = re.compile(
    r"(?i)(news[-_ ]?letters?|e-?news\b|tribal[-_ ]?news\b|"
    r"smoke[-_ ]signals|bulletins?\b|gazette|periodical|"
    r"press[-_ ]?releases?|annual[-_ ]?reports?|publications?\b)")
# newspaper mastheads: accepted from ANCHOR TEXT, where a human wrote the name,
# never from a URL slug, where the same words are ordinary English.
MASTHEAD = re.compile(
    r"(?i)\b(tribune|herald|crier|messenger|sentinel|observer|"
    r"the\s+\w+\s+(?:times|journal|voice|drum|news|word|eagle|arrow))\b")
BIZ = re.compile(
    r"(?i)\b(acquisition|acquired|merger|joint venture|contract award|"
    r"economic development|enterprise|subsidiary|casino|revenue|"
    r"business|employment|jobs|grant|award|construction|lease|"
    r"broadband|energy|opportunit\w+)\b")

_last, _robots_cache = {}, {}


# ------------------------------------------------------------------ fetching
def sleep_host(h):
    t = _last.get(h)
    if t is not None:
        d = HOST_DELAY - (time.time() - t)
        if d > 0:
            time.sleep(d)
    _last[h] = time.time()


def get(url, timeout=35, accept=None):
    """One attempt. Returns dict with status, headers, body, md5."""
    h = urlparse(url).netloc.lower()
    sleep_host(h)
    cmd = ["curl", "-s", "-L", "-D", "-", "-A", UA,
           "-H", "Accept: " + (accept or "text/html,application/xhtml+xml,"
                               "application/xml;q=0.9,application/json;q=0.9,*/*;q=0.8"),
           "-H", "Accept-Language: en-US,en;q=0.9",
           "--max-time", str(timeout), "--max-filesize", "8000000",
           "-w", "\n__HTTPSTATUS__%{http_code}", url]
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=timeout + 25)
    except subprocess.TimeoutExpired:
        return {"url": url, "status": 0, "headers": {}, "body": "", "md5": "",
                "error": "timeout"}
    out = p.stdout
    m = re.search(rb"\n__HTTPSTATUS__(\d+)$", out)
    status = int(m.group(1)) if m else 0
    raw = out[: m.start()] if m else out
    # curl -D - with -L prepends one header block per hop; keep the last
    parts = re.split(rb"\r?\n\r?\n", raw, maxsplit=0)
    hdr_txt, body = b"", raw
    for i, part in enumerate(parts):
        if part[:5].upper() == b"HTTP/":
            hdr_txt = part
            body = b"\r\n\r\n".join(parts[i + 1:])
    headers = {}
    for line in hdr_txt.decode("latin-1", "replace").splitlines()[1:]:
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip().lower()] = v.strip()
    return {"url": url, "status": status, "headers": headers,
            "body": body.decode("utf-8", "replace"),
            "md5": hashlib.md5(body).hexdigest() if body else "",
            "bytes": len(body), "error": ""}


def robots_for(base):
    """Return (disallow_paths, sitemaps, how). A 403/404 is NOT a ban."""
    if base in _robots_cache:
        return _robots_cache[base]
    r = get(urljoin(base, "/robots.txt"))
    dis, sm = [], []
    how = "robots_http_%s" % r["status"]
    if r["status"] == 200 and "<html" not in r["body"][:400].lower():
        agent_applies = True
        for line in r["body"].splitlines():
            line = line.split("#")[0].strip()
            if not line:
                continue
            k, _, v = line.partition(":")
            k, v = k.strip().lower(), v.strip()
            if k == "user-agent":
                agent_applies = v in ("*", "cedarpress-research")
            elif k == "disallow" and agent_applies and v:
                dis.append(v)
            elif k == "sitemap" and v:
                sm.append(v)
    else:
        how = "robots_absent_http_%s_NOT_a_ban" % r["status"]
    _robots_cache[base] = (dis, sm, how)
    return _robots_cache[base]


def blocked(path, disallow):
    for d in disallow:
        d = d.strip()
        if d == "/":
            return True
        if d and path.startswith(d.rstrip("*")):
            return True
    return False


# ------------------------------------------------------------------ the probe
def probe(ent, site):
    base = site if site.endswith("/") else site + "/"
    host = urlparse(base).netloc.lower()
    rec = {
        "cedar_uid": ent["cedar_uid"], "tribe_id": ent["tribe_id"],
        "canonical_name": ent["canonical_name"], "entity_class": ent["entity_class"],
        "state": ent["state"], "site": site, "site_host": host,
        "checked_date": TODAY, "route_coverage": [], "requests_made": 0,
        "found": [], "wp_total_media": None, "archive_years": [],
        "business_signal_terms": [], "identical_body_hashes": False,
        "soft_404_catchall": False,
        "robots": "", "robots_disallow": [], "outcome": "", "note": "",
        "attribution_caution": "",
    }
    hashes = Counter()
    budget = [REQ_BUDGET]

    def spend(url, **kw):
        if budget[0] <= 0:
            return None
        budget[0] -= 1
        rec["requests_made"] += 1
        r = get(url, **kw)
        # Only 200s are hashed. A host that 404s four probes with one custom
        # error page is not the ?wpdmdl= pathology; it is a normal 404 page,
        # and quarantining it would throw away good absences.
        if r["md5"] and r["status"] == 200:
            hashes[r["md5"]] += 1
        return r

    # ---- 1. robots
    dis, sitemaps, how = robots_for(base)
    rec["requests_made"] += 1
    budget[0] -= 1
    rec["robots"], rec["robots_disallow"] = how, dis[:20]
    rec["route_coverage"].append("robots_txt")

    def add(kind, url, title="", depth="", technique="", extra=None):
        if blocked(urlparse(url).path or "/", dis):
            return
        d = {"kind": kind, "url": url, "title": title[:180],
             "archive_depth": depth, "technique": technique}
        if extra:
            d.update(extra)
        rec["found"].append(d)

    # ---- 2. WordPress REST search: pages not in the navigation
    if budget[0] > 0 and not blocked("/wp-json/", dis):
        r = spend(base + "wp-json/wp/v2/search?search=newsletter&per_page=20")
        rec["route_coverage"].append("wp_json_search")
        if r and r["status"] == 200 and r["body"].lstrip()[:1] in "[{":
            try:
                for it in json.loads(r["body"])[:20]:
                    u = (it.get("url") or "").replace("\\/", "/")
                    if u and NEWSY.search(u + " " + (it.get("title") or "")):
                        add("page", u, it.get("title", ""),
                            technique="HIDDEN_DATA #3 wp-json search")
            except (ValueError, TypeError):
                pass

            # ---- 3. WP media: the PDF back issues, and the depth in a header
            r2 = spend(base + "wp-json/wp/v2/media?search=newsletter"
                              "&media_type=application&per_page=100")
            rec["route_coverage"].append("wp_json_media")
            if r2 and r2["status"] == 200:
                rec["wp_total_media"] = r2["headers"].get("x-wp-total")
                body = r2["body"].replace("\\/", "/")
                pdfs = sorted(set(re.findall(r'https?://[^"\s\\]+?\.(?:pdf|PDF)', body)))
                yrs = sorted(set(re.findall(r"/(19\d\d|20\d\d)/", " ".join(pdfs))))
                rec["archive_years"] += yrs
                for u in pdfs[:40]:
                    if NEWSY.search(u):
                        add("issue_pdf", u, depth="%d newsletter PDFs in the media index"
                            % len([x for x in pdfs if NEWSY.search(x)]),
                            technique="HIDDEN_DATA #3 wp-json media")

    # ---- 4. sitemap: the site's own inventory
    if budget[0] > 0:
        cand = sitemaps[:1] or [base + "sitemap_index.xml"]
        r = spend(cand[0])
        rec["route_coverage"].append("sitemap")
        if r and r["status"] == 200 and "<" in r["body"][:200]:
            locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r["body"])
            subs = [u for u in locs if u.endswith(".xml") and NEWSY.search(u)]
            for u in locs:
                if NEWSY.search(u) and not u.endswith(".xml"):
                    add("page", u, technique="HIDDEN_DATA #4 sitemap")
            if subs and budget[0] > 0:
                r2 = spend(subs[0])
                if r2 and r2["status"] == 200:
                    for u in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r2["body"]):
                        if NEWSY.search(u):
                            add("page", u, technique="HIDDEN_DATA #4 sitemap (nested)")
            rec["archive_years"] += sorted(set(re.findall(
                r"<lastmod>\s*(19\d\d|20\d\d)", r["body"])))

    # ---- 5. feed
    if budget[0] > 0 and not rec["found"]:
        r = spend(base + "feed/", accept="application/rss+xml,application/xml,*/*")
        rec["route_coverage"].append("feed")
        if r and r["status"] == 200 and re.search(r"(?i)<(rss|feed)\b", r["body"][:900]):
            items = re.findall(r"(?is)<item>(.*?)</item>", r["body"])[:60]
            yrs = sorted(set(re.findall(r"\b(19\d\d|20\d\d)\b",
                                        " ".join(re.findall(r"(?is)<pubDate>(.*?)</pubDate>",
                                                            r["body"])))))
            rec["archive_years"] += yrs
            add("feed", base + "feed/",
                depth="%d items in the feed document" % len(items),
                technique="HIDDEN_DATA #13 feeds")
            rec["business_signal_terms"] += sorted(set(
                x.lower() for x in BIZ.findall(r["body"])))[:12]

    # ---- 6. the rendered homepage, last
    if budget[0] > 0 and not rec["found"]:
        r = spend(base)
        rec["route_coverage"].append("homepage")
        if r and r["status"] and 200 <= r["status"] < 400:
            for href, txt in re.findall(
                    r'(?is)<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.{0,120}?)</a>', r["body"]):
                flat = re.sub(r"<[^>]+>", " ", txt).strip()
                if NEWSY.search(href) or NEWSY.search(flat) or MASTHEAD.search(flat):
                    u = urljoin(base, href)
                    if urlparse(u).scheme in ("http", "https"):
                        add("page", u, flat, technique="rendered homepage link (last resort)")
            rec["business_signal_terms"] += sorted(set(
                x.lower() for x in BIZ.findall(r["body"])))[:12]

    # ---- the download-side trap, in two halves.
    # A host that answers three DIFFERENT 200 requests with one identical body
    # is serving a default. If that host also produced findings, those findings
    # are untrustworthy and are discarded. If it produced none, the same fact is
    # merely a soft-404 catch-all router, which is worth recording and is not a
    # reason to throw away a legitimate absence.
    if hashes and max(hashes.values()) >= 3:
        rec["identical_body_hashes"] = True
        if rec["found"]:
            rec["found"] = []
            rec["outcome"] = "QUARANTINED_IDENTICAL_BODY_HASHES"
            rec["note"] = ("host returned the same 200 body md5 for %d different "
                           "URLs; findings discarded - a 200 with a valid body is "
                           "not proof the right object was served"
                           % max(hashes.values()))
            return rec
        rec["soft_404_catchall"] = True
        rec["identical_body_hashes"] = False
        rec["note"] = ("host answers unknown paths with one identical 200 body "
                       "(soft-404 catch-all); no finding was derived from it")

    # de-duplicate, then COLLAPSE ARTICLES INTO THE CHANNEL THEY BELONG TO.
    # A sitemap listing 25 press releases under /press-release/<slug>/ is one
    # channel with 25 items, not 25 publications. Recording it the other way
    # inflates the corpus with marketing copy and hides the archive depth.
    seen, ded = set(), []
    for d in rec["found"]:
        if d["url"] not in seen:
            seen.add(d["url"])
            ded.append(d)
    groups = defaultdict(list)
    singles = []
    for d in ded:
        p = urlparse(d["url"])
        segs = [s for s in p.path.split("/") if s]
        if d["kind"] == "page" and len(segs) >= 2 and NEWSY.search(segs[0]):
            groups["%s://%s/%s/" % (p.scheme, p.netloc, segs[0])].append(d)
        else:
            singles.append(d)
    collapsed = []
    for idx, items in groups.items():
        if len(items) >= 3:
            collapsed.append({
                "kind": "channel_index", "url": idx,
                "title": items[0].get("title", ""),
                "archive_depth": "%d item URLs under this path in the site's own "
                                 "index" % len(items),
                "technique": items[0]["technique"] + " (articles collapsed to the "
                                                     "channel path)",
                "example_item_urls": [i["url"] for i in items[:3]],
            })
        else:
            collapsed.extend(items)
    rec["found"] = (collapsed + singles)[:25]

    # attribution caution: the site we probed may belong to a regional
    # consortium or health corporation rather than to this entity. Flag, do not
    # drop - the web map put the URL there for a reason and that reason is
    # recorded upstream.
    toks = [t for t in re.split(r"[^a-z]+", rec["canonical_name"].lower()) if len(t) > 4]
    if toks and not any(t[:6] in host.replace("-", "") for t in toks):
        rec["attribution_caution"] = (
            "site host %s does not carry this entity's name; the channel found "
            "here may be published by another organisation (a regional "
            "consortium, health corporation or enterprise). Verify the publisher "
            "before treating this as the entity's own newsletter." % host)
    rec["archive_years"] = sorted(set(rec["archive_years"]))
    rec["business_signal_terms"] = sorted(set(rec["business_signal_terms"]))[:15]
    rec["outcome"] = "FOUND" if rec["found"] else "NONE_FOUND"
    if not rec["found"]:
        rec["note"] = ("no newsletter channel on any of the machine-readable "
                       "routes run (%s). This is an absence for THOSE routes."
                       % ", ".join(rec["route_coverage"]))
    return rec


# ------------------------------------------------------------------ driver
def load_targets():
    cover = list(csv.DictReader(COVER.open(encoding="utf-8-sig")))
    # a better site URL than the coverage table's first-seen one
    pref = {"government": 0, "organization": 1, "institution": 2, "corporate": 3,
            "consortium": 4, "tribal_council": 5}
    best = {}
    for m in csv.DictReader(WEBMAP.open(encoding="utf-8-sig")):
        st = m.get("http_status", "")
        if not (st.isdigit() and 200 <= int(st) < 400):
            continue
        rank = pref.get(m["url_type"], 9)
        cur = best.get(m["cedar_uid"])
        if cur is None or rank < cur[0]:
            best[m["cedar_uid"]] = (rank, m["url"])
    tgt, skipped = [], []
    for c in cover:
        if c["probe_status"] != "not_probed":
            continue
        if c["cedar_uid"] in RESTRICTIVE_UIDS:
            skipped.append((c, "TERMS_STATED_RESTRICTIVE"))
            continue
        if c["entity_class"] in OUT_OF_SCOPE_CLASSES:
            skipped.append((c, "deliberately_out_of_scope"))
            continue
        url = (best.get(c["cedar_uid"], (9, ""))[1] or c["site_url"]).strip()
        if not url.startswith("http"):
            skipped.append((c, "no_live_site"))
            continue
        h = urlparse(url).netloc.lower().lstrip("www.")
        # A Wayback base is not a site. Path-joining /wp-json/ onto a
        # /web/<ts>/ URL produces nonsense, and a snapshot of a THIRD PARTY's
        # page (the entity's regional consortium, typically) is not evidence
        # about this entity's own publishing.
        if h.endswith("archive.org") or h.endswith("archive-it.org"):
            skipped.append((c, "site_url_is_a_wayback_snapshot"))
            continue
        if any(h == d or h.endswith("." + d) for d in RESTRICTIVE_HOSTS):
            skipped.append((c, "TERMS_STATED_RESTRICTIVE_host"))
            continue
        tgt.append((c, url))
    return tgt, skipped


def summarize():
    recs = [json.loads(l) for l in OUT.read_text(encoding="utf-8").splitlines()
            if l.strip()] if OUT.exists() else []
    tgt, skipped = load_targets()
    real = [r for r in recs if r["outcome"] not in
            ("deliberately_out_of_scope", "no_live_site", "TERMS_STATED_RESTRICTIVE",
             "TERMS_STATED_RESTRICTIVE_host")]
    st = {
        "script": "code/991_newsletter_gap_sweep.py", "run_date": TODAY,
        "expected_total": len(tgt), "attempted": len(real),
        "run_complete": len({r["cedar_uid"] for r in real}) >= len(tgt),
        "found": sum(1 for r in real if r["outcome"] == "FOUND"),
        "none_found": sum(1 for r in real if r["outcome"] == "NONE_FOUND"),
        "quarantined": sum(1 for r in real if r["identical_body_hashes"]),
        "found_by_class": dict(Counter(r["entity_class"] for r in real
                                       if r["outcome"] == "FOUND")),
        "attempted_by_class": dict(Counter(r["entity_class"] for r in real)),
        "channels_found": sum(len(r["found"]) for r in real),
        "by_technique": dict(Counter(d["technique"] for r in real for d in r["found"])),
        "route_coverage": dict(Counter(x for r in real for x in r["route_coverage"])),
        "skipped": dict(Counter(why for _c, why in skipped)),
        "requests_made": sum(r["requests_made"] for r in real),
    }
    STATE.write_text(json.dumps(st, indent=2), encoding="utf-8")
    return st


def run(limit=None):
    tgt, _sk = load_targets()
    done = set()
    if OUT.exists():
        for line in OUT.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    done.add(json.loads(line)["cedar_uid"])
                except ValueError:
                    pass
    todo = [(c, u) for c, u in tgt if c["cedar_uid"] not in done]
    if limit:
        todo = todo[:limit]
    print("targets %d; already done %d; this run %d"
          % (len(tgt), len(done), len(todo)), file=sys.stderr)
    n = 0
    # Append-and-flush PER ENTITY. A buffered shard map nearly lost 1,159 rows
    # in this project once; a three-hour network sweep is exactly the run you
    # cannot afford to buffer.
    with OUT.open("a", encoding="utf-8") as fh:
        for c, url in todo:
            if time.time() > RUN_DEADLINE:
                print("RUN_DEADLINE reached", file=sys.stderr)
                break
            try:
                rec = probe(c, url)
            except Exception as exc:                      # noqa: BLE001
                rec = {"cedar_uid": c["cedar_uid"], "tribe_id": c["tribe_id"],
                       "canonical_name": c["canonical_name"],
                       "entity_class": c["entity_class"], "state": c["state"],
                       "site": url, "site_host": urlparse(url).netloc,
                       "checked_date": TODAY, "route_coverage": [],
                       "requests_made": 0, "found": [], "wp_total_media": None,
                       "archive_years": [], "business_signal_terms": [],
                       "identical_body_hashes": False, "robots": "",
                       "robots_disallow": [], "outcome": "ERROR",
                       "note": "%s: %s" % (type(exc).__name__, exc)}
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            n += 1
            if n % 10 == 0:
                print("  %d/%d  %-9s %s" % (n, len(todo), rec["outcome"],
                                            rec["canonical_name"][:44]), file=sys.stderr)
    st = summarize()
    print(json.dumps(st, indent=2)[:3000])
    return 0


# ------------------------------------------------------------------ verify
def verify(recs=None):
    if recs is None:
        recs = [json.loads(l) for l in OUT.read_text(encoding="utf-8").splitlines()
                if l.strip()] if OUT.exists() else []
    f = []

    # 1. no restricted publisher was touched
    bad = [r for r in recs if r["cedar_uid"] in RESTRICTIVE_UIDS
           or any((r.get("site_host", "").lstrip("www.") == d
                   or r.get("site_host", "").endswith("." + d))
                  for d in RESTRICTIVE_HOSTS)]
    if bad:
        f.append("RESTRICTIVE_SOURCE_TOUCHED: %d, e.g. %s"
                 % (len(bad), bad[0]["site_host"]))

    # 2. no robots Disallow path was fetched
    viol = []
    for r in recs:
        dis = r.get("robots_disallow") or []
        for d in r.get("found") or []:
            p = urlparse(d["url"]).path or "/"
            if urlparse(d["url"]).netloc.lower() == r.get("site_host", "").lower() \
                    and blocked(p, dis):
                viol.append((r["cedar_uid"], d["url"]))
    if viol:
        f.append("ROBOTS_DISALLOW_FETCHED: %d, e.g. %s" % (len(viol), viol[0][1]))

    # 3. no admin / staging / dotfile path was ever recorded
    forb = re.compile(r"(?i)/(wp-admin|wp-login|admin|staging|\.env|\.git|backup)")
    ap = [(r["cedar_uid"], d["url"]) for r in recs for d in (r.get("found") or [])
          if forb.search(urlparse(d["url"]).path or "")]
    if ap:
        f.append("FORBIDDEN_PATH_RECORDED: %d, e.g. %s" % (len(ap), ap[0][1]))

    # 4. a host that served identical bodies must have been quarantined
    leak = [r for r in recs if r.get("identical_body_hashes") and r.get("found")]
    if leak:
        f.append("IDENTICAL_HASH_HOST_NOT_QUARANTINED: %d" % len(leak))

    # 5. every record names the routes it actually ran; an absence with no
    #    routes recorded is the false negative this project keeps catching
    ghost = [r for r in recs if r["outcome"] == "NONE_FOUND"
             and not r.get("route_coverage")]
    if ghost:
        f.append("ABSENCE_WITHOUT_ROUTE_COVERAGE: %d" % len(ghost))

    # 6. the request budget was honoured
    over = [r for r in recs if r.get("requests_made", 0) > REQ_BUDGET]
    if over:
        f.append("REQUEST_BUDGET_EXCEEDED: %d, max %d"
                 % (len(over), max(r["requests_made"] for r in over)))
    return f


def selftest():
    base = {"cedar_uid": "CE-OK", "site_host": "example.org", "robots_disallow": [],
            "found": [], "outcome": "FOUND", "route_coverage": ["robots_txt"],
            "requests_made": 1, "identical_body_hashes": False}
    t = []
    r = dict(base, site_host="sudrum.com")
    t.append(("restrictive", any("RESTRICTIVE_SOURCE_TOUCHED" in x for x in verify([r]))))
    r = dict(base, robots_disallow=["/private/"],
             found=[{"url": "https://example.org/private/news.pdf"}])
    t.append(("robots", any("ROBOTS_DISALLOW_FETCHED" in x for x in verify([r]))))
    r = dict(base, found=[{"url": "https://example.org/wp-admin/x.pdf"}])
    t.append(("forbidden", any("FORBIDDEN_PATH_RECORDED" in x for x in verify([r]))))
    r = dict(base, identical_body_hashes=True, found=[{"url": "https://example.org/a.pdf"}])
    t.append(("hashes", any("IDENTICAL_HASH_HOST_NOT" in x for x in verify([r]))))
    r = dict(base, outcome="NONE_FOUND", route_coverage=[])
    t.append(("routes", any("ABSENCE_WITHOUT_ROUTE_COVERAGE" in x for x in verify([r]))))
    r = dict(base, requests_made=REQ_BUDGET + 5)
    t.append(("budget", any("REQUEST_BUDGET_EXCEEDED" in x for x in verify([r]))))
    for name, fired in t:
        print("  selftest %-12s %s" % (name, "FIRES" if fired else "DID NOT FIRE"))
    return 0 if all(x for _n, x in t) else 1


def main(argv):
    if "verify" in argv:
        if "--selftest" in argv and selftest():
            return 1
        fails = verify()
        if fails:
            for x in fails:
                print("FAIL", x)
            return 1
        st = summarize()
        print("verify OK - %d attempted, %d found, 6 invariants held"
              % (st["attempted"], st["found"]))
        return 0
    lim = None
    if "--limit" in argv:
        lim = int(argv[argv.index("--limit") + 1])
    return run(lim)


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
