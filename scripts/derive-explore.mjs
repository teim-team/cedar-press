import { reviewedNeedColumns } from "../src/features/grove/readerPresentation.js";
import { mixedSpreadsheetContract, PRESENTATION_COLUMNS } from "../src/features/grove/mixedSpreadsheet.js";
// Derive each collection's EXPLORE CONTRACT from its customer table, and
// record it in data/cedar/explore.json.
//
// Since 2026-10-04 the card reads one flat customer table per collection
// (public/data/cedar/downloads/<id>.csv, rendered by
// scripts/render_sample_downloads.py through the vendored customer_sheet
// rules), not the raw multi-table producer previews, which are no longer
// served. `customerTableContract` is the rule; the producer-spreadsheet
// rules below it stay for the tests that pin their behaviour.
//
//     node scripts/derive-explore.mjs            # write the contracts
//     node scripts/derive-explore.mjs --check    # exit 1 if the file is stale
//
// WHAT A CONTRACT IS
// The Explore card on the Collections page shows every table through the
// same three filters (entity, entity type, year) and, across collections,
// the same seven summary columns (entity, entity type, collection, date,
// observation, amount, source). No page may hard-code which of a table's
// columns those are: the lobbying table calls its year `filing_year`, the
// deals table `Event_Year`, the NAGPRA table `publication_year`. The contract
// names them, once, per table, and the card reads it.
//
// DERIVED, THEN OVERRIDDEN, NEVER TYPED INTO THE CARD. The rules below read
// the sample's header and pick columns by name. Where a rule picks wrong or
// picks nothing, `data/cedar/explore.overrides.json` says so for that one
// table, in the open, and the override wins. The tests fail on a shipped
// table with no contract, and on a stale file, naming this command.
//
// The importer should run this after copying the samples; until it does, it
// is run by hand and the check keeps it honest.
//
// TRACKED BY FORCE, like the manifest, the ledger and the publication record
// beside it: `/data/*` is ignored as a directory.

import { existsSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { isInternalProvenanceColumn, namesInternalFile } from "../src/features/grove/readerValues.js";

const REPO = fileURLToPath(new URL("..", import.meta.url));
const MANIFEST = `${REPO}data/cedar/collections.manifest.json`;
const OVERRIDES = `${REPO}data/cedar/explore.overrides.json`;
const OUT = `${REPO}data/cedar/explore.json`;
const PUBLIC = `${REPO}public`;
const NAMES = `${REPO}data/spine/cedar_entity_names.csv`;
const TYPES = `${REPO}data/spine/cedar_entity_types.csv`;
const IDENTITY = TYPES.replace(/cedar_entity_types\.csv$/, "cedar_identity_register.csv");
const REGISTER = `${PUBLIC}/data/cedar/register.json`;
// The customer tables (one per collection) the Explore card reads.
const DOWNLOADS = `${PUBLIC}/data/cedar/downloads`;

// Until 2026-10-02 the register withheld the name of every entity in this
// class (null name, uid and class only), mirroring
// code/cedar_domain.py may_publish_individual_native_field, which released a
// name only on recorded OPTED_IN consent. Owner ruling 2026-10-02: a firm is
// a business entity regardless of what it is named after, and its name,
// identifiers and business address are public business records (SAM and
// USAspending publish them for every federal awardee), so the rule now
// publishes every such field and the register carries every name. The class
// is still named so the count the register reports is measured against it,
// and so the viewer's null-name masking (explore.js) keeps a defined meaning:
// a null name is one the rule withholds, and today the rule withholds none.
const WITHHELD_CLASS = "Individually Native-owned business";
const WITHHELD_FIELD_PUBLISHES = true; // owner ruling 2026-10-02

// Column names are matched lowercased, in this order; the first present wins.
const RULES = {
  entity_uid: [
    "cedar_uid", "cedar_uids", "entity_cedar_uid", "owner_hub_cedar_uid", "resolved_native_entity_id",
    "sub_cedar_uid", "prime_cedar_uid", "cedar_entity_id", "entity_id", "entity_cedar_uids",
  ],
  entity_name: [
    "canonical_name", "canonical_names", "cedar_spine_canonical_name", "native_party_canonical_name",
    "tribe_canonical_name", "owner_hub_name", "cedar_entity_name", "tribe_name", "entity_name",
    "native_party", "client_name", "participant_name_as_published", "witness_organization",
    "recipient_name", "awardee_name", "sub_awardee_name", "enterprise_name", "name",
  ],
  entity_type: [
    "entity_type", "entity_class", "entity_classes", "cedar_native_entity_class", "cedar_spine_entity_class",
    "owner_hub_entity_class", "native_party_type", "entity_class_scope",
  ],
  year: ["fiscal_year", "filing_year", "event_year", "publication_year", "tax_year", "year"],
  date: [
    "action_date", "event_date", "hearing_date", "activity_date", "notice_date",
    "event_start_date", "publication_date", "payment_date", "subaward_date", "introduced_date",
    "filing_date", "dt_posted", "posted_date", "letter_date", "communication_file_date",
    "award_date", "date",
  ],
  amount: [
    "spend_usd", "obligated_usd", "amount_usd", "announced_value_usd", "total_award_value",
    "subaward_amount", "income_usd", "expenses_usd", "total_obligations", "face_value_of_loan",
    "total_lobbying_expenditures", "award_amount", "amount",
  ],
  source: [
    "source_url", "filing_url", "testimony_url", "document_url", "notice_url", "html_url", "source_1", "url",
  ],
  // The record's own identifier, so a row can be cited and found again.
  record_id: [
    "filing_uuid", "deal_id", "document_number", "assistance_transaction_unique_key",
    "contract_transaction_unique_key", "consultation_event_id", "bill_id", "enterprise_id",
    "resource_revenue_event_id", "subaward_source_record_id", "ein",
  ],
  // Who the record itself names, which is not always the resolved entity:
  // a subsidiary awardee, a registrant's client, the museum holding remains.
  subject: [
    "recipient_name", "client_name", "awardee_name", "sub_name", "enterprise_name",
    "recipient_entity_name", "org_name", "native_party", "institution_name",
    "participant_name_as_published",
  ],
  superseded: ["is_superseded", "supersession_status"],
  // The producer renamed the lobbying key from filing_uuid to record_id
  // (2026-10-01 release); the replacement link followed the old name until
  // 2026-10-02 and so was never offered for a superseded filing.
  superseded_by: ["superseded_by_record_id", "superseded_by_filing_uuid"],
  amount_basis: ["spend_basis", "value_type", "amount_sign_meaning", "measurement_status"],
};

/** "filing_year" -> "filing year", for the label over the year control. */
const words = (column) => column.replace(/_/g, " ").toLowerCase();

// Columns that describe the row, for the one-line observation, most telling
// first. A table gets up to four of the ones it has.
const OBSERVATION = [
  "hearing_title", "deal_title", "title", "subject_as_published", "subject", "topic",
  "filing_type_display", "registrant_name", "witness_name", "witness_title", "committee",
  "program", "program_name", "cfda_title", "awarding_agency_name", "agency", "agency_names",
  "description", "award_description", "transaction_description", "deal_category",
  "consultation_type", "sector", "relationship", "government_entities", "specific_issues_text",
  "product_or_service_description", "naics_description", "status", "city", "state",
];

// Never an observation column: identity, bookkeeping and money live elsewhere.
const NOISE = /(_id$|_uid|_uids$|_date$|^dt_|_year$|_usd|_amount$|_value$|_flag$|_basis$|_code$|^is_|_url$|uei|cage|_hash|_normalized$|_verbatim$|_quote$|^n_|_count$|_pct$|_percent|_rank|_score|confidence|tier|_uid_)/i;

const norm = (name) => name.trim().toLowerCase();

function header(path) {
  const text = readFileSync(path, "utf8");
  const line = text.slice(0, text.indexOf("\n") < 0 ? text.length : text.indexOf("\n")).replace(/^\uFEFF/, "");
  const out = [];
  let cell = "";
  let quoted = false;
  for (const ch of line) {
    if (ch === '"') quoted = !quoted;
    else if (ch === "," && !quoted) { out.push(cell); cell = ""; }
    else cell += ch;
  }
  out.push(cell);
  return out.map((c) => c.replace(/\r$/, ""));
}

function pick(columns, wanted) {
  const byNorm = new Map(columns.map((c) => [norm(c), c]));
  for (const name of wanted) if (byNorm.has(name)) return byNorm.get(name);
  return null;
}

// A fallback by shape, for tables whose names the lists do not know.
function pickShape(columns, pattern, exclude) {
  return columns.find((c) => pattern.test(norm(c)) && !(exclude && exclude.test(norm(c)))) ?? null;
}

/**
 * The columns whose values name Cedar's own files, scripts or paths in the
 * sample: `source_dataset = ferc_ex_parte_parties.csv`, `source_or_forum =
 * data/clean/gaming_land_decisions.csv (...)`. Real lineage, and never the
 * one-line observation a reader scans: the observation is what the RECORD
 * says, and these say how Cedar handled it.
 */
export function internalValueColumns(rows) {
  const hit = new Set();
  for (const row of rows) {
    for (const [column, value] of Object.entries(row)) {
      if (!hit.has(column) && value && namesInternalFile(value)) hit.add(column);
    }
  }
  return hit;
}

export function contractFor(columns, rows = []) {
  const internal = internalValueColumns(rows);
  const lineage = (col) => internal.has(col) || isInternalProvenanceColumn(col);
  const c = {};
  c.entity_uid = pick(columns, RULES.entity_uid) ?? pickShape(columns, /cedar_uid$/, /candidate/);
  // The approved plural block and the older pipe lists are lists; the
  // overrides may still say so in their own words.
  if (c.entity_uid && /_uids$|_ids$/.test(c.entity_uid)) c.entity_uid_list = true;
  c.entity_name = pick(columns, RULES.entity_name) ?? pickShape(columns, /canonical_name$/, null);
  c.entity_type = pick(columns, RULES.entity_type) ?? pickShape(columns, /entity_class$/, /scope/);
  c.year = pick(columns, RULES.year) ?? pickShape(columns, /_year$/, /base_year|built|report_year|fetched/);
  c.date = pick(columns, RULES.date)
    ?? pickShape(columns, /_date$/, /fetched|built|ruling|promoted|keyed|deadline|withdrawn|termination|modified|extract|refusal|probed|checked|retrieved|inactivated|release/);
  c.amount = pick(columns, RULES.amount) ?? pickShape(columns, /(_usd|_amount)$/, /real2025|inflation|_pct|share/);
  c.source = pick(columns, RULES.source) ?? pickShape(columns, /url$/, /candidate|allocation|evidence/);
  // A record id or none: the first column is not an identifier, and a
  // repeated value there gave ten records one id (Codex, PR #63). A table
  // with none falls back to its position in the sample.
  c.record_id = pick(columns, RULES.record_id)
    ?? pickShape(columns, /(_id|_uuid|_key|_number)$/, /entity|cedar|parent|prime_award|sub_|companion|sponsor|source_record|report/)
    ?? null;
  c.subject = pick(columns, RULES.subject);
  if (c.subject === c.entity_name) c.subject = null;
  c.superseded = pick(columns, RULES.superseded);
  c.superseded_by = pick(columns, RULES.superseded_by);
  c.amount_basis = c.amount ? pick(columns, RULES.amount_basis) : null;
  // What "year" means here, said in the table's own terms. A table with a
  // year column filters on that column and only that column; one with just
  // a date filters on the date's calendar year, and the label says so.
  c.year_basis = c.year ? words(c.year) : c.date ? `calendar year of ${words(c.date)}` : null;
  const taken = new Set(Object.values(c).filter((v) => typeof v === "string"));
  const observation = [];
  const byNorm = new Map(columns.map((col) => [norm(col), col]));
  for (const name of OBSERVATION) {
    const col = byNorm.get(name);
    if (col && !taken.has(col) && !observation.includes(col) && !lineage(col)) observation.push(col);
    if (observation.length === 4) break;
  }
  if (observation.length < 2) {
    for (const col of columns) {
      if (taken.has(col) || observation.includes(col) || NOISE.test(col) || lineage(col)) continue;
      observation.push(col);
      if (observation.length === 3) break;
    }
  }
  c.observation = observation;
  c.search = [...new Set([c.entity_name, ...observation].filter(Boolean))];
  // Collective scope and the link status, by their approved names only: the
  // population a record relates to is a different thing from the entity it
  // names (docs/COLLECTIVE_SCOPE_DECISION_2026-09-05.md), and no older
  // column is read as either.
  c.scopes = columns.includes("collective_scopes") ? "collective_scopes" : null;
  c.link_status = columns.includes("entity_link_status") ? "entity_link_status" : columns.includes("entity_link_statuses") ? "entity_link_statuses" : null;
  return c;
}


/** A verified producer spreadsheet keeps component identity and row grain. */
/**
 * The first view keeps the columns needed to interpret a reported observation.
 * Raw keys, record types and grains remain available in the record and show-all
 * views. Monetary qualifications and each union component's dates and sources
 * take precedence over another descriptive column.
 */
export function spreadsheetDefaultColumns(contract, columns) {
  const has = (column) => typeof column === "string" && columns.includes(column);
  const unique = (values) => [...new Set(values.filter(has))];
  const rowTypes = Object.values(contract.row_type_contracts ?? {});
  const identity = unique([contract.subject, contract.entity_name, contract.entity_role_column]);
  const kind = rowTypes.length > 1 ? unique(["record_type"]) : [];
  const money = contract.amount ? unique([
    contract.amount, contract.amount_basis,
    ...["measurement_status", "amount_sign_meaning"].filter(has),
    contract.currency, ...["currency", "currency_code", "amount_currency"].filter(has),
  ]) : [];
  const dateColumn = (type) => [type.date, type.year].find(has);
  const dates = unique(rowTypes.length
    ? rowTypes.map(dateColumn)
    : [dateColumn(contract)]);
  const sources = unique(rowTypes.length
    ? rowTypes.map((type) => type.source)
    : [contract.source]);
  const required = unique([...identity, ...kind, ...money, ...dates, ...sources]);
  if (required.length > 8) {
    throw new Error("Spreadsheet opening view needs a reviewed choice of at most eight semantic columns");
  }
  const structural = new Set(["record_type", "record_key", "record_grain"]);
  const observations = unique(contract.observation ?? [])
    .filter((column) => !structural.has(column) && !isInternalProvenanceColumn(column) && !required.includes(column))
    .slice(0, 8 - required.length);
  return unique([...identity, ...kind, ...money, ...dates, ...observations, ...sources]);
}

export function spreadsheetContract(columns, sampleRows = [], presentation = {}) {
  const mixed = mixedSpreadsheetContract(presentation.collection, columns, presentation.record_type_fields);
  if (mixed) return mixed;
  for (const required of ["record_type", "record_key", "record_grain"]) {
    if (!columns.includes(required)) throw new Error("producer spreadsheet lacks " + required);
  }
  const c = contractFor(columns, sampleRows);
  c.record_id = "record_key";
  c.record_type = "record_type";
  // Only the explicit central-entity block denotes a CE association. An
  // enterprise id/name, owner name, certifier or parent id cannot fill it.
  c.entity_uid = pick(columns, ["cedar_uid", "cedar_uids"]);
  c.entity_uid_list = c.entity_uid === "cedar_uids";
  c.entity_name = c.entity_uid ? pick(columns, c.entity_uid_list ? ["canonical_names"] : ["canonical_name"]) : null;
  c.entity_type = c.entity_uid ? pick(columns, c.entity_uid_list ? ["entity_classes"] : ["entity_class"]) : null;
  c.entity_role_column = c.entity_uid ? pick(columns, c.entity_uid_list ? ["entity_roles"] : ["cedar_entity_role"]) : null;
  c.entity_name_list = c.entity_uid_list && c.entity_name === "canonical_names";
  c.entity_type_list = c.entity_uid_list && c.entity_type === "entity_classes";
  c.entity_role_list = c.entity_uid_list && c.entity_role_column === "entity_roles";
  c.entity_role = null;
  c.entity_roles = [
    { column: "sub_cedar_uid", role: "subcontractor-side Native attribution" },
    { column: "prime_cedar_uid", role: "prime-contractor-side Native attribution" },
    { column: "affiliation_as_of_transaction_cedar_uid", role: "source-attributed affiliation as of the transaction" },
    { column: "beneficiary_entity_id", role: "beneficiary" },
  ].filter(role => columns.includes(role.column) && role.column !== c.entity_uid);
  c.subject = pick(columns, RULES.subject);
  if (c.subject === c.entity_name) c.subject = null;
  c.year = pick(columns, ["fiscal_year", "reporting_year", ...RULES.year]);
  c.date = pick(columns, [...RULES.date, "period_start"]);
  c.year_basis = c.year ? words(c.year) : c.date ? "calendar year of " + words(c.date) : null;
  // Resource observations describe a reporting period; an allocation need
  // not have a payment date. Keep payment_date available as its own field.
  if (["period_start", "period_end", "period_type", "measurement_status"].every(column => columns.includes(column))) {
    c.year = null;
    c.date = "period_start";
    c.year_basis = "calendar year in which the reported period starts";
  }
  c.subject = pick(columns, [...RULES.subject, "subcontractor_name", "organization_name", "business_name"]);
  if (c.subject === c.entity_name) c.subject = null;
  c.amount = pick(columns, ["obligations_usd", "reported_amount_usd", "subaward_amount_usd", "amount_usd", "announced_value_usd"]);
  c.amount_basis = c.amount ? pick(columns, ["amount_basis", "value_basis", "measurement_status", "amount_sign_meaning"]) : null;
  c.amount_label = c.amount ? words(c.amount) : null;
  c.observation = c.observation.filter(column => !["record_type", "record_key", "record_grain"].includes(column));
  if (["resource_type", "revenue_type", "commodity"].every(column => columns.includes(column))) {
    // A national revenue observation can intentionally name no recipient.
    // Describe the resource and revenue, without inventing a tribal payer/payee.
    c.observation = ["commodity", "resource_type", "revenue_type"];
  }
  c.default_columns = spreadsheetDefaultColumns(c, columns);
  const reviewedNeed = reviewedNeedColumns(columns);
  if (reviewedNeed) {
    c.observation = reviewedNeed.observation;
    c.default_columns = reviewedNeed.defaults;
  }
  // A union spreadsheet retains component-qualified columns when meanings
  // differ. Select them by record_type; an action date is not a notice date.
  if (columns.includes("consultation_participants__source_url") &&
      columns.includes("federal_actions__source_url")) {
    for (const name of ["record_type", "notice_date", "publication_date", "html_url"]) {
      if (!columns.includes(name)) throw new Error("Federal Register spreadsheet lacks " + name);
    }
    c.row_type_contracts = {
      consultation_participants: {
        label: "Consultation participant",
        source: "consultation_participants__source_url", source_fallback: null,
        date: "notice_date", year: null, year_basis: "calendar year of notice date",
      },
      federal_actions: {
        label: "Federal action",
        source: "federal_actions__source_url", source_fallback: "html_url",
        date: "publication_date", year: null, year_basis: "calendar year of publication date",
      },
    };
    c.source = null;
    c.date = null;
    c.year = null;
    c.year_basis = null;
    c.default_columns = spreadsheetDefaultColumns(c, columns);
  }
  c.mapping_kind = "producer_spreadsheet";
  c.reviewed = true;
  c.review_reason = "Presentation mapping of the verified producer spreadsheet: exact record key/grain, explicit CE block and source-declared roles. This is not a new identity or ownership determination.";
  return c;
}

/**
 * The record id of a customer table: the collection's own event or record
 * identifier, by name, and only when it is unique across the sample rows. A
 * repeated value would give two records one id (Codex, PR #63), so a table
 * whose identifier repeats falls back to the row's position, as before.
 */
const CUSTOMER_RECORD_ID = [
  "transaction_id", "deal_id", "document_number", "bill_id", "activity_id",
  "resource_revenue_event_id", "subaward_record_id", "disclosure_id", "plot_record_id",
  "business_uid", "business_source_id", "ein",
];

export function customerRecordId(columns, sampleRows = []) {
  for (const name of CUSTOMER_RECORD_ID) {
    if (!columns.includes(name)) continue;
    const values = sampleRows.map((row) => row[name] ?? "");
    if (values.every(Boolean) && new Set(values).size === values.length) return name;
  }
  return null;
}

/**
 * The contract for a collection's CUSTOMER TABLE: one flat table, one grain,
 * rendered by the vendored customer_sheet rules (owner ruling 2026-10-04,
 * scripts/render_sample_downloads.py). It carries no record_type, record_key
 * or record_grain -- those belonged to the raw multi-table producer preview,
 * which is no longer served -- so nothing here dispatches by record type.
 * The entity block is read by its approved names only, as for the producer
 * spreadsheet: an enterprise, owner or certifier name never fills it.
 */
// Collection rules that carry a reviewed reading of a column over from the
// producer-spreadsheet mapping (mixedSpreadsheet.js, readerPresentation.js)
// to the customer table's own column names. Each key is present in the
// customer table today; validateContract refuses the contract if one goes.
const CUSTOMER_PRESENTATION = Object.freeze({
  // NEED: the related entity and the relationship are the observation; the
  // enterprise is the subject (readerPresentation.reviewedNeedColumns).
  need: {
    subject: "enterprise_name",
    // The name the source used, for the enterprises no relationship names.
    observation: ["related_entity_name", "relationship_type", "ownership_extent", "source_reported_name"],
    default_columns: ["enterprise_name", "related_entity_name", "relationship_type", "ownership_extent", "uei", "cage_code"],
    // The owner's page for the ownership first, then the record's other citations.
    source: "native_owner_source", source_fallback: "source_urls",
  },
  // Federal Register: the customer table keeps the federal-action documents
  // only (customer_sheet.LAYOUTS), so it has no entity block; the document
  // number and type say which document a row is.
  "federal-register": {
    default_columns: ["document_number", "publication_date", "type", "title", "agency_names", "source_url"],
  },
  // Giving: announcement date and the source-reported year, the recipient as
  // reported when no name was resolved (mixedSpreadsheet.js GIVING_TYPES).
  "foundation-corporate-giving": {
    subject: "recipient_name",
    subject_candidates: ["recipient_name", "recipient_name_reported"],
    subject_entity_role: "recipient", entity_role: "recipient",
    date: "announcement_date", date_basis: "Announcement date",
    year: "report_year", year_basis: "Source-reported year",
    amount_label: "Reported nominal USD",
    amount_lower: "amount_lower_usd", amount_upper: "amount_upper_usd", amount_class: "amount_class",
    observation: ["funder_name", "financial_status", "record_kind"],
  },
  // PLOT: a source parcel observed on a date; nothing about ownership, title
  // or Native identity is inferred (mixedSpreadsheet.js PLOT_TYPES).
  plot: {
    subject: "source_parcel_id",
    subject_candidates: ["source_parcel_id", "plot_record_id"],
    // No date or year column is read: the customer table's dated columns
    // (ownership observation, source snapshot) are blank on every sample row,
    // and tax_year is a tax year, not when the land was observed. A year
    // filter over this table would filter on nothing.
    date: null, year: null, year_basis: null,
    source: "source_record_url", source_fallback: "source_url",
    observation: ["land_record_kind", "record_role", "estate_type", "trust_status"],
  },
});

export function customerTableContract(columns, sampleRows = [], collection = null) {
  const c = contractFor(columns, sampleRows);
  c.record_id = customerRecordId(columns, sampleRows);
  c.record_type = null;
  c.entity_uid = pick(columns, ["cedar_uid", "cedar_uids"]);
  c.entity_uid_list = c.entity_uid === "cedar_uids";
  c.entity_name = c.entity_uid ? pick(columns, c.entity_uid_list ? ["canonical_names"] : ["canonical_name"]) : null;
  c.entity_type = c.entity_uid ? pick(columns, c.entity_uid_list ? ["entity_classes"] : ["entity_class"]) : null;
  c.entity_role_column = c.entity_uid ? pick(columns, c.entity_uid_list ? ["entity_roles"] : ["cedar_entity_role"]) : null;
  c.entity_name_list = c.entity_uid_list && c.entity_name === "canonical_names";
  c.entity_type_list = c.entity_uid_list && c.entity_type === "entity_classes";
  c.entity_role_list = c.entity_uid_list && c.entity_role_column === "entity_roles";
  c.entity_role = null;
  c.entity_roles = [
    { column: "sub_cedar_uid", role: "subcontractor-side Native attribution" },
    { column: "prime_cedar_uid", role: "prime-contractor-side Native attribution" },
    { column: "affiliation_as_of_transaction_cedar_uid", role: "source-attributed affiliation as of the transaction" },
    { column: "beneficiary_entity_id", role: "beneficiary" },
  ].filter((role) => columns.includes(role.column) && role.column !== c.entity_uid);
  c.year = pick(columns, ["fiscal_year", "reporting_year", ...RULES.year]);
  c.date = pick(columns, [...RULES.date, "announcement_date", "period_start"]);
  if (["period_start", "period_end", "period_type", "measurement_status"].every((column) => columns.includes(column))) {
    c.year = null;
    c.date = "period_start";
  }
  c.year_basis = c.year ? words(c.year) : c.date ? `calendar year of ${words(c.date)}` : null;
  if (c.date === "period_start") c.year_basis = "calendar year in which the reported period starts";
  c.subject = pick(columns, [...RULES.subject, "subcontractor_name", "organization_name", "business_name", "recipient_name_reported"]);
  if (c.subject === c.entity_name) c.subject = null;
  c.amount = pick(columns, ["obligations_usd", "reported_amount_usd", "subaward_amount_usd", "amount_usd", "announced_value_usd", "amount_exact_usd"]);
  c.amount_basis = c.amount ? pick(columns, ["amount_basis", "value_basis", "measurement_status", "amount_sign_meaning"]) : null;
  c.amount_label = c.amount ? words(c.amount) : null;
  // The observation is what the record says, from the named list only: a
  // role, an identifier or the citation never pads it.
  const internal = internalValueColumns(sampleRows);
  const taken = new Set([c.entity_uid, c.entity_name, c.entity_type, c.entity_role_column, c.subject,
    c.year, c.date, c.amount, c.amount_basis, c.source, c.record_id].filter(Boolean));
  c.observation = OBSERVATION
    .map((name) => columns.find((column) => norm(column) === name))
    .filter((column) => column && !taken.has(column) && !internal.has(column) && !isInternalProvenanceColumn(column))
    .slice(0, 4);
  if (["resource_type", "revenue_type", "commodity"].every((column) => columns.includes(column))) {
    // A national revenue observation can intentionally name no recipient.
    c.observation = ["commodity", "resource_type", "revenue_type"];
  }
  const preset = CUSTOMER_PRESENTATION[collection] ?? {};
  Object.assign(c, preset);
  if (!("year_basis" in preset)) c.year_basis = c.year ? words(c.year) : c.date ? `calendar year of ${words(c.date)}` : null;
  c.search = [...new Set([c.entity_name, ...(c.subject_candidates ?? [c.subject]), ...c.observation].filter(Boolean))];
  if (!CUSTOMER_PRESENTATION[collection]?.default_columns) c.default_columns = spreadsheetDefaultColumns(c, columns);
  c.mapping_kind = "customer_table";
  c.reviewed = true;
  c.review_reason = "Presentation mapping of the collection's customer table (vendored customer_sheet rules, owner ruling 2026-10-04): its own record identifier, the explicit Cedar entity block and source-declared roles. This is not a new identity or ownership determination.";
  return c;
}

function rows(path) {
  const text = readFileSync(path, "utf8").replace(/^\uFEFF/, "");
  const out = [];
  let row = [];
  let cell = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') { cell += '"'; i += 1; }
      else if (ch === '"') quoted = false;
      else cell += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") { row.push(cell); cell = ""; }
    else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && text[i + 1] === "\n") i += 1;
      row.push(cell); out.push(row); row = []; cell = "";
    } else cell += ch;
  }
  if (cell.length || row.length) { row.push(cell); out.push(row); }
  const [head, ...body] = out;
  return body.filter((r) => r.length > 1).map((r) => Object.fromEntries(head.map((h, i) => [h, r[i] ?? ""])));
}

