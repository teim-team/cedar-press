# Codebook — Bills Votes

*147,788 rows across 6 file(s). Generated 2026-08-07.*

Variables marked **internal** are retained for auditing and are not included in published extracts.

| Variable | Type | Units / format | Filled | Description |
|---|---|---|---:|---|
| `bill_id` | text | code | 98% | Identifier. |
| `congress` | integer | integer | 100% | Number of the Congress. |
| `chamber` | text |  | 100% | One of: `House`, `Senate`, `house`, `senate` |
| `number` | integer | integer | 100% | Measure number. |
| `title` | text | text | 100% | Title of the document. |
| `policy_area` | text | category | 97% | Policy area assigned to the measure. |
| `bill_scope` | text |  | 95% | One of: `general`, `tribe-specific` |
| `affected_entities` | empty | text | 0% | Native entities the measure affects. |
| `sponsor` | text | text | 97% | Member sponsoring the measure. |
| `introduced_date` | text | YYYY-MM-DD | 100% | Date. |
| `latest_action` | text | text | 100% | Most recent action on the measure. |
| `outcome` | text |  | 89% | One of: `died-in-committee`, `enacted`, `passed-one-chamber`, `pending`, `vetoed` |
| `companion_bill_id` | text | code | 29% | Identifier. |
| `bill_type` | text | category | 100% | Chamber and kind of measure, such as HR or S. |
| `sponsor_bioguide_id` | text | code | 96% | Identifier. |
| `latest_action_date` | text | YYYY-MM-DD | 100% | Date. |
| `cosponsor_count` | integer | integer | 70% | Count. |
| `n_rollcalls` | integer | integer | 100% | Count. |
| `has_rollcall` | integer | 0 to 1 | 100% | One of: `0`, `1` |
| `bill_scope_basis` *(internal)* | text |  | 99% |  |
| `outcome_basis` *(internal)* | text |  | 99% | One of: `latest_action_text`, `no_action_record_available`, `latest_action_text; congress 119 still in session on 2026-08-05`, `tribal_bill_intros.final_status` |
| `companion_basis` *(internal)* | text |  | 29% | One of: `identical_normalized_title_same_congress_opposite_chamber` |
| `classification_source` | text | categorical | 100% | How a bill's Native-relevance classification was arrived at, e.g. `two_coder_adjudicated` or `single_coded_keyword_rule`. An adjudicated classification carries more weight than a keyword one. |
| `classification_kappa` | text |  | 14% | One of: `0.952`, `-1.000 (not meaningful: disjoint coder search strategies)` |
| `record_basis` *(internal)* | text |  | 100% | One of: `congress_api_bill_metadata`, `voteview_rollcall_only + congress_gov_bill_endpoint_title_backfill`, `voteview_rollcall + congress_api_bill_metadata`, `congress_api_bill_metadata (all_bill_intros.csv)`, `voteview_rollcall_only` |
| `source_file` *(internal)* | text |  | 100% | One of: `tribal_bill_intros.csv`, `HSall_rollcalls.csv (via tribal roll-call classification)`, `all_bill_intros.csv via 73_bills_votes_completion.py --sweep` |
| `build_date` | text | YYYY-MM-DD | 100% | Date. |
| `pre_2000_flag` | integer | 0/1 | 23% | 1 when the record predates the 2000 coverage floor. Such records are retained but fall outside the standard reporting window. |
| `floor_basis_field` | text |  | 99% | One of: `introduced_date`, `date`, `congress` |
| `vote_id` | text | code | 100% | Identifier. |
| `rollnumber` | integer | integer | 100% | Roll-call vote number within the Congress. |
| `date` | text | YYYY-MM-DD | 100% | Date of the event. |
| `question` | text | text | 100% | Question put to the chamber. |
| `result` | text | category | 83% | Outcome of the vote. |
| `yea` | integer | integer | 100% | Votes in favour. |
| `nay` | integer | integer | 100% | Votes against. |
| `present` | integer | 0 to 10 | 100% | One of: `0`, `1`, `2`, `10`, `3` |
| `not_voting` | integer | integer | 100% | Members not voting. |
| `D_yea` | integer | integer | 100% | Democratic votes in favour. |
| `D_nay` | integer | integer | 100% | Democratic votes against. |
| `R_yea` | integer | integer | 100% | Republican votes in favour. |
| `R_nay` | integer | integer | 100% | Republican votes against. |
| `I_yea` | integer | 0 to 3 | 100% | One of: `0`, `1`, `2`, `3` |
| `I_nay` | integer | 0 to 3 | 100% | One of: `0`, `1`, `2`, `3` |
| `margin` | integer | integer | 100% | Yea votes minus nay votes. |
| `republican_yea_share` | integer | 0-1 proportion | 100% | Share of voting Republicans voting yea. |
| `vehicle_type` | text |  | 100% | One of: `bill`, `resolution_vehicle`, `no_bill_number`, `treaty_document`, `unresolved_bill_type` |
| `majority_side` | text |  | 100% | One of: `yea`, `nay` |
| `question_source` | text |  | 100% | One of: `voteview_vote_question`, `icpsr_rollcall_description_verbatim_via_voteview_dtl_desc; no_official_electronic_record: House EVS begins 1990, Senate LIS begins the 101st Congress` |
| `result_source` | text | text | 100% | The evidence behind a recorded vote result, including the explicit statement when NO official electronic record exists for that era (House electronic voting begins 1990; Senate LIS at the 101st Congress). Absence of a tally is a fact about the record, not a missing value. |
| `vote_description` | text | text | 99% | Description of the vote. |
| `vote_description_source` | text |  | 99% | One of: `voteview_vote_desc`, `voteview_dtl_desc` |
| `democrat_yea_share` | integer | 0-1 proportion | 100% | Share of voting Democrats voting yea. |
| `republican_pro_tribal_share` | integer | 0-1 proportion | 57% | Share of voting Republicans taking the pro-tribal position. |
| `pro_tribal_is_yea` | integer | 0 to 1 | 57% | One of: `1.0`, `0.0` |
| `direction_source` | text |  | 100% | One of: `two_coder_adjudicated:agree`, `unresolved_needs_hand_coding`, `no_direction_coded`, `senate_inherit_from_house_adjudicated_by_bill`, `two_coder_adjudicated:disagree_default_yea` |
| `vote_type` | text |  | 100% | One of: `pro_tribal`, `senate_tribal`, `procedural_opposition`, `anti_tribal_expansion` |
| `n_republican_voting` | integer | integer | 100% | Count. |
| `n_democrat_voting` | integer | integer | 100% | Count. |
| `U_yea` | integer | constant 0 | 100% | One of: `0` |
| `U_nay` | integer | constant 0 | 100% | One of: `0` |
| `yea_paired_announced` | integer | integer | 100% | Yea positions recorded by pairing or announcement rather than a cast vote. |
| `nay_paired_announced` | integer | integer | 100% | Nay positions recorded by pairing or announcement rather than a cast vote. |
| `voteview_yea_count` | integer | integer | 100% | Count. |
| `voteview_nay_count` | integer | integer | 100% | Count. |
| `tally_matches_voteview` | integer | 0 to 1 | 100% | One of: `1`, `0` |
| `bill_number` | text | integer | 94% | Bill number within its type. |
| `bill_number_prefix_recognized` | integer | 0 to 1 | 94% | One of: `1.0`, `0.0` |
| `anti_tribal_is_yea` | text |  | 24% | One of: `True`, `False` |
| `anti_tribal_category` | text |  | 4% | One of: `cut_funding`, `weaken_tribal_bill`, `restrict_sovereignty`, `terminate_recognition`, `terminate_derecognize`, `restrict_land_rights`, `restrict_gaming` |
| `anti_tribal_direction_method` *(internal)* | text |  | 24% |  |
| `direction_circularity_flag` | integer | 0/1 | 100% | Indicator variable. |
| `bill_link_status` | text |  | 100% | One of: `linked`, `unlinked_no_bill_number` |
| `official_source_url` | text | URL | 72% | The exact XML document the official values were read from. |
| `official_question` | text | text | 72% | The question as the CHAMBER put it, from clerk.house.gov EVS XML or senate.gov LIS XML. Held separately from `question` so the official record is never confused with a value derived from another source. |
| `official_result` | text | text | 72% | The result as the chamber recorded it (`Passed`, `Failed`, `Agreed to`, `Amendment Rejected`...). Chamber vocabularies differ and are deliberately not harmonised. |
| `official_yea` | integer | integer | 72% | Yea total from the chamber's own record. |
| `official_nay` | integer | integer | 72% | Nay total from the chamber's own record. |
| `official_record_status` | text | category | 100% | Whether an official electronic record exists for this roll call and what happened when it was fetched. The important value is `no_official_electronic_record`: clerk.house.gov EVS begins with calendar year 1990 and senate.gov LIS with the 101st Congress, so no amount of scraping will produce an official question or result for a vote before those boundaries. |
| `counts_agree_with_official` | integer | 0/1/blank | 72% | 1 where our yea AND nay both equal the chamber's own totals, 0 where either differs, blank where no official record exists. A 0 is a finding to investigate, never a licence to overwrite: our counts are a member-level recount and are left untouched. |
| `question_family` | text | category | 20% | For roll calls with no official record, a descriptive label for the kind of motion the sourced question text describes (On Passage, On the Motion to Table, On Ordering the Previous Question...). Derived FROM the quoted text and offered beside it - it never replaces it. |
| `bioguide_id` | text | code | 100% | Identifier. |
| `icpsr` | integer | code | 100% | ICPSR legislator identifier, which is stable across Congresses. |
| `party` | text |  | 100% | One of: `D`, `R`, `I` |
| `party_code` | integer | code | 100% | Classification code. |
| `state_abbrev` | text | 2-letter code | 100% | State. |
| `district` | integer | integer | 100% | Congressional district. |
| `position` | text |  | 100% | One of: `Yea`, `Nay`, `Not Voting`, `Announced Yea`, `Paired Yea`, `Paired Nay`, `Announced Nay`, `Present` |
| `cosponsor_flag` | integer | 0/1 | 84% | Indicator variable. |
| `position_simple` | text |  | 100% | One of: `Yea`, `Nay`, `Not Voting`, `Present` |
| `cast_code` | integer | code | 100% | How the member's position was recorded. |
| `bioname` | text | text | 100% | Member name. |
| `disposition` | text | category | 100% | The most final thing that happened to this bill, read from its FULL Congress.gov action history rather than from its latest action alone. Values, most final first: `enacted`; `veto-overridden`; `vetoed`; `passed-both-chambers-not-enacted` (presented to the President, no law); `passed-one-chamber`; `floor-vote-failed`; `withdrawn`; `reported-from-committee-never-voted` (a committee said yes and the floor never called it up); `referred-and-died-in-committee` (no committee ever reported it); `pending-in-committee` (same shape, but the Congress is still sitting so no death can be inferred); `floor-vote-held-outcome-unresolved`; `unclassified`; `no-action-record`. The last is NOT a death - it means no action record was obtainable, which is a statement about our evidence and not about the bill. The two committee categories are the ones latest_action alone cannot tell apart, and they are different political facts. |
| `disposition_action_text` | text | text | 100% | The verbatim Congress.gov action sentence that establishes the disposition. Every classification can be audited back to this one line. |
| `disposition_action_date` | text | YYYY-MM-DD | 100% | Date of the action named in disposition_action_text - i.e. the date the disposition was established, which is NOT in general the date of the bill's last action. |
| `disposition_basis` *(internal)* | text |  | 100% | One of: `congress_gov_action_text; this is the MOST FINAL action in the bill's full history - the disposition is INFERRED FROM THE ABSENCE of any later passage, failure, withdrawal or enactment action, not from a statement that the bill died`, `congress_gov_action_text`, `congress_gov_action_text; this is the MOST FINAL action in the bill's full history - the disposition is INFERRED FROM THE ABSENCE of any later passage, failure, withdrawal or enactment action, not from a statement that the bill died; congress 119 is still in session, so no death can be inferred`, `congress_gov_action_text; this is the MOST FINAL action in the bill's full history - the disposition is INFERRED FROM THE ABSENCE of any later passage, failure, withdrawal or enactment action, not from a statement that the bill died; overridden by 1 recorded roll call(s) in bill_votes.csv - a bill with a roll call did reach a floor`, `NO ACTION RECORD AT ALL (Congress.gov: not_fetched). This is not evidence the bill died - it is evidence we have no record of what happened to it.` |
| `reached_floor_vote` | integer | 0/1 | 100% | 1 if at least one recorded roll call in bill_votes.csv is linked to this bill. 0 means no ROLL CALL, which is not the same as no floor action: voice votes and unanimous consent leave no tally. |
| `rollcall_vote_ids` | text | text | 9% | Semicolon-separated vote_id values joining this bill to bill_votes.csv. |
| `n_actions_on_record` | integer | integer | 100% | How many actions Congress.gov served for this bill. A low count on an old bill reflects the thinness of pre-1990s bill status data, not legislative inactivity. |
| `first_action_date` | text | YYYY-MM-DD | 100% | Date. |
| `last_action_date` | text | YYYY-MM-DD | 100% | Date. |
| `n_entities_in_bridge` | integer | integer | 100% | Count. |
| `entity_ids` | text | delimited identifiers | 19% | Cedar Press entity identifiers linked to this row, pipe- or semicolon-separated. Empty means no entity was linked, not that none is involved. |
| `outcome_prior_build` | text | category | 89% | The coarse `outcome` value the earlier build derived from latest_action alone, retained so the reclassification can be diffed rather than taken on trust. |
| `source` | text | text | 100% | Publisher of the record. |
| `entity_class` | text | category | 100% | Kind of Native entity: federally recognised tribe, state-recognised tribe, Alaska Native Village, Alaska Native Regional Corporation, or consortium. |
| `entity_id_prefix` | text | code | 100% | The spine tribe_id prefix identifying the class (ANVC-, ANRC-, NHO-, ITO-, AKNF-, TRBF-). Join to the spine on this prefix. |
| `n_spine_entities_in_class` | integer | integer | 100% | How many spine entities carry that prefix - the size of the class the bill reaches, as of the build date. |
| `subject_family` | text | category | 100% | Which subject family the bill's title matched: ANCSA / Alaska Native corporations, Native Hawaiian, Native American Housing (NAHASDA), Intertribal, Alaska Native (non-ANCSA), or Native American / American Indian (general). |
| `matched_phrase` | text | text | 100% | The exact phrase in the bill's title (or its CRS policy area) that triggered the subject-family match. |
| `class_match_basis` *(internal)* | text |  | 100% |  |
| `named_entities_also_in_bridge` | text | delimited | 20% | Entities named on this row that also appear in the corresponding entity bridge file, so the two can be reconciled. |
| `subjects` | empty | delimited | 0% | Legislative subject terms assigned to the bill by the Library of Congress. |
| `sponsor_party` | text |  | 99% | One of: `D`, `R`, `ID` |
| `sponsor_state` | text | 2-letter code | 99% | State. |
| `latest_action_text` | text | text | 100% | Free text. |
| `matched_in` | text | category | 100% | Where the phrase matched: `title`, `subjects_or_policy_area`, or `congress_gov_policy_area`. Title matches are the precision tier; only they were added to native_bills.csv. |
| `already_in_native_bills` | integer | 0/1 | 100% | 1 if the swept bill was already in native_bills.csv before the sweep. The complement is what the sweep actually added. |
| `sweep_basis` *(internal)* | text |  | 100% |  |

