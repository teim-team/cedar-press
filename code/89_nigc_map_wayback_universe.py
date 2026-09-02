#!/usr/bin/env python3
"""Cedar Press 89 — the NIGC gaming-location map universe over time, via Wayback.

Job: snapshot https://www.nigc.gov/map/ across years, extract each snapshot's
marker set, and diff consecutive snapshots into
`data/clean/gaming_property_universe_events.csv`.

RULES THIS SCRIPT IS BUILT AROUND
---------------------------------
1. **Disappearing from the NIGC map is NOT a closure.** It can be a delisting, a
   rename, a plugin/data refresh, or a submission gap. The event vocabulary has
   no `closed` value at all; absence is recorded as `absent_from_snapshot` and
   the event note says in as many words that it is not a closure.
2. **Every event carries the snapshot URL and the snapshot date on both sides.**
   An event with no retrievable snapshot is not written.
3. **One poller, one host.** `logs/_HOSTLOCK_web.archive.org.json` is claimed
   before the first request. Requests are sequential with a floor gap and
   exponential backoff. web.archive.org is intermittent (2026-08-06: the same
   URL answered in 2.0s and then timed out at 45s twenty minutes later), so a
   run that gets nothing is a finding, not a failure — it writes its probe log.
4. The `archive.org/wayback/available` API returned **HTTP 429** and the CDX
   endpoint **timed out at 20s** on 2026-08-06, so this script uses the
   `/web/<timestamp>/<url>` redirect route, which is what actually answered.

Writes
  data/raw/external/nigc/locations/wayback/nigc_map_<timestamp>.html   raw
  data/raw/external/nigc/locations/wayback/_probe_log_<date>.csv       evidence
  data/clean/gaming_property_universe_events.csv
"""

import csv
import hashlib
import html as html_mod
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
RAW = CEDAR / "data" / "raw" / "external" / "nigc" / "locations"
WB = RAW / "wayback"
LOGS = CEDAR / "logs"
TODAY = date.today().isoformat()

HOST = "web.archive.org"
LOCK = LOGS / f"_HOSTLOCK_{HOST}.json"
UA = "CedarPress/1.0 (research dataset; elijahsamsonmoreno@gmail.com)"

# The map lived at more than one path over the years. Try each; record which
# answered. Nothing is assumed about which existed when.
TARGETS = [
    "https://www.nigc.gov/map/",
    "https://www.nigc.gov/map",
    "http://www.nigc.gov/map/",
    "https://www.nigc.gov/gaming-locations/",
    "https://www.nigc.gov/Gaming_Locations",
]

# One capture per year. Wayback resolves a bare year to its nearest capture and
# reports the true timestamp back in the redirect URL, which is what we record —
# never the requested year.
YEARS = ["2010", "2012", "2014", "2016", "2017", "2018", "2019",
         "2020", "2021", "2022", "2023", "2024", "2025", "2026"]

MIN_GAP_S = 5.0
MAX_BACKOFF_S = 900.0
TOTAL_BUDGET_S = 3600.0


# ---------------------------------------------------------------- host lock

# --- REGENERATE GUARD (ADR-017, 2026-09-02) --------------------------------
def _carry_live_columns(path, canonical):
    """Derive this writer's header instead of declaring it.

    A wholesale writer holding a FIXED `fieldnames` list deletes every column
    an in-place enricher added since - no error, no exception, a diff nobody
    reads. Canonical order first so column order stays stable, then whatever
    the live file already carries. A retired column stays retired because it
    is not on disk; a promoted column survives because it is.

    THIS BUILD CANNOT REPOPULATE AN ENRICHER'S COLUMN. Carried columns are
    written BLANK and NAMED on stdout, which is strictly better than deleted:
    the schema survives and the enricher can refill them. Re-run the enricher
    after this build - `cedar_pipeline.enrichers_to_rerun(<table>)` names it.
    """
    import csv as _csv
    import os as _os
    canonical = list(canonical)
    _p = str(path)
    if not _os.path.exists(_p):
        return canonical
    with open(_p, encoding="utf-8-sig", newline="", errors="replace") as _fh:
        _live = next(_csv.reader(_fh), [])
    _extra = [c for c in _live if c and c not in canonical]
    if _extra:
        print("  [regenerate guard] %s: carrying %d enricher column(s) through "
              "this rebuild, BLANK - re-run the enricher: %s"
              % (_os.path.basename(_p), len(_extra), ", ".join(_extra)))
    return canonical + _extra


