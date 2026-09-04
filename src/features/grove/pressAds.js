/**
 * REVIEW OWNER: Havala
 *
 * PURPOSE
 * Sponsorship inventory on Cedar Press: where a unit may appear, and what
 * happens when none is sold.
 *
 * Tribal Business News sells this product and sells advertising, so the
 * reader needs somewhere for a sponsor to sit. The whole design question is
 * containment. Cedar Press earns money from subscriptions on the strength of
 * "every figure is traceable", and an advertiser adjacent to a number is the
 * fastest way to spend that.
 *
 * THE RULES THE SLOT LIST ENFORCES
 * 1. Never inside the data. No unit appears in a shelf band, beside a
 *    collection tile, or between a reader and a download. A sponsor next to a
 *    figure reads as a sponsor of the figure.
 * 2. Never on a trust surface. Methods, the tribal data request and research
 *    access carry no inventory at any price. Those pages exist to be believed.
 * 3. Never on the way in. The gate is a sign-in.
 * 4. Editorial adjacency only, and inside a region rather than between two.
 *    A unit sits under the articles, inside the release feed, or under a
 *    collection's download, where a reader is already reading.
 * 5. Never in a filtered view. Somebody who has narrowed the reader to Data
 *    is working, and the answer to "show me my collections" is the
 *    collections.
 * 6. Always labelled, in the page's own chrome register, above the unit
 *    rather than under it.
 *
 * UNSOLD IS AN INVITATION, ON THE SLOTS THAT CARRY ONE
 * `creativeFor` returns null because there is no inventory. A slot with no
 * creative used to render no DOM at all, on the reasoning that a page with
 * nothing sold should look like a page that was never designed to sell
 * anything. That was the wrong trade for a product still finding its
 * advertisers: the people reading these collections are tribal enterprises
 * and the firms working with them, which is to say they are the buyers, and
 * an invisible slot cannot tell them the space exists.
 *
 * So an unsold slot marked `house` renders the invitation instead. The rest
 * still render nothing, and that distinction is the whole point: a hosted
 * article carries four slots, and four "advertise here" panels down one piece
 * reads as a publication nobody buys. One per page, never more.
 *
 * Rules 1 through 3 below are unchanged and apply to the invitation exactly
 * as they apply to a booked unit. A house panel is a sponsorship unit; it
 * just has not been sold yet.
 *
 * SEEING THE LAYOUT
 * Append `?ads=demo` to any Cedar Press URL to draw every slot as a dashed
 * outline with its position and size. It is a preview for laying out and
 * selling against, off by default, and it never ships as a live state.
 */

/** The slots, by id. A unit may only appear in one of these. */
export const AD_SLOT = Object.freeze({
  OVERVIEW: "overview",
  BRIEFS: "briefs",
  FEED: "feed",
  ARTICLE_RAIL: "article-rail",
  ARTICLE_RAIL_LOWER: "article-rail-lower",
  ARTICLE_RAIL_END: "article-rail-end",
  ARTICLE_END: "article-end",
});

/**
 * What each slot is, for the media kit and for the preview.
 *
 * `size` is the creative a buyer supplies. `shape` is how the slot sits in the
 * layout: a `strip` runs the width of the region it is in, a `box` holds its
 * own ratio in a rail beside the text.
 *
 * THE ARTICLE PAGE IS THE INVENTORY
 * Four of the six slots sit on a hosted article, and that is the point of
 * hosting a piece here rather than on Tribal Business News. An article has
 * a rail, which the reader does not; it has an audience you can count and report; and it has a
 * subject, so a buyer can choose federal contracting or natural resources rather than
 * buying the whole product. The rail units sit beside the text and never
 * inside it.
 *
 * ONE UNIT PER PAGE, AND FEW PAGES
 * The collection slot went with the per-collection pages: a tile downloads
 * directly now, so the page that unit sat on no longer exists.
 *
 * A first pass put a 300x250 in the article stack and a second band on the
 * seam below it. Both were wrong. The box made the stack taller than the lead
 * article beside it, and a stretch-aligned grid answered by growing 150px of
 * empty card; and two units a screen apart on the main page of a product
 * somebody pays $500 a year for reads as a publication that ran out of
 * subscribers. Adding a fourth slot is a few lines. Deciding it is worth the
 * page is the part to think about.
 */
