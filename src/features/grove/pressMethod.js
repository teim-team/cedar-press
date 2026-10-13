/**
 * REVIEW OWNER: Havala
 *
 * PURPOSE
 * The method sections of the Cedar Press page: what the collections are built
 * from, how they are maintained, how they reinforce one another, and what a
 * tribal government has to do to request the records Cedar holds about it.
 *
 * These sit in a module rather than in the page for the same reason the
 * articles and citations do: the page renders whatever these lists hold, so a
 * new domain, pipeline stage or timeline entry is a data change, and the
 * claims can be tested rather than only read.
 *
 * COPY DISCIPLINE
 * Written to the brand lock in CLAUDE.md: no em dashes, no serial comma unless
 * dropping it creates ambiguity, and no antithesis constructions ("not X, it's
 * Y"). Several lines in the source brief used that reversal and are stated
 * directly here instead; the substance is unchanged.
 */

import { contactHref } from "./appLink.js";

/**
 * How Cedar Press is maintained, and what for (owner, 2026-09-27). One
 * source for the wording, so each surface that says it (the door, Methods,
 * the collection profile, the signed-in close, What's New and door Cedar)
 * says the same thing without pasting the same paragraph everywhere: a
 * surface takes the sentence, the goal or the short label it needs.
 */
export const MAINTENANCE = Object.freeze({
  /** The whole commitment, in one sentence. A schedule Cedar Press keeps,
   *  not a measured update history (2026-10-06). */
  sentence:
    "Cedar Press maintains its datasets on a weekly schedule with human review, expands their source coverage and useful fields over time and develops new collections.",
  /** Why: the goal the maintenance serves. */
  goal: "The aim is exceptionally useful, well-documented data and tools for Indian Country, well beyond filling in missing records.",
  /** The short form for a fact line. */
  label: "Weekly review schedule, with human review",
});

/**
 * Patents and credit ratings in Cedar NEED (owner, 2026-09-27): enrichments
 * of the enterprise records, not collections of their own, so they add no
 * catalog entry and no count. Each keeps the entity it concerns.
 */
export const NEED_ENRICHMENTS = Object.freeze({
  patents:
    "Patents, where records are available, cover those originally assigned to an entity and those it later acquired, and an acquired patent is shown as acquired rather than as the entity's own invention.",
  ratings:
    "Credit ratings, where records are available, keep their issuer, instrument, agency and date, so a historical rating reads as an observation on that date rather than as a current rating.",
  attachment:
    "Each patent and each rating stays attached to the Native entity or enterprise it concerns, so a subsidiary's record is never presented as its parent's.",
  // The download's native_owner columns (server/cedar_press/collections.py,
  // 2026-10-06).
  ownership:
    "Each NEED record names its ultimate Native owner, the nation, Alaska Native corporation or Native Hawaiian organization at the top of the ownership chain, where a recorded ownership ruling or register binding states it, with the basis and a public source in the download. Nothing is inferred from a company's name.",
});

/**
 * What the home page's example records are (owner, 2026-10-10): records from
 * each collection's served download, some chosen and ordered
 * (landingExamples.js), while the collections and every download carry the
 * release itself.
 */
export const EXAMPLES_NOTE =
  "The example records on the Cedar Press home page come from each collection's current download, chosen to show the collection clearly. What you open in a collection and what you download is the release itself, record for record.";

/**
 * The domains the collections are built out of. Each one has its own legal
 * definitions, administrative systems, reporting conventions, historical
 * changes and source quirks, which is the point: no single API or technical
 * skill covers them.
 */
export const EXPERTISE_DOMAINS = Object.freeze([
  "Federal contracting and subcontracting",
  "Federal funding, grants, loans and direct spending",
  "Natural resources",
  "Congressional legislation and voting",
  "Registered federal lobbying disclosure",
  "Federal Register actions",
  "Tribal recognition",
  "NAGPRA",
  "Native nonprofits",
  "Tribal enterprises and economic development",
  "Native business certification and ownership",
  // The owner's Methods concepts for the two collections that joined Cedar
  // Press on 2026-09-27 (Foundation & Corporate Giving, PLOT).
  "Philanthropic, corporate and bank giving",
  "Land ownership, transfers, permitting and development",
]);

