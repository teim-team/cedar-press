/**
 * REVIEW OWNER: Havala
 *
 * Who the collections are for, one worked example at a time.
 *
 * The door's audience band (`PressAudienceExample.jsx`) shows one audience and
 * one real task, with the collections that task combines. The audiences are
 * data, not markup, and every collection is named by its catalog id: the name
 * and the mark a visitor sees come from `pressCatalog.js` and
 * `COLLECTION_ICONS`, so there is no second list of collections here.
 *
 * TWO VERSIONS OF EACH SENTENCE, AND A GATE BETWEEN THEM
 * Each audience can carry:
 *
 *   atLaunch  the owner's sentence and collections (2026-09-26). Verbatim
 *             except where marked EXTENDED.
 *   now       a sentence that cites released collections only. Absent (null)
 *             where the owner's own sentence already does.
 *
 * `atLaunch` is chosen when every collection it cites is live, `now`
 * otherwise, and an audience with neither live, or with fewer than
 * `MIN_COLLECTIONS` live collections, is hidden rather than shown thin.
 *
 * Some of the owner's sentences cite collections that are announced but not
 * released. Those sentences, and the one audience that exists only for such a
 * collection, are NOT in this file: they live in `pressAnnounced.js`, which
 * nothing the page loads imports, so they are not in the shipped bundle at
 * all. Here, those audiences carry `now` only. Launching a collection moves
 * its sentences in as `atLaunch` (steps in that file; the tests name any step
 * missed), and the gate below then picks them with no other change.
 *
 * COVERAGE
 * Every live collection appears in at least one shown audience, today and
 * with the gate open (`uncoveredIds`, held by the tests). The band replaced
 * the door's collection shelf (owner, 2026-09-26), so it is now the way from
 * a task to each collection; the hero viewer's rail still lists all of them.
 *
 * Labels use "and", never an ampersand: the house-style smoke test reads the
 * rendered page.
 */
import { STOREFRONT_CATALOG } from "./pressCatalog.js";

/** The ids a page may resolve: the storefront's, and nothing else. */
export function liveIdsOf(catalog = STOREFRONT_CATALOG) {
  return new Set(catalog.map((entry) => entry.id));
}

/** A live catalog entry by id, or null. Only ever reads the catalog it is handed. */
export function liveCollection(id, catalog = STOREFRONT_CATALOG) {
  return catalog.find((entry) => entry.id === id) ?? null;
}

/** Fewer than this and the example does not show collections combining. */
export const MIN_COLLECTIONS = 3;

// INTERIM COPY FOR REVIEW. Every `now.use` below was written on 2026-09-26
// by trimming the owner's sentence to what the released collections support,
// and none is the owner's text, except the advisors sentence, which is the
// owner's and only its collection list is trimmed. Each gives way to the
// owner's copy when its collections are released (see `pressAnnounced.js`).
export const PRESS_AUDIENCES = Object.freeze([
  Object.freeze({
    id: "tribal-nations",
    label: "Tribal Nations",
    // The owner's sentence, extended with "and resource revenue", is in
    // `pressAnnounced.js`; this interim version keeps that extension.
    now: Object.freeze({
      use: "Review federal funding and resource revenue associated with your nation, follow relevant agency and congressional activity, and connect enterprise records to the same Native entities.",
      collections: Object.freeze(["funding", "natural-resources", "legislation", "lobbying", "need"]),
    }),
  }),
  Object.freeze({
    id: "ancs-nhos",
    label: "ANCs and NHOs",
    now: Object.freeze({
      use: "Follow subsidiaries and joint ventures, federal contracting and announced transactions across an enterprise network.",
      collections: Object.freeze(["need", "contractors", "subcontracting", "deals"]),
    }),
  }),
  Object.freeze({
    id: "native-enterprises",
    label: "Native enterprises",
    atLaunch: Object.freeze({
      use: "Research potential partners and counterparties, compare federal procurement activity, and follow ownership relationships and major transactions in the markets where you operate.",
      collections: Object.freeze(["need", "contractors", "subcontracting", "deals", "owned"]),
    }),
    now: null,
  }),
  Object.freeze({
    id: "banks-lenders",
    // CDFIs belong here rather than as an eleventh audience (owner's brief).
    // Nothing in either sentence implies a credit score or a substitute for
    // underwriting; keep it that way.
    label: "Banks and lenders",
    now: Object.freeze({
      use: "Resolve an organization to the Native entity and enterprise structure behind it, then review federal business, public funding and announced financings as part of diligence.",
      collections: Object.freeze(["need", "contractors", "funding", "deals"]),
    }),
  }),
  Object.freeze({
    id: "native-nonprofits",
    label: "Native nonprofits",
    now: Object.freeze({
      use: "Compare an organization's public record with the federal assistance it receives, research the federal programs that fund peer organizations, and follow their documented federal engagement.",
      collections: Object.freeze(["nonprofits", "funding", "lobbying"]),
    }),
  }),
  Object.freeze({
    id: "businesses",
    label: "Businesses working in Indian Country",
    atLaunch: Object.freeze({
      use: "Identify Native enterprises and individually owned Native businesses, understand ownership relationships, and research contracting and transaction activity before approaching a market or potential partner.",
      collections: Object.freeze(["need", "owned", "contractors", "deals"]),
    }),
    now: null,
  }),
  Object.freeze({
    id: "universities-researchers",
    label: "Universities and researchers",
    // EXTENDED from the owner's sentence, 2026-09-26: "repatriation" added,
    // for NAGPRA's research use. The owner left the collections open
    // ("collections can vary by example"): one per subject the sentence
    // names, all live, which also gives Legislation and NAGPRA their homes.
    atLaunch: Object.freeze({
      use: "Build source-linked research datasets across funding, policy, organizations, transactions, repatriation and other records without separately reconstructing the same public systems and entity crosswalks.",
      collections: Object.freeze(["funding", "legislation", "nonprofits", "deals", "nagpra"]),
    }),
    now: null,
  }),
  Object.freeze({
    id: "journalists",
    label: "Journalists and newsrooms",
    now: Object.freeze({
      use: "Start with a nation, organization or event and follow the underlying record across policy, federal money, organizations and transactions while retaining the original sources.",
      collections: Object.freeze(["federal-register", "lobbying", "deals", "funding", "need"]),
    }),
  }),
  Object.freeze({
    id: "advisors",
    label: "Advisors and professional services",
    now: Object.freeze({
      use: "Build a sourced picture of an organization, market or project before diligence, strategy work, negotiations or client outreach.",
      collections: Object.freeze(["need", "deals", "federal-register", "lobbying"]),
    }),
  }),
]);

