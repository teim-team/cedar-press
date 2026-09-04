# Fact Check — 2026-08-06

*Adversarial recomputation of every quantitative claim in `docs/handoffs/STATE_OF_BUILD.md`,
`docs/datasets/*.md`, `docs/COVERAGE_AUDIT.md`, `docs/CROSS_DATASET_LEARNING.md` and
`docs/codebooks/README.md`, against `data/clean/` and `data/spine/`.*

> ## ⚠ DO NOT WORK THIS LIST TOP-TO-BOTTOM. Flagged 2026-08-26.
>
> This fact-check was good work and most of it still holds. But it is **twenty days old, and
> a prescribed correction can go stale exactly the way the error it corrects did.** One
> entry on this list will now cause the regression it was written to prevent:
>
> **B-27 is stale and prescribes a wrong value.** It flags `docs/COVERAGE_AUDIT.md` and
> prescribes **exact 617 / absent 80 / bounded 77** for `gaming_facilities.open_date_class`.
> Later same-day sweeps in `docs/GAMING_TEMPORAL_BUILD_LOG.md` moved it to
> **exact 635 / bounded 90 / absent 49**, and `COVERAGE_AUDIT.md:94` **already carries the
> newer, correct figures.** Applying B-27 would overwrite a right number with a wrong one
> while feeling like a fix. Re-measure before applying any entry here.
>
> **Two findings on this list were never applied and are still live** (details in
> `docs/DOC_CONTRADICTIONS_2026-08-26.md`):
> - **A-11** — `COVERAGE_AUDIT.md:63` still states the pre-2007 identifier gap as an
>   absolute (*"no row carries…"*). The conclusion holds; the absolute does not.
> - **B-33** — `COVERAGE_AUDIT.md:75` still claims the combined assistance series is
>   *"2000–2023 continuous"*. It starts 2001, it unions two different populations, and
>   `federal_funding` now reaches **2026**.
>
> **And the structural point, which is the most useful thing on this page:** **B-1** — the
> deals row count of **790**, caused by `code/35_coverage_audit.py` globbing
> `deals_*_additions.csv` and never seeing the 131 root-ledger rows — was recorded here
> correctly on 2026-08-06 and **went on propagating for three weeks anyway**, into
> `START_HERE.md` and `docs/COMPETITIVE_POSITION.md`. Nothing linked this document to the
> pages carrying the error. **A fact-check that nothing acts on becomes another stale
> document.** Corrected 2026-08-26; the real count is 921.



**Method.** Every figure below was recomputed from the files, not read from any doc. Row
counts came from a full CSV parse (pyarrow for files over 20 MB, `csv` module otherwise),
so embedded newlines and quoted commas are handled correctly. Dollar sums are exact
float64 over every row, with the sign retained.

**Standing caveat — the data moved while this audit ran.** Other agents were pulling and
rebuilding throughout. `data/clean/cedar_identifier_ledger_final.csv` changed at 14:01 and
again at 14:20; `data/spine/cedar_entity_spine.csv` changed at 14:19 and again after. Every
ledger and spine figure below is stamped with the snapshot it was measured from
(`scratchpad/snap/`, taken 2026-08-06 14:20 ET). Figures that are a moving target are
labelled as such — that instability is itself a finding, see D-1.

---

## Verdict summary

| # | Claim | Verdict |
|---|---|---|
| **A. Load-bearing figures** | | |
| A-1 | Prime contracting 617,142 rows, FY2000–2022 | **AGREES** |
| A-2 | Prime universe $206.8B | **AGREES** ($206,761,786,335.36) — but silently nets $4.81B of deobligations |
| A-3 | $135B linked | **DISAGREES** — $136,398,401,306 by `tribe_id`, $139,107,177,261 by `attributed_flag` |
| A-4 | Publishable prime dollars $91,371M | **DISAGREES and NOT DEFENSIBLE** — see D-2 |
| A-5 | Tier A/B/C/X ledger split 1,581 / 4,803 / 12,715 / 133 | **DISAGREES** — 1,705 / 4,637 / 12,711 / 179 |
| A-6 | Federal funding 476,924 transactions to 2023-04-05 | **AGREES** |
| A-7 | Funding regression 364,095 rows / $107,047,741,074.94 | **AGREES on rows, $45.13 high on dollars** (documented float error) — but `STATE_OF_BUILD` calls it "PASS to the cent", which is wrong |
| A-8 | New pull 136,301 rows / $46,722,267,898.61 | **AGREES exactly** |
| A-9 | New pull has "zero gap and zero overlap" with the spine | **DISAGREES** — 26 shared transaction keys |
| A-10 | FAADS 2,769,748 rows | **AGREES** |
| A-11 | FAADS: 0.0% of FY2001–2006 rows carry a recipient identifier, 66 agency-years | **DISAGREES — this is a rounding artifact stated as an absolute.** 65 rows do; 14 of the 66 agency-years are non-zero. Conclusion survives, wording does not. See D-3 |
| A-12 | Lobbying 1999–2026, 27,796 matched of 39,448 | **AGREES** |
| A-13 | Spine 866 entities, 179 ANCSA village/group corps | **AGREES at the 14:20 snapshot** (952 by end of audit) — but `STATE_OF_BUILD` says 687 |
| A-14 | Deals 922 rows | **AGREES** (790 additions + 132 root ledgers) |
| A-15 | Deals 871 covered (94.5%) | **DISAGREES** — 900 of 922 (97.6%) |
| **B. Row counts in the docs** | | see §2 — 11 disagreements |
| **C. Failure modes** | | see §3 — 5 of 7 survive somewhere |

---

## 1. Load-bearing figures, recomputed

### A-1/A-2/A-3 — Prime contracting

Source: `data/clean/prime_contracts.csv` (617,142 rows, 29 cols, built 2026-08-06 14:02).

| Claim | Stated | Recomputed | Verdict |
|---|---|---|---|
| Rows | 617,142 | 617,142 | AGREES |
| Fiscal years | FY2000–2022 | 2000–2022, no interior gap | AGREES |
| Universe | $206.8B | **$206,761,786,335.36** | AGREES |
| Linked | $135B | **$136,398,401,306.09** (279,432 rows with a non-blank `tribe_id`) | DISAGREES |
| Linked, alt. definition | — | **$139,107,177,260.75** (285,113 rows with `attributed_flag = 1`) | — |

