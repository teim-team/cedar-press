"""561_pre2000_coverage_probe.py — READ-ONLY.

Measures whether transaction-level Native federal contracting data for
FY1981-FY1999 exists in files Cedar Press ALREADY HOLDS, before any network
route is considered.

Reads (never writes):
  data/raw/esm_hci/ESM/raw/Data Request 4-5-2023 File 1.csv   (HigherGov flag-at-award)
  data/raw/esm_hci/ESM/raw/Data Request 4-5-2023 File 2.csv   (HigherGov SAM-registration)
  data/raw/esm_hci/ESM/raw/Data Request 5-8-2023 IDVs.csv

Writes only  data/staging/pre2000_probe/*.json  (measurements, never dollars into
a shipped table).

SELECTION DECLARATION (docs/PULL_DISCIPLINE.md):
  These files were extracted BY HigherGov on the TYPE FILTER leg (FPDS Native
  business-type self-certification flags) plus, for File 2, current SAM
  registration.  No identifier leg.  Every row measured here therefore carries
  population_basis = 'type_filter'.  A flag-defined universe cannot measure what
  the flag misses; it is the right instrument only for "what does the flag FIND".
"""
import csv, json, sys, os, collections

csv.field_size_limit(2**31 - 1)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw", "esm_hci", "ESM", "raw")
OUT = os.path.join(ROOT, "data", "staging", "pre2000_probe")
os.makedirs(OUT, exist_ok=True)

FLAG_COLS = [
    "alaskan_native_corporation_owned_firm",
    "american_indian_owned_business",
    "indian_tribe_federally_recognized",
    "native_hawaiian_organization_owned_firm",
    "tribally_owned_firm",
    "native_american_owned_business",
    "us_tribal_government",
    "housing_authorities_public_tribal",
    "tribal_college",
    "alaskan_native_servicing_institution",
    "native_hawaiian_servicing_institution",
]
TRUE = {"t", "true", "y", "yes", "1"}


def probe(path, label):
    with open(path, newline="", encoding="utf-8", errors="replace") as fh:
        rd = csv.reader(fh)
        hdr = next(rd)
        ix = {c: i for i, c in enumerate(hdr)}
        i_fy = ix.get("action_date_fiscal_year")
        i_ad = ix.get("action_date")
        i_ob = ix.get("federal_action_obligation")
        i_nm = ix.get("recipient_name")
        i_uei = ix.get("uei_id")
        i_duns = ix.get("recipient_duns")
        i_cage = ix.get("cage_code")
        i_flags = [ix[c] for c in FLAG_COLS if c in ix]

        by_fy = collections.defaultdict(lambda: {"rows": 0, "obl": 0.0, "flag_rows": 0,
                                                 "flag_obl": 0.0, "has_uei": 0,
                                                 "has_duns": 0, "has_cage": 0})
        pre_names = collections.defaultdict(lambda: [0, 0.0])
        pre_ids = {"uei": set(), "duns": set(), "cage": set()}
        bad = 0
        n = 0
        for row in rd:
            n += 1
            if n % 200000 == 0:
                print(f"  {label}: {n:,}", file=sys.stderr, flush=True)
            try:
                fy = row[i_fy].strip()
                if not fy and i_ad is not None and row[i_ad][:4].isdigit():
                    y, m = int(row[i_ad][:4]), int(row[i_ad][5:7] or 1)
                    fy = str(y + (1 if m >= 10 else 0))
                fy = int(float(fy))
            except Exception:
                bad += 1
                continue
            try:
                ob = float(row[i_ob] or 0)
            except Exception:
                ob = 0.0
            d = by_fy[fy]
            d["rows"] += 1
            d["obl"] += ob
            flagged = any((row[j] or "").strip().lower() in TRUE for j in i_flags)
            if flagged:
                d["flag_rows"] += 1
                d["flag_obl"] += ob
            uei = (row[i_uei] or "").strip() if i_uei is not None else ""
            duns = (row[i_duns] or "").strip() if i_duns is not None else ""
            cage = (row[i_cage] or "").strip() if i_cage is not None else ""
            if uei:
                d["has_uei"] += 1
            if duns:
                d["has_duns"] += 1
            if cage:
                d["has_cage"] += 1
            if fy < 2000:
                nm = (row[i_nm] or "").strip().upper() if i_nm is not None else ""
                e = pre_names[nm]
                e[0] += 1
                e[1] += ob
                if uei:
                    pre_ids["uei"].add(uei)
                if duns:
                    pre_ids["duns"].add(duns)
                if cage:
                    pre_ids["cage"].add(cage)
    top = sorted(pre_names.items(), key=lambda kv: -kv[1][1])[:40]
    return {
        "file": os.path.basename(path),
        "rows_read": n,
        "unparseable_fy": bad,
        "by_fy": {str(k): {kk: (round(vv, 2) if isinstance(vv, float) else vv)
                           for kk, vv in v.items()} for k, v in sorted(by_fy.items())},
        "pre2000": {
            "rows": sum(v["rows"] for k, v in by_fy.items() if k < 2000),
            "obligations": round(sum(v["obl"] for k, v in by_fy.items() if k < 2000), 2),
            "flag_rows": sum(v["flag_rows"] for k, v in by_fy.items() if k < 2000),
            "flag_obligations": round(sum(v["flag_obl"] for k, v in by_fy.items() if k < 2000), 2),
            "distinct_recipient_names": len(pre_names),
            "distinct_uei": len(pre_ids["uei"]),
            "distinct_duns": len(pre_ids["duns"]),
            "distinct_cage": len(pre_ids["cage"]),
            "top_recipients_by_obligation": [
                {"recipient_name": k, "rows": v[0], "obligations": round(v[1], 2)}
                for k, v in top],
        },
        "population_basis": "type_filter",
    }


if __name__ == "__main__":
    targets = sys.argv[1:] or ["Data Request 4-5-2023 File 1.csv"]
    for t in targets:
        p = os.path.join(RAW, t)
        res = probe(p, t)
        slug = t.replace(" ", "_").replace(".csv", "")
        with open(os.path.join(OUT, f"{slug}_fy_profile.json"), "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=2)
        print(json.dumps({k: v for k, v in res.items() if k != "by_fy"}, indent=2)[:4000])
