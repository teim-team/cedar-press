#!/usr/bin/env python3
"""
Cedar Press master pipeline. One script, switches per stage.

    py -3 code/00_run_all.py                  # full rebuild
    py -3 code/00_run_all.py --only spine     # one stage
    py -3 code/00_run_all.py --from rulings   # this stage onward
    py -3 code/00_run_all.py --list           # show stages
    py -3 code/00_run_all.py --dry-run        # print, don't execute

Design rules this enforces:
  * Cedar Press is SELF-CONTAINED. Stages stage their inputs into
    data/raw/external/ and build from local copies.
  * NOTHING publishes above tier A. Rulings are the only promotion path.
  * Re-running is safe. Stages are idempotent; rulings accumulate from
    review/rulings_inbox_*.csv and are re-applied every run.

Update cadence: run `--from rulings` after each batch of Elijah's rulings.
Run the whole thing after a source refresh.
"""

import argparse
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
TODAY = date.today().isoformat()

# (key, script, description, rebuild_cost)
STAGES = [
    ("spine", "01_build_entity_spine.py",
     "Stage external inputs; build entity spine + identifier ledger", "fast"),
    ("exclusions", "02_extract_exclusion_rulings.py",
     "Extract per-UEI exclusion jurisprudence from hci_analysis.do", "fast"),
    ("tier", "03_apply_exclusions_and_tier.py",
     "Apply exclusions, detect authority conflicts, assign A/B/C/X tiers", "fast"),
    ("hierarchy", "13_build_fpds_hierarchy.py",
     "Rebuild UEI ownership edges + CAGE map from raw FPDS (4.4 GB)", "SLOW"),
    ("spiderweb", "18_spiderweb_v2_and_cage_backfill.py",
     "Propagate ownership structurally; backfill CAGE codes", "fast"),
    ("rulings", "09_import_rulings.py",
     "Import Elijah's rulings; propagate; flag discredited methods", "fast"),
    ("nho", "19_rebuild_nho_layer.py",
     "Rebuild NHO layer (rulings are the only verification)", "fast"),
    # A second spiderweb pass AFTER rulings. The first pass (stage 5) runs on
    # the pre-ruling ledger, so a newly confirmed entity would not seed
    # structural propagation until the next full run - and `--from rulings`
    # skipped it entirely. Elijah's rulings must reach the corporate families
    # they unlock BEFORE the review queue is rebuilt, or the queue keeps
    # showing items his rulings already resolved by inheritance.
    ("spiderweb2", "18_spiderweb_v2_and_cage_backfill.py",
     "Re-propagate ownership from newly ruled entities", "fast"),
    ("floor", "22_apply_temporal_floor.py",
     "Stamp pre_2000_flag across built datasets (flag, never delete)", "fast"),
    ("crossdata", "23_cross_dataset_propagation.py",
     "Propagate rulings, exclusions and method quarantines across all datasets", "fast"),
    ("linked", "31_build_dataset5_linked.py",
     "Dataset 5 — entity-year linked file + dated ownership-event ledger", "fast"),
    ("review", "08_build_review_page.py",
     "Regenerate the review queue, dropping settled items", "fast"),
    ("publish", "25_build_publication_layer.py",
     "Build dist/ — SQLite DB, master spreadsheet, sanity checks (FAILS LOUDLY)", "fast"),
]

# Stages that exist but are deliberately NOT in the default run.
MANUAL = {
    "05_parse_doi_nho_list.py": "DOI NHO roster - only when the PDF is refreshed",
    "07_parse_ancsa_ceiling.py": "ANCSA roster - only when the source page changes",
    "10_pull_federal_register.py": "FR harvest - hours; run deliberately",
    "11_classify_federal_actions.py": "FR classifier - run after a harvest",
    "14_build_bills_votes.py": "Bills & votes - run after a votingpatterns refresh",
    "15_build_compacts.py": "Compacts - run after a BIA compact refresh",
    "17_build_nonprofit_990.py": "IRS 990 - run after a BMF refresh",
    "23d_build_gaming_facilities.py": "Gaming directory core - run after a "
                                      "votingpatterns/Casino City refresh. "
                                      "REBUILDS gaming_facilities.csv and "
                                      "gaming_facility_metrics.csv from source, "
                                      "so 23f must run immediately after it.",
    "23f_gaming_temporal.py": "Gaming time dimension (as_of_date, opening "
                              "lifespan + bounds). Depends on 23d having run; "
                              "re-run it whenever 23d does or the temporal "
                              "columns are lost.",
    "70_key_unjoined_datasets.py":
        "Entity keys for compacts, bills, nonprofits, federal actions, "
        "ownership events and gaming. RE-RUN IT AFTER 15 / 17 / 23d / 31 - "
        "each of those REBUILDS a dataset 70 writes into, which silently "
        "drops tribe_id/entity_id and returns the file to 0% keyed. Also "
        "re-run after any spine or ruling change, since both feed the match. "
        "~3 min; safe to repeat (the pre-70 backup is written only once).",
    "24_funding_merge.py": "Federal funding merge (MR-1..MR-8) - ~100s, "
                           "streams the 631 MB assistance file twice; "
                           "run after a new USAspending assistance pull",
}


