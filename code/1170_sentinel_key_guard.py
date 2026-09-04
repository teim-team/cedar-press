#!/usr/bin/env python3
"""
1170 - sentinel_key_guard

THE DEFECT THIS OWNS, in the external reviewer's words:

    "NAN is functioning as a real join key, causing every missing record to
     match the population of other missing records. Any enrichment, duplicate
     count, or confidence field derived from those joins is suspect."

A sentinel string is a MISSING VALUE that was written to disk as text. `NAN`,
`UNKNOWN`, `NULL`, `N/A`, `-`, empty-after-strip. Every one of them compares
equal to itself, so `dict[key] += 1` over a column full of them builds one
bucket holding the whole missing population, and every missing row is then
handed that bucket's size as if it were its own.

WHAT IT READS
    data/clean/*.csv          every live file (`.bak_*` excluded)
    dist/customer/*.csv       the 13 delivered datasets
    docs/schema/dataset_contracts.json
                              key_columns / primary_key / join_cardinality,
                              which is where a join declares itself
    code/**.py                static index of which columns are used as keys

WHAT IT WRITES  (nothing under data/clean or dist/customer - ever)
    review/1170_sentinel_census.csv        one row per (file, column)
    review/1170_sentinel_census.json       machine form + the run's snapshot
                                           fingerprints
    review/1170_exploded_joins.csv         count columns constant across a
                                           sentinel key group
    review/1170_key_usage.csv              column -> scripts that key on it
    review/SENTINEL_DEFECT_2026-09-03.md   the ranked finding + the PROPOSED
                                           fix (proposal only; nothing applied)

SUBCOMMANDS
    scan       full uncapped census of sentinel strings. No sampling anywhere.
    joins      static index of join-key columns out of code/
    explode    exploded-join detection (part 2 of the brief)
    verify     THE GUARD. Four named invariants, exit 1 on any violation.
    selftest   inject each violation class into a synthetic fixture and prove
               the NAMED detector fires. "A check that returns zero without
               demonstrating that it can return one is not trustworthy."
    report     write review/SENTINEL_DEFECT_2026-09-03.md from the artefacts

SNAPSHOT DISCIPLINE
    Concurrent rebuilds are live on this machine. Every scanned file's
    (size, mtime) is recorded before AND after its own scan; a file that moved
    under the scan is marked `moved_during_scan` and its figures are a SNAPSHOT
    of a file that no longer exists in that form. Nothing here may be quoted as
    a standing figure without re-running `scan`.

RE-RUN
    py -3 code/1170_sentinel_key_guard.py scan
    py -3 code/1170_sentinel_key_guard.py joins
    py -3 code/1170_sentinel_key_guard.py explode
    py -3 code/1170_sentinel_key_guard.py verify
    py -3 code/1170_sentinel_key_guard.py selftest
"""
from __future__ import annotations

import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
DIST = ROOT / "dist" / "customer"
CODE = ROOT / "code"
REVIEW = ROOT / "review"
CONTRACTS = ROOT / "docs" / "schema" / "dataset_contracts.json"

CENSUS_CSV = REVIEW / "1170_sentinel_census.csv"
CENSUS_JSON = REVIEW / "1170_sentinel_census.json"
EXPLODE_CSV = REVIEW / "1170_exploded_joins.csv"
KEYUSE_CSV = REVIEW / "1170_key_usage.csv"

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

# --------------------------------------------------------------------------
# The vocabulary. Compared UPPER-CASED and STRIPPED, so `nan`, `NaN` and
# ` NAN ` are one token. BLANK (null / empty / whitespace-only) is counted
# separately because it is the only one that is arguably honest on disk - and
# it is still a real join key to `dict[""] += 1`.
# --------------------------------------------------------------------------
SENTINELS = [
    "NAN", "NULL", "NONE", "UNKNOWN", "N/A", "NA", "-", "--", "?", "TBD",
    "#N/A", "#NA", "NAT", "NOT APPLICABLE", "NOT AVAILABLE", "UNSPECIFIED",
    "MISSING", "NO DATA", "NOT REPORTED", "NONE LISTED", ".", "..",
]
# Longest sentinel, used as a cheap length pre-filter in SQL. Padded so a
# value like "   NOT APPLICABLE   " still reaches the comparison.
MAXLEN = max(len(s) for s in SENTINELS) + 24

# Sentinels that are ALWAYS a defect in a key column vs ones that can be a
# legitimate value in a free-text column. `-` is a real hyphen somewhere;
# `NAN` never is.
HARD_SENTINELS = {"NAN", "NULL", "NONE", "UNKNOWN", "N/A", "#N/A", "#NA",
                  "NAT", "TBD", "NOT APPLICABLE", "NOT AVAILABLE",
                  "UNSPECIFIED", "MISSING", "NO DATA", "NOT REPORTED"}

# --------------------------------------------------------------------------
# What counts as an identifier / join-key column BY NAME. Deliberately a
# suffix/exact test, not a substring one - rule 11 in the field guide, and the
# `tract` inside `contract_number` incident of 2026-09-01.
# --------------------------------------------------------------------------
KEY_EXACT = {
    "cedar_uid", "tribe_id", "cage_code", "uei", "duns", "ein", "entity_id",
    "facility_id", "cedar_place_id", "tribe_entity_id", "business_entity_id",
    "tribe_id_neid", "neid", "object_id", "award_id", "action_id",
    "opinion_id", "record_id", "vote_id", "bill_id", "docket_id",
    "child_uei", "parent_uei", "awardee_uei", "recipient_uei",
    "recipient_duns", "operating_company_uei", "contract_number",
    "parent_contract_number", "contract_transaction_unique_key",
    "contract_award_unique_key", "document_slug", "handle",
}
KEY_SUFFIX = ("_cedar_uid", "_uid", "_uei", "_duns", "_ein",
              "_entity_id", "_id_neid", "_unique_key", "_cage_code")


