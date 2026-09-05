// Measure which of the manifest's sample files this repository actually
// holds, and record the ones it does not in data/cedar/samples.published.json.
//
//     node scripts/measure-samples.mjs          # write the record
//     node scripts/measure-samples.mjs --check  # exit 1 if the record is stale
//
// WHY THIS EXISTS
// The manifest declares a ten-row sample for every table, and the importer
// copies each one under public/ from dist/review/samples/. Both directories
// are ignored by git (`/data/*`, `dist/`, `*.csv`), so a sample the importer
// wrote on one machine reaches the repository only when somebody adds it. On
// 2026-09-04 nineteen did not, and every deploy from then on failed the same
// test, so the live site froze at the last green build for a day while the
// twelve-collection release, a renamed collection and two rounds of review
// fixes waited behind one missing `git add`.
//
// A declared file the repository does not hold is a fact about the
// repository, not about the data, and it belongs in the open: the site says
// "not published yet" for that sample, the build prints the list, and the
// deploy goes green with the rest. This record is that fact, measured from
// the disk, never typed. The tests refuse a stale record (a file added or
// removed without re-running this), naming this command.
//
// TRACKED BY FORCE, like the manifest and the ledger beside it: `/data/*` is
// ignored as a directory and `.gitignore` re-includes this file by name.

import { execFileSync } from "node:child_process";
import { existsSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const REPO = fileURLToPath(new URL("..", import.meta.url));
const MANIFEST = `${REPO}data/cedar/collections.manifest.json`;
const RECORD = `${REPO}data/cedar/samples.published.json`;
const PUBLIC = `${REPO}public`;

/** The one sentence the site shows for a sample the repository lacks. */
const REASON =
  "The ten-row sample of {table} was produced with this release but is not in " +
  "the repository yet, so the site cannot serve it.";

/**
 * The sample files git TRACKS, not merely the ones on this disk.
 *
 * Codex, PR #60: the importer copies every sample under public/ before it
 * runs this script, so on the importer's machine a disk check saw all of
 * them, wrote an empty record, and the clean checkout CI builds from would
 * have had neither the files nor a record naming them - the red deploy this
 * script exists to end, back again. Published means in the index: a file
 * that is on this disk and not staged is exactly the file that goes missing.
 */
function tracked() {
  let out;
  try {
    out = execFileSync("git", ["-C", REPO, "ls-files", "-z", "--", "public/data/cedar/samples"],
                       { encoding: "utf8" });
  } catch (error) {
    throw new Error(
      "cannot list tracked samples: `git ls-files` failed (" +
      `${error.message.split("\n")[0]}). The record is measured against the ` +
      "index, so it cannot be written without one.",
    );
  }
  return new Set(out.split("\0").filter(Boolean).map((rel) => `/${rel.replace(/^public\//, "")}`));
}

/** Present on disk AND in the index; either alone is a file that goes missing. */
function published(path, index) {
  return index.has(path) && existsSync(`${PUBLIC}${path}`);
}

export function measure() {
  const manifest = JSON.parse(readFileSync(MANIFEST, "utf8"));
  const index = tracked();
  const unpublished = [];
  for (const collection of manifest.collections) {
    const flagship = collection.sample?.path ?? null;
    for (const table of collection.tables) {
      const path = table.sample_path;
      if (!path || published(path, index)) continue;
      unpublished.push({
        collection: collection.id,
        table: table.table,
        path,
        flagship: path === flagship,
      });
    }
    // A flagship that is not one of the tables (the manifest refuses that
    // today, but the check costs nothing and the omission would be silent).
    if (flagship && !collection.tables.some((t) => t.sample_path === flagship)
        && !published(flagship, index)) {
      unpublished.push({ collection: collection.id, table: collection.sample.table,
                         path: flagship, flagship: true });
    }
  }
  unpublished.sort((a, b) => a.path.localeCompare(b.path));
  return {
    generated_by: "scripts/measure-samples.mjs",
    note:
      "Every path here is declared by collections.manifest.json and not " +
      "published: absent from public/, or on disk but not in the git index. " +
      "Measured, never typed; re-run the script after `git add`ing or " +
      "removing a sample file.",
    reason: REASON,
    unpublished,
  };
}

function current() {
  if (!existsSync(RECORD)) return null;
  return JSON.parse(readFileSync(RECORD, "utf8"));
}

function main(argv) {
  const check = argv.includes("--check");
  const measured = measure();
  const held = current();
  const same = held !== null && JSON.stringify(held) === JSON.stringify(measured);
  if (check) {
    if (same) {
      process.stdout.write(
        `  samples   ${measured.unpublished.length} declared sample(s) not in the repository; record current\n`,
      );
      return 0;
    }
    process.stderr.write(
      `data/cedar/samples.published.json is ${held === null ? "missing" : "stale"}: ` +
      `${measured.unpublished.length} declared sample(s) are absent from public/ ` +
      `and the record says ${held ? held.unpublished.length : "nothing"}. ` +
      "Run `node scripts/measure-samples.mjs` and commit the result.\n",
    );
    return 1;
  }
  const tmp = `${RECORD}.tmp`;
  writeFileSync(tmp, JSON.stringify(measured, null, 2) + "\n");
  renameSync(tmp, RECORD);
  process.stdout.write(`  wrote data/cedar/samples.published.json\n`);
  for (const entry of measured.unpublished) {
    const where = existsSync(`${PUBLIC}${entry.path}`) ? "on disk, NOT in the index" : "not in repository";
    process.stdout.write(`    ${where}: ${entry.path}${entry.flagship ? "  (flagship)" : ""}\n`);
  }
  if (measured.unpublished.length) {
    process.stdout.write(
      "  A file on disk and not in the index is the one that goes missing in a clean " +
      "checkout: `git add public/data/cedar/samples`, then re-run this.\n",
    );
  }
  return 0;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  process.exit(main(process.argv.slice(2)));
}
