"""SHARD-B tribe web map probe (2026-09-01).

Verifies candidate tribal-government / casino / TERO / gaming-authority URLs for the
71 gaming tribes in shard B's slice (gaming_facilities.csv, distinct tribe_id sorted,
rows 72-142).

PULL DISCIPLINE (docs/PULL_DISCIPLINE.md):
  * one request per candidate URL, no retry loop; a refusal is recorded, not retried
  * per-host serial with a 2.5s floor between requests to the same host
  * robots.txt fetched once per host and honoured for our UA; disallowed URLs are
    recorded as ROBOTS_DISALLOWED and never fetched
  * global RUN_DEADLINE; per-host circuit breaker after 3 consecutive hard refusals
  * writes raw bytes to data/staging/tribe_harvest/shard_b/raw/ and a probe jsonl

Read-only with respect to every shipped dataset. Writes only under
data/staging/tribe_harvest/shard_b/ and data/staging/tribe_web_map/.
"""
import csv, json, os, re, sys, time, html, hashlib, datetime, subprocess
import urllib.robotparser as urp
from urllib.parse import urlparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "staging" / "tribe_harvest" / "shard_b"
RAW = OUT / "raw"
RAW.mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
ROBOTS_UA = "*"
HOST_DELAY = 2.5
RUN_DEADLINE = time.time() + 3 * 3600

_last = {}
_robots = {}
_fails = {}


def _sleep_host(host):
    t = _last.get(host)
    if t is not None:
        d = HOST_DELAY - (time.time() - t)
        if d > 0:
            time.sleep(d)
    _last[host] = time.time()


def _curl(url, timeout=40, head=False):
    cmd = ["curl", "-s", "-L", "--max-redirs", "5", "-A", UA,
           "-H", "Accept: text/html,application/xhtml+xml,application/pdf,*/*;q=0.8",
           "-H", "Accept-Language: en-US,en;q=0.9",
           "--max-time", str(timeout),
           "-w", "\n__META__%{http_code}|%{url_effective}|%{content_type}"]
    if head:
        cmd.append("-I")
    cmd.append(url)
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True)
    dur = time.time() - t0
    out = p.stdout
    m = re.search(rb"\n__META__(\d+)\|([^|]*)\|(.*)$", out, re.S)
    if m:
        status = int(m.group(1))
        eff = m.group(2).decode("utf-8", "replace")
        ctype = m.group(3).decode("utf-8", "replace").strip()
        body = out[:m.start()]
    else:
        status, eff, ctype, body = 0, url, "", out
    return status, eff, ctype, body, dur, p.returncode


def robots_ok(url):
    """(allowed, note). Fetch robots.txt once per host."""
    p = urlparse(url)
    host = p.netloc
    if host not in _robots:
        _sleep_host(host)
        st, _, _, body, _, _ = _curl(f"{p.scheme}://{host}/robots.txt", timeout=20)
        rp = urp.RobotFileParser()
        if st == 200 and body:
            try:
                rp.parse(body.decode("utf-8", "replace").splitlines())
            except Exception:
                rp = None
        else:
            rp = None
        _robots[host] = (rp, st)
    rp, st = _robots[host]
    if rp is None:
        return True, f"robots.txt http {st}; no applicable rules parsed"
    try:
        ok = rp.can_fetch(ROBOTS_UA, url)
    except Exception:
        return True, "robots.txt unparseable for this path"
    return ok, ("allowed by robots.txt" if ok else "DISALLOWED by robots.txt")


def _title(body):
    t = body.decode("utf-8", "replace")[:400000]
    m = re.search(r"<title[^>]*>(.*?)</title>", t, re.S | re.I)
    ti = html.unescape(re.sub(r"\s+", " ", m.group(1))).strip() if m else ""
    d = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', t, re.S | re.I)
    de = html.unescape(re.sub(r"\s+", " ", d.group(1))).strip() if d else ""
    return ti[:300], de[:400]


