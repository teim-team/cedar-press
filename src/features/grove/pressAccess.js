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
 * The shelves nest upward, so Cedar Press+ reaches standard and pro, and Grove
 * and Tree reach all three — which on this storefront means all twelve, since
 * nothing Cedar Press sells sits on the grove shelf. A collection PLACED on
 * the grove shelf opens for nobody here; see `canOpenDataset`.
 *
 * A capped dataset is shown rather than hidden: a reader should be able
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
// A date formatter, not release data: the roster line and the What's New
// feed should not print the same date two different ways.
import { formatUpdated } from "./pressReleases.js";

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
 * Whether this user can open a dataset ON CEDAR PRESS. A dataset with no
 * declared shelf is treated as pro rather than standard: a new entry that
 * nobody has classified should not fall open by default.
 *
 * NOTHING ON THE GROVE SHELF OPENS HERE, FOR ANY PLAN
 * Codex, PR #41. Giving PLAN_REACH the `tree: SHELF.GROVE` key it lacked fixed
 * the drift this file's header describes and exposed the disagreement beneath
 * it: `PRESS_CATALOG` carried Gaming Intelligence on the grove shelf and the
 * launch collection did not, so a Grove or Tree session was told it could
 * open a collection `repository.may_open` refuses — the same defect as the
 * `tree` drift, in the other direction and one layer down. The catalog
 * carries no grove-shelf collection since 2026-09-04; the rule stays, by
 * shelf, for the day one returns.
 *
 * The client is the wrong side, and the reason is a product ruling rather than
 * a symmetry. `code/cedar_publication.py` splits the shelves in two:
 * STOREFRONT_SHELVES ("standard", "pro") is the twelve a paying Cedar Press
 * customer sees and GROVE_SHELVES ("grove") is the one built to the same
 * standard and sold through Cedar Grove; BUILD_SHELVES is the thirteen.
 * `scripts/import_cedar_manifest.py` carries that split into the manifest, so
 * a grove-shelf collection reaches this repository in `excluded` and never in
 * the launch collection. The Cedar Press API therefore cannot serve one
 * without the Cedar data workspace changing its ruling first, and a page that
 * renders a download for it is offering a file no route will hand over.
 * `STOREFRONT_SHELVES` in pressCatalog.js is the same split, on this side.
 *
 * So the grove shelf stays in SHELF_ORDER and in PLAN_REACH — that is what
 * makes Grove and Tree reach everything Cedar Press has, and it is the map
 * `repository.SHELF_BY_TIER` is compared against — but a collection PLACED on
 * it is not sold on this storefront and does not open on it. `upgradeFor`
 * already answers this way: it names Cedar Grove, `sameProduct: false`, for a
 * grove-shelf dataset whatever the reader's plan.
 *
 * `server/tests/test_access.py` compares this function's answers, per tier and
 * per collection, against `repository.may_open`.
 */
export function canOpenDataset(user, dataset) {
  const shelf = shelfOf(dataset);
  if (shelf === SHELF.GROVE) return false;
  const reach = shelfReach(user);
  if (!reach) return false;
  const need = SHELF_ORDER.indexOf(shelf);
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
 * A collection's coverage declaration, or null if it states none.
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
function coverageOf(dataset) {
  if (!dataset) return null;
  return dataset.coverage ?? PRESS_CATALOG_BY_ID[dataset.id]?.coverage ?? null;
}

/**
 * The first year of a collection's series, or null when it has no series.
 *
 * Null is the honest answer for a roster, not a missing value to fill in.
 * Callers that reduce over collections — a shelf's earliest year, the hub's
 * "reaching back as far as" — must drop the nulls rather than substitute a
 * capture date, which is how a harvest date becomes a coverage claim.
 */
export function coverageFrom(dataset) {
  const coverage = coverageOf(dataset);
  if (coverage?.kind !== "series") return null;
  return Number.isInteger(coverage.from) ? coverage.from : null;
}

/**
 * Coverage as one line, in the shape the collection actually has.
 *
 * A series says the span. A roster says it is a roster and when it was taken,
 * because "1992 to present" for a list of live TERO certifications is a
 * promise of 34 years of history that nobody kept and no office archives.
 */
export function coverageLabel(dataset) {
  const coverage = coverageOf(dataset);
  if (!coverage) return "Coverage varies";
  if (coverage.kind === "roster") {
    return `Current roster, captured ${formatUpdated(coverage.captured)}`;
  }
  return `${coverage.from} to present`;
}
