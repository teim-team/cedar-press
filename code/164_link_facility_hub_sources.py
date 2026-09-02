#!/usr/bin/env python3
r"""Cedar Press 164 - link the REMAINING facility-hub sources to the entity.

THE MODEL (Elijah, 2026-08-26)
------------------------------
Everything connects to a native entity. **A CASINO IS A HUB**: devices, game
listings, loyalty programmes, employment, OSHA records, websites, promotional
material, capacity and revenue all hang off one facility, and the facility -
not each source - carries the link to the entity. So a source is linked by
joining `facility_id` into `gaming_facilities.csv` and taking THAT ROW's
`tribe_id`. No source re-derives the entity by name.

Script 159 did this for `gaming_facility_metrics.csv` (0% -> 95.9%). This
script does it for everything else that hangs off a facility.

THE TIER IS INHERITED, NEVER ASSIGNED
-------------------------------------
`AGENTS.md`: *"a tier is INHERITED from the source row, never assigned by the
consumer. The exactness of the KEY says nothing about the correctness of the
LINK."* An exact join on `facility_id` is exact; it says nothing about whether
that facility was correctly keyed to its tribe. So every row this script writes
carries `entity_tier` copied verbatim from the facility row, plus
`entity_tier_basis` naming where the tier came from - so a consumer can never
launder a B into an A by joining on an exact key.

**Script 159 filled `entity_id` on the metrics table and recorded the tier only
in its log.** This script adds the missing `entity_tier` column to that file
(and nothing else - `entity_id` is not touched, not recomputed, not re-joined).
A tier that every consumer has to re-derive is the consumer-assigns-the-tier
failure mode with an extra step.

THE RUNGS, IN ORDER. NAME AND ID FIRST; GEOMETRY IS NOT USED AT ALL.
--------------------------------------------------------------------
1. `facility_id_exact`
      The row names a facility; that facility exists in the hub and carries a
      tribe. entity_level = facility. Tier = the facility row's `entity_tier`.

2. `multi_property_host_unanimous_tribe`
      Website rows the crawl could NOT attribute to one property, because the
      host serves several. Script 142 recorded the candidate facility ids in
      `attribution_basis` verbatim - e.g. "multi_property_host: 3 Cedar
      properties resolve to this host (CCP-692800, CCP-570000, CCP-544800)".
      Where every named facility resolves to the SAME tribe, the row is a fact
      about that tribe even though it is not a fact about one property.
      entity_level = **tribe**, never facility - the property ambiguity is real
      and is not resolved by this rung.
      **Tier = the WEAKEST tier among the named facilities.** A rung that could
      not pick a property must not inherit the best evidence in the group.

3. `row_tribe_id_mirror`
      The row legitimately has no facility - a compact authorises a TRIBE, a
      statewide online sportsbook is not a building, a Form 5500 keys to an EIN.
      Its `tribe_id` was set by the source's own build with its own tier, so
      this rung MIRRORS an existing link into the uniform column block. It
      creates no new link and must never be read as one. Tier comes from the
      row's own tier column, blank if the row has none.

Anything that matches no rung goes to `review/` with its evidence. Nothing is
forced.

WHAT THIS SCRIPT DELIBERATELY REFUSES
-------------------------------------
* **No proximity, no coordinates, no nearest-property.** The 2026-08-26 rebuild
  measured what a 1.2 km carry-over costs: `Sportman's Bar` claimed `4 Bears
  Casino & Lodge` and `Firelake Bowling Center` claimed `Thunderbird Casino`,
  and each theft then made the correctly-named row look missing - one error
  producing two wrong answers. This script never looks at a coordinate.

* **No name matching.** Every rung here starts from an id another build already
  wrote. `33_apply_party_rulings.resolve_entity` holds the ONE resolver and this
  script does not need it, because a facility-hub source does not resolve names
  - it inherits a link.

* **`gaming_manufacturer_facts.csv` is NOT facility-linked.** Its own
  `property_attributed` column says, in words, on every row, that a
  manufacturer's installed base is never apportioned to a property
  (`GAMING_DEVICE_BUILD_LOG.md`). Linking it to a facility would contradict the
  column the build wrote to prevent exactly that. It is reported as
  CORRECTLY_UNLINKED, not as a gap.

* **`data/staging/*` is not written.** `gaming_employment_osha_tribe_staged.csv`
  (485 rows) and `gaming_employment_form5500_staged.csv` (2,046) belong to a
  concurrent agent. Both are read-only here and are reported on, not touched.

SAFETY
  * Every file backed up to `.bak_<date>_pre164` before it is rewritten.
  * `.part` then rename - an interruption must not look like a completion.
  * Columns are APPENDED. No column is dropped, renamed or reordered.
  * A `facility_id` that is not in the hub is a DANGLING REFERENCE and goes to
    review; it is never treated as a new property.
"""

