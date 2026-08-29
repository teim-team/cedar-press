#!/usr/bin/env python3
"""
Cedar Press - 75: Native philanthropy discovery via IRS Form 990 Schedule I.

Elijah's idea, 2026-08-06:
  "native americans in philanthropy is also a big org and you can look at the
   shakopee and who they give money to same with san manuel band and we can
   prob find more native orgs we could be missing"

Every roster used so far is a LIST OF A KIND (federally recognised tribes,
ANCs, NHOs, TCUs). A grantee list is different: it is a list of WHO NATIVE
MONEY ACTUALLY GOES TO, which surfaces organisations that appear on no roster
because they do not fit a category.

SOURCE
------
IRS Form 990 Schedule I Part II, "Grants and Other Assistance to Domestic
Organizations and Domestic Governments" - grantee name, address, EIN, IRC
section, cash amount, purpose. Structured and machine-readable.

ACCESS ROUTE (measured 2026-08-06)
----------------------------------
  * ProPublica Nonprofit Explorer JSON API  -> org lookup, filings list.  200
  * ProPublica org HTML page                -> object_id per filing.       200
  * ProPublica /nonprofits/full_text/<object_id>/IRS990ScheduleI
                                            -> rendered Schedule I.        200
  * ProPublica /nonprofits/download-xml?object_id=...  -> 403 Security Check
  * s3.amazonaws.com/irs-form-990/<object_id>_public.xml -> 404 NoSuchKey
    (the AWS mirror stopped being updated; IRS moved to per-year ZIPs)
So the full_text render is the working route. Responses are gzipped: curl
needs --compressed / urllib needs manual gzip handling.

api.usaspending.gov is NOT touched by this script. Host lock for
projects.propublica.org is at logs/_HOSTLOCK_projects.propublica.org.json.
Sequential, one request at a time, 1.2s spacing (ProPublica rate-limits softly
per docs/PULL_DISCIPLINE.md).

USAGE
-----
    py -3 code/75_philanthropy_schedule_i.py find      # resolve funder EINs
    py -3 code/75_philanthropy_schedule_i.py pull      # Schedule I grantees
    py -3 code/75_philanthropy_schedule_i.py resolve   # full names by EIN
"""

import csv
import gzip
import html
import io
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
RAW = CEDAR / "data" / "raw" / "external" / "philanthropy"
RAW.mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
PAUSE = 1.2

# Funders to work. Native grantmakers that actually file a 990 with a
# Schedule I, plus the tribal funders Elijah named (tribal GOVERNMENTS do not
# file 990s under IRC 7871 - their charitable arms sometimes do, which is
# exactly what `find` is testing).
FUNDERS = [
    "First Nations Development Institute",
    "Native Americans in Philanthropy",
    "NDN Collective",
    "American Indian College Fund",
    "Native American Agriculture Fund",
    "Notah Begay III Foundation",
    "Potlatch Fund",
    "Seventh Generation Fund for Indigenous Peoples",
    "Indian Land Tenure Foundation",
    "Running Strong for American Indian Youth",
    "Native Ways Federation",
    "American Indian Graduate Center",
    "Shakopee Mdewakanton Sioux Community",
    "San Manuel Band of Mission Indians",
    "Yuhaaviatam of San Manuel Nation",
    "Chickasaw Foundation",
    "Cherokee Nation Foundation",
    "Mohegan Tribe",
    "Mashantucket Pequot",
    "Tulalip Tribes Charitable Fund",
    "Muckleshoot Charity Fund",
    "Morongo Band of Mission Indians",
    "Pechanga Band of Indians",
    "Seminole Tribe of Florida",
]


def get(url, binary=False, tries=3):
    """One GET. Exponential backoff, never a metronome. Returns text or None."""
    wait = 20
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Accept-Encoding": "gzip",
            "Accept": "*/*",
        })
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                body = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
                time.sleep(PAUSE)
                return body if binary else body.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                print(f"    throttle {e.code}; backing off {wait}s")
                time.sleep(wait)
                wait *= 2
                continue
            print(f"    HTTP {e.code} {url}")
            return None
        except Exception as e:                                  # noqa: BLE001
            print(f"    {type(e).__name__} {url}: {e}")
            time.sleep(wait)
            wait *= 2
    return None


