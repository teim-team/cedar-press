/**
 * REVIEW OWNER: Havala
 *
 * PURPOSE
 * The Cedar Press and Cedar Grove ladder: what each tier costs, what it
 * promises, and which collection sits where.
 *
 * The organizing idea is that value is not spread evenly. Each rung carries
 * one or two things that make a particular reader say "obviously I need that
 * one", so the question at every boundary is concrete rather than a count of
 * datasets:
 *
 *   Cedar Press   what happened          lobbying, and a lot of current intelligence
 *   Cedar Press+  what drives it         federal contracting, and the deep history
 *   Cedar Grove   the whole environment  gaming intelligence, and the research tools
 *
 * THE BASE TIER IS THE PRODUCT
 * It is named "Cedar Press", not "Cedar Press Standard", because a tier called
 * Standard sitting under a product called Cedar Press makes a reader work out
 * which of the two they are looking at. The upgrade is "Cedar Press+", and the
 * page sets that plus raised at display size only.
 *
 * TWO AXES, NOT ONE
 * A reader can be short of a collection, or short of its history. Cedar Press
 * carries most collections from 2010 forward; Cedar Press+ unlocks the
 * reconstructed series behind them. So "upgrade" has two distinct meanings and the page has
 * to say which one applies, which is why `historyFrom` is a property of the
 * collection rather than a sentence in the marketing copy.
 *
 * RECOGNITION IS NOT A COLLECTION HERE
 * Legal-status change is the spine every other collection joins on, and it
 * moves rarely enough that selling it as a maintained subscription product
 * would be a promise about a cadence it does not have. It lives in the entity
 * and history layer instead, where the rest of the catalog reads it.
 *
 * THE CATALOG IS NOT THE PILOT
 * This is the architecture: every collection the ladder is designed around,
 * including ones with no data yet. `collection.js` holds the three that ship
 * in the pilot with real figures. A test pins that every shipping dataset
 * appears here, so the two cannot drift.
 */

/** The window the downloadable Cedar Press versions open at. */
export const PRESS_HISTORY_FROM = 2010;

export const PRESS_TIERS = Object.freeze([
  Object.freeze({
    id: "press",
    shelf: "standard",
    name: "Cedar Press",
    price: 500,
    question: "See what's happening.",
    promise:
      "Follow the money, policy, transactions, institutions and public actions across Indian Country.",
    historyNote: `Generally ${PRESS_HISTORY_FROM} to present.`,
  }),
  Object.freeze({
    id: "press_pro",
    shelf: "pro",
    name: "Cedar Press+",
    price: 1000,
    question: "Understand the systems behind it.",
    // Both axes, said here rather than left to the question. "Systems"
    // describes the four specialized collections and says nothing about the
    // archive, and the archive is half of what this tier sells.
    promise:
      "Federal contracting, subcontracting, resource revenue and the nonprofit sector, plus the full reconstructed archive behind every Cedar Press collection.",
    historyNote: "Full reconstructed series wherever one exists.",
  }),
  Object.freeze({
    id: "grove",
    shelf: "grove",
    name: "Cedar Grove",
    price: 2500,
    question: "Investigate it yourself.",
    promise:
      "Every Cedar collection, every new one as it lands and the harmonized public data your work already runs on. Grove is where you visualize it, analyze it and put it in front of your whole organization.",
    historyNote: "Everything, with the tools to query it.",
  }),
]);

/**
 * Every collection the ladder is designed around.
 *
 * `short` is the name on a badge, where a full title will not fit in a square.
 *
 * TWO COVERAGE FIELDS, NOT ONE MINUS A RULE
 * `standardFrom` is what a Cedar Press reader actually receives.
 * `historyFrom` is where the full reconstructed archive begins, which
 * Cedar Press+
 * opens. They are stored separately because the gap is not always the same
 * arithmetic: every Cedar Press collection starts at 2010, and how much
 * further back Cedar Press+ reaches is a property of the record rather than
 * of a rule. Deals is the case where the two are equal, because 2010 is all
 * the history there is, not because a window clipped it. Showing a Cedar
 * Press reader "1998 to present" for Lobbying describes an archive they were
 * not sold. When it is earlier than PRESS_HISTORY_FROM, Cedar Press+ unlocks
 * that depth for a collection Cedar Press already carries: the same shelf,
 * more years.
 */
