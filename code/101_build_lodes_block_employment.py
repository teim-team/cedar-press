#!/usr/bin/env python3
"""
Cedar Press - 101: LODES workplace jobs at the BLOCK level.

STATUS 2026-08-26 (407_unfinished_work_audit): NEVER RUN, and SUPERSEDED for
the employment leg by `code/100_finish_declinations_and_employment.py`, which
already shipped LODES rows into the collection and keeps the raw CNS codes with
a correct `measurement_note`. The CNS17/CNS18 label reversal that made this file
a trap -- it would have shipped the casino column under the hotel name -- was
CORRECTED today at the SECTORS dict below; nothing was contaminated, because
this script has no log and neither of its outputs has ever existed.

  * The employment leg (`gaming_employment_lodes.csv`) is SUPERSEDED. Do not
    re-derive it here; read what 100 produced.
  * The GEOCODE leg (`facility_block_geocode.csv`) is NOT superseded -- 100
    does not produce it, and `102_build_coverage_profile.py` still lists it as
    a hub source. That leg is the only reason this file is still here.

Before running any stage, claim the host lock for `geocoding.geo.census.gov`
and `lehd.ces.census.gov` per docs/PULL_DISCIPLINE.md, and re-read the caveat
block below -- it is the reason these rows are observations, not payroll.

ELIJAH, 2026-08-07
------------------
"we have lodes already so i assume we can get that quickly at the block level?"
"we probably want stuff in python to make it easier to sustain over time"

Both right, with one correction on the first.

WHAT WE ALREADY HOLD IS THE WRONG GRAIN
---------------------------------------
    4wheeler/lumecon_deliverables_v2/data/raw/lodes_reservation_employment.csv
    7,158 rows, 2005-2022, 32 columns          <- the FRESHER copy (2026-04-11)
    4wheeler/project/raw/api/...                  same content, 2026-03-24

That file is **reservation-aggregated**, and it was built by a Stata do-file
(`4wheeler/project/build/08_lodes_employment.do`). A reservation total sums the
tribal government, the school, the clinic, the casino and every other employer
inside the boundary - so it cannot stand in for one property's employment.

Block is LODES's NATIVE grain; the reservation file was aggregated UP from it.
So this is a re-pull, not new research. And it is Python, because the rest of
this project is Python and a second language is a maintenance tax.

THE CAVEAT THAT TRAVELS WITH EVERY ROW
--------------------------------------
LODES block jobs are **workplace jobs located in that block**, not casino
payroll. A block holding a casino, a hotel, a truck stop and a tribal office
reports all of it. So:

  - measurement_type is LODES_BLOCK_WORKPLACE_JOBS, never "employees"
  - `n_other_employers_in_block` is recorded, because a block with one employer
    is a far stronger observation than one with nine
  - it never overwrites an OSHA or environmental-review figure

Multiple independent employment observations are a FEATURE. Cedar may derive a
preferred value later; it retains every underlying one.

STAGES
------
    --geocode   properties -> 15-digit census block GEOID (Census Geocoder)
    --pull      LEHD WAC by state-year (block grain, native)
    --join      block WAC -> facility observations
    --all

Writes data/clean/gaming_employment_lodes.csv
       data/raw/lodes/wac/<st>/<st>_wac_S000_JT00_<year>.csv.gz
       data/clean/facility_block_geocode.csv
"""

import argparse
import csv
import gzip
import io
import json
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
RAW = CEDAR / "data" / "raw" / "lodes"
LOGS = CEDAR / "logs"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

LEHD = "https://lehd.ces.census.gov/data/lodes/LODES8/{st}/wac/{st}_wac_S000_JT00_{yr}.csv.gz"
GEOCODER = ("https://geocoding.geo.census.gov/geocoder/geographies/coordinates"
            "?x={lon}&y={lat}&benchmark=Public_AR_Current"
            "&vintage=Census2020_Current&format=json&layers=10")

# The CNS sectors where casino employment lands. Kept explicit rather than
# summed, because a property with a large hotel looks different from one that
# is a gaming floor and a car park.
# CORRECTED 2026-08-26 by 407_unfinished_work_audit. CNS17 and CNS18 were
# REVERSED here, and the reversal pointed the wrong way for exactly the column
# this script exists to produce: a casino is NAICS 713210, sector 71, which is
# CNS17 -- so casino jobs would have shipped under `jobs_accommodation_food`,
# the hotel name. The LODES WAC segments are the twenty NAICS supersectors in
# order (CNS01=11 ... CNS20=92); the other three entries below already agree
# with that ordering (CNS07=44-45 retail, CNS12=54 professional, CNS20=92
# public administration), which is what pins CNS17=71 and CNS18=72.
# Verified in the data by `code/100_finish_declinations_and_employment.py`,
# which keeps the raw codes and names them the right way round: Wetumpka block
# 010510308011030 reads C000=723, CNS17=688 -- 688 arts-and-entertainment jobs,
# i.e. the casino. See docs/LABOR_SOURCES_FOR_GAMING_2026-08-26.md lines 405-425.
SECTORS = {
    "C000": "total_jobs",
    "CNS17": "jobs_arts_entertainment_rec",  # NAICS 71 - WHERE THE CASINO IS
    "CNS18": "jobs_accommodation_food",      # NAICS 72
    "CNS07": "jobs_retail",
    "CNS12": "jobs_professional",
    "CNS20": "jobs_public_admin",            # tribal government on the block
}