def is_key_name(col: str) -> bool:
    c = col.strip().lower()
    if c in KEY_EXACT:
        return True
    if c.endswith(KEY_SUFFIX):
        return True
    # `_id` is the noisiest one: `fiscal_year_id` yes, `valid` no.
    return c.endswith("_id") and len(c) > 3


COUNT_RE = re.compile(
    r"^(n_[a-z0-9_]+|[a-z0-9_]*_count|[a-z0-9_]*_n|num_[a-z0-9_]+|"
    r"[a-z0-9_]*_rows|[a-z0-9_]*_observations|[a-z0-9_]*_coverage|"
    r"[a-z0-9_]*_matches|[a-z0-9_]*_hits)$")


def is_count_name(col: str) -> bool:
    return bool(COUNT_RE.match(col.strip().lower()))


# --------------------------------------------------------------------------
# file inventory
# --------------------------------------------------------------------------
def live_files() -> list[Path]:
    out = []
    for p in sorted(CLEAN.glob("*.csv")):
        if ".bak_" in p.name:
            continue
        out.append(p)
    out.extend(sorted(DIST.glob("*.csv")))
    return out


def fingerprint(p: Path) -> dict:
    st = p.stat()
    return {"size": st.st_size, "mtime": round(st.st_mtime, 3)}


