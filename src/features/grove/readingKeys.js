// REVIEW OWNER: Havala
//
// How to read the records of the two collections whose columns need a key
// (owner, 2026-10-06: "PLOT and NEED break out what they need to ... we'll
// have to train people what those mean").
//
// Every meaning here restates the codebook's own definition of the column
// (data/cedar/codebook.json, tables need/need and plot/plot) in plain words,
// and every value named is one that appears in the published rows. Nothing
// here is a figure, so nothing here can go stale against a release; a new
// value the producer starts writing is the one thing to add.

const term = (name, meaning) => Object.freeze({ term: name, meaning });

export const READING_KEYS = Object.freeze({
  need: Object.freeze({
    intro:
      "Each row is one enterprise that a Native entity owns or is tied to, checked by a reviewer against the owner's own sources. A blank field has not been reviewed yet; it never means no or zero.",
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
  plot: Object.freeze({
    intro:
      "Each row is one piece of land as a public land record reports it: a county assessor's tax parcel or a Bureau of Indian Affairs trust tract. The owner is what the record says, not a verified title.",
    terms: Object.freeze([
      term("Land record kind", "assessor parcel: a county tax parcel. BIA tract: a Bureau of Indian Affairs trust or restricted tract."),
      term("Parcel ID", "The parcel's or tract's identifier in its source. It is unique only within that county or BIA register."),
      term("Owner as recorded", "The owner exactly as the assessor or the BIA lists it. “United States in trust for” a nation means trust land the United States holds for that nation."),
      term("Record role", "assessor_owner_name_candidate: a county lists an owner that names a Native entity. bia_source_reported_tribal: the BIA reports the tract as tribal."),
      term("Ownership code", "The source's own ownership category, such as the BIA's T for tribal."),
      term("Estate type and trust status", "Whether the interest is surface, mineral or both, and its trust standing, where the source states them; unknown where it does not."),
      term("Acres", "Land area as the source records it. Check the acres measure (assessor-recorded acres or BIA tract acres) before adding rows together."),
      term("Tax", "The assessor's net property tax for the stated tax year. “Not cleared for ownership totals” means it should not be summed by owner."),
      term("Owner time basis", "When the owner listing applies, for example the current owner when the county submitted its data rather than the tax-roll year."),
      term("County FIPS", "The county's five-digit federal code."),
    ]),
  }),
});

/** The reading key for a collection, or null where its columns need none. */
export function readingKey(collectionId) {
  return READING_KEYS[collectionId] ?? null;
}
