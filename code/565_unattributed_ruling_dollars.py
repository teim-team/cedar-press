"""565_unattributed_ruling_dollars.py — READ-ONLY.

564 counted the unattributed pool's ruling_status by ROW.  The question that
decides what the $65.2B means is the DOLLAR split: a row already
RULED_NOT_NATIVE will never attribute, a row RULED_CLASS_ONLY is Native but
has no named owner, and a blank row has never been looked at.  Those are three
different findings and they must not be reported as one number.

Writes only data/staging/pre2000_probe/unattributed_ruling_dollars.json.
It rules on nothing.
"""
import csv, json, os, sys, collections

csv.field_size_limit(2**31 - 1)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "clean", "prime_contracts.csv")
OUT = os.path.join(ROOT, "data", "staging", "pre2000_probe")
TRUE = {"1", "true", "t", "y", "yes"}
FLAGS = ["reported_8a", "reported_buy_indian", "reported_indian_business",
         "reported_native_preference"]

with open(SRC, newline="", encoding="utf-8", errors="replace") as fh:
    rd = csv.reader(fh)
    h = next(rd)
    ix = {c: i for i, c in enumerate(h)}
    iA, iO, iR, iN, iU, iF = (ix["attributed_flag"], ix["total_obligations"],
                              ix["ruling_status"], ix["awardee_name"],
                              ix["awardee_uei"], ix["fiscal_year"])
    iFl = [ix[c] for c in FLAGS]
    iSA = ix["setaside"]
    by_ruling = collections.defaultdict(lambda: {"rows": 0, "obl": 0.0, "uei": set()})
    by_ruling_flag = collections.defaultdict(lambda: {"rows": 0, "obl": 0.0})
    setaside = collections.defaultdict(lambda: {"rows": 0, "obl": 0.0})
    unruled_top = collections.defaultdict(lambda: [0, 0.0, set(), 0])
    n = 0
    for r in rd:
        n += 1
        if n % 300000 == 0:
            print(n, file=sys.stderr, flush=True)
        if r[iA].strip() in TRUE:
            continue
        try:
            ob = float(r[iO] or 0)
        except Exception:
            ob = 0.0
        rs = (r[iR] or "").strip() or "(never ruled)"
        d = by_ruling[rs]
        d["rows"] += 1
        d["obl"] += ob
        if r[iU]:
            d["uei"].add(r[iU].strip())
        nat = any((r[j] or "").strip() in TRUE for j in iFl)
        k = (rs, "native_setaside" if nat else "no_native_setaside")
        by_ruling_flag[k]["rows"] += 1
        by_ruling_flag[k]["obl"] += ob
        sa = (r[iSA] or "").strip() or "(blank)"
        setaside[sa]["rows"] += 1
        setaside[sa]["obl"] += ob
        if rs == "(never ruled)":
            e = unruled_top[(r[iN] or "").strip().upper()]
            e[0] += 1
            e[1] += ob
            if r[iU]:
                e[2].add(r[iU].strip())
            if nat:
                e[3] += 1

res = {
    "unattributed_rows": sum(v["rows"] for v in by_ruling.values()),
    "unattributed_obligations": round(sum(v["obl"] for v in by_ruling.values()), 2),
    "by_ruling_status": {k: {"rows": v["rows"], "obligations": round(v["obl"], 2),
                             "distinct_uei": len(v["uei"])}
                         for k, v in sorted(by_ruling.items(), key=lambda kv: -kv[1]["obl"])},
    "by_ruling_status_x_native_setaside": {
        f"{k[0]} | {k[1]}": {"rows": v["rows"], "obligations": round(v["obl"], 2)}
        for k, v in sorted(by_ruling_flag.items(), key=lambda kv: -kv[1]["obl"])},
    "by_setaside": {k: {"rows": v["rows"], "obligations": round(v["obl"], 2)}
                    for k, v in sorted(setaside.items(), key=lambda kv: -kv[1]["obl"])},
    "never_ruled_top_50_awardees": [
        {"awardee_name": k, "rows": v[0], "obligations": round(v[1], 2),
         "n_uei": len(v[2]), "uei": sorted(v[2])[:3],
         "rows_with_native_setaside_flag": v[3]}
        for k, v in sorted(unruled_top.items(), key=lambda kv: -kv[1][1])[:50]],
    "never_ruled_distinct_awardees": len(unruled_top),
}
os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "unattributed_ruling_dollars.json"), "w", encoding="utf-8") as fh:
    json.dump(res, fh, indent=2)
print(json.dumps({k: v for k, v in res.items() if not k.startswith("never_ruled_top")}, indent=2))
