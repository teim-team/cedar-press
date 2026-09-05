/**
 * REVIEW OWNER: Havala
 *
 * PURPOSE
 * The Cedar Press and Cedar Grove ladder: what each tier costs, what it
 * promises, and which collection sits where.
 *
 * "Ladder" is the page's shape, not the products' relationship. Cedar Press is
 * a standalone product and Cedar Grove is a separate one that happens to
 * include all the datasets Press sells, plus a data library and other public
 * data work — `GROVE_PUBLIC_DATA` below is that part of it. So the third band
 * is a different product a reader may move to, not a higher rung of this one,
 * which is why `upgradeFor` marks it `sameProduct: false`.
 *
 * The Press/Grove content split is stated in one vocabulary, the Cedar data
 * workspace's: shelves `standard` and `pro` are what a Cedar Press customer
 * sees (`STOREFRONT_SHELVES` in `code/cedar_publication.py`), and shelf
 * `grove` is where a collection Grove carries and Press does not would sit.
 * Nothing sits there today. Gaming Intelligence did, shown on the shelf as a
 * Grove-exclusive preview, and the owner withdrew that promise on 2026-09-04
 * because the collection is still being built: a preview of work in progress
 * is a promise about a cadence and a scope nobody has measured. The
 * workspace still lists it in the manifest's `excluded`, with its reason, and
 * it comes back to this catalog when the workspace rules it ready. So the
 * catalog is exactly the storefront, twelve collections, and
 * `server/tests/test_access.py` compares this file's shelf assignment against
 * the workspace's so the site cannot move a collection across the boundary
 * on its own authority.
 *
 * The organizing idea is that value is not spread evenly. Each rung carries
 * one or two things that make a particular reader say "obviously I need that
 * one", so the question at every boundary is concrete rather than a count of
 * datasets:
 *
 *   Cedar Press   what happened          advocacy, and a lot of current intelligence
 *   Cedar Press+  what drives it         federal contracting, and the specialized record
 *   Cedar Grove   the whole environment  every collection, and the research tools
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
 * THE CATALOG IS THE STOREFRONT
 * Every collection the ladder is designed around, and every one of them ships:
 * `collection.js` reads the same twelve out of the manifest, with the measured
 * descriptor behind each. A test pins the two sets equal in both directions,
 * so a collection cannot be sold here without a descriptor, or measured there
 * without a place on a shelf.
 *
 * THE NUMBERS IN THE TIER COPY ARE DERIVED
 * "Six collections" and "twelve collections" used to be typed into the
 * promise. A count typed beside the list it counts is a second place for the
 * list to be wrong, so the tier copy that states a number reads it from the
 * catalog through `shelfCount`, and the tests hold the words to the counts.
 */

/** The shelves a Cedar Press subscription can reach, in the workspace's own
 *  vocabulary (`STOREFRONT_SHELVES` in `code/cedar_publication.py`). A
 *  collection on any other shelf is not sold here, whatever the plan. */
export const STOREFRONT_SHELVES = Object.freeze(["standard", "pro"]);

/** Whether a catalog entry is one the storefront sells. */
export function isOnStorefront(entry) {
  return STOREFRONT_SHELVES.includes(entry?.shelf);
}

/** Small counts as words, the way the tier copy spells them. */
const COUNT_WORDS = Object.freeze([
  "no", "one", "two", "three", "four", "five", "six",
  "seven", "eight", "nine", "ten", "eleven", "twelve",
]);
export function spellCount(n) {
  return COUNT_WORDS[n] ?? String(n);
}

/** Capitalised, for the head of a sentence. */
const capitalise = (word) => word[0].toUpperCase() + word.slice(1);

/**
 * The tiers are declared first and the catalog after them, so the counts the
 * tier copy states are computed once the catalog exists (`PRESS_TIERS`, at
 * the foot of this file). `storefront` says whether the tier is a rung of
 * this product: Cedar Grove is not, it is a different product the shelf
 * points at, which is why the shelf page never renders it as a band.
 */
