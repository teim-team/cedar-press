# Native Natural Resources Ledger — the state expansion

*Second wave, 2026-08-06. Built by `code/83_build_resource_ledger.py --more-states`.
Pairs with `docs/RESOURCE_LEDGER_BUILD_LOG.md`, which covers ONRR, ND, UT and MT.*

The first wave answered the question for North Dakota, Utah and Montana. This
wave asked it of every other state where a resource-revenue mechanism could
plausibly exist, and treated all three answers as output.

**Worked: 15 states plus the federal layer. 47 findings.
7 BUILT · 14 MECHANISM EXISTS, NO PUBLIC SERIES · 26 NO MECHANISM.**

**Added to the ledger: 174 revenue events, $186,060,232.51 nominal, 114 party
links, 1 entity newly named — The Osage Nation** (`TRBF-OSAGEN-00`).

By level: 106 `per_headright_rate` · 60 `entity_specific_component` ·
8 `entity_specific`. By status: 120 `actual_payment` · 54 `reported_revenue`.

The evidence sits in
`data/raw/resources/_state_mechanisms/cedar_state_mechanism_register.csv`, one
row per state × mechanism with the enacted citation, the URL actually read, a
verbatim quote and the date checked. This document is a reading of that file,
not a separate set of claims.

---

## The finding that governs everything else

**There is no published, named-tribe resource revenue series in the United
States, with one exception, and the exception is the Osage.**

That is not a shortfall of this pass. It is a measured property of the record,
and three independent lines of evidence converge on it:

1. **The federal collector suppresses it by law.** ONRR publishes Native
   American revenue only in national aggregate. Verified at the data level, not
   from site copy: across `monthly_revenue.csv`, `calendar_year_revenue.csv`,
   `fiscal_year_revenue.csv`, `fiscal_year_disbursements.csv` and
   `monthly_disbursements.csv`, **every** Native American row has `State`,
   `County` and `FIPS Code` empty, and **no ONRR file has a tribe-name field at
   all**. This forecloses the same lead in every state at once.

2. **The states mostly never built a mechanism.** Of the 26 NO_MECHANISM
   findings, most are enacted severance-tax distribution sections read end to
   end with no tribal recipient in them.

3. **Tribal governments do not self-disclose.** Confirmed independently by a
   parallel recipient-side sweep, and again here: the Southern Ute Growth Fund
   publishes no dollar figure at all, and the Southern Ute Constitution
   restricts the audited report to *"tribal members upon request."*

**What breaks the pattern is a tribe that publishes for itself.** The Osage
Minerals Council does, and that is the whole of this wave's new money.

---

## State by state

| State | Outcome | What is there |
|---|---|---|
| **Oklahoma** | **BUILT** | Osage Mineral Estate. Two series, 174 rows. The flagship. |
| **Alaska** | **BUILT** *(by another layer)* | ANCSA §7(i)/§7(j). Authority verified here; **no rows added** — see below. |
| **New Mexico** | **BUILT** *(mechanism verified, rows pending)* | Navajo Nation audited actuals. Parser shipped, transcription outstanding. |
| **Washington** | MECHANISM, NO SERIES | RCW 43.06.480 — a timber excise tax agreement with the Quinault Nation. |
| **Wisconsin** | MECHANISM, NO SERIES | Wis. Stat. 70.395(2)(d)2m — $100,000 to a Native American community. |
| **Colorado** | MECHANISM, NO SERIES | C.R.S. Title 24 art. 61 — and it runs the *other way*. |
| **Wyoming** | MECHANISM, NO SERIES | Federal channel only. State code is empty of tribes. |
| **Arizona** | MECHANISM, NO SERIES | Peabody's Navajo and Hopi coal leases. Rates published, dollars never. |
| **Montana** *(beyond Fort Peck)* | NO MECHANISM | Crow coal invalidated in 1988. Blackfeet agreement terminated. |
| **Nevada** | NO MECHANISM | The strongest verified absence in the wave. |
| **Minnesota** | NO MECHANISM | Minn. Stat. 298.28 distribution list, no tribal recipient. |
| **Michigan** | NO MECHANISM | Six full-text queries against a working positive control. |
| **Texas** | NO MECHANISM | Two recipients in the severance code, neither tribal. |
| **Louisiana** | NO MECHANISM | Parish governing authorities only, all 37 sections read. |
| **California** | **NOT CLOSED** | Recorded as unresolved rather than dressed up. |

