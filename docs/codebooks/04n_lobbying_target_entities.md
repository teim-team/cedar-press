# Codebook — Lobbying target entities

*116 rows. Written 2026-08-28 to unblock codebook registration; definitions
taken from the values on disk.*

One row per government body named as a lobbying target, as it appears on the
filings. This is the crosswalk between what registrants typed and the
department vocabulary the rest of the lobbying collection uses.

| Variable | Type | Units / format | Filled | Description |
|---|---|---|---:|---|
| `government_entity_as_filed` | text | text | 100% | The target body exactly as written on the LDA filing, including the filer's own capitalisation and abbreviation (`HOUSE OF REPRESENTATIVES`, `Interior, Dept of (DOI)`). Kept verbatim: it is the evidence of what was filed. |
| `n_filings` | integer | count | 100% | Filings naming this target string. Counted on the as-filed string, so two spellings of one department count separately here and are only combined by `normalized_department`. |
| `normalized_department` | text | category | 100% | The department the as-filed string resolves to. Both chambers resolve to `Congress`. |

## Reading it

**Never sum `n_filings` down the file.** One filing names several targets, so
the column double-counts across rows by design. The count of distinct filings
lives in the disclosure table, not here.

**Group on `normalized_department`, never on `government_entity_as_filed`.**
The as-filed string is the un-normalised half of the pair; grouping on it
splits one department across every spelling a registrant used, which is the
whole reason this crosswalk exists.

**A target is not an outcome.** Naming a body means the registrant reported
lobbying it, and says nothing about access, contact, or result.
