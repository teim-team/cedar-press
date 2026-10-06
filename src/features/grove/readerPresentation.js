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

/**
 * Text that was UTF-8, read as Windows-1252 and saved again ("CNSPÃ¢Â‚¬Â„¢S"
 * for "CNSP’S"), repaired for display. Applied only where the telltale
 * sequences appear, at most twice, and abandoned if a pass does not decode.
 */
const CP1252 = { 0x20ac: 0x80, 0x201a: 0x82, 0x192: 0x83, 0x201e: 0x84, 0x2026: 0x85, 0x2020: 0x86, 0x2021: 0x87, 0x2c6: 0x88, 0x2030: 0x89, 0x160: 0x8a, 0x2039: 0x8b, 0x152: 0x8c, 0x17d: 0x8e, 0x2018: 0x91, 0x2019: 0x92, 0x201c: 0x93, 0x201d: 0x94, 0x2022: 0x95, 0x2013: 0x96, 0x2014: 0x97, 0x2dc: 0x98, 0x2122: 0x99, 0x161: 0x9a, 0x203a: 0x9b, 0x153: 0x9c, 0x17e: 0x9e, 0x178: 0x9f };
// Sequences that survive no clean decode (a byte was lost on the way), as
// they appear in source text, mapped to the character they stood for.
const MOJIBAKE_SEQUENCES = [
  ["\u00c3\u00a2\u00c2\u201a\u00c2\u00ac\u00c2\u201e\u00c2\u00a2", "\u2019"],
  ["\u00c3\u00a2\u00c2\u20ac\u00c2\u2122", "\u2019"],
  ["\u00e2\u20ac\u2122", "\u2019"],
  ["\u00e2\u20ac\u02dc", "\u2018"],
  ["\u00e2\u20ac\u0153", "\u201c"],
  ["\u00e2\u20ac\u009d", "\u201d"],
  ["\u00e2\u20ac\u201d", "\u2014"],
  ["\u00e2\u20ac\u201c", "\u2013"],
];
export function repairMojibake(text) {
  let out = String(text ?? "");
  for (const [bad, good] of MOJIBAKE_SEQUENCES) if (out.includes(bad)) out = out.split(bad).join(good);
  for (let pass = 0; pass < 2 && /[\u00c2\u00c3][\u0080-\u00bf\u2018-\u203a\u20ac\u2122\u0152-\u0192]/.test(out); pass += 1) {
    const bytes = [];
    for (const ch of out) {
      const code = ch.codePointAt(0);
      if (code < 0x100) bytes.push(code);
      else if (CP1252[code] != null) bytes.push(CP1252[code]);
      else return out;
    }
    try {
      out = new TextDecoder("utf-8", { fatal: true }).decode(new Uint8Array(bytes));
    } catch {
      return out;
    }
  }
  return out;
}

/**
 * A source system's enumerated code (snake_case or SHOUTING_SNAKE) read as
 * words: "not_evaluated" and "NOT_EVALUATED" as "Not evaluated". Reviewed
 * labels (readerPresentation VALUE_LABELS) are applied before this and win.
 */
export function readableCode(text) {
  const value = String(text ?? "");
  if (!/^(?:[a-z][a-z0-9]*(?:_[a-z0-9]+)+|[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)$/.test(value)) return value;
  const words = value.toLowerCase().replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}
