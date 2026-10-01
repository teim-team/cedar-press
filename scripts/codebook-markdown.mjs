// Render data/cedar/codebook.json as the review document a reader (or a
// reviewer, or ChatGPT) can read without the repository:
//
//     node scripts/codebook-markdown.mjs            # write docs/DATASET_CODEBOOK.md
//     node scripts/codebook-markdown.mjs --check    # exit 1 if the document is stale
//
// The codebook is the one source: the viewer reads it for labels and
// meanings, this document is generated from it, and a test keeps the two in
// step so the structure a reviewer reads is the structure the site shows.

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { releasedBook } from "./release-docs.mjs";

const REPO = fileURLToPath(new URL("..", import.meta.url));
const CODEBOOK = `${REPO}data/cedar/codebook.json`;
const MANIFEST = `${REPO}data/cedar/collections.manifest.json`;
const OUT = `${REPO}docs/DATASET_CODEBOOK.md`;

export function render() {
  const codebook = JSON.parse(readFileSync(CODEBOOK, "utf8"));
  const manifest = JSON.parse(readFileSync(MANIFEST, "utf8"));
  const byId = Object.fromEntries(manifest.collections.map((entry) => [entry.id, entry]));
  const current = new Map();
  for (const entry of manifest.collections) {
    const selected = releasedBook(entry, codebook);
    if (selected) current.set(selected.key, selected.book);
  }
  const lines = [];
  const p = (text = "") => lines.push(text);
  const esc = (value) => String(value ?? "").replace(/\|/g, "\\|").replace(/\r?\n/g, " ");
  p("# Cedar Press dataset dictionaries");
  p();
  p("Generated from `data/cedar/codebook.json` and `data/cedar/collections.manifest.json` by `scripts/codebook-markdown.mjs`. Edit the source dictionaries and regenerate this document.");
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

function main(argv) {
  const text = render();
  if (argv.includes("--check")) {
    const held = existsSync(OUT) ? readFileSync(OUT, "utf8") : null;
    if (held === text) { process.stdout.write("  codebook  document current\n"); return 0; }
    process.stderr.write("docs/DATASET_CODEBOOK.md is stale. Run `node scripts/codebook-markdown.mjs` and commit the result.\n");
    return 1;
  }
  writeFileSync(OUT, text);
  process.stdout.write(`  wrote docs/DATASET_CODEBOOK.md\n`);
  return 0;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  process.exit(main(process.argv.slice(2)));
}
