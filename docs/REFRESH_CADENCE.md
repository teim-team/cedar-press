# Refresh Cadence — measured, not cited

*Rewritten 2026-08-26 by `code/301_source_freshness_probe.py`. The 2026-08-06
version is preserved at `docs/REFRESH_CADENCE.md.bak_2026-08-26_pre301`; it was
written from publication schedules rather than from the files, and **four of its
recommendations are wrong against measurement**. Those four are named in
"WHAT THIS CORRECTS" at the bottom.*

**Every number in this document was produced by one re-runnable script.**
Re-run it and the numbers update:

```
py -3 code/301_source_freshness_probe.py            # zero network requests
py -3 code/301_source_freshness_probe.py --probe-net # + 3 bounded probes
```

Outputs `docs/SOURCE_FRESHNESS.json` (full measurement) and
`docs/SOURCE_FRESHNESS_SNAPSHOT.json` (compact state for the next diff). The
diff is the point: **the oldest period whose row count moved between two runs is
the empirical answer to "how far back does a refresh actually reach?"** — and
that number is what sets the trailing re-pull window. It gets sharper every run.

---

## THE SPINE OF THIS DOCUMENT: TWO JOBS, TWO CLOCKS

The owner's instinct — *"every quarter we can check for new entities … but
there's probably data that's more recurring"* — is right, and it splits cleanly.

| | **REFRESH** | **DISCOVERY** |
|---|---|---|
| question | new rows for entities we already know | entities we do **not** know |
| route | identifier-seeded (UEI / CAGE / EIN / tribe_id) | broad filter or full sweep |
| cost | small — a filtered read of a period window | large — a full-corpus scan |
| clock | **the LAG PROFILE below** — how long a period keeps growing | **the drift rate** — how fast the identifier list goes stale |
| owner | this document | `docs/DISCOVERY_GAP.json` · `code/276_measure_discovery_gap.py` |

They are different jobs because they fail differently. A refresh that runs too
slowly gives you *stale* numbers, which every reader can see. A discovery pass
that runs too slowly gives you *confidently wrong* numbers, which no reader can
see, because a missing entity leaves no hole in the table.

**The discovery clock, measured by script 276 (do not re-derive it here):**

| FY | rows a UEI-only pull would lose | |
|---|---:|---|
| FY2015 | 0.23% | the identifier list was near-complete |
| FY2019 | 6.24% | |
| FY2022 | 6.77% | |
| FY2023 | 7.49% | |
| FY2024 | 8.74% | |
| **FY2025** | **12.66%** | **+3.9 pp in one year** |

and, on the flag route, **9,719 entities carry a Native business-type flag in
FPDS prime data that the identifier route has never seen — 76.9% of all flagged
entities, $70.96B of obligations.**

Read those two together: coverage of the *known* population is fine and the
*known population itself* is drifting. The drift accelerated from ~1 pp/yr
(FY2019–23) to 3.9 pp in FY2025. **Quarterly discovery is the right instinct and
is, if anything, slightly conservative for contracting; annual is now too slow.**

⚠ A self-certification is not a determination. Everything discovery surfaces is
a **candidate for adjudication**, never a row to attribute. Goldbelt Raven, an
ANC subsidiary, certifies `alaskanNativeCorporationOwnedFirm = NO`.

---

# PART 1 — THE MEASURED LAG PROFILE

## 1.1 Where every collection actually stops, today

`EXACT_LAST_DATE` is the true maximum date in the file, not the month bucket. A
month bucket rounds a source that stops on the 3rd up to the 31st and hides four
weeks of lag — measured: prime `action_date` stops **2026-07-03**, which the
bucket `2026-07` reports as 12 days of lag when it is 40.

| collection | last data | our as-of | gap | **whose lag is it?** |
|---|---|---|---:|---|
| FERC docket filings | 2026-08-26 | 2026-08-26 | 0d | current |
| deals | 2026-08-20 | 2026-08-26 | 6d | current |
| subawards | 2026-08-03 | 2026-08-26 | 23d | source |
| FAC single audits | 2026-08-12 | 2026-08-13 | 1d | current |
| Federal Register | ~~2026-08-05~~ **2026-08-26** | 2026-08-26 | **0d** | ✅ **CLOSED 2026-08-26 — see PART 5** |
| NAGPRA notices | ~~2026-08-03~~ **2026-08-24** | 2026-08-26 | **2d** | ✅ **CLOSED 2026-08-26 — 2d is the source's own event gap** |
| lobbying (LDA) | 2026-08-04 | 2026-08-06 | 2d | **OURS — 20 days stale** |
| IBIA / IBLA appeals | 2026-07-28 | 2026-08-26 | 29d | source |
| prime contracts | **2026-07-03** | 2026-08-12 | **40d** | source (archive cut) |
| assistance | **2026-06-30** | 2026-08-26 | **57d** | source (archive cut) |
| CA gaming | 2026-06-30 | 2026-08-07 | 38d | source |
| resource revenue | 2026-06-30 | 2026-08-13 | 44d | source |
| 990 Schedule I | 2025-12-31 | 2026-08-26 | **238d** | source (structural) |
| gaming facility metrics (CT monthly) | 2025-12-31 | 2026-08-26 | **238d** | ⚠ **RE-DIAGNOSED 2026-08-26: the SOURCE's, not ours — see PART 5** |
| FAADS | 2007-09-30 | — | 6,884d | **CLOSED BY DESIGN** |
| FL gaming | 2031-06-30 | — | — | ⚠ see 1.6 |

**The single most useful column here is the last one.** Three collections that
look "behind" are behind because *we have not pulled*, not because the source
has not published. **Two of those three were closed on 2026-08-26 (PART 5) and
lobbying is the one that remains.** Verified live at the run that first measured
this:

> `www.federalregister.gov` → HTTP 200, newest `publication_date` = **2026-08-26**.
> Cedar's newest is 2026-08-05. **The source is same-day current and we are 21
> days behind it.**

Do not diagnose a source from a stale local file. That is the cheapest error in
this whole document to make and it points every remedy in the wrong direction.

## 1.2 How long a period keeps filling in

Method: take the median row count over a **mature window** (periods old enough
that nothing should still be arriving), then walk backwards from the newest
period counting how many sit below 90% of it. For sources whose periods are not
uniform — 990 `tax_period_end` piles onto months 12 and 06, LD-2 posting onto
Jan/Apr/Jul/Oct, CA gaming onto quarter ends — the flat plateau is compared
against the **same calendar month** in the mature window instead. Both are
reported; **the seasonal one is the correct one wherever the two disagree.**

