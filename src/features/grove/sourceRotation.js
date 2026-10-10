/**
 * The labels the landing page's provenance band rotates through, and the
 * claim above them.
 *
 * NOT `PRESS_SOURCES`. That list is the source systems the released
 * collections name, each held to its evidence by `pressSources.test.js`, and
 * Methods and the door answer from it. This one describes Lumecon's sourcing
 * as a whole, across dataset construction and research, so it names systems
 * no single released Cedar Press collection reads (labor, parcel records).
 * Copy supplied by the owner, 2026-09-25, verbatim.
 *
 * The gaming sources (NIGC reports and opinions, sports wagering, casino
 * websites, gaming licenses, facility capacity, BIA gaming compacts, gaming
 * payment records and gaming litigation) were removed on the owner's note of
 * 2026-09-27: gaming is not a Cedar Press collection, so a panel on the Cedar
 * Press door should not name its sources. Six that remained (NIGC revenue
 * and enforcement, Class III compacts, state regulators, casino websites,
 * facility registers) went on 2026-10-10 (L1-U09). Nothing counts this list: the
 * marquee's run time is its length, and the reach figure never depended on it.
 *
 * The parcel, assessor, deed, permit and environmental-review labels name
 * the systems PLOT is built from; the foundation, 990-PF, bank, corporate,
 * tribal-foundation, recipient and charity-registration labels name the
 * Foundation & Corporate Giving sources (owner, 2026-09-27). The patent and
 * ratings labels name the Cedar NEED enrichment: patent publication and
 * family records, historical S&P and Fitch ratings, and AM Best insurance
 * financial-strength releases, a different measure from a credit rating and
 * so its own line. Patent assignment histories are not named until their
 * source is verified.
 *
 * NO DOUBLE COUNTING. Each label is one kind of source, stated once. Where a
 * new label covered an old one, the old one went: "State and local permit
 * registers" replaced "Building permit and inspection records", and the
 * state environmental label says "state" so it does not read as the federal
 * EPA line. `sourceRotation.test.js` refuses a repeated label.
 *
 * THE FIGURE IS NOT THIS LIST, AND IT IS MEASURED (2026-10-06).
 * The door used to state an owner-supplied total of seven hundred-plus
 * sources (2026-10-02) that no registry in this repository or in
 * Lumecon-data reproduces. Measured on
 * 2026-10-06, with each unit stated:
 *   - 47 kinds of source named by the released collections: every
 *     `PRESS_SOURCES` entry evidenced by a collection descriptor's `sources`
 *     prose (38) or by the tribal business source registry (9 kinds), one
 *     line per source system or source kind. The two Cedar NEED enrichments
 *     (`declared`) are left out: the current NEED release carries no patent
 *     or rating rows.
 *   - 174 source programs in the tribal business source registry
 *     (`cedar_source_registry/sources.jsonl`), each one directory or
 *     registry; behind the Individual Native-Owned Businesses collection.
 *   - 114 registered source entries (103 distinct owner strings) in
 *     Lumecon-data's intake profiles for the thirteen non-gaming collections
 *     it profiles (branch codex/convergence-packet-guard-20260928). Producer
 *     bookkeeping, not shown on the door.
 *   - 154 dataset discovery leads (`cedar_source_registry/research/
 *     dataset_discovery_*.jsonl`): candidates, not sources, and not counted.
 * None of these reaches seven hundred with a unit a reader could check, so the door
 * states the first, computed here rather than typed, and the labels below
 * stay what they always were: kinds of source across collections and
 * research, which add nothing to the figure. Grove-only Infrastructure
 * sources remain in Grove's own catalog.
 */

import { PRESS_SOURCES } from "./pressSources.js";

/** Kinds of source behind the released collections. Counted, never typed. */
export const RELEASED_SOURCE_KINDS = PRESS_SOURCES.filter((source) => !source.declared).length;

export const SOURCE_REACH_CLAIM =
  `Cedar Press collections are built from ${RELEASED_SOURCE_KINDS} kinds of public source, ` +
  "including federal systems, filings and the registries nations and their enterprises publish.";

export const SOURCE_REACH_FIGURE = String(RELEASED_SOURCE_KINDS);
/** The unit the figure counts, said where the figure is shown. */
export const SOURCE_REACH_UNIT = "kinds of source behind the collections";
export const SOURCE_REACH_UPDATED = "2026-10-06";

