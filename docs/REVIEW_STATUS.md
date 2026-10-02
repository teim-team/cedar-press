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
| Producer | `767800c7aaa82508af4f454ad08ae1fa4a21a5ff` · [PR 17](https://github.com/teim-team/Lumecon-data/pull/17) | Hosted run 36962650641 passed Python 3.12/3.13, PostgreSQL, both consumer contracts, safety, package and audit jobs. This is a historical checkpoint. Supplied-bundle adapters are now committed through f459445; its hosted suite passed 3,043 tests but coverage was 92.91%, below 93%. The following producer head 6806ed6 cleared the floor: hosted run 36977496163 passed all five jobs, and a local run with the api, db and cloud extras passed 3,073 tests at 93.14%. |
| Economic engine | `8ce67dcb448a26edb17102afb46e396ba916870c` · [PR 25](https://github.com/teim-team/teim-engine/pull/25) | Reported hosted run 36954632861: 1,271 database-enabled tests, 90.74% coverage. |
| Cedar service | `42b07e3465c8dc4486121c03419af10655526bfb` · [PR 33](https://github.com/teim-team/cedar/pull/33) | CI green; 576 Linux service tests, 80.76% coverage, seven database tests separately, lock, lint, runtime audit, Docker build and Terraform Plan passed. Two optional Docling tests remain unexecuted. |
| Press | [PR 132](https://github.com/teim-team/cedar-press/pull/132) | Hosted Checks run 36975162774 and Subscriber storage contracts run 36975162792 passed at 30e132e; hosted run 36977001720 (gates, gaming-release-consumer, postgres-contracts) passed at 3820085. The 674-test / 88% API figure was measured on Windows; on Linux (Python 3.12) the same suite reports 663 tests, OK with 34 skipped, 85% against the 77 floor, because the platform skips differ. Frontend 630 passed, 1 skipped, 88.48% lines / 85.00% branches / 90.55% functions, floors met. The browser smoke suite was not rerun on 2026-10-02 after the #149 merge; the hosted Checks run for the new head is the record for it. |
| Grove | [PR 181](https://github.com/teim-team/teim-app/pull/181) | Hosted run 36973458499 passed frontend, database-backed backend, Python Grove, examples, manifest, lint/build, audit and container checks. Its handoff-document check is being corrected. Runtime pins and Engine schema pin are committed, and the actual Infrastructure/Gaming connection passed locally. |

Results apply to the stated checkpoints. Later changes require their own applicable checks. Service Windows cleanup covers the direct conversion worker; it does not certify termination of all descendants.

## Remaining release gates

Close the final Press/Grove hosted checks, and bind the final heads, release pins, and receipts in the review packet. Keep all unresolved identity candidates and restricted components under their specific evidence and rights decisions.

Cloud transfer/worker scaffolding and existing Actions access do not establish production readiness. The dedicated production role, private storage access, network boundaries, and RDS review-versus-production execution still require explicit, recorded validation. No deployment, production data publication, PR merge, or canonical identity promotion is asserted by this status.

AWS work is paused at the owner's instruction. The original three supplied ZIPs and Giving release have verified cloud upload receipts; other transfers are incomplete, so local originals are retained. The existing Brian preview account was preserved. Permanent TBN sign-in still requires the provider configuration and plan mapping. The CloudFront router and authenticated Cedar transport are prepared locally; this report does not claim they are deployed.

The nine-part Native Infrastructure delivery was downloaded from the supplied Dropbox folder and rebuilt with the supplied SHA-256. Its workbook, rebuild and map archives are preserved outside Git. Full workbook key checks and source adjudication feed a separate Grove integration; none of its panels or facility records is added to the Press observation total. Existing article drafts have authenticated delivery implemented and tested; further editorial work is paused pending engineering review. Landing-page copy changes proposed during this continuation were reverted at the owner's direction.

These integration, validation, and cloud tasks remain engineering work. Havala can review the code and evidence; unresolved identity questions remain separately scoped adjudications.

## Reproduction and script consolidation

Use the [presentation data flow](PRESENTATION_DATA_FLOW.md), [dataset codebook](DATASET_CODEBOOK.md), and [consumer continuation](TERMINAL_HANDOFF.md) as maintained entry points. Historical instructions are preserved as archives. Legacy entity identifiers and internal relationship codes are hidden or given reviewed reader labels; automated tests and deployment checks remain enabled. Source values and their evidence hashes are preserved.

The earlier broad inventory contained 685 script entries: 162 active, 20 historical, and 503 needing review. Maintained top-level script entry points are now consolidated to 19 in Press and 16 in the producer; this does not mean either whole repository contains fewer than 20 files. Press uses `dump.mjs --kind` and `docs-markdown.mjs --kind` for the former six overlapping commands. Historical material still requires targeted review before retirement. The producer owns acquisition, immutable releases, identity evidence, and export; consumers own access and presentation.

## October 2 integration checkpoint and review ownership

This is a committed review checkpoint, not a production deployment. Havala (@Havala-Hanson) is proposed as integration and data-review lead. Ari (@ArihantSwainLumecon) can own the producer-to-consumer connection, release activation and backend verification. Francesca (@mafranagn) can own calculation definitions, pipeline contracts and the Engine/Cedar boundary. Kaylyn (@kaylynhl) can own signed-in product behavior, reader terminology and editorial presentation. These are proposed review lanes for Havala to coordinate, not accepted assignments.

The coordinated PRs are [producer 17](https://github.com/teim-team/Lumecon-data/pull/17), [Press 132](https://github.com/teim-team/cedar-press/pull/132), [Grove 181](https://github.com/teim-team/teim-app/pull/181), [Engine 25](https://github.com/teim-team/teim-engine/pull/25) and [Cedar 33](https://github.com/teim-team/cedar/pull/33). Keep them as normal review PRs; no agent merge is authorized by this checkpoint.

Native Infrastructure has a verified local immutable release: `d7a93b56a862dc19aeb6c059dfbbd913929e040c56db035fdd6a3cb9c26ab552`. Its private full-manifest SHA-256 is `da9333c981e7437f8715e040f4ffac385f93ec5c2cf3af9ff59714b989ebc5f3`; the consumer projection SHA-256 is `89db65d8e9b819bb098a043c2b1a3b87b4cc4a895c9e9335546ab71d2b08bf8c`. Consumer pins must use the latter. The research receipt SHA-256 is `b9ed628047479d1ef155756254cd55ce44a62da856e4c53a11f911ba9ff9b242`. Local evidence lives in the private review packet outside Git (phase 2, native-infrastructure, 2026-10-02), including the infrastructure release receipt and the research-infrastructure folder; the packet path is recorded in the private review index, not here.

The 28,484 permitted Records rows comprise 1,163 IHS, 22,380 TTPTIP, 2,467 SDWIS, 1,254 DWINSA and 1,220 NBI observations. There are 80,108 rows across 14 overlapping source views; that is not an additive observation headline. The other 13 components remain restricted. All 683 profile keys match the canonical identity register, and all 1,431 typed links resolve their record endpoints. Infrastructure remains Grove-only, alongside Gaming. Press still has 14 collections; the shared consumer has 16 targets. The internal fifteenth intelligence layer is not a public target or master download.

The source archives remain outside Git. Explicit six-field header mappings preserve original names and source bytes, rather than changing field values or silently normalizing every column. The map audit resolves all identifier joins but still holds three data-center coordinate differences. Missing or held coordinates are not invented. Full map serving and its visual QA remain open.

The combined local Infrastructure and Gaming store is assembled and its actual consumer-process rehearsal passed, as recorded below. Gaming's immutable release and manifest hashes are preserved. Production activation remains separate: use the verified catalog and consumer-projection hashes, preserve research receipt hashes and relative packet paths, and verify the deployed authenticated endpoints before publication.

Entity intelligence's typed core is implemented in producer commit `767800c7aaa82508af4f454ad08ae1fa4a21a5ff`. It is not yet the full profile and Ask Cedar experience. Remaining work includes profile integration, permission-consistent answer support, linked metrics and production operation. Original observations and subject roles remain authoritative; governments, enterprises and subsidiaries must not be collapsed.

An evidence-backed repair remains in Federal Funding: Siletz Tribal Arts & Heritage Society is a separate nonprofit, while two source transactions currently project to the tribal-government recipient. Use exact recipient UEI `GJV4PJ8M5PC7` and award `ASST_NON_1896753-42-22_417` to withhold or correct that projection, preserve the raw transactions, and rebuild the pinned release. Do not invent a new Cedar ID. Evidence: https://siletzartsheritagesociety.org/board-of-directors/ and https://www.usaspending.gov/award/ASST_NON_1896753-42-22_417 . This is a researched data repair, not an owner ambiguity.

AWS work remains paused. No deployment or cloud transfer is asserted here, and incomplete transfers do not authorize deleting local originals. Preserve the Brian Edwards preview account. Permanent TBN/Newspack sign-in still requires provider configuration and plan mapping; do not copy reader passwords or present it as connected. Article drafts use the authenticated API and stay unavailable when that service is unconfigured; no public body fallback is permitted.

Press additions: authenticated article list/detail endpoints, private cache headers, reader-safe evidence views and PDF citations, plus Infrastructure declarations, exact component contracts and access tests. Welcome and three research drafts are integrated at this checkpoint; later editorial additions require their own claim and renderer checks. Historical demo articles are excluded. The 700+ source figure is the owner's working count, not a newly audited inventory; October 2 is the page update date, not a fabricated source refresh. Final API, generated artifact, frontend and browser results are recorded below. Connected article visual QA remains a separate verification step.

Final local Press source validation: 674 API tests passed with one Windows skip and 88% combined coverage; 630 frontend tests passed with one skip and coverage of 88.48% lines, 85.00% branches and 90.55% functions. ESLint, Ruff, generated artifacts and both dependency audits passed. The focused browser run passed 26 checks; its two initial desktop navigation timeouts passed on a separate targeted rerun. Public-build checks found no subscriber article paragraphs or private review files. These results do not assert a deployed connected article experience. No new editorial drafts from the resumed article lane were imported.

### Branch state on 2026-10-02

PR 132 is 0 behind `main`. [PR 149](https://github.com/teim-team/cedar-press/pull/149) (Deals public preview refresh, one commit against `main`) is merged into this branch so either PR can land first; it stays open as its own review. Under this branch the served Deals preview is `public/data/cedar/samples/deals/spreadsheet__10.csv`, so PR 149's ten refreshed rows land in `server/tests/fixtures/legacy-preview/samples/deals/deals_classified__10.csv` and its source and method prose in the manifest and descriptors, not in the regenerated guide.

Branches with no PR, measured with `git cherry` against this branch: `codex/giving-plot-consumer-20260926` and `codex/legislation-release-consumer` are ancestors of this branch. `codex/press-closure-integration-20260926` and `claude/gaming-consumer-hardening` (PRs 130 and 124, closed 2026-09-29) each carry one commit not here, a rename-inventory re-measurement that this branch re-measured later (440 references) and whose portable path-leak tests are already here. `claude/cedar-press-team-accounts` carries one commit that this branch re-implemented as e241f81 and 53462bd on 2026-09-27. `claude/gaming-grove-consumer` carries 25 commits from 2026-09-24/25 whose work continued in `claude/gaming-consumer-hardening` and then here; its standalone scripts were consolidated into `dump.mjs --kind` and `docs-markdown.mjs --kind`. None of these branches has been deleted; deleting them is Havala's call.

No Codex, Copilot or CodeQL review thread exists on PR 132 or PR 149. Codex code review stopped at its usage limit on both, so neither PR has had an automated line review.

### Fact-check and research-readiness pass, 2026-10-02

Recorded in [FACT_CHECK_2026-10-02.md](FACT_CHECK_2026-10-02.md). All 14 served public previews (`public/data/cedar/samples/*/spreadsheet__10.csv`) match the producer's pinned `sample_sha256` in `data/cedar/verified-preview-releases.json` byte for byte, so no served CSV was edited; data defects found in them are queued for the producer with row keys and evidence. Corrected in this repository: `data/cedar/collection_descriptors.json` was a 2026-09-02 (`v0`) copy carrying the pre-rename lobbying name, superseded row labels and no entries for Foundation & Corporate Giving or PLOT, and now mirrors the manifest's 14 descriptors; the Deals `method` prose claimed the served preview was the ten events checked on October 1, 2026, which describes the regression fixture from PR 149 rather than the served producer rows, and now describes both; the generated guides carry a per-column blank meaning, a units and formats statement, measured preview facts and the citation in the download's own form; the public meta description no longer claims every record is resolved to a Native entity. Remaining unresolved items and their owners are in the handoff's review queue.

### Verified local Infrastructure and Gaming connection

The actual Grove Node process, pinned Press Python consumer and authenticated loopback producer passed the combined release rehearsal. Discovery includes both collections. Infrastructure returned all 28,484 permitted records (43,961,986 bytes) with SHA-256 `e8879bbb03510e3c1a75059e5a2a303ada948d521d01e9890c0a358e705fe382`; the selected Gaming component returned its unchanged 224 records. The Infrastructure research packet returned 20 bounded sample rows against its 28,484-row source component. Press-tier access, an invalid producer credential and use of rehearsal data in production were refused. Temporary download files were removed.

The tested runtime pair is Press `152dcd8847c2e90b3a4c9c1deeae9ed9ed24df76` and producer `f45944533f18448b4e74ffe18aa8ecd1f7d3bb2a`. The merged catalog SHA-256 is `ce8581e1c6bf220cc7a94caaab06958387739ecdc7f8db9dace97ca12e12e71c`. Local proof is retained in the private review packet outside Git (phase 2, grove-infrastructure-connected, 2026-10-02, process-verification receipt). The final receipt hash is c3a483f06e86fa0173a7ad6bde1de1b6d3b82ce482725fc3e41d9afcd33bda46.

This verifies the release-consumer process boundary, not account HTTP login, production activation or the full map interface. No persistent production configuration changed. Gaming research was not re-registered because no existing packet registration was selected. The Infrastructure preview currently carries zero map features; the previously recorded coordinate holds and full map-serving work remain explicit.

Hosted Press verification: both Checks (36975162774) and Subscriber storage contracts (36975162792) passed for commit 30e132e50104b4986869cba43de015b1784f5673. The last source change corrected the test to accept Cookie within a Vary token list that also contains Origin. No application access or cache policy was weakened.
