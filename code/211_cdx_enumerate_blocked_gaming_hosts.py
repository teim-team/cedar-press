#!/usr/bin/env python3
"""
211_cdx_enumerate_blocked_gaming_hosts.py -- Cedar Press.

TARGET
------
`gaming.az.gov` and `www.nmgcb.org` are recorded in
docs/GAMING_UNIVERSE_REBUILD_2026-08-26.md as 403 / Cloudflare-blocked and
typed NOT_CHECKED. A 403 is a fact about ONE ROUTE, not about the document.

This script does the cheapest bypass first: enumerate EVERY URL the Wayback
Machine holds for those hosts via the CDX API. CDX is an index, not a search
engine -- it turns "I could not find it" into "it does not exist", and it
surfaces PDF paths nobody would guess.

It deliberately enumerates BOTH the current host and the historical host
(`www.azgaming.gov`, `www.gm.state.az.us` for Arizona; `nmgcb.org` without the
`www.` for New Mexico), because a state agency that renames its domain leaves
its old PDFs indexed under the old name only.

WHY NOT `code/95_wayback_az_gaming_status.py`
---------------------------------------------
95 enumerated by EXPLICIT PATH PREFIX (`status`, `contributions`, ...) because a
domain-wide `limit=` silently truncates. That was correct for its target -- the
Gaming Status Report -- and it is exactly wrong for this one: the whole point
here is to find paths we cannot name. This script pages the CDX result with
`resumeKey` instead of capping it with `limit`, so a domain-wide sweep is safe.

DISCIPLINE
----------
web.archive.org: single stream, >=5s gap, exponential backoff, 2h RUN_DEADLINE,
host lock claimed in this script's own name. The existing lock is held by
`code/95_...py` PID 7420 claimed 2026-08-07 -- dead and >6h old, which
PULL_DISCIPLINE rule 2 permits taking over.

WRITES
  data/raw/external/gaming_official/bypass_2026-08-26/cdx_<host>.json
  data/raw/external/gaming_official/bypass_2026-08-26/_cdx_state.json
"""
import json, os, re, sys, time, urllib.request, urllib.error, urllib.parse
from datetime import datetime, timezone
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
OUT = CEDAR / "data" / "raw" / "external" / "gaming_official" / "bypass_2026-08-26"
LOCK = CEDAR / "logs" / "_HOSTLOCK_web.archive.org.json"
UA = {"User-Agent": "CedarPress/1.0 (research; elijahsamsonmoreno@gmail.com)"}

HOSTS = [
    "gaming.az.gov",
    "www.azgaming.gov",
    "azgaming.gov",
    "www.gm.state.az.us",
    "www.nmgcb.org",
    "nmgcb.org",
]

MIN_GAP = 5.0
RUN_DEADLINE = time.time() + 2 * 3600
_last = [0.0]


def gap():
    d = MIN_GAP - (time.time() - _last[0])
    if d > 0:
        time.sleep(d)
    _last[0] = time.time()


def claim_lock():
    prev = json.loads(LOCK.read_text(encoding="utf-8")) if LOCK.exists() else {}
    LOCK.write_text(json.dumps({
        "host": "web.archive.org",
        "claimed_by": "code/211_cdx_enumerate_blocked_gaming_hosts.py (blocked-source bypass)",
        "pid": os.getpid(),
        "claimed_at": datetime.now(timezone.utc).isoformat(),
        "active": True,
        "policy": "single stream, >=5s gap, exponential backoff 30->480s, 2h RUN_DEADLINE",
        "took_over_from": prev.get("claimed_by"),
        "took_over_reason": "prior holder PID 7420 dead, claim 2026-08-07 (>6h) -- PULL_DISCIPLINE rule 2",
        "queue": [],
        "draining": prev.get("queue", []),
    }, indent=2), encoding="utf-8")


def release_lock(note):
    d = json.loads(LOCK.read_text(encoding="utf-8"))
    d["active"] = False
    d["released"] = datetime.now(timezone.utc).isoformat()
    d["note"] = note
    LOCK.write_text(json.dumps(d, indent=2), encoding="utf-8")


