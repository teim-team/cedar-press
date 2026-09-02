
======================================================================
[1] id=3915763659  data/cedar/README.md  line 277
**![P2 Badge](https://img.shields.io/badge/P2-yellow?style=flat)  Count all three blocked datasets in the overview**

Fresh evidence in this push is the newly added `federal-register` blocker, which makes three blocked datasets, but this sentence still says “Both” and the earlier overview on lines 65–69 still says only two blocker lists are non-empty (`owned` and `deals`). Consumers reading either summary receive a status count that contradicts the adjacent table and `.cedar.json`; update both summaries to name all three.

Useful? React with 👍 / 👎.

======================================================================
[2] id=3915763667  data/cedar/README.md  line 551
**![P2 Badge](https://img.shields.io/badge/P2-yellow?style=flat)  Remove the obsolete top-up description**

The new text says every race discards both passes and retries, but the same README still says on lines 654–661 that pass two “now” collects spares, tops up the mixed sample, and prints `RACED`. That leaves the documented current behavior internally contradictory and makes it unclear whether the round-4 race fix is actually active; rewrite the later paragraph as historical behavior or describe the retry logic there.

Useful? React with 👍 / 👎.

======================================================================
[3] id=3915763674  data/cedar/README.md  line 603
**![P2 Badge](https://img.shields.io/badge/P2-yellow?style=flat)  Propagate the corrected gaming denominator**

This newly establishes that only 780 of the 787 rows are facilities, yet the shipped descriptor still claims “one row per facility, with the single non-facility row” and advertises `694 of 787 facilities` with 93 unbounded; `samples/README.md` likewise labels all 787 as gaming facilities, and later prose on lines 751–767 repeats facility-denominator claims. Those customer-facing coverage and grain statements remain false after discovering the seven `No casino` placeholders, so recalculate them using real facilities and explicitly account for the placeholder rows.

Useful? React with 👍 / 👎.

======================================================================
[4] id=3915763684  data/cedar/samples/README.md  line None
**![P2 Badge](https://img.shields.io/badge/P2-yellow?style=flat)  Include the NAGPRA cells in the mojibake totals**

The per-dataset counts immediately below add up to 116 repaired and 1,098 unrecoverable cells: contractors contributes 2 repaired, subcontracting contributes 114 repaired plus 1,096 unrecoverable, and NAGPRA contributes another 2 unrecoverable. This summary instead reports 1,096 unrecoverable out of 1,212, silently omitting the two NAGPRA cells even though they are handled by the same scoring guard; report 1,098 of 1,214 so the published coverage total agrees with its breakdown.

Useful? React with 👍 / 👎.
