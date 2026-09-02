"""562_probe_atom_native_flags_pre2000.py — bounded, read-only network probe.

ONE QUESTION: does the FPDS-NG ATOM feed carry Native business-type
identification on pre-FY2000 records?  If it does, an FY1981-FY1999 Native
slice is publicly obtainable.  If it does not, FY1981-FY1999 Native
contracting is not reconstructable from the public transaction record at
any price, and Cedar's FY2000 floor is a boundary rather than an omission.

PROBE DESIGN (docs/PULL_DISCIPLINE.md, "design your probes so their outcomes
ELIMINATE explanations").  FPDS ezSearch fields FAIL OPEN - an unknown field
returns HTTP 200 with zero results rather than an error - so a zero count is
only interpretable against a positive control.

  P1  flag query, FY2010          -> validates the field name.  >0 required.
  P2  flag query, FY1995          -> the actual question.
  P3  unfiltered FY1995           -> validates the feed serves FY1995 at all.
  P4  flag query, FY1999          -> where the on-disk extracts first show rows.
  P5  flag query, FY2005          -> when FPDS-NG flags were fully in force.

BUDGET: <= 12 requests, >= 2.0s gap, 8 minute deadline, GET of page 0 only
(the feed returns the advertised total in rel="last"; no paging).
Writes only data/staging/pre2000_probe/atom_native_flag_probe.json.
"""
import json, os, re, sys, time, datetime, urllib.parse

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "staging", "pre2000_probe")
LOCK = os.path.join(ROOT, "logs", "_HOSTLOCK_www.fpds.gov.json")
ATOM = "https://www.fpds.gov/ezsearch/FEEDS/ATOM"
HDR = {"User-Agent": "CedarPress/1.0 (research; pre-2000 coverage verification)"}
MAX_REQ, GAP, DEADLINE = 12, 2.0, 8 * 60

_n = [0]
_t0 = time.time()


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def claim(active, **extra):
    d = {"host": "www.fpds.gov", "pid": os.getpid(),
         "script": "code/562_probe_atom_native_flags_pre2000.py",
         "claimed_at": now(), "active": active, "queue": [],
         "policy": f"<= {MAX_REQ} requests, >= {GAP}s gap, {DEADLINE//60} min deadline, GET page 0 only",
         "note": "does the ATOM feed carry Native business-type flags pre-FY2000?"}
    d.update(extra)
    with open(LOCK, "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=1)


def atom(q):
    if _n[0] >= MAX_REQ:
        return {"outcome": "BUDGET_EXHAUSTED", "q": q}
    if time.time() - _t0 > DEADLINE:
        return {"outcome": "DEADLINE", "q": q}
    if _n[0]:
        time.sleep(GAP)
    _n[0] += 1
    t = time.time()
    try:
        r = requests.get(ATOM, params={"FEEDNAME": "PUBLIC", "q": q, "start": "0"},
                         headers=HDR, timeout=90)
    except Exception as e:
        return {"outcome": "EXCEPTION", "q": q, "error": f"{type(e).__name__}: {e}",
                "elapsed_s": round(time.time() - t, 2)}
    body = r.text
    total = None
    m = re.search(r'rel="last"[^>]*href="[^"]*?[?&]start=(\d+)', body)
    if m:
        total = int(m.group(1))
    entries = body.count("<entry>")
    if total is None and entries:
        total = entries
    return {"outcome": "OK" if r.status_code == 200 else f"HTTP_{r.status_code}",
            "q": q, "http": r.status_code, "elapsed_s": round(time.time() - t, 2),
            "advertised_total_or_last_offset": total, "entries_on_page_0": entries,
            "bytes": len(body)}


FY = {y: f"SIGNED_DATE:[{y-1}/10/01,{y}/09/30]" for y in (1995, 1999, 2005, 2010)}
# Native business-type fields as exposed by FPDS ezSearch.
FLAG = "INDIAN_TRIBE:Y"
FLAG_ALT = "ALASKAN_NATIVE_OWNED_CORPORATION_OR_FIRM:Y"

PROBES = [
    ("P1_flag_FY2010_positive_control", f"{FLAG} {FY[2010]}"),
    ("P2_flag_FY1995_THE_QUESTION", f"{FLAG} {FY[1995]}"),
    ("P3_unfiltered_FY1995_feed_serves_year", FY[1995]),
    ("P4_flag_FY1999", f"{FLAG} {FY[1999]}"),
    ("P5_flag_FY2005", f"{FLAG} {FY[2005]}"),
    ("P6_altflag_FY2010_positive_control", f"{FLAG_ALT} {FY[2010]}"),
    ("P7_altflag_FY1995", f"{FLAG_ALT} {FY[1995]}"),
    ("P8_nonsense_field_FY2010_failopen_test", f"CEDAR_NOT_A_FIELD:Y {FY[2010]}"),
]

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    claim(True)
    res = {"probed_at": now(), "probes": {}}
    try:
        for name, q in PROBES:
            res["probes"][name] = atom(q)
            print(name, json.dumps(res["probes"][name]), flush=True)
    finally:
        claim(False, requests_issued=_n[0], released=now())
    with open(os.path.join(OUT, "atom_native_flag_probe.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2)
    print(json.dumps(res, indent=2))
