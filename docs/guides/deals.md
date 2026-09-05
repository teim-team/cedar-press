# Indian Country Deals: a researcher's guide

Collection `deals` · public file `deals.csv` · v1 · 2026-09-04. Generated from `data/cedar/guides.json`, `data/cedar/field_map.json`, `data/cedar/codebook.json` and the collection descriptor by `scripts/guides-markdown.mjs`; edit those, not this file. Written 2026-09-05 under `docs/PUBLIC_DATASET_SPEC_2026-09-05.md`.

## Purpose

Transactions involving Native entities — acquisitions, joint ventures, project financings, bond issuances and major capital projects — with the parties, the instrument and the announced value where one was published.

## Population

Announced transactions and awards involving a Native party: acquisitions, joint ventures, project financings, bond issuances, grants and major capital projects, with the parties, the instrument and the announced value where one was published. This is the one Cedar dataset that does not exist elsewhere, so every row carries a source link (collection descriptor). Inclusion is by a documented transaction, not by a press mention.

## One row is

**Today:** One announced transaction or award involving a Native party, classified.

**When the specification is applied:** One distinct transaction or project-financing event, enriched as new sources confirm it and updated as its status changes; several articles about one event are one row.

**Grain change:** Owed (§7): the event-boundary pass on the full table (a source index already exists in deals_source_index.csv); the three overlapping category fields are combined into one taxonomy only after the terminal tests where they disagree.

## Key identifiers

`deal_id` is Cedar's identifier for the event. Parties are named as published (`native_party`, `counterparty`); the Native party's register identity is the opening block.

## Sources and coverage

**Sources:** Tribal newsletters and tribal press; trade and journalist coverage; ANCSA shareholder filings; and Cedar's own federal contracting record, cited as a source where a transaction is visible only there.

**Rows in the flagship table as released (recorded 2026-09-04):** 1,073. This is the count the release recorded for `deals_classified.csv`, not the sum of the collection's 20 tables; the finished public table is re-measured at release and the count here is replaced by that measurement.

## Time and geography

`event_date` is the announcement date at the precision `event_date_precision` states (day, month or year); no day is invented for a month-precision date. `closing_date` ships only where a source confirms it (owed). `state` and `location` are the deal's or project's location as published.

## Entity relationships

The opening block of every row is `cedar_uid`, `cedar_entity_name`, `cedar_entity_type` and `cedar_entity_role`. `cedar_entity_role` is the Native party's role in the deal: acquirer, borrower, issuer, partner, grantee, seller. `native_party_type` is the party's kind as the source states it and `cedar_entity_type` the register's class; they can differ and both ship.

Joining detailed collections on `cedar_uid` alone multiplies rows: one entity has many transactions here and many elsewhere. Aggregate each collection to the entity, or the entity and year, before joining measures.

## Revisions

A new source confirming an existing transaction enriches the row; a press release naming several distinct transactions can produce several rows. `verification_status` says how the row was verified. The consolidation of the three overlapping category fields into one `deal_category`, and of the two status fields into one `status`, is owed until the terminal tests where they disagree (§7).

## Field dictionary

The approved header, in order (31 columns, of which 4 are owed and marked so). Data types are read off the ten-row sample the site serves; identifiers are text and keep leading zeros.

