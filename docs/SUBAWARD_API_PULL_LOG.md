# Subaward API pull — FY2021–FY2024 and the FY2020 contracts member

*Runner: `code/121_pull_subawards_api.py`. Host lock:
`logs/_HOSTLOCK_api.usaspending.gov.json`. Raw:
`data/raw/subcontracts/usaspending_2026-08-12/`. Run log:
`logs/121_pull_subawards_api.log`. Started 2026-08-12T16:11Z.*

**Status: NOT RETRIEVED — and the cause is at the source, not here. NINE
`bulk_download` jobs were submitted over 80 minutes, every one was ACCEPTED with
a token, and every one FAILED server-side with `"An error occurred."` That
includes a two-day canary, a two-day probe of FY2015 (a range this project
already downloaded successfully on 2026-08-05), and a two-day PRIME-award
control. USAspending's bulk_download service was generating no files on
2026-08-12. This is not our request rate, not our payload, and not specific to
subawards.**

**Delivered anyway:** the runner, the raw folder with a manifest that records
the failure precisely, the deflated `_real2025` columns on all 63,548 existing
rows, a codebook fragment, and a match pipeline validated end-to-end on real
FSRS rows. `62_no_regression_check.py` passed before and after.

---

## 1. Why this is API-only, and why it waited

`docs/ASSISTANCE_ARCHIVE_PULL_LOG.md` FINDING 1 settled it against a full
enumeration of the static archive: **zero of ~~4,631~~ 4,597 keys contain the string
`sub` in any case.**

> *Citation corrected 2026-08-26. **The conclusion is unaffected** — zero of 4,597 is still
> zero — but the key count cited here was retired by a re-enumeration on the same day this
> log was written. `ASSISTANCE_ARCHIVE_PULL_LOG.md` asserts 4,631 at lines 35/52/60 and then
> **self-corrects at 413-416** to **4,597**, which is the figure `PRIME_ARCHIVE_PULL_LOG.md`,
> `AGENTS.md` and `START_HERE.md` all carry. Recorded because a settling argument that
> cites a retired listing invites someone to re-open a closed question on a technicality.* `files.usaspending.gov` publishes Contracts and Assistance
and nothing else; every plausible subaward path returned 404 or 403. FSRS
subaward data is served by `POST /api/v2/bulk_download/awards/` with
`sub_award_types`, on `api.usaspending.gov`, and by nothing else. That is why
this gap survived two archive pulls. **No API key is required.**

## 2. What is owed

`docs/SUBAWARD_RAW_MATCH_LOG.md` §1 establishes the gap three independent ways:
`_state.json` holds 22 finished jobs and fy2021–fy2024 are not among them; every
one of 6,613,471 raw rows carries a fiscal year equal to its own job's, so the
missing years are not hiding in a neighbour; and the 548 FY2021–2024 rows the
clean file does hold name `highergov_2023_export` or `funding_forward_fill` on
every row.

| FY | clean rows before this run | neighbouring years |
|---|---:|---|
| 2021 | 173 | 2020 → 3,884 |
| 2022 | 89 | 2019 → 9,373 |
| 2023 | 120 | 2025 → 7,360 |
| 2024 | 166 | 2026 → 3,457 |

Plus the FY2020 **contract** member, which the completed job returned as
**4,144 bytes — one header line, zero data rows** against FY2019's 439 MB.
Re-submitted here as a **procurement-only** job so that an empty result would be
a fact about FY2020 rather than a fact about a mixed job.

## 3. What happened, minute by minute

Every line below is from a log, not from memory.

| UTC | event |
|---|---|
| 16:11:15 | `GET /api/v2/references/agency/456/` → **HTTP 200 in 0.46s**. Host healthy. |
| 16:11:17 | `fy2021` submitted, **accepted**, token `All_Subawards_2026-08-12_H16M11S17061900.zip` checkpointed |
| 16:14:18 | `fy2022` accepted |
| 16:17:19 | `fy2023` accepted |
| 16:20:21 | `fy2024` accepted |
| 16:23:22 | `fy2020_procurement` accepted |
| 16:25:53 | `fy2021`, `fy2022`, `fy2023` → `status: failed`, message **"An error occurred."** |
| 16:28:25 | `fy2024`, `fy2020_procurement` → same. **All five dead.** |
| 16:30:20 | PEER `code/114_pull_prime_archive.py` completes a **1.31 GB** FY2008 object successfully |
| 16:31:21 | PEER `HEAD` on `files.usaspending.gov` → **HTTP 500**, 0 bytes |
| 16:32:44 | PEER `HEAD` → **RemoteDisconnected in 0.5s**; peer enters backoff |
| ~16:35 | This run: `GET` reference endpoint → **RemoteDisconnected in 0.43s** |

