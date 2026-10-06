// REVIEW OWNER: Havala
//
// THE LANDING FRAME'S EXAMPLES.
//
// Owner, 2026-10-06: the landing page shows good, clean examples for every
// collection, and may show records beyond the ten pinned in the current
// release. Each collection's examples are curated in
// data/cedar/landing_examples/<collection>.json from real records already in
// this repository (the pinned downloads, the 100-row previews, test fixtures
// and Cedar's ownership rulings), each row naming where it came from in
// `_origin`. Values are copied, never invented.
//
// Only the landing frame reads this (PressCollectionPreview.jsx). The
// collection viewer, record and entity pages and every download read the
// pinned release (useSamples.js), so curation never changes the data a
// reader analyses or saves.
import contractors from "../../../data/cedar/landing_examples/contractors.json" with { type: "json" };
import deals from "../../../data/cedar/landing_examples/deals.json" with { type: "json" };
import federalRegister from "../../../data/cedar/landing_examples/federal-register.json" with { type: "json" };
import giving from "../../../data/cedar/landing_examples/foundation-corporate-giving.json" with { type: "json" };
import funding from "../../../data/cedar/landing_examples/funding.json" with { type: "json" };
import legislation from "../../../data/cedar/landing_examples/legislation.json" with { type: "json" };
import lobbying from "../../../data/cedar/landing_examples/lobbying.json" with { type: "json" };
import nagpra from "../../../data/cedar/landing_examples/nagpra.json" with { type: "json" };
import naturalResources from "../../../data/cedar/landing_examples/natural-resources.json" with { type: "json" };
import need from "../../../data/cedar/landing_examples/need.json" with { type: "json" };
import nonprofits from "../../../data/cedar/landing_examples/nonprofits.json" with { type: "json" };
import owned from "../../../data/cedar/landing_examples/owned.json" with { type: "json" };
import plot from "../../../data/cedar/landing_examples/plot.json" with { type: "json" };
import subcontracting from "../../../data/cedar/landing_examples/subcontracting.json" with { type: "json" };

/** Curated landing examples by collection id. */
export const LANDING_EXAMPLES = Object.freeze(Object.fromEntries(
  [contractors, deals, federalRegister, giving, funding, legislation, lobbying, nagpra, naturalResources, need, nonprofits, owned, plot, subcontracting]
    .map((set) => [set.collection, set]),
));

/**
 * The parsed example file the landing frame shows: the collection's curated
 * rows laid onto the download's own columns (a column a curated row does not
 * fill is blank), plus any `extra_columns` the set declares (PLOT's parcels
 * carry the tribe their recorded owner names, which the PLOT table has no
 * column for), or the pinned file unchanged where none are curated.
 */
export function landingSample(collectionId, parsed) {
  const set = LANDING_EXAMPLES[collectionId];
  if (!parsed?.columns || !set?.rows?.length) return parsed;
  const columns = [...parsed.columns, ...(set.extra_columns ?? []).filter((column) => !parsed.columns.includes(column))];
  return {
    ...parsed,
    columns,
    rows: set.rows.map((row) => Object.fromEntries(columns.map((column) => [column, row[column] ?? ""]))),
  };
}
