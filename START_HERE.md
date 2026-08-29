# START HERE — Cedar Press

*Rewritten at the close of 2026-08-12. Dataset table re-verified 2026-08-26.*

**Read order:** `README.md` → **this file** → `AGENTS.md` → `docs/PULL_DISCIPLINE.md` → the
build log for whatever you are touching.

`README.md` (new, 2026-08-26) covers what Cedar Press is, the folder layout, how to run
things, the hard safety rules, and **where the data actually goes** — the Collections
pipeline into `github.com/teim-team/cedar-press`. This file covers *current state*.

**Before quoting a number out of any build log, check
`docs/DOC_CONTRADICTIONS_2026-08-26.md`.** Superseded figures never get overwritten — they
sit in the document where they were written, looking exactly as authoritative as current
ones. That register indexes ~25 places where two documents disagree, and says which is
right.

> **UPDATE 2026-08-29 — there IS version control now.** `Desktop/Cedar Press` is a git
> repository as of commit `2036e46`. It tracks **source only**: 990 files, 38.8 MB — code,
> prose, schemas, manifests, and `data/spine/cedar_identity_register.csv`. It does **not**
> track the ~46 GB of content; data stays versioned by checksum in the run manifests and
> retired by MOVE to `graveyard/`, which survives a file being rewritten in place in a way
> git would not. This does not fix the stale-numbers problem above — a superseded figure in
> a committed document is still committed — but from here on **every change has an author,
> a date and a diff**, so the next contradiction can be traced instead of guessed at.
>
> `.gitignore` excludes content by **extension at any depth**, not by directory, because
> data here does not live in `data/`: 2.5 GB sat in `Federal Spending/`, 139 MB in
> `code/lobbying_pull/`, 21 MB of scraped pages in `code/ancsa_portal/txt/`, and loose
> `.dta` files at the repo root. A directory rule missed all four.

---

## THE FIVE THINGS THAT WILL BITE YOU

**1. A tier is INHERITED from the source row, never assigned by the consumer.**
Learned expensively today. A pass treated any EIN hit in the ledger as tier A,
because an EIN is an exact identifier. But 873 of 1,104 EIN rows sit on 52
entities carrying 5+ EINs each, and **821 are tier B via `need_v6` — 6.5%
accurate, never publishes alone**. Result: UNITED WAY OF THE GREATER CHIPPEWA
VALLEY (Wisconsin) attributed to United Auburn Indian Community (California) at
tier A. **The exactness of the KEY says nothing about the correctness of the
LINK.**

> **1b. AND A RULED METHOD IS NOT A POSITIVE RULING.** Added 2026-08-26, after
> that half-rule let a worse bug through. `code/148_resolve_schedule_i_recipients.py`
> did `tier = "A" if method in RULED`, and **all 317 `elijah_ruling` EIN rows in
> the ledger are tier X — NEGATIVE rulings**, so it published 317 owner
> exclusions as confident attributions (`COLVILLE ROTARY → Confederated
> Colville`, tier A). `attribution_method` says WHO decided; `confidence_tier`
> says WHAT was decided. Same trap in a second vocabulary the same day:
> `status = SETTLED` read as confirmation when the `outcome` was
> `HOLD_OVER_OWNER`. **Read the SIGN before you inherit the AUTHORITY.**
> Standing detector: **`py -3 code/293_lint_bug_classes.py`** — run it after
> touching any tier, and `--class 3` for this class in full with the per-site
> disposition table and the re-derived ledger exposure.
> **`code/248_audit_tier_inheritance_patterns.py` is RETIRED** (2026-08-26) and
> is now a stub that points at 293 and exits non-zero; two detectors for one
> class drift, and a drifted detector is worse than none because it is trusted.
> 293 is the single lint entry point and carries **seven** classes — the
> seventh is a POSITIONAL or otherwise non-deterministic primary key, consumed
> from `code/284_audit_nondeterministic_keys.py`. Full write-up in `AGENTS.md`
> and `docs/CODE_HEALTH_AUDIT.md`.

**2. `09_import_rulings.py` and `01_build_entity_spine.py` remain unsafe to
RUN.** Both rebuild from a stale upstream and silently delete later work. They
are safe to IMPORT — `124_apply_rulings_in_place.py` does that and is the
correct tool for rulings.

**3. `api.sam.gov` rejects a bad key with a STATUS THAT VARIES — 401 *and* 404
have both been measured.** 401 `API_KEY_INVALID` on 2026-08-05 and again on
2026-08-26; 404 on other paths in between. **The stable fact is the one that
matters: neither status is evidence that an endpoint path is wrong.** Do not
conclude an endpoint is absent, or that a key is fine, from either code until
one request has succeeded.

**4. The award archive REPLACES monthly.** All 4,597 keys now carry `20260806`;
`20260706` is dead everywhere. **Probe the stamp at run start, per-year, never
global.**

**5. `prime_contracts.extent_competed` HOLDS TWO VOCABULARIES. Filtering it
selects an ERA, not a competition status.** The USAspending award archive
changed what that column contains at the **FY2016/FY2017 boundary** — FY2008–16
files carry the raw FPDS code (`A`…`G`, `CDO`, `NDO`), FY2017+ and all BGOV rows
carry the rendered label. Measured in the raw extracts, so the break is
**upstream**, not ours. **Filter `extent_competed_normalized` instead** (added
2026-08-26 by `code/207_normalize_extent_competed.py`, one vocabulary, with
`extent_competed_normalized_basis` naming the crosswalk and its URL).
`extent_competed` is kept exactly as recorded — it is the evidence of which
vintage a row came from. The crosswalk is quoted verbatim from **DAIMS-DEC v2.2
(2022-06-03)**, `https://files.usaspending.gov/docs/Data_Dictionary_Crosswalk.xlsx`,
and lives in `code/cedar_extent_competed.py` — never re-derive it from the data.
Once mapped the two vocabularies reconcile: FY2016 vs FY2017, largest
single-category gap **1.86 pp**. **This is an in-place enricher: a rebuild of
`prime_contracts.csv` reverts it and 207 must be re-run.** Full write-up,
including the seam audit of every other column, in
**`docs/EXTENT_COMPETED_CROSSWALK.md`**. `funding_agency` is the other
two-vocabulary column and has **no** normalisation — do not join or group on it
across the seam.

---

## THE DOCUMENT INDEX — every doc in `docs/`, one hop from here

*Built 2026-08-28 by the consolidation pass. **Every `.md` in `docs/` appears
exactly once below.** If you are looking for the current record of a dataset,
find its row here and stop — you do not need to grep `docs/`.*

**Three things this index asserts, and their evidence:**

1. **`docs/DOC_CONTRADICTIONS_2026-08-26.md` outranks every build log on any
   number they both state.** Check it before quoting a figure.
2. **Where two docs cover one dataset, both are named and their split is
   stated.** They are companions; neither was retired. A "superseded" pair in
   this corpus is rare and is always labelled.
3. **Nothing was deleted.** Retired material is in `graveyard/` with an index —
   see the last row.

### Read first (the operating core, outside `docs/`)

| file | what it is |
|---|---|
| `docs/HANDOFF.md` | what was happening and what to do next. **Goes stale fastest of anything here.** |
| `AGENTS.md` | the durable rules, defect classes, concurrency discipline, the NEVER-RUN list |
| `START_HERE.md` (this file) | durable dataset state + this index |
| `docs/WORK_QUEUE.md` | the queue |
| **`docs/NATIVE_ENTITY_NUANCES.md`** | **the entity-type domain knowledge: FR parenthetical bands, renames, village tribe vs village corp, ultimate-owner enterprises. Took the assistance reconciliation from 78% to 100%.** |
| **`docs/IDENTIFIER_STANDARD.md`** | **one identity system (ours), the hub/sub-hub model, external ids, and what may never be published. Read before resolving or joining an entity.** |
| **`docs/ASSERTION_LAYER.md`** | **new 2026-08-29. How a fact carries who said it, why two sources agreeing can be one source twice (evidence lineage), and the 8 ordered rules that pick the value Cedar stands behind. Read before adding a source or trusting a corroboration count.** |
| **`code/build.py`** | **one entry point per collection.** `plan <id>` shows the ordered rebuilds-then-enrichers; `run <id> --execute` runs it. Holds no knowledge of its own — reads NEVER_RUN, the orderings, and the collection map. |
| `docs/ARCHITECTURE.md` · `docs/ENTITY_INVENTORY.md` · `docs/ARCHIVE_CANDIDATES.md` | **GENERATED** by `code/500_*` / `501_*` / `502_*` — what exists, what we hold per entity, and what is safe to retire. Never hand-edit; re-run the script. |
| `README.md` · `STATE_OF_BUILD.md` · `STATE_OF_THE_LAND_2026-08-07.md` | ⚠ the last two are **the densest concentrations of superseded numbers in the project** and carry banners saying so. Their *reasoning* is still good. Prefer this file on any conflict. |
| `SPEC_v2_ENTITY_EVENT_INTELLIGENCE.md` | the v2 spec |
| `*_DATASET_PLAN.md` (BILLS_VOTES, COMPACT, FEDERAL_ACTIONS, GAMING, INFLUENCE, NONPROFIT) | root-level forward plans, not build records |

