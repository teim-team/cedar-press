# Dataset harmonization audit — the 13 customer datasets, 2026-09-03

*Measured by `code/1168_harmonization_audit.py` (read-only; writes only to
`docs/harmonization_audit_2026-09-03/`) plus the one-off duckdb queries quoted
inline. **Every figure below came out of a command run against
`dist/customer/` on 2026-09-03 between 00:47 and 01:20 EDT.** Nothing is typed
from another document. Where a document is quoted, it is quoted in order to be
re-measured, and the re-measurement is printed beside it.*

> ## SNAPSHOT WARNING — READ BEFORE QUOTING ANY NUMBER HERE
>
> `dist/customer/` was being rebuilt by another agent while this ran, and it
> moved **under the measurement**. `contractors.csv` was rewritten at
> **00:54:43** while the first profile pass was reading the **00:35:55**
> version. That produced four apparent codebook defects
> (`cedar_uid`/`canonical_name` understated by 10,672; `ruling_status`/
> `ruling_applied_date` overstated by 154,765) which **do not exist** — every
> contractors figure in this document was re-measured against the 00:54:43
> file and all four reconcile exactly.
>
> The rest of the delivery is stable at 00:35:55–00:37:52. Re-run
> `py -3 code/1168_harmonization_audit.py all` before quoting anything.
>
> Row counts, snapshot 2026-09-03 01:0x: contractors 1,217,768 · deals 1,073 ·
> federal-register 11,402 · funding 701,955 · gaming 787 · legislation 3,069 ·
> lobbying 27,825 · nagpra 6,792 · native-owned-businesses 3,725 ·
> natural-resources 11,305 · nest 5,820 · nonprofits 12,689 ·
> subcontracting 70,597. **Total 2,074,807 rows, 1,147 columns.**

---

## ONE SCREEN

### What IS harmonized — measured, and better than the docs claim

| claim | measurement | file / command |
|---|---|---|
| **Row counts reconcile to source, with zero unexplained loss** | 13/13 delivered counts equal their flagship `data/clean` table. The only three shortfalls are `native-owned-businesses` −548, `nonprofits` −75, `subcontracting` −19,212 — **each exactly equal to the `rows_withheld` the MANIFEST declares.** | uncapped `count(*)` on both sides |
| **No duplicate rows anywhere** | **0 exact duplicate rows across all 2,074,807 rows**, md5 over the full concatenated row, uncapped, all 13 files | `duplicates.json` |
| **No duplicate primary keys** | 0 on all 8 datasets with a declared single-column key (`contract_transaction_unique_key` 841,002/841,002 · `Deal_ID` 1,073 · `bill_id` 3,069 · `document_number` 6,792 · `business_source_id` 3,725 · `resource_revenue_event_id` 11,305 · `subaward_source_record_id` 70,597) | same |
| **Codebooks name every shipped column and no phantom** | **1,147 shipped columns; 1,147 named; 0 missing, 0 phantom, both directions, all 13** | `codebook_diff.json` |
| **Codebook fill counts are true** | **1,147 of 1,147 `filled` figures match the delivered file exactly.** (The first pass found 4 mismatches; all 4 were the concurrent rebuild above.) | `codebook_count_check.json` |
| **Codebook sparsity lists are true** | Every "N columns are empty on every row" and "N columns under 10% populated" bullet matches, on all 13, name for name | `profile_*.json` |
| **`cedar_uid` is well-formed and registered** | Of the 10 datasets carrying it: **0 values fail the register's own shape (`AA-XXXXX-XX`) and 0 values are absent from `data/spine/cedar_identity_register.csv` (1,555 rows).** | `identity.json` |
| **One deflator, one base year** | All 4 datasets that deflate carry `deflator_factor_2025` + `inflation_base_year` = `2025`, single value, no other base year anywhere | `profile_*.json` |
| **The `extent_competed` two-vocabulary seam is closed in the delivery** | `extent_competed_normalized` **ships**, 10 values, one vocabulary. The raw two-vocabulary column ships beside it as evidence, as designed. | contractors header |

### What is NOT harmonized — ranked by how badly it misleads a reviewer

