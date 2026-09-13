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
      { name: "Federal Register consultation and ex parte notices", collections: ["lobbying"] },
      { name: "FERC and NRC dockets", collections: ["lobbying"] },
      { name: "IBIA and IBLA appeals", collections: ["lobbying"] },
      { name: "regulations.gov", collections: ["lobbying"] },
    ]),
  }),
  Object.freeze({
    id: "filings",
    label: "Tax and nonprofit filings",
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
      { name: "ANCSA section 7(i) and 7(j) filings", collections: ["natural-resources"] },
      { name: "Osage Minerals Council payment history", collections: ["natural-resources"] },
    ]),
  }),
  Object.freeze({
    id: "published",
    label: "What nations and corporations publish",
    sources: Object.freeze([
      { name: "Tribal TERO and licensing offices", match: "Tribal TERO offices", collections: ["owned"] },
      { name: "Nation enterprise registers", match: "enterprise registers", collections: ["owned", "need"] },
      { name: "ANC and NHO subsidiary directories", collections: ["need"] },
      { name: "Parent-published subsidiary disclosures", match: "parent-published subsidiary disclosures", collections: ["contractors"] },
      // One entry, not three: the Deals, Contractors and NEED descriptors
      // all point at the same filings made under Alaska Statute 45.55.139.
      { name: "ANCSA corporation filings", match: "Alaska Statute 45.55.139", collections: ["contractors", "need"] },
      { name: "Tribal newsletters and tribal press", collections: ["deals"] },
      { name: "Trade and journalist coverage", match: "trade and journalist coverage", collections: ["deals"] },
    ]),
  }),
  Object.freeze({
    id: "registry",
    label: "The tribal business source registry",
    sources: Object.freeze([
      { name: "Member-owned business directories", match: "Member-owned directory", registry: true, programs: 22 },
      { name: "Cross-tribal business directories", match: "Cross-tribal directory", registry: true, programs: 8 },
      { name: "Alaska Native corporation shareholder directories", match: "Alaska Native corporation shareholder directory", registry: true, programs: 7 },
      { name: "Regional chamber directories", match: "Regional chamber directory", registry: true, programs: 5 },
      { name: "Native artist directories", match: "Artist directory", registry: true, programs: 4 },
      { name: "Tribal enterprise pages", match: "Tribal enterprise page", registry: true, programs: 3 },
      { name: "State certified-vendor directories", match: "State certified-vendor directory", registry: true, programs: 2 },
      { name: "Chamber member directories", match: "Chamber member directory", registry: true, programs: 2 },
      { name: "Tribe-linked CDFI directories", match: "Tribe-linked CDFI directory", registry: true, programs: 1 },
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

/**
 * Source programs in the registry behind the registry-evidenced kinds. The
 * registry holds 174 in total; this counts the ones the door names a kind
 * for, so the figure and the list can never disagree.
 */
export const REGISTRY_PROGRAMS = PRESS_SOURCES.reduce(
  (sum, source) => sum + (source.registry ? source.programs : 0),
  0,
);

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
  const needle = fold(evidenceFor(source));
  return source.collections.some((id) => fold(prose[id]).includes(needle));
}