def plain(body, limit=None):
    t = body.decode("utf-8", "replace")
    t = re.sub(r"<(script|style|noscript|svg)\b.*?</\1>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"</(p|div|li|tr|h\d|td|section)>", "\n", t, flags=re.I)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    t = "\n".join(re.sub(r"[ \t]+", " ", l).strip() for l in t.split("\n"))
    t = re.sub(r"\n{3,}", "\n\n", t).strip()
    return t[:limit] if limit else t


def probe(url, tokens, slug, save=True, note=""):
    """Fetch one URL. tokens = evidence strings to look for in the page text."""
    rec = {"url": url, "checked_date": datetime.date.today().isoformat()}
    if time.time() > RUN_DEADLINE:
        rec["http_status"] = "SKIPPED_RUN_DEADLINE"
        return rec
    host = urlparse(url).netloc
    if _fails.get(host, 0) >= 3:
        rec["http_status"] = "SKIPPED_HOST_CIRCUIT_BREAKER"
        return rec
    ok, rnote = robots_ok(url)
    rec["robots_note"] = rnote
    if not ok:
        rec["http_status"] = "ROBOTS_DISALLOWED"
        return rec
    _sleep_host(host)
    st, eff, ctype, body, dur, rc = _curl(url)
    rec.update({"http_status": st, "final_url": eff, "content_type": ctype,
                "bytes": len(body), "seconds": round(dur, 2), "curl_rc": rc})
    if st in (0,) or (st == 0 and dur < 1.5):
        _fails[host] = _fails.get(host, 0) + 1
        rec["failure_shape"] = "edge_refusal_or_dns" if dur < 2 else "timeout"
        return rec
    if st >= 400:
        _fails[host] = _fails.get(host, 0) + 1
    else:
        _fails[host] = 0
    if body and st < 400:
        ti, de = _title(body)
        rec["title"] = ti
        rec["meta_description"] = de
        txt = plain(body)
        low = txt.lower()
        rec["token_hits"] = {k: (low.count(k.lower())) for k in tokens}
        hits = []
        for k in tokens:
            i = low.find(k.lower())
            if i >= 0:
                hits.append(re.sub(r"\s+", " ", txt[max(0, i - 90):i + 130]).strip())
        rec["evidence_quotes"] = hits[:4]
        rec["text_len"] = len(txt)
        if save:
            fn = f"{slug}_{hashlib.sha1(url.encode()).hexdigest()[:8]}"
            ext = ".pdf" if "pdf" in (ctype or "") else ".html"
            (RAW / (fn + ext)).write_bytes(body)
            rec["raw_file"] = fn + ext
            if ext == ".html":
                (RAW / (fn + ".txt")).write_text(txt, encoding="utf-8")
    if note:
        rec["note"] = note
    return rec


def main():
    cand = json.loads((OUT / "_candidates.json").read_text(encoding="utf-8"))
    outp = OUT / "_probe_results.jsonl"
    done = set()
    if outp.exists():
        for line in outp.open(encoding="utf-8"):
            try:
                done.add(json.loads(line)["url"])
            except Exception:
                pass
    n = 0
    with outp.open("a", encoding="utf-8") as f:
        for c in cand:
            if c["url"] in done:
                continue
            r = probe(c["url"], c.get("tokens", []), c.get("slug", "x"),
                      save=c.get("save", True), note=c.get("note", ""))
            r["tribe_id"] = c.get("tribe_id")
            r["url_type"] = c.get("url_type")
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            f.flush()
            n += 1
            print(n, r.get("http_status"), c["url"], "|", str(r.get("title", ""))[:70],
                  "|", r.get("token_hits"), flush=True)
            if time.time() > RUN_DEADLINE:
                print("RUN_DEADLINE reached", flush=True)
                break
    print("probed", n)


if __name__ == "__main__":
    main()
