# Methodology — Natural Resource Revenues

<!-- BEGIN GENERATED:IDENTITY -->

**`natural-resources` — Natural Resource Revenues.** Delivered as `dist/customer/natural-resources.csv`: **11,305 rows × 52 columns, 24.4 MB**, built from the flagship table `data/clean/resource_revenue.csv`. Shelf `pro`; sold through **Cedar Press**; on the Cedar Press storefront. Readiness **READY**. [measured 2026-09-02 from the delivered file]

> **This block and Appendix M at the foot of this paper are GENERATED** by `code/1143_methodology_papers.py` from the delivered file itself, on every build — the same reason the codebooks are generated. Do not hand-edit either; the next build overwrites them.
>
> Everything between `<!-- BEGIN EDITORIAL:natural-resources -->` and `<!-- END EDITORIAL:natural-resources -->` is **hand-written and preserved byte-for-byte** across rebuilds. Put prose there and nowhere else.
>
> This paper is **not** the codebook. `dist/customer/natural-resources__CODEBOOK.md` carries the grain, the folded-in tables and the per-column fill rates, and `__NOTES.txt` carries the same for a person. This paper says how the dataset came to exist and why you should believe it.
>
> Generated 2026-09-02. `py -3 code/1143_methodology_papers.py verify` **fails** if the delivered file has moved since — see §M7.

<!-- END GENERATED:IDENTITY -->

<!-- BEGIN EDITORIAL:natural-resources -->
**`natural-resources`. `data/clean/resource_revenue.csv`, 11,305 rows,
twelve source systems, 1880 to 2026-07.** [measured 2026-09-02]

*Written 2026-09-02. This is the methodology record: what was pulled and from
where, how the rows were made, how entities were attributed, what was decided
and why, what the known limits are, and how often it has to be re-pulled. It is
not the product copy (`docs/datasets/_descriptors.json`) and not the codebook
(`docs/codebooks/`).*

**A note on the figures.** `[measured]` means the figure was re-counted from
the live file with `csv.reader` on 2026-09-02. `[from the record]` means it
came from a build log or docstring without independent measurement. Where a doc
and the data disagreed, the measurement won; the disagreements are listed at
the end.

**Readiness: BLOCKED**, on one named blocker: *"C4 — only 25% of entity-bearing
rows carry a Cedar id, and every record in this dataset HAS an entity subject,
so this is unresolved work, not scope."* [measured —
`docs/DATASET_READINESS.md`, regenerated 2026-09-02] **§3 argues that the
blocker is measuring the wrong column**, and states the honest denominator.

---

## The fact that shapes everything: 87% of these rows are aggregate BY LAW

**Interior releases Native American extraction and revenue only in aggregate.**
Not as a matter of policy, not as a backlog — as a matter of statute. From
Interior's own Natural Resources Revenue Data site
(`revenuedata.doi.gov/how-revenue-works/native-american-revenue/`), quoted
verbatim:

> "For all Native American land, the federal government only releases natural
> resource extraction and revenue information **in aggregate**. Specific data
> on Native American revenues are confidential and proprietary. **Treaties,
> laws, and regulations dictate what data the government can release.**"

and, on the allottee mixture:

> "Individual mineral owners (allottees) may request that payments be made
> directly to them… **The amounts paid for extraction on tribal lands vary by
> tribe and are not available to the public.**"

**This is verified at the data level on every build, not taken from site
copy.** In ONRR's monthly revenue file, **0 of 9,277 Native rows carry any
geography** — `State`, `County`, `FIPS Code` and `Offshore Region` are blank on
100% of them — against **99.8% of Federal rows in the same file**. Interior's
own disbursement bucket is literally named *"Native American tribes and
individuals."*

**The 87%, two compatible ways — say which one you mean:**

- By **`aggregation_level`**, the column that marks it:
  `national_aggregate` **9,791 = 86.61%** · `entity_specific` 779 (6.89%) ·
  `per_headright_rate` 508 (4.49%) · `state_aggregate` 167 (1.48%) ·
  `entity_specific_component` 60 (0.53%). Adding state aggregates gives
  **9,958 = 88.08%**.
- By **source system**, which is how the shipped source doc computes it: ONRR
  monthly 9,277 + ONRR FY disbursements 157 + MMS calendar 315 + MMS fiscal 42
  + Montana state-aggregate letters 49 = **9,840 = 87.04%**.

[measured, both]

**Aggregation here is the statute, not a shortcoming.** No row is aggregate for
want of effort, and none was left unattributed because a resolver failed.

The suppression also produces a trap inside the file: from FY2015,
`fiscal_year_disbursements.csv` carries **11 to 15 rows per year that are
identical in every published column**, differing only in amount — because **the
dimension separating them was suppressed too.** A de-duplication on the visible
key would discard **134 rows and $10,789,042,639.73.**

---

## 1. Sources

Twelve source systems, all present in `resource_revenue.csv` [measured by
`source_system`]:

| source system | rows | coverage |
|---|---:|---|
| `ONRR_NRRD_monthly_revenue` | 9,277 | 2003-01 – 2026-07 |
| `OMC_headright_payment_history` | 508 | **1880 – 2026-Q2** |
| `ND_State_Treasurer_tax_distribution_search` | 492 | 2008-09 – 2026-08 |
| `MMS_MRM_american_indian_revenues_calendar` | 315 | CY1925 – CY2000 |
| `ANCSA_7i_7j_annual_reports` | 185 | FY2014 – FY2025 |
| `ONRR_NRRD_fiscal_year_disbursements` | 157 | FY2003 – FY2025 |
| `UT_COBI_fund_financials` | 118 | FY1996 – FY2025 |
| `OSMRE_AML_fee_based_grant_distribution` | 76 | FY2013 – FY2026 |
| `OMC_quarterly_newsletter` | 68 | 2014-Q3 – 2022-Q1 |
| `MT_DOR_county_oil_gas_distribution` | 49 | 2014-Q1 – 2026-Q1 |
| `MMS_MRM_american_indian_revenues` | 42 | FY1994 – FY2001 (FY1997 held) |
| `OSMRE_AML_IIJA_grant_distribution` | 18 | FY2022 – FY2026 |

