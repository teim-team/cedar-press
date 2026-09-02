# What a buyer may total — `funding` and `subcontracting`

*Generated 2026-09-02 by `code/574_ws1_money_and_conservation.py`. Every number below is re-measured from the live files and from the staged source objects on each run. Regenerate rather than edit.*

## The one-line answer per table

| table | additive measure | sum it at | what double-counts |
|---|---|---|---|
| `faads_transactions.csv` | `obligated_usd` | one row = one federal assistance TRANSACTION (a modification). Sum freely; group by `award_id_fain` to reach award level | nothing internal. **Never add it to `faads_transactions_all_agencies.csv`** — those 60,661 rows are carried into that file verbatim |
| `faads_transactions_all_agencies.csv` | `obligated_usd` | same grain; this file is the SUPERSET (Interior slice + 10 more agencies, FY2001–07) | adding the Interior file to it; and joining on `tribe_id`/`cedar_uid`, which are blank on every row |
| `subawards.csv` | `subaward_amount` | **only** rows with `duplicate_status == 'primary'` AND `subaward_exceeds_prime_flag != 'yes'` | summing past the flag; and adding subawards to prime obligations — **a subaward is a slice of a prime award already counted in `prime_contracts.csv`** |
| `native_passthrough.csv` | `amount_usd` | **only** rows with `amount_countable == 1`. `amount_countable` is a 0/1 FLAG, not a dollar column | summing past the flag; and adding pass-through dollars to either the prime or the subaward total — this file is a PROJECTION of `subawards.csv`, not new money |

### The subaward trap, in dollars

`subawards.csv` totals $47,301,660,819.78 across all 76,859 rows. **That figure must never be quoted.** The correct total is $25,864,997,128.19 over 58,117 rows. The money rule removes **$21,436,663,691.59**.

**State the denominator, every time.** That same $21,436,663,691.59 is **45.3% of the unfiltered $47,301,660,819.78** and **82.9% of the correct $25,864,997,128.19**. Codex caught the pair of numbers loose in the handoff — the sample README quoted one and the product descriptor the other — and a buyer holding both correctly concluded that one of them had to be wrong. **An overstatement is measured against the truth, so the number to quote is 82.9%: summing unfiltered lands you that far above the real total.** The other figure is the share of the inflated total that is spurious, which is a different and much less alarming-sounding sentence about the same error, and is not what a warning is for.

And that corrected total is still **not additive with prime contracting**. A subaward is a slice of a prime award Cedar already publishes. Federal dollars obligated = primes. Subawards say where those dollars went next.

### The pass-through trap

`native_passthrough.csv` totals $3,209,170,541.63 across 1,663 rows, of which only 1,259 rows / $1,050,719,668.88 are countable. FSRS is self-reported by the prime with no validation: **the RELATIONSHIP is the product, the AMOUNT carries a filter.**

## The duplicate allegations, re-measured

| table | rows | literal duplicate rows | groups | worst group | surplus $ | surplus rows at $0 |
|---|---:|---:|---:|---:|---:|---:|
| `faads_transactions.csv` | 60,661 | 0 | 0 | 0× | $0.00 | 0 |
| `faads_transactions_all_agencies.csv` | 2,769,748 | 3,441 | 3,027 | 10× | $7,427,641,526.00 | 65 |
| `native_passthrough.csv` | 1,663 | 0 | 0 | 0× | $0.00 | 0 |
| `subawards.csv` | 76,859 | 0 | 0 | 0× | $0.00 | 0 |

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

Source rows and distinct transaction keys are EQUAL in every object measured. The mapper `30_funding_pre2008.to_out_row` never carried `assistance_transaction_unique_key` or `modification_number`, so distinct transactions render identical. **De-duplicating these two tables would destroy $7,427,641,526.00 of real obligations** — the same mistake `prime_contracts.csv` came within one commit of, where 80,778 apparent duplicates went to zero without a row being removed.

### `subawards.csv` — already flagged, never deleted

Every one of the literal duplicate rows carries `duplicate_status = 'exact_repeat_within_source'`. Row counts by status:

| duplicate_status | rows |
|---|---:|
| `primary` | 58,731 |
| `exact_repeat_within_source` | 17,282 |
| `superseded_by_primary_source` | 846 |

These are monthly SAM re-filings of one subaward, not repeated subawards — `121_pull_subawards_api.py` proved it on the FY2021 pull (one group is 93 re-filings of a single $57,500 subaward running 2022-08 to 2025-01, each with its own `subaward_sam_report_id`). They are RETAINED and FLAGGED, per Cedar's flag-never-delete rule. The flag is the fix; the delete would be the defect.

## Row conservation (C5)

| table | source rows read | disposition | rows | % |
|---|---:|---|---:|---:|
| `faads_transactions.csv` | 60,661 | `emitted` | 60,661 | 100.0 |
| `faads_transactions_all_agencies.csv` | 2,769,748 | `emitted` | 2,769,748 | 100.0 |
| `subawards.csv` | 7,380,186 | `emitted:primary_the_countable_subaward_filing` | 58,731 | 0.8 |
| `subawards.csv` | 7,380,186 | `retained:exact_repeat_within_source_flagged_never_deleted_not_countable` | 17,282 | 0.23 |
| `subawards.csv` | 7,380,186 | `retained:superseded_by_primary_source_flagged_never_deleted_not_countable` | 846 | 0.01 |
| `subawards.csv` | 7,380,186 | `rejected:no_native_party_on_either_side_of_the_subaward` | 7,303,327 | 98.96 |
| `native_passthrough.csv` | 76,859 | `emitted` | 1,663 | 2.16 |
| `native_passthrough.csv` | 76,859 | `rejected:direction_is_not_both_sides_native` | 75,192 | 97.83 |
| `native_passthrough.csv` | 76,859 | `rejected:one_side_unresolved_to_a_cedar_entity` | 4 | 0.01 |

## The keys — three of four declared, one REFUSED

*This section replaced 'Why no primary key is declared' on 2026-09-02. It said `GRAIN_WS1` was empty on purpose and that none of the four tables had a key that survives full-file validation. That was true when it was written and is now true of one table.* Every line below is re-measured from the live files by this script; `512_build_dataset_contracts.py` re-validates all four against the files on every run and turns a broken promise into a release-blocking violation.

| table | primary key | measured |
|---|---|---|
| `faads_transactions.csv` | `assistance_transaction_unique_key` | unique and non-blank on all 60,661 rows |
| `faads_transactions_all_agencies.csv` | **REFUSED** — none exists | `assistance_transaction_unique_key` present on 825,754 of 2,769,748 rows and unique there; BLANK on 1,943,994. Refusal re-measured by `512` every run |
| `subawards.csv` | `source_dataset` + `subaward_source_record_id` | unique and non-blank on all 76,859 rows |
| `native_passthrough.csv` | `source_dataset` + `subaward_source_record_id` | unique and non-blank on all 1,663 rows |

**`subawards.csv` — the key was in the source all along.** FSRS publishes `subaward_sam_report_id`, one UUID per SAM filing, and `94.build_row` read 26 of the extract's 118 columns and dropped it. `910_subaward_report_id_backfill.py` streamed 8.48M rows of the staged zips already on disk, joined them on `45.identity_key` and recovered it for 75,861 rows; the 998 HigherGov rows use HigherGov's own per-subcontract permalink, already carried in `source_url`. `source_dataset` is the second half of the key because 347 rows are ONE filing that Cedar holds twice, from two of its own pulls, and both correctly carry the same UUID. **Byte-identical whole rows went 10,770 → 0 with zero rows removed and the money unchanged to the cent** — the third time in this project an allegation of literal duplicates has turned out to be dropped identity rather than repeated facts.

**`faads_transactions_all_agencies.csv` — REFUSED, and re-checked.** The grain IS declared; the primary key is empty and the refusal is recorded in `KEY_REFUSED` in `512`. 825,754 of 2,769,748 rows carry `assistance_transaction_unique_key` and it is unique with zero collisions where present; it is blank on the 1,943,994 FY2001–2006 rows of the nine non-Interior agencies because `30.COLUMNS` requested a 20-column subset and the key is not in the bytes on disk. **No re-extract can recover it** — only a fresh 112-column pull of those 54 agency-years, merged BY CONTENT so the 29,594 position-keyed attributions do not move. Until then the refusal is re-measured on every run of `512`: if any refused candidate becomes unique, or the 3,441 byte-identical rows change count, the declaration breaks. `code/912_selftest_refusal_gates.py` proves those two checks fire on a synthetic violation.

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

<!-- BEGIN UPSTREAM -->
## The Schedule I refusal is CLOSED, and the line ordinal exists

*Appended 2026-09-01 by workstream UPSTREAM. Re-measured by
`py -3 code/781_upstream_grain_columns.py --check`.*

The GRAIN-WS5 section above prescribes the fix and is correct in every
particular; this records that it has been applied, because that block says
`np_schedule_i_grants.csv` has **no key that validates** and it now has one.

| statement | before | after |
|---|---:|---:|
| rows | 58,685 | **58,685** |
| whole-row duplicates | 101 | **0** |
| grant dollars a de-dupe would have deleted | $2,089,185 | **$0 — no row was deleted** |
| validated primary key | none | **`(object_id, schedule_i_line_seq)`** |
| `517` export class | ROW_LEVEL_ONLY | **SAFE_TO_AGGREGATE** |

`schedule_i_line_seq` is 1..n within `object_id` in document order, exactly as
WS5 specified. **It changes no totalling rule above.** `cash_grant_usd` still
reconciles to `np_schedule_i_filers.part2_cash_grant_total_usd` at
$16,439,532,633 on both sides, still must never be added to
`federal_funding_transactions.csv` / `faads_*` / `native_passthrough.csv`, and
is still GRANTS MADE BY NONPROFITS rather than money reaching Indian Country.
What changed is that a buyer can now key the table and see that the two
$20,000 First Nations Development Institute grants to the Seneca Nation are
two grants.

`132` was fixed in the same pass so a rebuild reproduces the column. **It
cannot be run today**: both its XML caches (`data/raw/external/irs990_schedc
/xml`, `data/raw/external/irs990_grantee/xml`) hold **zero files**, so a run
would write an empty table over 58,685 real rows. The column was therefore
added in place by `code/781`, which refuses to write if a single column would
go missing or if any colliding group turned out to span a return
`np_schedule_i_filers.csv` holds more than once.

### `517.MONEY_HINTS` is fixed — the note on `tribal_resolution_financings.csv` above

The WS5 row for `tribal_resolution_financings.csv` records that
`517.MONEY_HINTS` substring-matches `amount` and calls `principal_amount_text`
and `pledged_revenues_text` money columns. Two workstreams flagged that and
nobody owned it. `517` now carries `MONEY_ANTI_HINTS`: a column whose name ends
in `_text`, `_basis`, `_type`, `_date`, `_flag`, `_countable`, `_cnt`, `_note`,
`_quote`, `_url` and the rest, or begins `is_` / `has_` / `n_`, is not money
however it matches. Measured across every shippable header: **202 names matched
`MONEY_HINTS` and 27 of them were this**, including `amount_countable` — the
0/1 flag on `native_passthrough.csv` that started the complaint — plus
`payment_date`, `obligation_type`, `Value_Type` and thirteen `*_value_basis`
columns. `native_passthrough.csv` still reports `amount_usd`, which is real
money: the fix removes the false positives and not the true one.
<!-- END UPSTREAM -->

<!-- BEGIN FAADS -->

# The FY2007 seam, as an exact set — and what the two faads tables are

*Appended 2026-09-01 by workstream FAADS (`code/791_faads_transaction_key_and_repoint.py`). Re-measured on every run of `791 seam`; enforced by `791 seam --verify`.* **This file is written WHOLESALE by `574`, which preserves only marked blocks; this section is inside `<!-- BEGIN FAADS -->` / `<!-- END FAADS -->` so it survives.**

## The FY2007 overlap is no longer an estimate

GRAIN-WS4 measured the seam at **98.9% of the modern table's FY2007 dollars** and could not do better, because neither side carried a transaction key. `30_funding_pre2008.to_out_row` dropped `assistance_transaction_unique_key`; the re-extract on 2026-09-01 restored it on every FY2007 row. Both sides now carry the same source identity, so the overlap is a **set intersection, not a ratio**:

| | rows | obligations |
|---|---:|---:|
| `faads_transactions_all_agencies.csv` FY2007 | 774,755 | $475,359,703,131.83 |
| …carrying `assistance_transaction_unique_key` | **774,755 (100%)** | |
| `federal_funding_transactions.csv` FY2007 | 11,443 | $2,189,838,445.60 |
| **…that are the SAME TRANSACTION as an archive row** | **11,063** | **$2,165,856,968.60** |
| …present only in the modern table | 380 | $23,981,477.00 |

WS4's dollar estimate was right to the cent; what is new is that the overlap is now **11,063 identified rows** a consumer can subtract by key, instead of a percentage they have to trust.

## The rule, and what enforces it

**Stack FY2001–2006 from `faads_transactions_all_agencies.csv` and FY2007 onward from `federal_funding_transactions.csv`.** The modern table is the attributed one, so the seam belongs on its side. Loading both files whole double-counts 11,063 FY2007 transactions and $2,165,856,969.

No code can stop a buyer adding two files together. What **is** enforced, by `py -3 code/791_faads_transaction_key_and_repoint.py seam --verify` (exit 1 on breach), is the property that makes the rule checkable rather than advisory:

1. **every FY2007 row of the archive table carries a transaction key**, so the overlap stays a set — if a future rebuild drops the column again this fails immediately and loudly instead of the seam quietly reverting to an estimate;
2. **the overlap is exactly the recorded row count and dollar figure**, re-measured against `docs/schema/faads_fy2007_seam.json`, which is written for consumers to subtract programmatically.

## Neither faads table is a Native table — restated, because the re-extract did not change it

`faads_transactions_all_agencies.csv`: `tribe_id` blank on **all 2,769,748 rows**; its $1,830,639,317,708 is the whole federal assistance universe for FY2001–2007, every recipient in the country. `faads_transactions.csv`: 60,661 rows, $9,348,473,200, `tribe_id` blank on all of them — an **agency** filter (Interior), not a Native one, and carried verbatim into the all-agencies file, so **never add the two**. The Native attribution for these years lives outside both files, in `faads_entity_attribution.csv` (29,594 rows, FY2001–06, $4,721,685,550 carried verbatim off the transactions — a projection, never new money).

## What a buyer may total, now that the grain is stated for one of the pair