def find_funders():
    out = []
    for name in FUNDERS:
        u = ("https://projects.propublica.org/nonprofits/api/v2/search.json?q="
             + urllib.parse.quote(name))
        txt = get(u)
        if not txt:
            out.append({"query": name, "n_results": "FETCH_FAILED"})
            continue
        d = json.loads(txt)
        orgs = d.get("organizations", [])
        print(f"{name}: {d.get('total_results')} results")
        for o in orgs[:6]:
            print(f"    {o['strein']}  {o['name']}  {o.get('city')}, "
                  f"{o.get('state')}  sub={o.get('subseccd')}")
            out.append({"query": name, "ein": o["ein"], "strein": o["strein"],
                        "name": o["name"], "city": o.get("city"),
                        "state": o.get("state"), "subseccd": o.get("subseccd"),
                        "source_url": u})
    p = RAW / "funder_search_results_2026-08-06.csv"
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["query", "ein", "strein", "name",
                                           "city", "state", "subseccd",
                                           "source_url", "n_results"])
        w.writeheader()
        for r in out:
            w.writerow(r)
    print(f"\n-> {p}")


# Schedule I Part II row. The render pipes fields; the shape is:
#   (n) NAME | ADDR | CITY | , | ST | ZIP | EIN | IRCSEC | AMOUNT | [noncash..] | PURPOSE
ROW = re.compile(
    r"\((\d+)\)\|(?P<name>[^|]+)\|(?P<addr>[^|]*)\|(?P<city>[^|]*)\|,\|"
    r"(?P<st>[A-Z]{2})\|(?P<zip>[0-9\-]*)\|(?P<ein>\d{2}-\d{7})\|"
    r"(?P<irc>[^|]*)\|(?P<rest>.*?)(?=\|\(\d+\)\||$)")


def sched_i_text(object_id):
    u = (f"https://projects.propublica.org/nonprofits/full_text/{object_id}"
         f"/IRS990ScheduleI")
    h = get(u)
    if not h:
        return None, u
    h = re.sub(r"<style.*?</style>", "", h, flags=re.S)
    t = re.sub(r"<[^>]+>", "|", h)
    t = html.unescape(t)
    t = re.sub(r"[|\s]*\|[|\s]*", "|", t)
    return t, u


def object_ids(ein):
    u = f"https://projects.propublica.org/nonprofits/organizations/{ein}"
    h = get(u)
    if not h:
        return [], u
    ids, seen = [], set()
    for m in re.finditer(r"object_id=(\d+)", h):
        if m.group(1) not in seen:
            seen.add(m.group(1))
            ids.append(m.group(1))
    return ids, u


