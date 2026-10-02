// Maintained researcher documentation, with shared parsing, formatting and freshness gates.
//   node scripts/docs-markdown.mjs --kind codebook|field-map|guides|all [--check]
// Field-map reports retain historical raw fixtures; current guides use the installed release dictionary.
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { assertReleasedDictionary, releasedBook } from "./release-docs.mjs";
const REPO = fileURLToPath(new URL("..", import.meta.url));
const SAMPLES = REPO + "server/tests/fixtures/legacy-preview/samples/";
const OUT_DIR = REPO + "docs/guides/";
const readData = (name) => JSON.parse(readFileSync(REPO + "data/cedar/" + name, "utf8"));
const esc = (s) => String(s ?? "").replace(/\|/g, "\\|").replace(/\r?\n/g, " ");
let guideInputs;
function guideData() {
  return guideInputs ??= {
    GUIDES: readData("guides.json"), MAP: readData("field_map.json"),
    CODEBOOK: readData("codebook.json"), MANIFEST: readData("collections.manifest.json"),
    DESCRIPTORS: readData("collection_descriptors.json"),
  };
}

export function render() {
  const codebook = readData("codebook.json");
  const manifest = readData("collections.manifest.json");
  const byId = Object.fromEntries(manifest.collections.map((entry) => [entry.id, entry]));
  const current = new Map();
  for (const entry of manifest.collections) {
    const selected = releasedBook(entry, codebook);
    if (selected) current.set(selected.key, selected.book);
  }
  const lines = [];
  const p = (text = "") => lines.push(text);
  p("# Cedar Press dataset dictionaries");
  p();
  p("Generated from `data/cedar/codebook.json` and `data/cedar/collections.manifest.json` by `scripts/docs-markdown.mjs --kind codebook`. Edit the source dictionaries and regenerate this document.");
  p();
  p("## Scope");
  p();
  p(`This document contains ${Object.keys(codebook.tables).length} dictionary entries. ${current.size} entries describe the installed producer spreadsheets selected by the manifest. Any other entry is labelled as a compatibility reference and does not describe a currently served spreadsheet.`);
  p();
  p("Each exported field keeps its own meaning, source role and publication qualification. A business identifier, an owner link, a certifying-authority link and a source-record key identify different objects or relationships. A missing identity is not filled by a shared name.");
  p();
  p("Read `record_type`, `record_key` and `record_grain` together. A researcher spreadsheet can contain several logical record types whose grains overlap. Amounts retain their stated basis; obligations, allocations, payments, ceilings and reported spending are not interchangeable.");
  p();
  p("The served previews are short excerpts. Matching a dictionary to a preview verifies the displayed schema, not every underlying fact or the entire population. Publication and field restrictions remain governed by the release.");
  p();
  p("## The dictionaries");
  p();
  for (const [key, table] of Object.entries(codebook.tables)) {
    const collection = byId[table.collection];
    const installed = current.has(key);
    p(`### ${table.dataset || table.collection}`);
    p();
    p(`Collection \`${table.collection}\` · table \`${key.split("/").slice(1).join("/")}\` · ${installed ? "installed producer spreadsheet" : "compatibility reference; not the manifest's installed spreadsheet"}`);
    p();
    if (installed && Number.isSafeInteger(collection?.sample?.of)) {
      p(`**Rows in this installed spreadsheet:** ${collection.sample.of.toLocaleString("en-US")}. This is an observation count at the declared record types and grains.`);
      p();
    }
    p(`**One row is:** ${table.row}`);
    p();
    p(`**Release or source location:** ${table.where}`);
    p();
    if (installed) {
      p("The columns below describe the exported names directly. No legacy rename, combine or promised identity block is applied to this spreadsheet.");
      p();
    }
    p(`**Fields (${table.fields.length}):**`);
    p();
    p("| # | Column | Label | Meaning |");
    p("|---|---|---|---|");
    table.fields.forEach((field, index) => {
      const flags = installed ? "" : [
        field.add ? "to add in the compatibility transform" : "",
        field.rename_to ? `rename to \`${field.rename_to}\`` : "",
        field.combine_into ? `combines into \`${field.combine_into}\`` : "",
      ].filter(Boolean).join("; ");
      p(`| ${index + 1} | \`${field.column}\`${flags ? ` (${flags})` : ""} | ${esc(field.label)} | ${esc(field.meaning)} |`);
    });
    p();
  }
  p("## Review questions");
  p();
  p("- Does each definition preserve the source's subject, relationship, date and amount basis?");
  p("- Are record type, grain and version restrictions sufficient for the proposed analysis?");
  p("- Which identity or source conflicts still need adjudication, and what evidence would resolve them?");
  p();
  return lines.join("\n") + "\n";
}


/** Column names that name a competing entity identifier, in any table. */
export const COMPETING_ID = /duns|neid|cicd|casino[ _-]?city|tribe_id|_candidate|proposed|resolver|(^|_)(native_)?entity_id$|resolved_(native_)?entity_id|existing_cedar_uid|_uid_candidate/i;
/** A retired scheme's name inside a value; `_` and a word boundary both separate. */
export const RETIRED_TOKEN = /(?<![a-z])(neid|cicd|casino[ _-]?city)(?![a-z])/i;

function header(path) { return parseCsv(readFileSync(path, "utf8")).columns ?? []; }
function sampleRows(collection, table) {
  const path = SAMPLES + collection + "/" + table + "__10.csv";
  return existsSync(path) ? parseCsv(readFileSync(path, "utf8")).rows : null;
}

/** Every supporting-table sample column that names a competing identifier. */
export function scanSupportingTables(map) {
  const flagships = new Set(Object.keys(map.tables).map((k) => `${k}__10.csv`));
  const hits = [];
  for (const collection of readdirSync(SAMPLES).sort()) {
    const dir = `${SAMPLES}${collection}`;
    let files;
    try { files = readdirSync(dir).filter((f) => f.endsWith(".csv")).sort(); } catch { continue; }
    for (const file of files) {
      const key = `${collection}/${file}`;
      if (flagships.has(key)) continue;
      const cols = header(`${dir}/${file}`).filter((c) => COMPETING_ID.test(c));
      if (cols.length) hits.push({ table: key.replace(/__10\.csv$/, ""), columns: cols });
    }
  }
  return hits;
}

