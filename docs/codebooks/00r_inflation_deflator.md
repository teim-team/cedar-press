# Codebook — Inflation deflator

*27 rows. Written 2026-08-28 to unblock codebook registration; every definition
below is taken from the values on disk, not composed.*

A reference series, not a Cedar measurement. It exists so that any dollar figure
in any collection can be expressed in constant terms against one declared base
year, using one declared source, rather than each script choosing its own.

| Variable | Type | Units / format | Filled | Description |
|---|---|---|---:|---|
| `year` | integer | YYYY | 100% | Calendar year the deflator index value applies to. |
| `gdp_deflator_index` | number | index | 100% | Implicit price deflator for GDP in that year, on the source's own index scale. Not a percentage and not a rate of change. |
| `base_year` | integer | YYYY | 100% | The year `factor_to_base` converts INTO. Constant down the column; a row whose base_year differs from its neighbours is a build error, not a variant. |
| `factor_to_base` | number | multiplier | 100% | Multiply a nominal dollar amount from `year` by this to express it in `base_year` dollars. Divide to go the other way. |
| `source` | text | citation | 100% | The published series the index came from, quoted rather than paraphrased so the figure can be re-fetched. |
| `retrieved` | text | YYYY-MM-DD | 100% | Date the source was read. The deflator is revised upstream, so a figure is only reproducible against the vintage named here. |

## Using it

**Deflate, do not inflate, when comparing across a long span.** Converting old
dollars forward to a recent base is the convention here (`base_year` is the
most recent year in the file), and mixing directions inside one series produces
a trend that is an artefact of the arithmetic.

**A deflated figure is derived and must say so.** Any published column carrying
constant dollars needs the base year in its own name or units, or a reader will
compare it against a nominal column and see a difference that is not there.
