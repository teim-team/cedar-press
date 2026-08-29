# 02h — `contractor_ranking.csv`

*Codebook fragment. Written by `code/269_build_contractor_ranking.py` on 2026-08-26. `data/clean/codebook_master.csv` is deliberately NOT touched — reconciling master from fragments is `cedar_register_codebook.py`'s job and its owner's timing.*

## What a row is

**One OPERATING COMPANY, with the entity that owns it, that entity's class, and the identifier that establishes the link.** An owner with nine subsidiaries occupies nine rows carrying one `owner_rank`.

## The four things to know before quoting a number off this file

1. **Tier A only.** Nothing below tier A is in this table. The tier is inherited from `cedar_identifier_ledger_final.csv`, never assigned here. `attributed_flag = 1` alone would put a $3.53B General Dynamics subsidiary inside an Alaska Native village government's record at rank 8 — that is a tier-B name-cluster artefact and it is excluded by construction.
2. **This is a FLOOR, twice.** Once because tier B is real money whose owner is not yet proven, and once because the set-aside flags used as the comparison instrument are generous.
3. **`total_obligations` is the only summable money column.** `cedar_domain.SUM_COLUMNS`.
4. **FY2026 is a nine-month partial**, cut at `action_date` 2026-07-03. Every FY2026 figure is year-to-date and only ever grows.

## Provenance

| input | vintage (mtime at build) |
|---|---|
| `data/clean/prime_contracts.csv` | 2026-08-26T18:45:37 |
| `data/spine/cedar_entity_spine.csv` | 2026-08-26T18:59:01 |
| `data/clean/cedar_identifier_ledger_final.csv` | 2026-08-26T18:59:02 |
| `data/clean/individual_native_ownership_verification.csv` | 2026-08-26T18:01:33 |

Entity identifiers follow the NEID scheme published by the **Center for Indian Country Development, Federal Reserve Bank of Minneapolis** (*Native Entity Connector Crosswalk*, February 2026), which seeded the Cedar Press entity spine. `ANVC-` and `ANRC-` prefixes are Cedar extensions to that scheme.

## Variables