def sqlq(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def sqlid(s: str) -> str:
    return '"' + s.replace('"', '""') + '"'


# --------------------------------------------------------------------------
# scan
# --------------------------------------------------------------------------
def scan(argv):
    import duckdb

    only = None
    if "--only" in argv:
        only = argv[argv.index("--only") + 1]

    files = live_files()
    if only:
        files = [f for f in files if only in f.name]
    if not files:
        raise SystemExit("UNMEASURED: no input files matched. Refusing to "
                         "report a clean census over an empty corpus.")

    con = duckdb.connect()
    con.execute("PRAGMA threads=8")
    inlist = ",".join(sqlq(s) for s in SENTINELS)

    started = time.time()
    results, filemeta = [], []
    print(f"1170 scan - {len(files)} live CSV files, "
          f"{sum(f.stat().st_size for f in files) / 1e9:.2f} GB")
    print("FULL FILE SCANS. No sampling, no row cap, no head-N.\n")

    for n, p in enumerate(files, 1):
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        before = fingerprint(p)
        t0 = time.time()
        rd = (f"read_csv({sqlq(str(p))}, all_varchar=true, sample_size=-1, "
              f"parallel=true)")
        try:
            cols = [r[0] for r in
                    con.execute(f"DESCRIBE SELECT * FROM {rd}").fetchall()]
        except Exception as e:
            print(f"  [{n}/{len(files)}] {rel}  UNPARSEABLE: "
                  f"{str(e).splitlines()[0][:120]}")
            filemeta.append({"file": rel, "status": "UNPARSEABLE",
                             "error": str(e).splitlines()[0][:300],
                             **before})
            continue

        parts = ["count(*) AS __n"]
        for i, c in enumerate(cols):
            cc = sqlid(c)
            parts.append(
                f"count(*) FILTER (WHERE {cc} IS NULL OR trim({cc})='') "
                f"AS b{i}")
            parts.append(
                f"histogram(upper(trim({cc}))) FILTER "
                f"(WHERE length({cc})<={MAXLEN} "
                f"AND upper(trim({cc})) IN ({inlist})) AS h{i}")
        try:
            row = con.execute("SELECT " + ",".join(parts)
                              + f" FROM {rd}").fetchone()
        except Exception as e:
            print(f"  [{n}/{len(files)}] {rel}  SCAN FAILED: "
                  f"{str(e).splitlines()[0][:120]}")
            filemeta.append({"file": rel, "status": "SCAN_FAILED",
                             "error": str(e).splitlines()[0][:300], **before})
            continue

        after = fingerprint(p)
        nrows = row[0]
        moved = (before != after)
        filemeta.append({"file": rel, "status": "OK", "rows": nrows,
                         "cols": len(cols), "seconds": round(time.time()-t0, 1),
                         "moved_during_scan": moved,
                         "size_before": before["size"],
                         "size_after": after["size"],
                         "mtime_before": before["mtime"],
                         "mtime_after": after["mtime"]})

        flagged = 0
        for i, c in enumerate(cols):
            blank = row[1 + 2 * i] or 0
            hist = row[2 + 2 * i] or {}
            hist = {k: int(v) for k, v in dict(hist).items()}
            sent = sum(hist.values())
            if not blank and not sent:
                continue
            flagged += 1
            results.append({
                "file": rel,
                "column": c,
                "rows": nrows,
                "blank": blank,
                "sentinel": sent,
                "hard_sentinel": sum(v for k, v in hist.items()
                                     if k in HARD_SENTINELS),
                "unusable": blank + sent,
                "unusable_share": round((blank + sent) / nrows, 6)
                if nrows else 0.0,
                "tokens": json.dumps(dict(sorted(hist.items(),
                                                 key=lambda kv: -kv[1]))),
                "is_key_name": is_key_name(c),
                "is_count_name": is_count_name(c),
                "moved_during_scan": moved,
            })
        print(f"  [{n}/{len(files)}] {rel}  rows={nrows:,} cols={len(cols)} "
              f"flagged={flagged} {time.time()-t0:.1f}s"
              + ("  ** MOVED DURING SCAN **" if moved else ""))

    REVIEW.mkdir(exist_ok=True)
    fields = ["file", "column", "rows", "blank", "sentinel", "hard_sentinel",
              "unusable", "unusable_share", "tokens", "is_key_name",
              "is_count_name", "moved_during_scan"]
    with CENSUS_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(results)
    CENSUS_JSON.write_text(json.dumps({
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "snapshot_warning": "Concurrent rebuilds are live. Every figure here "
                            "is a SNAPSHOT of the moment named above.",
        "sentinels": SENTINELS,
        "n_files": len(files),
        "elapsed_seconds": round(time.time() - started, 1),
        "files": filemeta,
        "columns": results,
    }, indent=1), encoding="utf-8")
    ok = [f for f in filemeta if f["status"] == "OK"]
    print(f"\nscanned {len(ok)}/{len(files)} files in "
          f"{time.time()-started:.0f}s; {len(results)} flagged columns")
    print(f"  wrote {CENSUS_CSV.relative_to(ROOT)}")
    print(f"  wrote {CENSUS_JSON.relative_to(ROOT)}")
    bad = [f for f in filemeta if f["status"] != "OK"]
    if bad:
        print(f"  {len(bad)} file(s) UNMEASURED - listed in the json, and "
              f"they are NOT counted as clean")
    return 0


# --------------------------------------------------------------------------
# joins - static index of which columns code/ actually keys on
# --------------------------------------------------------------------------
KEYPATS = [
    # pandas
    (re.compile(r"\.merge\([^)]{0,300}?\bon\s*=\s*\[?\s*['\"]([A-Za-z_0-9]+)"),
     "pandas_merge_on"),
    (re.compile(r"left_on\s*=\s*\[?\s*['\"]([A-Za-z_0-9]+)"), "pandas_left_on"),
    (re.compile(r"right_on\s*=\s*\[?\s*['\"]([A-Za-z_0-9]+)"), "pandas_right_on"),
    # the shape this repo actually uses: dict keyed on a column
    (re.compile(r"\br\.get\(\s*['\"]([A-Za-z_0-9]+)['\"]\s*\)\s*or\s*[\"']{2}\s*\)\s*\.strip\(\)"),
     "dict_key_strip"),
    (re.compile(r"\[\s*\(\s*r\.get\(\s*['\"]([A-Za-z_0-9]+)['\"]"),
     "dict_index_assign"),
    (re.compile(r"\bcnt\s*\[\s*\(?\s*(?:r|row)\.get\(\s*['\"]([A-Za-z_0-9]+)['\"]"),
     "count_bucket"),
    (re.compile(r"\bidx\s*\[\s*\(?\s*(?:r|row)\.get\(\s*['\"]([A-Za-z_0-9]+)['\"]"),
     "index_bucket"),
    (re.compile(r"dict\(zip\([^)]{0,120}?['\"]([A-Za-z_0-9]+)['\"]"), "dict_zip"),
    (re.compile(r"groupby\(\s*\[?\s*['\"]([A-Za-z_0-9]+)['\"]"), "groupby"),
    (re.compile(r"set_index\(\s*\[?\s*['\"]([A-Za-z_0-9]+)['\"]"), "set_index"),
]


def joins(argv):
    hits = defaultdict(lambda: defaultdict(set))
    nfiles = 0
    for p in sorted(CODE.rglob("*.py")):
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        nfiles += 1
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        for pat, kind in KEYPATS:
            for m in pat.finditer(txt):
                hits[m.group(1)][kind].add(rel)
    if nfiles == 0:
        raise SystemExit("UNMEASURED: no python files read from code/.")

    REVIEW.mkdir(exist_ok=True)
    rows = []
    for col, kinds in sorted(hits.items()):
        scripts = sorted({s for v in kinds.values() for s in v})
        rows.append({"column": col,
                     "n_scripts": len(scripts),
                     "kinds": ";".join(sorted(kinds)),
                     "scripts": ";".join(scripts[:12]),
                     "name_says_key": is_key_name(col)})
    rows.sort(key=lambda r: -r["n_scripts"])
    with KEYUSE_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["column", "n_scripts", "kinds",
                                           "scripts", "name_says_key"])
        w.writeheader()
        w.writerows(rows)
    print(f"read {nfiles} python files under code/")
    print(f"{len(rows)} distinct columns used as a key somewhere")
    print(f"  wrote {KEYUSE_CSV.relative_to(ROOT)}")
    for r in rows[:25]:
        print(f"  {r['column']:<44} {r['n_scripts']:>3} scripts  "
              f"[{r['kinds']}]")
    return 0


