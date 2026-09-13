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
 * A nation, an agency, an NHO, a consortium and an enterprise a nation owns are
 * all entities, and they get a Cedar entity id: `cedar_uid`, documented in
 * `docs/IDENTIFIER_STANDARD.md`, permanent, encoding nothing, surviving
 * recognition changes and renames and acquisitions.
 *
 * A firm that is Native-owned without being owned by a nation is not an entity
 * in that sense, and Cedar does not promote it to one. It gets a business id at
 * the source-record layer (`business_source_id`) and, once resolved, an
 * `entity_id` in the harmonized business registry. It carries that id from the
 * first sighting, because the day a nation acquires the firm the history has to
 * already exist. A history you start keeping on the day it becomes interesting
 * is not a history.
 *
 * EVIDENCE, NOT ASSERTION
 * Every class code named below is a class the published register really holds,
 * and every field named below is a field the registry schemas really declare.
 * `pressIdentity.test.js` reads `public/data/cedar/register.json` and
 * `cedar_source_registry/schema/*.json` and fails if either drifts. It also
 * pins the withholding claim: the register ships the individually owned firms
 * with a uid and no name, which is the whole point of the second identifier
 * and would be a lie to state if the file stopped doing it.
 *
 * COPY DISCIPLINE
 * Brand lock in CLAUDE.md: no em dashes, no antithesis ("not X, it's Y"), and
 * no sentence that ends in a comma and a fragment.
 */

/** The published register the test reads, and the app already fetches. */
export const REGISTER_SOURCE = "data/cedar/register.json";

/**
 * The two identifiers, as the page renders them.
 *
 * `classes` are register class codes this identifier covers, checked against
 * the published register. `fields` are schema field names, checked against the
 * registry schemas. `survives` is what the identifier is designed to outlive,
 * which is the only reason to have minted it in the first place.
 */
export const IDENTIFIERS = Object.freeze([
  Object.freeze({
    id: "entity",
    label: "Cedar entity id",
    shape: "CE-1A7K3-MQ",
    fields: Object.freeze(["cedar_uid"]),
    names:
      "A government, an agency, an NHO, a consortium, a college, a CDFI, a nonprofit, or an enterprise a nation owns.",
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
      "A nation or an enterprise renames",
      "An enterprise is reorganized under a new parent",
    ]),
    note:
      "The id encodes nothing, so nothing about the entity can force it to be rewritten. Two check characters catch every single-character transcription error and every adjacent transposition on the live register.",
  }),
  Object.freeze({
    id: "business",
    label: "Cedar business id",
    // NO SAMPLE ON PURPOSE, and this is not an oversight.
    //
    // The entity card can show CE-1A7K3-MQ because that form is minted, in
    // `data/spine/cedar_identity_register.csv`, and documented in
    // docs/IDENTIFIER_STANDARD.md. The business id's customer-facing form is
    // `CB-0000001`, decided by the owner on 2026-09-06 and recorded in
    // docs/CEDAR_BUSINESS_ID_DECISION_2026-09-06.md, and nothing in the
    // workspace mints it yet. This card showed `TBD-030:4033` for a day,
    // which is a `business_source_id`: real, but a source-record key with a
    // source code inside it, and the decision's first rule is that the
    // number means nothing. Showing it as the Cedar business id was showing
    // the reader the wrong object.
    //
    // The concept ships today under the two field names below. The sample
    // goes back the day CB- is minted, and not before.
    shape: null,
    fields: Object.freeze(["business_source_id", "entity_id"]),
    names:
      "A firm, as one source named it, and then the resolved firm those sightings add up to.",
    classes: Object.freeze(["Individually Native-owned business"]),
    survives: Object.freeze([
      "A firm appears in four directories under four spellings",
      "A certifying office and a nation disagree about it",
      "A nation acquires the firm and it becomes an enterprise",
    ]),
    note:
      "One per business, stable, never reused. It means nothing on purpose: ownership, state, trade and size all change, and an identifier that encodes any of them has to be rewritten the day it does. An individually owned firm carries a business id and no entity id, from the first sighting, so the record is continuous if a nation later buys it.",
  }),
]);

/**
 * The class the PUBLIC LOOKUP withholds names for, and what that does and
 * does not mean.
 *
 * The owner's challenge, 2026-09-13: "isn't that wrong that it doesn't publish
 * what it resolves?" It would be, and Cedar does publish it. What is withheld
 * is narrower than the earlier copy on this page implied, and the distinction
 * is the whole judgement:
 *
 * - The storefront's Individually Owned Native Businesses collection publishes
 *   these firms BY NAME, because a nation's own TERO or commerce office
 *   published them and shared them under stated terms. The name is the
 *   nation's to give and it gave it.
 * - Where the only evidence is a federal award file, the firm's activity
 *   publishes and the owner's name, address and UEI do not
 *   (`INDIVIDUAL_NATIVE_WITHHELD_FIELDS` in `code/cedar_domain.py`). A person
 *   who won a contract did not consent to being enumerated and ranked by
 *   obligations, and their own website saying they are Native is evidence,
 *   never permission. The rule is per field, defaults to withholding, and
 *   suppresses any published cell resolving to fewer than three firms.
 * - `register.json`, the entity lookup this whole site can read, withholds the
 *   name for this class outright, because it is a lookup and not a release.
 *
 * `pressIdentity.test.js` pins the last of those three against the published
 * file. The identifier is on the firm in all three cases, which is the point.
 */
export const WITHHELD_CLASS = "Individually Native-owned business";

/** What Cedar publishes about a firm it will not name, said plainly. */
export const WITHHELD_NOTE =
  "A firm carries its business id whether or not its name is ever published. Where a nation's own commerce office published its certified businesses and shared them under stated terms, they are in the collection by name. Where the only evidence is a federal award file, the activity publishes and the owner's name and address do not, because a person who won a contract did not consent to being ranked by obligations. The identifier holds both cases in one series.";

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
  "None of that is a feature that can be added later. It is an accumulation of decisions about records that contradict each other, and the decisions are the asset.";
