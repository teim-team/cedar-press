# Collects USAspending subaward bulk_download jobs whose tokens were ACCEPTED
# but whose collect deadline expired before the files landed.
#
# WHY THIS EXISTS: on 2026-08-26 the bulk_download fleet recovered after a
# service-wide outage and `121_pull_subawards_api.py pull --sequential` began
# five full-year jobs to close the FY2021-2024 hole (173/89/120/166 rows against
# ~7,000-9,000 in a healthy year). FY2021 alone sat 54 minutes at rows_so_far=0
# — not a stall, the canary did the same before returning 47,059 rows — but five
# full-year jobs plausibly outrun the script's 8h COLLECT_DEADLINE (~05:19Z).
# On deadline the script logs its outstanding tokens, leaves them in _state.json
# and exits. Accepted server work then sits uncollected. That is the exact
# built-but-never-landed failure this project has lost work to repeatedly.
#
# THIS SCRIPT ONLY COLLECTS. It does not promote. Promotion (41 -> 45 -> 35)
# rewrites shared tables and must be run supervised, when no other agent is
# writing. The remaining commands are printed at the end, not executed.
#
# Run:  powershell -File code\collect_subawards_after_deadline.ps1
# Safe to run repeatedly.

$root = "C:\Users\esm247\Desktop\Cedar Press"
$log  = Join-Path $root "logs\subaward_collect_retry.log"
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null

function Say($m) {
  $line = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $m
  Write-Host $line; Add-Content -Path $log -Value $line -Encoding utf8
}

Say "=== subaward collect retry armed ==="

# Wait until the pull's own 8h deadline has passed, plus slack, so we never
# contend with the live poller. NEVER run two pollers at one host.
$deadlineUtc = [DateTime]::UtcNow.Date.AddDays(1).AddHours(5).AddMinutes(35)  # ~05:35Z
$wait = [int]($deadlineUtc - [DateTime]::UtcNow).TotalSeconds
if ($wait -gt 0) {
  Say ("waiting until {0}Z ({1} min) so the live poller finishes or expires" -f $deadlineUtc.ToString("HH:mm"), [int]($wait/60))
  Start-Sleep -Seconds $wait
}

# Refuse to start if a poller is still alive - one poller per host, always.
#
# Watch ALL THREE processes in the tree, not just the requester. A poller
# launched under nohup is nohup.exe -> py.exe -> python.exe, and on 2026-08-26 a
# harness killed the bash WRAPPER while python.exe kept polling for another two
# minutes. "Background task killed" read exactly like "the pull died", and the
# reflex fix - re-run `pull` - would have re-submitted a job the server had been
# generating for 61 minutes, discarding the completed work and the queue
# position. A DEAD WRAPPER IS NOT A DEAD POLLER. If in any doubt: `collect`,
# never `pull`.
$live = Get-CimInstance Win32_Process -EA SilentlyContinue |
        Where-Object { $_.Name -in @('python.exe','py.exe','nohup.exe') -and
                       $_.CommandLine -like "*121_pull_subawards_api*" }
if ($live) {
  Say "a 121 process is STILL ALIVE - not contending. pids: $(($live | ForEach-Object { "$($_.ProcessId)/$($_.Name)" }) -join ', ')"
  Say "re-run this script later. Do NOT run 'pull' - the accepted token is still generating."
  exit 0
}

# Belt and braces: an unreleased host lock also means hands off.
$lockFile = Join-Path $root "logs\_HOSTLOCK_api.usaspending.gov.json"
if (Test-Path $lockFile) {
  try {
    $lock = Get-Content $lockFile -Raw | ConvertFrom-Json
    if ($lock.active -eq $true) { Say "host lock still ACTIVE on api.usaspending.gov - not contending."; exit 0 }
  } catch { Say "could not parse host lock; proceeding cautiously" }
}

Set-Location $root
Say "running: collect  (accepted tokens only - NEVER re-submits)"
& py -3 code/121_pull_subawards_api.py collect 2>&1 | ForEach-Object { Say "  $_" }

if ($LASTEXITCODE -eq 0) {
  Say "collect OK - running match"
  & py -3 code/121_pull_subawards_api.py match 2>&1 | ForEach-Object { Say "  $_" }
  if ($LASTEXITCODE -eq 0) {
    Say "match OK - running append"
    & py -3 code/121_pull_subawards_api.py append 2>&1 | ForEach-Object { Say "  $_" }
  }
}

Say ""
Say "STOPPING BEFORE PROMOTION - these rewrite shared tables, run them supervised:"
Say "  py -3 code/41_match_subawards_to_ledger.py"
Say "  py -3 code/45_promote_subawards.py"
Say "  py -3 code/35_coverage_audit.py     # subcontracts moves off 63,548"
Say "  py -3 code/62_no_regression_check.py"
Say "=== done ==="
