# Assistance archive pull — `files.usaspending.gov`, 2026-08-07/08

*Runner: `code/115_pull_assistance_archive.py`. Host lock:
`logs/_HOSTLOCK_files.usaspending.gov.json`. Raw:
`data/raw/usaspending_archive_2026-08-07/`. Run log:
`logs/115_assistance_archive.log`.*

**Status (2026-08-07/08 run): PARTIALLY COMPLETE. SEE THE 2026-08-12 UPDATE AT THE FOOT OF THIS FILE - the stamp has since rolled to 20260806 and the resume command below now 404s. Priority 1 (federal funding FY2024–FY2026) is
done. The credit-instrument backfill stopped at FY2007 when the host edge-blocked
us; FY2008–FY2023 are still owed. Gap 3 (subawards) is IMPOSSIBLE from this host
and the reason is a property of the source.**

---

## Why a different host

`api.usaspending.gov` edge-blocked this project twice on 2026-08-07 and its
`/search/` endpoints returned HTTP 503 through a full exponential backoff
(`logs/44_contracts_transactions.log`, 18:01–18:32Z and 23:25–23:56Z).

`files.usaspending.gov` is a **different host** serving static S3 objects out of
the bucket `dti-usaspending-monthly-downloads`. **No request was made to
`api.usaspending.gov` by this build — not even a probe.**

---

## What the archive actually contains

Full enumeration, 5 pages. The listing is **ListObjects v1**: it returns
`<Marker>` and `<IsTruncated>` with `MaxKeys` 1000, so pagination is by
`?marker=<last key>`. The v2 form (`?list-type=2&continuation-token=`) is not
what this endpoint answers, and the difference is invisible until page 2.
Listing saved at `data/raw/usaspending_archive_2026-08-07/_archive_listing.csv`.

**4,631 objects, 12 filename shapes:**

| n | shape |
|---:|---|
| 2000 | `FY####_###_Assistance_Full_########.zip` (3-digit agency) |
| 2000 | `FY####_###_Contracts_Full_########.zip` |
| 240 | `FY####_####_Assistance_Full_########.zip` (4-digit agency) |
| 240 | `FY####_####_Contracts_Full_########.zip` |
| 20 | `FY####_All_Assistance_Full_########.zip` ← used here |
| 20 | `FY####_All_Contracts_Full_########.zip` |
| 60 | `FY(All)_###_Contracts_Delta_########.zip` |
| 38 | `FY(All)_###_Assistance_Delta_########.zip` |
| 8 | `FY(All)_####_Contracts_Delta_########.zip` |
| 3 | `FY(All)_####_Assistance_Delta_########.zip` |
| 1 | `FY(All)_All_Assistance_Delta_########.zip` |
| 1 | `FY(All)_All_Contracts_Delta_########.zip` |

Every one of the 4,631 keys carries stamp **20260706**; max `LastModified` is
2026-07-10T15:38:11Z. **There is nothing newer to probe for.** Measured, not
assumed. The `_All_` series covers **FY2007–FY2026**.

---

## FINDING 1 — the archive publishes NO subaward file

**Zero of the 4,631 keys contain the string `sub` in any case.** Direct probes:

| URL | status |
|---|---|
| `award_data_archive/FY2024_All_Subawards_Full_20260706.zip` | **404** |
| `award_data_archive/FY2020_All_Subawards_Full_20260706.zip` | **404** |
| `subaward_data_archive/` · `subaward_archive/` · `subawards/` | 404 |
| `monthly_downloads/` · `database_download/` | 404 |
| `reference_data/` | 403 |
| `generated_downloads/` | 403 on the listing; individual objects DO serve |

So the third gap — **subawards FY2021–FY2024, and the missing FY2020 contract
subawards — cannot be closed from this host.** FSRS subaward data is served only
by `api.usaspending.gov` `/api/v2/bulk_download/awards/` with `sub_award_types`,
which is the blocked host. The job stays queued in
`logs/_HOSTLOCK_api.usaspending.gov.json`.

**One route that does work through this host, for future use:**
`files.usaspending.gov/generated_downloads/<file_name>.zip` serves the output of
an API job the server has *already accepted*. A job token persisted in a
`_state.json` can therefore be collected without touching the API. It does not
help here: the FY2021–FY2024 subaward jobs were never submitted, so no token
exists.

---

## FINDING 2 — the FY2020 contract-subaward member is a header with no rows

`data/raw/subcontracts/usaspending_subawards_2026-08-05/All_Subawards_2026-08-06_H02M44S03640497.zip`
contains both members, and the contracts one is **4,144 bytes: one header line,
zero data rows.**

| FY | contracts member | assistance member |
|---|---:|---:|
| 2019 | 438,869,613 B | 754,006,169 B |
| **2020** | **4,144 B (header only)** | 784,659,068 B |
| 2025 | 218,916,619 B | 799,676,554 B |
| 2026 | 66,880,368 B | 501,077,692 B |

The FY2020 zero is **not a parsing miss** — nothing was skipped locally. The
server returned an empty contracts member for that job. Neighbouring years hold
5,047 (FY2018) and 5,987 (FY2019) Native-linked contract subawards, so zero for
FY2020 is not credible as a fact about the world. It is a **defective job that
must be re-submitted against the API**, and that cannot be done while that host
is blocked.