def claim_lock(note):
    LOGS.mkdir(parents=True, exist_ok=True)
    if LOCK.exists():
        try:
            cur = json.load(open(LOCK, encoding="utf-8"))
        except Exception:
            cur = {}
        if cur.get("pid") and cur.get("pid") != os.getpid() and cur.get("active"):
            print(f"HOSTLOCK held by pid {cur['pid']}: {cur.get('claimed_by')}")
            print("Appending to its queue and exiting, per docs/PULL_DISCIPLINE.md.")
            cur.setdefault("queue", []).append({"at": datetime.now().isoformat(),
                                                "want": note})
            json.dump(cur, open(LOCK, "w", encoding="utf-8"), indent=2)
            sys.exit(0)
    json.dump({"host": HOST, "claimed_by": note, "pid": os.getpid(),
               "claimed_at": datetime.now().isoformat(), "active": True,
               "policy": f"sequential, >={MIN_GAP_S}s gap, exponential backoff to "
                         f"{MAX_BACKOFF_S}s, /web/ redirect route only "
                         "(availability API 429, CDX timeout at 20s on 2026-08-06)",
               "queue": []},
              open(LOCK, "w", encoding="utf-8"), indent=2)


def release_lock():
    try:
        cur = json.load(open(LOCK, encoding="utf-8"))
    except Exception:
        return
    cur["active"] = False
    cur["released_at"] = datetime.now().isoformat()
    json.dump(cur, open(LOCK, "w", encoding="utf-8"), indent=2)


# ---------------------------------------------------------------- fetching

PROBES = []
_last_request = [0.0]
_backoff = [0.0]
_started = [time.time()]


def fetch(url, timeout=45):
    """One request. Records every outcome to the probe log, success or not.

    Distinguishes, per docs/PULL_DISCIPLINE.md, an EDGE BLOCK (instant refusal,
    under 1s) from a THROTTLE (429) from a SLOW SERVER (timeout). Only the last
    two are worth retrying, and they are retried differently.
    """
    gap = MIN_GAP_S + _backoff[0]
    wait = gap - (time.time() - _last_request[0])
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    t0 = time.time()
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        body = r.read()
        el = time.time() - t0
        _last_request[0] = time.time()
        _backoff[0] = max(0.0, _backoff[0] / 2)
        PROBES.append({"requested_url": url, "outcome": "HTTP_200",
                       "http_status": r.status, "elapsed_s": round(el, 2),
                       "bytes": len(body), "final_url": r.url,
                       "probed_at": datetime.now().isoformat()})
        return body, r.url
    except urllib.error.HTTPError as e:
        el = time.time() - t0
        _last_request[0] = time.time()
        kind = "THROTTLE_429" if e.code == 429 else f"HTTP_{e.code}"
        if e.code == 429:
            _backoff[0] = min(MAX_BACKOFF_S, max(60.0, _backoff[0] * 2))
        PROBES.append({"requested_url": url, "outcome": kind, "http_status": e.code,
                       "elapsed_s": round(el, 2), "bytes": 0, "final_url": "",
                       "probed_at": datetime.now().isoformat()})
        return None, None
    except Exception as e:
        el = time.time() - t0
        _last_request[0] = time.time()
        # under 1s == the edge refused us; 20s+ == the server is just slow.
        kind = "EDGE_BLOCK" if el < 1.0 else "TIMEOUT"
        if kind == "EDGE_BLOCK":
            _backoff[0] = min(MAX_BACKOFF_S, max(60.0, _backoff[0] * 2))
        else:
            _backoff[0] = min(MAX_BACKOFF_S, max(15.0, _backoff[0] * 2))
        PROBES.append({"requested_url": url, "outcome": kind, "http_status": "",
                       "elapsed_s": round(el, 2), "bytes": 0, "final_url": "",
                       "probed_at": datetime.now().isoformat(),
                       "error": f"{type(e).__name__}: {e}"[:200]})
        return None, None


