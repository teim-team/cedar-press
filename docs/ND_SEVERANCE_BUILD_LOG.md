# North Dakota / Fort Berthold severance tax - build log

*Built 2026-08-07 by `code/113_build_nd_severance.py`. Output: appended SEVERANCE rows in `data/clean/tribal_tax_bases.csv`, `data/clean/nd_severance_allocation.csv`, `review/nd_severance_unresolved_2026-08-07.csv`, raw under `data/raw/external/nd_severance/` with `_SOURCE_MANIFEST.csv` and md5s.*

---

## The finding: the blend cannot be decomposed, and it does not have to be

North Dakota's 80/20 trust split governs **only wells on which drilling first commenced after 2019-06-30**, and NDCC 57-51.2-02(6) binds a well to the terms in force when it was drilled **for the life of the well**. So every monthly payment after mid-2019 is a blend of two regimes, and the weights - the spud-date mix of producing wells - are published by nobody.

**They do not need to be.** The North Dakota Legislative Council publishes, monthly, *both legs of the ratio*: gross production and oil extraction tax collections "in each county and the Fort Berthold Reservation", and "oil and gas tax revenue collections allocated to the Three Affiliated Tribes". The effective blended share is therefore **measured, not assumed**.

| Biennium | Months | FB gross production tax | FB oil extraction tax | Allocated to the tribe | of which straddle | **Measured on-reservation share** |
|---|---:|---:|---:|---:|---:|---:|
| 2013-15 (August 2014 - July 2015) | 12 | $200,495,439 | $213,462,256 | $206,981,621 | $0 | **50.00%** |
| 2015-17 (August 2016 - July 2017) | 12 | $122,299,024 | $117,841,918 | $120,071,481 | $0 | **50.00%** |
| 2017-19 | 24 | $460,061,035 | $447,343,823 | $453,699,550 | $0 | **50.00%** |
| 2019-21 | 24 | $419,211,284 | $400,061,890 | $419,460,520 | $0 | **51.20%** |
| 2021-23 | 24 | $637,631,817 | $638,786,727 | $688,468,099 | $9,770,257 | **53.17%** |
| 2023-25 | 24 | $461,794,876 | $409,509,301 | $480,949,712 | $9,226,760 | **54.14%** |
| 2025-27 to date (August 2025 - July 2026) | 12 | $164,096,368 | $139,856,156 | $172,101,092 | $3,480,698 | **55.48%** |

Two things in that table are load-bearing.

**The 2015-17 and 2017-19 shares are 50.00%.** That is the uniform 2013 regime - 50/50 on trust and fee alike - reproducing itself to four significant figures out of two independently published series. It is what validates the Fort Berthold collections row as the correct denominator for the tribal allocation row. Neither figure was adjusted to meet the other.

**The share then rises and keeps rising.** That is post-2019 wells replacing pre-2019 ones inside a payment series that looks like one number. A subscriber who picked up 80/20 and multiplied would be wrong by a factor that changes every month.

The rise also **forces a bound on the vintage mix**. The pre-2019 regime pays 50% of collections whatever the land status; the post-2019 regime pays at most 80%. So `post_2019_share >= (observed - 0.50) / 0.30`, and that inequality is written onto every monthly allocation row that exceeds 50%. It is a floor on how much of Fort Berthold production now comes from wells spudded after mid-2019 - recovered from two published dollar figures and no assumptions.

---

## Allocation periods recovered, with their statutes

