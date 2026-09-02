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

`native_passthrough.csv` totals $2,789,908,063.57 across 1,262 rows, of which only 891 rows / $712,252,766.20 are countable. FSRS is self-reported by the prime with no validation: **the RELATIONSHIP is the product, the AMOUNT carries a filter.**

## The duplicate allegations, re-measured

| table | rows | literal duplicate rows | groups | worst group | surplus $ | surplus rows at $0 |
|---|---:|---:|---:|---:|---:|---:|
| `faads_transactions.csv` | 60,661 | 1,001 | 946 | 6× | $75,078,206.00 | 3 |
| `native_passthrough.csv` | 1,262 | 114 | 19 | 44× | $123,011,703.71 | 0 |
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
| `native_passthrough.csv` | 72,837 | `emitted` | 1,262 | 1.73 |
| `native_passthrough.csv` | 72,837 | `rejected:direction_is_not_both_sides_native` | 71,311 | 97.9 |
| `native_passthrough.csv` | 72,837 | `rejected:one_side_unresolved_to_a_cedar_entity` | 4 | 0.01 |
| `native_passthrough.csv` | 72,837 | `stale:both_sides_native_rows_appended_to_subawards.csv_after_the_last_81_build_so_no_passthrough_row_exists_for_them_yet` | 260 | 0.36 |

## Why no primary key is declared

`GRAIN_WS1` in `code/512_build_dataset_contracts.py` is empty on purpose. A declared grain with no validated key is a release-blocking violation in `512`, and none of these four tables has a key that survives full-file validation:

- the `faads_*` pair has no identifying column at all — the source published one and the mapper dropped it. `30_funding_pre2008.py` now carries both columns; the re-extract is queued in `review/OWNER_DECISION_QUEUE.md` and has not run.
- `subawards.csv` retains byte-identical repeat filings on purpose and carries no per-occurrence ordinal. `45_promote_subawards.identity_key` is unique across all 55,316 `primary` rows and only there.
- `native_passthrough.csv` inherits both problems from its parent.

> **A downstream fragility worth naming:** `faads_entity_attribution.csv` keys 29,594 attributions to `faads_row_id`, which is the ROW POSITION in `faads_transactions_all_agencies.csv`. The queued rebuild that restores the transaction key will also re-order that file. The attributions must be re-pointed in the same pass or they silently move to different transactions.