TS_RE = re.compile(r"/web/(\d{14})(?:id_)?/")


def snapshot_timestamp(final_url):
    m = TS_RE.search(final_url or "")
    return m.group(1) if m else ""


# ------------------------------------------------------- marker extraction

def extract_markers(html):
    """Pull the marker set out of a captured NIGC map page.

    THREE routes, tried in order, because the page changed plugin over time.
    Whichever fires is recorded on every marker as `extract_route`, so a diff
    between two snapshots can be checked for being an artefact of the route
    rather than a real change in the universe. That check matters: a route
    change that drops the address field would otherwise read as 490 properties
    all "moving" in one year.
    """
    out, route = [], ""

    # Route A: WP Google Maps localizes its marker array into a <script>.
    for m in re.finditer(r"wpgmza[_a-zA-Z]*\s*=\s*(\[.*?\]);", html, re.S):
        try:
            arr = json.loads(m.group(1))
        except Exception:
            continue
        if isinstance(arr, list) and arr and isinstance(arr[0], dict):
            for d in arr:
                if "lat" in d or "title" in d:
                    out.append(d)
            route = "wpgmza_localized_script_array"
    if out:
        return out, route

    # Route B: the older plugin printed one <div class="wpgmza_marker"> per
    # marker with data- attributes.
    for m in re.finditer(
            r'data-lat="([-0-9.]+)"[^>]*data-lng="([-0-9.]+)"[^>]*data-title="([^"]*)"',
            html):
        out.append({"lat": m.group(1), "lng": m.group(2), "title": m.group(3)})
    if out:
        return out, "marker_div_data_attributes"

    # Route C: the PRE-WORDPRESS nigc.gov map (observed on the 2015-10-02
    # capture). It embedded the whole universe as a hidden HTML table inside
    # `<div id="locations" style="display:none">`, one <tr> per location with
    # td.title / td.address / td.phone / td.region / td.lat / td.lon. The
    # JavaScript read that table to build the markers, so the table IS the
    # marker set and no AJAX call has to be replayed. It carries MORE than
    # today's JSON does — NIGC's own region name is a column.
    block = html
    mdiv = re.search(r'<div id="locations".*?>(.*?)</div>', html, re.S)
    if mdiv:
        block = mdiv.group(1)
    for tr in re.split(r"<tr[^>]*>", block):
        if 'class="lat"' not in tr:
            continue
        def td(cls):
            m = re.search(r'<td class="%s">(.*?)</td>' % cls, tr, re.S)
            if not m:
                return ""
            s = re.sub(r"<br\s*/?>", ", ", m.group(1))
            s = re.sub(r"<[^>]+>", " ", s)
            return re.sub(r"\s+", " ", s).strip().strip(",").strip()
        lat, lon, title = td("lat"), td("lon") or td("lng"), td("title")
        if not title:
            continue
        out.append({"lat": lat, "lng": lon, "title": unesc(title),
                    "address": unesc(td("address")), "region": td("region"),
                    "phone": td("phone")})
    if out:
        return out, "hidden_locations_table_td_classes"

    # Route D: an inline `new google.maps.Marker({position: new LatLng(..)..})`
    for m in re.finditer(
            r"LatLng\(\s*([-0-9.]+)\s*,\s*([-0-9.]+)\s*\).{0,400}?title\s*:\s*"
            r"[\"']([^\"']{2,120})[\"']", html, re.S):
        out.append({"lat": m.group(1), "lng": m.group(2), "title": m.group(3)})
    if out:
        return out, "inline_google_maps_marker"

    return [], "no_marker_route_matched"


def unesc(s):
    """Decode HTML entities BEFORE anything compares two strings.

    THIS IS NOT COSMETIC AND THE FIRST RUN PROVED IT. The 2015 capture stores
    `Graton Resort &amp; Casino` and the 2026 JSON stores `Graton Resort &
    Casino`. Without decoding, `norm_title` turns the first into
    "graton resort amp casino" and the second into "graton resort casino", and
    the SAME PROPERTY is emitted twice — once as `absent_from_snapshot` in 2015
    and once as `present_in_snapshot` in 2026. That is a fabricated pair of
    events on a casino that never went anywhere, and it fired on 419 address
    diffs and dozens of title diffs before this was added.
    """
    return html_mod.unescape(s or "")


