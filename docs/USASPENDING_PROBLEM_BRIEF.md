# USAspending extraction — problem brief

*Cedar Press, 2026-08-12. Self-contained. Hand this to anyone helping solve it.*

> ## ⚠ TWO CORRECTIONS BEFORE YOU ACT ON THIS BRIEF. Flagged 2026-08-26.
>
> This brief carries a heading reading *"Verified by direct measurement on 2026-08-12, not
> from memory."* That was true when written and the merge it describes as pending completed
> the same day. **Two of its statements will now send someone to do work that is already
> done, or to skip work that is possible.**
>
> **1. The backfill IS merged.** Line 29 says the 631,507-row full-universe backfill is
> *"not yet merged"*, and line 28 gives prime as **826,637 rows**. `AGENTS.md:728` records
> the merge (`826,637 → 1,217,768`), and `data/clean/prime_contracts.csv` holds
> **1,217,768 rows, FY2000–2026, $310.01B** as of 2026-08-26. **Do not re-run the merge.**
> Re-running a completed merge is the same shape as the `09_import_rulings.py` accident
> that destroyed 1,327 ledger rows.
>
> **2. The static archive DOES reach FY2007.** Line 51 says *"The static archive only goes
> back to FY2008. FY2000–2007 prime contracts cannot be fixed this way. This is an open
> problem."* `docs/PRIME_ARCHIVE_PULL_LOG.md` measured it: `_All_Contracts_Full_` exists for
> **FY2007 through FY2026**. There is no FY2000–FY2006 file, but **FY2007 is retrievable**,
> and `START_HERE.md` classifies its absence as a **host edge-block, not absence**.
>
> This matters more than one year sounds. The SAM.gov backfill is scoped FY2000–**2007** off
> this brief's floor, and SAM is capped at **10 requests/day** until the pending org-role
> grant lands. Spending that budget on a year the free archive already serves is expensive.
> **Scope the SAM backfill FY2000–FY2006.**
>
> Line 32's *"Financial assistance | 608,419 | complete for its span"* is also stale:
> `docs/ASSISTANCE_ARCHIVE_PULL_LOG.md:364` records **608,419 → 684,923 (+76,504)**, which
> is the file's size today. *"Complete for its span"* is the phrase that discouraged the
> check that found those rows.

---

## THE GOAL

A complete, entity-resolved panel of US federal money flowing to Native
entities — tribal governments, Alaska Native corporations, Native Hawaiian
organisations, and their enterprises. Three legs, all needed:

1. **Prime contracts** (procurement) — **FY2000 → present**
2. **Subawards / subcontracts** (FSRS) — as far back as they exist
3. **Financial assistance** (grants, loans, direct payments) — **FY2001 → present**

The 2001-onward requirement is firm. Short panels are the binding constraint on
everything downstream.

---

## WHERE WE ACTUALLY ARE

Verified by direct measurement on 2026-08-12, not from memory.

| leg | rows | span | status |
|---|---:|---|---|
| Prime contracts (working file) | 826,637 | FY2000–2026 | FY2000–2022 is a **filtered** extract, see below |
| Prime contracts (full-universe backfill, staged) | 631,507 | FY2008–2022 | downloaded, **not yet merged** |
| Financial assistance | 608,419 | FY2007–2026 | complete for its span |
| FAADS (pre-2008 assistance) | 2,769,748 | FY2001–2007 | on disk, **not merged**, separate schema |
| Subawards | 63,548 | 2001–2026 | **FY2021–24 effectively empty** |

### Problem A — the prime panel's early years are a filtered subset

FY2000–2022 came from a Bloomberg Government export that had to be filtered at
download time to where Native entities were most likely to appear. It is not the
full universe. The cost is measurable now that full-universe archive files exist
for the same years:

| FY | filtered (BGOV) | full universe | gap |
|---|---:|---:|---|
| 2012 | 33,793 | 42,322 | +25% |
| 2020 | 35,365 | 45,713 | +29% |

