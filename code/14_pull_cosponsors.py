"""
14_pull_cosponsors.py
Cedar Press Dataset 10 -- cosponsor gap fill.

The local Congress.gov pull in votingpatterns stored only a cosponsor COUNT, not the cosponsor
roster, so `member_positions.cosponsor_flag` cannot be filled from the copied files alone.
This script fetches the cosponsor roster from Congress.gov API v3 for the bills that actually
carry a tribal roll call (the only bills where cosponsor_flag is joinable to a member position).

Coverage limit, stated rather than papered over: Congress.gov cosponsor data begins with the
93rd Congress for hr/s and is complete from the 103rd; bills earlier than the 103rd that
return no cosponsor record are recorded with status=no_api_record, not as "zero cosponsors".

Key: CONGRESS_API_KEY from votingpatterns/.env. Never printed.
Output: data/clean/_cosponsors.csv  (bill_id, bioguide_id, full_name, party, state, date)
        data/clean/_cosponsor_fetch_log.csv (per-bill fetch status -- the provenance record)
"""
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
ENVFILE = Path(r"C:\Users\esm247\Desktop\votingpatterns\.env")
BASE = "https://api.congress.gov/v3"
SLEEP = 0.7
MAX_RETRIES = 4


def get_key():
    k = os.environ.get("CONGRESS_API_KEY", "").strip()
    if k:
        return k
    if ENVFILE.exists():
        for line in ENVFILE.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"\s*(?:export\s+)?CONGRESS_API_KEY\s*=\s*['\"]?([^'\"\s]+)", line)
            if m:
                return m.group(1)
    return ""


KEY = get_key()
if not KEY:
    print("No CONGRESS_API_KEY found; aborting cosponsor pull.")
    sys.exit(1)
print("API key loaded (value not logged).")


def api_get(url, params=None):
    q = dict(params or {})
    q["format"] = "json"
    q["api_key"] = KEY
    full = url + "?" + urllib.parse.urlencode(q)
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(full, headers={
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (academic research; Cedar Press; elijahsamsonmoreno@gmail.com)"})
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.loads(r.read().decode("utf-8"))
            time.sleep(SLEEP)
            return d, "ok"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None, "http_404"
            if e.code in (429, 500, 502, 503, 504):
                time.sleep((2 ** attempt) * 2)
                continue
            return None, f"http_{e.code}"
        except Exception as e:
            time.sleep((2 ** attempt) * 2)
            last = str(e)
    return None, "failed_after_retries"


def main():
    nb = pd.read_csv(CLEAN / "native_bills.csv", low_memory=False)
    tgt = nb[(nb.has_rollcall == 1) & (nb.bill_type.notna())].copy()
    # only types the API serves
    ok_types = {"hr", "s", "hres", "sres", "hjres", "sjres", "hconres", "sconres"}
    tgt = tgt[tgt.bill_type.isin(ok_types)]
    print(f"Bills with >=1 tribal roll call and an API-servable type: {len(tgt)}")

    rows, fetchlog = [], []
    for i, r in enumerate(tgt.itertuples(), 1):
        url = f"{BASE}/bill/{int(r.congress)}/{r.bill_type}/{r.number}/cosponsors"
        got, n_page, status = [], 0, "ok"
        offset = 0
        while True:
            d, st = api_get(url, {"limit": 250, "offset": offset})
            if d is None:
                status = st
                break
            cs = d.get("cosponsors", [])
            got.extend(cs)
            tot = (d.get("pagination") or {}).get("count", len(got))
            offset += 250
            if offset >= tot or not cs:
                break
        for c in got:
            rows.append({
                "bill_id": r.bill_id,
                "bioguide_id": c.get("bioguideId", ""),
                "full_name": c.get("fullName", ""),
                "party": c.get("party", ""),
                "state": c.get("state", ""),
                "district": c.get("district", ""),
                "sponsorship_date": c.get("sponsorshipDate", ""),
                "is_original": c.get("isOriginalCosponsor", ""),
            })
        if status == "ok" and not got:
            status = "no_api_record" if int(r.congress) < 103 else "zero_cosponsors_reported"
        fetchlog.append({"bill_id": r.bill_id, "congress": int(r.congress),
                         "bill_type": r.bill_type, "number": r.number,
                         "n_cosponsors": len(got), "status": status})
        if i % 25 == 0:
            print(f"  {i}/{len(tgt)} bills; {len(rows)} cosponsor rows", flush=True)

    pd.DataFrame(rows).to_csv(CLEAN / "_cosponsors.csv", index=False)
    fl = pd.DataFrame(fetchlog)
    fl.to_csv(CLEAN / "_cosponsor_fetch_log.csv", index=False)
    print(f"\nWROTE _cosponsors.csv rows={len(rows):,} bills={fl.bill_id.nunique():,}")
    print(fl.status.value_counts().to_string())


if __name__ == "__main__":
    main()