- **`faads_transactions.csv` — SAFE at transaction grain.** `assistance_transaction_unique_key` is unique on all 60,661 rows (0 collisions, 0 blanks) and the grain is declared in `512.GRAIN_FAADS`. The 1,001 rows it was blocked on as literal duplicates are **1,001 distinct source transactions**; the count is 0 now and **not one row was deleted**.
- **`faads_transactions_all_agencies.csv` — still ROW-LEVEL ONLY, and by a knowable amount.** The key is present on 825,754 of 2,769,748 rows (29.8%: every FY2007 row, every Interior row) and unique where present. It is blank on the 1,943,994 FY2001–2006 rows of the other nine agencies because those staged objects were requested with a 20-column subset and **physically lack the column** — the USAspending Award Data Archive, the only full-column route, begins at FY2007. **3,441 rows** remain byte-identical to another row across all 27 columns, all of them inside that unkeyed region. `obligated_usd` is additive at transaction grain; the residual exposure a buyer carries is those 3,441 rows.

**Nothing was de-duplicated.** Whole-row duplicates fell 179,259 → 3,441 on the all-agencies table and 1,001 → 0 on the Interior table by **restoring an identity column, not by deleting a row**. A de-dupe would have destroyed $8,291,124,113 of real obligations — `ed_fy2007_archive.zip` holds 344,401 rows and 344,401 distinct keys, and the worst apparent group (445 identical UC Irvine rows) is 740 real transactions carrying modification numbers 0001–0740, 592 of them $0.

<!-- END FAADS -->

<!-- BEGIN GAMING-NR -->

## Gaming self-published claims — a marketing number is not a measurement (workstream GAMING-NR, 2026-09-01)

`gaming_property_self_published_assertions.csv` (622 rows) and `gaming_property_self_published_claims.csv` (270 rows) hold what a casino says about ITSELF on its own website — machine counts, hotel rooms, square footage, ownership and opening dates. Every row carries `assertion_class`, and every class is deliberately OUTSIDE `cedar_domain.MeasurementType`.

**A buyer may never sum either table against a regulator's figure.** Specifically, never against `gaming_capacity_official.csv` (regulator-reported capacity), `nigc_regional_ggr.csv` or `nigc_revenue_bands.csv` (NIGC), `state_gaming_observations.csv`, `wa_machine_allocations.csv`, or the Casino City vendor panel. A self-published count and a regulator count of the same floor are TWO CLAIMS ABOUT ONE THING, not two things; adding them doubles the floor, and preferring the larger is how a marketing number becomes a statistic.

Three further measured cautions on the claims table: 162 of 270 values are BOUNDED ("more than 1,000 slots") and a bound is not a count; 9 rows restate an observation that is already in `gaming_property_site_observations.csv`, so stacking the two files double counts them; and 229 were RECOVERED from a refusal pile by `code/383` and are published because a refusal that hides the claim is worse than one that labels it, not because they got better.

The grain is a claim occurrence, not a fact: two sentences on one page stating the same number about two different ballrooms are two rows, and collapsing them deletes a ballroom. See `512.GRAIN_GAMING_NR`.

`fac_audit_sefa_gaming_programs.csv` (1 row) carries `amount_expended`, which is a FEDERAL AWARD EXPENDITURE and is not gaming revenue of any kind. It may not be summed with any gaming money column, and it is additive only at (report_id, award_reference) — one SEFA line of one Single Audit.

<!-- END GAMING-NR -->

<!-- BEGIN INT-READY -->
## Gaming, lobbying and 990 Schedule C — three totals with one name, and one column family that carries no money at all

*Appended 2026-09-02 by workstream INT-READY (`code/960`, `code/961`,
`code/512`). Every figure re-measured with `csv.reader` from the live files on
the date shown; nothing is quoted from a build log.*

### `gaming_facilities.csv` gained eleven columns and NOT ONE DOLLAR — deliberately

`code/960` put the class and the revenue-bound path on the facility record. It
put **no money column there**, and the reason is a measurement rather than
caution:

| `measurement_status` in `gaming_revenue_bounds.csv` | rows | is it this property's money? |
|---|---:|---|
| `REGIONAL_GGR_CEILING` | 13,494 | **no** — a ceiling for the whole NIGC region, repeated on every property in it |
| `TRIBE_LEVEL_REVENUE` | 133 | no — and these rows carry no `facility_id` at all |
| `SINGLE_PROPERTY_ATTRIBUTED` | 115 | yes |
| `REPORTED_PROPERTY_REVENUE` | 61 | yes |

**The two honest per-property statuses reach 11 of 787 ROWS (1.4%).**
*(Correction appended 2026-09-02 from outside this block, no other line touched: 787 is a row count. See `GAMING-DENOMINATOR-2026-09-02` at the foot of this file — the property denominator is 714, so this is nearer 1.54%.)* A
dollar column on the facility table would therefore be 98.6% blank, and the
cells a buyer *could* see would mostly be a regional ceiling — which, summed
across that region's properties, multiplies the region's entire GGR by its
property count. So the facility record carries `has_revenue_bound`,
`n_revenue_bound_fiscal_years`, `revenue_bound_strongest_status` and a
`revenue_bound_basis` that names the join and the rule, and the dollars stay
where their grain is stated.

**The rule for the bounds table itself:** `gaming_revenue_bounds.csv` is
**(facility | tribe, fiscal year, bound method)** grain. `revenue_lower_bound`,
`revenue_upper_bound`, `point_value`, `regional_total_usd` and
`known_property_sum_usd` may be **read per row and never summed across rows** —
not across facilities, not across years, and above all not across
`measurement_status`. Every row is tier B. 158 of 13,803 rows carry no
`facility_id`; a facility-keyed join silently drops them.

`state_revenue_disclosure_status = SEALED_BY_STATUTE_OR_COMPACT` is on **174 of
787 rows across seven states — AZ, CO, KS, MN, ND, NV, WI** — each with
the statute or compact clause quoted in `state_revenue_disclosure_basis`. A
blank there is `NOT_ASSESSED`, **not** evidence that the state publishes.

### Three tables answer "how much did tribal lobbying cost" and give three different numbers

All three are correct about different questions. **Adding any two of them
double-counts the same dollar.**

| table | column | total, measured 2026-09-02 | what one row is |
|---|---|---:|---|
| `lobbying_registrants.csv` | `spend_reported_usd` | **$645,052,868.51** (351 of 653 rows > 0) | one Senate LDA **registrant** — the firm, rolled up |
| `tribe_year_lobbying_panel.csv` | `total_lobbying_spend_usd` | **$680,561,640.52** | one (**entity**, filing year) |
| `native_entity_lobbying_disclosures.csv` | `spend_usd` | **$725,743,974.52** | one LDA **filing** — and `spend_usd` is `income_usd` + `expenses_usd`, two different reporting regimes stacked in one column |

Pick one and say which. The registrant rollup is the smallest because a
registrant is a firm and a firm's Native work is one slice of its filings; the
filing-grain total is the largest because a self-filer's `expenses_usd` and a
retained firm's `income_usd` are both in it.

**`spend_reported_usd` is not a measurement, it is a floor with a stated
ceiling.** The LDA reports in period **bands**, not exact figures.
`spend_sensitivity_percell_max_usd` totals **$650,383,870.30** and
`spend_sensitivity_naive_sum_usd` totals **$685,798,224.52** on the same 653
rows. Those three columns are the same money measured three ways and must
never be added to one another. `n_filings_reporting_no_dollar` is non-zero on
402 registrants: a $0 here often means *the filing reported no dollar figure*,
not *no money moved*.

### `nonprofit_schedule_c_lobbying.csv` — the headline already contains its parts

Registered into `lobbying` on 2026-09-02 (it was an orphan). 6,870 rows, one
per IRS 990 e-file **return**, keyed on `schedule_c_row_id`.

```
lobbying_usd_headline     $3,325,511   over 132 returns   <- the one to total
  total_lobbying_usd      $1,029,249   over  43 returns   (501(h) electors, Part II-A)
  nonelecting_lobbying_usd $2,296,262   over  89 returns   (Part II-B)
                          ----------
                          $3,325,511   exactly
```

**`lobbying_usd_headline` IS the union of the other two.** Summing the headline
with either part double-counts; summing it with both counts every dollar twice.
`direct_lobbying_usd` ($936,552) and `grassroots_lobbying_usd` ($92,697) are
components of `total_lobbying_usd`, not additions to it.
`political_expenditure_usd` ($1,277,338) is §527 political activity and is
**not lobbying** — it is a different line on a different part of the schedule
and never belongs in a lobbying total.

**And no Schedule C total may be published without
`nonprofit_schedule_c_coverage.csv` beside it.** `coverage_status` is `PARTIAL`
on all ten index years: **32,218 returns were indexed as targets and 6,870 were
retrieved — 21.3%.** The 25,348 shortfall is Cedar's own fetch backlog and the
table says so verbatim ("NOT an absence at the IRS"). A buyer given $3.3M
without that table reads a download queue as evidence about Native nonprofits.
<!-- END INT-READY -->

<!-- BEGIN GEO -->

## Geography — a shared county code is NOT permission to sum (ADR-015 workstream INT)

*Appended 2026-09-02 by `code/875_geo_money_rules_section.py`. Every figure is re-read from the measurement JSONs that `870`–`874` write; regenerate rather than edit.* **This file is written WHOLESALE by `574`, which preserves only marked blocks; this section sits inside a GEO marker pair so it survives that rewrite.**

### What changed, and why it is a new hazard

Before 2026-09-02, **1,070 rows** in `data/clean/` carried a joinable geographic key. Across the same population of transaction and asset tables they now number **4,295,674 of 4,768,577 (90.1%)**, concentrated in the four largest money tables Cedar publishes. Every one of those tables was already non-additive with the others, and every one of them is now trivially joinable to the others on `county_fips`.

**That is the hazard this section exists for.** A county code makes the forbidden sum easy, not legal. Nothing above in this file is relaxed by the geography axis; ADR-015 rule 4 restates it and this section makes it operational.

### The four geography columns, and the one rule that governs them

Each promoted table carries TWO county keys, never one:

| column | answers |
|---|---|
| `geo_recipient_county_fips` | where the AWARDEE is |
| `geo_pop_county_fips` | where the WORK WAS PERFORMED |

**ADR-015 rule 1: these are not interchangeable and must never be coalesced.** They disagree on a large minority of awards, and that disagreement IS the measure the axis was built for. A query that `COALESCE`s them to a single `county` column has destroyed the product.

On `subawards.csv` the columns are named `geo_prime_award_recipient_county_fips` and `geo_prime_award_pop_county_fips` because they are the PRIME award's geography, not the subawardee's. The subawardee's county is not derivable from that table — it carries `sub_state` and no sub city, zip or county column at all.

### What may be totalled by county, per table

| table | rows | keyed EXACT | keyed DERIVED | unkeyed | any key |
|---|---:|---:|---:|---:|---:|
| `prime_contracts.csv` | 1,217,768 | 247,987 | 963,727 | 6,054 | 99.5% |
| `subawards.csv` | 76,859 | 12,140 | 0 | 64,719 | 15.8% |
| `federal_funding_transactions.csv` | 701,955 | 149,112 | 514,061 | 38,782 | 94.5% |
| `faads_transactions_all_agencies.csv` | 2,769,748 | 615,012 | 1,792,565 | 362,171 | 86.9% |

**`exact` means a federal record named the county for that award or that transaction.** `derived` means the row's own zip5 or city+state was resolved to its MODAL county in `geo_place_county_crosswalk.csv`, and the row carries `geo_*_place_dominance_share` and `geo_*_place_ambiguous` so a consumer can set its own threshold. A derived key is a best guess with its confidence attached. **Do not publish a county figure built mostly on derived keys without saying so** — on `prime_contracts.csv` that is 79.1% of rows.

### The additive rules, unchanged, restated for county grouping

1. **Within one table, group freely.** Summing `total_obligations` by `geo_pop_county_fips` over `prime_contracts.csv` is a valid partition of that table and `874` proves it to the cent.
2. **Across tables, never.** A county code does not make a subaward addable to a prime, `faads_transactions.csv` addable to `faads_transactions_all_agencies.csv`, or FY2007 addable across the seam between `faads_transactions_all_agencies.csv` and `federal_funding_transactions.csv`. Every rule above in this file still governs and county grouping changes none of them.
3. **Unkeyed is not zero.** Rows with no county key are unallocated, not absent. A county-level total plus the unallocated residual equals the table total; a county-level total on its own does not. The residual per table is in `docs/GEO_TWO_SUMS_STATS.json` and is republished on every run.
4. **A county is not a reservation (ADR-015 rule 2).** County FIPS is coarser than AIANNH: reservations span counties and counties contain fractions of reservations. Any county-level result about Indian Country ships labelled as an approximation. `geo_aiannh_dim.csv` carries all 864 TIGER 2024 AIANNH areas and `geo_aiannh_county_observed.csv` carries the 374 (AIANNH, county) pairs Cedar has actually observed — a floor, never a census, because county polygons are not on disk to intersect against.

### The ADR-015 difference measure, and the one rule people will break

`data/clean/geo_county_two_sums.csv` publishes, per (dataset, county), **two sums kept separate**:

- `pop_sum_usd` — money flowing TO the area, by place of performance
- `native_recipient_sum_usd` — money reaching Native entities there, by recipient county

**It publishes no difference column, on purpose (ADR-015 rule 3).** The difference is derivable in one subtraction and is meaningless without its bounds, so the bounds ride on every row: `native_sum_is_a_floor`, `signed_money_note`, `universe_note`, `county_is_not_a_reservation`, `never_sum_across_datasets`.

Three things that make a bare difference wrong:

- **The Native sum is a FLOOR.** It counts only recipients Cedar has attributed. Better matching moves it up and the difference down, never the other way. The difference is therefore a CEILING.
- **Obligations are SIGNED.** A deobligation is a negative row, so a county's Native sum can legitimately exceed its all-recipient sum. Only the ROW COUNTS nest.
- **Two of the three datasets are not the federal universe.** `prime_contracts.csv` and `federal_funding_transactions.csv` are Native-CANDIDATE corpora — their recipient universe was pulled from Native entity lists — so their place-of-performance sum for a county is *Cedar's corpus performed there*, not *all federal money there*. Only `faads_transactions_all_agencies.csv` is unfiltered, and only for FY2001–2007. Reading a difference on the other two as 'money that bypassed Native entities' is the single most likely misuse of this table.

