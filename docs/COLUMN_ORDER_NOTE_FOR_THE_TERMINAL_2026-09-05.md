# Note for the terminal: column order and column count in the customer files

Written 2026-09-05 from the twelve flagship samples in `public/data/cedar/samples/`
(ten rows each, headers read in full) after the owner asked whether every column in
each dataset is necessary and whether the Cedar variables come first. This is a
**recommendation with the reasoning shown**, not a ruling: a ten-row sample proves
a column exists and what it looks like, not whether a customer needs it. The owner
decides; the terminal implements in `code/770_sample_extracts.py` and
`code/1135_full_dataset_review_bundle.py`, where the published column order is
written, and the site follows through `data/cedar/explore.overrides.json`
(`default_columns`) and the re-derived contracts.

## The rule

1. **The Cedar identity block comes first, in this order, in every table:**
   `cedar_uid`, `canonical_name`, `entity_class`. Then the record's own identifier.
   The three names are the register's names (`data/spine/cedar_entity_names.csv`),
   not each table's local spelling, so a customer who joins two files joins on the
   same three columns. Where a table today carries the name or class under another
   header (`native_party_canonical_name`, `Native_Party_Type`, `owner_hub_name`,
   `cedar_spine_canonical_name`, `entity_type`), keep that column if it means
   something different (the party as published, the owner hub) and ADD the three
   canonical ones from the register at the front; where it means the same thing,
   rename it.
2. **A table whose rows name several entities** (bills: `entity_cedar_uids`; NAGPRA:
   the six `*_entity_ids` role columns) keeps the pipe-separated uid column as the
   first column and adds a pipe-separated `entity_names` beside it (bills already
   have one). Do not force a single `cedar_uid` on a row that names three.
3. **Three tiers of column.** A: what the record says (the customer file). B:
   provenance a customer might need to cite or audit (source URL, source record id,
   attribution method, confidence tier, the one `*_basis` that explains an amount).
   C: pipeline bookkeeping (`built_date`, `fetched_date`, `retrieved_date`,
   `promoted_date`, `artifact_mtime`, `*_basis` strings that explain a matcher,
   `*_normalized`, `*_token*`, `review_flag*`, `parse_template`, `spans_found`,
   `population_basis`, `floor_basis_field`, `pre_2000_flag`, `duplicate_status`,
   the `geo_*` dominance shares and ambiguity flags, `deflator_factor_2025`,
   `inflation_base_year`). Tier C stays in the workspace and out of the customer
   file. The `*_real2025` columns are a judgment call: keep them (they are what a
   customer would otherwise compute wrongly) but put them beside their nominal
   column, with the deflator and base year dropped and stated once in the
   collection's documentation.
