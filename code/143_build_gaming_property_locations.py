#!/usr/bin/env python3
r"""
143_build_gaming_property_locations.py -- Cedar Press

A PUBLISHABLE address + latitude/longitude layer for the gaming property
universe, sourced entirely from free official sources.

Writes  data/clean/gaming_property_locations.csv   (one row per property per
                                                    source observation)
        data/raw/external/gaming/locations/*       (raw geocoder responses)
        review/gaming_locations_vendor_only_<date>.csv
        review/gaming_locations_geocode_conflicts_<date>.csv

`data/clean/gaming_facilities.csv` IS NOT TOUCHED. The merge is proposed in
`docs/GAMING_LOCATION_LAYER.md`, not performed.


WHY THIS EXISTS, GIVEN THAT 89% OF THE FILE IS ALREADY GEOCODED
---------------------------------------------------------------
`gaming_facilities.csv` carries 688 coordinates and 677 addresses. Almost none
of it can ship.

    coords_basis = "Casino City Press coordinates"      430 rows
    source_datasets names casino_city_press             440 rows
    casino_city_id present                              595 rows

and the standing rule in `docs/GAMING_SPEC_RECONCILIATION.md` is: *"Casino City
may be read for QA and may never be published or resold."*

THE FINDING THAT REFRAMES THE JOB. `tribal_property_list` IS ALSO CASINO CITY.
It is the *Casino City Tribal Property List* -- 23d says so in as many words
(`open_date_basis = "Casino City Tribal Property List, 'Open Date'"`). So the
vendor-derived share of the file is not 440 rows, it is **610 of 774**, and only
`votingpatterns_canonical` (164 rows) is free-sourced end to end.

That inverts the apparent priority. The brief said 68 of the 86 properties with
no coordinate "already have an address to work with." They do -- and **all 68
of those addresses are Casino City's.** Every one of the 86 uncoordinated rows
is `tribal_property_list`-sourced. Geocoding them would produce 68 coordinates
that still cannot ship, because re-geocoding a vendor address does not launder
it: the ADDRESS is the vendor's fact, and the coordinate is derived from it.

So the work is not gap-filling. It is re-sourcing.


THE SOURCES, AND WHAT EACH ONE IS AUTHORITATIVE FOR
---------------------------------------------------
1. **NIGC gaming location map** (`nigc_gaming_locations_map6_2026-08-06.json`,
   490 markers, already on disk). A federal regulator publishing the address and
   the point of every gaming location it maps. Free, official, quotable.
   Attached to Cedar IDs through the EXISTING deterministic roster match in
   `review/nigc_roster_diff_2026-08-06.csv` (350 MATCHED). **No new match is
   invented here** and no new property ID is created; the 140 unmatched NIGC
   markers remain staged in `review/gaming_additions_2026-08-06.csv` behind
   `do_not_append_without_ruling`.

2. **US Census Geocoder** (free, no key). Two distinct services, kept as two
   distinct observations because they are two different facts:
     - `addressbatch`  address -> coordinate, with Match/Tie/No_Match and
                       Exact/Non_Exact, plus state/county/tract/block.
     - `geographies/coordinates`  a coordinate -> the block it falls in.
   The second is applied to every free-sourced coordinate, which is what turns
   this layer into a LODES join key.

3. **votingpatterns canonical casino addresses** (411 records). Addresses and
   coordinates compiled from each property's OWN official website (the `source`
   column names the site). Free and official in origin. Its weakness is
   documentation, not licence -- the compilation preserved no URL, no retrieval
   date and no quote -- so it publishes at tier C, promoted to tier B where the
   Census Geocoder returns an Exact match on the same address.

4. **California CGCC licensed-facility list** (`ca_gaming_facilities_official`,
   245 rows already keyed to facility_id). City and county only, no street. It
   still earns a row: an official county assignment is exactly what a
   county-level join needs, and it corroborates the geocoded county.

5. **Casino City Press / Tribal Property List.** Recorded, never publishable.
   Present so the vendor dependency is visible and measurable per property
   rather than inferred from a column name.

6. **Indian Gaming Dataset.** Not Casino City, but its address column carries no
   stated origin, no URL and no retrieval date. Recorded at tier C with
   `publishable = N` and the reason named. A source whose provenance is unknown
   is not a free source; it is an unsourced one.

REFUSED, AND WHY (see the report and docs/GAMING_LOCATION_LAYER.md):
  - `bia_compact_properties_geocoded_v2.csv` (766 rows). Its addresses are
    regex-extracted from compact PDF text and are frequently not property
    addresses at all -- `11 Supreme Court`, `202 East Drive`. 590 of 766 are
    `No_Match`, `casino_name_candidate` is null on nearly all of them, and
    nothing keys a row to a facility. Attaching a compact's stray street string
    to a casino is the false-attribution trap, so it is not used.
  - Property websites. Another agent holds those hosts for capacity; ~100
    `logs/_HOSTLOCK_*.json` files exist for casino domains. Not crawled here.


THE RULES THIS FILE IS BUILT AROUND
-----------------------------------
* **`publishable = N` for anything traceable to Casino City**, including any
  coordinate derived from a Casino City address. `publishable_reason` states the
  ground per row; it is never left to be inferred from a source name.
* **`county_fips`, `census_tract`, `census_block` are TEXT.** Leading zeros are
  real -- `01053`, `090117011005003`. Written zero-padded and quoted.
* **A geocode is a dated observation with a match quality.** `Exact` and
  `Non_Exact` are separate facts and are stored separately; a coordinate the
  source itself published (`SOURCE_PUBLISHED_POINT`) is a third thing again and
  never merged with either.
* **The coordinate locates the PROPERTY, not the enterprise.** A tribal gaming
  campus routinely holds a hotel, a travel plaza, a c-store, a clinic and the
  tribal administration inside one block group. `coordinate_scope_note` travels
  on every row so the caveat cannot be lost in a join, and it matters directly
  for LODES: block workplace jobs are jobs in that block, not casino payroll.
* Attach to existing `CCP-`/`VP-`/`TPL-` IDs. **No new IDs are minted here.**
* One poller per host, sequential, wall-clock deadline, stop on first refusal.
"""

import argparse
import csv
import io
import json
import math
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
LOGS = CEDAR / "logs"
SRC_DIR = CEDAR / "data" / "raw" / "external" / "gaming" / "directory_core"
NIGC_DIR = CEDAR / "data" / "raw" / "external" / "nigc" / "locations"
RAW_OUT = CEDAR / "data" / "raw" / "external" / "gaming" / "locations"
RAW_OUT.mkdir(parents=True, exist_ok=True)

