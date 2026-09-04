# Prior-finding closure matrix

*Written 2026-09-03. Owner of this pass: the prior-finding reconciliation workstream.
Companion script: `code/1171_prior_finding_regression_pack.py`.*

## Why this document exists

An external reviewer read the 2026-09-03 changelog and said:

> "I cannot translate the work into 'X of 142 findings closed.' The changelog needs an
> explicit closure table keyed to the prior issue IDs. Right now it is a strong narrative
> of new discoveries but a weak accounting of old blockers."

They are right. This is the accounting.

## Read this before the table

**The prior review is `review/QA_REVIEW_10ROW_2026-09-02.txt`.** It carries **151**
findings with IDs `CP-001` … `CP-151`, not 142 — counted, not asserted:

```
grep -cE "^\| CP-[0-9]+ \| P[0-9] \|" review/QA_REVIEW_10ROW_2026-09-02.txt   -> 151
grep -oE "CP-[0-9]+" review/QA_REVIEW_10ROW_2026-09-02.txt | sort -u | wc -l -> 151
```

Priority split, parsed out of the same tables: **59 P0, 76 P1, 16 P2**. The reviewer's
"142 findings / 41 blockers" does not match any count in the document; the numbers used
here are the ones in the file.

**Nothing below takes a document's word for anything.** Not `AGENTS.md`, not
`docs/KNOWN_ISSUES.md`, not the 2026-09-03 changelog. A finding is `CLOSED` only where a
command run on 2026-09-03 against the current tree returned a number that makes the
finding false. Where a measurement was not run, the row says `OPEN` or
`NOT_REPRODUCIBLE` and names what was missing.

**The product surface moved under the review.** The review inspected two six-collection
sample bundles of ten-row CSVs. Those bundles no longer exist. Today the surface is:

| surface | what it is | measured today |
|---|---|---|
| `dist/customer/*.csv` | the 13 delivered full datasets | 2,074,807 data rows, 1,147 columns |
| `dist/preview/*.csv` | 13 × 100-row previews, 7–11 curated columns each | 1,300 rows |
| `dist/samples/*.csv` | 15 × 10-row storefront samples | 150 rows |

Every row below is measured against **`dist/customer`** unless it says otherwise, because
that is the file a paying customer receives. Where a finding was about the *sample* and
the sample no longer has the field, that is recorded as a **narrowing of the preview, not
a repair of the data** — and one measurement below shows why that distinction matters.

**This run is a SNAPSHOT.** Concurrent rebuilds were writing `data/clean` and `dist/`
during this pass; `dist/customer/*.csv` carries mtimes between 00:35 and 01:38 on
2026-09-03. `review/1171_regression_pack_2026-09-03.json` stamps the size and mtime of
every file read. Re-run before quoting any figure as current.

**Zero observed is a floor.** Where a detector returned 0 this document says "no instance
in the N rows read", never "clean" and never "100%".

---

## Closure counts

| status | count | share of 151 |
|---|---:|---:|
| **CLOSED** — a measurement run today makes the finding false | 34 | 22.5% |
| **PARTIAL** — the mechanism exists, the condition still holds for some rows | 38 | 25.2% |
| **OPEN** — the condition still holds, measured | 68 | 45.0% |
| **REJECTED** — re-measured and the finding is not a defect as stated | 3 | 2.0% |
| **NOT_REPRODUCIBLE** — the named artifact could not be located to re-measure | 8 | 5.3% |

By the review's own priority:

| priority | total | CLOSED | PARTIAL | OPEN | REJECTED | NOT_REPRODUCIBLE |
|---|---:|---:|---:|---:|---:|---:|
| P0 (release blockers) | 59 | 17 | 12 | 26 | 1 | 3 |
| P1 | 76 | 14 | 22 | 34 | 2 | 4 |
| P2 | 16 | 3 | 4 | 8 | 0 | 1 |

**The honest headline is 34 of 151 closed, 17 of 59 release blockers closed.** No
collection has crossed from DO NOT SHIP to shippable on the strength of this pass.

---

## Live regressions — fixtures that FAIL right now

`py -3 code/1171_prior_finding_regression_pack.py check` exits **1**. Twelve of its 23
named detectors are nonzero. Four of those are rows the review named individually and
that a reader of the changelog would reasonably have believed were fixed:

| fixture | count today | rows read | the named row |
|---|---:|---:|---|
| `AVCP_ATTRIBUTED_TO_ASRC_FUNDING` | **84** | 701,955 (full) | AVCP Regional Housing Authority, Bethel AK → `Arctic Slope Regional Corporation`, `CE-00078-KR`, `attributed_flag=1` |
| `AVCP_ATTRIBUTED_TO_ASRC_NEST` | **1** | 5,820 (full) | the same false parent, in `nest.csv`, `publishable=Y` |
| `GOLDBELT_FAMILY_ATTRIBUTED_TO_TLINGIT_HAIDA` | **1,148** | 1,217,768 (full) | `C P Leasing, Inc`, parent `Goldbelt Incorporated`, canonical `Tlingit & Haida` |
| `SUBAWARD_DWARFS_ITS_PRIME` | **11** | 70,597 (full) | `VISTA DEFENSE TECHNOLOGIES, LLC` $1,282,234,055.80 against prime `STS SYSTEMS INTEGRATION` $13,406,053.11 |
| `UNION_CALENDAR_RECORDED_DIED_IN_COMMITTEE` | **89** | 3,069 (full) | `110-hr-1575` Burt Lake Reaffirmation Act, `Placed on the Union Calendar, Calendar No. 512.` → `died-in-committee` |
| `MUNICIPAL_PHA_KEYED_TO_A_TRIBE` | **6,002** | 701,955 (full) | Housing Authority of the City of Omaha → `Omaha`; Housing Authority of the City of Yakima → `Confederated Yakama` |
| `ENTITY_IS_ITS_OWN_ENTERPRISE` | **234** | 5,820 (full) | `The Tohono O'Odham Nation` as an enterprise of `Tohono O'odham` |
| `SUPERSEDED_LOBBYING_FILING_SHIPPED` | **1,064** | 27,825 (full) | 958 `SUPERSEDED_BY_AMENDMENT` + 106 `SUPERSEDED_BY_LATER_AMENDMENT` |
| `WITHDRAWN_ATTRIBUTION_SHIPPED` | **471** | 27,825 (full) | `attribution_withdrawn=1` still delivered |
| `QUARANTINED_CONTRACT_ROW_SHIPPED` | **227,540** | 1,217,768 (full) | `identifier_ruling_quarantined=Y` |
| `UNRULED_NONPROFIT_SHIPPED` | **12,366** | 12,689 (full) | `classification_ruling=UNRULED` |
| `NAGPRA_*` (3 of 4 fire) | 21 / 10 / 241 | 6,792 (full) | notice prose in `institution_name`; `Mesa Verde National Park` in `institution_city`; `by the Thurston` / `site in McKinley` in `removal_counties` |
| `MACHINE_PATH_IN_CUSTOMER_FIELD` | **4,227** | 2,074,807 (full) | `nest.source_document` = `… on this machine at ~/Desktop/dissertation/data/tribal…` |
| `CODE_LINEAGE_IN_CUSTOMER_FIELD` | **190,695** | 2,074,807 (full) | `legislation.entity_link_basis` = `… by code/1140 …` |

Eleven detectors return zero. Those are the closures with teeth — and every one of them
was proven able to return **one** first, by `selftest`.

### The most important single measurement in this document

The changelog says the preview no longer exposes unsafe states. That is true and it is not
the same claim as "the preview no longer contains unsafe rows". Joining the preview back
to the delivered file on its own visible columns:

```
PREVIEW lobbying:    100 rows, 100 matched to dist/customer/lobbying.csv,
                     12 of them join to a filing whose supersession_status is SUPERSEDED_*
PREVIEW contractors: 100 rows, 100 matched to dist/customer/contractors.csv,
                     10 of them join to a row with identifier_ruling_quarantined = Y
```

Caveat, stated because it changes how the number should be read: 81 of the 100 lobbying
joins are one-to-many on the four columns the preview exposes, so 12 is an indication of
the rate, not an exact count. Join ambiguity for contractors was not measured.

