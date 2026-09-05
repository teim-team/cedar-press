// Derive each table's EXPLORE CONTRACT from its published sample, and record
// it in data/cedar/explore.json.
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

const REPO = fileURLToPath(new URL("..", import.meta.url));
const MANIFEST = `${REPO}data/cedar/collections.manifest.json`;
const OVERRIDES = `${REPO}data/cedar/explore.overrides.json`;
const OUT = `${REPO}data/cedar/explore.json`;
const PUBLIC = `${REPO}public`;
const NAMES = `${REPO}data/spine/cedar_entity_names.csv`;
const TYPES = `${REPO}data/spine/cedar_entity_types.csv`;
const REGISTER = `${PUBLIC}/data/cedar/register.json`;

// The one class whose names the publication rule withholds unless the owner
// opted in (code/cedar_domain.py may_publish_individual_native_field: a
// firm's website is evidence, never permission). The register carries the
// uid and the class so a row keyed to one still filters by type; the name
// is null and the picker says so.
const WITHHELD_CLASS = "Individually Native-owned business";

// Column names are matched lowercased, in this order; the first present wins.
const RULES = {
  entity_uid: [
    "cedar_uid", "entity_cedar_uid", "owner_hub_cedar_uid", "resolved_native_entity_id",
    "sub_cedar_uid", "prime_cedar_uid", "cedar_entity_id", "entity_id", "entity_cedar_uids",
  ],
  entity_name: [
    "canonical_name", "cedar_spine_canonical_name", "native_party_canonical_name",
    "tribe_canonical_name", "owner_hub_name", "cedar_entity_name", "tribe_name", "entity_name",
    "native_party", "client_name", "participant_name_as_published", "witness_organization",
    "recipient_name", "awardee_name", "sub_awardee_name", "enterprise_name", "name",
  ],
  entity_type: [
    "entity_type", "entity_class", "cedar_native_entity_class", "cedar_spine_entity_class",
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
  superseded_by: ["superseded_by_filing_uuid"],
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

export function contractFor(columns) {
  const c = {};
  c.entity_uid = pick(columns, RULES.entity_uid) ?? pickShape(columns, /cedar_uid$/, /candidate/);
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
    if (col && !taken.has(col) && !observation.includes(col)) observation.push(col);
    if (observation.length === 4) break;
  }
  if (observation.length < 2) {
    for (const col of columns) {
      if (taken.has(col) || observation.includes(col) || NOISE.test(col)) continue;
      observation.push(col);
      if (observation.length === 3) break;
    }
  }
  c.observation = observation;
  c.search = [...new Set([c.entity_name, ...observation].filter(Boolean))];
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
  const index = new Map(classes.map((c, i) => [c.code, i]));
  const entities = [];
  let withheld = 0;
  for (const r of rows(NAMES)) {
    if (!index.has(r.entity_class)) throw new Error(`register: unknown class ${r.entity_class} on ${r.cedar_uid}`);
    const withhold = r.entity_class === WITHHELD_CLASS;
    if (withhold) withheld += 1;
    entities.push([r.cedar_uid, withhold ? null : r.name, index.get(r.entity_class)]);
  }
  entities.sort((a, b) => (a[1] ?? "\uffff").localeCompare(b[1] ?? "\uffff") || a[0].localeCompare(b[0]));
  return {
    generated_by: "scripts/derive-explore.mjs",
    source: "data/spine/cedar_entity_names.csv and cedar_entity_types.csv",
    note:
      "Each entity is [cedar_uid, name, class index into `classes`]. A null name is " +
      `withheld by the publication rule for ${WITHHELD_CLASS} (code/cedar_domain.py).`,
    withheld_names: withheld,
    classes,
    entities,
  };
}

export function derive() {
  const manifest = JSON.parse(readFileSync(MANIFEST, "utf8"));
  const overrides = existsSync(OVERRIDES) ? JSON.parse(readFileSync(OVERRIDES, "utf8")) : {};
  const tables = {};
  const unpublished = [];
  for (const collection of manifest.collections) {
    for (const table of collection.tables) {
      const key = `${collection.id}/${table.table.replace(/\.csv$/, "")}`;
      const path = table.sample_path ? `${PUBLIC}${table.sample_path}` : null;
      if (!path || !existsSync(path)) {
        unpublished.push(key);
        continue;
      }
      const columns = header(path);
      const override = overrides[key] ?? {};
      const contract = { ...contractFor(columns), ...override };
      // The year's meaning follows the year and date the override settled on,
      // unless the override states it in its own words.
      if (!("year_basis" in override)) {
        contract.year_basis = contract.year ? words(contract.year) : contract.date ? `calendar year of ${words(contract.date)}` : null;
      }
      if (!("amount_basis" in override) && !contract.amount) contract.amount_basis = null;
      // Derived by name, so PROPOSED, not certified: only a declaration in the
      // overrides file, with its reason, marks a table's mapping reviewed.
      contract.reviewed = override.reviewed === true;
      for (const column of contract.default_columns ?? []) {
        if (!columns.includes(column)) throw new Error(`${key}: default column ${column} is not in the sample`);
      }
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
      "Derived from the published sample's header by name, so PROPOSED; a table is `reviewed` " +
      "only where data/cedar/explore.overrides.json declares it so, with its reason. " +
      "Re-run after the importer copies samples.",
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