Submissions were spaced **180s** apart and the total request count for the whole
run was roughly **35**.

### FINDING 1 — an accepted token is not a working job

This is the finding worth carrying forward. The server returned a `file_name`
for every one of the five submissions, the API answered HTTP 200 throughout, and
the checkpoint logic recorded five healthy-looking jobs. **All five then failed
server-side with a generic "An error occurred."** Nothing in the acceptance
response predicted it.

A pull that treats acceptance as success will report five jobs in flight and
five hours later discover it has nothing. `code/121` now carries a **canary**
stage — a single two-day job, which generated in 37 seconds on this endpoint on
2026-08-05 — so the health of the download fleet is established for the price of
one submission instead of five full fiscal years.

### FINDING 2 — the whole bulk_download service was down, and three cheap probes proved it

After the edge cleared at 17:05, `code/121 ... diagnose` ran three **two-day**
jobs designed so that their outcomes would separate three explanations with
opposite implications. Two days generated in 37 seconds on this endpoint on
2026-08-05, so each probe is about as cheap as a real job can be.

| probe | filter | window | outcome |
|---|---|---|---|
| `diag_sub_2021` | `sub_award_types` | 2021-10-01..02 | **FAILED** `"An error occurred."` |
| `diag_sub_2015` | `sub_award_types` | 2015-10-01..02 | **FAILED** `"An error occurred."` |
| `diag_prime_2021` | `prime_award_types` | 2021-10-01..02 | **FAILED** `"An error occurred."` |

Each row kills an explanation:

* **FY2015 failing kills "the FY2021–2024 window is broken."** That exact range
  downloaded successfully a week ago.
* **The PRIME control failing kills "`sub_award_types` is broken."** The endpoint
  understood the request — it named the output
  `All_PrimeTransactions_2026-08-12_....zip`, a different prefix — and then
  failed identically.
* **The two-day canary failing kills "the jobs are too big"**, and a single
  submission into a host answering HTTP 200 kills "we are being rate-limited."

**Verdict: the whole `bulk_download` service was generating nothing on
2026-08-12.** Nobody's pull works today. The correct response is to wait and
re-run, **not** to redesign the payload, split the years, or add workers — every
one of which would have been a plausible-looking wrong move, and the first two
were on the table before these probes ran.

Nine jobs, ~80 minutes, and the whole diagnosis cost three two-day submissions.
That is the argument for the canary: **the cheap answer should always be bought
before the expensive one.**

### FINDING 3 — the block spans both hostnames, and the peer's log proved it for free

`files.usaspending.gov` is genuinely a different host from `api.usaspending.gov`
and `code/114_pull_prime_archive.py` says so in its own docstring. **Both were
refusing the same IP inside two minutes of each other**, with the identical
sub-second `RemoteDisconnected` signature. Treating them as independent
rate-limit budgets is wrong.

The evidence for this cost **zero requests**: the peer's log was already
recording HTTP 500 then `RemoteDisconnected`, so reading it answered "has the
edge cleared?" without probing anything. Where a peer is already polling a host,
**its log is the cheapest probe available**, and it is strictly better than
adding a second prober.

### Attribution — recorded, and not resolved into a single cause

`PULL_DISCIPLINE.md` requires that whoever caused a block be named. Two
candidates, and this build will not pretend to have separated them:

1. **The peer.** `114_pull_prime_archive.py` was pulling ~1.3 GB archive objects
   back to back with a 60s pause. That is the same shape
   `ASSISTANCE_ARCHIVE_PULL_LOG.md` FINDING 6 records as having edge-blocked
   this IP on 2026-08-08 — six ~2 GB objects in twelve minutes.