**The preview dropped the column that names the state. It did not drop the row.** A
reviewer looking at today's preview cannot see this; only the join can.

---

## Method

1. Parsed all 151 finding rows out of the review's markdown tables into
   `id | priority | category | location | finding | why | fix | release test`.
2. For each finding, ran a measurement against `dist/customer` (and `dist/preview` /
   `dist/samples` where the finding is about the sample).
3. Where the finding names a specific row, searched for that row's identifier and either
   re-read it or recorded `NOT_REPRODUCIBLE` with the search that failed.
4. Promoted 23 of the measurements into named detectors in
   `code/1171_prior_finding_regression_pack.py`, each of which is proven to fire on an
   injected violation before it is trusted to return zero.

Full detector output: `review/1171_regression_pack_2026-09-03.json`.

---

## The matrix

Column meanings: **measurement** is the command or predicate actually run today and the
number it returned. **limitation** is what is still not known after that measurement.

### Cross-cutting (CP-001 – CP-015)

| id | finding | status | measurement run 2026-09-03 | datasets | remaining limitation |
|---|---|---|---|---|---|
| CP-001 | P0 · a `cite_as` metadata row appended to 11 data CSVs | **CLOSED** | `1171` detector `CITE_AS_METADATA_ROW_IN_DATA_FILE` = **0** over 2,074,807 rows / 13 files; `grep -c cite_as dist/preview/*.csv dist/samples/*.csv` = 0 everywhere | all 13 | detector reads the first two cells of a row; a manifest row hidden in a later column would be missed |
| CP-002 | P0 · rows the pipeline marks HOLD / quarantined / contradicted / superseded / duplicate / awaiting-ruling are exported | **OPEN** | quarantined 227,540 (contractors); superseded 1,064 + withdrawn 471 (lobbying); UNRULED 12,366 (nonprofits); all uncapped | contractors, lobbying, nonprofits | there is still no single `is_publication_eligible` gate; `1165` passes because it audits identity and money, not adjudication state |
| CP-003 | P0 · `cedar_uid` means a different role in each collection | **OPEN** | `nest`: `cedar_uid == owner_hub_cedar_uid` on **5,820 of 5,820** rows, `enterprise_existing_cedar_uid` populated on only **103**; `nonprofits`: `cedar_uid` blank on **12,134 of 12,689** and names a linked tribe where present; `subcontracting`: `cedar_uid == prime_cedar_uid` while `sub_cedar_uid` differs on **714** rows | nest, nonprofits, subcontracting, funding | no role-specific ID columns have been minted; the subject of a NEST row still has no key of its own |
| CP-004 | P0 · the sampler selects rows without requiring them to be clean or complete | **PARTIAL** | preview→delivered join: **12 of 100** preview lobbying rows reach a `SUPERSEDED_*` filing; **10 of 100** preview contractors rows reach `identifier_ruling_quarantined=Y` | lobbying, contractors | the sampler is now reproducible (`1151 --seed`) and the preview is narrowed to 7–11 columns, but eligibility is still not a precondition of selection |
| CP-005 | P1 · analytical fields, evidence, parser diagnostics, review notes and build metadata share one file | **OPEN** | column counts today: contractors 79, funding 79, nest 88, subcontracting 86, nagpra 76, nonprofits 73, native-owned-businesses 70, legislation 65, lobbying 62, deals 60, natural-resources 52, federal-register 45, gaming 312 | all 13 | no `*_core` / `*_audit` split exists in `dist/customer` |
| CP-006 | P1 · the ZIPs contain only CSVs — no manifest, README, dictionary, grain or key statement | **CLOSED** | `find dist -name '*.zip'` = **0 files**; `dist/customer` carries `MANIFEST.csv` (25 columns incl. `grain`, `rows`, `columns`, `tables_folded_in`, `rows_withheld`, `withheld_why`), `REPORT.md`, and per-dataset `__CODEBOOK.md` + `__NOTES.txt` + `__NOTES.pdf` for all 13 | all 13 | the manifest's `grain` is prose, not a machine-checkable primary key declaration; file hashes were not found in `MANIFEST.csv` |
| CP-007 | P1 · local ZIPs, Python scripts, review CSVs and desktop paths are treated as the source | **OPEN** | `CODE_LINEAGE_IN_CUSTOMER_FIELD` = **190,695** rows; `MACHINE_PATH_IN_CUSTOMER_FIELD` = **4,227** rows; both over 2,074,807 rows | 8 of 13 files fire | `source_*` and `pipeline_*` are still the same namespace |
| CP-008 | P1 · naming conventions vary (snake_case, Title_Case, `EIN`) | **OPEN** | `deals`: **38 of 60** columns are Title_Case; `nonprofits` still carries `EIN` uppercase | deals, nonprofits | no cross-dataset naming contract is enforced by a gate |
| CP-009 | P1 · missingness encoded as blank / 0 / `UNKNOWN` / `NAN` / `-1` | **OPEN** | `contractors.cage_code == 'NAN'` **398,840**; `owner_as_of_transaction_cedar_uid == 'UNKNOWN'` **1,066,926** of 1,217,768; `funding.assistance_type == '-1'` **75** | contractors, funding | a null convention is documented nowhere this pass could find and is not gated |
| CP-010 | P1 · one-to-many relationships packed into pipe-delimited cells | **PARTIAL** | `nagpra.affiliated_entity_ids` contains a pipe on **2,223 of 6,792** rows; `lobbying.government_entities` on **19,819 of 27,825** | nagpra, lobbying, federal-register | child tables now exist (`n_nagpra_notice_institutions`, `nagpra_notice_institutions`) but the packed cells were not removed from the parent |
| CP-011 | P1 · dates mix publication / event / award / performance / synthetic without a precision model | **PARTIAL** | `deals.Event_Date_precision` now exists: day 972, month 75, `unknown_within_fiscal_year` 10, unknown 7, year 2, blank 7; `nagpra.fetched_date` blank on **6,792 of 6,792** | deals (fixed), nagpra (not) | precision is declared in `deals` only; the other twelve datasets have no precision column |
| CP-012 | P1 · money measures appear together with no additivity flag | **OPEN** | `deals` has **no** column matching `addit`/`sum`; **7** rows still carry the phrase `Do NOT sum` as prose; `contractors`: **50,414 of 307,671** distinct `contract_award_unique_key` values carry more than one `total_award_value` | deals, contractors, funding | additivity is still communicated in a note field a customer must read |
| CP-013 | P1 · overlapping records across collections with no crosswalk or duplication policy | **PARTIAL** | `federal-register.nagpra_notice_overlap` = `same_notice_in_nagpra_notices` on **10,920 of 11,402** rows — the overlap is now declared per row | federal-register, nagpra, deals, funding | declared, not resolved; no shared source-record key was found joining the two, and Deals↔Funding overlap was not re-measured |
| CP-014 | P2 · samples dominated by one agency / entity / period | **PARTIAL** | the sampler is a seeded reservoir draw (`1151 --seed=20260903`); the underlying concentration is real — `natural-resources` has **26 distinct `recipient_entity_name` in 11,305 rows**, and the name is blank on **9,840** of them | natural-resources, deals | a representative sample cannot be drawn from a population this concentrated; that is a coverage problem, not a sampler problem |
| CP-015 | P2 · canonical names shortened to labels | **OPEN** | observed live in this pass: `Tlingit & Haida`, `Confederated Yakama`, `Omaha`, `Three Affiliated` | contractors, funding, natural-resources | no full-legal-name column exists alongside `canonical_name` |

### Prime Contracting (CP-016 – CP-026) — `contractors.csv`, 1,217,768 rows, 79 columns