/**
 * The strip the Methods page names its domains from. Each names the domains
 * above that it stands for, so the strip is provably a summary of the list
 * rather than a separate claim: `covers` entries must appear verbatim in
 * EXPERTISE_DOMAINS, and every domain must be covered by one of these.
 *
 * Gaming was one of these until 2026-09-04. It left with the Gaming
 * Intelligence preview: a page that names gaming as a domain of expertise
 * beside a shelf that sells no gaming collection reads as a promise, and the
 * collection is still being built.
 */
export const EXPERTISE_STRIP = Object.freeze([
  Object.freeze({
    id: "spending",
    label: "Federal spending",
    covers: Object.freeze(["Federal funding, grants, loans and direct spending"]),
  }),
  Object.freeze({
    id: "contracting",
    label: "Contracting",
    covers: Object.freeze(["Federal contracting and subcontracting"]),
  }),
  Object.freeze({
    id: "resources",
    label: "Natural resources",
    covers: Object.freeze(["Natural resources"]),
  }),
  Object.freeze({
    id: "policy",
    label: "Policy and regulation",
    covers: Object.freeze([
      "Congressional legislation and voting",
      "Registered federal lobbying disclosure",
      "Federal Register actions",
      "Tribal recognition",
      "NAGPRA",
    ]),
  }),
  Object.freeze({
    id: "institutions",
    label: "Native institutions and enterprises",
    covers: Object.freeze([
      "Native nonprofits",
      "Tribal enterprises and economic development",
      "Native business certification and ownership",
    ]),
  }),
  Object.freeze({
    id: "giving",
    label: "Private giving",
    covers: Object.freeze(["Philanthropic, corporate and bank giving"]),
  }),
  Object.freeze({
    id: "land",
    label: "Land ownership",
    covers: Object.freeze(["Land ownership, transfers, permitting and development"]),
  }),
]);

/** The domains as one sentence, for the Methods page's expertise paragraph. */
export function expertiseSentence() {
  const labels = EXPERTISE_STRIP.map((domain) => domain.label);
  const lowered = labels.map((label, index) => (index === 0 ? label : label[0].toLowerCase() + label.slice(1)));
  return `${lowered.slice(0, -1).join(", ")} and ${lowered.at(-1)}`;
}

/**
 * Where the records come from. Named because the page should not imply that
 * Cedar downloads finished files from government websites; most of these were
 * never published as a collection at all.
 */
export const SOURCE_KINDS = Object.freeze([
  "APIs",
  "Historical files",
  "Regulatory documents",
  "Federal Register notices",
  "Environmental reviews",
  "Agency reports",
  "State disclosures",
  "Archived webpages",
  "Transaction announcements",
  "Legal and administrative decisions",
  "Entity records",
  "Manually reviewed documentation",
  // Cedar NEED's enrichments (owner, 2026-09-27).
  "Patent records, supported by company, tribal, SEC and court evidence",
  "Rating-agency announcements, supported by issuer and tribal releases, filings, regulator records and labeled secondary sources",
]);

/**
 * How a collection gets made, in order. Rendered as the pipeline on the
 * Methods page (`ProcessRail`), which used to carry its own copy of these
 * seven stages while this list rendered nowhere; the two had different
 * names for the same steps. One list, the rendered one.
 */
export const CONSTRUCTION_STEPS = Object.freeze([
  Object.freeze({
    id: "discover",
    label: "Discover",
    note: "Find APIs, archives, public notices, regulatory dockets, filings and state reports.",
  }),
  Object.freeze({
    id: "extract",
    label: "Extract",
    note: "Retrieve structured records, historical files and relevant document-level information.",
  }),
  Object.freeze({
    id: "normalize",
    label: "Normalize",
    note: "Reconcile names, dates, identifiers and geographies so records from different sources line up.",
  }),
  Object.freeze({
    id: "resolve",
    label: "Resolve",
    note: "Tie each record to the government, enterprise, ANC, NHO, nonprofit or facility behind it.",
  }),
  Object.freeze({
    id: "validate",
    label: "Validate",
    note: "Use source documentation and other Cedar collections to confirm relationships and identify conflicts.",
  }),
  Object.freeze({
    id: "review",
    label: "Review",
    note: "Researchers examine ambiguous matches, unusual relationships and historical changes that automation cannot safely resolve alone.",
  }),
  Object.freeze({
    id: "maintain",
    label: "Maintain",
    note: "Track new entities, renames, acquisitions, ownership changes, closures, reorganizations and corrections over time.",
  }),
]);

/**
 * How Cedar decides what to build next (owner, 2026-09-26): from a question
 * the collections cannot answer yet to a maintained release. The Methods
 * chapter draws these in order; Priorities is where the questions come in.
 */
