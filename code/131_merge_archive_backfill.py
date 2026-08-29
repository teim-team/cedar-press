#!/usr/bin/env python3
"""
Cedar Press - 131: Merge the staged archive backfill into prime_contracts.csv.

WHAT THIS FIXES
---------------
`prime_contracts.csv` FY2000-FY2022 came from `master prime file.dta`, a BGOV
export taken under a size cap and **pre-filtered to where Native entities were
expected**. `prime_contracts_archive_backfill.csv` holds 631,507 rows for
FY2008-FY2022 pulled from the USAspending static archive, which has no upstream
filter.

The filter's damage is MISSING ENTITIES, not wrong dollars. Measured on FY2022
(docs/PRIME_ARCHIVE_PULL_LOG.md): 96.3% of shared contracts agree within 0.5% on
obligations, while 20 Cedar entities had FY2022 prime contracting the `.dta`
population missed entirely. So this is a POPULATION replacement, not a
measurement correction.


THE KEY, AND WHY IT IS NOT THE ONE THAT WAS ASKED FOR
-----------------------------------------------------
The obvious transaction identity is PIID + modification_number +
transaction_number + agency. **Two of those four fields do not exist on the
BGOV side and the fourth is not an identifier.** Verified, not assumed:

1. `master prime file.dta` has 27 columns and **carries no modification_number
   and no transaction_number**. The full column list is in the docstring of
   `code/40_build_prime_contracts.py`'s source; re-read it before disputing
   this. A BGOV row is an award-year-vendor aggregate, not a modification.
   Measured: 507,564 BGOV rows FY2008-22 over 402,005 distinct (PIID, FY) -
   1.26 rows per contract-year. The archive over the same years is 631,507 rows
   over 295,664 distinct (PIID, FY) - 2.14 rows per contract-year, which is
   what transaction level looks like.

2. `funding_agency` IS PRESENT ON BOTH SIDES AND MUST NOT BE IN THE KEY. It is
   a free-text agency LABEL and the two sources use different vocabularies for
   the same office - `Us Geological Survey` vs `Geological Survey`,
   `Office Of The Assistant Secretary For Administration (Asa)` vs the
   unparenthesised form, and so on. Measured cost of including it:

       key                     BGOV attributed rows left unmatched
       piid+fy+uei                    584   ($0.203B)
       piid+fy+uei+agency          40,949   ($20.739B)   <- 20.5B double-counted

   Adding `agency` to the key would have left **$20.5B of the same contracts
   counted twice** on nothing but a label difference, and the file would have
   looked bigger and more complete while doing it.

**So the key is (contract_number, fiscal_year, awardee_uei)** - the
contract-year-vendor identity, the finest key BOTH sources actually support.
`fiscal_year` is in the key because both files are fiscal-year partitioned and
a PIID spans years; dropping it would collapse across years. `awardee_uei` is
in the key because a PIID recurs across vendors under an IDV - dropping it
wrongly merged 157 rows belonging to a different vendor.


PRECEDENCE: THE ARCHIVE WINS WHOLESALE ON A SHARED KEY, NOT FIELD BY FIELD
--------------------------------------------------------------------------
On a key present in both sources, every BGOV row is DROPPED and every archive
row is KEPT. There is no per-field blending, and that is deliberate: the BGOV
side contributes ONE aggregate row per key and the archive contributes N
transaction rows. Copying a field from the aggregate onto the transactions, or
vice versa, would invent a row that neither source reported.

Why the archive is the winner where they disagree:
  - it is the unfiltered universe; the `.dta` is the filtered one, and the
    filter is the defect being repaired;
  - it is transaction-level, matching FY2023-FY2026 already in the file;
  - 96.3% dollar agreement on shared contracts means completeness is not being
    bought with accuracy;
  - its set-aside is already filled forward award-level across all 19 pulled
    years by `code/114_pull_prime_archive.py` (191,991 awards), so the field
    that most needed borrowing does not need borrowing.

`source_file` is NOT rewritten on any row. Every kept BGOV row still says
`master prime file.dta`; every archive row still names its own archive object
and stamp. The seam stays visible in the data.


WHAT IS DELIBERATELY LEFT ALONE
-------------------------------
  - **FY2000-FY2007** - untouched. No `_All_Contracts_Full_` object exists
    below FY2007 in the archive listing and FY2007 has not landed, so these
    years stay BGOV-filtered. This is a known coverage floor, not an oversight.
  - **FY2023-FY2026** - untouched. Already archive-sourced. The backfill holds
    no rows for these years and the script asserts it.
  - **266,604 unattributed BGOV rows in FY2008-22 ($55.2B)** - kept. The
    archive extract retained only ledger-matched rows, so these have no archive
    counterpart and cannot double-count against it. They remain
    `attributed_flag=0` and enter no entity total.
  - **584 attributed BGOV rows ($0.203B) on keys the archive never had** -
    kept and written to review/. These are the ".dta-only" contracts the pull
    log flagged for a ruling. Flagged, not dropped.

Reads  data/clean/prime_contracts.csv
       data/clean/prime_contracts_archive_backfill.csv
       data/spine/cedar_entity_spine.csv        (via cedar_prime_panel)
Writes data/clean/prime_contracts.csv            (backed up first)
       data/clean/prime_contracts_entity_year.csv (backed up first)
       review/prime_merge_bgov_only_attributed_<date>.csv

Run `py -3 code/62_no_regression_check.py` before AND after. Restore from the
backup on any FELL line.
"""

