/**
 * PURPOSE
 * The launch collection: what the standalone Cedar Grove license reads.
 *
 * The collection plan replaces the organizational insight layer on the
 * Overview with the curated Cedar Press datasets. This module holds the
 * collection's descriptors, the findings the collection currently supports
 * (in the same claim shapes the organizational findings use, so FindingsPanel
 * renders them unchanged), the figure specs for the Overview's chart cards,
 * and the CSV rows behind each dataset's download button.
 *
 * OUTPUTS
 * `LAUNCH_COLLECTION` descriptors, `collectionFindings()`, `COLLECTION_FIGURES`
 * and `collectionCsv()`.
 *
 * ASSUMPTIONS
 * Findings here are hand-derived from the same rows the figures draw, and the
 * two must move together: a release that changes a series must revisit the
 * findings that cite it. The organizational findings derive this mechanically;
 * the collection will too once datasets load from manifests
 * (see datasetManifest.js), and until then this file is the single place both
 * live so they cannot drift silently.
 *
 * PROTOTYPE LIMITATIONS
 * Every number in this file is demonstration data, exactly like
 * prototypeData.js: plausible values for the demo workspace, never real
 * published figures. The real pilot datasets arrive as manifest + data files
 * and replace the inline series here.
 */

import { CLAIM_CLASS } from "./claims.js";
import { releaseFor } from "./pressReleases.js";

/**
 * The three pilot datasets, in the order the Overview shows them.
 *
 * Descriptor fields mirror the manifest contract (datasetManifest.js): what it
 * tracks, the period, the refresh cadence, the sources, plus the release
 * bookkeeping a subscriber checks before trusting a download (version,
 * vintage, updated). `rowsLabel` is display copy, not a count the code trusts.
 *
 * `origin` and `level` use the evidence registry's vocabulary
 * (SOURCE_ORIGIN, SOURCE_AVAILABILITY in evidence.js). All three launch
 * datasets are Lumecon-built curations over public records, and saying so is
 * the point: the raw records exist elsewhere, the reconciled, entity-matched,
 * versioned dataset exists because Lumecon assembled it. `level` says what
 * the rows are: entity records, or entity records that also roll up to
 * geography.
 */
export const LAUNCH_COLLECTION = Object.freeze([
  Object.freeze({
    id: "deals",
    origin: "lumecon",
    level: "entity",
    name: "Indian Country Deals",
    shortName: "Deals",
    tracks:
      "Documented public transactions under published inclusion rules: acquisitions, property purchases, project financings, bond issuances and major capital projects, 2010 to current.",
    rowsLabel: "1,248 rows",
    downloads: 1610,
    vintage: "2026 Q2",
    version: "v9",
    updated: "Jul 15",
    sources: "Primary-source target · TBN archive",
    method:
      "Announced and closed are labeled separately, and a transaction enters totals only when its status is confirmed against a primary source. Inclusion rules are published with every release, so a missing row is a known gap, not a silent one.",
  }),
  Object.freeze({
    id: "contractors",
    origin: "lumecon",
    level: "entity",
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
    method:
      "Collected weekly, reconciled and versioned quarterly. The parent-entity matching is the curation: awards roll up to the owning tribe, ANC or NHO, and provisional matches are labeled until registration confirms them.",
  }),
  Object.freeze({
    id: "funding",
    origin: "lumecon",
    level: "both",
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
    method:
      "USAspending assistance records in v1, sharing the contractor dataset's entity matching. Figures for the current fiscal year are partial until the quarterly release lands, and the page says so wherever they appear.",
  }),
  Object.freeze({
    id: "owned",
    origin: "tribal-primary",
    level: "entity",
    name: "Individually Owned Native Businesses",
    shortName: "Owned",
    tracks:
      "Individually owned Native businesses certified by their nations' TERO and commerce offices: trade, preference tier and certification status, collected office by office with each nation's consent.",
    rowsLabel: "22 businesses · 1 nation",
    downloads: 0,
    vintage: "2026 Q3",
    version: "v0.1",
    updated: "Aug 28",
    sources: "Tribal TERO offices · White Earth Nation",
    method:
      "Consent-first: each nation's TERO or commerce office shares its certified list directly, and rows appear only under that nation's stated terms. Until an office confirms publication terms, its businesses appear in aggregates only, and every listing is credited to the issuing office. White Earth Nation is the first roster in; the remaining outreach wave is in progress.",
  }),
]);

/** One line for the context strip: versions and the latest refresh date. */
export function collectionContextLine() {
  const versions = LAUNCH_COLLECTION.map((d) => `${d.shortName} ${d.version}`).join(" · ");
  const updated = LAUNCH_COLLECTION.map((d) => d.updated).sort().slice(-1)[0];
  return `${versions} · all current as of ${updated}`;
}

/**
 * What the collection supports today, in FindingsPanel's shapes.
 *
 * Supported findings are claim objects like the organizational layer's:
 * class and confidence held as separate dimensions, a basis naming the
 * dataset and version, and `fidelity: "direct"` because the collection
 * measures what it names rather than standing a wider geography in.
 * "Needs" here are the collection's own honesty items: rows awaiting
 * confirmation and releases still partial.
 */