| variable | type | published | description |
|---|---|---|---|
| `owner_rank` | integer | yes | Rank of the OWNING entity by tier-A prime obligations, FY2000-FY2026. Dense over entities; repeated on every operating-company row belonging to that owner. Recomputed every build - never join on it. |
| `owner_entity_id` | text | yes | The owning entity's Cedar identifier. Prefix and token follow the NEID scheme published by the Center for Indian Country Development, Federal Reserve Bank of Minneapolis (Native Entity Connector Crosswalk, Feb 2026), which seeded this spine. `ANVC-`/`ANRC-` are Cedar extensions to that scheme. |
| `owner_name` | text | yes | `fr_official_name` from the entity spine where present - the name as it appears in the Federal Register list of federally recognized tribes - otherwise `canonical_name`. Several `canonical_name` values are truncated stems ('Houlton', 'Blue Lake') and must not be printed. |
| `owner_class` | text | yes | TRIBE · STATE_RECOGNIZED_TRIBE · ANC_REGIONAL · ANC_VILLAGE · ANC_GROUP · NHO · ALASKA_NATIVE_VILLAGE_GOVERNMENT · OTHER_NATIVE_INSTITUTION. A village GOVERNMENT is never folded into ANC_VILLAGE: under the ANCSA ownership ruling (docs/ANCSA_OWNERSHIP_RULING.md) a village government never owns an ANC, in either direction, and the two populations name each other by statute. |
| `owner_entity_class_as_recorded` | text | yes | The spine's `entity_class` verbatim, so the mapping above is auditable rather than lossy. |
| `owner_state` | text | yes | Spine state. |
| `owner_obligations_usd` | numeric | yes | Sum of `total_obligations` over this owner's TIER-A attributed prime transactions, FY2000-FY2026, nominal dollars. `total_obligations` is the only summable money column (cedar_domain.SUM_COLUMNS); `total_award_value` is restated per transaction and sums to $5.63T. |
| `owner_share_of_publishable_pct` | numeric | yes | `owner_obligations_usd` as a percent of the tier-A publishable total. NOT a share of all Native federal contracting. |
| `owner_n_operating_companies` | integer | yes | Distinct operating companies (by UEI, or by name where no UEI is recorded) carrying tier-A links to this owner. |
| `owner_n_identifiers` | integer | yes | Distinct (identifier_type, identifier) pairs establishing this owner's tier-A links. |
| `owner_n_uei_links` | integer | yes | Of those, how many are UEIs. Two or more is the visible signature of the SBA 8(a) nine-year non-renewable term: a continuing programme requires a new legal entity with a new UEI. |
| `owner_first_fy` | integer | yes | Earliest fiscal year with a tier-A transaction. |
| `owner_last_fy` | integer | yes | Latest fiscal year with a tier-A transaction. FY2026 is a NINE-MONTH PARTIAL - the prime cut is at action_date 2026-07-03. |
| `owner_native_setaside_usd` | numeric | yes | Tier-A dollars on transactions whose `setaside` is 8(a), Indian Business or Buy Indian. Transaction level, not forward-filled - use the award-level column for shares. |
| `owner_8a_usd` | numeric | yes | Tier-A dollars on `setaside = 8(a)` alone. 8(a) is open to non-Native disadvantaged firms and is NOT evidence of Native ownership. |
| `owner_native_specific_setaside_usd` | numeric | yes | Tier-A dollars on the two Native-BY-DEFINITION set-asides only: Indian Business and Buy Indian. |
| `owner_no_setaside_usd_award_level` | text | yes | Tier-A dollars on AWARDS none of whose transactions carries any Native set-aside. Award key is `(contract_number, awardee_uei)`, matching `docs/CICD_BENCHMARK.md` UNDERCOUNT-01. Award level because `setaside` is blank on the majority of archive-era transactions and arrives as the literal 'None reported' - see the seam register in docs/ANOMALY_REPORT.md. This is the conservative measure and the one the article quotes. |
| `owner_no_setaside_share_pct` | numeric | yes | The award-level column over `owner_obligations_usd`. |
| `operating_company_name` | text | yes | `awardee_name` as recorded on the prime transactions. From BGOV `master prime file.dta` and the USAspending award archive, NOT a SAM entity extract, so the D&B Open Data bulk restriction does not attach. `WITHHELD_POSSIBLE_PERSONAL_NAME` where the personal-name guard fired. |
| `operating_company_uei` | text | yes | SAM Unique Entity ID. Blank where the name was withheld, and blank where the transactions carry no UEI. |
| `publishable_operating_name` | text | yes | `N` where the name may be a private individual's. Contract facts still publish on an `N` row; the name and the UEI do not. Deliberately over-inclusive: SAM's public search resolves a UEI to a legal name, and a sole proprietor's legal name is a private person's name. |
| `privacy_class` | text | yes | `CORPORATE_FORM_PRESENT` · `POSSIBLE_PERSONAL_NAME` · `NO_CORPORATE_FORM` · `UNKNOWN` · `RULED_NOT_NAMEABLE_BY_02f`. The first four use `code/171_build_individual_native_verification.py::privacy_class` VERBATIM so that one project rule about naming a private individual has one definition; the fifth means the UEI was already adjudicated not-nameable in `individual_native_ownership_verification.csv` and a privacy ruling only ever tightens. The rule is blunt on purpose and it withholds names that are plainly corporate (`JVYS`, `YAKAMA POWER`); a reviewer clears those one at a time, never by widening the rule. |
| `link_identifier_type` | text | yes | UEI or CAGE - which identifier carries the majority of this firm's tier-A dollars into the owner. |
| `link_identifier` | text | yes | The identifier value itself. Blank on a withheld row. |
| `link_tier` | text | yes | Always A on this file. Tier is INHERITED from the ledger row that made the link and is never assigned here. A tier-B link never publishes alone; nothing below tier A appears in this table at all. |
| `link_join_route` | text | yes | How prime_contracts reached the ledger: `uei_exact`, `cage_exact`, `parent_uei` or `ruling_applied`. This is the JOIN ROUTE, not the strength of the link - an exact UEI match to a tier-B ledger row is still a tier-B link. |
| `link_ledger_method` | text | yes | The ledger's own `attribution_method`: how a human or a pass established that this identifier belongs to this owner. `hand`, `bgov_manual`, `elijah_ruling`, `web_verified`, `agent_research_two_leg`, `subsidiary_lookup`. `NOT_IN_LEDGER` where the identifier could not be re-found at this vintage. |
| `link_is_ruling` | text | yes | `Y` where `link_ledger_method` is in `cedar_domain.RULED_METHODS` - a permanent human decision that only a new ruling reverses. `N` marks a link that is tier A on evidence but has not been ruled. |
| `link_tier_rationale` | text | yes | The ledger's written reason for the tier, verbatim. |
| `link_ledger_source_file` | text | yes | Which upstream file the link came from. |
| `link_evidence_url` | text | yes | Evidence URL where the ledger carries one. Frequently blank on `hand` and `bgov_manual` rows, whose evidence is the crosswalk itself. |
| `link_legal_business_name_internal_only` | text | no | The ledger's `legal_business_name`. Retained for audit. Treat as internal: it is the one field on this table whose provenance varies by ledger source. |
| `firm_obligations_usd` | numeric | yes | This operating company's tier-A prime obligations. |
| `firm_transaction_rows` | integer | yes | Tier-A transaction rows behind that figure. The grain of prime_contracts is contract x fiscal year x vendor, not one row per award. |
| `firm_first_fy` | integer | yes | Earliest tier-A fiscal year for this firm. Together with `firm_last_fy` this is what makes a successor-firm sequence visible. |
| `firm_last_fy` | integer | yes | Latest tier-A fiscal year for this firm. |
| `firm_native_setaside_usd` | numeric | yes | Transaction-level Native set-aside dollars for this firm. |
| `firm_carries_any_native_setaside` | text | yes | `N` means a flag-based method would never have found this firm at all. This is the column the undercount finding is built on. |
| `firm_8a_usd` | numeric | yes | 8(a) dollars for this firm. |
| `measured_from` | text | yes | The file every dollar on this row was summed from. |
| `source_vintage` | text | yes | mtime of that file at build time. Several agents write it concurrently; a count without a vintage is a claim about a file that no longer exists. |
| `built_date` | date | yes | Build date. |
| `built_by` | text | yes | This script. |
