#!/usr/bin/env python3
"""
16_federal_funding_recon.py
Cedar Press Dataset 3 (Federal Funding / assistance) -- reconciliation of two lineages.

LINEAGE A (hand-checked, reference standard):
    Cedar Press/Federal Spending/raw/Assistance_PrimeTransactions_2023-04-09_H19M53S53_1.csv
    Cedar Press/Federal Spending/clean/fed_funding_data_clean_corrtd.dta
LINEAGE B (automated expansion, read-only):
    dissertation/data/tribal_federal_spending/clean/*.csv

This script PROFILES ONLY. It does not merge. Zero fabrication: every number
written comes from a streaming read of the actual file.

Switches:
  --profile-a-raw    stream the 616MB USAspending assistance CSV
  --profile-a-dta    read the corrected Stata clean file (pyreadstat, chunked)
  --profile-b        profile the dissertation-corpus lineage
  --dropped          profile the dedup dropped-rows file (the $67B claim)
  --harvest          emit funding_identifier_harvest.csv
  --netnew           compare harvested UEIs against cedar_identifier_ledger_final.csv
  --all              everything
"""
import csv, json, os, sys, argparse, datetime, collections, re

csv.field_size_limit(10_000_000)

CEDAR = r"C:\Users\esm247\Desktop\Cedar Press"
DISS  = r"C:\Users\esm247\Desktop\dissertation\data\tribal_federal_spending"

A_RAW = os.path.join(CEDAR, "Federal Spending", "raw",
                     "Assistance_PrimeTransactions_2023-04-09_H19M53S53_1.csv")
A_DTA = os.path.join(CEDAR, "Federal Spending", "clean", "fed_funding_data_clean_corrtd.dta")
A_DTA_ORIG = os.path.join(CEDAR, "Federal Spending", "clean", "fed_funding_data_clean.dta")

B_AWARD   = os.path.join(DISS, "clean", "award_level_panel_research_ready_deduped.csv")
B_DROPPED = os.path.join(DISS, "clean", "award_level_panel_research_ready_deduped_dropped_rows.csv")
B_TY      = os.path.join(DISS, "clean", "tribe_year_research_ready_wide_deduped.csv")
B_MASTER  = os.path.join(DISS, "clean", "master_tribal_spending_panel.csv")
B_AWARD_PRE = os.path.join(DISS, "clean", "award_level_panel_research_ready.csv")

OUT   = os.path.join(CEDAR, "data", "clean")
INTER = os.path.join(CEDAR, "data", "raw", "external", "federal_funding")
LOG   = os.path.join(CEDAR, "logs", "16_federal_funding_recon_2026-08-05.log")
os.makedirs(INTER, exist_ok=True)

_logf = open(LOG, "a", encoding="utf-8")
TAG = os.environ.get("RECON_TAG", "run")
def log(msg):
    line = f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}][{TAG}] {msg}"
    print(line, flush=True)
    _logf.write(line + "\n"); _logf.flush()

def fnum(s):
    if s is None: return 0.0
    s = s.strip()
    if not s: return 0.0
    try: return float(s)
    except ValueError:
        try: return float(s.replace(",", ""))
        except ValueError: return 0.0

def dump(name, obj):
    p = os.path.join(INTER, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, default=str)
    log(f"wrote {p}")

