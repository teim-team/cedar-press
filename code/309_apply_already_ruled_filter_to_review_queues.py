#!/usr/bin/env python3
"""
Cedar Press - 309: subtract ALREADY-RULED subjects from every review queue in
`review/`, using the one shared helper `code/cedar_review_queue.py`.

    py -3 code/309_apply_already_ruled_filter_to_review_queues.py           # report
    py -3 code/309_apply_already_ruled_filter_to_review_queues.py --apply   # rewrite
    py -3 code/309_apply_already_ruled_filter_to_review_queues.py --file <p>

NO NETWORK. Reads `review/*.csv` and two clean tables. With `--apply` it
rewrites queue files in place, after a backup, `.part`-then-rename, and
re-reads every one of them to verify.

WHY
---
The 2026-08-12 Schedule I queue asks the owner about **2,138 recipients**, and
**30 of those rows carry an EIN he had already ruled tier X** - including
`UNITED WAY OF THE GREATER CHIPPEWA VALLEY INC`, the exact case the whole
tier-inheritance rule was built on. Measured against BOTH ruling sources the
overlap is far larger than 30.

He raised this on 2026-08-26: he is being re-shown entities he has already
adjudicated. **A one-off cleanup of one file would not fix it** - the next
queue writer re-creates it - so the subtraction is a shared helper
(`cedar_review_queue.subtract`) that every review-queue writer calls before its
file reaches a human, and this script applies it to the queues already on disk.

THE FOUR SAFETY RULES, AND WHY EACH ONE EXISTS
----------------------------------------------
**1. A ROW THAT ALREADY CARRIES AN ANSWER IS NEVER REMOVED.** `review/` is not
only a queue directory - it is the RULING CORPUS.
`173_consolidate_rulings_ledger.py` discovers its verdicts by walking
`review/**.csv` for a ruling column. Deleting an answered row would delete a
ruling. Only rows whose answer column is BLANK are eligible, so 173's input is
bit-for-bit unchanged for every verdict it reads.

**2. HAND INBOXES AND THE CONSOLIDATOR'S OWN OUTPUTS ARE NEVER TOUCHED.**
`rulings_inbox_*`, `_decisions_*`, `cedar_ruling_*` - these are evidence, not
questions. The exclusion is imported from 173 where it can be, so the two
cannot drift.

**3. A FILE ANOTHER AGENT IS WRITING IS NAMED, NOT EDITED.** Anything modified
within `LIVE_WINDOW_MIN` minutes is skipped and printed. Concurrency rule 6.

**4. EVERY DROPPED ROW IS WRITTEN OUT, IN FULL, WITH THE REASON.** This project
counts what it drops, by name. The removals land in
`review/_already_ruled_removals/`, and columns 173 would read as a ruling are
prefixed `queued_` there so the audit file can never be swept back in as
evidence for itself.

WHAT "ALREADY RULED" MEANS
--------------------------
Defined once, in `cedar_review_queue`, and filtered on **`outcome`, never
`status`**. `status` says the ruling was PROCESSED; `outcome` says what it
DECIDED, and a ruling has already read `status = SETTLED` while its outcome was
`HOLD_OVER_OWNER` - "HOLD - RETRACTION REQUIRED". A CONFLICTED subject is KEPT
and ANNOTATED rather than removed: a contradiction needs a human, but he should
be told he is looking at one.
"""

import csv
import importlib.util
import re
import shutil
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CODE = CEDAR / "code"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()
SCRIPT = "309_apply_already_ruled_filter_to_review_queues.py"
REMOVALS_DIR = REVIEW / "_already_ruled_removals"

LIVE_WINDOW_MIN = 30

sys.path.insert(0, str(CODE))
import cedar_review_queue as RQ                              # noqa: E402

#: Columns that ASK the owner something. A file with none of these is not a
#: queue and is not touched.
ASK_COLUMNS = ("your_ruling", "your_decision", "your_call", "needs_ruling",
               "question")
#: The column that would hold his answer, in priority order.
ANSWER_COLUMNS = ("your_ruling", "your_decision", "your_call", "ruling",
                  "decision", "verdict", "resolution")

#: Filenames that are a RECORD OF A REMOVAL, not a queue. Added after the
#: first run flagged `individual_native_queue_withdrawn_already_ruled_
#: 2026-08-26.csv` - another agent's own audit of what IT withdrew for being
#: already ruled - and would have emptied it. Subtracting already-ruled rows
#: from a file whose whole content IS already-ruled rows deletes the evidence
#: that the withdrawal happened. A record of a drop is not a question.
RECORD_NAME_RE = re.compile(
    r"(already_ruled|withdrawn|_removals?(_|\.)|_removed(_|\.)|"
    r"_applied(_|\.)|_audit(_|\.)|_log(_|\.))", re.I)