export const SOURCE_ROTATION = Object.freeze([
  "USAspending contract awards",
  "FPDS contract awards feed",
  "SEC EDGAR filings",
  "ANCSA corporation filings",
  "Tribal newsrooms and trade reporting",
  "Federal agency award lists",
  "Federal Register documents",
  "Agency tribal consultation pages",
  "Dear Tribal Leader letters",
  "BLM NEPA ePlanning projects",
  "USAspending assistance transactions",
  "FAADS historical assistance records",
  "USAC E-Rate and Rural Health Care data",
  "BIA land-into-trust actions",
  "EPA environmental impact reviews",
  "Federal Audit Clearinghouse single audits",
  "OSHA injury and illness data",
  "DOL Form 5500 filings",
  "NLRB election records",
  "Census LODES employment data",
  "Lobbying Disclosure Act filings",
  "Regulations.gov public comments",
  "Congressional hearing records",
  "Congress.gov bills and actions",
  "House Clerk roll-call votes",
  "Senate roll-call votes",
  "Agency FOIA and correspondence logs",
  "FERC eLibrary dockets",
  "NRC public meeting records",
  "OIRA Executive Order 12866 meetings",
  "Interior IBIA and IBLA appeals",
  "Congressional earmark disclosures",
  "National NAGPRA public databases",
  "ONRR monthly revenue",
  "ONRR fiscal-year disbursements",
  "ONRR production volumes",
  "Historical MMS Indian collections",
  "OSMRE Abandoned Mine Land distributions",
  "North Dakota tribal tax distributions",
  "North Dakota oil and gas tax series",
  "State tribal tax agreement reports",
  "Utah COBI and revitalization funds",
  "Montana oil and gas county distributions",
  "Osage Minerals Council payment history",
  "Resource asset source documents",
  "BTFA budget disclosures",
  "Parent-published Native company lists",
  "SBA and GSA certification records",
  "IRS Exempt Organizations Business Master File",
  "IRS Form 990 returns and schedules",
  "IRS Form 990-N e-Postcard data",
  "Tribal government and enterprise directories",
  "Member-owned business directories",
  "Cross-tribal business directories",
  "Alaska Native corporation shareholder directories",
  "Regional chamber directories",
  "Native artist directories",
  "State certified-vendor directories",
  "Tribe-linked CDFI directories",
  "FSRS subaward reporting",
  "BIA Realty/Tract Viewer",
  "Statewide parcel and cadastral GIS",
  "County parcel GIS",
  "County assessor and property-tax records",
  "State and local permit registers",
  "State environmental permits and CEQA reviews",
  "Recorded deeds and land transfers",
  "EPA facility and permit records",
  "Foundation grant databases and award lists",
  "Bank charitable-giving disclosures",
  "Corporate foundation award announcements",
  "Tribal foundation award records",
  "Grant-recipient announcements",
  "State charity registrations",
  "Municipal bond disclosure filings",
  "Patent publication and family records",
  "Historical S&P and Fitch ratings",
  "AM Best insurance financial-strength releases",
  "CourtListener court dockets and opinions",
  "Supreme Court dockets and amicus briefs",
  "ProPublica Nonprofit Explorer",
  "ANCSA 7(i) revenue-sharing reports",
  "BIE school directory",
  "Urban Indian organization rosters",
  "BIA mineral acreage records",
  "Center for Indian Country Development data",
  "Tribal Employment Rights Office registries",
  "DOL OLMS and state WARN notices",
  "Tribal contractor directories",
  "Tribal certification notices",
  "State product and producer directories",
]);

/**
 * The order the banner shows them in: fixed, so a build is reproducible and
 * the prerendered page matches the hydrated one, but with no pattern a reader
 * can follow (owner, 2026-09-27). Each label is placed by a hash of its own
 * text, so adding or removing one does not reshuffle the rest.
 */
const placeOf = (label) => {
  let h = 0x811c9dc5;
  for (const ch of `cedar-banner:${label}`) h = Math.imul(h ^ ch.codePointAt(0), 0x01000193) >>> 0;
  return h;
};

export const SOURCE_ROTATION_ORDER = Object.freeze(
  [...SOURCE_ROTATION].sort((a, b) => placeOf(a) - placeOf(b)),
);
