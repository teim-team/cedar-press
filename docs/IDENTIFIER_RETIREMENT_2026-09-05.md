# Identifier retirement report

Generated from `data/cedar/field_map.json` and the sample headers by `scripts/field-map-markdown.mjs`; edit the map, not this file. Written 2026-09-05 under the retirement rule in `docs/PUBLIC_DATASET_SPEC_2026-09-05.md` (addendum): migrate, reconcile, verify, retire, regression-test.

## The rule, as enforced

`cedar_uid` is Cedar's one cross-dataset identity. Every competing entity identifier in a flagship's header has a retirement entry in the map with what it identifies and its disposition. The writer (`cedar_publication.apply_field_map`) enforces the dispositions on every build: an `alias_verified` column is compared to `cedar_uid` on every row and the dataset is refused where they differ; an `adjudicate` column stops the dataset wherever it is populated, and is neither retained nor deleted; a `retired_scheme` name in any shipped value, or a prohibited name in the header, stops the dataset. The regression tests (`server/tests/test_field_map.py` and the site's explore test suite) fail if a prohibited identifier returns to any approved header, and the writer fails at build if one returns to a value.

`rows_affected` below is the count of rows carrying the identifier in the ten-row sample; the writer prints the full-table count on every build as `retired: dataset | old_identifier | what_it_identified | cedar_uid_or_replacement | disposition | rows_affected | unresolved_count`, and that line is the report row for the release.

## Flagship identifiers

| dataset | old_identifier | what_it_identified | cedar_uid_or_replacement | disposition | rows_affected (sample) | unresolved_count (sample) |
|---|---|---|---|---|---:|---:|
| `funding` | `recipient_duns` | the recipient in the pre-2022 federal record | recipient_uei and cedar_uid | internal_crosswalk | 10 | 0 |
| `funding` | `attribution_status` | how the row was attributed, in a vocabulary naming the retired scheme | a recoded attribution_status vocabulary | retired_scheme | 10 | 10 |
| `lobbying` | `entity_id` | the canonical Native entity, as a second spelling of cedar_uid on the same row | cedar_uid | alias_verified | 10 | 0 |
| `lobbying` | `client_id` | the client in the LDA database | client_id, kept | object_id | 10 | 0 |
| `lobbying` | `registrant_id` | the registrant in the LDA database | registrant_id, kept | object_id | 10 | 0 |
| `lobbying` | `attribution_withdrawn_entity_id` | the entity a withdrawn attribution pointed at | attribution_withdrawn_reason | internal_crosswalk | 0 | 0 |
| `natural-resources` | `recipient_entity_id` | the canonical Native entity, as a second spelling of cedar_uid on the same row | cedar_uid | alias_verified | 10 | 0 |
| `natural-resources` | `beneficiary_entity_id` | the beneficiary, in its declared namespace | kept as beneficiary_entity_id | object_id | 10 | 0 |
| `natural-resources` | `payer_entity_id` | the payer, in its declared namespace | kept as payer_entity_id | object_id | 10 | 0 |
| `natural-resources` | `operator_entity_id` | the operator, in its declared namespace | kept as operator_entity_id | object_id | 0 | 0 |
| `nest` | `enterprise_id` | the enterprise (a business), not the Native entity | kept as enterprise_id | object_id | 10 | 0 |
| `nest` | `owner_hub_cedar_uid` | the canonical Native entity, as a second spelling of cedar_uid on the same row | cedar_uid | alias_verified | 10 | 0 |
| `nest` | `uei_candidate` | a candidate UEI for the enterprise | uei, where verified | internal_crosswalk | 0 | 0 |
| `nest` | `enterprise_existing_cedar_uid` | the enterprise as a register entity in its own right, distinct from its owner | enterprise_id, or a documented cross-reference to the enterprise's own cedar_uid | adjudicate | 1 | 1 |
| `nonprofits` | `entity_id` | unknown: an earlier or different entity link that disagrees with cedar_uid on at least one row | cedar_uid | adjudicate | 2 | 2 |
| `nonprofits` | `cedar_spine_entity_id` | the spine entity the organization was keyed to before a redirect that cedar_uid reflects and this column does not, on at least one row | cedar_uid | adjudicate | 9 | 9 |
| `nonprofits` | `key_redirect_proposed_entity_id` | a proposed redirect of the entity link | cedar_uid, once the redirect is ruled | internal_crosswalk | 0 | 0 |

The three findings that stop a dataset today, from the samples: Funding's `attribution_status` carries the value `cedar_neid` on every sample row (a vocabulary naming the retired scheme; recode it); NEST's `enterprise_existing_cedar_uid` is populated where the enterprise is itself a register entity and differs from the owner's uid (adjudicate: the enterprise's own cedar_uid is a real cross-reference, not an alias); Nonprofits' `entity_id` and `cedar_spine_entity_id` disagree with `cedar_uid` on the same row (adjudicate: the link was redirected and the two columns were not). None of these is deleted; the writer refuses those three datasets until they are settled.

## Supporting tables

Supporting tables are not customer downloads, but the rule reaches the whole pipeline: every supporting-table sample column that names a competing identifier, for the terminal to migrate to `cedar_uid` or an object identifier, move to the identity layer, or adjudicate. The pattern is the same one the regression test applies to public headers.

