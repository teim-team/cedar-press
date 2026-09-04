/**
 * REVIEW OWNER: Havala
 *
 * PURPOSE
 * Freshness. What release a collection is on, when it last changed, how often
 * it changes, and what changed in it.
 *
 * This is the reason Cedar is a subscription rather than a file you buy once.
 * A collection can be accurate when published and wrong a year later if nobody
 * maintains the organizations behind it, so "last updated" is a headline fact
 * about a collection, not a footnote inside a methodology paragraph. It lives
 * in metadata rather than in page copy so a page cannot go stale independently
 * of the thing it describes.
 *
 * THE RELEASE IS THE MANIFEST'S, NOT THIS FILE'S
 * Version and date come from `data/cedar/collections.manifest.json`, the same
 * descriptor the citation, the download filename and the Python service read.
 * This file used to hold a hand-written history per collection, with versions
 * (v4.2, v9.0) and change notes ("added 386 awards through July") that no
 * release had shipped, and it covered ten collections while the storefront
 * sold twelve: a reader citing "Deals v9.0" from the feed downloaded
 * `deals-v0-sample.csv`. Deriving the record from the descriptor makes that
 * disagreement impossible and gives every collection a release the day its
 * descriptor lands, with nothing typed twice.
 *
 * What the manifest does not carry is the reason a release happened. The
 * first release's notes are derived from what the manifest does measure (the
 * table count, the row count, the preview file). Later releases get editorial
 * notes in `RELEASE_NOTES`, written for a reader of the research product:
 * "resolved 14 recipients to existing tribal enterprises" is something a
 * subscriber can act on, "bump parser to 2.3" is not. A note can only describe
 * a version the manifest has shipped; a test holds that.
 *
 * TWO KINDS OF RELEASE
 * A data update adds records, corrects them, or extends coverage. A
 * methodology update changes inclusion rules, classification or resolution
 * logic, and can therefore change a number somebody already published. The
 * second kind is called out loudly, because silently changing consequential
 * methodology is how a research product loses researchers.
 *
 * CADENCE IS A PROMISE, NOT A MEASUREMENT
 * Cedar's cadence measurement has produced no vintage for any collection
 * (`UNMEASURED_FIELDS` in collection.js), so the cadence here is what Cedar
 * commits to maintain, declared per collection because the sources move at
 * different speeds: the Federal Register moves when the agencies move,
 * lobbying moves on filing quarters. A collection with no declared cadence
 * states none rather than borrowing one.
 */

import { PRESS_CATALOG_BY_ID } from "./pressCatalog.js";
import { LAUNCH_COLLECTION, collectionCedarFacts, collectionSample } from "./collection.js";

/** How often a collection changes. The label is what a reader sees. */
export const CADENCE = Object.freeze({
  MONTHLY: "Updated monthly",
  QUARTERLY: "Updated quarterly",
  CONTINUOUS: "Updated continuously",
  ON_CHANGE: "Updated as records arrive",
  ANNUAL: "Updated annually",
});

/** A release changes the data, or it changes how the data is made. */
export const RELEASE_KIND = Object.freeze({
  DATA: "data",
  METHOD: "methodology",
});

/**
 * The maintenance Cedar commits to, per collection. A product declaration,
 * kept apart from the measured fields on purpose: nothing in the manifest
 * says how often a collection moves, and a test requires every storefront
 * collection to declare one here so a new collection cannot arrive silent.
 */
export const DECLARED_CADENCE = Object.freeze({
  funding: CADENCE.MONTHLY,
  "federal-register": CADENCE.ON_CHANGE,
  legislation: CADENCE.MONTHLY,
  deals: CADENCE.CONTINUOUS,
  nagpra: CADENCE.ON_CHANGE,
  lobbying: CADENCE.QUARTERLY,
  contractors: CADENCE.MONTHLY,
  subcontracting: CADENCE.MONTHLY,
  "natural-resources": CADENCE.QUARTERLY,
  // Office by office: a nation's TERO or commerce office shares its list when
  // it confirms terms, and there is no filing calendar behind that.
  owned: CADENCE.ON_CHANGE,
  nonprofits: CADENCE.ANNUAL,
  // Structures change when a parent publishes a new edition of its filings or
  // its enterprise register, which is not a calendar either.
  nest: CADENCE.ON_CHANGE,
});

/**
 * Editorial change notes, keyed by collection id, newest first.
 *
 * Each entry is `{ version, date, kind, note?, changed }` and describes a
 * release the manifest has shipped: `version` must be the descriptor's
 * current version or one before it, and `date` may not run ahead of the
 * descriptor's `updated`. When the workspace re-imports a collection at a new
 * version, its notes are written here and the derived first-release entry
 * stays below them as the floor of the history.
 *
 * Empty today. Every collection is on its first release, and the first
 * release's notes are derived below rather than typed.
 */
export const RELEASE_NOTES = Object.freeze({});

