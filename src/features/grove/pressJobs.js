/**
 * REVIEW OWNER: Havala
 *
 * What people use Cedar Press for, and what each collection can answer: the
 * two shared layers every surface reads (owner's brief, 2026-09-26, second
 * pass, "Architecture").
 *
 *   COLLECTION_JOBS  per collection: the questions its fields can answer
 *                    (collection profile), and the questions Cedar can answer
 *                    about it (Cedar's suggested questions)
 *   AUDIENCE_JOBS    per use case: audience, job, outcome, explanation (the
 *                    brief's "intelligence"), evidence (the collections, as catalog
 *                    ids), an image pool, and where one exists, a
 *                    research-access example
 *   JOBS             the shared vocabulary of jobs a use case is for
 *   QUESTION_KINDS   Describe, Compare, Trace: every question carries one
 *   ENTITY_JOBS      the entity page's line and the actions that work today
 *
 * Surfaces that read them: the door's use-case band
 * (`PressAudienceExample.jsx`), the collection profile
 * (`PressCollectionAbout.jsx`), Cedar's suggested questions
 * (`readerCedar.js`, `CedarPress.jsx`), the entity page
 * (`CedarPressEntity.jsx`) and Research access
 * (`CedarPressResearchAccess.jsx`). None of them types a question, outcome or
 * example of its own: `pressJobs.test.js` fails if a page hard-codes a string
 * this file owns. Collections are named by catalog id only, so names and
 * marks come from `pressCatalog.js`, the same discipline as the catalog.
 *
 * EVERY QUESTION HAS TO BE ANSWERABLE TODAY
 * Two different promises, held by two different tests:
 *
 *   questions  a subscriber can answer it from the collection's own fields.
 *              Each names the codebook columns it rests on (`fields`), and
 *              the node suite fails if a column is not in that collection's
 *              codebook table.
 *   cedar      Cedar can answer it from what it can actually read. For Cedar
 *              Press that is the collection's release profile
 *              (`server/cedar_press/collection_profiles.answer_from_profile`):
 *              what a collection holds, how it is built and resolved, and
 *              what its latest release changed. It cannot read records, so
 *              "which programs appear most often among these organizations"
 *              is not a question it can answer, however useful. Each
 *              question names the branch it must land in (`kind`), and the
 *              Python suite runs every one through the router and fails on a
 *              refusal or a different branch. That matters because the
 *              router matches words: "what changed in this organization's
 *              structure" lands on the release notes, a confident answer to
 *              a question nobody asked.
 *
 * ONE SENTENCE PER AUDIENCE: THE OWNER'S
 * Every audience carries the owner's intelligence sentence and the
 * collections it names. All fourteen collections are on the shelf (owner,
 * 2026-09-27), so every sentence the owner wrote is the one the page shows;
 * an audience is hidden only when a collection it names is not in the catalog
 * it is resolved against, or when it names fewer than `MIN_COLLECTIONS`.
 *
 * TWO COLLECTIONS ARE PRESENTED BY THEIR RECORD STRUCTURE
 * Foundation & Corporate Giving and PLOT are live on their shelves with no
 * release file in this repository (`coverage: STRUCTURE`). Their profile
 * questions are held to the producer's declared fields where a producer
 * exists, and they carry no Cedar questions: Cedar's suggested questions are
 * routed through a release profile, and neither has one. See
 * `COLLECTION_JOBS` below.
 *
 * COVERAGE IS A REVIEW CHECK, NOT A RULE (owner, 2026-09-26: "The landing
 * page should show the best reasons to use Cedar Press, not prove that each
 * dataset got a turn"). `uncoveredIds` reports any live collection no shown
 * use case cites; the node suite prints that report and docs/DESIGN_SYSTEM.md
 * lists it, and nothing fails on it. Chips are the collections a sentence
 * actually names, never one added so a collection gets a turn.
 *
 * HOUSE STYLE: "and", never an ampersand, in every string here; the smoke
 * suite reads the rendered page.
 */
