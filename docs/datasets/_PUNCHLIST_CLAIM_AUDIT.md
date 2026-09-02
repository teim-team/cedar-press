# Punch-list claim audit

*Generated 2026-09-02 by `code/1107_punchlist_claim_verify.py`. It imports `code/526_dataset_standard.py` and re-measures its output against the live files with **no row cap**. `526` is integrator-owned; this file does not edit it.*

**339 punch items. 12 carry a FALSE claim. 9 findings on the checks themselves.**

| invariant | what it re-measures | false claims |
|---|---|---:|
| V1 | C11 *always empty in N rows*, full-file recount | **10** |
| V2 | C11 *not in any codebook*, exact set membership | 0 |
| V3 | C5 *no conservation coverage*, bracket qualifier stripped | **2** |
| V4 | C9 *no runbook*, file existence | 0 |

V1 checked 81 items and found **47** individual column claims false.

## FALSE CLAIMS — do not act on these punch-list lines

### `cedar_identifier_graph_edges.csv` — _entity_layer — V1

- punch list says: *always empty in 20,001 rows: asserting_row_ref*
- why it is false: 'always empty' asserted from a 20,000-row sample of a 46,820-row file
- true row count: **46,820** (the line says 20,001)
- of 1 columns called always empty, **0** are
- non-blank counts over the full file:
  - `asserting_row_ref` — **7,997** non-blank

### `prime_contracts.csv` — contractors — V1

- punch list says: *always empty in 20,001 rows: contract_transaction_unique_key, contract_award_unique_key, naics_code, naics_description ...*
- why it is false: 'always empty' asserted from a 20,000-row sample of a 1,217,768-row file
- true row count: **1,217,768** (the line says 20,001)
- of 10 columns called always empty, **0** are
- non-blank counts over the full file:
  - `contract_transaction_unique_key` — **841,002** non-blank
  - `contract_award_unique_key` — **841,002** non-blank
  - `action_date` — **841,002** non-blank
  - `geo_award_unique_key` — **841,002** non-blank
  - `naics_code` — **838,229** non-blank
  - `award_type` — **769,868** non-blank
  - `product_or_service_code` — **574,011** non-blank
  - `product_or_service_code_description` — **574,011** non-blank
  - `award_base_description` — **573,320** non-blank
  - `naics_description` — **561,536** non-blank

### `federal_actions.csv` — federal-register — V1

- punch list says: *always empty in 20,001 rows: comment_url, tribe_or_native_entity*
- why it is false: 'always empty' asserted from a 20,000-row sample of a 156,897-row file
- true row count: **156,897** (the line says 20,001)
- of 2 columns called always empty, **1** are
- non-blank counts over the full file:
  - `comment_url` — **1,178** non-blank

### `federal_actions_raw.csv` — federal-register — V1

- punch list says: *always empty in 20,001 rows: comment_url*
- why it is false: 'always empty' asserted from a 20,000-row sample of a 156,897-row file
- true row count: **156,897** (the line says 20,001)
- of 1 columns called always empty, **0** are
- non-blank counts over the full file:
  - `comment_url` — **1,178** non-blank

### `faads_transactions.csv` — funding — V1

- punch list says: *always empty in 20,001 rows: recipient_duns, tribe_id, recipient_uei, assistance_type_description ...*
- why it is false: 'always empty' asserted from a 20,000-row sample of a 60,661-row file
- true row count: **60,661** (the line says 20,001)
- of 5 columns called always empty, **3** are
- non-blank counts over the full file:
  - `recipient_duns` — **1** non-blank
  - `recipient_uei` — **1** non-blank

### `faads_transactions_all_agencies.csv` — funding — V1

- punch list says: *always empty in 20,001 rows: recipient_duns, tribe_id, recipient_uei, assistance_type_description ...*
- why it is false: 'always empty' asserted from a 20,000-row sample of a 2,769,748-row file
- true row count: **2,769,748** (the line says 20,001)
- of 7 columns called always empty, **4** are
- non-blank counts over the full file:
  - `recipient_duns` — **677,035** non-blank
  - `recipient_uei` — **604,653** non-blank
  - `assistance_type_description` — **594** non-blank

### `federal_funding_transactions.csv` — funding — V1

- punch list says: *always empty in 20,001 rows: face_value_of_loan, original_loan_subsidy_cost, total_face_value_of_loan, total_loan_subsidy_cost ...*
- why it is false: 'always empty' asserted from a 20,000-row sample of a 701,955-row file
- true row count: **701,955** (the line says 20,001)
- of 18 columns called always empty, **2** are
- non-blank counts over the full file:
  - `face_value_of_loan` — **225,031** non-blank
  - `original_loan_subsidy_cost` — **225,031** non-blank
  - `total_face_value_of_loan` — **225,031** non-blank
  - `total_loan_subsidy_cost` — **225,031** non-blank
  - `credit_instrument_flag` — **225,031** non-blank
  - `business_types_code` — **225,031** non-blank
  - `source_archive_stamp` — **225,031** non-blank
  - `fetched_date` — **225,031** non-blank
  - `business_types_description` — **223,337** non-blank
  - `business_types_description_normalized` — **223,337** non-blank
  - `business_types_description_normalized_basis` — **223,337** non-blank
  - `state_agreement` — **199,873** non-blank
  - `geo_pop_county_fips` — **92,064** non-blank
  - `geo_pop_state_fips` — **92,064** non-blank
  - `geo_pop_county_name` — **92,054** non-blank
  - `ledger_proposed_tribe_id` — **15,878** non-blank