TODAY = date.today().isoformat()
SCRIPT = "code/143_build_gaming_property_locations.py"
UA = "CedarPress/1.0 (research data build; elijahsamsonmoreno@gmail.com)"
HOST = "geocoding.geo.census.gov"
GEO_HOST_LOCK = LOGS / f"_HOSTLOCK_{HOST}.json"

BENCHMARK = "Public_AR_Current"
VINTAGE = "Census2020_Current"          # 2020 blocks == the LODES8 block vintage

DEADLINE_MIN = 45
FLOOR_GAP_S = 0.35

SCOPE_NOTE = (
    "The coordinate locates the gaming PROPERTY, not the enterprise. Tribal "
    "gaming properties commonly sit on a mixed-use campus (hotel, travel plaza, "
    "convenience store, clinic, tribal administration), so a census block "
    "containing this point may contain several establishments and several "
    "employers. LODES block workplace jobs are jobs located in the block, never "
    "casino payroll."
)

_log_buf = io.StringIO()


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    _log_buf.write(s + "\n")


# --------------------------------------------------------------------------
# normalisation -- deliberately identical to 23d_build_gaming_facilities.py so
# the property match reproduces that build's keys exactly rather than drifting.
# --------------------------------------------------------------------------
def norm(s):
    if s is None or (isinstance(s, float) and math.isnan(s)):
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9]+", " ", s).lower().strip()
    return re.sub(r"\s+", " ", s)


def sv(v):
    if v is None:
        return ""
    if isinstance(v, float) and math.isnan(v):
        return ""
    v = str(v).strip()
    return "" if v.lower() in ("nan", "nat", "none") else v


STATE_ABBR = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Idaho": "ID", "Illinois": "IL",
    "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY",
    "Louisiana": "LA", "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA",
    "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO",
    "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH",
    "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH",
    "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA",
    "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
    "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY",
}


def st(v):
    v = sv(v)
    if len(v) == 2:
        return v.upper()
    return STATE_ABBR.get(v.title(), v.upper()[:2] if v else "")


def key(name, state):
    return (norm(name), st(state))


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def fnum(v):
    try:
        f = float(v)
        return f if not math.isnan(f) else None
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------
# address typing. A mailing address is not a location, and saying so up front
# stops a PO-Box ZIP centroid from being read as a rooftop.
# --------------------------------------------------------------------------
PO_BOX = re.compile(r"\b(p\.?\s*o\.?\s*box|post\s+office\s+box|general\s+delivery)\b", re.I)
NON_STD = re.compile(
    r"\b(highway|hwy|exit|milepost|mile\s+marker|route|rr\s*\d|rural\s+route|"
    r"junction|jct|county\s+road|state\s+road|interstate|i-\d)\b", re.I)


def address_type(addr):
    a = sv(addr)
    if not a:
        return "ABSENT"
    if PO_BOX.search(a):
        return "PO_BOX_MAILING_ADDRESS"
    if re.match(r"^\s*\d+\s+\S", a) and not NON_STD.search(a):
        return "STREET"
    if NON_STD.search(a):
        return "NON_STANDARD_ROUTE_OR_LANDMARK"
    return "NON_STANDARD"


NIGC_ADDR = re.compile(
    r"^(?P<street>.+?),\s*(?P<city>[^,]+?)[,\s]+(?P<state>[A-Z]{2})\.?\s*"
    r"(?P<zip>\d{5}(?:-\d{4})?)?\s*$")


def parse_nigc_address(raw):
    """NIGC publishes one string: '271 Cayuga Street, Union Springs NY 13160'.
    Returns (street, city, state, zip). Anything that does not parse keeps the
    whole string in `street` and leaves the rest blank -- never guessed."""
    a = sv(raw).replace("\u2019", "'").strip().rstrip(",")
    if not a:
        return "", "", "", ""
    m = NIGC_ADDR.match(a)
    if not m:
        return a, "", "", ""
    return (m.group("street").strip(), m.group("city").strip(),
            (m.group("state") or "").upper(), (m.group("zip") or "").strip())


# ==========================================================================
# HOST DISCIPLINE
# ==========================================================================
def claim_host(note, queue):
    prior = {}
    if GEO_HOST_LOCK.exists():
        try:
            prior = json.load(open(GEO_HOST_LOCK, encoding="utf-8"))
        except Exception:
            prior = {}
    if prior.get("active") and prior.get("script") != SCRIPT:
        log(f"REFUSED: {HOST} is claimed by {prior.get('script')} "
            f"(pid {prior.get('pid')}). Appending to its queue and exiting.")
        prior.setdefault("queue", []).extend(queue)
        json.dump(prior, open(GEO_HOST_LOCK, "w", encoding="utf-8"), indent=1)
        sys.exit(0)
    json.dump({"host": HOST, "pid": os.getpid(), "script": SCRIPT, "active": True,
               "started": datetime.now(timezone.utc).isoformat(),
               "queue": queue, "note": note, "released": ""},
              open(GEO_HOST_LOCK, "w", encoding="utf-8"), indent=1)


def release_host():
    try:
        d = json.load(open(GEO_HOST_LOCK, encoding="utf-8"))
    except Exception:
        return
    d["active"] = False
    d["released"] = datetime.now(timezone.utc).isoformat()
    json.dump(d, open(GEO_HOST_LOCK, "w", encoding="utf-8"), indent=1)


class Refusal(Exception):
    pass


_last_req = [0.0]


def _gap():
    dt = time.time() - _last_req[0]
    if dt < FLOOR_GAP_S:
        time.sleep(FLOOR_GAP_S - dt)
    _last_req[0] = time.time()


def http(req, timeout=(20, 180)):
    """Distinguish an edge block (instant transport failure) from a throttle
    from a slow server. Per docs/PULL_DISCIPLINE.md a 0 is stop-work."""
    _gap()
    t0 = time.time()
    try:
        r = urllib.request.urlopen(req, timeout=timeout[1])
        return r.status, r.read()
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise Refusal(f"HTTP 429 throttle after {time.time()-t0:.1f}s")
        return e.code, b""
    except Exception as e:
        dt = time.time() - t0
        if dt < 1.0:
            raise Refusal(f"transport failure in {dt:.2f}s ({type(e).__name__}) "
                          f"-- reads as an edge block, stopping")
        raise


