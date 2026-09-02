# North Dakota per-tribe non-gaming tax distributions - build log

*Built 2026-08-07 by `code/116_build_nd_tribal_taxes.py`. Output: appended `MOTOR_FUEL`, `TOBACCO`, `RETAIL_SALES` and `ALCOHOL` rows in `data/clean/tribal_tax_bases.csv`, a codebook fragment at `data/clean/codebook/15_tribal_tax.csv`, `review/nd_tribal_tax_unresolved_2026-08-07.csv`, raw under `data/raw/external/nd_tribal_tax/` with `_SOURCE_MANIFEST.csv` and md5s.*

---

## The finding: this is the first per-tribe non-gaming tax money in the dataset, and it arrives with both legs of the division

`docs/TRIBAL_TAX_BUILD_LOG.md` recorded that **no tribe carried a per-tribe non-gaming tax amount** and that the netting machinery was "built, tested and idle". Four North Dakota tribes now carry one. Washington holds the fullest fuel-agreement roster in the country and **may not publish** the per-tribe figures - its report says so in its own words. North Dakota does not withhold them.

More than that: for motor fuel the North Dakota Legislative Council prints, in a single paragraph, **the statutory rate and the per-tribe allocation percentage**. A distribution is a share of collections, so a base needs two divisions and two quoted rates:

```
payment / tribal_allocation_share = tax collected inside the reservation
tax collected / statutory_rate    = the taxable base
```

That is the first time both have been available together anywhere in this dataset.

---

## What the ND Treasurer publishes, per tribe

| Tribe | Tax type | Payments | Total | First | Last |
|---|---|---:|---:|---|---|
| Spirit Lake Tribe | Tribal Highway Tax | 231 | $4,514,876.41 | 2007-02-14 | 2026-07-15 |
| Standing Rock Sioux Tribe | Tribal Cigarette | 258 | $1,587,520.47 | 2005-01-14 | 2026-07-15 |
| Standing Rock Sioux Tribe | Tribal Highway Tax | 259 | $7,443,990.88 | 2005-01-14 | 2026-07-15 |
| Standing Rock Sioux Tribe | Tribal Sales Tax | 22 | $623,674.24 | 2016-09-15 | 2019-03-14 |
| Three Affiliated Tribes | Tribal Alcohol | 7 | $456,233.08 | 2025-01-15 | 2026-07-15 |
| Three Affiliated Tribes | Tribal Highway Tax | 223 | $30,553,775.69 | 2008-01-15 | 2026-07-15 |
| Turtle Mtn. Chippewa | Tribal Highway Tax | 189 | $10,852,365.04 | 2010-11-15 | 2026-07-15 |

Each tribe's listing was read whole and **footed against the application's own printed Grand Total** before any row was written:

| Tribe | Payments in listing | Rows sum to | Printed Grand Total |
|---|---:|---:|---:|
| Standing Rock Sioux Tribe | 560 | $9,693,290.26 | $9,693,290.26 |
| Spirit Lake Tribe | 231 | $4,514,876.41 | $4,514,876.41 |
| Three Affiliated Tribes | 719 | $3,156,463,118.33 | $3,156,463,118.33 |
| Turtle Mtn. Chippewa | 189 | $10,852,365.04 | $10,852,365.04 |

---

## Only one of the four taxes derives a base, and it derives a VOLUME

| Tax | Sharing rate published? | Statutory rate a single number? | Base derived |
|---|---|---|---|
| **MOTOR_FUEL** | yes, per tribe | yes - 23 cents per gallon under **both** NDCC 57-43.1-02(1) and 57-43.2-02(1) | **GALLONS** |
| TOBACCO | yes, 87% less 1% | **no** - 22 mills per cigarette, 28% of wholesale price on cigars and pipe tobacco, 60c and 16c per ounce on snuff and chewing tobacco | none |
| RETAIL_SALES | yes, 80/20 | **no** - five rates in one agreement (5%, 3%, 7%, 3%, plus .25% tribal local) | none |
| ALCOHOL | yes, 80/20 | **no** - a six-tier per-gallon schedule, possibly pooled with a 7% ad valorem tax | none |

The single derivation:

```
payment / tribal share (0.86, 0.75, 0.69 or 0.95) = fuel tax collected
fuel tax collected / $0.23 per gallon             = GALLONS
```