| dataset | rows | obligations | Native rows | Native obligations | counties |
|---|---:|---:|---:|---:|---:|
| `faads_transactions_all_agencies.csv` | 2,769,748 | $1,830,639,317,707.66 | 29,594 | $4,721,685,550.00 | 3,501 |
| `prime_contracts.csv` | 1,217,768 | $310,005,258,661.21 | 888,862 | $244,765,639,853.72 | 2,249 |
| `federal_funding_transactions.csv` | 701,955 | $219,689,020,478.59 | 550,937 | $169,072,556,167.99 | 2,035 |

**Read down that table, never across it.** Three universes, three periods, and two of the three overlap at FY2007.

### Provenance

- `geo_award_county_crosswalk.csv` — 1,050,968 award keys, 1,045,397 with both sides filled, from the USAspending gapfill prime award summaries. Built by `870`.
- `geo_place_county_crosswalk.csv` — 42,650 places (zip5 and city+state) with modal county and dominance share, pooled over five local USAspending corpora. Built by `870`.
- `geo_county_dim.csv` — every county code the crosswalks reference, including USAspending's `SS000` state-wide placeholders, each labelled by `county_code_class`. Built by `870`.
- `geo_aiannh_dim.csv`, `geo_aiannh_county_observed.csv`, `geo_point_aiannh_assignment.csv` — TIGER/Line 2024 AIANNH and Cedar's geocoded points inside it. Built by `873`.
- `geo_county_two_sums.csv` — the two sums. Built by `874`, which proves the money and row partitions to the cent on every run.

<!-- END GEO -->

<!-- BEGIN SUBAWARD-FUNDING -->

## The subaward key, the two legs, and the one refusal (workstream SUBAWARD-FUNDING, 2026-09-02)

*Marked so it survives the wholesale rewrites `574` performs on this file. Every
number is re-checkable by the command named beside it.*

### `subawards.csv` now has a primary key, and it is two columns for a reason

    primary key   (source_dataset, subaward_source_record_id)
    check         py -3 code/910_subaward_report_id_backfill.py verify

**A row is one SUBAWARD FILING as ingested from one source**, not one subaward.
FFATA requires the prime to re-file an open subaward monthly; one $57,500
subaward is 93 rows spanning 2022-08 to 2025-01, and all 93 are real reporting
events. That is why the money rule is a filter and not a de-duplication.

`subaward_source_record_id` is the SOURCE's own record id, recovered, never
minted: the SAM filing UUID on 75,861 rows, HigherGov's per-subcontract
permalink (already in `source_url`, 998 of 998 distinct) on the other 998.
`source_dataset` is the second half because **347 rows are one filing Cedar
holds twice**, from `usaspending_fsrs_pull` and from `funding_forward_fill`.
Both carry the same UUID, correctly — it is one filing — and the second is
already flagged `superseded_by_primary_source` and already excluded from every
money total. **Do not read that pair as two subawards.**

### The duplicate allegation that was phantom, for the third time

| | before | after | rows deleted |
|---|---:|---:|---:|
| `subawards.csv` byte-identical whole rows | 10,770 | **0** | **0** |
| `native_passthrough.csv` byte-identical whole rows | 116 | **0** | **0** |
| `subawards.csv` `sum(subaward_amount)` | $47,301,660,819.78 | $47,301,660,819.78 | — |

Nothing was de-duplicated. The rows stopped being byte-identical because the
column that always separated them — the SAM report UUID the mapper dropped —
was put back. This is the same shape as `prime_contracts.csv` (80,778 alleged,
real answer zero) and `faads_transactions.csv` (1,001 alleged, real answer
zero). **Measure before you collapse anything.**

### A subaward has TWO legs and only one of them used to have a Cedar id

`cedar_uid` on this table is the PRIME's entity id — `503_identity.py stamp`
derives it from `prime_native_tribe_id`, the first of its preference columns
present in the header — so it is blank on the 43,282 rows whose only Native
party is the SUBAWARDEE. It is not wrong, it is half the table.

    prime_cedar_uid   the prime leg          33,503 rows
    sub_cedar_uid     the subawardee leg     44,945 rows
    at least one leg                         76,785 of 76,859 (99.90%)
    check   py -3 code/911_subaward_sub_leg_cedar_uid.py verify

**Never sum a money column after joining on both legs at once** — a row where
both legs are Native (1,663 of them, which is exactly `native_passthrough.csv`)
would be counted under two entities. Group by ONE leg, and say which.

### `faads_transactions_all_agencies.csv` — no key, and that is a declaration

`obligated_usd` IS additive at transaction grain across this file
($1,830,639,317,707.66, FY2001–2007). What is unavailable is the JOIN: no
primary key exists at any arity, because `30.COLUMNS` requested a 20-column
subset for 60 of the source objects and `assistance_transaction_unique_key` is
not in the bytes on disk for 1,943,994 rows. The refusal is recorded in
`KEY_REFUSED` in `512_build_dataset_contracts.py` and **re-measured against the
file on every run**: if a refused candidate becomes unique, or the 3,441
byte-identical rows change count, the declaration breaks and the table goes
back to blocking. `py -3 code/912_selftest_refusal_gates.py verify` proves both
checks fire on a synthetic violation.

Its export class is `AGGREGATE_ONLY_NO_KEY` — a fourth class added the same
day, because "a buyer may NOT total a column" was a false warning on $1.83T of
genuinely additive obligations, and a false warning teaches a buyer to ignore
the true ones.

### After any subaward promotion, run these, in this order

    py -3 code/121_pull_subawards_api.py ...            # the promotion
    py -3 code/910_subaward_report_id_backfill.py rescan
    py -3 code/910_subaward_report_id_backfill.py apply
    py -3 code/911_subaward_sub_leg_cedar_uid.py apply
    py -3 code/871_promote_geo_keys_contracts.py        # geography workstream
    py -3 code/81_build_passthrough_dataset.py

Registered in `cedar_pipeline.KNOWN_ORDERINGS`, because a promotion that stops
before them leaves the appended rows with a blank key — and blank collides with
blank, which is how this table came to have no key in the first place.

<!-- END SUBAWARD-FUNDING -->

<!-- BEGIN TRIBAL-DEBT -->
## Tribal debt — `tribal_debt_holdings`, `tribal_debt_obligors`, `tribal_debt_distress_events`

*Appended 2026-09-02 by `code/1082_tribal_debt_holdings_disclosure.py` (staged
in `data/staging/`, not yet in `data/clean/`). This block is inside
a marked block named TRIBAL-DEBT (BEGIN/END comment markers, written
without the literal syntax here so `574`'s scanner sees exactly ONE pair) so
its wholesale rewrite preserves it. Do not edit another workstream's block.*

### The one-line answer per table

| table | additive measure | sum it at | what double-counts |
|---|---|---|---|
| `tribal_debt_holdings.csv` | **none — there is no additive measure** | one row = ONE FUND'S POSITION in one instrument, as of one `report_period_end` | everything: across funds, across report periods, and against every other money column in Cedar |
| `tribal_debt_obligors.csv` | none. `max_single_fund_principal_usd` is a **maximum, not a total** | one row = one obligor | reading the max as a sum |
| `tribal_debt_distress_events.csv` | none — it is an event table | one row = one as-filed default/arrears flag on one instrument at one date | counting an instrument once per fund that holds it and calling it several events |

### Why `principal_usd` is the most dangerous column in this table

It is a real, audited, machine-readable dollar figure, and it is **a fraction
of an instrument, not the instrument**. Form N-PORT Item C reports what *this
fund* holds. Seventy-two different registered funds report a position in
Mohegan Tribal Gaming Authority paper; adding their balances produces a number
that is not the par of anything, is not Mohegan's debt, and is not even a
consistent slice of it, because the funds report on different period ends.

Three specific prohibitions, each of which would produce a plausible wrong
number:

1. **Never sum across funds.** Fund A and Fund B may hold the same CUSIP; they
   may also hold different tranches. Neither case makes their sum a par
   amount.
2. **Never sum across `report_period_end`.** The same position held for eight
   quarters is one position, not eight.
3. **Never add it to a deal value.** `deals_classified.Announced_Value_USD` and
   `tribal_bond_issuances.par_amount` describe the *whole* instrument at
   issuance. A holdings balance describes a slice of it years later. They are
   the same money counted at different grains, and the correct relationship
   between them is `<=`, not `+`.

### A bond principal is not revenue. Neither is a management fee.

There is no revenue column in any of these three tables, and that is not an
omission — **this seam produces no revenue figure at all**. It answers "who
holds the debt and on what terms", not "what does the property earn". Anyone
joining these tables to `gaming_facility_metrics` or `gaming_revenue_bounds`
must carry that distinction in the join, not in a footnote.

### Revenue from an audited bond disclosure is a THIRD evidence class

Where such a figure is ever obtained, it is not an NIGC figure and not a
casino's own marketing claim. It carries its own `assertion_class` and it must
**never** be summed against an NIGC regional ceiling: `gaming_revenue_bounds`
already records that a region total is an *upper bound on any one operation
inside it*, so adding a property figure to a regional figure adds a part to its
own whole. As of this build the class is declared and **zero facilities carry a
revenue figure through it** — see the coverage note in
`docs/TRIBAL_DEBT_HOLDINGS_BUILD_LOG.md`.

### `is_default_as_filed` is not a default

The flag is Form N-PORT Item C.9, reported by **the fund**, about the security.
It is the fund's characterisation for portfolio-reporting purposes. It is not a
court finding, not an acceleration, and not a corporate insolvency — **a tribal
obligor is a sovereign, and a tribal default is not a corporate default**. Any
use of this column must quote the instrument and the filing, must name the fund
as the speaker, and must not describe a nation's finances beyond what the
document states. Every row in `tribal_debt_distress_events.csv` carries that
caution in `sovereign_immunity_caution`.

### `not_summable_with` is populated on every row

Both `tribal_debt_holdings.csv` and `tribal_debt_obligors.csv` carry a
`not_summable_with` string naming the specific columns this data must never be
added to. `py -3 code/1082_tribal_debt_holdings_disclosure.py verify` fails
(exit 1) on invariant `I3_no_holding_asserts_a_summable_total` if any row loses
it, and `selftest` proves that check fires.
<!-- END TRIBAL-DEBT -->

<!-- BEGIN TRIBAL-DEBT-COURT -->
## Tribal debt in the courts - `tribal_debt_court_events`, `tribal_debt_court_dockets`

*Appended 2026-09-02 by `code/1110_tribal_debt_court_distress.py` (staged in
`data/staging/`, not in `data/clean/`). Companion to the TRIBAL-DEBT block
above, which covers the HOLDINGS side. This block has its own marker name so
`574`'s wholesale rewrite preserves both. Do not edit another workstream's
block.*

### The one-line answer per table

| table | additive measure | sum it at | what double-counts |
|---|---|---|---|
| `tribal_debt_court_events.csv` | **none** | one row = ONE EVENT TYPE in ONE COURT DOCUMENT | everything. Several sentences supporting one event type are ONE event; an appellate and a district opinion in one case are TWO documents about ONE dispute |
| `tribal_debt_court_dockets.csv` | **none** | one row = ONE DOCKET in ONE COURT | an appeal and its district case are two dockets and one dispute. Counting dockets is not counting disputes |

### `amount_as_recited` is not a debt figure

It is whatever dollar amount appears **inside the quoted sentence**, exactly as
the court wrote it. It is not normalised, not converted, not verified against
the instrument, and frequently it is a figure a party alleged rather than one a
court found. Never sum it, never chart it, and never place it beside
`tribal_debt_holdings.principal_usd`, `deals_classified.Announced_Value_USD` or
`tribal_bond_issuances.par_amount` - those describe an instrument, this
describes a sentence about one. `not_summable_with` says so on every row.

### AN EVENT IS NOT A RUNNING CONDITION

Every row is dated and every row carries `currency_caution` in full. A 2013
restructuring is a fact about 2013. **Nothing in this table says anything about
any nation's finances today**, and the newest event in it is from **2017**.
Presenting these rows without their date, or aggregating them into a per-nation
"distress" score, misrepresents every one of them.

### A DEFAULT IS NOT WHAT THIS TABLE MOSTLY CONTAINS

The largest single `event_type` is
`LITIGATION_OUTCOME_INSTRUMENT_HELD_VOID_OR_UNENFORCEABLE` (10 of 32). In
*Wells Fargo v. Lake of the Torches*, 658 F.3d 684 (7th Cir. 2011), the bond
indenture was held **void** as a management contract unapproved by the NIGC -
and in *Stifel v. Lac du Flambeau*, 807 F.3d 184 (7th Cir. 2015), on the same
paper, the resolutions were held **not** void. **A tribal obligor is a
sovereign and a tribal default is not a corporate default.** Read
`event_type`, `assertion_or_finding` and `verbatim_quote` together, or do not
use the row.

### A FILING IS A PARTY'S ASSERTION; A JUDGMENT IS A FINDING

`assertion_or_finding` is `ALLEGATION_BY_A_PARTY` (3), `COURT_FINDING` (2) or
`PROCEDURAL_RECORD` (27), with the cue that decided it in
`assertion_or_finding_basis`. **Only two rows in the whole table are a court
holding something.** Quoting a `PROCEDURAL_RECORD` or an
`ALLEGATION_BY_A_PARTY` row as though a court had found it is the single
easiest way to misuse this dataset.

### The join to the holdings register is on the ENTITY, never on the label

`joins_1082_holdings` is computed against `obligor_cedar_uid`, not against the
obligor label a fund's schedule of investments happened to print. Three of
`1082`'s fourteen obligors are reached. **Zero EVENT rows join** - the entities
with opinions and the entities with fund holdings are almost disjoint, and the
two tables' year ranges (opinions end 2017, N-PORT begins 2019) do not overlap
by a single year. Do not present them as one series.
<!-- END TRIBAL-DEBT-COURT -->


<!-- BEGIN LOBBY-SUPERSESSION -->
## The LDA amendment double-count, closed 2026-09-02 — and the FOURTH lobbying number that now exists

*Appended by `code/1091_lobby_amendment_supersession.py`. Every figure below
was re-measured with `csv.reader` from the live file on 2026-09-02; nothing is
quoted from a build log. Nothing outside these markers was touched.*

### What was wrong

`docs/METHODOLOGY_LOBBYING.md` described the cleaning sequence as *"amendments
applied over the originals they replace ... non-standard records
(registrations, terminations) set aside before any total is struck."*
**`native_entity_lobbying_disclosures.csv` had never done this.** An amended
LD-2 *restates* the period it amends, and the LDA publishes the amendment as a
**new filing with its own uuid** rather than replacing the original. Both ship.

`data/clean/cedar_export_safety.csv` marked the table `SAFE_TO_AGGREGATE /
aggregation_safe = 1` — **correctly for what `517` measures** (`filing_uuid` is
unique, 0 literal duplicate rows) and **not for what a buyer does with
`spend_usd`.** A literal-duplicate-row test is not an amendment-supersession
test, and the whole double-count passed straight through it.

### The measurement, and the doc figure that does not reproduce

| | |
|---|---:|
| rows | 27,825 |
| amendment rows | 1,416 · $41,640,996.01 |
| groups on `(client_id, registrant_id, filing_year, filing_period)` holding an amendment **and** a non-amendment | **1,135** |
| the same, with **form family** added to the key | 1,005 |
| rows superseded by a later filing in their own group | **1,064** |
| **money on superseded rows** | **$37,349,254.01 — 5.15%** |

**`docs/methodology/lobbying.md`'s "$28,961,112 — 4.0%" does not reproduce.**
The string appears in that document twice and in no script. Eight candidate
definitions were measured against the live file: $33,218,483 (sum-minus-max
within the mixed groups), $36,347,996 (the amendment rows), $39,183,189 (the
non-amendment rows), $40,119,485 (all-but-latest by `dt_posted`), $45,805,356
(all-but-latest over every multi-row group), $47,866,925 (sum-minus-min), and
the two `attribution_withdrawn` / `org_type_barred` variants, which move
further away rather than closer. **The 1,135 reproduces to the row; the dollar
figure reproduces under nothing.** $37,349,254.01 is the figure this project
can defend, and the methodology doc has been corrected to it.

### Why the doc's key could not be used as written

`(client_id, registrant_id, filing_year, filing_period)` puts a REGISTRATION in
the same bucket as the REPORT that follows it:

```
key ('153096','43651','1999','mid_year')
  3014138c...  Registration                 $0       posted 1999-03-29
  f8fa8e38...  Registration - Amendment     $0       posted 1999-06-03
  bca72f60...  Mid-Year Report         $60,000       posted 1999-08-13
```

A naive "the amendment supersedes the group" rule keeps the **$0 registration
amendment** and deletes the **$60,000 report**. The key therefore carries a
fifth component — the form family, REGISTRATION or REPORT — and even then it
**refuses** in the 294 groups that still hold more than one non-amendment row.

### What ships now

Four columns, added in place. **No row was dropped, no existing cell changed,
no money column rewritten, and no new money column created.** Row conservation
27,825 → 27,825 and money conservation on all three dollar columns to the cent
were proved on the write and are re-provable with `verify`.

| column | |
|---|---|
| `supersession_group_id` | blake2b digest over the five-part key |
| `supersession_status` | eight values, including two `AMBIGUOUS_*` refusals |
| `is_superseded` | 1 on 1,064 rows |
| `superseded_by_filing_uuid` | resolves into the same group, never to a superseded row |

Status distribution, with the money on each:

```
NOT_SUPERSEDED                             24,106   $645,244,682.29
REGISTRATION_NO_MONEY                       1,183             $0.00
AMENDMENT_SURVIVOR                            973    $31,306,058.22
SUPERSEDED_BY_AMENDMENT                       958    $33,654,987.22
UNFLAGGED_DUPLICATE_CANDIDATE                 370     $8,194,182.00
SUPERSEDED_BY_LATER_AMENDMENT                 106     $3,694,266.79
AMBIGUOUS_MULTIPLE_ORIGINALS                   93     $2,320,542.00
AMBIGUOUS_ORIGINAL_POSTED_AFTER_AMENDMENT      36     $1,329,256.00
```

**129 rows are `AMBIGUOUS_*`, carrying $3,649,798.** Which filing restates
which is not knowable there from the LDA fields Cedar holds, so they are **left
in the total and flagged**, never guessed. 370 rows are
`UNFLAGGED_DUPLICATE_CANDIDATE` — a repeated `filing_type_display` with no
amendment flag anywhere in the group. The LDA never said one replaces the
other, so Cedar does not say it either.

### THE FOURTH NUMBER. Read this before quoting any of them.

The three-totals table earlier in this document is still exact — all three were
re-measured 2026-09-02 and all three reproduce to the cent. **This work adds a
fourth figure to the same collection, and it is the only additive one at filing
grain:**

| table | column | figure | one row is |
|---|---|---:|---|
| `lobbying_registrants.csv` | `spend_reported_usd` | $645,052,868.51 | one registrant — **already** amendment-deduplicated by `180` |
| `tribe_year_lobbying_panel.csv` | `total_lobbying_spend_usd` | $680,561,640.52 | one (entity, year) — **not** amendment-adjusted |
| `native_entity_lobbying_disclosures.csv` | `spend_usd` | **$688,394,720.51** | one filing, `WHERE is_superseded = 0` — **the additive one** |
| `native_entity_lobbying_disclosures.csv` | `spend_usd` | $725,743,974.52 | one filing, unfiltered — **double-counts $37.3M** |

**Adding any two of these four counts the same dollar twice.** The two middle
figures are within $7.8M of each other and measure *different populations by
different rules*; their closeness is a coincidence and is the most likely way
someone gets this wrong.

That `lobbying_registrants.csv` was **already** doing supersession is the
corroboration for the key used here. Its shipped codebook has said since
2026-08-26: *"Deduplicated to one value per (registrant, client, year,
reporting period), taken from the filing with the latest dt_posted, because an
amendment supersedes what it amends."* The rollup did it; the filing table it
was built from did not.

