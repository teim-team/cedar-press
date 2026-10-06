// REVIEW OWNER: Havala
//
// DISPLAY ADDITIONS TO THE EXAMPLE RECORDS, DERIVED FROM THE SAME ROW ONLY.
//
// Until 2026-10-06 this file also added NEED facts in the browser: an
// ultimate owner for each example and five enterprises that were not in the
// release. A reader then saw records and owners the download did not carry.
// The owner now travels in the download itself (native_owner columns, added
// by server/cedar_press/collections.py from data/cedar/need_ownership_evidence.json
// with a basis and a public source), so the page and the file agree, and the
// five unreleased enterprises are gone until the producer publishes them
// (docs/handoffs/CODEX_LANDING_FOLLOWUPS_2026-10-06.md).
//
// What remains is a reading aid computed from the row's own cells.

/**
 * A parsed example file `{ columns, rows }` with display columns computed from
 * each row's own cells. Returns the input unchanged for other collections.
 */
export function enrichSample(collectionId, parsed) {
  if (collectionId === "owned" && parsed?.rows) return withStatedTribe(parsed);
  return parsed;
}

/**
 * Individual Native-Owned Businesses: the tribe the registry lists for the
 * business, read from the registry's own "Tribe: ..." statement in
 * `identity_claim_text`. Without it the only tribe on the row is the
 * certifying office's, which reads as if the certifier owned the business.
 */
function withStatedTribe(parsed) {
  const columns = [...parsed.columns];
  if (!columns.includes("stated_tribe")) columns.splice(Math.max(columns.indexOf("business_name") + 1, 0), 0, "stated_tribe");
  const rows = parsed.rows.map((row) => {
    const match = /(?:^|;\s*)Tribe:\s*([^;]+)/.exec(row.identity_claim_text ?? "");
    return { ...row, stated_tribe: match ? match[1].trim() : "" };
  });
  return { ...parsed, columns, rows };
}

/**
 * Contract fields the viewer adds so a record links to the entity its own
 * columns name. NEED's record is about its ultimate Native owner, which the
 * download carries in native_owner and native_owner_cedar_uid.
 */
export const CONTRACT_ADDITIONS = Object.freeze({
  "need/need": Object.freeze({ entity_uid: "native_owner_cedar_uid", entity_name: "native_owner" }),
  // The landing's PLOT parcels name the tribe their recorded owner is
  // (landingExamples.js `extra_columns`).
  "plot/plot": Object.freeze({ entity_uid: "native_entity_cedar_uid", entity_name: "native_entity_name" }),
});
