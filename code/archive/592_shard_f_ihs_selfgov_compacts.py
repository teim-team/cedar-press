#!/usr/bin/env python3
"""
Cedar Press - SHARD F, step 10: the IHS register of Title V SELF-GOVERNANCE compacts.

WHAT THIS IS
------------
`https://www.ihs.gov/selfgovernance/tribes/` lists every Tribe and Tribal
Organization holding a Self-Governance compact with the Indian Health Service,
grouped by IHS Area, **each with the year it entered compact**. IHS states the
authority on its own landing page:

    "OTSG develops and oversees the implementation of Tribal Self-Governance
     legislation and authorities within the IHS under Title V of the Indian
     Self-Determination and Education Assistance Act (ISDEAA), Public Law
     93-638, as amended."

For this shard's 29 `Federal-level self-governance consortium` entities that is
the *defining* record - it is what makes the class true of them - and Cedar does
not have it. It is also a dated participation relation for several hundred
tribal governments, which is shards A-D's business, not mine; this file records
what the page says and leaves the attaching to them.

ONE PAGE, ONE REQUEST. The compact year is taken verbatim from the parenthesis
IHS prints; it is never inferred from anything else.

Output: data/staging/tribe_harvest/shard_f/ihs_selfgov_compacts.jsonl
"""
import json, os, re, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shard_f_fetch as F

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SH = os.path.join(ROOT, "data", "staging", "tribe_harvest", "shard_f")
OUT = os.path.join(SH, "ihs_selfgov_compacts.jsonl")
URL = "https://www.ihs.gov/selfgovernance/tribes/"
LANDING = "https://www.ihs.gov/selfgovernance/"

AREA = re.compile(
    r"^(Alaska|Albuquerque|Bemidji|Billings|California|Great Plains|Nashville|"
    r"Navajo|Oklahoma City|Phoenix|Portland|Tucson)\s+Area\s*\((\d+)\)\s*$", re.I)
ENTRY = re.compile(r"^(.+?)\s*\((\d{4})\)\s*$")

QUOTE = ("OTSG develops and oversees the implementation of Tribal Self-Governance "
         "legislation and authorities within the IHS under Title V of the Indian "
         "Self-Determination and Education Assistance Act (ISDEAA), Public Law "
         "93-638, as amended.")


def main():
    r = F.fetch(URL)
    print("compact register:", r["http_status"], r["robots_note"])
    if r["http_status"] != 200:
        print("register unavailable", file=sys.stderr)
        return 1
    h = F.read_raw(r)
    m = re.search(r'id="site_content"(.*?)</main>', h, re.S)
    body = m.group(1) if m else h
    lines = [re.sub(r"\s+", " ", x).strip()
             for x in F.to_text(body).split("\n")]

    rows = []
    area = ""
    area_n = ""
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        am = AREA.match(ln)
        if am:
            area, area_n = am.group(1), am.group(2)
            continue
        em = ENTRY.match(ln)
        if not em or not area:
            continue
        name = em.group(1).strip(" -–—")
        year = em.group(2)
        if len(name) < 4 or len(name) > 140:
            continue
        parent, program = "", ""
        if "–" in name or "—" in name:
            parts = re.split(r"\s*[–—]\s*", name, 1)
            parent, program = parts[0].strip(), parts[1].strip()
        rows.append({
            "ihs_area": area,
            "ihs_area_count_as_printed": area_n,
            "name_as_listed": name,
            "parent_tribe_as_listed": parent,
            "program_as_listed": program,
            "compact_year": year,
            "authorizing_basis": "isdeaa_title_v_self_governance_compact",
            "authorizing_basis_quote": QUOTE,
            "authorizing_basis_source": LANDING,
            "source_url": r.get("final_url") or URL,
            "retrieved_date": time.strftime("%Y-%m-%d"),
        })

    with open(OUT, "w", encoding="utf-8") as fh:
        for x in rows:
            fh.write(json.dumps(x, ensure_ascii=False) + "\n")

    import collections
    c = collections.Counter(x["ihs_area"] for x in rows)
    printed = {x["ihs_area"]: int(x["ihs_area_count_as_printed"]) for x in rows}
    print(f"{len(rows)} compacts -> {os.path.relpath(OUT, ROOT)}")
    for a in sorted(c):
        flag = "" if c[a] == printed.get(a) else f"  <-- IHS PRINTS {printed.get(a)}"
        print(f"  {a:15s} parsed {c[a]:3d}{flag}")
    tot = sum(printed.values())
    print(f"  parsed total {len(rows)} against IHS's own per-area counts summing to {tot}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
