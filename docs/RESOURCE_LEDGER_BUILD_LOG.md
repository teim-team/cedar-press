# Native Natural Resources Ledger — build log

> **SUPERSEDED IN PART, 2026-09-01 (workstream O). Read
> `docs/datasets/natural_resources_sources.md` first** — it carries the
> permanent per-source COVERAGE table (upstream years vs held years) that this
> log does not.
>
> Three statements below are now wrong and are corrected there, not here:
>
> * **"MMS CY1925-1995 … outside the 2000-2026 target"** — built.
>   `Am_Ind_Coll.pdf` was already on disk; read by *coordinate* rather than by
>   line it yields **CY1925-CY2000, 315 rows, $4,088,925,436**, passing a
>   per-year cross-foot, a per-column printed total, and exact agreement with
>   this log's own hand transcription of CY1996-2000. The 2000-2026 target the
>   scoping decision rested on has been retired by the owner.
> * **"ONRR … 2003-01 .. 2026-06"** — refreshed to **2026-07**. And the two
>   grains no longer reconcile to $0.00: CY2024 differs by $25,202.49 and
>   CY2025 by $1,302.57, filed as `RESOURCE:ONRR:GRAIN_DISAGREEMENT`.
> * **"489 payments totalling $3,125,453,109.56"** (North Dakota) — now
>   **492 payments, $3,144,235,826.73**, through 2026-08-21.
>
> The reasoning in this log is why those numbers can be trusted. It is kept.


*Built 2026-08-06 by `code/83_build_resource_ledger.py`. Nothing on natural
resources existed in Cedar Press before this.*

Elijah, on gaming, and it governs here too:

> "id rather someone else estimate reveneu than us lol"

The temptation is sharper here than it was for gaming. ONRR publishes oil and
gas **volumes** from Native American land, and a price series is a web search
away. Multiply the two and you can print a number for what a tribe "should
have" earned. That number would be wrong, it would be quoted, and it would be
ours.

**Built:** 10,123 revenue events · 1994–2026 · 7 source systems · 1,096 party
links · 4 items held for review.

---

## What was refused, and why

| Refused | Why |
|---|---|
| `estimated_gross_production_value` | Volume × price is a model, not a measurement. Out of scope for publication. |
| `estimated_royalty` | A royalty rate we did not retrieve is a guess. |
| `modeled_amount` of any kind | Same. |
| Per-tribe splits of the federal aggregate | Interior releases Native American extraction and revenue information **only in aggregate, by law**. Dividing it by anything is fabrication. |
| Land status inferred from a map | A well inside a reservation boundary is not evidence of tribal mineral ownership. Trust versus fee is the whole question. |
| Applying North Dakota's 80/20 split to the post-2019 series | The 2019 split governs **only wells spudded after 2019-06-30**; earlier wells keep the old split for life. Every post-2019 payment is a blend, and we do not model the mix. |
| Describing Utah's fund deposits as tribal royalty income | Utah's own code says the fund "consists of state severance tax money to be spent at the discretion of the state" and "does not constitute a trust fund." |
| Utah Tax Commission severance-deposit figures | Column order shifts between report vintages; the extraction is ambiguous. Held rather than published wrong. |
| MMS FY1997 | Its own components miss its own printed subtotal by $10. Held by the reconciliation gate. |

---

## The label that matters most

ONRR's `Native American` land class is **revenue from Native American lands**.
It mixes tribal mineral interests with individual Indian (allottee) interests.
It is **not** "payments to tribal governments."

This is not an inference. Interior's own disbursement category is literally
named **"Native American tribes and individuals"**, and the portal's own
documentation describes allottee direct pay alongside tribal leases:

> "Individual mineral owners (allottees) may request that payments be made
> directly to them. The Bureau of Indian Affairs (BIA) approves or denies these
> direct pay requests. **The amounts paid for extraction on tribal lands vary by
> tribe and are not available to the public.**"
> — <https://revenuedata.doi.gov/how-revenue-works/native-american-revenue/>

Every federal row carries that caveat in `beneficiary_note`, and the codebook
repeats it.

---

## What got built

| Source system | Rows | Coverage | `measurement_status` |
|---|---:|---|---|
| `ONRR_NRRD_monthly_revenue` | 9,238 | 2003-01 .. 2026-06 | `reported_revenue` |
| `ND_State_Treasurer_tax_distribution_search` | 489 | 2008-09 .. 2026-07 | `actual_payment` |
| `ONRR_NRRD_fiscal_year_disbursements` | 157 | FY2003 .. FY2025 | `actual_payment` |
| `UT_COBI_fund_financials` | 118 | FY1996 .. FY2025 | `reported_revenue` / `actual_payment` |
| `MT_DOR_county_oil_gas_distribution` | 49 | 2014Q1 .. 2026Q1 | `actual_payment` |
| `MMS_MRM_american_indian_revenues` | 42 | FY1994 .. FY2001 | `reported_revenue` |
| `MMS_MRM_american_indian_revenues_calendar` | 30 | CY1996 .. CY2000 | `reported_revenue` |