| Row | Period | Wells it governs | Trust (tribe/state) | Fee (tribe/state) | Authority |
|---|---|---|---|---|---|
| ND-ALLOC-001 | 2007-07-01 .. 2013-06-30 | No vintage rule in the enacted allocation itself: the split turns on t | 0.50/0.50 | 0.20/0.80 | 2007 ND Session Laws ch. 545 (SB 2419), 60th Legislative Assembly, ena |
| ND-ALLOC-002 | 2013-07-01 .. 2019-06-30 | None | 0.50/0.50 | 0.50/0.50 | 2013 ND Session Laws ch. 473 (HB 1198), 63rd Legislative Assembly, ame |
| ND-ALLOC-003 | 2019-07-01 .. in force | WELLS ON WHICH DRILLING FIRST COMMENCED ON OR BEFORE 2019-06-30 | 0.50/0.50 | 0.50/0.50 | NDCC 57-51.2-02(6); 2019 ND Session Laws ch. 506 (SB 2312) sec. 5 APPL |
| ND-ALLOC-004 | 2019-07-01 .. in force | WELLS ON WHICH DRILLING FIRST COMMENCED AFTER 2019-06-30 ONLY | 0.80/0.20 | 0.20/0.80 | 2019 ND Session Laws ch. 506 (SB 2312), 66th Legislative Assembly, ame |
| ND-ALLOC-005 | 2021-09-01 .. in force | STRADDLE WELLS - wells located OUTSIDE the reservation with one or mor | 0.50/0.50 | 0.50/0.50 | NDCC 57-51.1-07.10(2)(a)-(b), enacted 2021 (SB 2319), applying to coll |
| ND-ALLOC-006 | 2021-09-01 .. in force | STRADDLE WELLS drilled ON OR AFTER 2019-07-01 | 0.80/0.20 | 0.20/0.80 | NDCC 57-51.1-07.10(2)(c)-(d), enacted 2021 (SB 2319), applying to coll |
| ND-ALLOC-000 | - .. 2007-06-30 | No allocation | *(blank by design)* | *(blank by design)* | NDCC 57-51.2-01 (authority to enter agreements) |

`ND-ALLOC-003` and `ND-ALLOC-004` are **both in force today**, which is the whole point. `ND-ALLOC-002` therefore carries `superseded_by = ND-ALLOC-004` and a note that it was superseded **for new production only**: the 2013 split still governs every well drilled before 2019-07-01 and will until those wells stop producing. Reading `superseded_by` as an end date is the error this file exists to prevent.

`ND-ALLOC-000` carries **blank share columns on purpose**. Chapter 57-51.2 did not exist before 2007 and no distribution exists before September 2008. Carrying a later formula backwards would have manufactured an allocation.

---

## Why no point base is published anywhere in this build

`derived_taxable_base` is **empty on every row**. Three independent blockers, each written onto the row in `bound_basis` with its arithmetic:

**1. The gross production tax pools two incompatible units.** Oil is five percent of gross value at the well (NDCC 57-51-02, base in USD). Gas is an annually indexed rate per mcf (NDCC 57-51-02.2, base in MCF) - $.0405 in FY2022, $.1423 in FY2024, $.0655 in FY2027. One published dollar figure, two bases, two units, and no oil/gas split of Fort Berthold collections anywhere. Dividing it produces neither dollars nor mcf. **This is a fourth distinct way a rate inversion fails**, after the marginal base, the graduated schedule read as flat, and receipts lagging obligations.

**2. The oil extraction rate on the reservation is state-contingent.** It is five percent, but NDCC 57-51.1-02(2) raises it to six whenever WTI exceeds an indexed trigger price for three consecutive months - and the 2023 session removed that trigger for every other North Dakota well while keeping it for reservation and straddle wells. Trigger prices retrieved: $89.65 (CY2021), $117.20 (CY2026). No notice stating the rate actually in force in any month was found, so each month carries `[collections/0.06, collections/0.05]` and is never divided once.

**3. The agreement is not published.** NDCC 57-51.2-02(3) caps the trust-land extraction rate at six and one-half percent "but may be reduced through negotiation", and 57-51.2-02(4) turns the chapters' exemptions off on the reservation "except as otherwise provided in the agreement". Four agreements are described by the Legislative Council - signed 2008-06-10, 2010-01-13, 2013-06-21 and 2019-02-28, the last effective 2019-03-29 - and **the text of none of them was found** on ndlegis.gov, tax.nd.gov, treasurer.nd.gov or governor.nd.gov. Every rate here is therefore the statutory rate, and any exempt or reduced-rate barrel makes collections/rate a **lower** bound on gross value at the well.

The one place the blend does narrow to something tight is the **straddle-well distribution**, because both vintages are multiplied by the *same* annually certified acreage ratios:

- **FY2025** (Fort Berthold Indian Reservation, July 1, 2024 - June 30, 2025): trust ratio 0.1570093, non-trust ratio 0.2298095 -> effective share of certified straddle-well taxes lies in [0.1715693, 0.1934094], about 12.7% wide.
- **FY2026** (Fort Berthold Indian Reservation, July 1, 2025 - June 30, 2026): trust ratio 0.1615461, non-trust ratio 0.2294837 -> effective share of certified straddle-well taxes lies in [0.1751336, 0.1955149], about 11.6% wide.

---

## What North Dakota publishes, and what it structurally does not