# ------------------------------------------------------------------ LINEAGE A raw
def profile_a_raw(harvest=False):
    log("=== LINEAGE A raw: %s" % A_RAW)
    log("   size=%.1f MB  mtime=%s" % (os.path.getsize(A_RAW)/1e6,
        datetime.datetime.fromtimestamp(os.path.getmtime(A_RAW))))
    f = open(A_RAW, encoding="utf-8", errors="replace", newline="")
    rd = csv.reader(f); hdr = next(rd)
    I = {c: i for i, c in enumerate(hdr)}

    n = 0
    by_year_obl   = collections.Counter()
    by_year_rows  = collections.Counter()
    by_atype      = collections.Counter()   # code -> $
    by_atype_rows = collections.Counter()
    atype_desc    = {}
    by_biztype    = collections.Counter()
    by_agency     = collections.Counter()
    by_rectype    = collections.Counter()
    by_state_rows = collections.Counter()
    ueis, dunss, names, fains, txkeys = set(), set(), set(), set(), set()
    n_txkey_dupe = 0
    total_obl = 0.0
    loans_face = 0.0
    action_dates_min, action_dates_max = None, None
    # identifier harvest accumulator
    H = {}

    i_obl  = I["federal_action_obligation"]
    i_fy   = I["action_date_fiscal_year"]
    i_ad   = I["action_date"]
    i_uei  = I["recipient_uei"]
    i_duns = I["recipient_duns"]
    i_nm   = I["recipient_name"]
    i_st   = I["recipient_state_code"]
    i_city = I["recipient_city_name"]
    i_zip  = I["recipient_zip_code"]
    i_at   = I["assistance_type_code"]
    i_atd  = I["assistance_type_description"]
    i_bt   = I["business_types_description"]
    i_ag   = I["awarding_agency_name"]
    i_rt   = I["record_type_description"]
    i_fain = I["award_id_fain"]
    i_tk   = I["assistance_transaction_unique_key"]
    i_face = I["face_value_of_loan"]

    for row in rd:
        if len(row) != len(hdr):
            continue
        n += 1
        obl = fnum(row[i_obl])
        fy  = row[i_fy].strip()
        total_obl += obl
        by_year_obl[fy]  += obl
        by_year_rows[fy] += 1
        at = row[i_at].strip()
        by_atype[at] += obl
        by_atype_rows[at] += 1
        if at not in atype_desc: atype_desc[at] = row[i_atd].strip()
        by_biztype[row[i_bt].strip()[:120]] += 1
        by_agency[row[i_ag].strip()] += obl
        by_rectype[row[i_rt].strip()] += 1
        by_state_rows[row[i_st].strip()] += 1
        loans_face += fnum(row[i_face])
        ad = row[i_ad].strip()
        if ad:
            if action_dates_min is None or ad < action_dates_min: action_dates_min = ad
            if action_dates_max is None or ad > action_dates_max: action_dates_max = ad
        u = row[i_uei].strip(); d = row[i_duns].strip(); nm = row[i_nm].strip()
        if u: ueis.add(u)
        if d: dunss.add(d)
        if nm: names.add(nm)
        fa = row[i_fain].strip()
        if fa: fains.add(fa)
        tk = row[i_tk].strip()
        if tk in txkeys: n_txkey_dupe += 1
        else: txkeys.add(tk)

        if harvest:
            key = (u, "", d, nm.upper(), row[i_st].strip(), row[i_city].strip().upper(),
                   row[i_zip].strip())
            h = H.get(key)
            if h is None:
                h = H[key] = {"n": 0, "fy_min": None, "fy_max": None, "obl": 0.0,
                              "atypes": set()}
            h["n"] += 1; h["obl"] += obl
            if at: h["atypes"].add(at)
            if fy.isdigit():
                y = int(fy)
                if h["fy_min"] is None or y < h["fy_min"]: h["fy_min"] = y
                if h["fy_max"] is None or y > h["fy_max"]: h["fy_max"] = y
        if n % 250000 == 0:
            log(f"   ... {n:,} rows")
    f.close()

    res = {
        "file": A_RAW, "rows": n, "total_federal_action_obligation": total_obl,
        "total_face_value_of_loan": loans_face,
        "action_date_min": action_dates_min, "action_date_max": action_dates_max,
        "distinct_recipient_uei": len(ueis), "distinct_recipient_duns": len(dunss),
        "distinct_recipient_name": len(names), "distinct_award_id_fain": len(fains),
        "distinct_transaction_unique_key": len(txkeys),
        "duplicate_transaction_unique_key_rows": n_txkey_dupe,
        "by_fiscal_year": {k: {"rows": by_year_rows[k], "obligation": by_year_obl[k]}
                           for k in sorted(by_year_obl)},
        "by_assistance_type": {k: {"desc": atype_desc.get(k, ""),
                                   "rows": by_atype_rows[k], "obligation": by_atype[k]}
                               for k in sorted(by_atype)},
        "by_business_type_top40": by_biztype.most_common(40),
        "by_record_type": dict(by_rectype),
        "by_awarding_agency_top25": by_agency.most_common(25),
        "by_recipient_state_rows_top60": by_state_rows.most_common(60),
    }
    dump("profile_lineageA_raw.json", res)
    log(f"   A_raw rows={n:,} total_obl=${total_obl:,.0f} ueis={len(ueis):,} duns={len(dunss):,}")
    if harvest:
        return res, H
    return res, None