### Where the warning reaches a buyer

Not in this document — a buyer never opens it. Three rows were added to
`data/clean/series_breaks.csv` (24 → 27, zero pre-existing rows lost, written
by `code/86_build_series_breaks.py`), which `code/87_build_dataset_notes.py`
renders as the **`## Comparability`** block of
`dist/04_lobbying/native_entity_lobbying_disclosures.NOTES.md` and
`dist/04_lobbying/tribe_year_lobbying_panel.NOTES.md`, and the codebook
descriptions of `spend_usd` and `total_lobbying_spend_usd` were rewritten in
`codebook_master.csv`. Before 2026-09-02 neither shipped note mentioned
amendments or the other totals at all, and the panel's
`total_lobbying_spend_usd` was described, in full, as *"Amount."*

### The check, and the proof that it fires

```
py -3 code/1091_lobby_amendment_supersession.py measure    # read-only
py -3 code/1091_lobby_amendment_supersession.py verify     # exit 1 on breach
py -3 code/1091_lobby_amendment_supersession.py selftest   # 8/8 fire
```

`selftest` injects one synthetic violation at a time, asserts the **named**
invariant is among the failures, restores, and asserts clean again — I1 row
conservation, I2 money conservation, I3 cell preservation, I4 key preservation,
I5 superseder resolves, I6 one survivor per group, I7 the drop accounts
exactly. The first draft of I6 printed **SILENT** on a real violation: it
picked a superseded row out of a two-row group, so un-superseding it emptied
the group of superseded rows and the invariant's precondition went false. That
is AGENT_FIELD_GUIDE §3 in miniature and it is why the fixture now picks from a
group with at least two superseded rows.

`1091` is an **in-place enricher**. `code/lobbying_pull/05_match_filings_v2.py`
rebuilds this table from `raw_filings.jsonl` and reverts it. The order after
any such rebuild is **65 → 350 → 351 → 353 → 1091**; `1091` is idempotent and
recomputes rather than appends.

### OWNER DECISION OUTSTANDING

`517`/`512` still class this table `SAFE_TO_AGGREGATE`, `aggregation_safe = 1`,
and that classification is **correct on its own terms** — it is a primary-key
and literal-duplicate test, and both still pass. It is nevertheless the field a
buyer's tooling reads before it reads any prose. Either `517` gains a notion of
*additive under a stated predicate*, or the lobbying contract in `512` declares
one. **Both files are the integrator's.** The measurement is here; the
classification is not an agent's to change.

---

## Schedule C: the "21.3% fetch backlog" is closed, and two figures above it are now stale

*Re-measured 2026-09-02. The `INT-READY` block earlier in this file is another
workstream's and is not edited here; this is the correction beside it.*

`INT-READY` states, correctly as of the day it was written: *"`coverage_status`
is `PARTIAL` on all ten index years: **32,218 returns were indexed as targets
and 6,870 were retrieved — 21.3%.** The 25,348 shortfall is Cedar's own fetch
backlog."* **That is no longer the state of the disk.**

| | 2026-09-01 | 2026-09-02 |
|---|---:|---:|
| indexed target returns | 32,218 | 32,218 |
| XML on disk | 6,870 | **29,149** |
| parsed into `nonprofit_schedule_c_lobbying.csv` | 6,870 | **29,149** |
| coverage | 21.3% | **90.5%** |
| `lobbying_usd_headline` | $3,325,511 over 132 returns | **$16,455,891 over 607 returns** |
| 2019 | PARTIAL | **FULL** |

Two things happened. `code/860`'s full-history pull extracted 21,807 returns
overnight and never re-parsed them — they sat on disk, paid for, invisible,
which is `ON_DISK_NOT_PROMOTED` and not a fetch at all. And 691 returns had
been logged `indexed_but_absent_from_archives` when they were really
**DEFLATE64-compressed members CPython's `zipfile` cannot decode**;
`--steps irs-deflate64` recovered **472** of them with the system 7-Zip.

**The 3,069 that remain are not a backlog and must never be reported as one:**

```
775   return_type 990T (772) and 990PR (3)   Schedule C does not exist on those
                                             forms. SOURCE_DOES_NOT_PUBLISH.
2,294 requested, and absent from every IRS ZIP archive published for their
      year. Logged per object in _xml_fetch_log.csv. 2017 (912) and 2022
      (1,430) carry 2,342 of the 3,069.
```

The union identity still holds on the larger corpus: `total_lobbying_usd`
$5,725,829 (220 returns) + `nonelecting_lobbying_usd` $10,730,062 (387) =
`lobbying_usd_headline` $16,455,891 (607), to the dollar. **Summing the
headline with either part still double-counts.** And Schedule C is still not
LDA lobbying — `is_lobbying = 0` on every row — so it never adds to any of the
four LDA totals above.
<!-- END LOBBY-SUPERSESSION -->

<!-- BEGIN SEC-GAMING -->

## SEC-filed gaming money — a third class, and the fee is not the revenue (workstream SEC-GAMING, 2026-09-02)

*Appended by `code/1080_sec_gaming_facility_revenue.py`. Every figure below was
re-counted from the live files on 2026-09-02 with `csv.reader`. This section is
inside `<!-- BEGIN SEC-GAMING -->` / `<!-- END SEC-GAMING -->`; `574` rewrites
this file wholesale and preserves only marked blocks.*

`sec_gaming_financial_disclosures.csv` (67 rows) and
`sec_gaming_management_contract_terms.csv` (7 rows) hold what a **public SEC
registrant filed about a tribal gaming property under a federal disclosure
obligation** — the property's own revenues where the registrant is the tribal
gaming authority, and the management or relinquishment fee where the registrant
is the manager.

### They are a THIRD class, and they are pooled with neither of the other two

Gaming already separates a regulator's figure from an operator's self-published
claim. These rows are neither.

| class | example table | what it is |
|---|---|---|
| regulator | `nigc_regional_ggr.csv`, `gaming_capacity_official.csv` | a regulator's measurement of the industry |
| self-published | `gaming_property_self_published_claims.csv` | what a casino says about itself on its own website |
| **SEC-filed** | **`sec_gaming_financial_disclosures.csv`** | **the filer's own accounting of its own contract or its own property, filed with the SEC and (in a 10-K) sitting inside or beside audited statements** |

`assertion_class = SEC_FILED_FINANCIAL_DISCLOSURE`, deliberately outside
`cedar_domain.MeasurementType` and outside the `SELF_PUBLISHED_*` family.
`not_summable_with` is populated on every row and names
`gaming_revenue_bounds.csv`, `nigc_regional_ggr.csv`, `nigc_revenue_bands.csv`,
`gaming_capacity_official.csv`, `state_gaming_observations.csv` and both
self-published tables.

**Never add an SEC-derived property figure to an NIGC regional ceiling.** The
property is *inside* the region; the ceiling already contains it. `1080 verify`
measures the overlap rather than asserting there is none: **7 of the 8
facility_ids in this table also carry a `REGIONAL_GGR_CEILING` bound row.** That
is expected. It is the whole reason the fence is declared.

### Four traps inside the table itself

**1. A 10-K restates the two prior fiscal years, and 32 of the 67 rows are such
a restatement.** Mohegan Sun's FY2017 net revenues of $1,079,920 thousand appear
in the FY2017, FY2018 *and* FY2019 10-Ks. All three rows are kept — each is a
real disclosure in a real filing — but **only `is_first_filing_of_this_fact = Y`
is safe to total. That subset is 49 of 67 rows.** Summing the whole table by
property-year triples Mohegan Sun. `restatements_agree` records whether the
later filings match the first: **0 of 32 disagree**, which is the only genuine
internal corroboration this table has.

**2. `figure_type` is not decoration. Never sum across it.** Six kinds are in
force and they are four different quantities about one property:
`FACILITY_NET_REVENUES` (32) · `MANAGEMENT_FEE_REVENUE` (16) ·
`RELINQUISHMENT_PAYMENT` (7) · `DERIVED_FACILITY_GROSS_REVENUES_AS_DEFINED` (7) ·
`DERIVED_FACILITY_NET_INCOME_AS_DEFINED` (3) · `FACILITY_NET_GAMING_REVENUE` (2).
A manager's fee and the property's revenue are related by a contract, not by
addition.

**3. THE FEE DOES NOT IMPLY THE REVENUE. It implies the contract's own base, and
that base is usually PROFIT.** This is the correction this workstream owes the
premise it started from. IGRA defines "net revenues" at **25 U.S.C. § 2703(9)**
as gross gaming revenues *less* amounts paid out as prizes and *less* total
gaming-related operating expenses excluding management fees — far closer to
operating profit than to revenue. And the contracts in this corpus do not even
share one base: Lakes' Red Hawk fee is *"30% of net revenue (as defined by the
development and management agreement)"*; Red Rock's Graton fee is *"24% of
Graton Resort's net income (as defined in the management agreement)"* in years
1–4 and 27% in years 5–7. Dividing a fee by its rate recovers **that contract's
base and nothing else**, which is why the derived types say `AS_DEFINED` and
never say "revenue" unqualified. A derived row carries `derived_from_fee = Y`,
the arithmetic in `derivation_arithmetic`, the rate's own accession in
`derivation_percentage_source_accession`, and a `derivation_caveat` that says
what the base is. **`1080 verify` V10 refuses a derived figure that wears a
reported figure's `figure_type`.**