/**
 * The version of an audience's copy a page may show against `catalog`, with
 * its collections resolved to live catalog entries, or null when the audience
 * is hidden until launch.
 *
 * Returns `{ id, label, version: "atLaunch" | "now", use, collections }`.
 */
export function resolveAudience(audience, catalog = STOREFRONT_CATALOG) {
  const live = liveIdsOf(catalog);
  const allLive = (version) => Boolean(version) && version.collections.every((id) => live.has(id));
  const pick = allLive(audience.atLaunch) ? "atLaunch" : allLive(audience.now) ? "now" : null;
  if (!pick) return null;
  const version = audience[pick];
  const collections = version.collections.map((id) => liveCollection(id, catalog));
  if (collections.length < MIN_COLLECTIONS) return null;
  return Object.freeze({
    id: audience.id,
    label: audience.label,
    version: pick,
    use: version.use,
    collections: Object.freeze(collections),
  });
}

/** Every audience the page shows today, in order, resolved. */
export function visibleAudiences(catalog = STOREFRONT_CATALOG, audiences = PRESS_AUDIENCES) {
  return audiences.map((audience) => resolveAudience(audience, catalog)).filter(Boolean);
}

/** Every collection id an audience cites, in either version, for the gate test. */
export function citedIds(audiences = PRESS_AUDIENCES) {
  const ids = new Set();
  for (const audience of audiences) {
    for (const version of [audience.atLaunch, audience.now]) {
      for (const id of version?.collections ?? []) ids.add(id);
    }
  }
  return ids;
}

/**
 * Live collections no shown audience cites. Must be empty: the band is how a
 * visitor gets from a task to the data, so a collection missing from every
 * example is one the band cannot lead anyone to.
 */
export function uncoveredIds(catalog = STOREFRONT_CATALOG, audiences = PRESS_AUDIENCES) {
  const cited = new Set(
    visibleAudiences(catalog, audiences).flatMap((audience) => audience.collections.map((entry) => entry.id)),
  );
  return catalog.map((entry) => entry.id).filter((id) => !cited.has(id));
}

/** "01 / 09": the counter, from the shown set, never from the declared ten. */
export function counterLabel(index, total) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(index + 1)} / ${pad(total)}`;
}

// ── Rotation ──────────────────────────────────────────────────────────────
//
// The band advances by itself, slowly, until the visitor does anything with
// it. The rules (owner's brief, section 3): about 7 to 9 seconds a step;
// automatic rotation stops for good once the visitor interacts; it pauses
// while the band is hovered or holds focus; and under prefers-reduced-motion
// it never cycles. A fifth condition is this page's own: it does not advance
// while the band is off screen, so a visitor who scrolls down to it starts on
// the first example rather than on whichever one the timer reached.
//
// Kept as a pure reducer so the node suite can hold each rule, and the
// component only turns events into actions and `shouldRotate` into a timer.

/** Milliseconds between automatic steps: inside the brief's 7 to 9 seconds. */
export const ROTATE_MS = 8000;

export const INITIAL_ROTATION = Object.freeze({
  index: 0,
  stopped: false,
  hovered: false,
  focused: false,
  visible: false,
});

/** The next state. `total` is the number of audiences shown. */
export function rotationReducer(state, action) {
  const total = Math.max(1, action.total ?? 1);
  switch (action.type) {
    case "tick":
      // A tick only ever arrives while `shouldRotate` holds, but the reducer
      // re-checks rather than trusting the timer: a late tick after a click
      // must not move the example the visitor just chose.
      if (state.stopped || state.hovered || state.focused || !state.visible) return state;
      return { ...state, index: (state.index + 1) % total };
    case "select":
      return { ...state, stopped: true, index: ((action.index % total) + total) % total };
    case "stop":
      // The visitor committed to something inside the band (a collection):
      // the example they were reading stays put.
      return { ...state, stopped: true };
    case "next":
      return { ...state, stopped: true, index: (state.index + 1) % total };
    case "prev":
      return { ...state, stopped: true, index: (state.index - 1 + total) % total };
    case "hover":
      return { ...state, hovered: Boolean(action.on) };
    case "focus":
      return { ...state, focused: Boolean(action.on) };
    case "visible":
      return { ...state, visible: Boolean(action.on) };
    default:
      return state;
  }
}

/** Whether a timer should be running. */
export function shouldRotate(state, { reducedMotion = false, total = 0 } = {}) {
  return !reducedMotion && total > 1 && !state.stopped && !state.hovered && !state.focused && state.visible;
}
