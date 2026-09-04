# Workstream GRAIN-WS4 — grain refusals, funding money paths, legislation row conservation

*Generated 2026-09-01 by `code/730_ws4_grain_money_conservation.py`. Every number is re-measured from the live files on every run; `verify` exits 1 when one of them stops being true.*

## A. Why `512.GRAIN_WS4` is empty

A file containing a LITERAL duplicate row — a whole row repeating byte for byte — has no unique key at any arity, because the widest candidate available is the whole row and it already collides. `512.validate_grain` turns a declaration with no usable key into a release-blocking violation. Seven of the eight tables this workstream was handed are in that state; the eighth holds zero rows. **No de-duplication was performed and no row was deleted.**

| table | collection | rows | literal dup rows | groups | key possible today |
|---|---|---:|---:|---:|---|
| `faads_transactions.csv` | funding | 60,661 | 1,001 | 946 | **NO** |
| `faads_transactions_all_agencies.csv` | funding | 2,769,748 | 179,259 | 63,578 | **NO** |
| `native_passthrough.csv` | funding | 1,522 | 116 | 20 | **NO** |
| `ferc_docket_filings.csv` | lobbying | 102,615 | 822 | 602 | **NO** |
| `hearing_bill_links.csv` | lobbying | 465 | 1 | 1 | **NO** |
| `lobbying_registrant_native_ownership_evidence.csv` | lobbying | 27 | 4 | 4 | **NO** |
| `congressional_correspondence_log.csv` | legislation | 0 | 0 | 0 | yes |
| `native_bills_subject_sweep.csv` | legislation | 2,414 | 5 | 5 | **NO** |

### Candidate keys tested on the FULL file

| table | candidate | duplicate rows |
|---|---|---:|
| `faads_transactions.csv` | `award_id_fain` | 18,942 |
| `faads_transactions.csv` | `award_id_fain+action_date+obligated_usd` | 1,199 |
| `faads_transactions_all_agencies.csv` | `award_id_fain` | 1,058,171 |
| `faads_transactions_all_agencies.csv` | `award_id_fain+action_date+obligated_usd` | 252,612 |
| `native_passthrough.csv` | `subaward_number` | 570 |
| `native_passthrough.csv` | `subaward_number+prime_award_id+from_tribe_id+to_tribe_id` | 510 |
| `native_passthrough.csv` | `subaward_number+prime_award_id+from_tribe_id+to_tribe_id+subaward_date+amount_usd` | 273 |
| `ferc_docket_filings.csv` | `ferc_filing_id` | 989 |
| `ferc_docket_filings.csv` | `docket_number+subdocket+accession_number+filer_organization_as_recorded` | 822 |
| `hearing_bill_links.csv` | `event_id+bill_id` | 1 |
| `hearing_bill_links.csv` | `event_id+bill_id+link_basis+relationship` | 1 |
| `lobbying_registrant_native_ownership_evidence.csv` | `registrant_id+evidence_route` | 7 |
| `lobbying_registrant_native_ownership_evidence.csv` | `registrant_id+evidence_route+native_entity_id+evidence_tier` | 4 |
| `congressional_correspondence_log.csv` | `record_id` | 0 |
| `congressional_correspondence_log.csv` | `record_id+control_number` | 0 |
| `native_bills_subject_sweep.csv` | `bill_id` | 5 |
| `native_bills_subject_sweep.csv` | `bill_id+subject_family+matched_phrase` | 5 |

### The eighth table: `congressional_correspondence_log.csv`

Zero rows, so every key is vacuously unique and the file cannot testify about itself. The question is therefore about the GENERATOR, and the generator is measurable. `136.build_correspondence_layer` mints `record_id = "FOIAREQ-{agency_code}-{foia_request_id}"` for every `foia_request_index.csv` row whose requester is a congressional office.

- `foia_request_index.csv` holds **20,102** rows and **4** of them name a congressional office as requester. ~~9,481 rows and 0 congressional requesters~~ — **SUPERSEDED, re-measured 2026-09-02 by `code/1156_doc_claim_gate.py`.** The conclusion below has FLIPPED and that is the point of re-measuring: the table is no longer empty of congressional requesters, so "nothing qualified" is no longer true. Four rows now carry `requester_is_congressional_office = Y` against 20,098 `N`. Anything built on the old zero must be rechecked.
- `(agency_code, foia_request_id)` — the exact pair the id is built from — **collides in 368 groups over 19,716 distinct values, 386 surplus rows** (~~381 collisions over 9,100 distinct values~~ — re-measured 2026-09-02 with the row count above).
- The colliding rows say why themselves, in `parse_quality_reason`: `control_number_appears_more_than_once` ×744; `no_date_recovered_from_this_layout` ×223; `description_begins_mid_sentence` ×222.

So `record_id` is **not unique on the population it is drawn from**. Declaring it as a primary key would validate today against zero rows and break the first time the table fills. It stays in `GRAIN_OPEN`. **The fix is upstream of this table:** the PDF layout solver in `136` recovers one control number for two different requests — different requester, different description, different official — and stamps both. Owner: whoever holds `136`.

### What each refusal needs, and who owns it