---

## 1. Oklahoma — the Osage, and why it is the only one

### Why the Osage estate is structurally unlike every other case

The 1906 Osage Allotment Act severed surface from minerals and reserved the
**entire** mineral estate — 1.45 million acres, coextensive with Osage County —
to the Osage Nation, **undivided**. Every other allotted reservation had its
minerals allotted along with the surface. That is precisely why ONRR's Native
American class mixes tribal with individual allottee interests and cannot be
decomposed: on the Osage estate there is exactly one owner to name.

### That did not make the federal government publish it

**Measured in this repository, not assumed.** The string `Osage` appears **zero
times** in every ONRR bulk file Cedar Press holds — monthly revenue,
calendar-year revenue, fiscal-year disbursements, production. The distinctive
legal status buys nothing against the suppression.

> The brief's hypothesis — that BIA/ONRR reporting on the Osage might be more
> specific than the suppressed national aggregate — is **REFUTED**. What
> rescues Oklahoma is not a federal source. It is that **the Osage publish for
> themselves.**

### 1a. Headright payment history — 106 rows

Source: `Headright history updated 5.12.26.xlsx`, linked from the Osage
Minerals Council page. Annual totals since 1880, quarterly since 1906,
**2000Q1–2026Q2 published here** (the 2000–2026 scope floor, the same rule that
scoped out MMS CY1925–1995).

**The unit is the whole point.** These are **dollars per full headright** — a
rate, not a total. The Council prints a divisor of **2,228.97393 headrights**
right beside it, and the temptation is exact: multiply, and print an aggregate
for the hundred-plus quarters where only the rate exists.

> **Refused.** The divisor is used **only as a check**, never as a multiplier.
> These rows carry `aggregation_level = per_headright_rate`, a value added to
> the vocabulary so the non-additivity is machine-visible rather than a
> footnote.

**The gate.** The sheet prints an annual total beside the four quarters. Every
complete year must satisfy `Q1+Q2+Q3+Q4 == printed annual total` or the year is
held. **All 28 years from 1998 to 2025 reconcile to $0.00.** That check is what
makes the sheet's three side-by-side year blocks (1880–1930 in columns A–F,
1931–1981 in H–M, 1982–2032 in O–T) safe to read; a block misalignment would
break it immediately, while the numbers alone would look entirely plausible.

Corroborated independently: the 2020 Q4 cell reads **$2,385**, and Osage News
reported *"the December quarterly headright payment was formally announced at
$2,385 per full headright."* Two publications, same figure.

### 1b. Quarterly mineral estate revenue — 68 rows

Source: the Osage Minerals Council's quarterly newsletters. **8 quarters
between 2014Q3 and 2022Q1**, carrying total revenue plus an oil / gas / sand and
gravel / rental / bonus / water-use breakdown and the Oklahoma gross production
tax paid.

**Dating these is a measurement, not an inference — and that took work.** Each
newsletter states a production quarter *in words*, but that wording **does not
agree** with the payment quarter for two of the eight letters, and one letter
states no quarter at all. What every letter does state is the resulting
per-headright payment — and that value matches **exactly one** cell in the
headright spreadsheet within a year of the document's own date. So the period is
fixed by agreement between two independent publications of the same body, and
any letter failing to match uniquely is held. The letter's own quarter wording
is preserved verbatim in `source_record_id` so the disagreement stays visible.

**A comparability break, found by arithmetic and invisible in the numbers.**
Through 2017, total revenue ÷ divisor reproduces the published headright rate.
From 2021 it overshoots by ~5%. Subtracting the Oklahoma gross production tax
first restores the match:

```
2016Q3   7,209,421.48                      / 2,228.97393 = 3,234.41 -> $3,230  MATCH
2021Q3  11,317,385.83                      / 2,228.97393 = 5,077.40 -> $5,075  NO
2021Q3 (11,317,385.83 -   551,143.16)      / 2,228.97393 = 4,830.13 -> $4,830  MATCH
```

> **"Total Revenue" is NET of the state gross production tax in the early
> vintage and GROSS of it in the later one.** A subscriber charting the two
> together would read a definition change as ~5% growth. Written to
> `review/resource_series_breaks_2026-08-06.csv`.