# ------------------------------------------------------------------ LINEAGE A dta
def profile_a_dta(path=A_DTA, tag="corrtd"):
    import pyreadstat
    log(f"=== LINEAGE A dta [{tag}]: {path}")
    log("   size=%.1f MB  mtime=%s" % (os.path.getsize(path)/1e6,
        datetime.datetime.fromtimestamp(os.path.getmtime(path))))
    _, meta = pyreadstat.read_dta(path, metadataonly=True)
    cols = list(meta.column_names)
    log(f"   n_rows(meta)={meta.number_rows:,} n_cols={len(cols)}")
    dump(f"lineageA_dta_{tag}_columns.json",
         {"file": path, "n_rows": meta.number_rows, "columns": cols,
          "value_labels_keys": list(meta.variable_value_labels.keys())})

    want = [c for c in ["tribe_id", "Tribe", "flag", "action_date_fiscal_year",
                        "federal_action_obligation", "assistance_type_code",
                        "recipient_uei", "recipient_duns", "recipient_name",
                        "recipient_state_code", "recipient_city_name",
                        "recipient_zip_code", "assistance_type_description",
                        "inflfac", "obligation2022", "total_obligated_amount",
                        "award_id_fain", "cfda_number", "awarding_agency_name"]
            if c in cols]
    log(f"   reading columns: {want}")
    n = 0
    by_year = collections.Counter(); by_year_rows = collections.Counter()
    by_atype = collections.Counter(); by_atype_rows = collections.Counter()
    by_year_flagged = collections.Counter()
    tribes = set(); tribe_ids = set(); ueis = set(); dunss = set(); names = set()
    tribe_id_name = {}
    flag_rows = 0; total = 0.0; total_unflagged = 0.0
    tid_missing_rows = 0
    by_year_kept = collections.Counter()
    reader = pyreadstat.read_file_in_chunks(pyreadstat.read_dta, path,
                                            chunksize=200000, usecols=want)
    for df, _m in reader:
        n += len(df)
        fy = df["action_date_fiscal_year"].astype("string").fillna("") if "action_date_fiscal_year" in df else None
        obl = df["federal_action_obligation"].fillna(0.0) if "federal_action_obligation" in df else None
        fl = df["flag"].fillna(0) if "flag" in df else None
        tid = df["tribe_id"] if "tribe_id" in df else None
        for c, s in (("recipient_uei", ueis), ("recipient_duns", dunss),
                     ("recipient_name", names)):
            if c in df:
                s.update(x for x in df[c].dropna().astype(str).unique() if x.strip())
        if "Tribe" in df:
            tribes.update(x for x in df["Tribe"].dropna().astype(str).unique() if x.strip())
        if tid is not None:
            tribe_ids.update(int(x) for x in tid.dropna().unique())
            tid_missing_rows += int(tid.isna().sum())
            if "Tribe" in df:
                sub = df[["tribe_id", "Tribe"]].dropna()
                for t, nm in zip(sub["tribe_id"], sub["Tribe"]):
                    tribe_id_name.setdefault(int(t), str(nm))
        if fy is not None and obl is not None:
            g = obl.groupby(fy).sum()
            for k, v in g.items(): by_year[k] += float(v)
            gr = obl.groupby(fy).size()
            for k, v in gr.items(): by_year_rows[k] += int(v)
            if fl is not None:
                keepmask = (fl == 0)
                g2 = obl[keepmask].groupby(fy[keepmask]).sum()
                for k, v in g2.items(): by_year_kept[k] += float(v)
                g3 = obl[~keepmask].groupby(fy[~keepmask]).sum()
                for k, v in g3.items(): by_year_flagged[k] += float(v)
        if "assistance_type_code" in df and obl is not None:
            at = df["assistance_type_code"].astype("string").fillna("")
            g = obl.groupby(at).sum()
            for k, v in g.items(): by_atype[k] += float(v)
            gr = obl.groupby(at).size()
            for k, v in gr.items(): by_atype_rows[k] += int(v)
        if obl is not None:
            total += float(obl.sum())
            if fl is not None: total_unflagged += float(obl[fl == 0].sum())
            if fl is not None: flag_rows += int((fl != 0).sum())
        log(f"   ... {n:,} rows")
    res = {"file": path, "rows": n, "total_obligation": total,
           "total_obligation_flag0": total_unflagged, "rows_flagged": flag_rows,
           "rows_tribe_id_missing": tid_missing_rows,
           "distinct_Tribe_strings": len(tribes), "distinct_tribe_id": len(tribe_ids),
           "tribe_id_min": min(tribe_ids) if tribe_ids else None,
           "tribe_id_max": max(tribe_ids) if tribe_ids else None,
           "distinct_recipient_uei": len(ueis), "distinct_recipient_duns": len(dunss),
           "distinct_recipient_name": len(names),
           "by_fiscal_year": {k: {"rows": by_year_rows[k], "obligation": by_year[k],
                                  "obligation_flag0": by_year_kept.get(k, 0.0),
                                  "obligation_flagged": by_year_flagged.get(k, 0.0)}
                              for k in sorted(by_year)},
           "by_assistance_type": {k: {"rows": by_atype_rows[k], "obligation": by_atype[k]}
                                  for k in sorted(by_atype)}}
    dump(f"profile_lineageA_dta_{tag}.json", res)
    with open(os.path.join(INTER, f"lineageA_tribe_id_names_{tag}.csv"), "w",
              encoding="utf-8", newline="") as fh:
        w = csv.writer(fh); w.writerow(["tribe_id", "example_Tribe_string"])
        for k in sorted(tribe_id_name): w.writerow([k, tribe_id_name[k]])
    log(f"   A_dta rows={n:,} total=${total:,.0f} tribe_ids={len(tribe_ids)}")
    return res

