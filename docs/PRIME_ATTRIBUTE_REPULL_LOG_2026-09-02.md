# Prime contracting — the PSC / description re-pull

*Build log for `code/1085_prime_psc_desc_repull.py`, 2026-09-02. Every figure
was measured from the live `data/clean/prime_contracts.csv` on the day; the
per-object evidence is `data/raw/contracts/prime_attr_repull_2026-09-02/_SOURCE_MANIFEST.csv`
and `_state.json`, and the apply record is `docs/PRIME_ATTRIBUTE_REPULL.json`.*

**Status: COMPLETE. All nineteen archive objects (FY2008–FY2026) were
re-fetched and applied. PSC is on 840,754 of 1,217,768 rows — 99.97% of the
841,002-row archive stratum, which is the structural ceiling.**

> ### CLOSED 2026-09-02T15:38Z — and the apply had to be run TWICE
>
> The eleven objects this log left QUEUED were fetched between 12:12Z and
> 15:09Z, after the edge block cleared, at the 480s pacing this script gained
> from causing it. Every one answered HTTP 200 on stamp `20260806`; **no year
> was recorded absent and no stamp went unresolved.**
>
> **The 10:45Z apply had been reverted before those objects landed.**
> `871_promote_geo_keys_contracts.py` rebuilt `prime_contracts.csv` at 09:11Z
> and left the evidence beside it as
> `prime_contracts.csv.REVERTED_BY_871_2026-09-02_kept_as_evidence`; measured
> at 15:34Z, `product_or_service_code` was back at **247,987 (20.4%)**, the
> pre-1085 value, on the nose. This is the fourth instance of the
> rebuild-versus-in-place collision `START_HERE.md` records, and the standing
> rule held: **the enricher runs LAST.** Nothing was lost, because `pull`
> keeps its attribute files on disk and `apply` is a pure re-run.
>
> **Its pre-1085 backup was stale and would have made `verify` lie.** The
> backup on disk was taken at 06:33Z, three rebuilds ago, so `verify`'s
> INV-ATTR-1 would have compared the live file against a vintage that no
> longer describes it. It was renamed
> `...pre_1085_prime_psc_desc_repull.superseded_by_871_revert_kept_as_evidence`
> so a fresh, correct comparand could be written. **A conservation check
> against the wrong baseline is worse than none.**
>
> | | 10:45Z apply (8 files) | 15:38Z apply (19 files) |
> |---|---:|---:|
> | attribute keys available | 326,166 | **592,925** |
> | rows newly filled | 326,166 | **592,925** |
> | non-blank values overwritten | 0 | **0** |
> | rows | 1,217,768 → 1,217,768 | **1,217,768 → 1,217,768** |
> | obligations | conserved to the cent | **$310,005,258,661.21 → $310,005,258,661.21, conserved to the cent** |
> | `verify` | exit 0 | **exit 0** |
> | `selftest` | exit 0 | **exit 0 — both invariants proven to FIRE on an injected violation, then restored** |
>
> Column fill on the whole table, against the 20.4% this log was written to fix:
>
> | column | at 06:00Z | **now** | of the 841,002 archive rows |
> |---|---:|---:|---:|
> | `product_or_service_code` | 247,987 (20.4%) | **840,754 (69.04%)** | **99.97%** |
> | `product_or_service_code_description` | 247,987 (20.4%) | **840,738 (69.04%)** | 99.97% |
> | `award_base_description` | 247,987 (20.4%) | **840,079 (68.99%)** | 99.89% |
> | `naics_description` | 247,987 (20.4%) | **827,858 (67.98%)** | 98.44% |
> | `naics_code` (6-digit) | 838,229 (68.83%) | 838,229 (68.83%) | unchanged — it never needed the re-pull |
>
> PSC fill per fiscal year, **as a share of that year's archive rows**, is now
> 99.7% or better in all nineteen years (FY2008 99.7 · FY2009 99.9 · FY2010 99.9
> · FY2011–FY2026 100.0). The FY2016 4.7% / FY2017 6.8% / FY2018 11.3% figures
> in the table further down are the pre-resume state and are dead.
>
> **The 376,766 rows that remain blank are not a shortfall and no re-pull
> reaches them.** They carry no `contract_transaction_unique_key` because a
> BGOV / master-prime row is a (contract, parent vehicle, fiscal year, vendor)
> aggregate rather than an FPDS transaction, so there is no transaction for a
> key to name. `award_attributes_basis` says which state a row is in per row.
> **Do not quote 69% as a coverage failure without that denominator.**

---

## What was wrong, and why it was not laziness

