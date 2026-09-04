# Cedar Press Dataset — Native Bills & Congressional Votes
*Build plan, 2026-07-31. Dataset 10. Status: MOSTLY BUILT — Elijah already holds the core dataset from prior research; this plan documents completion, not construction. Companion to AGENTS.md and docs/plans/INFLUENCE_DATASET_PLAN.md.*

## What this is
The legislative record of Indian Country: bills affecting tribes and Native entities — proposed and enacted — with roll-call votes, member positions, cosponsorships, and outcomes. It is the **outcomes leg of the influence chain**: dataset 4 records who lobbied and on what; this dataset records what the lobbying was aimed at and how the votes went.

## Status: already built (mostly)
Elijah constructed the core of this dataset for existing research on tribal lobbying influence. What exists: the Native-bill universe with vote records for at least one chamber (confirm: House in hand; Senate to verify — may already be captured). What remains is completion and productization, not a build:
1. **Chamber completion**: whichever side is missing. Congress.gov API (free key, GET) covers bills, actions, and cosponsors for both chambers; roll-calls come from the House Clerk XML and Senate.gov XML feeds. One-afternoon class of work.
2. **Spine linking**: bills tagged to affected tribes/entities where tribe-specific (many are general Indian-affairs bills — a bill_scope field distinguishes tribe-specific from general, same discipline as the FR dataset's tribe-specific vs broadly-applicable actions).
3. **Refresh pipeline**: current-Congress ingestion on the standing cadence.

## The research anchor (Elijah's existing paper)
The design that motivated the build: Democratic support for Native legislation is a relatively fixed baseline; tribal influence operates on the **Republican margin**. That makes member-level Republican votes on Native bills the outcome of interest, and it is exactly what the joined stack can now condition properly: which tribes were lobbying, spending how much, through which registrants, on which bills, in whose districts — with contracting revenue and gaming presence as the economic-stake covariates from datasets 2 and 7.

## Vote-count layer (the core tables)
- `native_bills.csv`: bill_id, congress, chamber, number, title, policy_area, bill_scope (tribe-specific / general), affected_entities (spine IDs where applicable), sponsor, introduced_date, latest_action, outcome (enacted / passed-one-chamber / died-in-committee / vetoed), companion_bill_id
- `bill_votes.csv`: vote_id, bill_id, chamber, date, question (passage / amendment / cloture / motion), result, yea, nay, present, not_voting, party_breakdown (D-yea, D-nay, R-yea, R-nay, I-yea, I-nay), margin, **republican_yea_share** (the paper's outcome, precomputed)
- `member_positions.csv`: vote_id, member (bioguide_id), party, state, district, position, cosponsor_flag — member-level, because the analysis lives here
- `bill_lobbying.csv` (the money join): bill_id ↔ LDA filing_uuid via bill numbers parsed from filings' specific-lobbying-issues text (already planned in dataset 4) — which clients lobbied which bills, with spend
- Derived: per-Congress indices — Native bills introduced/enacted, vote margins over time, cosponsorship networks, member-level Native-vote scorecards (the quotable layer; note scorecards are politically potent — same sensitivity posture as the counter-lobby layer: public record, evidence-cited, framed as position tracking)

## Joins across the stack
- **Lobbying (4)**: filing → bill → vote = the complete measured influence chain: who paid whom to lobby which bill and how the vote went. Almost no policy domain has this assembled; none has it for Indian Country.
- **Federal actions (FR dataset)**: the regulatory parallel — statutes here, rules there, together the full formal-policy record; enacted bills link forward to their implementing rules via authority citations.
- **Deals / contracting / gaming**: economic stakes as covariates (district-level tribal contracting revenue, gaming presence, compact events) — and enacted legislation as institutional treatments for the outcome panels.
- **Members ↔ districts ↔ tribes**: district overlays from the geography layer give each member a "tribal constituency" measure — the natural instrument-adjacent variation for the Republican-margin design.

## Caveats (publish these)
1. **"Native bill" is a ruled category, not a keyword hit** — committee referral (House Natural Resources / Senate Indian Affairs), policy-area tags, and text signals seed the net; edge cases (appropriations riders, general bills with tribal titles) go through the jurisprudence loop. Riders and provisions inside omnibus vehicles are the known undercount — record them as provisions where identified, state the gap.
2. **Most bills never get a roll-call**: voice votes, unanimous consent, and committee death dominate — the vote tables cover the votable subset; bill outcomes cover the universe. Never present roll-call analysis as the full legislative record.
3. Cosponsorship is cheap talk relative to votes; keep them separate signals.
4. Position scorecards inherit the counter-lobby sensitivity rules.

## Phasing
1. **Now**: inventory the existing build (chambers, Congresses covered, variable list); confirm the Senate gap; document provenance in the workbook's Source_Registry.
2. **Completion pass**: missing chamber + current Congress via the APIs; spine tagging; republican_yea_share computed.
3. **The money join**: runs automatically when dataset 4's bill-number parse ships.
4. **Product**: per-Congress indices and scorecards at the portal tier; member-level and joined tables in Grove; the existing research paper doubles as the method note and the flag-plant.

Same rules as everywhere: zero fabrication, ruled categories with evidence, voice-vote gap stated, provisions gap stated, sensitivity posture on scorecards.
