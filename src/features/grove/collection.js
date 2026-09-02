/**
 * PURPOSE
 * The launch collection: what the standalone Cedar Grove license reads.
 *
 * This module holds the collection's descriptors, the findings the collection
 * currently supports (in the same claim shapes the organizational findings
 * use, so FindingsPanel renders them unchanged), the figure specs for the
 * Overview's chart cards, and the rows behind each dataset's download button.
 *
 * OUTPUTS
 * `LAUNCH_COLLECTION` descriptors, `collectionFindings()`, `COLLECTION_FIGURES`,
 * `collectionCsv()`, and the sample/table manifest each collection carries.
 *
 * ONE SOURCE, TWO LANGUAGES
 * This file and `server/cedar_press/collections.py` read the same manifest,
 * `data/cedar/collections.manifest.json`. They used to hold two hand-written
 * copies of the same literals, and the Python docstring claimed a test
 * compared them value for value. No such test existed, and the two had
 * already drifted: the Python descriptor carried `shelf` and this one did
 * not, and this file resolved a citation's version through `pressReleases.js`
 * while Python read the descriptor, so one dataset cited as v9.0 here and v9
 * there. Reading one file makes a value difference impossible, and
 * `server/tests/test_collection.py` runs both implementations and compares
 * them field by field anyway.
 *
 * WHERE THE NUMBERS COME FROM
 * `scripts/import_cedar_manifest.py` writes the manifest from the Cedar data
 * workspace: `code/760_collection_descriptors.py` for the descriptors and
 * `code/1135_full_dataset_review_bundle.py` for the per-table row counts and
 * the ten-row samples. Nothing here is typed by hand.
 *
 * WHAT IS STILL NOT MEASURED, AND SAYS SO
 * `vintage` and `downloads` are `null` on every dataset, and
 * `UNMEASURED_FIELDS` carries the reason for each: Cedar's cadence
 * measurement produced no vintage, and no download counter exists. Absent
 * rather than zero or blank, because a zero download count and an empty
 * vintage both read as measurements.
 *
 * `COLLECTION_FIGURES` is the one place demonstration data remains. Cedar
 * publishes no figure series, so the pilot charts are the placeholders they
 * always were -- now carrying `demonstration: true` in the data rather than
 * only in prose. The Owned figure is the exception, marked
 * `demonstration: false`: its aggregates come from the roster White Earth
 * Nation's TERO supplied on 2026-08-28. No figure was invented for the eight
 * collections that arrived with this change; they have none, and none is
 * drawn.
 */

import manifest from "../../../data/cedar/collections.manifest.json" with { type: "json" };

import { CLAIM_CLASS } from "./claims.js";

const deepFreeze = (value) => {
  if (Array.isArray(value)) return Object.freeze(value.map(deepFreeze));
  if (value && typeof value === "object") {
    return Object.freeze(
      Object.fromEntries(Object.entries(value).map(([key, item]) => [key, deepFreeze(item)])),
    );
  }
  return value;
};

/**
 * Which fields carry no measurement, and why. Read by anything that would
 * otherwise render an absent value as a real one.
 */
export const UNMEASURED_FIELDS = deepFreeze(manifest.unmeasured_fields);

/**
 * Collections Cedar measures that the storefront does not sell, each with the
 * reason. Held rather than dropped: an absence nobody can see is an absence
 * nobody can question.
 */
export const EXCLUDED_COLLECTIONS = deepFreeze(manifest.excluded);

/**
 * The twelve collections the storefront carries, in shelf order.
 *
 * Descriptor fields mirror the manifest contract: what it tracks, the period,
 * the sources, plus the release bookkeeping a subscriber checks before
 * trusting a download (version, vintage, updated). `rowsLabel` is display
 * copy, not a count the code trusts -- it reads "row count unresolved" where
 * two Cedar-side declarations of a collection's membership disagree, which is
 * a real state one dataset is in today rather than a placeholder.
 *
 * `origin` and `level` use the evidence registry's vocabulary (SOURCE_ORIGIN,
 * SOURCE_AVAILABILITY in evidence.js). `level` says what the rows are: entity
 * records, entity records that also roll up to geography, or geography.
 *
 * Keys are camelCase here and snake_case in the manifest, which is the one
 * transformation this file performs: the JavaScript surface was camelCase
 * before the manifest existed and renaming it would touch every consumer.
 */