2. **This build.** Five full-year FSRS bulk_download jobs in twelve minutes is
   real server-side work, even though it is only ~35 HTTP requests.

The server-side job failures at **16:25** *precede* the peer's first 500 at
**16:31**, which argues the API's download fleet was already unhealthy before
the edge closed. The shared IP is the common factor. Both are written down so
the next agent does not re-trigger this assuming the host is merely flaky.

## 4. What this run did NOT do, deliberately

* **It did not start a second backoff loop.** The peer was already backing off
  against the same refusing IP. A second one is precisely the 2026-08-05
  failure — four agents quadrupling the probe rate against a host blocking them
  *for* probe rate. `auto` waits for the peer to go quiet before it probes at
  all, and logs "ZERO requests issued" while it waits.
* **It did not re-submit anything into a refusing host.**
* **It did not read the five dead tokens as "not published."** A failed job and
  an absent object are different facts. The tokens are retained in `_state.json`
  as evidence.

### Rule 5 does not bind on a failed job

All five tokens report `status: failed`. Rule 5 forbids discarding a job the
server is still generating, because that throws away completed server work and
the queue position. **A failed job is a corpse, not work in progress.**
Re-submitting it discards nothing. `code/121` encodes exactly this distinction:
a token with `status == "failed"` is archived under a suffixed key and a fresh
job is submitted; a token in any other state is recovered and polled, never
re-submitted.

## 5. Guardrails observed

* One poller per host, checked with `Win32_Process` **including
  `ParentProcessId`**. The first attempt of this build read *its own `py.exe`
  launcher* as a peer and stopped; the self-check now walks the process
  ancestry. `ps aux` cannot see command lines on Windows (rule 9) and was not
  used.
* Peers on `files.usaspending.gov` do not block submission — a different host —
  but they **gate downloads**, which land there. `wait_for_files_host()` defers a
  download rather than stacking it on an active archive puller; deferring is free
  because the generated object stays retrievable by its `file_name`.
* Transport failure and HTTP status are never collapsed: `http_status = 0` is
  recorded with the reading spelled out, so absence is never inferred from a
  block.
* The probing leg is bounded at **2h regardless of `CEDAR_SUBMIT_HOURS`**.
  Raising that variable gives the submission leg room on a *healthy* host; it
  must never silently extend how long a *refusing* host is probed.
* No process was killed by image name.
* `code/62_no_regression_check.py` run before: **no regressions**.

## 5b. What DID land: the deflator columns, and a disagreement they exposed

`_real2025` does not depend on the pull — it is computed from `fiscal_year` and
`subaward_amount`, which every existing row already carries — so it was applied
while the host was down.

`data/clean/subawards.csv`: **49 → 52 columns**, gaining
`subaward_amount_real2025`, `deflator_factor_2025` and `inflation_base_year`,
from `data/clean/inflation_deflator.csv` (BEA NIPA 1.1.9, base 2025). **No
second deflator was introduced.** Row count unchanged at 63,548.

The header change means a rewrite, done exactly as
`115_pull_assistance_archive.py` did it: new columns appended at the END, the
file re-read immediately before writing, written to a temp file and swapped
atomically, with a timestamped `.bak`. Then verified field-by-field:

> **all 63,548 pre-existing rows byte-identical on all 49 original columns.**

**60,091 of 63,548 rows (94.6%) carry a real2025 value. Every one of the 3,457
blanks is FY2026**, because `inflation_deflator.csv` ends at 2025. No factor was
invented for a year the source does not cover.

### FINDING 4 — three Cedar datasets deflate FY2026 two different ways

Measured while doing this, not inherited from a doc:

| file | FY2026 `deflator_factor_2025` | rows |
|---|---|---:|
| `prime_contracts.csv` | **1.0** | 61,813 |
| `federal_funding_transactions.csv` | **blank** | 24,895 |
| `subawards.csv` (this build) | **blank** | 3,457 |