Aggregation: 9,467 `national_aggregate`, 489 `entity_specific`, 167
`state_aggregate`. **These must not be summed together** — the national
aggregate already contains the tribe-specific money.

---

## 1. ONRR — the baseline

**Source.** Natural Resources Revenue Data portal, bulk downloads at
`https://revenuedata.doi.gov/downloads/<name>.csv`. Retrieved 2026-08-06. Raw
copies under `data/raw/resources/onrr/` — Cedar Press is self-contained, no
external runtime reads.

### Coverage: the prior report's "2022–2025" was wrong by nineteen years

A prior report claimed ONRR coverage of **2022–2025 only**. The measured range
is **January 2003 through June 2026**, and the portal states its own floor:

> "We offer revenue by month and year for **January 2003** through the most
> recently completed month."
> — `nrrd_downloads_revenue_page-data.json`, from
> `https://revenuedata.doi.gov/page-data/downloads/revenue/page-data.json`

### Geography suppression — verified, not taken on faith

The build performs this check every run and prints it:

```
GEOGRAPHY CHECK (measured, not assumed)
  Native rows carrying any geography : 0 of 9,238
  Federal rows carrying any geography: 400,597 of 401,348 (99.8%)
```

**`State`, `County`, `FIPS Code` and `Offshore Region` are blank on 100% of
Native American rows**, against 99.8% populated on Federal rows in the same
file. Same in `calendar_year_production.csv` (222/222 blank) and
`fiscal_year_disbursements.csv` (157/157 blank). The publisher says why:

> "For all Native American land, the federal government only releases natural
> resource extraction and revenue information in aggregate. Specific data on
> Native American revenues are confidential and proprietary. Treaties, laws,
> and regulations dictate what data the government can release."
> — <https://revenuedata.doi.gov/how-revenue-works/native-american-revenue/>

Consequence: every ONRR row is `national_aggregate` with **no** entity
resolved, and a row is filed to `review/resource_ledger_unresolved.csv`
recording that no attribution is possible — so an empty party set reads as a
property of the source rather than an unfinished join.

### Two grains, one published

ONRR publishes the same dollars monthly and by calendar year. The build
**reconciles them before dropping one** and reports the result:

```
GRAIN RECONCILIATION monthly vs calendar-year, 23 shared years:
  max abs difference $0.00
  monthly extends beyond the calendar-year file: ['2026']
```

Exact to the cent across all 23 shared years. The **monthly** grain is
published because it is strictly finer and reaches six months further forward;
the calendar-year file is retained as the check. Summing months to a calendar
year is safe, and the reconciliation is the evidence.

### Data oddities found

**Negatives are 19.0% of Native revenue rows.** 1,758 of 9,238 rows are
negative, summing to **−$1,075,020,365.16**; the largest single negative is
−$71,602,394.93 (2021-08, Royalties, Oil). These are refunds, recoupments and
prior-period corrections. Per `docs/DATA_ODDITIES.md` they are **retained and
belong in any total**. 348 rows (3.8%) are exactly zero — an assertion, not a
blank.

**The undisclosed disbursement split — the trap in this dataset.** Through
FY2014 `fiscal_year_disbursements.csv` carries exactly **one** Native row per
fiscal year. From **FY2015** it carries **11–15 rows per year identical in
every published column** — fiscal year, fund type, source, state, county —
differing only in amount. The dimension separating them (which tribe, which
account) has been suppressed along with the geography, leaving rows that look
like duplicates and are not.

> **A dedupe on the visible key would discard 134 rows and $10,789,042,639.73.**

Every row is kept with its own ordinal in `source_record_id`.

### `other_reported_revenue` is deliberately outside the enum

`Other revenues` (2,829 rows), `Civil penalties` and `Inspection fees` map to
`other_reported_revenue` rather than being forced into `royalty | bonus | rent
| …`. ONRR groups several unlike things under `Other revenues`, and guessing
which enum value each belongs to would invent a distinction the source does not
make.

---

## 1b. Pre-2003 — recovered, and my own earlier conclusion was wrong

**I first recorded pre-2003 as `NOT AVAILABLE`. That was wrong and is corrected
here.** The portal's floor is January 2003, but that is the *portal's* floor,
not the government's. MMS Minerals Revenue Management — ONRR's predecessor —
published American Indian mineral revenue collections back to **CY1925**, and
those pages survive on `web.archive.org`. Raw copies under
`data/raw/resources/onrr_historical/`.

### The extraction hazard, and the gate that makes it safe

These PDFs have a text layer **vertically offset by exactly one line**: the
value printed beside `Coal` belongs to `Royalties:`, and every label sits one
row behind its number. A naive dump yields numbers that are individually
plausible and systematically wrong — the worst kind of failure, because nothing
looks broken.

So the parser de-offsets and then **refuses to publish anything that does not
reconcile**. Two checks must pass per year:

```
coal + gas + oil + other royalties == printed royalty subtotal
subtotal + rents + bonuses + other revenues == printed total
```