| # | severity | defect | the number |
|---|---|---|---|
| **H1** | S1 | `contractors` counts the literal strings `NAN` and `UNKNOWN` as populated data | `owner_as_of_transaction_cedar_uid` codebook **100.0% filled**; **1,066,926 of 1,217,768 (87.6%) are the string `UNKNOWN`**. `cage_code` 77.8% filled; **398,840 are `NAN`**. Also `place_of_perform_city` 88,269 `NAN`, `place_of_perform_state` 87,068 `NAN` |
| **H2** | S1 | `contractors`' six `n_<table>` join-count columns explode on a sentinel key | **669,287 rows (55.0%)** carry a meaningless count. All 270,447 blank-`cage_code` rows read `n_sam_prime_contracts_fy2000_2007 = 268,096`; all 398,840 `cage_code='NAN'` rows read `n_prime_contracts_archive_backfill = 398,840` |
| **H3** | S1 | **Two identity namespaces ship side by side and one dataset carries only the second** | `cedar_uid` (`CE-0011W-HN`) in 10 datasets; the register's **`handle`** (`TRBF-MHATAT-00`) in `*_entity_id` columns of 7. **`nagpra` ships 6,792 rows, 6,169 with a resolved entity, and ZERO `cedar_uid`.** A third namespace, `bia:cherokee-nation`, on `native-owned-businesses.nation_id` (3,453 rows) |
| **H4** | S1 | `funding.canonical_name` is the alias that won the match, not the entity's name | **340,738 of 549,134 keyed rows (62.1%)** disagree with the register's `canonical_name` for that row's own `cedar_uid`; 364,692 rows carry an all-lowercase name. Every other dataset agrees ≥98.7% |
| **H5** | S1 | **`tier` means two different things in two datasets** | `federal-register.tier` = Cedar confidence tier (`B`, 11,402 rows). `nonprofits.tier` = the IRS **filing form** (`990_N` 6,400, `full_990` 2,801, `not_required_to_file` 2,045, `990_EZ` 1,314, `UNKNOWN` 129). Same name, unrelated concepts |
| **H6** | S1 | `subcontracting` states two different money overstatements 30 lines apart in one file, on two undeclared denominators | `__NOTES.txt` line ~21: **63.4%** ($57,020,557,710.47 unfiltered / $34,906,694,737.65 countable) — true of the **89,809-row source**. Footer: **20.8%** ($42,172,721,583.24 / same countable) — true of the **70,597-row delivered file**. Both reproduce exactly. Neither says which file it describes |
| **H7** | S1 | The same file's prose describes rows it does not contain | `subcontracting__NOTES.txt` says Cedar "RETAINS all of them and flags the repeats in `duplicate_status`; it does not delete them" and quotes "87,355 of 89,809 rows (97.27%)" and "47,561 rows". The delivered file is 70,597 rows, `duplicate_status = 'primary'` on **100%**, either-leg coverage **69,278/70,597 = 98.13%**, `sub_cedar_uid` 38,563 |
| **H8** | S2 | Booleans use **six** vocabularies across the delivery, four of them inside one dataset | `0`/`1` (48 columns) · `Y`/`N` (11) · `yes` (11) · `Yes`/`No` (2) · `True`/`False` (1) · `Y`/`N`/`UNKNOWN` (1). `native-owned-businesses` alone ships `publishable`=`Y`, `publishable_before_1100`=`Y`/`N`, `is_current`=`True`/`False`, `owner_name_present`=`0`/`1` |
| **H9** | S2 | `pre_2000_flag` — one name, three encodings | `contractors`: `'0'` on all 1,217,768. `legislation`: `'1'` on 585, blank on 2,484. `subcontracting`: **blank on all 70,597** |
| **H10** | S2 | State is spelled 6 ways as a column and 4 ways as a value | Columns: `state` · `State` · `state_province` · `institution_state` · `sub_state` · `recipient_state_code` · `place_of_perform_state` · `entity_state`/`client_state`/`registrant_state` · `owner_hub_state`. Values: `nest.state_province` **567 of 5,820 rows are not USPS** (`Alaska` 211 beside `AK` 714; `Virginia` 109 beside `VA` 164; **12 rows hold the sentence `The business owner has hidden this information from public searches`**). `subcontracting.sub_state` **536 rows** hold `Michigan`/`MICHIGAN` beside `MI`. `native-owned-businesses.state_province` **110 rows** including truncations `Ne`, `Uta`, `Alas`, `Okl`, `Min`, `Geo`, `Tex`, `Nev`, `Ariz`. `deals.State` holds `Multi` (42), `Intl` (3), `Multiple`, `United Kingdom`, `AL / AK` |
| **H11** | S2 | The subaward money fence is printed into **all 13** codebooks; **12 have no `subaward_amount`** | `code/1137_customer_dataset_combine.py` L~388 emits `subaward_warning()` unconditionally, while the lobbying fence two lines below is correctly gated by `if coll == "lobbying"` |
| **H12** | S2 | The codebooks' "Quirks to know" bullets are chosen by naked substring match | **66 bullets across 13 codebooks; only 3 have the dataset's name in the heading.** **4 of `nest`'s 6 matched on the word `honest`.** `native-owned-businesses` gets **0** — `KNOWN_ISSUES.md` writes `native_owned_businesses` with underscores and the matcher looks for hyphens or spaces. `contractors` ships the bullet *"M1 · OPEN, BLOCKING A SHIP · `dist/customer/contractors.csv` does not exist"* — the file is 1.48 GB and 1,217,768 rows |
| **H13** | S2 | Provenance is not harmonized, and one dataset has none | `source_url` on **7 of 13**; **`lobbying` (27,825 rows) carries no source URL, no fetched date and no built date**; `nagpra.fetched_date` exists and is **blank on all 6,792 rows**; `funding.fetched_date` on 225,031 of 701,955 (32.1%); `built_date` (5 datasets) vs **`build_date`** (legislation) — one letter, one concept |
| **H14** | S2 | `funding` ships 12 always-blank BIE columns described as deliberate sparsity; they are a join that could never match | `bie_uio_dollars_by_entity.csv` holds 114 `cedar_uid`s, all valid register keys. **0 of the 114 appear in `funding.csv`'s 669 distinct `cedar_uid`s.** The codebook says "kept deliberately … Sparsity is a coverage fact." The disjointness is not stated |
| **H15** | S3 | Dates are ISO almost everywhere and not quite | `native-owned-businesses.certification_expiration` **45 of 750 non-ISO** (`8-13-2025`); `certification_start` **77 of 117**. `gaming.open_date` mixes `1994` / `2002-11` / ISO and holds **float years `2013.0`, `2005.0`**; `close_date` likewise. `nest.source_edition_date` 101 bare `YYYY`. `subcontracting.subaward_sam_report_last_modified_date` is **100% `YYYY-MM-DD 00:00:00+00`**, the only tz-stamped column in the delivery |
| **H16** | S3 | Prose and build notes inside controlled vocabularies | `gaming.property_status_literal` — one value is a 200-character correction narrative beginning *"Temporarily Closed \| CORRECTED 2026-09-01 (code/587) from `current`…"*. `gaming.…nigc_management_contract_status` = `not_held_by_cedar_press_this_session` on all 774. `subcontracting.prime_native_tier` = `source_filter` on 74 rows in an otherwise A/B column |
| **H17** | S3 | "Tier" is 14 column names and 4 unrelated concepts | Confidence: `confidence_tier`, `entity_tier`, `cedar_link_tier`, `identifier_ruling_tier`, `native_party_attribution_tier`, `federal_link_tier`, `prime_native_tier`, `sub_native_tier`, `link_tier`, `entity_link_tiers` (pipe-delimited: `B|A|B`), `tier`. **Method, not tier**: `geo_key_tier` = `derived_place_modal` / `exact_award_summary` / `exact_transaction`. **Source programme label**: `certification_tier` — 18 values, four spellings of one idea (`Priority 1` 201, `Priority #1` 142, `Preference Level 1` 113, `PREFERENCE 1` 91) plus `BID LIMIT: NOT APPLICABLE` |
| **H18** | S3 | Status vocabularies split by case and style | UPPER_SNAKE (`RULED_ATTRIBUTED`, `CANDIDATE_NAME_ONLY`, `SEALED_BY_STATUTE_OR_COMPACT`), lower_snake (`cedar_neid`, `reported_revenue`, `operating`), Title Case (`Primary verified`, `Approved`), hyphenated-lower (`died-in-committee`). `native-owned-businesses` carries `federal_link_status = NO_MATCH` **and** `federal_identifier_match_status = no_match` — the same token, two cases, two columns apart |
| **H19** | S3 | Real-2025 restatement covers 4 of the 8 money-bearing datasets | Deflated: contractors, funding, natural-resources, subcontracting. **Not deflated: `deals.Announced_Value_USD` ($47.88B), `lobbying.spend_usd`, `nonprofits.bmf_revenue_amt`, gaming's revenue columns.** Also `subcontracting.inflation_base_year` is stamped on all 70,597 rows while `deflator_factor_2025` is on 67,263 — 3,334 rows claim a base year with no factor |
| **H20** | S3 | Fiscal vs calendar year is never declared in the name | `fiscal_year` (contractors FY2000–2026, funding FY2007–2026, subcontracting FY2001–2026) sits beside calendar-year `Event_Year`, `filing_year`, `publication_year`, `first_observed_year`. `natural-resources` has **no year column at all** — only `period_start`/`period_end` |
| **H21** | S4 | `deals` is the only dataset not in `lower_snake_case` | **40 of 1,147 columns are not lower_snake_case; 38 are in `deals`** (`Deal_ID`, `Event_Date`, `Native_Party`, `Announced_Value_USD` …). The other two are `contractors.n_sam_prime_contracts_fy2000_2007_PUBLISHABLE` and `nonprofits.EIN` |
| **H22** | S4 | `funding` lost a geo column its sibling kept | `funding.geo_pop_place_ambiguous` and `geo_pop_place_dominance_share` are blank on all 701,955 rows while `geo_pop_county_fips` is populated on 92,064 — the same enricher wrote both flags on `contractors` (828,021 rows) |