Tier composition of `prime_contracts.csv` itself:

| Tier | Rows | Obligations |
|---|---:|---:|
| A | 146,447 | $82,798,993,104 |
| B | 138,666 | $56,308,184,157 |
| C (unattributed) | 332,029 | $67,654,609,075 |

**Two defects fall out of this.**

*Deobligations are netted with no disclosure.* 59,794 of the 617,142 rows carry a
**negative** `total_obligations`, totalling **−$4,813,482,633.74**. Gross positive
obligations are **$211,575,268,969.10**. The published $206.8B is therefore a *net* figure.
Nothing in `docs/handoffs/STATE_OF_BUILD.md`, `docs/datasets/02_contracting.md` or the codebook says so. A
subscriber summing awards will not reproduce it.

*`attributed_flag` and `tribe_id` disagree on 5,681 rows.* 285,113 rows carry
`attributed_flag = 1` but only 279,432 carry a non-blank `tribe_id`. The 5,681-row gap is
$2.7B. Whichever is right, two columns that are meant to say the same thing do not, and
there is no sanity check on the pair.

### A-4/A-5 — The publishable prime dollar figure

Measured from the 14:20 snapshot of `cedar_identifier_ledger_final.csv`.

| Quantity | Value |
|---|---:|
| `sum(prime_dollars_M)`, tier A rows | **90,876.443 M** |
| `sum(prime_dollars_M)`, all 19,232 rows | **256,317.745 M = $256.3B** |
| ...tier B | 69,732.171 M |
| ...tier C | 93,900.782 M |
| ...tier X *(ruled non-Native)* | 1,808.349 M |

The claimed **$91,371M** does not reproduce. Closest is $90,876M at 14:20 and $90,788M at
14:01 — the figure moved twice in twenty minutes. But the arithmetic is the smaller problem:

**`prime_dollars_M` is not a defensible dollar column and no total built from it should
ship.** Three independent proofs:

1. **It sums to more than the entire universe.** $256.3B across the ledger against a
   $206.8B prime-contracts file. A subset cannot exceed its superset.
2. **It does not reconcile to `prime_contracts.csv` on the same identifier.** Of the 11,809
   ledger rows with `prime_dollars_M > 0`, every one matches an identifier present in
   `prime_contracts.csv`, and **7,790 of them (66%) disagree by more than 0.5%** — always
   in the same direction, ledger high. On the matched rows the ledger says 256,391.1M and
   `prime_contracts.csv` says 206,820.3M.

   | Identifier | Entity | Ledger $M | prime_contracts $M |
   |---|---|---:|---:|
   | `JGSGGJJTAMK1` Petro Star | ANRC-ARCSLO-00 | 3,382.3 | 2,647.1 |
   | `M46UYYHVH4B1` TKC Integration | ANRC-NANARC-00 | 3,429.6 | 2,827.9 |
   | `WVJKC2L1ZN11` S&K Aerospace | TRBF-KTNIID-00 | 3,079.5 | 2,473.6 |
   | `DLNEJMG8NFB4` Chugach Mgmt Svcs | ANRC-CHGCCO-00 | 2,068.0 | 1,354.2 |
   | `HR78NDAERF44` NJVC | ANVC-CHENEG-00 | 1,695.1 | 1,119.9 |

3. **$92,481.9M of it sits on rows with a blank `tribe_id`** — i.e. 36% of the column's mass
   is attached to identifiers attributed to nobody. It cannot be an entity-level total and
   it cannot be an attributed total.

The codebook (`docs/codebooks/02_prime_contracting.md`) states what `prime_dollars_M` *is*
but not what window or source it measures, so there is no way for a buyer to reconcile it.

**The defensible replacement**, computed from `prime_contracts.csv` by joining awardee
UEI/CAGE to the tier-A identifier set:

> **$79,870,461,337.43 across 139,467 rows** (tier A as of the 14:20 ledger), or
> **$41,440,802,000** using the currently shipped `cedar_publishable_identifiers.csv`.

Neither is $91,371M.

**Tier split.** `docs/handoffs/STATE_OF_BUILD.md` line 142 says 1,581 / 4,803 / 12,715 / 133. No file has
ever held those numbers:

| File | mtime | A | B | C | X |
|---|---|---:|---:|---:|---:|
| `cedar_identifier_ledger_tiered.csv` | 08-05 16:20 | 1,577 | 4,813 | 12,721 | 121 |
| `..._final.csv.bak_..._pre56` | 08-05 18:32 | 1,628 | 4,636 | 12,711 | 257 |
| `..._final.csv.bak_..._pre50` | 08-05 19:00 | 1,699 | 4,637 | 12,711 | 185 |
| `..._final.csv` (snapshot) | 08-06 14:20 | **1,705** | **4,637** | **12,711** | **179** |

### A-6..A-9 — Federal funding

Source: `data/clean/federal_funding_transactions.csv`.

| Claim | Recomputed | Verdict |
|---|---|---|
| 476,924 transactions | 476,924 | AGREES |
| `action_date` runs to 2023-04-05 | 2007-10-01 → **2023-04-05** | AGREES |
| Transaction key 1:1, no dedup step needed | 476,924 distinct keys, **0 duplicates** | AGREES |
| Regression: 364,095 rows | tier A = **364,095** | AGREES |
| Regression: $107,047,741,074.94 | **$107,047,741,120.07** (+$45.13) | Matches the documented Stata-float error; `STATE_OF_BUILD` calling it "PASS **to the cent**" is wrong. `docs/datasets/03_funding.md` states the ~$45 correctly. |
| New pull 136,301 rows | 136,301 | AGREES |
| New pull $46,722,267,898.61 | **$46,722,267,898.61** | AGREES exactly |
| New pull dates 2023-04-06 → 2026-07-31 | same | AGREES |
| New pull population `business_types_code ∈ {I,J,K}` | I 115,374 · K 19,026 · J 1,901 · 0 outside | AGREES |
| New pull is 6 rows wider on award type (`07`) | exactly 6 | AGREES |

**A-9 — "zero gap and zero overlap" is false.** `data/raw/federal_funding/usaspending_2023_2026/_SOURCE.md`
§1 states the pull abuts the spine with "zero gap and zero overlap". **26
`assistance_transaction_unique_key` values appear in both.** They are not identical rows —
the same key carries a 2022 date and a large amount in the spine and a 2024–2026 date with
$0.00 or a small deobligation in the new pull:

