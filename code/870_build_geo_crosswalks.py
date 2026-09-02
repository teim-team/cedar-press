#!/usr/bin/env python3
"""870 - harvest the geographic key crosswalks out of the local corpora (ADR-015).

WHY THIS EXISTS
---------------
ADR-015 measured the geography axis on 2026-09-02 and found it unbuilt:
7,399,905 rows across data/clean/ carry a PLACE (city / state / zip) and
1,070 rows carry a JOINABLE key (fips / geoid / aiannh). 0.0%. Nearly every
row in Cedar says where it is in prose and almost none of it says so in a code
you can group by.

The fix needs no download. USAspending's extract schema carries county FIPS on
BOTH sides of every award, and Cedar already has that schema on disk in five
separate corpora. ADR-015 names only one of them:

    data/raw/contracts/usaspending_gapfill_2026-08-05/     prime AWARD summaries
    data/raw/external/faads/{agencies,seam}/               prime TRANSACTIONS
    data/raw/federal_funding/usaspending_2023_2026/        prime TRANSACTIONS
    data/raw/federal_funding/usaspending_credit_2026-08-06/  prime TRANSACTIONS
    data/raw/subcontracts/usaspending_subawards_2026-08-05/  subawards

ADR-015 says "the unlock is already on disk" and points at the gapfill corpus.
That is true and it is also an undercount: the gapfill corpus is a NATIVE
RECIPIENT UNIVERSE, so the place lookup it yields alone covers 6,421 zip codes,
which is nowhere near enough to key `faads_transactions_all_agencies.csv`
(2,769,748 rows, the whole federal assistance universe FY2001-07). The FAADS
archive zips carry `prime_award_transaction_recipient_county_fips_code`
themselves. See the note appended to ADR-015.

TWO GRAINS, TWO FILES, BECAUSE THEY HAVE DIFFERENT EVIDENTIAL STANDING
----------------------------------------------------------------------
1. `geo_award_county_crosswalk.csv` - grain: one row per award unique key,
   from the gapfill PRIME AWARD SUMMARIES only. EXACT. The federal government
   said this award's recipient sits in this county and its work was performed
   in that one. Tier `exact` everywhere it is used.

2. `geo_place_county_crosswalk.csv` - grain: one row per place (zip5, or
   city+state). DERIVED. Built by counting how often a given place was
   reported alongside a given county fips across every row of every corpus,
   recipient side and place-of-performance side pooled as independent
   observations of the same underlying fact ("this place is in that county").

3. `geo_county_dim.csv` - grain: one county fips. The modal county NAME the
   corpora report for it, so that nothing downstream has to guess.

Grain 2 is the multiplier and also the danger. A city is not inside exactly
one county - "KANSAS CITY, MO" straddles four, "HOUSTON, TX" three. So the
crosswalk records `n_distinct_counties` and `dominance_share` per place and
does NOT resolve the ambiguity here. The consumer decides its own threshold
and the tier it will accept; this file only reports what the corpora observed.
A zip5 is far tighter than a city but still not clean (ZCTAs cross county
lines), so zip5 is emitted at its own grain rather than folded in.

WHY POOL RECIPIENT AND POP OBSERVATIONS. Both columns are a (city, state, zip)
address paired with the county fips the federal system assigned to that same
address. The pairing is the fact being harvested; which side of the award it
came from is irrelevant to it and pooling roughly doubles the evidence. The
side is NOT pooled anywhere else - see ADR-015 rule 1 - only in this lookup
table, which is about places, not about money.

COUNTY NAME IS RESOLVED FROM THE FIPS, NOT FROM THE FIRST ROW SEEN. An earlier
draft of this script stored the county NAME alongside a place on first sight and
then chose the county FIPS by modal vote. On any multi-county place those two
disagree, and the file would have asserted "county_fips 20209, county_name
JACKSON" - a county that does not exist. Names are now voted per FIPS in
`geo_county_dim.csv` and looked up from the FIPS that won. `state_fips` is
likewise always `county_fips[:2]` and never a remembered value.

WHAT THIS DOES NOT DO. It writes no key onto any transaction table. That is
871 (contracts) and 872 (assistance). It builds no AIANNH crosswalk. That is
873. Keeping the harvest separate means a bad promotion can be reverted
without re-reading the corpora.

MODES
-----
    py -3 code/870_build_geo_crosswalks.py           build the crosswalks
    py -3 code/870_build_geo_crosswalks.py verify    re-measure and assert
    py -3 code/870_build_geo_crosswalks.py selftest  corrupt a COPY of each
                                                     output and prove verify
                                                     exits 1 on it

INVARIANTS (verify exits 1 on any failure)
------------------------------------------
  I1 award crosswalk key is unique - the file is a lookup and a duplicate key
     silently multiplies rows in every downstream join.
  I2 every non-empty county_fips is exactly 5 digits and its first 2 equal the
     state fips on the same row. A 4-digit fips (leading zero eaten by Excel
     or by a float cast) joins to the wrong county silently.
  I3 the place crosswalk's dominance_share equals n_observations /
     n_observations_total on every row, and n_distinct_counties >= 1.
  I4 both files are non-empty and the award crosswalk covers >= 900,000 keys
     (ADR-015 measured 1,041,147 distinct award keys in the gapfill corpus; a
     large shortfall means a zip failed to open and was skipped silently).
  I5 every county_name printed on a place row is the modal name of THAT row's
     county_fips in geo_county_dim.csv, and state_fips == county_fips[:2].
  I6 geo_county_dim.csv carries EVERY county code the crosswalks reference --
     including the SS000 state-wide placeholders and codes seen without a name.
     A dimension that silently omits them makes a downstream join drop rows.
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
OUT_CDIM = os.path.join(CLEAN, "geo_county_dim.csv")
OUT_STATS = os.path.join(ROOT, "docs", "GEO_CROSSWALK_STATS.json")

# ------------------------------------------------------- award-grain column map
# Gapfill prime award summaries. Contracts = 286 cols, assistance = 100 cols;
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

# ------------------------------------------------------- place-grain column map
# One QUAD = one (address -> county fips) assertion the federal system made,
# wherever it appears. Any CSV is scanned for every quad whose fips column is
# present; a corpus contributing three quads contributes three observations per
# row. Names differ between the summary / transaction / subaward schemas but the
# assertion is identical, so they pool.
#   (fips, county_name, state_fips, state_code, city, zip)
PLACE_QUADS = [
    # prime award SUMMARY schema (gapfill)
    ("prime_award_summary_recipient_county_fips_code", "recipient_county_name",
     "prime_award_summary_recipient_state_fips_code", "recipient_state_code",
     "recipient_city_name", "recipient_zip_4_code"),
    ("prime_award_summary_recipient_county_fips_code", "recipient_county_name",
     "prime_award_summary_recipient_state_fips_code", "recipient_state_code",
     "recipient_city_name", "recipient_zip_code"),
    ("prime_award_summary_place_of_performance_county_fips_code",
     "primary_place_of_performance_county_name",
     "prime_award_summary_place_of_performance_state_fips_code",
     "primary_place_of_performance_state_code",
     "primary_place_of_performance_city_name", "primary_place_of_performance_zip_4"),
    # prime TRANSACTION schema (faads archive, assistance 2023-26, credit)
    ("prime_award_transaction_recipient_county_fips_code", "recipient_county_name",
     "prime_award_transaction_recipient_state_fips_code", "recipient_state_code",
     "recipient_city_name", "recipient_zip_code"),
    ("prime_award_transaction_place_of_performance_county_fips_code",
     "primary_place_of_performance_county_name",
     "prime_award_transaction_place_of_performance_state_fips_code",
     "primary_place_of_performance_state_code",
     "primary_place_of_performance_city_name", "primary_place_of_performance_zip_4"),
    # SUBAWARD schema - carries the PRIME's geography, harvested as place
    # evidence only; it never reaches the award crosswalk.
    ("prime_awardee_county_fips_code", "prime_awardee_county_name",
     "prime_awardee_state_fips_code", "prime_awardee_state_code",
     "prime_awardee_city_name", "prime_awardee_zip_code"),
    ("prime_award_primary_place_of_performance_county_fips_code",
     "prime_award_primary_place_of_performance_county_name",
     "prime_award_primary_place_of_performance_state_fips_code",
     "prime_award_primary_place_of_performance_state_code",
     "prime_award_primary_place_of_performance_city_name",
     "prime_award_primary_place_of_performance_address_zip_code"),
]

# Corpora scanned for PLACE observations. (label, directory, recurse)
PLACE_CORPORA = [
    ("gapfill_award_summaries", os.path.join("data", "raw", "contracts",
                                             "usaspending_gapfill_2026-08-05"), True),
    ("faads_archive", os.path.join("data", "raw", "external", "faads"), True),
    ("assistance_2023_2026", os.path.join("data", "raw", "federal_funding",
                                          "usaspending_2023_2026"), False),
    ("assistance_credit", os.path.join("data", "raw", "federal_funding",
                                       "usaspending_credit_2026-08-06"), False),
    ("subawards_2026_08_05", os.path.join("data", "raw", "subcontracts",
                                          "usaspending_subawards_2026-08-05"), False),
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
    "n_distinct_counties", "ambiguous_flag", "runner_up_county_fips",
]

CDIM_FIELDS = ["county_fips", "state_fips", "county_name", "county_code_class",
               "n_observations", "n_name_variants"]

# USAspending writes SS000 when it knows the state and not the county. It is a
# PLACEHOLDER, not a county, and 01000 sitting unlabelled in a county dimension
# would be read as one. Everything observed is kept -- flag, never delete -- but
# the class travels with it so nothing downstream can mistake it.
def county_code_class(fips, named):
    if fips.endswith("000"):
        return "state_wide_placeholder_not_a_county"
    return "county" if named else "county_code_observed_without_a_name"


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


def list_zips(d, recurse):
    out = []
    if not os.path.isdir(d):
        return out
    if recurse:
        for r, _dirs, files in os.walk(d):
            out += [os.path.join(r, f) for f in sorted(files) if f.lower().endswith(".zip")]
    else:
        out += [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.lower().endswith(".zip")]
    return sorted(out)


def list_csvs(d, recurse):
    out = []
    if not os.path.isdir(d):
        return out
    if recurse:
        for r, _dirs, files in os.walk(d):
            out += [os.path.join(r, f) for f in sorted(files) if f.lower().endswith(".csv")]
    else:
        out += [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.lower().endswith(".csv")]
    return sorted(out)


def iter_members(paths):
    """Yield (container_basename, member_name, csv.reader) for every CSV inside
    every zip, and for every loose CSV."""
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
                    tf = io.TextIOWrapper(fh, encoding="utf-8-sig", newline="",
                                          errors="replace")
                    yield os.path.basename(p), os.path.basename(name), csv.reader(tf)
        else:
            with open(p, newline="", encoding="utf-8-sig", errors="replace") as fh:
                yield os.path.basename(p), os.path.basename(p), csv.reader(fh)


def build():
    # ---------------------------------------------------------------- state
    awards = {}                       # key -> [kind, packed, n_rows]
    award_srcs = defaultdict(set)
    conflicts = set()
    place_obs = defaultdict(Counter)  # (grain, place_key) -> Counter(county_fips)
    place_meta = {}                   # (grain, place_key) -> (state, city, zip5)
    county_names = defaultdict(Counter)   # county_fips -> Counter(county_name)
    county_seen = Counter()               # county_fips -> observations, named or not
    corpus_stats = {}

    def observe(city, state, zip5, fips, cname):
        """Record one (place -> county fips) observation. The county NAME is
        voted globally against the FIPS, never remembered against the place."""
        if not fips:
            return
        county_seen[fips] += 1
        if cname:
            county_names[fips][cname] += 1
        if zip5:
            k = ("zip5", zip5)
            place_obs[k][fips] += 1
            place_meta.setdefault(k, (state, "", zip5))
        if city and state:
            k = ("city_state", f"{state}|{city}")
            place_obs[k][fips] += 1
            place_meta.setdefault(k, (state, city, ""))

    # ------------------------------------------- PASS 1: award grain (gapfill)
    gap = list_zips(GAPFILL, True)
    print(f"[870] gapfill zips: {len(gap)}")
    prime_rows = 0
    for zbase, member, rdr in iter_members(gap):
        if "PrimeAwardSummaries" not in member:
            continue
        try:
            hdr = next(rdr)
        except StopIteration:
            continue
        idx = {c: i for i, c in enumerate(hdr)}
        kind = "assistance" if member.startswith("Assistance") else "contract"
        m = PRIME_MAP[kind]
        if m["key"] not in idx:
            print(f"  !! {member}: no {m['key']}, skipped")
            continue
        g = {k: idx.get(v, -1) for k, v in m.items()}
        n = 0

        def cell(row, j):
            return row[j] if 0 <= j < len(row) else ""

        for row in rdr:
            prime_rows += 1
            n += 1
            if len(row) <= g["key"]:
                continue
            key = (row[g["key"]] or "").strip()
            if not key:
                continue
            rsf = norm_sfips(cell(row, g["rcp_sfips"]))
            psf = norm_sfips(cell(row, g["pop_sfips"]))
            rf = norm_fips(cell(row, g["rcp_fips"]), rsf)
            pf = norm_fips(cell(row, g["pop_fips"]), psf)
            rcn = cell(row, g["rcp_cname"]).strip().upper()
            pcn = cell(row, g["pop_cname"]).strip().upper()
            rst = norm_state(cell(row, g["rcp_state"]))
            pst = norm_state(cell(row, g["pop_state"]))
            rct = norm_city(cell(row, g["rcp_city"]))
            pct = norm_city(cell(row, g["pop_city"]))
            rz = norm_zip5(cell(row, g["rcp_zip"]))
            pz = norm_zip5(cell(row, g["pop_zip"]))

            for _f, _n in ((rf, rcn), (pf, pcn)):
                if _f:
                    county_seen[_f] += 1
                    if _n:
                        county_names[_f][_n] += 1
            packed = (rf, rcn, rsf or rf[:2], rst, rct, rz,
                      pf, pcn, psf or pf[:2], pst, pct, pz)
            prev = awards.get(key)
            if prev is None:
                awards[key] = [kind, packed, 1]
            else:
                prev[2] += 1
                # Conflict is judged PER SIDE. The earlier draft judged the pair
                # jointly, so an award whose recipient fips disagreed while its
                # POP fips was merely blank got silently merged and never flagged.
                for i in (0, 6):
                    if prev[1][i] and packed[i] and prev[1][i] != packed[i]:
                        conflicts.add(key)
                if any((not prev[1][i]) and packed[i] for i in range(12)):
                    prev[1] = tuple(prev[1][i] or packed[i] for i in range(12))
            award_srcs[key].add(zbase)
        print(f"  [award ] {zbase:<30} {n:>9,} rows")
    print(f"[870] award-grain rows read : {prime_rows:,}")
    print(f"[870] distinct award keys   : {len(awards):,}")
    print(f"[870] conflicting keys      : {len(conflicts):,}")

    # ------------------------------------------------- PASS 2: place grain
    for label, rel, recurse in PLACE_CORPORA:
        d = os.path.join(ROOT, rel)
        paths = list_zips(d, recurse) + [p for p in list_csvs(d, recurse)
                                         if os.path.getsize(p) > 200]
        rows_here = 0
        obs_here = 0
        files_here = 0
        for cbase, member, rdr in iter_members(sorted(paths)):
            try:
                hdr = next(rdr)
            except (StopIteration, csv.Error):
                continue
            idx = {c: i for i, c in enumerate(hdr)}
            quads = []
            for f, cn, sf, sc, ci, zp in PLACE_QUADS:
                if f in idx:
                    quads.append((idx[f], idx.get(cn, -1), idx.get(sf, -1),
                                  idx.get(sc, -1), idx.get(ci, -1), idx.get(zp, -1)))
            if not quads:
                continue
            files_here += 1
            width = len(hdr)
            for row in rdr:
                rows_here += 1
                if len(row) < width:
                    row = row + [""] * (width - len(row))
                for fi, cni, sfi, sci, cii, zpi in quads:
                    raw = row[fi]
                    if not raw:
                        continue
                    sfp = norm_sfips(row[sfi]) if sfi >= 0 else ""
                    fp = norm_fips(raw, sfp)
                    if not fp:
                        continue
                    observe(norm_city(row[cii]) if cii >= 0 else "",
                            norm_state(row[sci]) if sci >= 0 else "",
                            norm_zip5(row[zpi]) if zpi >= 0 else "",
                            fp,
                            row[cni].strip().upper() if cni >= 0 else "")
                    obs_here += 1
        corpus_stats[label] = {"files_with_geo": files_here,
                               "rows_read": rows_here,
                               "observations": obs_here}
        print(f"  [place ] {label:<26} files {files_here:>3}  rows {rows_here:>10,}"
              f"  obs {obs_here:>10,}")

    # ------------------------------------------------- county dimension file
    # Resolve one modal name per county fips FIRST; the place file then quotes
    # the name of the fips it actually chose.
    cname_of = {}
    by_class = Counter()
    with open(OUT_CDIM, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(CDIM_FIELDS)
        for fips in sorted(set(county_seen) | set(county_names)):
            c = county_names.get(fips) or Counter()
            nm = c.most_common(1)[0][0] if c else ""
            if nm:
                cname_of[fips] = nm
            klass = county_code_class(fips, bool(nm))
            by_class[klass] += 1
            w.writerow([fips, fips[:2], nm, klass,
                        county_seen.get(fips, sum(c.values())), len(c)])
    print(f"[870] wrote {os.path.relpath(OUT_CDIM, ROOT)}  "
          f"codes {len(set(county_seen) | set(county_names)):,}  {dict(by_class)}")

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
            w.writerow([key, kind,
                        rf, (cname_of.get(rf) or rcn) if rf else "", rf[:2], rst, rct, rz,
                        pf, (cname_of.get(pf) or pcn) if pf else "", pf[:2], pst, pct, pz,
                        n, "1" if key in conflicts else "0",
                        ";".join(sorted(award_srcs[key]))])
    print(f"[870] wrote {os.path.relpath(OUT_AWARD, ROOT)}")
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
            ranked = c.most_common(2)
            fips, n = ranked[0]
            runner = ranked[1][0] if len(ranked) > 1 else ""
            state, city, zip5 = place_meta[(grain, pkey)]
            share = round(n / total, 6)
            ndist = len(c)
            amb = "1" if ndist > 1 else "0"
            if amb == "1":
                n_amb += 1
            by_grain[grain] += 1
            n_place += 1
            w.writerow([grain, pkey, state, city, zip5, fips,
                        cname_of.get(fips, ""), fips[:2],
                        n, total, f"{share:.6f}", ndist, amb, runner])
    print(f"[870] wrote {os.path.relpath(OUT_PLACE, ROOT)}")
    print(f"        places                : {n_place:,}  {dict(by_grain)}")
    print(f"        multi-county places   : {n_amb:,} ({n_amb/max(1,n_place):.1%})")

    stats = {
        "built": "2026-09-02",
        "script": "870_build_geo_crosswalks.py",
        "award_grain_source": "data/raw/contracts/usaspending_gapfill_2026-08-05/",
        "place_grain_sources": {k: v for k, v in corpus_stats.items()},
        "award_rows_read": prime_rows,
        "award_keys": len(awards),
        "award_keys_conflicting": len(conflicts),
        "award_recipient_fips_filled": n_rcp,
        "award_pop_fips_filled": n_pop,
        "award_both_filled": n_both,
        "place_rows": n_place,
        "place_by_grain": dict(by_grain),
        "place_multi_county": n_amb,
        "counties_named": len(cname_of),
        "county_codes_by_class": dict(by_class),
    }
    with open(OUT_STATS, "w", encoding="utf-8") as fh:
        json.dump(stats, fh, indent=2)
    print(f"[870] wrote {os.path.relpath(OUT_STATS, ROOT)}")
    return stats


def verify(award_path=None, place_path=None, cdim_path=None, quiet=False):
    """Re-measure the written files and assert I1..I5. Returns 0 / 1.
    Paths are overridable so `selftest` can point it at a deliberately
    corrupted copy and prove the invariant actually fires."""
    award_path = award_path or OUT_AWARD
    place_path = place_path or OUT_PLACE
    cdim_path = cdim_path or OUT_CDIM
    say = (lambda *a: None) if quiet else print

    fails = []
    for p in (award_path, place_path, cdim_path):
        if not os.path.exists(p):
            fails.append(f"MISSING {p}")
    if fails:
        for f in fails:
            say("FAIL:", f)
        return 1

    seen = set()
    dup = 0
    bad_fips = 0
    n = 0
    n_rcp = n_pop = 0
    with open(award_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
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
    say(f"[870 verify] award rows {n:,}  unique {len(seen):,}  dup {dup}  bad_fips {bad_fips}")
    say(f"[870 verify] recipient fips {n_rcp:,}  pop fips {n_pop:,}")
    if dup:
        fails.append(f"I1 award_unique_key not unique: {dup} duplicates")
    if bad_fips:
        fails.append(f"I2 malformed / state-inconsistent county fips: {bad_fips}")
    if n < 900_000:
        fails.append(f"I4 award crosswalk only {n:,} keys, expected >= 900,000 "
                     f"(ADR-015 measured 1,041,147) -- a zip probably failed to open")

    cname_of = {}
    dim_codes = set()
    with open(cdim_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            cname_of[row["county_fips"]] = row["county_name"]
            dim_codes.add(row["county_fips"])
    referenced = set()
    with open(award_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            for c in ("recipient_county_fips", "pop_county_fips"):
                if row[c]:
                    referenced.add(row[c])

    m = 0
    bad_share = bad_dist = bad_name = bad_sfips = 0
    with open(place_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
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
            f5 = row["county_fips"]
            referenced.add(f5)
            if row["county_name"] and cname_of.get(f5, "") != row["county_name"]:
                bad_name += 1
            if row["state_fips"] != f5[:2]:
                bad_sfips += 1
    say(f"[870 verify] place rows {m:,}  bad_share {bad_share}  bad_counts {bad_dist}"
        f"  bad_name {bad_name}  bad_state_fips {bad_sfips}")
    if bad_share or bad_dist:
        fails.append(f"I3 place crosswalk arithmetic broken: share {bad_share}, "
                     f"counts {bad_dist}")
    if m == 0:
        fails.append("I4 place crosswalk is empty")
    if bad_name or bad_sfips:
        fails.append(f"I5 place row names a county its own fips does not carry: "
                     f"name {bad_name}, state_fips {bad_sfips}")
    orphan = referenced - dim_codes
    say(f"[870 verify] county codes referenced {len(referenced):,}  "
        f"in dimension {len(dim_codes):,}  orphaned {len(orphan):,}")
    if orphan:
        fails.append(f"I6 {len(orphan)} county codes are referenced by a crosswalk "
                     f"and absent from geo_county_dim.csv, e.g. "
                     f"{sorted(orphan)[:5]}")

    if fails:
        for f in fails:
            say("FAIL:", f)
        return 1
    say("[870 verify] OK -- I1 I2 I3 I4 I5 I6 all hold")
    return 0


def selftest():
    """Prove verify() fires. Copies the real outputs to a temp directory,
    injects one violation per invariant, and asserts verify() returns 1."""
    import shutil
    import tempfile
    if not os.path.exists(OUT_AWARD):
        print("[870 selftest] build first")
        return 1
    tmp = tempfile.mkdtemp(prefix="870_selftest_")
    a = os.path.join(tmp, "award.csv")
    pl = os.path.join(tmp, "place.csv")
    cd = d = os.path.join(tmp, "cdim.csv")
    ok = True

    def reset():
        shutil.copyfile(OUT_AWARD, a)
        shutil.copyfile(OUT_PLACE, pl)
        shutil.copyfile(OUT_CDIM, cd)

    def rows(path):
        with open(path, newline="", encoding="utf-8") as fh:
            return list(csv.reader(fh))

    def write(path, rr):
        with open(path, "w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerows(rr)

    def case(name, mutate):
        nonlocal ok
        reset()
        mutate()
        rc = verify(a, pl, cd, quiet=True)
        good = (rc == 1)
        print(f"  {name:<52} verify -> {rc}  {'FIRES' if good else '!! DID NOT FIRE'}")
        ok = ok and good

    reset()
    base = verify(a, pl, cd, quiet=True)
    print(f"[870 selftest] clean copy verify -> {base} "
          f"{'(expected 0)' if base == 0 else '!! CLEAN COPY ALREADY FAILS'}")
    ok = ok and base == 0

    def dup_key():
        rr = rows(a)
        rr.append(list(rr[1]))
        write(a, rr)

    def bad_fips():
        rr = rows(a)
        i = rr[0].index("recipient_county_fips")
        for r in rr[1:]:
            if r[i]:
                r[i] = r[i][1:]      # eat a leading digit -> 4 chars
                break
        write(a, rr)

    def truncate_award():
        write(a, rows(a)[:5000])

    def bad_share():
        rr = rows(pl)
        rr[1][rr[0].index("dominance_share")] = "0.123456"
        write(pl, rr)

    def wrong_county_name():
        rr = rows(pl)
        rr[1][rr[0].index("county_name")] = "NOT A COUNTY"
        write(pl, rr)

    def wrong_state_fips():
        rr = rows(pl)
        rr[1][rr[0].index("state_fips")] = "99"
        write(pl, rr)

    def dim_drops_a_code():
        keep = rows(pl)[1][rows(pl)[0].index("county_fips")]
        rr = rows(d)
        i = rr[0].index("county_fips")
        write(d, [rr[0]] + [r for r in rr[1:] if r[i] != keep])

    case("I1 duplicate award_unique_key", dup_key)
    case("I2 county fips loses a leading digit", bad_fips)
    case("I4 award crosswalk truncated to 5,000 keys", truncate_award)
    case("I3 dominance_share no longer equals n/total", bad_share)
    case("I5 place quotes a name its fips does not carry", wrong_county_name)
    case("I5 state_fips diverges from county_fips[:2]", wrong_state_fips)
    case("I6 dimension drops a code a crosswalk still references", dim_drops_a_code)

    shutil.rmtree(tmp, ignore_errors=True)
    print("[870 selftest] " + ("OK -- every invariant fired" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "build"
    if mode == "verify":
        sys.exit(verify())
    if mode == "selftest":
        sys.exit(selftest())
    build()
    sys.exit(verify())
