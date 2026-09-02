#!/usr/bin/env python3
"""872 - promote joinable geographic keys onto the ASSISTANCE tables (ADR-015).

WHAT IT WRITES ONTO WHAT
------------------------
    data/clean/federal_funding_transactions.csv        701,955 rows  FY2007-2026
    data/clean/faads_transactions_all_agencies.csv   2,769,748 rows  FY2001-2007

Both in place, both backed up first, both proven row- and money-conserving.
`faads_transactions_all_agencies.csv` is the single largest table in Cedar and,
before this script, carried a city / state / zip on nearly every row and a
joinable key on none of them.

THE SOURCE ADR-015 DID NOT KNOW ABOUT
-------------------------------------
ADR-015 names one corpus, `usaspending_gapfill_2026-08-05`, and says the unlock
is there. For contracts it is. For assistance it is not the best route and for
FAADS it is barely a route at all: the gapfill assistance slice is 9,821 award
rows over five CFDA programmes.

The better source was already on disk and unlisted. USAspending's prime
TRANSACTION schema carries the same two county-fips columns at TRANSACTION
grain, and Cedar holds it in three places:

    data/raw/federal_funding/usaspending_2023_2026/       FY2023-2026
    data/raw/federal_funding/usaspending_credit_2026-08-06/  credit instruments
    data/raw/external/faads/{agencies,seam}/              FY2007 + DOI FY2001-11

Transaction grain is strictly better than award grain here. An award summary
gives one county for an award that may run years; the transaction record gives
the county as of that action. Where a transaction key resolves, this script
uses it and does not fall back to the award summary.

WHAT DOES NOT RESOLVE, AND WHY - stated here because it is most of the table
---------------------------------------------------------------------------
1. `faads_transactions_all_agencies.csv` carries
   `assistance_transaction_unique_key` on 825,754 of its 2,769,748 rows (29.8%).
   The other 70% never got one: `30_funding_pre2008.to_out_row` did not carry
   the column, as MONEY_TOTALLING_RULES already records, and the re-extract that
   would restore it is queued and unrun. Those rows are keyed by PLACE or not at
   all. This is the largest single ceiling on the geography axis and it is a
   MAPPER defect, not a source defect -- the key is in the staged zips.
2. Of the FAADS archive zips, only the twelve `*_fy2007_archive.zip` and the
   eleven DOI `seam/doi_fy*.zip` carry the county columns. The FY2001-2006
   per-agency pulls use an older extract schema with no county fips at all. No
   amount of local work fixes that; it needs a re-pull.

TWO COLUMNS, NEVER ONE (ADR-015 rule 1). `geo_recipient_county_fips` and
`geo_pop_county_fips` are kept apart on both tables and neither is ever filled
from the other.

TIERS, strongest first
----------------------
    exact_transaction     the federal TRANSACTION record named this county for
                          this exact transaction key. No inference.
    exact_award_summary   the federal AWARD SUMMARY named it for the award this
                          transaction belongs to. Exact, one grain coarser.
    derived_place_zip5    the row's own zip5, resolved to its modal county in
                          geo_place_county_crosswalk.csv.
    derived_place_modal   the row's own city+state, same lookup, coarser and
                          much more often ambiguous.

`geo_*_place_dominance_share` and `geo_*_place_ambiguous` are written on the two
derived tiers so a consumer can set its own threshold. ZCTAs cross county lines
and cities cross them constantly; a derived key is a best guess with its own
confidence attached, never a fact.

MODES
-----
    py -3 code/872_promote_geo_keys_assistance.py           promote in place
    py -3 code/872_promote_geo_keys_assistance.py verify    re-measure and assert
    py -3 code/872_promote_geo_keys_assistance.py selftest  prove verify fires

INVARIANTS (verify exits 1 on any failure)
------------------------------------------
  I1 ROW CONSERVATION to the row against the pre-run backup.
  I2 MONEY CONSERVATION to the cent against the pre-run backup.
  I3 COLUMN CONSERVATION: no column present in the backup is missing after.
  I4 every non-empty county fips is 5 digits and starts with its own state fips.
  I5 tier and fips agree on every row: no tier without a fips, no fips without
     a tier, and no `derived_*` row without a dominance share.
"""

import csv
import io
import json
import os
import shutil
import sys
import zipfile
from collections import Counter

