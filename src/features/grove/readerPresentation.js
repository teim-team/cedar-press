/** Reader-facing columns and record labels shared by both preview paths. */
import { tableLabel } from "./readerValues.js";

const RETIRED_TOKENS = new Set(["cicd", "neid", "handle"]);
const RETIRED_COLUMNS = new Set(["tribe_id", "tribe_id_scheme"]);

// These are reviewed display labels, not transformations of source values.
const VALUE_LABELS = {
  need: {
    ownership_extent: { wholly_owned: "Wholly owned" },
    relationship_type: { owned_by: "Owned by" },
  },
  "natural-resources": {
    measurement_status: { reported_revenue: "Reported revenue", appropriated_amount: "Appropriated amount", actual_payment: "Actual payment" },
  },
  owned: { cedar_entity_role: { certifying_authority: "Certifying authority" } },
  lobbying: { amount_basis: { none_reported: "No amount reported" } },
  "federal-register": { participant_role: { not_enumerated: "Not enumerated" } },
};

export function readerValueLabel(collection, column, value) {
  return VALUE_LABELS[collection]?.[column]?.[value] ?? value;
}

/** A named observation is useful even when it has no resolved entity link. */
export function unlinkedRecordSubject(item) {
  if (item.entity?.withheld || item.linkStatus === "withheld") return null;
  if (item.subject) return item.subject;
  if (item.collection === "natural-resources" && item.row?.aggregation_level === "national_aggregate") return "National aggregate";
  return null;
}

/** Retired entity identifiers, never source record IDs or citation publishers. */
export function isRetiredIdentifierColumn(column) {
  const name = String(column ?? "").trim().toLowerCase();
  return RETIRED_COLUMNS.has(name) || name.split("_").some((token) => RETIRED_TOKENS.has(token));
}

/** Use a maintained label when provided, otherwise the existing table-name formatter. */
export function recordTypeLabel(value, fallback = "") {
  const declared = value?.label || value?.title;
  if (typeof declared === "string" && declared.trim()) return declared.trim();
  const name = value?.component || value?.table_id;
  return name ? tableLabel({ table: name }) : fallback;
}

/** A public sample count describes that sample, never the current full dataset. */
export function sampleRecordCount(value) {
  return Number.isSafeInteger(value) && value >= 0 ? value : null;
}
