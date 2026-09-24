# Gaming Intelligence audit and Claude handoff — 2026-09-24

**Scope and verdict.** Gaming is a **Cedar Grove** collection, outside the twelve Cedar Press storefront collections. No Gaming release is ready today. This is a read-only audit of the live ignored data in Desktop/Cedar Press, tracked origin/main code at 6d445f4, the fetched origin/codex/legislation-release-consumer release proof, Desktop/4wheeler, Desktop/votingpatterns, Desktop/cedar-press-repo, and Desktop/Lumecon-data. The audit branch is codex/gaming-intelligence-audit. Existing launch worktrees, canonical CSVs, and the twelve-collection review queue were not changed. The only new code is the read-only inventory command [audit_gaming_inventory.py](../../scripts/audit_gaming_inventory.py).

**Measurement contract.** Appendix A records exact current row counts, full SHA-256 hashes, column counts, and selected observed year ranges for 74 gaming-related clean CSVs. Run `py -3 scripts/audit_gaming_inventory.py 'C:\Users\esm247\Desktop\Cedar Press\data\clean'` for every header, identifier fill/distinct count, 2025–2026 count, and ISO retrieval-date range. The script emits JSON lines to stdout and writes nothing. Its year scan is lexical; a year in a quote, URL, or scheduled future obligation is not a coverage claim. CSV headers and per-table contracts at docs/schema/tables are the schemas; contracts need checking against live bytes. The local clean tree is ignored by Git and may change independently of this branch. All counts below are observations of that tree on 2026-09-24, not a frozen canonical release.

## Readiness by component

| Component | Verdict | Measured basis and limit |
|---|---|---|
| NIGC regional GGR and bands | **READY WITH GAPS** | 198 region-years FY2001–2025 and 20 band rows FY2022–2025; official source, unique version/region/year key. Region vintages, rounding, FY2025 inflation basis and release integration remain. |
| Tribe or facility revenue | **NOT READY** | 494 mixed state observations, 68,211 metrics, 13,803 bounds, 10,766 digital rows, and SEC disclosures have incompatible definitions, derived/modelled/vendor measures. No defensible national tribe-year panel exists. |
| Facility directory and amenities | **SOURCE-LIMITED** | 787 source rows and 717 nonblank distinct place IDs; 16 negative placeholders. 595 rows carry Casino City IDs and inherited capacity is licensed. Public-source replacement and identity rulings remain. |
| Compacts, terms, payments | **READY WITH GAPS** | 707 compacts, 1,158 versions, 2,887 structured terms; CA 41,758 and FL 9,756 payment rows. Instrument, version, clause, payment direction, recipient and base differ. |
| Regulatory/environmental events | **READY WITH GAPS** | 327 declination letters, 265 decision events, 138 land decisions, 362 enforcement actions, 1,155 ordinances, two-project NEPA pilot. Status reversal and event identity must survive. |
| Employment and labor | **NOT READY** | 3,421 clean observations combine OSHA, Form 5500, block jobs, projections and other measures. OLMS and NLRB candidates remain outside clean Gaming. |
| Sports betting, licensing, permits, crosswalks | **NOT READY** | 154 digital relationships, 740 vendor-license candidates, state records, 2,438 NIGC assignments and 2,124 wider administrative assignments. No complete current status census verified. |
| Governed Cedar Grove delivery | **NOT READY** | Two-collection release proof exists on a separate branch; no Gaming Grove catalog pin, entitlement test, audit rehearsal or rollback proof. |

## Inventory, provenance, and reported counts

The live source tree has local snapshots, not just scripts. Under data/raw/external: gaming 29 files, compacts 2,434 (including 1,119 PDFs and 1,119 text extracts), nigc 81, nigc_declinations 490, nigc_ordinances 1,417, gaming_nepa 25, gaming_official 1,047, gaming_property_sites 1,985, state_gaming 281, ca_gaming 195, fl_gaming 112, wa_gaming 46, digital_gaming 80, and osha_ita 12. These are file counts, not deduplicated documents or rows. Source manifests retain URL, path, fetched date, size and source hash, with differing algorithms. The following SHA-256 hashes are **of the manifest files**, not their referenced source bytes:

| Manifest under data/raw/external | Records | Manifest SHA-256 |
|---|---:|---|
| gaming/_SOURCE_MANIFEST.csv | 22 | 352f19cb44f75a1665cb54fa8dc17a720a80c2ceaf0bd8a78f073db5e9895fc3 |
| nigc/_SOURCE_MANIFEST.csv | 26 | 1c12ec5605c464213263f9bfe57dbaba58f0ce11dd7220e52086fb005ce8fc49 |
| nigc_declinations/_SOURCE_MANIFEST.csv | 328 | c3ed62ac1d847ec4a61f29b7f4d33d983e68d25f620147090bbca77013c3f28d |
| nigc_ordinances/_SOURCE_MANIFEST.csv | 1,151 | 80240d7ea1d2fa7512c29e69f2679c70296e2081c84d4b85917c1920ce839cc2 |
| ca_gaming/_SOURCE_MANIFEST.csv | 181 | efc7562157c9349360f0a02994f2960aebe1839caa6571d167d8ca834fe522b9 |
| fl_gaming/_SOURCE_MANIFEST.csv | 106 | b8219ae7baa5f974a7e96b51226561f7716fe985378d40892ac7f2d1b2b065e6 |
| state_gaming/_SOURCE_MANIFEST.csv | 280 | 20f06e787c6b7f5e209ebccbe8c6269fa785a26ed9211704f639db2152cab4f7 |
| osha_ita/_SOURCE_MANIFEST.csv | 10 | e3ea7cc37854b11c206274860271140b04bb7311ffbcaf83844955421bf5c0de |

Also inspect compacts/SOURCE_MANIFEST.md and the gaming_nepa, gaming_devices, digital_gaming, nigc_documents, wa_gaming, and gaming_official/NM manifests. Verify every referenced byte before building; a manifest row is not proof the source still matches. Appendix A pins clean outputs; no canonical release pins all raw inputs and decisions yet.

Desktop/votingpatterns/data/processed has published_tribal_gaming_revenue_v3_audited.csv **530** rows (1994–2026; SHA prefix 2bf3ee7055fe), per_tribe_gaming_revenue_reverse_engineered.csv **611** rows (1994–2026; d258535adb0f), per_property_gaming_revenue_FINAL_v3_audited.csv **512** rows (1994–2026; 54cc6b998e09), bia_compact_content_v2.csv **1,188**, compact_master_aiannh.csv **1,242**, and tribe_year_compact_panel.csv **9,505** (1990–2030, including future periods). These are candidate/research artifacts, not canonical Gaming outputs. Property estimates use compact rates and accommodation/arts GDP and cannot become reported GGR. The votingpatterns Python/R/Stata revenue, compact, casino-district and geocode scripts are predecessor research; copied files under data/raw/external/gaming/directory_core inherit that provenance, not independent corroboration.

