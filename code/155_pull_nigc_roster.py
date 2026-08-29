#!/usr/bin/env python3
r"""Cedar Press 155 - pull the CURRENT NIGC gaming location roster.

WHY THIS SCRIPT EXISTS
----------------------
The only NIGC roster Cedar holds is a 2026-08-06 snapshot of the WP Google Maps
marker JSON (490 markers) at
`data/raw/external/nigc/locations/nigc_gaming_locations_map6_2026-08-06.json`.
No script in `code/` reproduced that fetch, so the route was undocumented and
the roster could not be refreshed.

THE ROUTE, MEASURED 2026-08-26 (each probe recorded because each one kills an
explanation, per docs/PULL_DISCIPLINE.md):

  POST admin-ajax.php action=get_markers&map_id=6   -> HTTP 400, body "0"
       (WP's answer for an action that is not registered)
  GET  /wp-json/wpgmza/v1/markers?filter=...        -> HTTP 401 rest_not_logged_in
       ...with X-WP-Nonce                           -> HTTP 401 (unchanged)
       ...with cookie jar + _wpnonce query param    -> HTTP 401 (unchanged)
  GET  /?rest_route=/wpgmza/v1/markers              -> HTTP 401 (unchanged)
  POST admin-ajax action=wpgmza_rest_api_request
       route=/markers/                              -> HTTP 403 rest_forbidden
       route=/markers                               -> HTTP 404 rest_no_route
  POST admin-ajax action=wpgmza_rest_api_request
       route=/datatables/                           -> HTTP 200, 522 records

So: **www.nigc.gov serves the REST API to nobody anonymous** (401 is WP's own
`rest_authentication_errors` filter, not a nonce failure - the nonce is stable
across page loads and adding it changes nothing). The marker route is closed
even through the plugin's own AJAX fallback. The **marker-listing datatable is
the only public route**, and it is the one the page itself uses: the map page
carries `data-wpgmza-rest-api-route="/datatables/"` on the listing table.

WHAT THE DATATABLE GIVES AND WHAT IT COSTS
------------------------------------------
Columns: icon html, title, category (= NIGC region), address, description
(contact block), link. **No coordinates and no marker id** - those are in the
marker route we cannot reach. Coordinates for the overlap remain available from
the 2026-08-06 snapshot, which is why that file is not superseded and not
deleted.

One row is not a gaming location: `NIGC Headquarters`, category NULL, whose
"address" cell holds a coordinate pair. It is dropped, and the drop is
recorded rather than silently filtered.

Writes
  data/raw/external/nigc/locations/nigc_marker_listing_map6_<date>.json  (raw)
  data/raw/external/nigc/locations/nigc_roster_current_<date>.csv        (parsed)
  logs/155_nigc_roster_pull.log
"""

import csv
import html
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
RAW = CEDAR / "data" / "raw" / "external" / "nigc" / "locations"
LOGS = CEDAR / "logs"
TODAY = date.today().isoformat()
HOST = "www.nigc.gov"
LOCK = LOGS / f"_HOSTLOCK_{HOST}.json"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

MAP_PAGE = "https://www.nigc.gov/map/"
AJAX = "https://www.nigc.gov/wp-admin/admin-ajax.php"


