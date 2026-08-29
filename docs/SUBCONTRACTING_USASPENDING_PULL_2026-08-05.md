# Dataset 2b — fresh USAspending/FSRS subaward pull, 2026-08-05

*Replaces the 2023 HigherGov export as Dataset 2b's source. Scripts:
`code/40_pull_usaspending_subawards.py`, `code/41_match_subawards_to_ledger.py`,
`code/42_write_subaward_source_doc.py`, `code/43_resume_subaward_pull.sh`.
Raw + `_SOURCE.md` in `data/raw/subcontracts/usaspending_subawards_2026-08-05/`.
Derived outputs are **staged**, in `data/staging/subawards_usaspending_2026-08-05/`.
`data/clean/` and `data/spine/` were opened read-only and are unmodified.*

---

## Headline: the well was never dry — it was the wrong well

| | 2023 HigherGov export | This pull (partial, 11 of 26 FY) |
|---|---:|---:|
| Subaward rows | 998 | **345,090** |
| Distinct UEIs | 304 | **51,519** |
| **Net-new UEIs vs the 2023 file** | — | **51,396** |
| Net-new vs union(2023 file, `fpds_uei_cage_map`) | **0** | **50,926** |
| Fiscal years | FY2011–FY2023 | FY2001–FY2011 so far |

The prior build's conclusion was right about its source and wrong about the ceiling.
`subcontract-05-09-23-22-23-37.csv` really was mined out — every one of its 304 UEIs was
already known. But that file was a HigherGov *query result* with an unpreserved sampling
frame. Going to the primary source with no recipient filter at all returns the whole
federal subaward universe, and **51,396 of its UEIs had never been seen by this project**
— from **one third of the target year range**.

Of the 1,798 Native-linked rows found so far, only **19** appear in the 2023 file. That
file was not a small sample of this population; it was a different population.

---

## 1. What was pulled

```
POST https://api.usaspending.gov/api/v2/bulk_download/awards/
{"filters": {"sub_award_types": ["procurement", "grant"],
             "date_type": "action_date",
             "date_range": {"start_date": "<FY start>", "end_date": "<FY end>"}},
 "file_format": "csv"}
```

Full request detail, discovered parameter values and per-file sha256 are in
`data/raw/subcontracts/usaspending_subawards_2026-08-05/_SOURCE.md` and
`_SOURCE_MANIFEST_usaspending_subawards.csv`. Three things worth carrying forward:

- **`sub_award_types` takes `procurement` and `grant`.** `sub-contracts` / `sub-grants`
  are rejected outright.
- **`date_type=action_date` keys on the SUBAWARD action date**, verified against a
  two-day probe, not on the prime's.
- **`date_range` is capped at one year.** Fiscal year is the largest possible chunk.
- **No agency or recipient filter was applied.** This is the entire federal subaward
  universe per year, which is what finally gives Dataset 2b a denominator. No
  share-of-market claim was ever supportable from the HigherGov export; from a complete
  pull, it will be.

### Rows per fiscal year, as returned

| FY | rows | contract subawards | assistance subawards | (a) native prime | (b) native subawardee | both |
|---|---:|---:|---:|---:|---:|---:|
| 2001 | 53 | 21 | 32 | 0 | 0 | 0 |
| 2002 | 220 | 4 | 216 | 1 | 6 | 0 |
| 2003 | 20 | 9 | 11 | 0 | 1 | 0 |
| 2004 | 31 | 14 | 17 | 1 | 0 | 0 |
| 2005 | 41 | 19 | 22 | 0 | 0 | 0 |
| 2006 | 118 | 88 | 30 | 0 | 0 | 0 |
| 2007 | 660 | 271 | 389 | 0 | 1 | 0 |
| 2008 | 1,291 | 749 | 542 | 1 | 6 | 0 |
| 2009 | 2,511 | 1,100 | 1,411 | 4 | 26 | 0 |
| 2010 | 13,501 | 5,350 | 8,151 | 42 | 66 | 5 |
| 2011 | 326,644 | 42,726 | 283,918 | 654 | 968 | 16 |
| **total** | **345,090** | **50,351** | **294,739** | **703** | **1,074** | **21** |

**FY2012–FY2026 are outstanding.** See §6.

---

## 2. The two populations, kept apart

Matching is UEI-exact against `data/clean/cedar_identifier_ledger_final.csv`. No fuzzy
matching and no new attribution method was invented. Rows matching on both sides are
held in a third bucket so neither headline double-counts.

