# Federal Funding (Dataset 3) — Lineage Reconciliation
*2026-08-05. Reconciliation and documentation only. No merged panel was produced. Every figure below was read out of the files named; nothing is estimated, averaged, or carried over from memory.*

Build log: `logs/16_federal_funding_recon_2026-08-05.log`
Scripts: `code/16_federal_funding_recon.py`, `code/16_profile_fedfunding_dta.do`, `code/16b_extract_funding_rulings.py`, `code/16c_copy_funding_inputs.py`
Rulings ledger: `data/spine/federal_funding_rulings_from_dofile.csv`
Year table (machine-readable): `data/clean/federal_funding_year_comparison_2026-08-05.csv`
Inputs + manifest: `data/raw/external/federal_funding/_SOURCE_MANIFEST_federal_funding.csv`

---

## 0. The finding that reframes the whole exercise

**The two lineages are not two datasets. They are two treatments of one file.**

`Assistance_PrimeTransactions_2023-04-09_H19M53S53_1.csv` exists in both trees:

| copy | bytes | md5 |
|---|---|---|
| `Cedar Press/Federal Spending/raw/…` | 631,463,188 | `5414c27e9620fc90c8c3b0f1c9204e64` |
| `dissertation/data/federalspending/raw/…` | 631,463,188 | `5414c27e9620fc90c8c3b0f1c9204e64` |

Byte-identical. Lineage B's own build script (`build_research_ready_panel.py` line 37, `integrate_grants_to_panel.py` line 24) reads that exact path and tags the result `usaspending_assistance_2008_2023` / `usaspending_assistance_2009_2023Q1`.

So there is no independent second source of assistance dollars to reconcile against. The question is not "which pull is right" but **"which processing of the one pull is right"** — and on that question the answer is measurable rather than a matter of taste (§4, §5).

---

## 1. Universe of each lineage

### Lineage A — hand-checked (`Cedar Press/Federal Spending/`)
Authored by Anna Malinovskaya (the `import delimited` path in both do-files is `C:\Users\Anna Malinovskaya\Desktop\...`). Two do-file vintages, 2,466 and 2,467 lines.

| | raw CSV | clean `.dta` (corrtd) |
|---|---|---|
| rows | 476,924 transactions | 364,095 transactions |
| obligations (`federal_action_obligation`) | $140,437,899,149 | $107,047,741,075 |
| action_date range | 2007-10-01 → 2023-04-05 | same window |
| fiscal years | FY2008 – FY2023 (FY2023 partial, through 2023-04-05) | FY2008 – FY2023 |
| distinct `recipient_uei` | 5,458 | 975 |
| distinct `recipient_duns` | 6,364 | 1,303 |
| distinct `recipient_name` | 7,221 | 1,688 |
| distinct `award_id_fain` | 128,071 | — |
| distinct transaction keys | 476,924 (**zero duplicates**) | — |
| tribes | n/a | **359 `tribe_id`s** |
| geography | all states incl. AK (55,443 AK rows) | **41 states + `00`; Alaska entirely absent** |

Assistance types present in **both** the raw file and the clean panel — identical set, no loans anywhere:

| code | description | raw rows | raw $ |
|---|---|---|---|
| 02 | Block grant | 71,028 | $11,857,007,331 |
| 03 | Formula grant | 68,643 | $9,200,844,323 |
| 04 | Project grant | 112,915 | $23,175,546,709 |
| 05 | Cooperative agreement | 19,096 | $3,641,483,486 |
| 06 | Direct payment for specified use | 188,824 | $89,222,907,945 |
| 10 | Direct payment, unrestricted use | 10,084 | $1,259,641,999 |
| 11 | Other reimbursable / indirect assistance | 6,334 | $2,080,467,356 |

`total_face_value_of_loan` sums to **$0.00** across all 476,924 rows. **There are no loans in Lineage A**, and no assistance type 07/08 rows exist.