| table | columns |
|---|---|
| `contractors/contractor_ranking` | `owner_entity_id` |
| `deals/deals_party_matches` | `proposed_tribe_id`, `proposed_name` |
| `deals/ownership_events` | `native_entity_neid`, `neid_join_status`, `entity_id` |
| `deals/tribal_resolution_financings` | `entity_id` |
| `federal-register/fr_ex_parte_parties` | `resolved_native_entity_id` |
| `federal-register/fr_ex_parte_party_entity_links` | `resolved_native_entity_id` |
| `federal-register/nepa_administrative_record_parties` | `resolved_native_entity_id` |
| `federal-register/nepa_eplanning_projects` | `tribe_ids_named_in_record` |
| `federal-register/section_106_project_parties` | `resolved_native_entity_id` |
| `funding/faads_identifier_coverage_by_agency_year` | `pct_with_duns`, `pct_with_duns_tribal_rows_only` |
| `funding/faads_transactions` | `recipient_duns` |
| `funding/faads_transactions_all_agencies` | `recipient_duns` |
| `funding/funding_identifier_harvest` | `recipient_duns` |
| `funding/native_passthrough` | `from_tribe_id`, `to_tribe_id` |
| `funding/native_passthrough_pairs` | `from_tribe_id`, `to_tribe_id` |
| `legislation/congressional_correspondence_log` | `tribe_entity_id` |
| `lobbying/admin_appeal_decisions` | `native_entity_candidate_ids`, `native_entity_candidate_names` |
| `lobbying/admin_appeal_parties` | `resolved_entity_id`, `entity_link_held_candidate_id`, `entity_link_held_candidate_name` |
| `lobbying/admin_appeal_positions` | `native_entity_id` |
| `lobbying/advocacy_passthrough_2026-08-07` | `funder_entity_id`, `recipient_entity_id` |
| `lobbying/advocacy_passthrough` | `funder_entity_id`, `recipient_entity_id` |
| `lobbying/earmarks` | `entity_id` |
| `lobbying/ferc_docket_filings` | `resolved_native_entity_id` |
| `lobbying/ferc_docket_parties` | `resolved_native_entity_id` |
| `lobbying/ferc_ex_parte_communications` | `resolved_native_entity_id` |
| `lobbying/ferc_ex_parte_parties` | `resolved_native_entity_id` |
| `lobbying/ferc_tribal_dockets` | `applicant_resolved_native_entity_id` |
| `lobbying/hearing_appearances` | `entity_id` |
| `lobbying/lobbying_issue_families_filing` | `entity_id` |
| `lobbying/lobbying_registrant_client_relationships` | `native_entity_id` |
| `lobbying/lobbying_registrant_identifiers` | `prime_tribe_id` |
| `lobbying/lobbying_registrant_native_ownership_evidence` | `native_entity_id` |
| `lobbying/lobbying_registrants` | `native_ownership_entity_id` |
| `lobbying/nonprofit_schedule_c_lobbying` | `cedar_entity_id` |
| `lobbying/nrc_meeting_participants` | `resolved_entity_id`, `entity_link_held_candidate_id`, `entity_link_held_candidate_name`, `native_entity_id` |
| `lobbying/oira_meeting_participants` | `entity_id` |
| `lobbying/oira_meetings` | `entity_id` |
| `lobbying/tribe_year_lobbying_panel` | `entity_id` |
| `natural-resources/resource_assets` | `operator_entity_id` |
| `natural-resources/resource_parties` | `entity_id` |
| `natural-resources/tribal_bond_issuances` | `issuer_entity_id` |
| `nonprofits/fac_tribal_single_audits` | `entity_id` |
| `nonprofits/grantmaker_funding_flows` | `cedar_funder_spine_entity_id`, `cedar_recipient_spine_entity_id` |
| `nonprofits/np_ein_entity_hub` | `entity_id` |
| `nonprofits/np_financials` | `in_recheck_candidate`, `cedar_spine_entity_id` |
| `nonprofits/np_org_scale` | `in_recheck_candidate` |
| `nonprofits/np_schedule_i_filers` | `filer_tribe_id_np_orgs`, `cedar_filer_spine_entity_id` |
| `nonprofits/np_schedule_i_grants` | `recipient_np_orgs_tribe_id`, `recipient_entity_id`, `cedar_filer_spine_entity_id`, `cedar_recipient_spine_entity_id` |

48 supporting tables carry such a column in their samples. Columns whose name ends in `_entity_id` are listed because they may hold a Cedar uid under another name (an alias to verify) or a non-Cedar namespace (an object id to keep, as Natural Resources' payer and operator ids are); each needs the same determination the flagship columns received.

## The rest of the pipeline

Measured with `git grep -il` on 2026-09-05, as the inventory of remaining dependencies, not as a claim they are all customer-facing: 84 files under `code/` mention DUNS, 43 mention the NEID scheme by name, 53 mention CICD, and 67 files across the repository mention Casino City. `code/843_retire_cicd_scheme.py` and `code/844_nuke_cicd.py` did the first retirement; `cedar_publication.translate_neid_values` still translates NEID tokens inside strings at load, which is the migration half of the rule and stays. Two sample files carry a retired scheme's name in a value: `funding/federal_funding_transactions` (`attribution_status`, above) and `deals/ownership_events` (`neid_join_status`, a supporting table).

