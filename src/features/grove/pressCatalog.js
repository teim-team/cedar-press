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
 *   Cedar Press+  what drives it         federal contracting, and the specialized record
 *   Cedar Grove   the whole environment  gaming intelligence, and the research tools
 *
 * THE BASE TIER IS THE PRODUCT
 * It is named "Cedar Press", not "Cedar Press Standard", because a tier called
 * Standard sitting under a product called Cedar Press makes a reader work out
 * which of the two they are looking at. The upgrade is "Cedar Press+", and the
 * page sets that plus raised at display size only.
 *
 * ONE AXIS: WHICH COLLECTIONS YOU GET
 * A reader can be short of a collection. That is the only thing an upgrade
 * fixes. Cedar Press carries its six collections for every year Cedar holds;
 * Cedar Press+ adds six more, at the same depth.
 *
 * This used to be two axes. Cedar Press was capped at 2010 and Cedar Press+
 * sold the years behind that cap as the other half of its value, so every
 * collection carried both a `standardFrom` and a deeper `historyFrom` and the
 * page had to work out which of the two meanings of "upgrade" applied. That
 * was retired on the owner's ruling of 2026-09-02: the year cap was invented
 * to give Cedar Press+ something to sell, it made the cheaper tier worse for
 * no reason Cedar could point at in the data, and two axes made every
 * coverage sentence on the site conditional on a tier. One axis is the
 * cleaner promise and the honest one, so `coverageFrom` is now a single
 * number per collection and no tier changes it.
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

export const PRESS_TIERS = Object.freeze([
  Object.freeze({
    id: "press",
    shelf: "standard",
    name: "Cedar Press",
    price: 500,
    question: "See what's happening.",
    promise:
      "Follow the money, policy, transactions, institutions and public actions across Indian Country.",
    // No year in this note any more. Each collection reaches back a different
    // distance and every one of those distances is measured and stated on the
    // collection itself, so a single sentence here could only be wrong.
    coverageNote: "Six collections, every year Cedar holds of each.",
  }),
  Object.freeze({
    id: "press_pro",
    shelf: "pro",
    name: "Cedar Press+",
    price: 1000,
    question: "Understand the systems behind it.",
    // The whole tier, said here rather than left to the question. "Systems"
    // says nothing about which collections arrive, and which collections
    // arrive is now the entire difference between this tier and the one
    // below. All six pro-shelf collections are named: a promise that omits
    // one undersells the tier, and there is no second axis left to carry it.
    promise:
      "Six more collections on top of Cedar Press: federal contracting, subcontracting, resource revenue, individually owned Native businesses, enterprise structures and the nonprofit sector.",
    coverageNote: "Twelve collections, at the same depth as Cedar Press.",
  }),
  Object.freeze({
    id: "grove",
    shelf: "grove",
    name: "Cedar Grove",
    price: 2500,
    question: "Investigate it yourself.",
    promise:
      "Every Cedar collection, every new one as it lands and the harmonized public data your work already runs on. Grove is where you visualize it, analyze it and put it in front of your whole organization.",
    coverageNote: "Everything, with the tools to query it.",
  }),
]);

/**
 * Every collection the ladder is designed around.
 *
 * `short` is the name on a badge, where a full title will not fit in a square.
 *
 * ONE COVERAGE FIELD, AND IT IS MEASURED
 * `coverageFrom` is the earliest year the collection actually holds — the
 * same number for every tier that opens the collection at all, because no
 * tier clips the years any more.
 *
 * There used to be two fields, `standardFrom` (2010 on every Cedar Press
 * collection) and a deeper `historyFrom`. Collapsing them was not a rename:
 * `historyFrom` was hand-typed and three of its numbers were promises the
 * delivered data does not keep — funding said 2001 and starts in FY2007,
 * NAGPRA said 1990 and starts in 1994, lobbying said 1998 and starts in
 * 1999. Every number below was measured on 2026-09-02 against the file a
 * subscriber receives, `dist/customer/<id>.csv`, and the column measured is
 * named beside it so the next reader can re-run the check rather than trust
 * this comment. Where the old catalog and the data disagreed, the data won.
 *
 * A number here is a claim to a paying customer. It is not editable without
 * re-measuring.
 */
