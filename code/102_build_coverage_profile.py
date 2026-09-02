#!/usr/bin/env python3
"""
Cedar Press - 102: How partial is it? Per property, per field, per source.

ELIJAH, 2026-08-07
------------------
"even if we have partial coverage on some fields i want to see how partial it
 is because its still valuable, thats the point"

Exactly. A field that is 30% filled is valuable WHEN THE 30% IS STATED. It is
only dangerous when a subscriber assumes 100% and it is 30%.

This is the same discipline as documenting oddities: never filter a gap out
silently, measure it and publish the measurement. A coverage profile turns
"incomplete" from an apology into a specification.

TWO OUTPUTS, TWO AUDIENCES
--------------------------
1. `gaming_property_coverage.csv` - one row per property, one column per
   source. Answers "what do we actually know about THIS casino?" A subscriber
   sorts by it; we point new sources at the properties they can enrich.

2. `gaming_field_coverage.csv` - one row per field. Answers "how partial is
   this column?" This is what goes in the codebook and the notes PDF, so a
   number is never read as complete when it is not.

THE RULE THIS ENFORCES
----------------------
When a new source arrives the question is "WHICH EXISTING RECORDS CAN THIS
ENRICH?" - never "can this become another dataset?" The per-property profile
makes that question answerable in one sort.

Writes data/clean/gaming_property_coverage.csv
       data/clean/gaming_field_coverage.csv
"""

import csv
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