---

## The population seam, and why it is a column rather than an adjustment

`federal_funding_transactions.csv` FY2008–FY2023 is **not** full-universe
assistance. Across all 476,924 pre-existing rows, `business_types_code` takes
exactly three values — I, K, J — i.e. USAspending Recipient Type
"Indian/Native American Tribal Government". The archive files are full universe.

Filtering the archive on ledger identifiers alone would have silently changed
what the series counts: it would add ledger-known corporations carrying no
tribal recipient-type code, and drop tribal-coded recipients whose UEI the
ledger has never seen. No total, count or date range would have revealed it.

Rows are kept under a **union of two legs**, recorded on every row in
`population_basis`:

| value | rows in the file now | meaning |
|---|---:|---|
| `recipient_type` | 495,985 | `business_types_code` contains I, J or K — reproduces the FY2008–2023 population exactly |
| `both` | 96,191 | both legs fire |
| `ledger_uei` | 12,950 | ledger identifier only |
| `ledger_uei_withheld` | 3,293 | ledger leg only, and the state-agreement guard refused it (Finding 3) |

Filter `population_basis NOT LIKE 'ledger_uei%'` to reproduce the original
series. **Identifier join only — no name matching was performed on any archive
file.**

`source_file` is the other half of the seam: **476,924 rows carry the API-route
value and 131,495 carry an archive object name.**

---

## FINDING 3 — the identifier ledger's UEI leg proposes large false attributions

The first FY2024 extract surfaced this and it is not small. The ledger maps UEIs
to entities that are a different organisation in a different state:

| withheld $ | rows | ledger proposed | recipient actually filing |
|---:|---:|---|---|
| 1,782,219,598 | 389 | Pueblo of Santa Clara (NM) | SANTA CLARA COUNTY HOUSING AUTHORITY (CA) |
| 190,800,953 | 226 | Pueblo of Santa Ana (NM) | SANTA ANA, CITY OF (CA) |
| 125,091,952 | 327 | "Manchester" (CA) | MANCHESTER HOUSING & REDEVELOPMENT AUTHORITY (NH) |
| 81,470,686 | 305 | Peoria Tribe of Oklahoma (OK) | PEORIA HOUSING AUTH (IL) |
| 58,982,888 | 174 | Bois Forte (MN) | BOISE CITY ADA COUNTY HOUSING (ID) |
| 35,764,440 | 286 | Winnebago (NE) | WINNEBAGO COUNTY HOUSING AUTHORITY (IL) |

Every one is the short-name collision AGENTS.md records 161 of in the spine, and
every one would have published as Native federal funding.

**The guard applied** is the one AGENTS.md names as working: *require a state
agreement*. It is not name matching, and it is not used to **detect** a match —
only to **refuse** one the ledger already proposed, which is the only direction
that file permits. It is asymmetric on purpose:

* `population_basis == 'ledger_uei'` (ledger is the **only** evidence) and the
  states disagree → **attribution withheld**. The row is kept, the proposed
  entity is preserved in `ledger_proposed_tribe_id`, and the dollars go to the
  review queue.
* `population_basis == 'both'` (USAspending independently codes the recipient as
  a tribal government or tribally designated organisation) → the disagreement is
  **recorded in `state_agreement`** and nothing is withheld. Tribes operate
  across state lines and a second independent federal leg is real evidence.

**Result: 99 recipients, 3,293 rows, $2,503,254,778 held out of Native totals**
→ `review/assistance_archive_ledger_state_disagreement_2026-08-07.csv`.

**The guard also refuses some TRUE attributions, and that is disclosed, not
hidden.** Navajo Technical University (NM) under the Navajo Nation (spine state
AZ) is $73.9M; ASRC Federal Holding Company (MD) under Arctic Slope Regional
Corporation (AK) is $12.6M; Navajo Transitional Energy Company (CO) is $6.6M.
All three are almost certainly correct and were withheld anyway. Every one of
the 99 carries a `YOUR_RULING` column. A conservative refusal that lands in a
queue is recoverable; a false attribution that ships is not.

This is a **ledger defect, not an artefact of this pull.** The same UEI rows will
be proposing the same attributions anywhere else the ledger is joined.

---

## FINDING 4 — a new assistance-type taxonomy appears from FY2024

The FY2008–FY2023 series takes exactly seven `assistance_type` values
(02/03/04/05/06/10/11). The archive shows a second, lettered taxonomy running
alongside the numeric one:

| code | description | first seen |
|---|---|---|
| `F001` | GRANT | FY2024 (2 rows), FY2026 (640 rows) |
| `F002` | COOPERATIVE AGREEMENT | FY2026 (139 rows) |
| `F010` | OTHER FINANCIAL ASSISTANCE | FY2026 (4 rows) |

In FY2026 the lettered codes are **783 of 24,908 kept rows (3.1%)** and rising.
A consumer grouping on `assistance_type` will silently split grants across `03`,
`04` and `F001`. **This is a candidate row for `series_breaks.csv`, which this
build did not edit.**

---

## FINDING 5 — type 09 (insurance) does NOT behave like 07 and 08

