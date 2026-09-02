# 02l_individual_native_exclusion_pairs

*Tribal-link refusals from the five rulings that read 'Not a Native entity - individually Native-owned firm', recorded as (identifier, entity) PAIRS and blocking the NAME path as well as the identifier path. A refusal of a tribal link, never a refusal of Native ownership.*

Generated 2026-08-26 by `code/243_write_individual_native_class_codebook_fragment.py` from `individual_native_exclusion_pairs.csv` (5 rows, 17 variables).

**Publication is answered PER FIELD, never per dataset.** `published = 0` on 3 of 17 variables here; every one of them is a name, an address, an identifier that resolves to a name, or a sentence that pairs a person with an assertion about their ancestry.

| variable | type | units | filled | published | tier | description |
|---|---|---|---:|---:|---|---|
| `identifier_type` | text | category | 100.0% | 1 | public | `UEI`, `CAGE` or `NAME` - the key the owner's refusal was recorded against. |
| `identifier` | text | code | 100.0% | 0 | internal | WITHHELD from publication. See the one-hop rule: SAM's public entity search resolves a UEI to a legal name and a street address. |
| `firm_surrogate_entity_id` | text | code | 100.0% | 1 | public | The firm's Cedar surrogate. **The firm IS in the spine** as an individually Native-owned business; this row refuses a TRIBAL link, not the firm. |
| `firm_name_norm` | text | text | 100.0% | 0 | internal | WITHHELD from publication. Normalised firm name, present so a NAME-based resolver can honour the exclusion. |
| `firm_name_core` | text | text | 100.0% | 0 | internal | WITHHELD from publication. `core()` form of the firm name, same purpose. |
| `excluded_entity_id` | text | code | 40.0% | 1 | public | The spine entity the ruling refuses. Blank where the refusal is against ANY tribal, ANC or NHO owner rather than a named one. |
| `excluded_entity_name` | text | name | 40.0% | 1 | public | Canonical name of the refused entity. A tribe, ANC or NHO - a public body, so naming it raises none of the private-individual questions the firm's own name raises. |
| `excluded_entity_name_norm` | text | text | 40.0% | 1 | public | Normalised form of the refused entity's name. **Present so the exclusion blocks the NAME path.** `resolve_entity` matches on names, so an exclusion recorded only against an identifier hands the same bad match straight back through the resolver. |
| `excluded_entity_name_core` | text | text | 40.0% | 1 | public | `core()` form of the refused entity's name, same purpose. |
| `exclusion_scope` | text | category | 100.0% | 1 | public | `PAIR` where a specific entity is refused, `ALL_TRIBAL_ANC_NHO_ENTITIES` where the refusal is general. **An exclusion is scoped to a (identifier, entity) PAIR, never applied as a blanket block on the identifier** - a blanket block suppresses a correct attribution somewhere else. |
| `blocks_identifier_path` | int | 0/1 | 100.0% | 1 | public | Always 1. The exclusion applies to identifier-keyed resolution. |
| `blocks_name_path` | int | 0/1 | 100.0% | 1 | public | Always 1. A consumer that honours only the identifier column has done half the job and will re-derive the defect through the resolver. |
| `ruling_outcome` | text | category | 100.0% | 1 | public | The outcome this exclusion came from. Always the refuse-tribal-link-affirm-individual-ownership outcome. |
| `reason` | text | text | 100.0% | 1 | public | Why the pair is refused, in enough words to survive being read alone. |
| `does_not_mean` | text | text | 100.0% | 1 | public | What this row does NOT say - stated explicitly, because the ruling it comes from has already been misread once. It is not a finding that the firm is not Native-owned, and there is no NOT_NATIVE value in this schema. |
| `ruled_date` | date | ISO date | 100.0% | 1 | public | Date of the ruling. |
| `flagged_date` | date | ISO date | 100.0% | 1 | public | Date this exclusion row was written. |
