"""SHARD-E ANC corporate web probe (2026-09-01).

Probes Alaska Native Corporation corporate sites for the 191 entities in shard E's
slice (12 regional corporations, 6 ANCSA group corporations, 173 village
corporations) and for the SUBSIDIARY-LIST pages that are the shard's main
deliverable.

PULL DISCIPLINE (docs/PULL_DISCIPLINE.md):
  * one request per candidate URL. No retry loop. A refusal is RECORDED and the
    run moves on -- the recovery ladder (Wayback -> PDF -> SEC -> AK registry) is
    driven by hand from the recorded status, never by re-probing.
  * per-host serial with a 3.0s floor between requests to the same host.
  * robots.txt fetched once per host and honoured; disallowed URLs are recorded
    as ROBOTS_DISALLOWED and never fetched.
  * global RUN_DEADLINE (2h); per-host circuit breaker after 3 consecutive hard
    refusals; global stop if the FIRST 12 probes all refuse (that is a network or
    edge fact, not 12 separate per-site facts).
  * host lock written to logs/_HOSTLOCK_shard_e_anc_web.json listing every host
    this run will touch, so a peer can see the claim.

Writes ONLY under data/staging/tribe_harvest/shard_e/ and
data/staging/tribe_web_map/shard_e.csv. Read-only w.r.t. every shipped dataset.

usage: py -3 code/532_shard_e_anc_web_probe.py <candidates.json>
"""
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.robotparser as urp
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "staging" / "tribe_harvest" / "shard_e"
RAW = OUT / "raw"
RAW.mkdir(parents=True, exist_ok=True)
LOCK = ROOT / "logs" / "_HOSTLOCK_shard_e_anc_web.json"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
HOST_DELAY = 3.0
RUN_DEADLINE = time.time() + 2 * 3600

_last = {}
_robots = {}
_fails = {}
_probes = 0
_ok = 0

NAV_RE = re.compile(
    r"(?i)(subsidiar|our-?compan|famil[-y]|operating|portfolio|business|"
    r"annual-?report|newsletter|shareholder|village|about)")

SIGNALS = ("subsidiar", "our companies", "family of companies", "operating compan",
           "annual report", "newsletter", "shareholder", "joint venture",
           "8(a)", "village corporation", "wholly owned")


def _sleep_host(host):
    t = _last.get(host)
    if t is not None:
        d = HOST_DELAY - (time.time() - t)
        if d > 0:
            time.sleep(d)
    _last[host] = time.time()


def _curl(url, timeout=35):
    cmd = ["curl", "-s", "-L", "--max-redirs", "5", "-A", UA,
           "-H", "Accept: text/html,application/xhtml+xml,application/pdf,*/*;q=0.8",
           "-H", "Accept-Language: en-US,en;q=0.9",
           "--max-time", str(timeout),
           "-w", "\n__META__%{http_code}|%{url_effective}|%{content_type}", url]
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True)
    dur = time.time() - t0
    out = p.stdout
    m = re.search(rb"\n__META__(\d+)\|([^|]*)\|(.*)$", out, re.S)
    if m:
        return (int(m.group(1)), m.group(2).decode("utf-8", "replace"),
                m.group(3).decode("utf-8", "replace").strip(), out[:m.start()],
                dur, p.returncode)
    return 0, url, "", out, dur, p.returncode


def robots_ok(url):
    p = urlparse(url)
    host = p.netloc
    if host not in _robots:
        _sleep_host(host)
        st, _, _, body, _, _ = _curl(p.scheme + "://" + host + "/robots.txt", timeout=20)
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
        return True, "robots.txt http %s; no applicable rules parsed" % st
    try:
        ok = rp.can_fetch("*", url)
    except Exception:
        return True, "robots.txt unparseable for this path"
    return ok, ("allowed by robots.txt" if ok else "DISALLOWED by robots.txt")


