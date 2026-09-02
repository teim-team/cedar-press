# Federal Funding (Dataset 3) — Merge Log

*2026-08-05. Built by `code/24_funding_merge.py`. Log: `logs/24_funding_merge_2026-08-05.log`.*
*Every figure below is computed from a streaming read of the named files. Nothing is estimated, tuned, or carried from memory.*

Merge rules: `docs/FEDERAL_FUNDING_RECONCILIATION_2026-08-05.md` (MR-1 … MR-8).

---

## 1. Regression test (MR-3)

The attributed lower-48 subset — reconstructed from the published flags alone (`ak_flag==0 & excluded_flag==0 & attributed_flag==1`), not from an internal survivor mask — must reproduce the hand-checked `fed_funding_data_clean_corrtd.dta`.

| | rows | obligations |
|---|---:|---:|
| target (`_corrtd` .dta) | 364,095 | 107,047,741,074.94 |
| **actual, single precision** (as the .dta stores it) | **364,095** | **107,047,741,074.94** |
| delta | **+0** | **+0.00** |
| actual, double precision (exact decimals from the source CSV) | 364,095 | 107,047,741,120.07 |
| delta | +0 | +45.13 |

**VERDICT: PASS**

**The row count is exact.** The dollar figure is reported twice because `federal_action_obligation` is stored as a Stata `float` — single precision — in `fed_funding_data_clean_corrtd.dta`. That is visible in the .dta's own profile, where cell totals land on dyadic rationals such as `7,627,905.203125` and `43,274,232.57763672`. Rounding each of the 364,095 obligations to single precision and summing reproduces the target **to the cent** (+0.00). Summing the exact decimal strings from the source CSV in double precision gives 107,047,741,120.07, +45.13 — a relative difference of 4.22e-10, which is single-precision representation error and nothing else. The double-precision figure is the more accurate one and is what the shipped files carry; the single-precision figure is what proves the rebuild matches the hand-checked file transaction for transaction.

Independent cross-check: rows still alive at the end of the Stata replay = 364,095 / $107,047,741,120. This is the survivor set the do-file itself would have produced, and it agrees with the flag-reconstructed subset above by construction (a row is alive iff it is non-AK, non-excluded and attributed).

Second independent cross-check, against the tribe×year profile read out of the authoritative `.dta` (`lineageA_dta_corrtd_tribe_year.csv`): 5,496 rebuilt cells vs 5,496 truth cells, **0 value mismatches**, 0 cells only in the truth file, 0 only in the rebuild.

---

## 2. Row accounting — nothing was dropped

| | rows |
|---|---:|
| spine rows read from the raw file | 476,924 |
| rows written to `federal_funding_transactions.csv` | 476,924 |
| rows lost | **0** |
| distinct `assistance_transaction_unique_key` | 476,924 |
| duplicate transaction keys | 0 |

MR-1 holds: the transaction key is 1:1 on the spine, so **there is no deduplication step in this dataset**.

The three Lineage-A deletions are now flags on retained rows:

| flag | meaning | rows=1 | rows=0 |
|---|---|---:|---:|
| `ak_flag` | `drop if recipient_state_code=="AK"` (do-file line 9), a scope exclusion applied before any tribe matching | 55,443 | 421,481 |
| `excluded_flag` | matched a named exclusion ruling (`replace flag=1` → `drop if flag==1`, the exact/prefix/regex `drop if Tribe…` block, or the `university of` dummy drop) | 53,191 | 423,733 |
| `attributed_flag` | a `tribe_id` was assigned by the do-file before the row was excluded | 365,535 | 111,389 |

Confidence tiers (Cedar A/B/C/X):

| tier | rows | obligations | meaning |
|---|---:|---:|---|
| A | 364,095 | $107,047,741,120 | attributed lower-48, hand-checked by the analyst — publishable |
| B | 0 | $0 | algorithmic — none in this dataset; no automated attribution was used |
| C | 59,638 | $21,084,404,779 | unattributed or Alaska — discovery pool, never publishes |
| X | 53,191 | $12,305,753,249 | matches an exclusion ruling — never publishes |

