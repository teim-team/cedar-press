/**
 * REVIEW OWNER: Havala
 *
 * Collections that are announced to this codebase but not released, and every
 * word the door will say about them at launch.
 *
 * NOTHING THE PAGE LOADS IMPORTS THIS FILE. That is the gate, and it is
 * structural rather than a flag: a module no runtime module imports is not in
 * the bundle, so these names, descriptions and sentences cannot be read out of
 * the shipped JavaScript by anyone with devtools. Foundation & Corporate
 * Giving is still under rights review, and PLOT has no producer. Two checks
 * hold it: `pressJobs.test.js` fails if any non-test module imports this
 * file or `pressAnnouncedIcons.jsx`, and the smoke suite's "the bundle" test
 * greps the production build for every string declared here and for the two
 * icons' path data.
 *
 *   plot                         PLOT. No producer exists in any repository
 *                                yet (checked 2026-09-26).
 *   foundation-corporate-giving  Foundation and corporate giving. Built in
 *                                Lumecon-data (branch
 *                                codex/foundation-corporate-giving), status
 *                                "internal review and unpromoted rehearsal
 *                                only" per docs/foundation-giving-contract.md;
 *                                the grantmaker-database publication ruling is
 *                                still open.
 *
 * WHAT IS HERE
 *   ANNOUNCED_COLLECTIONS  the owner's names and descriptions (2026-09-26)
 *   ANNOUNCED_COLLECTION_JOBS
 *                          the owner's questions for each collection's
 *                          profile, the gated half of `COLLECTION_JOBS`
 *   LAUNCH_COPY            the owner's intelligence sentences that cite
 *                          either collection, keyed by audience id; the page
 *                          shows each audience's interim `now` copy until then
 *   ANNOUNCED_AUDIENCES    audiences that exist only for a gated collection
 *                          (Foundations and philanthropy), with where each
 *                          goes in the selector
 *   pressAnnouncedIcons.jsx  the two marks, drawn with the family
 *
 * LAUNCHING ONE (all in the same change, once the verified release,
 * entitlement pin and publication approval exist):
 *   1. move its entry from ANNOUNCED_COLLECTIONS into `PRESS_CATALOG`, with
 *      its measured coverage and shelf;
 *   2. move its mark from `pressAnnouncedIcons.jsx` into `COLLECTION_ICONS`;
 *   3. move every LAUNCH_COPY entry and ANNOUNCED_AUDIENCES entry whose
 *      collections are now all live into `AUDIENCE_JOBS` as its `atLaunch`;
 *   4. move its ANNOUNCED_COLLECTION_JOBS entry into `COLLECTION_JOBS`, with
 *      the codebook fields each question rests on and the questions Cedar
 *      can answer from its release profile;
 *   5. move its `methods` concepts into Methods and every
 *      ANNOUNCED_ECOSYSTEM_EXAMPLES entry whose collections are now all live
 *      into `ECOSYSTEM_EXAMPLES` (`pressMethod.js`).
 * The catalog entry keeps its `shelf`: Foundation & Corporate Giving in
 * Cedar Press, PLOT in Cedar Press+, a seven and seven split of fourteen.
 * Every count on the site is derived from the catalog, so none needs
 * editing.
 * The tests name each step that was missed: a collection in both places, a
 * live collection with no mark, launch copy left here whose collections are
 * all live, and a live collection with no questions, or questions naming no
 * field its codebook holds, each fail.
 */
import { AUDIENCE_JOBS, liveIdsOf } from "./pressJobs.js";
import { STOREFRONT_CATALOG } from "./pressCatalog.js";