export function renderMap() {
  const map = readData("field_map.json");
  const manifest = readData("collections.manifest.json");
  const byId = Object.fromEntries(manifest.collections.map((c) => [c.id, c]));
  const lines = [];
  const p = (s = "") => lines.push(s);
  p("# Cedar Press datasets: historical field-by-field transform map");
  p();
  p("Generated from `data/cedar/field_map.json` by `scripts/docs-markdown.mjs --kind field-map`; edit the JSON, not this file. Written 2026-09-05.");
  p();
  p("## What this is");
  p();
  p("The companion to the owner's exact public column specification (`docs/PUBLIC_DATASET_SPEC_2026-09-05.md`, addendum): for each flagship, every column its current sample header carries with one decision, the approved public header in the owner's exact order, the owner's default viewer selection, and a retirement entry for every competing entity identifier. The customer-file writer generates the export from this list (`code/1137_customer_dataset_combine.py` through `cedar_publication.apply_field_map`): it renames, drops what is internal or documented, fills the opening block from the register, builds the plural aligned arrays and the named rules, verifies every alias, orders the header exactly, and refuses a dataset that carries a column with no decision, an identifier awaiting adjudication, or a retired scheme's name in a shipped column or value. This pass changes columns, never rows, identities or publication eligibility.");
  p();
  p("This dated map describes historical raw inputs, retained as private regression fixtures in `server/tests/fixtures/legacy-preview/`. Current public previews are already-projected, verified producer spreadsheets; this map is not reapplied to them. Their field definitions, record types, grains and pinned releases are in `docs/DATASET_CODEBOOK.md` and the collection guides.");
  p();
  p("## Current public spreadsheet previews");
  p();
  p("| Collection | Public file | Permitted observations | Record types |");
  p("|---|---|---:|---|");
  for (const collection of manifest.collections) {
    for (const table of collection.tables ?? []) {
      if (!table.sample_path || !table.record_types) continue;
      p(`| ${esc(collection.name ?? collection.id)} | \`${esc(table.table)}\` | ${table.rows_published ?? table.rows_in ?? "—"} | ${Object.entries(table.record_types).map(([kind, count]) => `${esc(kind)}: ${count}`).join("; ")} |`);
    }
  }
  p();
  p("Counts are permitted source observations, not unique Native entities or businesses. A CE association identifies the role stated on its row; owner, certifier and business are not interchangeable. NEED exposes only its evidence-pinned reviewed base; other NEED components retain their publication holds.");
  p();
  p("**Decisions:**");
  p();
  for (const [name, meaning] of Object.entries(map.decisions)) p(`- \`${name}\`: ${meaning}`);
  p();
  p("**Retirement dispositions:**");
  p();
  for (const [name, meaning] of Object.entries(map.dispositions)) p(`- \`${name}\`: ${meaning}`);
  p();
  p("**The opening block:**");
  p();
  p(`Singular, for a record with one canonical Native entity association: ${map.opening.singular.map((c) => `\`${c}\``).join(", ")}. Plural, for Legislation and NAGPRA: ${map.opening.plural.map((c) => `\`${c}\``).join(", ")}, aligned JSON arrays.`);
  p();
  for (const name of [...map.opening.singular, ...map.opening.plural]) p(`- \`${name}\`: ${map.opening[name]}`);
  p();
  p(`**\`research_note\`:** ${map.research_note}`);
  p();
  p("## Column counts");
  p();
  p("| Dataset | Inspected columns | Public columns | Keep | Rename | Withhold | Combine | Derive | Document | Internal | Owed | Retirement entries |");
  p("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|");
  for (const [key, t] of Object.entries(map.tables)) {
    const count = (d) => t.fields.filter((f) => f.decision === d).length;
    const owed = t.new.filter((n) => n.status === "pending").length;
    p(`| \`${key}\` | ${t.columns_today ?? "no sample"} | ${t.columns_target} | ${count("keep")} | ${count("rename")} | ${count("withhold")} | ${count("combine")} | ${count("derive")} | ${count("document")} | ${count("internal")} | ${owed} | ${t.retire.length} |`);
  }
  p();
  p("\"Public columns\" is the approved header including columns still owed; \"Owed\" counts the target columns the terminal builds from the full table (a combine crosswalk, an editorial note) and which are absent, never blank, until they exist. Funding ships 39 where the owner's list says 40: `recipient_duns` is retired under the rule in the same addendum.");
  p();
  p("## The datasets");
  p();
  for (const [key, t] of Object.entries(map.tables)) {
    const collection = byId[t.collection];
    p(`### ${collection?.name ?? t.collection} (\`${key}\`)`);
    p();
    p(`**Public file:** \`${t.public_file}\` · **One row is:** ${t.row}`);
    p();
    if (t.note) { p(`**Note:** ${t.note}`); p(); }
    p(`**Entity role (\`cedar_entity_role\` / \`entity_roles\`):** ${t.entity_role}${t.primary_role ? ` · the primary list's role is *${t.primary_role}*` : ""}`);
    if (t.entity_roles?.length) {
      p();
      p("Role-specific links on the row, each an entity of the record the viewer finds it by:");
      p();
      for (const r of t.entity_roles) p(`- \`${r.column}\`: ${r.role}${r.list ? " (several)" : ""}`);
    }
    p();
    p(`**Approved header, exact order (${t.order.length}):** ${t.order.map((c) => `\`${c}\``).join(", ")}`);
    p();
    p(`**Default viewer:** ${t.default_viewer.map((c) => `\`${c}\``).join(", ")}`);
    p();
    if (t.fields.length) {
      p(`**Every current column and its decision (${t.fields.length}):**`);
      p();
      p("| # | Column today | Decision | Ships as | Why | Spec |");
      p("|---|---|---|---|---|---|");
      t.fields.forEach((f, i) => {
        const to = f.decision === "keep" || f.decision === "withhold" ? f.column : f.to ?? "";
        const why = f.retire ? `${f.why} *Retirement: ${f.retire.disposition}.*` : f.why;
        p(`| ${i + 1} | \`${f.column}\` | ${f.decision} | ${to ? `\`${to}\`` : "—"} | ${esc(why)} | ${f.spec ?? ""} |`);
      });
      p();
    }
    if (t.new.length) {
      p(`**Target columns built at write time or owed (${t.new.length}):**`);
      p();
      p("| Column | From | Why | Status |");
      p("|---|---|---|---|");
      for (const n of t.new) p(`| \`${n.column}\` | ${esc(n.from)} | ${esc(n.why)} | ${n.status ?? "built at write time"} |`);
      p();
    }
  }
  p("## What is not decided here");
  p();
  p("- Every `combine`: the sources are tested for agreement across the full table before one column replaces them; until then the sources stay in the workspace and the target is absent.");
  p("- Every `derive` marked owed: the editorial `research_note` for Deals, the date precision for the Federal Register, the names as published for Legislation and NAGPRA from the bridge.");
  p("- This historical Native-owned businesses map predates the current producer spreadsheet. The current row grain is a source certification or directory listing, not necessarily one unique business.");
  p("- Historical NEED, Nonprofits and Funding transformation holds remain regression controls for those raw inputs. They do not describe the eligibility of a new producer release. NEED’s current exception is limited to the separately verified reviewed base and does not authorize the original held components.");
  p();
  return lines.join("\n") + "\n";
}

