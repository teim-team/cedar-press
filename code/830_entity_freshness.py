#!/usr/bin/env python3
"""
Cedar Press - 830: WHEN WAS EACH ENTITY LAST TOUCHED BY ANYTHING?

    py -3 code/830_entity_freshness.py            # measure + write
    py -3 code/830_entity_freshness.py verify     # exit 1 if the ledger is stale

WHY
---
Owner, 2026-09-01: *"Are you scanning every Native entity? Are you keeping
track of that? When's the last time something's been updated? I think the last
time something's been updated is a good thing to keep track of. Update could be
any change."*

Nothing tracked it, and three other instruments each answer a different
question:

  `528` SHARD_COVERAGE     does this entity have a website
  `630` REFRESH_CADENCE    is this SOURCE behind its publisher
  `518` DATASET_READINESS  does this DATASET meet the contract

None of them can answer *"has anybody looked at the Ely Shoshone Tribe this
year?"* - which is the owner's standing worry, stated back in August: **certain
Native entities might never get updated, silently, because nothing counts them.**

A dataset can be READY, its sources CURRENT and its coverage complete while an
individual entity sits untouched for two years, because every one of those
measures aggregates across entities. This one does not aggregate.

WHAT COUNTS AS AN UPDATE
------------------------
The owner's answer: **any change.** So this is deliberately generous - a row
appearing, a date advancing, an identifier landing, an attribution being
corrected. It reads every date-bearing column on every row keyed to an entity
and takes the newest.

What it does NOT do is read `built_date` or `fetched_date` as evidence about
the ENTITY. Those say when CEDAR ran, not when anything about the entity
changed, and 70 tables carry one - counting them would report every entity as
fresh today and the ledger would be worthless. That is the same defect
`cedar_period_columns.py` was written about, and the `NEVER_PERIOD` list there
exists for it.

THE NUMBER THAT MATTERS IS THE TAIL
-----------------------------------
Not the median. An entity nobody has touched in 500 days is invisible to every
other gate, and it is exactly the row a customer notices.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today()
CLEAN = ROOT / "data" / "clean"
REG = ROOT / "data" / "spine" / "cedar_identity_register.csv"
OUT = ROOT / "data" / "clean" / "cedar_entity_freshness.csv"
OUT_MD = ROOT / "docs" / "ENTITY_FRESHNESS.md"

ID_COLS = ("cedar_uid", "tribe_id", "entity_id", "nation_id",
           "certifying_authority_entity_id", "recipient_entity_id")

# Dates about CEDAR, never about the entity. Counting these reports every
# entity as touched today and makes the ledger a mirror of the last build.
# Dates about CEDAR's own activity. The first version missed `asserted_date`
# and it won for 856 of 1,555 entities - `cedar_assertions.asserted_date` is
# when WE recorded a claim, not when anything about the entity changed. Every
# entity then read as touched today and the ledger said nothing at all.
NEVER = re.compile(
    r"built|fetched|harvest|retrieved|measured|checked|keyed|stamped|"
    r"ingest|parsed|scraped|crawl|_run|load|refresh|generated|written|"
    r"assert|observ|ruled|adjudicat|resolv|minted|promoted|reviewed|"
    r"first_seen|last_seen|_date_added")
DATEY = re.compile(r"date|year|period|_at$|_on$|expir|vintage|updated|"
                   r"filed|published|effective|start|end|close|open")
ISO = re.compile(r"^(19|20)\d\d-\d\d(-\d\d)?")
YEAR = re.compile(r"^(19|20)\d\d$")


def parse(v: str):
    v = (v or "").strip()
    if not v:
        return None
    if ISO.match(v):
        return v[:10] if len(v) >= 10 else v + "-01"
    if YEAR.match(v):
        y = int(v)
        if 1800 <= y <= TODAY.year + 2:
            # A BARE YEAR IS A PERIOD, NOT A DAY. Resolving FY2026 to
            # 2026-12-31 made 594 entities read as fresher than today and
            # FY2027 rows read as 2027 - a future date cannot be evidence of a
            # past change. Take the year's end, then let the caller cap it.
            return f"{y}-12-31"
    return None


def cap(d: str):
    """A future date is DISCARDED, not clamped to today.

    Clamping was the second wrong answer in a row. A bare `fiscal_year` of 2026
    resolves to 2026-12-31, which is in the future; clamping it to today made
    every entity holding a current-FY row read as touched TODAY - maximally
    fresh, which is the exact opposite of what the field means. Median went to
    6 days and the tail vanished. A period that has not finished is not
    evidence that anybody touched this entity, so it contributes nothing."""
    return d if d <= TODAY.isoformat() else None


def main() -> int:
    verify = len(sys.argv) > 1 and sys.argv[1] == "verify"

    reg = list(csv.DictReader(REG.open(encoding="utf-8-sig", errors="replace")))
    known = {r["cedar_uid"]: r for r in reg if r.get("cedar_uid")}
    by_handle = {r["handle"]: r["cedar_uid"] for r in reg if r.get("handle")}

    last: dict = defaultdict(lambda: ("", "", ""))   # uid -> (date, table, col)
    seen_in: dict = defaultdict(set)
    rows_of: dict = defaultdict(int)

    tables = sorted(p for p in CLEAN.glob("*.csv")
                    if ".bak" not in p.name and not p.name.startswith("_"))
    scanned = 0
    for p in tables:
        try:
            with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
                rd = csv.DictReader(fh)
                hdr = rd.fieldnames or []
                idc = next((c for c in ID_COLS if c in hdr), None)
                if not idc:
                    continue
                dcols = [c for c in hdr
                         if DATEY.search(c.lower()) and not NEVER.search(c.lower())]
                scanned += 1
                for r in rd:
                    raw = (r.get(idc) or "").strip()
                    if not raw:
                        continue
                    uid = raw if raw in known else by_handle.get(raw)
                    if not uid:
                        continue
                    seen_in[uid].add(p.name)
                    rows_of[uid] += 1
                    for c in dcols:
                        d = parse(r.get(c))
                        d = cap(d) if d else None
                        if d and d > last[uid][0]:
                            last[uid] = (d, p.name, c)
        except OSError:
            continue

    out = []
    for uid, r in known.items():
        d, tbl, col = last.get(uid, ("", "", ""))
        age = ""
        if d:
            try:
                y, m, dd = (int(x) for x in d.split("-"))
                age = (TODAY - date(y, m, dd)).days
            except ValueError:
                age = ""
        out.append({
            "cedar_uid": uid,
            "handle": r.get("handle", ""),
            "canonical_name": r.get("canonical_name", ""),
            "entity_class": r.get("entity_class", ""),
            "last_change": d,
            "days_since_change": age,
            "last_change_table": tbl,
            "last_change_column": col,
            "n_datasets_present_in": len(seen_in.get(uid, ())),
            "n_rows_across_cedar": rows_of.get(uid, 0),
            "measured_date": TODAY.isoformat(),
        })
    out.sort(key=lambda x: (x["last_change"] or "0000", x["canonical_name"]))

    never = [x for x in out if not x["last_change"]]
    absent = [x for x in out if x["n_rows_across_cedar"] == 0]
    aged = [x for x in out if isinstance(x["days_since_change"], int)]
    old365 = [x for x in aged if x["days_since_change"] > 365]

    if not verify:
        with OUT.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
            w.writeheader()
            for x in out:
                w.writerow(x)
        L = ["# Entity freshness — when was each entity last touched by anything",
             "",
             f"*Generated {TODAY} by `code/830_entity_freshness.py` across "
             f"{scanned} entity-bearing tables. An update is ANY change: a row "
             f"appearing, a date advancing, an identifier landing. `built_date` "
             f"and `fetched_date` are deliberately NOT counted — they say when "
             f"Cedar ran, not when the entity changed, and 70 tables carry one.*",
             "",
             "This answers a question no other instrument can. Coverage says "
             "who has a website; cadence says which SOURCE is behind; readiness "
             "says which DATASET meets the contract. All three aggregate across "
             "entities, so an entity can sit untouched for two years while every "
             "one of them reads green.",
             "",
             "| | n |", "|---|---:|",
             f"| entities in the register | {len(out):,} |",
             f"| **appear in NO Cedar row at all** | **{len(absent):,}** |",
             f"| present but carrying no usable date | {len(never) - len(absent):,} |",
             f"| last change more than a year ago | {len(old365):,} |", ""]
        if aged:
            s = sorted(x["days_since_change"] for x in aged)
            L += [f"Median days since last change: **{s[len(s)//2]:,}**. "
                  f"p90: **{s[int(len(s)*.9)]:,}**. Oldest: **{s[-1]:,}**.", "",
                  "## The tail — 25 entities nobody has touched longest", "",
                  "| entity | class | last change | days | where |",
                  "|---|---|---|---:|---|"]
            for x in [y for y in out if y["last_change"]][:25]:
                L.append(f"| {x['canonical_name'][:34]} | "
                         f"{x['entity_class'][:26]} | {x['last_change']} | "
                         f"{x['days_since_change']:,} | "
                         f"`{x['last_change_table']}` |")
        if absent:
            L += ["", f"## Present in the register, absent from every dataset — "
                      f"{len(absent):,}", "",
                  "These are the entities the owner has been asking about since "
                  "August: they exist in the identity layer and no Cedar dataset "
                  "has a single row for them.", "",
                  "| entity | class |", "|---|---|"]
            for x in absent[:30]:
                L.append(f"| {x['canonical_name'][:40]} | {x['entity_class']} |")
        OUT_MD.write_text("\n".join(L) + "\n", encoding="utf-8")

    print(f"  830 entity freshness   {len(out):,} entities   "
          f"{scanned} tables scanned")
    print(f"    in NO Cedar row at all        {len(absent):,}")
    print(f"    no usable date                {len(never) - len(absent):,}")
    print(f"    last change > 1 year ago      {len(old365):,}")
    if aged:
        s = sorted(x["days_since_change"] for x in aged)
        print(f"    median days since change      {s[len(s)//2]:,}"
              f"   p90 {s[int(len(s)*.9)]:,}   max {s[-1]:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