### What was deliberately not used

| refused | reason |
|---|---|
| `estimated_gross_production_value`, `estimated_royalty`, any `modeled_amount` | **Volume × price is a model.** Owner: *"id rather someone else estimate revenue than us"* |
| **Per-tribe splits of the federal aggregate** | Interior releases Native revenue only in aggregate, by law. **Dividing it is fabrication** |
| ONRR production volumes | Retrieved and held raw — there is nothing attributable to attach them to |
| ONRR calendar-year revenue file | The same dollars as the monthly file at a coarser grain. Publishing both would double the ledger. **Retained as the reconciliation check** |
| Land status inferred from a map | A well inside a reservation boundary is **not** evidence of tribal mineral ownership. Trust against fee **is** the question — and in North Dakota it is *fractional*, not binary: each spacing unit carries a Trust Ratio and a Non-Trust Ratio |
| North Dakota's 80/20 split applied post-2019 | It governs **only wells spudded after 2019-06-30, for the life of the well.** Every post-2019 payment is a blend |
| Utah fund deposits as "tribal royalty income" | Utah Code 63N-24-703(4): the fund *"consists of state severance tax money to be spent at the discretion of the state"* and *"does not constitute a trust fund"* |
| Utah Tax Commission severance figures | Column order shifts between report vintages; extraction ambiguous. Held raw |
| MMS FY1997 | Its own components miss its own printed subtotal **by $10.** Held by the gate |
| Bureau of Trust Funds Administration ($8.8B, 4,300 tribal accounts, 414,000 IIM accounts) | Interior's own words make royalties **one of six ingredients**, alongside judgments, settlements, land-use and investment income. **Scale context, not a series** |
| BIA NIOGEMS | An internal BIA system, about 50 tribal users across 8 reservations. **A partnership target, never a cited source.** The four `niogems_*` columns are **blank on all 35 asset rows by construction** [measured], so access would be a merge rather than a rebuild |
| BIA LTRO allotment tracts, IIM account detail | Not public **and not sought** |
| **`pdftotext -layout`** | *"not safe on any document in this collection."* It fabricated a one-row offset on the MMS calendar table **and** on the OSMRE tables **in opposite directions**, with every number individually plausible. Use `pdfplumber` word coordinates |
| North Dakota DMR well index, Montana BOGC | Subscription-gated — **and neither records mineral ownership**, so neither could establish trust against fee anyway |
| Tribal bonds via MSRB EMMA | Terms of Use forbid scraping and forbid building a database to be sold; and *"tribal debt in the public market is a gaming instrument"*, so the register was scoped out of the resource ledger |
| Cobell ($3.4B), tribal trust settlements (~$1B), Osage ($380M) | *"a figure I cannot quote from a retrieved document does not exist"* — the search budget was exhausted and `justice.gov` returned 403 |
| Terms-restricted tribal directories | Colville, CTUIR/Umatilla, Yakama, Chickasaw, NANA/Akima, Southern Ute, Forest County Potawatomi, Stillaguamish — excluded across Cedar by every route. **See §6** |

---

## 2. How the rows were made

- **`code/83_build_resource_ledger.py`** — the ONRR, North Dakota, Utah and
  Montana legs, then `--more-states` for the fifteen-state sweep and Osage.
- **`code/84_resource_recipient_side.py`** — the ANCSA §7(i)/§7(j) recipient
  side.
- **`code/135_build_resource_assets.py`** — the asset layer.
- **`code/137_link_resource_revenue_entities.py`** →
  **`code/149_apply_resource_entity_links.py`** — the entity-link
  proposal/apply pair.
- **`code/108_build_tribal_tax_bases.py`**, **`code/113_build_nd_severance.py`**,
  **`code/116_build_nd_tribal_taxes.py`** — the tax layer.
- **`code/07_parse_ancsa_ceiling.py`** (roster); the ANCSA STAR portal harvest
  under `code/ancsa_portal/`.
- **`code/814_gaming_nr_grain_and_conservation.py`** — the twelve-source
  conservation ledger.

> ⚠ **Three docstrings point at script numbers that do not exist.**
> `docs/RESOURCE_ASSETS_BUILD_LOG.md` cites `code/130_build_resource_assets.py`
> — `code/130_*` is the Section 106 builder. `code/137`'s docstring opens
> *"Cedar Press - 133"* and `code/149`'s opens *"Cedar Press - 146"*. Anyone
> following a docstring number to a file lands on the wrong script.

### Row conservation

**421,590 source readings → 11,305 published rows**, with a **named** refusal
reason for every one. The two largest are
`rejected:onrr_land_class_is_not_Native_American` (401,624) and
`rejected:onrr_disbursement_fund_type_is_not_Native_American` (8,280) — i.e.
**the publisher's own Land Class column is the filter, and nothing is
inferred.**

---

## 3. How entities were attributed

**The same shared resolver** — `resolve_entity` from
`code/33_apply_party_rulings.py`. No second matcher exists in this collection.

**Attribution routes through a PARTY TABLE, deliberately.**
`resource_parties.csv` holds **1,938 rows** keyed by `(object_type,
object_id)`: `revenue_event` 1,897 plus `asset` 41. `relationship` [measured]:

| relationship | rows | means |
|---|---:|---|
| `parent_native_entity` | 1,321 | **ownership** |
| `counterparty` | 498 | not an owner |
| `serves_native_entities` | 119 | **service, not ownership** — Utah's funds |