Both choices are defensible in isolation — `114_pull_prime_archive.py` argues in
its own docstring that "forecasting the index and presenting the forecast as a
measurement would be worse", and 1.0 is the honest limit of that argument — but
**a subscriber summing `*_real2025` across the three datasets silently gets
FY2026 included in prime contracting and excluded from funding and
subawards.** No total, count or date range reveals it.

This build took the conservative side and matched the funding file. **It did not
edit `prime_contracts.csv` or `series_breaks.csv`** — both are on the do-not-edit
list, and a cross-dataset convention is not one build's to settle. Recorded here
as a review item: `FY2026-DEFLATOR-CONVENTION`.

## 6. The match pipeline was validated offline while blocked

Rather than idle, `match` was smoke-tested against an existing small zip
(`fy2010`, 13,501 rows) with review and staging redirected to a scratch
directory and `--dry-run` set:

* all 13,501 rows streamed, both members, contract and assistance;
* every guard fired — `guard8_municipal_or_county_government` 2,331,
  `guard7_single_token_core` 1,986, `guard3_separate_legal_person` 1,289,
  `guard5_non_us_country` 232;
* `cedar_match_guard.guard()`, wired in as a **second veto layer after**
  `resolve_entity`, refused 2 further distinct cases the eight local guards had
  allowed — one on a folded identity token (`community`), one on an institution
  marker (`council`). It was imported and **not modified**;
* **0 new rows**, which is the correct answer: FY2010 is already in
  `subawards.csv` at that multiplicity. The dedupe-by-multiplicity check is
  therefore confirmed working on real data rather than asserted.

So when data lands, the only untested thing is the data.

## 7. Resume

The run is fully resumable and nothing needs to be re-derived.

```
py -3 code/121_pull_subawards_api.py canary            # is the fleet healthy?
py -3 code/121_pull_subawards_api.py pull --sequential # one job in flight, not five
py -3 code/121_pull_subawards_api.py collect           # accepted tokens only
py -3 code/121_pull_subawards_api.py match
py -3 code/121_pull_subawards_api.py append
py -3 code/121_pull_subawards_api.py codebook
py -3 code/81_build_passthrough_dataset.py
py -3 code/62_no_regression_check.py
```

`auto` chains the first two behind a peer-quiet wait and a bounded edge probe.

**Do not raise `MAX_INFLIGHT` back to 5.** Sequential is the post-2026-08-12
posture: one job in flight cannot produce five simultaneous server-side failures,
and the canary makes the cheap answer available before the expensive one.

## 8. Still owed

1. **FY2021, FY2022, FY2023, FY2024 subawards** — the whole of the gap. Nothing
   about it has changed except that the pull machinery now exists and is tested.
2. **The FY2020 procurement member.**
3. Whether the FY2020 contracts member is genuinely empty at source remains
   **unanswered**. The procurement-only job that would answer it failed with the
   others.
4. **Re-run when USAspending's bulk_download service recovers.** Start with
   `canary` — one two-day submission answers it in about a minute. Do not
   submit five fiscal years to find out.
5. `FY2026-DEFLATOR-CONVENTION` (FINDING 4) needs an owner's decision, applied
   across `prime_contracts.csv`, `federal_funding_transactions.csv` and
   `subawards.csv` together, not one at a time.

## 9. What was NOT produced, and why that is not a silent gap

`review/subaward_api_unresolved_<date>.csv` **was not written.** It is the
discovery pool of subawardees the ledger has never seen, and it is derived from
retrieved rows. With zero rows retrieved it would be an empty file, and an empty
review file reads as *"we looked and found nothing to rule"* — the
`NOT_FOUND` / `NOT_CHECKED` conflation this project treats as a distinct kind of
error. **NOT_CHECKED, because the source served nothing.** `match` writes it
automatically on the first successful pull.

The same applies to the pass-through refresh: `81_build_passthrough_dataset.py`
was re-run against the widened file and returned **1,262 rows / 212 pairs /
$712.3M / 166 entities — identical to before**, which is the correct outcome
when no subaward row was added, and confirms the 52-column file still reads
cleanly downstream.

---

## 2026-09-02 — `subawards.csv` has a primary key for the first time

*Workstream SUBAWARD-FUNDING, `code/910_subaward_report_id_backfill.py` and
`code/911_subaward_sub_leg_cedar_uid.py`. Zero network calls: every byte came
from zips already on disk.*