An earlier reconciliation on FY2022 found **20 Native entities present in the
full universe and absent from the filtered file**, while 96.3% of contracts
present in both agreed within 0.5% on dollars. So the filter's damage is
**missing entities**, not wrong numbers — which is the worse failure for us.

**The static archive only goes back to FY2008.** FY2000–2007 prime contracts
cannot be fixed this way. This is an open problem.

### Problem B — subawards FY2021–24 are missing outright

| FY | rows | comparable year |
|---|---:|---|
| 2019 | 9,373 | — |
| 2020 | 3,884 | half-populated |
| **2021** | **173** | should be ~9,000 |
| **2022** | **89** | should be ~9,000 |
| **2023** | **120** | should be ~9,000 |
| **2024** | **166** | should be ~9,000 |

Roughly **35,000 rows missing**. The 548 rows that do exist for those years came
from a third-party export and a forward-fill, not from the source.

Established three independent ways: the job-state file holds 22 completed jobs
and fy2021–fy2024 are not among them; all 6,613,471 raw rows carry a fiscal year
equal to their own job's, so the missing years are not hiding in a neighbouring
file; and every FY2021–24 row names a non-USAspending provenance.

### Problem C — pre-2008 assistance is a different dataset

FAADS was the federal assistance reporting system **through FY2007**; USAspending
replaced it in FY2008. We hold 2.77M FAADS rows covering FY2001–2007 (1.07 GB),
but they are in a separate file with a different schema and have never been
harmonised with the FY2007+ file. This is not a gap in coverage — it is
unmerged work, with a genuine series break at FY2008 that must be documented,
not smoothed over.

---

## THE BLOCKER — what actually failed

**`POST https://api.usaspending.gov/api/v2/bulk_download/awards/`** is the only
route that serves FSRS subaward data. No API key is required.

On 2026-08-12, nine jobs were submitted over 80 minutes. **Every submission was
accepted with HTTP 200 and a `file_name` token. Every job then failed
server-side** with the generic message:

```
status:  failed
message: "An error occurred."
```

Submissions were spaced 180 seconds apart; total request count for the run was
about 35. Timeline:

```
16:11:15  GET /api/v2/references/agency/456/  -> HTTP 200 in 0.46s (host healthy)
16:11:17  fy2021 submitted -> ACCEPTED, token All_Subawards_2026-08-12_H16M11S17061900.zip
16:14:18  fy2022 -> ACCEPTED
16:17:19  fy2023 -> ACCEPTED
16:20:21  fy2024 -> ACCEPTED
16:23:22  fy2020_procurement -> ACCEPTED
16:25:53  fy2021, fy2022, fy2023 -> status: failed, "An error occurred."
16:28:25  fy2024, fy2020_procurement -> same. All five dead.
16:31:21  HEAD files.usaspending.gov -> HTTP 500, 0 bytes
16:32:44  HEAD files.usaspending.gov -> RemoteDisconnected in 0.5s
~16:35    GET api.usaspending.gov      -> RemoteDisconnected in 0.43s
17:05     edge block clears; job failures continue afterwards
```

### What has been RULED OUT — do not re-suggest these

Three deliberately cheap two-day probes, each designed to kill one explanation.
Two days of data generated in 37 seconds on this same endpoint on 2026-08-05.

| probe | filter | window | outcome | kills the theory |
|---|---|---|---|---|
| `diag_sub_2021` | `sub_award_types` | 2021-10-01..02 | FAILED | — |
| `diag_sub_2015` | `sub_award_types` | 2015-10-01..02 | FAILED | "the FY2021–24 window is broken" — that range downloaded fine a week earlier |
| `diag_prime_2021` | `prime_award_types` | 2021-10-01..02 | FAILED | "`sub_award_types` is broken" — endpoint understood it, named the output `All_PrimeTransactions_…zip`, failed identically |

So, already excluded:

- ❌ **"The jobs are too big"** — a two-day job failed.
- ❌ **"Split the years / add workers / parallelise"** — a two-day job failed, so
  smaller units do not help. **This is the key point for anyone proposing
  parallelisation.**
- ❌ **"We're rate-limited"** — one submission into a host answering HTTP 200.
- ❌ **"Our payload is malformed"** — the server accepted it, tokenised it, and
  named the output file.
- ❌ **"It's a subaward-specific bug"** — the prime-award control failed too.
- ❌ **"api and files are separate hosts so we have two budgets"** — both refused
  the same IP within two minutes, identical sub-second `RemoteDisconnected`.

**Working verdict: the entire `bulk_download` service was generating nothing on
2026-08-12**, independent of who was asking. The correct response is to retry
later, not to redesign. A one-minute canary now exists to test this before
committing to a real pull.

**What is NOT yet ruled out and is worth attacking:** whether the outage is
persistent, and whether a route exists that bypasses `bulk_download` entirely.

---

## WHAT WE WANT HELP WITH

### Q1 — is there a bulk route that bypasses `bulk_download` entirely?

The most promising untested lead is the **full USAspending PostgreSQL database
download** (nightly dumps published under `files.usaspending.gov`, distinct from
the per-year "Award Data Archive" zips we already use). If that includes the
FSRS subaward tables, it solves subawards, prime, and assistance in one move and
removes the dependence on a job-queue service that can silently fail.

Open questions: does the dump include subawards; what is the actual size and is
there a delta/incremental option; what Postgres version and restore path; is
there a schema-only manifest that can be inspected before committing to the
download.

**Hard constraint: the machine currently has ~3 GB of free disk.** A
multi-hundred-GB restore is not feasible without either freeing space or pulling
a subset. Advice on extracting selected tables from a dump *without* a full
restore would be directly useful.

### Q2 — how do we get FY2000–2007 prime contracts?

The static archive begins at FY2008. FPDS-NG is the system of record for
procurement back to the 1970s and exposes an ATOM feed. Is that feed still live,
what is its paging behaviour and rate limit, and does it serve complete
historical years? Any other mirror of pre-2008 FPDS in bulk form is of interest.

### Q3 — is FSRS reachable outside USAspending?

Subaward data originates in FSRS (`fsrs.gov`), which fed into SAM.gov. If a
direct bulk export exists there, it would remove a single point of failure.

### Q4 — is there a public mirror of the archive files?

Anything that mirrors `files.usaspending.gov/award_data_archive/` — data.gov,
academic mirrors, cloud public-dataset programmes — would provide a fallback
when the origin misbehaves.

### Q5 — is the outage still on, and how would we know cheaply?

A one-shot health check we can run before every pull, that distinguishes "service
degraded" from "our request is wrong". Right now the only signal is submitting a
job and waiting, and acceptance does not predict success.

---

## A ROUTE THAT IS ALREADY KNOWN-BAD

**Do not suggest `/api/v2/search/spending_by_award/` as a substitute.** It
returns **cumulative snapshots**, not transactions, and summing them inflates
totals by roughly **2.2×**. This was measured and is a settled finding here. Two
further known behaviours of that endpoint: the six award-type families cannot be
mixed in one request (HTTP 422), and `recipient_uei` is ignored as a filter —
`recipient_search_text` must be used instead.

---

## OPERATING CONSTRAINTS

- **Python**, invoked as `py -3`. Windows 11, 28 logical cores, 15.7 GB RAM,
  **~3 GB free disk** (the binding limit).
- **One poller per host**, and `api.` and `files.` must be treated as **one**
  rate-limit budget, since a block hit both within two minutes.
- Any long run needs a wall-clock deadline and must **stop on the first refusal**
  rather than retry into a ban. A backoff bounds the request *rate*, not the
  total run.
- **No API key is required** for any USAspending endpoint discussed here.
- Everything must land as dated observations with source URL, fetched date, and
  provenance. Existing rows are never overwritten.