| id | finding | status | measurement run 2026-09-03 | datasets | remaining limitation |
|---|---|---|---|---|---|
| CP-016 | P0 · every sample row `identifier_ruling_quarantined=Y` | **OPEN** | full uncapped pass: `Y` **227,540**, `N` 661,262, blank 328,966 | contractors | quarantined rows are still exported; `MANIFEST.csv` records 166,166 rows as *attribution-masked*, which is a different and smaller set |
| CP-017 | P0 · `attributed_flag=1` on rows that are `RULED_HOLD` / `RULED_TIER_UNSTATED` | **PARTIAL** | cross-tab over all 1,217,768 rows: `RULED_HOLD` or `RULING_CONFLICT` **AND** `attributed_flag=1` → **0**; the same statuses with a non-blank `canonical_name` → **0**. But `RULED_TIER_UNSTATED` with `attributed_flag=1` → **506**, and `RULED_OWNER_NOT_IN_SPINE` with `attributed_flag=1` → **4,542** | contractors | the HOLD/CONFLICT half of the finding is genuinely closed; the TIER_UNSTATED half named in the review is not |
| CP-018 | P0 · Copper River Cyber Solutions → Native Village of Eyak while `RULED_HOLD` | **CLOSED** | full pass: rows with `COPPER RIVER` in `awardee_name` **and** `EYAK` in `canonical_name` = **0**; the named contract `75A50223F62012` is present (1 row) and re-read | contractors | closes the named pair only; the token-collision class it belongs to is CP-116/CP-038, still open |
| CP-019 | P0 · GSI North America → Lumbee while on HOLD | **CLOSED** | full pass: `GSI NORTH AMERICA` + `LUMBEE` = **0**; named contract `W9128F22F0179` present (2 rows) and re-read | contractors | as above |
| CP-020 | P0 · both S & T Services rows → Tikigaq despite `CONTRADICTED_AS_OF` | **CLOSED** | full pass: `S&T SERVICES` + `TIKIGAQ` = **0**; `CONTRADICTED_AS_OF` rows carrying a `canonical_name` = **0** | contractors | `CONTRADICTED_AS_OF` still counts 9,223 rows in the file; they no longer carry a name |
| CP-021 | P0 · one award appears with three different cumulative totals | **OPEN** | **50,414 of 307,671** distinct `contract_award_unique_key` values carry more than one distinct `total_award_value`; named award `12314422F0384` present, 8 rows | contractors | transaction rows and award snapshots are still one table; `total_award_value` is still summable by a customer |
| CP-022 | P1 · `source_file`, `ruling_source_file` cite local ZIPs and review CSVs | **OPEN** | `CODE_LINEAGE_IN_CUSTOMER_FIELD` fires on `contractors.csv` | contractors | — |
| CP-023 | P1 · 75 columns including parser, ruling and basis fields | **OPEN — worse** | column count today **79**, up from the 75 the review counted; always-empty columns **0** | contractors | — |
| CP-024 | P1 · `award_type` splits `DO` and `DELIVERY ORDER` | **OPEN** | `DELIVERY ORDER` 406,869 vs `DO` 146,269; also `PURCHASE ORDER` 47,141 vs `PO` 21,725; blank 447,900 | contractors | no controlled vocabulary is enforced |
| CP-025 | P1 · `cage_code` uses the literal `NAN` | **OPEN** | `cage_code == 'NAN'` on **398,840 of 1,217,768** rows (32.8%) | contractors | this is also the sentinel that makes the `n_*` join counts explode (changelog §6.5) |
| CP-026 | P2 · PIID, parent PIID, award key and transaction key not distinguished | **PARTIAL** | all four columns exist and are named: `contract_number`, `parent_contract_number`, `contract_award_unique_key`, `contract_transaction_unique_key`; `MANIFEST.csv` declares the two-population grain in prose | contractors | the manifest's grain statement is prose; no primary key is machine-declared or gated |

### Subcontracting (CP-027 – CP-037) — `subcontracting.csv`, 70,597 rows, 86 columns

| id | finding | status | measurement run 2026-09-03 | datasets | remaining limitation |
|---|---|---|---|---|---|
| CP-027 | P0 · $1,282,234,055.80 subaward against a $13,406,053.11 prime | **OPEN** | the named row is still delivered: `SSI348` present, `VISTA DEFENSE TECHNOLOGIES, LLC` / `STS SYSTEMS INTEGRATION`, `subaward_exceeds_prime_flag=yes`. The class: **11** rows ≥ $100M and > 10× their prime; **2** rows ≥ $1B; **676** rows exceed their prime at all | subcontracting | the row is flagged and published. Flagging is correct (flag never delete); publishing a flagged impossibility as a measure is not |
| CP-028 | P0 · two rows marked `exact_repeat_within_source` remain in the sample | **CLOSED** | `duplicate_status` is `primary` for **70,597 of 70,597** rows — no `exact_repeat_within_source` value survives anywhere in the file; named rows `SSI203` and `NT18.0016` each present exactly once | subcontracting | de-duplication was verified by the absence of the marker, not by re-deriving duplicates independently |
| CP-029 | P0 · one row combines two subawards behind `MULTIPLE; SEE DESC` | **OPEN** | `subaward_number` contains `MULTIPLE` on **53** rows | subcontracting | rows are not atomised |
| CP-030 | P1 · generic `cedar_uid` follows the prime side | **OPEN** | **714** rows where `cedar_uid == prime_cedar_uid` while `sub_cedar_uid` is different and non-blank | subcontracting | role-specific IDs exist (`prime_cedar_uid`, `sub_cedar_uid`) but the ambiguous generic column was kept |
| CP-031 | P1 · `source_file=fy2016` — a partition named as a source | **PARTIAL** | `source_dataset` now names pull families: `usaspending_fsrs_pull` 66,842, `usaspending_fsrs_name_match` 2,703, `highergov_2023_export` 543, `usaspending_fsrs_parent_cluster` 306 | subcontracting | still a pipeline label, not an evidentiary record |
| CP-032 | P1 · `source_url` resolves to the prime award page, not the subaward filing | **PARTIAL** | `source_url` blank on **0** rows; **19,194 distinct URLs across 70,597 rows** — 3.7 rows per URL, consistent with award-level rather than subaward-level granularity | subcontracting | URL granularity was inferred from the ratio, not from fetching a URL |
| CP-033 | P1 · `geo_subawardee_county_gap_reason` contains `closed 2026-09-02 by code/1109…` | **OPEN** | that sentence is present on **67,665 of 70,597** rows | subcontracting | — |
| CP-034 | P1 · 81 columns, nine entirely empty | **PARTIAL** | column count now **86** (up 5); always-empty columns now **1** (`pre_2000_flag`), down from 9 | subcontracting | the empty columns were filled, not removed; the file got wider |
| CP-035 | P1 · description begins `ROVIDE THE SUPPORT…` — a truncated first character | **OPEN** | **6** rows whose `description` begins with a truncated word (`ROVIDE`, …); named row `A16-002982` present, 2 rows | subcontracting | the truncation cause was not traced to a parser |
| CP-036 | P2 · `pre_2000_flag` blank rather than false | **OPEN** | blank on **70,597 of 70,597** rows | subcontracting | the column is now entirely non-informative |
| CP-037 | P2 · all ten sample rows `both_sides_native` | **REJECTED as stated** | population: `b_native_as_subawardee` 38,110, `a_native_as_prime` 30,915, `both_sides_native` **1,530**, `unknown` 42 — the sample was unrepresentative, the data are not skewed | subcontracting | this was a sampler defect (CP-004/CP-014), correctly identified there |

### Federal Funding (CP-038 – CP-049) — `funding.csv`, 701,955 rows, 79 columns