| collection | flat | **seasonal** | reading |
|---|---:|---:|---|
| prime contracts (monthly) | 3 | **3** | 2026-05 at 44%, 2026-06 at 54%, 2026-07 at 5% — the last is the archive cut |
| assistance | 2 | **2** | 2026-05 at 66%, 2026-06 at 60% |
| **990 Schedule I** | 6 | **1** | flat is an artifact; only 2025-12 is short — **at 12% of a December plateau** |
| FAC single audits | 2 | **2** | |
| CA gaming | 5 | **5** | five quarters short, and **2026-03 is missing outright** |
| resource revenue | 0 | **1** | |
| Federal Register · NAGPRA · FERC · lobbying | 1 | **1** | the current month only, i.e. our staleness |
| IBIA/IBLA · deals · gaming metrics · FAADS | 0 | **0** | no detectable fill |
| subawards | 1 | 1 | ⚠ **untrustworthy — see 1.5** |

**The headline: the two federal spending series stop filling in about two months
after a month closes, and they stop hard.** Prime: 2026-05 at 44% and 2026-06 at
54% of plateau, while every month before 2026-05 is at or above it. Assistance:
identical shape, two months. That is the number that sets their cadence, and it
is not the vendor's schedule.

## 1.3 The USAspending award archive — measured to the second

All 4,597 objects, **93.9 GB**, from the on-disk listing:

| | |
|---|---|
| stamp on every key | **`20260806`** |
| S3 `last_modified`, earliest | **2026-08-10T00:14:25Z** |
| S3 `last_modified`, latest | **2026-08-10T00:18:05Z** |
| distinct write timestamps | 206, all inside **3 minutes 40 seconds** |
| previous stamp | `20260706`, dead everywhere by 2026-08-12 |

Four things follow, and all four are operational:

1. **The whole archive is rewritten atomically, once a month, in under four
   minutes, at ~00:14 UTC.** FY2007 is rewritten as surely as FY2026.
2. **The stamp is the 6th; publication is the 10th.** A ~4-day production lag
   between as-of date and availability, consistent across the two stamps we
   hold. **Never probe for a new stamp before the 10th of the month.**
3. **Object metadata carries no signal about which years changed** — every
   object's `last_modified` moves every month whether its contents did or not.
   You cannot decide what to re-download from the listing. You must diff
   contents, which is what script 301's snapshot diff is for.
4. Probe the stamp **per-year at run start, never globally.** FY2007–2016 in
   Cedar came down under `20260806` and FY2017–2026 under `20260706`; a single
   global stamp variable would have mislabelled half the corpus.

> ⚠ **A TRAP, ENCODED IN THE SCRIPT SO NOBODY REPEATS IT.**
> `data/raw/contracts/usaspending_archive_2026-08-07/_SOURCE_MANIFEST.csv` is
> **generated from** `_state.json`. Their `rows_scanned` columns are identical by
> construction. Differencing them produces a clean "0.000% change across every
> fiscal year" table that looks exactly like a month-over-month archive
> comparison and **is not one.** It measures nothing.
> **Cedar holds no genuine cross-vintage measurement today.** Getting one is
> cheap and worth doing: re-filter one already-held fiscal year under the next
> stamp and diff the row counts. Until then, section 1.2's within-vintage fill
> curve is the best evidence available, and it should be labelled as such.

### 1.3a Whether a cross-vintage measurement can be had from disk — ANSWERED, and it cannot

*Measured 2026-08-26 by the harmonisation pass (`code/334`–`337`). The
conclusion above stands; what is new is that the REASON is now measured rather
than assumed, and the exact cost of obtaining one is stated.*

Two routes exist in principle. **Both are closed, and each for its own
structural reason.**

**Route 1 — diff the same fiscal year across the two archive stamps. CLOSED:
no fiscal year is held under both.** The stamps partition the years rather than
overlapping them:

| stamp | fiscal years held | rows |
|---|---|---:|
| `20260706` | FY2007, FY2024, FY2025, FY2026 | 131,495 |
| `20260806` | FY2008 … FY2023 | 93,536 |

There is no intersection, so there is nothing to difference.
`data/raw/contracts/usaspending_archive_2026-08-07/_state.json` carries a
single global `stamp = 20260706`, which is also why the per-year stamp had to
be recovered from the clean table rather than the manifest.

**Route 2 — diff the 2023 bulk extract against the 2026 archive on their
overlapping years. CLOSED: the two strata are DISJOINT ON TRANSACTION KEY.**
They do cover the same span (FY2008–2023), which makes the route look
available. Measured on `assistance_transaction_unique_key`:

```
stratum A (2023-04-09 bulk download)   476,924 keys
stratum B (archive stamp 20260806)      93,536 keys
keys present in BOTH                          0
```

Zero. `24_funding_merge.py` deduplicated on that key, so the archive
contributed only transactions the 2023 extract did not already have. **The
merge that made the table correct is the same merge that destroyed its ability
to measure retroactive correction.** That is worth stating plainly, because it
is not a defect — a deduplicated table is the right table to ship — but it does
mean the measurement has to be taken from the RAW extracts, before the merge,
or not at all.

**What would actually be needed, and what it costs.** One fiscal year already
held, re-pulled under the NEXT stamp, kept as a separate raw extract, and
diffed against the copy we hold — row counts first, then field values on the
shared transaction keys. **FY2023 is the cheapest candidate**: 34,511 rows, one
object, already held under `20260806`, and it is the only year served by both
eras so it exercises the merge logic too. The next stamp is `20260906`,
published **2026-09-10**; do not probe before the 11th.

⚠ **It is not attemptable today.** `code/121_pull_subawards_api.py pull
--sequential` holds `api.usaspending.gov` (PID 13736, confirmed live at 20:10Z
via `Win32_Process`), and `files.usaspending.gov` shares its rate-limit budget.
One poller per host, always.

> **The finding this earns: a table can be correct and unmeasurable at the same
> time.** Deduplication, backfill-merge and "replace the trailing window" all
> improve the shipped product and all destroy the evidence a freshness
> measurement needs. If a cross-vintage number is wanted, **the raw extract of
> at least one year must be retained unmerged, on purpose, before the merge
> runs.** Nothing in the pipeline does that today.

## 1.4 Submission lag, measured from the source's own two dates

