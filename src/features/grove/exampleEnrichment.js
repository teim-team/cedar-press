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
// (docs/TERMINAL_HANDOFF.md, "Open follow-ups from the 2026-10-06 landing-page work").
//
// What remains is the contract addition below.

/**
 * Contract fields the viewer adds so a record links to the entity its own
 * columns name. NEED's record is about its ultimate Native owner, which the
 * download carries in native_owner and native_owner_cedar_uid.
 */
export const CONTRACT_ADDITIONS = Object.freeze({
  "need/need": Object.freeze({ entity_uid: "native_owner_cedar_uid", entity_name: "native_owner" }),
});