| Population | rows | tier A | tier B | reported $ | **$ after QC (§4)** |
|---|---:|---:|---:|---:|---:|
| **(a) Native entity as PRIME**, subcontracting out | **703** | 68 | 635 | $1,459,250,858 | **$648,574,045** |
| **(b) Native entity as SUBAWARDEE**, under a prime | **1,074** | 390 | 684 | $1,113,075,039 | **$506,557,743** |
| Both sides Native | 21 | — | 5 | $25,118,085 | $25,118,085 |

**188 distinct NEID entities** appear: 129 federally recognized tribes, 33 Alaska Native
villages, 10 ANCs, 7 federal-level constituency entities, 4 self-governance consortia,
4 state-recognized tribes, 1 state-level constituency entity.

### Population (b) is the find, and it does not look like population (a)

Direction (b) was predicted to be "the revenue channel the prime-award data misses
entirely." It is, and the *shape* of it is the surprise. The primes paying Native
subawardees are overwhelmingly **state governments passing federal grants through**:

```
WA OFFICE OF SUPERINTENDENT OF PUBLIC INSTRUCTION -> MAKAH TRIBAL COUNCIL
MONTANA DEPARTMENT OF TRANSPORTATION              -> FORT PECK ASSINIBOINE & SIOUX TRIBES
WI DEPT OF PUBLIC INSTRUCTION                     -> MENOMINEE INDIAN TRIBE OF WISCONSIN
NORTH CAROLINA DEPARTMENT OF PUBLIC INSTRUCTION   -> EASTERN BAND OF CHEROKEE INDIANS
NE ST DEPARTMENT OF HEALTH                        -> PONCA TRIBE OF NEBRASKA
MONTANA STATE UNIVERSITY                          -> FORT PECK COMMUNITY COLLEGE
```

That is a **state-mediated federal funding channel to tribal governments**, invisible in
both the prime-contracting panel (the prime is a state agency) and the federal funding
panel (the recipient of record is a state agency). 294,739 of the 345,090 rows are
assistance subawards, and (b) is concentrated there. Anyone measuring federal dollars
reaching tribes from prime awards alone is undercounting by this entire channel.

Direction (a) looks completely different — ANC and village-corporation federal
contractors hiring commercial subcontractors (Arctic Slope, Doyon, Calista, Chenega,
Koniag families).

**These two must never be summed.** They are different economic relationships measured in
different directions.

---

## 3. What is NOT counted as Native-linked

| Bucket | rows | why |
|---|---:|---|
| Ledger tier C only | **3,521** | Tier C is literally `No attribution - discovery candidate`, with `tribe_id` **blank on 9,537 of the ledger's 9,550 tier-C UEI rows**. A tier-C hit means "this UEI is in the discovery pool," not "this is a Native entity." Counting it would fabricate 3,521 attributions. |
| Tier X exclusion ruling | 61 | Exclusion rulings are enforced, not reported as links. |

A first pass counted tier C as Native and reported 285 linked rows on FY2010 where the
true figure is 113. The distinction is worth stating loudly because the tier-C pool is
**twice the size of the real linked population**.

Tier A is the only publishable layer: **68 rows** in (a) and **390 rows** in (b).
The 1,319 tier-B rows need rulings before anything is published from them.

---

## 4. QC — 0.9% of the linked rows carry 54.6% of the dollars

**FSRS amounts are filer-entered and unaudited, and some are catastrophically wrong.**

The worked case that forced this check:

| field | value |
|---|---|
| prime award | `N6945011M3601`, **$64,910.88** |
| prime awardee | MOWA DEVELOPMENT LLC |
| subawardee | GEOPAVE LLC |
| **subaward amount** | **$794,526,041.00** |
| description | "SUBGRADE REPAIRS, ASPHALT AND STRIPE PARKING SPACES" |
| ratio | **12,240×** |

A subaward cannot exceed its own prime award. Left unflagged, this single row put a
state-recognized tribe at the top of the subcontracting-out league table. The second
worst is Montana DOT → Confederated Salish & Kootenai at **$598,550,278 on a $304,509
prime — 1,966×**.

Across the whole 345,090-row pull:

| check | rows | share | dollars |
|---|---:|---:|---:|
| `subaward_amount` > `prime_award_amount` | **5,941** | 1.7% | **$68,720,235,941** |
| ratio ≥ 10× | 869 | 0.25% | — |
| …of which Native-linked | **17** | **0.9% of linked rows** | **$1,417,194,109 = 54.6% of linked dollars** |

