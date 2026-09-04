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
 * THE HISTORY IS THE LEDGER'S
 * `data/cedar/releases.json` is the append-only record of every release the
 * manifest has shipped, written by `scripts/record-release.mjs` after each
 * import with the facts the release shipped with (tables, rows, preview,
 * blockers). Codex, PR #51, and it is right: the first version of this file
 * derived the "first release" from the CURRENT descriptor, so a re-import at
 * v1 would have recomputed v0 as v1 and the v0 entry, its date and the
 * permalink anchor a citation may already name would have vanished. A release
 * on the record stays on the record; the ledger refuses to overwrite a
 * version whose facts changed, and a test fails, naming the command, when the
 * manifest carries a version the ledger does not.
 *
 * What neither file carries is the reason a release happened. A ledger entry
 * says what shipped; `RELEASE_NOTES` says why, written for a reader of the
 * research product: "resolved 14 recipients to existing tribal enterprises"
 * is something a subscriber can act on, "bump parser to 2.3" is not. A note
 * overlays the ledger entry for its version and can only describe a version
 * the ledger holds; a test holds that too.
 *
 * A RETIRED COLLECTION STAYS CITABLE
 * A collection the storefront stops selling keeps its releases in the ledger,
 * and they stay in the feed as read-only history: `#<id>-v0` still resolves,
 * because a citation that named it does not expire with the shelf (Codex, PR
 * #53). Such a record carries `retired: true`, no cadence and no shelf
 * download, and the overview's "recently updated" rail leaves it out.
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

import ledger from "../../../data/cedar/releases.json" with { type: "json" };

import { PRESS_CATALOG_BY_ID } from "./pressCatalog.js";
import { LAUNCH_COLLECTION } from "./collection.js";

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
 * Editorial change notes, keyed by collection id, then by the version they
 * describe.
 *
 * Each note is `{ kind, note?, changed }` and overlays the ledger's entry for
 * that version: the ledger supplies the date and the measured facts, the
 * note supplies the reason and, for a methodology release, the warning. A
 * note for a version the ledger does not hold fails a test, because a note
 * can only describe a release that shipped.
 *
 * Empty today. Every collection is on its first release, and what a first
 * release changed is said from the ledger's facts rather than typed.
 */
export const RELEASE_NOTES = Object.freeze({});

/** The ledger's entries for a collection, oldest first, as recorded. */
export function ledgerFor(id, source = ledger) {
  return source.releases[id] ?? [];
}

/**
 * What a recorded release shipped, said for a reader, from its facts alone.
 *
 * Only the CURRENT release's preview "downloads from the shelf". The importer
 * writes each sample to one unversioned path and the shelf serves whatever is
 * there, so an older release's preview is a fact about what shipped then, not
 * a file a reader can still take (Codex, PR #52).
 */
function describe(record, { isFirst, isCurrent }) {
  const lead = isFirst ? "First release on Cedar Press" : "Release";
  const tables = record.tables
    ? `${record.tables} ${record.tables === 1 ? "table" : "tables"}, ${record.rowsLabel}`
    : record.rowsLabel;
  const changed = [`${lead}: ${tables}.`];
  if (record.preview) {
    const preview = `A ${record.preview.rows}-row preview of ${record.preview.table}, the collection's flagship table`;
    changed.push(
      isCurrent
        ? `${preview}, downloads from the shelf.`
        : `${preview}, was published with this release; the shelf now serves the current release's preview.`,
    );
  } else {
    changed.push(
      "No preview file yet: the collection's flagship table is unsettled, and no sample is published until it is.",
    );
  }
  const blockers = Array.isArray(record.blockers) ? record.blockers.length : 0;
  if (blockers) {
    changed.push(
      `Readiness is blocked, with ${blockers} named ${blockers === 1 ? "blocker" : "blockers"} recorded in the manifest.`,
    );
  }
  return changed;
}

/** One collection's history, newest first: the ledger, with notes overlaid. */
function historyOf(id, currentVersion, source) {
  const notes = RELEASE_NOTES[id] ?? {};
  return ledgerFor(id, source).map((record, index) => {
    const note = notes[record.version];
    const standing = { isFirst: index === 0, isCurrent: record.version === currentVersion };
    return Object.freeze({
      version: record.version,
      date: record.date,
      kind: note?.kind ?? RELEASE_KIND.DATA,
      ...(note?.note ? { note: note.note } : {}),
      changed: Object.freeze(note?.changed ?? describe(record, standing)),
    });
  }).reverse();
}

/**
 * Per collection: where it is now, and how it got here.
 *
 * For a collection the storefront sells, `version` and `updated` are the
 * descriptor's and `history` is the ledger's, newest first, with editorial
 * notes overlaid where they exist. For a collection the ledger holds and the
 * storefront no longer sells, the record is read-only history: its last
 * recorded release, `retired: true`, no cadence.
 *
 * A pure function of its inputs, so a test can hand it a synthetic ledger.
 */
export function buildReleases(source, launch) {
  const sold = new Map(launch.map((dataset) => [dataset.id, dataset]));
  const releases = {};
  for (const dataset of launch) {
    releases[dataset.id] = Object.freeze({
      name: dataset.name,
      version: dataset.version,
      updated: dataset.updated,
      cadence: DECLARED_CADENCE[dataset.id] ?? null,
      retired: false,
      history: Object.freeze(historyOf(dataset.id, dataset.version, source)),
    });
  }
  for (const [id, records] of Object.entries(source.releases)) {
    if (sold.has(id) || !records.length) continue;
    const last = records[records.length - 1];
    releases[id] = Object.freeze({
      name: last.name ?? id,
      version: last.version,
      updated: last.date,
      cadence: null,
      retired: true,
      history: Object.freeze(historyOf(id, null, source)),
    });
  }
  return Object.freeze(releases);
}

export const PRESS_RELEASES = buildReleases(ledger, LAUNCH_COLLECTION);

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

/** Catalog order, for tie-breaking releases that landed on one day. A
 *  retired collection sorts after every sold one. */
const ORDER = new Map(LAUNCH_COLLECTION.map((dataset, index) => [dataset.id, index]));
const orderOf = (id) => ORDER.get(id) ?? ORDER.size;

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
export function buildFeed(releases) {
  return Object.freeze(
    Object.entries(releases)
      .flatMap(([id, release]) =>
        release.history.map((entry) => {
          const name = PRESS_CATALOG_BY_ID[id]?.name ?? release.name ?? id;
          const row = { id, name, retired: release.retired, ...entry };
          return Object.freeze({
            ...row,
            anchor: anchorOf(row),
            haystack: [name, entry.version, entry.note ?? "", ...entry.changed].join(" ").toLowerCase(),
          });
        }),
      )
      .sort((a, b) => (a.date === b.date ? orderOf(a.id) - orderOf(b.id) : a.date < b.date ? 1 : -1)),
  );
}

export const RELEASE_FEED = buildFeed(PRESS_RELEASES);

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
    .filter(([, release]) => !release.retired)
    .map(([id, release]) => ({ id, ...release }))
    .sort((a, b) => (a.updated === b.updated ? orderOf(a.id) - orderOf(b.id) : a.updated < b.updated ? 1 : -1))
    .slice(0, limit);
}
