# Cedar Press Dataset 6 — Native Nonprofit & Philanthropic Economy
*Build plan, fleshed out 2026-07-31. Companion to AGENTS.md and docs/plans/INFLUENCE_DATASET_PLAN.md. Extends the draft proposal with identification methodology, coverage caveats, mechanics, and integration with the existing spine.*

## What this is
A longitudinal dataset of Native-controlled, tribally affiliated, and Native-serving nonprofit organizations and the philanthropic capital flowing into Indian Country, built from IRS public tax records and linked into the Cedar Press entity graph. Standalone research product plus modeling substrate: it fills the nonprofit sector gap in Lumecon's I-O work and adds EIN — the one identifier the stack currently lacks — to the spine.

## Correction to the draft before anything else
The draft's closing "enhancement" proposes minting a permanent internal Cedar Entity ID. **Do not mint a new ID system — it already exists.** The spine is NEID (CICD connector) plus the Entity_Master ID series, with the crosswalk carrying CAGE/UEI/DUNS. This dataset's job is to add **EIN** as a new identifier column on existing canonical entities and to add new N-series (nonprofit) entities where no record exists. One spine, more identifiers per entity — never parallel ID systems. The entity graph the draft imagines is the spine plus the ownership-change ledger we already maintain.

## Identification methodology (the hard part, as always)
No single field in IRS data says "Native." Identification is a multi-net capture followed by jurisprudence rulings, same architecture as everything else in the stack:

**Net 1 — Name match:** BMF and 990 filer names against the Entity_Master corpus, aliases, and the naming rulebook. Distinctive Native-language names are high-precision (the ANC/NHO lesson holds: Nakupuna, Ukpeaġvik, Alakaʻina resolve themselves); English names are the trap ("Cherokee" orgs, "Indian" missions run by non-Native churches). Rulings accumulate per EIN.

**Net 2 — Geography:** filer addresses geocoded against Lumecon's 491 tribal-area geographies. The draft misses this entirely, and it's a differentiator nobody else has operationalized: an org headquartered on or adjacent to a reservation is a strong candidate, and the same layer later powers "philanthropic deserts" analysis. Weak alone (border-town non-Native orgs), strong combined.

**Net 3 — Roster seeding:** known-population lists imported as pre-ruled members: Native CDFI Network membership (note: an existing TBN/StoryLab client — warm channel), Native Americans in Philanthropy, First Nations Development Institute grantee history, AIHEC tribal colleges, NCUIH urban Indian orgs, IHS Urban Indian Organization list, NB3-type sector orgs, the I-layer intertribal orgs (most are 990 filers themselves — NCAI, NIGA, NAFOA, USET all have EINs and now get their financials attached).

**Net 4 — Relationship traversal:** Schedule R related-organization names walked against the spine (a nonprofit listing a tribe or tribal enterprise as related is near-conclusive); Schedule I grant recipients of already-identified Native funders; officers/directors shared with known entities (supporting signal only, never dispositive — individual Native leadership ≠ Native-controlled org, the individually-owned vs tribally-owned distinction transposed to the nonprofit world).

**Net 5 — Federal-award backfill:** EINs appear in assistance records; recipients already identified as Native in the funding dataset carry their ruling over, and their EIN unlocks the 990 history. This is the reinforcement loop working in reverse.

