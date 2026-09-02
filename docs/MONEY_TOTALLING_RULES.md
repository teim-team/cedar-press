# What a buyer may total — `funding` and `subcontracting`

*Generated 2026-09-01 by `code/574_ws1_money_and_conservation.py`. Every number below is re-measured from the live files and from the staged source objects on each run. Regenerate rather than edit.*

## The one-line answer per table

| table | additive measure | sum it at | what double-counts |
|---|---|---|---|
| `faads_transactions.csv` | `obligated_usd` | one row = one federal assistance TRANSACTION (a modification). Sum freely; group by `award_id_fain` to reach award level | nothing internal. **Never add it to `faads_transactions_all_agencies.csv`** — those 60,661 rows are carried into that file verbatim |
| `faads_transactions_all_agencies.csv` | `obligated_usd` | same grain; this file is the SUPERSET (Interior slice + 10 more agencies, FY2001–07) | adding the Interior file to it; and joining on `tribe_id`/`cedar_uid`, which are blank on every row |
| `subawards.csv` | `subaward_amount` | **only** rows with `duplicate_status == 'primary'` AND `subaward_exceeds_prime_flag != 'yes'` | summing past the flag; and adding subawards to prime obligations — **a subaward is a slice of a prime award already counted in `prime_contracts.csv`** |
| `native_passthrough.csv` | `amount_usd` | **only** rows with `amount_countable == 1`. `amount_countable` is a 0/1 FLAG, not a dollar column | summing past the flag; and adding pass-through dollars to either the prime or the subaward total — this file is a PROJECTION of `subawards.csv`, not new money |

### The subaward trap, in dollars

`subawards.csv` totals $45,624,073,879.27 across all 72,837 rows. **That figure must never be quoted.** The correct total is $24,413,436,422.47 over 54,719 rows. The money rule removes **$21,210,637,456.80** — 46.5% of the unfiltered figure.

And that corrected total is still **not additive with prime contracting**. A subaward is a slice of a prime award Cedar already publishes. Federal dollars obligated = primes. Subawards say where those dollars went next.

### The pass-through trap

`native_passthrough.csv` totals $2,972,389,900.81 across 1,522 rows, of which only 1,135 rows / $869,328,591.38 are countable. FSRS is self-reported by the prime with no validation: **the RELATIONSHIP is the product, the AMOUNT carries a filter.**

## The duplicate allegations, re-measured

| table | rows | literal duplicate rows | groups | worst group | surplus $ | surplus rows at $0 |
|---|---:|---:|---:|---:|---:|---:|
| `faads_transactions.csv` | 60,661 | 1,001 | 946 | 6× | $75,078,206.00 | 3 |
| `native_passthrough.csv` | 1,522 | 116 | 20 | 44× | $123,621,558.43 | 0 |
| `subawards.csv` | 72,837 | 10,770 | 2,933 | 22× | $9,829,436,042.38 | 555 |

**Every count matches the allegation exactly. Three of the four findings behind them do not.**

### `faads_*` — distinct transactions, not repeated ones

Asked of the SOURCE, not inferred from the output:

| staged object | rows | distinct `assistance_transaction_unique_key` | verdict |
|---|---:|---:|---|
| `ed_fy2007_archive.zip` | 344,401 | 344,401 | every row is a distinct transaction |
| `doi_fy2001.zip` | 6,951 | 6,951 | every row is a distinct transaction |
| `doi_fy2002.zip` | 6,842 | 6,842 | every row is a distinct transaction |
| `doi_fy2003.zip` | 8,180 | 8,180 | every row is a distinct transaction |
| `doi_fy2004.zip` | 10,703 | 10,703 | every row is a distinct transaction |
| `doi_fy2005.zip` | 9,088 | 9,088 | every row is a distinct transaction |
| `doi_fy2006.zip` | 9,235 | 9,235 | every row is a distinct transaction |
| `doi_fy2007.zip` | 9,662 | 9,662 | every row is a distinct transaction |

Source rows and distinct transaction keys are EQUAL in every object measured. The mapper `30_funding_pre2008.to_out_row` never carried `assistance_transaction_unique_key` or `modification_number`, so distinct transactions render identical. **De-duplicating these two tables would destroy $75,078,206.00 of real obligations** — the same mistake `prime_contracts.csv` came within one commit of, where 80,778 apparent duplicates went to zero without a row being removed.

### `subawards.csv` — already flagged, never deleted

Every one of the literal duplicate rows carries `duplicate_status = 'exact_repeat_within_source'`. Row counts by status:

