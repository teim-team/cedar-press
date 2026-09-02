#!/usr/bin/env python3
"""
Cedar Press - SHARD F: one polite fetcher, used by every step of this shard.

PULL DISCIPLINE (docs/PULL_DISCIPLINE.md)
-----------------------------------------
* One process. This shard runs exactly one fetcher and it is this file.
* robots.txt is fetched once per host, cached, and OBEYED. A disallowed path is
  recorded as http_status "robots_disallow" and skipped - never fetched.
* >= MIN_GAP seconds between requests to the SAME host, always.
* Three failure shapes are distinguished and recorded, not collapsed:
    edge block   sub-second connection reset      -> stop this host for the run
    throttle     429 / Retry-After                -> honour it, once, then give up
    server slow  timeout                          -> one retry
* RUN_DEADLINE bounds the run, not just the rate.
* Every response body is written to raw/ so nothing needs re-fetching, and the
  evidence survives the session.

Usage:
    py -3 code/shard_f_fetch.py <url> [<url> ...]         fetch and print status
    py -3 code/shard_f_fetch.py --text <url>              fetch and print page text
    py -3 code/shard_f_fetch.py --links <url>             fetch and print links
"""
import hashlib, html, json, os, re, socket, ssl, sys, time
import urllib.parse
import urllib.request
import urllib.error
import urllib.robotparser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHARD = os.path.join(ROOT, "data", "staging", "tribe_harvest", "shard_f")
RAW = os.path.join(SHARD, "raw")
LOG = os.path.join(SHARD, "_fetch_log.jsonl")
LOCK = os.path.join(ROOT, "logs", "_HOSTLOCK_shard_f_org_web.json")

UA = "CedarPress/1.0 (research; elijahsamsonmoreno@gmail.com)"
HDR = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/pdf,*/*",
    "Accept-Language": "en-US,en;q=0.9",
}
MIN_GAP = 2.0          # seconds between requests to one host
TIMEOUT = 25
RUN_DEADLINE = time.time() + 2 * 3600

_last_hit = {}
_robots = {}
_dead_hosts = set()     # hosts that produced an edge block this run
_ctx = ssl.create_default_context()
_ctx.check_hostname = False
_ctx.verify_mode = ssl.CERT_NONE


def _host(url):
    return urllib.parse.urlsplit(url).netloc.lower()


def _wait(host):
    t = _last_hit.get(host)
    if t is not None:
        d = MIN_GAP - (time.time() - t)
        if d > 0:
            time.sleep(d)
    _last_hit[host] = time.time()


def robots_ok(url):
    """True/False/None. None = robots.txt itself unreachable (treated as allow,
    and recorded as such so the decision is auditable)."""
    host = _host(url)
    sp = urllib.parse.urlsplit(url)
    if host not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        rurl = f"{sp.scheme}://{host}/robots.txt"
        _wait(host)
        try:
            req = urllib.request.Request(rurl, headers=HDR)
            with urllib.request.urlopen(req, timeout=12, context=_ctx) as r:
                body = r.read(200000).decode("utf-8", "replace")
            rp.parse(body.splitlines())
            _robots[host] = rp
        except Exception:
            _robots[host] = None
    rp = _robots[host]
    if rp is None:
        return None
    try:
        return rp.can_fetch(UA, url)
    except Exception:
        return None


def _rawname(url):
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
    base = re.sub(r"[^a-z0-9]+", "_", _host(url).replace("www.", ""))[:40]
    ext = ".pdf" if url.lower().split("?")[0].endswith(".pdf") else ".html"
    return f"{base}_{h}{ext}"


def fetch(url, force=False):
    """Returns a dict; never raises. Writes the body to raw/ and appends to the log."""
    rec = {
        "url": url,
        "checked_date": time.strftime("%Y-%m-%d"),
        "http_status": None,
        "final_url": None,
        "raw_file": None,
        "bytes": 0,
        "seconds": None,
        "failure_shape": None,
        "robots_note": None,
    }
    host = _host(url)

    if time.time() > RUN_DEADLINE:
        rec["http_status"] = "run_deadline"
        return rec
    if host in _dead_hosts:
        rec["http_status"] = "host_edge_block"
        rec["failure_shape"] = "edge_block"
        rec["robots_note"] = "host refused earlier this run; not re-probed"
        _log(rec)
        return rec

    ok = robots_ok(url)
    if ok is False:
        rec["http_status"] = "robots_disallow"
        rec["robots_note"] = "disallowed by robots.txt - NOT fetched"
        _log(rec)
        return rec
    rec["robots_note"] = "allowed by robots.txt" if ok else "robots.txt unreachable; treated as allow"

    out = os.path.join(RAW, _rawname(url))
    if os.path.exists(out) and not force:
        rec["http_status"] = 200
        rec["final_url"] = url
        rec["raw_file"] = os.path.basename(out)
        rec["bytes"] = os.path.getsize(out)
        rec["robots_note"] += " (cached on disk from an earlier request this run)"
        return rec

    for attempt in (1, 2):
        _wait(host)
        t0 = time.time()
        try:
            req = urllib.request.Request(url, headers=HDR)
            with urllib.request.urlopen(req, timeout=TIMEOUT, context=_ctx) as r:
                body = r.read(4_000_000)
                rec["http_status"] = r.status
                rec["final_url"] = r.geturl()
                rec["content_type"] = r.headers.get("Content-Type", "")
            rec["seconds"] = round(time.time() - t0, 2)
            with open(out, "wb") as fh:
                fh.write(body)
            rec["raw_file"] = os.path.basename(out)
            rec["bytes"] = len(body)
            break
        except urllib.error.HTTPError as e:
            rec["http_status"] = e.code
            rec["final_url"] = url
            rec["seconds"] = round(time.time() - t0, 2)
            if e.code == 429:
                rec["failure_shape"] = "throttle"
                ra = e.headers.get("Retry-After")
                if ra and attempt == 1:
                    try:
                        time.sleep(min(float(ra), 120))
                        continue
                    except ValueError:
                        pass
            else:
                rec["failure_shape"] = "http_error"
            break
        except socket.timeout:
            rec["seconds"] = round(time.time() - t0, 2)
            rec["http_status"] = "timeout"
            rec["failure_shape"] = "server_slow"
            if attempt == 1:
                continue
            break
        except Exception as e:
            el = round(time.time() - t0, 2)
            rec["seconds"] = el
            rec["http_status"] = f"{type(e).__name__}"
            rec["error"] = str(e)[:300]
            if el < 1.5 and isinstance(e, (urllib.error.URLError, ConnectionError)):
                rec["failure_shape"] = "edge_block_or_no_such_host"
            else:
                rec["failure_shape"] = "conn_error"
            break

    _log(rec)
    return rec


def _log(rec):
    os.makedirs(SHARD, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")


# Parked / for-sale placeholder pages. A 200 from one of these is NOT a site.
PARKED = re.compile(
    r"domain (is )?for sale|buy this domain|parked (free )?(by|at)"
    r"|godaddy\.com/domainsearch|this domain (may be|is) for sale"
    r"|hugedomains|sedoparking|namecheap parked", re.I)


# ---------------------------------------------------------------- text helpers
_TAG = re.compile(r"<(script|style|noscript|svg)[^>]*>.*?</\1>", re.S | re.I)
_ANY = re.compile(r"<[^>]+>")


def read_raw(rec):
    if not rec.get("raw_file"):
        return ""
    p = os.path.join(RAW, rec["raw_file"])
    if not os.path.exists(p):
        return ""
    return open(p, "rb").read().decode("utf-8", "replace")


def to_text(h):
    h = _TAG.sub(" ", h)
    h = re.sub(r"<br\s*/?>|</(p|div|li|tr|h[1-6]|td)>", "\n", h, flags=re.I)
    h = _ANY.sub(" ", h)
    h = html.unescape(h)
    h = re.sub(r"[ \t\xa0]+", " ", h)
    h = re.sub(r"\n\s*\n+", "\n", h)
    return h.strip()