The calendar-year table cross-foots in **both** directions — 7 column totals
and 5 row totals, 12 independent checks, all exact. That arithmetic is the
evidence the de-skew is right; without it this would be a guess dressed as a
series.

**The gate earned its keep on the first run.** FY1997 was **held**: its
components sum to $202,076,282 against a printed subtotal of $202,076,292 — a
**$10 internal inconsistency in the source document**. The year's total does
reconcile against the printed subtotal, so the fault is in one component. Held
rather than published, and recorded here as a finding.

### Coverage recovered, and the gap that remains

| Grain | Recovered | Gap | Portal resumes |
|---|---|---|---|
| Calendar year | CY1996 – CY2000 | **CY2001, CY2002** | CY2003 |
| Federal fiscal year | FY1994 – FY2001 (FY1997 held) | **FY2002** | FY2003 |

**CY2001 and CY2002 are a genuine gap.** No `CollFY02Ind.PDF`, no
`Coll_Qrt_Ind_02.pdf` and no `mrr01`/`mrr02` exist in the Wayback index; the
MRMWebStats app was captured only for FY2004–FY2009. CY2001 exists only as a
Jan–Sep partial, which is not a year and is not published as one.

So against the 2000–2026 target: **2000 recovered, 2001–2002 not obtainable,
2003–2026 complete.** That is a property of the record, and stating it beats
filling it.

The full CY1925–1995 series exists in `Am_Ind_Coll.pdf` and is **scoped but not
built** — outside the 2000–2026 target.

---

## 2. North Dakota — Three Affiliated Tribes / MHA Nation

**The strongest tribe-identifiable rows in the ledger.** The ND State
Treasurer's Tax Distribution Search names one tribe, one tax type, one payment
date and one amount. Nothing aggregated, nothing inferred.

Source: `https://apps.nd.gov/stn/inquiry/search.aspx?searchtype=tribe`. The
public Treasurer page exposes only `searchtype=city`; the tribe mode is an
undocumented parameter on the same app.

| Distribution type | Payments | Coverage |
|---|---:|---|
| Oil Extraction Tax | 215 | 2008-09 .. 2026-07 |
| Oil & Gas Gross Production | 215 | 2008-09 .. 2026-07 |
| Oil & Gas Straddle Well | 59 | 2021-09 .. 2026-07 |

**489 payments totalling $3,125,453,109.56.** Parsed independently twice — once
by the retrieval agent, once by the build script — agreeing to **$0.00**, and
both matching the app's own printed Grand Total.

**2008-09 is the true start.** The query asked for 2000 onward and the app
returned nothing earlier, consistent with the 2007 enabling act. Pre-2008
distributions do not exist.

### A hardcoded label silently returned zero rows

The first parser hardcoded `"Oil and Gas Gross Production Tax"` and found
**nothing**, because the Treasurer writes `"Oil & Gas Gross Production"`. A
filter that finds nothing looks exactly like a series that does not exist —
the failure `docs/PULL_DISCIPLINE.md` warns about for `recipient_type_names`.
The parser now reads each page's own declared `Distribution Type:` and holds
any label it does not recognise instead of dropping it.

### The allocation formula, by period — all four changes sourced

Chapter 57-51.2 was touched in exactly four sessions: **2007, 2013, 2015,
2019**. No changes in 2009, 2011, 2017, 2021, 2023 or 2025. Recorded in
`data/raw/resources/north_dakota/cedar_allocation_formula.csv`, each period
with its enacted session law and a verbatim quote.

| Period | Trust (tribe/state) | Fee (tribe/state) | Authority |
|---|---|---|---|
| 2007-07-01 .. 2013-06-30 | 50 / 50 | **20 / 80** | 2007 ch. 545 (SB 2419) |
| 2013-07-01 .. 2019-06-30 | 50 / 50 | **50 / 50** | 2013 ch. 473 (HB 1198) |
| 2019-07-01 .. | **80 / 20** | **20 / 80** | 2019 ch. 506 (SB 2312) |

I verified the 2019 and 2013 text in the session-law PDFs myself, strikethrough
preserved as printed: *"AllThe tribe must receive eighty percent"*,
*"fiftytwenty percent … nontrust lands"*, *"twentyfifty percent"*.

**A conflict worth recording.** 2013 ch. 5 (HB 1005, appropriations) also
amended the same subsection but kept "twenty percent". It was approved
2013-04-30, six days before HB 1198. The Century Code text as of Dec 2016 reads
"fifty", so HB 1198 controls. Four Wayback snapshots of the official Century
Code PDF (2016-12, 2019-05, 2020-06, 2021-10) corroborate independently: 50/50
through May 2019, 80/20 by June 2020.

**The 2019 change is vintage-based, not a date switch — and this is the trap.**
SECTION 5 APPLICATION, verified in the PDF:

> "Sections 1 and 2 of this Act are effective for all new oil and gas wells on
> which **drilling first commences after June 30, 2019**…"