**Never publish an FSRS dollar total without filtering `subaward_exceeds_prime_flag`.**
Both the flag and `subaward_to_prime_ratio` are carried on every staged row. Rows are
flagged, never deleted, per the house rule.

---

## 5. The temporal floor, demonstrated rather than asserted

Cedar Press floors every dataset at 2000. **FSRS began under FFATA and phased in during
2010, so 2010 is the real data floor for Dataset 2b.** That is a source limitation, not
a coverage failure, and it is permanent — no other source can supply pre-2010 subawards.

Jobs were nonetheless submitted for FY2001–FY2009 so the floor would be demonstrated.
They returned **4,945 rows**, which is a trap: those rows are *misdated*, not early.

**Every one carries `subaward_sam_report_year` ≥ 2010** (min = 2010, distribution running
to 2026) — including a SpaceX subaward with `subaward_action_date = 2000-11-09` filed in
**2024**. The action date is a filer typo. Charting this range by action date would
publish a phantom 2001–2009 series.

Rows retained and flagged `action_date_precedes_ffata_flag = yes`, with
`subaward_sam_report_year` carried alongside so the test is reproducible downstream.

**Recommended entry for the STATE_OF_BUILD floor table:**
`2b Subcontracting | 2010– | cannot reach 2000 — FSRS did not exist before FFATA`.

---

## 6. This pull is incomplete — and how to finish it

**11 of 26 fiscal-year jobs are staged. FY2012–FY2026 are outstanding.**

`api.usaspending.gov` rate-limits by IP. At 21:16Z both `api.usaspending.gov` and
`files.usaspending.gov` began refusing every request with `RemoteDisconnected`, from a
fresh connection, and had not cleared 20 minutes later. This is the same edge block
documented for the FY2001–07 assistance backfill. Running six concurrent workers is what
tripped it; hammering through with retries appears to extend it, so the puller was
stopped deliberately rather than left running.

Nothing is lost. Every completed job is checkpointed and `pull` skips what is on disk.

```
bash code/43_resume_subaward_pull.sh
```

probes once every 300s, and on recovery:
1. `recover`s the FY2012/FY2013 jobs that were **already accepted server-side** before
   the block — they kept generating; re-submitting would discard completed server work
   and add load to an edge that is refusing us. Handles are in the run log.
2. finishes the remaining years at **`--workers 1`**.

Then re-run `41` and `42`; both are idempotent and read every `_state*.json` present.

**Expected final scale.** FY2011 alone is 326,644 rows. FY2012–FY2026 will be larger per
year. A completed pull is plausibly 5–15M rows and 2–4 GB of zips. Disk had 22.9 GB free.
Zips are stream-read and never extracted.

---

## 7. Review queue — 36 name near-matches, none attributed

`review/subaward_unmatched_2026-08-05.csv`. These are subawardees whose UEI carries **no
A/B attribution** in the ledger but whose normalized name matches a ledger entity name
exactly. `tribe_id` is blank on every row and a `YOUR_RULING` column is provided.

The genuine finds are Native entities the ledger does not yet reach under the UEI they
subcontract with — e.g. `RED LAKE BAND OF CHIPPEWA INDIANS` ($283,996),
`SQUAXIN ISLAND TRIBE` ($159,423), `TANANA CHIEFS CONFERENCE INC` ($141,501),
`COLVILLE CONFEDERATED TRIBES` ($25,120).

The file also surfaces **ledger tier-B defects, which is the point of not auto-linking**:
`UNITED STATES DEPARTMENT OF THE ARMY`, `INDIAN AFFAIRS, BUREAU OF` and
`PENNSYLVANIA STATE UNIVERSITY, THE` all normalize onto tier-B ledger rows carrying real
`tribe_id`s. Had this been an automatic name join, the Army would have been attributed to
an Arctic Slope village corporation.

A first pass indexed tier-C ledger names too and filled the queue with Duke University and
W.W. Grainger. The index is now restricted to rows that actually attribute an entity.

---

## 8. Two ledger issues found, neither fixed here

1. **`TRBF-KTNIID-00` conflates two distinct tribes.** Canonical name "Kootenai", tier A,
   `attribution_method = hand`. Its UEIs include `Kootenai Tribe Of Idaho` **and** `Cs&Kt`,
   `Salish Kootenai College, Inc.`, and the S&K company family — which belong to the
   Confederated Salish and Kootenai Tribes of the Flathead Reservation, Montana. Two
   different federally recognized tribes roll up to one NEID. Any per-tribe subaward
   total for either is wrong. **Needs an Elijah ruling; not touched.**
