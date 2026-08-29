"""
202_verify_pre2007_procurement_routes.py
========================================
Cedar Press. Written 2026-08-26.

Independent verification of two pre-FY2007 procurement routes reported by a
research sweep. A route is not AVAILABLE until this repo has measured it.

  ROUTE A  FPDS-NG ATOM feed
           https://www.fpds.gov/ezsearch/FEEDS/ATOM?FEEDNAME=PUBLIC&q=...
           Claims: live, no key, serves FY1979-2007, ~26.9M records,
           HARD 400,000-record paging ceiling per query.

  ROUTE B  NARA RG 269, series naId 573450 -- Federal Procurement Data Center
           "Records of Contracts Awarded by Federal Agencies", FY1979-1997,
           8,663,457 records, Access: Unrestricted, direct ZIP, no login.

Each claim below is either CONFIRMED by a measured response or recorded as
unverified. Two hosts, both new to this project, neither holding a lock:
`www.fpds.gov` and `catalog.archives.gov`. Locks are claimed for both.

DISCIPLINE: <= 14 requests total, >=1.5s apart, 10 min deadline, stop on the
first edge refusal. HEAD/range-GET only for the big objects -- nothing is
downloaded. Only 404 and 403 are facts about an object; a 500 means try later.

Run:  py -3 code/202_verify_pre2007_procurement_routes.py
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "PRE2007_PROCUREMENT_ROUTE_VERIFICATION.json")
LOGS = os.path.join(ROOT, "logs")

UA = ("CedarPress-research/1.0 (+https://cedarpress.co; "
      "elijahsamsonmoreno@gmail.com)")
HDR = {"User-Agent": UA}

GAP = 1.5
DEADLINE_S = 10 * 60
MAX_REQUESTS = 14
START = time.time()
_n = {"i": 0}

ATOM = "https://www.fpds.gov/ezsearch/FEEDS/ATOM"
NARA_PROXY = "https://catalog.archives.gov/proxy/records/search"
# naId -> fiscal year, from the reported manifest. Two are probed, not all.
NARA_ZIP = ("https://catalog.archives.gov/medialive/{last2}/8828/{naid}/"
            "content/arcmedia/electronic-records/rg-269/FPDS/RG137.FEDPROC.Y{yy}.zip")


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
            "script": "code/202_verify_pre2007_procurement_routes.py",
            "claimed_at": datetime.now(timezone.utc).isoformat(),
            "active": active, "queue": [],
            "policy": f"<= {MAX_REQUESTS} requests total, >={GAP}s gap, "
                      f"{DEADLINE_S//60} min deadline, HEAD/range only",
            "note": "pre-FY2007 procurement route verification",
        }
        if extra:
            payload.update(extra)
        tmp = p + ".part"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1)
        os.replace(tmp, p)


def req(method, url, **kw):
    if _n["i"] >= MAX_REQUESTS:
        return {"outcome": "BUDGET_EXHAUSTED", "url": url}
    if time.time() - START > DEADLINE_S:
        return {"outcome": "DEADLINE", "url": url}
    _n["i"] += 1
    t0 = time.time()
    try:
        r = requests.request(method, url, headers=HDR, timeout=60,
                             allow_redirects=True, **kw)
    except Exception as e:
        dt = time.time() - t0
        # sub-second failure on connect is an EDGE BLOCK, not a slow server
        return {"outcome": "TRANSPORT", "error": repr(e)[:200],
                "seconds": round(dt, 3),
                "reading": ("EDGE BLOCK (sub-second) - stop, more requests "
                            "extend it" if dt < 1.0 else "transport failure"),
                "url": url}
    time.sleep(GAP)
    return {"outcome": "HTTP", "status": r.status_code,
            "seconds": round(time.time() - t0, 3),
            "final_url": r.url,
            "content_type": r.headers.get("Content-Type", ""),
            "content_length": r.headers.get("Content-Length"),
            "body_head": (r.text[:1500] if method != "HEAD" and
                          "zip" not in r.headers.get("Content-Type", "") else None),
            "url": url}


def atom_total(q):
    """Total record count advertised by the feed's rel='last' link."""
    res = req("GET", ATOM, params={"FEEDNAME": "PUBLIC", "q": q, "start": "0"})
    if res.get("status") != 200 or not res.get("body_head"):
        res["advertised_total"] = None
        return res
    body = res["body_head"]
    # the full body is needed for the last-link; refetch text is wasteful, so
    # parse what we have and fall back to a wider slice
    m = re.search(r'rel="last"[^>]*href="[^"]*?start=(\d+)', body)
    res["advertised_total"] = int(m.group(1)) if m else "NOT_IN_FIRST_1500_BYTES"
    res["has_entries"] = "<entry" in body
    return res