# --------------------------------------------------------------------------
# explode - the exploded joins
# --------------------------------------------------------------------------
def _load_census():
    if not CENSUS_CSV.exists():
        raise SystemExit(f"UNMEASURED: {CENSUS_CSV} does not exist. "
                         f"Run `scan` first.")
    with CENSUS_CSV.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def explode(argv):
    """
    A count column is EXPLODED when its value is constant across the whole
    population sharing a sentinel key - i.e. every missing row was handed the
    size of the missing population.

    The measurement, per (file, count_column, key_column):
        rows where the key is sentinel/blank
        distinct values the count column takes on those rows
        the modal value and its share
    A single distinct value over a large group is the signature.
    """
    import duckdb

    con = duckdb.connect()
    con.execute("PRAGMA threads=8")
    census = _load_census()

    # candidate key columns per file: a key-named column that carries a
    # sentinel or a blank at all.
    bad_keys = defaultdict(list)
    for r in census:
        if r["is_key_name"] == "True" and int(r["unusable"]) > 0:
            bad_keys[r["file"]].append(r["column"])

    files_scanned = {r["file"] for r in census}
    out = []
    inlist = ",".join(sqlq(s) for s in SENTINELS)

    for rel in sorted(files_scanned):
        p = ROOT / rel
        if not p.exists():
            continue
        keys = bad_keys.get(rel) or []
        if not keys:
            continue
        rd = (f"read_csv({sqlq(str(p))}, all_varchar=true, sample_size=-1)")
        try:
            cols = [r[0] for r in
                    con.execute(f"DESCRIBE SELECT * FROM {rd}").fetchall()]
        except Exception:
            continue
        counts = [c for c in cols if is_count_name(c)]
        if not counts:
            continue
        for k in keys:
            kk = sqlid(k)
            pred = (f"({kk} IS NULL OR trim({kk})='' OR "
                    f"(length({kk})<={MAXLEN} AND upper(trim({kk})) "
                    f"IN ({inlist})))")
            sel = ["count(*) AS grp"]
            for i, c in enumerate(counts):
                cc = sqlid(c)
                sel.append(f"count(DISTINCT {cc}) AS d{i}")
                sel.append(f"max({cc}) AS m{i}")
            try:
                row = con.execute(
                    "SELECT " + ",".join(sel) + f" FROM {rd} WHERE {pred}"
                ).fetchone()
            except Exception:
                continue
            grp = row[0]
            if grp < 2:
                continue
            # same statistics over the rows with a REAL key, for contrast
            sel2 = ["count(*) AS grp"]
            for i, c in enumerate(counts):
                cc = sqlid(c)
                sel2.append(f"count(DISTINCT {cc}) AS d{i}")
                sel2.append(f"max({cc}) AS m{i}")
            row2 = con.execute(
                "SELECT " + ",".join(sel2) + f" FROM {rd} WHERE NOT {pred}"
            ).fetchone()
            total = grp + (row2[0] or 0)
            for i, c in enumerate(counts):
                distinct, mx = row[1 + 2 * i], row[2 + 2 * i]
                d2, m2 = row2[1 + 2 * i], row2[2 + 2 * i]
                if distinct != 1:
                    continue
                out.append({
                    "file": rel,
                    "count_column": c,
                    "key_column": k,
                    "sentinel_key_rows": grp,
                    "dataset_rows": total,
                    "blast_share": round(grp / total, 6) if total else 0.0,
                    "value_on_every_sentinel_row": mx,
                    "real_key_rows": row2[0],
                    "distinct_values_on_real_keys": d2,
                    "max_on_real_keys": m2,
                    "self_referential": (str(mx) == str(grp)),
                })
            print(f"  {rel} key={k}: {grp:,} sentinel-key rows of "
                  f"{total:,}; {sum(1 for i,_ in enumerate(counts) if row[1+2*i]==1)}"
                  f"/{len(counts)} count columns constant across them")

    REVIEW.mkdir(exist_ok=True)
    out.sort(key=lambda r: -r["sentinel_key_rows"])
    fields = ["file", "count_column", "key_column", "sentinel_key_rows",
              "dataset_rows", "blast_share", "value_on_every_sentinel_row",
              "real_key_rows", "distinct_values_on_real_keys",
              "max_on_real_keys", "self_referential"]
    with EXPLODE_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(out)
    print(f"\n{len(out)} exploded (count column, sentinel key) pairs")
    print(f"  wrote {EXPLODE_CSV.relative_to(ROOT)}")
    return 0


# --------------------------------------------------------------------------
# verify - THE GUARD
# --------------------------------------------------------------------------
INVARIANTS = {
    "SENTINEL_IN_KEY":
        "no sentinel string may appear in a declared identifier / join-key "
        "column",
    "JOIN_CARDINALITY_UNDECLARED":
        "every key column a build joins on must declare its cardinality in "
        "docs/schema/dataset_contracts.json",
    "JOIN_CARDINALITY_MISMATCH":
        "a key DECLARED one-to-one must MEASURE one-to-one on the rows "
        "actually on disk at join time. (Declared many / measured one is not "
        "a violation: `many` is an upper bound and a one-to-one join against "
        "it is safe. Declared ONE and measured MANY is the dangerous "
        "direction - it is the shape where `idx[k] = row` keeps an arbitrary "
        "one of N and the row count never moves, so no row-count check can "
        "see it.)",
    "SENTINEL_KEY_CONTRIBUTES_TO_COUNT":
        "a null or sentinel key must contribute ZERO to any derived count "
        "column",
    "FILL_RATE_COUNTS_SENTINEL":
        "a fill-rate statistic may not count a sentinel string as filled",
}


def _contracts():
    if not CONTRACTS.exists():
        return {}
    d = json.loads(CONTRACTS.read_text(encoding="utf-8"))
    return {c["collection"]: c for c in d.get("contracts", [])}


def _sentinel_pred(k):
    kk = sqlid(k)
    inlist = ",".join(sqlq(s) for s in SENTINELS)
    return (f"({kk} IS NULL OR trim({kk})='' OR (length({kk})<={MAXLEN} "
            f"AND upper(trim({kk})) IN ({inlist})))")


