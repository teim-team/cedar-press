# Codebook — Lobbying issue families, by year

*476 rows. Written 2026-08-28 to unblock codebook registration; definitions
taken from the values on disk, including the table's own
`preferred_series_for_trend` column.*

One row per issue family × filing year. The table carries **two different
denominators** and names which one to trend on, because choosing the wrong one
produces a series that tracks classification coverage rather than lobbying.

| Variable | Type | Units / format | Filled | Description |
|---|---|---|---:|---|
| `issue_family` | text | category | 100% | Issue family the filings were classified into (`agriculture`, …). Families group segments; one filing can carry several. |
| `filing_year` | integer | YYYY | 100% | Year the filings were submitted for. |
| `n_filings` | integer | count | 100% | Filings in that year naming this family. |
| `n_filings_with_any_family` | integer | count | 100% | Filings that year carrying **any** classified family. The denominator for `share_of_classified_filings`. |
| `share_of_classified_filings` | number | proportion 0-1 | 96% | `n_filings` over `n_filings_with_any_family`. Blank where that denominator is zero — blank means undefined, never 0. |
| `n_family_mentions_that_year` | integer | count | 100% | Total family mentions that year across all filings. A filing naming three families contributes three. |
| `share_of_family_mentions` | number | proportion 0-1 | 96% | `n_filings` over `n_family_mentions_that_year`. Blank where that denominator is zero. |
| `n_filings_total_that_year` | integer | count | 100% | All filings that year, classified or not. Context for how much of the year the classified set covers. |
| `preferred_series_for_trend` | text | column name | 100% | Which share column to trend on. The table states its own answer: `share_of_family_mentions`. |

## Reading it

**Trend on `share_of_family_mentions`, as the table itself says.**
`share_of_classified_filings` moves with how many filings were classifiable in a
given year, so a family can appear to rise purely because coverage improved.
The mention-based share holds the denominator to what was actually said.

**Compare `n_filings_with_any_family` against `n_filings_total_that_year`
before reading any year.** Where classified coverage is a small fraction of all
filings, every share in that row describes a minority of the year.

**A zero is real; a blank is not.** `n_filings = 0` means the family was named
by nobody that year. A blank share means the denominator was zero and the ratio
does not exist — never plot it as zero.

**Families are not mutually exclusive.** Shares across families in one year sum
above 1 on the filing denominator, because filings name several. That is the
data, not an error.
