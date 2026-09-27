/**
 * REVIEW OWNER: Havala
 *
 * What each record holds, for the collections Cedar Press presents by their
 * record structure: Foundation & Corporate Giving and PLOT.
 *
 * Both are live on their plans like every other collection on their shelf
 * (owner, 2026-09-27: "treat PLOT and Foundation & Corporate Giving as
 * published and live everywhere"). Neither has sample rows in this
 * repository, so where a viewer would show sample records it shows this
 * instead, in the same frame: each field and what it means. Nothing here is
 * a record, a count, a figure or a date range, and nothing may become one:
 * no row count and no year span is stated for either collection anywhere,
 * rather than a placeholder standing in for one.
 *
 * SOURCES
 *   foundation-corporate-giving  the producer's `FIELDS`, in its order
 *                                (teim-team/Lumecon-data,
 *                                `src/lumecon_data/collections/foundation_release.py`,
 *                                f917e6e), with meanings from the same
 *                                repository's `docs/foundation-giving-contract.md`.
 *                                `pressJobs.test.js` holds the names to a
 *                                copy of that list.
 *   plot                         the owner's description of a PLOT record
 *                                (2026-09-27): owner or entity, parcel ID,
 *                                transfers, parcel characteristics, geometry,
 *                                permits, development activity, dates,
 *                                source. No producer exists in any
 *                                repository, so these are the owner's
 *                                headings rather than column names.
 *
 * HOUSE STYLE: plain sentences, "and" never an ampersand, no em dash.
 */

const field = (name, meaning) => Object.freeze({ name, meaning });

export const RECORD_STRUCTURE = Object.freeze({
  "foundation-corporate-giving": Object.freeze({
    // The producer's own column names, so a reader who later opens the file
    // meets the same words.
    kind: "columns",
    // One sentence for surfaces that describe rather than list (Cedar on
    // the door): the same fields, in plain words, with no figure.
    summary:
      "Each record is one disclosure: the funder, the legal recipient and, where review established one, its Cedar entity, the purpose, the amount as disclosed, its financial status, the dates and the source.",
    fields: Object.freeze([
      field("disclosure_id", "Stable identifier for one disclosure: its source, funder, published recipient and report year."),
      field("award_id", "Joins versions of the same award where a reviewed source links them; blank when they cannot safely be joined."),
      field("version_kind", "Whether the disclosure is an original, amended, renewed or expanded award, or unknown."),
      field("funder_name", "The foundation, corporation or bank that reported the funding."),
      field("recipient_name", "The legal recipient, as the source published it."),
      field("cedar_uid", "The Cedar identifier of the Native entity that received it, where review established one."),
      field("recipient_entity_type", "The kind of organization the recipient is."),
      field("recipient_affiliation", "The recipient's Native affiliation as the source supports it, kept apart from its legal identity."),
      field("purpose", "What the funding is for, as disclosed."),
      field("amount_exact_usd", "The exact amount in US dollars, when the source states one."),
      field("amount_lower_usd", "The lower bound in US dollars, when the source gives a range."),
      field("amount_upper_usd", "The upper bound in US dollars, when the source gives a range."),
      field("amount_aggregate_usd", "A program amount the source did not allocate to this recipient."),
      field("financial_status", "Whether the amount is committed, pledged, authorized, paid, an unpaid balance or unknown."),
      field("announcement_date", "When the funding was announced."),
      field("report_year", "The year the source reports the funding in."),
      field("award_period_text", "The award period as published, kept as text when the source gives no exact dates."),
      field("project_geography", "Where the funded work takes place, or the recipient's state."),
      field("source_url", "Where the disclosure was published."),
      field("source_document_sha256", "A fingerprint of the source document as retrieved, so the citation can be checked."),
      field("source_retrieved_date", "When the source was retrieved."),
      field("source_class", "The kind of publisher the disclosure comes from, such as a public filing or a first-party announcement."),
      field("source_id", "The registered source the disclosure came from."),
      field("publication_rights_status", "The basis on which the facts are published: derived facts with a citation, never the source's text."),
      field("overlap_status", "Whether the disclosure was reviewed against others that may report the same funding."),
      field("addability_status", "Whether the amount may be added to others; disclosures are a view of funding, not a ledger to total."),
      field("observation", "One plain sentence stating the fact the record holds."),
    ]),
  }),
  plot: Object.freeze({
    // The owner's headings for a PLOT record.
    kind: "headings",
    summary:
      "Each record follows one parcel: its owner or entity, parcel ID, transfers, parcel characteristics, geometry, permits, development activity, dates and source.",
    fields: Object.freeze([
      field("Owner or entity", "The Native nation, organization or enterprise the parcel is associated with, linked to its Cedar entity."),
      field("Parcel ID", "The parcel's identifier in the public record it comes from."),
      field("Transfers", "Recorded changes in ownership, with the parties to each."),
      field("Parcel characteristics", "The parcel's recorded attributes, such as its size and land use."),
      field("Geometry", "The parcel's boundary, for mapping."),
      field("Permits", "Permits recorded against the parcel."),
      field("Development activity", "Construction and other development recorded on the parcel."),
      field("Dates", "When each transfer, permit and development event was recorded."),
      field("Source", "The public record each fact comes from, so it can be checked."),
    ]),
  }),
});

/** The heading every surface gives the field list (owner copy). */
export const RECORD_STRUCTURE_TITLE = "What each record holds";

/** A collection's record structure, or null when it shows sample records instead. */
export function recordStructure(collectionId) {
  return RECORD_STRUCTURE[collectionId] ?? null;
}
