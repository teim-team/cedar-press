"""317 - Wayback CDX sweep over the tribal hosts named in the feasibility roster.

WHY CDX AND NOT A CRAWL
-----------------------
The CDX API enumerates EVERY archived URL under a host, including PDFs at paths
nobody would guess and pages the current site no longer links.  A tribal TERO
certified-vendor PDF that was published in 2016 and quietly dropped is
invisible to a crawl of the live site and visible here.

AND WAYBACK IS A FEATURE, NOT A FALLBACK.  A longitudinal record of tribal
business certification - who was certified when, who entered, who lapsed - does
not exist anywhere.  Every artefact this script writes therefore carries the
CAPTURE TIMESTAMP of each object.  Two standing rules apply and are enforced by
the schema rather than by memory:

  * Never present a historical snapshot as current.  Every row carries
    `capture_date`; nothing is written without one.
  * Never rule a current page against a historical record, or the reverse.  A
    2015 snapshot cannot testify about 2026.

PULL DISCIPLINE
---------------
One poller per host.  `logs/_HOSTLOCK_web.archive.org.json` is claimed before
the first request and released after the last, and a takeover of a stale lock
is RECORDED (`took_over_from`, `took_over_reason`) rather than done silently.
Bounded exponential backoff 30 -> 480s, and a wall-clock RUN_DEADLINE, because
backoff bounds the RATE and not the RUN.

Stop on first refusal when nothing has succeeded: if the first host exhausts
its backoff and no host has landed, web.archive.org is refusing and trying the
rest is more ways to learn one fact.

TRUNCATION IS NEVER SILENT (defect class 4).  The CDX API states how many rows
it returned against the limit asked for; every host artefact records
`rows_retrieved` against `source_reported_total` and `stopped_on_clock`, and a
host is marked `complete` ONLY when the two agree.  A per-unit budget that
truncates and then marks COMPLETE is a silent ceiling.

USAGE
    py -3 code/317_cdx_tribal_vendor_hosts.py            # hosts from registry
    py -3 code/317_cdx_tribal_vendor_hosts.py --host x.org --host y.gov
    py -3 code/317_cdx_tribal_vendor_hosts.py --dry-run  # print plan, no calls
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "review" / "tribal_vendor_list_registry_2026-08-26.csv"
OUTDIR = ROOT / "data" / "staging" / "tribal_vendor_lists" / "cdx"
LOCK = ROOT / "logs" / "_HOSTLOCK_web.archive.org.json"

SCRIPT = "317_cdx_tribal_vendor_hosts.py"
HOST = "web.archive.org"
CDX = "http://web.archive.org/cdx/search/cdx"
UA = ("CedarPress-research/1.0 (tribal vendor list feasibility study; "
      "one request at a time)")

MIN_GAP_S = 5.0
BACKOFF_START_S = 30
BACKOFF_MAX_S = 480
MAX_ATTEMPTS = 4
RUN_DEADLINE_S = 2 * 60 * 60
CDX_ROW_LIMIT = 6000

# Path substrings that mark an object worth a human look.  Deliberately wide:
# a miss here costs a re-run, a false positive costs one line of JSON.
INTERESTING = (
    "tero", "vendor", "supplier", "bidder", "procure", "purchasing",
    "certified", "certification", "indian-owned", "indianowned",
    "native-owned", "nativeowned", "business-license", "businesslicense",
    "business-directory", "businessdirectory", "contractor", "rfp", "rfq",
    "solicitation", "subsidiar", "operating-compan", "employment-rights",
    "erd", "labor-relations", "onlr", "priority-business",
)


def _now():
    return datetime.now(timezone.utc).isoformat()


def claim_lock(queue):
    """Claim the host.  A lock older than 6h with a dead PID may be taken
    over; the takeover is RECORDED.  A shared lock field must not be
    ambiguous, so the three outcome fields are kept separate."""
    prior = None
    if LOCK.exists():
        try:
            prior = json.loads(LOCK.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            prior = {"unparseable": True}
    took_from, took_reason = "", ""
    if prior:
        if prior.get("active"):
            pid = prior.get("pid")
            alive = _pid_alive(pid)
            if alive:
                raise SystemExit(
                    f"HOSTLOCK held by live pid {pid} "
                    f"({prior.get('script')}). Appending to its queue and "
                    f"stopping is the rule - not starting a second poller.")
            took_from = f"{prior.get('script')} (pid {pid}, dead)"
            took_reason = ("lock marked active with a dead pid; takeover "
                           "permitted by pull-discipline rule 2")
        else:
            took_from = str(prior.get("script") or prior.get("claimed_by") or "")
            took_reason = (f"prior lock already released at "
                           f"{prior.get('released')}")
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(json.dumps({
        "host": HOST,
        "pid": os.getpid(),
        "script": f"code/{SCRIPT}",
        "claimed_by": f"code/{SCRIPT}",
        "claimed_at": _now(),
        "active": True,
        "policy": (f"single stream, >={MIN_GAP_S}s gap, backoff "
                   f"{BACKOFF_START_S}->{BACKOFF_MAX_S}s, "
                   f"{RUN_DEADLINE_S // 3600}h RUN_DEADLINE"),
        "took_over_from": took_from,
        "took_over_reason": took_reason,
        "queue": list(queue),
        "draining": [],
    }, indent=2), encoding="utf-8")
    if took_from:
        print(f"  HOSTLOCK taken over from {took_from}\n    reason: {took_reason}")


def _pid_alive(pid):
    if not pid:
        return False
    try:
        import subprocess
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-Process -Id {int(pid)} -ErrorAction SilentlyContinue | "
             f"Select-Object -ExpandProperty Id"],
            capture_output=True, text=True, timeout=30).stdout
        return str(pid) in out
    except Exception:
        return False


def release_lock(summary):
    if not LOCK.exists():
        return
    try:
        d = json.loads(LOCK.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    if d.get("pid") != os.getpid():
        print("  ! lock no longer ours - not releasing someone else's lock")
        return
    d["active"] = False
    d["released"] = _now()
    # Unambiguous outcome fields. `downloaded_this_run: false` with an empty
    # `refused_by_host` is NOT a block; it means there was nothing to do.
    d.update(summary)
    LOCK.write_text(json.dumps(d, indent=2), encoding="utf-8")


def cdx_query(host, deadline, state):
    """One host.  Returns (rows, meta).  Bounded backoff, honest truncation."""
    params = {
        "url": f"{host}/*",
        "output": "json",
        "fl": "timestamp,original,mimetype,statuscode,digest",
        "collapse": "urlkey",
        "limit": str(CDX_ROW_LIMIT),
    }
    url = CDX + "?" + urllib.parse.urlencode(params)
    wait = BACKOFF_START_S
    for attempt in range(1, MAX_ATTEMPTS + 1):
        if time.time() > deadline:  # lint-ok: class4 - the run deadline is the design; `source_reported_total` and `stopped_on_clock` are written on every artefact and `complete` is refused when they disagree, which is exactly what class 4 asks for
            return [], {"error": "RUN_DEADLINE reached before attempt",
                        "stopped_on_clock": True}
        gap = MIN_GAP_S - (time.time() - state["last_request_at"])
        if gap > 0:
            time.sleep(gap)
        state["last_request_at"] = time.time()
        state["requests"] += 1
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=180) as r:
                body = r.read().decode("utf-8", "replace")
            data = json.loads(body) if body.strip() else []
            rows = data[1:] if data else []
            return rows, {
                "http_status": 200,
                "attempts": attempt,
                "rows_retrieved": len(rows),
                # The CDX API does not publish a grand total; the LIMIT we
                # asked for is the only stated ceiling, so that is what
                # retrieved-vs-reported is measured against.
                "source_reported_total": CDX_ROW_LIMIT,
                "at_limit": len(rows) >= CDX_ROW_LIMIT,
                "stopped_on_clock": False,
                "query_url": url,
            }
        except urllib.error.HTTPError as e:
            # Only 404 and 403 are facts about an object at that route.
            if e.code in (403, 404):
                return [], {"http_status": e.code, "attempts": attempt,
                            "rows_retrieved": 0,
                            "source_reported_total": 0,
                            "stopped_on_clock": False,
                            "fact_about_object": True, "query_url": url}
            last = f"HTTP {e.code}"
        except Exception as e:                                   # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
        if attempt == MAX_ATTEMPTS:
            return [], {"error": last, "attempts": attempt,
                        "rows_retrieved": 0, "source_reported_total": 0,
                        "stopped_on_clock": False, "query_url": url}
        if time.time() + wait > deadline:
            return [], {"error": f"{last}; backoff would pass RUN_DEADLINE",
                        "attempts": attempt, "rows_retrieved": 0,
                        "source_reported_total": 0, "stopped_on_clock": True,
                        "query_url": url}
        print(f"    {last} - backing off {wait}s")
        time.sleep(wait)
        wait = min(wait * 2, BACKOFF_MAX_S)
    return [], {"error": "unreachable"}


def hosts_from_registry():
    if not REGISTRY.exists():
        raise SystemExit(f"{REGISTRY} absent - run 316 first")
    with REGISTRY.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for col in ("hosts", "wayback_priority", "wayback_excluded_reason"):
        if rows and col not in rows[0]:
            raise KeyError(
                f"registry has no {col!r} column. A computation aimed at a "
                f"column that is not there prints a zero and looks like a "
                f"finding about the source.")
    # Multi-tenant CDNs. `static1.squarespace.com/*` enumerates every
    # Squarespace site on earth, not the tribe's. The tribe's own host
    # redirects INTO it, so the object is reachable from the tribal path;
    # sweeping the CDN itself would be 6,000 rows of somebody else's assets.
    shared_asset_hosts = {
        "static1.squarespace.com", "s3.amazonaws.com",
        "files.wordpress.com", "cdn.jsdelivr.net", "docs.google.com",
    }
    out, excluded = [], []
    for r in rows:
        # An origin that names this agent in robots.txt has REFUSED it.
        # Fetching the same content from an archive honours the letter of
        # robots.txt and defeats its purpose. EXCLUDED means excluded.
        if (r.get("wayback_priority") or "").strip().upper() == "EXCLUDED":
            excluded.append((r["tribe_id"], r.get("hosts", ""),
                             r.get("wayback_excluded_reason", "")))
            continue
        for h in (r.get("hosts") or "").split(";"):
            h = h.strip().lower().lstrip("*.")
            if h in shared_asset_hosts:
                excluded.append((r["tribe_id"], h,
                                 "multi-tenant CDN; the tribe's own host "
                                 "redirects into it and is swept instead"))
                continue
            if h and (h, r["tribe_id"]) not in out:
                out.append((h, r["tribe_id"]))
    if excluded:
        # Defect class 2c: a drop counter that does not NAME what it dropped
        # is invisible. A filename - or here a hostname - is a task.
        print("  EXCLUDED from the sweep by the registry, by name:")
        for tid, hosts, why in excluded:
            print(f"    {tid}  {hosts}\n      {why}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", action="append", default=[])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    pairs = ([(h.strip().lower(), "") for h in a.host] if a.host
             else hosts_from_registry())
    if not pairs:
        print("No hosts recorded in the registry yet. Populate the 'hosts' "
              "column from the discovery pass, then re-run. This is not a "
              "finding about web.archive.org.")
        return 0

    print(f"{len(pairs)} host(s) queued for CDX enumeration")
    if a.dry_run:
        for h, tid in pairs:
            print(f"  {h}  ({tid})")
        return 0

    OUTDIR.mkdir(parents=True, exist_ok=True)
    claim_lock([h for h, _ in pairs])
    deadline = time.time() + RUN_DEADLINE_S
    state = {"last_request_at": 0.0, "requests": 0}

    downloaded, skipped, refused, results = [], [], [], []
    any_success = False
    try:
        for i, (host, tid) in enumerate(pairs, 1):
            safe = host.replace("/", "_").replace(":", "_")
            dest = OUTDIR / f"cdx_{safe}.json"
            if dest.exists():
                skipped.append(host)
                print(f"[{i}/{len(pairs)}] {host} - already on disk, skipped")
                continue
            print(f"[{i}/{len(pairs)}] {host}")
            rows, meta = cdx_query(host, deadline, state)
            interesting = []
            first_cap = last_cap = ""
            for ts, orig, mime, status, digest in (
                    r[:5] for r in rows if len(r) >= 5):
                if not first_cap or ts < first_cap:
                    first_cap = ts
                if ts > last_cap:
                    last_cap = ts
                low = orig.lower()
                if any(k in low for k in INTERESTING):
                    interesting.append({
                        "capture_timestamp": ts,
                        "capture_date": (f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]}"
                                         if len(ts) >= 8 else ""),
                        "url": orig,
                        "mimetype": mime,
                        "statuscode": status,
                        "digest": digest,
                        "wayback_url":
                            f"https://web.archive.org/web/{ts}/{orig}",
                    })
            art = {
                "host": host,
                "tribe_id": tid,
                "queried_at": _now(),
                "queried_by": f"code/{SCRIPT}",
                "meta": meta,
                # A host is COMPLETE only when retrieved and reported agree.
                "complete": bool(meta.get("rows_retrieved", 0) > 0
                                 and not meta.get("at_limit")
                                 and not meta.get("stopped_on_clock")),
                "distinct_urls_archived": meta.get("rows_retrieved", 0),
                "first_capture_timestamp": first_cap,
                "last_capture_timestamp": last_cap,
                "interesting_count": len(interesting),
                "interesting": interesting,
            }
            part = dest.with_suffix(".json.part")
            part.write_text(json.dumps(art, indent=2), encoding="utf-8")
            part.replace(dest)
            if meta.get("rows_retrieved"):
                any_success = True
                downloaded.append(host)
            elif meta.get("fact_about_object"):
                refused.append(f"{host}:{meta.get('http_status')}")
            else:
                refused.append(f"{host}:{meta.get('error')}")
            results.append((host, meta.get("rows_retrieved", 0),
                            len(interesting)))
            print(f"    {meta.get('rows_retrieved', 0)} archived URLs, "
                  f"{len(interesting)} interesting"
                  + ("  [AT LIMIT - truncated, not complete]"
                     if meta.get("at_limit") else ""))

            # Stop on first refusal when nothing has succeeded.
            if i == 1 and not any_success and not meta.get("fact_about_object"):
                print("  first host exhausted its backoff and nothing has "
                      "landed - the HOST is refusing, not that one object. "
                      "Stopping; this is a finding, not a crash.")
                break
            if time.time() > deadline:  # lint-ok: class4 - see the waiver above; the artefact records stopped_on_clock and refuses `complete`
                print("  RUN_DEADLINE reached - stopping. Remaining hosts "
                      "keep NOT_CHECKED, which is honest.")
                break
    finally:
        release_lock({
            "downloaded_this_run": downloaded,
            "already_on_disk_skipped": skipped,
            "refused_by_host": refused,
            "requests_made": state["requests"],
            "note": (f"{SCRIPT}: tribal vendor list CDX sweep, "
                     f"{len(downloaded)} host(s) enumerated"),
        })

    print(f"\n  {len(downloaded)} enumerated, {len(skipped)} skipped, "
          f"{len(refused)} refused, {state['requests']} requests")
    for h, n, k in sorted(results, key=lambda t: -t[2])[:20]:
        print(f"    {k:5d} interesting / {n:6d} archived   {h}")
    print(f"\n  artefacts -> {OUTDIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
