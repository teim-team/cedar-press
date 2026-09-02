"""
200_probe_fac_historical_depth.py
=================================
Cedar Press. Written 2026-08-26.

QUESTION: how far back does the Federal Audit Clearinghouse actually go, and
does it name the recipient (EIN) before FY2007?

`data/clean/fac_tribal_single_audits.csv` spans audit_year 2016-2026. That is a
property of the PULL, which used a 2016 floor -- not necessarily a property of
the source. The Single Audit universe predates 2007 (the Single Audit Act
Amendments date from 1996), and the Census-era clearinghouse covered 1997-2015.

If api.fac.gov serves pre-2007 tribal records WITH an `auditee_ein`, then
per-entity federal spending before FY2007 is observable through the SEFA --
a completely different route from FAADS, keyed on EIN rather than on a name.

DISCIPLINE: api.fac.gov is fronted by api.data.gov (1,000 req/hr). This probe
issues at most ~20 requests, 0.6s apart, with a wall-clock deadline, claims the
host lock, and stops on the first edge refusal. It writes ONE json to docs/ and
touches no clean table.

Run:  py -3 code/200_probe_fac_historical_depth.py
"""

import json
import os
import sys
import time
from datetime import datetime, timezone

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "FAC_HISTORICAL_DEPTH_PROBE.json")
LOCK = os.path.join(ROOT, "logs", "_HOSTLOCK_api.fac.gov.json")

API = "https://api.fac.gov"
KEY = os.environ.get("API_DATA_GOV_KEY",
                     "xAmmmCQ05iWdMTWfhvBeSgul008UxCUfSsdZRbex")
UA = ("CedarPress-research/1.0 (+https://cedarpress.co; "
      "elijahsamsonmoreno@gmail.com)")
HDR = {"X-Api-Key": KEY, "User-Agent": UA, "Accept": "application/json"}

GAP = 0.7
DEADLINE_S = 12 * 60
MAX_REQUESTS = 24

START = time.time()
_req = {"n": 0}


def claim_lock():
    """Rule 1/2: one poller per host. Refuse if a LIVE holder exists."""
    if os.path.exists(LOCK):
        try:
            cur = json.load(open(LOCK, encoding="utf-8"))
        except Exception:
            cur = {}
        if cur.get("active"):
            print("api.fac.gov is held by another poller (active=true). "
                  "Exiting without a request.", file=sys.stderr)
            sys.exit(3)
    payload = {
        "host": "api.fac.gov",
        "pid": os.getpid(),
        "script": "code/200_probe_fac_historical_depth.py",
        "claimed_at": datetime.now(timezone.utc).isoformat(),
        "active": True,
        "queue": [],
        "policy": f"sequential, single poller, >={GAP}s gap, "
                  f"max {MAX_REQUESTS} requests, {DEADLINE_S//60} min deadline",
        "note": "historical-depth probe: earliest audit_year, tribal EIN pre-2007",
    }
    tmp = LOCK + ".part"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
    os.replace(tmp, LOCK)
    return payload


def release_lock(payload, result_note):
    payload["active"] = False
    payload["released"] = datetime.now(timezone.utc).isoformat()
    payload["requests_issued"] = _req["n"]
    payload["result"] = result_note
    tmp = LOCK + ".part"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
    os.replace(tmp, LOCK)


def get(path, params, want_count=False):
    """One metered GET. Returns (status, json_or_text, content_range)."""
    if _req["n"] >= MAX_REQUESTS:
        return ("BUDGET_EXHAUSTED", None, None)
    if time.time() - START > DEADLINE_S:
        return ("DEADLINE", None, None)
    h = dict(HDR)
    if want_count:
        h["Prefer"] = "count=exact"
        h["Range-Unit"] = "items"
        h["Range"] = "0-0"
    _req["n"] += 1
    try:
        r = requests.get(f"{API}/{path}", params=params, headers=h, timeout=60)
    except Exception as e:
        return ("TRANSPORT", repr(e), None)
    time.sleep(GAP)
    cr = r.headers.get("Content-Range", "")
    try:
        body = r.json()
    except Exception:
        body = r.text[:400]
    return (r.status_code, body, cr)


