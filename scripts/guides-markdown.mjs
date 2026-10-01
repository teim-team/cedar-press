// Render one researcher guide per collection into docs/guides/<collection>.md
// (docs/PUBLIC_DATASET_SPEC_2026-09-05.md §16), from four sources that are
// each kept in step by a test:
//
//   data/cedar/guides.json                the prose: population, identifiers,
//                                         time and geography, relationships,
//                                         revisions, limitations, analyses
//   data/cedar/collection_descriptors.json  purpose, sources and method, the
//                                         measured copy the storefront shows
//   data/cedar/field_map.json             the row unit, the grain, the roles,
//                                         the approved header and what is owed
//   data/cedar/codebook.json              the field dictionary: label, meaning
//                                         and the shipped name of each column
//
// The data type of each column is read off the ten-row sample the site
// serves, and says so. Counts are the release's, quoted with their date; the
// finished public table is re-measured at release, which this script cannot
// do from the repository.
//
//     node scripts/guides-markdown.mjs            # write docs/guides/*.md
//     node scripts/guides-markdown.mjs --check    # exit 1 if any guide is stale

import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { assertReleasedDictionary, releasedBook } from "./release-docs.mjs";

const REPO = fileURLToPath(new URL("..", import.meta.url));
const GUIDES = JSON.parse(readFileSync(`${REPO}data/cedar/guides.json`, "utf8"));
const MAP = JSON.parse(readFileSync(`${REPO}data/cedar/field_map.json`, "utf8"));
const CODEBOOK = JSON.parse(readFileSync(`${REPO}data/cedar/codebook.json`, "utf8"));
const MANIFEST = JSON.parse(readFileSync(`${REPO}data/cedar/collections.manifest.json`, "utf8"));
const DESCRIPTORS = JSON.parse(readFileSync(`${REPO}data/cedar/collection_descriptors.json`, "utf8"));
const OUT_DIR = `${REPO}docs/guides/`;

export const SECTIONS = [
  "Purpose", "Population", "One row is", "Key identifiers", "Sources and coverage",
  "Time and geography", "Entity relationships", "Revisions", "Field dictionary",
  "Missing values", "Limitations", "Suitable analyses", "Unsafe aggregations",
  "What is still owed", "Release, citation and method",
];

const esc = (s) => String(s ?? "").replace(/\|/g, "\\|").replace(/\r?\n/g, " ");

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
  const entry = MANIFEST.collections.find((c) => c.id === collection);
  const path = entry?.sample?.path ? `${REPO}public${entry.sample.path}` : null;
  if (!path || !existsSync(path)) return null;
  return parseCsv(readFileSync(path, "utf8"));
}

function typeOf(column, values) {
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
  if (filled.every((v) => /^-?\d+(\.\d+)?$/.test(v)) && !/code|period|month|fips|zip/.test(name)) return T.number;
  if (filled.some((v) => v.includes("|")) && filled.every((v) => !/^https?:/.test(v)) && /entities|counties|states|codes|organizations|variants/.test(name)) return T.list;
  return T.text;
}

function blankMeans(column, decision, type) {
  const T = GUIDES.types;
  if (decision === "withhold") return "masked where the publication policy withholds it; otherwise the source reports none";
  if (/^n_/.test(column)) return "not stated by the source; 0 means the source states none";
  if (type === T.yesno) return "not stated; 0 is no";
  if (type === T.money) return "the source reports no amount; never zero";
  if (type === T.date || type === T.datetime || type === T.year) return "the source states no date";
  if (/cedar_uid|cedar_entity/.test(column)) return "unattributed or unresolved, with the reason in the attribution status where the table carries one; never non-Native";
  return "the source states none, or not applicable to this row";
}