### Cross-cutting — read before trusting any single build log

| doc | what it is |
|---|---|
| `DOC_CONTRADICTIONS_2026-08-26.md` | **the arbiter.** Where two docs disagree, the measured value is here |
| `FACT_CHECK_2026-08-06.md` | earlier fact-check. ⚠ some findings are themselves now stale — see contradictions **A4** |
| `ANOMALY_REPORT.md` | anomalies across every table (largest doc; touches nearly every dataset) |
| `ASSUMPTIONS_AND_LIMITATIONS.md` | **reporting-regime confounders — read before publishing any trend** |
| `COVERAGE_AUDIT.md` | coverage per dataset. ⚠ still says 790 deals (contradictions **C4**) |
| `DATA_ODDITIES.md` · `CROSS_DATASET_LEARNING.md` · `CROSS_SOURCE_VERIFICATION.md` | standing policy: one source is a claim, two agreeing is a verification, two disagreeing is a finding |
| `CODE_HEALTH_AUDIT.md` · `DEPENDENCY_MANIFEST.md` · `TOOLING_AND_PIPELINE.md` | code health, script→table dependencies, pipeline shape |
| `UNFINISHED_WORK_AUDIT.md` | ⚠ **the 85%-false-positive lesson.** 45 of 53 "unfinished scripts" were detector artefacts |
| `UNSHIPPED_TABLE_TRIAGE.md` · `STAGED_SHIP_CHAIN_2026-08-26.md` · `SHIPPING_RUNBOOK.md` · `STRANDED_DATA_DISPOSITION.md` | what is built but not shipped, and how to ship it |
| `REFRESH_CADENCE.md` · `SOURCE_FRESHNESS.json` | what is stale and how stale |
| `PUBLISHED_LANDSCAPE_2026-08-26.md` · `COMPETITIVE_POSITION.md` · `EDITORIAL_PIPELINE.md` · `CONTENT_ANALYSIS.md` · `DRAFT_top_native_federal_contractors.md` | market, editorial slate, drafts |
| `DATABASE_INTEGRATION.md` · `SUBSET_DATASETS.md` · `DATASET_SCAFFOLD.md` | how datasets are assembled. ⚠ scaffold carries a banner (resources = 734, not 13) |

### Per dataset — the current doc, and its companions

| dataset (`data/clean/`) | current doc | companions / notes |
|---|---|---|
| `prime_contracts.csv` | `PRIME_ARCHIVE_PULL_LOG.md` | `USASPENDING_PROBLEM_BRIEF.md` ⚠ banner'd (says "not yet merged" — it merged) · `CICD_BENCHMARK.md` · `EXTENT_COMPETED_CROSSWALK.md` · `FPDS_HIERARCHY_BUILD_LOG_2026-08-05.md` |
| `federal_funding_transactions.csv` | `ASSISTANCE_ARCHIVE_PULL_LOG.md` | `FEDERAL_FUNDING_MERGE_LOG_2026-08-05.md` · `FEDERAL_FUNDING_RECONCILIATION_2026-08-05.md` · `FEDERAL_AWARD_LISTS_LOG.md` |
| `faads_transactions_all_agencies.csv` | `FAADS_NAME_ATTRIBUTION_LOG.md` | `FAADS_FEASIBILITY_2026-08-05.md` · `FUNDING_PRE2008_BUILD_LOG.md` · `PRE2007_SPENDING_SOURCES.md` |
| `subawards.csv` | `SUBAWARD_API_PULL_LOG.md` | `SUBAWARD_RAW_MATCH_LOG.md` · `SUBCONTRACTING_USASPENDING_PULL_2026-08-05.md` · `SUBCONTRACTING_BUILD_LOG_2026-08-05.md` ⚠ banner'd (its 998 is superseded) |
| `deals_classified.csv` | **`DEALS_BUILD_LOG_2026-08-26.md`** | earlier waves, each a distinct channel and all still the only record of it: `DEALS_BUILD_LOG_2026-08-05.md` (newsroom sweep) · `DEALS_2000_2019_BUILD_LOG.md` · `DEALS_ANC_REPORTS_BUILD_LOG.md` · `DEALS_SEC_2010_2017_BUILD_LOG.md` · `DEALS_PARTY_RESEARCH_LOG.md` · `OWNERSHIP_CHANGE_DETECTION.md` |
| `native_entity_lobbying_disclosures.csv` | `LOBBYING_BUILD_LOG_2026-08-05.md` | `METHODOLOGY_LOBBYING.md` · `LOBBYING_REGISTRANT_BUILD_LOG.md` · `LOBBYING_EXPANSION_RECONCILIATION.md` ⚠ banner'd (97% keyed is really 68.3%) · `ADVOCACY_PASSTHROUGH_LOG.md` |
| `np_orgs.csv`, `np_schedule_i_grants.csv` | `NONPROFIT_ENTITY_LINKAGE_BUILD_LOG.md` | `SCHEDULE_I_BUILD_LOG.md` · `NONPROFIT_BUILD_LOG_2026-08-05.md` · `NONPROFIT_CLASSIFICATION_RESEARCH_LOG.md` · `NONPROFIT_FINANCIALS_LOG.md` · `GRANTEE_990_LOG.md` · `ANNUAL_REPORT_ORG_DISCOVERY_LOG.md` |
| `grantmaker_funding_flows.csv` | `GRANTMAKER_FUNDING_FLOWS_BUILD_LOG.md` | `PHILANTHROPY_DISCOVERY_LOG.md` |
| `gaming_facilities.csv` | `GAMING_SOURCE_AUDIT_2026-08-26.md` | `GAMING_BUILD_LOG_2026-08-05.md` · `GAMING_TEMPORAL_BUILD_LOG.md` · `GAMING_UNIVERSE_REBUILD_2026-08-26.md` · `GAMING_FACILITY_HUB_LINKAGE_2026-08-26.md` · `GAMING_SPEC_RECONCILIATION.md` |
| `gaming_ordinances.csv` | **`GAMING_ORDINANCE_OCR_MERGE_LOG.md`** | `GAMING_ORDINANCE_BUILD_LOG.md` — **genuinely superseded on every provision count**, banner'd in both directions |
| `gaming_property_locations.csv` | `GAMING_LOCATION_LAYER.md` ⚠ banner'd | `GAMING_PROPERTY_SITE_BUILD_LOG.md` · `GAMING_PROPERTY_SITE_REMINE_2026-08-26.md` |
| `gaming_employment_observations.csv` | `LABOR_SOURCES_FOR_GAMING_2026-08-26.md` | `GAMING_EMPLOYMENT_LOG.md` — ⚠ **both still say 769; it is 3,246** (contradictions, "ADDED evening") |
| `gaming_facility_metrics.csv` | `GAMING_CAPACITY_OFFICIAL_LOG.md` | `GAMING_DEVICE_BUILD_LOG.md` · `REVENUE_BOUNDS_LOG.md` · `GAMING_FINANCIAL_EXHAUST_BUILD_LOG.md` |
| state gaming | `STATE_GAMING_FRAMEWORKS.md` | `STATE_GAMING_PULL_LOG.md` · `CA_GAMING_BUILD_LOG.md` · `FL_GAMING_BUILD_LOG.md` · `WA_ALLOCATION_BUILD_LOG.md` · `DIGITAL_GAMING_BUILD_LOG.md` |
| NIGC layers | `NIGC_DECLINATION_BUILD_LOG.md` | `NIGC_REGION_BUILD_LOG.md` · `GAMING_NEPA_PILOT_LOG.md` |
| `compact_structured_terms.csv` | `COMPACT_TERMS_BUILD_LOG.md` | `COMPACTS_BUILD_LOG_2026-08-05.md` |
| `federal_actions.csv`, `nagpra_notices.csv` | `FEDERAL_ACTIONS_BUILD_LOG_2026-08-05.md` | `NAGPRA_BUILD_LOG.md` · `FR_EX_PARTE_BUILD_LOG.md` — ⚠ **both quote pre-refresh counts; now 156,772 / 6,772** |
| `federal_recognition_roster.csv` | `RECOGNITION_HISTORY_BUILD_LOG.md` (verification + defects) | `RECOGNITION_HISTORY_LOG.md` (parsing method) — **companions, cross-linked 2026-08-28; neither supersedes the other** |
| `section_106_consultation_events.csv` | `SECTION_106_BUILD_AND_MERGE_PROPOSAL.md` | `CONSULTATION_BUILD_LOG.md` |
| `admin_appeal_decisions.csv` | `RULING_APPLICATION_LOG.md` | `RECONCILIATION_TOOL.md` |
| `ferc_docket_filings.csv` | `CLASS7_KEY_MIGRATION_LOG.md` | see START_HERE dataset table for current counts (102,615) |
| `foia_request_index.csv` | `CONGRESSIONAL_CORRESPONDENCE_FOIA_BUILD_LOG.md` | — |
| `resource_revenue.csv` | `RESOURCE_LEDGER_BUILD_LOG.md` (ONRR, ND, UT, MT) | `RESOURCE_LEDGER_STATES_LOG.md` (the other 15 states) · `RESOURCE_RECIPIENT_SIDE_LOG.md` · `RESOURCE_ASSETS_BUILD_LOG.md` — **explicitly paired waves, not duplicates** |
| `tribal_tax_bases.csv` | `TRIBAL_TAX_BUILD_LOG.md` | `ND_TRIBAL_TAX_LOG.md` · `ND_SEVERANCE_BUILD_LOG.md` · `TRIBAL_TAX_DECOMPOSITION.md` |
| tribal debt / bonds | `TRIBAL_DEBT_BUILD_LOG.md` | — |
| bills & votes | `BILLS_VOTES_COMPLETION_LOG.md` | `BILLS_VOTES_BUILD_LOG_2026-08-05.md` · `VOTINGPATTERNS_BIA_INDEX_WARNING.md` |
| OIRA / hearings | `OIRA_HEARINGS_BUILD_LOG.md` | — |
| earmarks | `EARMARKS_SCHEDC_BUILD_LOG.md` | — |
| `fac_tribal_single_audits.csv` | `GAMING_FINANCIAL_EXHAUST_BUILD_LOG.md` | plus the CORRECTION section in this file (opt-out, not a bar) |
| dataset 5 (linked file) | `DATASET5_LINKED_FILE_BUILD_LOG.md` | — |

