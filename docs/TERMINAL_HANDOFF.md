# Terminal handoff ? current Codex implementation checkpoint

*Rewritten in place, never appended to. Updated 2026-09-23.*

## Workspace and ownership

Codex worktree: <cedar-press checkout>, branch
codex/early-access-takeover, base b6abb374a7a40216a7648ef79fc1df9e5b471f79.
Dirty changes are intentional, uncommitted and unpushed. Scope is recorded in
`docs/ARCHITECTURE_DECISIONS.md`. Original Desktop/Cedar Press remains on
collections-coverage-audit at 49c846a4c39c5f2ec1995753ac17f1a9044bd466.
Six tracked edits and eight untracked files were preserved with checksums before
integration. Do not reset, clean, pull blindly, or write in the original worktree.

Lumecon Data: <lumecon-data checkout>, branch codex/cedar-press-pilot,
base 0ae36dda36d650b1b3861173fb122e7603b0dc3f. Foundation/hardening PRs are merged.
Python 3.13 environment installed with uv; no real collection transfer completed.

Checkpoint root: <checkpoint root>. It holds working-set,
NEED/owner/R7/publication/NAGPRA input receipts and independent candidate folders.
Machine baseline: 20 physical / 28 logical cores, about 16 GB RAM, only 3.2 GB
available initially. Run large transforms sequentially, DuckDB 512 MB / one thread.
Do not infer capacity from cores or launch multiple contracting-data copies at once.

## Active human review ? preserve it

Elijah is working at http://127.0.0.1:8765/cedar_review.html.
Do not regenerate that page, change its evidence or reorder its queue while active.
The loop uses `code/08_build_review_page.py` and `code/09_import_rulings.py`.
The field-level INTERNAL_ONLY ruling is now authorized in the policy and field map.
The active page remains a preserved historical batch, not clearance of its route.
It contains 18 affiliation exceptions; the other
85 populated cross-reference records are excluded from the human queue.
`review/OWNER_DECISION_QUEUE.md` contains the semantic explanation and scope.
Local review HTML/evidence are ignored artifacts, not committed production data.

Browser tests proved drafts do not resolve, reopening preserves decisions, Copy
and Download agree, revisions preserve history, stale evidence is refused, and
reimport is idempotent. Actual browser CSV also passed the Python receipt importer
twice with byte-identical second receipt. All were synthetic TEST REVIEWER cases;
no real owner decisions are recorded. `server/tests/test_need_review_import.py`
contains four regression tests. Receipts do not apply policy or publish data.

First safe continuation when a decision file arrives:

```
py -3 -B code/09_import_rulings.py --need-review <returned.csv> --queue review/need_existing_cedar_uid_evidence.json --receipt-ledger <isolated-receipt.json> --dry-run
```

Review the receipt, import unchanged valid explicit decisions without requesting
another approval, then implement their authorized effects with contract tests.
Do not feed these rulings into legacy identifier propagation. No publication yet.

## New owner systemic stop

The 2026-09-23 owner ruling in `docs/PUBLICATION_POLICY.md` now requires
source-attributed public affiliation, internal-only enterprise cross-references,
and an affirmative-evidence gate across collections. The 18-case review revealed
a systemic route problem, not completed adjudication. Audit full route populations,
preserve decisions, and hold NEED publication independently of the field disposition.
Do not regenerate a review until route negative controls and stratified evidence pass.
Confirmed defective token routes and evidence inflation are recorded in
`docs/NEED_BUILD_LOG.md`. Four routes touch 3,828 enterprise IDs / 3,911 observations;
all OWNERV6 touches 4,714 IDs / 4,901 observations. Exposure is not proof every link
is wrong. The checkpoint quarantine manifest preserves every affected key.
1133 refuses known automated routes; 1072 refuses legacy OWNERV6 staging before
writing outputs. Previously completed candidates remain migration proofs, not
affiliation-quality certificates. Their nine-stage success predates this new stop.
Two isolated pre-hold candidates had identical output hashes; the second used
about 699 MB peak summed process RSS and 20.3 seconds. No new queue generated.

## Completed implementation and remaining gates

| Work | Measured result | Next gate |
|---|---|---|
| NEED migration | Candidate-c ran all nine supported stages; 5,820 enterprises, 8,690 relations, 6,089 bindings including 269 historical-only, 367 dual-role rows; no minted IDs or changed inputs | Systemic affiliation hold; bounded patch review only, no promotion |
| NEED hub diagnostics | Fixed retired-handle comparisons, cross-hub sibling/duplicate grouping, stale enrichment; fixture tests pass | Candidate-c comparison review; immutable human review remains candidate-b |
| NEED measured correction | 1,096 rows change only five diagnostic fields; 216 parent-status changes; corroborated 255?399, contradicted 195?25, unresolved 423?449; duplicate-marked rows 404?144 | These are code-derived diagnostics, not new ownership approvals |
| NEED field | 103 populated rows / 99 own-entity CEs / 77 hubs; four relation patterns; all references active, no cross-reference changes in candidate-c | INTERNAL_ONLY owner ruling recorded in field map; independent NEED hold remains |
| Build orchestrator | Existing `code/build.py` now refuses empty/incomplete plans and owns isolated candidate command | Further collection producer consolidation and retirement not certified |
| NAGPRA export | `code/1137_customer_dataset_combine.py` plan now executes actual joins; blank keys cannot join; 19 publication tests pass | Seven undeclared joined fields still stop both plan and build; no export generated |
| Runtime metadata | All five were tracked; narrow ignore exceptions and tracking tests added | Clean Windows clone passed all seven generated checks, build, 58 JS / 43 Python tests; see `data/cedar/README.md` |
| R7 | Isolated active bundle f37240f77e40bf5e390219ae integrity PASS; 17,282 issued / 17,279 active CBs; 83 unresolved proposals; G03?G06 blocked | Format/policy and supported evidence decisions; no importer/promotion approved |
| Delivery | Current product still serves committed samples; no full entitled release path proved | Validated Lumecon release ? product/API/download; deployed access/storage verification |

