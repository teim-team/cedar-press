#!/usr/bin/env python3
"""
Cedar Press - 59: Source index and discovery channel for the deals ledger.

TWO THINGS ELIJAH ASKED FOR, AND THEY ARE NOT THE SAME THING
------------------------------------------------------------
"make sure for these that the source is included so it can be clicked on ...
 and also for deals you can include a field if tribal business news reported on
 it (in which case prob shouldnt be a source but where they found it)"

1. SOURCE - the document that establishes the fact. An SEC filing, an agency
   award list, a company's own release. This is what a subscriber cites.

2. DISCOVERY CHANNEL - how we came to know the deal existed. Tribal Business
   News reporting on an acquisition is real and useful, but the trade press is
   not the authority for the date or the amount; the filing is.

Collapsing them would let a trade-press mention masquerade as the evidence
behind a number. Keeping them apart means a row can say honestly: found via
Tribal Business News, verified against the SEC filing.

CLASSIFICATION
--------------
By domain, because that is a fact about the publisher rather than a judgement:

  AUTHORITY    .gov, sec.gov, agency award lists, the party's own site,
               the state ANCSA portal, rating agencies
  TRADE_PRESS  tribalbusinessnews.com and the like - discovery, not authority
  WIRE         prnewswire and friends - the company's own words, but
               distributed rather than filed
  ARCHIVE      web.archive.org - inherits the authority of what it archived,
               so it is resolved to the ORIGINAL url before classifying

Reads  data/clean/deals_classified.csv   <- THE TRUTH for the deal universe
       (was `deals_*_additions.csv`, which indexed 790 of 935 rows; fixed
       2026-08-26, `docs/FACT_CHECK_2026-08-06.md` finding B-1)
Writes data/clean/deals_source_index.csv   party -> sources + discovery channel
"""

import csv
import glob
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cedar_domain as DOM   # noqa: E402  - DEALS_TRUTH

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
TODAY = date.today().isoformat()

TRADE_PRESS = {
    "tribalbusinessnews.com", "indiancountrytoday.com", "ictnews.org",
    "nativenewsonline.net", "indianz.com", "tribalcollegejournal.org",
    "casino.org", "cdcgamingreports.com", "ggbmagazine.com",
}
WIRE = {"prnewswire.com", "businesswire.com", "globenewswire.com",
        "accesswire.com", "newswire.ca"}

# web.archive.org/web/<timestamp>/<original>  - the archive is a delivery
# mechanism, not a publisher. Classify what it archived.
WAYBACK_RE = re.compile(r"web\.archive\.org/web/[^/]+/(?P<orig>https?://.+)$", re.I)
DOMAIN_RE = re.compile(r"https?://([^/]+)", re.I)


def domain_of(url):
    m = WAYBACK_RE.search(url or "")
    if m:
        url = unquote(m.group("orig"))
    m = DOMAIN_RE.search(url or "")
    return m.group(1).lower().replace("www.", "") if m else ""


def classify(url):
    d = domain_of(url)
    if not d:
        return "", "NONE"
    if d in TRADE_PRESS:
        return d, "TRADE_PRESS"
    if d in WIRE:
        return d, "WIRE"
    if d.endswith(".gov") or ".gov/" in (url or "") or d.endswith(".mil"):
        return d, "AUTHORITY"
    if d.endswith(".edu"):
        return d, "AUTHORITY"
    return d, "AUTHORITY_OR_PARTY"


def read_csv(p):
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def main():
    print("=== Cedar Press 59: deal source index ===\n")

    by_party = defaultdict(lambda: {"srcs": [], "trade": set(), "n": 0})
    kinds = Counter()

    # THE TRUTH: data/clean/deals_classified.csv (cedar_domain.DEALS_TRUTH).
    #
    # This globbed `deals_*_additions.csv` until 2026-08-26 and so indexed the
    # sources of 790 rows while the ledger held 935 - the 145 rows from the two
    # root ledgers and the August collection contributed NO source URLs to
    # `deals_source_index.csv`. An index that silently omits a source is worse
    # than an absent one, because it is the file a reader checks to see whether
    # a deal is sourced. `docs/FACT_CHECK_2026-08-06.md` finding B-1; see
    # `cedar_domain.PROMOTED_TABLES`.
    for r in read_csv(CEDAR / DOM.DEALS_TRUTH):
        party = (r.get("Native_Party") or "").strip()
        if not party:
            continue
        rec = by_party[party]
        rec["n"] += 1
        for col in ("Source_1", "Source_2"):
            url = (r.get(col) or "").strip()
            if not url:
                continue
            dom, kind = classify(url)
            kinds[kind] += 1
            if kind == "TRADE_PRESS":
                # Discovery, not evidence.
                rec["trade"].add(dom)
                continue
            if url not in [s["url"] for s in rec["srcs"]]:
                rec["srcs"].append({"url": url, "label": dom or col,
                                    "kind": kind})

    print("source classification")
    for k, v in kinds.most_common():
        print(f"  {v:5d}  {k}")

    rows = []
    for party, rec in sorted(by_party.items()):
        # Authority first, so the clickable source a subscriber sees leads with
        # the document that actually establishes the fact.
        srcs = sorted(rec["srcs"],
                      key=lambda s: (s["kind"] != "AUTHORITY", s["label"]))[:3]
        rows.append({
            "native_party": party,
            "n_deals": rec["n"],
            "source_1_url": srcs[0]["url"] if srcs else "",
            "source_1_label": srcs[0]["label"] if srcs else "",
            "source_1_kind": srcs[0]["kind"] if srcs else "",
            "source_2_url": srcs[1]["url"] if len(srcs) > 1 else "",
            "source_2_label": srcs[1]["label"] if len(srcs) > 1 else "",
            "discovery_channel": "; ".join(sorted(rec["trade"])),
            "n_sources": len(rec["srcs"]),
            "built_date": TODAY,
        })

    p = CLEAN / "deals_source_index.csv"
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\n  wrote {p.relative_to(CEDAR)}  ({len(rows):,} parties)")

    withsrc = sum(1 for r in rows if r["source_1_url"])
    withtrade = sum(1 for r in rows if r["discovery_channel"])
    print(f"  parties with a clickable source : {withsrc:,} / {len(rows):,}")
    print(f"  parties found via trade press   : {withtrade:,}  "
          f"(recorded as discovery, NOT as the source of the number)")


if __name__ == "__main__":
    main()