# ==========================================================================
# CENSUS GEOCODER
# ==========================================================================
BATCH_URL = f"https://{HOST}/geocoder/geographies/addressbatch"
COORD_URL = f"https://{HOST}/geocoder/geographies/coordinates"


def census_batch(records):
    """records: list of (uid, street, city, state, zip). Returns dict uid->row.
    The batch endpoint takes 10,000 per file; chunked at 250 so a refusal costs
    one small chunk and the checkpoint stays fine-grained."""
    out = {}
    CH = 250
    for i in range(0, len(records), CH):
        chunk = records[i:i + CH]
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        for uid, s1, c, s2, z in chunk:
            w.writerow([uid, s1, c, s2, z])
        payload_csv = buf.getvalue().encode("utf-8")

        # lint-ok: class7 - this is a MULTIPART FORM BOUNDARY for an HTTP POST to the
        # Census batch geocoder, not an id. It must be unique within one request and must
        # never be reused; a deterministic value would be the defect here. Nothing about
        # it is written to a row. Triaged LOW by 326_triage_class7_key_risk.py 2026-08-26.
        b = "----cedar" + uuid.uuid4().hex
        parts = [
            (f'--{b}\r\nContent-Disposition: form-data; name="addressFile"; '
             f'filename="batch.csv"\r\nContent-Type: text/csv\r\n\r\n').encode()
            + payload_csv + b"\r\n"]
        for n, v in (("benchmark", BENCHMARK), ("vintage", VINTAGE)):
            parts.append((f'--{b}\r\nContent-Disposition: form-data; '
                          f'name="{n}"\r\n\r\n{v}\r\n').encode())
        parts.append(f"--{b}--\r\n".encode())
        req = urllib.request.Request(
            BATCH_URL, data=b"".join(parts),
            headers={"User-Agent": UA,
                     "Content-Type": "multipart/form-data; boundary=" + b})
        status, body = http(req)
        if status != 200:
            log(f"  batch chunk {i//CH}: HTTP {status} -- chunk skipped, "
                f"recorded as not attempted")
            continue
        text = body.decode("utf-8", "replace")
        (RAW_OUT / f"census_addressbatch_{TODAY}_{i//CH:03d}.csv").write_text(
            text, encoding="utf-8")
        for row in csv.reader(io.StringIO(text)):
            if not row:
                continue
            uid = row[0]
            rec = {"input": row[1] if len(row) > 1 else "",
                   "match": row[2] if len(row) > 2 else "",
                   "quality": row[3] if len(row) > 3 else "",
                   "matched_address": "", "lon": "", "lat": "",
                   "state": "", "county": "", "tract": "", "block": ""}
            if rec["match"] == "Match" and len(row) >= 12:
                rec["matched_address"] = row[4]
                ll = row[5].split(",")
                if len(ll) == 2:
                    rec["lon"], rec["lat"] = ll[0], ll[1]
                rec["state"], rec["county"] = row[8], row[9]
                rec["tract"], rec["block"] = row[10], row[11]
            out[uid] = rec
        log(f"  batch chunk {i//CH}: {len(chunk)} sent, {len(out)} cumulative")
    return out


_coord_cache = {}


def census_coord(lat, lon):
    """One coordinate -> county name+FIPS, tract, block. Cached on the rounded
    pair so two sources agreeing to 6dp cost one request, not two."""
    ck = (round(float(lat), 6), round(float(lon), 6))
    if ck in _coord_cache:
        return _coord_cache[ck]
    q = urllib.parse.urlencode({
        "x": lon, "y": lat, "benchmark": BENCHMARK, "vintage": VINTAGE,
        "format": "json", "layers": "Census Blocks,Counties,Census Tracts"})
    status, body = http(urllib.request.Request(COORD_URL + "?" + q,
                                               headers={"User-Agent": UA}))
    res = {"county_fips": "", "county_name": "", "tract": "", "block": ""}
    if status == 200:
        try:
            g = json.loads(body.decode("utf-8", "replace"))["result"]["geographies"]
            blocks = g.get("Census Blocks") or []
            counties = g.get("Counties") or []
            tracts = g.get("Census Tracts") or []
            if blocks:
                b0 = blocks[0]
                res["block"] = sv(b0.get("GEOID"))
                res["tract"] = (sv(b0.get("STATE")) + sv(b0.get("COUNTY"))
                                + sv(b0.get("TRACT")))
                res["county_fips"] = sv(b0.get("STATE")) + sv(b0.get("COUNTY"))
            if tracts and not res["tract"]:
                res["tract"] = sv(tracts[0].get("GEOID"))
            if counties:
                res["county_fips"] = res["county_fips"] or sv(counties[0].get("GEOID"))
                res["county_name"] = sv(counties[0].get("NAME"))
        except Exception as e:
            log(f"  coord parse failure at {lat},{lon}: {type(e).__name__}")
    _coord_cache[ck] = res
    return res


# ==========================================================================
# HARVEST -- free official observations, keyed to EXISTING property IDs
# ==========================================================================
def load_facilities():
    f = pd.read_csv(CLEAN / "gaming_facilities.csv", dtype=str, low_memory=False)
    f = f.fillna("")
    return f


def build_indexes(fac):
    name_idx, addr_idx = defaultdict(list), defaultdict(list)
    for r in fac.to_dict("records"):
        name_idx[key(r["facility_name"], r["state"])].append(r["facility_id"])
        if sv(r["address"]):
            addr_idx[key(r["address"], r["state"])].append(r["facility_id"])
    return name_idx, addr_idx


