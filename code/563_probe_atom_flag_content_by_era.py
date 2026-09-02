"""563_probe_atom_flag_content_by_era.py — bounded, read-only network probe.

562 could not settle the question because FPDS ezSearch FIELDS FAIL OPEN: an
unknown field name returns HTTP 200 with zero entries, identically to a valid
field with no matches (verified: a deliberately nonsense field returned the
same empty feed as the Native-flag candidates).  A filter probe therefore
cannot distinguish "wrong field name" from "no such data".

So this probe reads the RECORDS instead of filtering them.  The FY1995 ATOM
entry carries the full modern schema, including isIndianTribe,
isTriballyOwnedFirm, isAlaskanNativeOwnedCorporationOrFirm and
isNativeHawaiianOwnedOrganizationOrFirm.  The question is whether those
elements carry VALUES on pre-FY2000 records or are structurally empty.

Sampling: N pages of 10 entries at spread offsets per fiscal year.  For each
entry, count (a) any Native socio-economic indicator true, (b) ANY vendor
socio-economic indicator true at all.  (b) is the control: if the entire
certification block is empty pre-2000, no Native filter can ever recover it,
and the absence is a property of the source rather than of the query.

BUDGET: <= 40 requests, >= 1.5s gap, 12 minute deadline, GET only.
Writes only data/staging/pre2000_probe/atom_flag_content_by_era.json.
"""
import json, os, re, time, datetime, collections
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "staging", "pre2000_probe")
LOCK = os.path.join(ROOT, "logs", "_HOSTLOCK_www.fpds.gov.json")
ATOM = "https://www.fpds.gov/ezsearch/FEEDS/ATOM"
HDR = {"User-Agent": "CedarPress/1.0 (research; pre-2000 coverage verification)"}
MAX_REQ, GAP, DEADLINE = 40, 1.5, 12 * 60
_n, _t0 = [0], time.time()

NATIVE = ["isIndianTribe", "isTriballyOwnedFirm", "isTribalGovernment",
          "isTribalCollege", "isAlaskanNativeOwnedCorporationOrFirm",
          "isAlaskanNativeServicingInstitution", "isAmericanIndianOwned",
          "isNativeAmericanOwnedBusiness", "isNativeHawaiianOwnedOrganizationOrFirm",
          "isNativeHawaiianServicingInstitution", "isHousingAuthoritiesPublicOrTribal"]


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def claim(active, **extra):
    d = {"host": "www.fpds.gov", "pid": os.getpid(),
         "script": "code/563_probe_atom_flag_content_by_era.py", "claimed_at": now(),
         "active": active, "queue": [],
         "policy": f"<= {MAX_REQ} requests, >= {GAP}s gap, {DEADLINE//60} min deadline, GET only",
         "note": "do pre-FY2000 FPDS records carry vendor socio-economic values?"}
    d.update(extra)
    with open(LOCK, "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=1)


def get(q, start):
    if _n[0] >= MAX_REQ or time.time() - _t0 > DEADLINE:
        return None
    if _n[0]:
        time.sleep(GAP)
    _n[0] += 1
    try:
        r = requests.get(ATOM, params={"FEEDNAME": "PUBLIC", "q": q, "start": str(start)},
                         headers=HDR, timeout=90)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}
    return {"http": r.status_code, "body": r.text}


def total_of(body):
    m = re.search(r'rel="last"[^>]*?start=(\d+)', body)
    return int(m.group(1)) + 10 if m else None


def sample_fy(fy, pages=6):
    q = f"SIGNED_DATE:[{fy-1}/10/01,{fy}/09/30]"
    first = get(q, 0)
    if not first or "body" not in first:
        return {"fy": fy, "error": first}
    tot = total_of(first["body"])
    offsets = [0]
    if tot and tot > 10:
        step = max(10, (tot // pages) // 10 * 10)
        offsets = [min(o, (tot - 10) // 10 * 10) for o in range(0, step * pages, step)][:pages]
        offsets = sorted(set(offsets))
    bodies = [first["body"]]
    for o in offsets[1:]:
        r = get(q, o)
        if r and "body" in r:
            bodies.append(r["body"])
    ent = 0
    any_socio = 0
    any_native = 0
    per_flag = collections.Counter()
    truthy = collections.Counter()
    for b in bodies:
        for e in b.split("<entry>")[1:]:
            e = e.split("</entry>")[0]
            ent += 1
            block = re.findall(r"<ns1:(is[A-Za-z0-9]+)>([^<]*)</ns1:", e)
            hit_s = hit_n = False
            for tag, val in block:
                v = val.strip().lower()
                truthy[v] += 1
                if v in ("true", "y", "yes", "1"):
                    hit_s = True
                    per_flag[tag] += 1
                    if tag in NATIVE:
                        hit_n = True
            any_socio += hit_s
            any_native += hit_n
    return {"fy": fy, "advertised_total": tot, "pages_fetched": len(bodies),
            "entries_sampled": ent, "entries_with_any_socio_true": any_socio,
            "entries_with_any_native_socio_true": any_native,
            "value_vocabulary": dict(truthy.most_common(8)),
            "top_true_flags": dict(per_flag.most_common(12))}


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    claim(True)
    res = {"probed_at": now(), "years": {}}
    try:
        for fy in (1985, 1990, 1995, 1999, 2005, 2010):
            res["years"][str(fy)] = sample_fy(fy)
            print(json.dumps(res["years"][str(fy)]), flush=True)
    finally:
        claim(False, requests_issued=_n[0], released=now())
    with open(os.path.join(OUT, "atom_flag_content_by_era.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2)
