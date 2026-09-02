#!/usr/bin/env python3
"""870 — harvest the geographic key crosswalks out of the gapfill corpus (ADR-015).

WHY THIS EXISTS
---------------
ADR-015 measured the geography axis on 2026-09-02 and found it unbuilt:
7,399,905 rows across data/clean/ carry a PLACE (city / state / zip) and
1,070 rows carry a JOINABLE key (fips / geoid / aiannh). 0.0%. Nearly every
row in Cedar says where it is in prose and almost none of it says so in a code
you can group by.

The fix needs no download. `data/raw/contracts/usaspending_gapfill_2026-08-05/`
already holds USAspending prime-award-summary extracts whose 286-column schema
carries, per award:

    prime_award_summary_recipient_county_fips_code          (recipient side)
    prime_award_summary_place_of_performance_county_fips_code (POP side)

kept apart, exactly as ADR-015 rule 1 requires. This script does not join
anything; it only harvests, at two grains, and it produces TWO files because
the two grains have completely different evidential standing:

1. `geo_award_county_crosswalk.csv` — grain: one row per award unique key.
   EXACT. The federal government said this award's recipient sits in this
   county. Tier A everywhere it is used.

2. `geo_place_county_crosswalk.csv` — grain: one row per place (zip5, or
   city+state). DERIVED. Built by counting how often a given place was
   reported alongside a given county fips across every row of the corpus,
   recipient side and place-of-performance side pooled as independent
   observations of the same underlying fact ("this place is in that county").

Grain 2 is the multiplier and also the danger. A city is not inside exactly
one county — "KANSAS CITY, MO" straddles four, "HOUSTON, TX" three. So the
crosswalk records `n_distinct_counties` and `dominance_share` per place and
does NOT resolve the ambiguity here. The consumer decides its own threshold
and the tier it will accept; this file only reports what the corpus observed.
A zip5 is far tighter than a city but still not clean (ZCTAs cross county
lines), so zip5 is emitted at its own grain rather than folded in.

WHY POOL RECIPIENT AND POP OBSERVATIONS. Both columns are a (city, state, zip)
address paired with the county fips the federal system assigned to that same
address. The pairing is the fact being harvested; which side of the award it
came from is irrelevant to it and pooling roughly doubles the evidence. The
side is NOT pooled anywhere else — see rule 1 — only in this lookup table,
which is about places, not about money.

WHAT THIS DOES NOT DO. It writes no key onto any transaction table. That is
871 (contracts) and 872 (assistance). It builds no AIANNH crosswalk. That is
873. Keeping the harvest separate means a bad promotion can be reverted
without re-reading 6 zips (~24 minutes).

MODES
-----
    py -3 code/870_build_geo_crosswalks.py           build both crosswalks
    py -3 code/870_build_geo_crosswalks.py verify    re-measure and assert

INVARIANTS (verify exits 1 on any failure)
------------------------------------------
  I1 award crosswalk key is unique — the file is a lookup and a duplicate key
     silently multiplies rows in every downstream join.
  I2 every non-empty county_fips is exactly 5 digits and its first 2 equal the
     state fips on the same row. A 4-digit fips (leading zero eaten by Excel
     or by a float cast) joins to the wrong county silently.
  I3 the place crosswalk's dominance_share equals n_observations /
     n_observations_total on every row, and n_distinct_counties >= 1.
  I4 both files are non-empty and the award crosswalk covers >= 900,000 keys
     (ADR-015 measured 1,041,147 distinct award keys in this corpus; a large
     shortfall means a zip failed to open and was skipped silently).
"""

import csv
import io
import json
import os
import sys
import zipfile
from collections import Counter, defaultdict

csv.field_size_limit(10 * 1024 * 1024)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAPFILL = os.path.join(ROOT, "data", "raw", "contracts", "usaspending_gapfill_2026-08-05")
CLEAN = os.path.join(ROOT, "data", "clean")

OUT_AWARD = os.path.join(CLEAN, "geo_award_county_crosswalk.csv")
OUT_PLACE = os.path.join(CLEAN, "geo_place_county_crosswalk.csv")
OUT_STATS = os.path.join(ROOT, "docs", "GEO_CROSSWALK_STATS.json")

