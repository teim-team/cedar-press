#!/usr/bin/env python3
"""
Cedar Press - 151: rebuild the cross-source entity evidence profile.

WHY NOW
-------
`entity_evidence_profile.csv` was built when Cedar Press held roughly ten
datasets. Today added nine more that carry an entity link - Section 106, FERC,
NEPA, IBIA/IBLA, NRC, 990 Schedule I, FAC Single Audits, grantmaker funding
flows, and litigation positions - plus the deals layer went from 0 entity links
to 752.

The gaming spec states the thesis plainly:

> "Cedar's advantage is not one source. It is that all these administrative
>  traces resolve to one entity/property/event history."

This file is the measurement of that claim. An entity seen in one source is a
lead; an entity seen in eight is a subject.

WHAT IT REFUSES TO DO
---------------------
- **It does not sum dollars across sources.** A prime contract obligation, a
  990 grant received, a resource royalty and a compact payment are different
  concepts in different directions. Summing them would invent a number no
  source reports. Amounts are carried PER SOURCE, never totalled.
- **It does not treat a source as evidence of Native status.** Appearing in
  IBIA as an appellant, or in a FOIA log as a subject, says the entity exists in
  a record - not that it is Native, and not that any attribution is correct.
  Tier stays with the ledger.
- **It counts INDEPENDENT sources.** Two files derived from the same upstream
  are one source. `prime_contracts` and `prime_contracts_archive_backfill` are
  the same federal procurement record and count once.

    py -3 code/151_rebuild_entity_evidence_profile.py
"""

import csv
import os
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"
OUT = CLEAN / "entity_evidence_profile.csv"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

# (file, entity-id column candidates, amount column or None, source label)
# One label per INDEPENDENT record system.
SOURCES = [
    ("prime_contracts.csv", ("tribe_id",), "total_obligations", "federal_contracts"),
    ("federal_funding_transactions.csv", ("tribe_id", "entity_id"), "obligated_usd", "federal_assistance"),
    ("subawards.csv", ("tribe_id", "entity_id"), "subaward_amount", "federal_subawards"),
    ("native_entity_lobbying_disclosures.csv", ("entity_id",), None, "lobbying_lda"),
    ("consultation_events.csv", ("tribe_id",), None, "consultation"),
    ("section_106_consultation_events.csv", ("tribe_id",), None, "section_106"),
    ("ferc_docket_filings.csv", ("resolved_native_entity_id",), None, "ferc"),
    ("nepa_eplanning_projects.csv", ("tribe_id", "entity_id"), None, "nepa"),
    ("admin_appeal_decisions.csv", ("tribe_id", "entity_id"), None, "ibia_ibla"),
    ("nrc_public_meetings.csv", ("tribe_id", "entity_id"), None, "nrc"),
    ("np_schedule_i_grants.csv", ("recipient_entity_id",), "cash_grant_amount", "irs_990_schedule_i"),
    ("fac_tribal_single_audits.csv", ("entity_id", "tribe_id"), None, "single_audit"),
    ("native_issue_litigation_positions.csv", ("native_entity_id",), None, "litigation"),
    ("compacts.csv", ("entity_id", "tribe_id"), None, "gaming_compacts"),
    ("gaming_ordinances.csv", ("tribe_id",), None, "gaming_ordinances"),
    ("gaming_facilities.csv", ("tribe_id", "entity_id"), None, "gaming_properties"),
    ("deals_classified.csv", ("native_party_entity_id",), None, "deals"),
    ("resource_revenue.csv", ("recipient_entity_id",), "amount_usd", "resource_revenue"),
    ("resource_assets.csv", ("owner_entity_id", "entity_id"), None, "resource_assets"),
    ("foia_request_index.csv", ("entity_id", "tribe_id"), None, "foia_requests"),
]


def load(p):
    p = Path(p)
    if not p.exists():
        return None
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def money(v):
    try:
        return float(str(v or "0").replace(",", "").replace("$", "") or 0)
    except ValueError:
        return 0.0


def main():
    print("=== 151: cross-source entity evidence profile ===\n")
    spine = load(SPINE) or []
    meta = {r["tribe_id"]: r for r in spine}

    hits = defaultdict(lambda: defaultdict(int))      # entity -> source -> rows
    amts = defaultdict(dict)                          # entity -> source -> usd
    missing = []

    for fname, idcols, amtcol, label in SOURCES:
        rows = load(CLEAN / fname)
        if rows is None:
            missing.append(fname)
            print(f"  {label:22s} MISSING {fname}")
            continue
        col = next((c for c in idcols if rows and c in rows[0]), None)
        if not col:
            print(f"  {label:22s} no entity column in {fname} "
                  f"(looked for {idcols})")
            continue
        n = 0
        for r in rows:
            eid = (r.get(col) or "").strip()
            if not eid:
                continue
            hits[eid][label] += 1
            n += 1
            if amtcol and amtcol in r:
                amts[eid][label] = amts[eid].get(label, 0.0) + money(r.get(amtcol))
        print(f"  {label:22s} {n:>9,} linked rows  "
              f"({len({(r.get(col) or '').strip() for r in rows if (r.get(col) or '').strip()}):>4} entities)")

    print(f"\n  entities with at least one source: {len(hits):,}")

    out = []
    for eid, srcs in hits.items():
        m = meta.get(eid, {})
        per = "; ".join(f"{k}={v}" for k, v in sorted(srcs.items()))
        amt = "; ".join(f"{k}=${v:,.0f}" for k, v in sorted(amts.get(eid, {}).items()) if v)
        out.append({
            "cedar_entity_id": eid,
            "cedar_entity_name": m.get("canonical_name", ""),
            "entity_class": m.get("entity_class", ""),
            "state": m.get("state", ""),
            "in_spine": "YES" if eid in meta else "NO",
            "n_independent_sources": len(srcs),
            "sources": "; ".join(sorted(srcs)),
            "rows_per_source": per,
            "amounts_per_source_NEVER_SUM": amt,
            "built_date": TODAY,
        })
    out.sort(key=lambda r: (-r["n_independent_sources"],
                            r["cedar_entity_name"] or "zzz"))

    dist = defaultdict(int)
    for r in out:
        dist[r["n_independent_sources"]] += 1
    print("\n  sources per entity:")
    for k in sorted(dist, reverse=True):
        bar = "#" * min(40, dist[k])
        print(f"    {k:>2} source(s): {dist[k]:>4}  {bar}")

    corroborated = sum(1 for r in out if r["n_independent_sources"] >= 3)
    print(f"\n  corroborated by 3+ independent sources: {corroborated:,}")
    print(f"  not in the spine (link points nowhere) : "
          f"{sum(1 for r in out if r['in_spine'] == 'NO'):,}")

    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print(f"\n  wrote {OUT.relative_to(CEDAR)}  ({len(out):,} entities)")

    print("\n  deepest evidence:")
    for r in out[:12]:
        print(f"    {r['n_independent_sources']:>2}  "
              f"{(r['cedar_entity_name'] or r['cedar_entity_id'])[:38]:38s} "
              f"{r['sources'][:70]}")


if __name__ == "__main__":
    main()