export const PRESS_CATALOG = Object.freeze([
  Object.freeze({
    id: "funding",
    short: "Federal Funding",
    name: "Federal Funding to Indian Country",
    shelf: "standard",
    standardFrom: 2010,
    historyFrom: 2001,
    blurb:
      "Every award the federal government reports sending into Indian Country: grants, loans, direct payments and insurance. Trace a program's reach, a recipient's funding history or a year's totals, award by award.",
    linkage:
      "Recipients resolved to the Native entity behind them, so an award to a subsidiary, a housing authority or a consortium is attributed to the nation or organization it belongs to.",
  }),
  Object.freeze({
    id: "federal-register",
    short: "Federal Register",
    name: "Federal Register",
    shelf: "standard",
    standardFrom: 2010,
    historyFrom: 1994,
    blurb:
      "The Federal Register is the government's daily record of proposed and final agency action. Catch every notice, rule and comment window touching tribes, lands, water or recognition while there is still time to respond.",
    linkage:
      "Notices matched to the tribes, lands and organizations they name, including entities that appear under former or variant names.",
  }),
  Object.freeze({
    id: "legislation",
    short: "Legislation",
    name: "Congressional Votes and Proposed Legislation",
    shelf: "standard",
    standardFrom: 2010,
    historyFrom: 1989,
    blurb:
      "Bills, resolutions and roll-call votes from both chambers of Congress, the House and the Senate. Follow a measure from introduction to the floor and see who sponsored it, who voted and how.",
    linkage:
      "Bills and votes tied to the tribes and Native organizations they affect, not only to the sponsors who filed them.",
  }),
  Object.freeze({
    id: "deals",
    short: "Deals",
    name: "Indian Country Deals",
    shelf: "standard",
    standardFrom: 2010,
    historyFrom: 2010,
    blurb:
      "Announced transactions across Indian Country: acquisitions, property purchases, project financings, bond issuances and capital projects. See who bought, who financed, what closed and how a quarter compares with the last.",
    linkage:
      "Buyers, sellers, borrowers and issuers resolved to tribal governments, tribally owned enterprises, ANCs and NHOs.",
  }),
  Object.freeze({
    id: "nagpra",
    short: "NAGPRA",
    name: "NAGPRA",
    shelf: "standard",
    standardFrom: 2010,
    historyFrom: 1990,
    blurb:
      "Activity under the Native American Graves Protection and Repatriation Act: notices, inventories and completed repatriations. Track an institution's progress or a nation's outstanding claims, item by item.",
    linkage:
      "Notices matched to the tribes and Native Hawaiian organizations named in them, across the naming changes of three decades.",
  }),
  Object.freeze({
    id: "lobbying",
    short: "Lobbying",
    name: "Lobbying",
    shelf: "standard",
    standardFrom: 2010,
    historyFrom: 1998,
    blurb:
      "Federal lobbying registrations and the quarterly filings behind them. See who hired which firm, what they paid and which issues and bills the money is working.",
    linkage:
      "Registrants and clients resolved to the tribes and Native organizations behind them, including firms retained on their behalf.",
  }),
  Object.freeze({
    id: "contractors",
    short: "Prime Contracting",
    name: "Federal Prime Contracting",
    shelf: "pro",
    standardFrom: 2010,
    historyFrom: 2000,
    blurb:
      "A prime contract is an award the government makes directly to a vendor, whether a firm, a tribal enterprise or a tribal government itself. Every prime award here names the agency, the dollars, the industry and the set-aside path it came through.",
    linkage:
      "Vendors resolved to tribally owned firms, ANC and NHO subsidiaries and 8(a) participants, then rolled up to the parent nation or corporation.",
  }),
  Object.freeze({
    id: "subcontracting",
    short: "Subcontracting",
    name: "Federal Subcontracting",
    shelf: "pro",
    standardFrom: 2010,
    historyFrom: 2010,
    blurb:
      "A subaward is work a prime vendor passes down to another. Follow the dollars below the prime layer to see which vendors do the work, under whom and in which sectors.",
    linkage:
      "Subawards matched to the same resolved entities as the prime contracts above them.",
  }),
  Object.freeze({
    id: "natural-resources",
    short: "Natural Resources",
    name: "Natural Resource Revenues",
    shelf: "pro",
    standardFrom: 2010,
    historyFrom: 2003,
    blurb:
      "Energy and mineral activity on trust and restricted lands: production volumes, the royalties it owes and the disbursements that follow. See what a commodity produced, what it paid and where the money went.",
    linkage:
      "Production and disbursements matched to the nations and allottees they belong to.",
  }),
  Object.freeze({
    id: "nonprofits",
    short: "Native Nonprofits",
    name: "Native Nonprofits",
    shelf: "pro",
    standardFrom: 2010,
    historyFrom: 2001,
    blurb:
      "Native-led and Native-serving nonprofits with their annual federal filings. Compare budgets, revenue mixes, program spending and how an institution's finances move year over year.",
    linkage:
      "Filers classified as Native-led, Native-serving or Native-focused, which are three different things and are labeled separately.",
  }),
  Object.freeze({
    id: "gaming",
    short: "Gaming",
    name: "Gaming Intelligence",
    shelf: "grove",
    standardFrom: 1988,
    historyFrom: 1988,
    blurb:
      "Facilities, ownership and affiliation over time, declination letters, environmental reviews, expansions, employment estimates and transaction history, cross-validated against Deals.",
    // A Grove-exclusive collection is shown on Cedar Press rather than hidden,
    // because the point of it is to be a reason to cross a line. What a reader
    // may see without Grove is listed rather than left to a component to
    // decide, so the boundary is reviewable in one place.
    preview: Object.freeze({
      shows: Object.freeze([
        "What it contains",
        "Historical coverage",
        "Selected aggregate findings",
        "Related Cedar Press articles",
        "A methodology summary",
      ]),
      withholds: Object.freeze([
        "Record-level exploration",
        "Downloads",
        "Entity filters",
        "Full historical records",
        "Advanced queries",
      ]),
    }),
    linkage:
      "Facilities matched to their operators and their owners. This is the one collection where the counterparties are not all Native: management companies and outside operators are resolved and labeled as such.",
  }),
]);

