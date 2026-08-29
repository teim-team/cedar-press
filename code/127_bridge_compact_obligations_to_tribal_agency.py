#!/usr/bin/env python3
"""
Cedar Press - 127: name the tribal agency a compact obligation actually runs to.

THE GAP
-------
`compact_required_reports.csv` holds 4,121 reporting obligations. 1,030 of them
run to the TRIBAL side, across 168 tribes - and the compacts name the recipient
only as boilerplate:

    Tribal Gaming Agency            674
    Tribal Gaming Commission        153
    The Tribal Gaming Agency        110
    Tribe. The Tribal Gaming Agency  48
    State. The Tribal Gaming Commission 11

So we know 1,030 obligations run to a tribal regulator and cannot name a single
one of them. The compact parse surfaced this and could not close it.

The gaming ordinance build (2026-08-12) closed it from the other side: **284 of
321 tribes name their gaming agency in the ordinance**, 397 distinct names, 363
tribe-specific. This script joins the two.

WHY IT IS TIME-AWARE, AND WHY THAT MATTERS
------------------------------------------
A tribe's gaming agency is not a constant. Ordinances are amended - Bay Mills
alone has 23 instruments spanning decades - and amendments rename, restructure
and replace the regulator. Attaching a 2019 agency name to a 1997 obligation
would assert an institution that did not exist.

So each obligation is matched against the ordinance instrument **in force on the
obligation's effective date**, using `effective_range_start` / `effective_range_end`.
Where the obligation carries no usable date, the match is still made but typed
`AGENCY_NAME_UNDATED_MATCH` so it can never be mistaken for a dated one.

WHAT IT REFUSES TO DO
---------------------
- **It writes a BRIDGE, never into `compact_required_reports.csv`.** That file is
  rebuilt by its own script; columns added here would be silently destroyed on
  the next run, and a link that disappears is worse than one that was never made.
- **A tribe with no ordinance gets NO row.** Not a blank, not a guess - absence
  from the ordinance index is a property of NIGC's index, and 18 tribes hold a
  compact with no ordinance published at all.
- **It does not resolve the 37 tribes whose ordinance names no agency.** An
  ordinance that is silent on the regulator is silent; inventing "X Tribal
  Gaming Commission" from the tribe's name would be fabrication.
- **It does not collapse an agency onto the tribe.** A tribal gaming agency is a
  distinct institution from the tribal government that chartered it.

    py -3 code/127_bridge_compact_obligations_to_tribal_agency.py
"""

import csv
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

OUT = CLEAN / "compact_obligation_tribal_agency_bridge.csv"

# Boilerplate placeholders that name no institution.
GENERIC = re.compile(
    r"^\s*(the\s+|tribe\.\s*the\s+|state\.\s*the\s+)?"
    r"tribal\s+gaming\s+(agency|commission|authority|board|office)\s*$", re.I)