import { STOREFRONT_CATALOG } from "./pressCatalog.js";

/** The ids a page may resolve: the storefront's, and nothing else. */
export function liveIdsOf(catalog = STOREFRONT_CATALOG) {
  return new Set(catalog.map((entry) => entry.id));
}

/** A live catalog entry by id, or null. Only ever reads the catalog it is handed. */
export function liveCollection(id, catalog = STOREFRONT_CATALOG) {
  return catalog.find((entry) => entry.id === id) ?? null;
}

/** Fewer than this and the example does not show collections combining. */
export const MIN_COLLECTIONS = 3;

/**
 * What a question asks of the data (owner, 2026-09-26). Every collection
 * question and every Cedar suggestion carries one, and each collection aims
 * for a mix where its fields allow.
 */
export const QUESTION_KINDS = Object.freeze({
  describe: "Describe",
  compare: "Compare",
  trace: "Trace",
});

/**
 * The jobs a use case can be for: one shared vocabulary, so the same job
 * reads the same wherever it appears and can be reused across audiences and
 * surfaces (owner, 2026-09-26).
 */
export const JOBS = Object.freeze([
  "Competitive intelligence",
  "Due diligence",
  "Competitive funding",
  "Peer benchmarking",
  "Economic development",
  "Market entry",
  "Investment opportunity",
  "Partner discovery",
  "Research",
  "Journalism",
  "Policy monitoring",
  // The owner's own wording for consultants and advisors (2026-09-27).
  "Client strategy",
  // Government and public agency officials (owner, 2026-09-27).
  "Tribal consultation",
]);

// ── COLLECTION_JOBS ───────────────────────────────────────────────────────
//
// `questions`: two or three per collection, in the register of the owner's
// examples. The owner's own examples are kept verbatim where the fields
// answer them (Federal Funding, Deals, Cedar NEED, Native Nonprofits).
//
// Each carries its `kind` (Describe, Compare, Trace) and the codebook
// `fields` it rests on.
//
// `cedar`: what Cedar can answer about the collection. Each names the profile
// branch it must land in (`route`: "content", what the collection holds;
// "construct", how it is built and how a record reaches its entity), and its
// kind: a content question describes, a construct question traces. The
// shared release question below compares one release with the last, and
// `cedarQuestions` adds it to every collection's list.

const { describe, compare, trace } = QUESTION_KINDS;
const q = (kind, text, fields) => Object.freeze({ q: text, kind, fields: Object.freeze(fields) });
const ask = (kind, text, route) => Object.freeze({ q: text, kind, route });

/** Cedar's release question, the same for every collection. */
export const CEDAR_CHANGES_QUESTION = Object.freeze({
  q: "What changed since I last used this collection?",
  kind: compare,
  route: "changes",
});

