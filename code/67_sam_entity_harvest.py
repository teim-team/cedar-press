#!/usr/bin/env python3
"""
Cedar Press - 67: Harvest Native entities and hierarchy from the SAM.gov API.

STATUS: READY TO RUN, BLOCKED ON ONE THING.
    The stored SAM key returns HTTP 401 API_KEY_INVALID on BOTH v3 and v4 -
    it was rotated 2026-07-25. Paste the replacement into
    dissertation/data/tribal_federal_spending/.env.local as SAM_GOV_API_KEY and
    this runs unchanged.

WHY THIS IS WORTH DOING - AND WHICH PART IS THE PRIZE
-----------------------------------------------------
Two distinct things are on offer, and the SECOND is worth more than the one
that gets talked about.

1. ENTITY HIERARCHY. Parent/child structure straight from SAM rather than
   inferred from FPDS. Useful - but it is **FOUO, not public**. A basic public
   API key returns name, UEI, address, business types, NAICS and PSC and does
   NOT return hierarchy. Whether we get it depends on the sensitivity level of
   the account the key belongs to. Do not plan around it until proven.

2. SELF-DECLARED BUSINESS TYPE. This IS public, and it is the prize. Every SAM
   registrant declares its own business types, and the codeset includes
   tribally owned, Alaska Native Corporation owned, and Native Hawaiian
   Organization owned. That is a roster of firms **declaring themselves Native
   to the federal government**, with UEI and CAGE attached.

   It is a completely independent axis from everything Cedar Press has. Our
   crosswalk is built from names, rulings and FPDS parentage. This is
   self-declaration under penalty of False Claims Act liability. Where the two
   agree, confidence is genuinely corroborated. Where they DISAGREE, that
   disagreement is the most valuable output in the file - it is either a firm
   we missed or a declaration that does not hold up.

   Alutiiq Pacific declares itself ANC-owned. We know it is Afognak's only
   because Elijah told us.

THE RATE LIMIT IS THE DESIGN CONSTRAINT
---------------------------------------
A basic account is **10 requests per day**. Per-UEI lookups are therefore
useless: 13,000 identifiers would take three and a half years.

The extract endpoint returns up to **1,000,000 records in one request**. So the
whole strategy is: ONE request per business-type code, asynchronous, download
the file. Ten codes fits inside a basic account's daily budget. This script
never issues a per-UEI call.

CODES ARE DISCOVERED, NOT GUESSED
---------------------------------
The exact business-type code strings differ across API versions and I will not
hard-code values I have not seen returned. `--discover` pulls a sample, prints
every business-type code and description SAM actually returns, and writes them
to disk. Then `--extract` uses the confirmed codes.

Usage
    py -3 code/67_sam_entity_harvest.py --probe      # is the key alive?
    py -3 code/67_sam_entity_harvest.py --discover   # what codes exist
    py -3 code/67_sam_entity_harvest.py --extract    # bulk pull
    py -3 code/67_sam_entity_harvest.py --reconcile  # compare to our ledger
"""

import csv
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
RAW = CEDAR / "data" / "raw" / "external" / "sam_api"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

ENV = Path(r"C:\Users\esm247\Desktop\dissertation\data\tribal_federal_spending\.env.local")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}

BASE = "https://api.sam.gov/entity-information/v4/entities"

# Free-text seeds. Used only for DISCOVERY of the codeset, never as evidence -
# a name containing "tribal" is not an attribution and this script never treats
# it as one.
SEEDS = ["tribal", "tribe", "native american", "alaska native",
         "native hawaiian", "indian"]


def key():
    if not ENV.exists():
        raise SystemExit(f"no env file at {ENV}")
    for line in ENV.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("SAM_GOV_API_KEY="):
            k = line.split("=", 1)[1].strip().strip('"').strip("'")
            if k:
                return k
    raise SystemExit("SAM_GOV_API_KEY not set in .env.local")


def get(params, timeout=90):
    url = BASE + "?" + urllib.parse.urlencode(params)
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                   timeout=timeout)
        return json.loads(r.read()), None
    except Exception as e:
        body = ""
        try:
            body = e.read().decode()[:200]
        except Exception:
            pass
        code = getattr(e, "code", "")
        if code == 401 or "API_KEY_INVALID" in body:
            return None, ("KEY INVALID - the stored SAM key was rotated "
                          "2026-07-25. Collect the replacement from the SAM.gov "
                          "profile page (Public API Key) and put it in "
                          f"{ENV}")
        if code == 429:
            return None, "RATE LIMITED - a basic account is 10 requests/day."
        return None, f"{type(e).__name__} {code} {body[:120]}"


def probe():
    d, err = get({"api_key": key(), "ueiSAM": "HD9LT6J78NB3"})
    print(f"  {'OK, key is live' if d else err}")
    if d:
        print(f"  totalRecords={d.get('totalRecords')}")
    return bool(d)