def pull(targets):
    """targets: list of (ein, funder_name, n_years)."""
    rows = []
    for ein, fname, nyears in targets:
        print(f"\n=== {fname} (EIN {ein})")
        ids, org_url = object_ids(ein)
        if not ids:
            print("    no object_ids")
            continue
        for oid in ids[:nyears]:
            t, u = sched_i_text(oid)
            if not t:
                continue
            m = re.search(r"TY (\d{4}) Form 990", t)
            ty = m.group(1) if m else ""
            n = 0
            for mm in ROW.finditer(t):
                rest = mm.group("rest")
                nums = re.findall(r"([\d,]{3,})", rest)
                amt = nums[0].replace(",", "") if nums else ""
                purpose = rest.split("|")[-1].strip()
                rows.append({
                    "funder_name": fname, "funder_ein": ein,
                    "tax_year": ty, "object_id": oid,
                    "grantee_name_as_filed": mm.group("name").strip(),
                    "grantee_ein": mm.group("ein").replace("-", ""),
                    "grantee_city": mm.group("city").strip(),
                    "grantee_state": mm.group("st"),
                    "grantee_zip": mm.group("zip"),
                    "irc_section_as_filed": mm.group("irc").strip(),
                    "cash_grant_usd": amt,
                    "purpose_as_filed": purpose,
                    "source_url": u,
                    "funder_org_url": org_url,
                    "retrieved_date": "2026-08-06",
                })
                n += 1
            print(f"    TY{ty} object {oid}: {n} grantee rows")
    p = RAW / "schedule_i_grantees_2026-08-06.csv"
    write = "a" if p.exists() and "--append" in sys.argv else "w"
    with open(p, write, newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        if write == "w":
            w.writeheader()
        w.writerows(rows)
    print(f"\n{len(rows)} rows -> {p}")


def resolve(eins, outname):
    """Full legal name / NTEE / city / state per EIN, from the ProPublica
    record. Schedule I truncates names at ~34 chars; the EIN does not lie."""
    out = []
    for i, ein in enumerate(eins, 1):
        u = (f"https://projects.propublica.org/nonprofits/api/v2/"
             f"organizations/{ein}.json")
        t = get(u)
        if not t:
            out.append({"ein": ein, "status": "FETCH_FAILED", "source_url": u})
            continue
        try:
            o = json.loads(t)["organization"]
        except Exception:                                       # noqa: BLE001
            out.append({"ein": ein, "status": "NOT_FOUND", "source_url": u})
            continue
        out.append({
            "ein": ein, "status": "ok", "name": o.get("name"),
            "sub_name": o.get("sub_name"), "city": o.get("city"),
            "state": o.get("state"), "ntee_code": o.get("ntee_code"),
            "subseccd": o.get("subseccd"),
            "address": o.get("address"),
            "ruling_date": o.get("ruling_date"),
            "tax_period": o.get("tax_period"),
            "revenue_amount": o.get("revenue_amount"),
            "asset_amount": o.get("asset_amount"),
            "latest_object_id": o.get("latest_object_id"),
            "subsection_code": o.get("subsection_code"),
            "source_url": u, "retrieved_date": "2026-08-06",
        })
        if i % 25 == 0:
            print(f"    {i}/{len(eins)}")
    p = RAW / outname
    cols = ["ein", "status", "name", "sub_name", "city", "state", "ntee_code",
            "subseccd", "subsection_code", "address", "ruling_date",
            "tax_period", "revenue_amount", "asset_amount",
            "latest_object_id", "source_url", "retrieved_date"]
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)
    print(f"{len(out)} rows -> {p}")


MISSION_PATS = [
    # Form 990 Part I line 1 and Part III line 1, as the render labels them.
    r"Briefly describe the organization's mission[^|]*\|(?P<m>[^|]{15,900})",
    r"Briefly describe the organization.s mission:\|(?P<m>[^|]{15,900})",
    r"Description\|(?P<m>[^|]{25,900})",
]


def missions(eins, outname):
    """The org's own words, from its own return. This is the evidence that
    settles Native status for an organisation whose NAME carries no Native
    token - the discoveries that matter most, and the ones a name-based
    classifier can only guess at.

    Two requests per org: the JSON record (for latest_object_id) and the
    rendered Form 990 page.
    """
    out = []
    for i, ein in enumerate(eins, 1):
        ju = (f"https://projects.propublica.org/nonprofits/api/v2/"
              f"organizations/{ein}.json")
        t = get(ju)
        oid = None
        if t:
            try:
                oid = json.loads(t)["organization"].get("latest_object_id")
            except Exception:                                   # noqa: BLE001
                oid = None
        rec = {"ein": ein, "object_id": oid or "", "mission": "",
               "source_url": "", "retrieved_date": "2026-08-06"}
        if oid:
            u = (f"https://projects.propublica.org/nonprofits/full_text/"
                 f"{oid}/IRS990")
            h = get(u)
            if h:
                h = re.sub(r"<style.*?</style>", "", h, flags=re.S)
                txt = re.sub(r"<[^>]+>", "|", h)
                txt = html.unescape(txt)
                txt = re.sub(r"[|\s]*\|[|\s]*", "|", txt)
                rec["source_url"] = u
                for pat in MISSION_PATS:
                    m = re.search(pat, txt)
                    if m and m.group("m").strip():
                        rec["mission"] = " ".join(m.group("m").split())
                        break
                if not rec["mission"]:
                    # 990-EZ / 990-PF render differently; keep a slice so the
                    # ruling can still be made from retrieved text.
                    k = txt.find("Part III")
                    if k > 0:
                        rec["mission"] = " ".join(
                            txt[k:k + 600].replace("|", " ").split())
        out.append(rec)
        if i % 20 == 0:
            print(f"    {i}/{len(eins)}")
    p = RAW / outname
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["ein", "object_id", "mission",
                                           "source_url", "retrieved_date"])
        w.writeheader()
        w.writerows(out)
    print(f"{len(out)} rows -> {p}")