**It is a volume. It is not a dollar figure and must never be read as one.** It is also a **lower bound**: NDCC 57-43.2-03(1) taxes propane at two percent of value and dyed diesel at four cents rather than 23, and NDCC 57-43.1-03.2(1) refunds fuel tax to individual enrolled members buying on their own reservation. Both leaks push the true gallon count **up**, never down.

### The one percent administration fee is a percentage POINT

The source says *87 percent, less a 1 percent administration fee* to the tribe and *thirteen percent, plus the 1 percent administration fee* to the general fund. Those two legs sum to exactly 100 percent only if the fee is one percentage **point** off the tribe's share - 86 and 14, not 86.13 and 13.87. **The source's own second sentence forces the reading**, and it forces it identically for all four tribes.

| Tribe | Agreement effective | Allocation stated | Tribal share used |
|---|---|---|---:|
| Standing Rock Sioux Tribe | 1999-01-01 | 87% less 1% | **0.86** (from 2015-05-01) |
| Spirit Lake Tribe | 2006-09-01 | 76% less 1% | **0.75** (from 2006-09-01) |
| Three Affiliated Tribes | 2007-09-01 | 70% less 1% | **0.69** (from 2007-09-01) |
| Turtle Mtn. Chippewa | 2010-09-01 | 96% less 1% | **0.95** (from 2010-09-01) |

Standing Rock is the exception and it costs rows. Its agreement became effective **1999-01-01** and the Legislative Council states an allocation only for the agreement **renegotiated 2015-05-01**. Carrying the 2015 percentage backwards would be an assumption, so no Standing Rock fuel payment before 2015-05-01 is divided - it keeps the amount and the per-gallon rate and gets no base. One division of two is not a base.

Derived rows by tribe:

| Tribe | Payments | of which derive a base |
|---|---:|---:|
| Spirit Lake Tribe | 231 | 231 |
| Standing Rock Sioux Tribe | 259 | 135 |
| Three Affiliated Tribes | 223 | 223 |
| Turtle Mtn. Chippewa | 189 | 189 |

---

## The four documented failure modes, checked on all four taxes

| Failure mode | Fired? | Where |
|---|---|---|
| **Marginal base** ("in excess of") | no | both fuel statutes read "on **all** motor vehicle fuel sold or used in this state"; the allocations are flat shares |
| **Graduated schedule read as flat** | **yes, three times** | tobacco (four bases), sales (five rates), alcohol (six per-gallon tiers) |
| **Receipts lag obligations** | **yes** | the Treasurer publishes a payment date only. Standing Rock's sales tax is the live case: state administration was discontinued **2017-03-07** and payments continue to **2019-03-14** |
| **Mixed units in one figure** | **yes** | "Tribal Alcohol" can pool a per-wine-gallon wholesale tax with a seven percent ad valorem gross receipts tax - NDCC 57-39.10-07 and -09 pay both out of the same tribal allocation fund |

A fifth complication, short of failure: **the tobacco products wholesale allocation in NDCC 57-39.10-04(4) is still a PER-CAPITA FORMULA** - enrolled membership times state revenue per capita. That is the same shape as Washington's per-capita fuel agreements, which `derive_base()` already refuses in code. The 2023 session replaced the per-capita method for **alcohol only**; the alcohol series begins 2025-01-15 and so falls entirely under the 80/20 method that replaced it.

---

## Measured absences

| Tribe | Tax type with no distribution |
|---|---|
| Standing Rock Sioux Tribe | Tribal Alcohol |
| Spirit Lake Tribe | Tribal Alcohol |
| Spirit Lake Tribe | Tribal Sales Tax |
| Spirit Lake Tribe | Tribal Cigarette |
| Three Affiliated Tribes | Tribal Sales Tax |
| Three Affiliated Tribes | Tribal Cigarette |
| Turtle Mtn. Chippewa | Tribal Alcohol |
| Turtle Mtn. Chippewa | Tribal Sales Tax |
| Turtle Mtn. Chippewa | Tribal Cigarette |

These are **measured**, not blank. Each tribe's complete listing foots to the application's own Grand Total and contains no payment of that type.

**They were NOT measured by per-type queries, and that matters.** The application validates its `DistType` parameter against an unpublished code list and answers an unknown code with **"Unable to Process"** - an application error, not an empty result. Seven candidate codes were probed and every one errored. A per-type sweep would have produced false absences indistinguishable from real ones. This is the same class as South Dakota's broken search: a site's own navigation failing is a fact about the navigation.

