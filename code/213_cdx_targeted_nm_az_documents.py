#!/usr/bin/env python3
"""
213_cdx_targeted_nm_az_documents.py -- Cedar Press.

Replaces the domain-wide sweep in `code/211_cdx_enumerate_blocked_gaming_hosts.py`
with a TARGETED one, for a reason worth writing down:

    A domain-wide CDX enumeration of `gaming.az.gov` returned 20,000 rows per
    page and was still paging after three pages and twelve minutes. ADG's site
    carries query-string URLs, so the capture count is dominated by pages that
    cannot possibly be the document. **An index is only cheap if you index the
    right axis.** Two axes are cheap and are the ones that matter here:

      1. `filter=mimetype:application/pdf`  -- the reports are PDFs.
      2. `url=<the one page whose HTML holds the ids I need>` with NO collapse,
         which returns every capture of that page in timestamp order so the
         NEWEST can be taken. Collapsing by urlkey would return exactly one.

WHY AXIS 2 IS THE WHOLE NEW MEXICO ANSWER
-----------------------------------------
`docs/GAMING_CAPACITY_OFFICIAL_LOG.md` records NM 2023-2025 as unreachable and
says *"Getting past Cloudflare once, to read the current page's GUIDs, is the
only route."* It is not. NMGCB's quarterly PDFs are not served from nmgcb.org at
all -- they live on `api.realfile.rtsclients.com`, which is a different host,
answers normally, and has no robots.txt. The only thing nmgcb.org holds is the
`data-folder-id` / `data-widget-id` GUIDs in the page markup. **A Wayback
capture of that page taken AFTER 2023 carries the 2023+ GUIDs**, and Wayback is
not behind Cloudflare. The saved capture on disk is 2023-01-30, which is simply
too early -- the constraint was the SNAPSHOT DATE, never the block.

WRITES
  data/raw/external/gaming_official/bypass_2026-08-26/cdx_<label>.json
  data/raw/external/gaming_official/bypass_2026-08-26/_cdx_targeted_state.json
"""
import json, os, time, urllib.request, urllib.error, urllib.parse
from datetime import datetime, timezone
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
OUT = CEDAR / "data" / "raw" / "external" / "gaming_official" / "bypass_2026-08-26"
LOCK = CEDAR / "logs" / "_HOSTLOCK_web.archive.org.json"
UA = {"User-Agent": "CedarPress/1.0 (research; elijahsamsonmoreno@gmail.com)"}

# (label, cdx params). NM first: it is the one with a live document behind it.
QUERIES = [
    ("nm_revsharing_page_all_captures", {
        "url": "nmgcb.org/tribal-revenue-sharing*", "matchType": "prefix",
        "fl": "timestamp,original,mimetype,statuscode,digest,length"}),
    ("nm_revsharing_page_www_all_captures", {
        "url": "www.nmgcb.org/tribal-revenue-sharing*", "matchType": "prefix",
        "fl": "timestamp,original,mimetype,statuscode,digest,length"}),
    ("nm_all_pdf", {
        "url": "nmgcb.org/*", "filter": "mimetype:application/pdf",
        "collapse": "urlkey",
        "fl": "timestamp,original,mimetype,statuscode,digest,length"}),
    ("nm_www_all_pdf", {
        "url": "www.nmgcb.org/*", "filter": "mimetype:application/pdf",
        "collapse": "urlkey",
        "fl": "timestamp,original,mimetype,statuscode,digest,length"}),
    ("nm_home_recent", {
        "url": "nmgcb.org", "from": "2023", "matchType": "exact",
        "fl": "timestamp,original,mimetype,statuscode,digest,length"}),
    ("az_all_pdf", {
        "url": "gaming.az.gov/*", "filter": "mimetype:application/pdf",
        "collapse": "urlkey",
        "fl": "timestamp,original,mimetype,statuscode,digest,length"}),
    ("az_old_host_all_pdf", {
        "url": "azgaming.gov/*", "filter": "mimetype:application/pdf",
        "collapse": "urlkey",
        "fl": "timestamp,original,mimetype,statuscode,digest,length"}),
    ("az_contributions_pages", {
        "url": "gaming.az.gov/*contribution*", "matchType": "prefix",
        "collapse": "urlkey",
        "fl": "timestamp,original,mimetype,statuscode,digest,length"}),
    ("realfile_public_nm", {
        "url": "api.realfile.rtsclients.com/PublicFiles/c5d7c9d5c4424c1fb796bb563e87e31c*",
        "matchType": "prefix", "collapse": "urlkey",
        "fl": "timestamp,original,mimetype,statuscode,digest,length"}),
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
        "host": "web.archive.org", "pid": os.getpid(),
        "claimed_by": "code/213_cdx_targeted_nm_az_documents.py (blocked-source bypass)",
        "claimed_at": datetime.now(timezone.utc).isoformat(), "active": True,
        "policy": "single stream, >=5s gap, backoff 30->480s, 2h RUN_DEADLINE",
        "took_over_from": prev.get("claimed_by"),
        "took_over_reason": "same agent, 211 superseded by a targeted query set",
        "queue": [], "draining": prev.get("draining", [])}, indent=2), encoding="utf-8")


def release_lock(note):
    d = json.loads(LOCK.read_text(encoding="utf-8"))
    d.update({"active": False, "released": datetime.now(timezone.utc).isoformat(),
              "note": note})
    LOCK.write_text(json.dumps(d, indent=2), encoding="utf-8")


def get(url, tries=4):
    delay = 30
    last = None
    for i in range(tries):
        if time.time() > RUN_DEADLINE:
            return "DEADLINE", b""
        gap()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                return e.code, b""
            last = e.code
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
        if i < tries - 1:
            time.sleep(min(delay, max(0, RUN_DEADLINE - time.time())))
            delay = min(delay * 2, 480)
    return last, b""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    claim_lock()
    state = {"started": datetime.now(timezone.utc).isoformat(), "queries": {}}
    try:
        for label, params in QUERIES:
            f = OUT / f"cdx_{label}.json"
            if f.exists():
                state["queries"][label] = {"verdict": "already_on_disk_skipped"}
                print(f"  {label}: on disk", flush=True)
                continue
            p = dict(params)
            p["output"] = "json"
            p.setdefault("limit", "20000")
            url = "http://web.archive.org/cdx/search/cdx?" + urllib.parse.urlencode(p)
            t0 = time.time()
            st, body = get(url)
            if st != 200:
                state["queries"][label] = {"verdict": f"status_{st}", "secs": round(time.time() - t0, 1)}
                print(f"  {label}: status {st}", flush=True)
                continue
            try:
                data = json.loads(body.decode("utf-8", "replace") or "[]")
            except Exception as e:
                state["queries"][label] = {"verdict": f"unparseable: {e}"}
                continue
            rows = [dict(zip(data[0], r)) for r in data[1:]] if data else []
            f.write_text(json.dumps(rows, indent=1), encoding="utf-8")
            state["queries"][label] = {"verdict": "ok", "rows": len(rows),
                                       "secs": round(time.time() - t0, 1)}
            print(f"  {label}: {len(rows)} rows in {round(time.time()-t0,1)}s", flush=True)
            if time.time() > RUN_DEADLINE:
                state["stopped"] = "RUN_DEADLINE"
                break
    finally:
        state["finished"] = datetime.now(timezone.utc).isoformat()
        (OUT / "_cdx_targeted_state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
        release_lock("213 targeted CDX complete")
    print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