export const LAUNCH_COLLECTION = deepFreeze(
  manifest.collections.map((entry) => ({
    id: entry.descriptor.id,
    origin: entry.descriptor.origin,
    level: entry.descriptor.level,
    name: entry.descriptor.name,
    shortName: entry.descriptor.short_name,
    shelf: entry.descriptor.shelf,
    tracks: entry.descriptor.tracks,
    rowsLabel: entry.descriptor.rows_label,
    downloads: entry.descriptor.downloads,
    vintage: entry.descriptor.vintage,
    version: entry.descriptor.version,
    updated: entry.descriptor.updated,
    sources: entry.descriptor.sources,
    method: entry.descriptor.method,
  })),
);

const CEDAR = deepFreeze(
  Object.fromEntries(manifest.collections.map((entry) => [entry.id, entry.cedar])),
);
const SAMPLES = deepFreeze(
  Object.fromEntries(manifest.collections.map((entry) => [entry.id, entry.sample])),
);
const TABLES = deepFreeze(
  Object.fromEntries(manifest.collections.map((entry) => [entry.id, entry.tables])),
);

/** Readiness, blockers and measured counts for a dataset, or `null`. */
export function collectionCedarFacts(datasetId) {
  return CEDAR[datasetId] ?? null;
}

/**
 * Every table in a collection, with its sample and its full-file facts.
 *
 * The full spreadsheets are not in this repository -- the set measures 6.2 GB
 * and single tables exceed GitHub's file limit -- so each entry carries the
 * row count, the split and the file count a serving layer needs to locate the
 * real file. `full_file.shippable` is the publication rule's own answer.
 */
export function collectionTables(datasetId) {
  return TABLES[datasetId] ?? [];
}

/** The flagship table's ten-row sample: which table, where, how many of. */
export function collectionSample(datasetId) {
  return SAMPLES[datasetId] ?? null;
}

/**
 * Why a collection has no preview file, when it has none. `null` when a
 * sample exists. A collection whose flagship table Cedar could not settle
 * carries the reason as data, so a surface can say what is actually wrong
 * instead of reporting the collection missing.
 */
export function sampleUnavailableReason(datasetId) {
  return SAMPLES[datasetId]?.unavailable_because ?? null;
}

/** One line for the context strip: versions and the latest refresh date. */
export function collectionContextLine() {
  const versions = LAUNCH_COLLECTION.map((d) => `${d.shortName} ${d.version}`).join(" · ");
  const updated = LAUNCH_COLLECTION.map((d) => d.updated).sort().slice(-1)[0];
  return `${versions} · all current as of ${updated}`;
}

/**
 * What the collection supports today, in FindingsPanel's shapes.
 *
 * Supported findings are claim objects like the organizational layer's: class
 * and confidence held as separate dimensions, a basis naming the dataset, and
 * `fidelity: "direct"` because the collection measures what it names rather
 * than standing a wider geography in. "Needs" are the collection's own
 * honesty items: rows awaiting confirmation, releases still partial, and the
 * fields nothing has measured.
 *
 * Every supported finding carries `demonstration: true`. These read on the
 * same series COLLECTION_FIGURES draws, and Cedar publishes no figure series,
 * so none of them is a measured claim. They used to name versions in their
 * basis strings -- "Contractors v6", "Deals v9" -- that no release ever
 * carried; the basis is derived from the descriptor now, so it cannot name a
 * version that does not exist.
 */
