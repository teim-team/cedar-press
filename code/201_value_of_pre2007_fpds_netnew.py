"""
201_value_of_pre2007_fpds_netnew.py
===================================
Cedar Press. Written 2026-08-26.

Script 198 found 31,500 pre-FY2007 (PIID, FY, UEI) keys carrying $9.83B that
are on disk in the HigherGov FPDS extracts and absent from
`data/clean/prime_contracts.csv`, plus 1,074 pre-2007 UEIs the clean prime table
has never seen in that window.

THIS SCRIPT ANSWERS: how much of that is NATIVE, and at what tier?

A row is only worth merging if it reaches a Native entity. The test is the
identifier ledger -- and per START_HERE.md's first standing rule, **a tier is
INHERITED from the ledger row, never assigned here**. An exact UEI join onto a
tier-B row is still tier B.

Also measures the pre-FY2000 window, which `prime_contracts.csv` does not cover
at all (its earliest fiscal_year is 2000).

READ-ONLY. One JSON to docs/. Zero network requests. Does not write, merge, or
propose a merge -- this is a valuation, not a build.

Run:  py -3 code/201_value_of_pre2007_fpds_netnew.py
"""

import csv
import json
import os
import sys
import collections
from datetime import datetime, timezone

csv.field_size_limit(10 ** 9)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "data", "clean", "cedar_identifier_ledger_final.csv")
PRIME = os.path.join(ROOT, "data", "clean", "prime_contracts.csv")
OUT = os.path.join(ROOT, "docs", "PRE2007_FPDS_NETNEW_VALUE.json")

FPDS_FILES = [
    os.path.join(ROOT, "data", "raw", "esm_hci", "ESM", "raw",
                 "Data Request 4-5-2023 File 1.csv"),
    os.path.join(ROOT, "data", "raw", "esm_hci", "ESM", "raw",
                 "Data Request 4-5-2023 File 2.csv"),
    os.path.join(ROOT, "data", "raw", "esm_hci", "ESM", "raw",
                 "Data Request 5-8-2023 IDVs.csv"),
]
CUTOFF = 2007


def load_ledger():
    """UEI -> (best tier, methods, entity ids). Tier is INHERITED, never assigned."""
    uei = {}
    if not os.path.exists(LEDGER):
        return uei, {"error": "ledger not found"}
    order = {"A": 0, "B": 1, "C": 2, "X": 3}
    stats = collections.Counter()
    with open(LEDGER, encoding="utf-8", errors="replace", newline="") as f:
        rd = csv.DictReader(f)
        for r in rd:
            if (r.get("identifier_type") or "").strip().upper() != "UEI":
                continue
            k = (r.get("identifier") or "").strip().upper()
            if not k:
                continue
            t = (r.get("confidence_tier") or "").strip().upper()
            stats[t] += 1
            cur = uei.get(k)
            if cur is None or order.get(t, 9) < order.get(cur["tier"], 9):
                uei[k] = {
                    "tier": t,
                    "method": (r.get("attribution_method") or "").strip(),
                    "entity": (r.get("tribe_id") or r.get("entity_id") or "").strip(),
                    "name": (r.get("canonical_name") or "").strip(),
                }
    return uei, dict(stats)


def load_prime_pre_keys():
    keys = set()
    piid_fy = set()
    min_fy = None
    with open(PRIME, encoding="utf-8", errors="replace", newline="") as f:
        rd = csv.reader(f)
        hdr = next(rd)
        ix = {h: i for i, h in enumerate(hdr)}
        for row in rd:
            if len(row) < len(hdr):
                continue
            fy = row[ix["fiscal_year"]].strip()
            if fy.isdigit():
                v = int(fy)
                min_fy = v if min_fy is None else min(min_fy, v)
            if fy.isdigit() and int(fy) < CUTOFF:
                p = row[ix["contract_number"]].strip().upper()
                u = row[ix["awardee_uei"]].strip().upper()
                if p:
                    keys.add((p, fy, u))
                    piid_fy.add((p, fy))
    return keys, piid_fy, min_fy