/**
 * The entity register the card's pickers read: every uid in the spine with
 * its name and class, and the eighteen classes with their labels. Served as
 * a static file (public/) rather than bundled: 1,916 names is a hundred
 * kilobytes a reader who never opens the card should not download.
 */
export function deriveRegister() {
  const classes = rows(TYPES).map((t) => ({ code: t.type_code, label: t.label }));
  // The register's own date: the latest mint date the identity register
  // records. The register can vouch for an entity's class on and after that
  // day and not before, which is what a scope's membership evaluation reads
  // (Codex, PR #69: a current class is not historical membership).
  const asOf = rows(IDENTITY).map((r) => r.minted).filter((d) => /^\d{4}-\d{2}-\d{2}$/.test(d)).sort().at(-1) ?? null;
  const index = new Map(classes.map((c, i) => [c.code, i]));
  const entities = [];
  let withheld = 0;
  for (const r of rows(NAMES)) {
    if (!index.has(r.entity_class)) throw new Error(`register: unknown class ${r.entity_class} on ${r.cedar_uid}`);
    const withhold = r.entity_class === WITHHELD_CLASS && !WITHHELD_FIELD_PUBLISHES;
    if (withhold) withheld += 1;
    entities.push([r.cedar_uid, withhold ? null : r.name, index.get(r.entity_class)]);
  }
  entities.sort((a, b) => (a[1] ?? "\uffff").localeCompare(b[1] ?? "\uffff") || a[0].localeCompare(b[0]));
  return {
    generated_by: "scripts/derive-explore.mjs",
    source: "data/spine/cedar_entity_names.csv, cedar_entity_types.csv, and cedar_identity_register.csv (as_of: its latest mint date)",
    note:
      "Each entity is [cedar_uid, name, class index into `classes`]. A null name is " +
      `one the publication rule withholds (code/cedar_domain.py may_publish_individual_native_field); ` +
      `since the owner ruling of 2026-10-02 every ${WITHHELD_CLASS} name publishes, so withheld_names is 0.`,
    withheld_names: withheld,
    as_of: asOf,
    classes,
    entities,
  };
}

