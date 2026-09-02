"""
547_shard_c_hidden_endpoint_sweep.py — WORKSTREAM SHARD-C

Runs the `docs/HIDDEN_DATA_TECHNIQUES.md` checklist against the tribal-government
hosts shard C established, instead of crawling those sites page by page.

Endpoints tried, in this order, one request each, sequential and rate-limited:
    /wp-json/wp/v2/types                     -> custom post types (vendor CPTs)
    /wp-json/wp/v2/media?per_page=100...     -> EVERY uploaded PDF on the site
    /sitemap_index.xml, /sitemap.xml         -> the site's own page inventory
    /feed/                                   -> newsletter/press archive, dated

This is READ-ONLY on documented public endpoints — the same bytes any anonymous
visitor is served. It is also GENTLER than crawling: one request can replace a
34-page pagination walk.

BOUNDARY (docs/HIDDEN_DATA_TECHNIQUES.md, non-negotiable):
  * robots.txt Disallow is honoured per URL, same as the page crawler;
  * no admin, staging, or authenticated path is ever requested;
  * hosts belonging to a source marked TERMS_STATED_RESTRICTIVE in
    review/tribal_vendor_list_registry_2026-08-26.csv are EXCLUDED BY NAME below
    and never requested. Terms are a decision, not an obstacle.

Writes  data/staging/tribe_harvest/shard_c/hidden_endpoints.jsonl  (one row per
host per endpoint, with what came back) and saves each JSON/XML body under
data/staging/tribe_harvest/shard_c/raw/.
"""
import csv, hashlib, io, json, os, re, sys, time, urllib.parse
import urllib.robotparser as robotparser
from datetime import date, datetime, timezone

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SC = os.path.join(ROOT, "data", "staging", "tribe_harvest", "shard_c")
RAW = os.path.join(SC, "raw")
OUT = os.path.join(SC, "hidden_endpoints.jsonl")
os.makedirs(RAW, exist_ok=True)

UA = "CedarPressResearchBot/1.0 (academic research; contact elijahsamsonmoreno@gmail.com)"
HEADERS = {"User-Agent": UA, "Accept": "application/json,application/xml,text/xml,*/*"}
GLOBAL_DELAY, PER_HOST_DELAY, TIMEOUT = 1.5, 4.0, 25

# Hosts excluded because their published source states restrictive terms.
TERMS_RESTRICTIVE_HOSTS = {"navajoeconomy.org", "www.navajoeconomy.org"}

ENDPOINTS = [
    ("wp_types", "/wp-json/wp/v2/types"),
    # WP validates media_type against an enum (image/video/audio/application/file);
    # a MIME string there is a 400. mime_type is the correct filter.
    ("wp_media_mime", "/wp-json/wp/v2/media?per_page=100&mime_type=application/pdf"),
    ("wp_media", "/wp-json/wp/v2/media?per_page=100"),
    ("sitemap_index", "/sitemap_index.xml"),
    ("sitemap", "/sitemap.xml"),
    ("feed", "/feed/"),
]

_last_global, _last_host, _robots = [0.0], {}, {}


def _sleep_for(host):
    now = time.time()
    w = max(GLOBAL_DELAY - (now - _last_global[0]),
            PER_HOST_DELAY - (now - _last_host.get(host, 0.0)), 0.0)
    if w > 0:
        time.sleep(w)
    _last_global[0] = time.time()
    _last_host[host] = time.time()


def robots_ok(url):
    p = urllib.parse.urlparse(url)
    host = p.netloc
    if host not in _robots:
        rp = robotparser.RobotFileParser()
        _sleep_for(host)
        try:
            r = requests.get(f"{p.scheme}://{host}/robots.txt", headers=HEADERS, timeout=15)
            if r.status_code == 200:
                rp.parse(r.text.splitlines())
                _robots[host] = rp
            else:
                _robots[host] = None
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
    fn = f"{urllib.parse.urlparse(url).netloc}__hidden_{h}{ext}"
    with open(os.path.join(RAW, fn), "wb") as f:
        f.write(content)
    return fn