**A single `recipient_entity_id` column on a revenue row would have to pick one
of the tribal government, the allottees, the enterprise, the operator, the
lessee and the trust account — and would assert a false exclusivity.** One
payment routinely involves several at once. **An operator is never an owner:**
`operator_entity_id` is **0% populated on all 11,305 rows, and that is
correct** — Teck Alaska, Peabody Western, Westmoreland and Donlin Gold are not
spine entities and must never be written as though they were. Non-Native payers
carry a `PAYER-` prefix (`PAYER-US-BIA` 508, `PAYER-STATE-ND` 492,
`PAYER-US-ONRR` 157, `PAYER-US-OSMRE` 94) precisely so a downstream join cannot
treat the State of Oklahoma as a Native entity. [measured]

**19 distinct entities are touched** across `resource_parties` — the 12 ANCSA
regionals plus MHA Nation, Osage Nation, Navajo Nation, Crow, Hopi and Uintah
& Ouray — with `entity_is_native = 1` on 1,440 rows and 0 on 498. [measured]

### The evidence gates

**The ANCSA layer.** Every declared fact must verify against the actual
document text: `quote_type = verbatim_sentence` (the whole sentence must
whitespace-normalise-match) or `table_reading` (the label **and every printed
number** must appear). **134 facts declared, 134 verified, 0 refused** — one
initially failed on a U+2019-versus-ASCII apostrophe and was corrected. The
verbatim quote travels in `beneficiary_note`.

**The asset layer.** An anchor regex must match **exactly one sentence in
exactly one candidate document** — zero matches is missing, more than one is
ambiguous, and **both refuse** — and every declared number must appear
literally in that sentence. 16 facts were refused on the first run; final
**35 declared, 35 verified, 0 refused**, byte-identical on re-run. `confidence`
**A 30 / B 5**. [measured]

**Confidence on revenue: A 10,815 / B 490.** [measured] B is used where a
figure is printed once with nothing to check it against — the 26 annual-only
Osage years 1880–1905, and the 30 pre-1907 rows demoted wholesale.

### The refusal that defines the Osage layer

**"Holders of Osage headrights (individuals)" is not the Osage Nation.** The
Nation's own auditor states the distributions *"are not received by the
Nation."* So the 508 headright rows carry a **class, never a person**, and
`aggregation_level = per_headright_rate` makes the non-additivity
machine-visible.

The Council prints a divisor of **2,228.97393 headrights**, and **it is used
only as a check and never as a multiplier** — multiplying would manufacture an
aggregate, and dividing would approach an individual's income.

### The blocker is measuring the wrong column

`recipient_entity_id` is populated on **705 of 11,305 rows (6.24%)**, 17
distinct values [measured] — but **9,516 unlinked rows carry no recipient name
at all**, because the publisher suppressed it. So 11,305 is not the honest
denominator.

**The closeable universe is about 966 rows (9.2%). Counting
`resource_parties`, the entity-attributed share is 1,405 rows (12.4%), and
0 rows are unattributed for want of a resolver.**

---

## 4. Decisions that shaped the data

### `aggregation_level` is load-bearing, and the naive sum is meaningless

**A `national_aggregate` row already contains the `entity_specific` money.**
Sums that must never be added together [measured]: national_aggregate
$42.84B + entity_specific $8.00B + entity_specific_component $96.9M +
state_aggregate $35.2M + per_headright_rate $1.11M = the naive
**$50,973,259,111.49**.

And **within the aggregate itself**, ONRR monthly ($19.09B) and ONRR fiscal-year
disbursements ($18.25B) are the same dollars at two stages, while MMS calendar
(CY1925–2000) overlaps MMS fiscal (FY1994–2001).

### Negatives and zeros belong in every total

**1,770 of 9,277 ONRR monthly rows (19.08%) are negative, summing to
−$1,087,243,415.14**; the largest single row is −$71,602,394.93 (2021-08 oil
royalties). **350 rows are exactly zero** — an assertion, not a blank. Montana's
49 quarters all read *"Tribal Distribution: $0.00"* and are published as
measured statements. [measured]

### Two grains were reconciled before one was dropped

ONRR monthly against ONRR calendar-year agreed to **$0.00 across 23 shared
years** on the 2026-08-06 vintage, and monthly was published because it is
finer and reaches further. **On the 2026-09-01 refresh they no longer agree** —
CY2024 differs by $25,202.49 and CY2025 by $1,302.57 — filed as
`RESOURCE:ONRR:GRAIN_DISAGREEMENT`. Only the two most recent years move, which
is what a rolling restatement looks like.

### The MMS de-skew was gated, not trusted

The MMS PDFs have a text layer offset vertically by exactly one line — *"the
value printed beside `Coal` belongs to `Royalties:`"* — producing numbers that
are individually plausible and systematically wrong. The parser de-offsets and
then **refuses to publish anything that fails three checks**: a per-year
cross-foot (76/76), a per-column printed total (6/6), and exact agreement with
an **independent hand transcription** of CY1996–2000 (30/30). The 76 annual
totals sum to the document's own printed grand total of **$4,088,925,436**
exactly. FY1997 was **held** on a $10 internal inconsistency in the source.

### OSMRE: the refusal was right and the diagnosis was wrong

An earlier wave held eleven PDFs believing the text layer was offset, and
proposed a de-skew. **The offset was a `pdftotext` artefact, and the proposed
de-skew was also wrong** — `pdfplumber` reads the same page correctly with no
de-skew at all. **The refusal to publish an unproven de-skew is why a false
attribution never shipped.** Five checks now gate every tribe-year, and
**FY2018 Crow fails** (a scanned OCR prints 1,180,946 where 1,242,983 − 82,037
= 1,160,946) and is held.

### The pre-1907 Osage correction: a fix by field, not by deletion