**The "Major Details" block is not a partition, and this is provable.** In
2016Q3 the oil line alone ($7,332,608.57) **exceeds** the quarter's stated total
revenue ($7,209,421.48). The components are real published measurements and are
kept, but they carry `aggregation_level = entity_specific_component` so they can
never be summed to the total or to each other.

**Two source defects carried through rather than silently corrected:**
- The Q1 2022 letter computes the payment as `$5655` while the Council's own
  spreadsheet says `5665`. The dating gate caught this and held the quarter —
  correctly, because `$5655` matches no published cell. Rather than assume which
  publication is right, the parser **recomputes the rate from the letter's own
  arithmetic** and requires *that* to land on exactly one cell:
  `(13,286,673.55 − 649,807.68) / 2,228.97393 = 5,669.32 → $5,665`, which is the
  spreadsheet's value exactly. Two independent routes agreeing is evidence, not
  a loosened gate — if the recomputation had also failed to land uniquely, the
  letter would still be held. The typo is carried in `source_record_id`, never
  silently corrected.
- The 2021 Fall letter prints `Total Revenue $11,317,385.83` and
  `Major Details of the $11,317,383.83` — a $2.00 internal inconsistency.

**Money flowing the other way.** The newsletters carry a line
*"Gross Production Tax Paid to the State of Oklahoma"*. That is a measured
amount leaving a named Native entity for a state. It is recorded with
`revenue_type = production_tax_paid_to_state`, deliberately outside the enum,
because every enum value names money **received** and forcing it into one would
invert its direction.

### 1c. Oklahoma's own tax code — a documented absence with two legs

**68 O.S. § 1004**, the gross production tax apportionment section, contains
**zero** occurrences of tribe, tribal, Indian or Osage. The recipients are the
General Revenue Fund, county highway funds, school districts and named state
funds.

The corroboration is better than the statute. The Oklahoma Tax Commission's own
FY2025 apportionment chart **has a column headed "Returned To Participating
Tribes."** It carries $26.1M of motor-fuel and storage-leakage money — and it is
**blank on both gross production tax rows**, against $1.04B of gross production
tax collected.

> A tribal column exists in Oklahoma's severance accounting, and severance is
> provably not in it. That is a far stronger negative than "the statute does not
> mention tribes."

### 1d. What Oklahoma did **not** yield

- **The Osage Nation's own audited financials carry no royalty line, and say
  so.** Note 1: *"The distribution of mineral royalty income to entitled mineral
  royalty income owners is administered by the Bureau of Indian Affairs; these
  distributions are not received by the Nation and are not reflected in the
  accompanying financial statements."* A documented exclusion, not a gap — and
  the reason no ledger row names the Nation as recipient.
- **The *Fletcher* litigation record.** The 2015 opinion records the November
  2011 settlement of *Osage Tribe of Indians v. United States* at **$380
  million**. That is a **settlement**, not resource revenue — the same reason
  the first wave kept BTFA out of the ledger. Recorded as context. The 10th
  Circuit's *"Every headright yields on average $7975 per quarter"* is an
  **average** and is not built.
- **Two newsletters 404** from the Council's own index (2015-01 and 2015-07).
  Recorded in `review/` so the gap reads as link rot rather than as quarters
  that were never published.

---

## 2. Alaska — built, but not by this layer

ANCSA §7(i) is real and it is the second-largest named-entity resource revenue
mechanism in the country. **43 U.S.C. 1606(i):**

> *"70 percent of all revenues received by each Regional Corporation from the
> timber resources and subsurface estate patented to it pursuant to this chapter
> shall be divided annually by the Regional Corporation among all twelve
> Regional Corporations…"*

**A parallel recipient-side sweep landed 185 rows covering all twelve regional
corporations, FY2014–FY2025, before this wave reached them.** This layer
verified the enacted authority and **deliberately added no rows.**

That is `docs/CROSS_SOURCE_VERIFICATION.md` applied to our own work: when two
builds could each produce the same entity, one holds rather than publishing a
competing version. Agreement between two independent internal methods is
evidence; a silent merge would destroy it.

---

## 3. Colorado — the mechanism exists and runs the wrong way

