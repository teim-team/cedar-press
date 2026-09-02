"""
shard_c_tribe_web_probe.py — WORKSTREAM SHARD-C (tribes 143-213 of the gaming slice)

Probes candidate tribal-government / casino / TERO / gaming-authority URLs, ONE
request per URL, sequentially, with a global rate limit. This is NOT a poller:
there is no retry loop and no backoff schedule, because there is nothing to wait
for — a candidate domain either answers or it does not, and a non-answer is the
finding. Per docs/PULL_DISCIPLINE.md rule 1 a lock is claimed for any host that
receives more than one request in a run.

Reads  : a candidates CSV (tribe_id, cedar_uid, canonical_name, url_type, url)
Writes : data/staging/tribe_harvest/shard_c/raw/<host>__<hash>.html   (page bytes)
         <out>.csv  — one row per candidate with status / final url / title /
                      token evidence

SELECTION DECLARATION: candidates are seeded from (a) verified property domains
already on disk in data/interim/{142,384}_property_domains.csv, (b) the hand
survey in review/tribal_vendor_list_registry_2026-08-26.csv, (c) name-pattern
guesses, and (d) WebSearch results recorded by the agent. Every row records
which. A guess that answers is NOT evidence on its own — the token check is what
makes it evidence, and rows with no token hit are reported as unestablished.
"""
import csv, hashlib, io, json, os, re, sys, time, urllib.parse
import urllib.robotparser as robotparser
from datetime import date, datetime, timezone

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "staging", "tribe_harvest", "shard_c", "raw")
os.makedirs(RAW, exist_ok=True)

