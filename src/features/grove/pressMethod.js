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
  "Federal advocacy, from lobbying disclosure to consultation and testimony",
  "Federal Register actions",
  "Tribal recognition",
  "NAGPRA",
  "Native nonprofits",
  "Tribal enterprises and economic development",
  "Native business certification and ownership",
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
      "Federal advocacy, from lobbying disclosure to consultation and testimony",
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
    note: "Find APIs, archives, notices, regulatory records, filings, state reports and other relevant sources.",
  }),
  Object.freeze({
    id: "extract",
    label: "Extract",
    note: "Retrieve structured records, historical files and relevant document-level information.",
  }),
  Object.freeze({
    id: "normalize",
    label: "Normalize",
    note: "Reconcile names, dates, identifiers, classifications, formats and geographies.",
  }),
  Object.freeze({
    id: "resolve",
    label: "Resolve",
    note: "Connect tribal governments, enterprises, ANCs, NHOs, businesses, nonprofits, facilities and relevant counterparties.",
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
 * One organization's lineage, as an illustration of what "maintained" means.
 * Generic on purpose: it demonstrates the shape of a tracked history without
 * asserting anything about a real enterprise. Rendered by `EntityTimeline`
 * on the Methods page, which carried its own copy until 2026-09-04.
 */
export const MAINTENANCE_TIMELINE = Object.freeze([
  Object.freeze({ year: "2017", event: "Enterprise created" }),
  Object.freeze({ year: "2019", event: "Subsidiary added" }),
  Object.freeze({ year: "2021", event: "Property acquired" }),
  Object.freeze({ year: "2023", event: "Entity renamed" }),
  Object.freeze({ year: "2025", event: "Ownership changed" }),
  Object.freeze({ year: "2026", event: "Historical records reconciled" }),
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
  "Advocacy records, from lobbying filings to consultations, docket comments and testimony, connect organizations to legislation, and bill histories and votes show what followed.",
  "A nation's own enterprise register or audited filing names the subsidiaries the federal record files under unrelated names.",
  "Federal funding and contracting records add economic activity to an entity profile.",
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
    "mailto:contact@lumecon.ai?subject=Tribal%20Data%20Request",
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
