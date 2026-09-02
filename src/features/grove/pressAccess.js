/**
 * REVIEW OWNER: Havala
 *
 * PURPOSE
 * Who may read Cedar Press, and how much of the collection they get.
 *
 * Cedar Press is a standalone product, not a rung on the platform ladder and
 * not a Cedar Grove surface. It is sold through Tribal Business News: an
 * eligible membership issues an access code, the code creates the account.
 *
 * Cedar Grove does not include Cedar Press, and neither does Tree. This used
 * to return true for both, which meant a Grove licensee was shown a page
 * nobody sold them and the copy told readers their Grove plan covered it.
 *
 * THREE SHELVES
 * A dataset sits on one of them, and that is the only access fact about it:
 *
 *   standard  every Cedar Press reader
 *   pro       Cedar Press+ and above
 *   grove     Cedar Grove only, and never on Cedar Press
 *
 * The shelves nest upward, so Cedar Press+ sees standard and pro, and Grove
 * sees all
 * three. A capped dataset is shown rather than hidden: a reader should be able
 * to see what exists and what it would take to open it. `upgradeFor` names the
 * product that opens a given shelf, so the prompt in the card can say which
 * one rather than "upgrade".
 *
 * No prices here. Prices belong to the marketing site and to whatever the
 * working session settles; entitlement code carrying a number goes stale the
 * first time one moves.
 *
 * This is the client-side affordance in the same sense as
 * pages/cedarGroveModel.js: it decides what renders. The server's
 * tierCapabilities is the control once press data moves behind endpoints, and
 * the two must answer identically.
 *
 * WHO ANSWERS
 * The session payload carries the server's resolution as `user.press`
 * ({ canRead, shelfReach }, from tierCapabilities.pressShelfReach), and when
 * it is present it is the answer: a renewal or a capability change on the
 * server reaches the browser through the payload rather than waiting for a
 * client release. The tier map below is the fallback for a payload written
 * before the field existed, and it must stay identical to the server's.
 */

import { resolveTier } from "../../workspaceTier.js";
import { PRESS_CATALOG_BY_ID } from "./pressCatalog.js";

/** The shelves, lowest first. A dataset declares exactly one. */
export const SHELF = Object.freeze({
  STANDARD: "standard",
  PRO: "pro",
  GROVE: "grove",
});

const SHELF_ORDER = [SHELF.STANDARD, SHELF.PRO, SHELF.GROVE];

// How far up the shelves each plan reaches. A plan absent from this map
// reaches nothing, which is the safe answer for an unknown or lapsed tier.
const PLAN_REACH = Object.freeze({
  press: SHELF.STANDARD,
  press_pro: SHELF.PRO,
  grove: SHELF.GROVE,
});

/** Whether this user's plan includes the Cedar Press page at all. */
export function canReadCedarPress(user) {
  if (typeof user?.press?.canRead === "boolean") return user.press.canRead;
  const tier = resolveTier(user);
  return tier === "press" || tier === "press_pro";
}

/** How far up the shelves this user reaches, or null for no reach at all. */
export function shelfReach(user) {
  // The server's resolution when the payload carries one. An unrecognized
  // value reaches nothing, the same safe answer as an unknown tier.
  if (user?.press && "shelfReach" in user.press) {
    const reach = user.press.shelfReach;
    return SHELF_ORDER.includes(reach) ? reach : null;
  }
  return PLAN_REACH[resolveTier(user)] ?? null;
}

/**
 * Whether this user can open a dataset. A dataset with no declared shelf is
 * treated as pro rather than standard: a new entry that nobody has classified
 * should not fall open by default.
 */
export function canOpenDataset(user, dataset) {
  const reach = shelfReach(user);
  if (!reach) return false;
  const need = SHELF_ORDER.indexOf(shelfOf(dataset));
  if (need < 0) return false;
  return SHELF_ORDER.indexOf(reach) >= need;
}

/**
 * The product that opens a shelf, for the prompt on a capped card. Grove-only
 * datasets are never opened by a Cedar Press plan, which is why the Grove
 * shelf names a different product rather than a higher rung of this one.
 */
export function upgradeFor(dataset) {
  const shelf = shelfOf(dataset);
  if (shelf === SHELF.GROVE) {
    return { id: "grove", name: "Cedar Grove", sameProduct: false };
  }
  return { id: "press_pro", name: "Cedar Press+", sameProduct: true };
}

/**
 * A dataset's shelf, from the dataset or from the catalog it is listed in.
 * Unclassified means pro, never standard: an entry nobody has placed must not
 * fall open to the cheapest plan.
 */
function shelfOf(dataset) {
  if (!dataset) return SHELF.PRO;
  return dataset.shelf || PRESS_CATALOG_BY_ID[dataset.id]?.shelf || SHELF.PRO;
}

/**
 * The earliest year a collection holds, or null if it does not state one.
 *
 * THERE IS NO SECOND AXIS
 * There used to be a `historyFor(user, dataset)` here, because Cedar Press
 * was capped at 2010 and Cedar Press+ sold the years behind the cap. Coverage
 * was therefore a function of the reader as well as of the collection, and
 * three of the page's sentences existed only to say which of the two an
 * upgrade would fix. The cap was retired on 2026-09-02 (see
 * `pressCatalog.js`), so coverage is now a property of the collection alone
 * and takes no user: whoever can open a collection gets all of it.
 *
 * A collection is still capped in the only sense left — a reader whose shelf
 * does not reach it cannot open it at all — and that question is
 * `canOpenDataset`, which is where it always belonged.
 */
export function coverageFrom(dataset) {
  if (!dataset) return null;
  const value = dataset.coverageFrom ?? PRESS_CATALOG_BY_ID[dataset.id]?.coverageFrom;
  return Number.isInteger(value) ? value : null;
}
