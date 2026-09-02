"""
198_compare_fpds_extracts_vs_prime_clean.py
===========================================
Cedar Press. Written 2026-08-26.

Script 197 measured that the three HigherGov FPDS extracts on disk carry
`uei_id` on 100.0% of rows back to FY1979 and `recipient_duns` on ~99%.
That is per-entity pre-FY2007 procurement data sitting inside this repo.

THE QUESTION THIS SCRIPT ANSWERS: is any of it NEW?

`data/clean/prime_contracts.csv` already runs FY2000-2026. If its FY1979-2006
rows came from these same extracts, the finding is "already exploited" and adds
nothing. If they came from somewhere else -- or if there are no FY1979-1999 rows
at all -- then the extracts are an unexploited pre-2007 source.

Compares on the identifier the two sides share: (contract_number/award_id_piid,
fiscal_year, uei). AGENTS.md's standing rule applies -- PIID and UEI are
IDENTIFIERS; funding_agency is a RENDERED LABEL and is kept OUT of the key.

READ-ONLY. Writes one JSON report to docs/. Zero network requests.

Run:  py -3 code/198_compare_fpds_extracts_vs_prime_clean.py
"""

import csv
import json
import os
import sys
import collections
from datetime import datetime, timezone

csv.field_size_limit(10 ** 9)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRIME = os.path.join(ROOT, "data", "clean", "prime_contracts.csv")
OUT = os.path.join(ROOT, "docs", "PRE2007_FPDS_VS_PRIME_OVERLAP.json")

FPDS_FILES = [
    os.path.join(ROOT, "data", "raw", "esm_hci", "ESM", "raw",
                 "Data Request 4-5-2023 File 1.csv"),
    os.path.join(ROOT, "data", "raw", "esm_hci", "ESM", "raw",
                 "Data Request 4-5-2023 File 2.csv"),
    os.path.join(ROOT, "data", "raw", "esm_hci", "ESM", "raw",
                 "Data Request 5-8-2023 IDVs.csv"),
]

CUTOFF = 2007          # "pre-2007" means action_date_fiscal_year < 2007


def load_prime():
    """Pre-2007 slice of the clean prime table, plus provenance by year."""
    f = open(PRIME, encoding="utf-8", errors="replace", newline="")
    rd = csv.reader(f)
    hdr = next(rd)
    ix = {h: i for i, h in enumerate(hdr)}

    keys = set()                      # (piid, fy, uei)
    piid_fy = set()                   # (piid, fy) -- looser key
    ueis = set()
    by_year = collections.defaultdict(lambda: collections.Counter())
    src_by_year = collections.defaultdict(collections.Counter)
    dollars = collections.defaultdict(float)

    n = 0
    for row in rd:
        if len(row) < len(hdr):
            continue
        n += 1
        fy = row[ix["fiscal_year"]].strip()
        by_year[fy]["rows"] += 1
        src_by_year[fy][row[ix["source_file"]].strip()] += 1
        try:
            dollars[fy] += float(row[ix["total_obligations"]] or 0)
        except ValueError:
            pass
        if row[ix["awardee_uei"]].strip():
            by_year[fy]["uei"] += 1
        if row[ix["cage_code"]].strip():
            by_year[fy]["cage"] += 1
        if row[ix["attributed_flag"]].strip() in ("1", "True", "true"):
            by_year[fy]["attributed"] += 1
        if fy.isdigit() and int(fy) < CUTOFF:
            p = row[ix["contract_number"]].strip().upper()
            u = row[ix["awardee_uei"]].strip().upper()
            if p:
                piid_fy.add((p, fy))
                keys.add((p, fy, u))
            if u:
                ueis.add(u)
        if n % 300000 == 0:
            print(f"  ...prime {n:,}", file=sys.stderr)
    f.close()

    years = {}
    for fy in sorted(by_year):
        r = by_year[fy]["rows"]
        years[fy] = {
            "rows": r,
            "obligated_usd": round(dollars[fy], 2),
            "uei_pct": round(100.0 * by_year[fy]["uei"] / r, 3) if r else None,
            "cage_pct": round(100.0 * by_year[fy]["cage"] / r, 3) if r else None,
            "attributed_pct": round(100.0 * by_year[fy]["attributed"] / r, 3) if r else None,
            "source_files": dict(src_by_year[fy].most_common(6)),
        }
    return {"total_rows": n, "by_fiscal_year": years}, keys, piid_fy, ueis