def log(msg):
    line = f"{datetime.now().isoformat(timespec='seconds')} {msg}"
    # the console here is cp1252 and NIGC names carry U+2019 and mojibake bytes
    sys.stdout.write(line.encode("ascii", "replace").decode("ascii") + "\n")
    with open(LOGS / "155_nigc_roster_pull.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ---------------------------------------------------------------- host lock
def claim_lock(note):
    """One poller per host. Append and exit if someone live holds it."""
    if LOCK.exists():
        try:
            cur = json.loads(LOCK.read_text(encoding="utf-8"))
        except Exception:
            cur = {}
        if cur.get("active") and not cur.get("released"):
            log(f"HOSTLOCK held by pid {cur.get('pid')} ({cur.get('script')}); "
                "appending to queue and exiting.")
            cur.setdefault("queue", []).append(note)
            LOCK.write_text(json.dumps(cur, indent=1), encoding="utf-8")
            sys.exit(3)
    LOCK.write_text(json.dumps({
        "host": HOST, "pid": os.getpid(), "script": "code/155_pull_nigc_roster.py",
        "started": datetime.utcnow().isoformat() + "Z", "active": True,
        "queue": [note], "note": note,
        "downloaded_this_run": 0, "refused_by_host": [],
    }, indent=1), encoding="utf-8")


def release_lock(downloaded, refused):
    d = json.loads(LOCK.read_text(encoding="utf-8"))
    d["active"] = False
    d["released"] = datetime.utcnow().isoformat() + "Z"
    d["downloaded_this_run"] = downloaded
    d["refused_by_host"] = refused
    LOCK.write_text(json.dumps(d, indent=1), encoding="utf-8")


# ---------------------------------------------------------------- fetching
def curl(url, args=(), timeout=90, cookie_jar=None, save_cookies=None):
    cmd = ["curl", "-s", "-A", UA, "--max-time", str(timeout),
           "-w", "\n__HTTPSTATUS__%{http_code}"]
    if cookie_jar:
        cmd += ["-b", str(cookie_jar)]
    if save_cookies:
        cmd += ["-c", str(save_cookies)]
    cmd += list(args) + [url]
    p = subprocess.run(cmd, capture_output=True)
    out = p.stdout
    m = re.search(rb"\n__HTTPSTATUS__(\d+)$", out)
    status = int(m.group(1)) if m else 0
    return status, (out[:m.start()] if m else out)


def strip_tags(s):
    if not s:
        return ""
    s = re.sub(r"<br\s*/?>|</br>", " | ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


# NIGC's own address strings are not clean. Measured defects the pattern must
# survive rather than silently drop:
#   * CT ZIPs lose the leading zero  - `Mashantucket CT 6338`  (= 06338)
#   * a truncated ZIP+4              - `Immokalee FL 34142-430`
#   * a ZIP+4 run together           - `Pickstown SD 573670229`
#   * the address cell holding a coordinate pair instead of an address
# So the ZIP is matched as 4-9 digits with an optional dash and NOT required to
# be five. A parser that required \d{5} reported "address did not parse" on
# Foxwoods and Mohegan Sun - two of the largest casinos in the country.
ADDR_RE = re.compile(r"^(?P<street>.*?),?\s*(?P<city>[A-Za-z\.\-'\u2019 ]+?)[, ]+"
                     r"(?P<state>[A-Z]{2})\.?\s+(?P<zip>\d{4,9}(?:-\d{1,4})?)\s*$")
COORD_RE = re.compile(r"^-?\d+\.\d+\s*,\s*-?\d+\.\d+$")


def parse_address(addr):
    a = re.sub(r"\s+", " ", (addr or "")).strip()
    if COORD_RE.match(a):
        return {"street": "", "city": "", "state": "", "postal_code": "",
                "address_is_coordinates": "1"}
    m = ADDR_RE.match(a)
    if not m:
        return {"street": a, "city": "", "state": "", "postal_code": "",
                "address_is_coordinates": "0"}
    z = m.group("zip")
    if "-" not in z and len(z) == 4:
        z = "0" + z                    # CT/MA/NJ leading zero, stated as such
    return {"street": m.group("street").strip().rstrip(","),
            "city": m.group("city").strip().title(),
            "state": m.group("state"), "postal_code": z,
            "address_is_coordinates": "0"}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(exist_ok=True)
    raw_path = RAW / f"nigc_marker_listing_map6_{TODAY}.json"
    if raw_path.exists() and "--refetch" not in sys.argv:
        # Idempotent: today's roster is already on disk. Re-parse it rather than
        # spend a request. `--refetch` forces the network leg.
        log(f"reusing {raw_path.name} (pass --refetch to force a new pull)")
        parse_and_write(json.loads(raw_path.read_bytes().decode("utf-8", "replace")))
        return

    claim_lock("nigc_gaming_location_roster_refresh")
    downloaded, refused = 0, []
    try:
        cj = RAW / f"_cookies_{TODAY}.txt"

        # 1. the map page - carries the per-route REST nonce table
        st, body = curl(MAP_PAGE, save_cookies=cj)
        log(f"GET {MAP_PAGE} -> {st} ({len(body)} bytes)")
        if st != 200:
            refused.append(MAP_PAGE)
            raise SystemExit(f"map page {st}")
        downloaded += 1
        page = body.decode("utf-8", "replace")
        m = re.search(r'"/datatables"\s*:\s*"(\w+)"', page)
        if not m:
            raise SystemExit("no /datatables nonce in the map page - the route "
                             "moved; re-probe before assuming absence")
        nonce = m.group(1)
        log(f"datatables nonce {nonce}")

        # 2. the marker-listing datatable through the plugin's AJAX fallback
        args = ["-X", "POST",
                "-H", f"X-WP-Nonce: {nonce}",
                "-H", "Referer: https://www.nigc.gov/map/",
                "--data-urlencode", "action=wpgmza_rest_api_request",
                "--data-urlencode", "route=/datatables/",
                "--data-urlencode", f"_wpnonce={nonce}",
                "--data-urlencode", r"phpClass=WPGMZA\MarkerListing\AdvancedTable",
                "--data-urlencode", "start=0",
                "--data-urlencode", "length=5000",
                "--data-urlencode", "draw=1",
                "--data-urlencode", 'm={"map_id":6}']
        st, body = curl(AJAX, args, cookie_jar=cj)
        log(f"POST admin-ajax /datatables/ -> {st} ({len(body)} bytes)")
        if st != 200:
            refused.append(AJAX)
            raise SystemExit(f"datatables {st}")
        downloaded += 1

        tmp = raw_path.with_suffix(".json.part")
        tmp.write_bytes(body)
        tmp.replace(raw_path)                      # never a half file at the real name
        parse_and_write(json.loads(body.decode("utf-8", "replace")))
    finally:
        release_lock(downloaded, refused)


def parse_and_write(data):
        total = data.get("recordsTotal")
        rows = data.get("data", [])
        log(f"recordsTotal={total} returned={len(rows)}")
        if total != len(rows):
            raise SystemExit(f"PARTIAL PAGE: {len(rows)} of {total}. Not written "
                             "as a roster - raise `length` and re-run.")

        # DEFECTS IN NIGC'S OWN MAP, recorded rather than smoothed over. Same
        # class as the five defects already recorded in NIGC's ordinance index.
        #   * 10 markers are CHINESE RAILWAY STATIONS (Beijing, Shanghai,
        #     Nanjing, Chengdu, Chongqing, Guangzhou South, Xiamen North, and
        #     two with CJK titles) - demo/spam rows in the WP plugin, no region
        #     category, coordinates in the address cell.
        #   * one marker is entirely blank except the address cell "California".
        #   * Golden Eagle Casino and Naskila Gaming each appear TWICE.
        # A row is a gaming location iff it carries a region category and a
        # title. That test drops the junk without naming any of it by hand.
        out, dropped = [], []
        for r in rows:
            title = strip_tags(r[1])
            region = strip_tags(r[2]) if r[2] else ""
            addr = strip_tags(r[3])
            if not region or not title:
                dropped.append({"title": title, "address": addr,
                                "reason": "no region category" if not region
                                          else "no title"})
                continue
            p = parse_address(addr)
            out.append({
                "nigc_location_name": title,
                "nigc_region_name": region.replace(" Region", "").strip(),
                "nigc_address": addr,
                "street": p["street"], "city": p["city"],
                "state": p["state"], "postal_code": p["postal_code"],
                "address_is_coordinates": p["address_is_coordinates"],
                "contact_block": strip_tags(r[4]),
                "source_url": MAP_PAGE,
                "source_route": ("admin-ajax.php action=wpgmza_rest_api_request "
                                 "route=/datatables/ m={\"map_id\":6}"),
                "fetched_date": TODAY,
            })
        log(f"gaming locations {len(out)}; dropped {len(dropped)} non-location "
            f"rows: {[d['title'] or '(blank)' for d in dropped]}")
        with open(RAW / f"nigc_roster_dropped_{TODAY}.csv", "w",
                  encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["title", "address", "reason"])
            w.writeheader()
            w.writerows(dropped)
        seen = {}
        for r in out:
            seen.setdefault((r["nigc_location_name"], r["nigc_address"]), 0)
            seen[(r["nigc_location_name"], r["nigc_address"])] += 1
        dups = {k: v for k, v in seen.items() if v > 1}
        log(f"exact duplicate markers in NIGC's roster: {len(dups)} -> "
            f"{[k[0] for k in dups]}")

        csv_path = RAW / f"nigc_roster_current_{TODAY}.csv"
        tmp = csv_path.with_suffix(".csv.part")
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
            w.writeheader()
            w.writerows(out)
        tmp.replace(csv_path)
        log(f"wrote {csv_path} ({len(out)} rows)")

        unparsed = sum(1 for r in out if not r["state"])
        log(f"addresses that did not parse to city/state: {unparsed}")


if __name__ == "__main__":
    main()