Combined with NDCC 57-51.2-02(6) — a well stays subject to its agreement terms
**for the life of the well** — every post-2019 monthly distribution is a
**blend of both regimes**, weighted by the spud-date mix of producing wells.
The published series does not decompose by vintage and Cedar Press does not
model it. The `allocation_formula` value for that period says so in the field
itself, so a subscriber cannot pick up 80/20 and multiply.

The formula is matched to rows by **payment date**, which lags the taxable
event; the caveat is stated in the field value rather than left implicit.

### Trust vs fee, and why no assets were built

**No ND DMR field states trust vs fee mineral ownership.** DMR's free well
search exposes Field, Operator, Township, Range, Section — location only. The
strings `TRUST` and `INDIAN` that appear in DMR data are **lease, well and
operator names** (`AN-MOGEN TRUST- 153-94-2932H-5`, `W. H. HUNT TRUST ESTATE`,
a field named `INDIAN HILL`) and must never be parsed as ownership.

Trust/fee is a **Tax Commissioner construct, and it is fractional rather than
binary**: each spacing unit carries a Trust Ratio and Non-Trust Ratio by
mineral acreage, encoded in pool codes (`Bakken - Fort Berthold Trust - Pre
2019` = 451, `… Fee - Pre 2019` = 351). A single well typically splits across
both. So reservation-boundary geography could not establish ownership even in
principle, and DMR cannot supply the attribution at all.

The complete DMR Well Index is **subscription-gated** ($100/yr basic). No
asset rows were built; `resource_assets.csv` ships with headers and zero rows,
which is the honest state.

---

## 3. Utah — Uintah Basin and Navajo Revitalization Funds

**Classification first, because it is the whole point.** A state severance-tax
allocation into a revitalization fund is **not a royalty and not a payment to a
tribal government**. Utah's enacted code says so directly:

> "(4) The fund: (a) consists of **state severance tax money to be spent at the
> discretion of the state**; and (b) **does not constitute a trust fund**."
> — Utah Code 63N-24-703(4)

So no tribe is written as recipient or beneficiary on these rows. The tribe
appears in `resource_parties.csv` with `relationship = serves_native_entities`
— the fund serves a Native population and is emphatically not owned by it. That
is the same distinction script 33 draws for Cook Inlet Housing Authority;
writing a parent here would invent an ownership fact. Grantees include
counties, state agencies and nonprofits alongside tribal entities.

### Statutory percentages — from enacted code, not a bill draft

The prior report cited an **introduced-bill PDF, which is not authority**.
These come from the versioned enacted text on le.utah.gov (effective
2026-07-01, so current law today):

**59-5-116, Uintah Basin Revitalization Fund** —
<https://le.utah.gov/xcode/Title59/Chapter5/C59-5-S116_2026050620260701.html>
- **33%** of severance tax on wells producing on or before 1995-06-30
- **80%** on wells producing on or after 1995-07-01
- **80%** on Ute-Moab Land Restoration Act lands, production from 2001-01-01
- Cap: $3M FY2005-06 rising to $6M FY2007-09, CPI-indexed from FY2009-10

**59-5-119, Navajo Revitalization Fund** —
<https://le.utah.gov/xcode/Title59/Chapter5/C59-5-S119_2026050620260701.html>
- **33%** on wells producing on or before 1996-06-30
- **80%** on wells producing on or after 1996-07-01
- Cap: $2M FY2006-07, **$3M** from FY2007-08

Both conditioned on interests **held in trust by the United States** for the
tribe and its members — which is why these are the only rows in the ledger
carrying `land_status = trust`, and the basis column says exactly why.

**A citation correction:** the governing chapters were **renumbered in 2026**.
Both programs moved from Title 35A ch. 8 into **Title 63N ch. 24** (parts 6 and
7) by ch. 393, 2026 General Session. The Utah DWS program pages still cite the
old 35A-8-1601/1701 numbers. Anything citing Title 35A is now stale.

### The money series

`UT_COBI_fund_financials`, from the Legislative Fiscal Analyst's COBI API —
`https://cobi-ws.utah.gov/api/fund/2115.json` (Navajo) and `/2135.json`
(Uintah Basin). **118 fund-year rows: NRF FY1997–FY2025, UBRF FY1996–FY2025**,
each carrying beginning balance, revenues, expenses, transfers and ending
balance. Revenues and expenses are published as ledger rows; the source's
negative sign on expenses is retained so inflow and outflow do not have to be
told apart by column name.

**A caveat carried in the data, not just here:** COBI `revenues` is **not pure
severance tax** — the funds also earn interest and can receive appropriations,
so the figure exceeds the statutory severance deposit. That sentence is in
`beneficiary_note` on every affected row.

### Not built

**Utah State Tax Commission severance-deposit figures.** 26 annual reports
(`fy00report.pdf`–`fy25report.pdf`) were retrieved and are held raw. The
labelled fund rows appear only for **FY2003–FY2009 and FY2018–FY2025** —
FY2010–FY2017 reports carry no such row at all, and FY2000–FY2002 do not
mention the funds. More importantly, the **column order shifts between report
vintages** (some years print current/prior/change/%, others prior/current),
so the figures were read positionally and are ambiguous. Held rather than
published wrong.

