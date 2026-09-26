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
 * hold it: `pressAudiences.test.js` fails if any non-test module imports this
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
 *   LAUNCH_COPY            the owner's use-case sentences that cite either
 *                          collection, keyed by audience id; the page shows
 *                          each audience's interim `now` copy until then
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
 *      collections are now all live into `PRESS_AUDIENCES` as its `atLaunch`.
 * The tests name each step that was missed: a collection in both places, a
 * live collection with no mark, and launch copy left here whose collections
 * are all live each fail.
 */
import { PRESS_AUDIENCES, liveIdsOf } from "./pressAudiences.js";
import { STOREFRONT_CATALOG } from "./pressCatalog.js";

export const ANNOUNCED_COLLECTIONS = Object.freeze([
  Object.freeze({
    id: "plot",
    short: "PLOT",
    name: "PLOT",
    icon: "plot",
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

/** Whether an id is announced and not yet released. */
export function isAnnounced(id) {
  return ANNOUNCED_IDS.includes(id);
}

/** Whether an id is one a use case may cite: released, or deliberately gated. */
export function isCitable(id, catalog = STOREFRONT_CATALOG) {
  return liveIdsOf(catalog).has(id) || isAnnounced(id);
}

/**
 * The owner's sentences (2026-09-26) that cite a gated collection, by audience
 * id. Two are EXTENDED from the owner's text so every collection has a home,
 * marked where they are.
 */
export const LAUNCH_COPY = Object.freeze({
  // EXTENDED: "and resource revenue" added so Natural Resources has a home.
  // Advocacy carries "agency and congressional activity", so the Federal
  // Register chip made way for it; the Register stays on Journalists and
  // Advisors. "Associated with" implies no payment chain the royalty records
  // do not establish.
  "tribal-nations": Object.freeze({
    use: "Review federal and philanthropic funding and resource revenue associated with your nation, follow relevant agency and congressional activity, and connect enterprise and property records to the same Native entities.",
    collections: Object.freeze(["funding", "foundation-corporate-giving", "natural-resources", "lobbying", "plot"]),
  }),
  "ancs-nhos": Object.freeze({
    use: "Follow subsidiaries and joint ventures, federal contracting, announced transactions and property activity across an enterprise network.",
    collections: Object.freeze(["need", "contractors", "subcontracting", "deals", "plot"]),
  }),
  "banks-lenders": Object.freeze({
    use: "Resolve an organization to the Native entity and enterprise structure behind it, then review federal business, public funding, announced financings and parcel activity as part of diligence.",
    collections: Object.freeze(["need", "contractors", "funding", "deals", "plot"]),
  }),
  "native-nonprofits": Object.freeze({
    use: "Compare an organization's public record with federal assistance and disclosed private giving, research prospective funders, and examine funding relationships among peer organizations.",
    collections: Object.freeze(["nonprofits", "funding", "foundation-corporate-giving", "lobbying"]),
  }),
  journalists: Object.freeze({
    use: "Start with a nation, organization or event and follow the underlying record across policy, money, organizations, property and transactions while retaining the original sources.",
    collections: Object.freeze(["federal-register", "lobbying", "deals", "foundation-corporate-giving", "plot"]),
  }),
  advisors: Object.freeze({
    use: "Build a sourced picture of an organization, market or project before diligence, strategy work, negotiations or client outreach.",
    collections: Object.freeze(["need", "deals", "federal-register", "lobbying", "plot"]),
  }),
});

/** Audiences that exist only for a gated collection, and where each goes. */
export const ANNOUNCED_AUDIENCES = Object.freeze([
  Object.freeze({
    after: "native-nonprofits",
    audience: Object.freeze({
      id: "foundations-philanthropy",
      label: "Foundations and philanthropy",
      atLaunch: Object.freeze({
        use: "See which Native nations and organizations appear in disclosed private giving, compare philanthropic activity with federal funding, and examine funding patterns by recipient, geography and purpose.",
        collections: Object.freeze(["foundation-corporate-giving", "nonprofits", "funding"]),
      }),
      now: null,
    }),
  }),
]);

/**
 * The page's audiences as they will stand at launch: each gated sentence
 * restored as its audience's `atLaunch`, and each gated audience put back in
 * its place. What `pressAudiences.js`'s own gate then does with them is the
 * runtime code, unchanged.
 */
export function withLaunchCopy(audiences = PRESS_AUDIENCES) {
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
    ...ANNOUNCED_COLLECTIONS.filter((entry) => ids.includes(entry.id)).map((entry) => ({ ...entry, shelf: "pro" })),
  ]);
}

/** Every string declared here that must never reach the shipped bundle. */
export function gatedPhrases() {
  const out = new Set();
  for (const entry of ANNOUNCED_COLLECTIONS) {
    for (const value of [entry.id, entry.short, entry.name, entry.blurb]) out.add(value);
  }
  for (const copy of Object.values(LAUNCH_COPY)) {
    // The advisors sentence is the owner's and ships today as interim copy;
    // only sentences the page does not already say are secrets.
    if (!PRESS_AUDIENCES.some((audience) => audience.now?.use === copy.use)) out.add(copy.use);
  }
  for (const { audience } of ANNOUNCED_AUDIENCES) {
    out.add(audience.id);
    out.add(audience.label);
    out.add(audience.atLaunch.use);
  }
  return [...out];
}