The raw pull is already Native-filtered at source (USAspending recipient business type): 238,430 + 172,153 rows "Indian/Native American tribal government (federally recognized)", 40,613 "tribal designated organization", 2,570 "other than federally-recognized", 23,158 blank.

**`_corrtd` vs original — resolved exactly.** Both files have 364,095 rows and the *same* $107,047,741,075 total. Exactly two `tribe_id`s differ, and they differ by a swap:

| tribe_id | example name | original | corrected | delta |
|---|---|---|---|---|
| 204 | oneida indian nation (NY) | $890,113,321 | $173,967,757 | −$716,145,565 |
| 205 | oneida nation (WI) | $173,967,757 | $890,113,321 | +$716,145,565 |

The correction reassigns $716,145,565 from the Wisconsin Oneida to the New York Oneida ID slot and back. **`_corrtd` is the version to use**; nothing else changed.

### Lineage B — automated expansion (`dissertation/data/tribal_federal_spending/clean/`)

`award_level_panel_research_ready_deduped.csv`: 645,149 rows, $557,987,076,891, 17,060 UEIs, **618 `tribe_id`s**, keyed `(award_id, uei, award_type_family)`, year field = **`first_seen_year`** (not a fiscal year).

Three sources, only one of which is assistance:

| data_source | rows |
|---|---|
| `master_prime_2000_2022` | 391,734 |
| `usaspending_bulk_fy2023_2025` | 143,844 |
| `usaspending_assistance_2008_2023` | 109,571 |

Entity universe is much broader than A — it is a *contracting* universe with assistance folded in:

| prefix | tribe_ids |
|---|---|
| TRBF (federally recognized tribe) | 341 |
| AKNF (AK Native village) | 221 |
| TRBS (state-recognized) | 25 |
| ANRC (AK regional corp) | 11 |
| CNSF / CNSS (consortia) | 10 |
| SGVF | 8 |
| NHO | 2 |

Attribution quality: 324,554 rows `unmatched`, 190,907 `cluster_v3` (algorithmic), 79,344 `hand`, 25,447 `subsidiary_lookup`, 8,274 `web_verified`. Unmatched rows include plainly non-Native recipients (Duke University, Paragon Systems Inc.) — the panel is a *pull*, not a curated universe.

**Assistance types in B**: families `grants`, `direct_pay`, `other_assist` carry dollars; `idvs` and `contracts` are the contracting side; the `loans` column exists in `tribe_year_research_ready_wide_deduped.csv` and is **$0.00 in every one of the 10,451 rows** — a schema placeholder, not data. B therefore covers the same assistance types as A (grants / direct payments / other), plus contracts and IDVs which are Dataset 2, not Dataset 3.

---

## 2. Year-by-year dollars

All figures FY, USD. `A_raw` = every recipient in the shared raw file. `A_clean` = lineage A after Alaska drop, exclusions and tribe attribution. `B_assist(shared file)` = lineage B's assistance dollars traced to the same raw file. `B_assist(bulk)` = lineage B's FY2023–25 bulk pull. `B_wide` = the shipped `tribe_year_research_ready_wide_deduped.csv`, which is indexed by `first_seen_year`.