csv.field_size_limit(10 * 1024 * 1024)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN = os.path.join(ROOT, "data", "clean")
XWALK_AWARD = os.path.join(CLEAN, "geo_award_county_crosswalk.csv")
XWALK_PLACE = os.path.join(CLEAN, "geo_place_county_crosswalk.csv")
OUT_STATS = os.path.join(ROOT, "docs", "GEO_PROMOTION_ASSISTANCE.json")
STAMP = "2026-09-02"

FFT = os.path.join(CLEAN, "federal_funding_transactions.csv")
FAADS = os.path.join(CLEAN, "faads_transactions_all_agencies.csv")
BAK_FFT = FFT + f".bak_{STAMP}_pre872_promote_geo_keys_assistance"
BAK_FAADS = FAADS + f".bak_{STAMP}_pre872_promote_geo_keys_assistance"

TXN_DIRS = [
    os.path.join(ROOT, "data", "raw", "federal_funding", "usaspending_2023_2026"),
    os.path.join(ROOT, "data", "raw", "federal_funding", "usaspending_credit_2026-08-06"),
    os.path.join(ROOT, "data", "raw", "external", "faads", "agencies"),
    os.path.join(ROOT, "data", "raw", "external", "faads", "seam"),
]

TXN_KEY = "assistance_transaction_unique_key"
TXN_RFIPS = "prime_award_transaction_recipient_county_fips_code"
TXN_RSFIPS = "prime_award_transaction_recipient_state_fips_code"
TXN_PFIPS = "prime_award_transaction_place_of_performance_county_fips_code"
TXN_PSFIPS = "prime_award_transaction_place_of_performance_state_fips_code"

NEW_COLS = [
    "geo_recipient_county_fips", "geo_recipient_county_name",
    "geo_recipient_state_fips", "geo_recipient_place_dominance_share",
    "geo_recipient_place_ambiguous",
    "geo_pop_county_fips", "geo_pop_county_name",
    "geo_pop_state_fips", "geo_pop_place_dominance_share",
    "geo_pop_place_ambiguous",
    "geo_key_tier", "geo_key_basis", "geo_built_date",
]

BASIS = {
    "exact_transaction": "usaspending_prime_award_transaction_record_on_"
                         "assistance_transaction_unique_key",
    "exact_award_summary": "usaspending_prime_award_summary_on_"
                           "assistance_award_unique_key",
    "derived_place_zip5": "modal county of this row's own zip5 in "
                          "geo_place_county_crosswalk.csv",
    "derived_place_modal": "modal county of this row's own city+state in "
                           "geo_place_county_crosswalk.csv",
}


def norm_city(v):
    return " ".join((v or "").strip().upper().split())


def norm_state(v):
    v = (v or "").strip().upper()
    return v if len(v) == 2 and v.isalpha() else ""


def norm_zip5(v):
    v = (v or "").strip().replace("-", "")
    if v.endswith(".0"):
        v = v[:-2]
    if not v.isdigit():
        return ""
    if len(v) >= 9:
        v = v[:5]
    elif len(v) == 8:
        v = v.zfill(9)[:5]
    elif len(v) == 4:
        v = v.zfill(5)
    return v if len(v) == 5 and v.isdigit() and v != "00000" else ""


def norm_sfips(v):
    v = (v or "").strip()
    if v.endswith(".0"):
        v = v[:-2]
    if not v or not v.isdigit():
        return ""
    return v.zfill(2)[:2] if len(v) <= 2 else ""


def norm_fips(v, sfips=""):
    v = (v or "").strip()
    if not v or v.lower() in ("nan", "none", "null"):
        return ""
    if v.endswith(".0"):
        v = v[:-2]
    v = v.zfill(5) if len(v) == 4 else v
    if len(v) != 5 or not v.isdigit():
        return ""
    if sfips:
        s = norm_sfips(sfips)
        if s and v[:2] != s:
            return ""
    return v


def money_cents(v):
    v = (v or "").strip().replace(",", "").replace("$", "")
    if not v:
        return 0
    try:
        return int(round(float(v) * 100))
    except ValueError:
        return 0


def iter_members(paths):
    for p in paths:
        if p.lower().endswith(".zip"):
            try:
                z = zipfile.ZipFile(p)
            except Exception as e:
                print(f"  !! CANNOT OPEN {os.path.basename(p)}: {e}")
                continue
            for name in z.namelist():
                if not name.lower().endswith(".csv"):
                    continue
                with z.open(name) as fh:
                    yield (os.path.basename(p),
                           csv.reader(io.TextIOWrapper(fh, encoding="utf-8-sig",
                                                       newline="", errors="replace")))
        else:
            with open(p, newline="", encoding="utf-8-sig", errors="replace") as fh:
                yield os.path.basename(p), csv.reader(fh)


