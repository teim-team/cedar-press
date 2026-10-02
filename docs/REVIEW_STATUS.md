# Review status

Updated 2026-10-02. **Engineering and evidence review is in progress; this is not production release approval.**

Individual records remain individual records. The Native-owned business view leads
with each business name; a certifying tribe appears only as a separately qualified
relationship. This review inventory counts rows; it does not replace them with an
aggregated dataset. Sample bytes, source keys and identifiers are preserved.

## Collection inventory

All 15 collections received structural population checks for counts, declared keys, schemas, and preservation. Source claims received finite, documented fact checks. **The roughly 2.1 million release records have not all been independently fact-checked.** These are mixed-grain records, not a count of unique people, businesses, awards, or economic activity.

| Collection | Records in reviewed releases, including internal components | Permitted review/export rows |
| --- | ---: | ---: |
| Prime Contracting | 841,002 | 841,002 |
| Deals | 978 | 978 |
| Federal Register | 21,258 | 21,258 |
| Foundation & Corporate Giving | 7,801 | 193 |
| Federal Funding | 640,942 | 640,942 |
| Gaming | 86,563 | 68,340 |
| Legislation | 3,064 | 3,064 |
| Advocacy / Lobbying | 27,825 | 27,825 |
| NAGPRA | 6,792 | 6,792 |
| Natural Resources | 11,120 | 11,120 |
| NEED | 143,369 | 43 |
| Native Nonprofits | 89 | 89 |
| Native-Owned Businesses | 3,725 | 3,725 |
| PLOT | 235,385 | 151,715 |
| Subcontracting | 70,054 | 70,054 |
| **Total** | **2,099,967** | **1,847,140** |

The original census contained 2,099,924 records. The current reconciliation adds 43 NEED reviewed-base records while preserving its 143,326 original internal records; count-preserving refreshes retain the other collection totals. The 14 Press collections contain 1,778,800 permitted observations; the remaining 68,340 permitted rows belong to Grove Gaming. Source-admission holds outside the assembled releases are not included in this table. Export permission does not imply deployment or production approval. Gaming and the incoming Native Infrastructure collection remain Grove-only.

## Evidence and identity limits

- **NEED:** 43 reviewed rows are permitted through the proof-bound public-base component. Claim-scoped records preserve affiliation separately from ownership, including null ownership and federal identifiers where unproved. This cohort does not establish identities for the remaining 5,777 of the 5,820 enterprise source rows. Four unmatched candidate entries remain held separately. Internal patent, rating, relationship, and other restricted components retain their existing rights and holds.
- **Giving ↔ Nonprofits:** the recipient comparison covers 244 source records and 217 observations, producing **11 HOLD candidates and zero CONTESTED candidates**. Fourteen primary-source captures support six organization identity checks. The comparison preserves raw EIN formatting and dated address qualifications. No candidate was canonically promoted, and identity evidence does not establish a donation's correctness. The funder comparison produced zero candidates, which is not a negative identity finding.
- **NEED ↔ Subcontracting:** candidate processing was refused at the configured resource bound. No completed candidate result or no-match conclusion is claimed. Rerun only through a validated resource plan; do not bypass rights or memory guards.
- **Definitions:** 135 maintained reviewed definitions resolve the current preview fields, with zero unresolved definitions in that scope. This does not certify every historical source field.
- **Visual QA:** 45 source-table screenshots cover first, middle, and last sample panels across the 15 collections. The updated local Press desktop/phone review checks individual record names, qualified entity roles, monetary meanings and source columns. The final screenshot receipt is retained with the engineering review packet; it does not substitute for source verification. Neither screenshot set verifies all source facts or proves a deployed preview.