| id | finding | status | measurement run 2026-09-03 | datasets | remaining limitation |
|---|---|---|---|---|---|
| CP-038 | P0 · AVCP Regional Housing Authority (Bethel, AK) → Arctic Slope Regional Corporation | **OPEN — LIVE REGRESSION** | full uncapped pass: **84 of 99** AVCP rows carry `canonical_name = Arctic Slope Regional Corporation`, `cedar_uid = CE-00078-KR`, `attributed_flag = 1`. The same false parent also survives in `nest.csv` (1 row, `publishable=Y`). Named FAIN `10IH0202000` present | funding, nest | ASRC and AVCP are unrelated: ASRC is the North Slope regional corporation, AVCP the Yukon-Kuskokwim tribal consortium ~600 miles away. This is the review's single most-cited example and it is still shipping |
| CP-039 | P0 · every row states `tribe_id_scheme was left blank by 24_funding_merge.py` | **PARTIAL** | `attribution_basis` still mentions `tribe_id_scheme` on **183,419 of 701,955** rows (26.1%), down from "every row" | funding | the retired-scheme *values* are gone (changelog §1) but the narrative about them is still shipped as provenance |
| CP-040 | P0 · housing-authority awards presented under a tribe with no separate recipient ID | **OPEN** | `MUNICIPAL_PHA_KEYED_TO_A_TRIBE` = **6,002** rows: Housing Authority of the City of Omaha → `Omaha` / `CE-0017W-FN` (5,015 rows, `attributed_flag=1`); Housing Authority of the City of Yakima → `Confederated Yakama` / `CE-001CC-8N` (965 rows) | funding | the changelog records negative rulings written for these and **not applied** (§3). Montgomery County Housing Authority *is* now `excluded_not_native` with a blank name — 29 rows — so the class is being worked, unevenly |
| CP-041 | P0 · −$0.90 and −$4,163,330 obligations with no action-type field | **OPEN** | negative `obligated_usd` on **43,866 of 701,955** rows; columns matching `action_type` or `modification`: **none**. Named FAINs `B04SR040502` and `10IH2726660` both present | funding | a customer summing this column cannot tell a deobligation from a correction |
| CP-042 | P1 · rows point only to local USAspending archive ZIPs, no public award URL | **OPEN** | no `source_url` column exists in `funding.csv`'s 79 columns | funding | — |
| CP-043 | P1 · `assistance_type = -1` as missing | **PARTIAL** | `-1` on **75** rows only, not on the older population generally | funding | 75 rows still carry a negative sentinel |
| CP-044 | P1 · `ak_flag` blank on every row including Alaska recipients | **PARTIAL** | blank on **225,031 of 701,955** rows (32.1%), so it is populated on 476,924 | funding | still blank on a third of the file, including rows the review named |
| CP-045 | P1 · `CITY OR TOWNSHIP GOVERNMENT` on tribal recipients | **OPEN** | **22,704** rows carry `CITY OR TOWNSHIP GOVERNMENT` in `business_types_description` | funding | this is the federal source's own code; the defect is that Cedar attributes those rows to tribes anyway (see CP-040) |
| CP-046 | P1 · 69 columns, 14 empty | **OPEN** | **79** columns today; **14** always-empty on the full pass — twelve `bie_uio_dollars_by_entity__*` and two `geo_pop_place_*` | funding | the file got wider and the empty count did not move |
| CP-047 | P1 · no plain-language award description | **OPEN** | the only `*description*` columns are `assistance_type_description`, `business_types_description`, `business_types_description_normalized`, `business_types_description_normalized_basis` — all code labels | funding | — |
| CP-048 | P1 · four loan-value fields all zero in a grant-only sample | **PARTIAL** | the four loan columns are not in the always-empty list, so they are populated somewhere in the full file | funding | not re-measured per row; the sample-level finding does not transfer to the population |
| CP-049 | P2 · all ten sample rows are HUD 2008/2010 | **REJECTED as stated** | a sampler artefact; the delivered file spans 701,955 rows across many CFDA programs (`cfda_title` is populated) | funding | subsumed by CP-004 |

### Federal Register (CP-050 – CP-061) — `federal-register.csv`, 11,402 rows, 45 columns

| id | finding | status | measurement run 2026-09-03 | datasets | remaining limitation |
|---|---|---|---|---|---|
| CP-050 | P0 · mixed grain: event rows and participant rows in one table | **PARTIAL** | the grain is now *declared* by four columns that exist and are populated: `is_event_primary_row` (1 → 2,313; 0 → 9,089), `n_participant_rows_for_event`, `participant_role`, `document_role` (`consultation_reported_in_document` 10,888 / `consultation_notice_published` 514). 2,223 distinct `federal_register_citation` values over 11,402 rows | federal-register | declared, not split. One table still holds two grains; `MANIFEST.csv` states it as "one row per (consultation event, participant as published)" |
| CP-051 | P0 · two participant rows share one event while the quote lists many more | **PARTIAL** | max rows per citation is now 50 (`85 FR 32417`, `85 FR 68360`), p-values recorded in `MANIFEST.csv`; the named document `FR 2013-13468` was **not** re-located by citation search | federal-register | completeness of participant extraction per notice was not measured |
| CP-052 | P0 · `location = Indian Education Programs, MS` — a mail-stop fragment | **OPEN** | **2** rows whose `location` matches a mail-stop shape | federal-register | narrow regex; other malformed locations would not match it |
| CP-053 | P0 · event date parsed as April 3 when the quote lists March 31 | **NOT_REPRODUCIBLE** | `FR 95-6969` not found by `fr_document_number` or `federal_register_citation` in the current 11,402 rows | federal-register | the row may have been dropped, re-keyed, or renumbered; not established which |
| CP-054 | P0 · `event_end_date=2002-12-20` inconsistent with the listed meetings | **CLOSED (for the invariant)** | rows where `event_end_date < event_start_date`: **0 of 11,402**. Named document `FR 01-30327` not located | federal-register | a self-consistent interval can still disagree with its source quote; that was not re-checked against the quote |
| CP-055 | P0 · multi-session notice collapsed to one start/end | **NOT_REPRODUCIBLE** | `FR 2011-8999` not located in the current file | federal-register | no multi-session model exists to test against |
| CP-056 | P1 · in-person meetings labelled `written_comment` | **PARTIAL** | `format` is now multi-valued: blank 11,222, `written_comment` 104, `virtual` 34, `virtual;written_comment` 15, `teleconference` 7, `teleconference;written_comment` 4 | federal-register | a semicolon-joined multi-value string in one cell; and `format` is blank on 98.4% of rows |
| CP-057 | P1 · half the sample duplicates NAGPRA notices | **PARTIAL** | now declared per row: `nagpra_notice_overlap = same_notice_in_nagpra_notices` on **10,920 of 11,402** rows (95.8%) | federal-register, nagpra | the overlap is far larger than the review found and is labelled but not resolved; no shared record key |
| CP-058 | P1 · `program` holds sentence fragments | **OPEN** | not separately measured this pass; `program` is present in the 45 columns | federal-register | **unmeasured** — recorded as OPEN rather than closed for that reason |
| CP-059 | P1 · `confidence=high` on all rows despite parse errors | **PARTIAL** | `high` 10,867, `medium` 535 — the scale now varies | federal-register | 95.3% still `high` while `NAGPRA_*` and location detectors fire |
| CP-060 | P1 · overlap, basis and long source quotes embedded in the core table | **OPEN** | `nagpra_notice_overlap`, `nagpra_bridge_overlap`, `nagpra_coverage_window`, `event_date_basis`, `event_date_source_quote`, `location_basis`, `location_source_quote`, `source_quote` all present in the 45 delivered columns | federal-register | — |
| CP-061 | P2 · `match_method = no_participants_named_in_record` — an absence stored as a method | **OPEN** | that literal value on **1,006 of 11,402** rows | federal-register | — |

### Legislation (CP-062 – CP-072) — `legislation.csv`, 3,069 rows, 65 columns