def load(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def d(s):
    s = (s or "").strip()[:10]
    return s if re.match(r"^\d{4}-\d{2}-\d{2}$", s) else ""


def main():
    print("=== 127: bridge compact obligations -> named tribal agency ===\n")
    reports = load(CLEAN / "compact_required_reports.csv")
    ords = load(CLEAN / "gaming_ordinances.csv")
    if not reports or not ords:
        print("  missing input - refusing")
        return

    # tribe_id -> [(start, end, agency, ordinance_id, approval_date)]
    by_tribe = defaultdict(list)
    named_tribes = set()
    for o in ords:
        ag = (o.get("tribal_gaming_agency_named") or "").strip()
        if not ag or ag.upper() in {"NO", "FALSE", "NONE", "N/A"}:
            continue
        tid = (o.get("tribe_id") or "").strip()
        if not tid:
            continue
        named_tribes.add(tid)
        by_tribe[tid].append((
            d(o.get("effective_range_start")) or d(o.get("approval_date")),
            d(o.get("effective_range_end")),
            ag,
            o.get("ordinance_id", ""),
            d(o.get("approval_date")),
            (o.get("in_force_status") or "").strip(),
        ))
    for tid in by_tribe:
        by_tribe[tid].sort(key=lambda x: x[0] or "")
    print(f"  ordinances                 : {len(ords):,}")
    print(f"  tribes naming an agency    : {len(named_tribes):,}")

    tribal = [r for r in reports
              if (r.get("recipient_side") or "").strip().lower() == "tribal"
              or "tribal" in (r.get("recipient_agency") or "").lower()]
    print(f"  reporting obligations      : {len(reports):,}")
    print(f"  ...running to tribal side  : {len(tribal):,}")
    gen = sum(1 for r in tribal if GENERIC.match(r.get("recipient_agency") or ""))
    print(f"  ...whose recipient is boilerplate: {gen:,}")

    out, stats = [], Counter()
    for r in tribal:
        tid = (r.get("tribe_id") or "").strip()
        if not tid:
            stats["no tribe_id on obligation"] += 1
            continue
        cands = by_tribe.get(tid)
        if not cands:
            stats["REFUSED - tribe has no ordinance naming an agency"] += 1
            continue

        when = d(r.get("effective_from"))
        pick, basis = None, ""
        if when:
            in_force = [c for c in cands
                        if (not c[0] or c[0] <= when)
                        and (not c[1] or c[1] >= when)]
            if in_force:
                pick, basis = in_force[-1], "AGENCY_NAME_IN_FORCE_AT_OBLIGATION_DATE"
            else:
                prior = [c for c in cands if c[0] and c[0] <= when]
                if prior:
                    pick, basis = prior[-1], "AGENCY_NAME_MOST_RECENT_PRIOR_INSTRUMENT"
        if pick is None:
            pick = cands[-1]
            basis = ("AGENCY_NAME_UNDATED_MATCH" if not when
                     else "AGENCY_NAME_NO_INSTRUMENT_COVERS_DATE")
        stats[basis] += 1

        out.append({
            "bridge_id": f"CORTA-{r.get('report_id','')}",
            "report_id": r.get("report_id", ""),
            "compact_id": r.get("compact_id", ""),
            "tribe_id": tid,
            "tribe_canonical_name": r.get("tribe_canonical_name", ""),
            "state": r.get("state", ""),
            "obligation_frequency": r.get("frequency", ""),
            "compact_recipient_text": r.get("recipient_agency", ""),
            "compact_recipient_is_boilerplate":
                "YES" if GENERIC.match(r.get("recipient_agency") or "") else "NO",
            "obligation_effective_from": when,
            "named_tribal_gaming_agency": pick[2],
            "agency_source_ordinance_id": pick[3],
            "agency_ordinance_approval_date": pick[4],
            "agency_ordinance_in_force_status": pick[5],
            "match_basis": basis,
            "n_agency_instruments_for_tribe": len(cands),
            "confidence_tier": "A" if basis.startswith(
                "AGENCY_NAME_IN_FORCE") else "B",
            "source": "compact_required_reports.csv + gaming_ordinances.csv",
            "built_date": TODAY,
        })

    print("\n[match basis]")
    for k, v in stats.most_common():
        print(f"  {k:52s} {v:>5}")

    if not out:
        print("\n  nothing bridged - refusing to write an empty file")
        return

    tiers = Counter(r["confidence_tier"] for r in out)
    agencies = {r["named_tribal_gaming_agency"] for r in out}
    tribes = {r["tribe_id"] for r in out}
    print(f"\n  obligations now naming an agency : {len(out):,}")
    print(f"  distinct agencies named          : {len(agencies):,}")
    print(f"  distinct tribes                  : {len(tribes):,}")
    print(f"  tier                             : {dict(tiers)}")

    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print(f"\n  wrote {OUT.relative_to(CEDAR)}  ({len(out):,} rows)")

    print("\n  sample:")
    for r in out[:8]:
        print(f"    {r['tribe_canonical_name'][:26]:26s} "
              f"{r['compact_recipient_text'][:24]:24s} -> "
              f"{r['named_tribal_gaming_agency'][:40]}")


if __name__ == "__main__":
    main()
