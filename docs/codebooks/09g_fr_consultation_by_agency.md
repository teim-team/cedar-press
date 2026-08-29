# Codebook — Federal Register consultation notices, by agency

*21 rows. Written 2026-08-28 to unblock codebook registration; definitions taken
from the values on disk.*

One row per department. A rollup of the consultation-notice layer, not a source
record: the grain is the agency, and the counts are of Cedar's own classified
notices.

| Variable | Type | Units / format | Filled | Description |
|---|---|---|---:|---|
| `normalized_department` | text | category | 95% | Cabinet department or independent agency the notice was issued by, normalised to one spelling. Blank where the issuing body could not be resolved to a known department — blank is "unresolved", never "none". |
| `n_consultation_notices` | integer | count | 100% | Federal Register notices classified as tribal consultation and attributed to this department. |
| `share_of_notices` | number | proportion 0-1 | 100% | This department's share of all classified consultation notices. A proportion, not a percentage. |

## Reading it

**These are counts of NOTICES, not of consultations.** One notice can announce
several sessions and several sessions can share one notice, so this measures
publication activity in the Federal Register, not how often an agency consulted.

**`share_of_notices` sums across the whole file, including the blank
department.** Dropping the unresolved row and re-normalising changes every
share; if you filter, say so, because the denominators no longer match the
published figures.

**Agency attention is not agency obligation.** A department with few notices may
consult heavily under a different instrument, or may publish elsewhere. This
column answers "who published tribal consultation notices" and nothing wider.