# ---------------------------------------------------------------- column maps
# Prime award summary schemas. Contracts = 286 cols, assistance = 100 cols;
# the geographic block is named identically in both except for the zip columns
# (contracts pack zip+4 into one field, assistance splits it).
PRIME_MAP = {
    "contract": {
        "key": "contract_award_unique_key",
        "rcp_fips": "prime_award_summary_recipient_county_fips_code",
        "rcp_cname": "recipient_county_name",
        "rcp_sfips": "prime_award_summary_recipient_state_fips_code",
        "rcp_state": "recipient_state_code",
        "rcp_city": "recipient_city_name",
        "rcp_zip": "recipient_zip_4_code",
        "pop_fips": "prime_award_summary_place_of_performance_county_fips_code",
        "pop_cname": "primary_place_of_performance_county_name",
        "pop_sfips": "prime_award_summary_place_of_performance_state_fips_code",
        "pop_state": "primary_place_of_performance_state_code",
        "pop_city": "primary_place_of_performance_city_name",
        "pop_zip": "primary_place_of_performance_zip_4",
    },
    "assistance": {
        "key": "assistance_award_unique_key",
        "rcp_fips": "prime_award_summary_recipient_county_fips_code",
        "rcp_cname": "recipient_county_name",
        "rcp_sfips": "prime_award_summary_recipient_state_fips_code",
        "rcp_state": "recipient_state_code",
        "rcp_city": "recipient_city_name",
        "rcp_zip": "recipient_zip_code",
        "pop_fips": "prime_award_summary_place_of_performance_county_fips_code",
        "pop_cname": "primary_place_of_performance_county_name",
        "pop_sfips": "prime_award_summary_place_of_performance_state_fips_code",
        "pop_state": "primary_place_of_performance_state_code",
        "pop_city": "primary_place_of_performance_city_name",
        "pop_zip": "primary_place_of_performance_zip_4",
    },
}

# Subaward schemas carry the prime's geography under different names. Harvested
# for PLACE observations only -- they are not award-grain rows.
SUB_PAIRS = [
    ("prime_awardee_county_fips_code", "prime_awardee_county_name",
     "prime_awardee_state_fips_code", "prime_awardee_zip_code", None, None),
    ("prime_award_primary_place_of_performance_county_fips_code",
     "prime_award_primary_place_of_performance_county_name",
     "prime_award_primary_place_of_performance_state_fips_code",
     "prime_award_primary_place_of_performance_address_zip_code", None, None),
]

AWARD_FIELDS = [
    "award_unique_key", "award_key_type",
    "recipient_county_fips", "recipient_county_name",
    "recipient_state_fips", "recipient_state_code",
    "recipient_city_name", "recipient_zip5",
    "pop_county_fips", "pop_county_name",
    "pop_state_fips", "pop_state_code",
    "pop_city_name", "pop_zip5",
    "n_source_rows", "conflict_flag", "source_files",
]

PLACE_FIELDS = [
    "place_key_type", "place_key", "state_code", "city_name", "zip5",
    "county_fips", "county_name", "state_fips",
    "n_observations", "n_observations_total", "dominance_share",
    "n_distinct_counties", "ambiguous_flag",
]


def norm_fips(v, sfips=""):
    """Return a 5-digit county fips or ''. Repairs the two damage patterns
    actually present in federal extracts: a float cast ('06037.0') and a lost
    leading zero ('6037'). A 4-digit value is only repaired when the state
    fips on the same row confirms the missing digit -- never guessed."""
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
            return ""  # internally inconsistent row: refuse it, do not repair
    return v


def norm_sfips(v):
    v = (v or "").strip()
    if v.endswith(".0"):
        v = v[:-2]
    if not v or not v.isdigit():
        return ""
    return v.zfill(2)[:2] if len(v) <= 2 else ""