### The spine, identifiers and rulings

| topic | doc |
|---|---|
| entity spine | `ENTITY_HARVEST_LOG.md` · `ENTITY_KEY_PROPAGATION_LOG.md` · `BIE_UIO_BUILD_LOG.md` · `TCU_CDFI_BUILD_LOG.md` · `NHO_SPINE_MERGE_LOG.md` · `NHO_INTERTRIBAL_REGISTER_LOG.md` |
| **assertions, provenance & evidence lineage** | **`ASSERTION_LAYER.md`** — `code/510_assertions.py`; the source registry and resolution rules ship as data in `data/spine/cedar_source_registry.csv` and `cedar_resolution_rules.csv` |
| aliases & relationships | `ALIAS_RELATIONSHIP_MIGRATION_LOG.md` |
| identifier graph | `IDENTIFIER_GRAPH_BUILD_LOG.md` |
| ANCSA / Alaska | `ANCSA_OWNERSHIP_RULING.md` · `ANCSA_PORTAL_BUILD_LOG.md` · `ANCSA_PORTAL_V2_LOG.md` |
| individually Native-owned class | `INDIVIDUAL_NATIVE_CLASS_PROPOSAL.md` · `INDIVIDUAL_NATIVE_OWNERSHIP_VERIFICATION_BUILD_LOG.md` |
| taxonomy | `CEDAR_TAXONOMY.md` (+ `.json`) |
| admin regions | `ADMIN_REGION_CROSSWALK_LOG.md` |
| derivation policy | `SELF_DISCLOSED_DERIVATION.md` |

### Sourcing, access and policy

`SOURCING_STRATEGY.md` · `PULL_DISCIPLINE.md` (**mandatory before any remote fetch**) ·
`ACCESS_TECHNIQUES.md` · `BLOCKED_SOURCE_BYPASS_2026-08-26.md` ·
`API_MANUALS_AND_QUIRKS.md` (**three live defects named in HANDOFF §5**) · `API_KEYS.md` ·
`SAM_EXTRACTION_PLAN.md` · `UNTAPPED_FREE_SOURCES_2026-08-26.md` ·
`COVERAGE_EXPANSION_OPTIONS.md` · `TRIBAL_VENDOR_LISTS_FEASIBILITY.md` ·
`INDIAN_INCENTIVE_PROGRAM_GAP.md` · `DEWEY_BRIEF_FOR_ANOTHER_INSTANCE.md`

### Machine-readable and generated (do not hand-edit)

| path | note |
|---|---|
| `docs/*.json` (37 files) | detector and probe outputs — re-derive by running the script named in the file, never edit |
| `docs/datasets/*.md` (12) | **generated** by `code/24_generate_dataset_docs.py` — fix the script, not the output |
| `docs/codebooks/*.md` (29) | generated codebook blocks |
| `docs/schema/*` (12) | schema contracts |
| `docs/CONSOLIDATION_{DOC,SCRIPT}_INVENTORY.json` | re-derive with `py -3 code/465_consolidation_inventory.py` (read-only, safe) |

### Retired material

**`graveyard/2026-08-28_consolidation/GRAVEYARD_INDEX.md`** — 153 `.bak` files moved out
of the live tree on 2026-08-28, each with its original path, the file it backed up, its
size and its reason tag. **Nothing was deleted.** Earlier graveyard folders
(`2026-08-05`, `2026-08-12_*`, `2026-08-26_*`) predate this pass.

⚠ **Script numbers are not unique.** 43 numbers are shared by two or three different
scripts (`91_` is three different builds; so are `92_`, `94_`, `172_`, `173_`, `174_`).
**`ls code/<n>_*` before claiming a number or citing "script N".** The full collision map
is `duplicate_number_map` in `docs/CONSOLIDATION_SCRIPT_INVENTORY.json`.

---

## THE DATASETS — EVERY ROW RE-VERIFIED AGAINST THE FILES 2026-08-26

*The heading previously read "ALL VERIFIED AGAINST THE FILES 2026-08-12" and it was not
true of every row. Each line below was re-counted from the actual CSV on 2026-08-26; the
`file` column names what was counted, so the next reader can repeat it instead of trusting
it. Corrections are recorded under the table, not silently applied.*