```
12K2_AM22LFPA0000C026   spine 2022-07-19 $5,500,000.00 | new 2026-05-19 $0.00   Tuolumne Me-Wuk
12K2_AM23LFPA0000C010   spine 2022-12-06 $2,819,150.00 | new 2025-07-21 $0.00   CRITFC
12K2_AM23LFPA0000C011   spine 2022-12-29 $1,764,261.00 | new 2026-03-24 $0.00   MS Band of Choctaw
2050_21VITA0107         spine 2021-03-01 $   34,300.00 | new 2025-10-08 $-17,831.48  Shoshone-Bannock
```

$19,770,475 of spine dollars sit on those 26 keys. The consequence is not a simple
overstatement — it is that **`assistance_transaction_unique_key` is not stable across
vintages**. The project's own rule, "the transaction key is already 1:1 across all 476,924
rows", is true *within* a vintage and false *across* them. A naive append creates 26
duplicate keys; a dedup-keeping-max-$ silently discards USAspending's own revision, which
is the MR-7 anti-pattern this project already banned.

### A-10/A-11 — FAADS, and the claim that governs what can be sold

Source: `data/clean/faads_transactions_all_agencies.csv`, 2,769,748 rows, full scan.

| Claim | Recomputed | Verdict |
|---|---|---|
| 2,769,748 rows | 2,769,748 | AGREES |
| 66 agency-years | 77 agency-years in the file; **66 in FY2001–2006** (11 agencies × 6 yr) | AGREES as stated |
| USDA FY2001–2006 aggregate rows 309,339 | **309,339** on `record_type = 1`; 309,347 on the literal name `MULTIPLE RECIPIENTS` | AGREES |
| ...$321B | **$321.18B** (USDA FY2001–06); $321.73B for every aggregate row in the file | AGREES |

**A-11 fails.** `docs/COVERAGE_AUDIT.md` states:

> "**no row carries a recipient identifier before 2007**. 6 fiscal years (2001–2006) are
> 0.0% DUNS across every agency, maximum 0.0%"

Direct scan of the transaction file:

| FY | Rows | Rows with a DUNS or UEI | % |
|---|---:|---:|---:|
| 2001 | 316,006 | **1** | 0.0003 |
| 2002 | 321,290 | **3** | 0.0009 |
| 2003 | 334,206 | **6** | 0.0018 |
| 2004 | 318,543 | **9** | 0.0028 |
| 2005 | 327,210 | **7** | 0.0021 |
| 2006 | 377,738 | **39** | 0.0103 |
| 2007 | 774,755 | 676,970 | 87.38 |

**65 of 1,994,993 pre-FY2007 rows carry a recipient identifier, and 14 of the 66
agency-years are non-zero** (max 0.044%, DOJ FY2006), not 52 of 66 as implied.

*Mechanism.* `data/clean/faads_identifier_coverage_by_agency_year.csv` stores
`pct_with_duns` **rounded to one decimal** and carries **no raw count column**.
`code/35_coverage_audit.py` then tests `max(pct) > 0`. 0.0103% becomes `0.0`, and a
rounding artifact is published as an absolute claim about the data.

**The conclusion survives; the sentence does not.** 0.0033% is operationally zero and the
FY2007 attributable floor is correct. But "no row carries" is a falsifiable absolute in a
document a buyer will read, and it is false. Correct wording: *65 of 1,994,993 FY2001–2006
rows (0.003%) carry a recipient DUNS or UEI; the highest agency-year rate is 0.04%. The
attributable floor is FY2007.*

*Also in FAADS, undisclosed:* 225,204 negative rows totalling **−$70,017,881,527.77**
against +$1,900,657,199,235.43 positive. And `recipient_uei` is populated on FY2007 rows —
UEIs did not exist until 2022, so that column is a back-filled *current* identifier, not a
contemporaneous one. Neither fact is stated anywhere.

### A-12 — Lobbying

`data/clean/native_entity_lobbying_disclosures.csv`: **27,796 rows, 27,796 distinct
`filing_uuid`, `filing_year` 1999–2026, 300 distinct `entity_id`, zero blank.**
`docs/LOBBYING_BUILD_LOG_2026-08-05.md` records 39,448 filings scored. 27,796 / 39,448 =
70.5% matched. **AGREES.** No row multiplication: summing `spend_usd` raw and deduped on
`filing_uuid` both give **$725,223,724.52**.

### A-13 — Spine

Read directly from `data/spine/cedar_entity_spine.csv` early in this audit: **866 rows**,
prefix `ANVC` = **179** (173 Alaska Native Village Corporations + 6 ANCSA Group
Corporations). **AGREES.**

Minutes later the same file held **952 rows** (55 `ITO` intertribal and 31 `NHO` rows added
by another agent mid-session). `ANVC` was still 179 — the ANCSA count is stable, the entity
total is not.

`docs/handoffs/STATE_OF_BUILD.md` says **687** in two places (line 78 of `02_contracting.md` and the Spine
status table). That was the NEID backbone count and is now 179–265 entities stale.

### A-14/A-15 — Deals

| Component | Rows |
|---|---:|
| `deals_*_additions.csv` (9 files) | 790 |
| `deals_2026_ytd.csv` | 76 |
| `deals_historical_2020_2025.csv` | 56 |
| **Total** | **922** |

**922 AGREES.** `Deal_ID` is unique across all 922; no ID appears in both an additions file
and a root ledger.

**Party attribution — 871 (94.5%) DISAGREES.** Recomputing coverage of the 607 distinct
`Native_Party` values against `deals_party_attribution.csv` (Elijah, 57),
`deals_party_autoresolved.csv` (443) and `deals_party_attribution_agent.csv` (530):

> **900 of 922 rows covered = 97.61%.** 22 rows (22 distinct parties) uncovered.

By tier: **A 853 · B 39 · X 8 · none 22.** `STATE_OF_BUILD` also says "604 at tier A" —
recomputed **853**. Both figures predate `code/57_autoresolve_deal_parties.py`.

**The charting-rule numbers are wrong.** `docs/handoffs/STATE_OF_BUILD.md` and
`docs/datasets/01_deals.md` both say *"622 'Grant / public financing' rows against 116
acquisitions"* and give a federal-award share by year.

