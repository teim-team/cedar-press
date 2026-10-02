/** Reader-facing columns and record labels shared by both preview paths. */
import { tableLabel } from "./readerValues.js";

const RETIRED_TOKENS = new Set(["cicd", "neid", "handle"]);
const RETIRED_COLUMNS = new Set(["tribe_id", "tribe_id_scheme"]);

// These are reviewed display labels, not transformations of source values.
const VALUE_LABELS = {
  "foundation-corporate-giving": {
    financial_status: { committed: "Committed", pledged: "Pledged", authorized: "Authorized", paid: "Paid", unpaid_balance: "Unpaid balance", committed_increment: "Commitment increment", unknown: "Financial status not established" },
    amount_basis: { commitment: "Commitment", commitment_increment: "Commitment increment", payment: "Payment", future_payable: "Future payable", reported_grant: "Reported grant" },
    amount_class: { exact: "Exact amount", range: "Reported range", unstated: "Amount not stated" },
    record_kind: { grant_event: "Grant-related disclosure", recipient_year_total: "Recipient-year total" },
  },
  need: {
    ownership_extent: { wholly_owned: "Wholly owned", majority: "Majority owned" },
    relationship_type: { owned_by: "Owned by", subsidiary_of: "Subsidiary of", affiliated_with: "Affiliated with" },
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

/** Claim-scoped NEED keeps an affiliation counterpart separate from ownership. */
export function reviewedNeedColumns(columns) {
  if (!["enterprise_name", "owner_name", "ownership_extent", "evidence_pins"].every(column => columns.includes(column))) return null;
  const counterpart = columns.includes("related_entity_name") ? "related_entity_name" : "owner_name";
  return {
    observation: [counterpart, "relationship_type", "ownership_extent"].filter(column => columns.includes(column)),
    defaults: ["enterprise_name", counterpart, "relationship_type", "ownership_extent", "uei", "cage_code", "record_grain"].filter(column => columns.includes(column)),
  };
}
