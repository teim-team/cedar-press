# Codebook — TCU / CDFI ownership evidence

*130 rows. Written 2026-08-28 to unblock codebook registration; definitions
taken from the values on disk.*

One row per **quoted passage**, not per institution. This is the evidence layer
behind chartering and ownership statements for Tribal Colleges and Native
CDFIs: it records what a source actually said, where it said it, and which
pattern matched — so a claim can be checked rather than trusted.

| Variable | Type | Units / format | Filled | Description |
|---|---|---|---:|---|
| `institution` | text | text | 100% | Institution the passage is about, as named on the roster it came from. |
| `layer` | text | category | 100% | Which roster the institution sits in (`TCU`, and the CDFI layer). Determines which universe the row belongs to; the two are not merged. |
| `pattern` | text | category | 100% | The extraction pattern that matched (`chartered_by`, `x_chartered_y`). **Names how the passage was found, not how reliable it is** — a matched pattern is a candidate, not a ruling. |
| `captured_owner` | text | text | 26% | The chartering or owning body the pattern captured. **Blank on 74% of rows** — the pattern matched a passage but did not yield a clean owner string. Blank means "not extracted", never "no owner". |
| `quote` | text | text | 100% | The source sentence, verbatim. The evidence itself; every other column is a claim about it. |
| `evidence_url` | text | URL | 100% | Page the quote was read from. |

## Reading it

**One institution has several rows.** The grain is the passage. Counting rows
counts quotes, not colleges — deduplicate on `institution` before any per-entity
figure.

**`captured_owner` is a candidate, not an attribution.** It is filled on a
quarter of rows and was produced by pattern match, not by a ruling. Promoting it
into an ownership assertion requires the ruling path; an exact string here says
nothing about the correctness of the link.

**A quote establishes what a source said, not that it is true.** These are
institutional self-descriptions from about-pages. They are good evidence of a
chartering claim and weak evidence of current governance.

**Absence is not evidence.** An institution with no row here had no passage
match, which happens when a site is worded differently or was unreachable.