import csv
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
LOGS = CEDAR / "logs"
STAGING = CEDAR / "data" / "staging"
TODAY = date.today().isoformat()
SCRIPT = "164_link_facility_hub_sources.py"

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

VALID_TIERS = {"A", "B", "C", "X"}

# The uniform block every facility-hub table gains. Appended, never inserted.
BLOCK = ["entity_id", "entity_level", "entity_tier", "entity_tier_basis",
         "entity_link_rung", "entity_link_date"]

# file, facility column, tribe column (or None), the row's OWN tier column (or
# None), whether a tribe-level mirror is legitimate for this source
TABLES = [
    # ---- capacity / metrics -------------------------------------------------
    # LICENSED (Casino City). Linked for internal join-ability only; the file
    # is in cedar_domain.LICENSED_SOURCE_FILES and 87 refuses it by name.
    ("gaming_property_capacity_history.csv", "facility_id", None, None, False),
    # ---- game listings ------------------------------------------------------
    ("gaming_game_finder_observations.csv", "facility_id", "tribe_id",
     "confidence", False),
    # ---- devices ------------------------------------------------------------
    ("gaming_device_observations.csv", "facility_id", "tribe_id", "tier", True),
    # ---- websites / promotional --------------------------------------------
    ("gaming_property_site_observations.csv", "facility_id", "tribe_id",
     "confidence", False),
    ("gaming_property_labor_demand.csv", "facility_id", "tribe_id",
     "confidence", False),
    # ---- loyalty ------------------------------------------------------------
    ("loyalty_program_property.csv", "facility_id", "tribe_id",
     "confidence_tier", False),
    ("loyalty_programs.csv", None, "tribe_id", "confidence_tier", True),
    # ---- digital ------------------------------------------------------------
    ("digital_gaming_relationships.csv", "facility_id", "tribe_id", "tier",
     True),
    ("digital_gaming_revenue.csv", "facility_id", "tribe_id",
     "confidence_tier", True),
    # ---- employment ---------------------------------------------------------
    ("gaming_employment_observations.csv", "facility_id", "tribe_id", None,
     True),
]

# `confidence` on the website/game-finder tables holds a Tier letter; on the
# employment table it holds high/medium/low, which is NOT a tier. Only letters
# in VALID_TIERS are ever copied into `entity_tier`.


def read(p):
    p = Path(p)
    if not p.exists():
        return [], []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        r = csv.DictReader(fh)
        return list(r), list(r.fieldnames or [])


def write_atomic(path, fields, rows):
    path = Path(path)
    part = path.with_suffix(path.suffix + ".part")
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    part.replace(path)


def backup(path, tag="pre164"):
    path = Path(path)
    if path.exists():
        b = path.with_suffix(path.suffix + f".bak_{TODAY}_{tag}")
        if not b.exists():
            shutil.copy2(path, b)
        return b.name
    return ""


def facility_ids_in(text):
    """Pull Cedar facility ids out of a free-text attribution basis.

    Deliberately literal: the ids were WRITTEN there by script 142, so this is
    reading a record, not inferring one.
    """
    import re
    return re.findall(r"(?:CCP|VP|CEDAR-FAC)-[0-9]+", text or "")


