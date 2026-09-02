#!/usr/bin/env python3
"""
Cedar Press - 830: WHEN WAS EACH ENTITY LAST TOUCHED BY ANYTHING?

    py -3 code/830_entity_freshness.py            # measure + write
    py -3 code/830_entity_freshness.py verify     # exit 1 if the ledger is stale
                                                  # or credits a build stamp

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
#
# THIRD OCCURRENCE, 2026-09-02. The list above still missed the biggest one:
# `entity_aliases.created_at` won for 1,126 of 1,555 entities and holds three
# values - 2026-08-07 (5,942 rows), 2026-08-26 (354), 2026-09-01 (2) - which
# are Cedar build dates, not alias dates. That row's own `alias_layer_basis`
# says so in prose: "They are deliberately NOT filled with the build date."
# The ledger then read median 26 days, p90 26, and ZERO entities untouched for
# a year, which is the same worthless mirror the first two versions produced.
#
# Names added here, each measured before it was added (distinct values in the
# column, and what they are):
#   created_at                      3   Cedar build dates
#   classified_date                     Cedar classified the deal
#   entity_link_date                1   2026-08-26 on all 11 tables that hold it
#   ruling_applied_date / ruling_date   Cedar adjudicated; `ruled` did not match
#                                       `ruling`, which is why it slipped
#   attributed_date                 1   2026-08-06
#   attribution_repair/withdrawn_date   Cedar repaired or withdrew
#   *_withdrawn_date                    Cedar withdrew a link
#   recorded_date / rederived_date      Cedar recorded / re-derived
#   verified_date                       Cedar verified; `reviewed` did not match
#   Date_Added                          `_date_added` required a leading
#                                       underscore and never matched `Date_Added`
#   expanded_date, ocr_date,            Cedar expanded / OCR'd / built
#   temporal_build_date
#   native_ownership_evidence_date  3   Cedar build dates, not document dates
#   snapshot                            Cedar's snapshot boundary
#
# DELIBERATELY KEPT, because they are the SOURCE changing and not us:
#   index_post_date  (174 distinct, 2024-2025 - when NIGC posted the document)
#   source_last_updated (7 distinct, real publisher dates)
#   cedar_open_date  (39 distinct - when a PROPERTY opened, a fact about the
#                     entity that Cedar merely records)
#   fac_accepted_date, publication_date, action_date, filed/filing/effective
#
# A blacklist of names is why this defect has now recurred three times, so the
# names are no longer the only defence - see BUILD_STAMP below.
NEVER = re.compile(
    r"built|fetched|harvest|retrieved|measured|checked|keyed|stamped|"
    r"ingest|parsed|scraped|crawl|_run|load|refresh|generated|written|"
    r"assert|observ|rul(ed|ing)|adjudicat|resolv|minted|promoted|reviewed|"
    r"first_seen|last_seen|date_added|"
    r"creat|classif|entity_link|attributed_date|attribution_repair|"
    r"withdrawn|recorded|rederiv|verif|expanded_date|ocr_|temporal_build|"
    r"ownership_evidence|snapshot")

# A DATE COLUMN THAT HOLDS ALMOST NO DISTINCT VALUES IS A BUILD STAMP.
#
# The name-based defence has now failed three times, always on a name nobody
# thought of. This is the shape-based one, and it does not care what the column
# is called: if a column supplies the newest date for at least BUILD_STAMP_MIN
# of the register AND those dates take at most BUILD_STAMP_DISTINCT values,
# every entity it "freshened" was freshened on the same day, which is what a
# build does and is not what an entity does.
#
# Measured against the live tree: it refuses `entity_aliases.created_at`
# (1,126 entities, 3 values) and nothing legitimate - `action_date`,
# `publication_date` and `index_post_date` all carry hundreds of distinct
# values across the entities they win for.
#
# Refused columns are REPORTED, never silently dropped. Flag, never delete.
BUILD_STAMP_MIN = 0.05          # of the register
BUILD_STAMP_DISTINCT = 3
DATEY = re.compile(r"date|year|period|_at$|_on$|expir|vintage|updated|"
                   r"filed|published|effective|start|end|close|open")
ISO = re.compile(r"^(19|20)\d\d-\d\d(-\d\d)?")
YEAR = re.compile(r"^(19|20)\d\d$")
RANGE = re.compile(r"^((?:19|20)\d\d)[-/]((?:19|20)\d\d)$")


def parse(v: str):
    v = (v or "").strip()
    if not v:
        return None
    # A YEAR RANGE IS NOT A DATE. `bie_uio_identifier_links.fiscal_years`
    # holds "2001-2007", which the ISO pattern below read as year 2001 month
    # 20, and the ledger then published `2001-2001-01` as five BIE schools'
    # last change. Take the LATER year, which is the period the row covers.
    m = RANGE.match(v)
    if m:
        y = int(m.group(2))
        return f"{y}-12-31" if 1800 <= y <= TODAY.year + 2 else None
    if ISO.match(v):
        d = v[:10] if len(v) >= 10 else v + "-01"
        try:                       # month 20 is not a month. Validate, do not
            date(*(int(x) for x in d.split("-")))   # trust the pattern.
        except (ValueError, TypeError):
            return None
        return d
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


def resolve(cand: dict, n_register: int):
    """Pick each entity's newest date, refusing build stamps as they surface.

    Iterative, because refusing one column promotes whatever was second, and
    the promoted column can be a build stamp too. Terminates: every round
    either refuses at least one column or stops.

    Returns (uid -> (date, table, col), [refusal dicts]).
    """
    refused_keys: set = set()
    refused: list = []
    floor = max(1, int(n_register * BUILD_STAMP_MIN))
    while True:
        win: dict = {}
        for uid, cols in cand.items():
            best = ("", "", "")
            for (tbl, col), d in cols.items():
                if (tbl, col) in refused_keys:
                    continue
                if d > best[0]:
                    best = (d, tbl, col)
            if best[0]:
                win[uid] = best
        by_col: dict = defaultdict(set)          # (tbl, col) -> distinct dates
        n_col: dict = defaultdict(int)
        for d, tbl, col in win.values():
            by_col[(tbl, col)].add(d)
            n_col[(tbl, col)] += 1
        newly = [(k, n_col[k], sorted(by_col[k]))
                 for k in by_col
                 if n_col[k] >= floor and len(by_col[k]) <= BUILD_STAMP_DISTINCT]
        if not newly:
            return win, refused
        for k, n, dates in newly:
            refused_keys.add(k)
            refused.append({"table": k[0], "column": k[1], "entities": n,
                            "distinct_dates": len(dates), "values": dates})


def main() -> int:
    verify = len(sys.argv) > 1 and sys.argv[1] == "verify"

    reg = list(csv.DictReader(REG.open(encoding="utf-8-sig", errors="replace")))
    known = {r["cedar_uid"]: r for r in reg if r.get("cedar_uid")}
    by_handle = {r["handle"]: r["cedar_uid"] for r in reg if r.get("handle")}

    # uid -> {(table, col): newest date that column offers for this entity}
    cand: dict = defaultdict(dict)
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
                    cu = cand[uid]
                    for c in dcols:
                        d = parse(r.get(c))
                        d = cap(d) if d else None
                        if d:
                            k = (p.name, c)
                            if d > cu.get(k, ""):
                                cu[k] = d
        except OSError:
            continue

    last, refused = resolve(cand, len(known))

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
        if refused:
            L += ["## Columns REFUSED as build stamps", "",
                  f"*A date column that supplies the newest date for "
                  f"{BUILD_STAMP_MIN:.0%}+ of the register while holding at most "
                  f"{BUILD_STAMP_DISTINCT} distinct values freshened every one "
                  f"of those entities on the same day. That is what a build "
                  f"does. Refused and named here rather than silently dropped — "
                  f"if one of these is genuinely an entity date, say so and it "
                  f"comes back.*", "",
                  "| table | column | would have won for | distinct values |",
                  "|---|---|---:|---|"]
            for x in refused:
                L.append(f"| `{x['table']}` | `{x['column']}` | "
                         f"{x['entities']:,} | {', '.join(x['values'])} |")
            L.append("")
        if aged:
            s = sorted(x["days_since_change"] for x in aged)
            L += [f"Median days since last change: **{s[len(s)//2]:,}**. "
                  f"p90: **{s[int(len(s)*.9)]:,}**. Oldest: **{s[-1]:,}**.", "",
                  "## The tail — 25 entities nobody has touched longest", "",
                  "| entity | class | last change | days | where |",
                  "|---|---|---|---:|---|"]
            for x in [y for y in out if y["last_change"]][:25]:
                age = x['days_since_change']
                age = f"{age:,}" if isinstance(age, int) else "unparseable"
                L.append(f"| {x['canonical_name'][:34]} | "
                         f"{x['entity_class'][:26]} | {x['last_change']} | "
                         f"{age} | "
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
    for x in refused:
        print(f"    REFUSED as a build stamp      {x['table']}::{x['column']}"
              f"   would have won for {x['entities']:,} entities on "
              f"{x['distinct_dates']} distinct date(s)")

    # `verify` is a GATE, not a dry run. It used to print and return 0, which
    # is the docstring promising something the code never did.
    if verify:
        bad = []
        if not OUT.exists():
            bad.append(f"{OUT.name} has never been written")
        else:
            live = max((p.stat().st_mtime for p in tables), default=0)
            if OUT.stat().st_mtime < live:
                bad.append(f"{OUT.name} is older than the newest "
                           f"entity-bearing table it claims to measure")
            with OUT.open(encoding="utf-8-sig", errors="replace") as fh:
                held = {(r["last_change_table"], r["last_change_column"])
                        for r in csv.DictReader(fh) if r.get("last_change_table")}
            for x in refused:
                if (x["table"], x["column"]) in held:
                    bad.append(f"the shipped ledger still credits "
                               f"{x['table']}::{x['column']}, refused here as a "
                               f"build stamp ({x['distinct_dates']} distinct "
                               f"value(s) across {x['entities']:,} entities)")
        for b in bad:
            print("  FAIL " + b)
        print(f"  830 verify   {'FAIL' if bad else 'ok'}   {len(bad)} problem(s)")
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