const TIER_DECLARATIONS = Object.freeze([
  Object.freeze({
    id: "press",
    shelf: "standard",
    storefront: true,
    name: "Cedar Press",
    price: 500,
    question: "See what's happening.",
    promise:
      "Follow the money, policy, transactions, institutions and public actions across Indian Country.",
    // No year in this note any more. Each collection reaches back a different
    // distance and every one of those distances is measured and stated on the
    // collection itself, so a single sentence here could only be wrong.
    coverageNote: (count) => `${capitalise(spellCount(count))} collections, every year Cedar holds of each.`,
  }),
  Object.freeze({
    id: "press_pro",
    shelf: "pro",
    storefront: true,
    name: "Cedar Press+",
    price: 1000,
    question: "Understand the systems behind it.",
    // The whole tier, said here rather than left to the question. "Systems"
    // says nothing about which collections arrive, and which collections
    // arrive is now the entire difference between this tier and the one
    // below. Every pro-shelf collection is named: a promise that omits one
    // undersells the tier, and there is no second axis left to carry it. The
    // count is derived and a test holds the names to the shelf.
    promise: (count) =>
      `${capitalise(spellCount(count))} more collections on top of Cedar Press: federal contracting, subcontracting, resource revenue, individually owned Native businesses, enterprise structures and the nonprofit sector.`,
    coverageNote: (count, total) =>
      `${capitalise(spellCount(total))} collections, at the same depth as Cedar Press.`,
  }),
  Object.freeze({
    id: "grove",
    shelf: "grove",
    storefront: false,
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
 * ONE COVERAGE FIELD, AND IT IS NOT ALWAYS A YEAR
 * `coverage` says what the collection covers, in one of two shapes:
 *
 *   { kind: "series", from: 1994 }              a run of years
 *   { kind: "roster", captured: "2026-09-01" }  who is on the list, as of
 *
 * The same value for every tier that opens the collection at all, because no
 * tier clips the years any more. There used to be two fields, `standardFrom`
 * (2010 on every Cedar Press collection) and a deeper `historyFrom`, and the
 * gap between them was the second thing an upgrade bought.
 *
 * WHY IT IS A SHAPE AND NOT A NUMBER
 * Two of these collections are rosters. Their source publishes who is
 * certified, or exempt, NOW, and archives nothing: the TERO and commerce
 * offices behind Owned keep no superseded lists, and the IRS Business Master
 * File behind Nonprofits states the organizations that exist today, not the
 * ones that existed in 2004. A field that is always a year forces those two
 * to name one, and the only years available are accidents — one live
 * certification that started in 1992, one defunct filer whose last return was
 * 1983. Neither is a span anybody is covered for. So a roster is a
 * first-class value that states its capture date and no "from" at all.
 *
 * COVERAGE IS NOT min(year)
 * This is the mistake this field has now made twice, in both directions. A
 * minimum is the earliest row present; coverage is what the collection
 * systematically holds, and the two differ whenever the earliest rows are a
 * defect or the wrong kind of event:
 *
 *   subcontracting  min 2001, coverage 2010. The 51 pre-2010 rows are filer
 *                   typos flagged `action_date_precedes_ffata_flag`; FFATA's
 *                   reporting threshold makes 2010 a statutory floor.
 *
 * Where a dataset documents an exclusion flag, the floor is measured AFTER
 * applying it and the comment names the flag, so the next person can re-run
 * the measurement rather than trusting the number. The floors that need no
 * flag say which column they are the minimum of, for the same reason.
 *
 * The other direction was the old hand-typed `historyFrom`, which promised
 * three spans the delivered data does not hold: funding said 2001 and starts
 * in FY2007, NAGPRA said 1990 (the statute) and starts in 1994, lobbying said
 * 1998 (the first LDA year) and starts in 1999.
 *
 * Everything below was measured on 2026-09-02 against the file a subscriber
 * receives, `dist/customer/<id>.csv`. A value here is a claim to a paying
 * customer. It is not editable without re-measuring.
 */
export const PRESS_CATALOG = Object.freeze([
  Object.freeze({
    id: "funding",
    short: "Federal Funding",
    name: "Federal Funding to Indian Country",
    shelf: "standard",
    // Series. Floor: min(fiscal_year) in dist/customer/funding.csv, which is
    // FY2007. The earliest action_date is in October 2006 and belongs to
    // FY2007's first quarter, so 2006 would claim a calendar year Cedar has
    // three months of. The old catalog claimed 2001, which is in no file.
    coverage: Object.freeze({ kind: "series", from: 2007 }),
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
    // Series. Floor: min(notice_date) in dist/customer/federal-register.csv.
    coverage: Object.freeze({ kind: "series", from: 1994 }),
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
    // Series. Floor: min(introduced_date) in dist/customer/legislation.csv:
    // real bills of the 93rd Congress. Thin and gapped through the 1980s
    // (docs/datasets/10_bills_votes.md records the interior gap at 1974), so
    // this is the year the record opens, not a dense series from 1973.
    coverage: Object.freeze({ kind: "series", from: 1973 }),
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
    // Series. Floor: min(Event_Year) in dist/customer/deals.csv.
    coverage: Object.freeze({ kind: "series", from: 2000 }),
    // CANONICAL. Must match cedar_publication.DATASET_DEFINITION["deals"]
    // verbatim; 1169's release gate fails the build if it drifts.
    blurb:
      "Material transactions and capital commitments involving Native nations, organizations and enterprises, including acquisitions, divestitures, property purchases, investments, financing agreements, bond issuances, joint ventures and major capital projects. Track who participated, the Native entity involved, announced value, status and timing, and compare activity across periods.",
    linkage:
      "Buyers, sellers, borrowers and issuers resolved to tribal governments, tribally owned enterprises, ANCs and NHOs.",
  }),
  Object.freeze({
    id: "nagpra",
    short: "NAGPRA",
    name: "NAGPRA",
    shelf: "standard",
    // Series. Floor: min(publication_year) in dist/customer/nagpra.csv. The
    // old catalog claimed 1990, which is when NAGPRA was enacted; the first
    // notice under it published in 1994.
    coverage: Object.freeze({ kind: "series", from: 1994 }),
    blurb:
      "Activity under the Native American Graves Protection and Repatriation Act: notices, inventories and completed repatriations. Track an institution's progress or a nation's outstanding claims, item by item.",
    linkage:
      "Notices matched to the tribes and Native Hawaiian organizations named in them, across the naming changes of three decades.",
  }),
  Object.freeze({
    id: "lobbying",
    short: "Advocacy",
    name: "Native Federal Advocacy & Engagement",
    shelf: "standard",
    // Series. Floor: min(filing_year) in dist/customer/lobbying.csv. The old
    // catalog claimed 1998, the first year the LDA required filings; Cedar's
    // earliest filing is 1999.
    coverage: Object.freeze({ kind: "series", from: 1999 }),
    // CANONICAL. Must match cedar_publication.DATASET_DEFINITION["lobbying"]
    // verbatim; 1169's release gate fails the build if it drifts.
    blurb:
      "Documented federal advocacy and engagement involving Native nations and organizations, including registered lobbying, agency meetings, tribal consultations, regulatory comments, congressional testimony and nonprofit lobbying disclosures. Each row represents one entity-linked activity or source record.",
    linkage:
      "Each activity, from a lobbying registration to a consultation, a docket filing or testimony, keyed to the tribe or Native organization behind it where the record names one exactly; a row the record cannot place keeps its printed party name and a blank key rather than a guess.",
  }),
  Object.freeze({
    id: "contractors",
    short: "Prime Contracting",
    name: "Federal Prime Contracting",
    shelf: "pro",
    // Series. Floor: min(fiscal_year) in dist/customer/contractors.csv, and
    // it is a real boundary rather than the edge of a pull: FPDS carries the
    // Native business-type flags on FY1985 records with false on all of them,
    // so Native identification does not exist in the federal record before
    // roughly FY2000 (docs/datasets/native-owned-businesses.md).
    coverage: Object.freeze({ kind: "series", from: 2000 }),
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
    // Series. Floor: min(fiscal_year) in dist/customer/subcontracting.csv
    // AFTER excluding action_date_precedes_ffata_flag = yes.
    //
    // The unfiltered minimum is 2001 and it is a defect, not coverage. FFATA
    // dropped the subaward reporting threshold to $25,000 in October 2010, so
    // FSRS holds nothing before FY2010; the 51 rows dated earlier are filer
    // typos, every one of them filed in 2010 or later, and the flag exists to
    // keep them out of exactly this claim. docs/datasets/02b_subcontracting.md:
    // "They must never be counted as coverage." Excluding them moves the
    // floor to 2010 on the nose, which is the statutory floor.
    coverage: Object.freeze({ kind: "series", from: 2010 }),
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
    // Series. Floor: min(period_start) in dist/customer/natural-resources.csv.
    // Osage headright payments, published retrospectively by the Osage Minerals
    // Council and carried as dated revenue events with amounts.
    coverage: Object.freeze({ kind: "series", from: 1880 }),
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
    // Roster, not a series, so it states no year to be covered from. Every
    // certifying office publishes who is certified NOW and none of them
    // archives a superseded list, so the collection is a capture rather than
    // a span: docs/datasets/native-owned-businesses.md, "A CURRENT SNAPSHOT,
    // not a series."
    //
    // min(certification_start) is 1992, and it is not a coverage year: it is
    // one live certification that happens to have started early. Captured:
    // max(harvest_date) in dist/customer/native-owned-businesses.csv.
    coverage: Object.freeze({ kind: "roster", captured: "2026-09-01" }),
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
    // Roster, not a series. The delivered file is the IRS Business Master
    // File register, one row per EIN, carrying each filer's LATEST period
    // rather than a run of them: docs/datasets/06_nonprofit.md, "A monthly
    // SNAPSHOT, not a series."
    //
    // min(bmf_tax_period) is 1983, and it is one defunct filer's last return,
    // not the start of anything. The annual filings this collection's blurb
    // describes live in np_financials (tax_year 1996-2025, thin to 2000) and
    // are not folded into the delivered file; when they are, this becomes a
    // series and this field should change shape with it. Captured:
    // bmf_vintage_fetched, which is one value across all 12,764 rows.
    coverage: Object.freeze({ kind: "roster", captured: "2026-04-29" }),
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
    // Series. Floor: min(first_observed_year) in dist/customer/nest.csv, which
    // is the earliest year any source named an enterprise or a tie. The runs of
    // source editions are what date a relationship, so this is an observation
    // series with a left edge rather than a roster.
    coverage: Object.freeze({ kind: "series", from: 2016 }),
    blurb:
      "Who owns whom across Indian Country's enterprises: parent nations and corporations, their subsidiaries, holding companies and joint ventures, and how those ties change as entities are created, renamed, acquired and wound down.",
    linkage:
      "This is the structure the rest of the record resolves against, published as a collection in its own right: every tie names the nation or corporation behind it.",
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
    collections: Object.freeze(["natural-resources"]),
  }),
  Object.freeze({
    id: "enterprises",
    name: "Enterprises and Ownership",
    lede: "Who owns what across Indian Country, and how that changes.",
    collections: Object.freeze(["owned", "nest"]),
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
  // sentence that keeps twelve federal-sounding names from reading as
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

/**
 * The earliest year any collection on a shelf reaches back to.
 *
 * Rosters are skipped rather than coerced: a roster states no year, and
 * folding its capture date in here would make "as far back as" read off the
 * date Cedar last harvested a list.
 */
function earliestOnShelf(shelf) {
  const years = PRESS_CATALOG.filter(
    (entry) => entry.shelf === shelf && entry.coverage.kind === "series",
  ).map((entry) => entry.coverage.from);
  return years.length ? Math.min(...years) : null;
}

/**
 * The shelves below, as one badge each.
 *
 * Cedar Press+ does not redraw the Cedar Press collections to say it
 * includes them, and Grove should not redraw twelve. Listing every collection
 * on the top tier made it the busiest band on the page, which reads as
 * clutter rather than as abundance.
 *
 * The years and the counts are derived, not typed. They used to be literals — 1978 on the
 * standard rollup and 2000 on the pro one — and neither was the earliest year
 * of anything: no collection on either shelf began in 1978. A summary of
 * numbers stated elsewhere has to be computed from them or it is a fourth
 * place for them to disagree.
 */
export const GROVE_INCLUDES = Object.freeze([
  Object.freeze({
    id: "all-standard",
    short: "All of Press",
    reachesBackTo: earliestOnShelf("standard"),
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
    reachesBackTo: earliestOnShelf("pro"),
    name: "Everything in Cedar Press+",
    kind: "rollup",
    shelf: "pro",
    blurb: `The ${spellCount(collectionsOnShelf("pro").length)} specialized collections Cedar Press does not carry.`,
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
 * been shown twelve collections already believes there is a lot of data. What
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

/** The collections a tier's shelf carries, in catalog order. */
export function collectionsOnShelf(shelf) {
  return PRESS_CATALOG.filter((entry) => entry.shelf === shelf);
}

/**
 * How many collections a tier opens: its own shelf plus every shelf below it
 * on the storefront. Cedar Grove reaches everything the storefront sells.
 */
export function shelfCount(shelf) {
  const reach = STOREFRONT_SHELVES.indexOf(shelf);
  const reached = reach < 0 ? STOREFRONT_SHELVES : STOREFRONT_SHELVES.slice(0, reach + 1);
  return PRESS_CATALOG.filter((entry) => reached.includes(entry.shelf)).length;
}

/** The catalog's storefront entries, which today is all of it. */
export const STOREFRONT_CATALOG = Object.freeze(PRESS_CATALOG.filter(isOnStorefront));

/**
 * The tiers with their counts filled in. Copy that states a number is a
 * function of the count in `TIER_DECLARATIONS`; it is resolved here, once,
 * so every page reads a finished string and no page can print a number the
 * catalog does not add up to.
 */
export const PRESS_TIERS = Object.freeze(
  TIER_DECLARATIONS.map((tier) => {
    const own = collectionsOnShelf(tier.shelf).length;
    const total = shelfCount(tier.shelf);
    const resolve = (value) => (typeof value === "function" ? value(own, total) : value);
    return Object.freeze({
      ...tier,
      promise: resolve(tier.promise),
      coverageNote: resolve(tier.coverageNote),
    });
  }),
);