### What is MISSING

- **33 columns are empty on every row** across 7 datasets; **126 more are >90% blank**. Every one is named in its own codebook, so none is a surprise — but **not one carries a cause specific to itself**; all six affected codebooks print the same generated "kept deliberately / sparsity is a coverage fact" sentence. For `funding`'s 12 BIE columns that sentence is positively wrong (H14). See §4b.
- **`legislation.affected_entities` is blank on all 3,069 rows** — `KNOWN_ISSUES` L6 reproduces exactly.
- **No row is missing.** All 13 reconcile to source; the three shortfalls are the three declared withholds.

### What I FIXED vs what I PROPOSED

| | |
|---|---|
| **Fixed** | `docs/KNOWN_ISSUES.md` — appended `<!-- BEGIN HARMONIZATION-AUDIT-1168 -->`, a re-measurement of M1–M5, L6 and WHAT_IS_MISSING §2/§3/§4 against the live delivery. **M1 is closed** and **M2's "26 customer files" is now 0.** No other agent's marker block was touched, and no line was edited in place. |
| **Fixed** | `code/1168_harmonization_audit.py` — the audit instrument itself, with its own first-run detector artefact (`column`, the markdown table header, reported as a phantom on all 13) documented in a comment rather than silently patched. |
| **Proposed, not applied** | `review/harmonization_proposals_2026-09-03.md` — 8 proposals. Six touch DATA or a builder another agent holds (`1137`); two are codebook-generator one-liners. Nothing in `dist/` was written. |

