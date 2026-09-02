"""
203_verify_fac_historical_bulk_tribal.py
========================================
Cedar Press. Written 2026-08-26.

WHY THIS MATTERS MORE THAN ANYTHING ELSE IN THIS SWEEP.

`code/200_probe_fac_historical_depth.py` measured `api.fac.gov` and found the
dissemination table starts at **audit_year 2016** -- zero rows for every year
1997-2013, 22 requests, clean. On that evidence alone the correct write-up was
"FAC: NOT_FOUND pre-2016".

**That would have been wrong.** A research sweep found that FAC publishes the
1998-2015 Census-era archive as **bulk ZIPs on a different path entirely**:

    https://www.fac.gov/data/download/historic/
    -> https://app.fac.gov/dissemination/public-data/census/csv/census-YYYY.zip

The API and the bulk archive are different surfaces over different eras. Probing
one and concluding about the source is the exact error this project has already
paid for twice (the tribal Single Audit "dead end"; `resource_assets.csv`) --
and it very nearly happened a third time, in the SAME dataset, today.

WHAT THIS SCRIPT ESTABLISHES, BY MEASUREMENT:
  1. Do the historic ZIPs exist, and where does the series actually start?
  2. Does the payload carry a real recipient identifier (EIN) pre-2007?
  3. How many TRIBAL auditees are in it, and what do they report expending?

That last question is the one that decides whether CEILING 1 has a hole in it.

DISCIPLINE: hosts `www.fac.gov` / `app.fac.gov` (+ the signed S3 redirect).
Locks claimed. <= 12 requests. Downloads at most 2 ZIPs (~40 MB) into
data/raw/, `.part` then rename. Checks free disk first.

Run:  py -3 code/203_verify_fac_historical_bulk_tribal.py
"""

import csv
import io
import json
import os
import shutil
import sys
import time
import zipfile
import collections
from datetime import datetime, timezone

import requests

csv.field_size_limit(10 ** 9)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "FAC_HISTORICAL_BULK_VERIFICATION.json")
RAW = os.path.join(ROOT, "data", "raw", "fac_historical_census")
LOGS = os.path.join(ROOT, "logs")

INDEX = "https://www.fac.gov/data/download/historic/"
ZIP_URL = "https://app.fac.gov/dissemination/public-data/census/csv/census-%s.zip"

UA = ("CedarPress-research/1.0 (+https://cedarpress.co; "
      "elijahsamsonmoreno@gmail.com)")
HDR = {"User-Agent": UA}

GAP = 2.0
DEADLINE_S = 20 * 60
MAX_REQUESTS = 12
DISK_FLOOR_GB = 6.0
START = time.time()
_n = {"i": 0}

# Fetch two years: the claimed first year, and one inside the pre-2007 window.
FETCH_YEARS = ["1998", "2005"]
PROBE_ONLY = ["1997", "2015"]      # boundary probes, HEAD only


def locks(hosts, active, extra=None):
    for h in hosts:
        p = os.path.join(LOGS, f"_HOSTLOCK_{h}.json")
        if active and os.path.exists(p):
            try:
                cur = json.load(open(p, encoding="utf-8"))
                if cur.get("active"):
                    print(f"{h} held by another poller. Exiting, zero requests.",
                          file=sys.stderr)
                    sys.exit(3)
            except Exception:
                pass
        payload = {
            "host": h, "pid": os.getpid(),
            "script": "code/203_verify_fac_historical_bulk_tribal.py",
            "claimed_at": datetime.now(timezone.utc).isoformat(),
            "active": active, "queue": [],
            "policy": f"<= {MAX_REQUESTS} requests, >={GAP}s gap, "
                      f"{DEADLINE_S//60} min deadline, <=2 objects downloaded",
            "note": "FAC Census-era historic bulk archive: existence + tribal census",
        }
        if extra:
            payload.update(extra)
        tmp = p + ".part"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1)
        os.replace(tmp, p)


def free_gb(path):
    return shutil.disk_usage(path).free / (1024 ** 3)