Tribe ids 5 and 6 were probed for the same reason and answered `{'5': 'UNABLE', '6': 'UNABLE'}`. The application **errors** outside its own list rather than returning nothing, which is what closes the list at four - while **NDCC 57-39.9-01 and 57-39.10-01 each name five tribes**. Sisseton-Wahpeton Oyate is authorised by statute and absent from the Treasurer's tribe list.

---

## Measured and deliberately NOT published

| Tribe | Distribution type | Payments | Total | Range | Why not published |
|---|---|---:|---:|---|---|
| Standing Rock Sioux Tribe | County Sales Tax | 21 | $38,104.67 | 2016-09-22 .. 2021-10-21 | no authorising instrument retrieved |

Rule 4 forbids publishing a tribal tax figure whose authority is unstated, and *"County Sales Tax"* paid to a tribe is exactly the kind of number that invites a wrong reading in either direction. It is measured here, staged in `review/`, and kept out of the CSV until the instrument is found.

---

## Entity resolution

| Treasurer label | Spine id | How |
|---|---|---|
| Standing Rock Sioux Tribe | TRBF-STNDRK-00 | containment |
| Spirit Lake Tribe | TRBF-SPRTLK-00 | core |
| Three Affiliated Tribes | TRBF-MHATAT-00 | core |
| Turtle Mtn. Chippewa | TRBF-TURTLM-00 | hand_ruling_via[containment] |

**"Turtle Mtn. Chippewa" is the one hand ruling in this build, and it was worth making rather than refusing** - it keys 189 motor fuel payments worth $10.85M that would otherwise have been dropped. It does not rest on the matcher. The Legislative Council names the agreement party in full - *"The Turtle Mountain Band of Chippewa Indians, which became effective September 1, 2010"* - and the Treasurer's first Turtle Mountain distribution is 2010-11-15. Two guards run at build time and both must hold or the build refuses to key a dollar: the Legislative Council's full name must resolve to the same id through the shared resolver, and **exactly one** federally recognised tribe in North Dakota may carry the name. That is a uniqueness test, not a similarity score. The alias is staged for the spine so no later build re-rules it.

---

## Netting: still zero North Dakota tribes, and the blocker has MOVED

This build supplies the input the subtraction method was waiting for - per-tribe non-gaming money, for four tribes, over twenty-one years. It still cannot net a single North Dakota tribe, and the reason is now the **other operand**.

**North Dakota seals every tribal gaming record by statute.** `data/clean/state_gaming_observations.csv` carries `SG-ND-00001`, a documented absence quoting *N.D.C.C. 54-58-02, "Tribal gaming records not subject to disclosure"*, flagged `held_by_state_but_sealed`. `gaming_revenue_bounds.csv` holds **zero** North Dakota rows. There is no whole-tribe or gaming revenue figure for any ND tribe anywhere in this dataset to subtract from.

So the honest count is:

- **4 of 4** tribes in the Treasurer's list now carry per-tribe non-gaming tax money.
- **1** tribe - the Three Affiliated Tribes - carries **two** separately taxed categories here (motor fuel and alcohol) plus the severance series from script 113, so it is the best-covered subtrahend in the dataset.
- **0** tribes have a whole-tribe revenue figure to net it out of.

The minuend has to come from a **tribal** source - an audited financial statement, a bond official statement, a tribal annual report - because North Dakota will not supply it. That is a different research task from the one this build closed, and naming it precisely is worth more than the rows.

---

## Rows added

| tax_type | measurement_status | rows |
|---|---|---:|
| ALCOHOL | AGREEMENT_ROSTER_NO_AMOUNT | 1 |
| ALCOHOL | MEASURED_ABSENCE_NO_DISTRIBUTION | 3 |
| ALCOHOL | RATE_ONLY_NO_AMOUNT | 2 |
| ALCOHOL | REPORTED_TAX_REMITTANCE_PER_TRIBE | 7 |
| MOTOR_FUEL | AGREEMENT_ROSTER_NO_AMOUNT | 5 |
| MOTOR_FUEL | DERIVED_TAXABLE_BASE | 778 |
| MOTOR_FUEL | RATE_ONLY_NO_AMOUNT | 2 |
| MOTOR_FUEL | REPORTED_TAX_REMITTANCE_PER_TRIBE | 124 |
| RETAIL_SALES | AGREEMENT_ROSTER_NO_AMOUNT | 1 |
| RETAIL_SALES | MEASURED_ABSENCE_NO_DISTRIBUTION | 3 |
| RETAIL_SALES | RATE_ONLY_NO_AMOUNT | 1 |
| RETAIL_SALES | REPORTED_TAX_REMITTANCE_PER_TRIBE | 22 |
| TOBACCO | AGREEMENT_ROSTER_NO_AMOUNT | 2 |
| TOBACCO | MEASURED_ABSENCE_NO_DISTRIBUTION | 3 |
| TOBACCO | RATE_ONLY_NO_AMOUNT | 2 |
| TOBACCO | REPORTED_TAX_REMITTANCE_PER_TRIBE | 258 |

