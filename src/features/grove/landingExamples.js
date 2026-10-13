// REVIEW OWNER: Havala
//
// THE LANDING FRAME'S EXAMPLES.
//
// Owner, 2026-10-10 (Havala Hanson, replacing Elijah Moreno's direction of
// 2026-10-06 that the door may show records beyond the release): the door
// shows only records from each collection's served download, the file a
// reader can save, so every example has passed the publication rules. A
// collection's set in data/cedar/landing_examples/<collection>.json may
// choose and order those records by their record ID and name the columns
// they are shown on; a set with no rows shows the download as served.
// Values are never copied or edited here. The one addition is PLOT's
// `extra_columns`: the tribe a parcel's recorded owner names, by exact Cedar
// register name, which the PLOT table has no column for.
//
// Only the landing frame reads this (PressCollectionPreview.jsx). The
// collection viewer, record and entity pages and every download read the
// pinned release (useSamples.js).
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
import { contractFor } from "./explore.js";

/** Each collection's landing set (record choices and shown columns) by collection id. */
export const LANDING_EXAMPLES = Object.freeze(Object.fromEntries(
  [contractors, deals, federalRegister, giving, funding, legislation, lobbying, nagpra, naturalResources, need, nonprofits, owned, plot, subcontracting]
    .map((set) => [set.collection, set]),
));

/**
 * The parsed example file the landing frame shows: the download's records the
 * collection's set chooses, in the set's order, on the download's own columns
 * plus any `extra_columns` the set declares, or the download unchanged where
 * the set chooses none. A chosen ID missing from the download is skipped (its
 * test fails, so a refresh that drops it is noticed).
 */
export function landingSample(collectionId, parsed) {
  const set = LANDING_EXAMPLES[collectionId];
  if (!parsed?.columns || !set?.rows?.length) return parsed;
  const idColumn = contractFor(`${collectionId}/${collectionId}`)?.record_id;
  if (!idColumn) return parsed;
  const byId = new Map(parsed.rows.map((row) => [row[idColumn], row]));
  const extra = (set.extra_columns ?? []).filter((column) => !parsed.columns.includes(column));
  const columns = [...parsed.columns, ...extra];
  const rows = set.rows.flatMap((ref) => {
    const row = byId.get(ref.id);
    return row ? [{ ...row, ...Object.fromEntries(extra.map((column) => [column, ref[column] ?? ""])) }] : [];
  });
  return { ...parsed, columns, rows };
}
