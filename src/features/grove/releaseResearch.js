/** A transport declaration never turns an unavailable release into a download. */
export function researchComponents(target) {
  const grouped = Array.isArray(target?.release);
  const values = grouped ? target.release : [target?.release];
  return values.filter(Boolean).map((value) => ({
    component: grouped ? value.component || value.table_id : null,
    releaseId: value.release_id,
    available: value.kind === "full" && value.status !== "unavailable"
      && /^[a-f0-9]{64}$/.test(value.release_id || "") && Number.isSafeInteger(value.record_count)
      && value.record_count > 0,
    rows: value.record_count,
  }));
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
