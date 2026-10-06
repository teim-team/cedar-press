// REVIEW OWNER: Havala
//
// The one sample layout the site serves: one flat customer table per
// collection.
//
// Owner ruling 2026-10-04: a collection is one whole flat spreadsheet, built by
// the shared `customer_sheet` rules (vendored from Lumecon-data,
// server/cedar_press/customer_sheet.py, policy customer-sheet-2026-10-04.5).
// `scripts/render_sample_downloads.py` writes each collection's sample in that
// layout to `public/data/cedar/downloads/<id>.csv` -- the service's own bytes,
// `repository.collection_csv` -- and records each file's SHA-256, row and
// column counts in `data/cedar/sample_downloads.json`.
//
// Every surface that reads sample rows reads these files: the download, the
// Explore reader and its cut, the record and entity pages and the public
// preview door. The raw producer previews they are rendered from carry the
// multi-table layout and retired identifier schemes (`CEDAR-NEST-` on NEED);
// they moved out of `public/` on 2026-10-04 and are no longer served at all.
//
// A fetched file is used only when its digest matches the record, so a cached
// response from before a re-render, or any other file served in its place, is
// refused rather than shown.
//
// A leaf module: it imports only the record, so explore.js, sampleFetch.js and
// pressDownload.js can all read it without a cycle.

import downloads from "../../../data/cedar/sample_downloads.json" with { type: "json" };

const RECORDS = Object.freeze(downloads.collections ?? {});
const BY_PATH = new Map(Object.values(RECORDS).map((record) => [record.path, record]));

/** The rendered customer table for a collection, or `null`. */
export function downloadRecord(id) {
  return Object.hasOwn(RECORDS, id ?? "") ? RECORDS[id] : null;
}

/** Where the browser fetches a collection's customer table, or `null`. */
export function downloadPath(id) {
  return downloadRecord(id)?.path ?? null;
}

/** The record for a served path, or `null` when the path is not a customer table. */
export function downloadRecordForPath(path) {
  return BY_PATH.get(path) ?? null;
}

/** Every collection with a rendered customer table. */
export function customerTableIds() {
  return Object.keys(RECORDS);
}

const SHA256 = /^[a-f0-9]{64}$/;

/** The lowercase hex SHA-256 of a string's UTF-8 bytes, or `null` where Web Crypto is absent. */
export async function sha256Hex(text) {
  const subtle = globalThis.crypto?.subtle;
  if (!subtle || typeof text !== "string") return null;
  const digest = await subtle.digest("SHA-256", new TextEncoder().encode(text));
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

/** Whether `text` is exactly the bytes whose digest is `expected`. */
export async function textMatchesDigest(text, expected) {
  if (typeof text !== "string" || !SHA256.test(expected ?? "")) return false;
  try {
    return (await sha256Hex(text)) === expected;
  } catch {
    return false;
  }
}

/**
 * Whether fetched bytes are exactly the rendered customer table for `id`. A
 * cached response from before a re-render, or the raw preview served in its
 * place, is refused.
 */
export async function downloadTextMatches(id, text) {
  return textMatchesDigest(text, downloadRecord(id)?.sha256);
}

/*
 * WHAT A CUSTOMER-TABLE COLUMN MEANS
 * `data/cedar/codebook.json` is the producer preview's dictionary, written
 * from the producer's own definitions (scripts/stage_verified_previews.py),
 * and a customer table mostly keeps those columns under the same names. The
 * customer_sheet rules add a few, rename a few, and lift a component's
 * qualified columns (`ownership_observations__state`) to plain ones (`state`).
 * These three tables say where each such column's meaning comes from, so a
 * reader never sees a column with no meaning. Every sentence below restates
 * server/cedar_press/customer_sheet.py, the vendored rules that write the
 * column; nothing is described that those rules do not do.
 */

/** Columns the customer_sheet rules add, with what each holds. */
export const CUSTOMER_COLUMNS = Object.freeze({
  cite_as: {
    label: "Cite as",
    meaning: "The collection's citation, repeated on every row so a saved file still says what it is, whose work it is and how to credit it.",
  },
  native_owner: {
    label: "Native owner",
    meaning: "The Native nation, Alaska Native corporation or Native Hawaiian organization at the top of the enterprise's ownership chain, as Cedar's recorded ownership evidence states it (server/cedar_press/collections.py, data/cedar/need_ownership_evidence.json). Blank where no ruling or binding is recorded; never inferred from a name.",
  },
  native_owner_cedar_uid: {
    label: "Native owner Cedar ID",
    meaning: "The Cedar Entity ID (CE-) of the Native owner.",
  },
  native_owner_basis: {
    label: "Native owner basis",
    meaning: "The kinds of evidence behind the Native owner, in plain words: a recorded ownership ruling, a register binding, the owner's own published page or a federal identifier chain.",
  },
  native_owner_source: {
    label: "Native owner source",
    meaning: "A public page a reader can open for the ownership: the owner's or its contracting arm's own page listing the enterprise.",
  },
  native_identity_basis: {
    label: "Native identity basis",
    meaning: "The kind of evidence behind the Native identity the record asserts, strongest first: tribal_government, ancsa_corporation, native_hawaiian_organization, enrolled_tribal_citizen, program_certified, publicly_stated, self_certified or unknown. Derived only from evidence already on the row; where several apply, the strongest documented one.",
  },
  native_identity_source: {
    label: "Native identity source",
    meaning: "The public source cited for the Native identity basis on this row.",
  },
  needs_cedar_id: {
    label: "Needs a Cedar ID",
    meaning: "Set where an outdated Cedar identifier was removed and no exact crosswalk binds the row to a Cedar Entity or Business ID. The ID is left blank; nothing is matched, minted or inferred.",
  },
  business_uid: {
    label: "Cedar Business ID",
    meaning: "The Cedar Business ID (CB-) of the enterprise, where an exact crosswalk binds one. Blank, with Needs a Cedar ID set, where the earlier enterprise ID was an outdated scheme.",
  },
  source_urls: {
    label: "Source URLs",
    meaning: "The public citations for the record's evidence. A local file, path or other non-public reference is left out, not replaced.",
  },
  review_level: {
    label: "Review level",
    meaning: "Whether the disclosure was independently reviewed or is a source disclosure the publication rules admit.",
  },
  land_record_kind: {
    label: "Land record kind",
    meaning: "Which kind of land record the row observes: a BIA tract or an assessor parcel.",
  },
});

/** Customer columns renamed from a producer column whose meaning they keep. */
export const CUSTOMER_RENAMES = Object.freeze({
  // customer_sheet.VERSION_RENAMES: a real-world attribute, not a release version.
  revision_kind: "version_kind",
});

/**
 * Collections whose customer table lifts one or more producer components to
 * plain columns (customer_sheet.LAYOUTS `main`), in the order they are tried.
 */
export const CUSTOMER_COMPONENTS = Object.freeze({
  "federal-register": ["federal_actions"],
  plot: ["ownership_observations", "tract_observations"],
});