Code fixes: `code/1072_tribally_owned_enterprises.py`,
`code/1102_need_corroboration_adjudication.py`, `code/1130_need_owner_v6_reconcile.py`,
`code/1177_retire_handle_column.py`; recovered tests are in the worktree.
1130 now verifies exact input-derived reconciliation instead of a fabricated
minimum for net-new candidates. Fixed run dates use CEDAR_RUN_DATE.

R7 policy and identity authority remain `docs/CEDAR_IDENTITY_SYSTEM_2026-09-13.md`
and `code/1188_import_chatgpt_r7_business_register.py`. Do not change the CB UI flag
`live: false` → `true` until an approved imported register and product integration
justify it. Issued CBs in an external package are not an imported subscriber register.
Current withholding rules in `code/cedar_domain.py` remain effective.

## Twelve-collection launch matrix

These are measured row/date baselines, NOT acceptance certificates. Source cutoffs
are unmeasured for every row; observation maxima are not retrieval/freshness proof.
Delivery is NOT TESTED for all twelve. All data readiness is NOT TESTED except
NEED/NAGPRA/Native-Owned, which are BLOCKED for the specific gates named above.
Full input hashes and date distributions live beside launch-measurements in the
checkpoint, not duplicated here. Last reproduced full pipeline: NEED candidate-c;
others not run (NAGPRA publication plan deliberately refuses).

| Collection | Rows | 2025 / 2026 by measured basis | Next blocker |
|---|---:|---|---|
| Funding | 701,955 | 43,254 / 18,325 action date | Source refresh, attribution and additive grain |
| Federal Register | 11,402 consultation rows | 8 / 6 notice date | Discovery coverage; broad documents are separate |
| Legislation | 3,069 | 207 / 55 introduced | Bill/action/vote scope and current refresh |
| Deals | 1,073 | 105 / 103 Event_Year; strict dates 99 / 102 | Fiscal/partial dates explain different denominators; validate sources |
| NAGPRA | 6,792 | 900 / 633 publication date | Seven joined fields need explicit existing-contract destinations |
| Advocacy | 27,825 | 1,377 / 672 filing_year | Reconcile earlier reported year basis before release |
| Prime Contracting | 1,217,768 | 47,599 / 55,014 action date | Refresh, identity and adjustment semantics |
| Subcontracting | 89,809 | 6,306 / 2,049 subaward date | Correct prime/subcontractor roles and repeated reports |
| Native-Owned | 4,273 | Current register, not annual | Approved publishable scope; R7 import blocked |
| Nonprofits | 12,764 | Organization snapshot, not annual | Inclusion evidence versus filings and CE attribution |
| Natural Resources | 11,305 | 505 / 280 period_start | Mixed period grains; 36 / 24 is payment_date subset; suppression |
| NEED | 5,820 | Current register, not annual | Active owner review; no export or promotion |

## Shared ID framework, initial implementation

`code/cedar_ids.py` extends the existing service with declared namespace/table/role
contracts and read-only validators. `code/503_identity.py` now refuses a CE checksum
payload under CB/LOB/other prefixes. `server/tests/test_id_contracts.py` covers
namespace, source/native separation, mapping, immutable bindings, duplicates and
derived views. NEED's existing verifier calls the shared service for enterprise
and affiliated CE IDs; actual 5,820-row structural verification passes.
This is an initial integration, not proof every legacy join or mint route complies.
Existing NEED hub/name-bound allocation remains a migration concern: do not mint
replacement IDs merely because an affiliation/name changes. No IDs were minted.

## Infrastructure is now the primary lane

See `docs/HAVALA_INFRASTRUCTURE_REVIEW.md` for the single architecture packet.
NEED survivor assessment is bounded; no new queue or promotion. Legislation bill
register is the provisional pilot, not a validated full collection. Protected
downloads currently return public samples; a pinned full-release adapter is missing.
D: has about 843 GiB free and is reported fixed SATA, not confirmed removable.
No data moved; AWS deployed state remains unverified without configured access.

## Supported checks and restrictions

`Makefile` is the shared CI gate authority; `.github/workflows/ci.yml` runs PR checks,
and `.github/workflows/deploy.yml` gates publication. Earlier no-PR-check prose is stale.
`docs/SHIPPING_RUNBOOK.md` retains historical chains; do not execute its old gaming
sequence as the twelve-collection launch command. `docs/PUBLIC_DATASET_SPEC_2026-09-05.md`
and `data/cedar/field_map.json` remain the publication contract.

Local coherent commits are authorized solely for a fixed Havala review range.
No pushes, production database changes, publishing, permanent deletion or
customer communications are authorized by this checkpoint. Shared identity and
publication remain single-writer. Preserve the active review while independent
work continues. Candidate success is not a release, fresh-clone success is not a
full-data rebuild, and no collection is certified ready by this handoff.