---

## 1. COLUMN HARMONY — the cross-dataset census

**1,147 columns across 13 datasets resolve to 1,052 distinct names. Only 58 names
appear in two or more datasets.** The delivery is therefore not one schema with
extensions; it is thirteen schemas that share a thin spine.

The shared spine, in full (`docs/harmonization_audit_2026-09-03/census.json`):

| n | column | datasets |
|---:|---|---|
| 10 | `cedar_uid` | contractors, deals, federal-register, funding, gaming, lobbying, natural-resources, nest, nonprofits, subcontracting |
| 7 | `source_url` | federal-register, nagpra, native-owned-businesses, natural-resources, nest, nonprofits, subcontracting |
| 6 | `fetched_date` | federal-register, funding, gaming, nagpra, natural-resources, subcontracting |
| 5 | `built_date` | contractors, federal-register, natural-resources, nest, nonprofits |
| 4 | `deflator_factor_2025`, `inflation_base_year` | contractors, funding, natural-resources, subcontracting |
| 4 | `city` | gaming, native-owned-businesses, nest, nonprofits |
| 3 | `fiscal_year` | contractors, funding, subcontracting |
| 3 | `confidence_tier` | contractors, funding, nonprofits |
| 3 | `canonical_name`, `attribution_method` | contractors, funding, lobbying |
| 3 | `entity_id` | gaming, lobbying, nonprofits |
| 3 | `pre_2000_flag` | contractors, legislation, subcontracting |

### 1a. One concept, more than one spelling

| concept | spellings measured | note |
|---|---|---|
| identity key | `cedar_uid` · `entity_id` · `*_entity_id` · `entity_cedar_uids` · `*_entity_ids` · `nation_id` · `business_source_id` | **and two namespaces** — see §3 |
| entity display name | `canonical_name` · `tribe_canonical_name` · `native_party_canonical_name` · `cedar_spine_canonical_name` · `entity_names` · `owner_hub_name` | |
| build stamp | **`built_date`** (5) vs **`build_date`** (legislation) · `geo_built_date` · `temporal_build_date` · `classified_date` · `promoted_date` | one-letter divergence |
| retrieval stamp | `fetched_date` (6) · `harvest_date` · `retrieved_date` · `artifact_mtime` · `Data_As_Of` · `first_seen`/`last_seen` | |
| state | `state` · `State` · `state_province` · `institution_state` · `sub_state` · `recipient_state_code` · `place_of_perform_state` · `entity_state` · `client_state` · `registrant_state` · `owner_hub_state` | |
| nominal money | `total_obligations` · `obligated_usd` · `amount_usd` · `subaward_amount` · `spend_usd` · `income_usd` · `Announced_Value_USD` · `bmf_revenue_amt` | the deflated form is uniformly `<nominal>_real2025` — that half is harmonized |
| tier | 14 names — see H17 | |
| year | `fiscal_year` · `Event_Year` · `filing_year` · `publication_year` · `first_observed_year` · `subaward_sam_report_year` | fiscal vs calendar never declared |

### 1b. THE DANGEROUS CLASS — one name, two meanings

| name | dataset A | dataset B | why it bites |
|---|---|---|---|
| **`tier`** | `federal-register` — Cedar confidence tier, `B` on all 11,402 | `nonprofits` — IRS filing form: `990_N` 6,400, `full_990` 2,801, `not_required_to_file` 2,045, `990_EZ` 1,314, `UNKNOWN` 129 | a reviewer who unions the two on `tier` gets a column mixing a confidence grade with a tax form |
| **`entity_id`** | gaming/lobbying/nonprofits — the register's **`handle`** (`TRBF-MHATAT-00`), 100% resolvable | `native-owned-businesses.business_entity_id` — mixes `CEDAR-ENT-000061` and `ANVC-HUNATO-00` (5 rows) | two id grammars under one name |
| **`pre_2000_flag`** | contractors — `'0'` on 100% | legislation — `'1'` on 585, blank on the rest; subcontracting — blank on 100% | three encodings of one boolean |
| **`*_tier` suffix** | confidence grades A/B/C/X | `geo_key_tier` — a **method** name | a `_tier` column that is not a tier |
| **`state`** | gaming/nonprofits/nagpra — clean USPS, 0 offenders | nest/native-owned-businesses/subcontracting/deals — mixed spellings and non-state tokens | see H10 |

---

## 2. VALUE HARMONY

### 2a. Booleans — six vocabularies

| vocabulary | columns | example |
|---|---:|---|
| `0` / `1` | 48 (+5 all-`0`, +9 all-`1`) | `contractors.attributed_flag` |
| `Y` / `N` | 11 (+4 all-`Y`) | `nest.parent_is_hub` |
| `yes` (lower, only value present) | 11 | `subcontracting.subaward_exceeds_prime_flag` (676) |
| `Yes` / `No` | 2 | `deals.Threshold_Exception`, `gaming.native_american_flag` |
| `True` / `False` | 1 | `native-owned-businesses.is_current` |
| `Y` / `N` / `UNKNOWN` | 1 | `nonprofits.keyed_state_agreement` |

### 2b. States — the non-USPS residue, measured