The brief expected state severance-tax sharing with the Southern Ute. There is
none. What exists is **C.R.S. Title 24, article 61** — the Taxation Compact
between the Southern Ute Indian Tribe, La Plata County and the State of Colorado
(enacted L. 96, p. 1705 § 1, effective **1996-06-03**; amended 2000 and 2005).

> *"So long as this Taxation Compact remains in full force and effect, the State
> and the County shall not seek to impose on the Tribe … an ad valorem tax …
> conservation levy or environmental response fund charge … or severance tax
> (article 29 of title 39, C.R.S.)."*

The Tribe is **exempted** from state severance tax, and makes a **voluntary
payment in lieu of taxes to La Plata County**. Article 11.04 caps it — the Tribe
may terminate if the annual payment ever exceeds **$1,000,000**. The annual
amounts go to the county and are **not published**. Article 6.04 does print one
measured amount in the statute itself: **$77,065.84** in full satisfaction of
past claims.

**Colorado also has the same confidentiality trap as New Mexico**, which the
brief did not anticipate. C.R.S. 39-7-101(1)(c) requires operators to separately
report volumes *"delivered to … any Indian tribe as royalty"* — and 39-7-101(4)
makes those statements private documents, with disclosure a petty offense under
C.R.S. 39-1-116. **The data exists and cannot be obtained.**

Severance sharing itself is a clean negative with two legs: the enacted articles
contain no tribal recipient, and the live DOLA grants service shows program
`SEV_FML` with **11,048 records 2014–2025, every one carrying a
local-government id and none naming a tribe.** Statutory eligibility is
"political subdivisions", which a tribe is not.

---

## 4. New Mexico — the prior report confirmed, and broader than flagged

The prior report said taxable value is computed after subtracting royalties paid
to the United States, New Mexico, or an Indian tribe or pueblo, and that
taxpayer detail is confidential. **CONFIRMED, and it is three articles, not
one** — NMSA 1978 §§ **7-29-4.1** (severance), **7-31-5** (emergency school) and
**7-32-5** (ad valorem production) all carry:

> *"B. royalties paid or due any Indian tribe, Indian pueblo or Indian that is a
> ward of the United States of America;"*

Confidentiality confirmed at **§ 7-1-8**. The sharpest corroboration is
**§ 7-1-8.2**, which enumerates what *may* be revealed and includes
taxpayer-level **fuel** detail but has **no oil-and-gas equivalent**. Oil and gas
is closed **by design, not by omission**.

Two clean negatives worth recording: the monthly **Ad Valorem Distribution by
Fund** reports name every recipient with an exact amount and contain zero
tribal hits (Rio Arriba and San Juan counties appear; nothing routes to a
tribe); and the State Land Office's published beneficiary list contains no
tribe, nation or pueblo — structurally correct, since the SLO pays trust
beneficiaries only.

**Navajo is the one buildable New Mexico entity**, from its own audited basic
financial statements, General Fund *"Natural resource revenue — Oil and gas"*
and *"— Mining"*. Schedule 1 separates `Original budget | Final budget | Actual
| Budget variance`, and **only the Actual column is publishable** — the parser
holds any row whose `column_read` is not `actual`, because a projection carrying
`measurement_status = reported_revenue` would misdescribe itself.

**Jicarilla is not buildable.** The taxing power is settled (*Merrion v.
Jicarilla Apache Tribe*, 455 U.S. 130 (1982)) and the collection portal is live
and login-gated, but no aggregate is published. **A trap to avoid:** the NMFA
bond official statement prints *"Jicarilla Apache Nation (General Revenues)
3,085,750"* — that is a **debt-service loan payment**, not oil and gas revenue.

NM OCD publishes **production only** — volumes and operator identity, no revenue
field, no royalty field, no tribal-owner field. "Sales by volume" means volume.

---

## 5. Wyoming — the code is empty, and the vintage rule is in the Statutes at Large

**Across all 514 pages of Wyoming Statutes Title 39, the words *tribe*,
*tribal*, *Wind River*, *Shoshone* and *Arapaho* appear zero times.** The single
"Indian" hit is the Indian Wars veteran property-tax exemption at
39-13-105(a)(i); all five "reservation" hits are substrings of "preservation".