Of the **8 distinct (property, rate) fee formulas** found across 51 statements, only **two** supported a derivation - Mohegan Sun at a flat 5% and Graton at a flat
27% - and the other six did not: Four Winds is *"24% of net income up to a certain
threshold and 19% over that threshold"* with the threshold undisclosed; Cimarron
is 30% of net income *"in excess of $4 million"*; Gun Lake's rate is never
stated (the "30% of the facility's net income" in the same 10-K belongs to the
**North Fork** project); and one apparent FireKeepers term is the **statutory
NIGC ceiling** recited in a regulatory-background section, not that contract's
fee.

**4. Twelve rows are a property a tribe owns that is NOT Indian-lands gaming.**
`facility_is_on_indian_lands` is `N` on the twelve Mohegan Sun Pocono rows — a
Pennsylvania racino owned by the Mohegan Tribal Gaming Authority — and the nine
Ontario `MGE Niagara Resorts` rows were rejected outright and are not in the
table. They are labelled rather than dropped because a reader of MTGA's segment
table needs to see why the segment lines do not add up to the tribal properties.

### How much of the universe this reaches, stated honestly

**8 facility records, 7 distinct Indian-lands properties, 6 tribes.** Against
787 ROWS that is **0.9%** *(correction appended 2026-09-02 from outside this block: 787 is a row count; against the 714 distinct properties it is 0.98%. `GAMING-DENOMINATOR-2026-09-02` at the foot of this file)*. It is not a solution to the missing-revenue
problem and must never be presented as one; it is a deep, well-evidenced core
for the handful of tribal casinos whose economics passed through a public
company's books. What it does add is duration — Mohegan Sun is covered for 15
distinct years (2000–2022), Graton for 5, Seneca Allegany for 3.

`sec_gaming_management_contract_terms.csv` **carries no money at all.**
`fee_percentage` is a rate. Nothing in that table may be totalled with anything.

<!-- END SEC-GAMING -->

<!-- BEGIN NEWSLETTERS -->
## Newsletters — there is no money here, and one column is still not summable

*Appended 2026-09-02 by workstream `newsletters` (`code/1105_newsletter_corpus_ship.py`).
This file is written WHOLESALE by `574`, which preserves only marked blocks;
this section lives inside `<!-- BEGIN NEWSLETTERS -->` / `<!-- END NEWSLETTERS -->`.*

`tribal_newsletter_corpus.csv` and `tribal_newsletter_coverage.csv` **carry no
dollar column of any kind.** There is nothing in either table that may be
totalled as money, and 517 classifies both accordingly.

The block is here anyway, because the mistake this file exists to prevent has a
non-monetary form and this dataset has it:

**1. `COUNT(*)` on the corpus is not the channel count.** The file holds
**1,889 rows** and **1,394 publication channels**. The other 495 are recorded
absences (481), one signup form with no archive, and 13 shard-I place-name
collisions kept flagged for their owner. **Filter `record_status =
'publication_channel'` before counting anything.** Counting rows overstates by
36%. This is the same class of error as *"539 publishable coords"* — a number
whose unit was never stated — and the answer here is the same one: the unit is
declared per row in a column, and 990's invariants 8–10 fail the build if the
column and the data it summarises ever disagree.

**2. `archive_span_years` is a FLOOR and must never be summed or averaged into
a claim about how long a paper has existed.** It is the span the channel's own
index exposes. The *Cherokee Phoenix* has printed since 1828; this table says
2000, because that is where its online index starts. Sum it and you get a
number about websites, not about the Native press.

**3. `n_channels` in the coverage table counts channels, not publications.** A
nation whose newspaper is indexed at both `/newspaper` and
`/newspaper/archive` has two channels and one masthead. Use
`publication_name` for a masthead count — **286 named newsletter channels,
365 distinct publication names across all channel types** — and expect it to be
lower than the channel count by design.

**4. Coverage rates need `site_url_class` in the denominator.** *Native Hawaiian
Organizations publish at 5%* and *NHOs that have a website publish at 11%* are
both true and they are different statements; 108 of 210 NHOs have no website
of any kind. Quoting the first as a Cedar coverage gap is wrong — it is
`SOURCE_DOES_NOT_PUBLISH`. See the coverage section of
`docs/NEWSLETTER_CORPUS.md`, which derives both from the file.
<!-- END NEWSLETTERS -->

<!-- BEGIN GAMING-DEEP -->
## `gaming_revenue_bounds.csv` — 97.76% of it is ONE number, repeated

*Appended 2026-09-02 by workstream GAMING-DEEP
(`code/1095_gaming_bounds_summability_and_seal_typing.py`). Re-measured on every
`1095 apply`; enforced by `1095 verify`, whose selftest proves each invariant
fires on an injected violation. **This file is written WHOLESALE by `574`, which
preserves only marked blocks; this section lives inside the BEGIN/END comment
markers named GAMING-DEEP, and nothing outside those markers belongs to this
workstream.***

| what | rows | measured |
|---|---:|---|
| `REGIONAL_GGR_CEILING` | 12,518 | NIGC's region-year total, written onto **every** property in that region-year |
| `REGIONAL_GGR_CEILING_NET_OF_KNOWN` | 951 | the same, less the properties whose revenue is separately known |
| `UNKNOWN_PROPERTIES_RESIDUAL_SUM` | 25 | the same residual, shared |
| **a repeated regional ceiling** | **13,494 (97.76%)** | over **694 distinct facilities** |
| `SINGLE_PROPERTY_TRIBE_LEVEL_GAMING_REVENUE` | 115 | honest, per property |
| `TRIBE_LEVEL_NOT_ATTRIBUTABLE_TO_A_PROPERTY` | 133 | honest, per **tribe** |
| `REPORTED_SLOT_WIN_IS_FLOOR_FOR_GGR` | 61 | honest, a floor |
| **an honest figure** | **309** | over **11 facilities of 787 ROWS** *(correction appended 2026-09-02 from outside this block: the facility denominator is 714, `GAMING-DENOMINATOR-2026-09-02` at the foot of this file)* |

**`SUM(revenue_upper_bound)` adds NIGC's regional total to itself once per
property in the region.** The largest single ceiling is carried by **162
facilities**. The table said this in a build log; it did not say it on the row,
and a `GROUP BY` in a subscriber's warehouse never reads a build log.

Five columns now say it per row, populated on all 13,803:

- **`not_summable_with`** — and for a ceiling row the FIRST thing it names is
  **`other_rows_of_gaming_revenue_bounds`**, because the trap is internal.
- **`bound_is_a_repeated_regional_ceiling`** — `Y` on 13,494, `N` on 309.
- **`n_facilities_sharing_this_ceiling`** — the repetition, counted.
- **`aggregation_level`** — `regional_aggregate` /
  `tribe_level_not_property_attributable` / `entity_specific`.
- **`summability_basis`** — one sentence, including why the ceiling is **never
  divided** by the operation count: NIGC's own FY2025 distribution has 8.6% of
  operations holding 55.8% of GGR while 54.3% hold 4.8%. An even split would be
  a fabrication with a plausible citation.

**No dollar column was added and none was changed** — `1095` asserts the five
money columns are byte-identical before and after, and refuses to write if they
are not. The standing refusal to put a revenue column on `gaming_facilities` is
untouched.

### The self-published web harvest, merged 2026-09-02

`code/1094_merge_web_harvest_into_gaming_claims.py` merged the 1,175 rows of
`gaming_web_harvest_observations.csv` into the two tables that already hold
self-published gaming evidence — **314 capacity signals into
`gaming_property_self_published_claims.csv` (270 → 584)** and **861 identity
assertions into `gaming_property_self_published_assertions.csv` (622 → 1,483)**.

Three qualifiers travel on every merged row and each of them blocks a total:

1. **152 of the 314 capacity figures are LOWER BOUNDS** ("500 + Slots").
   `value_is_bounded = Y`, `bound_direction = LOWER_BOUND`, and
   `bound_direction_as_harvested` keeps the source's own word. **A bound is not
   a count and must not be summed as one.**
2. **`measurement_scope = UNVERIFIED_SCOPE` on 309** — nothing in the sentence
   says whether the figure is the whole property or one room. The column is new
   on the destination table, and **blank on the 270 pre-existing rows means NOT
   RECORDED BY THAT EXTRACTION, never "scope verified."**
3. **712 of 1,175 rows carry NO `facility_id`**
   (`TRIBE_LEVEL_MULTI_FACILITY_NOT_DISAMBIGUATED`) — a host serving several of
   one tribe's properties where the page does not say which. The candidate list
   rides in `tribe_facility_ids_not_disambiguated`. **Never distribute a
   tribe-level claim across a tribe's facilities**; 463 rows key to 82
   facilities and the rest do not key at all.

**`not_summable_with` on every capacity row names four series and then names
this table itself** — two sentences on one page counting the same floor are two
claims about one thing, and adding them doubles the floor.

**9 merged rows duplicate an existing claim on `(source_url, metric, value)` and
16 also appear in `gaming_property_site_observations.csv`.** Both are FLAGGED
(`duplicate_of_existing_claim_id`,
`also_in_gaming_property_site_observations`), not dropped. **A count that
appears in two Cedar tables is one fact, and a buyer who unions them counts it
twice** — filter on the flag.

### Which states seal revenue, and which never collected it

*(Correction appended 2026-09-02 from outside this block, nothing else altered: **174 is the count of the ASSERTION, not of the evidence.** 113 carry `SEALED_HELD_BY_REGULATOR`; 58 carry `DISPOSITION_UNSUPPORTED_BY_RECORDED_QUOTE` (MN 48, NV 10) and 3 carry `NOT_COLLECTED_BY_THIS_BODY` (CO). Full derivation in `GAMING-DENOMINATOR-2026-09-02` at the foot of this file.)*

174 facilities carry `state_revenue_disclosure_status =
SEALED_BY_STATUTE_OR_COMPACT` across seven states. **They are not all the same
legal fact**, and the new `state_revenue_disclosure_disposition` separates them
from the recorded quote, never from an unquoted statute:

| disposition | states | facilities |
|---|---|---:|
| `SEALED_HELD_BY_REGULATOR` | AZ 43 · WI 40 · ND 22 · KS 8 | 113 |
| `NOT_COLLECTED_BY_THIS_BODY` | CO 3 | 3 |
| `DISPOSITION_UNSUPPORTED_BY_RECORDED_QUOTE` | MN 48 · NV 10 | 58 |

**Minnesota is the largest of the seven and its recorded quote is about compact
renegotiation** — it states no confidentiality, no aggregation and no
disclosure rule. Nevada's states a monthly *submission* requirement (NGC-31),
not a seal. Neither is a claim that those states publish per-tribe revenue;
both are a claim that **Cedar does not hold a quote that supports what the
column says**, and that is a re-sourcing task rather than a finding about the
state's law. `state_revenue_disclosure_quote_supports_status` is `N` on those
58 rows and `Y` on the other 116.
<!-- END GAMING-DEEP -->


<!-- BEGIN DEALS-MERGE-1088 -->
## deals — the 2026-09-02 staged merge, and the two sums that must stay apart

*Appended 2026-09-02 by workstream DEALS-MERGE-1088
(`code/1088_merge_staged_deals.py`). This file is written WHOLESALE by
`code/574_ws1_money_and_conservation.py`, which preserves only marked blocks;
this section is inside `<!-- BEGIN DEALS-MERGE-1088 -->` /
`<!-- END DEALS-MERGE-1088 -->` and no other block was touched.*

### The new totals

| | before | after |
|---|---:|---:|
| `deals_classified.csv` rows | 935 | **1,073** |
| `Announced_Value_USD` | $45,195,917,316 | **$47,880,355,533** |
| added by the merge | — | **$2,684,438,217** |

Conservation was proved row-for-row, not asserted: **0 of the 935 pre-merge
`Deal_ID`s lost, 0 pre-merge values changed, 0 columns lost.** The merge runs
through `88_build_deals_taxonomy.py`, which is an append-merge over
`cedar_pipeline.merge_table` and cannot drop a row.

> The ledger reached **1,079** before gate `G11` (an article date is not a
> transaction date) was added. Six rows merged before it existed were
> **withdrawn WHOLE** to `review/deals_withdrawn_duplicates.csv`, never
> deleted — 1,079 -> 1,073 rows, 52 -> 52 columns. **All six carried $0, so no
> total in this table moved**, which is why the money row above is the same
> either way. Named: `NLTR-2016-003`, `NLTR-2018-009`, `NLTR-2020-003`,
> `NLTR-2021-008`, `NLTR-2024-010`, `NLTR-2026-013`.

### A CEILING IS NOT A VALUE, and this merge is where the rule earns its keep

`Announced_Value_USD` is **consideration**. `Project_Total_Value_USD` is where
everything that is a sum but not consideration is parked so it cannot
double-count. They are DISJOINT by construction and **must never be added
together.**

Two staged rows named a facility ceiling in their own `value_basis` and were
moved, $58,500,000 in total:

* **Lytton Rancheria of California / Cadiz Inc.**, 2025-10-27 — an unsecured
  term loan facility of **up to $51.0 million**. The maximum a borrower may
  draw is not money that moved.
* **Bristol Bay Industrial, LLC / Alaska Communications**, 2022-06-15 — a
  secured delayed-draw term loan of **up to $7.5 million**. Same shape.

Each keeps its number, in `Project_Total_Value_USD`, with `Value_Type` reading
`NOT CONSIDERATION - moved out of Announced_Value_USD by code/1088 ceiling
rule` followed by the source's own phrase. Nothing was discarded and the total
does not lie.

**The largest sum in the whole staging set — a $151,000,000,000 IDIQ ceiling on
a multiple-award vehicle — never reached the value rule.** It was refused a step
earlier as a federal contract award, which is what it is: the maximum the
government may spend across every awardee on that vehicle, not money any one
nation received. Had it been admitted it would have been **3.2x the entire
deals dataset**.

### Three sums in this dataset that a buyer can still get wrong

1. **Never sum `deals_press_edgar_ancsa_additions.csv` alongside
   `deals_classified.csv`.** All 138 of its rows ARE in the classified table —
   it is their source, not an addition to it. This is the same rule already in
   force for the other nine `deals_*_additions.csv` slices, which together hold
   $22.67B of the classified table's own money.