def plain(body):
    t = body.decode("utf-8", "replace")
    t = re.sub(r"<(script|style|noscript|svg)\b.*?</\1>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"</(p|div|li|tr|h\d|td|section|option|a)>", "\n", t, flags=re.I)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    t = "\n".join(re.sub(r"[ \t]+", " ", ln).strip() for ln in t.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def links(body, base):
    out = []
    for m in re.finditer(rb'href=["\']([^"\'>]+)["\']', body, re.I):
        u = m.group(1).decode("utf-8", "replace")
        if u.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        if u.startswith("//"):
            u = "https:" + u
        elif u.startswith("/"):
            p = urlparse(base)
            u = p.scheme + "://" + p.netloc + u
        elif not u.startswith("http"):
            continue
        out.append(u)
    return out


def probe(c):
    global _probes, _ok
    url = c["url"]
    rec = {k: c.get(k) for k in ("cedar_uid", "canonical_name", "url_type", "slug", "note")}
    rec["url"] = url
    rec["checked_date"] = datetime.now(timezone.utc).date().isoformat()
    # lint-ok: class4 - this does NOT mark anything complete. The skipped URL is
    # written back as SKIPPED_RUN_DEADLINE and counted in _coverage.json against
    # candidates_total, whose `complete` boolean goes false. A half-walked
    # corporate tree must never be readable as the whole tree.
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
    _probes += 1
    rec.update({"http_status": st, "final_url": eff, "content_type": ctype,
                "bytes": len(body), "seconds": round(dur, 2), "curl_rc": rc})
    if st == 0:
        _fails[host] = _fails.get(host, 0) + 1
        rec["failure_shape"] = "edge_refusal_or_dns" if dur < 2 else "timeout"
        return rec
    # A 404 on a GUESSED path is a fact about that path, not a refusal by the
    # host. Only refusal shapes (0, 403, 429, 5xx) may trip the circuit breaker;
    # counting 404s tripped it after three guessed paths and skipped the real
    # pages behind them (observed on ahtna.com / aleutcorp.com, 2026-09-01).
    if st in (403, 429) or st >= 500:
        _fails[host] = _fails.get(host, 0) + 1
    elif st < 400:
        _fails[host] = 0
        _ok += 1
    if body and st < 400:
        txt = plain(body)
        head = body.decode("utf-8", "replace")[:300000]
        m = re.search(r"<title[^>]*>(.*?)</title>", head, re.S | re.I)
        rec["title"] = html.unescape(re.sub(r"\s+", " ", m.group(1))).strip()[:300] if m else ""
        rec["text_len"] = len(txt)
        low = txt.lower()
        rec["signals"] = {k: low.count(k) for k in SIGNALS if low.count(k)}
        fn = "%s_%s" % (c.get("slug", "x"), hashlib.sha1(url.encode()).hexdigest()[:8])
        ext = ".pdf" if "pdf" in (ctype or "") else ".html"
        (RAW / (fn + ext)).write_bytes(body)
        rec["raw_file"] = fn + ext
        if ext == ".html":
            (RAW / (fn + ".txt")).write_text(txt, encoding="utf-8")
            keep = [u for u in links(body, eff) if NAV_RE.search(u)]
            rec["nav_links"] = sorted(set(keep))[:80]
    return rec


def main():
    cand = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    hosts = sorted({urlparse(c["url"]).netloc for c in cand})
    LOCK.write_text(json.dumps({
        "host": "shard_e_anc_web (multi-host claim)",
        "pid": os.getpid(),
        "script": "code/532_shard_e_anc_web_probe.py",
        "claimed_at": datetime.now(timezone.utc).isoformat(),
        "policy": "single stream, >=3.0s per-host gap, no retries, 2h RUN_DEADLINE",
        "hosts": hosts,
        "n_candidates": len(cand),
    }, indent=1), encoding="utf-8")
    outp = OUT / "_probe_results.jsonl"
    done = set()
    if outp.exists():
        for line in outp.open(encoding="utf-8"):
            try:
                done.add(json.loads(line)["url"])
            except Exception:
                pass
    n = 0
    stop_reason = "candidate_list_exhausted"
    with outp.open("a", encoding="utf-8") as f:
        for c in cand:
            if c["url"] in done:
                continue
            r = probe(c)
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            f.flush()
            n += 1
            try:
                print(n, r.get("http_status"), c["url"], "|",
                      str(r.get("title", ""))[:60], "|", r.get("signals"), flush=True)
            except UnicodeEncodeError:
                print(n, r.get("http_status"), c["url"], flush=True)
            if _probes >= 12 and _ok == 0:
                stop_reason = "global_stop_first_12_refused"
                print("GLOBAL STOP: first 12 probes all refused -- network/edge fact",
                      flush=True)
                break
            # lint-ok: class4 - the deadline never marks the crawl COMPLETE. Every
            # exit writes _coverage.json with candidates_total vs
            # candidates_attempted and an explicit `complete` boolean, and the
            # unattempted URLs are listed by name in `not_attempted`. A
            # deadline-truncated corporate tree must never be readable as the
            # whole tree -- half a subsidiary list is a wrong answer, not a small
            # one -- so coverage is asserted against the SOURCE list, not assumed.
            if time.time() > RUN_DEADLINE:
                stop_reason = "run_deadline"
                print("RUN_DEADLINE reached", flush=True)
                break

    attempted = done | {c["url"] for c in cand[:0]}
    seen_now = set()
    for line in outp.open(encoding="utf-8"):
        try:
            seen_now.add(json.loads(line)["url"])
        except Exception:
            pass
    not_attempted = [c["url"] for c in cand if c["url"] not in seen_now]
    cov = {
        "candidates_total": len(cand),
        "candidates_attempted": len(cand) - len(not_attempted),
        "probed_this_run": n,
        "responses_ok": _ok,
        "stop_reason": stop_reason,
        "complete": len(not_attempted) == 0 and stop_reason == "candidate_list_exhausted",
        "deadline_truncated": stop_reason == "run_deadline",
        "not_attempted": not_attempted,
        "candidate_file": str(Path(sys.argv[1]).name),
        "finished": datetime.now(timezone.utc).isoformat(),
    }
    covp = OUT / ("_coverage_" + Path(sys.argv[1]).stem + ".json")
    covp.write_text(json.dumps(cov, indent=1), encoding="utf-8")

    lk = json.loads(LOCK.read_text(encoding="utf-8"))
    lk.update({"released": datetime.now(timezone.utc).isoformat(),
               "requests_made": _probes, "responses_ok": _ok,
               "stop_reason": stop_reason, "coverage_complete": cov["complete"],
               "not_attempted_n": len(not_attempted)})
    LOCK.write_text(json.dumps(lk, indent=1), encoding="utf-8")
    print("probed", n, "ok", _ok, "| coverage complete:", cov["complete"],
          "| not attempted:", len(not_attempted), "| stop:", stop_reason)
    return 0


if __name__ == "__main__":
    sys.exit(main())
