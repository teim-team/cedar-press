/**
 * REVIEW OWNER: Havala
 *
 * The source systems the collections are built from, for the door.
 *
 * WHY THIS IS A LIST AND NOT A SENTENCE
 * Each collection's descriptor carries its sources as prose
 * (`data/cedar/collections.manifest.json`), which is the right shape for a
 * collection page and the wrong shape for a band that has to name every
 * system at once. This file is that prose broken into the systems it names,
 * with the collections each one serves.
 *
 * NOTHING HERE MAY BE INVENTED
 * Every entry carries `match`: a string that must appear, case-insensitively,
 * in the `sources` prose of at least one collection it claims. `pressSources.test.js`
 * asserts that for every entry in both directions, so a system cannot be
 * displayed on the door unless a collection descriptor actually names it, and
 * a descriptor cannot quietly drop a system that the door still advertises.
 * When the workspace adds a source to a descriptor, add it here; when it
 * removes one, the test fails until this file follows.
 *
 * WHAT IS DELIBERATELY ABSENT
 * - Cedar's own federal contracting record, which the Deals descriptor cites
 *   as a source where a transaction is visible only there. It is real and it
 *   is not an outside system, and this band is about what the collections
 *   begin from.
 * - EDGAR and the NIGC. Both are genuinely behind Cedar work — EDGAR through
 *   the Deals release's SEC and EDGAR addition tables, the NIGC through
 *   Gaming Intelligence — but neither is named in a storefront collection's
 *   `sources` prose today, and the Gaming collection is not sold here at all
 *   (`EXCLUDED_COLLECTIONS`). They belong on this band the day the workspace
 *   names them in a descriptor, and not before.
 */

import { LAUNCH_COLLECTION } from "./collection.js";

/**
 * The source systems, grouped by the kind of record they hold. The grouping
 * is for the reader; the door renders one continuous run.
 *
 * `name` is what the door shows. `match` is the evidence, defaulting to the
 * name where the prose already says it that way.
 */
export const SOURCE_GROUPS = Object.freeze([
  Object.freeze({
    id: "spending",
    label: "Federal spending and awards",
    sources: Object.freeze([
      { name: "USAspending", collections: ["funding", "contractors", "subcontracting"] },
      { name: "FAADS", collections: ["funding"] },
      { name: "FPDS", collections: ["contractors"] },
      { name: "FSRS", collections: ["subcontracting"] },
      { name: "SAM entity registrations", collections: ["contractors"] },
    ]),
  }),
  Object.freeze({
    id: "congress",
    label: "Congress and the Federal Register",
    sources: Object.freeze([
      { name: "Congress.gov", collections: ["legislation"] },
      { name: "Voteview", collections: ["legislation"] },
      { name: "Committee and hearing records", match: "committee and hearing records", collections: ["legislation"] },
      { name: "federalregister.gov", collections: ["federal-register"] },
      { name: "Federal Register NAGPRA notices", collections: ["nagpra"] },
    ]),
  }),
  Object.freeze({
    id: "advocacy",
    label: "Advocacy, consultation and dockets",
    sources: Object.freeze([
      { name: "Senate and House lobbying disclosure", collections: ["lobbying"] },
      { name: "Federal Register consultation notices", match: "Federal Register consultation", collections: ["lobbying"] },
      { name: "Ex parte notices", match: "ex parte notices", collections: ["lobbying"] },
      { name: "FERC dockets", match: "FERC and NRC dockets", collections: ["lobbying"] },
      { name: "NRC dockets", match: "FERC and NRC dockets", collections: ["lobbying"] },
      { name: "IBIA appeals", match: "IBIA and IBLA appeals", collections: ["lobbying"] },
      { name: "IBLA appeals", match: "IBIA and IBLA appeals", collections: ["lobbying"] },
      { name: "regulations.gov", collections: ["lobbying"] },
    ]),
  }),
  Object.freeze({
    id: "filings",
    label: "Nonprofit and tax filings",
    sources: Object.freeze([
      { name: "IRS Business Master File", collections: ["nonprofits"] },
      { name: "Form 990 e-file returns", collections: ["nonprofits"] },
      { name: "990-N e-Postcard corpus", collections: ["nonprofits"] },
      { name: "IRS Form 990 Schedule C", collections: ["lobbying"] },
      { name: "ProPublica Nonprofit Explorer", collections: ["nonprofits"] },
    ]),
  }),
  Object.freeze({
    id: "resources",
    label: "Resource revenue and royalties",
    sources: Object.freeze([
      { name: "ONRR disbursements", collections: ["natural-resources"] },
      { name: "MMS American Indian collections", collections: ["natural-resources"] },
      { name: "OSMRE Abandoned Mine Land distributions", collections: ["natural-resources"] },
      { name: "State severance distributions", match: "state severance distributions", collections: ["natural-resources"] },
      { name: "ANCSA 7(i) and 7(j) filings", match: "ANCSA section 7(i) and 7(j) filings", collections: ["natural-resources"] },
      { name: "Osage Minerals Council payment history", collections: ["natural-resources"] },
    ]),
  }),
  Object.freeze({
    id: "published",
    label: "What nations and corporations publish",
    sources: Object.freeze([
      { name: "Tribal TERO offices", collections: ["owned"] },
      { name: "Business licensing departments", match: "business licensing departments", collections: ["owned"] },
      { name: "Enterprise registers", match: "enterprise registers", collections: ["owned", "need"] },
      { name: "Tribal newsletters and tribal press", collections: ["deals"] },
      { name: "Trade and journalist coverage", match: "trade and journalist coverage", collections: ["deals"] },
      { name: "ANCSA shareholder filings", collections: ["deals"] },
      { name: "Alaska Division of Banking and Securities", collections: ["need"] },
      { name: "ANCSA audited filings", collections: ["contractors"] },
      { name: "Nations’ “Our Companies” registers", match: "Our Companies", collections: ["need"] },
      { name: "ANC and NHO subsidiary directories", collections: ["need"] },
      { name: "Parent-published subsidiary disclosures", match: "parent-published subsidiary disclosures", collections: ["contractors"] },
    ]),
  }),
]);

/** Every source, flattened, in group order. */
export const PRESS_SOURCES = Object.freeze(
  SOURCE_GROUPS.flatMap((group) =>
    group.sources.map((source) => Object.freeze({ ...source, group: group.id })),
  ),
);

/** How many source systems the door can name. Counted, never typed. */
export const SOURCE_COUNT = PRESS_SOURCES.length;

/** A collection's `sources` prose, by id. The evidence the test reads. */
export const SOURCE_PROSE = Object.freeze(
  Object.fromEntries(LAUNCH_COLLECTION.map((entry) => [entry.id, entry.sources])),
);

/** The string that has to appear in a descriptor for this entry to ship. */
export function evidenceFor(source) {
  return (source.match ?? source.name).toLowerCase();
}

/**
 * Whether a collection descriptor names this source. Curly quotes are folded
 * to straight ones first: the NEED descriptor writes “Our Companies” with
 * typographic quotes and a list written by hand should not have to match the
 * glyph to be correct.
 */
export function isEvidenced(source, prose = SOURCE_PROSE) {
  const needle = evidenceFor(source).replace(/[“”]/g, '"').replace(/[‘’]/g, "'");
  return source.collections.some((id) =>
    String(prose[id] ?? "")
      .toLowerCase()
      .replace(/[“”]/g, '"')
      .replace(/[‘’]/g, "'")
      .includes(needle),
  );
}