`docs/DATA_ODDITIES.md` records that credit types 07/08/09 report
`obligated_usd` as exactly 0.00 by design. Measured on the 82 credit rows
retrieved here, that holds for **07 and 08 only**:

| type | rows | obligation | face value | subsidy cost |
|---|---:|---:|---:|---:|
| 07 direct loan | 63 | 0.00 | 287,767,030.00 | 80,014,136.17 |
| 08 guaranteed/insured loan | 12 | 0.00 | 14,006,000.00 | 380,695.00 |
| **09 insurance** | **7** | **1,297,392.00** | **0.00** | **0.00** |

All seven type-09 rows are FY2007 and all seven carry a **non-zero obligation
and no face value at all**. The script flags this as
`credit_rows_with_NONZERO_obligation` rather than assuming the documented rule.
`DATA_ODDITIES.md` was not edited; this is a measurement against it.

---

## What landed

`_SOURCE_MANIFEST.csv` carries url, HTTP status, bytes, md5, content-type,
magic-bytes check, member list and row counts for every object.

| FY | object bytes | md5 | scanned | kept | rec_type | both | ledger | tier X | credit |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 2007 | 155,621,381 | a7aa5b5e… | 1,023,900 | 11,443 | 2,883 | 3,041 | 5,519 | 40 | 45 |
| 2024 | 1,354,904,435 | 88f6460f… | 5,194,878 | 50,690 | 6,328 | 39,709 | 4,653 | 203 | 16 |
| 2025 | 1,483,367,843 | 267a9b5a… | 6,435,385 | 44,479 | 6,225 | 34,261 | 3,993 | 158 | 19 |
| 2026 | 774,929,298 | 9f5ef2ab… | 3,496,186 | 24,908 | 3,626 | 19,204 | 2,078 | 89 | 2 |

**16,150,349 source rows scanned, 131,520 kept.**

`federal_funding_transactions.csv`: **476,924 → 608,419 rows (+131,495)**;
25 duplicate transaction keys skipped. **639 entities newly reached.**

Rows added by FY × `assistance_type`:

```
FY2007  02 4048 · 03 1524 · 04 3987 · 05 454 · 06 1326 · 07 27 · 08 11 · 09 7 · 10 52 · 11 7
FY2024  02 3305 · 03 12645 · 04 12704 · 05 3642 · 06 17026 · 07 15 · 08 1 · 10 781 · 11 565 · F001 2
FY2025  02 3003 · 03 8201 · 04 12646 · 05 3483 · 06 15997 · 07 19 · 10 641 · 11 481
FY2026  02 1334 · 03 5230 · 04 5492 · 05 1551 · 06 10028 · 07 2 · 10 320 · 11 155 · F001 640 · F002 139 · F010 4
```

Money by FY, **three fields never pooled**:

| FY | grant obligation | credit rows | credit obligation | face value | subsidy cost |
|---|---:|---:|---:|---:|---:|
| 2007 | 2,188,541,053.60 | 45 | 1,297,392.00 | 26,064,119.00 | 2,559,719.00 |
| 2024 | 16,236,074,877.89 | 16 | 0.00 | 64,355,447.00 | 2,795,643.91 |
| 2025 | 16,674,151,861.02 | 19 | 0.00 | 211,353,464.00 | 75,039,468.26 |
| 2026 | 12,120,704,678.80 | 2 | 0.00 | 0.00 | 0.00 |
| **all** | | **82** | **1,297,392.00** | **301,773,030.00** | **80,394,831.17** |

**Face value is the borrower's principal; subsidy cost is what the guarantee
costs the government. Neither was added to grant obligations, and
`total_face_value_of_loan` is an award-cumulative snapshot that is never summed
across transactions.**

FY2007 is a **new floor year** — the pre-existing series began FY2008. It is
labelled by `source_file` and `population_basis` like every other archive row.

---

## FINDING 6 — this build edge-blocked the host, and that is on this build

At **2026-08-08T00:55Z**, after six large objects in twelve minutes with only a
15s pause between them, `files.usaspending.gov` began answering **HTTP 500 in
under a second** and then closing connections without a response. A single HEAD
probe returned `RemoteDisconnected` in **0.43s**. Sub-second failure is an
**edge block**, not a slow server.

FY2008 and FY2009 were refused and recorded with `http_status = 500` in the
manifest. **Both objects are in the listing.** A refusal is a fact about the
host, not about the object, and neither year is written off.

**The block had not cleared 48 minutes later.** A resumer armed at 00:56Z woke
at 01:42Z and its first two attempts both returned `RemoteDisconnected` in under
a second.

Mitigation now in the script: `download()` backs off exponentially 60s → 30 min
over six attempts, and the inter-object pause is **180s, not 15s**. `fetch` is
resumable — a year whose extract already exists is skipped, so nothing is
re-downloaded. `append` is idempotent: it dedupes on
`assistance_transaction_unique_key`.

### The runaway that backoff alone does not prevent

Exponential backoff bounds the *rate*; it does not bound the *run*. The first
resumer had no global stop, so left alone it would have walked **16 years × 6
attempts** against a refusing host — hours of probing, extending the block for
the contracts agent sharing this IP. `PULL_DISCIPLINE.md` says stop at ~2h and
the script did not.