/**
 * How the intelligence is organized for a reader, which is a different layer
 * from what it costs.
 *
 * Subject first, access second. The tiers explain depth of access; the
 * taxonomy explains the world, and organizing the whole information
 * architecture around price would make the catalog a rate card. It also
 * scales: health, housing, energy, lending, land and education enter a
 * structure rather than extending a wall of entries.
 */
export const PRESS_TAXONOMY = Object.freeze([
  Object.freeze({
    id: "public-finance",
    name: "Public Finance and Spending",
    lede: "Where federal money goes, and who it reaches.",
    collections: Object.freeze(["funding", "contractors", "subcontracting"]),
  }),
  Object.freeze({
    id: "policy",
    name: "Policy and Government",
    lede: "The actions, votes and legal changes that set the terms.",
    collections: Object.freeze(["federal-register", "legislation", "lobbying"]),
  }),
  Object.freeze({
    id: "markets",
    name: "Markets and Transactions",
    lede: "What is being bought, financed and built.",
    collections: Object.freeze(["deals"]),
  }),
  Object.freeze({
    id: "industries",
    name: "Industries and Resources",
    lede: "The sectors that carry the most economic weight.",
    collections: Object.freeze(["natural-resources", "gaming"]),
  }),
  Object.freeze({
    id: "institutions",
    name: "Institutions and Stewardship",
    lede: "The organizations and obligations that hold it together.",
    collections: Object.freeze(["nonprofits", "nagpra"]),
  }),
]);

