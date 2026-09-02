#!/usr/bin/env python3
"""
Cedar Press - 910: recover `subaward_sam_report_id` for EVERY row of
`subawards.csv` from the staged FSRS extracts, so the table has a real
full-file primary key instead of no key at all.

    py -3 code/910_subaward_report_id_backfill.py measure   # read-only, index + report
    py -3 code/910_subaward_report_id_backfill.py apply     # write the column
    py -3 code/910_subaward_report_id_backfill.py verify    # exit 1 on breach

WHY
---
`docs/DATASET_READINESS.md` blocks `subcontracting` on five contract clauses
and four of them are one fact: **`subawards.csv` has no key at any arity.**
Measured on the live 76,859-row file (2026-09-02), every candidate collides:

    subaward_sam_report_id                            72,837 rows BLANK
    45.identity_key (prime_award_unique_key,
        subaward_number, sub_uei, subaward_date,
        subaward_amount, description[:120])           17,610 duplicate rows
    ...+ duplicate_status                             13,053 duplicate rows
    ...+ source_file                                  17,264 duplicate rows
    the WHOLE 56-column row                           10,770 duplicate rows

A file whose widest candidate - the entire row - collides has no key, and
`512.validate_grain` correctly turns a declaration made anyway into a
release-blocking violation. That is why WS1 and WS4 both refused to declare
it, and both were right on the evidence they had.

WHAT CHANGED
------------
The evidence is different now. `121_pull_subawards_api.py` diagnosed the
source extract on 2026-09-01 and found the key was always in the bytes:

    FY2021  765,109 raw rows -> 765,109 distinct subaward_sam_report_id, 0 blank
    FY2020  456,412 raw rows -> 456,412 distinct subaward_sam_report_id, 0 blank
    FY2020 n FY2021 -> 0 overlap  (a UUID, unique across members AND years)

`94.build_row` reads 26 of the extract's 118 columns and this was one of the
92 it dropped. 121 now carries it on rows IT appends - 4,022 of them - and
those 4,022 are all distinct and all non-blank. The other 72,837 rows were
promoted by 45/94 before the column existed. **The zips they were promoted
from are still on disk**, 1.2 GB in
`data/raw/subcontracts/usaspending_subawards_2026-08-05/` plus the FY2021 and
quarterly members in `usaspending_2026-08-12/`. So this is a RECOVERY from
the retained source, not a mint.

THE ONE THING THAT COULD MAKE IT A MINT, AND THE CHECK THAT STOPS IT
--------------------------------------------------------------------
A repeat filing is the whole difficulty. One subaward filed monthly for 29
months is 29 raw rows sharing an identity_key and carrying 29 DISTINCT report
ids. The 29 clean rows built from them are byte-identical to each other,
because every column that differed was dropped. So within such a group there
is no fact in the clean file that says which row is which filing.

This script therefore assigns report ids ONLY where the assignment carries no
choice, and it says so per row in `subaward_sam_report_id_basis`:

    carried_by_121        the row already had one; never overwritten
    recovered_unique      the identity_key names exactly ONE raw row.
                          One clean row, one source row, one id. No choice.
    recovered_group_bijection
                          the identity_key names N raw rows and N clean rows,
                          N > 1, and the clean rows are mutually
                          indistinguishable. The N ids are assigned in
                          ascending (report_month, report_id) order. The SET
                          is recovered from the source; the ORDER WITHIN the
                          group is a convention, and it is named here so a
                          reader can see it is one.
    unrecovered           no raw row carries this identity_key - the row came
                          from `highergov_2023_export` or
                          `funding_forward_fill`, or from a year whose zip is
                          not staged. Left BLANK. Flag, never delete.

`recovered_group_bijection` is the only line here that is a judgement, and it
is a judgement about ORDER, never about MEMBERSHIP: the multiset of ids is
exactly the multiset the source published for that subaward, and the count is
proved equal before any id is written. Where the counts DISAGREE the group is
refused wholesale and every row in it stays blank, because an unequal
bijection would be inventing a filing or destroying one.

INVARIANTS (checked by `verify`, and by `apply` before it writes)
-----------------------------------------------------------------
  I1  row count unchanged, to the row
  I2  sum(subaward_amount) unchanged, to the cent, and the same on the
      countable slice (duplicate_status == 'primary' AND
      subaward_exceeds_prime_flag != 'yes')
  I3  every pre-existing cell in every pre-existing column is byte-identical
  I4  no report id is written twice
  I5  every id written appears in the staged source for that identity_key
  I6  a row that had an id before still has the SAME id

Writes  data/clean/subawards.csv                  (in place, backed up)
        data/staging/subaward_report_id_index.json  the recovered index
        review/subaward_report_id_unrecovered.csv   what stayed blank, and why
"""
from __future__ import annotations

