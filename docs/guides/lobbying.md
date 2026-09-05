# Tribal Advocacy and Lobbying: a researcher's guide

Collection `lobbying` · public file `lobbying.csv` · v1 · 2026-09-04. Generated from `data/cedar/guides.json`, `data/cedar/field_map.json`, `data/cedar/codebook.json` and the collection descriptor by `scripts/guides-markdown.mjs`; edit those, not this file. Written 2026-09-05 under `docs/PUBLIC_DATASET_SPEC_2026-09-05.md`.

## Purpose

Federal advocacy by tribes and Native organisations across twenty channels — LDA registrations and reports, tribal consultation, Section 106, agency dockets, administrative appeals, hearing testimony and nonprofit Schedule C.

## Population

Federal advocacy by Native entities. The flagship is one row per Lobbying Disclosure Act filing whose client resolves to a Native entity; `activity_type` names the source family so that other documented families (consultation, testimony, agency dockets, ex parte records, comments, nonprofit Schedule C) can join under the same schema as they are obtained and supported. The Lobbying Disclosure Act sees a fraction of tribal advocacy: 300 entities appear in LDA filings, 669 in a non-LDA channel, and only 4 are visible to the LDA and nowhere else (collection descriptor, measured 2026-09-02).

## One row is

**Today:** One Lobbying Disclosure Act filing whose client resolves to a Native entity.

**When the specification is applied:** One advocacy activity, with activity_type saying which source family it is; LDA filings are the first family, one row per filing, and other documented families (consultations, testimony, ex parte, comments) join under the same schema only as they are obtained and supported.

**Grain change:** Owed (§9): the activity schema over the other source families the collection already holds in the workspace (hearing_appearances, ferc_ex_parte_*, oira_meetings, nrc_public_meetings, advocacy_passthrough). Each family is evaluated against the common schema before it ships; a lead is not coverage.

## Key identifiers

`activity_id` (owed) is the collection-wide key; `filing_id` is the LDA filing's own identifier; `client_id` and `registrant_id` are the LDA database's identifiers for the parties; `superseded_by_filing_id` names the amendment that replaces a filing.

## Sources and coverage

**Sources:** Senate and House lobbying disclosure; Federal Register consultation and ex parte notices; FERC and NRC dockets; IBIA and IBLA appeals; regulations.gov; IRS Form 990 Schedule C.

**Rows in the flagship table as released (recorded 2026-09-04):** 27,825. This is the count the release recorded for `native_entity_lobbying_disclosures.csv`, not the sum of the collection's 39 tables; the finished public table is re-measured at release and the count here is replaced by that measurement.

## Time and geography

`filing_year` and `filing_period` are the reporting period; `posted_date` is when the filing was posted. Client and registrant states are the parties' registered states, not where the lobbying happened.

## Entity relationships

The opening block of every row is `cedar_uid`, `cedar_entity_name`, `cedar_entity_type` and `cedar_entity_role`. `cedar_entity_role` is `client`: the Native entity is the filing's client, resolved to the register with `attribution_method` and `match_confidence`. The client's own name stays in `client_name`. A withdrawn attribution (`attribution_withdrawn` = 1) is a real filing that stays in the file with its Cedar link withdrawn and the reason stated; its spend is not Native lobbying.

Joining detailed collections on `cedar_uid` alone multiplies rows: one entity has many transactions here and many elsewhere. Aggregate each collection to the entity, or the entity and year, before joining measures.

## Revisions

Amendments supersede the filings they amend. `filing_status` is current or superseded; the default view counts current filings only, and the original and its amendment are never two spendings.

## Field dictionary

The approved header, in order (35 columns, of which 1 are owed and marked so). Data types are read off the ten-row sample the site serves; identifiers are text and keep leading zeros.

