# Codebook — Nagpra

*58,067 rows across 2 file(s). Generated 2026-08-07.*

Variables marked **internal** are retained for auditing and are not included in published extracts.

| Variable | Type | Units / format | Filled | Description |
|---|---|---|---:|---|
| `document_number` | text | code | 100% | Federal Register document number. |
| `publication_date` | text | YYYY-MM-DD | 100% | Date published in the Federal Register. |
| `publication_year` | integer | YYYY | 100% | Year. |
| `notice_type` | text | categorical | 100% | Which NAGPRA notice this is. `inventory_completion` (25 U.S.C. 3003) publishes an inventory of human remains and associated funerary objects and the cultural affiliation found for them. `intent_to_repatriate` (25 U.S.C. 3004) covers unassociated funerary objects, sacred objects and objects of cultural patrimony; the 2023 rule renamed its title to 'Notice of Intended Repatriation' without changing the stage, and both wordings appear under this one value with the published wording kept in notice_title_form. `intended_disposition` (43 CFR 10.7) is a THIRD and different thing: remains from Federal or Tribal lands disposed of by statutory priority where no cultural affiliation was determined. Never merge the three. |
| `notice_title_form` | text |  | 100% | One of: `Notice of Inventory Completion`, `Notice of Intended Repatriation`, `Notice of Intent To Repatriate`, `Notice of Intent to Repatriate`, `Notice of Intended Disposition` |
| `statute_stage` | text |  | 100% | One of: `25 U.S.C. 3003 inventory / cultural affiliation`, `25 U.S.C. 3004 summary / cultural items`, `43 CFR 10.7 disposition of unclaimed remains` |
| `is_correction` | integer | 0/1 | 100% | 1 if the title marks this as a correction to an earlier notice. A correction amends a previous publication and must not be counted as an additional repatriation. |
| `title` | text | text | 100% | Title of the document. |
| `institution_name` | text | text | 100% | Name. |
| `institution_primary` | text | text | 100% | The first institution named in the notice title. Where a notice is issued jointly, this is the lead holder; use institution_names_all for every institution on the notice. |
| `institution_names_all` | text | pipe-separated | 100% | Every institution named in the notice title, pipe-separated, with city and state removed. Group on this rather than on the raw title string, or a jointly issued notice reads as an institution of its own. |
| `institution_city` | text | text | 98% | City. |
| `institution_state` | text | 2-letter code | 98% | State. |
| `institution_count` | integer | integer | 100% | Count. |
| `institution_name_basis` *(internal)* | text |  | 100% | One of: `title_colon`, `title_remainder`, `title_possession` |
| `institution_type_derived` | text |  | 100% | One of: `university`, `museum`, `federal_agency`, `other`, `state_agency`, `historical_society`, `tribal` |
| `responsible_party_statement` | text | text | 45% | The notice's own sentence naming who is responsible for its determinations - 'The determinations in this notice are the sole responsibility of X'. The National Park Service publishes these notices but is explicitly NOT responsible for their findings, and this column is where the notice says so. |
| `object_categories` | text | pipe-separated | 70% | Which statutory categories the notice's own subject statement names: human_remains, associated_funerary_objects, unassociated_funerary_objects, sacred_objects, objects_of_cultural_patrimony. Read from the SUMMARY or opening sentence only - the boilerplate elsewhere in a modern notice lists all five regardless. |
| `mni_total_stated` | integer | count of individuals | 63% | The minimum number of individuals the notice STATES for itself, taken from its own determination that the remains 'represent the physical remains of N individuals of Native American ancestry'. EMPTY means the notice states no single total - most often because it describes several removal events with their own minima. Those figures are kept verbatim in mni_statements and are NOT added together. Never sum, impute or estimate this column; a total that the institution did not state is not a fact about anybody's ancestors. |
| `mni_basis` *(internal)* | text |  | 100% | One of: `determinations_finding`, `no_mni_stated`, `single_description_statement`, `multiple_statements_not_summed` |
| `mni_statement_count` | integer | integer | 100% | Count. |
| `mni_statements` | text | text | 66% | Every minimum-number-of-individuals sentence found in the notice, verbatim and pipe-separated, so any total can be audited against the text that produced it. |
| `n_associated_funerary_objects_stated` | integer | integer | 24% | Count. |
| `n_unassociated_funerary_objects_stated` | integer | integer | 7% | Count. |
| `n_sacred_objects_stated` | integer | integer | 5% | Count. |
| `n_objects_of_cultural_patrimony_stated` | integer | integer | 5% | Count. |
| `cultural_items_total_stated` | integer | count of items | 3% | The total number of cultural items the notice states have been requested for repatriation. Empty where the notice gives more than one such total; those are never added together. |
| `removal_counties` | text | pipe-separated | 52% | Counties named in the notice's own 'removed from' statements. A county here is where the ancestors were taken FROM; it says nothing about which nation is affiliated, and county names in this corpus include Cherokee, Creek, Apache and Oneida. |
| `removal_states` | text | pipe-separated USPS codes | 66% | Two-letter USPS codes for the states named in the notice's 'removed from' statements - where the ancestors or items were taken from, not where the holding institution is. |
| `removal_location_statements` | text | text | 80% | The notice's own removal-location wording, verbatim, so any parsed county or state can be audited against the sentence it came from. |
| `removal_location_basis` *(internal)* | text |  | 80% | One of: `body_removal_statement`, `title_from_clause` |
| `repatriation_eligible_date` | text | YYYY-MM-DD | 40% | The date on or after which repatriation may occur - the opening of the statutory response window. Empty on older notices, which instead set a contact deadline; see response_deadline_date. |
| `response_deadline_date` | text | YYYY-MM-DD | 58% | The date by which another party must come forward, used by notices published before the 'on or after' wording was adopted. |
| `window_days_derived` | integer | days | 98% | Days between publication and the date repatriation may occur (or the response deadline on older notices). DERIVED by subtraction, not stated in the notice. |
| `n_consulted_named` | integer | integer | 100% | Count. |
| `n_consulted_resolved` | integer | integer | 100% | Count. |
| `consulted_entity_ids` | text | pipe-separated | 39% | Entity identifiers for parties the notice says were CONSULTED. Not an affiliation finding - see relationship. |
| `n_affiliated_named` | integer | integer | 100% | Count. |
| `n_affiliated_resolved` | integer | integer | 100% | Count. |
| `affiliated_entity_ids` | text | pipe-separated | 73% | Entity identifiers for parties the notice DETERMINED to be culturally affiliated. This is the legal finding. |
| `n_disposition_priority_named` | integer | integer | 100% | Count. |
| `n_disposition_priority_resolved` | integer | integer | 100% | Count. |
| `disposition_priority_entity_ids` | text | pipe-separated | 7% | Entity identifiers holding statutory priority for disposition under 43 CFR 10.7. Priority is not cultural affiliation. |
| `n_repatriation_recipient_named` | integer | integer | 100% | Count. |
| `n_repatriation_recipient_resolved` | integer | integer | 100% | Count. |
| `repatriation_recipient_entity_ids` | text | pipe-separated | 24% | Entity identifiers the notice states the material may go, or has gone, to. |
| `n_letter_of_support_named` | integer | integer | 100% | Count. |
| `n_letter_of_support_resolved` | integer | integer | 100% | Count. |
| `letter_of_support_entity_ids` | text | pipe-separated | 0% | Entity identifiers recorded as having written in support of another nation's repatriation claim. No determination was made about them. |
| `n_aboriginal_land_named` | integer | integer | 100% | Count. |
| `n_aboriginal_land_resolved` | integer | integer | 100% | Count. |
| `aboriginal_land_entity_ids` | text | pipe-separated | 9% | Entity identifiers whose aboriginal land the ancestors were removed from, per Indian Claims Commission or Court of Federal Claims judgments. A territorial finding, not an affiliation finding. |
| `n_parties_named` | integer | integer | 100% | Count. |
| `n_entities_resolved` | integer | integer | 100% | Count. |
| `has_resolved_entity` | integer | 0 to 1 | 100% | One of: `1`, `0` |
| `lineal_descendant_determination` | integer | 0/1 | 100% | 1 if the notice determines that a lineal descendant, rather than a nation, is entitled to the material (25 U.S.C. 3005(a)(1)). Such a notice correctly names no affiliated tribe. The individual is never recorded. |
| `culturally_unidentifiable` | integer | 0/1 | 100% | 1 if the notice determines that a relationship of shared group identity CANNOT be reasonably traced to any present-day Indian Tribe (25 U.S.C. 3001(2); disposition then follows 43 CFR 10.11). This is an affirmative determination, not a gap: such a notice names no culturally affiliated nation because the institution found none, and it must never be read as a parsing failure. Culturally unidentifiable human remains are the most contested category in NAGPRA practice. |
| `parse_template` | text | categorical | 100% | Which drafting era the notice belongs to, which governs how much structure is recoverable: `A_early_freeform` (1994-96, no headings), `B_nps_template` (headed Consultation / Determinations sections), `C_2024_rule` (the 2023 rule's SUMMARY / Determinations / Requests layout). |
| `spans_found` *(internal)* | text |  | 95% |  |
| `agency_names` | text | text | 100% | Issuing agencies. |
| `html_url` | text | URL | 100% | Link to the document. |
| `pdf_url` | text | URL | 100% | Link to the document as filed. |
| `full_text_url` | text | URL | 100% | Link. |
| `source_url` | text | URL | 100% | Link to the record's published source. |
| `parent_dataset` | text |  | 100% | One of: `federal_actions.csv (Cedar Press Dataset 9)` |
| `fetched_date` | text | YYYY-MM-DD | 100% | Date. |
| `relationship` | text | categorical | 100% | What the notice says this party's relation to the material IS. `consulted` - the institution consulted them. `culturally_affiliated` - the institution DETERMINED a relationship of shared group identity under 25 U.S.C. 3001(2). `repatriation_recipient` - the notice states the material may go, or has gone, to them. `disposition_priority` - statutory priority for disposition under 43 CFR 10.11, which applies precisely WHERE NO AFFILIATION WAS FOUND. `letter_of_support` - the notice records that they wrote in support of another nation's claim; no determination was made about them. `aboriginal_land` - the Indian Claims Commission or the Court of Federal Claims established that the land the ancestors were removed FROM is this nation's aboriginal territory; a judicial fact about territory, NOT a statement that the ancestors are of that nation. THESE ARE DIFFERENT LEGAL FINDINGS AND MUST NEVER BE COLLAPSED. A notice routinely consults many more nations than it finds affiliated with, and reporting a consultation as an affiliation asserts a claim about ancestry that the notice does not make. |
| `party_name_verbatim` | text | text | 100% | The nation, organisation or agency name exactly as the notice writes it, after list-splitting only. Historical names are preserved: a 1996 notice says 'Devil's Lake Sioux Tribe' and that is what this column holds, even though the nation is now the Spirit Lake Tribe. This column is authoritative for what was published; tribe_id is not. |
| `party_name_as_published` | text | text | 100% | The undivided string the notice published, before any splitting. Where a single published phrase named two nations, several rows share one value here. |
| `tribe_id` | text | code | 93% | Cedar Press permanent identifier for the Native entity. Stable across releases; use this to join datasets. |
| `canonical_name` | text | text | 93% | Cedar Press standard name for the Native entity. |
| `resolve_method` *(internal)* | text |  | 100% |  |
| `resolve_status` | text | categorical | 100% | Whether the published party name was matched to a Cedar Press entity: `resolved`, `unresolved`, or `generic_reference` (the notice referred to 'the appropriate Indian Tribes' and named no one). `unresolved` means the name is real and recorded but did not match the current entity spine - most often a historical name. It never means the consultation did not happen. |
| `confidence_tier` | text | category | 95% | Publication tier. A = verified, publishable. B = provisional, withheld from published extracts. C = unattributed. X = ruled out. |
| `source_span_label` | text |  | 100% | One of: `affiliation_finding`, `consultation_section`, `body_sentence`, `repatriation_sentence`, `aboriginal_land_finding`, `disposition_finding`, `affiliation_finding+letters_of_support`, `consultation_section+letters_of_support` |
| `source_span_text` | text | text | 100% | Free text. |

## Value sets

- **`notice_type`** — `inventory_completion`, `intent_to_repatriate`, `intended_disposition`
- **`notice_title_form`** — `Notice of Inventory Completion`, `Notice of Intended Repatriation`, `Notice of Intent To Repatriate`, `Notice of Intent to Repatriate`, `Notice of Intended Disposition`
- **`statute_stage`** — `25 U.S.C. 3003 inventory / cultural affiliation`, `25 U.S.C. 3004 summary / cultural items`, `43 CFR 10.7 disposition of unclaimed remains`
- **`institution_type_derived`** — `university`, `museum`, `federal_agency`, `other`, `state_agency`, `historical_society`, `tribal`
- **`object_categories`** — `associated_funerary_objects|human_remains`, `human_remains`, `unassociated_funerary_objects`, `objects_of_cultural_patrimony`, `sacred_objects`, `associated_funerary_objects`, `sacred_objects|objects_of_cultural_patrimony`, `unassociated_funerary_objects|sacred_objects|objects_of_cultural_patrimony`, `unassociated_funerary_objects|objects_of_cultural_patrimony`, `unassociated_funerary_objects|sacred_objects`, `unassociated_funerary_objects|associated_funerary_objects|sacred_objects|objects_of_cultural_patrimony|human_remains`, `unassociated_funerary_objects|associated_funerary_objects`, `objects_of_cultural_patrimony|human_remains`, `unassociated_funerary_objects|associated_funerary_objects|human_remains`, `unassociated_funerary_objects|human_remains`
- **`parse_template`** — `B_nps_template`, `C_2024_rule`, `A_early_freeform`, `correction_unheaded`
- **`agency_names`** — `Interior Department; National Park Service`, `Interior Department`, `Interior Department;`
- **`relationship`** — `culturally_affiliated`, `consulted`, `repatriation_recipient`, `aboriginal_land`, `disposition_priority`, `letter_of_support`
- **`resolve_status`** — `resolved`, `unresolved`, `generic_reference`
- **`confidence_tier`** — `B`, `C`, `X`
- **`source_span_label`** — `affiliation_finding`, `consultation_section`, `body_sentence`, `repatriation_sentence`, `aboriginal_land_finding`, `disposition_finding`, `affiliation_finding+letters_of_support`, `consultation_section+letters_of_support`