# ------------------------------------------------------------------ LINEAGE B
def profile_b_csv(path, label, obl_cols=None, year_col=None, harvest=False):
    log(f"=== LINEAGE B [{label}]: {path}")
    log("   size=%.1f MB  mtime=%s" % (os.path.getsize(path)/1e6,
        datetime.datetime.fromtimestamp(os.path.getmtime(path))))
    f = open(path, encoding="utf-8", errors="replace", newline="")
    rd = csv.reader(f); hdr = next(rd)
    I = {c: i for i, c in enumerate(hdr)}
    log(f"   cols({len(hdr)}): {hdr}")
    n = 0
    sums = collections.Counter()
    by_year = collections.defaultdict(lambda: collections.Counter())
    by_year_rows = collections.Counter()
    cat = collections.defaultdict(collections.Counter)
    setcols = {c: set() for c in
               ["recipient_uei", "recipient_duns", "recipient_name", "tribe_id",
                "tribe_name", "recipient_ein", "cage_code", "uei", "award_id",
                "award_id_fain", "source", "source_file", "data_source"]
               if c in I}
    catcols = [c for c in ["assistance_type", "assistance_type_code", "award_type",
                           "source", "data_source", "source_file", "spending_category",
                           "award_category", "agency", "awarding_agency_name",
                           "drop_reason", "dedup_reason", "reason", "entity_type",
                           "match_method", "match_type"] if c in I]
    obl_cols = obl_cols or [c for c in hdr if re.search(
        r"(obligat|amount|dollar|total_|_usd|federal_action|face_value|spending)", c, re.I)]
    obl_cols = [c for c in obl_cols if c in I]
    year_col = year_col or next((c for c in ["fiscal_year", "action_date_fiscal_year",
                                             "year", "fy", "first_seen_year"] if c in I), None)
    fam_col = next((c for c in ["award_type_family"] if c in I), None)
    fam_year = collections.defaultdict(lambda: collections.Counter())  # fam -> year -> $
    fam_year_rows = collections.defaultdict(collections.Counter)
    H = {}
    for row in rd:
        if len(row) != len(hdr): continue
        n += 1
        y = row[I[year_col]].strip() if year_col else ""
        by_year_rows[y] += 1
        for c in obl_cols:
            v = fnum(row[I[c]])
            sums[c] += v
            by_year[y][c] += v
        for c in catcols:
            cat[c][row[I[c]].strip()[:80]] += 1
        for c in setcols:
            v = row[I[c]].strip()
            if v: setcols[c].add(v)
        if fam_col:
            fam = row[I[fam_col]].strip()
            fam_year_rows[fam][y] += 1
            for c in obl_cols:
                fam_year[fam][y] += fnum(row[I[c]])
        if harvest:
            u  = row[I["recipient_uei"]].strip()  if "recipient_uei"  in I else (
                 row[I["uei"]].strip() if "uei" in I else "")
            d  = row[I["recipient_duns"]].strip() if "recipient_duns" in I else ""
            e  = row[I["recipient_ein"]].strip()  if "recipient_ein"  in I else ""
            nm = (row[I["recipient_name"]].strip() if "recipient_name" in I else (
                  row[I["legal_business_name"]].strip() if "legal_business_name" in I else ""))
            st = row[I["recipient_state_code"]].strip() if "recipient_state_code" in I else (
                 row[I["recipient_state"]].strip() if "recipient_state" in I else "")
            ci = row[I["recipient_city_name"]].strip() if "recipient_city_name" in I else (
                 row[I["recipient_city"]].strip() if "recipient_city" in I else "")
            zp = row[I["recipient_zip_code"]].strip() if "recipient_zip_code" in I else (
                 row[I["recipient_zip"]].strip() if "recipient_zip" in I else "")
            at = ""
            for c in ("assistance_type_code", "assistance_type", "award_type",
                      "award_type_family"):
                if c in I: at = row[I[c]].strip(); break
            ob = 0.0
            for c in ("federal_action_obligation", "total_obligation_usd",
                      "total_obligation", "obligated_usd", "obligation",
                      "total_obligated_amount", "amount"):
                if c in I: ob = fnum(row[I[c]]); break
            key = (u, e, d, nm.upper(), st, ci.upper(), zp)
            h = H.get(key)
            if h is None:
                h = H[key] = {"n": 0, "fy_min": None, "fy_max": None, "obl": 0.0,
                              "atypes": set()}
            h["n"] += 1; h["obl"] += ob
            if at: h["atypes"].add(at)
            if y.isdigit():
                yy = int(y)
                if h["fy_min"] is None or yy < h["fy_min"]: h["fy_min"] = yy
                if h["fy_max"] is None or yy > h["fy_max"]: h["fy_max"] = yy
        if n % 250000 == 0: log(f"   ... {n:,} rows")
    f.close()
    res = {"file": path, "label": label, "rows": n, "columns": hdr,
           "year_col": year_col, "obligation_cols": obl_cols,
           "column_sums": dict(sums),
           "by_year": {k: dict(v) | {"rows": by_year_rows[k]} for k, v in sorted(by_year.items())},
           "distinct": {k: len(v) for k, v in setcols.items()},
           "by_family_year": {f: {y: {"obligation": v, "rows": fam_year_rows[f][y]}
                                  for y, v in sorted(d.items())}
                              for f, d in sorted(fam_year.items())},
           "categoricals": {c: cat[c].most_common(40) for c in catcols}}
    dump(f"profile_lineageB_{label}.json", res)
    log(f"   B[{label}] rows={n:,} sums={ {k: round(v) for k, v in sums.items()} }")
    if harvest: return res, H
    return res, None

