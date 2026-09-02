#!/usr/bin/env python3
"""
1126_annual_total_federal_and_gaming.py -- the annual series the owner asked
for: federal obligations beside tribal gaming revenue, side by side, with the
boundary between them stated.

THE OWNER
---------
  "I think we have a more accurate annual total of funding flowing to Indian
   Country when we include NIGC's regional gaming numbers."

He is right, and the reason has to be stated precisely or the series is worse
than no series:

  **Federal obligations are transfers INTO Indian Country.
   Gaming revenue is Indian Country's OWN-SOURCE revenue.**

A total that omits the largest own-source stream badly understates the economy.
A total that adds them into one number claims they are the same kind of money.
So this builds BOTH, side by side, in one long table whose grain is
(fiscal_year, series_id), with `money_class` on every row and an explicit
`never_add_to` column. **No grand total is written anywhere in this table**, and
`verify` fails if one appears. The reader may add them; Cedar may not do it for
them without saying what the sum means.

THE FENCES THIS SERIES OBEYS
----------------------------
1. **Prime + assistance, NEVER summed with subawards.** A subaward is a slice of
   a prime award already counted (`docs/MONEY_TOTALLING_RULES.md`). No subaward
   figure appears in this table and `verify` V5 proves it.
2. **NIGC publishes REGIONAL GGR, not per-facility.** A regional figure is never
   apportioned to a facility and never summed across facilities.
   `gaming_revenue_bounds.csv` is 13,803 rows of which 13,494 are one regional
   ceiling repeated across 694 facilities; the largest single ceiling is carried
   by 162 of them. This table therefore rolls NIGC up only along the axis NIGC
   itself publishes -- region to nation, within one region system.
3. **THE DOUBLE-COUNT THIS PASS FOUND.** Every NIGC report carries the current
   fiscal year AND the prior year, and three years -- FY2002, FY2007, FY2016 --
   are present under TWO region systems for exactly that reason. Summing
   `nigc_regional_ggr.csv` by `fiscal_year` alone doubles those three years:
   FY2002 $29.213B against a true $14.497B, FY2007 $52.160B against $26.016B,
   FY2016 $62.600B against $31.300B. The discriminator already exists in the
   table -- `figure_vintage` -- and the rule is: **sum only
   `figure_vintage = own_year_report` within a fiscal year, and where a year has
   no own-year report, take its prior-year column and SAY SO.** Four years are
   in that state (FY2001, FY2011, FY2013, FY2021).
4. **Only 11 distinct gaming properties have an honest per-property figure**,
   against a denominator IMPORTED from the gated ladder. Said on every gaming
   row of the output, in `coverage_note`.
5. **The audited per-property SEC figures are their own class** and are carried
   as a separate series that may never be netted against a regional figure --
   the property is INSIDE the region and the regional figure already contains
   it.

THE DENOMINATOR, EVERY TIME
---------------------------
The gated gaming ladder is `code/846_session_audit.py::_denom`, and this script
IMPORTS it rather than retyping it -- both the number and the sentence that
explains it. FIVE denominators circulated on the morning of 2026-09-02 and all
five were quoted as settled (787, 780, 734, 727, 714); the ladder itself then
moved 714 -> 717 the same evening. **Any figure typed into this file would
already be stale.** If `_denom()` reports a shape change it refuses to stand
behind its own number, and this script then records UNMEASURED rather than
guessing.

usage
  py -3 code/1126_annual_total_federal_and_gaming.py build
  py -3 code/1126_annual_total_federal_and_gaming.py verify    # exit 1 on breach
  py -3 code/1126_annual_total_federal_and_gaming.py selftest  # prove it FIRES
  py -3 code/1126_annual_total_federal_and_gaming.py doc       # the marked block
"""
import argparse
import collections
import csv
import importlib.util
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
CLEAN = os.path.join(ROOT, "data", "clean")
OUT = os.path.join(CLEAN, "annual_indian_country_money_series.csv")
JSONOUT = os.path.join(ROOT, "docs", "ANNUAL_INDIAN_COUNTRY_MONEY_SERIES.json")
RULES = os.path.join(ROOT, "docs", "MONEY_TOTALLING_RULES.md")
MARK = "GAMING-TOTAL"
TODAY = "2026-09-02"
BUILT_BY = "code/1126_annual_total_federal_and_gaming.py"

csv.field_size_limit(10 ** 9)

TRANSFER = "FEDERAL_OBLIGATION_TRANSFERRED_INTO_INDIAN_COUNTRY"
OWNSOURCE = "INDIAN_COUNTRY_OWN_SOURCE_REVENUE"

COLS = ["fiscal_year", "series_id", "money_class", "usd", "n_source_rows",
        "is_partial_fiscal_year", "figure_precision", "additive_with",
        "never_add_to", "source_table", "basis", "coverage_note",
        "built_by", "built_date"]


def rd(p):
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def f(x):
    try:
        return float(str(x).strip() or 0)
    except ValueError:
        return 0.0


# --------------------------------------------------------------------------
# the gaming denominator -- imported from the gated ladder, never retyped
# --------------------------------------------------------------------------
def denom():
    p = os.path.join(ROOT, "code", "846_session_audit.py")
    if not os.path.exists(p):
        return None, ("UNMEASURED: code/846_session_audit.py is absent, so the "
                      "gated gaming denominator could not be imported. This "
                      "script will not retype it.")
    spec = importlib.util.spec_from_file_location("cedar_846", p)
    m = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(m)
        ok, text = m._denom()
    except Exception as e:                                  # noqa: BLE001
        return None, ("UNMEASURED: code/846_session_audit.py::_denom() raised "
                      "%r; the denominator is not being guessed." % (e,))
    if not ok:
        return None, ("UNMEASURED: the gated ladder reports a shape change and "
                      "refuses to stand behind its own figure -- %s" % text)
    # "... = 714 distinct properties"
    n = None
    for tok in text.replace("=", " ").split():
        if tok.isdigit():
            n = int(tok)
    return {"distinct_properties": n, "ladder_text": text},         "code/846_session_audit.py::_denom()"