| Figure | Stated | Recomputed (all 922) |
|---|---:|---:|
| Grant / public financing | 622 | **622** ✓ |
| Acquisition | 116 | **152** ✗ |
| 2019 share | 85% | **81.3%** (61/75) |
| 2022 share | 97% | **92.5%** (172/186) |
| 2024 share | 93% | **90.4%** (160/177) |
| 2026 share | 35% | **32.5%** (25/77) |
| pre-2010 share | 0% | **0%** ✓ (2000–2009 all zero) |

Share computed as `Deal_Category = 'Grant / public financing'` ÷ rows in that `Event_Year`.
The *substance* of the charting rule — never chart the two populations as one series — is
correct and the swing is real. Only the four percentages and the acquisition count are off.

---

## 2. Every stated row count and figure, recomputed

Green rows are omitted where they simply agree; **everything that disagrees is listed, with
the file it is written in.**

### 2.1 Disagreements

| # | Figure | Stated | Where it is written | Recomputed |
|---|---|---:|---|---:|
| B-1 | Deals rows | 790 | `docs/COVERAGE_AUDIT.md` deals row | **922** — the audit globs `deals_*_additions.csv` and never sees the 132 rows in `deals_2026_ytd.csv` + `deals_historical_2020_2025.csv` |
| B-2 | Lobbying rows | 11,717 | `docs/handoffs/STATE_OF_BUILD.md` §Where every dataset stands | **27,796** |
| B-3 | Lobbying disclosures file | 43,963 | `docs/datasets/04_lobbying.md` Files table | **27,796** |
| B-4 | Subawards rows | 1,817 | `docs/handoffs/STATE_OF_BUILD.md` (twice) · `docs/datasets/02b_subcontracting.md` | **998** |
| B-5 | Federal actions rows | 156,466 | `docs/handoffs/STATE_OF_BUILD.md` Datasets table · `docs/datasets/09_federal_actions.md` (both files) | **156,452** |
| B-6 | Native bills rows | 3,047 | `docs/handoffs/STATE_OF_BUILD.md` · `docs/datasets/10_bills_votes.md` | **3,037** |
| B-7 | Compact terms | 1,705 | `docs/handoffs/STATE_OF_BUILD.md` · `docs/datasets/compacts.md` | **1,311** |
| B-8 | Gaming facilities | 775 | `docs/handoffs/STATE_OF_BUILD.md` · `docs/datasets/gaming.md` | **774** |
| B-9 | Dataset 5 entity-year rows | 10,845 | `docs/handoffs/STATE_OF_BUILD.md` (4 places) | **11,865** |
| B-10 | Ownership events | 99 | `docs/handoffs/STATE_OF_BUILD.md` (3 places) | **98** |
| B-11 | Spine entities | 687 | `docs/handoffs/STATE_OF_BUILD.md` Spine status · `docs/datasets/02_contracting.md` | **866** at 14:20; **952** later |
| B-12 | Publishable identifiers | 1,581 | `docs/handoffs/STATE_OF_BUILD.md` | **1,577** in the file; **1,705** tier A in the ledger |
| B-13 | Awaiting a ruling | 4,751 | `docs/handoffs/STATE_OF_BUILD.md` | **4,637** tier B |
| B-14 | Elijah rulings on file | 164, then 25, then 157 | `docs/handoffs/STATE_OF_BUILD.md` (two different numbers) · `docs/CROSS_DATASET_LEARNING.md` | `data/spine/cedar_rulings.csv` = **8**; `review/rulings_inbox_*.csv` = **13 files, 335 ruled rows**. No file holds 164, 25 or 157. |
| B-15 | Elijah deals rulings | 34 parties | `docs/handoffs/STATE_OF_BUILD.md` Live warnings | **57** rows in `deals_party_attribution.csv` |
| B-16 | Deals party coverage | 871 of 922 (94.5%), 604 at tier A | `docs/handoffs/STATE_OF_BUILD.md` | **900 of 922 (97.6%)**, **853 at tier A** |
| B-17 | Deals: acquisitions | 116 | `docs/handoffs/STATE_OF_BUILD.md` · `docs/datasets/01_deals.md` | **152** |
| B-18 | Deals: federal-award share 2019/2022/2024/2026 | 85 / 97 / 93 / 35 % | both files | **81.3 / 92.5 / 90.4 / 32.5 %** |
| B-19 | Codebook: 02_prime_contracting rows | 622,750 | `docs/codebooks/README.md` | **623,174** |
| B-20 | Codebook: 03_federal_funding rows | 2,748,625 | `docs/codebooks/README.md` | **3,252,168** |
| B-21 | FPDS edges: distinct children | 1,805 | `docs/datasets/02_contracting.md` | **1,844** |
| B-22 | FPDS edges: children with >1 parent | 190 | `docs/datasets/02_contracting.md` | **267** |
| B-23 | FR rulemakings not to be quoted as tribal | 63,248 | `docs/handoffs/STATE_OF_BUILD.md` · `docs/datasets/09_federal_actions.md` | **63,400** (Rule 39,710 + Proposed Rule 23,690) |
| B-24 | Nonprofit tier-A revenue aggregate | $2.51B | `docs/handoffs/STATE_OF_BUILD.md` · `docs/datasets/06_nonprofit.md` | **$218,256,135** latest-year over 419 orgs (**$7.13B** all years). Umatilla Electric and Yavapai Community Hospital are no longer tier A. *The warning is still right — do not quote it — but the number is stale.* |
| B-25 | Nonprofit tier-A rows awaiting a ruling | 412 | `docs/datasets/06_nonprofit.md` | **81** with `review_flag` set (739 tier A total) |
| B-26 | Gaming `open_date_precision` | 152 day / 258 year / 148 month | `docs/handoffs/STATE_OF_BUILD.md` | **180 day / 279 year / 158 month** (+156 blank, 1 decade) |
| B-27 | Gaming `open_date_class` | exact 576 / absent 138 / bounded 60 | `docs/COVERAGE_AUDIT.md` | **exact 617 / absent 80 / bounded 77** |
| B-28 | Gaming day-31 / day-15 placeholders | 150 / 148 | `docs/handoffs/STATE_OF_BUILD.md` | **151 / 155** |
| B-29 | Gaming `open_date_event = gaming_commenced` | 112 | `docs/handoffs/STATE_OF_BUILD.md` | **162** |
| B-30 | Pre-IGRA gaming facilities | 42 | `docs/handoffs/STATE_OF_BUILD.md` | **51** with `open_date` year < 1988 |
| B-31 | Funding regression | "PASS **to the cent**" | `docs/handoffs/STATE_OF_BUILD.md` | passes to **$45.13**; `docs/datasets/03_funding.md` states this correctly |
| B-32 | FAADS observed years | 2000–2007 | `docs/COVERAGE_AUDIT.md` | `fiscal_year` is **2001–2007**; FY2000 has zero rows. The 2000 comes from `action_date` 2000-10-01, which is FY2001. |
| B-33 | Combined assistance series "2000–2023 continuous" | — | `docs/COVERAGE_AUDIT.md` | **2001–2023**, and see C-5: it unions two different populations |