/**
 * The invariants an override must satisfy against the sample it describes.
 * Exported so a test can inject each violation and watch it fire
 * (Codex, PR #66): a guard that has only ever seen valid input is a guard
 * nobody has proven.
 */
// The link builders the viewer knows (explore.js builtSource), each with the
// columns its pattern reads. A declaration naming another kind, or a column
// the sample does not carry, would build nothing and say nothing, so it is
// refused here instead.
export const SOURCE_BUILDERS = Object.freeze({
  usaspending_award: (b) => [b.column],
  congress_bill: () => ["congress", "bill_type", "number"],
  federal_register_document: (b) => [b.column],
  propublica_ein: (b) => [b.column],
});

export function validateContract(key, contract, columns) {
  for (const [kind, child] of Object.entries(contract.row_type_contracts ?? {})) {
    validateContract(key + ":" + kind, child, columns);
    for (const field of ["source_fallback", "date", "year", "subject", "entity_uid", "entity_name", "entity_type", "entity_role_column", "amount", "amount_basis", "amount_lower", "amount_upper", "amount_class"]) {
      if (child[field] && !columns.includes(child[field])) throw new Error(key + ": missing component " + field);
    }
  }
  for (const column of contract.default_columns ?? []) {
    if (!columns.includes(column) && !(contract.mapping_kind === "producer_spreadsheet" && Object.hasOwn(PRESENTATION_COLUMNS, column))) throw new Error(`${key}: default column ${column} is not in the sample`);
  }
  if (contract.source && !columns.includes(contract.source)) {
    throw new Error(`${key}: source column ${contract.source} is not in the sample`);
  }
  if (contract.source_builder) {
    const needs = SOURCE_BUILDERS[contract.source_builder.kind];
    if (!needs) throw new Error(`${key}: unknown source builder ${contract.source_builder.kind}`);
    for (const column of needs(contract.source_builder)) {
      if (!column || !columns.includes(column)) {
        throw new Error(`${key}: source builder ${contract.source_builder.kind} reads ${column ?? "no column"}, which is not in the sample`);
      }
    }
  }
  // Every declared role column exists, names a role, and is not the
  // entity column itself (which carries the table's own role).
  for (const role of contract.entity_roles ?? []) {
    if (!columns.includes(role.column)) throw new Error(`${key}: role column ${role.column} is not in the sample`);
    if (!role.role) throw new Error(`${key}: role column ${role.column} names no role`);
    if (role.column === contract.entity_uid) throw new Error(`${key}: ${role.column} is the entity column, not a further role`);
  }
}

