// Render data/cedar/field_map.json as two documents a reviewer reads without
// the repository:
//
//   docs/FIELD_MAP_2026-09-05.md              the field-by-field map behind the
//                                             owner's exact column specification
//   docs/IDENTIFIER_RETIREMENT_2026-09-05.md  the identifier retirement report
//                                             the retirement rule asks for
//
//     node scripts/field-map-markdown.mjs            # write both
//     node scripts/field-map-markdown.mjs --check    # exit 1 if either is stale
//
// The JSON is the one source: the customer-file writer reads it
// (code/cedar_publication.apply_field_map), the codebook is kept in step with
// it by a test, and these documents are generated from it. The retirement
// report's rows_affected is what the writer counts at build; here it is the
// count in the ten-row sample, labelled so.

import { existsSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const REPO = fileURLToPath(new URL("..", import.meta.url));
const MAP = `${REPO}data/cedar/field_map.json`;
const MANIFEST = `${REPO}data/cedar/collections.manifest.json`;
const SAMPLES = `${REPO}public/data/cedar/samples/`;
const OUT_MAP = `${REPO}docs/FIELD_MAP_2026-09-05.md`;
const OUT_RETIRE = `${REPO}docs/IDENTIFIER_RETIREMENT_2026-09-05.md`;

const esc = (s) => String(s ?? "").replace(/\|/g, "\\|").replace(/\r?\n/g, " ");

/** Column names that name a competing entity identifier, in any table. */
export const COMPETING_ID = /duns|neid|cicd|casino[ _-]?city|tribe_id|_candidate|proposed|resolver|(^|_)(native_)?entity_id$|resolved_(native_)?entity_id|existing_cedar_uid|_uid_candidate/i;
/** A retired scheme's name inside a value; `_` and a word boundary both separate. */
export const RETIRED_TOKEN = /(?<![a-z])(neid|cicd|casino[ _-]?city)(?![a-z])/i;

function header(path) {
  const first = readFileSync(path, "utf8").replace(/^﻿/, "").split(/\r?\n/)[0] ?? "";
  const out = [];
  let cell = "";
  let quoted = false;
  for (const ch of first) {
    if (quoted) { if (ch === '"') quoted = false; else cell += ch; }
    else if (ch === '"') quoted = true;
    else if (ch === ",") { out.push(cell); cell = ""; }
    else cell += ch;
  }
  out.push(cell);
  return out;
}

function sampleRows(collection, table) {
  const path = `${SAMPLES}${collection}/${table}__10.csv`;
  if (!existsSync(path)) return null;
  const text = readFileSync(path, "utf8").replace(/^﻿/, "");
  const rows = [];
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
      row.push(cell); rows.push(row); row = []; cell = "";
    } else cell += ch;
  }
  if (cell.length || row.length) { row.push(cell); rows.push(row); }
  const [head, ...body] = rows;
  return body.filter((r) => r.length > 1).map((r) => Object.fromEntries(head.map((h, j) => [h, r[j] ?? ""])));
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
  const map = JSON.parse(readFileSync(MAP, "utf8"));
  const manifest = JSON.parse(readFileSync(MANIFEST, "utf8"));
  const byId = Object.fromEntries(manifest.collections.map((c) => [c.id, c]));
  const lines = [];
  const p = (s = "") => lines.push(s);
  p("# Cedar Press datasets: the field-by-field map");
  p();
  p("Generated from `data/cedar/field_map.json` by `scripts/field-map-markdown.mjs`; edit the JSON, not this file. Written 2026-09-05.");
  p();
  p("## What this is");
  p();
  p("The companion to the owner's exact public column specification (`docs/PUBLIC_DATASET_SPEC_2026-09-05.md`, addendum): for each flagship, every column its current sample header carries with one decision, the approved public header in the owner's exact order, the owner's default viewer selection, and a retirement entry for every competing entity identifier. The customer-file writer generates the export from this list (`code/1137_customer_dataset_combine.py` through `cedar_publication.apply_field_map`): it renames, drops what is internal or documented, fills the opening block from the register, builds the plural aligned arrays and the named rules, verifies every alias, orders the header exactly, and refuses a dataset that carries a column with no decision, an identifier awaiting adjudication, or a retired scheme's name in a shipped column or value. This pass changes columns, never rows, identities or publication eligibility.");
  p();
  p("Written against the ten-row samples in `public/data/cedar/samples/`. The terminal validates each rename value for value and each combine across the full table before applying it, and proves the row count, record multiplicity, event identity, totals and eligibility are unchanged.");
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
  p("- The Native-owned businesses map, written when its sample lands and the audit has run.");
  p("- The two adjudications the retirement report names (NEST's `enterprise_existing_cedar_uid`, Nonprofits' `entity_id` and `cedar_spine_entity_id`) and the recoding of Funding's `attribution_status` vocabulary: the writer stops those datasets until they are settled.");
  p();
  return lines.join("\n") + "\n";
}