| dataset.column | non-USPS rows | worst values |
|---|---:|---|
| `nest.state_province` | **567 of 5,820** (41 values) | `Alaska` 211 · `Virginia` 109 · `Hawaii` 36 · **`The business owner has hidden this information from public searches` 12** |
| `subcontracting.sub_state` | **536 of 70,176** (64 values) | `Michigan` 67 · `OKLAHOMA` 51 · `MICHIGAN` 46 · `Oklahoma` 40 |
| `native-owned-businesses.state_province` | **110 of 3,725** (15 values) | `Ariz` 36 · `Wisconsin` 24 · `Alaska` 16 · `Ne` 14 · `Uta` 5 · `Alas` 2 · `Okl` 2 |
| `deals.State` | **48 of 940** (5 values) | `Multi` 42 · `Intl` 3 · `Multiple` · `United Kingdom` · `AL / AK` |
| `gaming.state` · `nonprofits.state` · `nagpra.institution_state` | **0** | clean |

`GROUP BY` on the first three splits a single state across up to three keys.

### 2c. Dates — ISO nearly everywhere

Clean ISO-8601 `YYYY-MM-DD` with **zero** offenders: `legislation.introduced_date`
and `latest_action_date` (3,061 each), `nagpra.repatriation_eligible_date` (2,782)
and `response_deadline_date` (3,904), `natural-resources.period_start`/`period_end`
(10,813) and `payment_date` (495), `nonprofits.ruling_date` (327) and
`placename_refusal_date` (516), `lobbying.termination_date` (776),
`gaming.first_observed_date` (453), `subcontracting.subaward_date` (70,597).

Not clean:

| dataset.column | non-ISO | form |
|---|---:|---|
| `native-owned-businesses.certification_start` | **77 of 117** | `8-13-2024`, `2020-09` |
| `native-owned-businesses.certification_expiration` | **45 of 750** | `8-13-2025`, `09-10-2025` |
| `gaming.open_date` | **448 of 636** | `1994`, `2002-11` |
| `gaming.close_date` | **91 of 148** | `2006-11`, **`2013.0`, `2005.0`** — a float year |
| `nest.source_edition_date` | **101 of 5,248** | bare `YYYY` |
| `subcontracting.subaward_sam_report_last_modified_date` | **70,054 of 70,054** | `2016-09-30 00:00:00+00` |

`WHAT_IS_MISSING.md` §4 said the six date formats in
`native-owned-businesses` were normalised to ISO by `771`. **Re-measured today:
the slash formats are gone and a dash-delimited US format remains on 45 + 77
rows.** Half fixed.

### 2d. Literal null-sentinel strings

`nan` / `NaN` / `NAN` / `None` / `NULL` / `N/A` / `unknown` / `-` etc., counted as
values, uncapped, all 13 files (`null_sentinels.json`):

| dataset | columns hit | worst |
|---|---:|---|
| contractors | 9 | `owner_as_of_transaction_cedar_uid` **1,066,926** · `cage_code` **398,840** · `place_of_perform_city` 88,269 · `place_of_perform_state` 87,068 · `extent_competed` 9,411 |
| nest | 3 | `status` 211 (`unknown`) |
| nonprofits | 2 | `tier` 129 (`UNKNOWN`) |
| gaming | 2 | `…compact_status` 153 (`unknown`) |
| funding | 3 | `cfda_title` 1,070 |
| subcontracting | 3 | `direction` 42 |
| native-owned-businesses | 1 | `identity_scope` 138 |
| deals, lobbying | 1 each | ≤7 |
| **federal-register, legislation, nagpra, natural-resources** | **0** | clean |

Some of these (`nonprofits.tier = UNKNOWN`, `gaming…compact_status = unknown`)
are legitimate declared vocabulary values. **The contractors ones are not** —
they are a pandas `NaN` stringified and uppercased, and they are counted as
populated in the codebook's `fill %`.

---

## 3. IDENTITY HARMONY

### 3a. Which datasets carry an identity key

| dataset | `cedar_uid` rows keyed | distinct uids | other entity-key columns |
|---|---:|---:|---|
| contractors | 625,787 | 384 | `owner_as_of_transaction_cedar_uid` (87.6% `UNKNOWN`) |
| funding | 552,756 | 669 | — |
| subcontracting | 32,369 | 169 | `prime_cedar_uid` 32,203 · `sub_cedar_uid` 38,563 |
| lobbying | 26,513 | 302 | `entity_id` (handle) 26,513 |
| federal-register | 10,396 | 396 | — |
| nest | 5,820 | 707 | `owner_hub_cedar_uid` 5,820 (correctly cedar_uid) |
| deals | 959 | 331 | `native_party_entity_id` (handle) 959 |
| gaming | 785 | 284 | `entity_id` (handle) 228 |
| natural-resources | 705 | 17 | `recipient_entity_id` (handle) 705 |
| nonprofits | 555 | 208 | `entity_id` (handle) 84 · `cedar_spine_entity_id` (handle) 591 |
| **legislation** | **0** | — | `entity_cedar_uids` — pipe-delimited, 676 tokens, **154 distinct, 0 bad, 0 unregistered** |
| **native-owned-businesses** | **0** | — | `certifying_authority_entity_id` (handle) 3,576 · `nation_id` **`bia:` slugs** 3,453 · `business_entity_id` 5 |
| **nagpra** | **0** | — | six `*_entity_ids` columns, **47,252 handle tokens, 100% resolvable to `register.handle`, not one `cedar_uid`** |