Total retained obligations across every flag state: $140,437,899,149 — the raw file's own total. The $33,390,158,029 that Lineage A deleted is **retained and flagged here**, not discarded.

Tier C splits cleanly, and the split is itself a validation:

| | rows |
|---|---:|
| Alaska (`ak_flag=1`) | 55,443 |
| lower-48, reached the end of the do-file with no `tribe_id` | 4,195 |

The reconciliation reports 55,443 Alaska rows, and the do-file's own line 2460 — `count if tribe_id==.` — carries the analyst's recorded answer in the very next line: **4,195**. This rebuild reproduces both figures independently (55,443 and 4,195), which is a third check on the replay that does not go through the .dta at all.

Note also `attributed_flag=1` (365,535) exceeds tier A (364,095) by 1,440. Those are rows the do-file assigned to a tribe and *then* excluded by a later named ruling. They are retained with `excluded_flag=1`, so the exclusion and the tribe it was excluded from are both visible — exactly the jurisprudence Cedar wants to keep.

---

## 3. Year coverage (MR-6)

Action dates in the spine run **2007-10-01 → 2023-04-05**.

| FY | retained rows | retained obligations | attributed rows | attributed obligations | status |
|---:|---:|---:|---:|---:|---|
| 2008 | 14,157 | $2,045,446,723 | 10,192 | $1,479,165,051 | complete |
| 2009 | 23,827 | $5,317,824,769 | 18,176 | $3,938,894,154 | complete |
| 2010 | 23,558 | $3,912,585,387 | 16,720 | $2,679,428,159 | complete |
| 2011 | 22,211 | $3,345,630,897 | 15,784 | $2,398,530,246 | complete |
| 2012 | 18,141 | $3,505,370,584 | 13,275 | $2,408,290,636 | complete |
| 2013 | 26,927 | $5,146,101,115 | 20,371 | $3,805,748,948 | complete |
| 2014 | 29,913 | $5,689,217,970 | 23,102 | $4,198,459,436 | complete |
| 2015 | 28,105 | $5,798,982,012 | 22,020 | $4,333,694,396 | complete |
| 2016 | 33,701 | $6,564,905,337 | 24,328 | $4,687,693,668 | complete |
| 2017 | 32,756 | $7,335,920,131 | 26,537 | $5,114,757,103 | complete |
| 2018 | 39,432 | $7,986,701,702 | 30,743 | $5,911,072,821 | complete |
| 2019 | 37,880 | $9,431,696,632 | 29,409 | $6,445,422,236 | complete |
| 2020 | 43,274 | $18,084,111,227 | 33,605 | $14,800,066,317 | complete |
| 2021 | 43,604 | $38,233,357,624 | 33,256 | $31,508,876,540 | complete |
| 2022 | 44,297 | $12,046,976,890 | 34,509 | $9,002,387,439 | complete |
| 2023 | 15,141 | $5,993,070,148 | 12,068 | $4,335,253,969 | **PARTIAL — through 2023-04-05** |

### FY2023 caveat — state this wherever the data is published

**The source pull ends 2023-04-05.** FY2008–FY2022 are complete fiscal years. **FY2023 is partial**: it covers 2022-10-01 → 2023-04-05 only, roughly the first half of the fiscal year. Every FY2023 row carries `fy_partial_flag=1` in both deliverables. **FY2023-04-06 onward, and FY2024–FY2025 entirely, require a fresh USAspending assistance download on the same filter**, appended on `assistance_transaction_unique_key`. Per MR-6 the Lineage-B `usaspending_bulk_fy2023_2025` file is *not* an acceptable substitute: it is award-grain on `first_seen_year`, it overlaps FY2023 with this file without a reliable key, and it passed through the max-keeping dedup that MR-7 prohibits.

### FY2000–FY2007 — the other end of the gap

