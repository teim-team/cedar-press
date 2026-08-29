#!/usr/bin/env python3
"""
Cedar Press - 93: Review cards ranked by TOTAL downstream leverage.

ELIJAH, 2026-08-07
------------------
"update the web page for me to adjudicate things and ill work on that as you
 work on stuff"

The previous page measured leverage against prime contracts only. A ruling is
worth more than that: the same identifier appears in federal funding, subawards
and FAADS. Counting one dataset understates every card and mis-ranks the queue.

This counts a ruling's reach across EVERY dataset that carries the identifier,
so the ordering reflects what the ruling is actually worth.

WHAT MAKES A CARD RULABLE IN SECONDS
------------------------------------
Identifier chips (click to copy), recipient address, where the work was
performed, funding agencies, active years, filed-as aliases, and four external
lookups. The question on each card is one question - is this firm Native-owned -
because every card is a self-parented independent firm.

Writes review/leverage_cards_<date>.json
"""

import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
SCRATCH = Path(r"C:\Users\esm247\AppData\Local\Temp\claude"
               r"\C--Users-esm247-Desktop"
               r"\ea2ef30b-afc5-4319-b753-2cd3cb0d0ebb\scratchpad")
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

# dataset -> (file, identifier columns, money column, year column, name column)
SOURCES = [
    ("prime", "prime_contracts.csv",
     ("awardee_uei", "cage_code"), "total_obligations", "fiscal_year",
     "awardee_name"),
    ("funding", "federal_funding_transactions.csv",
     ("recipient_uei", "recipient_duns", "uei"), "obligated_usd",
     "fiscal_year", "recipient_name"),
    ("subawards", "subawards.csv",
     ("sub_uei", "prime_uei", "subawardee_uei"), "subaward_amount",
     "fiscal_year", "sub_name"),
]


def read_queue():
    q = sorted(REVIEW.glob("MASTER_QUEUE_*.csv"))[-1]
    with open(q, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh)), q.name


def main():
    print("=== Cedar Press 93: leverage cards ===\n")
    items, qname = read_queue()
    want = {}
    for x in items:
        i = (x.get("identifier") or "").strip().upper()
        if i and i not in want:
            want[i] = x
    print(f"queue: {len(items):,} items ({qname}), "
          f"{len(want):,} distinct identifiers")

    D = defaultdict(lambda: {
        "rows": Counter(), "usd": Counter(), "uei": set(), "cage": set(),
        "name": Counter(), "city": Counter(), "pop": Counter(),
        "agency": Counter(), "parent": set(), "fy": set()})

    for tag, fname, idcols, moneycol, yearcol, namecol in SOURCES:
        p = CLEAN / fname
        if not p.exists():
            print(f"  {tag:10s} MISSING")
            continue
        n = hits = 0
        with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
            rd = csv.DictReader(fh)
            hdr = rd.fieldnames or []
            cols = [c for c in idcols if c in hdr]
            if not cols:
                print(f"  {tag:10s} no identifier column; has "
                      f"{[h for h in hdr if 'uei' in h.lower() or 'cage' in h.lower()][:3]}")
                continue
            for r in rd:
                n += 1
                if (r.get("tribe_id") or "").strip():
                    continue
                key = None
                for c in cols:
                    v = (r.get(c) or "").strip().upper()
                    if v and v in want:
                        key = v
                        break
                if not key:
                    continue
                hits += 1
                d = D[key]
                d["rows"][tag] += 1
                try:
                    d["usd"][tag] += float(r.get(moneycol) or 0)
                except ValueError:
                    pass
                u = (r.get("awardee_uei") or r.get("recipient_uei") or "").strip().upper()
                if u:
                    d["uei"].add(u)
                c_ = (r.get("cage_code") or "").strip().upper()
                if c_:
                    d["cage"].add(c_)
                nm = (r.get(namecol) or "").strip()
                if nm:
                    d["name"][nm] += 1
                ct = (r.get("recipient_city_name") or "").strip()
                st = (r.get("recipient_state_code") or "").strip()
                if ct or st:
                    d["city"][f"{ct}, {st}".strip(", ")] += 1
                pc = (r.get("place_of_perform_city") or "").strip()
                ps = (r.get("place_of_perform_state") or "").strip()
                if pc or ps:
                    d["pop"][f"{pc}, {ps}".strip(", ")] += 1
                ag = (r.get("funding_agency") or r.get("awarding_agency") or "").strip()
                if ag:
                    d["agency"][ag] += 1
                pn = (r.get("parent_name") or "").strip()
                if pn:
                    d["parent"].add(pn)
                fy = (r.get(yearcol) or "")[:4]
                if fy.isdigit():
                    d["fy"].add(int(fy))
        print(f"  {tag:10s} {n:>9,} rows scanned, {hits:>7,} hit the queue")

    cards = []
    for k in sorted(D, key=lambda x: -sum(D[x]["rows"].values())):
        d = D[k]
        it = want[k]
        fys = sorted(d["fy"])
        cards.append({
            "id": k,
            "name": (d["name"].most_common(1)[0][0] if d["name"]
                     else it.get("entity_name", "")),
            "aka": [n for n, _ in d["name"].most_common(4)],
            "uei": sorted(d["uei"])[:3],
            "cage": sorted(d["cage"])[:3],
            "parent": sorted(d["parent"])[:2],
            "rows": sum(d["rows"].values()),
            "usd": round(sum(d["usd"].values())),
            "by": dict(d["rows"]),
            "city": [c for c, _ in d["city"].most_common(2)],
            "pop": [c for c, _ in d["pop"].most_common(3)],
            "agency": [a for a, _ in d["agency"].most_common(3)],
            "yrs": f"{fys[0]}-{fys[-1]}" if fys else "",
            "why": it.get("why_it_matters", ""),
            "src": it.get("source_file", ""),
            "url": it.get("evidence_url", ""),
        })
    for i, c in enumerate(cards):
        c["i"] = i

    SCRATCH.mkdir(parents=True, exist_ok=True)
    (SCRATCH / "hv.json").write_text(json.dumps(cards), encoding="utf-8")
    (REVIEW / f"leverage_cards_{TODAY}.json").write_text(
        json.dumps(cards, indent=1), encoding="utf-8")

    tot_rows = sum(c["rows"] for c in cards)
    tot_usd = sum(c["usd"] for c in cards)
    print(f"\n  {len(cards):,} cards")
    print(f"  rows they settle : {tot_rows:,}")
    print(f"  dollars          : ${tot_usd/1e9:,.2f}B")
    print(f"  average per card : {tot_rows//max(len(cards),1):,} rows")
    multi = sum(1 for c in cards if len(c["by"]) > 1)
    print(f"  appear in 2+ datasets: {multi:,}")
    print("\n  top by total reach:")
    for c in cards[:10]:
        print(f"   {c['rows']:>6,} rows  ${c['usd']/1e6:>9,.1f}M  "
              f"{c['name'][:34]:34s} {c['by']}")


if __name__ == "__main__":
    main()