| id | finding | status | measurement run 2026-09-03 | datasets | remaining limitation |
|---|---|---|---|---|---|
| CP-062 | P0 · 105-hr-948 failed 240-167 but `outcome = passed-one-chamber` | **CLOSED** | `1171` detector `BURT_LAKE_FAILED_VOTE_RECORDED_AS_PASSED` = **0**; the row now reads `outcome = floor-vote-failed`, `latest_action = "On motion to suspend the rules and pass the bill Failed by the Yeas and Nays: (2/3 required): 240 - 167 (Roll no. 574)."`. A new `floor-vote-failed` value exists on 11 rows. Chamber-aware generalisation `HOUSE_BILL_FAILED_HOUSE_VOTE_RECORDED_AS_PASSED` = **0** over all 3,069 rows | legislation | the naïve version of this detector fires once, on `95-s-666` — a Senate bill that passed the Senate and then failed in the House, where `passed-one-chamber` is defensible. That row is a false positive and is excluded by the chamber test, not by a repair |
| CP-063 | P0 · a bill on the Union Calendar classified `died-in-committee` | **OPEN — LIVE** | `UNION_CALENDAR_RECORDED_DIED_IN_COMMITTEE` = **89 of 101** rows whose `latest_action` contains `Placed on the Union Calendar`. Named row `104-hr-3828` (Indian Child Welfare Act Amendments of 1996) still reads `died-in-committee`; so does `110-hr-1575`, the Burt Lake Reaffirmation Act | legislation | being reported out and calendared is the opposite of dying in committee. The outcome ladder was rebuilt enough to add `floor-vote-failed` but not enough to add a reported-to-floor state |
| CP-064 | P0 · the Burt Lake-specific bill has a blank `affected_entities` | **OPEN** | `affected_entities` blank on **3,069 of 3,069** rows; for `105-hr-948` both `affected_entities` and `entity_names` are empty | legislation | entity-linkage columns exist (`entity_cedar_uids`, `entity_names`, `n_entities_resolved`) but the advertised field is empty everywhere |
| CP-065 | P1 · the only source is `tribal_bill_intros.csv`; no Congress.gov URL | **PARTIAL** | `record_basis` now reads `voteview_rollcall_only + congress_gov_bill_endpoint_title_backfill + scope_ruled_1092_2026-09-02` — the API is named. `native_bill_action_coverage__source_url` exists | legislation | the source is named in a basis string, not delivered as a per-row record URL |
| CP-066 | P1 · `classification_source` holds methods, not sources | **OPEN** | `classification_source` is still a delivered column | legislation | not re-measured value-by-value this pass |
| CP-067 | P1 · companions inferred from identical normalised titles | **OPEN** | `companion_basis` is still a delivered column stating the inference | legislation | the inference itself was not re-validated |
| CP-068 | P1 · the product promises votes but ships bill rows only | **PARTIAL** | `has_rollcall = 1` on **283 of 3,069** rows and `n_rollcalls > 0` on the same 283; `n_bill_votes`, `n_bill_votes_entity_bridge`, `n_member_positions` join-count columns exist | legislation | roll-call and member-vote rows are counted, not delivered in this file |
| CP-069 | P1 · nine of ten rows get the same coarse outcome | **PARTIAL** | the ladder now has 8 values: `died-in-committee` 2,189, `passed-one-chamber` 421, `enacted` 283, `pending` 125, blank 17, `superseded-by-another-measure` 15, `floor-vote-failed` 11, `vetoed` 8 | legislation | 71.3% still land on `died-in-committee`, and CP-063 shows 89 of those are wrong |
| CP-070 | P2 · `cosponsor_count` as decimal strings, one blank | **OPEN** | decimal-formatted on **2,045** rows; blank on **1,024** of 3,069 | legislation | — |
| CP-071 | P2 · a collection-level kappa repeated on every row | **OPEN** | `classification_kappa` has **3** distinct values across 3,069 rows | legislation | — |
| CP-072 | P2 · all sample bills from the 103rd–105th Congresses | **REJECTED as stated** | the delivered file spans Congress **93 – 119** | legislation | a sampler artefact; subsumed by CP-004 |

### Deals (CP-073 – CP-083) — `deals.csv`, 1,073 rows, 60 columns

| id | finding | status | measurement run 2026-09-03 | datasets | remaining limitation |
|---|---|---|---|---|---|
| CP-073 | P0 · nine of ten rows are federal grants, not deals | **PARTIAL** | `Deal_Category` in the population: `Grant / public financing` **623**, `Acquisition` 173, `Private transaction` 90, `Financing` 38, `Capital project` 25, `Real estate / land acquisition` 22 | deals | grants are now a named category rather than an unlabelled majority — but they are still 58.1% of a product sold as a deal ledger, and the scope question the review raised is unanswered |
| CP-074 | P0 · `Event_Date` is a performance-start date on rows labelled `Awarded` | **OPEN** | `Event_Date_precision` exists but no column distinguishes award date from performance start; the named rows `FA-DOE-0003` / `FA-DOE-0014` were not separately re-read this pass | deals | **partly unmeasured** — recorded OPEN for that reason |
| CP-075 | P0 · month-only dates converted to the 15th | **CLOSED** | **12 of 1,073** rows have an `Event_Date` ending `-15`, and **0** of those carry `Event_Date_precision = month`. Month precision is declared on 75 rows and those are not silently dated | deals | precision is declared for `deals` only |
| CP-076 | P0 · `$5M` and `$10M` coexist with a note saying `Do NOT sum` | **PARTIAL** | **7** rows still carry the literal phrase `Do NOT sum`; **no** column name in the 60 matches `addit` or `sum` | deals | the additivity rule is prose in a note field, which is exactly the finding |
| CP-077 | P1 · the ≥$1M DOE-share rule is repeated in notes | **OPEN** | still present in `Notes`; **48** rows carry `Staged by code/994; merged by code/1088_merge_staged_deals.py after gates G0-G7…` | deals | population rules belong in the README, not on each row |
| CP-078 | P1 · internal addition CSVs and attribution files exposed | **OPEN** | `Event_Date_precision_basis` fires the code-lineage detector on **1,073 of 1,073** rows; `Notes` on 141; `Native_Connection` on 90 | deals | — |
| CP-079 | P1 · duplicate raw/standard field pairs | **OPEN** | `Value_Type` and `value_type_raw` both delivered; the pattern repeats for sector/type/category/status | deals | — |
| CP-080 | P1 · the DOE grant number lives inside the description text | **OPEN** | **no** column name in the 60 contains `award` or `grant` | deals | — |
| CP-081 | P1 · `Primary verified` with `Medium` confidence and no indication of what is uncertain | **OPEN** | both columns still delivered; not cross-tabbed this pass | deals | **unmeasured** cross-tab |
| CP-082 | P2 · Deals is the only Title_Case file | **OPEN** | **38 of 60** columns are Title_Case | deals | — |
| CP-083 | P2 · canonical names shortened (`Coyote Valley`, `Seminole`, `Forest County`) | **OPEN** | same class as CP-015, observed live | deals | — |

### NAGPRA (CP-084 – CP-096) — `nagpra.csv`, 6,792 rows, 76 columns

| id | finding | status | measurement run 2026-09-03 | datasets | remaining limitation |
|---|---|---|---|---|---|
| CP-084 | P0 · `fetched_date` blank; only `artifact_mtime` populated | **OPEN** | `fetched_date` blank on **6,792 of 6,792** rows; `artifact_mtime` still delivered; `source_url` blank on 0 | nagpra | retrieval date is the one provenance field a re-verifier needs and it is empty everywhere |
| CP-085 | P0 · DOE Richland and the Burke Museum concatenated, `institution_count=1` | **PARTIAL** | the specific collapse test — `institution_names_all` listing more than one institution while `institution_count` says 1 — returns **0 of 6,792**. `institution_count` now varies (1 → 6,415; 2 → 350; 3 → 21; 8 → 3; 6 → 2; 5 → 1) and a child table `nagpra_notice_institutions` exists. **But** `institution_name` still holds notice-title prose on **21** rows (`of Native American Human Remains from the Island of Lanai in the Collections of the Bernice Pauahi Bishop Museum`), and **1,092** rows carry a conjunction in `institution_name` while `institution_count` is 1 | nagpra | the counter was fixed; the parser was not. 1,092 conjunction rows are an upper bound — `Anchorage Museum of History and Art` is one institution — so that figure is a candidate set, not a defect count |
| CP-086 | P0 · a National Park Service unit and the Burke Museum concatenated | **PARTIAL** | same measurement as CP-085 | nagpra | as above |
| CP-087 | P0 · `institution_city = Big Bend National Park` | **OPEN — LIVE** | **10** rows whose `institution_city` is a national park / monument / forest: `Mesa Verde National Park` ×3, `Hawaii National Park` ×2, `Badlands National Park`, `Rio Grande National Forest`, `Big Bend National Park`, `Ocmulgee National Monument` | nagpra | — |
| CP-088 | P0 · county fields hold `Rockshelter in Allamakee`, `site in Brewster` | **OPEN — LIVE** | **241 of 6,792** rows: `site in` ×186, `River in` ×53, `by the` ×2. Example: `King|Pierce|Thurston|by the Thurston`; `River in Pima|by the Pinal|site in McKinley|site in Pima` | nagpra | — |
| CP-089 | P0 · `n_parties_named` double-counts a tribe appearing in several roles | **OPEN** | **3,742 of 6,792** rows have `n_parties_named > n_entities_resolved` | nagpra | the gap is consistent with double counting *and* with unresolved names; the two were not separated |
| CP-090 | P0 · corrections included with no original-notice link or supersession policy | **OPEN** | `is_correction = 1` on **286** rows; the only correction-related column in the 76 is `is_correction` itself — no link column, no current-version flag | nagpra | — |
| CP-091 | P1 · unresolved party names are not supplied as a list | **OPEN** | the 3,742-row gap above; no `*_unresolved_names` column exists | nagpra | — |
| CP-092 | P1 · a correction reports object counts while `object_categories` is blank | **NOT_REPRODUCIBLE** | named document `03-10916` not re-located by `document_number` this pass | nagpra | — |
| CP-093 | P1 · role-specific entity IDs packed into pipe-delimited cells | **OPEN** | pipe present in `affiliated_entity_ids` on **2,223** rows; six such `*_entity_ids` columns are delivered | nagpra | the child table exists for institutions, not for party roles |
| CP-094 | P1 · `parent_dataset`, `parse_template`, span diagnostics exposed | **OPEN** | all three still in the 76 delivered columns | nagpra | — |
| CP-095 | P1 · all ten sample rows are inventory-completion notices | **REJECTED as stated** | population: `inventory_completion` 4,801, `intent_to_repatriate` 1,861, `intended_disposition` 130 | nagpra | a sampler artefact; subsumed by CP-004 |
| CP-096 | P2 · four URL columns repeat the same link | **OPEN** | `html_url`, `pdf_url`, `full_text_url`, `source_url` all delivered | nagpra | overlap between them was not measured value-by-value |