def harvest(fac):
    """Every observation, free and vendor alike. Returns list of dicts."""
    obs = []
    name_idx, addr_idx = build_indexes(fac)
    fmap = {r["facility_id"]: r for r in fac.to_dict("records")}

    # ---- 1. NIGC gaming location map -------------------------------------
    markers = json.load(open(NIGC_DIR / "nigc_gaming_locations_map6_2026-08-06.json",
                             encoding="utf-8"))
    mk = {sv(m.get("id") or m.get("marker_id") or ""): m for m in markers}
    if not any(mk):                       # the export keys markers positionally
        mk = {}
    # the roster diff carries nigc_marker_id; markers carry it as 'id' when
    # present, otherwise index order is the marker id used by 92/94.
    by_id = {}
    for i, m in enumerate(markers, start=1):
        mid = sv(m.get("id")) or str(i)
        by_id[mid] = m

    # NIGC REUSES ONE POINT ACROSS A TRIBE'S PROPERTIES. Measured on this
    # export: 105 of 490 markers share a coordinate with at least one other
    # marker, across 30 shared coordinate values -- 19 White Earth locations at
    # one point, 18 Chickasaw locations at another, 6 Ho-Chunk, 6 Oneida. Those
    # points are tribal/administrative markers, NOT property locations, and the
    # marker's ADDRESS is property-specific while its coordinate is not. So the
    # coordinate is WITHHELD on those rows and the address is kept. Publishing a
    # tribe-level point in a column called `latitude` on a property row is the
    # same error as writing AUTHORIZED_MAXIMUM into ACTIVE_FLOOR_COUNT.
    coord_users = Counter((sv(x.get("lat")), sv(x.get("lng"))) for x in markers)

    diff = pd.read_csv(REVIEW / "nigc_roster_diff_2026-08-06.csv", dtype=str).fillna("")
    matched = diff[diff.outcome == "MATCHED"]
    n_nigc, n_withheld = 0, 0
    for r in matched.to_dict("records"):
        fid = r["facility_id"]
        if fid not in fmap:
            continue
        m = by_id.get(r["nigc_marker_id"])
        # the roster row already carries the marker's own address; the JSON is
        # preferred because it is the untranscoded original.
        raw_addr = sv(m.get("address")) if m else sv(r["nigc_address"])
        title = sv(m.get("title")) if m else sv(r["nigc_location_name"])
        lat, lon = (fnum(m.get("lat")), fnum(m.get("lng"))) if m else (None, None)
        n_share = coord_users.get((sv(m.get("lat")), sv(m.get("lng"))), 0) if m else 0
        withheld = ""
        if lat is not None and n_share > 1:
            others = [x["title"] for x in markers
                      if (sv(x.get("lat")), sv(x.get("lng")))
                      == (sv(m.get("lat")), sv(m.get("lng")))][:8]
            withheld = (
                f"NIGC publishes this exact coordinate ({lat:.6f}, {lon:.6f}) for "
                f"{n_share} different mapped locations, so it is a tribal or "
                f"administrative marker rather than this property's position. "
                f"Locations sharing it include: {'; '.join(others)}. The "
                f"coordinate is recorded here in text and withheld from the "
                f"latitude/longitude fields; the ADDRESS on this row is still "
                f"property-specific and is used to geocode a real point.")
            lat = lon = None
            n_withheld += 1
        street, city, state, zc = parse_nigc_address(raw_addr)
        obs.append(dict(
            coordinate_withheld_reason=withheld,
            nigc_markers_sharing_this_point=str(n_share) if n_share > 1 else "",
            property_id=fid, property_name=fmap[fid]["facility_name"],
            property_name_as_published=title,
            address=street, city=city, state=state or fmap[fid]["state"],
            postal_code=zc, address_type=address_type(street),
            latitude=("%.6f" % lat) if lat is not None else "",
            longitude=("%.6f" % lon) if lon is not None else "",
            geocode_method=("NIGC_PUBLISHED_POINT" if lat is not None else "NONE"),
            match_quality=("SOURCE_PUBLISHED_COORDINATE" if lat is not None
                           else "NIGC_POINT_IS_SHARED_TRIBAL_MARKER_WITHHELD"
                           if withheld else "ADDRESS_ONLY"),
            source_system="nigc_gaming_location_map",
            address_source_system="nigc_gaming_location_map",
            source_url="https://www.nigc.gov/map/",
            retrieved_at="2026-08-06",
            verbatim_quote=f"{title} | {raw_addr}",
            confidence_tier="A",
            publishable="Y",
            publishable_reason=(
                "Address and coordinate both published by the National Indian "
                "Gaming Commission, a federal regulator, on its free public "
                "gaming location map. No licensed vendor content."),
            match_to_property_basis=(
                f"existing deterministic NIGC roster match, basis="
                f"{r['match_basis']}"
                + (f", distance={r['match_distance_m']}m" if r["match_distance_m"] else "")
                + ("; NOTE: this match was established against Cedar's incumbent "
                   "coordinate, which is Casino City derived. The linkage used a "
                   "vendor coordinate as a matching key; the published address and "
                   "coordinate on this row are NIGC's."
                   if r["match_basis"].startswith("coords") else "")),
        ))
        n_nigc += 1
    n_shared_markers = sum(v for v in coord_users.values() if v > 1)
    log(f"NIGC gaming location map   : {len(markers)} markers, "
        f"{n_nigc} attached to existing Cedar property IDs "
        f"({len(diff[diff.outcome=='IN_NIGC_NOT_IN_CEDAR'])} unmatched markers left "
        f"staged in review/gaming_additions_2026-08-06.csv, not minted as new IDs)")
    log(f"  NIGC coordinate defect   : {n_shared_markers} of {len(markers)} markers "
        f"share a point with another marker across "
        f"{sum(1 for v in coord_users.values() if v > 1)} shared coordinate values; "
        f"{n_withheld} of our attached rows had their coordinate withheld as a "
        f"tribal marker rather than a property position")

    # ---- 2. votingpatterns canonical addresses ----------------------------
    vp = pd.read_csv(SRC_DIR / "canonical_casino_addresses_supplement.csv",
                     dtype=str).fillna("")
    n_vp, n_vp_addr = 0, 0
    for r in vp.to_dict("records"):
        state = st(r.get("state"))
        hits = name_idx.get(key(r.get("casino_name"), state), [])
        how = "exact match on normalised (facility_name, state)"
        if len(hits) != 1 and sv(r.get("address")):
            ah = addr_idx.get(key(r["address"], state), [])
            if len(ah) == 1:
                hits, how = ah, "exact match on normalised (street address, state)"
                n_vp_addr += 1
        if len(hits) != 1:
            continue
        fid = hits[0]
        lat, lon = fnum(r.get("latitude")), fnum(r.get("longitude"))
        site = sv(r.get("source"))
        obs.append(dict(
            property_id=fid, property_name=fmap[fid]["facility_name"],
            property_name_as_published=sv(r.get("casino_name")),
            address=sv(r.get("address")), city=sv(r.get("city")), state=state,
            postal_code=sv(r.get("zip")), address_type=address_type(r.get("address")),
            latitude=("%.6f" % lat) if lat is not None else "",
            longitude=("%.6f" % lon) if lon is not None else "",
            geocode_method=("OFFICIAL_PROPERTY_WEBSITE_POINT" if lat is not None
                            else "NONE"),
            match_quality=("SOURCE_COMPILED_COORDINATE" if lat is not None
                           else "ADDRESS_ONLY"),
            source_system="votingpatterns_canonical_addresses",
            address_source_system="votingpatterns_canonical_addresses",
            source_url="",
            retrieved_at="2026-04-27",
            verbatim_quote=(f"{sv(r.get('casino_name'))} | {sv(r.get('address'))}, "
                            f"{sv(r.get('city'))} {state} {sv(r.get('zip'))} | "
                            f"source as recorded: {site}"),
            confidence_tier="C",
            publishable="Y",
            publishable_reason=(
                f"Free-source origin: the compilation names the property's own "
                f"official website ('{site}') as the source. No licensed vendor "
                f"content. Tier C because the compilation preserved no URL, no "
                f"retrieval date and no verbatim page text; the coordinate is "
                f"recorded as hand-curated from that site rather than published "
                f"by it."),
            match_to_property_basis=how,
        ))
        n_vp += 1
    log(f"votingpatterns canonical   : {len(vp)} records, {n_vp} attached "
        f"({n_vp_addr} of them via street address rather than name)")

    # ---- 3. California CGCC licensed-facility list ------------------------
    ca = pd.read_csv(CLEAN / "ca_gaming_facilities_official.csv", dtype=str).fillna("")
    n_ca = 0
    seen_ca = set()
    for r in ca.to_dict("records"):
        fid = sv(r.get("facility_id"))
        if not fid or fid not in fmap:
            continue
        k = (fid, sv(r.get("casino_city")), sv(r.get("casino_county")))
        if k in seen_ca or not (k[1] or k[2]):
            continue
        seen_ca.add(k)
        obs.append(dict(
            property_id=fid, property_name=fmap[fid]["facility_name"],
            property_name_as_published=sv(r.get("facility_name_as_published")),
            address="", city=sv(r.get("casino_city")), state="CA",
            postal_code="", address_type="ABSENT",
            latitude="", longitude="",
            geocode_method="NONE",
            match_quality="CITY_AND_COUNTY_ONLY_NO_STREET_ADDRESS",
            source_system="ca_cgcc_licensed_facility_list",
            address_source_system="ca_cgcc_licensed_facility_list",
            source_url=sv(r.get("source_url")),
            retrieved_at=sv(r.get("fetched_date")) or sv(r.get("as_of_date")),
            verbatim_quote=sv(r.get("source_quote"))[:600],
            confidence_tier="A",
            publishable="Y",
            publishable_reason=(
                "City and county as published by the California Gambling Control "
                "Commission, a state regulator, in its free licensed-facility "
                "list. No street address is published, so this row carries no "
                "coordinate and must not be read as one."),
            match_to_property_basis=sv(r.get("facility_name_match_method")),
            county_name_published=sv(r.get("casino_county")),
        ))
        n_ca += 1
    log(f"CA CGCC licensed facilities: {n_ca} city/county observations attached")

    # ---- 4. Indian Gaming Dataset (provenance undocumented) ---------------
    igd = pd.read_excel(SRC_DIR / "Indian Gaming Dataset.xlsx", sheet_name="Sheet1")
    igd.columns = [str(c).strip() for c in igd.columns]
    n_igd = 0
    for r in igd.to_dict("records"):
        name, state = sv(r.get("company")), st(r.get("state"))
        if not name:
            continue
        hits = name_idx.get(key(name, state), [])
        if len(hits) != 1:
            continue
        fid = hits[0]
        if not sv(r.get("address")):
            continue
        obs.append(dict(
            property_id=fid, property_name=fmap[fid]["facility_name"],
            property_name_as_published=name,
            address=sv(r.get("address")), city=sv(r.get("city")), state=state,
            postal_code=sv(r.get("zipcode")), address_type=address_type(r.get("address")),
            latitude="", longitude="", geocode_method="NONE",
            match_quality="ADDRESS_ONLY",
            source_system="indian_gaming_dataset",
            address_source_system="indian_gaming_dataset",
            source_url="", retrieved_at="2026-03-12",
            verbatim_quote=(f"{name} | {sv(r.get('address'))}, {sv(r.get('city'))} "
                            f"{state} {sv(r.get('zipcode'))}"),
            confidence_tier="C",
            publishable="N",
            publishable_reason=(
                "NOT PUBLISHABLE: the source file states no origin for its "
                "address column -- no URL, no retrieval date, no quote. A source "
                "of unknown provenance is not a free official source, it is an "
                "unsourced one. Retained for internal corroboration only."),
            match_to_property_basis="exact match on normalised (company, state)",
        ))
        n_igd += 1
    log(f"Indian Gaming Dataset      : {n_igd} addresses attached "
        f"(publishable=N, provenance undocumented)")

    # ---- 5. Casino City Press / Tribal Property List (vendor) -------------
    n_v = 0
    for r in fac.to_dict("records"):
        vendor = ("casino_city_press" in r["source_datasets"]
                  or "tribal_property_list" in r["source_datasets"])
        if not vendor:
            continue
        cb = r["coords_basis"]
        coord_is_vendor = cb.startswith("Casino City")
        has_addr, has_coord = bool(sv(r["address"])), bool(sv(r["latitude"]))
        if not (has_addr or (has_coord and coord_is_vendor)):
            continue
        obs.append(dict(
            property_id=r["facility_id"], property_name=r["facility_name"],
            property_name_as_published=r["facility_name"],
            address=r["address"] if has_addr else "",
            city=r["city"], state=r["state"], postal_code=r["postal_code"],
            address_type=address_type(r["address"]),
            latitude=r["latitude"] if coord_is_vendor else "",
            longitude=r["longitude"] if coord_is_vendor else "",
            geocode_method=("VENDOR_PUBLISHED_POINT" if coord_is_vendor else "NONE"),
            match_quality=(cb.split("locationprecision=")[-1].strip().upper()
                           .replace(" ", "_") if coord_is_vendor else "ADDRESS_ONLY"),
            source_system="casino_city_press [LICENSED VENDOR - DO NOT PUBLISH]",
            address_source_system="casino_city_press",
            source_url="", retrieved_at=r["fetched_date"],
            verbatim_quote="",
            confidence_tier="X",
            publishable="N",
            publishable_reason=(
                "NOT PUBLISHABLE: Casino City Press is a licensed vendor panel. "
                "Standing rule (docs/GAMING_SPEC_RECONCILIATION.md): 'Casino City "
                "may be read for QA and may never be published or resold.' The "
                "Tribal Property List is the same vendor. Neither this address nor "
                "any coordinate derived from it may ship, and re-geocoding the "
                "address does not launder it -- the address itself is the vendor's "
                "fact."),
            match_to_property_basis="native Cedar row; the property ID is derived "
                                    "from this source",
        ))
        n_v += 1
    log(f"Casino City / TPL (vendor) : {n_v} observations recorded, all "
        f"publishable=N")

    return obs