Dropping the coverage floor to 1880 published 30 rows stamped with the modern
characterisation. **The Osage Mineral Estate was created by the 1906 Osage
Allotment Act**, and the first Osage oil lease of any kind was the **Foster
lease, 1896-03-16**. So for 1880–1895 Cedar was asserting oil-and-gas revenue
from an estate that did not exist.

Fixed field by field: `commodity` blanked; `resource_type = not_stated` (not
`mixed`, which would assert a mixture of minerals); `revenue_type =
trust_disbursement`; `land_status = not_stated` (`trust` is an anachronism
before the Act that created the trust); `confidence` demoted to **B on all
30**. The 16 rows for 1880–1895 additionally carry, verbatim: *"THERE WAS NO
OSAGE OIL LEASE OF ANY KIND IN THIS YEAR… A petroleum characterisation of this
payment is not merely unsourced — it is impossible."*

**Row count unchanged at 11,305 — the house rule is flag, never delete.**
Whether those 30 rows belong in the table at all is an **open owner decision**:
the BTFA precedent cuts against, and one-continuous-series cuts for.

### North Dakota: the blend cannot be decomposed, and does not need to be

The Legislative Council publishes **both legs of the ratio** monthly, so the
effective on-reservation share is *measured* rather than assumed: 50.00%
(2015-17 and 2017-19, reproducing the uniform 2013 regime to four significant
figures out of two independent series) → 51.20% → 53.17% → 54.14% →
**55.48%** (2025-27 to date). The rise forces a **published bound** on vintage
mix: `post_2019_share >= (observed − 0.50) / 0.30`.

**No point base is published**, and the reason is a fourth distinct way rate
inversion fails: the gross production tax **pools two incompatible units** —
oil at 5% of gross value in dollars, gas at an indexed rate per mcf. (The other
three, recorded elsewhere in Cedar: a marginal base read as flat, a graduated
rate read as flat, and receipts lagging obligations.)

### One deflator, and a deliberate divergence from contracting

The BEA GDP implicit price deflator, same 2025 base as
`40_build_prime_contracts.py`; **no second deflator was created.** The
divergence: script 40 falls back to 1.0 for an unknown year, which is safe
there. This ledger runs to 2026 (no annual index yet) and back to 1880, so
**`amount_usd_real2025` is blank on 1,048 rows and never 1.0.** [measured] A
1.0 would silently assert that an 1880 dollar is a 2025 dollar.

### Refusals in the tribal debt layer

**Mislabelling a rating-action date as an issue date was refused.** *"Rating
actions are excellent for what and how much, and poor for when."* Ten named
value traps were refused with it — undrawn revolvers, refinanced balances,
accrued-interest-plus-principal, semi-annual interest payments, *"total rated
debt affected"* — and a whole new trap class was recorded: **a rating action's
headline is a launch size, not a settlement size.** Choctaw 2001 was rated
$150M and priced $200M; Little Traverse 2005 was rated $195M due 2013 and later
described as $122M due 2014. **No row was written at either figure.**

---

## 5. What a buyer may total

- **Never sum across `aggregation_level`.** The naive total is
  $50,973,259,111.49 and it double-counts by construction.
- **Never sum ONRR monthly with ONRR fiscal-year disbursements** — the same
  dollars at two stages. **Never sum MMS calendar with MMS fiscal** — they
  overlap CY1994–2000.
- **`per_headright_rate` is a RATE, not an amount.** Never multiply it by the
  headright divisor.
- **Negatives and zeros stay in.** A negative is a correct restatement and a
  zero is an assertion.
- **`resource_assets` is not money** — it is a 35-row register of physical
  assets with a verified anchor sentence each.
- **The ANCSA §7(i)/§7(j) directions are separate series and must not be
  netted.** `ancsa_7i_revenue_sharing_net_of_7j` 92 ·
  `ancsa_7i_revenue_sharing` 43 · `ancsa_7j_redistribution` 35 ·
  `ancsa_7i_7j_obligation_combined` 7. **The same dollars appear in both the
  payer's and the receiver's report**, and **8 conflicts are recorded rather
  than resolved** — NANA FY2023 at $96,882K against $143,609K; Chugach's exact
  2:1 gross/net pair.
- **`tribal_resolution_financings.csv` has no money column at all**, and
  `nigc_declination_cross_reference` exists precisely so that an authorisation
  and an NIGC review of one transaction are not counted as two.

---

## 6. What was excluded on purpose

> **SUPERSEDED 2026-09-02 by owner ruling** (`docs/PUBLICATION_POLICY.md`, `TERMS-OWNER-RULING-2026-09-02`): a tribal website's terms language no longer blocks harvest, and all eight are released for harvest of **their own public pages**. The exclusions below are kept as the *observation* of what each publisher stated - and as the worklist the ruling creates. Still binding, none of them a terms question: technical access controls; a natural person's data apart from their public role (the business row may be harvested, `owner_name_raw` / `email` / `phone` / `address_raw` may not be published); EMMA/MSRB + CUSIP Global Services, a third-party licensor; Casino City and D-U-N-S.

~~Sources marked `TERMS_STATED_RESTRICTIVE` are excluded by **every** route,~~
including a harmonised derivative: **Navajo, Confederated Colville,
Confederated Yakama, CTUIR / Umatilla, The Chickasaw Nation, Forest County
Potawatomi, Southern Ute, NANA Regional, Stillaguamish** — nine entries in
`review/tribal_vendor_list_registry_2026-08-26.csv`, each carrying the verbatim
quote that justifies it, with `consent_status = UNRESOLVED` on all 359 registry
rows. [measured]

**The exclusion is SOURCE-scoped, not ENTITY-scoped.** **NANA has 35 rows in
`resource_revenue.csv`** [measured] — every one from
`ANCSA_7i_7j_annual_reports`, retrieved from the **State of Alaska's** STAR
portal (`portal.akdbsstar.us`), where the filings are **mandated by AS
45.55.139**, not from `nana.com`.

