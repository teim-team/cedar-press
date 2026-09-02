# Waits for the SAM daily quota reset (00:00 UTC), then downloads every
# outstanding contract-awards extract token.
#
# WHY: on 2026-08-26 all six FY2000-2007 extracts were ACCEPTED by SAM, but the
# 10/day call budget was exhausted before they could all be downloaded. The
# submissions are the irreplaceable half and they are done. Tokens are
# checkpointed in _export_tokens.json.
#
# Run:  powershell -File code\retry_sam_downloads.ps1
# Safe to run repeatedly. Already-downloaded tokens are skipped.

$ErrorActionPreference = "Stop"
$dest = "C:\Users\esm247\Desktop\Cedar Press\data\raw\contracts\sam_contract_awards"
$log  = "C:\Users\esm247\Desktop\Cedar Press\logs\sam_retry_downloads.log"
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null

function Say($m) {
  $line = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $m
  Write-Host $line; Add-Content -Path $log -Value $line -Encoding utf8
}

$tokens = [ordered]@{
  "EANGlhSctK" = "INDIAN / ENTITY_OWNED"
  "fdgGBhrCjJ" = "ALASKAN NATIVE / ENTITY_OWNED"
  "YkWOTVSRHn" = "NATIVE HAWAIIAN / ENTITY_OWNED"
  "xAjEAaGtTI" = "AMERICAN INDIAN / INDIVIDUAL_NATIVE_OWNED"
  "PTdhhaQztU" = "NATIVE AMERICAN / INDIVIDUAL_NATIVE_OWNED"
}

Say "=== SAM retry starting ==="

# --- wait for 00:00 UTC ---
$nowUtc = (Get-Date).ToUniversalTime()
$reset  = $nowUtc.Date.AddDays(1)          # next UTC midnight
$wait   = [int]($reset - $nowUtc).TotalSeconds
if ($wait -gt 0) {
  Say ("quota resets at {0}Z - sleeping {1} min" -f $reset.ToString("yyyy-MM-dd HH:mm"), [int]($wait/60))
  Start-Sleep -Seconds ($wait + 120)       # 2 min of slack
}
Say "quota window open"

$k = [Environment]::GetEnvironmentVariable("SAM_API_KEY","User")
if (-not $k) { Say "FATAL: SAM_API_KEY not set in user environment"; exit 1 }

$ok = 0; $gone = 0; $failed = 0
foreach ($t in $tokens.Keys) {
  $final = Join-Path $dest "sam_extract_$t.zip"
  if (Test-Path $final) { Say "skip $t - already downloaded"; continue }

  $out = Join-Path $dest "sam_extract_$t.part"
  try {
    Invoke-WebRequest -Uri "https://api.sam.gov/contract-awards/v1/download?api_key=$k&token=$t" `
                      -OutFile $out -TimeoutSec 600 -ErrorAction Stop
    $sz = (Get-Item $out).Length
    Move-Item $out $final -Force
    Say ("OK   {0}  {1}  {2:N2} MB" -f $t, $tokens[$t], ($sz/1MB))
    $ok++
  } catch {
    $c = $null; if ($_.Exception.Response) { $c = [int]$_.Exception.Response.StatusCode }
    if (Test-Path $out) { Remove-Item $out -Force }
    if ($c -eq 429) { Say "STOP $t - still rate limited; aborting rather than hammering"; break }
    # a 303 wrapping an S3 404 means the export object was never written -
    # the token is NOT bad. Do not discard it.
    Say ("FAIL {0}  HTTP {1}  {2}" -f $t, $c, $tokens[$t])
    if ($c -eq 404 -or $c -eq 410) { $gone++ } else { $failed++ }
  }
  Start-Sleep -Seconds 20   # space the calls; the tier is small
}

Say "=== done: $ok downloaded, $gone expired, $failed other ==="
if ($gone -gt 0) {
  Say "Expired tokens must be RE-SUBMITTED (not re-downloaded):"
  Say "  py -3 code/141_pull_sam_contract_awards.py extract"
  Say "  Six calls covers all six variants; budget is 10/day."
}
Get-ChildItem $dest -Filter "sam_extract_*.zip" |
  ForEach-Object { Say ("  have: {0}  {1:N2} MB" -f $_.Name, ($_.Length/1MB)) }