| dataset | file (`data/clean/`) | rows | note |
|---|---|---:|---|
| Prime contracts | `prime_contracts.csv` | **1,217,768** ✅ | **$310.01B**, FY2000–2026 ✅ |
| …attributed | ” | **$244.77B (79.0%)** ✅ | 498 entities ✅ · 888,803 rows |
| Assistance | `federal_funding_transactions.csv` | **701,955** ⚠ | FY2007–2026 ✅ · *was written 684,923* · **3 source vintages, 2 id schemes — see below** |
| FAADS (pre-2008) | `faads_transactions_all_agencies.csv` | 2,769,748 ✅ | unharmonised |
| Subawards | `subawards.csv` | **72,837** ✅ | **FY2021 PROMOTED 2026-08-28: 173 → 9,462.** FY2022–24 still 89/120/166 — those three jobs failed server-side |
| 990 Schedule I | `np_schedule_i_grants.csv` | **58,685** ✅ | **627** distinct `filer_ein` — *was written 628* |
| Grantmaker funding flows | `grantmaker_funding_flows.csv` | **18,656** ✅ | 14 grantmakers ✅ |
| FOIA discovery index | `foia_request_index.csv` | **9,481** ✅ | source logs span 1993–2026; **parsed dates span 1975–2026 and 1,775 rows carry none** |
| IBIA/IBLA decisions | `admin_appeal_decisions.csv` | **15,613** ✅ | IBIA 4,855 + IBLA 10,758; 114/114 year indices |
| FERC docket documents | `ferc_docket_filings.csv` | **102,615** ✅ | **22,540 `ADVOCACY` + 278 `GOVERNMENT_ENGAGEMENT` = 22,818**; **307 of 307 dockets, 0 truncated**; **1,107 entity-linked (1.08%)** (2026-08-26) |
| Game finder observations | `gaming_game_finder_observations.csv` | **6,851** ✅ | 3 systems ✅ |
| NRC public meetings | `nrc_public_meetings.csv` | **251** ✅ | new |
| Section 106 | `section_106_consultation_events.csv` | **1,363** ✅ | was 20 |
| Gaming ordinances | `gaming_ordinances.csv` | 1,155 ✅ | **321 ORIGINAL_ORDINANCE + 834 AMENDMENT. Only 299 distinct `tribe_id`** — *was written "321 tribes"* |
| Compact → named tribal agency | `compact_obligation_tribal_agency_bridge.csv` | **927** ✅ | was 0 named |
| FAC tribal Single Audits | `fac_tribal_single_audits.csv` | **6,780** ✅ | 2,052 `is_public = 1` ✅ |
| Property locations | `gaming_property_locations.csv` | 2,212 ✅ | **1,068 observation rows are `publishable = Y` with a coordinate**, resolving to 539 distinct properties — *the table said "539 publishable coords" without saying 539 what* |
| Deals | `deals_classified.csv` | **935** | **886 entity-linked (94.8%)** — *was written 790 / 752; 921/874 mid-merge* |
| Resource revenue | `resource_revenue.csv` | 10,482 ✅ | 734 recipient-linked ✅; ceiling 966 |
| `tier_A_ruled` | `cedar_identifier_ledger_final.csv` | **1,538** ✅ | was 1,465. Ledger totals: 20,559 rows · A 2,148 · B 5,690 · C 12,524 · X 197 |

### CORRECTION 2026-08-26 — five rows of this table were wrong

Sixteen of twenty-one rows re-counted exactly. The five that did not:

1. **Deals were 790/752; the file holds 921/874.** `790` is the sum of the nine
   `deals_*_additions.csv` files and **omits the 131 rows that come from the two root
   ledgers** — `deals_2026_ytd.csv` (76) and `deals_historical_2020_2025.csv` (56, of which
   55 classify). `docs/FACT_CHECK_2026-08-06.md` finding **B-1** identified this exact
   miscount three weeks earlier: *"the audit globs `deals_*_additions.csv` and never sees
   the 132 rows in the root ledgers."* It kept propagating because nothing connected the
   fact-check to the documents repeating the error. **`docs/COVERAGE_AUDIT.md` still says
   790 in two places and is wrong for the same reason.** `752` is not reproducible from any
   current file.

   **Fixed the same day.** `code/153_merge_base_ledgers_into_classified.py` merged 131 of
   those 132 root-ledger rows (MA2020-008 withdrawn as a duplicate of ANCSA2-2020-004,
   the audited Calista/Nordic row), and the additions-only glob was repaired at source in
   **both** `88_build_deals_taxonomy.py` and `57_autoresolve_deal_parties.py` so it cannot
   recur. `code/155_collect_deals_2026_08.py` then added 14 collected rows. Final:
   **935 rows, 886 entity-linked (94.8%)**, guard clean.

   **Two traps found while fixing it, both worth keeping:**
   - **Re-running 57 to widen its input REBUILDS from the CURRENT spine and loses work.**
     The spine grew 952 → 1,310 since 57 last ran, so a straight re-run repointed
     *Confederated Salish and Kootenai Tribes* from `TRBF-CSKTFR-00` to `TCU-SLSHKT-00` —
     a tribal government onto that tribe's college — plus three more, and dropped four
     parties outright. Rejected, kept at
     `data/clean/deals_party_autoresolved.csv.rerun57_2026-08-26_REJECTED`, and merged
     ADDITIVELY instead by `code/154_extend_autoresolved_parties_additive.py`.
   - **Four autoresolver proposals were the containment defect and were refused by hand**
     (`review/deals_party_refused_2026-08-26.csv`): *Riverside San Bernardino County
     Indian Health Inc* → `UIO-HEALTH-00` (that is "Native Health", **Arizona**);
     *Department of Hawaiian Home Lands* → "Hawaiian Native Corporation" (a state agency
     vs an NHO); and **two AGGREGATE party strings keyed to a single tribe** — an
     eight-recipient IHS round and a nine-applicant award. An aggregate party must never
     resolve to one entity.
2. **Gaming ordinances: "321 tribes" is 321 *ordinances*.** 321 is the count of
   `ordinance_type = ORIGINAL_ORDINANCE` rows. Distinct `tribe_id` is **299**, and **55 rows
   carry no `tribe_id` at all**. Distinct `tribe_name` is 314, so the tribe universe is
   somewhere around 314 and the ID coverage is short of it. Anyone building a per-tribe
   denominator off "321" overstates it by ~7%.
3. **Schedule I: 628 filers is 627.** `docs/SCHEDULE_I_BUILD_LOG.md` line 54 says 628; the
   file has 627 distinct non-blank `filer_ein` across 58,685 rows. Off by one, harmless to
   any conclusion, recorded so the next reader does not re-derive it.
4. **FERC "18,538 advocacy" conflates two event classes.** `event_class` is `ADVOCACY`
   18,310 and `GOVERNMENT_ENGAGEMENT` 228. Their sum is 18,538. Both are advocacy in the
   loose sense and the total is right; the label is not. Note also that
   **`is_lobbying` is `0` on every row** — do not filter on it expecting advocacy.

   **Superseded by the 2026-08-26 completion run**, which finished the remaining 119
   dockets and rebuilt the file: **102,615 rows, `ADVOCACY` 22,540 + `GOVERNMENT_ENGAGEMENT`
   278 = 22,818**. The conflation warning still stands, against the new numbers.
5. **"539 publishable coords" has no stated unit.** The file holds **1,068 observation rows**
   that are `publishable = Y` and carry both latitude and longitude.
   `docs/GAMING_LOCATION_LAYER.md` line 44 is the origin and says
   *"properties with a publishable coordinate — 539"*: the unit is **properties**, and
   several observations can attach to one property. Both numbers are correct about
   different things. Say which.

Two rows are right but were stated in a way that will mislead:

- **FOIA "1993–2026"** describes the **89 retrieved source log objects**
  (`docs/CONGRESSIONAL_CORRESPONDENCE_FOIA_BUILD_LOG.md` line 46), not the request dates in
  the file. Parsed request dates run **1975–2026**, are stored in mixed `M/D/YYYY` and ISO
  form, and **1,775 of 9,481 rows have no parseable date**. Do not build a year series off
  this column without normalising it first.
- **`tier_A_ruled` = 1,538** is correct and is **not** the same as tier A (2,148). It counts
  tier-A rows whose `attribution_method` is in the RULED set defined in
  `code/62_no_regression_check.py`: `hand` 522 · `bgov_manual` 837 · `elijah_ruling` 119 ·
  `elijah_ruling_redirect` 22 · `web_verified` 38. That distinction is the whole point of
  the metric — see the comment block in script 62 — and quoting 2,148 as "ruled" erases it.

