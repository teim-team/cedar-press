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


def staged_members():
    """(label, opener) over every staged FSRS extract - zipped or loose."""
    out = []
    for d in RAW_DIRS:
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            p = os.path.join(d, fn)
            low = fn.lower()
            if low.endswith(".zip"):
                out.append(("zip", p))
            elif low.endswith(".csv") and "subaward" in low:
                out.append(("csv", p))
    return out


def build_index(wanted: set) -> dict:
    """identity_key -> sorted list of [report_id, month, last_modified].

    Streams every staged extract. Only keys the clean file actually holds are
    retained, so the 8.5M-row corpus costs time, not memory.
    """
    idx = defaultdict(dict)          # key -> {report_id: (month, modified)}
    counters = [0, 0, 0]             # rows, matched, matched-with-blank-id

    def consume(rd, label):
        if ID_COL not in (rd.fieldnames or []):
            print(f"  NOTE {label} has no {ID_COL} - skipped")
            return
        for r in rd:
            counters[0] += 1
            k = raw_identity_key(r)
            if k not in wanted:
                continue
            rid = (r.get(ID_COL) or "").strip()
            if not rid:
                counters[2] += 1
                continue
            counters[1] += 1
            idx[k][rid] = ((r.get(MONTH_COL) or "").strip(),
                           (r.get(MOD_COL) or "").strip())

    for kind, p in staged_members():
        base = os.path.basename(p)
        if kind == "zip":
            try:
                z = zipfile.ZipFile(p)
            except (zipfile.BadZipFile, OSError) as e:
                print(f"  WARN unreadable zip, skipped: {base} ({e})")
                continue
            with z:
                for m in z.namelist():
                    if not m.lower().endswith(".csv"):
                        continue
                    with z.open(m) as fh:
                        consume(csv.DictReader(io.TextIOWrapper(
                            fh, encoding="utf-8-sig", newline="")),
                            f"{base}::{m}")
        else:
            with open(p, encoding="utf-8-sig", newline="") as fh:
                consume(csv.DictReader(fh), base)
        print(f"  scanned {base:58s} cumulative raw rows {counters[0]:,}  "
              f"matched {counters[1]:,}")
    n_rows, n_hit, n_norid = counters
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
    """Decide an id for every row. Returns (assignment list, stats).

    THE POOL IS PER identity_key; THE ALLOCATION IS PER source_dataset.
    Both halves were learned by getting one of them wrong.

    Allocating one pool across the whole identity_key group refused 694 rows
    on a count mismatch. 790 of those were 395 filings Cedar holds TWICE, once
    from `usaspending_fsrs_pull` and once from `funding_forward_fill` - one
    filing, ingested by two Cedar pulls, and the source published exactly one
    id for it. Both rows must carry the SAME SAM UUID, because it IS the same
    filing; what separates the two ROWS is the source that reported them, and
    that is why `source_dataset` is half the published key.

    THE DIRECTION OF THE INEQUALITY IS THE WHOLE RULE.
      M rows, N source filings, M <  N   Cedar retains a SUBSET of the source's
                                         filings. Assign M distinct real ids,
                                         injectively, in (month, id) order.
                                         Nothing is invented; which subset was
                                         retained is simply not recorded, and
                                         the N filings this arises from are
                                         byte-identical in the source anyway.
      M == N                             a bijection.
      M >  N                             REFUSED, always. Cedar would have
                                         more rows than the source published
                                         filings, so some row could only be
                                         given an id that is not its own. That
                                         is the fabrication this refuses; it
                                         fires on 0 partitions today and the
                                         synthetic test in `selftest` proves
                                         it still fires.
    """
    by_key = defaultdict(list)
    for i, r in enumerate(rows):
        by_key[_kstr(clean_identity_key(r))].append(i)

    assign = [None] * len(rows)      # (report_id, month, modified, basis)
    st = Counter()
    refused = []
    for gk, members in by_key.items():
        have = [i for i in members if (rows[i].get(ID_COL) or "").strip()]
        for i in have:
            r = rows[i]
            # AN EXISTING BASIS IS A FACT ABOUT HOW THIS ROW GOT ITS ID, AND A
            # RE-RUN MUST NOT OVERWRITE IT.  (2026-09-02)
            #
            # `carried_by_121` means "121 append supplied this id". After a
            # first `apply`, EVERY row has an id, so on the second run every
            # row lands in `have` and would be re-labelled `carried_by_121` -
            # including the 71,839 whose id this script itself recovered. That
            # is not a re-classification, it is a false provenance claim, and
            # the I3 guard below correctly refused the whole run because of it
            # ("row 0 column 'subaward_sam_report_id_basis' changed
            # 'recovered_unique' -> 'carried_by_121'").
            #
            # The consequence was worse than a refusal: after `121 append`
            # added 10,318 rows, `apply` could not run AT ALL, so those rows
            # kept a blank `subaward_sam_report_id_basis` and a blank
            # `subaward_source_record_id` - which is half the declared primary
            # key. The table went from 0 rows with a blank key to 10,318.
            #
            # Preserving the recorded basis makes `apply` idempotent, which is
            # what the fold-in cycle needs, and it keeps the true one.
            prior = (r.get(BASIS_COL) or "").strip()
            assign[i] = ((r.get(ID_COL) or "").strip(),
                         (r.get(MONTH_COL) or "").strip(),
                         (r.get(MOD_COL) or "").strip(),
                         prior or "carried_by_121")
            st[prior or "carried_by_121"] += 1
        claimed = {(rows[i].get(ID_COL) or "").strip() for i in have}
        free = [t for t in idx.get(gk, []) if t[0] not in claimed]

        per_src = defaultdict(list)
        for i in members:
            if i not in set(have):
                per_src[(rows[i].get("source_dataset") or "").strip()].append(i)
        for src in sorted(per_src):
            need = sorted(per_src[src])
            if not free:
                for i in need:
                    st["unrecovered_no_source_row"] += 1
                continue
            if len(need) > len(free):
                refused.append((gk, src, len(need), len(free)))
                for i in need:
                    st["unrecovered_more_rows_than_source_filings"] += 1
                continue
            basis = ("recovered_unique" if len(need) == 1 == len(free)
                     else "recovered_group_bijection" if len(need) == len(free)
                     else "recovered_group_injection")
            for i, t in zip(need, free):
                assign[i] = (t[0], t[1], t[2], basis)
                st[basis] += 1
    return assign, st, refused