The claimed **616 tribe-year observations / 46 tribes / 1992–2025 / 22 facility events** did **not** reproduce as one artifact in the scanned workspaces. Do not quote them as coverage. Closest measured quantities are 611 reverse-engineered tribe rows, 735 4wheeler employment-panel rows over 55 written tribe names (1992–2025), 10 gaming_property_universe_events roster-change rows, and 265 gaming_decision_events rows. None verifies 22 facility events. Require the claimant's file/hash, grain and inclusion query before using those numbers.

The fetched Cedar remote refs origin/claude/cedar-press-datasets-3n2wjf and origin/codex/early-access-takeover contribute no unmerged Gaming/NIGC/compact/release paths relative to origin/main; the separate legislation-release-consumer ref contributes the governed-release proof described below. This does not turn ignored local data into a remote artifact.

Desktop/4wheeler/casino_employment_validation/data contains a 7,396-row analysis file, 5,166-row Form 5500 panel, 10,733 resolved Form 5500 rows, 2,009 resolved OSHA rows, 34,794 NLRB election rows and 250 candidate tribal-casino election rows. Cedar staging holds 2,046 Form 5500 rows (2009–2025; SHA prefix fdfdbf4ed783), 502 OSHA tribe rows (2016–2025; 1a4a1798e920), 65 loyalty, 622 self-published assertions, 41 claims and 231 recovered claims. Staging rows are not extra clean observations. [Labor sources](../LABOR_SOURCES_FOR_GAMING_2026-08-26.md) records methods and known false positives; current clean employment count supersedes its older 769-row opening statement. No OLMS-derived clean Gaming table was located. The standalone Lumecon Data repo holds governed storage code and tests, not a Gaming source table. The older Desktop/cedar-press-repo has registry candidate copy, not current data authority.

## Table model and identifiers Claude should implement

| Table family | Row grain and primary key | Relationship and non-additivity rule |
|---|---|---|
| nigc_regional_ggr; nigc_revenue_bands | Published report observation by region-system version + region + FY; band by report/band/FY. Preserve report vintage, precision, operation count, nominal GGR, deflator and real-2025 field separately. | Regional totals belong to **regions**. nigc_region_assignments is geographic membership only. A facility link cannot convert a region total or its mean into a facility or tribe value. Never sum overlapping vintages or nominal with real dollars. |
| state_gaming_observations; digital_gaming_revenue; SEC/audit disclosures | One source observation with observation_id, revenue_id or disclosure_id, measure, period, coverage, reporting party and evidence class. | State, tribe, property, online licensee and enterprise scopes differ. Direct reported win, payment, compact inversion, model and bound require separate facts. A bound is never added to an observation. |
| gaming_facilities/gaming_properties; amenity/capacity/site/license observations | Stable **facility** record by facility_id; distinct place hub by cedar_place_id; each dated capacity/amenity assertion has its own observation ID, source, status and as-of date. | 787 rows are not 787 operating casinos. Multiple facility records may refer to a place; some assert no place; a hotel/golf course is not gaming capacity. Snapshots cannot be summed across years or merged with proposals. |
| compacts, compact_versions, compact_structured_terms, compact_events, compact_required_reports | Instrument compact_id; version version_id; clause term_id; event event_id; obligation report_id. | Preserve amendment order, effective interval, game class and scope. compact_terms is a derived view, not another agreement. A rate is not payment or revenue. |
| ca_gaming_payments; fl_gaming_payments | Source line payment_id, fund, direction, recipient, period and document. | Do not sum inflow with redistribution, forecast with paid, or overlapping cadences. Invert a rate only when compact base and payment match, and label the result derived scope-specific revenue. |
| Land, NIGC, ordinance, NEPA, financing and universe events | Source document/decision/filing ID plus event_id for each dated status transition; project IDs remain distinct from facility IDs. | Approved, rescinded, pending, proposed, built and observed operation differ. NEPA projection is an applicant scenario. Declination shows agency review, not approval. |
| OSHA, Form 5500, NLRB, OLMS, LODES/QCEW/QWI | Establishment-year, plan/sponsor-year, bargaining unit/election, labor filing, or geographic cell; each source gets its own filing/observation ID. | Plan participants, eligible voters, block jobs, suppressed cells and employees are distinct. Preserve source and measured concept. |
| Regional crosswalks | assignment_id or facility + region-system version + effective interval; many-to-many links carry method/confidence. | cedar_uid is authoritative for the **Native entity**. facility_id, cedar_place_id, compact_id, version_id, payment_id, filing IDs, event_id, observation_id, administrative_region_id and source IDs are distinct namespaces. Legacy tribe_id is only a checked alias; AIANNH/FIPS is geography, not identity. |

The live CSVs prove why these keys matter. gaming_facilities has 787 unique facility_id values, 16 blank place IDs, 717 distinct nonblank places, 284 distinct cedar_uid values and 2 blank entity links. nigc_regional_ggr has 198 unique (region_system_version, administrative_region_id, fiscal_year) combinations. gaming_revenue_bounds has 13,803 rows but 12,554 distinct (facility_id, fiscal_year) pairs, with up to 11 bounds per pair. gaming_employment_observations has 3,421 rows but 2,022 distinct (cedar_uid, year) pairs, with up to 17 measures per pair. These multiplicities are different measures, not rows to sum or deduplicate mechanically.

## Defects, coverage and rights

The property denominator has a documented history of 787, 780, 734, 727, 714 and 717 being quoted for different definitions. Use row and place keys; 717 is today's nonblank distinct place count, not proof of 717 operating NIGC facilities. [Gaming quality pass](../GAMING_THIRTEENTH_DATASET_2026-09-02.md) names Stables joint operation, 7 Clans First Council Ponca/Otoe-Missouria attribution, uncertain 7 Clans Ponca, and coordinate/address conflicts. Preserve competing evidence. NIGC's FY2025 announcement describes **545 establishments, 246 tribes and $46.2B**, an independently defined audited reporting universe; it does not validate Cedar's 787 rows as operations. [NIGC FY2025 announcement](https://www.nigc.gov/nigc-announces-46-2-billion-in-fy-2025-gross-gaming-revenues/).

