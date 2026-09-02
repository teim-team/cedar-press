"""564_benchmark_reconciliation.py — READ-ONLY single pass over prime_contracts.csv.

Two jobs:
  (1) reconcile Cedar's attributed prime total to CICD's published $202B
      (1981-2021, 2021 dollars, $198B prime + $4B sub) on a like-for-like
      basis, using the deflator ALREADY on the table rather than a new one;
  (2) characterise the unattributed pool (attributed_flag = 0) so that 503/510
      and the owner's rulings have ranked evidence to work from.

It NEVER attributes anything and never writes a dollar figure into a shipped
table.  Output is data/staging/pre2000_probe/benchmark_reconciliation.json.
"""
import csv, json, os, sys, collections

csv.field_size_limit(2**31 - 1)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "clean", "prime_contracts.csv")
OUT = os.path.join(ROOT, "data", "staging", "pre2000_probe")

FLAGCOLS = ["reported_8a", "reported_buy_indian", "reported_indian_business",
            "reported_native_preference"]
TRUE = {"1", "true", "t", "y", "yes"}


def f(x):
    try:
        return float(x)
    except Exception:
        return 0.0


def main():
    os.makedirs(OUT, exist_ok=True)
    fy = collections.defaultdict(lambda: {
        "rows": 0, "obl": 0.0, "real2025": 0.0,
        "att_rows": 0, "att_obl": 0.0, "att_real2025": 0.0,
        "unatt_rows": 0, "unatt_obl": 0.0})
    tier = collections.Counter()
    tier_obl = collections.Counter()
    defl_by_fy = {}
    # unattributed characterisation
    un_awardee = collections.defaultdict(lambda: {
        "rows": 0, "obl": 0.0, "uei": set(), "cage": set(), "fy": set(),
        "method": collections.Counter(), "tier": collections.Counter(),
        "ruling": collections.Counter(), "nativeflag_rows": 0,
        "agency": collections.Counter()})
    un_method = collections.Counter()
    un_ruling = collections.Counter()
    un_has_uei = 0
    un_has_cage = 0
    un_nativeflag_rows = 0
    un_nativeflag_obl = 0.0
    pre2000 = 0

    with open(SRC, newline="", encoding="utf-8", errors="replace") as fh:
        rd = csv.DictReader(fh)
        n = 0
        for r in rd:
            n += 1
            if n % 200000 == 0:
                print(f"  {n:,}", file=sys.stderr, flush=True)
            try:
                y = int(float(r["fiscal_year"]))
            except Exception:
                continue
            ob = f(r["total_obligations"])
            rl = f(r.get("total_obligations_real2025"))
            d = fy[y]
            d["rows"] += 1
            d["obl"] += ob
            d["real2025"] += rl
            if (r.get("deflator_factor_2025") or "").strip() and y not in defl_by_fy:
                defl_by_fy[y] = f(r["deflator_factor_2025"])
            if (r.get("pre_2000_flag") or "").strip() in TRUE:
                pre2000 += 1
            att = (r.get("attributed_flag") or "").strip() in TRUE
            t = (r.get("confidence_tier") or "").strip() or "(blank)"
            tier[t] += 1
            tier_obl[t] += ob
            nat = any((r.get(c) or "").strip() in TRUE for c in FLAGCOLS)
            if att:
                d["att_rows"] += 1
                d["att_obl"] += ob
                d["att_real2025"] += rl
            else:
                d["unatt_rows"] += 1
                d["unatt_obl"] += ob
                nm = (r.get("awardee_name") or "").strip().upper() or "(blank)"
                e = un_awardee[nm]
                e["rows"] += 1
                e["obl"] += ob
                if r.get("awardee_uei"):
                    e["uei"].add(r["awardee_uei"].strip())
                    un_has_uei += 1
                if r.get("cage_code"):
                    e["cage"].add(r["cage_code"].strip())
                    un_has_cage += 1
                e["fy"].add(y)
                e["method"][(r.get("attribution_method") or "").strip() or "(blank)"] += 1
                e["tier"][t] += 1
                e["ruling"][(r.get("ruling_status") or "").strip() or "(blank)"] += 1
                e["agency"][(r.get("funding_agency") or "").strip() or "(blank)"] += 1
                un_method[(r.get("attribution_method") or "").strip() or "(blank)"] += 1
                un_ruling[(r.get("ruling_status") or "").strip() or "(blank)"] += 1
                if nat:
                    e["nativeflag_rows"] += 1
                    un_nativeflag_rows += 1
                    un_nativeflag_obl += ob

    top = sorted(un_awardee.items(), key=lambda kv: -kv[1]["obl"])[:60]
    res = {
        "source": SRC,
        "rows_read": n,
        "pre_2000_flag_set_on_rows": pre2000,
        "fiscal_year_min": min(fy),
        "fiscal_year_max": max(fy),
        "deflator_factor_2025_by_fy": {str(k): round(v, 6) for k, v in sorted(defl_by_fy.items())},
        "by_fy": {str(k): {kk: (round(vv, 2) if isinstance(vv, float) else vv)
                           for kk, vv in v.items()} for k, v in sorted(fy.items())},
        "confidence_tier_rows": dict(tier.most_common()),
        "confidence_tier_obligations": {k: round(v, 2) for k, v in tier_obl.most_common()},
        "unattributed": {
            "rows": sum(v["unatt_rows"] for v in fy.values()),
            "obligations": round(sum(v["unatt_obl"] for v in fy.values()), 2),
            "distinct_awardee_names": len(un_awardee),
            "rows_with_uei": un_has_uei,
            "rows_with_cage": un_has_cage,
            "rows_carrying_a_native_setaside_flag": un_nativeflag_rows,
            "obligations_carrying_a_native_setaside_flag": round(un_nativeflag_obl, 2),
            "attribution_method": dict(un_method.most_common(20)),
            "ruling_status": dict(un_ruling.most_common(20)),
            "top_60_awardees_by_obligation": [
                {"awardee_name": k,
                 "rows": v["rows"],
                 "obligations": round(v["obl"], 2),
                 "fy_min": min(v["fy"]), "fy_max": max(v["fy"]),
                 "distinct_uei": sorted(v["uei"])[:4],
                 "n_uei": len(v["uei"]),
                 "distinct_cage": sorted(v["cage"])[:4],
                 "rows_with_native_setaside_flag": v["nativeflag_rows"],
                 "attribution_method": dict(v["method"].most_common(3)),
                 "confidence_tier": dict(v["tier"].most_common(3)),
                 "ruling_status": dict(v["ruling"].most_common(3)),
                 "top_funding_agency": dict(v["agency"].most_common(2))}
                for k, v in top],
        },
    }
    with open(os.path.join(OUT, "benchmark_reconciliation.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2)
    print("WROTE", os.path.join(OUT, "benchmark_reconciliation.json"))


if __name__ == "__main__":
    main()