**The "800+ Navajo revitalization grants since 1998" claim: NOT VERIFIED.**
The claim was not located in the DWS program pages, either policy-and-procedure
PDF, or four board packets — zero hits on "since 1998", "800+", "over 800". The
underlying consolidated grant list was not found either; the statutory
reporting duty runs into GOEO's consolidated report rather than a standalone
list. **The number is not asserted anywhere in this build.** What does exist:
per-year allocations FY2003–FY2025 (UBRF) and FY2003–FY2024 (NRF) in the policy
PDFs, and per-meeting approvals 2021–2026 in the Granicus board packets.

---

## 4. Montana — Fort Peck, and a finding that is a zero

### The "50%, quarterly" claim: CONFIRMED — but by the agreement, not by statute

The brief expected MCA Title 15 ch. 36. **No section of chapter 36 mentions
tribes, tribal agreements, or a 50% share** — 15-36-331 and 15-36-332 contain
only county/school/state allocations. The authority is the **State-Tribal
Cooperative Agreements Act, MCA Title 18 ch. 11**, and MCA 18-11-112(5) is why
no percentage appears in the tax title at all:

> "If a tax or license or permit fee is collected or refunded pursuant to a
> state-tribal cooperative agreement, each party must receive its share **as
> provided in the agreement, notwithstanding any contrary state statutory …
> distribution formula**."

The percentage lives in the agreement itself — signed **2008-03-25** by Tribal
Chairman A.T. Stafne and Governor Schweitzer, approved by the Attorney General
under MCA 18-11-105 — at Section VIII:

> "The amount of oil and natural gas production tax monies that the Tribes
> shall receive each calendar year quarter shall be equivalent to **50% of the
> total tax on new oil and on new natural gas production** on the Reservation…"

Payment frequency is Section VII.B — four fixed quarterly remittance dates.
**Confirmed.**

**Two scope limits an outside reader would miss.** Section II.B: the agreement
covers **new production only** — wells drilled on or after the effective date —
and does not affect existing production. Section XXI.C excludes the
privilege-and-license tax and the oil/gas natural resource account.

### The finding: 49 consecutive quarters of $0.00

Montana DOR's quarterly distribution letters carry an explicit
`Tribal Distribution:` line. I extracted it from **all 49 letters myself**,
production quarters **2014Q1 through 2026Q1**:

> **Every single quarter reads `Tribal Distribution: $0.00`.**

Per `docs/DATA_ODDITIES.md` a zero is an assertion, not missing data — the
state is stating it distributed nothing. Dropping these rows would convert a
measured fact into an absence, which is the opposite of what happened. They are
published, with `amount_sign_meaning` saying so.

Corroborated by Montana Legislative Services (2010-07-19): *"The State is to
collect the tax and distribute 50% of it on a quarterly basis to the tribe.
**To date, there has been no tax collected by the state.**"*

**No tribe is attributed.** The letters name no tribe, so these rows are
`state_aggregate` with an empty recipient. The agreement behind the line is
with the Assiniboine and Sioux Tribes of the Fort Peck Reservation, but that is
context for this log, not an attribution for a row.

### Coverage and other tribes

Nothing before production 2014Q1 exists at this source; all 24 probed
2009–2014 URLs returned 404. **Blackfeet** had an agreement in the 1990s,
amended 2000-02-04, **terminated by the Tribe**; the document itself is not
online. **Crow**: negotiations in 2009, no evidence an agreement was ever
executed. Neither is built.

**MT BOGC records no mineral-ownership field** — the documented attribute list
is location and well identity only. Same conclusion as North Dakota.

---

## 5. Scale context that is NOT a series

**BTFA.** Verified against the FY2027 Interior Budget in Brief, BTFA chapter
p. BTFA-2, retrieved to `data/raw/resources/btfa/2027bibbtfa508.pdf`:

> "BTFA will continue to manage approximately **$8.8 billion** of Indian trust
> funds held in more than **4,300 Tribal accounts** and more than **414,000
> Individual Indian Money accounts**."

> "BTFA **disburses more than $1 billion annually**…"

All four figures check out verbatim. **And the same page is why it is not a
resource-revenue series:**

> "Trust funds include payments from **judgment awards, settlements of claims,
> land-use agreements, royalties on natural resource use, other proceeds
> derived directly from trust resources, and financial investment income.**"

Royalties are one of six ingredients. Scale context, recorded here, not in the
ledger.

**IRS.** <https://www.irs.gov/government-entities/indian-tribal-governments/natural-resources-and-tribes>
is **tax-treatment guidance, not a dataset** (IRC §7873 fishing-rights income
and related FAQs). Nothing was built from it.

**BIA NIOGEMS.** Lease, tract, agreement and well identifiers for Indian
minerals live in an **internal BIA system** — on the order of 50 tribal users
across 8 reservations — that Cedar Press has no access to.
`resource_assets.csv` carries `niogems_lease_id`, `niogems_tract_id`,
`niogems_agreement_id` and `niogems_well_id` **empty by construction**, so that
if access is ever granted the join is a merge rather than a rebuild. NIOGEMS is
a **partnership target, never a cited source.**