2. **Never sum `Announced_Value_USD` and `Project_Total_Value_USD`.** See above.
   `Project_Total_Value_USD` across the whole table is $11,423,670,087 and it is
   a different concept.
3. **The four new `IDOBS-` rows and their kin carry no value on purpose.**
   `Value_Type` reads *"No value published. Never inferred."* A blank there is
   a fact about the source, not a gap in Cedar.
<!-- END DEALS-MERGE-1088 -->

<!-- BEGIN DEEPEN-SUBAWARD-DENOMINATOR -->
## The subaward overstatement — ALWAYS STATE THE DENOMINATOR

*Added 2026-09-02 by the `deepen` pass. Owned by this marker; `code/574` will
preserve it. Re-measure with `py -3 code/574_ws1_money_and_conservation.py`
after any subaward fold-in, and update the four figures below together — they
are one measurement, not four.*

**Measured 2026-09-02 on `data/clean/subawards.csv`, 76,859 rows:**

```
all rows                                       $47,301,660,819.78   <- never quote
countable  duplicate_status == 'primary'
       AND subaward_exceeds_prime_flag != 'yes'
           58,117 rows                         $25,864,997,128.19   <- the correct total
the money rule removes                         $21,436,663,691.59
```

> **SUPERSEDED THE SAME DAY — re-measured 2026-09-02T17:00Z, cents-exact, by the
> forward-construction pass. This block's own instruction is to update the four
> figures together after any fold-in; two fold-ins have happened since it was
> written, so the correction is stated here and the author's prose below is left
> exactly as written.**
>
> ```
> all 89,809 rows                              $57,020,557,710.47   <- never quote
> countable  69,921 rows                       $34,906,694,737.65   <- the correct total
> the money rule removes                       $22,113,862,972.82
>    = 38.8% of the unfiltered figure
>    = 63.4% MORE than the correct total
> ```
>
> `121 append` added **10,318 rows at 12:09Z** (FY2023 Q3, FY2024 Q1–Q4) and
> **2,632 at 16:49Z** (FY2023 Q4, re-pulled after the server returned a
> header-only object). `duplicate_status` is now `primary` **70,597** ·
> `exact_repeat_within_source` **18,366** · `superseded_by_primary_source` 846.
>
> **The overstatement FELL, from 82.9% to 63.4%, and the reason is worth
> stating: the money a real year of coverage adds is overwhelmingly `primary`.**
> A rising overstatement would have meant more re-filings; a falling one means
> more distinct subawards. **Quote 63.4%, and name its base — the correct
> $34.91B — in the same sentence.** Everything the block says below about WHICH
> percentage to quote, and why a bare one is a coin flip, is unchanged and is
> the reason this correction states both.

**The removed amount is 82.9% of the correct total and 45.3% of the inflated
one.** Both are true and they are not the same statement:

| phrasing | figure | what it means |
|---|---:|---|
| **"the unfiltered figure overstates by 82.9%"** | **82.9%** | removed ÷ **correct** ($25.86B). **This is the one to quote** — it is what a reader wants when they ask how wrong the big number is. |
| "the money rule removes 45.3% of the raw total" | 45.3% | removed ÷ **inflated** ($47.30B). Correct, and answers a different question. |

**Quote 82.9%, and name its base in the same sentence.** A bare percentage here
has already cost this project credibility twice, and both times the arithmetic
was fine:

- `docs/WHAT_IS_MISSING.md` recorded that the shipped sample README says
  *"46.5% overstatement"* while the dataset descriptor says *"86.9%"*, and
  observed that a buyer who reads both concludes one of them is wrong. Neither
  was. They were the same difference over two different denominators, on an
  older vintage of the same three numbers.
- An earlier generation of this very file said the rule removes
  *"$21,210,637,456.80 — 86.9% of the unfiltered figure."* $21.21B ÷ $45.62B is
  **46.5%**, not 86.9%; 86.9% was the overstatement, mislabelled as a share of
  the raw. **The number was right and the noun was wrong**, which is the harder
  error to catch because nothing fails.

**The rule this earns: a percentage whose denominator is not named in the same
sentence is not a measurement, it is a coin flip between two true answers.**

### And the corrected total is still not additive with prime contracting

A subaward is a slice of a prime award Cedar already publishes in
`prime_contracts.csv`. Federal dollars obligated = primes. Subawards say where
those dollars went **next**. Never add the two.

### One row is one FILING, not one subaward

FFATA requires monthly re-filing, so a single subaward appears once per month
it is open. Proved rather than assumed on the FY2021 pull: **one group is 93
re-filings of a single $57,500 subaward** running 2022-08 to 2025-01 — each
with its own `subaward_sam_report_id`, one action date, one subaward number.
That is why `duplicate_status` exists, why the duplicates are RETAINED and
flagged rather than deleted, and why **any count of rows in this table is a
count of filings**. Say "filings" or filter to `primary`; never say
"subawards" over the unfiltered row count.

<!-- END DEEPEN-SUBAWARD-DENOMINATOR -->

<!-- BEGIN QUARANTINE -->
## The quarantined-method exposure, and the $16.998B that left the attributed total

*Appended 2026-09-02 by workstream QUARANTINE
(`code/1079_quarantine_method_exposure.py`, ADR-019). Re-measured on every run
of `1079 verify`; the authority is `docs/QUARANTINED_METHOD_EXPOSURE.json`,
which that command regenerates. This section is inside
`<!-- BEGIN QUARANTINE -->` / `<!-- END QUARANTINE -->`; this file is written
WHOLESALE by `574` and preserves only marked blocks.*

**`prime_contracts.csv` still totals `$310,005,258,660.75` and still holds
1,217,768 rows.** Nothing was created or destroyed. What changed is how much of
that total Cedar claims to have attributed to a nation:

| | rows | obligations |
|---|---:|---:|
| attributed, before 2026-09-02 | 888,958 | $245,035,411,233.42 |
| attributed, after | 785,737 | **$227,965,023,146.82** |
| moved to the honestly-unattributed pool | 103,221 | **$17,070,388,086.60** |

**Anyone quoting "$244.77B attributed / 79.0%" from `START_HERE.md` is quoting
a superseded figure.** The current attributed total is $227.97B, and the
unattributed pool it publishes as a virtue grew by $17.070B.

**Three new rules for anyone summing this table.**

1. **`identifier_ruling_quarantined = 'Y'` marks money that rests on a
   discredited method.** 227,540 rows carry it, $28,862,571,317.64 of them
   still attributed. It is legitimate to publish, and it is not legitimate to publish
   *silently*: any per-entity total should be able to state how much of itself
   sits on a quarantined ruling.
2. **`identifier_ruling_method` is the RULING; `attribution_method` is the
   JOIN.** They answer different questions and neither substitutes for the
   other. Filtering on `attribution_method = 'uei_exact'` selects rows whose
   identifiers matched exactly — it says nothing about whether the identifier
   belongs to that nation.
3. **The repointed $2,443,371,845.81 is a MOVE, not new money.** 126 entities
   changed total; the gains and the losses net to zero. Never add
   `review/1079_entity_ledger_2026-09-02.csv` to anything — it is a delta
   table, and the levels it deltas are already in `prime_contracts.csv`.

**Subaward dollars are reported separately and may not be added to any of the
above.** On the sub side 1,971 rows lost a `sub_native_tribe_id` and 122 were
repointed; on the prime side 517 and 186. Those are subaward amounts, a
different money column in a different file.
<!-- END QUARANTINE -->

<!-- BEGIN GAMING-DENOMINATOR-2026-09-02 -->
## The gaming denominator, and the sealed-revenue disposition

*Appended 2026-09-02 by `code/1116_ruling_propagation_2026_09_02.py`'s pass, inside its own marked block so `574` preserves it. **No other block in this file was rewritten**; where a figure inside another workstream's block is superseded, a single attributed correction line was appended beside it and the surrounding prose left exactly as its author wrote it.*

### The denominator

**`gaming_facilities.csv` holds 787 ROWS, and a row is not a facility.** The ladder, owned and gated by `code/846_session_audit.py::_denom`:

```
787   rows in gaming_facilities.csv
-16   whose NAME says no casino - 7 exactly "No casino", plus 9 more like
      "Grand Canyon West - no casino", "Tribal admin only - no casino"
=771   facility rows
-57   extra rows across the same-tribe duplicate groups
=714   distinct properties
```

**FIVE denominators circulated on 2026-09-02 and all five were quoted as settled: 787, 780, 734, 727, 714.** Each came from a different definition of "facility" and none said which. 787 is raw rows; 780 removes only the 7 EXACT placeholders and misses the 9 that say it in a longer name; 734 is 787 minus duplicates with every placeholder left in; 727 is 780 minus a duplicate count of 53. **None of them is wrong about the piece it measured, and four of them are wrong as a denominator.** No verdict is applied in the table itself - `duplicate_of_facility_id` is populated on 10 rows, not 57 - so 714 is a measurement, not a state of the file. Note also that the duplicate register carries `DIFFERENT_TRIBES_CHECK_BOTH` groups that are **not** duplicates: Stables Casino pairs the Miami Tribe with Modoc Nation, which is a joint operation. Dividing by 787 inflates the denominator by 10.2% and understates every gaming coverage percentage by about 9.3%.

### The sealed-revenue disposition

**CORRECTED 2026-09-02.** 174 facilities carry `state_revenue_disclosure_status = SEALED_BY_STATUTE_OR_COMPACT`, and **174 is not the number of facilities evidenced as sealed**. The disposition column says so on the same row: **113** are `SEALED_HELD_BY_REGULATOR` (AZ 43, KS 8, ND 22, WI 40); **58** are `DISPOSITION_UNSUPPORTED_BY_RECORDED_QUOTE` (MN 48, NV 10) - the status was asserted and the recorded quote does not support it; **3** are `NOT_COLLECTED_BY_THIS_BODY` (CO 3), which is a different fact entirely: the body does not hold the figure, so there is nothing sealed. Quote **113**, and quote the disposition beside it.

**The rule both of these earn, and it is a totalling rule:** *a status column and a disposition column on the same row can disagree, and the status is the one that gets summed.* `SEALED_BY_STATUTE_OR_COMPACT` was asserted 174 times and the evidence recorded on the row supports it 113 times. Nothing was broken; nothing was lost; the count was simply about the assertion rather than about the evidence. **Sum the column that carries the evidence, and print the disposition beside the total.**

Re-derive: `py -3 code/1116_ruling_propagation_2026_09_02.py derive`.
Gate: `py -3 code/1116_ruling_propagation_2026_09_02.py verify` exits 1 while
any document still states a superseded figure with nothing beside it.
<!-- END GAMING-DENOMINATOR-2026-09-02 -->

<!-- BEGIN ACQUIRE-BIA-ACREAGE -->
## Acreage is a total, and the BIA mineral acreage table double-counts one

*Appended 2026-09-02 by workstream `ACQUIRE-1119-1121`
(`code/1119_acquire_biamaps_arcgis.py`), inside its own marked block so `574`
preserves it. **No other block in this file was read or rewritten.** Acreage
is not money, but it is the denominator `resource_revenue.csv` has never had,
and a denominator that is silently 0.60% too large produces a per-acre figure
that is silently 0.60% too small — which is exactly the class of error this
file exists to fence.*

`data/clean/resource_bia_mineral_acreage_tracts.csv`, 249,165 rows, one row
per **title record**.

| | acres |
|---|---:|
| naive sum of the `acres` column across all rows | **70,290,363.9** |
| one acreage per (`land_area_code`, `tract_id`) | **69,872,859.0** |
| **overstatement** | **417,504.8 — 0.60%** |

**The cause is not a duplicate row.** 5,465 tracts are written **twice**, once
with `ownership_type = Trust` and once with `ownership_type = Restricted`, and
**both rows carry the identical acreage rather than a split of it**. Tract
`256 2181` on TURTLE MOUNTAIN is 157.08 acres and appears as 157.08 Trust and
157.08 Restricted. Those are two title statuses touching one parcel. Measured:
of the 5,465, **5,465 carry identical acres on both rows and 0 carry differing
acres** — so this is a rule, not a tendency. The publisher's own vocabulary
already has the value it should have used: `Both Trust & Restricted`, which it
applies on exactly 2 rows.

**It is concentrated, so it is not a rounding error anywhere it matters:**

| land area | overstated acres |
|---|---:|
| FORT HALL | 172,025.6 |
| BAD RIVER (LA POINTE) | 26,021.9 |
| LAC COURTE OREILLES | 20,001.6 |
| PINE RIDGE | 19,909.7 |
| STANDING ROCK | 17,909.0 |
| OSAGE | 14,588.3 |

**THE RULE.** Take **one acreage per (`land_area_code`, `tract_id`)** before
totalling anything. If you need the trust/restricted split, this column cannot
give it to you: the file states *which statuses touch a tract*, not *how many
acres each holds*, and any split derived from it is invented.

**AND A PER-STATE TOTAL DOUBLE-COUNTS A CROSS-STATE TRACT.**
`FORT MOJAVE 604 T 106`, 879.87 acres, is recorded once under `AZ` and once
under `CA` because the reservation straddles the line. Every other published
attribute on the two rows is identical, so no combination of columns separates
them. Total by `land_area_code`. Total by `state` only after deciding what a
state boundary means for a tract that crosses one, and say which you did.

**GISACRES IS A DIFFERENT MEASURE AND MAY NOT BE DIFFERENCED AGAINST THIS.**
`bia_aian_national_lar.csv`.`GISACRES` is a GIS-computed polygon area from the
Land Area Record layer. `acres` here is a title acreage from the Land Titles
and Records offices. They answer different questions, are produced by
different processes, and their difference is not a finding about anything.

**AND THIS TABLE IS NOT A REVENUE DENOMINATOR YET, BECAUSE IT HAS NO TRIBE
KEY.** 184 of its 495 distinct `land_area_name` values reach a Cedar spine
entity by name. The other 311 include boarding-school lands, ANCSA areas and
public-domain allotments named for individuals. Dividing a nation's royalty by
"its" acreage requires a land-area-to-entity ruling that does not exist;
manufacturing it with a name matcher is the containment defect with a new
front door.

Re-derive every figure above:
`py -3 code/1119_acquire_biamaps_arcgis.py build` then read
`docs/codebooks/12g_bia_mineral_acreage.md`.
Gate: `py -3 code/1119_acquire_biamaps_arcgis.py verify` exits 1 on breach and
`selftest` proves it fires on an injected short retrieval.
<!-- END ACQUIRE-BIA-ACREAGE -->

