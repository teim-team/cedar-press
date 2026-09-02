# Codebook — Compacts

*9,057 rows across 5 file(s). Generated 2026-08-07.*

Variables marked **internal** are retained for auditing and are not included in published extracts.

| Variable | Type | Units / format | Filled | Description |
|---|---|---|---:|---|
| `compact_id` | text | code | 100% | Identifier. |
| `entity_id` | text | code | 92% | Identifier. |
| `tribe` | text | text | 100% | Tribe as named in the source record. |
| `state` | text | 2-letter code | 100% | US state or territory. |
| `original_effective_date` | text | YYYY-MM-DD | 100% | Date. |
| `approval_type` | text |  | 100% | One of: `secretarial`, `deemed-approved`, `secretarial-procedures`, `unknown` |
| `FR_citation` | text | citation | 78% | Federal Register citation approving the compact. |
| `term_end` | text | YYYY-MM-DD | 25% | Date the compact term ends. |
| `renewal_provisions` | text | text | 24% | Renewal terms stated in the compact. |
| `status` | text | text | 100% | The asset's operating status as the source states it. |
| `successor_compact_id` | text | code | 58% | Identifier. |
| `instrument_type` | text |  | 100% | One of: `compact`, `secretarial-procedures`, `orphan-no-base-instrument-in-index` |
| `tribe_name_basis` *(internal)* | text |  | 100% | One of: `bia_tribes_column (agrees with BIA title)`, `bia_title (BIA tribes column conflicts with title and PDF)`, `bia_tribes_column (title conflicts but not corroborated by PDF name)`, `bia_tribes_column (title empty; cross-check impossible)` |
| `bia_tribes_column` | text | text | 100% | Tribes named in the agency record. |
| `bia_tribes_column_conflict` | integer | 0 to 1 | 100% | One of: `0`, `1` |
| `bia_title` | text | text | 99% | Title of the agency record. |
| `bia_decision` | text |  | 100% | One of: `Approve`, `Deemed Approved`, `Secretarial Procedures`, `Extensions` |
| `bia_decision_date` | text | YYYY-MM-DD | 100% | Date. |
| `original_effective_date_basis` *(internal)* | text |  | 100% | One of: `fr_publication_date_from_notice_url`, `bia_index_decision_date` |
| `FR_notice_url` | text | URL | 78% | Link to the approving Federal Register notice. |
| `n_versions` | integer | integer | 100% | Count. |
| `term_end_basis` *(internal)* | text |  | 25% |  |
| `status_basis` *(internal)* | text |  | 100% |  |
| `source_pdf` | text | URL | 100% | Link to the source document. |
| `source_url` | text | URL | 100% | Link to the record's published source. |
| `pre_2000_flag` | integer | 0/1 | 31% | 1 when the record predates the 2000 coverage floor. Such records are retained but fall outside the standard reporting window. |
| `floor_basis_field` | text |  | 100% | One of: `original_effective_date` |
| `tribe_id` | text | code | 99% | Cedar Press permanent identifier for the Native entity. Stable across releases; use this to join datasets. |
| `tribe_canonical_name` | text | text | 99% | Name. |
| `entity_match_method` *(internal)* | text |  | 99% | One of: `alias`, `inherited_from_compact_id`, `containment`, `exact`, `core`, `resolver_core` |
| `entity_tier` | text |  | 99% | One of: `A`, `B` |
| `entity_match_basis` *(internal)* | text |  | 100% |  |
| `entity_keyed_date` | text | YYYY-MM-DD | 100% | Date. |
| `event_id` | text | code | 100% | Congress.gov committee-meeting event identifier. |
| `event_date` | text | YYYY-MM-DD | 100% | Date. |
| `event_type` | text |  | 100% | One of: `secretarial_disapproval` |
| `description` | text | text | 100% | Description of the item. |
| `basis` | text | text | 100% | The evidence behind this party link - what the source said, or which name the entity resolved from. |
| `version_id` | text | code | 100% | Identifier. |
| `term_type` | text |  | 100% | One of: `revenue_share_base`, `game_scope`, `exclusivity`, `revenue_share_rate`, `dispute_provision`, `local_share`, `machine_cap`, `tier_structure` |
| `value` | text | text | 100% | The term as stated in the compact. Numeric terms also appear in value_numeric. |
| `unit` | text | category | 100% | Unit the value is expressed in, such as devices, tables, percent, or US dollars. |
| `applies_to` | text | category | 15% | Whether the term applies to a single gaming facility or to the tribe's gaming as a whole. Blank where the compact language supports neither reading. |
| `source_page` | integer | integer | 100% | Page of the source document. |
| `quote` | text | text | 100% | Quoted compact language supporting the recorded term. |
| `doc_zone` | text | category | 100% | Which part of the source document the quote comes from. |
| `extraction_method` *(internal)* | text |  | 100% | One of: `regex v5 (95_parse_compact_terms.py); page-wise PyMuPDF re-extraction; TOC and approval-letter zoning guards; verbatim quote and PDF page retained on every row`, `regex v4 (15d_terms_extract.py) + quote re-verification (15e), verbatim quote and PDF page retained` |
| `pilot_validated_type` | text |  | 100% | One of: `pilot 14/14 sampled of 19; correct as DEFINED TERM, over-claims where the instrument defines the term but shares no revenue`, `pilot 6/6 (locates the authorised-games section; does not enumerate games)`, `pilot 12/12 sampled pre-dedup`, `pilot 4/4; corpus spot check 7/12 clear, 2/12 wrong, 3/12 unverifiable -> strict quote re-verification applied in 15e`, `pilot 8/8`, `NO pilot hits; corpus sample 9/10 correct as a located provision`, `pilot 1/1; corpus spot check 11/12 values correct, applies_to errs toward UNSET`, `NO pilot hits; corpus sample 8/10 correct content; value is located schedule text, brackets are NOT parsed` |
| `term_id` | text | code | 100% | Cedar-internal identifier for one extracted compact term. |
| `amendment_number` | integer | text | 93% | Amendment number as recorded on the instrument. |
| `version_seq` | integer | integer | 100% | Order of the instrument within its compact. |
| `version_role` | text | category | 100% | Whether the instrument is an original compact, an amendment, or an extension. |
| `doc_kind` | text | category | 100% | What kind of document the source is. |
| `term_field` | text | category | 100% | Which term of the compact this row records, such as a device cap, a revenue-sharing rate, or a reporting requirement. |
| `value_numeric` | numeric | number | 21% | Numeric form of the term where one exists. |
| `measurement_type` | text | category | 3% | What kind of quantity the value is. Caps are AUTHORIZED_MAXIMUM: the maximum a compact permits, never the number in operation. |
| `revenue_concept` | text | text | 31% | The revenue measure the compact names, in the compact's own words, such as Class III net win or adjusted gross gaming revenue. |
| `base_scope` | text | category | 14% | Whether the compact ties the revenue the rate applies to a single gaming facility, or to the tribe's gaming as a whole. A tribe-wide base does not yield a property revenue figure. |
| `formula_invertibility` | text | category | 14% | Whether a payment under this compact can be divided by a single rate to recover the revenue amount exactly. |
| `bound_basis` | text | text | 6% | What prevents a payment from being divided by a single rate to recover the revenue amount exactly, such as a bracket schedule, a minimum payment, or more than one rate in the same compact. |
| `revenue_evidence_class` | text | category | 9% | The level and strength a revenue figure derived from this term would carry. |
| `effective_from` | text | YYYY-MM-DD | 100% | Date the term takes effect. |
| `effective_from_basis` | text | category | 100% | What the start date is taken from: the compact's stated effective date, or the approval date of the instrument that introduced the term. |
| `effective_to` | text | YYYY-MM-DD | 47% | Date the term stops applying. Blank where the compact states no end and no later instrument replaces it. |
| `effective_to_basis` | text | category | 100% | Why the term ends when it does: a later instrument replaced it, the compact states an end date, or the compact states none. |
| `confidence_tier` | text | category | 100% | Publication tier. A = verified, publishable. B = provisional, withheld from published extracts. C = unattributed. X = ruled out. |
| `is_instrument_language` | text | yes/no | 100% | Whether the quoted text is the compact itself rather than a transmittal or approval letter bundled with it. |
| `source_quote` | text | text | 100% | The document's own words supporting the recorded term. |
| `fetched_date` | text | YYYY-MM-DD | 100% | Date. |
| `built_by_script` | text |  | 100% | One of: `95_parse_compact_terms.py` |
| `report_id` | text | code | 100% | Cedar-internal identifier for one reporting obligation recorded in a compact. |
| `obligation_type` | text | category | 100% | The kind of obligation recorded. REQUIRED_REPORT_EXISTS means the compact requires a report to be filed. |
| `frequency` | text | category | 100% | How often the report must be filed. |
| `recipient_agency` | text | text | 61% | The agency the report must be filed with, as named in the compact. |
| `recipient_side` | text | category | 100% | Whether the receiving agency is a state, federal, or tribal body. |
| `other_agencies_named` | text | text | 41% | Additional agencies named in the same clause. |
| `fields_required` | text | text | 45% | The items the report must contain, such as net win, device counts, or licensing records. |
| `report_subject_level` | text | category | 100% | Whether the report covers each gaming facility separately or the tribe's gaming as a whole. |
| `public_availability` | text | category | 100% | What the reporting clause itself says about disclosure of the report. |
| `version_has_confidentiality_provision` | text | yes/no | 100% | Whether the same instrument contains a confidentiality provision elsewhere in its text. |