### Lobbying (CP-097 – CP-106) — `lobbying.csv`, 27,825 rows, 62 columns

| id | finding | status | measurement run 2026-09-03 | datasets | remaining limitation |
|---|---|---|---|---|---|
| CP-097 | P0 · eight of ten filings are superseded | **OPEN — LIVE** | `is_superseded = 1` on **1,064 of 27,825** delivered rows: `SUPERSEDED_BY_AMENDMENT` 958, `SUPERSEDED_BY_LATER_AMENDMENT` 106. Also `UNFLAGGED_DUPLICATE_CANDIDATE` 370, `AMBIGUOUS_MULTIPLE_ORIGINALS` 93, `AMBIGUOUS_ORIGINAL_POSTED_AFTER_AMENDMENT` 36. And 12 of 100 preview rows join to a superseded filing | lobbying | the supersession model is good and complete; nothing consumes it as a publication gate |
| CP-098 | P0 · seven of ten rows have no specific-issues text | **PARTIAL** | `specific_issues_text` blank on **8,326 of 27,825** (29.9%); `lobbying_issues_codes` blank on 5,102 | lobbying | improved against the sample rate but still blank on nearly a third of the product's headline field |
| CP-099 | P0 · termination filings with blank `termination_date` | **OPEN** | **1,233** filings whose `filing_type_display` contains `TERMINAT`; **457** of them (37.1%) have a blank `termination_date` | lobbying | — |
| CP-100 | P0 · client state disagrees with the resolved entity state | **OPEN** | `client_state != entity_state` on **1,850** rows where both are populated. Named filing `bdf7b163-…` not separately re-read | lobbying | a state disagreement is evidence of a bad match; none of the 1,850 is gated |
| CP-101 | P1 · `spend_usd` is copied from reported income | **PARTIAL** | `spend_basis` now names the source per row: `income` 16,283, `none_reported` 11,314, `expenses` 228 | lobbying | the basis is disclosed; 58.5% of the "spend" column is still income |
| CP-102 | P1 · `government_entities` pipe-delimited | **OPEN** | pipe present on **19,819 of 27,825** rows | lobbying | — |
| CP-103 | P1 · bill references left in prose | **OPEN** | no structured bill-id column exists in the 62 | lobbying | — |
| CP-104 | P1 · `pull_keyword`, `matched_alias`, matching internals exposed | **OPEN** | `match_confidence`, `matched_alias`, `pull_keyword`, `attribution_method` all delivered | lobbying | — |
| CP-105 | P1 · zero vs blank money not distinguished | **PARTIAL** | `spend_basis = none_reported` on 11,314 rows now separates "nothing reported" from a reported zero | lobbying | `income_usd` / `expenses_usd` themselves still mix 0 and blank |
| CP-106 | P2 · sample is 1999–2005 outside registrants only | **REJECTED as stated** | delivered `filing_year` spans **1999 – 2026** | lobbying | a sampler artefact; subsumed by CP-004 |

### Natural Resources (CP-107 – CP-115) — `natural-resources.csv`, 11,305 rows, 52 columns

| id | finding | status | measurement run 2026-09-03 | datasets | remaining limitation |
|---|---|---|---|---|---|
| CP-107 | P0 · nine of ten rows are one North Dakota series | **PARTIAL** | the concentration is a property of the population, not the sample: **26 distinct `recipient_entity_name`** in 11,305 rows, and the field is **blank on 9,840** of them (87.0%). Commodities do vary: Oil 2,589, Gas 2,397, Coal 778, Sand & gravel 764 | natural-resources | the blank-recipient rate is a larger problem than the one the review found and was not previously recorded |
| CP-108 | P0 · a federal IIJA reclamation grant sits alongside resource-tax revenue | **OPEN** | `revenue_type` and `source_system` columns exist; the taxonomy question was not re-adjudicated this pass | natural-resources | **unmeasured** — recorded OPEN for that reason |
| CP-109 | P1 · the note emphasises an $8M program while the row is $296,296.30 | **NOT_REPRODUCIBLE** | `RRE-OSMRE-IIJA-AMLIS1X-CROWTRIBE` not located by `resource_revenue_event_id` this pass | natural-resources | — |
| CP-110 | P1 · a one-time payment given a full fiscal-year period | **OPEN** | `period_type`, `period_start`, `period_end`, `payment_date` all delivered; the specific row was not located | natural-resources | **unmeasured** for the named row |
| CP-111 | P1 · the source URL is a generic search page | **OPEN** | `source_url` and `allocation_formula_source_url` delivered; durability not tested | natural-resources | fetching was out of scope for this pass |
| CP-112 | P1 · `cedar_uid_basis`, `record_scope_basis` cite internal register paths | **OPEN** | `cedar_uid_basis`, `record_scope_basis`, `entity_attribution_basis` all in the 52 delivered columns | natural-resources | — |
| CP-113 | P1 · 46 columns, 5 empty | **PARTIAL** | **52** columns today; **3** always-empty | natural-resources | wider file, fewer empties |
| CP-114 | P1 · `confidence = A` on every row | **PARTIAL** | `A` 10,815, `B` 490 — the grade now varies | natural-resources | 95.7% still `A` |
| CP-115 | P2 · allocation formulas repeated on every payment row | **OPEN** | `allocation_formula`, `allocation_formula_effective_start`, `allocation_formula_effective_end`, `amount_sign_meaning` delivered per row | natural-resources | — |

### NEST (CP-116 – CP-130) — `nest.csv`, 5,820 rows, 88 columns