# ------------------------------------------------------------------ harvest writer
MAL_UEI  = re.compile(r"^[A-Z0-9]{12}$")
MAL_DUNS = re.compile(r"^[0-9]{9}$")
MAL_EIN  = re.compile(r"^[0-9]{2}-?[0-9]{7}$")

def write_harvest(HA, HB, path):
    """One row per distinct identifier OBSERVATION.

    Key = (uei, ein, duns, recipient_name, state, city, zip) exactly as observed.
    source_lineage is decided by whether the (uei, ein, duns) TRIPLE is seen in
    each lineage -- not by whether the whole observation tuple matches, because
    lineage B carries no duns/ein/city/zip at all and would never tie.
    Values are emitted verbatim: no zero-stripping, no case folding, no repair.
    """
    log("=== building funding_identifier_harvest.csv")
    tripA = {(k[0], k[1], k[2]) for k in HA}
    tripB = {(k[0], k[1], k[2]) for k in HB}
    log(f"   lineage A (uei,ein,duns) triples: {len(tripA):,}")
    log(f"   lineage B (uei,ein,duns) triples: {len(tripB):,}")
    log(f"   triples in BOTH lineages         : {len(tripA & tripB):,}")
    rows = []
    for store, lin_self, srcfile in ((HA, "A", os.path.basename(A_RAW)),
                                     (HB, "B", os.path.basename(B_AWARD))):
        other = tripB if lin_self == "A" else tripA
        for k, v in store.items():
            uei, ein, duns, nm, st, city, zp = k
            lin = "both" if (uei, ein, duns) in other else lin_self
            mal = []
            if uei and not MAL_UEI.match(uei): mal.append("uei_format")
            if duns and not MAL_DUNS.match(duns): mal.append("duns_format")
            if ein and not MAL_EIN.match(ein): mal.append("ein_format")
            if not uei and not duns and not ein: mal.append("no_identifier")
            rows.append([uei, duns, ein, "", nm, st, city, zp, v["n"],
                         v["fy_min"] if v["fy_min"] is not None else "",
                         v["fy_max"] if v["fy_max"] is not None else "",
                         round(v["obl"], 2), "|".join(sorted(v["atypes"])),
                         lin, srcfile, "|".join(mal)])
    rows.sort(key=lambda r: (-r[11], r[4]))
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["recipient_uei", "recipient_duns", "recipient_ein", "cage_code",
                    "recipient_name", "recipient_state", "recipient_city",
                    "recipient_zip", "n_awards", "first_year", "last_year",
                    "total_obligated_usd", "assistance_types", "source_lineage",
                    "source_file", "malformed_flag"])
        w.writerows(rows)
    log(f"   wrote {path}: {len(rows):,} identifier-observation rows")
    ueis = {r[0] for r in rows if r[0]}
    duns = {r[1] for r in rows if r[1]}
    eins = {r[2] for r in rows if r[2]}
    log(f"   distinct UEI={len(ueis):,}  DUNS={len(duns):,}  EIN={len(eins):,}")
    return ueis, duns, eins

