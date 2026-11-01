// REVIEW OWNER: Havala
//
// How to read the records of a collection whose columns need a key (owner,
// 2026-10-06: "we'll have to train people what those mean"). NEED is the one
// left.
//
// Every meaning here restates the codebook's own definition of the column
// (data/cedar/codebook.json, table need/need) in plain words,
// and every value named is one that appears in the published rows. Nothing
// here is a figure, so nothing here can go stale against a release; a new
// value the producer starts writing is the one thing to add.

const term = (name, meaning) => Object.freeze({ term: name, meaning });

export const READING_KEYS = Object.freeze({
  need: Object.freeze({
    intro:
      "NEED is the Native Entity Enterprise Dataset. Each row is one enterprise that a Native entity owns or is tied to, checked by a reviewer against the owner's own sources. A blank field has not been reviewed yet; it never means no or zero.",
    terms: Object.freeze([
      term("Enterprise", "The business, as Cedar's enterprise register names it. The name the source printed is kept beside it."),
      term("Owner", "The company that owns the enterprise, shown only where a reviewer confirmed it from a source."),
      term("Relationship", "Subsidiary of: the enterprise is the owner's subsidiary. Owned by: the owner owns it. Affiliated with: the two are tied, with no ownership stated."),
      term("Owner scope", "Immediate: the owner is the direct legal parent. Ultimate: the owner sits at the top of the chain."),
      term("Ownership extent", "Wholly owned or majority owned, only where a source says so. \u201cNot provided\u201d means no source states it."),
      term("UEI and CAGE", "The enterprise's federal contracting identifiers (SAM.gov Unique Entity ID and CAGE code), included only where primary evidence confirms them."),
      term("Verified claims", "The facts on the row that were independently confirmed, such as identity, UEI, CAGE code, subsidiary or ownership. A fact not listed is unreviewed, not false."),
      term("Subject binding", "How the source was matched to this enterprise: by its exact UEI, by its exact CAGE code, or by a reviewed profile link. Never by a shared name."),
      term("Reviewed on", "When a reviewer checked the evidence, not when the relationship began."),
    ]),
  }),
});

/** The reading key for a collection, or null where its columns need none. */
export function readingKey(collectionId) {
  return READING_KEYS[collectionId] ?? null;
}
