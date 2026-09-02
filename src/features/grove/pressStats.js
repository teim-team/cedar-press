/**
 * REVIEW OWNER: Havala
 *
 * PURPOSE
 * The landing page's headline figures: the four numbers that make a visitor
 * want in, stated once, here, so the door and any future page that repeats
 * them cannot drift apart.
 *
 * WHY THESE FOUR
 * Dollars and transactions, not inventory. The door's job is "look what this
 * sees", and money moving through Indian Country says that better than any
 * count of entities or datasets — deliberately no "575 tribes" / "1,555
 * entities" style figure here, which reads as surveillance to the very
 * governments whose trust the product depends on. Scale shows up once, small,
 * in the support line.
 *
 * EVERY FIGURE MUST REPRODUCE
 * Each figure below is the data project's own published total, copied from
 * the `data/cedar` handshake (the `cedar-data-samples` branch:
 * `collection_descriptors.json` + its README), never computed here and never
 * rounded past one decimal. The data project's MONEY_TOTALLING_RULES are why
 * this file exists at all: the naive sums are catastrophically wrong (the
 * owner-grain contracting column sums 36.98x high; unfiltered subawards
 * overstate by 46.5%), so a marketing page improvising its own totals is how
 * a research product publishes a number it later has to retract.
 *
 * NO LIVE COUNTERS
 * These are static figures with a stated cadence, on purpose. A ticking
 * odometer on a landing page claims real-time updating that the pipeline
 * does not do; the honest version is a number, an as-of, and the refresh
 * promise. Do not animate these.
 *
 * KEEPING IT CURRENT
 * `PRESS_STATS_ASOF` is the data vintage the figures were copied at. Until
 * the real manifests are wired into the platform, refreshing this file by
 * hand against the data project's published totals IS the weekly update the
 * support line promises — a stale as-of is a broken promise, so bump both
 * together.
 */

/** The vintage of every figure below (the data project's `updated` stamp). */
export const PRESS_STATS_ASOF = "2026-09-01";

export const PRESS_LEAD_STATS = Object.freeze([
  Object.freeze({
    id: "contracting",
    figure: "$176.7B",
    // "Traced to", not "won by all Native firms": this is the attributed
    // total (the additive firm-grain family, $176.74B). A further $65.2B of
    // candidate awards remains unattributed rather than assumed — the figure
    // understates on purpose, which is the safe direction for a headline.
    label: "in federal contracts traced to Native-owned firms since 2000",
  }),
  Object.freeze({
    id: "subcontracting",
    figure: "$24.4B",
    // The de-duplicated total ($24.41B), primary filings only. A subaward is
    // a slice of a prime award: never add this figure to the one above.
    label: "in federal subawards where a Native business was prime or sub",
  }),
  Object.freeze({
    id: "funding",
    figure: "3.5M",
    // 3,544,079 assistance transactions. A transaction count, not dollars:
    // the data project has not published an additive dollar total for the
    // assistance record yet, and this file states no total the data side
    // has not. Swap to dollars the day one is published.
    label: "federal grant and assistance payments to Indian Country on record",
  }),
  Object.freeze({
    id: "deals",
    figure: "2,386",
    // The one collection that exists nowhere else; every row source-linked.
    // "Transactions", the dataset's own grain, not "deals": one deal can
    // carry several events, and the door must not inflate by renaming.
    label: "transactions tracked — acquisitions, joint ventures, financings and bonds",
  }),
]);

/**
 * The line under the figures. Scale appears here, once and small (8.5M rows
 * across the collections), and the cadence is a promise the operation keeps:
 * weekly, by refresh — not live, and the page never pretends otherwise.
 */
export const PRESS_LEAD_NOTE =
  "Compiled from 8.5 million maintained records. Figures updated weekly.";
