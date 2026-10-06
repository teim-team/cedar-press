// REVIEW OWNER: Havala
//
// The door's example records for collections with no published sample.

import { datasetRowsOf } from "./collection.js";

/**
 * EVERY COLLECTION SHOWS REAL RECORDS ON THE DOOR (owner, 2026-10-06).
 *
 * Native-Owned Businesses (its current sample has not been exported to this
 * repository) and PLOT (no producer has shipped a release) have no published
 * flagship sample. Each shows ten real records instead, in its own field
 * names, from public/data/cedar/examples/. Nothing in them is synthesised.
 *
 * Foundation & Corporate Giving is NOT here: no foundation-to-Native grant
 * record exists in any teim-team repository, and none could be verified
 * against its source page (2026-10-06, the source sites were unreachable
 * from the build environment). Until real rows exist it shows what each
 * record holds, never invented rows.
 *
 *   owned__10.csv       ten publishable rows of native_owned_businesses.csv
 *                       (data/cedar/samples/owned__sample.csv, built by
 *                       code/770 from the clean table, 2026-09-02), the
 *                       internal identifier and diagnostics columns dropped.
 *   plot__10.csv        ten BIA trust tracts from the BIA Mineral Acreage
 *                       register (the published natural-resources sample
 *                       resource_bia_mineral_acreage_tracts__10.csv), in
 *                       PLOT's vocabulary: parcel, land area, acres,
 *                       ownership, interest.
 *
 * `columns` is the order the pane opens on; the file holds nothing else.
 */
const DOOR_EXAMPLES = Object.freeze({
  owned: Object.freeze({
    path: "/data/cedar/examples/owned__10.csv",
    columns: ["business_name", "certifying_authority_name", "directory", "service_category", "city", "state"],
  }),
  plot: Object.freeze({
    path: "/data/cedar/examples/plot__10.csv",
    columns: ["parcel_id", "land_area", "acres", "ownership", "interest", "state", "source_url"],
  }),
});

/** The door's example file for a collection with no published sample, or null. */
export function doorExample(collectionId) {
  const example = DOOR_EXAMPLES[collectionId];
  if (!example) return null;
  return { ...example, key: `${collectionId}/example`, rows: datasetRowsOf(collectionId), flagship: true, example: true };
}