UA = {"User-Agent": "CedarPress/1.0 (research; contact hello@cedarpress.co)"}


def log(msg):
    LOGS.mkdir(exist_ok=True)
    line = f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}] {msg}"
    print(line)
    with open(LOGS / f"101_lodes_{TODAY}.log", "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def read_csv(p):
    if not Path(p).exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def get(url, tries=4):
    """One poller per host, exponential backoff. An edge block (instant
    disconnect) is a stop signal - more requests extend it."""
    delay = 5
    for i in range(tries):
        t0 = time.time()
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except Exception as e:
            dt = time.time() - t0
            if dt < 1.0 and i >= 1:
                raise RuntimeError(f"edge block after {i+1} instant failures: {e}")
            if i == tries - 1:
                raise
            log(f"    retry {i+1} in {delay}s ({type(e).__name__})")
            time.sleep(delay)
            delay *= 2


# ---------------------------------------------------------------- geocode ---

def geocode():
    """Property lat/lon -> 15-digit census block. Only the ones we lack."""
    fac = read_csv(CLEAN / "gaming_facilities.csv")
    done = {r["facility_id"]: r for r in read_csv(CLEAN / "facility_block_geocode.csv")}
    todo = [f for f in fac
            if f.get("latitude") and f.get("longitude")
            and f["facility_id"] not in done]
    log(f"geocode: {len(fac)} properties, {len(done)} already done, "
        f"{len(todo)} to do")
    if not todo:
        return
    n_ok = 0
    for i, f in enumerate(todo, 1):
        try:
            lat = float(f["latitude"])
            lon = float(f["longitude"])
        except (TypeError, ValueError):
            continue
        try:
            raw = get(GEOCODER.format(lat=lat, lon=lon))
            j = json.loads(raw)
            blocks = (j.get("result", {}).get("geographies", {})
                      .get("Census Blocks", []))
        except Exception as e:
            log(f"    {f['facility_id']}: {type(e).__name__} {e}")
            if "edge block" in str(e):
                log("    STOPPING - host is edge-blocking. Resume later.")
                break
            continue
        if not blocks:
            continue
        b = blocks[0]
        done[f["facility_id"]] = {
            "facility_id": f["facility_id"],
            "facility_name": f.get("facility_name", ""),
            "tribe_id": f.get("tribe_id", ""),
            "latitude": lat, "longitude": lon,
            "coords_basis": f.get("coords_basis", ""),
            "block_geoid": b.get("GEOID", ""),
            "state_fips": b.get("STATE", ""),
            "county_fips": b.get("COUNTY", ""),
            "tract": b.get("TRACT", ""),
            "block": b.get("BLOCK", ""),
            "geocoded_date": TODAY,
        }
        n_ok += 1
        if i % 25 == 0:
            log(f"    {i}/{len(todo)} ({n_ok} resolved)")
            _write_geocode(done)
        time.sleep(0.4)          # be a good citizen on a free federal service
    _write_geocode(done)
    log(f"geocode: {len(done)} properties now carry a block GEOID")


def _write_geocode(done):
    rows = list(done.values())
    if not rows:
        return
    p = CLEAN / "facility_block_geocode.csv"
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


# ------------------------------------------------------------------- pull ---

def pull(years):
    """WAC by state-year at block grain. Only states we actually need."""
    geo = read_csv(CLEAN / "facility_block_geocode.csv")
    if not geo:
        log("pull: no geocodes yet - run --geocode first")
        return
    fips2usps = _fips_map()
    states = sorted({fips2usps.get(r["state_fips"], "").lower()
                     for r in geo if r.get("state_fips")} - {""})
    log(f"pull: {len(states)} states needed: {' '.join(states)}")
    RAW.mkdir(parents=True, exist_ok=True)
    got = miss = 0
    for st in states:
        (RAW / "wac" / st).mkdir(parents=True, exist_ok=True)
        for yr in years:
            dest = RAW / "wac" / st / f"{st}_wac_S000_JT00_{yr}.csv.gz"
            if dest.exists() and dest.stat().st_size > 1000:
                got += 1
                continue
            try:
                data = get(LEHD.format(st=st, yr=yr))
                dest.write_bytes(data)
                got += 1
                log(f"    {st} {yr}  {len(data)/1024:.0f} KB")
            except Exception as e:
                miss += 1
                log(f"    {st} {yr}  MISSING ({type(e).__name__})")
                if "edge block" in str(e):
                    log("    STOPPING - host is edge-blocking.")
                    return
            time.sleep(0.3)
    log(f"pull: {got} files present, {miss} unavailable")


def _fips_map():
    return {
        "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO",
        "09": "CT", "10": "DE", "11": "DC", "12": "FL", "13": "GA", "15": "HI",
        "16": "ID", "17": "IL", "18": "IN", "19": "IA", "20": "KS", "21": "KY",
        "22": "LA", "23": "ME", "24": "MD", "25": "MA", "26": "MI", "27": "MN",
        "28": "MS", "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
        "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH",
        "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD",
        "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA",
        "54": "WV", "55": "WI", "56": "WY",
    }


# ------------------------------------------------------------------- join ---

def join():
    geo = read_csv(CLEAN / "facility_block_geocode.csv")
    if not geo:
        log("join: no geocodes - run --geocode first")
        return
    fips2usps = _fips_map()
    want = defaultdict(list)          # (state, block_geoid) -> facilities
    for r in geo:
        st = fips2usps.get(r.get("state_fips", ""), "").lower()
        if st and r.get("block_geoid"):
            want[(st, r["block_geoid"])].append(r)
    log(f"join: {len(want):,} distinct blocks across {len(geo):,} properties")

    out = []
    for st in sorted({k[0] for k in want}):
        d = RAW / "wac" / st
        if not d.exists():
            continue
        for f in sorted(d.glob(f"{st}_wac_S000_JT00_*.csv.gz")):
            yr = f.stem.split("_")[-1].replace(".csv", "")
            blocks = {k[1] for k in want if k[0] == st}
            try:
                with gzip.open(f, "rt", encoding="utf-8", errors="replace") as fh:
                    for row in csv.DictReader(fh):
                        g = (row.get("w_geocode") or "").strip()
                        if g not in blocks:
                            continue
                        for fac in want[(st, g)]:
                            rec = {
                                "observation_id": f"LODES-{fac['facility_id']}-{yr}",
                                "facility_id": fac["facility_id"],
                                "facility_name": fac.get("facility_name", ""),
                                "tribe_id": fac.get("tribe_id", ""),
                                "year": int(yr),
                                "block_geoid": g,
                                "measurement_type": "LODES_BLOCK_WORKPLACE_JOBS",
                                "geographic_level": "census_block",
                                "n_properties_sharing_this_block":
                                    len(want[(st, g)]),
                                "source_url": LEHD.format(st=st, yr=yr),
                                "source_note": (
                                    "Workplace jobs located in this census "
                                    "block. NOT casino payroll - every "
                                    "employer in the block is included."),
                                "fetched_date": TODAY,
                                "built_date": TODAY,
                            }
                            for code, label in SECTORS.items():
                                try:
                                    rec[label] = int(row.get(code) or 0)
                                except ValueError:
                                    rec[label] = ""
                            out.append(rec)
            except Exception as e:
                log(f"    {f.name}: {type(e).__name__} {e}")

    if not out:
        log("join: nothing produced - pull the WAC files first")
        return
    p = CLEAN / "gaming_employment_lodes.csv"
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    yrs = sorted({r["year"] for r in out})
    props = {r["facility_id"] for r in out}
    shared = sum(1 for r in out if r["n_properties_sharing_this_block"] > 1)
    log(f"join: wrote {p.relative_to(CEDAR)}")
    log(f"  {len(out):,} observations · {len(props):,} properties · "
        f"{yrs[0]}-{yrs[-1]}")
    log(f"  {shared:,} rows sit on a block shared with another property - "
        f"weaker evidence, flagged not dropped")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--geocode", action="store_true")
    ap.add_argument("--pull", action="store_true")
    ap.add_argument("--join", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--years", default="2010-2022")
    a = ap.parse_args()
    lo, hi = (int(x) for x in a.years.split("-"))
    years = list(range(lo, hi + 1))

    log("=== Cedar Press 101: LODES block-level employment ===")
    if a.all or a.geocode:
        geocode()
    if a.all or a.pull:
        pull(years)
    if a.all or a.join:
        join()
    if not any((a.all, a.geocode, a.pull, a.join)):
        ap.print_help()


if __name__ == "__main__":
    main()