WEAKEST = {"A": 0, "B": 1, "C": 2, "X": 3}


def main():
    print("=== Cedar Press 164: link the facility-hub sources ===\n")
    REVIEW.mkdir(exist_ok=True)
    LOGS.mkdir(exist_ok=True)

    fac, _ = read(CLEAN / "gaming_facilities.csv")
    if not fac:
        print("FATAL: no gaming_facilities.csv")
        return 1
    hub = {}
    for f in fac:
        fid = (f.get("facility_id") or "").strip()
        if not fid:
            continue
        if fid in hub:
            print(f"FATAL: duplicate facility_id in the hub: {fid}")
            return 1
        hub[fid] = f
    print(f"hub: {len(hub):,} facilities, "
          f"{sum(1 for f in hub.values() if (f.get('tribe_id') or '').strip()):,}"
          f" carry a tribe\n")

    tribeless = {fid for fid, f in hub.items()
                 if not (f.get("tribe_id") or "").strip()}

    review = []
    summary = []
    blocked_by_tribeless = Counter()
    blocked_detail = Counter()
    blank_tier_mirror = Counter()
    # facility -> set of source labels, for the source-stack count
    stack = defaultdict(set)

    for fname, fcol, tcol, tiercol, allow_mirror in TABLES:
        path = CLEAN / fname
        rows, fields = read(path)
        if not rows:
            print(f"  {fname:44s} ABSENT")
            continue

        before = sum(1 for r in rows if (r.get("entity_id") or "").strip())
        newfields = list(fields)
        for c in BLOCK:
            if c not in newfields:
                newfields.append(c)

        rung = Counter()
        tiers = Counter()
        for i, r in enumerate(rows):
            for c in BLOCK:
                r.setdefault(c, "")
            fid = (r.get(fcol) or "").strip() if fcol else ""
            tid = (r.get(tcol) or "").strip() if tcol else ""
            basis = r.get("attribution_basis") or ""
            own_tier = (r.get(tiercol) or "").strip().upper() if tiercol else ""
            if own_tier not in VALID_TIERS:
                own_tier = ""

            # ---- the source's own negative ruling wins over every rung ---
            # `is_tribe_attributable = no` is script 119 stating, per row, that
            # this licensee is NOT a Native entity - CT Lottery Corp, MGM Grand
            # Detroit, MotorCity, Greektown, the AZ operator brands. Those rows
            # are CORRECT as they stand. Sending them to review would file 2,849
            # right answers as open questions, and a review queue that is mostly
            # correct rows is a queue nobody reads.
            if (r.get("is_tribe_attributable") or "").strip().lower() == "no":
                r["entity_link_rung"] = "not_tribe_attributable_by_source"
                r["entity_tier_basis"] = (
                    "the source states this licensee is not a Native entity: "
                    + (r.get("attribution_basis") or "")[:200])
                r["entity_link_date"] = TODAY
                rung["correctly_unlinked_not_tribe_attributable"] += 1
                continue

            # ---- rung 1: exact facility id ------------------------------
            if fid:
                f = hub.get(fid)
                if f is None:
                    review.append({
                        "source_file": fname, "row_index": i,
                        "facility_id": fid, "tribe_id": tid,
                        "reason": "DANGLING_FACILITY_ID",
                        "evidence": "facility_id is not present in "
                                    "gaming_facilities.csv; not minted as a "
                                    "new property",
                    })
                    rung["unlinked_dangling_facility_id"] += 1
                    continue
                ftribe = (f.get("tribe_id") or "").strip()
                if not ftribe:
                    # NOT one review row per affected record. 1,736 vendor
                    # capacity rows on one unkeyed hub row is ONE question
                    # asked 1,736 times, and a queue of 1,736 identical cards
                    # is a queue nobody reads. Aggregated below, per facility.
                    blocked_by_tribeless[fid] += 1
                    blocked_detail[(fname, fid)] += 1
                    rung["unlinked_hub_row_has_no_entity"] += 1
                    continue
                r["entity_id"] = ftribe
                r["entity_level"] = "facility"
                r["entity_tier"] = (f.get("entity_tier") or "").strip()
                r["entity_tier_basis"] = (
                    f"inherited from gaming_facilities.{fid}.entity_tier "
                    f"(method={f.get('entity_match_method','') or 'none'})")
                r["entity_link_rung"] = "facility_id_exact"
                r["entity_link_date"] = TODAY
                rung["facility_id_exact"] += 1
                tiers[r["entity_tier"] or "(blank)"] += 1
                stack[fid].add(fname)
                continue

            # ---- rung 2: multi-property host, unanimous tribe -----------
            cands = facility_ids_in(basis) if basis.startswith(
                "multi_property_host") else []
            if len(cands) >= 2:
                known = [hub[c] for c in cands if c in hub]
                trs = {(k.get("tribe_id") or "").strip() for k in known}
                trs.discard("")
                if len(known) == len(cands) and len(trs) == 1:
                    ts = [(k.get("entity_tier") or "").strip() for k in known]
                    weakest = max(ts, key=lambda t: WEAKEST.get(t, 9))
                    r["entity_id"] = next(iter(trs))
                    r["entity_level"] = "tribe"
                    r["entity_tier"] = weakest
                    r["entity_tier_basis"] = (
                        "WEAKEST of the tiers on the candidate facilities "
                        + ",".join(f"{c}={t}" for c, t in zip(cands, ts))
                        + " - the rung could not pick a property and must not "
                          "inherit the best evidence in the group")
                    r["entity_link_rung"] = "multi_property_host_unanimous_tribe"
                    r["entity_link_date"] = TODAY
                    rung["multi_property_host_unanimous_tribe"] += 1
                    tiers[weakest or "(blank)"] += 1
                    continue
                review.append({
                    "source_file": fname, "row_index": i, "facility_id": "",
                    "tribe_id": tid, "reason": "MULTI_HOST_TRIBE_NOT_UNANIMOUS",
                    "evidence": basis[:400],
                })
                rung["unlinked_multi_host_not_unanimous"] += 1
                continue

            # ---- rung 3: mirror an existing tribe-level link ------------
            if tid and allow_mirror:
                r["entity_id"] = tid
                r["entity_level"] = "tribe"
                r["entity_tier"] = own_tier
                r["entity_tier_basis"] = (
                    f"mirrored from this row's own {tiercol}"
                    if own_tier else
                    f"NOT INHERITED - the source row carries no tier "
                    f"({tiercol or 'no tier column'}); needs a ruling")
                r["entity_link_rung"] = "row_tribe_id_mirror"
                r["entity_link_date"] = TODAY
                rung["row_tribe_id_mirror"] += 1
                tiers[own_tier or "(blank)"] += 1
                if not own_tier:
                    blank_tier_mirror[fname] += 1
                continue

            if tid and not allow_mirror:
                review.append({
                    "source_file": fname, "row_index": i, "facility_id": "",
                    "tribe_id": tid, "reason": "TRIBE_ID_WITHOUT_FACILITY",
                    "evidence": "this source is property-level by design; a "
                                "tribe-level mirror is not authorised for it. "
                                + basis[:300],
                })
                rung["unlinked_tribe_only_not_authorised"] += 1
                continue

            review.append({
                "source_file": fname, "row_index": i, "facility_id": "",
                "tribe_id": "", "reason": "NO_FACILITY_AND_NO_TRIBE",
                "evidence": basis[:400] or "(no attribution_basis on this row)",
            })
            rung["unlinked_no_facility_no_tribe"] += 1

        after = sum(1 for r in rows if (r.get("entity_id") or "").strip())
        backup(path)
        write_atomic(path, newfields, rows)
        print(f"  {fname:44s} {len(rows):>7,} rows   "
              f"entity_id {before:,} -> {after:,} "
              f"({after * 100.0 / len(rows):.1f}%)")
        for k, v in rung.most_common():
            print(f"      {k:44s} {v:>7,}")
        print(f"      tiers: {dict(tiers)}")
        summary.append({
            "source_file": fname, "rows": len(rows),
            "entity_id_before": before, "entity_id_after": after,
            "pct_after": round(after * 100.0 / len(rows), 1),
            **{f"rung_{k}": v for k, v in rung.items()},
        })

    # ------------------------------------------------------------------
    # metrics: add the MISSING tier column only. entity_id is NOT touched.
    # ------------------------------------------------------------------
    print("\n-- gaming_facility_metrics.csv: adding the inherited tier "
          "(entity_id untouched) --")
    mpath = CLEAN / "gaming_facility_metrics.csv"
    # IDEMPOTENCY FIX 2026-08-26 (172): this branch used to `continue` the
    # moment `entity_tier` existed, which meant a SECOND run of 164 skipped the
    # metrics table entirely - and the metrics table is the largest
    # facility-level source, so `stack` lost one source per facility and
    # `logs/164_facility_source_stack_<date>.csv` was REWRITTEN, on the second
    # run, with 187 facilities reading "0 sources" that hold thousands of
    # metric rows each. A re-run that degrades a published log is not
    # idempotent. The recompute now always happens; the column-add is what is
    # conditional. `entity_id` is still never touched here - 159 owns it.
    mrows, mfields = read(mpath)
    if mrows:
        had_tier = "entity_tier" in mfields
        mnew = list(mfields)
        for c in ("entity_tier", "entity_tier_basis"):
            if c not in mnew:
                mnew.append(c)
        t = Counter()
        changed = 0
        for r in mrows:
            eid = (r.get("entity_id") or "").strip()
            fid = (r.get("facility_id") or "").strip()
            f = hub.get(fid)
            before_tier = (r.get("entity_tier") or "")
            if eid and f and (f.get("tribe_id") or "").strip() == eid:
                r["entity_tier"] = (f.get("entity_tier") or "").strip()
                r["entity_tier_basis"] = (
                    f"inherited from gaming_facilities.{fid}.entity_tier")
                t[r["entity_tier"] or "(blank)"] += 1
            else:
                r["entity_tier"] = ""
                r["entity_tier_basis"] = (
                    "NOT INHERITED - no facility row confirms this "
                    "entity_id" if eid else "")
                t["(no entity_id)" if not eid else "(unconfirmed)"] += 1
            if r["entity_tier"] != before_tier:
                changed += 1
            if fid and eid:
                stack[fid].add("gaming_facility_metrics.csv")
        backup(mpath)
        write_atomic(mpath, mnew, mrows)
        print(f"   {len(mrows):,} rows, tiers {dict(t)}"
              f" | column {'already present' if had_tier else 'ADDED'},"
              f" {changed:,} tier cell(s) changed")

    # ------------------------------------------------------------------
    # review
    # ------------------------------------------------------------------
    # the tribeless hub rows are the highest-leverage item: one unkeyed
    # facility blocks every source hanging off it.
    for fid, n in blocked_by_tribeless.most_common():
        f = hub[fid]
        detail = "; ".join(
            f"{sf}={c:,}" for (sf, ff), c in sorted(blocked_detail.items())
            if ff == fid)
        review.append({
            "source_file": "gaming_facilities.csv", "row_index": "",
            "facility_id": fid, "tribe_id": "",
            "reason": "HUB_FACILITY_UNKEYED_BLOCKS_DOWNSTREAM",
            "evidence": f"{f.get('facility_name','')} ({f.get('state','')}) "
                        f"carries no tribe_id and blocks {n:,} downstream "
                        f"source rows from reaching an entity ({detail}). "
                        f"Keying this ONE hub row links all of them. NOTE the "
                        f"record's own dates before ruling it against a "
                        f"current roster - property_status="
                        f"{f.get('property_status','') or '(blank)'}, "
                        f"close_date={f.get('close_date','') or '(none)'}.",
        })
    # the four unkeyed hub rows that block nothing today still block everything
    # tomorrow, so they are queued too rather than left invisible.
    for fid in sorted(tribeless - set(blocked_by_tribeless)):
        f = hub[fid]
        review.append({
            "source_file": "gaming_facilities.csv", "row_index": "",
            "facility_id": fid, "tribe_id": "",
            "reason": "HUB_FACILITY_UNKEYED_NO_SOURCES_YET",
            "evidence": f"{f.get('facility_name','')} ({f.get('state','')}) "
                        f"carries no tribe_id. No facility-hub source hangs off "
                        f"it today, so nothing is blocked yet - but any source "
                        f"that arrives for it will be unlinkable.",
        })
    for fname, n in blank_tier_mirror.most_common():
        review.append({
            "source_file": fname, "row_index": "", "facility_id": "",
            "tribe_id": "", "reason": "MIRRORED_LINK_CARRIES_NO_TIER",
            "evidence": f"{n:,} rows carry a tribe_id whose source row records "
                        f"no confidence tier, so entity_tier could not be "
                        f"INHERITED and was left blank rather than assigned. "
                        f"These rows are entity-linked and un-tiered: they must "
                        f"not be read as tier A. Needs a ruling on what tier "
                        f"this build's own linkage earns.",
        })

    rpath = REVIEW / f"gaming_facility_hub_unlinked_{TODAY}.csv"
    rf = ["source_file", "row_index", "facility_id", "tribe_id", "reason",
          "evidence"]
    write_atomic(rpath, rf, review)
    print(f"\nreview -> {rpath.name}  {len(review):,} rows")
    for k, v in Counter(x["reason"] for x in review).most_common():
        print(f"   {k:44s} {v:>7,}")

    # ------------------------------------------------------------------
    # the source stack
    # ------------------------------------------------------------------
    spath = LOGS / f"164_facility_source_stack_{TODAY}.csv"
    srows = []
    for fid, f in hub.items():
        srows.append({
            "facility_id": fid,
            "facility_name": f.get("facility_name", ""),
            "state": f.get("state", ""),
            "entity_id": (f.get("tribe_id") or "").strip(),
            "entity_tier": (f.get("entity_tier") or "").strip(),
            "n_hub_sources_linked": len(stack[fid]),
            "hub_sources_linked": "|".join(sorted(stack[fid])),
        })
    write_atomic(spath, list(srows[0].keys()), srows)
    dist = Counter(r["n_hub_sources_linked"] for r in srows)
    print(f"\nsource stack per facility -> logs/{spath.name}")
    for k in sorted(dist):
        print(f"   {k} source(s): {dist[k]:,} facilities")

    # ------------------------------------------------------------------
    # things deliberately NOT linked, stated rather than omitted
    # ------------------------------------------------------------------
    print("\nCORRECTLY UNLINKED - stated, not silently omitted:")
    mf, _ = read(CLEAN / "gaming_manufacturer_facts.csv")
    print(f"   gaming_manufacturer_facts.csv         {len(mf):>7,} rows - "
          "manufacturer-level. Its own `property_attributed` column forbids "
          "apportioning to a property.")
    dr, _ = read(CLEAN / "digital_gaming_revenue.csv")
    na = [r for r in dr if (r.get("is_tribe_attributable") or "") == "no"]
    print(f"   digital_gaming_revenue.csv            {len(na):>7,} rows - "
          "is_tribe_attributable = no (CT Lottery, MGM Grand Detroit, "
          "MotorCity, Greektown, AZ operator brands). NOT a linkage gap.")
    # lint-ok: class1 - these two ARE staging files and are read only to COUNT
    # and NAME them as unpromoted. No promoted table exists for them yet; that
    # is the point of printing them.
    for f in ("gaming_employment_osha_tribe_staged.csv",
              "gaming_employment_form5500_staged.csv"):
        rows, _ = read(STAGING / f)
        print(f"   data/staging/{f:38s} {len(rows):>7,} rows - another "
              "agent's staging file, read-only here.")

    lpath = LOGS / f"164_linkage_summary_{TODAY}.csv"
    keys = sorted({k for s in summary for k in s})
    write_atomic(lpath, keys, summary)
    print(f"\nsummary -> logs/{lpath.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