export function renderReleasedGuide(collection, book, entry, descriptor, sample) {
  assertReleasedDictionary(book, sample);
  const lines = [];
  const p = (text = "") => lines.push(text);
  const name = book.dataset || descriptor.name || collection;
  const columns = new Set(book.fields.map((field) => field.column));
  const names = (pattern) => book.fields.filter((field) => pattern.test(field.column)).map((field) => `\`${field.column}\``).join(", ");
  p(`# ${name}: a researcher's guide`);
  p();
  p(`Collection \`${collection}\` · producer spreadsheet \`${entry.sample.table}\`. Generated by \`scripts/guides-markdown.mjs\` from the installed release manifest and its field dictionary. The statements below describe that release.`);
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
    const values = sample.rows.map((row) => row[field.column]);
    const type = field.column === "record_key" ? "JSON source key" : typeOf(field.column, values);
    p(`| ${index + 1} | \`${field.column}\` | ${esc(field.label)} | ${esc(field.meaning)} | ${esc(type)} | Not recorded in this export; consult the field definition and publication policy. |`);
  });
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
  p(`**Cite as:** Lumecon, "${name}", Cedar Press collection, cedarpress.ai, the exact release named above. Add the date accessed and the record type and key for row-specific claims.`);
  p();
  p(`**Method:** the preview is an excerpt of the installed producer spreadsheet. ${columns.has("source_url") ? "The source_url field and the dictionary's other source fields carry row-level provenance." : "Use the source fields defined in the dictionary for row-level provenance."}`);
  p();
  p("Dataset-level release details and citation belong here and in the manifest, never as rows appended to the CSV.");
  p();
  return lines.join("\n") + "\n";
}

// ── One guide ──────────────────────────────────────────────────────────────

function guideFor(collection) {
  const prose = GUIDES.collections[collection];
  const entry = MANIFEST.collections.find((c) => c.id === collection);
  const descriptor = DESCRIPTORS.find((d) => d.id === collection) ?? entry?.descriptor ?? {};
  const current = releasedBook(entry, CODEBOOK);
  if (current) {
    const sample = sampleFor(collection);
    if (!sample) throw new Error(`Missing installed spreadsheet sample: ${collection}`);
    return renderReleasedGuide(collection, current.book, entry, descriptor, sample);
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
  p(`Collection \`${collection}\` · public file \`${map?.public_file ?? `${collection}.csv`}\` · ${version}${updated ? ` · ${updated}` : ""}. Generated from \`data/cedar/guides.json\`, \`data/cedar/field_map.json\`, \`data/cedar/codebook.json\` and the collection descriptor by \`scripts/guides-markdown.mjs\`; edit those, not this file. Written 2026-09-05 under \`docs/PUBLIC_DATASET_SPEC_2026-09-05.md\`.`);
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
  const out = {};
  for (const collection of Object.keys(GUIDES.collections)) out[`${OUT_DIR}${collection}.md`] = guideFor(collection);
  out[`${OUT_DIR}README.md`] = [
    "# Researcher guides",
    "",
    "One guide per Cedar Press collection, generated by `scripts/guides-markdown.mjs`. Installed producer spreadsheets use their manifest-selected dictionary and exact served header, with the release's record grains and qualifications. Collections without an installed producer spreadsheet retain the authored guide and compatibility field map. Edit the input contracts and regenerate; a test fails when these files are stale.",
    "",
    ...Object.keys(GUIDES.collections).map((c) => {
      const d = DESCRIPTORS.find((x) => x.id === c) ?? {};
      return `- [${d.name ?? c}](${c}.md) (\`${c}\`)`;
    }),
    "",
  ].join("\n");
  return out;
}

function main(argv) {
  const files = renderAll();
  if (argv.includes("--check")) {
    const stale = Object.entries(files).filter(([path, text]) => !existsSync(path) || readFileSync(path, "utf8") !== text).map(([path]) => path.slice(REPO.length));
    if (!stale.length) { process.stdout.write(`  guides    ${Object.keys(files).length - 1} guide(s) current\n`); return 0; }
    process.stderr.write(`${stale.join(", ")} stale or missing. Run \`node scripts/guides-markdown.mjs\` and commit the result.\n`);
    return 1;
  }
  mkdirSync(OUT_DIR, { recursive: true });
  for (const [path, text] of Object.entries(files)) writeFileSync(path, text);
  process.stdout.write(`  wrote ${Object.keys(files).length - 1} guides to docs/guides/\n`);
  return 0;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  process.exit(main(process.argv.slice(2)));
}
