#!/usr/bin/env python3
"""874 - the ADR-015 difference measure: two sums, published separately.

WHAT ADR-015 ASKED FOR
----------------------
    money flowing TO an area       sum by PLACE OF PERFORMANCE
    money reaching ENTITIES there  sum by RECIPIENT, where the recipient is a
                                   Native entity
    the difference                 federal money landing in Indian Country that
                                   does not reach Native entities

Rule 3 of that ADR says the difference is "derived, labelled, and bounded" and
that what gets PUBLISHED is the two sums. This script therefore writes the two
sums and never writes a difference column. The bounds it needs to be read with
travel on the rows themselves, not in a footnote someone can lose.

THE THING ADR-015 ASSUMES THAT IS NOT TRUE OF CEDAR
---------------------------------------------------
"Money flowing TO an area" only means what it says if the table you are summing
is the WHOLE federal universe for that area. Two of Cedar's three big money
tables are not:

    prime_contracts.csv                Native-CANDIDATE contracting corpus. Its
                                       recipient universe was pulled from Native
                                       entity lists, so its place-of-performance
                                       sum for a county is "Cedar's contracting
                                       corpus performed there", not "all federal
                                       contracting performed there".
    federal_funding_transactions.csv   same shape, assistance, FY2007-2026.
    faads_transactions_all_agencies    THE WHOLE FEDERAL ASSISTANCE UNIVERSE,
                                       FY2001-2007, every recipient in the
                                       country, Native and not.

Only the third supports the measure as ADR-015 words it. MONEY_TOTALLING_RULES
already says so in prose ("its $1,830,639,317,708 is the WHOLE federal
assistance universe ... every recipient in the country"); ADR-015 was written
without that in view. The other two datasets are still emitted, because the
within-corpus comparison is worth having, but every row carries a
`universe_note` saying what its denominator actually is, and the demonstration
is run on FAADS.

WHERE THE NATIVE SIDE COMES FROM, PER DATASET
---------------------------------------------
    faads_transactions_all_agencies.csv  faads_entity_attribution.csv joined on
                                         faads_row_id, the 0-based ROW ORDINAL
                                         of the transaction table. Proven, not
                                         assumed: all 29,594 attribution rows
                                         match their transaction on recipient
                                         name, fiscal year and obligation to the
                                         cent at offset 0, and 4 of 29,594 at
                                         offset 1. 872 rewrote that table in
                                         place WITHOUT reordering it, so the
                                         ordinal survived; I3 re-proves the
                                         match every run rather than trusting it.
    prime_contracts.csv                  attributed_flag == 1
    federal_funding_transactions.csv     tribe_id_neid non-empty AND
                                         excluded_flag != 1

THE NATIVE SUM IS A FLOOR, ALWAYS. Attribution is a name/UEI matching exercise
that can miss and is documented to. A county's Native sum can only be revised
UP by better matching. So the derived difference is a CEILING on the money that
did not reach Native entities, never a point estimate.

RULE 2 IS NOT A DISCLAIMER, IT IS THE HEADLINE. A county is not a reservation.
Reservations span counties and counties contain fractions of reservations, so a
county-level difference measures a county, and a county is mostly not Indian
Country even where a reservation sits inside it. `aiannh_geoids_observed` and
`aiannh_overlap_basis` are carried per row from 873 so a reader can see which
counties have any AIANNH area in them at all, and `county_is_not_a_reservation`
repeats the warning on every row.

RULE 4. Every row carries `never_sum_across_datasets`. A shared county code is
not permission to add a subaward to a prime, or FAADS to
federal_funding_transactions across the FY2007 seam.

MODES
-----
    py -3 code/874_geography_two_sums.py           build + write demonstration
    py -3 code/874_geography_two_sums.py verify    re-measure and assert
    py -3 code/874_geography_two_sums.py selftest  prove verify fires

INVARIANTS (verify exits 1 on any failure)
------------------------------------------
  I1 MONEY PARTITION, to the cent: for each dataset and each side, the sum over
     counties plus the unallocated (no key on that side) residual equals the
     dataset's own total obligations exactly.
  I2 ROW PARTITION: same, in rows.
  I3 ROW SUBSET: in every cell the Native row count <= the all-recipient row
     count. Only the ROW counts nest. The first draft of this invariant also
     required the Native MONEY to be <= the all-recipient money, and it fired on
     49 real cells -- wrongly. Obligations are SIGNED: a county whose non-Native
     rows net negative through deobligations has an all-recipient sum below its
     Native sum with nothing whatever wrong. The count of such cells is reported
     as a diagnostic, not a failure.
  I4 every county_fips is 5 digits and present in geo_county_dim.csv, and its
     county_code_class matches what the dimension says it is. The dimension
     carries USAspending's SS000 state-wide placeholders; this keeps them
     LABELLED as placeholders here instead of passing as counties.
  I5 every row carries the four rule-bearing notes non-empty (universe_note,
     county_is_not_a_reservation, never_sum_across_datasets, signed_money_note).
     ADR-015 rules 2 and 4 ride on the data or they do not ride at all.
  I6 NATIVE PARTITION, to the cent: per dataset, the Native sums over counties
     plus the Native money on rows with no recipient key equals the dataset's
     own Native total. This is what catches an attribution join that multiplied
     or dropped rows -- the job the broken money-subset test was trying to do.
  I7 the FAADS row-ordinal join still matches on every attributed row. That join
     is a ROW POSITION; anything that reorders the transaction table silently
     re-points all 29,594 attributions.
"""