It was killed **by PID** (`Win32_Process`, `CommandLine` match, `Stop-Process
-Id`; never `/IM`) and the script now carries two independent stops:

* **`RUN_DEADLINE`** — no attempt starts more than 2h after the run began.
* **stop-on-first-refusal-when-nothing-has-succeeded** — a year that exhausts
  its backoff while no year has landed means the **host** is refusing, not that
  one object is bad. Trying the remaining fifteen years is fifteen more ways to
  learn the same fact. Exits 2 on that path.

**Resume with:** `py -3 code/115_pull_assistance_archive.py fetch 2008..2023`
then `py -3 code/115_pull_assistance_archive.py append`.

If the contracts agent sharing this host saw refusals around 00:55Z, this build
is why. It is a shared IP block and it clears.

---

## Still owed

1. **FY2008–FY2023 assistance archive objects** — the credit-instrument
   backfill. FY2023 in particular: the clean file still holds only **15,141
   FY2023 rows** (the API spine ends at action_date 2023-04-05), against ~45k in
   neighbouring years. FY2023 is the largest single remaining gap and it is one
   object.
2. **Subawards FY2021–FY2024 and FY2020 contracts** — not obtainable from this
   host at all. Queued against `api.usaspending.gov`.
3. **99 withheld ledger attributions** need rulings —
   `review/assistance_archive_ledger_state_disagreement_2026-08-07.csv`.
4. **2,056 unresolved tribal-recipient-type UEIs** —
   `review/assistance_archive_unresolved_2026-08-07.csv`. These are a discovery
   pool, not an attribution.
5. `F001`/`F002`/`F010` belong in `series_breaks.csv`, which this build did not
   edit.

---

## Guardrails observed

* HTTP status **and** archive magic bytes both checked before any read.
* Members streamed (`zipfile.open` → `TextIOWrapper`); nothing loaded whole.
* Disk was 15.2 GB free against ~19.6 GB of objects, so each zip is deleted
  after extraction. URL, status, bytes and **md5** are in `_SOURCE_MANIFEST.csv`,
  and the filtered extract — full source schema, no columns dropped — is
  retained as the raw artefact.
* No process killed by image name.
* `codebook_master.csv` untouched; fragment written to
  `data/clean/codebook/03_federal_funding_archive.csv` (14 variables, pct_filled
  measured over the 608,419-row file).
* `prime_contracts.csv`, `series_breaks.csv`, the identifier ledger and the
  spine were not modified. `code/01_build_entity_spine.py` was not run.
* `code/62_no_regression_check.py` passed **before and after**: no regressions.

---

# UPDATE 2026-08-12 — the backfill, and four things the source did that the first run could not have known

*Runner: `code/115_pull_assistance_archive.py`. Run logs:
`logs/115_run_2026-08-12.out`, `_run2_`, `_run3_`.*

**Status: FY2008–FY2019 and FY2023 landed. FY2020, FY2021 and FY2022 are still
owed and the reason is LOCAL DISK, not the host and not absence.**

## What landed

`federal_funding_transactions.csv`: **608,419 → 684,923 rows (+76,504)**, with
**476,902 duplicate transaction keys skipped**. That skip count is the real
result and it is good news: it means the API-route spine already held most of
FY2008–FY2019, and the archive confirms it transaction-for-transaction rather
than replacing it. **11 entities newly reached.**

| FY | rows before | rows after | delta |
|---:|---:|---:|---:|
| 2008 | 14,157 | 15,669 | +1,512 |
| 2009 | 23,827 | 26,844 | +3,017 |
| 2010 | 23,558 | 26,919 | +3,361 |
| 2011 | 22,211 | 26,103 | +3,892 |
| 2012 | 18,141 | 22,854 | +4,713 |
| 2013 | 26,927 | 30,950 | +4,023 |
| 2014 | 29,913 | 33,513 | +3,600 |
| 2015 | 28,105 | 31,191 | +3,086 |
| 2016 | 33,701 | 37,213 | +3,512 |
| 2017 | 32,756 | 36,122 | +3,366 |
| 2018 | 39,432 | 43,789 | +4,357 |
| 2019 | 37,880 | 41,434 | +3,554 |
| **2023** | **15,141** | **49,652** | **+34,511** |

**FY2023 was the single highest-value object and it is closed.** It held 15,141
rows against ~45k in neighbouring years because the API spine stopped at
`action_date 2023-04-05`; it now sits at 49,652, between FY2022's 44,297 and
FY2024's 50,686. The gap was the API's stopping point, not a fact about FY2023.

## FINDING 5 confirmed at scale — type 09 still does not behave like 07 and 08

The first run measured this on 82 credit rows from one year. The backfill takes
it to 1,757 rows across thirteen, and it holds:

| type | rows | obligation | face value | subsidy cost |
|---|---:|---:|---:|---:|
| 07 direct loan | 1,584 | **0.00** | 3,261,973,056.75 | 123,915,048.77 |
| 08 guaranteed/insured loan | 100 | **0.00** | 1,061,657,423.00 | 74,663,937.00 |
| **09 insurance** | **73** | **26,937,458.87** | **0.00** | **0.00** |