Use the [Native entities, relationships, and identifiers guide](https://github.com/teim-team/Lumecon-data/blob/767800c7aaa82508af4f454ad08ae1fa4a21a5ff/docs/native-entity-resolution.md) to distinguish governments, businesses, owners, certifiers, affiliations, and dated identifier evidence. A shared name, address, or owner identifier is not sufficient for a business identity merge.

## Code checkpoints

| Component | Reviewed checkpoint | Status |
| --- | --- | --- |
| Producer | `767800c7aaa82508af4f454ad08ae1fa4a21a5ff` · [PR 17](https://github.com/teim-team/Lumecon-data/pull/17) | Hosted run 36962650641 passed Python 3.12/3.13, PostgreSQL, both consumer contracts, safety, package and audit jobs. New supplied-bundle adapters remain a separate working-tree change. |
| Economic engine | `8ce67dcb448a26edb17102afb46e396ba916870c` · [PR 25](https://github.com/teim-team/teim-engine/pull/25) | Reported hosted run 36954632861: 1,271 database-enabled tests, 90.74% coverage. |
| Cedar service | `42b07e3465c8dc4486121c03419af10655526bfb` · [PR 33](https://github.com/teim-team/cedar/pull/33) | CI green; 576 Linux service tests, 80.76% coverage, seven database tests separately, lock, lint, runtime audit, Docker build and Terraform Plan passed. Two optional Docling tests remain unexecuted. |
| Press | [PR 132](https://github.com/teim-team/cedar-press/pull/132) | Current local integration: 621 frontend tests passed, one skipped; 88.92% lines, 84.89% branches, 90.45% functions. October 2 API run: 652 tests, one Windows skip, 87% combined coverage, with an isolated PostgreSQL database. ESLint, Ruff, six generated-artifact checks and both dependency audits pass. Earlier browser results remain historical; new browser verification and hosted checks on the final head remain required. |
| Grove | [PR 181](https://github.com/teim-team/teim-app/pull/181) | 2,015 frontend tests passed (33 skipped, no TODOs); lint/build passed. Final consumer pins and Linux server verification remain open. |

Results apply to the stated checkpoints. Later changes require their own applicable checks. Service Windows cleanup covers the direct conversion worker; it does not certify termination of all descendants.

## Remaining release gates

Close the final Press/Grove hosted checks, and bind the final heads, release pins, and receipts in the review packet. Keep all unresolved identity candidates and restricted components under their specific evidence and rights decisions.

Cloud transfer/worker scaffolding and existing Actions access do not establish production readiness. The dedicated production role, private storage access, network boundaries, and RDS review-versus-production execution still require explicit, recorded validation. No deployment, production data publication, PR merge, or canonical identity promotion is asserted by this status.

AWS work is paused at the owner's instruction. The original three supplied ZIPs and Giving release have verified cloud upload receipts; other transfers are incomplete, so local originals are retained. The existing Brian preview account was preserved. Permanent TBN sign-in still requires the provider configuration and plan mapping. The CloudFront router and authenticated Cedar transport are prepared locally; this report does not claim they are deployed.

The nine-part Native Infrastructure delivery was downloaded from the supplied Dropbox folder and rebuilt with the supplied SHA-256. Its workbook, rebuild and map archives are preserved outside Git. Full workbook key checks and source adjudication feed a separate Grove integration; none of its panels or facility records is added to the Press observation total. Editorial drafts and their authenticated delivery remain work in progress. Landing-page copy changes proposed during this continuation were reverted at the owner's direction.

These integration, validation, and cloud tasks remain engineering work. Havala can review the code and evidence; unresolved identity questions remain separately scoped adjudications.

## Reproduction and script consolidation

Use the [presentation data flow](PRESENTATION_DATA_FLOW.md), [dataset codebook](DATASET_CODEBOOK.md), and [consumer continuation](TERMINAL_HANDOFF.md) as maintained entry points. Historical instructions are preserved as archives. Legacy entity identifiers and internal relationship codes are hidden or given reviewed reader labels; automated tests and deployment checks remain enabled. Source values and their evidence hashes are preserved.

The earlier broad inventory contained 685 script entries: 162 active, 20 historical, and 503 needing review. Maintained top-level script entry points are now consolidated to 19 in Press and 16 in the producer; this does not mean either whole repository contains fewer than 20 files. Press uses `dump.mjs --kind` and `docs-markdown.mjs --kind` for the former six overlapping commands. Historical material still requires targeted review before retirement. The producer owns acquisition, immutable releases, identity evidence, and export; consumers own access and presentation.

## October 2 integration checkpoint and review ownership

This is a committed review checkpoint, not a production deployment. Havala (@Havala-Hanson) is proposed as integration and data-review lead. Ari (@ArihantSwainLumecon) can own the producer-to-consumer connection, release activation and backend verification. Francesca (@mafranagn) can own calculation definitions, pipeline contracts and the Engine/Cedar boundary. Kaylyn (@kaylynhl) can own signed-in product behavior, reader terminology and editorial presentation. These are proposed review lanes for Havala to coordinate, not accepted assignments.

The coordinated PRs are [producer 17](https://github.com/teim-team/Lumecon-data/pull/17), [Press 132](https://github.com/teim-team/cedar-press/pull/132), [Grove 181](https://github.com/teim-team/teim-app/pull/181), [Engine 25](https://github.com/teim-team/teim-engine/pull/25) and [Cedar 33](https://github.com/teim-team/cedar/pull/33). Keep them as normal review PRs; no agent merge is authorized by this checkpoint.

Native Infrastructure has a verified local immutable release: `d7a93b56a862dc19aeb6c059dfbbd913929e040c56db035fdd6a3cb9c26ab552`. Its private full-manifest SHA-256 is `da9333c981e7437f8715e040f4ffac385f93ec5c2cf3af9ff59714b989ebc5f3`; the consumer projection SHA-256 is `89db65d8e9b819bb098a043c2b1a3b87b4cc4a895c9e9335546ab71d2b08bf8c`. Consumer pins must use the latter. The research receipt SHA-256 is `b9ed628047479d1ef155756254cd55ce44a62da856e4c53a11f911ba9ff9b242`. Local evidence lives under `D:/cedar-convergence-20260926/review/phase2/native-infrastructure-20261002/`, including `release-review-20261002/infrastructure-release-receipt.json` and `research-infrastructure`.

The 28,484 permitted Records rows comprise 1,163 IHS, 22,380 TTPTIP, 2,467 SDWIS, 1,254 DWINSA and 1,220 NBI observations. There are 80,108 rows across 14 overlapping source views; that is not an additive observation headline. The other 13 components remain restricted. All 683 profile keys match the canonical identity register, and all 1,431 typed links resolve their record endpoints. Infrastructure remains Grove-only, alongside Gaming. Press still has 14 collections; the shared consumer has 16 targets. The internal fifteenth intelligence layer is not a public target or master download.

The source archives remain outside Git. Explicit six-field header mappings preserve original names and source bytes, rather than changing field values or silently normalizing every column. The map audit resolves all identifier joins but still holds three data-center coordinate differences. Missing or held coordinates are not invented. Full map serving and its visual QA remain open.

For local activation, preserve Gaming's release and manifest hashes, copy only verified immutable infrastructure release bytes into the store served by the existing producer API, rebuild the merged catalog, and update all pins to its new catalog digest. Preserve research receipt hashes and valid relative packet paths. Verify discovery, research packets, spreadsheets and downloads for both collections. This checkpoint does not claim that activation or deployment has happened.

Entity intelligence's typed core is implemented in producer commit `767800c7aaa82508af4f454ad08ae1fa4a21a5ff`. It is not yet the full profile and Ask Cedar experience. Remaining work includes profile integration, permission-consistent answer support, linked metrics and production operation. Original observations and subject roles remain authoritative; governments, enterprises and subsidiaries must not be collapsed.

An evidence-backed repair remains in Federal Funding: Siletz Tribal Arts & Heritage Society is a separate nonprofit, while two source transactions currently project to the tribal-government recipient. Use exact recipient UEI `GJV4PJ8M5PC7` and award `ASST_NON_1896753-42-22_417` to withhold or correct that projection, preserve the raw transactions, and rebuild the pinned release. Do not invent a new Cedar ID. Evidence: https://siletzartsheritagesociety.org/board-of-directors/ and https://www.usaspending.gov/award/ASST_NON_1896753-42-22_417 . This is a researched data repair, not an owner ambiguity.

AWS work remains paused. No deployment or cloud transfer is asserted here, and incomplete transfers do not authorize deleting local originals. Preserve the Brian Edwards preview account. Permanent TBN/Newspack sign-in still requires provider configuration and plan mapping; do not copy reader passwords or present it as connected. Article drafts use the authenticated API and stay unavailable when that service is unconfigured; no public body fallback is permitted.

Press additions: authenticated article list/detail endpoints, private cache headers, reader-safe evidence views and PDF citations, plus Infrastructure declarations, exact component contracts and access tests. Welcome and three research drafts are integrated at this checkpoint; later editorial additions require their own claim and renderer checks. Historical demo articles are excluded. The 700+ source figure is the owner's working count, not a newly audited inventory; October 2 is the page update date, not a fabricated source refresh. The final full API, generated artifact, frontend and browser checks are being recorded below. Connected article visual QA remains a separate verification step.

Final local Press source validation: 674 API tests passed with one Windows skip and 88% combined coverage; 630 frontend tests passed with one skip and coverage of 88.48% lines, 85.00% branches and 90.55% functions. ESLint, Ruff, generated artifacts and both dependency audits passed. The focused browser run passed 26 checks; its two initial desktop navigation timeouts passed on a separate targeted rerun. Public-build checks found no subscriber article paragraphs or private review files. These results do not assert a deployed connected article experience. No new editorial drafts from the resumed article lane were imported.