export const ANNOUNCED_COLLECTIONS = Object.freeze([
  Object.freeze({
    id: "plot",
    short: "PLOT",
    name: "PLOT",
    icon: "plot",
    // Owner, 2026-09-26: PLOT launches in Cedar Press+.
    shelf: "pro",
    // What Methods will say about it at launch (owner's concepts).
    methods:
      "Land ownership, transfers, permitting and development, followed parcel by parcel: each parcel and the recorded events attached to it, linked to the Native entity that holds it.",
    // Owner copy, 2026-09-26. Deals follows a transaction or a capital event
    // between parties; PLOT follows a parcel and the recorded events attached
    // to it. A nation's site acquisition may be a Deal while the parcels it
    // bought appear separately in PLOT: link the two, never collapse them.
    blurb:
      "Parcel-level ownership and development records associated with Native nations, organizations and enterprises. Follow ownership, transfers, parcel characteristics, geometry, permits and other recorded property activity over time.",
  }),
  Object.freeze({
    id: "foundation-corporate-giving",
    // HOUSE STYLE, DELIBERATELY NOT APPLIED. The owner wants this name kept
    // with its ampersand. `tests/smoke.spec.js` ("uses no ampersand in visible
    // copy") will fail the day this collection renders, and it should: that
    // is the moment to add a NAMED, deliberate exemption for this one
    // collection name, the way the Quechan register name is exempted. Do not
    // add the exemption before then; an exemption for a name that never
    // renders is the stale-exemption failure that test's own history records.
    short: "Foundation & Corporate Giving",
    name: "Foundation & Corporate Giving",
    icon: "foundation-corporate-giving",
    // Owner, 2026-09-26: it launches in Cedar Press, which with PLOT in
    // Cedar Press+ makes the fourteen a seven and seven split.
    shelf: "standard",
    // What Methods will say about it at launch (owner's concepts).
    methods:
      "Philanthropic, corporate and bank giving, each disclosure kept as its own record: commitments and payments are separate facts, and the legal recipient is kept distinct from the Native beneficiary.",
    // Owner copy, 2026-09-26, bound by the producer contract: one row is one
    // source disclosure or award version; commitments and payments are
    // separate facts; legal recipient and Native beneficiary are separate
    // concepts; a non-Native intermediary does not become a Native entity
    // because a grant benefits Native people; possible duplicates are never
    // silently summed.
    blurb:
      "Foundation, corporate and bank funding publicly disclosed for Native nations, organizations and initiatives. Follow the funder, legal recipient, purpose, geography, amount and timing while keeping commitments, payments, authorizations and other reported financial statuses distinct.",
  }),
]);

export const ANNOUNCED_IDS = Object.freeze(ANNOUNCED_COLLECTIONS.map((entry) => entry.id));

/**
 * Worked examples of collections combining (Methods' `ECOSYSTEM_EXAMPLES`)
 * that need a gated collection. They join that list at launch.
 */
export const ANNOUNCED_ECOSYSTEM_EXAMPLES = Object.freeze([
  Object.freeze({
    collections: Object.freeze(["deals", "plot"]),
    text: "A site acquisition recorded in Indian Country Deals links to the parcels PLOT follows, so a transaction and the land it bought read together without being collapsed into one record.",
  }),
  Object.freeze({
    collections: Object.freeze(["foundation-corporate-giving", "funding", "nonprofits"]),
    text: "Foundation, corporate and bank giving read beside federal funding and the Native Nonprofits roster shows how an organization's private and public support combine, with the legal recipient and the Native beneficiary kept apart.",
  }),
]);

/** Whether an id is announced and not yet released. */
export function isAnnounced(id) {
  return ANNOUNCED_IDS.includes(id);
}

/** Whether an id is one a use case may cite: released, or deliberately gated. */
export function isCitable(id, catalog = STOREFRONT_CATALOG) {
  return liveIdsOf(catalog).has(id) || isAnnounced(id);
}

/**
 * The owner's questions (2026-09-26) for each announced collection's profile.
 * No `fields` yet: neither collection has a codebook in this repository, so
 * there is nothing to check a question against. Moving one into
 * `COLLECTION_JOBS` at launch requires them (step 4 above).
 */
export const ANNOUNCED_COLLECTION_JOBS = Object.freeze({
  "foundation-corporate-giving": Object.freeze({
    questions: Object.freeze([
      "Which funders support organizations like this one?",
      "What purposes and geographies are receiving disclosed private funding?",
      "How does private giving compare with federal support?",
    ]),
  }),
  plot: Object.freeze({
    questions: Object.freeze([
      "Where does this entity hold or acquire property?",
      "What permits or development activity are associated with those parcels?",
      "How has recorded activity around a property changed over time?",
    ]),
  }),
});

/**
 * The owner's intelligence sentences (2026-09-26) that cite a gated
 * collection, by audience id, with the evidence each will cite at launch.
 * Each audience's outcome is not gated and lives with it in `AUDIENCE_JOBS`.
 */