export const BUILD_NEXT_QUESTION = "What important question can I not answer today?";

export const BUILD_NEXT_STEPS = Object.freeze([
  Object.freeze({
    id: "question",
    label: "Question",
    note: "A question the current collections cannot answer, from a subscriber's priority, a Nation's request or Cedar's own research.",
  }),
  Object.freeze({
    id: "sources",
    label: "Source investigation",
    note: "Which public records could answer it, who publishes them, how far back they reach and what they leave out.",
  }),
  Object.freeze({
    id: "design",
    label: "Research and collection design",
    note: "What one record is, which fields it carries and how each record reaches the Native entity it is about.",
  }),
  Object.freeze({
    id: "validate",
    label: "Validation",
    note: "Records checked against their sources and against the other collections; ambiguous matches go to a researcher.",
  }),
  Object.freeze({
    id: "release",
    label: "Release",
    note: "Published with an update date, a coverage span, its sources and what it does not contain.",
  }),
  Object.freeze({
    id: "maintain",
    label: "Maintenance",
    note: "Reviewed by a person on a weekly schedule as sources update, organizations change and corrections arrive, with each change logged against a release and source coverage and useful fields added over time.",
  }),
]);

/** What research judgment looks like when direct reporting runs out. */
export const DISCOVERY_MOVES = Object.freeze([
  "Identifying indirect evidence",
  "Finding records in unexpected agencies",
  "Using one source to validate another",
  "Reconstructing history from archived material",
  "Building defensible estimates where direct reporting is unavailable",
  "Distinguishing recipients from beneficiaries",
  "Tracking affiliations and ownership across time",
]);

/** The changes Cedar tracks, which is what keeps a collection from going stale. */
export const MAINTENANCE_TRACKED = Object.freeze([
  "Name changes",
  "Mergers and acquisitions",
  "Ownership transfers",
  "New subsidiaries",
  "Closed or renamed organizations",
  "Changes in tribal affiliation",
  "Recognition and legal-status changes",
  "Corrections to historical records",
  "Changes in source systems",
  "Newly released historical files",
]);

/**
 * The collections that feed the shared entity layer, and are fed by it, live
 * in `pressEcosystem.js` (`ECOSYSTEM`), keyed by catalog id, because that is
 * the module the diagram draws from. A second list here carried different
 * ids and a collection the storefront does not sell.
 */

/** Worked examples of one collection improving another. */
export const ECOSYSTEM_EXAMPLES = Object.freeze([
  "A transaction in Indian Country Deals can reveal a new owner, subsidiary or renamed enterprise, which corrects the enterprise structure, contracting and nonprofit records.",
  "A Federal Register notice can validate a recognition event, a regulatory action or a land-related development.",
  "Lobbying disclosure filings connect organizations to the issues and bills they lobbied on, and bill histories and votes show what followed.",
  "A nation's own enterprise register or audited filing names the subsidiaries the federal record files under unrelated names.",
  "Patent records and rating-agency announcements add to an enterprise's Cedar NEED profile where records are available, each kept with the specific entity it concerns and its date.",
  "Federal funding and contracting records add economic activity to an entity profile.",
  "A site acquisition recorded in Indian Country Deals links to the parcels PLOT follows, so a transaction and the land it bought read together without being collapsed into one record.",
  "Foundation, corporate and bank giving read beside federal funding and the Native Nonprofits roster shows how an organization's private and public support combine, with the legal recipient and the Native beneficiary kept apart.",
  "Better entity resolution then improves matching across every collection above.",
]);

/** What reproducing the collections would actually take. */
export const REPLICATION_CALLOUTS = Object.freeze([
  "Decades of combined domain experience",
  "Sources that were never designed to connect",
  "Proprietary linkage and reconciliation methods",
  "Human review of difficult records",
  "Continuous ownership and affiliation tracking",
  "Collections that validate and improve one another",
]);

/**
 * The Tribal Data Request policy. Written so that an unaffiliated person
 * cannot obtain a tribe's compiled records by asserting a connection: the
 * request has to come from, or be expressly authorized by, the federally
 * recognized tribal government, and Cedar can verify that independently.
 */
