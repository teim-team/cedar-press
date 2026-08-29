# Codebook — Lobbying disclosure verbosity, by year

*27 rows. Written 2026-08-28 to unblock codebook registration; definitions taken
from the values on disk.*

One row per filing year. Measures **how much detail registrants wrote**, not how
much lobbying happened — the two move independently and conflating them is the
main way this table gets misread.

| Variable | Type | Units / format | Filled | Description |
|---|---|---|---:|---|
| `filing_year` | integer | YYYY | 100% | Year the filings were submitted for. |
| `n_classified_filings` | integer | count | 100% | Filings in that year that carried enough issue text to classify. The denominator for both means below — and it is small in the early years (single digits before 2003), so those means are volatile. |
| `mean_issue_families_per_filing` | number | families / filing | 100% | Average distinct issue families named per classified filing. |
| `mean_segments_per_filing` | number | segments / filing | 100% | Average distinct issue segments per classified filing. Always ≥ the family mean, since families group segments. |

## Reading it

**This is a REPORTING-REGIME series, not an activity series.** A rise means
filings described more issues, which can follow a disclosure-form change, a
guidance update, or a change in who files — none of which is a change in
lobbying. Do not plot it beside spend or filing counts without saying so.

**The early years are not comparable to the late ones.** With
`n_classified_filings` in the single digits, one verbose filing moves the mean
by a whole family. Read `n_classified_filings` before reading either mean.

**Classified is a subset.** Filings with no usable issue text are absent
entirely, so this describes the classifiable population, not all filings.