`docs/DATA_ODDITIES.md` records that 07/08/09 all report `obligated_usd` as
exactly 0.00 by design. That is exactly right for 07 and 08 and **wrong for
09**, which carries a non-zero obligation and no face value at all. On seven
FY2007 rows that was a curiosity; on 73 rows and $26.9M spread across the
series it is a documented rule that the data contradicts. `DATA_ODDITIES.md`
is **not edited here** — this is a measurement against it, and the script
flags the rows as `credit_rows_with_NONZERO_obligation` rather than assuming
either source is right.

## FINDING 7 — the archive replaces its objects monthly, and the stamp rolled mid-build

The 2026-08-07 enumeration recorded 4,631 keys all stamped `20260706` and
concluded *"There is nothing newer to probe for."* True when written. On
2026-08-10 the August file published, and **every `20260706` object was
deleted**: a full re-enumeration on 2026-08-12 returned **4,597 keys, all
`20260806`, none `20260706`**.

So the resume command left in this log — `fetch 2008..2023` — would have
requested objects that now answer a **real HTTP 404**, and a reader trusting
"nothing newer to probe for" would have read those 404s as the archive having
dropped those years. **Re-probing for a newer stamp before settling was
load-bearing.** The `_All_` series still covers FY2007–FY2026; only the stamp
moved.

Rows keep the stamp they were written with in `source_archive_stamp`, so
FY2007/2024/2025/2026 still say `20260706` and this backfill says `20260806`.

## FINDING 8 — an interruption must not look like a completion

`fetch_year` skipped any year whose extract already existed, and wrote that
extract **straight to its final name**. So an interruption at any point left a
partial file at the path that means *this year is done*.

Measured: FY2011's download stalled, the process was stopped, and a
**126,628-byte / 256-row** extract was left beside ~20 MB / ~27,000-row
neighbours. Every later run would have skipped it, and FY2011 would have been
**0.9% complete forever** while looking like a finished year — a row count that
is a fact about an interrupted process presented as a fact about FY2011.

This is the same shape as *a block must not look like an absence*, one layer
down. The extract is now written to `.part` and renamed only after every member
has streamed to the end, which is what script 114 already did. FY2011 was
re-fetched and holds 26,103 rows.

## FINDING 9 — a stalled stream is a third failure shape

`download()` knew two shapes: refusal and slow server. A third exists.
`requests`' `timeout=1800` is the **gap between chunks**, not a total, so a
connection the host quietly stopped feeding sat for 30 minutes per attempt, six
attempts deep — burning the entire 2h `RUN_DEADLINE` without making a single
useful request. FY2011 died at **exactly 20,971,520 bytes** (20 MB, a round
number, which is a server-side cutoff rather than a network drop).

Fixed two ways: the read timeout is now `(30, 120)` — a two-minute silence from
a CDN that was delivering 40 MB/s is a dead socket — and the received byte count
is checked against `Content-Length`, because **a truncated zip still starts with
`PK` and passes the magic-byte test**. A short read now raises onto the retry
path instead of being blamed on the object.

## FINDING 10 — the per-agency cut is the same universe, and it is verified, not assumed

FY2020's `_All_` object is **3.15 GB** against **~2.5 GB free**. That is a
constraint of this machine, not of the source, and recording it as "FY2020
could not be obtained" would be the absence/refusal confusion in a third form.

The archive publishes every year twice: once whole, and once as ~112 per-agency
objects. FY2020 cut by agency is 3.06 GB whose **largest** member is 1.99 GB, so
peak disk is one object instead of a year.

**That the union is the same universe was an assumption, so it was tested.**
Two FY2008 per-agency objects were pulled and filtered with the same rule, then
checked against the FY2008 `_All_` extract already on disk:

```
agency 091 (Education): scanned 1,065,431, kept 3,693
kept rows absent from the _All_ extract:                 0
rows in _All_ for those agencies missing from the parts: 0
VERDICT: exact match in both directions
```

The route is sound. **It is the request COUNT that defeats it here**: 112
objects per year against a host that edge-blocked this build after six objects
in two minutes. At the pacing this host demonstrably tolerates (~3 min between
objects) one year costs ~5.5 hours, so it was not run today.

## Still owed, with the reason stated precisely

| FY | why | route when resumed |
|---|---|---|
| **2020** | `_All_` is 3.15 GB vs ~2.5 GB free — **local disk**. Per-agency fits (largest 1.99 GB) but needs 112 paced requests. | free ~4.5 GB then `fetch 2020`, or run the per-agency fallback over a long window |
| **2021** | `_All_` is 2.80 GB — **local disk**. Per-agency largest is 1.19 GB and fits today. | same |
| **2022** | `_All_` is 1.57 GB. Free space fell to **1.68 GB** during the session as other agents wrote, so it no longer fits either; a per-agency attempt at 20:08Z reached object 17 of 112 before the host edge-blocked. **Local disk, then host rate.** | free ~2.5 GB then `fetch 2022` - one request |

**None of the three is absent.** All 112×3 per-agency objects and all three
`_All_` objects were enumerated in the 2026-08-12 listing
(`data/raw/contracts/archive_listing_2026-08-12.csv`). FY2020–FY2022 already
hold API-spine rows (43,274 / 43,604 / 44,297), so the series is not empty
there — the archive would add the credit instruments and the ledger-only leg,
as it did for FY2008–FY2019.

