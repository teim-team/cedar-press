"""30_wait_and_pull.py — wait out the usaspending edge block, then pull immediately.

The FY2001-2007 backfill is gated on one thing: api.usaspending.gov answering.
This waits at a polite fixed cadence and, the moment the host responds, starts
retrieving agencies in the brief's priority order without losing the window.

Route choice is made at runtime, gentlest first:
  1. Award Data Archive — pre-generated static per-agency, per-FY files. Costs no
     job generation, which is the resource the edge appears to meter.
  2. Generated bulk_download jobs — the route the prior run proved.

Everything is checkpointed per agency-year by 30_funding_pre2008.py, so a second
block mid-run costs only the agency in flight.

Usage: py -3 code/30_wait_and_pull.py [poll_seconds] [max_polls]
"""
import importlib.util
import os
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "fp", os.path.join(ROOT, "code", "30_funding_pre2008.py"))
fp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fp)

MIN_FREE_GB = 6


def free_gb() -> float:
    return shutil.disk_usage(ROOT).free / 1e9


def main():
    poll = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    max_polls = int(sys.argv[2]) if len(sys.argv) > 2 else 30

    fp.log(f"WAIT-AND-PULL armed: poll {poll}s x {max_polls} "
           f"(max {poll*max_polls/60:.0f} min), free disk {free_gb():.1f} GB")

    for i in range(1, max_polls + 1):
        if fp.api_available():
            fp.log(f"API AVAILABLE on poll {i}/{max_polls} — starting retrieval")
            break
        fp.log(f"PROBE {i}/{max_polls} api.usaspending.gov -> BLOCKED")
        if i == max_polls:
            fp.log("BLOCK NEVER CLEARED. Nothing retrieved. Zero agencies added. "
                   "State is clean and the pull is resumable: rerun this script.")
            return 1
        time.sleep(poll)

    if free_gb() < MIN_FREE_GB:
        fp.log(f"ABORT: only {free_gb():.1f} GB free, need {MIN_FREE_GB} GB headroom")
        return 5

    # Route 1 — static archive, if it exists and is reachable.
    # A pull that stops part-way must STILL be built and manifested: whatever
    # landed before the stop is real retrieved data and is not thrown away.
    try:
        files = fp.archive_index()
        fp.log(f"Award Data Archive reachable: {len(files)} assistance files listed")
        have_pre2008 = [f for f in files
                        if fp.FY_FIRST <= int(f[2:6]) <= fp.FY_LAST]
        fp.log(f"  of which FY{fp.FY_FIRST}-{fp.FY_LAST}: {len(have_pre2008)} files")
        if have_pre2008:
            fp.log("ROUTE = Award Data Archive (no job generation)")
            try:
                fp.stage_pull_archive(sleep_between=30)
            except SystemExit as e:
                fp.log(f"archive pull stopped early (exit {e.code}); continuing")
        else:
            fp.log("archive holds no pre-2008 assistance files for this window")
    except Exception as e:
        fp.log(f"archive route unavailable ({type(e).__name__}: {e}); continuing")

    # Route 2 — generated bulk jobs for whatever the archive could not supply.
    # This ALWAYS runs: the archive's assistance coverage starts at FY2007, so it
    # can never close FY2001-2006 on its own. stage_pull skips every agency-year
    # already held by either route, so this costs nothing when there is no gap.
    fp.log("ROUTE = generated bulk_download jobs for remaining agency-years")
    try:
        fp.stage_pull(sleep_between=60)
    except SystemExit as e:
        fp.log(f"bulk pull stopped early (exit {e.code}); building what landed")

    fp.stage_build()
    fp.stage_manifest()
    fp.log("WAIT-AND-PULL COMPLETE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