def source_record_id(r, assigned_id):
    """The SOURCE's own identifier for this record, and what names it.

    Never minted. The SAM UUID where the source is SAM/FSRS; the HigherGov
    per-subcontract permalink - already carried in `source_url`, 998 rows, 998
    distinct values, 0 blank - where the source is HigherGov.
    """
    if assigned_id:
        return assigned_id, "sam_subaward_report_id"
    if (r.get("source_dataset") or "").strip() == "highergov_2023_export":
        u = (r.get("source_url") or "").strip()
        if u:
            return u, "highergov_subcontract_permalink"
    return "", "unrecovered"


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
    ids = [a[0] for a in assign if a and a[0]]
    print(f"\n  clean rows                          {n:,}")
    for k in ("carried_by_121", "recovered_unique",
              "recovered_group_bijection", "recovered_group_injection",
              "unrecovered_no_source_row",
              "unrecovered_more_rows_than_source_filings"):
        if st.get(k):
            print(f"    {k:44s} {st[k]:,}")
    print(f"  rows carrying a SAM report id       {len(ids):,} "
          f"({100.0*len(ids)/n:.2f}%)")
    print(f"    distinct SAM report ids           {len(set(ids)):,}")
    print(f"    repeats (one filing, two Cedar sources) "
          f"{len(ids) - len(set(ids)):,}")

    # the PUBLISHED key: (source_dataset, subaward_source_record_id)
    pk, blank = Counter(), 0
    by_basis = Counter()
    for r, a in zip(rows, assign):
        v, b = source_record_id(r, a[0] if a else "")
        by_basis[b] += 1
        if not v:
            blank += 1
            continue
        pk[((r.get("source_dataset") or "").strip(), v)] += 1
    dup = sum(c - 1 for c in pk.values() if c > 1)
    print(f"  PRIMARY KEY (source_dataset, {SRC_ID_COL})")
    for b, c in by_basis.most_common():
        print(f"    basis {b:36s} {c:,}")
    print(f"    BLANK on                          {blank:,} rows")
    print(f"    COLLISIONS                        {dup:,} rows")
    print(f"  partitions refused (rows > source filings) {len(refused):,}")
    for gk, src, a, b in refused[:5]:
        s = f"{src} | {gk.replace(chr(31), ' | ')}"[:110]
        print(f"      need {a:3d} rows, source offers {b:3d} ids  "
              + s.encode("ascii", "replace").decode("ascii"))
    return blank, dup