> **An open boundary worth stating rather than leaving implicit.** Those
> filings are still the corporation's own publications, and
> `resource_revenue.csv` is not in `cedar_codebook.TRIBAL_SOURCE_RESTRICTED_FILES`
> — the gate covers only the four `tribal_certification_*` staging files. The
> reading that reconciles it is that the NANA restriction attaches to the
> **company directory** on `nana.com`, not to a securities filing the State of
> Alaska compels and publishes. That reading is coherent and **it is written
> down in neither document.** It should be settled explicitly.

**Asking is the route back in; a cleverer scrape is not.**

---

## 7. Known limits

| limit | measured |
|---|---|
| Aggregate share | **9,840 of 11,305 (87.04%)** by source system; **9,791 (86.61%)** by `aggregation_level` |
| Entity keying | `recipient_entity_id` **705 (6.24%)**, 17 distinct; `cedar_uid` 705; **19 distinct entities** across `resource_parties` |
| `operator_entity_id` | **0 of 11,305 — correct, not a gap** |
| `land_status` | `not_stated` **10,641** · `trust` **664** (only Utah and post-1906 Osage) |
| `period_start` blank | **492 rows** — the whole North Dakota series, whose `period_type` is `payment_date_only`. **There is no period end and none should be invented** |
| No volume, no price | The table has `commodity`, `product` and `amount_usd` and **no production volume and no price.** ONRR publishes monthly production volumes in the same system and they were not pulled. **A royalty figure with no volume cannot distinguish a price collapse from a production collapse** — the first question an energy analyst asks. Volume is acquirable from a source already in use; unit price is genuinely not published |
| `resource_assets` | **35 rows**, 41 party links, 17 entity ids; `land_status` ancsa_fee 30 / tribal_trust 4 / not_stated 1; **all four `niogems_*` columns blank by construction** |
| `resource_asset_source_coverage` | 18 findings: WITHHOLDS 7 · PUBLISHES 4 · NOT_CHECKED 4 · NOT_FOUND 3 |
| `resource_parties` key | `party_link_id` is **not unique — 1 collision**, already declared in the contract |
| `tribal_tax_bases` | **1,712 rows, and it is a North Dakota table**: ND 1,640 · WA 29 · NM 21 · MT 10 · MI 10 · OK 2. `MOTOR_FUEL` 939 · `SEVERANCE` 426 · `TOBACCO` 296 · `RETAIL_SALES` 28 · `ALCOHOL` 13 · `OTHER` 10. `derived_taxable_base` is populated on **779 rows, all gallons**, and is **empty on all 426 SEVERANCE rows** for three independently stated reasons. **Washington holds per-tribe fuel gallons and may not publish them** — an RCW-quoted exemption on all 25 fuel rows |
| `nd_severance_allocation` | **7 rows.** ND-ALLOC-003 and ND-ALLOC-004 are **both in force today** — reading `superseded_by` as an end date is the error the file exists to prevent |
| `tribal_bond_issuances` | **29 rows, 10 issuers. `cusip` blank on 29 of 29** — the market key of a bond is absent, and that is for whoever can buy the CUSIPs. **`issue_date` blank on 28 of 29**; the one populated value is `2021-01-26`, Mohegan's second-lien closing, quoted verbatim from a Moody's action. `issuer_entity_id` **blank on all 29**. `rating_agency` = Moody's on **all 29** — single-source. **Nothing here is a time series** |
| `anc_ceiling_roster` | **196 rows** (village 182 / regional 13 / urban 1). **`uei` and `cage_code` blank on all 196**; `confidence_tier = C` on all 196; the single source is **a law firm's list, not a government roster**; 190 resolved / 6 unresolved |
| `ancsa_filings_index` | **19,269 rows over 60 corporations. `filing_date` parses to a year on 0 rows.** `downloaded = yes` on **251 of 19,269 (1.3%)**. **94.3% is proxy material**; only **609 are annual reports.** Portal coverage is **60 of the 196-entry roster (31%)**, and Alaska HB126 (effective 2026-06-25) narrowed the filer population further |
| ANCSA §7(i)/§7(j) | **185 rows, 14 recipients, FY2014-03-31 – FY2025-12-31, $4,681,122,972** |
| **Village corporations** | **173 in the spine, and zero are attributed a §7(j) amount.** No regional's report names which village received what. Structural, and **the single largest named-entity gap in the collection** |
| Legally closed states | **New Mexico** (NMSA 7-29-4.1, 7-31-5, 7-32-5, §7-1-8) and **Colorado** (C.R.S. 39-7-101(4) — disclosure is a petty offense). *The data exists and cannot be obtained* |
| The strongest **verified absence** | **Nevada.** Its Net Proceeds of Minerals Bulletin publishes named royalty recipient × operator × mine × commodity × county with dollars — exactly the table this dataset wants — and **no tribe appears in any of eleven years** |
| Row conservation | the 814 ledger covers `resource_revenue`; the other four builders (105, 108, 113, 135) are **uninstrumented** |

---

## 8. Refresh

