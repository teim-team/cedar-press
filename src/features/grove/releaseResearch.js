/** A transport declaration never turns an unavailable release into a preview. */
export function researchComponents(target) {
  const grouped = Array.isArray(target?.release);
  const values = grouped ? target.release : [target?.release];
  return values.filter(Boolean).map((value) => ({
    component: grouped ? value.component || value.table_id : null,
    label: value.component || value.table_id || target.name,
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
    && !["internal", "remove", "keep_internal", "keep_internally"].includes(field.display_disposition));
}

export function researchValue(value) {
  if (value === null || value === undefined || value === "") return "Not recorded";
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}
