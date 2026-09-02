"""SHARD-D tribe web map probe (2026-09-01).

Reads a candidate URL list, checks robots.txt for each host once, fetches the
allowed candidates with curl, stores the raw bytes under
data/staging/tribe_harvest/shard_d/raw/ and emits one JSON line per candidate to
data/staging/tribe_harvest/shard_d/_probe_results.jsonl.

PULL DISCIPLINE
  * One host is touched at most once per candidate; a >=2.5s per-host gap and a
    >=0.8s global gap are enforced.
  * No retry loop. A refusal is recorded with its status/curl exit code and the
    candidate is abandoned.
  * RUN_DEADLINE caps the whole run at 90 minutes.
  * robots.txt is fetched first for every host; a Disallow matching the path for
    User-agent: * marks the candidate ROBOTS_DISALLOW and it is NOT fetched.
  * Read-only with respect to every Cedar dataset. Writes only under
    data/staging/tribe_harvest/shard_d/.

usage: py -3 code/shard_d_web_probe.py [candidates.csv] [--out results.jsonl]
"""
import csv
import datetime
import hashlib
import html as htmlmod
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "data" / "staging" / "tribe_harvest" / "shard_d"
RAW = BASE / "raw"
ROBOTS = RAW / "_robots"
RAW.mkdir(parents=True, exist_ok=True)
ROBOTS.mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

RUN_DEADLINE = time.time() + 90 * 60
HOST_GAP = 2.5
GLOBAL_GAP = 0.8
_last_host = {}
_last_any = [0.0]


def _sleep_for(host):
    now = time.time()
    w = max(_last_host.get(host, 0) + HOST_GAP - now,
            _last_any[0] + GLOBAL_GAP - now, 0)
    if w > 0:
        time.sleep(w)
    _last_host[host] = time.time()
    _last_any[0] = time.time()


def curl(url, timeout=45, max_bytes=6_000_000):
    """Return (status, final_url, body_bytes, curl_exit)."""
    cmd = ["curl", "-sS", "-L", "--compressed", "-A", UA,
           "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,"
                 "application/pdf,application/json,*/*;q=0.8",
           "-H", "Accept-Language: en-US,en;q=0.9",
           "--max-time", str(timeout), "--max-filesize", str(max_bytes),
           "--retry", "0",
           "-w", "\n__CEDARMETA__%{http_code}|%{url_effective}", url]
    p = subprocess.run(cmd, capture_output=True)
    out = p.stdout
    m = re.search(rb"\n__CEDARMETA__(\d+)\|(.*)$", out, re.S)
    if m:
        return int(m.group(1)), m.group(2).decode("utf-8", "replace").strip(), out[:m.start()], p.returncode
    return 0, url, out, p.returncode


_robots_cache = {}


def robots_for(host, scheme="https"):
    if host in _robots_cache:
        return _robots_cache[host]
    _sleep_for(host)
    st, _fu, body, _rc = curl(f"{scheme}://{host}/robots.txt", timeout=25)
    txt = body.decode("utf-8", "replace") if st == 200 else ""
    fn = ROBOTS / (re.sub(r"[^a-z0-9.-]", "_", host.lower()) + ".txt")
    fn.write_bytes(body if st == 200 else b"")
    rules = []
    if st == 200 and len(txt) < 200_000:
        applies = False
        for line in txt.splitlines():
            line = line.split("#", 1)[0].strip()
            if not line or ":" not in line:
                continue
            k, v = line.split(":", 1)
            k, v = k.strip().lower(), v.strip()
            if k == "user-agent":
                applies = (v == "*")
            elif applies and k == "disallow" and v:
                rules.append(v)
            elif applies and k == "allow" and v:
                rules.append("ALLOW:" + v)
    _robots_cache[host] = (st, rules)
    return _robots_cache[host]


def robots_blocks(host, path):
    st, rules = robots_for(host)
    if st != 200:
        return None  # unreadable robots -> not treated as a block, noted instead
    allows = [r[6:] for r in rules if r.startswith("ALLOW:")]
    disallows = [r for r in rules if not r.startswith("ALLOW:")]
    best_a = max((len(a) for a in allows if path.startswith(a)), default=-1)
    best_d = max((len(d) for d in disallows if d == "/" or path.startswith(d)), default=-1)
    return best_d > best_a and best_d >= 0


TAGSTRIP = re.compile(r"<(script|style|noscript|svg)\b.*?</\1>", re.S | re.I)


def page_text(body):
    t = body.decode("utf-8", "replace")
    t = TAGSTRIP.sub(" ", t)
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"</(p|div|li|tr|td|h[1-6]|section)>", "\n", t, flags=re.I)
    t = htmlmod.unescape(re.sub(r"<[^>]+>", " ", t))
    t = re.sub(r"[ \t\xa0]+", " ", t)
    return "\n".join(l.strip() for l in t.split("\n") if l.strip())


def title_of(body):
    t = body.decode("utf-8", "replace")
    m = re.search(r"<title[^>]*>(.*?)</title>", t, re.S | re.I)
    if not m:
        m = re.search(r'<meta[^>]+property=["\']og:site_name["\'][^>]+content=["\']([^"\']+)', t, re.I)
    return htmlmod.unescape(re.sub(r"\s+", " ", m.group(1)).strip())[:300] if m else ""