export function collectionFindings() {
  const basis = (datasetId, detail) => {
    const dataset = LAUNCH_COLLECTION.find((item) => item.id === datasetId);
    return `${dataset?.shortName ?? datasetId} ${dataset?.version ?? "v0"}, ${detail}`;
  };

  const supported = [
    {
      id: "col-contracting-up",
      recipeId: null,
      demonstration: true,
      text: "Federal contracting to Native entities rose for a fourth straight quarter.",
      basis: basis("contractors", "FPDS and USAspending."),
      claimClass: CLAIM_CLASS.descriptive,
      confidence: "high",
      fidelity: "direct",
    },
    {
      id: "col-deals-record",
      recipeId: null,
      demonstration: true,
      text: "Announced deal volume in 2025 runs ahead of every prior year in the series.",
      basis: basis("deals", "announced and closed labeled separately."),
      claimClass: CLAIM_CLASS.descriptive,
      confidence: "high",
      fidelity: "direct",
    },
    {
      id: "col-sector-lead",
      recipeId: null,
      demonstration: true,
      text: "Energy and project finance lead 2025 announced transactions, ahead of hospitality.",
      basis: basis("deals", "sector taxonomy."),
      claimClass: CLAIM_CLASS.comparative,
      confidence: "moderate",
      fidelity: "direct",
    },
  ];

  const needs = [
    {
      id: "col-need-closing",
      text: "Three large announced deals await closing confirmation before they enter totals (Deals, primary source pending).",
    },
    {
      id: "col-need-fy26",
      text: "FY2026 assistance figures are partial until the Q1 release lands (Funding, USAspending publication lag).",
    },
    {
      id: "col-need-matches",
      text: "Two parent-entity matches are provisional pending SAM re-registration (Contractors, entity resolution queue).",
    },
    {
      id: "col-need-owned-terms",
      text: "White Earth listings enter entity rows once the nation confirms publication terms; aggregates only until then (Owned, consent pending).",
    },
    {
      id: "col-need-owned-membership",
      text: "Native-Owned Businesses publishes no row count and no preview file: the table Cedar names as the collection's flagship is not one its collection contract claims, and the two memberships have not been reconciled (Owned, collection membership unresolved).",
    },
    {
      id: "col-need-vintage",
      text: "No collection states a vintage: Cedar's cadence measurement produced no newest-held period for any of them, so the field is absent rather than estimated.",
    },
  ];

  const narratives = [
    {
      id: "col-lead-energy",
      name: "Energy project financing expansion",
      have: 3,
      need: 3,
      missing: [],
      requires: [{ label: "Deal series" }, { label: "Sector taxonomy" }, { label: "Primary confirmations" }],
    },
    {
      id: "col-lead-8a",
      name: "8(a) participation and award growth",
      have: 3,
      need: 3,
      missing: [],
      requires: [{ label: "Entity matches" }, { label: "Award histories" }, { label: "Certification lists" }],
    },
    {
      id: "col-lead-assist",
      name: "Assistance shifts under new appropriations",
      have: 2,
      need: 3,
      missing: ["Q1 release"],
      requires: [{ label: "Assistance records" }, { label: "Entity matches" }, { label: "Q1 release" }],
    },
  ];

  return { supported, needs, narratives };
}

/** A figure's basis line, derived so it cannot name a stale version. */
function basisFor(datasetId, fallback) {
  const dataset = LAUNCH_COLLECTION.find((item) => item.id === datasetId);
  return dataset ? `${dataset.shortName} ${dataset.version}` : fallback;
}

/**
 * The Overview's chart cards.
 *
 * Kept as data rather than JSX so the panel stays a dumb renderer and a
 * release can change what the cards show without touching a component.
 * `kind` picks the mark: quarterly bars, a leader-vs-others comparison, or a
 * two-series trend (the gray dashed series is the comparison line).
 *
 * `demonstration` says whether the points are a measurement. Cedar publishes
 * no figure series, so three of the four are placeholders and say so here
 * rather than only in a docstring.
 */
export const COLLECTION_FIGURES = deepFreeze([
  {
    id: "deals",
    title: "Announced deals by quarter",
    basis: basisFor("deals", "Deals"),
    kind: "bars",
    demonstration: true,
    points: [
      { label: "Q2'25", value: 9 },
      { label: "Q3'25", value: 12 },
      { label: "Q4'25", value: 10 },
      { label: "Q1'26", value: 16 },
      { label: "Q2'26", value: 19 },
    ],
  },
  {
    id: "contractors",
    title: "Top parents by obligations",
    basis: basisFor("contractors", "Contractors"),
    kind: "leader",
    demonstration: true,
    points: [
      { label: "Parent entity A", value: 100 },
      { label: "Parent entity B", value: 78 },
      { label: "Parent entity C", value: 65 },
      { label: "Parent entity D", value: 48 },
    ],
  },
  // The one measured figure on the page: White Earth Nation's TERO supplied
  // the roster on 2026-08-28 and these are its certification tiers. It is not
  // in the descriptor manifest because Cedar's descriptor emitter publishes no
  // figure series for any collection.
  {
    id: "owned",
    title: "White Earth certified businesses by preference tier",
    basis: "White Earth Nation TERO roster, supplied 2026-08-28",
    kind: "leader",
    demonstration: false,
    points: [
      { label: "1st preference", value: 17 },
      { label: "2nd preference", value: 4 },
      { label: "4th preference", value: 1 },
    ],
  },
  {
    id: "funding",
    title: "Federal assistance, trend",
    basis: basisFor("funding", "Funding"),
    kind: "trend",
    demonstration: true,
    points: [
      { label: "FY21", value: 52, compare: 44 },
      { label: "FY22", value: 58, compare: 46 },
      { label: "FY23", value: 55, compare: 45 },
      { label: "FY24", value: 71, compare: 49 },
      { label: "FY25", value: 84, compare: 52 },
    ],
  },
]);

/**
 * The collection's figures, in the order the shelf carries the datasets.
 *
 * This used to be `figuresByDownloads` and sorted on a download count. No
 * download counter exists -- the count was demonstration data and is now
 * `null` -- so ordering by "demonstrated use" ranked the figures on a number
 * nobody had measured. Shelf order is a fact the manifest states.
 */
