"""
199_faads_identifier_by_agency_year.py
======================================
Cedar Press. Written 2026-08-26.

WHY THIS EXISTS.

`docs/FAADS_FEASIBILITY_2026-08-05.md` measured the pre-2008 identifier gap on
ONE agency -- Department of the Interior -- and found DUNS at 0.0% right through
FY2009, 14.3% in FY2010, 99.9% in FY2011. It concluded "the seam is at FY2010".

Script 197 measured the SAME quantity across ALL 2,769,748 rows and got a
different shape: FY2006 = 0.0103% DUNS, **FY2007 = 87.4% DUNS**.

Both are correct. They disagree because one is DOI and one is everybody. That
means the identifier cliff is AGENCY-SPECIFIC, and the project has been
generalising one agency's behaviour into a rule about the source -- the exact
error shape recorded twice already (the tribal Single Audit "dead end" and
`resource_assets.csv`).

THE QUESTION: does ANY agency carry a recipient identifier before FY2007? If
even one does, then "per-entity federal assistance cannot begin before FY2007"
is false as stated, and the true statement is narrower and per-agency.

READ-ONLY. One JSON + one CSV to docs/. Zero network requests.

Run:  py -3 code/199_faads_identifier_by_agency_year.py
"""

import csv
import json
import os
import sys
import collections
from datetime import datetime, timezone

csv.field_size_limit(10 ** 9)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAADS = os.path.join(ROOT, "data", "clean", "faads_transactions_all_agencies.csv")
OUT_JSON = os.path.join(ROOT, "docs", "PRE2007_IDENTIFIER_BY_AGENCY.json")
OUT_CSV = os.path.join(ROOT, "docs", "PRE2007_IDENTIFIER_BY_AGENCY.csv")

TRIBAL_TYPE_CODES = {"I", "J", "K"}   # USAspending recipient-type = tribal