Against the Cedar temporal floor of 2000, this dataset starts eight years late: the earliest action date in the source pull is 2007-10-01, so **FY2000–FY2007 are absent entirely**, not empty. No `pre_2000_flag` is emitted because there are no pre-2000 rows to flag. Closing that end also requires a fresh USAspending assistance pull; note that USAspending's assistance coverage is itself thin before FY2008, so the gap may prove partly unclosable at source. Nothing here estimates or backfills it.

Note the corollary already recorded in `STATE_OF_BUILD.md`: federal funding does **not** thin after 2022. That finding was an artifact of `first_seen_year`. This panel is indexed on `action_date_fiscal_year` — a true fiscal year — and `first_seen_year` appears nowhere in the build.

---

## 4. Deliverables

| file | grain | rows |
|---|---|---:|
| `data/clean/federal_funding_transactions.csv` | transaction (`assistance_transaction_unique_key`) | 476,924 |
| `data/clean/federal_funding_tribe_year_panel.csv` | tribe × true fiscal year, attributed lower-48 only | 5,496 |
| `review/funding_tribe_candidates_2026-08-05.csv` | recipient UEI, MR-4 candidate queue | 975 |

### MR-4 — candidates only

`tribe_id` in both deliverables is Lineage A's own integer scheme (`tribe_id_scheme = lineageA_dofile_integer`), which is local to the do-file. `tribe_id_neid` is **deliberately empty**: the NEID crosswalk is a ruling, not a computation. Lineage B and the Cedar ledger supply *candidates*, routed to the queue for Elijah:

| candidate source | UEIs |
|---|---:|
| cedar_ledger | 644 |
| no_candidate_found | 266 |
| spine_exact_name_on_lineageA_tribe | 65 |

**`cluster_v3` is never auto-accepted** — Elijah's rulings have run 9-for-0 against automated name matching. Lineage B contributes zero dollars to Dataset 3.

---

## 5. What this build did not do

- **No deduplication.** MR-1/MR-7. The transaction key is already 1:1. The prohibited operator — collapse on `(award_id, uei, family)` keeping the max-$ row — discarded ~$60.6B of unequal-value rows in the prior pipeline, 83.7% of which were distinct fiscal-year slices of live awards. That prohibition is written into the script header where a future maintainer will hit it.
- **No Lineage B dollars.** Not one. B's assistance layer is this same raw file filtered to non-blank `recipient_uei`; it can only lose $3,018,812,188 across 31,699 transactions, never add.
- **No Alaska import.** MR-5. The 55,443 Alaska rows are retained here from Lineage A's own spine with `ak_flag=1`, awaiting attribution against the Cedar ANC / AK-village spine. They were never attributed by the do-file because line 9 removed them before matching, so they carry `attribution_method = not_evaluated:ak_scope_line9`.
- **No forward-year fill.** MR-6.

---

## 6. Method — how the rulings were replayed (MR-2)

`fed_funding_do_file_corrtd.do` was parsed into **1836 executable statements** and replayed in source-line order by a closed-grammar interpreter that reproduces Stata's semantics exactly, including the one that matters most: **a row removed by an earlier `drop` is invisible to every later statement**. Later rulings override earlier ones, as `replace` does.

The grammar is small and fully enumerated — the parser raises on anything it does not recognize, so a silent mis-parse is not possible:

| form | count |
|---|---:|
| `set_tribe` | 915 |
| `drop` | 851 |
| `set_flag` | 68 |
| `noop_tribe_subinstr` | 1 |
| `gen_dummy` | 1 |

Every condition reads only `Tribe`, `recipient_city_name`, `recipient_state_code` and the derived `tribe_id`/`flag`/`dummy`, so the program is a pure function of that triple. It was therefore evaluated once per **distinct** triple (9,659 of them) rather than once per transaction (476,924) — identical result, two orders of magnitude less work.