import argparse
import csv
import os
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CEDAR / "code"))

import cedar_prime_panel  # noqa: E402  (needs CEDAR on the path first)
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

SHIPPED = CLEAN / "prime_contracts.csv"
BACKFILL = CLEAN / "prime_contracts_archive_backfill.csv"
PANEL = CLEAN / "prime_contracts_entity_year.csv"

# Default scope: the years the staged backfill held on 2026-08-12. FY2007 is
# NOT in this default because it had not landed yet - it was still owed from the
# host. When it lands it is appended to the backfill by script 114 and merged
# with `--years 2007`, using the same key and the same precedence rule.
#
# The scope is a PARAMETER rather than a constant so that adding a year cannot
# silently re-merge the years already merged. Every run asserts that the
# backfill holds no year outside the scope it was asked for, and refuses if the
# target already carries an archive row for a year in scope.
LO, HI = 2008, 2022


def key(r):
    """Contract-year-vendor identity. See the docstring for why not PIID+mod."""
    return (r["contract_number"], r["fiscal_year"],
            (r.get("awardee_uei") or "").strip().upper())


def read_header(p):
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return next(csv.reader(fh))


def main():
    global LO, HI
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default=f"{LO}-{HI}",
                    help="fiscal years in scope, e.g. '2007' or '2008-2022'")
    args = ap.parse_args()
    if "-" in args.years:
        LO, HI = (int(x) for x in args.years.split("-", 1))
    else:
        LO = HI = int(args.years)

    csv.field_size_limit(10 ** 9)
    print("=== Cedar Press 131: merge archive backfill into prime_contracts ===")
    print(f"    scope: FY{LO}-FY{HI}\n")

    # ---- preconditions ---------------------------------------------------
    h_ship, h_back = read_header(SHIPPED), read_header(BACKFILL)
    if h_ship != h_back:
        sys.exit(f"REFUSING: schemas differ.\n shipped: {h_ship}\n backfill: {h_back}")
    print(f"schemas identical ({len(h_ship)} columns)")

    # Pass 1 over the backfill: keys and year bounds, RESTRICTED TO SCOPE.
    #
    # Out-of-scope years are skipped, not refused. Once FY2007 lands, script
    # 114 appends it to this same backfill file alongside the FY2008-22 rows
    # that a previous run already merged. Re-reading those merged years here
    # would re-add every one of them. So scope filtering is what keeps a
    # second run from double-counting the first run's work.
    arch_keys = set()
    arch_years = Counter()
    skipped_years = Counter()
    with open(BACKFILL, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            y = int(r["fiscal_year"])
            if not (LO <= y <= HI):
                skipped_years[y] += 1
                continue
            arch_years[y] += 1
            arch_keys.add(key(r))
    if not arch_years:
        sys.exit(f"REFUSING: the backfill holds no rows for FY{LO}-FY{HI}. "
                 f"Years present: {sorted(skipped_years)}. Nothing to merge.")
    arch_rows = sum(arch_years.values())
    print(f"backfill in scope: {arch_rows:,} rows, FY{min(arch_years)}-"
          f"FY{max(arch_years)}, {len(arch_keys):,} distinct keys")
    if skipped_years:
        print(f"  out of scope, left alone: {sum(skipped_years.values()):,} rows "
              f"in FY{min(skipped_years)}-FY{max(skipped_years)}")

    # IDEMPOTENCY GUARD. If a year in scope already holds an archive-sourced
    # row the merge has run before, and running it again would append a second
    # full copy while every count still looked like growth.
    with open(SHIPPED, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            y = int(r["fiscal_year"])
            if LO <= y <= HI and "_All_Contracts_Full_" in (r.get("source_file") or ""):
                sys.exit(f"REFUSING: FY{y} already holds an archive-sourced row "
                         f"({r['source_file']}). The merge has already run. "
                         f"Restore from a backup rather than merging twice.")
    print(f"idempotency guard passed - no FY{LO}-FY{HI} archive rows "
          f"already present")

    # ---- backup ----------------------------------------------------------
    scope = f"{LO}" if LO == HI else f"{LO}-{HI}"
    for p in (SHIPPED, PANEL):
        bak = p.with_suffix(p.suffix + f".bak_{TODAY}_pre_archive_merge_fy{scope}")
        if bak.exists():
            sys.exit(f"REFUSING: backup {bak.name} already exists - would overwrite "
                     f"the only copy of the pre-merge state.")
        bak.write_bytes(p.read_bytes())
        print(f"backed up -> {bak.name}")

    # ---- merge -----------------------------------------------------------
    part = SHIPPED.with_suffix(".csv.part")
    dropped = Counter()
    dropped_obl = 0.0
    kept = 0
    kept_by_fy = Counter()
    bgov_only_attr = []          # attributed BGOV rows the archive never had
    ent_after = defaultdict(float)
    ent_before = defaultdict(float)

    with open(part, "w", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(out, fieldnames=h_ship)
        w.writeheader()

        with open(SHIPPED, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                v = float(r.get("total_obligations") or 0)
                attr = r.get("attributed_flag") == "1"
                if attr:
                    ent_before[r["tribe_id"]] += v
                y = int(r["fiscal_year"])
                if LO <= y <= HI and key(r) in arch_keys:
                    dropped[r.get("attributed_flag")] += 1
                    dropped_obl += v
                    continue
                if LO <= y <= HI and attr:
                    bgov_only_attr.append(r)
                w.writerow(r)
                kept += 1
                kept_by_fy[y] += 1
                if attr:
                    ent_after[r["tribe_id"]] += v

        with open(BACKFILL, encoding="utf-8-sig", newline="") as fh:
            n = 0
            for r in csv.DictReader(fh):
                y = int(r["fiscal_year"])
                if not (LO <= y <= HI):      # already merged by an earlier run
                    continue
                w.writerow(r)
                n += 1
                kept_by_fy[y] += 1
                if r.get("attributed_flag") == "1":
                    ent_after[r["tribe_id"]] += float(r.get("total_obligations") or 0)
    total = kept + n
    print(f"\ndropped {sum(dropped.values()):,} BGOV rows on shared keys "
          f"(${dropped_obl/1e9:.3f}B) - attributed_flag {dict(dropped)}")
    print(f"kept    {kept:,} BGOV/existing rows")
    print(f"added   {n:,} archive rows")
    print(f"MERGED  {total:,} rows")

    os.replace(part, SHIPPED)
    print(f"\nwrote {SHIPPED.name}")

    # ---- rebuild the entity-year panel (the guard reads THIS file) -------
    #
    # THE GRAIN IS (tribe_id, fiscal_year). This block used to key the panel on
    # (tribe_id, canonical_name, fiscal_year, confidence_tier) - one entity-year
    # in up to three rows - and so did 40 and 114. A buyer merging any other
    # entity-year table onto a file NAMED entity-year fanned out and multiplied
    # their own dollars, with nothing to warn them. The aggregation now lives in
    # `cedar_prime_panel` so the three copies cannot drift apart again, and it
    # REFUSES to write a panel whose primary key is not unique or whose dollars
    # do not equal the rows it summed.
    prows, pstats = cedar_prime_panel.build_from_prime(
        prime_path=SHIPPED, panel_path=PANEL, today=TODAY)
    cedar_prime_panel.write_panel(prows, PANEL)
    print(f"wrote {PANEL.name}  ({len(prows):,} rows, "
          f"{len({r['tribe_id'] for r in prows}):,} entities, "
          f"one row per (tribe_id, fiscal_year) - verified)")
    cedar_prime_panel.print_stats(pstats)
    _xp, _xn = cedar_prime_panel.write_excluded(pstats, TODAY)
    print(f"wrote {_xp.relative_to(CEDAR)}  ({_xn:,} named exclusions - every (awardee_uei, awardee_name, fiscal_year, reason) that entered no entity total)")

    # ---- what changed ----------------------------------------------------
    be = {k for k in ent_before if k}
    af = {k for k in ent_after if k}
    print(f"\nentities  {len(be):,} -> {len(af):,}   NEW {len(af - be):,}   "
          f"LOST {len(be - af):,}")
    if af - be:
        print("  NEW entities the BGOV-filtered file never had:")
        for t in sorted(af - be, key=lambda t: -ent_after[t]):
            print(f"    {t:26} ${ent_after[t]:>16,.2f}")
    tb, ta = sum(ent_before[k] for k in be), sum(ent_after[k] for k in af)
    print(f"\nattributed obligations ${tb:,.2f} -> ${ta:,.2f}  (+${ta - tb:,.2f})")

    # ---- flag, do not drop ----------------------------------------------
    REVIEW.mkdir(exist_ok=True)
    rp = REVIEW / f"prime_merge_bgov_only_attributed_fy{scope}_{TODAY}.csv"
    with open(rp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=h_ship + ["review_note"])
        w.writeheader()
        for r in bgov_only_attr:
            r = dict(r)
            r["review_note"] = ("Attributed BGOV row FY2008-22 whose "
                                "(PIID, FY, awardee_uei) the archive universe "
                                "does not contain. RETAINED. Needs a ruling on "
                                "whether the .dta saw something the archive did "
                                "not, or carries a stale identifier.")
            w.writerow(r)
    print(f"\nwrote {rp.relative_to(CEDAR)}  ({len(bgov_only_attr):,} rows flagged, "
          f"not dropped)")

    print("\nrows by fiscal year after merge:")
    for y in sorted(kept_by_fy):
        print(f"  {y}  {kept_by_fy[y]:8,}")
    print("\nNOW RUN: py -3 code/62_no_regression_check.py")


if __name__ == "__main__":
    main()