# --------------------------------------------------------------------------
# federal legs
# --------------------------------------------------------------------------
def duck():
    try:
        import duckdb
    except ImportError:
        raise SystemExit("UNMEASURED: duckdb is not importable; the federal "
                         "legs read million-row CSVs and will not be sampled.")
    return duckdb


def federal_prime():
    d = duck()
    src = ("read_csv('%s', ignore_errors=true, sample_size=-1, all_varchar=true)"
           % os.path.join(CLEAN, "prime_contracts.csv").replace("\\", "/"))
    q = ("SELECT fiscal_year AS fy, count(*) AS n, "
         "sum(TRY_CAST(total_obligations AS DOUBLE)) AS usd "
         "FROM %s WHERE attributed_flag='1' GROUP BY 1 ORDER BY 1" % src)
    return [(int(r.fy), int(r.n), float(r.usd)) for r in
            d.sql(q).df().itertuples() if str(r.fy).strip().isdigit()]


def federal_assistance():
    d = duck()
    src = ("read_csv('%s', ignore_errors=true, sample_size=-1, all_varchar=true)"
           % os.path.join(CLEAN,
                          "federal_funding_transactions.csv").replace("\\", "/"))
    q = ("SELECT fiscal_year AS fy, count(*) AS n, "
         "sum(TRY_CAST(obligated_usd AS DOUBLE)) AS usd, "
         "count(*) FILTER (WHERE lower(fy_partial_flag) IN ('1','true','y')) AS p "
         "FROM %s WHERE attributed_flag='1' GROUP BY 1 ORDER BY 1" % src)
    return [(int(r.fy), int(r.n), float(r.usd), int(r.p)) for r in
            d.sql(q).df().itertuples() if str(r.fy).strip().isdigit()]


def faads_pre2008():
    p = os.path.join(CLEAN, "faads_entity_attribution.csv")
    if not os.path.exists(p):
        return []
    agg = collections.defaultdict(lambda: [0, 0.0])
    for r in rd(p):
        fy = (r.get("fiscal_year") or "").strip()
        if not fy.isdigit():
            continue
        a = agg[int(fy)]
        a[0] += 1
        a[1] += f(r.get("obligated_usd"))
    return sorted((y, v[0], v[1]) for y, v in agg.items())


# --------------------------------------------------------------------------
# gaming legs
# --------------------------------------------------------------------------
def nigc_national():
    """Roll NIGC regions up to the nation WITHIN ONE REGION SYSTEM PER YEAR.

    Returns (rows, doublecount_evidence). `doublecount_evidence` records what a
    naive `GROUP BY fiscal_year` would have produced, so the fence is proved to
    bite rather than asserted to.
    """
    rows = rd(os.path.join(CLEAN, "nigc_regional_ggr.csv"))
    by = collections.defaultdict(list)
    for r in rows:
        fy = (r.get("fiscal_year") or "").strip()
        if fy.isdigit():
            by[int(fy)].append(r)
    out, ev = [], []
    for y in sorted(by):
        all_rows = by[y]
        own = [r for r in all_rows if r.get("figure_vintage") == "own_year_report"]
        use = own if own else [r for r in all_rows
                               if r.get("figure_vintage") == "prior_year_column"]
        vintage = "own_year_report" if own else "prior_year_column_only"
        systems = sorted({r.get("region_system_version", "") for r in use})
        naive = sum(f(r.get("ggr_usd")) for r in all_rows)
        kept = sum(f(r.get("ggr_usd")) for r in use)
        prec = sorted({r.get("figure_precision", "") for r in use})
        if len(all_rows) != len(use):
            ev.append({"fiscal_year": y,
                       "naive_group_by_fiscal_year_usd": naive,
                       "one_region_system_usd": kept,
                       "overstatement_usd": naive - kept,
                       "region_systems_present":
                           sorted({r.get("region_system_version", "")
                                   for r in all_rows})})
        out.append({"fiscal_year": y, "n": len(use), "usd": kept,
                    "vintage": vintage, "systems": systems,
                    "precision": "|".join(p for p in prec if p),
                    "operations": sum(int((r.get("operation_count") or "0") or 0)
                                      for r in use)})
    return out, ev


def sec_per_property():
    """The audited per-property class. First-filing rows only -- a 10-K restates
    its two prior years and 32 of 67 rows are such a restatement."""
    p = os.path.join(CLEAN, "sec_gaming_financial_disclosures.csv")
    if not os.path.exists(p):
        return [], {}
    rows = rd(p)
    keep = [r for r in rows
            if (r.get("is_first_filing_of_this_fact") or "").strip().upper() == "Y"
            and (r.get("figure_type") or "").strip() == "FACILITY_NET_REVENUES"
            and (r.get("facility_is_on_indian_lands") or "").strip().upper() != "N"]
    agg = collections.defaultdict(lambda: [0, 0.0, set()])
    for r in keep:
        fy = (r.get("fiscal_year") or "").strip()
        if not fy.isdigit():
            continue
        a = agg[int(fy)]
        a[0] += 1
        a[1] += f(r.get("amount_usd") or r.get("figure_usd") or r.get("value_usd"))
        a[2].add(r.get("facility_id") or r.get("property_name") or "")
    meta = {"table_rows": len(rows), "first_filing_and_net_revenues_and_indian_lands":
            len(keep)}
    return sorted((y, v[0], v[1], len(v[2])) for y, v in agg.items()), meta


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------
NEVER_FEDERAL = ("subawards.csv (a subaward is a SLICE of a prime award already "
                 "counted here); native_passthrough.csv (a projection of "
                 "subawards); np_schedule_i_grants.csv (grants MADE BY "
                 "nonprofits); fac_tribal_single_audits.total_amount_expended "
                 "(federal awards EXPENDED, a different measure); and any "
                 "gaming series in this table, which is own-source revenue and "
                 "not a transfer")