# ==========================================================================
# GEOCODE
# ==========================================================================
def geocode(obs, deadline):
    """Two Census services, two kinds of new observation.

    (a) every FREE-SOURCED coordinate -> its census block  (coordinates service)
    (b) every FREE-SOURCED street address -> a Census coordinate + block, as a
        SEPARATE observation row with its own match quality (batch service)

    Vendor-sourced rows are deliberately NOT sent. A coordinate derived from a
    Casino City address is still Casino City's, so spending requests on it would
    buy nothing shippable and would put vendor strings on a federal host."""
    free = [o for o in obs if o["publishable"] == "Y"]

    # ---- (a) coordinate -> geography -------------------------------------
    todo = [o for o in free if o["latitude"] and o["longitude"]]
    log(f"\ncoordinate -> census block : {len(todo)} free-sourced coordinates")
    done = 0
    for o in todo:
        if time.time() > deadline:
            log("  wall-clock deadline reached; remaining coordinates left blank "
                "and recorded as NOT_ATTEMPTED_DEADLINE")
            break
        try:
            g = census_coord(o["latitude"], o["longitude"])
        except Refusal as e:
            log(f"  REFUSAL from {HOST}: {e}. Stopping the coordinate stage on "
                f"first refusal, per pull discipline.")
            break
        o["county_fips"] = g["county_fips"]
        o["county"] = g["county_name"] or o.get("county_name_published", "")
        o["census_tract"] = g["tract"]
        o["census_block"] = g["block"]
        if g["block"]:
            o["geocode_method"] += "+CENSUS_COORDINATE_TO_2020_BLOCK"
        done += 1
        if done % 100 == 0:
            log(f"  {done}/{len(todo)}")
    log(f"  {done} coordinates resolved to a 2020 census block")

    # ---- (b) address -> Census geocode, as its own observation ------------
    cands, seen = [], {}
    for o in free:
        if o["address_type"] not in ("STREET", "NON_STANDARD",
                                     "NON_STANDARD_ROUTE_OR_LANDMARK"):
            continue
        if not (o["address"] and o["state"]):
            continue
        k = (o["property_id"], norm(o["address"]), o["state"])
        if k in seen:
            continue
        seen[k] = o
        cands.append(o)
    log(f"\naddress -> census geocode  : {len(cands)} distinct free-sourced "
        f"(property, address) pairs")

    if time.time() > deadline:
        log("  deadline reached before the batch stage; not attempted")
        return obs, []

    records = [(str(i), c["address"], c["city"], c["state"], c["postal_code"])
               for i, c in enumerate(cands)]
    try:
        res = census_batch(records)
    except Refusal as e:
        log(f"  REFUSAL from {HOST}: {e}. Batch stage stopped on first refusal.")
        res = {}

    # RETRY PASS. A casino access road on tribal land is routinely absent from
    # TIGER's address ranges, and NIGC/VP city spellings are not always TIGER's
    # ("Tuscon"). The one safe second attempt is to drop the CITY and let the
    # ZIP carry the locality: the ZIP is in the source, the street is unchanged,
    # and nothing is invented. Addresses are NOT rewritten -- no hyphen
    # stripping, no abbreviation expansion, no unit removal -- because a
    # transformed address is a different claim.
    retry = [(str(i), c["address"], "", c["state"], c["postal_code"])
             for i, c in enumerate(cands)
             if res.get(str(i), {}).get("match") == "No_Match" and c["postal_code"]]
    if retry and time.time() < deadline:
        log(f"  retry (street + ZIP, city dropped): {len(retry)} No_Match inputs")
        try:
            res2 = census_batch(retry)
        except Refusal as e:
            log(f"  REFUSAL on retry: {e}")
            res2 = {}
        n_rec = 0
        for uid, r2 in res2.items():
            if r2["match"] == "Match":
                r2["retry"] = "city dropped, ZIP retained"
                res[uid] = r2
                n_rec += 1
        log(f"  retry recovered {n_rec} matches")

    new_rows = []
    qc = Counter()
    for i, c in enumerate(cands):
        r = res.get(str(i))
        if not r:
            qc["NOT_RETURNED"] += 1
            continue
        q = r["match"] if r["match"] != "Match" else r["quality"]
        qc[q] += 1
        lat, lon = fnum(r["lat"]), fnum(r["lon"])
        blk = ""
        if r["state"] and r["county"] and r["tract"] and r["block"]:
            blk = (r["state"].zfill(2) + r["county"].zfill(3)
                   + r["tract"].zfill(6) + r["block"])
        row = dict(c)
        row.update(
            property_name_as_published=c["property_name_as_published"],
            address=r["matched_address"].split(",")[0].strip() if r["matched_address"] else c["address"],
            city=(r["matched_address"].split(",")[1].strip()
                  if r["matched_address"].count(",") >= 3 else c["city"]),
            postal_code=(r["matched_address"].split(",")[3].strip()
                         if r["matched_address"].count(",") >= 3 else c["postal_code"]),
            latitude=("%.6f" % lat) if lat is not None else "",
            longitude=("%.6f" % lon) if lon is not None else "",
            county_fips=(r["state"].zfill(2) + r["county"].zfill(3)
                         if r["state"] and r["county"] else ""),
            county="",
            census_tract=(r["state"].zfill(2) + r["county"].zfill(3)
                          + r["tract"].zfill(6) if r["tract"] else ""),
            census_block=blk,
            geocode_method="CENSUS_BATCH_ADDRESS_GEOCODE",
            match_quality=q,
            coordinate_withheld_reason="",
            nigc_markers_sharing_this_point="",
            source_system="us_census_geocoder",
            source_url=(f"https://{HOST}/geocoder/geographies/addressbatch"
                        f" (benchmark={BENCHMARK}, vintage={VINTAGE})"),
            retrieved_at=TODAY,
            verbatim_quote=(f"input: {r['input']} | returned: "
                            f"{r['matched_address'] or r['match']}"
                            + (f" | second attempt: {r['retry']}"
                               if r.get("retry") else "")),
            confidence_tier=("A" if q == "Exact" else
                             "B" if q == "Non_Exact" else "C"),
        )
        # the laundering rule: a Census coordinate is only as free as its input.
        row["address_source_system"] = c["address_source_system"]
        row["publishable"] = "Y"
        row["publishable_reason"] = (
            f"Coordinate and census geography from the US Census Geocoder, a free "
            f"federal service with no key and no licence. The input address came "
            f"from '{c['address_source_system']}', which is a free official "
            f"source, so nothing on this row traces to a licensed vendor. Match "
            f"quality {q}: "
            + {"Exact": "the geocoder matched the address as given.",
               "Non_Exact": "the geocoder matched an approximate address and the "
                            "returned street differs from the input; treat the "
                            "point as block-level, not rooftop.",
               "Tie": "the geocoder found multiple equally good candidates and "
                      "returned none; NO coordinate is asserted.",
               "No_Match": "the geocoder found no candidate; NO coordinate is "
                           "asserted.",
               "NOT_RETURNED": "the batch returned no row for this input."
               }.get(q, "unclassified geocoder outcome."))
        row["match_to_property_basis"] = (
            f"inherited from the address observation it geocodes "
            f"({c['source_system']}): {c['match_to_property_basis']}")
        new_rows.append(row)
    log("  batch match quality: "
        + ", ".join(f"{k}={v}" for k, v in qc.most_common()))

    # county names for the batch rows, from the same host, reusing the cache
    need = [r for r in new_rows if r["latitude"] and not r["county"]]
    for r in need:
        if time.time() > deadline:
            break
        try:
            g = census_coord(r["latitude"], r["longitude"])
        except Refusal as e:
            log(f"  REFUSAL during county naming: {e}")
            break
        r["county"] = g["county_name"]
    return obs, new_rows