## Value sets

- **`approval_type`** — `secretarial`, `deemed-approved`, `secretarial-procedures`, `unknown`
- **`status`** — `renegotiated`, `unknown`, `active`, `expired`
- **`instrument_type`** — `compact`, `secretarial-procedures`, `orphan-no-base-instrument-in-index`
- **`bia_decision`** — `Approve`, `Deemed Approved`, `Secretarial Procedures`, `Extensions`
- **`entity_tier`** — `A`, `B`
- **`description`** — `Middletown Rancheria of Pomo Indians Tribal State Gaming Compact Disapproval Letter`, `Santa Rosa Indian Community of the Santa Rosa Rancheria Tribal State Gaming Compact Disapproval Letter`, `Saint Regis Mohawk Tribe Tribal State Gaming Compact Disapproval Letter`, `Cheyenne and Arapaho Tribes Tribal State Gaming Compact Disapproval Letter`, `Yankton Sioux Tribe Tribal State Gaming Compact Disapproval Letter`, `Nooksack Indian Tribe Tribal State Gaming Compact Disapproval Letter`, `Big Sandy Rancheria of Western Mono Indians Tribal State Gaming Compact Disapproval Letter`, `Picayune Rancheria of Chukchansi Indians Tribal State Gaming Compact Disapproval Letter`, `Ewiiaapaayp Band of Kumeyaay Indians Tribal State Gaming Compact Disapproval Letter`, `Habematolel Pomo of Upper Lake Tribal State Gaming Compact Disapproval Letter`, `Rincon Band of Luiseno Mission Indians of the Rincon Reservation Tribal State Gaming Compact Disapproval Letter`, `Pinoleville Pomo Nation Tribal State Gaming Compact Disapproval Letter`, `Table Mountain Rancheria Tribal State Gaming Compact Disapproval Letter`, `Sac and Fox Nation of Missouri in Kansas and Nebraska Tribal State Gaming Compact Disapproval Letter`, `Jena Band of Choctaw Indians Tribal State Gaming Compact Disapproval Letter`, `Mashpee Wampanoag Tribe Tribal State Gaming Compact Disapproval Letter`, `Pueblo of Jemez Tribal State Gaming Compact Disapproval Letter`, `Pueblo of Zuni Tribal State Gaming Compact Disapproval Letter`, `Stockbridge-Munsee Band of Mohicans Tribal State Gaming Compact Disapproval Letter`, `Comanche Nation Tribal State Gaming Compact Disapproval Letter`, `Confederated Tribes of the Warm Springs Reservation Tribal State Gaming Compact Disapproval Letter`, `Stillaguamish Tribe of Indians Tribal State Gaming Compact Disapproval Letter`, `Forest County Potawatomi Community Tribal State Gaming Compact Disapproval Letter`, `Forest County Potawatomi Community Tribal State Gaming Compact`, `Menominee Indian Tribe Tribal State Gaming Compact Disapproval Letter`
- **`term_type`** — `revenue_share_base`, `game_scope`, `exclusivity`, `revenue_share_rate`, `dispute_provision`, `local_share`, `machine_cap`, `tier_structure`
- **`unit`** — `text`, `defined_term`, `percent`, `boolean`, `date`, `game_list`, `enum`, `usd_per_device`, `devices`, `percent_of_bracket`, `usd`, `facilities`, `schedule_text_located`, `tables`
- **`applies_to`** — `tribe_wide`, `facility`, `statewide`
- **`doc_zone`** — `instrument_text`, `approval_letter`
- **`pilot_validated_type`** — `pilot 14/14 sampled of 19; correct as DEFINED TERM, over-claims where the instrument defines the term but shares no revenue`, `pilot 6/6 (locates the authorised-games section; does not enumerate games)`, `pilot 12/12 sampled pre-dedup`, `pilot 4/4; corpus spot check 7/12 clear, 2/12 wrong, 3/12 unverifiable -> strict quote re-verification applied in 15e`, `pilot 8/8`, `NO pilot hits; corpus sample 9/10 correct as a located provision`, `pilot 1/1; corpus spot check 11/12 values correct, applies_to errs toward UNSET`, `NO pilot hits; corpus sample 8/10 correct content; value is located schedule text, brackets are NOT parsed`
- **`version_role`** — `original-instrument`, `amendment`, `extension`
- **`doc_kind`** — `instrument_text`, `letter_or_short_doc`
- **`term_field`** — `revenue_sharing_base`, `other_mitigation_payments`, `revenue_sharing_rate`, `class_iii_devices_authorized`, `confidentiality_provision`, `expiration_date`, `gaming_types_authorized`, `machine_based_payment`, `local_payment`, `sports_wagering_authorized`, `progressive_rate_schedule`, `device_caps`, `state_payment`, `mobile_wagering_scope`, `internet_wagering_authorized`, `facility_caps`, `hotel_tax_equivalent`, `minimum_payment`, `table_caps`
- **`base_scope`** — `tribe`, `facility`
- **`formula_invertibility`** — `NOT_INVERTIBLE`, `NOT_APPLICABLE_APPROVAL_LETTER`, `INVERTIBLE_FLAT_RATE`
- **`bound_basis`** — `progressive_rate_schedule_present;no_flat_rate_stated_only_a_bracket_schedule`, `2_distinct_rates_in_instrument`, `3_distinct_rates_in_instrument`, `per_device_payment_component_present`, `4_distinct_rates_in_instrument`, `5_distinct_rates_in_instrument`, `progressive_rate_schedule_present`, `progressive_rate_schedule_present;no_flat_rate_stated_only_a_bracket_schedule;per_device_payment_component_present`, `minimum_payment_floor_present`
- **`revenue_evidence_class`** — `TRIBE_LEVEL_REVENUE`, `BOUNDED_DERIVED_REVENUE`, `EXACT_DERIVED_PROPERTY_REVENUE`
- **`effective_from_basis`** — `compact original_effective_date`, `version approval_date`
- **`is_instrument_language`** — `yes`, `no`
- **`frequency`** — `unspecified`, `annual`, `quarterly`, `on_request`, `monthly`, `within_10_days`, `within_30_days`, `within_60_days`, `within_15_days`, `weekly`, `within_20_days`, `within_21_days`, `within_90_days`, `daily`, `within_120_days`, `within_7_days`, `within_5_days`, `semiannual`, `within_180_days`
- **`recipient_side`** — `unspecified`, `state`, `tribal`, `federal`
- **`report_subject_level`** — `unspecified`, `facility`
- **`public_availability`** — `NOT_STATED_IN_COMPACT`, `CONFIDENTIAL_PER_COMPACT`, `PUBLIC_PER_COMPACT`
- **`version_has_confidentiality_provision`** — `yes`, `no`