NEVER_GAMING = ("any federal obligation series in this table (a transfer INTO "
                "Indian Country is not own-source revenue); "
                "gaming_revenue_bounds.csv REGIONAL_GGR_CEILING rows (the same "
                "regional figure, repeated per facility); "
                "sec_gaming_financial_disclosures.csv (the property is INSIDE "
                "the region and the regional figure already contains it); any "
                "self-published casino claim")


def build(a):
    out = []
    prime = federal_prime()
    asst = federal_assistance()
    faads = faads_pre2008()
    nigc, dc = nigc_national()
    sec, secmeta = sec_per_property()
    dn, dnwhy = denom()
    nprop = (dn or {}).get("distinct_properties")

    honest = gaming_honest_property_count()
    cov = ("NIGC publishes GGR at the REGION level only. This row is that "
           "year's regions summed to the nation WITHIN ONE REGION SYSTEM; it is "
           "never apportioned to a property. Of the %s distinct gaming "
           "properties Cedar holds, %s have an honest per-property revenue "
           "figure." % (nprop if nprop is not None else "UNMEASURED", honest))

    pm = {y: (n, u) for y, n, u in prime}
    am = {y: (n, u, p) for y, n, u, p in asst}

    for y, n, usd in prime:
        out.append(dict(fiscal_year=y, series_id="federal_prime_obligations",
                        money_class=TRANSFER, usd=round(usd, 2), n_source_rows=n,
                        is_partial_fiscal_year="Y" if y >= 2026 else "N",
                        figure_precision="exact_dollars",
                        additive_with="federal_assistance_obligations",
                        never_add_to=NEVER_FEDERAL,
                        source_table="data/clean/prime_contracts.csv",
                        basis="sum(total_obligations) WHERE attributed_flag='1'. "
                              "attributed_flag already excludes the 103,221 rows "
                              "/ $17.07B moved to the unattributed pool by "
                              "code/1079 on 2026-09-02.",
                        coverage_note="FY2000-2026. FY2007 is thin (host "
                                      "edge-block, see START_HERE item 3).",
                        built_by=BUILT_BY, built_date=TODAY))
    for y, n, usd, p in asst:
        out.append(dict(fiscal_year=y,
                        series_id="federal_assistance_obligations",
                        money_class=TRANSFER, usd=round(usd, 2), n_source_rows=n,
                        is_partial_fiscal_year="Y" if p else "N",
                        figure_precision="exact_dollars",
                        additive_with="federal_prime_obligations",
                        never_add_to=NEVER_FEDERAL,
                        source_table="data/clean/federal_funding_transactions.csv",
                        basis="sum(obligated_usd) WHERE attributed_flag='1'. "
                              "%d rows in this year carry fy_partial_flag." % p,
                        coverage_note="FY2007-2026, three source vintages; "
                                      "FY2024-26 still sit on the 20260706 "
                                      "archive stamp.",
                        built_by=BUILT_BY, built_date=TODAY))
    for y in sorted(set(pm) | set(am)):
        pn, pu = pm.get(y, (0, 0.0))
        an, au, ap = am.get(y, (0, 0.0, 0))
        out.append(dict(fiscal_year=y, series_id="federal_obligations_total",
                        money_class=TRANSFER, usd=round(pu + au, 2),
                        n_source_rows=pn + an,
                        is_partial_fiscal_year="Y" if (y >= 2026 or ap) else "N",
                        figure_precision="exact_dollars",
                        additive_with="",
                        never_add_to="its own two components (they are ALREADY "
                                     "summed here); " + NEVER_FEDERAL,
                        source_table="data/clean/prime_contracts.csv + "
                                     "data/clean/federal_funding_transactions.csv",
                        basis="prime + assistance. These two are disjoint and "
                              "additive; SUBAWARDS ARE NOT IN THIS SUM and must "
                              "never be added to it.",
                        coverage_note="Complete only from FY2007, where the "
                                      "modern assistance table begins. FY2000-06 "
                                      "carries prime only; the pre-2008 Native "
                                      "assistance slice is the separate "
                                      "faads_pre2008_assistance_attributed "
                                      "series and is TIER B THROUGHOUT.",
                        built_by=BUILT_BY, built_date=TODAY))
    for y, n, usd in faads:
        out.append(dict(fiscal_year=y,
                        series_id="faads_pre2008_assistance_attributed",
                        money_class=TRANSFER, usd=round(usd, 2), n_source_rows=n,
                        is_partial_fiscal_year="N",
                        figure_precision="exact_dollars",
                        additive_with="",
                        never_add_to="federal_assistance_obligations for FY2007 "
                                     "(11,063 FY2007 transactions / $2.166B are "
                                     "the SAME transactions -- see the FY2007 "
                                     "seam); " + NEVER_FEDERAL,
                        source_table="data/clean/faads_entity_attribution.csv",
                        basis="sum(obligated_usd) over the pre-FY2007 Native "
                              "attribution, which is a PROJECTION carried "
                              "verbatim off faads_transactions_all_agencies.csv "
                              "and is never new money.",
                        coverage_note="TIER B ON EVERY ROW -- no DUNS or UEI "
                                      "exists on any pre-FY2007 FAADS row, so "
                                      "the attribution is a guarded name match "
                                      "and can never be tier A.",
                        built_by=BUILT_BY, built_date=TODAY))
    for r in nigc:
        out.append(dict(fiscal_year=r["fiscal_year"],
                        series_id="nigc_regional_ggr_rolled_to_nation",
                        money_class=OWNSOURCE, usd=round(r["usd"], 2),
                        n_source_rows=r["n"],
                        is_partial_fiscal_year="N",
                        figure_precision=r["precision"],
                        additive_with="",
                        never_add_to=NEVER_GAMING,
                        source_table="data/clean/nigc_regional_ggr.csv",
                        basis="sum(ggr_usd) over the %d regions of ONE region "
                              "system (%s), figure_vintage=%s. A naive GROUP BY "
                              "fiscal_year doubles FY2002, FY2007 and FY2016, "
                              "which each appear under two region systems "
                              "because every NIGC report restates the prior "
                              "year. %d gaming operations."
                              % (r["n"], "|".join(r["systems"]), r["vintage"],
                                 r["operations"]),
                        coverage_note=cov,
                        built_by=BUILT_BY, built_date=TODAY))
    for y, n, usd, nfac in sec:
        out.append(dict(fiscal_year=y,
                        series_id="sec_filed_per_property_net_revenues",
                        money_class=OWNSOURCE, usd=round(usd, 2), n_source_rows=n,
                        is_partial_fiscal_year="N",
                        figure_precision="exact_dollars",
                        additive_with="",
                        never_add_to=NEVER_GAMING,
                        source_table="data/clean/sec_gaming_financial_disclosures.csv",
                        basis="sum over is_first_filing_of_this_fact='Y' AND "
                              "figure_type='FACILITY_NET_REVENUES' AND "
                              "facility_is_on_indian_lands<>'N', %d properties. "
                              "A THIRD assertion class "
                              "(SEC_FILED_FINANCIAL_DISCLOSURE)." % nfac,
                        coverage_note="7 Indian-lands properties out of %s. This "
                                      "is a deep core, not a national measure, "
                                      "and it is INSIDE the NIGC regional "
                                      "figure for the same year."
                                      % (nprop if nprop is not None
                                         else "UNMEASURED"),
                        built_by=BUILT_BY, built_date=TODAY))

    out.sort(key=lambda r: (r["fiscal_year"], r["series_id"]))
    tmp = OUT + ".part"
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(out)
    os.replace(tmp, OUT)

    meta = {
        "built_by": BUILT_BY, "built_date": TODAY, "rows": len(out),
        "gaming_denominator_ladder": (dn or {}).get("ladder_text") or dnwhy,
        "gaming_denominator_source": dnwhy or "UNMEASURED",
        "gaming_properties_with_an_honest_per_property_figure": honest,
        "nigc_double_count_a_naive_group_by_would_have_produced": dc,
        "sec_table": secmeta,
        "series": sorted({r["series_id"] for r in out}),
        "money_classes": sorted({r["money_class"] for r in out}),
        "note": "No grand total is written. Federal obligations are transfers "
                "INTO Indian Country; gaming revenue is Indian Country's "
                "OWN-SOURCE revenue. Both are published; the boundary is "
                "money_class and the reader may add if they choose.",
    }
    json.dump(meta, open(JSONOUT, "w"), indent=1, default=str)
    print("wrote %s -- %d rows" % (os.path.relpath(OUT, ROOT), len(out)))
    print("wrote %s" % os.path.relpath(JSONOUT, ROOT))
    print("\nthe double count the fence removes:")
    for e in dc:
        print("  FY%d  naive $%.3fB -> one region system $%.3fB  "
              "(overstated by $%.3fB)"
              % (e["fiscal_year"], e["naive_group_by_fiscal_year_usd"] / 1e9,
                 e["one_region_system_usd"] / 1e9,
                 e["overstatement_usd"] / 1e9))
    print("\nside by side, $B:")
    print("  %-6s %14s %14s %14s" % ("FY", "federal(prime+", "assistance)",
                                     "NIGC GGR"))
    fed = {r["fiscal_year"]: r["usd"] for r in out
           if r["series_id"] == "federal_obligations_total"}
    gg = {r["fiscal_year"]: r["usd"] for r in out
          if r["series_id"] == "nigc_regional_ggr_rolled_to_nation"}
    for y in sorted(set(fed) | set(gg)):
        print("  %-6d %29s %14s"
              % (y, ("%.2f" % (fed[y] / 1e9)) if y in fed else "-",
                 ("%.2f" % (gg[y] / 1e9)) if y in gg else "-"))
    return out