export const TRIBAL_REQUEST = Object.freeze({
  mailto:
    contactHref("Tribal Data Request"),
  policy:
    "Cedar will not release a tribe-specific data package because an individual claims affiliation with a tribe. Requests must be submitted or expressly authorized by the federally recognized tribal government, and Cedar may independently verify the requester's authority before releasing any records.",
  eligibility: Object.freeze([
    "An elected tribal official",
    "An authorized tribal employee",
    "Tribal legal counsel",
    "A formally designated representative",
  ]),
  verification: Object.freeze([
    "An official tribal government email address",
    "A signed authorization letter",
    "Confirmation from leadership, the executive office or legal counsel",
  ]),
  // What a package covers is what the collections hold about the nation.
  // "Its gaming operations" was on this list while Gaming Intelligence was
  // previewed on the shelf; it left with the preview on 2026-09-04, because a
  // request policy that names records the product does not yet publish is a
  // promise the desk cannot keep on the day the request arrives.
  included: Object.freeze([
    "Tribal government records",
    "Affiliated tribal enterprises",
    "Wholly owned or controlled entities",
    "Other records Cedar can reliably associate with the requesting tribal government",
  ]),
  // Written in the case they are read in: the page runs these into one
  // sentence, and lowercasing them there turned "Cedar" into "cedar".
  excluded: Object.freeze([
    "other tribes' records",
    "national comparative collections",
    "proprietary crosswalks",
    "Cedar's internal matching systems",
    "the complete Cedar entity graph",
    "restricted third-party information",
  ]),
  /** The five moments of a request, in order. */
  steps: Object.freeze([
    Object.freeze({ step: "Request", body: "Request your records" }),
    Object.freeze({ step: "Verify", body: "Confirm governmental authority" }),
    Object.freeze({ step: "Deliver", body: "Receive the tribe-specific package" }),
    Object.freeze({ step: "Review", body: "Review Cedar's records" }),
    Object.freeze({ step: "Correct", body: "Submit documentation or corrections" }),
  ]),
  purposes: Object.freeze([
    "Governmental planning",
    "Internal validation",
    "Economic development",
    "Research",
    "Record correction",
    "Administrative review",
  ]),
});

/**
 * Methodological restraint, stated as commitments.
 *
 * Not legal boilerplate: each of these is a thing Cedar could do to look more
 * complete and chooses not to, because the product's claim is trustworthy
 * intelligence and every one of these is where that claim would quietly die.
 * The first is also a sovereignty position, not only a data-quality one:
 * who and what is Native is each nation's to say.
 */
export const METHOD_COMMITMENTS = Object.freeze([
  Object.freeze({
    id: "no-inferred-identity",
    text: "Cedar does not infer tribal citizenship or Native identity. A business or organization carries the status its nation or certifying office states, and nothing overrides what a nation says about its own.",
  }),
  Object.freeze({
    id: "unresolved-stays-unresolved",
    text: "Unresolved entity relationships remain unresolved. A provisional match is labeled provisional rather than guessed into the graph.",
  }),
  Object.freeze({
    id: "conflicts-preserved",
    text: "Source conflicts are preserved and reviewed, never silently overwritten by the newer or more convenient record.",
  }),
  Object.freeze({
    id: "lineage-kept",
    text: "Historical records keep the lineage needed to reproduce earlier results. A correction adds to the history; it does not erase it.",
  }),
]);

/**
 * Where the team's institutional experience comes from. Named rather than
 * gestured at ("Ivy League researchers"), because the specifics are stronger
 * than the euphemism and a reader can check them.
 *
 * Text only, and no logos: a wall of institutional marks reads as sponsorship,
 * which none of these have given. The strip is a claim about the people, so it
 * carries the disclaimer with it wherever it renders.
 */
export const CREDIBILITY_STRIP = Object.freeze([
  Object.freeze({
    id: "federal-reserve",
    kind: "institution",
    label: "Federal Reserve experience",
    // Full institutional names, consistently: "Minneapolis Fed" beside
    // "Federal Reserve Board" read as two registers for one system.
    names: Object.freeze([
      "Federal Reserve Board",
      "Federal Reserve Bank of Minneapolis",
      "Federal Reserve Bank of Philadelphia",
    ]),
  }),
  Object.freeze({
    id: "universities",
    kind: "academic",
    label: "Academic backgrounds",
    names: Object.freeze(["MIT", "Oxford", "Cornell", "Brown", "Dartmouth", "Yale"]),
  }),
]);

/**
 * Required wherever CREDIBILITY_STRIP renders. Naming an institution a team
 * member studied or worked at is a fact about the person; leaving it
 * unqualified beside a product invites a reader to hear endorsement.
 */
export const CREDIBILITY_DISCLAIMER =
  "Institutional names reflect team members' professional or academic affiliations and do not imply institutional endorsement.";