**Total 1214 rows.** `derived_taxable_base` is populated on 778 of them, all MOTOR_FUEL, all in gallons.

## Unresolved, staged for a ruling

- **ND-TREASURER-ALIAS-RULED::Turtle Mtn. Chippewa** (`ALIAS_RULED_IN_SCRIPT_NOT_IN_SPINE`) - The ND Treasurer's label 'Turtle Mtn. Chippewa' does not resolve against the spine and was ruled to TRBF-TURTLM-00 in code/116_build_nd_tribal_taxes.py on published evidence, not by matching. North Dakota Legislative Council, Tribal and State Relations Committee background memorandum 27.9066.01000 (August 2025): 'The Turtle Mountain Band of Chippewa Indians, which became effective September 1, 2010, provides for a revenue allocation of 96 percent, less a 1 percent administration fee, to the tribe.' The Treasurer's first Turtle Mountain distribution is 2010-11-15. Two guards were applied and both hold: the Legislative Council's full name resolves to the same id through the shared resolver, and exactly one ND federally recognised tribe carries the name. This ruling now keys real money and belongs in the spine's alias list rather than in a build script.
- **ND-DISTRIBUTION-NOT-PUBLISHED::Standing Rock Sioux Tribe::County Sales Tax** (`AUTHORITY_NOT_ESTABLISHED`) - The ND Treasurer's tribe listing shows 21 'County Sales Tax' payments to Standing Rock Sioux Tribe totalling $38,104.67, 2016-09-22 to 2021-10-21. NO instrument authorising a county sales tax distribution to a tribe was retrieved from ndlegis.gov or tax.nd.gov. Rule 4 of docs/TRIBAL_TAX_DECOMPOSITION.md forbids publishing a tribal tax figure whose authority is unstated, so these rows are MEASURED AND NOT PUBLISHED.
- **ND-TRIBAL-TAX-AGREEMENT-TEXTS-NOT-PUBLISHED** (`SOURCE_WITHHELD_OR_UNPUBLISHED`) - Not one of the state-tribal fuel, cigarette, sales or alcohol agreement TEXTS was found on ndlegis.gov or tax.nd.gov. Every allocation percentage in this build comes from the Legislative Council's description of the agreements, not from the instruments. The same blocker was recorded for the oil and gas agreements by script 113, so it is now four tax types deep and is the single highest-value document request in the North Dakota work.
- **ND-STANDING-ROCK-FUEL-ALLOCATION-1999-2015-UNKNOWN** (`RATE_NOT_UNIQUELY_DETERMINED`) - The Standing Rock motor fuel agreement became effective 1999-01-01 and the Legislative Council states an allocation only for the agreement RENEGOTIATED 2015-05-01. Every Standing Rock fuel payment before 2015-05-01 therefore carries an amount and a per-gallon rate but no sharing rate, and no base is derived from it. The same gap applies to the 1993 cigarette agreement before its 2015-05-01 renegotiation.
- **ND-TRIBAL-ALCOHOL-WHICH-TAX-UNKNOWN** (`MIXED_UNITS_IN_ONE_FIGURE`) - The Treasurer's 'Tribal Alcohol' line does not say whether it is the alcoholic beverages WHOLESALE tax (NDCC 5-03-07, six per-gallon tiers), the alcoholic beverages GROSS RECEIPTS tax (NDCC 57-39.6-02, seven percent ad valorem), or both. NDCC 57-39.10-07 and -09 pay both from the same tribal allocation fund on the same quarterly cycle. If the Tax Commissioner confirms the line is gross receipts only, the base follows in one more division: payment / 0.80 / 0.07 = dollars of alcoholic beverage retail sales inside the reservation.
- **ND-TRIBAL-CIGARETTE-LINE-SCOPE-UNKNOWN** (`MIXED_UNITS_IN_ONE_FIGURE`) - The agreement is a 'cigarette and tobacco excise tax' agreement but the Treasurer's label is 'Tribal Cigarette'. If the line is cigarettes only, packs = payment / 0.86 / $0.44 and the arithmetic is already written onto every post-2015-05-01 row as an UPPER bound. If it pools cigars, pipe tobacco, snuff and chewing tobacco, no volume comes out of it at all.
- **ND-57-39.9-AUTHORISED-BUT-NO-DISTRIBUTION** (`MEASURED_ABSENCE`) - NDCC 57-39.9-01, enacted 2019, authorises state-tribal sales, use and gross receipts tax agreements with FIVE named tribes including Sisseton-Wahpeton Oyate. The Treasurer's complete listings for all four tribes in its own tribe list show NO sales tax distribution after 2019-03-14. The authority exists and nothing has flowed under it, at least to these four tribes.
- **ND-TREASURER-TRIBE-LIST-EXCLUDES-SISSETON-WAHPETON** (`SOURCE_COVERAGE_GAP`) - NDCC 57-39.9-01 and 57-39.10-01 each name FIVE tribes - Three Affiliated, Sisseton-Wahpeton Oyate of the Lake Traverse Reservation, Spirit Lake, Standing Rock and Turtle Mountain. The Treasurer's tribe list holds FOUR. Tribe ids 5 and 6 were probed and the application answered {'5': 'UNABLE', '6': 'UNABLE'} - 'Unable to Process' is an application error, not an empty result, so the list is closed at four rather than merely returning nothing for a fifth. Sisseton-Wahpeton's ND-side reservation area is therefore unrepresented in this series.
- **ND-STN-DISTTYPE-CODE-LIST-NOT-PUBLISHED** (`SOURCE_STRUCTURALLY_SILENT`) - The Treasurer application's DistType parameter is validated against an internal code list that is not exposed anywhere in the public interface - the search page serves only a county selector. Probed 2026-08-07 with 'TRIBAL HWY', 'TRIBAL HIGHWAY', 'TRIBAL CIG', 'TRIBAL CIGARETTE', 'TRIBAL SALES', 'TRIBAL ALCOHOL' and 'COUNTY SALES': every one returned 'Unable to Process'. A per-type absence sweep would therefore have produced false absences that looked exactly like real ones.
- **ND-113-BUILD-LOG-PRINTS-ZERO-FOR-1.5BN** (`DOWNSTREAM_DEFECT_IN_ANOTHER_BUILD`) - `parse_stn` in code/113_build_nd_severance.py scans for the trailing 'Grand Total:' line inside a loop bounded by `i < len(L) - 3`, so it never reaches it and always returns grand=None. docs/ND_SEVERANCE_BUILD_LOG.md consequently prints 'Three Affiliated Tribes | 215 payments, $0.00' for a series worth $1,587,965,950.39, and $0.00 for the extraction and straddle rows too. The CSV rows are unaffected - only the log's table is wrong. This build's parser scans the whole line list and uses the Grand Total as a footing check.
- **TRIBAL-TAX-BUILD-LOG-NETTING-SECTION-NOW-FALSE** (`DOWNSTREAM_UPDATE_OWED`) - `docs/TRIBAL_TAX_BUILD_LOG.md` (script 108) carries a section headed 'Netting readiness: zero tribes, and that is the honest number' whose second sentence reads 'No tribe in this dataset yet carries a per-tribe non-gaming tax amount'. That is now false: four North Dakota tribes do. Its 'Next targets' list also still ranks North Dakota first with SEVERANCE described as an empty tax type, which scripts 113 and 116 have both closed. The zero COUNT of nettable tribes happens to remain correct, but for a completely different reason - North Dakota seals tribal gaming records - so the sentence would mislead even where it lands on the right number.
- **ND-NETTING-BLOCKED-BY-SEALED-GAMING-RECORDS** (`OTHER_SIDE_OF_THE_SUBTRACTION_MISSING`) - Four North Dakota tribes now carry per-tribe non-gaming tax money, which is the input the netting method in docs/TRIBAL_TAX_DECOMPOSITION.md was waiting for. It still cannot run for a single ND tribe, and the blocker has MOVED to the other operand: North Dakota holds and seals every tribal gaming record under NDCC 54-58-02, recorded in data/clean/state_gaming_observations.csv as SG-ND-00001 with exclusion_flag 'held_by_state_but_sealed'. There is no whole-tribe or gaming revenue figure for any ND tribe anywhere in this dataset to subtract from, and gaming_revenue_bounds.csv holds zero ND rows.