**710 `cedar_uid`s appear in more than one dataset.**

### 3b. The two namespaces

`data/spine/cedar_identity_register.csv` has 1,555 rows and **two keys**:
`cedar_uid` (`CE-00001-6S`) and `handle` (`AKNF-ACSRMT-00-CALSTA-ASVCPR`). The
delivery ships both, under different column names, with no crosswalk in the
package:

- every `*_entity_id` value tested resolves to `register.handle` at **100%**
  (gaming 228/228, lobbying 26,513/26,513, nonprofits 84/84 and 591/591,
  deals 959/959, natural-resources 705/705, native-owned-businesses 3,576/3,576,
  nagpra 47,252/47,252) and to `register.cedar_uid` at **0%**;
- every `cedar_uid` value resolves to `register.cedar_uid` at 100% and to
  `handle` at 0%.

Nothing is broken. But a customer joining `nagpra` to `funding` on the only
entity column each carries gets **zero rows**, and the register that reconciles
them is not in the delivery.

### 3c. Same uid, different name — 350 cases

`identity.json` lists every one. **25 are casing/punctuation only. 325 are
substantively different strings.** The cause is measurable:

| dataset | name column | rows with uid+name | disagree with register | all-lowercase names |
|---|---|---:|---:|---:|
| **funding** | `canonical_name` | 549,134 | **340,738 (62.1%)** | **364,692** |
| contractors | `canonical_name` | 625,787 | 8,125 (1.3%) | 0 |
| lobbying | `canonical_name` | 26,513 | 134 (0.5%) | 0 |
| deals | `native_party_canonical_name` | 959 | 2 (0.2%) | 0 |
| gaming | `tribe_canonical_name` | 785 | **0** | 0 |
| nonprofits | `tribe_canonical_name` | 555 | **0** | 0 |

`WHAT_IS_MISSING.md` §2 stated 341,486 of 548,980 (62.2%). **Re-measured
2026-09-03: 340,738 of 549,134 (62.1%). The document is accurate and the defect
is not fixed.** Specimens, all one `cedar_uid`:

- `CE-0011W-HN` → `Pueblo of Acoma` (contractors, gaming, lobbying) vs
  `haaku community academy` (funding)
- `CE-0012G-ES` → `Blackfeet` vs `blackfeet community college`
- `CE-000QD-1N` → `Fond du Lac` vs `fond du lac tribal and community college`
- `CE-000B5-ND` → **`Barrow` and `Natives of Kodiak, Inc.` — both inside
  `contractors`.** Two unrelated ANCs on one key; this one is not a display
  problem and is proposed for adjudication in `review/`.

---

## 4. MISSING DATA

### 4a. Row counts against source of truth — no shortfall is unexplained

| dataset | flagship (`data/clean/`) | source rows | delivered | delta | declared withheld |
|---|---|---:|---:|---:|---:|
| contractors | prime_contracts.csv | 1,217,768 | 1,217,768 | 0 | 0 |
| deals | deals_classified.csv | 1,073 | 1,073 | 0 | 0 |
| federal-register | consultation_events.csv | 11,402 | 11,402 | 0 | 0 |
| funding | federal_funding_transactions.csv | 701,955 | 701,955 | 0 | 0 |
| gaming | gaming_facilities.csv | 787 | 787 | 0 | 0 |
| legislation | native_bills.csv | 3,069 | 3,069 | 0 | 0 |
| lobbying | native_entity_lobbying_disclosures.csv | 27,825 | 27,825 | 0 | 0 |
| nagpra | nagpra_notices.csv | 6,792 | 6,792 | 0 | 0 |
| native-owned-businesses | native_owned_businesses.csv | 4,273 | 3,725 | **−548** | **548** ✔ |
| natural-resources | resource_revenue.csv | 11,305 | 11,305 | 0 | 0 |
| nest | nest_enterprises.csv | 5,820 | 5,820 | 0 | 0 |
| nonprofits | np_orgs.csv | 12,764 | 12,689 | **−75** | **75** ✔ |
| subcontracting | subawards.csv | 89,809 | 70,597 | **−19,212** | **19,212** ✔ |

### 4b. Empty and near-empty columns, and whether the blank means anything