import csv
import json
import os
import shutil
import sys
from collections import defaultdict

csv.field_size_limit(10 * 1024 * 1024)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN = os.path.join(ROOT, "data", "clean")
OUT = os.path.join(CLEAN, "geo_county_two_sums.csv")
OUT_STATS = os.path.join(ROOT, "docs", "GEO_TWO_SUMS_STATS.json")
OUT_DEMO = os.path.join(ROOT, "docs", "GEO_TWO_SUMS_DEMONSTRATION.md")
STAMP = "2026-09-02"

NOT_A_RESERVATION = ("A county is not a reservation (ADR-015 rule 2). "
                     "Reservations span counties and counties contain fractions "
                     "of reservations. This row is a county-level APPROXIMATION.")
NEVER_SUM = ("ADR-015 rule 4: a shared county code is not permission to add this "
             "dataset's money to another's. MONEY_TOTALLING_RULES.md governs.")
FLOOR = ("The Native sum is a FLOOR: attribution can miss and never invents. "
         "A derived difference is therefore a CEILING, not a point estimate.")
SIGNED = ("Obligations are SIGNED: a deobligation is a negative row. A county's "
          "Native sum can therefore exceed its all-recipient sum without any "
          "error, when the non-Native rows in that county net negative. Only the "
          "ROW COUNTS are guaranteed to nest.")

DATASETS = [
    {
        "name": "faads_transactions_all_agencies.csv",
        "money": "obligated_usd",
        "period": "FY2001-2007",
        "universe_note": ("UNFILTERED. The whole federal assistance universe for "
                          "FY2001-2007, every recipient in the country, Native and "
                          "not. This is the only Cedar money table whose "
                          "place-of-performance sum is a true 'all federal money to "
                          "this area' figure."),
        "native_basis": "faads_entity_attribution.csv joined on faads_row_id "
                        "(0-based row ordinal), FY2001-2006",
    },
    {
        "name": "prime_contracts.csv",
        "money": "total_obligations",
        "period": "FY1979-2026",
        "universe_note": ("NATIVE-CANDIDATE CORPUS, NOT THE FEDERAL UNIVERSE. The "
                          "recipient universe was pulled from Native entity lists, so "
                          "the place-of-performance sum is 'Cedar's contracting corpus "
                          "performed in this county', NOT all federal contracting "
                          "performed there. Do not read the difference as money that "
                          "bypassed Native entities."),
        "native_basis": "attributed_flag == 1",
    },
    {
        "name": "federal_funding_transactions.csv",
        "money": "obligated_usd",
        "period": "FY2007-2026",
        "universe_note": ("NATIVE-CANDIDATE CORPUS, NOT THE FEDERAL UNIVERSE. Same "
                          "caveat as prime_contracts.csv. Also overlaps FAADS at "
                          "FY2007 - see the FY2007 seam in MONEY_TOTALLING_RULES.md."),
        "native_basis": "tribe_id_neid non-empty AND excluded_flag != 1",
    },
]

FIELDS = [
    "dataset", "period", "county_fips", "county_name", "state_fips",
    "county_code_class",
    "pop_sum_usd", "pop_rows", "pop_exact_rows",
    "all_recipient_sum_usd", "all_recipient_rows", "all_recipient_exact_rows",
    "native_recipient_sum_usd", "native_recipient_rows",
    "native_recipient_exact_rows",
    "aiannh_geoids_observed", "aiannh_overlap_basis",
    "native_sum_is_a_floor", "signed_money_note", "universe_note",
    "county_is_not_a_reservation", "never_sum_across_datasets",
    "native_side_basis", "built_date",
]


def cents(v):
    v = (v or "").strip().replace(",", "").replace("$", "")
    if not v:
        return 0
    try:
        return int(round(float(v) * 100))
    except ValueError:
        return 0


def usd(c):
    return f"{c / 100:.2f}"