def norm_title(t):
    t = re.sub(r"\s*\(\d+\)\s*$", "", unesc(t))       # NIGC appends "(4)" etc.
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def norm_addr(a):
    """Compare addresses on content, not punctuation.

    The 2015 table prints `Rohnert Park, CA 94928` and the 2026 JSON prints
    `Rohnert Park CA 94928`. Comparing raw strings reports every one of 419
    markers as having changed address in a single interval, which is obviously
    a formatting change at source and not 419 relocations. Only a difference
    that survives this normalisation is emitted as an event.
    """
    a = re.sub(r"[^a-z0-9]+", " ", unesc(a).lower()).strip()
    # A trailing ZIP that lost its leading zero is a source artefact, not a
    # move. NIGC's current JSON prints Uncasville CT as `6382` and Mashantucket
    # CT as `6338` where the 2015 table printed `06382` and `06338` — numeric
    # coercion somewhere in the plugin. Those two were the ONLY address_changed
    # events in the 2015->2026 interval before this line existed, and neither
    # casino has moved an inch.
    return re.sub(r"\b0*(\d{4,5})\s*$", lambda m: m.group(1).lstrip("0"), a)


# ------------------------------------------------------------------- main

def main():
    WB.mkdir(parents=True, exist_ok=True)
    claim_lock("script 89 — NIGC map universe over time (gaming triage agent)")
    print("=== Cedar Press 89: NIGC map universe via Wayback ===\n")

    snapshots = {}   # timestamp -> {markers, route, url, requested}
    try:
        for year in YEARS:
            if time.time() - _started[0] > TOTAL_BUDGET_S:
                print("  budget exhausted; stopping cleanly")
                break
            got = False
            for target in TARGETS:
                url = f"https://web.archive.org/web/{year}/{target}"
                body, final = fetch(url)
                if not body:
                    print(f"  {year} {target[:44]:44s} -> {PROBES[-1]['outcome']}")
                    continue
                ts = snapshot_timestamp(final)
                html = body.decode("utf-8", "replace")
                markers, route = extract_markers(html)
                print(f"  {year} {target[:44]:44s} -> ts={ts or '?'} "
                      f"{len(markers)} markers via {route}")
                if not ts:
                    continue
                p = WB / f"nigc_map_{ts}.html"
                p.write_bytes(body)
                if markers:
                    snapshots[ts] = {"markers": markers, "route": route,
                                     "snapshot_url": final, "requested_year": year,
                                     "target": target, "local": str(p),
                                     "md5": hashlib.md5(body).hexdigest()}
                    got = True
                    break
            if not got:
                print(f"  {year}: no snapshot with an extractable marker set")
    finally:
        release_lock()

    # probe log always written — a blocked run must leave its evidence
    if PROBES:
        keys = ["requested_url", "outcome", "http_status", "elapsed_s", "bytes",
                "final_url", "probed_at", "error"]
        with open(WB / f"_probe_log_{TODAY}.csv", "w", encoding="utf-8",
                  newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            w.writerows(PROBES)
        print(f"\nprobe log: {len(PROBES)} probes -> "
              f"{(WB / f'_probe_log_{TODAY}.csv').relative_to(CEDAR)}")

    if len(snapshots) < 2:
        print(f"\nOnly {len(snapshots)} usable snapshot(s). A universe diff needs "
              "two. Writing no event file; the probe log is the finding.")
        return

    build_events(snapshots)


def build_events(snapshots):
    order = sorted(snapshots)
    events = []
    for a, b in zip(order, order[1:]):
        A, B = snapshots[a], snapshots[b]
        route_changed = A["route"] != B["route"]
        ia = {norm_title(m.get("title")): m for m in A["markers"] if m.get("title")}
        ib = {norm_title(m.get("title")): m for m in B["markers"] if m.get("title")}

        def ev(kind, key, m, note, extra=None):
            d = {
                "event_id": f"NIGCMAP-{b}-{hashlib.md5(key.encode()).hexdigest()[:8]}",
                "event_type": kind,
                "marker_title": unesc((m or {}).get("title", "")),
                "marker_address": unesc((m or {}).get("address", "")),
                "latitude": (m or {}).get("lat", ""),
                "longitude": (m or {}).get("lng", ""),
                "from_snapshot_timestamp": a,
                "from_snapshot_date": f"{a[:4]}-{a[4:6]}-{a[6:8]}",
                "from_snapshot_url": A["snapshot_url"],
                "to_snapshot_timestamp": b,
                "to_snapshot_date": f"{b[:4]}-{b[4:6]}-{b[6:8]}",
                "to_snapshot_url": B["snapshot_url"],
                "from_marker_count": len(A["markers"]),
                "to_marker_count": len(B["markers"]),
                "extract_route_from": A["route"],
                "extract_route_to": B["route"],
                "extract_route_changed": int(route_changed),
                "event_note": note,
                "source_url": "https://www.nigc.gov/map/",
                "built_date": TODAY,
            }
            d.update(extra or {})
            events.append(d)

        # RENAMES FIRST. A property whose NAME changed appears as an absence and
        # a presence — two events for one non-event, and the absence is exactly
        # the shape this dataset must never publish as a closure. `San Manuel
        # Indian Bingo & Casino` and `Yaamava' Resort & Casino at San Manuel`
        # are one building at 777 San Manuel Blvd; `Fort McDowell Gaming Center`
        # and `Fort McDowell Casino` are one building on Fort McDowell Rd.
        # Pairing them on an EXACT normalised address — a deterministic key, not
        # a name match, and the one field a rename does not touch — turns six
        # misleading events into three correct ones.
        gone, came = ia.keys() - ib.keys(), ib.keys() - ia.keys()
        addr_gone = {}
        for k in gone:
            na = norm_addr(ia[k].get("address"))
            if na:
                addr_gone.setdefault(na, []).append(k)
        renamed_from, renamed_to = {}, set()
        for k in came:
            na = norm_addr(ib[k].get("address"))
            cands = addr_gone.get(na, [])
            if len(cands) == 1 and na:          # one-to-one only; never a guess
                renamed_from[k] = cands[0]
                renamed_to.add(cands[0])
        for k, oldk in renamed_from.items():
            ev("renamed", k, ib[k],
               "Marker name changed while its address stayed identical after "
               "normalisation. Recorded as ONE rename, not as a disappearance "
               "plus an appearance. The address is the field a rename does not "
               "touch, so it is the key used; the pairing is one-to-one and "
               "nothing is paired on a name.",
               {"prior_marker_title": ia[oldk].get("title", ""),
                "prior_address": ia[oldk].get("address", "")})

        for k in came - set(renamed_from):
            ev("present_in_snapshot", k, ib[k],
               "Marker present in the later snapshot and not the earlier one. "
               "This is a LISTING event, not an opening: NIGC's map is a "
               "published roster and a marker can appear because the location "
               "was newly listed, renamed, or re-submitted.")
        for k in gone - renamed_to:
            ev("absent_from_snapshot", k, ia[k],
               "Marker present in the earlier snapshot and absent from the "
               "later one. THIS IS NOT A CLOSURE. It can be a delisting, a "
               "rename, a data refresh or a submission gap. No closure is "
               "claimed anywhere in this dataset without a document that says "
               "closed.")
        for k in ia.keys() & ib.keys():
            ma, mb = ia[k], ib[k]
            try:
                moved = (abs(float(ma.get("lat") or 0) - float(mb.get("lat") or 0)) > 0.005
                         or abs(float(ma.get("lng") or 0) - float(mb.get("lng") or 0)) > 0.005)
            except (TypeError, ValueError):
                moved = False
            if moved:
                ev("coordinates_changed", k, mb,
                   "Marker coordinates moved between snapshots. A coordinate "
                   "change can be a relocation OR a geocoding correction; the "
                   "map does not distinguish them and neither does this row.",
                   {"prior_latitude": ma.get("lat", ""),
                    "prior_longitude": ma.get("lng", "")})
            aa, ab = (ma.get("address") or ""), (mb.get("address") or "")
            if aa and ab and norm_addr(aa) != norm_addr(ab):
                ev("address_changed", k, mb,
                   "Marker address changed between snapshots, and the change "
                   "survives normalisation for punctuation, case and HTML "
                   "entities. May be a move, a re-address, or a correction; the "
                   "map does not distinguish them and neither does this row.",
                   {"prior_address": unesc(aa)})

        if route_changed:
            print(f"  WARNING {a} -> {b}: extraction route changed "
                  f"({A['route']} -> {B['route']}). Every event in this pair "
                  "carries extract_route_changed=1 and should be read as "
                  "possibly an artefact of the page's own markup change.")

    EVENT_CANONICAL = ["event_id", "event_type", "marker_title",
                       "prior_marker_title", "marker_address",
                       "latitude", "longitude", "prior_latitude",
                       "prior_longitude", "prior_address",
                       "from_snapshot_timestamp", "from_snapshot_date",
                       "from_snapshot_url", "to_snapshot_timestamp",
                       "to_snapshot_date", "to_snapshot_url",
                       "from_marker_count", "to_marker_count",
                       "extract_route_from", "extract_route_to",
                       "extract_route_changed", "event_note", "source_url",
                       "built_date"]
    out = CLEAN / "gaming_property_universe_events.csv"
    fields = _carry_live_columns(out, EVENT_CANONICAL)
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore",
                           restval="")
        w.writeheader()
        w.writerows(events)
    print(f"\nwrote {out.relative_to(CEDAR)}  ({len(events):,} events over "
          f"{len(order)} snapshots)")