def fn_profiles(pairs, outname):
    """First Nations Development Institute publishes a full Awarded Grants
    database (1994-2026, 464 result pages) plus a per-grantee profile page at
    /grantee-profiles/<slug>/.

    That page is the best evidence this channel offers for the organisations
    that no roster can see: it carries a project DESCRIPTION written about the
    grantee, and a "Community Partners" field that names the affiliated tribe.
    It is a published grantee list - Task 2 - reached through Task 1's names.

    Different host from ProPublica; still sequential, still spaced.
    """
    out = []
    for i, (ein, name) in enumerate(pairs, 1):
        base = re.sub(r"[^a-z0-9]+", "-",
                      name.lower().replace("'", "").replace("’", "")
                      ).strip("-")
        variants = [base]
        for suf in ("-inc", "-incorporated", "-corporation", "-llc"):
            if base.endswith(suf):
                variants.append(base[: -len(suf)])
        variants.append(base + "-inc")
        seen = set()
        for slug in [v for v in variants if not (v in seen or seen.add(v))][:3]:
            u = f"https://www.firstnations.org/grantee-profiles/{slug}/"
            h = get(u)
            if not h or "Page Not Found" in h[:4000]:
                continue
            h2 = re.sub(r"<(script|style|nav|footer)[^>]*>.*?</\1>", "", h,
                        flags=re.S)
            t = re.sub(r"<[^>]+>", "|", h2)
            t = html.unescape(t)
            t = re.sub(r"[|\s]*\|[|\s]*", "|", t)
            title = t.split("|")[1] if "|" in t else ""
            partners = "; ".join(sorted(set(
                m.group(1) for m in
                re.finditer(r"Community Partners\|([^|]+)\|", t))))
            descs = [m.group(1).strip() for m in
                     re.finditer(r"Description\|([^|]{25,})\|", t)]
            descs = sorted(set(descs), key=len, reverse=True)
            m = re.search(r"\|(\d+)\|Grants\|\$([\d,]+)\|Total Awarded\|"
                          r"([\d\s\-]+)\|Years", t)
            out.append({
                "ein": ein, "query_name": name, "slug": slug,
                "profile_title": title,
                "n_grants": m.group(1) if m else "",
                "total_awarded": m.group(2) if m else "",
                "years": " ".join(m.group(3).split()) if m else "",
                "community_partners": partners,
                "description": descs[0] if descs else "",
                "source_url": u, "retrieved_date": "2026-08-06",
            })
            break
        if i % 20 == 0:
            print(f"    {i}/{len(pairs)}  hits={len(out)}")
    p = RAW / outname
    cols = ["ein", "query_name", "slug", "profile_title", "n_grants",
            "total_awarded", "years", "community_partners", "description",
            "source_url", "retrieved_date"]
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(out)
    print(f"{len(out)} profiles -> {p}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "find"
    if cmd == "find":
        find_funders()
    elif cmd == "pull":
        spec = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        pull([(s["ein"], s["name"], s.get("years", 2)) for s in spec])
    elif cmd in ("resolve", "missions"):
        eins = [l.strip() for l in
                Path(sys.argv[2]).read_text(encoding="utf-8").split()
                if l.strip()]
        (resolve if cmd == "resolve" else missions)(eins, sys.argv[3])
    elif cmd == "fnprofiles":
        pairs = [tuple(l.split("\t")) for l in
                 Path(sys.argv[2]).read_text(encoding="utf-8").splitlines()
                 if "\t" in l]
        fn_profiles(pairs, sys.argv[3])