**Wyoming has no state-tribal tax agreement authority at all** — no analogue to
Montana's MCA Title 18 ch. 11. Title 9 ch. 4 (federal mineral royalty
distribution) is likewise empty of tribes, and structurally so: 30 U.S.C. § 191
is the state's share of *federal public-domain* leases, and Indian trust
minerals are not public domain. Title 9's tribal references are all
economic-development eligibility (9-12-601 names both tribes for business-ready
community grants), never revenue.

Wind River royalties flow through the **federal** channel, and ONRR suppresses
them. **CONFIRMED.**

> **A vintage rule the brief told me to look for, and it is real.** The
> per-capita share is **85%** under P.L. 85-610, Aug. 8, 1958, 72 Stat. 541 § 2 —
> but the original Act of May 19, 1947, ch. 80, 61 Stat. 102 § 3 set
> **two-thirds**, paid semi-annually. **The 85% applies only from ~1959-01-01
> forward and must never be applied backwards.**
>
> **Citation correction:** 25 U.S.C. § 612 is **omitted from the Code** *"as
> being of special and not general application."* Cite the Statutes at Large,
> not the U.S.C. section.

Four Wind River entity-years are public in Single Audits (Joint Programs FY2016
and FY2022, Northern Arapaho FY2020, Eastern Shoshone FY2016); every other year
is suppressed under the tribal opt-out at 2 CFR 200.512(b)(2) and the PDFs
return HTTP 403. **Not built this pass**, and the two Joint Programs years are
**not one series** — FY2016's $3.97M sits in the Office of Natural Resources
fund, FY2022's $69.66M in the Wind River Energy Commission fund under a
different arrangement.

---

## 6. Arizona — rates without dollars

**A.R.S. § 42-5205 / § 42-5029(D)** carry no tribal recipient. And **coal is
outside the severance tax entirely**: § 42-5201 defines *metalliferous mineral*
as copper, gold, silver, molybdenum or other metal, so coal falls under the
nonmetalliferous mining classification at § 42-5072.

Peabody's 10-Ks confirm the leases — *"Similar provisions govern three coal
leases with the Navajo and Hopi Indian tribes … 64,783 acres"* — but **never
state a dollar amount or a tribal royalty rate.** The 12.5%/8% rates in adjacent
10-K text are **federal** leases and must not be applied to the tribal ones.

> **An important negative.** The widely repeated claim that the Hopi general
> fund was ~80–85% coal-royalty dependent appears only in news and advocacy
> sources and is **NOT VERIFIED in any official document.** It is asserted
> nowhere in this build. Every Hopi Single Audit year is suppressed.

Arizona State Land Department *does* publish royalty dollars — and *Tribe*,
*tribal*, *Indian*, *Navajo*, *Hopi* and *Coal* appear zero times. Structurally
correct: there is no state trust land inside the Navajo or Hopi reservations.

---

## 7. Montana beyond Fort Peck — the prior work confirmed

**Crow coal: NO MECHANISM, and there is a reason.** The Legislative Services
handbook states that Montana's tribal agreements cover *"tobacco, alcohol, motor
fuel, and, in one instance, oil and natural gas taxes"* — **coal is absent** —
because *"In 1988, Montana's tax on coal produced on the Crow Reservation was
invalidated"* (*Crow Tribe of Indians v. Montana*, 819 F.2d 895 (9th Cir. 1987),
aff'd 484 U.S. 997 (1988)). **"Crow" appears zero times in all 430 pages of the
MT DOR 2022–2024 Biennial Report.** The prior conclusion — negotiations in 2009,
no executed agreement — is **CONFIRMED**.

Westmoreland's Crow lease publishes **rates** (*"6.5% of the sales price per ton
sold and delivered F.O.B. Mine at loadout"*, capped at *"12.5% of the Sale
Price"*) and **never a dollar amount paid**. Rate × tonnage would be a modelled
number and is refused. **Vintage rule:** the earlier schedule EX-10.16 applies
only 1994-12-01 to 2004-11-30. **A trap:** the commonly cited *"yearly average
of $3.1 million of income"* is **company** income, not a tribal payment.

**Blackfeet.** The handbook's *"in one instance"* means exactly **one**
oil-and-gas agreement statewide as of Nov 2020, and that one is Fort Peck. The
termination date and any amounts ever distributed remain **NOT VERIFIED**;
MCA 18-11-107 requires agreements to be filed with the secretary of state, so a
records request is the realistic route.