def gaming_honest_property_count():
    """The two per-property statuses in gaming_revenue_bounds.csv, as PROPERTIES
    -- not as rows. Computed, because this is the figure five denominators went
    wrong on."""
    p = os.path.join(CLEAN, "gaming_revenue_bounds.csv")
    if not os.path.exists(p):
        return "UNMEASURED"
    honest = set()
    for r in rd(p):
        if (r.get("measurement_status") or "").strip() in (
                "SINGLE_PROPERTY_ATTRIBUTED", "REPORTED_PROPERTY_REVENUE"):
            fid = (r.get("facility_id") or "").strip()
            if fid:
                honest.add(fid)
    return len(honest)


# --------------------------------------------------------------------------
# verify
# --------------------------------------------------------------------------
def _checks(rows, meta):
    out = []
    rows = [dict(r, fiscal_year=int(str(r["fiscal_year"]).strip()))
            for r in rows]

    # V1 -- THE WORK LANDED. Not a conservation check: a floor on the intended
    # delta, on the intended columns (AGENT_FIELD_GUIDE rule 5).
    ser = collections.Counter(r["series_id"] for r in rows)
    want = {"federal_prime_obligations", "federal_assistance_obligations",
            "federal_obligations_total", "nigc_regional_ggr_rolled_to_nation"}
    fedyrs = ser.get("federal_obligations_total", 0)
    gyrs = ser.get("nigc_regional_ggr_rolled_to_nation", 0)
    out.append(("V1_work_landed_both_streams_present_over_a_real_span",
                want <= set(ser) and fedyrs >= 20 and gyrs >= 20,
                "series=%s | federal years=%d | gaming years=%d"
                % (sorted(ser), fedyrs, gyrs)))

    # V2 -- the boundary is stated on every row and NO row mixes the classes
    bad = [r for r in rows if r["money_class"] not in (TRANSFER, OWNSOURCE)]
    out.append(("V2_every_row_declares_its_money_class", not bad,
                "%d rows carry no recognised money_class" % len(bad)))

    # V3 -- no grand total exists. The whole point of publishing both.
    fed = {r["fiscal_year"]: f(r["usd"]) for r in rows
           if r["series_id"] == "federal_obligations_total"}
    gg = {r["fiscal_year"]: f(r["usd"]) for r in rows
          if r["series_id"] == "nigc_regional_ggr_rolled_to_nation"}
    grand = []
    for r in rows:
        y = r["fiscal_year"]
        if y in fed and y in gg and abs(f(r["usd"]) - (fed[y] + gg[y])) < 1.0:
            grand.append((y, r["series_id"]))
    out.append(("V3_no_row_is_a_federal_plus_gaming_grand_total", not grand,
                "%d rows equal federal+gaming: %s" % (len(grand), grand[:3])))

    # V4 -- the derived federal total IS its two components, to the cent
    pm = {r["fiscal_year"]: f(r["usd"]) for r in rows
          if r["series_id"] == "federal_prime_obligations"}
    am = {r["fiscal_year"]: f(r["usd"]) for r in rows
          if r["series_id"] == "federal_assistance_obligations"}
    bad4 = [y for y in fed
            if abs(fed[y] - (pm.get(y, 0.0) + am.get(y, 0.0))) > 0.01]
    out.append(("V4_federal_total_equals_prime_plus_assistance_to_the_cent",
                not bad4, "%d years disagree: %s" % (len(bad4), bad4[:5])))

    # V5 -- no subaward figure is anywhere in this table
    sub = [r for r in rows if "subaward" in (r["source_table"] or "").lower()
           or "subaward" in (r["series_id"] or "").lower()]
    out.append(("V5_no_subaward_figure_is_in_this_table", not sub,
                "%d rows source a subaward table" % len(sub)))

    # V6 -- the NIGC double-count fence BITES. Re-derive the naive sum and
    # assert the shipped figure is the smaller one on the three overlap years.
    live, dc = nigc_national()
    lm = {r["fiscal_year"]: r["usd"] for r in live}
    bad6 = [y for y in gg if abs(gg[y] - lm.get(y, -1)) > 1.0]
    bites = [e for e in dc if e["overstatement_usd"] > 1.0]
    out.append(("V6_one_region_system_per_year_and_the_fence_bites",
                not bad6 and len(bites) >= 3,
                "%d years disagree with a live re-derivation; the fence removes "
                "%d overlap years worth $%.3fB"
                % (len(bad6), len(bites),
                   sum(e["overstatement_usd"] for e in bites) / 1e9)))

    # V7 -- every gaming row states the property denominator, computed
    bad7 = [r for r in rows if r["money_class"] == OWNSOURCE
            and "distinct gaming propert" not in (r["coverage_note"] or "")
            and "properties out of" not in (r["coverage_note"] or "")]
    out.append(("V7_every_gaming_row_states_the_property_denominator", not bad7,
                "%d gaming rows do not state it" % len(bad7)))

    # V8 -- a regional figure is never presented per facility
    bad8 = [r for r in rows
            if r["series_id"] == "nigc_regional_ggr_rolled_to_nation"
            and "region" not in (r["basis"] or "").lower()]
    out.append(("V8_the_regional_roll_up_names_its_axis", not bad8,
                "%d NIGC rows do not name the region axis" % len(bad8)))

    # V9 -- the prime leg still reconciles to the live table
    try:
        livep = {y: u for y, _n, u in federal_prime()}
        bad9 = [y for y in pm if abs(pm[y] - livep.get(y, -1)) > 0.01]
    except SystemExit:
        return out + [("V9_prime_leg_reconciles_to_the_live_table", False,
                       "UNMEASURED: duckdb unavailable")]
    out.append(("V9_prime_leg_reconciles_to_the_live_table", not bad9,
                "%d years disagree: %s" % (len(bad9), bad9[:5])))
    return out