export const COLLECTION_JOBS = Object.freeze({
  funding: Object.freeze({
    questions: Object.freeze([
      // The owner's "organizations like this one", made exact: "like" is
      // the register's entity type, not a similarity measure Cedar lacks.
      q(describe, "Which federal programs are supporting organizations of the same type as this one?", ["program_name", "entity_class", "canonical_name"]),
      q(compare, "How has reported federal assistance changed over time?", ["fiscal_year", "obligations_usd", "fy_partial_flag"]),
      q(compare, "Which agencies are most active among a set of peer organizations?", ["awarding_agency", "canonical_name"]),
    ]),
    cedar: Object.freeze([
      ask(describe, "What does this collection let me compare across peer organizations?", "content"),
      ask(trace, "How are awards to subsidiaries and housing authorities credited to their Nation?", "construct"),
    ]),
  }),
  "federal-register": Object.freeze({
    questions: Object.freeze([
      q(describe, "Which agencies are opening consultations with tribes, and on what topics?", ["agency", "topic", "activity_type"]),
      q(compare, "How has consultation activity changed over time?", ["notice_date", "agency"]),
      q(trace, "Which Federal Register document does a consultation come from?", ["fr_document_number", "federal_register_citation", "consultation_participants__source_url", "federal_actions__source_url", "html_url"]),
    ]),
    cedar: Object.freeze([
      ask(describe, "What does this collection let me follow across agencies?", "content"),
      ask(trace, "How are notices matched to the tribes they name?", "construct"),
    ]),
  }),
  legislation: Object.freeze({
    questions: Object.freeze([
      q(describe, "Which bills concerning a Nation have moved past introduction?", ["canonical_names", "outcome", "latest_action"]),
      q(compare, "Which policy areas draw the most legislation concerning Indian Country?", ["policy_area"]),
      q(trace, "Who sponsors legislation affecting a set of Nations?", ["sponsor_name", "canonical_names"]),
    ]),
    cedar: Object.freeze([
      ask(describe, "What does this collection let me follow on a bill?", "content"),
      ask(trace, "How are bills tied to the tribes they affect?", "construct"),
    ]),
  }),
  deals: Object.freeze({
    questions: Object.freeze([
      q(describe, "What kinds of major transactions are peer organizations announcing?", ["deal_type", "entity_class"]),
      q(trace, "Which organizations or counterparties appear repeatedly?", ["canonical_name", "counterparty_or_funder"]),
      q(compare, "Where is acquisition or financing activity increasing?", ["deal_type", "state", "event_year"]),
    ]),
    cedar: Object.freeze([
      ask(describe, "What does this collection track about each transaction?", "content"),
      ask(trace, "How are buyers, sellers and borrowers tied to the Native entity behind them?", "construct"),
    ]),
  }),
  nagpra: Object.freeze({
    questions: Object.freeze([
      q(trace, "Which institutions have published notices naming a Nation?", ["institution_name", "canonical_names"]),
      q(describe, "What kinds of notices has an institution published, and when?", ["notice_type", "publication_date", "institution_name"]),
      q(describe, "Which removal locations do the notices record?", ["removal_states", "removal_counties"]),
    ]),
    cedar: Object.freeze([
      ask(describe, "What does this collection hold about each notice?", "content"),
      ask(trace, "How are notices matched to the Nations and Native Hawaiian organizations they name?", "construct"),
    ]),
  }),
  lobbying: Object.freeze({
    questions: Object.freeze([
      q(describe, "Which agencies and chambers do Native organizations engage, and on which issues?", ["government_bodies", "issue_codes"]),
      q(compare, "How much are peer organizations reporting on federal lobbying?", ["reported_amount_usd", "canonical_name", "reporting_year"]),
      q(trace, "Which registrants file on an organization's behalf?", ["registrant_name", "client_name", "canonical_name"]),
    ]),
    cedar: Object.freeze([
      ask(describe, "What does this collection include beyond registered lobbying?", "content"),
      ask(trace, "How is each activity tied to the tribe or organization behind it?", "construct"),
    ]),
  }),
  contractors: Object.freeze({
    questions: Object.freeze([
      q(describe, "Which agencies award contracts to Native-owned firms in a given industry?", ["funding_agency", "naics_description"]),
      q(compare, "How does an organization's use of set-asides compare with its peers?", ["set_aside_classification", "obligations_usd", "canonical_name"]),
      q(trace, "What parent and Native-entity associations are recorded for a contractor?", ["awardee_name", "parent_name", "canonical_name"]),
    ]),
    cedar: Object.freeze([
      ask(describe, "What does this collection let me examine on an award?", "content"),
      ask(trace, "How are vendors rolled up to their parent Nation or corporation?", "construct"),
    ]),
  }),
  subcontracting: Object.freeze({
    questions: Object.freeze([
      q(trace, "Which prime contractors and subcontractors appear together in reported subawards?", ["prime_name", "subcontractor_name", "native_direction"]),
      q(describe, "Which industries are recorded for subcontractors in the release?", ["naics_description", "native_direction"]),
      q(compare, "How large are subawards relative to their prime awards?", ["subaward_amount_usd", "prime_award_amount_usd", "subaward_to_prime_ratio"]),
    ]),
    cedar: Object.freeze([
      ask(describe, "What does this collection show about the prime relationship?", "content"),
      ask(trace, "How are subawards tied to the same entities as their primes?", "construct"),
    ]),
  }),
  "natural-resources": Object.freeze({
    questions: Object.freeze([
      q(describe, "Which commodities and monetary measures are recorded for a Nation?", ["commodity", "canonical_name", "amount_usd", "measurement_status"]),
      q(compare, "How do reported resource amounts vary by period and measurement status?", ["revenue_type", "period_start", "amount_usd", "measurement_status"]),
      q(trace, "Who pays and who operates on the lands behind these revenues?", ["payer_name", "operator_name"]),
    ]),
    cedar: Object.freeze([
      ask(describe, "What does this collection let me compare across commodities?", "content"),
      ask(trace, "How are production and disbursements matched to Nations and allottees?", "construct"),
    ]),
  }),
  owned: Object.freeze({
    // Two, not three. A listing appears only on the terms its nation sets and
    // otherwise only in aggregates, so a question about where individual
    // businesses are would promise rows the collection withholds.
    questions: Object.freeze([
      q(trace, "Which offices certify Native-owned businesses, and under which programs?", ["certifying_authority_name", "program_name"]),
      q(describe, "In which industries are a Nation's certified businesses concentrated?", ["naics_code", "certifying_authority_name"]),
    ]),
    cedar: Object.freeze([
      ask(describe, "What does this collection hold about each business?", "content"),
      ask(trace, "How does a business come to be listed, and on whose terms?", "construct"),
    ]),
  }),
  nonprofits: Object.freeze({
    questions: Object.freeze([
      // The owner's "operate in a similar space", made exact: the IRS
      // activity code (NTEE) in the release, not an invented similarity.
      q(compare, "Which organizations share the same IRS activity code?", ["ntee_code"]),
      q(compare, "How do Native-led and Native-serving organizations differ across the roster?", ["organization_entity_class", "ntee_code", "state"]),
      q(trace, "Which organizations also appear in federal funding or advocacy records?", ["cedar_uid"]),
    ]),
    cedar: Object.freeze([
      ask(describe, "What does this collection hold about each organization?", "content"),
      ask(trace, "How are Native-led and Native-serving organizations told apart?", "construct"),
    ]),
  }),
  need: Object.freeze({
    questions: Object.freeze([
      q(trace, "What ownership relationships are documented for the reviewed enterprises?", ["enterprise_name", "owner_name", "relationship_type"]),
      q(compare, "Which federal identifiers are documented for the reviewed enterprises?", ["enterprise_name", "uei", "cage_code"]),
      q(trace, "Which evidence and source release support each reviewed enterprise?", ["evidence_pins", "source_release_id", "reviewed_on"]),
    ]),
    cedar: Object.freeze([
      ask(describe, "What does this collection hold about an enterprise's owner and parent?", "content"),
      ask(trace, "How are subsidiaries and joint ventures tied to the Nation or corporation behind them?", "construct"),
    ]),
  }),
});

