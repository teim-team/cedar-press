#!/usr/bin/env python3
"""1128_cicd_benchmark_refresh_2026_09_02.py — the external sanity check, re-run
after the 2026-09-02 attribution corrections, with the two CICD quantities kept
APART.

    py -3 code/1128_cicd_benchmark_refresh_2026_09_02.py measure
    py -3 code/1128_cicd_benchmark_refresh_2026_09_02.py verify     # exit 1 on breach
    py -3 code/1128_cicd_benchmark_refresh_2026_09_02.py selftest   # prove verify FIRES

WHY THIS EXISTS BESIDE 186
--------------------------
`186_cicd_benchmark.py` compares Cedar to CICD's HEADLINE TOTALS. It does not
build a year-by-year series and it does not deflate. `567_stage_cicd_published_
series.py` built the year-by-year comparison once, on 2026-09-01 20:15, against a
Cedar table that has since moved by $15.3B of attribution. This re-runs the Cedar
side FRESH and reports the movement in BOTH directions.

THE TWO CICD QUANTITIES ARE NOT ONE QUANTITY
--------------------------------------------
The 2022 article (Chavis, Gregg, Moreno, 21 Dec 2022) publishes:

  (1) a GRAPHED PRIME SERIES, year by year, 1981-2021, in 2021 dollars. Its
      chart caption says, verbatim: "Federal contracting revenue is from prime
      contracts only." The three entity series sum to $197.99B against the
      article's stated $198B. This is the ONLY CICD quantity with an annual
      shape, and it is the only one Cedar's annual series may be set against.

  (2) a COMBINED PRIME + SUBAWARD TOTAL, stated ONCE in prose: $202B, 1981-2021,
      2021 dollars, i.e. $198B prime + ~$4B sub. There is no annual series
      behind it. Per the owner, who wrote these articles: subawards are messy
      year to year, so the combined figure was reported as a total precisely
      because an annual subaward series could not be stood behind.

CHECKING (2) AGAINST CEDAR'S ANNUAL PRIME SERIES WOULD MANUFACTURE A GAP THAT IS
PURELY DEFINITIONAL. They are computed here as two separate comparisons with two
separate Cedar quantities, and neither is allowed to answer for the other.

CEDAR'S RULES FORBID ADDING A SUBAWARD TO A PRIME
-------------------------------------------------
`docs/MONEY_TOTALLING_RULES.md`: "a subaward is a slice of a prime award already
counted in prime_contracts.csv". So the combined figure is a METHODOLOGICAL
DIFFERENCE to be STATED, not reconciled away. This script computes Cedar's
equivalent BOTH WAYS — under CICD's convention (added) and under Cedar's (prime
only, subawards reported separately as a slice) — and prints them side by side.

THE SUBAWARD DENOMINATOR, ALWAYS STATED
---------------------------------------
FFATA requires a monthly re-filing, so one subaward is many rows (measured on the
FY2021 pull: one $57,500 subaward filed 93 times). Removing the repeats is a
share, and the share must name its denominator, because both figures shipped once
without one and a reviewer correctly concluded one of them had to be wrong. This
script prints BOTH shares beside BOTH totals, computed, never quoted.

UNITS
-----
CICD's series is 2021 dollars. Cedar's `total_obligations` is nominal;
`total_obligations_real2025` is the same money in 2025 dollars. Cedar is put into
2021 dollars by dividing by the table's OWN `deflator_factor_2025` for FY2021 —
the table's deflator, not a new one. CICD does not state its price index (the
caption says only "FRED"), so the residual carries an UNQUANTIFIED index
difference. That is recorded on every comparison, never netted out.

READ-ONLY against every Cedar table. Writes only into
`data/staging/cicd_benchmark_1128/`, which is a staging area for a comparison
against a PUBLISHED figure. Nothing here is ever merged as a Cedar measurement.
"""
from __future__ import annotations

import collections
import csv
import datetime
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
csv.field_size_limit(2 ** 31 - 1)

PRIME = os.path.join(ROOT, "data", "clean", "prime_contracts.csv")
SUB = os.path.join(ROOT, "data", "clean", "subawards.csv")
NEST = os.path.join(ROOT, "data", "clean", "nest_enterprises.csv")
CICD_SERIES = os.path.join(ROOT, "data", "staging", "cicd_published",
                           "cicd_prime_series_1981_2021.csv")