| duplicate_status | rows |
|---|---:|
| `primary` | 55,316 |
| `exact_repeat_within_source` | 16,675 |
| `superseded_by_primary_source` | 846 |

These are monthly SAM re-filings of one subaward, not repeated subawards — `121_pull_subawards_api.py` proved it on the FY2021 pull (one group is 93 re-filings of a single $57,500 subaward running 2022-08 to 2025-01, each with its own `subaward_sam_report_id`). They are RETAINED and FLAGGED, per Cedar's flag-never-delete rule. The flag is the fix; the delete would be the defect.

## Row conservation (C5)

| table | source rows read | disposition | rows | % |
|---|---:|---|---:|---:|
| `faads_transactions.csv` | 60,661 | `emitted` | 60,661 | 100.0 |
| `faads_transactions_all_agencies.csv` | 2,769,748 | `emitted` | 2,769,748 | 100.0 |
| `subawards.csv` | 7,380,186 | `emitted:primary_the_countable_subaward_filing` | 55,316 | 0.75 |
| `subawards.csv` | 7,380,186 | `retained:exact_repeat_within_source_flagged_never_deleted_not_countable` | 16,675 | 0.23 |
| `subawards.csv` | 7,380,186 | `retained:superseded_by_primary_source_flagged_never_deleted_not_countable` | 846 | 0.01 |
| `subawards.csv` | 7,380,186 | `rejected:no_native_party_on_either_side_of_the_subaward` | 7,307,349 | 99.01 |
| `native_passthrough.csv` | 72,837 | `emitted` | 1,522 | 2.09 |
| `native_passthrough.csv` | 72,837 | `rejected:direction_is_not_both_sides_native` | 71,311 | 97.9 |
| `native_passthrough.csv` | 72,837 | `rejected:one_side_unresolved_to_a_cedar_entity` | 4 | 0.01 |

## Why no primary key is declared

`GRAIN_WS1` in `code/512_build_dataset_contracts.py` is empty on purpose. A declared grain with no validated key is a release-blocking violation in `512`, and none of these four tables has a key that survives full-file validation:

- the `faads_*` pair has no identifying column at all — the source published one and the mapper dropped it. `30_funding_pre2008.py` now carries both columns; the re-extract is queued in `review/OWNER_DECISION_QUEUE.md` and has not run.
- `subawards.csv` retains byte-identical repeat filings on purpose and carries no per-occurrence ordinal. `45_promote_subawards.identity_key` is unique across all 55,316 `primary` rows and only there.
- `native_passthrough.csv` inherits both problems from its parent.

> **A downstream fragility worth naming:** `faads_entity_attribution.csv` keys 29,594 attributions to `faads_row_id`, which is the ROW POSITION in `faads_transactions_all_agencies.csv`. The queued rebuild that restores the transaction key will also re-order that file. The attributions must be re-pointed in the same pass or they silently move to different transactions.

<!-- BEGIN GRAIN-WS4 -->

## `funding` — the CROSS-TABLE paths, and the FY2007 seam

*Appended 2026-09-01 by workstream GRAIN-WS4 (`code/730_ws4_grain_money_conservation.py`). Re-measured from the live files on every run.* **This file is written WHOLESALE by `574`, which will delete this section; re-run `730` to restore it.**

The section above states what a buyer may total WITHIN each funding table. It does not say what happens when two of them are loaded together, and that is where the largest unstated double-count in this dataset lives.

### THE FY2007 SEAM — the one nobody had measured

`faads_transactions_all_agencies.csv` covers **FY2001–2007**. `federal_funding_transactions.csv` covers **FY2007–2026**. **They both hold FY2007**, and it is not a token overlap:

| | rows | obligations |
|---|---:|---:|
| `faads_transactions_all_agencies.csv` FY2007 | 774,755 | $475,359,703,132 |
| `federal_funding_transactions.csv` FY2007 | 11,443 | $2,189,838,446 |
| …of which sits on a FAIN the faads file ALSO carries | | **$2,165,856,969** (98.9%) |

**98.9% of the FY2007 dollars in the modern table are the same awards the archive table already carries.** A buyer building a FY2001–FY2026 series by stacking the two files double-counts FY2007. Stack them at **FY2001–2006 from the archive, FY2007 onward from `federal_funding_transactions.csv`** — the modern table is the attributed one, so the seam belongs on its side.

### `faads_transactions_all_agencies.csv` IS NOT A NATIVE TABLE