2. **`Cherokee General Corporation` → `ANRC-DOYONL-00` is CORRECT**, and worth recording
   as a positive: it is a Doyon Government Group subsidiary, tier A, ruled 2026-08-05
   with a `doyongovgrp.com` citation. A name-based matcher would have sent it to Cherokee
   Nation. This is the "Cherokee Inc. trap" resolved properly, and the reason UEI-exact
   matching is the rule.

---

## 9. Outputs

| Path | Rows | What |
|---|---:|---|
| `data/raw/subcontracts/usaspending_subawards_2026-08-05/*.zip` | 345,090 | 11 raw API zips, original filenames, sha256 in manifest |
| `…/_SOURCE.md` | — | endpoint, exact payload, pull date, row counts, schema |
| `…/_SOURCE_MANIFEST_usaspending_subawards.csv` | 11 | per-file sha256, bytes, date_range, rows |
| `…/_state.json`, `_state_pre2010.json` | 11 jobs | checkpoints; resume reads these |
| `data/staging/…/subawards_native_linked_2026-08-05.csv` | **1,798** | Native-linked rows, both populations, tier + QC flags |
| `data/staging/…/subaward_native_entities_2026-08-05.csv` | **188** | per-NEID rollup, (a) and (b) columns kept separate |
| `data/staging/…/subaward_uei_netnew_2026-08-05.csv` | **51,519** | every UEI seen, with in-2023-file / in-FPDS-map / in-ledger flags |
| `data/staging/…/subaward_rows_by_fiscal_year.csv` | 11 | the FY table above |
| `data/staging/…/_SUMMARY.json` | — | every figure quoted in this document |
| `review/subaward_unmatched_2026-08-05.csv` | **36** | name near-matches, unattributed, awaiting rulings |

**Nothing in `data/clean/` or `data/spine/` was written.** The master pipeline was not
run. Promotion of the staged outputs into Dataset 2b is a separate, deliberate step that
should wait until the pull is complete.

---

## 10. Standing caveats

1. **FSRS is self-reported, threshold-gated and unaudited.** Absence of a subaward is not
   evidence that no subcontracting occurred. Every total is a lower bound.
2. **The most recent fiscal year will be partial** when FY2026 lands — pulled mid-year.
   Never chart it as a decline.
3. **`prime_award_naics_code` is the prime contract's industry, not the subaward's.** For
   TEIM input-output work this describes demand, not the supplying industry.
4. **Assistance subawards carry no NAICS at all**, so any industry cut silently restricts
   to the 50,351 contract rows and drops the 294,739 assistance rows — which is where
   population (b) mostly lives.
5. **Tier B is not publishable.** 1,319 of the 1,798 linked rows are tier B.

---

# PROMOTION — 2026-08-06

`code/45_promote_subawards.py` merged the staged pull into `data/clean/subawards.csv`.
Zero network requests were issued: the puller (PID 15684,
`40_pull_usaspending_subawards.py pull --workers 1`) was verified live via
`Win32_Process.CommandLine` and left alone, per PULL_DISCIPLINE rule 1.

## The pull grew while the document above was being written

§1's table describes 11 fiscal years. **22 are now on disk** — FY2001–FY2020 plus FY2025
and FY2026 — for **6,613,471 raw rows**, not 345,090. FY2021 is mid-flight; FY2022, 2023
and 2024 are outstanding. The figures in §1–§4 above are superseded by this section.

| | doc §1 (11 FY) | promotion (22 FY) |
|---|---:|---:|
| raw rows | 345,090 | **6,613,471** |
| Native-linked | 1,798 | **53,429** |
| net-new UEIs vs the 2023 file | 51,396 | **251,814** |
| (a) Native as prime | 703 | **18,696** |
| (b) Native as subawardee | 1,074 | **22,096** |

## The key that would have destroyed the dataset

`(prime_award_id, subaward_number)` is **not unique** and must never be used to dedupe.
It collapses 53,417 rows onto 30,773 keys — **22,644 rows destroyed**. FEMA disaster
grant `1843DRAKP0000000` files subaward number `1843-GR35056` against **eleven different
Alaska Native villages** (Eagle, Tuluksak, Akiak, Akiachak, Tanana, Fort Yukon, Kwethluk
and more). Deduping would have merged eleven tribes into one row. This is the MR-7 error
wearing new clothes: the excess rows are distinct records, not repeats.

Identity key actually used:
`(prime_award_unique_key, subaward_number, subawardee_uei, action_date, amount, description)`.
3,082 groups repeat on it (12,623 excess rows) and **0 of those groups span a fiscal
year**, so they are same-year re-filings.