def main():
    print("[1/3] ledger ...", file=sys.stderr)
    ledger, lstats = load_ledger()
    print(f"  ledger UEI keys: {len(ledger):,}  tiers: {lstats}", file=sys.stderr)

    print("[2/3] prime pre-2007 keys ...", file=sys.stderr)
    pkeys, ppiid, prime_min_fy = load_prime_pre_keys()
    print(f"  {len(pkeys):,} keys; prime min fiscal_year = {prime_min_fy}",
          file=sys.stderr)

    print("[3/3] scanning extracts ...", file=sys.stderr)
    # net-new pre-2007, bucketed by inherited ledger tier
    tier_rows = collections.Counter()
    tier_usd = collections.defaultdict(float)
    tier_ueis = collections.defaultdict(set)
    entities = collections.Counter()
    entity_usd = collections.defaultdict(float)
    # pre-FY2000 window, which prime does not cover at all
    pre2000_rows = 0
    pre2000_usd = 0.0
    pre2000_tierA_rows = 0
    pre2000_tierA_usd = 0.0
    pre2000_years = collections.Counter()
    by_file = {}

    for path in FPDS_FILES:
        f = open(path, encoding="utf-8", errors="replace", newline="")
        rd = csv.reader(f)
        hdr = next(rd)
        ix = {}
        for i, h in enumerate(hdr):
            if h not in ix:
                ix[h] = i
        need = ["action_date_fiscal_year", "award_id_piid", "uei_id",
                "federal_action_obligation", "uei_legal_business_name"]
        maxi = max(ix[c] for c in need)
        fstat = collections.Counter()
        fusd = collections.defaultdict(float)
        n = 0
        for row in rd:
            if len(row) <= maxi:
                continue
            n += 1
            fy = row[ix["action_date_fiscal_year"]].strip()
            if not fy.isdigit():
                continue
            fyi = int(fy)
            if fyi >= CUTOFF:
                if n % 250000 == 0:
                    print(f"  ...{os.path.basename(path)} {n:,}", file=sys.stderr)
                continue
            p = row[ix["award_id_piid"]].strip().upper()
            u = row[ix["uei_id"]].strip().upper()
            try:
                d = float(row[ix["federal_action_obligation"]] or 0)
            except ValueError:
                d = 0.0
            led = ledger.get(u)
            tier = led["tier"] if led else "(no ledger link)"

            if fyi < 2000:
                pre2000_rows += 1
                pre2000_usd += d
                pre2000_years[fy] += 1
                if tier == "A":
                    pre2000_tierA_rows += 1
                    pre2000_tierA_usd += d

            k = (p, fy, u)
            if k in pkeys or (p, fy) in ppiid:
                continue                       # already in the clean table
            tier_rows[tier] += 1
            tier_usd[tier] += d
            if u:
                tier_ueis[tier].add(u)
            fstat[tier] += 1
            fusd[tier] += d
            if led and led["tier"] in ("A", "B") and led["entity"]:
                entities[(led["entity"], led["name"], led["tier"])] += 1
                entity_usd[(led["entity"], led["name"], led["tier"])] += d
            if n % 250000 == 0:
                print(f"  ...{os.path.basename(path)} {n:,}", file=sys.stderr)
        f.close()
        by_file[os.path.basename(path)] = {
            "netnew_rows_by_inherited_tier": dict(fstat),
            "netnew_usd_by_inherited_tier": {k: round(v, 2) for k, v in fusd.items()},
        }

    top_ent = sorted(entities.items(), key=lambda kv: -entity_usd[kv[0]])[:25]

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "script": "code/201_value_of_pre2007_fpds_netnew.py",
        "network_requests_issued": 0,
        "tier_policy": ("Tier is INHERITED from cedar_identifier_ledger_final.csv, "
                        "never assigned here. An exact UEI join onto a tier-B row "
                        "is still tier B (START_HERE.md standing rule 1)."),
        "ledger_uei_keys": len(ledger),
        "ledger_tier_counts": lstats,
        "prime_min_fiscal_year": prime_min_fy,
        "netnew_pre2007": {
            "rows_by_inherited_tier": dict(tier_rows),
            "usd_by_inherited_tier": {k: round(v, 2) for k, v in tier_usd.items()},
            "distinct_uei_by_inherited_tier": {k: len(v) for k, v in tier_ueis.items()},
            "total_rows": sum(tier_rows.values()),
            "total_usd": round(sum(tier_usd.values()), 2),
        },
        "netnew_by_source_file": by_file,
        "pre_fy2000_window": {
            "note": ("prime_contracts.csv min fiscal_year is %s, so this window "
                     "is absent from the clean table entirely." % prime_min_fy),
            "rows": pre2000_rows,
            "usd": round(pre2000_usd, 2),
            "rows_on_tier_A_ledger_uei": pre2000_tierA_rows,
            "usd_on_tier_A_ledger_uei": round(pre2000_tierA_usd, 2),
            "rows_by_fiscal_year": dict(sorted(pre2000_years.items())),
        },
        "top_netnew_entities_tierAB": [
            {"entity_id": e, "name": nm, "inherited_tier": t,
             "netnew_rows": c, "netnew_usd": round(entity_usd[(e, nm, t)], 2)}
            for (e, nm, t), c in top_ent
        ],
    }

    tmp = OUT + ".part"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
    os.replace(tmp, OUT)
    with open(OUT, encoding="utf-8") as fh:
        back = json.load(fh)
    assert back["script"] == report["script"], "re-read verification FAILED"
    print(f"\nwrote + verified {OUT}", file=sys.stderr)

    nn = report["netnew_pre2007"]
    print(f"\nNET-NEW pre-FY2007 rows: {nn['total_rows']:,}  "
          f"${nn['total_usd']:,.0f}", file=sys.stderr)
    for t in sorted(nn["rows_by_inherited_tier"], key=lambda x: str(x)):
        print(f"  inherited tier {t:<18} rows={nn['rows_by_inherited_tier'][t]:>7,} "
              f"${nn['usd_by_inherited_tier'][t]:>16,.0f} "
              f"uei={nn['distinct_uei_by_inherited_tier'][t]:>5,}", file=sys.stderr)
    p2 = report["pre_fy2000_window"]
    print(f"\npre-FY2000 (absent from prime entirely): rows={p2['rows']:,} "
          f"${p2['usd']:,.0f}; on tier-A ledger UEIs: {p2['rows_on_tier_A_ledger_uei']:,} "
          f"(${p2['usd_on_tier_A_ledger_uei']:,.0f})", file=sys.stderr)
    print("\ntop net-new entities (tier A/B, inherited):", file=sys.stderr)
    for e in report["top_netnew_entities_tierAB"][:12]:
        print(f"  [{e['inherited_tier']}] {(e['name'] or e['entity_id'])[:46]:<46} "
              f"rows={e['netnew_rows']:>6,} ${e['netnew_usd']:>14,.0f}",
              file=sys.stderr)


if __name__ == "__main__":
    main()
