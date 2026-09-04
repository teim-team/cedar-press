# The thirteen delivered datasets — measured, not written

*Generated 2026-09-03 by `code/1162_twelve_dataset_report.py`. Every figure below is read off a file on disk when the report runs; nothing is typed, and anything this run could not measure says **UNMEASURED** rather than carrying a plausible number.*

Thirteen datasets are built. Twelve are sold on the Cedar Press storefront; `gaming` is built and gated to the same standard and is sold through Cedar Grove. A report about the deliverables covers all thirteen — an earlier version of this file iterated the preview directory, which the storefront-only preview builder writes, and so left the largest collection in the project out of a report about delivery.

### Where each figure comes from

| label | source | what it means |
|---|---|---|
| measured (delivered) | `code/1165_delivered_publication_audit.py`, a full uncapped pass over `dist/customer/*.csv` | read off the file the customer receives. `1165 selftest` injects each violation class and asserts the named detector fires. |
| measured (source) | a CSV-parser re-count of the flagship table | records, not physical lines; a quoted field may contain a newline. |
| builder's record | `dist/customer/MANIFEST.csv` | what `1137` says it did. Its row and column counts are checked against the measured ones below; a disagreement is printed as a defect. |

## The thirteen, as delivered

| dataset | shelf | sold through | rows | columns | file size | preview rows | empty columns |
|---|---|---|---:|---:|---:|---:|---:|
| `contractors` | pro | Cedar Press | 1,217,768 | 79 | 1,485.4 MB | 100 | 0 |
| `deals` | standard | Cedar Press | 1,073 | 60 | 2.0 MB | 100 | 0 |
| `federal-register` | standard | Cedar Press | 11,402 | 45 | 16.9 MB | 100 | 0 |
| `funding` | standard | Cedar Press | 701,955 | 79 | 605.3 MB | 100 | 14 |
| `gaming` | grove | Cedar Grove | 787 | 312 | 4.2 MB | none | 10 |
| `legislation` | standard | Cedar Press | 3,069 | 65 | 5.3 MB | 100 | 1 |
| `lobbying` | standard | Cedar Press | 27,825 | 62 | 21.2 MB | 100 | 0 |
| `nagpra` | standard | Cedar Press | 6,792 | 76 | 11.8 MB | 100 | 1 |
| `native-owned-businesses` | pro | Cedar Press | 3,725 | 70 | 5.8 MB | 100 | 3 |
| `natural-resources` | pro | Cedar Press | 11,305 | 52 | 24.4 MB | 100 | 3 |
| `nest` | pro | Cedar Press | 5,820 | 88 | 9.6 MB | 100 | 0 |
| `nonprofits` | pro | Cedar Press | 12,689 | 73 | 14.1 MB | 100 | 0 |
| `subcontracting` | pro | Cedar Press | 70,597 | 86 | 91.4 MB | 100 | 1 |
| **total** | | | **2,074,807** | | **2.30 GB** | | |

`gaming` has no preview file: `1151` writes previews for the 12 storefront datasets only. That is a fact about the preview builder, not about the delivery.

**Manifest against measurement.** 13 datasets checked on rows and on columns; 0 disagreement(s).

## The publication rules, checked in the delivered files

Masking and column-dropping happen at export, so `data/clean` is the wrong place to look for them and `MANIFEST.csv` is the writer grading its own homework. These are read off `dist/customer/`.

| rule | what must be true | measured |
|---|---|---|
| personal-data columns (`NEVER`) | absent from every delivered header | **0** present across 13 headers |
| licensed proprietary identifiers (`DROP_COLS`) | absent from every delivered header | **0** present |
| build-lineage columns | absent from every delivered header | **0** present |
| rows in a WITHHOLD adjudication state | none delivered | **0** delivered |
| rows in a state the policy does not enumerate | none delivered (deny-by-default) | **0** delivered |
| a MASK row still carrying its Cedar attribution | none | **0** cells |
| a quarantined non-tier-A row still carrying its attribution | none | **0** cells |
| rows with more fields than the header | none | **0** |
| retired NEID columns, by NAME | absent from every delivered header | **0** present |
| retired NEID identifiers, by VALUE | none delivered | **89,680** identifier(s) on **52,817** rows |

**The quarantine rows are still in the file, and that is the policy.** 227,540 delivered rows carry `identifier_ruling_quarantined = Y` with a tier other than A, and 0 carry tier A. `BLOCKED_COMBINATIONS` disposes the first set MASK, not WITHHOLD: the award is a real federal record and ships, while the Cedar attribution on it does not. Reporting only the leak count of 0 would leave a reader to assume those rows were dropped.

**The subaward fence has two legs and they are different kinds of rule.** `duplicate_status == 'primary'` is a ROW gate — the other two `duplicate_status` values are WITHHOLD and may not ship. `subaward_exceeds_prime_flag != 'yes'` is a MONEY fence — those rows are real filings, they ship flagged, and they are excluded from the countable total. Measured in the delivered file:

| leg | measured |
|---|---|
| `duplicate_status` | `primary` = 70,597 |
| `subaward_exceeds_prime_flag` | `(blank)` = 69,921; `yes` = 676 |
| `subaward_amount` | $42,172,721,583.24 summed over every delivered row against $34,906,694,737.65 over the 69,921 rows inside the fence |

**The lobbying money fence.** Superseded LDA filings are PUBLISHED with their supersession stated — an amendment restating an original's money is a money rule, not a row rule. The fence is `supersession_status NOT IN ('SUPERSEDED_BY_AMENDMENT', 'SUPERSEDED_BY_LATER_AMENDMENT', 'UNFLAGGED_DUPLICATE_CANDIDATE', 'AMBIGUOUS_MULTIPLE_ORIGINALS', 'AMBIGUOUS_ORIGINAL_POSTED_AFTER_AMENDMENT')` AND `attribution_withdrawn != '1'`.

## The retired NEID identifiers (owner ruling, 2026-09-03)

The CICD/NEID identifiers are retired; Cedar's own key is the identity. `cedar_publication.publishable_columns()` now drops `NEID_COLS` and `PROPOSED_COLS` at export, which puts the rule on the whole publication surface instead of the three files `code/843_retire_cicd_scheme.py` named by hand.

**By column name, the retirement landed.** Measured in the delivered headers: 0 retired column name(s) survive across the thirteen files.

**By VALUE, it did not.** A name gate cannot see the same identifier arriving in a column called something else, and that is what the delivered files hold. Every count below is a full pass over the delivered file, testing each cell — and each token of a pipe-delimited cell — for membership in the 1,562-value NEID vocabulary harvested from `data/clean` and `data/spine`, not against a shape:

| dataset | column | rows | identifiers | example |
|---|---|---:|---:|---|
| `deals` | `native_party_entity_id` | 959 | 959 | `TRBF-MHEGAN-00` |
| `gaming` | `entity_id` | 228 | 228 | `AKNF-VLKAKE-00-SEALSK-TLNGHD` |
| `gaming` | `loyalty_programs__operator_entity_id` | 131 | 131 | `TRBF-POARCH-00` |
| `lobbying` | `attribution_withdrawn_entity_id` | 471 | 471 | `TRBF-SROSAR-00` |
| `lobbying` | `entity_id` | 26,513 | 26,513 | `TRBF-FALLON-00` |
| `nagpra` | `aboriginal_land_entity_ids` | 595 | 3,897 | `TRBF-PNBSCT-00` |
| `nagpra` | `affiliated_entity_ids` | 5,022 | 18,972 | `TRBF-CHYNRV-00` |
| `nagpra` | `consulted_entity_ids` | 2,698 | 17,104 | `NHO-FFCHWN-00` |
| `nagpra` | `disposition_priority_entity_ids` | 445 | 2,517 | `TRBS-MSSISQ-00` |
| `nagpra` | `letter_of_support_entity_ids` | 4 | 8 | `TRBF-ALCOUS-00` |
| `nagpra` | `repatriation_recipient_entity_ids` | 1,625 | 4,754 | `TRBF-ZUNINM-00` |
| `native-owned-businesses` | `business_entity_id` | 5 | 5 | `CEDAR-ENT-000092` |
| `native-owned-businesses` | `certifying_authority_entity_id` | 3,576 | 3,576 | `TRBF-TULALP-00` |
| `natural-resources` | `beneficiary_entity_id` | 586 | 586 | `TRBF-CROWMT-00` |
| `natural-resources` | `payer_entity_id` | 67 | 67 | `ANRC-ALEUTC-00` |
| `natural-resources` | `recipient_entity_id` | 705 | 705 | `ANRC-AHTNAI-00` |
| `nest` | `fpds_parent_resolves_to` | 361 | 361 | `AKNF-ALGACQ-00-CALSTA-ASVCPR` |
| `nest` | `nest_entity_dual_role__handle` | 2,319 | 2,319 | `AKNF-AGDAGX-00-ALEUTC-PRBLFA` |
| `nest` | `owner_hub_handle` | 5,820 | 5,820 | `AKNF-AFGNAK-00-KONIAG` |
| `nonprofits` | `cedar_spine_entity_id` | 591 | 591 | `ANRC-AHTNAI-00` |
| `nonprofits` | `entity_id` | 84 | 84 | `AKNF-YKTTLN-00-SEALSK-TLNGHD` |
| `nonprofits` | `key_redirect_proposed_entity_id` | 12 | 12 | `CDFI-YRKLLN-00` |
| **total** | **22 column(s) in 8 dataset(s)** | **52,817** | **89,680** | |

Screened and **not** counted above: `contractors.award_base_description` 3 cell(s); `subcontracting.subaward_number` 565 cell(s). These match the NEID shape and are absent from the vocabulary — `contractors.award_base_description` holds `DPW-00229-01` inside a contract description and `subcontracting.subaward_number` holds `SR-2012-11`. A shape test alone reported 568 of these as violations and missed 2,173 real identifiers, which is why membership is the test.

**Which datasets can still name an entity.** A dataset whose only entity key was a NEID has nothing left after the retirement, and no row-count or column-count check can see that — dropping a column never fails a row count.

| dataset | Cedar identity column(s) in the delivered header | filled |
|---|---|---:|
| `contractors` | `cedar_uid` | `cedar_uid` 625,787 |
| `deals` | `cedar_uid` | `cedar_uid` 959 |
| `federal-register` | `cedar_uid` | `cedar_uid` 10,396 |
| `funding` | `cedar_uid` | `cedar_uid` 552,756 |
| `gaming` | `cedar_uid` | `cedar_uid` 785 |
| `legislation` | `entity_cedar_uids` | `entity_cedar_uids` 591 |
| `lobbying` | `cedar_uid` | `cedar_uid` 26,513 |
| `nagpra` | **NONE** | — |
| `native-owned-businesses` | **NONE** | — |
| `natural-resources` | `cedar_uid` | `cedar_uid` 705 |
| `nest` | `cedar_uid` | `cedar_uid` 5,820 |
| `nonprofits` | `cedar_uid`, `cedar_spine_entity_id` | `cedar_uid` 555; `cedar_spine_entity_id` 591 |
| `subcontracting` | `cedar_uid`, `prime_cedar_uid`, `sub_cedar_uid` | `cedar_uid` 32,369; `prime_cedar_uid` 32,203; `sub_cedar_uid` 38,563 |

**An identity-named column holding retired identifiers.** `nonprofits.cedar_spine_entity_id` is 591 of 591 populated rows. The name says Cedar; the values are NEIDs. The table above is built from column NAMES, so it credits these as identity coverage — read them out of it.

**`nagpra`, `native-owned-businesses` carry no `cedar_uid` under any spelling.** This is NOT a regression from the retirement — their flagship tables never held one, and their delivered column counts did not move — but it is the condition that makes the retirement bite: their only entity keys are `*_entity_id` / `*_entity_ids` columns holding the retired identifiers. Until Cedar's key is promoted onto them, applying the ruling to those columns would leave the datasets unable to name a party at all.

**`funding` lost six columns and that is a CORRECTION, not a regression.** Four are internal working columns: `ledger_proposed_tribe_id`, `tribe_id_neid_proposed`, `tribe_id_neid_proposed_tier` and `tribe_id_neid_proposed_basis` are proposals that `843` states are never shipped, and 67,826 funding rows carried a proposed NEID with no `cedar_uid` — rows with no settled identity at all, advertising one. Two more columns went with them: `tribe_id_neid` itself and `bie_uio_dollars_by_entity__tribe_id`, which was populated on zero rows. A no-regression gate reading the drop in populated-identity cells as a loss would be reading a correction as damage.

## Per dataset

### `contractors` — Federal Prime Contracting

`1,217,768` rows × `79` columns · 1,485.4 MB · shelf `pro` · sold through Cedar Press — *measured (delivered)*

