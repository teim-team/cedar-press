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

const REPO = fileURLToPath(new URL("..", import.meta.url));
const CODEBOOK = `${REPO}data/cedar/codebook.json`;
const MANIFEST = `${REPO}data/cedar/collections.manifest.json`;
const NOTE = "docs/COLUMN_ORDER_NOTE_FOR_THE_TERMINAL_2026-09-05.md";
const OUT = `${REPO}docs/DATASET_CODEBOOK.md`;

export function render() {
  const codebook = JSON.parse(readFileSync(CODEBOOK, "utf8"));
  const manifest = JSON.parse(readFileSync(MANIFEST, "utf8"));
  const byId = Object.fromEntries(manifest.collections.map((c) => [c.id, c]));
  const lines = [];
  const p = (s = "") => lines.push(s);
  p("# Cedar Press datasets: the proposed structure of each, for review");
  p();
  p("Generated from `data/cedar/codebook.json` by `scripts/codebook-markdown.mjs`; edit the JSON, not this file. Written 2026-09-05.");
  p();
  p("## What this is");
  p();
  p("Cedar Press sells twelve collections. Each collection has one customer-facing dataset (its flagship table) and, in the workspace, a number of supporting tables. Today the flagship files carry between 37 and 78 columns, of which a third to two-thirds are pipeline bookkeeping: how a row was matched, when it was built, the basis of a derived value. This document is the data dictionary of the structure each dataset has when a customer downloads it under `docs/PUBLIC_DATASET_SPEC_2026-09-05.md`: what one row is, and the columns that ship, each with a plain-English label and what it means. Every column here is one `docs/FIELD_MAP_2026-09-05.md` ships, under the name the map gives it; columns not listed stay in the workspace, and the per-column decisions with their reasons are in the map (the earlier reasoning is in `" + NOTE + "`).");
  p();
  p("Three rules apply to every dataset:");
  p();
  p("1. **The Cedar opening block comes first**: `cedar_uid` (the entity's permanent ID), `canonical_name` (its name as Cedar's register spells it), `entity_class` (which of Cedar's eighteen classes it is) and `cedar_entity_role` (why the entity is on the row). The first three are the join key across collections; the fourth says what the join means. Legislation and NAGPRA, whose records concern several entities, carry the plural block instead: `cedar_uids`, `canonical_names`, `entity_classes`, `entity_roles`, `entity_names_as_published`, aligned JSON arrays with one position per entity-role association. Where a table lacks a column today it is marked *to add* and the writer fills it from the register; where it carries the same thing under another name, the rename is shown; a combine's sources are shown until the combined column exists.");
  p("2. **One row is one thing**, stated at the top of each dataset, and this pass changes columns, never rows; a table whose records concern several entities carries them in the plural block's aligned arrays, never as several ids in one singular cell.");
  p("3. **Every amount says what it is** (an obligation, an announced value, a reported spend) and is never summed across datasets; every row cites a source; every dataset ends with `research_note`, a concise factual qualification, blank when nothing needs saying.");
  p();
  p("Where the data lives: the full tables are built in the Cedar data workspace by `code/1135_full_dataset_review_bundle.py` into `dist/review/spreadsheets/<collection>/<table>.csv` (6.2 GB in all, not in the website repository); ten-row samples of each are copied to the website at `public/data/cedar/samples/<collection>/<table>__10.csv` and served at `https://cedarpress.ai/data/cedar/samples/...`. The entity register is `data/spine/cedar_entity_names.csv` (1,916 entities, 18 classes).");
  p();
  p("Meanings below were read from the column names and ten rows of values and are to be confirmed against the build scripts; a meaning marked *(confirm)* is the least certain.");
  p();
  p("## The datasets");
  p();
  for (const [key, table] of Object.entries(codebook.tables)) {
    const collection = byId[table.collection];
    const rows = collection?.sample?.of ?? null;
    p(`### ${table.dataset}`);
    p();
    p(`Collection \`${table.collection}\` · table \`${key.split("/")[1]}\`${rows ? ` · ${rows.toLocaleString("en-US")} rows in the full table` : ""} · ${collection?.descriptor?.shelf === "pro" ? "Cedar Press+" : "Cedar Press"} shelf`);
    p();
    p(`**One row is** ${table.row}`);
    p();
    p(`**Where:** ${table.where}`);
    p();
    p(`**Columns a subscriber sees (${table.fields.length}):**`);
    p();
    p("| # | Column | Label | Meaning |");
    p("|---|---|---|---|");
    table.fields.forEach((field, i) => {
      const flags = [field.add ? "*to add*" : "", field.rename_to ? `*rename to \`${field.rename_to}\`*` : "", field.combine_into ? `*combines into \`${field.combine_into}\`*` : ""].filter(Boolean).join(", ");
      p(`| ${i + 1} | \`${field.column}\`${flags ? ` (${flags})` : ""} | ${field.label} | ${field.meaning.replace(/\|/g, "\\|")} |`);
    });
    p();
  }
  p("## Questions for the reviewer");
  p();
  p("- Is any kept column unnecessary for a subscriber, and is any dropped column (see the note) something a subscriber would miss?");
  p("- Are the labels the words a subscriber would use? Is any meaning wrong or unclear?");
  p("- Is the opening block the right first four columns for every dataset, and should the record's own identifier be the fifth everywhere?");
  p("- For datasets whose rows name several entities (Legislation, NAGPRA), is one row per record with `|`-separated entities better than one row per record and entity?");
  p("- Which datasets should carry inflation-adjusted amounts, and should the base year be a column or a note?");
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