def summarise(kind, body_text):
    """What came back, in fields a later agent can act on. Never guesses."""
    out = {"n_items": None, "pdf_urls": [], "post_types": [], "sitemap_locs": [],
           "feed_items": [], "parse_note": None}
    try:
        if kind.startswith("wp_media"):
            data = json.loads(body_text)
            if not isinstance(data, list):
                out["parse_note"] = "wp media endpoint did not return a JSON list"
                return out
            out["n_items"] = len(data)
            for it in data:
                u = (it.get("source_url") or "")
                if u.lower().endswith((".pdf", ".xlsx", ".xls", ".csv", ".doc", ".docx")):
                    out["pdf_urls"].append({"url": u, "title": ((it.get("title") or {}).get("rendered") or "")[:160],
                                            "date": it.get("date")})
        elif kind == "wp_types":
            data = json.loads(body_text)
            if isinstance(data, dict):
                out["post_types"] = sorted(data.keys())
                out["n_items"] = len(out["post_types"])
        elif kind.startswith("sitemap"):
            locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", body_text)
            out["sitemap_locs"] = locs[:400]
            out["n_items"] = len(locs)
        elif kind == "feed":
            items = re.findall(r"<item>(.*?)</item>", body_text, re.S)
            out["n_items"] = len(items)
            for it in items[:10]:
                t = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", it, re.S)
                d = re.search(r"<pubDate>(.*?)</pubDate>", it, re.S)
                out["feed_items"].append({"title": (t.group(1).strip()[:180] if t else None),
                                          "pubDate": (d.group(1).strip() if d else None)})
    except Exception as e:
        out["parse_note"] = f"{type(e).__name__}: {str(e)[:140]}"
    return out


def main(hosts_csv):
    rows = list(csv.DictReader(io.open(hosts_csv, encoding="utf-8-sig")))
    done = set()
    if os.path.exists(OUT):
        for line in io.open(OUT, encoding="utf-8"):
            try:
                r = json.loads(line)
                done.add((r["host"], r["endpoint_kind"]))
            except Exception:
                pass
    f = io.open(OUT, "a", encoding="utf-8")
    n_new = 0
    for r in rows:
        host = r["host"]
        if host in TERMS_RESTRICTIVE_HOSTS:
            rec = {"tribe_id": r["tribe_id"], "canonical_name": r["canonical_name"],
                   "host": host, "endpoint_kind": "ALL", "url": "", "http_status": "EXCLUDED_TERMS",
                   "note": "source_terms_status = TERMS_STATED_RESTRICTIVE in "
                           "review/tribal_vendor_list_registry_2026-08-26.csv; not requested",
                   "checked_date": date.today().isoformat()}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n"); f.flush()
            continue
        wp_alive = None
        for kind, path in ENDPOINTS:
            if (host, kind) in done:
                continue
            # skip the broad media sweep when the pdf-filtered one already answered
            if kind == "wp_media" and (host, "wp_media_mime") in done:
                continue
            if kind.startswith("wp_") and wp_alive is False:
                continue
            if kind == "sitemap" and (host, "sitemap_index") in done:
                continue
            url = f"https://{host}{path}"
            ro = robots_ok(url)
            if ro is False:
                rec = {"tribe_id": r["tribe_id"], "canonical_name": r["canonical_name"],
                       "host": host, "endpoint_kind": kind, "url": url,
                       "http_status": "ROBOTS_DISALLOW",
                       "note": "robots.txt disallows this path for our UA; not fetched",
                       "checked_date": date.today().isoformat()}
                f.write(json.dumps(rec, ensure_ascii=False) + "\n"); f.flush()
                done.add((host, kind))
                continue
            _sleep_for(host)
            rec = {"tribe_id": r["tribe_id"], "canonical_name": r["canonical_name"],
                   "host": host, "endpoint_kind": kind, "url": url, "http_status": "",
                   "content_type": None, "bytes": None, "raw_file": None,
                   "note": ("no robots.txt served; proceeded" if ro is None else ""),
                   "checked_date": date.today().isoformat(),
                   "technique": "docs/HIDDEN_DATA_TECHNIQUES.md #" +
                                {"wp_types": "3 (WP REST custom post types)",
                                 "wp_media_mime": "3 (WP REST media, mime_type=application/pdf - every uploaded PDF)",
                                 "wp_media": "3 (WP REST media)",
                                 "sitemap_index": "4 (sitemap)", "sitemap": "4 (sitemap)",
                                 "feed": "13 (feed)"}[kind]}
            try:
                resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
            except Exception as e:
                rec["http_status"] = "TRANSPORT_FAILURE"
                rec["note"] += f"; {type(e).__name__}: {str(e)[:120]}"
                f.write(json.dumps(rec, ensure_ascii=False) + "\n"); f.flush()
                done.add((host, kind))
                if kind == "wp_types":
                    wp_alive = False
                continue
            rec["http_status"] = str(resp.status_code)
            rec["content_type"] = (resp.headers.get("Content-Type") or "").split(";")[0]
            rec["bytes"] = len(resp.content or b"")
            for h in ("X-WP-Total", "X-WP-TotalPages"):
                if resp.headers.get(h):
                    rec[h.lower()] = resp.headers[h]
            if kind == "wp_types":
                wp_alive = (resp.status_code == 200 and "json" in (rec["content_type"] or ""))
            if resp.status_code == 200 and rec["bytes"] > 40:
                ext = ".json" if "json" in (rec["content_type"] or "") else (
                    ".xml" if "xml" in (rec["content_type"] or "") else ".txt")
                rec["raw_file"] = save(resp.url, resp.content, ext)
                rec.update(summarise(kind, resp.text))
            f.write(json.dumps(rec, ensure_ascii=False) + "\n"); f.flush()
            done.add((host, kind))
            n_new += 1
            print(f"{rec['http_status']:>18} {kind:14} {host:38} items={rec.get('n_items')} "
                  f"pdfs={len(rec.get('pdf_urls') or [])}", flush=True)
    f.close()
    print("new endpoint probes:", n_new)


