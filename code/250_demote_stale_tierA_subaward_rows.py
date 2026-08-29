#!/usr/bin/env python3
"""
Cedar Press - 250: demote the 93 subaward rows carrying a tier A their source
row no longer supports. Reasoning and measurement: `code/249_...py` docstring.

WHAT THIS WRITES
----------------
`data/clean/subawards.csv`, two columns only:

    sub_native_tier   : "A" -> "B"   on 91 rows
    prime_native_tier : "A" -> "B"   on  2 rows

**No entity column is touched. No row is added or removed. No column is added.
Nothing is promoted. Nothing is re-tiered to X.**

WHICH ROWS, AND HOW THEY ARE SELECTED
-------------------------------------
Seven UEIs, all Olgoonik, whose ledger row is tier B via
`agent_research_one_leg` ("single evidence leg") since the 2026-08-06 pass
AGENTS.md records as *"49 single-leg rows were correctly demoted A -> B"*. A row
qualifies only when all three hold on the same leg:

    <leg>_uei              == one of the seven UEIs
    <leg>_native_tribe_id  == the entity the ledger names for that UEI
    <leg>_native_tier      == "A"

The entity condition is what makes this safe to re-run and impossible to
over-reach: it will not touch a row that some other pass has since repointed.

WHY THIS IS NOT THE `09`/`50` REBUILD-REVERT SHAPE
--------------------------------------------------
`41_match_subawards_to_ledger.py` and `45_promote_subawards.py` write these two
columns as a straight copy of the ledger's `confidence_tier` for that UEI. The
ledger says B. So a full re-promotion would write B here on its own, and this
script moves the file TOWARD the rebuild's output rather than away from it. It
adds no column a rebuild could silently drop.

CONCURRENCY - READ BEFORE RUNNING
---------------------------------
`121_pull_subawards_api.py pull` APPENDS to this same file. Check for it before
running:

    Get-CimInstance Win32_Process -Filter "Name like '%python%'" |
      Where-Object { $_.CommandLine -like '*121_pull_subawards_api*' }

This script therefore: records `mtime` and row count before reading, backs up
to `.bak_<date>_pre_250_demote_stale_tierA_subaward_rows` (script NAME, not
number), writes `.part` and renames, **re-checks the mtime immediately before
the rename and ABORTS if the file moved under it**, then re-reads the result
from disk and verifies the counts. A run log is not evidence that a write
landed on a shared machine.

    py -3 code/250_demote_stale_tierA_subaward_rows.py            # dry run
    py -3 code/250_demote_stale_tierA_subaward_rows.py --apply
"""

import csv
import os
import shutil
import sys
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
SUB = CLEAN / "subawards.csv"
TODAY = date.today().isoformat()
SCRIPT = "250_demote_stale_tierA_subaward_rows"
BACKUP = SUB.with_name(SUB.name + f".bak_{TODAY}_pre_{SCRIPT}")

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

LEGS = (("sub_uei", "sub_native_tribe_id", "sub_native_tier"),
        ("prime_uei", "prime_native_tribe_id", "prime_native_tier"))

REASON = (
    "Demoted A -> B on {date} by code/{script}. The tier on this column is a "
    "COPY of `confidence_tier` from the identifier ledger row for this UEI "
    "(41_match_subawards_to_ledger / 45_promote_subawards). That row is tier B "
    "via `agent_research_one_leg` - a single evidence leg - and has been since "
    "2026-08-06. The A here was taken before that demotion. A tier is INHERITED "
    "from the source row, never held by the consumer after the source moves. "
    "The ENTITY is unchanged and correct (docs/ANCSA_OWNERSHIP_RULING.md); only "
    "the tier is brought back into line. See "
    "review/ancsa_tierA_subaward_disposition_{date}.csv."
).format(date=TODAY, script=SCRIPT)


def load_disposition():
    p = REVIEW / f"ancsa_tierA_subaward_disposition_{TODAY}.csv"
    if not p.exists():
        raise SystemExit(f"run code/249 first - missing {p}")
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        rows = list(csv.DictReader(fh))
    targets = {}
    for r in rows:
        if not r["disposition"].startswith("DEMOTE_A_TO_"):
            continue
        to_tier = r["disposition"].rsplit("_", 1)[1]
        targets[r["identifier"].strip().upper()] = (
            r["to_entity_id"].strip(), to_tier, r["ledger_origin_method"])
    return rows, targets