**MCA Title 15 ch. 35 (coal severance) has no tribal share**, nor do coal gross
proceeds (15-23-703) or metal mines (15-37-117). **Vintage warning:** two
versions of 15-35-108 are in force, one terminating 2027-06-30 and one effective
2027-07-01, and subsections (3)–(5) step between FY2020 and FY2021 by their own
terms. Earlier MCA editions are **NOT VERIFIED — do not back-cast.**

**There is no coal or metal-mines analogue to the quarterly oil and gas
distribution letters.** Checked the publications index, the coal severance page,
the coal gross proceeds page and the metal mines page: zero document links on
each. **A trap:** the single "Fort Peck" hit in the Shared Revenue chapter is the
**town** of Fort Peck in Valley County, not the tribe.

---

## 8. Nevada — the strongest verified absence in the wave

Nevada's **Net Proceeds of Minerals Bulletin** publishes **named royalty
recipient × operator × mine × commodity × county, with dollar amounts** —
including geothermal at Stillwater, Dixie Valley and Brady. It is structurally
*exactly* the table this dataset wants.

**No tribe appears in any of eleven years.** And NRS ch. 362 contains **zero**
occurrences of Indian, Native American, tribal, reservation or colony.

> This is what a strong negative looks like: not "we could not find a source"
> but "we found the right source, it names recipients individually, and the
> tribes are not in it." (FY2016-17 is missing from the state's own page and
> that year is unverified.)

---

## 9. The remaining states

**Washington — MECHANISM, NO SERIES.** RCW 43.06.480: *"The governor is
authorized to enter into a timber harvest excise tax agreement with the Quinault
Nation."* RCW 84.33.0776 grants a credit against the state tax for a tribal tax
imposed under it. A genuine enacted mechanism naming **one** tribe. DOR's forest
tax page publishes county distributions and harvest statistics only. Whether the
agreement was ever executed is **NOT VERIFIED**.

**Wisconsin — MECHANISM, NO SERIES.** Wis. Stat. 70.395(2)(d)2m directs *"To any
Native American community that has tribal lands within a municipality qualified
to receive a payment under this section, an amount equal to $100,000 minus any
payments during that year…"* — a capped entitlement, not a share of production.
No recipient report was located and the Legislative Fiscal Bureau's 102-paper
index contains no mining-tax paper at all, consistent with the provision being
dormant. **Menominee Tribal Enterprises is unusable**: the only revenue figures
available are commercial aggregator estimates, which are modelled, not measured.

**Minnesota — NO MECHANISM.** Minn. Stat. 298.28 (taconite production tax
distribution), 298.75 and ch. 97A checked; no tribal recipient.

**Michigan — NO MECHANISM.** Six full-text MCL queries pairing "Indian tribe"
with resource terms returned zero against a positive control returning 76.
Michigan's tribal-state tax agreements list six taxes, none of them severance,
mineral or timber; MCL 324.51108(8) is an **exclusion**, not a payment. The
Great Lakes Fishery Commission workbooks carry **landings volume only, in
thousands of pounds, with no dollar column** — it must not be converted. CORA is
a five-tribe inter-tribal authority, not a named single entity.

**Texas — NO MECHANISM.** Tex. Tax Code § 202.353 sends one-fourth to the
foundation school fund and three-fourths to general revenue. Two recipients,
neither tribal. § 151.337 does name all three tribes but is a **sales** tax
exemption, out of scope. **Caveat:** `statutes.capitol.texas.gov` refuses
connections at the network layer, so the quote rests on the texas.public.law
mirror rather than the official host.

**Louisiana — NO MECHANISM.** La. R.S. 47:645 credits severance taxes to
*"the governing authority of the parish within which severance or production
occurs"*. All 37 sections of R.S. 47:614–647 fetched individually, zero tribal
hits. **A trap avoided:** "Coushatta", "Jena" and "Houma" hits in the Department
of Revenue annual report are **municipality** names in beer-tax tables, verified
in context.

**California — NOT CLOSED.** Recorded as unresolved rather than dressed up as a
finding. The CDTFA timber-yield-tax page returned HTTP 404 and the operative
Hoopa-Yurok text was never read — 25 U.S.C. 1300i-3 is **omitted** from the
Code, so Pub. L. 100-580 § 4 must be read in the Statutes at Large. The Hoopa
Valley Tribe self-publishes audited financials for FY2013 and FY2014 only, and
the FY2013 Statement of Activities does **not** isolate timber; it sits inside
Economic Development charges for services of $13,658,641. The one clean line,
*"California Revenue Sharing 1,100,000"*, is **gaming** and out of scope.

