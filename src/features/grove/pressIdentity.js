/**
 * REVIEW OWNER: Havala
 *
 * PURPOSE
 * The identity argument: the two identifiers Cedar assigns and maintains, what
 * each one names, and what carrying them makes possible that no source system
 * can do on its own. This is the load-bearing claim on the Methods page, so it
 * lives here where a test can hold it to the register and the schemas.
 *
 * WHY TWO
 * The owner's specification of 2026-09-13 (docs/CEDAR_IDENTITY_SYSTEM_2026-09-13.md)
 * sets two separate permanent namespaces, both identity anchors for the Cedar
 * graph and neither a descriptive label, a classification or a source-system
 * id:
 *
 *   CE-  one canonical Native entity. A federally recognized tribe, an Alaska
 *        Native corporation, an NHO, a tribal government, a Native nonprofit
 *        or another defined class in the register. Live today as `cedar_uid`,
 *        documented in docs/IDENTIFIER_STANDARD.md.
 *   CB-  one distinct business or enterprise. A tribal operating company, a
 *        subsidiary, a holding company, a vendor, a privately owned Native
 *        firm. Specified, and not yet minted anywhere in the workspace.
 *
 * A NATION AND THE COMPANY IT OWNS ARE TWO SUBJECTS. An earlier draft of this
 * file said the entity id names "an enterprise a nation owns", which the
 * register does not back (it holds no tribal-enterprise class) and which the
 * specification reverses: the enterprise is a CB-, and the ownership between
 * the two is a dated relationship row with a source. Collapsing them makes
 * "what has this nation been involved in" and "what has this enterprise won"
 * the same query with the same wrong answer.
 *
 * A firm that is Native-owned without being owned by a nation carries a
 * business id and no entity id, from the first sighting, because the day a
 * nation acquires it the history has to already exist. A history you start
 * keeping on the day it becomes interesting is not a history. (The 45
 * `Individually Native-owned business` entities minted before ADR-043 keep
 * their uids and gain business ids; the class is closed to new mints.)
 *
 * EVIDENCE, NOT ASSERTION
 * Every class code named below is a class the published register really holds,
 * and every column named below is one the specification names.
 * `pressIdentity.test.js` reads `public/data/cedar/register.json` and fails if
 * it drifts, and holds the entity sample to a uid the register really has. It
 * also
 * pins the withholding claim: the register ships the individually owned firms
 * with a uid and no name, which is the whole point of the second identifier
 * and would be a lie to state if the file stopped doing it.
 *
 * COPY DISCIPLINE
 * Brand lock in CLAUDE.md: no em dashes, no antithesis ("not X, it's Y"), and
 * no sentence that ends in a comma and a fragment.
 */

import { SCOPES } from "./explore.js";

/**
 * The two identifiers, as the page renders them.
 *
 * WRITTEN AGAINST THE OWNER'S SPECIFICATION OF 2026-09-13, recorded verbatim
 * in docs/CEDAR_IDENTITY_SYSTEM_2026-09-13.md. Two separate permanent
 * namespaces, both identity anchors for the Cedar graph and neither a
 * descriptive label, a classification or a source-system id.
 *
 * `classes` are register class codes this identifier covers, checked against
 * the published register. `fields` are the role-specific column names the
 * specification names. `survives` is what the identifier is designed to
 * outlive, which is the only reason to mint one.
 */
