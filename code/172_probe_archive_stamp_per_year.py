#!/usr/bin/env python3
"""
Cedar Press - 172: probe the award-archive stamp PER YEAR. Read only.

WHY PER-YEAR AND NOT A HEAD ON A GUESSED URL
--------------------------------------------
The archive REPLACES its objects monthly. A `HEAD` on a URL built from a
hardcoded stamp answers only "is my guess still alive"; a 404 then looks like a
fact about the fiscal year when it is a fact about the vintage. That confusion
already cost this project a day (docs/ASSISTANCE_ARCHIVE_PULL_LOG.md FINDING 7).

A prefixed listing answers the better question - *what stamp does this year
carry right now* - for the same one request:

    GET /award_data_archive/?prefix=FY2020_All_Assistance_Full_

START_HERE.md: "Probe the stamp at run start, per-year, never global." One
request per year, paced, against a host that edge-blocks on request frequency
rather than on bytes.

Only 404 and 403 are facts about an object. Anything else is a fact about the
moment and is reported as such.

    py -3 code/172_probe_archive_stamp_per_year.py 2020 2021 2022
"""

import re
import sys
import time

import requests

HOST = "files.usaspending.gov"
BASE = f"https://{HOST}/award_data_archive/"
UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/126.0.0.0 Safari/537.36")}
KEY_RE = re.compile(r"<Key>(.*?)</Key>.*?<Size>(\d+)</Size>", re.S)


def probe(year):
    prefix = f"FY{year}_All_Assistance_Full_"
    url = f"{BASE}?prefix={prefix}"
    t0 = time.time()
    try:
        r = requests.get(url, headers=UA, timeout=(15, 60))
    except requests.exceptions.RequestException as e:
        dt = time.time() - t0
        print(f"FY{year}: TRANSPORT FAILURE in {dt:.2f}s {type(e).__name__}"
              + ("   <-- sub-second = EDGE BLOCK, a fact about the host, "
                 "NOT about FY{year}".format(year=year) if dt < 1 else ""))
        return None
    dt = time.time() - t0
    if r.status_code != 200:
        print(f"FY{year}: listing HTTP {r.status_code} in {dt:.2f}s - "
              "a fact about the host, not about this year")
        return None
    found = KEY_RE.findall(r.text)
    if not found:
        print(f"FY{year}: HTTP 200 in {dt:.2f}s and ZERO keys under prefix "
              f"{prefix!r}. THIS is the shape that means the object is absent.")
        return None
    for k, sz in found:
        m = re.search(r"_(\d{8})\.zip$", k)
        print(f"FY{year}: HTTP 200 in {dt:.2f}s  stamp={m.group(1) if m else '?'}"
              f"  {int(sz)/1e9:.2f} GB  {k}")
    return [(k, int(sz)) for k, sz in found]


def main():
    years = [int(a) for a in sys.argv[1:] if a.isdigit()] or [2020, 2021, 2022]
    out = {}
    for i, y in enumerate(years):
        if i:
            time.sleep(15)
        out[y] = probe(y)
    stamps = {re.search(r"_(\d{8})\.zip$", k).group(1)
              for v in out.values() if v for k, _ in v}
    print(f"\ndistinct stamps across the probed years: {sorted(stamps)}")
    if len(stamps) > 1:
        print("!! years carry DIFFERENT stamps - the stamp must stay per-year, "
              "never global.")


if __name__ == "__main__":
    main()