export function renderRetirement() {
  const map = readData("field_map.json");
  const lines = [];
  const p = (s = "") => lines.push(s);
  p("# Historical identifier retirement report");
  p();
  p("Generated from `data/cedar/field_map.json` and the sample headers by `scripts/docs-markdown.mjs --kind field-map`; edit the map, not this file. Written 2026-09-05 under the retirement rule in `docs/PUBLIC_DATASET_SPEC_2026-09-05.md` (addendum): migrate, reconcile, verify, retire, regression-test.");
  p();
  p("## The rule, as enforced");
  p();
  p("`cedar_uid` is Cedar's one cross-dataset identity. Every competing entity identifier in a flagship's header has a retirement entry in the map with what it identifies and its disposition. The writer (`cedar_publication.apply_field_map`) enforces the dispositions on every build: an `alias_verified` column is compared to `cedar_uid` on every row and the dataset is refused where they differ; an `adjudicate` column stops the dataset wherever it is populated, and is neither retained nor deleted; a `retired_scheme` name in any shipped value, or a prohibited name in the header, stops the dataset. The regression tests (`server/tests/test_field_map.py` and the site's explore test suite) fail if a prohibited identifier returns to any approved header, and the writer fails at build if one returns to a value.");
  p();
  p("`rows_affected` below is the count in the historical raw test fixture, not the current public preview or the current release. The historical writer prints its full-table disposition count on its own build. Current release field and identity contracts are documented in `docs/DATASET_CODEBOOK.md`.");
  p();
  p("## Flagship identifiers");
  p();
  p("| dataset | old_identifier | what_it_identified | cedar_uid_or_replacement | disposition | rows_affected (sample) | unresolved_count (sample) |");
  p("|---|---|---|---|---|---:|---:|");
  for (const [key, t] of Object.entries(map.tables)) {
    const rows = t.fields.length ? sampleRows(t.collection, key.split("/")[1]) : null;
    for (const r of t.retire) {
      const affected = rows ? rows.filter((row) => (row[r.column] ?? "").trim()).length : "—";
      let unresolved = 0;
      if (rows && r.disposition === "adjudicate") unresolved = affected;
      if (rows && r.disposition === "alias_verified") {
        unresolved = rows.filter((row) => (row[r.column] ?? "").trim() && (row[t.entity_uid] ?? "").trim() && row[r.column].trim() !== row[t.entity_uid].trim()).length;
      }
      if (rows && r.value_level) unresolved = rows.filter((row) => RETIRED_TOKEN.test(row[r.column] ?? "")).length;
      p(`| \`${t.collection}\` | \`${r.column}\` | ${esc(r.identifies)} | ${esc(r.replacement)} | ${r.disposition} | ${affected} | ${unresolved} |`);
    }
  }
  p();
  p("The entries above describe historical raw transform inputs and their unresolved dispositions, not current producer release eligibility. Current NEED publication is restricted to its separately evidence-pinned reviewed base; the original held components are not admitted. Preserve evidence and issued IDs, and distinguish CE associations, business identities and source record keys.");
  p();
  p("## Supporting tables");
  p();
  p("Supporting tables are not customer downloads, but the rule reaches the whole pipeline: every supporting-table sample column that names a competing identifier, for the terminal to migrate to `cedar_uid` or an object identifier, move to the identity layer, or adjudicate. The pattern is the same one the regression test applies to public headers.");
  p();
  const hits = scanSupportingTables(map);
  p("| table | columns |");
  p("|---|---|");
  for (const h of hits) p(`| \`${h.table}\` | ${h.columns.map((c) => `\`${c}\``).join(", ")} |`);
  p();
  p(`${hits.length} supporting tables carry such a column in their samples. Columns whose name ends in \`_entity_id\` are listed because they may hold a Cedar uid under another name (an alias to verify) or a non-Cedar namespace (an object id to keep, as Natural Resources' payer and operator ids are); each needs the same determination the flagship columns received.`);
  p();
  p("## The rest of the pipeline");
  p();
  p("Measured with `git grep -il` on 2026-09-05, as the inventory of remaining dependencies, not as a claim they are all customer-facing: 84 files under `code/` mention DUNS, 43 mention the NEID scheme by name, 53 mention CICD, and 67 files across the repository mention Casino City. `code/843_retire_cicd_scheme.py` and `code/844_nuke_cicd.py` did the first retirement; `cedar_publication.translate_neid_values` still translates NEID tokens inside strings at load, which is the migration half of the rule and stays. Two sample files carry a retired scheme's name in a value: `funding/federal_funding_transactions` (`attribution_status`, above) and `deals/ownership_events` (`neid_join_status`, a supporting table).");
  p();
  return lines.join("\n") + "\n";
}


export const SECTIONS = [
  "Purpose", "Population", "One row is", "Key identifiers", "Sources and coverage",
  "Time and geography", "Entity relationships", "Revisions", "Field dictionary",
  "Missing values", "Limitations", "Suitable analyses", "Unsafe aggregations",
  "What is still owed", "Release, citation and method",
];