| FY | A_raw (all) | A_clean (lower-48, attributed) | B_assist (shared file) | B_assist (bulk 23–25) | B_wide (first_seen) | B_wide tribe-rows |
|---:|---:|---:|---:|---:|---:|---:|
| 2000–2007 | 0 | 0 | 0 | 0 | 0 | 56–219 (contracts only) |
| 2008 | 2,045,446,723 | 1,479,165,049 | 1,518,788,337 | 0 | 2,087,668,847 | 520 |
| 2009 | 5,317,824,769 | 3,938,894,152 | 3,766,949,507 | 0 | 13,348,774,295 | 497 |
| 2010 | 3,912,585,387 | 2,679,428,163 | 3,594,615,642 | 0 | 1,821,127,550 | 508 |
| 2011 | 3,345,630,897 | 2,398,530,243 | 3,211,944,550 | 0 | 5,318,509,470 | 482 |
| 2012 | 3,505,370,584 | 2,408,290,639 | 3,398,034,305 | 0 | 1,101,729,425 | 480 |
| 2013 | 5,146,101,115 | 3,805,748,948 | 5,072,322,715 | 0 | 4,953,228,547 | 528 |
| 2014 | 5,689,217,970 | 4,198,459,436 | 5,604,356,150 | 0 | 3,394,469,332 | 511 |
| 2015 | 5,798,982,012 | 4,333,694,399 | 5,755,792,772 | 0 | 3,767,170,650 | 511 |
| 2016 | 6,564,905,337 | 4,687,693,668 | 6,534,725,161 | 0 | 4,808,243,708 | 533 |
| 2017 | 7,335,920,131 | 5,114,757,100 | 7,315,874,874 | 0 | 3,878,558,605 | 518 |
| 2018 | 7,986,701,702 | 5,911,072,817 | 7,964,441,457 | 0 | 4,550,742,965 | 531 |
| 2019 | 9,431,696,632 | 6,445,422,233 | 9,401,525,536 | 0 | 5,564,935,219 | 548 |
| 2020 | 18,084,111,227 | 14,800,066,334 | 18,058,623,107 | 0 | 11,578,960,997 | 591 |
| 2021 | 38,233,357,624 | 31,508,876,502 | 38,208,981,206 | 0 | 22,797,439,245 | 597 |
| 2022 | 12,046,976,890 | 9,002,387,429 | 12,019,041,494 | 0 | 4,719,668,853 | 592 |
| 2023 | 5,993,070,148 | 4,335,253,962 | 5,993,070,148 | 47,320,480,734 | 41,200,701,320 | 409 |
| 2024 | 0 | 0 | 0 | 62,244,260,195 | 20,747,168,865 | 539 |
| 2025 | 0 | 0 | 0 | 59,823,140,923 | 4,436,998,079 | 465 |
| **Total** | **140,437,899,149** | **107,047,741,075** | **137,419,086,960** | **169,387,881,852** | **160,076,095,974** | |

### Where they agree
Columns `A_raw` and `B_assist (shared file)` agree **to the dollar, every year**, once one adjustment is made. Splitting `A_raw` by whether the transaction carries a `recipient_uei`:

| FY | A_raw rows WITH uei | A_raw rows WITHOUT uei | no-uei rows |
|---:|---:|---:|---:|
| 2008 | 1,518,788,337 | 526,658,386 | 3,185 |
| 2009 | 3,766,949,507 | 1,550,875,262 | 7,113 |
| 2010 | 3,594,615,642 | 317,969,745 | 3,455 |
| … | … | … | … |
| 2022 | 12,019,041,494 | 27,935,397 | 550 |
| 2023 | 5,993,070,148 | 0 | 0 |
| **Total** | **137,419,086,960** | **3,018,812,188** | **31,699** |

The "with uei" column **is** `B_assist (shared file)`, exactly, in all sixteen years. So:

> **Lineage B's assistance layer = Lineage A's raw file restricted to rows with a non-blank `recipient_uei`. It drops $3,018,812,188 across 31,699 transactions because its pipeline is UEI-keyed.** Of that, **$2,413,003,547 over 17,505 transactions survives Lineage A's own attribution**, i.e. is real, tribe-attributed money that Lineage B structurally cannot represent.