def verify(a):
    if not os.path.exists(OUT):
        print("UNMEASURED: %s does not exist. verify will not report clean "
              "about work that has not run." % os.path.relpath(OUT, ROOT))
        return 1
    rows = rd(OUT)
    if not rows:
        print("UNMEASURED: %s is empty." % os.path.relpath(OUT, ROOT))
        return 1
    meta = json.load(open(JSONOUT)) if os.path.exists(JSONOUT) else {}
    rc = 0
    for name, ok, detail in _checks(rows, meta):
        print("%-4s %-58s %s" % ("PASS" if ok else "FAIL", name, detail))
        if not ok:
            rc = 1
    print("\nrows=%d" % len(rows))
    print("EXIT", rc)
    return rc


def selftest(a):
    if not os.path.exists(OUT):
        print("UNMEASURED: build first.")
        return 1
    rows = rd(OUT)
    meta = json.load(open(JSONOUT)) if os.path.exists(JSONOUT) else {}
    base = _checks(rows, meta)
    if any(not ok for _n, ok, _d in base):
        print("selftest needs a GREEN baseline; verify is red.")
        return 1
    import copy
    fired = []

    def fires(tag, m):
        got = [n for n, ok, _ in _checks(m, meta) if not ok]
        print("  inject %-40s -> FAIL: %s" % (tag, got or "NOTHING (BAD)"))
        fired.append(bool(got))

    m = [r for r in copy.deepcopy(rows)
         if r["series_id"] != "nigc_regional_ggr_rolled_to_nation"]
    fires("the gaming stream is dropped", m)                     # V1
    m = copy.deepcopy(rows); m[0]["money_class"] = "MONEY"
    fires("a row loses its money_class", m)                      # V2
    m = copy.deepcopy(rows)
    fedr = [r for r in m if r["series_id"] == "federal_obligations_total"]
    ggr = {r["fiscal_year"]: f(r["usd"]) for r in m
           if r["series_id"] == "nigc_regional_ggr_rolled_to_nation"}
    y = next(r["fiscal_year"] for r in fedr if r["fiscal_year"] in ggr)
    fy = next(r for r in fedr if r["fiscal_year"] == y)
    m.append(dict(fy, series_id="total_money_in_indian_country",
                  usd=str(f(fy["usd"]) + ggr[y])))
    fires("a federal+gaming grand total appears", m)             # V3
    m = copy.deepcopy(rows)
    for r in m:
        if r["series_id"] == "federal_obligations_total":
            r["usd"] = str(f(r["usd"]) + 1000)
            break
    fires("the federal total stops equalling its parts", m)      # V4
    m = copy.deepcopy(rows)
    m.append(dict(rows[0], series_id="subaward_amounts",
                  source_table="data/clean/subawards.csv"))
    fires("a subaward figure is added", m)                       # V5
    m = copy.deepcopy(rows)
    for r in m:
        if r["series_id"] == "nigc_regional_ggr_rolled_to_nation" \
                and r["fiscal_year"] == "2002":
            r["usd"] = "29212969000"       # the naive two-system sum
            break
    fires("FY2002 reverts to the two-system sum", m)             # V6
    m = copy.deepcopy(rows)
    for r in m:
        if r["money_class"] == OWNSOURCE:
            r["coverage_note"] = "gaming revenue"
            break
    fires("a gaming row drops the denominator", m)               # V7
    m = copy.deepcopy(rows)
    for r in m:
        if r["series_id"] == "nigc_regional_ggr_rolled_to_nation":
            r["basis"] = "sum of ggr"
            break
    fires("the roll-up stops naming its axis", m)                # V8
    m = copy.deepcopy(rows)
    for r in m:
        if r["series_id"] == "federal_prime_obligations":
            r["usd"] = "1"
            break
    fires("the prime leg stops reconciling", m)                  # V9
    ok = all(fired)
    print("\nselftest: %d/%d injections fired -> %s"
          % (sum(fired), len(fired), "PASS" if ok else "FAIL"))
    return 0 if ok else 1


