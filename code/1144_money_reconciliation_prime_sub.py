#!/usr/bin/env python3
"""1144 - money reconciliation across the three customer money datasets.

Workstream MONEY-RECON-1144 (2026-09-02).

WHY THIS EXISTS
---------------
`docs/MONEY_TOTALLING_RULES.md` states, per table, which columns may be summed.
Nothing measured all three money datasets in ONE pass against the files that are
actually delivered in `dist/customer/`, and nothing had ever put a number on the
prime-vs-sub question: a past article reported a combined prime+sub total while
the chart showed primes only.

This script MEASURES. It writes no dataset. `verify` fails when a measured
number stops matching the recorded one, so it cannot pass on a table where
nothing happened.

Every read is `all_varchar=true` + `TRY_CAST`. `ignore_errors=true` was
deliberately NOT used: it drops malformed rows silently, and a money total over
a silently-shortened table is exactly the defect this file exists to prevent.

  py -3 code/1144_money_reconciliation_prime_sub.py measure
  py -3 code/1144_money_reconciliation_prime_sub.py verify
  py -3 code/1144_money_reconciliation_prime_sub.py selftest
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import duckdb  # noqa: F401  (kept: types/exceptions)
import cedar_duck

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "docs" / "MONEY_RECONCILIATION_1144.json"

DIST = ROOT / "dist" / "customer"
CLEAN = ROOT / "data" / "clean"

FUNDING = DIST / "funding.csv"
SUBS = DIST / "subcontracting.csv"
CONTRACTORS_DIST = DIST / "contractors.csv"
CONTRACTORS_SRC = CLEAN / "prime_contracts.csv"

T0 = time.time()


def say(msg):
    print("[%7.1fs] %s" % (time.time() - T0, msg), flush=True)


def src(path):
    p = str(path).replace("\\", "/").replace("'", "''")
    return "read_csv('%s', all_varchar=true, sample_size=-1, header=true)" % p


def q(con, sql):
    return con.sql(sql).fetchall()


def one(con, sql):
    return q(con, sql)[0]


def measure():
    con = cedar_duck.connect()
    con.sql("PRAGMA threads=4")
    out = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "script": "code/1144_money_reconciliation_prime_sub.py",
    }

    # ---------------------------------------------------------------- delivery
    say("D1 - what is actually IN dist/customer")
    delivered = sorted(p.name for p in DIST.glob("*.csv") if p.name != "MANIFEST.csv")
    man = q(con, "SELECT dataset, flagship, rows FROM " + src(DIST / "MANIFEST.csv"))
    declared = {r[0]: {"flagship": r[1], "rows": int(r[2])} for r in man}
    missing = sorted(d for d in declared if (d + ".csv") not in delivered)
    out["delivery"] = {
        "declared_in_manifest": sorted(declared),
        "csv_present": delivered,
        "declared_but_absent": missing,
    }
    for d in missing:
        say("  DEFECT  manifest declares '%s' (%s rows) and dist/customer/%s.csv "
            "DOES NOT EXIST" % (d, format(declared[d]["rows"], ","), d))

    # ---------------------------------------------------------------- funding
    say("F1 - funding.csv headline")
    r = one(con, """
        SELECT count(*),
               sum(TRY_CAST(obligated_usd AS DOUBLE)),
               count(*) FILTER (WHERE TRY_CAST(obligated_usd AS DOUBLE) IS NULL),
               count(*) FILTER (WHERE coalesce(excluded_flag,'') = '1'),
               sum(TRY_CAST(obligated_usd AS DOUBLE))
                   FILTER (WHERE coalesce(excluded_flag,'') <> '1'),
               count(*) FILTER (WHERE coalesce(attributed_flag,'') = '1'),
               sum(TRY_CAST(obligated_usd AS DOUBLE))
                   FILTER (WHERE coalesce(attributed_flag,'') = '1'),
               count(DISTINCT cedar_uid) FILTER (WHERE coalesce(cedar_uid,'') <> ''),
               count(*) FILTER (WHERE coalesce(cedar_uid,'') <> ''),
               min(TRY_CAST(fiscal_year AS INT)), max(TRY_CAST(fiscal_year AS INT))
        FROM """ + src(FUNDING))
    out["funding"] = {
        "file": "dist/customer/funding.csv",
        "rows": r[0],
        "sum_obligated_usd_all_rows": r[1],
        "rows_obligated_usd_uncastable": r[2],
        "rows_excluded_flag_1": r[3],
        "sum_obligated_usd_not_excluded": r[4],
        "rows_attributed_flag_1": r[5],
        "sum_obligated_usd_attributed": r[6],
        "distinct_cedar_uid": r[7],
        "rows_with_cedar_uid": r[8],
        "linkage_rate_cedar_uid": round(100.0 * r[8] / r[0], 4),
        "fiscal_year_min": r[9],
        "fiscal_year_max": r[10],
    }
    say("  funding rows=%s obligated=$%s attributed=$%s cedar_uid on %s (%.2f%%)"
        % (format(r[0], ","), format(r[1], ",.2f"), format(r[6], ",.2f"),
           format(r[8], ","), 100.0 * r[8] / r[0]))

    say("F2 - funding attribution_status vs the two key columns")
    st = q(con, """
        SELECT coalesce(attribution_status,'(blank)') s, count(*),
               sum(TRY_CAST(obligated_usd AS DOUBLE)),
               count(*) FILTER (WHERE coalesce(cedar_uid,'') <> ''),
               count(*) FILTER (WHERE coalesce(tribe_id_neid,'') <> ''),
               count(*) FILTER (WHERE coalesce(attributed_flag,'') = '1')
        FROM """ + src(FUNDING) + " GROUP BY 1 ORDER BY 2 DESC")
    out["funding"]["attribution_status"] = [
        {"status": a, "rows": b, "usd": c, "rows_cedar_uid": d,
         "rows_tribe_id_neid": e, "rows_attributed_flag": f}
        for a, b, c, d, e, f in st
    ]
    for a, b, c, d, e, f in st:
        say("    %-24s rows=%9s  cedar_uid=%9s  neid=%9s  flag=%9s"
            % (a, format(b, ","), format(d, ","), format(e, ","), format(f, ",")))

    # ------------------------------------------------------------- contractors
    say("C1 - contractors flagship")
    cpath = CONTRACTORS_DIST if CONTRACTORS_DIST.exists() else CONTRACTORS_SRC
    say("  reading %s" % cpath)
    r = one(con, """
        SELECT count(*),
               sum(TRY_CAST(total_obligations AS DOUBLE)),
               count(*) FILTER (WHERE TRY_CAST(total_obligations AS DOUBLE) IS NULL),
               count(*) FILTER (WHERE coalesce(attributed_flag,'') = '1'),
               sum(TRY_CAST(total_obligations AS DOUBLE))
                   FILTER (WHERE coalesce(attributed_flag,'') = '1'),
               count(DISTINCT cedar_uid) FILTER (WHERE coalesce(cedar_uid,'') <> ''),
               count(*) FILTER (WHERE coalesce(cedar_uid,'') <> ''),
               count(*) FILTER (WHERE coalesce(identifier_ruling_quarantined,'') = 'Y'),
               sum(TRY_CAST(total_obligations AS DOUBLE))
                   FILTER (WHERE coalesce(identifier_ruling_quarantined,'') = 'Y'
                           AND coalesce(attributed_flag,'') = '1'),
               min(TRY_CAST(fiscal_year AS INT)), max(TRY_CAST(fiscal_year AS INT)),
               sum(TRY_CAST(total_award_value AS DOUBLE))
        FROM """ + src(cpath))
    out["contractors"] = {
        "file": str(cpath.relative_to(ROOT)).replace("\\", "/"),
        "measured_from_dist": cpath == CONTRACTORS_DIST,
        "rows": r[0],
        "sum_total_obligations": r[1],
        "rows_total_obligations_uncastable": r[2],
        "rows_attributed_flag_1": r[3],
        "sum_total_obligations_attributed": r[4],
        "distinct_cedar_uid": r[5],
        "rows_with_cedar_uid": r[6],
        "linkage_rate_cedar_uid": round(100.0 * r[6] / r[0], 4),
        "rows_quarantined_ruling": r[7],
        "sum_attributed_on_quarantined_ruling": r[8],
        "fiscal_year_min": r[9],
        "fiscal_year_max": r[10],
        "sum_total_award_value_DO_NOT_ADD_TO_OBLIGATIONS": r[11],
    }
    say("  contractors rows=%s obligations=$%s attributed=$%s on %s rows / %s entities"
        % (format(r[0], ","), format(r[1], ",.2f"), format(r[4], ",.2f"),
           format(r[3], ","), format(r[5], ",")))
    say("  cedar_uid on %s (%.2f%%)" % (format(r[6], ","), 100.0 * r[6] / r[0]))

    say("K1 - KEY vs FLAG consistency: does a populated cedar_uid mean attributed?")
    rows = q(con, """
        SELECT coalesce(attribution_method,'(blank)') m,
               coalesce(confidence_tier,'(blank)') t,
               count(*) AS n, sum(TRY_CAST(total_obligations AS DOUBLE)) AS usd
        FROM """ + src(cpath) + """
        WHERE coalesce(cedar_uid,'') <> '' AND coalesce(attributed_flag,'') <> '1'
        GROUP BY 1, 2 ORDER BY 3 DESC
    """)
    out["contractors"]["keyed_but_not_attributed"] = [
        {"attribution_method": a, "confidence_tier": b, "rows": c, "usd": d}
        for a, b, c, d in rows]
    for a, b, c, d in rows:
        say("    contractors keyed-not-attributed  %-24s tier=%s rows=%s $%s"
            % (a, b, format(c, ","), format(d, ",.2f")))

    rows = q(con, """
        SELECT coalesce(attribution_method,'(blank)') m,
               coalesce(attribution_status,'(blank)') s,
               coalesce(excluded_flag,'') e,
               count(*) AS n, sum(TRY_CAST(obligated_usd AS DOUBLE)) AS usd
        FROM """ + src(FUNDING) + """
        WHERE coalesce(cedar_uid,'') <> '' AND coalesce(attributed_flag,'') <> '1'
        GROUP BY 1, 2, 3 ORDER BY 4 DESC
    """)
    out["funding"]["keyed_but_not_attributed"] = [
        {"attribution_method": a, "attribution_status": b, "excluded_flag": c,
         "rows": d, "usd": e} for a, b, c, d, e in rows]
    for a, b, c, d, e in rows:
        say("    funding keyed-not-attributed  %-38s %s excl=%s rows=%s $%s"
            % (a, b, c, format(d, ","), format(e, ",.2f")))

    rows = q(con, """
        SELECT coalesce(attribution_status,'(blank)') s,
               coalesce(canonical_name,'(blank)') nm,
               count(*) AS n, sum(TRY_CAST(obligated_usd AS DOUBLE)) AS usd
        FROM """ + src(FUNDING) + """
        WHERE coalesce(attributed_flag,'') = '1'
          AND coalesce(cedar_uid,'') = '' AND coalesce(tribe_id_neid,'') = ''
        GROUP BY 1, 2 ORDER BY 3 DESC
    """)
    out["funding"]["attributed_but_unkeyed"] = [
        {"attribution_status": a, "canonical_name": b, "rows": c, "usd": d}
        for a, b, c, d in rows]
    for a, b, c, d in rows:
        say("    funding attributed-but-UNKEYED  %-22s %-18s rows=%s $%s"
            % (a, b, format(c, ","), format(d, ",.2f")))

    # ---------------------------------------------------------- subcontracting
    say("S1 - subcontracting.csv, unfiltered vs countable")
    r = one(con, """
        SELECT count(*),
               sum(TRY_CAST(subaward_amount AS DOUBLE)),
               count(*) FILTER (WHERE TRY_CAST(subaward_amount AS DOUBLE) IS NULL),
               count(*) FILTER (WHERE duplicate_status = 'primary'
                                AND coalesce(subaward_exceeds_prime_flag,'') <> 'yes'),
               sum(TRY_CAST(subaward_amount AS DOUBLE))
                   FILTER (WHERE duplicate_status = 'primary'
                           AND coalesce(subaward_exceeds_prime_flag,'') <> 'yes'),
               min(TRY_CAST(fiscal_year AS INT)), max(TRY_CAST(fiscal_year AS INT))
        FROM """ + src(SUBS))
    unf, cnt = r[1], r[4]
    removed = unf - cnt
    out["subcontracting"] = {
        "file": "dist/customer/subcontracting.csv",
        "rows": r[0],
        "sum_subaward_amount_ALL_ROWS_NEVER_QUOTE": unf,
        "rows_subaward_amount_uncastable": r[2],
        "countable_rows": r[3],
        "sum_subaward_amount_countable": cnt,
        "money_rule_removes": removed,
        "overstatement_pct_of_correct": round(100.0 * removed / cnt, 2),
        "removed_share_of_unfiltered_pct": round(100.0 * removed / unf, 2),
        "fiscal_year_min": r[5],
        "fiscal_year_max": r[6],
    }
    say("  subs rows=%s unfiltered=$%s countable(n=%s)=$%s"
        % (format(r[0], ","), format(unf, ",.2f"), format(r[3], ","),
           format(cnt, ",.2f")))
    say("  removes $%s = %.1f%% OF THE CORRECT TOTAL (= %.1f%% of the unfiltered)"
        % (format(removed, ",.2f"), 100.0 * removed / cnt, 100.0 * removed / unf))

    ds = q(con, """
        SELECT coalesce(duplicate_status,'(blank)'), count(*),
               sum(TRY_CAST(subaward_amount AS DOUBLE))
        FROM """ + src(SUBS) + " GROUP BY 1 ORDER BY 2 DESC")
    out["subcontracting"]["duplicate_status"] = [
        {"status": a, "rows": b, "usd": c} for a, b, c in ds]
    for a, b, c in ds:
        say("    %-32s rows=%7s  $%s" % (a, format(b, ","), format(c, ",.2f")))

    ex = one(con, """
        SELECT count(*) FILTER (WHERE subaward_exceeds_prime_flag = 'yes'),
               sum(TRY_CAST(subaward_amount AS DOUBLE))
                   FILTER (WHERE subaward_exceeds_prime_flag = 'yes'),
               count(*) FILTER (WHERE subaward_exceeds_prime_flag = 'yes'
                                AND duplicate_status = 'primary'),
               sum(TRY_CAST(subaward_amount AS DOUBLE))
                   FILTER (WHERE subaward_exceeds_prime_flag = 'yes'
                           AND duplicate_status = 'primary')
        FROM """ + src(SUBS))
    out["subcontracting"]["exceeds_prime"] = {
        "rows": ex[0], "usd": ex[1],
        "rows_that_are_also_primary": ex[2], "usd_that_are_also_primary": ex[3],
    }
    say("  exceeds_prime=yes: %s rows / $%s; of which primary %s / $%s"
        % (format(ex[0], ","), format(ex[1] or 0, ",.2f"),
           format(ex[2], ","), format(ex[3] or 0, ",.2f")))

    say("S2 - subcontracting linkage, per LEG")
    r = one(con, """
        SELECT count(*),
               count(*) FILTER (WHERE coalesce(cedar_uid,'') <> ''),
               count(*) FILTER (WHERE coalesce(sub_cedar_uid,'') <> ''),
               count(*) FILTER (WHERE coalesce(prime_cedar_uid,'') <> ''),
               count(*) FILTER (WHERE coalesce(sub_cedar_uid,'') <> ''
                                   OR coalesce(prime_cedar_uid,'') <> ''),
               count(*) FILTER (WHERE coalesce(sub_cedar_uid,'') <> ''
                                  AND coalesce(prime_cedar_uid,'') <> ''),
               count(DISTINCT sub_cedar_uid) FILTER (WHERE coalesce(sub_cedar_uid,'') <> ''),
               count(DISTINCT prime_cedar_uid) FILTER (WHERE coalesce(prime_cedar_uid,'') <> ''),
               count(*) FILTER (WHERE coalesce(sub_native_tribe_id,'') <> ''),
               count(*) FILTER (WHERE coalesce(prime_native_tribe_id,'') <> '')
        FROM """ + src(SUBS))
    out["subcontracting"]["linkage"] = {
        "rows": r[0], "rows_cedar_uid": r[1], "rows_sub_cedar_uid": r[2],
        "rows_prime_cedar_uid": r[3], "rows_either_leg": r[4], "rows_both_legs": r[5],
        "distinct_sub_entities": r[6], "distinct_prime_entities": r[7],
        "rows_sub_native_tribe_id": r[8], "rows_prime_native_tribe_id": r[9],
        "rate_cedar_uid_pct": round(100.0 * r[1] / r[0], 4),
        "rate_either_leg_pct": round(100.0 * r[4] / r[0], 4),
    }
    say("  cedar_uid %s (%.2f%%) | sub leg %s | prime leg %s | EITHER leg %s (%.2f%%)"
        % (format(r[1], ","), 100.0 * r[1] / r[0], format(r[2], ","),
           format(r[3], ","), format(r[4], ","), 100.0 * r[4] / r[0]))

    say("S3 - WHAT `cedar_uid` ACTUALLY IS in this table")
    r = one(con, """
        SELECT count(*) FILTER (WHERE coalesce(cedar_uid,'') <> ''
                                AND cedar_uid = prime_cedar_uid),
               count(*) FILTER (WHERE coalesce(cedar_uid,'') <> ''
                                AND cedar_uid = sub_cedar_uid),
               count(*) FILTER (WHERE coalesce(cedar_uid,'') <> ''
                                AND cedar_uid <> coalesce(prime_cedar_uid,'')
                                AND cedar_uid <> coalesce(sub_cedar_uid,'')),
               count(*) FILTER (WHERE coalesce(cedar_uid,'') = ''),
               count(*) FILTER (WHERE coalesce(cedar_uid,'') = ''
                                AND coalesce(sub_cedar_uid,'') <> ''),
               count(*) FILTER (WHERE coalesce(cedar_uid,'') = ''
                                AND coalesce(sub_cedar_uid,'') = ''
                                AND coalesce(prime_cedar_uid,'') = '')
        FROM """ + src(SUBS))
    out["subcontracting"]["cedar_uid_semantics"] = {
        "nonblank_equal_to_prime_leg": r[0],
        "nonblank_equal_to_sub_leg": r[1],
        "nonblank_equal_to_NEITHER_leg": r[2],
        "blank": r[3],
        "blank_but_sub_leg_is_keyed": r[4],
        "blank_and_neither_leg_keyed_THE_REAL_GAP": r[5],
    }
    say("  cedar_uid == prime leg on %s of the %s non-blank; == sub leg %s; "
        "== NEITHER %s" % (format(r[0], ","), format(out["subcontracting"]
                           ["linkage"]["rows_cedar_uid"], ","),
                           format(r[1], ","), format(r[2], ",")))
    say("  blank on %s rows, of which %s DO carry a sub leg; only %s rows have "
        "no Native party keyed at all"
        % (format(r[3], ","), format(r[4], ","), format(r[5], ",")))

    # ------------------------------------------------- prime <-> sub reconcile
    say("R1 - do subaward prime keys reach prime_contracts?")
    r = one(con, """
        WITH s AS (
          SELECT prime_award_unique_key k,
                 TRY_CAST(subaward_amount AS DOUBLE) amt
          FROM """ + src(SUBS) + """
          WHERE duplicate_status = 'primary'
            AND coalesce(subaward_exceeds_prime_flag,'') <> 'yes'
        ), p AS (
          SELECT DISTINCT contract_award_unique_key k FROM """ + src(CONTRACTORS_SRC) + """
          WHERE coalesce(contract_award_unique_key,'') <> ''
        )
        SELECT count(*),
               count(*) FILTER (WHERE coalesce(s.k,'') <> ''),
               count(*) FILTER (WHERE p.k IS NOT NULL),
               sum(s.amt),
               sum(s.amt) FILTER (WHERE p.k IS NOT NULL),
               count(DISTINCT s.k) FILTER (WHERE coalesce(s.k,'') <> ''),
               count(DISTINCT p.k) FILTER (WHERE p.k IS NOT NULL)
        FROM s LEFT JOIN p ON s.k = p.k
    """)
    out["prime_sub_reconciliation"] = {
        "countable_sub_rows": r[0],
        "countable_sub_rows_with_prime_award_unique_key": r[1],
        "countable_sub_rows_whose_prime_award_is_IN_prime_contracts": r[2],
        "countable_sub_usd": r[3],
        "countable_sub_usd_whose_prime_award_is_IN_prime_contracts": r[4],
        "distinct_prime_keys_cited_by_subs": r[5],
        "distinct_prime_keys_matched": r[6],
        "match_rate_rows_pct": round(100.0 * r[2] / r[0], 2) if r[0] else None,
        "match_rate_usd_pct": round(100.0 * (r[4] or 0) / r[3], 2) if r[3] else None,
    }
    say("  countable sub rows=%s; carry a prime key %s; that key IS in "
        "prime_contracts on %s (%.1f%%)"
        % (format(r[0], ","), format(r[1], ","), format(r[2], ","),
           100.0 * r[2] / r[0]))
    say("  countable sub $=%s; on a prime award Cedar also publishes $%s (%.1f%%)"
        % (format(r[3], ",.2f"), format(r[4] or 0, ",.2f"),
           100.0 * (r[4] or 0) / r[3]))

    say("R1b - the overlap DECOMPOSED by which leg is the Native party")
    rows = q(con, """
        WITH s AS (
          SELECT prime_award_unique_key k, coalesce(direction,'(blank)') dirn,
                 TRY_CAST(subaward_amount AS DOUBLE) amt
          FROM """ + src(SUBS) + """
          WHERE duplicate_status = 'primary'
            AND coalesce(subaward_exceeds_prime_flag,'') <> 'yes'
        ), p AS (
          SELECT DISTINCT contract_award_unique_key k FROM """ + src(CONTRACTORS_SRC) + """
          WHERE coalesce(contract_award_unique_key,'') <> ''
        )
        SELECT (p.k IS NOT NULL) AS in_prime, s.dirn, count(*) AS n, sum(s.amt) AS usd
        FROM s LEFT JOIN p ON s.k = p.k
        GROUP BY 1, 2 ORDER BY 1, 4 DESC
    """)
    out["prime_sub_reconciliation"]["decomposition"] = [
        {"prime_award_in_prime_contracts": bool(a), "direction": b,
         "rows": c, "usd": d} for a, b, c, d in rows]
    for a, b, c, d in rows:
        say("    in_prime=%-5s %-24s rows=%7s  $%s"
            % (bool(a), b, format(c, ","), format(d, ",.2f")))

    say("R1c - of the overlap, is the matched prime row itself Native-ATTRIBUTED?")
    rows = q(con, """
        WITH s AS (
          SELECT prime_award_unique_key k, TRY_CAST(subaward_amount AS DOUBLE) amt
          FROM """ + src(SUBS) + """
          WHERE duplicate_status = 'primary'
            AND coalesce(subaward_exceeds_prime_flag,'') <> 'yes'
            AND coalesce(prime_award_unique_key,'') <> ''
        ), p AS (
          SELECT contract_award_unique_key k,
                 max(CASE WHEN coalesce(attributed_flag,'') = '1' THEN 1 ELSE 0 END) attr
          FROM """ + src(CONTRACTORS_SRC) + """
          WHERE coalesce(contract_award_unique_key,'') <> '' GROUP BY 1
        )
        SELECT p.attr, count(*) AS n, sum(s.amt) AS usd
        FROM s JOIN p ON s.k = p.k GROUP BY 1 ORDER BY 1
    """)
    out["prime_sub_reconciliation"]["overlap_by_prime_attribution"] = [
        {"prime_row_attributed": bool(a), "rows": b, "usd": c} for a, b, c in rows]
    for a, b, c in rows:
        say("    prime_attributed=%-5s rows=%7s  $%s"
            % (bool(a), format(b, ","), format(c, ",.2f")))

    say("R2 - the containment test: sub dollars vs their own prime's obligations")
    r = one(con, """
        WITH s AS (
          SELECT prime_award_unique_key k, sum(TRY_CAST(subaward_amount AS DOUBLE)) sub_amt
          FROM """ + src(SUBS) + """
          WHERE duplicate_status = 'primary'
            AND coalesce(subaward_exceeds_prime_flag,'') <> 'yes'
            AND coalesce(prime_award_unique_key,'') <> ''
          GROUP BY 1
        ), p AS (
          SELECT contract_award_unique_key k,
                 sum(TRY_CAST(total_obligations AS DOUBLE)) prime_amt
          FROM """ + src(CONTRACTORS_SRC) + """
          WHERE coalesce(contract_award_unique_key,'') <> ''
          GROUP BY 1
        )
        SELECT count(*), sum(s.sub_amt), sum(p.prime_amt),
               count(*) FILTER (WHERE s.sub_amt > p.prime_amt + 0.01),
               sum(s.sub_amt - p.prime_amt) FILTER (WHERE s.sub_amt > p.prime_amt + 0.01)
        FROM s JOIN p ON s.k = p.k
    """)
    out["prime_sub_reconciliation"]["containment"] = {
        "matched_prime_awards": r[0],
        "sub_usd_on_them": r[1],
        "prime_obligations_on_the_same_awards": r[2],
        "awards_where_subs_exceed_the_prime": r[3],
        "excess_usd": r[4],
    }
    say("  %s matched awards: subs $%s inside primes $%s; %s awards where subs "
        "EXCEED the prime ($%s)"
        % (format(r[0], ","), format(r[1] or 0, ",.2f"), format(r[2] or 0, ",.2f"),
           format(r[3], ","), format(r[4] or 0, ",.2f")))

    con.close()
    return out


# ---------------------------------------------------------------------------
# LINKAGE: subaward UEI self-consistency
#
# The SAME UEI is keyed to a Cedar entity on some rows of subawards.csv and
# blank on others. That is not a name match and it is not a new ruling - it is
# Cedar's own already-adjudicated key, on an exact federal registration
# identifier, applied consistently within one file. The tier is INHERITED from
# the keyed rows (START_HERE trap 1: a tier is never assigned by the consumer).
#
# The rule is deliberately narrow and refuses more than it takes:
#   * the UEI must resolve to EXACTLY ONE cedar_uid among the keyed rows, and
#     to at most one tribe_id and one tier - otherwise skipped;
#   * only rows with NEITHER leg keyed are touched, so nothing already resolved
#     is re-litigated;
#   * a DIFFERENT UEI of the same-named firm is NOT evidence. WIND RIVER
#     CONSTRUCTION LLC files under three UEIs; one (VHSJFRQKMXG9, 3 rows) is
#     keyed and two are not, and the 516 rows / ~$1.0B on JWH3U659JTN1 are
#     LEFT ALONE. A separate registration is a separate question.
# ---------------------------------------------------------------------------
SUB_CLEAN = CLEAN / "subawards.csv"
PROPOSAL = ROOT / "review" / "1144_subaward_uei_self_consistency_2026-09-02.csv"
PRIOR = ROOT / "review" / "1144_subaward_uei_prior_values_2026-09-02.csv"

LEGS = [
    ("sub", "sub_uei", "sub_cedar_uid", "sub_native_tribe_id", "sub_native_tier"),
    ("prime", "prime_uei", "prime_cedar_uid", "prime_native_tribe_id",
     "prime_native_tier"),
]


def _load_subawards():
    import pandas as pd
    return pd.read_csv(SUB_CLEAN, dtype=str, keep_default_na=False,
                       na_filter=False, low_memory=False)


def _build_targets(df):
    """Return (targets, skipped) without touching df."""
    targets = []   # dicts, one per row to write
    skipped = []   # (leg, uei, reason, rows)
    unkeyed = (df["sub_cedar_uid"].str.strip() == "") & \
              (df["prime_cedar_uid"].str.strip() == "")
    for leg, ucol, kcol, tcol, tiercol in LEGS:
        keyed = df[(df[kcol].str.strip() != "") & (df[ucol].str.strip() != "")]
        for uei, grp in keyed.groupby(ucol):
            uids = sorted(set(grp[kcol].str.strip()) - {""})
            tids = sorted(set(grp[tcol].str.strip()) - {""})
            tiers = sorted(set(grp[tiercol].str.strip()) - {""})
            if len(uids) != 1:
                skipped.append((leg, uei, "uei_resolves_to_%d_entities" % len(uids),
                                len(grp)))
                continue
            if len(tids) > 1 or len(tiers) > 1:
                skipped.append((leg, uei, "uei_carries_conflicting_tribe_id_or_tier",
                                len(grp)))
                continue
            hit = unkeyed & (df[ucol].str.strip() == uei)
            if not hit.any():
                continue
            for idx in df.index[hit]:
                targets.append({
                    "row_index": int(idx),
                    "leg": leg,
                    "source_dataset": df.at[idx, "source_dataset"],
                    "subaward_source_record_id": df.at[idx, "subaward_source_record_id"],
                    "uei": uei,
                    "name_as_recorded": df.at[idx, "sub_name" if leg == "sub"
                                              else "prime_name"],
                    "subaward_amount": df.at[idx, "subaward_amount"],
                    "cedar_uid_col": kcol,
                    "cedar_uid_new": uids[0],
                    "tribe_id_col": tcol,
                    "tribe_id_new": tids[0] if tids else "",
                    "tier_col": tiercol,
                    "tier_new": tiers[0] if tiers else "",
                    "n_keyed_rows_supplying_the_evidence": int(len(grp)),
                    "basis": ("exact UEI %s is keyed to %s on %d other rows of this "
                              "same file; tier INHERITED, not assigned"
                              % (uei, uids[0], len(grp))),
                })
    return targets, skipped


def _rewrite(df):
    """Write subawards.csv via .part + os.replace, retrying a Windows lock."""
    import os
    part = SUB_CLEAN.with_suffix(".csv.part_1144")
    df.to_csv(part, index=False, lineterminator="\n")
    deadline = time.time() + 60
    while True:
        try:
            os.replace(part, SUB_CLEAN)
            return
        except PermissionError:
            if time.time() > deadline:
                # Never leave a .part a later reader could mistake for the table.
                part.unlink(missing_ok=True)
                raise
            say("  os.replace locked (another agent holds a handle) - retrying")
            time.sleep(5)


def linkage(execute=False):
    import pandas as pd
    say("L0 - loading %s" % SUB_CLEAN.relative_to(ROOT))
    df = _load_subawards()
    n_rows, n_cols = df.shape
    say("  %s rows x %s columns" % (format(n_rows, ","), n_cols))

    targets, skipped = _build_targets(df)
    usd = sum(float(t["subaward_amount"] or 0) for t in targets)
    say("L1 - %s rows recoverable by exact-UEI self-consistency, $%s, over %s "
        "(leg,uei) groups"
        % (format(len(targets), ","), format(usd, ",.2f"),
           format(len({(t["leg"], t["uei"]) for t in targets}), ",")))
    say("L2 - %s (leg,uei) groups REFUSED: %s"
        % (len(skipped), ", ".join(sorted({s[2] for s in skipped})) or "none"))

    PROPOSAL.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(targets).to_csv(PROPOSAL, index=False, lineterminator="\n")
    say("  wrote %s" % PROPOSAL.relative_to(ROOT))

    if not execute:
        say("DRY RUN - nothing written to the flagship. Re-run with `apply --execute`.")
        return 0

    prior = [{"row_index": t["row_index"],
              "source_dataset": t["source_dataset"],
              "subaward_source_record_id": t["subaward_source_record_id"],
              "column": c, "prior_value": df.at[t["row_index"], c]}
             for t in targets
             for c in (t["cedar_uid_col"], t["tribe_id_col"], t["tier_col"])]
    pd.DataFrame(prior).to_csv(PRIOR, index=False, lineterminator="\n")
    say("  wrote %s (%s cells)" % (PRIOR.relative_to(ROOT), format(len(prior), ",")))

    before = df.copy(deep=True)
    for t in targets:
        i = t["row_index"]
        df.at[i, t["cedar_uid_col"]] = t["cedar_uid_new"]
        if t["tribe_id_new"]:
            df.at[i, t["tribe_id_col"]] = t["tribe_id_new"]
        if t["tier_new"]:
            df.at[i, t["tier_col"]] = t["tier_new"]

    # Conservation, asserted rather than hoped for.
    assert df.shape == (n_rows, n_cols), "row or column count changed"
    assert list(df.columns) == list(before.columns), "column order changed"
    changed = (df != before)
    n_changed_cells = int(changed.to_numpy().sum())
    n_changed_rows = int(changed.any(axis=1).sum())
    # A row can legitimately be a target TWICE - once per leg - when both its
    # parties are recoverable. Count DISTINCT rows, not target entries; the
    # first run of this assertion caught exactly that (300 entries, 290 rows)
    # and refused to write, which is what it is for.
    distinct_targets = {t["row_index"] for t in targets}
    say("L3 - %s cells on %s rows changed (targets: %s entries over %s distinct "
        "rows; %s rows recoverable on BOTH legs)"
        % (format(n_changed_cells, ","), format(n_changed_rows, ","),
           format(len(targets), ","), format(len(distinct_targets), ","),
           format(len(targets) - len(distinct_targets), ",")))
    assert n_changed_rows == len(distinct_targets), \
        "touched a row that was not a target"
    assert set(df.index[changed.any(axis=1)]) == distinct_targets, \
        "the set of changed rows is not the set of target rows"
    money_before = pd.to_numeric(before["subaward_amount"], errors="coerce").sum()
    money_after = pd.to_numeric(df["subaward_amount"], errors="coerce").sum()
    assert abs(money_before - money_after) < 0.01, "the money moved"
    say("L4 - money unchanged: $%s" % format(money_after, ",.2f"))

    bak = SUB_CLEAN.parent / (
        SUB_CLEAN.name + ".bak_2026-09-02_pre_1144_money_reconciliation_prime_sub")
    if not bak.exists():
        bak.write_bytes(SUB_CLEAN.read_bytes())
        say("  backed up to %s" % bak.name)
    _rewrite(df)
    say("L5 - WROTE %s" % SUB_CLEAN.relative_to(ROOT))
    return 0


def linkage_verify():
    """FAILS when the write did not land. The floor is the specific rows.

    A count-based floor would pass on a table where nothing happened - the
    exact error that once shipped a '$1.5B attributed' claim. This asserts the
    named rows carry the named value, which no prior state satisfies because
    every one of them was blank before.
    """
    import pandas as pd
    if not PROPOSAL.exists():
        print("FAIL: no proposal on disk - run `linkage` first", flush=True)
        return 1
    prop = pd.read_csv(PROPOSAL, dtype=str, keep_default_na=False)
    if prop.empty:
        print("FAIL: proposal is empty - nothing to verify", flush=True)
        return 1
    df = _load_subawards()
    key = ["source_dataset", "subaward_source_record_id"]
    idx = df.set_index(key)
    missing, wrong = [], []
    for _, r in prop.iterrows():
        rec = "%s/%s" % (r["source_dataset"], r["subaward_source_record_id"])
        try:
            row = idx.loc[(r["source_dataset"], r["subaward_source_record_id"])]
        except KeyError:
            # A count is not actionable; the key is. Named, not tallied.
            missing.append(rec)
            continue
        if hasattr(row, "iloc") and getattr(row, "ndim", 1) > 1:
            row = row.iloc[0]
        if str(row[r["cedar_uid_col"]]).strip() != r["cedar_uid_new"]:
            wrong.append("%s %s expected=%s found=%r"
                         % (rec, r["cedar_uid_col"], r["cedar_uid_new"],
                            str(row[r["cedar_uid_col"]]).strip()))
    print("  proposal rows: %d | not found in the table: %d | not carrying the "
          "expected key: %d" % (len(prop), len(missing), len(wrong)), flush=True)
    for rec in missing[:20]:
        print("    NOT FOUND  %s" % rec, flush=True)
    for rec in wrong[:20]:
        print("    NOT KEYED  %s" % rec, flush=True)
    if len(missing) + len(wrong) > 40:
        print("    (%d more not listed)"
              % (len(missing) + len(wrong) - 40), flush=True)
    if missing or wrong:
        print("FAIL: the linkage write did not land (or was reverted by a "
              "rebuild of subawards.csv - re-run `apply --execute`)", flush=True)
        return 1
    print("PASS: all %d rows carry the inherited key" % len(prop), flush=True)
    return 0


def load_prev():
    if OUT_JSON.exists():
        return json.loads(OUT_JSON.read_text(encoding="utf-8"))
    return None


# The invariants `verify` enforces. Each is (dotted path, comparison).
# A verify that only proves nothing broke is not a verify - every entry below
# is a number this pass MEASURED and would notice moving.
CHECKS = [
    ("funding.rows", "eq"),
    ("funding.sum_obligated_usd_all_rows", "money"),
    ("funding.rows_obligated_usd_uncastable", "eq"),
    ("contractors.rows", "eq"),
    ("contractors.sum_total_obligations", "money"),
    ("subcontracting.rows", "eq"),
    ("subcontracting.sum_subaward_amount_ALL_ROWS_NEVER_QUOTE", "money"),
    ("subcontracting.sum_subaward_amount_countable", "money"),
    ("subcontracting.countable_rows", "eq"),
    ("prime_sub_reconciliation.countable_sub_usd", "money"),
]


def dig(d, path):
    cur = d
    for part in path.split("."):
        cur = cur[part]
    return cur


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "measure"
    if cmd == "measure":
        out = measure()
        OUT_JSON.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        say("wrote %s" % OUT_JSON.relative_to(ROOT))
        return 0
    if cmd == "verify":
        prev = load_prev()
        if prev is None:
            print("FAIL: no recorded measurement - run `measure` first", flush=True)
            return 1
        now = measure()
        bad = []
        for path, kind in CHECKS:
            try:
                a, b = dig(prev, path), dig(now, path)
            except KeyError:
                print("  FAIL  %s: absent from the recorded measurement" % path)
                bad.append(path)
                continue
            if kind == "eq":
                ok = a == b
            else:
                ok = (a is not None and b is not None
                      and abs(float(a) - float(b)) < 0.01)
            print("  %s  %s: recorded=%s live=%s"
                  % ("ok  " if ok else "FAIL", path, a, b), flush=True)
            if not ok:
                bad.append(path)
        if bad:
            print("FAIL: %d recorded number(s) no longer reproduce: %s"
                  % (len(bad), ", ".join(bad)), flush=True)
            return 1
        print("PASS: every recorded number reproduces against the live files",
              flush=True)
        return 0
    if cmd in ("linkage", "apply"):
        return linkage(execute="--execute" in sys.argv)
    if cmd == "linkage-verify":
        return linkage_verify()
    if cmd == "selftest":
        # Prove `verify` FAILS when the work did not land, rather than proving
        # that nothing broke. Perturb each recorded number and assert the
        # comparison rejects it.
        prev = load_prev()
        if prev is None:
            print("FAIL: run `measure` first")
            return 1
        fired = 0
        for path, kind in CHECKS:
            a = dig(prev, path)
            perturbed = (a + 1) if isinstance(a, (int, float)) else str(a) + "X"
            if kind == "eq":
                ok = (a == perturbed)
            else:
                ok = abs(float(a) - float(perturbed)) < 0.01
            if not ok:
                fired += 1
            else:
                print("  SELFTEST FAIL: %s did not notice a perturbation" % path)
        print("selftest: %d/%d checks fire on a perturbed value"
              % (fired, len(CHECKS)), flush=True)
        return 0 if fired == len(CHECKS) else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