// ── The sample, for data types ─────────────────────────────────────────────

function parseCsv(text) {
  const out = [];
  let row = [];
  let cell = "";
  let quoted = false;
  const src = text.replace(/^﻿/, "");
  for (let i = 0; i < src.length; i += 1) {
    const ch = src[i];
    if (quoted) {
      if (ch === '"' && src[i + 1] === '"') { cell += '"'; i += 1; }
      else if (ch === '"') quoted = false;
      else cell += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") { row.push(cell); cell = ""; }
    else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && src[i + 1] === "\n") i += 1;
      row.push(cell); out.push(row); row = []; cell = "";
    } else cell += ch;
  }
  if (cell.length || row.length) { row.push(cell); out.push(row); }
  const [head, ...body] = out;
  return { columns: head, rows: body.filter((r) => r.length > 1).map((r) => Object.fromEntries(head.map((h, j) => [h, r[j] ?? ""]))) };
}

function sampleFor(collection) {
  const { MANIFEST } = guideData();
  const entry = MANIFEST.collections.find((c) => c.id === collection);
  const path = entry?.sample?.path ? `${REPO}public${entry.sample.path}` : null;
  if (!path || !existsSync(path)) return null;
  return parseCsv(readFileSync(path, "utf8"));
}

function typeOf(column, values) {
  const { GUIDES } = guideData();
  const T = GUIDES.types;
  const name = column.toLowerCase();
  const filled = values.map((v) => String(v ?? "").trim()).filter(Boolean);
  if (/^(cedar_uid|.*_cedar_uid|.*_uid|.*_id|.*_ids|.*_key|.*_uuid|ein|.*_number|.*_cage|cage_code|.*uei|document_number)$/.test(name) && !/^n_/.test(name)) {
    return filled.some((v) => v.includes("|")) || /_ids$/.test(name) ? T.list : T.id;
  }
  if (/_names$|_tiers$|_classes$|_uids$/.test(name)) return T.list;
  if (/(_usd|_amt|obligations|_amount|_value_usd|_cost|face_value_of_loan)$/.test(name) || /^(income|expenses|amount)_/.test(name)) return T.money;
  if (/(^|_)url(_\d)?$/.test(name)) return T.url;
  if (/^(is_|has_|self_|reported_|credit_instrument)|_flag$|^attributed_flag$|^attribution_withdrawn$|^is_correction$|^in_federal_contracting$|^parent_is_hub$|^evidence_human_reviewed$|^culturally_unidentifiable$|^lineal_descendant_determination$/.test(name)) return T.yesno;
  if (/_year$|^year$|^congress$/.test(name)) return T.year;
  if (!filled.length) return T.text;
  if (filled.every((v) => /^\d{4}-\d{2}-\d{2}T/.test(v))) return T.datetime;
  if (filled.every((v) => /^\d{4}-\d{2}-\d{2}$/.test(v))) return T.date;
  // A date column whose rows stop at the month or the year where the source
  // does (deals: "2014-05" beside event_date_precision "month").
  if (filled.every((v) => /^\d{4}(-\d{2}){0,2}$/.test(v)) && filled.some((v) => v.includes("-")) && /date|_on$/.test(name)) return T.date_precision ?? T.date;
  if (filled.every((v) => /^-?\d+(\.\d+)?$/.test(v)) && !/code|period|month|fips|zip/.test(name)) return T.number;
  if (filled.some((v) => v.includes("|")) && filled.every((v) => !/^https?:/.test(v)) && /entities|counties|states|codes|organizations|variants/.test(name)) return T.list;
  return T.text;
}

function blankMeans(column, decision, type) {
  const { GUIDES } = guideData();
  const T = GUIDES.types;
  if (decision === "withhold") return "masked where the publication policy withholds it; otherwise the source reports none";
  if (/^(record_type|record_key|record_grain)$/.test(column)) return "never blank; the producer sets it on every row";
  if (/^n_/.test(column)) return "not stated by the source; 0 means the source states none";
  if (type === T.yesno) return "not stated; 0 is no";
  if (type === T.money) return "the source reports no amount; never zero";
  if (type === T.date || type === T.date_precision || type === T.datetime || type === T.year) return "the source states no date";
  if (/_precision$/.test(column)) return "no date is stated on this row, so no precision applies";
  if (/cedar_uid|cedar_entity|canonical_name|entity_class/.test(column)) return "no registered Cedar entity is linked; read the link or attribution status column where the table carries one; never a finding that no Native entity is involved";
  return "the source states none, or not applicable to this row";
}

// Tokens that read as a value and are sometimes a stand-in for one. Each
// occurrence in a preview is reported by column, so a reader can check the
// dictionary's definition before treating it as data; the generator never
// recodes it.
const TOKENS = /^(null|none|unknown|nan|n\/a|na|tbd|undisclosed)$/i;

/**
 * What the preview itself shows, measured from its rows rather than typed:
 * record types and their counts, the columns blank on every row, the literal
 * tokens present, and the money, date and date-time columns the unit and
 * format statements apply to. Re-measured on every render, so the guide
 * cannot describe a sample it no longer ships.
 */
export function previewFacts(book, sample) {
  const { GUIDES } = guideData();
  const T = GUIDES.types;
  const rows = sample.rows;
  const cell = (row, column) => String(row[column] ?? "").trim();
  const recordTypes = new Map();
  for (const row of rows) {
    const kind = cell(row, "record_type") || "(blank)";
    recordTypes.set(kind, (recordTypes.get(kind) ?? 0) + 1);
  }
  const allBlank = [];
  const tokens = [];
  const typed = new Map();
  for (const field of book.fields) {
    const values = rows.map((row) => cell(row, field.column));
    const type = field.column === "record_key" ? "JSON source key" : typeOf(field.column, values);
    typed.set(field.column, type);
    if (rows.length && values.every((v) => !v)) allBlank.push(field.column);
    const found = new Map();
    for (const v of values) if (TOKENS.test(v)) found.set(v, (found.get(v) ?? 0) + 1);
    for (const [token, count] of found) tokens.push({ column: field.column, token, count });
  }
  const columnsOf = (type) => [...typed].filter(([, t]) => t === type).map(([c]) => c);
  const money = columnsOf(T.money);
  const dateColumns = [...columnsOf(T.date), ...columnsOf(T.date_precision)];
  const datetimeColumns = columnsOf(T.datetime);
  const monthPrecision = book.fields
    .map((field) => field.column)
    .filter((column) => rows.some((row) => /^\d{4}-\d{2}$/.test(cell(row, column))));
  return {
    rowCount: rows.length,
    recordTypes: [...recordTypes],
    allBlank,
    tokens,
    typed,
    money,
    real2025: money.filter((c) => /_real2025$/.test(c)),
    currencyColumn: typed.has("currency"),
    dateColumns,
    datetimeColumns,
    precisionColumns: book.fields.map((f) => f.column).filter((c) => /_precision$/.test(c)),
    monthPrecision,
  };
}

