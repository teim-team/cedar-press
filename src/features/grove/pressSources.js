/**
 * REVIEW OWNER: Havala
 *
 * The source systems the collections are built from, for the door.
 *
 * ONE ENTRY PER KIND OF SOURCE, NOT ONE PER SITE
 * The Owned collection alone reads 174 source programs, most of them a
 * single nation's own registry. Naming them individually would be a wall of
 * 174 near-identical lines that says less than one line saying what kind of
 * thing they are. So "Tribal newsletters and tribal press" is one entry, and
 * so is "Member-owned business directories", and neither is split.
 *
 * NOTHING HERE MAY BE INVENTED, AND THERE ARE TWO KINDS OF EVIDENCE
 * - A `collections` entry is evidenced by the `sources` prose of a
 *   collection descriptor (`data/cedar/collections.manifest.json`).
 * - A `registry` entry is evidenced by the source registry itself
 *   (`cedar_source_registry/sources.jsonl`), whose 174 programs carry a
 *   `source_type`. These are the kinds of source the Owned collection reads
 *   that no descriptor sentence enumerates: state certified-vendor
 *   directories, regional chambers, artist directories and the rest.
 *
 * - A `declared` entry is evidenced by the owner's direction for a Cedar NEED
 *   enrichment (2026-09-27: patents and credit ratings), which no descriptor
 *   sentence names yet. Each carries what supports it (`supportedBy`), and
 *   the test allows this kind for Cedar NEED alone.
 *
 * `pressSources.test.js` holds every entry to its evidence, and holds each
 * registry entry's declared count to the registry's real one, so the door
 * cannot advertise a source Cedar does not read and cannot quietly keep one
 * the workspace has dropped.
 *
 * NO NEAR-DUPLICATES
 * Three separate entries used to name the same ANCSA corporation filings,
 * and three more split "enterprise registers" across two collections. One
 * source, one line. The test refuses a repeated display name; the rest is
 * judgement, and the rule is that if two lines would send a reader to the
 * same place they are one line.
 *
 * STILL ABSENT, AND WHY
 * EDGAR and the NIGC. Both are genuinely behind Cedar work — EDGAR through
 * the Deals release's SEC and EDGAR addition tables, the NIGC through Gaming
 * Intelligence — and neither is named in a storefront collection's `sources`
 * prose or in the registry. They belong here the day the workspace names
 * them, and not before.
 */

import { LAUNCH_COLLECTION } from "./collection.js";

/**
 * The source kinds, grouped by the sort of record they hold. The grouping is
 * for the reader; the door renders one continuous run.
 *
 * `name` is what the door shows. `match` is the evidence, defaulting to the
 * name where the prose already says it that way. `registry` marks an entry
 * evidenced by the source registry, with `programs` as its count there.
 */
export const SOURCE_GROUPS = Object.freeze([
  Object.freeze({
    id: "giving-disclosures",
    label: "Giving disclosures",
    sources: Object.freeze([
      { name: "First-party donation reports", match: "first-party donation reports", collections: ["foundation-corporate-giving"] },
      { name: "Public foundation, corporate and bank disclosures", match: "public foundation, corporate and bank disclosures", collections: ["foundation-corporate-giving"] },
    ]),
  }),
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
    ]),
  }),
  // The Advocacy collection's current release holds Lobbying Disclosure Act
  // filings only (2026-10-06). Consultation notices, FERC and NRC dockets,
  // IBIA and IBLA appeals, regulations.gov and Form 990 Schedule C left with
  // the descriptor's sources prose, and return when a release carries them.
  Object.freeze({
    id: "advocacy",
    label: "Lobbying disclosure",
    sources: Object.freeze([
      { name: "Senate and House lobbying disclosure", match: "lobbying disclosure filings made to the Senate and House", collections: ["lobbying"] },
    ]),
  }),
  Object.freeze({
    id: "filings",
    label: "Tax and nonprofit filings",
    sources: Object.freeze([
      { name: "IRS Business Master File", collections: ["nonprofits"] },
      { name: "Form 990 e-file returns", collections: ["nonprofits"] },
      { name: "990-N e-Postcard corpus", collections: ["nonprofits"] },
      { name: "ProPublica Nonprofit Explorer", collections: ["nonprofits"] },
    ]),
  }),
  Object.freeze({
    id: "published",
    label: "What nations and corporations publish",
    sources: Object.freeze([
      { name: "Nation enterprise registers", match: "enterprise registers", collections: ["need"] },
      { name: "ANC and NHO subsidiary directories", collections: ["need"] },
      { name: "Parent-published subsidiary disclosures", match: "parent-published subsidiary disclosures", collections: ["contractors"] },
      // One entry, not three: the Deals, Contractors and NEED descriptors
      // all point at the same filings made under Alaska Statute 45.55.139.
      { name: "ANCSA corporation filings", match: "Alaska Statute 45.55.139", collections: ["contractors", "need"] },
      { name: "Tribal newsletters and tribal press", collections: ["deals"] },
      { name: "Tribal enterprise announcements", collections: ["deals"] },
      { name: "Lender transaction announcements", collections: ["deals"] },
      { name: "Transaction counsel announcements", collections: ["deals"] },
      { name: "Government land-transfer releases", collections: ["deals"] },
      { name: "Trade and journalist coverage", match: "trade and journalist coverage", collections: ["deals"] },
    ]),
  }),
  Object.freeze({
    id: "enrichments",
    label: "Cedar NEED enrichments",
    sources: Object.freeze([
      { name: "Patent records", declared: "owner, 2026-09-27", supportedBy: "company, tribal, SEC and court evidence", collections: ["need"] },
      { name: "Rating-agency announcements", declared: "owner, 2026-09-27", supportedBy: "issuer and tribal releases, filings, regulator records and labeled secondary sources", collections: ["need"] },
    ]),
  }),
]);

/** Every source, flattened, in group order. */
export const PRESS_SOURCES = Object.freeze(
  SOURCE_GROUPS.flatMap((group) =>
    group.sources.map((source) => Object.freeze({ ...source, group: group.id })),
  ),
);

/** How many kinds of source the door can name. Counted, never typed. */
export const SOURCE_COUNT = PRESS_SOURCES.length;

/** A collection's `sources` prose, by id. The evidence the test reads. */
export const SOURCE_PROSE = Object.freeze(
  Object.fromEntries(LAUNCH_COLLECTION.map((entry) => [entry.id, entry.sources])),
);

/** The string that has to appear in the evidence for this entry to ship. */
export function evidenceFor(source) {
  return (source.match ?? source.name).toLowerCase();
}

const fold = (text) =>
  String(text ?? "").toLowerCase().replace(/[“”]/g, '"').replace(/[‘’]/g, "'");

/**
 * Whether a collection descriptor names this source. Curly quotes are folded
 * to straight ones first: a descriptor written with typographic quotes should
 * not force a hand-written list to match the glyph.
 */
export function isEvidenced(source, prose = SOURCE_PROSE) {
  if (source.registry) return true; // the test checks these against the registry
  if (source.declared) return true; // the test holds these to Cedar NEED
  const needle = fold(evidenceFor(source));
  return source.collections.some((id) => fold(prose[id]).includes(needle));
}