The strongest evidence in this document, because it does not depend on our pull
history at all — only on two dates the source itself stamped.

**Federal Audit Clearinghouse — `fy_end_date` → `fac_accepted_date`, n = 6,780**

| | days |
|---|---:|
| p10 | 179 |
| **median** | **271** |
| p75 | 336 |
| **p90** | **569** |
| p99 | 1,370 |
| max | 3,464 |

2 CFR 200.512(a) requires submission within **9 months (274 days)** of the audit
period end. The median is **271 days** — the deadline describes the median
auditee almost exactly. **And 30.93% of tribal single audits land after it**,
with a p90 of 569 days and a tail past nine years.

> **A deadline that the median hits and a third of filers miss is not a
> cadence.** Planning FAC around 274 days captures half the population. A FAC
> refresh must re-read a **two-year trailing window**, every time.

**IRS 990 Schedule I — `tax_period_end` → our retrieval, n = 58,355**

p10 = **584 days**. That is an upper bound (it contains our own delay), but the
*tightest* bound available, and it is already 19 months. The structural ~18-month
990 lag is confirmed from the files, not assumed. Corroborated by the fill curve:
calendar-2025 fiscal-year-ends sit at **12% of a December plateau** and 2026 is
**zero rows**.

## 1.5 Two places the naive measurement lies, and the guards that catch them

Both are now detectors in script 301, not footnotes.

**(a) A single entity can move a monthly row count by 9x.**
Prime `2026-03` shows 37,323 rows against ~4,500 in the neighbouring months — a
ratio of 9.74 to plateau, which reads as a colossal reporting surge. It is one
vendor: **`ASRC FEDERAL FACILITIES LOGISTICS, LLC` (UEI `MA1VZ6667CB1`)
contributed 33,502 of them, 89.8% of the month**, matched on
`recipient_parent_uei`. It holds 62.6% of 2026-04 as well.

At fiscal-year granularity the same entity is **66% of all 61,813 FY2026 prime
rows** (`ANRC-ARCSLO-00`). **An FY2026 that is two-thirds one ANC is not a normal
year**, and any FY2026-vs-FY2025 comparison must say so.
`SINGLE_ENTITY_DOMINATED_PERIODS` now flags every period where one entity holds
≥25% of rows. **Row counts are not a robust series; `distinct_entities_by_period`
is, and it is now emitted alongside.**

**(b) The mature window can land inside a known hole.**
Subawards' mature window (2021-08 → 2024-08) is *exactly* the FY2021–24 upstream
gap — 152 / 80 / 155 rows in calendar 2021/22/23 against an all-period median of
249. Every ratio computed from it was 30–70x and meaningless.
`PLATEAU_WARNING` now fires whenever the plateau falls below 25% of the
all-period median. **No subaward cadence can be measured until the hole is
filled**, and `code/121_pull_subawards_api.py pull --sequential` is running right
now (PID 13736, submitted 21:19Z, collect deadline 2026-08-27T05:19Z) trying to
fill it.

## 1.6 Data oddities this measurement surfaced

- **`fl_gaming.period_end` runs to 2031-06-30** with a steady 22–24 rows/month
  through 2031. These are forward-dated compact *schedule* rows, not
  observations. `period_end` is the wrong freshness column for that collection
  and any "last data" claim built on it is wrong by five years.
- **CA gaming is missing 2026-03 entirely**, and 2025-03 (112) / 2025-12 (110)
  are ~25% of a ~450-row quarter. The CCGC series has real holes at the edge; it
  is not merely lagging.
- **`gaming_facility_metrics` is two series wearing one name.** Its monthly
  component is *only* Connecticut: `CT Dept of Consumer Protection /
  data.ct.gov`, **3,240 rows, 747 facility-months, 1993-01 → 2025-12**, Foxwoods
  396 + Mohegan Sun 351, **with zero missing months in either**. Everything else
  in the file is annual or irregular. Cadence must be set per series, not per
  file.
  > *Doc correction:* the standing figure is **748** casino-months; the file
  > holds **747**. Off by one, harmless to any conclusion, recorded so nobody
  > re-derives it.
- **`federal_funding_transactions.csv` holds 701,955 rows, not 684,923.**
  `START_HERE.md` and the dataset table still say 684,923. The table was
  refreshed today (`fetched_date` max = 2026-08-26) and **carries two archive
  vintages simultaneously — `20260706` on 131,495 rows and `20260806` on
  93,536.** That is fine as provenance and fatal as a `vintage` string; see
  Part 4.

---

# PART 2 — THE DOCUMENTED SCHEDULE, PER SOURCE

Each row: what the source says, then what we measured. Verified rows are marked.

