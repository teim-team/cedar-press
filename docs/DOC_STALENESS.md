# Document staleness — where prose disagrees with live data

*Generated 2026-09-01 by `code/527_doc_staleness.py`. Two lists, deliberately: a **LIVE** document is one a reader consults for current state, and a wrong number there misleads. A **RECORD** — a build log, a review packet, a dated measurement — was true when written, and its value is that it says what was believed then. Fix the first. Leave the second.*

## Live measurements

| fact | value |
|---|---:|
| aliases | 6,298 |
| assertions | 34,615 |
| collections | 13 |
| contract_violations | 0 |
| edges | 5,167 |
| entities | 1,555 |
| facts | 34,275 |
| ready | 2 |

## LIVE documents that are stale — 17

| document | line | stale | current |
|---|---:|---|---|
| `AGENTS.md` | 4593 | entity count | 1,555 |
| `docs/ASSERTION_LAYER.md` | 31 | entity count | 1,555 |
| `docs/ASSERTION_LAYER.md` | 252 | assertion count | 34,615 |
| `docs/ASSERTION_LAYER.md` | 275 | assertion count | 34,615 |
| `docs/ASSERTION_LAYER.md` | 668 | entity count | 1,555 |
| `docs/KNOWN_ISSUES.md` | 184 | prime_contracts duplicates | 0 - they were distinct FPDS transactions |
| `docs/KNOWN_ISSUES.md` | 206 | grain unstated | 25 |
| `docs/KNOWN_ISSUES.md` | 497 | prime_contracts duplicates | 0 - they were distinct FPDS transactions |
| `docs/KNOWN_ISSUES.md` | 641 | prime_contracts duplicates | 0 - they were distinct FPDS transactions |
| `docs/NATIVE_ENTITY_NUANCES.md` | 142 | entity count | 1,555 |
| `docs/NATIVE_ENTITY_NUANCES.md` | 318 | ownership edges | 5,167 |
| `docs/TWELVE_DATASET_PLAN.md` | 15 | entity count | 1,555 |
| `NEXT_SESSION.md` | 122 | entity count | 1,555 |
| `review/OWNER_DECISION_QUEUE.md` | 86 | prime_contracts duplicates | 0 - they were distinct FPDS transactions |
| `review/OWNER_DECISION_QUEUE.md` | 209 | prime_contracts duplicates | 0 - they were distinct FPDS transactions |
| `review/OWNER_DECISION_QUEUE.md` | 274 | ownership edges | 5,167 |
| `START_HERE.md` | 531 | assertion count | 34,615 |

## RECORD documents carrying superseded numbers — 31 (informational, do not 'fix')

- `dist/02o_fpds_uei_edges/fpds_uei_edges.NOTES.md` L5 — ownership edges
- `dist/04x_admin_appeal_parties/admin_appeal_parties.NOTES.md` L56 — entity count
- `dist/manifests/VALIDATION.md` L127 — ownership edges
- `dist/SANITY_CHECKS.md` L27 — entity count
- `dist/SANITY_CHECKS.md` L33 — ownership edges
- `docs/ALIAS_RELATIONSHIP_MIGRATION_LOG.md` L47 — ownership edges
- `docs/ARCHITECTURE.md` L253 — ownership edges
- `docs/ARCHITECTURE_DECISIONS.md` L473 — grain unstated
- `docs/DATASET_SCAFFOLD.md` L19 — entity count
- `docs/datasets/federal-register.md` L195 — entity count
- `docs/ENTITY_INVENTORY.md` L5 — entity count
- `docs/EXTERNAL_REVIEW_PACKET.md` L59 — entity count
- `docs/EXTERNAL_REVIEW_PACKET.md` L235 — entity count
- `docs/EXTERNAL_REVIEW_PACKET_R2.md` L43 — entity count
- `docs/EXTERNAL_REVIEW_PACKET_R2.md` L240 — assertion count
- `docs/EXTERNAL_REVIEW_PACKET_R2.md` L259 — prime_contracts duplicates
- `docs/EXTERNAL_REVIEW_RESPONSE.md` L40 — entity count
- `docs/FACT_CHECK_2026-08-06.md` L368 — ownership edges
- `docs/FOUNDATION_AUDIT.md` L44 — repo status
- `docs/FOUNDATION_AUDIT.md` L196 — assertion count
- `docs/HANDOFF.md` L409 — entity count
- `docs/RELEASE_REPLAY_LOG.md` L1123 — assertion count
- `docs/RESOLUTION_RULES_LEARNED.md` L112 — entity count
- `docs/RESOLUTION_RULES_LEARNED.md` L150 — entity count
- `docs/RESOLUTION_RULES_LEARNED.md` L199 — ownership edges
- `docs/RESOLUTION_RULES_LEARNED.md` L497 — entity count
- `docs/SPIDERWEB_LEARNING_PLAN.md` L203 — ownership edges
- `docs/TEMPORAL_MODEL.md` L67 — assertion count
- `docs/TEMPORAL_MODEL.md` L121 — assertion count
- `docs/UNSHIPPED_TABLE_TRIAGE.md` L51 — ownership edges
- `review/identity_layer_audit_2026-08-26.md` L96 — ownership edges