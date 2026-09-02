# Codebook — Grantmaker funding overlap

*69 rows. Written 2026-08-28 to unblock codebook registration; definitions taken
from the values on disk, including the table's own `row_caveat` column.*

One row per funder × resolved recipient. Records that a grantmaker funded an
institution on a documented side of the ICWA litigation, and **how weak that
fact is as an inference about the funder**.

> **The table states its own caveat on every row, and it governs this codebook:
> a shared funder is not a shared position.** A foundation appearing here has
> made a grant. It has not thereby endorsed anything, and `carries_institutional_position`
> is `0` on these rows precisely so nobody reads it as endorsement.

| Variable | Type | Units / format | Filled | Description |
|---|---|---|---:|---|
| `funder_key` | text | code | 100% | Short internal key for the funder. Stable within this table; not a Cedar entity id. |
| `funder_ein` | text | EIN | 100% | Employer Identification Number of the filing foundation. The join key to the 990 layer. |
| `funder_name_canonical` | text | text | 100% | Foundation legal name as filed. |
| `funder_is_donor_advised_fund` | boolean | 0/1 | 100% | 1 where the funder is a donor-advised fund. **A DAF grant identifies the sponsor, not the originating donor** — attribution stops at the sponsor. |
| `recipient_resolved_target` | text | code | 100% | Recipient institution, resolved to one key across name variants. |
| `recipient_side` | text | category | 100% | Which documented side the recipient sits on (e.g. `DOCUMENTED_ANTI_ICWA_INSTITUTION`). A classification of the **institution**, established from its own filings or litigation record — not of the grant. |
| `overlap_tier` | text | category | 100% | Which side of the overlap this row represents. |
| `n_grants` | integer | count | 100% | Grants from this funder to this recipient across `tax_years`. |
| `cash_grant_usd_total` | number | USD, nominal | 100% | Total cash granted across those years. Nominal; deflate with `inflation_deflator` before comparing across time. |
| `tax_years` | text | comma-separated YYYY | 100% | Filing years the grants appear in. Tax year, not calendar year of payment. |
| `recipient_unit_identified_breakdown` | text | category | 100% | Whether the grant could be attributed to a unit inside the recipient, or the recipient is a single legal person so the question does not arise. |
| `recipient_match_basis_breakdown` | text | category | 100% | How the recipient was matched (e.g. `recipient_name_phrase_match_no_ein`). **A name-phrase match with no EIN is weaker than an EIN match and this column is the only place that shows it.** |
| `example_purposes_verbatim` | text | text | 18% | Grant purpose as written on the 990, quoted. Blank on most rows — blank means the filing gave no purpose, not that none existed. |
| `funder_gave_to_both_sides_unit_identified` | boolean | 0/1 | 100% | 1 where this funder also funded the other side, at unit-identified grain. |
| `funder_gave_to_both_sides_institution_level` | boolean | 0/1 | 100% | Same at institution grain. **Both-sides funding is common and is the clearest reason a single row cannot be read as alignment.** |
| `evidence_class` | text | category | 100% | What kind of evidence the row is. `FUNDER_ACTIVITY` = a grant was made; it is not a statement of position. |
| `carries_institutional_position` | boolean | 0/1 | 100% | 1 only where the FUNDER itself has a documented institutional position. `0` on a funder-activity row. **This is the column that separates "gave money" from "took a side".** |
| `row_caveat` | text | text | 100% | The caveat, carried on the row so it travels with the number into any extract. |
| `built_date` | text | YYYY-MM-DD | 100% | Build date. |
| `built_by_script` | text | path | 100% | Script that produced the row. |

## Reading it

**Never publish a funder as anti-ICWA on the strength of a row here.** The
row's own `evidence_class` is `FUNDER_ACTIVITY` and its
`carries_institutional_position` is `0`. Those two columns exist to stop exactly
that inference.

**Check `funder_gave_to_both_sides_*` before writing a sentence about any
funder.** A foundation funding both sides is not taking one.

**`recipient_match_basis_breakdown` is the confidence column.** A phrase match
with no EIN can attach a grant to the wrong organisation of a similar name; read
it before quoting `cash_grant_usd_total`.

**Totals are nominal and span several tax years.** Deflate before comparing, and
say which years, because `tax_years` differs row to row.