export function renderReleasedGuide(collection, book, entry, descriptor, sample) {
  assertReleasedDictionary(book, sample);
  const lines = [];
  const p = (text = "") => lines.push(text);
  const name = book.dataset || descriptor.name || collection;
  const updated = descriptor?.updated ?? entry?.descriptor?.updated ?? null;
  const facts = previewFacts(book, sample);
  const columns = new Set(book.fields.map((field) => field.column));
  const names = (pattern) => book.fields.filter((field) => pattern.test(field.column)).map((field) => `\`${field.column}\``).join(", ");
  p(`# ${name}: a researcher's guide`);
  p();
  p(`Collection \`${collection}\` · producer spreadsheet \`${entry.sample.table}\`${updated ? ` · Updated ${updated}` : ""}. Generated by \`scripts/docs-markdown.mjs --kind guides\` from the installed release manifest, its field dictionary and the served preview. The statements below describe that release.`);
  p();
  p("## Purpose"); p();
  p(`Use the ${name} spreadsheet to inspect source observations at their declared record type and grain, with the identifiers, sources and qualifications retained on each row.`);
  p();
  p("## Population"); p();
  p(book.row);
  if (collection === "need") {
    p();
    p("This preview covers only the reviewed public base identified by the installed release. It does not expose the held enterprise graph or establish ownership for the rest of NEED. A decision about one enterprise does not promote other enterprises or relationships.");
  }
  if (collection === "owned") {
    p();
    p("The observation is a business-directory or certification listing. Several listings may refer to one business; counting listings does not count unique businesses.");
  }
  p();
  p("## One row is"); p();
  p(book.row);
  p();
  p("Read `record_type`, `record_key` and `record_grain` together. The key preserves the source record's identity; neither a repeated entity nor a matching name is a reason to collapse observations.");
  p();
  p("## Key identifiers"); p();
  p(names(/(^record_key$|(?:^|_)(?:id|ids|uid|uids|uei|cage|ein|key|number)$|^cage_code$)/) || "Use the record key and identifiers defined in the dictionary below.");
  p();
  p("Identifiers identify the subject or relationship stated in their definition. Business, certifier, owner, recipient and source-record identifiers are not interchangeable. Identifier strings keep their leading zeros.");
  p();
  p("## Sources and coverage"); p();
  p(`**Release provenance:** ${book.where}`);
  p();
  const count = entry.sample.of;
  p(Number.isSafeInteger(count) && count >= 0
    ? `**Rows in the installed spreadsheet:** ${count.toLocaleString("en-US")}. The served preview contains ${sample.rows.length.toLocaleString("en-US")} rows. A preview is not a representative population sample or a source-fact audit.`
    : `The served preview contains ${sample.rows.length.toLocaleString("en-US")} rows; a full-spreadsheet count is not recorded in this manifest.`);
  const table = entry.tables?.find((item) => item.table === entry.sample.table || item.name === entry.sample.table);
  if (table?.record_types && typeof table.record_types === "object") {
    const types = Object.entries(table.record_types).filter(([, count]) => Number.isSafeInteger(count) && count >= 0);
    if (types.length) {
      p();
      p("Logical record types retained in this spreadsheet:");
      p();
      for (const [kind, count] of types) p(`- \`${esc(kind)}\`: ${count.toLocaleString("en-US")} observations.`);
    }
  }
  p();
  p("## Time and geography"); p();
  p("Each date and geographic field retains the meaning stated in its definition. Observation, publication, award, performance and ownership-effective dates describe different events. A current source does not establish historical ownership.");
  p();
  p("## Entity relationships"); p();
  p("A Cedar entity link is a relationship to the record in its stated role. Read each party's identifier and role together; an association does not make the record subject identical to its owner, certifier or other party.");
  if (collection === "owned") {
    p();
    p("The certifying authority identifies who lists or certifies the business. It does not establish tribal-government ownership, and individual Native ownership is a separate claim.");
  }
  if (collection === "subcontracting") {
    p();
    p("Prime and subrecipient links describe separate parties. Their Native associations and any ownership-time qualification remain separate; a Native prime does not make its subcontractors Native, and a present association does not verify ownership on the subaward date.");
  }
  if (collection === "nonprofits") {
    p();
    p("A name match, heuristic flag or candidate classification is not independently verified Native governance or ownership. Apply the row's evidence and review qualifications.");
  }
  if (collection === "need") {
    p();
    p("Use only the relationships supported by the reviewed public record. A blank parent or missing relationship field does not imply a direct owner, a resolved identity or an approved graph edge.");
  }
  p();
  p("Joining two detailed collections on an entity identifier can multiply rows. Establish compatible grain, role and period before joining measures.");
  p();
  p("## Revisions"); p();
  p("The installed manifest and field dictionary identify the release used here. Preserve source record keys and version qualifications when comparing releases. A changed sample does not establish that a source event changed.");
  p();
  p("## Field dictionary"); p();
  p(`The ${book.fields.length} columns below follow the served spreadsheet header exactly. Types describe the sample's formatting; they do not infer missing values or revise the producer's field definitions.`);
  p();
  p("| # | Column | Label | Definition | Type | Blank means |");
  p("|---|---|---|---|---|---|");
  book.fields.forEach((field, index) => {
    const type = facts.typed.get(field.column);
    p(`| ${index + 1} | \`${field.column}\` | ${esc(field.label)} | ${esc(field.meaning)} | ${esc(type)} | ${esc(blankMeans(field.column, undefined, type))} |`);
  });
  p();
  p("The \"Blank means\" column is the general rule for a column of that type; the producer's field definition beside it takes precedence where it states a narrower meaning.");
  p();
  p("### Units and formats"); p();
  if (facts.money.length) {
    const nominal = facts.money.filter((c) => !facts.real2025.includes(c)).map((c) => `\`${c}\``).join(", ");
    p(`- Money columns are nominal US dollars as recorded, no rounding: ${nominal || "none at nominal value in this spreadsheet"}.${facts.real2025.length ? ` Columns ending \`_real2025\` (${facts.real2025.map((c) => `\`${c}\``).join(", ")}) are the same amounts adjusted to 2025 dollars, as the dictionary states; a nominal and a 2025-dollar column are never added together.` : ""}${facts.currencyColumn ? " The `currency` column states the reported currency of each row where it is filled; a blank currency is a gap, not an assumption of US dollars." : ""}`);
  } else {
    p("- This spreadsheet carries no money column.");
  }
  if (facts.dateColumns.length || facts.datetimeColumns.length || facts.monthPrecision.length) {
    p(`- Dates are ISO 8601 calendar dates (YYYY-MM-DD).${facts.precisionColumns.length ? ` Where a precision column (${facts.precisionColumns.map((c) => `\`${c}\``).join(", ")}) states \`month\` or \`year\`, the date is written to that precision (YYYY-MM or YYYY) and no day is invented.` : ""}${facts.datetimeColumns.length ? ` Date-time columns (${facts.datetimeColumns.map((c) => `\`${c}\``).join(", ")}) carry their UTC offset.` : ""}`);
  }
  p("- Identifiers, codes, FIPS and EIN values are text and keep their leading zeros.");
  p();
  p("### Observed in the preview"); p();
  p("Measured from the served preview rows when this guide was generated; a preview describes itself, not the full spreadsheet.");
  p();
  p(`- Preview rows: ${facts.rowCount.toLocaleString("en-US")}; record types present: ${facts.recordTypes.map(([kind, count]) => `\`${esc(kind)}\` (${count})`).join(", ") || "none"}.`);
  p(`- Columns blank on every preview row (${facts.allBlank.length} of ${book.fields.length}): ${facts.allBlank.length ? facts.allBlank.map((c) => `\`${c}\``).join(", ") : "none"}. A column blank in the preview can be filled elsewhere in the spreadsheet; it is reported so a reader does not read the preview as the column's coverage.`);
  p(`- Literal tokens present as cell values: ${facts.tokens.length ? facts.tokens.map(({ column, token, count }) => `\`${esc(token)}\` in \`${column}\` (${count})`).join("; ") : "none"}. A token is the producer's declared value where the field definition above defines it; a token the definition does not define is a finding for the producer, never a value to recode.`);
  p();
  p("## Missing values"); p();
  p("A blank is not zero, an invented date, proof of no relationship or permission to fill a value from another party. Preserve documented distinctions between unknown, not applicable and withheld values. Do not infer a redaction marker that the field contract does not declare.");
  p();
  p("## Limitations"); p();
  p("- The spreadsheet and its sample retain the release's publication scope and field restrictions. A guide grants no additional access.");
  p("- An absent or withheld name must not be reconstructed from aliases, other fields or source text.");
  p("- This dictionary documents fields; it does not verify every source fact, entity binding or historical relationship.");
  p("- Record types and grains may overlap. The combined spreadsheet is not automatically an additive analytical table.");
  p();
  p("## Suitable analyses"); p();
  p("Inspect and compare observations within a declared record type, at the stated grain, using the row's source and qualifications. Count unique subjects only after identity and multiplicity are established.");
  p();
  p("## Unsafe aggregations"); p();
  p("- Summing across overlapping record types, report versions or incompatible periods.");
  p("- Treating obligations, allocations, payments, ceilings and reported spending as the same measure.");
  p("- Counting entity associations, certifications or filings as unique businesses or owners.");
  p("- Interpreting a current association as verified historical ownership.");
  p();
  p("## What is still owed"); p();
  p("Any unresolved field, identity, source or publication qualification remains unresolved in this guide. Required engineering checks and owner adjudications must be recorded separately; a generated dictionary does not close them.");
  p();
  p("## Release, citation and method"); p();
  p(`**Release:** ${book.where}`);
  p();
  p(`**Cite as:** Lumecon, "${name}", Cedar Press collection, cedarpress.ai.${updated ? ` Updated ${updated}.` : ""} Accessed <date>.`);
  p();
  p("This is the sentence every download of the collection carries. Cite the collection by its name and Updated date, never by a version label, file count or table count; add the record type and record key for a row-specific claim, and the exact release identifier above when a reviewer must reproduce the file.");
  p();
  p(`**Method:** the preview is an excerpt of the installed producer spreadsheet. ${columns.has("source_url") ? "The source_url field and the dictionary's other source fields carry row-level provenance." : "Use the source fields defined in the dictionary for row-level provenance."}`);
  p();
  p("Dataset-level release details and citation belong here and in the manifest, never as rows appended to the CSV.");
  p();
  return lines.join("\n") + "\n";
}