def title_of(h):
    m = re.search(r"<title[^>]*>(.*?)</title>", h, re.S | re.I)
    return html.unescape(_ANY.sub("", m.group(1))).strip()[:200] if m else ""


def links_of(h, base):
    out = []
    for m in re.finditer(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', h, re.S | re.I):
        href = html.unescape(m.group(1)).strip()
        txt = html.unescape(_ANY.sub(" ", m.group(2)))
        txt = re.sub(r"\s+", " ", txt).strip()
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        out.append((urllib.parse.urljoin(base, href), txt))
    return out


def load_resolved():
    """The best VERIFIED site per entity.

    Prefers `_resolved_sites.json` when the probe has finished, and otherwise
    rebuilds it from `_probe_results.jsonl`, which the probe flushes per row.
    That means every later step works off partial results and nothing is held
    only in a running process's memory.
    """
    rp = os.path.join(SHARD, "_resolved_sites.json")
    pp = os.path.join(SHARD, "_probe_results.jsonl")
    best = {}
    if os.path.exists(pp):
        for line in open(pp, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("verdict") != "verified":
                continue
            u = d["cedar_uid"]
            if u not in best or d["name_match"] > best[u]["name_match"]:
                best[u] = d
    if os.path.exists(rp):
        try:
            for k, v in json.load(open(rp, encoding="utf-8")).items():
                best.setdefault(k, v)
        except Exception:
            pass
    return best


if __name__ == "__main__":
    args = sys.argv[1:]
    mode = "status"
    if args and args[0] in ("--text", "--links"):
        mode = args.pop(0)[2:]
    for u in args:
        r = fetch(u)
        if mode == "status":
            print(json.dumps(r))
        else:
            h = read_raw(r)
            print(f"### {u} -> {r['http_status']} {r.get('final_url')}")
            print(f"### title: {title_of(h)}")
            if mode == "text":
                print(to_text(h)[:20000])
            else:
                for lu, lt in links_of(h, r.get("final_url") or u):
                    print(f"{lt[:80]}\t{lu}")