---

## Schema decisions

**Three clean files, not two.** The brief named `resource_assets.csv` and
`resource_revenue.csv` and separately required *"many-to-many party links, not
a single `tribe_id`"*. Those cannot both hold in two flat files: a single owner
column on an asset row would have to pick one of the tribal government, the
allottees, the enterprise, the operator, the lessee and the trust account, and
would assert a false exclusivity. Party attachment is therefore its own table,
`resource_parties.csv`, keyed by `(object_type, object_id)` and serving assets
and revenue events alike.

`relationship` preserves the spine's distinction rather than collapsing it:
`parent_native_entity` is **ownership**, `serves_native_entities` is
**service**, `counterparty` is an outside party. **An operator is never an
owner.** Utah's funds are the live case — `serves_native_entities`, parent
empty.

**`aggregation_level` was added** and is load-bearing beside
`measurement_status`. A national aggregate already contains the tribe-specific
money, so summing across levels double-counts.

**Deflator.** `amount_usd_real2025` uses `data/clean/inflation_deflator.csv` —
the same BEA GDP implicit price deflator (NIPA Table 1.1.9), same 2025 base,
as `code/40_build_prime_contracts.py`. **No second deflator was created.**

One deliberate divergence from script 40: it falls back to a factor of `1.0`
for an unknown year, safe there because its data stops in a complete year.
**This ledger runs into 2026, where BEA publishes no annual index**, and
backwards to 1994, before the file starts. A `1.0` fallback would silently
assert those are 2025 dollars. `amount_usd_real2025` is therefore **blank** on
312 rows, never 1.0, and the deflator file was not extended to invent factors.

**Entity resolution** goes through `resolve_entity` imported from
`code/33_apply_party_rulings.py`. No second name matcher was written. Anything
unresolved is written to `review/resource_ledger_unresolved.csv` and **held out
of the ledger**.

---

## Held for review (4)

| Item | Why |
|---|---|
| `ONRR:NATIVE_AMERICAN_LAND_CLASS` | 9,395 rows can never be attributed. **No action possible** — recorded so the empty party set reads as source design, not unfinished work. |
| `RESOURCE:MMS:FY1997` | Source's own components miss its own subtotal by $10. |
| `SPINE_ALIAS:Mandan, Hidatsa, and Arikara Nation` | Resolves only as "Three Affiliated Tribes". **Append** the alias to `TRBF-MHATAT-00`. |
| `SPINE_ALIAS:MHA Nation` | Same. No ledger row is affected; this prevents a future source failing to resolve. |

*The spine was not edited — `code/01_build_entity_spine.py` was not run, and
these are queued as append-only suggestions.*

---

## Scoped but not built

| Scope | Why |
|---|---|
| **New Mexico** | Royalty deductions are **confidential at taxpayer level**; NM supports production context but cannot yield tribal payment amounts. No estimate was built to fill the gap. |
| **Colorado** (Southern Ute, Ute Mountain Ute) | Not sourced this pass. |
| **Wyoming** (Wind River) | Not sourced this pass. |
| **Oklahoma** (Osage mineral estate) | A distinct legal regime deserving its own treatment, not a row in a state-tax table. |
| **MMS CY1925–1995** | Verified extraction method exists; outside the 2000–2026 target. |
| **Utah Tax Commission severance deposits** | Column order ambiguous across vintages. Raw retained. |
| **ONRR production volumes** | Retrieved and held raw. Nothing to attach them to — ONRR suppresses everything below national aggregate. |
| **ND DMR well index / MT BOGC** | Subscription-gated; and neither records mineral ownership, so neither could establish trust vs fee anyway. |
| **BIA NIOGEMS** | No access. Partnership target. |

---

## Verified vs taken on faith

*This section is the point of the log.*

### Verified myself, against a retrieved document

| Claim | Verdict |
|---|---|
| ONRR suppresses state/county/FIPS on Native records | **VERIFIED.** 0 of 9,238 Native rows carry geography; 99.8% of Federal rows do. Re-measured every run. |
| ONRR Native coverage reaches back further than 2022 | **VERIFIED.** 2003-01 .. 2026-06. |
| ONRR monthly and calendar-year files agree | **VERIFIED.** $0.00 max difference across 23 shared years. |
| BTFA ~$8.8B, 4,300+ Tribal accounts, 414,000+ IIM accounts, $1B+/yr | **VERIFIED** verbatim, FY2027 Budget in Brief p. BTFA-2. |
| BTFA totals mix royalties with settlements, land-use and investment income | **VERIFIED** verbatim, same page. |
| Native American land revenue mixes tribal and allottee interests | **VERIFIED** verbatim, NRRD documentation. |
| ND: 489 payments, $3,125,453,109.56 | **VERIFIED.** Two independent parses agree to $0.00 and match the app's printed Grand Total. |
| ND 2019 split is 80/20 trust, 20/80 fee, **wells spudded after 2019-06-30 only** | **VERIFIED** in the session-law PDF, SECTION 5 APPLICATION. |
| ND 2013 change to 50/50 on non-trust | **VERIFIED** in the session-law PDF, strikethrough preserved. |
| MT Fort Peck: 50% of tax on new production, paid quarterly | **VERIFIED** verbatim, agreement Sections VIII and VII.B. |
| MT tribal distribution is $0.00 every quarter 2014Q1–2026Q1 | **VERIFIED.** I extracted the line from all 49 letters myself. |
| MMS calendar-year de-skew is correct | **VERIFIED.** Cross-foots both directions, 12 exact checks. |
| Utah percentages (33% / 80%) and caps | **VERIFIED** against **enacted code**, not a bill draft. |
| Utah funds are state money, not tribal royalty | **VERIFIED** verbatim, Utah Code 63N-24-703(4). |
| IRS page is guidance, not a dataset | **VERIFIED.** |