def _load_173():
    try:
        spec = importlib.util.spec_from_file_location(
            "m173_309", CODE / "173_consolidate_rulings_ledger.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception as e:                                   # noqa: BLE001
        print(f"  !! 173_consolidate_rulings_ledger.py could not be imported "
              f"({type(e).__name__}: {e}). Its hand-inbox and self-output "
              f"exclusions are UNAVAILABLE, so this run refuses to write.")
        return None


def header_of(p):
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return next(csv.reader(fh), [])


def read_rows(p):
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def pick(hdr, names):
    low = {(h or "").strip().lower(): h for h in hdr}
    for n in names:
        if n in low:
            return low[n]
    return None


def eligible_files(m173):
    """[(path, ask_col, answer_col)] - queues, not rulings, not live."""
    out, skipped = [], []
    now = time.time()
    for p in sorted(REVIEW.rglob("*.csv")):
        if ".bak" in p.name or p.suffix == ".part":
            continue
        if p.parent == REMOVALS_DIR:
            continue
        if RECORD_NAME_RE.search(p.name):
            skipped.append((p, "the filename says this is a RECORD of a "
                               "removal/application, not a question. "
                               "Subtracting already-ruled rows from it would "
                               "delete the evidence"))
            continue
        if m173 and (p.name in m173.SELF_OUTPUTS
                     or p.name.startswith(m173.SELF_PREFIX)
                     or m173.is_hand_inbox(p.name)):
            skipped.append((p, "ruling evidence (173 self-output or hand "
                               "inbox), never a queue"))
            continue
        try:
            hdr = header_of(p)
        except Exception as e:                               # noqa: BLE001
            skipped.append((p, f"unreadable ({type(e).__name__})"))
            continue
        if not hdr:
            continue
        ask = pick(hdr, ASK_COLUMNS)
        if not ask:
            continue
        age_min = (now - p.stat().st_mtime) / 60.0
        if age_min < LIVE_WINDOW_MIN:
            skipped.append((p, f"WRITTEN {age_min:.1f} MIN AGO - another agent "
                               f"may be mid-write; named, not edited "
                               f"(concurrency rule 6)"))
            continue
        out.append((p, ask, pick(hdr, ANSWER_COLUMNS)))
    return out, skipped


def rename_ruling_columns(rows, m173):
    """Prefix any column 173 would read as a ruling, in the AUDIT file only."""
    ruling_cols = {"your_ruling", "ruling", "decision", "entity_class",
                   "proposed_class", "entity_category", "verdict",
                   "audit_verdict", "resolution", "existing_ruling",
                   "proposed_ruling", "your_decision"}
    out = []
    for r in rows:
        out.append({(f"queued_{k}" if (k or "").strip().lower() in ruling_cols
                     else k): v for k, v in r.items()})
    return out


def main():
    apply = "--apply" in sys.argv
    only = None
    if "--file" in sys.argv:
        only = Path(sys.argv[sys.argv.index("--file") + 1]).resolve()

    print("=" * 78)
    print(f"309  ALREADY-RULED SUBTRACTION OVER review/  -  "
          f"{'APPLY' if apply else 'REPORT'}")
    print("=" * 78)

    m173 = _load_173()
    if m173 is None and apply:
        return 1

    print("\n[1] the already-ruled index")
    ruled = RQ.already_ruled(verbose=True)
    print(f"    ADJUDICATED outcomes: "
          f"{', '.join(sorted(RQ.ADJUDICATED_OUTCOMES))}")
    print(f"    CONFLICTED (kept, annotated): "
          f"{', '.join(sorted(RQ.CONFLICTED_OUTCOMES))}")

    files, skipped = eligible_files(m173)
    if only:
        files = [f for f in files if f[0].resolve() == only]
    print(f"\n[2] queue files in review/: {len(files)} eligible, "
          f"{len(skipped)} skipped")
    for p, why in skipped:
        print(f"    SKIP  {p.name:<62} {why}")

    print(f"\n[3] per-file result "
          f"({'rewriting in place' if apply else 'dry run'})")
    print(f"    {'file':<62} {'rows':>7} {'removed':>8} {'kept':>7} "
          f"{'annot':>6}")
    total_in = total_removed = total_annot = 0
    per_file, failures = [], []
    grand = Counter()

    for p, ask_col, ans_col in files:
        try:
            rows = read_rows(p)
            hdr = header_of(p)
        except Exception as e:                               # noqa: BLE001
            failures.append((p.name, f"unreadable ({type(e).__name__}: {e})"))
            continue

        # RULE 1: only a row with NO answer is eligible. An answered row is a
        # ruling and 173 reads it, so it is passed through untouched and is
        # never even offered to the filter.
        #
        # ORDER IS PRESERVED EXACTLY, by deciding row by row rather than
        # splitting into two lists and stitching them back together. The
        # stitch is where the bug would live.
        out_rows, removed, stats = [], [], Counter()
        n_annot = 0
        for r in rows:
            if ans_col and (r.get(ans_col) or "").strip():
                out_rows.append(r)
                stats["kept_answered_already"] += 1
                continue
            (new, action), = RQ.decide([r], ruled)
            if action == "REMOVE":
                removed.append(new)
                stats["removed_already_ruled"] += 1
                stats[f"removed_outcome_{new['removed_outcome']}"] += 1
            else:
                out_rows.append(new)
                if RQ.ANNOTATION_COLUMN in new:
                    n_annot += 1
                    stats["kept_conflicted"] += 1
                else:
                    stats["kept_never_ruled"] += 1

        if not removed and not n_annot:
            continue

        n_in, n_rm = len(rows), len(removed)
        n_answered = stats["kept_answered_already"]
        total_in += n_in
        total_removed += n_rm
        total_annot += n_annot
        for k, v in stats.items():
            grand[k] += v
        per_file.append((p, out_rows, removed, hdr, n_in, n_rm, n_annot,
                         n_answered))
        print(f"    {p.name:<62} {n_in:>7,} {n_rm:>8,} "
              f"{n_in - n_rm:>7,} {n_annot:>6,}")

    print(f"\n    {'TOTAL':<62} {total_in:>7,} {total_removed:>8,} "
          f"{total_in - total_removed:>7,} {total_annot:>6,}")
    print(f"\n    removals by outcome:")
    for k, v in sorted(grand.items()):
        if k.startswith("removed_outcome_"):
            print(f"      {k[len('removed_outcome_'):]:<24} {v:>6,}")
    print(f"      {'kept, never ruled':<24} "
          f"{grand.get('kept_never_ruled', 0):>6,}")
    print(f"      {'kept, CONFLICTED':<24} "
          f"{grand.get('kept_conflicted', 0):>6,}")

    for name, why in failures:
        print(f"    !! {name}: {why}")

    if not apply:
        print(f"\n    REPORT ONLY - nothing written. Re-run with --apply.")
        return 0
    if not per_file:
        print(f"\n    nothing to subtract. NOTHING WRITTEN.")
        return 0

    REMOVALS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n[4] writing")
    bad = []
    for p, out_rows, removed, hdr, n_in, n_rm, n_annot, n_ans in per_file:
        cols = list(hdr)
        if n_annot and RQ.ANNOTATION_COLUMN not in cols:
            cols.append(RQ.ANNOTATION_COLUMN)
        bak = p.with_name(p.name + f".bak_{TODAY}_pre_{SCRIPT[:-3]}")
        shutil.copy2(p, bak)
        part = p.with_suffix(p.suffix + ".part")
        with open(part, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(out_rows)
        part.replace(p)

        rpath = REMOVALS_DIR / f"{p.stem}_already_ruled_{TODAY}.csv"
        RQ.write_removals(rpath, rename_ruling_columns(removed, m173))

        # VERIFY BY RE-READING (concurrency rule 4).
        back = read_rows(p)
        hdr_back = header_of(p)
        ok = (len(back) == n_in - n_rm
              and [c for c in hdr if c in hdr_back] == list(hdr))
        print(f"    {p.name:<62} {len(back):>7,} rows on disk, "
              f"{len(hdr_back)} cols  {'OK' if ok else 'MISMATCH'}  "
              f"(bak {bak.name[-42:]})")
        if not ok:
            bad.append(p.name)

    if bad:
        print(f"\n    !! RE-READ MISMATCH on {bad}. The backups are beside "
              f"each file, tagged _pre_{SCRIPT[:-3]}.")
        return 1
    print(f"\n    {len(per_file)} queue file(s) rewritten, "
          f"{total_removed:,} already-ruled rows subtracted, "
          f"{total_annot:,} annotated as CONFLICTED.")
    print(f"    every dropped row is in {REMOVALS_DIR.relative_to(CEDAR)}, "
          f"in full, with the reason.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