def norm_zip5(v):
    v = (v or "").strip().replace("-", "")
    if v.endswith(".0"):
        v = v[:-2]
    if not v.isdigit():
        return ""
    if len(v) >= 9:
        v = v[:5]
    elif len(v) == 8:          # 8 digits = 4-digit zip lost its leading zero + plus4
        v = v.zfill(9)[:5]
    elif len(v) == 4:
        v = v.zfill(5)
    if len(v) != 5 or not v.isdigit() or v == "00000":
        return ""
    return v


def norm_city(v):
    return " ".join((v or "").strip().upper().split())


def norm_state(v):
    v = (v or "").strip().upper()
    return v if len(v) == 2 and v.isalpha() else ""


def iter_zip_csvs(paths):
    for zp in paths:
        try:
            z = zipfile.ZipFile(zp)
        except Exception as e:
            print(f"  !! CANNOT OPEN {os.path.basename(zp)}: {e}")
            continue
        for name in z.namelist():
            if not name.lower().endswith(".csv"):
                continue
            with z.open(name) as fh:
                tf = io.TextIOWrapper(fh, encoding="utf-8-sig", newline="", errors="replace")
                yield os.path.basename(zp), name, csv.reader(tf)


def build():
    zips = []
    for d in (GAPFILL, os.path.join(GAPFILL, "assistance_fain")):
        if os.path.isdir(d):
            zips += [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith(".zip")]
    print(f"[870] gapfill zips found: {len(zips)}")
    for z in zips:
        print(f"        {os.path.relpath(z, ROOT)}  {os.path.getsize(z)/1e6:.1f} MB")

    awards = {}                       # key -> list(values) packed
    award_srcs = defaultdict(set)
    conflicts = set()
    # place evidence: (grain, place_key) -> Counter(county_fips)
    place_obs = defaultdict(Counter)
    place_meta = {}                   # (grain, place_key) -> (state, city, zip5, cname, sfips)
    rows_read = 0
    prime_rows = 0
    sub_rows = 0

    def observe(city, state, zip5, fips, cname, sfips):
        if not fips:
            return
        if zip5:
            k = ("zip5", zip5)
            place_obs[k][fips] += 1
            place_meta.setdefault(k, (state, "", zip5, cname, sfips))
        if city and state:
            k = ("city_state", f"{state}|{city}")
            place_obs[k][fips] += 1
            place_meta.setdefault(k, (state, city, "", cname, sfips))

    for zbase, member, rdr in iter_zip_csvs(zips):
        try:
            hdr = next(rdr)
        except StopIteration:
            continue
        idx = {c: i for i, c in enumerate(hdr)}
        is_prime = "PrimeAwardSummaries" in member
        kind = "assistance" if member.startswith("Assistance") else "contract"

        if is_prime:
            m = PRIME_MAP[kind]
            if m["key"] not in idx:
                print(f"  !! {member}: no {m['key']}, skipped")
                continue
            g = {k: idx.get(v, -1) for k, v in m.items()}
            n = 0
            for row in rdr:
                rows_read += 1
                prime_rows += 1
                n += 1
                if len(row) <= g["key"]:
                    continue
                key = (row[g["key"]] or "").strip()
                if not key:
                    continue
                rsf = norm_sfips(row[g["rcp_sfips"]] if g["rcp_sfips"] >= 0 else "")
                psf = norm_sfips(row[g["pop_sfips"]] if g["pop_sfips"] >= 0 else "")
                rf = norm_fips(row[g["rcp_fips"]] if g["rcp_fips"] >= 0 else "", rsf)
                pf = norm_fips(row[g["pop_fips"]] if g["pop_fips"] >= 0 else "", psf)
                rcn = (row[g["rcp_cname"]] if g["rcp_cname"] >= 0 else "").strip().upper()
                pcn = (row[g["pop_cname"]] if g["pop_cname"] >= 0 else "").strip().upper()
                rst = norm_state(row[g["rcp_state"]] if g["rcp_state"] >= 0 else "")
                pst = norm_state(row[g["pop_state"]] if g["pop_state"] >= 0 else "")
                rct = norm_city(row[g["rcp_city"]] if g["rcp_city"] >= 0 else "")
                pct = norm_city(row[g["pop_city"]] if g["pop_city"] >= 0 else "")
                rz = norm_zip5(row[g["rcp_zip"]] if g["rcp_zip"] >= 0 else "")
                pz = norm_zip5(row[g["pop_zip"]] if g["pop_zip"] >= 0 else "")

                observe(rct, rst, rz, rf, rcn, rsf)
                observe(pct, pst, pz, pf, pcn, psf)

                packed = (rf, rcn, rsf, rst, rct, rz, pf, pcn, psf, pst, pct, pz)
                prev = awards.get(key)
                if prev is None:
                    awards[key] = [kind, packed, 1]
                else:
                    prev[2] += 1
                    # conflict only on the county keys -- names and cities vary
                    if (prev[1][0], prev[1][6]) != (packed[0], packed[6]):
                        if prev[1][0] and prev[1][6]:
                            conflicts.add(key)
                        else:
                            # earlier row was blank on a side: adopt the filled one
                            merged = tuple(prev[1][i] or packed[i] for i in range(12))
                            prev[1] = merged
                award_srcs[key].add(zbase)
            print(f"  [prime  ] {zbase:<28} {member[:44]:<46} {n:>9,} rows")
        else:
            cols = []
            for f, cn, sf, zp, _, _ in SUB_PAIRS:
                if f in idx:
                    cols.append((idx[f], idx.get(cn, -1), idx.get(sf, -1), idx.get(zp, -1)))
            if not cols:
                continue
            n = 0
            for row in rdr:
                rows_read += 1
                sub_rows += 1
                n += 1
                for fi, ci, si, zi in cols:
                    if len(row) <= fi:
                        continue
                    sfp = norm_sfips(row[si] if si >= 0 else "")
                    fp = norm_fips(row[fi], sfp)
                    if not fp:
                        continue
                    cn = (row[ci] if ci >= 0 else "").strip().upper()
                    z5 = norm_zip5(row[zi] if zi >= 0 else "")
                    observe("", "", z5, fp, cn, sfp)
            print(f"  [sub    ] {zbase:<28} {member[:44]:<46} {n:>9,} rows")

    print(f"\n[870] rows read           : {rows_read:,}  (prime {prime_rows:,} / sub {sub_rows:,})")
    print(f"[870] distinct award keys : {len(awards):,}")
    print(f"[870] conflicting keys    : {len(conflicts):,}")

    # ------------------------------------------------------------ award file
    n_rcp = n_pop = n_both = 0
    with open(OUT_AWARD, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(AWARD_FIELDS)
        for key in sorted(awards):
            kind, p, n = awards[key]
            rf, rcn, rsf, rst, rct, rz, pf, pcn, psf, pst, pct, pz = p
            if rf:
                n_rcp += 1
            if pf:
                n_pop += 1
            if rf and pf:
                n_both += 1
            w.writerow([key, kind, rf, rcn, rsf, rst, rct, rz,
                        pf, pcn, psf, pst, pct, pz, n,
                        "1" if key in conflicts else "0",
                        ";".join(sorted(award_srcs[key]))])
    print(f"[870] wrote {OUT_AWARD}")
    print(f"        recipient fips filled : {n_rcp:,} ({n_rcp/max(1,len(awards)):.1%})")
    print(f"        pop       fips filled : {n_pop:,} ({n_pop/max(1,len(awards)):.1%})")
    print(f"        both sides filled     : {n_both:,} ({n_both/max(1,len(awards)):.1%})")

    # ------------------------------------------------------------ place file
    n_place = 0
    n_amb = 0
    by_grain = Counter()
    with open(OUT_PLACE, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(PLACE_FIELDS)
        for (grain, pkey) in sorted(place_obs):
            c = place_obs[(grain, pkey)]
            total = sum(c.values())
            fips, n = c.most_common(1)[0]
            state, city, zip5, cname, sfips = place_meta[(grain, pkey)]
            share = round(n / total, 6)
            ndist = len(c)
            amb = "1" if ndist > 1 else "0"
            if amb == "1":
                n_amb += 1
            by_grain[grain] += 1
            n_place += 1
            w.writerow([grain, pkey, state, city, zip5, fips, cname,
                        sfips or fips[:2], n, total, f"{share:.6f}", ndist, amb])
    print(f"[870] wrote {OUT_PLACE}")
    print(f"        places                : {n_place:,}  {dict(by_grain)}")
    print(f"        multi-county places   : {n_amb:,} ({n_amb/max(1,n_place):.1%})")

    stats = {
        "built": "2026-09-02",
        "script": "870_build_geo_crosswalks.py",
        "source": "data/raw/contracts/usaspending_gapfill_2026-08-05/",
        "rows_read": rows_read,
        "prime_rows": prime_rows,
        "sub_rows": sub_rows,
        "award_keys": len(awards),
        "award_keys_conflicting": len(conflicts),
        "award_recipient_fips_filled": n_rcp,
        "award_pop_fips_filled": n_pop,
        "award_both_filled": n_both,
        "place_rows": n_place,
        "place_by_grain": dict(by_grain),
        "place_multi_county": n_amb,
    }
    with open(OUT_STATS, "w", encoding="utf-8") as fh:
        json.dump(stats, fh, indent=2)
    print(f"[870] wrote {OUT_STATS}")
    return stats


def verify():
    fails = []
    for p in (OUT_AWARD, OUT_PLACE):
        if not os.path.exists(p):
            fails.append(f"MISSING {p}")
    if fails:
        for f in fails:
            print("FAIL:", f)
        return 1

    # I1 / I2 on the award crosswalk
    seen = set()
    dup = 0
    bad_fips = 0
    n = 0
    n_rcp = n_pop = 0
    with open(OUT_AWARD, newline="", encoding="utf-8") as fh:
        r = csv.DictReader(fh)
        for row in r:
            n += 1
            k = row["award_unique_key"]
            if k in seen:
                dup += 1
            seen.add(k)
            for fcol, scol in (("recipient_county_fips", "recipient_state_fips"),
                               ("pop_county_fips", "pop_state_fips")):
                v = row[fcol]
                if not v:
                    continue
                if fcol == "recipient_county_fips":
                    n_rcp += 1
                else:
                    n_pop += 1
                if len(v) != 5 or not v.isdigit():
                    bad_fips += 1
                elif row[scol] and v[:2] != row[scol]:
                    bad_fips += 1
    print(f"[870 verify] award rows {n:,}  unique {len(seen):,}  dup {dup}  bad_fips {bad_fips}")
    print(f"[870 verify] recipient fips {n_rcp:,}  pop fips {n_pop:,}")
    if dup:
        fails.append(f"I1 award_unique_key not unique: {dup} duplicates")
    if bad_fips:
        fails.append(f"I2 malformed / state-inconsistent county fips: {bad_fips}")
    if n < 900_000:
        fails.append(f"I4 award crosswalk only {n:,} keys, expected >= 900,000 "
                     f"(ADR-015 measured 1,041,147) -- a zip probably failed to open")

    # I3 on the place crosswalk
    m = 0
    bad_share = 0
    bad_dist = 0
    with open(OUT_PLACE, newline="", encoding="utf-8") as fh:
        r = csv.DictReader(fh)
        for row in r:
            m += 1
            try:
                nn = int(row["n_observations"])
                tt = int(row["n_observations_total"])
                sh = float(row["dominance_share"])
                nd = int(row["n_distinct_counties"])
            except ValueError:
                bad_share += 1
                continue
            if tt <= 0 or abs(sh - nn / tt) > 1e-5:
                bad_share += 1
            if nd < 1 or nn > tt:
                bad_dist += 1
    print(f"[870 verify] place rows {m:,}  bad_share {bad_share}  bad_counts {bad_dist}")
    if bad_share or bad_dist:
        fails.append(f"I3 place crosswalk arithmetic broken: share {bad_share}, counts {bad_dist}")
    if m == 0:
        fails.append("I4 place crosswalk is empty")

    if fails:
        for f in fails:
            print("FAIL:", f)
        return 1
    print("[870 verify] OK — I1 I2 I3 I4 all hold")
    return 0


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "build"
    if mode == "verify":
        sys.exit(verify())
    build()
    sys.exit(verify())