### 2.2 Figures that agree (spot-verified)

`prime_contracts` 617,142 · prime universe $206,761,786,335.36 · funding 476,924 /
0 duplicate keys / last `action_date` 2023-04-05 / tier A 364,095 · new pull 136,301 /
$46,722,267,898.61 / `business_types_code` I 115,374 K 19,026 J 1,901 / 6 type-`07` rows ·
FAADS 2,769,748 rows / 66 FY2001–2006 agency-years / USDA aggregate 309,339 rows / $321.18B ·
lobbying 27,796 of 39,448, 1999–2026, `filing_uuid` unique, `spend_usd` $725,223,724.52 with
zero row multiplication · spine `ANVC` 179 (173 village + 6 group) · ANC ceiling 196 ·
DOI NHO roster 190 · identifier ledger 19,232 · `fpds_uei_edges` 2,290 · `fpds_uei_cage_map`
24,977 · `cedar_cage_backfill` 4,362 · 9 malformed CAGEs, all 9 flagged · nonprofit exclusions
4,656, all `authority_class = automated_filter` · `np_orgs` 12,764 · `np_financials` 8,507 ·
compacts 707 / versions 1,158 / deemed-approved 165 / term recall 618 of 1,158 = 53.4% /
21 tier-bracket rows · gaming land decisions 138, `bia_tribes_column_conflict` on 3 ·
`gaming_facility_metrics` 65,223 · **`measure_type = gaming_revenue` 592 observations,
`value_basis` reported 126 / payments_derived 372 / modelled 56 / reverse_engineered 38 —
all four exact** · 1,108 non-`current` observations including 298 `gaming_machines` ·
27 `open_date_postdates_observation` · `title_abstract_term_hit` 22,169 = 14.2% ·
283 of 3,037 bills with a roll call = 9.3% · 141 Senate roll calls, 28 with
`pro_tribal_is_yea` · 21 `direction_circularity_flag` · 53 `resolution_vehicle` votes ·
`cross_dataset_ruling_map` 7,507 · subaward number non-unique 867 of 998 · codebook README
row counts for datasets 01, 02b, 04, 05, 06, 07, 08, 09, 10.

---

## 3. The seven failure modes — which ones survive

| # | Failure mode | Status |
|---|---|---|
| 1 | Double counting from overlapping source files | **SURVIVES — 2 instances** |
| 2 | Signed obligations netted silently | **SURVIVES — 3 instances, none disclosed** |
| 3 | Cumulative read as transactional | **SUSPECTED — 382 contracts show the signature; the file has no unique key** |
| 4 | Aggregate recipients reaching a per-entity figure | **CLEAN** |
| 5 | Population mismatch (filtered ∪ unfiltered) | **SURVIVES — published in `COVERAGE_AUDIT.md`** |
| 6 | Entity conflation | **SURVIVES — and the fix is regressing** |
| 7 | Village corporation booked to village government | **SURVIVES — $27.59B, the largest single defect found** |

### C-1 · Double counting — two live instances

**(a) A duplicated deal, $15.827M.** The same Bristol Bay Native Corporation / Bristol
Express Fuels acquisition, `2015-07-15`, `$15,827,000`, appears twice:

| Deal_ID | File | Source |
|---|---|---|
| `ND-2015-201` | `deals_anc_reports_additions.csv` | `web.archive.org/.../bbnc.net/wp-content/...` |
| `ANCSA-2015-002` | `deals_ancsa_portal_additions.csv` | `portal.akdbsstar.us/StarWebPortal/ViewFile.aspx?Id=49741017-73` |

Distinct `Deal_ID`s, so no key check catches it. Same party, same date, same amount, same
counterparty, same deal title. **It is the only such collision across all 922 rows**, and
to the project's credit it is already sitting in `review/deals_duplicate_candidates.csv`
(`why_flagged: same party, same counterparty, dates within 180 days`, `value_match = 1`).

But `YOUR_RULING` is **blank on all 19 rows of that queue**, so the duplicate is live: it is
inside the 922-row count, inside the `Acquisition` category count, and worth $15,827,000 of
double-counted deal value until ruled. By the project's own dating rule the filing-sourced
`ANCSA-2015-002` should survive and `ND-2015-201` should be withdrawn to
`review/deals_withdrawn_duplicates.csv` (which currently holds 2 rows, `ND-2026-077` and
`ANCSA2-2020-003`).

**(b) 26 transactions shared between the funding spine and the new pull** — see A-9. The
`_SOURCE.md` claim of "zero overlap" is false, and the overlap is of the dangerous kind: the
same key with different dates and amounts across vintages.

Everything else checked clean. `subawards.csv` draws from **one** source file
(`subcontract-05-09-23-22-23-37.csv`), and `(prime_award_id, subaward_number)` is unique
across all 998 rows. Across the nine `deals_*_additions.csv` files, all 790 `Deal_ID`s are
distinct and none collides with the 132 root-ledger IDs. `federal_funding_transactions.csv`
has 476,924 distinct keys and zero duplicates.

### C-2 · Signed obligations — three undisclosed nettings

| Where | Negative rows | Negative $ | Positive $ | Published net |
|---|---:|---:|---:|---:|
| `prime_contracts.csv` | 59,794 | −$4,813,482,633.74 | $211,575,268,969.10 | **$206,761,786,335.36** |
| Funding tier A (the regression figure) | 19,364 | −$2,073,877,248.15 | $109,121,618,368.22 | **$107,047,741,120.07** |
| `faads_transactions_all_agencies.csv` | 225,204 | −$70,017,881,527.77 | $1,900,657,199,235.43 | $1,830,639,317,707.66 |