### What was blocking

`docs/DATASET_READINESS.md` had `subcontracting` BLOCKED on five contract
clauses, and four of them were one fact — **the file had no key at any arity**.
Measured on the live 76,859-row file before any change:

| candidate | duplicate rows |
|---|---:|
| `subaward_sam_report_id` | blank on 72,837 |
| `45.identity_key` (5 cols) | 17,894 |
| …+ `description` | 17,610 |
| …+ `duplicate_status` | 13,053 |
| …+ `source_file` | 17,264 |
| **the whole 56-column row** | **10,770** |

A file whose widest candidate — the entire row — collides has no key, and
`512.validate_grain` correctly turns a declaration made anyway into a
release-blocking violation. `GRAIN_WS1` and `GRAIN_WS4` both refused it, and on
the evidence they had, both were right.

### What changed the evidence

`121` diagnosed on 2026-09-01 that the FSRS extract **has always carried**
`subaward_sam_report_id` — one UUID per SAM filing, 765,109 of 765,109 distinct
on FY2021 — and that `94.build_row` reads 26 of the extract's 118 columns and
dropped it. 121 carried it on the 4,022 rows it appended. The other 72,837 were
promoted before the column existed, **and the zips they came from are still on
disk.**

`910` streamed all of them: 8,482,363 raw rows across four staging directories,
joined on `45.identity_key` (imported from 45, never restated), matching 76,668
raw rows to the clean file's 59,228 distinct identity keys.

    carried_by_121                 4,022
    recovered_unique              51,191
    recovered_group_bijection     20,644     N filings, N rows, N ids
    recovered_group_injection          4     Cedar retains a SUBSET of the
                                             source's filings; ids assigned
                                             injectively in (month, id) order
    no SAM id exists (HigherGov)     998     -> their own permalink instead
    REFUSED (rows > source filings)    0     the guard, proved by `selftest`

**The direction of the inequality is the whole rule.** M rows against N source
filings: M ≤ N is an injective assignment of real ids and invents nothing;
M > N is refused wholesale, because some row could only be given an id that is
not its own. It fires on 0 partitions today and
`910 ... selftest` proves it still fires.

### One staging directory was the difference between 97.7% and 100%

The first pass read only the two `data/raw/subcontracts/` folders and left
1,788 rows unrecovered. 606 of them came from four **loose**
`Assistance_Subawards_*.csv` extracts under `data/raw/federal_funding/` — the
same FSRS object, staged by a different puller, never zipped. **A recovery that
reads only the staging area it expected reports a source gap that is really a
search gap.** `RAW_DIRS` now names all four and the loose CSVs are read too.

### The published key, and why it is two columns

    primary key   (source_dataset, subaward_source_record_id)

`subaward_source_record_id` is the SOURCE's own id — the SAM UUID on 75,861
rows, HigherGov's per-subcontract permalink (already in `source_url`, 998 of
998 distinct, 0 blank) on the rest. `source_dataset` is the second half because
**347 rows are one filing Cedar holds twice**, once from `usaspending_fsrs_pull`
and once from `funding_forward_fill`. Both carry the same UUID because it IS
one filing; the second is already flagged `superseded_by_primary_source` and
already excluded from every money total.

### Conservation, and the duplicate allegation

| | before | after |
|---|---:|---:|
| rows | 76,859 | **76,859** |
| `sum(subaward_amount)` | $47,301,660,819.78 | **$47,301,660,819.78** |
| countable sum (`primary` ∧ not `exceeds_prime`) | $25,864,997,128.19 | **$25,864,997,128.19** |
| byte-identical whole rows | 10,770 | **0** |
| key blanks / collisions | — | **0 / 0** |
| columns | 66 → 69 (910) → 71 (911) | gained 5, lost 0 |

**Nothing was de-duplicated and no row was removed.** The 10,770 stopped being
byte-identical because the column that always separated them was put back. That
is the third time in this project: `prime_contracts.csv` (80,778 alleged, real
answer zero), `faads_transactions.csv` (1,001 alleged, real answer zero), and
now this.