### Where they diverge
1. **Alaska.** Line 9 of both do-files is `drop if recipient_state_code=="AK"`, executed before any tribe matching. 55,443 raw AK rows never enter Lineage A. Lineage B carries 221 AK village + 11 ANRC tribe_ids.
2. **Attribution loss.** A_clean runs 68.3% (FY2019) to 82.4% (FY2021) of A_raw, never higher; the gap is Alaska plus 4,195 unattributable recipients that line 2463 `drop if tribe_id==.` removes outright.
3. **FY2023–2025.** A ends 2023-04-05. B's FY2023–25 dollars come entirely from a different pull (`usaspending_bulk_fy2023_2025`).
4. **FY2023 is double-covered in B.** B holds both the partial-year assistance file ($5,993,070,148, Oct 2022–Apr 2023) *and* a full-FY2023 bulk pull ($47,320,480,734) in the same year cell. The award-level dedup only catches matching `award_id`s, so any FY2023 assistance award whose id differs between the two pulls is counted twice.
5. **`B_wide` is not a fiscal-year series at all.** It is indexed by `first_seen_year`, so a multi-year award's entire lifetime obligation lands in the year it first appeared. Compare 2009 ($13.35B in B_wide vs $3.77B on a true FY basis) or 2012 ($1.10B vs $3.40B). The only Lineage B file carrying a true `fiscal_year` is `master_tribal_spending_panel.csv` — which is a **pre-dedup vintage** (built 09:43 on 2026-05-01; the dedup ran at 16:07 the same day). Lineage B has no file that is both deduped and fiscal-year-accurate.

### The coverage-thinning claim — confirmed, and explained
592 tribe-rows in 2022 → **409** in 2023 → **539** in 2024 → **465** in 2025: confirmed exactly in `tribe_year_research_ready_wide_deduped.csv`.

It is an artifact of `first_seen_year`, not of coverage. On a true fiscal-year basis the same underlying data gives 598 / 535 / 554 / 550 tribes for 2022–2025 — a mild, monotone-ish decline consistent with a partial FY2025, not a 31% cliff and rebound. A tribe drops out of the `B_wide` 2023 row simply because none of its awards were *first seen* in 2023; the tribe is still receiving money on awards first seen earlier.

---

## 3. The $67B overcount claim

**Arithmetically substantiated. Substantively not.**

Verified from the files: pre-dedup `award_level_panel_research_ready.csv` = 678,258 rows / **$625,239,738,743**. Deduped = 645,149 rows / **$557,987,076,891**. Difference = **$67,252,661,852**, matching the $67,252,661,853 in `_dropped_rows.csv` (33,109 rows) to $1 of float rounding. `CHANGELOG.md` line 15 and `RESEARCH_READY_DATA_DICTIONARY.md` line 13 describe this as "~$67B over-count … mostly bulk fy2023-2025 re-reporting awards already in master_prime".

The dedup rule is: group on `(award_id, uei, award_type_family)`, **keep the single largest-$ row, delete the rest**. Decomposing the $67.25B by what the deleted rows actually are:

| category | rows dropped | $ dropped | share |
|---|---:|---:|---:|
| A. same source, **distinct fiscal-year slices** of one award | 10,199 | 3,880,481,105 | 5.8% |
| B. same source, same year | 456 | 145,400,232 | 0.2% |
| C. cross-source, **exact $ match** (true re-report) | 6,295 | 6,583,322,777 | **9.8%** |
| D. cross-source, **different year windows, unequal $** | 15,642 | 56,267,946,786 | **83.7%** |
| E. cross-source, same year, unequal $ | 517 | 375,510,952 | 0.6% |
| **total** | **33,109** | **67,252,661,853** | |

Only **9.8% ($6.58B)** of the removal is a demonstrable duplicate — two sources reporting the identical dollar figure for the identical award. **83.7% ($56.27B)** is the same award seen through two different observation windows at two different cumulative amounts; deleting the smaller one is a guess, not a dedup.

Two supporting checks contradict the documentation:
- The dedup script's own docstring asserts "median bulk/master_prime $-ratio for the cross-source overlap = 1.00 (i.e., these are the same awards reported twice, not time-slices)". Recomputed over the 22,432 cross-source duplicate groups, the **median second/first ratio is 0.8687**, the mean is 0.7367, and only **28.3%** are exact. The 1.00 median is not reproducible from these files.
- **21,732 of the 22,432 cross-source groups have differing `first_seen_year` across sources**, and 9,205 of the 9,660 same-source groups do too. These are time-slices. The docstring's stated reason for ruling out time-slices does not hold.