`docs/COLUMN_PROMOTION_LOG_2026-09-02.md` promoted nine columns onto
`prime_contracts.csv` and got three of them to only **20.4% (247,987 of
1,217,768)**, booking the rest `NOT_ACQUIRED`. That was the right call and the
reason is on disk:

`114_pull_prime_archive.py :: release()` deletes each
`FY*_All_Contracts_Full_*.zip` after filtering it down to
`filtered/FY####_ledger_rows.csv`. Measured 2026-09-02 across all twenty of
those files: **35 columns, one signature, every file.** They carry
`contract_transaction_unique_key` and `naics_code` and they carry **no**
`product_or_service_code`, **no** `naics_description` and **no** description
column of any kind. The projection is lossy and the source object is gone.

What `release()` kept is what makes this recoverable: url, http_status, bytes,
md5 and the S3 multipart etag, per year, in `_SOURCE_MANIFEST.csv`. FY2008's
recorded size is 1,308,576,327 bytes and the object re-fetched today is
1,308,576,327 bytes — **the same object, provably.**

## The route

One host, `files.usaspending.gov`, plain GET on static S3 objects, **zero
requests to `api.usaspending.gov`**. Per year: HEAD each candidate stamp until
one answers 200 → download → stream every CSV member → keep four columns for
the 593,015 transaction keys that need them → write `FY####_attrs.csv` →
**delete the zip**. Exactly one zip on disk at a time.

**The stamp is probed per year and never assumed.** Measured today:
`20260806` answers 200; `20260706` **404s** — and eleven years of
`prime_contracts.csv` carry `20260706` in `source_file`. A hard-coded stamp
would have 404'd on every year and read as "the archive does not have it."

Four columns, all attributes, joined on `contract_transaction_unique_key`:

| written to `prime_contracts.csv` | read from the archive |
|---|---|
| `product_or_service_code` | `product_or_service_code` |
| `product_or_service_code_description` | `product_or_service_code_description` |
| `award_base_description` | `transaction_description` |
| `naics_description` | `naics_description` |

**No money, entity, tier, attribution or provenance column is touched, no row
is added or removed, and a non-blank value is never overwritten** — 0 rows had
one to overwrite.

## What landed

| | rows scanned in the archive | attribute rows kept |
|---|---:|---:|
| FY2008 | 4,505,732 | 41,397 |
| FY2009 | 3,497,692 | 43,213 |
| FY2010 | 3,543,904 | 45,471 |
| FY2011 | 3,408,506 | 46,554 |
| FY2012 | 3,129,630 | 41,837 |
| FY2013 | 2,515,088 | 35,891 |
| FY2014 | 2,528,544 | 35,646 |
| FY2015 | 4,375,316 | 36,157 |
| **total** | **27,504,412** | **326,166** |

Apply, `code/1085 apply`:

| | |
|---|---:|
| rows | 1,217,768 → 1,217,768 **conserved** |
| obligations | $310,005,258,661.21 → $310,005,258,661.21 **conserved to the cent** |
| rows newly filled | 326,166 |
| non-blank values overwritten | **0** |
| `verify` | exit 0 |
| `selftest` | exit 0 — both invariants proven to FIRE on an injected violation |

Column fill, before → after — **these are the EIGHT-OBJECT PARTIAL RUN's
figures and are superseded; the closing table at the top of this file has
the final ones (PSC 840,754 / 69.04%). Kept because they are the measured
midpoint that shows what each tranche of objects bought:**

| column | before | after (partial, 8 of 19 objects) |
|---|---:|---:|
| `product_or_service_code` | 247,987 (20.4%) | **574,011 (47.1%)** |
| `product_or_service_code_description` | 247,987 (20.4%) | **574,011 (47.1%)** |
| `award_base_description` | 247,987 (20.4%) | **573,320 (47.1%)** |
| `naics_description` | 247,987 (20.4%) | **561,536 (46.1%)** |

By fiscal year, on the archive stratum, PSC fill **at the partial-run
midpoint** was — every one of these is now 99.7% or better; see the
closing table:

```
FY2008  99.7%   FY2013 100.0%   FY2018  11.3%   FY2023  73.9%
FY2009  99.9%   FY2014 100.0%   FY2019  17.4%   FY2024  86.3%
FY2010  99.9%   FY2015 100.0%   FY2020  24.4%   FY2025  85.1%
FY2011 100.0%   FY2016   4.7%   FY2021  34.0%   FY2026  94.2%
FY2012 100.0%   FY2017   6.8%   FY2022  47.7%
```