**Classification taxonomy (ruled per entity, with evidence):**
- *Tribally controlled* — instrumentality, tribally chartered, or tribe-appointed board
- *Native-controlled* — majority Native board/leadership, independent of any tribe
- *Native-serving* — mission targets Native populations, control status separate
- *Native-founded / legacy* — historical affiliation, current control unclear (park, don't guess)
- NTEE codes are recorded but treated as weak signal only — the taxonomy does not reliably distinguish Native organizations, and any claim that it does should be tested, not assumed.

## Coverage caveats that make the dataset honest (publish these)
1. **Tribal instrumentalities largely don't file 990s.** Entities under tribal governments (IRC §7871 treatment) are typically outside the 990 universe entirely — meaning the *biggest* "nonprofit-like" tribal institutions can be invisible in IRS data. The dataset must say what it cannot see, and the tribal-government side of the ledger lives in datasets 2–3, not here. Getting this boundary right is exactly the sovereignty-literate judgment competitors lack.
2. **990-N postcard filers (<$50K revenue) yield almost no data** — name, EIN, existence, nothing financial. A large share of grassroots Native orgs live here. Tier the dataset openly: full-990 tier (rich), 990-EZ tier (partial), 990-N tier (existence only).
3. **Fiscal sponsorship hides organizations.** Many Native projects operate under non-Native fiscal sponsors and never hold an EIN. Track known sponsored projects as a candidate list; do not pretend the EIN universe is the org universe.
4. **Churches and certain religious orgs are exempt from filing** — relevant for Native ministries and some longstanding mission-adjacent institutions.
5. **Filing lag** is one to two years; the "current year" in this dataset is always trailing. State the vintage on every table, per house rules.

## Mechanics
- **Sources:** IRS 990 e-file XML corpus (bulk, covers most filers from the e-file mandate era; earlier years thinner), Exempt Organizations BMF (monthly snapshots — keep vintages, orgs vanish on revocation), 990-PF for foundations, Schedules I/R/J/O parsed to their own tables. ProPublica's Nonprofit Explorer API as the fast lookup/QC layer during resolution.
- **Both directions of money:** grants *into* Native orgs (mainstream philanthropy's Schedule I lines matched against the Native EIN set — this is how you reproduce and then continuously update the chronically-cited underfunding statistics with your own numbers) and grants *out of* Native funders (Native foundations, ANC foundations — note the two ANC-affiliated foundations already sighted in the ANCSA directory work, tribal community foundations).
- **Flat CSV schema per the AI-native layer:** `np_orgs` (EIN, spine entity_id, classification ruling + evidence, tiers), `np_financials` (EIN-year panel), `np_grants` (funder EIN → recipient, amount, purpose, year), `np_people` (officers/comp), `np_related` (Schedule R edges), all joining the existing reconcile-queue loop for ambiguous rulings.

## Integration payoffs (why this is dataset 6 and not a side quest)
- **EIN joins the spine** → every entity can now be tracked across contracts (UEI/CAGE), assistance (UEI/EIN), lobbying (name→ruling), deals (event stream), and tax filings (EIN). That's the unified graph, achieved by extension rather than reinvention.
- **Lobbying cross-check:** 990s disclose lobbying expenditures — an independent measurement of dataset 4's coverage, and a way to catch influence spending that never hit an LDA filing.
- **Deals enrichment:** nonprofit acquisitions, mergers, and asset transfers surface in 990s years before anyone reports them; Schedule O narratives are an underused deal-discovery channel.
- **TEIM/modeling:** nonprofit payroll and program spending by geography plugs the nonprofit sector into regional models with real numbers instead of national ratios — the compounding effect the draft correctly names, now with a concrete mechanism.

## Products and papers
- **Grove-first debut** per the tier logic: full dataset in Cedar Grove; headline aggregates and the annual "Native Nonprofit Economy" brief at the portal tier; executive-compensation detail stays Grove-only (public record, but detail-tier appropriate).
- **Paper candidate (descriptive flag-plant, same pattern as the lobbying trends paper):** the size, composition, funding mix, and geography of the Native nonprofit economy — first comprehensive account, and its likeliest institutional buyers (foundations) are also Grove's natural license customers. NAP and First Nations are partnership channels, not competitors: they publish advocacy research on this; you'd be publishing the maintained infrastructure under it.
- The draft's research questions all stand; add the two the linkages make unique: how nonprofit funding co-moves with federal awards to the same entities, and whether philanthropic flows respond to the deal/lobbying activity the rest of the stack observes.

## Phasing
1. **Q4 slot (per the Year One roadmap's "next three" decision):** BMF pull + Nets 1/3/5 → candidate universe with tier labels; first reconcile-queue cycles.
2. **+1 quarter:** 990 XML financial panel for ruled entities; Schedule I flows both directions; the underfunding benchmark reproduced with stated method.
3. **+2 quarters:** Schedules R/J/O parsed; geography net run; entity-graph edges shipped; Grove release with the descriptive brief.

Same rules as everywhere: zero fabrication, rulings with evidence, tiers and gaps published, vintages on every table.
