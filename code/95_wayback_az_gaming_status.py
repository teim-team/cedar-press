#!/usr/bin/env python3
"""
95_wayback_az_gaming_status.py -- Cedar Press.

Drains the item that script 92's build QUEUED on the `web.archive.org` host lock
on 2026-08-06 and never got to run:

    "Wayback CDX enumeration of gaming.az.gov for prior editions of the ADG
     Gaming Status Report ... would convert a snapshot into a per-property
     device-count PANEL that overlaps the vendor panel year-for-year and is the
     single highest-value remaining pull in the gaming build."

The lock (logs/_HOSTLOCK_web.archive.org.json) was claimed by script 89, whose
PID 30908 is dead and whose claim is >6h old. PULL_DISCIPLINE rule 2 permits
takeover in exactly that case, and this script rewrites the lock in its own name
before the first request.

Failure shapes observed on this host on 2026-08-07 and handled per rule 4:
  * curl/urllib connect failure in ~21s, intermittently, on maybe half of calls
    -- SERVER SLOW / flaky edge, not a block, because the very next identical
    request returns 200. Retry with exponential backoff, single stream.
  * CDX `limit=` silently truncates. Enumerate by explicit path prefix instead
    of one domain-wide sweep.

WRITES
  data/raw/external/gaming_official/wayback_az_cdx_<date>.json   (the enumeration)
  data/raw/external/gaming_official/az_wayback/<timestamp>_<name>  (the captures)
"""
import json, os, re, sys, time, urllib.request, urllib.error, urllib.parse
from datetime import datetime, timezone
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
RAW = CEDAR / "data" / "raw" / "external" / "gaming_official"
OUT = RAW / "az_wayback"
LOCK = CEDAR / "logs" / "_HOSTLOCK_web.archive.org.json"
TODAY = "2026-08-07"
UA = {"User-Agent": "CedarPress/1.0 (research; elijahsamsonmoreno@gmail.com)"}

MIN_GAP = 5.0
_last = [0.0]


def claim_lock():
    prev = json.loads(LOCK.read_text(encoding="utf-8")) if LOCK.exists() else {}
    LOCK.write_text(json.dumps({
        "host": "web.archive.org",
        "claimed_by": "code/95_wayback_az_gaming_status.py (gaming capacity official layer)",
        "pid": os.getpid(),
        "claimed_at": datetime.now(timezone.utc).isoformat(),
        "active": True,
        "policy": "single stream, >=5s gap, exponential backoff 30->900s, 2h cap",
        "took_over_from": prev.get("claimed_by"),
        "took_over_reason": "prior holder PID dead and claim older than 6h (PULL_DISCIPLINE rule 2)",
        "queue": [],
        "draining": prev.get("queue", []),
    }, indent=2), encoding="utf-8")


def release_lock(note):
    if not LOCK.exists():
        return
    d = json.loads(LOCK.read_text(encoding="utf-8"))
    d["active"] = False
    d["released_at"] = datetime.now(timezone.utc).isoformat()
    d["result"] = note
    LOCK.write_text(json.dumps(d, indent=2), encoding="utf-8")


def get(url, timeout=60, tries=8):
    """One request, exponential backoff, single stream."""
    wait = 15.0
    for i in range(tries):
        gap = MIN_GAP - (time.time() - _last[0])
        if gap > 0:
            time.sleep(gap)
        _last[0] = time.time()
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            if e.code in (429, 503, 502, 504):
                ra = e.headers.get("Retry-After")
                sl = float(ra) if (ra or "").isdigit() else wait
                print(f"    HTTP {e.code}; sleeping {sl:.0f}s", flush=True)
                time.sleep(sl)
                wait = min(wait * 2, 240)
                continue
            return e.code, b"", {}
        except Exception as e:
            print(f"    attempt {i+1}/{tries} failed: {str(e)[:90]}; "
                  f"sleeping {wait:.0f}s", flush=True)
            time.sleep(wait)
            wait = min(wait * 2, 240)
    return 0, b"", {}


