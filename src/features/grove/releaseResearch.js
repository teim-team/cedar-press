import { isRetiredIdentifierColumn, recordTypeLabel } from "./readerPresentation.js";

/** A transport declaration never turns an unavailable release into a preview. */
export function researchComponents(target) {
  const grouped = Array.isArray(target?.release);
  const values = grouped ? target.release : [target?.release];
  return values.filter(Boolean).map((value) => ({
    component: grouped ? value.component || value.table_id : null,
    label: recordTypeLabel(value, target.name),
    releaseId: value.release_id,
    available: value.kind === "full" && value.status !== "unavailable"
      && /^[a-f0-9]{64}$/.test(value.release_id || "") && Number.isSafeInteger(value.record_count)
      && value.record_count > 0,
    rows: value.record_count,
  }));
}

export function researchFields(packet) {
  const fields = new Map((packet?.codebook?.fields || []).map((field) => [field.name, field]));
  return (packet?.display_order || []).map((name) => fields.get(name)).filter((field) => field
    && !isRetiredIdentifierColumn(field.name)
    && !["internal", "remove", "keep_internal", "keep_internally"].includes(field.display_disposition));
}


/** Count only the same permitted observations advertised by the spreadsheet. */
export function spreadsheetRecordCount(target) {
  const metadata = target?.spreadsheet;
  const parts = researchComponents(target).filter((part) => part.available);
  if (metadata?.kind !== "spreadsheet" || metadata.format !== "csv"
    || !Number.isSafeInteger(metadata.record_count) || metadata.record_count < 0
    || !parts.length || parts.some((part) => part.releaseId !== metadata.release_id)) return null;
  const measured = parts.reduce((total, part) => total + part.rows, 0);
  return Number.isSafeInteger(measured) && measured === metadata.record_count ? measured : null;
}

export function researchValue(value) {
  if (value === null || value === undefined || value === "") return "Not recorded";
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}
