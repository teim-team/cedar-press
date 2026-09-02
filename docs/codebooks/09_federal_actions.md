# Codebook — Federal Actions

*156,452 rows across 1 file(s). Generated 2026-08-07.*

Variables marked **internal** are retained for auditing and are not included in published extracts.

| Variable | Type | Units / format | Filled | Description |
|---|---|---|---:|---|
| `document_number` | text | code | 100% | Federal Register document number. |
| `publication_date` | text | YYYY-MM-DD | 100% | Date published in the Federal Register. |
| `effective_on` | text | YYYY-MM-DD | 28% | Date the action takes effect. |
| `title` | text | text | 100% | Title of the document. |
| `abstract` | text | text | 83% | Summary of the document. |
| `type` | text |  | 100% | One of: `Notice`, `Rule`, `Proposed Rule`, `Uncategorized Document`, `Presidential Document`, `Correction`, `Sunshine Act Document` |
| `action` | text | text | 83% | Action the document takes. |
| `agency_names` | text | text | 99% | Issuing agencies. |
| `agency_raw_names` | text | text | 99% | Issuing agencies exactly as named in the source. |
| `agency_slugs` | text | code | 99% | Short agency identifiers. |
| `docket_ids` | text | code | 67% | Docket identifiers. |
| `regulation_id_numbers` | text | code | 26% | Regulation Identifier Numbers. |
| `cfr_references` | text | citation | 41% | Code of Federal Regulations sections affected. |
| `comment_url` | text | URL | 1% | Link for submitting public comment. |
| `dates` | text | text | 81% | Dates stated in the document, such as comment deadlines and effective dates. |
| `html_url` | text | URL | 100% | Link to the document. |
| `pdf_url` | text | URL | 98% | Link to the document as filed. |
| `json_url` | text | URL | 100% | Link. |
| `net_caught` | text |  | 100% | One of: `keyword`, `both`, `agency` |
| `keyword_terms_matched` *(internal)* | text |  | 100% |  |
| `title_abstract_term_hit` | integer | 0 to 1 | 100% | One of: `0`, `1` |
| `title_abstract_terms` *(internal)* | text |  | 14% |  |
| `source_url` | text | URL | 100% | Link to the record's published source. |
| `api_endpoint` | text |  | 100% | One of: `https://www.federalregister.gov/api/v1/documents.json` |
| `fetched_date` | text | YYYY-MM-DD | 100% | Date. |
| `action_type` | text | category | 100% | Classified action type, such as a rule, notice, or proposed rule. |
| `action_type_rule` *(internal)* | text |  | 44% |  |
| `action_type_signal` *(internal)* | text |  | 44% |  |
| `action_type_source_field` | text |  | 44% | One of: `type`, `title`, `abstract` |
| `tribe_or_native_entity` | empty | text | 0% | Native entity named in the document. |
| `classified_date` | text | YYYY-MM-DD | 100% | Date. |
| `pre_2000_flag` | integer | 0/1 | 14% | 1 when the record predates the 2000 coverage floor. Such records are retained but fall outside the standard reporting window. |
| `floor_basis_field` | text |  | 100% | One of: `publication_date` |

## Value sets

- **`type`** — `Notice`, `Rule`, `Proposed Rule`, `Uncategorized Document`, `Presidential Document`, `Correction`, `Sunshine Act Document`
- **`net_caught`** — `keyword`, `both`, `agency`
- **`action_type`** — `other`, `rulemaking`, `grant_solicitation`, `ancsa_conveyance`, `tribal_state_compact`, `land_into_trust`, `liquor_ordinance`, `consultation`, `federal_acknowledgment`, `reservation_proclamation`, `gaming_land_decision`, `irrigation_rates`, `recognition_list_update`
- **`action_type_source_field`** — `type`, `title`, `abstract`