| source | stated schedule | measured | verdict |
|---|---|---|---|
| **USAspending award archive** | monthly replacement | stamp = 6th, published 10th 00:14Z, whole 93.9 GB in 3m40s | ✅ **confirmed, and tightened to the minute** |
| **USAspending transaction load** | agencies submit ≥ twice monthly (DATA Act) | assistance fills for ~2 months past a month's close | ✅ consistent |
| **FPDS-NG** | agencies report within 3 business days of award | prime fills for ~2 months past a month's close | ⚠ the 3-day rule is about *entry*; corrections run months longer |
| **FPDS-NG ATOM feed** | — | `sam.gov/contracting`: *"will be retired later in FY 2026"* | ⛔ **an expiry date, not a standing option** |
| **LDA (LD-2)** | quarterly, **due 20 days after quarter close** — 20 Jan / Apr / Jul / Oct | median **exactly 20 days**; only **57.4%** filed by day 20 | ⚠ **half-true — see 2.1** |
| **LDA (LD-203)** | semiannual, due 30 Jan / 30 Jul | visible as Feb (2,147) and Aug (2,435) posting bumps with no May/Nov twin | ✅ **inferred from the seasonal profile** |
| **LDA pre-2008 (HLOGA break)** | LD-2 was **semiannual** before 2008 | 2006–07: `mid_year` + `year_end` only. 2008: four quarters. | ✅ **the break is in the data, at exactly 2008** |
| **FSRS subawards** | prime files by end of the month following the award month | not measurable — the mature window is inside the FY2021–24 hole | ⚠ **unmeasurable today** |
| **Federal Audit Clearinghouse** | 2 CFR 200.512(a): earlier of +30d after auditor's report or **9 months** after period end | median 271d, **p90 569d, 30.9% late** | ⚠ **the deadline is not the cadence** |
| **Federal Register** | every federal business day; public inspection the day before | newest `publication_date` = 2026-08-26 (probed live, HTTP 200) | ✅ **confirmed same-day** |
| **IRS 990 e-file index** | annual `index_YYYY.csv`, submission years **2017–2026**; `index_2016` and earlier → 302 → /404 | 5,576,866 index rows streamed (concurrent agent) | ✅ e-filing begins 2017 (Taxpayer First Act) |
| **IRS 990 returns** | released in batches as processed | p10 = **584 days** from fiscal-year end | ✅ **~18-month structural lag confirmed** |
| **IRS BMF** | monthly exempt-organisation extract | 1,957,340 rows held | not re-probed this run |
| **FERC eLibrary** | indexed ~1 business day after acceptance | last filed date = **2026-08-26**, i.e. today | ✅ **confirmed** |
| **IBIA / IBLA** | posted to Interior year indices as issued | last decision 2026-07-28, 29d back | ✅ event-driven, ~1 month |
| **NAGPRA notices** | Federal Register documents | same daily cadence, event-driven arrival | ✅ |
| **regulations.gov** | continuous; comment periods are the events | not yet built — `code/221`, staged in `review/` | ⚠ **sweep docket-first, never entity-first** |
| **CourtListener / RECAP** | continuous | 200 anon, **429s under load**; get a free Free Law Project token | not swept |
| **SEC EDGAR full-text** | continuous | reachable, not swept | not swept |
| **NIGC gaming revenue report** | **annual**, for the prior FY | our gaming series ends 2025-12 | annual |
| **CT DCP** | **monthly per casino** | **747 facility-months, zero gaps, 1993-01 → 2025-12** | ✅ **the only true monthly gaming series Cedar holds** |
| **CA CCGC** | quarterly | quarterly, **with 2026-03 missing and edge quarters short** | ⚠ holes, not just lag |
| **other state regulators** | annual, mostly | NM & AZ 403 behind Cloudflare — `NOT_CHECKED`, **not** `NOT_FOUND` | |
| **ONRR / resource revenue** | monthly disbursement, monthly + annual statistics | monthly, flat, ends 2026-06-30 | ✅ |
| **LODES** | annual, ~2-year lag | not re-probed | annual |
| **QWI** | quarterly, ~2–3 quarter lag | not re-probed | quarterly |
| **QCEW** | quarterly, ~5 months after quarter close | not re-probed | quarterly |
| **FAADS** | **retired** — superseded by USAspending | ends **2007-09-30**, 6,884 days back | ⛔ **closed by design; no cadence** |
| **Advan / Dewey** | weekly patterns | usable window **2018-03 → 2025, 2026 breaking** | ⛔ **cannot serve a recent-first cadence at all** |
| **api.sam.gov** | — | **10 calls/day** pending an org role request | ⛔ **not contacted; uniquely required for nothing** |

## 2.1 The LDA finding, because it changes the pull date

Measured over all **27,796** Cedar LD-2/LD-203 filings, days from the reporting
period's close to `dt_posted`:

| | |
|---|---:|
| median | **20** — the statutory deadline, exactly |
| **filed by day 20 (the deadline)** | **57.4%** |
| filed by day 27 (deadline + 1 week) | 70.5% |
| filed by day 34 (deadline + 2 weeks) | **74.0%** |
| filed by day 55 | 88.2% |
| filed by day 90 | 92.0% |
| filed by day 180 | 95.2% |
| filed by day 365 | 98.1% |
| p90 / p99 / max | 64 / 495 / 5,885 days |
| posted on or before the period close | 1,373 (early filers and terminations) |

Per quarter the medians are identical (20d) and the p90s are 42–55d. Under the
pre-2008 semiannual regime they were far looser: median 45d, p90 151–224d.

**And then the live probe, which is the finding that matters:**

> `lda.senate.gov` → HTTP 200. 1,976,414 filings. Ordered by `-dt_posted`, **the
> single most recently posted filing in the entire LDA system today is a
> `2A — 2nd Quarter Amendment` for filing year 2024** — a period that closed
> **2024-06-30, 787 days ago.**

The back-catalogue never stops moving. **A period-keyed pull is structurally
incapable of catching that filing.** The refresh key must be `dt_posted`, not
`filing_year` + `filing_period`.

> ⚠ **The strength of this one deserves stating precisely.** It rests on a
> *single* request. The API echoed `ordering=-dt_posted` back in its `next` URL,
> so the parameter was **accepted** — and acceptance is not application. This
> repo already records the shape: `recipient_type_names` on USAspending returns
> HTTP 200 with an empty set for a bogus value rather than an error. **Confirm
> with a second request** (`?ordering=dt_posted`, oldest-first) before quoting
> "787 days" as a headline. What does *not* depend on the probe, and is measured
> over 27,796 rows, is the distribution: **p99 = 495 days, max = 5,885**. The
> trailing re-pull is justified by the distribution alone.

---

# PART 3 — THE CALENDAR

## 3.1 The recommended default

