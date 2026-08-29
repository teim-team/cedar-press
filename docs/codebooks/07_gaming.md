# Codebook — Gaming

*66,135 rows across 3 file(s). Generated 2026-08-07.*

Variables marked **internal** are retained for auditing and are not included in published extracts.

| Variable | Type | Units / format | Filled | Description |
|---|---|---|---:|---|
| `facility_id` | text | code | 98% | Identifier. |
| `entity_id` | text | code | 1% | Identifier. |
| `tribe` | text | text | 100% | Tribe as named in the source record. |
| `facility_name` | text | text | 99% | Name. |
| `company` | text | text | 57% | Operating company. |
| `address` | text | text | 87% | Street address. |
| `city` | text | text | 92% | City. |
| `state` | text | 2-letter code | 98% | US state or territory. |
| `postal_code` | text | text | 78% | Postal code. |
| `latitude` | numeric | decimal degrees | 89% | Latitude of the facility. |
| `longitude` | numeric | decimal degrees | 89% | Longitude of the facility. |
| `coords_basis` *(internal)* | text |  | 89% |  |
| `observation_status` | text |  | 99% | One of: `current`, `proposed`, `approved` |
| `property_status` | text |  | 57% | One of: `current`, `approved` |
| `property_status_literal` | text |  | 57% | One of: `Open`, `Temporarily Closed`, `Under Construction` |
| `property_status_observed_date` | text | YYYY-MM-DD | 57% | Date. |
| `open_date` | text | mixed: YYYY-MM-DD | YYYY | free text | 82% | The opening date as the source states it, unmodified. THREE things a subscriber cannot infer from this value and must read alongside it. (1) WHICH EVENT it marks is a separate column: this field carries both 'gaming commenced here' and 'this property opened', which are different events on a site that existed before it hosted gaming — read `open_date_event`, which is `unspecified` on most rows because the source does not say. (2) IT IS NOT AS PRECISE AS IT LOOKS: two thirds of the inherited ISO values are year- or month-precision placeholders written as full dates (`YYYY-12-31` is the source's year placeholder and `YYYY-MM-15` its mid-month convention) — read `open_date_precision`, and use `open_date_not_before`/`open_date_not_after` for the interval the source actually supports. (3) IT IS NOT RELIABLY THE ORIGINAL OPENING: on some rows it dates the current building or a re-opening — read `open_date_postdates_observation`. Rows with no stated date are retained; see `open_date_class`. NOT A UNIFORM ISO COLUMN — because the source value is never modified, it holds 506 `YYYY-MM-DD`, 111 bare `YYYY` and one literal `1980s`. A strict date parser will error or silently drop 112 rows. **Parse `open_date_not_before`/`open_date_not_after` instead — those are uniformly ISO with no exceptions** and they carry the interval the source supports rather than a padded point. |
| `open_date_basis` *(internal)* | text |  | 82% | One of: `Casino City Tribal Property List, 'Open Date'`, `Indian Gaming Dataset, hand-coded opening event with a per-event source URL`, `hand-researched 2026-08-06; day-precision date stated by the cited source`, `hand-researched 2026-08-06; year-precision date stated by the cited source`, `hand-researched 2026-08-06; month-precision date stated by the cited source` |
| `open_date_source_url` | text | URL | 24% | Link supporting the opening date. |
| `close_date` | text | mixed: YYYY-MM-DD | YYYY.0 | 19% | The closing date as the source states it, unmodified. Subject to the same placeholder-precision caveat as `open_date` — read `close_date_precision`. A blank means unknown, never 'still open'; property status is a separate column. Like `open_date` it is NOT uniform: 133 values are `YYYY-MM-DD` and 15 are a float artefact carried verbatim from the source (`2019.0`), which is a year. Parse `close_date_not_before`/`close_date_not_after` instead — those are uniformly ISO. |
| `close_date_basis` *(internal)* | text |  | 19% | One of: `Casino City Tribal Property List, '1st Close Date'`, `Indian Gaming Dataset, hand-coded closing event` |
| `close_date_source_url` | text | URL | 2% | Link supporting the closing date. |
| `gaming_machines` | integer | integer | 53% | Number of gaming machines. |
| `gaming_machines_value_basis` *(internal)* | text |  | 100% | One of: `reported`, `not_published`, `no_capacity_source_for_this_facility` |
| `gaming_machines_observation_status` | text |  | 53% | One of: `current`, `approved` |
| `gaming_machines_observed_date` | text | YYYY-MM-DD | 53% | Date. |
| `table_games` | integer | integer | 26% | Number of table games. |
| `table_games_value_basis` *(internal)* | text |  | 100% | One of: `not_published`, `reported`, `no_capacity_source_for_this_facility` |
| `table_games_observation_status` | text |  | 26% | One of: `current` |
| `table_games_observed_date` | text | YYYY-MM-DD | 26% | Date. |
| `poker_tables` | integer | integer | 20% | Number of poker tables. |
| `poker_tables_value_basis` *(internal)* | text |  | 100% | One of: `not_published`, `no_capacity_source_for_this_facility`, `reported` |
| `poker_tables_observation_status` | text |  | 20% | One of: `current`, `proposed`, `approved` |
| `poker_tables_observed_date` | text | YYYY-MM-DD | 20% | Date. |
| `bingo_seats` | integer | integer | 16% | Number of bingo seats. |
| `bingo_seats_value_basis` *(internal)* | text |  | 100% | One of: `not_published`, `no_capacity_source_for_this_facility`, `reported` |
| `bingo_seats_observation_status` | text |  | 16% | One of: `current`, `approved` |
| `bingo_seats_observed_date` | text | YYYY-MM-DD | 16% | Date. |
| `gaming_square_feet` | integer | square feet | 39% | Gaming floor area. |
| `gaming_square_feet_value_basis` *(internal)* | text |  | 100% | One of: `reported`, `not_published`, `no_capacity_source_for_this_facility` |
| `gaming_square_feet_observation_status` | text |  | 39% | One of: `current`, `proposed` |
| `gaming_square_feet_observed_date` | text | YYYY-MM-DD | 39% | Date. |
| `convention_square_feet` | integer | square feet | 12% | Convention and meeting area. |
| `convention_square_feet_value_basis` *(internal)* | text |  | 100% | One of: `not_published`, `no_capacity_source_for_this_facility`, `reported` |
| `convention_square_feet_observation_status` | text |  | 12% | One of: `current` |
| `convention_square_feet_observed_date` | text | YYYY-MM-DD | 12% | Date. |
| `hotel_rooms` | integer | integer | 16% | Number of hotel rooms. |
| `hotel_rooms_value_basis` *(internal)* | text |  | 100% | One of: `not_published`, `no_capacity_source_for_this_facility`, `reported` |
| `hotel_rooms_observation_status` | text |  | 16% | One of: `current`, `approved` |
| `hotel_rooms_observed_date` | text | YYYY-MM-DD | 16% | Date. |
| `parking_spaces` | integer | integer | 23% | Number of parking spaces. |
| `parking_spaces_value_basis` *(internal)* | text |  | 100% | One of: `not_published`, `no_capacity_source_for_this_facility`, `reported` |
| `parking_spaces_observation_status` | text |  | 23% | One of: `current` |
| `parking_spaces_observed_date` | text | YYYY-MM-DD | 23% | Date. |
| `employees` | integer | integer | 42% | Reported employee count. |
| `employees_value_basis` *(internal)* | text |  | 100% | One of: `reported`, `not_published`, `no_capacity_source_for_this_facility` |
| `employees_observation_status` | text |  | 42% | One of: `current`, `proposed` |
| `employees_observed_date` | text | YYYY-MM-DD | 42% | Date. |
| `restaurants` | integer | integer | 43% | Number of restaurants. |
| `restaurants_value_basis` *(internal)* | text |  | 100% | One of: `reported`, `not_published`, `no_capacity_source_for_this_facility` |
| `restaurants_observation_status` | text |  | 43% | One of: `current` |
| `restaurants_observed_date` | text | YYYY-MM-DD | 43% | Date. |
| `casino_city_id` | integer | code | 77% | Identifier. |
| `n_capacity_observations` | integer | integer | 100% | Count. |
| `first_observed_date` | text | YYYY-MM-DD | 57% | Earliest date this variant was seen in a source, where a source states one. |
| `last_observed_date` | text | YYYY-MM-DD | 57% | Latest date this variant was seen in a source, where a source states one. |
| `native_american_flag` | text | 0/1 | 57% | Indicator variable. |
| `property_type` | text |  | 57% | One of: `Casino` |
| `source_datasets` *(internal)* | text |  | 100% |  |
| `match_status` | text |  | 100% | One of: `casino_city_only`, `matched_casino_city_and_votingpatterns`, `votingpatterns_only_no_exact_casino_city_match` |
| `match_basis` *(internal)* | text |  | 100% | One of: `no exact normalised (name, state) match from another source`, `exact match on normalised (facility_name, state)`, `no exact normalised (name, state) match in Casino City`, `exact match on normalised (street address, state)` |
| `duplicate_risk` | integer | 0 to 1 | 100% | One of: `0`, `1` |
| `fetched_date` | text | YYYY-MM-DD | 100% | Date. |
| `open_date_class` | text | category | 100% | Strength of the evidence behind the opening date. `exact` a source states it · `bounded` a source proves the facility was already operating by a date, or could not have opened before one, but none states the opening · `absent` no source located, or the row is not a datable facility. |
| `open_date_precision` | text | category | 82% | How precise the stated opening date actually is: day, month, year or decade. Derived, not assumed - two thirds of the inherited ISO dates are year- or month-precision placeholders written as full dates. |
| `open_date_not_before` | text | YYYY-MM-DD | 83% | Earliest date the facility could have opened. Always true; always ISO. |
| `open_date_not_after` | text | YYYY-MM-DD | 93% | Latest date the facility could have opened - it was demonstrably operating by then. Always true; always ISO. NOT an opening date. |
| `open_date_evidence` | text | text | 94% | What establishes the class or the bound, in plain words. |
| `open_date_evidence_url` | text | URL | 31% | URL of the source behind the bound. |
| `open_date_evidence_quote` | text | text | 16% | Verbatim snippet from that source carrying the evidence. |
| `open_date_absent_reason` | text | text | 6% | Why no opening date exists for this row. Not all absences are the same: it distinguishes `no source located` from a row ruled to be a duplicate, a non-gaming property, or an identity that could not be established. |
| `close_date_class` | text | category | 100% | `exact` when a source states a closing date, `absent` otherwise. Absent means unknown, never 'still open'. |
| `close_date_precision` | text | category | 19% | Precision of the stated closing date. |
| `close_date_not_before` | text | YYYY-MM-DD | 19% | Earliest date the facility could have closed. |
| `close_date_not_after` | text | YYYY-MM-DD | 19% | Latest date the facility could have closed. |
| `observed_open_by` | text | YYYY-MM-DD | 56% | Earliest date a source observed this property already operating. An upper bound on the opening, not the opening. |
| `open_date_postdates_observation` | integer | 0/1 | 3% | 1 where the stated opening date is LATER than an observation of the same property already open — so it dates the current building or a re-opening, not the original opening. Exclude these before charting openings by year. |
| `close_date_precedes_open_date` | integer | 0/1 | 1% | 1 where the closing date falls before the opening date. Both are source values and neither was corrected; the pair almost certainly mixes a predecessor building's closure with a replacement's opening. |
| `open_date_event` | text | category | 82% | WHICH EVENT the opening date marks — read this before using the date. `gaming_commenced` gaming began here · `property_opened` the property was established, which is not the same thing on a site that existed before it hosted gaming · `not_gaming_commencement` verified not a gaming date · `unspecified` the source publishes an 'Open Date' for a gaming property without saying which event it marks, and it is not inferred here. `unspecified` is the majority and is what the source supports, not a defect. `not_gaming_commencement` is reserved for rows actually verified against a source; a date that is merely implausible as a gaming date stays `unspecified` and carries `open_date_predates_tribal_gaming_era` instead. |
| `open_date_event_basis` *(internal)* | text | text | 82% | What establishes the event, in plain words. |
| `open_date_predates_tribal_gaming_era` | integer | 0/1 | 1% | 1 where the stated opening date falls before 1979, the year the Seminole Tribe opened the Hollywood high-stakes bingo hall that produced Seminole Tribe v. Butterworth and, through it, IGRA. A tribal gaming property dated earlier is prima facie dating something other than gaming. |
| `temporal_build_date` | text | YYYY-MM-DD | 100% | Date the temporal layer was last built for this row. |
| `tribe_id` | text | code | 98% | Cedar Press permanent identifier for the Native entity. Stable across releases; use this to join datasets. |
| `tribe_canonical_name` | text | text | 98% | Name. |
| `entity_match_method` *(internal)* | text |  | 98% | One of: `containment`, `alias`, `core`, `exact` |
| `entity_tier` | text |  | 98% | One of: `B`, `A` |
| `entity_match_basis` *(internal)* | text |  | 100% |  |
| `entity_keyed_date` | text | YYYY-MM-DD | 100% | Date. |
| `interim_open_date` | text | YYYY-MM-DD | 0% | Date. |
| `interim_open_date_basis` *(internal)* | text |  | 0% | One of: `exact` |
| `interim_open_note` | text |  | 0% | One of: `Two openings, both real. A TEMPORARY facility opened 1998-05-20 and the PERMANENT building opened 1998-12-15, which is what `open_date` carries. Recorded separately rather than resolved by a house rule: "when did gaming start here" and "when did this building open" are different questions and a single date cannot answer both.` |
| `duplicate_of_facility_id` | text | facility_id or empty | 1% | Populated when this row has been RULED to describe the same property as another row, which is the row that carries the opening date. The contributing rosters name some properties twice under different naming, and the row is retained with the duplication disclosed rather than deleted. TO COUNT DISTINCT PROPERTIES, filter to rows where this is empty. Each ruling names its evidence in `open_date_absent_reason`. |
| `decision_id` | text | code | 100% | Identifier. |
| `state_abbr` | text | 2-letter code | 100% | State. |
| `legal_theory` | text |  | 99% | One of: `Two-Part Secretarial Determination`, `Restored Lands`, `Within or Contiguous to Reservation Boundaries`, `Oklahoma - Within Former Reservation Boundaries`, `Initial Reservation`, `Settlement of a Land Claim`, `Within Last Recognized Reservation` |
| `decision_status` | text |  | 100% | One of: `Approved`, `Disapproved`, `Pending` |
| `decision_date` | text | YYYY-MM-DD | 100% | Date of the agency decision. |
| `document_urls` | text | URL list | 100% | Links to the decision documents. |
| `federal_register_url` | text | URL | 54% | Link to the Federal Register document. |
| `source_url` | text | URL | 100% | Link to the record's published source. |
| `decision_date_displayed` | text | text | 100% | Decision date as shown in the source. |
| `decision_title` | text | text | 100% | Title of the agency decision. |
| `document_labels` | text | text | 100% | Labels applied to the decision documents. |
| `document_types` | text | text | 100% | Kinds of document in the decision record. |
| `n_documents` | integer | integer | 100% | Count. |
| `document_urls_basis` *(internal)* | text |  | 100% | One of: `bia_gaming_land_decisions_index_row`, `bia_individual_project_page (index row lists no documents)` |
| `federal_register_date` | text | YYYY-MM-DD | 54% | Date. |
| `federal_register_doc_number` | text | code | 54% | Federal Register document number. |
| `federal_register_slug` | text | text | 54% | Federal Register URL slug. |
| `project_page_url` | text | URL | 4% | Link. |
| `bia_note_text` | text | text | 25% | Explanatory note carried in the agency record. |
| `index_row_position` *(internal)* | integer | 1 to 138 | 100% |  |
| `tribe_basis` *(internal)* | text |  | 100% | One of: `bia_index_Tribe(s)_column, verbatim (agrees with the BIA title)`, `bia_index_Tribe(s)_column, verbatim BUT CONFLICTED: it shares no distinctive token with the BIA title, and the title's name is corroborated by the linked document labels. See tribe_from_title.` |
| `bia_tribes_column_conflict` | integer | 0 to 1 | 100% | One of: `0`, `1` |
| `tribe_from_title` | text | text | 2% | Descriptive name. |
| `legal_theory_basis` *(internal)* | text |  | 100% | One of: `bia_index_Legal_Theory_column, verbatim` |
| `decision_status_basis` *(internal)* | text |  | 100% | One of: `bia_index_Decision_Status_column, verbatim (current state only; see gaming_decision_events.csv)` |
| `decision_date_basis` *(internal)* | text |  | 100% | One of: `bia_index_Date_column <time datetime> attribute` |
| `entity_level` | text |  | 100% | One of: `facility`, `tribe`, `implan_sector_line_item` |
| `metric` | text | text | 100% | Name of the reported measure. |
| `measure_type` | text |  | 100% | One of: `capacity`, `gaming_revenue`, `payment_to_government` |
| `value` | numeric | see `unit` | 100% | Value of the reported measure. |
| `unit` | text | text | 100% | Unit of the reported measure. |
| `observation_date` | text | YYYY-MM-DD | 98% | Date. |
| `observation_period` | integer | text | 2% | Period the observation covers. |
| `source_status_literal` *(internal)* | text |  | 100% |  |
| `value_basis` *(internal)* | text |  | 100% | One of: `reported`, `payments_derived`, `modelled`, `reverse_engineered` |
| `value_verification` | text |  | 100% | One of: `published_by_source`, `source_archived`, `source_archived: data/raw/multistate_gaming_revenue/ok_gaming_compliance_{2018,2023}.pdf`, `source_archived: data/raw/multistate_gaming_revenue/ct_slot_revenue.csv`, `not_source_verified (hand-written estimate)`, `not_source_verified`, `source_archived state aggregate: data/raw/multistate_gaming_revenue/az_jlbc_2024.pdf` |
| `value_basis_detail` *(internal)* | text |  | 100% |  |
| `source` | text | text | 100% | Publisher of the record. |
| `source_file` *(internal)* | text |  | 100% | One of: `tribal_casino_panel.dta`, `published_tribal_gaming_revenue_v3_audited.csv`, `per_property_gaming_revenue_FINAL_v3_audited.csv` |
| `as_of_date` | text | YYYY-MM-DD | 100% | The date this measurement describes. Populated on every observation. A capacity or revenue figure without one is uninterpretable. |
| `as_of_date_precision` | text | category | 100% | `day` when the source dates the observation, `year` when it gives only a reporting year - in which case the date is that year's 1 January and the month and day are not claimed. |
| `as_of_date_basis` *(internal)* | text |  | 100% | One of: `source observation_date`, `derived from observation_period; the source states a fiscal year only, so month and day are not claimed` |

## Value sets

- **`observation_status`** — `current`, `proposed`, `approved`
- **`property_status`** — `current`, `approved`
- **`property_status_literal`** — `Open`, `Temporarily Closed`, `Under Construction`
- **`close_date_source_url`** — `https://www.500nations.com/casinos/ok-Cherokee-Tahlequah-Casino.asp`, `https://en.wikipedia.org/wiki/Choctaw_Casino_Bingo`, `https://www.yogonet.com/international/news/2022/05/13/62633-oklahoma-ukb-tribe-closer-to-reopening-tahlequah-casino-after-favorable-court-ruling-in-cherokee-dispute`, `https://www.kiowatribe.org/sites/default/files/inline-files/KCOA%20news%20update%204-2024.pdf`, `https://static1.squarespace.com/static/5e83a16cec038607f18cf780/t/64130c9ff87c8521ce118300/1678970015689/MNE+March+2023+Press+Release.pdf`, `River Spirit Casino to reopen earlier than anticipated | The Journal Record`, `https://www.oklahoman.com/story/news/2003/06/15/seminole-nation-to-close-4-casinos/62039182007/`, `OK Casino Closes Suddenly, Leaving Workers Without Paychecks (news9.com)`, `https://www.artesianhotel.com/footer/history-our-story/`, `https://oldcampcasino.com/`, `https://www.worldcasinodirectory.com/casino/lil-chiefs-casino-3200#`, `Feds order Nooksack Tribe to shutter casino over violations | AP News`, `https://www.seattletimes.com/seattle-news/northwest/nooksack-river-casino-shuts-down-after-financial-issues/`, `https://www.500nations.com/casinos/waTwoRivers.asp`, `https://www.casinocitytimes.com/news/article/sevenwinds-and-grindstone-creek-casinos-will-close-until-further-notice-234520`
- **`gaming_machines_observation_status`** — `current`, `approved`
- **`poker_tables_observation_status`** — `current`, `proposed`, `approved`
- **`bingo_seats_observation_status`** — `current`, `approved`
- **`gaming_square_feet_observation_status`** — `current`, `proposed`
- **`gaming_square_feet_observed_date`** — `2023-01-01`, `2012-01-01`, `2019-01-01`, `2006-11-07`, `2008-04-22`, `2014-01-01`, `2017-01-01`, `2015-07-01`, `2016-01-01`, `2012-09-17`, `2007-05-02`, `2005-01-25`, `2017-07-01`, `2013-01-01`, `2018-01-01`, `2011-04-28`, `2007-11-06`, `2022-07-01`, `2010-05-17`, `2013-07-01`, `2014-07-01`, `2022-01-01`, `2004-01-27`, `2021-07-01`, `2016-07-01`
- **`convention_square_feet_observed_date`** — `2023-01-01`, `2008-04-22`, `2006-11-07`, `2005-09-02`, `2007-05-02`, `2007-11-06`, `2015-07-01`, `2016-01-01`, `2004-01-27`
- **`hotel_rooms_observation_status`** — `current`, `approved`
- **`hotel_rooms_observed_date`** — `2023-01-01`, `2019-01-01`, `2007-05-02`, `2006-11-07`, `2008-04-22`, `2018-01-01`, `2010-11-03`, `2007-11-06`, `2015-07-01`, `2017-01-01`, `2005-09-02`
- **`parking_spaces_observed_date`** — `2023-01-01`, `2006-11-07`, `2007-11-06`, `2022-07-01`, `2007-05-02`, `2017-01-01`, `2019-01-01`, `2011-04-28`, `2012-01-01`, `2022-01-01`, `2015-07-01`, `2016-01-01`, `2004-01-27`, `2016-07-01`
- **`employees_observation_status`** — `current`, `proposed`
- **`employees_observed_date`** — `2023-01-01`, `2006-11-07`, `2007-11-06`, `2017-01-01`, `2019-01-01`, `2010-05-17`, `2016-01-01`, `2008-04-22`, `2014-01-01`, `2014-07-01`, `2012-01-01`, `2021-07-01`, `2015-07-01`, `2022-07-01`, `2005-01-25`, `2013-01-01`, `2009-11-09`, `2012-09-17`, `2007-05-02`, `2011-04-28`, `2013-07-01`, `2022-01-01`, `2018-01-01`, `2004-01-27`, `2005-09-02`
- **`restaurants_observed_date`** — `2023-01-01`, `2019-01-01`, `2006-11-07`, `2021-07-01`, `2008-04-22`, `2017-07-01`, `2007-11-06`, `2016-01-01`, `2014-01-01`, `2012-01-01`, `2015-07-01`, `2017-01-01`, `2006-03-28`, `2005-01-25`, `2012-09-17`, `2018-07-01`, `2007-05-02`, `2013-01-01`, `2009-04-22`, `2011-04-28`, `2013-07-01`, `2022-01-01`, `2004-01-27`, `2022-07-01`
- **`native_american_flag`** — `Yes`, `No`
- **`match_status`** — `casino_city_only`, `matched_casino_city_and_votingpatterns`, `votingpatterns_only_no_exact_casino_city_match`
- **`open_date_class`** — `exact`, `bounded`, `absent`
- **`open_date_precision`** — `year`, `day`, `month`, `decade`
- **`open_date_absent_reason`** — `not a gaming facility - this row comes from the votingpatterns tribe roster and its facility_name records that the tribe operates no casino; there is no opening to date`, `no source located - see docs/GAMING_TEMPORAL_BUILD_LOG.md for what was searched`, `cross-reference stub - facility_name points at another row for the same property; not a distinct facility`, `duplicate row - RULED 2026-08-06 (session 3) to be the same property as VP-0011, which carries the date. See `duplicate_of_facility_id`. The votingpatterns source file annotates this record 'Same property' and gives its address as 11154 Hwy 76 - byte-identical to VP-0011 Pala Casino Spa Resort and to CCP-521600 (11154 Highway 76). It is the hotel tower added to the existing Pala Casino, not a separate casino. Gaming at the property commenced 2001-04-03, which VP-0011 already carries; the hotel/spa expansion opened 2003-08-19, which is an expansion, not an opening. This is the §7.5c row whose well-sourced date was deliberately NOT recorded, and this ruling is why: the date is real and it belongs to VP-0011.`, `gaming status not established - RULED 2026-08-06 (session 3), REPLACING a 2026-08-06 ruling of 'not a gaming facility' that over-claimed. FOR gaming: this row is a Casino City Tribal Property List record, and that roster is a gaming-property roster (its Montana entries include B & S Laundry, Dad's Bar and TJ's Quikstop, which are licensed video-gambling locations). It carries a close date of 2003-11-21, so the vendor tracked it as an operating gaming location until then. AGAINST gaming: saulttribe.com's CURRENT enterprise page describes MidJim as a convenience-store and fuel brand listed separately from Kewadin Casinos - 'Midjim has two locations in the Upper Peninsula, in Sault Ste. Marie and St. Ignace. Both locations offer items such as gasoline, cigarettes, beer, wine and other convenience items.' That page describes the brand in 2026 and cannot speak to a location that closed in 2003. Neither the opening date nor the gaming status is established. https://www.saulttribe.com/enterprises/midjim`, `gaming status not established - RULED 2026-08-06 (session 3), REPLACING a 2026-08-06 ruling of 'not a gaming facility' that over-claimed (see TPL-0070 for the full reasoning; same MidJim brand, Casino City close date 2005-03-15). SEPARATE AND STILL OPEN: this row is labelled 'St. Ignace' but Casino City gives its address as 2205 Shunk Road, which is in Sault Ste. Marie - the two MidJim locations appear to have been crossed. Queued, not corrected. https://www.saulttribe.com/enterprises/midjim`, `duplicate row - RULED 2026-08-06 (session 3) to be the same property as CCP-67000, which carries the date. See `duplicate_of_facility_id`. Address is byte-identical to the dated row - 6800 Y Frontage Rd NW against CCP-67000's 6800 Y Frontage Road Northwest, both Walker MN, both Leech Lake Band of Ojibwe - and the votingpatterns source file cites 'NorthernLightsCasino.com', the twin's own site. One property. READ THE TWIN'S EVENT RULING: researching this row is what established that CCP-67000's 2001-05-15 is a REPLACEMENT BUILDING, not the original opening (see RULED_EVENT). The original opening is still unsourced.`, `duplicate row - RULED 2026-08-06 (session 3) to be the same property as CCP-688700, which carries the date. See `duplicate_of_facility_id`. Same property, and the TRIBE on this row is wrong. The votingpatterns source file cites 'IronHorseBarAndCasino.com' for this record - the twin's own site - and the twin is CCP-688700 Iron Horse Bar & Casino, Emerson NE, open 2004-07-09, operated by the WINNEBAGO Tribe of Nebraska. This row attributes it to the OMAHA Tribe of Nebraska. Emerson is a village of about 800 people and does not host two casinos of the same name run by two tribes. The '- small' suffix is the roster's size-class descriptor, not a separate property. Addresses differ (1402 Hwy 75 against the vendor's 1106 South Main Street) and that discrepancy is disclosed rather than smoothed over.`, `duplicate row - RULED 2026-08-06 (session 3) to be the same property as CCP-39900, which carries the date. See `duplicate_of_facility_id`. Cross-reference stub. The facility_name says '- main IA' and the votingpatterns source file annotates the record 'Main casino in IA', both pointing at the Winnebago Tribe of Nebraska's Iowa property - CCP-39900 WinnaVegas Casino Resort, 1500 330th Street, Sloan IA, 1992. Not a distinct Nebraska facility. The CROSS_REF name rule did not catch it because that rule keys on '- actual XX' and 'see X', and this row says '- main IA'.`, `duplicate row - RULED 2026-08-06 (session 3) to be the same property as CCP-908000, which carries the date. See `duplicate_of_facility_id`. SAME PROPERTY, AND THE TRIBE AND STATE ON THIS ROW ARE WRONG. Sage Hill Casino is on the FORT HALL Reservation in IDAHO and belongs to the SHOSHONE-BANNOCK Tribes - the operator's own page states 'Located on the Fort Hall Indian Reservation, 3 mi South of Blackfoot on Highway 91. I-15 Exit 89' (sho-ban.com, fetched 2026-08-06 (session 3)). This row says Shoshone-PAIUTE Tribes at Owyhee, NEVADA. The votingpatterns source file cites 'SageHillCasino.com' - the Idaho property's own site - and annotates the record 'NV side', so the roster knowingly filed an Idaho casino under a Nevada tribe. This file ALREADY HOLDS the property correctly as CCP-908000 Sage Hill Casino, Shoshone-Bannock Tribes, Idaho, open 2009-03-18. The 23g duplicate scorer could not find that twin because it searches within a state and this row's state field is the corrupted one. THIS IS WHY THE §7.5c DATE WAS HELD: applying the sourced 'February 2009' opening here would have dated a Nevada row with an Idaho casino's opening while the correct row already carried it. NOTE A REMAINING CONFLICT, not resolved here: the held source says February 2009 and Casino City says 2009-03-18. Both are early 2009; neither is preferred without a further source.`, `not a distinct gaming property - RULED 2026-08-06 (session 3). The row fuses three different nations' facts: '7 Clans' is the OTOE-MISSOURIA brand (this file holds six 7 Clans rows, all Otoe-Missouria, none in Ponca City); the tribe field says Ponca Tribe of Oklahoma, whose own Ponca City casino IS in this file as CCP-411000 Blue Star Gaming and Casino, 20 White Eagle Drive, opened 2010-10-15; and the location, Ponca City, is where the OSAGE NATION's casino sits (CCP-859600 / VP-0199, 2007). The Indian Gaming Dataset independently records the Ponca Tribe's Ponca City property as 'Two Rivers Casino', 101 White Eagle Dr, grand opening 2010, closed 2013 - the same White Eagle site as CCP-411000. Every real property this row could denote is already in the file and dated. Dating this row would create a fourth Ponca City record for three casinos.`, `identity not established - RULED 2026-08-06 (session 3). No distinct Choctaw CASINO in Atoka is evidenced anywhere: 'Atoka' appears nowhere in a 31,054-row CDX enumeration of choctawcasinos.com, and the live locations page (fetched 2026-08-06) lists Durant, Pocola, Hochatown, Broken Bow, Idabel, McAlester, Grant and Stringtown as casinos, with Atoka appearing only as CHOCTAW TRAVEL PLAZA ATOKA. Stringtown is in Atoka County, which is a plausible source of the mislabel. This file already holds the tribe's Atoka gaming property as CCP-970700 Choctaw Travel Plaza - Atoka (1302 South Mississippi, 2010-06-15) - and travel plazas in this file DO host gaming, so that row is not a non-casino. NOT ruled a duplicate: this row's address is 1790 S Mississippi Ave against the vendor's 1302 South Mississippi, and a different street number is not a merge this project will make on inference. Searching harder cannot date a row whose subject is undefined. https://www.choctawcasinos.com/locations/`, `not a distinct gaming property - RULED 2026-08-06 (session 3). The name does not resolve: potawatomi.org's gaming enterprise list has exactly TWO properties, Grand Casino Hotel & Resort and FireLake Casino, and 'FireLake Express' is the Citizen Potawatomi Nation's GROCERY chain. The votingpatterns source file that contributed this row cites 'GrandResortOK.com' and annotates it 'Adjacent to Grand' - i.e. the roster itself recorded it as an adjunct of the Grand Casino property, not as a casino of its own. Both candidate properties are already dated here (CCP-766700 Grand Casino Hotel Resort, 2006; CCP-409700 FireLake Casino, 1989), and the duplicate queue scores this row STRONG against BOTH - which is the tell that it is a merged label rather than a property. A date was available (October 2006 for the Grand) and was deliberately NOT recorded. https://www.potawatomi.org/`, `duplicate row - RULED 2026-08-06 (session 3) to be the same property as CCP-962300, which carries the date. See `duplicate_of_facility_id`. Same property - Indigo Sky Casino, Eastern Shawnee Tribe, Wyandotte OK - and THIS ROW IS THE ONE WITH THE CORRECT ADDRESS. It carries 70220 E Hwy 60, which the Indian Gaming Dataset also gives for Indigo Sky Casino (70220 US-60). The dated twin CCP-962300 carries 130 North Oneida Street, which is the PREDECESSOR Bordertown Casino's address (the Indian Gaming Dataset puts Bordertown Casino & Arena at 129 Oneida St). So the twin is dated, and this row is correctly located, and they are one casino. READ THE TWIN'S EVENT RULING: CCP-962300's 1981-12-31 cannot be Indigo Sky's opening.`, `not a gaming facility - RULED 2026-08-06 (session 3). Peoria Ridge is the Peoria Tribe's 18-hole GOLF COURSE. peoriatribe.com lists Buffalo Run Casino & Resort and Peoria Ridge Golf Course as SEPARATE enterprises, and the row's address (10238 S 580 Rd, Miami OK) is the golf course, not the casino (8520 S Highway 69A, carried on CCP-646400 Peoria Gaming Center). Same class of row as Lake of Isles, Foxwoods' golf course (VP-0002). There is no gaming opening to date. https://www.peoriatribe.com/`, `identity not established - RULED 2026-08-06 (session 3). The Sac and Fox Nation of Oklahoma's Shawnee gaming property is The Black Hawk Casino, already in this file as CCP-692600 (42008 Westech Road, Shawnee, 2004-07-28), and the Indian Gaming Dataset independently lists Shawnee's casinos as Thunderbird, FireLake, Grand, Kickapoo Shawnee and The Black Hawk - with no 'Sac and Fox Casino Shawnee' among them. NOT ruled a duplicate of CCP-692600, because this row's address (920866 S Hwy 99) is a STROUD address - the Sac and Fox Nation's headquarters sits at 920883 S Hwy 99, Stroud - while its city field says Shawnee. Name, city and address disagree, and the votingpatterns roster cites 'SacAndFoxCasinos.com' for it, a domain the 2026-08-06 sweep found belongs to a DIFFERENT TRIBE (the Sac and Fox Nation of MISSOURI, Powhattan, Kansas). Resolve which property this row is before dating it.`, `duplicate row - RULED 2026-08-06 (session 3) to be the same property as CCP-800600, which carries the date. See `duplicate_of_facility_id`. Same property. Name, city and tribe all agree with CCP-800600 Sac & Fox Nation Stroud Casino (Stroud OK, 2005-06-15), and the Indian Gaming Dataset records the Sac and Fox Nation Casino at 356120 926 Rd, Stroud - the same 356120 house number this row carries as '356120 EW 1240', which is the same rural address under Oklahoma's two road-naming conventions. Contrast VP-0165, the tribe's other roster row, which is NOT ruled a duplicate because its name, city and address disagree with each other.`, `duplicate row - RULED 2026-08-06 (session 3) to be the same property as CCP-411600, which carries the date. See `duplicate_of_facility_id`. The votingpatterns source file annotates this record 'Same property as primary' and gives its address as 777 Casino Ave, Thackerville - which the Indian Gaming Dataset also gives for WinStar World Casino and Resort (grand opening 2003, expansion 2024). WinStar is a single complex whose themed plazas (Beijing, Madrid, Paris, Rome, Vienna, London, New York, Cairo) were added across successive expansions; there is no 'additional plaza' with an opening of its own. CCP-411600 carries the 2003 date.`, `duplicate row - RULED 2026-08-06 (session 3) to be the same property as CCP-11800, which carries the date. See `duplicate_of_facility_id`. Address is byte-identical to the dated row - 321 Sitting Bull St against CCP-11800's 321 Sitting Bull Street, both Lower Brule SD, both Lower Brule Sioux Tribe - the votingpatterns source file cites 'GoldenBuffaloCasino.com', and the Indian Gaming Dataset independently records 'The Golden Buffalo Casino Restaurant and Motel' at 321 Sitting Bull St with a 1992 grand opening, agreeing with CCP-11800's 1992-02-15. Three sources, one property.`
- **`close_date_class`** — `absent`, `exact`
- **`close_date_precision`** — `month`, `day`, `year`
- **`open_date_event`** — `unspecified`, `gaming_commenced`, `property_opened`, `permanent_facility_opened`, `not_gaming_commencement`
- **`entity_tier`** — `B`, `A`
- **`duplicate_of_facility_id`** — `VP-0011`, `CCP-67000`, `CCP-688700`, `CCP-39900`, `CCP-908000`, `CCP-962300`, `CCP-800600`, `CCP-411600`, `CCP-11800`
- **`state_abbr`** — `CA`, `OK`, `WA`, `WI`, `MI`, `OR`, `NY`, `AZ`, `MN`, `IN`, `KS`, `NE`, `NM`, `CT`, `LA`, `MA`, `MO`, `MS`, `MT`, `ND`, `SC`, `WY`
- **`legal_theory`** — `Two-Part Secretarial Determination`, `Restored Lands`, `Within or Contiguous to Reservation Boundaries`, `Oklahoma - Within Former Reservation Boundaries`, `Initial Reservation`, `Settlement of a Land Claim`, `Within Last Recognized Reservation`
- **`decision_status`** — `Approved`, `Disapproved`, `Pending`
- **`source_url`** — `https://www.bia.gov/as-ia/oig/gaming-land-decisions`, `https://www.bia.gov/as-ia/oig/gaming-land-decisions/pending`
- **`project_page_url`** — `https://www.bia.gov/as-ia/oig/gaming-decisions/koi-nation-northern-california-shiloh-resort-and-casino-project`, `https://www.bia.gov/as-ia/oig/gaming-decisions/osage-nation-lake-ozark-casino-resort-project`, `https://www.bia.gov/as-ia/oig/gaming-decisions/colville-tribes-fee-trust-and-casino-project-franklin-county-washington`, `https://www.bia.gov/as-ia/oig/gaming-decisions/nisqually-quiemuth-casino-resort-and-fee-trust-project`, `https://www.bia.gov/as-ia/oig/gaming-decisions/menominee-indian-tribe-wisconsin-kenosha-casino-project`
- **`tribe_from_title`** — `Federated Indians of Graton Rancheria`, `Tunica-Biloxi Indian Tribe`, `Saint Regis Mohawk Tribe`
- **`entity_level`** — `facility`, `tribe`, `implan_sector_line_item`
- **`measure_type`** — `capacity`, `gaming_revenue`, `payment_to_government`
- **`unit`** — `machines`, `sq_ft`, `persons`, `outlets`, `tables`, `spaces`, `rooms`, `seats`, `usd_millions`
- **`value_verification`** — `published_by_source`, `source_archived`, `source_archived: data/raw/multistate_gaming_revenue/ok_gaming_compliance_{2018,2023}.pdf`, `source_archived: data/raw/multistate_gaming_revenue/ct_slot_revenue.csv`, `not_source_verified (hand-written estimate)`, `not_source_verified`, `source_archived state aggregate: data/raw/multistate_gaming_revenue/az_jlbc_2024.pdf`
- **`source`** — `Casino City Press gaming-property panel (tribal_casino_panel.dta)`, `OK State Auditor / OMES Gaming Compliance Unit`, `CT Dept of Consumer Protection / data.ct.gov dataset i6ts-ib7c`, `MI Gaming Control Board`, `Lumecon IMPLAN per-tribe inputs (Box)`, `OR OTGA Annual Report`, `MIGA estimates`, `OK State Auditor by-tribe`, `WA State Gambling Commission`, `Seminole Compact Annual Reports`, `WI Dept of Administration`, `CA Gambling Control Commission Quarterly`, `NY State Gaming Commission`, `AZ Joint Legislative Budget Committee`, `MI Gaming Control Board Tribal Compacts Annual`, `OR Tribal Gaming Alliance OTGA Annual Report`, `Minnesota Indian Gaming Association Public`, `Mille Lacs Corporate Ventures Public`, `CA Gambling Control Commission`, `WA State Gambling Commission Reports`
- **`as_of_date_precision`** — `day`, `year`

---

## CHANGES 2026-08-26 — `code/155`–`162`. Read this before using any date column.

Full log: `docs/GAMING_UNIVERSE_REBUILD_2026-08-26.md`.

### `open_date` and `close_date` no longer carry fabricated day precision

The description above says two thirds of the inherited ISO values are
year- or month-precision placeholders written as full dates, and told the
reader to consult `open_date_precision` instead. **That disclosure now lives in
the value itself.** 415 values whose own `*_precision` column said `year` or
`month` were re-typed — `1992-12-31` is now `1992`, `1985-04-15` is now
`1985-04`.

- 177 `open_date` → year · 162 `open_date` → month
- 17 `close_date` → year · 59 `close_date` → month
- 12 day-precision values kept, because a cited source states the day
- 3 re-sourced to a real day with a citable URL (`code/162`)

`*_not_before` / `*_not_after` are unchanged and remain the columns to parse.

| new variable | type | note |
|---|---|---|
| `open_date_source_value_verbatim` *(internal)* | text | the source's original string, retained so the retyping is reversible and auditable. Blank where nothing was changed. |
| `close_date_source_value_verbatim` *(internal)* | text | as above. |

`open_date_basis` and `close_date_basis` gain a sentence beginning
`DAY PRECISION WITHDRAWN 2026-08-26:` on every re-typed row.

**A re-typed date is not a publishable date.** 436 of them still rest only on
the Casino City vendor roster; see
`review/gaming_open_date_resourcing_2026-08-26.csv`.

### 10 new facility rows, prefix `CEDAR-FAC-`

Minted through `code/cedar_ids.allocate("CEDAR-FAC")`. Sourced from NIGC's
gaming location map, `source_datasets = NIGC_GAMING_LOCATION_MAP`,
`match_status = nigc_only_no_cedar_match`. **None carries an opening date**:
`open_date_class = absent`, because NIGC states that a location is a regulated
gaming operation *now* and states nothing about when it opened.

7 of the 10 carry a **tier B** tribe under
`entity_match_method = unanimous_city_operator` — every Cedar gaming property
already recorded in that town belongs to one tribe. That is corroboration, not
an identification. 3 carry no tribe, with the reason in `entity_match_basis`.

### New file: `data/clean/gaming_nigc_roster_link.csv` (442 rows)

One row per NIGC current gaming location that resolves to a Cedar property.
`match_basis` names the rung and `link_tier` is A or B; `nigc_listed_as_of`
dates the listing. **A Cedar row absent from this file is not a row NIGC
contradicts** — NIGC's map is a current-operations map and covers Class II/III
on Indian lands only.

### `gaming_facility_metrics.csv`

- `entity_id` is now populated on **65,436 of 68,211 rows (95.9%)**, by an exact
  join on `facility_id` into `gaming_facilities.csv`. The tier is **inherited
  from the facility row**, never assigned here.
- New `measure_type` value **`amount_wagered`** — handle / coin-in. It is not
  revenue and must never be summed with or substituted for a win or GGR figure.
- New `metric` values: `ct_slot_win_monthly`, `ct_slot_handle_monthly`,
  `ct_slot_contribution_monthly`, `ct_slot_weighted_average_machines`
  (2,988 rows, monthly, 1993-01 to 2025-12, per casino).
- New `source` value: `CT Dept of Consumer Protection / data.ct.gov dataset
  i6ts-ib7c (monthly series)`.
- **CT `payout` and `hold` are deliberately absent.** The source changes their
  units mid-series without changing the column name (`91.45` in 1993-01,
  `0.912` in 2025-12).
