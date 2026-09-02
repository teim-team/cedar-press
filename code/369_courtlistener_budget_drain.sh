#!/bin/sh
# 369 - drain the CourtListener daily budget in rolling-window slices.
#
# WHY A LOOP AND NOT ONE PASS.  The free tier's hourly cap is a ROLLING
# 60-minute window, not a clock hour.  49 requests sent between 00:16 and
# 00:34 free up a few slots at a time from 01:16 onward, so a single pass
# after a fixed sleep spends 8 requests and exits with 70 unspent.  This
# walks the window instead: attempt, spend whatever room exists, sleep,
# attempt again.  366/367/368 each meter themselves against the shared
# ledger and exit cleanly with `room <= 0`, so a no-op pass costs nothing.
#
# ONE POLLER.  All three scripts claim logs/_HOSTLOCK_www.courtlistener.com.json
# and queue-and-exit if it is held, so this loop can never become a second
# poller against the host.
#
# BOUNDED.  Stops after DEADLINE seconds no matter what - PULL_DISCIPLINE's
# "backoff bounds the RATE, not the RUN".
cd "C:/Users/esm247/Desktop/Cedar Press"
DEADLINE=$(( $(date +%s) + 9000 ))
while [ "$(date +%s)" -lt "$DEADLINE" ]; do
  echo "=== pass at $(date -u +%H:%M:%S)Z ==="
  py -3 code/368_courtlistener_party_roles_and_docs.py roles --max 8
  py -3 code/367_courtlistener_party_name_probe.py ask --max 25
  SPENT=$(py -3 code/366_courtlistener_ownership_adjudication.py spend 2>/dev/null | grep "last 24h" | tr -dc '0-9/' )
  echo "budget line: $SPENT"
  case "$SPENT" in 125/125) echo "DAILY BUDGET EXHAUSTED"; break;; esac
  sleep 420
done
echo "=== drain finished at $(date -u +%H:%M:%S)Z ==="