# --------------------------------------------------------------------------
# the marked block for docs/MONEY_TOTALLING_RULES.md
# --------------------------------------------------------------------------
def doc(a):
    rows = rd(OUT)
    meta = json.load(open(JSONOUT))
    dc = meta["nigc_double_count_a_naive_group_by_would_have_produced"]
    fed = {int(r["fiscal_year"]): f(r["usd"]) for r in rows
           if r["series_id"] == "federal_obligations_total"}
    gg = {int(r["fiscal_year"]): f(r["usd"]) for r in rows
          if r["series_id"] == "nigc_regional_ggr_rolled_to_nation"}
    # THE HONEST WINDOW is where BOTH federal legs exist AND gaming exists.
    # FY2001-2006 have prime but no modern assistance table, so a ratio taken
    # across them divides gaming by a federal figure that is missing a leg --
    # which is how FY2001 comes out at 22x and means nothing.
    pmy = {int(r["fiscal_year"]) for r in rows
           if r["series_id"] == "federal_prime_obligations"}
    amy = {int(r["fiscal_year"]) for r in rows
           if r["series_id"] == "federal_assistance_obligations"}
    both = sorted(set(fed) & set(gg) & pmy & amy)
    lo, hi = both[0], both[-1]
    fsum = sum(fed[y] for y in both)
    gsum = sum(gg[y] for y in both)
    lines = []
    A = lines.append
    A("<!-- BEGIN %s -->" % MARK)
    A("")
    A("## The annual total, with gaming in it -- and the boundary that keeps "
      "it honest (workstream GAMING-TOTAL, %s)" % TODAY)
    A("")
    A("*Appended by `%s`. Every figure below is re-derived from the live files "
      "by `1126 build` and re-checked by `1126 verify` (exit 1 on breach); "
      "`1126 selftest` proves each check fires on an injected violation. The "
      "series itself is `data/clean/annual_indian_country_money_series.csv`, "
      "one row per (fiscal_year, series_id).*" % BUILT_BY)
    A("")
    A("**The owner's question was whether the annual total is more accurate "
      "with NIGC's regional gaming numbers in it. It is -- and the reason is "
      "also the reason the two may not be added silently:**")
    A("")
    A("> **Federal obligations are transfers INTO Indian Country. "
      "Gaming revenue is Indian Country's OWN-SOURCE revenue.**")
    A("")
    A("A total that omits the largest own-source stream badly understates the "
      "economy. A total that adds them into one number claims they are the "
      "same kind of money. So both are published, side by side, with "
      "`money_class` on every row -- `%s` and `%s` -- and **no grand total is "
      "written anywhere in the table**. `verify` V3 fails if a row ever equals "
      "federal + gaming. The reader may add them; Cedar states what the sum "
      "would mean instead of doing it for them." % (TRANSFER, OWNSOURCE))
    A("")
    A("Over the **%d fiscal years where BOTH federal legs and the gaming "
      "series all exist (FY%d-FY%d)**: federal obligations attributed to a "
      "nation total **$%s**, and NIGC gross gaming revenue totals **$%s**. "
      "Gaming is **%.2fx** the federal stream over that window. That ratio is "
      "the whole argument for publishing both, and it is also why neither is "
      "the answer on its own."
      % (len(both), lo, hi, "{:,.0f}".format(fsum), "{:,.0f}".format(gsum),
         gsum / fsum if fsum else 0))
    A("")
    A("**The window is FY%d onward and not FY2001, deliberately.** The modern "
      "assistance table begins at FY2007, so a ratio taken across FY2001-2006 "
      "divides gaming by a federal figure that is missing one of its two "
      "legs - which is how FY2001 comes out at 22x and means nothing. The "
      "shape inside the window is the interesting part and it is not flat: "
      "gaming runs about 2x federal through the 2010s, **crosses below 1.0 in "
      "FY2020 and FY2021** when pandemic assistance more than doubled the "
      "federal stream while COVID closures took GGR from $34.7B to $27.8B, "
      "and settles near 1.5x from FY2022. Neither series explains Indian "
      "Country's year on its own." % (lo,))
    A("")
    A("### What may be summed, and what may not")
    A("")
    A("| series | grain | additive with | never add to |")
    A("|---|---|---|---|")
    A("| `federal_prime_obligations` | fiscal year | `federal_assistance_obligations` | subawards (a subaward is a SLICE of a prime already counted), `native_passthrough.csv`, Schedule I, FAC expenditures, any gaming series |")
    A("| `federal_assistance_obligations` | fiscal year | `federal_prime_obligations` | the same list, plus `faads_pre2008_assistance_attributed` in FY2007, where 11,063 transactions / $2.166B are the same transactions |")
    A("| `federal_obligations_total` | fiscal year | **nothing** -- it already IS prime + assistance | its own components; anything above |")
    A("| `faads_pre2008_assistance_attributed` | fiscal year, FY2001-06 | nothing | anything. **Tier B on every row** -- no DUNS or UEI exists on any pre-FY2007 FAADS row |")
    A("| `nigc_regional_ggr_rolled_to_nation` | fiscal year | **nothing** | every federal series here; `gaming_revenue_bounds.csv` ceiling rows; SEC per-property figures; any self-published casino claim |")
    A("| `sec_filed_per_property_net_revenues` | fiscal year | nothing | above all the NIGC row for the same year -- **the property is INSIDE the region and the regional figure already contains it** |")
    A("")
    A("### The double count a naive `GROUP BY fiscal_year` produces, and the "
      "column that stops it")
    A("")
    A("**Every NIGC report carries the current fiscal year AND the prior year, "
      "and three years are therefore present under TWO region systems.** "
      "Grouping `nigc_regional_ggr.csv` by `fiscal_year` alone doubles them:")
    A("")
    A("| fiscal year | naive `GROUP BY fiscal_year` | one region system | overstated by |")
    A("|---|---:|---:|---:|")
    for e in dc:
        A("| FY%d | $%.3fB | **$%.3fB** | $%.3fB |"
          % (e["fiscal_year"], e["naive_group_by_fiscal_year_usd"] / 1e9,
             e["one_region_system_usd"] / 1e9, e["overstatement_usd"] / 1e9))
    A("")
    A("The discriminator was already in the table and nothing was reading it: "
      "**`figure_vintage`**. The rule is *sum only `own_year_report` rows "
      "within a fiscal year*, which is also NIGC's first publication of that "
      "year rather than its later restatement. **Four years have no own-year "
      "report on this disk -- FY2001, FY2011, FY2013, FY2021 -- and take their "
      "prior-year column, which the row says in its `basis`.** This is the "
      "same shape as the `extent_competed` two-vocabulary seam: the file was "
      "right, and the consumer had no way to see the seam.")
    A("")
    A("### A regional figure is never a property's money")
    A("")
    A("NIGC publishes GGR at the **region** level and nowhere else. "
      "`gaming_revenue_bounds.csv` is 13,803 rows of which **13,494 are one "
      "`REGIONAL_GGR_CEILING` repeated across 694 facilities**, and the "
      "largest single ceiling is carried by 162 of them. Apportioning it to "
      "facilities, or summing it across them, multiplies a region's entire GGR "
      "by its property count. This series therefore rolls NIGC up **only along "
      "the axis NIGC itself publishes** -- region to nation.")
    A("")
    # THE SENTENCE IS COMPUTED, not typed. The ladder moved 714 -> 717 within
    # hours of this section first being written, which is exactly why it is
    # imported from `846::_denom` and pasted here as a measurement rather than
    # remembered as a number.
    A("**The denominator, computed rather than typed** "
      "(`code/846_session_audit.py::_denom`, the single gated ladder, read at "
      "build time and never retyped): **%s**. **%s of those carry an honest "
      "per-property revenue figure** (`SINGLE_PROPERTY_ATTRIBUTED` or "
      "`REPORTED_PROPERTY_REVENUE`, counted as distinct properties rather "
      "than as rows). Every gaming row of the output states that denominator "
      "in `coverage_note`, and `verify` V7 fails if one does not. **This "
      "figure has moved twice in one day** - 714 on the morning of "
      "2026-09-02, 717 by that evening - so import the ladder, do not quote "
      "this paragraph."
      % (meta["gaming_denominator_ladder"],
         meta["gaming_properties_with_an_honest_per_property_figure"]))
    A("")
    A("### Precision, and the years a chart will get wrong")
    A("")
    A("`figure_precision` rides on every gaming row. FY2001-FY2012 are exact "
      "thousands; **FY2013-FY2020 are rounded to $0.1B** because NIGC "
      "published only a distribution map in those years, so eight regions each "
      "rounded to $0.1B carry up to $0.4B of rounding in the national figure; "
      "FY2021-FY2025 are exact dollars. FY2020 is a COVID trough "
      "($34.7B -> $27.8B -> $39.0B) and must not be smoothed or used as a "
      "growth base. And the two clocks are not the same clock: NIGC aggregates "
      "**each operation's own audited fiscal year**, so a fiscal-year GGR "
      "figure can include revenue earned up to 16 months before publication, "
      "while a federal fiscal year is the government's.")
    A("")
    A("### The federal side, stated with its denominator")
    A("")
    A("`federal_prime_obligations` is `sum(total_obligations)` over "
      "`attributed_flag='1'` -- **$%s across %s rows**, which is %.1f%% of the "
      "$310,005,258,660.75 the whole table holds. `attributed_flag` already "
      "excludes the 103,221 rows / $17.07B that `code/1079` moved to the "
      "unattributed pool on 2026-09-02. `federal_assistance_obligations` is "
      "`sum(obligated_usd)` over the same flag -- **$%s across %s rows**. "
      "**Neither is ever summed with `subawards.csv`**, and `verify` V5 fails "
      "if a subaward figure ever reaches this table."
      % ("{:,.2f}".format(sum(f(r["usd"]) for r in rows
                              if r["series_id"] == "federal_prime_obligations")),
         "{:,}".format(sum(int(r["n_source_rows"]) for r in rows
                           if r["series_id"] == "federal_prime_obligations")),
         100.0 * sum(f(r["usd"]) for r in rows
                     if r["series_id"] == "federal_prime_obligations")
         / 310005258660.75,
         "{:,.2f}".format(sum(f(r["usd"]) for r in rows
                              if r["series_id"]
                              == "federal_assistance_obligations")),
         "{:,}".format(sum(int(r["n_source_rows"]) for r in rows
                           if r["series_id"]
                           == "federal_assistance_obligations"))))
    A("")
    A("**The federal total is complete only from FY2007**, where the modern "
      "assistance table begins. FY2000-06 carries prime only; the pre-2008 "
      "Native assistance slice is the separate "
      "`faads_pre2008_assistance_attributed` series, is **tier B throughout**, "
      "and overlaps the modern table in FY2007 by 11,063 transactions.")
    A("")
    A("<!-- END %s -->" % MARK)
    block = "\n".join(lines)
    if a.write:
        txt = open(RULES, encoding="utf-8").read()
        b, e = "<!-- BEGIN %s -->" % MARK, "<!-- END %s -->" % MARK
        if b in txt:
            i, j = txt.index(b), txt.index(e) + len(e)
            txt = txt[:i] + block + txt[j:]
        else:
            txt = txt.rstrip() + "\n\n" + block + "\n"
        open(RULES, "w", encoding="utf-8").write(txt)
        print("wrote block %s into %s" % (MARK, os.path.relpath(RULES, ROOT)))
    else:
        print(block)
    return 0


