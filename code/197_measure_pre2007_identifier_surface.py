"""
197_measure_pre2007_identifier_surface.py
=========================================
Cedar Press. Written 2026-08-26.

PURPOSE — separate two claims the project has been conflating.

  CLAIM A (measured, sound, stands): FAADS as held carries a RECIPIENT
          IDENTIFIER on 0.0% of rows FY2001-06.
  CLAIM B (does NOT follow): per-entity federal spending is unobtainable
          before FY2007.

This script re-measures CLAIM A from the file, and then measures what the file
DOES carry on those same rows -- award identifier, recipient name, city, state,
zip, CFDA -- because a route that keys on a FAIN or on (name, city, state, zip)
is a different route, not a weaker version of the same one.

It also measures the local FPDS extracts' pre-2007 slice, because
`fpds_uei_cage_map.csv` spans 1979-2023 and that is direct evidence that
contractor-level pre-2007 data already exists inside this repo.

READ-ONLY. Writes exactly one JSON report to docs/. Touches no clean table,
no spine, no ledger. Makes ZERO network requests.

Run:  py -3 code/197_measure_pre2007_identifier_surface.py
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
OUT = os.path.join(ROOT, "docs", "PRE2007_IDENTIFIER_SURFACE.json")

FPDS_FILES = [
    os.path.join(ROOT, "data", "raw", "esm_hci", "ESM", "raw",
                 "Data Request 4-5-2023 File 1.csv"),
    os.path.join(ROOT, "data", "raw", "esm_hci", "ESM", "raw",
                 "Data Request 4-5-2023 File 2.csv"),
    os.path.join(ROOT, "data", "raw", "esm_hci", "ESM", "raw",
                 "Data Request 5-8-2023 IDVs.csv"),
]


def pct(n, d):
    return round(100.0 * n / d, 4) if d else None


def measure_faads():
    """Per-fiscal-year population of every column that could key a recipient."""
    if not os.path.exists(FAADS):
        return {"error": "file not found", "path": FAADS}

    f = open(FAADS, encoding="utf-8", errors="replace", newline="")
    rd = csv.reader(f)
    hdr = next(rd)
    ix = {h: i for i, h in enumerate(hdr)}

    # every column that could conceivably resolve a recipient
    probe = ["recipient_duns", "recipient_uei", "tribe_id", "award_id_fain",
             "recipient_name", "recipient_city", "recipient_state",
             "recipient_zip", "recipient_type", "cfda_program", "source_url",
             "api_endpoint", "source_file"]
    probe = [c for c in probe if c in ix]

    by_year = collections.defaultdict(lambda: collections.Counter())
    totals = collections.Counter()
    dollars = collections.defaultdict(float)
    endpoints = collections.Counter()
    srcfiles = collections.Counter()
    # distinct (name, city, state, zip) tuples -- the tier-B name floor's real key
    namekeys = collections.defaultdict(set)

    n = 0
    for row in rd:
        if len(row) < len(hdr):
            continue
        n += 1
        fy = row[ix["fiscal_year"]].strip()
        by_year[fy]["rows"] += 1
        totals["rows"] += 1
        try:
            d = float(row[ix["obligated_usd"]] or 0)
        except ValueError:
            d = 0.0
        dollars[fy] += d
        for c in probe:
            if row[ix[c]].strip():
                by_year[fy][c] += 1
                totals[c] += 1
        if "api_endpoint" in ix:
            endpoints[row[ix["api_endpoint"]].strip()] += 1
        if "source_file" in ix:
            srcfiles[row[ix["source_file"]].strip()] += 1
        # name-floor key, only for the pre-2007 years we care about
        if fy and fy < "2007":
            namekeys[fy].add((
                row[ix["recipient_name"]].strip().upper(),
                row[ix["recipient_city"]].strip().upper(),
                row[ix["recipient_state"]].strip().upper(),
                row[ix["recipient_zip"]].strip()[:5],
            ))
        if n % 500000 == 0:
            print(f"  ...{n:,} rows", file=sys.stderr)
    f.close()

    years = {}
    for fy in sorted(by_year):
        r = by_year[fy]["rows"]
        years[fy] = {
            "rows": r,
            "obligated_usd": round(dollars[fy], 2),
            "populated_pct": {c: pct(by_year[fy][c], r) for c in probe},
            "distinct_name_city_state_zip": len(namekeys[fy]) if fy in namekeys else None,
        }

    return {
        "path": FAADS,
        "columns": hdr,
        "total_rows": totals["rows"],
        "overall_populated_pct": {c: pct(totals[c], totals["rows"]) for c in probe},
        "by_fiscal_year": years,
        "api_endpoint_values": dict(endpoints.most_common(10)),
        "distinct_source_files": len(srcfiles),
        "source_file_sample": [k for k, _ in srcfiles.most_common(8)],
    }


def measure_fpds(path, cap_rows=None):
    """Pre-2007 slice of one FPDS extract: rows, dollars, identifier population."""
    if not os.path.exists(path):
        return {"error": "file not found", "path": path}

    f = open(path, encoding="utf-8", errors="replace", newline="")
    rd = csv.reader(f)
    hdr = next(rd)
    ix = {}
    for i, h in enumerate(hdr):
        if h not in ix:          # duplicate headers exist; keep FIRST position
            ix[h] = i

    need = ["action_date_fiscal_year", "federal_action_obligation", "uei_id",
            "cage_code", "recipient_duns", "recipient_name", "award_id_piid",
            "recipient_state_code", "type_of_set_aside", "naics_code",
            "awarding_agency_name", "ultimate_parent_uei"]
    need = [c for c in need if c in ix]
    maxi = max(ix[c] for c in need)

    by_year = collections.defaultdict(lambda: collections.Counter())
    dollars = collections.defaultdict(float)
    ueis_pre = set()
    cages_pre = set()
    duns_pre = set()
    piids_pre = set()

    n = 0
    for row in rd:
        if len(row) <= maxi:
            continue
        n += 1
        if cap_rows and n > cap_rows:
            break
        fy = row[ix["action_date_fiscal_year"]].strip()
        by_year[fy]["rows"] += 1
        try:
            dollars[fy] += float(row[ix["federal_action_obligation"]] or 0)
        except ValueError:
            pass
        for c in need:
            if row[ix[c]].strip():
                by_year[fy][c] += 1
        if fy.isdigit() and int(fy) < 2007:
            if "uei_id" in ix and row[ix["uei_id"]].strip():
                ueis_pre.add(row[ix["uei_id"]].strip())
            if "cage_code" in ix and row[ix["cage_code"]].strip():
                cages_pre.add(row[ix["cage_code"]].strip())
            if "recipient_duns" in ix and row[ix["recipient_duns"]].strip():
                duns_pre.add(row[ix["recipient_duns"]].strip())
            if "award_id_piid" in ix and row[ix["award_id_piid"]].strip():
                piids_pre.add(row[ix["award_id_piid"]].strip())
        if n % 250000 == 0:
            print(f"  ...{os.path.basename(path)} {n:,} rows", file=sys.stderr)
    f.close()

    years = {}
    pre_rows = 0
    pre_dollars = 0.0
    for fy in sorted(by_year):
        r = by_year[fy]["rows"]
        years[fy] = {
            "rows": r,
            "obligated_usd": round(dollars[fy], 2),
            "populated_pct": {c: pct(by_year[fy][c], r) for c in need},
        }
        if fy.isdigit() and int(fy) < 2007:
            pre_rows += r
            pre_dollars += dollars[fy]

    return {
        "path": path,
        "rows_scanned": n,
        "pre_fy2007": {
            "rows": pre_rows,
            "obligated_usd": round(pre_dollars, 2),
            "distinct_uei": len(ueis_pre),
            "distinct_cage": len(cages_pre),
            "distinct_duns": len(duns_pre),
            "distinct_piid": len(piids_pre),
        },
        "by_fiscal_year": years,
    }


def main():
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "script": "code/197_measure_pre2007_identifier_surface.py",
        "network_requests_issued": 0,
        "purpose": ("Separate 'FAADS-as-held carries no recipient identifier' "
                    "(true) from 'pre-FY2007 per-entity spending is "
                    "unobtainable' (does not follow)."),
    }

    print("[1/2] FAADS identifier surface ...", file=sys.stderr)
    report["faads"] = measure_faads()

    print("[2/2] FPDS extracts pre-2007 slice ...", file=sys.stderr)
    report["fpds_extracts"] = [measure_fpds(p) for p in FPDS_FILES]

    tmp = OUT + ".part"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
    os.replace(tmp, OUT)

    # verify the write by RE-READING it (concurrency rule 4)
    with open(OUT, encoding="utf-8") as fh:
        back = json.load(fh)
    assert back["script"] == report["script"], "re-read verification FAILED"
    print(f"\nwrote + verified {OUT}", file=sys.stderr)

    fa = report["faads"]
    if "by_fiscal_year" in fa:
        print("\nFAADS pre-2007 identifier population:", file=sys.stderr)
        for fy in sorted(fa["by_fiscal_year"]):
            if fy.isdigit() and int(fy) < 2008:
                y = fa["by_fiscal_year"][fy]
                p = y["populated_pct"]
                print(f"  FY{fy}  rows={y['rows']:>9,}  "
                      f"duns={p.get('recipient_duns')}%  "
                      f"uei={p.get('recipient_uei')}%  "
                      f"fain={p.get('award_id_fain')}%  "
                      f"name={p.get('recipient_name')}%  "
                      f"zip={p.get('recipient_zip')}%  "
                      f"distinct_name_key={y['distinct_name_city_state_zip']}",
                      file=sys.stderr)
    for e in report["fpds_extracts"]:
        if "pre_fy2007" in e:
            p = e["pre_fy2007"]
            print(f"\n{os.path.basename(e['path'])}: pre-FY2007 "
                  f"rows={p['rows']:,} ${p['obligated_usd']:,.0f} "
                  f"uei={p['distinct_uei']:,} cage={p['distinct_cage']:,} "
                  f"duns={p['distinct_duns']:,} piid={p['distinct_piid']:,}",
                  file=sys.stderr)


if __name__ == "__main__":
    main()