There is a second, smaller problem: award sentinels. $4,505,672,981 of the dropped total sits on award_ids of ≤4 characters (`0000`, `0001`, blank). The script says sentinels are "treated as opaque — we only collapse when uei also matches", but a repeated sentinel id under one UEI is exactly where collapsing is *least* safe. Worked example from the file — `award_id='0001'`, `uei=CCKSXPWFV5V7`: three rows (FY2005 $3,748; FY2006 $1,110,040; FY2006 $1,937). Dedup keeps $1,110,040 and discards the other two as "duplicates".

Also note the pre-dedup diagnostics quoted in the docs ("11,172 within-source duplicates, ~$12.5B") do not reproduce either: on the `(award_id, uei, family)` key there are 9,660 same-source groups accounting for $4.03B.

**Verdict: the $67B was removed, but it is not a $67B overcount. A defensible removal on this evidence is ~$6.6B (category C). The remaining ~$60.6B was discarded on an unproven assumption, and the max-keeping reducer is the wrong operator for time-sliced records.** None of this touches the assistance-only comparison in §2, which is exact — it is a warning about Lineage B generally and about ever reusing this dedup rule.

---

## 4. What each lineage has that the other does not

**Only in Lineage A**
- $3,018,812,188 / 31,699 transactions with no `recipient_uei` (of which $2,413,003,547 is tribe-attributed). Invisible to B by construction.
- **Transaction grain** with a true `action_date` (2007-10-01 → 2023-04-05) and `action_date_fiscal_year`. B is award-grain with `first_seen_year`.
- **DUNS**: 6,364 distinct values. Lineage B carries none; the Cedar identifier ledger carries none.
- CFDA/program, awarding agency and sub-agency, place of performance, recipient address/city/zip, `assistance_type_code`, `business_types_description` — 105 columns. B keeps 14.
- **3,789 auditable per-recipient rulings** (§5) with the analyst's reasoning attached.
- A clean 1:1 transaction key: 476,924 rows, 476,924 distinct `assistance_transaction_unique_key`, **zero duplicates**. No dedup is required at this grain.

**Only in Lineage B**
- **Alaska** — 221 AK village + 11 ANRC tribe_ids that A discards wholesale.
- **FY2023-04-06 → FY2025**, from a separate bulk pull.
- **Contracts and IDVs** — but those are Cedar Dataset 2, not Dataset 3.
- A `tribe_id` scheme (618 ids, NEID-prefixed) that ties to the rest of the Cedar spine, where A's `tribe_id` is a bare 1–381 integer local to the do-file.
- State-recognized tribes, consortia, and 2 NHOs as first-class entities.

---

## 5. Per-recipient rulings recovered from the do-files

`data/spine/federal_funding_rulings_from_dofile.csv` — **3,789 rows** (1,895 from `_corrtd`, 1,894 from the original; the files are otherwise near-identical).

| ruling | identifier_type | rows |
|---|---|---:|
| INCLUDE | recipient_name_prefix | 1,558 |
| INCLUDE | recipient_name_exact | 265 |
| EXCLUDE | recipient_name_exact | 1,792 |
| EXCLUDE | recipient_name_prefix | 92 |
| EXCLUDE | recipient_name_regex | 80 |
| EXCLUDE | recipient_state_code | 2 |