// ── The two collections presented by their record structure ─────────────
//
// The owner's questions (2026-09-26) for Foundation & Corporate Giving and
// PLOT. Neither has a release file, so neither has a codebook table in this
// repository, and neither carries `cedar` questions: Cedar answers from a
// release profile and there is none to answer from. `cedarQuestions` returns
// nothing for them, and the Python suite, which runs every Cedar question
// through the profile router, has none to run.
//
// Foundation & Corporate Giving's `fields` name the producer's declared
// columns (Lumecon-data, `foundation_release.py`, `FIELDS`), and the node
// suite holds them to that list until a codebook table replaces it. PLOT has
// no producer in any repository, so its questions name no field; the suite
// pins that as the one named exception and fails the day a PLOT codebook
// table exists and the fields are still empty.
//
// "Organizations like this one" is made exact the way Federal Funding's is:
// "like" is the recipient's entity type, not a similarity measure.
const STRUCTURE_JOBS = Object.freeze({
  "foundation-corporate-giving": Object.freeze({
    questions: Object.freeze([
      q(describe, "Which funders support organizations of the same type as this one?", ["funder_name", "recipient_entity_type", "recipient_name"]),
      q(describe, "What purposes and geographies are receiving disclosed private funding?", ["purpose", "project_geography", "amount_exact_usd"]),
      q(compare, "How does private giving compare with federal support?", ["cedar_uid", "amount_exact_usd", "financial_status"]),
    ]),
  }),
  plot: Object.freeze({
    questions: Object.freeze([
      q(trace, "Where does this entity hold or acquire property?", []),
      q(describe, "What permits or development activity are associated with those parcels?", []),
      q(compare, "How has recorded activity around a property changed over time?", []),
    ]),
  }),
});

