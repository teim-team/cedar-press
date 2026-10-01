# Review status

Updated 2026-10-01. **Engineering and evidence review is in progress; this is not production release approval.**

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
| NEED | 143,353 | 27 |
| Native Nonprofits | 89 | 89 |
| Native-Owned Businesses | 3,725 | 3,725 |
| PLOT | 235,385 | 151,715 |
| Subcontracting | 70,054 | 70,054 |
| **Total** | **2,099,951** | **1,847,124** |

The original census contained 2,099,924 records. The current reconciliation adds 27 NEED reviewed-base records while preserving its 143,326 original internal records; count-preserving refreshes retain the other collection totals. Source-admission holds outside the assembled releases are not included in this table. Export permission does not imply deployment or production approval, and this inventory does not expand the existing Press storefront. Gaming's storefront exclusion remains unchanged.

## Evidence and identity limits

- **NEED:** 27 evidence-reviewed enterprise rows are permitted through the proof-bound public-base component. Of the 5,820 enterprise source rows, 5,793 were not identity-verified by this cohort review. Four unmatched candidate entries remain held separately. Internal patent, rating, relationship, and other restricted components retain their existing rights and holds; they are not made public by the 27-row exception.
- **Giving ↔ Nonprofits:** the recipient comparison covers 244 source records and 217 observations, producing **11 HOLD candidates and zero CONTESTED candidates**. Fourteen primary-source captures support six organization identity checks. The comparison preserves raw EIN formatting and dated address qualifications. No candidate was canonically promoted, and identity evidence does not establish a donation's correctness. The funder comparison produced zero candidates, which is not a negative identity finding.
- **NEED ↔ Subcontracting:** candidate processing was refused at the configured resource bound. No completed candidate result or no-match conclusion is claimed. Rerun only through a validated resource plan; do not bypass rights or memory guards.
- **Definitions:** 135 maintained reviewed definitions resolve the current preview fields, with zero unresolved definitions in that scope. This does not certify every historical source field.
- **Visual QA:** 45 source-table screenshots cover first, middle, and last sample panels across the 15 collections. The updated local Press desktop/phone review checks individual record names, qualified entity roles, monetary meanings and source columns. The final screenshot receipt is retained with the engineering review packet; it does not substitute for source verification. Neither screenshot set verifies all source facts or proves a deployed preview.

Use the [Native entities, relationships, and identifiers guide](https://github.com/teim-team/Lumecon-data/blob/bdb630841bc344872d79a444eadebcde61b21bb7/docs/native-entity-resolution.md) to distinguish governments, businesses, owners, certifiers, affiliations, and dated identifier evidence. A shared name, address, or owner identifier is not sufficient for a business identity merge.

## Code checkpoints

| Component | Reviewed checkpoint | Status |
| --- | --- | --- |
| Producer | `bdb630841bc344872d79a444eadebcde61b21bb7` · [PR 17](https://github.com/teim-team/Lumecon-data/pull/17) | Green reported gates: 2,861 tests; 93.45% coverage. |
| Economic engine | `009b981663c718a3c71de8aa8cbfd65160d2d5f0` · [PR 25](https://github.com/teim-team/teim-engine/pull/25) | Green reported gates: 1,256 tests; 90.74% coverage. |
| Cedar service | `42b07e3465c8dc4486121c03419af10655526bfb` · [PR 33](https://github.com/teim-team/cedar/pull/33) | CI green; 576 Linux service tests, 80.76% coverage, seven database tests separately, lock, lint, runtime audit, Docker build and Terraform Plan passed. Two optional Docling tests remain unexecuted. |
| Press | [PR 132](https://github.com/teim-team/cedar-press/pull/132) | 587 frontend tests passed, one skipped; 87.33% line coverage. Lint/build and generated files pass. The full browser run passed 260 checks with 36 device-specific skips; focused final presentation checks also passed. API verification ran 600 tests, 32 skipped, at 83% coverage. Hosted checks on the final head remain required. |
| Grove | [PR 181](https://github.com/teim-team/teim-app/pull/181) | 2,015 frontend tests passed (33 skipped, no TODOs); lint/build passed. Final consumer pins and Linux server verification remain open. |

Results apply to the stated checkpoints. Later changes require their own applicable checks. Service Windows cleanup covers the direct conversion worker; it does not certify termination of all descendants.

## Remaining release gates

Close the final Press/Grove hosted checks, and bind the final heads, release pins, and receipts in the review packet. Keep all unresolved identity candidates and restricted components under their specific evidence and rights decisions.

Cloud transfer/worker scaffolding and existing Actions access do not establish production readiness. The dedicated production role, private storage access, network boundaries, and RDS review-versus-production execution still require explicit, recorded validation. No deployment, production data publication, PR merge, or canonical identity promotion is asserted by this status.

These integration, validation, and cloud tasks remain engineering work. Havala can review the code and evidence; unresolved identity questions remain separately scoped adjudications.

## Reproduction and script consolidation

Use the [presentation data flow](PRESENTATION_DATA_FLOW.md), [dataset codebook](DATASET_CODEBOOK.md), and [consumer continuation](TERMINAL_HANDOFF.md) as maintained entry points. Historical instructions are preserved as archives. Legacy entity identifiers and internal relationship codes are hidden or given reviewed reader labels; automated tests and deployment checks remain enabled. Source values and their evidence hashes are preserved.

The script inventory contains 685 entries: 162 active, 20 historical, and 503 needing review. This is an inventory and targeted consolidation, not certification that every old script is safe or redundant. The producer owns acquisition, immutable releases, identity evidence, and export; consumers own access and presentation.