None of the three is described as net anywhere. The $206.8B and $107.0B figures are both
sold as headline totals. A buyer who sums positive awards will be $4.8B and $2.1B high
respectively and will conclude the data is wrong.

*What to do:* say "net of deobligations" beside each figure, and add a `gross_obligations` /
`deobligations` pair to the entity-year panels. Do not strip the negatives — they are real.

### C-3 · Cumulative vs transactional — a smell, not yet a proof

`prime_contracts.csv` has **no unique key**:

- `contract_number` alone: 318,792 distinct over 617,142 rows
- `(contract_number, fiscal_year)`: **132,743 duplicate rows**
- `(contract_number, fiscal_year, awardee_uei)`: **19,257 duplicate rows**

87,339 contracts span more than one fiscal year. Of those, **382 carry an identical non-zero
`total_obligations` in every year they appear**, and 4,511 more carry a strictly
non-decreasing series. Example:

```
F3260599MU054   2000 $733,000 · 2001 $733,000 · 2002 $733,000 · 2003 $733,000
F0466602C0029   2002–2006, $150,534 in each of five years
DABK1503C0005   2003–2007, $175,000 in each of five years
```

Identical option-year obligations are possible, so this is not proof. But it is the exact
signature of an award-level snapshot repeated per year, it affects a bounded and checkable
set of 382 contracts, and nobody has looked. Until someone does, `prime_contracts.csv`
cannot be certified transactional.

Separately, `total_award_value` sums to **$712,933,823,060** — 3.4× obligations. Nothing
reports it as a flow today, and nothing documents that it must not be.

### C-4 · Aggregate recipients — CLEAN

USDA FY2001–2006 books **309,339 rows** (`record_type = 1`) / **$321.18B** to
`MULTIPLE RECIPIENTS`. Verified they cannot reach a per-entity figure:

- **`tribe_id` is blank on all 2,769,748 FAADS rows.** Not one row is attributed to any
  entity, so no per-entity total can include them.
- FAADS is not joined into `federal_funding_transactions.csv`, `entity_year_panel.csv` or
  `prime_contracts_entity_year.csv`.
- In `federal_funding_transactions.csv` only 187 rows carry an aggregate recipient name
  (186 `MULTIPLE RECIPIENTS`, 1 `MISCELLANEOUS FOREIGN AWARDEES`), and the 26 overlap rows
  include one, `2001_SLFRPMIS1` = `DOMESTIC AWARDEES (UNDISCLOSED)`.

The one exposure is C-5: if the "combined series" is ever built, $321B of aggregate money
enters a chart labelled Native assistance.

### C-5 · Population mismatch — published, in `COVERAGE_AUDIT.md`

`docs/COVERAGE_AUDIT.md` §Combined series states:

> "**Federal assistance** — `faads` 2000–2007 + `federal_funding` 2007–2023 → **2000–2023
> continuous**"

These are not two halves of one series. They are two different populations:

| | `faads_transactions_all_agencies.csv` | `federal_funding_transactions.csv` |
|---|---|---|
| Rows | 2,769,748 | 476,924 |
| Recipient filter | **none** — full federal assistance universe | **tribal only** (`business_types_code ∈ {I,J,K}`) |
| Largest recipient type | `A` STATE GOVERNMENT, 719,231 rows | tribal governments and TDHEs |
| Rows attributed to an entity | **0** | 364,095 |
| Total obligations | **$1,830,639,317,708** | $140,437,899,149 |

Concatenating them produces a series that is $1.83 trillion of mostly state and local money
through FY2007 and $140B of tribal money after — a 13× step change at the seam that is
purely a change of population. `code/35_coverage_audit.py` builds this claim from year
ranges alone (`obs[p][0]`, `obs[p][1]`) and never compares the two files' populations.

This is the single most saleable-looking and most wrong sentence in the documentation.

### C-6 · Entity conflation — the Kootenai fix is regressing

`review/kootenai_conflation_correction.csv` records the correct ruling: six UEIs move from
`TRBF-KTNIID-00` (Kootenai Tribe of Idaho) to `TRBF-CSKTFR-00` (Confederated Salish and
Kootenai), citing S&K's own site. **The correction is not in the shipped ledger.**

| File | mtime | S&K Aerospace `WVJKC2L1ZN11` | EIN `237641597` |
|---|---|---|---|
| `cedar_identifier_ledger_tiered.csv` | 08-05 16:20 | KTNIID, A | KTNIID, B |
| `..._final.csv.bak_..._pre56` | 08-05 18:32 | **CSKTFR, A** ✔ | **X** ✔ |
| `..._final.csv.bak_..._pre50` | 08-05 19:00 | KTNIID, A ✘ | B ✘ |
| `..._final.csv.bak_2026-08-06_pre56` | 08-05 19:01 | **CSKTFR, A** ✔ | **X** ✔ |
| **`cedar_identifier_ledger_final.csv`** | **08-06 14:20** | **KTNIID, A** ✘ | **B** ✘ |
| **`cedar_publishable_identifiers.csv`** (shipped) | 08-05 16:20 | **KTNIID, A** ✘ | — |

**Mechanism.** `code/09_import_rulings.py` reads `cedar_identifier_ledger_tiered.csv`
(line 92) and writes `cedar_identifier_ledger_final.csv` (line 294). `code/50` patches the
*final* file. Any subsequent run of 09 rebuilds final from tiered and discards the patch.
The fix has been applied and lost twice; it is lost right now.

Live consequence: all seven S&K/Salish-Kootenai UEIs sit at tier A under a tribe named
"Kootenai" in `cedar_publishable_identifiers.csv`, the file the publication layer ships,
carrying `prime_dollars_M` of 3,079.5 + 272.7 + 125.5 + 4.0 + 2.0 + 0.01. Any per-tribe
total for either tribe is wrong.

*Note* — `prime_contracts.csv` **is** correct: it books $3.43B to `TRBF-CSKTFR-00` and only
$393,695 to `TRBF-KTNIID-00`. So the two shipped artefacts now disagree with each other
about the same tribe.