| | |
|---|---|
| **PUBLISHES** | Monthly tribal distributions by tax type, per tribe, via the State Treasurer's tax distribution search (`searchtype=tribe`, an undocumented mode on the public app). |
| **PUBLISHES** | Monthly **total gross production and oil extraction tax collections on the Fort Berthold Reservation** - the denominator - in the Legislative Council's oil and gas tax revenue collections and allocations detail reports. |
| **PUBLISHES** | The full statutory rate history, the annual per-mcf gas rate table back to 1991, the annual oil trigger price, the straddle-well acreage ratio certifications, and pool codes that name the four categories the Tax Commissioner actually accounts in: Fort Berthold Trust / Fee, Pre 2019 / post. |
| **DOES NOT PUBLISH** | **Collections by pool code.** The pool codes prove the state books trust-vs-fee and pre-vs-post-2019 separately for every formation on the reservation. The money against those codes is never published, and that single file would decompose the blend completely. |
| **DOES NOT PUBLISH** | Anything per well. Schedule T-84 makes each operator report a trust/non-trust allocation per well; the filings are confidential taxpayer data. |
| **DOES NOT PUBLISH** | The agreements themselves. |
| **DOES NOT PUBLISH** | Any reservation aggregate or ownership field at DMR. Its free statistics are by county, formation and statewide only; the complete Well Index carrying spud dates is subscription-gated. Even with per-well spud dates the vintage weights would need per-well tax collections, which are confidential. **The mix is unreachable from public sources in principle, not just in practice.** |

---

## Three tribes with no oil agreement, measured rather than assumed

NDCC 57-51.2-01 authorises oil and gas tax agreements with **three** tribes - Three Affiliated, Standing Rock and Turtle Mountain. All four tribes in the Treasurer's own list were queried against all three oil distribution types:

| Tribe | Oil Extraction | Gross Production | Straddle Well |
|---|---|---|---|
| Three Affiliated Tribes | 215 payments | 215 payments | 59 payments |

> **CORRECTED 2026-08-08.** This row previously printed **$0.00** for all three
> series. That was a LOG defect, not a data defect: `parse_stn`'s loop is bounded
> `i < len(L)-3` and never reaches the trailing `Grand Total:` line, so every
> total rendered as zero. **The CSV rows were always correct.** Verified from
> `tribal_tax_bases.csv`: 134 `REPORTED_TAX_REMITTANCE_PER_TRIBE` rows totalling
> **$2,886,139,700.00** to the Three Affiliated Tribes, against
> **$5,525,xxx,xxx** of `REPORTED_TAX_COLLECTIONS_ON_RESERVATION`. Anyone who
> read the $0.00 as a finding should re-read it as a rendering bug.

| Standing Rock Sioux Tribe | **no records** | **no records** | **no records** |
| Spirit Lake Tribe | **no records** | **no records** | **no records** |
| Turtle Mtn. Chippewa | **no records** | **no records** | **no records** |

`no records` here is the application answering, not a search failing - which makes it a **measured absence** and not a `NOT_CHECKED`.

---

## Cross-source verification

The Legislative Council's monthly "allocated to the Three Affiliated Tribes" figure and the sum of the State Treasurer's three distribution types **agree to the dollar** on every month checked - two agencies, two publication routes, one number. Under `docs/CROSS_SOURCE_VERIFICATION.md` that is a verification, not a claim.

It also settles a scope question: the LC allocation figure **includes** the straddle-well distribution, whose collections sit in the *county* rows rather than the Fort Berthold row. Straddle money is therefore netted out of the numerator before any effective share is computed, on every row that has it.

---

## Rows added

- `RATE_ONLY_NO_AMOUNT` - 24
- `REPORTED_TAX_COLLECTIONS_ON_RESERVATION` - 268
- `REPORTED_TAX_REMITTANCE_PER_TRIBE` - 134
- **total 426 `SEVERANCE` rows**, against zero before this build.

`derived_taxable_base` is populated on **none** of them, for the three reasons above. That is the same outcome as the California gaming build reached after reading its own quotes: the bound machinery works, and the honest answer is a range.

## Unresolved, staged for a ruling