### `911` — the subawardee leg

`cedar_uid` here is the PRIME's id, because `503_identity.py stamp` derives it
from the first of its `ID_COLS` present in the header and for this table that
is `prime_native_tribe_id`. 121's comment already said so and called the blanks
legitimate. They are — but they are 43,282 rows, **56% of the file**, and the
half that matters most for a Native-business dataset: a tribally owned firm
winning work UNDER a non-Native prime.

    prime_cedar_uid   33,503     (equals cedar_uid on every row — checked, V2)
    sub_cedar_uid     44,945
    at least one leg  76,785 / 76,859 = 99.90%

Resolved with `503.register_map()`, imported. `cedar_uid` is untouched: 503
owns it. **A handle the register does not know is left BLANK and listed in
`review/subaward_unresolved_leg_handles.csv`, never guessed.**

### What is still owed on the pull itself

> **UPDATED 2026-09-02T15:55Z. The fold-in HAPPENED, and the blocker moved.**
>
> `121 append` ran at **12:09:09Z** and wrote *"76,859 existing + 10,318
> appended = 87,177 rows, 71 columns (added [])"*, having verified all 76,859
> pre-existing rows byte-identical on all 71 columns. `fy2023_q3` was
> re-submitted and answered — **156,986 rows, retrieved 11:56:23Z** — so the
> premise below ("`fy2023_q3` failed") is dead. The enrichers named at the end
> of this section were then run: `910` (12:09Z), `911` (13:14Z), `871`.
>
> **The blocker is now `fy2023_q4`, and it is a header-only object, not a
> failure.** Measured today:
>
> | | |
> |---|---|
> | token | `All_Subawards_2026-09-02_H02M36S11241136.zip`, submitted 02:36:11Z |
> | server status | `finished`, `message: null` — **no error was reported** |
> | server seconds | **80.1**, against 2,809–4,087 for its four sibling quarters |
> | `rows_reported_by_server` | **0** |
> | on disk | 1,889 bytes; contracts member **4,144 bytes**, assistance member **3,992 bytes**, one newline each |
>
> **4,144 bytes is the exact signature of the FY2020 empty contracts member**
> this script was written to chase. The clean table shows the hole directly:
> 2023-07 / 08 / 09 hold **14 / 24 / 23** subaward rows against 484–704 in every
> neighbouring month. Zero is not credible as a fact about the world.
>
> **`staged()` was returning True for it**, because the record predates the code
> that writes `_empty_object` at the download site, so `pull` would have skipped
> it forever while `status` printed `finished`. The flag was set by hand from a
> live `zip_data_rows()` measurement — not assumed — with the basis recorded in
> `_state.json`, and `pull --only fy2023_q4 --sequential` then took the designed
> re-submit-once path at **15:42:31Z**.
>
> **And `fy2022_q1..q4` have never been submitted at all.** `121 status` prints
> `NOT SUBMITTED` for all four, and FY2022 still holds **89 countable rows /
> $47,021,525**. The full-year `fy2022` job is a corpse (`failed`, *"An error
> occurred."*, 221,865 rows reported before it died). That is the largest
> remaining hole in this dataset and it is a straight four-quarter re-run of the
> route that has now worked for eight quarters in a row.
>
> *The original paragraph follows; its reasoning about the schema guard is still
> the reason the append could run at all.*

**The FY2024 quarters were NOT folded in, and this is why.** `_state.json` shows
`fy2024_q1..q4` all `finished` with local files (210,619 / 156,690 / 131,921 /
195,021 rows) and `fy2023_q3` **failed**, so FY2023 is incomplete. More
immediately, `121`'s schema guard would have refused to run at all:
`871_promote_geo_keys_contracts.py` added ten `geo_*` columns to
`subawards.csv` at 01:14 on 2026-09-02 and they were in none of the guard's
fillable maps. That is now fixed — see `POST_PROMOTION_COLS` in 121 — so the
promotion can proceed. **Whoever runs it must run the enrichers afterwards**;
they are registered in `cedar_pipeline.KNOWN_ORDERINGS` and printed by the
guard itself:

    910 rescan → 910 apply → 911 apply → 871 → 81