4. **A column blank on every row of the sample is not proof it is empty** (ten rows
   of one agency's grants have no loan fields). Check the full table before
   dropping; drop only what is empty or constant across the whole release, or is
   tier C by meaning.
5. **Order within a table:** identity block → record id → what happened (date,
   year, kind, title or description) → who else (client, registrant, awardee,
   counterparty, institution) → money and its basis → status → source link →
   tier-B provenance. Nothing after the source link should be something a reader
   needs to understand the row.

## Per table

Counts are the sample's header today. "Drop" means drop from the customer file, not
from the workspace. Columns not named are tier A or B and keep their place.

### funding / federal_funding_transactions (63 columns)
Front: `cedar_uid`, `canonical_name`, **add `entity_class`** (absent), `assistance_transaction_unique_key`.
Then: `action_date`, `fiscal_year`, `obligated_usd`, `obligated_usd_real2025`, `assistance_type_description`, `cfda`, `cfda_title`, `awarding_agency_name`, `awarding_sub_agency_name`, `recipient_name`, `recipient_uei`, `recipient_city_name`, `recipient_state_code`, `business_types_description`, the four loan columns, `award_id_fain`, `assistance_award_unique_key`, `attribution_method`, `confidence_tier`, `source_vintage`.
Drop (tier C, 24): `fy_partial_flag`, `attribution_source_line`, `attribution_rule`, `exclusion_reason`, `exclusion_source_line`, `exclusion_rule`, `ak_flag`, `excluded_flag`, `attributed_flag` (every published row is attributed, or it would not be published), `credit_instrument_flag`, `business_types_code`, `deflator_factor_2025`, `inflation_base_year`, `population_basis`, `state_agreement`, `source_archive_stamp`, `fetched_date`, `attribution_status`, `attribution_basis`, `source_vintage_basis`, `business_types_description_normalized`, `business_types_description_normalized_basis`, `recipient_duns` (retired identifier), and the twelve `geo_*` columns except `geo_recipient_county_name` and `geo_pop_county_name` if the county is a customer feature.
Note: the sample has no source URL column; the site builds the USAspending award page from `assistance_award_unique_key`. Consider writing `source_url` into the file so the file is self-sufficient.

### federal-register / consultation_events (39 columns)
Front: `cedar_uid`, **add `canonical_name` and `entity_class`** (the table has `tribe_name` as published and no class), `consultation_event_id`.
Then: `notice_date`, `event_start_date`, `event_end_date`, `consultation_type`, `topic`, `agency`, `sub_agency`, `program`, `participant_name_as_published`, `participant_role`, `location`, `format`, `comment_deadline`, `has_written_comments`, `has_summary`, `has_transcript`, `federal_register_citation`, `fr_document_number`, `source_url`, `source_quote`, `tier`, `confidence`, `match_method`.
Drop (10): `channel` (constant), `fetched_date`, `built_date`, `nagpra_notice_overlap`, `nagpra_bridge_overlap`, `nagpra_coverage_window`, `event_date_basis`, `event_date_source_quote`, `location_basis`, `location_source_quote`, `document_role`, `n_participant_rows_for_event`, `is_event_primary_row`. The last three are how the table was built, not what a consultation was.

### legislation / native_bills (37 columns)
Front: `entity_cedar_uids`, `entity_names`, **add `entity_classes`** (pipe-separated, from the register; `entity_class_scope` is a class-level scope, not the entity's class, and its own `_basis` says so), `bill_id`.
Then: `congress`, `chamber`, `bill_type`, `number`, `title`, `policy_area`, `introduced_date`, `sponsor`, `sponsor_bioguide_id`, `cosponsor_count`, `latest_action`, `latest_action_date`, `outcome`, `n_rollcalls`, `has_rollcall`, `companion_bill_id`, `bill_scope`, `entity_link_tiers`.
Drop (12): `affected_entities` (blank), `bill_scope_basis`, `outcome_basis`, `companion_basis`, `classification_source`, `classification_kappa`, `record_basis`, `build_date`, `pre_2000_flag`, `floor_basis_field`, `has_resolved_entity`, `n_entities_resolved`, `entity_link_basis`, `n_entity_classes`, `entity_class_scope_basis`. Keep `entity_class_scope` only if renamed to say what it is.
Note: no source URL; the site builds the congress.gov page from `congress`, `bill_type`, `number`. Write `source_url` into the file.

### deals / deals_classified (40 columns)
Front: `cedar_uid`, `native_party_canonical_name` → rename `canonical_name`, **add `entity_class`** (`Native_Party_Type` is the party's type as published, not the register's class; keep it after), `Deal_ID`.
Then: `Event_Date`, `Event_Date_precision`, `Event_Year`, `Deal_Title`, `Native_Party`, `Native_Party_Type`, `native_party_role`, `Counterparty_or_Funder`, `Deal_Category`, `Industry`, `sector`, `transaction_type`, `capital_source`, `Event_Type`, `Status`, `deal_status_std`, `Announced_Value_USD`, `Value_Type`, `Project_Total_Value_USD`, `State`, `Location`, `Description`, `Native_Connection`, `Source_1`, `Source_1_Type`, `Source_2`, `Source_2_Type`, `Verification_Status`, `Confidence`, `native_party_attribution_tier`.
Drop (7): `Event_Date_not_before`, `Event_Date_not_after` (fold into `Event_Date_precision`), `Event_Quarter`, `Event_Month` (derivable), `Notes` (internal), `Date_Added`, `Data_As_Of` (release metadata, state once).
Also: this is the one table with mixed-case headers; lowercase them to match the rest.

### nagpra / nagpra_notices (69 columns)
Front: `affiliated_entity_ids`, **add `affiliated_entity_names`** and **`affiliated_entity_classes`**, `document_number`. The other role columns (`consulted_*`, `repatriation_recipient_*`, `disposition_priority_*`, `letter_of_support_*`, `aboriginal_land_*`) keep their ids and each gains a names column; the paired `n_*_named` / `n_*_resolved` counts are tier C.
Then: `publication_date`, `publication_year`, `notice_type`, `statute_stage`, `is_correction`, `title`, `institution_name`, `institution_names_all`, `institution_city`, `institution_state`, `institution_type_derived`, `responsible_party_statement`, `object_categories`, `mni_total_stated`, `mni_statements`, the four `n_*_objects_stated`, `cultural_items_total_stated`, `removal_counties`, `removal_states`, `removal_location_statements`, `repatriation_eligible_date`, `response_deadline_date`, `window_days_derived`, `lineal_descendant_determination`, `culturally_unidentifiable`, `agency_names`, `source_url`, `html_url`, `pdf_url`, `full_text_url`.
Drop (21): `notice_title_form` (constant with `notice_type`), `institution_primary`, `institution_count`, `institution_name_basis`, `mni_basis`, `mni_statement_count`, `removal_location_basis`, all twelve `n_*_named` / `n_*_resolved`, `n_parties_named`, `n_entities_resolved`, `has_resolved_entity`, `parse_template`, `spans_found`, `parent_dataset`, `fetched_date`, `artifact_mtime`, `institution_split_flag`, `institution_split_basis`.

### lobbying / native_entity_lobbying_disclosures (43 columns)
Front: `cedar_uid`, `canonical_name`, `entity_type` → rename `entity_class`, `filing_uuid`. (`entity_id` duplicates `cedar_uid` on every sample row; drop it.)
Then: `filing_year`, `filing_period`, `filing_type`, `filing_type_display`, `dt_posted`, `client_name`, `client_id`, `client_state`, `registrant_name`, `registrant_id`, `registrant_state`, `self_filed`, `income_usd`, `expenses_usd`, `spend_usd`, `spend_basis`, `lobbying_issues_codes`, `specific_issues_text`, `government_entities`, `affiliated_organizations`, `termination_date`, `supersession_status`, `is_superseded`, `superseded_by_filing_uuid`, `supersession_group_id`, `filing_url`, `attribution_method`, `match_confidence`.
Drop (10): `entity_id`, `entity_state` (the register has it), `matched_alias`, `pull_keyword`, `org_type_barred`, `org_type_reason`, `filing_url_original` (keep one URL), the four `attribution_withdrawn*` (a withdrawn attribution is a row that should not be in the customer file at all).
And the sample: eight of ten rows are superseded amendments. Have 770 sample current versions first, or the preview shows two records.

### contractors / prime_contracts (72 columns)
Front: `cedar_uid`, `canonical_name`, **add `entity_class`**, `contract_transaction_unique_key`.
Then: `action_date`, `fiscal_year`, `total_obligations`, `total_obligations_real2025`, `total_award_value` (with its NEVER SUM warning in the documentation), `awardee_name`, `awardee_uei`, `parent_name`, `parent_uei`, `contract_number`, `parent_contract_number`, `contract_award_unique_key`, `funding_agency`, `award_type`, `naics_code`, `naics_description`, `product_or_service_code`, `product_or_service_code_description`, `award_base_description`, `setaside`, `setaside_reported`, `reported_8a`, `reported_buy_indian`, `reported_indian_business`, `reported_native_preference`, `extent_competed_normalized` (rename `extent_competed` and drop the raw one, or keep both), `sector`, `supersector`, `defense`, `recipient_city_name`, `recipient_state_code`, `place_of_perform_city`, `place_of_perform_state`, `owner_attribution_status`, `owner_as_of_transaction_cedar_uid`, `attribution_method`, `confidence_tier`, `identifier_ruling_tier`, `source_authority`.
Drop (25): `cage_code` (the publication rule's carve-out for individually owned firms applies here; publish only where the firm is demonstrably incorporated, else drop), `pre_2000_flag`, `total_award_value_real2025` (a cumulative figure deflated row by row is not a number anyone should have), `deflator_factor_2025`, `inflation_base_year`, `attributed_flag`, `built_date`, `ruling_status`, `ruling_applied_date`, `extent_competed_normalized_basis`, `award_attributes_basis`, `identifier_ruling_method`, `identifier_ruling_quarantined`, `identifier_ruling_basis`, `identifier_ruling_review`, and the twelve `geo_*` except the two county names, `geo_award_unique_key`, `geo_built_date`.
Note: no source URL; write one from `contract_award_unique_key`.

### subcontracting / subawards (78 columns)
Front: `cedar_uid`, **add `canonical_name` and `entity_class`**, then `sub_cedar_uid`, `prime_cedar_uid` (which side is Native is the point of this table; `direction` says it), `subaward_source_record_id`.
Then: `subaward_date`, `fiscal_year`, `subaward_amount`, `subaward_amount_real2025`, `subaward_type`, `award_kind`, `description`, `sub_name`, `sub_uei`, `sub_state`, `sub_parent_name`, `sub_parent_uei`, `sub_business_types`, `sub_native_tier`, `prime_name`, `prime_uei`, `prime_parent_name`, `prime_parent_uei`, `prime_native_tier`, `prime_award_id`, `prime_award_unique_key`, `prime_award_amount`, `subaward_to_prime_ratio`, `prime_top_awarding_agency`, `prime_awarding_sub_agency`, `prime_set_aside`, `naics`, `naics_title`, `psc`, `psc_title`, `direction`, `subaward_number`, `subaward_sam_report_id`, `subaward_sam_report_year`, `source_url`, `source_dataset`.
Drop (36): the four `*_cage` (see the carve-out), `fetched_date`, `pre_2000_flag`, `floor_basis_field`, `source_population`, `subaward_exceeds_prime_flag`, `action_date_precedes_ffata_flag`, `duplicate_status` (publish primaries only), `promoted_date`, `deflator_factor_2025`, `inflation_base_year`, `subaward_sam_report_month`, `subaward_sam_report_last_modified_date`, `subaward_sam_report_id_basis`, `subaward_source_record_id_basis`, and all twenty-one `geo_*` except `geo_subawardee_city`, `geo_subawardee_state_code`, `geo_subawardee_county_name`.

### owned / native_owned_businesses (no sample in the repository)
Not audited: the flagship sample is one of the nineteen not yet added. When it is, run `python scripts/import_cedar_manifest.py --audit` before anything else: the six supporting tables of this collection carried withheld names and were struck on 2026-09-05, and the flagship has not been checked.

### nest / nest_enterprises (65 columns)
Front: `cedar_uid` (`owner_hub_cedar_uid` duplicates it on every sample row; keep one), `owner_hub_name` → `canonical_name`, `owner_hub_entity_class` → `entity_class`, `enterprise_id`.
Then: `enterprise_name`, `name_variants_observed`, `owner_class`, `owner_hub_state`, `parent_enterprise_id`, `parent_name`, `parent_is_hub`, `hierarchy_level`, `relationship`, `relation_class`, `relationship_as_recorded`, `ownership_percent_stated`, `sector`, `status`, `city`, `state_province`, `uei`, `cage_code` (carve-out), `in_federal_contracting`, `first_observed_year`, `last_observed_year`, `n_distinct_sources`, `evidence_class`, `evidence_human_reviewed`, `source_id`, `source_url`, `source_document`, `source_edition_date`, `fpds_declared_parent_name`, `fpds_parent_corroboration`.
Drop (28): `enterprise_name_normalized`, `status_basis`, `address_basis`, `address_is_publishable` (apply it, do not publish it), `identifier_basis`, `uei_candidate`, `uei_candidate_basis`, `identifier_status`, `in_federal_contracting_basis`, `identity_scope`, `assertion_class`, `n_source_observations`, `n_auto_ruled_observations`, `enterprise_existing_cedar_uid`, `constellation_edge_id`, `constellation_note`, `hub_resolution_method`, `hub_resolution_note`, `population_basis`, `publishable`, `publishable_basis` (same: apply), `retrieved_date`, `built_date`, `fpds_parent_corroboration_route`, `fpds_declared_parent_uei`, `fpds_declared_parent_observations`, `fpds_parent_resolves_to`, `fpds_parent_corroboration_basis`, `duplicate_name_variant_group`, `duplicate_name_variant_basis`.

### natural-resources / resource_revenue (45 columns)
Front: `cedar_uid`, `recipient_entity_name` → `canonical_name`, **add `entity_class`**, `resource_revenue_event_id`. (`recipient_entity_id` duplicates `cedar_uid`; keep one.)
Then: `payment_date`, `period_type`, `period_start`, `period_end`, `revenue_type`, `resource_type`, `commodity`, `product`, `mineral_lease_type`, `amount_usd`, `amount_usd_real2025`, `amount_sign_meaning`, `measurement_status`, `aggregation_level`, `beneficiary_entity_id`, `beneficiary_entity_name`, `beneficiary_note`, `payer_entity_id`, `payer_entity_name`, `operator_entity_id`, `operator_entity_name`, `land_status`, `allocation_formula`, `allocation_formula_effective_start`, `allocation_formula_effective_end`, `allocation_formula_source_url`, `geography_note`, `confidence`, `source_system`, `source_record_id`, `source_url`.
Drop (9): `related_asset_ids` (blank; keep if the asset table ships), `deflator_factor_2025`, `inflation_base_year`, `land_status_basis`, `fetched_date`, `built_date`, `cedar_uid_basis`, `record_scope_basis`, `entity_attribution_status`, `entity_attribution_basis`.

### nonprofits / np_orgs (67 columns)
Front: `cedar_uid`, `cedar_spine_canonical_name` → `canonical_name`, `cedar_spine_entity_class` → `entity_class`, `EIN`. (`entity_id` and `cedar_spine_entity_id` duplicate it; keep one. `cedar_native_entity_class` is the organization's own class; keep it after, renamed `org_entity_class`.)
Then: `org_name`, `state`, `city`, `ntee_code`, `classification_ruling`, `tier`, `confidence_tier`, `disposition`, `bmf_status`, `bmf_subsection`, `bmf_foundation_cd`, `bmf_irs_ruling_yyyymm`, `bmf_tax_period`, `bmf_revenue_amt`, `bmf_asset_amt`, `bmf_income_amt`, `bmf_vintage_fetched`, `ruling_authority`, `ruling_confidence`, `ruling_date`, `entity_match_method`, `entity_tier`, `cedar_link_tier`, `source_dataset`, `source_url`.
Drop (36): `evidence`, `tier_basis`, `funnel_stage`, `review_flag`, `review_flag_token`, `excluded_by_prior_ruling`, `exclusion_reason`, `canonical_name_token_match`, `n_coders_agree`, `bmf_in_snapshot`, `bmf_filing_req_cd`, `source_files`, `built_date`, `placename_risk_flag`, `tribe_canonical_name` (duplicates the spine name), `entity_match_basis`, `entity_keyed_date`, `cedar_link_basis`, `cedar_link_key`, `cedar_link_sources`, `disposition_basis`, `name_match_support`, `name_match_shared_tokens`, `name_match_support_measured_against`, `keyed_name_match_support`, `keyed_name_match_shared_tokens`, `keyed_name_match_residue`, `keyed_state_agreement`, `key_review_disposition`, `key_review_basis`, `key_redirect_proposed_entity_id`, `key_redirect_proposed_name`, `placename_refusal_rung`, `placename_refusal_basis`, `placename_refusal_date`. This table is a matcher's worksheet published whole; two-thirds of it is how the link was made.

## What to change, in order

1. In 770 and 1135, write the customer column order per table above (identity block
   first) and stop writing tier C to `dist/customer/` and to the samples. Keep the
   workspace tables as they are.
2. Add `entity_class` (and `canonical_name` where absent) from the register at write
   time, keyed on `cedar_uid`, so the three columns are the register's, not a copy
   that can drift.
3. Write `source_url` into funding, legislation and contractors from the award key
   or the bill's congress, type and number, so the file cites itself.
4. Re-run `scripts/import_cedar_manifest.py` (which now strikes any sample that
   carries a withheld name), then `node scripts/derive-explore.mjs`; the contracts
   re-derive and the `default_columns` in `explore.overrides.json` need renaming to
   match. The site's tests will name every declared column that no longer exists.
5. Publish the column list per table in the collection's documentation, one line a
   column, with the tier-B provenance columns explained.

## What the site already does

The viewer puts `cedar_uid`, the canonical name and the entity class first in every
table view regardless of the file's own order, pins the first two, and shows the
declared `default_columns` before the rest; the download keeps the file's order and
every column. So the order above is about the files a customer downloads, and about
not shipping a matcher's worksheet as a dataset.