/**
 * Override keys that name no table the manifest declares. An override is a
 * hand-written declaration that only takes effect when its key matches
 * `<collection>/<table stem>`; after the 2026-10-01 release renamed every
 * table to `<collection>.csv`, all 27 keys written against the 2026-09-02
 * tables matched nothing and their `reviewed`, `record_id` and
 * `default_columns` silently stopped applying (found 2026-10-02). Keys that
 * begin with `_` are prose or retired blocks and are never matched.
 */
export function unknownOverrideKeys(overrides, manifest) {
  const known = new Set();
  for (const collection of manifest.collections) {
    for (const table of collection.tables) known.add(`${collection.id}/${table.table.replace(/\.csv$/, "")}`);
  }
  return Object.keys(overrides).filter((key) => !key.startsWith("_") && !known.has(key)).sort();
}

export function derive() {
  const manifest = JSON.parse(readFileSync(MANIFEST, "utf8"));
  const overrides = existsSync(OVERRIDES) ? JSON.parse(readFileSync(OVERRIDES, "utf8")) : {};
  const unknown = unknownOverrideKeys(overrides, manifest);
  if (unknown.length) {
    throw new Error(
      `explore.overrides.json declares ${unknown.length} table(s) the manifest does not: ${unknown.join(", ")}. ` +
      "An override that matches no table applies to nothing; retire it under a `_` key or rename it.",
    );
  }
  const tables = {};
  const unpublished = [];
  // One table per collection: the customer table rendered from its flagship
  // (scripts/render_sample_downloads.py). The release's supporting tables
  // have no served sample since 2026-10-04, so each is listed as unpublished.
  for (const collection of manifest.collections) {
    const flagship = collection.sample?.path ? collection.sample.table : null;
    for (const table of collection.tables) {
      const key = `${collection.id}/${table.table.replace(/\.csv$/, "")}`;
      const path = table.table === flagship ? `${DOWNLOADS}/${collection.id}.csv` : null;
      if (!path || !existsSync(path)) {
        unpublished.push(key);
        continue;
      }
      const columns = header(path);
      const override = overrides[key] ?? {};
      const contract = { ...customerTableContract(columns, rows(path), collection.id), ...override };
      // The year's meaning follows the year and date the override settled on,
      // unless the override states it in its own words.
      if (!("year_basis" in override) && "year" in override) {
        contract.year_basis = contract.year ? words(contract.year) : contract.date ? `calendar year of ${words(contract.date)}` : null;
      }
      if (!("amount_basis" in override) && !contract.amount) contract.amount_basis = null;
      validateContract(key, contract, columns);
      contract.columns = columns.length;
      tables[key] = contract;
    }
  }
  const sorted = Object.fromEntries(Object.keys(tables).sort().map((k) => [k, tables[k]]));
  return {
    generated_by: "scripts/derive-explore.mjs",
    note:
      "Per table: which columns the Explore card reads as the record id, the entity, its type, " +
      "the record's own subject, the year (and what year means there), the date, the amount and " +
      "its basis, the source, supersession, and which columns make the one-line observation. " +
      "Derived by name from each collection's customer table (public/data/cedar/downloads/<id>.csv, " +
      "one flat table per collection, rendered by scripts/render_sample_downloads.py); " +
      "data/cedar/explore.overrides.json wins where it speaks, with its reason. " +
      "Re-run after re-rendering the customer tables.",
    unpublished,
    tables: sorted,
  };
}

