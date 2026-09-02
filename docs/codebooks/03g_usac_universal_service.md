# Codebook — USAC universal service: E-Rate and Rural Health Care

*Four tables, 72,850 rows. Acquired 2026-09-02 by
`code/1120_acquire_usac_open_data.py` from `opendata.usac.org`, the Universal
Service Administrative Company's Socrata portal. No key for read.*

**Licence, verbatim from the asset metadata:** `license.name` = **`Public
Domain`**, `licenseId` = `PUBLIC_DOMAIN`, `attribution` = *"Universal Service
Administrative Company"*. Recorded in
`data/raw/external/usac/_manifest.json` so the permission is auditable
without re-fetching. `robots.txt` sets `Crawl-delay: 1` and disallows only
faceted `/browse?*` query strings; the `/resource/` SODA path carries no
directive and the pull sleeps 1.5 s.

## Why Cedar holds it

Universal Service Fund money reaches Indian Country through the FCC's
universal service mechanism, **not** through USAspending, so no existing
Cedar source sees a dollar of it.

And the E-Rate file does something no other source in Cedar's registry does:
it carries a **`tribal_type` the publisher assigned**.
`docs/PULL_DISCIPLINE.md`'s selection doctrine measured that an
identifier-seeded pull *"can never discover an entity we do not already
know"* — roughly three quarters of the entity universe is invisible to one.
`tribal_type` is a **TYPE FILTER leg**, and USAC did the Native
identification itself, on 53,847 rows.

---

# `usac_erate_tribal_commitments.csv` — 53,847 rows

**One row per (FCC Form 471 line item × recipient of service) that USAC
flagged with a `tribal_type`.**

> ### ⚠ THIS IS NOT ONE ROW PER SCHOOL
> **53,847 line items collapse to 2,752 entities — 19.6×.** One school
> appears once per funded line item per funding year, and a district filing
> for twelve services across nine years appears 108 times. Counting rows as
> schools overstates by an order of magnitude. The entity count is done once,
> in `usac_erate_tribal_entities.csv`.

> ### ⚠ THE MONEY COLUMNS ARE ALTERNATIVE RENDERINGS OF ONE MONEY
> Summing more than one of them double-counts. Measured on the full file:
>
> | column | all 53,847 rows | `Funded` rows only |
> |---|---:|---:|
> | `pre_discount_extended_eligible_line_item_costs` | $13,662,162,053 | $10,026,149,457 |
> | `post_discount_extended_eligible_line_item_costs` | $11,972,064,439 | **$8,791,223,114** |
> | `post_discount_applicant_share` | $1,690,097,615 | $1,234,926,344 |
>
> **`pre_discount = post_discount + applicant_share`**, exactly, to the
> dollar. The E-Rate discount is the federal share; the applicant share is
> what the school pays. **The committed federal figure is
> `post_discount_extended_eligible_line_item_costs`, and only on `Funded`
> rows.**
>
> ### ⚠ AND 8,358 ROWS ARE NOT COMMITTED MONEY AT ALL
> `form_471_frn_status_name`: **`Funded` 45,489 · `Pending` 3,940 ·
> `Cancelled` 3,909 · `Denied` 509.** Summing every row books **$11.97B**
> where the committed figure is **$8.79B** — a **36% overstatement**, of which
> a third is money that was *denied or cancelled*. Filter on
> `form_471_frn_status_name = 'Funded'`; on those rows
> `form_471_status_name` is `Committed` on all 45,489, so the two agree and
> either will do.