| collection | REFRESH | DISCOVERY | trigger date | cost | if you skip a cycle |
|---|---|---|---|---|---|
| **Federal Register / federal actions** | **daily** | n/a — no entity population | any business day | minutes, ~1 API page/day | you go blind to the recognition-notice trigger that fires the spine rebuild |
| **FERC dockets** | **weekly** | quarterly | any | ~300 docket sheets, hours | little — filings persist; only the review queue goes stale |
| **NAGPRA notices** | **weekly** (rides the FR pull) | with the FR sweep | any | free, same request stream | nothing |
| **Prime contracts** | **monthly, on the 11th** | **quarterly** | archive publishes the 10th ~00:14Z | 20 objects × ~1.2–2.0 GB; hours | one month of new awards; the 2-month fill window means the *previous* month was provisional anyway |
| **Assistance** | **monthly, on the 11th** | **quarterly** | same object set | 20 objects; hours | same |
| **Subawards (FSRS)** | **monthly**, once the FY2021–24 hole closes | quarterly | after the prime refresh | ~2,733 paginated calls; **gated on the SAM org role** | the hole stays open; nothing else moves |
| **Lobbying (LDA)** | **quarterly at deadline + 10d (= day 30 from close), keyed on `dt_posted`, with a 4-quarter trailing re-pull** | annual | 30 Jan / 30 Apr / 30 Jul / 30 Oct | 15/min anon, 120/min keyed — cheap | you miss ~28% of the quarter *and* every amendment to the last two years |
| **990 / nonprofits** | **semiannual** | annual | Feb and Aug | e-file index is 10 annual files, ~77 MB each | **nothing.** An 18-month structural lag makes any faster cadence theatre |
| **FAC single audits** | **quarterly, with a 2-YEAR trailing window** | annual | ~3 weeks after each calendar quarter | api.data.gov key, 1,000/hr | ~31% of audits land late; a 9-month window silently drops them |
| **CT gaming (monthly)** | **monthly** | n/a — 2 facilities | ~mid-month | trivial, one open-data endpoint | ~~currently 8 months behind; the cheapest win in the file~~ — **wrong: measured live 2026-08-26, the endpoint itself stops at 2025-12-31. Cedar holds every casino-month it serves. See PART 5.** |
| **CA gaming (quarterly)** | **quarterly** | quarterly | ~6 weeks after quarter close | small | edge quarters are already short and 2026-03 is already missing |
| **Other state gaming** | **annual** | annual | per state | varies; NM/AZ blocked at 403 | little |
| **NIGC gaming revenue** | **annual** | annual | on release | one report | a year |
| **Resource revenue (ONRR)** | **monthly** | annual | ~6 weeks after month close | small | one month |
| **Deals** | **weekly sweep, quarterly deep pass** | continuous — deals *are* discovery | any | manual + press | **link rot.** Backfill reverse-chronologically; this is the one collection where delay destroys evidence |
| **IBIA / IBLA appeals** | **monthly** | annual | any | year indices | one month |
| **Entity spine** | **on the Federal Register recognition notice** | — | event | cascades everywhere | the whole build keys to it |
| **FAADS** | ⛔ **never** | ⛔ never | — | zero | **nothing, ever. The source ended in 2007 by design.** |
| **Advan / Dewey** | ⛔ **no recent-first cadence possible** | — | — | 298 GB national | its window ends in 2025 |
| **SAM** | ⛔ **not required for anything** | — | — | 10 calls/day | nothing — a concurrent agent proved SAM is uniquely required for nothing |

## 3.2 Why "the 11th"

The archive publishes on the **10th at ~00:14 UTC** with a stamp dated the
**6th**. Probing on the 9th finds last month's objects and burns a request
budget against a host that has already given us a 62-minute IP cooldown for
exactly that kind of impatience. Probing on the 11th finds the new stamp on the
first try. **Probe per-year, and never assume one global stamp.**

## 3.3 Why LDA moves from "+2 weeks" to "+10 days with a 4-quarter tail"

The old doc said *"pull two weeks after each deadline so late and amended
filings are in."* Measured, day 34 from period close captures **74.0%**. The
correction is not to wait longer — the curve is flat after day 55 and you would
be waiting for a 4% tail — but to **stop pulling by period at all**. Key on
`dt_posted >= last_pull` and re-read the trailing four quarters every cycle.
That is what catches a 2024-Q2 amendment posted in 2026.

## 3.4 Constraints that gate the calendar

- **SAM is 10 calls/day** pending an org role request. It gates nothing in the
  table above, because SAM is now uniquely required for nothing — but any plan
  that reintroduces a SAM dependency inherits a 10/day ceiling and must be
  costed at that rate. **Do not contact `api.sam.gov` casually.**
- **The FPDS-NG ATOM feed retires in FY2026.** It is a route with an expiry
  date. Anything that depends on it needs its data extracted *before* the
  retirement, not a cadence *around* it.
- **990s lag ~18 months structurally.** The 2025 endpoint is already near the
  source's own limit. A quarterly nonprofit cadence buys nothing.
- **Advan/Dewey's usable window is 2018-03 → 2025, 2026 breaking.** It cannot
  serve a recent-first cadence at all. Treat it as a historical panel.
- **One poller per host, always.** `api.usaspending.gov` and
  `files.usaspending.gov` are different hostnames and **one rate-limit budget** —
  they refused the same IP within two minutes of each other. Check
  `Win32_Process.CommandLine`; `ps aux` cannot answer this on Windows and
  manufactures false confidence. Where a peer is already polling, **its log is
  the cheapest probe available** and strictly better than adding a second prober.

### Host state observed at this run

- **`code/121_pull_subawards_api.py pull --sequential` is LIVE** (PID 13736,
  parent 8404). Both usaspending hosts were therefore refused by this script by
  policy, not by preference. Script 301 enumerates live pollers at start and
  records them in its output. **A dead wrapper is not a dead poller — and a live
  wrapper is not a live poller either. Check the child.**
- **`logs/_HOSTLOCK_web.archive.org.json` is no longer stale.** It was recorded
  as `active: true` behind dead PID 7420 with two items queued for 19 days. It
  has since been taken over by `code/213_cdx_targeted_nm_az_documents.py` (PID
  26476, claimed 22:58:48Z, `took_over_from: code/211_…`) and **released at
  2026-08-26T23:08:38Z**. No takeover was needed by this work.
- 266 host locks exist on disk. **Two were active at the final run** —
  `api.usaspending.gov` (PID 13736, `code/121_pull_subawards_api.py pull`, three
  jobs queued behind it) and `gaming.az.gov` (`code/217_pull_az_adg_report_archive.py`,
  claimed 23:29:32Z, a concurrent agent working the NM/AZ regulators). Script 301
  reads both and defers; it never probes a locked host.
- Three bounded probes were issued, one per host, ≥6s apart, honouring locks:
  `www.federalregister.gov` **200**, `lda.senate.gov` **200**, `api.fac.gov`
  **403**. The 403 is a fact about *that unauthenticated request* — `api.fac.gov`
  is fronted by api.data.gov and the keyed route answered 22 requests
  successfully at 22:37Z today. **A 403 on an unkeyed request is not a statement
  that the endpoint is closed.**

---

# PART 4 — TYING IT TO THE PRODUCT

Collections ship carrying `vintage`, `version` and `updated`, and the server's
docstring is explicit: **"Version and vintage are load-bearing, not garnish"** —
the citation string is generated from them. So the cadence must produce an
**honest** `vintage` on a schedule, and honesty here has a specific meaning:

> **`vintage` must name the last date the SOURCE covers, never the date we
> pulled.** They differ by 40 days on prime and 57 on assistance right now. A
> collection stamped `vintage: 2026-08-26` whose newest contract action is
> `2026-07-03` is a false citation, and it is false in the direction that
> flatters us.