`tribe_id` is blank on **all 2,769,748 rows** and its $1,830,639,317,708 is the WHOLE federal assistance universe for FY2001–2007: every recipient in the country, Native and not, unfiltered. **It must never be quoted as money reaching Indian Country, and no ratio to a Native total is meaningful because the file contains no attribution to divide by.** `faads_transactions.csv` (60,661 rows, $9,348,473,200, FY2001–2007) is the *Interior* slice of that same file, carried into it verbatim — an AGENCY filter, not a Native one; its `tribe_id` is blank on all 60,661 rows too. Never add the two. The Native attribution for these years lives OUTSIDE both files, in `faads_entity_attribution.csv` (29,594 rows, FY2001–06). The Native-attributed figure Cedar publishes for the modern era is $167,692,910,442 over 547,586 rows of `federal_funding_transactions.csv` (`tribe_id` populated, `excluded_flag != 1`, FY2007–2026) — a different PERIOD as well as a different population, so it is not the denominator of anything above.

### The four ROLL-UPS and PROJECTIONS that are not new money

| table | measure | it is a roll-up / projection of | never add to |
|---|---|---|---|
| `federal_funding_tribe_year_panel.csv` | `total_obligated_usd` = $107,047,741,120 over 5,496 (tribe, year) cells, 364,095 transactions | `federal_funding_transactions.csv`, after its attribution and exclusion filters | the transaction table, and its own `obl_type_*` columns, which decompose `total_obligated_usd` and sum back to it |
| `faads_entity_attribution.csv` | `obligated_usd` = $4,721,685,550 over 29,594 rows | `faads_transactions_all_agencies.csv` — the dollar is carried verbatim onto an attribution row | either faads table |
| `native_passthrough_pairs.csv` | `countable_usd` = $869,328,591 over 307 entity pairs | the countable rows of `native_passthrough.csv` — it reconciles to the cent | `native_passthrough.csv` |
| `bie_uio_dollars_by_entity.csv` | `total_usd` = $3,905,609,834 over 114 entities | **FIVE DATASETS AT ONCE** (see below) | anything |

### `bie_uio_dollars_by_entity.csv` — a cross-dataset roll-up, and it double-counts inside itself

| component | dollars | already published as |
|---|---:|---|
| `usd_federal_funding` | $3,537,539,150 | `federal_funding_transactions.csv` |
| `usd_prime_contracts` | $235,304,731 | `prime_contracts.csv` |
| `usd_faads_all_agencies` | $120,183,074 | `faads_transactions_all_agencies.csv` |
| `usd_subawards` | $12,582,879 | `subawards.csv` — **and a subaward is a SLICE of a prime already counted in the row above it** |
| `usd_nonprofit_990` | $0 | `np_*` |
| **`total_usd`** | **$3,905,609,834** | the sum of the five |

`total_usd` is a **PROGRAMME-EXPOSURE MEASURE, not a dollar total**: it adds an assistance obligation, a contract obligation and a subaward slice of that same contract, which are three different things and, for the subaward column, partly the same dollar twice. $12,582,879 of it is inside `usd_prime_contracts` by construction, and `usd_faads_all_agencies` straddles the FY2007 seam with `usd_federal_funding`. Read the components; never quote the total as money received.

### `native_passthrough.csv` — rebuilt, and what changed

Rebuilt 2026-09-01 by GRAIN-WS4: **1,522 rows**, was 1,262 and 20% incomplete since 2026-08-12. `amount_usd` is additive **only** at `amount_countable == 1` — 1,135 rows, **$869,328,591**, against $2,972,389,901 unfiltered. The filter now removes $2,103,061,309.

The table carries **116 literal duplicate rows**, inherited from `subawards.csv`'s retained monthly re-filings. 110 of them already carry `amount_countable = 0`, so the money rule excludes them without anything being deleted. The remaining **6 rows, $2,751,845**, are countable AND repeated — that is the entire exposure, and it is the one number a buyer needs. **The fix is not a delete:** `81` collapses `subawards.duplicate_status` and `subaward_exceeds_prime_flag` into a single 0/1 flag and drops both source columns, so the file cannot say WHICH filter failed. Carrying `duplicate_status` through would make the de-dupe key statable and cost one line.

> `amount_countable` is a **0/1 FLAG, not money**. `517.MONEY_HINTS` matches the substring `amount` and counts it as a money column, which is why this table reports one more money column than it has. Flagged by GRAIN-WS1, still open, owner: whoever holds `517`.

<!-- END GRAIN-WS4 -->