| dataset | empty | >90% blank | blanks that are a stated "not applicable" | blanks with **no stated cause** |
|---|---:|---:|---|---|
| contractors | 0 | 0 | — | — |
| deals | 0 | 1 | — | `Event_Date_source_value_verbatim` (77) |
| federal-register | 0 | 8 | conditional on `is_event_primary_row` — the 8 event/location columns are only written for event rows | — |
| funding | **14** | 3 | `exclusion_*` conditional on `excluded_flag` ✔ | **12 BIE columns — cause given is wrong (H14); 2 geo_pop flags (H22)** |
| gaming | **10** | 32 | loyalty columns conditional on a program existing | 2 `source_url` columns blank while `source_url` is the delivery's provenance convention |
| legislation | **1** | 1 | — | **`affected_entities` — 0 of 3,069, KNOWN_ISSUES L6, open** |
| lobbying | 0 | 11 | `attribution_withdrawn_*` conditional ✔; `superseded_by_filing_uuid` conditional ✔ | — |
| nagpra | **1** | 9 | object-count columns conditional on the notice type ✔ | **`fetched_date` — 0 of 6,792** |
| native-owned-businesses | **3** | 17 | `publish_hold*` conditional on a hold existing | `person_name_check_1100` |
| natural-resources | **3** | 8 | | `operator_entity_id`, `operator_entity_name`, `related_asset_ids`; `cedar_uid` 705 of 11,305 (6.2%) is the lowest identity coverage of the ten |
| nest | 0 | 12 | mostly conditional evidence columns ✔ | — |
| nonprofits | 0 | 15 | ruling/refusal columns conditional ✔ | — |
| subcontracting | **1** | 9 | `sub_cage`/`prime_cage`/`psc` are FPDS-side and legitimately thin | `pre_2000_flag` |