def get(url, tries=5):
    """Returns (status, bytes). status is an int, or a string for a transport failure."""
    delay = 30
    for i in range(tries):
        if time.time() > RUN_DEADLINE:
            return "DEADLINE", b""
        gap()
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            # 403/404 are facts about the object at this route. Do not retry.
            if e.code in (403, 404):
                return e.code, b""
            last = e.code
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
        if i < tries - 1:
            time.sleep(min(delay, max(0, RUN_DEADLINE - time.time())))
            delay = min(delay * 2, 480)
    return last, b""


def cdx(host):
    """Page the whole CDX result with resumeKey. Never uses `limit` as a cap."""
    rows, resume, pages = [], None, 0
    # MEASURED 2026-08-26: `collapse=digest` on a domain-wide query does not
    # return -- a first page was still in flight after 26 minutes and had to be
    # killed. `collapse=urlkey` answers the same query for gaming.az.gov in 27s.
    # Digest collapse de-duplicates by CONTENT across the whole host, which is a
    # far more expensive server-side scan than collapsing adjacent urlkeys.
    base = ("http://web.archive.org/cdx/search/cdx?"
            + urllib.parse.urlencode({
                "url": host + "/*",
                "output": "json",
                "fl": "timestamp,original,mimetype,statuscode,digest,length",
                "collapse": "urlkey",
                "showResumeKey": "true",
                "limit": "20000",
            }))
    while True:
        url = base + (("&resumeKey=" + urllib.parse.quote(resume)) if resume else "")
        st, body = get(url)
        pages += 1
        if st != 200:
            return rows, f"cdx_page_{pages}_status_{st}"
        try:
            data = json.loads(body.decode("utf-8", "replace") or "[]")
        except Exception as e:
            return rows, f"cdx_page_{pages}_unparseable: {e}"
        if not data:
            return rows, "ok"
        hdr, body_rows = data[0], data[1:]
        # resumeKey arrives as a blank row followed by the key
        resume = None
        while body_rows and (not body_rows[-1] or not body_rows[-1][0]):
            body_rows.pop()
        if body_rows and len(body_rows[-1]) == 1:
            resume = body_rows.pop()[0]
        rows.extend(dict(zip(hdr, r)) for r in body_rows if len(r) == len(hdr))
        print(f"    {host}: page {pages}, +{len(body_rows)} -> {len(rows)}", flush=True)
        if not resume:
            return rows, "ok"
        if pages > 20:
            return rows, "stopped_at_20_pages"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    claim_lock()
    state = {"started": datetime.now(timezone.utc).isoformat(), "hosts": {}}
    any_ok = False
    try:
        for host in HOSTS:
            f = OUT / f"cdx_{host}.json"
            if f.exists():
                print(f"  {host}: already on disk, skipped", flush=True)
                state["hosts"][host] = {"verdict": "already_on_disk_skipped",
                                        "rows": len(json.loads(f.read_text(encoding='utf-8')))}
                continue
            print(f"  {host}: enumerating ...", flush=True)
            rows, verdict = cdx(host)
            f.write_text(json.dumps(rows, indent=1), encoding="utf-8")
            pdfs = sum(1 for r in rows if r.get("mimetype", "").endswith("pdf")
                       or r.get("original", "").lower().split("?")[0].endswith(".pdf"))
            state["hosts"][host] = {"verdict": verdict, "rows": len(rows), "pdf_rows": pdfs}
            print(f"  {host}: {len(rows)} captures, {pdfs} PDF, verdict={verdict}", flush=True)
            if rows:
                any_ok = True
            if time.time() > RUN_DEADLINE:
                state["stopped"] = "RUN_DEADLINE"
                break
            # PULL_DISCIPLINE: stop on first refusal when nothing has landed
            if not any_ok and verdict != "ok":
                state["stopped"] = "first_host_refused_and_nothing_landed"
                break
    finally:
        state["finished"] = datetime.now(timezone.utc).isoformat()
        (OUT / "_cdx_state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
        release_lock("211 CDX enumeration of gaming.az.gov / nmgcb.org complete")
    print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