/** Every collection's questions, released or not, by catalog id. */
export const ALL_COLLECTION_JOBS = Object.freeze({ ...COLLECTION_JOBS, ...STRUCTURE_JOBS });

/** The questions a collection's fields can answer, or none. */
export function collectionQuestions(id) {
  return ALL_COLLECTION_JOBS[id]?.questions ?? [];
}

/** What Cedar can answer about a collection, the release question last. */
export function cedarQuestions(id) {
  const own = COLLECTION_JOBS[id]?.cedar;
  return own ? [...own, CEDAR_CHANGES_QUESTION] : [];
}

/**
 * One Cedar question per collection, scoped to it, for a panel that opened
 * with no collection in hand. The `n`th collection offers its `n`th question
 * (wrapping), so the set shows the different kinds of thing Cedar can answer
 * rather than the same question several times.
 */
export function openCedarQuestions(entries) {
  return entries
    .map((entry, i) => {
      const asked = cedarQuestions(entry?.id);
      return asked.length ? { q: asked[i % asked.length].q, scope: { id: entry.id, name: entry.name } } : null;
    })
    .filter(Boolean);
}

// ── AUDIENCE_JOBS ─────────────────────────────────────────────────────────
//
// One use case per audience: { audience, job, outcome, explanation (the
// brief's "intelligence"), collections, imagePool }. Outcome and explanation are
// the owner's, verbatim.
//
// `collections` are the collections the sentence actually names, in the
// order it names them, and nothing added for coverage.
//
// `imagePool` is the use case's approved pool (`pressImagery.js`), in the order
// a returning visitor sees it: each visit to the use case shows the next.
// Only photographs with no identifiable person; each keeps its own sector's
// wash. The pools are recorded in docs/IMAGE_LICENSES.md.

