// Render data/cedar/field_map.json as the document a reviewer reads without
// the repository: the old-to-new field map the specification asks for first
// (docs/PUBLIC_DATASET_SPEC_2026-09-05.md §17).
//
//     node scripts/field-map-markdown.mjs            # write docs/FIELD_MAP_2026-09-05.md
//     node scripts/field-map-markdown.mjs --check    # exit 1 if the document is stale
//
// The JSON is the one source: the customer-file writer reads it
// (code/cedar_publication.apply_field_map), the codebook is kept in step with
// it by a test, and this document is generated from it.

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const REPO = fileURLToPath(new URL("..", import.meta.url));
const MAP = `${REPO}data/cedar/field_map.json`;
const MANIFEST = `${REPO}data/cedar/collections.manifest.json`;
const OUT = `${REPO}docs/FIELD_MAP_2026-09-05.md`;

const esc = (s) => String(s ?? "").replace(/\|/g, "\\|");

export function render() {
  const map = JSON.parse(readFileSync(MAP, "utf8"));
  const manifest = JSON.parse(readFileSync(MANIFEST, "utf8"));
  const byId = Object.fromEntries(manifest.collections.map((c) => [c.id, c]));
  const lines = [];
  const p = (s = "") => lines.push(s);
  p("# Cedar Press datasets: the old-to-new field map");
  p();
  p("Generated from `data/cedar/field_map.json` by `scripts/field-map-markdown.mjs`; edit the JSON, not this file. Written 2026-09-05.");
  p();
  p("## What this is");
  p();
  p("The first step `docs/PUBLIC_DATASET_SPEC_2026-09-05.md` §17 asks for: an inventory of every column each flagship table carries today, with one decision per column, and the approved public header each dataset ships with. The customer-file writer (`code/1137_customer_dataset_combine.py` through `cedar_publication.apply_field_map`) generates the export from this list: it renames, drops what is internal or documented, fills the opening block from the register, orders the header as `order` says, and refuses to build a dataset whose flagship carries a column with no decision here, so a new upstream field needs a publication decision before it can reach a customer.");
  p();
  p("Written against the ten-row samples in `public/data/cedar/samples/`. A decision is validated by the terminal against the full table before it is applied: a blank in ten rows proves nothing, and a `combine` is owed until its sources have been tested for agreement.");
  p();
  p("**Decisions:**");
  p();
  for (const [name, meaning] of Object.entries(map.decisions)) p(`- \`${name}\`: ${meaning}`);
  p();
  p("**The opening block, in every dataset:**");
  p();
  for (const [name, meaning] of Object.entries(map.opening)) p(`- \`${name}\`: ${meaning}`);
  p();
  p("## Summary");
  p();
  p("| Dataset | Columns today | Ship | Keep | Rename | Withhold | Combine | Derive | Document | Internal | Owed |");
  p("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|");
  for (const [key, t] of Object.entries(map.tables)) {
    const count = (d) => t.fields.filter((f) => f.decision === d).length;
    const owed = t.new.filter((n) => n.status === "pending").length;
    p(`| \`${key}\` | ${t.columns_today ?? "no sample"} | ${t.columns_target ?? "—"} | ${count("keep")} | ${count("rename")} | ${count("withhold")} | ${count("combine")} | ${count("derive")} | ${count("document")} | ${count("internal")} | ${owed} |`);
  }
  p();
  p("\"Ship\" counts the approved header including columns still owed; \"Owed\" counts the target columns that do not exist until the terminal builds them (a combined taxonomy, an annual grain, names as published).");
  p();
  p("## The datasets");
  p();
  for (const [key, t] of Object.entries(map.tables)) {
    const collection = byId[t.collection];
    p(`### ${collection?.name ?? t.collection} (\`${key}\`)`);
    p();
    p(`**Public file:** \`${t.public_file}\``);
    p();
    p(`**One row today:** ${t.row_today}`);
    p();
    p(`**One row when the specification is applied:** ${t.row_target}`);
    p();
    if (t.grain_change) { p(`**Grain change:** ${t.grain_change}`); p(); }
    p(`**Entity role (\`cedar_entity_role\`):** ${t.entity_role}`);
    if (t.entity_roles?.length) {
      p();
      p("Role-specific links kept beside the opening block:");
      p();
      for (const r of t.entity_roles) p(`- \`${r.column}\`: ${r.role}${r.list ? " (several, separated by |)" : ""}`);
    }
    p();
    p(`**Approved header (${t.order.length}):** ${t.order.map((c) => `\`${c}\``).join(", ")}`);
    p();
    if (t.fields.length) {
      p(`**Every current column and its decision (${t.fields.length}):**`);
      p();
      p("| # | Column today | Decision | Ships as | Why | Spec |");
      p("|---|---|---|---|---|---|");
      t.fields.forEach((f, i) => {
        const to = f.decision === "keep" || f.decision === "withhold" ? f.column : f.to ?? "";
        p(`| ${i + 1} | \`${f.column}\` | ${f.decision} | ${to ? `\`${to}\`` : "—"} | ${esc(f.why)} | ${f.spec ?? ""} |`);
      });
      p();
    }
    if (t.new.length) {
      p(`**Target columns that do not exist in the file today (${t.new.length}):**`);
      p();
      p("| Column | From | Why | Status |");
      p("|---|---|---|---|");
      for (const n of t.new) p(`| \`${n.column}\` | ${esc(n.from)} | ${esc(n.why)} | ${n.status ?? "built at write time"} |`);
      p();
    }
  }
  p("## What is not decided here");
  p();
  p("- Whether the annual grain the specification asks of Funding and Contractors is supported: the terminal measures the transaction history first (§4, §10), and the transaction-grain header above is what ships until it does.");
  p("- Whether vote and action records ship inside Legislation under a `record_type` or stay supporting tables (§6).");
  p("- Which other advocacy source families join the Lobbying flagship under `activity_type` (§9); each is evaluated against the schema before it ships.");
  p("- The Native-owned businesses map, written when its sample lands and the audit has run (§15).");
  p("- Every `combine`: the sources are tested for agreement before one column replaces them (§17).");
  p();
  return lines.join("\n") + "\n";
}

function main(argv) {
  const text = render();
  if (argv.includes("--check")) {
    const held = existsSync(OUT) ? readFileSync(OUT, "utf8") : null;
    if (held === text) { process.stdout.write("  field map document current\n"); return 0; }
    process.stderr.write("docs/FIELD_MAP_2026-09-05.md is stale. Run `node scripts/field-map-markdown.mjs` and commit the result.\n");
    return 1;
  }
  writeFileSync(OUT, text);
  process.stdout.write("  wrote docs/FIELD_MAP_2026-09-05.md\n");
  return 0;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  process.exit(main(process.argv.slice(2)));
}
