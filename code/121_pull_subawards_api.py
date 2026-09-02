#!/usr/bin/env python3
"""
Cedar Press - 121: close the FY2021-FY2024 subaward gap, and re-pull the FY2020
contract-subaward member that came back empty. API-ONLY WORK.

WHY THIS IS THE ONLY ROUTE
--------------------------
`docs/ASSISTANCE_ARCHIVE_PULL_LOG.md` FINDING 1, measured against a full
enumeration of the static archive: **zero of 4,631 keys contain the string
"sub" in any case.** `files.usaspending.gov` publishes Contracts and Assistance
only. Direct probes of every plausible subaward path returned 404 or 403. FSRS
subaward data is served by `api.usaspending.gov`
`POST /api/v2/bulk_download/awards/` with `sub_award_types` and by nothing else,
which is why this gap outlived two archive pulls.

WHAT IS OWED, AND HOW IT WAS ESTABLISHED
----------------------------------------
`docs/SUBAWARD_RAW_MATCH_LOG.md` §1, three independent checks:

  1. `_state.json` holds 22 finished jobs: fy2001..fy2020, fy2025, fy2026.
     fy2021, fy2022, fy2023, fy2024 were NEVER SUBMITTED.
  2. Across all 6,613,471 raw rows, every row's
     `subaward_action_date_fiscal_year` equals its own job's fiscal year - zero
     bleed - so the missing years are not hiding inside a neighbouring chunk.
  3. The 548 FY2021-2024 rows the clean file does hold name a different source
     on every row (`highergov_2023_export`, `funding_forward_fill`).

And a fifth job: the `fy2020` bulk download returned its assistance member with
456,412 rows and a contracts member of **4,144 bytes - one header line, zero
data rows** (FY2019's is 439 MB). Neighbouring years hold 5,047 and 5,987
Native-linked contract subawards, so zero is not credible as a fact about the
world. The server returned an empty member. It is re-submitted here as a
PROCUREMENT-ONLY job so the answer is unambiguous: an empty procurement-only
file is a fact about FY2020, not a fact about a mixed job.

PULL DISCIPLINE - THE TWO STOPS BACKOFF CANNOT PROVIDE
-------------------------------------------------------
`docs/PULL_DISCIPLINE.md` (2026-08-08): an agent with correct 60s->30min backoff
still built a runaway, because backoff bounds the RATE and not the RUN. 16 years
x 6 attempts against a refusing host extended a block for a peer on the same IP.

Two stops, both enforced in code:

  * `SUBMIT_DEADLINE` - no NEW work (probe, submit, or a backoff retry) may
    START more than SUBMIT_HOURS (default 2h) after the run began. Checked
    before each attempt AND before each backoff sleep, because a 30-minute sleep
    otherwise carries you past the deadline anyway.

  * stop-on-first-refusal-when-nothing-has-succeeded. If the first job exhausts
    its backoff and NOTHING has been accepted by the server, the HOST is
    refusing, not the object. Trying the remaining four is four more ways to
    learn the same fact. Exits 2 - a finding, not a crash.

A THIRD DEADLINE, AND WHY IT IS SEPARATE
-----------------------------------------
`COLLECT_DEADLINE` (default 8h) governs polling for jobs THE SERVER HAS ALREADY
ACCEPTED. It is deliberately longer than SUBMIT_DEADLINE and it is not a licence
to hammer anything:

  * Rule 5 forbids re-submitting an accepted job. Measured generation times on
    this exact endpoint run 550s to 11,102s - fy2019 took 3.1 hours. A 2h stop
    applied to collection would ABANDON completed server work and force exactly
    the re-submission the rule prohibits.
  * The poll is one cheap GET per outstanding job per POLL_EVERY (150s), and it
    stops INSTANTLY on a refusal (status 0 or 5xx), falling back to the same
    bounded backoff.
  * Every token is persisted to `_state.json` the moment the server accepts it,
    so a killed poller loses nothing and `collect` resumes it. That is what
    makes stopping safe.

A DROPPED CONNECTION IS NOT A 404
----------------------------------
`http_status = 0` means the transport failed and is STOP-WORK; a 404 is a fact
about the object. They are never collapsed. Every request records
(status, seconds, detail) and sub-second failures are logged as an EDGE BLOCK.

WHO CAUSED THE LAST BLOCK
-------------------------
Recorded in the host lock and in `docs/ASSISTANCE_ARCHIVE_PULL_LOG.md` FINDING
6: script 115 pulled six ~2 GB objects in twelve minutes with a 15s pause and
edge-blocked `files.usaspending.gov` at 2026-08-08T00:55Z, which then stopped a
peer. This run's objects are ~100-200 MB, submissions are spaced SUBMIT_SPACING
(180s), and at most MAX_INFLIGHT (3) jobs generate at once.

THE MONEY RULES TRAVEL WITH THE DATA
-------------------------------------
`docs/DATA_ODDITIES.md`: 5,941 rows report a subaward LARGER than its own prime
award, worst case 12,240x. `duplicate_status` and `subaward_exceeds_prime_flag`
are computed on EVERY appended row and applied to NONE. Totalling requires
`duplicate_status == 'primary' AND subaward_exceeds_prime_flag != 'yes'`.

FSRS floor is 2010: FFATA's threshold dropped from $25M to $25,000 in October
2010, which is why FY2009->FY2012 runs 30 -> 113 -> 1,652 -> 2,679. That ramp is
the threshold, not the activity, and it is already in `series_breaks.csv` (not
edited here). Rows dated earlier carry `action_date_precedes_ffata_flag` and are
retained.

RESOLUTION - IDENTIFIERS FIRST, THEN NAMES, WITH THE GUARDS
-------------------------------------------------------------
`33_apply_party_rulings.resolve_entity` is the ONE resolver (standing rule 8) and
it is IMPORTED. So is the entire guarded name route from
`94_match_raw_subawards.py` - `name_route`, `build_spine_index`, `parent_ok`,
`build_row` - because re-typing eight guards that each cost a real
misattribution is how they drift apart. `cedar_match_guard.guard()` is imported
and called as a SECOND veto layer after `resolve_entity`; it is NOT modified.

Route order and tier:
  identifier (UEI exact, ledger)      -> ledger's own A/B
  declared parent UEI (ledger)        -> B, family level
  name + 8 guards + cedar_match_guard -> B, always, and always to review/
  containment                         -> attributes NOTHING, banked as candidate

APPEND-ONLY, WITH ONE DOCUMENTED HEADER CHANGE
-----------------------------------------------
Rows are appended; no existing row is ever rewritten. The file does gain three
COLUMNS it never had (`subaward_amount_real2025`, `deflator_factor_2025`,
`inflation_base_year`), which is a header change and therefore a rewrite - done
exactly as `115_pull_assistance_archive.py` did it: every existing row keeps
every existing value, new columns are appended at the END, the file is re-read
immediately before writing, written to a temp file and swapped atomically, and a
timestamped `.bak` is kept. A field-by-field verification of all pre-existing
rows against the backup runs after the swap and restores on any mismatch.

`_real2025` uses `data/clean/inflation_deflator.csv` (BEA NIPA 1.1.9 implicit
GDP price deflator, base 2025). NO SECOND DEFLATOR is introduced.

THE MATCH SCHEMA GUARD WAS WRONG AND IS CORRECTED (2026-08-28)
--------------------------------------------------------------
`match` tested `header != m45.COLS` - strict equality against the 49-column
promoted schema. That guard **deadlocked this script against its own output**.
`append` adds three columns at the END of `subawards.csv`, so from the first
successful append onwards the live header is a 52-column superset and `match`
refused every subsequent run: "subawards.csv header is not the promoted
schema". That is what blocked the FY2021 backfill. It was drift, not
corruption - all 49 canonical columns were present and in order.

The old check was wrong because equality is not the property that matters.
What matters is whether a row written with the 49 canonical columns can land
in the file with nothing silently blanked. So the guard now requires:
  1. the 49 canonical columns present, IN ORDER, at the front, and
  2. every column beyond them to be one `append` knows how to compute (NEW_COLS).
Condition 2 is why this is not a loosening: an extra column `append` cannot
fill would be blanked on every appended row, and that still halts the run.
The deflator columns are never blanked - `append` recomputes all three from
`fiscal_year` and `subaward_amount` for EVERY row it writes, pre-existing and
newly staged alike, which also makes `append` idempotent.

The ordering is unchanged and is the one AGENTS.md concurrency rule 5
prescribes: the staging step writes the canonical columns, and THE ENRICHER
RUNS LAST. `append` is that enricher. There is no separate enricher script.

NOTE FOR THE NEXT AGENT - 41 AND 45 CANNOT PROMOTE THIS PULL.
`41_match_subawards_to_ledger.py` and `45_promote_subawards.py` both read only
`data/raw/subcontracts/usaspending_subawards_2026-08-05`. They cannot see
`usaspending_2026-08-12/`. Running 45 to promote FY2021 would (a) not promote
it, (b) re-read the live 63k-row `subawards.csv` through `load_existing()`,
which stamps `source_dataset=highergov_2023_export` on every row it reads -
written when that file held only the 998 HigherGov rows - and re-append them
on top of a fresh rebuild of the same universe, and (c) write 49 columns,
reverting the deflator enrichment (defect class 6). The route for the
2026-08-12 pull is `121 match` then `121 append`.

THE 2026-09-01 RUN - WHAT WAS FETCHED, AND THE ONE PARAMETER THAT CHANGED
--------------------------------------------------------------------------
State on entry: `fy2021` FINISHED on 2026-08-26 (765,109 raw rows, 23,613s
server-side) and is appended. `fy2022`, `fy2023`, `fy2024` and
`fy2020_procurement` still carried their 2026-08-12 tokens, all four
`status: failed / "An error occurred."` - the service-wide outage that run
diagnosed. Rule 5 does not bind on a corpse, so they are re-submitted; the dead
tokens stay in `_state.json` as evidence.

Canary first, as the doctrine requires: ONE two-day job, 2026-09-01 22:36:22Z,
FINISHED 22:45:29Z with 47,060 rows. The fleet builds files today.

**max_inflight is 5 (parallel) for this run, not 1 (sequential), and the reason
is a measurement rather than a preference.** The sequential posture was adopted
after 2026-08-12, when five concurrent full-year jobs were all accepted and all
failed. `diagnose` then ruled that out as the cause: `diag_prime_2021` was a
two-day PRIME job and it failed too, so the outage was service-wide (verdict A),
not a function of how many subaward jobs were queued. Against that, sequential
now has a measured cost: fy2021 alone took 6.6 hours server-side, so three years
one-at-a-time is ~20 hours and would cross COLLECT_DEADLINE with tokens still
generating. Three ACCEPTED jobs are SERVER-side load; OUR request rate is three
cheap status GETs per POLL_EVERY, i.e. one request per 50 seconds. The
2026-08-05 block came from four POLLERS on a 300s metronome, not from queued
jobs. If a future run sees all of several concurrent jobs fail while a lone
canary succeeds, THAT is the evidence sequential was waiting for; it did not
exist on 2026-09-01.

THE DROPPED COLUMN - `subaward_sam_report_id` (MEASURED 2026-09-01, ZERO NETWORK)
---------------------------------------------------------------------------------
`525_event_ids.py` registers subcontracting as the one dataset that GENUINELY
lacks an event id, and closes "diagnose the source extract first." Done, on the
extracts already on disk:

  * The FSRS extract carries **121 columns**. `94_match_raw_subawards.build_row`
    reads **26** of them. Ninety-five are dropped.
  * One of the dropped ones is **`subaward_sam_report_id`**, and it is a
    GLOBALLY UNIQUE ROW ID:
        FY2021  765,109 rows -> 765,109 distinct, 0 blank
        FY2020  456,412 rows -> 456,412 distinct, 0 blank
        FY2020 n FY2021 = **0** overlap
    It is a UUID, unique across BOTH zip members and across fiscal years.

**This is the same shape as `prime_contracts`, where 80,778 "duplicates" turned
out to be distinct transactions whose `modification_number` the mapper never
carried.** The source has always had the key; the mapper never carried it.

BUT THE MONEY RULE IS NOT WRONG, AND THIS IS THE HALF THAT MATTERS
-------------------------------------------------------------------
A unique id on the row does NOT mean the rows are distinct subawards, and the
difference is the whole finding. `m45.identity_key` collides on 111,933 of
765,109 FY2021 raw rows (14.6%). The worst group is 93 rows. All 93 carry
distinct `subaward_sam_report_id`s - and their `subaward_sam_report_month`
values run from 2022-08 to 2025-01 on ONE $57,500 subaward with one action date
and one subaward number.

**They are 93 monthly SAM re-filings of one subaward, not 93 subawards.** So:

  * `duplicate_status == 'exact_repeat_within_source'` is SUBSTANTIVELY CORRECT
    and the money rule that excludes those rows must stay. Summing them would
    inflate FY2021 by ~14.6% of rows.
  * `subaward_sam_report_id` identifies **a SAM subaward REPORT**, not a
    subaward. Any surrogate minted over it must SAY that in its name and in the
    525 registry, or it manufactures the same false distinctions 525 warns
    about - just with a source-provided id instead of a home-made one.
  * Carrying `subaward_sam_report_id`, `subaward_sam_report_month` and
    `subaward_sam_report_last_modified_date` would make `duplicate_status`
    AUDITABLE - today it is inferred from a six-field tuple and cannot be
    checked against the source without re-reading a 1.2 GB zip.

**NOT DONE HERE, DELIBERATELY.** Adding those columns changes the grain
declaration of a shipping table and belongs with whoever owns `525_event_ids.py`
and the schema. This run reports the measurement and does not mint the key.
Also dropped and recoverable from this same extract, noted for that pass:
`subawardee_duns` / `prime_awardee_duns` (the 2023 HigherGov export had no DUNS
at all), sub-side city / zip / place-of-performance, congressional districts,
CFDA numbers on the assistance member, and the five highly-compensated-officer
pairs.

COVERAGE IS A CLAIM ABOUT THE SOURCE, NOT ABOUT OUR FILE
---------------------------------------------------------
`docs/datasets/subcontracting.md` carries the per-source coverage table this
project keeps re-deriving. Two boundaries in it are REAL-WORLD FACTS and are
therefore coverage being COMPLETE:

  * **FSRS begins FY2010.** FFATA dropped the reporting threshold from $25M to
    $25,000 in October 2010. FY2001-2009 jobs returned 4,945 rows in total and
    every one carries `subaward_sam_report_year >= 2010` - they are filer typos
    in `subaward_action_date`, retained and flagged
    (`action_date_precedes_ffata_flag`), never counted as coverage.
  * **FY2026 is open.** Its window runs to 2026-09-30 and cannot be complete.

And one that is OURS:

  * **FY2020 has no contract subawards at all.** The 2026-08-05 `fy2020` job
    returned an assistance member of 456,412 rows and a contracts member of
    4,144 bytes - one header line. Every other year's contracts member is
    60-470 MB. `fy2020_procurement` exists to answer that unambiguously.

Reads   api.usaspending.gov  (bulk_download/awards, download/status)
        files.usaspending.gov/generated_downloads/  (the accepted job's output)
        data/clean/cedar_identifier_ledger_final.csv
        data/spine/cedar_entity_spine.csv
        data/clean/inflation_deflator.csv
        data/clean/subawards.csv                      (index + header)
Writes  data/raw/subcontracts/usaspending_2026-08-12/*.zip
                                          + _state.json + _SOURCE_MANIFEST.csv
        data/clean/subawards.csv                      (append + 3 new columns)
        data/clean/codebook/02b_subawards_api.csv     (FRAGMENT ONLY)
        review/subaward_api_unresolved_<date>.csv
        logs/121_pull_subawards_api.log
        logs/_HOSTLOCK_api.usaspending.gov.json       (claim/release)

NEVER TOUCHED: codebook_master.csv, series_breaks.csv, the identifier ledger,
the spine, prime_contracts.csv, federal_funding_transactions.csv, gaming_*,
nigc_*, compact_*, entity_*. `09_import_rulings.py` and
`01_build_entity_spine.py` are NOT run.

Usage
  py -3 code/121_pull_subawards_api.py claim      # host lock, then stop
  py -3 code/121_pull_subawards_api.py pull       # claim + submit + collect
  py -3 code/121_pull_subawards_api.py collect    # resume accepted tokens only
  py -3 code/121_pull_subawards_api.py status
  py -3 code/121_pull_subawards_api.py manifest
  py -3 code/121_pull_subawards_api.py match [--dry-run]
  py -3 code/121_pull_subawards_api.py append
  py -3 code/121_pull_subawards_api.py codebook
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import json
import os
import shutil
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import Counter, defaultdict
from datetime import date, datetime, timezone

csv.field_size_limit(1 << 27)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = os.path.join(ROOT, "code")
CLEAN = os.path.join(ROOT, "data", "clean")
SPINE_DIR = os.path.join(ROOT, "data", "spine")
REVIEW = os.path.join(ROOT, "review")
LOGS = os.path.join(ROOT, "logs")

RAW = os.path.join(ROOT, "data", "raw", "subcontracts", "usaspending_2026-08-12")
STATE = os.path.join(RAW, "_state.json")
MANIFEST = os.path.join(RAW, "_SOURCE_MANIFEST.csv")
STAGE = os.path.join(ROOT, "data", "staging", "subawards_api_2026-08-12")
LOGFILE = os.path.join(LOGS, "121_pull_subawards_api.log")
HOSTLOCK = os.path.join(LOGS, "_HOSTLOCK_api.usaspending.gov.json")

OUT = os.path.join(CLEAN, "subawards.csv")
DEFLATOR = os.path.join(CLEAN, "inflation_deflator.csv")

HOST = "api.usaspending.gov"
API = "https://api.usaspending.gov/api/v2/bulk_download/awards/"
STATUS_EP = "https://api.usaspending.gov/api/v2/download/status"
PROBE_EP = "https://api.usaspending.gov/api/v2/references/agency/456/"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

FETCHED = "2026-08-12"
TODAY = date.today().isoformat()

# ---- pacing. Every number here is a measurement or a rule, not a preference.
SUBMIT_HOURS = float(os.environ.get("CEDAR_SUBMIT_HOURS", "2"))
COLLECT_HOURS = float(os.environ.get("CEDAR_COLLECT_HOURS", "8"))
SUBMIT_SPACING = 180        # 115's 15s pause earned an edge block; 180s did not
POLL_EVERY = 150            # one cheap GET per outstanding job per interval
# All five jobs are submitted UP FRONT, spaced 180s apart, so every submission
# lands inside SUBMIT_DEADLINE (~12 minutes of a 2h budget) and the run never
# has to choose between the deadline rule and rule 5. Five ACCEPTED jobs is
# server-side load, not our request rate: our rate is five cheap status GETs per
# POLL_EVERY, i.e. one request per 30s. The 2026-08-05 block came from FOUR
# POLLERS on a 300s metronome, not from queued jobs.
MAX_INFLIGHT = 5
BACKOFF_BASE = 60.0
BACKOFF_MAX = 1800.0
BACKOFF_TRIES = 6

RUN_START = time.time()
SUBMIT_DEADLINE = RUN_START + SUBMIT_HOURS * 3600
COLLECT_DEADLINE = RUN_START + COLLECT_HOURS * 3600

# ---------------------------------------------------------------------------
# THE JOBS. Payload is byte-identical to the one that produced the 22 staged
# jobs (`_SOURCE.md` §1 / `40_pull_usaspending_subawards.build_payload`), so the
# new years are the same population as the old ones and the seam is a date, not
# a definition.
#
# `fy2020_procurement` is the exception and it is deliberate: procurement-only,
# so an empty result is unambiguous.
# ---------------------------------------------------------------------------
JOBS = [
    ("fy2021", "2020-10-01", "2021-09-30", ["procurement", "grant"]),
    ("fy2022", "2021-10-01", "2022-09-30", ["procurement", "grant"]),
    ("fy2023", "2022-10-01", "2023-09-30", ["procurement", "grant"]),
    ("fy2024", "2023-10-01", "2024-09-30", ["procurement", "grant"]),
    ("fy2020_procurement", "2019-10-01", "2020-09-30", ["procurement"]),
    # ---- added 2026-09-01 under the FULL-HORIZON COVERAGE MANDATE ----------
    # FSRS reports arrive YEARS after the action date - measured on one FY2021
    # subaward whose 93 SAM reports run from 2022-08 to 2025-01. So a fiscal
    # year that has CLOSED still gains rows, and "we pulled that year once" is
    # not the same claim as "we hold that year". These two re-pull the same
    # windows the 2026-08-05 corpus used, so every row they add is a filing
    # that did not exist when that pull ran. They are DEDUPED, not stacked:
    # `match` skips any row whose `m45.identity_key` count is already met by
    # the live file, so re-reading a window is idempotent by construction.
    ("fy2025_refresh", "2024-10-01", "2025-09-30", ["procurement", "grant"]),
    ("fy2026_refresh", "2025-10-01", "2026-09-30", ["procurement", "grant"]),
]


# ---------------------------------------------------------------------------
# QUARTERLY SLICES - the fallback, added 2026-09-01 after fy2023 and fy2024
# died together server-side.
#
# READ THIS BEFORE CONCLUDING "THE JOBS ARE TOO BIG". They are not, and the
# measurement is on this very endpoint in this very directory:
#
#   fy2021       full fiscal year, 765,109 rows  -> FINISHED in 23,613s
#   canary_2day  two days,          47,060 rows  -> FINISHED in 536s
#   canary_2day  two days           (2026-08-12) -> FAILED server-side
#
# A full year completes and a two-day job can fail, so SIZE DOES NOT PREDICT
# THE OUTCOME. Note also that fy2021 reported `rows_so_far=0` for almost all of
# its 393 minutes - the server reports 0 until it has built the file - so a job
# sitting at zero rows for an hour is EARLY, not dead. Do not kill it; that
# discards completed server work and costs the queue position (rule 5).
#
# What DID separate the outcomes on 2026-09-01 was CONCURRENCY: three full-year
# jobs were accepted 180s apart, and the second and third failed at the SAME
# INSTANT (00:07:14Z) while the first kept generating. That is the evidence the
# post-2026-08-12 sequential posture was waiting for and never had.
#
# So the slices below are a HEDGE, not a diagnosis. They buy two things a
# smaller request genuinely does buy, whatever killed the full-year jobs:
#   * a failure costs ONE QUARTER of server time instead of a fiscal year, and
#   * every quarter that lands is checkpointed and readable on its own, so the
#     year accumulates on disk instead of arriving all-or-nothing at the end.
# Run them with `--sequential`. Four quarters at max_inflight=1 is one job in
# flight, which is the one configuration 2026-09-01 did not test.
# ---------------------------------------------------------------------------

def fy_quarters(fy: int):
    """(key, start, end) for the four quarters of a US federal fiscal year.

    FY2023 = 2022-10-01..2023-09-30, so Q1 falls in the PREVIOUS calendar year.
    """
    return [
        (f"fy{fy}_q1", f"{fy-1}-10-01", f"{fy-1}-12-31"),
        (f"fy{fy}_q2", f"{fy}-01-01", f"{fy}-03-31"),
        (f"fy{fy}_q3", f"{fy}-04-01", f"{fy}-06-30"),
        (f"fy{fy}_q4", f"{fy}-07-01", f"{fy}-09-30"),
    ]


QUARTER_JOBS = [(k, a, b, ["procurement", "grant"])
                for fy in (2022, 2023, 2024)
                for k, a, b in fy_quarters(fy)]

# Quarters are part of JOBS so that `match`, `write_manifest` and `status` see
# them without a second code path. A quarter with no state is simply skipped.
#
# THE DOUBLE-COUNT GUARD: a quarter covers a window its full-year job also
# covers. If BOTH land, `match` reads both and `m45.identity_key` de-duplicates
# them against the live file exactly as it de-duplicates a re-pull - the second
# reader of a row finds the key already satisfied and drops it. That is the same
# mechanism `fy2025_refresh` relies on, so mixing grains is safe; it is not an
# invitation to pull both on purpose.
JOBS = JOBS + QUARTER_JOBS

CONTRACT_MARK = "Contracts_Subawards"
ASSIST_MARK = "Assistance_Subawards"
FFATA_FLOOR_FY = 2010

ROUTE_UEI = "usaspending_fsrs_pull"
ROUTE_PARENT = "usaspending_fsrs_parent_cluster"
ROUTE_NAME = "usaspending_fsrs_name_match"
POPULATION = "full_federal_subaward_universe"

NEW_COLS = ["subaward_amount_real2025", "deflator_factor_2025",
            "inflation_base_year"]

# COLUMNS THIS FILE CARRIES THAT ANOTHER SCRIPT OWNS (2026-09-01).
#
# `503_identity.py stamp` materialises `cedar_uid` onto every clean table that
# carries an entity column - for `subawards.csv` that column is
# `prime_native_tribe_id`, so `cedar_uid` is the PRIME's permanent entity id and
# is legitimately BLANK on the 41,354 rows whose only Native leg is the
# subawardee. It appeared in the header after this script last ran, and the
# `match` schema guard - correctly - refuses any column beyond the promoted
# schema that `append()` cannot fill, because such a column is blanked on every
# appended row.
#
# The answer is NOT to loosen the guard. `append()` now FILLS this column, using
# 503's OWN `register_map()` and `entity_col()` - imported, never re-implemented
# (standing rule 8). 503's own comment says `cedar_uid` is DERIVED and must be
# re-stamped rather than skipped, which is exactly what makes deriving it here
# safe: a later `503 stamp` recomputes the same value from the same register.
#
# A column added here must EITHER be computable by `append()` or be added to
# this map with the script that owns it. Nothing may be silently blanked.
STAMPED_COLS = {"cedar_uid": "code/503_identity.py"}

# THE SOURCE ROW KEY, CARRIED AT LAST (2026-09-01).
#
# `525_event_ids.py` registers subcontracting as the ONE dataset that genuinely
# lacks an event id and closes "diagnose the source extract first". Diagnosed,
# on zips already on disk, zero network:
#
#   FY2021  765,109 rows -> 765,109 distinct subaward_sam_report_id, 0 blank
#   FY2020  456,412 rows -> 456,412 distinct subaward_sam_report_id, 0 blank
#   FY2020 n FY2021 -> 0 overlap        (it is a UUID; unique across members
#                                        AND across fiscal years)
#
# `build_row` reads 26 of the extract's 121 columns and this was one of the 95
# it dropped. Same shape as `prime_contracts`, where 80,778 "duplicates" were
# distinct transactions whose `modification_number` the mapper never carried.
#
# WHAT IT KEYS, AND WHAT IT DOES NOT. It identifies a SAM subaward REPORT, not
# a subaward. Measured: `m45.identity_key` collides on 111,933 of 765,109
# FY2021 rows (14.6%), and the worst group is 93 rows that carry 93 distinct
# report ids whose `subaward_sam_report_month` runs 2022-08 -> 2025-01 on ONE
# $57,500 subaward with one action date and one subaward number. They are 93
# monthly RE-FILINGS. So:
#   * `duplicate_status == 'primary'` remains the correct filter for money, and
#   * a surrogate minted over this column must be named for the REPORT grain,
#     or it manufactures exactly the false distinctions 525 warns about.
# Carrying month and last-modified alongside is what makes that auditable
# instead of inferred - today `duplicate_status` cannot be checked against the
# source without re-reading a 1.2 GB zip.
#
# THE SEAM, STATED PLAINLY: only rows THIS SCRIPT writes carry these columns.
# Rows promoted by the 2026-08-05 route are blank, because there is no key to
# join them back on - which is the very defect being fixed. Backfilling them
# means re-running the mapper over the retained raw zips (all of FY2001-2021,
# FY2025, FY2026 are on disk) and is a separate job, owned by 45, not by a
# puller.
REPORT_COLS = ["subaward_sam_report_id", "subaward_sam_report_month",
               "subaward_sam_report_last_modified_date"]

# COLUMNS AN ENRICHER FILLS **AFTER** THIS SCRIPT, NOT DURING IT.
# Added 2026-09-02 by workstream SUBAWARD-FUNDING.
#
# `STAMPED_COLS` above means something precise - "append() computes this, using
# the owning script's own register" - and these five are NOT that. `append()`
# leaves them BLANK on a newly appended row and the owning script re-derives
# them for the whole file afterwards. Putting them in STAMPED_COLS would have
# been a lie inside a map, so they get their own.
#
# WHY THE GUARD MAY ACCEPT THEM ANYWAY, when its whole point is that a column
# append() cannot fill must not be silently blanked: they are not silent. Two
# gates catch a promotion that forgets them, both already wired:
#   * `py -3 code/910_subaward_report_id_backfill.py verify` fails on any blank
#     or colliding key;
#   * `512_build_dataset_contracts.py` re-validates the declared primary key
#     (source_dataset, subaward_source_record_id) against the FULL file on
#     every run and turns a blank into a release-blocking violation.
# The ordering is registered in `cedar_pipeline.KNOWN_ORDERINGS` so
# `build.py` and `62`'s enricher check both know about it.
#
# AFTER ANY PROMOTION, IN THIS ORDER:
#   py -3 code/910_subaward_report_id_backfill.py rescan   (index the new zips)
#   py -3 code/910_subaward_report_id_backfill.py apply
#   py -3 code/911_subaward_sub_leg_cedar_uid.py apply
#   py -3 code/81_build_passthrough_dataset.py             (projection)
POST_PROMOTION_COLS = {
    "subaward_sam_report_id_basis": "code/910_subaward_report_id_backfill.py",
    "subaward_source_record_id": "code/910_subaward_report_id_backfill.py",
    "subaward_source_record_id_basis": "code/910_subaward_report_id_backfill.py",
    "prime_cedar_uid": "code/911_subaward_sub_leg_cedar_uid.py",
    "sub_cedar_uid": "code/911_subaward_sub_leg_cedar_uid.py",
    # NOT MINE - registered here on the geography workstream's behalf,
    # 2026-09-02, because without it THIS SCRIPT CANNOT RUN AT ALL.
    # `871_promote_geo_keys_contracts.py` added ten `geo_*` columns to
    # subawards.csv at 01:14 today. They are not in NEW_COLS, STAMPED_COLS or
    # REPORT_COLS, so the guard above classed all ten as unfillable and
    # `match` raised SystemExit - correctly, and fatally for the FY2022-24
    # promotion that is mid-flight. 871 is an in-place enricher keyed on
    # `prime_award_unique_key`, which every row already carries, so it
    # recomputes cleanly for appended rows: it is a post-promotion enricher of
    # exactly this kind and belongs in this map. Geography workstream: if that
    # is wrong, this is the line to correct.
    "geo_prime_award_recipient_county_fips": "code/871_promote_geo_keys_contracts.py",
    "geo_prime_award_recipient_county_name": "code/871_promote_geo_keys_contracts.py",
    "geo_prime_award_recipient_state_fips": "code/871_promote_geo_keys_contracts.py",
    "geo_prime_award_pop_county_fips": "code/871_promote_geo_keys_contracts.py",
    "geo_prime_award_pop_county_name": "code/871_promote_geo_keys_contracts.py",
    "geo_prime_award_pop_state_fips": "code/871_promote_geo_keys_contracts.py",
    "geo_key_tier": "code/871_promote_geo_keys_contracts.py",
    "geo_key_basis": "code/871_promote_geo_keys_contracts.py",
    "geo_subawardee_county_gap_reason": "code/871_promote_geo_keys_contracts.py",
    "geo_built_date": "code/871_promote_geo_keys_contracts.py",
}


def log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')}] {msg}"
    print(line, flush=True)
    os.makedirs(LOGS, exist_ok=True)
    with open(LOGFILE, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


class HostRefusing(RuntimeError):
    """The host is refusing us. Distinct from a job failing."""


# ===========================================================================
# 1. HOST LOCK
# ===========================================================================

def read_lock() -> dict:
    if os.path.exists(HOSTLOCK):
        try:
            with open(HOSTLOCK, encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError):
            log("WARN host lock unreadable (mid-write?); not overwriting blindly")
            raise
    return {"host": HOST}


def write_lock(lk: dict) -> None:
    os.makedirs(LOGS, exist_ok=True)
    tmp = HOSTLOCK + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(lk, fh, indent=1)
    os.replace(tmp, HOSTLOCK)


# Which script talks to which host. A poller on `api.usaspending.gov` blocks
# this run under rule 1. A poller on `files.usaspending.gov` does NOT - that is
# a different host, as `114_pull_prime_archive.py` says in its own docstring -
# but this run's DOWNLOAD leg lands there, so it gates downloads instead.
API_HOST_SCRIPTS = ("40_pull_usaspending_subawards", "43_resume_subaward_pull",
                    "44_pull_contracts_transactions", "46_pull_funding_credit_types",
                    "30_wait_and_pull", "37_wait_then_pull",
                    "121_pull_subawards_api")
FILES_HOST_SCRIPTS = ("114_pull_prime_archive", "115_pull_assistance_archive")


def _proc_table():
    """Win32_Process with ParentProcessId. `ps aux` CANNOT see command lines on
    Windows - on 2026-08-05 it returned 0 with FOUR pullers live (rule 9)."""
    import subprocess
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process | Select-Object ProcessId,"
         "ParentProcessId,Name,CommandLine | ConvertTo-Json -Compress -Depth 3"],
        capture_output=True, text=True, timeout=180).stdout
    data = json.loads(out) if out.strip() else []
    return [data] if isinstance(data, dict) else data


# A POLLER IS A PROCESS THAT MAKES REQUESTS, NOT A PROCESS THAT MENTIONS A
# FILENAME. Measured 2026-08-12: matching on the script name alone counted this
# build's OWN `tail -f logs/121_pull_subawards_api.log` monitors - and the bash
# wrappers around them - as four live pollers, and stopped the run. A log
# watcher issues no HTTP. The process image must be a Python interpreter.
PY_IMAGES = ("python.exe", "pythonw.exe", "py.exe")


def _is_python_proc(p):
    return (p.get("Name") or "").lower() in PY_IMAGES


def _my_tree(data):
    """My own PID and every ancestor of it.

    `py.exe -3 code/121...` LAUNCHES `python.exe code/121...`, so a naive
    self-check on os.getpid() sees its own launcher, reports a peer, and stops
    the run. Measured on the first attempt of this build.
    """
    parent = {p.get("ProcessId"): p.get("ParentProcessId") for p in data}
    mine, pid = set(), os.getpid()
    while pid and pid not in mine:
        mine.add(pid)
        pid = parent.get(pid)
    return mine


def other_pollers():
    """Returns (api_peers, files_peers) or None if the check itself failed."""
    try:
        data = _proc_table()
    except Exception as e:                              # noqa: BLE001
        log(f"WARN could not enumerate processes ({type(e).__name__}); "
            f"NOT assuming the host is free")
        return None
    mine = _my_tree(data)
    api_peers, files_peers = [], []
    for p in data:
        cl = (p.get("CommandLine") or "")
        pid = p.get("ProcessId")
        if pid in mine or not cl or not _is_python_proc(p):
            continue
        if any(k in cl for k in API_HOST_SCRIPTS):
            api_peers.append((pid, cl.strip()))
        elif any(k in cl for k in FILES_HOST_SCRIPTS):
            files_peers.append((pid, cl.strip()))
    return api_peers, files_peers


FILES_BUSY_WAIT = 300
FILES_BUSY_MAX_WAITS = 12          # one hour, then defer to the next poll cycle


def files_host_busy():
    """True if a peer is actively pulling from `files.usaspending.gov`.

    This run's downloads land on that host, and FINDING 6 records that six
    ~2GB objects in twelve minutes edge-blocked it and stopped a peer. Our
    objects are ~100-200MB and arrive hours apart, but stacking them on top of
    an active archive puller is exactly the shape that caused the block.
    """
    peers = other_pollers()
    if peers is None:
        return True                # cannot see: assume busy, never assume free
    return bool(peers[1])


def claim(force=False) -> bool:
    peers = other_pollers()
    if peers is None and not force:
        log("STOP: process enumeration failed. A check that cannot observe what "
            "it claims to check is worse than no check.")
        return False
    api_peers, files_peers = peers
    if api_peers:
        for pid, cl in api_peers:
            log(f"OTHER POLLER LIVE on {HOST}  pid={pid}  {cl[:140]}")
        log("STOP: rule 1 - one poller per host, ever. Appending to the lock "
            "queue and exiting.")
        lk = read_lock()
        lk.setdefault("queue", []).append(
            "subaward FY2021-2024 + FY2020 procurement (code/121) - DEFERRED, "
            f"peer live at {datetime.now(timezone.utc).isoformat()}")
        write_lock(lk)
        return False
    for pid, cl in files_peers:
        log(f"NOTE peer on files.usaspending.gov (a DIFFERENT host, not rule 1) "
            f"pid={pid}  {cl[:120]}")
    if files_peers:
        log("Submissions and status polls go to api.usaspending.gov and are "
            "unaffected. DOWNLOADS land on files.usaspending.gov and are gated "
            "on that peer going quiet; tokens are checkpointed, so waiting "
            "costs nothing.")

    lk = read_lock()
    # Drop this script's own stale DEFERRED note - the first attempt of this
    # build read its own `py.exe` launcher as a peer and deferred to itself.
    lk["queue"] = [q for q in (lk.get("queue") or [])
                   if not (isinstance(q, str) and "code/121" in q
                           and "DEFERRED" in q)]
    prev = lk.get("holder")
    lk["previous_holder"] = prev
    lk["holder"] = {
        "script": "code/121_pull_subawards_api.py pull",
        "pid": os.getpid(),
        "claimed": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "jobs": [j[0] for j in JOBS],
        "submit_deadline_utc": datetime.fromtimestamp(
            SUBMIT_DEADLINE, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "collect_deadline_utc": datetime.fromtimestamp(
            COLLECT_DEADLINE, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    lk["deferring"] = False
    lk["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lk["last_updated_by"] = (
        "code/121_pull_subawards_api.py - subaward FY2021-2024 + FY2020 "
        "procurement re-pull. Probed 2026-08-12: reference GET 200 in 0.44s, "
        "download/status 404-for-unknown-file in 0.41s (a valid answer shape). "
        "The 2026-08-07/08 edge block has cleared.")
    # UNAMBIGUOUS STATUS FIELDS. `any_success: false` written after skipping
    # work already on disk once read to a peer as "the host refused" (rule,
    # PULL_DISCIPLINE 2026-08-08). These three cannot be misread.
    lk["downloaded_this_run"] = []
    lk["already_on_disk_skipped"] = []
    lk["refused_by_host"] = []
    lk["block_attribution_history"] = lk.get("block_attribution_history") or [
        {"when": "2026-08-08T00:55Z", "host": "files.usaspending.gov",
         "cause": "code/115_pull_assistance_archive.py pulled six ~2GB objects "
                  "in twelve minutes with a 15s inter-object pause",
         "effect": "edge block; a peer agent sharing the IP was refused"},
        {"when": "2026-08-05T17:17Z", "host": "api.usaspending.gov",
         "cause": "four concurrent pollers, each retrying on a 300s metronome",
         "effect": "per-IP cooldown, cleared ~62 minutes after traffic dropped"},
    ]
    write_lock(lk)
    log(f"HOST LOCK CLAIMED for {HOST} (pid {os.getpid()}); no other poller live")
    return True


def lock_update(**fields) -> None:
    try:
        lk = read_lock()
    except Exception:                                   # noqa: BLE001
        return
    for k, v in fields.items():
        lk[k] = v
    lk["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    write_lock(lk)


def release(downloaded, skipped, refused, note="") -> None:
    try:
        lk = read_lock()
    except Exception:                                   # noqa: BLE001
        return
    if (lk.get("holder") or {}).get("pid") == os.getpid():
        lk["holder"] = None
    lk["downloaded_this_run"] = sorted(downloaded)
    lk["already_on_disk_skipped"] = sorted(skipped)
    lk["refused_by_host"] = sorted(refused)
    lk["status_field_reading"] = (
        "downloaded_this_run = objects actually fetched now. "
        "already_on_disk_skipped = present, no request made. "
        "refused_by_host = the host declined. "
        "downloaded_this_run EMPTY with refused_by_host EMPTY is NOT a block - "
        "it means there was nothing to do.")
    lk["released"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lk["released_by"] = "code/121_pull_subawards_api.py" + (f" - {note}" if note else "")
    lk["last_updated"] = lk["released"]
    lk["last_updated_by"] = lk["released_by"]
    # Drain this build's own item from the shared queue; leave everyone else's.
    lk["queue"] = [q for q in (lk.get("queue") or [])
                   if not (isinstance(q, str) and "subaward FY2021-2024" in q
                           and "DEFERRED" not in q)
                   and not (isinstance(q, str) and "subaward FY2020 contracts" in q)]
    write_lock(lk)
    log("HOST LOCK RELEASED")


# ===========================================================================
# 2. HTTP - and the distinction that matters
# ===========================================================================

def _request(url, payload=None, timeout=300):
    """Returns (status, seconds, body_or_detail).

    status 0 == TRANSPORT FAILURE == stop-work. A 404 is a fact about the
    object; a 0 is a fact about the host. `head()` returning 0 for both once
    made a pull race through 19 years in five seconds against a refusing host.
    """
    t0 = time.time()
    try:
        if payload is None:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
        else:
            req = urllib.request.Request(
                url, data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json", "User-Agent": UA},
                method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, time.time() - t0, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, time.time() - t0, e.read().decode("utf-8", "replace")[:600]
    except (urllib.error.URLError, socket.timeout, ConnectionError,
            OSError) as e:
        return 0, time.time() - t0, f"{type(e).__name__}: {str(e)[:200]}"


def classify(status, secs, detail):
    """The three failure shapes, which call for opposite responses."""
    if status == 0:
        shape = "EDGE_BLOCK" if secs < 1.0 else "TRANSPORT_FAILURE"
        return shape, f"status=0 ({shape}) in {secs:.2f}s: {detail}"
    if status == 429:
        return "THROTTLE", f"HTTP 429 in {secs:.2f}s"
    if 500 <= status < 600:
        shape = "EDGE_BLOCK" if secs < 1.0 else "SERVER_ERROR"
        return shape, f"HTTP {status} ({shape}) in {secs:.2f}s: {detail[:200]}"
    if 400 <= status < 500:
        return "CLIENT_ERROR", f"HTTP {status} in {secs:.2f}s: {detail[:300]}"
    return "OK", ""


def call(url, payload=None, what="request", timeout=300, tries=BACKOFF_TRIES,
         deadline=None):
    """Bounded exponential backoff with a HARD RUN STOP.

    The deadline is checked before each attempt AND before each sleep, because
    a 30-minute sleep otherwise carries you past it anyway.
    """
    deadline = deadline if deadline is not None else SUBMIT_DEADLINE
    last = ""
    for i in range(1, tries + 1):
        if time.time() > deadline:
            raise HostRefusing(
                f"{what}: RUN DEADLINE reached before attempt {i} "
                f"({(time.time()-RUN_START)/3600:.2f}h into the run). "
                f"Stopping rather than probing on. Last: {last}")
        status, secs, detail = _request(url, payload, timeout)
        shape, msg = classify(status, secs, detail)
        if shape == "OK":
            try:
                return json.loads(detail)
            except json.JSONDecodeError:
                return {"_raw": detail}
        last = msg
        if shape == "CLIENT_ERROR" and status not in (408, 429):
            # A fact about the request, not about the host. Do not retry.
            raise RuntimeError(f"{what}: {msg}")
        log(f"  {what}: {msg}")
        wait = min(BACKOFF_BASE * (2 ** (i - 1)), BACKOFF_MAX)
        if time.time() + wait > deadline:
            raise HostRefusing(
                f"{what}: a {wait:.0f}s backoff would cross the run deadline. "
                f"Stopping. Last: {last}")
        log(f"  {what}: backoff {i}/{tries}, sleeping {wait:.0f}s")
        time.sleep(wait)
    raise HostRefusing(f"{what}: exhausted {tries} attempts. Last: {last}")


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ===========================================================================
# 3. STATE - checkpointed BEFORE the first request, not after the last
# ===========================================================================

def load_state() -> dict:
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as fh:
            return json.load(fh)
    return {"jobs": {}, "created": datetime.now(timezone.utc).isoformat()}


def save_state(st: dict) -> None:
    os.makedirs(RAW, exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(st, fh, indent=1)
    os.replace(tmp, STATE)


def build_payload(start, end, sub_types):
    return {
        "filters": {
            "sub_award_types": sub_types,
            "date_type": "action_date",
            "date_range": {"start_date": start, "end_date": end},
        },
        "file_format": "csv",
    }


def staged(rec) -> bool:
    """On disk AND carrying data.

    An object that is header-only is on disk and is NOT staged data. Counting
    it as staged is exactly how FY2020 came to hold zero contract subawards
    while every report said the pull had succeeded.
    """
    return bool(rec and rec.get("_local_file")
                and os.path.exists(os.path.join(ROOT, rec["_local_file"]))
                and not rec.get("_empty_object"))


# ===========================================================================
# 4. PULL
# ===========================================================================

def probe() -> bool:
    status, secs, detail = _request(PROBE_EP, timeout=60)
    shape, msg = classify(status, secs, detail)
    log(f"PROBE {PROBE_EP} -> HTTP {status} in {secs:.2f}s [{shape}]")
    if shape != "OK":
        log(f"PROBE REFUSED: {msg}")
        return False
    return True


def diagnose() -> int:
    """Three cheap 2-day jobs that separate three different explanations.

    Six subaward jobs - five full fiscal years and one two-day canary - were all
    ACCEPTED and all came back `failed / "An error occurred."` on 2026-08-12.
    Size is ruled out (two days failed the same way as a year) and request rate
    is ruled out (the canary was one submission into a host answering 200). Three
    explanations remain, and they have opposite implications for the next agent:

      A. the whole bulk_download service is generating nothing
         -> nobody's pull works today; wait, do not redesign anything
      B. only `sub_award_types` is broken; prime downloads still generate
         -> a source-side FSRS defect; report it, and the prime backfills can
            still proceed
      C. only the FY2021-2024 window is broken
         -> the remaining years are still retrievable now

    Each probe is a two-day range, which generated in 37 seconds on this
    endpoint on 2026-08-05. Submissions are spaced; nothing here is a full year.
    """
    st = load_state()
    st.setdefault("jobs", {})
    if not probe():
        log("diagnose: probe refused. STOP-WORK.")
        return 2
    trials = [
        ("diag_sub_2021", {"sub_award_types": ["procurement", "grant"]},
         "2021-10-01", "2021-10-02",
         "subawards inside the missing window"),
        ("diag_sub_2015", {"sub_award_types": ["procurement", "grant"]},
         "2015-10-01", "2015-10-02",
         "subawards in a year we ALREADY hold - isolates the window"),
        ("diag_prime_2021", {"prime_award_types": ["A", "B", "C", "D"]},
         "2021-10-01", "2021-10-02",
         "PRIME awards, same window - isolates sub_award_types"),
    ]
    results = {}
    for i, (key, filt, start, end, why) in enumerate(trials):
        if i:
            log(f"  spacing {SUBMIT_SPACING}s")
            time.sleep(SUBMIT_SPACING)
        payload = {"filters": dict(filt, date_type="action_date",
                                   date_range={"start_date": start,
                                               "end_date": end}),
                   "file_format": "csv"}
        log(f"DIAG {key}: {why}")
        try:
            resp = call(API, payload, f"submit {key}", timeout=300, tries=3)
        except (HostRefusing, RuntimeError) as e:
            results[key] = f"SUBMIT_REFUSED: {str(e)[:200]}"
            log(f"  {key} -> {results[key]}")
            continue
        fn = resp.get("file_name")
        if not fn:
            results[key] = f"NO_FILE_NAME: {str(resp)[:200]}"
            log(f"  {key} -> {results[key]}")
            continue
        st["jobs"][key] = {"file_name": fn, "status": "accepted",
                           "_payload": payload, "_date_range": [start, end],
                           "_diagnostic": why,
                           "_submitted": datetime.now(timezone.utc).isoformat()}
        save_state(st)
        log(f"  {key} accepted -> {fn}")
        outcome = "TIMEOUT_INCONCLUSIVE"
        for _ in range(12):
            time.sleep(30)
            try:
                meta = poll_one(key, st, COLLECT_DEADLINE)
            except HostRefusing as e:
                outcome = f"POLL_REFUSED: {str(e)[:150]}"
                break
            s = meta.get("status")
            if s == "finished":
                outcome = (f"FINISHED rows={meta.get('total_rows')} "
                           f"secs={meta.get('seconds_elapsed')}")
                break
            if s == "failed":
                outcome = f"FAILED_SERVER_SIDE: {meta.get('message')!r}"
                break
        results[key] = outcome
        log(f"  {key} -> {outcome}")

    log("DIAGNOSIS " + json.dumps(results, indent=1))
    sub21 = results.get("diag_sub_2021", "")
    sub15 = results.get("diag_sub_2015", "")
    prime = results.get("diag_prime_2021", "")
    if "FINISHED" in prime and "FAILED" in sub21:
        verdict = ("B - PRIME downloads generate and SUBAWARD downloads do not. "
                   "A source-side FSRS defect on USAspending, not our rate and "
                   "not our payload.")
    elif "FAILED" in prime and "FAILED" in sub21:
        verdict = ("A - the whole bulk_download service is generating nothing "
                   "today. Nobody's pull works; wait, do not redesign.")
    elif "FINISHED" in sub15 and "FAILED" in sub21:
        verdict = ("C - subaward generation works for FY2015 and fails for the "
                   "FY2021 window. The defect is window-specific.")
    elif "FINISHED" in sub21:
        verdict = ("RECOVERED - subaward generation is working again. Run "
                   "`pull --sequential`.")
    else:
        verdict = "INCONCLUSIVE - see the per-trial outcomes above."
    log("VERDICT: " + verdict)
    with open(os.path.join(REVIEW, f"_121_diagnosis_{TODAY}.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"run": datetime.now(timezone.utc).isoformat(),
                   "trials": {k: v for k, v in results.items()},
                   "verdict": verdict}, fh, indent=1)
    return 0


def waitclear(deadline=None) -> bool:
    """ONE poller, exponential backoff, hard deadline. Probes the CHEAPEST
    endpoint the host offers - never the real job (rule: probe cheap).

    This is armed only after the peer archive puller has exhausted its own
    backoff. Two backoff loops against one refusing IP is the 2026-08-05
    failure - four agents quadrupling the probe rate against a host that was
    blocking them FOR probe rate.
    """
    deadline = deadline if deadline is not None else SUBMIT_DEADLINE
    wait = BACKOFF_BASE
    n = 0
    while True:
        if time.time() > deadline:
            log(f"waitclear: RUN DEADLINE reached after {n} probes "
                f"({(time.time()-RUN_START)/3600:.2f}h). The edge has not "
                f"cleared. STOPPING rather than probing all night - a block is "
                f"a finding, not a failure.")
            return False
        n += 1
        status, secs, detail = _request(PROBE_EP, timeout=60)
        shape, msg = classify(status, secs, detail)
        log(f"waitclear probe {n}: HTTP {status} in {secs:.2f}s [{shape}]")
        if shape == "OK":
            log(f"EDGE CLEARED after {n} probes, "
                f"{(time.time()-RUN_START)/60:.0f} minutes into the run.")
            return True
        if time.time() + wait > deadline:
            log(f"waitclear: a {wait:.0f}s backoff would cross the deadline. "
                f"Stopping. Last: {msg}")
            return False
        log(f"  still refusing; sleeping {wait:.0f}s")
        time.sleep(wait)
        wait = min(wait * 2, BACKOFF_MAX)


def peer_archive_live() -> bool:
    p = other_pollers()
    return True if p is None else bool(p[1])


def auto() -> int:
    """The whole chain, unattended and resumable:
    wait for the peer to stop -> wait for the edge -> canary -> sequential pull.
    """
    # Do not probe while the peer is still backing off against the same IP.
    waited = 0
    while peer_archive_live() and waited < 3600:
        log(f"auto: peer archive puller still live on the shared IP; not "
            f"probing (waited {waited}s). ZERO requests issued.")
        time.sleep(300)
        waited += 300
    if not claim():
        return 3
    # THE PROBING LEG IS BOUNDED AT 2h, ALWAYS, whatever SUBMIT_HOURS is set to.
    # PULL_DISCIPLINE's "stop at ~2 hours" is a rule about probing a REFUSING
    # host, and that is exactly this loop. SUBMIT_HOURS may be raised to give
    # the sequential submission leg room on a HEALTHY host - a different
    # activity with a different justification - and must never silently extend
    # how long we probe a host that is saying no.
    probe_deadline = RUN_START + 2 * 3600
    if not waitclear(deadline=probe_deadline):
        release([], [], [j[0] for j in JOBS], "edge never cleared")
        return 2
    rc = canary()
    if rc != 0:
        log(f"auto: canary returned {rc}; NOT submitting full-year jobs.")
        release([], [], [j[0] for j in JOBS],
                f"canary rc={rc} - fleet unhealthy or host refusing")
        return rc
    return pull(do_claim=False, sequential=True)


def canary() -> int:
    """ONE two-day job. The cheapest possible test that the download fleet works.

    MEASURED 2026-08-12, and the reason this exists: five full-year jobs were
    submitted 180s apart, ALL FIVE were accepted with tokens, and all five came
    back `status: failed / "An error occurred."` within 8-14 minutes. The host
    was answering HTTP 200 the whole time. **An accepted token is not a working
    job**, and finding that out five full-year jobs at a time is expensive for
    us and for the host.

    A two-day range generated in 37 seconds on this endpoint on 2026-08-05
    (fy2001 probe). If the fleet is unhealthy this fails in about a minute and
    costs one submission instead of five.
    """
    st = load_state()
    st.setdefault("jobs", {})
    if not probe():
        log("canary: probe refused. STOP-WORK. Nothing submitted.")
        return 2
    key = "canary_2day"
    start, end, types = "2021-10-01", "2021-10-02", ["procurement", "grant"]
    try:
        submit_one(key, start, end, types, st)
    except HostRefusing as e:
        log(f"canary REFUSED at submission: {e}")
        return 2
    for _ in range(20):
        time.sleep(30)
        try:
            meta = poll_one(key, st, COLLECT_DEADLINE)
        except HostRefusing as e:
            log(f"canary REFUSED while polling: {e}")
            return 2
        s = meta.get("status")
        log(f"  canary ...{s} rows={meta.get('total_rows')}")
        if s == "finished":
            log("CANARY PASSED: the bulk_download fleet is generating files. "
                "Full-year jobs may be submitted, ONE AT A TIME "
                "(`pull --sequential`).")
            return 0
        if s == "failed":
            log(f"CANARY FAILED server-side: {meta.get('message')!r}. "
                "The host answers HTTP 200 and its download workers do not "
                "produce files. Submitting full-year jobs now would fail the "
                "same way and add load. STOP.")
            return 4
    log("canary: still generating after 10 minutes; treat as inconclusive.")
    return 5


def submit_one(key, start, end, sub_types, st):
    payload = build_payload(start, end, sub_types)
    log(f"SUBMIT {key}: {start}..{end} sub_award_types={sub_types}")
    resp = call(API, payload, f"submit {key}", timeout=300)
    fn = resp.get("file_name")
    if not fn:
        raise RuntimeError(f"{key}: no file_name in response: {str(resp)[:400]}")
    st["jobs"][key] = {
        "_chunk_key": key,
        "_date_range": [start, end],
        "_sub_award_types": sub_types,
        "_endpoint": API,
        "_payload": payload,
        "file_name": fn,
        "status": "accepted",
        "_submitted": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    save_state(st)              # checkpoint the TOKEN before anything else
    log(f"  {key} ACCEPTED -> {fn}  (token checkpointed; rule 5: never re-submit)")
    return fn


def poll_one(key, st, deadline):
    fn = st["jobs"][key]["file_name"]
    url = STATUS_EP + "?file_name=" + urllib.parse.quote(fn)
    meta = call(url, None, f"status {key}", timeout=180, tries=BACKOFF_TRIES,
                deadline=deadline)
    st["jobs"][key].update({k: v for k, v in meta.items() if not k.startswith("_")})
    save_state(st)
    return meta


def wait_for_files_host(key) -> bool:
    """Bounded wait for the archive puller to go quiet. Returns False to DEFER.

    Deferring is free: the generated object stays retrievable by its
    `file_name` and the token is already on disk, so the next poll cycle picks
    it up. This is the opposite of re-submitting.
    """
    for i in range(FILES_BUSY_MAX_WAITS):
        if not files_host_busy():
            if i:
                log(f"  files.usaspending.gov quiet after {i * FILES_BUSY_WAIT}s; "
                    f"downloading {key}")
            return True
        if time.time() > COLLECT_DEADLINE:
            log(f"  {key}: collect deadline reached while waiting for the "
                f"archive puller. Token is on disk; resume with `collect`.")
            return False
        log(f"  {key}: archive puller live on files.usaspending.gov; waiting "
            f"{FILES_BUSY_WAIT}s ({i+1}/{FILES_BUSY_MAX_WAITS})")
        time.sleep(FILES_BUSY_WAIT)
    log(f"  {key}: files host still busy after "
        f"{FILES_BUSY_MAX_WAITS * FILES_BUSY_WAIT // 60}m. DEFERRING this "
        f"download to a later cycle - the token is checkpointed and nothing "
        f"is lost. NOT re-submitted (rule 5).")
    return False


# ===========================================================================
# THE THIRD FAILURE MODE: "FINISHED" WITH NO DATA ROWS (measured 2026-09-02)
# ===========================================================================
# This endpoint fails in three distinct ways and only two of them look like
# failure:
#
#   1. accepted, then `status: failed / "An error occurred."`   - visible
#   2. accepted, generating, then killed mid-build              - visible
#   3. accepted, `status: finished`, HTTP 200, and the object   - INVISIBLE
#      contains NOTHING BUT HEADER LINES
#
# Mode 3 measured on `fy2023_q4` (2023-07-01..2023-09-30): server reported
# `finished` in 80s with `total_rows=0`, and the 1,889-byte zip held a
# 4,144-byte contracts member and a 3,992-byte assistance member, both one
# header line and zero data rows. Its own neighbours are 207,459 (Q1) and
# 153,650 (Q2) rows, so zero is not a fact about the world.
#
# **4,144 bytes is a signature, not a coincidence.** The FY2020 contracts member
# retrieved on 2026-08-06 is 4,144 bytes for the same reason, and THAT is why
# `subawards.csv` holds zero FSRS contract subawards for FY2020 against 5,868
# in FY2019 and 6,484 in FY2021. The defect has been in this dataset for a
# month wearing the costume of a successful pull.
#
# `docs/PULL_DISCIPLINE.md` already states the principle for a different
# endpoint - "an empty result is not evidence of absence" - and the same
# sentence applies here. An empty object is recorded as a PULL FAILURE, never
# as a measurement, and never silently read as data.

def zip_data_rows(path):
    """(has_data, {member: has_data}) - does any CSV member have a row past the
    header? Cheap: reads two lines per member, never the whole file."""
    detail = {}
    try:
        with zipfile.ZipFile(path) as z:
            for i in z.infolist():
                if not i.filename.lower().endswith(".csv"):
                    continue
                with z.open(i) as fh:
                    txt = io.TextIOWrapper(fh, encoding="utf-8-sig")
                    txt.readline()                      # header
                    detail[i.filename] = bool(txt.readline().strip())
    except (zipfile.BadZipFile, OSError) as e:          # noqa: BLE001
        return False, {"_error": f"{type(e).__name__}: {e}"}
    return (any(detail.values()), detail)


def download_one(key, meta, st):
    url = meta.get("file_url")
    if not url:
        raise RuntimeError(f"{key}: finished job has no file_url")
    fname = os.path.basename(urllib.parse.urlparse(url).path)
    dest = os.path.join(RAW, fname)
    os.makedirs(RAW, exist_ok=True)
    log(f"DOWNLOAD {key} <- {url}")
    t0 = time.time()
    tmp = dest + ".part"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=3600) as r, open(tmp, "wb") as fh:
            n = 0
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                fh.write(chunk)
                n += len(chunk)
        os.replace(tmp, dest)
    except Exception as e:                              # noqa: BLE001
        if os.path.exists(tmp):
            os.remove(tmp)
        raise HostRefusing(f"download {key}: {type(e).__name__}: {str(e)[:200]}") from e
    # magic bytes, not just "the file has content" - a 404 body can be non-empty
    with open(dest, "rb") as fh:
        if fh.read(2) != b"PK":
            raise RuntimeError(f"{key}: downloaded object is not a zip archive")
    has_data, members = zip_data_rows(dest)
    st["jobs"][key].update({
        "_member_has_data": members,
        "_empty_object": not has_data,
        "_local_file": os.path.relpath(dest, ROOT).replace("\\", "/"),
        "_bytes": os.path.getsize(dest),
        "_sha256": sha256(dest),
        "_download_seconds": round(time.time() - t0, 1),
        "_retrieved": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "_http_status": 200,
        "file_url": url,
    })
    save_state(st)
    log(f"CHECKPOINT {key} -> {st['jobs'][key]['_local_file']} "
        f"({st['jobs'][key]['_bytes']:,} bytes in "
        f"{st['jobs'][key]['_download_seconds']}s)")
    if not has_data:
        log(f"!! EMPTY OBJECT {key}: the server reported FINISHED and the "
            f"downloaded zip contains ONLY HEADER LINES - {members}. This is a "
            f"PULL FAILURE, not a measurement, and it is NOT evidence that the "
            f"window has no subawards. Same signature as the FY2020 contracts "
            f"member (4,144 bytes). The object is kept as evidence; `staged()` "
            f"treats it as NOT staged so `match` will not read it as data.")
    else:
        empty = [m for m, ok in members.items() if not ok]
        if empty:
            log(f"!! PARTIAL OBJECT {key}: member(s) with no data rows: "
                f"{empty}. The other member(s) have data. Check this against "
                f"neighbouring windows before believing the empty one.")


def pull(only=None, do_claim=True, sequential=False, inflight_cap=None) -> int:
    # SEQUENTIAL is the post-2026-08-12 default posture. Five concurrent
    # full-year jobs were all accepted and all failed server-side; one job in
    # flight is slower and cannot produce that outcome five times over.
    #
    # `--max-inflight N` (2026-09-01) exists because the posture had only two
    # settings and the evidence needs a third. Measured that day: at THREE
    # concurrent full-year jobs the second and third failed together while the
    # first kept generating; at ONE (the canary, and fy2021 on 2026-08-26) jobs
    # complete. TWO has never been tried. An explicit cap lets the next run
    # narrow that down instead of choosing between "known bad" and "very slow".
    # It is a ceiling on ACCEPTED SERVER JOBS, not on our request rate - the
    # request rate is one cheap status GET per job per POLL_EVERY either way.
    max_inflight = (int(inflight_cap) if inflight_cap
                    else (1 if sequential else MAX_INFLIGHT))
    log(f"pull: max_inflight={max_inflight} "
        f"({'SEQUENTIAL' if sequential else 'parallel'})")
    os.makedirs(RAW, exist_ok=True)
    if do_claim and not claim():
        return 3
    st = load_state()
    st.setdefault("jobs", {})
    save_state(st)                                      # checkpoint before request 1

    todo = [j for j in JOBS if (not only or j[0] in only)]
    downloaded, skipped, refused = [], [], []
    for key, *_ in todo:
        if staged(st["jobs"].get(key)):
            skipped.append(key)
    log(f"PULL: {len(todo)} jobs; already on disk: {skipped or 'none'}")

    if not probe():
        log("STOP-WORK: the cheapest endpoint the host offers refused us. "
            "No job was submitted. This is a finding, not a failure.")
        release(downloaded, skipped, [k for k, *_ in todo], "probe refused")
        return 2

    pending = [j for j in todo if not staged(st["jobs"].get(j[0]))]
    inflight = []           # keys accepted, not yet downloaded
    accepted_any = False
    fatal = None

    try:
        while pending or inflight:
            # ---- submit, up to MAX_INFLIGHT, spaced ---------------------
            while pending and len(inflight) < max_inflight:
                if time.time() > SUBMIT_DEADLINE:
                    log("SUBMIT DEADLINE reached; no further jobs will be "
                        "submitted this run. Outstanding tokens are on disk.")
                    pending = []
                    break
                key, start, end, types = pending.pop(0)
                rec = st["jobs"].get(key)
                if rec and rec.get("_empty_object"):
                    # A header-only object is a build that produced nothing.
                    # Rule 5 protects COMPLETED SERVER WORK; an empty file is
                    # not that. Re-submit ONCE, keep the dead object and its
                    # token as evidence, and never loop: if the second attempt
                    # is also empty, that is a finding to report, not a reason
                    # for a third request.
                    tries_done = int(rec.get("_empty_resubmits") or 0)
                    if tries_done >= 1:
                        log(f"  {key}: came back HEADER-ONLY twice. NOT "
                            f"re-submitting a third time. Report it as an "
                            f"unresolved empty window - a documented boundary "
                            f"beats another request.")
                        refused.append(key)
                        continue
                    log(f"  {key}: previous object was HEADER-ONLY "
                        f"({rec.get('_member_has_data')}); re-submitting once. "
                        f"An empty build is not completed server work.")
                    st["jobs"][key + "_empty_" + (rec.get("file_name") or "?")[:40]] = rec
                    rec = dict(rec)
                    rec["_empty_resubmits"] = tries_done + 1
                    st["jobs"][key] = {"_empty_resubmits": tries_done + 1}
                    save_state(st)
                    rec = None
                if rec and rec.get("status") == "failed":
                    # A FAILED job is not completed server work. Rule 5 forbids
                    # discarding a job the server is still generating; it does
                    # not require honouring a corpse. The dead token is kept in
                    # _state.json as evidence and a fresh job is submitted.
                    log(f"  {key}: previous token {rec.get('file_name')} came "
                        f"back FAILED ({rec.get('message')!r}); re-submitting. "
                        f"Rule 5 does not bind on a failed job.")
                    st["jobs"][key + "_failed_" + rec.get("file_name", "?")[:40]] = rec
                    rec = None
                if rec and rec.get("file_name") and not staged(rec):
                    # RULE 5. The server already accepted this; recover, never
                    # re-submit - a re-submission discards completed server work
                    # and costs the queue position.
                    log(f"RECOVER {key}: token {rec['file_name']} already "
                        f"accepted; polling instead of re-submitting")
                    inflight.append(key)
                    accepted_any = True
                    continue
                try:
                    submit_one(key, start, end, types, st)
                except HostRefusing as e:
                    log(f"REFUSED submitting {key}: {e}")
                    refused.append(key)
                    # STOP ON FIRST REFUSAL WHEN NOTHING HAS SUCCEEDED.
                    if not accepted_any:
                        raise
                    continue
                inflight.append(key)
                accepted_any = True
                if pending and len(inflight) < max_inflight:
                    log(f"  spacing {SUBMIT_SPACING}s before the next submission")
                    time.sleep(SUBMIT_SPACING)

            if not inflight:
                break

            # ---- poll the accepted jobs --------------------------------
            time.sleep(POLL_EVERY)
            if time.time() > COLLECT_DEADLINE:
                log(f"COLLECT DEADLINE ({COLLECT_HOURS}h) reached with "
                    f"{len(inflight)} job(s) still generating: {inflight}. "
                    f"Their tokens are in _state.json; resume with "
                    f"`py -3 code/121_pull_subawards_api.py collect`. "
                    f"NEVER re-submit them.")
                break
            for key in list(inflight):
                try:
                    meta = poll_one(key, st, COLLECT_DEADLINE)
                except HostRefusing as e:
                    log(f"REFUSED polling {key}: {e}")
                    refused.append(key)
                    inflight.remove(key)
                    if not downloaded:
                        raise
                    continue
                s = meta.get("status")
                if s == "finished":
                    log(f"  {key} FINISHED rows={meta.get('total_rows')} "
                        f"cols={meta.get('total_columns')} "
                        f"size={meta.get('total_size')}KB "
                        f"elapsed={meta.get('seconds_elapsed')}s")
                    if not wait_for_files_host(key):
                        continue          # stays inflight; retried next cycle
                    try:
                        download_one(key, meta, st)
                        downloaded.append(key)
                    except HostRefusing as e:
                        log(f"REFUSED downloading {key}: {e}")
                        refused.append(key)
                        inflight.remove(key)
                        if not downloaded:
                            raise
                        continue
                    inflight.remove(key)
                    if pending or inflight:
                        log(f"  pacing {SUBMIT_SPACING}s after a download")
                        time.sleep(SUBMIT_SPACING)
                elif s == "failed":
                    log(f"  {key} SERVER-SIDE JOB FAILED: {meta.get('message')}")
                    st["jobs"][key]["_failed"] = meta.get("message")
                    save_state(st)
                    inflight.remove(key)
                else:
                    el = int(time.time() - RUN_START)
                    log(f"  {key} ...{s} rows_so_far={meta.get('total_rows')} "
                        f"(run {el//60}m)")
    except HostRefusing as e:
        fatal = str(e)
        log(f"STOP-WORK: {fatal}")
        log("Nothing had landed, so the HOST is refusing, not the object. "
            "Trying the remaining jobs is more ways to learn the same fact.")
    finally:
        lock_update(downloaded_this_run=sorted(set(downloaded)),
                    already_on_disk_skipped=sorted(set(skipped)),
                    refused_by_host=sorted(set(refused)))

    write_manifest(st)
    log(f"PULL COMPLETE. downloaded_this_run={sorted(set(downloaded))} "
        f"already_on_disk_skipped={sorted(set(skipped))} "
        f"refused_by_host={sorted(set(refused))}")
    release(set(downloaded), set(skipped), set(refused),
            fatal or "pull finished")
    return 2 if (fatal and not downloaded) else 0


def collect() -> int:
    """Resume accepted tokens WITHOUT re-submitting anything."""
    st = load_state()
    st.setdefault("jobs", {})
    outstanding = [k for k, r in st["jobs"].items()
                   if r.get("file_name") and not staged(r)]
    if not outstanding:
        log("collect: no outstanding tokens. Nothing to do. "
            "(This is NOT a block - see status_field_reading in the host lock.)")
        return 0
    if not probe():
        log("STOP-WORK: probe refused; accepted tokens remain on disk.")
        return 2
    downloaded, refused = [], []
    while outstanding and time.time() < COLLECT_DEADLINE:
        for key in list(outstanding):
            try:
                meta = poll_one(key, st, COLLECT_DEADLINE)
            except HostRefusing as e:
                log(f"REFUSED polling {key}: {e}")
                refused.append(key)
                outstanding.remove(key)
                continue
            if meta.get("status") == "finished":
                if not wait_for_files_host(key):
                    continue
                try:
                    download_one(key, meta, st)
                    downloaded.append(key)
                except HostRefusing as e:
                    log(f"REFUSED downloading {key}: {e}")
                    refused.append(key)
                outstanding.remove(key)
                if outstanding:
                    time.sleep(SUBMIT_SPACING)
            elif meta.get("status") == "failed":
                log(f"  {key} SERVER-SIDE JOB FAILED: {meta.get('message')}")
                outstanding.remove(key)
            else:
                log(f"  {key} ...{meta.get('status')} "
                    f"rows_so_far={meta.get('total_rows')}")
        if outstanding:
            time.sleep(POLL_EVERY)
    write_manifest(st)
    lock_update(downloaded_this_run=sorted(set(downloaded)),
                refused_by_host=sorted(set(refused)))
    log(f"COLLECT COMPLETE. downloaded={downloaded} refused={refused} "
        f"still_outstanding={outstanding}")
    return 0


def write_manifest(st=None) -> None:
    st = st or load_state()
    os.makedirs(RAW, exist_ok=True)
    cols = ["local_file", "chunk_key", "source_url", "endpoint",
            "date_range_start", "date_range_end", "sub_award_types", "date_type",
            "submission_http_status", "server_job_status", "server_job_message",
            "outcome_reading", "rows_reported_by_server",
            "columns", "bytes", "sha256", "zip_members", "member_bytes",
            "rows_read_locally", "submitted_utc", "retrieved_utc",
            "server_seconds_elapsed", "fetched_date"]
    with open(MANIFEST, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for key, start, end, types in JOBS:
            m = st["jobs"].get(key)
            if not m:
                continue
            members, mbytes, nrows = "", "", ""
            lf = m.get("_local_file")
            if lf and os.path.exists(os.path.join(ROOT, lf)):
                try:
                    with zipfile.ZipFile(os.path.join(ROOT, lf)) as z:
                        infos = [i for i in z.infolist()
                                 if i.filename.lower().endswith(".csv")]
                        members = "|".join(i.filename for i in infos)
                        mbytes = "|".join(str(i.file_size) for i in infos)
                except zipfile.BadZipFile:
                    members = "BAD_ZIP"
                nrows = m.get("_rows_read_locally", "")
            # THREE DIFFERENT FACTS, NEVER COLLAPSED INTO ONE STATUS.
            #   submission_http_status - did the API accept the request?
            #   server_job_status      - did the server then BUILD the file?
            #   local_file             - did we retrieve it?
            # On 2026-08-12 the first was 200 on every job and the second was
            # `failed` on every job. A single status column would have recorded
            # that as either "fine" or "refused", and both readings are wrong.
            job_status = m.get("status", "")
            submitted = bool(m.get("file_name"))
            if lf:
                reading = "RETRIEVED"
            elif job_status == "failed":
                reading = ("ACCEPTED BY THE API, THEN FAILED SERVER-SIDE. This "
                           "is NOT a host refusal and NOT evidence that the "
                           "data does not exist - the server took the job and "
                           "did not build the file.")
            elif submitted:
                reading = ("ACCEPTED, still generating or not yet collected. "
                           "The token is in _state.json; recover it, never "
                           "re-submit (rule 5).")
            else:
                reading = ("NOT SUBMITTED. Says nothing about the data.")
            w.writerow({
                "local_file": os.path.basename(lf or ""),
                "chunk_key": key,
                "source_url": m.get("file_url", ""),
                "endpoint": API,
                "date_range_start": start, "date_range_end": end,
                "sub_award_types": "|".join(types), "date_type": "action_date",
                "submission_http_status": 200 if submitted else 0,
                "server_job_status": job_status,
                "server_job_message": m.get("message") or "",
                "outcome_reading": reading,
                "rows_reported_by_server": m.get("total_rows", ""),
                "columns": m.get("total_columns", ""),
                "bytes": m.get("_bytes", ""),
                "sha256": m.get("_sha256", ""),
                "zip_members": members, "member_bytes": mbytes,
                "rows_read_locally": nrows,
                "submitted_utc": m.get("_submitted", ""),
                "retrieved_utc": m.get("_retrieved", ""),
                "server_seconds_elapsed": m.get("seconds_elapsed", ""),
                "fetched_date": FETCHED,
            })
    log(f"manifest -> {MANIFEST}")


def status() -> None:
    st = load_state()
    for key, start, end, types in JOBS:
        m = st["jobs"].get(key)
        if not m:
            print(f"{key:20s} NOT SUBMITTED")
            continue
        print(f"{key:20s} {m.get('status','?'):10s} "
              f"token={m.get('file_name','-')[:46]:46s} "
              f"rows={str(m.get('total_rows','-')):>9} "
              f"file={'yes' if staged(m) else 'no'}")


# ===========================================================================
# 5. MATCH - imports the ONE resolver and the guarded name route
# ===========================================================================

def _load(name, filename):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(CODE, filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_MODS = {}


def mods():
    """Import, never re-implement. Standing rule 8."""
    if _MODS:
        return _MODS
    sys.path.insert(0, CODE)
    m94 = _load("m94", "94_match_raw_subawards.py")     # the eight guards
    # Use 94's OWN module instances, not fresh loads. Loading 33 twice would
    # give one cached `norm`/`core` and one uncached, and the guards would then
    # be asking a different question from the pre-filter that fed them.
    m33, m41, m45 = m94.m33, m94.m41, m94.m45
    import cedar_match_guard as cmg                     # the central veto layer
    import cedar_domain as cd
    _MODS.update(m33=m33, m41=m41, m45=m45, m94=m94, cmg=cmg, cd=cd)
    return _MODS


def iter_new_subawards(st):
    """Yield (chunk_key, award_kind, member_name, row) over the NEW zips only."""
    for key, *_ in JOBS:
        m = st["jobs"].get(key)
        lf = (m or {}).get("_local_file")
        if not lf:
            continue
        path = os.path.join(ROOT, lf)
        if not os.path.exists(path):
            log(f"WARN {key}: staged file missing on disk: {lf}")
            continue
        with zipfile.ZipFile(path) as z:
            members = [i for i in z.infolist()
                       if i.filename.lower().endswith(".csv")]
            if not members:
                log(f"NOTE {key}: zip contains no CSV member")
            for info in members:
                kind = ("contract" if CONTRACT_MARK in info.filename else
                        "assistance" if ASSIST_MARK in info.filename else "unknown")
                log(f"  {key}: member {info.filename} "
                    f"({info.file_size:,} bytes uncompressed) kind={kind}")
                with z.open(info) as fh:
                    rd = csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8-sig"))
                    for row in rd:
                        yield key, kind, info.filename, row


def load_deflator():
    """BEA NIPA 1.1.9, base 2025. ONE deflator; no second one is introduced."""
    out = {}
    with open(DEFLATOR, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                out[r["year"].strip()] = float(r["factor_to_base"])
            except (KeyError, ValueError):
                continue
    return out


def load_uid_register():
    """503's OWN handle -> cedar_uid map, and the column it stamps on.

    IMPORTED, never re-implemented (standing rule 8). `503_identity.py` is not
    run and not edited here - two read-only functions are called:
    `entity_col()` picks which column of `subawards.csv` carries the handle
    (`prime_native_tribe_id`), and `register_map()` returns the permanent
    register, retired handles included. Returns (column, map) or (None, {}) if
    503 cannot be loaded, in which case `append()` leaves `cedar_uid` alone and
    says so rather than guessing.
    """
    try:
        import pathlib
        m503 = _load("m503", "503_identity.py")
        col, _hdr = m503.entity_col(pathlib.Path(OUT))
        reg = m503.register_map()
        return col, reg
    except Exception as e:                              # noqa: BLE001
        log(f"WARN could not load 503_identity ({type(e).__name__}: "
            f"{str(e)[:120]}); cedar_uid will be left as found and NEW rows "
            f"will carry it blank. Re-run `py -3 code/503_identity.py stamp "
            f"--apply` to fill them.")
        return None, {}


def match(dry=False) -> int:
    M = mods()
    m33, m41, m45, m94, cmg = M["m33"], M["m41"], M["m45"], M["m94"], M["cmg"]
    Tier = M["cd"].Tier
    os.makedirs(STAGE, exist_ok=True)
    os.makedirs(REVIEW, exist_ok=True)

    st = load_state()
    have = [k for k, *_ in JOBS if staged(st["jobs"].get(k))]
    if not have:
        log("match: no staged zips. Run `pull` first.")
        return 1
    log(f"=== 121 match: staged jobs {have} ===")

    spine = m33.read_csv(os.path.join(SPINE_DIR, "cedar_entity_spine.csv"))
    idx, by_id, cores, anvc_cores, core_list, exact = m94.build_spine_index(spine)
    log(f"spine: {len(spine):,} entities, {len(idx):,} index tokens")
    by_uei, _t, _n = m41.load_ledger()

    existing_keys, header, n_existing = read_existing_index(m45)
    log(f"existing subawards.csv: {n_existing:,} rows, "
        f"{len(existing_keys):,} distinct identity keys")
    # THE SCHEMA GUARD. Corrected 2026-08-28 - see the module docstring section
    # "APPEND-ONLY, WITH ONE DOCUMENTED HEADER CHANGE".
    #
    # The old test was `header != m45.COLS`, i.e. strict equality, and it
    # deadlocked this script against its OWN output: `append()` below adds the
    # three deflator columns at the END of the file, so from the first
    # successful append onwards the live header is a 52-column SUPERSET of the
    # 49-column promoted schema and `match` could never run again.
    #
    # The question the guard actually has to ask is not "is the header equal"
    # but "can a row written with the 49 canonical columns land in this file
    # WITHOUT any column being silently blanked". That needs two conditions,
    # and a bare prefix test only checks the first:
    #   1. the 49 canonical columns are present, in order, at the FRONT, and
    #   2. every column BEYOND them is one `append()` knows how to compute.
    # Condition 2 is what keeps this from being a loosening: an extra column
    # that `append()` cannot fill would be blanked on every appended row, and
    # that still halts here. The deflator columns are not blanked, because
    # `append()` recomputes all three from `fiscal_year` and `subaward_amount`
    # for EVERY row it emits - pre-existing and newly staged alike.
    #
    # Ordering is unchanged and is the one AGENTS.md concurrency rule 5
    # prescribes: the full-rebuild/stage step writes the canonical columns and
    # THE ENRICHER RUNS LAST. `append()` is that enricher.
    if header is not None:
        extras = header[len(m45.COLS):]
        unfillable = [c for c in extras
                      if c not in NEW_COLS and c not in STAMPED_COLS
                      and c not in REPORT_COLS
                      and c not in POST_PROMOTION_COLS]
        if header[:len(m45.COLS)] != m45.COLS or unfillable:
            raise SystemExit(
                "subawards.csv header is not the promoted schema; refusing to "
                f"proceed (canonical prefix ok="
                f"{header[:len(m45.COLS)] == m45.COLS}, "
                f"columns append() cannot fill={unfillable})")
        if extras:
            log(f"header carries {len(extras)} column(s) beyond the promoted "
                f"schema: {extras}. All are written by append(), which runs "
                f"AFTER this step and recomputes them for every row. Staged "
                f"rows are written with the {len(m45.COLS)} canonical columns.")
            owned = [c for c in extras if c in STAMPED_COLS]
            if owned:
                log(f"  of those, {owned} are owned by "
                    f"{sorted({STAMPED_COLS[c] for c in owned})} and are filled "
                    f"by append() through that script's OWN register, imported "
                    f"rather than re-implemented.")
            post = [c for c in extras if c in POST_PROMOTION_COLS]
            if post:
                log(f"  and {post} are filled by an enricher that runs AFTER "
                    f"this script - append() leaves them BLANK. RUN THESE "
                    f"WHEN THIS FINISHES, in order: "
                    f"910_subaward_report_id_backfill.py rescan; "
                    f"910_subaward_report_id_backfill.py apply; "
                    f"911_subaward_sub_leg_cedar_uid.py apply; "
                    f"81_build_passthrough_dataset.py. Until they run, "
                    f"subawards.csv has no primary key and "
                    f"512_build_dataset_contracts.py will say so.")

    # per-job retrieval dates, read off the checkpointed state
    fetched_for = {}
    for k, *_ in JOBS:
        rec = st["jobs"].get(k) or {}
        ts = (rec.get("_retrieved") or "")[:10]
        if ts:
            fetched_for[k] = ts
    log("fetched_date per job (from _state.json `_retrieved`): "
        + json.dumps(fetched_for))

    stage_path = os.path.join(STAGE, f"subawards_api_{TODAY}.csv")
    fstage = open(stage_path, "w", newline="", encoding="utf-8")
    # m45.COLS + REPORT_COLS. `build_row` returns the 49 canonical columns and
    # `extrasaction="ignore"` would silently drop anything else, which is how
    # `subaward_sam_report_id` went missing in the first place.
    wstage = csv.DictWriter(fstage, fieldnames=m45.COLS + REPORT_COLS,
                            extrasaction="ignore")
    wstage.writeheader()

    n_read = n_new = 0
    rows_per_job = Counter()
    rows_per_member = Counter()
    fy_raw, fy_new, dup_new, dir_new = Counter(), Counter(), Counter(), Counter()
    kind_new = Counter()
    route_rows = Counter()
    route_entities = defaultdict(set)
    refusals = Counter()
    cmg_refusals = Counter()
    ents_new = set()
    seen_new = Counter()
    memo = {}
    usd_new = 0.0
    n_pre_ffata = n_exceeds = 0
    unresolved = defaultdict(lambda: {"n": 0, "usd": 0.0, "name": "",
                                      "states": set(), "fy": set(), "side": set()})
    q = defaultdict(lambda: {"n": 0, "usd": 0.0, "fy": set(), "ueis": set(),
                             "states": set(), "prime": "", "how": "",
                             "canon": "", "cls": "", "ent_state": "",
                             "parent_uei": ""})
    cand_q = defaultdict(lambda: {"n": 0, "usd": 0.0, "fy": set(), "ueis": set(),
                                  "states": set()})

    def resolve_name(nm, stt, cc):
        k = ((nm or "").strip().upper(), (stt or "").strip().upper(),
             (cc or "").strip().upper())
        hit = memo.get(k)
        if hit is None:
            if len(memo) > 800_000:
                memo.clear()
            hit = m94.name_route(nm, stt, cc, spine, idx, by_id, cores,
                                 anvc_cores, core_list, exact)
            # SECOND VETO LAYER. `cedar_match_guard.guard()` is imported and
            # called, never modified. It can only REFUSE what the resolver and
            # 94's eight guards already allowed - it never proposes anything.
            tid = hit[0]
            if tid:
                ok, why = cmg.guard(nm, by_id.get(tid, {}), how=hit[2],
                                    context={"record_state": stt})
                if not ok:
                    cmg_refusals[why.split(":")[0].split(" - ")[0][:60]] += 1
                    hit = (None, None, f"cedar_match_guard:{why}")
            memo[k] = hit
        return hit

    def is_link(m):
        return (m is not None and m.get("confidence_tier") in ("A", "B")
                and bool((m.get("tribe_id") or "").strip()))

    for chunk, kind, member, r in iter_new_subawards(st):
        n_read += 1
        rows_per_job[chunk] += 1
        rows_per_member[(chunk, kind)] += 1
        fy = (r.get("subaward_action_date_fiscal_year") or "").strip()
        fy_raw[fy] += 1
        if n_read % 250_000 == 0:
            log(f"  ...{n_read:,} raw rows read, {n_new:,} staged, "
                f"{len(memo):,} distinct names resolved")

        puei = (r.get("prime_awardee_uei") or "").strip().upper()
        suei = (r.get("subawardee_uei") or "").strip().upper()
        pm, sm = by_uei.get(puei), by_uei.get(suei)
        pl, sl = is_link(pm), is_link(sm)
        p_tid = pm.get("tribe_id") if pl else ""
        p_tier = pm.get("confidence_tier") if pl else ""
        s_tid = sm.get("tribe_id") if sl else ""
        s_tier = sm.get("confidence_tier") if sl else ""
        route = ROUTE_UEI if (pl or sl) else ""

        # ---- route 2: declared parent identifier, family level, tier B ----
        if not pl:
            ppar = (r.get("prime_awardee_parent_uei") or "").strip().upper()
            pmm = by_uei.get(ppar)
            if ppar and ppar != puei and is_link(pmm):
                ok, why = m94.parent_ok(r.get("prime_awardee_name", ""),
                                        pmm.get("tribe_id"), by_id, cores)
                if ok:
                    p_tid, p_tier = pmm.get("tribe_id"), Tier.B.value
                    route = route or ROUTE_PARENT
                else:
                    refusals[f"prime_parent|{why.split(':')[0]}"] += 1
        if not sl:
            spar = (r.get("subawardee_parent_uei") or "").strip().upper()
            smm = by_uei.get(spar)
            if spar and spar != suei and is_link(smm):
                ok, why = m94.parent_ok(r.get("subawardee_name", ""),
                                        smm.get("tribe_id"), by_id, cores)
                if ok:
                    s_tid, s_tier = smm.get("tribe_id"), Tier.B.value
                    route = route or ROUTE_PARENT
                else:
                    refusals[f"sub_parent|{why.split(':')[0]}"] += 1

        # ---- route 3: NAME, tier B always ---------------------------------
        p_how = s_how = ""
        if not p_tid:
            tid, canon, how = resolve_name(
                r.get("prime_awardee_name", ""),
                r.get("prime_awardee_state_code", ""),
                r.get("prime_awardee_country_code", ""))
            if tid and how == "containment":
                d = cand_q[("prime", (r.get("prime_awardee_name") or "").strip().upper(), tid)]
                d["n"] += 1
                d["usd"] += m45.fnum(r.get("subaward_amount"))
                d["fy"].add(fy)
                if r.get("prime_awardee_state_code"):
                    d["states"].add(r["prime_awardee_state_code"])
                tid = None
            if tid:
                p_tid, p_tier, p_how = tid, Tier.B.value, how
                route = route or ROUTE_NAME
            elif how and not how.startswith(("no_spine_token", "no_core",
                                             "name_too_short", "prefilter_",
                                             "resolver:no_spine_match")):
                refusals[f"prime|{how.split(':')[0]}"] += 1
        if not s_tid:
            tid, canon, how = resolve_name(
                r.get("subawardee_name", ""),
                r.get("subawardee_state_code", ""),
                r.get("subawardee_country_code", ""))
            if tid and how == "containment":
                d = cand_q[("sub", (r.get("subawardee_name") or "").strip().upper(), tid)]
                d["n"] += 1
                d["usd"] += m45.fnum(r.get("subaward_amount"))
                d["fy"].add(fy)
                if suei:
                    d["ueis"].add(suei)
                if r.get("subawardee_state_code"):
                    d["states"].add(r["subawardee_state_code"])
                tid = None
            if tid:
                s_tid, s_tier, s_how = tid, Tier.B.value, how
                route = route or ROUTE_NAME
            elif how and not how.startswith(("no_spine_token", "no_core",
                                             "name_too_short", "prefilter_",
                                             "resolver:no_spine_match")):
                refusals[f"sub|{how.split(':')[0]}"] += 1

        if not (p_tid or s_tid):
            # DISCOVERY POOL, not an attribution: a subawardee UEI the ledger
            # has never seen, on a row we could not attribute either way. This
            # is the file the next ruling pass mines.
            if suei and len(unresolved) < 200_000:
                d = unresolved[suei]
                d["n"] += 1
                d["usd"] += m45.fnum(r.get("subaward_amount"))
                d["name"] = d["name"] or (r.get("subawardee_name") or "")
                d["fy"].add(fy)
                d["side"].add("sub")
                if r.get("subawardee_state_code"):
                    d["states"].add(r["subawardee_state_code"])
            continue

        # THE WEAKEST ROUTE LABELS THE ROW (94's rule, kept).
        if p_how or s_how:
            route = ROUTE_NAME
        elif route == ROUTE_UEI and (
                (p_tid and p_tier == Tier.B.value and not pl)
                or (s_tid and s_tier == Tier.B.value and not sl)):
            route = ROUTE_PARENT

        row = m94.build_row(r, kind, chunk, (p_tid, p_tier, s_tid, s_tier), route)
        # `fetched_date` is PER JOB, not per campaign (fixed 2026-09-01).
        # FETCHED is the date this raw DIRECTORY was opened; the jobs inside it
        # landed on three different days - fy2021 on 2026-08-26, fy2022-24 on
        # 2026-09-01 - because the 2026-08-12 submissions all failed
        # server-side. Stamping every row 2026-08-12 asserts a retrieval that
        # did not happen and makes the FSRS filing lag unmeasurable from the
        # clean file. The job's own `_retrieved` timestamp is the fact.
        row["fetched_date"] = fetched_for.get(chunk, FETCHED)
        # `source_file` must keep the SEAM visible: the chunk key alone would
        # not say which pull these came from.
        row["source_file"] = f"usaspending_2026-08-12/{chunk}"
        row["promoted_date"] = TODAY
        for c in REPORT_COLS:
            row[c] = (r.get(c) or "").strip()

        ik = m45.identity_key(row)
        seen_new[ik] += 1
        if seen_new[ik] <= existing_keys.get(ik, 0):
            continue
        row["duplicate_status"] = ("primary"
                                   if seen_new[ik] - existing_keys.get(ik, 0) == 1
                                   else "exact_repeat_within_source")
        wstage.writerow(row)
        n_new += 1
        route_rows[route] += 1
        fy_new[row["fiscal_year"]] += 1
        dup_new[row["duplicate_status"]] += 1
        dir_new[row["direction"]] += 1
        kind_new[kind] += 1
        if row["action_date_precedes_ffata_flag"] == "yes":
            n_pre_ffata += 1
        if row["subaward_exceeds_prime_flag"] == "yes":
            n_exceeds += 1
        elif row["duplicate_status"] == "primary":
            usd_new += m45.fnum(row["subaward_amount"])
        for tid in (p_tid, s_tid):
            if tid:
                route_entities[route].add(tid)
                ents_new.add(tid)

        amt = m45.fnum(row["subaward_amount"])
        if route in (ROUTE_NAME, ROUTE_PARENT):
            for side, tid, nm, how, uei, stt, par in (
                    ("prime", p_tid, row["prime_name"], p_how,
                     row["prime_uei"], "", row["prime_parent_uei"]),
                    ("sub", s_tid, row["sub_name"], s_how,
                     row["sub_uei"], row["sub_state"], row["sub_parent_uei"])):
                if not tid:
                    continue
                if route == ROUTE_NAME and not how:
                    continue
                ent = by_id.get(tid, {})
                d = q[(route, side, (nm or "").strip().upper(), tid)]
                d["n"] += 1
                d["usd"] += amt
                d["fy"].add(row["fiscal_year"])
                if uei:
                    d["ueis"].add(uei)
                if stt:
                    d["states"].add(stt)
                d["prime"] = d["prime"] or row["prime_award_id"]
                d["how"] = d["how"] or (how or "declared_parent_uei")
                d["canon"] = ent.get("canonical_name", "")
                d["cls"] = ent.get("entity_class", "")
                d["ent_state"] = ent.get("state", "")
                d["parent_uei"] = d["parent_uei"] or par

    fstage.close()
    log(f"READ {n_read:,} raw rows from the new pull")
    log("  rows by job: " + json.dumps(dict(rows_per_job)))
    log("  rows by (job, kind): "
        + json.dumps({f"{k[0]}|{k[1]}": v for k, v in sorted(rows_per_member.items())}))
    log("  raw rows by fiscal year: " + json.dumps(dict(sorted(fy_raw.items()))))
    log(f"NEW rows staged -> {stage_path}: {n_new:,}")
    log("  by route: " + json.dumps(dict(route_rows)))
    log("  by fiscal year: " + json.dumps(dict(sorted(fy_new.items()))))
    log("  by award kind: " + json.dumps(dict(kind_new)))
    log("guard refusals (a refusal is the guard working): "
        + json.dumps(dict(refusals.most_common(25))))
    log("cedar_match_guard vetoes: " + json.dumps(dict(cmg_refusals.most_common(15))))

    # record local row counts back into state, for the manifest
    for k, v in rows_per_job.items():
        if k in st["jobs"]:
            st["jobs"][k]["_rows_read_locally"] = v
    for k, *_ in JOBS:
        if k in st["jobs"] and staged(st["jobs"][k]):
            st["jobs"][k].setdefault("_rows_read_locally", rows_per_job.get(k, 0))
    save_state(st)
    write_manifest(st)

    # ---------------------------------------------------------- review queue
    rpath = os.path.join(REVIEW, f"subaward_api_unresolved_{TODAY}.csv")
    with open(rpath, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["status", "route", "side", "record_name", "record_states",
                    "record_ueis", "record_parent_uei", "tribe_id",
                    "canonical_name", "entity_class", "entity_state",
                    "resolver_how", "confidence_tier", "n_subawards",
                    "total_usd_UNFILTERED", "fiscal_years",
                    "example_prime_award_id", "match_basis", "YOUR_RULING"])
        for (route, side, nm, tid), d in sorted(q.items(),
                                                key=lambda kv: -kv[1]["usd"]):
            w.writerow([
                "STAGED_TIER_B", route, side, nm,
                "|".join(sorted(d["states"]))[:60],
                "|".join(sorted(d["ueis"]))[:200], d["parent_uei"], tid,
                d["canon"], d["cls"], d["ent_state"], d["how"], "B",
                d["n"], round(d["usd"], 2),
                "|".join(sorted(x for x in d["fy"] if x)), d["prime"],
                "name resolved through 33_apply_party_rulings.resolve_entity, "
                "passed 94's eight guards AND cedar_match_guard; NO identifier "
                "evidence" if route == ROUTE_NAME else
                "declared a parent UEI present in the identifier ledger; "
                "family-level, not a legal-entity match", ""])
        for (side, nm, tid), d in sorted(cand_q.items(),
                                         key=lambda kv: -kv[1]["usd"]):
            ent = by_id.get(tid, {})
            w.writerow([
                "CANDIDATE_NOT_APPENDED", ROUTE_NAME, side, nm,
                "|".join(sorted(d["states"]))[:60],
                "|".join(sorted(d["ueis"]))[:200], "", tid,
                ent.get("canonical_name", ""), ent.get("entity_class", ""),
                ent.get("state", ""), "containment", "", d["n"],
                round(d["usd"], 2),
                "|".join(sorted(x for x in d["fy"] if x)), "",
                "containment survived every guard and STILL attributes nothing. "
                "Spec 3: containment is not a match. A human decides.", ""])
        for uei, d in sorted(unresolved.items(),
                             key=lambda kv: -kv[1]["usd"])[:6000]:
            w.writerow(["UNRESOLVED_DISCOVERY_POOL", "", "sub", d["name"],
                        "|".join(sorted(d["states"]))[:60], uei, "", "", "", "",
                        "", "", "", d["n"], round(d["usd"], 2),
                        "|".join(sorted(x for x in d["fy"] if x)), "",
                        "subawardee UEI absent from the identifier ledger and "
                        "the name resolved to nothing. A DISCOVERY POOL, not an "
                        "attribution.", ""])
    log(f"WROTE {rpath} - {len(q):,} staged tier-B, {len(cand_q):,} containment "
        f"candidates attributed to nobody, "
        f"{min(len(unresolved), 6000):,} unresolved discovery rows")

    summary = {
        "run_date": TODAY,
        "jobs_staged": have,
        "raw_rows_read": n_read,
        "raw_rows_by_job": dict(rows_per_job),
        "raw_rows_by_job_and_kind": {f"{k[0]}|{k[1]}": v
                                     for k, v in sorted(rows_per_member.items())},
        "raw_rows_by_fiscal_year": dict(sorted(fy_raw.items())),
        "existing_rows": n_existing,
        "new_rows": n_new,
        "new_rows_by_route": dict(route_rows),
        "new_rows_by_fiscal_year": dict(sorted(fy_new.items())),
        "new_rows_by_award_kind": dict(kind_new),
        "new_rows_by_direction": dict(dir_new),
        "new_rows_duplicate_status": dict(dup_new),
        "new_rows_pre_ffata_flagged": n_pre_ffata,
        "new_rows_flagged_subaward_exceeds_prime": n_exceeds,
        "distinct_entities_touched": len(ents_new),
        "distinct_entities_by_route": {k: len(v) for k, v in route_entities.items()},
        "usd_new_after_BOTH_filters": round(usd_new, 2),
        "containment_candidates_banked_not_attributed": len(cand_q),
        "unresolved_discovery_ueis": len(unresolved),
        "guard_refusals": dict(refusals),
        "cedar_match_guard_vetoes": dict(cmg_refusals),
        "staging_file": stage_path,
    }
    with open(os.path.join(REVIEW, f"_121_summary_{TODAY}.json"), "w",
              encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1)
    log("SUMMARY " + json.dumps(summary, indent=1))
    if dry:
        log("--dry-run: nothing appended")
    return 0


def read_existing_index(m45):
    keys = Counter()
    header = None
    n = 0
    if not os.path.exists(OUT):
        return keys, header, n
    with open(OUT, encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        header = rd.fieldnames
        for r in rd:
            n += 1
            keys[m45.identity_key(r)] += 1
    return keys, header, n


# ===========================================================================
# 6. APPEND - and the one documented header change
# ===========================================================================

def append() -> int:
    M = mods()
    m45 = M["m45"]
    stage_path = os.path.join(STAGE, f"subawards_api_{TODAY}.csv")
    # A MISSING STAGING FILE IS NOT AN ERROR, and the reason is the point.
    # `_real2025` is computed from `fiscal_year` and `subaward_amount`, both of
    # which every existing row already carries. Adding the deflated columns does
    # not depend on the pull landing, and rows appended later are deflated by
    # the same code path from the same file, so no seam is created. Running this
    # with zero new rows is a column addition and nothing else.
    have_stage = os.path.exists(stage_path)
    if not have_stage:
        log("append: no staging file - no new rows to append. Proceeding as a "
            "COLUMN ADDITION only (the deflator needs no new data).")
    defl = load_deflator()
    uid_col, uid_reg = load_uid_register()
    if uid_col:
        log(f"cedar_uid: stamping NEW rows from 503's register "
            f"({len(uid_reg):,} handles) keyed on `{uid_col}`. PRE-EXISTING "
            f"rows are carried through untouched - re-stamping them is 503's "
            f"job, not this script's, and the verify step below would fail if "
            f"this run changed one.")

    # Re-read the target IMMEDIATELY before writing.
    with open(OUT, encoding="utf-8-sig", newline="") as fh:
        base_fields = list(csv.DictReader(fh).fieldnames)
    if base_fields[:len(m45.COLS)] != m45.COLS:
        raise SystemExit("subawards.csv header changed under us; refusing")
    want = NEW_COLS + REPORT_COLS
    fields = base_fields + [c for c in want if c not in base_fields]
    adding = [c for c in want if c not in base_fields]

    bak = OUT + f".bak_{TODAY}_pre121"
    if not os.path.exists(bak):
        shutil.copy2(OUT, bak)
        log(f"backup -> {os.path.basename(bak)}")

    def real(row):
        fy = (row.get("fiscal_year") or "").strip()
        f = defl.get(fy)
        amt = m45.fnum(row.get("subaward_amount"))
        if f is None or not (row.get("subaward_amount") or "").strip():
            return "", "", "2025"
        return round(amt * f, 2), f, "2025"

    tmp = OUT + ".tmp121"
    n_existing = n_added = 0
    n_uid_stamped = n_uid_unknown = 0
    with open(OUT, encoding="utf-8-sig", newline="") as src, \
            open(tmp, "w", newline="", encoding="utf-8") as dst:
        rd = csv.DictReader(src)
        w = csv.DictWriter(dst, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rd:
            # EVERY EXISTING VALUE IS CARRIED THROUGH UNCHANGED. The only
            # change to an existing row is that it gains the three NEW columns,
            # appended at the end. Nothing is edited, reordered or dropped.
            v, f, base = real(r)
            r["subaward_amount_real2025"] = v
            r["deflator_factor_2025"] = f
            r["inflation_base_year"] = base
            w.writerow(r)
            n_existing += 1
        if have_stage:
            with open(stage_path, encoding="utf-8-sig", newline="") as sf:
                for r in csv.DictReader(sf):
                    v, f, base = real(r)
                    r["subaward_amount_real2025"] = v
                    r["deflator_factor_2025"] = f
                    r["inflation_base_year"] = base
                    # cedar_uid on NEW rows only. Blank where the handle is
                    # blank (the row has no Native prime) or is not in the
                    # register - NEVER guessed. 503 re-derives the same value.
                    if uid_col and "cedar_uid" in fields:
                        h = (r.get(uid_col) or "").strip()
                        r["cedar_uid"] = uid_reg.get(h, "") if h else ""
                        if h and not uid_reg.get(h):
                            n_uid_unknown += 1
                        elif h:
                            n_uid_stamped += 1
                    w.writerow(r)
                    n_added += 1
    os.replace(tmp, OUT)
    log(f"WROTE {OUT}: {n_existing:,} existing + {n_added:,} appended = "
        f"{n_existing + n_added:,} rows, {len(fields)} columns "
        f"(added {adding})")
    if uid_col and n_added:
        log(f"cedar_uid on the {n_added:,} appended rows: {n_uid_stamped:,} "
            f"stamped from the register, {n_uid_unknown:,} carried a handle the "
            f"register does not know (left BLANK, never guessed), the rest have "
            f"no `{uid_col}` at all. Run `py -3 code/503_identity.py stamp` to "
            f"confirm against 503's own count.")

    # ---- verification: every pre-existing row, field by field, vs the backup
    bad = 0
    with open(bak, encoding="utf-8-sig", newline="") as a, \
            open(OUT, encoding="utf-8-sig", newline="") as b:
        ra, rb = csv.DictReader(a), csv.DictReader(b)
        for i, (x, y) in enumerate(zip(ra, rb)):
            for c in base_fields:
                if (x.get(c) or "") != (y.get(c) or ""):
                    bad += 1
                    if bad <= 5:
                        log(f"  MISMATCH row {i} col {c}: "
                            f"{x.get(c)!r} != {y.get(c)!r}")
            if bad > 20:
                break
    if bad:
        shutil.copy2(bak, OUT)
        raise SystemExit(f"VERIFY FAILED: {bad} field mismatches on pre-existing "
                         f"rows. Restored from {os.path.basename(bak)}.")
    log(f"VERIFIED: all {n_existing:,} pre-existing rows byte-identical on all "
        f"{len(base_fields)} original columns")
    return 0


# ===========================================================================
# 7. CODEBOOK FRAGMENT - never codebook_master.csv
# ===========================================================================

def codebook() -> int:
    sys.path.insert(0, CODE)
    import cedar_codebook as cb
    rows = []
    with open(OUT, encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        fields = rd.fieldnames
        filled = Counter()
        n = 0
        for r in rd:
            n += 1
            for c in fields:
                if (r.get(c) or "").strip():
                    filled[c] += 1
    DESC = {
        "subaward_amount_real2025": (
            "subaward_amount x the BEA GDP implicit price deflator "
            "(NIPA 1.1.9) rebased to 2025, keyed on fiscal_year. Blank where "
            "the year is outside data/clean/inflation_deflator.csv or the "
            "nominal amount is blank. IT INHERITS EVERY DEFECT OF THE NOMINAL "
            "FIELD - deflating a filer-entered figure does not validate it."),
        "deflator_factor_2025": (
            "The factor applied to obtain subaward_amount_real2025. FY2025 "
            "rows carry 1.0. Recorded so the deflation is reproducible and so "
            "no second deflator can be introduced downstream."),
        "inflation_base_year": "2025 on every row. One base year, project-wide.",
        "subaward_sam_report_id": (
            "The FSRS/SAM report id, carried straight from the source extract. "
            "MEASURED GLOBALLY UNIQUE: 765,109 distinct over 765,109 FY2021 "
            "rows and 456,412 over 456,412 FY2020 rows, zero blank, zero "
            "overlap between the two years. IT IDENTIFIES A REPORT, NOT A "
            "SUBAWARD - one $57,500 FY2021 subaward carries 93 of them, filed "
            "monthly from 2022-08 to 2025-01. Use it to key a row; use "
            "duplicate_status=='primary' to key a subaward. BLANK on rows "
            "promoted before 2026-09-01, which had no key to join back on."),
        "subaward_sam_report_month": (
            "Calendar month of the SAM filing, 1-12, paired with "
            "subaward_sam_report_year. The pair is what distinguishes a "
            "re-filing from a second subaward, and is why duplicate_status is "
            "now auditable against the source instead of inferred."),
        "subaward_sam_report_last_modified_date": (
            "When the filer last touched the report. Together with the report "
            "id this measures FSRS FILING LAG - the gap between "
            "subaward_action_date and the filing - which is why a CLOSED "
            "fiscal year still gains rows and why a re-pull of an old window "
            "is not a duplicate pull."),
        "source_file": (
            "Which pull a row came from. Rows added 2026-08-12 carry "
            "`usaspending_2026-08-12/<job>`, which keeps the seam between the "
            "2026-08-05 corpus and the FY2021-2024 backfill visible."),
        "duplicate_status": (
            "`primary` or `exact_repeat_within_source`. A FILTER COLUMN, "
            "applied to no row. Never sum this dataset without "
            "duplicate_status=='primary'."),
        "subaward_exceeds_prime_flag": (
            "`yes` where the reported subaward exceeds its own prime award - "
            "arithmetically impossible and therefore a source defect. 5,941 "
            "such rows exist across the corpus, worst case 12,240x. A FILTER "
            "COLUMN, applied to no row."),
        "action_date_precedes_ffata_flag": (
            "`yes` where the subaward action date precedes FY2010. FSRS did "
            "not exist before FFATA; these are misdated filings, retained and "
            "flagged, never counted as coverage."),
        "source_dataset": (
            "The RESOLUTION ROUTE, labelled by the WEAKEST leg used: "
            "usaspending_fsrs_pull (UEI exact against the identifier ledger), "
            "usaspending_fsrs_parent_cluster (a declared parent UEI in the "
            "ledger; family-level, tier B), usaspending_fsrs_name_match (the "
            "one resolver plus eight guards plus cedar_match_guard; tier B, "
            "always). Internal, not published."),
    }
    for c in fields:
        if c not in DESC:
            continue
        rows.append({
            "dataset": "02b_subawards", "variable": c,
            "description": DESC[c],
            "pct_filled": f"{100.0 * filled[c] / n:.1f}" if n else "",
            "n_rows": n,
            "source": "USAspending FSRS bulk_download (api.usaspending.gov) "
                      "+ BEA NIPA 1.1.9 for the deflator",
            "published": "0" if c == "source_dataset" else "1",
            "added_by": "code/121_pull_subawards_api.py",
            "added_date": TODAY,
        })
    fields_out = ["dataset", "variable", "description", "pct_filled", "n_rows",
                  "source", "published", "added_by", "added_date"]
    frag = cb.FRAG / "02b_subawards_api.csv"
    cb.write_fragment("02b_subawards_api", rows, fields_out)
    log(f"WROTE codebook FRAGMENT {frag} - {len(rows)} variables. "
        f"codebook_master.csv NOT touched.")
    return 0


def main() -> int:
    stage = sys.argv[1] if len(sys.argv) > 1 else "status"
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
    if stage == "claim":
        return 0 if claim("--force" in sys.argv) else 3
    if stage == "probe":
        return 0 if probe() else 2
    if stage == "canary":
        return canary()
    if stage == "diagnose":
        return diagnose()
    if stage == "waitclear":
        return 0 if waitclear(deadline=COLLECT_DEADLINE) else 2
    if stage == "auto":
        return auto()
    if stage == "pull":
        cap = None
        if "--max-inflight" in sys.argv:
            cap = sys.argv[sys.argv.index("--max-inflight") + 1]
        return pull(only, do_claim="--no-claim" not in sys.argv,
                    sequential="--sequential" in sys.argv, inflight_cap=cap)
    if stage == "collect":
        return collect()
    if stage == "status":
        status()
        return 0
    if stage == "manifest":
        write_manifest()
        return 0
    if stage == "match":
        return match("--dry-run" in sys.argv)
    if stage == "append":
        return append()
    if stage == "codebook":
        return codebook()
    raise SystemExit(f"unknown stage {stage}")


if __name__ == "__main__":
    sys.exit(main())
