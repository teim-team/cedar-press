# Codebook — Gaming mitigation agreements

*24 rows. Written 2026-08-28 to unblock codebook registration; definitions taken
from the values on disk.*

One row per agreement between a Nation and a local government, as disclosed in
the environmental assessment for a gaming project. Every row is sourced to a
document and a page, because the agreements themselves are mostly not public —
the EA's description of them is the evidence, and it is often incomplete.

| Variable | Type | Units / format | Filled | Description |
|---|---|---|---:|---|
| `project_id` | text | code | 100% | The gaming project the agreement belongs to. |
| `tribe` | text | text | 100% | Nation party to the agreement, as named in the source document. |
| `counterparty_government` | text | text | 100% | The other party — a county, municipality, sheriff's department, school district. |
| `counterparty_type` | text | category | 100% | Class of counterparty (`county law enforcement`, `municipality`). |
| `agreement_name` | text | text | 100% | Name of the instrument. Parenthesised where the EA describes an agreement without naming it. |
| `service` | text | text | 100% | What the agreement provides — emergency response, law enforcement, roads. |
| `agreement_status` | text | category | 100% | `executed`, `under_negotiation`, and similar. **An agreement described in an EA may never have been signed; this column is the only thing that says which.** |
| `amount` | text | text | 75% | The consideration exactly as the source states it, including where that is not a number (`rate premium, unquantified`). Kept verbatim. |
| `amount_basis` | text | category | 100% | How the amount is set: `fixed_annual`, `not_yet_agreed`, and similar. **Read this before `amount_value`.** |
| `amount_value` | number | numeric | 62% | The parsed figure, where one exists. Blank where the source gave no number — blank means undisclosed, never zero. |
| `amount_unit` | text | text | 62% | What `amount_value` is denominated in — `USD per year`, `percent of Net Win`. **`amount_value` is meaningless without it: 3 can be $3 or 3% of net win.** |
| `term` | text | text | 79% | Duration as stated. Often prose (`three years, commencing with the…`). |
| `effective_date` | text | YYYY-MM or YYYY-MM-DD | 79% | Start date where given; month precision where that is all the source offered. |
| `date_basis` | text | text | 100% | Where the date came from, or an explicit statement that the EA gave none. |
| `source_document` | text | text | 100% | Document the row was read from. |
| `source_url` | text | URL | 100% | Where that document is published. |
| `page` / `page_label` | integer / text | page | 100% | Page in the source. `page` is the PDF page; `page_label` is the printed number, and they differ. |
| `notes` | text | text | 87% | What the source did not say, most often — e.g. that the agreement text itself is not in the appendix. |

## Reading it

**Never sum `amount_value`.** The column mixes units — annual dollars and
percentages of net win — and 38% of rows have no value at all. A total across it
is meaningless. Filter on `amount_unit` first, and report the undisclosed count
alongside any figure.

**`executed` and `under_negotiation` are different facts.** An EA frequently
describes an agreement the parties intend to reach. Counting all rows as
agreements in force overstates what exists.

**These are the agreements an EA disclosed, not all agreements.** Only projects
requiring a federal action produce an EA, and an EA describes what the applicant
chose to describe. Absence here is not absence of an agreement.

**Two page columns, deliberately.** Citing the printed label when a reader has
the PDF, or the reverse, sends them to the wrong page.