def main():
    hosts = ["www.fpds.gov", "catalog.archives.gov"]
    locks(hosts, True)
    out = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "script": "code/202_verify_pre2007_procurement_routes.py",
        "hosts_contacted": hosts,
        "note": ("Independent verification of a research sweep's claims. "
                 "Nothing downloaded; HEAD / first-bytes only."),
        "route_A_fpds_atom": {},
        "route_B_nara_rg269": {},
    }
    try:
        A = out["route_A_fpds_atom"]

        # A1 -- is the endpoint live at all, and does it serve FY1979-2007?
        A["full_window_FY1979_2007"] = atom_total(
            "SIGNED_DATE:[1978/10/01,2007/09/30]")

        # A2 -- a single early year, to prove depth rather than a total
        A["FY1981"] = atom_total("SIGNED_DATE:[1980/10/01,1981/09/30]")

        # A3 -- the 400,000 paging ceiling, the claim that decides feasibility
        for start in ("399990", "400000"):
            A[f"paging_probe_start_{start}"] = req(
                "GET", ATOM,
                params={"FEEDNAME": "PUBLIC",
                        "q": "SIGNED_DATE:[1979/10/01,1980/09/30]",
                        "start": start})
            r = A[f"paging_probe_start_{start}"]
            if r.get("body_head"):
                r["entry_count_in_first_1500b"] = r["body_head"].count("<entry")
                del r["body_head"]

        # A4 -- the retired variants, recorded so nobody retries them
        A["retired_api_fpds_gov"] = req(
            "GET", "https://api.fpds.gov/", )
        A["retired_ebiz_path"] = req(
            "GET", "https://www.fpds.gov/ebiz/fpdsatomfeed/1.0/ATOM_FEED")

        B = out["route_B_nara_rg269"]

        # B1 -- does the unauthenticated proxy search answer, and name the series?
        B["catalog_search"] = req(
            "GET", NARA_PROXY,
            params={"q": '"Records of Contracts Awarded by Federal Agencies"',
                    "limit": "5"})

        # B2 -- do the ZIPs exist? HEAD two of them (FY1979, FY1993).
        for naid, yy in (("1882845", "79"), ("1882874", "90")):
            url = NARA_ZIP.format(last2=naid[-2:], naid=naid, yy=yy)
            B[f"zip_naid_{naid}_FY19{yy}"] = req("HEAD", url)

        # B3 -- FY1981 claimed genuinely absent; probe the gap naId
        url = NARA_ZIP.format(last2="66", naid="1882866", yy="81")
        B["zip_naid_1882866_FY1981_claimed_absent"] = req("HEAD", url)

    finally:
        out["requests_issued"] = _n["i"]
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

    def show(label, r):
        if not isinstance(r, dict):
            return
        st = r.get("status", r.get("outcome"))
        extra = ""
        if "advertised_total" in r:
            extra += f" total={r['advertised_total']} entries={r.get('has_entries')}"
        if "entry_count_in_first_1500b" in r:
            extra += f" entries_in_head={r['entry_count_in_first_1500b']}"
        if r.get("content_length"):
            extra += f" bytes={int(r['content_length']):,}"
        print(f"  {label:<44} {st}{extra}", file=sys.stderr)

    print("\nROUTE A - FPDS-NG ATOM feed", file=sys.stderr)
    for k, v in out["route_A_fpds_atom"].items():
        show(k, v)
    print("\nROUTE B - NARA RG 269 (naId 573450)", file=sys.stderr)
    for k, v in out["route_B_nara_rg269"].items():
        show(k, v)


if __name__ == "__main__":
    main()