// ── One guide ──────────────────────────────────────────────────────────────

function guideFor(collection) {
  const { GUIDES, MANIFEST, DESCRIPTORS, MAP, CODEBOOK } = guideData();
  const prose = GUIDES.collections[collection];
  const entry = MANIFEST.collections.find((c) => c.id === collection);
  const descriptor = DESCRIPTORS.find((d) => d.id === collection) ?? entry?.descriptor ?? {};
  const current = releasedBook(entry, CODEBOOK);
  if (current) {
    const sample = sampleFor(collection);
    if (!sample) throw new Error(`Missing installed spreadsheet sample: ${collection}`);
    return renderReleasedGuide(collection, current.book, entry, descriptor, sample);
  }
  if (!prose) {
    throw new Error(`Missing authored guide or installed producer dictionary: ${collection}`);
  }
  const version = entry?.descriptor?.version ?? descriptor.version ?? "v0";
  const updated = entry?.descriptor?.updated ?? descriptor.updated ?? "";
  const vintage = entry?.descriptor?.vintage ?? descriptor.vintage;
  const mapKey = Object.keys(MAP.tables).find((k) => MAP.tables[k].collection === collection);
  const map = mapKey ? MAP.tables[mapKey] : null;
  const book = mapKey ? CODEBOOK.tables[mapKey] : null;
  const sample = sampleFor(collection);
  const name = descriptor.name ?? entry?.descriptor?.name ?? collection;
  const lines = [];
  const p = (s = "") => lines.push(s);
  p(`# ${name}: a researcher's guide`);
  p();
  p(`Collection \`${collection}\` · public file \`${map?.public_file ?? `${collection}.csv`}\` · ${version}${updated ? ` · ${updated}` : ""}. Generated from \`data/cedar/guides.json\`, \`data/cedar/field_map.json\`, \`data/cedar/codebook.json\` and the collection descriptor by \`scripts/docs-markdown.mjs --kind guides\`; edit those, not this file. Written 2026-09-05 under \`docs/PUBLIC_DATASET_SPEC_2026-09-05.md\`.`);
  p();
  p("## Purpose");
  p();
  p(descriptor.tracks ?? "");
  p();
  p("## Population");
  p();
  p(prose.population);
  p();
  p("## One row is");
  p();
  if (map) {
    p(map.row);
    p();
    p("This pass changes columns, never rows: no aggregation, deduplication, change of publication eligibility or reassignment of Cedar IDs.");
    if (map.note) { p(); p(`**Note:** ${map.note}`); }
  }
  p();
  p("## Key identifiers");
  p();
  p(prose.identifiers);
  p();
  p("## Sources and coverage");
  p();
  p(`**Sources:** ${descriptor.sources ?? ""}`);
  p();
  const of = entry?.sample?.of;
  if (of) {
    p(`**Rows in the flagship table as released${updated ? ` (recorded ${updated})` : ""}:** ${of.toLocaleString("en-US")}. This is the count the release recorded for \`${entry.sample.table}\`, not the sum of the collection's ${entry.tables?.length ?? "supporting"} tables; the finished public table is re-measured at release and the count here is replaced by that measurement.`);
  } else {
    p("**Rows in the flagship table as released:** not yet measured; the flagship sample is not in the repository.");
  }
  p();
  p("## Time and geography");
  p();
  p(prose.time_and_geography);
  p();
  p("## Entity relationships");
  p();
  p(map?.plural
    ? `The opening block of every row is \`cedar_uids\`, \`canonical_names\`, \`entity_classes\`, \`entity_roles\` and \`entity_names_as_published\`, aligned JSON arrays. ${prose.entity_relationships}`
    : `The opening block of every row is \`cedar_uid\`, \`canonical_name\`, \`entity_class\` and \`cedar_entity_role\`. ${prose.entity_relationships}`);
  if (map?.entity_roles?.length) {
    p();
    p("Further role-specific links on the row, each an entity of the record the viewer finds it by:");
    p();
    for (const r of map.entity_roles) p(`- \`${r.column}\`: ${r.role}${r.list ? " (several, separated by |)" : ""}`);
  }
  p();
  p("Joining detailed collections on `cedar_uid` alone multiplies rows: one entity has many transactions here and many elsewhere. Aggregate each collection to the entity, or the entity and year, before joining measures.");
  p();
  p("## Revisions");
  p();
  p(prose.revisions);
  p();
  p("## Field dictionary");
  p();
  if (map && book && map.fields.length) {
    p(`The approved header, in the owner's exact order (${map.order.length} columns, of which ${map.new.filter((n) => n.status).length} are owed and marked so). Data types are read off the ten-row sample the site serves; identifiers are text and keep leading zeros; a JSON array cell is one list, aligned with its neighbours where the dictionary says so.`);
    p();
    p("| # | Column | Label | Definition | Type | Blank means |");
    p("|---|---|---|---|---|---|");
    const byShipped = new Map();
    const decisionOf = new Map(map.fields.map((f) => [f.column, f]));
    for (const f of book.fields) {
      const decision = decisionOf.get(f.column);
      const target = decision?.decision === "rename" ? decision.to : (f.rename_to ?? f.column);
      const changed = target !== (f.rename_to ?? f.column);
      byShipped.set(target, changed
        ? { ...f, rename_to: target, label: target.replace(/_/g, " "), meaning: decision.why || f.meaning }
        : f);
    }
    const values = (col) => (sample?.rows ?? []).map((r) => r[col]);
    map.order.forEach((col, i) => {
      const field = byShipped.get(col);
      const added = map.new.find((n) => n.column === col);
      if (!field && added) {
        const availability = added.status
          ? "owed: not in the file until the producer builds it"
          : "See source qualification; not inferred from a legacy sample";
        p(`| ${i + 1} | \`${col}\` | ${esc(col.replace(/_/g, " "))} | ${esc(added.why || "See the declared field contract.")} | ${GUIDES.types.text} | ${availability} |`);
        return;
      }
      if (!field) return;
      const source = field.column;
      const decision = decisionOf.get(source)?.decision ?? "add";
      const type = field.add
        ? (map.plural && map.order.slice(0, 5).includes(col) || /^(additional_|entity_link_statuses$)/.test(col) ? GUIDES.types.json
          : col === "cedar_uid" ? GUIDES.types.id : /url/.test(col) ? GUIDES.types.url : GUIDES.types.text)
        : typeOf(source, values(source));
      const was = field.rename_to ? ` (was \`${source}\`)` : "";
      p(`| ${i + 1} | \`${col}\`${was} | ${esc(field.label)} | ${esc(field.meaning)} | ${type} | ${blankMeans(col, decision, type)} |`);
    });
    p();
    // A combine's sources, shown until the combined column exists.
    const combining = book.fields.filter((f) => f.combine_into);
    if (combining.length) {
      p("Until the combined columns exist, the file carries their sources, each with its own label:");
      p();
      for (const f of combining) p(`- \`${f.column}\` (${esc(f.label)}) combines into \`${f.combine_into}\`: ${esc(f.meaning)}`);
      p();
    }
  } else {
    p("The field dictionary is written when this collection's flagship sample lands in the repository and its field map is decided. The approved opening block and the specification's field list for it:");
    p();
    for (const col of map?.order ?? []) {
      const n = map.new.find((x) => x.column === col);
      p(`- \`${col}\`${n?.why ? `: ${n.why}` : ""}`);
    }
    p();
  }
  p("## Missing values");
  p();
  p("A blank is never zero and never an invented date. A blank JSON-list cell means unknown; `[]` means known to be empty (no additional source, no additional institution); a null element inside a list is one member the evidence names but does not resolve. Identifiers and codes are text with their leading zeros. Beyond the column-level rules above:");
  p();
  for (const m of prose.missing_values) p(`- ${m}`);
  p();
  p("## Limitations");
  p();
  for (const l of prose.limitations) p(`- ${l}`);
  p();
  p("## Suitable analyses");
  p();
  for (const a of prose.suitable_analyses) p(`- ${a}`);
  p();
  p("## Unsafe aggregations");
  p();
  for (const u of prose.unsafe_aggregations) p(`- ${u}`);
  p();
  p("## What is still owed");
  p();
  const owed = (map?.new ?? []).filter((n) => n.status);
  const adjudicate = (map?.retire ?? []).filter((r) => r.disposition === "adjudicate" || r.value_level);
  if (adjudicate.length) {
    p("Identifier retirement findings that stop this dataset until they are settled (see `docs/IDENTIFIER_RETIREMENT_2026-09-05.md`):");
    p();
    for (const r of adjudicate) p(`- \`${r.column}\`: ${esc(r.identifies)} (${r.disposition}).`);
    p();
  }
  if (owed.length) {
    p("Target columns the specification asks for that the terminal has not yet built from the full table. Each is absent until it exists, never blank.");
    p();
    for (const n of owed) p(`- \`${n.column}\` (${esc(n.from)}): ${esc(n.why || "see the field map")}`);
  } else {
    p("Nothing beyond the grain and harmonization work named above.");
  }
  p();
  p("## Release, citation and method");
  p();
  p(`**Version:** ${version}${vintage ? `, vintage ${vintage}` : ""}. **Release date:** ${updated || "not recorded"}.`);
  p();
  p(`**Cite as:** Lumecon, "${name}" (${version}${vintage ? `, vintage ${vintage}` : ""}), Cedar Press collection, cedarpress.ai. Add the date accessed.`);
  p();
  p(`**Method:** ${descriptor.method ?? ""}`);
  p();
  p("Dataset-level version, release date and citation live here and in the manifest, never as rows appended to the CSV. The row-level `source_url` and the qualifications named above are the file's own provenance.");
  p();
  return lines.join("\n") + "\n";
}

