# Documentation Contradictions Register — audited 2026-08-26

*A sweep of the ~110 markdown documents in `docs/` plus the four root-level state documents,
looking for places where two documents assert different values for the same fact. Every
"ground truth" figure below was counted from the actual CSV on 2026-08-26, not taken from a
document.*

**Why this file exists.** There is no version control here, so a superseded number does not
get overwritten — it goes on sitting in the document where it was written, indefinitely,
looking exactly as authoritative as a current one. The build logs are individually
excellent and mutually inconsistent. This register is the index that lets a future session
tell which is which.

**How to use it.** Before quoting any number from a build log, check whether it appears
below. If it does, the "correct" column is the measured value. Items are ordered by how
much damage acting on the wrong value would do.

---

## Ground truth

**RE-MEASURED 2026-09-01 by workstream H.** This register exists to be the
arbiter when two documents disagree, which makes a stale line here the most
expensive stale line in the repository — it is *believed*. Six of the fourteen
rows had gone stale in five days. The `2026-09-01` column is the live count;
where it differs, **the 2026-09-01 figure is the one to quote.**

The regenerable, always-current version of this table is
`docs/INVENTORY.md` (`py -3 code/521_inventory.py`), which measures every one
of 300+ tables rather than these fourteen. Prefer it. This register is kept for
the *contradictions* below, which are prose and cannot be regenerated.