export const AD_SLOTS = Object.freeze([
  Object.freeze({
    id: AD_SLOT.OVERVIEW,
    name: "Overview strip",
    where: "Cedar Press overview, under the section index",
    size: "728 × 90",
    shape: "strip",
    height: "5.6rem",
    house: true,
    note: "The first page a subscriber lands on, under the six sections and inside that region rather than on the seam below it. Never beside a figure: the overview names no numbers.",
  }),
  Object.freeze({
    id: AD_SLOT.BRIEFS,
    name: "Briefs strip",
    where: "Cedar Press reader, under the articles and inside their section",
    size: "728 × 90",
    shape: "strip",
    height: "5.6rem",
    house: true,
    note: "The only unit on the reader, and it sits in the editorial region rather than on the seam between two of them.",
  }),
  Object.freeze({
    id: AD_SLOT.FEED,
    name: "Feed unit",
    where: "What's new, after the first page of releases",
    size: "728 × 90",
    shape: "strip",
    height: "5.6rem",
    house: true,
    note: "Inside the feed, at the point a reader chooses to keep going.",
  }),
  Object.freeze({
    id: AD_SLOT.ARTICLE_RAIL,
    name: "Article rail",
    where: "A hosted article, top of the rail beside the text",
    size: "300 × 250",
    shape: "box",
    ratio: "300 / 250",
    house: true,
    note: "Sticks with the reader down the piece. Contextual: the article names its subject and its collections.",
  }),
  Object.freeze({
    id: AD_SLOT.ARTICLE_RAIL_LOWER,
    name: "Article rail, lower",
    where: "A hosted article, below the data panel in the rail",
    size: "300 × 600",
    shape: "box",
    ratio: "300 / 600",
    note: "The half page. Deep in the rail, where a reader who is still reading has earned the impression.",
  }),
  Object.freeze({
    id: AD_SLOT.ARTICLE_RAIL_END,
    name: "Article rail, end",
    where: "A hosted article, foot of the rail",
    size: "300 × 250",
    shape: "box",
    ratio: "300 / 250",
    note: "Only on the longest pieces. The rail is sticky, so this is the unit still beside the text when a reader is most of the way down.",
  }),
  Object.freeze({
    id: AD_SLOT.ARTICLE_END,
    name: "Article end",
    where: "A hosted article, after the body and before the data it draws on",
    size: "728 × 90",
    shape: "strip",
    height: "5.6rem",
    note: "The end of the read. It sits above the underlying-data block, never between that block and the download.",
  }),
]);

const BY_ID = Object.freeze(
  Object.fromEntries(AD_SLOTS.map((slot) => [slot.id, slot])),
);

/** The spec for a slot, or null for an id nobody has defined. */
export function slotSpec(id) {
  return BY_ID[id] ?? null;
}

/**
 * The creative booked into a slot, or null when nothing is.
 *
 * A stub with the shape the real one will have. When inventory arrives this
 * reads it from wherever Tribal Business News books it, and everything above
 * stays as it is: the caller already handles null on every render.
 */
export function creativeFor() {
  return null;
}

/** Where an advertising enquiry goes: TBN's media kit and rate request,
 * since display and sponsored content are sold through Tribal Business
 * News, not through the research desk's inbox. */
export const AD_ENQUIRY_HREF = "https://tribalbusinessnews.com/media-kit-request-rates";

/**
 * The invitation an unsold `house` slot renders.
 *
 * It describes the readership rather than counting it. Cedar Press does not
 * publish a circulation figure, and a number invented for a house panel would
 * be the one fabricated claim on a product whose argument is that every figure
 * is traceable — sold to the people most likely to check.
 */
export const AD_HOUSE = Object.freeze({
  cap: "Sponsorship",
  title: "Advertise on Cedar Press",
  body:
    "This space reaches the tribal governments, enterprises and the firms and analysts " +
    "working with them. Display and sponsored content are sold through Tribal Business News.",
  action: "Enquire about this space",
});

/** Whether an unsold slot invites a buyer rather than rendering nothing. */
export function invitesBuyers(id) {
  return slotSpec(id)?.house === true;
}

/**
 * Whether to draw the empty slots.
 *
 * Off unless a URL explicitly asks, so the same build serves the live page and
 * the layout preview and neither can turn into the other by accident.
 */
export function adsPreview(search) {
  if (typeof search !== "string") return false;
  return new URLSearchParams(search).get("ads") === "demo";
}
