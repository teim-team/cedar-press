# Native Influence Dataset — Build Plan
*Fourth leg of the stack. Drafted 2026-07-31, incorporating Dippel correspondence. Companion to AGENTS.md.*

## The core insight (Elijah's)
Economic impact studies are themselves lobbying instruments. Every TEIM-style multiplier analysis, every "tribes contribute $X to the state economy" report exists to move a legislator, an agency, or a compact negotiation. That means the influence dataset is not a side project — it closes the loop on everything else we build:

> deals → revenue → **lobbying** → contracts/grants/compacts → outcomes → impact studies → **lobbying** ...

It also means the customer for this dataset includes the lobby itself. The people best positioned to buy Native influence data are the entities and firms doing the influencing.

## What Dippel changes (May reply)
- He has **fully ingested and cleaned US + Canadian lobby data** with tribal/indigenous entities "pretty reliably identified in both." Do not take the identification on faith — the audit-first protocol below.
- His scraper captures **who each lobbying entity contacted** — his correction of the folk claim that filings only show "lobbying Congress." Read: the LD-2 government-entities-contacted field at scale (BIA, DOI, IHS, Treasury, OMB...), possibly more. Confirm exactly what the scraper yields before scoping analysis on it. Person-level meeting records still do not exist in LDA data; agency-level targets do.
- He is offering **data-for-coauthorship** with junior-friendly name ordering and limited time — meaning we drive scope.
- **Posture: nothing is asked of him.** His email is market intelligence, not a dependency. What it tells us: the product category exists, a senior academic with a lobbying-analytics firm values it enough to trade authorship for it, and his differentiator (contact-level scraping) is buildable from the same public filings. If he ever sends data unprompted, we audit it against our universe on our terms; otherwise the build is fully independent. Any co-authorship happens later, from strength, if it serves the dissertation or Lumecon.
- Canada parallels exist (First Nations development corps mirror the ANC structure, federal Registry of Lobbyists is public) — a future expansion we can also do without him.

## Entity model extension: intertribal & inter-Native organizations (new type: `I-`)
Collective vehicles do much of Indian Country's lobbying; without them the dataset undercounts influence and misattributes nothing to members. NEID already has a precedent (SGVF = self-governance consortia). Add an `I-` layer to Entity_Master:
- **National:** NCAI, NIGA, NAFOA, NCAIED, National Indian Health Board, NIEA, NAIHC, AFN (Alaska Federation of Natives), NHOA, ANCSA Regional Association, Native American Contractors Association (NACA — also a live Lumecon partnership target; note the dual relationship).
- **Regional:** USET, ATNI, ITCA, Great Plains Tribal Chairmen's Association, MAST, CRITFC, NWIFC, and peers.
- **Sector/purpose:** tribal health boards, self-governance consortia (link to existing SGVF NEIDs), gaming associations by state, tribal energy consortia.
- Attributes: member rosters (versioned — membership changes), whether the org files LDA itself, in-house vs hired lobbying, NEID/SGVF link where one exists.
- Analytic role: **indirect exposure** — a tribe that never files still lobbies through NCAI/NIGA dues and resolutions. Model membership as an exposure channel alongside direct filings.

## Counter-lobby layer: who lobbies against Native interests
Same LDA pull, opposite sign. The issue-code net (Indian/Native American Affairs + gaming) deliberately over-captures — the "false positives" are the point: non-Native clients filing on Native issues are the opposition and adjacency universe.
- **Stance classification** (the genuinely hard part): from specific-lobbying-issues free text + bill numbers + known positions. Categories: supporting, opposing, competing (e.g., commercial gaming vs compact expansion), regulatory-adjacent (banks, insurers on tribal jurisdiction), neutral/monitoring.
- Known opposition domains to seed the rulebook: commercial casino interests vs tribal gaming and compacts; sports-betting market fights; opponents of land-into-trust; ICWA challenge ecosystem; 8(a)/ANC contracting critics; jurisdiction and taxation fights.
- This is jurisprudence work again — stance rulings per client-issue pair, accumulated in the reconcile-queue loop, never one-shot classified. AI drafts, Elijah rules.
- Sensitivity note: it is all public LDA record, but a compiled "who opposes Native interests" product is politically potent. Frame outputs as issue-position tracking, keep the underlying rulings evidence-cited, follow LDA.gov citation requirements.

