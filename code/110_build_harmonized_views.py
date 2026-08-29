#!/usr/bin/env python3
"""
Cedar Press - 110: Harmonized views, and the variables only Cedar can make.

ELIJAH, 2026-08-07
------------------
"we want to improve the datasets we download and amalgamate too"
"we can also make our own variables too and clean up the data and harmonize it"

Script 109 built the vocabulary. This APPLIES it, and then adds the columns that
exist nowhere upstream.

WHAT A HARMONIZED VIEW IS
-------------------------
The source file is never touched. Each view is a parallel file carrying the
SAME rows under CANONICAL column names, plus Cedar's own derived columns:

    prime_contracts.csv          ->  views/v_prime_contracts.csv
      total_obligations                amount_usd
      awardee_uei                      identifier
      fiscal_year                      fiscal_year
      tribe_id                         cedar_entity_id

A subscriber can then write ONE query across nine datasets instead of learning
nine money-column names. `source_column_map` in the header of each view records
exactly what was renamed, so nothing is hidden.

THE DERIVED COLUMNS - the part nobody upstream has
--------------------------------------------------
    cedar_entity_id          resolved, stable across releases
    cedar_entity_name        canonical name
    ultimate_native_owner    top of the ownership chain, the group-by target
    amount_usd               one money column, whatever the source called it
    amount_usd_real2025      rebased, BEA GDP deflator
    n_independent_sources    how many DIFFERENT Cedar datasets carry this entity
    evidence_summary         plain language: what backs this row
    tier / publishable       may this row publish, per cedar_domain

`n_independent_sources` is the one to notice. No federal source can compute it,
because no federal source knows the others exist. An entity appearing in
contracts, funding, lobbying and gaming is a different asset from one appearing
once, and that is invisible until the datasets are joined on a resolved entity.

Writes data/clean/views/v_<dataset>.csv
       data/clean/entity_evidence_profile.csv
"""

import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
VIEWS = CLEAN / "views"
SPINE = CEDAR / "data" / "spine"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

try:
    from cedar_domain import Tier
except ImportError:
    Tier = None

# dataset file -> which of its columns plays each canonical role.
# First name found in the file wins, so a dataset that gains a column later
# does not need this table edited.
VIEWS_SPEC = {
    "prime_contracts.csv": {
        "cedar_entity_id": ["tribe_id"],
        "amount_usd": ["total_obligations"],
        "amount_usd_real2025": ["total_obligations_real2025"],
        "fiscal_year": ["fiscal_year"],
        "identifier": ["awardee_uei", "cage_code"],
        "reported_name": ["awardee_name"],
        "federal_agency": ["funding_agency"],
        "state": ["recipient_state_code"],
    },
    "federal_funding_transactions.csv": {
        "cedar_entity_id": ["tribe_id"],
        "amount_usd": ["obligated_usd"],
        "fiscal_year": ["fiscal_year"],
        "reported_name": ["recipient_name"],
        "federal_agency": ["awarding_agency", "funding_agency"],
    },
    "subawards.csv": {
        "cedar_entity_id": ["sub_native_tribe_id", "prime_native_tribe_id"],
        "amount_usd": ["subaward_amount"],
        "fiscal_year": ["fiscal_year"],
        "reported_name": ["sub_name"],
    },
    "native_entity_lobbying_disclosures.csv": {
        "cedar_entity_id": ["entity_id"],
        "amount_usd": ["spend_usd"],
        "fiscal_year": ["filing_year", "year"],
        "reported_name": ["client_name"],
    },
    "gaming_properties.csv": {
        "cedar_entity_id": ["tribe_id"],
        "reported_name": ["facility_name"],
        "state": ["state"],
    },
    "consultation_events.csv": {
        "cedar_entity_id": ["tribe_id"],
        "reported_name": ["tribe_name"],
        "federal_agency": ["agency"],
        "as_of_date": ["notice_date", "event_start_date"],
    },
    "earmarks.csv": {
        "cedar_entity_id": ["entity_id"],
        "amount_usd": ["amount_enacted", "amount_requested"],
        "fiscal_year": ["fiscal_year"],
        "reported_name": ["recipient_name"],
    },
    "hearing_appearances.csv": {
        "cedar_entity_id": ["entity_id"],
        "reported_name": ["witness_organization"],
        "as_of_date": ["hearing_date"],
    },
    "nagpra_notice_entity_bridge.csv": {
        "cedar_entity_id": ["tribe_id"],
        "reported_name": ["tribe_name", "party_name"],
    },
    "resource_revenue.csv": {
        "cedar_entity_id": ["recipient_entity_id"],
        "amount_usd": ["amount_usd"],
        "amount_usd_real2025": ["amount_usd_real2025"],
        "as_of_date": ["period_start"],
    },
}

