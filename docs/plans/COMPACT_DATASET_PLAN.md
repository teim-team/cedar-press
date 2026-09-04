# Cedar Press Dataset — Tribal-State Gaming Compacts
*Standalone build plan, 2026-07-31. Merges into the Tribal Gaming Development & Markets dataset (docs/plans/GAMING_DATASET_PLAN.md) as its authorization/fiscal layer, but is built and versioned as its own product.*

## What this is
The complete record of Class III tribal-state gaming compacts and amendments: who may operate what, where, until when, and on what fiscal terms. Standalone value: the authorization and revenue-sharing history of Indian gaming. Merged value: the legal-economic layer that completes the gaming triangle (proposed / built / authorized).

## Sources
1. **BIA Office of Indian Gaming compact records** — the approval-event backbone. Every compact and amendment is either affirmatively approved by the Secretary or takes effect by operation of law when the Secretary does not act within 45 days ("deemed approved to the extent consistent with IGRA," 25 U.S.C. 2710(d)(8)(C)); both paths produce a **Federal Register notice** — dated, citable, comprehensive. FR search on the notice series is the census check against the BIA page.
2. **Compact and amendment texts** — from BIA where posted; state gaming agency / governor / legislature sites where not. Text availability will be uneven; record has_text as a field, never infer terms from secondary summaries without flagging.
3. **NIGC** — secondary confirmation, ordinances, and regulatory context.
4. **State payment reports** — the observation channel: states that publish tribal contribution / revenue-sharing payment figures (inventory to be built state-by-state; granularity ranges from annual statewide totals to facility-level figures). Payments-derived revenue estimates are always labeled as such.

## Schema (flat CSVs, AI-native layer)
- `compacts.csv`: compact_id, tribe (spine entity_id), state, original_effective_date, approval_type (secretarial / deemed-approved), FR citation, term_end, renewal_provisions, status (active / expired / renegotiated / litigation), successor_compact_id
- `compact_versions.csv`: version_id, compact_id, amendment_number, approval_date, FR citation, what_changed (scope / caps / sharing / term / other), has_text
- `compact_terms.csv`: version_id, term_type (machine_cap, game_scope, exclusivity, revenue_share_rate, revenue_share_base, tier_structure, local_share, dispute_provision), value, unit, applies_to (statewide / facility), source_page
- `state_payments.csv`: state, tribe/facility, period, amount, payment_type, source_report, derivable_revenue_flag
- `compact_events.csv`: forward calendar — expirations, renegotiation windows, arbitration/litigation events

## Extraction notes and caveats (publish these)
1. **Deemed-approved compacts carry a legal asterisk** — effective only "to the extent consistent with IGRA," and some terms in deemed-approved compacts have later been invalidated. approval_type is therefore a first-class field, not trivia.
2. **Revenue sharing is legally conditional** — lawful only in exchange for meaningful concessions (typically substantial exclusivity). This context belongs in the method note; it explains why terms vary so widely and why some compacts share nothing.
3. **Compacts are tribe-state instruments; facilities are sites.** The merge to the gaming dataset is one-to-many, and some compacts or amendments are facility-specific — applies_to handles this. Never propagate a facility-specific term tribewide.
4. **Amendment sprawl**: long-lived compacts accrete amendments across decades; the version table is the record, and "current terms" is always a computed view, never a stored fact.
5. Secretarial disapprovals and litigation (e.g., compacts struck in court) are events, not deletions — the same never-collapse-history discipline as everywhere else.
6. Text extraction of terms is the hard, valuable curation (CLAW work); the index layer (parties, dates, FR citations) is cheap and comes first.

## Merge plan into the gaming dataset
- **Keys**: tribe spine entity_id + state joins compacts to facilities; facility-specific terms join on facility where designated.
- **The closing analytical joins** (from the gaming plan, restated as merge outputs):
  - machine_cap (compact_terms) vs proposed machines (NEPA layer) vs built/current machines (directory) → cap-binding analysis
  - term_end / renegotiation windows (compact_events) → forward event list feeding the deals pipeline (renegotiations precede expansions/financings) and dataset 4's state-lobbying phase (negotiations = predictable lobbying spikes; two-part determinations already tie in via governor concurrence)
  - revenue_share terms + state_payments → payments-derived revenue estimates attached to facilities, clearly labeled, the closest public observable to Class III revenue
  - mitigation-agreements table (gaming plan Table 3) + local_share terms → the full picture of gaming's fiscal interface with non-tribal governments
- **Merge deliverable**: one joined analytical view per facility-year — authorized capacity, proposed capacity, built capacity, sharing terms in force, payments observed — with every cell traceable to its layer.

## Papers unlocked
- Compact renegotiation political economy: what predicts terms (market power, exclusivity value, lobbying activity from dataset 4, litigation posture)
- Revenue-sharing incidence and the price of exclusivity
- Cap-binding and capacity pressure as a predictor of renegotiation and expansion deals

## Phasing
1. **Index scrape** (same session-class as the gaming decisions table; do together): BIA compact list + FR notice sweep → compacts.csv and compact_versions.csv skeletons, joined to the spine.
2. **State payment-report inventory**: which states publish, at what granularity → state_payments.csv begins where data exists.
3. **Terms extraction pilot** (CLAW): a handful of major compacts spanning approval types and eras; validate compact_terms schema and the applies_to discipline.
4. **Backfill and forward calendar**: full terms extraction working from largest markets outward; compact_events populated; merge views shipped with the gaming dataset's Grove release.

Same rules as everywhere: zero fabrication, versions never collapsed, deemed-approved flagged, payments-derived estimates labeled, every term carrying source and page.