def load_county_dim():
    """fips -> (modal county name, county_code_class). The class matters: 870
    emits USAspending's SS000 state-wide placeholders into the dimension rather
    than dropping them, and they must never be read as counties here either."""
    d = {}
    p = os.path.join(CLEAN, "geo_county_dim.csv")
    with open(p, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            d[row["county_fips"]] = (row["county_name"],
                                     row.get("county_code_class", "county"))
    return d


def load_aiannh_by_county():
    d = defaultdict(set)
    p = os.path.join(CLEAN, "geo_aiannh_county_observed.csv")
    if os.path.exists(p):
        with open(p, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                d[row["county_fips"]].add(row["aiannh_geoid"])
    return d


def load_faads_native_ordinals():
    """0-based row ordinals of faads_transactions_all_agencies.csv that carry a
    Cedar Native attribution, plus the fingerprint needed to re-prove the join."""
    ords = {}
    p = os.path.join(CLEAN, "faads_entity_attribution.csv")
    with open(p, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            rid = (row.get("faads_row_id") or "").strip()
            if not rid.isdigit():
                continue
            ords[int(rid)] = (row.get("recipient_name", "").strip(),
                              row.get("fiscal_year", "").strip(),
                              cents(row.get("obligated_usd")))
    return ords


def is_native(dataset, row, ordinal, faads_ords):
    if dataset == "faads_transactions_all_agencies.csv":
        return ordinal in faads_ords
    if dataset == "prime_contracts.csv":
        return (row.get("attributed_flag") or "").strip() == "1"
    if dataset == "federal_funding_transactions.csv":
        return bool((row.get("tribe_id_neid") or "").strip()) and \
            (row.get("excluded_flag") or "").strip() != "1"
    return False


def scan(ds, faads_ords):
    """One streaming pass per dataset. Returns per-county cells plus the totals
    the money-partition invariant is proven against."""
    path = os.path.join(CLEAN, ds["name"])
    money = ds["money"]
    cells = defaultdict(lambda: dict(pop_c=0, pop_n=0, pop_x=0,
                                     rcp_c=0, rcp_n=0, rcp_x=0,
                                     nat_c=0, nat_n=0, nat_x=0))
    tot_c = tot_n = 0
    unalloc_pop_c = unalloc_pop_n = 0
    unalloc_rcp_c = unalloc_rcp_n = 0
    nat_tot_c = nat_tot_n = 0
    unalloc_nat_c = unalloc_nat_n = 0
    join_checked = join_matched = 0
    is_faads = ds["name"] == "faads_transactions_all_agencies.csv"
    with open(path, newline="", encoding="utf-8") as fh:
        r = csv.DictReader(fh)
        for i, row in enumerate(r):
            c = cents(row.get(money))
            tot_c += c
            tot_n += 1
            tier = (row.get("geo_key_tier") or "").strip()
            exact = 1 if tier.startswith("exact") else 0

            pf = (row.get("geo_pop_county_fips") or "").strip()
            if pf:
                e = cells[pf]
                e["pop_c"] += c
                e["pop_n"] += 1
                e["pop_x"] += exact
            else:
                unalloc_pop_c += c
                unalloc_pop_n += 1

            rf = (row.get("geo_recipient_county_fips") or "").strip()
            nat = is_native(ds["name"], row, i, faads_ords)
            if nat:
                nat_tot_c += c
                nat_tot_n += 1
                if is_faads:
                    want = faads_ords[i]
                    join_checked += 1
                    if (want[0] == (row.get("recipient_name") or "").strip()
                            and want[1] == (row.get("fiscal_year") or "").strip()
                            and want[2] == c):
                        join_matched += 1
            if rf:
                e = cells[rf]
                e["rcp_c"] += c
                e["rcp_n"] += 1
                e["rcp_x"] += exact
                if nat:
                    e["nat_c"] += c
                    e["nat_n"] += 1
                    e["nat_x"] += exact
            else:
                unalloc_rcp_c += c
                unalloc_rcp_n += 1
                if nat:
                    unalloc_nat_c += c
                    unalloc_nat_n += 1
    return dict(cells=cells, total_cents=tot_c, total_rows=tot_n,
                unalloc_nat_cents=unalloc_nat_c, unalloc_nat_rows=unalloc_nat_n,
                unalloc_pop_cents=unalloc_pop_c, unalloc_pop_rows=unalloc_pop_n,
                unalloc_rcp_cents=unalloc_rcp_c, unalloc_rcp_rows=unalloc_rcp_n,
                native_total_cents=nat_tot_c, native_total_rows=nat_tot_n,
                join_checked=join_checked, join_matched=join_matched)


def build():
    cdim = load_county_dim()
    aia = load_aiannh_by_county()
    print(f"[874] county dimension {len(cdim):,}   counties with an observed "
          f"AIANNH area {len(aia):,}")
    faads_ords = load_faads_native_ordinals()
    print(f"[874] faads attribution ordinals {len(faads_ords):,}")

    stats = {"built": STAMP, "script": "874_geography_two_sums.py", "datasets": {}}
    rows_out = 0
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(FIELDS)
        for ds in DATASETS:
            print(f"\n[874] scanning {ds['name']}")
            s = scan(ds, faads_ords)
            print(f"       rows {s['total_rows']:,}   {ds['money']} "
                  f"${s['total_cents']/100:,.2f}")
            print(f"       counties touched {len(s['cells']):,}")
            print(f"       unallocated on POP side       "
                  f"{s['unalloc_pop_rows']:,} rows  ${s['unalloc_pop_cents']/100:,.2f}")
            print(f"       unallocated on RECIPIENT side "
                  f"{s['unalloc_rcp_rows']:,} rows  ${s['unalloc_rcp_cents']/100:,.2f}")
            print(f"       Native-attributed             "
                  f"{s['native_total_rows']:,} rows  ${s['native_total_cents']/100:,.2f}")
            if s["join_checked"]:
                print(f"       faads ordinal join re-proved  "
                      f"{s['join_matched']:,}/{s['join_checked']:,}")
            for cf in sorted(s["cells"]):
                e = s["cells"][cf]
                w.writerow([
                    ds["name"], ds["period"], cf, cdim.get(cf, ("", ""))[0], cf[:2],
                    cdim.get(cf, ("", "county_code_absent_from_dimension"))[1],
                    usd(e["pop_c"]), e["pop_n"], e["pop_x"],
                    usd(e["rcp_c"]), e["rcp_n"], e["rcp_x"],
                    usd(e["nat_c"]), e["nat_n"], e["nat_x"],
                    ";".join(sorted(aia.get(cf, ()))),
                    "observed_point_partial_see_geo_aiannh_county_observed.csv"
                    if cf in aia else "no_aiannh_area_observed_in_cedar_points",
                    FLOOR, SIGNED, ds["universe_note"], NOT_A_RESERVATION, NEVER_SUM,
                    ds["native_basis"], STAMP])
                rows_out += 1
            stats["datasets"][ds["name"]] = {
                "period": ds["period"],
                "money_column": ds["money"],
                "total_rows": s["total_rows"],
                "total_usd": usd(s["total_cents"]),
                "counties": len(s["cells"]),
                "unallocated_pop_rows": s["unalloc_pop_rows"],
                "unallocated_pop_usd": usd(s["unalloc_pop_cents"]),
                "unallocated_recipient_rows": s["unalloc_rcp_rows"],
                "unallocated_recipient_usd": usd(s["unalloc_rcp_cents"]),
                "native_rows": s["native_total_rows"],
                "native_usd": usd(s["native_total_cents"]),
                "unallocated_native_rows": s["unalloc_nat_rows"],
                "unallocated_native_usd": usd(s["unalloc_nat_cents"]),
                "faads_ordinal_join_checked": s["join_checked"],
                "faads_ordinal_join_matched": s["join_matched"],
                "universe_note": ds["universe_note"],
                "native_basis": ds["native_basis"],
            }
    print(f"\n[874] wrote {os.path.relpath(OUT, ROOT)}  rows {rows_out:,}")
    with open(OUT_STATS, "w", encoding="utf-8") as fh:
        json.dump(stats, fh, indent=2)
    print(f"[874] wrote {os.path.relpath(OUT_STATS, ROOT)}")
    write_demo(stats)
    return stats


# ------------------------------------------------------------ demonstration
MIN_POP_ROWS = 100
MIN_NATIVE_ROWS = 20
MIN_EXACT_SHARE = 0.95


def _cov(row):
    pn, rn = int(row["pop_rows"]), int(row["all_recipient_rows"])
    px, rx = int(row["pop_exact_rows"]), int(row["all_recipient_exact_rows"])
    return (px / pn if pn else 0.0), (rx / rn if rn else 0.0)


def pick_demo():
    """Pick ONE geography, by rule applied to the file rather than by eye.

    ADR-015 asks for a difference measure. A difference between two sums is only
    worth showing where BOTH sums are well covered -- otherwise the difference is
    a coverage artefact wearing the costume of a finding. So the filters are
    about coverage first and size second:

      1. a real county. USAspending's SS000 state-wide placeholders are in the
         dimension (870 keeps them rather than dropping them) and are excluded
         here -- a placeholder is not a geography.
      2. >= MIN_EXACT_SHARE of rows keyed at an EXACT tier on BOTH sides, so
         neither sum rests on modal-zip or modal-city inference.
      3. >= MIN_POP_ROWS rows on the place-of-performance side and
         >= MIN_NATIVE_ROWS Native recipient rows, so it is not a small-number
         artefact.
      4. of what survives, prefer a county with an AIANNH area observed inside
         it -- the measure is about Indian Country, and a county with no
         reservation in it is a worse illustration of it whatever its dollars.
      5. then the largest Native-recipient sum.

    Returns (winner, candidates, rows).
    """
    rows = list(csv.DictReader(open(OUT, newline="", encoding="utf-8")))
    cand = []
    for row in rows:
        if row["county_code_class"] != "county":
            continue
        pn, rn = int(row["pop_rows"]), int(row["all_recipient_rows"])
        nn = int(row["native_recipient_rows"])
        if pn < MIN_POP_ROWS or nn < MIN_NATIVE_ROWS:
            continue
        pshare, rshare = _cov(row)
        if pshare < MIN_EXACT_SHARE or rshare < MIN_EXACT_SHARE:
            continue
        cand.append(row)
    cand.sort(key=lambda r: (1 if r["aiannh_geoids_observed"] else 0,
                             float(r["native_recipient_sum_usd"])), reverse=True)
    return (cand[0] if cand else None), cand, rows


def write_demo(stats):
    win, cand, rows = pick_demo()
    L = []
    A = L.append
    A("# ADR-015 worked demonstration - the two sums, on one geography\n")
    A(f"*Generated {STAMP} by `code/874_geography_two_sums.py`. Every number is "
      f"re-measured from `data/clean/` on each run; regenerate rather than edit. "
      f"The full table is `data/clean/geo_county_two_sums.csv`.*\n")

    A("## Why this geography and not another\n")
    A("A difference between two sums is only worth showing where **both sums are "
      "well covered**. Otherwise the difference measures Cedar's key coverage and "
      "not the world. The rule is in `pick_demo()` and was applied to the file:\n")
    A("1. A **real county**. USAspending writes `SS000` when it knows the state "
      "and not the county; 870 keeps those codes in the dimension rather than "
      "dropping them, and they are excluded here because a placeholder is not a "
      "geography.")
    A(f"2. At least **{int(MIN_EXACT_SHARE*100)}% of rows keyed at an EXACT tier "
      f"on BOTH sides** - the federal record named the county - so neither sum "
      f"rests on modal-zip or modal-city inference.")
    A(f"3. At least **{MIN_POP_ROWS} rows** on the place-of-performance side and "
      f"**{MIN_NATIVE_ROWS} Native recipient rows**, so it is not a small-number "
      f"artefact.")
    A("4. Prefer a county with an **AIANNH area observed inside it**. The measure "
      "is about Indian Country; a county with no reservation in it is a worse "
      "illustration of it whatever its dollars.")
    A("5. Then the largest Native-recipient sum.\n")
    A(f"**{len(cand):,} of {len(rows):,} county-dataset cells passed.** That is a "
      f"small number and it is the honest headline of this exercise: the "
      f"geography axis now exists, and the places where it is exact enough on "
      f"BOTH sides to carry a difference measure are still few.\n")

    if not win:
        A("**No cell passed. The demonstration cannot be made, and this document "
          "says so rather than lowering the bar until one does.**\n")
        open(OUT_DEMO, "w", encoding="utf-8").write("\n".join(L))
        print("[874] NO cell passed the demonstration filters")
        return

    cf = win["county_fips"]
    cname = win["county_name"]
    A(f"The winner is **{cname} County, state FIPS {win['state_fips']} "
      f"(county FIPS `{cf}`)**, on `{win['dataset']}`.\n")
    if win["aiannh_geoids_observed"]:
        A(f"Cedar's geocoded points place AIANNH area(s) "
          f"`{win['aiannh_geoids_observed']}` inside it. "
          f"See `data/clean/geo_aiannh_dim.csv` for what those are.\n")

    A("## The two sums, stated separately\n")
    ds = stats["datasets"][win["dataset"]]
    A(f"Dataset `{win['dataset']}`, {ds['period']}, money column "
      f"`{ds['money_column']}`.\n")
    A("| | sum | rows | rows keyed at an exact tier |")
    A("|---|---:|---:|---:|")
    A(f"| **money flowing TO the area** - sum by PLACE OF PERFORMANCE, every "
      f"recipient | ${float(win['pop_sum_usd']):,.2f} | {int(win['pop_rows']):,} | "
      f"{int(win['pop_exact_rows']):,} |")
    A(f"| **money reaching NATIVE ENTITIES there** - sum by RECIPIENT county, "
      f"Cedar-attributed Native recipients only | "
      f"${float(win['native_recipient_sum_usd']):,.2f} | "
      f"{int(win['native_recipient_rows']):,} | "
      f"{int(win['native_recipient_exact_rows']):,} |")
    A(f"| *for context* - all money by RECIPIENT county, every recipient | "
      f"${float(win['all_recipient_sum_usd']):,.2f} | "
      f"{int(win['all_recipient_rows']):,} | "
      f"{int(win['all_recipient_exact_rows']):,} |")
    A("\n**The two headline rows are different measures over different columns, "
      "and that is the design.** The first reads `geo_pop_county_fips`, the "
      "second `geo_recipient_county_fips`. ADR-015 rule 1 exists because "
      "collapsing them into one `county` column would destroy exactly this "
      "comparison.\n")

    A("## The difference, derived and bounded\n")
    A("Rule 3 says publish the two sums and let the difference be derived. "
      "Derived here once, so the bounds can be nailed to it:\n")
    pop = float(win["pop_sum_usd"])
    nat = float(win["native_recipient_sum_usd"])
    A("```")
    A(f"  ${pop:>18,.2f}   money performed in the county   (place of performance)")
    A(f"- ${nat:>18,.2f}   money reaching Native entities  (recipient county)")
    A(f"= ${pop - nat:>18,.2f}")
    A("```\n")
    A("It is **a ceiling, not an estimate**, and it is not a finding until every "
      "one of these is read with it:\n")
    A("1. **The Native sum is a floor.** It counts only recipients Cedar has "
      "attributed. Attribution is name and UEI matching; it misses and never "
      "invents. Better matching moves the Native sum up and the difference down, "
      "never the other way, so the number above is a CEILING on the money that "
      "did not reach Native entities.")
    A(f"2. **The two sums do not partition the same rows.** A recipient "
      f"headquartered outside the county can perform work inside it, and one "
      f"inside it can perform work elsewhere - ADR-015 rule 3 names this "
      f"directly. The context row is there so the gap between the county's POP "
      f"total (${pop:,.2f}, {int(win['pop_rows']):,} rows) and its recipient "
      f"total (${float(win['all_recipient_sum_usd']):,.2f}, "
      f"{int(win['all_recipient_rows']):,} rows) is visible rather than implied.")
    A("3. **A county is not a reservation (ADR-015 rule 2).** Reservations span "
      "counties and counties contain fractions of reservations, so this is a "
      "county-level APPROXIMATION of an area whose real boundary is elsewhere."
      + (" The AIANNH list above is itself a floor - observed from geocoded "
         "points Cedar happens to hold, not a census of overlap, because county "
         "polygons are not on disk to intersect against."
         if win["aiannh_geoids_observed"] else ""))
    A("4. **Obligations are signed.** A deobligation is a negative row, so a "
      "county's Native sum can exceed its all-recipient sum with nothing wrong. "
      "Only the ROW COUNTS are guaranteed to nest.")
    A(f"5. **Coverage, dataset-wide.** {int(ds['unallocated_pop_rows']):,} rows "
      f"carrying ${float(ds['unallocated_pop_usd']):,.2f} have NO "
      f"place-of-performance county key and sit in no county's POP sum; "
      f"{int(ds['unallocated_recipient_rows']):,} rows carrying "
      f"${float(ds['unallocated_recipient_usd']):,.2f} have no recipient county "
      f"key, of which {int(ds['unallocated_native_rows']):,} rows / "
      f"${float(ds['unallocated_native_usd']):,.2f} are Native-attributed. "
      f"Unallocated is not zero.")
    A(f"6. **Universe.** {ds['universe_note']}")
    A("7. **Never sum across datasets.** " + NEVER_SUM + "\n")

    A(f"## The same county, in every dataset that reaches it\n")
    A("Read down this table, never across it. The three rows are three different "
      "universes over three different periods and adding them would be the exact "
      "error ADR-015 rule 4 and `MONEY_TOTALLING_RULES.md` forbid.\n")
    A("| dataset | period | POP sum | POP rows | POP exact | Native sum | "
      "Native rows | all-recipient sum | all-recipient rows |")
    A("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for row in rows:
        if row["county_fips"] != cf:
            continue
        pshare, _r = _cov(row)
        A(f"| `{row['dataset']}` | {row['period']} | "
          f"${float(row['pop_sum_usd']):,.0f} | {int(row['pop_rows']):,} | "
          f"{pshare:.0%} | ${float(row['native_recipient_sum_usd']):,.0f} | "
          f"{int(row['native_recipient_rows']):,} | "
          f"${float(row['all_recipient_sum_usd']):,.0f} | "
          f"{int(row['all_recipient_rows']):,} |")
    A("\nThe universe note for each is in the CSV, on every row. The FAADS row is "
      "the only one whose POP sum is a true 'all federal money to this area' "
      "figure; the other two are Native-candidate corpora and their POP sums are "
      "corpus-scoped.\n")

    A("## Every cell that passed the coverage bar\n")
    A("| dataset | county | state FIPS | POP sum | POP rows | Native sum | "
      "Native rows | AIANNH observed |")
    A("|---|---|---|---:|---:|---:|---:|---|")
    for row in cand[:20]:
        A(f"| `{row['dataset'].replace('.csv','')}` | {row['county_name']} | "
          f"{row['state_fips']} | ${float(row['pop_sum_usd']):,.0f} | "
          f"{int(row['pop_rows']):,} | "
          f"${float(row['native_recipient_sum_usd']):,.0f} | "
          f"{int(row['native_recipient_rows']):,} | "
          f"{row['aiannh_geoids_observed'] or 'none'} |")

    A("\n## Whole-dataset totals these cells partition\n")
    A("| dataset | rows | obligations | Native rows | Native obligations | "
      "counties touched |")
    A("|---|---:|---:|---:|---:|---:|")
    for name, d in stats["datasets"].items():
        A(f"| `{name}` | {int(d['total_rows']):,} | "
          f"${float(d['total_usd']):,.2f} | {int(d['native_rows']):,} | "
          f"${float(d['native_usd']):,.2f} | {int(d['counties']):,} |")
    fa = stats["datasets"].get("faads_transactions_all_agencies.csv", {})
    if fa.get("faads_ordinal_join_checked"):
        A(f"\nThe FAADS row-ordinal join underpinning its Native side was "
          f"re-proved this run on **{int(fa['faads_ordinal_join_matched']):,} of "
          f"{int(fa['faads_ordinal_join_checked']):,}** attributed rows - "
          f"recipient name, fiscal year and obligation all matching to the cent.")
    A("\nInvariants I1 and I2 prove, to the cent and to the row, that the "
      "per-county sums plus the unallocated residual equal each dataset's own "
      "total, on both the place-of-performance and the recipient side. If that "
      "ever stops being true, `verify` exits 1.\n")

    open(OUT_DEMO, "w", encoding="utf-8").write("\n".join(L))
    print(f"[874] wrote {os.path.relpath(OUT_DEMO, ROOT)}")
    print(f"       demonstration : {cname} ({cf}) on {win['dataset']}")
    print(f"       POP sum       ${float(win['pop_sum_usd']):,.2f} over "
          f"{int(win['pop_rows']):,} rows")
    print(f"       Native sum    ${float(win['native_recipient_sum_usd']):,.2f} over "
          f"{int(win['native_recipient_rows']):,} rows")
    print(f"       cells passing the coverage bar: {len(cand):,} of {len(rows):,}")


# ------------------------------------------------------------------- verify
def verify(out_path=None, stats_path=None, quiet=False):
    out_path = out_path or OUT
    stats_path = stats_path or OUT_STATS
    say = (lambda *a: None) if quiet else print
    fails = []
    for p in (out_path, stats_path):
        if not os.path.exists(p):
            fails.append(f"MISSING {p}")
    if fails:
        for f in fails:
            say("FAIL:", f)
        return 1
    with open(stats_path, encoding="utf-8") as fh:
        stats = json.load(fh)
    cdim = load_county_dim()

    agg = defaultdict(lambda: dict(pop_c=0, pop_n=0, rcp_c=0, rcp_n=0,
                                   nat_c=0, nat_n=0))
    bad_fips = bad_class = bad_note = subset = n = 0
    signed_cells = 0
    with open(out_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            n += 1
            d = row["dataset"]
            cf = row["county_fips"]
            if len(cf) != 5 or not cf.isdigit() or cf not in cdim:
                bad_fips += 1
            elif row.get("county_code_class") != cdim[cf][1]:
                bad_class += 1
            for c in ("universe_note", "county_is_not_a_reservation",
                      "never_sum_across_datasets", "signed_money_note"):
                if not (row.get(c) or "").strip():
                    bad_note += 1
            a = agg[d]
            a["pop_c"] += cents(row["pop_sum_usd"])
            a["pop_n"] += int(row["pop_rows"])
            a["rcp_c"] += cents(row["all_recipient_sum_usd"])
            a["rcp_n"] += int(row["all_recipient_rows"])
            a["nat_c"] += cents(row["native_recipient_sum_usd"])
            a["nat_n"] += int(row["native_recipient_rows"])
            if int(row["native_recipient_rows"]) > int(row["all_recipient_rows"]):
                subset += 1
            if (cents(row["native_recipient_sum_usd"])
                    > cents(row["all_recipient_sum_usd"])):
                signed_cells += 1
    say(f"[874 verify] cells {n:,}  bad_county_fips {bad_fips}  "
        f"bad_county_code_class {bad_class}  missing_rule_notes {bad_note}  "
        f"row_subset_violations {subset}")
    say(f"[874 verify] diagnostic (NOT a failure): {signed_cells:,} cells where the "
        f"Native sum exceeds the all-recipient sum because that county's "
        f"non-Native rows net negative through deobligations")
    if bad_fips:
        fails.append(f"I4 {bad_fips} cells carry a county_fips that is not 5 digits "
                     f"or is absent from geo_county_dim.csv")
    if bad_class:
        fails.append(f"I4 {bad_class} cells disagree with geo_county_dim.csv about "
                     f"county_code_class -- a state-wide placeholder may be passing "
                     f"as a county")
    if bad_note:
        fails.append(f"I5 {bad_note} rule-note fields are empty; ADR-015 rules 2 and "
                     f"4 must ride on the data")
    if subset:
        fails.append(f"I3 {subset} cells where the Native ROW COUNT exceeds the "
                     f"all-recipient one -- the attribution join multiplied rows")

    for name, d in stats["datasets"].items():
        a = agg.get(name)
        if a is None:
            fails.append(f"I1 {name}: no cells written at all")
            continue
        tot_c = cents(d["total_usd"])
        tot_n = int(d["total_rows"])
        pop_c = a["pop_c"] + cents(d["unallocated_pop_usd"])
        pop_n = a["pop_n"] + int(d["unallocated_pop_rows"])
        rcp_c = a["rcp_c"] + cents(d["unallocated_recipient_usd"])
        rcp_n = a["rcp_n"] + int(d["unallocated_recipient_rows"])
        say(f"[874 verify] {name}")
        say(f"    POP       cells+unallocated {pop_c:,}c / {pop_n:,} rows"
            f"   vs total {tot_c:,}c / {tot_n:,} rows"
            f"   {'ok' if (pop_c == tot_c and pop_n == tot_n) else 'MISMATCH'}")
        say(f"    RECIPIENT cells+unallocated {rcp_c:,}c / {rcp_n:,} rows"
            f"   vs total {tot_c:,}c / {tot_n:,} rows"
            f"   {'ok' if (rcp_c == tot_c and rcp_n == tot_n) else 'MISMATCH'}")
        nat_c = a["nat_c"] + cents(d.get("unallocated_native_usd", "0"))
        nat_n = a["nat_n"] + int(d.get("unallocated_native_rows", 0))
        tnat_c = cents(d["native_usd"])
        tnat_n = int(d["native_rows"])
        say(f"    NATIVE    cells+unallocated {nat_c:,}c / {nat_n:,} rows"
            f"   vs dataset native {tnat_c:,}c / {tnat_n:,} rows"
            f"   {'ok' if (nat_c == tnat_c and nat_n == tnat_n) else 'MISMATCH'}")
        if nat_c != tnat_c:
            fails.append(f"I6 {name}: Native money partition off by "
                         f"${abs(nat_c-tnat_c)/100:,.2f}")
        if nat_n != tnat_n:
            fails.append(f"I6 {name}: Native row partition off by "
                         f"{abs(nat_n-tnat_n):,}")
        if pop_c != tot_c:
            fails.append(f"I1 {name}: POP money partition off by "
                         f"${abs(pop_c-tot_c)/100:,.2f}")
        if rcp_c != tot_c:
            fails.append(f"I1 {name}: RECIPIENT money partition off by "
                         f"${abs(rcp_c-tot_c)/100:,.2f}")
        if pop_n != tot_n:
            fails.append(f"I2 {name}: POP row partition off by {abs(pop_n-tot_n):,}")
        if rcp_n != tot_n:
            fails.append(f"I2 {name}: RECIPIENT row partition off by "
                         f"{abs(rcp_n-tot_n):,}")
        chk = d.get("faads_ordinal_join_checked") or 0
        mat = d.get("faads_ordinal_join_matched") or 0
        if chk and chk != mat:
            fails.append(f"I7 {name}: the faads row-ordinal join no longer matches "
                         f"on {chk - mat:,} rows -- the transaction table was "
                         f"reordered under the attribution file")

    if fails:
        for f in fails:
            say("FAIL:", f)
        return 1
    say("[874 verify] OK -- I1 I2 I3 I4 I5 I6 I7 all hold")
    return 0


def selftest():
    import tempfile
    if not os.path.exists(OUT):
        print("[874 selftest] build first")
        return 1
    tmp = tempfile.mkdtemp(prefix="874_selftest_")
    o = os.path.join(tmp, "two_sums.csv")
    s = os.path.join(tmp, "stats.json")
    ok = True

    def reset():
        shutil.copyfile(OUT, o)
        shutil.copyfile(OUT_STATS, s)

    def rows(p):
        with open(p, newline="", encoding="utf-8") as fh:
            return list(csv.reader(fh))

    def write(p, rr):
        with open(p, "w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerows(rr)

    reset()
    base = verify(o, s, quiet=True)
    print(f"[874 selftest] clean copy verify -> {base} "
          f"{'(expected 0)' if base == 0 else '!! CLEAN COPY ALREADY FAILS'}")
    ok = ok and base == 0

    def case(name, mutate):
        nonlocal ok
        reset()
        mutate()
        rc = verify(o, s, quiet=True)
        good = rc == 1
        print(f"  {name:<56} verify -> {rc}  {'FIRES' if good else '!! DID NOT FIRE'}")
        ok = ok and good

    def money_off_by_a_cent():
        rr = rows(o)
        i = rr[0].index("pop_sum_usd")
        for r in rr[1:]:
            if cents(r[i]):
                r[i] = f"{float(r[i]) + 0.01:.2f}"
                break
        write(o, rr)

    def drop_a_cell():
        rr = rows(o)
        write(o, rr[:1] + rr[2:])

    def native_rows_exceed_all():
        rr = rows(o)
        ni = rr[0].index("native_recipient_rows")
        ai = rr[0].index("all_recipient_rows")
        for r in rr[1:]:
            if int(r[ai]):
                r[ni] = str(int(r[ai]) + 1)
                break
        write(o, rr)

    def native_money_off_by_a_cent():
        rr = rows(o)
        i = rr[0].index("native_recipient_sum_usd")
        for r in rr[1:]:
            if cents(r[i]):
                r[i] = f"{float(r[i]) + 0.01:.2f}"
                break
        write(o, rr)

    def placeholder_passes_as_county():
        rr = rows(o)
        i = rr[0].index("county_code_class")
        ci = rr[0].index("county_fips")
        hit = None
        for r in rr[1:]:
            if r[ci].endswith("000"):
                hit = r
                break
        if hit is None:
            hit = rr[1]
            hit[i] = "state_wide_placeholder_not_a_county"
        else:
            hit[i] = "county"
        write(o, rr)

    def bad_county():
        rr = rows(o)
        rr[1][rr[0].index("county_fips")] = "4021"
        write(o, rr)

    def strip_rule_note():
        rr = rows(o)
        rr[1][rr[0].index("never_sum_across_datasets")] = ""
        write(o, rr)

    def break_join_stat():
        with open(s, encoding="utf-8") as fh:
            d = json.load(fh)
        for _k, v in d["datasets"].items():
            if v.get("faads_ordinal_join_checked"):
                v["faads_ordinal_join_matched"] = v["faads_ordinal_join_checked"] - 7
        with open(s, "w", encoding="utf-8") as fh:
            json.dump(d, fh, indent=2)

    case("I1 one county's POP sum moved by a cent", money_off_by_a_cent)
    case("I2 one county cell dropped entirely", drop_a_cell)
    case("I3 a Native ROW COUNT made to exceed its all-recipient count",
         native_rows_exceed_all)
    case("I6 one county's Native sum moved by a cent", native_money_off_by_a_cent)
    case("I4 a state-wide placeholder relabelled as a county",
         placeholder_passes_as_county)
    case("I4 a county_fips loses its leading zero", bad_county)
    case("I5 a row loses its never-sum rule note", strip_rule_note)
    case("I7 the FAADS row-ordinal join stops matching", break_join_stat)

    shutil.rmtree(tmp, ignore_errors=True)
    print("[874 selftest] " + ("OK -- every invariant fired" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "build"
    if mode == "verify":
        sys.exit(verify())
    if mode == "selftest":
        sys.exit(selftest())
    build()
    sys.exit(verify())
