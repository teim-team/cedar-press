/**
 * PURPOSE
 * REVIEW OWNER: Havala
 *
 * The Cedar Press routes, as constants rather than strings scattered across
 * pages. Six surfaces, split by who is standing in front of them.
 *
 * The routes are registered in src/main.jsx, the standalone site's entry. A
 * page added here is not reachable until main.jsx names it.
 *
 * - PRESS_PATH is the reader's page: the briefs, the collection and the
 *   citation register, and nothing arguing for the product, because whoever
 *   is looking at it already bought it.
 * - PRESS_METHODS_PATH is the reference: how a collection is built and how it
 *   is kept current. Nobody reads this on arrival; they open it when they are
 *   about to cite a number.
 * - PRESS_REQUEST_PATH is the tribal data request policy on its own page, so
 *   the URL can be sent to a council office and land on exactly that.
 * - PRESS_RESEARCH_PATH is limited research access, for a narrow project that
 *   does not warrant a subscription.

 */

export const PRESS_PATH = "/";
/** The briefs' own front page: the newest leads, the rest stack beside it. */
export const PRESS_ARTICLES_PATH = "/articles";
/** The shelves: what each collection holds, and the release downloads. */
export const PRESS_DATA_PATH = "/data";
/** The account, and the errands that were crowding the footer. */
export const PRESS_SETTINGS_PATH = "/settings";
export const PRESS_METHODS_PATH = "/methods";
export const PRESS_REQUEST_PATH = "/tribal-data-request";
/**
 * Limited research access: one or two collections for a defined project. Its
 * own route rather than a section on the reader, because the people it is for
 * arrive from a citation or a colleague, not from inside the product.
 */
export const PRESS_RESEARCH_PATH = "/research-access";

/** A collection's own page. The reader leads here rather than handing over a
 *  file inline, because a subject is worth more than a download. */
/** One chronological feed for every collection, not a changelog per dataset. */
export const PRESS_WHATS_NEW_PATH = "/whats-new";
// Shape the Research: the priorities subscribers put Cedar Points toward.
export const PRESS_PRIORITIES_PATH = "/priorities";

/** A hosted article. Pieces that publish on Tribal Business News keep their
 *  own URL and never reach this route. */
// There is no per-collection route. A tile is the download and What's New
// is the one page that tracks changes; a detail page per dataset was more
// product than the answer needed.
export const PRESS_ARTICLE_PATH = "/articles/:articleId";
export const pressArticlePath = (id) => `/articles/${id}`;