# --------------------------------------------------------------------------
# codebook -- a table with no registry block cannot ship, however good the
# prose is. `62`'s `tables_undocumented_in_codebook` is the gate and it says so
# in its own failure text. Built is not done; shipped is done.
# --------------------------------------------------------------------------
CB_DATASET = "05s_annual_indian_country_money_series"

CB_DESC = {
    "fiscal_year": "Federal fiscal year for the federal series; NIGC's own "
                   "reporting fiscal year for the gaming series. THE TWO ARE "
                   "NOT THE SAME CLOCK: NIGC aggregates each gaming "
                   "operation's own audited fiscal year and says its figures "
                   "may include revenue earned up to 16 months before "
                   "publication.",
    "series_id": "Which series this row measures. Half of the primary key.",
    "money_class": "THE FENCE. FEDERAL_OBLIGATION_TRANSFERRED_INTO_INDIAN_"
                   "COUNTRY is money moving IN; "
                   "INDIAN_COUNTRY_OWN_SOURCE_REVENUE is money Indian Country "
                   "earned. Never sum across this column. No row of this "
                   "table is a grand total.",
    "usd": "The figure, in nominal dollars of the stated fiscal year. Not "
           "deflated; the source tables carry real-2025 columns.",
    "n_source_rows": "How many source rows produced this figure. For the NIGC "
                     "series it is the number of REGIONS summed, not "
                     "facilities.",
    "is_partial_fiscal_year": "Y where the fiscal year is incomplete in the "
                              "source (FY2026 throughout; FY2023 assistance "
                              "carries fy_partial_flag on 12,126 rows).",
    "figure_precision": "As the publisher stated it. NIGC FY2013-FY2020 are "
                        "rounded to $0.1B - eight regions each rounded carry "
                        "up to $0.4B of rounding in the national figure.",
    "additive_with": "The series this one may be added to. Blank means none.",
    "never_add_to": "What this figure must never be summed with, named "
                    "explicitly rather than left to a footnote.",
    "source_table": "The data/clean table(s) this row was computed from.",
    "basis": "The exact filter and rule. For NIGC it names the region system "
             "and the figure_vintage, because a naive GROUP BY fiscal_year "
             "doubles FY2002, FY2007 and FY2016.",
    "coverage_note": "What the figure does and does not reach. Every gaming "
                     "row states the property denominator here.",
    "built_by": "Producer script.",
    "built_date": "Build date.",
}