`Tribe` is reconstructed as `strlower(recipient_name)` with every `"` removed, matching the do-file's line-13 `subinstr(Tribe, `"""', "", .)`, which exists because the import used `bindquote(strict) stripquote(no)` and so kept the literal quote characters around quoted fields.

City/state disambiguation is preserved verbatim, including the Delaware Nation vs Delaware Tribe split on `recipient_city_name` (`CADDO-WICHITA-DELAWAR` / `ANADARKO` / `BARTLESVILLE` / `CHELSEA`).

### Finding: the `_corrtd` do-file does not reproduce the `_corrtd` .dta

This surfaced from the regression test and is worth recording.

The Oneida correction renumbered the block but left it incomplete in two places:

- **line 696** — the Wisconsin catch-all `replace tribe_id=205 if strpos(Tribe, "oneida")==1` still sits *after* the two New York rulings at **lines 684–685**. Executed literally it swallows every New York row: all $1.06B of Oneida money lands on 205 and 204 keeps one row.
- **line 1516** — `replace tribe_id=204 if Tribe=="onsin oneida tribe of wisc"` is a stale 204 that was correct when 204 meant Wisconsin. Anna's own corrected **line 686** rules that same entity to 205; line 1516 then pulls it back. The .dta keeps it on 205, and the name says "wisc".

The authoritative `.dta` does not look like that. It carries **332 rows / $173,967,756.72 on 204** and **$890,113,321.44 on 205**, and it leaves `onsin oneida tribe of wisc` on 205. That is exactly what running the *original* do-file produces — where the WI block comes first and the NY block last — followed by swapping the two id labels. Which is precisely how the reconciliation describes the correction: it *"reassigns $716,145,565 from the Wisconsin Oneida to the New York Oneida ID slot and back."* **The `_corrtd` .dta was produced by a label swap on the original run, not by re-executing the reordered file.**

To reproduce the .dta — and to honour MR-2's explicit instruction that **204 = NY, 205 = WI** — this build re-applies three of Anna's own rulings verbatim, at the end of the sequence, immediately before `drop if tribe_id==.`: **686** (205 for `onsin oneida tribe of wisc`), **684** (204 for `oneida nation` in NY) and **685** (204 for `oneida indian nation`). No ruling was invented and no threshold was tuned — each injected statement is a line of the corrected do-file, replayed at the execution position the .dta demonstrates it had. Every row touched carries its originating line in `attribution_source_line` and an `MR-2 Oneida 204=NY` marker in `attribution_method`, so the step is auditable in the shipped data.

Consequence for anyone re-running the source: **do not expect `fed_funding_do_file_corrtd.do` to rebuild `fed_funding_data_clean_corrtd.dta` unaided.** It will put the entire Oneida total on 205. The .dta is the authority; the do-file needs line 696 moved above line 684, and line 1516 changed to 205, to agree with it. Nothing was written back to the do-file — it is Anna's source and this build only reads it.

Each retained row carries `attribution_source_line` and `attribution_rule` (the literal Stata statement that assigned it), and each excluded row carries `exclusion_source_line`, `exclusion_rule` and the analyst's own `exclusion_reason` where the do-file recorded one. The attribution is auditable back to the line of hand-checked work that produced it.

---

## 7. Still open for Elijah

1. **NEID crosswalk** — `review/funding_tribe_candidates_2026-08-05.csv`, 975 rows. Until ruled, `tribe_id_neid` stays empty and Dataset 3 cannot join the rest of the Cedar spine.
2. **Alaska** — 55,443 retained rows are unattributed by construction. MR-5 restoration needs an attribution pass against the ANC / AK-village spine.
3. **BIA-operated schools** — the do-file's own header declares the defect: 58 Bureau-Operated schools are currently *kept* and the analyst wrote that they should be dropped. Unresolved; nothing was changed here.
4. **The three self-declared coin-flips** — `zuni housing authority` dropped "unsure … but I'll drop it" while `turtle mountain public utilities comm` is kept on the same doubt; `tohono o' odham community action` excluded while the farming authority is kept; `laguna de santa rosa foundation` excluded while `laguna rainbow corp` is kept.
5. **State-recognized tribes** — dropped wholesale by Lineage A (retained here with `excluded_flag=1`), carried as 25 `TRBS` ids by Lineage B. Cedar needs one policy.
6. **~120 "X is missing data" notes** — tribes the analyst flagged as having no observed assistance. Genuine zeros or a name-matching miss?