<!-- BEGIN GRAIN-WS5 -->

# What a buyer may total — `contractors`, `nonprofits`, `deals`

*Appended 2026-09-01 by workstream GRAIN-WS5. Every number is re-measured by
`py -3 code/731_ws5_grain_contractors_nonprofits_deals.py measure`, and
`verify` exits 1 when one of them stops being true. The prose lives in
`docs/WS5_GRAIN_AND_SOURCES.md`; this is the one-line answer per table.*

## The one-line answer per table

| table | additive measure | sum it at | what double-counts |
|---|---|---|---|
| `contractor_ranking.csv` | `firm_obligations_usd` **and only the `firm_*` family** | one row = one operating company of one owner, tier A only. Key `(owner_entity_id, operating_company_seq)` | **every `owner_*` column.** They are OWNER-grain attributes repeated on every operating-company row of that owner — row-summing `owner_obligations_usd` gives $6,535.96B against a true $176.74B, a **36.98× inflation** over 283 owners. And the whole table is a **lossless partition of `prime_contracts.csv`**'s tier-A attributed slice: $176.74B on both sides, agreeing to $0.04. Never sum it alongside that file and never union them |
| `np_schedule_i_grants.csv` | `cash_grant_usd` | one Schedule I Part II grant LINE. **No key validates** — see the refusal below | `np_schedule_i_filers.part2_cash_grant_total_usd`. THE SAME MONEY AT TWO GRAINS and it reconciles to the dollar, $16,439,532,633 on both sides, and all 10,314 returns reconcile individually. Also never add it to `federal_funding_transactions.csv` / `faads_*` / `native_passthrough.csv` |
| `deals_classified.csv` | `Announced_Value_USD` | one deal EVENT. Key `Deal_ID`, 935 rows | **any of the nine `deals_*_additions.csv` files.** 790 of their 790 rows are already in this table — $22.67B against a $45.20B headline. And 618 of 935 rows carry a `Value_Type` naming a FEDERAL award, $6.87B Cedar already ships in `funding` and `contractors` |
| `deals_*_additions.csv` (all nine) | `Announced_Value_USD` | one deal event added by one staging pass | `deals_classified.csv`, and each other. All nine are individually safe to aggregate and **no two of them are safe together** |
| `tribal_resolution_financings.csv` | **NONE. This table has no money column.** | one retrieved document naming a financing AUTHORISATION | `principal_amount_text` and `pledged_revenues_text` are FREE TEXT (`517.MONEY_HINTS` matches the substring `amount` and calls them money; they are not) and both are blank on the only row. And `financing_status` is AUTHORIZED on the whole table: a council resolution PERMITS a transaction, it does not close or fund one. Never sum with `nigc_declination_letters.csv`, `gaming_financing_events.csv` or `tribal_bond_issuances.csv` — `nigc_declination_cross_reference` exists precisely so an authorisation and an NIGC review of ONE transaction are not counted as two |

### The owner-grain trap, in dollars

`contractor_ranking.csv` looks like a firm table and is half an owner table. Row-summed:

| statement | measured |
|---|---:|
| `SUM(firm_obligations_usd)` over every row | **$176,743,066,195.69** |
| `prime_contracts.csv`, tier-A attributed `total_obligations` | $176,743,066,195.73 |
| difference | $0.04 |
| `SUM(owner_obligations_usd)` over every row | $6,535,955,756,591.51 |
| the same, over distinct `owner_entity_id` | $176,743,066,195.70 |
| **inflation if row-summed**, over 283 owners | **36.98×** |

`owner_rank` is an owner attribute too, and it is recomputed every build. So is
`operating_company_seq`, which is a POSITION within the owner in descending
`firm_obligations_usd` — join on `operating_company_uei` if you need something
stable across vintages.

### The Schedule I refusal, and why it is not a de-dupe

`np_schedule_i_grants.csv` carries 101 literal duplicate rows in 90 groups over
58,685. **They are not duplicates.** 11 `object_id`s carry a collision and
**0** of them appear more than once in `np_schedule_i_filers.csv` — so every
group sits inside ONE return that was parsed exactly once, and the FILER listed
the grant line twice. First Nations Development Institute lists two $20,000
Economic Development grants to Seneca Nation of Indians on its FY2017 return
and both are real.

**A de-dupe deletes $2,089,185 of real grants.** The fix is a LINE ORDINAL, not
a DELETE: `132.parse_one` walks `RecipientTable` in document order and records
none. One column — `schedule_i_line_seq`, 1..n within `object_id` — makes
`(object_id, schedule_i_line_seq)` unique and takes the count to zero without
removing a row. Same shape as `430`'s fix for `prime_contracts` and as
`operating_company_seq` above.