**`data/clean/coverage_audit.csv` is stale and must not be quoted.** It is dated
2026-08-06, predates the archive backfill, and reports **prime_contracts = 0 rows for
FY2023–FY2026** (actual: 45,747 / 53,056 / 48,879 / 61,813) and **federal_funding = 0 for
FY2024–FY2026** (actual: 49,871 / 43,254 / 18,325, with FY2023 at 48,481 against the
audit's 6,771). Its `subcontracts` rows sum to 55,035 — the pre-raw-match promotion, before
the 8,513-row pass. A rebuild is in progress. Until it lands, treat every year-coverage
claim sourced from it as unverified, including those in `docs/COVERAGE_AUDIT.md`.

**`dist/` is stale in the same way.** `dist/notes_index.json` and
`dist/02_prime_contracting/prime_contracts.notes.json` both still record prime at
**617,142 rows / FY2000–2022 / 470 entities**, vintage 2026-08-06, and
`federal_funding_transactions` at 476,924 / 2008–2023. `dist/` has not been rebuilt since
the backfill. **Nothing in `dist/` should ship until it is.**

> **SUPERSEDED — measured 2026-08-28.** `dist/` was rebuilt on **2026-08-26**
> and now agrees with `data/clean` exactly:
>
> | | `dist/` claims | `data/clean` holds |
> |---|---:|---:|
> | `prime_contracts` | 1,217,768 | 1,217,768 |
> | `faads_transactions_all_agencies` | 2,769,748 | 2,769,748 |
> | `federal_funding_transactions` | 701,955 | 701,955 |
>
> The 617,142 / 476,924 figures in the struck paragraph are the pre-backfill
> vintage and are dead. **The "nothing should ship until it is" hold is lifted.**
>
> This paragraph cost something before anyone checked it: on 2026-08-28 it was
> read as a live blocker and used to defer running the ship chain — for a
> rebuild that had already happened two days earlier. **A warning with no expiry
> outlives the condition it describes.** When writing one, say what would make
> it false.

---

## CORRECTION 2026-08-26: assistance is 701,955 rows, and it has THREE seams

Measured by `code/334`–`337`. The table is **correct**; what was missing is any
way for a reader to SEE how it is composed. All three seams are now declared in
columns rather than left to be discovered.

**1. THREE SOURCE VINTAGES, YEAR-ALIGNED — and the newest years are the stale
ones.**

| vintage | fiscal years | rows |
|---|---|---:|
| `usaspending_bulk_download_2023-04-09` | FY2008–2023 | 476,924 |
| `usaspending_award_archive_20260806` | FY2008–2023 | 93,536 |
| `usaspending_award_archive_20260706` | **FY2007, FY2024–26** | 131,495 |

**FY2024/25/26 sit on `20260706`, the stamp this file calls dead everywhere.**
New columns `source_vintage` / `source_vintage_basis` are populated on every
row. `87_build_dataset_notes.py` now cites the source edge (**2026-06-30**)
instead of the build date, removing a 57-day overstatement, and ships the
composition. Full reasoning in `docs/REFRESH_CADENCE.md` §1.3a and §4.0a.

**2. TWO IDENTIFIER SCHEMES IN `tribe_id`, worth $107.50B.** 365,535 rows carry
Lineage A's own INTEGER ids; 183,995 carry Cedar NEIDs; 152,425 are
unattributed. **Nothing is blank and nothing is malformed**, so a per-entity
total SPLITS an entity at the boundary and a distinct-entity count
DOUBLE-COUNTS it, invisibly. The scheme is now declared per row in
`tribe_id_scheme_resolved` (never blank). **The crosswalk is NOT applied** —
`data/clean/assistance_tribe_id_crosswalk.csv` already holds 344 of 361
candidates, all tier B, **122 of them via the containment matcher that
AGENTS.md forbids from keying a dollar**, and both
`152_build_assistance_id_crosswalk.py` and `24_funding_merge.py` deliberately
decline to write them in ("the NEID crosswalk is a ruling, not a computation").
Those refusals are honoured; the proposal rides in
`tribe_id_neid_proposed` + `_tier` + `_basis` so a consumer adopts or refuses it
explicitly. **17 integers have no candidate** and are spine gaps (Confederated
Salish and Kootenai, Shoshone-Bannock, Keweenaw Bay).

> ⚠ **`playground.do` IS THE WRONG KEY FOR THIS AND WILL SILENTLY MISLABEL
> EVERY ROW.** It is a real 379-entry shortname→integer key and it belongs to
> the HCI **contracting** lineage. The ranges overlap and disagree:
> playground.do says `307 → Stillaguamish`; this table's `307` is
> `southern ute indian tribe`. The right key is
> `data/raw/external/federal_funding/lineageA_dta_corrtd_tribe_key.csv`.

**3. A FLAG-SHAPED STRING WITH TWO RENDERINGS.**
`business_types_description` renders the federally-recognized tribal government
token both as `...AMERICAN TRIBAL GOVERNMENT (FEDERALLY-RECOGNIZED)` (118,465)
and `...AMERICANTRIBAL GOVERNMENT (FEDERALLY RECOGNIZED)` (7,160) — **one
missing space, one absent hyphen**. An exact-string filter drops 7,160 Native
recipients silently. `business_types_description_normalized` carries one
vocabulary; the original is kept as evidence. Measured across all 26 distinct
tokens, **this is the only such collision**.

**A COMPOUND NEID IS NOT A BROKEN ONE.** `AKNF-MTLKTL-00-TLNGHD` and
`CNSF-MINNCH-LL` are canonical spine ids — 231 of 231 verified present in
`cedar_entity_spine.csv`. The apparent "base" `AKNF-MTLKTL-00` is **NOT** in the
spine. Never strip the suffix to make a join work; it would turn 21,693
joinable rows into unjoinable ones while looking like a normalisation.

**These are IN-PLACE ENRICHERS.** A rebuild of `federal_funding_transactions.csv`
by `24_funding_merge.py` reverts all nine columns. Re-run 335 then 336 after any
rebuild — the `.bak_*_pre335` / `_pre336` files beside the table are the signal.

---

## THE REVIEW QUEUE

`web_claude/entity_reconciliation.html` — **493 observations, 271 with a read**,
nine sources. Rebuild:

    py -3 code/129_build_review_queue.py     # queue + guesses
    py -3 code/128_build_review_page.py      # render, then publish as an Artifact

**Every card must be answerable with the controls it offers.** 60 location-
conflict cards were pulled for failing that — they ask "which source is right?"
while the buttons answer "what class of entity is this?" The genuine ones
(Northern Edge Navajo: Fruitland NM address, Roswell coordinate, 492 km apart)
wait for a map interface.

**The export carries `agreed_with_our_read`.** Confirmations are as informative
as corrections — they are what lets a confidence band earn auto-apply. Bands
today: 85% x17, 70% x152, 55% x45, 40% x55.

---

## TOMORROW, IN ORDER

> ### UPDATED 2026-08-29 — the top of this list changed
>
> **Item 0 is now the only one that unblocks the rest of the mission spec.**
> `docs/ASSERTION_LAYER.md` is new and `docs/FOUNDATION_AUDIT.md` §F-3b records why.
>
> **0. Harvest a SECOND, GENUINELY INDEPENDENT SOURCE for a field the spine already
> asserts.** This is now the highest-value work in the project, ahead of every pull below.
>
> The assertion layer is built (`code/510_assertions.py`, Phase 3, gate green) and it
> measured something nobody had measured before: **every fact in Cedar rests on exactly one
> source.** Across 8,975 single-valued facts — **0** have a second source, **0** disagree,
> and **2** have more than one independent evidence family. The arbitration machinery works
> and has nothing to arbitrate.
>
> Do not read that as "the data agrees with itself." It means nothing has ever checked it.
>
> Harvesting the Federal Register roster directly was the first attempt and is worth
> understanding before the second: 565 of 575 entries matched the spine, and the
> corroborated count **stayed at 2** — correctly, because a copy of the FR sitting in the
> spine and the FR itself are the **same evidence family**. Copying a source into your own
> table does not corroborate it. A warehouse without lineage would have booked 565 new
> confirmations there.
>
> So the second source must be *elsewhere*, not a republication. Best candidates, in order
> of how much they would settle:
>
> 1. **IRS BMF / Form 990** for `entity.state`, `entity.city` and the filed legal name —
>    genuinely independent of the FR roster, and already a declared source
>    (`LR_IRS`) with nothing harvested into it.
> 2. **SAM registration** addresses for the same fields — `LR_SAM`, also declared and
>    unharvested. Note it is self-reported, so it is NOT authoritative for ownership.
> 3. **`entity.website`** from `org_self_statement` — the layer's own I7 check already
>    flags this as a *dead authority*: declared authoritative, asserts 0 times.
>
> ~~**A ready-made first test exists.**~~ **DONE 2026-08-29.** The Bristol Bay defect is
> closed: `354_correction_register.py --apply` (new flag) propagated the applied FA-01
> ruling to all 10 stale tables — 742 rows unlinked, the ledgers marked **tier X** so the
> refutation is permanent and harvested by 510 as deny assertion #332. Root cause was a
> `cluster_v3` name-cluster: "Bristol Bay" matched, the wrong Bristol Bay won, while the
> spine already held the health consortium as `SGVF-BRSTLB-00`. The **repoint** of those
> rows to `SGVF-BRSTLB-00` keys dollars, so it awaits an owner ruling —
> `review/rulings_inbox_2026-08-29_agent.csv`, verification protocol: the owner's CAGE
> check (see the new ownership section in `docs/NATIVE_ENTITY_NUANCES.md`).
>
> Also open, all recorded in `docs/ASSERTION_LAYER.md` under *Where this is honestly weak*:
> `gaming_source_claims` contributes 0 assertions (no `cedar_uid`; 10 of 113 rows resolved);
> **11,676 of 23,310 assertions are `unattributed_legacy`**, meaning half the store carries
> no evidence because the row it came from never recorded any; and
> `entity.is_federally_recognized` has no negative case.

1. **SAM FY2000–2007. BLOCKED ON A KEY — see the correction below.**
   Resets 00:00 UTC. Six variants, **one extract each covers all eight years** —
   `dateSigned` takes a range and the Native slice is ~1.4%.

       SAM_API_KEY=... py -3 code/141_pull_sam_contract_awards.py canary
       SAM_API_KEY=... py -3 code/141_pull_sam_contract_awards.py extract

   `canary` spends **one** call and `extract` **refuses to run until it has been
   accepted**. Do not collapse them back into one command.
2. **OCR.** `py -3 code/150_run_ocr_overnight.py --now` — 27 of 263, resumable,
   8 shards x `OMP_NUM_THREADS=3`. Never uncapped: 8 uncapped shards ran
   *slower per document* than one process.
3. **Prime FY2007 + assistance FY2020/21/22** — host edge-block, not absence.
   Disk is no longer the constraint (30 GB free).
4. ~~**FERC** — 180 of 307 dockets unfetched~~ — **DONE 2026-08-26. 307 of 307
   dockets on disk, 0 refused, 0 truncated.** The final 119 fetched in one
   sequential pass; the host answered every request (a cheap probe in 0.18s, no
   stalled streams, no 429/403), so the 2026-08-12 stall was a property of that
   run's individual sockets and not of eLibrary. `pageNumber` is still
   **zero-based** and `subdockets` must still be a **string** — both carried
   forward unchanged and both are still the reason a docket can look empty.
   **Four dockets were separately topped up**: P-1971, P-2082, P-2146 and
   P-2232 had been written at 2,300–3,200 of 3,555–4,847 documents because
   `PER_DOCKET_BUDGET_S` is 240 seconds, and being marked `done` meant a resume
   would never revisit them. **A per-docket budget that truncates a sheet and
   then marks it done is a silent ceiling** — the only thing that exposed it was
   comparing `documents_retrieved` against `total_hits_reported_by_source` on
   every sheet. Do that check after any 133 fetch.
   **Entity linkage after re-running 168: 1,107 of 102,615 rows (1.08%), 100
   distinct entities** (`filer_entity_link_tier` A 930 · B 177). Still ~1%;
   closing it further is phase-2 harmonisation work, not attempted here.

   **THE REBUILD/IN-PLACE COLLISION HAPPENED AGAIN, ON THE SAME DAY, IN A NEW
   PLACE.** `133 build` is a FULL REBUILD of `ferc_docket_filings.csv` from
   `data/raw/advocacy/ferc/docket_sheets/*.json`.
   `168_link_adjudication_hubs.py` (renamed mid-run from 163) had, four minutes
   earlier, written its links into that same file IN PLACE — raising it 581 →
   931 and adding nine columns. The rebuild reverted all of it, exactly as
   script 09 reverts script 50's patches. Nothing warned; the build printed a
   larger row count and looked like pure progress.
   **Repaired by re-running 168**, which is designed for it: zero network calls,
   `.part`-then-rename, backs up to `.bak_<date>_pre163`, and it explicitly
   *honours a pre-existing 133 link and never re-litigates it*. On the enlarged
   file it beat its own earlier run — 1,107 links against 931 — because there
   are more dockets to link on. `ferc_docket_parties.csv` went 183 → 11,563
   rows and `ferc_tribal_dockets.csv` 183 → 307.

   **AND THEN IT HAPPENED A FOURTH TIME, TO THE DOCKET TABLE, AS A PARTIAL
   RESTORE.** Found the same evening by the new retrieved-vs-reported check in
   `code/62_no_regression_check.py`, which failed on its first run naming
   P-2232 at 2,308 of 4,838, P-2146 at 2,404 of 4,847, P-1971 at 3,004 of
   4,241 and P-2082 at 3,200 of 3,555 — **the exact four dockets topped up
   above**. The raw sheets were fine: all 307 complete, 0 short. The clean
   table was not. From the backups, `133 build` wrote the correct 307-docket
   table at 17:37 and by 17:50 the live file was the **183-row pre-rebuild
   vintage** again with the 08-12 truncated counts, which `168` then enriched
   with its ten link columns. `ferc_docket_filings.csv` did **not** revert. So
   the two files described different universes — 102,615 filings drawn from
   307 dockets, described by a docket table listing 183 — and neither file
   looked wrong on its own.
   Repaired by `code/175_restore_ferc_docket_table_after_rebuild_revert.py`
   (307-row base + the ten enrichment columns merged on `docket_number` +
   `subdocket`, after verifying the base holds every live key). **124 dockets
   recovered; the gate's truncation metric went 4 → 0.** The recovered 124
   carry BLANK link columns — blank means *not yet linked* — so **re-run
   `168_link_adjudication_hubs.py`** to finish them.
   **The rule this earns: a partial restore is a rebuild revert wearing a
   different hat.** Restore the whole set or none of it, then run the enricher
   last.
   **The rule this earns: a full-rebuild stage and an in-place enricher on one
   file need an ordering, and the enricher must run LAST.** Before running
   `133 build`, check whether an in-place linker has touched
   `ferc_docket_filings.csv` since the last build — a `.bak_*_pre<script>` file
   sitting beside it is the signal — and re-run that linker afterwards.

   **LATENT: `ferc_filing_id` IS NOT STABLE ACROSS REBUILDS.** Its last segment
   is `abs(hash(filer_organization)) % 10000`, and Python randomises string
   hashing per process, so the same document gets a different id every build.
   Measured across the 08-12 and 08-26 files: **4 of 2,534 shared documents kept
   their id.** Nothing keys on the column today — it appears only in the file
   and in `133_build_ferc_advocacy.py` — so nothing is broken yet, and that is
   exactly why it is worth writing down now. **Do not join on
   `ferc_filing_id`**; join on `docket_number` + `accession_number` +
   `filer_organization_as_recorded`, which is what the id is built from anyway.
   Fixing it means a stable digest (`hashlib.md5`) in place of `hash()`.
5. ~~**641 FR ex parte notices**~~ — **DONE, and the line was wrong twice.**
   Struck 2026-08-26; see `docs/FR_EX_PARTE_BUILD_LOG.md`.
   (a) **133 already pulled it on 2026-08-12** — 641 documents, 609 the notice
   series, **4,248 communications** in `ferc_ex_parte_parties.csv`. The queue
   entry predates the work by a few hours.
   (b) **641 was never 641 notices.** It is a full-text term count for ONE
   agency's phrase, and it includes Order No. 607, Sunshine Act notices and
   the 2003 tribal consultation policy statement.
   `code/154_build_fr_ex_parte_notices.py` swept the FR-wide surface instead:
   **7,818 documents carry an ex parte phrase, and outside FERC only 69 name a
   party** (ITA 40, NHTSA 7, FCC 4, Copyright Office 3, …) → 112 party rows,
   `fr_ex_parte_notices.csv` / `fr_ex_parte_parties.csv`.
   **The FCC is 4,430 of the 7,818 and contributes almost nothing** — its ex
   parte filings are in ECFS, and the FR text is permit-but-disclose
   boilerplate. **"Ex Parte No. 733" is a DOCKET NUMBER at the Surface
   Transportation Board** (616 documents); matching the substring would have
   typed them as communications. Two FERC notices 133 never saw are staged for
   it to adopt.
6. **The SAM role request** — 10/day → 1,000/day. Subawards need ~2,733
   paginated calls and are **not attemptable** without it.

---

## STANDING RULES EARNED TODAY

- **Blocking one bad-match path pushes it to the next.** The containment guard
  fixed "Denver Indian Health → Native Health"; the same match then arrived via
  the token path. `NAME_TRAPS` now covers both, 39 terms.
- **A place suffix makes a tribe name a place.** "Boys & Girls Clubs of Wichita
  Falls" is not the Wichita Tribe.
- **Only 404 and 403 are facts about an object.** A 500 means try later.
- **An interruption must not look like a completion.** Write `.part`, then
  rename.
- **Never kill by image name, or by a substring that could appear in another
  run's arguments.** A filter matching `--hosts www.winstar.com` killed the
  wrong process because that string sat in a different run's host list.
- **Back up an output before re-running a build whose counts are asserted
  elsewhere.**
- **Script numbers 130–150 are taken and the prefix no longer implies step
  order** — five collisions today from concurrent agents.

---

## LICENSING, BEFORE ANYTHING SHIPS

- **Casino City** may be read for QA and never published. `tribal_property_list`
  IS Casino City — the vendor share of the property universe is **610 of 774**,
  not 440.
- **D&B Open Data** (legal name, street, city, state, ZIP) may not be
  disseminated in bulk, and attaches to every base award dated before
  2022-04-04 — 100% of the SAM FY2000–2007 backfill. Contract facts publish;
  entity name and address do not.
- **Dewey Data** — paper and product have different licence answers.
  `docs/DEWEY_BRIEF_FOR_ANOTHER_INSTANCE.md`.
- **A SAM socio-economic flag is self-certification.** Goldbelt Raven, an ANC
  subsidiary, certifies `alaskanNativeCorporationOwnedFirm = NO`.

---

## CORRECTION 2026-08-12: the tribal Single Audit "dead end" was wrong

This file listed tribal Single Audits under **documented dead ends - do not
retry**, on the strength of 2 CFR 200.512(b)(2) and Seminole Tribe of Florida
returning `is_public: false` on 10 of 10 filings.

**2 CFR 200.512(b)(2) is an AUDITEE OPT-OUT, not a bar.** Measured on
`api.fac.gov`:

| `entity_type = tribal` | |
|---|---:|
| general records | **6,780** |
| `is_public = true` | **2,052 (30.3%)** |
| `is_public = false` | 4,728 |

The published set includes gaming tribes whose reporting-package PDFs download:
Sault Ste. Marie, Mississippi Choctaw, Muscogee (Creek), Gila River, Turtle
Mountain, Quapaw, Robinson Rancheria.

**One auditee's election was generalised into a rule about the source.** That is
the same error shape as "broken search != absence" - a property of one record
read as a property of the whole system. A dead end recorded from a single
entity's behaviour needs a second entity before it is written down.

### What is actually withheld, measured per endpoint on matched samples of 25

| endpoint | public auditee | non-public auditee |
|---|---|---|
| `notes_to_sefa` | 25/25 | **0/25** |
| findings / corrective actions | 25/25 | **0/25** |
| reporting-package PDF | serves | **403** |
| **`federal_awards` (SEFA)** | **25/25** | **25/25** |

**The SEFA survives the withholding; the reporting package does not.** 127 SEFA
rows exist for Seminole FY2022 against a 403 on its PDF. No API table carries
the financial statements at all - that is `NOT_FOUND`, and it is why the PDF
layer was needed.

### What it yielded

**25 `MACHINE_PARTICIPATION_ARRANGEMENT` disclosures across 8 tribal entities**,
and **2 with an exact figure** typed `MACHINE_PARTICIPATION_EXPENSE` - Robinson
Rancheria wide-area progressive, **$319,889 (FY2019)** and **$210,827 (FY2020)**.
Arrangement and measure are separate columns: a participation note with no dollar
still proves the arrangement exists.

Sault Ste. Marie FY2022-24, verbatim: *"The Gaming Authority leases some of its
slot machines from gaming equipment manufacturers under participation
arrangements, whereby the gaming manufacturer receives a percentage of the handle
or net win."*

### Access note

**`api.fac.gov` is fronted by api.data.gov**, so the existing key in
`dissertation/docs/API_KEYS.md` works on it at 1,000/hr. `DEMO_KEY` 429s after
about seven calls. All 340 PDFs fetched had a text layer - no OCR backlog.

---

## CORRECTION 2026-08-26: subawards were never 76,361, and promotion is complete

The table above read **76,361** under a heading claiming verification against the
files. The file held **63,548** that day, and `docs/SUBAWARD_API_PULL_LOG.md`,
written the same day, states 63,548 three separate times. The string `76,361`
appears nowhere else in the repo and does not match any other subaward-family
file. Corrected above.

**Do not go looking for ~12,800 missing rows, and do not try to "promote" the
staging directory.** Both were investigated on 2026-08-26 and both are dead ends:

- `_PROMOTION_SUMMARY.json` is a **completed-promotion record**, not a hold.
  55,035 retained rows + 8,513 from the raw-match pass = **63,548 exactly**.
- Every staged row was checked for membership against the clean file on
  `(subaward_number, prime_award_unique_key, subaward_amount)`. **Zero staged
  rows are uncovered.** Both staging sets landed.
- `subaward_uei_netnew_2026-08-05.csv` is a **252,078-row UEI dimension table**,
  one row per UEI, 8 columns. It is **not subawards**. Summing it into a row
  count produces a phantom ~317k figure. It fooled one reader already.

~~**The FY2021–2024 hole is upstream, not ours.**~~ **OUT OF DATE — FY2021
LANDED AND IS PROMOTED (2026-08-28).** `_state.json` now shows
`fy2021: finished`, 765,109 rows (csv-parsed and confirmed exactly: 242,337
contracts + 522,772 assistance). It was promoted on 2026-08-28 and
`subawards.csv` is **72,837** rows. **fy2022, fy2023, fy2024 and
fy2020_procurement remain `status: failed`** with the opaque body
`"An error occurred."` — those four are still upstream.

**The promotion route in the sentence below was WRONG and is corrected here.**
It is **not** "re-run 41 and 45". `41` and `45` read only the
`usaspending_subawards_2026-08-05` directory and cannot see the 08-12 pull at
all; `45` additionally re-reads the live table through `load_existing()`, which
relabels every row `highergov_2023_export`, and writes 49 columns, dropping the
deflator enrichment. **The route for anything in `usaspending_2026-08-12/` is
`py -3 code/121_pull_subawards_api.py match` then `… append`** — and `append`
is also the inflation enricher, so there is no third step. `append` is
idempotent on the columns but **not** on the rows: it does not dedupe, so run
it once per `match`. For a retry of the failed years, `collect` — **never
`pull`** — then `match` → `append`. Never raise `MAX_INFLIGHT` above 1.

**Linkage is better than the headline number suggests.** `prime_native_tribe_id`
is populated on 26,430 rows (41.6%) and `sub_native_tribe_id` on 38,336, but
**either is populated on 63,504 of 63,548 — 99.9%.** Quoting the 41.6% alone
understates the dataset badly.

---

## CORRECTION 2026-08-26: the SAM `emailId` line above was FALSE, and the key is DEAD

This file previously told the next agent that `emailId` "is now supplied and the
first extract is a canary." **Neither was true.** It was written from an
intention, not from a run, and it is the exact shape of claim that costs a day.

### What the log actually held

All six extract variants failed at **00:06 UTC on 2026-08-13**, HTTP 400:

> "Parameters 'format' and 'emailId' must both be supplied for successful
> emailing of the download link. Please re-submit your request with both
> parameters or none."

The logged URLs carry `format=csv` and **no `emailId`**. Five calls — the whole
remaining daily budget — died on one defect, because six identical requests went
out together and the first one's answer was never waited for.

**The API key was never the problem.** A rejected key does not return 400 with a
parameter message.

### What was fixed in `code/141_pull_sam_contract_awards.py`

- **One builder, one enforcer.** `extract_params()` is the only place an extract
  request is constructed and it writes `format` and `emailId` as a literal pair;
  `check_params()` re-checks the pair **pre-flight**, before the socket opens, so
  a malformed request is refused at zero quota cost. Neither can be edited away
  without the other catching it. An empty string counts as absent.
- **The `emailId` value is the SAM account address** and is used for nothing
  else. Override with `SAM_EMAIL` if the account moves.
- **The canary is a SEPARATE INVOCATION.** `canary` spends exactly one call;
  `extract` **exits non-zero and sends nothing** until an accepted canary is on
  record. A canary that lives inside the same loop it is meant to guard is not a
  canary — that is what 2026-08-13 proved.
- **`extract` now stops on 400/403/404/429**, not on 400-if-first. Repeating a
  parameter error five times is five ways to learn one fact.
- **The redaction bug is gone.** `record()` spliced strings by hand and dropped
  the `&` after `REDACTED`, so every logged URL read
  `api_key=REDACTEDdateSigned=...`. It now round-trips through `parse_qsl`,
  keeping every parameter legible and the key value out. A log you cannot read
  the parameters off is why a missing `emailId` took a day to see.
- **Quota accounting distinguishes three states**: a request never sent
  (`request_sent: false`), a request sent that charged nothing
  (`charged_quota: false`), and a real metered call.

### THE BLOCKER: there is no working SAM key on this machine

**Measured 2026-08-26, one request, zero quota charged:**

```
HTTP 401  <h1>API_KEY_INVALID</h1>
```

The only key on disk is `SAM_GOV_API_KEY` in
`dissertation/data/tribal_federal_spending/.env.local`, **last written
2026-04-27**, dead since the 2026-07-25 rotation and re-confirmed dead today.
The key that returned HTTP 200 on 2026-08-12/13 **was never persisted anywhere**
— it lived only in that session's environment. Both `docs/API_KEYS.md` files
still describe SAM as `ROTATED - needs new key`, and they were right.

**An invalid key has no subscription, so the gateway rejects it before any
throttle counter exists to increment. The 401 charged nothing: the full 10 calls
for 2026-08-26 remain unspent.**

**To unblock:** log in at sam.gov directly — **do not follow the link in the
rotation email** — Workspace > Profile > Account Details > **Public API Key**,
eye icon, one-time password to email. Then:

    export SAM_API_KEY="<new key>"          # note: 141 reads SAM_API_KEY,
                                            # not SAM_GOV_API_KEY
    py -3 code/141_pull_sam_contract_awards.py canary     # ONE call
    py -3 code/141_pull_sam_contract_awards.py extract    # the other five

Write the new key into `dissertation/docs/API_KEYS.md` (the master) at the same
time, or the next agent repeats this search.

### The licensing mark travels with the output

Every row of this backfill is a base award dated before 2022-04-04, so **D&B
Open Data attaches to 100% of it**. Contract facts (PIID, action date,
obligation, NAICS, agency, socio-economic flags) publish. **Legal business name,
street, city, state and ZIP do not, in bulk.** The destination directory carries
`LICENSING.md` stating this, written before any data lands rather than after.

---

## UPDATE 2026-08-26, later: the key came back, and `emailId` is NOT AN EMAIL

The correction above stands on the code fix and on the D&B mark. Its "no working
key" section is **superseded**: a replacement was collected, persisted to three
non-session locations, and **all six FY2000–2007 extracts were accepted.**

### The finding that cost one call and was worth it

The canary — one request, exactly as designed — came back:

```
HTTP 400  "Parameter 'emailId' must be either YES or NO."
```

**`emailId` is a BOOLEAN FLAG on this endpoint, not an address.** The parameter
is named `emailId`; the 2026-08-13 error said the pair is required "for
successful emailing of the download **link**"; every reading of that says
*supply an address*. It is wrong. The link goes to the address on the SAM
account, and this parameter only chooses **whether** to send it.

Two weeks of blockage came from a message that named the missing parameter and
still misled about its type. **An error naming a parameter tells you WHICH one
is wrong, never WHAT it should contain.** The canary is what made that cost one
call instead of six.

We send `emailId=YES` deliberately: the response body carries the token, but an
accepted job whose token is lost is a wasted call out of ten, and the email is a
second copy at no extra quota.

### What landed

| variant | class | exportToken |
|---|---|---|
| INDIAN | ENTITY_OWNED | `EANGlhSctK` |
| ALASKAN NATIVE | ENTITY_OWNED | `fdgGBhrCjJ` |
| NATIVE HAWAIIAN | ENTITY_OWNED | `YkWOTVSRHn` |
| TRIBAL | ENTITY_OWNED | `zrlwsqiydG` |
| AMERICAN INDIAN | INDIVIDUAL_NATIVE_OWNED | `xAjEAaGtTI` |
| NATIVE AMERICAN | INDIVIDUAL_NATIVE_OWNED | `PTdhhaQztU` |

All six checkpointed to
`data/raw/contracts/sam_contract_awards/_export_tokens.json`. ~~**Zero CSV rows
are on disk yet** — the files were still generating when the budget ran out.~~

> **CORRECTED 2026-08-28. Three extracts landed and one more was loaded.**
> On disk: `sam_extract_EANGlhSctK.zip` (INDIAN, 48 MB),
> `sam_extract_PTdhhaQztU.zip` (**NATIVE AMERICAN, INDIVIDUAL_NATIVE_OWNED**,
> 50 MB) and `sam_extract_YkWOTVSRHn.zip` (NATIVE HAWAIIAN, **52 KB — three
> orders of magnitude smaller than its siblings; verify before trusting it**).
> `_loader_state.json` also records `zrlwsqiydG` (TRIBAL) as processed:
> 8,273 rows in, 1,730 added, 6,543 already present.
>
> **Still to download: `fdgGBhrCjJ` (ALASKAN NATIVE), `zrlwsqiydG` (TRIBAL
> re-fetch) and `xAjEAaGtTI` (AMERICAN INDIAN, INDIVIDUAL_NATIVE_OWNED).**
>
> **The quota counter lies about the reset.** Measured 2026-08-28: the local
> `spent_today()` read `0/10` and the very first download returned
> **HTTP 429 — `"You have exceeded your quota. You can access API after
> 2026-Aug-29 00:00:00+0000 UTC"`**. The local counter rolls at local midnight;
> the server enforces its own 24-hour window. Trust the server's
> `nextAccessTime`, not the local count, or you will spend a call learning it
> again. `download` handled it correctly — it stopped and kept the token.
>
> **CORRECTED AGAIN 2026-08-29 03:56 UTC: THE TOKENS EXPIRE.** The note above
> says *"a token is retryable tomorrow; a submission is not."* The first half is
> false. Quota had reset (`0/10`) and the download returned
> **HTTP 403 `"Token provided has expired"`**. The three unfetched exports
> (`fdgGBhrCjJ` ALASKAN NATIVE, `zrlwsqiydG` TRIBAL, `xAjEAaGtTI` AMERICAN
> INDIAN) are **dead and must be re-SUBMITTED**, spending extract quota again.
> **Download the same day you submit** — the irreplaceable half is only
> irreplaceable for about 48 hours.
>
> **`download` filters on the VARIANT NAME, not the token.**
> `download xAjEAaGtTI` silently matches nothing and prints only the quota
> line, which reads as success. Use `download "AMERICAN INDIAN"`.

### THE TRAP IN THE DOWNLOAD LEG — read this before discarding a token

A download attempted while the export is still building answers:

```
HTTP 303  "Cannot proceed with download: The specified key does not exist.
           (Service: S3, Status Code: 404 ...)"
```

**That 404 is S3's, about an object not yet WRITTEN.** The standing rule *"only
404 and 403 are facts about the object"* is about `api.sam.gov` answering for
our request — it does not reach a storage-layer 404 quoted inside a 303 body.
Read literally, that string says "the export does not exist" and gets a **live
token thrown away and the call resubmitted**, which discards accepted
server-side work for nothing. `download()` now recognises it explicitly and
keeps the token.

### Where the ten calls went, and what is left

| | calls |
|---|---:|
| canary #1 — `emailId` as an address, 400 | 1 |
| canary #2 — `emailId=YES`, **accepted** | 1 |
| extract, five remaining variants | 5 |
| download probe (INDIAN) — still generating | 1 |
| **spent** | **8/10** |

**Tomorrow, after 00:00 UTC, spend the first six calls on
`py -3 code/141_pull_sam_contract_awards.py download`** — nothing else. The
tokens are already paid for; the submissions are the irreplaceable half and they
are done. A download is retryable, a submission is not, which is why the budget
went to submissions first.

Then reconcile against the 42,322 verified FY2012 archive rows **before**
trusting any of FY2000–2007, and dedupe across variants on PIID + modification
number. The two classes stay separate and are never summed into one "Native"
total.