| Variable group | Notes |
|---|---|
| `ros_entity_number` · `ros_entity_name` · `ros_entity_type` | The recipient of service. `ros_entity_type`: `School` 42,812 · `Library` 10,880 · `Non-Instructional Facility (NIF)` 155. **`ros_entity_type` and `tribal_type` are different columns**: a `Library` can carry `tribal_type = Tribal Library` or `Tribal College/University Library`. |
| `tribal_type` · `tribal_type_verbatim` | **The publisher's Native flag, and the reason this table exists.** Four values, censused against USAC's own `$group` and reconciling exactly: `Tribal School` 42,967 · `Tribal Library` 10,862 · `Tribal College/University Library (for public use)` 17 · `Tribal College/University Library (for public use), Tribal Library` 1 (a comma-joined **multi-value** cell — parse it, do not treat it as a fifth category). `tribal_type_verbatim` is the same string kept unmodified as evidence. **Never blank on this file, by construction**; the script's `verify` exits 1 if it ever is. |
| `is_school_library_independent` · `ros_subtype` · `ros_status` | USAC's own sub-classification of the recipient. |
| `ros_physical_address` … `ros_physical_county` · `ros_latitude` · `ros_longitude` | The recipient's physical location. 36 states: `OK` 13,595 · `AZ` 9,891 · `NM` 7,615 · `UT` 5,425 · `SD` 3,708 · `AK` 2,883 · `CA` 2,117 · `TX` 1,892. |
| `ros_urban_rural_status` · `ros_square_footage` · `ros_number_of_full_time_students` · `ros_number_of_nslp_students` | Recipient characteristics as filed. `ros_number_of_nslp_students` is the National School Lunch Program count — a poverty proxy the applicant self-reports to set the discount rate, **not a census figure**. |
| `billed_entity_number` · `organization_name` · `organization_entity_type_name` · `org_*` | The **billed entity** — usually the district or consortium that filed, not the school that received. Two different entities on one row; do not conflate them. |
| `funding_year` | 2017–2026. **The file begins at 2017**, not at the programme's start: 1,636 rows in 2017 rising to 14,782 in 2023 then 10,742 / 5,141 / 4,688. **The 2024–2026 fall is a filing-cycle artefact, not a decline in funding** — recent years are still being committed. Do not publish a trend off the last three years. |
| `application_number` · `funding_request_number` · `form_471_line_item_number` | With `ros_entity_number`, the four-part **primary key**: 53,847 distinct, 0 blank, measured on the full file. |
| `spin_name` · `spin_number` · `service_provider_*` | The vendor. A SPIN is USAC's service-provider identifier; it is **not** a UEI, CAGE or EIN and does not join to anything else in Cedar. |
| `chosen_category_of_service` · `form_471_service_type_name` · `form_471_function_name` · `form_471_product_name` · `form_471_frn_fiber_*` · `upload_speed` · `download_speed` · `*_unit_name` | What was bought. **Speeds carry a separate unit column** — a bare `download_speed` of `1` may be 1 Mbps or 1 Gbps. Never compare the number without the unit. |
| `dis_pct` | The discount percentage applied. |
| `inclusion_basis` · `inclusion_basis_detail` | ADR-013 C12: **`subject_classification`**, and the classifier is named — `USAC tribal_type = <value>`. The publisher did the Indian-Country classification; Cedar did not. |
| `months_of_service` · `monthly_*` · `total_*` · `original_allocation` · `qty_allocation` | The cost build-up. See the money box. |

**No federal identifier.** USAC publishes no UEI, EIN or CAGE anywhere on
this asset — measured across all 68 source columns. Any link to the Cedar
spine is a **name + state** join, which is a candidate, not a determination.

---

# `usac_erate_tribal_entities.csv` — 2,752 rows

**One row per distinct `ros_entity_number` carrying a `tribal_type`.** This is
the entity grain; the table above is the money grain.