def load_txn_geo(needed):
    """transaction key -> (rcp_fips, pop_fips), restricted to keys we will use.
    `needed` keeps the dict to the size of the tables being written rather than
    the size of the corpora."""
    out = {}
    files = []
    for d in TXN_DIRS:
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.lower().endswith((".zip", ".csv")):
                p = os.path.join(d, f)
                if os.path.getsize(p) > 200:
                    files.append(p)
    scanned = 0
    for base, rdr in iter_members(files):
        try:
            hdr = next(rdr)
        except (StopIteration, csv.Error):
            continue
        idx = {c: i for i, c in enumerate(hdr)}
        if TXN_KEY not in idx or TXN_RFIPS not in idx:
            continue
        ik, irf = idx[TXN_KEY], idx[TXN_RFIPS]
        irs = idx.get(TXN_RSFIPS, -1)
        ipf = idx.get(TXN_PFIPS, -1)
        ips = idx.get(TXN_PSFIPS, -1)
        w = len(hdr)
        n = 0
        for row in rdr:
            scanned += 1
            n += 1
            if len(row) < w:
                row = row + [""] * (w - len(row))
            k = row[ik].strip()
            if not k or k not in needed:
                continue
            rf = norm_fips(row[irf], row[irs] if irs >= 0 else "")
            pf = norm_fips(row[ipf], row[ips] if ips >= 0 else "") if ipf >= 0 else ""
            if rf or pf:
                prev = out.get(k)
                if prev is None:
                    out[k] = (rf, pf)
                else:
                    out[k] = (prev[0] or rf, prev[1] or pf)
        if n:
            print(f"       [txn] {base:<44} {n:>9,} rows")
    print(f"       transaction rows scanned {scanned:,}; keys matched {len(out):,}")
    return out


