# Codebook — Tribal Colleges and Universities roster

*37 rows. Written 2026-08-28 to unblock codebook registration; definitions taken
from the values on disk.*

One row per Tribal College or University, as listed by AIHEC. An entity roster:
it says who exists and how each was chartered, and carries the quoted evidence
for the chartering claim rather than asserting it.

| Variable | Type | Units / format | Filled | Description |
|---|---|---|---:|---|
| `name` | text | text | 100% | Institution name as published on the source roster. |
| `acronym` | text | text | 100% | Short form as published. Not unique across all Native institutions — join on the entity id, never on this. |
| `membership_tier` | text | category | 100% | The source's own membership class (e.g. `REGULAR MEMBERS`). A membership status with AIHEC, **not** an accreditation status and not a federal designation. |
| `state` | text | USPS code | 100% | State of the main campus. Institutions with campuses in several states appear once, under the main campus. |
| `chartered_year` | integer | YYYY | 100% | Year the institution was chartered. |
| `charter_marker` | text | category | 8% | Who granted the charter, where the profile text names it (`BIA`, `Congress`). **Blank on 92% of rows and blank means "the source did not say" — never "chartered by a tribe by default".** |
| `website` | text | URL | 100% | Institution website as listed. |
| `source_url` | text | URL | 100% | The roster page the row was read from. |
| `retrieved_date` | text | YYYY-MM-DD | 100% | Date the roster was read. The roster changes; a row is only reproducible against this vintage. |
| `ownership_evidence` | text | JSON array | 100% | Quoted passages supporting a chartering or ownership statement, each with its quote. `[]` where the profile text carried none — an empty array is "no evidence found", not "no ownership". |
| `serves_evidence` | text | JSON array | 100% | Quoted passages about who the institution serves. Frequently `[]`. |
| `profile_text` | text | text | 100% | The institution's profile prose as published, retained so any claim above can be checked against its source. |

## Reading it

**Chartered by a tribe, chartered by Congress and chartered by the BIA are
different facts**, and only 8% of rows say which. Do not fill the other 92% by
assumption; `charter_marker` is blank because the source was silent.

**The evidence columns are arrays, not booleans.** `[]` is the common case and
means nobody found a quote, which is not the same as a negative finding.

**This is a membership roster, not the TCU universe.** An institution absent
from AIHEC's list is absent here, whatever its status.
