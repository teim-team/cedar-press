#!/usr/bin/env python3
"""
1168 - harmonization_audit

READ-ONLY measurement of the 13 customer datasets in `dist/customer/`.
Writes NOTHING into dist/. Writes only into
`docs/harmonization_audit_2026-09-03/` (JSON evidence) so every number in
`docs/DATASET_HARMONIZATION_AUDIT_2026-09-03.md` can be re-derived.

No network. No caps: every profile figure below is a FULL-FILE stream via
duckdb `read_csv(..., all_varchar=true, sample_size=-1)`. Where a figure is
capped the JSON says so in a `cap` field; there are currently none.

    py -3 code/1168_harmonization_audit.py census    # column census across 13
    py -3 code/1168_harmonization_audit.py profile   # per-column fill + cardinality + small vocabularies
    py -3 code/1168_harmonization_audit.py codebook  # codebook <-> shipped column diff, both directions
    py -3 code/1168_harmonization_audit.py identity  # cedar_uid / canonical_name agreement across datasets
    py -3 code/1168_harmonization_audit.py all

Snapshot discipline: dist/customer is being rebuilt concurrently. Every output
carries the mtime+size of each CSV it read, so a later reader can tell whether
the file moved under the measurement.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
import time

import duckdb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUST = os.path.join(ROOT, "dist", "customer")
OUT = os.path.join(ROOT, "docs", "harmonization_audit_2026-09-03")

DATASETS = [
    "contractors", "deals", "federal-register", "funding", "gaming",
    "legislation", "lobbying", "nagpra", "native-owned-businesses",
    "natural-resources", "nest", "nonprofits", "subcontracting",
]

# columns whose full distinct-value set we always want, regardless of cardinality
VOCAB_MAX = 40


def _path(d):
    return os.path.join(CUST, d + ".csv")


def _stamp(d):
    p = _path(d)
    st = os.stat(p)
    return {"file": os.path.relpath(p, ROOT).replace("\\", "/"),
            "bytes": st.st_size,
            "mtime": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(st.st_mtime))}


def _headers(d):
    with open(_path(d), newline="", encoding="utf-8", errors="replace") as fh:
        return next(csv.reader(fh))


def _ensure_out():
    os.makedirs(OUT, exist_ok=True)


def _rel(path):
    return read_csv_expr(path)


def read_csv_expr(path):
    q = path.replace("'", "''")
    return f"read_csv('{q}', all_varchar=true, sample_size=-1, header=true)"


# ---------------------------------------------------------------- census
def census():
    _ensure_out()
    inv = {}
    per = {}
    for d in DATASETS:
        cols = _headers(d)
        per[d] = cols
        for c in cols:
            inv.setdefault(c, []).append(d)
    res = {"snapshot": {d: _stamp(d) for d in DATASETS},
           "columns_per_dataset": {d: len(per[d]) for d in DATASETS},
           "distinct_column_names": len(inv),
           "headers": per,
           "shared": {c: ds for c, ds in inv.items() if len(ds) >= 2}}
    with open(os.path.join(OUT, "census.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    print(f"distinct column names across 13 datasets: {len(inv)}")
    for d in DATASETS:
        print(f"  {d:26s} {len(per[d]):4d} columns")
    print(f"shared (>=2 datasets): {len(res['shared'])}")
    return res


# ---------------------------------------------------------------- profile
def profile(only=None):
    _ensure_out()
    con = duckdb.connect()
    con.execute("PRAGMA threads=4")
    out = {}
    for d in DATASETS:
        if only and d != only:
            continue
        cols = _headers(d)
        src = read_csv_expr(_path(d))
        t0 = time.time()
        # one pass: rows, non-blank per column, approx distinct per column
        sel = ["count(*) AS __rows"]
        for i, c in enumerate(cols):
            q = c.replace('"', '""')
            sel.append(f'count(nullif(trim("{q}"), \'\')) AS "nb_{i}"')
            sel.append(f'approx_count_distinct(nullif(trim("{q}"), \'\')) AS "nd_{i}"')
        row = con.execute(f"SELECT {', '.join(sel)} FROM {src}").fetchone()
        nrows = row[0]
        prof = {}
        low = []
        for i, c in enumerate(cols):
            nb = row[1 + 2 * i]
            nd = row[2 + 2 * i]
            prof[c] = {"nonblank": int(nb), "blank": int(nrows - nb),
                       "pct_blank": round(100.0 * (nrows - nb) / nrows, 4) if nrows else None,
                       "approx_distinct": int(nd)}
            if nd and nd <= VOCAB_MAX:
                low.append(c)
        # second pass: exact vocabularies for low-cardinality columns
        for c in low:
            q = c.replace('"', '""')
            vals = con.execute(
                f'SELECT nullif(trim("{q}"), \'\') v, count(*) n FROM {src} '
                f'WHERE nullif(trim("{q}"), \'\') IS NOT NULL GROUP BY 1 ORDER BY 2 DESC'
            ).fetchall()
            if len(vals) <= VOCAB_MAX:
                prof[c]["vocabulary"] = {str(v): int(n) for v, n in vals}
        out[d] = {"snapshot": _stamp(d), "rows": int(nrows),
                  "columns": len(cols), "seconds": round(time.time() - t0, 1),
                  "profile": prof}
        print(f"{d:26s} rows={nrows:>9,}  cols={len(cols):>4}  "
              f"empty_cols={sum(1 for v in prof.values() if v['nonblank'] == 0):>3}  "
              f"{out[d]['seconds']}s", flush=True)
        with open(os.path.join(OUT, f"profile_{d}.json"), "w", encoding="utf-8") as fh:
            json.dump(out[d], fh, indent=1)
    return out


# ---------------------------------------------------------------- codebook
CB_COL_RE = re.compile(r"^\s*\|\s*`?([A-Za-z_][A-Za-z0-9_.]*)`?\s*\|")


def codebook():
    _ensure_out()
    res = {}
    for d in DATASETS:
        cb = os.path.join(CUST, d + "__CODEBOOK.md")
        shipped = _headers(d)
        named = []
        if os.path.exists(cb):
            with open(cb, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    m = CB_COL_RE.match(line)
                    # 'column' is the markdown table HEADER cell, not a column.
                    # Reported as a phantom on all 13 datasets on the first run;
                    # that was a detector artefact, not a defect. (Field guide s3.)
                    if m and m.group(1) != "column":
                        named.append(m.group(1))
        named_set = []
        for n in named:
            if n not in named_set:
                named_set.append(n)
        res[d] = {
            "codebook_exists": os.path.exists(cb),
            "shipped_columns": len(shipped),
            "codebook_named_columns": len(named_set),
            "shipped_not_in_codebook": [c for c in shipped if c not in named_set],
            "codebook_not_shipped": [c for c in named_set if c not in shipped],
        }
        print(f"{d:26s} shipped={len(shipped):>4} codebook={len(named_set):>4} "
              f"missing_from_codebook={len(res[d]['shipped_not_in_codebook']):>4} "
              f"phantom_in_codebook={len(res[d]['codebook_not_shipped']):>4}")
    with open(os.path.join(OUT, "codebook_diff.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    return res


# ---------------------------------------------------------------- identity
UID_COLS = {
    "contractors": ("cedar_uid", "canonical_name"),
    "deals": ("cedar_uid", None),
    "federal-register": ("cedar_uid", None),
    "funding": ("cedar_uid", "canonical_name"),
    "gaming": ("cedar_uid", "tribe_canonical_name"),
    "lobbying": ("cedar_uid", "canonical_name"),
    "natural-resources": ("cedar_uid", None),
    "nest": ("cedar_uid", None),
    "nonprofits": ("cedar_uid", "tribe_canonical_name"),
    "subcontracting": ("cedar_uid", None),
}


def identity():
    _ensure_out()
    con = duckdb.connect()
    con.execute("PRAGMA threads=4")
    parts = []
    for d, (uid, name) in UID_COLS.items():
        src = read_csv_expr(_path(d))
        nm = f'nullif(trim("{name}"), \'\')' if name else "NULL"
        parts.append(
            f"SELECT '{d}' AS ds, nullif(trim(\"{uid}\"), '') AS uid, {nm} AS nm, "
            f"count(*) AS n FROM {src} WHERE nullif(trim(\"{uid}\"), '') IS NOT NULL "
            f"GROUP BY 1,2,3")
    con.execute("CREATE TABLE u AS " + " UNION ALL ".join(parts))
    stats = con.execute(
        "SELECT ds, count(DISTINCT uid) uids, sum(n) rows_keyed FROM u GROUP BY 1 ORDER BY 1"
    ).fetchall()
    multi = con.execute(
        "SELECT uid, count(DISTINCT ds) nds FROM u GROUP BY 1 HAVING count(DISTINCT ds)>1"
    ).fetchall()
    disagree = con.execute(
        "SELECT uid, list(DISTINCT nm) AS nmlist, list(DISTINCT ds) AS dslist FROM u "
        "WHERE nm IS NOT NULL GROUP BY 1 HAVING count(DISTINCT nm)>1 ORDER BY 1"
    ).fetchall()
    shape = con.execute(
        "SELECT ds, count(*) FILTER (WHERE NOT regexp_matches(uid, '^[A-Z0-9]+-[A-Z0-9]+-[0-9]+$')) bad, "
        "count(*) tot FROM (SELECT DISTINCT ds, uid FROM u) GROUP BY 1 ORDER BY 1"
    ).fetchall()
    res = {
        "per_dataset": [{"dataset": a, "distinct_uid": b, "rows_keyed": int(c)} for a, b, c in stats],
        "uids_in_multiple_datasets": len(multi),
        "name_disagreements": [{"cedar_uid": a, "names": list(b), "datasets": list(c)} for a, b, c in disagree],
        "uid_shape_offenders": [{"dataset": a, "nonconforming_uids": b, "distinct_uids": c} for a, b, c in shape],
    }
    print(json.dumps({k: v for k, v in res.items() if k != "name_disagreements"}, indent=1))
    print(f"name disagreements: {len(res['name_disagreements'])}")
    with open(os.path.join(OUT, "identity.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    return res


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    only = sys.argv[2] if len(sys.argv) > 2 else None
    if cmd == "census":
        census()
    elif cmd == "profile":
        profile(only)
    elif cmd == "codebook":
        codebook()
    elif cmd == "identity":
        identity()
    elif cmd == "all":
        census(); codebook(); profile(); identity()
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