def offline():
    """Rebuild the universe from HTML already on disk. No network at all.

    The poller writes every capture it retrieves before it tries to parse it,
    so extraction can be improved and re-run without touching web.archive.org
    again. That matters here: web.archive.org was intermittent all session and
    a re-fetch to fix a regex would have been an avoidable request against a
    host that was already refusing.

    The CURRENT marker set is added as the final snapshot from the structured
    admin-ajax JSON already held in data/raw/, so the last diff interval is
    against today's real universe rather than against the newest capture.
    """
    snapshots = {}
    for p in sorted(WB.glob("nigc_map_*.html")):
        ts = p.stem.split("_")[-1]
        html = p.read_text(encoding="utf-8", errors="replace")
        markers, route = extract_markers(html)
        print(f"  {ts}  {len(markers):4d} markers via {route}   {p.name}")
        if markers:
            snapshots[ts] = {
                "markers": markers, "route": route,
                "snapshot_url": f"https://web.archive.org/web/{ts}/https://www.nigc.gov/map/",
                "requested_year": ts[:4], "target": "https://www.nigc.gov/map/",
                "local": str(p), "md5": hashlib.md5(p.read_bytes()).hexdigest()}

    cur = RAW / "nigc_gaming_locations_map6_2026-08-06.json"
    if cur.exists():
        raw = json.load(open(cur, encoding="utf-8"))
        ms = [{"lat": m.get("lat"), "lng": m.get("lng"), "title": m.get("title"),
               "address": m.get("address")} for m in raw]
        snapshots["20260806000000"] = {
            "markers": ms, "route": "admin_ajax_map6_json_live_pull",
            "snapshot_url": "https://www.nigc.gov/map/  (admin-ajax.php map_id=6, "
                            "pulled 2026-08-06, held at "
                            "data/raw/external/nigc/locations/)",
            "requested_year": "2026", "target": "https://www.nigc.gov/map/",
            "local": str(cur), "md5": ""}
        print(f"  20260806  {len(ms):4d} markers via admin_ajax_map6_json_live_pull "
              "(current universe, not a Wayback capture)")

    if len(snapshots) < 2:
        print(f"\nOnly {len(snapshots)} usable snapshot(s); a diff needs two.")
        return
    build_events(snapshots)


if __name__ == "__main__":
    if "--offline" in sys.argv:
        offline()
    else:
        main()