| id | finding | status | measurement run 2026-09-03 | datasets | remaining limitation |
|---|---|---|---|---|---|
| CP-116 | P0 · Goldbelt Hawk assigned to Tlingit & Haida | **CLOSED in `nest`, OPEN in `contractors`** | in `nest.csv`, all **37** Goldbelt rows now name `Goldbelt, Incorporated` / `CE-0008Y-WE`; zero name Tlingit & Haida, and `Goldbelt Hawk, LLC`, `Goldbelt Hawk LLC (GbHawk)`, `Goldbelt Nighthawk, LLC`, `Goldbelt Seahawk` are all correct. In `contractors.csv` the same false parent survives on **1,148** rows (`C P Leasing, Inc`, parent `Goldbelt Incorporated`, canonical `Tlingit & Haida`, `CE-0006B-0K`) | nest (fixed), contractors (not) | a repair applied to one dataset and not propagated. Goldbelt, Incorporated is the Juneau urban ANCSA corporation; the Central Council of Tlingit & Haida is a federally recognised tribe. They are not the same entity |
| CP-117 | P0 · United Tribes Technical College assigned to United Auburn | **CLOSED** | zero rows in `nest.csv` match `UNITED TRIBES TECHNICAL` in either `enterprise_name` or `owner_hub_name`; in `funding.csv`, **2,879** UTTC rows exist and **0** carry `AUBURN` in `canonical_name` (uncapped, 701,955 rows) | nest, funding | UTTC's funding rows carry a blank `canonical_name` — the wrong answer was removed, no right answer was minted |
| CP-118 | P0 · the Tohono O'odham Nation emitted as an enterprise owned by itself | **OPEN — LIVE** | `ENTITY_IS_ITS_OWN_ENTERPRISE` = **234 of 5,820** rows. The named rows survive: `The Tohono O'Odham Nation` → hub `Tohono O'odham`, and `Tohono O'Odham Nation, The` → the same hub, both `publishable=Y`. The class is broad: `NATIVE VILLAGE OF AFOGNAK` → `Afognak`, `AKIACHAK NATIVE COMMUNITY` → `Akiachak`, and 231 more | nest | the fold deliberately keeps corporate forms distinguishing (`Afognak Native Corporation` ≠ `Afognak`), so 234 is a conservative count of self-reference, not a maximum |
| CP-119 | P0 · `cedar_uid` repeats the owner-hub UID | **OPEN** | `cedar_uid == owner_hub_cedar_uid` on **5,820 of 5,820** rows; `enterprise_existing_cedar_uid` populated on **103** | nest | the enterprise — the subject of the row — has no key of its own on 98.2% of rows |
| CP-120 | P0 · affiliation rows carry `assertion_class=OWNERSHIP` and `publishable=Y` | **CLOSED** | `relation_class = affiliation` **and** `assertion_class = OWNERSHIP` **and** `publishable = Y` → **0 of 5,820**. The two columns are now consistent: `affiliation`/`AFFILIATION` 4,325, `ownership`/`OWNERSHIP` 1,495 | nest | — |
| CP-121 | P0 · auto-only rows (`evidence_human_reviewed=N`) are publishable | **OPEN** | `evidence_human_reviewed = N` **and** `publishable = Y` on **3,910 of 5,820** rows (67.2%) | nest | — |
| CP-122 | P0 · rows flagged duplicate name variants remain separate and publishable | **OPEN** | `duplicate_name_variant_group` non-blank **and** `publishable = Y` on **144** rows | nest | the `FLAGGED, NOT MERGED` policy is unchanged |
| CP-123 | P1 · `source_url` values are not valid URLs | **CLOSED** | rows with a non-blank `source_url` that does not begin `http` → **0 of 5,820** | nest | — |
| CP-124 | P1 · several rows have no public source URL | **OPEN** | `source_url` blank on **2,519 of 5,820** rows (43.3%) | nest | — |
| CP-125 | P1 · `source_document` exposes `~/Desktop/dissertation/…` | **OPEN — LIVE** | `MACHINE_PATH_IN_CUSTOMER_FIELD` fires on **4,227 of 5,820** rows, all in `source_document`: `native_entity_enterprise_dataset_v6_geocoded.csv (the owner's research dataset, on this machine at ~/Desktop/dissertation/data/tribal…)` | nest | this is the single largest concentration of machine-path leakage in the delivered product |
| CP-126 | P1 · code paths, ledger filenames and reconciliation narrative in the core file | **OPEN** | code-lineage detector fires on `nest.csv` | nest | — |
| CP-127 | P1 · `status=operating` inferred from being named in a current source | **PARTIAL** | `status` now varies: `operating` 5,339, `last_seen_earlier` 270, `unknown` 211; `status_basis` is delivered | nest | 91.7% still `operating`; the inference is disclosed, not replaced |
| CP-128 | P1 · `sector` mixes supersectors, service lists and `Other services or Not given` | **OPEN** | **98 distinct** `sector` values across 5,820 rows | nest | — |
| CP-129 | P1 · rows asserted to a top-level owner while FPDS names an intermediate parent | **OPEN** | `fpds_parent_corroboration`, `fpds_parent_corroboration_route`, `fpds_declared_parent_name`, `fpds_parent_resolves_to` all delivered; disagreement rate not cross-tabbed | nest | **unmeasured** cross-tab |
| CP-130 | P1 · 68 columns of evidence counts, diagnostics and build metadata | **OPEN — worse** | **88** columns today, up from 68 | nest | — |

### Native Nonprofits (CP-131 – CP-145) — `nonprofits.csv`, 12,689 rows, 73 columns

| id | finding | status | measurement run 2026-09-03 | datasets | remaining limitation |
|---|---|---|---|---|---|
| CP-131 | P0 · eight of ten rows are `NATIVE_PROPOSED_AWAITING_OWNER_RULING` | **OPEN** | that literal disposition returns **0** — the vocabulary changed — but the state it named did not: `classification_ruling = UNRULED` on **12,366 of 12,689** rows (97.5%), against `place_name_coincidence` 309, `tribally_controlled` 8, `native_controlled` 6. Dispositions: `CANDIDATE_NAME_ONLY` 5,082, `EXCLUDED_PRIOR_RULING` 4,681, `CANDIDATE_NAME_MATCH_UNVERIFIED` 1,573, `NATIVE_VERIFIED_STRICT` 697 | nonprofits | a renamed state is not a closed finding. 97.5% of the delivered file is unruled |
| CP-132 | P0 · every row `placename_risk_flag=REVIEW` | **PARTIAL** | blank 9,001, `REVIEW` **2,330**, `HIGH` **1,358** — 29.1% still carry a risk flag | nonprofits | the flag is now discriminating; flagged rows still ship |
| CP-133 | P0 · a NC Tuscarora organisation keyed to the NY Tuscarora entity despite `HELD_STATE_DISAGREES` | **PARTIAL** | `key_review_disposition = HELD_STATE_DISAGREES` on **458** rows, all still delivered; the named EIN `874031049` was not separately re-read | nonprofits | the hold is recorded and the row ships anyway — same shape as CP-002 |
| CP-134 | P0 · low-confidence name-only linkage (Southern Cherokee Helpers) | **OPEN** | `disposition = CANDIDATE_NAME_ONLY` on **5,082** rows and `CANDIDATE_NAME_MATCH_GENERIC_TOKEN_ONLY` on **258** | nonprofits | — |
| CP-135 | P0 · an organisation keyed to United South and Eastern Tribes with a redirect proposed | **PARTIAL** | `key_review_disposition = REDIRECT_PROPOSED` on **12** rows; `key_redirect_proposed_entity_id` populated on **12** — a proposal exists and the original key still ships | nonprofits | named EIN `582328510` not separately re-read |
| CP-136 | P0 · revenue/assets/income exported as zero for 990-N organisations | **OPEN** | `bmf_revenue_amt` is the literal `0` on **5,269 of 12,689** rows | nonprofits | a true zero and an unfiled 990-N are indistinguishable in the delivered column |
| CP-137 | P1 · `cedar_uid` identifies a linked tribe, not the nonprofit; `entity_id` mostly blank | **OPEN** | `cedar_uid` blank on **12,134 of 12,689** (95.6%); `entity_id` blank on **12,605** (99.3%) | nonprofits | the nonprofit still has no subject ID. The changelog's identity work did not reach this file |
| CP-138 | P1 · evidence relies on Wikipedia, Yahoo, CauseIQ, ProPublica and agent narrative | **PARTIAL** | **278 of 12,689** rows (2.2%) cite one of those four in `evidence` — far below the sample rate | nonprofits | still 278 rows whose evidence is a search-result page |
| CP-139 | P1 · every row links to the generic IRS BMF landing page | **OPEN** | **1 distinct `source_url`** across 12,689 rows | nonprofits | — |
| CP-140 | P1 · pipeline bundle names and `agent_research` exposed | **OPEN** | code-lineage detector fires on `nonprofits.csv`: `placename_refusal_basis` 516, `exclusion_reason` 27, `entity_match_basis` 27 | nonprofits | — |
| CP-141 | P1 · the collection mixes governments, state-recognised organisations, controlled nonprofits and longhouses | **OPEN** | `classification_ruling` has only 4 values and 97.5% are `UNRULED`, so the collection is not yet typed at all | nonprofits | — |
| CP-142 | P1 · row name and evidence describe different organisations | **NOT_REPRODUCIBLE** | named EIN `320671686` not separately re-read this pass | nonprofits | — |
| CP-143 | P1 · `native_controlled` rulings rest on name and location | **PARTIAL** | only **6** rows are `native_controlled` in the whole file, so the exposure is small | nonprofits | governance evidence for those 6 was not inspected |
| CP-144 | P1 · 66 columns of token matches, coder counts, funnel stages, redirect proposals | **OPEN — worse** | **73** columns today; **0** always-empty | nonprofits | — |
| CP-145 | P2 · two-to-four coders agree while rows await owner ruling | **OPEN** | `n_coders_agree`: blank 7,018, 2 → 3,135, 3 → 1,999, 4 → 502, 5 → 35 — 5,671 rows carry a coder count while 12,366 are `UNRULED` | nonprofits | — |

### Native-Owned Businesses (CP-146 – CP-151) — `native-owned-businesses.csv`, 3,725 rows, 70 columns

| id | finding | status | measurement run 2026-09-03 | datasets | remaining limitation |
|---|---|---|---|---|---|
| CP-146 | P0 · the download contains zero business records | **CLOSED** | `dist/customer/native-owned-businesses.csv` holds **3,725 rows, 70 columns**, one row per harvested business (`business_source_id`, `business_name_raw`, `business_entity_name`) | native-owned-businesses | the flagship still has no column named `cedar_uid`; it names entities through `*_entity_id` columns (changelog §6.9) |
| CP-147 | P0 · the file is a fallback metadata export, wrongly named | **CLOSED** | no file named `owned-collection-description.csv` exists anywhere in the tree (`find . -name '*owned-collection-description*'` → 0); the delivered file is `native-owned-businesses.csv` and the storefront sample is `dist/samples/owned__sample.csv`, 10 business rows with 16 columns | native-owned-businesses | — |
| CP-148 | P0 · the collection copy is corrupted | **CLOSED** | the broken string is gone with the file; `native-owned-businesses__NOTES.txt` and `__CODEBOOK.md` are present and non-empty | native-owned-businesses | the copy was read for existence, not proofread |
| CP-149 | P1 · no fields for name, certifying nation, type, trade, location, status, source, as-of | **CLOSED** | all present and named: `business_name_raw`, `certifying_authority_name`, `programme_name`, `service_category_raw`, `city`, `state_province`, `certification_start`, `certification_expiration`, `harvest_date`, `source_url` | native-owned-businesses | — |
| CP-150 | P1 · certification provenance has no issuing office or terms | **CLOSED** | **37 distinct `certifying_authority_name`** values; `source_terms_status` is delivered (e.g. `TERMS_STATED_NO_REUSE_RESTRICTION`) | native-owned-businesses | terms are recorded per source, not per certification |
| CP-151 | P1 · the copy mixes TERO and commerce-office lists without saying whether rules differ | **PARTIAL** | `programme_name` now names the issuing programme per row: `Cherokee Nation TERO Directory` 836, `Chickasaw Business Directory` 602, `Navajo Business Opportunity Act source listing` 346, `MCN CESO Vendor List` 337, `Lummi Owned Businesses (LIBC business-licence report)` 140; `directory_type` distinguishes `tero` | native-owned-businesses | the programme is named; whether eligibility rules differ across the 37 authorities is still not stated |

---

## What could not be located or re-measured

Eight findings are `NOT_REPRODUCIBLE`. In every case the named artefact was searched for
by its own identifier and not found; none is recorded as closed on that basis.

| id | named artefact | search that failed |
|---|---|---|
| CP-053 | Federal Register document `95-6969` | not present in `fr_document_number` or `federal_register_citation` across 11,402 rows |
| CP-055 | Federal Register document `2011-8999` | same search |
| CP-051 | Federal Register document `2013-13468` | same search — the *finding* was partly re-measured (max 50 participant rows per citation), the *row* was not |
| CP-092 | NAGPRA document `03-10916` | not present in `document_number` across 6,792 rows |
| CP-109 | `RRE-OSMRE-IIJA-AMLIS1X-CROWTRIBE` | not present in `resource_revenue_event_id` across 11,305 rows |
| CP-142 | EIN `320671686` | not re-read; the finding is about evidence text, which needs a row-level read this pass did not run |
| CP-133 / CP-135 | EINs `874031049`, `582328510` | the *class* was measured (458 `HELD_STATE_DISAGREES`, 12 `REDIRECT_PROPOSED`); the named rows were not individually re-read |

Six further findings are recorded **OPEN with the word "unmeasured" in their limitation
column** — CP-058, CP-074, CP-081, CP-108, CP-110, CP-129. They are OPEN because nothing
was run that could close them, not because something was run and failed.

A prior-review artefact that could **not** be located at all: the reviewer referred to a
file named `cedar_press_sample_qa_review.md`. No such filename exists in the repo, on the
Desktop, or in any worktree. The document reconciled here is
`review/QA_REVIEW_10ROW_2026-09-02.txt`, which matches the description in every other
respect (12 collections, 10-row samples, DO NOT SHIP verdicts) but carries 151 findings,
not 142.

---

## The regression fixture pack

`code/1171_prior_finding_regression_pack.py`. Four modes; run `selftest` first.

```
py -3 code/1171_prior_finding_regression_pack.py selftest   # prove each detector fires
py -3 code/1171_prior_finding_regression_pack.py check      # full pass, exits 1 on any hit
py -3 code/1171_prior_finding_regression_pack.py check --quick   # 200k-row cap, prints CAPPED
py -3 code/1171_prior_finding_regression_pack.py ratchet    # fail only on an increase
```

**`selftest` is the load-bearing mode.** For each of the 23 detectors it writes a
two-row synthetic fixture — one clean row, one carrying the injected violation — and
asserts the detector returns ≥1 on the dirty row and exactly 0 on the clean one. Result
on 2026-09-03: **23 of 23 OK**. A detector that cannot be shown to fire is printed as
`NOT_TRUSTWORTHY` and the mode exits 1, so it cannot ship.

This is the reviewer's rule and it earned its place here twice in one pass:

- `FAILED_VOTE_RECORDED_AS_PASSED`, written naïvely, fired on `95-s-666` — a Senate bill
  that passed the Senate and then failed in the House, where `passed-one-chamber` is
  correct. Split into a bill-id-pinned assertion for the named Burt Lake row and a
  chamber-aware generalisation; the clean fixture for the generalisation is that Senate
  bill, so the false positive can never come back silently.
- `NAGPRA_COUNTY_CELL_HOLDS_SOURCE_PHRASE` returned 4 under an ad-hoc regex and **241**
  under the shipped one. The difference is `site in` and `River in`, which the first
  pattern did not carry. The low number looked like a nearly-closed finding.

**No baseline has been recorded.** `baseline` would write today's counts —
6,002 municipal-PHA misattributions, 1,148 Goldbelt misattributions, 227,540 quarantined
rows — as a ceiling, and a ceiling recorded over live P0 defects reads as a waiver. Run
`check` and read the truth; record a baseline once the P0 rows are zero and the residual
classes are the only thing left to ratchet.

## What a reader should do with this

1. `AVCP → Arctic Slope`, `Goldbelt → Tlingit & Haida`, the municipal PHAs, and the Union
   Calendar outcomes are wrong facts about real organisations that are shipping today.
   They outrank every schema item in this document.
2. Three of them were fixed **in one dataset and not another** — AVCP in `funding` but not
   `nest`; Goldbelt in `nest` but not `contractors`; UTTC in both. A per-dataset repair is
   not a repair. The fixture pack now reads every dataset for each named pair, which is
   the only reason two of the three were visible.
3. The publication gate the review asked for (CP-002) still does not exist. Four separate
   states — quarantined, superseded, withdrawn, unruled — each ship, each already modelled
   correctly, none consumed by an export gate.
