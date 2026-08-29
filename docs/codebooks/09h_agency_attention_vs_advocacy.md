# Codebook — Agency attention vs advocacy

*22 rows (department grain) and 698 rows (department × year). Written 2026-08-28
to unblock codebook registration; definitions taken from the values on disk and
from the `*_basis` columns the table carries about itself.*

One row per department. Sets **what the government published about Indian
Country** beside **what registrants reported lobbying about**, so the two can be
compared — and the comparison is the entire point, which is also the main way it
can mislead.

| Variable | Type | Units / format | Filled | Description |
|---|---|---|---:|---|
| `department` | text | category | 100% | Cabinet department or executive body, normalised to one spelling. `White House / EOP` is a single bucket. |
| `fr_documents` | integer | count | 100% | Federal Register documents attributed to this department in the classifiable set. |
| `fr_share_of_agency_mentions` | number | proportion 0-1 | 100% | This department's share of all agency mentions in that set. |
| `lobbying_filings_targeting` | integer | count | 100% | LDA filings naming this department as a target. Filings name several targets, so this column double-counts across departments by design. |
| `lobbying_share_of_targets` | number | proportion 0-1 | 100% | This department's share of all target mentions. |
| `advocacy_minus_attention_pp` | number | percentage points | 100% | `lobbying_share_of_targets` minus `fr_share_of_agency_mentions`, in points. Positive = lobbied more than published about; negative = the reverse. **A difference between two shares of two different denominators, not a rate.** |
| `fr_share_executive_only` | number | proportion 0-1 | 95% | `fr_share_of_agency_mentions` recomputed with Congress excluded. |
| `lobbying_share_executive_only` | number | proportion 0-1 | 95% | `lobbying_share_of_targets` recomputed with Congress excluded. |
| `gap_pp_executive_only` | number | percentage points | 95% | `advocacy_minus_attention_pp` on the executive-only denominators. Blank on rows that are not executive bodies — blank means "not in this universe", never zero. |
| `fr_basis` | text | text | 100% | The measurement rule behind the FR columns, stated on the row so a reader cannot use the number without it. |
| `lobbying_basis` | text | text | 100% | The measurement rule behind the lobbying columns, same purpose. |

## The year file

`agency_attention_vs_advocacy_year.csv` is the same comparison at
department × year grain: `department`, `year`, `fr_documents`,
`lobbying_filings_targeting`. It carries **no share and no gap columns** — the
denominators shift year to year, and a share computed inside one year is not
comparable to the pooled shares above.

## Reading it

**The two sides count different things and neither is a denominator for the
other.** FR documents are publications by an agency. Lobbying filings are
reports by registrants about targeting an agency. `advocacy_minus_attention_pp`
is a difference of shares, and it is a description, not a finding.

**A gap is not lobbying success or agency neglect.** A department can publish
little and be lobbied heavily because its decisions are not made in the Federal
Register. Read `fr_basis` and `lobbying_basis` before drawing any inference —
they are on every row precisely so the caveat travels with the number.

**Congress dominates the lobbying side and has no FR presence.** That is why the
`*_executive_only` columns exist. Compare like with like, or the executive
departments all appear under-lobbied.

**In the year file, a zero in `lobbying_filings_targeting` is real but thin.**
Early years carry single-digit or zero counts; a ratio built on them is noise.