def main():
    lock = claim_lock()
    out = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "script": "code/200_probe_fac_historical_depth.py",
        "host": "api.fac.gov",
        "probes": [],
    }
    note = "incomplete"
    try:
        # 1. earliest audit_year ANYWHERE in the dissemination table
        st, body, cr = get("general",
                           {"select": "audit_year,auditee_ein,auditee_name,"
                                      "entity_type,fac_accepted_date",
                            "order": "audit_year.asc", "limit": "3"})
        out["probes"].append({"probe": "earliest audit_year, any entity_type",
                              "status": st, "content_range": cr, "body": body})
        if st == 200 and isinstance(body, list) and body:
            out["earliest_audit_year_any"] = body[0].get("audit_year")

        # 2. earliest audit_year for entity_type = tribal
        st, body, cr = get("general",
                           {"select": "audit_year,auditee_ein,auditee_name,"
                                      "auditee_state,total_amount_expended,is_public",
                            "entity_type": "eq.tribal",
                            "order": "audit_year.asc", "limit": "5"})
        out["probes"].append({"probe": "earliest audit_year, entity_type=tribal",
                              "status": st, "content_range": cr, "body": body})
        if st == 200 and isinstance(body, list) and body:
            out["earliest_audit_year_tribal"] = body[0].get("audit_year")

        # 3. does ANY row exist with audit_year < 2016?  (count, cheap)
        st, body, cr = get("general",
                           {"select": "report_id", "audit_year": "lt.2016"},
                           want_count=True)
        out["probes"].append({"probe": "count of rows audit_year < 2016",
                              "status": st, "content_range": cr,
                              "body": body if not isinstance(body, list) else "(list)"})
        out["count_all_before_2016"] = cr

        # 4. tribal rows before 2016
        st, body, cr = get("general",
                           {"select": "report_id", "entity_type": "eq.tribal",
                            "audit_year": "lt.2016"},
                           want_count=True)
        out["probes"].append({"probe": "count tribal rows audit_year < 2016",
                              "status": st, "content_range": cr,
                              "body": body if not isinstance(body, list) else "(list)"})
        out["count_tribal_before_2016"] = cr

        # 5. tribal rows before 2007 -- the question that matters
        st, body, cr = get("general",
                           {"select": "report_id", "entity_type": "eq.tribal",
                            "audit_year": "lt.2007"},
                           want_count=True)
        out["probes"].append({"probe": "count tribal rows audit_year < 2007",
                              "status": st, "content_range": cr,
                              "body": body if not isinstance(body, list) else "(list)"})
        out["count_tribal_before_2007"] = cr

        # 6. per-year census of tribal rows for the early window, if any exist
        early = {}
        for y in range(1997, 2017):
            if _req["n"] >= MAX_REQUESTS - 2:
                early[str(y)] = "BUDGET_EXHAUSTED"
                break
            st, body, cr = get("general",
                               {"select": "report_id",
                                "entity_type": "eq.tribal",
                                "audit_year": f"eq.{y}"},
                               want_count=True)
            early[str(y)] = {"status": st, "content_range": cr}
            if st not in (200, 206):
                break
        out["tribal_rows_by_early_year"] = early

        note = "completed"
    finally:
        out["requests_issued"] = _req["n"]
        tmp = OUT + ".part"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1)
        os.replace(tmp, OUT)
        with open(OUT, encoding="utf-8") as fh:
            back = json.load(fh)
        assert back["script"] == out["script"], "re-read verification FAILED"
        release_lock(lock, note)
        print(f"wrote + verified {OUT}  ({_req['n']} requests)", file=sys.stderr)

    print("\nearliest audit_year (any):   ",
          out.get("earliest_audit_year_any"), file=sys.stderr)
    print("earliest audit_year (tribal):",
          out.get("earliest_audit_year_tribal"), file=sys.stderr)
    print("count all < 2016:   ", out.get("count_all_before_2016"), file=sys.stderr)
    print("count tribal < 2016:", out.get("count_tribal_before_2016"), file=sys.stderr)
    print("count tribal < 2007:", out.get("count_tribal_before_2007"), file=sys.stderr)
    print("\nper-year tribal counts:", file=sys.stderr)
    for y, v in sorted(out.get("tribal_rows_by_early_year", {}).items()):
        print(f"  {y}: {v}", file=sys.stderr)


if __name__ == "__main__":
    main()