def main():
    f = open(FAADS, encoding="utf-8", errors="replace", newline="")
    rd = csv.reader(f)
    hdr = next(rd)
    ix = {h: i for i, h in enumerate(hdr)}

    cell = collections.defaultdict(lambda: collections.Counter())
    dollars = collections.defaultdict(float)
    # tribal-flagged rows, which is the population Cedar Press actually needs
    tribal = collections.defaultdict(lambda: collections.Counter())
    tribal_dollars = collections.defaultdict(float)

    n = 0
    for row in rd:
        if len(row) < len(hdr):
            continue
        n += 1
        fy = row[ix["fiscal_year"]].strip()
        ag = row[ix["agency"]].strip() or "(blank)"
        key = (fy, ag)
        cell[key]["rows"] += 1
        try:
            d = float(row[ix["obligated_usd"]] or 0)
        except ValueError:
            d = 0.0
        dollars[key] += d
        has_duns = bool(row[ix["recipient_duns"]].strip())
        has_uei = bool(row[ix["recipient_uei"]].strip())
        if has_duns:
            cell[key]["duns"] += 1
        if has_uei:
            cell[key]["uei"] += 1
        if row[ix["award_id_fain"]].strip():
            cell[key]["fain"] += 1

        rt = row[ix["recipient_type"]].strip().upper()
        if rt in TRIBAL_TYPE_CODES:
            tribal[key]["rows"] += 1
            tribal_dollars[key] += d
            if has_duns:
                tribal[key]["duns"] += 1
            if has_uei:
                tribal[key]["uei"] += 1
        if n % 500000 == 0:
            print(f"  ...{n:,}", file=sys.stderr)
    f.close()

    rows_out = []
    for (fy, ag) in sorted(cell):
        c = cell[(fy, ag)]
        t = tribal[(fy, ag)]
        rows_out.append({
            "fiscal_year": fy,
            "agency": ag,
            "rows": c["rows"],
            "obligated_usd": round(dollars[(fy, ag)], 2),
            "duns_rows": c["duns"],
            "duns_pct": round(100.0 * c["duns"] / c["rows"], 4) if c["rows"] else 0,
            "uei_rows": c["uei"],
            "uei_pct": round(100.0 * c["uei"] / c["rows"], 4) if c["rows"] else 0,
            "fain_pct": round(100.0 * c["fain"] / c["rows"], 4) if c["rows"] else 0,
            "tribal_flagged_rows": t["rows"],
            "tribal_flagged_usd": round(tribal_dollars[(fy, ag)], 2),
            "tribal_duns_rows": t["duns"],
            "tribal_duns_pct": round(100.0 * t["duns"] / t["rows"], 4) if t["rows"] else 0,
        })

    tmp = OUT_CSV + ".part"
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows_out[0].keys()))
        w.writeheader()
        w.writerows(rows_out)
    os.replace(tmp, OUT_CSV)

    # ---- the finding: any agency-year before FY2007 with a real identifier? ----
    pre = [r for r in rows_out if r["fiscal_year"].isdigit()
           and int(r["fiscal_year"]) < 2007]
    any_id = sorted([r for r in pre if r["duns_rows"] > 0],
                    key=lambda r: -r["duns_rows"])
    tribal_any_id = sorted([r for r in pre if r["tribal_duns_rows"] > 0],
                           key=lambda r: -r["tribal_duns_rows"])

    # FY2007 by agency -- who had crossed over and who had not
    fy07 = sorted([r for r in rows_out if r["fiscal_year"] == "2007"],
                  key=lambda r: -r["rows"])

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "script": "code/199_faads_identifier_by_agency_year.py",
        "network_requests_issued": 0,
        "rows_scanned": n,
        "question": "Does ANY agency carry a recipient identifier before FY2007?",
        "pre_fy2007_agency_year_cells": len(pre),
        "pre_fy2007_cells_with_at_least_one_DUNS": len(any_id),
        "pre_fy2007_rows_total": sum(r["rows"] for r in pre),
        "pre_fy2007_rows_with_DUNS": sum(r["duns_rows"] for r in pre),
        "pre_fy2007_usd_total": round(sum(r["obligated_usd"] for r in pre), 2),
        "pre_fy2007_tribal_flagged_rows": sum(r["tribal_flagged_rows"] for r in pre),
        "pre_fy2007_tribal_flagged_usd": round(
            sum(r["tribal_flagged_usd"] for r in pre), 2),
        "pre_fy2007_tribal_rows_with_DUNS": sum(r["tribal_duns_rows"] for r in pre),
        "top_pre2007_cells_with_any_DUNS": any_id[:25],
        "top_pre2007_TRIBAL_cells_with_any_DUNS": tribal_any_id[:25],
        "fy2007_by_agency": fy07,
        "csv": OUT_CSV,
    }

    tmp = OUT_JSON + ".part"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
    os.replace(tmp, OUT_JSON)
    with open(OUT_JSON, encoding="utf-8") as fh:
        back = json.load(fh)
    assert back["script"] == report["script"], "re-read verification FAILED"

    print(f"\nwrote + verified {OUT_JSON}\nwrote {OUT_CSV}", file=sys.stderr)
    print(f"\npre-FY2007: {report['pre_fy2007_rows_total']:,} rows, "
          f"${report['pre_fy2007_usd_total']:,.0f}", file=sys.stderr)
    print(f"  agency-year cells: {report['pre_fy2007_agency_year_cells']}, "
          f"cells with >=1 DUNS: {report['pre_fy2007_cells_with_at_least_one_DUNS']}",
          file=sys.stderr)
    print(f"  rows with a DUNS: {report['pre_fy2007_rows_with_DUNS']:,}",
          file=sys.stderr)
    print(f"  TRIBAL-flagged rows: {report['pre_fy2007_tribal_flagged_rows']:,} "
          f"(${report['pre_fy2007_tribal_flagged_usd']:,.0f}), "
          f"of which with DUNS: {report['pre_fy2007_tribal_rows_with_DUNS']:,}",
          file=sys.stderr)
    print("\n  top pre-2007 cells carrying ANY DUNS:", file=sys.stderr)
    for r in any_id[:12]:
        print(f"    FY{r['fiscal_year']} {r['agency'][:52]:<52} "
              f"{r['duns_rows']:>6,}/{r['rows']:>7,} = {r['duns_pct']}%",
              file=sys.stderr)
    print("\n  FY2007 by agency (the crossover year):", file=sys.stderr)
    for r in fy07[:18]:
        print(f"    {r['agency'][:52]:<52} rows={r['rows']:>7,} "
              f"duns={r['duns_pct']:>7}%  tribal={r['tribal_flagged_rows']:>6,} "
              f"tribal_duns={r['tribal_duns_pct']}%", file=sys.stderr)


if __name__ == "__main__":
    main()
