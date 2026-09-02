"""37_wait_then_pull.py — wait out the USAspending edge block, then resume.

FINDING THIS ENCODES
    api.usaspending.gov and files.usaspending.gov answer normally from a cold
    start, but sustained job submission + 20s status polling trips an
    edge-level block that presents as HTTP 000 / RemoteDisconnected on BOTH
    hosts at once. That is the same symptom an earlier session reported and
    concluded was a permanent network block. It is not permanent; it is
    self-inflicted and it clears. The fix is to poll gently and wait it out,
    never to hammer harder.

Probes every PROBE_EVERY seconds and exits the moment the host answers, then
hands off to 37_contracts_gapfill.pull (which resumes from checkpointed job
handles and never resubmits a job already paid for).
"""
import importlib.util
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
PROBE = "https://api.usaspending.gov/api/v2/references/agency/456/"
PROBE_EVERY = 300
MAX_TRIES = 48          # 4 hours


def stamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def alive():
    try:
        req = urllib.request.Request(PROBE, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.status == 200
    except urllib.error.HTTPError:
        return True          # edge is answering
    except Exception:
        return False


def main():
    for i in range(1, MAX_TRIES + 1):
        if alive():
            print(f"[{stamp()}] EDGE CLEAR after {i} probe(s) — resuming pull",
                  flush=True)
            break
        print(f"[{stamp()}] probe {i}/{MAX_TRIES}: still blocked", flush=True)
        time.sleep(PROBE_EVERY)
    else:
        print(f"[{stamp()}] STILL BLOCKED after {MAX_TRIES} probes. Nothing "
              f"resubmitted. Rerun this script later; job handles are "
              f"checkpointed so no generated file is lost.", flush=True)
        return 1

    time.sleep(30)
    spec = importlib.util.spec_from_file_location(
        "gf", os.path.join(HERE, "37_contracts_gapfill.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.stage_pull(sleep_between=60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