def req(method, url, stream=False):
    if _n["i"] >= MAX_REQUESTS:
        return None, {"outcome": "BUDGET_EXHAUSTED", "url": url}
    if time.time() - START > DEADLINE_S:
        return None, {"outcome": "DEADLINE", "url": url}
    _n["i"] += 1
    t0 = time.time()
    try:
        r = requests.request(method, url, headers=HDR, timeout=(15, 180),
                             allow_redirects=True, stream=stream)
    except Exception as e:
        dt = time.time() - t0
        return None, {"outcome": "TRANSPORT", "error": repr(e)[:200],
                      "seconds": round(dt, 3), "url": url}
    meta = {"outcome": "HTTP", "status": r.status_code,
            "seconds": round(time.time() - t0, 3),
            "content_type": r.headers.get("Content-Type", ""),
            "content_length": r.headers.get("Content-Length"),
            "final_host": r.url.split("/")[2] if "//" in r.url else None,
            "url": url}
    if not stream:
        time.sleep(GAP)
    return r, meta


def profile_zip(path, year):
    """Open the archive and measure the identifier + tribal surface."""
    prof = {"zip": os.path.basename(path),
            "bytes": os.path.getsize(path), "members": []}
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        prof["members"] = [{"name": nm, "size": z.getinfo(nm).file_size}
                           for nm in names]
        hdr_name = next((nm for nm in names
                         if "AUDITHEADER" in nm.upper()), None)
        awd_name = next((nm for nm in names
                         if nm.upper().endswith("ELECAUDITS.CSV")), None)
        if not hdr_name:
            prof["error"] = "no ELECAUDITHEADER member found"
            return prof

        with z.open(hdr_name) as fh:
            txt = io.TextIOWrapper(fh, encoding="utf-8", errors="replace",
                                   newline="")
            rd = csv.DictReader(txt)
            cols = rd.fieldnames or []
            prof["header_columns"] = cols

            def col(*cands):
                for c in cands:
                    for f in cols:
                        if f and f.strip().upper() == c:
                            return f
                return None

            c_ein = col("EIN")
            c_duns = col("DUNS")
            c_name = col("AUDITEENAME")
            c_type = col("TYPEOFENTITY")
            c_exp = col("TOTFEDEXPEND")
            c_yr = col("AUDITYEAR")
            c_id = col("DBKEY", "AUDITEEID", "ID")

            n = 0
            ein_n = duns_n = 0
            types = collections.Counter()
            tribal_rows = []
            tribal_eins = set()
            tribal_exp = 0.0
            years = collections.Counter()
            for r in rd:
                n += 1
                if c_ein and (r.get(c_ein) or "").strip():
                    ein_n += 1
                if c_duns and (r.get(c_duns) or "").strip():
                    duns_n += 1
                t = (r.get(c_type) or "").strip().upper() if c_type else ""
                types[t] += 1
                if c_yr:
                    years[(r.get(c_yr) or "").strip()] += 1
                if t.startswith("I"):        # 'I' / 'INDIAN TRIBE' variants
                    e = (r.get(c_ein) or "").strip() if c_ein else ""
                    if e:
                        tribal_eins.add(e)
                    try:
                        tribal_exp += float((r.get(c_exp) or 0) or 0)
                    except ValueError:
                        pass
                    if len(tribal_rows) < 15:
                        tribal_rows.append({
                            "auditee_name": (r.get(c_name) or "").strip(),
                            "ein": e,
                            "type_of_entity": t,
                            "total_fed_expend": (r.get(c_exp) or "").strip(),
                            "audit_year": (r.get(c_yr) or "").strip(),
                        })

            prof["header_rows"] = n
            prof["ein_populated_pct"] = round(100.0 * ein_n / n, 3) if n else None
            prof["duns_populated_pct"] = round(100.0 * duns_n / n, 3) if n else None
            prof["audit_years_in_file"] = dict(years.most_common(6))
            prof["type_of_entity_values"] = dict(types.most_common(15))
            prof["tribal_auditee_rows"] = sum(
                v for k, v in types.items() if k.startswith("I"))
            prof["tribal_distinct_ein"] = len(tribal_eins)
            prof["tribal_total_fed_expend"] = round(tribal_exp, 2)
            prof["tribal_sample"] = tribal_rows

        if awd_name:
            with z.open(awd_name) as fh:
                txt = io.TextIOWrapper(fh, encoding="utf-8", errors="replace",
                                       newline="")
                rd = csv.DictReader(txt)
                cols = rd.fieldnames or []
                prof["awards_columns"] = cols
                cnt = 0
                for _ in rd:
                    cnt += 1
                prof["awards_rows"] = cnt
    return prof