def scan_fpds(path, prime_keys, prime_piid_fy, prime_ueis):
    f = open(path, encoding="utf-8", errors="replace", newline="")
    rd = csv.reader(f)
    hdr = next(rd)
    ix = {}
    for i, h in enumerate(hdr):
        if h not in ix:
            ix[h] = i
    need = ["action_date_fiscal_year", "award_id_piid", "uei_id",
            "federal_action_obligation", "recipient_duns", "uei_legal_business_name"]
    missing = [c for c in need if c not in ix]
    if missing:
        return {"path": path, "error": f"missing columns {missing}"}
    maxi = max(ix[c] for c in need)

    matched_exact = set()
    matched_piid_fy = set()
    unmatched_keys = set()
    pre_keys = set()
    new_ueis = set()
    seen_ueis = set()
    dollars_matched = 0.0
    dollars_unmatched = 0.0
    rows_pre = 0
    by_year_new = collections.defaultdict(lambda: {"rows": 0, "new_rows": 0, "usd_new": 0.0})

    n = 0
    for row in rd:
        if len(row) <= maxi:
            continue
        n += 1
        fy = row[ix["action_date_fiscal_year"]].strip()
        if not (fy.isdigit() and int(fy) < CUTOFF):
            if n % 250000 == 0:
                print(f"  ...{os.path.basename(path)} {n:,}", file=sys.stderr)
            continue
        rows_pre += 1
        p = row[ix["award_id_piid"]].strip().upper()
        u = row[ix["uei_id"]].strip().upper()
        try:
            d = float(row[ix["federal_action_obligation"]] or 0)
        except ValueError:
            d = 0.0
        k = (p, fy, u)
        pre_keys.add(k)
        by_year_new[fy]["rows"] += 1
        if u:
            seen_ueis.add(u)
            if u not in prime_ueis:
                new_ueis.add(u)
        if k in prime_keys:
            matched_exact.add(k)
            dollars_matched += d
        elif (p, fy) in prime_piid_fy:
            matched_piid_fy.add((p, fy))
            dollars_matched += d
        else:
            unmatched_keys.add(k)
            dollars_unmatched += d
            by_year_new[fy]["new_rows"] += 1
            by_year_new[fy]["usd_new"] += d
        if n % 250000 == 0:
            print(f"  ...{os.path.basename(path)} {n:,}", file=sys.stderr)
    f.close()

    return {
        "path": path,
        "rows_scanned": n,
        "pre_fy2007_rows": rows_pre,
        "pre_fy2007_distinct_keys_piid_fy_uei": len(pre_keys),
        "keys_matching_prime_exactly": len(matched_exact),
        "keys_matching_prime_on_piid_fy_only": len(matched_piid_fy),
        "keys_NOT_in_prime": len(unmatched_keys),
        "usd_on_matched": round(dollars_matched, 2),
        "usd_on_unmatched": round(dollars_unmatched, 2),
        "distinct_uei_pre2007": len(seen_ueis),
        "distinct_uei_pre2007_ABSENT_from_prime_pre2007": len(new_ueis),
        "by_fiscal_year": {fy: {"rows": v["rows"], "rows_not_in_prime": v["new_rows"],
                                "usd_not_in_prime": round(v["usd_new"], 2)}
                           for fy, v in sorted(by_year_new.items())},
    }


def main():
    print("[1/2] loading clean prime table ...", file=sys.stderr)
    prime_profile, pkeys, ppiid, pueis = load_prime()
    print(f"  prime pre-{CUTOFF} keys: {len(pkeys):,}; "
          f"distinct UEIs: {len(pueis):,}", file=sys.stderr)

    print("[2/2] scanning FPDS extracts ...", file=sys.stderr)
    ext = [scan_fpds(p, pkeys, ppiid, pueis) for p in FPDS_FILES]

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "script": "code/198_compare_fpds_extracts_vs_prime_clean.py",
        "network_requests_issued": 0,
        "cutoff_fiscal_year": CUTOFF,
        "join_key": "contract_number/award_id_piid + fiscal_year + UEI "
                    "(funding_agency deliberately EXCLUDED -- it is a rendered "
                    "label, not an identifier; see AGENTS.md 2026-08-12)",
        "prime_clean": prime_profile,
        "prime_pre2007_distinct_keys": len(pkeys),
        "prime_pre2007_distinct_uei": len(pueis),
        "fpds_extracts": ext,
    }

    tmp = OUT + ".part"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
    os.replace(tmp, OUT)
    with open(OUT, encoding="utf-8") as fh:
        back = json.load(fh)
    assert back["script"] == report["script"], "re-read verification FAILED"
    print(f"\nwrote + verified {OUT}", file=sys.stderr)

    print("\n--- clean prime_contracts.csv, FY1979-2008 ---", file=sys.stderr)
    for fy in sorted(prime_profile["by_fiscal_year"]):
        if fy.isdigit() and int(fy) < 2009:
            y = prime_profile["by_fiscal_year"][fy]
            print(f"  FY{fy} rows={y['rows']:>8,} ${y['obligated_usd']:>15,.0f} "
                  f"uei={y['uei_pct']}% attr={y['attributed_pct']}% "
                  f"src={list(y['source_files'])[:2]}", file=sys.stderr)

    print("\n--- extracts vs prime ---", file=sys.stderr)
    tot_new = 0
    tot_usd = 0.0
    for e in ext:
        if "error" in e:
            print(e, file=sys.stderr)
            continue
        print(f"  {os.path.basename(e['path'])}: pre-2007 rows={e['pre_fy2007_rows']:,} "
              f"keys={e['pre_fy2007_distinct_keys_piid_fy_uei']:,} "
              f"exact_match={e['keys_matching_prime_exactly']:,} "
              f"NOT_in_prime={e['keys_NOT_in_prime']:,} "
              f"(${e['usd_on_unmatched']:,.0f}) "
              f"new_UEIs={e['distinct_uei_pre2007_ABSENT_from_prime_pre2007']:,}",
              file=sys.stderr)
        tot_new += e["keys_NOT_in_prime"]
        tot_usd += e["usd_on_unmatched"]
    print(f"\n  TOTAL pre-2007 keys not in prime_contracts.csv: {tot_new:,} "
          f"(${tot_usd:,.0f})", file=sys.stderr)


if __name__ == "__main__":
    main()