def netnew(ueis):
    led = os.path.join(CEDAR, "data", "clean", "cedar_identifier_ledger_final.csv")
    log(f"=== net-new check against {led} (read-only)")
    # ledger is LONG format: identifier_type / identifier
    have = set(); types = collections.Counter()
    with open(led, encoding="utf-8", errors="replace", newline="") as f:
        for row in csv.DictReader(f):
            t = (row.get("identifier_type") or "").strip().upper()
            v = (row.get("identifier") or "").strip()
            types[t] += 1
            if t == "UEI" and v and v.upper() not in ("NA", "NAN", "NONE"):
                have.add(v.upper())
    log(f"   ledger identifier_type counts: {dict(types)}")
    log(f"   ledger distinct UEI values: {len(have):,}")
    new = {u for u in ueis if u.upper() not in have}
    log(f"   funding-harvest distinct UEI: {len(ueis):,}")
    log(f"   NET NEW UEIs not in cedar_identifier_ledger_final.csv: {len(new):,}")
    with open(os.path.join(OUT, "funding_identifier_netnew_ueis.csv"), "w",
              encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["recipient_uei"])
        for u in sorted(new): w.writerow([u])
    return len(have), len(new)

# ------------------------------------------------------------------ main
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    for s in ["profile-a-raw", "profile-a-dta", "profile-b", "dropped", "harvest",
              "netnew", "all"]:
        ap.add_argument("--" + s, action="store_true")
    a = ap.parse_args()
    log("#" * 70)
    log("RUN 16_federal_funding_recon.py args=%s" % vars(a))
    HA = HB = None
    if a.all or a.profile_a_raw or a.harvest:
        _, HA = profile_a_raw(harvest=(a.all or a.harvest))
    if a.all or a.profile_a_dta:
        profile_a_dta(A_DTA, "corrtd")
    if a.all or a.profile_b or a.harvest:
        _, HB = profile_b_csv(B_AWARD, "award_deduped", harvest=(a.all or a.harvest))
    if a.all or a.profile_b:
        profile_b_csv(B_TY, "tribe_year_wide_deduped")
        profile_b_csv(B_MASTER, "master_tribal_spending_panel")
    if a.all or a.dropped:
        profile_b_csv(B_DROPPED, "dedup_dropped_rows")
    if a.all or a.harvest:
        ueis, _, _ = write_harvest(HA or {}, HB or {},
                                   os.path.join(OUT, "funding_identifier_harvest.csv"))
        if a.all or a.netnew:
            netnew(ueis)
    log("DONE")