def run(script, dry):
    path = CEDAR / "code" / script
    if not path.exists():
        print(f"    SKIP - not on disk: {script}")
        return None
    if dry:
        print(f"    would run: py -3 code/{script}")
        return True
    t0 = time.time()
    proc = subprocess.run([sys.executable, str(path)], cwd=str(CEDAR),
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    dt = time.time() - t0
    log = CEDAR / "logs" / f"_pipeline_{script.replace('.py','')}_{TODAY}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text((proc.stdout or "") + (proc.stderr or ""), encoding="utf-8")
    tail = [l for l in (proc.stdout or "").strip().splitlines() if l.strip()][-4:]
    for l in tail:
        print(f"      {l}")
    if proc.returncode != 0:
        print(f"    FAILED ({dt:.1f}s) - see {log.name}")
        err = (proc.stderr or "").strip().splitlines()
        for l in err[-5:]:
            print(f"      ! {l}")
        return False
    print(f"    ok ({dt:.1f}s)")
    return True


def main():
    ap = argparse.ArgumentParser(description="Cedar Press master pipeline")
    ap.add_argument("--only", metavar="STAGE", help="run exactly one stage")
    ap.add_argument("--from", dest="start", metavar="STAGE",
                    help="run from this stage onward")
    ap.add_argument("--skip", metavar="STAGE", action="append", default=[],
                    help="skip a stage (repeatable)")
    ap.add_argument("--list", action="store_true", help="list stages and exit")
    ap.add_argument("--dry-run", action="store_true", help="print without executing")
    ap.add_argument("--include-slow", action="store_true",
                    help="include stages marked SLOW (default: skipped)")
    args = ap.parse_args()

    if args.list:
        print("\nCedar Press pipeline stages\n")
        for k, s, d, cost in STAGES:
            mark = "  [SLOW]" if cost == "SLOW" else ""
            print(f"  {k:<11} {s:<38} {d}{mark}")
        print("\nManual / on-refresh only:")
        for s, why in MANUAL.items():
            print(f"  {'':<11} {s:<38} {why}")
        print()
        return 0

    keys = [k for k, _, _, _ in STAGES]
    for bad in [x for x in ([args.only, args.start] + args.skip) if x and x not in keys]:
        print(f"unknown stage: {bad}\nvalid: {', '.join(keys)}")
        return 2

    selected = STAGES
    if args.only:
        selected = [s for s in STAGES if s[0] == args.only]
    elif args.start:
        i = keys.index(args.start)
        selected = STAGES[i:]
    selected = [s for s in selected if s[0] not in args.skip]
    if not args.include_slow and not args.only:
        skipped_slow = [s[0] for s in selected if s[3] == "SLOW"]
        selected = [s for s in selected if s[3] != "SLOW"]
        if skipped_slow:
            print(f"(skipping SLOW stages: {', '.join(skipped_slow)} "
                  f"- pass --include-slow to run them)")

    print(f"\n=== Cedar Press pipeline - {TODAY} ===")
    print(f"{len(selected)} stage(s)\n")

    results = {}
    for k, script, desc, cost in selected:
        print(f"  [{k}] {desc}")
        results[k] = run(script, args.dry_run)

    print("\n=== PIPELINE SUMMARY ===")
    ok = sum(1 for v in results.values() if v is True)
    failed = [k for k, v in results.items() if v is False]
    missing = [k for k, v in results.items() if v is None]
    print(f"  ok      : {ok}")
    if missing:
        print(f"  missing : {', '.join(missing)}")
    if failed:
        print(f"  FAILED  : {', '.join(failed)}")
        return 1
    print("\n  Reminder: only tier A publishes. Everything else waits on a ruling.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