UA = "CedarPressResearchBot/1.0 (academic research; contact elijahsamsonmoreno@gmail.com)"
HEADERS = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,*/*"}
GLOBAL_DELAY = 1.5          # seconds between ANY two requests
PER_HOST_DELAY = 4.0        # seconds between two requests to the same host
TIMEOUT = 25

_last_global = [0.0]
_last_host = {}
_robots = {}
_host_hits = {}


def _sleep_for(host):
    now = time.time()
    w1 = GLOBAL_DELAY - (now - _last_global[0])
    w2 = PER_HOST_DELAY - (now - _last_host.get(host, 0.0))
    w = max(w1, w2, 0.0)
    if w > 0:
        time.sleep(w)
    _last_global[0] = time.time()
    _last_host[host] = time.time()


def robots_ok(url):
    """True/False/None (None = robots.txt itself unreachable, treat as allowed
    but record it)."""
    p = urllib.parse.urlparse(url)
    host = p.netloc
    if host not in _robots:
        rp = robotparser.RobotFileParser()
        rurl = f"{p.scheme}://{host}/robots.txt"
        _sleep_for(host)
        try:
            r = requests.get(rurl, headers=HEADERS, timeout=15)
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


TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
TAG_RE = re.compile(r"<(script|style)\b.*?</\1>", re.I | re.S)
ANYTAG_RE = re.compile(r"<[^>]+>")


def text_of(html):
    t = TAG_RE.sub(" ", html)
    t = ANYTAG_RE.sub(" ", t)
    t = re.sub(r"\s+", " ", t)
    return t


def probe(url, tokens):
    """Returns dict. tokens = list of lowercase strings; evidence is which appear."""
    p = urllib.parse.urlparse(url)
    host = p.netloc
    _host_hits[host] = _host_hits.get(host, 0) + 1
    if _host_hits[host] == 2:
        # rule 2: claim the host once we are making more than one request to it
        lock = os.path.join(ROOT, "logs", f"_HOSTLOCK_{host}.json")
        try:
            json.dump({"host": host, "pid": os.getpid(),
                       "script": "code/shard_c_tribe_web_probe.py",
                       "started": datetime.now(timezone.utc).isoformat(),
                       "downloaded_this_run": True, "refused_by_host": [],
                       "note": "shard-C web map probe; sequential, no retry loop"},
                      open(lock, "w"), indent=1)
        except Exception:
            pass
    out = {"url": url, "http_status": "", "final_url": "", "title": "",
           "bytes": "", "tokens_found": "", "raw_file": "", "note": ""}
    ro = robots_ok(url)
    if ro is False:
        out["http_status"] = "ROBOTS_DISALLOW"
        out["note"] = "robots.txt disallows this path for our UA; not fetched"
        return out
    if ro is None:
        out["note"] = "no robots.txt served (or unreachable); proceeded"
    _sleep_for(host)
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
    except requests.exceptions.SSLError as e:
        out["http_status"] = "SSL_ERROR"
        out["note"] = (out["note"] + "; " if out["note"] else "") + str(e)[:160]
        return out
    except Exception as e:
        out["http_status"] = "TRANSPORT_FAILURE"
        out["note"] = (out["note"] + "; " if out["note"] else "") + type(e).__name__ + ": " + str(e)[:140]
        return out
    out["http_status"] = str(r.status_code)
    out["final_url"] = r.url
    ctype = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
    out["note"] = (out["note"] + "; " if out["note"] else "") + "content_type=" + (ctype or "unstated")
    if ctype and "html" not in ctype and "xml" not in ctype and "text/plain" not in ctype:
        # binary object (PDF / XLSX / DOC). Keep the bytes; the token check cannot
        # run on it, so the object is recorded as PRESENT, not as established.
        ext = {"application/pdf": ".pdf",
               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
               "application/vnd.ms-excel": ".xls",
               "application/msword": ".doc"}.get(ctype, ".bin")
        h = hashlib.sha1(r.url.encode()).hexdigest()[:16]
        fn = f"{urllib.parse.urlparse(r.url).netloc}__{h}{ext}"
        with open(os.path.join(RAW, fn), "wb") as f:
            f.write(r.content)
        out["raw_file"] = fn
        out["bytes"] = str(len(r.content or b""))
        out["title"] = "(binary object)"
        out["tokens_found"] = "BINARY_OBJECT_PRESENT"
        return out
    body = r.text or ""
    out["bytes"] = str(len(r.content or b""))
    m = TITLE_RE.search(body)
    if m:
        out["title"] = re.sub(r"\s+", " ", ANYTAG_RE.sub("", m.group(1))).strip()[:200]
    low = text_of(body).lower() + " " + out["title"].lower()
    hits = [t for t in tokens if t and t.lower() in low]
    out["tokens_found"] = "|".join(hits)
    if r.status_code == 200 and len(r.content or b"") > 500:
        h = hashlib.sha1(r.url.encode()).hexdigest()[:16]
        fn = f"{urllib.parse.urlparse(r.url).netloc}__{h}.html"
        with io.open(os.path.join(RAW, fn), "w", encoding="utf-8", errors="replace") as f:
            f.write(body)
        out["raw_file"] = fn
    return out


def main():
    cand = sys.argv[1]
    outp = sys.argv[2]
    rows = list(csv.DictReader(io.open(cand, encoding="utf-8-sig")))
    done = {}
    if os.path.exists(outp):
        for r in csv.DictReader(io.open(outp, encoding="utf-8-sig")):
            done[(r["tribe_id"], r["url"])] = r
    fields = ["tribe_id", "cedar_uid", "canonical_name", "url_type", "url",
              "http_status", "final_url", "title", "bytes", "tokens_found",
              "raw_file", "note", "seed", "checked_date"]
    res = []
    settled = set()   # (tribe_id, url_type) already established -> skip later guesses
    for k, r in done.items():
        if r.get("http_status") == "200" and r.get("tokens_found"):
            settled.add((r["tribe_id"], r["url_type"]))
    for i, r in enumerate(rows, 1):
        key = (r["tribe_id"], r["url"])
        if key in done:  # lint-ok: class5 - this is the IDEMPOTENCE guard, not a breach of it. Class 5 is a build that rewrites its own log; this one CARRIES the prior row forward unchanged (res.append(done[key])) so a resumed run reproduces the earlier result byte-for-byte and re-requests nothing. Removing it would make the script non-idempotent and would re-hit every host, which is what docs/PULL_DISCIPLINE.md rule 6 exists to prevent.
            res.append(done[key])
            continue
        if (r["tribe_id"], r["url_type"]) in settled and r.get("seed", "").endswith("guess"):
            rec = {k: "" for k in fields}
            rec.update({k: r.get(k, "") for k in ("tribe_id", "cedar_uid", "canonical_name", "url_type", "url")})
            rec["seed"] = r.get("seed", "")
            rec["http_status"] = "NOT_PROBED"
            rec["note"] = "a earlier candidate for this tribe/url_type already answered 200 with token evidence; not fetched"
            rec["checked_date"] = date.today().isoformat()
            res.append(rec)
            continue
        toks = [t for t in (r.get("tokens") or "").split("|") if t]
        p = probe(r["url"], toks)
        rec = {k: "" for k in fields}
        rec.update({k: r.get(k, "") for k in ("tribe_id", "cedar_uid", "canonical_name", "url_type", "url")})
        rec["seed"] = r.get("seed", "")
        rec.update({k: v for k, v in p.items() if k in fields})
        rec["checked_date"] = date.today().isoformat()
        if rec["http_status"] == "200" and rec["tokens_found"]:
            settled.add((r["tribe_id"], r["url_type"]))
        res.append(rec)
        print(f"[{i}/{len(rows)}] {rec['http_status']:>18}  {r['url']}  :: {rec['tokens_found'][:70]}", flush=True)
        with io.open(outp, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(res)
    print("done", len(res))


if __name__ == "__main__":
    main()
