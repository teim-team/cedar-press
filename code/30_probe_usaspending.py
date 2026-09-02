"""30_probe_usaspending.py — polite availability probe for api.usaspending.gov.

The FY2001-2007 backfill depends on the bulk_download API. A prior run tripped an
edge-level rate limit (RemoteDisconnected on both api. and files. hosts while
www. stays 200). This probe checks availability at a low, fixed cadence and exits
the moment the host answers, so no request storm is generated.

Usage: py -3 code/30_probe_usaspending.py [interval_seconds] [max_tries]
Exit 0 = API reachable. Exit 1 = still blocked after max_tries.
"""
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

URL = "https://api.usaspending.gov/api/v2/references/agency/020/"
LOG = "logs/30_funding_pre2008.log"


def log(msg):
    line = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def probe():
    req = urllib.request.Request(URL, headers={"User-Agent": "CedarPress-research/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return True, f"HTTP {r.status}, {len(r.read())} bytes"
    except urllib.error.HTTPError as e:
        # An HTTP error still means the edge is talking to us.
        return True, f"HTTPError {e.code} (host reachable)"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def main():
    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    max_tries = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    for i in range(1, max_tries + 1):
        ok, detail = probe()
        log(f"PROBE {i}/{max_tries} api.usaspending.gov -> {'AVAILABLE' if ok else 'BLOCKED'} | {detail}")
        if ok:
            return 0
        if i < max_tries:
            time.sleep(interval)
    return 1


if __name__ == "__main__":
    sys.exit(main())
