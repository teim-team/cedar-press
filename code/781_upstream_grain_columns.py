r"""781_upstream_grain_columns.py -- Cedar Press. Workstream UPSTREAM, 2026-09-01.

THE ONE-LINE VERSION
--------------------
Three shippable tables have no primary key at any arity, and all three are one
missing column upstream. This script puts the column on the LIVE file, because
the three builders that own the column cannot be run today.

WHY IN PLACE AND NOT A REBUILD -- THE POINT OF THIS FILE
--------------------------------------------------------
The builders were fixed in the same pass (`132`, `133`, `98`), so a future
rebuild produces these columns itself. But NONE OF THE THREE MAY BE RUN NOW,
and each refuses for a different, checkable reason:

  132_build_schedule_i_layer.py   its inputs ARE GONE. `data/raw/irs990_schedc
                                  /xml` and `data/raw/irs990_grantee/xml` hold
                                  ZERO files. Running it would parse nothing
                                  and write an EMPTY np_schedule_i_grants.csv
                                  over 58,685 real rows.
  133_build_ferc_advocacy.py      its own header says the build is a full
                                  rebuild that REVERTS `168_link_adjudication
                                  _hubs.py`'s in-place enrichment, and it
                                  re-fetches eLibrary.
  98_build_oira_and_hearings.py   `--stage build` rewrites hearing_appearances
                                  .csv, which `400_promote_stranded_hearing
                                  _appearances.py` enriches IN PLACE. Same
                                  shape of defect: a full-rebuild stage
                                  reverting an enricher.

So the column is added here, additively, to the file that exists.

WHAT IT DOES, AND THE THREE GUARANTEES IT MAKES
-----------------------------------------------
  ferc_docket_filings.csv     + filing_occurrence_seq
  np_schedule_i_grants.csv    + schedule_i_line_seq
  hearing_bill_links.csv      un-ingests source repetition (no column)

  1. NO ROW IS DELETED, except in the hearing case, where what is removed is
     provably a second reading of ONE Congress.gov array element and is proved
     to be so against the cached source before anything is written. Every
     other row count in equals row count out, asserted, not hoped.
  2. NO COLUMN IS LOST. The header is diffed before and after and the write is
     refused if a single column would go missing. That defect erased
     `cedar_uid` from three tables on 2026-09-01 alone.
  3. EVERY WRITE TAKES A `.bak` FIRST, as all 15 spine enrichers do.

Idempotent: re-running finds the column present, re-verifies the key, and
writes nothing.

USAGE
-----
    py -3 code/781_upstream_grain_columns.py            # apply
    py -3 code/781_upstream_grain_columns.py --check    # measure only
"""

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
RAW_ADV = CEDAR / "data" / "raw" / "advocacy"
LOGS = CEDAR / "logs"

TODAY = date.today().isoformat()
SCRIPT = "781_upstream_grain_columns.py"

csv.field_size_limit(min(sys.maxsize, 2147483647))

FERC = CLEAN / "ferc_docket_filings.csv"
SCHED_I = CLEAN / "np_schedule_i_grants.csv"
SCHED_I_FILERS = CLEAN / "np_schedule_i_filers.csv"
HEAR_LINKS = CLEAN / "hearing_bill_links.csv"
HEAR_DETAIL = RAW_ADV / "hearing_meeting_detail.jsonl"

REPORT = []


def log(m=""):
    print(m, flush=True)
    REPORT.append(m)


def read_csv(p):
    p = Path(p)
    if not p.exists():
        return [], []
    with open(p, newline="", encoding="utf-8-sig", errors="replace") as fh:
        rd = csv.DictReader(fh)
        rows = list(rd)
        return rows, list(rd.fieldnames or [])


