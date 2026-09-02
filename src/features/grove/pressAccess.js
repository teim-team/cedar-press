/**
 * REVIEW OWNER: Havala
 *
 * PURPOSE
 * Who may read Cedar Press, and how much of the collection they get.
 *
 * Cedar Press is a standalone product, not a rung on the platform ladder and
 * not a Cedar Grove surface. It is sold through Tribal Business News: an
 * eligible membership issues an access code, the code creates the account.
 * Cedar Grove is a superset of it by content — Grove carries all the datasets,
 * plus a data library and other public data work — but Press reads the same
 * upstream Grove does and runs without it.
 *
 * TWO QUESTIONS, NOT ONE
 * "Does this plan include Cedar Press?" and "which collections does this plan
 * open?" have different answers, and this module answers both. Running them
 * together is what produced the two defects below.
 *
 * `canReadCedarPress` is the page. Cedar Grove does not include it and neither
 * does Tree: a Grove or Tree licensee reaches the collections through Grove,
 * not through this storefront. This used to return true for both, which meant
 * a Grove licensee was shown a page nobody sold them and the copy told readers
 * their Grove plan covered it.
 *
 * `shelfReach` is the collections. Grove reaches every shelf because Grove
 * carries every dataset, and Tree reaches every shelf because Tree includes
 * Grove. `tree` was missing from PLAN_REACH while the server's
 * `SHELF_BY_TIER` carried it, so a Tree subscriber was served twelve
 * collections by the API and shown none of them here. The maps are compared
 * key for key by `server/tests/test_access.py`.
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
import { PRESS_CATALOG_BY_ID, PRESS_HISTORY_FROM } from "./pressCatalog.js";

/** The shelves, lowest first. A dataset declares exactly one. */
export const SHELF = Object.freeze({
  STANDARD: "standard",
  PRO: "pro",
  GROVE: "grove",
});

const SHELF_ORDER = [SHELF.STANDARD, SHELF.PRO, SHELF.GROVE];

/**
 * How far up the shelves each plan reaches. A plan absent from this map
 * reaches nothing, which is the safe answer for an unknown or lapsed tier.
 *
 * Exported so `server/tests/test_access.py` can compare it against
 * `repository.SHELF_BY_TIER` key for key. It must stay identical to that map:
 * this decides what renders and that decides what is served, and a tier in one
 * and not the other is a reader who is served data the page will not show, or
 * shown a card the API will refuse.
 *
 * `tree` reaches the Grove shelf because Tree includes Grove and Grove carries
 * every dataset. That is not the same as saying Tree includes the Cedar Press
 * page — it does not; see `canReadCedarPress`.
 */
export const PLAN_REACH = Object.freeze({
  press: SHELF.STANDARD,
  press_pro: SHELF.PRO,
  grove: SHELF.GROVE,
  tree: SHELF.GROVE,
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

/** A year field off the dataset, or off the catalog entry it names. */
function yearOf(dataset, field) {
  if (!dataset) return null;
  const value = dataset[field] ?? PRESS_CATALOG_BY_ID[dataset.id]?.[field];
  return Number.isInteger(value) ? value : null;
}

/**
 * How far back this reader can go in a dataset they can open.
 *
 * The second axis. Cedar Press carries most collections from
 * PRESS_HISTORY_FROM forward; Cedar Press+ unlocks the reconstructed series
 * behind them. So a reader can
 * be short of a collection or short of its history, and those are different
 * sentences on the page: one sells a shelf, the other sells depth.
 *
 * `deeper` is true only when upgrading would actually move the year. A
 * collection that begins after the Press window has no depth to sell, and
 * saying otherwise would be a promise the data cannot keep.
 */
export function historyFor(user, dataset) {
  const full = yearOf(dataset, "historyFrom");
  // Declared per collection rather than derived, so a collection whose whole
  // history starts after the Press window is not described as capped.
  const standard = yearOf(dataset, "standardFrom") ?? (full == null ? null : Math.max(PRESS_HISTORY_FROM, full));
  if (!canOpenDataset(user, dataset)) {
    return { from: null, standard, full, capped: false, deeper: false };
  }
  const reach = shelfReach(user);
  const wholeSeries = reach === SHELF.PRO || reach === SHELF.GROVE;
  if (full == null) {
    return { from: null, standard: null, full: null, capped: false, deeper: false };
  }
  if (wholeSeries) {
    return { from: full, standard, full, capped: false, deeper: false };
  }
  return { from: standard, standard, full, capped: standard > full, deeper: standard > full };
}