| Variable | Description |
|---|---|
| `ros_entity_number` | Primary key. 2,752 distinct, 0 blank. USAC's own entity number. |
| `ros_entity_name` | The **modal** name across that entity's line items — USAC's spelling can drift between filings and this picks the commonest, it does not merge them. |
| `tribal_type` | The **modal** `tribal_type`: `Tribal School` 2,332 · `Tribal Library` 417 · `Tribal College/University Library (for public use)` 3. |
| `tribal_type_distinct_values` | **How many distinct `tribal_type` values USAC ever gave this entity.** `1` on 2,748 of 2,752; **4 entities were typed two different ways** across their filings. Read this column before treating the type as settled. |
| `ros_entity_type` | `School` 2,324 · `Library` 420 · `Non-Instructional Facility (NIF)` 8. |
| `line_item_rows` | How many rows in the commitments table this entity holds. The 19.6× factor, per entity. |
| `funding_years_present` · `first_funding_year` · `last_funding_year` | 2017–2026 across the file. **`funding_years_present` is a COUNT of distinct years, not a span** — an entity present in 2017 and 2026 only has `2`, not `10`. |
| address columns, `ros_latitude`, `ros_longitude`, `ros_number_of_full_time_students`, `organization_name`, `billed_entity_number` | **The LAST NON-BLANK value seen**, not a history. This table cannot answer when an entity moved, changed district, or changed size. |
| `source_asset_id` · `retrieved_at` · `source_id` · `population_basis` | Provenance. `population_basis = TYPE_FILTER`. |
| `inclusion_basis` · `inclusion_basis_detail` | `subject_classification`, naming USAC's modal `tribal_type` for the entity. |

### What this closes

`docs/KNOWN_ISSUES.md` **A4** and the BIE school gap concern 185 BIE schools
whose only external source, NCES CCD, is capped at a 2024-10-01 count date
and a static 174-school universe. **This file reaches 2,752 tribal schools
and libraries with funding years running to 2026** — a much wider and much
fresher population, from a publisher with no relationship to NCES. It does
not *replace* the BIE directory (it is a funding recipient list, not a school
register) and it carries no NCES school number, so the join is by name and
state. But it is a genuinely independent second observation of a tribal
school's existence, name and address, and Cedar had none.

---

# `usac_rhc_hcp_directory.csv` — 11,142 rows

**One row per (Rural Health Care filing health care provider, address as
recorded).** The **full universe**, taken whole so the Native subset has a
denominator.

> ### ⚠ `filing_hcp` IS NOT A KEY
> 11,142 rows, **11,116 distinct `filing_hcp`**. 26 providers appear twice
> because some USAC line rows carry a blank city/state/county/zip for a
> provider that is fully addressed elsewhere — Antelope Memorial Hospital has
> 39 addressed rows and 1 blank one. **Count providers with distinct
> `filing_hcp`, not with rows.**

| Variable | Description |
|---|---|
| `filing_hcp` | USAC's health care provider number. Not unique in this table; see the box. |
| `filing_hcp_name` · `filing_hcp_entity_type` | Name and clinical category. Twelve categories: `Consortium Of The Above` 332,862 line rows · `Not-For-Profit Hospital` · `Rural Health Clinic` · `Community Health Center…` · `Community Mental Health Center` · `Local Health Department Or Agency` · `Dedicated Er Of Rural, For-Profit Hospital` · `Skilled Nursing Facility` · `Not Available` · `Post-Secondary Educational Institution…` · `Part-Time Eligible Entity`. **None of them is tribal.** |
| `filing_hcp_city` · `_state` · `_county` · `_zip_code` | Address as recorded. Blank on the 26 duplicate rows. |
| `line_rows` · `first_year` · `last_year` | How many commitment lines this provider holds and the year span, from USAC's own `$group`. |
| `inclusion_basis` | **`NOT_INDIAN_COUNTRY_SCOPED_DENOMINATOR`** — see the box below. |

> ### ⚠ THIS TABLE IS NOT INDIAN-COUNTRY SCOPED, AND ITS `inclusion_basis` IS A PROPOSAL
> Every other shipped table in Cedar can answer ADR-013 C12's question — *why
> is this row here?* — with one of six adopted bases. **This one cannot, and
> saying so is more honest than picking the nearest fit.** Most of these
> 11,142 providers are not Native and are not meant to be: the table is held
> so the 5,109-row Native candidate slice has a denominator, which is the
> thing coverage claims are divided by and the thing Cedar most often lacks.
>
> `inclusion_basis` is therefore written as
> **`NOT_INDIAN_COUNTRY_SCOPED_DENOMINATOR`**, a value **proposed to ADR-013
> and not adopted**. It is flagged in
> `docs/BIAMAPS_ACQUISITION_LOG_2026-09-02.md` as an integrator decision. A
> buyer must not be shown this table as a Native dataset; a coverage
> percentage computed against it is exactly what it is for.