def discover():
    """Print every business-type code SAM actually returns. No guessing."""
    RAW.mkdir(parents=True, exist_ok=True)
    codes, seen = Counter(), {}
    for q in SEEDS:
        d, err = get({"api_key": key(), "q": q, "page": 0,
                      "includeSections": "entityRegistration,coreData"})
        if not d:
            print(f"  '{q}': {err}")
            if "KEY INVALID" in (err or ""):
                return
            continue
        ents = d.get("entityData") or []
        print(f"  '{q}': {d.get('totalRecords')} records, sampled {len(ents)}")
        for e in ents:
            core = e.get("coreData") or {}
            bt = ((core.get("businessTypes") or {}).get("businessTypeList")) or []
            for b in bt:
                c = b.get("businessTypeCode", "")
                codes[c] += 1
                seen[c] = b.get("businessTypeDesc", "")
        time.sleep(2)

    rows = [{"business_type_code": c, "description": seen.get(c, ""),
             "seen_in_sample": n, "discovered": TODAY}
            for c, n in codes.most_common()]
    if rows:
        p = RAW / "sam_business_type_codes.csv"
        with open(p, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"\n  wrote {p.relative_to(CEDAR)}  ({len(rows)} codes)")
        print("\n  codes whose description mentions a Native form:")
        for r in rows:
            if re.search(r"tribal|tribe|indian|alaska native|native hawaiian",
                         r["description"], re.I):
                print(f"     {r['business_type_code']:6s} {r['description']}")


def extract():
    """One request per confirmed code. Never per-UEI - see the rate limit."""
    p = RAW / "sam_business_type_codes.csv"
    if not p.exists():
        raise SystemExit("run --discover first; codes are not hard-coded")
    with open(p, encoding="utf-8-sig", newline="") as fh:
        codes = [r for r in csv.DictReader(fh)
                 if re.search(r"tribal|tribe|indian|alaska native|native hawaiian",
                              r["description"], re.I)]
    print(f"  extracting {len(codes)} Native business-type codes")
    RAW.mkdir(parents=True, exist_ok=True)
    for c in codes:
        d, err = get({"api_key": key(), "businessTypeCode": c["business_type_code"],
                      "includeSections": "entityRegistration,coreData",
                      "format": "json", "size": 10000})
        if not d:
            print(f"    {c['business_type_code']}: {err}")
            continue
        out = RAW / f"sam_entities_{c['business_type_code']}_{TODAY}.json"
        out.write_text(json.dumps(d), encoding="utf-8")
        print(f"    {c['business_type_code']:6s} {d.get('totalRecords')} records "
              f"-> {out.name}")
        time.sleep(5)


def reconcile():
    """Compare SAM's self-declaration against our crosswalk.

    Three outcomes, and the third is the point:
      AGREE      SAM says Native, we say Native  -> corroboration
      SAM_ONLY   SAM says Native, we have nothing -> candidates we missed
      OURS_ONLY  we attribute, SAM does not declare -> not a contradiction;
                 a tribal government does not register as a "tribally owned
                 firm". Reported, never used to withdraw an attribution.
    """
    files = sorted(RAW.glob("sam_entities_*.json"))
    if not files:
        raise SystemExit("no extract files - run --extract first")
    sam = {}
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        for e in d.get("entityData") or []:
            reg = e.get("entityRegistration") or {}
            uei = (reg.get("ueiSAM") or "").strip().upper()
            if uei:
                sam[uei] = {"name": reg.get("legalBusinessName", ""),
                            "cage": reg.get("cageCode", ""),
                            "source_file": f.name}
    print(f"  SAM self-declared Native registrants: {len(sam):,}")

    ours = {}
    with open(CLEAN / "cedar_identifier_ledger_final.csv",
              encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            if r.get("identifier_type") == "UEI" and \
                    r.get("confidence_tier") in ("A", "B"):
                ours[r["identifier"].upper()] = r.get("canonical_name", "")

    agree = sorted(set(sam) & set(ours))
    sam_only = sorted(set(sam) - set(ours))
    ours_only = sorted(set(ours) - set(sam))
    print(f"    AGREE     : {len(agree):,}")
    print(f"    SAM only  : {len(sam_only):,}  <- candidates we missed")
    print(f"    ours only : {len(ours_only):,}  <- not a contradiction")

    rows = [{"uei": u, "sam_legal_name": sam[u]["name"], "cage": sam[u]["cage"],
             "status": "SAM_ONLY_candidate", "cedar_entity": "",
             "note": "Self-declared Native to SAM; absent from our crosswalk. "
                     "A CANDIDATE, not an attribution.", "found": TODAY}
            for u in sam_only]
    if rows:
        p = REVIEW / f"sam_selfdeclared_not_in_ledger_{TODAY}.csv"
        with open(p, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"    wrote {p.relative_to(CEDAR)}")


if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else "--probe"
    print(f"=== Cedar Press 67: SAM harvest ({a}) ===\n")
    {"--probe": probe, "--discover": discover,
     "--extract": extract, "--reconcile": reconcile}[a]()