export const IDENTIFIERS = Object.freeze([
  Object.freeze({
    id: "entity",
    label: "Cedar entity id",
    // Cherokee Nation's real uid, and the same one the worked example uses.
    //
    // Codex, PR #78: this was CE-00001-6S, which the published register binds
    // to Asa'carsarmiut Tribe, and the worked example paired it with Cherokee
    // Nation. A methods page whose whole argument is that identifiers resolve
    // to one entity, printing an identifier that resolves to a different one.
    // The test now checks the NAME the register gives the uid, not merely
    // that the uid exists, which is the check that missed it.
    shape: "CE-00134-BX",
    live: true,
    // Codex, PR #78: the card advertised the specification's role-specific
    // names, and not one of them appears in a published table. `cedar_uid` is
    // on 66. A customer following the page could not join a current export.
    //
    // Two rows now: what ships, and what the standard is renaming it to. The
    // test holds `fields` against the real contracts and `becoming` against
    // the specification, so neither half can drift into the other.
    fields: Object.freeze(["cedar_uid"]),
    becoming: Object.freeze([
      "native_entity_uid",
      "recipient_native_entity_uid",
      "owner_cedar_uid",
      "parent_cedar_uid",
    ]),
    names:
      "One canonical Native entity, across every Cedar dataset. A federally recognized tribe, an Alaska Native corporation, a Native Hawaiian organization, a tribal government, a Native nonprofit or another defined entity class in the register.",
    // Enterprises are NOT on this list any more. The earlier copy said the
    // entity id names "an enterprise a nation owns", which the register does
    // not back (it holds no tribal-enterprise class) and which the owner's
    // specification reverses: an operating enterprise is a business id, and
    // the ownership between the two is a dated relationship.
    classes: Object.freeze([
      "Federally recognized tribe",
      "Federally recognized Alaska Native Village",
      "Native Hawaiian Organization",
      "Alaska Native Regional Corporation",
      "Alaska Native Village Corporation",
      "State-recognized tribe",
      "Intertribal Organization",
      "Tribal College or University",
      "Native Community Development Financial Institution",
      "Urban Indian Organization",
      "Native nonprofit",
    ]),
    survives: Object.freeze([
      "A nation wins federal recognition and its class changes",
      "Cedar corrects the name or an attribute it holds",
      "A dataset would be tidier if the id moved, and it does not",
    ]),
    note:
      "An opaque serial with a check component. Neither part encodes geography, entity type, ownership, legal status, dataset or ordering, so nothing Cedar learns about an entity can force its identity to be rewritten. Never recycled.",
  }),
  Object.freeze({
    id: "business",
    label: "Cedar business id",
    // SPECIFIED, NOT YET MINTED. The owner set this display form on
    // 2026-09-13; the 2026-09-06 decision (docs/CEDAR_BUSINESS_ID_DECISION_2026-09-06.md,
    // at the tag data-workspace-final) carries a
    // check-character variant (CB-0001842-XQ) and the specification says a
    // check convention can come later, so the plain serial is what ships on
    // the page. No CB- exists in data/spine yet, which is why `live` is
    // false and the section says so in one line rather than implying a
    // register that is already populated.
    //
    // It showed `TBD-030:4033` for a day. That is a real business_source_id
    // and the wrong object: a source-record key with a source code inside
    // it, which the specification classes as an external identifier, never
    // an identity.
    shape: "CB-0000001",
    live: false,
    // Nothing ships a business id yet, so there is no live column to name.
    fields: Object.freeze([]),
    becoming: Object.freeze(["business_uid"]),
    names:
      "One distinct business or enterprise. A tribal operating company, a subsidiary, a holding company, a vendor, a contractor, an acquisition target or a privately owned Native firm.",
    classes: Object.freeze(["Individually Native-owned business"]),
    survives: Object.freeze([
      "The name, the DBA, the address or the NAICS code changes",
      "A certification lapses, or the owner changes entirely",
      "The business is dissolved or acquired, and keeps its record",
    ]),
    note:
      "Opaque, append-only, never reused. It identifies the business, not its owner, not a citizenship or certification claim, not a UEI, CAGE, EIN, DUNS or SAM registration, not a location, brand, project or contract, and not a person. A surviving legal business keeps its id through a change; a genuine legal successor gets a new one.",
    // Codex, PR #77, and it was right: the displayed copy said flatly that an
    // individually owned firm carries a business id and no entity id, while
    // the published register shows the 44 firms in that class carrying CE-
    // uids today. ADR-043 closed the class to new mints and gives those 44 an
    // equivalence row rather than taking their uids away, so the rule is true
    // going forward and false about the firms that already exist. Said as
    // what it is: a rule with a dated exception, on the page, not in a
    // comment.
    // Codex, PR #78: this said the 44 firms have equivalence rows and that
    // every firm resolved from here carries a business id only. No CB- value
    // and no equivalence row exists in data/spine, so both were present-tense
    // claims about a register that has not been written. Future tense, which
    // is also what the governing decision says.
    exception:
      "Forty-four privately owned firms were minted into the entity register before this rule and keep their entity ids. The class is closed to new mints: when the business register is written, those firms gain a business id with an equivalence row to their entity id, and every firm resolved after it carries a business id alone.",
  }),
]);

