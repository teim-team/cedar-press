/**
 * The claim classes a finding carries.
 *
 * Confidence and causality are separate dimensions: a finding can be as
 * certain as evidence gets and still be purely descriptive. Each finding names
 * its class, declared by the evidence behind it and never inferred from the
 * sentence. `server/cedar_press/claims.py` holds the same classes.
 */

/**
 * What kind of statement a piece of evidence can support.
 *
 * Seven classes, ordered from what was observed to what was identified. The
 * order matters: Grove may always describe a claim in a weaker class than its
 * evidence allows, and never in a stronger one.
 */
export const CLAIM_CLASS = Object.freeze({
  /** What was observed, in the data, as recorded. */
  descriptive: "descriptive",
  /** A difference between groups, places or periods. */
  comparative: "comparative",
  /** Two things move together or are statistically related. */
  associational: "associational",
  /** Produced by a model rather than observed. */
  modeled: "modeled",
  /** An identified effect, from a design that supports causal inference. */
  causal: "causal",
  /** Establishes the setting rather than proving a finding. */
  contextual: "contextual",
  /** A pattern worth investigating, not yet a finding. */
  exploratory: "exploratory",
});