def write_unrecovered(rows, assign):
    os.makedirs(REVIEW, exist_ok=True)
    cols = ["row_index", "fiscal_year", "source_dataset", "source_file",
            "prime_award_unique_key", "subaward_number", "sub_uei",
            "subaward_date", "subaward_amount", "duplicate_status", "reason"]
    n = 0
    with open(UNREC, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for i, (r, a) in enumerate(zip(rows, assign)):
            v, _ = source_record_id(r, a[0] if a else "")
            if v:
                continue
            n += 1
            w.writerow({c: (r.get(c) or "") for c in cols[1:-1]}
                       | {"row_index": i, "reason": "no staged source row "
                          "carries this identity_key, and the source is not "
                          "one that publishes its own record id"})
    return n


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
    n = write_unrecovered(rows, assign)
    print(f"  {n:,} unrecovered rows listed in {UNREC}")
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
    blank, collisions = report(fields, rows, assign, st, refused)
    if collisions:
        sys.exit(f"REFUSED: the published key would collide on "
                 f"{collisions:,} rows")

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
        v, b = source_record_id(r, a[0] if a else "")
        r[SRC_ID_COL], r[SRC_ID_BASIS] = v, b
        out.append(r)

    # I3: every pre-existing cell in every pre-existing column byte-identical,
    # except the three the recovery is allowed to FILL (never to change).
    # The three id columns, PLUS the three columns this script owns outright.
    # Extended 2026-09-02. `fillable` permits a change only where the old cell
    # was EMPTY (`b[j] == ""` below), so widening it cannot mask a real edit -
    # a value changing to a different value is still refused, which is exactly
    # what caught the `recovered_unique -> carried_by_121` regression above.
    #
    # It had to be widened because `121 append` adds rows with these three
    # BLANK, and the guard as written refused the fill: after the 2026-09-02
    # fold-in, 10,318 of 87,177 rows carried a blank `subaward_source_record_id`
    # - half the declared primary key - and `apply` could not fix them because
    # fixing them was the thing being refused. A guard that blocks the repair
    # of the state it is meant to protect is inverted.
    fillable = {ID_COL, MONTH_COL, MOD_COL, BASIS_COL, SRC_ID_COL, SRC_ID_BASIS}
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
    """The invariant: (`source_dataset`, `subaward_source_record_id`) is a
    PRIMARY KEY on the live file - non-blank on every row, unique across the
    whole file - and every SAM id it carries is one the staged source actually
    published for that row's identity_key."""
    fails = []
    fields, rows = read_clean()
    for c in (ID_COL, SRC_ID_COL, SRC_ID_BASIS, "source_dataset"):
        if c not in fields:
            fails.append(f"V1 {c} is not in the header")
            rows = []
    key = [((r.get("source_dataset") or "").strip(),
            (r.get(SRC_ID_COL) or "").strip()) for r in rows]
    blank = sum(1 for _, v in key if not v)
    dup = len(key) - len(set(key))
    if blank:
        fails.append(f"V2 {SRC_ID_COL} is BLANK on {blank:,} of {len(rows):,} "
                     f"rows - blank collides with blank, so this is not a key")
    if dup:
        fails.append(f"V3 (source_dataset, {SRC_ID_COL}) collides on "
                     f"{dup:,} rows")
    if os.path.exists(INDEX) and rows:
        idx = load_index()
        bad = 0
        for r in rows:
            v = (r.get(ID_COL) or "").strip()
            if not v or (r.get(BASIS_COL) or "") == "carried_by_121":
                continue
            pool = {t[0] for t in idx.get(_kstr(clean_identity_key(r)), [])}
            if pool and v not in pool:
                bad += 1
        if bad:
            fails.append(f"V4 {bad:,} rows carry a report id the staged source "
                         f"never published for that identity_key")
    print(f"  910 verify   {len(rows):,} rows   key blank {blank:,}   "
          f"key collisions {dup:,}")
    for f in fails:
        print(f"  FAIL  {f}")
    return 1 if fails else 0


def do_selftest() -> int:
    """PROVE THE REFUSAL FIRES, on a synthetic violation.

    Two rows sharing one identity_key and one source_dataset, against a source
    pool holding ONE filing. That is the M > N case: giving both rows an id
    would put the same real id on two rows, or invent one. The planner must
    refuse both and assign neither.
    """
    ok = True
    base = {"prime_award_unique_key": "CONT_AWD_SELFTEST", "subaward_number": "1",
            "sub_uei": "ZZZZZZZZZZZZ", "subaward_date": "2020-01-01",
            "subaward_amount": "100.00", "description": "SELFTEST",
            "source_dataset": "usaspending_fsrs_pull", "source_url": "",
            ID_COL: "", MONTH_COL: "", MOD_COL: "",
            "duplicate_status": "primary", "subaward_exceeds_prime_flag": ""}
    rows = [dict(base), dict(base)]
    gk = _kstr(clean_identity_key(rows[0]))
    idx = {gk: [["THE-ONE-REAL-ID", "2020-02", "2020-02-01"]]}
    assign, st, refused = plan(list(base), rows, idx)
    if not refused or st.get("unrecovered_more_rows_than_source_filings") != 2:
        print("  FAIL  S1 M>N was NOT refused - the guard does not fire")
        ok = False
    else:
        print(f"  S1 M>N refused as designed: {len(refused)} partition, "
              f"2 rows left unassigned")
    if any(a for a in assign):
        print("  FAIL  S2 a refused partition still got an id assigned")
        ok = False

    # and the control: one row, one filing -> assigned.
    rows2 = [dict(base)]
    assign2, st2, refused2 = plan(list(base), rows2, idx)
    if refused2 or assign2[0][0] != "THE-ONE-REAL-ID":
        print("  FAIL  S3 the guard is over-firing - a clean 1:1 was refused")
        ok = False
    else:
        print("  S3 control passes: a 1:1 partition is still recovered")

    # and the key derivation for a HigherGov row, which has no SAM id at all
    hg = dict(base, source_dataset="highergov_2023_export",
              source_url="https://www.highergov.com/subcontract/SELFTEST")
    v, b = source_record_id(hg, "")
    if b != "highergov_subcontract_permalink" or not v:
        print("  FAIL  S4 HigherGov rows do not fall back to their permalink")
        ok = False
    else:
        print("  S4 HigherGov permalink is used as the source record id")
    print("  910 selftest " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


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
    if cmd == "selftest":
        return do_selftest()
    sys.exit(__doc__)


if __name__ == "__main__":
    sys.exit(main())