export const AUDIENCE_JOBS = Object.freeze([
  Object.freeze({
    id: "tribal-nations",
    audience: "Tribal Nations",
    job: "Economic development",
    outcome: "Learn from how peer nations are building their economies.",
    // Every phrase has a collection: enterprise growth (Cedar NEED),
    // contracts (Prime Contracting), major transactions (Deals), resource
    // activity (Natural Resources), funding (Federal Funding).
    explanation: "Follow enterprise growth, contracts, major transactions, resource activity and funding across Indian Country to identify strategies worth examining in your own planning.",
    collections: Object.freeze(["need", "contractors", "natural-resources", "funding"]),
    // Owner: economy sectors (hospitality, energy, construction,
    // manufacturing, healthcare), and not "Tribal Nations = council
    // chamber", so no government photograph. An exterior scene leads; the
    // hotel room is an interior and comes last. Healthcare is left out:
    // Lumecon's photograph shows two faces.
    imagePool: Object.freeze(["construction", "utilities-v2", "manufacturing-v2", "hospitality"]),
  }),
  Object.freeze({
    id: "ancs-nhos",
    audience: "ANCs and NHOs",
    // The owner's direction for this audience (2026-09-26), added to the
    // shared vocabulary for it.
    job: "Competitive intelligence",
    outcome: "Understand the competitive environment around your portfolio.",
    explanation: "Track subsidiaries, joint ventures, federal business, major transactions and property activity to see where peer organizations are expanding and where new opportunities may be forming.",
    collections: Object.freeze(["need", "subcontracting", "deals", "plot"]),
    imagePool: Object.freeze(["transportation", "manufacturing", "construction"]),
  }),
  Object.freeze({
    id: "native-enterprises",
    audience: "Native enterprises",
    job: "Partner discovery",
    outcome: "Find opportunities, partners and competitive signals.",
    explanation: "Compare ownership networks, contracting, transactions and Native-owned businesses to identify partners, suppliers, competitors and markets worth watching.",
    collections: Object.freeze(["need", "contractors", "deals", "owned"]),
    imagePool: Object.freeze(["manufacturing-v2", "agriculture", "retail", "wholesale"]),
  }),
  Object.freeze({
    id: "banks-lenders",
    // Investors and CDFIs belong here (owner's brief). Nothing in either
    // sentence implies a credit score or a substitute for underwriting; keep
    // it that way.
    audience: "Banks, lenders and investors",
    job: "Due diligence",
    outcome: "Do more informed diligence and spot opportunities earlier.",
    explanation: "Understand ownership, federal business, funding relationships, transactions and property activity before financing, investing in or partnering with a Native enterprise.",
    collections: Object.freeze(["contractors", "foundation-corporate-giving", "deals", "plot"]),
    imagePool: Object.freeze(["finance", "realestate"]),
  }),
  Object.freeze({
    id: "native-nonprofits",
    audience: "Native nonprofits",
    job: "Competitive funding",
    outcome: "Make a stronger case for competitive funding.",
    explanation: "See which funders support peer organizations, how similar nonprofits combine federal and private support, and where your own funding mix differs before pursuing the next grant.",
    collections: Object.freeze(["nonprofits", "funding", "foundation-corporate-giving", "lobbying"]),
    imagePool: Object.freeze(["otherservices", "context-cedar"]),
  }),
  Object.freeze({
    id: "foundations-philanthropy",
    audience: "Foundations and philanthropy",
    // "Capital allocation" in the owner's note; the nearest job in the
    // shared vocabulary.
    job: "Investment opportunity",
    // Owner copy, revised 2026-09-26.
    outcome: "Put need and existing support in context before allocating capital.",
    // The owner's caution: the collections show observable indicators of
    // funding, activity, service footprint and organizational presence, and
    // must not claim a definitive need score. The body says so.
    explanation: "Compare disclosed private giving with federal support and see which organizations and places already attract funding. Cedar Press shows observable public and private funding and activity, not a need score.",
    collections: Object.freeze(["foundation-corporate-giving", "funding", "nonprofits"]),
    // The owner's list: health, housing, education, community services.
    // Lumecon's health and education photographs show faces.
    imagePool: Object.freeze(["otherservices", "realestate"]),
  }),
  Object.freeze({
    id: "businesses",
    audience: "Businesses working in Indian Country",
    job: "Market entry",
    outcome: "Understand the market before entering it.",
    explanation: "Identify Native enterprises, Native-owned businesses, active sectors, contracting patterns and major transactions before choosing markets, partners or outreach targets.",
    collections: Object.freeze(["need", "owned", "subcontracting", "deals"]),
    // The owner's list: construction, logistics, professional services,
    // tech, finance. Lumecon's professional-services and information
    // photographs show faces, so logistics is carried twice instead.
    imagePool: Object.freeze(["construction", "wholesale", "transportation", "finance"]),
  }),
  Object.freeze({
    id: "universities-researchers",
    audience: "Universities and researchers",
    job: "Research",
    outcome: "Spend more time answering the research question, not rebuilding the data.",
    // "Federal, tribal and institutional datasets": legislation and advocacy
    // (federal), natural resource revenues on trust lands (tribal), and
    // NAGPRA's institutional records.
    explanation: "Start with cleaned, linked and source-backed records instead of rebuilding separate federal, tribal and institutional datasets from scratch.",
    collections: Object.freeze(["legislation", "lobbying", "natural-resources", "nagpra"]),
    // Research is not a sector, and Lumecon's education photograph shows a
    // seated audience's faces: the two context textures, in slate.
    imagePool: Object.freeze(["context-lattice", "context-cedar"]),
    researchExample: Object.freeze({
      text: "A researcher studying federal advocacy needs the Advocacy collection for one article and wants the underlying records and source trail.",
      collections: Object.freeze(["lobbying"]),
    }),
  }),
  Object.freeze({
    // NEW, owner, 2026-09-27: federal, state and local officials. Not a
    // Native audience, so it sits after the researchers rather than beside
    // Tribal Nations, which stays its own audience. Cedar SUPPORTS
    // consultation and government-to-government relationships; no sentence
    // here may present it as a substitute for engaging Native nations
    // directly.
    id: "government-officials",
    audience: "Government and public agency officials",
    job: "Tribal consultation",
    outcome: "Prepare more informed tribal consultations, build stronger government-to-government relationships, and better serve the communities you represent.",
    // Every claim has a collection, in the sentence's order: funding
    // (Federal Funding), legislation (Legislation), agency actions (Federal
    // Register), and Native-entity records (NAGPRA, whose notices are the
    // consultation record most agencies and museums work from).
    explanation: "Bring funding, legislation, agency actions and Native-entity records together with sources you can check.",
    collections: Object.freeze(["funding", "legislation", "federal-register", "nagpra"]),
    // Public infrastructure with no faces and no council chamber: utilities,
    // transportation, then the cedar texture.
    imagePool: Object.freeze(["utilities", "transportation", "context-cedar"]),
  }),
  Object.freeze({
    id: "journalists",
    audience: "Journalists and newsrooms",
    job: "Journalism",
    outcome: "Get to the story faster and show the record behind it.",
    explanation: "Follow organizations and events across funding, policy, advocacy, ownership, land and transactions while keeping the underlying source attached.",
    collections: Object.freeze(["federal-register", "lobbying", "need", "plot", "deals"]),
    imagePool: Object.freeze(["context-cedar", "context-lattice"]),
    researchExample: Object.freeze({
      text: "A reporter needs Deals and Cedar NEED to trace an acquisition and the enterprise structure behind it.",
      collections: Object.freeze(["deals", "need"]),
    }),
  }),
  Object.freeze({
    id: "advisors",
    // Renamed by the owner, 2026-09-27, from "Advisors and professional
    // services"; the id is kept. Research for client work and outreach, NOT
    // a contact database: nothing here may promise contacts, leads lists or
    // outreach lists, because no collection holds them.
    audience: "Consultants and advisors",
    job: "Client strategy",
    outcome: "Build sourced analyses for clients without reconstructing records across agencies and vendors.",
    // Every claim has a collection, in the sentence's order: funding
    // (Federal Funding), contracting (Prime Contracting), ownership (Cedar
    // NEED), policy (Federal Register), transaction records (Deals).
    explanation: "Research organizations, markets and prospective clients through funding, contracting, ownership, policy and transaction records.",
    collections: Object.freeze(["contractors", "subcontracting", "federal-register", "lobbying"]),
    // Lumecon's professional-services and management photographs both show
    // faces, and a handshake beside this sentence reads as an endorsement.
    imagePool: Object.freeze(["context-lattice", "context-cedar"]),
  }),
  Object.freeze({
    // NEW, owner's brief of 2026-09-26: investors, CDFIs, banks, corporate
    // development teams, foundations, government agencies, suppliers,
    // infrastructure developers and economic development organizations, as
    // one audience rather than nine. "Philanthropy" here is a kind of
    // outside support that may fit, not a claim on the giving collection's
    // records.
    id: "economic-development",
    audience: "Economic development, investors and outside partners",
    job: "Economic development",
    outcome: "See where capital, support or partnership may fit.",
    explanation: "Compare public funding, enterprise activity, contracting, transactions and organizational presence to understand where outside investment, procurement, philanthropy or technical support may fit.",
    collections: Object.freeze(["funding", "subcontracting", "foundation-corporate-giving", "nonprofits"]),
    imagePool: Object.freeze(["utilities", "agriculture", "construction"]),
  }),
]);


