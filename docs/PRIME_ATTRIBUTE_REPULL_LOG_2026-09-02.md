# Prime contracting — the PSC / description re-pull

*Build log for `code/1085_prime_psc_desc_repull.py`, 2026-09-02. Every figure
was measured from the live `data/clean/prime_contracts.csv` on the day; the
per-object evidence is `data/raw/contracts/prime_attr_repull_2026-09-02/_SOURCE_MANIFEST.csv`
and `_state.json`, and the apply record is `docs/PRIME_ATTRIBUTE_REPULL.json`.*

**Status: PARTIAL and RESUMABLE. FY2008–FY2015 landed and are applied.
FY2016–FY2026 are queued behind an edge block that this run caused and that is
documented rather than worked around.**

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

Column fill, before → after:

| column | before | after |
|---|---:|---:|
| `product_or_service_code` | 247,987 (20.4%) | **574,011 (47.1%)** |
| `product_or_service_code_description` | 247,987 (20.4%) | **574,011 (47.1%)** |
| `award_base_description` | 247,987 (20.4%) | **573,320 (47.1%)** |
| `naics_description` | 247,987 (20.4%) | **561,536 (46.1%)** |

By fiscal year, on the archive stratum, PSC fill is now:

```
FY2008  99.7%   FY2013 100.0%   FY2018  11.3%   FY2023  73.9%
FY2009  99.9%   FY2014 100.0%   FY2019  17.4%   FY2024  86.3%
FY2010  99.9%   FY2015 100.0%   FY2020  24.4%   FY2025  85.1%
FY2011 100.0%   FY2016   4.7%   FY2021  34.0%   FY2026  94.2%
FY2012 100.0%   FY2017   6.8%   FY2022  47.7%
```

**The eight re-pulled years are at ~100%; the eleven that are not are still on
the gapfill corpus alone.** That contrast is the measurement of what the
re-pull buys, and it is why finishing it matters.

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

## To finish it

```
py -3 code/1085_prime_psc_desc_repull.py pull     # resumes at FY2016; idempotent
py -3 code/1085_prime_psc_desc_repull.py apply    # re-run; skips what is filled
py -3 code/1085_prime_psc_desc_repull.py verify
```

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