**Who caused the 19:00Z block: this build.** The per-agency fallback issued six
objects in roughly two minutes with an 8s pause, and the host began answering
HTTP 500 and then closing connections in under half a second. The 8s pace was
too aggressive for this host and is recorded here so the next agent does not
rediscover it. It cleared in about an hour last time.

## Guardrails observed

* One poller per host, claimed in `logs/_HOSTLOCK_files.usaspending.gov.json`;
  the prime and assistance runners were never run concurrently.
* Processes stopped by **PID** via `Win32_Process` `CommandLine` match. Never
  `/IM`.
* Zips released immediately after their rows are consumed; url, status, bytes
  and md5 retained in `_SOURCE_MANIFEST.csv`.
* `codebook_master.csv` untouched — fragment only
  (`data/clean/codebook/03_federal_funding_archive.csv`, 14 variables over
  684,923 rows).
* `series_breaks.csv`, the identifier ledger and the spine not modified.
* `code/62_no_regression_check.py` passed **before and after**: no regressions.

---

# UPDATE 2026-08-26 — credit types 07/08/09: the gap is now THREE YEARS, not sixteen

*Runner: `code/46_pull_funding_credit_types.py`. Run log: `logs/46_run_2026-08-26.out`.
Raw: `data/raw/federal_funding/usaspending_credit_2026-08-06/`.*

## The host recovered

`GET /api/v2/references/agency/456/` → **HTTP 200 in 0.46s**. The 2026-08-07T18:01Z
HTTP 503 wall and the 2026-08-12T16:35Z sub-second `RemoteDisconnected` have both
cleared. One probe request bought that answer.

## Script 46 was written before this backfill existed, and the backfill beat it

`46_pull_funding_credit_types.py` was written 2026-08-06 to pull credit types
07/08/09 for **FY2007–FY2023**, because the then-current spine held none of them.
The archive backfill of 2026-08-07/08 and 2026-08-12 has since landed **1,757
credit rows** in `federal_funding_transactions.csv` (07: 1,584 · 08: 100 · 09: 73).

Four count probes settled whether script 46 still had anything to add. **The
archive route is a STRICT SUPERSET on every year it covered**, because the archive
keeps rows under a UNION (`recipient_type` OR `ledger_uei`) while script 46 filters
on `recipient_type_names` alone:

| FY | script 46's route (API) | clean file (archive) | delta |
|---:|---:|---:|---:|
| 2011 | 761 | 816 | **-55** |
| 2018 | 19 | 21 | **-2** |
| 2023 | 2 | 15 | **-13** |
| 2020 | 7 | **0** | **+7** |
| 2021 | 9 | **0** | **+9** |
| 2022 | 34 | **0** | **+34** |

Re-pulling FY2007–2019 and FY2023 would have issued **sixteen** server-side jobs to
obtain **fewer** rows than are already on disk. **Only FY2020, FY2021 and FY2022
hold zero credit rows** — precisely the three archive objects listed as "Still
owed" above, and owed for **local disk**, not for the host.

`--years` was added to the script with this table in the comment, so the next agent
cannot re-derive it. Restricting is the same discipline as *a 404 is a fact about
the object*: spend requests where the gap is **measured**, not where it is assumed.

## What was pulled

Three chunks. GATE 1 and GATE 2 both PASSED against the live host first:

```
GATE 1  fy2022 API 44,312 vs spine 44,297  delta +0.03%   PASS
        fy2021 API 43,769 vs spine 43,604  delta +0.38%   PASS
GATE 2  fy2022 credit filtered     34 vs unfiltered  2,345,558  PASS
        fy2021 credit filtered      9 vs unfiltered 10,525,767  PASS
```

| FY | type | rows | obligation | face value | subsidy cost |
|---:|---|---:|---:|---:|---:|
| 2020 | 07 | 7 | 0.00 | 4,615,963.00 | 227,275.76 |
| 2021 | 07 | 8 | 0.00 | 235,150,300.53 | 11,686,955.00 |
| 2021 | **09** | 1 | **44,475.57** | 0.00 | 0.00 |
| 2022 | 07 | 34 | 0.00 | 1,328.48 | 0.00 |

**50 rows, and every one of the retrieved row counts equalled its pre-submission
count probe exactly** (7 / 9 / 34) — the filter did what the gate said it would.
`business_types_code` is `{I: 12, K: 38}`, entirely inside {I,J,K}: the population
was reproduced, not approximated.

## FINDING 5 confirmed a THIRD time, on a year that had never been measured

The one type-09 row is **STANDING ROCK SIOUX TRIBE, 2021-09-14, obligation
$44,475.57, face value 0.00**. `docs/DATA_ODDITIES.md` records that 07/08/09 all
report `obligated_usd` as exactly 0.00 by design. That is right for 07 and 08 and
**wrong for 09**, now measured on 7 FY2007 rows, then 73 rows across thirteen
years, and now again on an independent FY2021 row retrieved by a different route
and a different endpoint. `DATA_ODDITIES.md` is still not edited — this is a third
measurement against it, not a correction of it.