/** The subject group a collection belongs to, for its own page's masthead. */
export function groupOf(id) {
  return PRESS_TAXONOMY.find((group) => group.collections.includes(id)) ?? null;
}

export const PRESS_CATALOG_BY_ID = Object.freeze(
  Object.fromEntries(PRESS_CATALOG.map((entry) => [entry.id, entry])),
);

/**
 * What Cedar actually sells.
 *
 * The underlying records are public. Anyone can pull a federal spending file
 * or a lobbying registration. What does not exist anywhere else is the join:
 * knowing that a contract awarded to a subsidiary with an unrelated name
 * belongs to a particular nation, that a nonprofit is Native-led rather than
 * Native-serving, that an entity renamed in 2014 is the same entity.
 *
 * This is the sentence the page has to lead with, because without it the
 * catalog reads as a repackaging of open data.
 */
export const NATIVE_LINKAGE = Object.freeze({
  // Not "resolved to the Native entity behind it": Cedar also carries
  // management companies, outside lobbying firms and other counterparties who
  // are not Native at all, and a claim the data cannot keep is worse than a
  // duller one it can.
  claim: "Every record gets the right context.",
  body:
    "Cedar connects changing names, ownership, affiliations, subsidiaries, governments, organizations, transactions and policy activity over time. Tribal governments, tribal enterprises, ANCs, NHOs, Native-owned businesses, Native-led organizations, Native-serving organizations and relevant counterparties remain distinct rather than being collapsed into one broad category.",
  hard: "The records may be public. The maintained relationships are Cedar's work.",
  /* Four concepts on the reader; the full taxonomy belongs on Methods. */
  groups: Object.freeze([
    "Governments and Native entities",
    "Native organizations",
    "Native-focused activity",
    "Relevant counterparties",
  ]),
  /* Distinct relationships, deliberately not collapsed into "Native". An
   * organization can serve Native communities without being Native-owned,
   * and a page that blurs the two is making a claim the data does not. */
  tiers: Object.freeze([
    Object.freeze({
      name: "Tribal governments",
      note: "Federally recognized tribes and Native Hawaiian organizations, with their agencies and authorities.",
    }),
    Object.freeze({
      name: "Tribally owned enterprises",
      note: "Businesses and corporations owned by a nation, rolled up to the government that owns them.",
    }),
    Object.freeze({
      name: "ANCs and NHOs",
      note: "Alaska Native Corporations, Native Hawaiian Organizations and their subsidiaries.",
    }),
    Object.freeze({
      name: "Native-led organizations",
      note: "Governed and run by Native people, without being owned by a nation.",
    }),
    Object.freeze({
      name: "Native-serving organizations",
      note: "Work directed at Native communities without Native ownership or governance. Labeled separately, never merged into the above.",
    }),
  ]),
});

/**
 * The public data Cedar Grove harmonizes alongside its own collections.
 *
 * Not Cedar collections and not sold separately: the reason a Grove licensee
 * stops keeping a folder of downloads is that the series they routinely need
 * for a grant report or a council packet are already joined to the Cedar
 * entities beside them. Listed on the shelf because a band showing one badge
 * misrepresents what the tier is.
 */
