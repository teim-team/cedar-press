# ADR-015 worked demonstration - the two sums, on one geography

*Generated 2026-09-02 by `code/874_geography_two_sums.py`. Every number is re-measured from `data/clean/` on each run; regenerate rather than edit. The full table is `data/clean/geo_county_two_sums.csv`.*

## Why this geography and not another

A difference between two sums is only worth showing where **both sums are well covered**. Otherwise the difference measures Cedar's key coverage and not the world. The rule is in `pick_demo()` and was applied to the file:

1. A **real county**. USAspending writes `SS000` when it knows the state and not the county; 870 keeps those codes in the dimension rather than dropping them, and they are excluded here because a placeholder is not a geography.
2. At least **95% of rows keyed at an EXACT tier on BOTH sides** - the federal record named the county - so neither sum rests on modal-zip or modal-city inference.
3. At least **100 rows** on the place-of-performance side and **20 Native recipient rows**, so it is not a small-number artefact.
4. Prefer a county with an **AIANNH area observed inside it**. The measure is about Indian Country; a county with no reservation in it is a worse illustration of it whatever its dollars.
5. Then the largest Native-recipient sum.

**0 of 7,785 county-dataset cells passed.** That is a small number and it is the honest headline of this exercise: the geography axis now exists, and the places where it is exact enough on BOTH sides to carry a difference measure are still few.

**No cell passed. The demonstration cannot be made, and this document says so rather than lowering the bar until one does.**