---

## Found, held, and worth more than a guess

### OSMRE abandoned mine land fee distributions — the best-looking source not built

SMCRA levies a per-ton reclamation fee on coal production (30 U.S.C. § 1232) and
distributes half to states and tribes with approved programs. OSMRE publishes it
as a table **naming the Crow Tribe, the Hopi Tribe and the Navajo Nation with
dollar amounts, every fiscal year FY2016–FY2026 without a gap.** Named entity,
measured amount, continuous series, federal publisher.

**It is held, because the text layer is offset by one row.** Measured on FY2022:

```
Wyoming        No   3,059,874.30   -            241,490.23    3,059,874
Crow Tribe     No           974.31 (776,388.22) 3,059,874.30          -
Hopi Tribe     Yes    776,388.22   -                  974.31    799,809
Navajo Nation  Yes    799,808.95   -                       -    812,928
```

Read naively, the Hopi Tribe received $799,809. Read correctly, **$799,809 is
the Navajo Nation's distribution printed on Hopi's line**, and $776,388.22 is
Hopi's collection printed on Crow's. Every number is individually plausible and
every attribution is wrong by one row.

The MMS layer in the first wave was publishable because the document printed
subtotals that let a de-skew be **proven** right. These tables print no per-row
check, the eleven files are not laid out alike, and FY2018 is scanned OCR whose
text contains `StatefTribe` and `Ir."mr""r't~:`. An unverifiable de-skew that
assigns real dollars to the wrong tribe is exactly the false attribution this
project refuses.

All eleven PDFs are retrieved into `data/raw/resources/_federal/osmre/aml/` and
the hazard is queued. **This is the highest-value unbuilt lead in the wave.**

### Navajo Tax Commission — the same hazard, same answer

`tax.navajo-nsn.gov` publishes collections by tax type FY2012–FY2024, including
Oil & Gas Severance. **`pdftotext` shifts every row label down by one**, so an
automated parse silently publishes Business Activity figures as Possessory
Interest. The source also carries a genuine defect: the FY2024 Sales–Non-Retail
and Sales–Retail values are **swapped in the published PDF**. Must be read
visually. **The `?ver=` token in the URL is load-bearing** — strip it and the
host returns 404. **Do not cite `navajotax.org`**, which has been lost to a
squatter serving generic tax-filing spam; it was legitimate through Dec 2022.

### Do not spend time on tribal government financial pages

Measured across this wave and the parallel recipient-side sweep: the yield is
approximately zero. Southern Ute, Ute Mountain Ute, Eastern Shoshone, Northern
Arapaho, Hopi and Crow publish no resource revenue figure. Where audited
statements exist they are constitutionally restricted to members, or suppressed
under the Single Audit tribal opt-out with the PDFs returning HTTP 403.

**The exception that proves the rule is the Osage Minerals Council**, and it is
an exception because the Council is a *minerals* body with a statutory duty to
the headright holders, not a tribal government reporting its general fund.

---

## Citations I had to correct

| Claim | Verdict |
|---|---|
| BIA/ONRR reporting on the Osage may be more specific than the national aggregate | **REFUTED.** `Osage` appears zero times in every ONRR bulk file held. The mineral estate's tribal ownership buys nothing against the suppression. |
| Colorado has state severance-tax sharing with the Southern Ute analogous to Utah's funds | **REFUTED.** The enacted instrument (C.R.S. Title 24 art. 61) **exempts** the Tribe from state severance tax and has the Tribe pay **La Plata County**. It runs the opposite way. |
| The 85% Wind River per-capita share, cited to 25 U.S.C. § 612 | **STALE CITE.** § 612 is **omitted** from the Code. Cite P.L. 85-610, 72 Stat. 541 § 2 — and the rate was **two-thirds** before ~1959-01-01. |
| New Mexico's tribal royalty deduction is in one article | **INCOMPLETE.** It is in three: NMSA 7-29-4.1, 7-31-5 and 7-32-5. |
| The Hopi general fund was ~80–85% coal-royalty dependent | **NOT VERIFIED.** News and advocacy sources only. Asserted nowhere in this build. |
| *Fletcher* / 10th Cir. "$7,975 per quarter per headright" | **NOT A MEASUREMENT.** It is an average, and it is not built. |
| Westmoreland's "$3.1 million yearly average" for Crow coal | **MISATTRIBUTED.** That is **company** income, not a payment to the Tribe. |
| NMFA's "Jicarilla Apache Nation (General Revenues) 3,085,750" | **MISCLASSIFIED.** A debt-service loan payment, not oil and gas revenue. |
| `revenuedata.doi.gov` | **MOVED.** 308-redirects to `revenuedata.onrr.gov`. |
| `mtrevenue.gov/publications/` | **MOVED.** Now 403s; the live index is `revenue.mt.gov/resources/index#publications`. |
| `navajotax.org` | **LOST.** Now a squatter's content farm. The Commission is at `tax.navajo-nsn.gov`. |

