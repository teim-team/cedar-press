# Fact-check and research-readiness pass, 2026-10-02

Branch `codex/cedar-convergence-consumer-20260926` (PR 132), starting head `7c56a56`.
Measurements were taken on 2026-10-02 with
`python3 server/tests/test_public_preview_audit.py --report` (added in this pass; read-only, and
its invariants run as tests under `make test-python`) and the one-off checks named in each section. This
document is a record of what was measured, what was changed and what remains open.
It does not state that any collection is fully fact-checked: the served files are
ten-row previews, and the full spreadsheets (1,778,800 permitted observations) are
not in this repository.

## 1. Scope and grain

Reviewed: the 14 served public previews `public/data/cedar/samples/<id>/spreadsheet__10.csv`
(140 rows in all), `data/spine/*.csv` (5 files), `data/cedar/collections.manifest.json`,
`data/cedar/collection_descriptors.json`, `data/cedar/releases.json`,
`data/cedar/verified-preview-releases.json`, the generated guides `docs/guides/*.md`,
the SEO surface (`index.html` head and JSON-LD, `public/sitemap.xml`, `scripts/seo-head.mjs`,
`src/features/grove/useDocumentTitle.js`), `README.md` and `docs/REVIEW_STATUS.md`.
Excluded: the full producer spreadsheets (not in Git), `server/tests/fixtures/legacy-preview/`
(private regression fixtures), `data/cedar/samples/*__sample.csv` (2026-09-02 historical
extracts, now bannered as superseded) and `dist/`.

Grain and key per collection, as the manifest and the served header declare them. Every
served row carries `record_type`, `record_key` (the source primary key as JSON) and
`record_grain`; `record_key` was distinct and non-blank on every row of every preview.

| Collection | Rows in release | Preview rows x cols | Record types in release | Record-level key |
| --- | ---: | --- | --- | --- |
| contractors | 841,002 | 10 x 52 | prime_contracts | `transaction_id` |
| deals | 978 | 10 x 36 | records | `deal_id` |
| federal-register | 21,258 | 10 x 61 | consultation_participants 11,402; federal_actions 9,856 | `consultation_record_key` or `fr_document_number` by record type |
| foundation-corporate-giving | 193 | 10 x 66 | policy_eligible_disclosures; reviewed_disclosures | `disclosure_id` |
| funding | 640,942 | 10 x 42 | federal_funding_transactions | `transaction_id` |
| legislation | 3,064 | 10 x 33 | records | `bill_id` |
| lobbying | 27,825 | 10 x 41 | records | `activity_id` |
| nagpra | 6,792 | 10 x 55 | records | `document_number` |
| natural-resources | 11,120 | 10 x 41 | records | `resource_revenue_event_id` |
| need | 43 | 10 x 23 | reviewed_public_base | `enterprise_id` |
| nonprofits | 89 | 10 x 27 | records | `ein` |
| owned | 3,725 | 10 x 35 | records | `business_source_id` (a listing, not a business) |
| plot | 151,715 | 10 x 106 | six source record types | `plot_record_id` or the source record id per type |
| subcontracting | 70,054 | 10 x 57 | records | `subaward_record_id` |

Every served preview's SHA-256 equals the producer's pinned `sample_sha256` in
`data/cedar/verified-preview-releases.json` (14 of 14), every preview's row and column
count equals the manifest's `sample.rows` and `sample.columns` (14 of 14), no row is ragged,
and `data/cedar/releases.json` agrees with the manifest (`node scripts/record-release.mjs --check`).
Because the previews are byte-exact producer artifacts, no served CSV was edited in this pass;
data defects found in them are queued for the producer in section 5.

## 2. Identity rules

- `cedar_uid` (format `CE-XXXXX-XX`) is the registered Native entity: who. 1,916 register rows,
  all well-formed, 1,913 `active` and 3 `active_unverified`. Dataset keys (`deal_id`,
  `transaction_id`, `document_number`, `enterprise_id`, `business_source_id` and so on)
  identify the record: what. Role columns (`cedar_entity_role`, `native_party_role`,
  `participant_role`, `native_direction`) are the how.
