# ADR-015 worked demonstration - the two sums, on one geography

*Generated 2026-09-02 by `code/874_geography_two_sums.py`. Every number is re-measured from `data/clean/` on each run; regenerate rather than edit.*

## Why this geography and not another

The selection rule is in `pick_demo()` and was applied to the file, not chosen by eye:

1. **Dataset must be an unfiltered universe.** Only `faads_transactions_all_agencies.csv` qualifies. Cedar's other two big money tables are Native-CANDIDATE corpora - their recipient universe was pulled from Native entity lists - so their place-of-performance sum for a county is not 'all federal money to that area' and the ADR-015 difference would be meaningless computed on them. This is the one table where it is not.
2. At least **200 rows** on the place-of-performance side.
3. At least **95% of those rows keyed at an EXACT tier** (the federal transaction record named the county), so the result does not rest on modal-zip inference.
4. Of what survives, the **largest Native-recipient sum** - the biggest case is the most useful demonstration and the least likely to be an artefact of small numbers.

98 of the 3,501 counties this dataset touches passed filters 2 and 3 with a non-zero Native sum.

The winner is **APACHE County, state FIPS 04 (county FIPS `04001`)**.

## The two sums, stated separately

Dataset `faads_transactions_all_agencies.csv`, FY2001-2007, money column `obligated_usd`.

| | sum | rows | rows keyed at an exact tier |
|---|---:|---:|---:|
| **money flowing TO the area** - sum by PLACE OF PERFORMANCE, every recipient | $153,611,719.00 | 222 | 222 |
| **money reaching NATIVE ENTITIES there** - sum by RECIPIENT county, Cedar-attributed Native recipients only | $497,400,007.00 | 571 | 0 |
| *for context* - all money by RECIPIENT county, every recipient | $969,693,754.00 | 1,404 | 163 |

**The two headline rows are different measures over different columns and that is the design.** The first is `geo_pop_county_fips`, the second is `geo_recipient_county_fips`. ADR-015 rule 1 exists because collapsing them into one 'county' column would destroy exactly this comparison.

## The difference, derived and bounded

ADR-015 rule 3 says publish the two sums and let the difference be derived. Derived here, once, so the bounds can be nailed to it:

```
  $    153,611,719.00   money performed in the county (place of performance)
- $    497,400,007.00   money reaching Native entities in the county (recipient)
= $   -343,788,288.00
```

That figure is **a ceiling, not an estimate**, and it is not a finding until every one of these is read with it:

1. **The Native sum is a floor.** It counts only recipients Cedar has attributed. Attribution is name and UEI matching; it misses and never invents. Better matching moves the Native sum up and the difference down, never the other way.
2. **The two sums do not partition the same rows.** A recipient headquartered outside the county can perform work inside it, and one inside it can perform work elsewhere - ADR-015 rule 3 names this directly. The context row is there so the reader can see how far apart the county's POP total ($153,611,719.00) and its recipient total ($969,693,754.00) actually are.
3. **A county is not a reservation.** A county is not a reservation (ADR-015 rule 2). Reservations span counties and counties contain fractions of reservations. This row is a county-level APPROXIMATION. Cedar holds no geocoded point inside any AIANNH area in this county. That is not evidence none overlaps it - only that Cedar cannot see one.
4. **Coverage.** Across the whole dataset, 2,250,759 rows carrying $1,699,737,123,392.83 have NO place-of-performance county key at all and sit in no county's POP sum; 367,716 rows carrying $329,474,133,066.00 have no recipient county key. Those dollars are unallocated, not zero.
5. **Never sum this across datasets.** ADR-015 rule 4: a shared county code is not permission to add this dataset's money to another's. MONEY_TOTALLING_RULES.md governs.

## The runners-up, so the winner is not the only case on show

| county | state FIPS | POP sum | POP rows | Native recipient sum | Native rows | AIANNH observed |
|---|---|---:|---:|---:|---:|---|
| APACHE | 04 | $153,611,719 | 222 | $497,400,007 | 571 | no |
| NAVAJO | 04 | $56,842,547 | 300 | $87,442,693 | 519 | yes |
| BRYAN | 40 | $7,424,794 | 233 | $85,154,050 | 151 | yes |
| OKMULGEE | 40 | $21,911,036 | 221 | $79,617,456 | 87 | yes |
| HUMBOLDT | 06 | $32,990,702 | 461 | $69,700,221 | 301 | yes |
| PONTOTOC | 40 | $11,878,372 | 249 | $67,360,170 | 172 | yes |
| HILL | 30 | $12,549,325 | 305 | $59,264,363 | 226 | no |
| WHATCOM | 53 | $28,728,056 | 625 | $57,956,557 | 321 | yes |
| MARICOPA | 04 | $1,206,146,476 | 5,192 | $55,861,311 | 214 | yes |
| CHIPPEWA | 26 | $13,912,436 | 242 | $50,111,305 | 280 | yes |
| OTTAWA | 40 | $8,815,795 | 205 | $43,315,268 | 465 | yes |
| PIMA | 04 | $109,518,547 | 1,461 | $41,992,955 | 290 | yes |

## Whole-dataset totals these cells partition

- rows: **2,769,748**, obligations **$1,830,639,317,707.66**
- Native-attributed: **29,594** rows, **$4,721,685,550.00** (faads_entity_attribution.csv joined on faads_row_id (0-based row ordinal), FY2001-2006)
- the FAADS row-ordinal join was re-proved this run on **29,594 of 29,594** attributed rows

Invariant I1 proves, to the cent, that the per-county POP sums plus the unallocated residual equal the dataset total, and the same on the recipient side. If that ever stops being true, `verify` exits 1.
