#!/usr/bin/env python3
"""
Cedar Press - SHARD F, step 2: the IHS Title V register of Urban Indian Organizations.

WHY THIS SOURCE
---------------
An `Urban Indian Organization` row in Cedar's register is a *federal programme
status*, not a self-description. IHS says so on the index page in one sentence:

    "The Urban Indian Organizations (UIO) listed below have current Title V
     Indian Health Care Improvement Act contracts with the Indian Health
     Service. UIOs have been arranged in alphabetical order based on the IHS
     area and respective State they belong in."

So this single federal directory carries, for every UIO, four things Cedar's
spine does not have and cannot honestly assert without a source:

    the organisation's own website     -> the web map
    Location (city) and State          -> the service area / catchment
    IHS Area                           -> the administrative region
    Service Level                      -> what the Title V contract actually buys
    Title V contract status itself     -> the `program_authority` inclusion basis

Twelve area pages, twelve requests, obeying robots and the 2s/host gap.

Output: data/staging/tribe_harvest/shard_f/ihs_uio_register.jsonl
"""
import html, json, os, re, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shard_f_fetch as F

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "staging", "tribe_harvest", "shard_f", "ihs_uio_register.jsonl")

INDEX = "https://www.ihs.gov/urban/urban-indian-organizations/"
AREAS = [
    "albuquerque", "bemidji", "billings", "california", "great-plains",
    "nashville", "navajo", "oklahoma-city", "phoenix", "portland", "tucson",
    "regional-national-tribal",
]

_TAGS = re.compile(r"<[^>]+>")


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(_TAGS.sub(" ", s))).strip()


def content_region(h):
    m = re.search(r'id="site_content"(.*?)</main>', h, re.S)
    return m.group(1) if m else ""


def parse_area(h, area, url):
    """Walk the content region in document order, tracking the current <h2> state
    heading, and emit one record per <li><a href=...>Name</a> block that is
    followed by a Location:/Service Level: sub-list."""
    body = content_region(h)
    if not body:
        return []
    out = []
    state = ""
    # split into tokens we care about, in order
    pat = re.compile(
        r"<h2[^>]*>(?P<h2>.*?)</h2>"
        r"|<li[^>]*>\s*<a\s+href=\"(?P<href>https?://[^\"]+)\"[^>]*>(?P<name>.*?)</a>"
        r"|<li[^>]*>\s*(?P<kv>(?:Location|Service Level|Services|Note)\s*:.*?)</li>",
        re.S | re.I,
    )
    cur = None
    for m in pat.finditer(body):
        if m.group("h2") is not None:
            state = clean(m.group("h2"))
            continue
        if m.group("href") is not None:
            href = html.unescape(m.group("href"))
            name = clean(m.group("name"))
            if "ihs.gov/Disclaimers" in href or not name:
                continue
            cur = {
                "org_name_as_listed": name,
                "org_website": href,
                "state_heading": state,
                "ihs_area": area,
                "location_city": "",
                "service_level": "",
                "notes": "",
                "source_url": url,
                "retrieved_date": time.strftime("%Y-%m-%d"),
                "authorizing_basis": (
                    "Title V, Indian Health Care Improvement Act - current IHS "
                    "contract, per the IHS Office of Urban Indian Health Programs "
                    "register"
                ),
                "authorizing_basis_quote": (
                    "The Urban Indian Organizations (UIO) listed below have current "
                    "Title V Indian Health Care Improvement Act contracts with the "
                    "Indian Health Service."
                ),
            }
            out.append(cur)
            continue
        if m.group("kv") is not None and cur is not None:
            kv = clean(m.group("kv"))
            k, _, v = kv.partition(":")
            k = k.strip().lower()
            v = v.strip()
            if k == "location":
                cur["location_city"] = v
            elif k in ("service level", "services"):
                cur["service_level"] = v
            else:
                cur["notes"] = (cur["notes"] + " " + kv).strip()
    return out


def main():
    idx = F.fetch(INDEX)
    print("index:", idx["http_status"], idx["robots_note"])
    if idx["http_status"] != 200:
        print("index unavailable; cannot enumerate areas", file=sys.stderr)
        return 1

    rows = []
    for a in AREAS:
        u = INDEX + a + "/"
        r = F.fetch(u)
        h = F.read_raw(r)
        got = parse_area(h, a, r.get("final_url") or u) if h else []
        print(f"  {a:26s} {str(r['http_status']):>4}  {len(got):3d} UIO entries")
        rows.extend(got)

    with open(OUT, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n{len(rows)} rows -> {os.path.relpath(OUT, ROOT)}")
    print(f"  with website     : {sum(1 for r in rows if r['org_website'])}")
    print(f"  with city        : {sum(1 for r in rows if r['location_city'])}")
    print(f"  with servicelevel: {sum(1 for r in rows if r['service_level'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