### Refuted

| Claim | Verdict |
|---|---|
| ONRR Native coverage is 2022–2025 | **REFUTED.** Actual 2003-01 .. 2026-06, and MMS extends it to 1994. |
| Pre-2003 is unavailable *(my own earlier conclusion in this log)* | **REFUTED.** MMS-era archives reach CY1925. Corrected above. |
| Montana's 50% share is in MCA Title 15 ch. 36 | **REFUTED.** Chapter 36 never mentions tribes. Authority is Title 18 ch. 11; the percentage is in the agreement. |
| Utah's funds are governed by Title 35A ch. 8 | **STALE.** Renumbered into Title 63N ch. 24 by ch. 393, 2026 GS. |

### Could NOT verify

| Claim | Status |
|---|---|
| "800+ Navajo Revitalization Fund grants since 1998" | **NOT VERIFIED.** Neither the claim's source sentence nor the underlying grant list was located. **Not asserted anywhere in this build.** |
| Whether the Fort Peck agreement was renewed after 2017-06-30 | **NOT VERIFIED.** Only the auto-renewal clause (Sec. XX) is primary evidence; no executed renewal found. |
| Text of the terminated Blackfeet agreement (2000-02-04) | **NOT RETRIEVED.** Described in a 2010 legislative report; document not online. |
| CY2001, CY2002, FY2002 Indian revenue | **NOT AVAILABLE.** Absent from the Wayback index and from every MMS/ONRR route probed. |
| Trust vs fee decomposition of the ND distribution series | **NOT PUBLISHED ANYWHERE.** The state reports one combined amount per tax type per month. |

---

## 2026-09-02 — C4 CLOSED. `natural-resources` is READY.

*Written by the workstream that owned the last blocker. Every figure is
reproducible with `py -3 code/900_nr_hub_join.py verify` and
`py -3 code/901_nr_record_scope.py verify`; both exit 1 when they stop being
true, and both prove that with `verify --selftest`.*

`518` reported one blocker: **"C4 only 25% of entity-bearing rows carry a Cedar
id"**. Re-measured with `csv.reader` against the live files, that 25% was
`3,744 / 14,997` and it was **three unrelated things summed into one
percentage** — two of which were measurement defects and one of which was real
work.

### 1. What the 25% was actually made of

| | rows | what it was |
|---|---:|---|
| `national_aggregate` revenue rows scored as unkeyed | 9,791 | **the statute, not a defect** |
| resolved entities the scanner could not see | 705 | a scanner blind spot |
| named entity, no `cedar_uid` | **586** | **the genuine work — a hub join** |

**The aggregate rows are not a gap and never can be.** Interior publishes
Native American resource revenue only in aggregate, in its own words, and the
file agrees: `State`, `County`, `FIPS Code` and `Offshore Region` are blank on
100% of Native American rows against 99.8% populated on the Federal rows of the
same extract. There is no entity on the row to carry an id. Counting those rows
as unkeyed measured the law.

ADR-010 had already decided this — consequence 1, verbatim: *"Coverage is
measured against the resolvable denominator, not the row count."* What was
missing was a per-row column that made the resolvable denominator derivable,
which is exactly what `518`'s own comment said it was waiting for. `901` writes
it.

### 2. `901_nr_record_scope.py` — ADR-010 scope on `resource_revenue.csv`

Scope is a deterministic function of `aggregation_level` + `source_system`.
Nothing is judged row by row.

| scope | rows | attached | why |
|---|---:|---:|---|
| `entity` | 1,287 | 1,287 | 779 `entity_specific` + 508 Osage `per_headright_rate` |
| `unresolved` | 60 | 0 | OMC newsletter component lines. **The work queue, and they stay in the denominator as misses.** |
| `indian_country` | 9,791 | 0 | aggregate by law (above) |
| `native_serving` | 118 | 0 | Utah Code 63N-24-703(4) — state severance money, *"does not constitute a trust fund"*; the tribe is `serves_native_entities` in `resource_parties.csv`, never recipient |
| `geographic` | 49 | 0 | MT DOR quarterly letter carries a tribal line and **names no tribe**; scoped to the state |