def meta_desc(body):
    t = body.decode("utf-8", "replace")
    m = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']*)', t, re.I)
    return htmlmod.unescape(re.sub(r"\s+", " ", m.group(1)).strip())[:500] if m else ""


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    cand_path = Path(args[0]) if args else BASE / "_candidates.csv"
    out_path = BASE / "_probe_results.jsonl"
    for i, a in enumerate(sys.argv):
        if a == "--out":
            out_path = Path(sys.argv[i + 1])

    done = set()
    if out_path.exists():
        for line in out_path.open(encoding="utf-8"):
            try:
                r = json.loads(line)
                done.add((r["tribe_id"], r["url_type"], r["candidate_url"]))
            except Exception:
                pass

    rows = list(csv.DictReader(cand_path.open(encoding="utf-8-sig")))
    today = datetime.date.today().isoformat()
    # expected_total is the SOURCE-reported size of this run's work: every
    # candidate row in the file. n_attempted is what this process actually got
    # to. The two are compared at the end and written to _run_state.json, so a
    # deadline-truncated run can NEVER be read as complete coverage of a slice.
    expected_total = len(rows)
    n_skipped_already_done = sum(
        1 for r in rows if (r["tribe_id"], r["url_type"], r["url"]) in done)
    fh = out_path.open("a", encoding="utf-8")
    n_new = 0
    deadline_hit = False
    n_unattempted = 0
    for r in rows:
        key = (r["tribe_id"], r["url_type"], r["url"])
        if key in done:
            continue
        if deadline_hit or time.time() > RUN_DEADLINE:
            deadline_hit = True
            n_unattempted += 1
            continue
        u = urlparse(r["url"])
        host, path = u.netloc, (u.path or "/")
        rec = {"tribe_id": r["tribe_id"], "url_type": r["url_type"],
               "candidate_url": r["url"], "host": host, "checked_date": today}
        blocked = robots_blocks(host, path)
        rec["robots_status"] = _robots_cache[host][0]
        if blocked is True:
            rec.update(outcome="ROBOTS_DISALLOW", http_status="", raw_file="")
            fh.write(json.dumps(rec) + "\n"); fh.flush(); n_new += 1
            print(f"{r['tribe_id']:16} {r['url_type']:16} ROBOTS_DISALLOW {r['url']}")
            continue
        _sleep_for(host)
        st, final, body, rc = curl(r["url"])
        rec["http_status"] = st
        rec["curl_exit"] = rc
        rec["final_url"] = final
        rec["bytes"] = len(body)
        if st and 200 <= st < 400 and body:
            h = hashlib.sha1((r["tribe_id"] + r["url"]).encode()).hexdigest()[:8]
            ext = ".pdf" if body[:4] == b"%PDF" else ".html"
            fn = f"{r['tribe_id']}_{r['url_type']}_{h}{ext}"
            (RAW / fn).write_bytes(body)
            rec["raw_file"] = f"raw/{fn}"
            if ext == ".html":
                txt = page_text(body)
                rec["title"] = title_of(body)
                rec["meta_description"] = meta_desc(body)
                rec["text_head"] = txt[:6000]
                rec["text_len"] = len(txt)
            else:
                rec["title"] = ""
                rec["text_head"] = ""
            rec["outcome"] = "FETCHED"
        else:
            rec["outcome"] = "REFUSED" if st else "NO_RESPONSE"
            rec["raw_file"] = ""
            rec["error_head"] = body[:300].decode("utf-8", "replace")
        fh.write(json.dumps(rec) + "\n"); fh.flush(); n_new += 1
        print(f"{r['tribe_id']:16} {r['url_type']:16} {rec['outcome']:14} {st:>4} {r['url']}")
    fh.close()

    # ---- coverage accounting: retrieved vs the total this run was asked for.
    # Written every run, whether or not the deadline bit. `coverage_complete` is
    # false unless every candidate in the file was attempted; a truncated run
    # therefore cannot be mistaken for a finished slice by any later reader.
    n_attempted = n_new
    coverage_complete = (n_attempted + n_skipped_already_done) == expected_total \
        and not deadline_hit
    state = {
        "candidates_file": str(cand_path),
        "expected_total": expected_total,
        "already_on_disk_skipped": n_skipped_already_done,
        "attempted_this_run": n_attempted,
        "unattempted_after_deadline": n_unattempted,
        "deadline_hit": deadline_hit,
        "coverage_complete": coverage_complete,
        "results_file": str(out_path),
        "finished_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    # APPENDED, never rewritten: every run of this script leaves its own record,
    # so a later run that skips everything already on disk cannot overwrite the
    # run that actually did the fetching with a zeroed summary.
    with (BASE / "_run_state.jsonl").open("a", encoding="utf-8") as sf:
        sf.write(json.dumps(state) + "\n")
    print(f"\n{n_new} new probes -> {out_path}")
    print(f"coverage: attempted {n_attempted} + already-on-disk "
          f"{n_skipped_already_done} of expected_total {expected_total}; "
          f"coverage_complete={coverage_complete}")
    if not coverage_complete:
        print(f"INCOMPLETE: {n_unattempted} candidates were never attempted "
              f"(RUN_DEADLINE). This run does NOT cover its candidate list.",
              file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