**A second rule the measurement forces:** a collection assembled from more than
one source vintage cannot carry a single `vintage` string honestly.
`federal_funding_transactions.csv` today holds **`20260706` on 131,495 rows and
`20260806` on 93,536** — the file is real and correct, and no single stamp
describes it. Either re-pull the whole span under one stamp before shipping, or
publish `vintage` as the **oldest** contributing stamp and say so. Do not publish
the newest.

### 4.0a BOTH RULES ARE NOW IMPLEMENTED, AND THE COMPOSITION IS THREE, NOT TWO

*2026-08-26, `code/335`–`337` and the `code/87_build_dataset_notes.py` change.*

**The count above was incomplete.** 131,495 + 93,536 = 225,031 against a file
of **701,955 rows**, so **476,924 rows — 67.9% of the table — carried NO stamp
at all** and were invisible to a two-way description. They are not a mystery:
`source_file` names them to the day as the `Assistance_PrimeTransactions_`
**2023-04-09** bulk download. The composition is three strata, and it is
**year-aligned**:

| stratum | vintage | fiscal years | rows |
|---|---|---|---:|
| A | `usaspending_bulk_download_2023-04-09` | FY2008–2023 | 476,924 |
| B | `usaspending_award_archive_20260806` | FY2008–2023 | 93,536 |
| C | `usaspending_award_archive_20260706` | FY2007, FY2024–26 | 131,495 |

⚠ **Read stratum C carefully. FY2024, FY2025 and FY2026 sit on `20260706`,
which START_HERE records as dead everywhere since 2026-08-12.** The most recent
fiscal years — the ones a launch piece leads on — are the un-refreshed ones.
That is the opposite of the intuitive assumption and it should drive the next
re-pull's priority.

**What was implemented, so the next reader does not redo it:**

1. **Per-row vintage, never blank.** `code/335_harmonize_assistance_seams_in_place.py`
   adds `source_vintage` and `source_vintage_basis` to every one of the 701,955
   rows. A reader can now tell which rows came from which vintage by reading
   the row. The stamp is derived from `source_archive_stamp` where present and
   from the pull date recorded in `source_file` where it is not — both are
   recorded facts, neither is inferred.
2. **`vintage` in the notes contract is no longer the build date.**
   `code/87_build_dataset_notes.py` set `"vintage": TODAY`, which is exactly the
   false citation this section warns about. It now emits the **maximum of the
   table's period column** — so assistance cites **`2026-06-30`**, its true
   source edge, instead of `2026-08-26`, a **57-day overstatement removed** —
   plus `vintage_basis`, `built` (the old value, honestly named), and
   `source_vintages` carrying the full composition with
   `vintage_is_a_range: true`. A collection assembled from several vintages now
   ships the composition rather than choosing one and being wrong about the
   rest.
3. **A bare year stays a bare year.** Where a table's only period is a fiscal
   year — `gaming_revenue_bounds` — the vintage is `2025`, not a fabricated
   `2025-12-31`. Inventing a day is the defect that already put 415 gaming
   dates on day-15 and day-31.

**The audit that says this is the only such table:**
`code/334_audit_source_vintage_mixing.py` scanned **all 276 tables** under
`data/clean/` for multiple source vintages in one file. **One is mixed —
`federal_funding_transactions.csv` — and 275 are not.** See
`docs/VINTAGE_MIXING_AUDIT.json`.

⚠ **`prime_contracts.csv` is clean only because it records nothing.** It has no
`source_archive_stamp` column, so it cannot be mixed by measurement — but its
raw extracts came down under **both** stamps (FY2007–2016 under `20260806`,
FY2017–2026 under `20260706`, per §1.3), and that split survives into the clean
table with no column to expose it. **Assistance is the better-documented of the
two, not the worse one.** Giving prime the same `source_vintage` column is the
obvious next step and was not done here.

## 4.1 The year-turn refresh, per collection, stated exactly

Launch before end of calendar 2026; refresh once the year turns. FY2026 closed
2026-09-30, **but prime data stops 2026-07-03 and assistance 2026-06-30, so
FY2025 is the last complete fiscal year** and must be what the launch
collections advertise.

| collection | what the year-turn refresh changes | **when the data supports saying it** |
|---|---|---|
| **Prime contracts** | FY2026 becomes complete; `vintage` moves FY2025 → FY2026 | **archive published 2027-01-10** (stamp `20270106`). FY2026 closed 2026-09-30 + the measured 2-month fill = settled by ~2026-12-01, and the January archive is the first to carry all of it. **Do not claim a complete FY2026 before 2027-01-11.** |
| **Assistance** | same | same object set, same date |
| **Subawards** | FY2026 subawards land — **only if the FY2021–24 hole closed first** | FSRS filing +1 month after award month, so FY2026 is filed by ~2026-11-30 and appears in the **2027-01-10** archive. Blocked until 121 succeeds. |
| **Lobbying** | 2026 Q4 (closes 2026-12-31) | **2027-01-30**, deadline + 10d. Also re-read 2025Q4–2026Q3 for amendments; expect ~4% of 2026 filings still to arrive after this pull. |
| **990 / Schedule I** | **almost nothing** | tax-year-2025 volume is **4,614 rows against 9,779 for 2024 — 47%**, and the split says why: **June-2025 fiscal-year ends are fully in, December-2025 ends are at 12% of a December plateau**, because their extended deadline is 2026-11-15. Maturity ~mid-2027. **A year-turn 990 refresh is not worth running.** Move it to the Feb cycle and describe the collection as 2024-complete / 2025-partial. |
| **FAC single audits** | FY2025 audits (Dec-2025 year ends, due 2026-09-30) mostly land | **2027-01**, and *still* re-read two years back — 31% arrive late. FY2026 will not be presentable until 2027-09 at the earliest. |
| **CT gaming** | 2026 monthly series completes | **~2027-01-15**, one month after December. This one is genuinely current if we pull it. |
| **CA gaming** | 2026 Q4 | ~**2027-02-15**. Backfill 2025-03, 2025-12 and the missing **2026-03** in the same pass — those are holes, not lag. |
| **NIGC** | FY2026 gaming revenue report | **mid-2027**. Nothing to do at the year turn. |
| **Resource revenue** | 2026 months complete | ~**2027-02-15** |
| **Federal Register / NAGPRA / FERC / appeals** | continuous; the year turn means nothing | any day — but **pull now**, they are 20–21 days stale |
| **Entity spine** | Interior's annual recognised-entities notice | published late January (91 FR 4102 was **2026-01-30**). **Trigger the spine rebuild from that notice, not from a timer.** |
| **FAADS** | ⛔ nothing, ever | it is a fixed historical asset; stamp it once and never touch it |
| **Advan / Dewey** | ⛔ nothing | window ends 2025 |

