/**
 * PURPOSE
 * The citation register: every known public use of a Cedar Press dataset.
 *
 * A dataset that gets cited in public earns trust in public, so the register
 * is part of the method, not marketing. Each entry records who cited the
 * data, which dataset and version they used, where the piece appeared and
 * when. Citations arrive two ways: readers report them (the page carries the
 * address), and the partnership watches for them; an automated watch that
 * feeds this same register is server work for later, and this module is the
 * single shape both paths write into.
 *
 * The register launches EMPTY on purpose. Inventing entries would be
 * fabricated proof, exactly what the datasets exist to replace; the page
 * renders an honest counting-begins state until the first real citation
 * lands.
 */

/** Where a reader reports a citation the register missed. */
export const REPORT_CITATION_HREF =
  "mailto:contact@lumecon.ai?subject=Cedar%20Press%20citation";

/**
 * Entries, newest first. Shape:
 * { id, datasetId, version, outlet, piece, href, date }
 * `datasetId` must name a launch-collection dataset and `version` the release
 * the citing piece used, because a correction to that release must be able to
 * find everyone who relied on it.
 */
export const CITATIONS = Object.freeze([]);

/** How many recorded citations name a dataset. */
export function citationCountFor(datasetId) {
  return CITATIONS.filter((entry) => entry.datasetId === datasetId).length;
}