**33 empty, 126 >90% blank.** Every one is named in its own codebook — that part
is exact. **Not one of the 33 carries a reason specific to itself.** All six
codebooks that have empty columns print the same generated sentence — *"kept
deliberately … Dropping blank columns would make the schema depend on which rows
shipped … Sparsity is a coverage fact"* — which is a good policy statement and
is not a cause. For 12 of the 33 (`funding`'s BIE block) that sentence is
positively misleading: the columns are blank because the two key populations do
not intersect at all (H14), which is a fact about the join, not about coverage.
The remaining 21 — `funding`'s 2 `geo_pop_place_*` flags, `gaming`'s 10,
`legislation.affected_entities`, `nagpra.fetched_date`,
`native-owned-businesses`' 3, `natural-resources`' 3, `subcontracting.pre_2000_flag`
— ship with no stated cause at all, and at least two of them
(`legislation.affected_entities`, `funding.geo_pop_place_ambiguous`) are known
pipeline gaps rather than "not applicable".

---

## 5. CODEBOOK TRUTH

**Both directions, all 13, clean.**

- `codebook` command parses the `| \`column\` | filled | fill % | distinct | …`
  table out of each `<name>__CODEBOOK.md`.
- **1,147 shipped columns; 1,147 named in a codebook. 0 shipped-not-documented.
  0 documented-not-shipped.**
- **1,147 of 1,147 `filled` counts match the delivered file exactly**, after
  re-measuring contractors against the 00:54:43 rebuild.
- Every "N columns are empty on every row" / "N columns are under 10%
  populated" bullet is exact, name for name, on all 13.
- Every codebook's stated row × column count matches the file and the MANIFEST.

**The detector artefact, recorded so it is not re-opened.** The first run
reported one phantom column, `column`, on all 13. That is the markdown table's
own header cell. It is excluded by name in `code/1168_harmonization_audit.py`
with a comment saying why.

**What the codebooks get wrong is not the columns; it is the prose around
them** — H11 (the subaward fence in all 13) and H12 (66 quirk bullets by
substring match). And the `fill %` figures are true about non-blankness and
false about populated-ness wherever H1's sentinels live.

---

## 6. CRITIQUES ACTUALLY CLOSED — every stated defect, re-measured today

*`docs/KNOWN_ISSUES.md`, `docs/WHAT_IS_MISSING.md`, `docs/ANOMALY_REPORT.md`,
`docs/CODEX_REVIEW_LOG.md`, filtered to claims that are testable against the 13
delivered files. Nothing below is taken on the document's word.*

| ref | the claim | reproducible **right now**? | the measurement |
|---|---|---|---|
| **KI M1** | *"`dist/customer/contractors.csv` does not exist"* — OPEN, BLOCKING A SHIP | **NO — CLOSED** | the file exists: 1,480,867,420 bytes, **1,217,768 rows, 79 columns**, mtime 2026-09-03 00:54:43. The doc is stale, and the stale text **ships to the customer** in `contractors__CODEBOOK.md` |
| **KI M2** | *"'86.9%' ships in 26 customer files"* | **NO — the boilerplate is fixed; the claim is now stale in the other direction** | `grep "86.9%" dist/customer/*` → **2 hits, both the quoted heading of M2 itself**, in `funding__CODEBOOK.md` L37 and `subcontracting__CODEBOOK.md` L25. The footer now prints a measured figure. The only place the stale number still reaches a buyer is the record of the defect |
| **KI M2 (residue)** | *"one file, twenty-six lines apart, one measurement, two answers"* | **YES, with new numbers — see H6** | `subcontracting__NOTES.txt` now says **63.4%** (source, 89,809 rows) and **20.8%** (delivered, 70,597 rows). Both reproduce exactly. Neither states its denominator |
| **KI M3** | `subcontracting` either-leg coverage 97.27% (87,355/89,809) | **superseded by the delivery** | on the **delivered** file: **69,278 of 70,597 = 98.13%**; `cedar_uid` alone 32,369 = 45.85%. 1,319 rows have no leg keyed |
| **KI M4** | 44 funding rows with `attributed_flag='1'` and no key | **YES — OPEN** | `attributed_flag='1' AND cedar_uid=''` → **44 rows**, exactly |
| **KI M5** | contractors 96 rows / $269,771,379.45 keyed but `attribution_method='unattributed'` | **NO — does not reproduce** | **0 rows** |
| **KI M5** | funding 3,620 rows / $1,534,889,361.52 keyed but not attributed | **YES — reproduces to the cent** | 3,620 rows, **$1,534,889,361.52** |
| **KI C1** | `faads_transactions_all_agencies.csv` 179,259 duplicate rows | **not applicable to the delivery** | that table is not one of the 13; it enters `funding` only as a count column. `funding.csv` has **0 duplicate rows** |
| **KI C2** | `subawards.csv` 10,770 duplicate rows | **not applicable to the delivery** | the delivered file has **0 exact duplicates** and `duplicate_status='primary'` on 100% — the repeats are the 19,212 withheld rows |
| **KI L6** | `native_bills.affected_entities` blank on all 3,069 rows | **YES — OPEN** | `legislation.affected_entities` non-blank = **0 of 3,069** |
| **KI NP-1** | 78.8% of linked nonprofit keys are wrong | **not re-testable here** — it rests on a hand-labelled sample, not a computable predicate. What IS measurable: the delivered file keys **555 of 12,689 rows (4.4%)**, and `key_review_disposition='SUPPORTED'` is **555** — i.e. the publication mask and the key column now agree exactly, which is what NP-3 asked for |
| **KI QA-STATUS-VOCAB** | `RULED_ATTRIBUTED` can mean a quarantined resolver guessed | **YES — still shipping** | `contractors.ruling_status='RULED_ATTRIBUTED'` on 458,548 rows sits beside `identifier_ruling_quarantined='Y'` on 227,540. Both ship; the name is unchanged |
| **WIM §2** | Acoma → school; 341,486 of 548,980 funding rows (62.2%) name-disagree | **YES — reproduces** | **340,738 of 549,134 (62.1%)**. `CE-0011W-HN` still reads `haaku community academy` in funding and `Pueblo of Acoma` in three others |
| **WIM §3** | `contract_number` is a modification PIID; 290,525 rows (23.9%) ≤6 chars; `parent_contract_number` populated on all 1,217,768 and not shipped | **HALF CLOSED** | `parent_contract_number` **now ships** — but on **798,403 rows (65.6%), not all of them**. `contract_number` ≤6 chars: **290,525 (23.9%)**, reproduces exactly; `'0001'` on **11,700**. The `nan` residue that pass found is gone: literal `nan` in `parent_contract_number` = **0** |
| **WIM §4** | `certification_expiration` in six date formats; fixed to ISO by `771` | **HALF CLOSED** | slash formats gone; **45 of 750 remain non-ISO** as `M-D-YYYY`, and `certification_start` is **77 of 117** |
| **START_HERE #5** | `extent_competed` holds two vocabularies; filter `extent_competed_normalized` | **CLOSED in the delivery** | both columns ship; the normalized one has 10 values in one vocabulary; `extent_competed_normalized_basis` ships too |
| **START_HERE #5 (b)** | *"`funding_agency` is the other two-vocabulary column and has no normalisation"* | **still true, and undocumented in the codebook** | 315 distinct values, 314 after upper-casing — so it is not a *casing* split, but the FY2016/17 label-vs-code seam is not normalised and no `_normalized` sibling ships. The contractors codebook carries no warning about it |
| **CODEX PR29 F4** | 156,592 rows, self-parent PIID | **not reproducible from the delivered columns** — `parent_contract_number` equals `contract_number` on the delivered file is measurable but the finding's own predicate used a column not shipped. **Not measured.** |
| **ANOMALY / gaming** | `property_status = current` beside `close_date`, 113 of 787 rows | **not re-measured this pass** — flagged as out of scope; `property_status` is populated on only 453 of 787 rows in the delivery, so the denominator has moved. **Not measured.** |

> **GAMING-DENOMINATOR-2026-09-02.** The 787 above is a ROW count and is used correctly as one. It is NOT a facility count: 16 rows say no casino in their own name (7 exactly `No casino`, 9 more inside a longer name), leaving 771 facility rows and **714 distinct properties** after the same-tribe duplicate groups. Five denominators circulated on 2026-09-02 — 787, 780, 734, 727, 714 — and four of them are wrong as a denominator. Re-derive rather than quote: `py -3 code/1116_ruling_propagation_2026_09_02.py derive`.

---

## 7. HOW TO REPRODUCE EVERY NUMBER HERE

```
py -3 code/1168_harmonization_audit.py all
```

Writes `docs/harmonization_audit_2026-09-03/`: `census.json` (headers + the
shared-column map + the mtime/size of every file read), `profile_<ds>.json`
(per-column non-blank, blank %, cardinality, and the exact vocabulary of every
column with ≤40 distinct values), `codebook_diff.json`, `codebook_count_check.json`,
`identity.json`, `duplicates.json`, `null_sentinels.json`, `date_formats.json`.

No network. No caps — every figure is a full-file stream through
`read_csv(..., all_varchar=true, sample_size=-1)`. Runtime ≈ 4 minutes, of which
84 s is contractors.

**Two things this instrument does NOT measure, said plainly rather than
implied:** it does not judge whether an attribution is *correct* (only whether
the key resolves and the names agree), and it does not re-derive any money
total beyond the two subaward fences quoted in H6.