**The one-sentence version for the owner:** *the year turn is a single event on
2027-01-10/11 that upgrades prime, assistance and subawards from FY2025-complete
to FY2026-complete; lobbying follows on 2027-01-30; nonprofits do not move at all
and should not be re-pulled; and four collections are stale today for reasons
that have nothing to do with the calendar.*

## 4.2 The collections that need no cadence

- **FAADS** — closed by design, ends FY2007. Stamp it once.
- **Advan / Dewey** — window closes 2025.
- **Anything sourced from the FPDS-NG ATOM feed** — extract before the FY2026
  retirement; there is no cadence, only a deadline.
- **Historical statute, compact text, ANCSA rulings** — settled facts with URLs.
  They change only when Congress acts, which the Federal Register feed sees.

---

## WHAT THIS CORRECTS IN THE 2026-08-06 VERSION

The previous document was written from publication schedules. Four of its rows
do not survive contact with the files.

1. **"Prime contracting — pull weekly."** ❌ The archive is replaced **monthly**,
   atomically, and there is nothing new between replacements. Weekly costs seven
   probes to learn one fact and risks the IP cooldown. → **Monthly, on the 11th.**
2. **"Federal funding — pull weekly; the last ~4 weeks are provisional."**
   ❌ Right in spirit, wrong in size. Measured, **two months** are provisional
   (2026-05 at 66%, 2026-06 at 60%), not four weeks. → **Monthly, trailing
   2-month re-read.**
3. **"Lobbying — quarterly, +2 weeks."** ❌ Day 34 from period close captures
   **74.0%**, and the newest filing in the whole LDA system today amends a period
   that closed in 2024. → **Deadline + 10d, keyed on `dt_posted`, with a
   4-quarter trailing re-pull.**
4. **"Nonprofit / 990 — quarterly."** ❌ p10 is 584 days. A quarterly cadence on
   an 18-month lag manufactures churn in a dataset that did not change. →
   **Semiannual.**

Three of its rules survive unchanged and are re-affirmed here:
**re-pull the trailing window rather than appending**; **never use a natural key
you have not proved unique** (the FEMA subaward `1843-GR35056` files against
eleven different Alaska Native villages); and **an upsert must never overwrite a
human ruling**.

## After ANY refresh, re-run in this order

```
py -3 code/62_no_regression_check.py       # baseline BEFORE
<the refresh>
py -3 code/124_apply_rulings_in_place.py   # rulings reapplied on top
py -3 code/207_normalize_extent_competed.py  # in-place; a prime rebuild reverts it
py -3 code/168_link_adjudication_hubs.py   # in-place enrichers run LAST
py -3 code/301_source_freshness_probe.py   # record what actually moved
py -3 code/62_no_regression_check.py       # must report no regressions
```

**Never run `01`, `09`, `41` or `88`.** They rebuild from a stale upstream and
silently delete later work.

**A full-rebuild stage and an in-place enricher on one file need an ordering, and
the enricher must run LAST.** This has now bitten FERC four times in one day.
Before any rebuild, check for a `.bak_*_pre<script>` file sitting beside the
target — that is the signal that an in-place linker has touched it.

**And run script 301 immediately after every refresh.** Its snapshot diff is the
only mechanism that turns "we think the source corrects retroactively" into a
measured trailing-window number. Today it holds a baseline for all 20
collections and reports no movement (nothing has refreshed since it was taken).
After the next refresh it will name **the oldest period that moved**, and that
number replaces every within-vintage estimate in Part 1.

> **The rule 301 earned against itself, on its first day.**
> `py -3 code/301_source_freshness_probe.py --only deals --stages files`
> overwrote the 243 KB full measurement with a 3.9 KB one and truncated the
> snapshot to 68 bytes — **erasing the diff baseline for all twenty
> collections**. It printed `wrote docs/SOURCE_FRESHNESS.json` and looked like
> progress. Same shape as `133 build` reverting `168`'s in-place links: a
> narrower run replacing a wider one, silently.
> Fixed and verified: a filtered or `files`-only run now writes
> `SOURCE_FRESHNESS.partial.json` and leaves the full measurement alone, and the
> snapshot **merges** rather than replaces, so a partial run updates only what it
> measured. **A partial run must never replace a full one** — and a monitoring
> tool that can destroy its own baseline is worse than no monitoring, because
> the loss is invisible until the next diff comes back empty.

---

# PART 5 — THE 2026-08-26 REFRESH, MEASURED BEFORE AND AFTER

*Executed the same evening this document was written, against the three
collections it named as stale for OUR reasons. Every figure below is from
`docs/SOURCE_FRESHNESS.json`, re-measured by script 301 after the work, and the
before-figures are from the same script's run four hours earlier — not from a
run log.*

| collection | last data BEFORE | last data AFTER | rows before → after | verdict |
|---|---|---|---:|---|
| **Federal Register** | 2026-08-05 (21d behind) | **2026-08-26 (0d)** | 156,452 → **156,772** (+320) | **CLOSED** |
| **NAGPRA notices** | 2026-08-03 (23d behind) | **2026-08-24 (2d)** | 6,729 → **6,772** (+43) | **CLOSED** — 2d is the source's own gap since the last notice |
| **CT gaming (monthly)** | 2025-12-31 (238d) | 2025-12-31 (238d) | 68,211 → 68,211 (0) | **NOT OURS — see below** |

## 5.1 Federal Register — incremental, because the two obvious tools are traps

`code/342_pull_federal_register_incremental.py`. 14 nets (1 agency + 13 keyword),
one shard each over **2026-08-06 .. 2026-08-26**, 320 documents, **zero already
held**, and **`records_retrieved == source_reported_total` on every one of the
14 shards**.

Neither existing script could do this:

- **`10_pull_federal_register.py` re-shards 1994..today.** Its cache key is
  `net__key__d0__d1`, so moving `END_DATE` renames the 2026 shard and refetches
  the whole year across all 14 nets to re-learn what we already hold.