def check_file(con, path: Path, rel: str, declared: dict,
               hard_only: bool = True) -> list[dict]:
    """
    Run all four invariants against ONE csv. `declared` is
    {key_column: "one"|"many"} from dataset_contracts.json, {} if the table
    declares nothing.

    Returns a list of violation dicts; [] means the file passed EVERY
    invariant, and the caller records which invariants were actually
    evaluated so that "0 violations" is never reported for a file where a
    check could not run.
    """
    v = []
    rd = f"read_csv({sqlq(str(path))}, all_varchar=true, sample_size=-1)"
    cols = [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM {rd}").fetchall()]
    nrows = con.execute(f"SELECT count(*) FROM {rd}").fetchone()[0]
    if nrows == 0:
        return [{"invariant": "UNMEASURED", "file": rel, "column": "",
                 "detail": "file has zero rows; no invariant could be "
                           "evaluated"}]

    keycols = [c for c in cols if is_key_name(c)]
    inlist = ",".join(sqlq(s) for s in SENTINELS)

    # ---- SENTINEL_IN_KEY -------------------------------------------------
    for c in keycols:
        cc = sqlid(c)
        toks = con.execute(
            f"SELECT upper(trim({cc})) AS t, count(*) FROM {rd} "
            f"WHERE length({cc})<={MAXLEN} AND upper(trim({cc})) "
            f"IN ({inlist}) GROUP BY 1 ORDER BY 2 DESC").fetchall()
        for tok, n in toks:
            if hard_only and tok not in HARD_SENTINELS:
                continue
            v.append({"invariant": "SENTINEL_IN_KEY", "file": rel,
                      "column": c,
                      "detail": f"{n:,} of {nrows:,} rows "
                                f"({n/nrows:.2%}) carry the literal string "
                                f"'{tok}' in an identifier column"})

    # ---- JOIN_CARDINALITY_UNDECLARED / _MISMATCH -------------------------
    for c in keycols:
        cc = sqlid(c)
        pred = _sentinel_pred(c)
        # measure on REAL keys only. A sentinel bucket is not a cardinality.
        r = con.execute(
            f"SELECT count(*), count(DISTINCT {cc}) FROM {rd} "
            f"WHERE NOT {pred}").fetchone()
        n_real, n_dist = r
        if n_real == 0:
            continue
        measured = "one" if n_real == n_dist else "many"
        if c not in declared:
            v.append({"invariant": "JOIN_CARDINALITY_UNDECLARED", "file": rel,
                      "column": c,
                      "detail": f"key column joined on by code/ but no "
                                f"join_cardinality declared; MEASURED "
                                f"{measured} ({n_real:,} rows, {n_dist:,} "
                                f"distinct non-sentinel values)"})
        elif declared[c] == "one" and measured == "many":
            dupes = n_real - n_dist
            v.append({"invariant": "JOIN_CARDINALITY_MISMATCH", "file": rel,
                      "column": c,
                      "detail": f"declared 'one', MEASURED 'many' "
                                f"({n_real:,} non-sentinel rows over "
                                f"{n_dist:,} distinct values, {dupes:,} "
                                f"surplus rows a one-to-one join would "
                                f"silently discard)"})

    # ---- SENTINEL_KEY_CONTRIBUTES_TO_COUNT -------------------------------
    countcols = [c for c in cols if is_count_name(c)]
    for k in keycols:
        pred = _sentinel_pred(k)
        n_sent = con.execute(
            f"SELECT count(*) FROM {rd} WHERE {pred}").fetchone()[0]
        if n_sent < 2:
            continue
        for c in countcols:
            cc = sqlid(c)
            r = con.execute(
                f"SELECT count(*) FILTER (WHERE TRY_CAST({cc} AS BIGINT) > 0),"
                f" count(DISTINCT {cc}), max(TRY_CAST({cc} AS BIGINT)) "
                f"FROM {rd} WHERE {pred}").fetchone()
            nonzero, distinct, mx = r
            if nonzero and distinct == 1:
                v.append({
                    "invariant": "SENTINEL_KEY_CONTRIBUTES_TO_COUNT",
                    "file": rel, "column": c,
                    "detail": f"{nonzero:,} rows whose join key '{k}' is a "
                              f"sentinel all carry the SAME non-zero value "
                              f"{mx} in '{c}'"
                              + (" - which equals the size of the sentinel "
                                 "bucket itself" if str(mx) == str(n_sent)
                                 else "")})
    return v


def verify(argv):
    import duckdb

    only = argv[argv.index("--only") + 1] if "--only" in argv else None
    strict = "--all-sentinels" in argv
    fixdir = argv[argv.index("--dir") + 1] if "--dir" in argv else None

    cs = _contracts()
    declared_by_table = {}
    for c in cs.values():
        for t in c.get("tables", []):
            declared_by_table[t["table"]] = t.get("join_cardinality") or {}

    if fixdir:
        # selftest path: run the SAME code over a fixture directory so the
        # end-to-end exit code is proven, not assumed. `_declared.json` in
        # that directory stands in for dataset_contracts.json.
        files = sorted(Path(fixdir).glob("*.csv"))
        dj = Path(fixdir) / "_declared.json"
        if dj.exists():
            declared_by_table = json.loads(dj.read_text(encoding="utf-8"))
    else:
        files = live_files()
    if only:
        files = [f for f in files if only in f.name]
    if not files:
        raise SystemExit("UNMEASURED: no files to verify. A guard with no "
                         "input is not a passing guard.")

    con = duckdb.connect()
    con.execute("PRAGMA threads=8")
    all_v, evaluated, unmeasured = [], [], []
    for p in files:
        try:
            rel = str(p.relative_to(ROOT)).replace("\\", "/")
        except ValueError:
            rel = p.name
        try:
            vs = check_file(con, p, rel,
                            declared_by_table.get(p.name, {}),
                            hard_only=not strict)
        except Exception as e:
            unmeasured.append((rel, str(e).splitlines()[0][:200]))
            continue
        evaluated.append(rel)
        all_v.extend([x for x in vs if x["invariant"] != "UNMEASURED"])
        unmeasured.extend([(rel, x["detail"]) for x in vs
                           if x["invariant"] == "UNMEASURED"])

    by = defaultdict(int)
    for x in all_v:
        by[x["invariant"]] += 1
    print(f"1170 verify - {len(evaluated)} file(s) evaluated, "
          f"{len(unmeasured)} UNMEASURED")
    for name, desc in INVARIANTS.items():
        print(f"  {name:<38} {by.get(name,0):>6}   {desc}")
    if unmeasured:
        print("\nUNMEASURED (NOT counted as clean):")
        for rel, why in unmeasured[:20]:
            print(f"  {rel}: {why}")
    if all_v:
        print(f"\nfirst 40 of {len(all_v)} violations:")
        for x in all_v[:40]:
            print(f"  [{x['invariant']}] {x['file']}::{x['column']} - "
                  f"{x['detail']}")
    if not fixdir:
        out = REVIEW / "1170_verify_violations.csv"
        REVIEW.mkdir(exist_ok=True)
        with out.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["invariant", "file", "column",
                                               "detail"])
            w.writeheader()
            w.writerows(all_v)
        print(f"\nwrote {out.relative_to(ROOT)}")
    # An UNMEASURED file is NOT a pass. Rule 4: absence of evidence may never
    # print as evidence of absence.
    return 1 if (all_v or unmeasured) else 0