**Identification logic, in execution order:**
1. `drop if recipient_state_code=="AK"` (line 9) — Alaska removed before anything else.
2. `Tribe = strlower(recipient_name)`, quotes stripped; `tribe_id = .`; `flag = 0`.
3. ~912 `replace tribe_id=N if strpos(Tribe,"<prefix>")==1` statements walking tribes 1→381 alphabetically, each followed by a `tab Tribe if tribe_id==N` eyeball check. Disambiguation is done with `recipient_state_code` and `recipient_city_name` conditions (Delaware Nation vs Delaware Tribe via `CADDO-WICHITA-DELAWAR` / `ANADARKO` / `BARTLESVILLE` / `CHELSEA`; Oneida NY vs WI via state; Apache, Shoshone and Chippewa families each get an explicit state cross-tab audit at lines 2408–2445).
4. 68 `replace flag=1 if Tribe=="…"` per-entity exclusions, then `drop if flag==1` (line 1275).
5. A post-1275 block adding tribally controlled schools and enterprises, guided by two cited references (bie.edu school directory; bia.gov tribal-school PDF).
6. ~762 exact-name `drop if Tribe=="…"` plus 92 prefix and 80 substring pattern drops, removing municipal/county housing authorities, BIA and IHS themselves, intertribal organizations, universities and public school districts.
7. An explicit **state-recognized and unrecognized** drop list (line 2400): Haliwa-Saponi, MOWA Choctaw, Lumbee entities, United Houma, Ma-Chis Lower Creek, Pee Dee, Waccamaw Siouan, Nipmuc, Juaneño, Meherrin, Coharie, Fernandeño Tataviam, Brothertown, Tubatulabal, Pointe-au-Chien, Occaneechi, Nor-El-Muk and others; plus "the chickamauga nation" as *federally recognized but not serviced*; plus Burt Lake Band (recognized ~2022–23, post-dating the roster).
8. `drop if tribe_id==.` (line 2463) — 4,195 recipients removed.

**Standing policy stated in the header comment (line 2):** schools and colleges are assigned to a tribe if tribally owned/operated; public schools on reservation are dropped; multi-tribe schools and colleges are dropped. The analyst notes 58 Bureau-Operated and 129 Tribally-Controlled schools and flags that BIA-operated schools **should** be dropped but currently are not — an open, self-declared defect.

**The evidentiary gold — 12 exclusions carrying the analyst's reasoning** (the assistance-side analogue of the `hci_analysis.do` per-UEI drops):

| line | recipient | ruling | analyst's reason |
|---:|---|---|---|
| 21 | agua caliente solar, llc | EXCLUDE | "this enterprise appears to have no connection to the tribe" |
| 157 | chippewa cree const corp / chippewa cree construction corp | EXCLUDE | "rocky boy schools and chippewa cree tribe/health care are not flagged because they are affiliated with the tribe" |
| 377 | upper lake rancheria koi | EXCLUDE | "Koi nation lives on lower lake rancheria" |
| 630 | navajo health foundation-sage memorial hospital | EXCLUDE | "navajo agricultural projects industry (napi) is owned by navajo nation" |
| 791 | acoma number 8 ranch | EXCLUDE | "acoma cattle growers association appears separate from the tribe" |
| 808 | laguna de santa rosa foundation | EXCLUDE | "laguna rainbow corp appears to be a tribe entity" |
| 842 | santa clara cnty housing auth | EXCLUDE | "santa clara day school is owned by the tribe" |
| 1101 | muscogee nation of florida, inc. | EXCLUDE | "they are a state-recognized tribe" |
| 1123 | tohono o' odham community action | EXCLUDE | "tohono o'odham farming authority is tribally owned" |
| 1156 | turtle mountain tribal arts association | EXCLUDE | "I'm unsure about turtle mountain public utilities comm but I'll keep it" |
| 1271 | zuni housing authority | EXCLUDE | "I'm unsure about zuni housing authority but I'll drop it" |
| 2403 | the chickamauga nation | EXCLUDE | "the following tribe is federally recognized but not serviced" |

Plus ~120 INCLUDE rulings carrying notes, mostly of the form "*X Rancheria is missing data but it belongs to the Pit River tribe*" (Likely, Lookout, Roaring Creek, XL Ranch) and "*X is missing data*" (Carson Colony, Dresslerville, Keechi, Koosharem, Tawakonie, California Valley, Cedar Band). These are **coverage gaps the analyst identified by hand** and are worth their own Cedar queue.

Extraction discipline: `evidence_url` is populated **only** where a URL appears in the ruling's own adjacent comment — 0 rows qualify, so the column is empty rather than back-filled from the two section-level reference links. Where the only nearby comment sits on the *preceding* line (which may belong to the prior ruling), the reason is prefixed `[preceding comment, attribution uncertain]`.