function writeAtomically(path, value, pretty) {
  const tmp = `${path}.tmp`;
  writeFileSync(tmp, (pretty ? JSON.stringify(value, null, 2) : JSON.stringify(value)) + "\n");
  renameSync(tmp, path);
}

function current(path, value) {
  return existsSync(path) && JSON.stringify(JSON.parse(readFileSync(path, "utf8"))) === JSON.stringify(value);
}

function main(argv) {
  const derived = derive();
  const register = deriveRegister();
  if (argv.includes("--check")) {
    const stale = [
      [OUT, derived, "data/cedar/explore.json"],
      [REGISTER, register, "public/data/cedar/register.json"],
    ].filter(([path, value]) => !current(path, value)).map(([, , name]) => name);
    if (!stale.length) {
      process.stdout.write(
        `  explore   ${Object.keys(derived.tables).length} table contract(s), ` +
        `${register.entities.length} register entries; files current\n`,
      );
      return 0;
    }
    process.stderr.write(
      `${stale.join(" and ")} ${stale.length > 1 ? "are" : "is"} stale or missing. ` +
      "Run `node scripts/derive-explore.mjs` and commit the result.\n",
    );
    return 1;
  }
  writeAtomically(OUT, derived, true);
  // Compact: one line an entity, so the file the browser fetches is the size
  // of its contents and not of its indentation.
  writeAtomically(REGISTER, register, false);
  process.stdout.write(
    `  wrote public/data/cedar/register.json: ${register.entities.length} entities, ` +
    `${register.classes.length} classes, ${register.withheld_names} names withheld\n`,
  );
  const gaps = Object.entries(derived.tables).filter(([, c]) => !c.entity_uid || !(c.year || c.date));
  process.stdout.write(
    `  wrote data/cedar/explore.json: ${Object.keys(derived.tables).length} tables, ` +
    `${derived.unpublished.length} without a published sample, ` +
    `${gaps.length} without an entity or a year\n`,
  );
  for (const [key, c] of gaps) {
    process.stdout.write(`    ${key}: entity=${c.entity_uid ?? "-"} year=${c.year ?? "-"} date=${c.date ?? "-"}\n`);
  }
  return 0;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  process.exit(main(process.argv.slice(2)));
}
