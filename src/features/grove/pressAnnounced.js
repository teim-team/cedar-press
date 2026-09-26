/**
 * REVIEW OWNER: Havala
 *
 * Collections that are announced to this codebase but not released.
 *
 * WHY THIS IS NOT IN pressCatalog.js
 * `PRESS_CATALOG` is the storefront: every entry in it is sold, measured and
 * pinned to a release, and `collection.js`, the release gate (1169) and
 * `server/tests/test_access.py` all hold it to that. The two collections below
 * are written for and not yet published:
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
 * The owner's brief (2026-09-26) is explicit that neither is wired into the
 * catalog until its verified release, entitlement pin and publication approval
 * exist, and that every claim the public page displays is grounded in a
 * current release. So they are declared HERE, once, with the owner's names and
 * descriptions, and nothing on a public page resolves an id from this list.
 * The public resolver (`liveCollection` below) reads the catalog only.
 *
 * THE GATE
 * An id is live when, and only when, the storefront catalog carries it.
 * Launching one of these is therefore: move the entry into `PRESS_CATALOG`
 * (with its measured coverage and shelf), delete it from this list, and let
 * the parity tests (catalog <-> manifest <-> server) tell you what else has to
 * move with it. `pressAudiences.test.js` fails if an id is ever in both.
 *
 * Icons are keyed by these ids in `pressCollectionIcons.jsx`, drawn with the
 * rest of the family; the key is named here as `icon`.
 */
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

/**
 * The ids a public page may resolve. Defaults to the storefront; a test passes
 * its own catalog to see what the page would do once a collection launches.
 */
export function liveIdsOf(catalog = STOREFRONT_CATALOG) {
  return new Set(catalog.map((entry) => entry.id));
}

/**
 * A live catalog entry by id, or null. Never an announced entry: the gate is
 * that this function only ever reads the catalog it is handed.
 */
export function liveCollection(id, catalog = STOREFRONT_CATALOG) {
  return catalog.find((entry) => entry.id === id) ?? null;
}
