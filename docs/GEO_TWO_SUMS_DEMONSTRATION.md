# ADR-015 worked demonstration - the two sums, on one geography

*Generated 2026-09-02 by `code/874_geography_two_sums.py`. Every number is re-measured from `data/clean/` on each run; regenerate rather than edit. The full table is `data/clean/geo_county_two_sums.csv`.*

## Why this geography and not another

A difference between two sums is only worth showing where **both sums are well covered**. Otherwise the difference measures Cedar's key coverage and not the world. The rule is in `pick_demo()` and was applied to the file:

1. A **real county**. USAspending writes `SS000` when it knows the state and not the county; 870 keeps those codes in the dimension rather than dropping them, and they are excluded here because a placeholder is not a geography.
2. At least **95% of rows keyed at an EXACT tier on BOTH sides** - the federal record named the county - so neither sum rests on modal-zip or modal-city inference.
3. At least **100 rows** on the place-of-performance side and **20 Native recipient rows**, so it is not a small-number artefact.
4. Prefer a county with an **AIANNH area observed inside it**. The measure is about Indian Country; a county with no reservation in it is a worse illustration of it whatever its dollars.
5. Then the largest Native-recipient sum.

**5 of 7,785 county-dataset cells passed.** That is a small number and it is the honest headline of this exercise: the geography axis now exists, and the places where it is exact enough on BOTH sides to carry a difference measure are still few.

The winner is **ROOSEVELT County, state FIPS 30 (county FIPS `30085`)**, on `federal_funding_transactions.csv`.

Cedar's geocoded points place AIANNH area(s) `1250R` inside it. See `data/clean/geo_aiannh_dim.csv` for what those are.

## The two sums, stated separately

Dataset `federal_funding_transactions.csv`, FY2007-2026, money column `obligated_usd`.

| | sum | rows | rows keyed at an exact tier |
|---|---:|---:|---:|
| **money flowing TO the area** - sum by PLACE OF PERFORMANCE, every recipient | $231,438,735.86 | 443 | 443 |
| **money reaching NATIVE ENTITIES there** - sum by RECIPIENT county, Cedar-attributed Native recipients only | $171,641,950.76 | 145 | 143 |
| *for context* - all money by RECIPIENT county, every recipient | $171,641,950.76 | 146 | 143 |

**The two headline rows are different measures over different columns, and that is the design.** The first reads `geo_pop_county_fips`, the second `geo_recipient_county_fips`. ADR-015 rule 1 exists because collapsing them into one `county` column would destroy exactly this comparison.

## The difference, derived and bounded

Rule 3 says publish the two sums and let the difference be derived. Derived here once, so the bounds can be nailed to it:

```
  $    231,438,735.86   money performed in the county   (place of performance)
- $    171,641,950.76   money reaching Native entities  (recipient county)
= $     59,796,785.10
```

It is **a ceiling, not an estimate**, and it is not a finding until every one of these is read with it:

1. **The Native sum is a floor.** It counts only recipients Cedar has attributed. Attribution is name and UEI matching; it misses and never invents. Better matching moves the Native sum up and the difference down, never the other way, so the number above is a CEILING on the money that did not reach Native entities.
2. **The two sums do not partition the same rows.** A recipient headquartered outside the county can perform work inside it, and one inside it can perform work elsewhere - ADR-015 rule 3 names this directly. The context row is there so the gap between the county's POP total ($231,438,735.86, 443 rows) and its recipient total ($171,641,950.76, 146 rows) is visible rather than implied.
3. **A county is not a reservation (ADR-015 rule 2).** Reservations span counties and counties contain fractions of reservations, so this is a county-level APPROXIMATION of an area whose real boundary is elsewhere. The AIANNH list above is itself a floor - observed from geocoded points Cedar happens to hold, not a census of overlap, because county polygons are not on disk to intersect against.
4. **Obligations are signed.** A deobligation is a negative row, so a county's Native sum can exceed its all-recipient sum with nothing wrong. Only the ROW COUNTS are guaranteed to nest.
5. **Coverage, dataset-wide.** 609,891 rows carrying $182,043,929,833.49 have NO place-of-performance county key and sit in no county's POP sum; 38,854 rows carrying $5,180,787,170.33 have no recipient county key, of which 30,870 rows / $4,441,208,294.92 are Native-attributed. Unallocated is not zero.
6. **Universe.** NATIVE-CANDIDATE CORPUS, NOT THE FEDERAL UNIVERSE. Same caveat as prime_contracts.csv. Also overlaps FAADS at FY2007 - see the FY2007 seam in MONEY_TOTALLING_RULES.md.
7. **Never sum across datasets.** ADR-015 rule 4: a shared county code is not permission to add this dataset's money to another's. MONEY_TOTALLING_RULES.md governs.

## The same county, in every dataset that reaches it

Read down this table, never across it. The three rows are three different universes over three different periods and adding them would be the exact error ADR-015 rule 4 and `MONEY_TOTALLING_RULES.md` forbid.

| dataset | period | POP sum | POP rows | POP exact | Native sum | Native rows | all-recipient sum | all-recipient rows |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `faads_transactions_all_agencies.csv` | FY2001-2007 | $16,763,334 | 156 | 100% | $0 | 0 | $35,734,621 | 311 |
| `prime_contracts.csv` | FY1979-2026 | $2,726,443 | 77 | 68% | $1,822,352 | 73 | $2,231,727 | 116 |
| `federal_funding_transactions.csv` | FY2007-2026 | $231,438,736 | 443 | 100% | $171,641,951 | 145 | $171,641,951 | 146 |

The universe note for each is in the CSV, on every row. The FAADS row is the only one whose POP sum is a true 'all federal money to this area' figure; the other two are Native-candidate corpora and their POP sums are corpus-scoped.

## Every cell that passed the coverage bar

| dataset | county | state FIPS | POP sum | POP rows | Native sum | Native rows | AIANNH observed |
|---|---|---|---:|---:|---:|---:|---|
| `federal_funding_transactions` | ROOSEVELT | 30 | $231,438,736 | 443 | $171,641,951 | 145 | 1250R |
| `federal_funding_transactions` | NEW LONDON | 09 | $28,398,961 | 181 | $18,550,276 | 204 | 2145R;2320R |
| `prime_contracts` | FREDERICKSBURG (CITY) | 51 | $97,719,319 | 313 | $418,513,631 | 889 | none |
| `prime_contracts` | MANASSAS (CITY) | 51 | $255,102,279 | 340 | $279,245,866 | 628 | none |
| `prime_contracts` | ESSEX | 34 | $219,105,155 | 42,103 | $91,766,364 | 38,821 | none |

## Whole-dataset totals these cells partition

| dataset | rows | obligations | Native rows | Native obligations | counties touched |
|---|---:|---:|---:|---:|---:|
| `faads_transactions_all_agencies.csv` | 2,769,748 | $1,830,639,317,707.66 | 29,594 | $4,721,685,550.00 | 3,501 |
| `prime_contracts.csv` | 1,217,768 | $310,005,258,661.21 | 888,862 | $244,765,639,853.72 | 2,249 |
| `federal_funding_transactions.csv` | 701,955 | $219,689,020,478.59 | 550,937 | $169,072,556,167.99 | 2,035 |

The FAADS row-ordinal join underpinning its Native side was re-proved this run on **29,594 of 29,594** attributed rows - recipient name, fiscal year and obligation all matching to the cent.

Invariants I1 and I2 prove, to the cent and to the row, that the per-county sums plus the unallocated residual equal each dataset's own total, on both the place-of-performance and the recipient side. If that ever stops being true, `verify` exits 1.