**The eight re-pulled years are at ~100%; the eleven that are not are still on
the gapfill corpus alone.** That contrast is the measurement of what the
re-pull buys, and it is why finishing it matters. **It was finished the same
day** — all eleven remaining objects landed between 12:12Z and 15:09Z and every
year is now 99.7% or better.

## What stopped it, and why the run stopped rather than pushing through

At 10:36:24Z, on the ninth object, `files.usaspending.gov` began answering HEAD
with an instant `RemoteDisconnected` — under a second, on all four stamp
candidates, for FY2016 and again for FY2017. That is an **edge block**, and
this run caused it: eight objects totalling ~9.4 GB in twenty-six minutes with
no inter-object pause. It is the same shape as FINDING 6 in the host lock (six
~2 GB objects in twelve minutes, 2026-08-08).

**Seventy-eight seconds later `api.usaspending.gov` refused a peer** —
`code/121_pull_subawards_api.py`'s cheap status GET, after twenty-five minutes
of clean 200s. A control request to `www.federalregister.gov` returned HTTP 200
in 0.66s, so it is not the network. **The two subdomains share a rate limiter**,
which contradicts what the host lock and `121` both currently tell an agent.
Written up in the new 2026-09-02 section of `docs/PULL_DISCIPLINE.md`.

The puller was **stopped by hand**, by PID, immediately — not left retrying.

### Three defects in this script, found by the block and fixed

1. **`resolve_stamp()` treated an edge refusal as a per-year fact.** It logged
   it, slept 30s, tried the next stamp, then returned `None` and let the caller
   record the year as `stamp_unresolved` **and move on to the next year** —
   four fresh requests per year against a host refusing us for request rate. It
   now raises `EdgeBlocked` on a sub-second disconnect, and `pull` breaks out
   of the year loop and checkpoints. A 404 still means only what a 404 means:
   that one key is absent. A year is recorded absent **only when every
   candidate stamp 404s.**
2. **Two years were written down as `stamp_unresolved`** — a permanent record
   saying FY2016 and FY2017 could not be resolved, when what happened is that
   the host would not answer. Corrected in `_state.json` to
   **`edge_refused_not_an_absence`**, with the reason.
3. **`fetch()` retried an instant disconnect on a fresh connection.** It now
   raises rather than retry; retrying is what extends a block.

Pacing added: `INTER_OBJECT_PAUSE_S`, default **480 seconds**. Two independent
measurements bound the safe rate from above and neither bounds it from below,
so the honest statement is *"slower than one object every three minutes, and we
do not know how much slower."*

## ~~To finish it~~ — FINISHED 2026-09-02T15:38Z

```
py -3 code/1085_prime_psc_desc_repull.py pull     # all 19 years now `filtered`; a re-run is a no-op
py -3 code/1085_prime_psc_desc_repull.py apply    # re-run after ANY rebuild of prime_contracts.csv
py -3 code/1085_prime_psc_desc_repull.py verify   # exits 1 on breach
```

**`apply` is the command that matters from here.** The nineteen `FY*_attrs.csv`
files are on disk and are the whole cost of the re-pull; re-applying them takes
about 25 seconds and no network requests. Anything that rebuilds
`prime_contracts.csv` reverts the four columns and `apply` puts them back.

`pull` skips any year already `filtered`, so a resume costs only the eleven
outstanding objects (~14 GB, ~2.5 hours at the 480s pacing). Wait for the
block to clear first — the 2026-08-05 cooldown lifted about 62 minutes after
traffic dropped — and probe with a single HEAD, never with the job.

**Expected end state:** PSC and PSC description on **~838,000 of 841,002
archive rows**, i.e. **~68.8% of the whole table**. That is the structural
ceiling and it is not reachable past: the other **376,766 rows are BGOV /
master-prime lineage and carry no `contract_transaction_unique_key` at all**,
because no such key exists for them — a BGOV row is a (contract, parent
vehicle, fiscal year, vendor) aggregate, not an FPDS transaction. There is
nothing to join on, and `award_attributes_basis` says so per row rather than
leaving a reader to guess whether a blank means "not acquired" or "not
applicable."

## Standing note

**This is an IN-PLACE ENRICHER.** A rebuild of `prime_contracts.csv` by
`114_pull_prime_archive.py` or `131_merge_archive_backfill.py` reverts all four
columns. The signal is
`data/clean/prime_contracts.csv.bak_*_pre_1085_prime_psc_desc_repull` sitting
beside the table. Re-run 1085 `apply` after any rebuild, and after `871`, which
is the other in-place enricher on this file. The ordering rule is the one
`START_HERE.md` earned four times over: **the enricher runs LAST.**
