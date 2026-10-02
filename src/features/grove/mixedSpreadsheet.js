/** Reviewed presentation of mixed-grain producer spreadsheets.
 * Field mappings come from the verified spreadsheet plan, never from row values.
 * This module neither changes publication rights nor creates identity bindings.
 */
export const PRESENTATION_COLUMNS = Object.freeze({
  __subject: "Record subject",
  __date: "Date and basis",
  __observation: "Observation",
  __amount: "Reported amount",
});

const PLOT_TYPES = Object.freeze({
  tract_observations: { label: "Tract observation", subject: ["source_parcel_id", "plot_record_id"], date: "source_snapshot_date", date_basis: "Source snapshot", observation: ["record_role", "source_ownership_code", "estate_type", "trust_status"] },
  ownership_observations: { label: "Ownership observation", subject: ["source_parcel_id", "plot_record_id"], date: "ownership_observation_date", year: "ownership_observation_year", date_basis: "Ownership observation", observation: ["owner_name_raw", "record_role", "estate_type", "trust_status"] },
  permits: { label: "Permit observation", subject: ["permit_number", "source_permit_id", "permit_id"], date: "issued_date", date_basis: "Permit issue date", observation: ["authority_name", "permit_type_raw", "program", "status_raw"] },
  permit_events: { label: "Permit event", subject: ["permit_id", "permit_event_id"], date: "event_date", date_basis: "Reported event date", observation: ["event_type", "status_raw", "authority_name"] },
  environmental_permits: { label: "Environmental permit", subject: ["source_permit_id", "environmental_record_id"], date: "issued_date", date_basis: "Permit issue date", observation: ["facility_name_raw", "program", "status_raw"] },
  environmental_events: { label: "Environmental event", subject: ["environmental_record_id", "environmental_event_id"], date: "event_date", date_basis: "Reported event date", observation: ["event_type", "program", "status_raw"] },
});
const GIVING_TYPES = new Set(["policy_eligible_disclosures", "reviewed_disclosures"]);

export function mixedSpreadsheetContract(collection, columns, fieldsByType) {
  if (!["foundation-corporate-giving", "plot"].includes(collection)) return null;
  if (!fieldsByType || typeof fieldsByType !== "object" || Array.isArray(fieldsByType) || !Object.keys(fieldsByType).length) {
    throw new Error(collection + ": verified per-type field mappings are required");
  }
  for (const column of ["record_type", "record_key", "record_grain"]) {
    if (!columns.includes(column)) throw new Error(collection + ": missing " + column);
  }
  const base = {
    mapping_kind: "producer_spreadsheet", reviewed: true,
    review_reason: "Exact source fields are dispatched by their verified record type. No ownership, Native identity, payment, or title is inferred.",
    record_id: "record_key", record_type: "record_type",
    entity_uid: null, entity_name: null, entity_type: null, entity_role_column: null,
    entity_roles: [], entity_uid_list: false, entity_name_list: false,
    entity_type_list: false, entity_role_list: false,
    subject: null, source: null, source_fallback: null, date: null, year: null,
    year_basis: null, amount: null, amount_basis: null, amount_label: null,
    scopes: null, link_status: null, superseded: null, superseded_by: null,
    observation: [], search: [], row_type_contracts: {},
    default_columns: collection === "plot"
      ? ["__subject", "record_type", "__observation", "__date"]
      : ["__subject", "record_type", "__observation", "__amount", "__date"],
  };
  for (const [kind, mapping] of Object.entries(fieldsByType)) {
    if (!mapping || typeof mapping !== "object" || Array.isArray(mapping)) throw new Error("Invalid component field map");
    for (const [field, column] of Object.entries(mapping)) {
      if (!field || typeof column !== "string" || !columns.includes(column)) throw new Error(kind + ": absent mapped field " + field);
    }
    const field = (name) => mapping[name] ?? null;
    const first = (names) => names.map(field).find(Boolean) ?? null;
    const sources = Object.fromEntries(Object.entries(mapping));
    if (collection === "foundation-corporate-giving") {
      if (!GIVING_TYPES.has(kind)) throw new Error("Unreviewed Giving record type: " + kind);
      const subjectCandidates = ["recipient_name", "recipient_name_reported"].map(field).filter(Boolean);
      const subject = subjectCandidates[0] ?? null;
      if (!subject || !field("funder_name") || !field("source_url")) throw new Error(kind + ": Giving subject/funder/source missing");
      base.row_type_contracts[kind] = {
        label: kind === "reviewed_disclosures" ? "Reviewed disclosure" : "Permitted disclosure",
        subject, subject_candidates: subjectCandidates, subject_entity_role: "recipient", entity_uid: field("cedar_uid"), entity_name: null,
        entity_type: field("recipient_entity_type"), entity_role: "recipient",
        source: field("source_url"), source_fallback: null, source_fields: sources,
        date: field("announcement_date"), year: field("report_year"),
        date_basis: "Announcement date",
        year_basis: "Source-reported year",
        amount: field("amount_exact_usd"), amount_basis: field("amount_basis"),
        amount_qualifiers: ["financial_status", "amount_class"].map(field).filter(Boolean),
        amount_lower: field("amount_lower_usd"), amount_upper: field("amount_upper_usd"),
        amount_class: field("amount_class"), amount_label: "Reported nominal USD",
        observation: ["funder_name", "financial_status", "record_kind", "report_year_basis"].map(field).filter(Boolean),
        search: [...subjectCandidates, field("funder_name")],
      };
    } else {
      const spec = PLOT_TYPES[kind];
      if (!spec) throw new Error("Unreviewed PLOT record type: " + kind);
      const subjectCandidates = spec.subject.map(field).filter(Boolean);
      const subject = subjectCandidates[0] ?? null;
      const source = first(["source_record_url", "source_url"]);
      if (!subject || !source) throw new Error(kind + ": PLOT subject/source missing");
      base.row_type_contracts[kind] = {
        label: spec.label, subject, subject_candidates: subjectCandidates, entity_uid: null, entity_name: null, entity_type: null,
        entity_role_column: null, entity_role: null, entity_roles: [],
        source, source_fallback: source === field("source_record_url") ? field("source_url") : null,
        source_fields: sources, date: field(spec.date), year: spec.year ? field(spec.year) : null,
        date_basis: spec.date_basis, year_basis: spec.date_basis + " year; not acquisition or payment",
        amount: null, amount_basis: null, amount_label: null,
        observation: spec.observation.map(field).filter(Boolean),
        search: [...subjectCandidates, ...spec.observation.map(field).filter(Boolean)],
      };
    }
  }
  return base;
}