---

## A defect fixed in the first wave's output

`data/clean/resource_revenue.csv` carried **12 duplicate primary keys**. The MMS
builder constructed ids as `comp[:4].upper()`, and **both** `Other royalties`
and `Other revenues` truncate to `OTHE` — six fiscal years and five calendar
years each collapsing two distinct rows onto one key, invisible to anything that
keys on the id.

A prefix of a label is not an identifier. The generator now uses a declared
`MMS_COMPONENT_SLUG` map, and the 24 already-published rows were repaired **in
place** — deterministically, by reading each row's own recorded component name
out of `source_record_id` — rather than by a full rebuild, because a rebuild
from raw would have deleted 185 ANCSA rows written by another layer from sources
script 83 does not read.

`append_ledger` now **refuses to write** if any event id repeats across the whole
file. **10,474 ids, all unique.**

---

## How this layer writes

`--more-states` **appends**. It reads the published ledger, replaces **only**
rows whose event id starts with a prefix this layer owns
(`RRE-OK-`, `RRE-CO-`, `RRE-NM-`, …), and carries everything else through
untouched and unreordered. Verified: two consecutive runs produce a
**byte-identical** file, and a no-op run left all 10,308 pre-existing rows intact
with matching SHA-256.

A full `--all` run still rebuilds from raw, and that is correct only while
script 83 is this file's sole author. **It no longer is.** A rebuild now
**refuses** if the published ledger carries any `source_system` this script does
not write:

```
REFUSING --all: resource_revenue.csv carries rows this script did not write,
and a rebuild from raw would delete them:
       185  ANCSA_7i_7j_annual_reports
```

That failure mode is the dangerous kind — the file would still look healthy
afterwards, just smaller — so it is a hard stop rather than a warning.

### Downstream, now stale

`docs/codebooks/12_resources.md` and `dist/12_resources/*.notes.json` are
generated by other scripts and do not yet describe this wave: two new
`aggregation_level` values (`per_headright_rate`,
`entity_specific_component`), two new `revenue_type` values outside the enum
(`total_reported_revenue`, `production_tax_paid_to_state`), a new `period_type`
(`payment_quarter`, `tribal_fiscal_year`) and three new `source_system` values.
**Regenerate them; do not hand-edit** — a number in a doc that is not recomputed
from the data is a claim, not a fact.

---

## Open leads, in order of value

1. **OSMRE AML** — positional (bbox) extraction or a hand transcription of three
   tribal rows × 11 years, gated on the page-1 "State and Tribal share" total.
2. **Navajo Tax Commission** — visual transcription, FY2012–FY2024.
3. **Navajo audited actuals** — the parser is shipped; harvest the remaining
   years from `dibb.nnols.org` into
   `data/raw/resources/new_mexico/cedar_navajo_audited_actuals.csv`.
4. **La Plata County ACFRs** — the Southern Ute annual compact payment under
   C.R.S. 24-61 art. 6.02. Blocked on a JavaScript document centre.
5. **California** — read Pub. L. 100-580 § 4 in the Statutes at Large.
6. **BIA forestry timber-by-reservation** — `bia.gov/bia/ots/forestry` 404s; the
   one remaining plausible route to named-tribe timber value for AK/WA/MN/WI/CA.
7. **Montana Secretary of State records request** — the Blackfeet agreement
   under MCA 18-11-107.