[The NIGC region build log](../NIGC_REGION_BUILD_LOG.md) is the geographic authority for this build. Region systems changed in FY2003, FY2008 and FY2017; Montana moved, Region V split, Rapid City split, and Oklahoma/Nebraska need property-map evidence or explicit unassigned/conflict status. **Never spatially allocate NIGC regional GGR to a tribe or facility**, including by operation count, midpoint or average. Some older figures are rounded; ggr_usd_real2025 is a separate deflated view and FY2025 nominal/real coincide by definition. Pin the deflator series, base year and figure precision before trend comparisons. [NIGC report archive](https://www.nigc.gov/commission/reports-and-publications/gross-gaming-revenue-reports/), [NIGC location map](https://www.nigc.gov/map).

Missingness is source-specific. state_gaming_observations has 54 blank entity links, including state aggregates deliberately left unassigned. digital_gaming_revenue has 2,870 blank cedar_uid rows, largely commercial operators. ca_gaming_payments has 4,484 blanks; gaming_revenue_bounds has 359; nigc_declination_letters has 20. A name-only join must not fill them. QCEW and QWI suppress small/dominant cells; LODES injects noise; OSHA reporting varies by year; Form 5500 counts active **plan participants**, not employees. [Labor sources](../LABOR_SOURCES_FOR_GAMING_2026-08-26.md) explains why a suppressed zero is not measured zero. Revenue bounds repeat regional ceilings across facilities; their 13,803 rows cannot be summed. A compact payment derived from Class III electronic net win is not total casino revenue. Dates are equally qualified: YYYY-12-31 and YYYY-MM-15 may be source placeholders; open_date can be a property opening, rebuild, or nongaming amenity rather than gaming commencement.

[State frameworks](../STATE_GAMING_FRAMEWORKS.md) document different sports-betting and internet-gaming licensing regimes, including Michigan; the digital tables are period/operator observations, not a nationwide active-license or permit register. BIA gaming-land decisions and NEPA records identify federal actions and environmental-review documents, not a complete state/local permit history. NLRB election candidates in 4wheeler and possible OLMS filings require source-specific joins and cannot establish a casino-wide workforce or a labor agreement by name alone.

2025 coverage is real but uneven: eight FY2025 NIGC GGR rows; 566 FY2025 revenue-bound rows (mostly contextual ceilings); 949 CA payment lines ending in 2025; 312 FL lines; 145 employment observations marked 2025; 17 NIGC declinations and 13 decision events dated 2025. 2026 rows are mainly document/retrieval dates or partial periods: 1,057 CA payment lines ending 2026, 372 FL lines (some forecasts through 2031), 1,378 digital period-end rows, 3 NIGC declinations, 3 decision events, and 1 employment row marked 2026. No FY2026 NIGC GGR exists in the local table; on 2026-09-24 the official archive lists FY2025 as latest. The 2026 coverage is not a complete revenue year. NEPA project tables hold 19 facility assertions, 116 projections and 24 mitigation lines from two projects; their 2026 documents are not 2026 operating outcomes. [NIGC report archive](https://www.nigc.gov/commission/reports-and-publications/gross-gaming-revenue-reports/).

Independent FY2025 arithmetic on the live regional CSV yields exactly eight rows, $46,162,783,570 GGR and 545 operations, all under NIGC_R4_FY2017_present. This agrees with the printed national total in [the local NIGC build log](../NIGC_REGION_BUILD_LOG.md); it validates that year’s transcription, not the other years or any entity-level allocation. Only three state_gaming_observations rows have a period ending in 2025, so that table is especially thin as a current revenue source.

**Publication rights are a field-level gate.** gaming_facility_metrics (68,211 rows), gaming_property_capacity_history (64,181), and casino_city_id/inherited vendor fields are Casino City Press lineage and **internal QA only** under [spec reconciliation](../GAMING_SPEC_RECONCILIATION.md), [labor sources](../LABOR_SOURCES_FOR_GAMING_2026-08-26.md), code/87_build_dataset_notes.py and the dataset contract. Keeping CCP- as an internal stable key does not confer rights to republish vendor values. Every displayed name, address, amenity and capacity needs independent evidence or withholding. Votingpatterns modelled property revenue, IMPLAN estimates and trade-directory facts are research/QA, not reported GGR. Official NIGC/BIA/state/DOL/OSHA/SEC records are acquisition leads with source-specific attribution, refresh, suppression and retention checks; public availability alone does not certify a transformed table. DOL confirms public structured Form 5500 annual datasets and monthly updates for 2009 onward; local pull date matters. [DOL Form 5500 datasets](https://www.dol.gov/agencies/ebsa/about-ebsa/our-activities/public-disclosure/foia/form-5500-datasets).

## Script authority and deterministic rebuild

Running `py -3 code/build.py plan gaming --verbose` in the live checkout finds **65 clean collection tables, 16 full rebuilders, 28 in-place enrichers and 4 ambiguous mixed writers**: 102_build_coverage_profile, 103_build_california_gaming, 147_build_fac_single_audits and 15e_finalize_terms. It warns of enricher backups on 57 tables. The same command in the fresh audit worktree returns NO_TABLES/NO_STAGES because clean inputs are ignored; it fails closed. **No whole-Gaming deterministic rebuild has been proved.** A green plan in a populated checkout is dependency discovery, not row/hash replay. [cedar_pipeline.py](../../code/cedar_pipeline.py) puts 41_build_codebooks.py in NEVER_RUN; do not run it.

Authoritative **for scoped source extraction** are 84_build_nigc_regions.py, 91_build_nigc_declinations.py, 95_parse_compact_terms.py, 103_build_california_gaming.py, 105_build_florida_gaming.py, 92_build_gaming_capacity_official.py, 156_stage_form5500_gaming_employment.py, 157_reconcile_nigc_roster.py, 32b_build_gaming_nepa_pilot.py and their source manifests. 1141_gaming_quality_pass.py, 1095_gaming_bounds_summability_and_seal_typing.py, 960_promote_gaming_facility_class_and_revenue_reach.py, 1129_place_ids.py and 814_gaming_nr_grain_and_conservation.py are checks/enrichers, not new source acquisition. 586_promote_nigc_gaming.py and 587_gaming_facility_corrections.py are promotion/correction history requiring replay order. 23d_build_gaming_facilities.py must precede 960, and 82_build_gaming_property_dataset.py must precede 160_sync_published_gaming_view.py, or enriched columns can be lost. Votingpatterns v1/v2/v3 revenue and compact files are successive candidate versions, not additive. _1080_facility_aliases.py, .bak files and scripts outside the declared plan remain **unreferenced or historical until a caller and output contract are proved**; no deletion is authorized. A file named FINAL or a passing selftest is not current authority. Use [dependency_manifest.json](../schema/dependency_manifest.json) and [gaming_sources.md](../datasets/gaming_sources.md) to enumerate writers, but verify live call paths and exact inputs, writes, side effects and semantic diffs before a supported build route.

## Website promise and governed-release path

On origin/main, [pressCatalog.js](../../src/features/grove/pressCatalog.js) explicitly says the Gaming Intelligence Grove preview was withdrawn on 2026-09-04; the storefront has twelve, and Gaming is excluded pending readiness. [pressSources.js](../../src/features/grove/pressSources.js) also withholds NIGC from storefront source claims. The older dirty Desktop/cedar-press-repo checkout still has a Gaming catalog card and PressShelf invitation; it is **stale candidate copy**, not current release authority. The current site does not promise a Gaming download or cadence. Broader Cedar Grove language does not validate tribe-level gaming revenue.

The fetched Cedar origin/codex/legislation-release-consumer branch and Lumecon Data origin/codex/legislation-storage-safety branch provide the relevant **infrastructure proof**, summarized in docs/HAVALA_INFRASTRUCTURE_REVIEW.md on the Cedar branch: Legislation 3,069 bill IDs and Natural Resources 11,305 source-observation IDs pass pinned-source projection, Lumecon DatasetContract validation, immutable content-addressed snapshots, catalog manifest digest, exact JSONL download, session/current-tier entitlement, redacted audit and rollback to a prior verified catalog. That is a local review proof, not Gaming publication or production deployment. Gaming must reuse code/build.py release-pilot, cedar_pipeline.RELEASE_PILOTS, cedar_publication field map/hold, Lumecon contracts.py/pipeline.py/storage.py/catalog.py, the Cedar server repository adapter and subscriber authorization. Add one reviewed Grove catalog/entitlement declaration without moving Gaming into the twelve Press shelves. Bind source hashes/dates, rights decision, register/decision hash, grain/key, reference preservation, row count, schema and artifact hash. Test anonymous/wrong-tier/stale-account denial, exact bytes, redacted audit, immutable-replacement refusal and verified rollback. Do not create a second release runner, ID allocator, catalog definition or audit log.

## Human review queue and engineering queue

Only these require a policy or identity ruling, in priority order:

1. **Vendor-derived facility rights.** Decide the evidence threshold for independently verified names/addresses/capacity under stable internal CCP- keys; hold unresolved fields.
2. **Place/operator identity.** Resolve Stables joint operation, 7 Clans First Council Ponca/Otoe-Missouria attribution, 7 Clans Ponca and named address/coordinate conflicts. Preserve competing claims until ruled.
3. **Revenue scope policy.** Decide whether compact-inverted, payment-derived scoped values can enter later access, and their labels/aggregation rules. This never authorizes regional allocation.
4. **Grove scope and entitlement.** Approve regional-only early access and its customer caveats, tier and refresh promise after the pilot passes. Keep it outside Cedar Press.
5. **Ambiguous Native links.** Review only records with competing cedar_uid candidates after deterministic matching; blank state aggregates and commercial digital operators are not human identity tasks.

Engineering owns source acquisition/refresh, manifests and hash pinning, four mixed-writer plan defects, rights filters, crosswalk checks, OLMS/NLRB/permit ingestion, source-specific suppression, deterministic replay and release integration. Those are not owner policy questions.

## Bounded build plan for Claude

Each commit belongs on a **separate Gaming branch**, preserves canonical inputs until its producer/replay contract is approved, and stops on unexplained row/hash/identity loss. Keep the Cedar Press launch branches and twelve-collection review queue untouched.

1. **Inventory lock and receipts.** Inputs: Appendix A, raw manifests, 4wheeler/votingpatterns candidates, current register/rulings. Output: source inventory under the existing schema/inventory authority with SHA-256, fetched/published dates, rights class, grain and writer. Tests: every referenced byte/hash, missing-input refusal, duplicate path/ID detection, fresh-checkout read-only plan. Stop if source or rights record absent. No backup-as-current or unpinned scrape into canonical data.
2. **Grain/key/rights gates.** Inputs: contracts, register, source claims. Output: versioned Gaming contracts and field allowlist with separate ID namespaces and null/uncertain links. Inject duplicate primary key, regional-to-entity GGR, vendor-field leak and unsupported crosswalk promotion; each must fail by name. Stop if licensed field reaches projection. No 65-table flattening or name-string ID mint.
3. **Official regional candidate.** Inputs: pinned NIGC FY2001–2025 PDFs and manifest, regional/band tables. Outputs: two source-grain candidate tables, bibliography, precision/vintage/deflator metadata and Grove-only copy. Tests: FY2025 eight regions reconcile to printed national total; versioned region/year unique; no cedar_uid, facility_id or allocated GGR. Stop on missing report or unreconciled sum. No FY2000/FY2026 interpolation.
4. **Facility/regulatory separation.** Inputs: NIGC map/roster, BIA decisions/compacts, operator/state sources, rights rulings. Outputs: independently evidenced facility/place records and status-event histories. Tests: conserve/disposition all 787 old rows, 16 negative placeholders, multi-operator and merge groups; source-level uncertainty retained. Stop if vendor-only value publishes or decision date becomes opening date.
5. **Payments/terms and labor lanes.** Inputs: pinned state filings/compact PDFs, OSHA, Form 5500, acquired NLRB/OLMS. Outputs: separate payment, compact-version/term, employment/filer/event tables. Tests: direction/recipient, forecast exclusion, rate/base validity, duplicate plans, suppression and no cross-measure sums. Stop on unknown base, ambiguous sponsor or absent source. No participant-as-employee or payment-as-gross.
6. **Governed Grove pilot.** Inputs: approved small flagship(s) from commit 3, existing Cedar/Lumecon release contracts, Grove entitlement decision. Outputs: immutable candidate, verified catalog pin, exact JSONL, audit receipts and rollback rehearsal. Mirror Legislation/Natural Resources preservation/hash/denial/stale-account/immutable-replacement/rollback tests; run both repositories' CI. Stop on unapproved field/identity or failed denial. Do not promote/publish in this commit or add Gaming to Press.
7. **Expansion gates.** Add independently evidenced facility amenities, regulatory events, compact/payment and labor tables one lane at a time. Each needs manifest, dated coverage, rights decision, direct observation key, semantic diff and two-release replay. Stop on unexplained duplicates, suppression or source drift. Consider entity revenue only from **direct** tribe/property reporting with a documented non-overlap rule.

**Smallest defensible early access.** A Cedar Grove-only, clearly labelled **NIGC regional gaming revenue and revenue-band research release**: 198 historical regional observations and 20 band observations in separate tables, with source PDFs, fiscal-year/report-vintage precision and no entity-level revenue, facility-count claim or FY2026 estimate. This is a *candidate*, not yet published; governed release/entitlement/rollback proof and editorial approval remain. Expand through source-separated regulatory and compact lanes, then independently evidenced facilities/amenities, then scoped payments and labor. A nationwide tribe-year GGR panel is not a permitted shortcut.

## Appendix A — live clean-file inventory

SHA-256 hashes are of complete CSV bytes in C:/Users/esm247/Desktop/Cedar Press/data/clean on 2026-09-24. Date is the chosen observation/source column and min–max lexical year, not a claim of full coverage. “—” means no suitable dated field in this compact index. Run the inventory command above for all columns and dates. Being present does not mean shippable.

| Clean CSV | Rows | Columns | Date | SHA-256 |
|---|---:|---:|---|---|
| admin_region_assignments.csv | 2,124 | 22 | effective_start_year 2025–2025 | 3a40f26d78c0258caff14e1306183c43d2881e528c404258e1e2d2a111db70e2 |
| admin_region_overlap_derived.csv | 28 | 10 | — | a845661d1c7d7273c3d00282bd87e4e6d936673380d475aeb1781296cac68f46 |
| admin_region_systems.csv | 6 | 17 | effective_start_year 2026–2026 | dd121b57c9d2b93efacc096d840caecabebee13ab328d6ae3fd68e6cd9fa9139 |
| admin_regional_observations.csv | 27 | 16 | fetched_date 2026–2026 | e019ce59dec3c72f734c57f71b0209a795cc4d94fc8518bf54b3f9d9a8e71c90 |
| admin_regions.csv | 155 | 17 | — | 1b07e7709193fa21df629e76339e683d80c78e0d5722a259c9d4396b400cdc8c |
| ca_gaming_facilities_official.csv | 245 | 32 | as_of_date 2024–2025 | bcb185768f89ec72164d41eeb44c11a9dab7cd6de4c81c0e46e8e57084faf809 |
| ca_gaming_payments.csv | 41,758 | 46 | period_end 2001–2026 | 3d6a1433b4fcaad176353ca77cd09ccb73e22fbed5761ac311c1e692dc6ce415 |
| compact_events.csv | 31 | 20 | event_date 1992–2025 | 6b229914b36b15df181b57a428b595b45d44b203120bfaaa03fccf8dfe4da8f8 |
| compact_obligation_tribal_agency_bridge.csv | 927 | 20 | — | 037f66dbe7b7a36bd54c44ffb52e077df9f73fc3da3101800fe97b2e97ebe6be |
| compact_required_reports.csv | 4,121 | 34 | fetched_date 2026–2026 | 248578e0b6e82223a10b53a21153f32a9923a73585bd1c4ef91a656268e39bc7 |
| compact_structured_terms.csv | 2,887 | 40 | fetched_date 2026–2026 | 9aab0db29f25261afea7c9f674c81ff6275d307cfd7f275fc851670c32e0152d |
| compact_terms.csv | 1,311 | 22 | — | 5461d458acfc243ec37afd6015169fd4980e027c083dbb3330f4c45b7562dff8 |
| compact_versions.csv | 1,158 | 25 | approval_date 1990–2026 | ff8d0153daee7a76331c0190a52eebdd4ec505cf9ff3667241f4c09ff2c21e6d |
| compacts.csv | 707 | 34 | — | 8e9d5c82b42d7e4bdade0dcf6e3e23f2e798e6f2088776aeffc8a85c1a06aa01 |
| digital_gaming_relationships.csv | 154 | 42 | fetched_date 2026–2026 | fc5366737c76c162e7275ac9096aef63978e32c5e721ac9aa3c8d0cadde9d9b1 |
| digital_gaming_revenue.csv | 10,766 | 36 | period_end 2021–2026 | 2bb34c74e9c42f05d1ffed10c984bea218b0f408facafc11b2ea1a4fc3133876 |
| fac_audit_gaming_disclosures.csv | 1,521 | 25 | audit_year 2016–2026 | 96365ab1e6ba1b66282244f1e18c162c7019f69ce39eb17d254aee3e06d0dd71 |
| fac_audit_sefa_gaming_programs.csv | 1 | 26 | audit_year 2021–2021 | ecc8cf9c393dc84c395f6f7bae194ac84177c6f79f18d256473778d638695649 |
| fl_gaming_payments.csv | 9,756 | 58 | period_end 2008–2031 | ea97d17a4d6e510f9763727c9b8d270d26387164e96d1a1deb5c1dc71ebf4b14 |
| gaming_capacity_official.csv | 6,649 | 36 | period_end 1993–2050 | 60f1af73855c9d921ef899486ce531bfd90c4075e23897a84ee09aebf5aa013a |
| gaming_decision_compact_join.csv | 138 | 16 | decision_date 1990–2026 | 2ea63df338d3de33eeec80c43f0468108001929264ea10dae62206f02909bb7c |
| gaming_decision_events.csv | 265 | 13 | event_date 1990–2026 | 6da4e043114c6487ba3a54c27f803ac96567355768eb78a8ec42ea8b6fd9c17d |
| gaming_device_observations.csv | 1,326 | 28 | observation_date 1990–2026 | 10a71bc4ad908db24a19a118c90e34dd1b06a6d5dbc7225b05dccd01bf589ac2 |
| gaming_employment_observations.csv | 3,421 | 65 | year 2008–2026 | 355f6ae52aa76395044dc669cd69c49f2fbe6332122617cbd3239482b937d3ef |
| gaming_facilities.csv | 787 | 129 | open_date 1905–2025 | 12ec517ebbf306f0c14e70266758dd58432c715a4cbc125cadf776295c11b967 |
| gaming_facility_metrics.csv | 68,211 | 27 | as_of_date 1993–2026 | 8fd2b1d1e9009e6baa7ad45ef8a3599bbc64cf7b42d4c131460fe79d07777aa8 |
| gaming_field_coverage.csv | 112 | 7 | — | 1c3c74118c07edad7158caaea86038fd5bcc30dd22f5c94b03244dbb12058cf1 |
| gaming_financing_events.csv | 293 | 39 | opinion_date 2013–2026 | eca79fa02a830f4184cd0f15cece2a54eeeeb98fd9af1add8e6a3ecf03e9d76b |
| gaming_game_finder_observations.csv | 6,851 | 40 | — | 01f9e6a5ae44f8b891cf91df833c7de2cfe021b8cf0208bbc3d29a35f0441bc6 |
| gaming_game_finder_systems.csv | 3 | 16 | — | d03c96eee8a0f5d06b41f0b72c2219502c8abe5213c1f9f1878f5817d295bde3 |
| gaming_land_decisions.csv | 138 | 37 | decision_date 1990–2026 | 0733a2acc5700ea712bb9faf5831586da1af7c795488143b538532f2044f9321 |
| gaming_manufacturer_facts.csv | 62 | 20 | fiscal_year 2020–2025 | c9ad938f90098895330405699ef5e0a22c56ba667d65b23d4264ac2fdeecf04f |
| gaming_mitigation_agreements.csv | 24 | 20 | — | 141001ef38248ea25f855fa95bbc6c934b1d9edb91bb1adccad5e5d3471f98ca |
| gaming_nigc_roster_link.csv | 453 | 20 | — | df95d56d04a3150ddd41794c0e5821d0a4d5a665ffd7733aacaef58f845cc50a |
| gaming_ordinance_ocr.csv | 263 | 19 | — | fd25e79828581995608d14402006aefcda825533cd6118e4b1ba99076c470aad |
| gaming_ordinances.csv | 1,155 | 74 | approval_date 1985–2026 | 091d14c0dacda707ddd4d4d0d05a3e886e80c1424dc3afaf93639f759bf06c34 |
| gaming_project_facilities.csv | 19 | 41 | document_date 2023–2026 | f39a9808eaf11177cb670e92a415fbe85ec7e1e3c024f4c7b46d5b7a5159ccb8 |
| gaming_projections.csv | 116 | 22 | source_document_date 2023–2026 | 792ab62f859198c5a94d284b9300d90ca6d9a45c4abf0ec78b892626cf9f3b4d |
| gaming_properties.csv | 787 | 57 | open_date 1905–2025 | a8dc4fabf92d123ae52200173cacf061aabc42fb1176df31e023e112fbcdd2c7 |
| gaming_property_capacity_history.csv | 64,181 | 18 | as_of_date 2001–2023 | 4e9a5b635c45420b12c20e46e40a395cdd7af4b3f63ee6c5ae36d5cf6b963128 |
| gaming_property_coverage.csv | 787 | 39 | — | 4bda1e80f1b675ca25f9c4928f1812687459a32970ee3883f7a5552e366c12e7 |
| gaming_property_federal_traces.csv | 774 | 70 | — | d4ce278d3ea30b9a3dadbe255968a6e65c66d80725774f79d6bb68753e817e54 |
| gaming_property_labor_demand.csv | 43 | 32 | — | eb662d89d0c239ce509ceedce2fa06f9dad68e3976e58f32a571e2bff9755fa8 |
| gaming_property_locations.csv | 2,212 | 32 | — | 452062b9fb48ee6cd5756d2a32bbc35d7f716c436c4f25da69b51f1b47dc692a |
| gaming_property_self_published_assertions.csv | 1,483 | 45 | as_of_date 2026–2026 | fc1c8c164c40735adcc0d2fac72562a59b7d30954496c8008b12c431fea0acc1 |
| gaming_property_self_published_claims.csv | 584 | 55 | as_of_date 2026–2026 | 90d9d16b2b0057dc21352258430d5e0a127c6b5a02aff08d3692877304401146 |
| gaming_property_site_observations.csv | 262 | 36 | as_of_date 2026–2026 | 35b540949c43a135f04990210433ff0659786646b7461f031dd902ba018437bf |
| gaming_property_universe_events.csv | 10 | 35 | — | 8ab1a7bcfeb3491d7a2fbe4e6c554e6c4fbd41c9696b292e6b505c19e194bff4 |
| gaming_revenue_bounds.csv | 13,803 | 27 | fiscal_year 1994–2025 | 3eb4bb2de028b3b501c0eb773db441c2c0bb0c9d4834673f7e9c4f15bbda5bfc |
| gaming_source_claims.csv | 113 | 25 | fetched_date 2026–2026 | 10a52ada1af0d5f60cec02f0dfc6b1dafd38d6fb1d4332178f6cc3ae6ddde3ff |
| gaming_vendor_tribal_licenses.csv | 740 | 31 | — | 76230b1de7b3fcbb102a3c95d06b2be38e78a57dca910b3f1349efcd5941b4f7 |
| gaming_web_harvest_coverage.csv | 590 | 40 | — | 23e05b0640bc479bf06b9d52eaf5a19354918cb7fe64a49612fae0f31ed31b13 |
| gaming_web_harvest_observations.csv | 1,175 | 43 | as_of_date 2026–2026 | e5dfc3ad2e710ef52a86cfa9b87b1d7047f135c07f46ea92898700a606fd47df |
| loyalty_program_property.csv | 48 | 22 | observation_date 2026–2026 | aa3de0db7a00394920cd5f7b8cb646d5892510e49c962e469a969074b68f4c07 |
| loyalty_programs.csv | 18 | 39 | observation_date 2026–2026 | 7f5cc2d5ac212e095b4aa41097670dd77e265d4eca0da95fc30bf2b76a7e1a53 |
| nepa_administrative_record_parties.csv | 36 | 23 | fetched_date 2026–2026 | 996a1e5dd7ee07aa4885d70d1db6e5feeff1f15412f3be1ce3a9725248663ef5 |
| nepa_eplanning_projects.csv | 312 | 27 | fetched_date 2026–2026 | 494447fc6d3ef3b4af667d2f689c4d34ac1a9acc9c194173d44147dbe3896d64 |
| nepa_project_documents.csv | 789 | 21 | fetched_date 2026–2026 | c6f3328a33e24de03af4169d9453225eb6d6d0a22bf9075881caeee980800553 |
| nepa_source_coverage.csv | 5 | 7 | — | 4269fe0acc649890f09dfc3670e8b4fec4337b66282b9e9faab15ddbe021a984 |
| nigc_action_parties.csv | 386 | 12 | — | e629fae7e66662fecd5eff20058b4126766b3d44322d9c490a4e2670378609b7 |
| nigc_declination_letters.csv | 327 | 61 | opinion_date 2013–2026 | 6b6d12dcb8a665a2c11e7c408e07a413fbc515d0d29188576dbdb1ccf5b296a5 |
| nigc_document_surface.csv | 7,930 | 20 | index_post_date 2015–2026 | 43563669a78fac4e7a114afbd1b76fef126622c4ba2f0a2f4891259dac46ce62 |
| nigc_enforcement_actions.csv | 362 | 36 | document_date 2005–2026 | 69a51649f5814434efc1c126c9057be3366774e669871a92926eafba115ce2a9 |
| nigc_game_classification_opinions.csv | 122 | 25 | opinion_date 1992–2024 | d349f65caa1200ca0821d7854a8f8a248f930dddf4998ece1a0b247fd834e55b |
| nigc_indian_lands_opinions.csv | 102 | 28 | opinion_date 1997–2026 | 77821a34f8abf16567337abb3aa6f0885ef38b29d48687e9156c88d1fb4a72ee |
| nigc_management_contract_approvals.csv | 68 | 36 | document_date 2011–2018 | 6f577d667ae4b439a6897454e1f2db3b3287c752cfbb5369b44198702024e3a0 |
| nigc_region_assignments.csv | 2,438 | 23 | effective_start_year 2001–2025 | df00e9dec700d3df25340446846b2757d6435d286ad9d636e67a8e4ea2cf5f46 |
| nigc_regional_ggr.csv | 198 | 27 | fiscal_year 2001–2025 | c112a5bc82bf57ce45c8fe91dbafd8e8311f6a44ce39dbb24e2643b01706c7cb |
| nigc_revenue_bands.csv | 20 | 29 | fiscal_year 2022–2025 | 9342bb7667bae3de71b14c9e78f94a6bb62618aea8901a1fd7a068afa53f47bd |
| sec_gaming_financial_disclosures.csv | 67 | 53 | fiscal_year 2000–2022 | 8ad223ebd08b26e1e97efc0abdf21d9765e3895dbf54090e83d0f1c66d2b594c |
| sec_gaming_management_contract_terms.csv | 7 | 33 | filing_date 2003–2012 | fa580ae0455706e3368fe8ba179f45e96072a47eafd6fb1d7b0938ebc04fabe6 |
| state_gaming_observations.csv | 494 | 34 | period_end 1992–2025 | 3995f6ab7af4ebbe19535f684b9aade48ab22fcbb2e7927cd5e9920c31504d99 |
| wa_machine_allocations.csv | 75 | 17 | fetched_date 2026–2026 | d560da011a0fe2b22ff2972db4dc615ecc3b7de72440e3e6a473da986acda5d2 |
| wa_machine_transfers.csv | 0 | 18 | — | 97aa260f4bf2d681e6bc8a07ad15c88388ba1550b70add8403f8ed6bc8b2fce2 |

## Implementation status (Claude, 2026-09-24, branch `claude/gaming-intelligence`)

**Repository split (2026-09-24, owner directive; read this first).** Data-side
Gaming state now lives in **Lumecon-data branch `claude/gaming-grove-release`**:
the producers (`src/lumecon_data/gaming/`, ported with history from 1200-1203,
`gaming_grove.py` and the online sportsbook module), the candidate build, the
leak gate, the data contract (`docs/gaming-contract.md`, `schemas/gaming/`),
the VP dispositions (`decisions/gaming/`) and the release and catalog build.
Lumecon builds ONE multi-component Gaming release with one collection manifest
and one catalog entry, and it only PROPOSES ID bindings.

Cedar (`claude/gaming-grove-consumer`, on top of this branch's `75a2f1b`, which
is unchanged) keeps:
- the identity service, as the sole issuer: the `cedar_ids.GAMING_BLOCKS`
  reservation and `code/build.py gaming-issue-ids`, which is not run;
- the pin `data/cedar/grove_release_pin.json`, which is empty until issuance;
- the consumer adapter, entitlement and audit;
- the `gaming/*` field-map presentation entry, which is checked against the
  pinned contract.

The ownership map and the release sequence are in
[HAVALA_INFRASTRUCTURE_REVIEW.md](../HAVALA_INFRASTRUCTURE_REVIEW.md#gaming-repository-ownership-and-cross-repository-release-sequence-2026-09-24).
Cedar's side is in the [infrastructure notes](../GAMING_GROVE_INFRASTRUCTURE_NOTES.md).

The text below records the state and measurements as built on
`claude/gaming-intelligence`. Where it names a Cedar producer, command or
file that has since moved, the Lumecon-data branch is now authoritative.

Current state, updated in place. Built on Cedar PR #122 (`codex/legislation-release-consumer` @3195e70), this audit, and Codex's identifier-retirement commit (cherry-picked `b8626c9` → `0331b82`). Local commits only: not pushed, not promoted, not published.

**Identity: migrated to the ratified contract, no ID issued.** Per `docs/IDENTIFIER_STANDARD.md` ("CICD retirement contract"):
- `CE` for Native entities.
- Existing `CEDAR-PLACE` for physical facilities.
- Existing Cedar NEED enterprise IDs only where an enterprise independently qualifies. Gaming never creates or feeds NEED.
- `CB` for legal operators, held (`held_business_unbound`) until the gated business register binds them.
- `CEDAR-OBS` for observations, `CEDAR-EVENT` for events, `CEDAR-REL` for relationships, `CEDAR-SRC` for sportsbook reporting series and `CEDAR-CONTRACT` for compacts and compact versions, all from static blocks now declared persistently in `cedar_ids.GAMING_BLOCKS` (formerly from `code/gaming_grove.py`).

`VP`, `CCP`, `TPL`, `CEDAR-FAC` and `PROV` survive only as internal source keys. A candidate writes 93,824 **PROPOSED** bindings to its own append-only register: OBS 25,433, EVENT 60,716, REL 5,775, SRC 35 and CONTRACT 1,865. The live registry is untouched, and `release-pilot` refuses any ID not `ISSUED` in the live register.

The full before/after crosswalk is `<candidate>/components/gaming_id_migration_crosswalk.csv`, 95,380 rows. It maps every PROV key, compact key, facility key and legacy handle column to a public ID or a held status, with affected row counts.

The controlled issuance process is Cedar's `code/build.py gaming-issue-ids`. It reads Lumecon's PROPOSED bindings artifact, pinned by hash, and emits a registry snapshot for Lumecon to pin. Preconditions, commands and rollback are in `docs/SHIPPING_RUNBOOK.md` (Cedar Grove Gaming). It has not been run.

Remaining for Codex:
- Declare Gaming bindings in `cedar_ids.IDENTIFIER_CONTRACTS`.
- Run the independent scan.
- Fix the 1169 composite-handle blind spot.
- Remove retired handles embedded in Advocacy's own event IDs.

**16 unbound VP keys: all not-a-gaming-facility.** The reviewed dispositions are now in Lumecon-data `decisions/gaming/` (formerly `docs/GAMING_VP_DISPOSITIONS_2026-09-24.csv`).
- Each is a votingpatterns "no casino" assertion with no address. 1129 deliberately excludes them, and NIGC and CGCC corroborate that.
- VP-0101's "no casino" claim for Yurok is false (Redwood Hotel Casino is `CEDAR-PLACE-000109-XN`) and is never published.
- Tribe-level capacity and CGCC rows hung on these keys were re-keyed to the tribe.
- No owner card was needed.

**Maintained surface (as built here; now `lumecon-data gaming build` in Lumecon-data).** One entry:

`py -3 code/build.py candidate gaming --input-root <Cedar Press> --output-root <new dir outside git> --as-of YYYY-MM-DD [--bindings <live register>]`

Producers run in `cedar_pipeline.GROVE_COMPONENTS` order:
1. 1201: facilities.
2. 1200: revenue, payments, disclosures and online sportsbook (module `gaming_grove_online_sports.py`).
3. 1202: compacts, regulatory events, land, NEPA, licenses and litigation.
4. 1203: labor and advocacy links.

The runner revalidates every table, checks cross-table references, pins input and code hashes and runs the public leak gate (`grove-leak-gate`). It writes a deterministic manifest (timing is split into `*.volatile.json`), public-only samples, and coverage and change reports.

`grove-contracts gaming [--check]` regenerates registration, the field map and [the data contract](../GAMING_GROVE_DATA_CONTRACT.md). The 65 pre-existing gaming tables carry an explicit `grove_role`; nothing was deleted.

**Release path (as built here; superseded).** Multi-component: a release unit was (collection, component table). After the split it is ONE Lumecon collection release. Cedar pins that one release and refuses per-table releases.
- `release-pilot` validates every declared component before writing anything, makes one Lumecon release per component, and builds one catalog.
- The server serves Grove components to grove and tree tiers from a separately pinned Grove catalog (`collections.GROVE_RELEASE_IDS`).
- It refuses PROV- values, vendor facility keys, retired handles (composite forms included), non-CE `cedar_uid`, non-ISSUED bindings, and non-public rights on any field or row.
- Press collections are unchanged; the Legislation and Natural Resources release tests pass unmodified.

**Verification on the migrated candidate (`idmig-1` vs `idmig-2`).**
- All governed outputs, the manifest included, are byte-identical.
- Validation passed with 0 changed or unverifiable inputs.
- The leak gate over 50 public surfaces (87,538 rows) found 0 retired, vendor or PROV values. Before the final build it caught Advocacy source-event IDs embedding `TRBF-` handles; that column is now internal.
- Every public row is `public_official`, `public_derived` or `public_first_party`.
- Shared and overlapping totals stay nonadditive.
- Tests pass: all 380 server tests (32 skipped for environment), the producer tests, build_test, 1170, both node checks and `grove-contracts --check`.
- The live `_id_registry.json` counters are unchanged.

| Component table | Rows | Table status |
|---|---:|---|
| gaming_regional_revenue (198 region + 26 printed national, FY2001–2025; one preferred national figure per FY; FY2013 has no printed total) | 224 | public |
| gaming_revenue_bands (FY2022–2025) | 20 | public |
| gaming_government_payments (CA+FL; forecasts never paid/summable) | 53,465 | public rows 53,124 |
| gaming_reported_revenue_observations (state, digital) | 8,832 | public rows 8,508 |
| gaming_financial_disclosures (SEC, FAC, bonds) | 1,935 | public rows 1,756 |
| gaming_online_sportsbook_units | 35 | internal |
| gaming_online_sportsbook_financials (1,249 regulator/official, 297 secondary) | 1,546 | internal |
| gaming_online_sportsbook_relationships (25 single-entity, 14 not allocated) | 39 | internal |
| gaming_coverage_gaps | 20 | internal |
| gaming_grove_facilities (379 of 702 with official name+location+status) | 702 | source_limited |
| gaming_facility_names / history / capacity | 1,353 / 2,231 / 3,458 | source_limited |
| gaming_facility_relationships (0 owner/operator; 33 first-party self-described affiliations) | 865 | source_limited |
| gaming_facility_crosswalk (all 787 legacy rows disposed once) | 3,133 | internal |
| gaming_compacts / versions | 707 / 1,158 | public |
| gaming_compact_terms | 3,213 | internal |
| gaming_regulatory_events | 3,776 | public |
| gaming_land_eligibility | 240 | public |
| gaming_environmental_reviews / licenses / litigation | 214 / 694 / 96 | source_limited |
| gaming_labor_observations | 4,852 | internal |
| gaming_advocacy_links | 4,871 | internal |

Only public-status components can enter a release; the Gaming pilot declares one today (`gaming_regional_revenue`).

**Online sportsbook package (owner-delivered 2026-09-24).** The three delivered files are hash-pinned and read-only in `cedar-grove-gaming-work/raw/online_sports_2026-09-24/`. The delivered names differ from the integration review: the workbook is `tribal_online_sports_2026-09-24.xlsx`, and there is no standalone monthly CSV (the build reads the zip's `data/*.csv`).

Reproduced counts:
- 1,247 regulator monthly + 293 secondary monthly = 1,540 monthly rows, plus 6 annual-only.
- 31 linked tribes.
- 10 states: 7 with regulator monthly data (CT IN ME MI NJ OH PA), plus AZ secondary monthly, AR secondary annual and IL official annual.
- All 98 cited sources re-hash.

Count distinctions:
- **34 CE IDs vs 31 linked tribes.** The package register lists 34 tribes. Three have no financial row and appear only as coverage-gap participation leads:
  - Eastern Band of Cherokee Indians (NC): no operator-level series.
  - Southern Ute Indian Tribe (CO): no historical series.
  - Ute Mountain Ute Tribe (CO): participation needs review.

  All 34 are valid, active CE IDs; 31 is the correct linked-tribe figure.
- **297 secondary vs 293.** The 297 non-public rows are the 293 secondary monthly rows plus 4 annual Arkansas BetSaracen rows (2022–2025, from a casino revenue dashboard rounded to $0.01M). The other 2 annual rows, Illinois Hard Rock Bet 2024–2025, come from Illinois Gaming Board annual reports and are official, so 1,247 + 2 = 1,249 rows are public_official.

Controls:
- The NJ license/brand overlap is refused in 62 rows.
- The PA Mohegan Dec-2019 discrepancy is isolated to its row (published −31,744.02, calculated −42,875.40).
- Maine's three-tribe report is stored once and not allocated.
- 771 MI/CT rows cross-reference 3,882 existing digital-revenue rows, with equal values.
- One of the seven property-naming units links on evidence (MI NHBP → FireKeepers, `CEDAR-PLACE-000176-S0`); six stay unresolved.

Public wording: a Native-entity link identifies a documented affiliation, regulatory relationship or beneficiary context, not an ownership share or retained income.

**616 / 46 / 22 provenance.** All three reproduce exactly from the untracked `Desktop\4wheeler\casino_employment_validation_SHARE\` bundle, built 2026-08-12 by `13_build_share_bundle.py`:
- `data/casino_employment_panel.csv` (sha256 `8c125cf7…5bb2f`): 616 rows, 46 tribes, 1992–2025.
- `data/facility_events.csv` (`97ddd6f6…b9697`): 22 rows.

**616/46 are a stale snapshot.** About 40 minutes later the live panel became 735 rows / 55 tribes, and no filter on it yields 616.

**22 is current**: the file is byte-identical in every copy. This audit's "none verifies 22" missed it.

The figures are exact but mislabelled:
- The grain is tribe × year × source (605 distinct tribe-years).
- 565 of the 616 rows are Form 5500 plan participants rather than employees.
- The 22 events cover 13 tribes, three of them non-gaming businesses.

Rerunning 13 would delete the only copy, so the bundle is preserved with a verified SHA-256 manifest at `C:\Users\esm247\cedar-grove-gaming-work\preserved\4wheeler_share_2026-08-12\`. The 74-table inventory reproduced exactly (rows, columns, SHA-256).

**Evidence rules applied.**
- Operator and casino websites are `public_first_party`: usable for self-description, never proof of ownership, control, revenue allocation or retention. The former 25 owner / 23 operator rows are now 33 self-described affiliations.
- Secondary compilations are `secondary_corroboration` and never public.
- Vendor lineage (Casino City, votingpatterns, trade directories) stays internal.

**Recorded test results (before pushing for review).** Run on 2026-09-24 against a clean working tree, with the Lumecon venv (`PYTHONPATH=<Lumecon>/src;server`) for the server suite and `py -3` for the rest:

| Check | Result |
|---|---|
| Producer tests 1200 / 1201 / 1202 / 1203 / online sports | 26 / 31 / 12 / 16 / 14 OK |
| `code/build_test.py` | 3 OK |
| `code/1170_dependency_contract_test.py` | 6 passed |
| Server suite (`unittest discover -s server/tests -t server`) | 380 OK, 32 skipped (Postgres or other environment) |
| `node --test` per `src/**/*.test.js` | 29 files pass; 6 cannot load `react` because this worktree has no `node_modules`. The branch changes nothing under `src/` |
| field-map, guides, `grove-contracts gaming`, 521 `check-scripts` (all `--check`) | current / passed |
| `git diff --check` | clean |
| Candidate `idmig-1` vs `idmig-2` | governed outputs and manifest byte-identical; leak gate 0 findings |

Not run: the full `npm test` coverage gate (needs `npm install`) and `1169_release_verify.py selftest` (needs the populated workspace's vocabulary). Codex's independent verification and issuance certificate are the next step.

**Open items.**
1. **Live issuance** (Codex certificate, then an owner decision ID): Cedar `code/build.py gaming-issue-ids`. After it, Lumecon builds a production release and Cedar opens a pin PR. This blocks publication only.
2. **Havala**:
   - a second Grove catalog variable vs one store keyed by product;
   - the Grove landing route;
   - moving the rights check into `apply_field_map`;
   - block reservation (Cedar) vs ordinal proposal (Lumecon), now that the blocks are persisted in `cedar_ids`;
   - the 16 MiB Lumecon intake cap vs the payments table;
   - `512_build_dataset_contracts.py` preserving producer-declared entries;
   - `--authority-root` for the pilot;
   - the repository ownership map and release sequence in `HAVALA_INFRASTRUCTURE_REVIEW.md`.
3. **Owner identity rulings** (bounded; do not pause engineering): the Stables place merge (VP-0153 vs CCP-305300); the 7 Clans Ponca link, kept `reviewed_disputed`.
4. **Acquisition leads** (not acquired):
   - OLMS LM filings and state WARN notices;
   - the EPA EIS database and Army Corps permits;
   - state sports-wagering and licensing censuses;
   - litigation dockets;
   - Arizona official sportsbook reports after 2022;
   - Illinois and Arkansas monthly sportsbook series.
5. **Privacy rule for retrieval**: requests use a project contact, and saved diagnostics never contain personal identifying headers. One earlier CourtListener probe carried the owner's email in its user-agent; it was stopped by robots.txt and nothing was downloaded.