CICD_PROV = os.path.join(ROOT, "data", "staging", "cicd_published", "_provenance.json")
PRIOR_BYYEAR = os.path.join(ROOT, "data", "staging", "cicd_published",
                            "cedar_vs_cicd_by_year.csv")
OUTDIR = os.path.join(ROOT, "data", "staging", "cicd_benchmark_1128")
OUT = os.path.join(OUTDIR, "cedar_vs_cicd_2026_09_02.json")
OUT_CSV = os.path.join(OUTDIR, "cedar_vs_cicd_by_year_refreshed.csv")

# ---------------------------------------------------------------------------
# PUBLISHED FIGURES. Quoted from the source named on each line. NEVER a Cedar
# measurement, never merged, never recomputed from Cedar. Any of them can be
# wrong; a gap is a question, not a verdict on either side.
# ---------------------------------------------------------------------------
PUBLISHED = {
    "prime_series_1981_2021_2021usd": {
        "value": 198_000_000_000.0,
        "unit": "2021 dollars, PRIME ONLY",
        "form": "GRAPHED ANNUAL SERIES (Highcharts series.data, staged by code/567)",
        "source": "CICD 2022-12-21, chart caption verbatim: 'Federal contracting "
                  "revenue is from prime contracts only.'",
    },
    "combined_prime_plus_sub_1981_2021_2021usd": {
        "value": 202_000_000_000.0,
        "unit": "2021 dollars, PRIME + SUBAWARD COMBINED",
        "form": "PROSE TOTAL, stated once, NO annual series behind it",
        "source": "CICD 2022-12-21, recorded in docs/PUBLISHED_LANDSCAPE_2026-08-26.md "
                  "1.4 as '$202B 1981-2021 ($198B prime + $4B sub)'",
    },
    "unique_contracts_1981_2021": {
        "value": 50167,
        "unit": "unique contracts",
        "form": "PROSE COUNT",
        "source": "CICD 2022 appendix, verbatim: 'This rigorous process ... resulted in "
                  "a dataset of 50,167 unique contracts obtained from 1981 ... through 2021.'",
    },
    "entities_linked": {
        "value": 391,
        "unit": "Native entities (79 ANC + 22 NHO + 290 tribes)",
        "form": "PROSE COUNTS",
        "source": "CICD 2022, recorded in docs/PUBLISHED_LANDSCAPE_2026-08-26.md 1.3",
    },
    "enterprises_linked": {
        "value": 2623,
        "unit": "enterprises (1,396 ANC-owned + 117 NHO-owned + 1,110 tribally owned)",
        "form": "PROSE COUNTS",
        "source": "CICD 2022, recorded in docs/PUBLISHED_LANDSCAPE_2026-08-26.md 1.3",
    },
    "need_establishments": {
        "value": 5559,
        "unit": "unique establishments owned by 344 federally recognized tribes",
        "form": "PROSE COUNT",
        "source": "CICD NEED launch, 2025-04-15, verbatim: \"we've identified 5,559 unique "
                  "establishments owned by 344 federally recognized tribes\"",
    },
}

# The window on which Cedar and the graphed series overlap at all.
OVERLAP_LO, OVERLAP_HI = 2000, 2021
# A comparison that produced fewer than this many joined years did not run.
MIN_OVERLAP_YEARS = 22

TRUE = {"1", "true", "t", "y", "yes"}


def _f(x) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0