## The seam: HigherGov is a coarser rendering, not a rival population

HigherGov writes composite `IDV-ORDER` prime ids (`W52P1J18DA075-W91QVN20F0157`) where
USAspending carries order PIID and parent PIID separately. Matching raw strings finds
**203** overlaps; matching PIID variants finds **442** — a naive key misses more than half
the seam.

Of the overlapping rows, **121 are the same subaward with cents rounded away**
(711,657.0 vs 711,657.10) and **16 are HigherGov aggregating several FSRS filings into
one row**, reconciling to the cent: `W9124A13C0002 / FTHU-B-002` = $1,094,669 against
$352,381 + $742,288.37. 66 do not reconcile within $1 and are left flagged, not judged.

**FY2023 cannot be compared across sources** — the primary pull has no FY2021–2024 yet.
The FY2023 rows in the promoted file come only from HigherGov (23) and the funding
forward-fill (99).

## The free bonus is population (a), and only (a)

The 682 rows in `data/raw/federal_funding/usaspending_2023_2026/Assistance_Subawards_*.csv`
cover FY2023–2026 (102 / 184 / 261 / 135) and cost nothing. **They are not a
full-universe slice.** `request_fy2024.json` shows the filter:
`recipient_type_names = ["indian_native_american_tribal_government"]`, applied to the
**PRIME**. So the prime is a Native entity by construction and the file **cannot observe
population (b) at all**.

The trap: 204 of those rows match the ledger only on the subawardee side, which a
mechanical reading would label direction (b). All 12 primes on them are **intertribal
organizations** — Northwest Indian Fisheries Commission (120 rows), USET, Columbia River
Inter-Tribal Fish Commission, Southern Plains and Great Plains tribal health boards,
Great Lakes Inter-Tribal Council. The ledger declines to attribute those to a single
tribe because, per the taxonomy, `I-` entities have **members, not owners**. They are
carried as direction (a) with `prime_native_tier = source_filter` and
`source_population = prime_tribal_filtered`.

## Two filters, not one

```
countable  =  duplicate_status == 'primary'
              AND subaward_exceeds_prime_flag != 'yes'
```

All 55,035 rows are retained. 41,743 are countable; 12,446 are
`exact_repeat_within_source`; 846 are `superseded_by_primary_source`.

The dollar rule removes **492 rows carrying $5,959,656,647** — a quarter of the
$23.9B unfiltered total. It is written into `code/24_generate_dataset_docs.py`'s SPEC,
not into the generated file, so regeneration cannot wipe it.

## Population (b) at scale: the shape claim needs splitting

By **row count** the state-mediated pass-through channel holds: 16,941 of 22,096 (b) rows
are assistance subawards. By **dollars** it does not — the ranking is led by defense and
commercial primes (Alcyon Technical Services JV $972M, Indyne $552M, Exelis $506M,
Lockheed Martin $480M, United Excel $404M), with state agencies well below (SC Employment
& Workforce $103M, PA Public Welfare $79M). Both statements are true; say which.

## Tier B carries more dollars than tier A, and some of it is wrong

| direction | tier A | tier B |
|---|---:|---:|
| (a) Native as prime | $4.73B (10,050 rows) | $3.90B (8,274) |
| (b) Native as subawardee | $3.31B (8,864 rows) | $5.27B (13,090) |

**Tier A total $8.03B. Tier B total $9.17B.** Two large tier-B links are provably wrong:
`PENNSYLVANIA STATE UNIVERSITY, THE` → `TRBF-LWSXMN-00` (3,301 rows, ~$987M) and
`GEORGE MASON UNIVERSITY` → `AKNF-PRBLFC-00` (1,346 rows, ~$425M). §7 above predicted
exactly this. Tier B never publishes, so nothing shipped wrong — but no tier-B aggregate
is safe. 432 tier-B entities carrying ≥$1M each ($9.84B) are queued with a `YOUR_RULING`
column in `review/subaward_tierB_attribution_review_2026-08-06.csv`.

`data/clean/brand_family_proposals.csv` (484 rows) was **not applied**: every row is
`proposed_tier = B`, so it is a proposal set awaiting rulings, not an attribution source.

## To finish

Re-run `py -3 code/41_match_subawards_to_ledger.py` then
`py -3 code/45_promote_subawards.py` when FY2021–2024 land. Both are idempotent and
rebuild from every `_state*.json` and zip present. Re-run them after any batch of ledger
rulings too — the ledger grew between this session's match pass (53,417 links) and its
promotion pass (53,429), and script 45 picked up the newer version.