| source | cadence / lag | state | what breaks if not re-pulled |
|---|---|---|---|
| ONRR NRRD monthly | **monthly**, ~6-week lag | ✅ current to 2026-07-31 | **"87% of these dollars name no tribe, and that is the LAW, not a backlog"** |
| ONRR fiscal-year disbursements | annual, ~3-month lag | FY2025; FY2026 closes 2026-09-30 | the reconciliation check against the monthly series |
| Osage headright history | **quarterly since 1906; annual before it** | ✅ 2026-Q2 | the 30 pre-1907 rows and their open scoping question |
| ND State Treasurer | monthly | 2026-08-21; source not re-probed since 2026-08-07 | **`period_type = payment_date_only` on all 492 rows — no `period_end` exists and none should be invented** |
| OSMRE AML (fee-based + IIJA) | annual, at appropriation | ✅ FY2026, with a **forward-dated `period_end` that is correct, not a defect** | **FY2010–FY2012 are scanned images, retrieved and held rather than guessed — do not re-fetch them** |
| MMS / MRM | ⛔ **retired — the agency no longer exists** | CY2000, where ONRR begins | nothing |
| MT DOR · UT COBI · ANCSA 7(i) · OMC newsletter | quarterly / state-FY / corporate-FY / **stopped 2022-03-31** | ✅ MT 2026-Q1 | **four cadences in one registry row. If any of these needs its own refresh date, split it out rather than averaging them** |
| ANCSA STAR portal | a filings queue — **allow 10 business days before concluding a document is missing** | index stale by ~4 weeks | the 60-name dropdown is expected to **shrink** after HB126 — **re-capture and diff it every run** |

[measured — `docs/REFRESH_CADENCE.json`, regenerated 2026-09-02]

---

## Stale claims found while writing this

1. **`docs/datasets/natural_resources_sources.md` says
   "`tribal_bond_issuances.csv` — every row carries `issue_date = 2021-01-26`
   … that is a placeholder."** **False.** Measured: **28 of 29 blank, and the
   one populated value is a sourced closing date** with a `date_basis` quoting
   Moody's *"on January 26, MTGA closed on a refinancing."*
   `docs/TRIBAL_DEBT_BUILD_LOG.md` said this correctly all along, and
   `docs/DATASET_CONTRACTS.md` already carries the corrected statement. **The
   named "defect" is the design.**
2. **`docs/DOC_CONTRADICTIONS_2026-08-26.md`'s ground-truth row for
   `resource_revenue.csv` says "10,482 rows · 734 recipient-linked |
   unchanged."** Measured **11,305 rows · 705 recipient-linked** — the file was
   rebuilt 2026-09-01. The arbiter is the document the project instructs
   everyone to believe over the build logs, so a stale row in it is the most
   expensive kind.
3. **`docs/WHAT_IS_MISSING.md` says `cedar_uid` is filled on "119 of 11,305
   rows (1.1%)."** Measured **705 (6.24%)**.