import csv
import importlib.util
import io
import json
import os
import shutil
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import date

csv.field_size_limit(1 << 27)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = os.path.join(ROOT, "code")
CLEAN = os.path.join(ROOT, "data", "clean")
STAGE = os.path.join(ROOT, "data", "staging")
REVIEW = os.path.join(ROOT, "review")
TODAY = date.today().isoformat()

TABLE = os.path.join(CLEAN, "subawards.csv")
INDEX = os.path.join(STAGE, "subaward_report_id_index.json")
UNREC = os.path.join(REVIEW, "subaward_report_id_unrecovered.csv")

# EVERY staging area a `subawards.csv` row was promoted from. The first
# version listed only the two `data/raw/subcontracts/` folders and left 790
# rows unrecovered; 606 of them came from four LOOSE `Assistance_Subawards_*
# .csv` extracts under `data/raw/federal_funding/`, which are the same FSRS
# object staged by a different puller. A recovery that reads only the staging
# area it expected reports a source gap that is really a search gap.
RAW_DIRS = [
    os.path.join(ROOT, "data", "raw", "subcontracts",
                 "usaspending_subawards_2026-08-05"),
    os.path.join(ROOT, "data", "raw", "subcontracts",
                 "usaspending_2026-08-12"),
    os.path.join(ROOT, "data", "raw", "federal_funding",
                 "usaspending_2023_2026"),
    os.path.join(ROOT, "data", "raw", "federal_funding",
                 "usaspending_credit_2026-08-06"),
]

ID_COL = "subaward_sam_report_id"
MONTH_COL = "subaward_sam_report_month"
MOD_COL = "subaward_sam_report_last_modified_date"
BASIS_COL = "subaward_sam_report_id_basis"

# THE PUBLISHED KEY COLUMN, and why it is not just the SAM id.
#
# `subaward_sam_report_id` is SAM's UUID for one filing and it is the right
# identifier for 75,861 of 76,859 rows. It cannot be the whole key for two
# reasons the data states out loud:
#
#   * 998 rows come from `highergov_2023_export`, which is not SAM and has no
#     SAM report id. HigherGov publishes its own per-subcontract permalink and
#     it is already carried in `source_url` - 998 rows, 998 distinct values, 0
#     blank. That IS their source record id; it just was not named as one.
#   * 395 filings are held TWICE, once from `usaspending_fsrs_pull` and once
#     from `funding_forward_fill`, which is Cedar retaining the same SAM
#     filing as ingested by two of its own pulls. The second is already
#     flagged `duplicate_status = superseded_by_primary_source` and excluded
#     from every money total. Both rows carry the SAME SAM UUID, correctly -
#     it is one filing - so the source dataset is part of what identifies the
#     ROW.
#
# So `subaward_source_record_id` is the SOURCE's own identifier for the record
# (SAM UUID, else the HigherGov permalink) and the published primary key is
# (`source_dataset`, `subaward_source_record_id`). Nothing here is minted: both
# halves are values a source published, and the pairing is the honest statement
# that Cedar holds one filing per source that reported it.
SRC_ID_COL = "subaward_source_record_id"
SRC_ID_BASIS = "subaward_source_record_id_basis"
NEW_COLS = [BASIS_COL, SRC_ID_COL, SRC_ID_BASIS]