export const GROVE_PUBLIC_DATA = Object.freeze([
  Object.freeze({
    id: "census",
    short: "Census",
    name: "Census and American Community Survey",
    blurb:
      "Population, housing, income and employment for tribal areas and the counties around them, joined to the same entities as the Cedar collections.",
    kind: "public",
  }),
  Object.freeze({
    id: "labor",
    short: "Labor Statistics",
    name: "Bureau of Labor Statistics",
    blurb:
      "Employment, wages and industry detail, on the geographies your reporting and grant applications ask for.",
    kind: "public",
  }),
  Object.freeze({
    id: "economy",
    short: "Economic Data",
    name: "Bureau of Economic Analysis",
    blurb: "Output, income and industry accounts, harmonized to the same regions and years.",
    kind: "public",
  }),
  Object.freeze({
    id: "new-collections",
    short: "New collections",
    name: "Every collection Cedar builds next",
    blurb:
      "New Cedar collections land in Grove and stay there. Cedar Press carries what it carries; the roadmap arrives here.",
    kind: "public",
  }),
]);

/**
 * The shelves below, as one badge each.
 *
 * Cedar Press+ does not redraw the Cedar Press collections to say it
 * includes them, and Grove should not redraw eleven. Listing every collection
 * on the top tier made it the busiest band on the page, which reads as
 * clutter rather than as abundance.
 */
export const GROVE_INCLUDES = Object.freeze([
  Object.freeze({
    id: "all-standard",
    short: "All of Press",
    historyFrom: 1978,
    name: "Everything in Cedar Press",
    kind: "rollup",
    shelf: "standard",
    blurb:
      "Every Cedar Press collection, at full history rather than the years Cedar Press opens.",
    linkage:
      "The same entity resolution, with the whole reconstructed identity history behind it rather than the years Cedar Press opens.",
  }),
  Object.freeze({
    id: "all-pro",
    short: "All of Press+",
    historyFrom: 2000,
    name: "Everything in Cedar Press+",
    kind: "rollup",
    shelf: "pro",
    blurb: "The four specialized collections and the reconstructed archive behind every Cedar Press collection.",
    linkage:
      "Contracting, subcontracting, resources and nonprofits, all rolled up to the parent nation or corporation.",
  }),
]);

/**
 * What Grove is beyond the data, for the shelf that has to explain it.
 * Copy, not entitlement: nothing here decides what anyone can open.
 */
/**
 * What Cedar Grove does, rather than what it contains.
 *
 * The contents argument is weak on its own, because a reader who has just
 * been shown eleven collections already believes there is a lot of data. What
 * they cannot see from the shelf is that Grove analyses across all of it,
 * finds things nobody went looking for, opens to a whole organization at
 * once, and keeps growing as Lumecon builds. Every line here is a capability
 * that exists: visualization and cross-collection analysis, findings computed
 * from evidence rather than written by hand (findings.js and leads.js),
 * reproducible outputs (reproduce.js), and the dataset contract that makes
 * "every new one as it lands" a pipeline rather than a promise.
 */
export const GROVE_CAPABILITIES = Object.freeze([
  "Visualization and analysis across every collection at once, with nothing to export first",
  "Findings surfaced from the data itself, including the ones nobody went looking for",
  "Unlimited users on one licence, in an organization of any size",
  "Context for your organization, so answers arrive in your terms",
  "Every dataset Lumecon builds from here, and the public data behind our modeling of Indian Country, as each one lands",
  "Extraction and reproducible outputs, so a number can be checked and cited",
]);

/**
 * Which collections lead their shelf.
 *
 * A grid of equally weighted objects has no hierarchy, and hierarchy is what
 * separates an intelligence product from a directory. These are the entries
 * that get room and a real preview; the rest of the shelf runs compact
 * beneath them. Only collections with an actual figure appear here: a
 * featured slot filled with a decorative chart is exactly the fake dashboard
 * this page is trying not to be.
 */
export const FEATURED = Object.freeze({
  standard: Object.freeze(["funding", "deals"]),
  pro: Object.freeze(["contractors"]),
  grove: Object.freeze(["gaming"]),
});

/** The collections a tier's shelf carries, in catalog order. */
export function collectionsOnShelf(shelf) {
  return PRESS_CATALOG.filter((entry) => entry.shelf === shelf);
}