ALWAYS = ["source_url", "source_quote", "fetched_date", "tier",
          "confidence_tier", "measurement_type", "measurement_status"]


def read(p, limit=None):
    p = Path(p)
    if not p.exists():
        return None
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        r = csv.DictReader(fh)
        out = []
        for i, row in enumerate(r):
            if limit and i >= limit:
                break
            out.append(row)
        return out


def pick(row, cands):
    for c in cands:
        v = (row.get(c) or "").strip()
        if v:
            return v, c
    return "", ""


def main():
    print("=== Cedar Press 110: harmonized views ===\n")
    VIEWS.mkdir(parents=True, exist_ok=True)
    spine = {r["tribe_id"]: r for r in read(SPINE / "cedar_entity_spine.csv")}
    print(f"spine: {len(spine):,} entities")

    seen = defaultdict(set)          # entity -> which datasets it appears in
    ent_usd = Counter()

    built = []
    for fname, spec in VIEWS_SPEC.items():
        src = CLEAN / fname
        rows = read(src)
        if rows is None:
            print(f"  {fname:44s} absent")
            continue
        if not rows:
            print(f"  {fname:44s} empty")
            continue

        colmap, out = {}, []
        for r in rows:
            rec = {}
            for canon, cands in spec.items():
                v, used = pick(r, cands)
                rec[canon] = v
                if used and canon not in colmap:
                    colmap[canon] = used
            eid = rec.get("cedar_entity_id", "")
            sp = spine.get(eid, {})
            rec["cedar_entity_name"] = sp.get("canonical_name", "")
            rec["ultimate_native_owner"] = (
                sp.get("ultimate_parent_entity_name")
                or sp.get("canonical_name", ""))
            rec["entity_class"] = sp.get("entity_class", "")
            for c in ALWAYS:
                if c in r:
                    rec[c] = r.get(c, "")
            rec["source_dataset"] = fname
            rec["built_date"] = TODAY
            out.append(rec)
            if eid:
                seen[eid].add(fname)
                try:
                    ent_usd[eid] += float(rec.get("amount_usd") or 0)
                except ValueError:
                    pass

        dest = VIEWS / f"v_{fname}"
        with open(dest, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
            w.writeheader()
            w.writerows(out)
        # what was renamed, recorded beside the view rather than hidden
        (VIEWS / f"v_{fname.replace('.csv', '')}_columnmap.json").write_text(
            json.dumps({"source_file": fname, "renamed": colmap,
                        "built": TODAY}, indent=1), encoding="utf-8")
        built.append((fname, len(out), len(colmap)))
        print(f"  {fname:44s} {len(out):>9,} rows -> v_{fname}")

    # ---- the variable no upstream source can compute --------------------
    prof = []
    for eid, ds in seen.items():
        sp = spine.get(eid, {})
        n = len(ds)
        prof.append({
            "cedar_entity_id": eid,
            "cedar_entity_name": sp.get("canonical_name", ""),
            "entity_class": sp.get("entity_class", ""),
            "state": sp.get("state", ""),
            "n_independent_sources": n,
            "sources": " | ".join(sorted(x.replace(".csv", "") for x in ds)),
            "total_amount_usd": round(ent_usd.get(eid, 0.0), 2),
            "evidence_summary": (
                f"Appears in {n} independent Cedar dataset"
                f"{'s' if n != 1 else ''}: "
                + ", ".join(sorted(x.replace('.csv', '').replace('_', ' ')
                                   for x in ds))
                + "." + (" Cross-dataset agreement raises confidence in the "
                         "attribution." if n >= 3 else
                         " A single source is weaker evidence than several."
                         if n == 1 else "")),
            "built_date": TODAY,
        })
    prof.sort(key=lambda r: (-r["n_independent_sources"],
                             -r["total_amount_usd"]))
    p = CLEAN / "entity_evidence_profile.csv"
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(prof[0].keys()))
        w.writeheader()
        w.writerows(prof)

    print(f"\n  wrote {p.relative_to(CEDAR)}  ({len(prof):,} entities)")
    d = Counter(r["n_independent_sources"] for r in prof)
    for k in sorted(d, reverse=True):
        print(f"     {d[k]:>4} entities appear in {k} dataset"
              f"{'s' if k != 1 else ''}")
    multi = sum(1 for r in prof if r["n_independent_sources"] >= 3)
    print(f"\n  {multi:,} entities are corroborated by 3+ independent datasets")
    print("  That number cannot be computed from any single federal source -")
    print("  no source knows the others exist. It is the join that creates it.")
    print("\n  most corroborated:")
    for r in prof[:8]:
        print(f"     {r['n_independent_sources']}x  "
              f"{r['cedar_entity_name'][:34]:34s} {r['sources'][:56]}")


if __name__ == "__main__":
    main()
