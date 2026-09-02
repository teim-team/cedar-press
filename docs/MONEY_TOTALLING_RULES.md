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

*Appended 2026-09-01 by workstream FAADS (`code/791_faads_transaction_key_and_repoint.py`). Re-measured on every run of `791 seam`; enforced by `791 seam --verify`.* **This file is written WHOLESALE by `574`, which preserves only marked blocks; this section is inside `<!-- BEGIN FAADS -->` / `<!-- END FAADS -->

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

**The two honest per-property statuses reach 11 of 787 facilities (1.4%).** A
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
787 facilities across seven states — AZ, CO, KS, MN, ND, NV, WI** — each with
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