def main():
    apply = "--apply" in sys.argv
    rows_disp, targets = load_disposition()
    expected = sum(1 for r in rows_disp
                   if r["disposition"].startswith("DEMOTE_A_TO_"))
    print(f"=== 250: demote stale tier-A subaward rows ({'APPLY' if apply else 'DRY RUN'}) ===\n")
    print(f"  identifiers to demote : {len(targets)}")
    print(f"  rows expected (from 249): {expected}")

    st0 = SUB.stat()
    print(f"  subawards.csv mtime   : {st0.st_mtime_ns}  size {st0.st_size:,}")

    with open(SUB, encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        fields = list(rd.fieldnames)
        data = list(rd)
    print(f"  rows read             : {len(data):,}  columns {len(fields)}")

    changed = Counter()
    for r in data:
        for uk, tk, tierk in LEGS:
            u = (r.get(uk) or "").strip().upper()
            tgt = targets.get(u)
            if not tgt:
                continue
            want_entity, to_tier, meth = tgt
            if (r.get(tk) or "").strip() != want_entity:
                continue
            if (r.get(tierk) or "").strip() != "A":
                continue
            r[tierk] = to_tier
            changed[(tierk, u)] += 1

    total = sum(changed.values())
    print(f"\n  rows changed          : {total:,}")
    for k, v in sorted(changed.items()):
        print(f"    {k[0]:<18} {k[1]}  {v:>4}")
    by_col = Counter(k[0] for k in changed.elements())
    for k, v in by_col.items():
        print(f"  {k:<18} total {v:,}")

    if total != expected:
        raise SystemExit(
            f"REFUSING: matched {total} rows, 249 said {expected}. The two "
            f"must agree exactly or the selection is not the audited set.")

    if not apply:
        print("\n  dry run - nothing written. Re-run with --apply.")
        return

    # ---- concurrency: nothing may have touched the file since we read it ---
    st1 = SUB.stat()
    if (st1.st_mtime_ns, st1.st_size) != (st0.st_mtime_ns, st0.st_size):
        raise SystemExit("REFUSING: subawards.csv changed while this script "
                         "was reading it. Another writer (121?) is live. "
                         "Nothing written.")

    shutil.copy2(SUB, BACKUP)
    print(f"\n  backed up to {BACKUP.name}")

    tmp = SUB.with_suffix(SUB.suffix + ".part")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(data)

    st2 = SUB.stat()
    if (st2.st_mtime_ns, st2.st_size) != (st0.st_mtime_ns, st0.st_size):
        os.remove(tmp)
        raise SystemExit("REFUSING at the last moment: subawards.csv changed "
                         "between read and rename. .part removed, live file "
                         "untouched, backup left in place.")
    tmp.replace(SUB)
    print("  renamed .part -> subawards.csv")

    # ---- verify by RE-READING, not by trusting the loop above -------------
    with open(SUB, encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        f2 = list(rd.fieldnames)
        back = list(rd)
    assert f2 == fields, "column set changed - restore from the backup"
    assert len(back) == len(data), "row count changed - restore from the backup"
    still_a = 0
    for r in back:
        for uk, tk, tierk in LEGS:
            u = (r.get(uk) or "").strip().upper()
            tgt = targets.get(u)
            if tgt and (r.get(tk) or "").strip() == tgt[0] \
                    and (r.get(tierk) or "").strip() == "A":
                still_a += 1
    print(f"\n  re-read: {len(back):,} rows, {len(f2)} columns, "
          f"{still_a} of the audited rows still tier A (must be 0)")
    assert still_a == 0, "demotion did not land - restore from the backup"

    note = REVIEW / f"ancsa_tierA_subaward_demotions_applied_{TODAY}.csv"
    tmp2 = note.with_suffix(note.suffix + ".part")
    with open(tmp2, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["identifier_type", "identifier", "tier_column",
                    "entity_id", "tier_before", "tier_after", "n_rows",
                    "ledger_origin_method", "reason", "applied_date"])
        for (tierk, u), n in sorted(changed.items()):
            ent, to_tier, meth = targets[u]
            w.writerow(["UEI", u, tierk, ent, "A", to_tier, n, meth,
                        REASON, TODAY])
    tmp2.replace(note)
    print(f"  wrote {note.relative_to(CEDAR)}")


if __name__ == "__main__":
    main()