export const PRESS_CATALOG = Object.freeze([
  Object.freeze({
    id: "funding",
    short: "Federal Funding",
    name: "Federal Funding to Indian Country",
    shelf: "standard",
    // Measured: min(fiscal_year) in dist/customer/funding.csv.
    // The catalog claimed 2001. USAspending assistance plus the FAADS
    // backfill begins at FY2007 in the delivered file; 2001 was never in it.
    coverageFrom: 2007,
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
    // Measured: min(notice_date) in dist/customer/federal-register.csv.
    coverageFrom: 1994,
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
    // Measured: min(introduced_date) in dist/customer/legislation.csv.
    // Real bills of the 93rd Congress, not a stray date.
    coverageFrom: 1973,
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
    // Measured: min(Event_Year) in dist/customer/deals.csv.
    coverageFrom: 2000,
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
    // Measured: min(publication_year) in dist/customer/nagpra.csv.
    // The catalog claimed 1990, the year NAGPRA was enacted. The notices
    // Cedar carries start with the first ones published, in 1994.
    coverageFrom: 1994,
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
    // Measured: min(filing_year) in dist/customer/lobbying.csv.
    // The catalog claimed 1998, the first LDA year. Cedar's filings start in 1999.
    coverageFrom: 1999,
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
    // Measured: min(fiscal_year) in dist/customer/contractors.csv.
    coverageFrom: 2000,
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
    // Measured: min(fiscal_year) in dist/customer/subcontracting.csv.
    coverageFrom: 2001,
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
    // Measured: min(period_start) in dist/customer/natural-resources.csv.
    // Osage headright payments, published retrospectively by the Osage
    // Minerals Council and carried as dated revenue events.
    coverageFrom: 1880,
    blurb:
      "Energy and mineral activity on trust and restricted lands: production volumes, the royalties it owes and the disbursements that follow. See what a commodity produced, what it paid and where the money went.",
    linkage:
      "Production and disbursements matched to the nations and allottees they belong to.",
  }),
  Object.freeze({
    id: "owned",
    short: "Native-Owned Businesses",
    name: "Individually Owned Native Businesses",
    shelf: "pro",
    // Measured: min(certification_start) in dist/customer/native-owned-businesses.csv.
    // The earliest certification a nation's office states, not the harvest
    // date: this is a register of live certifications, and 2,044 of them
    // were first seen by Cedar in 2026.
    coverageFrom: 1992,
    blurb:
      "Individually owned Native businesses, certified by their own nations' TERO and commerce offices and shared with the project office by office. The businesses no federal register counts: who they are, what trades they work and what preference status their nation certifies.",
    linkage:
      "Every listing carries the nation whose office certified it, appears only under that nation's stated terms, and is credited to the issuing TERO or commerce office.",
  }),
  Object.freeze({
    id: "nonprofits",
    short: "Native Nonprofits",
    name: "Native Nonprofits",
    shelf: "pro",
    // Measured: min(bmf_tax_period) in dist/customer/nonprofits.csv.
    // The earliest BMF financial period in the delivered register, which is a
    // current snapshot carrying one period per EIN rather than an annual
    // panel, so 1983 is one defunct filer's last return and not the start of
    // a series. The year-over-year filings the blurb promises live in the
    // collection's np_financials table, whose earliest tax_year is 1996; that
    // table is not folded into the delivered file. Whichever number the page
    // should show, 1983 is the one measurable in what a subscriber receives.
    coverageFrom: 1983,
    blurb:
      "Native-led and Native-serving nonprofits with their annual federal filings. Compare budgets, revenue mixes, program spending and how an institution's finances move year over year.",
    linkage:
      "Filers classified as Native-led, Native-serving or Native-focused, which are three different things and are labeled separately.",
  }),
  Object.freeze({
    id: "nest",
    short: "NEST",
    name: "Native Enterprise Structures and Ties",
    shelf: "pro",
    // Measured: min(first_observed_year) in dist/customer/nest.csv.
    // The earliest source edition a published ownership tie was observed in.
    coverageFrom: 2016,
    blurb:
      "Who owns whom across Indian Country's enterprises: parent nations and corporations, their subsidiaries, holding companies and joint ventures, and how those ties change as entities are created, renamed, acquired and wound down.",
    linkage:
      "This is the structure the rest of the record resolves against, published as a collection in its own right: every tie names the nation or corporation behind it.",
  }),
  Object.freeze({
    id: "gaming",
    short: "Gaming",
    name: "Gaming Intelligence",
    shelf: "grove",
    // Measured: min(open_date) in dist/customer/gaming.csv.
    // A facility open date, and the earliest four are flagged
    // `open_date_predates_tribal_gaming_era`. The earliest unflagged one is
    // 1979; the catalog's old 1988 was IGRA's year, not the record's.
    coverageFrom: 1905,
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
  // The door-sized version, for the gate's collection-name strip: the one
  // sentence that keeps eleven federal-sounding names from reading as
  // keyword filters over open data. Same discipline as `claim`: connected
  // to the Native entities each record touches, never "every record is
  // Native", which the counterparties would break.
  door:
    "Not keyword filters: every collection is connected to the tribal governments, tribal enterprises, ANCs, NHOs and Native organizations it touches, with names, ownership and affiliations maintained over time.",
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

/** The earliest year any collection on a shelf reaches back to. */
function earliestOnShelf(shelf) {
  return Math.min(
    ...PRESS_CATALOG.filter((entry) => entry.shelf === shelf).map((entry) => entry.coverageFrom),
  );
}

/**
 * The shelves below, as one badge each.
 *
 * Cedar Press+ does not redraw the Cedar Press collections to say it
 * includes them, and Grove should not redraw eleven. Listing every collection
 * on the top tier made it the busiest band on the page, which reads as
 * clutter rather than as abundance.
 *
 * The years are derived, not typed. They used to be literals — 1978 on the
 * standard rollup and 2000 on the pro one — and neither was the earliest year
 * of anything: no collection on either shelf began in 1978. A summary of
 * numbers stated elsewhere has to be computed from them or it is a fourth
 * place for them to disagree.
 */
export const GROVE_INCLUDES = Object.freeze([
  Object.freeze({
    id: "all-standard",
    short: "All of Press",
    coverageFrom: earliestOnShelf("standard"),
    name: "Everything in Cedar Press",
    kind: "rollup",
    shelf: "standard",
    blurb: "Every Cedar Press collection, for every year Cedar holds of each.",
    linkage:
      "The same entity resolution, with the whole reconstructed identity history behind it.",
  }),
  Object.freeze({
    id: "all-pro",
    short: "All of Press+",
    coverageFrom: earliestOnShelf("pro"),
    name: "Everything in Cedar Press+",
    kind: "rollup",
    shelf: "pro",
    blurb: "The six specialized collections Cedar Press does not carry.",
    linkage:
      "Contracting, subcontracting, resources, individually owned Native businesses, enterprise structures and nonprofits: awards roll up to the parent nation or corporation, and each owned business carries its certifying nation.",
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