export function renderRetirement() {
  const map = JSON.parse(readFileSync(MAP, "utf8"));
  const lines = [];
  const p = (s = "") => lines.push(s);
  p("# Identifier retirement report");
  p();
  p("Generated from `data/cedar/field_map.json` and the sample headers by `scripts/field-map-markdown.mjs`; edit the map, not this file. Written 2026-09-05 under the retirement rule in `docs/PUBLIC_DATASET_SPEC_2026-09-05.md` (addendum): migrate, reconcile, verify, retire, regression-test.");
  p();
  p("## The rule, as enforced");
  p();
  p("`cedar_uid` is Cedar's one cross-dataset identity. Every competing entity identifier in a flagship's header has a retirement entry in the map with what it identifies and its disposition. The writer (`cedar_publication.apply_field_map`) enforces the dispositions on every build: an `alias_verified` column is compared to `cedar_uid` on every row and the dataset is refused where they differ; an `adjudicate` column stops the dataset wherever it is populated, and is neither retained nor deleted; a `retired_scheme` name in any shipped value, or a prohibited name in the header, stops the dataset. The regression tests (`server/tests/test_field_map.py` and the site's explore test suite) fail if a prohibited identifier returns to any approved header, and the writer fails at build if one returns to a value.");
  p();
  p("`rows_affected` below is the count of rows carrying the identifier in the ten-row sample; the writer prints the full-table count on every build as `retired: dataset | old_identifier | what_it_identified | cedar_uid_or_replacement | disposition | rows_affected | unresolved_count`, and that line is the report row for the release.");
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
  p("The three findings that stop a dataset today, from the samples: Funding's `attribution_status` carries the value `cedar_neid` on every sample row (a vocabulary naming the retired scheme; recode it); NEST's `enterprise_existing_cedar_uid` is populated where the enterprise is itself a register entity and differs from the owner's uid (adjudicate: the enterprise's own cedar_uid is a real cross-reference, not an alias); Nonprofits' `entity_id` and `cedar_spine_entity_id` disagree with `cedar_uid` on the same row (adjudicate: the link was redirected and the two columns were not). None of these is deleted; the writer refuses those three datasets until they are settled.");
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

function main(argv) {
  const files = { [OUT_MAP]: renderMap(), [OUT_RETIRE]: renderRetirement() };
  if (argv.includes("--check")) {
    const stale = Object.entries(files).filter(([path, text]) => !existsSync(path) || readFileSync(path, "utf8") !== text).map(([path]) => path.slice(REPO.length));
    if (!stale.length) { process.stdout.write("  field map and retirement report current\n"); return 0; }
    process.stderr.write(`${stale.join(", ")} stale. Run \`node scripts/field-map-markdown.mjs\` and commit the result.\n`);
    return 1;
  }
  for (const [path, text] of Object.entries(files)) writeFileSync(path, text);
  process.stdout.write("  wrote docs/FIELD_MAP_2026-09-05.md and docs/IDENTIFIER_RETIREMENT_2026-09-05.md\n");
  return 0;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  process.exit(main(process.argv.slice(2)));
}