**Other short/generic spine names to check.** **419 of the 952 spine entities** have a
`canonical_name` of 12 characters or fewer, many of them bare words that will act as
magnets: `Kaw`, `Koi`, `Ute`, `Crow`, `Hopi`, `Zuni`, `Eagle`, `Wales`, `Nome`, `Solomon`,
`Inupiat`, `Barrow`. Two are already visibly wrong (see C-7): `AKNF-INPTAS-00` is named
`Inupiat` and holds ASRC regional-corporation subsidiaries; `AKNF-VWALES-00` is named
`Wales` and holds *Prince of Wales* entities (`Powtec (Prince Of Wales Tribal Enterprise
Co...)`, $94.3M) — a different place entirely.

### C-7 · Village corporation vs village government — $27.59 billion

`review/village_corp_namesake_pairs.csv` lists 77 pairs and states the rule outright:

> "Separate legal persons. A contract to the corporation is not revenue to the government."

The ledger breaks that rule 164 times, and `prime_contracts_entity_year.csv` — a shipped
per-entity panel — carries the result:

> **96 `AKNF-` Alaska Native Village GOVERNMENT entities carry $27,593,515,241 of prime
> obligations.** 34 of them ($16,550,837,919) have a named ANCSA corporation counterpart in
> the namesake-pairs file. Meanwhile only **19 `ANVC-` village corporations carry anything at
> all** ($16.94B), out of 179 in the spine.

| Booked to (village GOVERNMENT) | Obligations | Actual awardee family | Should be |
|---|---:|---|---|
| `AKNF-CHNEGA-00-...` "Chenega" | $5,054,600,923 | Chenega Infinity, Chenega IT Enterprise, CTSC | `ANVC-CHENEG-00` Chenega Corporation |
| `AKNF-AFGNAK-00-KONIAG` "Afognak" | $3,835,970,815 | Alutiiq International, FSS Alutiiq JV | `ANVC-AFOGNA-00` Afognak Native Corporation |
| `AKNF-INPTBW-00-ARCSLO` "Barrow" | $3,738,886,555 | Bowhead Science & Technology, DECO | Ukpeaġvik Iñupiat Corporation |
| `AKNF-TLNGHD-00-SEALSK` "Tlingit & Haida" | $2,637,560,354 | Goldbelt Wolf, Goldbelt Security, Goldbelt Falcon | Goldbelt Inc. (Juneau **urban** corporation) |
| `AKNF-WAINWT-00-ARCSLO` "Wainwright" | $1,903,479,556 | Olgoonik Global Security, Olgoonik Diversified | Olgoonik Corporation |
| `AKNF-VEAGLE-00-...` "Eagle" | $1,491,239,125 | Eagle Eye Electric, Eagle Global Scientific | — |
| `AKNF-INPTAS-00-ARCSLO` "Inupiat" | $1,258,613,845 | Arctic Slope Mission Services, Bowhead Transportation | `ANRC-ARCSLO-00` ASRC (a **regional** corporation) |
| `AKNF-NVEYAK-00-...` "Eyak" | $1,141,721,217 | Copper River IT, NorthTide Group | `ANVC-EYAKXX-00` Eyak Corporation |
| `AKNF-TYONEK-00-CKINLT` "Tyonek" | $1,057,189,579 | Tyonek Services Overhaul, Tyonek Manufacturing | `ANVC-TYONE1-00` The Tyonek Native Corporation |

The Tlingit & Haida row is worse than a namesake swap: Goldbelt is the Juneau **urban**
corporation, whose shareholders are Juneau-area Alaska Natives, not the Central Council of
Tlingit and Haida Indian Tribes of Alaska, which is a tribal government. $2.64B is booked to
a government that never received it.

This is the same defect class as `TRBF-KTNIID-00` at roughly ten times the scale, and it is
systematic rather than a single row. It also contradicts the project's own taxonomy:
`parent_native_entity` is defined as **ownership**, and a village corporation is owned by its
ANCSA shareholders, not by the village government.

The ledger rows are tier **B**, so they do not publish today. But `prime_contracts.csv` and
`prime_contracts_entity_year.csv` assign the `tribe_id` regardless of tier, and the entity-year
panel is a deliverable. The $27.59B is already inside a shipped file.

---

## 4. Publication layer — `code/25_build_publication_layer.py`

Run 2026-08-06. **12 checks executed and passed, 1 skipped, 0 failed.**

| Check | Result |
|---|---|
| Blank identifiers in ledger | PASS (0) |
| Tier X leaked into publishable set | PASS (0) — **but see below, this check cannot fail** |
| Excluded identifiers present in publishable set | PASS (0) |
| Malformed CAGE unflagged in `uei_cage_map` | PASS (0) |
| Ownership self-edges | PASS (0) |
| Federal roll-up unflagged in ownership edges | PASS (0) |
| Duplicate `compact_id` | PASS (0) |
| Orphan `compact_versions` | PASS (0) |
| Dangling `bill_id` in `bill_votes` | PASS (0) |
| NHO firms in tier A with no ruled parent | PASS (0) |
| Funding rows attributed AND excluded without both flags | PASS (0) |
| pre-2000 rows in `federal_actions` (informational) | PASS (22,006, expected non-zero) |
| **Deal rows missing a `Deal_Category`** | **SKIP — `no such table: deals`** |

### 4.1 The skipped check has never run

`deals` is not in the `TABLES` list in `code/25`. The check guarding the single most
important editorial rule in the product — never chart negotiated transactions and federal
awards as one series — has never executed once. More broadly, **Dataset 1 is absent from
`dist/cedar_press.db` and `dist/cedar_press_master.xlsx` entirely.** So are
`prime_contracts.csv`, `prime_contracts_entity_year.csv`, `entity_year_panel.csv`
(Dataset 5), `ownership_events.csv`, `np_financials.csv`, `gaming_facility_metrics.csv`,
`gaming_decision_events.csv` and `faads_transactions_all_agencies.csv` — nine of the
project's largest and most saleable files, including the entire prime-contracting
transaction layer that A-1 to A-3 are computed from.

### 4.2 One check is self-referential and can never fail

```sql
SELECT COUNT(*) FROM publishable_identifiers WHERE confidence_tier <> 'A'
```

`cedar_publishable_identifiers.csv` is *written* as the tier-A subset, so the column it
tests is a constant. The check reads as protection against tier leakage and provides none.
The real risk — that the publishable file has drifted from the ledger — is measured against
the ledger, and it has: **118 tier-A ledger rows are missing from the publishable file**
(1,577 vs 1,705). The publishable file has not been regenerated since 2026-08-05 16:20 while
the ledger changed at least four times since.

