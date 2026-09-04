# Cedar Press Dataset — Tribal Gaming Development & Markets
*Build plan, 2026-07-31. Companion to AGENTS.md, INFLUENCE_DATASET_PLAN.md, NONPROFIT_DATASET_PLAN.md. Incorporates the NEPA-documents memo and CLAW's independent source verification of the same date.*

## What this is
Two layers, one product. A **directory core**: the current universe of Indian gaming facilities (operator, class, machines/tables, hotel keys, sq ft) from NIGC, compacts, operator sites, and trade directories. And the differentiating **development layer**: the proposal-to-operation history of gaming projects reconstructed from federal environmental review documents (EAs, EISs, FONSIs, RODs) and BIA gaming-land decisions — what was proposed, at what scale, with what projected economics, what was approved, what got built, what failed, and what got reversed. Directories exist; the development layer exists nowhere. It converts "casinos and slot counts" into the capacity, investment, market, and infrastructure history of Indian gaming.

## Source verification (CLAW, 2026-07-31)
- **BIA Gaming Land Decisions database confirmed**: 138 records at bia.gov/as-ia/oig/gaming-land-decisions, faceted by decision status (Approved / Disapproved / Pending), eleven legal theories (Restored Lands, Two-Part Determination, Initial Reservation, Settlement of a Land Claim, etc.), tribe, and state; companion Pending list at /pending. Server-rendered Drupal HTML with an items-per-page=All option — **trivially scrapeable, and bia.gov permits automated fetch** (verified live). Every record links decision letters, RODs, FONSIs, EAs/FEISs as direct bia.gov PDFs, plus Federal Register notices carrying dates and legal history.
- **Failure and reversal tracking confirmed in the source**: disapprovals are in the list (e.g., Los Coyotes Barstow denial), and so is live volatility — Scotts Valley approved 01/10/25 with gaming eligibility temporarily rescinded 03/27/25; Koi Nation Shiloh with an April 2026 Federal Register reversal of the land acquisition. No directory product tracks failed or clawed-back projects; the status field does it for free.
- **Deals-ledger overlap confirmed**: Wilton, Scotts Valley, Redding, Soboba, Pascua Yaqui, Catawba and others in the decision list already have rows in the deals dataset. The decision records are the federal-action backbone behind deals we carry — joinable on day one.
- **BIA warns the list is not exhaustive.** It is the seed table, not the census.
- Document size reality: main documents are bounded (EA ≤ ~75 pp, EIS ≤ ~150 pp under current rules) but appendices and comment corpora are tonnage (Redding's ROD comment letters alone run to hundreds of MB across files). Extraction targets the EA/EIS, ROD, FONSI, and the economic/traffic/market appendices; comment corpora are skipped by default and flagged as available.

## Why NEPA documents are the moat (from the memo, confirmed)
The federal action (fee-to-trust, gaming eligibility, permits) triggers review; the review forces disclosure. A single EA (Osage Lake Ozark is the worked example) yields, in structured tables rather than promotional copy:
- **Facility specs**: total and gaming sq ft, machine and table counts, hotel keys, meeting space, F&B seats, parking, operating hours.
- **Operating assumptions**: daily patrons, occupied rooms — from which annualized visitation and implied occupancy are *calculated* fields (1,760 patrons/day → ~642,400 annual visits; 128/150 rooms → ~85% occupancy), always labeled calculated, never reported.
- **Modeled economics**: construction and stabilized jobs and wages by geography, first-year output — plus, in the impact-study appendix, the model used, geographies, substitution and local-capture assumptions. This is **competitor-methodology reconnaissance for Lumecon/TEIM**: every impact shop working tribal gaming, harvested project by project.
- **Market studies**: competitor identities, distances, revenues, projected cannibalization ($1.8M displacement from the nearest competitor in the Osage case), hotel-market displacement — close to a private feasibility study, in the public record.
- **Infrastructure demand**: water/wastewater gallons per day (consistently quantified because capacity must be evaluated), daily trip generation (~7,448 for Osage — a visitation proxy when machine counts are missing). Electricity loads are inconsistently disclosed; treat as sparse.
- **Intergovernmental economics**: property taxes removed by trust status ($56,840/yr for Osage), mitigation payments (the $50,000/yr sheriff agreement), fire/EMS/water/road commitments with dates and durations. A mitigation-agreements table is itself a novel dataset — how gaming developments financially interface with surrounding governments.
- **Named professionals**: architects, engineers, economists, traffic consultants — the tribal-gaming development-services ecosystem, mapped as a byproduct.

## Discovery hierarchy
1. BIA Gaming Land Decisions (+ Pending) — the seed
2. Individual BIA project pages and regional-office pages
3. EPA EIS database (EIS records since 1987, PDFs since Oct 2012; weak for EAs)
4. Federal Register NOIs/NOAs (also supply precise dates and legal posture)
5. Project-specific NEPA sites (e.g., the separately-posted Menominee Kenosha appendix set)
6. Directory core sources for the current-facility universe: NIGC, state compact records, operator sites, trade directories

## CLAW extraction design (adopting the memo's schema)
**Table 1 — facility-project record**, one row per development alternative: project_id, tribe (spine entity_id), facility_name, status, document/date, alternative, acres, gaming sq ft, total sq ft, machines, tables, hotel rooms, meeting sqft, restaurant seats, parking, hours, construction cost/start/duration, projected opening.

**Table 2 — projection/impact record**, one row per project × metric × geography × period: metric, value, unit, impact_type, geography, time_period, **reported_or_calculated**, source_document, page, table, confidence. Calculated fields (annualized visits, implied occupancy) always carry the derivation.

**Table 3 (addition) — mitigation & intergovernmental agreements**: project_id, counterparty government, service, amount, term, effective date, source.

**Stage tracking is the design, not a feature.** Every quantity carries observation_status in {proposed, approved, built, current} with dates for proposal, approval, construction, opening. A project proposed at 2,500 machines, opened at 1,500, expanded to 2,200 is three honest observations, not one misleading "slot count." Alternatives analyzed in the EA are preserved as alternative rows — the road not taken is data.

## Coverage caveats (publish these)
1. **Structural bias**: only projects requiring a federal action appear. On-reservation construction on existing trust land — most routine casino building — never enters this pipeline. The NEPA layer over-represents fee-to-trust, off-reservation, newly-acquired-land, and contested projects. The directory core carries the full universe; the development layer is deep where federal review reached.
2. BIA's list is non-exhaustive by its own statement; regional pages and the Federal Register net additional projects over time.
3. **Proposed ≠ built** — handled by stage tracking; never quote a proposal-stage number as a facility fact.
4. Modeled economics are the applicant's consultants' outputs, not observed outcomes. They are data *about projections* (and about modeling practice), and the dataset says so. Output figures are never gaming revenue.
5. Resource variables are inconsistent (water yes, electricity rarely); sparsity is recorded, not imputed.

## Integration payoffs
- **Deals ledger**: every gaming-land decision is a candidate deal event (approval, denial, reversal, trust acquisition), and construction milestones already in the ledger (Catawba, Coushatta, Jamul, Wind Creek) gain their federal paper trail. Reversals feed the "disputed" status discipline (Scotts Valley precedent already in the 2026 table).
- **Spine**: projects resolve to NEID/Entity_Master IDs; named consultants and developers extend the counterparty universe.
- **TEIM/Lumecon**: appendix impact studies = a library of competing models, assumptions, and multipliers for tribal gaming geographies — calibration evidence and competitive intelligence in one pass.
- **Lobbying (dataset 4)**: contested land decisions are lobbying magnets; decision dates give event timing for influence analysis. Two-part determinations requiring governor concurrence tie directly into the state-lobbying phase.
- **Papers**: the proposed-vs-built gap is a paper in itself (what predicts whether projects shrink, die, or get reversed — legal theory, opposition, market depth); projection accuracy of impact studies is a second (evaluating consultants' forecasts against realized outcomes — few datasets on earth can do this for any industry).

## Phasing
1. **Now (one session)**: scrape the 138-record index + Pending into a structured decisions table (tribe, state, legal theory, status, dates, document URLs); join to deals ledger and spine; log as a RUN entry. This is cheap and immediately useful regardless of what follows.
2. **Extraction pilot**: Osage Lake Ozark EA (clean single-document test), then Menominee Kenosha (stress test — large, separately-posted appendix set). Validate the three tables and the reported/calculated discipline.
3. **Backfill**: work the decision list oldest-to-newest through CLAW extraction; Federal Register sweep for projects missing from the BIA list.
4. **Directory core**: NIGC/compact/operator sweep for the current-facility universe; link development histories where they exist.
5. **Grove release** with the development-history layer as the premium tier; headline aggregates to the portal per the tier logic.

Same rules as everywhere: zero fabrication, reported vs calculated always labeled, stages never collapsed, gaps published, every figure carrying source, page, and table.

## Compact layer (added 2026-07-31, per Elijah)
The third layer, completing the triangle: NEPA documents = what was proposed; facility data = what was built; **compacts = what is legally authorized and on what fiscal terms.**
- **Source**: BIA Office of Indian Gaming approved-compact records. Every Class III compact and amendment requires Secretarial approval with a Federal Register notice — dated, citable approval events, same scrape posture as the decisions table (verify the compacts page fetches like the rest of bia.gov; expect yes). NIGC as secondary.
- **Extract per compact/amendment**: parties, approval and effective dates, term/expiration, renewal and renegotiation provisions, gaming scope (Class III games authorized), machine caps, exclusivity terms, revenue-sharing structure (rate, base, tiers), local-share provisions, dispute/renegotiation triggers. Amendments tracked as versioned rows — compacts have the same stage-history problem as facilities and get the same treatment.
- **Payment observation channel**: where sharing is a percentage of win, state-published tribal contribution / payment reports partially reveal Class III revenue — the closest public observable to gaming revenue in a non-disclosing industry. Build a state-by-state inventory of which states publish payments and at what granularity; ingest where available; label everything as payments-derived, never as reported revenue.
- **The closing joins**: compact machine caps vs EA-proposed counts vs built counts (does the cap bind? does capacity pressure precede renegotiation?); expiration calendar as a forward event list feeding the lobbying dataset (renegotiations = predictable state-lobbying spikes) and the deals pipeline (renegotiations precede expansions and financings); revenue-sharing terms as the fiscal-context layer under the mitigation-agreements table.
- **Papers unlocked**: compact renegotiation political economy (what predicts terms — market power, exclusivity value, lobbying); revenue-sharing incidence; and the cap-binding analysis above.
- **Phasing**: compact index scrape alongside Phase 1 (same session class); terms extraction rides the CLAW pilot; state payment-report inventory in the directory-core phase.
