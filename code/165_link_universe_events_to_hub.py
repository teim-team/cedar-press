#!/usr/bin/env python3
r"""Cedar Press 165 - link `gaming_property_universe_events.csv` to the hub.

THE PROBLEM
-----------
The file is 10 NIGC map-change events (a marker appeared, disappeared, moved or
was renamed). It carries `marker_title`, `marker_address` and a coordinate pair
and **no `facility_id` and no `tribe_id`** - so script 102 counted it against
`facility_id`, found nothing, and has reported `universe_events 0/774 0.0%`
since 2026-08-07 while holding ten real events about ten real properties.

THE ROUTE, AND WHY IT IS NOT A NAME MATCH
-----------------------------------------
`data/clean/gaming_nigc_roster_link.csv` (453 rows, written today by script
157) is a RULED table mapping `nigc_location_name` -> `facility_id` +
`tribe_id` + `link_tier`, built by a six-rung ladder with the name rungs first.
This script joins the event's NIGC marker title to THAT table's NIGC name. It
is an exact join into an existing ruling, not a fresh name match - the same
relationship script 164's `facility_id_exact` rung has to `gaming_facilities`.

`33_apply_party_rulings.resolve_entity` is deliberately NOT called: there is no
name to resolve here, only a ruling to look up.

NORMALISATION - THE APOSTROPHE RULE
-----------------------------------
`King's Club Casino` with U+2019, spaced by OCR or a scrape, normalises to
`king s` and loses an otherwise exact match. The apostrophe class (U+2019,
U+2018, U+0027, U+00B4, U+FFFD) is DELETED, never turned into a space. Every
other punctuation run collapses to one space. Recorded in the 2026-08-26
rebuild as a defect that cost real links.

THE ANACHRONISM RULE
--------------------
`gaming_nigc_roster_link.csv` is the **current** roster, dated 2026-08-26. A
universe event can be a *disappearance* from 2015. Ruling a historical record
against a current roster is the error three gaming rulings were withdrawn for
on 2026-08-06. So:

  * a `renamed` or `moved` event may use EITHER title, because the roster's
    current name is the post-rename one;
  * a `disappeared` event is linked only with `link_anachronism_note` set, and
    it is never read as evidence the property is currently listed;
  * where a title matches nothing, the row goes to review with the title
    quoted. Nothing is snapped to a nearest coordinate - this file HAS
    coordinates, and using them is exactly the 1.2 km carry-over that let
    `Sportman's Bar` claim `4 Bears Casino & Lodge`.

TIER: INHERITED from `gaming_nigc_roster_link.link_tier`, never assigned here.
"""

import csv
import re
import shutil
import sys
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

APOSTROPHES = "\u2019\u2018\u0027\u00b4\u02bc\ufffd\u2032"


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = "".join(c for c in s if c not in APOSTROPHES)   # DELETED, not spaced
    s = re.sub(r"[^0-9a-zA-Z]+", " ", s).lower()
    return re.sub(r"\s+", " ", s).strip()


def read(p):
    p = Path(p)
    if not p.exists():
        return [], []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        r = csv.DictReader(fh)
        return list(r), list(r.fieldnames or [])


def write_atomic(path, fields, rows):
    path = Path(path)
    if path.exists():
        b = path.with_suffix(path.suffix + f".bak_{TODAY}_pre165")
        if not b.exists():
            shutil.copy2(path, b)
    part = path.with_suffix(path.suffix + ".part")
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    part.replace(path)


def main():
    print("=== Cedar Press 165: universe events -> facility hub ===\n")
    ev, evf = read(CLEAN / "gaming_property_universe_events.csv")
    link, _ = read(CLEAN / "gaming_nigc_roster_link.csv")
    if not ev:
        print("no gaming_property_universe_events.csv")
        return 0
    if not link:
        print("no gaming_nigc_roster_link.csv - cannot link without the ruling")
        return 1

    by_name = {}
    ambiguous = set()
    for r in link:
        k = norm(r.get("nigc_location_name"))
        if not k:
            continue
        if k in by_name and by_name[k]["facility_id"] != r["facility_id"]:
            ambiguous.add(k)
        by_name.setdefault(k, r)
    for k in ambiguous:
        by_name.pop(k, None)
    print(f"ruled NIGC names: {len(by_name):,} usable, "
          f"{len(ambiguous)} dropped as ambiguous\n")

    block = ["facility_id", "entity_id", "entity_level", "entity_tier",
             "entity_tier_basis", "entity_link_rung", "link_anachronism_note",
             "entity_link_date"]
    newf = list(evf) + [c for c in block if c not in evf]

    review = []
    rung = Counter()
    for i, r in enumerate(ev):
        for c in block:
            r.setdefault(c, "")
        titles = [(r.get("marker_title") or "", "marker_title"),
                  (r.get("prior_marker_title") or "", "prior_marker_title")]
        hit = None
        which = ""
        for t, w in titles:
            k = norm(t)
            if k and k in by_name:
                hit, which = by_name[k], w
                break
        if hit is None:
            review.append({
                "source_file": "gaming_property_universe_events.csv",
                "event_id": r.get("event_id", ""),
                "event_type": r.get("event_type", ""),
                "marker_title": r.get("marker_title", ""),
                "prior_marker_title": r.get("prior_marker_title", ""),
                "reason": "NO_RULED_NIGC_NAME",
                "evidence": "neither title matches a ruled nigc_location_name "
                            "in gaming_nigc_roster_link.csv. NOT snapped to a "
                            "nearest coordinate: this row carries lat/lon and "
                            "using it is the 1.2 km carry-over defect.",
            })
            rung["unlinked_no_ruled_name"] += 1
            continue
        r["facility_id"] = hit["facility_id"]
        r["entity_id"] = hit.get("tribe_id", "")
        r["entity_level"] = "facility"
        r["entity_tier"] = hit.get("link_tier", "")
        r["entity_tier_basis"] = (
            f"inherited from gaming_nigc_roster_link.link_tier "
            f"(match_basis={hit.get('match_basis','')}) via {which}")
        r["entity_link_rung"] = "ruled_nigc_name_exact"
        r["entity_link_date"] = TODAY
        et = (r.get("event_type") or "").lower()
        if et in ("disappeared", "removed", "delisted", "absent_from_snapshot"):
            r["link_anachronism_note"] = (
                "HISTORICAL EVENT LINKED TO A CURRENT ROSTER. The roster is "
                f"dated {hit.get('nigc_listed_as_of','')} and this event is a "
                "disappearance; the link identifies WHICH property the event "
                "is about and is NOT evidence the property is listed today.")
        rung["ruled_nigc_name_exact"] += 1

    write_atomic(CLEAN / "gaming_property_universe_events.csv", newf, ev)
    print(f"gaming_property_universe_events.csv  {len(ev)} rows")
    for k, v in rung.most_common():
        print(f"   {k:36s} {v:>4}")
    print(f"   event_type: {dict(Counter(r.get('event_type') for r in ev))}")
    print(f"   tiers:      {dict(Counter(r['entity_tier'] for r in ev if r['entity_tier']))}")
    print(f"   anachronism notes written: "
          f"{sum(1 for r in ev if r['link_anachronism_note'])}")

    if review:
        REVIEW.mkdir(exist_ok=True)
        p = REVIEW / f"gaming_universe_events_unlinked_{TODAY}.csv"
        write_atomic(p, list(review[0].keys()), review)
        print(f"\nreview -> {p.name}  {len(review)} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
