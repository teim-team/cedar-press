# Cedar Press Dataset — Federal Actions Affecting Tribal Nations
*Build plan, 2026-07-31. From the Federal Register memo, with integration and cross-verification notes from the full build session. Companion to AGENTS.md and the gaming, compact, nonprofit, and influence plans.*

## What this is
An event-level, tribe-linked longitudinal record of formal federal actions involving tribal nations and Native entities, built from the Federal Register: 1994 to present via the API, with pre-1994 backfill as a later phase. Each row is an **action, not a document** — reservation proclamations, ANCSA conveyances, compact approvals, acknowledgment milestones, consultations, rules, NEPA notices, liquor ordinances, recognition-list updates — with `related_action_id` linking documents into proceedings (consultation → proposed rule → final rule → correction → effective date as one connected record, not five strays).

The claim worth making plainly: this is the closest available thing to a **longitudinal event log of the formal federal-tribal relationship**, and turning legal publications into tribe-linked, research-ready events is the moat. The documents are free; the classification, entity linking, quantity extraction, and proceeding assembly are the product.

## Source posture (favorable, verified-adjacent)
- The FR API covers 1994+, requires no key, and is GET-based — **the LDA-class of source: runnable inside agent sessions**, unlike the POST-only and robots-walled channels that blocked other builds. Document metadata, full text, XML, official PDFs, agency, RIN, docket, CFR parts, comment deadlines, effective dates all exposed.
- Session-verified adjacency: today's BIA gaming-land scrape showed FR notices attached to essentially every decision — the FR stream and the BIA administrative record cross-reference each other natively.

## Why Elijah's cross-verification instinct is the headline
This dataset is not just additive — it is the **independent dating and event authority under the rest of the stack**:
- **Deals ledger**: land-into-trust, proclamations, conveyances, and compact events get authoritative FR dates — the date-basis discipline gains a canonical source, and FR events generate deal candidates the news layer misses.
- **Entity spine**: the annual recognized-tribes list *is* the FR product the BIA TLD mirrors — recognition events (Lumbee) and renames (Yuhaaviatam) arrive here first, making this the standing alias/status feed for Entity_Master. Module 11 (names, status, service areas, self-governance assumptions) is spine maintenance automated.
- **ANC layer**: the ANCSA conveyance stream names the same corporations already seeded — Sealaska, CIRI, BSNC, Doyon, and village corps down to Beaver Kwit'chin, which appears both in the 2024 FR record and in our village-corporation table. Conveyance events attach land histories to existing A-rows.
- **Gaming + compact datasets**: FR NOIs/NOAs are the NEPA discovery layer (already listed in that plan's hierarchy); compact-approval notices are the compact plan's approval-event backbone. This dataset is where both of those index scrapes live permanently.
- **Lobbying (dataset 4)**: rules, consultations, and land decisions are the *targets* of the lobbying the LDA data records — FR events supply the event timing for influence analysis.
- **Dissertation tie-ins**: the consultation module is the administrative record behind the ESSA consultation work; the acknowledgment module is the institutional companion to the termination/recognition chapter. The memo's "institutional treatments" framing is exactly right — this is the treatment-variable library for papers 6–7 and beyond.

## The modules (adopting the memo's structure and priorities)
**Tier 1 — commercial priority:**
1. **Tribal land & status actions**: reservation proclamations (tribe, acreage, county/state, authority, prior status — e.g., the 2,099-acre Fort Berthold addition), ANCSA conveyances (kept analytically separate from Lower-48 trust actions, per the memo — correct call), acknowledgment proceedings (petition-level timelines: petitioner, dates, findings, outcomes, years_in_process — genuinely original, especially with pre-1994 backfill), recognition-list and name/status updates, gaming-land and NEPA actions.
2. **Tribal regulatory environment**: compact approvals (merging into docs/plans/COMPACT_DATASET_PLAN.md), liquor ordinances (an underrated commercial-development indicator — ordinance activity clusters around casino/resort/retail buildout), and rules affecting taxation, contracting, housing, energy, health, self-governance — assembled as proceedings.
3. **Federal-tribal relationship index**: derivative measures over the action base — consultation frequency by agency and administration, regulatory attention by policy area, consultation-to-final-action lag, tribe-specific vs. general actions. Derivative, but the kind of thing agencies, associations, and journalists quote — the index is the marketing layer over the original database.

**Supporting modules**: consultations (component, not standalone product — the memo's judgment stands), irrigation rates (niche panel; collect cheaply, don't productize), grant solicitations (attach to dataset 3 as context, not a separate product).

## Schema (memo's, adopted)
`federal_actions.csv`: action_id, publication_date, effective_date, action_type (the memo's class list), document_stage, tribe_or_native_entity (**spine entity_id via the jurisprudence loop — the hard part, as always**), agency/subagency, title, summary, state, county, acreage, policy_area, legal_authority, CFR_parts, RIN, docket, comment_deadline, related_action_id, source_document_number, source_url, extracted_quantities, confidence. Plus per-module extension tables (proclamations with legal descriptions; acknowledgment petitions with the full timeline fields).

## Caveats (publish these)
1. **1994 API floor**: pre-1994 lives in scanned FR volumes (GovInfo) — acknowledge the seam; backfill acknowledgment and ANCSA histories as a dedicated later phase.
2. **FR ≠ the complete universe**: land can enter trust without a proclamation; not every federal-tribal interaction produces a notice. State what the log can and cannot see, same discipline as everywhere.
3. **Entity linking is the work**: notices name tribes inconsistently across eras and renames — the spine's alias history (fed by this very dataset) plus reconcile-queue rulings, never string-matching alone.
4. **Brief notices point elsewhere**: compact notices may not contain terms; NEPA notices point to documents — this dataset records the event authoritatively and links out; deep extraction belongs to the specialized plans.
5. Proceedings assembly (related_action_id) is judgment-laden for messy rulemakings — link conservatively, flag uncertain chains.

## Phasing
1. **API harvest + classifier v1**: pull the Indian Affairs / DOI recurring-notice categories plus keyword nets across agencies; classify into action types; entity-link through the spine; the recurring BIA categories (proclamations, compacts, liquor ordinances, acknowledgment, irrigation, NEPA notices) are self-labeling and go first.
2. **Proceedings assembly** on RIN/docket/citation chains; Tier-1 module tables shipped.
3. **Relationship index** computed and released as the public-facing layer; module data Grove-gated per the tier logic.
4. **Pre-1994 backfill** for acknowledgment and ANCSA (scanned-FR phase, priced as its own effort).

## Placement in the catalog
This joins the Q4 next-three candidate queue with a strong claim on a slot: it is the cheapest-to-start (free GET API, in-session runnable), the most cross-reinforcing (it maintains the spine and dates every other dataset), and the land/status module alone is a defensible product. Realistically it competes with gaming+compacts and nonprofits for the three slots — and note that choosing gaming+compacts effectively starts this one anyway, since their index layers are FR streams.

Same rules as everywhere: zero fabrication, actions not documents, proceedings linked conservatively, entity links ruled with evidence, gaps published.