## What this did NOT do

**Script 46 has no `append` stage and none was invented.** Its `build` is offline
reporting only. So `federal_funding_transactions.csv` **still holds zero credit
rows for FY2020–FY2022**; the 50 rows exist as raw evidence plus `_summary.json`
and `review/funding_credit_new_ueis_2026-08-06.csv`.

**The right way to close it is the archive, not this route**, and it is now
unblocked: free disk is **42 GB**, against the ~2.5 GB that stopped FY2020–2022 on
2026-08-12. One request per year, and it brings the ledger-only leg with it:

```
py -3 code/115_pull_assistance_archive.py fetch 2020 2021 2022
py -3 code/115_pull_assistance_archive.py append
```

Pace them ~3 minutes apart. FY2020 `_All_` is 3.15 GB, FY2021 2.80 GB, FY2022
1.57 GB — all three now fit, and `append` dedupes on
`assistance_transaction_unique_key`, so the 50 rows above cannot double-count.

---

# UPDATE 2026-08-26, later — FY2020/21/22 CLOSED. The credit gap is now ZERO years.

*Runner: `code/115_pull_assistance_archive.py fetch 2020 2021 2022` then `append`.
Logs: `logs/115_fetch_2026-08-26.out`, `logs/115_append_2026-08-26.out`.
Measurement: `code/171_credit_gap_measure.py` (`logs/171_baseline_2026-08-26.out`
before, `logs/171_after_2026-08-26.out` after). Stamp probe:
`code/172_probe_archive_stamp_per_year.py` (`logs/172_stamp_probe_2026-08-26.out`).*

**The blocker was never the host and never the source. It was 2.5 GB of free
disk.** Free space today is 41 GB, so all three `_All_` objects took the
one-request-per-year route and the 112-object per-agency fallback was never
triggered.

## The stamp was probed PER YEAR, and the probe form was changed

A `HEAD` on a URL built from the hardcoded stamp answers only *is my guess still
alive*, and its 404 reads as a fact about the fiscal year. A prefixed listing
answers the better question for the same one request:

```
GET /award_data_archive/?prefix=FY2020_All_Assistance_Full_
FY2020: HTTP 200 in 0.47s  stamp=20260806  3.15 GB
FY2021: HTTP 200 in 0.46s  stamp=20260806  2.80 GB
FY2022: HTTP 200 in 0.46s  stamp=20260806  1.57 GB
```

Three requests, 15s apart. All three carry `20260806`, matching the constant in
the script; nothing was assumed.

## No block was caused, and the peer was never interrupted

`code/121_pull_subawards_api.py pull --sequential` (pid 13736) was live on
`api.usaspending.gov` throughout, mid-`fy2021`. **That is coexistence by design,
not contention**, and the design is 121's own: it lists
`115_pull_assistance_archive` in `FILES_HOST_SCRIPTS` and **not** in
`API_HOST_SCRIPTS`, so this run is not a rule-1 peer to it, and its
`wait_for_files_host()` defers its *download* leg while this process is live —
deferring is free, because the token is already checkpointed and rule 5 is not
touched. Its first files-host download was ~3h away when this run started and
this run took 25 minutes.

**Zero requests were issued to `api.usaspending.gov` by this agent.**
`PULL_DISCIPLINE.md` — *where a peer is already polling, its LOG is the cheapest
probe available* — so the host-health reading was taken from 121's own log line
at 21:19:09Z (`GET /api/v2/references/agency/456/` → HTTP 200 in 0.46s) instead
of adding a second prober.

**Three objects at 180s spacing produced zero refusals on this side.** That is
inside the tolerance AGENTS.md records (ten 1.4 GB objects at 2.5 min apart
succeeded); the 2026-08-08 block came from six objects at 15s. Downloads ran at
~45 MB/s.

**The peer took ONE transport failure and it is reported rather than glossed.**
At 22:12:12Z 121's `status fy2021` poll failed `WinError 10060` **in 21.07
seconds**, backed off 60s, and resumed cleanly at 22:13:12Z with the job still
running and nothing lost. Two reasons it is not this run's edge block, and both
of them are the discipline's own tests rather than a convenient reading:

* **Shape.** `PULL_DISCIPLINE.md` classifies a sub-second `RemoteDisconnected`
  as an edge block and a 30s-plus timeout as a slow server. **21 seconds is the
  slow-server shape, not the refusal shape.** The whole point of that table is
  that the two call for opposite responses.
* **Timing.** This run's last network request finished at **22:05:29Z**, seven
  minutes earlier; `append` is pure local CPU and disk and issues nothing.

Recorded anyway, because `PULL_DISCIPLINE.md` says who caused a block goes in
the log, and a run that reports only the failures it can disown is not
reporting.

| FY | object | md5 | scanned | kept | credit |
|---|---:|---|---:|---:|---:|
| 2020 | 3,149.3 MB | 3f154098373a0192c645171c80fa757f | 25,183,037 | 49,192 | 7 |
| 2021 | 2,804.0 MB | c372c09eea1413574e272a302f6e8556 | 20,637,031 | 48,410 | 10 |
| 2022 | 1,570.1 MB | 70c5a8bc98133ff9286d1925d6683b3a | 8,811,030 | 50,450 | 43 |

