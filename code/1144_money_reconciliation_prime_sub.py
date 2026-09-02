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

import duckdb

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
    con = duckdb.connect()
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
               count(*) FILTER (WHERE s.sub_amt > p.prime_amt),
               sum(s.sub_amt - p.prime_amt) FILTER (WHERE s.sub_amt > p.prime_amt)
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