---

## 6. Identifier harvest (addendum deliverable)

`data/clean/funding_identifier_harvest.csv` — **37,704 identifier-observation rows**, one per distinct `(uei, ein, duns, recipient_name, state, city, zip)` tuple as observed. Values verbatim; nothing normalized; anomalies carried in `malformed_flag` (1,871 rows `no_identifier`, 7 rows `duns_format`).

| | Lineage A (assistance raw) | Lineage B (award panel) | union |
|---|---:|---:|---:|
| observation rows | 12,710 | 24,994 | 37,704 |
| distinct UEI | 5,458 | 17,060 | 17,060 |
| distinct DUNS | 6,364 | 0 | 6,364 |
| distinct EIN | 0 | 0 | **0** |
| distinct CAGE | 0 | 0 | **0** |

`source_lineage`: 10,886 A-only, 22,043 B-only, 4,775 both (tie made on the `(uei, ein, duns)` triple, since B carries no DUNS/EIN/city/zip and could never tie on the full tuple). All 5,458 Lineage-A UEIs also appear in Lineage B.

**Correction to the addendum's premise:** the USAspending assistance download has **no EIN column and no CAGE column** — 105 fields, none of them a tax ID. Assistance does *not* carry EIN here. EIN and CAGE do exist in a *sibling* dissertation file, `native_entity_enterprise_dataset_v6_geocoded.csv` (1,104 EINs, 4,059 CAGEs on 18,110 rows), but those come from IRS-990 and SAM enrichment, not from the funding data, and pulling them into this harvest would be inference and entity linking. Both columns are therefore emitted empty, per instruction.

### Net new identifiers — the headline
`data/clean/cedar_identifier_ledger_final.csv` (read-only) holds 13,191 UEI, 4,937 CAGE, 1,104 EIN and **no DUNS at all**.

- **4,249 UEIs in the funding data are not in the Cedar identifier ledger.**
- **All 4,249 come from Lineage A**, the hand-checked assistance pull, not from Lineage B.
- **0 of the 4,249 were attributed to any tribe by Lineage B** — every one sits in B's `unmatched` pile.
- Additionally **6,364 DUNS values**, an identifier class the Cedar ledger does not currently hold in any form. **5,407 of them co-occur with a UEI in the same observation, giving a direct pre-2022 DUNS→UEI bridge**; 968 DUNS appear with no UEI at all.

Written out: `data/clean/funding_identifier_netnew_ueis.csv`.

Caveat to carry: these are federal *assistance recipients* flagged Native at source by USAspending business type (tribal government / tribal designated organization). They are not pre-vetted Cedar entities. The 4,249 belong in the reconcile queue, not straight into the spine.

---

## 7. Recommendation and the exact merge rule

### Recommendation
**Ship Lineage A as Cedar Press Dataset 3. Do not ship Lineage B's assistance figures, and do not average or blend the two.** The reasons are evidentiary, not stylistic:
- Lineage B's assistance layer is a strict subset of Lineage A's source (identical file, filtered to non-blank UEI). It cannot add assistance dollars for FY2008–2023Q2; it can only lose $3.02B of them.
- Lineage A is transaction-grain with a true action date. Lineage B's only deduped assistance product is indexed by `first_seen_year` and is not a fiscal-year series; its only true-fiscal-year product is pre-dedup.
- Lineage A's identification is reviewable line by line (3,789 rulings now extracted). Lineage B's is 30% algorithmic clustering with 324,554 unmatched rows.
- Lineage B's headline dedup deleted ~$60.6B on an assumption that does not reproduce from its own files.

But Lineage A alone is **not shippable as-is**: Alaska is gone, coverage stops 2023-04-05, and 4,195 recipients were hard-deleted. So a merge is needed — a **structural** merge (grain, coverage, spine ids), not a dollar merge.

### Proposed merge rule (awaiting approval — nothing has been run)