**What one row is.** TWO populations under one schema, and the seam is real. Archive rows (FY2008-FY2026, source_file `FY*_All_Contracts_Full_*.zip`): one row per FPDS TRANSACTION, identified by `contract_transaction_unique_key`. BGOV rows (`master prime file.dta`): one row per (contract, parent vehicle, fiscal year, ve

**Join provenance.** Flagship table `prime_contracts.csv`, measured at 1,217,768 rows. *(builder's record for the rest of this paragraph.)*

_No supporting table met the one-to-one test; the substantive columns are the flagship's own._

Counted, **not** joined. These are one-to-many on the shared key; joining them would multiply the flagship's rows and inflate every money total, so each contributes a count column instead:

- `fpds_uei_cage_map(1:many on cage_code -> n_fpds_uei_cage_map)`
- `prime_contracts_archive_backfill(1:many on cage_code -> n_prime_contracts_archive_backfill)`
- `prime_contracts_awards(1:many on cage_code -> n_prime_contracts_awards)`
- `prime_contracts_entity_year(1:many on cedar_uid -> n_prime_contracts_entity_year)`
- `prime_contracts_published(1:many on cage_code -> n_prime_contracts_published)`
- `sam_prime_contracts_fy2000_2007(1:many on cage_code -> n_sam_prime_contracts_fy2000_2007)`
- `sam_prime_contracts_fy2000_2007_PUBLISHABLE(1:many on cage_code -> n_sam_prime_contracts_fy2000_2007_PUBLISHABLE)`

Measured in the delivered header: 0 column(s) carry a join prefix, from 0 source table(s); 7 count column(s).

**What was withheld, and why.**

- Measured: the flagship holds 1,217,768 rows and 1,217,768 were delivered — **0 row(s) not delivered**.
- Builder's per-reason breakdown: none — no row was withheld.

**What was masked.** A MASK keeps the row — a real public record — and withholds the Cedar attribution on it.

- Measured (delivered), one row one disposition, from `cedar_publication.adjudication()`: `FLAG` = 527,489; `MASK` = 351,438; `PUBLISH` = 338,841
- Builder's record of masks that actually cleared a cell: 166,166 row(s) — `identifier_ruling_review=HOLD=12063; identifier_ruling_review=WITHDRAWN_BY_1079=4487; owner_attribution_status=CONTRADICTED_AS_OF=9223; quarantined_method_not_ruled_tier_A=100114; ruling_status=RULED_CLASS_ONLY=3962; ruling_status=RULED_HOLD=16468; ruling_status=RULED_NAME_KEY_ONLY_NOT_ATTRIBUTED=7703; ruling_status=RULED_NOT_NATIVE=558; ruling_status=RULING_CONFLICT=11588`
- The two differ (351,438 rows adjudicated MASK against 166,166 recorded) because a mask on a row whose attribution columns were **already blank** clears nothing and is not counted by the builder. Both are correct about what they measure.

**Known defects.**

- 1,217,768 rows exceeds Excel's 1,048,576-row sheet limit; every other reader (R, Stata, pandas, DuckDB, Power BI) opens the whole file
- 1,485 MB exceeds GitHub's 100 MB file limit — a hosting problem, not a reason to split the dataset

Headings in `docs/KNOWN_ISSUES.md` that MENTION `contractors` — a mention, found by substring, not a finding about this dataset:

- B2 · S1 · `contractor_ranking.csv` carries no ownership status at all
- C4 · S2 · Nine grain rulings only a human can make
- L2 · S2 · The McGrath hub's whole distinctive name is one common surname
- M1 · OPEN, BLOCKING A SHIP · `dist/customer/contractors.csv` does not exist
- M5 · NOT A DEFECT, BUT DO NOT COUNT IT AS LINKAGE
- QA-STATUS-VOCAB · S1 · OPEN · `RULED_ATTRIBUTED` can mean "a quarantined resolver guessed", and that naming cost an escalation

### `deals` — Indian Country Deals

`1,073` rows × `60` columns · 2.0 MB · shelf `standard` · sold through Cedar Press — *measured (delivered)*

**What one row is.** one row per classified deal event - the merged deals ledger

**Join provenance.** Flagship table `deals_classified.csv`, measured at 1,073 rows. *(builder's record for the rest of this paragraph.)*

_No supporting table met the one-to-one test; the substantive columns are the flagship's own._

Counted, **not** joined. These are one-to-many on the shared key; joining them would multiply the flagship's rows and inflate every money total, so each contributes a count column instead:

- `ownership_events(1:many on cedar_uid -> n_ownership_events)`
- `seminole_bond_disclosures(1:many on cedar_uid -> n_seminole_bond_disclosures)`
- `tribal_resolution_financings(1:many on cedar_uid -> n_tribal_resolution_financings)`

Measured in the delivered header: 0 column(s) carry a join prefix, from 0 source table(s); 3 count column(s).

**What was withheld, and why.**

- Measured: the flagship holds 1,073 rows and 1,073 were delivered — **0 row(s) not delivered**.
- Builder's per-reason breakdown: none — no row was withheld.

**What was masked.** A MASK keeps the row — a real public record — and withholds the Cedar attribution on it.

- Measured (delivered), one row one disposition, from `cedar_publication.adjudication()`: `PUBLISH` = 1,073
- Builder's record of masks that actually cleared a cell: 0 row(s).

**Known defects.**

- retired NEID identifiers still ship as VALUES in `native_party_entity_id` — 959 row(s), 959 identifier(s) (e.g. `TRBF-MHEGAN-00`). The 2026-09-03 retirement dropped the NEID columns by NAME; a name gate cannot see the same identifier under another column name
- 1 column(s) are under 10% populated — real, but do not build a headline on them: `Event_Date_source_value_verbatim`

Headings in `docs/KNOWN_ISSUES.md` that MENTION `deals` — a mention, found by substring, not a finding about this dataset:

- A2 · S3 · Three collections were documented as planning a script "not in the repository" — all three scripts exist
- A3 · S2 · Three dataset runbooks named build scripts that have never existed
- A5 [RESOLVED 2026-09-02 — see note at end] · S1 · The arbiter document of last resort had gone stale in 6 of 14 rows
- C4 · S2 · Nine grain rulings only a human can make
- C8 · S2 · Three tables cannot ship until a publication decision is made
- Corroboration: what the family count exposed (workstream CORROBORATION, 2026-09-02)

### `federal-register` — Federal Register

`11,402` rows × `45` columns · 16.9 MB · shelf `standard` · sold through Cedar Press — *measured (delivered)*

**What one row is.** one row per (consultation event, participant as published), and a consultation event is ONE FEDERAL REGISTER DOCUMENT - `consultation_event_id` is 1:1 with `fr_document_number`, 2,313 of each over 11,402 rows. ONE DOCUMENT BECOMES UP TO 50 ROWS: max 50, p95 21, median 1, mean 4.93; 1,009 documents c

**Join provenance.** Flagship table `consultation_events.csv`, measured at 11,402 rows. *(builder's record for the rest of this paragraph.)*

_No supporting table met the one-to-one test; the substantive columns are the flagship's own._

Counted, **not** joined. These are one-to-many on the shared key; joining them would multiply the flagship's rows and inflate every money total, so each contributes a count column instead:

- `federal_actions_entity_bridge(1:many on cedar_uid -> n_federal_actions_entity_bridge)`
- `fr_ex_parte_parties(1:many on cedar_uid -> n_fr_ex_parte_parties)`
- `fr_ex_parte_party_entity_links(1:many on cedar_uid -> n_fr_ex_parte_party_entity_links)`
- `nepa_administrative_record_parties(1:many on cedar_uid -> n_nepa_administrative_record_parties)`
- `section_106_consultation_events(1:many on cedar_uid -> n_section_106_consultation_events)`
- `section_106_project_parties(1:many on cedar_uid -> n_section_106_project_parties)`

Measured in the delivered header: 0 column(s) carry a join prefix, from 0 source table(s); 7 count column(s).

**What was withheld, and why.**

- Measured: the flagship holds 11,402 rows and 11,402 were delivered — **0 row(s) not delivered**.
- Builder's per-reason breakdown: none — no row was withheld.

**What was masked.** A MASK keeps the row — a real public record — and withholds the Cedar attribution on it.

- Measured (delivered), one row one disposition, from `cedar_publication.adjudication()`: `PUBLISH` = 11,402
- Builder's record of masks that actually cleared a cell: 0 row(s).

**Known defects.**

- 8 column(s) are under 10% populated — real, but do not build a headline on them: `event_date_basis`, `event_date_source_quote`, `event_end_date`, `event_start_date`, `format`, `location`, `location_basis`, `location_source_quote`

Headings in `docs/KNOWN_ISSUES.md` that MENTION `federal-register` — a mention, found by substring, not a finding about this dataset:

- A11 · S3 · `START_HERE.md` said READY 0 / 13
- C8 · S2 · Three tables cannot ship until a publication decision is made
- D1 · S1 · `503_identity.py` would REINTRODUCE the retired CICD scheme on its next rebuild
- M5 · NOT A DEFECT, BUT DO NOT COUNT IT AS LINKAGE

### `funding` — Federal Funding to Indian Country

`701,955` rows × `79` columns · 605.3 MB · shelf `standard` · sold through Cedar Press — *measured (delivered)*

**What one row is.** one row per federal assistance award TRANSACTION, across the union of the assistance and archive pulls

**Join provenance.** Flagship table `federal_funding_transactions.csv`, measured at 701,955 rows. *(builder's record for the rest of this paragraph.)*

Folded in one-to-one, cardinality re-measured on the rows actually loaded rather than trusted from the contracts file:

- `bie_uio_dollars_by_entity(cedar_uid)`

Counted, **not** joined. These are one-to-many on the shared key; joining them would multiply the flagship's rows and inflate every money total, so each contributes a count column instead:

- `faads_entity_attribution(1:many on cedar_uid -> n_faads_entity_attribution)`
- `faads_transactions(1:many on cedar_uid -> n_faads_transactions)`
- `faads_transactions_all_agencies(1:many on cedar_uid -> n_faads_transactions_all_agencies)`
- `federal_funding_tribe_year_panel(1:many on cedar_uid -> n_federal_funding_tribe_year_panel)`

Measured in the delivered header: 12 column(s) carry a join prefix, from 1 source table(s) — `bie_uio_dollars_by_entity`; 4 count column(s).

**What was withheld, and why.**

- Measured: the flagship holds 701,955 rows and 701,955 were delivered — **0 row(s) not delivered**.
- Builder's per-reason breakdown: none — no row was withheld.

**What was masked.** A MASK keeps the row — a real public record — and withholds the Cedar attribution on it.

- Measured (delivered), one row one disposition, from `cedar_publication.adjudication()`: `PUBLISH` = 701,955
- Builder's record of masks that actually cleared a cell: 0 row(s).

**Known defects.**

- 605 MB exceeds GitHub's 100 MB file limit — a hosting problem, not a reason to split the dataset
- 14 column(s) are blank on every delivered row and are kept deliberately: `geo_pop_place_dominance_share`, `geo_pop_place_ambiguous`, `bie_uio_dollars_by_entity__entity_class`, `bie_uio_dollars_by_entity__bie_operation_type`, `bie_uio_dollars_by_entity__parent_native_entity`, `bie_uio_dollars_by_entity__rolls_up_to_a_tribe`, `bie_uio_dollars_by_entity__total_usd`, `bie_uio_dollars_by_entity__usd_faads_all_agencies`, `bie_uio_dollars_by_entity__usd_federal_funding`, `bie_uio_dollars_by_entity__usd_nonprofit_990`, `bie_uio_dollars_by_entity__usd_prime_contracts`, `bie_uio_dollars_by_entity__usd_subawards` … — dropping blank columns would make the schema depend on which rows shipped
- 3 column(s) are under 10% populated — real, but do not build a headline on them: `exclusion_reason`, `exclusion_rule`, `exclusion_source_line`

Headings in `docs/KNOWN_ISSUES.md` that MENTION `funding` — a mention, found by substring, not a finding about this dataset:

- A5 [RESOLVED 2026-09-02 — see note at end] · S1 · The arbiter document of last resort had gone stale in 6 of 14 rows
- C1 · S1 · `faads_transactions_all_agencies.csv` — 179,259 duplicate rows, diagnosed, not repaired
- C2 · S1 · `subawards.csv` — 10,770 duplicate rows, same shape suspected, unproven
- C8 · S2 · Three tables cannot ship until a publication decision is made
- STANDARD — do not act on these punch-list lines (2026-09-02)
- What stands, and what was deliberately not done

### `gaming` — Gaming Intelligence

`787` rows × `312` columns · 4.2 MB · shelf `grove` · sold through Cedar Grove — *measured (delivered)*

**What one row is.** one row per gaming facility - the directory core, docs/GAMING_BUILD_LOG_2026-08-05.md

**Join provenance.** Flagship table `gaming_facilities.csv`, measured at 787 rows. *(builder's record for the rest of this paragraph.)*

Folded in one-to-one, cardinality re-measured on the rows actually loaded rather than trusted from the contracts file:

- `gaming_nigc_roster_link(facility_id)`
- `gaming_properties(facility_id)`
- `gaming_property_federal_traces(facility_id)`
- `loyalty_program_property(facility_id)`
- `loyalty_programs(cedar_uid)`

Counted, **not** joined. These are one-to-many on the shared key; joining them would multiply the flagship's rows and inflate every money total, so each contributes a count column instead:

- `ca_gaming_facilities_official(1:many on facility_id -> n_ca_gaming_facilities_official)`
- `ca_gaming_payments(1:many on cedar_uid -> n_ca_gaming_payments)`
- `compact_events(1:many on cedar_uid -> n_compact_events)`
- `compact_obligation_tribal_agency_bridge(1:many on cedar_uid -> n_compact_obligation_tribal_agency_bridge)`
- `compact_required_reports(1:many on cedar_uid -> n_compact_required_reports)`
- `compact_structured_terms(1:many on cedar_uid -> n_compact_structured_terms)`
- `compact_terms(1:many on cedar_uid -> n_compact_terms)`
- `compacts(1:many on cedar_uid -> n_compacts)`
- `digital_gaming_relationships(1:many on facility_id -> n_digital_gaming_relationships)`
- `digital_gaming_revenue(1:many on facility_id -> n_digital_gaming_revenue)`
- `fac_audit_gaming_disclosures(1:many on cedar_uid -> n_fac_audit_gaming_disclosures)`
- `fac_audit_sefa_gaming_programs(1:many on cedar_uid -> n_fac_audit_sefa_gaming_programs)`
- `fl_gaming_payments(1:many on facility_id -> n_fl_gaming_payments)`
- `gaming_capacity_official(1:many on facility_id -> n_gaming_capacity_official)`
- `gaming_device_observations(1:many on facility_id -> n_gaming_device_observations)`
- `gaming_employment_observations(1:many on facility_id -> n_gaming_employment_observations)`
- `gaming_financing_events(1:many on cedar_uid -> n_gaming_financing_events)`
- `gaming_game_finder_observations(1:many on facility_id -> n_gaming_game_finder_observations)`
- `gaming_land_decisions(1:many on cedar_uid -> n_gaming_land_decisions)`
- `gaming_ordinance_ocr(1:many on cedar_uid -> n_gaming_ordinance_ocr)`
- `gaming_ordinances(1:many on cedar_uid -> n_gaming_ordinances)`
- `gaming_project_facilities(1:many on cedar_uid -> n_gaming_project_facilities)`
- `gaming_property_labor_demand(1:many on facility_id -> n_gaming_property_labor_demand)`
- `gaming_property_self_published_assertions(1:many on facility_id -> n_gaming_property_self_published_assertions)`
- `gaming_property_self_published_claims(1:many on facility_id -> n_gaming_property_self_published_claims)`
- `gaming_property_site_observations(1:many on facility_id -> n_gaming_property_site_observations)`
- `gaming_property_universe_events(1:many on facility_id -> n_gaming_property_universe_events)`
- `gaming_revenue_bounds(1:many on facility_id -> n_gaming_revenue_bounds)`
- `gaming_vendor_tribal_licenses(1:many on cedar_uid -> n_gaming_vendor_tribal_licenses)`
- `nigc_action_parties(1:many on cedar_uid -> n_nigc_action_parties)`
- `nigc_declination_letters(1:many on cedar_uid -> n_nigc_declination_letters)`
- `nigc_enforcement_actions(1:many on cedar_uid -> n_nigc_enforcement_actions)`
- `nigc_indian_lands_opinions(1:many on cedar_uid -> n_nigc_indian_lands_opinions)`
- `nigc_management_contract_approvals(1:many on cedar_uid -> n_nigc_management_contract_approvals)`
- `nigc_region_assignments(1:many on facility_id -> n_nigc_region_assignments)`
- `sec_gaming_financial_disclosures(1:many on facility_id -> n_sec_gaming_financial_disclosures)`
- `sec_gaming_management_contract_terms(1:many on facility_id -> n_sec_gaming_management_contract_terms)`
- `state_gaming_observations(1:many on facility_id -> n_state_gaming_observations)`
- `wa_machine_allocations(1:many on cedar_uid -> n_wa_machine_allocations)`

Measured in the delivered header: 146 column(s) carry a join prefix, from 5 source table(s) — `gaming_nigc_roster_link`, `gaming_properties`, `gaming_property_federal_traces`, `loyalty_program_property`, `loyalty_programs`; 43 count column(s).

**What was withheld, and why.**

- Measured: the flagship holds 787 rows and 787 were delivered — **0 row(s) not delivered**.
- Builder's per-reason breakdown: none — no row was withheld.

**What was masked.** A MASK keeps the row — a real public record — and withholds the Cedar attribution on it.

- Measured (delivered), one row one disposition, from `cedar_publication.adjudication()`: `PUBLISH` = 787
- Builder's record of masks that actually cleared a cell: 0 row(s).

**Known defects.**

- retired NEID identifiers still ship as VALUES in `entity_id` — 228 row(s), 228 identifier(s) (e.g. `AKNF-VLKAKE-00-SEALSK-TLNGHD`). The 2026-09-03 retirement dropped the NEID columns by NAME; a name gate cannot see the same identifier under another column name
- retired NEID identifiers still ship as VALUES in `loyalty_programs__operator_entity_id` — 131 row(s), 131 identifier(s) (e.g. `TRBF-POARCH-00`). The 2026-09-03 retirement dropped the NEID columns by NAME; a name gate cannot see the same identifier under another column name
- 10 column(s) are blank on every delivered row and are kept deliberately: `gaming_properties__source_url`, `loyalty_program_property__source_url`, `loyalty_programs__start_date`, `loyalty_programs__end_date`, `loyalty_programs__tier_names`, `loyalty_programs__tier_thresholds`, `loyalty_programs__earning_currency`, `loyalty_programs__digital_wallet`, `loyalty_programs__cashless_gaming`, `loyalty_programs__source_url` — dropping blank columns would make the schema depend on which rows shipped
- 32 column(s) are under 10% populated — real, but do not build a headline on them: `cedar_place_id_absent_reason`, `close_date_precedes_open_date`, `close_date_source_url`, `close_date_source_value_placeholder`, `close_date_source_value_placeholder_basis`, `close_date_source_value_verbatim`, `duplicate_of_facility_id`, `interim_open_date`, `interim_open_date_basis`, `interim_open_note` …

Headings in `docs/KNOWN_ISSUES.md` that MENTION `gaming` — a mention, found by substring, not a finding about this dataset:

- A3 · S2 · Three dataset runbooks named build scripts that have never existed
- A16 · S3 · The three "undocumented tables" in the gate and the three standing owner items were the same three tables
- C4 · S2 · Nine grain rulings only a human can make
- C8 · S2 · Three tables cannot ship until a publication decision is made
- D2 · S2 · `docs/WHAT_IS_MISSING.md` carries two figures that do not reproduce
- STANDARD — do not act on these punch-list lines (2026-09-02)

### `legislation` — Congressional Votes and Proposed Legislation

`3,069` rows × `65` columns · 5.3 MB · shelf `standard` · sold through Cedar Press — *measured (delivered)*

**What one row is.** one row per Native-relevant bill

**Join provenance.** Flagship table `native_bills.csv`, measured at 3,069 rows. *(builder's record for the rest of this paragraph.)*

Folded in one-to-one, cardinality re-measured on the rows actually loaded rather than trusted from the contracts file:

- `native_bill_action_coverage(bill_id)`
- `native_bill_cosponsor_coverage(bill_id)`

Counted, **not** joined. These are one-to-many on the shared key; joining them would multiply the flagship's rows and inflate every money total, so each contributes a count column instead:

- `bill_votes(1:many on bill_id -> n_bill_votes)`
- `bill_votes_entity_bridge(1:many on bill_id -> n_bill_votes_entity_bridge)`
- `member_positions(1:many on bill_id -> n_member_positions)`
- `native_bill_actions(1:many on bill_id -> n_native_bill_actions)`
- `native_bill_cosponsors(1:many on bill_id -> n_native_bill_cosponsors)`
- `native_bill_outcomes(1:many on bill_id -> n_native_bill_outcomes)`
- `native_bills_entity_bridge(1:many on bill_id -> n_native_bills_entity_bridge)`
- `native_bills_entity_class(1:many on bill_id -> n_native_bills_entity_class)`
- `native_bills_subject_sweep(1:many on bill_id -> n_native_bills_subject_sweep)`

Measured in the delivered header: 19 column(s) carry a join prefix, from 2 source table(s) — `native_bill_action_coverage`, `native_bill_cosponsor_coverage`; 12 count column(s).

**What was withheld, and why.**

- Measured: the flagship holds 3,069 rows and 3,069 were delivered — **0 row(s) not delivered**.
- Builder's per-reason breakdown: none — no row was withheld.

**What was masked.** A MASK keeps the row — a real public record — and withholds the Cedar attribution on it.

- Measured (delivered), one row one disposition, from `cedar_publication.adjudication()`: `PUBLISH` = 3,069
- Builder's record of masks that actually cleared a cell: 0 row(s).

**Known defects.**

- 1 column(s) are blank on every delivered row and are kept deliberately: `affected_entities` — dropping blank columns would make the schema depend on which rows shipped
- 1 column(s) are under 10% populated — real, but do not build a headline on them: `classification_kappa`

Headings in `docs/KNOWN_ISSUES.md` that MENTION `legislation` — a mention, found by substring, not a finding about this dataset:

- ~~OPEN~~ **RESOLVED 2026-09-02** — the collapsed-escape defect is not confined to `846`. SEVEN more live scripts carry it, and one of them is the iden
- RESOLVED — all 41 collapsed escapes repaired, every one measured before and after, and gated (2026-09-02, `code/1136_control_byte_gate.py`)
- Open after the FULLDATA-THREE-GAPS pass (1159 / 1160 / 1161), 2026-09-02

### `lobbying` — Lobbying

`27,825` rows × `62` columns · 21.2 MB · shelf `standard` · sold through Cedar Press — *measured (delivered)*

**What one row is.** one row per LDA filing attributed to a Native entity

**Join provenance.** Flagship table `native_entity_lobbying_disclosures.csv`, measured at 27,825 rows. *(builder's record for the rest of this paragraph.)*

_No supporting table met the one-to-one test; the substantive columns are the flagship's own._

Counted, **not** joined. These are one-to-many on the shared key; joining them would multiply the flagship's rows and inflate every money total, so each contributes a count column instead:

- `admin_appeal_parties(1:many on cedar_uid -> n_admin_appeal_parties)`
- `admin_appeal_positions(1:many on cedar_uid -> n_admin_appeal_positions)`
- `advocacy_passthrough(1:many on cedar_uid -> n_advocacy_passthrough)`
- `earmarks(1:many on cedar_uid -> n_earmarks)`
- `ferc_docket_filings(1:many on cedar_uid -> n_ferc_docket_filings)`
- `ferc_docket_parties(1:many on cedar_uid -> n_ferc_docket_parties)`
- `ferc_ex_parte_communications(1:many on cedar_uid -> n_ferc_ex_parte_communications)`
- `ferc_ex_parte_parties(1:many on cedar_uid -> n_ferc_ex_parte_parties)`
- `fr_ex_parte_parties(1:many on cedar_uid -> n_fr_ex_parte_parties)`
- `fr_ex_parte_party_entity_links(1:many on cedar_uid -> n_fr_ex_parte_party_entity_links)`
- `hearing_appearances(1:many on cedar_uid -> n_hearing_appearances)`
- `lobbying_issue_families_filing(1:many on cedar_uid -> n_lobbying_issue_families_filing)`
- `lobbying_registrant_client_relationships(1:many on cedar_uid -> n_lobbying_registrant_client_relationships)`
- `lobbying_registrant_native_ownership_evidence(1:many on cedar_uid -> n_lobbying_registrant_native_ownership_evidence)`
- `nonprofit_schedule_c_lobbying(1:many on cedar_uid -> n_nonprofit_schedule_c_lobbying)`
- `nrc_meeting_participants(1:many on cedar_uid -> n_nrc_meeting_participants)`
- `oira_meeting_participants(1:many on cedar_uid -> n_oira_meeting_participants)`
- `oira_meetings(1:many on cedar_uid -> n_oira_meetings)`
- `tribe_year_lobbying_panel(1:many on cedar_uid -> n_tribe_year_lobbying_panel)`

Measured in the delivered header: 0 column(s) carry a join prefix, from 0 source table(s); 19 count column(s).

**What was withheld, and why.**

- Measured: the flagship holds 27,825 rows and 27,825 were delivered — **0 row(s) not delivered**.
- Builder's per-reason breakdown: none — no row was withheld.

**What was masked.** A MASK keeps the row — a real public record — and withholds the Cedar attribution on it.

- Measured (delivered), one row one disposition, from `cedar_publication.adjudication()`: `PUBLISH` = 26,262; `FLAG` = 1,563
- Builder's record of masks that actually cleared a cell: 0 row(s).

**Known defects.**

- retired NEID identifiers still ship as VALUES in `attribution_withdrawn_entity_id` — 471 row(s), 471 identifier(s) (e.g. `TRBF-SROSAR-00`). The 2026-09-03 retirement dropped the NEID columns by NAME; a name gate cannot see the same identifier under another column name
- retired NEID identifiers still ship as VALUES in `entity_id` — 26,513 row(s), 26,513 identifier(s) (e.g. `TRBF-FALLON-00`). The 2026-09-03 retirement dropped the NEID columns by NAME; a name gate cannot see the same identifier under another column name
- 11 column(s) are under 10% populated — real, but do not build a headline on them: `affiliated_organizations`, `attribution_withdrawn`, `attribution_withdrawn_date`, `attribution_withdrawn_entity_id`, `attribution_withdrawn_reason`, `expenses_usd`, `filing_url_original`, `org_type_barred`, `org_type_reason`, `superseded_by_filing_uuid` …

Headings in `docs/KNOWN_ISSUES.md` that MENTION `lobbying` — a mention, found by substring, not a finding about this dataset:

- A2 · S3 · Three collections were documented as planning a script "not in the repository" — all three scripts exist
- B5 · S3 · `516_release_manifest.py` loses a script's directory, which is the whole of debt D7
- C4 · S2 · Nine grain rulings only a human can make
- D2 · S2 · `docs/WHAT_IS_MISSING.md` carries two figures that do not reproduce
- Corroboration: what the family count exposed (workstream CORROBORATION, 2026-09-02)
- The retroactive defect-class sweep, 2026-09-02 — 898 instances of 12 classes

### `nagpra` — NAGPRA

`6,792` rows × `76` columns · 11.8 MB · shelf `standard` · sold through Cedar Press — *measured (delivered)*

**What one row is.** one row per NAGPRA notice, keyed on the Federal Register document number - docs/NAGPRA_BUILD_LOG.md. A correction notice is its own row (is_correction=1) and does not supersede the row it amends. The `*_entity_ids` columns are PIPE-DELIMITED LISTS, not join keys: join to entities through nagpra_noti

**Join provenance.** Flagship table `nagpra_notices.csv`, measured at 6,792 rows. *(builder's record for the rest of this paragraph.)*

Folded in one-to-one, cardinality re-measured on the rows actually loaded rather than trusted from the contracts file:

- `fr_nagpra_title_index(document_number)`

Counted, **not** joined. These are one-to-many on the shared key; joining them would multiply the flagship's rows and inflate every money total, so each contributes a count column instead:

- `nagpra_notice_entity_bridge(1:many on document_number -> n_nagpra_notice_entity_bridge)`
- `nagpra_notice_institutions(1:many on document_number -> n_nagpra_notice_institutions)`

Measured in the delivered header: 5 column(s) carry a join prefix, from 1 source table(s) — `fr_nagpra_title_index`; 20 count column(s).

**What was withheld, and why.**

- Measured: the flagship holds 6,792 rows and 6,792 were delivered — **0 row(s) not delivered**.
- Builder's per-reason breakdown: none — no row was withheld.

**What was masked.** A MASK keeps the row — a real public record — and withholds the Cedar attribution on it.

- Measured (delivered), one row one disposition, from `cedar_publication.adjudication()`: `PUBLISH` = 6,792
- Builder's record of masks that actually cleared a cell: 0 row(s).

**Known defects.**

- retired NEID identifiers still ship as VALUES in `aboriginal_land_entity_ids` — 595 row(s), 3,897 identifier(s) (e.g. `TRBF-PNBSCT-00`). The 2026-09-03 retirement dropped the NEID columns by NAME; a name gate cannot see the same identifier under another column name
- retired NEID identifiers still ship as VALUES in `affiliated_entity_ids` — 5,022 row(s), 18,972 identifier(s) (e.g. `TRBF-CHYNRV-00`). The 2026-09-03 retirement dropped the NEID columns by NAME; a name gate cannot see the same identifier under another column name
- retired NEID identifiers still ship as VALUES in `consulted_entity_ids` — 2,698 row(s), 17,104 identifier(s) (e.g. `NHO-FFCHWN-00`). The 2026-09-03 retirement dropped the NEID columns by NAME; a name gate cannot see the same identifier under another column name
- retired NEID identifiers still ship as VALUES in `disposition_priority_entity_ids` — 445 row(s), 2,517 identifier(s) (e.g. `TRBS-MSSISQ-00`). The 2026-09-03 retirement dropped the NEID columns by NAME; a name gate cannot see the same identifier under another column name
- retired NEID identifiers still ship as VALUES in `letter_of_support_entity_ids` — 4 row(s), 8 identifier(s) (e.g. `TRBF-ALCOUS-00`). The 2026-09-03 retirement dropped the NEID columns by NAME; a name gate cannot see the same identifier under another column name
- retired NEID identifiers still ship as VALUES in `repatriation_recipient_entity_ids` — 1,625 row(s), 4,754 identifier(s) (e.g. `TRBF-ZUNINM-00`). The 2026-09-03 retirement dropped the NEID columns by NAME; a name gate cannot see the same identifier under another column name
- **no Cedar identity column at all** — this dataset carries no `cedar_uid` under any spelling, so after the NEID retirement its only entity key is a retired identifier
- 1 column(s) are blank on every delivered row and are kept deliberately: `fetched_date` — dropping blank columns would make the schema depend on which rows shipped
- 9 column(s) are under 10% populated — real, but do not build a headline on them: `aboriginal_land_entity_ids`, `cultural_items_total_stated`, `disposition_priority_entity_ids`, `institution_split_basis`, `institution_split_flag`, `letter_of_support_entity_ids`, `n_objects_of_cultural_patrimony_stated`, `n_sacred_objects_stated`, `n_unassociated_funerary_objects_stated`

Headings in `docs/KNOWN_ISSUES.md` that MENTION `nagpra` — a mention, found by substring, not a finding about this dataset:

- A11 · S3 · `START_HERE.md` said READY 0 / 13
- A17 · S1 · A validated grain proof can silently expire, and four have
- C8 · S2 · Three tables cannot ship until a publication decision is made
- ~~OPEN~~ **RESOLVED 2026-09-02** — the collapsed-escape defect is not confined to `846`. SEVEN more live scripts carry it, and one of them is the iden
- RESOLVED — all 41 collapsed escapes repaired, every one measured before and after, and gated (2026-09-02, `code/1136_control_byte_gate.py`)
- PLACE IDS (ADR-030, `code/1129_place_ids.py`) — 2026-09-02

### `native-owned-businesses` — Native-Owned Businesses

`3,725` rows × `70` columns · 5.8 MB · shelf `pro` · sold through Cedar Press — *measured (delivered)*

**What one row is.** one row per (certifying authority's directory, entry in it). NOT one row per FIRM: a firm certified by two nations is two rows, and that is the point - each row is one AUTHORITY'S assertion about that firm, and the two assertions are not the same claim. NOT one row per certification either: the Pyra

**Join provenance.** Flagship table `native_owned_businesses.csv`, measured at 4,273 rows. *(builder's record for the rest of this paragraph.)*

_No supporting table met the one-to-one test; the substantive columns are the flagship's own._

Measured in the delivered header: 0 column(s) carry a join prefix, from 0 source table(s); 1 count column(s).

**What was withheld, and why.**

- Measured: the flagship holds 4,273 rows and 3,725 were delivered — **548 row(s) not delivered**.
- Builder's per-reason breakdown: `publishable=548`

**What was masked.** A MASK keeps the row — a real public record — and withholds the Cedar attribution on it.

- Measured (delivered), one row one disposition, from `cedar_publication.adjudication()`: `PUBLISH` = 3,725
- Builder's record of masks that actually cleared a cell: 0 row(s).

**Known defects.**

- retired NEID identifiers still ship as VALUES in `business_entity_id` — 5 row(s), 5 identifier(s) (e.g. `CEDAR-ENT-000092`). The 2026-09-03 retirement dropped the NEID columns by NAME; a name gate cannot see the same identifier under another column name
- retired NEID identifiers still ship as VALUES in `certifying_authority_entity_id` — 3,576 row(s), 3,576 identifier(s) (e.g. `TRBF-TULALP-00`). The 2026-09-03 retirement dropped the NEID columns by NAME; a name gate cannot see the same identifier under another column name
- **no Cedar identity column at all** — this dataset carries no `cedar_uid` under any spelling, so after the NEID retirement its only entity key is a retired identifier
- 3 column(s) are blank on every delivered row and are kept deliberately: `publish_hold`, `person_name_check_1100`, `publish_hold_basis` — dropping blank columns would make the schema depend on which rows shipped
- 17 column(s) are under 10% populated — real, but do not build a headline on them: `business_entity_class`, `business_entity_id`, `business_entity_name`, `business_license_number`, `certification_number`, `certification_start`, `federal_cage_candidate`, `federal_cage_linked`, `federal_contract_number`, `federal_link_corroboration` …

### `natural-resources` — Natural Resource Revenues

`11,305` rows × `52` columns · 24.4 MB · shelf `pro` · sold through Cedar Press — *measured (delivered)*

**What one row is.** one row per resource revenue event as recorded by its source system

**Join provenance.** Flagship table `resource_revenue.csv`, measured at 11,305 rows. *(builder's record for the rest of this paragraph.)*

_No supporting table met the one-to-one test; the substantive columns are the flagship's own._

Counted, **not** joined. These are one-to-many on the shared key; joining them would multiply the flagship's rows and inflate every money total, so each contributes a count column instead:

- `anc_ceiling_roster(1:many on cedar_uid -> n_anc_ceiling_roster)`
- `ancsa_filings_index(1:many on cedar_uid -> n_ancsa_filings_index)`
- `nd_severance_allocation(1:many on cedar_uid -> n_nd_severance_allocation)`
- `resource_assets(1:many on cedar_uid -> n_resource_assets)`
- `resource_parties(1:many on cedar_uid -> n_resource_parties)`
- `tribal_tax_bases(1:many on cedar_uid -> n_tribal_tax_bases)`

Measured in the delivered header: 0 column(s) carry a join prefix, from 0 source table(s); 6 count column(s).

**What was withheld, and why.**

- Measured: the flagship holds 11,305 rows and 11,305 were delivered — **0 row(s) not delivered**.
- Builder's per-reason breakdown: none — no row was withheld.

**What was masked.** A MASK keeps the row — a real public record — and withholds the Cedar attribution on it.

- Measured (delivered), one row one disposition, from `cedar_publication.adjudication()`: `PUBLISH` = 11,305
- Builder's record of masks that actually cleared a cell: 0 row(s).

**Known defects.**

- retired NEID identifiers still ship as VALUES in `beneficiary_entity_id` — 586 row(s), 586 identifier(s) (e.g. `TRBF-CROWMT-00`). The 2026-09-03 retirement dropped the NEID columns by NAME; a name gate cannot see the same identifier under another column name
- retired NEID identifiers still ship as VALUES in `payer_entity_id` — 67 row(s), 67 identifier(s) (e.g. `ANRC-ALEUTC-00`). The 2026-09-03 retirement dropped the NEID columns by NAME; a name gate cannot see the same identifier under another column name
- retired NEID identifiers still ship as VALUES in `recipient_entity_id` — 705 row(s), 705 identifier(s) (e.g. `ANRC-AHTNAI-00`). The 2026-09-03 retirement dropped the NEID columns by NAME; a name gate cannot see the same identifier under another column name
- 3 column(s) are blank on every delivered row and are kept deliberately: `operator_entity_id`, `operator_entity_name`, `related_asset_ids` — dropping blank columns would make the schema depend on which rows shipped
- 8 column(s) are under 10% populated — real, but do not build a headline on them: `allocation_formula_effective_end`, `allocation_formula_effective_start`, `beneficiary_entity_id`, `beneficiary_entity_name`, `cedar_uid`, `cedar_uid_basis`, `payment_date`, `recipient_entity_id`

Headings in `docs/KNOWN_ISSUES.md` that MENTION `natural-resources` — a mention, found by substring, not a finding about this dataset:

- A2 · S3 · Three collections were documented as planning a script "not in the repository" — all three scripts exist
- C4 · S2 · Nine grain rulings only a human can make

### `nest` — NEST: Native Enterprise Structures and Ties

`5,820` rows × `88` columns · 9.6 MB · shelf `pro` · sold through Cedar Press — *measured (delivered)*

**What one row is.** one row per ENTERPRISE that a Native entity owns or has published a tie to - a sub-hub of its owner, never a spine entity in its own right (docs/IDENTIFIER_STANDARD.md §2). Identity is the Cedar-minted `enterprise_id`; the owner is `owner_hub_cedar_uid`, which is always a spine entity. NOT one row p

**Join provenance.** Flagship table `nest_enterprises.csv`, measured at 5,820 rows. *(builder's record for the rest of this paragraph.)*

Folded in one-to-one, cardinality re-measured on the rows actually loaded rather than trusted from the contracts file:

- `nest_entity_dual_role(cedar_uid)`

Counted, **not** joined. These are one-to-many on the shared key; joining them would multiply the flagship's rows and inflate every money total, so each contributes a count column instead:

- `nest_enterprise_relations(1:many on cedar_uid -> n_nest_enterprise_relations)`

Measured in the delivered header: 20 column(s) carry a join prefix, from 1 source table(s) — `nest_entity_dual_role`; 4 count column(s).

**What was withheld, and why.**

- Measured: the flagship holds 5,820 rows and 5,820 were delivered — **0 row(s) not delivered**.
- Builder's per-reason breakdown: none — no row was withheld.

**What was masked.** A MASK keeps the row — a real public record — and withholds the Cedar attribution on it.

- Measured (delivered), one row one disposition, from `cedar_publication.adjudication()`: `PUBLISH` = 5,820
- Builder's record of masks that actually cleared a cell: 0 row(s).

**Known defects.**

- retired NEID identifiers still ship as VALUES in `fpds_parent_resolves_to` — 361 row(s), 361 identifier(s) (e.g. `AKNF-ALGACQ-00-CALSTA-ASVCPR`). The 2026-09-03 retirement dropped the NEID columns by NAME; a name gate cannot see the same identifier under another column name
- retired NEID identifiers still ship as VALUES in `nest_entity_dual_role__handle` — 2,319 row(s), 2,319 identifier(s) (e.g. `AKNF-AGDAGX-00-ALEUTC-PRBLFA`). The 2026-09-03 retirement dropped the NEID columns by NAME; a name gate cannot see the same identifier under another column name
- retired NEID identifiers still ship as VALUES in `owner_hub_handle` — 5,820 row(s), 5,820 identifier(s) (e.g. `AKNF-AFGNAK-00-KONIAG`). The 2026-09-03 retirement dropped the NEID columns by NAME; a name gate cannot see the same identifier under another column name
- 12 column(s) are under 10% populated — real, but do not build a headline on them: `constellation_edge_id`, `constellation_note`, `duplicate_name_variant_basis`, `duplicate_name_variant_group`, `enterprise_existing_cedar_uid`, `fpds_parent_resolves_to`, `hub_resolution_note`, `name_variants_observed`, `ownership_percent_stated`, `parent_enterprise_id` …

Headings in `docs/KNOWN_ISSUES.md` that MENTION `nest` — a mention, found by substring, not a finding about this dataset:

- A1 · S3 · `502_archive_candidates.py` was proposing a LIVE crawler for archival
- Corroboration: what the family count exposed (workstream CORROBORATION, 2026-09-02)
- Lesson 3 — "COLUMN SHIFT" WAS THE WRONG DIAGNOSIS, AND THE RIGHT ONE IS WORSE
- What stands, and what was deliberately not done
- L2 · S2 · The McGrath hub's whole distinctive name is one common surname
- QA-STATUS-VOCAB · S1 · OPEN · `RULED_ATTRIBUTED` can mean "a quarantined resolver guessed", and that naming cost an escalation

### `nonprofits` — Native Nonprofits

`12,689` rows × `73` columns · 14.1 MB · shelf `pro` · sold through Cedar Press — *measured (delivered)*

**What one row is.** one row per EIN considered for the Native nonprofit universe, ruled in or out

**Join provenance.** Flagship table `np_orgs.csv`, measured at 12,764 rows. *(builder's record for the rest of this paragraph.)*

_No supporting table met the one-to-one test; the substantive columns are the flagship's own._

Counted, **not** joined. These are one-to-many on the shared key; joining them would multiply the flagship's rows and inflate every money total, so each contributes a count column instead:

- `fac_native_nontribal_sefa_programs(1:many on entity_id -> n_fac_native_nontribal_sefa_programs)`
- `fac_native_nontribal_single_audits(1:many on entity_id -> n_fac_native_nontribal_single_audits)`
- `fac_tribal_single_audits(1:many on cedar_uid -> n_fac_tribal_single_audits)`
- `grantmaker_funding_flows(1:many on cedar_uid -> n_grantmaker_funding_flows)`
- `np_ein_entity_hub(1:many on cedar_uid -> n_np_ein_entity_hub)`
- `np_schedule_i_grants(1:many on cedar_uid -> n_np_schedule_i_grants)`

Measured in the delivered header: 0 column(s) carry a join prefix, from 0 source table(s); 7 count column(s).

**What was withheld, and why.**

- Measured: the flagship holds 12,764 rows and 12,689 were delivered — **75 row(s) not delivered**.
- Builder's per-reason breakdown: `disposition=CONFLICT_EXCLUDED_AND_RULED_NATIVE=2; disposition=NATIVE_PROPOSED_AWAITING_OWNER_RULING=73`

**What was masked.** A MASK keeps the row — a real public record — and withholds the Cedar attribution on it.

- Measured (delivered), one row one disposition, from `cedar_publication.adjudication()`: `FLAG` = 11,328; `MASK` = 827; `PUBLISH` = 534
- Builder's record of masks that actually cleared a cell: 827 row(s) — `key_review_disposition=HELD_STATE_DISAGREES=458; key_review_disposition=REDIRECT_PROPOSED=12; key_review_disposition=REFUSED_GENERIC_TOKEN_ONLY=61; key_review_disposition=REFUSED_PLACE_NAME_IS_THE_ADDRESS=296`

**Known defects.**

- retired NEID identifiers still ship as VALUES in `cedar_spine_entity_id` — 591 row(s), 591 identifier(s) (e.g. `ANRC-AHTNAI-00`). The 2026-09-03 retirement dropped the NEID columns by NAME; a name gate cannot see the same identifier under another column name
- retired NEID identifiers still ship as VALUES in `entity_id` — 84 row(s), 84 identifier(s) (e.g. `AKNF-YKTTLN-00-SEALSK-TLNGHD`). The 2026-09-03 retirement dropped the NEID columns by NAME; a name gate cannot see the same identifier under another column name
- retired NEID identifiers still ship as VALUES in `key_redirect_proposed_entity_id` — 12 row(s), 12 identifier(s) (e.g. `CDFI-YRKLLN-00`). The 2026-09-03 retirement dropped the NEID columns by NAME; a name gate cannot see the same identifier under another column name
- 15 column(s) are under 10% populated — real, but do not build a headline on them: `cedar_link_key`, `cedar_spine_canonical_name`, `cedar_spine_entity_id`, `cedar_uid`, `entity_id`, `key_redirect_proposed_entity_id`, `key_redirect_proposed_name`, `keyed_name_match_residue`, `placename_refusal_basis`, `placename_refusal_date` …

Headings in `docs/KNOWN_ISSUES.md` that MENTION `nonprofits` — a mention, found by substring, not a finding about this dataset:

- M5 · NOT A DEFECT, BUT DO NOT COUNT IT AS LINKAGE
- NP-3 - The linkage ratchet cannot see a withdrawn claim - OPEN, integrator's call
- NP-6 - A NAME-LEVEL ETHNONYM VETO WAS BUILT, MEASURED AND REJECTED - do not rebuild it
- Open after the FULLDATA-THREE-GAPS pass (1159 / 1160 / 1161), 2026-09-02

### `subcontracting` — Federal Subcontracting

`70,597` rows × `86` columns · 91.4 MB · shelf `pro` · sold through Cedar Press — *measured (delivered)*

**What one row is.** one row per SUBAWARD FILING AS INGESTED FROM ONE SOURCE - not one row per subaward. FFATA/FSRS requires the PRIME to re-file an open subaward monthly, and every filing is a real reporting event, so one $57,500 subaward can be 93 rows spanning 2022-08 to 2025-01. Cedar RETAINS all of them and flags t

**Join provenance.** Flagship table `subawards.csv`, measured at 89,809 rows. *(builder's record for the rest of this paragraph.)*

Folded in one-to-one, cardinality re-measured on the rows actually loaded rather than trusted from the contracts file:

- `subaward_entity_rollup(cedar_uid)`

Measured in the delivered header: 8 column(s) carry a join prefix, from 1 source table(s) — `subaward_entity_rollup`; 0 count column(s).

**What was withheld, and why.**

- Measured: the flagship holds 89,809 rows and 70,597 were delivered — **19,212 row(s) not delivered**.
- Builder's per-reason breakdown: `duplicate_status=exact_repeat_within_source=18366; duplicate_status=superseded_by_primary_source=846`

**What was masked.** A MASK keeps the row — a real public record — and withholds the Cedar attribution on it.

- Measured (delivered), one row one disposition, from `cedar_publication.adjudication()`: `PUBLISH` = 70,597
- Builder's record of masks that actually cleared a cell: 0 row(s).

**Known defects.**

- 1 column(s) are blank on every delivered row and are kept deliberately: `pre_2000_flag` — dropping blank columns would make the schema depend on which rows shipped
- 9 column(s) are under 10% populated — real, but do not build a headline on them: `action_date_precedes_ffata_flag`, `prime_cage`, `prime_parent_cage`, `prime_set_aside`, `psc`, `psc_title`, `sub_cage`, `sub_parent_cage`, `subaward_exceeds_prime_flag`

Headings in `docs/KNOWN_ISSUES.md` that MENTION `subcontracting` — a mention, found by substring, not a finding about this dataset:

- C2 · S1 · `subawards.csv` — 10,770 duplicate rows, same shape suspected, unproven
- M2 · OPEN · "86.9%" ships in 26 customer files and is two vintages stale
- M3 · CORRECTED · `subcontracting` is 97.27% linked, not 44.8%

## Gates, run for this report

| gate | result |
|---|---|
| `846` `(no args)` | **pass** — 31/32 pass   1 fail   0 of them CRITICAL (identity layer) |
| `1137` `verify` | **pass** — 1137 verify   ok   0 problem(s); 13 datasets |
| `1151` `verify` | **pass** — 1151 verify   ok   0 problem(s); 12 storefront datasets |
| `1152` `verify` | **FAIL rc=1** — 1152 verify   FAIL   2 problem(s) |
| `845` `verify` | **pass** — 845 verify   ok   3 unsafe writer(s), 0 new since baseline |
| `1165` `selftest` | **pass** — 1165 selftest   ok   0 detector(s) did not fire as named |

`1137 verify` is the freshness gate: a delivered file older than any table it was built from is STALE and it exits 1 naming the file that moved. `1165 selftest` is the proof that the publication audit's detectors fire — a green audit whose detectors have never been made to go red is not evidence of anything.

## The outside QA review, reconciled

`review/QA_RECONCILIATION_2026-09-02.csv` holds 173 logged findings, each checked against the live tables rather than judged by reading.

| verdict | findings |
|---|---:|
| CONFIRMED_BY_100ROW | 108 |
| STILL_REQUIRES_FULL_DATA_CHECK | 25 |
| OBSOLETE_OLD_SAMPLE_DESIGN | 24 |
| LIKELY_FIXED_IN_NEW_EXPORT | 12 |
| NEEDS_HUMAN | 4 |

## What is NOT fixed, and what was NOT measured

Stated because a reviewer's first move is to look for what the report avoided.

- **The delivered files are wide.** 45–312 columns. Every column is kept deliberately — dropping the blank ones would make the schema depend on which rows shipped — but a reviewer who called the export cluttered will still find it cluttered.
- **`gaming` is the thirteenth dataset** and ships through Cedar Grove, not the Cedar Press storefront. It is built and gated with the twelve and it has no preview file.
- **Nothing here measures whether a VALUE is correct.** This report measures shape, provenance and the publication policy. Whether a contract is attributed to the right nation is the adjudication layer's question and is not answered by any figure above.
- **A green gate is not a proof of coverage.** `1165` reports zero violations of the rules it implements; rules nobody has written are not tested by it. The rule of three applies — zero observed violations licenses a floor, never a claim of correctness.

*Built set: 13 datasets across shelves `standard`, `pro`, `grove`; storefront: 12 across `standard`, `pro`. Rebuild the deliverables with `py -3 code/1137_customer_dataset_combine.py build`; regenerate this report with `py -3 code/1162_twelve_dataset_report.py build`.*
