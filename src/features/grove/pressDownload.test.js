// What a Cedar Press download hands over: every file carries its own
// citation, because a saved file outlives the page it came from and
// provenance that lives only in the UI is provenance the reader loses.
//
// The sample rows are static files the built site serves, so `csvFor` fetches
// them. These tests inject a reader instead of a network: the one below reads
// the real file off disk, so what is asserted is the bytes a reader receives
// and not a fixture that can drift from them.

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { LAUNCH_COLLECTION, collectionSample, hasSample, samplePath } from "./collection.js";
import { csvFor, hasReleaseFile } from "./pressDownload.js";

const PUBLIC = fileURLToPath(new URL("../../../public", import.meta.url));
const readSample = (path) => readFile(`${PUBLIC}${path}`, "utf8");

/**
 * A minimal RFC 4180 reader, because line counting is wrong here and quietly
 * so: `subcontracting`'s sample carries a newline inside a quoted cell, so its
 * ten rows occupy eleven physical lines. A test that split on "\n" would have
 * reported that as a row-count bug in the data.
 */
function parseCsv(text) {
  const rows = [[""]];
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    const row = rows.at(-1);
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') {
        row[row.length - 1] += '"';
        i += 1;
      } else if (ch === '"') quoted = false;
      else row[row.length - 1] += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") row.push("");
    else if (ch === "\n") rows.push([""]);
    else if (ch !== "\r") row[row.length - 1] += ch;
  }
  return rows;
}

test("a launch dataset downloads its sample rows, citation row included", async () => {
  const { csv, name } = await csvFor({ id: "deals", name: "Indian Country Deals" }, readSample);
  assert.equal(name, "deals.csv");
  const rows = parseCsv(csv);
  // Ten real rows plus a header plus the citation. A preview that quietly
  // shrank would otherwise still pass every assertion below it.
  assert.equal(rows.length, 12, `expected header + 10 rows + citation, got ${rows.length}`);
  const last = rows.at(-1);
  assert.equal(last[0], "cite_as");
  assert.ok(last[1].startsWith("Lumecon, "), last[1]);
  // The version the descriptor carries, not one the release feed invented.
  const deals = LAUNCH_COLLECTION.find((d) => d.id === "deals");
  assert.ok(last[1].includes(`(${deals.version})`), last[1]);
  // The citation row is padded to the table's real width, so the file is not
  // ragged when a spreadsheet opens it.
  assert.equal(last.length, rows[0].length);
});

test("every collection with a sample downloads real rows for it", async () => {
  for (const dataset of LAUNCH_COLLECTION) {
    if (!hasSample(dataset.id)) continue;
    const { csv, name } = await csvFor(dataset, readSample);
    const sample = collectionSample(dataset.id);
    assert.equal(name, `${dataset.id}.csv`, dataset.id);
    const rows = parseCsv(csv);
    // The manifest states how many rows and columns Cedar published for this
    // table; the file has to match, or the manifest is describing a file that
    // is not the one being handed over.
    assert.equal(rows.length, sample.rows + 2, dataset.id);
    assert.equal(rows[0].length, sample.columns, dataset.id);
    assert.equal(rows.at(-1)[0], "cite_as", dataset.id);
    assert.equal(rows.at(-1).length, sample.columns, dataset.id);
  }
});

// The one collection with no preview is `owned`, and the reason is a real
// unresolved disagreement about which table the collection is. It must fall
// back to the description file rather than hand over another table's rows.
// UPDATED 2026-09-04. This test used `owned` as its live example of a
// collection Cedar could not settle a sample for. It is not one any more -
// the rebuild gave it native_owned_businesses__10.csv, 10 rows of 4,273 - and
// measured against the manifest, ALL TWELVE collections now carry a sample.
//
// So the fallback is exercised against a collection that does not exist rather
// than against whichever real one happens to be broken today. A test that
// depends on a real dataset staying broken passes for the wrong reason and
// fails the day somebody fixes it, which is what just happened.
test("a collection whose sample Cedar could not settle falls back, and says why", async () => {
  const absent = { id: "not-a-collection", name: "Not A Collection" };
  assert.equal(samplePath("not-a-collection"), null);
  const { name } = await csvFor(absent, readSample);
  assert.equal(name, "not-a-collection-collection-description.csv");
});

// And the contract that replaced "every collection has a sample": a collection
// either serves a sample file, or says why it does not. The "why" is data --
// the manifest's own reason for a flagship Cedar could not settle, or the
// measured record of a sample the importer produced that nobody committed
// (samples.published.json). A path with neither is the 404 this guards.
test("every storefront collection serves a sample or says why it cannot", () => {
  for (const dataset of LAUNCH_COLLECTION) {
    const path = samplePath(dataset.id);
    const sample = collectionSample(dataset.id);
    assert.ok(
      path || sample?.unavailable_because,
      `${dataset.id} has no sample path and no reason for it`,
    );
    if (path) assert.ok(existsSync(`${PUBLIC}${path}`), `${dataset.id}: ${path} would 404`);
    assert.equal(hasReleaseFile(dataset), Boolean(path), `${dataset.id}: the tile disagrees with the path`);
  }
});

// The record of unpublished samples is measured from the disk, so it must
// agree with the disk: a sample added or removed without re-running the
// measurement fails here, naming the command.
test("samples.published.json matches what public/ holds", () => {
  const script = fileURLToPath(new URL("../../../scripts/measure-samples.mjs", import.meta.url));
  const run = spawnSync(process.execPath, [script, "--check"], { encoding: "utf8" });
  assert.equal(run.status, 0, run.stderr || run.stdout);
});

// And the measurement itself, proven on a planted repository where the disk
// and the index disagree (a clean checkout never disagrees, so the check
// above alone could not tell an index-aware measurement from a disk one).
test("measure-samples tells committed, untracked, unstaged and absent apart", () => {
  const script = fileURLToPath(new URL("../../../scripts/measure-samples.mjs", import.meta.url));
  const run = spawnSync(process.execPath, [script, "--selftest"], { encoding: "utf8" });
  assert.equal(run.status, 0, run.stderr || run.stdout);
});

// A fetch that fails must not leave the button dead: the reader gets the
// honest smaller file, and the filename says which one arrived.
test("an unreadable sample falls back to the collection description", async () => {
  const { csv, name } = await csvFor(
    { id: "deals", name: "Indian Country Deals" },
    async () => null,
  );
  assert.equal(name, "deals-collection-description.csv");
  assert.equal(csv.split("\n")[0], '"field","value"');
});

test("a shelf collection without release bookkeeping cites by name", async () => {
  const entry = {
    id: "not-a-launch-dataset",
    name: "Example Shelf Collection",
    shelf: "standard",
    coverage: { kind: "series", from: 2015 },
    blurb: "What it holds.",
    linkage: "Joined to the entity layer.",
  };
  const { csv, name } = await csvFor(entry, readSample);
  // The filename says what the file is: a description of the collection,
  // never the collection's rows. The surface reads hasReleaseFile to label
  // the tile the same way before the click.
  assert.equal(hasReleaseFile(entry), false);
  assert.equal(name, "not-a-launch-dataset-collection-description.csv");
  const lines = csv.split("\n");
  assert.equal(lines[0], '"field","value"');
  const citeLine = lines.at(-1);
  assert.ok(citeLine.startsWith('"cite_as"'), citeLine);
  assert.ok(citeLine.includes("Example Shelf Collection"));
  assert.ok(citeLine.includes("cedarpress.ai"));
});