**C4 on the resolvable denominator: 1,287 / 1,347 = 95.5%.** The raw row-count
denominator says 11.4%, and both numbers are printed side by side on every run
so nobody has to take the choice on trust.

**The Osage rows keep the publication rule.** `per_headright_rate` is scoped
`entity` because the record's subject is the Osage mineral estate — one Native
entity, carried in `resource_parties.csv` as `mineral_estate_owner` at 100%.
The **recipient** is a class of individual headright holders and is never
published as individuals. The Council's 2,228.97393 divisor stays a check and
never a multiplier.

**The anti-gaming invariant, because a scope column is exactly how a bad number
gets made to look good:** no row scoped `indian_country`, `geographic` or
`native_serving` may carry a `cedar_uid` or a `parent_native_entity` party. A
row only leaves the denominator when nothing in Cedar stands behind it. The
Utah rows pass on the letter of ADR-010 (`serves_native_entities` is
deliberately unkeyed on the actor side), not by being excused. `verify
--selftest` re-scopes an attached row and confirms the guard fires.

### 3. `900_nr_hub_join.py` — the 586, and 19,465 rows nobody was measuring

Nothing here decides who an entity is. Every id written is an exact lookup of
an identifier the row already holds, in `cedar_identity_register.csv`,
`register_status = active`.

| table | rows | joined | note |
|---|---:|---:|---|
| `resource_revenue.csv` | 11,305 | **586** | `recipient_entity_id` → `cedar_uid`. Three Affiliated 492 · Crow 32 · Hopi 32 · Navajo 30. 119 were already keyed → 705 total |
| `resource_parties.csv` | 1,938 | 1,220 | `entity_id` handle → `cedar_uid`; 220 already keyed |
| `anc_ceiling_roster.csv` | 196 | 190 | **local `anc_id` scheme lifted onto the hub** |
| `ancsa_filings_index.csv` | 19,269 | 19,269 | via `anc_id` → roster |
| `resource_assets.csv` | 35 | 32 | through the **party table**, single `parent_native_entity` |

**The two ANCSA tables were the bigger finding.** They key entities in a
source-local scheme (`anc_id = ANC-<16 hex>`) the hub had never adopted — the
exact ADR-009 defect — and the old scanner did not score them 0%, it **did not
see them at all**, because neither table had a column it recognised. 19,465
rows. The join is fenced: candidates restricted to `ANRC`/`ANVC` handles only,
because a roster row is an ANCSA **corporation** by construction. That fence is
load-bearing — **22 of 196 roster names match a federally recognized village
TRIBE (`AKNF`) and a village CORPORATION (`ANVC`) both**, which is the trap
`docs/NATIVE_ENTITY_NUANCES.md` names. Comparison is on a typographically
normalised name only: curly apostrophe → ASCII, diacritic folding, corporate
suffixes. **No containment, no fuzzy distance, no closest match.** Exactly one
candidate or the row keeps its blank.

**501 refusals, each with a written reason**, in
`review/nr_hub_join_unresolved_2026-09-02.csv`:

- **492** `resource_parties` rows whose `entity_id` is `PAYER-STATE-ND`,
  `PAYER-US-BIA` and four siblings. Federal and state payer stubs. Correctly
  not in the hub, and they must never count as Native-entity attachment.
- **6 roster rows.** Two are *The Thirteenth Regional Corporation* / *The 13th
  Regional Corporation* — **one real ANC, entered twice, and absent from the
  Cedar spine.** Four are **scraper artefacts**, not corporations, captured as
  page furniture from the roster's source page (`lbblawyers.com`,
  `confidence_tier = C`): *"A compilation of information about the Alaska
  Native Claims Settlement Act"*, *"Alaska Native Claims Settlement Act
  (ANCSA)"*, *"Native Corporations | ANCSA Resource Center"*, *"Village and
  Urban Corporations"*. **Flagged, not deleted** —
  `entity_resolution_status = unresolved` on the row, and proposed to the owner
  in `review/OWNER_DECISION_QUEUE.md`.
- **3 assets.** One has two `parent_native_entity` lessors (Navajo *and* Hopi,
  the Peabody leases) and is refused rather than collapsed onto one; two have
  no parent party.

### 4. What is still open in this dataset

| item | size | evidence |
|---|---:|---|
| OMC newsletter component lines with no bridge row | 60 rows | scoped `unresolved`, in the denominator |
| `tribal_bond_issuances.issuer_entity_id` blank | 29 rows | issuer names carry the parent tribe in a parenthetical; the register's canonical names are short forms and **no exact match lands**, so it needs the alias layer, not a fuzzy matcher |
| The Thirteenth Regional Corporation absent from the spine | 1 entity, 2 roster rows | a mint, not a match |
| `resource_parties` PAYER stubs | 492 rows | correctly unkeyed; a payer dimension, not an entity gap |

None of these is a C4 blocker: 23,879 of 24,533 entity-scoped rows across all
eight tables carry a Cedar id.