def main():
    hosts = ["www.fac.gov", "app.fac.gov"]
    locks(hosts, True)
    os.makedirs(RAW, exist_ok=True)
    out = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "script": "code/203_verify_fac_historical_bulk_tribal.py",
        "why": ("api.fac.gov starts at audit_year 2016 (code/200). The Census-era "
                "1998-2015 archive lives on a DIFFERENT path. Probing one surface "
                "and concluding about the source is the error this project has "
                "already paid for twice."),
        "free_gb_at_start": round(free_gb(ROOT), 2),
        "index_page": {}, "boundary_probes": {}, "downloads": {}, "profiles": {},
    }
    try:
        if free_gb(ROOT) < DISK_FLOOR_GB:
            out["aborted"] = f"free disk below {DISK_FLOOR_GB} GB"
            return

        r, meta = req("GET", INDEX)
        if r is not None and r.status_code == 200:
            body = r.text
            meta["mentions_census_zip"] = body.count("census-")
            import re
            meta["years_linked"] = sorted(set(
                re.findall(r"census-(\d{4})\.zip", body)))
        out["index_page"] = meta

        for y in PROBE_ONLY:
            _, m = req("HEAD", ZIP_URL % y)
            out["boundary_probes"][y] = m

        for y in FETCH_YEARS:
            dest = os.path.join(RAW, f"census-{y}.zip")
            if os.path.exists(dest):
                out["downloads"][y] = {"outcome": "ALREADY_ON_DISK",
                                       "bytes": os.path.getsize(dest)}
            else:
                r, m = req("GET", ZIP_URL % y, stream=True)
                if r is None or r.status_code != 200:
                    out["downloads"][y] = m
                    continue
                tmp = dest + ".part"
                got = 0
                with open(tmp, "wb") as fh:
                    for chunk in r.iter_content(1 << 20):
                        if chunk:
                            fh.write(chunk)
                            got += len(chunk)
                os.replace(tmp, dest)          # .part then rename
                m["bytes_written"] = got
                out["downloads"][y] = m
                time.sleep(GAP)
            if os.path.exists(dest):
                try:
                    out["profiles"][y] = profile_zip(dest, y)
                except Exception as e:
                    out["profiles"][y] = {"error": repr(e)[:300]}
    finally:
        out["requests_issued"] = _n["i"]
        out["free_gb_at_end"] = round(free_gb(ROOT), 2)
        tmp = OUT + ".part"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1)
        os.replace(tmp, OUT)
        with open(OUT, encoding="utf-8") as fh:
            back = json.load(fh)
        assert back["script"] == out["script"], "re-read verification FAILED"
        locks(hosts, False, {"requests_issued": _n["i"],
                             "released": datetime.now(timezone.utc).isoformat()})
        print(f"wrote + verified {OUT}  ({_n['i']} requests)", file=sys.stderr)

    ip = out["index_page"]
    print(f"\nindex {INDEX}", file=sys.stderr)
    print(f"  status={ip.get('status')} years_linked={ip.get('years_linked')}",
          file=sys.stderr)
    print("\nboundary probes:", file=sys.stderr)
    for y, m in out["boundary_probes"].items():
        print(f"  census-{y}.zip  status={m.get('status')} "
              f"ctype={m.get('content_type')} len={m.get('content_length')}",
              file=sys.stderr)
    for y, p in out["profiles"].items():
        if "error" in p:
            print(f"\n{y}: {p['error']}", file=sys.stderr)
            continue
        print(f"\ncensus-{y}.zip  {p['bytes']:,} bytes, "
              f"{len(p['members'])} members", file=sys.stderr)
        print(f"  ELECAUDITHEADER rows = {p.get('header_rows'):,}",
              file=sys.stderr)
        print(f"  EIN populated  = {p.get('ein_populated_pct')}%",
              file=sys.stderr)
        print(f"  DUNS populated = {p.get('duns_populated_pct')}%",
              file=sys.stderr)
        print(f"  audit years in file: {p.get('audit_years_in_file')}",
              file=sys.stderr)
        print(f"  TRIBAL auditee rows = {p.get('tribal_auditee_rows'):,}; "
              f"distinct EIN = {p.get('tribal_distinct_ein'):,}; "
              f"total fed expend = ${p.get('tribal_total_fed_expend'):,.0f}",
              file=sys.stderr)
        if p.get("awards_rows"):
            print(f"  ELECAUDITS (auditee x CFDA) rows = {p['awards_rows']:,}",
                  file=sys.stderr)
        for s in (p.get("tribal_sample") or [])[:5]:
            print(f"    {s['auditee_name'][:44]:<44} EIN={s['ein']} "
                  f"exp={s['total_fed_expend']}", file=sys.stderr)


if __name__ == "__main__":
    main()