def stamp(path: str) -> dict:
    st = os.stat(path)
    return {
        "path": os.path.relpath(path, ROOT).replace("\\", "/"),
        "bytes": st.st_size,
        "mtime": datetime.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
        "read_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }


def B(x) -> str:
    return "n/a" if x is None else f"${x/1e9:,.2f}B"


# ---------------------------------------------------------------------------
# 1. CEDAR PRIME — one streaming pass, nominal AND deflated, per fiscal year
# ---------------------------------------------------------------------------
def scan_prime() -> dict:
    t0 = time.time()
    fy = collections.defaultdict(lambda: {
        "rows": 0, "att_rows": 0,
        "obl": 0.0, "att_obl": 0.0,
        "real2025": 0.0, "att_real2025": 0.0,
    })
    defl: dict[int, float] = {}
    defl_conflict: dict[int, set] = collections.defaultdict(set)
    fy_entities = collections.defaultdict(set)
    fy_trbf = collections.defaultdict(set)
    # award-key candidates on attributed FY2000-2021 rows (the SANITY-04 grain)
    k_parent, k_piid, k_piid_uei = set(), set(), set()
    k_award_unique = set()
    k_uei = set()
    k_cage = set()
    # the same keys on ALL FY2000-2021 rows, attributed or not: CICD's 50,167 is
    # the set they VERIFIED as Native, which is an attributed-side quantity, but
    # the unattributed side bounds how much the key could still move.
    k_parent_all, k_piid_all = set(), set()
    rows = 0
    with open(PRIME, encoding="utf-8", errors="replace", newline="") as fh:
        for d in csv.DictReader(fh):
            rows += 1
            try:
                y = int(float(d["fiscal_year"]))
            except Exception:
                continue
            ob = _f(d.get("total_obligations"))
            rl = _f(d.get("total_obligations_real2025"))
            b = fy[y]
            b["rows"] += 1
            b["obl"] += ob
            b["real2025"] += rl
            dv = (d.get("deflator_factor_2025") or "").strip()
            if dv:
                v = round(_f(dv), 6)
                defl.setdefault(y, v)
                defl_conflict[y].add(v)
            att = (d.get("attributed_flag") or "").strip() in TRUE
            if not att:
                if OVERLAP_LO <= y <= OVERLAP_HI:
                    k_parent_all.add(d.get("parent_contract_number", ""))
                    k_piid_all.add(d.get("contract_number", ""))
                continue
            b["att_rows"] += 1
            b["att_obl"] += ob
            b["att_real2025"] += rl
            ti = (d.get("tribe_id") or "").strip()
            if ti:
                fy_entities[y].add(ti)
                if ti.startswith("TRBF-"):
                    fy_trbf[y].add(ti)
            if OVERLAP_LO <= y <= OVERLAP_HI:
                pc = d.get("parent_contract_number", "")
                cn = d.get("contract_number", "")
                ue = d.get("awardee_uei", "")
                k_parent.add(pc)
                k_piid.add(cn)
                k_piid_uei.add((cn, ue))
                k_parent_all.add(pc)
                k_piid_all.add(cn)
                au = (d.get("contract_award_unique_key") or "").strip()
                if au:
                    k_award_unique.add(au)
                if ue:
                    k_uei.add(ue)
                cg = (d.get("cage_code") or "").strip()
                if cg:
                    k_cage.add(cg)

    return dict(
        source=stamp(PRIME),
        elapsed_s=round(time.time() - t0, 1),
        rows=rows,
        by_fy={str(k): {kk: (round(vv, 2) if isinstance(vv, float) else vv)
                        for kk, vv in v.items()} for k, v in sorted(fy.items())},
        deflator_factor_2025_by_fy={str(k): v for k, v in sorted(defl.items())},
        deflator_values_per_fy={str(k): sorted(v) for k, v in sorted(defl_conflict.items())},
        fy_distinct_entities={str(k): len(v) for k, v in sorted(fy_entities.items())},
        fy_distinct_trbf={str(k): len(v) for k, v in sorted(fy_trbf.items())},
        entities_all_years=len(set().union(*fy_entities.values())) if fy_entities else 0,
        award_keys_attributed_fy2000_2021=dict(
            parent_piid=len(k_parent),
            piid=len(k_piid),
            piid_plus_uei=len(k_piid_uei),
            contract_award_unique_key=len(k_award_unique),
            distinct_awardee_uei=len(k_uei),
            distinct_cage=len(k_cage),
        ),
        award_keys_all_rows_fy2000_2021=dict(
            parent_piid=len(k_parent_all),
            piid=len(k_piid_all),
        ),
    )


# ---------------------------------------------------------------------------
# 2. CEDAR SUBAWARDS — three totals, each named, none allowed to stand alone
# ---------------------------------------------------------------------------
def scan_sub() -> dict:
    t0 = time.time()
    n_all = n_prim = n_countable = 0
    a_all = a_prim = a_countable = 0.0
    fy_all = collections.Counter()
    fy_prim = collections.Counter()
    fy_countable = collections.Counter()
    fy_rows_countable = collections.Counter()
    by_status = collections.Counter()
    exceeds = collections.Counter()
    with open(SUB, encoding="utf-8", errors="replace", newline="") as fh:
        for d in csv.DictReader(fh):
            a = _f(d.get("subaward_amount"))
            st = (d.get("duplicate_status") or "").strip() or "(blank)"
            ex = (d.get("subaward_exceeds_prime_flag") or "").strip()
            by_status[st] += 1
            exceeds[ex or "(blank)"] += 1
            try:
                y = int(float(d.get("fiscal_year") or 0))
            except Exception:
                y = 0
            n_all += 1
            a_all += a
            fy_all[y] += a
            if st != "primary":
                continue
            n_prim += 1
            a_prim += a
            fy_prim[y] += a
            if ex.lower() in {"yes", "true", "1", "y"}:
                continue
            n_countable += 1
            a_countable += a
            fy_countable[y] += a
            fy_rows_countable[y] += 1
    removed_repeats = a_all - a_prim
    return dict(
        source=stamp(SUB),
        elapsed_s=round(time.time() - t0, 1),
        rows_all=n_all,
        rows_primary=n_prim,
        rows_countable=n_countable,
        rows_by_duplicate_status=dict(by_status),
        rows_by_exceeds_prime_flag=dict(exceeds),
        usd_all_rows=round(a_all, 2),
        usd_primary=round(a_prim, 2),
        usd_countable=round(a_countable, 2),
        repeat_filings_removed_usd=round(removed_repeats, 2),
        # STATE THE DENOMINATOR. Both, every time.
        repeat_removal_pct_of_correct=round(100.0 * removed_repeats / a_prim, 1) if a_prim else None,
        repeat_removal_pct_of_inflated=round(100.0 * removed_repeats / a_all, 1) if a_all else None,
        money_rule_removal_usd=round(a_all - a_countable, 2),
        money_rule_removal_pct_of_correct=round(100.0 * (a_all - a_countable) / a_countable, 1) if a_countable else None,
        money_rule_removal_pct_of_inflated=round(100.0 * (a_all - a_countable) / a_all, 1) if a_all else None,
        fy_all={str(k): round(v, 2) for k, v in sorted(fy_all.items())},
        fy_primary={str(k): round(v, 2) for k, v in sorted(fy_prim.items())},
        fy_countable={str(k): round(v, 2) for k, v in sorted(fy_countable.items())},
        fy_rows_countable={str(k): v for k, v in sorted(fy_rows_countable.items())},
    )


# ---------------------------------------------------------------------------
# 3. CICD's PUBLISHED graphed series, read from the staging file 567 wrote
# ---------------------------------------------------------------------------
def read_cicd_series() -> dict:
    if not os.path.exists(CICD_SERIES):
        return {"present": False, "reason": "staged series absent — run code/567 first"}
    ser = {}
    with open(CICD_SERIES, encoding="utf-8", newline="") as fh:
        for d in csv.DictReader(fh):
            ser[int(d["year"])] = {
                "total": _f(d["total_prime_2021usd"]),
                "anc": _f(d["anc_prime_2021usd"]),
                "nho": _f(d["nho_prime_2021usd"]),
                "tribes": _f(d["tribes_prime_2021usd"]),
                "share_all_federal_pct": _f(d["share_of_all_federal_contract_dollars_pct"]),
            }
    total = sum(v["total"] for v in ser.values())
    stated = PUBLISHED["prime_series_1981_2021_2021usd"]["value"]
    err = abs(total - stated) / stated
    return {
        "present": True,
        "source": stamp(CICD_SERIES),
        "years": len(ser),
        "series": ser,
        "series_sum_1981_2021": round(total, 2),
        "article_stated_prime_total": stated,
        "relative_error": round(err, 6),
        "reproduces_its_own_headline": err <= 0.005,
    }


def read_nest() -> dict:
    if not os.path.exists(NEST):
        return {"present": False}
    n = absent = present_fc = 0
    by_class = collections.Counter()
    with open(NEST, encoding="utf-8", errors="replace", newline="") as fh:
        for d in csv.DictReader(fh):
            n += 1
            by_class[(d.get("owner_hub_entity_class") or "").strip() or "(blank)"] += 1
            v = (d.get("in_federal_contracting") or "").strip().lower()
            if v in {"1", "true", "yes", "y"}:
                present_fc += 1
            else:
                absent += 1
    return {
        "present": True,
        "source": stamp(NEST),
        "rows": n,
        "in_federal_contracting": present_fc,
        "absent_from_federal_contracting": absent,
        "absent_pct": round(100.0 * absent / n, 1) if n else None,
        "by_owner_hub_entity_class": dict(by_class.most_common()),
    }


def read_prior_byyear() -> dict:
    """The 2026-09-01 20:15 vintage of this same comparison — the BEFORE side of
    the movement report. It is a prior MEASUREMENT of Cedar, not a Cedar fact."""
    if not os.path.exists(PRIOR_BYYEAR):
        return {"present": False}
    out = {}
    with open(PRIOR_BYYEAR, encoding="utf-8", newline="") as fh:
        for d in csv.DictReader(fh):
            if d["cedar_attributed_prime_2021usd"]:
                out[int(d["year"])] = _f(d["cedar_attributed_prime_2021usd"])
    return {"present": True, "source": stamp(PRIOR_BYYEAR), "by_year": out}


# ---------------------------------------------------------------------------
# 4. THE COMPARISON
# ---------------------------------------------------------------------------
def compare(P, S, C, prior) -> dict:
    if not C.get("present"):
        return {"ran": False, "reason": C.get("reason", "CICD series unavailable")}

    defl = P["deflator_factor_2025_by_fy"]
    f21 = defl.get("2021")
    if not f21:
        return {"ran": False, "reason": "no FY2021 deflator_factor_2025 on prime_contracts.csv"}

    rows = []
    overlap = 0
    for y in sorted(C["series"]):
        c = C["series"][y]["total"]
        cy = P["by_fy"].get(str(y))
        if cy is None:
            rows.append(dict(year=y, cicd_2021usd=round(c, 2), cedar_2021usd=None,
                             delta_usd=None, delta_pct=None, cedar_att_rows=0,
                             prior_cedar_2021usd=None, movement=None,
                             note="Cedar holds no rows for this year"))
            continue
        cedar = cy["att_real2025"] / f21
        prev = prior.get("by_year", {}).get(y)
        mv = None
        if prev is not None and c:
            was = abs(prev - c)
            now = abs(cedar - c)
            mv = "TOWARD" if now < was else ("AWAY" if now > was else "UNCHANGED")
        overlap += 1
        rows.append(dict(
            year=y,
            cicd_2021usd=round(c, 2),
            cedar_2021usd=round(cedar, 2),
            delta_usd=round(cedar - c, 2),
            delta_pct=round(100.0 * (cedar - c) / c, 2) if c else None,
            cedar_att_rows=cy["att_rows"],
            prior_cedar_2021usd=round(prev, 2) if prev is not None else None,
            prior_delta_usd=round(prev - c, 2) if prev is not None else None,
            movement=mv,
            note="CICD year is BGOV contract year; Cedar is federal fiscal year",
        ))

    def rng(lo, hi, key):
        return sum(r[key] for r in rows if lo <= r["year"] <= hi and r[key] is not None)

    cicd_0021 = rng(OVERLAP_LO, OVERLAP_HI, "cicd_2021usd")
    cedar_0021 = rng(OVERLAP_LO, OVERLAP_HI, "cedar_2021usd")
    prior_0021 = sum(v for y, v in prior.get("by_year", {}).items()
                     if OVERLAP_LO <= y <= OVERLAP_HI)
    cicd_8199 = rng(1981, 1999, "cicd_2021usd")

    toward = sum(1 for r in rows if r["movement"] == "TOWARD")
    away = sum(1 for r in rows if r["movement"] == "AWAY")

    return {
        "ran": True,
        "unit": "2021 dollars on BOTH sides",
        "deflator": ("Cedar deflated with prime_contracts.total_obligations_real2025 "
                     f"divided by the table's own deflator_factor_2025 for FY2021 = {f21}. "
                     "CICD does not state its price index; its caption says only 'FRED'. "
                     "The residual carries an UNQUANTIFIED index difference."),
        "cedar_deflator_factor_2021": f21,
        "overlap_years": overlap,
        "by_year": rows,
        "window_2000_2021": {
            "cicd_2021usd": round(cicd_0021, 2),
            "cedar_2021usd": round(cedar_0021, 2),
            "delta_usd": round(cedar_0021 - cicd_0021, 2),
            "delta_pct": round(100.0 * (cedar_0021 - cicd_0021) / cicd_0021, 2),
            "prior_cedar_2021usd": round(prior_0021, 2) if prior_0021 else None,
            "prior_delta_pct": round(100.0 * (prior_0021 - cicd_0021) / cicd_0021, 2) if prior_0021 else None,
            "direction_since_prior": (
                None if not prior_0021 else
                ("TOWARD" if abs(cedar_0021 - cicd_0021) < abs(prior_0021 - cicd_0021)
                 else "AWAY" if abs(cedar_0021 - cicd_0021) > abs(prior_0021 - cicd_0021)
                 else "UNCHANGED")),
        },
        "cicd_only_1981_1999_2021usd": round(cicd_8199, 2),
        "cicd_only_1981_1999_share_of_41yr_pct": round(100.0 * cicd_8199 / C["series_sum_1981_2021"], 3),
        "years_moved_toward_cicd": toward,
        "years_moved_away_from_cicd": away,
    }


def combined_comparison(P, S, C, cmp_) -> dict:
    """THE PROSE TOTAL. A separate comparison against a separate Cedar quantity.

    CICD combined $202B = $198B prime + ~$4B sub, 1981-2021, 2021 dollars, stated
    ONCE with no annual series behind it. Cedar's equivalent is given under BOTH
    conventions and the two are NEVER collapsed into one number.
    """
    f21 = cmp_.get("cedar_deflator_factor_2021")
    if not f21:
        return {"ran": False, "reason": "no deflator"}
    cedar_prime = cmp_["window_2000_2021"]["cedar_2021usd"]

    # Cedar's subaward layer, deflated the same way. subawards.csv carries its own
    # `subaward_amount_real2025`, but it is BLANK on FY2026 (see contractors.md),
    # so the FY window is stated rather than assumed.
    sub_countable_nominal = sum(v for k, v in S["fy_countable"].items()
                                if k.isdigit() and OVERLAP_LO <= int(k) <= OVERLAP_HI)
    sub_rows = sum(v for k, v in S["fy_rows_countable"].items()
                   if k.isdigit() and OVERLAP_LO <= int(k) <= OVERLAP_HI)
    return {
        "ran": True,
        "cicd_published_combined_2021usd": PUBLISHED["combined_prime_plus_sub_1981_2021_2021usd"]["value"],
        "cicd_published_prime_component_2021usd": PUBLISHED["prime_series_1981_2021_2021usd"]["value"],
        "cicd_implied_subaward_component_2021usd": (
            PUBLISHED["combined_prime_plus_sub_1981_2021_2021usd"]["value"]
            - PUBLISHED["prime_series_1981_2021_2021usd"]["value"]),
        "cicd_window": "1981-2021",
        "cedar_window": f"FY{OVERLAP_LO}-{OVERLAP_HI} (Cedar holds NO pre-FY2000 prime row)",
        "under_cicd_convention_prime_plus_sub_2021usd": round(
            cedar_prime + sub_countable_nominal / f21, 2),
        "under_cedar_convention_prime_only_2021usd": round(cedar_prime, 2),
        "cedar_subaward_slice_2021usd_reported_separately": round(sub_countable_nominal / f21, 2),
        "cedar_subaward_rows_in_window": sub_rows,
        "cedar_rule_being_set_aside_to_compute_the_first_line": (
            "docs/MONEY_TOTALLING_RULES.md: 'a subaward is a slice of a prime award already "
            "counted in prime_contracts.csv'. The combined line is computed ONLY to meet CICD's "
            "published definition and MUST NOT be quoted as a Cedar total."),
        "cedar_subaward_layer_is_not_an_annual_series": (
            "Cedar's subaward coverage is incomplete in the later years and the incompleteness is "
            "not uniform, so no annual subaward series is published here. The owner's own reading "
            "of the CICD article — that subawards are messy year to year, which is why the "
            "combined figure was reported as a single total — applies to Cedar identically."),
    }


def entity_comparison(P, S, N) -> dict:
    return {
        "cicd_entities_linked": PUBLISHED["entities_linked"],
        "cicd_enterprises_linked": PUBLISHED["enterprises_linked"],
        "cicd_need_establishments": PUBLISHED["need_establishments"],
        "cedar_entities_carrying_prime_dollars_any_year": P["entities_all_years"],
        "cedar_entities_fy2021": P["fy_distinct_entities"].get("2021"),
        "cedar_federally_recognized_tribes_fy2021": P["fy_distinct_trbf"].get("2021"),
        "cedar_nest_enterprises": N.get("rows"),
        "cedar_nest_absent_from_federal_contracting": N.get("absent_from_federal_contracting"),
        "cedar_nest_absent_pct": N.get("absent_pct"),
        "what_the_two_sides_count": (
            "CICD's 391 is entities it linked to a CONTRACT and its 2,623 is the awardee "
            "ENTERPRISES under them, both over 1981-2021. Cedar's entity count is hubs carrying "
            "prime dollars in prime_contracts.tribe_id; Cedar's nest_enterprises.csv is an "
            "OWNERSHIP register that deliberately includes enterprises with NO federal "
            "contracting at all. The two enterprise counts are therefore NOT the same object and "
            "the arithmetic gap between them is a scope difference, not a coverage finding. "
            "CICD's NEED (5,559 establishments / 344 tribes) is a THIRD object again — "
            "establishments, lower 48, ANCs and NHOs excluded."),
    }


# ---------------------------------------------------------------------------
def measure() -> dict:
    os.makedirs(OUTDIR, exist_ok=True)
    print("[1128] scanning prime_contracts.csv ...", flush=True)
    P = scan_prime()
    print(f"       {P['rows']:,} rows in {P['elapsed_s']}s", flush=True)
    print("[1128] scanning subawards.csv ...", flush=True)
    S = scan_sub()
    print(f"       {S['rows_all']:,} rows; all {B(S['usd_all_rows'])} / "
          f"primary {B(S['usd_primary'])} / countable {B(S['usd_countable'])}", flush=True)
    C = read_cicd_series()
    N = read_nest()
    prior = read_prior_byyear()
    cmp_ = compare(P, S, C, prior)
    payload = {
        "script": "code/1128_cicd_benchmark_refresh_2026_09_02.py",
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "read_only": True,
        "never_merge": ("The CICD side is a PUBLISHED figure staged for comparison. It is an "
                        "external check and stays one. It is never merged as a Cedar measurement."),
        "published_figures": PUBLISHED,
        "cedar_prime": {k: v for k, v in P.items() if k != "by_fy"},
        "cedar_prime_by_fy": P["by_fy"],
        "cedar_subawards": S,
        "cicd_published_series": {k: v for k, v in C.items() if k != "series"},
        "prior_vintage": {"present": prior.get("present"), "source": prior.get("source")},
        "comparison_A_graphed_prime_series": cmp_,
        "comparison_B_prose_combined_total": combined_comparison(P, S, C, cmp_),
        "comparison_C_entity_and_enterprise_counts": entity_comparison(P, S, N),
        "cedar_nest": N,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    if cmp_.get("ran"):
        with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
            cols = []
            for r in cmp_["by_year"]:
                for k in r:
                    if k not in cols:
                        cols.append(k)
            w = csv.DictWriter(fh, fieldnames=cols, restval="")
            w.writeheader()
            for r in cmp_["by_year"]:
                w.writerow(r)
    print(f"[1128] wrote {OUT}")
    print(f"[1128] wrote {OUT_CSV}")
    return payload


# ---------------------------------------------------------------------------
# VERIFY. Exits 1 on breach. An empty join must NEVER read as agreement.
# ---------------------------------------------------------------------------
def verify(payload=None) -> int:
    if payload is None:
        if not os.path.exists(OUT):
            print("V0 FAIL  no measurement on disk — run `measure` first. "
                  "UNMEASURED, not clean.")
            return 1
        payload = json.load(open(OUT, encoding="utf-8"))

    fails, checks = [], []

    def chk(cid, ok, msg):
        checks.append((cid, "PASS" if ok else "FAIL", msg))
        if not ok:
            fails.append(f"{cid} {msg}")

    C = payload.get("cicd_published_series", {})
    A = payload.get("comparison_A_graphed_prime_series", {})
    B_ = payload.get("comparison_B_prose_combined_total", {})
    S = payload.get("cedar_subawards", {})

    # V1 — the external side must reproduce its OWN published headline, or it is
    #      not a benchmark, it is an extraction artefact.
    chk("V1", bool(C.get("present")) and bool(C.get("reproduces_its_own_headline")),
        f"CICD graphed series reproduces its own $198B headline "
        f"(sum {C.get('series_sum_1981_2021')}, rel err {C.get('relative_error')})")

    # V2 — THE COMPARISON MUST HAVE ACTUALLY RUN. An empty join is UNMEASURED.
    ran = bool(A.get("ran"))
    n = A.get("overlap_years", 0)
    chk("V2a", ran, f"comparison ran (reason if not: {A.get('reason')})")
    chk("V2b", n >= MIN_OVERLAP_YEARS,
        f"joined years {n} >= {MIN_OVERLAP_YEARS} — fewer means the join did not happen")
    both = [r for r in A.get("by_year", [])
            if r.get("cedar_2021usd") is not None and r.get("cicd_2021usd")]
    chk("V2c", len(both) >= MIN_OVERLAP_YEARS,
        f"{len(both)} years carry BOTH a Cedar and a CICD value")

    # V3 — units. Both sides must be in 2021 dollars and the deflator named.
    chk("V3a", A.get("unit") == "2021 dollars on BOTH sides", "unit declared on both sides")
    chk("V3b", bool(A.get("cedar_deflator_factor_2021")),
        f"deflator named: {A.get('cedar_deflator_factor_2021')}")

    # V4 — the subaward denominators must both be stated, and must be ORDERED.
    #      all >= primary >= countable. A rule that does not reduce is not applied.
    o = (S.get("usd_all_rows"), S.get("usd_primary"), S.get("usd_countable"))
    chk("V4a", all(v is not None for v in o) and o[0] >= o[1] >= o[2],
        f"subaward totals ordered all {B(o[0])} >= primary {B(o[1])} >= countable {B(o[2])}")
    chk("V4b", S.get("money_rule_removal_pct_of_correct") is not None
        and S.get("money_rule_removal_pct_of_inflated") is not None,
        "both subaward denominators stated (share of correct AND share of inflated)")

    # V5 — the two CICD quantities must be kept apart. The prose combined total
    #      may never be the yardstick for the annual prime series.
    chk("V5a", bool(B_.get("ran")), "prose-combined comparison is its own comparison")
    chk("V5b",
        B_.get("under_cicd_convention_prime_plus_sub_2021usd") is not None
        and B_.get("under_cedar_convention_prime_only_2021usd") is not None
        and B_["under_cicd_convention_prime_plus_sub_2021usd"]
        != B_["under_cedar_convention_prime_only_2021usd"],
        "Cedar's equivalent is given under BOTH conventions and they differ")

    # V6 — the benchmark is never a Cedar measurement.
    chk("V6", "never merged" in (payload.get("never_merge") or ""),
        "the never-merge declaration is on the artefact")

    for cid, st, msg in checks:
        print(f"  {cid:<5} {st}  {msg}")
    if fails:
        print(f"\nVERIFY FAILED — {len(fails)} breach(es)")
        for x in fails:
            print("  -", x)
        return 1
    print(f"\nVERIFY OK — {len(checks)} checks, comparison confirmed to have run on "
          f"{n} joined years")
    return 0


def selftest() -> int:
    """Prove verify FIRES. A check that has never failed on purpose is not known
    to work (AGENT_FIELD_GUIDE rule 1)."""
    if not os.path.exists(OUT):
        print("selftest needs a measurement on disk — run `measure` first")
        return 1
    base = json.load(open(OUT, encoding="utf-8"))
    print("-- baseline, unmodified: expect exit 0")
    if verify(json.loads(json.dumps(base))) != 0:
        print("SELFTEST FAIL: baseline does not pass, so a firing check proves nothing")
        return 1

    violations = [
        ("V2 empty join", lambda p: (p["comparison_A_graphed_prime_series"].update(
            {"by_year": [], "overlap_years": 0}), p)[1]),
        ("V2 comparison did not run", lambda p: (p.__setitem__(
            "comparison_A_graphed_prime_series", {"ran": False, "reason": "synthetic"}), p)[1]),
        ("V1 external side does not reproduce its own headline",
         lambda p: (p["cicd_published_series"].update(
             {"reproduces_its_own_headline": False}), p)[1]),
        ("V4 subaward money rule does not reduce",
         lambda p: (p["cedar_subawards"].update({"usd_countable": 9e99}), p)[1]),
        ("V5 the two conventions collapsed into one number",
         lambda p: (p["comparison_B_prose_combined_total"].update(
             {"under_cicd_convention_prime_plus_sub_2021usd":
              p["comparison_B_prose_combined_total"]["under_cedar_convention_prime_only_2021usd"]}), p)[1]),
    ]
    bad = 0
    for name, mut in violations:
        p = mut(json.loads(json.dumps(base)))
        print(f"\n-- synthetic violation: {name} (expect exit 1)")
        rc = verify(p)
        if rc != 1:
            print(f"SELFTEST FAIL: '{name}' did not fire")
            bad += 1
    print("\n-- baseline again, unmodified: expect exit 0")
    if verify(json.loads(json.dumps(base))) != 0:
        bad += 1
    if bad:
        print(f"\nSELFTEST FAILED — {bad} detector(s) did not fire")
        return 1
    print("\nSELFTEST OK — every detector fires on its own violation and the "
          "baseline still passes")
    return 0


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "measure"
    if cmd == "measure":
        measure()
        return 0
    if cmd == "verify":
        return verify()
    if cmd == "selftest":
        return selftest()
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