export function renderAll() {
  const { GUIDES, DESCRIPTORS, MANIFEST } = guideData();
  const collections = [...new Set([
    ...Object.keys(GUIDES.collections),
    ...MANIFEST.collections.map((entry) => entry.id),
  ])];
  const out = {};
  for (const collection of collections) out[`${OUT_DIR}${collection}.md`] = guideFor(collection);
  out[`${OUT_DIR}README.md`] = [
    "# Researcher guides",
    "",
    "One guide per Cedar Press collection, generated by `scripts/docs-markdown.mjs --kind guides`. Installed producer spreadsheets use their manifest-selected dictionary and exact served header, with the release's record grains and qualifications. Collections without an installed producer spreadsheet retain the authored guide and compatibility field map. Edit the input contracts and regenerate; a test fails when these files are stale.",
    "",
    ...collections.map((c) => {
      const d = MANIFEST.collections.find((x) => x.id === c)?.descriptor ?? DESCRIPTORS.find((x) => x.id === c) ?? {};
      return `- [${d.name ?? c}](${c}.md) (\`${c}\`)`;
    }),
    "",
  ].join("\n");
  return out;
}



export function parseDocumentArguments(argv) {
  let kind = null;
  let check = false;
  const seen = new Set();
  for (let i = 0; i < argv.length; i += 1) {
    const flag = argv[i];
    if (!["--kind", "--check"].includes(flag) || seen.has(flag)) throw new Error("Use --kind codebook|field-map|guides|all [--check].");
    seen.add(flag);
    if (flag === "--check") check = true;
    else kind = argv[++i];
  }
  if (!["codebook", "field-map", "guides", "all"].includes(kind)) throw new Error("Choose --kind codebook, field-map, guides or all.");
  return { kind, check };
}