PREFIXES = [
    "gaming.az.gov/sites/default/files*",
    "gaming.az.gov/report*",
    "gaming.az.gov/current-status*",
    "gaming.az.gov/tribal*",
    "azgaming.gov/*",
]

KEEP = ("status", "allocation", "contribution", "annual", "device")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    claim_lock()
    started = time.time()
    found = {}
    try:
        for pref in PREFIXES:
            u = ("https://web.archive.org/cdx/search/cdx?url="
                 + urllib.parse.quote(pref, safe="*/:")
                 + "&output=json&collapse=digest&limit=20000")
            print(f"CDX {pref}", flush=True)
            ck = RAW / ("wayback_az_cdx_raw_"
                        + re.sub(r"[^a-z0-9]+", "_", pref.lower()).strip("_") + ".json")
            if ck.exists():
                code, body = 200, json.dumps(
                    [["h"]] + json.loads(ck.read_text(encoding="utf-8"))).encode()
                print("  -> reusing checkpoint", flush=True)
            else:
                code, body, _ = get(u)
            if code != 200 or not body.strip():
                print(f"  -> {code}, no rows", flush=True)
                continue
            try:
                rows = json.loads(body)[1:]
            except Exception:
                print("  -> unparseable", flush=True)
                continue
            print(f"  -> {len(rows):,} captures", flush=True)
            (RAW / ("wayback_az_cdx_raw_"
                    + re.sub(r"[^a-z0-9]+", "_", pref.lower()).strip("_")
                    + ".json")).write_text(json.dumps(rows), encoding="utf-8")
            for r in rows:
                ts, orig, mime, status = r[1], r[2], r[3], r[4]
                low = orig.lower()
                if status != "200":
                    continue
                if not any(k in low for k in KEEP):
                    continue
                found[(ts, orig)] = dict(timestamp=ts, original=orig,
                                         mimetype=mime, statuscode=status)
            if time.time() - started > 7200:
                break

        man = RAW / f"wayback_az_cdx_{TODAY}.json"
        man.write_text(json.dumps(sorted(found.values(),
                                         key=lambda d: d["timestamp"]), indent=1),
                       encoding="utf-8")
        print(f"\n{len(found):,} candidate captures -> {man.name}", flush=True)

        # Fetch, newest capture per distinct original URL first.
        best = {}
        for d in found.values():
            o = d["original"]
            if o not in best or d["timestamp"] > best[o]["timestamp"]:
                best[o] = d
        print(f"{len(best):,} distinct URLs to fetch", flush=True)
        got = 0
        for o, d in sorted(best.items()):
            name = (d["timestamp"] + "_"
                    + o.rsplit("/", 1)[-1].split("?")[0][:110].replace("%20", "_"))
            if not name.lower().endswith((".pdf", ".html", ".htm")):
                name += ".pdf" if "pdf" in d["mimetype"] else ".html"
            p = OUT / name
            if p.exists() and p.stat().st_size > 0:
                got += 1
                continue
            url = f"https://web.archive.org/web/{d['timestamp']}id_/{o}"
            code, body, hdrs = get(url, timeout=120, tries=4)
            if code == 200 and body:
                p.write_bytes(body)
                got += 1
                print(f"  {code} {len(body):>9,}  {name}", flush=True)
            else:
                print(f"  {code} FAILED  {o[:110]}", flush=True)
            if time.time() - started > 7200:
                print("2h cap reached; stopping (PULL_DISCIPLINE rule 3)", flush=True)
                break
        release_lock(f"{got} captures written to {OUT}")
        print(f"\nDONE: {got} captures in {OUT}", flush=True)
    except BaseException as e:
        release_lock(f"aborted: {type(e).__name__}: {e}")
        raise


if __name__ == "__main__":
    main()
