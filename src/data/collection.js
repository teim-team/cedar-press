/**
 * PURPOSE
 * The launch collection: the datasets the Cedar Press shelf shows.
 *
 * Ported from the app (teim-app, src/features/grove/collection.js) when Cedar
 * Press became a standalone site. This module holds the collection's
 * descriptors, the figure specs for the shelf's chart cards, and the CSV rows
 * behind each dataset's download button.
 *
 * PROTOTYPE LIMITATIONS
 * Every number in this file is demonstration data: plausible values for the
 * demo, never real published figures. The real pilot datasets arrive as
 * manifest + data files served by the real backend and replace the inline
 * series here.
 */

/**
 * The three pilot datasets, in the order the shelf shows them.
 *
 * Descriptor fields mirror the app's manifest contract: what it tracks, the
 * period, the refresh cadence, the sources, plus the release bookkeeping a
 * subscriber checks before trusting a download (version, vintage, updated).
 * `rowsLabel` is display copy, not a count the code trusts.
 */
export const LAUNCH_COLLECTION = Object.freeze([
  Object.freeze({
    id: "deals",
    name: "Indian Country Deals",
    shortName: "Deals",
    tracks:
      "Documented public transactions under published inclusion rules: acquisitions, property purchases, project financings, bond issuances and major capital projects, 2020 to current.",
    rowsLabel: "1,248 rows",
    downloads: 1610,
    vintage: "2026 Q2",
    version: "v9",
    updated: "Jul 15",
    sources: "Primary-source target · TBN archive",
  }),
  Object.freeze({
    id: "contractors",
    name: "Native Federal Contractors",
    shortName: "Contractors",
    tracks:
      "Tribally owned firms, ANC and NHO subsidiaries and 8(a) participants, matched to parent entities, with award histories.",
    rowsLabel: "3,904 entities",
    downloads: 2140,
    vintage: "2026 Q2",
    version: "v6",
    updated: "Jul 12",
    sources: "SAM · SBA · FPDS · USAspending",
  }),
  Object.freeze({
    id: "funding",
    name: "Federal Funding to Indian Country",
    shortName: "Funding",
    tracks:
      "Grants and federal assistance to tribes and Native organizations: who received what, from which program, when.",
    rowsLabel: "28,517 awards",
    downloads: 940,
    vintage: "FY2025 + YTD",
    version: "v4",
    updated: "Jul 12",
    sources: "USAspending assistance",
  }),
]);

/**
 * The shelf's three chart cards, one per dataset.
 *
 * Kept as data rather than JSX so the card stays a dumb renderer and a
 * release can change what the cards show without touching a component.
 * `kind` picks the mark: quarterly bars, a leader-vs-others comparison, or a
 * two-series trend (the gray dashed series is the comparison line).
 */
export const COLLECTION_FIGURES = Object.freeze([
  Object.freeze({
    id: "deals",
    title: "Announced deals by quarter",
    basis: "Deals v9",
    kind: "bars",
    points: Object.freeze([
      Object.freeze({ label: "Q2'25", value: 9 }),
      Object.freeze({ label: "Q3'25", value: 12 }),
      Object.freeze({ label: "Q4'25", value: 10 }),
      Object.freeze({ label: "Q1'26", value: 16 }),
      Object.freeze({ label: "Q2'26", value: 19 }),
    ]),
  }),
  Object.freeze({
    id: "contractors",
    title: "Top parents by obligations",
    basis: "Contractors v6",
    kind: "leader",
    points: Object.freeze([
      Object.freeze({ label: "Parent entity A", value: 100 }),
      Object.freeze({ label: "Parent entity B", value: 78 }),
      Object.freeze({ label: "Parent entity C", value: 65 }),
      Object.freeze({ label: "Parent entity D", value: 48 }),
    ]),
  }),
  Object.freeze({
    id: "funding",
    title: "Federal assistance, trend",
    basis: "Funding v4",
    kind: "trend",
    points: Object.freeze([
      Object.freeze({ label: "FY21", value: 52, compare: 44 }),
      Object.freeze({ label: "FY22", value: 58, compare: 46 }),
      Object.freeze({ label: "FY23", value: 55, compare: 45 }),
      Object.freeze({ label: "FY24", value: 71, compare: 49 }),
      Object.freeze({ label: "FY25", value: 84, compare: 52 }),
    ]),
  }),
]);

/**
 * The collection's figures, most-downloaded dataset first: the public shelf
 * orders by demonstrated use. Download counts are demonstration data like
 * every number here; the real counter is server work that lands with the
 * first release.
 */
export function figuresByDownloads() {
  return [...COLLECTION_FIGURES].sort((a, b) => {
    const da = LAUNCH_COLLECTION.find((d) => d.id === a.id)?.downloads ?? 0;
    const db = LAUNCH_COLLECTION.find((d) => d.id === b.id)?.downloads ?? 0;
    return db - da;
  });
}

/**
 * The rows behind a dataset card's Download button.
 *
 * The figure's own points, so what downloads is exactly what the card shows.
 * Real datasets download their full release files; this is the prototype's
 * honest stand-in, and the header row says which release it came from.
 */
export function collectionCsv(datasetId) {
  const figure = COLLECTION_FIGURES.find((item) => item.id === datasetId);
  const dataset = LAUNCH_COLLECTION.find((item) => item.id === datasetId);
  if (!figure || !dataset) return null;
  const header = ["period", "value", `${dataset.name} ${dataset.version} (demonstration data)`];
  const rows = figure.points.map((point) => [point.label, point.value, ""]);
  return [header, ...rows].map((row) => row.join(",")).join("\n");
}