<!-- BEGIN GAMING-TOTAL -->

## The annual total, with gaming in it -- and the boundary that keeps it honest (workstream GAMING-TOTAL, 2026-09-02)

*Appended by `code/1126_annual_total_federal_and_gaming.py`. Every figure below is re-derived from the live files by `1126 build` and re-checked by `1126 verify` (exit 1 on breach); `1126 selftest` proves each check fires on an injected violation. The series itself is `data/clean/annual_indian_country_money_series.csv`, one row per (fiscal_year, series_id).*

**The owner's question was whether the annual total is more accurate with NIGC's regional gaming numbers in it. It is -- and the reason is also the reason the two may not be added silently:**

> **Federal obligations are transfers INTO Indian Country. Gaming revenue is Indian Country's OWN-SOURCE revenue.**

A total that omits the largest own-source stream badly understates the economy. A total that adds them into one number claims they are the same kind of money. So both are published, side by side, with `money_class` on every row -- `FEDERAL_OBLIGATION_TRANSFERRED_INTO_INDIAN_COUNTRY` and `INDIAN_COUNTRY_OWN_SOURCE_REVENUE` -- and **no grand total is written anywhere in the table**. `verify` V3 fails if a row ever equals federal + gaming. The reader may add them; Cedar states what the sum would mean instead of doing it for them.

Over the **19 fiscal years where BOTH federal legs and the gaming series all exist (FY2007-FY2025)**: federal obligations attributed to a nation total **$367,602,232,832**, and NIGC gross gaming revenue totals **$618,977,205,572**. Gaming is **1.68x** the federal stream over that window. That ratio is the whole argument for publishing both, and it is also why neither is the answer on its own.

**The window is FY2007 onward and not FY2001, deliberately.** The modern assistance table begins at FY2007, so a ratio taken across FY2001-2006 divides gaming by a federal figure that is missing one of its two legs - which is how FY2001 comes out at 22x and means nothing. The shape inside the window is the interesting part and it is not flat: gaming runs about 2x federal through the 2010s, **crosses below 1.0 in FY2020 and FY2021** when pandemic assistance more than doubled the federal stream while COVID closures took GGR from $34.7B to $27.8B, and settles near 1.5x from FY2022. Neither series explains Indian Country's year on its own.

### What may be summed, and what may not

| series | grain | additive with | never add to |
|---|---|---|---|
| `federal_prime_obligations` | fiscal year | `federal_assistance_obligations` | subawards (a subaward is a SLICE of a prime already counted), `native_passthrough.csv`, Schedule I, FAC expenditures, any gaming series |
| `federal_assistance_obligations` | fiscal year | `federal_prime_obligations` | the same list, plus `faads_pre2008_assistance_attributed` in FY2007, where 11,063 transactions / $2.166B are the same transactions |
| `federal_obligations_total` | fiscal year | **nothing** -- it already IS prime + assistance | its own components; anything above |
| `faads_pre2008_assistance_attributed` | fiscal year, FY2001-06 | nothing | anything. **Tier B on every row** -- no DUNS or UEI exists on any pre-FY2007 FAADS row |
| `nigc_regional_ggr_rolled_to_nation` | fiscal year | **nothing** | every federal series here; `gaming_revenue_bounds.csv` ceiling rows; SEC per-property figures; any self-published casino claim |
| `sec_filed_per_property_net_revenues` | fiscal year | nothing | above all the NIGC row for the same year -- **the property is INSIDE the region and the regional figure already contains it** |

### The double count a naive `GROUP BY fiscal_year` produces, and the column that stops it

**Every NIGC report carries the current fiscal year AND the prior year, and three years are therefore present under TWO region systems.** Grouping `nigc_regional_ggr.csv` by `fiscal_year` alone doubles them:

| fiscal year | naive `GROUP BY fiscal_year` | one region system | overstated by |
|---|---:|---:|---:|
| FY2002 | $29.213B | **$14.497B** | $14.716B |
| FY2007 | $52.160B | **$26.016B** | $26.143B |
| FY2016 | $62.600B | **$31.300B** | $31.300B |

The discriminator was already in the table and nothing was reading it: **`figure_vintage`**. The rule is *sum only `own_year_report` rows within a fiscal year*, which is also NIGC's first publication of that year rather than its later restatement. **Four years have no own-year report on this disk -- FY2001, FY2011, FY2013, FY2021 -- and take their prior-year column, which the row says in its `basis`.** This is the same shape as the `extent_competed` two-vocabulary seam: the file was right, and the consumer had no way to see the seam.

### A regional figure is never a property's money

NIGC publishes GGR at the **region** level and nowhere else. `gaming_revenue_bounds.csv` is 13,803 rows of which **13,494 are one `REGIONAL_GGR_CEILING` repeated across 694 facilities**, and the largest single ceiling is carried by 162 of them. Apportioning it to facilities, or summing it across them, multiplies a region's entire GGR by its property count. This series therefore rolls NIGC up **only along the axis NIGC itself publishes** -- region to nation.

**The denominator, computed rather than typed** (`code/846_session_audit.py::_denom`, the single gated ladder, read at build time and never retyped): **787 rows - 16 NOT_A_PLACE = 771 placed -> 717 distinct properties**. **11 of those carry an honest per-property revenue figure** (`SINGLE_PROPERTY_ATTRIBUTED` or `REPORTED_PROPERTY_REVENUE`, counted as distinct properties rather than as rows). Every gaming row of the output states that denominator in `coverage_note`, and `verify` V7 fails if one does not. **This figure has moved twice in one day** - 714 on the morning of 2026-09-02, 717 by that evening - so import the ladder, do not quote this paragraph.

### Precision, and the years a chart will get wrong

`figure_precision` rides on every gaming row. FY2001-FY2012 are exact thousands; **FY2013-FY2020 are rounded to $0.1B** because NIGC published only a distribution map in those years, so eight regions each rounded to $0.1B carry up to $0.4B of rounding in the national figure; FY2021-FY2025 are exact dollars. FY2020 is a COVID trough ($34.7B -> $27.8B -> $39.0B) and must not be smoothed or used as a growth base. And the two clocks are not the same clock: NIGC aggregates **each operation's own audited fiscal year**, so a fiscal-year GGR figure can include revenue earned up to 16 months before publication, while a federal fiscal year is the government's.

### The federal side, stated with its denominator

`federal_prime_obligations` is `sum(total_obligations)` over `attributed_flag='1'` -- **$229,441,298,847.35 across 789,360 rows**, which is 74.0% of the $310,005,258,660.75 the whole table holds. `attributed_flag` already excludes the 103,221 rows / $17.07B that `code/1079` moved to the unattributed pool on 2026-09-02. `federal_assistance_obligations` is `sum(obligated_usd)` over the same flag -- **$168,639,438,944.64 across 549,530 rows**. **Neither is ever summed with `subawards.csv`**, and `verify` V5 fails if a subaward figure ever reaches this table.

**The federal total is complete only from FY2007**, where the modern assistance table begins. FY2000-06 carries prime only; the pre-2008 Native assistance slice is the separate `faads_pre2008_assistance_attributed` series, is **tier B throughout**, and overlaps the modern table in FY2007 by 11,063 transactions.

<!-- END GAMING-TOTAL -->

<!-- BEGIN GAMING-DENOMINATOR-717-CORRECTION -->

## CORRECTION 2026-09-02 — the gaming property denominator is 717, not 714

Appended by `code/1142_gaming_denominator_doc_sweep.py`. **No prose above this
line was edited**, per the rule the `GAMING-DENOMINATOR-2026-09-02` banner set
for itself.

Any figure in this document that uses **714** as the count of distinct gaming
properties is superseded. The settled figure is **717**:

```
787   rows in gaming_facilities.csv
-16   carrying cedar_place_id_absent_reason = NOT_A_PLACE
=771   rows that are a place
-54   extras collapsed by the 53 ADJUDICATED merge groups
=717   distinct properties        <- COUNT(DISTINCT cedar_place_id)
```

**Why the old ladder gave 714.** It subtracted **57** duplicate extras found by
name normalisation. The adjudication found **54**. The three-property
difference is three groups a mechanical duplicate test called the same property
and a human verdict did not:

| group | why it is two properties |
|---|---|
| `THREE RIVERS` (OR) | Coos Bay 97420 and Florence 97439 — **67 km apart**, two casinos |
| `GLACIER PEAKS` (MT) | a casino and its hotel |
| `CITIES OF GOLD` (NM) | a casino and its hotel |

A duplicate count is an upper bound on merges; an adjudication is the answer.

**Two groups remain genuinely open** and either ruling moves 717: `THE STABLES`
(a real Miami/Modoc joint operation — one property, two sovereigns) and
`7 CLANS FIRST COUNCIL` (OK). Both are in
`review/OWNER_DECISION_QUEUE.md` as GP-1 and GP-2.

**Do not re-derive this number.** Seven values circulated for it — 787, 780,
734, 727, 725, 717, 714 — each from a correct-looking rule applied to an
undefined question. `gaming_facilities.csv` now answers it itself: the 16
non-places carry a reason column, and the merged properties share a
`cedar_place_id`. Read `COUNT(DISTINCT cedar_place_id)`.

<!-- END GAMING-DENOMINATOR-717-CORRECTION -->

<!-- BEGIN MONEY-RECON-1144 -->

## The three money datasets, measured together — and the prime-vs-sub answer

*Workstream MONEY-RECON-1144, 2026-09-02. Every figure below is produced by
`py -3 code/1144_money_reconciliation_prime_sub.py measure`, recorded in
`docs/MONEY_RECONCILIATION_1144.json`, and re-checked by `verify`, which exits 1
when one of the ten recorded numbers stops reproducing. `selftest` perturbs each
of the ten and asserts the comparison rejects it (10/10) — so a PASS here is
evidence the measurement happened, not evidence that nothing broke.*

**Read method:** every file is read `all_varchar=true` + `TRY_CAST`.
`ignore_errors=true` was deliberately NOT used. It drops malformed rows
silently, and a money total over a silently-shortened table is the defect this
section exists to prevent. Uncastable money cells: **0** in `funding`, **0** in
`contractors`, **0** in `subcontracting`.

### 0. A DELIVERY DEFECT: the largest money dataset is not in `dist/customer/`

`dist/customer/MANIFEST.csv` declares **13** datasets. **12 CSVs are on disk.**

```
declared and absent:  contractors  (1,217,768 rows, manifest says 1,606.5 MB)
```

`contractors__CODEBOOK.md`, `contractors__NOTES.txt` and
`contractors__NOTES.pdf` were all written at **16:24**, after the other twelve
datasets landed at 16:10–16:11, and `dist/manifests/contractors.json` exists.
So the combine ran for `contractors` and produced its paper; the CSV itself is
not there. `C:` had **17 GB free** at measurement time against a declared
1.6 GB output, so free space is not obviously the cause. **The flagship money
dataset cannot ship in this state, and the manifest currently promises a file a
buyer would not receive.** `contractors` figures below are therefore measured
from the flagship source, `data/clean/prime_contracts.csv`, and 1144 records
`contractors.measured_from_dist = false` so the substitution is never silent.

### 1. The headline totals, as of 2026-09-02

| dataset | file measured | rows | the total | attributed to a nation | entities |
|---|---|---:|---:|---:|---:|
| `funding` | `dist/customer/funding.csv` | 701,955 | `obligated_usd` **$219,689,020,478.59** | **$168,156,517,719.76** on 549,180 rows | 669 |
| `contractors` | `data/clean/prime_contracts.csv` | 1,217,768 | `total_obligations` **$310,005,258,660.75** | **$230,259,821,658.99** on 791,521 rows | 526 |
| `subcontracting` | `dist/customer/subcontracting.csv` | 89,809 | `subaward_amount` countable **$34,906,694,737.65** on 69,921 filings | — (see §3) | 656 sub / 163 prime |

`contractors`' $310,005,258,660.75 reproduces the figure in the QUARANTINE block
above to the cent. Its **attributed** total does not, and should not: that block
recorded $227,965,023,146.82 / 785,737 rows immediately after `1079`, and
`1140` and the rulings passes have since moved it to **$230,259,821,658.99 /
791,521 rows**. Quote the live figure or re-derive; the QUARANTINE block's
number is a correct record of a moment, not a current fact. The quarantined
exposure moved with it: **227,540 rows carry
`identifier_ruling_quarantined = 'Y'`, and $30,258,921,540.23 of the attributed
total now rests on one** — the QUARANTINE block's $28,862,571,317.64 is the
same measurement taken earlier in the day. Any per-entity total should still be
able to state how much of itself sits on a quarantined ruling; it is now 13.1%
of the attributed figure.

**Columns that may be summed, restated for these three files only:**

- `funding.obligated_usd` — freely, one row is one assistance transaction.
- `contractors.total_obligations` — freely. **`total_award_value` is a
  different measure and is 18.15× larger**: $5,625,791,120,828.75 across the
  same 1,217,768 rows. It is a *ceiling on the award*, restated on every
  transaction of that award, not money moved. Never add the two, never sum it
  across transactions, and never let a chart labelled "obligations" be built
  from it.
- `subcontracting.subaward_amount` — **only** where
  `duplicate_status = 'primary'` AND `subaward_exceeds_prime_flag != 'yes'`.
- `contractors.total_obligations` **+** `subcontracting.subaward_amount` — see
  §3. The answer is no.

### 2. The subaward overstatement — the live figure, and the THREE vintages currently shipping

Re-measured on the delivered file, 89,809 rows:

```
all rows                          $57,020,557,710.47   <- never quote
countable, 69,921 filings         $34,906,694,737.65   <- the correct total
the money rule removes            $22,113,862,972.82
   = 63.4% of the correct total   <- the number to quote, with its base named
   = 38.8% of the unfiltered one
```

`duplicate_status`: `primary` 70,597 · `exact_repeat_within_source` 18,366 ·
`superseded_by_primary_source` 846. `subaward_exceeds_prime_flag = 'yes'` on
836 rows / $7,581,669,521.78, of which 676 / $7,266,026,845.59 are also
`primary` — that flag is doing real work and is the reason `primary` alone
($42,172,721,583.24) is not the answer either.

**This agrees exactly with the DEEPEN-SUBAWARD-DENOMINATOR correction above,
with `dist/samples/README.md`, with `dist/collection_descriptors.json` and with
`dist/measured_facts.json`. It agrees with nothing else that a buyer receives.**