## Build phases
1. **LDA-native pull** (the path, no gates): free GET API (now LDA.gov), 1999→present. Three nets — issue-code (IND/GAM), name (corpus + aliases + subsidiary/DBA variants + FPDS names), affiliated-organizations field (LD-1's >$5K participants = free hierarchy signal). Hygiene: self-filers use registrant expenses not summed income; $3K/quarter de minimis means small entities need individual search; LD-203 contributions as a companion table.
2. **Entity resolution**: lobbying_client ↔ NEID crosswalk via the reconcile-queue loop; `I-` layer built alongside.
3. **Contact & stance enrichment**: agencies-contacted per activity (built from the LD-2 records directly); stance rulings for the counter-lobby layer.
4. **Link to outcomes**: filings joined to the contracting obligations panel, the deals ledger, and (dissertation tie-in) consultation-mandate outcomes. The paper: who lobbies in Indian Country, aimed where, and what it predicts in federal obligations.
5. **Phase 2**: state lobbying registries (compact politics lives here) — CA/WA/OK/AZ first, gaming-revenue ranked; Canada later.

## Schema sketch (flat CSVs, per the AI-native layer)
- `lobby_clients.csv`: client_id, name_as_filed, NEID/entity_id ruling, ownership_class (tribal / ANC / NHO / intertribal / individually-Native / non-Native), ruling_evidence
- `lobby_filings.csv`: filing_uuid, client_id, registrant, period, income_or_expenses, self_filed_flag
- `lobby_activities.csv`: filing_uuid, issue_code, specific_issues_text, bills_parsed, agencies_contacted
- `lobby_stances.csv`: client_id, issue_domain, stance_ruling, evidence
- `org_memberships.csv`: entity_id, I-org_id, years, source
- `lobby_contributions.csv`: LD-203

## Positioning: why this stack is a moat
Four datasets — **deals ledger, entity universe + identifier crosswalk, contracting outcomes panel, influence dataset** — each individually replicable in part, jointly not:
- The binding constraint everywhere is **entity resolution with sovereignty-literate judgment** (tribally-owned vs individually-owned, DBA collapse, family structures, recognition events). That is accumulated jurisprudence, not a model prompt. AI accelerates it; AI alone cannot produce it, because the rulings require domain authority and the errors are invisible to outsiders.
- Competitors rationally do **slices**: Dippel/LobbyIQ does lobbying; HigherGov does contracts; CICD does identifiers; nobody holds the joined stack plus the M&A event stream that makes attribution time-aware.
- The thesis: **specializing in data about Native economies** — the stack is simultaneously dissertation infrastructure, Lumecon/Cedar's substrate, and a subscription-grade product line whose most natural customers (advocates, associations, the lobby, agencies, journalists, researchers) are already named inside it.
- Collaboration posture that follows: partner on slices (Dippel gets the lobbying paper), never license the resolution machine; share derived matches and results, keep the rulings.

## What we build instead of asking
1. **Contacts:** our own agencies-contacted extraction from LD-2 activity records — same public field his scraper reads. Nobody's data has person-level meetings; agency-level targets are in the filings and ours to parse.
2. **Identification:** ours IS the standard — 815-entity universe, per-UEI jurisprudence, tribally-owned vs individually-owned rulings. His method is his problem.
3. **Coverage:** LD-203 and state registries on our roadmap (phase 2), Canadian Registry of Lobbyists public when we want it.
4. **Terms:** none pending. The stack stays whole; slices get partnered only when it serves us.

## Research pipeline (papers 6 and 7)
Portfolio context: four articles in the pipeline plus one future project. The influence dataset adds two more, sequenced deliberately:

**Paper 6 — descriptive flag-plant: "Who Lobbies in Indian Country?"**
First comprehensive account of Native lobbying, 1999-present: trends in spend and filer counts; direct vs collective (the I-org layer is the novelty — nobody has membership-adjusted exposure); in-house vs hired representation; issue mix and which agencies get contacted (the LD-2 field, at scale); spend scaled against gaming and contracting revenue from our own panels; and the counter-lobby composition on Native issues. Low identification risk, fast to write once the pull runs, and it publicly establishes the dataset - which is simultaneously the academic flag-plant and the Lumecon marketing artifact, since the paper's subjects are its readers. Descriptive papers on genuinely new data travel well (policy journals, Public Choice-adjacent, or the working-paper-to-flagship route).

**Paper 7 — the linkage paper: lobbying, contracts, deals, and federal funding.**
Does influence predict money? Outcomes are already on the shelf: the obligations panel (2000-2022), the assistance/funding panel (2009-2023, incoming), and the deals ledger. Design realities to state up front: reverse causality is the whole game (revenue funds lobbying), so the paper lives or dies on design, not data. Candidate strategies: tribe fixed effects with event studies around first registration and lobbying stops; representation shocks (lobbying-firm dissolutions or a tribe's lobbyist exiting) as plausibly exogenous loss of access; congressional committee turnover affecting a tribe's delegation; and the time-aware ownership ledger to keep attribution honest when entities change hands mid-panel. Deals as an outcome is the novel margin - does lobbying precede acquisition activity and land-into-trust wins, not just appropriations?

Sequencing logic: 6 before 7, because 6 debugs the data in public, accumulates the stance and resolution rulings 7 depends on, and generates the citations that make 7's data section one paragraph instead of twenty pages.