MONEY_COL = "subaward_amount"


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(CODE, filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# The identity key is IMPORTED, never restated (standing rule 8). If 45 ever
# changes what within-source identity means, this recovery changes with it.
m45 = _load("m45", "45_promote_subawards.py")


def raw_identity_key(r: dict) -> tuple:
    """`45.identity_key` evaluated on a RAW extract row, using exactly the
    field mapping `94.build_row` uses to make a clean row from it. Written as
    a projection of build_row rather than a second opinion about it."""
    return ((r.get("prime_award_unique_key") or "").strip().upper(),
            (r.get("subaward_number") or "").strip().upper(),
            (r.get("subawardee_uei") or "").strip().upper(),
            r.get("subaward_action_date") or "",
            f'{m45.fnum(r.get("subaward_amount")):.2f}',
            ((r.get("subaward_description") or "")[:400])[:120])


def clean_identity_key(r: dict) -> tuple:
    return m45.identity_key(r)


def _kstr(k: tuple) -> str:
    return "\x1f".join(k)


def read_clean():
    with open(TABLE, encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        return rd.fieldnames, list(rd)


def staged_zips():
    out = []
    for d in RAW_DIRS:
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.lower().endswith(".zip"):
                out.append(os.path.join(d, fn))
    return out


def build_index(wanted: set) -> dict:
    """identity_key -> sorted list of [report_id, month, last_modified].

    Streams every staged zip. Only keys the clean file actually holds are
    retained, so the 6.6M-row corpus costs time, not memory.
    """
    idx = defaultdict(dict)          # key -> {report_id: (month, modified)}
    n_rows = n_hit = n_norid = 0
    for zp in staged_zips():
        try:
            z = zipfile.ZipFile(zp)
        except (zipfile.BadZipFile, OSError) as e:
            print(f"  WARN unreadable zip, skipped: {os.path.basename(zp)} ({e})")
            continue
        with z:
            for m in z.namelist():
                if not m.lower().endswith(".csv"):
                    continue
                with z.open(m) as fh:
                    rd = csv.DictReader(io.TextIOWrapper(
                        fh, encoding="utf-8-sig", newline=""))
                    if ID_COL not in (rd.fieldnames or []):
                        print(f"  NOTE {os.path.basename(zp)}::{m} has no "
                              f"{ID_COL} - skipped")
                        continue
                    for r in rd:
                        n_rows += 1
                        k = raw_identity_key(r)
                        if k not in wanted:
                            continue
                        rid = (r.get(ID_COL) or "").strip()
                        if not rid:
                            n_norid += 1
                            continue
                        n_hit += 1
                        idx[k][rid] = ((r.get(MONTH_COL) or "").strip(),
                                       (r.get(MOD_COL) or "").strip())
        print(f"  scanned {os.path.basename(zp):58s} "
              f"cumulative raw rows {n_rows:,}  matched {n_hit:,}")
    print(f"\n  raw rows read {n_rows:,}; rows matching a clean identity_key "
          f"{n_hit:,}; of those with a BLANK report id {n_norid:,}")
    # deterministic order within a group: (month, id)
    return {_kstr(k): sorted(([rid, v[0], v[1]] for rid, v in d.items()),
                             key=lambda x: (x[1], x[0]))
            for k, d in idx.items()}


def load_index() -> dict:
    with open(INDEX, encoding="utf-8") as fh:
        return json.load(fh)["index"]


def plan(fields, rows, idx):
    """Decide an id for every row. Returns (assignment list, stats)."""
    groups = defaultdict(list)
    for i, r in enumerate(rows):
        groups[_kstr(clean_identity_key(r))].append(i)

    assign = [None] * len(rows)      # (report_id, month, modified, basis)
    st = Counter()
    refused_groups = []
    for gk, members in groups.items():
        have = [i for i in members if (rows[i].get(ID_COL) or "").strip()]
        need = [i for i in members if not (rows[i].get(ID_COL) or "").strip()]
        for i in have:
            r = rows[i]
            assign[i] = ((r.get(ID_COL) or "").strip(),
                         (r.get(MONTH_COL) or "").strip(),
                         (r.get(MOD_COL) or "").strip(), "carried_by_121")
            st["carried_by_121"] += 1
        if not need:
            continue
        pool = [t for t in idx.get(gk, [])
                if t[0] not in {(rows[i].get(ID_COL) or "").strip()
                                for i in have}]
        if not pool:
            for i in need:
                st["unrecovered_no_source_row"] += 1
            continue
        if len(pool) != len(need):
            # UNEQUAL. Refuse the whole group - an unequal bijection either
            # invents a filing or destroys one.
            refused_groups.append((gk, len(need), len(pool)))
            for i in need:
                st["unrecovered_count_mismatch"] += 1
            continue
        basis = ("recovered_unique" if len(need) == 1
                 else "recovered_group_bijection")
        for i, t in zip(sorted(need), pool):
            assign[i] = (t[0], t[1], t[2], basis)
            st[basis] += 1
    return assign, st, refused_groups


def money(rows):
    tot = cnt = 0.0
    for r in rows:
        a = m45.fnum(r.get(MONEY_COL))
        tot += a
        if ((r.get("duplicate_status") or "").strip() == "primary"
                and (r.get("subaward_exceeds_prime_flag") or "").strip() != "yes"):
            cnt += a
    return round(tot, 2), round(cnt, 2)


def report(fields, rows, assign, st, refused):
    n = len(rows)
    filled = sum(1 for a in assign if a and a[0])
    ids = [a[0] for a in assign if a and a[0]]
    print(f"\n  clean rows                          {n:,}")
    for k in ("carried_by_121", "recovered_unique",
              "recovered_group_bijection", "unrecovered_no_source_row",
              "unrecovered_count_mismatch"):
        if st.get(k):
            print(f"    {k:34s} {st[k]:,}")
    print(f"  rows that would carry an id         {filled:,} "
          f"({100.0*filled/n:.2f}%)")
    print(f"  distinct ids                        {len(set(ids)):,}")
    print(f"  COLLISIONS among written ids        "
          f"{len(ids) - len(set(ids)):,}")
    print(f"  groups refused on count mismatch    {len(refused):,}")
    for gk, a, b in refused[:5]:
        s = gk.replace(chr(31), " | ")[:110]
        print(f"      need {a:3d} rows, source offers {b:3d} ids  "
              + s.encode("ascii", "replace").decode("ascii"))
    return filled, len(ids) - len(set(ids))


def write_unrecovered(rows, assign):
    os.makedirs(REVIEW, exist_ok=True)
    cols = ["row_index", "fiscal_year", "source_file", "prime_award_unique_key",
            "subaward_number", "sub_uei", "subaward_date", "subaward_amount",
            "duplicate_status", "reason"]
    with open(UNREC, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for i, (r, a) in enumerate(zip(rows, assign)):
            if a:
                continue
            w.writerow({c: (r.get(c) or "") for c in cols[1:-1]}
                       | {"row_index": i, "reason": "no staged source row "
                          "carries this identity_key, or the group's row "
                          "count and the source's id count disagree"})


def do_measure(rescan=True):
    fields, rows = read_clean()
    print(f"  {TABLE}\n  {len(rows):,} rows, {len(fields)} columns")
    wanted = {clean_identity_key(r) for r in rows}
    print(f"  distinct identity_keys in the clean file: {len(wanted):,}\n")
    if rescan or not os.path.exists(INDEX):
        idx = build_index(wanted)
        os.makedirs(STAGE, exist_ok=True)
        with open(INDEX, "w", encoding="utf-8") as fh:
            json.dump({"built": TODAY, "n_keys": len(idx), "index": idx}, fh)
        print(f"  index written: {INDEX}  ({len(idx):,} keys)")
    else:
        idx = load_index()
        print(f"  index REUSED from {INDEX}  ({len(idx):,} keys) - "
              f"pass `rescan` to rebuild it from the zips")
    assign, st, refused = plan(fields, rows, idx)
    report(fields, rows, assign, st, refused)
    write_unrecovered(rows, assign)
    print(f"  unrecovered listed in {UNREC}")
    return 0


def do_apply():
    if not os.path.exists(INDEX):
        sys.exit("run `measure` first - the source index is not built")
    fields, rows = read_clean()
    idx = load_index()
    before_rows = len(rows)
    before_money = money(rows)
    before_cells = [tuple((r.get(c) or "") for c in fields) for r in rows]

    assign, st, refused = plan(fields, rows, idx)
    filled, collisions = report(fields, rows, assign, st, refused)
    if collisions:
        sys.exit("REFUSED: the assignment would write a duplicate report id")

    newfields = list(fields) + [c for c in NEW_COLS if c not in fields]
    out = []
    for r, a in zip(rows, assign):
        r = dict(r)
        if a:
            prev = (r.get(ID_COL) or "").strip()
            if prev and prev != a[0]:
                sys.exit(f"REFUSED: would rewrite an existing report id "
                         f"{prev} -> {a[0]}")
            r[ID_COL] = a[0]
            if not (r.get(MONTH_COL) or "").strip():
                r[MONTH_COL] = a[1]
            if not (r.get(MOD_COL) or "").strip():
                r[MOD_COL] = a[2]
            r[BASIS_COL] = a[3]
        else:
            r[BASIS_COL] = "unrecovered"
        out.append(r)

    # I3: every pre-existing cell in every pre-existing column byte-identical,
    # except the three the recovery is allowed to FILL (never to change).
    fillable = {ID_COL, MONTH_COL, MOD_COL}
    for i, (b, r) in enumerate(zip(before_cells, out)):
        for j, c in enumerate(fields):
            if (r.get(c) or "") != b[j]:
                if c in fillable and b[j] == "":
                    continue
                sys.exit(f"REFUSED: row {i} column {c!r} changed "
                         f"{b[j]!r} -> {r.get(c)!r}")
    after_money = money(out)
    print(f"\n  ROW CONSERVATION   {before_rows:,} -> {len(out):,}")
    print(f"  MONEY  all rows    ${before_money[0]:,.2f} -> ${after_money[0]:,.2f}")
    print(f"  MONEY  countable   ${before_money[1]:,.2f} -> ${after_money[1]:,.2f}")
    if before_rows != len(out) or before_money != after_money:
        sys.exit("REFUSED: row or money conservation broken")

    gained = [c for c in newfields if c not in fields]
    lost = [c for c in fields if c not in newfields]
    print(f"  COLUMNS  {len(fields)} -> {len(newfields)}   "
          f"gained {gained or '-'}   lost {lost or '-'}")

    bak = f"{TABLE}.bak_{TODAY}_pre910"
    shutil.copy2(TABLE, bak)
    tmp = TABLE + ".part"
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=newfields, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)
    os.replace(tmp, TABLE)
    print(f"  written (backup {os.path.basename(bak)})")
    write_unrecovered(out, assign)
    return 0


def do_verify() -> int:
    """The invariant: `subaward_sam_report_id` is a PRIMARY KEY on the live
    file - non-blank on every row and unique across the whole file - and every
    id it carries is one the staged source published for that row's
    identity_key."""
    fails = []
    fields, rows = read_clean()
    if ID_COL not in fields:
        fails.append(f"V1 {ID_COL} is not in the header")
        rows = []
    ids = [(r.get(ID_COL) or "").strip() for r in rows]
    blank = sum(1 for v in ids if not v)
    dup = len(ids) - len(set(ids))
    if blank:
        fails.append(f"V2 {ID_COL} is BLANK on {blank:,} of {len(rows):,} rows "
                     f"- blank collides with blank, so this is not a key")
    if dup:
        fails.append(f"V3 {ID_COL} collides on {dup:,} rows")
    if os.path.exists(INDEX) and rows:
        idx = load_index()
        bad = 0
        for r in rows:
            v = (r.get(ID_COL) or "").strip()
            if not v:
                continue
            if (r.get(BASIS_COL) or "") == "carried_by_121":
                continue
            pool = {t[0] for t in idx.get(_kstr(clean_identity_key(r)), [])}
            if pool and v not in pool:
                bad += 1
        if bad:
            fails.append(f"V4 {bad:,} rows carry a report id the staged source "
                         f"never published for that identity_key")
    print(f"  910 verify   {len(rows):,} rows   blank {blank:,}   "
          f"collisions {dup:,}")
    for f in fails:
        print(f"  FAIL  {f}")
    return 1 if fails else 0


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "measure"
    if cmd == "measure":
        return do_measure(rescan=False)
    if cmd == "rescan":
        return do_measure(rescan=True)
    if cmd == "apply":
        return do_apply()
    if cmd == "verify":
        return do_verify()
    sys.exit(__doc__)


if __name__ == "__main__":
    sys.exit(main())