/**
 * An audience as a page shows it against `catalog`, with its collections
 * resolved to catalog entries, or null when a collection it names is not in
 * that catalog or it names fewer than `MIN_COLLECTIONS`.
 *
 * Returns `{ id, audience, job, outcome, explanation, collections, imagePool }`.
 */
export function resolveAudience(useCase, catalog = STOREFRONT_CATALOG) {
  const collections = useCase.collections.map((id) => liveCollection(id, catalog));
  if (collections.some((entry) => !entry) || collections.length < MIN_COLLECTIONS) return null;
  return Object.freeze({
    id: useCase.id,
    audience: useCase.audience,
    job: useCase.job,
    outcome: useCase.outcome,
    explanation: useCase.explanation,
    collections: Object.freeze(collections),
    imagePool: useCase.imagePool ?? Object.freeze([]),
  });
}

/** Every audience the page shows today, in order, resolved. */
export function visibleAudiences(catalog = STOREFRONT_CATALOG, audiences = AUDIENCE_JOBS) {
  return audiences.map((audience) => resolveAudience(audience, catalog)).filter(Boolean);
}

/** Every collection id an audience cites. */
export function citedIds(audiences = AUDIENCE_JOBS) {
  return new Set(audiences.flatMap((audience) => audience.collections));
}

