/**
 * Legacy fallback for catalog entries without a verified preview release.
 * Every current Press collection has a measured preview. Record definitions
 * come from the exact release codebook rather than a parallel imagined schema.
 */
export const RECORD_STRUCTURE = Object.freeze({});
export const RECORD_STRUCTURE_TITLE = "What each record holds";
export function recordStructure(collectionId) {
  return RECORD_STRUCTURE[collectionId] ?? null;
}