def read(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def write_atomic(path, fields, rows):
    """Back up what is overwritten, then `.part` and rename.

    Added 2026-08-26. Both outputs of this script have their counts asserted in
    docs, and START_HERE's own rule is that an interruption must not look like
    a completion. This script wrote straight to the final name.
    """
    import shutil
    path = Path(path)
    if path.exists():
        b = path.with_suffix(path.suffix + f".bak_{TODAY}_pre164")
        if not b.exists():
            shutil.copy2(path, b)
    part = path.with_suffix(path.suffix + ".part")
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    part.replace(path)


# source file, label, the column that names a facility, and whether it is a
# LICENSED source (counted for internal QA, never a publishable coverage claim)
SOURCES = [
    ("gaming_capacity_official.csv", "official_capacity", "facility_id", False),
    ("gaming_property_capacity_history.csv", "vendor_capacity", "facility_id", True),
    ("nigc_region_assignments.csv", "nigc_region", "facility_id", False),
    ("gaming_property_federal_traces.csv", "federal_traces", "facility_id", False),
    ("gaming_employment_lodes.csv", "lodes_employment", "facility_id", False),
    ("gaming_employment_observations.csv", "employment_other", "facility_id", False),
    ("facility_block_geocode.csv", "block_geocode", "facility_id", False),
    ("gaming_property_universe_events.csv", "universe_events", "facility_id", False),
    # --- added 2026-08-26 by script 164 -------------------------------------
    # A CASINO IS A HUB. Six more source families hang off `facility_id` and
    # were never counted here, so a property with a crawled website, a slot
    # finder, a loyalty programme and a device observation read as "THIN - 1
    # source". The coverage profile measured eight of fourteen hub sources and
    # reported the answer as if it were all of them.
    ("gaming_game_finder_observations.csv", "game_finder", "facility_id", False),
    ("gaming_property_site_observations.csv", "website", "facility_id", False),
    ("gaming_property_labor_demand.csv", "website_labor_demand", "facility_id", False),
    ("gaming_device_observations.csv", "device_observation", "facility_id", False),
    ("loyalty_program_property.csv", "loyalty_program", "facility_id", False),
    # --- added 2026-08-26 by script 337 -------------------------------------
    # A REVENUE BOUND IS A FACT ABOUT A PROPERTY and this profile never counted
    # it. 13,645 of 13,803 rows carry a `facility_id`, resolving to 694
    # properties - more properties than any other single source in this list
    # touches. Its absence understated `n_publishable_sources` on every one of
    # them, which is what drives the `evidence_strength` banding, so casinos
    # with a published revenue bound were being reported as THIN.
    # The table keys its PERIOD on `fiscal_year` (a bare year, no day - see
    # code/cedar_period_columns.py), which is why a generic date scan never
    # saw it either.
    ("gaming_revenue_bounds.csv", "revenue_bound", "facility_id", False),
    # LICENSED: the FILE is in cedar_domain.LICENSED_SOURCE_FILES and 87
    # refuses it by name, so it is counted for internal QA only - even though
    # 4,030 of its rows are now from free regulator sources (CT DCP monthly).
    # Marking the file licensed is the conservative reading of a mixed file.
    ("gaming_facility_metrics.csv", "vendor_metrics", "facility_id", True),
]

# these attach to the TRIBE, not the facility
TRIBE_SOURCES = [
    ("compacts.csv", "compact", "tribe_id"),
    ("compact_structured_terms.csv", "compact_terms", "tribe_id"),
    ("gaming_land_decisions.csv", "land_decision", "tribe_id"),
    # `tribe_id` DOES NOT EXIST in either of these two files - both key the
    # entity as `tribe_entity_id`. `DictReader.get("tribe_id")` returns None on
    # every row, so both sources reported **0 tribes covered** from 2026-08-07
    # until 2026-08-26 while holding 307 and 274 keyed rows respectively. A
    # column name that is absent reads exactly like a source that is empty, and
    # nothing in the script distinguished them. Fixed 2026-08-26 by script 164.
    ("nigc_declination_letters.csv", "declination_letter", "tribe_entity_id"),
    ("gaming_financing_events.csv", "financing", "tribe_entity_id"),
    ("gaming_source_claims.csv", "source_claims", "subject_entity_id"),
    # --- added 2026-08-26 by script 164 -------------------------------------
    # Digital gaming is authorised to a TRIBE and an online sportsbook is not a
    # building, so these are tribe-level by construction and must never be
    # attached to one property. Same discipline as `compact`.
    ("digital_gaming_relationships.csv", "digital_gaming", "tribe_id"),
    ("digital_gaming_revenue.csv", "digital_revenue", "tribe_id"),
]


def main():
    print("=== Cedar Press 102: coverage profile ===\n")
    fac = read(CLEAN / "gaming_facilities.csv")
    if not fac:
        print("no gaming_facilities.csv")
        return
    print(f"properties: {len(fac):,}")

    by_fac = defaultdict(Counter)
    licensed = set()
    for fname, label, col, is_lic in SOURCES:
        rows = read(CLEAN / fname)
        if not rows:
            print(f"  {label:22s} (absent)")
            continue
        if col not in rows[0]:
            # A NAMED COLUMN THAT IS ABSENT IS NOT AN EMPTY SOURCE. This is the
            # defect that hid 307 declination letters and 274 financing events
            # for 19 days. Fail loudly rather than reporting 0.0%.
            print(f"  {label:22s} !! FATAL: column '{col}' is not in {fname} "
                  f"(has: {', '.join(list(rows[0])[:8])} ...)")
            raise SystemExit(1)
        if is_lic:
            licensed.add(label)
        n = 0
        for r in rows:
            fid = (r.get(col) or "").strip()
            if fid:
                by_fac[fid][label] += 1
                n += 1
        print(f"  {label:22s} {len(rows):>7,} rows -> "
              f"{len({(r.get(col) or '').strip() for r in rows if r.get(col)}):>4} properties"
              f"{'   [LICENSED - internal QA only]' if is_lic else ''}")

    by_tribe = defaultdict(Counter)
    for fname, label, col in TRIBE_SOURCES:
        rows = read(CLEAN / fname)
        if not rows:
            print(f"  {label:22s} (absent)")
            continue
        if col not in rows[0]:
            print(f"  {label:22s} !! FATAL: column '{col}' is not in {fname} "
                  f"(has: {', '.join(list(rows[0])[:8])} ...)")
            raise SystemExit(1)
        for r in rows:
            t = (r.get(col) or "").strip()
            if t:
                by_tribe[t][label] += 1
        print(f"  {label:22s} {len(rows):>7,} rows -> "
              f"{len({(r.get(col) or '').strip() for r in rows if r.get(col)}):>4} tribes")

    labels = [l for _, l, _, _ in SOURCES] + [l for _, l, _ in TRIBE_SOURCES]

    out = []
    for f in fac:
        fid = f["facility_id"]
        tid = (f.get("tribe_id") or "").strip()
        row = {
            "facility_id": fid,
            "facility_name": f.get("facility_name", ""),
            "tribe_id": tid,
            "entity": f.get("tribe_canonical_name", ""),
            "state": f.get("state", ""),
            "property_status": f.get("property_status", ""),
            # the hub's own link to the entity, carried onto the coverage row
            # so a coverage question and an attribution question are answered
            # from the same table. The TIER IS INHERITED from the facility row
            # and is never recomputed here.
            "entity_id": tid,
            # THE HUB KEY, carried from the facility row. Added 2026-09-01
            # (INT-2) because this rebuild was a silent column-dropper:
            # `gaming_property_coverage.csv` held `cedar_uid` populated and
            # this writer's field list did not, so every run erased it and
            # `62`'s `files_with_columns_lost_vs_backup` caught it. C4
            # attachment is measured on `cedar_uid`. Inherited, like the tier,
            # never recomputed here.
            "cedar_uid": (f.get("cedar_uid") or "").strip(),
            "entity_tier": (f.get("entity_tier") or "").strip(),
            "entity_tier_basis": (
                f"inherited from gaming_facilities.{fid}.entity_tier"
                if tid else "no entity on the hub row"),
        }
        pub = 0
        for _, label, _, is_lic in SOURCES:
            c = by_fac[fid][label]
            row[f"n_{label}"] = c
            if c and not is_lic:
                pub += 1
        for _, label, _ in TRIBE_SOURCES:
            c = by_tribe[tid][label] if tid else 0
            row[f"n_{label}"] = c
            if c:
                pub += 1
        row["n_publishable_sources"] = pub
        row["n_licensed_sources"] = sum(
            1 for _, l, _, il in SOURCES if il and by_fac[fid][l])
        row["evidence_strength"] = (
            "STRONG - 4+ independent sources" if pub >= 4 else
            "MODERATE - 2-3 sources" if pub >= 2 else
            "THIN - 1 source" if pub == 1 else
            "NONE - no publishable source")
        row["built_date"] = TODAY
        out.append(row)

    p = CLEAN / "gaming_property_coverage.csv"
    write_atomic(p, list(out[0].keys()), out)
    print(f"\n  wrote {p.relative_to(CEDAR)}")

    dist = Counter(r["evidence_strength"] for r in out)
    for k in ("STRONG - 4+ independent sources", "MODERATE - 2-3 sources",
              "THIN - 1 source", "NONE - no publishable source"):
        n = dist[k]
        print(f"     {n:>4} ({n/len(out)*100:>5.1f}%)  {k}")

    print("\n  per-source property coverage:")
    rows_field = []
    for label in labels:
        n = sum(1 for r in out if r.get(f"n_{label}", 0))
        rows_field.append({
            "field_or_source": label,
            "properties_covered": n,
            "properties_total": len(out),
            "pct_covered": round(n / len(out) * 100, 1),
            "licensed_internal_only": int(label in licensed),
            "note": ("LICENSED - validates internally, never publishes"
                     if label in licensed else ""),
            "built_date": TODAY,
        })
        bar = "#" * int(n / len(out) * 30)
        print(f"     {label:22s} {n:>4}/{len(out)} {n/len(out)*100:>5.1f}%  {bar}"
              f"{'  [LICENSED]' if label in licensed else ''}")

    # ---- field-level fill inside the flagship files ---------------------
    for fname in ("gaming_properties.csv", "gaming_capacity_official.csv"):
        rows = read(CLEAN / fname)
        if not rows:
            continue
        for col in rows[0]:
            filled = sum(1 for r in rows if (r.get(col) or "").strip())
            rows_field.append({
                "field_or_source": f"{fname}::{col}",
                "properties_covered": filled,
                "properties_total": len(rows),
                "pct_covered": round(filled / len(rows) * 100, 1),
                "licensed_internal_only": 0,
                "note": "",
                "built_date": TODAY,
            })

    p2 = CLEAN / "gaming_field_coverage.csv"
    write_atomic(p2, list(rows_field[0].keys()), rows_field)
    print(f"\n  wrote {p2.relative_to(CEDAR)}  ({len(rows_field)} fields measured)")

    thin = [r for r in out if r["n_publishable_sources"] <= 1]
    print(f"\n  {len(thin)} properties rest on 0-1 publishable sources - "
          f"that is the target list for the next source, and it is a\n  "
          f"SPECIFICATION, not an apology.")


if __name__ == "__main__":
    main()