- The register used is `data/spine/cedar_identity_register.csv` with
  `data/spine/cedar_entity_names.csv`. The samples' `canonical_name` follows the published
  name in `cedar_entity_names.csv` (`name`), not the short handle in the register's
  `canonical_name` column: 88 of 88 uid/name pairs across the 14 previews match the
  published name exactly, 0 match the handle, and 0 uids are absent from the register.
  The two files differ on 585 of 1,916 entities by design (`name_differs_from_prior = 1`,
  for example `Navajo` versus `Navajo Nation, Arizona, New Mexico, & Utah`). Entity class
  agrees between the two files on all 1,916 rows and with every preview pair.
- `cedar_retired_neid_crosswalk.csv`: 1,555 retired handles, every one resolving to a
  register uid, all `unique`. `cedar_nonprofit_ein_links.csv`: 380 links, all EINs nine
  digits, no duplicate EIN, every uid in the register, all tier `A`.
- EIN, UEI, CAGE and FIPS are evidence attributes, not identities. Formats measured on the
  previews: every `cedar_uid` well-formed; every nonprofit `ein` nine digits with leading
  zeros kept (`043049162`); every `*_uei` 12 alphanumeric; every `*_fips` five digits with
  leading zeros kept (`06073`, `01089`); the one hyphenated EIN (`13-1684331`, Ford Foundation)
  is the giving collection's raw source formatting, which the review status says is preserved
  on purpose. No stable ID was created, changed or removed in this pass.

## 3. Changes made

None of the changes touches a served CSV, a stable ID or a count in the manifest.

1. **`data/cedar/collection_descriptors.json` reconciled to the manifest.** The file was a
   2026-09-02 (`v0`) copy: lobbying still named `Tribal Advocacy and Lobbying` (renamed
   2026-09-18 to `Native Federal Advocacy and Engagement`), row labels such as
   `3,345,971 rows` for contractors against the release's 841,002, no entries for
   Foundation & Corporate Giving or PLOT, and entries for the excluded gaming, newsletters
   and `_entity_layer`. It now holds the manifest's 14 descriptor blocks in manifest order.
   Visible effect: `docs/guides/README.md` names every guide by its current collection
   name (it had printed the old lobbying name and bare ids for giving and PLOT).
2. **Deals `method` prose corrected** in `data/cedar/collections.manifest.json`,
   `data/cedar/collection_descriptors.json` and `docs/datasets/_descriptors.json`. It said
   the public preview "contains ten selected events checked against primary sources on
   October 1, 2026". The served preview is the producer's pinned sample (deal ids
   `ACQ2020-015` to `ACQ2020-023` and `ANCSA-2012-001` to `ANCSA-2015-001`, all
   `deal_type = Acquisition`); the ten events checked on October 1 (`CEV-2025-*`,
   `CEV-2021-*`) live in `server/tests/fixtures/legacy-preview/samples/deals/deals_classified__10.csv`
   and in `docs/DEALS_PUBLIC_PREVIEW_REVIEW_2026-10-01.md`. The prose now describes both and
   says the reviewed events reach the served preview only through a producer release.
3. **Generated guides** (`scripts/docs-markdown.mjs`, regenerated into `docs/guides/*.md`):
   the field dictionary's "Blank means" column is now the rule for the column's type
   (money: never zero; dates: no date stated; precision columns; entity-link columns;
   `n_*` counts; the opening block never blank) instead of one sentence for every column;
   a new "Units and formats" block states nominal US dollars, the `_real2025` columns,
   the `currency` column where one exists, ISO 8601 dates with month precision where a
   precision column says so, and leading zeros; a new "Observed in the preview" block is
   measured from the served rows (record types, columns blank on every row, literal tokens
   present); the header carries the Updated date; the citation is the exact sentence the
   downloads carry (collection name and Updated date, no version label); and a
   precision-aware date type was added to `data/cedar/guides.json`. Covered by four new
   tests in `src/features/grove/releaseDocs.test.js`.