/**
 * Live collections no shown use case cites: a REPORT for review, not a rule.
 * The use cases lead with the best reasons to use Cedar Press, so a
 * collection that no sentence names is noted (the node suite prints it) and
 * never given a chip to fill the gap. Every collection is still one click
 * away in the hero viewer's rail and on the collections page.
 */
export function uncoveredIds(catalog = STOREFRONT_CATALOG, audiences = AUDIENCE_JOBS) {
  const cited = new Set(
    visibleAudiences(catalog, audiences).flatMap((audience) => audience.collections.map((entry) => entry.id)),
  );
  return catalog.map((entry) => entry.id).filter((id) => !cited.has(id));
}

/**
 * Research access's good-fit examples, from the audiences that carry one,
 * each with its collections resolved. An example citing a collection that is
 * not live is not offered.
 */
export function researchExamples(catalog = STOREFRONT_CATALOG, audiences = AUDIENCE_JOBS) {
  return audiences
    .filter((audience) => audience.researchExample)
    .map((audience) => ({
      id: audience.id,
      text: audience.researchExample.text,
      collections: audience.researchExample.collections.map((id) => liveCollection(id, catalog)),
    }))
    .filter((example) => example.collections.every(Boolean));
}

// ── ENTITY_JOBS ─────────────────────────────────────────────────────────
//
// The owner named four contextual actions for the entity page (revised
// 2026-09-26). Only the ones that work today are shown, and no dead button
// stands in for the rest; they stay listed here, unavailable, so the gap is
// recorded where the next change will look for it.
//
//   related    Cedar NEED narrowed to this entity: the enterprises it owns or
//              is affiliated with (`?c=need&e=`). Offered only when the
//              reader's plan opens Cedar NEED.
//   over-time  every record the reader's plan opens for this entity, oldest
//              first (`?e=&s=date:asc`)
//   compare    Compare with peers: no peer or similarity method exists
//   ask        Ask Cedar about this organization: Cedar reads a collection's
//              release profile, not an entity's records, so it cannot answer

export const ENTITY_JOBS = Object.freeze({
  line: "See this organization across Cedar Press.",
  actions: Object.freeze([
    Object.freeze({ id: "compare", label: "Compare with peers", available: false }),
    Object.freeze({ id: "ask", label: "Ask Cedar about this organization", available: false }),
    Object.freeze({ id: "related", label: "View related enterprises", available: true, collection: "need" }),
    Object.freeze({ id: "over-time", label: "See activity over time", available: true }),
  ]),
});

/** The entity page's actions that work today, in the owner's order. */
export function entityActions() {
  return ENTITY_JOBS.actions.filter((action) => action.available);
}