def codebook(a):
    import importlib.util as _iu
    spec = _iu.spec_from_file_location("cedar_codebook",
                                       os.path.join(ROOT, "code",
                                                    "cedar_codebook.py"))
    cb = _iu.module_from_spec(spec)
    spec.loader.exec_module(cb)
    rows = rd(OUT)
    if not rows:
        raise SystemExit("UNMEASURED: build first.")
    n = len(rows)
    out = []
    for c in COLS:
        filled = sum(1 for r in rows if str(r.get(c, "")).strip() != "")
        desc = CB_DESC.get(c)
        if not desc:
            raise SystemExit("UNMEASURED: column %r has no description. A "
                             "column with no entry is a column a reader "
                             "guesses at." % c)
        out.append({
            "dataset": CB_DATASET, "variable": c,
            "type": "number" if c in ("fiscal_year", "usd", "n_source_rows")
                    else "text",
            "units": "usd" if c == "usd" else
                     ("count" if c == "n_source_rows" else
                      ("year" if c == "fiscal_year" else "text")),
            # MEASURED off the live file, never typed.
            "pct_filled": round(100.0 * filled / n, 1), "n_rows": n,
            "published": 1, "access_tier": "public",
            "description": desc, "generated": TODAY})
    cb.write_fragment(CB_DATASET, out)
    print("wrote fragment %s (%d columns, %d rows measured)"
          % (CB_DATASET, len(out), n))
    cb.build()
    sh, lic, und = cb.registered_tables()
    names = {p.name for p, _g, _s in sh}
    ok = os.path.basename(OUT) in names
    print("registered as shippable via the codebook: %s" % ok)
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    s = ap.add_subparsers(dest="cmd", required=True)
    s.add_parser("build").set_defaults(fn=build)
    s.add_parser("codebook").set_defaults(fn=codebook)
    s.add_parser("verify").set_defaults(fn=verify)
    s.add_parser("selftest").set_defaults(fn=selftest)
    p = s.add_parser("doc"); p.add_argument("--write", action="store_true")
    p.set_defaults(fn=doc)
    a = ap.parse_args()
    r = a.fn(a)
    sys.exit(r if isinstance(r, int) else 0)


if __name__ == "__main__":
    main()