4. **`docs/RESOURCE_ASSETS_BUILD_LOG.md` cites a script that does not exist** —
   `code/130_build_resource_assets.py`. The builder is
   `code/135_build_resource_assets.py`, whose own docstring still opens *"Cedar
   Press 130"*; `code/130_*` is the Section 106 builder. The same renumbering
   drift appears in `code/137` ("Cedar Press - 133") and `code/149` ("Cedar
   Press - 146").
5. **`docs/RESOURCE_LEDGER_BUILD_LOG.md`'s header table is a generation
   behind**: 10,123 events / 7 source systems / 9,467 national_aggregate / ND
   489 payments at $3,125,453,109.56 / ONRR through 2026-06. Measured
   **11,305 / 12 / 9,791 / ND 492 payments at $3,144,235,826.73 / ONRR through
   2026-07.** The log's own banner flags three of these; the header table was
   not updated.
6. **`docs/datasets/natural_resources_sources.md` notes "820 rows not yet in
   `dist/`."** That is now closed — `dist` and `data/clean` both hold 11,305.
7. **The readiness blocker — "only 25% of entity-bearing rows carry a Cedar
   id" — is measuring `resource_revenue.csv` rather than
   `resource_parties.csv`.** Counting parties, the entity-attributed share is
   **1,405 of 11,305 (12.4%)** and **0 rows are unattributed for want of a
   resolver**; the closeable universe is about 966 rows, because 9,516 rows
   carry no recipient name to resolve. The blocker points at real remaining
   work, but its denominator implies the work is four times larger than it is.
<!-- END EDITORIAL:natural-resources -->

<!-- BEGIN GENERATED:MEASURED -->

---

# Appendix M — measured from the delivered file

*Generated 2026-09-02 by `code/1143_methodology_papers.py` from `dist/customer/natural-resources.csv`, read whole with duckdb and never sampled. Not from `data/clean/`, not from a build log, not from `MANIFEST.csv`. Where this appendix and a document disagree, **the delivered file is right** and `verify` prints the disagreement rather than smoothing it over.*

*Grain, folded-in tables and per-column fill rates are in `dist/customer/natural-resources__CODEBOOK.md` and are deliberately not repeated here.*

## M1 · Sources, as the delivered rows themselves record them

**`source_system`** — 11,305 of 11,305 rows populated, 12 distinct values:

| value | rows |
|---|---:|
| `ONRR_NRRD_monthly_revenue` | 9,277 |
| `OMC_headright_payment_history` | 508 |
| `ND_State_Treasurer_tax_distribution_search` | 492 |
| `MMS_MRM_american_indian_revenues_calendar` | 315 |
| `ANCSA_7i_7j_annual_reports` | 185 |
| `ONRR_NRRD_fiscal_year_disbursements` | 157 |
| `UT_COBI_fund_financials` | 118 |
| `OSMRE_AML_fee_based_grant_distribution` | 76 |
| `OMC_quarterly_newsletter` | 68 |
| `MT_DOR_county_oil_gas_distribution` | 49 |
| `MMS_MRM_american_indian_revenues` | 42 |
| `OSMRE_AML_IIJA_grant_distribution` | 18 |

**`source_url`** — 11,305 of 11,305 rows carry one. Hosts, by row count:

| host | rows |
|---|---:|
| `revenuedata.doi.gov` | 9,434 |
| `www.osagenation-nsn.gov` | 576 |
| `www.nd.gov` | 492 |
| `web.archive.org` | 371 |
| `portal.akdbsstar.us` | 185 |
| `cobi-ws.utah.gov` | 118 |
| `www.osmre.gov` | 80 |
| `revenue.mt.gov` | 49 |

**`fetched_date`** — 11,305 of 11,305 rows populated, 3 distinct values:

| value | rows |
|---|---:|
| `2026-09-01` | 10,805 |
| `2026-08-06` | 315 |
| `2026-08-05` | 185 |

### The terms rulings that bind this dataset

Quoted from `docs/PUBLICATION_POLICY.md`, which holds the rulings; this paper does not restate them from memory.

- **Owner ruling, 2026-09-02** (`<!-- BEGIN TERMS-OWNER-RULING-2026-09-02 -->`): *"So tribal websites, I actually don't care if they say it does scrape. Because if it's publicly available and you can scrape it, scrape it."* A tribal entity's own public pages may be harvested regardless of a terms statement. `source_terms_status = TERMS_STATED_RESTRICTIVE` on a Native entity's own site is now **a recorded observation, not a gate**.
- **Four things that ruling does NOT touch, and none is a terms question:** (1) technical access controls — nothing login-gated, no admin or staging paths, no exploiting a misconfiguration; (2) a natural person's data held apart from their public role — home address, personal email or phone, DOB, SSN/TIN; (3) non-tribal licensors — EMMA/MSRB bars redistribution of its output "sold or free of charge" and names "any manual process", with CUSIP Global Services as a second licensor; (4) proprietary identifiers — Casino City, D-U-N-S — held internally, never shipped.
- **A terms restriction is scoped to the SOURCE that stated it, not to the nation** (`<!-- BEGIN TERMS-SCOPE -->`), and it does not bind a third party's filing of the same fact.

## M2 · How the rows were built — the pipeline, in order

**One documented rebuild:** `py -3 code/build.py run natural-resources --execute`. `py -3 code/build.py plan natural-resources` prints the ordering below live; it is reproduced here so the paper stands alone.

The collection holds **10 tables**. Those with a named build stage, flagship first:

| table | rebuilt by | then enriched by (must run LAST) | status |
|---|---|---|---|
| `resource_revenue.csv` **(flagship)** | — | — | shippable |
| `ancsa_filings_index.csv` | `build_manifest_index.py` | `update_index.py` | shippable |

**A full rebuild and an in-place enricher on one file need an ordering, and the enricher must run LAST.** A `.bak_*_pre<script>` file sitting beside a table is the signal that an enricher has touched it since the last build. This has cost this project four reverts of one file in a single day.

The delivered spreadsheet is then assembled by `code/1137_customer_dataset_combine.py`, which folds supporting tables onto the flagship **only where the measured cardinality on the shared key is one**, reverts any join that moved the row count, and prefixes every joined column with its source table's stem. One-to-many tables contribute a count column instead of rows, so a money total cannot be multiplied by a join.

## M3 · How entities were attributed

Cedar keys every dataset to one identity layer. `cedar_uid` is permanent and never reused; the human-readable handle retires when an entity is reclassified, so **join on `cedar_uid`, never on the handle**. A compound handle is canonical, not broken — stripping a suffix to make a join work turns joinable rows into unjoinable ones while looking like a normalisation.

**Entity attachment in the delivered file:**

| key column | rows carrying one | distinct values | coverage |
|---|---:|---:|---:|
| `cedar_uid` | 705 | 17 | 6.2% |

**An unkeyed row is often the right answer, not a defect.** ADR-010 separates *"we could not identify the entity"* — a defect — from *"there is no single entity to identify"* — the correct representation. Coverage is measured against the *resolvable* denominator, not the row count.

### What `attribution_method` means **in this dataset**

`docs/schema/attribution_method_vocabulary.json`, declared 2026-09-02: *"`attribution_method` is three different columns sharing a name — a join method, an evidence provenance, and a name-match algorithm. Each table is gated against its OWN vocabulary."* Reading one table's sense into another is how a containment match came to key a dollar.

**This dataset carries no `attribution_method` column.** The identity evidence it does carry is measured below. Do not import another dataset's term list to interpret it.

**And a RULED METHOD IS NOT A POSITIVE RULING.** `attribution_method` says WHO decided; `confidence_tier` says WHAT was decided. All 317 `elijah_ruling` EIN rows in the ledger are tier **X** — *negative* — and a script that read "the method is in the RULED set" as "the answer was yes" published 317 owner *exclusions* as confident attributions. Standing detector: `py -3 code/293_lint_bug_classes.py`. [from the record — `START_HERE.md`, defect class 1b]

### Every identity, tier and method column, measured

- **`record_scope`** — 5 distinct values: `indian_country` 9,791 · `entity` 1,287 · `native_serving` 118 · `unresolved` 60 · `geographic` 49

### The evidence tiers

| tier | what it means |
|---|---|
| **A** | an identifier (UEI, CAGE, EIN, declared parent UEI), or a human ruling. The only grade a dollar may be keyed on without corroboration |
| **B** | a strong name method with an independent corroborator, or inheritance from a tier-A parent |
| **C** | a weak method — containment, token subset — held as a candidate, not published as a fact |
| **X** | **refused.** A negative ruling. Never read as a confirmation |

**A tier is INHERITED from the source row, never assigned by the consumer.** The exactness of the KEY says nothing about the correctness of the LINK: 873 of 1,104 EIN rows in the ledger sit on 52 entities carrying five or more EINs each, and 821 are tier B via `need_v6`, which is 6.5% accurate and never publishes alone. [from the record — `START_HERE.md`, defect class 1]

## M4 · What is **not** in it, and why

**No row was withheld from this delivery.** Every row that passed the collection's own inclusion test is in the spreadsheet. [measured — `dist/customer/MANIFEST.csv`, `rows_withheld = 0`]

The row gate is `code/cedar_publication.row_ok`, applied identically by every publisher: a row is withheld if `publishable` is set to anything outside `{Y, y, 1, true, TRUE, blank}`, or if `source_terms_status` is outside `{SILENT, TERMS_STATED_NO_REUSE_RESTRICTION, blank}`. **A blank gate column means the gate was never evaluated for that row, not that it failed.**

Two families are refused as **COLUMNS** rather than as rows, by `cedar_publication.publishable_columns`, because the row is ours and the field is not: the proprietary identifiers (`casino_city_id` — Casino City Press; the D-U-N-S family — Dun & Bradstreet), and personal data held apart from a public role (`owner_name_raw`, `email`, `phone`, `home_address`, `personal_email`, `ssn`, `tin`, `date_of_birth`, `officer_name`, `contact_name`).

**The personal-data family became a column drop on 2026-09-02, and the change is worth understanding.** Until then it was a row gate only, and measured against the live tree that published **5 of the 587 rows** of `bia_tribal_leaders_directory.csv` — every row carrying a phone or an email was withheld whole — *and shipped the `phone` and `email` headers anyway on the five survivors*. Both halves of that were wrong. A tribal leader's name and office is a PUBLIC ROLE and belongs in the dataset; the phone number is the thing that must not travel. Dropping the field keeps 587 rows and publishes no contact data, where the row gate kept 5 rows and still advertised two contact columns. `row_ok` keeps its check as a **backstop**, for a personal field arriving under a name the list does not yet know. [from the record — the docstring of `cedar_publication.publishable_columns`, 2026-09-02]

### Known gaps — every line in `docs/WHAT_IS_MISSING.md` that names this dataset or its flagship

- **L617** *(under “`natural-resources` — `resource_revenue.csv`, 11,305 rows”)* — ## `natural-resources` — `resource_revenue.csv`, 11,305 rows

### Open issues — every line in `docs/KNOWN_ISSUES.md` that names this dataset or its flagship

- **L85** *(under “A2 · S3 · Three collections were documented as planning a script "not in the repository" — all three scripts exist”)* — `build_v2.py`, `lobbying` → `05_match_filings_v2.py`, `natural-resources` →
- **L544** *(under “C4 · S2 · Nine grain rulings only a human can make”)* — `contractors`, `gaming`, `lobbying`, `natural-resources`, `deals`,

## M5 · The money rules — which columns may be summed

Measured over the delivered file. **A sum printed here is the unfiltered arithmetic sum of the column and is NOT necessarily a figure a buyer may quote** — the fence below says which are and which are not.

| column | rows populated | distinct values | sum (unfiltered) | min | max |
|---|---:|---:|---:|---:|---:|
| `amount_usd` | 11,305 | 9,883 | $50,973,259,111.49 | $-71,602,394.93 | $1,146,119,618.68 |
| `amount_usd_real2025` | 10,257 | 9,455 | $58,433,978,189.20 | $-83,814,684.60 | $1,533,124,099.72 |

**Columns whose NAME looks like money and whose CONTENT is not** — measured, not assumed, because a name test alone promotes a 0/1 flag and a free-text field into a dollar column, which is the mistake `517.MONEY_HINTS` made:

- `revenue_type` — does not parse as a number. Not summable.

### The fence, quoted verbatim from `docs/MONEY_TOTALLING_RULES.md`

That document is authoritative on which columns may be summed. It is **quoted here, never re-derived** — re-deriving a totalling rule from the data is precisely the error it exists to prevent.

**`docs/MONEY_TOTALLING_RULES.md` states no one-line rule for `resource_revenue.csv`.** Where this dataset carries a money column and the rules document does not fence it, treat that as an open item, not as permission.

Marked blocks in that document that name `resource_revenue.csv`: `<!-- BEGIN ACQUIRE-BIA-ACREAGE -->`.

## M6 · Known limits, stated plainly

**Readiness: READY.** [measured — `docs/DATASET_READINESS.md`, regenerated by `py -3 code/518_dataset_readiness.py`]

| tables | grain | keys | duplicates | agg-unsafe | rebuild |
|---|---|---|---|---|---|
| 9 | 9/9 | 9/9 | clean | 0 | declared  |

The twelve-point contract a dataset is held to — grain declared and validated; keys and cardinality measured, not guessed; duplicates removed or the distinguishing dimension declared; entity attachment where the subject is an entity; every harvested row in a named disposition bucket; unresolved identity conflicts never shipping as definite facts; no double-counting path; one documented rebuild that does not destroy later enrichment; an update runbook another session can execute from the document alone; regression and semantic-diff gates over the outputs; column hygiene; and an inclusion basis on every row.

**3 columns are blank on every delivered row** and are kept deliberately. Dropping them would make the schema depend on which rows shipped, and a buyer diffing two deliveries would watch columns appear and vanish. Sparsity is a coverage fact. They are named in the codebook.

**Do not sell past the evidence.** Where this paper states a figure it was measured on the date stamped beside it, from the file named beside it. Where it states a decision it names who made it. Anything not stated here is not known.

## M7 · Fingerprint — what makes this paper stale

`verify` re-measures the four values below against `dist/customer/natural-resources.csv` and **exits 1 if any has moved**. A methodology paper is stale the moment its dataset is rebuilt, and a stale paper that cannot say so is worse than no paper.

```json
{
  "dataset": "natural-resources",
  "file": "dist/customer/natural-resources.csv",
  "bytes": 24432382,
  "rows": 11305,
  "columns": 52,
  "header_sha256": "7599f3bc40b1db610a4f6de6dd1bb22dbaf2cb630a1ea10566535218e4cc19a4",
  "measured": "2026-09-02"
}
```

Cross-check against `dist/customer/MANIFEST.csv`, which `code/1137_customer_dataset_combine.py` wrote at build time: it records **11305 rows × 52 columns**. The two agree.

<!-- END GENERATED:MEASURED -->