| # | Column | Label | Definition | Type | Blank means |
|---|---|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the Native entity this record is attributed to. The join key across every collection; never the record's own ID. | identifier, as text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 2 | `cedar_entity_name` (was `native_party_canonical_name`) | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) are kept in their own columns. | text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 3 | `cedar_entity_type` | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. | text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 4 | `cedar_entity_role` (was `native_party_role`) | Entity role | Why the entity is on this row: read from native_party_role (acquirer, borrower, issuer, partner, grantee, seller). | text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 5 | `deal_id` (was `Deal_ID`) | Deal ID | Cedar's identifier for the deal. | identifier, as text | the source states none, or not applicable to this row |
| 6 | `deal_title` (was `Deal_Title`) | Title | A one-line description of the deal. | text | the source states none, or not applicable to this row |
| 7 | `native_party` (was `Native_Party`) | Native party as published | The Native party's name as the source gives it. | text | the source states none, or not applicable to this row |
| 8 | `native_party_type` (was `Native_Party_Type`) | Native party type as published | How the source describes the Native party. | text | the source states none, or not applicable to this row |
| 9 | `counterparty` (was `Counterparty_or_Funder`) | Counterparty or funder | The other side of the deal. | text | the source states none, or not applicable to this row |
| 10 | `deal_category` | deal category | One deliberate taxonomy (financing, acquisition, partnership, asset sale, project announcement, grant) built after the three are tested for agreement. | — | owed: not in the file until the terminal builds it |
| 11 | `industry` (was `Industry`) | Industry | The industry the deal is in. | text | the source states none, or not applicable to this row |
| 12 | `sector` | Sector | The broad sector the deal belongs to, beside the finer industry. | text | the source states none, or not applicable to this row |
| 13 | `capital_source` | Capital source | Where the capital comes from: public, private or tribal. | text | the source states none, or not applicable to this row |
| 14 | `event_date` (was `Event_Date`) | Date | When the deal happened or was announced. | text | the source states none, or not applicable to this row |
| 15 | `event_date_precision` (was `Event_Date_precision`) | Date precision | Whether the date is known to the day, the month or the year. | text | the source states none, or not applicable to this row |
| 16 | `closing_date` | closing date | The closing date where a source confirms it; blank otherwise. | — | owed: not in the file until the terminal builds it |
| 17 | `status` | status | Announced, completed, cancelled, unconfirmed. | — | owed: not in the file until the terminal builds it |
| 18 | `announced_value_usd` (was `Announced_Value_USD`) | Announced value | The dollar value announced, where one was. | amount in US dollars, as recorded (no rounding; negative where the source records a reduction) | the source reports no amount; never zero |
| 19 | `value_basis` (was `Value_Type`) | What the value is | What the announced figure represents (consideration paid, grant amount, project cost). | text | the source states none, or not applicable to this row |
| 20 | `project_total_value_usd` (was `Project_Total_Value_USD`) | Project total | The total project value, where larger than the announced value. | amount in US dollars, as recorded (no rounding; negative where the source records a reduction) | the source reports no amount; never zero |
| 21 | `state` (was `State`) | State | The state the deal is located in. | text | the source states none, or not applicable to this row |
| 22 | `location` (was `Location`) | Location | The place, as the source gives it. | text | the source states none, or not applicable to this row |
| 23 | `description` (was `Description`) | Description | A longer description of the deal. | text | the source states none, or not applicable to this row |
| 24 | `native_connection` (was `Native_Connection`) | Native connection | Why this deal is in the collection: how the Native party is connected. | text | the source states none, or not applicable to this row |
| 25 | `research_note` | research note | A short factual caveat where one is needed ("Amount covers the entire joint venture; the Native participant's share is not stated"). | — | owed: not in the file until the terminal builds it |
| 26 | `verification_status` (was `Verification_Status`) | Verification | Whether the deal was verified against a primary source. | text | the source states none, or not applicable to this row |
| 27 | `attribution_tier` (was `native_party_attribution_tier`) | Attribution tier | How firmly the Native party resolves to Cedar's register (A strongest). | text | the source states none, or not applicable to this row |
| 28 | `source_url` (was `Source_1`) | Source | The primary source document or page. | text | the source states none, or not applicable to this row |
| 29 | `source_type` (was `Source_1_Type`) | Source type | What kind of document the primary source is. | text | the source states none, or not applicable to this row |
| 30 | `source_url_2` (was `Source_2`) | Second source | A second source, where one was found. | text | the source states none, or not applicable to this row |
| 31 | `source_type_2` (was `Source_2_Type`) | Second source type | What kind of document the second source is. | text | the source states none, or not applicable to this row |

Until the combined columns exist, the file carries their sources, each with its own label:

- `Deal_Category` (Category) combines into `deal_category`: Acquisition, grant or public financing, joint venture, and so on.
- `Event_Type` (Event) combines into `deal_category`: What kind of event this row records (an acquisition of a 90% interest, an award).
- `transaction_type` (Transaction type) combines into `deal_category`: The third of three overlapping classifications; shown until the one taxonomy replaces all three.
- `Status` (Status) combines into `status`: Completed, announced, awarded, pending.
- `deal_status_std` (Status (standardized)) combines into `status`: The standardized status; shown until one status column replaces the two.

## Missing values

A blank is never zero and never an invented date. Beyond the column-level rules above:

- A blank `announced_value_usd` means the value was not published, never zero.
- A blank `closing_date` means no source confirms a closing.

## Limitations

- Values are announced values. `value_basis` says what the announced value measures; `project_total_value_usd` is the whole project's value and is not the Native participant's share, which is never allocated by guesswork.
- Missing transactions and undisclosed values mean no market total can be built from this file.
- Where an ownership change is visible only in federal contracting, the row cites the contracting record so the reader can re-run the check.

## Suitable analyses

- Deal counts by category, industry, state and year.
- Announced values by category where `value_basis` is comparable, stated with the count of undisclosed values.
- Which entities transact with which counterparties.

## Unsafe aggregations

- Summing announced values across different `value_basis` values, or adding project totals to consideration paid.
- Reading the sum of announced values as a market size.
- Counting an announcement and its completion as two deals.

## What is still owed

Target columns the specification asks for that the terminal has not yet built from the full table. Each ships blank-free, not blank: it is absent until it exists.

- `deal_category` (combine:Deal_Category\|transaction_type\|Event_Type): One deliberate taxonomy (financing, acquisition, partnership, asset sale, project announcement, grant) built after the three are tested for agreement.
- `status` (combine:Status\|deal_status_std): Announced, completed, cancelled, unconfirmed.
- `closing_date` (pending:source review): The closing date where a source confirms it; blank otherwise.
- `research_note` (derived:Notes): A short factual caveat where one is needed ("Amount covers the entire joint venture; the Native participant's share is not stated").

## Release, citation and method

**Version:** v1. **Release date:** 2026-09-04.

**Cite as:** Lumecon, "Indian Country Deals" (v1), Cedar Press collection, cedarpress.ai. Add the date accessed.

**Method:** This is the one Cedar dataset that does not exist elsewhere, so every row carries a source link. Announced and closed are labelled separately and a transaction enters totals only when its status is confirmed. Where an ownership change is visible in federal contracting but was never publicly announced, Cedar reports it and cites the contracting record with the identifier and years so a reader can re-run the check — and a change of reporting parent within one tribal corporate family is not treated as a transaction.

Dataset-level version, release date and citation live here and in the manifest, never as rows appended to the CSV. The row-level `source_url` and the qualifications named above are the file's own provenance.