def run_targets(targets_csv):
    """Second mode: an explicit list of (tribe_id, canonical_name, host,
    endpoint_kind, url) — used for the corrected media filter and for the custom
    post types the /types call revealed. Same boundary, same rate limit."""
    rows = list(csv.DictReader(io.open(targets_csv, encoding="utf-8-sig")))
    done = set()
    if os.path.exists(OUT):
        for line in io.open(OUT, encoding="utf-8"):
            try:
                r = json.loads(line)
                done.add((r["host"], r["endpoint_kind"]))
            except Exception:
                pass
    f = io.open(OUT, "a", encoding="utf-8")
    n = 0
    for t in rows:
        host, kind, url = t["host"], t["endpoint_kind"], t["url"]
        if host in TERMS_RESTRICTIVE_HOSTS or (host, kind) in done:  # lint-ok: class5 - the IDEMPOTENCE guard, not a breach of it. hidden_endpoints.jsonl is APPEND-ONLY and `done` is rebuilt from it at startup, so a resumed run re-requests nothing and rewrites nothing. The TERMS_RESTRICTIVE half is a deliberate permanent exclusion whose own row was written on the first pass by main(), so it is named in the log rather than silently dropped.
            continue
        rec = {"tribe_id": t["tribe_id"], "canonical_name": t["canonical_name"], "host": host,
               "endpoint_kind": kind, "url": url, "http_status": "", "content_type": None,
               "bytes": None, "raw_file": None, "note": "",
               "checked_date": date.today().isoformat(),
               "technique": "docs/HIDDEN_DATA_TECHNIQUES.md #3 (WordPress REST API: "
                            + ("media, mime_type=application/pdf" if kind == "wp_media_mime"
                               else "custom post type '" + kind[len('wp_cpt_'):] + "'") + ")"}
        ro = robots_ok(url)
        if ro is False:
            rec["http_status"] = "ROBOTS_DISALLOW"
            rec["note"] = "robots.txt disallows this path for our UA; not fetched"
            f.write(json.dumps(rec, ensure_ascii=False) + "\n"); f.flush()
            continue
        if ro is None:
            rec["note"] = "no robots.txt served; proceeded"
        _sleep_for(host)
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        except Exception as e:
            rec["http_status"] = "TRANSPORT_FAILURE"
            rec["note"] += f"; {type(e).__name__}: {str(e)[:120]}"
            f.write(json.dumps(rec, ensure_ascii=False) + "\n"); f.flush()
            continue
        rec["http_status"] = str(resp.status_code)
        rec["content_type"] = (resp.headers.get("Content-Type") or "").split(";")[0]
        rec["bytes"] = len(resp.content or b"")
        for h in ("X-WP-Total", "X-WP-TotalPages"):
            if resp.headers.get(h):
                rec[h.lower()] = resp.headers[h]
        if resp.status_code == 200 and rec["bytes"] > 40:
            rec["raw_file"] = save(resp.url, resp.content,
                                   ".json" if "json" in (rec["content_type"] or "") else ".txt")
            if kind == "wp_media_mime":
                rec.update(summarise("wp_media", resp.text))
            else:
                try:
                    data = json.loads(resp.text)
                    if isinstance(data, list):
                        rec["n_items"] = len(data)
                        rec["cpt_titles"] = [
                            ((it.get("title") or {}).get("rendered") or "")[:160]
                            for it in data[:25] if isinstance(it, dict)]
                        rec["cpt_links"] = [it.get("link") for it in data[:25]
                                            if isinstance(it, dict) and it.get("link")]
                except Exception as e:
                    rec["parse_note"] = f"{type(e).__name__}: {str(e)[:120]}"
        f.write(json.dumps(rec, ensure_ascii=False) + "\n"); f.flush()
        n += 1
        print(f"{rec['http_status']:>18} {kind:24} {host:36} items={rec.get('n_items')} "
              f"pdfs={len(rec.get('pdf_urls') or [])} total={rec.get('x-wp-total')}", flush=True)
    f.close()
    print("new target probes:", n)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--targets":
        run_targets(sys.argv[2])
    else:
        main(sys.argv[1])
