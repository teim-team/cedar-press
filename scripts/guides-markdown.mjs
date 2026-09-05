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

// ── One guide ──────────────────────────────────────────────────────────────

function guideFor(collection) {
  const prose = GUIDES.collections[collection];
  const entry = MANIFEST.collections.find((c) => c.id === collection);
  const descriptor = DESCRIPTORS.find((d) => d.id === collection) ?? entry?.descriptor ?? {};
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
    p(`**Today:** ${map.row_today}`);
    p();
    p(`**When the specification is applied:** ${map.row_target}`);
    if (map.grain_change) { p(); p(`**Grain change:** ${map.grain_change}`); }
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
  p(`The opening block of every row is \`cedar_uid\`, \`cedar_entity_name\`, \`cedar_entity_type\` and \`cedar_entity_role\`. ${prose.entity_relationships}`);
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
    p(`The approved header, in order (${map.order.length} columns, of which ${map.new.filter((n) => n.status).length} are owed and marked so). Data types are read off the ten-row sample the site serves; identifiers are text and keep leading zeros.`);
    p();
    p("| # | Column | Label | Definition | Type | Blank means |");
    p("|---|---|---|---|---|---|");
    const byShipped = new Map();
    for (const f of book.fields) byShipped.set(f.rename_to ?? f.column, f);
    const decisionOf = new Map(map.fields.map((f) => [f.column, f]));
    const values = (col) => (sample?.rows ?? []).map((r) => r[col]);
    map.order.forEach((col, i) => {
      const field = byShipped.get(col);
      const added = map.new.find((n) => n.column === col);
      if (!field && added?.status) {
        p(`| ${i + 1} | \`${col}\` | ${esc(col.replace(/_/g, " "))} | ${esc(added.why || "Owed: see below.")} | — | owed: not in the file until the terminal builds it |`);
        return;
      }
      if (!field) return;
      const source = field.column;
      const decision = decisionOf.get(source)?.decision ?? "add";
      const type = field.add
        ? (/cedar_uid/.test(col) ? (map.entity_uid_list ? GUIDES.types.list : GUIDES.types.id) : /url/.test(col) ? GUIDES.types.url : GUIDES.types.text)
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
  p("A blank is never zero and never an invented date. Beyond the column-level rules above:");
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
  if (owed.length) {
    p("Target columns the specification asks for that the terminal has not yet built from the full table. Each ships blank-free, not blank: it is absent until it exists.");
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
    "One guide per Cedar Press collection, generated by `scripts/guides-markdown.mjs` from `data/cedar/guides.json` (the prose), `data/cedar/field_map.json` (the row unit, roles, approved header and what is owed), `data/cedar/codebook.json` (the field dictionary) and the collection descriptor (purpose, sources, method). Edit those; a test fails when these files are stale. Each guide carries the sections `docs/PUBLIC_DATASET_SPEC_2026-09-05.md` §16 asks for.",
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