> ### ⚠ CORRECTION TO `docs/SOURCE_EXPLORATION_2026-09-02.md` §1.3
> That survey lists RHC beside the E-Rate file as though the two shared a
> publisher-assigned tribal flag. **They do not. RHC has no `tribal_type`
> column and no tribal category anywhere.** Measured 2026-09-02 on the live
> asset: the only categorical is `filing_hcp_entity_type`, whose twelve values
> are listed above. The survey's *verdict* still holds — tribal and IHS
> clinics draw RHC funds and no Cedar source saw them — but its *reason*
> ("same portal, same terms, one more extract") understates the work: this
> half is a name sweep, not a type filter.

---

# `usac_rhc_native_candidate_lines.csv` — 5,109 rows

**One row per RHC commitment line whose filing OR participating provider
NAME carries one of 15 Native tokens.**

> ### ⚠ EVERY ROW IS A CANDIDATE. NOTHING HERE IS ATTRIBUTED.
> `confidence_tier` = **`C`** and `attribution_method` =
> `usac_rhc_name_token_candidate` on all 5,109 rows. The script's `verify`
> exits 1 if a single row carries anything else.
>
> A name token is not a determination. `START_HERE.md` standing rule 1: the
> exactness of a key says nothing about the correctness of a link, and
> *"a place suffix makes a tribe name a place"* — "Boys & Girls Clubs of
> Wichita Falls" is not the Wichita Tribe. **A tier is inherited from the
> source row, never assigned by the consumer**, and there is no source row
> here that ruled anything.

**The token list, and what was deliberately left out.** 15 tokens:
`tribal`, `tribe`, `indian health`, `indian hospital`, `native american`,
`alaska native`, `native hawaiian`, `pueblo`, `navajo`, `cherokee nation`,
`choctaw nation`, `chickasaw nation`, `muscogee`, `ihs `, `i.h.s.`.
**Excluded on purpose**: `nation`, `band`, `eagle`, `chief` — each produces
place-name false positives on its own, and a measured probe returned 1,324
name hits for `nation` and 18,124 for `band ` (mostly `Bandera`, `Bandon`),
against 252 for `tribal`.

`population_basis = NAME_TOKEN_SWEEP`. Neither the type leg nor the
identifier leg was available: RHC has no tribal flag and USAC publishes no
federal identifier. That is declared per row rather than left to be
discovered.

`inclusion_basis = term_match`, and ADR-013 C12 requires that **the matched
terms are recorded, not just the fact of matching** —
`inclusion_basis_terms_matched` carries them, semicolon-joined, **blank on 0
of 5,109 rows**. The commonest: `indian health` 1,944 · `cherokee nation` 402
· `ihs` 396 · `tribal` 286 · `indian health; ihs` 279 · `tribe` 262 ·
`muscogee` 248. It is re-derived at build time from the same `RHC_TOKENS`
list the SQL `WHERE` clause is built from, so the column cannot drift away
from the filter that produced the row.

Columns are the RHC source columns plus provenance. `funding_request_number`
+ `frn_line_number` is the primary key: 5,109 distinct, 0 blank.

---

## Reproducing

```
py -3 code/1120_acquire_usac_open_data.py probe
py -3 code/1120_acquire_usac_open_data.py pull
py -3 code/1120_acquire_usac_open_data.py build     # zero network
py -3 code/1120_acquire_usac_open_data.py verify    # exits 1 on breach
py -3 code/1120_acquire_usac_open_data.py selftest  # proves verify FIRES
```

Every page is hashed; page hashes are in
`data/raw/external/usac/_manifest.json` and `verify` asserts they are all
distinct, because a paginated API that ignores `$offset` returns the same
body forever and every status is 200.