Measured across the delivered artifacts, **three generations of this one warning
ship side by side**:

| figure | where it ships | vintage |
|---|---|---|
| **63.4% · $57.02B · $34.91B · $22.11B** | `dist/samples/README.md`, `dist/collection_descriptors.json`, `dist/measured_facts.json` | **current, correct** |
| 82.9% · $25,864,997,128.19 correct · $47,301,660,819.78 unfiltered | `dist/customer/subcontracting__NOTES.txt` L20–22, `subcontracting__CODEBOOK.md` L9 | the 76,859-row file, superseded |
| "the unfiltered subaward total runs **86.9%** above the correct one" | the boilerplate footer of **all 13 `*__CODEBOOK.md` and all 13 `*__NOTES.txt`** | the oldest — the generation this file records as *"the number was right and the noun was wrong"* |

**A buyer opening `subcontracting__NOTES.txt` reads 82.9% at line 21 and 86.9%
at line 47.** Twenty-six lines apart, in one file, about one measurement. That
is the precise failure `docs/WHAT_IS_MISSING.md` recorded when the sample README
said 46.5% and the descriptor said 86.9%, and it has not been closed — it has
been *tripled*, because the corrected figure was added alongside the two stale
ones instead of replacing them.

The same sentence in `subcontracting__NOTES.txt` carries a fourth stale number:
it says `cedar_uid` is *"legitimately blank on the 43,282 rows whose only Native
party is the subawardee."* The measured count is **47,561** (see §4).

**Where these come from, and what was done:**

| site | fixed here | why |
|---|---|---|
| `code/512_build_dataset_contracts.py` `GRAIN_SUBAWARD_FUNDING` L1905–1913 | **YES** — the four stale figures replaced with the measured ones | they are stale facts, not a design choice; the dict's key, cardinality and basis were not touched |
| `code/1137_customer_dataset_combine.py` L65, **L361**, **L456** | **NO — NOT TOUCHED** | that file is owned by another live workstream (mtime 16:58, five minutes before this measurement). L361 and L456 are the boilerplate that stamps "86.9%" into all 26 delivered paper files |

**The 1137 fix is one string in two places** and is the single highest-value
customer-facing correction outstanding. Both should read: *"and the unfiltered
subaward total runs 63.4% above the correct one."* Its owner should re-measure
rather than paste — the four figures move on every subaward fold-in, which is
exactly how they got out of step three times.

### 3. Prime vs sub — the combined figure, and whether combining is defensible

**It is not. There is no single defensible "prime + sub" total, and the chart
that showed primes only was right.** Here is the arithmetic that settles it.

Take the $34,906,694,737.65 of countable subaward dollars and ask, of each
filing, whether its `prime_award_unique_key` is an award Cedar already publishes
in `prime_contracts.contract_award_unique_key`:

| | filings | USD | share of countable |
|---|---:|---:|---:|
| **the prime award IS in `prime_contracts.csv`** | 27,319 | **$13,612,271,637.21** | 39.0% |
| the prime award is NOT | 42,602 | $21,294,423,100.44 | 61.0% |
| *(543 countable filings carry no prime key at all)* | | | |

Now decompose both halves by which leg is the Native party:

| prime award in `prime_contracts`? | `direction` | filings | USD |
|---|---|---:|---:|
| **yes** | `a_native_as_prime` | 26,587 | $12,955,932,319.97 |
| **yes** | `both_sides_native` | 699 | $639,083,134.11 |
| **yes** | `b_native_as_subawardee` | 33 | $17,256,183.13 |
| no | `b_native_as_subawardee` | 37,850 | **$19,317,140,197.29** |
| no | `a_native_as_prime` | 3,944 | $1,439,559,118.53 |
| no | `both_sides_native` | 766 | $499,305,405.62 |
| no | `unknown` | 42 | $38,418,379.00 |

And of the $13.61B overlap, **$13,500,614,272.77 (99.2%, 27,195 filings) sits on
a prime row that is itself `attributed_flag = 1`** — already inside the
$230,259,821,658.99 headline. Only $111,657,364.44 sits on an unattributed
prime.

**So a naive `primes + subs` = $310.01B + $34.91B does three wrong things at
once:**

1. **It double-counts $13.61B outright**, 99.2% of it already inside the
   attributed prime figure. A subaward is a slice of a prime award; adding it
   re-counts a dollar the federal government obligated once.
2. **It mixes two epistemic objects.** FPDS primes are *government-recorded*.
   FSRS subawards are *vendor self-reported by the prime, unvalidated*. A single
   number cannot carry two evidentiary standards, and a reader has no way to
   discount the half that is a filer's own claim.
3. **It launders a coverage gap into growth.** The $1,439,559,118.53 of
   `a_native_as_prime` on primes Cedar does NOT carry is not new money reaching
   Indian Country — it is 3,944 filings pointing at prime awards missing from
   `prime_contracts.csv`. Adding it patches the prime table's gaps from the sub
   table on 3,944 awards and not on the rest, which is worse than either
   consistent choice.

**What may be said instead.** Two numbers, two labels, never one:

> **Federal prime contract obligations, FPDS, government-recorded:**
> $310,005,258,660.75 across 1,217,768 transactions FY2000–FY2026, of which
> **$230,259,821,658.99 is attributed to a Native nation** (791,521 rows, 526
> entities).
>
> **Federal subcontract dollars reaching Native firms as the SUBAWARDEE, on
> prime awards Cedar does not otherwise carry — FSRS, vendor self-reported:**
> **$19,317,140,197.29** across 37,850 countable filings.

That second figure is the **only** slice of the subaward file that is neither a
re-slice of a published prime nor a patch over a prime-table gap, and it is
still a self-report. It may be presented **beside** the prime total. It may
never be added into it, and the sentence that carries it must say
"self-reported by the prime."

**A ceiling, for anyone who wants the outer bound.** On the 7,305 prime awards
where both sides are present, subawards total $13,612,271,637.21 against
$41,120,683,994.44 of prime obligations on the same awards — contained at 33%.
**444 of those awards have subawards exceeding their prime's obligations, by
$1,737,942,789.89 in aggregate**, and they survive the
`subaward_exceeds_prime_flag` filter because that flag is evaluated per filing
against the source's own `prime_award_amount`, not per award against Cedar's
summed obligations. This is not automatically a defect — obligations accrue over
a contract's life and can trail an award's value — but it is a real ceiling on
how tightly the two tables reconcile, and no product should claim they
reconcile more tightly than that.

### 4. `subcontracting`'s 44.8% linkage rate is measuring the PRIME leg

**The `cedar_uid` column in `subcontracting.csv` is not "the Native party on
this row." It is the prime leg.** Measured on all 89,809 rows:

| | rows |
|---|---:|
| `cedar_uid` non-blank | 40,201 |
| …equal to `prime_cedar_uid` | **39,567** |
| …equal to `sub_cedar_uid` | 894 |
| …equal to **neither** leg named on the row | **631** |
| `cedar_uid` blank | 49,608 |
| …but `sub_cedar_uid` IS populated | **47,561** |
| …and neither leg is keyed — **the real gap** | **2,047** |

So the coverage figure carried into this session — *"subcontracting 44.8%, the
lowest rate of any large dataset"* — reproduces exactly as a measurement of
`cedar_uid` (40,201 / 89,809 = 44.76%) **and it is not this dataset's linkage
rate.** A subaward has two legs; the dataset's own majority population is
`b_native_as_subawardee` (49,360 filings, $32.43B), and those are precisely the
rows where `cedar_uid` is blank by design.

**Measured on either leg, `subcontracting` is 87,355 of 89,809 rows —
97.27% linked**, not 44.8%. That is the highest linkage rate of any money
dataset in the project, not the lowest. Its true unlinked residue is **2,454
rows / $1,662,416,606.58** with neither leg keyed — of which 1,852 carry no key
in any of the three columns and 407 carry a `cedar_uid` matching neither leg.
That residue is the number worth working, and §6 works part of it.

Two consequences:

1. **Do not spend a linkage pass closing the 49,608 blank `cedar_uid` rows.**
   47,561 of them are already keyed on the leg that matters and closing them
   would mean writing the *subawardee's* id into a column documented as the
   prime's — which would silently corrupt every `GROUP BY cedar_uid` a customer
   runs against this file.
2. **The 631 rows whose `cedar_uid` matches neither leg are a genuine
   inconsistency** and are flagged here, not changed. A row naming a Cedar
   entity that is neither of its two named parties cannot be right; it is small,
   and resolving it is an identity question, not an arithmetic one.

### 5. A populated key is not an attribution — measured on both money tables

`cedar_uid` being non-blank does **not** mean Cedar stands behind the
attribution, in either table. Anyone computing a coverage rate or a per-entity
total off key presence is including rows the pipeline deliberately withholds.

**`contractors` — 96 rows / $269,771,379.45.** All 96 are *Nakupuna
Foundation*, `attribution_method = 'unattributed'`, `confidence_tier = C`, key
present, `attributed_flag = 0`. **This is correct behaviour** — tier C does not
key a dollar — and it is why `rows_with_cedar_uid` (791,617) exceeds
`rows_attributed_flag_1` (791,521). Quote the flag, never the key.

**`funding` — 3,620 rows / $1,534,889,361.52 keyed but not attributed:**

| `attribution_method` | rows | USD | reading |
|---|---:|---:|---|
| `ledger_uei_state_disagreement_withheld` | 2,051 | $586,605,621.55 | deliberate withhold. Correct, and the key's presence is what makes the withhold auditable |
| `not_evaluated:ak_scope_line9` | 789 | $585,951,384.42 | Alaska scope, tier C, never evaluated. Correct |
| `unattributed` (excl=0) | 524 | $208,029,567.40 | **inconsistent** — `attribution_method` says unattributed while `attribution_status` says `cedar_neid` and both keys are populated |
| `unattributed` (excl=1) | 256 | $154,302,788.15 | excluded; the exclusion governs |

**`funding` — 44 rows / $2,192,775.00 that claim an attribution they do not
hold.** `attributed_flag = '1'` with `cedar_uid` AND `tribe_id_neid` both blank:

| `attribution_status` | `canonical_name` | rows | USD |
|---|---|---:|---:|
| `excluded_not_native` | *(blank)* | 21 | $850,345.00 |
| `unresolved_native` | `tuscarora tribe` | 13 | $940,847.00 |
| `excluded_not_native` | `tuscarora tribe` | 10 | $401,583.00 |

This is the residue of the same class `1140` closed at 504 rows (T5). Two
things are wrong on the 23 Tuscarora rows and only one of them is arithmetic:
the flag claims an attribution with no key, **and** ten rows are simultaneously
`excluded_not_native` and named for a tribe. **The flag is a bug; the exclusion
is a ruling.** Both are left in place and flagged here rather than patched,
because `federal_funding_transactions.csv` was being written in place by another
workstream during this pass and because "is Tuscarora excluded" is an identity
question this pass has no standing to answer. It is $2.19M — 0.001% of the
funding total — and it is recorded so the next pass does not re-derive it.


### 6. What this pass ADDED: 290 rows keyed by exact-UEI self-consistency

`py -3 code/1144_money_reconciliation_prime_sub.py apply --execute`, applied to
`data/clean/subawards.csv` on 2026-09-02. Backup:
`data/clean/subawards.csv.bak_2026-09-02_pre_1144_money_reconciliation_prime_sub`.
Prior values for all 900 cells:
`review/1144_subaward_uei_prior_values_2026-09-02.csv`. The applied rows, with
their evidence: `review/1144_subaward_uei_self_consistency_2026-09-02.csv`.

**The same UEI was keyed to a Cedar entity on some rows of this file and blank
on others.** That is not a name match and it is not a new ruling — it is
Cedar's own already-adjudicated key, on an exact federal registration
identifier, applied consistently within one table. **The tier is INHERITED from
the keyed rows** (`START_HERE` trap 1: a tier is never assigned by the
consumer): 1 group tier A, 18 tier B, none minted.

**290 rows / $98,041,089.48**, 300 target entries because 10 rows were
recoverable on *both* legs. Largest: `Native Hawaiian Veterans`
(`YGMHQFZH3YE5`, 26 rows, $32.54M, tier A), `STILLAGUAMISH TRIBE OF INDIANS`
(`SCBFR3JUM1W3`, 60 rows across two name spellings, $15.80M),
`CANKDESKA CIKANA COMMUNITY COLLEGE`, `SOUTHEAST ALASKA REGIONAL HEALTH
CONSORTIUM`, `STONE CHILD COLLEGE`. Either-leg coverage on the clean table
moves **87,355 → 87,645 (97.27% → 97.59%)** and the neither-leg residue
**2,454 → 2,164 rows / $1,567,901,108.10**.

**What it REFUSED, and why the refusal is the point.** 152 (leg, UEI) groups
were skipped — 120 because the UEI carries a conflicting `tribe_id` or tier
among its keyed rows, 32 because **one federal registration is keyed to two
different Cedar entities**. Only 30 rows / $3,999,950.40 of unkeyed money was
actually blocked by those refusals, so the rule costs almost nothing and the
32 two-entity UEIs are a standing identity defect worth someone's attention.

**And it deliberately left ~$1.0B on the table.** `WIND RIVER CONSTRUCTION LLC`
is the single largest unkeyed subawardee in the file. It files under **three**
UEIs: `VHSJFRQKMXG9` (3 rows) **is** keyed to `CE-0014C-0N`; `JWH3U659JTN1`
(516 rows) and `XP6ZPHL3PN88` (5 rows) are not. **A different UEI of a
same-named firm is not evidence** — a separate registration is a separate
question, and answering it is an identity ruling this pass has no standing to
make. The rule takes the identifier, never the name.

**Ordering.** This is an IN-PLACE enricher on `data/clean/subawards.csv`. A
rebuild by `94_*`/`121` reverts it and will look like pure progress.
`py -3 code/1144_money_reconciliation_prime_sub.py linkage-verify` exits 1 when
it has been reverted — and it is a row-level assertion, not a count floor:
it names 300 specific `(source_dataset, subaward_source_record_id)` pairs and
requires each to carry its expected key. Every one of them was blank before, so
no prior state can satisfy it. **It was observed failing** on the first
`apply`, which aborted on a conservation assertion before writing.

**`dist/customer/subcontracting.csv` does not yet carry this** — it is
generated, and the figures in §1–§5 above were measured on the delivered file
as it stands. Regenerate before shipping.

<!-- END MONEY-RECON-1144 -->