## Value sets

- **`chamber`** — `House`, `Senate`, `house`, `senate`
- **`bill_scope`** — `general`, `tribe-specific`
- **`outcome`** — `died-in-committee`, `enacted`, `passed-one-chamber`, `pending`, `vetoed`
- **`bill_type`** — `hr`, `s`, `hres`, `hjres`, `sjres`, `sconres`, `treatydocno`, `hre`, `treatydoc`, `hjr`
- **`classification_source`** — `congress_gov_policy_area_native_americans`, `single_coded_keyword_rule_on_title`, `two_coder_adjudicated`, `single_coded_keyword_rule`, `two_coder_zero_overlap_adjudicated`, `two_coder_adjudicated_inherited_from_rollcall`, `subject_family_phrase_sweep:ANCSA / Alaska Native corporations`, `single_coded_8strategy_expansion`, `subject_family_phrase_sweep:Native American / American Indian (general)`, `subject_family_phrase_sweep:Native Hawaiian`
- **`classification_kappa`** — `0.952`, `-1.000 (not meaningful: disjoint coder search strategies)`
- **`build_date`** — `2026-08-05`, `2026-08-06`
- **`floor_basis_field`** — `introduced_date`, `date`, `congress`
- **`result`** — `Passed`, `Failed`, `Amendment Rejected`, `Motion to Table Agreed to`, `Agreed to`, `Amendment Agreed to`, `Bill Passed`, `Cloture Motion Rejected`, `Cloture Motion Agreed to`, `Motion Rejected`, `Motion to Table Failed`, `Conference Report Agreed to`, `Motion Agreed to`, `Concurrent Resolution Agreed to`, `Motion for Attendance Agreed to`, `Cloture on the Motion to Proceed Agreed to`, `Motion to Proceed Agreed to`
- **`vehicle_type`** — `bill`, `resolution_vehicle`, `no_bill_number`, `treaty_document`, `unresolved_bill_type`
- **`majority_side`** — `yea`, `nay`
- **`question_source`** — `voteview_vote_question`, `icpsr_rollcall_description_verbatim_via_voteview_dtl_desc; no_official_electronic_record: House EVS begins 1990, Senate LIS begins the 101st Congress`
- **`vote_description_source`** — `voteview_vote_desc`, `voteview_dtl_desc`
- **`direction_source`** — `two_coder_adjudicated:agree`, `unresolved_needs_hand_coding`, `no_direction_coded`, `senate_inherit_from_house_adjudicated_by_bill`, `two_coder_adjudicated:disagree_default_yea`
- **`vote_type`** — `pro_tribal`, `senate_tribal`, `procedural_opposition`, `anti_tribal_expansion`
- **`anti_tribal_is_yea`** — `True`, `False`
- **`anti_tribal_category`** — `cut_funding`, `weaken_tribal_bill`, `restrict_sovereignty`, `terminate_recognition`, `terminate_derecognize`, `restrict_land_rights`, `restrict_gaming`
- **`bill_link_status`** — `linked`, `unlinked_no_bill_number`
- **`official_result`** — `Passed`, `Failed`, `Amendment Rejected`, `Motion to Table Agreed to`, `Amendment Agreed to`, `Agreed to`, `Bill Passed`, `Cloture Motion Rejected`, `Cloture Motion Agreed to`, `Motion Rejected`, `Motion to Table Failed`, `Conference Report Agreed to`, `Motion Agreed to`, `Concurrent Resolution Agreed to`, `Motion for Attendance Agreed to`, `Cloture on the Motion to Proceed Agreed to`, `Motion to Proceed Agreed to`
- **`official_record_status`** — `ok`, `no_official_electronic_record: House EVS begins 1990, Senate LIS begins the 101st Congress`
- **`question_family`** — `On Passage`, `On Agreeing to the Amendment`, `On the Motion to Table`, `On Agreeing to the Resolution`, `On the Conference Report`, `On Ordering the Previous Question`
- **`party`** — `D`, `R`, `I`
- **`position`** — `Yea`, `Nay`, `Not Voting`, `Announced Yea`, `Paired Yea`, `Paired Nay`, `Announced Nay`, `Present`
- **`position_simple`** — `Yea`, `Nay`, `Not Voting`, `Present`
- **`disposition`** — `referred-and-died-in-committee`, `passed-one-chamber`, `enacted`, `placed-on-calendar-never-voted`, `committee-acted-never-reported`, `pending-in-committee`, `reported-from-committee-never-voted`, `superseded-by-another-measure`, `floor-vote-failed`, `floor-vote-held-outcome-unresolved`, `no-action-record`, `vetoed`
- **`outcome_prior_build`** — `died-in-committee`, `enacted`, `passed-one-chamber`, `pending`, `vetoed`
- **`entity_class`** — `Federally Recognized Tribe`, `Native Hawaiian Organization`, `Alaska Native Village Corporation`, `Alaska Native Regional Corporation`, `Alaska Native Village Government`, `Intertribal Organization`
- **`entity_id_prefix`** — `TRBF-`, `NHO-`, `ANVC-`, `ANRC-`, `AKNF-`, `ITO-`
- **`subject_family`** — `Native American / American Indian (general)`, `ANCSA / Alaska Native corporations`, `Native Hawaiian`, `Native American Housing (NAHASDA)`, `Alaska Native (non-ANCSA)`, `Intertribal / inter-tribal organisations`
- **`sponsor_party`** — `D`, `R`, `ID`
- **`matched_in`** — `subjects_or_policy_area`, `title`