/**
 * What each identifier is NOT, which is half of what makes it useful.
 *
 * The specification is emphatic about this and it is the part a reader who
 * has seen other vendors' "unique IDs" will not expect: everything that can
 * change, be missing, be shared or be misreported by a source lives outside
 * the identifier, in a dated row with its evidence.
 */
export const KEPT_OUTSIDE = Object.freeze([
  Object.freeze({
    id: "relationships",
    label: "Ownership and structure",
    body:
      "Owner, parent, subsidiary, operator and affiliation are relationship rows carrying both ids, a type, effective dates, a source and a confidence. None of it is inside either identifier.",
  }),
  Object.freeze({
    id: "external",
    label: "Everyone else's identifiers",
    body:
      "UEI, CAGE, EIN, SAM registrations, NAICS, state registrations, websites and aliases sit in an attribute ledger. They change, go missing, get shared and get reported wrong. A Cedar id does none of those things.",
  }),
  Object.freeze({
    id: "events",
    label: "What happened",
    body:
      "An award, a deal, a filing, a notice, a bill and a subcontract each keep their own record id and link out to the entity or the business the source actually named. A Cedar id says who; a dataset id says what.",
  }),
]);

/**
 * Why two namespaces rather than one, as the worked example the owner uses.
 *
 * A single id space collapses an enterprise into its tribal owner, and then
 * "what has this nation been involved in" and "what has this enterprise won"
 * become the same query with the same wrong answer.
 */
export const WHY_BOTH = Object.freeze({
  entity: Object.freeze({
    id: "CE-00134-BX",
    name: "Cherokee Nation",
    role: "The Native government, in the entity register.",
  }),
  business: Object.freeze({
    id: "CB-0000001",
    // The entity side of this example is real and checked: CE-00134-BX is
    // Cherokee Nation in the published register. The business side cannot be,
    // because no CB- register exists, so CB-0000001 is the FORM and not this
    // enterprise's identifier. Marked, so a reader does not transcribe it as
    // one. This is the same error Codex caught on the entity side of PR #78,
    // one card over, and the fix is to say which of the two is a real
    // identifier rather than to print both as though they were.
    pending: true,
    name: "Cherokee Nation Businesses",
    role: "A distinct operating enterprise, in the business register.",
  }),
  edge: "owns or controls, with effective dates and a source",
  questions: Object.freeze([
    "What activity is associated with this nation?",
    "What contracts has this enterprise received?",
  ]),
  close:
    "Two questions, two answers. A contract, a deal, a lobbying filing or a subsidiary links to whichever of the two the source actually identified, and to both where it named both. A Cedar entity id never goes in a business column, and a business id never goes in an entity column.",
});

/**
 * The class the PUBLIC LOOKUP withholds names for, and what that does and
 * does not mean.
 *
 * The owner's challenge, 2026-09-13: "isn't that wrong that it doesn't publish
 * what it resolves?" It would be, and Cedar does publish it. What is withheld
 * is narrower than the earlier copy on this page implied, and the distinction
 * is the whole judgement:
 *
 * - The storefront's Individual Native-Owned Businesses collection publishes
 *   these firms BY NAME, because a nation's own TERO or commerce office
 *   published them. The name is the nation's to give and it gave it.
 * - Where the only evidence is a federal award file, the firm publishes by
 *   name too, since the owner ruling of 2026-10-02: a firm is a business
 *   entity regardless of what it is named after, and its name, identifiers
 *   and business address are public business records (SAM and USAspending
 *   publish exactly these for every federal awardee), not personal
 *   identifying information. Until that date `INDIVIDUAL_NATIVE_WITHHELD_FIELDS`
 *   in the retired `code/cedar_domain.py` withheld them absent recorded consent, on the
 *   reasoning that a firm named after its owner is a private individual; the
 *   ruling rejects that reasoning for this class. The rule is still per
 *   field and still fails closed on a field it does not know. The
 *   aggregate small-cell rule (fewer than three firms) was lifted by the
 *   owner ruling of 2026-10-04, and source terms are provenance, not a gate.
 * - `register.json`, the entity lookup this whole site can read, therefore
 *   carries the name for this class; its `withheld_names` reads 0.
 *
 * `pressIdentity.test.js` pins the last of those against the published file.
 * The identifier is on the firm in every case, which is the point.
 */