- **ND-TREASURER-TRIBE-UNRESOLVED::Turtle Mtn. Chippewa** (`ENTITY_NOT_RESOLVED`) - The ND Treasurer's own label 'Turtle Mtn. Chippewa' does not resolve against the spine. No dollar is keyed to it in this build - the Treasurer returns no oil distribution for this tribe - so nothing is at risk, but the label will block a later fuel or tobacco build off the same application.
- **ND-SEVERANCE-AGREEMENT-TEXT-NOT-PUBLISHED** (`SOURCE_WITHHELD_OR_UNPUBLISHED`) - The four state-tribal oil and gas tax agreements (2008-06-10, 2010-01-13, 2013-06-21, 2019-02-28) are described by the Legislative Council but their text was not found on ndlegis.gov, tax.nd.gov, treasurer.nd.gov or governor.nd.gov. NDCC 57-51.2-02(3) lets the agreement set the trust-land oil extraction rate below the statutory cap and 57-51.2-02(4) turns the chapters' exemptions off on the reservation 'except as otherwise provided in the agreement', so the agreement is the only document that could close the rate question.
- **ND-OET-TRIGGER-RATE-IN-FORCE-UNKNOWN** (`RATE_NOT_UNIQUELY_DETERMINED`) - NDCC 57-51.1-02(2) raises the reservation oil extraction rate from 5% to 6% after three consecutive months above an indexed WTI trigger price. Trigger prices retrieved: $89.65 (CY2021), $117.20 (CY2026). Tax Commissioner notices for CY2022-CY2025 were probed at the same URL pattern and are not published there.
- **ND-FB-COLLECTIONS-PRE-AUG-2013** (`OUR_COVERAGE_GAP`) - Fort Berthold collections are published back to August 2011 in LC# 13.9128, but that report prints three sub-columns per month (gross production, extraction, total) in a layout this parser does not read safely. Aug 2013 - Jul 2014 and Aug 2015 - Jul 2016 are published only as twelve-month cumulative totals in the reports retrieved.
- **ND-TREASURER-PUBLISHES-FOUR-MORE-TRIBAL-TAX-TYPES** (`HIGH_VALUE_LEAD_OUT_OF_SCOPE`) - The same ND Treasurer application publishes per-tribe monthly amounts for Tribal Highway Tax (motor fuel), Tribal Cigarette, Tribal Sales Tax and Tribal Alcohol, for four tribes: Standing Rock, Spirit Lake, Three Affiliated and Turtle Mountain. Measured 2026-08-07: highway tax 902 payments across four tribes ($53.4M total, from 2005-01), cigarette 258 payments (Standing Rock, $1.59M), sales tax 22 payments (Standing Rock, 2016-09 to 2019-03, $0.62M), alcohol 7 payments (Three Affiliated, $0.46M). docs/TRIBAL_TAX_BUILD_LOG.md records that NO tribe in the dataset carries a per-tribe non-gaming tax amount. North Dakota publishes them.
- **ND-NO-OIL-AGREEMENT-FOR-THREE-OTHER-TRIBES** (`MEASURED_ABSENCE`) - NDCC 57-51.2-01 authorises oil and gas tax agreements with the Three Affiliated Tribes, the Standing Rock Sioux Tribe and the Turtle Mountain Band of Chippewa Indians. Queried 2026-08-07 for all four tribes in the Treasurer's list against all three oil distribution types: only Three Affiliated Tribes returns records. Standing Rock, Spirit Lake and Turtle Mountain return 'No records found' and a $0.00 grand total.
- **SERIES-BREAK-ND-2019-NEEDS-THE-MEASURED-SHARE** (`DOWNSTREAM_UPDATE_OWED`) - `data/clean/series_breaks.csv` carries a resource_revenue / allocation_formula break at 2019-06-30 whose effect_on_series ends 'The published distribution does not decompose by vintage and Cedar Press does not model the mix.' That is still true of the VINTAGE mix, but the EFFECTIVE SHARE is now measured monthly against the Legislative Council's Fort Berthold collections - 50.00% through mid-2019, 55.48% in the 2025-27 biennium to date. The break entry should say so rather than leaving a reader with no number at all.
- **ND-DMR-CANNOT-SUPPLY-WELL-VINTAGE-MIX** (`SOURCE_STRUCTURALLY_SILENT`) - ND DMR's free statistics are by county, formation and statewide. Probed 2026-08-07: the statistics index offers monthly production by county, historical monthly oil/gas statistics, annual and cumulative production by formation, and drilling statistics. There is NO reservation aggregate and no trust/fee field. The complete Well Index carrying spud dates is subscription-gated. Even with per-well spud dates, per-well tax collections are confidential taxpayer data, so the vintage weights cannot be reconstructed from public sources at all.