| file | as measured 2026-08-26 | measured 2026-09-01 |
|---|---|---|
| `data/clean/prime_contracts.csv` | 1,217,768 rows · $310.01B · FY2000–2026 · attributed $244.77B (79.0%) across 498 entities | **unchanged at 1,217,768 rows**; attributed obligations $244,765,639,853.91 across 498 entities; **0 literal duplicate rows** (the 80,778 were distinct FPDS transactions, restored by `430`, none deleted) |
| `data/clean/federal_funding_transactions.csv` | 684,923 rows · FY2007–2026 | **701,955 rows** |
| `data/clean/faads_transactions_all_agencies.csv` | 2,769,748 rows | unchanged · 179,259 literal duplicate rows (DIAGNOSED, not repaired) |
| `data/clean/subawards.csv` | 63,548 rows | **72,837 rows** · 10,770 literal duplicates |
| `data/clean/cedar_identifier_ledger_final.csv` | 20,559 rows · A 2,148 · B 5,690 · C 12,524 · X 197 · `tier_A_ruled` 1,538 | **20,577 rows · A 2,286 · X 468 · `tier_A_ruled` 1,676** (from `62`'s live metrics) |
| `data/spine/cedar_entity_spine.csv` | **1,310 entities**, 16 classes | **1,555 entities, 17 classes** — and it moved TWICE during the 2026-09-01 pass (1,536 → 1,555 while three workstreams ran). Never quote the spine size from a document; read `data/spine/cedar_identity_register.csv`, the one table git tracks |
| `data/clean/gaming_ordinances.csv` | 1,155 rows = 321 `ORIGINAL_ORDINANCE` + 834 `AMENDMENT`; **299 distinct `tribe_id`**, 55 rows blank; 314 distinct `tribe_name` | 1,155 rows unchanged; **302 distinct `tribe_id`** |
| `data/clean/gaming_property_locations.csv` | 2,212 rows; **1,068 rows** `publishable = Y` with coordinates | 2,212 rows; **1,471 rows `publishable = Y`** (741 `N`, which is the figure §7 of the owner queue uses). The 1,068 was the *with-coordinates* subset — a different question, and the two were being read as the same one |
| `data/clean/deals_classified.csv` | 921 rows · 874 entity-linked | **935 rows · 886 entity-linked** |
| `data/clean/resource_revenue.csv` | 10,482 rows · **734 recipient-linked** | unchanged |
| `data/clean/ferc_docket_filings.csv` | 81,805 rows · 127 dockets · `ADVOCACY` 18,310 + `GOVERNMENT_ENGAGEMENT` 228 · `is_lobbying` = 0 on every row | **102,615 rows** · 822 literal duplicates |
| `data/clean/fac_tribal_single_audits.csv` | 6,780 rows · 2,052 `is_public = 1` | unchanged |
| `data/clean/np_schedule_i_grants.csv` | 58,685 rows · **627** distinct `filer_ein` | unchanged · 101 literal duplicates |
| `data/clean/admin_appeal_decisions.csv` | 15,613 = IBIA 4,855 + IBLA 10,758 | unchanged at 15,613 |

---

## A. Contradictions that would cause real damage if acted on

### A1. `docs/USASPENDING_PROBLEM_BRIEF.md` will send someone to re-run a completed merge

Line 29 says the 631,507-row full-universe backfill is **"not yet merged"**, and line 28
gives prime as **826,637 rows** — under a heading reading *"Verified by direct measurement
on 2026-08-12, not from memory."* The merge completed: `AGENTS.md:728` records
`826,637 → 1,217,768`, and the file holds 1,217,768 today.

**Danger:** re-running a merge that has already run is exactly the shape of the
`09_import_rulings.py` accident. Correct value: **1,217,768, merged.**

### A2. The same brief writes off a retrievable fiscal year as an open problem

`docs/USASPENDING_PROBLEM_BRIEF.md:51` — *"The static archive only goes back to FY2008.
FY2000–2007 prime contracts cannot be fixed this way. This is an open problem."*

`docs/PRIME_ARCHIVE_PULL_LOG.md` contradicts it directly: `_All_Contracts_Full_` exists for
**FY2007 through FY2026**. There is no FY2000–FY2006 file, but **FY2007 exists** and
`START_HERE.md` classifies it as a *host edge-block, not absence*.

**Danger:** the SAM.gov backfill scope (FY2000–**2007**) is sized off the brief's error, and
SAM is rate-limited to 10 requests/day without the pending role grant. A day of that budget
could be spent retrieving a year the free archive already serves.
**Correct: the archive reaches FY2007.**

### A3. `STATE_OF_THE_LAND_2026-08-07.md` lists two *reversed* dead ends under "do not re-attempt"

The document has a section headed **"WHAT IS EMPTY ON PURPOSE — do not re-attempt"**,
described as *"documented ceilings, not unfinished work."* Two of its entries have since
been overturned, and the document was never annotated:

- **Lines 51–53, `resource_assets.csv` (0 rows).** Attributed to source limits — ND DMR and
  MT BOGC recording well location but never mineral ownership.
  `docs/RESOURCE_ASSETS_BUILD_LOG.md` (2026-08-12) found the real cause: **a code defect.**
  Script 83 wrote the file outside its `do_all` branch and **truncated it on every partial
  run.** The file now holds 35 assets and 41 party links across 16 Native entities.
- **Lines 63–65, tribal Single Audits.** Asserted as barred by 2 CFR 200.512(b)(2) on the
  strength of one auditee returning `is_public: false` ten times.
  `START_HERE.md` reverses it: **6,780 records, 2,052 public (30.3%).** 200.512(b)(2) is an
  **auditee opt-out, not a bar.**

**These are the same error twice: a property of one record read as a property of the whole
system** — and in the `resource_assets` case, a property of *our own bug* read as a
property of the source. A "documented ceiling" claimed from a single observation is a
hypothesis. `START_HERE.md` already records the Single Audit reversal; nothing records the
`resource_assets` one outside its own build log.

### A4. `docs/FACT_CHECK_2026-08-06.md` finding B-27 is now itself stale, and prescribes a regression

B-27 (line 316) flags `docs/COVERAGE_AUDIT.md` as wrong and prescribes
**exact 617 / absent 80 / bounded 77** for `gaming_facilities.open_date_class`. Later
same-day sweeps in `docs/GAMING_TEMPORAL_BUILD_LOG.md` moved it to
**exact 635 / bounded 90 / absent 49**, and `COVERAGE_AUDIT.md:94` already carries the
newer figures.

**Danger:** anyone working the FACT_CHECK list top-to-bottom will overwrite a correct number
with a stale one, believing they are fixing an error. **COVERAGE_AUDIT is right here.**

### A5. A superseded ledger denominator is baked into a consumer-facing rule

`docs/datasets/02b_subcontracting.md:30` — *"`tribe_id` is blank on 12,681 of **12,711**
tier-C ledger rows."* Tier C is **12,524**. This is a published "never do this" rule
teaching a ratio computed against a ledger that no longer exists. `docs/datasets/*.md` is
**generated** by `code/24_generate_dataset_docs.py`; fix the script, not the output.

### A6. Lobbying "97.0% keyed" is computed on a file that already dropped 29.5% of filings

`docs/LOBBYING_EXPANSION_RECONCILIATION.md:55` headlines *"27,796 filings, 97.0% keyed —
the highest keyed rate of any Cedar dataset."* Not arithmetically wrong, but the
denominator is the **post-match** file. `docs/LOBBYING_BUILD_LOG_2026-08-05.md:44-47`:
39,448 filings were scored, **27,796 matched (70.5%)**, 11,652 did not.

True coverage of the pulled universe is 26,955 / 39,448 = **68.3%**. Quoting "97% keyed,
highest of any dataset" in a sales context is **off by 29 points**, and it is the kind of
claim that does not survive a buyer's own check.

---

## B. Same fact, several values

### B1. Spine entity count — four live values, none marked superseded

| value | asserted in |
|---:|---|
| 687 | `docs/datasets/02_contracting.md:7` · `docs/ENTITY_HARVEST_LOG.md:19-21` · `docs/FEDERAL_ACTIONS_BUILD_LOG_2026-08-05.md:103` · `docs/DATASET5_LINKED_FILE_BUILD_LOG.md:194` · `docs/LOBBYING_BUILD_LOG_2026-08-05.md:405,494` |
| 866 | `docs/COMPETITIVE_POSITION.md` — nine places |
| 952 | `STATE_OF_BUILD.md:118,175` · `docs/ENTITY_KEY_PROPAGATION_LOG.md:7` · `docs/SUBSET_DATASETS.md:88` · `docs/TCU_CDFI_BUILD_LOG.md:7` |
| **1,310** | `AGENTS.md:16` · `docs/DATASET_SCAFFOLD.md:14,41,98` · `docs/FAADS_NAME_ATTRIBUTION_LOG.md:98` · `docs/SOURCING_STRATEGY.md:92` · `docs/GAMING_ORDINANCE_BUILD_LOG.md:338` |

**1,310 is correct.** The upgrade path is traceable: `TCU_CDFI_BUILD_LOG.md:36` records
952 → 1,082, `BIE_UIO_BUILD_LOG.md:41` records 1,082 → 1,310.

**The trap is `COMPETITIVE_POSITION.md`**, which *corrects* 687 → 866 in an authoritative
voice. A reader who finds that correction reasonably concludes the question was settled at
866. Flagged in place 2026-08-26.

### B2. Identifier ledger — `STATE_OF_BUILD.md` asserts both values, fifty lines apart

- `STATE_OF_BUILD.md:126-127` — 20,559 links; tiers 1,708 / 5,963 / 12,711 / 177
- `STATE_OF_BUILD.md:176-177` — 19,232 links; tiers 1,705 / 4,637 / 12,711 / 179

Neither table names the file it measured (`_final` vs `_tiered`), which is the whole
problem. **19,232 is the signature of the unsafe `09_import_rulings.py` rebuild**
documented at `AGENTS.md:33` — the one that destroyed 1,327 rows. Current: **20,559 rows,
A 2,148 · B 5,690 · C 12,524 · X 197.**

The 19,232 figure also survives in `docs/COMPETITIVE_POSITION.md` (flagged in place today).

### B3. `subawards.csv` — four values across four documents

| value | asserted in | what it actually is |
|---:|---|---|
| 998 | `docs/SUBCONTRACTING_BUILD_LOG_2026-08-05.md:118` | the 2023 HigherGov export — now **one of three source datasets inside** the promoted file |
| 55,035 | `docs/COVERAGE_AUDIT.md:12` | the promotion of 2026-08-06, **before** the 8,513-row raw-match pass |
| 67,229 | `STATE_OF_BUILD.md:108` | **matches nothing.** Appears in no other document and no file |
| **63,548** | `docs/SUBAWARD_RAW_MATCH_LOG.md:109,167` · `docs/SUBAWARD_API_PULL_LOG.md:18,207,214` | correct — 55,035 + 8,513 |

Related, and separately corrected in `docs/COMPETITIVE_POSITION.md` today: **345,090 is not
a subaward count at all.** It is raw all-recipient rows from the first 11 of 26 fiscal
years, superseded the same day by 6,613,471. And `subaward_uei_netnew_2026-08-05.csv`
(252,078 rows) is a **one-row-per-UEI dimension table, not subawards** — summing it into a
row count produces a phantom ~317k figure.

### B4. Lobbying filings — 43,963 vs 27,796

- `STATE_OF_BUILD.md:110` — 43,963
- `docs/FACT_CHECK_2026-08-06.md:296-297` (B-2, B-3) — recomputed **27,796**; 43,963 wrong
- `SPEC_v2_ENTITY_EVENT_INTELLIGENCE.md:27` — carries both, guessing *"43,963 may be raw filings"*

**27,796 is correct.** The guess is wrong too: the raw pull is **39,448**
(`LOBBYING_BUILD_LOG_2026-08-05.md:220`). **43,963 matches no lobbying file at any stage.**

### B5. Federal assistance rows — 476,924 vs 608,419 vs 684,923

- `docs/COVERAGE_AUDIT.md:10` — 476,924, FY2007–**2023**
- `docs/USASPENDING_PROBLEM_BRIEF.md:32` — 608,419, FY2007–2026, **"complete for its span"**
- `docs/ASSISTANCE_ARCHIVE_PULL_LOG.md:364` — 608,419 → **684,923 (+76,504)**

**684,923 / FY2007–2026 is correct.** *"Complete for its span"* is the dangerous phrase — it
discourages the very check that would have found the 76,504 rows.

### B6. FAC tribal Single Audits — 6,774/2,046 vs 6,780/2,052

- `docs/GAMING_SPEC_RECONCILIATION.md:231` and `docs/GAMING_FINANCIAL_EXHAUST_BUILD_LOG.md:27` — 6,774 / 2,046
- `START_HERE.md` — 6,780 / 2,052 (30.3%)

**6,780 / 2,052 is correct.**

### B7. Archive key count — 4,631 vs 4,597

`docs/ASSISTANCE_ARCHIVE_PULL_LOG.md` says 4,631 at lines 35/52/60 and then **self-corrects
at 413-416**: a re-enumeration on 2026-08-12 returned **4,597**. `PRIME_ARCHIVE_PULL_LOG.md`,
`AGENTS.md:681` and `START_HERE.md` all use 4,597.

But `docs/SUBAWARD_API_PULL_LOG.md:26` still cites *"zero of 4,631 keys"* as its settling
evidence, written the same day. **The conclusion survives; the citation points at a listing
that was retired hours later.** Correct: **4,597**.

### B8. Gaming facility universe — 775 vs 774

`docs/GAMING_PROPERTY_SITE_BUILD_LOG.md:71` says 775 and **contradicts itself two lines
later at :73** with 774. `docs/FACT_CHECK_2026-08-06.md:302` (B-8) already recorded 775 as
an error. **774 is correct**, corroborated by `GAMING_TEMPORAL_BUILD_LOG.md:1140`,
`GAMING_SPEC_RECONCILIATION.md:81` and `COVERAGE_AUDIT.md:21`.

### B9. Resource revenue linkage — 13 entities vs 734

`docs/DATASET_SCAFFOLD.md:107` — *"Resources | 10,482 rows, **13 entities**"*.
Measured: **734 recipient-linked rows**. The scaffold's figure makes the dataset look
unusable and would kill it in any prioritisation pass.

### B10. Schedule I filers — 628 vs 627

628 in `docs/SCHEDULE_I_BUILD_LOG.md:54`, `docs/GRANTMAKER_FUNDING_FLOWS_BUILD_LOG.md:31`
and `START_HERE.md`; **627** in `logs/build_litigation_positions_2026-08-12.md:120` and in
the file. Three documents propagated one source's off-by-one. **627 is correct.**
Harmless to every conclusion — recorded so nobody re-derives it.

---

## C. Superseded without a banner

### C1. `docs/SUBCONTRACTING_BUILD_LOG_2026-08-05.md` — the file named after the dataset

Line 118 still reads *"`data/clean/subawards.csv` | **998** | One row per subaward.
`direction` = `unknown` on all 998, by design."* Both halves are dead:
`docs/datasets/02b_subcontracting.md:20` records that the HigherGov export **is superseded**
— *a different population, not a sample; only 19 of its rows recur in the primary-source
pull* — and `:29` shows `direction` now separating populations (a) and (b).

Someone opening the build log named after the dataset reads 998 as current. **Banner added
2026-08-26.**

### C2. Gaming ordinance provisions — the superseding log announces itself; the superseded ones stay silent

`docs/GAMING_ORDINANCE_OCR_MERGE_LOG.md:5` states it *"supersedes `GAMING_ORDINANCE_BUILD_LOG.md`
on every count it restates."* Good practice — but it only works from one direction.

| measure | pre-OCR (still asserted) | post-OCR (correct) |
|---|---:|---:|
| `tribal_gaming_agency_named` rows | 741 | **973** |
| …tribes | 284 | **307** |
| …distinct agency names | 397 | **469** |
| `licensing_provisions` rows | 728 | **932** |
| …tribes | 296 | **317** |

Still carrying the old figures: `docs/GAMING_ORDINANCE_BUILD_LOG.md:149,225` and
`docs/GAMING_SPEC_RECONCILIATION.md:196`. **`GAMING_SPEC_RECONCILIATION.md` is not even
named as a companion**, so a reader following the pointer will never find it.

**The lesson generalises:** a supersession banner on the *new* document is only half the
job. The old document is the one people open.

### C3. "321 tribes" on the gaming ordinance file — contradicted inside its own build log

`START_HERE.md` and `docs/GAMING_SPEC_RECONCILIATION.md:155` both say **321 tribes**.
`docs/GAMING_ORDINANCE_BUILD_LOG.md:269-270` says plainly: **"So NIGC's 321 rows are not 321
distinct tribes."** and `:327` gives **305 of 321** resolving.

Measured 2026-08-26: **299 distinct `tribe_id`**, 55 rows blank, 314 distinct `tribe_name`.
So **321 is wrong and 305 is also wrong.** The row arithmetic (321 originals + 834
amendments = 1,155) is right everywhere. It is only the tribe count that is bad.

### C4. FACT_CHECK findings still uncorrected in their target documents

Two findings from `docs/FACT_CHECK_2026-08-06.md` were recorded and never applied:

- **A-11** (line 36) — flags *"this is a rounding artifact stated as an absolute. 65 rows
  do; 14 of the 66 agency-years are non-zero."* `docs/COVERAGE_AUDIT.md:63` still reads
  *"**No row** carries a recipient identifier before 2007… 0.0% DUNS across every agency."*
  **The conclusion survives** — no tier-A series before FY2007 — **the absolute does not.**
- **B-33** (line 319) — flags the combined-series claim. `COVERAGE_AUDIT.md:75` still reads
  *"`faads` 2000–2007 + `federal_funding` 2007–2023 → 2000–2023 continuous."* It is
  **2001**–2023 (B-32: `fiscal_year` starts 2001) and it unions two different populations.
  Separately, `federal_funding` now reaches **2026**, so the "still short of 2026 by 3 yr"
  conclusion is doubly wrong.

**The structural finding here matters more than either item: a fact-check that nothing acts
on becomes another stale document.** `FACT_CHECK_2026-08-06.md` correctly identified the
deals-790 miscount as B-1 on 2026-08-06, and 790 was still propagating into `START_HERE.md`
and `COMPETITIVE_POSITION.md` three weeks later.

### C5. Gaming location layer — a tier distribution that cannot be what it says

`docs/GAMING_LOCATION_LAYER.md:218` — *"Tier distribution of **publishable rows**:
A 689 · B 101 · C 681"*, which **sums to 1,471**. Line 222 says *"1,067 geocoded rows."*
Measured: **1,068 rows** are `publishable = Y` with coordinates.

539 (properties, line 44) and 1,068 (observation rows) are compatible — different units.
**1,471 is not compatible with either**, and 1,067 is off by one. Line 218 is probably
measuring all 2,212 rows, but that is a guess; **undecidable from the files.** Do not quote
line 218.

---

## D. Where the largest concentrations of stale numbers sit

`STATE_OF_BUILD.md` (2026-08-06) and `STATE_OF_THE_LAND_2026-08-07.md` (2026-08-07) have not
been touched since they were written and are the two densest concentrations of superseded
figures in the project. Between them they carry the 19,232 ledger, the 952 spine, the 67,229
subaward count, the 43,963 lobbying count, and both reversed dead ends. **Banners added
2026-08-26; the contents were deliberately left intact**, because their *reasoning* is
still good and rewriting them would destroy the record of how the project thought at that
point.

Prefer `START_HERE.md` on any conflict with either.

---

## ADDED 2026-08-26 evening — `gaming_employment_observations.csv` is no longer 769

**Ground truth, counted from the file after scripts 158 / 262 / 265:**

| file | value |
|---|---|
| `data/clean/gaming_employment_observations.csv` | **3,246 rows**, 62 columns · `FORM5500_ACTIVE_PARTICIPANTS` 1,975 · `OSHA_TRIBE_LEVEL_REPORTED` 502 · `LODES_BLOCK_WORKPLACE_JOBS` 384 · `OSHA_ESTABLISHMENT_REPORTED` 364 · `PROJECTED` 20 · `ENVIRONMENTAL_REVIEW_COUNT` 1 · entity-linked 3,235 (99.7%) · **239 distinct tribes**, 2008–2026 |
| `data/clean/gaming_facilities.csv` | **787 rows**, 785 keyed, 2 unkeyed |
| `data/clean/gaming_ordinances.csv` | 1,155 rows · blank `tribe_id` **55 → 48** |
| `data/clean/ca_gaming_facilities_official.csv` | 245 rows · blank `tribe_id` **11 → 6** |

**Every document below says 769 and is now superseded.** They are correct about the state
they described and are deliberately NOT edited, per this register's own premise.

- `docs/GAMING_EMPLOYMENT_LOG.md` line 5
- `docs/GAMING_FACILITY_HUB_LINKAGE_2026-08-26.md` lines 42, 420
- `docs/GAMING_SOURCE_AUDIT_2026-08-26.md` lines 67, 171, 333, 488, 536, 712, 736
- `docs/LABOR_SOURCES_FOR_GAMING_2026-08-26.md`, throughout Part I

### THE ONE THAT IS A TRAP: `docs/ASSUMPTIONS_AND_LIMITATIONS.md:1484` says 3,300

It reads *"`gaming_employment_observations.csv` (3,300 rows)"*. **3,300 is the number the
merge was PLANNED to reach and it is the number script 158 printed** — 769 + 2,046 + 485.
The file does not hold it, and the difference is not a defect in the merge:

```
  3,300   after 158
    -71   removed by 262 - Form 5500 rows for COMMERCIAL operators that the
          upstream resolver had attributed to tribes (Hawaiian Gardens Casino
          -> a Native Hawaiian org; Prairie Meadows, Iowa -> Prairie Band
          Potawatomi; Gaming Entertainment (Delaware) LLC -> the Delaware
          Nation). Moved to review/, not deleted.
    +17   added by 265 - OSHA rows that attached once script 172 keyed the
          Barona / San Manuel / Yaamava hub rows, plus Plateau Travel Plaza
  = 3,246
```

**3,300 is a planned figure that was written down before the file was measured**, which is
the exact failure mode `START_HERE.md` records for the SAM `emailId` line: *"written from
an intention, not from a run."* A number that appears in a doc and was never counted from
the file is the most dangerous kind here, because it matches the build log exactly.

**Also superseded by the same work:** 262 additionally re-keyed **133** Form 5500 rows that
carried the WRONG tribe (not a blank) — so any per-tribe cut of this table taken between
the 158 merge and the 262 repair is wrong for 204 of 2,046 rows, 10.0% of the layer.

---

## ADDED 2026-08-26 by `code/301_source_freshness_probe.py` — three freshness-related contradictions

Measured by a streaming pass over the clean tables; re-derive with
`py -3 code/301_source_freshness_probe.py`, output in `docs/SOURCE_FRESHNESS.json`.

### 1. `federal_funding_transactions.csv` is **701,955 rows**, not 684,923

The "Ground truth, measured 2026-08-26" table above says **684,923**, and so does the
dataset table in `START_HERE.md`. Both were true earlier on 2026-08-26 and are no longer.
`data/raw/usaspending_archive_2026-08-07/_append_summary.json` records the change
explicitly — `rows_before: 684923`, `rows_added: 17032`, `rows_after: 701955`, with
684,426 duplicates skipped — and the file's `fetched_date` maximum is **2026-08-26**.

**This is the register's own failure mode happening inside the register**: a number
counted from the file in the morning and superseded by an append in the evening. It is not
an error in either document; it is what a ground-truth table costs when the file underneath
it is live. **Any ground-truth row must carry the time of day it was counted, not just the
date**, on any day a puller is running.

*Nuance that matters more than the count:* the file now carries **two archive vintages at
once** — `source_archive_stamp` = `20260706` on 131,495 rows and `20260806` on 93,536.
No single `vintage` string describes it. See `docs/REFRESH_CADENCE.md` Part 4.

### 2. The Connecticut gaming series is **747** facility-months, not 748

The standing figure is 748 casino-months, 1993-01 → 2025-12. Counted from
`data/clean/gaming_facility_metrics.csv` filtered to `source = "CT Dept of Consumer
Protection / data.ct.gov"`: **3,240 rows, 747 distinct (facility, month) pairs** —
Foxwoods Resort Casino **396** + Mohegan Sun **351**. Both series have **zero missing
months** across their spans, so the discrepancy is not a gap; 748 is simply off by one.
Harmless to any conclusion, recorded so nobody re-derives it.

### 3. `ferc_docket_filings.csv` — the register's own row is superseded

The ground-truth table above reads **81,805 rows · 127 dockets · `ADVOCACY` 18,310 +
`GOVERNMENT_ENGAGEMENT` 228**. `START_HERE.md` records the 2026-08-26 completion run that
supersedes it: **102,615 rows · 307 of 307 dockets · `ADVOCACY` 22,540 +
`GOVERNMENT_ENGAGEMENT` 278 = 22,818**. Measured today: **102,615 rows**, newest
`filed_date` **2026-08-26**. The `is_lobbying = 0 on every row` warning still stands
against the new numbers.

---

## ADDED 2026-08-26, evening — after the Federal Register / NAGPRA / CT refresh

### 4. `federal_actions.csv` is **156,772** rows and NAGPRA is **6,772** notices

Both moved after this register was written. Every document quoting **156,452** FR
documents or **6,729** NAGPRA notices is describing the state before
2026-08-26 ~23:54Z — that includes `docs/FEDERAL_ACTIONS_BUILD_LOG_2026-08-05.md`
(header table), `docs/NAGPRA_BUILD_LOG.md` (provenance section),
`code/77_build_nagpra_dataset.py`'s own docstring, and
`code/130_build_section_106_consultation.py:47`.

| file | before | **now** | newest date |
|---|---:|---:|---|
| `data/clean/federal_actions_raw.csv` | 156,452 | **156,772** | 2026-08-26 |
| `data/clean/federal_actions.csv` | 156,452 | **156,772** | 2026-08-26 |
| `data/clean/nagpra_notices.csv` | 6,729 | **6,772** | 2026-08-24 |
| `data/clean/nagpra_notice_entity_bridge.csv` | — | **51,521** | 2026-08-24 |

Provenance and the before/after measurement: `docs/REFRESH_CADENCE.md` PART 5.

**And a live one, in the same shape as A1.** `fr_content_classification.csv`
still holds **156,452** rows. That is *not* a contradiction to correct — it is a
derived table that has not been rebuilt since its parent grew, and rebuilding it
runs `78_content_analysis.py`, which also rewrites five lobbying tables. Correct
reading: the parent is 156,772; the derived table is one refresh behind and
says so.

### 5. The CT "748 vs 747" discrepancy is SETTLED, and neither number was wrong

Item 2 above records the standing 748 casino-months against 747 counted in the
file, and calls it "off by one … harmless". Measured live at the source on
2026-08-26 (`code/343_refresh_ct_gaming_monthly.py`, two bounded requests):

```
$select=count(1)  -> 748 rows reported by data.ct.gov i6ts-ib7c
$limit=50000      -> 748 rows retrieved
of which casino = "Mohegan Sun Prior Period Adj."   1
```

**748 is the SOURCE's row count; 747 is the count of casino-months.** The
difference is the single `Mohegan Sun Prior Period Adj.` row, which is an
accounting adjustment rather than a month of operations and is excluded by
design (and named in the log) by `159_extend_gaming_metrics.py`. Both figures
are correct about different things. Say which.

### 6. CT gaming's 238-day gap is the SOURCE's, not ours

`docs/REFRESH_CADENCE.md` §3.1 called it *"currently 8 months behind; this is
the cheapest win in the file."* Measured at the endpoint the same day: the
series stops at **2025-12-31** and Cedar holds every casino-month it serves.
There is nothing to pull. Corrected in place in that document and written up in
its PART 5 §5.3.