| # | Column | Label | Definition | Type | Blank means |
|---|---|---|---|---|---|
| 1 | `cedar_uid` | Cedar ID | Cedar's permanent identifier for the Native entity this record is attributed to. The join key across every collection; never the record's own ID. | identifier, as text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 2 | `cedar_entity_name` (was `canonical_name`) | Native entity | That entity's name as Cedar's register spells it, so one entity reads the same in every collection. The record's own names (recipient, contractor, organization) are kept in their own columns. | text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 3 | `cedar_entity_type` (was `entity_type`) | Entity type | Which of Cedar's eighteen classes the entity is (federally recognized tribe, Alaska Native village, ANCSA corporation, Native nonprofit, and so on), from the register. | text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 4 | `cedar_entity_role` | Entity role | Why the entity is on this row: client. | text | unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native |
| 5 | `activity_id` | activity id | A collection-wide activity identifier (lda:<filing_id> for this family) so families share one key space. | — | owed: not in the file until the terminal builds it |
| 6 | `activity_type` | Activity type | Which kind of documented advocacy the row is. Every row today is an LDA filing; other source families join under the same schema as they are obtained. | text | the source states none, or not applicable to this row |
| 7 | `filing_id` (was `filing_uuid`) | Filing ID | The filing's identifier in the Senate LDA database. | identifier, as text | the source states none, or not applicable to this row |
| 8 | `client_name` | Client | The client as the filing names it (the Native entity, in its own spelling). | text | the source states none, or not applicable to this row |
| 9 | `client_id` | Client ID | The client's identifier in the Lobbying Disclosure Act database. | identifier, as text | the source states none, or not applicable to this row |
| 10 | `client_state` | Client state | The client's state. | text | the source states none, or not applicable to this row |
| 11 | `registrant_name` | Registrant | The lobbying firm or, for a self-filer, the client itself. | text | the source states none, or not applicable to this row |
| 12 | `registrant_id` | Registrant ID | The registrant's identifier in the Lobbying Disclosure Act database. | identifier, as text | the source states none, or not applicable to this row |
| 13 | `registrant_state` | Registrant state | The registrant's state. | text | the source states none, or not applicable to this row |
| 14 | `self_filed` | Self-filed | Whether the client filed for itself rather than through a firm (yes or no). | yes or no (1 or 0) | not stated; 0 is no |
| 15 | `filing_type` (was `filing_type_display`) | Filing type | Registration, quarterly or year-end report, amendment, termination. | text | the source states none, or not applicable to this row |
| 16 | `filing_year` | Filing year | The year the filing covers. | year | the source states no date |
| 17 | `filing_period` | Period | Which reporting period of the year. | text | the source states none, or not applicable to this row |
| 18 | `posted_date` (was `dt_posted`) | Posted | When the filing was posted. | date and time | the source states no date |
| 19 | `termination_date` | Termination date | When the registration was terminated, where the filing is a termination. | text | the source states none, or not applicable to this row |
| 20 | `amount_usd` (was `spend_usd`) | Reported spend | Whichever of the two the filing reports; the basis column says which. | amount in US dollars, as recorded (no rounding; negative where the source records a reduction) | the source reports no amount; never zero |
| 21 | `amount_basis` (was `spend_basis`) | Basis of spend | Income, expenses, or none reported. | text | the source states none, or not applicable to this row |
| 22 | `income_usd` | Income reported | What the registrant reported receiving from the client this period. | amount in US dollars, as recorded (no rounding; negative where the source records a reduction) | the source reports no amount; never zero |
| 23 | `expenses_usd` | Expenses reported | What a self-filer reported spending this period. | amount in US dollars, as recorded (no rounding; negative where the source records a reduction) | the source reports no amount; never zero |
| 24 | `lobbying_issues_codes` | Issue codes | The LDA issue area codes on the filing. | text | the source states none, or not applicable to this row |
| 25 | `specific_issues_text` | Specific issues | What the filing says was lobbied on. | text | the source states none, or not applicable to this row |
| 26 | `government_entities` | Government entities contacted | Agencies and chambers the filing lists, separated by \|. | list, separated by | | the source states none, or not applicable to this row |
| 27 | `affiliated_organizations` | Affiliated organizations | Organizations the filing lists as affiliated with the client. | text | the source states none, or not applicable to this row |
| 28 | `filing_status` (was `supersession_status`) | Version status | Whether a later amendment replaces this filing. | text | the source states none, or not applicable to this row |
| 29 | `superseded_by_filing_id` (was `superseded_by_filing_uuid`) | Replaced by | The filing that replaces this one, where one does. | identifier, as text | the source states none, or not applicable to this row |
| 30 | `attribution_withdrawn` | Attribution withdrawn | Whether Cedar withdrew its link between this filing and the entity after review (yes or no). A withdrawn filing stays in the file; its spend is not counted as the entity's. | yes or no (1 or 0) | not stated; 0 is no |
| 31 | `attribution_withdrawn_reason` | Why withdrawn | The reason recorded for the withdrawal. | text | the source states none, or not applicable to this row |
| 32 | `attribution_method` | Attribution method | How the client was linked to the Native entity (an identifier, or a name with corroboration). | text | the source states none, or not applicable to this row |
| 33 | `match_confidence` | Match confidence | Cedar's confidence that the client is this entity. | text | the source states none, or not applicable to this row |
| 34 | `source_system` | Source system | Where the record came from: the Senate and House LDA database. | text | the source states none, or not applicable to this row |
| 35 | `source_url` (was `filing_url`) | Source | The filing on lda.senate.gov. | web address | the source states none, or not applicable to this row |

## Missing values

A blank is never zero and never an invented date. Beyond the column-level rules above:

- A blank `amount_usd` means the filing reports no amount (a registration, a termination, an activity below the threshold).
- A blank `superseded_by_filing_id` on a current filing is expected; on a superseded one it means the successor was not identified.

## Limitations

- `amount_usd` is the one amount the filing reports, with `amount_basis` saying whether it is the registrant's income or the self-filer's expenses. Income reported by a registrant and expenses reported by a client can describe overlapping activity and are never added.
- Non-monetary activity has a blank amount, not zero.
- The other source families are in the workspace and are owed under this schema (§9); a lead is not coverage, and the guide will name each family as it ships.

## Suitable analyses

- Lobbying spend by entity, year and issue code, over current filings with `attribution_withdrawn` = 0, income and expenses stated separately.
- Which registrants represent which entities, and for how long.
- Issues and government bodies lobbied, by year.

## Unsafe aggregations

- Summing amounts across original filings and their amendments.
- Adding registrant income to client expenses.
- Counting a withdrawn attribution's spend as Native lobbying.
- Reading LDA totals as the whole of tribal advocacy.

## What is still owed

Target columns the specification asks for that the terminal has not yet built from the full table. Each ships blank-free, not blank: it is absent until it exists.

- `activity_id` (derived:filing_id): A collection-wide activity identifier (lda:<filing_id> for this family) so families share one key space.

## Release, citation and method

**Version:** v1. **Release date:** 2026-09-04.

**Cite as:** Lumecon, "Tribal Advocacy and Lobbying" (v1), Cedar Press collection, cedarpress.ai. Add the date accessed.

**Method:** Built on the premise that the Lobbying Disclosure Act sees only a fraction of tribal advocacy: 300 entities appear in LDA filings, 669 appear in a non-LDA channel, and only 4 are visible to the LDA and nowhere else. Each channel is kept as its own record type rather than merged into a single misleading total, and organisations acting on behalf of many tribes are scoped as such rather than attributed to one.

Dataset-level version, release date and citation live here and in the manifest, never as rows appended to the CSV. The row-level `source_url` and the qualifications named above are the file's own provenance.