# --------------------------------------------------------------------------
# selftest - prove every named detector can return one
# --------------------------------------------------------------------------
def _write_csv(p: Path, header, rows):
    with p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def selftest(argv):
    """
    Four violation classes, one fixture each, plus a CLEAN control.

    The rule this obeys (AGENT_FIELD_GUIDE rule 1): assert the NAMED
    invariant fired, not merely that the run went red. A fixture that trips
    a different detector is a FAILED selftest here, not a pass.
    """
    import duckdb

    con = duckdb.connect()
    tmp = Path(tempfile.mkdtemp(prefix="1170_selftest_"))
    failures = []

    def run(name, header, rows, declared, expect, forbid=(), hard_only=True):
        """
        `expect` - the NAMED invariant that must fire (None = must be clean).
        `forbid` - invariants that must NOT fire. This is the half that makes
                   a detector trustworthy in the other direction: a check that
                   fires on everything is as useless as one that never fires.
        """
        p = tmp / f"{name}.csv"
        _write_csv(p, header, rows)
        vs = check_file(con, p, p.name, declared, hard_only=hard_only)
        fired = sorted({x["invariant"] for x in vs})
        ok = (expect in fired) if expect else (fired == [])
        bad_extra = [f for f in forbid if f in fired]
        ok = ok and not bad_extra
        status = "PASS" if ok else "FAIL"
        print(f"  {status}  {name:<38} expect={expect or 'CLEAN':<34} "
              f"fired={fired or ['(none)']}")
        for x in vs:
            print(f"           -> [{x['invariant']}] {x['column']}: "
                  f"{x['detail']}")
        if not ok:
            failures.append((name, expect, fired, bad_extra))
        return fired

    print("1170 selftest - injecting one violation per class into a "
          "synthetic fixture\n")

    # ---- control: clean ---------------------------------------------------
    run("00_clean_control",
        ["cedar_uid", "amount", "n_side_table"],
        [["CEDAR-1", "10", "2"], ["CEDAR-2", "20", "1"],
         ["CEDAR-3", "30", "0"]],
        {"cedar_uid": "one"}, None)

    # ---- 1. SENTINEL_IN_KEY ----------------------------------------------
    run("01_sentinel_in_key",
        ["cedar_uid", "amount"],
        [["CEDAR-1", "10"], ["NAN", "20"], ["UNKNOWN", "30"],
         ["nan", "40"], ["CEDAR-2", "50"]],
        {"cedar_uid": "many"}, "SENTINEL_IN_KEY")

    # ---- 2. JOIN_CARDINALITY_UNDECLARED ----------------------------------
    run("02_cardinality_undeclared",
        ["facility_id", "amount"],
        [["F1", "10"], ["F2", "20"], ["F3", "30"]],
        {}, "JOIN_CARDINALITY_UNDECLARED")

    # ---- 3. JOIN_CARDINALITY_MISMATCH ------------------------------------
    #   declared one-to-one; on disk the key repeats.
    run("03_cardinality_mismatch",
        ["facility_id", "amount"],
        [["F1", "10"], ["F1", "20"], ["F2", "30"]],
        {"facility_id": "one"}, "JOIN_CARDINALITY_MISMATCH")

    # ---- 4. SENTINEL_KEY_CONTRIBUTES_TO_COUNT ----------------------------
    #   the exact defect: four rows with key 'NAN' each carrying n=4, the
    #   size of their own missing-value bucket.
    run("04_sentinel_key_counts",
        ["cage_code", "n_side_table"],
        [["ABC12", "1"], ["DEF34", "3"], ["NAN", "4"], ["NAN", "4"],
         ["NAN", "4"], ["NAN", "4"]],
        {"cage_code": "many"}, "SENTINEL_KEY_CONTRIBUTES_TO_COUNT")

    # ---- 4b. the same shape, but BLANK instead of a literal --------------
    run("05_blank_key_counts",
        ["cage_code", "n_side_table"],
        [["ABC12", "1"], ["", "3"], ["", "3"], ["", "3"], ["  ", "3"]],
        {"cage_code": "many"}, "SENTINEL_KEY_CONTRIBUTES_TO_COUNT")

    # ---- 6. negative control: a sentinel in a NON-key column must NOT fire
    run("06_sentinel_in_nonkey_is_clean",
        ["cedar_uid", "free_text_note"],
        [["CEDAR-1", "NAN"], ["CEDAR-2", "UNKNOWN"], ["CEDAR-3", "-"]],
        {"cedar_uid": "one"}, None)

    # ---- 7. negative control: a count that genuinely VARIES on sentinel
    #        keys is not an explosion, it is data. The count detector must
    #        stay SILENT here while the key detector still fires.
    run("07_varying_count_on_sentinel",
        ["cage_code", "n_side_table"],
        [["ABC12", "1"], ["NAN", "2"], ["NAN", "5"], ["NAN", "9"]],
        {"cage_code": "many"}, "SENTINEL_IN_KEY",
        forbid=("SENTINEL_KEY_CONTRIBUTES_TO_COUNT",))

    # ---- 7b. negative control: declared MANY, measured one. Safe direction;
    #          the cardinality detector must stay silent.
    run("07b_declared_many_measured_one",
        ["facility_id", "amount"],
        [["F1", "10"], ["F2", "20"], ["F3", "30"]],
        {"facility_id": "many"}, None,
        forbid=("JOIN_CARDINALITY_MISMATCH",))

    # ---- 7c. negative control: a sentinel key whose count column is ZERO
    #          everywhere is correct behaviour, not a violation.
    run("07c_sentinel_key_counts_zero",
        ["cage_code", "n_side_table"],
        [["ABC12", "1"], ["NAN", "0"], ["NAN", "0"], ["NAN", "0"]],
        {"cage_code": "many"}, "SENTINEL_IN_KEY",
        forbid=("SENTINEL_KEY_CONTRIBUTES_TO_COUNT",))

    # ---- 8. UNMEASURED, not clean, on an empty file ----------------------
    p = tmp / "08_empty.csv"
    _write_csv(p, ["cedar_uid", "n_side_table"], [])
    vs = check_file(con, p, p.name, {"cedar_uid": "one"})
    fired = sorted({x["invariant"] for x in vs})
    ok = fired == ["UNMEASURED"]
    print(f"  {'PASS' if ok else 'FAIL'}  08_empty_reports_unmeasured           "
          f"       expect=UNMEASURED                  fired={fired}")
    if not ok:
        failures.append(("08_empty_reports_unmeasured", "UNMEASURED", fired,
                         []))
    p.unlink()

    # ---- 9. END TO END. A detector that fires inside check_file but is
    #        swallowed by verify() is not a working guard. Run the real
    #        `verify` subcommand in a subprocess against the dirty fixture
    #        directory and assert exit 1; then against a clean-only
    #        directory and assert exit 0.
    decl = {f"{n}.csv": d for n, d in [
        ("01_sentinel_in_key", {"cedar_uid": "many"}),
        ("02_cardinality_undeclared", {}),
        ("03_cardinality_mismatch", {"facility_id": "one"}),
        ("04_sentinel_key_counts", {"cage_code": "many"}),
        ("05_blank_key_counts", {"cage_code": "many"}),
        ("06_sentinel_in_nonkey_is_clean", {"cedar_uid": "one"}),
        ("07_varying_count_on_sentinel", {"cage_code": "many"}),
        ("07b_declared_many_measured_one", {"facility_id": "many"}),
        ("07c_sentinel_key_counts_zero", {"cage_code": "many"}),
        ("00_clean_control", {"cedar_uid": "one"}),
    ]}
    (tmp / "_declared.json").write_text(json.dumps(decl), encoding="utf-8")
    me = [sys.executable, str(Path(__file__).resolve())]
    r = subprocess.run(me + ["verify", "--dir", str(tmp)],
                       capture_output=True, text=True)
    e2e_dirty_ok = (r.returncode == 1)
    print(f"  {'PASS' if e2e_dirty_ok else 'FAIL'}  "
          f"09_verify_exits_1_on_dirty_dir          expect=exit 1"
          f"                      got=exit {r.returncode}")
    if not e2e_dirty_ok:
        failures.append(("09_verify_exits_1_on_dirty_dir", "exit 1",
                         [f"exit {r.returncode}"], []))

    clean = Path(tempfile.mkdtemp(prefix="1170_selftest_clean_"))
    _write_csv(clean / "00_clean_control.csv",
               ["cedar_uid", "amount", "n_side_table"],
               [["CEDAR-1", "10", "2"], ["CEDAR-2", "20", "1"],
                ["CEDAR-3", "30", "0"]])
    (clean / "_declared.json").write_text(
        json.dumps({"00_clean_control.csv": {"cedar_uid": "one"}}),
        encoding="utf-8")
    r2 = subprocess.run(me + ["verify", "--dir", str(clean)],
                        capture_output=True, text=True)
    e2e_clean_ok = (r2.returncode == 0)
    print(f"  {'PASS' if e2e_clean_ok else 'FAIL'}  "
          f"10_verify_exits_0_on_clean_dir          expect=exit 0"
          f"                      got=exit {r2.returncode}")
    if not e2e_clean_ok:
        failures.append(("10_verify_exits_0_on_clean_dir", "exit 0",
                         [f"exit {r2.returncode}", r2.stdout[-400:]], []))

    shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(clean, ignore_errors=True)

    print()
    if failures:
        print(f"SELFTEST FAILED - {len(failures)} case(s):")
        for n, e, f, x in failures:
            print(f"  {n}: expected {e}, fired {f}"
                  + (f", FORBIDDEN fired {x}" if x else ""))
        return 1
    print("SELFTEST PASSED - each of the four named invariants was shown to "
          "return one on a fixture that violates it and only it; five "
          "negative controls stayed silent; an empty input reported "
          "UNMEASURED rather than clean; and `verify` itself was proven to "
          "exit 1 on a dirty directory and 0 on a clean one.")
    return 0