### `ca_gaming_payments.csv` — gaming — V1

- punch list says: *always empty in 20,001 rows: county, derived_tribe_revenue_value, derived_revenue_scope, issue_date*
- why it is false: 'always empty' asserted from a 20,000-row sample of a 41,758-row file
- true row count: **41,758** (the line says 20,001)
- of 4 columns called always empty, **3** are
- non-blank counts over the full file:
  - `issue_date` — **181** non-blank

### `lobbying_issue_families_filing.csv` — lobbying — V1

- punch list says: *always empty in 20,001 rows: entity_id_withdrawn, entity_id_withdrawn_reason, entity_id_withdrawn_by_script, entity_id_withdrawn_date*
- why it is false: 'always empty' asserted from a 20,000-row sample of a 27,796-row file
- true row count: **27,796** (the line says 20,001)
- of 4 columns called always empty, **0** are
- non-blank counts over the full file:
  - `entity_id_withdrawn` — **471** non-blank
  - `entity_id_withdrawn_reason` — **471** non-blank
  - `entity_id_withdrawn_by_script` — **471** non-blank
  - `entity_id_withdrawn_date` — **471** non-blank

### `native_entity_lobbying_disclosures.csv` — lobbying — V1

- punch list says: *always empty in 20,001 rows: expenses_usd, org_type_barred, org_type_reason, attribution_withdrawn ...*
- why it is false: 'always empty' asserted from a 20,000-row sample of a 27,825-row file
- true row count: **27,825** (the line says 20,001)
- of 8 columns called always empty, **0** are
- non-blank counts over the full file:
  - `org_type_barred` — **841** non-blank
  - `org_type_reason` — **841** non-blank
  - `attribution_withdrawn` — **471** non-blank
  - `attribution_withdrawn_entity_id` — **471** non-blank
  - `attribution_withdrawn_reason` — **471** non-blank
  - `attribution_withdrawn_by_script` — **471** non-blank
  - `attribution_withdrawn_date` — **471** non-blank
  - `expenses_usd` — **237** non-blank

### `cedar_identifier_ledger_final.csv` — _entity_layer — V3

- punch list says: *no conservation coverage*
- why it is false: conservation IS recorded, under a bracket-qualified source_table that 526's split('/')[-1] cannot match

### `np_orgs.csv` — nonprofits — V3

- punch list says: *no conservation coverage*
- why it is false: conservation IS recorded, under a bracket-qualified source_table that 526's split('/')[-1] cannot match

## Findings on the checks themselves

*Not breaches. Each would make a check STRICTER, and C12 is a HIGH-severity check ten agents are working from, so retuning it is the integrator's call, not this pass's.*

| finding | dataset | table | why |
|---|---|---|---|
| F1 | `_entity_layer` | `cedar_identifier_graph_nodes.csv` | C12 PASSES on a basis column that is mostly blank |
| F1 | `_entity_layer` | `cedar_ruling_ledger_consolidated.csv` | C12 PASSES on a basis column that is mostly blank |
| F1 | `_entity_layer` | `entity_hierarchy.csv` | C12 PASSES on a basis column that is mostly blank |
| F1 | `_entity_layer` | `native_fi_roster.csv` | C12 PASSES on a basis column that is mostly blank |
| F2 | `_entity_layer` | `nho_ownership_changes.csv` | C12 PASSES only on a FIELD-level provenance basis, which is not an inclusion basis |
| F2 | `gaming` | `compact_versions.csv` | C12 PASSES only on a FIELD-level provenance basis, which is not an inclusion basis |
| F2 | `gaming` | `gaming_decision_events.csv` | C12 PASSES only on a FIELD-level provenance basis, which is not an inclusion basis |
| F3 | `funding` | `faads_transactions.csv` | population_scope IS declared in dataset_contracts.json and C12 does not read it |
| F4 | `deals` | `deals_2026_ytd_additions.csv` | shippable but INVISIBLE to the standard: zero rows - 526 skips every column check, so the table produces no punch items at all |

## The patch `526` needs (integrator)

```python
# 1. C5 - strip the bracket qualifier before comparing (V3).
cons_tables = {re.sub(r'\s*\[.*$', '', (r.get('source_table') or '')).split('/')[-1]
               for r in read_csv(CONSERVATION)}

# 2. C11 - never assert 'always empty' from the capped pass (V1).
#    scan() stops at cap=20000; recount the candidates on the FULL
#    file before writing an instruction to DROP a column.
empty_cand = [h for h in hdr if nn[h] == 0]
if empty_cand and n > CAP:
    n, empty = full_counts(table_path(name), empty_cand)
else:
    empty = empty_cand

# 3. refuse to report a clean result you did not measure.
if not cb:
    raise SystemExit('UNMEASURED: codebook_master.csv is empty')
if n == 0:
    add(cid, 'C0', 'high', name, 'zero rows or unreadable - every column check was SKIPPED', 'table invisible to the standard')

# 4. verify must exit non-zero. Today main() returns 0 always,
#    so `526 verify` cannot fail and is not a gate.
```