And on the pass-through question specifically: a Schedule I grant is money the
FILER GRANTED OUT. Where the filer received a federal award and re-granted it,
that dollar is in the funding dataset AND here. Cedar's shape for that is
`native_passthrough.csv`'s directed edge plus its `amount_countable` flag;
Schedule I carries no such flag. So total it as GRANTS MADE BY NONPROFITS,
never add it to federal obligations, and never call the sum "money reaching
Indian Country".

### The deals dataset originates rather than collates — and every row is sourced

`docs/PUBLICATION_POLICY.md` asks for a source on every row of the one dataset
Cedar originates. Measured on all 935 rows of `deals_classified.csv`:

| | rows | share |
|---|---:|---:|
| two independent source URLs | 651 | 69.6% |
| one source URL | 284 | 30.4% |
| **no source URL at all** | **0** | **0.0%** |

61 distinct hosts; 662 rows (70.8%) cite a `.gov` source, led by
`broadbandusa.ntia.gov` (272), `hud.gov` (224) and `eda.gov` (51). The largest
non-government sources are the ANCSA STAR portal (77) and *Tribal Business
News* (65). This is a coverage fact about the ledger as it stands, not a claim
that every URL still resolves.

<!-- END GRAIN-WS5 -->

<!-- BEGIN INT-2-GAMING -->
## Gaming — what a buyer may total, and the three that never sum

*Appended 2026-09-01 by workstream INT-2 (`code/586`, `code/588`). Re-measured
from the live files.*

### The self-published layer is not the regulator layer

| table | rows | additive? | what double-counts |
|---|---:|---|---|
| `gaming_capacity_official.csv` | 6,649 | yes, WITHIN one `measurement_status` | **never pool `reported_revenue`, `reported_measurement` and `authorization`.** An authorization is a compact CEILING — what a tribe MAY operate — and summing it with counts of what exists produces a number that describes nothing. Metric names carry `_authorized_max` so the distinction survives any filter. |
| `gaming_property_self_published_claims.csv` | 270 | **NO** | **A MACHINE COUNT A CASINO ADVERTISES IS A CLAIM, NOT A MEASUREMENT.** 162 of the 270 are BOUNDS ("more than 1,000 slots"), not counts. Every row carries `value_is_bounded` and a `not_summable_with` naming the series it must never join. 9 rows also appear in `gaming_property_site_observations.csv` and are FLAGGED, not dropped — filter on `also_in_gaming_property_site_observations` before combining the two. |
| `gaming_property_capacity_history.csv` · `gaming_facility_metrics.csv` | — | **licensed, never published** | Casino City vendor panel. Internal fact-checking only. |
| `nigc_document_surface.csv` | 7,930 | it is a COUNT OF MEMBERSHIPS, not of documents | 7,930 (category, document) memberships over **4,071 distinct documents**. **Never sum it against `nigc_ordinances.csv` (1,155) or `nigc_declination_letters.csv` (327)** — those are instrument tables and this is the index that measures them. Count documents with `COUNT(DISTINCT document_slug)`. |
| `nigc_enforcement_actions.csv` | 362 | one row = one DOCUMENT | Not one row per violation. One matter routinely yields an NOV *and* a settlement agreement — Squaxin Island NOV-06-07 and SA-06-07 are two rows about one event. Counting rows counts documents; count matters by `action_code` stem. |

### The three FAC measures that never sum

Named because `review/sealed_state_typed_rows_2026-08-26.csv` holds ten
hand-typed NV/ND/KS figures across all three and totalling them triple-counts
the same dollar:

| measure | what it is | why it is not the others |
|---|---|---|
| `CASINO_ENTERPRISE_FUND_REVENUE` | what the gaming enterprise EARNED in the period | gross to the enterprise, before anything moves |
| `CASINO_DISTRIBUTION_TO_TRIBE` | cash actually TRANSFERRED to the tribal government | a subset of revenue, already counted inside it |
| `CASINO_PAYABLE_TO_TRIBE` | an obligation RECORDED and not yet paid | a balance-sheet position, not a flow — adding it to a distribution counts the same dollar in the year it was owed and again in the year it was paid |

**Sum at most one of the three, and say which.** A single tribe-year can carry
all three legitimately, and their sum is meaningless.
<!-- END INT-2-GAMING -->