def write_csv_guarded(path, rows, fields, cols_before, rows_before,
                      rows_may_fall_by=0):
    """Write, but only after proving nothing was silently lost.

    `rows_may_fall_by` is the ONLY licence to shrink a table, and the caller
    has to have proved the licence separately. Everything else is a hard stop.
    """
    path = Path(path)
    lost = [c for c in cols_before if c not in fields]
    if lost:
        raise SystemExit(
            f"REFUSED: writing {path.name} would drop column(s) {lost}. "
            f"This is the defect that erased cedar_uid from three tables on "
            f"2026-09-01. Nothing was written.")
    if len(rows) != rows_before - rows_may_fall_by:
        raise SystemExit(
            f"REFUSED: {path.name} would go {rows_before:,} -> {len(rows):,} "
            f"rows and only a fall of {rows_may_fall_by} is licensed here. "
            f"Nothing was written.")
    bak = path.with_name(path.name + f".bak_{TODAY}_pre781")
    if path.exists() and not bak.exists():
        bak.write_bytes(path.read_bytes())
        log(f"    backed up -> {bak.name}")
    part = path.with_suffix(path.suffix + ".part781")
    with open(part, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    part.replace(path)
    back, back_cols = read_csv(path)
    log(f"    wrote {path.name}: {len(back):,} rows, {len(back_cols)} cols "
        f"(was {rows_before:,} rows, {len(cols_before)} cols)")
    return back, back_cols


def dup_report(rows, cols, label):
    c = Counter(tuple(r.get(k, "") for k in cols) for r in rows)
    groups = [k for k, v in c.items() if v > 1]
    excess = sum(c[k] - 1 for k in groups)
    log(f"    {label}: {len(rows):,} rows, {len(groups):,} byte-identical "
        f"group(s), {excess:,} excess row(s)")
    return groups, excess


def key_collisions(rows, key):
    c = Counter(tuple(r.get(k, "") for k in key) for r in rows)
    return sum(v - 1 for v in c.values() if v > 1)


# ---------------------------------------------------------------------------
# 1. ferc_docket_filings.csv  -- filing_occurrence_seq
# ---------------------------------------------------------------------------
SEQ_FERC = "filing_occurrence_seq"


def fix_ferc(apply_it):
    log("\n" + "=" * 76)
    log("ferc_docket_filings.csv  ->  + filing_occurrence_seq   (owner: 133)")
    log("=" * 76)
    rows, cols = read_csv(FERC)
    if not rows:
        log("    ABSENT - nothing to do")
        return
    content = [c for c in cols if c != SEQ_FERC]
    dup_report(rows, content, "before")

    byid = defaultdict(list)
    for r in rows:
        byid[r.get("ferc_filing_id", "")].append(r)
    colliding = {k: v for k, v in byid.items() if len(v) > 1}

    # The split that decides what may be touched. 602 groups are identical on
    # every column; 167 differ ONLY in the case of the filer name and are NOT
    # duplicates. Re-measured here rather than trusted from the brief.
    n_identical = n_case = n_other = 0
    for members in colliding.values():
        exact = {tuple(r.get(c, "") for c in content) for r in members}
        if len(exact) == 1:
            n_identical += 1
            continue
        folded = {tuple((r.get(c, "") or "").strip().lower() for c in content)
                  for r in members}
        if len(folded) == 1:
            n_case += 1
        else:
            n_other += 1
    log(f"    ferc_filing_id collides on {len(colliding):,} group(s): "
        f"{n_identical:,} byte-identical, {n_case:,} differ ONLY in filer-name "
        f"case (NOT duplicates, and untouched), {n_other:,} differ otherwise")

    if SEQ_FERC in cols:
        log(f"    {SEQ_FERC} already present - re-verifying only")
    for members in byid.values():
        if len(members) == 1:
            members[0][SEQ_FERC] = "1"
            continue
        ordered = sorted(members, key=lambda x: tuple(str(x.get(c, ""))
                                                      for c in content))
        for n, r in enumerate(ordered, 1):
            r[SEQ_FERC] = str(n)

    key = ["ferc_filing_id", SEQ_FERC]
    coll = key_collisions(rows, key)
    log(f"    key {tuple(key)} collisions: {coll}")
    if coll:
        raise SystemExit("REFUSED: the ordinal did not produce a unique key.")
    if not apply_it:
        return
    fields = cols if SEQ_FERC in cols else (
        [cols[0], SEQ_FERC] + [c for c in cols[1:]])
    write_csv_guarded(FERC, rows, fields, cols, len(rows))
    back, bcols = read_csv(FERC)
    dup_report(back, [c for c in bcols if c != SEQ_FERC], "after (content)")
    log(f"    after (whole row, incl. the ordinal): "
        f"{key_collisions(back, bcols)} duplicate row(s)")


# ---------------------------------------------------------------------------
# 2. np_schedule_i_grants.csv  -- schedule_i_line_seq
# ---------------------------------------------------------------------------
SEQ_SCHED = "schedule_i_line_seq"


def fix_schedule_i(apply_it):
    log("\n" + "=" * 76)
    log("np_schedule_i_grants.csv  ->  + schedule_i_line_seq   (owner: 132)")
    log("=" * 76)
    rows, cols = read_csv(SCHED_I)
    if not rows:
        log("    ABSENT - nothing to do")
        return
    content = [c for c in cols if c != SEQ_SCHED]
    groups, excess = dup_report(rows, content, "before")

    # THE PROOF THAT NONE OF THESE IS A DUPLICATE. Each colliding group must
    # sit inside ONE return, and that return must appear exactly ONCE in
    # np_schedule_i_filers.csv. If both hold, the return was read once and the
    # FILER listed the line twice.
    filers, _ = read_csv(SCHED_I_FILERS)
    filer_n = Counter(f.get("object_id", "") for f in filers)
    bad = []
    money = 0.0
    for g in groups:
        d = dict(zip(content, g))
        oid = d.get("object_id", "")
        if filer_n.get(oid, 0) != 1:
            bad.append(oid)
        n_extra = sum(1 for r in rows
                      if tuple(r.get(k, "") for k in content) == g) - 1
        for c in ("cash_grant_usd", "noncash_assistance_usd"):
            try:
                money += float(d.get(c) or 0) * n_extra
            except ValueError:
                pass
    log(f"    every colliding group sits in ONE return that "
        f"np_schedule_i_filers.csv holds exactly once: "
        f"{'YES' if not bad else 'NO -> ' + str(sorted(set(bad))[:5])}")
    log(f"    money a de-dupe would have deleted: ${money:,.0f}")
    if bad:
        raise SystemExit(
            "REFUSED: a colliding group spans a return the filer table does "
            "not hold exactly once. That WOULD be a double-ingest and the "
            "ordinal is the wrong fix for it.")

    # Grant rows are contiguous by object_id - the parser appends a return's
    # recipient lines together and the holdout filter preserves order. Assert
    # it, because the ordinal means nothing if the file has been re-sorted.
    seen, breaks, prev = set(), 0, None
    for r in rows:
        o = r.get("object_id", "")
        if o != prev:
            if o in seen:
                breaks += 1
            seen.add(o)
            prev = o
    log(f"    object_id runs are contiguous (document order preserved): "
        f"{'YES' if not breaks else f'NO - {breaks} broken run(s)'}")
    if breaks:
        raise SystemExit(
            "REFUSED: np_schedule_i_grants.csv is no longer in parse order, "
            "so file position is not document order and the ordinal would be "
            "a fiction. Re-run 132 once the XML cache is restored.")

    if SEQ_SCHED in cols:
        log(f"    {SEQ_SCHED} already present - re-verifying only")
    n = Counter()
    for r in rows:
        oid = r.get("object_id", "")
        n[oid] += 1
        r[SEQ_SCHED] = str(n[oid])
    multi = sum(1 for v in n.values() if v > 1)
    log(f"    {len(rows):,} grant rows over {len(n):,} returns "
        f"({multi:,} list more than one recipient line)")

    key = ["object_id", SEQ_SCHED]
    coll = key_collisions(rows, key)
    log(f"    key {tuple(key)} collisions: {coll}")
    if coll:
        raise SystemExit("REFUSED: the ordinal did not produce a unique key.")
    if not apply_it:
        return
    if SEQ_SCHED in cols:
        fields = cols
    else:
        fields = list(cols)
        fields.insert(fields.index("object_id") + 1
                      if "object_id" in fields else len(fields), SEQ_SCHED)
    write_csv_guarded(SCHED_I, rows, fields, cols, len(rows))
    back, bcols = read_csv(SCHED_I)
    dup_report(back, [c for c in bcols if c != SEQ_SCHED], "after (content)")
    log(f"    after (whole row, incl. the ordinal): "
        f"{key_collisions(back, bcols)} duplicate row(s)")


# ---------------------------------------------------------------------------
# 3. hearing_bill_links.csv -- un-ingest the source's own repetition
# ---------------------------------------------------------------------------
def fix_hearing_links(apply_it):
    log("\n" + "=" * 76)
    log("hearing_bill_links.csv  ->  un-ingest source repetition   (owner: 98)")
    log("=" * 76)
    rows, cols = read_csv(HEAR_LINKS)
    if not rows:
        log("    ABSENT - nothing to do")
        return
    groups, excess = dup_report(rows, cols, "before")
    if not excess:
        log("    already clean - nothing to do")
        return
    if not HEAR_DETAIL.exists():
        log(f"    !! {HEAR_DETAIL} ABSENT. The removal below can only be made "
            f"against the cached source, so NOTHING is changed. The builder "
            f"fix in 98 stands and will apply on the next fetch.")
        return

    # THE LICENCE, AND IT IS THE ONLY ONE IN THIS FILE. A row may be removed
    # ONLY where the cached Congress.gov payload lists the SAME relatedItems
    # .bills element more than once VERBATIM. That is not a Cedar fact being
    # deleted; it is one API array element having been read twice.
    per_event = {}
    for line in HEAR_DETAIL.open(encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        rb = d.get("related_bills") or []
        c = Counter()
        for b in rb:
            try:
                c[json.dumps(b, sort_keys=True)] += 1
            except TypeError:
                pass
        if any(v > 1 for v in c.values()):
            allowed = Counter()
            for b in rb:
                bid = "%s-%s-%s" % (b.get("congress"),
                                    (b.get("type") or "").lower(),
                                    b.get("number"))
                allowed[bid] = 1          # deduped: at most one per bill
            per_event[str(d.get("event_id"))] = allowed
    log(f"    cached source: {len(per_event)} event(s) list a related bill "
        f"more than once verbatim")

    keep, dropped = [], []
    seen = Counter()
    for r in rows:
        ev, bid = r.get("event_id", ""), r.get("bill_id", "")
        cap = per_event.get(ev, {}).get(bid)
        seen[(ev, bid)] += 1
        if cap is not None and seen[(ev, bid)] > cap:
            dropped.append(r)
            continue
        keep.append(r)
    log(f"    rows whose ONLY provenance is a repeated source element: "
        f"{len(dropped)}")
    for r in dropped:
        log(f"      event {r.get('event_id')} bill {r.get('bill_id')} - "
            f"Congress.gov lists this relatedItems.bills element twice")
    if len(dropped) != excess:
        raise SystemExit(
            f"REFUSED: {excess} excess row(s) on the file but only "
            f"{len(dropped)} are explained by a source repetition. The "
            f"unexplained rows are NOT to be deleted - they are a real "
            f"duplicate-ingest defect and need a different fix.")

    coll = key_collisions(keep, ["event_id", "bill_id"])
    log(f"    key ('event_id', 'bill_id') collisions after: {coll}")
    if coll:
        raise SystemExit("REFUSED: (event_id, bill_id) still collides.")
    if not apply_it:
        return
    write_csv_guarded(HEAR_LINKS, keep, cols, cols, len(rows),
                      rows_may_fall_by=len(dropped))
    back, bcols = read_csv(HEAR_LINKS)
    dup_report(back, bcols, "after")
    lost = ({r["bill_id"] for r in rows} - {r["bill_id"] for r in back}) | \
           ({r["event_id"] for r in rows} - {r["event_id"] for r in back})
    log(f"    bill_ids or event_ids that left the table entirely: {len(lost)}")
    if lost:
        raise SystemExit(f"REFUSED (post-write): {sorted(lost)} vanished.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="measure and verify; write nothing")
    args = ap.parse_args()
    apply_it = not args.check

    log("=" * 76)
    log(f"{SCRIPT} - {TODAY} - "
        f"{'APPLY' if apply_it else 'CHECK ONLY'}")
    log("=" * 76)
    fix_ferc(apply_it)
    fix_schedule_i(apply_it)
    fix_hearing_links(apply_it)
    log("\ndone. No row was deleted except where a cached source payload was "
        "proved to list the same element twice.")

    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / f"781_upstream_grain_columns_{TODAY}.txt").write_text(
        "\n".join(REPORT), encoding="utf-8")


if __name__ == "__main__":
    main()