export const LAUNCH_COPY = Object.freeze({
  "ancs-nhos": Object.freeze({
    explanation: "Track subsidiaries, joint ventures, federal business, major transactions and property activity to see where peer organizations are expanding and where new opportunities may be forming.",
    collections: Object.freeze(["need", "contractors", "subcontracting", "deals", "plot"]),
  }),
  "banks-lenders": Object.freeze({
    explanation: "Understand ownership, federal business, funding relationships, transactions and property activity before financing, investing in or partnering with a Native enterprise.",
    collections: Object.freeze(["need", "contractors", "funding", "deals", "plot"]),
  }),
  journalists: Object.freeze({
    explanation: "Follow organizations and events across funding, policy, advocacy, ownership, land and transactions while keeping the underlying source attached.",
    collections: Object.freeze(["funding", "federal-register", "lobbying", "need", "plot", "deals"]),
  }),
  "native-nonprofits": Object.freeze({
    explanation: "See which funders support peer organizations, how similar nonprofits combine federal and private support, and where your own funding mix differs before pursuing the next grant.",
    collections: Object.freeze(["nonprofits", "funding", "foundation-corporate-giving", "lobbying"]),
  }),
});

/** Audiences that exist only for a gated collection, and where each goes. */
export const ANNOUNCED_AUDIENCES = Object.freeze([
  Object.freeze({
    after: "native-nonprofits",
    audience: Object.freeze({
      id: "foundations-philanthropy",
      audience: "Foundations and philanthropy",
      // "Capital allocation" in the owner's note; the nearest job in the
      // shared vocabulary.
      job: "Investment opportunity",
      // Owner copy, revised 2026-09-26.
      outcome: "Put need and existing support in context before allocating capital.",
      // The owner's caution: the collections show observable indicators of
      // funding, activity, service footprint and organizational presence,
      // and must not claim a definitive need score. The owner asked for the
      // body to say so; this sentence is written for review, 2026-09-26.
      atLaunch: Object.freeze({
        explanation: "Compare disclosed private giving with federal support and see which organizations and places already attract funding. Cedar Press shows observable public and private funding and activity, not a need score.",
        collections: Object.freeze(["foundation-corporate-giving", "funding", "nonprofits"]),
      }),
      now: null,
      // The owner's list: health, housing, education, community services.
      // Lumecon's health and education photographs show faces.
      imagePool: Object.freeze(["otherservices", "realestate"]),
    }),
  }),
]);

/**
 * The page's audiences as they will stand at launch: each gated sentence
 * restored as its audience's `atLaunch`, and each gated audience put back in
 * its place. What `pressJobs.js`'s own gate then does with them is the
 * runtime code, unchanged.
 */
export function withLaunchCopy(audiences = AUDIENCE_JOBS) {
  const merged = [];
  for (const audience of audiences) {
    const launch = LAUNCH_COPY[audience.id];
    merged.push(launch ? Object.freeze({ ...audience, atLaunch: launch }) : audience);
    for (const extra of ANNOUNCED_AUDIENCES) {
      if (extra.after === audience.id) merged.push(extra.audience);
    }
  }
  return Object.freeze(merged);
}

/** The catalog as it would stand with every announced collection launched. */
export function launchedCatalog(ids = ANNOUNCED_IDS, catalog = STOREFRONT_CATALOG) {
  return Object.freeze([
    ...catalog,
    ...ANNOUNCED_COLLECTIONS.filter((entry) => ids.includes(entry.id)),
  ]);
}

/** Every string declared here that must never reach the shipped bundle. */
export function gatedPhrases() {
  const out = new Set();
  for (const entry of ANNOUNCED_COLLECTIONS) {
    for (const value of [entry.id, entry.short, entry.name, entry.blurb, entry.methods]) out.add(value);
  }
  for (const example of ANNOUNCED_ECOSYSTEM_EXAMPLES) out.add(example.text);
  for (const jobs of Object.values(ANNOUNCED_COLLECTION_JOBS)) {
    for (const question of jobs.questions) out.add(question);
  }
  const shipped = new Set(AUDIENCE_JOBS.flatMap((audience) => [audience.now?.explanation, audience.atLaunch?.explanation]));
  for (const copy of Object.values(LAUNCH_COPY)) {
    // Only sentences the page does not already say are secrets.
    if (!shipped.has(copy.explanation)) out.add(copy.explanation);
  }
  for (const { audience } of ANNOUNCED_AUDIENCES) {
    out.add(audience.id);
    out.add(audience.audience);
    out.add(audience.outcome);
    out.add(audience.atLaunch.explanation);
  }
  return [...out];
}
