# Persist the SAM.gov public API key so it survives the session.
#
# WHY THIS EXISTS: on 2026-08-26 the key that worked on 08-12/13 could not be
# found anywhere on this machine. It had lived only in one session's
# environment and was never written down. Losing it cost the FY2000-2007
# backfill. This script makes that failure impossible to repeat.
#
# GET THE KEY:
#   1. https://sam.gov/  ->  sign in
#   2. Workspace  ->  Profile (your name, top right)  ->  Account Details
#   3. "Public API Key" section  ->  click the eye icon
#   4. SAM emails you a one-time password; enter it and the key is revealed
#      (Do NOT use the link in the rotation email - it does not show the key.)
#
# THEN RUN:
#   .\set_sam_key.ps1 -Key "PASTE_KEY_HERE"
#
# It writes to the USER environment (persists across reboots and sessions) and
# to a gitignored .env.local, then verifies with ONE metered call.

param([Parameter(Mandatory = $true)][string]$Key)

$Key = $Key.Trim()
if ($Key.Length -lt 20) { Write-Host "That does not look like a SAM key (too short). Nothing written." -ForegroundColor Red; exit 1 }

# 1. persist to the user environment - survives reboot
[Environment]::SetEnvironmentVariable("SAM_API_KEY", $Key, "User")
$env:SAM_API_KEY = $Key
Write-Host "SAM_API_KEY written to user environment." -ForegroundColor Green

# 2. persist to a local dotfile as a second copy
$envFile = Join-Path $PSScriptRoot ".env.local"
$lines = @()
if (Test-Path $envFile) { $lines = Get-Content $envFile | Where-Object { $_ -notmatch '^SAM_API_KEY=' } }
$lines += "SAM_API_KEY=$Key"
Set-Content -Path $envFile -Value $lines -Encoding utf8
Write-Host "Also written to $envFile" -ForegroundColor Green

# 3. verify with exactly one call
Write-Host "`nVerifying with one call..." -ForegroundColor Cyan
$u = "https://api.sam.gov/entity-information/v4/entities?api_key=$Key&entityName=test&includeSections=entityRegistration"
try {
    $r = Invoke-WebRequest -Uri $u -Method GET -UseBasicParsing -TimeoutSec 30 -ErrorAction Stop
    Write-Host "HTTP $($r.StatusCode) - key is VALID." -ForegroundColor Green
    Write-Host "`nNext, from the Cedar Press directory:" -ForegroundColor Cyan
    Write-Host "  py -3 code/141_pull_sam_contract_awards.py canary"
    Write-Host "  py -3 code/141_pull_sam_contract_awards.py extract"
    Write-Host "`nThe canary spends 1 of your 10 daily calls. extract will refuse to send until an accepted canary is on record."
} catch {
    $code = $null
    if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode }
    if ($code -eq 401 -or $code -eq 403) {
        Write-Host "HTTP $code - key was REJECTED. It is saved but will not work." -ForegroundColor Red
        Write-Host "Re-check you copied the Public API Key from Account Details, not a registration or rotation link."
    } elseif ($code -eq 429) {
        Write-Host "HTTP 429 - rate limited. The key may be fine; try the canary later." -ForegroundColor Yellow
    } else {
        Write-Host "Could not verify (HTTP $code). The key is saved; run the canary to test." -ForegroundColor Yellow
    }
}