def load_award_xwalk(prefix=None):
    xw = {}
    with open(XWALK_AWARD, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if prefix and not row["award_unique_key"].startswith(prefix):
                continue
            xw[row["award_unique_key"]] = (row["recipient_county_fips"],
                                           row["pop_county_fips"])
    return xw


def load_place_xwalk():
    zip5 = {}
    city = {}
    with open(XWALK_PLACE, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            v = (row["county_fips"], row["county_name"], row["state_fips"],
                 row["dominance_share"], row["ambiguous_flag"])
            if row["place_key_type"] == "zip5":
                zip5[row["place_key"]] = v
            else:
                city[row["place_key"]] = v
    return zip5, city


def load_county_names():
    d = {}
    p = os.path.join(CLEAN, "geo_county_dim.csv")
    if os.path.exists(p):
        with open(p, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                d[row["county_fips"]] = row["county_name"]
    return d


def keys_in(path, col):
    out = set()
    with open(path, newline="", encoding="utf-8") as fh:
        r = csv.reader(fh)
        hdr = next(r)
        if col not in hdr:
            return out
        i = hdr.index(col)
        for row in r:
            if i < len(row) and row[i].strip():
                out.add(row[i].strip())
    return out


def backup(src, dst):
    if os.path.exists(dst):
        print(f"  [bak] {os.path.basename(dst)} exists, kept")
        return
    shutil.copyfile(src, dst)
    print(f"  [bak] {os.path.basename(dst)}")


def promote(path, bak, money_col, txn_col, award_col, city_col, state_col,
            zip_col, txn_geo, award_xw, zip5_xw, city_xw, cname):
    print(f"\n[872] {os.path.relpath(path, ROOT)}")
    backup(path, bak)
    tmp = path + ".tmp872"
    tier = Counter()
    n = 0
    cents = 0
    with open(bak, newline="", encoding="utf-8") as fin, \
         open(tmp, "w", newline="", encoding="utf-8") as fout:
        r = csv.reader(fin)
        hdr = next(r)
        base_idx = [i for i, c in enumerate(hdr) if c not in NEW_COLS]
        w = csv.writer(fout)
        w.writerow([hdr[i] for i in base_idx] + NEW_COLS)
        i_money = hdr.index(money_col)
        i_txn = hdr.index(txn_col) if txn_col in hdr else -1
        i_aw = hdr.index(award_col) if award_col in hdr else -1
        i_city = hdr.index(city_col) if city_col in hdr else -1
        i_state = hdr.index(state_col) if state_col in hdr else -1
        i_zip = hdr.index(zip_col) if zip_col in hdr else -1
        width = len(hdr)
        for row in r:
            n += 1
            if len(row) < width:
                row = row + [""] * (width - len(row))
            cents += money_cents(row[i_money])
            vals = None

            k = row[i_txn].strip() if i_txn >= 0 else ""
            hit = txn_geo.get(k) if k else None
            if hit and (hit[0] or hit[1]):
                rf, pf = hit
                vals = [rf, cname.get(rf, ""), rf[:2] if rf else "", "", "",
                        pf, cname.get(pf, ""), pf[:2] if pf else "", "", "",
                        "exact_transaction", BASIS["exact_transaction"], STAMP]
                tier["exact_transaction"] += 1

            if vals is None and i_aw >= 0:
                a = row[i_aw].strip()
                hit = award_xw.get(a) if a else None
                if hit and (hit[0] or hit[1]):
                    rf, pf = hit
                    vals = [rf, cname.get(rf, ""), rf[:2] if rf else "", "", "",
                            pf, cname.get(pf, ""), pf[:2] if pf else "", "", "",
                            "exact_award_summary", BASIS["exact_award_summary"], STAMP]
                    tier["exact_award_summary"] += 1

            if vals is None and i_zip >= 0:
                z = norm_zip5(row[i_zip])
                hit = zip5_xw.get(z) if z else None
                if hit:
                    vals = [hit[0], hit[1], hit[2], hit[3], hit[4],
                            "", "", "", "", "",
                            "derived_place_zip5", BASIS["derived_place_zip5"], STAMP]
                    tier["derived_place_zip5"] += 1

            if vals is None and i_city >= 0 and i_state >= 0:
                st = norm_state(row[i_state])
                ct = norm_city(row[i_city])
                hit = city_xw.get(f"{st}|{ct}") if st and ct else None
                if hit:
                    vals = [hit[0], hit[1], hit[2], hit[3], hit[4],
                            "", "", "", "", "",
                            "derived_place_modal", BASIS["derived_place_modal"], STAMP]
                    tier["derived_place_modal"] += 1

            if vals is None:
                vals = [""] * 12 + [STAMP]
                tier["unkeyed"] += 1
            w.writerow([row[i] for i in base_idx] + vals)

    with open(tmp, newline="", encoding="utf-8") as fh:
        after_hdr = next(csv.reader(fh))
    gained = [c for c in after_hdr if c not in hdr]
    lost = [c for c in hdr if c not in after_hdr]
    print(f"  [cols] {len(hdr)} -> {len(after_hdr)}")
    print(f"         gained ({len(gained)}): {gained}")
    print(f"         lost   ({len(lost)}): {lost if lost else 'none'}")
    os.replace(tmp, path)
    print(f"  [rows] {n:,}   {money_col} ${cents/100:,.2f}")
    for k, v in tier.most_common():
        print(f"         {k:<22} {v:>9,}  {v/max(1,n):6.1%}")
    return {"rows": n, "cents": cents, "tiers": dict(tier)}


def build():
    cname = load_county_names()
    zip5_xw, city_xw = load_place_xwalk()
    print(f"[872] place crosswalk: zip5 {len(zip5_xw):,}  city_state {len(city_xw):,}")

    print("[872] transaction keys wanted by the two tables")
    needed = keys_in(FFT, "assistance_transaction_unique_key")
    print(f"       federal_funding_transactions : {len(needed):,}")
    nf = keys_in(FAADS, "assistance_transaction_unique_key")
    print(f"       faads_transactions_all       : {len(nf):,}")
    needed |= nf
    print(f"       union                        : {len(needed):,}")

    print("[872] scanning transaction corpora")
    txn_geo = load_txn_geo(needed)

    award_xw = load_award_xwalk(prefix="ASST_")
    print(f"[872] assistance award crosswalk keys: {len(award_xw):,}")

    stats = {"built": STAMP, "script": "872_promote_geo_keys_assistance.py",
             "txn_keys_resolved": len(txn_geo),
             "assistance_award_xwalk_keys": len(award_xw),
             "place_zip5": len(zip5_xw), "place_city_state": len(city_xw)}

    stats["federal_funding_transactions"] = promote(
        FFT, BAK_FFT, "obligated_usd",
        "assistance_transaction_unique_key", "assistance_award_unique_key",
        "recipient_city_name", "recipient_state_code", "",
        txn_geo, award_xw, zip5_xw, city_xw, cname)

    stats["faads_transactions_all_agencies"] = promote(
        FAADS, BAK_FAADS, "obligated_usd",
        "assistance_transaction_unique_key", "",
        "recipient_city", "recipient_state", "recipient_zip",
        txn_geo, award_xw, zip5_xw, city_xw, cname)

    with open(OUT_STATS, "w", encoding="utf-8") as fh:
        json.dump(stats, fh, indent=2)
    print(f"\n[872] wrote {os.path.relpath(OUT_STATS, ROOT)}")
    return stats


TABLES = [(FFT, BAK_FFT, "obligated_usd"), (FAADS, BAK_FAADS, "obligated_usd")]


def _scan(path, money_col):
    n = cents = bad_fips = tier_no_fips = fips_no_tier = derived_no_share = 0
    tiers = Counter()
    with open(path, newline="", encoding="utf-8") as fh:
        r = csv.DictReader(fh)
        hdr = list(r.fieldnames or [])
        for row in r:
            n += 1
            cents += money_cents(row.get(money_col))
            any_fips = False
            for fc, sc in (("geo_recipient_county_fips", "geo_recipient_state_fips"),
                           ("geo_pop_county_fips", "geo_pop_state_fips")):
                v = (row.get(fc) or "").strip()
                if not v:
                    continue
                any_fips = True
                if len(v) != 5 or not v.isdigit():
                    bad_fips += 1
                elif (row.get(sc) or "") and v[:2] != row.get(sc):
                    bad_fips += 1
            t = (row.get("geo_key_tier") or "").strip()
            tiers[t or "(none)"] += 1
            if t and not any_fips:
                tier_no_fips += 1
            if any_fips and not t:
                fips_no_tier += 1
            if t.startswith("derived_") and not (
                    row.get("geo_recipient_place_dominance_share") or "").strip():
                derived_no_share += 1
    return dict(rows=n, cents=cents, hdr=hdr, bad_fips=bad_fips, tiers=tiers,
                tier_no_fips=tier_no_fips, fips_no_tier=fips_no_tier,
                derived_no_share=derived_no_share)


def _scan_backup(path, money_col):
    n = cents = 0
    with open(path, newline="", encoding="utf-8") as fh:
        r = csv.reader(fh)
        hdr = next(r)
        i = hdr.index(money_col)
        for row in r:
            n += 1
            cents += money_cents(row[i] if i < len(row) else "")
    return n, cents, hdr


def verify(tables=None, quiet=False):
    tables = tables or TABLES
    say = (lambda *a: None) if quiet else print
    fails = []
    for path, bak, money_col in tables:
        name = os.path.basename(path)
        if not os.path.exists(path):
            fails.append(f"MISSING {path}")
            continue
        cur = _scan(path, money_col)
        say(f"[872 verify] {name}")
        say(f"    rows {cur['rows']:,}   {money_col} ${cur['cents']/100:,.2f}")
        say(f"    tiers {dict(cur['tiers'])}")
        say(f"    bad_fips {cur['bad_fips']}  tier_without_fips {cur['tier_no_fips']}"
            f"  fips_without_tier {cur['fips_no_tier']}"
            f"  derived_without_share {cur['derived_no_share']}")
        if cur["bad_fips"]:
            fails.append(f"I4 {name}: {cur['bad_fips']} malformed / "
                         f"state-inconsistent county fips")
        if cur["tier_no_fips"] or cur["fips_no_tier"] or cur["derived_no_share"]:
            fails.append(f"I5 {name}: tier/fips disagree "
                         f"(tier_no_fips {cur['tier_no_fips']}, "
                         f"fips_no_tier {cur['fips_no_tier']}, "
                         f"derived_no_share {cur['derived_no_share']})")
        if os.path.exists(bak):
            bn, bc, bhdr = _scan_backup(bak, money_col)
            lost = [c for c in bhdr if c not in cur["hdr"]]
            say(f"    vs backup: rows {bn:,} -> {cur['rows']:,}   "
                f"cents {bc:,} -> {cur['cents']:,}   "
                f"cols {len(bhdr)} -> {len(cur['hdr'])}   lost {lost if lost else 'none'}")
            if bn != cur["rows"]:
                fails.append(f"I1 {name}: row conservation broken {bn:,} -> {cur['rows']:,}")
            if bc != cur["cents"]:
                fails.append(f"I2 {name}: money conservation broken {bc:,}c -> "
                             f"{cur['cents']:,}c (delta ${abs(bc-cur['cents'])/100:,.2f})")
            if lost:
                fails.append(f"I3 {name}: columns lost vs backup: {lost}")
        else:
            say(f"    !! no backup {os.path.basename(bak)}")
            fails.append(f"I1/I2/I3 {name}: backup missing, conservation unprovable")
    if fails:
        for f in fails:
            say("FAIL:", f)
        return 1
    say("[872 verify] OK -- I1 I2 I3 I4 I5 all hold")
    return 0


def selftest():
    import tempfile
    if not os.path.exists(FFT):
        print("[872 selftest] build first")
        return 1
    tmp = tempfile.mkdtemp(prefix="872_selftest_")
    live = os.path.join(tmp, "t.csv")
    bak = os.path.join(tmp, "t.csv.bak")
    N = 20000

    def head(src, dst, n):
        with open(src, newline="", encoding="utf-8") as fi, \
             open(dst, "w", newline="", encoding="utf-8") as fo:
            r = csv.reader(fi)
            w = csv.writer(fo)
            for i, row in enumerate(r):
                if i > n:
                    break
                w.writerow(row)

    head(FFT, live, N)
    head(FFT, bak, N)
    spec = [(live, bak, "obligated_usd")]
    ok = True

    def rows(p):
        with open(p, newline="", encoding="utf-8") as fh:
            return list(csv.reader(fh))

    def write(p, rr):
        with open(p, "w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerows(rr)

    base = verify(spec, quiet=True)
    print(f"[872 selftest] clean {N:,}-row copy verify -> {base} "
          f"{'(expected 0)' if base == 0 else '!! CLEAN COPY ALREADY FAILS'}")
    ok = ok and base == 0

    def case(name, mutate):
        nonlocal ok
        head(FFT, live, N)
        head(FFT, bak, N)
        mutate()
        rc = verify(spec, quiet=True)
        good = rc == 1
        print(f"  {name:<54} verify -> {rc}  {'FIRES' if good else '!! DID NOT FIRE'}")
        ok = ok and good

    def drop_row():
        write(live, rows(live)[:1] + rows(live)[2:])

    def move_money():
        rr = rows(live)
        i = rr[0].index("obligated_usd")
        for r in rr[1:]:
            if r[i] and money_cents(r[i]):
                r[i] = str(float(r[i]) + 0.01)
                break
        write(live, rr)

    def drop_col():
        rr = rows(live)
        i = rr[0].index("cfda_title")
        write(live, [r[:i] + r[i + 1:] for r in rr])

    def break_fips():
        rr = rows(live)
        i = rr[0].index("geo_recipient_county_fips")
        for r in rr[1:]:
            if r[i]:
                r[i] = r[i][1:]
                break
        write(live, rr)

    def strip_share():
        rr = rows(live)
        ti = rr[0].index("geo_key_tier")
        si = rr[0].index("geo_recipient_place_dominance_share")
        for r in rr[1:]:
            if r[ti].startswith("derived_"):
                r[si] = ""
                break
        write(live, rr)

    def tier_without_fips():
        rr = rows(live)
        fi = rr[0].index("geo_recipient_county_fips")
        pi = rr[0].index("geo_pop_county_fips")
        for r in rr[1:]:
            if r[fi] or r[pi]:
                r[fi] = r[pi] = ""
                break
        write(live, rr)

    case("I1 one row dropped", drop_row)
    case("I2 one obligation moved by a cent", move_money)
    case("I3 an existing column dropped", drop_col)
    case("I4 a promoted county fips loses a digit", break_fips)
    case("I5 a derived row loses its dominance share", strip_share)
    case("I5 a tiered row loses both its fips", tier_without_fips)

    shutil.rmtree(tmp, ignore_errors=True)
    print("[872 selftest] " + ("OK -- every invariant fired" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "build"
    if mode == "verify":
        sys.exit(verify())
    if mode == "selftest":
        sys.exit(selftest())
    build()
    sys.exit(verify())