| table | the one change that lifts it | owner |
|---|---|---|
| `faads_transactions.csv`, `faads_transactions_all_agencies.csv` | the queued re-extract in `review/OWNER_DECISION_QUEUE.md`. `30_funding_pre2008.to_out_row` now carries `assistance_transaction_unique_key`; when it runs, both tables become declarable in one line. **It re-orders a 2.77M-row file and `faads_entity_attribution.csv` keys 29,594 attributions to ROW POSITION** — they must move in the same pass, and `faads_attribution_key` (`code/710`) is the content key that lets them. | owner decision queue |
| `native_passthrough.csv` | `81` carries `subawards.duplicate_status` through instead of collapsing it into `amount_countable`. The de-dupe key becomes statable; the duplicates stay. | `81_build_passthrough_dataset.py` |
| `ferc_docket_filings.csv` | 822 byte-identical repeats of one (document, filer). A further 167 digest collisions differ only in filer-name CASE and are NOT duplicates. `133` needs a per-occurrence ordinal or an upstream fetch fix. | `133_build_ferc_advocacy.py` |
| `hearing_bill_links.csv` | source-side: Congress.gov event 338549 lists 27 of its 64 `relatedItems.bills` twice, verbatim. `98` should de-duplicate the API payload per event before emitting — that is not a Cedar fact being deleted, it is an API repetition not being ingested twice. | `98_build_oira_and_hearings.py` |
| `lobbying_registrant_native_ownership_evidence.csv` | **ONE COLUMN.** The 4 duplicates are four INDEPENDENT source assertions of one UEI, rendered identical because `182` does not carry `asserted_by_source` onto the output row. The sibling table `lobbying_registrant_identifiers.csv` already keys on `identifier + asserted_by_source`. Carrying that column makes this table declarable and PRESERVES the corroboration a de-dupe would delete. | `182` |
| `native_bills_subject_sweep.csv` | the corpus: `data/raw/external/votingpatterns/all_bill_intros.csv` repeats 595 `bill_id`s byte-identically over 183,233 rows. A bill is introduced once. De-dupe key `bill_id`, applied to the CORPUS, not to the sweep. | the votingpatterns corpus |
| `congressional_correspondence_log.csv` | see above — the control number the id is built from is recovered twice from one PDF layout. | `136` |

## B. C7 — the funding money paths

Written to `docs/MONEY_TOTALLING_RULES.md` between the `GRAIN-WS4` markers. The headline: `faads_transactions_all_agencies.csv` and `federal_funding_transactions.csv` **both hold FY2007**, and 98.9% of the modern table's FY2007 dollars sit on FAINs the archive table also carries.

## C. C5 — row conservation

11 existing (source_table, disposition) rows updated in place, 0 added, 154 rows in the ledger. **Merge-only**: no row is ever removed and no key is ever rewritten from scratch — a wholesale rewrite of this ledger destroyed 2,146,673 accounted rows on 2026-09-01.

## D. The `62` gate reading at the end of this workstream — nothing red is WS4's

`py -3 code/62_no_regression_check.py` was run after every write below. **Standing rule 15 says a fail is stop-work and must not be recorded as 'pre-existing, not mine' and stepped around, so each red line was attributed by re-measuring it, not by assuming.**

| red line | verdict | owner |
|---|---|---|
| `lint_class1` 0 → 3, `lint_class2c` 60 → 61, `lint_new_defect_instances` | re-ran `293_lint_bug_classes.py` and read the named findings: every new instance is in `731_ws5_grain_contractors_nonprofits_deals.py`. **Zero findings name `730`.** | GRAIN-WS5 |
| `contract_violations = 7` | `entity_aliases.csv` `alias_id` not unique (1 blank-keyed row) + 6 orphan shippable tables. `512` reports **no violation for any table WS4 touched**, and `native_passthrough_pairs.csv` still validates its declared `from_tribe_id + to_tribe_id` key after the rebuild. | `entity_aliases` owner; codebook registrants |
| `contract_orphan_shippable = 6` | `native_owned_businesses.csv`, `nonprofit_schedule_c_coverage.csv`, `nonprofit_schedule_c_lobbying.csv`, `regulations_gov_comments.csv`, `regulations_gov_entity_coverage.csv`, `sam_native_class_distributions.csv` — registered in the codebook, claimed by no collection. WS4 registered nothing. | the workstreams that registered them |
| `rulings_unapplied` 1,215 → 2,894 | measured ONLY from `cedar_ruling_ledger_consolidated.csv` (43,321 rows), which WS4 never opened. | the ruling-mining workstream |
| `files_with_columns_lost_vs_backup` | re-ran the check's own logic: the only loss is `entity_evidence_profile.csv` against a `bak_2026-08-28_pre505` backup. WS4's three backups (`native_passthrough.csv`, `native_passthrough_pairs.csv`, `cedar_harvest_conservation.csv`, all `.bak_2026-09-01_pre_ws4*`) lose no column and the live file is newer than each. | `505` / entity-evidence owner |
| `SHIPPING LOST: advocacy_passthrough_2026-08-07.csv` | the coordinator's deliberate de-registration of a dated snapshot that was shipping the same $193,592,975 twice. The file is on disk. | the integrator |
| `tables_missing_from_25_TABLES` 179 → 187 | new tables registered by sibling workstreams; WS4 created no table. | siblings |

**WS4 moved three metrics the right way:** `harvest_source_rows_read` (the legislation conservation rows below), and `native_passthrough.csv` off the `ship_tables_at_zero`/unshipped-260 line by closing the stale disposition. It moved none the wrong way.