- **`11_classify_federal_actions.py` is a FULL REBUILD** of
  `federal_actions.csv` from the raw file, and that table carries two columns 11
  does not write — `pre_2000_flag` and `floor_basis_field`, put there in place
  by `22_apply_temporal_floor.py`. **Running 11 reverts them.** This is the
  133-vs-168 collision (concurrency rule 5), which had already bitten this
  project four times in one day. **11 WAS NOT RUN.** 342 imports 11's own
  `classify()` and 22's own `year_of()` and appends instead.

`action_type` of the 320 new rows: `other` 176 · `rulemaking` 138 ·
`liquor_ordinance` 3 · `consultation` 1 · `federal_acknowledgment` 1 ·
`grant_solicitation` 1.

**THE COMPLETENESS CONTRACT, and why it is not optional here.** The next
incremental run derives its start date from `max(publication_date)` in the file.
So a partial window merged forward would advance that maximum past documents
never retrieved, and the gap would be **permanent and invisible** — defect class
4 with no `done` flag to inspect. 342 therefore merges **only** if every net
returned and every shard's retrieved count equals the `count` the API itself
reported; otherwise the fetched shards stay on disk as cache, the CSVs are not
touched, and the run is recorded `INCOMPLETE`. This run recorded `COMPLETE`.

## 5.2 NAGPRA — rode the same request stream, exactly as this document predicted

`77_build_nagpra_dataset.py fetch` then `build`. Universe 6,729 → **6,774**
notices; 43 fetched, **2 returned HTTP 404** (`96-9758-2`, `97-18431-2` — 1996
and 1997 documents with no plain-text rendition, a fact about those objects,
recorded not retried), so the built table is **6,772**. Bridge rows 51,521.

**A defect fixed to get there.** `77`'s `claim_host()` read `prev["pid"] > 0`
alone and treated any lock naming a pid as held. A lock records its holder's pid
forever — a poller that releases correctly leaves `active: false` and a
`released` stamp behind a pid that is simply history. So 77 could never claim a
host any well-behaved poller had used: it queued itself behind a lock 342 had
released **nine seconds earlier** and exited having fetched nothing. Now held
means `active` **and** no `released` stamp. **A false "host is busy" stops work
that would have succeeded**, which PULL_DISCIPLINE already records for the
mirror-image case.

> ⚠ **THE 2024 SURGE IS A REGIME CHANGE, NOT A FINDING.** The revised
> regulations at **43 CFR 10 took effect 2024-01-12**: the notice trigger became
> unconditional (*"for all human remains … in the inventory"*), the
> culturally-unidentifiable section was deleted, and **43 CFR 10.10(d)(3) sets a
> 2029-01-10 deadline** that is compressing a decades-old backlog into a
> five-year window. Notices per year go 244 (2022) → 496 (2023) → 707 (2024) →
> 900 (2025). **That is BOUNDED, not a trend, and it must fall after 2029.**
> Already documented at `docs/ASSUMPTIONS_AND_LIMITATIONS.md` (`NAGPRA_2024_RULE`)
> and in `series_breaks.csv`; do not re-derive it, and never publish the rise as
> institutional behaviour.

> ⚠ **`mni_total_stated` MUST NEVER BE SUMMED.** Those are counts of human
> beings. Note that **`77`'s own build log prints a sum** — *"total individuals,
> summed over notices that state one: 158,327"*. That line is not a licence:
> it is a diagnostic in a run log, it is not a column in any shipped table, and
> nothing downstream may reproduce it.

## 5.3 CT gaming — the diagnosis in this document was wrong, and the fix is free

`code/343_refresh_ct_gaming_monthly.py`, two bounded requests behind the
`data.ct.gov` lock:

```
$select=count(1)                     -> 200   748 rows reported
$limit=50000&$order=date             -> 200   748 rows retrieved
source span                                   1993-01-31 .. 2025-12-31
casino-months at the source Cedar does not hold:   0
```

**`gaming_facility_metrics.csv` was not touched, because there was nothing to
add.** Cedar already holds all 747 casino-months (× 4 measures = 2,988 rows,
plus the `Mohegan Sun Prior Period Adj.` row excluded and named), landed earlier
the same day by `159_extend_gaming_metrics.py`.

So **the 238-day gap is the SOURCE's**: CT DCP has published no month after
2025-12-31. Section 3.1's *"currently 8 months behind; this is the cheapest win
in the file"* is corrected above.

> **The rule this earns, and it is the mirror of one already in this document.**
> §1.1 says *"do not diagnose a source from a stale local file."* The mirror is
> equally cheap to get wrong: **do not diagnose OUR lag from a cached copy of
> the source either.** The cadence audit read "our file stops at 2025-12, CT
> publishes monthly, therefore we are eight months behind" — every clause true,
> the conclusion false, because nobody asked the endpoint. Whose lag it is
> changes the remedy completely: there is no pull to run, and the collection is
> current with its source. `payout` and `hold` stay withheld on the
> already-recorded unit break (`91.45` in 1993-01 vs `0.912` in 2025-12); that
> finding was inherited from 159, not re-derived.

## 5.4 What the diff measured, and what is now one refresh behind

Script 301's snapshot diff, the whole point of running it after rather than
asserting an improvement:

| collection | oldest period that moved | detail |
|---|---|---|
| `federal_register` | **2026-08** | 82 → 402 rows |
| `nagpra` | **2026-08** | 18 → 61 rows |
| every other collection | — | 0 rows moved |

**Nothing reached back past the current month.** For a 21-day incremental that
is the expected shape and it is now measured rather than assumed; a longer gap
would be needed to size any genuine retroactive reach for these two.

**NAMED, NOT MINE — downstream tables derived from `federal_actions.csv` are now
one refresh behind it.** The largest is `fr_content_classification.csv` at
156,452 rows against the parent's 156,772. Its writer,
`78_content_analysis.py`, is a single-writer full rebuild **that also rebuilds
five lobbying tables** (`lobbying_issue_families_filing.csv`,
`lobbying_issue_family_year.csv`, `lobbying_disclosure_verbosity_year.csv`,
`lobbying_target_entities.csv`, `agency_attention_vs_advocacy*.csv`), and a
lobbying-registrant agent was live on 2026-08-26. **Run it when no lobbying
build is running, not before.** The same applies to every other consumer of the
parent corpus — `130` (Section 106), `76` (recognition history), `98` (OIRA RIN
join), `133` (FERC seeds), `136` (FOIA index): each is a separate owner's build
and none of them was run here.