### 4.3 Checks that would have caught what this audit found

Proposed, in priority order. Each names the defect it would have caught.

| Check | SQL / test | Catches |
|---|---|---|
| **1. Publishable set is in sync with the ledger** | `SELECT COUNT(*) FROM publishable_identifiers p LEFT JOIN identifier_ledger l USING(identifier_type,identifier,tribe_id) WHERE l.confidence_tier IS NULL OR l.confidence_tier<>'A'` — **and** the reverse, tier-A ledger rows absent from publishable | 4.2 — 118 missing rows, and any future X-leak |
| **2. `deals` table exists and is loaded** | assert `deals` in `TABLES`, then the existing `Deal_Category` check | 4.1 |
| **3. One entity, one legal person** | for every row of `review/village_corp_namesake_pairs.csv`, `SELECT ... FROM identifier_ledger WHERE tribe_id = <government_tribe_id> AND legal_business_name LIKE '%<corp stem>%'` → must be 0 | **C-7, $27.59B** |
| **4. Identifier name vs entity name** | flag any tier-A row where no token of `legal_business_name` appears in `canonical_name` or `aliases` and `attribution_method='hand'` | **C-6, Kootenai** |
| **5. Correction files are still applied** | for every `review/*_correction.csv`, assert the `*_after` state holds in the current ledger | **C-6 regression** — would fail today |
| **6. Every dollar total declares its sign basis** | assert each published total has a sibling `gross_*` / `deobligations_*`, or a `basis='net'` label | **C-2** |
| **7. Transaction files have a declared unique key** | assert a named key column set is unique on every file typed `transaction` | **C-3** |
| **8. Coverage audit sees every file in the dataset** | compare `DATASETS` globs in `code/35` against the dataset's file list in `code/24_generate_dataset_docs.py`; any file in one and not the other fails | **B-1** — 132 deal rows invisible to the audit |
| **9. Combined series requires a population match** | before emitting a "combined series" line, assert the two files agree on recipient-filter columns and on the share of rows carrying an entity id | **C-5** |
| **10. Zero claims must be counts, not rounded percentages** | any narrative "0.0% / no row" must be backed by a raw count column; `faads_identifier_coverage_by_agency_year.csv` must carry `n_with_duns` | **A-11** |
| **11. New pulls must not share keys with the spine** | before promoting a staged pull, `INTERSECT` on the transaction key; non-zero requires an explicit supersede rule | **A-9** — 26 keys |
| **12. Derived dollar columns must reconcile to source** | assert `prime_dollars_M` per identifier is within 0.5% of `SUM(total_obligations)` in `prime_contracts` for that identifier | **A-4** — fails on 7,790 of 11,809 rows |
| **13. `attributed_flag` agrees with `tribe_id`** | `SELECT COUNT(*) FROM prime_contracts WHERE (attributed_flag='1') <> (TRIM(COALESCE(tribe_id,''))<>'')` | A-3 — 5,681 rows |
| **14. Doc figures are regenerated, not typed** | fail the build if any number in `docs/handoffs/STATE_OF_BUILD.md` differs from the measured value | all 33 of §2.1 |

---

## 5. Two process findings

### D-1 · The numbers are a moving target

Three files changed *during* this audit:

| File | Observed changes on 2026-08-06 |
|---|---|
| `cedar_identifier_ledger_final.csv` | 14:01 (tier A = 1,699) → 14:20 (tier A = 1,705) |
| `cedar_entity_spine.csv` | 866 rows → 952 rows within minutes (55 `ITO`, 31 `NHO` added) |
| `gaming_facilities.csv` | rewritten 14:11, *after* `COVERAGE_AUDIT.md` was regenerated at 14:02 |

Consequence: `$91,371M`, the tier A/B/C/X split, and the spine entity count are all
quantities that had a different value an hour earlier and will have another an hour later.
No figure in this class should appear in a sale document without a snapshot hash beside it.

`docs/COVERAGE_AUDIT.md` carries a promise that it "cannot drift from the files it
describes". It drifted within nine minutes (B-27). The promise is only true if the audit is
the last thing that runs, and it is not. `code/00_run_all.py` should regenerate the three
measured docs as a final stage, and the sale package should be cut from a frozen snapshot
with a recorded hash per file.

### D-2 · `docs/handoffs/STATE_OF_BUILD.md` contradicts itself

The same document gives two values for the same quantity in several places:

- Elijah rulings on file: **164** (line 113) and **25** (Spine status table)
- Federal actions: **156,466** (Datasets table) and **156,452** (Where every dataset stands)
- Native bills: **3,047** and **3,037**
- Compact terms: **1,705** and **1,311**
- Gaming facilities: **775** and **774**
- Deals: **922** (Where every dataset stands) and **132** (Datasets table, "Inherited, not extended")
- Publishable prime dollars: **$42.6B** (Spine status) vs $42,236.8M measured in the file it names

A buyer reading the state document top to bottom will find it disagreeing with itself before
they reach the data.

---

## 6. What must change before sale

**Blocking — a wrong attribution is shipping.**

1. **C-7.** $27.59B booked to Alaska Native Village governments that should sit with ANCSA
   village and urban corporations. `prime_contracts_entity_year.csv` is a deliverable and is
   wrong for 96 entities.
2. **C-6.** Re-apply the Kootenai correction *in `code/09`'s input*, not downstream of it,
   and regenerate `cedar_publishable_identifiers.csv`.
3. **A-4.** Withdraw `prime_dollars_M` and any total built on it, including
   "$91,371M publishable prime dollars". Replace with the `prime_contracts.csv` join:
   **$79.87B** on tier A as of the 14:20 ledger.
4. **C-5.** Delete or rewrite the "Federal assistance 2000–2023 continuous" line in
   `COVERAGE_AUDIT.md`.
5. **A-11.** Rewrite the FAADS zero-identifier sentence as a count, not a rounded percentage.

**Correct before sale — 33 stated figures do not reproduce.** §2.1.

**Disclose — three totals are net of deobligations and say so nowhere.** §C-2.

**Investigate — 382 contracts with a cumulative-snapshot signature, and no unique key on
`prime_contracts.csv`.** §C-3.