export function renderDocuments(kind) {
  if (kind === "codebook") return { [REPO + "docs/DATASET_CODEBOOK.md"]: render() };
  if (kind === "field-map") return {
    [REPO + "docs/FIELD_MAP_2026-09-05.md"]: renderMap(),
    [REPO + "docs/IDENTIFIER_RETIREMENT_2026-09-05.md"]: renderRetirement(),
  };
  if (kind === "guides") return renderAll();
  if (kind === "all") return Object.assign({}, renderDocuments("codebook"), renderDocuments("field-map"), renderDocuments("guides"));
  throw new Error("Unknown document kind.");
}

export function staleDocuments(files) {
  return Object.entries(files)
    .filter(([path, text]) => !existsSync(path) || readFileSync(path, "utf8") !== text)
    .map(([path]) => path);
}

export function main(argv) {
  const { kind, check } = parseDocumentArguments(argv);
  const files = renderDocuments(kind);
  if (check) {
    const stale = staleDocuments(files).map(path => path.slice(REPO.length));
    if (stale.length) {
      process.stderr.write(stale.join(", ") + " stale or missing. Run node scripts/docs-markdown.mjs --kind " + kind + " and commit the result.\n");
      return 1;
    }
    process.stdout.write("  " + kind + " documents current\n");
    return 0;
  }
  for (const [path, text] of Object.entries(files)) {
    mkdirSync(dirname(path), { recursive: true });
    writeFileSync(path, text);
  }
  process.stdout.write("  wrote " + Object.keys(files).length + " " + kind + " document(s)\n");
  return 0;
}
if (process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1])) {
  try { process.exitCode = main(process.argv.slice(2)); }
  catch (error) { process.stderr.write(error.message + "\n"); process.exitCode = 2; }
}