export function figuresInShelfOrder() {
  const order = new Map(LAUNCH_COLLECTION.map((dataset, index) => [dataset.id, index]));
  return [...COLLECTION_FIGURES].sort(
    (a, b) => (order.get(a.id) ?? order.size) - (order.get(b.id) ?? order.size),
  );
}

/**
 * The canonical citation for a collection dataset.
 *
 * The citation register (pressCitations.js) records who cited a dataset; this
 * is the other half of that loop, the sentence to cite it WITH. A dataset that
 * is easy to cite correctly gets cited by name and version, corrections can
 * find everyone who relied on a release, and Lumecon's name travels with every
 * derivative table.
 *
 * Version is load-bearing. Vintage was too, and is omitted rather than printed
 * empty: Cedar states no vintage for any collection, and "vintage " with
 * nothing after it is a citation that cannot be checked.
 *
 * The version comes from the descriptor, not from `pressReleases.js`. Reading
 * the release feed here is what made this function disagree with its Python
 * mirror -- the feed carries demonstration change notes with versions no
 * release ever shipped, and a citation is not the place to prefer them.
 *
 * `accessedOn` is a pre-formatted date string supplied by the caller (display
 * code knows the reader's date; embedded files omit it), so this stays a pure
 * function and the two implementations can be compared byte for byte.
 */
export function collectionCitation(datasetId, accessedOn = null) {
  const dataset = LAUNCH_COLLECTION.find((item) => item.id === datasetId);
  if (!dataset) return null;
  const vintage = dataset.vintage ? `, vintage ${dataset.vintage}` : "";
  const accessed = accessedOn ? ` Accessed ${accessedOn}.` : "";
  return (
    `Lumecon, "${dataset.name}" (${dataset.version}${vintage}), ` +
    `Cedar Press collection, cedarpress.ai.${accessed}`
  );
}

// One CSV cell, quoted only when the value needs it, so ordinary cells stay
// byte-identical to what they were before quoting existed.
function csvCell(value) {
  const text = String(value ?? "");
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

/**
 * The number of columns in a CSV header line, respecting quoted cells.
 *
 * A header like `a,"b,c",d` is three columns, not four, and the citation row
 * has to be padded to the real width or the file is ragged.
 */
function columnCount(headerLine) {
  let count = 1;
  let quoted = false;
  for (const character of headerLine) {
    if (character === '"') quoted = !quoted;
    else if (character === "," && !quoted) count += 1;
  }
  return count;
}

/**
 * The rows behind a dataset card's Download button.
 *
 * The collection's flagship table, ten real rows of it, straight from
 * `code/1135_full_dataset_review_bundle.py`. This used to be the figure's own
 * points -- five demonstration bars dressed as a release file. What downloads
 * now is data.
 *
 * `null` when the collection has no sample. One is in that state today and
 * `sampleUnavailableReason` says why; handing over a metadata file in place of
 * the rows a tile promises is the failure this avoids, and `hasReleaseFile` in
 * pressDownload.js reads this to keep the tile honest.
 *
 * The last row is the citation. A downloaded file outlives the page it came
 * from, so the file itself must say what it is, whose work it is and how to
 * credit it; provenance that lives only in the UI is provenance the reader
 * loses on save.
 *
 * `sampleText` is the sample file's contents, which the browser fetches and
 * Node reads from disk. The bytes are not bundled: the twelve collections
 * carry 169 sample files and inlining them would put 1.4 MB of CSV into the
 * page for a button most readers never press.
 */
export function collectionCsv(datasetId, sampleText) {
  const sample = SAMPLES[datasetId];
  if (!sample?.path || sampleText == null) return null;
  const lines = sampleText.replace(/\r\n/g, "\n").replace(/\n+$/, "").split("\n");
  const width = columnCount(lines[0]);
  const citation = ["cite_as", collectionCitation(datasetId) ?? "", ...Array(Math.max(0, width - 2)).fill("")];
  return [...lines, citation.map(csvCell).join(",")].join("\n");
}

/**
 * Whether a collection ships a preview file at all, without needing its bytes.
 *
 * `collectionCsv` needs the sample text, which a browser has to fetch. A tile
 * has to know whether to offer the download before it fetches anything, so
 * this answers from the manifest alone.
 */
export function hasSample(datasetId) {
  return Boolean(SAMPLES[datasetId]?.path);
}

/** Where the browser fetches a collection's preview file, or `null`. */
export function samplePath(datasetId) {
  return SAMPLES[datasetId]?.path ?? null;
}