export function collectionFindings() {
  const supported = [
    {
      id: "col-contracting-up",
      recipeId: null,
      text: "Federal contracting to Native entities rose for a fourth straight quarter.",
      basis: "Contractors v6, FPDS and USAspending.",
      claimClass: CLAIM_CLASS.descriptive,
      confidence: "high",
      fidelity: "direct",
    },
    {
      id: "col-deals-record",
      recipeId: null,
      text: "Announced deal volume in 2025 runs ahead of every prior year in the series.",
      basis: "Deals v9, announced and closed labeled separately.",
      claimClass: CLAIM_CLASS.descriptive,
      confidence: "high",
      fidelity: "direct",
    },
    {
      id: "col-sector-lead",
      recipeId: null,
      text: "Energy and project finance lead 2025 announced transactions, ahead of hospitality.",
      basis: "Deals v9, sector taxonomy.",
      claimClass: CLAIM_CLASS.comparative,
      confidence: "moderate",
      fidelity: "direct",
    },
  ];

  const needs = [
    {
      id: "col-need-closing",
      text: "Three large announced deals await closing confirmation before they enter totals (Deals v9, primary source pending).",
    },
    {
      id: "col-need-fy26",
      text: "FY2026 assistance figures are partial until the Q1 release lands (Funding v4, USAspending publication lag).",
    },
    {
      id: "col-need-matches",
      text: "Two parent-entity matches are provisional pending SAM re-registration (Contractors v6, entity resolution queue).",
    },
    {
      id: "col-need-owned-terms",
      text: "White Earth listings enter entity rows once the nation confirms publication terms; aggregates only until then (Owned v0.1, consent pending).",
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

/**
 * The Overview's three chart cards, one per dataset.
 *
 * Kept as data rather than JSX so the panel stays a dumb renderer and a
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
    id: "owned",
    title: "White Earth certified businesses by preference tier",
    basis: "Owned v0.1",
    kind: "leader",
    points: Object.freeze([
      Object.freeze({ label: "1st preference", value: 17 }),
      Object.freeze({ label: "2nd preference", value: 4 }),
      Object.freeze({ label: "4th preference", value: 1 }),
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
 * orders by demonstrated use, the same signal the request rail counts.
 * Download counts are demonstration data like every number here; the real
 * counter is server work that lands with the first release.
 */
export function figuresByDownloads() {
  return [...COLLECTION_FIGURES].sort((a, b) => {
    const da = LAUNCH_COLLECTION.find((d) => d.id === a.id)?.downloads ?? 0;
    const db = LAUNCH_COLLECTION.find((d) => d.id === b.id)?.downloads ?? 0;
    return db - da;
  });
}

/**
 * The canonical citation for a collection dataset.
 *
 * The citation register (pressCitations.js) records who cited a dataset; this
 * is the other half of that loop, the sentence to cite it WITH. A dataset
 * that is easy to cite correctly gets cited by name and version, corrections
 * can find everyone who relied on a release, and Lumecon's name travels with
 * every derivative table. Version and vintage are load-bearing, not garnish.
 *
 * `accessedOn` is a pre-formatted date string supplied by the caller (display
 * code knows the reader's date; embedded files omit it), so this stays a pure
 * function and the two implementations can be compared byte for byte.
 */
export function collectionCitation(datasetId, accessedOn = null) {
  const dataset = LAUNCH_COLLECTION.find((item) => item.id === datasetId);
  if (!dataset) return null;
  const accessed = accessedOn ? ` Accessed ${accessedOn}.` : "";
  return (
    `Lumecon, "${dataset.name}" (${currentVersion(dataset)}, vintage ${dataset.vintage}), ` +
    `Cedar Press collection, cedarpress.ai.${accessed}`
  );
}

/**
 * The version a download should carry: the release feed's current version
 * when the changelog tracks this dataset, else the descriptor's own. The
 * shelf's freshness line reads from the feed, and a file that names an
 * older release than the tile it came from cannot be matched back to the
 * changelog.
 */
function currentVersion(dataset) {
  return releaseFor(dataset.id)?.version ?? dataset.version;
}

// One CSV cell, quoted only when the value needs it, so ordinary cells stay
// byte-identical to what they were before quoting existed.
function csvCell(value) {
  const text = String(value ?? "");
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

/**
 * The rows behind a dataset card's Download button.
 *
 * The figure's own points, so what downloads is exactly what the card shows.
 * Real datasets download their full release files; this is the prototype's
 * honest stand-in, and the header row says which release it came from.
 *
 * The last row is the citation. A downloaded file outlives the page it came
 * from, so the file itself must say what it is, whose work it is and how to
 * credit it; provenance that lives only in the UI is provenance the reader
 * loses on save.
 */
export function collectionCsv(datasetId) {
  const figure = COLLECTION_FIGURES.find((item) => item.id === datasetId);
  const dataset = LAUNCH_COLLECTION.find((item) => item.id === datasetId);
  if (!figure || !dataset) return null;
  // A two-series figure downloads both series: the card draws value and
  // compare together, and a file that cannot reproduce the comparison line
  // is not the figure's own points.
  const hasCompare = figure.points.some((point) => point.compare != null);
  const release = `${dataset.name} ${currentVersion(dataset)}`;
  const header = hasCompare
    ? ["period", "value", "compare", release]
    : ["period", "value", release];
  const rows = figure.points.map((point) =>
    hasCompare ? [point.label, point.value, point.compare ?? "", ""] : [point.label, point.value, ""],
  );
  const citation = hasCompare
    ? ["cite_as", collectionCitation(datasetId), "", ""]
    : ["cite_as", collectionCitation(datasetId), ""];
  return [header, ...rows, citation].map((row) => row.map(csvCell).join(",")).join("\n");
}