/** What the manifest measures about a first release, said for a reader. */
function firstRelease(dataset) {
  const cedar = collectionCedarFacts(dataset.id);
  const sample = collectionSample(dataset.id);
  const tables = cedar?.n_tables;
  const changed = [
    tables
      ? `First release on Cedar Press: ${tables} ${tables === 1 ? "table" : "tables"}, ${dataset.rowsLabel}.`
      : `First release on Cedar Press: ${dataset.rowsLabel}.`,
  ];
  if (sample?.path) {
    changed.push(
      `A ${sample.rows}-row preview of ${sample.table}, the collection's flagship table, downloads from the shelf.`,
    );
  } else {
    changed.push(
      "No preview file yet: the collection's flagship table is unsettled, and no sample is published until it is.",
    );
  }
  if (cedar?.blockers?.length) {
    const n = cedar.blockers.length;
    changed.push(`Readiness is blocked, with ${n} named ${n === 1 ? "blocker" : "blockers"} recorded in the manifest.`);
  }
  return Object.freeze({
    version: dataset.version,
    date: dataset.updated,
    kind: RELEASE_KIND.DATA,
    changed: Object.freeze(changed),
  });
}

/**
 * Per collection: where it is now, and how it got here.
 *
 * `version` and `updated` are the descriptor's. `history` is the editorial
 * notes, newest first, over the derived first release.
 */
export const PRESS_RELEASES = Object.freeze(
  Object.fromEntries(
    LAUNCH_COLLECTION.map((dataset) => [
      dataset.id,
      Object.freeze({
        version: dataset.version,
        updated: dataset.updated,
        cadence: DECLARED_CADENCE[dataset.id] ?? null,
        history: Object.freeze([...(RELEASE_NOTES[dataset.id] ?? []), firstRelease(dataset)]),
      }),
    ]),
  ),
);

/** The release record for a collection, or null when it has none. */
export function releaseFor(id) {
  return PRESS_RELEASES[id] ?? null;
}

/** The most recent release entry, which is what a collection page leads with. */
export function latestRelease(id) {
  return releaseFor(id)?.history?.[0] ?? null;
}

const MONTHS = Object.freeze([
  "Jan.", "Feb.", "Mar.", "Apr.", "May", "June",
  "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec.",
]);

/** Month and day, spelled the way the rest of the page spells dates. */
export function formatUpdated(iso) {
  if (!iso) return "";
  const [year, month, day] = iso.split("-").map(Number);
  return `${MONTHS[month - 1]} ${day}, ${year}`;
}

/** The short form for a metadata rail: `Updated Aug. 6 · Monthly`. */
export function freshnessLine(id) {
  const release = releaseFor(id);
  if (!release?.updated) return "";
  const [, month, day] = release.updated.split("-").map(Number);
  // No version number: collections update continuously, and a vX.X on a
  // continuously maintained series read as clutter. The date is the fact.
  // No cadence where none is declared, rather than a plausible one.
  const cadence = release.cadence ? ` · ${release.cadence.replace("Updated ", "")}` : "";
  return `Updated ${MONTHS[month - 1]} ${day}${cadence}`;
}

/** The release's stable anchor: cite `#funding-v0` and it stays citable. */
export function anchorOf(entry) {
  return `${entry.id}-${entry.version.replace(/\./g, "-")}`;
}

/** Catalog order, for tie-breaking releases that landed on one day. */
const ORDER = new Map(LAUNCH_COLLECTION.map((dataset, index) => [dataset.id, index]));

/**
 * Every release from every collection, newest first, flattened for the feed.
 *
 * Built once at module load rather than on every render: the feed is static
 * data, and the What's New page used to rebuild and re-sort it in two places
 * and re-lowercase every entry's text on every keystroke of the search box.
 * Each entry carries its collection's name, its permalink anchor and the
 * lowercased text the search matches against, so the page filters and never
 * derives.
 */
export const RELEASE_FEED = Object.freeze(
  Object.entries(PRESS_RELEASES)
    .flatMap(([id, release]) =>
      release.history.map((entry) => {
        const name = PRESS_CATALOG_BY_ID[id]?.name ?? id;
        const row = { id, name, ...entry };
        return Object.freeze({
          ...row,
          anchor: anchorOf(row),
          haystack: [name, entry.version, entry.note ?? "", ...entry.changed].join(" ").toLowerCase(),
        });
      }),
    )
    .sort((a, b) => (a.date === b.date ? ORDER.get(a.id) - ORDER.get(b.id) : a.date < b.date ? 1 : -1)),
);

/**
 * The feed's activity over a trailing window: how many releases landed, how
 * many collections they touched, how many changed methodology, and the date
 * of the newest release overall.
 *
 * Computed from the release log itself, never typed into copy, so the number
 * always carries its denominator — a bare "16 releases" reads as all-time,
 * this month or the current filter, and each of those is a different claim.
 * `today` is injectable so tests do not depend on the wall clock.
 */
export function recentActivity(days = 30, today = new Date()) {
  const cutoff = today.getTime() - days * 86400000;
  const inWindow = RELEASE_FEED.filter((entry) => new Date(entry.date).getTime() >= cutoff);
  return {
    days,
    releases: inWindow.length,
    collections: new Set(inWindow.map((entry) => entry.id)).size,
    methodology: inWindow.filter((entry) => entry.kind === RELEASE_KIND.METHOD).length,
    latest: RELEASE_FEED[0]?.date ?? null,
  };
}

/**
 * The collections that changed most recently, newest first. Drives the
 * "recently updated" rail on the reader, which is a reason to come back.
 */
export function recentlyUpdated(limit = 3) {
  return Object.entries(PRESS_RELEASES)
    .map(([id, release]) => ({ id, ...release }))
    .sort((a, b) => (a.updated === b.updated ? ORDER.get(a.id) - ORDER.get(b.id) : a.updated < b.updated ? 1 : -1))
    .slice(0, limit);
}