**MR-1 — Spine.** Dataset 3 = the raw assistance transaction file, all 476,924 rows, keyed on `assistance_transaction_unique_key`. That key is 1:1 already (0 duplicates), so **no deduplication step exists in this dataset**. Fiscal year comes from `action_date_fiscal_year`, never from a first-seen year.

**MR-2 — Attribution as a layer, not a filter.** Replay the `_corrtd` do-file rulings from `data/spine/federal_funding_rulings_from_dofile.csv` in source-line order (later rules overwrite earlier, as Stata does), emitting columns `tribe_id_lineageA`, `ruling_applied`, `ruling_source_line`. Preserve the corrected Oneida assignment (204 = NY, 205 = WI).

**MR-3 — Never drop; flag.** The three lineage-A deletions become flags, not row removals:
- `drop if recipient_state_code=="AK"` → `scope_flag = 'AK_excluded_lineageA'` on 55,443 rows, retained.
- `drop if flag==1` → `exclusion_reason` from the rulings ledger, retained.
- `drop if tribe_id==.` → `attribution_status = 'unattributed'` on the 4,195 recipients, retained.
Published/analysis subset = `attribution_status=='attributed' & scope_flag is null`, which reproduces $107,047,741,075 / 364,095 rows exactly and is the regression test for the build.

**MR-4 — Spine ids from Lineage B, dollars from nowhere but A.** Crosswalk A's integer `tribe_id` 1–381 to Cedar NEID `tribe_id`s using B's 618-id scheme as a *candidate* source only. Every crosswalk row lands in `reconcile_queue.csv` with a `YOUR_RULING` column; no automatic acceptance of `cluster_v3` assignments. B contributes **zero dollars** to Dataset 3.

**MR-5 — Alaska by restoration, not by import.** Alaska is restored from Lineage A's own retained rows (MR-3), attributed against the Cedar ANC/AK-village spine. Do **not** import B's AK dollars: they came from the same file and would arrive filtered to non-blank UEI.

**MR-6 — Forward years by a fresh pull, not from B's bulk file.** FY2023-04-06 → FY2025 requires a new USAspending assistance download on the same filter, appended on the same transaction key. Until it exists, Dataset 3 v1 ships **FY2008–FY2022 complete plus FY2023 explicitly labeled partial (through 2023-04-05)**. B's `usaspending_bulk_fy2023_2025` is not an acceptable substitute: it is award-grain on `first_seen_year`, it overlaps FY2023 with the assistance file without a reliable key, and it passed through the max-keeping dedup.

**MR-7 — Dedup policy, standing.** If a future pull ever needs deduplication, dedup on the exact transaction key. **Never** collapse on `(award_id, uei, family)` keeping the max-$ row: measured against these files that operator discards $60.6B of unequal-value rows, 83.7% of which are distinct fiscal-year slices of a live award.

**MR-8 — Identifiers ship separately and immediately.** `funding_identifier_harvest.csv` does not depend on any of the above and can move now: 4,249 net-new UEIs and 6,364 DUNS (5,407 with a UEI on the same row, forming a pre-2022 bridge) into the reconcile queue for Elijah's rulings, with no entity attribution attached.

### Open items for Elijah
1. The do-file's own declared defect: 58 BIA-operated schools are currently *kept* and the analyst says they should be dropped. Ruling needed.
2. ~120 "X is missing data" notes identify tribes with no observed assistance (Carson Colony, Dresslerville, Keechi, Koosharem, Tawakonie, California Valley, Cedar Band, and the four Pit River rancherias). Genuine zeros, or a name-matching miss?
3. `tohono o' odham community action` is excluded while `tohono o'odham farming authority` is kept; `laguna de santa rosa foundation` excluded while `laguna rainbow corp` kept; `zuni housing authority` dropped with the note "I'm unsure … but I'll drop it" while `turtle mountain public utilities comm` is kept on the same kind of doubt. These three coin-flips are worth confirming before publication.
4. State-recognized tribes are dropped by Lineage A and carried as 25 `TRBS` ids by Lineage B. Cedar needs one policy.