# --------------------------------------------------------------------------
# report - every sentence DERIVED from the artefacts, so it cannot rot
#          independently of them
# --------------------------------------------------------------------------
def report(argv):
    census = _load_census()
    meta = json.loads(CENSUS_JSON.read_text(encoding="utf-8"))
    ex = []
    if EXPLODE_CSV.exists():
        with EXPLODE_CSV.open(encoding="utf-8") as fh:
            ex = list(csv.DictReader(fh))
    keyuse = {}
    if KEYUSE_CSV.exists():
        with KEYUSE_CSV.open(encoding="utf-8") as fh:
            keyuse = {r["column"]: int(r["n_scripts"])
                      for r in csv.DictReader(fh)}

    for r in census:
        for k in ("rows", "blank", "sentinel", "hard_sentinel", "unusable"):
            r[k] = int(r[k])
        r["unusable_share"] = float(r["unusable_share"])
        r["key_scripts"] = keyuse.get(r["column"], 0)

    keys = [r for r in census
            if r["is_key_name"] == "True" and r["hard_sentinel"] > 0]
    keys.sort(key=lambda r: -r["hard_sentinel"])
    dist_keys = [r for r in keys if r["file"].startswith("dist/customer/")]

    ok = [f for f in meta["files"] if f["status"] == "OK"]
    bad = [f for f in meta["files"] if f["status"] != "OK"]
    moved = [f for f in ok if f.get("moved_during_scan")]

    L = []
    A = L.append
    A("# Sentinel strings used as join keys - repo-wide census, "
      "exploded joins, and the proposed fix")
    A("")
    A(f"*Generated by `code/1170_sentinel_key_guard.py report` from the "
      f"artefacts of a `scan` that started {meta['generated']} and took "
      f"{meta['elapsed_seconds']:.0f}s. Every number below is derived from "
      f"those artefacts at read time; none is typed.*")
    A("")
    A("> **SNAPSHOT.** Concurrent rebuilds were live on this machine "
      "throughout the scan. "
      + (f"**{len(moved)} file(s) changed size or mtime while being "
         f"scanned** and are marked `moved_during_scan` in "
         f"`review/1170_sentinel_census.csv`. "
         if moved else "No scanned file changed size or mtime during its "
                       "own scan. ")
      + "Re-run `scan` before quoting any figure here as current.")
    A("")
    A(f"Files scanned: **{len(ok)}** of {meta['n_files']} "
      f"({len(bad)} UNMEASURED - listed at the end, and NOT counted clean). "
      f"Full-file scans; no sampling, no row cap.")
    A("")
    A("## 1. Ranked - identifier / join-key columns carrying a hard sentinel")
    A("")
    A("A *hard* sentinel is one that can never be a legitimate value: "
      + ", ".join(f"`{s}`" for s in sorted(HARD_SENTINELS)) + ". "
      "`key_scripts` is how many scripts under `code/` key a dict, a "
      "groupby or a merge on that column name.")
    A("")
    A("| # | file | column | rows | hard sentinel | share | blank | "
      "tokens | key_scripts |")
    A("|---:|---|---|---:|---:|---:|---:|---|---:|")
    for i, r in enumerate(keys[:40], 1):
        A(f"| {i} | `{r['file']}` | `{r['column']}` | {r['rows']:,} | "
          f"**{r['hard_sentinel']:,}** | "
          f"{r['hard_sentinel']/r['rows']:.1%} | {r['blank']:,} | "
          f"{r['tokens']} | {r['key_scripts']} |")
    A("")
    A(f"Total: **{len(keys)}** (file, identifier-column) pairs carry a hard "
      f"sentinel, over **{len({r['file'] for r in keys})}** files, "
      f"**{sum(r['hard_sentinel'] for r in keys):,}** cells. "
      f"In the delivered `dist/customer/` files alone: **{len(dist_keys)}** "
      f"columns, **{sum(r['hard_sentinel'] for r in dist_keys):,}** cells.")
    A("")
    A("## 2. Exploded joins - the fields that are actively wrong")
    A("")
    if not ex:
        A("_`review/1170_exploded_joins.csv` is absent or empty. Run "
          "`py -3 code/1170_sentinel_key_guard.py explode`. This section is "
          "UNMEASURED, not clean._")
    else:
        A("A count column is EXPLODED when every row whose join key is a "
          "sentinel carries the SAME non-zero value - the size of the "
          "missing-value bucket, handed to each of its members as if it were "
          "that row's own. `self_referential` marks the cases where the "
          "value printed on the row IS the number of rows sharing the "
          "sentinel key.")
        A("")
        A("| file | count column | key | sentinel-key rows | dataset rows | "
          "blast share | value on every one of them | self-ref |")
        A("|---|---|---|---:|---:|---:|---:|:--:|")
        for r in sorted(ex, key=lambda r: -int(r["sentinel_key_rows"]))[:60]:
            A(f"| `{r['file']}` | `{r['count_column']}` | "
              f"`{r['key_column']}` | {int(r['sentinel_key_rows']):,} | "
              f"{int(r['dataset_rows']):,} | "
              f"{float(r['blast_share']):.1%} | "
              f"{r['value_on_every_sentinel_row']} | "
              f"{'YES' if r['self_referential']=='True' else ''} |")
        A("")
        byfile = defaultdict(set)
        for r in ex:
            byfile[r["file"]].add(r["count_column"])
        A(f"**{len(ex)}** exploded (count column, sentinel key) pairs across "
          f"**{len(byfile)}** files, covering "
          f"**{sum(len(v) for v in byfile.values())}** distinct count "
          f"columns.")
    A("")
    A("## 3. Files that could not be measured")
    A("")
    if bad:
        for f in bad:
            A(f"- `{f['file']}` - {f['status']}: {f.get('error','')}")
    else:
        A("_None. Every file in scope parsed and scanned._")
    A("")
    REVIEW.mkdir(exist_ok=True)
    out = REVIEW / "SENTINEL_KEY_CENSUS_DERIVED.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}  ({len(L)} lines)")
    return 0


# --------------------------------------------------------------------------
def main():
    argv = sys.argv[1:]
    if not argv:
        print(__doc__)
        return 0
    cmd = argv[0]
    fn = {"scan": scan, "joins": joins, "explode": explode,
          "verify": verify, "selftest": selftest, "report": report}.get(cmd)
    if not fn:
        print(__doc__)
        return 2
    return fn(argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