# ==========================================================================
# ASSEMBLE
# ==========================================================================
COLS = ["location_observation_id", "property_id", "property_name",
        "property_name_as_published", "address", "address_type", "city", "state",
        "postal_code", "county", "county_fips", "latitude", "longitude",
        "census_tract", "census_block", "geocode_method", "match_quality",
        "source_system", "address_source_system", "source_url", "retrieved_at",
        "verbatim_quote", "confidence_tier", "publishable", "publishable_reason",
        "match_to_property_basis", "coordinate_withheld_reason",
        "nigc_markers_sharing_this_point", "coordinate_scope_note",
        "distance_to_incumbent_coordinate_m", "built_date", "built_by_script"]


def assemble(obs, fac):
    fmap = {r["facility_id"]: r for r in fac.to_dict("records")}
    rows = []
    seq = Counter()
    for o in obs:
        pid = o["property_id"]
        seq[pid] += 1
        r = {c: "" for c in COLS}
        r.update({k: v for k, v in o.items() if k in COLS})
        r["location_observation_id"] = f"GLOC-{pid}-{seq[pid]:02d}"
        r["coordinate_scope_note"] = SCOPE_NOTE
        r["built_date"] = TODAY
        r["built_by_script"] = SCRIPT
        # zero-pad the text geographies. Leading zeros are real; this is a
        # documented past bug in this project.
        if r["county_fips"]:
            r["county_fips"] = str(r["county_fips"]).zfill(5)
        if r["census_tract"]:
            r["census_tract"] = str(r["census_tract"]).zfill(11)
        if r["census_block"]:
            r["census_block"] = str(r["census_block"]).zfill(15)
        # QA only: how far is this free coordinate from the incumbent one?
        inc = fmap.get(pid, {})
        la, lo = fnum(r["latitude"]), fnum(r["longitude"])
        ila, ilo = fnum(inc.get("latitude")), fnum(inc.get("longitude"))
        if None not in (la, lo, ila, ilo) and r["publishable"] == "Y":
            r["distance_to_incumbent_coordinate_m"] = "%d" % round(
                haversine_m(la, lo, ila, ilo))
        rows.append(r)
    return rows


