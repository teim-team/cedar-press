#!/usr/bin/env python3
"""
Cedar Press - 150: wait for the machine to clear, then run OCR alone overnight.

WHY A WAITER RATHER THAN JUST LAUNCHING
---------------------------------------
Elijah: "lets resume ocr over night so its the only thing running".

OCR is CPU-bound and its throughput collapses under contention. Measured today:
  8 shards, no thread cap  -> 5 docs in 45 min  (SLOWER per doc than 1 process)
  4 shards, OMP_NUM_THREADS=3 -> 24 docs in ~2.2 hours
The first run was worse than a single process because each rapidocr instance
lets onnxruntime grab every core it can see - 8 x 28 threads on 28 cores.

So this script does not start until the other work is actually done, then runs
8 shards at 3 threads each = 24 threads on 28 cores. That is deliberate
under-subscription, leaving headroom for the OS.

WHAT IT WAITS FOR
-----------------
Any python process that is NOT this script and NOT an OCR shard. Checked by
COMMAND LINE, never by image name - killing or counting `python.exe` by name
would catch every agent on the box. That rule is in AGENTS.md and it was
re-learned today when a kill filter matched the wrong PID because one run's
`--hosts` list contained another run's hostname.

RESUMABILITY
------------
`122_ocr_ordinance_scans.py` skips any ordinance whose .txt already exists, so
shards can be killed and restarted freely. Nothing is lost and no page is
re-rendered.

    py -3 code/150_run_ocr_overnight.py            # wait, then run
    py -3 code/150_run_ocr_overnight.py --now      # skip the wait
"""

import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
OCR_SCRIPT = "122_ocr_ordinance_scans.py"
OCR_DIR = CEDAR / "data" / "raw" / "external" / "nigc_ordinances" / "ocr"
LOGS = CEDAR / "logs"

N_SHARDS = 8
THREADS_PER_SHARD = "3"
WAIT_POLL_SEC = 120
MIN_BUSY_MB = 60          # below this it is a runtime, not a workload
WAIT_MAX_MIN = 600        # 10h - it is overnight; do not give up early


def busy_python():
    """Python processes doing REAL WORK - not this waiter, not OCR, not harness.

    Measured 2026-08-12: the box idles with 3 python processes from the uv
    cache at 0/14/17 MB. Those are MCP server / agent-harness infrastructure,
    not workloads. A naive "any python.exe" test treats them as busy and the
    waiter never fires.

    Two filters, both needed:
      - EXCLUDE anything running from the uv cache or uv python roots. That is
        harness, and it is always present.
      - INCLUDE only processes above a memory floor. A real build loads data;
        an idle runtime does not. 60 MB separates them cleanly here (the
        smallest real job today sat at 178 MB, the largest idle at 17 MB).

    Checked by COMMAND LINE, never by image name. Killing or counting
    `python.exe` by name would catch every agent on the machine - the rule in
    AGENTS.md, re-learned today when a filter matched the wrong PID because one
    run's --hosts list contained another run's hostname.
    """
    ps = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
         "ForEach-Object { [int]($_.WorkingSetSize/1MB).ToString() + '|' + $_.CommandLine }"],
        capture_output=True, text=True, timeout=60)
    out = []
    for line in (ps.stdout or "").splitlines():
        line = line.strip()
        if "|" not in line:
            continue
        mb_s, _, cmd = line.partition("|")
        try:
            mb = int(mb_s)
        except ValueError:
            continue
        if OCR_SCRIPT in cmd or "150_run_ocr_overnight" in cmd:
            continue
        low = cmd.lower()
        if r"\uv\cache" in low or r"roaming\uv\python" in low or "uv/cache" in low:
            continue                       # harness, always present
        if mb < MIN_BUSY_MB:
            continue                       # idle runtime, not a workload
        out.append(f"{mb} MB  {cmd[:70]}")
    return out


def done_count():
    return len(list(OCR_DIR.glob("*.txt"))) if OCR_DIR.exists() else 0


def main():
    now = "--now" in sys.argv
    t0 = time.time()
    print(f"=== 150: overnight OCR ===")
    print(f"  done so far: {done_count()} of 263\n")

    if not now:
        while True:
            busy = busy_python()
            if not busy:
                print("  machine clear - starting OCR")
                break
            mins = (time.time() - t0) / 60
            if mins > WAIT_MAX_MIN:
                print(f"  waited {WAIT_MAX_MIN} min and {len(busy)} job(s) are "
                      f"still up. Starting anyway - OCR yields under contention "
                      f"rather than failing.")
                break
            print(f"  [{datetime.now(timezone.utc):%H:%M}Z] waiting on "
                  f"{len(busy)} job(s):", flush=True)
            for b in busy[:4]:
                print(f"        {b}", flush=True)
            time.sleep(WAIT_POLL_SEC)

    LOGS.mkdir(exist_ok=True)
    for i in range(N_SHARDS):
        log = LOGS / f"ocr_shard_{i}.log"
        subprocess.Popen(
            ["py", "-3", "-u", f"code/{OCR_SCRIPT}", "--shard", f"{i}/{N_SHARDS}"],
            cwd=str(CEDAR),
            stdout=open(log, "a", encoding="utf-8"),
            stderr=subprocess.STDOUT,
            env={**__import__("os").environ,
                 "OMP_NUM_THREADS": THREADS_PER_SHARD,
                 "ORT_NUM_THREADS": THREADS_PER_SHARD},
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        print(f"  shard {i}/{N_SHARDS} launched (OMP_NUM_THREADS={THREADS_PER_SHARD})")
        time.sleep(2)

    print(f"\n  {N_SHARDS} shards x {THREADS_PER_SHARD} threads = "
          f"{N_SHARDS*int(THREADS_PER_SHARD)} threads on 28 cores")
    print(f"  progress: ls data/raw/external/nigc_ordinances/ocr/*.txt | wc -l")
    print(f"  resumable - completed .txt files are skipped on restart")


if __name__ == "__main__":
    main()
