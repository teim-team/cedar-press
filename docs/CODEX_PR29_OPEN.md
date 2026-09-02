
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

> **GAMING-DENOMINATOR-2026-09-02 — the gaming denominator, re-derived from the live files.**
> **`gaming_facilities.csv` holds 787 ROWS, and a row is not a facility.** The ladder, owned and gated by `code/846_session_audit.py::_denom`:
> 
> ```
> 787   rows in gaming_facilities.csv
> -16   whose NAME says no casino - 7 exactly "No casino", plus 9 more like
>       "Grand Canyon West - no casino", "Tribal admin only - no casino"
> =771   facility rows
> -57   extra rows across the same-tribe duplicate groups
> =714   distinct properties
> ```
> 
> **FIVE denominators circulated on 2026-09-02 and all five were quoted as settled: 787, 780, 734, 727, 714.** Each came from a different definition of "facility" and none said which. 787 is raw rows; 780 removes only the 7 EXACT placeholders and misses the 9 that say it in a longer name; 734 is 787 minus duplicates with every placeholder left in; 727 is 780 minus a duplicate count of 53. **None of them is wrong about the piece it measured, and four of them are wrong as a denominator.** No verdict is applied in the table itself - `duplicate_of_facility_id` is populated on 10 rows, not 57 - so 714 is a measurement, not a state of the file. Note also that the duplicate register carries `DIFFERENT_TRIBES_CHECK_BOTH` groups that are **not** duplicates: Stables Casino pairs the Miami Tribe with Modoc Nation, which is a joint operation. Dividing by 787 inflates the denominator by 10.2% and understates every gaming coverage percentage by about 9.3%.
>
> Authority: `code/846_session_audit.py::_denom`, which gates this ladder.
> Re-derive rather than quote: `py -3 code/1116_ruling_propagation_2026_09_02.py derive`.
> `py -3 code/1116_ruling_propagation_2026_09_02.py verify` exits 1 while any
> document in `docs/` or `review/` still states a superseded figure unmarked.
>
> Re-derive rather than quote: `py -3 code/1116_ruling_propagation_2026_09_02.py derive`.
> `py -3 code/1116_ruling_propagation_2026_09_02.py verify` exits 1 while any
> document in `docs/` or `review/` still states a superseded figure unmarked.

**CORRECTED 2026-09-02 — 780 is itself a partial denominator, and this finding is the reason five of them circulated.** Only **7** rows are the exact string `No casino`; **9 more say it inside a longer name** (`Grand Canyon West - no casino`, `Tribal admin only - no casino`, `Pueblo of Jemez - no casino`, `Las Vegas Paiute Smoke Shop - no casino`, `No casino currently`, and four others), so the facility-row count is **771**, and after the same-tribe duplicate groups it is **714 distinct properties**. See the note above. *The finding below is right about the defect and its number is one of the five.* ~~This newly establishes that only 780 of the 787 rows are facilities,~~ **771 of them are**, yet the shipped descriptor still claims “one row per facility, with the single non-facility row” and advertises `694 of 787 facilities` with 93 unbounded; `samples/README.md` likewise labels all 787 as gaming facilities, and later prose on lines 751–767 repeats facility-denominator claims. Those customer-facing coverage and grain statements remain false after discovering the seven `No casino` placeholders, so recalculate them using real facilities and explicitly account for the placeholder rows.

Useful? React with 👍 / 👎.

======================================================================
[4] id=3915763684  data/cedar/samples/README.md  line None
**![P2 Badge](https://img.shields.io/badge/P2-yellow?style=flat)  Include the NAGPRA cells in the mojibake totals**

The per-dataset counts immediately below add up to 116 repaired and 1,098 unrecoverable cells: contractors contributes 2 repaired, subcontracting contributes 114 repaired plus 1,096 unrecoverable, and NAGPRA contributes another 2 unrecoverable. This summary instead reports 1,096 unrecoverable out of 1,212, silently omitting the two NAGPRA cells even though they are handled by the same scoring guard; report 1,098 of 1,214 so the published coverage total agrees with its breakdown.

Useful? React with 👍 / 👎.