`federal_funding_transactions.csv`: **684,923 → 701,955 rows (+17,032)**, with
**684,426 duplicate transaction keys skipped**. Backed up first to
`.bak_2026-08-26_pre115_credit`, because the 684,923 figure is asserted in
several documents. **1 entity newly reached.** `62_no_regression_check.py`: **no
regressions.**

## The credit gap, before and after

| FY | credit rows before | after | by type |
|---:|---:|---:|---|
| 2020 | **0** | **7** | 07 ×7 |
| 2021 | **0** | **10** | 07 ×8 · 08 ×1 · 09 ×1 |
| 2022 | **0** | **43** | 07 ×42 · 08 ×1 |
| **all years** | 1,757 | **1,817** | 07 1,641 · 08 102 · 09 74 |

Money, **three fields, never pooled**:

| FY | credit rows | obligation | face value | subsidy cost |
|---:|---:|---:|---:|---:|
| 2020 | 7 | 0.00 | 4,615,963.00 | 227,275.76 |
| 2021 | 10 | **44,475.57** | 235,150,300.53 | 11,686,955.00 |
| 2022 | 43 | 0.00 | 9,041,337.48 | 541,989.91 |

## CROSS-SOURCE VERIFICATION — the two routes agree EXACTLY on the shared population

The 2026-08-26 script-46 probe found 7 / 9 / 34 rows by the narrower
`recipient_type_names` route. Splitting the archive's rows by
`population_basis` shows why the archive's totals are larger and proves the
agreement is exact rather than approximate:

| FY | recipient-type leg (`recipient_type` + `both`) | script 46 | ledger-only leg |
|---:|---:|---:|---:|
| 2020 | 6 + 1 = **7** | **7** | 0 |
| 2021 | 8 + 1 = **9** | **9** | 1 (`ledger_uei_withheld`) |
| 2022 | 33 + 1 = **34** | **34** | 9 (5 `ledger_uei`, 4 withheld) |

`docs/CROSS_SOURCE_VERIFICATION.md`: one federal source is a claim, two that
agree is a verification. **Two independent routes, two different endpoints, and
the shared population matches transaction-for-transaction on all three years.**
The extra 10 rows are the additive Cedar Press ledger leg — 5 attributed, 5
refused by the state-agreement guard and sitting in
`review/assistance_archive_ledger_state_disagreement_2026-08-26.csv` with a
`YOUR_RULING` column. **The seam is a column, never a silent adjustment.**

## FINDING 5 CONFIRMED A FOURTH TIME — and by a fourth route

`docs/DATA_ODDITIES.md` rules that credit types 07/08/09 all report
`obligated_usd` as exactly 0.00 by design. Measured on the enlarged file:

| type | rows | obligation | face value | subsidy cost |
|---|---:|---:|---:|---:|
| 07 direct loan | 1,641 | **0.00** | 3,510,680,657.76 | 136,371,269.44 |
| 08 guaranteed/insured loan | 102 | **0.00** | 1,061,757,423.00 | 74,663,937.00 |
| **09 insurance** | **74** | **26,981,934.44** | **0.00** | **0.00** |

The rule is exactly right for 07 and 08 and **wrong for 09**. The type-09
obligation total moved by **exactly $44,475.57**, which is the single row script
46 retrieved by the API on 2026-08-26:

```
FY2021  type 09  2021-09-14  obl 44,475.57  face 0.00
STANDING ROCK SIOUX TRIBE  TRBF-STNDRK-00  population_basis=both
source_file=FY2021_All_Assistance_Full_20260806.zip
```

It arrived here from the **static archive**, independently of the API route that
first found it, and `population_basis = both` means USAspending independently
codes the recipient as a tribal government. Measured now on 7 FY2007 rows, 73
rows across thirteen years, one FY2021 API row, and this archive row.
**`DATA_ODDITIES.md` is still not edited** — this is a fourth measurement
against it, not a correction of it.

## Coverage refreshed

`py -3 code/35_coverage_audit.py` (writes `data/clean/coverage_audit.csv`, 716
rows, and `docs/COVERAGE_AUDIT.md`; **script 102 writes the gaming property/field
profiles and is a different tool** — the two were confused in earlier notes).

`federal_funding` now reads **2006–2026, 701,955 rows**, `action_date`, **no
interior gaps**. Per calendar year of `action_date` — note this is NOT fiscal
year: 2020 **46,112** · 2021 **49,660** · 2022 **52,321** · 2023 48,481 ·
2024 49,871 · 2025 43,254 · 2026 18,325.

## Still owed — unchanged by this run

1. **Subawards FY2021–FY2024 and the FY2020 contracts member.** Not obtainable
   from this host at all (FINDING 1). In flight against `api.usaspending.gov`
   under `code/121_pull_subawards_api.py` as of 2026-08-26T21:19Z.
2. **The withheld ledger attributions** —
   `review/assistance_archive_ledger_state_disagreement_2026-08-26.csv`
   (64 recipients, $2,264.4M held out of Native totals). This is a **ledger**
   defect, not an artefact of this pull.
3. **`F001`/`F002`/`F010` still belong in `series_breaks.csv`**, which this run
   did not edit.