export const WITHHELD_CLASS = "Individually Native-owned business";

/** What Cedar publishes about an individually owned firm, said plainly. */
export const WITHHELD_NOTE =
  "A firm is published under its own name whatever it is named after. Where a nation's commerce office published its certified businesses, they are in the collection by name. Where the only evidence is a federal award file, the firm's name, identifiers, and business address are published as public business records with the same fields SAM and USAspending publish for all federal awardees. Cedar does not publish internal working text.";

/**
 * THE LINKAGE NOTE ON THE METHODS PAGE.
 *
 * Codex, PR #77: the linkage section once promised an organization's "whole
 * footprint". The page now says coverage varies by collection and why, and
 * prints no figure. The figures it once quoted were measured on 2026-09-02 by
 * the retired workspace (kept at the tag `data-workspace-final`) from tables
 * the served releases do not use, and nothing could refresh them. The page
 * can quote measured figures again once each release record carries its own
 * entity-coverage counts.
 */
export const LINKAGE_COVERAGE = Object.freeze({
  // A reader who takes a cross-collection total as a quality score has read
  // it wrong, so the page gives no single figure and says why.
  caveat:
    "A total across collections sums tables whose rows are not the same kind of thing. A contract award and a NAGPRA notice each count as one, so any total is a measure of scale and never of quality.",
  note:
    "How many records have a resolved Cedar entity varies by collection. A low share does not mean the same thing everywhere. For example, in Natural Resource Revenues, a royalty line names a lease rather than an organization, so a line like that has no entity by design. A record can have no entity for other reasons too, and they are specified below. Cedar links a record to an entity only where the evidence supports it.",
});

/**
 * WHY A ROW CARRIES NO ENTITY, and why most of it is not a miss.
 *
 * The owner's note, 2026-09-13: some data will never get an entity tag,
 * because it addresses all of Indian Country or because it is an individually
 * owned business, and the page should make that sound intentional rather than
 * like a hole. It is intentional, and the workspace already says so in its own
 * vocabulary: `link_statuses` in `data/cedar/scopes.json` carries a definition
 * for each state, two of which contain the phrases "Never a failed match" and
 * "not by failure".
 *
 * So the page renders those definitions rather than a paraphrase of them, and
 * the test holds each one to the file. The three states below are every state
 * except `resolved`.
 *
 * `unresolved` is the honest one and it stays on the page: a party the register
 * could not place is work still to do, and the collections are still being
 * built. Publishing the count beside the two intentional states is the whole
 * point of the door's "published with its limits" pillar.
 */
/**
 * One `link_statuses` definition, or a loud failure.
 *
 * `scopes.json` is workspace data the site renders verbatim. If a key it names
 * disappears, the honest outcomes are a failing test and a visible message,
 * never a card with nothing in it.
 */
export function requireStatus(id) {
  const body = SCOPES.link_statuses?.[id];
  if (typeof body === "string" && body.trim()) return body;
  return `Definition missing: data/cedar/scopes.json no longer defines link status "${id}".`;
}

export const UNLINKED_REASONS = Object.freeze(
  ["no_individual_named", "withheld", "unresolved"].map((id) =>
    Object.freeze({
      id,
      label: {
        no_individual_named: "It is about a population, not an organization",
        withheld: "The match was invalid",
        unresolved: "The register could not place the named party",
      }[id],
      intentional: id !== "unresolved",
      // The workspace's own words, not a paraphrase of them.
      //
      // Codex, PR #79: this was `?? ""`, so renaming or dropping a key in
      // scopes.json rendered an empty card and every assertion stayed green
      // while the page claimed each definition was held to the file. An
      // absent definition is a broken page, and a broken page should say so
      // where someone can see it rather than render a blank.
      body: requireStatus(id),
    }),
  ),
);