def write_csv(path, rows, cols):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, quoting=csv.QUOTE_MINIMAL,
                           extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-network", action="store_true")
    a = ap.parse_args()

    deadline = time.time() + DEADLINE_MIN * 60
    log(f"=== 143 gaming property locations  {datetime.now().isoformat(timespec='seconds')}")

    fac = load_facilities()
    log(f"gaming_facilities.csv      : {len(fac)} properties\n")

    obs = harvest(fac)
    log(f"\nharvested                  : {len(obs)} observations")

    new = []
    if not a.no_network:
        claim_host("gaming property address+coordinate layer",
                   ["census addressbatch (free-sourced gaming addresses)",
                    "census coordinates->2020 block (free-sourced coordinates)"])
        try:
            obs, new = geocode(obs, deadline)
        finally:
            release_host()
    else:
        log("\n--no-network: geocoding stages skipped")

    allobs = obs + new
    rows = assemble(allobs, fac)
    out = CLEAN / "gaming_property_locations.csv"
    # A --no-network run holds no geocodes, so writing it over a geocoded file is
    # a silent regression that looks like a successful build. Caught the hard way
    # on 2026-08-12: an offline re-run to regenerate a review file dropped 639
    # census rows from a finished output.
    if a.no_network and out.exists():
        prior = pd.read_csv(out, dtype=str).fillna("")
        if (prior["census_block"] != "").any():
            out = CLEAN / "gaming_property_locations_NO_NETWORK_PREVIEW.csv"
            log(f"\nREFUSED to overwrite a geocoded {CLEAN/'gaming_property_locations.csv'} "
                f"with a --no-network build. Writing the preview to {out.name} instead.")
    write_csv(out, rows, COLS)
    log(f"\nwrote {out}  ({len(rows)} rows)")

    # ---- review artefacts ------------------------------------------------
    pub = [r for r in rows if r["publishable"] == "Y"]
    pub_pids = {r["property_id"] for r in pub}
    pub_coord = {r["property_id"] for r in pub if r["latitude"]}
    pub_block = {r["property_id"] for r in pub if r["census_block"]}
    all_pids = set(fac["facility_id"])
    vendor_only = sorted(all_pids - pub_pids)

    # For each vendor-only property, is there an UNMATCHED NIGC marker sitting in
    # its own city and state? That is a candidate free source and a probable
    # roster match failure -- surfaced for a ruling, never auto-attached. Script
    # 92 already established that a large share of the 140 "missing" NIGC markers
    # are match failures against rows Cedar holds, not missing properties.
    diff_all = pd.read_csv(REVIEW / "nigc_roster_diff_2026-08-06.csv",
                           dtype=str).fillna("")
    unmatched = diff_all[diff_all.outcome == "IN_NIGC_NOT_IN_CEDAR"]
    nigc_by_place = defaultdict(list)
    for r in unmatched.to_dict("records"):
        street, city, state, zc = parse_nigc_address(r["nigc_address"])
        if city and state:
            nigc_by_place[(norm(city), state)].append(
                f"{r['nigc_location_name']} [{r['nigc_address']}]")

    vrows = []
    fmap = {r["facility_id"]: r for r in fac.to_dict("records")}
    for pid in vendor_only:
        f = fmap[pid]
        cand = nigc_by_place.get((norm(f["city"]), f["state"]), [])
        vrows.append(dict(
            candidate_unmatched_nigc_markers_same_city_state=" || ".join(cand[:4]),
            n_candidate_nigc_markers=str(len(cand)),
            property_id=pid, property_name=f["facility_name"], tribe=f["tribe"],
            state=f["state"], city=f["city"],
            incumbent_has_address="Y" if sv(f["address"]) else "N",
            incumbent_has_coordinate="Y" if sv(f["latitude"]) else "N",
            incumbent_source_datasets=f["source_datasets"],
            incumbent_coords_basis=f["coords_basis"],
            reason=("No free official source publishes an address or a "
                    "coordinate for this property. Everything Cedar holds for it "
                    "traces to Casino City Press / the Casino City Tribal "
                    "Property List and therefore cannot ship."),
            next_route=("NIGC map (not matched), the property's own official "
                        "website (held by the capacity agent), or the state "
                        "regulator's licensed-facility list."),
            ruling_warning=(
                "A candidate marker in the same city is NOT a match. Flandreau SD "
                "is the worked counter-example: the only unmatched NIGC marker "
                "there is 'Royal River Casino and Hotel' and the only vendor-only "
                "Cedar row there is 'First American Mart' -- a convenience store. "
                "A one-to-one city test would have attached the casino's address "
                "to the c-store. Rule each pair individually."),
            YOUR_RULING="",
            built_date=TODAY))
    write_csv(REVIEW / f"gaming_locations_vendor_only_{TODAY}.csv", vrows,
              list(vrows[0].keys()) if vrows else ["property_id"])

    # geocode conflicts: two free sources disagreeing by more than 1 km is a
    # finding about the sources, not something to average away.
    bypid = defaultdict(list)
    for r in pub:
        if r["latitude"]:
            bypid[r["property_id"]].append(r)
    conf = []
    for pid, rs in bypid.items():
        for i in range(len(rs)):
            for j in range(i + 1, len(rs)):
                d = haversine_m(float(rs[i]["latitude"]), float(rs[i]["longitude"]),
                                float(rs[j]["latitude"]), float(rs[j]["longitude"]))
                if d > 1000:
                    a, b_ = rs[i], rs[j]
                    same_src = (a["address_source_system"]
                                == b_["address_source_system"])
                    conf.append(dict(
                        property_id=pid, property_name=a["property_name"],
                        conflict_class=("SOURCE_DISAGREES_WITH_ITSELF"
                                        if same_src else "TWO_SOURCES_DISAGREE"),
                        source_a=a["source_system"], method_a=a["geocode_method"],
                        quality_a=a["match_quality"],
                        lat_a=a["latitude"], lon_a=a["longitude"],
                        address_a=a["address"],
                        source_b=b_["source_system"], method_b=b_["geocode_method"],
                        quality_b=b_["match_quality"],
                        lat_b=b_["latitude"], lon_b=b_["longitude"],
                        address_b=b_["address"],
                        distance_m="%d" % round(d),
                        note=(("The SAME source's published point and the Census "
                               "geocode of that source's OWN address disagree by "
                               "more than 1 km. A source disagreeing with itself is "
                               "a finding, not a bug to smooth over: the address is "
                               "property-specific and the published point is not "
                               "necessarily so. Both are retained.")
                              if same_src else
                              ("Two free official sources place this property more "
                               "than 1 km apart. Both are retained; neither is "
                               "averaged or preferred without a ruling.")),
                        YOUR_RULING="", built_date=TODAY))
    write_csv(REVIEW / f"gaming_locations_geocode_conflicts_{TODAY}.csv", conf,
              list(conf[0].keys()) if conf else ["property_id"])

    # ---- report ----------------------------------------------------------
    log("\n" + "=" * 66)
    log("COVERAGE")
    log(f"  properties in universe                        {len(all_pids)}")
    log(f"  with a PUBLISHABLE address observation        "
        f"{len({r['property_id'] for r in pub if r['address']})}")
    log(f"  with a PUBLISHABLE coordinate                 {len(pub_coord)}")
    log(f"  with a PUBLISHABLE 2020 census block          {len(pub_block)}")
    log(f"  vendor-only, nothing publishable              {len(vendor_only)}")
    log(f"  BEFORE this build, publishable coordinates    0  (every coordinate in "
        f"gaming_facilities.csv is Casino City's or a votingpatterns hand-curation "
        f"with no provenance record attached to it)")
    log("\nMATCH QUALITY (publishable rows carrying a coordinate)")
    for k, v in Counter(r["match_quality"] for r in pub if r["latitude"]).most_common():
        log(f"  {k:<42} {v}")
    log("\nBY SOURCE SYSTEM (all rows)")
    for k, v in Counter(r["source_system"] for r in rows).most_common():
        log(f"  {k:<52} {v}")
    log(f"\nreview/gaming_locations_vendor_only_{TODAY}.csv        {len(vrows)}")
    log(f"review/gaming_locations_geocode_conflicts_{TODAY}.csv  {len(conf)}")

    (LOGS / f"143_gaming_property_locations_{TODAY}.log").write_text(
        _log_buf.getvalue(), encoding="utf-8")


if __name__ == "__main__":
    main()
