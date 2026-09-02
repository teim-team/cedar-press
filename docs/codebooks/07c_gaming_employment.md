# Codebook - `data/clean/gaming_employment_observations.csv`

*Variables only. One row is one employment figure from one source for one year. Multiple figures for one property-year are expected and are NOT reconciled.*

| variable | type | definition |
|---|---|---|
| `observation_id` | string | Cedar id. `EMP-OSHA-`, `EMP-LODES-`, `EMP-DOC-`, `EMP-EA-` by source family. |
| `facility_id` | string | Cedar property id (`CCP-`/`VP-`/`TPL-`). Blank where the figure could not be attached to one property. |
| `tribe_id` | string | Cedar entity id of the tribe, from `gaming_facilities.csv`. Never inferred from the source's own naming. |
| `year` | integer | Year the figure refers to: OSHA `year_filing_for`, the LODES vintage, or the document's own date. Blank if the source carries no date. |
| `employment` | integer | The figure exactly as the source states it. Never rounded, scaled, deflated or reconciled. |
| `measurement_type` | enum | `OSHA_ESTABLISHMENT_REPORTED`, `LODES_BLOCK_WORKPLACE_JOBS`, `ENVIRONMENTAL_REVIEW_COUNT`, `PROJECTED`, `PROPERTY_REPORTED_COUNT`. From `cedar_domain.MeasurementType`. `PROJECTED` and `ENVIRONMENTAL_REVIEW_COUNT` are in `NEVER_PROMOTES_TO_ACTIVE`. |
| `geographic_level` | enum | What the number is measured over: `establishment`, `census_block_2020`, `property`, `named_project`, or the document's own geography string. |
| `source_url` | string | The publisher's URL. Populated on every row whose source is a web object. |
| `source_quote` | string | Verbatim support. For prose sources, the sentence as printed (whitespace collapsed, nothing else changed). For tabular sources, the source's own field names and values quoted exactly, because a CSV row has no sentence. |
| `fetched_date` | date | When Cedar retrieved the object. |
| `confidence` | enum | `high` / `medium` / `low`. Not a probability and not an interval. |
| `built_date` | date | When this row was written. |
| `source_name` | string | Human-readable source, e.g. *OSHA Injury Tracking Application, Form 300A establishment summary*. |
| `source_record` | string | The exact file the row came from. |
| `measurement_note` | string | What this measurement is and is not. Travels with the row so a join cannot lose it. |
| `match_rule` | string | How the figure was attached to the property. Exact normalised name equality only; no containment, no fuzzy match. |
| `name_in_source` | string | The property/establishment name as the source writes it. A regulator using a different name is an ALIAS, not a second property. |
| `state` | string | State as the source records it. |
| `flags` | string | Machine-readable cautions, e.g. `BLOCK_JOBS_ARE_NOT_PROPERTY_PAYROLL`, `IDENTICAL_VALUE_FILED_UNDER_n_PROPERTY_NAMES_SAME_TRIBE_YEAR`. |