4. **Public SEO text.** The `description`, `og:description` and `twitter:description` in
   `index.html` and the fallback in `useDocumentTitle.js` said every record was "resolved to
   the Native entities behind it"; the previews show 6 of 14 collections with every
   `cedar_uid` blank in the sample, and the JSON-LD already said "separately documented
   Native entity associations". The meta text now matches the JSON-LD. The document title
   separator changed from an em dash to a colon under the house copy rule. The JSON-LD
   `Dataset` entries gain `dateModified` (the manifest's Updated date) and, where the
   storefront name differs from the collection name on the downloads, that name as an
   `alternateName` (for example `Native Federal Contractors` beside `Federal Prime
   Contracting`), so a reader holding a file can find the dataset it came from; the
   `DataCatalog` gains `dateModified`. Regenerated with `node scripts/seo-head.mjs`.
5. **`README.md`**: a collections table with the manifest's names, shelves and observation
   counts measured on 2026-10-02, a source summary per collection, the citation sentence,
   a "What is not claimed" list and the check results of this pass.
6. **`docs/REVIEW_STATUS.md`**: two local Windows paths (`D:/cedar-convergence-20260926/...`)
   replaced by a reference to the private review packet; a dated subsection recording this
   pass. `data/cedar/samples/README.md` gained a banner marking its 2026-09-02 extracts and
   counts as superseded by the served previews (nothing reads that directory at build or
   run time, measured with `grep`).
7. **`server/tests/test_public_preview_audit.py`** added: nine tests that keep the measured
   invariants firing (pinned bytes, manifest shape, record keys, identifier formats, no
   private paths, entity links resolving with the published name and class, spine
   consistency, descriptors mirroring the manifest, the Deals method describing the served
   rows), plus a `--report` mode that prints the measurements; registered in
   `docs/PRESENTATION_DATA_FLOW.md`. It lives under `server/tests/` because the maintained
   `scripts/` inventory is held below twenty entries by a test.

Row counts in, row counts out: unchanged everywhere (no CSV edited).

## 4. Evidence and decisions

- Served preview versus producer receipt: `sha256sum public/data/cedar/samples/*/spreadsheet__10.csv`
  against `verified-preview-releases.json`; 14 of 14 equal. Decision: a served CSV is a
  producer artifact and is corrected upstream, never here (AGENTS.md invariant "fix the
  generating pipeline, never the output CSV").
- Deals preview: PR 149's own description and the review memo name the `CEV-*` events;
  `git show` of the fixture and the served file show different ids and schemas (40 legacy
  columns versus the 36-column producer header). Decision: keep the served wiring (it is
  the pinned, verified producer sample), correct the prose, and record the producer-side
  change needed if the reviewed events are to be served.
- Entity names: the 88 preview pairs match `cedar_entity_names.csv` exactly, so the guides'
  definition ("as Cedar's register spells it") is accurate when the register is read as the
  names layer. One name variant was found between the two spine files themselves:
  `CE-0009Z-7Q` is `Ukpeaġvik Iñupiat Corporation` in the register and `Ukpeagvik Iñupiat
  Corporation` (no dotted g) in the published names, source `ancsa_lbb`. The corporation's
  own site could not be fetched from this environment (egress blocked), so it is queued.
- Web verification: every primary source tried was blocked by the network egress proxy
  (tulaliptero.com, projects.propublica.org, uicalaska.com, api.usaspending.gov,
  federalregister.gov, congress.gov, govinfo.gov). No value was changed on the strength of a
  source that could not be read; each is queued with the exact URL to check.
- Tokens that look like placeholders: `null` in `federal-register.collective_scopes` (5 rows)
  is the producer's declared JSON null for consultation-participant rows (dictionary
  definition); `unknown` in giving `financial_status` (2) and `version_kind` (5) and in PLOT
  `estate_type` (2) and `trust_status` (3) are declared controlled values; `Undisclosed` in
  deals `value_basis` (4) is a declared value. None was recoded. Their presence is now
  reported in each guide's "Observed in the preview".
- Provenance leakage: no local path, personal email or key in `public/`, `src/` runtime
  code, `server/cedar_press/` or `data/cedar/`; the only `D:/` paths in a maintained document
  were the two in `docs/REVIEW_STATUS.md`, now removed. Dated logs
  (`docs/RELEASE_REPLAY_LOG.md`, `docs/COSPONSOR_HARVEST_LOG_2026-09-02.md`) still carry
  such paths and were left as history. `elijah.moreno@lumecon.ai` appears once in
  `src/pages/grove/PressChrome.jsx` as a deliberate contact address.
- Stable IDs: none changed.

## 5. Unresolved review queue

Producer (Lumecon-data), Havala Hanson coordinating; data methods to Francesca Agnes.

| Collection, row | Finding | Evidence | Next source to check | Status |
| --- | --- | --- | --- | --- |
| owned, `business_source_id` for `Cashwork Atm` (certification `1482`, Marysville WA) | `ownership_percent = 0.0` on a NAOB-registry listing; the dictionary says blank means no percentage supplied, so a zero on a Native-owned registry row reads as a false zero | preview row 7; 3 other rows carry `100.0`, 5 are blank | https://www.tulaliptero.com/TEROReports/NAOBRegistryAllAll (blocked here) | RESOLVED AT SOURCE 2026-10-02 (definition): the value is genuine; the column is the certifying tribe's stated share, and `code/330`, the override and the guide now say so (section 8) |
| subcontracting, `subaward_record_id 000375DB-0EC4-4293-B372-61CB6E8F9B8D` | `prime_award_amount_usd = 0.00` beneath a `3,299,182.00` subaward; `subaward_to_prime_ratio` blank; `subaward_exceeds_prime_flag` blank on all 10 rows although the dictionary defines it as yes or no and this row exceeds its prime | preview row 7; `prime_award_unique_key CONT_AWD_W81K0025FA146_9700_W81K0024D0002_9700` | https://www.usaspending.gov/award/CONT_AWD_W81K0025FA146_9700_W81K0024D0002_9700/ (blocked here) | FIXED AT SOURCE 2026-10-02 in `code/41`, `45`, `94` (yes/no, ratio, reason; section 8); the served preview changes when a release built on the corrected staging is pinned |
| deals, `ANCSA-2014-001` | `research_note` still says "A mid-month placeholder day (15) is used per ledger convention" while the shipped `event_date` is `2014-05` with precision `month`; the note is stale against the row | preview row 9 | ASRC 2016 annual report (cited in the note) only for the date; the fix is editorial in the producer | UNRESOLVED (low) |
| federal-register, consultation_participants rows | `collective_scopes` is the literal `null` on participant rows and blank on federal_actions rows: two conventions for "not evaluated" in one column | preview rows 1, 3, 5, 7, 9 | producer field contract | FIXED 2026-10-02: producer writes blank (v2/v3, `d780401`); definitions regenerated here (section 8); the served preview still shows the token until re-pinned |
| foundation-corporate-giving, `FG-*` rows | `currency` blank on all 5 `reviewed_disclosures` rows that carry `amount_exact_usd`; `publication_status` blank on the same rows while `FF-*` rows read `observed` | preview rows 2, 4, 6, 8, 10 | producer contract for the reviewed_disclosures component | UNRESOLVED |
| subcontracting, `CE-0009Z-7Q` | published name `Ukpeagvik Iñupiat Corporation` differs from the register canonical `Ukpeaġvik Iñupiat Corporation` by the dotted g | `data/spine/cedar_entity_names.csv` row 320 versus `cedar_identity_register.csv` row 320 | https://www.uicalaska.com/ (blocked here) | FIXED AT SOURCE 2026-10-02: names row 320 publishes the register spelling; the source rendering is an alias (section 8) |
| spine | `National Center for American Indian Enterprise Development` is the canonical name of two uids: `CE-000RA-MT` (Intertribal Organization, handle `I-004`) and `CE-001R2-8V` (Native nonprofit, AZ) | `cedar_identity_register.csv` | IRS BMF entry for NCAIED's EIN and the Intertribal Organization source; an owner identity adjudication, never a merge by name | CONTESTED candidate, recorded 2026-10-02 in `data/spine/cedar_duplicate_name_review.json` (pending owner adjudication) |
| spine | `cedar_entity_types.csv` states 359 `Native nonprofit` rows; the register holds 361 | both spine files | regenerate the types file from the register | FIXED AT SOURCE 2026-10-02: 361 (section 8) |
| deals, served preview | the ten events reviewed on 2026-10-01 (PR 149) are a regression fixture, not the served rows | section 4 | a producer release that selects them as the sample, if that is wanted | OWNER DECISION (Havala) |
| funding, Siletz repair | recorded in `docs/REVIEW_STATUS.md`: two transactions (`ASST_NON_1896753-42-22_417`, UEI `GJV4PJ8M5PC7`) project to the tribal government instead of the separate nonprofit | review status | apply in Lumecon-data, re-pin | HOLD 2026-10-02: the wrongly bound uid is not recorded, the only denial vocabulary (`not_native`) misstates a Native nonprofit, and the policy inputs are not in Git; what is missing is listed in `docs/REVIEW_STATUS.md`, "Source-side fixes, 2026-10-02" |
| all | the 1,778,800 full-spreadsheet rows were not re-measured here; only the 140 preview rows and the manifest were | section 1 | re-run this audit's checks over the full spreadsheets in the producer | NOT MEASURED |

Not defects, recorded so they are not re-investigated: negative `obligations_usd` are
de-obligations kept as recorded (dictionary); the `$0.00` funding transaction
(`...12X1105_10.664_0003`) is a zero-dollar modification; `fiscal_year 2026` on a
2025-12-24 subaward is the federal fiscal year; `registrant_id 400635921` is a post-2017
LDA registrant id; `reporting_year 1999` filed 2000-02-14 is a year-end report; the
contractor `award_id` duplicates are several transactions of one award (the key is
`transaction_id`); `owned.cedar_uid` equals the certifying tribe by definition
(`cedar_entity_role = certifying_authority`).

## 6. Reproduction

Inputs: `public/data/cedar/samples/*/spreadsheet__10.csv`, `data/cedar/collections.manifest.json`,
`data/cedar/verified-preview-releases.json`, `data/spine/*.csv`, `data/cedar/codebook.json`,
`data/cedar/guides.json`, `data/cedar/collection_descriptors.json`.
Outputs: `docs/guides/*.md`, `index.html` (JSON-LD block), `public/sitemap.xml`,
`docs/DATASET_CODEBOOK.md` (unchanged by this pass), this document.

```sh
npm ci                                            # Node 22
python3 server/tests/test_public_preview_audit.py --report          # the measurements in sections 1, 2, 4 and 5
python3 server/tests/test_public_preview_audit.py --report --json   # the same, machine-readable
python3 -W error -m unittest discover -s server/tests -t server -p "test_public_preview_audit.py"
node scripts/docs-markdown.mjs --kind all         # regenerate the guides, codebook and field-map docs
node scripts/seo-head.mjs                         # regenerate index.html's JSON-LD and public/sitemap.xml
make check-generated                              # every generated file current
```

Environment assumptions: no network is needed for any step above. Python 3.12 is the CI
version; under 3.11 five `server/tests` modules fail to import because `code/` scripts use
3.12 f-string syntax (see section 7). Safe refresh: a new producer release is staged with
`scripts/stage_verified_previews.py`, which rewrites the manifest and samples together;
rerun the three generators after it, never edit a sample by hand.

## 7. Validation

Run on 2026-10-02, Linux, Node 22.22.0, Python 3.11.15 (CI uses 3.12).

- `npm run lint`: clean. `ruff check server`: clean.
- `make check-generated`: all six generators current after regeneration.
- `node --test src/features/grove/releaseDocs.test.js`: 10 pass (6 existing, 4 new).
- `npm run test`: 635 tests, 634 pass, 0 fail, 1 skipped; coverage 88.64% lines, 85.00% branches,
  90.80% functions against floors 83 / 82 / 89.
- `make test-python`: `Ran 664 tests`, 33 skipped, coverage 85% against the 77 floor (`python3 -m
  coverage report`). Five import errors and one failure, identical to the baseline run before any
  change: `tests.test_candidate_review`, three `test_field_map` cases and one
  `test_pipeline_registration` case fail to import `code/1137_customer_dataset_combine.py`
  (3.12 f-string syntax, `SyntaxError` under 3.11), and
  `test_current_tree_has_no_new_unregistered_writer_edges` parses `code/` with `ast` and so sees
  a different census under 3.11. The hosted run on Python 3.12 is the record for this suite; the
  new module `test_public_preview_audit.py` passes its 9 tests here.
- `npm run build`: completes; the chunk-size warning is pre-existing.
- `make audit-node`: 0 vulnerabilities. `make audit-python`: no known vulnerabilities.
- Browser smoke suite (`npm run test:smoke`): not run here; the hosted Checks run on the
  pushed head is the record for it.

Release status: engineering and evidence review in progress; this pass changes
documentation, generated text and public metadata only. No production data publication,
deployment or merge is asserted.

## 8. Source-side fixes applied after this pass (2026-10-02)

Applied on this branch after the measurements above, each as its own commit with a test
that fails before and passes after; no served CSV, uid or dataset value changed.

| Finding (section 5) | Fix at source | Test |
| --- | --- | --- |
| `CE-0009Z-7Q` published name; `cedar_entity_types.csv` 359 vs 361 | `data/spine/cedar_entity_names.csv` rows 320 and 382 publish the register spelling (`Ukpeaġvik Iñupiat Corporation`; `Shee Atika, Incorporated`), the two `ancsa_lbb` renderings are kept in the new `cedar_entity_name_aliases.csv`, the types file says 361; applied from Lumecon-data's `lumecon-data spine regenerate` proposal (`d780401`) after diffing it against the live files; `identity_changes = 0`; `public/data/cedar/register.json` regenerated | `test_spine_files_are_internally_consistent` (types count equals the register per class; no rendering variants; aliases resolve); served cells that are a recorded alias pass through `name_is_recorded_alias` |
| NCAIED on two uids | `data/spine/cedar_duplicate_name_review.json`: "pending owner adjudication, 2026-10-02", evidence chain, next sources; not merged, not renamed | duplicate canonical names fail unless recorded there with a reason; a wrong pair or a blank reason is refused |
| subcontracting flag blank; 0.00 prime | `code/41_match_subawards_to_ledger.py` `subaward_money_fence` (one rule, used by 45 and 94): yes/no, ratio to four decimals, blank ratio with the reason under a non-positive prime, blank only when an amount is unreported; matches Lumecon-data `press_candidates._subaward_money_fence` | `code/41_match_subawards_to_ledger_test.py` (7 tests on the producer's fixture amounts) |
| `collective_scopes` null vs blank | definitions re-pinned to producer `d780401` (blank) and regenerated through `scripts/preview_definitions.py`; guides and codebook regenerated | `test_preview_definitions_state_the_blank_convention_for_unevaluated_scope` |
| owned `ownership_percent = 0.0` | the value is the source's; `code/330` dictionary, the override and the guide define the column as the certifying tribe's stated share, not Native ownership overall | `test_owned_ownership_percent_definition_states_whose_share_it_is` |
| Siletz repair | held; what is missing is written in `docs/REVIEW_STATUS.md` ("Source-side fixes, 2026-10-02") | none (nothing was changed) |

The served previews are unchanged by these fixes (they are producer-pinned bytes); they
pick up the corrected spine, flag and definitions when the producer builds and pins
releases against this source.
