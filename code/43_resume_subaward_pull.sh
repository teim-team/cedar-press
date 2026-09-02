#!/usr/bin/env bash
# 43_resume_subaward_pull.sh — patient resumer for the 2026-08-05 subaward pull.
#
# api.usaspending.gov rate-limits by IP and the block does NOT clear quickly
# (RemoteDisconnected on api. AND files. from a fresh connection). Retrying hard through
# it extends it. This waits at a low fixed cadence, touching the edge once every 5
# minutes with a single cheap GET, and only resumes real work once it answers.
#
# On recovery it does two things in order:
#   1. `recover` — adopts the FY2012/FY2013 jobs that were already ACCEPTED server-side
#      before the block. They kept generating; re-submitting would waste them.
#   2. `pull --workers 1` — one worker only. Six concurrent workers is what tripped the
#      block in the first place.
#
# Usage: bash code/43_resume_subaward_pull.sh
set -u
cd "$(dirname "$0")/.."

PROBE='https://api.usaspending.gov/api/v2/references/agency/456/'
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
LOG=logs/43_resume_subaward_pull.log

# chunk=handle pairs for jobs accepted before the block (from
# logs/40_subaward_pull_2026-08-05.log, "<key> accepted -> <file>")
HANDLES='fy2012=All_Subawards_2026-08-05_H21M07S09092153.zip,fy2013=All_Subawards_2026-08-05_H21M08S18722160.zip'

say() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$LOG"; }

say "resumer armed; probing every 300s"
for i in $(seq 1 288); do        # up to 24h
  code=$(curl -s -o /dev/null -w '%{http_code}' -A "$UA" --max-time 45 "$PROBE" || echo 000)
  if [ "$code" = "200" ]; then
    say "edge ANSWERING (HTTP 200) on probe $i — resuming"
    py -3 code/40_pull_usaspending_subawards.py recover "$HANDLES" >>"$LOG" 2>&1
    py -3 code/40_pull_usaspending_subawards.py pull --workers 1 >>"$LOG" 2>&1
    rc=$?
    say "pull exited rc=$rc"
    # A mid-run re-block leaves chunks outstanding. Go back to probing rather than
    # hammering; the loop will pick up where the checkpoints left off.
    if py -3 code/40_pull_usaspending_subawards.py status 2>/dev/null | grep -q 'NOT PULLED'; then
      say "chunks still outstanding — back to probing"
      continue
    fi
    say "ALL CHUNKS STAGED"
    py -3 code/40_pull_usaspending_subawards.py merge-state >>"$LOG" 2>&1
    py -3 code/40_pull_usaspending_subawards.py manifest >>"$LOG" 2>&1
    exit 0
  fi
  say "probe $i: edge refusing (curl code $code); sleeping 300s"
  sleep 300
done
say "gave up after 24h of probing"
exit 1
