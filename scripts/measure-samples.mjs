// Measure which of the manifest's sample files this repository actually
// holds, and record the ones it does not in data/cedar/samples.published.json.
//
//     node scripts/measure-samples.mjs             # write the record
//     node scripts/measure-samples.mjs --check     # exit 1 if the record is stale
//     node scripts/measure-samples.mjs --selftest  # prove it on a planted repository
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
import * as fsSync from "node:fs";
import { existsSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";

const REPO = fileURLToPath(new URL("..", import.meta.url));
const SAMPLES_DIR = "public/data/cedar/samples";

/** The one sentence the site shows for a sample the repository lacks. */
const REASON =
  "The ten-row sample of {table} was produced with this release but is not in " +
  "the repository yet, so the site cannot serve it.";

const paths = (root) => ({
  manifest: `${root}/data/cedar/collections.manifest.json`,
  record: `${root}/data/cedar/samples.published.json`,
  public: `${root}/public`,
});

function git(root, args) {
  return execFileSync("git", ["-C", root, ...args], { encoding: "utf8" });
}

/**
 * What the INDEX holds for the samples directory, not merely the disk.
 *
 * Codex, PR #60: the importer copies every sample under public/ before it
 * runs this script, so on the importer's machine a disk check saw all of
 * them, wrote an empty record, and the clean checkout CI builds from would
 * have had neither the files nor a record naming them - the red deploy this
 * script exists to end, back again. And PR #61: a tracked sample the
 * importer overwrote and nobody staged is the OLD bytes in the next clean
 * checkout, so membership is not enough; the worktree file has to match its
 * index blob. Published means: in the index, on disk, and byte-identical.
 */
function indexState(root) {
  let listed;
  let differing;
  try {
    listed = git(root, ["ls-files", "-z", "--", SAMPLES_DIR]);
    differing = git(root, ["diff", "--name-only", "-z", "--", SAMPLES_DIR]);
  } catch (error) {
    throw new Error(
      "cannot read the git index for the samples: " +
      `${error.message.split("\n")[0]}. The record is measured against the ` +
      "index, so it cannot be written without one.",
    );
  }
  const site = (rel) => `/${rel.replace(/^public\//, "")}`;
  return {
    tracked: new Set(listed.split("\0").filter(Boolean).map(site)),
    modified: new Set(differing.split("\0").filter(Boolean).map(site)),
  };
}

/** Why a declared sample is not published, or null when it is. */
function whyUnpublished(path, index, pub) {
  const onDisk = existsSync(`${pub}${path}`);
  if (!onDisk) return "not in repository";
  if (!index.tracked.has(path)) return "on disk, NOT in the index";
  if (index.modified.has(path)) return "on disk, modified and NOT staged";
  return null;
}

export function measure(root = REPO) {
  const at = paths(root);
  const manifest = JSON.parse(readFileSync(at.manifest, "utf8"));
  const index = indexState(root);
  const unpublished = [];
  const consider = (collection, table, path, flagship) => {
    const why = whyUnpublished(path, index, at.public);
    if (why) unpublished.push({ collection: collection.id, table, path, flagship, why });
  };
  for (const collection of manifest.collections) {
    const flagship = collection.sample?.path ?? null;
    for (const table of collection.tables) {
      if (table.sample_path) {
        consider(collection, table.table, table.sample_path, table.sample_path === flagship);
      }
    }
    // A flagship that is not one of the tables (the manifest refuses that
    // today, but the check costs nothing and the omission would be silent).
    if (flagship && !collection.tables.some((t) => t.sample_path === flagship)) {
      consider(collection, collection.sample.table, flagship, true);
    }
  }
  unpublished.sort((a, b) => a.path.localeCompare(b.path));
  return {
    generated_by: "scripts/measure-samples.mjs",
    note:
      "Every path here is declared by collections.manifest.json and not " +
      "published: absent from public/, on disk but not in the git index, or " +
      "on disk with changes not staged. Measured, never typed; re-run the " +
      "script after `git add`ing or removing a sample file.",
    reason: REASON,
    unpublished,
  };
}

function current(root) {
  const { record } = paths(root);
  if (!existsSync(record)) return null;
  return JSON.parse(readFileSync(record, "utf8"));
}

/** 0 when the record on disk is what the checkout measures, else 1 with the reason. */
export function check(root = REPO, log = (s) => process.stderr.write(s)) {
  const measured = measure(root);
  const held = current(root);
  if (held !== null && JSON.stringify(held) === JSON.stringify(measured)) {
    log(`  samples   ${measured.unpublished.length} declared sample(s) not published; record current\n`);
    return 0;
  }
  log(
    `data/cedar/samples.published.json is ${held === null ? "missing" : "stale"}: ` +
    `${measured.unpublished.length} declared sample(s) are not published ` +
    `and the record says ${held ? held.unpublished.length : "nothing"}. ` +
    "Run `node scripts/measure-samples.mjs` and commit the result.\n",
  );
  return 1;
}

/** Write the record; returns what it measured. */
export function write(root = REPO) {
  const measured = measure(root);
  const { record } = paths(root);
  const tmp = `${record}.tmp`;
  writeFileSync(tmp, JSON.stringify(measured, null, 2) + "\n");
  renameSync(tmp, record);
  return measured;
}

/**
 * The check proven on a planted repository (Codex, PR #61): a clean CI
 * checkout has disk and index agreeing, so the tests that run `--check`
 * there would stay green if this went back to a disk-only measurement.
 * Four declared samples in a throwaway git repository: committed, on disk
 * but never added, committed then overwritten without staging, and absent.
 * Exactly the last three must be on the record, each with its own reason;
 * a stale record must fail the check; staging the untracked file must move
 * the measurement; and rewriting the record must pass again.
 */
function selftest() {
  const { mkdtempSync, mkdirSync, rmSync } = fsSync;
  const root = mkdtempSync(`${tmpdir()}/measure-samples-`);
  const results = [];
  const expect = (label, got, want) => {
    const ok = JSON.stringify(got) === JSON.stringify(want);
    results.push(ok);
    process.stdout.write(`    ${ok ? "ok  " : "FAIL"}  ${label}${ok ? "" : `  (got ${JSON.stringify(got)})`}\n`);
  };
  try {
    git(root, ["init", "-q"]);
    git(root, ["config", "user.email", "selftest@example.invalid"]);
    git(root, ["config", "user.name", "selftest"]);
    const dir = `${root}/${SAMPLES_DIR}/fixture`;
    mkdirSync(dir, { recursive: true });
    mkdirSync(`${root}/data/cedar`, { recursive: true });
    const table = (name) => ({ table: `${name}.csv`, sample_path: `/data/cedar/samples/fixture/${name}__10.csv` });
    const manifest = { collections: [{ id: "fixture",
      sample: { table: "committed.csv", path: table("committed").sample_path },
      tables: [table("committed"), table("untracked"), table("modified"), table("absent")] }] };
    writeFileSync(`${root}/data/cedar/collections.manifest.json`, JSON.stringify(manifest));
    writeFileSync(`${dir}/committed__10.csv`, "a,b\n1,2\n");
    writeFileSync(`${dir}/modified__10.csv`, "a,b\n1,2\n");
    git(root, ["add", "-f", SAMPLES_DIR]);
    git(root, ["commit", "-q", "-m", "fixture"]);
    writeFileSync(`${dir}/untracked__10.csv`, "a,b\n1,2\n");
    writeFileSync(`${dir}/modified__10.csv`, "a,b\n1,3\n");

    const first = measure(root);
    expect("committed sample is published; the other three are not",
           first.unpublished.map((e) => `${e.table}: ${e.why}`),
           ["absent.csv: not in repository",
            "modified.csv: on disk, modified and NOT staged",
            "untracked.csv: on disk, NOT in the index"]);
    expect("the flagship is the committed one, so no flagship is unpublished",
           first.unpublished.some((e) => e.flagship), false);
    const quiet = () => {};
    expect("no record yet: --check fails", check(root, quiet), 1);
    write(root);
    expect("record written: --check passes", check(root, quiet), 0);
    git(root, ["add", "-f", `${dir}/untracked__10.csv`]);
    expect("staging the untracked file moves the measurement",
           measure(root).unpublished.map((e) => e.table), ["absent.csv", "modified.csv"]);
    expect("so the record is stale: --check fails", check(root, quiet), 1);
    write(root);
    expect("rewritten: --check passes", check(root, quiet), 0);
    git(root, ["add", "-f", `${dir}/modified__10.csv`]);
    expect("staging the modification publishes it",
           measure(root).unpublished.map((e) => e.table), ["absent.csv"]);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
  const failed = results.filter((r) => !r).length;
  process.stdout.write(`  measure-samples selftest ${failed ? "FAIL" : "PASS"}  ${results.length - failed} of ${results.length}\n`);
  return failed ? 1 : 0;
}

function main(argv) {
  if (argv.includes("--selftest")) return selftest();
  if (argv.includes("--check")) return check();
  const measured = write();
  process.stdout.write(`  wrote data/cedar/samples.published.json\n`);
  for (const entry of measured.unpublished) {
    process.stdout.write(`    ${entry.why}: ${entry.path}${entry.flagship ? "  (flagship)" : ""}\n`);
  }
  if (measured.unpublished.length) {
    process.stdout.write(
      "  A file on disk and not in the index, or changed and not staged, is the one " +
      "that goes missing in a clean checkout: `git add public/data/cedar/samples`, " +
      "then re-run this.\n",
    );
  }
  return 0;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  process.exit(main(process.argv.slice(2)));
}