/**
 * What the identifiers make possible, which is the argument for the layer.
 *
 * NO ONE DOMAIN CARRIES THIS. An earlier draft opened every example on a
 * federal contract, which reads as a contracting product with four other
 * datasets attached, and the owner said so. Contracting is one of twelve.
 * Each move below names a different kind of record for that reason.
 */
export const LINKAGE_MOVES = Object.freeze([
  Object.freeze({
    id: "join",
    label: "Join records that were never meant to join",
    body:
      "A Form 990, a royalty disbursement, a lobbying registration, an ANCSA audited filing and a nation's own enterprise register share no key and never will. Cedar puts the same identifier on all five, so a question can cross them.",
  }),
  Object.freeze({
    id: "time",
    label: "Hold an organization still while it changes",
    body:
      "Renames, acquisitions, new subsidiaries, closures and changes in legal status all break a name-matched time series. They do not break an id-keyed one, which is why a twenty-year view of one nation is possible at all.",
  }),
  Object.freeze({
    id: "lineage",
    label: "Read an old record with today's knowledge",
    body:
      "A retired handle keeps resolving. A 2009 NAGPRA notice filed under a former name still reaches the entity that filed it, and the answer says which name was current when.",
  }),
  Object.freeze({
    id: "deeper",
    label: "Follow one answer into the next question",
    body:
      "A nonprofit's filings name a subsidiary. The identifier on that subsidiary reaches its resource revenue, its advocacy and its enterprise structure without a new search. The datasets stop being separate places to look.",
  }),
  Object.freeze({
    id: "ask",
    label: "Ask a question instead of running a search",
    body:
      "A keyword search returns rows whose text matched. A question asked against an identified collection returns an organization's whole footprint, which is what lets Cedar answer something specific and show every record the answer rests on.",
  }),
  Object.freeze({
    id: "operate",
    label: "Hand the answer to someone else",
    body:
      "A cut leaves Cedar carrying the identifiers, the source of every row and the date it was taken. The person who receives it can rebuild it, extend it or join it to their own records without asking Cedar what a row means.",
  }),
]);

/**
 * The loop. Stated as four moments because the claim is that they feed each
 * other, and a bullet list of virtues would not say that.
 *
 * NOTE FOR THE OWNER
 * The first moment says the methods come out of Federal Reserve work and have
 * been rebuilt since. That is a claim about where members of the team learned
 * this, which is the same claim `CREDIBILITY_STRIP` makes, and the expertise
 * section's disclaimer travels with it. It deliberately does not say the
 * Federal Reserve uses Cedar's methods or endorses Cedar, because nothing in
 * the workspace evidences that and an institution named as a user is the one
 * claim on this page a reader could disprove.
 */
export const LOOP_STAGES = Object.freeze([
  Object.freeze({
    id: "methods",
    label: "Methods with a provenance",
    body:
      "The record-linkage work behind the entity layer comes out of the team's years inside the Federal Reserve system, on the problem of resolving organizations across administrative files that disagree. Cedar rebuilt it for records that system never had to read.",
  }),
  Object.freeze({
    id: "machine",
    label: "Machines propose",
    body:
      "Cedar builds and trains its own models on its own resolved records, and uses them where they are strongest: candidate generation, name and address normalization, reading a filing for the subsidiary buried in it.",
  }),
  Object.freeze({
    id: "human",
    label: "A researcher decides",
    body:
      "Every final output passes a person. Ambiguous matches, unusual ownership, conflicting sources and historical changes are ruled on by a researcher who knows what the record means, and the ruling carries its basis.",
  }),
  Object.freeze({
    id: "compound",
    label: "The decision goes back in",
    body:
      "A resolved match becomes evidence for the next ambiguous one. A newly found subsidiary corrects the contracting, nonprofit and transaction records at once. The collection is the input to the next pass over it, so accuracy rises with use rather than decaying.",
  }),
]);

/** The closing line of the loop section, kept here so a test can read it. */
export const LOOP_CLOSE =
  "None of that can be added later. It accumulates one decision at a time, from records that contradict each other, and every decision has to be kept.";
